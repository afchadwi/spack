# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from __future__ import division, print_function
from collections import defaultdict

import six.moves.urllib.parse as urllib_parse

import spack.fetch_strategy as fs
import spack.repo
import spack.util.crypto as crypto

from llnl.util import tty
from spack.url import parse_version_offset, parse_name_offset
from spack.url import parse_name, parse_version, color_url
from spack.url import substitute_version, substitution_offsets
from spack.url import UndetectableNameError, UndetectableVersionError
from spack.url import UrlParseError
from spack.util.web import find_versions_of_archive
from spack.util.naming import simplify_name

description = "debugging tool for url parsing"
section = "developer"
level = "long"


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar='SUBCOMMAND', dest='subcommand')

    # Parse
    parse_parser = sp.add_parser('parse', help='attempt to parse a url')

    parse_parser.add_argument(
        'url',
        help='url to parse')
    parse_parser.add_argument(
        '-s', '--spider', action='store_true',
        help='spider the source page for versions')

    # List
    list_parser = sp.add_parser('list', help='list urls in all packages')

    list_parser.add_argument(
        '-c', '--color', action='store_true',
        help='color the parsed version and name in the urls shown '
             '(versions will be cyan, name red)')
    list_parser.add_argument(
        '-e', '--extrapolation', action='store_true',
        help='color the versions used for extrapolation as well '
             '(additional versions will be green, names magenta)')

    excl_args = list_parser.add_mutually_exclusive_group()

    excl_args.add_argument(
        '-n', '--incorrect-name', action='store_true',
        help='only list urls for which the name was incorrectly parsed')
    excl_args.add_argument(
        '-N', '--correct-name', action='store_true',
        help='only list urls for which the name was correctly parsed')
    excl_args.add_argument(
        '-v', '--incorrect-version', action='store_true',
        help='only list urls for which the version was incorrectly parsed')
    excl_args.add_argument(
        '-V', '--correct-version', action='store_true',
        help='only list urls for which the version was correctly parsed')

    # Summary
    sp.add_parser(
        'summary',
        help='print a summary of how well we are parsing package urls')

    # Stats
    sp.add_parser(
        'stats',
        help='print statistics on versions and checksums for all packages')


def url(parser, args):
    action = {
        'parse':   url_parse,
        'list':    url_list,
        'summary': url_summary,
        'stats':   url_stats,
    }

    action[args.subcommand](args)


def url_parse(args):
    url = args.url

    tty.msg('Parsing URL: {0}'.format(url))
    print()

    ver,  vs, vl, vi, vregex = parse_version_offset(url)
    tty.msg('Matched version regex {0:>2}: r{1!r}'.format(vi, vregex))

    name, ns, nl, ni, nregex = parse_name_offset(url, ver)
    tty.msg('Matched  name   regex {0:>2}: r{1!r}'.format(ni, nregex))

    print()
    tty.msg('Detected:')
    try:
        print_name_and_version(url)
    except UrlParseError as e:
        tty.error(str(e))

    print('    name:    {0}'.format(name))
    print('    version: {0}'.format(ver))
    print()

    tty.msg('Substituting version 9.9.9b:')
    newurl = substitute_version(url, '9.9.9b')
    print_name_and_version(newurl)

    if args.spider:
        print()
        tty.msg('Spidering for versions:')
        versions = find_versions_of_archive(url)

        if not versions:
            print('  Found no versions for {0}'.format(name))
            return

        max_len = max(len(str(v)) for v in versions)

        for v in sorted(versions):
            print('{0:{1}}  {2}'.format(v, max_len, versions[v]))


def url_list(args):
    urls = set()

    # Gather set of URLs from all packages
    for pkg in spack.repo.path.all_packages():
        url = getattr(pkg.__class__, 'url', None)
        urls = url_list_parsing(args, urls, url, pkg)

        for params in pkg.versions.values():
            url = params.get('url', None)
            urls = url_list_parsing(args, urls, url, pkg)

    # Print URLs
    for url in sorted(urls):
        if args.color or args.extrapolation:
            print(color_url(url, subs=args.extrapolation, errors=True))
        else:
            print(url)

    # Return the number of URLs that were printed, only for testing purposes
    return len(urls)


def url_summary(args):
    # Collect statistics on how many URLs were correctly parsed
    total_urls       = 0
    correct_names    = 0
    correct_versions = 0

    # Collect statistics on which regexes were matched and how often
    name_regex_dict    = dict()
    name_count_dict    = defaultdict(int)
    version_regex_dict = dict()
    version_count_dict = defaultdict(int)

    tty.msg('Generating a summary of URL parsing in Spack...')

    # Loop through all packages
    for pkg in spack.repo.path.all_packages():
        urls = set()

        url = getattr(pkg.__class__, 'url', None)
        if url:
            urls.add(url)

        for params in pkg.versions.values():
            url = params.get('url', None)
            if url:
                urls.add(url)

        # Calculate statistics
        for url in urls:
            total_urls += 1

            # Parse versions
            version = None
            try:
                version, vs, vl, vi, vregex = parse_version_offset(url)
                version_regex_dict[vi] = vregex
                version_count_dict[vi] += 1
                if version_parsed_correctly(pkg, version):
                    correct_versions += 1
            except UndetectableVersionError:
                pass

            # Parse names
            try:
                name, ns, nl, ni, nregex = parse_name_offset(url, version)
                name_regex_dict[ni] = nregex
                name_count_dict[ni] += 1
                if name_parsed_correctly(pkg, name):
                    correct_names += 1
            except UndetectableNameError:
                pass

    print()
    print('    Total URLs found:          {0}'.format(total_urls))
    print('    Names correctly parsed:    {0:>4}/{1:>4} ({2:>6.2%})'.format(
        correct_names, total_urls, correct_names / total_urls))
    print('    Versions correctly parsed: {0:>4}/{1:>4} ({2:>6.2%})'.format(
        correct_versions, total_urls, correct_versions / total_urls))
    print()

    tty.msg('Statistics on name regular expressions:')

    print()
    print('    Index  Count  Regular Expression')
    for ni in sorted(name_regex_dict.keys()):
        print('    {0:>3}: {1:>6}   r{2!r}'.format(
            ni, name_count_dict[ni], name_regex_dict[ni]))
    print()

    tty.msg('Statistics on version regular expressions:')

    print()
    print('    Index  Count  Regular Expression')
    for vi in sorted(version_regex_dict.keys()):
        print('    {0:>3}: {1:>6}   r{2!r}'.format(
            vi, version_count_dict[vi], version_regex_dict[vi]))
    print()

    # Return statistics, only for testing purposes
    return (total_urls, correct_names, correct_versions,
            name_count_dict, version_count_dict)


def url_stats(args):
    class UrlStats(object):
        def __init__(self):
            self.total = 0
            self.schemes = defaultdict(lambda: 0)
            self.checksums = defaultdict(lambda: 0)
            self.url_type = defaultdict(lambda: 0)
            self.git_type = defaultdict(lambda: 0)

        def add(self, fetcher):
            self.total += 1

            url_type = fetcher.url_attr
            self.url_type[url_type or 'no code'] += 1

            if url_type == 'url':
                digest = getattr(fetcher, 'digest', None)
                if digest:
                    algo = crypto.hash_algo_for_digest(digest)
                else:
                    algo = 'no checksum'
                self.checksums[algo] += 1

                # parse out the URL scheme (https/http/ftp/etc.)
                urlinfo = urllib_parse.urlparse(fetcher.url)
                self.schemes[urlinfo.scheme] += 1

            elif url_type == 'git':
                if getattr(fetcher, 'commit', None):
                    self.git_type['commit'] += 1
                elif getattr(fetcher, 'branch', None):
                    self.git_type['branch'] += 1
                elif getattr(fetcher, 'tag', None):
                    self.git_type['tag'] += 1
                else:
                    self.git_type['no ref'] += 1

    npkgs = 0
    version_stats = UrlStats()
    resource_stats = UrlStats()

    for pkg in spack.repo.path.all_packages():
        npkgs += 1

        for v, args in pkg.versions.items():
            fetcher = fs.for_package_version(pkg, v)
            version_stats.add(fetcher)

        for _, resources in pkg.resources.items():
            for resource in resources:
                resource_stats.add(resource.fetcher)

    # print a nice summary table
    tty.msg("URL stats for %d packages:" % npkgs)

    def print_line():
        print("-" * 62)

    def print_stat(indent, name, stat_name=None):
        width = 20 - indent
        fmt = " " * indent
        fmt += "%%-%ds" % width
        if stat_name is None:
            print(fmt % name)
        else:
            fmt += "%12d%8.1f%%%12d%8.1f%%"
            v = getattr(version_stats, stat_name).get(name, 0)
            r = getattr(resource_stats, stat_name).get(name, 0)
            print(fmt % (name,
                         v, v / version_stats.total * 100,
                         r, r / resource_stats.total * 100))

    print_line()
    print("%-20s%12s%9s%12s%9s" % ("stat", "versions", "%", "resources", "%"))
    print_line()
    print_stat(0, "url", "url_type")

    print_stat(4, "schemes")
    schemes = set(version_stats.schemes) | set(resource_stats.schemes)
    for scheme in schemes:
        print_stat(8, scheme, "schemes")

    print_stat(4, "checksums")
    checksums = set(version_stats.checksums) | set(resource_stats.checksums)
    for checksum in checksums:
        print_stat(8, checksum, "checksums")
    print_line()

    types = set(version_stats.url_type) | set(resource_stats.url_type)
    types -= set(["url", "git"])
    for url_type in sorted(types):
        print_stat(0, url_type, "url_type")
        print_line()

    print_stat(0, "git", "url_type")
    git_types = set(version_stats.git_type) | set(resource_stats.git_type)
    for git_type in sorted(git_types):
        print_stat(4, git_type, "git_type")
    print_line()


def print_name_and_version(url):
    """Prints a URL. Underlines the detected name with dashes and
    the detected version with tildes.

    Args:
        url (str): The url to parse
    """
    name, ns, nl, ntup, ver, vs, vl, vtup = substitution_offsets(url)
    underlines = [' '] * max(ns + nl, vs + vl)
    for i in range(ns, ns + nl):
        underlines[i] = '-'
    for i in range(vs, vs + vl):
        underlines[i] = '~'

    print('    {0}'.format(url))
    print('    {0}'.format(''.join(underlines)))


def url_list_parsing(args, urls, url, pkg):
    """Helper function for :func:`url_list`.

    Args:
        args (argparse.Namespace): The arguments given to ``spack url list``
        urls (set): List of URLs that have already been added
        url (str or None): A URL to potentially add to ``urls`` depending on
            ``args``
        pkg (spack.package.PackageBase): The Spack package

    Returns:
        set: The updated set of ``urls``
    """
    if url:
        if args.correct_name or args.incorrect_name:
            # Attempt to parse the name
            try:
                name = parse_name(url)
                if (args.correct_name and
                    name_parsed_correctly(pkg, name)):
                    # Add correctly parsed URLs
                    urls.add(url)
                elif (args.incorrect_name and
                      not name_parsed_correctly(pkg, name)):
                    # Add incorrectly parsed URLs
                    urls.add(url)
            except UndetectableNameError:
                if args.incorrect_name:
                    # Add incorrectly parsed URLs
                    urls.add(url)
        elif args.correct_version or args.incorrect_version:
            # Attempt to parse the version
            try:
                version = parse_version(url)
                if (args.correct_version and
                    version_parsed_correctly(pkg, version)):
                    # Add correctly parsed URLs
                    urls.add(url)
                elif (args.incorrect_version and
                      not version_parsed_correctly(pkg, version)):
                    # Add incorrectly parsed URLs
                    urls.add(url)
            except UndetectableVersionError:
                if args.incorrect_version:
                    # Add incorrectly parsed URLs
                    urls.add(url)
        else:
            urls.add(url)

    return urls


def name_parsed_correctly(pkg, name):
    """Determine if the name of a package was correctly parsed.

    Args:
        pkg (spack.package.PackageBase): The Spack package
        name (str): The name that was extracted from the URL

    Returns:
        bool: True if the name was correctly parsed, else False
    """
    pkg_name = pkg.name

    name = simplify_name(name)

    # After determining a name, `spack create` determines a build system.
    # Some build systems prepend a special string to the front of the name.
    # Since this can't be guessed from the URL, it would be unfair to say
    # that these names are incorrectly parsed, so we remove them.
    if pkg_name.startswith('r-'):
        pkg_name = pkg_name[2:]
    elif pkg_name.startswith('py-'):
        pkg_name = pkg_name[3:]
    elif pkg_name.startswith('perl-'):
        pkg_name = pkg_name[5:]
    elif pkg_name.startswith('octave-'):
        pkg_name = pkg_name[7:]

    return name == pkg_name


def version_parsed_correctly(pkg, version):
    """Determine if the version of a package was correctly parsed.

    Args:
        pkg (spack.package.PackageBase): The Spack package
        version (str): The version that was extracted from the URL

    Returns:
        bool: True if the name was correctly parsed, else False
    """
    version = remove_separators(version)

    # If the version parsed from the URL is listed in a version()
    # directive, we assume it was correctly parsed
    for pkg_version in pkg.versions:
        pkg_version = remove_separators(pkg_version)
        if pkg_version == version:
            return True
    return False


def remove_separators(version):
    """Removes separator characters ('.', '_', and '-') from a version.

    A version like 1.2.3 may be displayed as 1_2_3 in the URL.
    Make sure 1.2.3, 1-2-3, 1_2_3, and 123 are considered equal.
    Unfortunately, this also means that 1.23 and 12.3 are equal.

    Args:
        version (str or Version): A version

    Returns:
        str: The version with all separator characters removed
    """
    version = str(version)

    version = version.replace('.', '')
    version = version.replace('_', '')
    version = version.replace('-', '')

    return version
