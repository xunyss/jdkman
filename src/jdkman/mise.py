import json
import shutil
import subprocess
from typing import Any

import typer

from .config import is_macos, is_windows, is_linux
from .console import out, MARK_INVALID, log, st_emp, st_div, st_dim
from .registry import get_installed, get_slug


def is_mise_enabled() -> bool:
    # noinspection PyDeprecation
    return shutil.which("mise") is not None


def link_path(location: str):
    # todo: impl other OS: linux, windows
    if is_macos():
        return f"{location}/Contents/Home"
    elif is_windows():
        pass
    elif is_linux():
        pass
    return None


def mise_ls() -> list[dict[str, Any]]:
    log(f"mise_ls()")

    command = ["mise", "ls", "java", "--json"]
    result = subprocess.run(command, capture_output=True, text=True)
    return json.loads(result.stdout)


def mise_link(slug: str) -> list[dict[str, Any]]:
    log(f"mise_link()")
    log(f"  slug: {slug}")

    # check mise installed
    if not is_mise_enabled():
        out(f"{MARK_INVALID} {st_div('mise')} is not installed!", highlight=False)
        raise typer.Exit(code=-1)

    # validate slug
    get_slug(slug)

    # validate installed
    installed = get_installed()
    if slug not in installed:
        out(f"{MARK_INVALID} {st_emp(slug)} is not installed!", highlight=False)
        raise typer.Exit(code=-1)

    command = ["mise", "link", f"java@{slug}", link_path(installed[slug]["location"])]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stderr:
        out(f"{MARK_INVALID} {st_dim(result.stderr)}", highlight=False)
        raise typer.Exit(code=-1)

    return mise_ls()

