from collections import defaultdict
from typing import Annotated

import typer

from .autocomplete import autocomplete_slugs
from .catalog import fetch_artifacts
from .config import CACHE_DIR
from .console import st_emp, st_nor
from .console import out, log, GREEN_CHECK
from .detect import scan_unmanaged
from .installer import download_jvm
from .registry import get_dist, get_slug, get_installed

app = typer.Typer()


@app.callback(no_args_is_help=True)
def dev_main(context: typer.Context):
    log(f"dev_main()")
    log(f"  context.args: {context.args}")
    log(f"  context.command: '{context.command.name}'")
    log(f"  context.command_path: '{context.command_path}'")
    log(f"  context.invoked_subcommand: '{context.invoked_subcommand}'")


@app.command()
def diff():
    """
    diff between zip and tar.gz
    """
    log(f"diff()")

    # (vendor, version, features, image_type) 기준으로 그루핑 후 file_type 수집
    groups: dict[tuple, set] = defaultdict(set)
    for artifact in fetch_artifacts():
        key = (artifact["vendor"], artifact["version"], tuple(sorted(artifact["features"])), artifact["image_type"])
        groups[key].add(artifact["file_type"])

    zip_only  = { k: v for k, v in groups.items() if v == {"zip"} }
    tar_only  = { k: v for k, v in groups.items() if v == {"tar.gz"} }
    both      = { k: v for k, v in groups.items() if v == {"zip", "tar.gz"} }

    out(f"zip only:    {len(zip_only)}")
    out(f"tar.gz only: {len(tar_only)}")
    out(f"both:        {len(both)}")
    out()

    out("=== zip only ===")
    for (vendor, version, features, image_type), _ in sorted(list(zip_only.items())):
        out(f"  {vendor:<20} {version:<30} {image_type}  {list(features)}")
    out()

    out("=== tar.gz only ===")
    for (vendor, version, features, image_type), _ in sorted(list(tar_only.items())):
        out(f"  {vendor:<20} {version:<30} {image_type}  {list(features)}")


@app.command()
def download(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution name to download. (e.g. zulu-21, temurin-17)",
            autocompletion=autocomplete_slugs
        )]
):
    """
    download_jvm(get_dist(distro))
    """
    log(f"download()")
    log(f"  distro: {distro}")

    dist_file = download_jvm(get_dist(distro))
    out(f"{GREEN_CHECK} Downloaded: {st_emp(distro)} {st_nor(dist_file.name)}", highlight=False)


@app.command()
def slug(
        distro: Annotated[str, typer.Argument(
            metavar="<DISTRO>",
            help="JVM distribution name to get detail information. (e.g. zulu-21, temurin-17)",
            autocompletion=autocomplete_slugs
        )]
):
    """
    get_slug(distro)
    """
    log(f"info()")
    log(f"  distro: {distro}")

    out(get_slug(distro))


@app.command()
def installed():
    """
    get_installed()
    """
    log(f"installed()")

    out(get_installed())


@app.command()
def cache():
    """
    CACHE_DIR.iterdir()
    """
    log(f"cache()")
    log(f"  CACHE_DIR: {CACHE_DIR}")

    for cached in CACHE_DIR.iterdir():
        out(cached)


@app.command()
def scan():
    """
    scan_unmanaged()
    """
    log(f"scan()")

    out(scan_unmanaged())

