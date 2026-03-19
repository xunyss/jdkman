import shutil
from pathlib import Path
from urllib.parse import urlparse

import requests
import typer
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

from .config import CACHE_DIR, INSTALL_DIR, CLEAN_WORK_DIR
from .console import log, out
from .registry import managed_add, get_installed, managed_del, get_outdated, get_dist, get_slug
from .utils import extract_archive, sha256_file


def verify_checksum(dist_file: Path, dist_checksum: str) -> Path:
    log(f"verify_checksum()")

    expected = dist_checksum.removeprefix("sha256:").lower()
    actual = sha256_file(dist_file)
    log(f"  expected: {expected}")
    log(f"  actual:   {actual}")

    if actual != expected:
        out(f"Checksum mismatch!")
        raise typer.Exit(code=1)

    return dist_file


def download_jvm(dist_info: dict) -> Path:
    log(f"download_jvm()")

    filename = Path(urlparse(dist_info["url"]).path).name
    dist_file = CACHE_DIR / filename

    if dist_file.exists():
        out(f"Already downloaded: {dist_file}")
    else:
        with requests.get(dist_info["url"], stream=True, timeout=60) as request:
            request.raise_for_status()
            total = int(request.headers.get("content-length", 0))
            with open(dist_file, "wb") as file:
                with Progress(
                    f"[green]Downloading...[/green] {filename}",
                    BarColumn(bar_width=None), DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn(),
                ) as progress:
                    task = progress.add_task("", total=total)
                    for chunk in request.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            file.write(chunk)
                            progress.update(task, advance=len(chunk))

    return verify_checksum(dist_file, dist_info["checksum"])


def find_dist_jvm_root(work_dir: Path) -> Path | None:
    for java_bin in work_dir.rglob("Contents/Home/bin/java"):
        return java_bin.parents[3]
    return None


def make_jvm_dir_name(slug_info: dict):
    _vendor_alias = {
        "graalvm": "graalvm-ce",
        "graalvm-community": "graalvm-ce",
        "oracle-graalvm": "graalvm",
        "microsoft": "ms",
        "jetbrains": "jbr",
    }
    vendor_alias = _vendor_alias.get(slug_info["vendor"], slug_info["vendor"])
    feature = slug_info["features"][0] if slug_info["features"] and slug_info["features"] != ["notarized"] else ""
    parts = [vendor_alias]
    if feature:
        parts.append(feature)
    parts.append(str(slug_info["major_version"]))
    return f"{"-".join(parts)}.{slug_info["image_type"]}"


def move_jvm_dir(slug: str, work_dir: Path) -> Path:
    slug_info = get_slug(slug)
    root = find_dist_jvm_root(work_dir)
    jvm_dir_name = make_jvm_dir_name(slug_info)
    renamed_jvm_dir = root.with_name(jvm_dir_name)

    root.rename(renamed_jvm_dir)
    shutil.move(renamed_jvm_dir, INSTALL_DIR)

    return INSTALL_DIR / renamed_jvm_dir.name


def install_jvm(slug: str):
    log(f"install_jvm()")
    log(f"  slug: {slug}")

    # download_jvm
    dist_info = get_dist(slug)
    dist_file = download_jvm(dist_info)

    # extract to work_dir
    work_dir = dist_file.parent / f"{slug}_{dist_info["version"]}"
    work_dir.mkdir(parents=True, exist_ok=True)
    extract_archive(dist_file, work_dir)

    # move to install_dir
    installed_dir = move_jvm_dir(slug, work_dir)

    # update managed
    managed_add(slug, dist_info, installed_dir)

    # remove cache
    if CLEAN_WORK_DIR:
        dist_file.unlink(missing_ok=True)
        shutil.rmtree(work_dir, ignore_errors=True)

    # installed jvm dir
    return installed_dir


def uninstall_jvm(slug: str):
    log(f"uninstall_jvm()")
    log(f"  slug: {slug}")

    # delete jvm location
    jvm_location = get_installed()[slug]["location"]
    shutil.rmtree(Path(jvm_location), ignore_errors=True)

    # update managed
    managed_del(slug)

    # deleted jvm dir
    return jvm_location


def upgrade_jvm(slug: str):
    log(f"upgrade_jvm()")
    log(f"  slug: {slug}")

    if get_outdated().get(slug):
        uninstall_jvm(slug)
        install_jvm(slug)
    else:
        out(f"{slug} is already up-to-date.")
        raise typer.Exit(code=1)

