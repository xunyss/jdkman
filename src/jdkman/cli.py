import sys
from typing import Annotated

import click
import typer

from .autocomplete import autocomplete_installed, autocomplete_slugs
from .cli_about import app as about_app, show_version
from .cli_dev import app as dev_app
from .cli_env import app as env_app
from .cli_tools import app as tools_app
from .config import is_dev, FORCE_VERBOSE, init_dirs
from .console import (
    update_state, log, out, table,
    MARK_CHECK, MARK_WARNING,
    st_emp, st_hig, st_dim
)
from .installer import install_jvm, uninstall_jvm, upgrade_jvm, cleanup_cache
from .registry import get_installed, get_outdated, list_vendors, list_editions, get_slugs
from .utils import shorten


app = typer.Typer(
    add_completion=True,
    suggest_commands=False,
    pretty_exceptions_enable=is_dev()
)
app.add_typer(
    env_app,
)
app.add_typer(
    tools_app,
)
if is_dev():
    app.add_typer(
        dev_app,
        name="dev",
        help="for Development..",
        rich_help_panel="Tools",
    )
app.add_typer(
    about_app,
)


def intercept_args(value: bool):
    """
    --show-completion:
        Same output as `_JDK_COMPLETE=source_zsh jdk` (with a leading '\n')
    --install-completion:
        Creates "~/.zfunc/_jdk"
            with the output of `_JDK_COMPLETE=source_zsh jdk`
        Appends to "~/.zshrc"
            fpath+=~/.zfunc; autoload -Uz compinit; compinit
            zstyle ':completion:*' menu select
    """
    if is_dev():  # Can be tested with dev_completion.zsh
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


@app.command(name="list", rich_help_panel="Managements")
@app.command(hidden=True)
def ls():
    """
    List installed JVM distributions.  [dim]\\[aliases: ls][/dim]

    Examples:
    -  jdk list
    -  jdk ls
    """
    log(f"ls()")

    _outdated = get_outdated().keys()
    # get_installed()
    tab = table("distro", "version", "status", "location")
    for slug, installed_info in get_installed(sort=True).items():
        tab.add_row(
            slug,
            st_dim(installed_info["version"]),
            slug not in _outdated and f"{MARK_CHECK} {st_dim('latest')}"
                or f"{MARK_WARNING} {st_dim('outdated')}",
            st_dim(shorten(installed_info["location"]))
        )
    out(tab if tab.row_count > 0
        else f"{MARK_CHECK} No installed JVM distributions.")


@app.command(name="vd", hidden=True)
@app.command(rich_help_panel="Managements")
def vendors():
    """
    List all available JVM vendors.  [dim]\\[aliases: vd][/dim]

    Examples:
    -  jdk vendors
    -  jdk vd
    """
    log(f"vendors()")

    # list_vendors()
    tab = table("vendor")
    for vendor in list_vendors():
        tab.add_row(vendor)
    out(tab)


@app.command(name="ed", hidden=True)
@app.command(rich_help_panel="Managements")
def editions():
    """
    List all available JVM editions.  [dim]\\[aliases: ed][/dim]

    Examples:
    -  jdk editions
    -  jdk ed
    """
    log(f"editions()")

    # list_editions()
    tab = table("edition")
    for p in list_editions():
        tab.add_row(p)
    out(tab)


@app.command(name="rl", hidden=True)
@app.command(rich_help_panel="Managements")
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
    List available JVM distributions.  [dim]\\[aliases: rl][/dim]

    Examples:
    -  jdk remote
    -  jdk remote --all
    -  jdk remote --all zulu
    -  jdk remote --with-feat
    -  jdk remote --with-jre temu
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
                slug in _installed and f"{MARK_CHECK} {st_dim('installed')}" or None
            )
    out(tab)


@app.command(name="out", hidden=True)
@app.command(rich_help_panel="Managements")
def outdated():
    """
    List outdated JVM distributions.  [dim]\\[aliases: out][/dim]

    Examples:
    -  jdk outdated
    """
    log(f"outdated()")

    # get_outdated()
    tab = table("distro", "installed", "latest")
    for slug, outdated_info in get_outdated().items():
        tab.add_row(
            slug,
            st_dim(outdated_info["installed"]),
            st_dim(outdated_info["latest"])
        )
    out(tab if tab.row_count > 0
        else f"{MARK_CHECK} No outdated JVM distributions.")


@app.command(name="add", hidden=True, no_args_is_help=True)
@app.command(rich_help_panel="Managements", no_args_is_help=True)
def install(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution name to install. (e.g. zulu-21, temurin-17)",
            autocompletion=autocomplete_slugs
        )]
):
    """
    Install a JVM distribution.  [dim]\\[aliases: add][/dim]

    Examples:
    -  jdk install zulu-21
    -  jdk install temurin-jre-17
    """
    log(f"install()")
    log(f"  distro: {distro}")

    installed_dir = install_jvm(distro)
    out(f"{MARK_CHECK} Installed: {st_emp(distro)} {st_dim(installed_dir)}", highlight=False)


@app.command(name="del", hidden=True, no_args_is_help=True)
@app.command(rich_help_panel="Managements", no_args_is_help=True)
def uninstall(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution name to uninstall. (e.g. zulu-21, temurin-17)",
            autocompletion=autocomplete_installed
        )]
):
    """
    Remove an installed JVM distribution.  [dim]\\[aliases: del][/dim]

    Examples:
    -  jdk uninstall zulu-21
    -  jdk uninstall temurin-jre-17
    """
    log(f"uninstall()")
    log(f"  distro: {distro}")

    uninstalled_dir = uninstall_jvm(distro)
    out(f"{MARK_CHECK} Uninstalled: {st_emp(distro)} {st_dim(uninstalled_dir)}", highlight=False)


@app.command(name="upd", hidden=True, no_args_is_help=True)
@app.command(rich_help_panel="Managements", no_args_is_help=True)
def upgrade(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution name to upgrade. (e.g. zulu-21, temurin-17)",
            autocompletion=autocomplete_installed
        )]
):
    """
    Upgrade an installed JVM distribution.  [dim]\\[aliases: upd][/dim]

    Examples:
    -  jdk upgrade zulu-21
    -  jdk upgrade temurin-jre-17
    """
    log(f"upgrade()")
    log(f"  distro: {distro}")

    upgraded_dir = upgrade_jvm(distro)
    out(f"{MARK_CHECK} Upgraded: {st_emp(distro)} {st_dim(upgraded_dir)}", highlight=False)


@app.command(name="cl", hidden=True)
@app.command(rich_help_panel="Managements")
def cleanup():
    """
    Remove application cache data.  [dim]\\[aliases: cl][/dim]

    Examples:
    -  jdk cleanup
    """
    log(f"cleanup()")

    cleanup_cache()
    out(f"{MARK_CHECK} Cache cleaned.")


@app.callback(
    epilog=f"For more information:\n\nvisit: {st_hig('https://github.com/xunyss/jdkman')}",
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
    A command-line tool for installing and managing JVM distributions, and switching Java environments.

    Managements Examples:
    -  jdk remote zulu        Search available JVM distributions
    -  jdk install zulu-21    Install a JVM distribution
    -  jdk list               List installed JVM distributions
    -  jdk outdated           List outdated JVM distributions
    -  jdk upgrade zulu-21    Upgrade an installed JVM distribution
    -  jdk uninstall zulu-21  Remove an installed JVM distribution

    Environments Examples:
    -  eval "$(jdk activate zsh)"  Enable auto Java environment switching on directory change
    -  jdk alias 21 zulu-21        Create alias '21' pointing to zulu-21
    -  jdk aliases                 List all aliases
    -  jdk use 21                  Set Java environment for current directory
    -  jdk use --global zulu-25    Set global fallback Java environment
    -  jdk unuse                   Clear Java environment for current directory
    -  jdk unalias 21              Remove alias '21'
    """
    log(f"main()")
    log(f"  context.args: {context.args}")
    log(f"  context.command: '{context.command.name}'")
    log(f"  context.command_path: '{context.command_path}'")
    log(f"  context.invoked_subcommand: '{context.invoked_subcommand}'")
    log(f"  _verbose: {_verbose}")
    log(f"  _version: {_version}")

    init_dirs()

