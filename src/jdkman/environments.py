from pathlib import Path

import typer

from .config import GLOBAL_ENV_FILE, LOCAL_ENV_FILE
from .console import log, out, MARK_INVALID, st_emp, st_div
from .registry import get_managed, get_installed, get_slug, add_aliases, get_aliases, del_aliases


def find_env_file(is_global: bool) -> Path | str:
    return GLOBAL_ENV_FILE if is_global else Path.cwd() / LOCAL_ENV_FILE


def set_env_file(env_tag: str, is_global: bool = False) -> str:
    log(f"set_env_file()")
    log(f"  env_tag: {env_tag}")
    log(f"  is_global: {is_global}")

    if env_tag not in get_managed():
        out(f"{MARK_INVALID} {st_div(env_tag)} is invalid!", highlight=False)
        raise typer.Exit(code=-1)

    env_file = find_env_file(is_global)
    env_file.write_text(env_tag + "\n")
    return env_file


def unset_env_file(is_global: bool = False) -> str:
    log(f"reset_env_file()")
    log(f"  is_global: {is_global}")

    env_file = find_env_file(is_global)
    env_file.write_text("")
    return env_file


def set_env_alias(alias: str, slug: str):
    log(f"set_env_alias()")
    log(f"  alias: {alias}")
    log(f"  slug: {slug}")

    installed = get_installed()

    # validate alias name
    if alias in installed:
        out(f"{MARK_INVALID} {st_div(alias)} conflicts with an installed JVM distribution name.", highlight=False)
        raise typer.Exit(code=-1)

    # validate slug
    get_slug(slug)

    # validate installed
    if slug not in installed:
        out(f"{MARK_INVALID} {st_emp(slug)} is not installed!", highlight=False)
        raise typer.Exit(code=-1)

    add_aliases(alias, slug)


def unset_env_alias(alias: str):
    log(f"unset_env_alias()")
    log(f"  alias: {alias}")

    aliases = get_aliases()

    # validate alias
    if alias not in aliases:
        out(f"{MARK_INVALID} {st_div(alias)} is not found.", highlight=False)
        raise typer.Exit(code=-1)

    del_aliases(alias)

