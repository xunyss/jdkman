from typing import Annotated

import typer

from .config import is_macos
from .console import out, log, ARGUMENT_SLUG, table, GREEN_CHECK
from .detect import exec_java_home
from .mise import mise_link, mise_ls


app = typer.Typer()


if is_macos():
    @app.command(
        hidden=not is_macos(),
        rich_help_panel="Tools",
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        },
    )
    def home(context: typer.Context):
        """
        Show installed JVM home paths. (macOS only)

        Wraps /usr/libexec/java_home with identical options.
        Run [blue]'jdk home -h'[/blue] to see all available options.
        """
        log(f"home()")
        log(f"  context.args: {context.args}")

        result = exec_java_home(*context.args)
        if result.stderr:
            out(result.stderr, end="", highlight=False)
        if result.stdout:
            out(result.stdout, end="", highlight=False)


@app.command(rich_help_panel="Tools")
def mise(
        distro: Annotated[str, typer.Argument(
            help="JVM distribution name to register as a mise symlink. (omit to list)"
        )] = None
):
    """
    Show or Register JVM distributions as mise java tools via symlink.

    Examples:
    -  jdk mise
    -  jdk mise zulu-21
    """
    log(f"mise()")
    log(f"  distro: {distro}")

    mise_tools = mise_link(distro) if distro else mise_ls()
    tab = table("mise_tool", "version", "symlink", "installed", "active")
    for mise_tool in mise_tools:
        is_link = True if mise_tool.get("symlinked_to") else False
        tab.add_row(
            "java", mise_tool["version"], is_link and GREEN_CHECK or None,
            mise_tool["installed"] and GREEN_CHECK or None,
            mise_tool["active"] and GREEN_CHECK or None
        )
    out(tab if tab.row_count > 0
        else f"{GREEN_CHECK} No mise java tools found.")

