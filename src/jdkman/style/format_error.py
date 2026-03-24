from dataclasses import dataclass

import click
import typer
import typer.rich_utils
from rich.padding import Padding
from rich.text import Text


@dataclass
class ErrorFormatter:
    """
    - No Panel Box for errors
    """
    header_style: str = "bold red"

    def apply(self) -> None:
        """Patch typer globally with this style."""
        typer.rich_utils.rich_format_error = self._build_formatter()

    def _build_formatter(self):
        style = self

        def rich_format_error(exc: click.ClickException) -> None:
            if exc.__class__.__name__ == "NoArgsIsHelpError":
                return

            _ru = typer.rich_utils
            # noinspection PyProtectedMember
            console = _ru._get_rich_console(stderr=True)
            ctx: click.Context | None = getattr(exc, "ctx", None)

            if ctx is not None:
                console.print(ctx.get_usage())

            if ctx is not None and ctx.command.get_help_option(ctx) is not None:
                console.print(
                    _ru.RICH_HELP.format(
                        command_path=ctx.command_path,
                        help_option=ctx.help_option_names[0],
                    ),
                    style=_ru.STYLE_ERRORS_SUGGESTION,
                )

            console.print(Padding(Text(f"{_ru.ERRORS_PANEL_TITLE}:", style=style.header_style), (0, 1, 0, 0)))
            console.print(Padding(_ru.highlighter(exc.format_message()), (0, 1, 0, 2)))

        return rich_format_error

