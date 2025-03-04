# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from __future__ import print_function

import codecs
import errno
import re
import os
import os.path
import shutil
import ssl
import sys
import traceback

from itertools import product

import six
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.error import URLError
import multiprocessing.pool

try:
    # Python 2 had these in the HTMLParser package.
    from HTMLParser import HTMLParser, HTMLParseError
except ImportError:
    # In Python 3, things moved to html.parser
    from html.parser import HTMLParser

    # Also, HTMLParseError is deprecated and never raised.
    class HTMLParseError(Exception):
        pass

from llnl.util.filesystem import mkdirp
import llnl.util.tty as tty

import spack.cmd
import spack.config
import spack.error
import spack.url
import spack.util.crypto
import spack.util.s3 as s3_util
import spack.util.url as url_util

from spack.util.compression import ALLOWED_ARCHIVE_TYPES


# Timeout in seconds for web requests
_timeout = 10

# See docstring for standardize_header_names()
_separators = ('', ' ', '_', '-')
HTTP_HEADER_NAME_ALIASES = {
    "Accept-ranges": set(
        ''.join((A, 'ccept', sep, R, 'anges'))
        for A, sep, R in product('Aa', _separators, 'Rr')),

    "Content-length": set(
        ''.join((C, 'ontent', sep, L, 'ength'))
        for C, sep, L in product('Cc', _separators, 'Ll')),

    "Content-type": set(
        ''.join((C, 'ontent', sep, T, 'ype'))
        for C, sep, T in product('Cc', _separators, 'Tt')),

    "Date": set(('Date', 'date')),

    "Last-modified": set(
        ''.join((L, 'ast', sep, M, 'odified'))
        for L, sep, M in product('Ll', _separators, 'Mm')),

    "Server": set(('Server', 'server'))
}


class LinkParser(HTMLParser):
    """This parser just takes an HTML page and strips out the hrefs on the
       links.  Good enough for a really simple spider. """

    def __init__(self):
        HTMLParser.__init__(self)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, val in attrs:
                if attr == 'href':
                    self.links.append(val)


class NonDaemonProcess(multiprocessing.Process):
    """Process that allows sub-processes, so pools can have sub-pools."""
    @property
    def daemon(self):
        return False

    @daemon.setter
    def daemon(self, value):
        pass


if sys.version_info[0] < 3:
    class NonDaemonPool(multiprocessing.pool.Pool):
        """Pool that uses non-daemon processes"""
        Process = NonDaemonProcess
else:

    class NonDaemonContext(type(multiprocessing.get_context())):
        Process = NonDaemonProcess

    class NonDaemonPool(multiprocessing.pool.Pool):
        """Pool that uses non-daemon processes"""

        def __init__(self, *args, **kwargs):
            kwargs['context'] = NonDaemonContext()
            super(NonDaemonPool, self).__init__(*args, **kwargs)


def uses_ssl(parsed_url):
    if parsed_url.scheme == 'https':
        return True

    if parsed_url.scheme == 's3':
        endpoint_url = os.environ.get('S3_ENDPOINT_URL')
        if not endpoint_url:
            return True

        if url_util.parse(endpoint_url, scheme='https').scheme == 'https':
            return True

    return False


__UNABLE_TO_VERIFY_SSL = (
    lambda pyver: (
        (pyver < (2, 7, 9)) or
        ((3,) < pyver < (3, 4, 3))
    ))(sys.version_info)


def read_from_url(url, accept_content_type=None):
    url = url_util.parse(url)
    context = None

    verify_ssl = spack.config.get('config:verify_ssl')

    # Don't even bother with a context unless the URL scheme is one that uses
    # SSL certs.
    if uses_ssl(url):
        if verify_ssl:
            if __UNABLE_TO_VERIFY_SSL:
                # User wants SSL verification, but it cannot be provided.
                warn_no_ssl_cert_checking()
            else:
                # User wants SSL verification, and it *can* be provided.
                context = ssl.create_default_context()
        else:
            # User has explicitly indicated that they do not want SSL
            # verification.
            context = ssl._create_unverified_context()

    req = Request(url_util.format(url))
    content_type = None
    is_web_url = url.scheme in ('http', 'https')
    if accept_content_type and is_web_url:
        # Make a HEAD request first to check the content type.  This lets
        # us ignore tarballs and gigantic files.
        # It would be nice to do this with the HTTP Accept header to avoid
        # one round-trip.  However, most servers seem to ignore the header
        # if you ask for a tarball with Accept: text/html.
        req.get_method = lambda: "HEAD"
        resp = _urlopen(req, timeout=_timeout, context=context)

        content_type = resp.headers.get('Content-type')

    # Do the real GET request when we know it's just HTML.
    req.get_method = lambda: "GET"
    response = _urlopen(req, timeout=_timeout, context=context)

    if accept_content_type and not is_web_url:
        content_type = response.headers.get('Content-type')

    reject_content_type = (
        accept_content_type and (
            content_type is None or
            not content_type.startswith(accept_content_type)))

    if reject_content_type:
        tty.debug("ignoring page {0}{1}{2}".format(
            url_util.format(url),
            " with content type " if content_type is not None else "",
            content_type or ""))

        return None, None, None

    return response.geturl(), response.headers, response


def warn_no_ssl_cert_checking():
    tty.warn("Spack will not check SSL certificates. You need to update "
             "your Python to enable certificate verification.")


def push_to_url(local_path, remote_path, **kwargs):
    keep_original = kwargs.get('keep_original', True)

    local_url = url_util.parse(local_path)
    local_file_path = url_util.local_file_path(local_url)
    if local_file_path is None:
        raise ValueError('local path must be a file:// url')

    remote_url = url_util.parse(remote_path)
    verify_ssl = spack.config.get('config:verify_ssl')

    if __UNABLE_TO_VERIFY_SSL and verify_ssl and uses_ssl(remote_url):
        warn_no_ssl_cert_checking()

    remote_file_path = url_util.local_file_path(remote_url)
    if remote_file_path is not None:
        mkdirp(os.path.dirname(remote_file_path))
        if keep_original:
            shutil.copy(local_file_path, remote_file_path)
        else:
            try:
                os.rename(local_file_path, remote_file_path)
            except OSError as e:
                if e.errno == errno.EXDEV:
                    # NOTE(opadron): The above move failed because it crosses
                    # filesystem boundaries.  Copy the file (plus original
                    # metadata), and then delete the original.  This operation
                    # needs to be done in separate steps.
                    shutil.copy2(local_file_path, remote_file_path)
                    os.remove(local_file_path)

    elif remote_url.scheme == 's3':
        extra_args = kwargs.get('extra_args', {})

        remote_path = remote_url.path
        while remote_path.startswith('/'):
            remote_path = remote_path[1:]

        s3 = s3_util.create_s3_session(remote_url)
        s3.upload_file(local_file_path, remote_url.netloc,
                       remote_path, ExtraArgs=extra_args)

        if not keep_original:
            os.remove(local_file_path)

    else:
        raise NotImplementedError(
            'Unrecognized URL scheme: {SCHEME}'.format(
                SCHEME=remote_url.scheme))


def url_exists(url):
    url = url_util.parse(url)
    local_path = url_util.local_file_path(url)
    if local_path:
        return os.path.exists(local_path)

    if url.scheme == 's3':
        s3 = s3_util.create_s3_session(url)
        from botocore.exceptions import ClientError
        try:
            s3.get_object(Bucket=url.netloc, Key=url.path)
            return True
        except ClientError as err:
            if err.response['Error']['Code'] == 'NoSuchKey':
                return False
            raise err

    # otherwise, just try to "read" from the URL, and assume that *any*
    # non-throwing response contains the resource represented by the URL
    try:
        read_from_url(url)
        return True
    except URLError:
        return False


def remove_url(url):
    url = url_util.parse(url)

    local_path = url_util.local_file_path(url)
    if local_path:
        os.remove(local_path)
        return

    if url.scheme == 's3':
        s3 = s3_util.create_s3_session(url)
        s3.delete_object(Bucket=url.s3_bucket, Key=url.path)
        return

    # Don't even try for other URL schemes.


def _list_s3_objects(client, url, num_entries, start_after=None):
    list_args = dict(
        Bucket=url.netloc,
        Prefix=url.path,
        MaxKeys=num_entries)

    if start_after is not None:
        list_args['StartAfter'] = start_after

    result = client.list_objects_v2(**list_args)

    last_key = None
    if result['IsTruncated']:
        last_key = result['Contents'][-1]['Key']

    iter = (key for key in
            (
                os.path.relpath(entry['Key'], url.path)
                for entry in result['Contents']
            )
            if key != '.')

    return iter, last_key


def _iter_s3_prefix(client, url, num_entries=1024):
    key = None
    while True:
        contents, key = _list_s3_objects(
            client, url, num_entries, start_after=key)

        for x in contents:
            yield x

        if not key:
            break


def list_url(url):
    url = url_util.parse(url)

    local_path = url_util.local_file_path(url)
    if local_path:
        return os.listdir(local_path)

    if url.scheme == 's3':
        s3 = s3_util.create_s3_session(url)
        return list(set(
            key.split('/', 1)[0]
            for key in _iter_s3_prefix(s3, url)))


def _spider(url, visited, root, depth, max_depth, raise_on_error):
    """Fetches URL and any pages it links to up to max_depth.

       depth should initially be zero, and max_depth is the max depth of
       links to follow from the root.

       Prints out a warning only if the root can't be fetched; it ignores
       errors with pages that the root links to.

       Returns a tuple of:
       - pages: dict of pages visited (URL) mapped to their full text.
       - links: set of links encountered while visiting the pages.
    """
    pages = {}     # dict from page URL -> text content.
    links = set()  # set of all links seen on visited pages.

    try:
        response_url, _, response = read_from_url(url, 'text/html')
        if not response_url or not response:
            return pages, links

        page = codecs.getreader('utf-8')(response).read()
        pages[response_url] = page

        # Parse out the links in the page
        link_parser = LinkParser()
        subcalls = []
        link_parser.feed(page)

        while link_parser.links:
            raw_link = link_parser.links.pop()
            abs_link = url_util.join(
                response_url,
                raw_link.strip(),
                resolve_href=True)
            links.add(abs_link)

            # Skip stuff that looks like an archive
            if any(raw_link.endswith(suf) for suf in ALLOWED_ARCHIVE_TYPES):
                continue

            # Skip things outside the root directory
            if not abs_link.startswith(root):
                continue

            # Skip already-visited links
            if abs_link in visited:
                continue

            # If we're not at max depth, follow links.
            if depth < max_depth:
                subcalls.append((abs_link, visited, root,
                                 depth + 1, max_depth, raise_on_error))
                visited.add(abs_link)

        if subcalls:
            pool = NonDaemonPool(processes=len(subcalls))
            try:
                results = pool.map(_spider_wrapper, subcalls)

                for sub_pages, sub_links in results:
                    pages.update(sub_pages)
                    links.update(sub_links)

            finally:
                pool.terminate()
                pool.join()

    except URLError as e:
        tty.debug(e)

        if hasattr(e, 'reason') and isinstance(e.reason, ssl.SSLError):
            tty.warn("Spack was unable to fetch url list due to a certificate "
                     "verification problem. You can try running spack -k, "
                     "which will not check SSL certificates. Use this at your "
                     "own risk.")

        if raise_on_error:
            raise NoNetworkConnectionError(str(e), url)

    except HTMLParseError as e:
        # This error indicates that Python's HTML parser sucks.
        msg = "Got an error parsing HTML."

        # Pre-2.7.3 Pythons in particular have rather prickly HTML parsing.
        if sys.version_info[:3] < (2, 7, 3):
            msg += " Use Python 2.7.3 or newer for better HTML parsing."

        tty.warn(msg, url, "HTMLParseError: " + str(e))

    except Exception as e:
        # Other types of errors are completely ignored, except in debug mode.
        tty.debug("Error in _spider: %s:%s" % (type(e), e),
                  traceback.format_exc())

    return pages, links


def _spider_wrapper(args):
    """Wrapper for using spider with multiprocessing."""
    return _spider(*args)


def _urlopen(req, *args, **kwargs):
    """Wrapper for compatibility with old versions of Python."""
    url = req
    try:
        url = url.get_full_url()
    except AttributeError:
        pass

    # We don't pass 'context' parameter because it was only introduced starting
    # with versions 2.7.9 and 3.4.3 of Python.
    if 'context' in kwargs:
        del kwargs['context']

    opener = urlopen
    if url_util.parse(url).scheme == 's3':
        import spack.s3_handler
        opener = spack.s3_handler.open

    return opener(req, *args, **kwargs)


def spider(root, depth=0):
    """Gets web pages from a root URL.

       If depth is specified (e.g., depth=2), then this will also follow
       up to <depth> levels of links from the root.

       This will spawn processes to fetch the children, for much improved
       performance over a sequential fetch.

    """

    root = url_util.parse(root)
    pages, links = _spider(root, set(), root, 0, depth, False)
    return pages, links


def find_versions_of_archive(archive_urls, list_url=None, list_depth=0):
    """Scrape web pages for new versions of a tarball.

    Arguments:
        archive_urls (str or list or tuple): URL or sequence of URLs for
            different versions of a package. Typically these are just the
            tarballs from the package file itself. By default, this searches
            the parent directories of archives.

    Keyword Arguments:
        list_url (str or None): URL for a listing of archives.
            Spack will scrape these pages for download links that look
            like the archive URL.

        list_depth (int): Max depth to follow links on list_url pages.
            Defaults to 0.
    """
    if not isinstance(archive_urls, (list, tuple)):
        archive_urls = [archive_urls]

    # Generate a list of list_urls based on archive urls and any
    # explicitly listed list_url in the package
    list_urls = set()
    if list_url is not None:
        list_urls.add(list_url)
    for aurl in archive_urls:
        list_urls |= spack.url.find_list_urls(aurl)

    # Add '/' to the end of the URL. Some web servers require this.
    additional_list_urls = set()
    for lurl in list_urls:
        if not lurl.endswith('/'):
            additional_list_urls.add(lurl + '/')
    list_urls |= additional_list_urls

    # Grab some web pages to scrape.
    pages = {}
    links = set()
    for lurl in list_urls:
        pg, lnk = spider(lurl, depth=list_depth)
        pages.update(pg)
        links.update(lnk)

    # Scrape them for archive URLs
    regexes = []
    for aurl in archive_urls:
        # This creates a regex from the URL with a capture group for
        # the version part of the URL.  The capture group is converted
        # to a generic wildcard, so we can use this to extract things
        # on a page that look like archive URLs.
        url_regex = spack.url.wildcard_version(aurl)

        # We'll be a bit more liberal and just look for the archive
        # part, not the full path.
        url_regex = os.path.basename(url_regex)

        # We need to add a / to the beginning of the regex to prevent
        # Spack from picking up similarly named packages like:
        #   https://cran.r-project.org/src/contrib/pls_2.6-0.tar.gz
        #   https://cran.r-project.org/src/contrib/enpls_5.7.tar.gz
        #   https://cran.r-project.org/src/contrib/autopls_1.3.tar.gz
        #   https://cran.r-project.org/src/contrib/matrixpls_1.0.4.tar.gz
        url_regex = '/' + url_regex

        # We need to add a $ anchor to the end of the regex to prevent
        # Spack from picking up signature files like:
        #   .asc
        #   .md5
        #   .sha256
        #   .sig
        # However, SourceForge downloads still need to end in '/download'.
        url_regex += r'(\/download)?$'

        regexes.append(url_regex)

    # Build a dict version -> URL from any links that match the wildcards.
    # Walk through archive_url links first.
    # Any conflicting versions will be overwritten by the list_url links.
    versions = {}
    for url in archive_urls + sorted(links):
        if any(re.search(r, url) for r in regexes):
            try:
                ver = spack.url.parse_version(url)
                versions[ver] = url
            except spack.url.UndetectableVersionError:
                continue

    return versions


def standardize_header_names(headers):
    """Replace certain header names with standardized spellings.

    Standardizes the spellings of the following header names:
    - Accept-ranges
    - Content-length
    - Content-type
    - Date
    - Last-modified
    - Server

    Every name considered is translated to one of the above names if the only
    difference between the two is how the first letters of each word are
    capitalized; whether words are separated; or, if separated, whether they
    are so by a dash (-), underscore (_), or space ( ).  Header names that
    cannot be mapped as described above are returned unaltered.

    For example: The standard spelling of "Content-length" would be substituted
    for any of the following names:
    - Content-length
    - content_length
    - contentlength
    - content_Length
    - contentLength
    - content Length

    ... and any other header name, such as "Content-encoding", would not be
    altered, regardless of spelling.

    If headers is a string, then it (or an appropriate substitute) is returned.

    If headers is a non-empty tuple, headers[0] is a string, and there exists a
    standardized spelling for header[0] that differs from it, then a new tuple
    is returned.  This tuple has the same elements as headers, except the first
    element is the standardized spelling for headers[0].

    If headers is a sequence, then a new list is considered, where each element
    is its corresponding element in headers, but mapped as above if a string or
    tuple.  This new list is returned if at least one of its elements differ
    from their corrsponding element in headers.

    If headers is a mapping, then a new dict is considered, where the key in
    each item is the key of its corresponding item in headers, mapped as above
    if a string or tuple.  The value is taken from the corresponding item.  If
    the keys of multiple items in headers map to the same key after being
    standardized, then the value for the resulting item is undefined.  The new
    dict is returned if at least one of its items has a key that differs from
    that of their corresponding item in headers, or if the keys of multiple
    items in headers map to the same key after being standardized.

    In all other cases headers is returned unaltered.
    """
    if isinstance(headers, six.string_types):
        for standardized_spelling, other_spellings in (
                HTTP_HEADER_NAME_ALIASES.items()):
            if headers in other_spellings:
                if headers == standardized_spelling:
                    return headers
                return standardized_spelling
        return headers

    if isinstance(headers, tuple):
        if not headers:
            return headers
        old = headers[0]
        if isinstance(old, six.string_types):
            new = standardize_header_names(old)
            if old is not new:
                return (new,) + headers[1:]
        return headers

    try:
        changed = False
        new_dict = {}
        for key, value in headers.items():
            if isinstance(key, (tuple, six.string_types)):
                old_key, key = key, standardize_header_names(key)
                changed = changed or key is not old_key

            new_dict[key] = value

        return new_dict if changed else headers
    except (AttributeError, TypeError, ValueError):
        pass

    try:
        changed = False
        new_list = []
        for item in headers:
            if isinstance(item, (tuple, six.string_types)):
                old_item, item = item, standardize_header_names(item)
                changed = changed or item is not old_item

            new_list.append(item)

        return new_list if changed else headers
    except TypeError:
        pass

    return headers


class SpackWebError(spack.error.SpackError):
    """Superclass for Spack web spidering errors."""


class NoNetworkConnectionError(SpackWebError):
    """Raised when an operation can't get an internet connection."""
    def __init__(self, message, url):
        super(NoNetworkConnectionError, self).__init__(
            "No network connection: " + str(message),
            "URL was: " + str(url))
        self.url = url
