from pathlib import Path
from typing import Annotated

import typer
from rich.pretty import pretty_repr

from .autocomplete import autocomplete_installed
from .console import out, log, MARK_CHECK, MARK_INVALID, st_emp, st_dim, st_div
from .registry import get_installed, read_managed, write_managed

app = typer.Typer()

_JAVA_VERSION_FILE = ".java-version"
_GLOBAL_JAVA_VERSION_FILE = Path.home() / ".java-version"


@app.command(name="activate", no_args_is_help=True)
def activate(
        shell: Annotated[str, typer.Argument(
            metavar="<SHELL>",
            help="Shell type. (e.g. zsh, bash)"
        )]
):
    """
    Print shell integration script for auto JDK switching.

    Add to your shell profile (~/.zshrc or ~/.bashrc):
    -  eval "$(jdk env activate zsh)"
    -  eval "$(jdk env activate bash)"
    """
    log(f"activate()")
    log(f"  shell: {shell}")

    script_file = Path(__file__).parent / f"resources/activate_script/{shell}_dev"
    if not script_file.is_file():
        out(f"{MARK_INVALID} Unsupported shell: {st_div(shell)}")
        raise typer.Exit(code=-1)

    print(script_file.read_text(), end="")


@app.command(name="use", no_args_is_help=True)
def local_version(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution to use in this directory.",
            autocompletion=autocomplete_installed
        )],
):
    """
    Set local JDK version for current directory.

    Creates a .java-version file in the current directory.

    Examples:
    -  jdk env local zulu-21
    -  jdk env local temurin-17
    """
    log(f"local_version()")
    log(f"  distro: {distro}")

    managed = read_managed()
    installed = managed["installed"]
    aliases = managed["aliases"]

    if distro not in installed and distro not in aliases:
        out(f"{MARK_INVALID} {st_emp(distro)} is not installed!", highlight=False)
        out(f"run jdk alias {distro} <INSTALLED_DISTRO>", highlight=False)
        raise typer.Exit(code=-1)

    version_file = Path.cwd() / _JAVA_VERSION_FILE
    version_file.write_text(distro + "\n")
    out(f"{MARK_CHECK} Local JDK: {st_emp(distro)} {st_dim(str(version_file))}", highlight=False)


@app.command(name="global", no_args_is_help=True)
def global_version(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution to use globally.",
            autocompletion=autocomplete_installed
        )],
):
    """
    Set global JDK version (fallback when no local .java-version).

    Creates ~/.java-version as the global default.

    Examples:
    -  jdk env global zulu-21
    -  jdk env global temurin-17
    """
    log(f"global_version()")
    log(f"  distro: {distro}")

    installed = get_installed()
    if distro not in installed:
        out(f"{MARK_INVALID} {st_emp(distro)} is not installed!", highlight=False)
        raise typer.Exit(code=-1)

    _GLOBAL_JAVA_VERSION_FILE.write_text(distro + "\n")
    out(f"{MARK_CHECK} Global JDK: {st_emp(distro)} {st_dim(str(_GLOBAL_JAVA_VERSION_FILE))}", highlight=False)


@app.command(name="hook-env")
def hook_env(slug: Annotated[str | None, typer.Option("--slug")]):
    """
    Internal: output env exports for the shell hook (called on directory change).
    """
    print(f"hook_env()")
    print(f"  slug: {slug}")

    managed = read_managed()
    installed = managed["installed"]
    aliases = managed["aliases"]
    if slug not in installed and slug not in aliases:
        print(f'# jdkman: {slug} is not installed')
        return

    if slug in aliases:
        slug = aliases[slug]

    java_home = f"{installed[slug]['location']}/Contents/Home"
    print(f'export JAVA_HOME="{java_home}"')


@app.command()
def aliases():
    log(f"alias()")

    managed = read_managed()
    aliases = managed["aliases"]
    log(f"  aliases: {pretty_repr(aliases)}")


@app.command()
def alias(
        ali: Annotated[str, typer.Argument(metavar="<ALIAS>=<DISTRO>", help="Alias name.")],
        slug: Annotated[str, typer.Argument(metavar="<DISTRO>", help="JVM distribution name.")],
):
    """
    alias
    """
    log(f"alias()")

    managed = read_managed()
    installed = managed["installed"]
    aliases = managed["aliases"]

    if ali in installed:
        out(f"** 이미 설치된 distro 이름이야 사용할수 없어: {ali}", highlight=False)
        raise typer.Exit(code=-1)
    if slug not in installed:
        out(f"** {slug} is not installed!", highlight=False)
        raise typer.Exit(code=-1)

    aliases[ali] = slug  # overwrite
    write_managed(managed)
    # managed_add_aliases()
    out(f"{MARK_CHECK} {ali} -> {slug}")


@app.command()
def unalias():
    log(f"unalias()")




"""

claude --resume 22c2d77f-92e6-412b-b0b9-883f47a0daab

jdk alias
jdk use 11

"""

