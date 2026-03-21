import typer

from .config import is_macos
from .console import out, log
from .detect import exec_java_home


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
def mise():
    """
    Integration with mise.
    """
    log(f"mise()")

