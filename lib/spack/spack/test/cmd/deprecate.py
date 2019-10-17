# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
import pytest

from spack.main import SpackCommand
import spack.store

install = SpackCommand('install')
deprecate = SpackCommand('deprecate')
find = SpackCommand('find')


def test_deprecate(mock_packages, mock_archive, mock_fetch, install_mockery):
    install('libelf@0.8.13')
    install('libelf@0.8.10')

    all_installed = spack.store.db.query()
    assert len(all_installed) == 2

    deprecate('-y', 'libelf@0.8.10', 'libelf@0.8.13')

    non_deprecated = spack.store.db.query()
    all_available = spack.store.db.query(installed=any)
    assert all_available == all_installed
    assert non_deprecated == spack.store.db.query('libelf@0.8.13')


def test_deprecate_no_such_package(mock_packages, mock_archive, mock_fetch,
                                   install_mockery):
    output = deprecate('-y', 'libelf@0.8.10', 'libelf@0.8.13',
                       fail_on_error=False)
    assert 'libelf@0.8.10 does not match any installed package' in output

    install('libelf@0.8.10')

    output = deprecate('-y', 'libelf@0.8.10', 'libelf@0.8.13',
                       fail_on_error=False)
    assert 'libelf@0.8.13 does not match any installed package' in output


def test_deprecate_install(mock_packages, mock_archive, mock_fetch,
                           install_mockery):
    install('libelf@0.8.10')

    to_deprecate = spack.store.db.query()
    assert len(to_deprecate) == 1

    deprecate('-y', '-i', 'libelf@0.8.10', 'libelf@0.8.13')

    non_deprecated = spack.store.db.query()
    deprecated = spack.store.db.query(installed=['deprecated'])
    assert deprecated == to_deprecate
    assert len(non_deprecated) == 1
    assert non_deprecated[0].satisfies('libelf@0.8.13')


def test_deprecate_deps(mock_packages, mock_archive, mock_fetch,
                        install_mockery):
    install('libdwarf@20130729 ^libelf@0.8.13')
    install('libdwarf@20130207 ^libelf@0.8.10')

    all_installed = spack.store.db.query()

    deprecate('-y', '-d', 'libdwarf@20130207', 'libdwarf@20130729')

    non_deprecated = spack.store.db.query()
    all_available = spack.store.db.query(installed=any)
    deprecated = spack.store.db.query(installed=['deprecated'])

    assert all_available == all_installed
    assert sorted(all_available) == sorted(deprecated + non_deprecated)

    new_spec = spack.spec.Spec('libdwarf@20130729^libelf@0.8.13').concretized()
    assert sorted(non_deprecated) == sorted(list(new_spec.traverse()))

    old_spec = spack.spec.Spec('libdwarf@20130207^libelf@0.8.10').concretized()
    assert sorted(deprecated) == sorted(list(old_spec.traverse()))


