from pathlib import Path
from typing import Any

import typer

from .config import GLOBAL_ENV_FILE, LOCAL_ENV_FILE
from .console import log, out, MARK_INVALID, st_emp, st_div
from .registry import get_managed, get_installed, get_slug, add_aliases, get_aliases, del_aliases


def print_activate_script(shell: str, dev_mode: bool = False):
    log(f"print_activate_script()")

    script = f"{shell}_dev" if dev_mode else shell
    script = Path(__file__).parent / f"resources/env_scripts/{script}"
    if not script.is_file():
        out(f"{MARK_INVALID} Unsupported shell: {st_div(shell)}")
        raise typer.Exit(code=-1)

    print(script.read_text(), end="")


def print_deactivate_script(shell: str):
    log(f"print_deactivate_script()")

    script = Path(__file__).parent / f"resources/env_scripts/{shell}_deactivate"
    if not script.is_file():
        out(f"{MARK_INVALID} Unsupported shell: {st_div(shell)}")
        raise typer.Exit(code=-1)

    print(script.read_text(), end="")


def find_env_file(is_global: bool) -> Path:
    return GLOBAL_ENV_FILE if is_global else Path.cwd() / LOCAL_ENV_FILE


def set_env_tag(env_tag: str, is_global: bool = False) -> Path:
    log(f"set_env_file()")
    log(f"  env_tag: {env_tag}")
    log(f"  is_global: {is_global}")

    if env_tag not in get_managed():
        out(f"{MARK_INVALID} {st_div(env_tag)} is invalid!", highlight=False)
        raise typer.Exit(code=-1)

    env_file = find_env_file(is_global)
    env_file.write_text(env_tag + "\n")
    return env_file


def unset_env_tag(is_global: bool = False) -> Path:
    log(f"reset_env_file()")
    log(f"  is_global: {is_global}")

    env_file = find_env_file(is_global)
    env_file.write_text("")
    return env_file


def get_env_tag_local() -> tuple[str | None, Path | None]:
    """
    Read local:
        traverse CWD → root for .java-version
    """
    log(f"get_env_tag_local()")

    d = Path.cwd()
    while d != d.parent:
        env_file = d / LOCAL_ENV_FILE
        if env_file.is_file():
            tag = env_file.read_text().strip()
            if tag:
                return tag, env_file
        d = d.parent
    return None, None


def get_env_tag_global() -> tuple[str | None, Path | None]:
    """
    Read global:
        ~/.config/jdkman/.java-version.
    """
    log(f"get_env_tag_global()")

    if GLOBAL_ENV_FILE.is_file():
        tag = GLOBAL_ENV_FILE.read_text().strip()
        if tag:
            return tag, GLOBAL_ENV_FILE
    return None, None


def get_env_tag() -> dict[str, dict[str, Any]]:
    log(f"get_env_tag()")

    g_tag, g_src = get_env_tag_global()
    l_tag, l_src = get_env_tag_local()
    return {
        "global": { "tag": g_tag, "source": g_src if g_src else None },
        "local": { "tag": l_tag, "source": l_src if l_src else None }
    }


def get_envs() -> dict[str, dict[str, Any]]:
    log(f"get_env()")

    # 현재 shell 에 activate 되어 있는지 일단 확인 필요
    managed = get_managed(sort=False, divided=True)
    installed = managed["installed"]
    aliases = managed["aliases"]

    envs = get_env_tag()
    for env in envs.values():
        slug = aliases.get(env["tag"], env["tag"])
        env["slug"] = slug
        env["version"] = installed[slug]["version"] if slug in installed else None

    return envs


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


def get_env_aliases() -> list[dict[str, Any]]:
    log(f"get_env_aliases()")

    managed = get_managed(sort=True, divided=True)
    installed = managed["installed"]
    aliases = managed["aliases"]
    return [
        {
            "alias": alias,
            "slug": slug,
            "version": installed[slug]["version"] if slug in installed else None,
        }
        for alias, slug in aliases.items()
    ]

