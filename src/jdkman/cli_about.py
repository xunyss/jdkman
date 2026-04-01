from typing import Annotated

import click
import typer

from .autocomplete import autocomplete_commands
from .console import log, out, MARK_INVALID, st_div, version_str


app = typer.Typer()


@app.command(name="version", rich_help_panel="About", add_help_option=False)
def show_version(
        callback: Annotated[bool, typer.Option(
            hidden=True
        )] = False
):
    """
    Show the version and exit.
    """
    log(f"show_version()")
    log(f"  callback: {callback}")

    out(version_str())
    raise typer.Exit()


# noinspection PyUnresolvedReferences
@app.command(name="help", rich_help_panel="About")
def show_help(
        context: typer.Context,
        command: Annotated[str | None, typer.Argument(
            help="Command to show help for.",
            autocompletion=autocomplete_commands
        )] = None
):
    """
    Show help for a command.

    Examples:
    -  jdk help
    -  jdk help list
    -  jdk help install
    """
    log(f"show_help()")
    log(f"  context: {context}")
    log(f"  command: {command}")

    if command:
        ctx = context.parent
        cmd = ctx.command.commands.get(command)
        if cmd is None:
            out(f"{MARK_INVALID} Unknown command: {st_div(command)}")
            raise typer.Exit(code=-1)
        with click.Context(cmd, info_name=command, parent=ctx) as sub_ctx:
            cmd.get_help(sub_ctx)
    else:
        context.parent.get_help()

