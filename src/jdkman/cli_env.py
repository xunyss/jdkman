from pathlib import Path
from typing import Annotated

import typer
from rich.pretty import pretty_repr

from .autocomplete import autocomplete_installed, autocomplete_aliases, autocomplete_managed
from .config import is_dev
from .console import log, out, MARK_CHECK, MARK_INVALID, st_emp, st_div, st_dim
from .environments import set_env_file, unset_env_file, set_env_alias, unset_env_alias
from .registry import get_aliases


app = typer.Typer()


@app.command(rich_help_panel="Environments", no_args_is_help=True)
def activate(
        shell: Annotated[str, typer.Argument(
            metavar="<SHELL>",
            help="Shell type. (e.g. zsh, bash)"
        )],
        _dev_mode: Annotated[bool, typer.Option(
            "--dev", "-d", hidden=True
        )] = False,
):
    """
    Print shell integration script for auto JVM-env switching.

    Add to your shell profile (~/.zshrc or ~/.bashrc):
    -  eval "$(jdk activate zsh)"
    -  eval "$(jdk activate bash)"
    """
    log(f"activate()")
    log(f"  shell: {shell}")
    log(f"  _dev_mode: {_dev_mode}")

    script = f"{shell}_dev" if _dev_mode and is_dev() else shell
    script = Path(__file__).parent / f"resources/activate_script/{script}"
    if not script.is_file():
        out(f"{MARK_INVALID} Unsupported shell: {st_div(shell)}")
        raise typer.Exit(code=-1)

    print(script.read_text(), end="")


@app.command(rich_help_panel="Environments", no_args_is_help=True)
def deactivate(
        shell: Annotated[str, typer.Argument(
            metavar="<SHELL>",
            help="Shell type. (e.g. zsh, bash)"
        )],
):
    """
    Print shell script to remove auto JVM-env switching.

    Handled automatically by the jdk() shell function:
    -  jdk deactivate
    """
    log(f"deactivate()")
    log(f"  shell: {shell}")

    script = Path(__file__).parent / f"resources/activate_script/{shell}_deactivate"
    if not script.is_file():
        out(f"{MARK_INVALID} Unsupported shell: {st_div(shell)}")
        raise typer.Exit(code=-1)

    print(script.read_text(), end="")


@app.command(rich_help_panel="Environments", no_args_is_help=True)
def use(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO|ALIAS>",
            help="JVM distribution name or alias.",
            autocompletion=autocomplete_managed
        )],
        set_global: Annotated[bool, typer.Option(
            "--global", "-g",
            help="Set as global fallback (~/.java-version) instead of current directory."
        )] = False,
):
    """
    Set Java version for current directory or globally.

    Creates a .java-version file in the current directory (default),
    or ~/.config/jdkman/.java-version.global with --global.
    Examples:
    -  jdk use zulu-17
    -  jdk use 11
    -  jdk use zulu-21 --global
    """
    log(f"use()")
    log(f"  distro: {distro}")
    log(f"  set_global: {set_global}")

    env_file = set_env_file(distro, set_global)
    out(f"{MARK_CHECK} {'Global' if set_global else 'Local'} Java environment: {st_emp(distro)} {st_dim(env_file)}", highlight=False)


@app.command(rich_help_panel="Environments")
def unuse(
        set_global: Annotated[bool, typer.Option(
            "--global", "-g",
            help="Clear global Java version (~/.config/jdkman/.java-version.global)."
        )] = False,
):
    """
    Clear Java version for current directory or globally.

    Empties the .java-version file in the current directory (default),
    or ~/.config/jdkman/.java-version.global with --global.
    Examples:
    -  jdk unuse
    -  jdk unuse --global
    """
    log(f"unuse()")
    log(f"  set_global: {set_global}")

    env_file = unset_env_file(set_global)
    out(f"{MARK_CHECK} Cleared {'global' if set_global else 'local'} Java environment: {st_dim(env_file)}",  highlight=False)


@app.command(rich_help_panel="Environments")
def aliases():
    """
    List all JVM distribution aliases.

    Examples:
    -  jdk aliases
    """
    log(f"aliases()")
    log(f"  aliases: {pretty_repr(get_aliases())}")


@app.command(name="alias", rich_help_panel="Environments", no_args_is_help=True)
def set_alias(
        alias: Annotated[str, typer.Argument(
            metavar="<ALIAS>",
            help="Alias name to create.",
        )],
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="Installed JVM distribution name to map to.",
            autocompletion=autocomplete_installed
        )],
):
    """
    Create an alias for an installed JVM distribution.

    Examples:
    -  jdk alias 21 zulu-21
    -  jdk alias lts temurin-21
    """
    log(f"set_alias()")
    log(f"  alias: {alias}")
    log(f"  distro: {distro}")

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

