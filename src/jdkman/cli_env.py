from typing import Annotated

import typer

from .autocomplete import autocomplete_installed, autocomplete_aliases, autocomplete_managed
from .config import is_dev
from .console import log, out, table, MARK_CHECK, MARK_WARNING, MARK_INVALID, st_emp, st_hig, st_div, st_dim, st_not
from .environments import (
    print_activate_script, print_deactivate_script,
    set_env_tag, unset_env_tag, get_env_aliases,
    set_env_alias, unset_env_alias, get_envs,
)
from .utils import shorten


app = typer.Typer()


@app.command(rich_help_panel="Environments", no_args_is_help=True)
def activate(
        shell: Annotated[str, typer.Argument(
            metavar="<SHELL>",
            help="Shell type. (e.g. zsh, bash, fish)"
        )],
        dev_mode: Annotated[bool, typer.Option(
            "--dev", "-d", hidden=True
        )] = False,
):
    """
    Print shell integration script for auto Java environment switching.

    Add to your shell profile (~/.zshrc or ~/.bashrc):
    -  eval "$(jdk activate zsh)"
    -  eval "$(jdk activate bash)"
    -  jdk activate fish | source
    """
    log(f"activate()")
    log(f"  shell: {shell}")
    log(f"  dev_mode: {dev_mode}")

    print_activate_script(shell, dev_mode and is_dev())


@app.command(rich_help_panel="Environments", no_args_is_help=True)
def deactivate(
        shell: Annotated[str, typer.Argument(
            metavar="<SHELL>",
            help="Shell type. (e.g. zsh, bash, fish)"
        )],
):
    """
    Print shell script to remove auto Java environment switching.

    Run with eval to apply to the current shell session:
    -  eval "$(jdk deactivate zsh)"
    -  eval "$(jdk deactivate bash)"
    -  jdk deactivate fish | source
    """
    log(f"deactivate()")
    log(f"  shell: {shell}")

    print_deactivate_script(shell)


@app.command(rich_help_panel="Environments")
def env():
    """
    Show current Java environment status.

    Displays the active Java environment for the current directory,
    along with local .java-version and global fallback settings.
    Examples:
    -  jdk env
    """
    log(f"env()")

    envs = get_envs(validate=True)
    active_scope = "local" if envs["local"]["version"] else "global" if envs["global"]["version"] else None
    if not active_scope and not envs["local"]["tag"] and not envs["global"]["tag"]:
        out(f"{MARK_CHECK} No active Java environment.")
        raise typer.Exit()

    tab = table("status", "scope", "tag", "distro", "version", "source")
    for scope, env_info in envs.items():
        is_active = scope == active_scope and env_info["version"]
        tag, slug, version, source = env_info["tag"], env_info["slug"], env_info["version"], shorten(env_info["source"])
        tab.add_row(
            is_active and f"{MARK_CHECK} {st_dim('active')}" or None,
            is_active and st_hig(scope) or st_dim(scope),
            is_active and st_emp(tag) or st_dim(tag) if tag else None,
            is_active and slug or st_dim(slug) if version else st_not(slug) if slug else None,
            version and st_dim(version) or None,
            source and st_dim(source) or None,
        )
    out(tab)


@app.command(name="set", hidden=True, no_args_is_help=True)
@app.command(rich_help_panel="Environments", no_args_is_help=True)
def use(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO|ALIAS>",
            help="JVM distribution name or alias.",
            autocompletion=autocomplete_managed
        )],
        set_global: Annotated[bool, typer.Option(
            "--global", "-g",
            help="Set as global fallback instead of current directory."
        )] = False,
):
    """
    Set Java environment for current directory or globally.  [dim]\\[aliases: set][/dim]

    Creates a .java-version file in the current directory (default),
    or ~/.config/jdkman/.java-version with --global.
    Examples:
    -  jdk use zulu-17
    -  jdk use 11
    -  jdk use zulu-21 --global
    """
    log(f"use()")
    log(f"  distro: {distro}")
    log(f"  set_global: {set_global}")

    env_file = set_env_tag(distro, set_global)
    out(f"{MARK_CHECK} {'Global' if set_global else 'Local'} "
        f"Java environment: {st_emp(distro)} {st_dim(env_file)}", highlight=False)


@app.command(name="uns", hidden=True)
@app.command(rich_help_panel="Environments")
def unuse(
        set_global: Annotated[bool, typer.Option(
            "--global", "-g",
            help="Clear global Java environment."
        )] = False,
):
    """
    Clear Java environment for current directory or globally.  [dim]\\[aliases: uns][/dim]

    Empties the .java-version file in the current directory (default),
    or ~/.config/jdkman/.java-version with --global.
    Examples:
    -  jdk unuse
    -  jdk unuse --global
    """
    log(f"unuse()")
    log(f"  set_global: {set_global}")

    env_file = unset_env_tag(set_global)
    out(f"{MARK_CHECK} Cleared {'global' if set_global else 'local'} "
        f"Java environment: {st_dim(env_file)}",  highlight=False)


@app.command(name="alias", rich_help_panel="Environments")
def set_alias(
        alias: Annotated[str, typer.Argument(
            help="Alias name to create.",
        )] = None,
        distro: Annotated[str, typer.Argument(
            help="Installed JVM distribution name to map to.",
            autocompletion=autocomplete_installed
        )] = None,
):
    """
    Create an alias for an installed JVM distribution or list all aliases.

    Examples:
    -  jdk alias 21 zulu-21
    -  jdk alias lts temurin-21
    -  jdk alias
    """
    log(f"set_alias()")
    log(f"  alias: {alias}")
    log(f"  distro: {distro}")

    if not alias:
        aliases()
        raise typer.Exit()
    if not distro:
        out(f"{MARK_INVALID} Missing Arguments: {st_div('[DISTRO]')}", highlight=False)
        raise typer.Exit(code=-1)

    set_env_alias(alias, distro)
    out(f"{MARK_CHECK} Alias: {st_emp(alias)} → {st_div(distro)}", highlight=False)


@app.command(name="unalias", rich_help_panel="Environments", no_args_is_help=True)
def unset_alias(
        alias: Annotated[str, typer.Argument(
            metavar="<ALIAS>",
            help="Alias name to remove.",
            autocompletion=autocomplete_aliases
        )],
):
    """
    Remove a JVM distribution alias.

    Examples:
    -  jdk unalias 21
    """
    log(f"unset_alias()")
    log(f"  alias: {alias}")

    unset_env_alias(alias)
    out(f"{MARK_CHECK} Unalias: {st_emp(alias)}", highlight=False)


@app.command(rich_help_panel="Environments")
def aliases():
    """
    List all JVM distribution aliases.  [dim]\\[aliases: alias][/dim]

    Examples:
    -  jdk aliases
    """
    log(f"aliases()")

    tab = table("alias", "distro", "version", "status")
    for item in get_env_aliases():
        alias, slug, version = item["alias"], item["slug"], item["version"]
        is_enabled = slug and version
        tab.add_row(
            alias,
            is_enabled and slug or st_not(slug),
            is_enabled and st_dim(version) or None,
            is_enabled and MARK_CHECK or f"{MARK_WARNING} {st_dim('disabled')}",
        )
    out(tab if tab.row_count > 0
        else f"{MARK_CHECK} No JVM distribution aliases.")

