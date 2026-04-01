import os
from typing import Any

import rich.box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .config import (
    DISABLE_SUGGEST_OPTIONS,
    CUSTOM_STYLE_HELP, CUSTOM_STYLE_ERROR, CUSTOM_STYLE_TABLE, APP_VERSION,
    platform_name
)
from .custom_typer.format_error import ErrorFormatter
from .custom_typer.format_help import HelpFormatter
from .custom_typer.option_parser import OptionParserPatch


_state = {
    "verbose": False
}

_table_style = {
    "box": rich.box.HORIZONTALS,
    "header_style": "bold italic yellow",
}

_console = Console()
_log_console = Console(force_terminal=True)
_err_console = Console(stderr=True)


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
    # `"_JDK_COMPLETE" in os.environ` => autocomplete: [TAB] key in.
    if not _state["verbose"] or "_JDK_COMPLETE" in os.environ:
        return
    prefix = Text.from_markup("[italic bright_black]verbose[/italic bright_black] ")
    with _log_console.capture() as capture:
        _log_console.print(*objs, **kwargs)
    for line in capture.get().rstrip("\n").splitlines():
        _err_console.print(Text.assemble(prefix, Text.from_ansi(line)))



MARK_ARROW = "[blue]==>[/blue]"
MARK_CHECK = "[green]:heavy_check_mark:[/green]"
MARK_WARNING = "[magenta]:warning:[/magenta]"
MARK_INVALID = "[red]:exclamation_question_mark:[/red]"

def st_emp(content: Any) -> str:
    return f"[bold yellow]{content}[/bold yellow]"

def st_hig(content: Any) -> str:
    return f"[bold blue]{content}[/bold blue]"

def st_div(content: Any) -> str:
    return f"[cyan]{content}[/cyan]"

def st_dim(content: Any) -> str:
    return f"[dim]{content}[/dim]"

def st_cod(content: Any) -> str:
    return f"[bold italic underline]{content}[/bold italic underline]"

def st_not(content: Any) -> str:
    return f"[strike dim]{content}[/strike dim]"


def version_str() -> str:
    return f"""\
[bold yellow]      _    ____ [/bold yellow]
[bold yellow]     (_)__/ / /__ __ _  ___  ___ [/bold yellow]
[bold yellow]    / / _  /  '_//  ' \\/ _ `/ _ \\ [/bold yellow]
[bold yellow] __/ /\\_,_/_/\\_\\/_/_/_/\\_,_/_//_/ [/bold yellow]
[bold yellow]|___/ [/bold yellow]
       [cyan bold]{APP_VERSION}[/cyan bold] [dim]({platform_name()})[/dim]"""

