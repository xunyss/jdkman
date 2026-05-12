import json
import shutil
import subprocess
from typing import Any

import typer

from .config import is_macos
from .console import log, out, MARK_INVALID, st_div, st_dim
from .registry import get_managed_slug


def validate_mise_installed():
    # noinspection PyDeprecation
    if not shutil.which("mise"):
        out(f"{MARK_INVALID} {st_div('mise')} is not installed!", highlight=False)
        raise typer.Exit(code=-1)


def link_path(location: str) -> str:
    # todo: impl other OS: linux, windows
    if is_macos():
        return f"{location}/Contents/Home"
    return location


def mise_ls() -> list[dict[str, Any]]:
    log(f"mise_ls()")

    command = ["mise", "ls", "java", "--json"]
    result = subprocess.run(command, capture_output=True, text=True)
    return json.loads(result.stdout)


def mise_link(env_tag: str):
    log(f"mise_link()")
    log(f"  env_tag: {env_tag}")

    # validate env_tag
    installed_info = get_managed_slug(env_tag)

    command = ["mise", "link", f"java@{env_tag}", link_path(installed_info["location"])]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stderr:
        out(f"{MARK_INVALID} {st_dim(result.stderr)}", highlight=False)
        raise typer.Exit(code=-1)

