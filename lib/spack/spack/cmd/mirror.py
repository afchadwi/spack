# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import sys

import argparse
import llnl.util.tty as tty
from llnl.util.tty.colify import colify

import spack.cmd
import spack.cmd.common.arguments as arguments
import spack.concretize
import spack.config
import spack.environment as ev
import spack.mirror
import spack.repo
import spack.util.url as url_util
import spack.util.web as web_util

from spack.spec import Spec
from spack.error import SpackError
from spack.util.spack_yaml import syaml_dict

description = "manage mirrors (source and binary)"
section = "config"
level = "long"


def setup_parser(subparser):
    arguments.add_common_arguments(subparser, ['no_checksum'])

    sp = subparser.add_subparsers(
        metavar='SUBCOMMAND', dest='mirror_command')

    # Create
    create_parser = sp.add_parser('create', help=mirror_create.__doc__)
    create_parser.add_argument('-d', '--directory', default=None,
                               help="directory in which to create mirror")
    create_parser.add_argument(
        'specs', nargs=argparse.REMAINDER,
        help="specs of packages to put in mirror")
    create_parser.add_argument(
        '-f', '--file', help="file with specs of packages to put in mirror")
    create_parser.add_argument(
        '-D', '--dependencies', action='store_true',
        help="also fetch all dependencies")
    create_parser.add_argument(
        '-n', '--versions-per-spec', type=int,
        default=1,
        help="the number of versions to fetch for each spec")

    # used to construct scope arguments below
    scopes = spack.config.scopes()
    scopes_metavar = spack.config.scopes_metavar

    # Add
    add_parser = sp.add_parser('add', help=mirror_add.__doc__)
    add_parser.add_argument('name', help="mnemonic name for mirror")
    add_parser.add_argument(
        'url', help="url of mirror directory from 'spack mirror create'")
    add_parser.add_argument(
        '--scope', choices=scopes, metavar=scopes_metavar,
        default=spack.config.default_modify_scope(),
        help="configuration scope to modify")

    # Remove
    remove_parser = sp.add_parser('remove', aliases=['rm'],
                                  help=mirror_remove.__doc__)
    remove_parser.add_argument('name')
    remove_parser.add_argument(
        '--scope', choices=scopes, metavar=scopes_metavar,
        default=spack.config.default_modify_scope(),
        help="configuration scope to modify")

    # Set-Url
    set_url_parser = sp.add_parser('set-url', help=mirror_set_url.__doc__)
    set_url_parser.add_argument('name', help="mnemonic name for mirror")
    set_url_parser.add_argument(
        'url', help="url of mirror directory from 'spack mirror create'")
    set_url_parser.add_argument(
        '--push', action='store_true',
        help="set only the URL used for uploading new packages")
    set_url_parser.add_argument(
        '--scope', choices=scopes, metavar=scopes_metavar,
        default=spack.config.default_modify_scope(),
        help="configuration scope to modify")

    # List
    list_parser = sp.add_parser('list', help=mirror_list.__doc__)
    list_parser.add_argument(
        '--scope', choices=scopes, metavar=scopes_metavar,
        default=spack.config.default_list_scope(),
        help="configuration scope to read from")


def mirror_add(args):
    """Add a mirror to Spack."""
    url = url_util.format(args.url)

    mirrors = spack.config.get('mirrors', scope=args.scope)
    if not mirrors:
        mirrors = syaml_dict()

    if args.name in mirrors:
        tty.die("Mirror with name %s already exists." % args.name)

    items = [(n, u) for n, u in mirrors.items()]
    items.insert(0, (args.name, url))
    mirrors = syaml_dict(items)
    spack.config.set('mirrors', mirrors, scope=args.scope)


def mirror_remove(args):
    """Remove a mirror by name."""
    name = args.name

    mirrors = spack.config.get('mirrors', scope=args.scope)
    if not mirrors:
        mirrors = syaml_dict()

    if name not in mirrors:
        tty.die("No mirror with name %s" % name)

    old_value = mirrors.pop(name)
    spack.config.set('mirrors', mirrors, scope=args.scope)

    debug_msg_url = "url %s"
    debug_msg = ["Removed mirror %s with"]
    values = [name]

    try:
        fetch_value = old_value['fetch']
        push_value = old_value['push']

        debug_msg.extend(("fetch", debug_msg_url, "and push", debug_msg_url))
        values.extend((fetch_value, push_value))
    except TypeError:
        debug_msg.append(debug_msg_url)
        values.append(old_value)

    tty.debug(" ".join(debug_msg) % tuple(values))
    tty.msg("Removed mirror %s." % name)


def mirror_set_url(args):
    """Change the URL of a mirror."""
    url = url_util.format(args.url)

    mirrors = spack.config.get('mirrors', scope=args.scope)
    if not mirrors:
        mirrors = syaml_dict()

    if args.name not in mirrors:
        tty.die("No mirror found with name %s." % args.name)

    entry = mirrors[args.name]

    try:
        fetch_url = entry['fetch']
        push_url = entry['push']
    except TypeError:
        fetch_url, push_url = entry, entry

    changes_made = False

    if args.push:
        changes_made = changes_made or push_url != url
        push_url = url
    else:
        changes_made = (
            changes_made or fetch_url != push_url or push_url != url)

        fetch_url, push_url = url, url

    items = [
        (
            (n, u)
            if n != args.name else (
                (n, {"fetch": fetch_url, "push": push_url})
                if fetch_url != push_url else (n, fetch_url)
            )
        )
        for n, u in mirrors.items()
    ]

    mirrors = syaml_dict(items)
    spack.config.set('mirrors', mirrors, scope=args.scope)

    if changes_made:
        tty.msg(
            "Changed%s url for mirror %s." %
            ((" (push)" if args.push else ""), args.name))
    else:
        tty.msg("Url already set for mirror %s." % args.name)


def mirror_list(args):
    """Print out available mirrors to the console."""

    mirrors = spack.mirror.MirrorCollection(scope=args.scope)
    if not mirrors:
        tty.msg("No mirrors configured.")
        return

    mirrors.display()


def _read_specs_from_file(filename):
    specs = []
    with open(filename, "r") as stream:
        for i, string in enumerate(stream):
            try:
                s = Spec(string)
                s.package
                specs.append(s)
            except SpackError as e:
                tty.debug(e)
                tty.die("Parse error in %s, line %d:" % (filename, i + 1),
                        ">>> " + string, str(e))
    return specs


def mirror_create(args):
    """Create a directory to be used as a spack mirror, and fill it with
       package archives."""
    # try to parse specs from the command line first.
    with spack.concretize.disable_compiler_existence_check():
        specs = spack.cmd.parse_specs(args.specs, concretize=True)

        # If there is a file, parse each line as a spec and add it to the list.
        if args.file:
            if specs:
                tty.die("Cannot pass specs on the command line with --file.")
            specs = _read_specs_from_file(args.file)

        # If nothing is passed, use environment or all if no active env
        if not specs:
            env = ev.get_env(args, 'mirror')
            if env:
                specs = env.specs_by_hash.values()
            else:
                specs = [Spec(n) for n in spack.repo.all_package_names()]
                specs.sort(key=lambda s: s.format("{name}{@version}").lower())

        # If the user asked for dependencies, traverse spec DAG get them.
        if args.dependencies:
            new_specs = set()
            for spec in specs:
                spec.concretize()
                for s in spec.traverse():
                    new_specs.add(s)
            specs = list(new_specs)

        # Skip external specs, as they are already installed
        external_specs = [s for s in specs if s.external]
        specs = [s for s in specs if not s.external]

        for spec in external_specs:
            msg = 'Skipping {0} as it is an external spec.'
            tty.msg(msg.format(spec.cshort_spec))

        mirror = spack.mirror.Mirror(
            args.directory or spack.config.get('config:source_cache'))

        directory = url_util.format(mirror.push_url)

        # Make sure nothing is in the way.
        existed = web_util.url_exists(directory)

        # Actually do the work to create the mirror
        present, mirrored, error = spack.mirror.create(
            directory, specs, num_versions=args.versions_per_spec)
        p, m, e = len(present), len(mirrored), len(error)

        verb = "updated" if existed else "created"
        tty.msg(
            "Successfully %s mirror in %s" % (verb, directory),
            "Archive stats:",
            "  %-4d already present"  % p,
            "  %-4d added"            % m,
            "  %-4d failed to fetch." % e)
        if error:
            tty.error("Failed downloads:")
            colify(s.cformat("{name}{@version}") for s in error)
            sys.exit(1)


def mirror(parser, args):
    action = {'create': mirror_create,
              'add': mirror_add,
              'remove': mirror_remove,
              'rm': mirror_remove,
              'set-url': mirror_set_url,
              'list': mirror_list}

    if args.no_checksum:
        spack.config.set('config:checksum', False, scope='command_line')

    action[args.mirror_command](args)
