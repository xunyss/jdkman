import os
from typing import Any

import rich.box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .config import DISABLE_SUGGEST_OPTIONS, CUSTOM_STYLE_HELP, CUSTOM_STYLE_ERROR, CUSTOM_STYLE_TABLE
from .style.format_error import ErrorFormatter
from .style.format_help import HelpFormatter
from .style.option_parser import OptionParserPatch


_state = {
    "verbose": False
}

_table_style = {
    "box": rich.box.HORIZONTALS,
    "header_style": "bold italic yellow",
}

_console = Console()
_log_console = Console(force_terminal=True)


if DISABLE_SUGGEST_OPTIONS:  # like "suggest_commands=False"
    OptionParserPatch().apply()


if CUSTOM_STYLE_HELP:
    HelpFormatter(
        section_header_style="bold yellow",
        section_order=["commands", "arguments", "options"],
        hidden_options={"--install-completion", "--show-completion"},
    ).apply()

if CUSTOM_STYLE_ERROR:
    ErrorFormatter(
        header_style="bold red",
    ).apply()


def update_state(key: str, value: Any):
    _state[key] = value


def table(*cols: str):
    if CUSTOM_STYLE_TABLE:
        return Table(*cols, **_table_style)
    return Table(*cols)


def out(*objs: Any, **kwargs: Any):
    _console.print(*objs, **kwargs)


def log(*objs: Any, **kwargs: Any):
    if not _state["verbose"] or "_JDK_COMPLETE" in os.environ:
        return
    prefix = Text.from_markup("[italic bright_black]verbose[/italic bright_black] ")
    with _log_console.capture() as capture:
        _log_console.print(*objs, **kwargs)
    for line in capture.get().rstrip("\n").splitlines():
        out(Text.assemble(prefix, Text.from_ansi(line)))



BLUE_ARROW = "[blue]==>[/blue]"
GREEN_CHECK = "[green]:heavy_check_mark:[/green]"
ORANGE_WARNING = "[orange3]:warning:[/orange3]"
RED_WARNING = "[red]:exclamation_question_mark:[/red]"


def st_emp(content: Any) -> str:
    return f"[yellow]{content}[/yellow]"

def st_div(content: Any) -> str:
    return f"[cyan]{content}[/cyan]"

def st_nor(content: Any) -> str:
    return f"[grey70]{content}[/grey70]"

