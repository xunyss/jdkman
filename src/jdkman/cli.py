import sys
from typing import Annotated, cast

import click
import typer

from .autocomplete import autocomplete_installed, autocomplete_slugs, autocomplete_commands
from .cli_dev import app as dev_app
from .cli_tools import app as tools_app
from .config import APP_VERSION, is_dev, FORCE_VERBOSE, init_dirs
from .console import (
    update_state, log, out, table,
    GREEN_CHECK, ORANGE_WARNING, RED_WARNING,
    st_emp, st_div, st_nor
)
from .installer import install_jvm, uninstall_jvm, upgrade_jvm
from .registry import list_vendors, get_slugs, get_outdated, cleanup_cache, get_installed, list_editions


app = typer.Typer(
    add_completion=True,
    suggest_commands=False,
    pretty_exceptions_enable=is_dev()
)
app.add_typer(
    tools_app
)
if is_dev():
    app.add_typer(
        dev_app,
        name="dev",
        help="for Development..",
        rich_help_panel="Tools"
    )


def intercept_args(value: bool):
    if is_dev():
        completion_opts = {"--install-completion"}
    else:
        completion_opts = {"--install-completion", "--show-completion"}

    for arg in sys.argv:
        if arg in completion_opts:
            raise click.NoSuchOption(arg)


def callback_verbose(value: bool):
    update_state("verbose", value)

    log(f"callback_verbose()")
    log(f"  verbose: {value}")


@app.command(name="list")
@app.command(hidden=True)
def ls():
    """
    List installed JVM distributions.  \\[aliases: ls]

    Examples:
    -  jdk list
    -  jdk ls
    """
    log(f"ls()")

    _outdated = get_outdated().keys()
    # get_installed()
    tab = table("distro", "version", "status", "location")
    for slug, managed_info in get_installed(sort=True).items():
        tab.add_row(
            slug,
            st_nor(managed_info["version"]),
            slug not in _outdated and f"{GREEN_CHECK} {st_nor('latest')}" or f"{ORANGE_WARNING} {st_nor('outdated')}",
            st_nor(managed_info["location"])
        )
    out(tab if tab.row_count > 0
        else f"{GREEN_CHECK} No installed JVM distributions.")


@app.command(name="vendor", hidden=True)
@app.command()
def vendors():
    """
    List all available JVM vendors.  \\[aliases: vendor]

    Examples:
    -  jdk vendors
    -  jdk vendor
    """
    log(f"vendors()")

    # list_vendors()
    tab = table("vendor")
    for vendor in list_vendors():
        tab.add_row(vendor)
    out(tab)


@app.command(name="edition", hidden=True)
@app.command()
def editions():
    """
    List all available JVM editions.  \\[aliases: edition]

    Examples:
    -  jdk editions
    -  jdk edition
    """
    log(f"editions()")

    # list_editions()
    tab = table("edition")
    for p in list_editions():
        tab.add_row(p)
    out(tab)


@app.command(name="search", hidden=True)
@app.command()
def remote(
        distro: Annotated[str, typer.Argument(
            help="Filter by distro. (e.g. zulu-21, temurin, ora)"
        )] = None,
        show_all: Annotated[bool, typer.Option(
            "--all/--no-all", "-a",
            help="Include all builds. (feature and JRE)"
        )] = False,
        include_feature: Annotated[bool, typer.Option(
            "--with-feat/--no-feat", "-f/-F",
            help="Include feature builds."
        )] = False,
        include_jre: Annotated[bool, typer.Option(
            "--with-jre/--no-jre", "-r/-R",
            help="Include JRE builds."
        )] = False,
        major_version: Annotated[str | None, typer.Option(
            "--version", "-v", metavar="<MAJOR_VERSION>",
            help="Filter by major version. (e.g. 17, 21)"
        )] = None,
):
    """
    List available JVM distributions.  \\[aliases: search]

    Examples:
    -  jdk remote
    -  jdk remote --all
    -  jdk remote --all zulu
    -  jdk remote --with-feat
    -  jdk remote --with-jre
    -  jdk remote --version 17
    """
    log(f"remote()")
    log(f"  distro: {distro}")
    log(f"  show_all: {show_all}")
    log(f"  include_feature: {include_feature}")
    log(f"  include_jre: {include_jre}")
    log(f"  major_version: {major_version}")

    if show_all:
        include_jre = True
        include_feature = True

    _installed = get_installed().keys()
    # get_slugs()
    tab = table("distro", "installed")
    for slug in get_slugs(include_jre, include_feature, major_version):
        if not distro or slug.startswith(distro):
            tab.add_row(
                slug,
                slug in _installed and f"{GREEN_CHECK} {st_nor('installed')}" or None
            )
    out(tab)


@app.command(name="old", hidden=True)
@app.command()
def outdated():
    """
    List outdated JVM distributions.  \\[aliases: old]

    Examples:
    -  jdk outdated
    """
    log(f"outdated()")

    # get_outdated()
    tab = table("distro", "installed", "latest")
    for slug, outdated_info in get_outdated().items():
        tab.add_row(
            slug,
            st_nor(outdated_info["installed"]),
            st_nor(outdated_info["latest"])
        )
    out(tab if tab.row_count > 0
        else f"{GREEN_CHECK} No outdated JVM distributions.")


@app.command(name="setup", hidden=True, no_args_is_help=True)
@app.command(name="add", hidden=True, no_args_is_help=True)
@app.command(no_args_is_help=True)
def install(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution name to install. (e.g. zulu-21, temurin-17)",
            autocompletion=autocomplete_slugs
        )]
):
    """
    Install a JVM distribution.  \\[aliases: setup, add]

    Examples:
    -  jdk install zulu-21
    -  jdk install temurin-jre-17
    """
    log(f"install()")
    log(f"  distro: {distro}")

    installed_dir = install_jvm(distro)
    out(f"{GREEN_CHECK} Installed: {st_emp(distro)} {st_nor(installed_dir)}", highlight=False)


@app.command(name="remove", hidden=True, no_args_is_help=True)
@app.command(name="rm", hidden=True, no_args_is_help=True)
@app.command(no_args_is_help=True)
def uninstall(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution name to uninstall. (e.g. zulu-21, temurin-17)",
            autocompletion=autocomplete_installed
        )]
):
    """
    Remove an installed JVM distribution.  \\[aliases: remove, rm]

    Examples:
    -  jdk uninstall zulu-21
    -  jdk uninstall temurin-jre-17
    """
    log(f"uninstall()")
    log(f"  distro: {distro}")

    uninstalled_dir = uninstall_jvm(distro)
    out(f"{GREEN_CHECK} Uninstalled: {st_emp(distro)} {st_nor(uninstalled_dir)}", highlight=False)


@app.command(name="update", hidden=True, no_args_is_help=True)
@app.command(no_args_is_help=True)
def upgrade(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution name to upgrade. (e.g. zulu-21, temurin-17)",
            autocompletion=autocomplete_installed
        )]
):
    """
    Upgrade an installed JVM distribution.  \\[aliases: update]

    Examples:
    -  jdk upgrade zulu-21
    -  jdk upgrade temurin-jre-17
    """
    log(f"upgrade()")
    log(f"  distro: {distro}")

    upgraded_dir = upgrade_jvm(distro)
    out(f"{GREEN_CHECK} Upgraded: {st_emp(distro)} {st_nor(upgraded_dir)}", highlight=False)


@app.command(name="clean", hidden=True)
@app.command(name="clear", hidden=True)
@app.command()
def cleanup():
    """
    Remove application cache data.  \\[aliases: clean, clear]

    Examples:
    -  jdk cleanup
    """
    log(f"cleanup()")

    cleanup_cache()
    out(f"{GREEN_CHECK} Cache cleaned.")


@app.command(name="version", add_help_option=False)
def show_version(
        callback: Annotated[bool, typer.Option(
            hidden=True
        )] = False
):
    """
    Show the version and exit.
    """
    log(f"version()")
    log(f"  callback: {callback}")

    out(f"[bold]jdkman[/bold] {st_div(APP_VERSION)}")
    raise typer.Exit()


@app.command(name="help")
def show_help(
        context: typer.Context,
        command: Annotated[str | None, typer.Argument(
            help="Command to show help for.",
            autocompletion=autocomplete_commands
        )] = None
):
    """
    Show help for a command.

    Examples:
    -  jdk help
    -  jdk help list
    -  jdk help install
    """
    if command:
        ctx = context.parent
        cmd = cast(click.Group, ctx.command).commands.get(command)
        if cmd is None:
            out(f"{RED_WARNING} Unknown command: {st_div(command)}")
            raise typer.Exit(code=1)
        with click.Context(cmd, info_name=command, parent=ctx) as sub_ctx:
            cmd.get_help(sub_ctx)
    else:
        context.parent.get_help()


@app.callback(
    epilog="── Made by [blue]xunyss[/blue] :thumbs_up: ──",
    invoke_without_command=True,
    no_args_is_help=True,
)
def main(
        context: typer.Context,
        _interceptor: Annotated[bool, typer.Option(
            hidden=True, expose_value=False,
            callback=intercept_args, is_eager=True,
        )] = False,
        _verbose: Annotated[bool, typer.Option(
            "--verbose", "-V",
            help="Show verbose output.",
            callback=callback_verbose,
            is_eager=True,
        )] = FORCE_VERBOSE,
        _version: Annotated[bool | None, typer.Option(
            "--version", "-v",
            help="Show the version and exit.",
            callback=lambda x: show_version(x) if x else None
        )] = None,
):
    """
    A command-line tool for installing and managing OpenJDK distributions.

    Examples:
    -  jdk remote zulu        Search available JVM distributions
    -  jdk install zulu-21    Install a JVM distribution
    -  jdk list               List installed JVM distributions
    -  jdk outdated           List outdated JVM distributions
    -  jdk upgrade zulu-21    Upgrade an installed JVM distribution
    -  jdk uninstall zulu-21  Remove an installed JVM distribution
    """
    log(f"main()")
    log(f"  context.args: {context.args}")
    log(f"  context.command: '{context.command.name}'")
    log(f"  context.command_path: '{context.command_path}'")
    log(f"  context.invoked_subcommand: '{context.invoked_subcommand}'")
    log(f"  _verbose: {_verbose}")
    log(f"  _version: {_version}")

    init_dirs()

