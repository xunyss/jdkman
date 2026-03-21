from typing import Any, Annotated

import rich.box
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .config import CUSTOM_STYLE_HELP, CUSTOM_STYLE_TABLE
from .style.format_help import HelpFormatter


_state = {
    "verbose": False
}

_table_style = {
    "box": rich.box.HORIZONTALS,
    "header_style": "bold italic yellow",
}

_console = Console()
_log_console = Console(force_terminal=True)


if CUSTOM_STYLE_HELP:
    HelpFormatter(
        section_header_style="bold yellow",
        section_order=["commands", "arguments", "options"],
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
    if not _state["verbose"]:
        return
    prefix = Text.from_markup("[italic bright_black]verbose[/italic bright_black] ")
    with _log_console.capture() as capture:
        _log_console.print(*objs, **kwargs)
    for line in capture.get().rstrip("\n").splitlines():
        out(Text.assemble(prefix, Text.from_ansi(line)))



BLUE_ARROW = "[blue]==>[/blue]"
GREEN_CHECK = "[green]:heavy_check_mark:[/green]"
RED_WARNING = "[red]:exclamation_question_mark:[/red]"


ARGUMENT_SLUG = Annotated[str, typer.Argument(
    metavar="<DISTRO>",
    help="JVM distribution name. (e.g. zulu-21, temurin-17)"
)]

