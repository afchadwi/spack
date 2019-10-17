# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
import pytest
from spack.main import SpackCommand
import spack.store

install = SpackCommand('install')
uninstall = SpackCommand('uninstall')
deprecate = SpackCommand('deprecate')
find = SpackCommand('find')
activate = SpackCommand('activate')


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

    new_spec = spack.spec.Spec('libdwarf@20130729^libelf@0.8.13').concretized()
    old_spec = spack.spec.Spec('libdwarf@20130207^libelf@0.8.10').concretized()

    all_installed = spack.store.db.query()

    deprecate('-y', '-d', 'libdwarf@20130207', 'libdwarf@20130729')

    non_deprecated = spack.store.db.query()
    all_available = spack.store.db.query(installed=any)
    deprecated = spack.store.db.query(installed=['deprecated'])

    assert all_available == all_installed
    assert sorted(all_available) == sorted(deprecated + non_deprecated)

    assert sorted(non_deprecated) == sorted(list(new_spec.traverse()))
    assert sorted(deprecated) == sorted(list(old_spec.traverse()))


def test_deprecate_fails_extensions(mock_packages, mock_archive, mock_fetch,
                                    install_mockery):
    install('extendee')
    install('extension1')
    activate('extension1')

    output = deprecate('-yi', 'extendee', 'libelf', fail_on_error=False)
    assert 'extension1' in output
    assert "Deactivate extensions before deprecating" in output

    output = deprecate('-yi', 'extension1', 'libelf', fail_on_error=False)
    assert 'extendee' in output
    assert 'is an active extension of' in output


def test_uninstall_deprecated(mock_packages, mock_archive, mock_fetch,
                              install_mockery):
    install('libelf@0.8.13')
    install('libelf@0.8.10')

    deprecate('-y', 'libelf@0.8.10', 'libelf@0.8.13')

    non_deprecated = spack.store.db.query()

    uninstall('-y', 'libelf@0.8.10')

    assert spack.store.db.query() == spack.store.db.query(installed=any)
    assert spack.store.db.query() == non_deprecated


def test_deprecate_deprecated(mock_packages, mock_archive, mock_fetch,
                              install_mockery):
    install('libelf@0.8.13')
    install('libelf@0.8.10')

    deprecate('-y', 'libelf@0.8.10', 'libelf@0.8.13')
    output = deprecate('-yi', 'libelf@0.8.10', 'libelf', fail_on_error=False)

    assert "already deprecated in favor of" in output


def test_concretize_deprecated(mock_packages, mock_archive, mock_fetch,
                               install_mockery):
    install('libelf@0.8.13')
    install('libelf@0.8.10')

    deprecate('-y', 'libelf@0.8.10', 'libelf@0.8.13')

    spec = spack.spec.Spec('libelf@0.8.10')
    with pytest.raises(spack.spec.SpecDeprecatedError):
        spec.concretize()
