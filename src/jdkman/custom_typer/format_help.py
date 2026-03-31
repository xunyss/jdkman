import inspect
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal

import click
import typer
import typer.rich_utils
from rich.align import Align
from rich.console import Group
from rich.padding import Padding
from rich.table import Table
from rich.text import Text


Section = Literal["arguments", "options", "commands"]

_DEFAULT_ORDER: list[Section] = ["arguments", "options", "commands"]


@dataclass
class HelpFormatter:
    """
    - No Section Box
    - No Option Highlighting in Command Help
    - Sections Ordering
    """
    section_header_style: str = "bold yellow"
    section_order: list[Section] = field(default_factory=lambda: list(_DEFAULT_ORDER))
    hidden_options: set[str] = field(default_factory=set)

    def apply(self) -> None:
        """Patch typer globally with this style."""
        typer.rich_utils.rich_format_help = self._build_formatter()
        self._patch_help_option()

    # noinspection PyMethodMayBeStatic
    def _patch_help_option(self) -> None:
        """Patch click's --help callback to avoid an extra newline."""
        import click.decorators
        _orig = click.decorators.help_option
        _ru = typer.rich_utils

        def _patched(*param_decls, **kwargs):
            def _show_help(ctx: click.Context, param: click.Parameter, value: bool) -> None:
                if value and not ctx.resilient_parsing:
                    cmd = ctx.command
                    # noinspection PyUnresolvedReferences
                    if hasattr(cmd, "rich_markup_mode") and cmd.rich_markup_mode is not None:
                        _ru.rich_format_help(obj=cmd, ctx=ctx, markup_mode=cmd.rich_markup_mode)
                    else:
                        click.echo(ctx.get_help(), color=ctx.color)
                    ctx.exit()

            kwargs.setdefault("callback", _show_help)
            return _orig(*param_decls, **kwargs)

        click.decorators.help_option = _patched

    def _build_formatter(self):
        style = self

        # noinspection PyProtectedMember
        def rich_format_help(
            *,
            obj: click.Command | click.Group,
            ctx: click.Context,
            markup_mode: typer.rich_utils.MarkupModeStrict,
        ) -> None:
            _ru = typer.rich_utils
            console = _ru._get_rich_console()
            console.print(Padding(_ru.highlighter(obj.get_usage(ctx)), (0, 1, 1, 0)), style=_ru.STYLE_USAGE_COMMAND)

            if obj.help:
                help_text = inspect.cleandoc(obj.help).partition("\f")[0]
                first_line, *remaining = help_text.split("\n\n")
                if markup_mode != "markdown" and not first_line.startswith("\b"):
                    first_line = first_line.replace("\n", " ")
                parts: list = [Text.from_markup(first_line.strip())]
                if remaining:
                    parts.append(Text(""))
                    parts.append(Text.from_markup("\n\n".join(remaining), style=_ru.STYLE_HELPTEXT))
                console.print(Padding(Align(Group(*parts), pad=False), (0, 1, 1, 0)), highlight=False)

            # Collect commands
            panel_to_commands: defaultdict[str, list[click.Command]] = defaultdict(list)
            if isinstance(obj, click.Group):
                for name in obj.list_commands(ctx):
                    cmd = obj.get_command(ctx, name)
                    if cmd and not cmd.hidden:
                        pname = getattr(cmd, _ru._RICH_HELP_PANEL_NAME, None) or _ru.COMMANDS_PANEL_TITLE
                        panel_to_commands[pname].append(cmd)
            max_cmd_len = max((len(c.name or "") for cmds in panel_to_commands.values() for c in cmds), default=0)

            # Collect arguments / options
            panel_to_arguments: defaultdict[str, list[click.Argument]] = defaultdict(list)
            panel_to_options: defaultdict[str, list[click.Option]] = defaultdict(list)
            for param in obj.get_params(ctx):
                if getattr(param, "hidden", False):
                    continue
                if isinstance(param, click.Option) and style.hidden_options.intersection(param.opts):
                    continue
                pname = getattr(param, _ru._RICH_HELP_PANEL_NAME, None)
                if isinstance(param, click.Argument):
                    panel_to_arguments[pname or _ru.ARGUMENTS_PANEL_TITLE].append(param)
                elif isinstance(param, click.Option):
                    panel_to_options[pname or _ru.OPTIONS_PANEL_TITLE].append(param)

            def _panels(panel_dict, default_title):
                entries = [(default_title, panel_dict.get(default_title, []))]
                entries += [(p, v) for p, v in panel_dict.items() if p != default_title]
                return [(p, v) for p, v in entries if v]

            section_panels = {
                "commands":  _panels(panel_to_commands,  _ru.COMMANDS_PANEL_TITLE),
                "arguments": _panels(panel_to_arguments, _ru.ARGUMENTS_PANEL_TITLE),
                "options":   _panels(panel_to_options,   _ru.OPTIONS_PANEL_TITLE),
            }

            has_epilog = bool(obj.epilog)
            active = [(s, section_panels[s]) for s in style.section_order if section_panels.get(s)]
            for si, (section, panels) in enumerate(active):
                is_last_section = si == len(active) - 1 and not has_epilog
                for pi, (pname, items) in enumerate(panels):
                    trailing = not (is_last_section and pi == len(panels) - 1)
                    console.print(Padding(Text(f"{pname}:", style=style.section_header_style), (0, 1, 0, 0)))
                    if section == "commands":
                        _print_commands(items, markup_mode, console, max_cmd_len, trailing)
                    else:
                        _print_params(items, ctx, markup_mode, console, trailing)

            if obj.epilog:
                lines = obj.epilog.split("\n\n")
                epilogue = "\n".join([x.replace("\n", " ").strip() for x in lines])
                epilogue_text = _ru._make_rich_text(text=epilogue, markup_mode=markup_mode)
                console.print(Padding(Align(epilogue_text, pad=False), (0, 1, 0, 0)))

        return rich_format_help


# ── internal rendering helpers ──────────────────────────────────────────────

# noinspection PyProtectedMember
def _print_commands(
    commands: list[click.Command],
    markup_mode: typer.rich_utils.MarkupModeStrict,
    console,
    cmd_len: int,
    trailing: bool = True,
) -> None:
    _ru = typer.rich_utils
    table = Table(highlight=False, show_header=False, expand=False, box=None, show_edge=False, pad_edge=False, padding=(0, 2))
    table.add_column(style=_ru.STYLE_COMMANDS_TABLE_FIRST_COLUMN, no_wrap=True, width=cmd_len)
    table.add_column(justify="left", no_wrap=False, ratio=10)
    for command in commands:
        name_text = Text(command.name or "", style=_ru.STYLE_DEPRECATED_COMMAND if command.deprecated else "")
        table.add_row(name_text, _ru._make_command_help(help_text=command.short_help or command.help or "", markup_mode=markup_mode))
    console.print(Padding(table, (0, 1, 1 if trailing else 0, 2)))


# noinspection PyProtectedMember,PyUnresolvedReferences
def _print_params(
    params: list[click.Option] | list[click.Argument],
    ctx: click.Context,
    markup_mode: typer.rich_utils.MarkupModeStrict,
    console,
    trailing: bool = True,
) -> None:
    _ru = typer.rich_utils
    rows: list[list[Any]] = []
    required_rows: list[str | Text] = []

    for param in params:
        opt_long, opt_short, neg_long, neg_short = [], [], [], []
        for s in param.opts:
            (opt_long if "--" in s else opt_short).append(s)
        for s in param.secondary_opts:
            (neg_long if "--" in s else neg_short).append(s)

        metavar = Text(style=_ru.STYLE_METAVAR, overflow="fold")
        metavar_str = param.make_metavar(ctx=ctx)
        if isinstance(param, click.Argument) and param.name and metavar_str == param.name.upper():
            metavar_str = param.type.name.upper()
        if metavar_str != "BOOLEAN":
            metavar.append(metavar_str)
        if (
            isinstance(param.type, click.types._NumberRangeBase)
            and isinstance(param, click.Option)
            and not (param.count and param.type.min == 0 and param.type.max is None)
        ):
            range_str = param.type._describe_range()
            if range_str:
                metavar.append(_ru.RANGE_STRING.format(range_str))

        required_rows.append(Text(_ru.REQUIRED_SHORT_STRING, style=_ru.STYLE_REQUIRED_SHORT) if param.required else "")
        rows.append([
            _ru.highlighter(",".join(opt_long)),
            _ru.highlighter(",".join(opt_short)),
            _ru.negative_highlighter(",".join(neg_long)),
            _ru.negative_highlighter(",".join(neg_short)),
            _ru.metavar_highlighter(metavar),
            _ru._get_parameter_help(param=param, ctx=ctx, markup_mode=markup_mode),
        ])

    final_rows = [[req, *row] for req, row in zip(required_rows, rows)] if any(required_rows) else rows
    table = Table(highlight=True, show_header=False, expand=False, box=None, show_edge=False, pad_edge=False, padding=(0, 1))
    for row in final_rows:
        table.add_row(*row)
    console.print(Padding(table, (0, 1, 1 if trailing else 0, 2)))


# convenience alias kept for backwards compat
# noinspection PyProtectedMember
custom_rich_format_help = HelpFormatter()._build_formatter()

