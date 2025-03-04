# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import ast
import os
import platform
import re
import sys

import llnl.util.tty as tty
from llnl.util.lang import match_predicate
from llnl.util.filesystem import (force_remove, get_filetype,
                                  path_contains_subdirectory)

import spack.store
import spack.util.spack_json as sjson
from spack.util.environment import is_system_path
from spack.util.prefix import Prefix
from spack import *


class Python(AutotoolsPackage):
    """The Python programming language."""

    homepage = "https://www.python.org/"
    url      = "https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz"
    list_url = "https://www.python.org/downloads/"
    list_depth = 1

    maintainers = ['adamjstewart']

    version('3.8.0',  sha256='f1069ad3cae8e7ec467aa98a6565a62a48ef196cb8f1455a245a08db5e1792df')
    version('3.7.4',  sha256='d63e63e14e6d29e17490abbe6f7d17afb3db182dbd801229f14e55f4157c4ba3', preferred=True)
    version('3.7.3',  sha256='d62e3015f2f89c970ac52343976b406694931742fbde2fed8d1ce8ebb4e1f8ff')
    version('3.7.2',  sha256='f09d83c773b9cc72421abba2c317e4e6e05d919f9bcf34468e192b6a6c8e328d')
    version('3.7.1',  sha256='36c1b81ac29d0f8341f727ef40864d99d8206897be96be73dc34d4739c9c9f06')
    version('3.7.0',  sha256='85bb9feb6863e04fb1700b018d9d42d1caac178559ffa453d7e6a436e259fd0d')
    version('3.6.8',  sha256='7f5b1f08b3b0a595387ef6c64c85b1b13b38abef0dd871835ee923262e4f32f0')
    version('3.6.7',  sha256='b7c36f7ed8f7143b2c46153b7332db2227669f583ea0cce753facf549d1a4239')
    version('3.6.6',  sha256='7d56dadf6c7d92a238702389e80cfe66fbfae73e584189ed6f89c75bbf3eda58')
    version('3.6.5',  sha256='53a3e17d77cd15c5230192b6a8c1e031c07cd9f34a2f089a731c6f6bd343d5c6')
    version('3.6.4',  sha256='7dc453e1a93c083388eb1a23a256862407f8234a96dc4fae0fc7682020227486')
    version('3.6.3',  sha256='ab6193af1921b30f587b302fe385268510e80187ca83ca82d2bfe7ab544c6f91')
    version('3.6.2',  sha256='7919489310a5f17f7acbab64d731e46dca0702874840dadce8bd4b2b3b8e7a82')
    version('3.6.1',  sha256='aa50b0143df7c89ce91be020fe41382613a817354b33acdc6641b44f8ced3828')
    version('3.6.0',  sha256='aa472515800d25a3739833f76ca3735d9f4b2fe77c3cb21f69275e0cce30cb2b')
    version('3.5.7',  sha256='542d94920a2a06a471a73b51614805ad65366af98145b0369bc374cf248b521b')
    version('3.5.2',  sha256='1524b840e42cf3b909e8f8df67c1724012c7dc7f9d076d4feef2d3eff031e8a0')
    version('3.5.1',  sha256='687e067d9f391da645423c7eda8205bae9d35edc0c76ef5218dcbe4cc770d0d7')
    version('3.5.0',  sha256='584e3d5a02692ca52fce505e68ecd77248a6f2c99adf9db144a39087336b0fe0')
    version('3.4.10', sha256='217757699249ab432571b381386d441e12b433100ab5f908051fcb7cced2539d')
    version('3.4.3',  sha256='8b743f56e9e50bf0923b9e9c45dd927c071d7aa56cd46569d8818add8cf01147')
    version('3.3.6',  sha256='0a58ad1f1def4ecc90b18b0c410a3a0e1a48cf7692c75d1f83d0af080e5d2034')
    version('3.2.6',  sha256='fc1e41296e29d476f696303acae293ae7a2310f0f9d0d637905e722a3f16163e')
    version('3.1.5',  sha256='d12dae6d06f52ef6bf1271db4d5b4d14b5dd39813e324314e72b648ef1bc0103')
    version('2.7.16', sha256='01da813a3600876f03f46db11cc5c408175e99f03af2ba942ef324389a83bad5')
    version('2.7.15', sha256='18617d1f15a380a919d517630a9cd85ce17ea602f9bbdc58ddc672df4b0239db')
    version('2.7.14', sha256='304c9b202ea6fbd0a4a8e0ad3733715fbd4749f2204a9173a58ec53c32ea73e8')
    version('2.7.13', sha256='a4f05a0720ce0fd92626f0278b6b433eee9a6173ddf2bced7957dfb599a5ece1')
    version('2.7.12', sha256='3cb522d17463dfa69a155ab18cffa399b358c966c0363d6c8b5b3bf1384da4b6')
    version('2.7.11', sha256='82929b96fd6afc8da838b149107078c02fa1744b7e60999a8babbc0d3fa86fc6')
    version('2.7.10', sha256='eda8ce6eec03e74991abb5384170e7c65fcd7522e409b8e83d7e6372add0f12a')
    version('2.7.9',  sha256='c8bba33e66ac3201dabdc556f0ea7cfe6ac11946ec32d357c4c6f9b018c12c5b')
    version('2.7.8',  sha256='74d70b914da4487aa1d97222b29e9554d042f825f26cb2b93abd20fdda56b557')

    extendable = True

    # --enable-shared is known to cause problems for some users on macOS
    # See http://bugs.python.org/issue29846
    variant('shared', default=sys.platform != 'darwin',
            description='Enable shared libraries')
    # From https://docs.python.org/2/c-api/unicode.html: Python's default
    # builds use a 16-bit type for Py_UNICODE and store Unicode values
    # internally as UCS2. It is also possible to build a UCS4 version of Python
    # (most recent Linux distributions come with UCS4 builds of Python).  These
    # builds then use a 32-bit type for Py_UNICODE and store Unicode data
    # internally as UCS4. Note that UCS2 and UCS4 Python builds are not binary
    # compatible.
    variant('ucs4', default=False,
            description='Enable UCS4 (wide) unicode strings')
    variant('pic', default=True,
            description='Produce position-independent code (for shared libs)')
    variant(
        'optimizations',
        default=False,
        description='Enable expensive build-time optimizations, if available'
    )
    # See https://legacy.python.org/dev/peps/pep-0394/
    variant('pythoncmd', default=True,
            description="Symlink 'python3' executable to 'python' "
            "(not PEP 394 compliant)")

    # Optional Python modules
    variant('readline', default=True,  description='Build readline module')
    variant('ssl',      default=True,  description='Build ssl module')
    variant('sqlite3',  default=True,  description='Build sqlite3 module')
    variant('dbm',      default=True,  description='Build dbm module')
    variant('nis',      default=False, description='Build nis module')
    variant('zlib',     default=True,  description='Build zlib module')
    variant('bz2',      default=True,  description='Build bz2 module')
    variant('lzma',     default=True,  description='Build lzma module')
    variant('pyexpat',  default=True,  description='Build pyexpat module')
    variant('ctypes',   default=True,  description='Build ctypes module')
    variant('tkinter',  default=False, description='Build tkinter module')
    variant('uuid',     default=False, description='Build uuid module')
    variant('tix',      default=False, description='Build Tix module')

    depends_on('pkgconfig@0.9.0:', type='build')
    depends_on('gettext')

    # Optional dependencies
    # See detect_modules() in setup.py for details
    depends_on('readline', when='+readline')
    depends_on('ncurses', when='+readline')
    depends_on('openssl', when='+ssl')
    depends_on('openssl@1.0.2:', when='@3.7:+ssl')  # https://docs.python.org/3/whatsnew/3.7.html#build-changes
    depends_on('sqlite@3.0.8:', when='+sqlite3')
    depends_on('gdbm', when='+dbm')  # alternatively ndbm or berkeley-db
    depends_on('libnsl', when='+nis')
    depends_on('zlib@1.1.3:', when='+zlib')
    depends_on('bzip2', when='+bz2')
    depends_on('xz', when='@3.3:+lzma')
    depends_on('expat', when='+pyexpat')
    depends_on('libffi', when='+ctypes')
    depends_on('tk', when='+tkinter')
    depends_on('tcl', when='+tkinter')
    depends_on('tix', when='+tix')
    if sys.platform != 'darwin':
        # On macOS systems, Spack's libuuid conflicts with the system-installed
        # version and breaks anything linked against Cocoa/Carbon. Since the
        # system-provided version is sufficient to build Python's UUID support,
        # the easy solution is to only depend on Spack's libuuid when *not* on
        # a Mac.
        depends_on('libuuid', when='+uuid')

    patch('tkinter.patch', when='@:2.8,3.3:3.7 platform=darwin')

    # Ensure that distutils chooses correct compiler option for RPATH on cray:
    patch('cray-rpath-2.3.patch', when='@2.3:3.0.1 platform=cray')
    patch('cray-rpath-3.1.patch', when='@3.1:3.99  platform=cray')

    # Fixes an alignment problem with more aggressive optimization in gcc8
    # https://github.com/python/cpython/commit/0b91f8a668201fc58fa732b8acc496caedfdbae0
    patch('gcc-8-2.7.14.patch', when='@2.7.14 %gcc@8:')

    # Fixes build with the Intel compilers
    # https://github.com/python/cpython/pull/16717
    patch('intel-3.6.7.patch', when='@3.6.7:3.6.8,3.7.1: %intel')

    # For more information refer to this bug report:
    # https://bugs.python.org/issue29712
    conflicts(
        '@:2.8 +shared',
        when='+optimizations',
        msg='+optimizations is incompatible with +shared in python@2.X'
    )
    conflicts('+tix', when='~tkinter',
              msg='python+tix requires python+tix+tkinter')

    _DISTUTIL_VARS_TO_SAVE = ['LDSHARED']
    _DISTUTIL_CACHE_FILENAME = 'sysconfig.json'
    _distutil_vars = None

    # An in-source build with --enable-optimizations fails for python@3.X
    build_directory = 'spack-build'

    def url_for_version(self, version):
        url = "https://www.python.org/ftp/python/{0}/Python-{1}.tgz"
        return url.format(re.split('[a-z]', str(version))[0], version)

    @when('@2.7:2.8,3.4:')
    def patch(self):
        # NOTE: Python's default installation procedure makes it possible for a
        # user's local configurations to change the Spack installation.  In
        # order to prevent this behavior for a full installation, we must
        # modify the installation script so that it ignores user files.
        ff = FileFilter('Makefile.pre.in')
        ff.filter(
            r'^(.*)setup\.py(.*)((build)|(install))(.*)$',
            r'\1setup.py\2 --no-user-cfg \3\6'
        )

    def setup_build_environment(self, env):
        spec = self.spec

        # TODO: The '--no-user-cfg' option for Python installation is only in
        # Python v2.7 and v3.4+ (see https://bugs.python.org/issue1180) and
        # adding support for ignoring user configuration will require
        # significant changes to this package for other Python versions.
        if not spec.satisfies('@2.7:2.8,3.4:'):
            tty.warn(('Python v{0} may not install properly if Python '
                      'user configurations are present.').format(self.version))

        # Need this to allow python build to find the Python installation.
        env.set('MACOSX_DEPLOYMENT_TARGET', platform.mac_ver()[0])

    def configure_args(self):
        spec = self.spec
        config_args = []

        # setup.py needs to be able to read the CPPFLAGS and LDFLAGS
        # as it scans for the library and headers to build
        link_deps = spec.dependencies('link')

        if link_deps:
            # Header files are often included assuming they reside in a
            # subdirectory of prefix.include, e.g. #include <openssl/ssl.h>,
            # which is why we don't use HeaderList here. The header files of
            # libffi reside in prefix.lib but the configure script of Python
            # finds them using pkg-config.
            cppflags = ' '.join('-I' + spec[dep.name].prefix.include
                                for dep in link_deps)

            # Currently, the only way to get SpecBuildInterface wrappers of the
            # dependencies (which we need to get their 'libs') is to get them
            # using spec.__getitem__.
            ldflags = ' '.join(spec[dep.name].libs.search_flags
                               for dep in link_deps)

            config_args.extend(['CPPFLAGS=' + cppflags, 'LDFLAGS=' + ldflags])

        # https://docs.python.org/3/whatsnew/3.7.html#build-changes
        if spec.satisfies('@:3.6'):
            config_args.append('--with-threads')

        if spec.satisfies('@2.7.13:2.8,3.5.3:', strict=True) \
                and '+optimizations' in spec:
            config_args.append('--enable-optimizations')

        if spec.satisfies('%gcc platform=darwin'):
            config_args.append('--disable-toolbox-glue')

        if spec.satisfies('%intel', strict=True) and \
                spec.satisfies('@2.7.12:2.8,3.5.2:', strict=True):
            config_args.append('--with-icc')

        if '+shared' in spec:
            config_args.append('--enable-shared')
        else:
            config_args.append('--disable-shared')

        if '+ucs4' in spec:
            if spec.satisfies('@:2.7'):
                config_args.append('--enable-unicode=ucs4')
            elif spec.satisfies('@3.0:3.2'):
                config_args.append('--with-wide-unicode')
            elif spec.satisfies('@3.3:'):
                # https://docs.python.org/3.3/whatsnew/3.3.html#functionality
                raise ValueError(
                    '+ucs4 variant not compatible with Python 3.3 and beyond')

        if spec.satisfies('@3:'):
            config_args.append('--without-ensurepip')

        if '+pic' in spec:
            config_args.append('CFLAGS={0}'.format(self.compiler.pic_flag))

        if spec.satisfies('@3.7:'):
            if '+ssl' in spec:
                config_args.append('--with-openssl={0}'.format(
                    spec['openssl'].prefix))

        if '+dbm' in spec:
            # Default order is ndbm:gdbm:bdb
            config_args.append('--with-dbmliborder=gdbm:bdb:ndbm')
        else:
            config_args.append('--with-dbmliborder=')

        if '+pyexpat' in spec:
            config_args.append('--with-system-expat')
        else:
            config_args.append('--without-system-expat')

        if '+ctypes' in spec:
            config_args.append('--with-system-ffi')
        else:
            config_args.append('--without-system-ffi')

        if '+tkinter' in spec:
            config_args.extend([
                '--with-tcltk-includes=-I{0} -I{1}'.format(
                    spec['tcl'].prefix.include, spec['tk'].prefix.include),
                '--with-tcltk-libs={0} {1}'.format(
                    spec['tcl'].libs.ld_flags, spec['tk'].libs.ld_flags)
            ])

        return config_args

    @run_after('install')
    def _save_distutil_vars(self):
        """
        Run before changing automatically generated contents of the
        _sysconfigdata.py, which is used by distutils to figure out what
        executables to use while compiling and linking extensions. If we build
        extensions with spack those executables should be spack's wrappers.
        Spack partially covers this by setting environment variables that
        are also accounted for by distutils. Currently there is one more known
        variable that must be set, which is LDSHARED, so the method saves its
        autogenerated value to pass it to the dependent package's setup script.
        """

        self._distutil_vars = {}

        input_filename = self.get_sysconfigdata_name()
        input_dict = None
        try:
            with open(input_filename) as input_file:
                match = re.search(r'build_time_vars\s*=\s*(?P<dict>{.*})',
                                  input_file.read(),
                                  flags=re.DOTALL)

                if match:
                    input_dict = ast.literal_eval(match.group('dict'))
        except (IOError, SyntaxError):
            pass

        if not input_dict:
            tty.warn("Failed to find 'build_time_vars' dictionary in file "
                     "'%s'. This might cause the extensions that are "
                     "installed with distutils to call compilers directly "
                     "avoiding Spack's wrappers." % input_filename)
            return

        for var_name in Python._DISTUTIL_VARS_TO_SAVE:
            if var_name in input_dict:
                self._distutil_vars[var_name] = input_dict[var_name]
            else:
                tty.warn("Failed to find key '%s' in 'build_time_vars' "
                         "dictionary in file '%s'. This might cause the "
                         "extensions that are installed with distutils to "
                         "call compilers directly avoiding Spack's wrappers."
                         % (var_name, input_filename))

        if len(self._distutil_vars) > 0:
            output_filename = None
            try:
                output_filename = join_path(
                    spack.store.layout.metadata_path(self.spec),
                    Python._DISTUTIL_CACHE_FILENAME)
                with open(output_filename, 'w') as output_file:
                    sjson.dump(self._distutil_vars, output_file)
            except Exception:
                tty.warn("Failed to save metadata for distutils. This might "
                         "cause the extensions that are installed with "
                         "distutils to call compilers directly avoiding "
                         "Spack's wrappers.")
                # We make the cache empty if we failed to save it to file
                # to provide the same behaviour as in the case when the cache
                # is initialized by the method load_distutils_data().
                self._distutil_vars = {}
                if output_filename:
                    force_remove(output_filename)

    def _load_distutil_vars(self):
        # We update and keep the cache unchanged only if the package is
        # installed.
        if not self._distutil_vars and self.installed:
            try:
                input_filename = join_path(
                    spack.store.layout.metadata_path(self.spec),
                    Python._DISTUTIL_CACHE_FILENAME)
                if os.path.isfile(input_filename):
                    with open(input_filename) as input_file:
                        self._distutil_vars = sjson.load(input_file)
            except Exception:
                pass

            if not self._distutil_vars:
                self._distutil_vars = {}

        return self._distutil_vars

    @run_after('install')
    def filter_compilers(self):
        """Run after install to tell the configuration files and Makefiles
        to use the compilers that Spack built the package with.

        If this isn't done, they'll have CC and CXX set to Spack's generic
        cc and c++. We want them to be bound to whatever compiler
        they were built with."""

        kwargs = {'ignore_absent': True, 'backup': False, 'string': True}

        filenames = [
            self.get_sysconfigdata_name(), self.get_makefile_filename()
        ]

        filter_file(spack_cc,  self.compiler.cc,  *filenames, **kwargs)
        filter_file(spack_cxx, self.compiler.cxx, *filenames, **kwargs)

    @run_after('install')
    def symlink(self):
        spec = self.spec
        prefix = self.prefix

        # TODO:
        # On OpenSuse 13, python uses <prefix>/lib64/python2.7/lib-dynload/*.so
        # instead of <prefix>/lib/python2.7/lib-dynload/*.so. Oddly enough the
        # result is that Python can not find modules like cPickle. A workaround
        # for now is to symlink to `lib`:
        src = os.path.join(prefix.lib64,
                           'python{0}'.format(self.version.up_to(2)),
                           'lib-dynload')
        dst = os.path.join(prefix.lib,
                           'python{0}'.format(self.version.up_to(2)),
                           'lib-dynload')
        if os.path.isdir(src) and not os.path.isdir(dst):
            mkdirp(dst)
            for f in os.listdir(src):
                os.symlink(os.path.join(src, f),
                           os.path.join(dst, f))

        if spec.satisfies('@3:') and spec.satisfies('+pythoncmd'):
            os.symlink(os.path.join(prefix.bin, 'python3'),
                       os.path.join(prefix.bin, 'python'))
            os.symlink(os.path.join(prefix.bin, 'python3-config'),
                       os.path.join(prefix.bin, 'python-config'))

    @run_after('install')
    @on_package_attributes(run_tests=True)
    def import_tests(self):
        """Test that basic Python functionality works."""

        spec = self.spec

        with working_dir('spack-test', create=True):
            # Ensure that readline module works
            if '+readline' in spec:
                self.command('-c', 'import readline')

            # Ensure that ssl module works
            if '+ssl' in spec:
                self.command('-c', 'import ssl')
                self.command('-c', 'import hashlib')

            # Ensure that sqlite3 module works
            if '+sqlite3' in spec:
                self.command('-c', 'import sqlite3')

            # Ensure that dbm module works
            if '+dbm' in spec:
                self.command('-c', 'import dbm')

            # Ensure that nis module works
            if '+nis' in spec:
                self.command('-c', 'import nis')

            # Ensure that zlib module works
            if '+zlib' in spec:
                self.command('-c', 'import zlib')

            # Ensure that bz2 module works
            if '+bz2' in spec:
                self.command('-c', 'import bz2')

            # Ensure that lzma module works
            if spec.satisfies('@3.3:'):
                if '+lzma' in spec:
                    self.command('-c', 'import lzma')

            # Ensure that pyexpat module works
            if '+pyexpat' in spec:
                self.command('-c', 'import xml.parsers.expat')
                self.command('-c', 'import xml.etree.ElementTree')

            # Ensure that ctypes module works
            if '+ctypes' in spec:
                self.command('-c', 'import ctypes')

            # Ensure that tkinter module works
            # https://wiki.python.org/moin/TkInter
            if '+tkinter' in spec:
                # Only works if ForwardX11Trusted is enabled, i.e. `ssh -Y`
                if 'DISPLAY' in env:
                    if spec.satisfies('@3:'):
                        self.command('-c', 'import tkinter; tkinter._test()')
                    else:
                        self.command('-c', 'import Tkinter; Tkinter._test()')
                else:
                    if spec.satisfies('@3:'):
                        self.command('-c', 'import tkinter')
                    else:
                        self.command('-c', 'import Tkinter')

            # Ensure that uuid module works
            if '+uuid' in spec:
                self.command('-c', 'import uuid')

    # ========================================================================
    # Set up environment to make install easy for python extensions.
    # ========================================================================

    @property
    def command(self):
        """Returns the Python command, which may vary depending
        on the version of Python and how it was installed.

        In general, Python 2 comes with ``python`` and ``python2`` commands,
        while Python 3 only comes with a ``python3`` command. However, some
        package managers will symlink ``python`` to ``python3``, while others
        may contain ``python3.6``, ``python3.5``, and ``python3.4`` in the
        same directory.

        Returns:
            Executable: the Python command
        """
        # We need to be careful here. If the user is using an externally
        # installed python, several different commands could be located
        # in the same directory. Be as specific as possible. Search for:
        #
        # * python3.6
        # * python3
        # * python
        #
        # in that order if using python@3.6.5, for example.
        version = self.spec.version
        for ver in [version.up_to(2), version.up_to(1), '']:
            path = os.path.join(self.prefix.bin, 'python{0}'.format(ver))
            if os.path.exists(path):
                return Executable(path)
        else:
            msg = 'Unable to locate {0} command in {1}'
            raise RuntimeError(msg.format(self.name, self.prefix.bin))

    def print_string(self, string):
        """Returns the appropriate print string depending on the
        version of Python.

        Examples:

        * Python 2

          .. code-block:: python

             >>> self.print_string('sys.prefix')
             'print sys.prefix'

        * Python 3

          .. code-block:: python

             >>> self.print_string('sys.prefix')
             'print(sys.prefix)'
        """
        if self.spec.satisfies('@:2'):
            return 'print {0}'.format(string)
        else:
            return 'print({0})'.format(string)

    def get_config_var(self, key):
        """Return the value of a single variable. Wrapper around
        ``distutils.sysconfig.get_config_var()``."""

        cmd = 'from distutils.sysconfig import get_config_var; '
        cmd += self.print_string("get_config_var('{0}')".format(key))

        return self.command('-c', cmd, output=str).strip()

    def get_config_h_filename(self):
        """Return the full path name of the configuration header.
        Wrapper around ``distutils.sysconfig.get_config_h_filename()``."""

        cmd = 'from distutils.sysconfig import get_config_h_filename; '
        cmd += self.print_string('get_config_h_filename()')

        return self.command('-c', cmd, output=str).strip()

    def get_makefile_filename(self):
        """Return the full path name of ``Makefile`` used to build Python.
        Wrapper around ``distutils.sysconfig.get_makefile_filename()``."""

        cmd = 'from distutils.sysconfig import get_makefile_filename; '
        cmd += self.print_string('get_makefile_filename()')

        return self.command('-c', cmd, output=str).strip()

    def get_python_inc(self):
        """Return the directory for either the general or platform-dependent C
        include files. Wrapper around ``distutils.sysconfig.get_python_inc()``.
        """

        cmd = 'from distutils.sysconfig import get_python_inc; '
        cmd += self.print_string('get_python_inc()')

        return self.command('-c', cmd, output=str).strip()

    def get_python_lib(self):
        """Return the directory for either the general or platform-dependent
        library installation. Wrapper around
        ``distutils.sysconfig.get_python_lib()``."""

        cmd = 'from distutils.sysconfig import get_python_lib; '
        cmd += self.print_string('get_python_lib()')

        return self.command('-c', cmd, output=str).strip()

    def get_sysconfigdata_name(self):
        """Return the full path name of the sysconfigdata file."""

        libdest = self.get_config_var('LIBDEST')

        filename = '_sysconfigdata.py'
        if self.spec.satisfies('@3.6:'):
            # Python 3.6.0 renamed the sys config file
            cmd = 'from sysconfig import _get_sysconfigdata_name; '
            cmd += self.print_string('_get_sysconfigdata_name()')
            filename = self.command('-c', cmd, output=str).strip()
            filename += '.py'

        return join_path(libdest, filename)

    @property
    def home(self):
        """Most of the time, ``PYTHONHOME`` is simply
        ``spec['python'].prefix``. However, if the user is using an
        externally installed python, it may be symlinked. For example,
        Homebrew installs python in ``/usr/local/Cellar/python/2.7.12_2``
        and symlinks it to ``/usr/local``. Users may not know the actual
        installation directory and add ``/usr/local`` to their
        ``packages.yaml`` unknowingly. Query the python executable to
        determine exactly where it is installed."""

        prefix = self.get_config_var('prefix')
        return Prefix(prefix)

    @property
    def libs(self):
        # Spack installs libraries into lib, except on openSUSE where it
        # installs them into lib64. If the user is using an externally
        # installed package, it may be in either lib or lib64, so we need
        # to ask Python where its LIBDIR is.
        libdir = self.get_config_var('LIBDIR')

        # The system Python installation on macOS and Homebrew installations
        # install libraries into a Frameworks directory
        frameworkprefix = self.get_config_var('PYTHONFRAMEWORKPREFIX')

        if '+shared' in self.spec:
            ldlibrary = self.get_config_var('LDLIBRARY')

            if os.path.exists(os.path.join(libdir, ldlibrary)):
                return LibraryList(os.path.join(libdir, ldlibrary))
            elif os.path.exists(os.path.join(frameworkprefix, ldlibrary)):
                return LibraryList(os.path.join(frameworkprefix, ldlibrary))
            else:
                msg = 'Unable to locate {0} libraries in {1}'
                raise RuntimeError(msg.format(ldlibrary, libdir))
        else:
            library = self.get_config_var('LIBRARY')

            if os.path.exists(os.path.join(libdir, library)):
                return LibraryList(os.path.join(libdir, library))
            elif os.path.exists(os.path.join(frameworkprefix, library)):
                return LibraryList(os.path.join(frameworkprefix, library))
            else:
                msg = 'Unable to locate {0} libraries in {1}'
                raise RuntimeError(msg.format(library, libdir))

    @property
    def headers(self):
        config_h = self.get_config_h_filename()

        if not os.path.exists(config_h):
            includepy = self.get_config_var('INCLUDEPY')
            msg = 'Unable to locate {0} headers in {1}'
            raise RuntimeError(msg.format(self.name, includepy))

        headers = HeaderList(config_h)
        headers.directories = [os.path.dirname(config_h)]
        return headers

    @property
    def python_lib_dir(self):
        return join_path('lib', 'python{0}'.format(self.version.up_to(2)))

    @property
    def python_include_dir(self):
        return join_path('include', 'python{0}'.format(self.version.up_to(2)))

    @property
    def site_packages_dir(self):
        return join_path(self.python_lib_dir, 'site-packages')

    @property
    def easy_install_file(self):
        return join_path(self.site_packages_dir, "easy-install.pth")

    def setup_dependent_build_environment(self, env, dependent_spec):
        """Set PYTHONPATH to include the site-packages directory for the
        extension and any other python extensions it depends on."""

        # If we set PYTHONHOME, we must also ensure that the corresponding
        # python is found in the build environment. This to prevent cases
        # where a system provided python is run against the standard libraries
        # of a Spack built python. See issue #7128
        env.set('PYTHONHOME', self.home)

        path = os.path.dirname(self.command.path)
        if not is_system_path(path):
            env.prepend_path('PATH', path)

        python_paths = []
        for d in dependent_spec.traverse(
                deptype=('build', 'run', 'test')):
            if d.package.extends(self.spec):
                python_paths.append(join_path(d.prefix,
                                              self.site_packages_dir))

        pythonpath = ':'.join(python_paths)
        env.set('PYTHONPATH', pythonpath)

    def setup_dependent_run_environment(self, env, dependent_spec):
        # For run time environment set only the path for
        # dependent_spec and prepend it to PYTHONPATH
        if dependent_spec.package.extends(self.spec):
            env.prepend_path('PYTHONPATH', join_path(
                dependent_spec.prefix, self.site_packages_dir))

    def setup_dependent_package(self, module, dependent_spec):
        """Called before python modules' install() methods.

        In most cases, extensions will only need to have one line::

        setup_py('install', '--prefix={0}'.format(prefix))"""

        module.python = self.command
        module.setup_py = Executable(
            self.command.path + ' setup.py --no-user-cfg')

        distutil_vars = self._load_distutil_vars()

        if distutil_vars:
            for key, value in distutil_vars.items():
                module.setup_py.add_default_env(key, value)

        # Add variables for lib/pythonX.Y and lib/pythonX.Y/site-packages dirs.
        module.python_lib_dir = join_path(dependent_spec.prefix,
                                          self.python_lib_dir)
        module.python_include_dir = join_path(dependent_spec.prefix,
                                              self.python_include_dir)
        module.site_packages_dir = join_path(dependent_spec.prefix,
                                             self.site_packages_dir)

        self.spec.home = self.home

        # Make the site packages directory for extensions
        if dependent_spec.package.is_extension:
            mkdirp(module.site_packages_dir)

    # ========================================================================
    # Handle specifics of activating and deactivating python modules.
    # ========================================================================

    def python_ignore(self, ext_pkg, args):
        """Add some ignore files to activate/deactivate args."""
        ignore_arg = args.get('ignore', lambda f: False)

        # Always ignore easy-install.pth, as it needs to be merged.
        patterns = [r'site-packages/easy-install\.pth$']

        # Ignore pieces of setuptools installed by other packages.
        # Must include directory name or it will remove all site*.py files.
        if ext_pkg.name != 'py-setuptools':
            patterns.extend([
                r'bin/easy_install[^/]*$',
                r'site-packages/setuptools[^/]*\.egg$',
                r'site-packages/setuptools\.pth$',
                r'site-packages/site[^/]*\.pyc?$',
                r'site-packages/__pycache__/site[^/]*\.pyc?$'
            ])
        if ext_pkg.name != 'py-pygments':
            patterns.append(r'bin/pygmentize$')
        if ext_pkg.name != 'py-numpy':
            patterns.append(r'bin/f2py[0-9.]*$')

        return match_predicate(ignore_arg, patterns)

    def write_easy_install_pth(self, exts, prefix=None):
        if not prefix:
            prefix = self.prefix

        paths = []
        unique_paths = set()

        for ext in sorted(exts.values()):
            easy_pth = join_path(ext.prefix, self.easy_install_file)

            if not os.path.isfile(easy_pth):
                continue

            with open(easy_pth) as f:
                for line in f:
                    line = line.rstrip()

                    # Skip lines matching these criteria
                    if not line:
                        continue
                    if re.search(r'^(import|#)', line):
                        continue
                    if (ext.name != 'py-setuptools' and
                            re.search(r'setuptools.*egg$', line)):
                        continue

                    if line not in unique_paths:
                        unique_paths.add(line)
                        paths.append(line)

        main_pth = join_path(prefix, self.easy_install_file)

        if not paths:
            if os.path.isfile(main_pth):
                os.remove(main_pth)

        else:
            with open(main_pth, 'w') as f:
                f.write("import sys; sys.__plen = len(sys.path)\n")
                for path in paths:
                    f.write("{0}\n".format(path))
                f.write("import sys; new=sys.path[sys.__plen:]; "
                        "del sys.path[sys.__plen:]; "
                        "p=getattr(sys,'__egginsert',0); "
                        "sys.path[p:p]=new; "
                        "sys.__egginsert = p+len(new)\n")

    def activate(self, ext_pkg, view, **args):
        ignore = self.python_ignore(ext_pkg, args)
        args.update(ignore=ignore)

        super(Python, self).activate(ext_pkg, view, **args)

        extensions_layout = view.extensions_layout
        exts = extensions_layout.extension_map(self.spec)
        exts[ext_pkg.name] = ext_pkg.spec

        self.write_easy_install_pth(exts, prefix=view.get_projection_for_spec(
            self.spec
        ))

    def deactivate(self, ext_pkg, view, **args):
        args.update(ignore=self.python_ignore(ext_pkg, args))

        super(Python, self).deactivate(ext_pkg, view, **args)

        extensions_layout = view.extensions_layout
        exts = extensions_layout.extension_map(self.spec)
        # Make deactivate idempotent
        if ext_pkg.name in exts:
            del exts[ext_pkg.name]
            self.write_easy_install_pth(exts,
                                        prefix=view.get_projection_for_spec(
                                            self.spec
                                        ))

    def add_files_to_view(self, view, merge_map):
        bin_dir = self.spec.prefix.bin
        for src, dst in merge_map.items():
            if not path_contains_subdirectory(src, bin_dir):
                view.link(src, dst)
            elif not os.path.islink(src):
                copy(src, dst)
                if 'script' in get_filetype(src):
                    filter_file(
                        self.spec.prefix,
                        os.path.abspath(
                            view.get_projection_for_spec(self.spec)
                        ),
                        dst,
                        backup=False
                    )
            else:
                orig_link_target = os.path.realpath(src)
                new_link_target = os.path.abspath(merge_map[orig_link_target])
                view.link(new_link_target, dst)

    def remove_files_from_view(self, view, merge_map):
        bin_dir = self.spec.prefix.bin
        for src, dst in merge_map.items():
            if not path_contains_subdirectory(src, bin_dir):
                view.remove_file(src, dst)
            else:
                os.remove(dst)
