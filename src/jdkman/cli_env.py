import os
import sys
from pathlib import Path
from typing import Annotated

import typer

from .autocomplete import autocomplete_installed
from .config import is_macos
from .console import out, log, MARK_CHECK, MARK_INVALID, st_emp, st_dim, st_div
from .registry import get_installed


app = typer.Typer()

_JAVA_VERSION_FILE = ".java-version"
_GLOBAL_JAVA_VERSION_FILE = Path.home() / ".java-version"


def _java_home_from_location(location: str) -> str:
    if is_macos():
        return f"{location}/Contents/Home"
    return location


def _find_java_version(start_dir: Path) -> tuple[str, Path] | None:
    """Walk up directory tree looking for .java-version, fallback to global."""
    current = start_dir.resolve()
    while True:
        candidate = current / _JAVA_VERSION_FILE
        if candidate.is_file():
            slug = candidate.read_text().strip()
            if slug:
                return slug, candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    if _GLOBAL_JAVA_VERSION_FILE.is_file():
        slug = _GLOBAL_JAVA_VERSION_FILE.read_text().strip()
        if slug:
            return slug, _GLOBAL_JAVA_VERSION_FILE

    return None


@app.command(name="activate")
def activate(
        shell: Annotated[str, typer.Argument(
            help="Shell type. (zsh, bash)"
        )] = "zsh",
):
    """
    Print shell integration script for auto JDK switching.

    Add to your shell profile (~/.zshrc or ~/.bashrc):
    -  eval "$(jdk env activate zsh)"
    -  eval "$(jdk env activate bash)"
    """
    log(f"activate()")
    log(f"  shell: {shell}")

    if shell == "zsh":
        print(_zsh_script(), end="")
    elif shell == "bash":
        print(_bash_script(), end="")
    else:
        out(f"{MARK_INVALID} Unsupported shell: {st_div(shell)}")
        raise typer.Exit(code=-1)


@app.command(name="local", no_args_is_help=True)
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

    installed = get_installed()
    if distro not in installed:
        out(f"{MARK_INVALID} {st_emp(distro)} is not installed!", highlight=False)
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


@app.command(name="hook-env", hidden=True)
def hook_env():
    """Internal: output env exports for the shell hook (called on directory change)."""
    log(f"hook_env()")

    cwd = Path(os.environ.get("PWD", str(Path.cwd())))
    result = _find_java_version(cwd)

    if result is None:
        print('unset JAVA_HOME', file=sys.stdout)
        print('export PATH="$_JDKMAN_ORIG_PATH"', file=sys.stdout)
        return

    slug, version_file = result
    log(f"  slug: {slug}")
    log(f"  version_file: {version_file}")

    installed = get_installed()
    if slug not in installed:
        print(f'# jdkman: {slug} is not installed', file=sys.stderr)
        return

    java_home = _java_home_from_location(installed[slug]["location"])
    print(f'export JAVA_HOME="{java_home}"', file=sys.stdout)
    print(f'export PATH="{java_home}/bin:$_JDKMAN_ORIG_PATH"', file=sys.stdout)


def _zsh_script() -> str:
    return '''\
export _JDKMAN_ORIG_PATH="$PATH"

_jdkman_hook_chpwd() {
  _JDKMAN_LAST_DIR="$PWD"
  eval "$(jdk env hook-env 2>/dev/null)"
}

_jdkman_hook_precmd() {
  if [[ "$PWD" != "$_JDKMAN_LAST_DIR" ]]; then
    _JDKMAN_LAST_DIR="$PWD"
    eval "$(jdk env hook-env 2>/dev/null)"
  fi
}

typeset -ag chpwd_functions
if [[ -z "${chpwd_functions[(r)_jdkman_hook_chpwd]+1}" ]]; then
  chpwd_functions=( _jdkman_hook_chpwd ${chpwd_functions[@]} )
fi
typeset -ag precmd_functions
if [[ -z "${precmd_functions[(r)_jdkman_hook_precmd]+1}" ]]; then
  precmd_functions=( _jdkman_hook_precmd ${precmd_functions[@]} )
fi
'''


def _bash_script() -> str:
    return '''\
export _JDKMAN_ORIG_PATH="$PATH"

_jdkman_hook() {
  local dir="$PWD"
  if [[ "$dir" != "$_JDKMAN_LAST_DIR" ]]; then
    _JDKMAN_LAST_DIR="$dir"
    local output
    output="$(jdk env hook-env 2>/dev/null)"
    [[ -n "$output" ]] && eval "$output"
  fi
}

if [[ "$PROMPT_COMMAND" != *"_jdkman_hook"* ]]; then
  PROMPT_COMMAND="_jdkman_hook${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi
'''
