from collections import defaultdict

import typer

from .catalog import fetch_artifacts
from .config import CACHE_DIR
from .console import ARGUMENT_SLUG
from .console import out, log, GREEN_CHECK
from .detect import scan_unmanaged
from .installer import download_jvm
from .registry import get_dist, get_slug

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
    Compare the file_type(.zip and .tar.gz) of artifacts.
    """
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
def info(distro: ARGUMENT_SLUG):
    """
    Show information about a JVM distribution.
    """
    log(f"info()")
    log(f"  distro: {distro}")
    out(get_slug(distro))

@app.command()
def download(distro: ARGUMENT_SLUG):
    """
    Install a JVM distribution.
    """
    log(f"download()")
    log(f"  distro: {distro}")
    install_dir = download_jvm(get_dist(distro))
    out(f"Downloaded: {distro} {install_dir} {GREEN_CHECK}")


@app.command()
def cache():
    """
    Show the paths within the cache directory.
    """
    log(f"cache()")
    log(f"  CACHE_DIR: {CACHE_DIR}")
    for cached in CACHE_DIR.iterdir():
        out(f"Path in cache: {cached}")


@app.command()
def scan():
    """
    Scan the local filesystem for unmanaged JVM distributions.
    """
    log(f"scan()")
    unmanaged = scan_unmanaged()
    out(f"Unmanaged:", unmanaged)

