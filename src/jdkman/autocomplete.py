from jdkman.catalog import fetch_slugs
from jdkman.registry import get_installed


def autocomplete_installed(incomplete: str):
    return list(get_installed(sort=True).keys())


def autocomplete_slugs(incomplete: str):
    return list(fetch_slugs(sort=True).keys())


def autocomplete_commands(ctx, incomplete: str):
    if ctx.parent:
        group = ctx.parent.command
        return [
            name for name, cmd in group.commands.items()
            if not cmd.hidden and name.startswith(incomplete)
        ]
    return []

