from typing import Annotated

import typer

from .autocomplete import autocomplete_managed
from .config import is_macos
from .console import log, out, table, MARK_CHECK, st_hig, st_dim
from .detect import exec_java_home
from .mise import validate_mise_installed, mise_link, mise_ls
from .utils import shorten


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
        Run '[bold italic underline]jdk home -h[/bold italic underline]' to see all available options.
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
            metavar="DISTRO|ALIAS",
            help="JVM distribution name to register as a mise symlink. (omit to list)",
            autocompletion=autocomplete_managed
        )] = None
):
    """
    Show or register JVM distributions as mise java tools via symlink.

    Examples:
    -  jdk mise
    -  jdk mise zulu-21
    """
    log(f"mise()")
    log(f"  distro: {distro}")

    validate_mise_installed()

    if distro:
        mise_link(distro)

    mise_tools = mise_ls()
    tab = table("mise_tool", "version", "symlink", "installed", "active", "source", "requested")
    for mise_tool in mise_tools:
        is_link = True if mise_tool.get("symlinked_to") else False
        is_active = mise_tool.get("active")
        tab.add_row(
            is_active and "java" or st_dim("java"),
            st_hig(mise_tool["version"]) if is_active else st_dim(mise_tool["version"]),
            is_link and st_dim(MARK_CHECK) or None,
            mise_tool["installed"] and st_dim(MARK_CHECK) or None,
            is_active and MARK_CHECK or None,
            is_active and shorten(mise_tool["source"]["path"]) or None,
            mise_tool["requested_version"] if is_active else None
        )
    out(tab if tab.row_count > 0
        else f"{MARK_CHECK} No mise java tools found.")

