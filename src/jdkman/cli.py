from typing import Annotated, cast

import click
import typer

from .cli_dev import app as dev_app
from .cli_tools import app as tools_app
from .config import APP_VERSION, is_dev, FORCE_VERBOSE, init_dirs
from .console import update_state, log, out, table, GREEN_CHECK, ARGUMENT_SLUG
from .installer import install_jvm, uninstall_jvm, upgrade_jvm
from .registry import list_vendors, get_slugs, get_outdated, cleanup_cache, get_installed


app = typer.Typer(
    add_completion=False,
    suggest_commands=True,
    rich_markup_mode="rich",
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

    # managed_list()
    res = table("label", "version", "location")
    for slug, managed_info in get_installed().items():
        res.add_row(slug, managed_info["version"], managed_info["location"])
    out(res)


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

    # get_vendors()
    res = table("vendor")
    for vendor in list_vendors():
        res.add_row(vendor)
    out(res)


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
    List available JVM distributions.

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

    # get_slugs()
    res = table("distro")
    for slug in get_slugs(include_jre, include_feature, major_version):
        if not distro or slug.startswith(distro):
            res.add_row(slug)
    out(res)


@app.command()
def outdated():
    """
    List outdated JVM distributions.

    Examples:
    -  jdk outdated
    """
    log(f"outdated()")

    # outdated_jdk()
    outdated_list = get_outdated()
    if not outdated_list:
        out(f"{GREEN_CHECK} No outdated JVM distributions.")
        raise typer.Exit()
    res = table("distro", "installed", "latest")
    for slug, outdated_info in outdated_list.items():
        res.add_row(slug, outdated_info["installed"], outdated_info["latest"])
    out(res)


@app.command(no_args_is_help=True)
def install(distro: ARGUMENT_SLUG):
    """
    Install a JVM distribution.

    Examples:
    -  jdk install zulu-21
    -  jdk install temurin-jre-17
    """
    log(f"install()")
    log(f"  distro: {distro}")

    installed_dir = install_jvm(distro)
    out(f"Installed: {distro} {installed_dir} {GREEN_CHECK}")


@app.command(name="remove", hidden=True, no_args_is_help=True)
@app.command(name="rm", hidden=True, no_args_is_help=True)
@app.command(no_args_is_help=True)
def uninstall(distro: ARGUMENT_SLUG):
    """
    Remove an installed JVM distribution.  \\[aliases: remove, rm]

    Examples:
    -  jdk uninstall zulu-21
    -  jdk uninstall temurin-jre-17
    """
    log(f"uninstall()")
    log(f"  distro: {distro}")

    uninstalled_dir = uninstall_jvm(distro)
    out(f"Uninstalled: {distro} {uninstalled_dir} {GREEN_CHECK}")


@app.command(name="update", hidden=True, no_args_is_help=True)
@app.command(no_args_is_help=True)
def upgrade(distro: ARGUMENT_SLUG):
    """
    Upgrade an installed JVM distribution.  \\[aliases: update]

    Examples:
    -  jdk upgrade zulu-21
    -  jdk upgrade temurin-jre-17
    """
    log(f"upgrade()")
    log(f"  distro: {distro}")

    upgraded_dir = upgrade_jvm(distro)
    out(f"Upgraded: {distro} {upgraded_dir} {GREEN_CHECK}")


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
    out(f"Cache cleaned: {GREEN_CHECK}")


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

    out(f"jdkman [yellow]version: {APP_VERSION}[/yellow]")
    raise typer.Exit()


@app.command(name="help")
def show_help(
        context: typer.Context,
        command: Annotated[str | None, typer.Argument(
            help="Command to show help for."
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
            out(f"[red]Unknown command:[/red] '{command}'")
            raise typer.Exit(1)
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

