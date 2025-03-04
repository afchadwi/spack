# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

"""This test does sanity checks on Spack's builtin package database."""
import os.path
import re

import pytest

import spack.fetch_strategy
import spack.paths
import spack.repo
import spack.util.executable as executable
# A few functions from this module are used to
# do sanity checks only on packagess modified by a PR
import spack.cmd.flake8 as flake8
import spack.util.crypto as crypto


def check_repo():
    """Get all packages in the builtin repo to make sure they work."""
    for name in spack.repo.all_package_names():
        spack.repo.get(name)


@pytest.mark.maybeslow
def test_get_all_packages():
    """Get all packages once and make sure that works."""
    check_repo()


def test_get_all_mock_packages():
    """Get the mock packages once each too."""
    db = spack.repo.RepoPath(spack.paths.mock_packages_path)
    with spack.repo.swap(db):
        check_repo()


def test_all_versions_are_lowercase():
    """Spack package names must be lowercase, and use `-` instead of `_`."""
    errors = []
    for name in spack.repo.all_package_names():
        if re.search(r'[_A-Z]', name):
            errors.append(name)

    assert len(errors) == 0


def test_all_virtual_packages_have_default_providers():
    """All virtual packages must have a default provider explicitly set."""
    defaults = spack.config.get('packages', scope='defaults')
    default_providers = defaults['all']['providers']
    providers = spack.repo.path.provider_index.providers
    default_providers_filename = \
        spack.config.config.scopes['defaults'].get_section_filename('packages')
    for provider in providers:
        assert provider in default_providers, \
            "all providers must have a default in %s" \
            % default_providers_filename


def test_package_version_consistency():
    """Make sure all versions on builtin packages produce a fetcher."""
    for name in spack.repo.all_package_names():
        pkg = spack.repo.get(name)
        spack.fetch_strategy.check_pkg_attributes(pkg)
        for version in pkg.versions:
            assert spack.fetch_strategy.for_package_version(pkg, version)


def test_no_fixme():
    """Packages should not contain any boilerplate such as
       FIXME or example.com."""
    errors = []
    fixme_regexes = [
        r'remove this boilerplate',
        r'FIXME: Put',
        r'FIXME: Add',
        r'example.com',
    ]
    for name in spack.repo.all_package_names():
        filename = spack.repo.path.filename_for_package_name(name)
        with open(filename, 'r') as package_file:
            for i, line in enumerate(package_file):
                pattern = next((r for r in fixme_regexes
                                if re.search(r, line)), None)
                if pattern:
                    errors.append(
                        "%s:%d: boilerplate needs to be removed: %s" %
                        (filename, i, line.strip())
                    )
            assert [] == errors


def test_docstring():
    """Ensure that every package has a docstring."""

    for name in spack.repo.all_package_names():
        pkg = spack.repo.get(name)
        assert pkg.__doc__


def test_all_packages_use_sha256_checksums():
    """Make sure that no packages use md5 checksums."""

    errors = []
    for name in spack.repo.all_package_names():
        pkg = spack.repo.path.get(name)

        # for now, don't enforce on packages that require manual downloads
        # TODO: eventually fix these, too.
        if pkg.manual_download:
            continue

        def invalid_sha256_digest(fetcher):
            if getattr(fetcher, "digest", None):
                h = crypto.hash_algo_for_digest(fetcher.digest)
                if h != "sha256":
                    return h

        for v, args in pkg.versions.items():
            fetcher = spack.fetch_strategy.for_package_version(pkg, v)
            bad_digest = invalid_sha256_digest(fetcher)
            if bad_digest:
                errors.append(
                    "All packages must use sha256 checksums. %s@%s uses %s." %
                    (name, v, bad_digest)
                )

        for _, resources in pkg.resources.items():
            for resource in resources:
                bad_digest = invalid_sha256_digest(resource.fetcher)
                if bad_digest:
                    errors.append(
                        "All packages must use sha256 checksums."
                        "Resource in %s uses %s." % (name, v, bad_digest)
                    )

    assert [] == errors


@pytest.mark.xfail
def test_api_for_build_and_run_environment():
    """Ensure that every package uses the correct API to set build and
    run environment, and not the old one.
    """
    failing = []
    for pkg in spack.repo.path.all_packages():
        add_to_list = (hasattr(pkg, 'setup_environment') or
                       hasattr(pkg, 'setup_dependent_environment'))
        if add_to_list:
            failing.append(pkg)

    msg = ('there are {0} packages using the old API to set build '
           'and run environment [{1}]')
    assert not failing, msg.format(
        len(failing), ','.join(x.name for x in failing)
    )


@pytest.mark.skipif(
    not executable.which('git'), reason='requires git to be installed'
)
def test_prs_update_old_api():
    """Ensures that every package modified in a PR doesn't contain
    deprecated calls to any method.
    """
    changed_package_files = [
        x for x in flake8.changed_files() if flake8.is_package(x)
    ]
    failing = []
    for file in changed_package_files:
        if 'builtin.mock' not in file:  # don't restrict packages for tests
            name = os.path.basename(os.path.dirname(file))
            pkg = spack.repo.get(name)

            failed = (hasattr(pkg, 'setup_environment') or
                      hasattr(pkg, 'setup_dependent_environment'))
            if failed:
                failing.append(name)

    msg = 'there are {0} packages still using old APIs in this PR [{1}]'
    assert not failing, msg.format(
        len(failing), ','.join(failing)
    )
