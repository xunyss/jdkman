import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import typer
from rich.pretty import pretty_repr
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

from .config import CACHE_DIR, INSTALL_DIR, CLEAN_WORK_DIR, is_macos
from .console import log, out, MARK_ARROW, MARK_INVALID, MARK_CHECK, st_emp, st_div, st_dim
from .registry import add_installed, del_installed, get_installed, get_installed_slug, get_outdated, get_slug, get_dist
from .utils import extract_archive, sha256_file


def verify_checksum(dist_file: Path, dist_checksum: str) -> Path:
    log(f"verify_checksum()")
    log(f"  dist_file: {dist_file}")

    expected = dist_checksum.removeprefix("sha256:").lower()
    actual = sha256_file(dist_file)
    log(f"  expected: {expected}")
    log(f"  actual:   {actual}")

    if actual != expected:
        out(f"{MARK_INVALID} Checksum mismatch!")
        raise typer.Exit(code=-1)
    else:
        out(f"{MARK_CHECK} Checksum verified.")

    return dist_file


def download_jvm(dist_info: dict[str, Any]) -> Path:
    log(f"download_jvm()")
    log(f"  dist_info: {pretty_repr(dist_info)}")

    filename = Path(urlparse(dist_info["url"]).path).name
    dist_file = CACHE_DIR / filename

    if dist_file.exists():
        out(f"Already downloaded: {st_div(dist_file.name)}", highlight=False)
    else:
        out(f"{MARK_ARROW} Downloading JVM distribution...", highlight=False)

        import requests  # lazy import
        with requests.get(dist_info["url"], stream=True, timeout=60) as request:
            request.raise_for_status()
            total = int(request.headers.get("content-length", 0))
            with open(dist_file, "wb") as file:
                with Progress(
                    f"Downloading... {st_dim(filename)}",
                    BarColumn(bar_width=None), DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn(),
                ) as progress:
                    task = progress.add_task("", total=total)
                    for chunk in request.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            file.write(chunk)
                            progress.update(task, advance=len(chunk))

        out(f"Downloaded: {st_div(dist_file.name)}", highlight=False)

    return verify_checksum(dist_file, dist_info["checksum"])


def find_dist_jvm_root(work_dir: Path) -> Path:
    log(f"find_dist_jvm_root()")
    log(f"  work_dir: {work_dir}")

    # todo: impl other OS: linux, windows
    if is_macos():
        for java_bin in work_dir.rglob("Contents/Home/bin/java"):
            return java_bin.parents[3]
    else:
        for java_bin in work_dir.rglob("bin/java"):
            return java_bin.parents[1]
    # 실행 안됨
    return work_dir


def make_jvm_dir_name(slug_info: dict[str, Any]):
    log(f"make_jvm_dir_name()")

    _vendor_aliases = {
        "graalvm": "graalvm-ce",
        "graalvm-community": "graalvm-ce",
        "oracle-graalvm": "graalvm",
        "microsoft": "ms",
        "jetbrains": "jbr",
    }
    vendor_alias = _vendor_aliases.get(slug_info["vendor"], slug_info["vendor"])
    feature = slug_info["features"][0] if slug_info["features"] and slug_info["features"] != ["notarized"] else ""
    parts = [vendor_alias]
    if feature:
        parts.append(feature)
    parts.append(str(slug_info["major_version"]))
    # noinspection PyTypeChecker
    return f"{'-'.join(parts)}.{slug_info['image_type']}"


def move_jvm_dir(slug: str, work_dir: Path) -> Path:
    log(f"move_jvm_dir()")
    log(f"  slug: {slug}")
    log(f"  work_dir: {work_dir}")

    slug_info = get_slug(slug)
    root = find_dist_jvm_root(work_dir)
    jvm_dir_name = make_jvm_dir_name(slug_info)
    renamed_jvm_dir = root.with_name(jvm_dir_name)

    root.rename(renamed_jvm_dir)
    shutil.move(renamed_jvm_dir, INSTALL_DIR)

    return INSTALL_DIR / renamed_jvm_dir.name


def install_jvm(slug: str) -> Path:
    log(f"install_jvm()")
    log(f"  slug: {slug}")

    # validate installed
    if slug in get_installed():
        out(f"{MARK_INVALID} {st_emp(slug)} is already installed!", highlight=False)
        raise typer.Exit(code=-1)

    # download_jvm
    dist_info = get_dist(slug)
    dist_file = download_jvm(dist_info)

    # extract to work_dir
    work_dir = dist_file.parent / f"{slug}_{dist_info['version']}"
    work_dir.mkdir(parents=True, exist_ok=True)
    extract_archive(dist_file, work_dir)

    # move to install_dir
    installed_dir = move_jvm_dir(slug, work_dir)

    # update managed["installed"]
    add_installed(slug, dist_info, installed_dir)

    # remove cache
    if CLEAN_WORK_DIR:
        dist_file.unlink(missing_ok=True)
        shutil.rmtree(work_dir, ignore_errors=True)

    # installed jvm dir
    return installed_dir


def uninstall_jvm(slug: str) -> Path:
    log(f"uninstall_jvm()")
    log(f"  slug: {slug}")

    # validate slug
    get_slug(slug)

    # validate installed
    installed_info = get_installed_slug(slug)

    # delete jvm location
    jvm_location = installed_info["location"]
    shutil.rmtree(Path(jvm_location), ignore_errors=True)

    # update managed["installed"]
    del_installed(slug)

    # deleted jvm dir
    return jvm_location


def upgrade_jvm(slug: str) -> Path:
    log(f"upgrade_jvm()")
    log(f"  slug: {slug}")

    # validate slug
    get_slug(slug)

    # validate installed
    get_installed_slug(slug)

    # validate outdated
    if slug not in get_outdated():
        out(f"{MARK_CHECK} {st_emp(slug)} is already up-to-date.", highlight=False)
        raise typer.Exit()

    uninstall_jvm(slug)
    return install_jvm(slug)


def cleanup_cache():
    log(f"cleanup_cache()")

    for cached in CACHE_DIR.iterdir():
        if cached.is_dir():
            shutil.rmtree(cached)
        else:
            cached.unlink()
        log(f"Remove: {cached}")

