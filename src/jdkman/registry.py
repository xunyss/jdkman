import json
import re
import shutil
from pathlib import Path
from typing import Any

import typer
from rich.pretty import pretty_repr

from .catalog import fetch_slugs
from .config import CACHE_DIR, MANAGED_JVM_DB
from .console import log, out, RED_WARNING, st_div
from .utils import version_key


def _read_managed() -> dict[str, dict[str, Any]]:
    if MANAGED_JVM_DB.is_file():
        return json.loads(MANAGED_JVM_DB.read_text())
    return _write_managed({})


def _write_managed(managed: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    MANAGED_JVM_DB.write_text(json.dumps(managed))
    return managed


def managed_add(slug: str, dist_info: dict[str, Any], installed_dir: Path):
    log(f"managed_add()")
    log(f"  slug: {slug}")
    log(f"  dist_info: {pretty_repr(dist_info)}")
    log(f"  installed_dir: {installed_dir}")

    managed = _read_managed()
    managed[slug] = dist_info | {
        "location": str(installed_dir)
    }
    del managed[slug]["file_type"]
    del managed[slug]["url"]
    del managed[slug]["checksum"]
    del managed[slug]["created_at"]
    _write_managed(managed)


def managed_del(slug: str):
    log(f"managed_del()")
    log(f"  slug: {slug}")

    managed = _read_managed()
    managed.pop(slug)
    _write_managed(managed)


def managed_sort_key(managed_item: tuple[str, dict[str, Any]]):
    slug, managed_info = managed_item
    return (
        managed_info["vendor"],
        managed_info["image_type"],
        managed_info["features"][0] if managed_info["features"] else "",
        managed_info["jvm_impl"],
        managed_info["major_version"],
    )


def get_installed(sort: bool = False) -> dict[str, dict[str, Any]]:
    log(f"get_installed()")
    log(f"  sort: {sort}")

    managed = _read_managed()
    return dict(sorted(managed.items(), key=managed_sort_key)) if sort else managed


def get_outdated() -> dict[str, dict[str, Any]]:
    log(f"get_outdated()")

    return {
        slug: {
            "installed": managed_info["version"],
            "latest": slug_info["latest"],
        }
        for slug, managed_info in get_installed().items()
        if version_key(managed_info["version"]) < version_key((slug_info := get_slug(slug))["latest"])
    }


def list_vendors() -> list[str]:
    log(f"list_vendors()")

    return sorted({slug_info["vendor"] for slug_info in fetch_slugs().values()})


def list_editions() -> list[str]:
    log(f"list_editions()")

    # mise ls-remote java | grep -o '^[a-zA-Z0-9-]*-[a-zA-Z0-9]*' | sed 's/-[0-9].*//' | sort -u | grep -v '^$'
    return list(dict.fromkeys(re.sub(r'-\d+$', '', s) for s in fetch_slugs(sort=True).keys()))


def get_slugs(include_jre: bool, include_feature: bool, major_version: str | None) -> dict[str, dict[str, Any]]:
    log(f"get_slugs()")
    log(f"  include_jre: {include_jre}")
    log(f"  include_feature: {include_feature}")
    log(f"  major_version: {major_version}")

    return {
        slug: slug_info
        for slug, slug_info in fetch_slugs(sort=True).items()
        if (include_jre or slug_info["image_type"] == "jdk")
           and (include_feature or not slug_info["features"] or slug_info["features"] == ["notarized"])
           and (not major_version or major_version == str(slug_info["major_version"]))
    }


def get_slug(slug: str) -> dict[str, Any]:
    log(f"get_slug()")
    log(f"  slug: {slug}")

    slugs = fetch_slugs()
    if slug not in slugs:
        out(f"{RED_WARNING} {st_div(slug)} is invalid!", highlight=False)
        raise typer.Exit(code=1)

    return slugs.get(slug)


def get_dist(slug: str, version: str | None = None) -> dict[str, Any]:
    log(f"get_dist()")
    log(f"  slug: {slug}")
    log(f"  version: {version}")

    slug_info = get_slug(slug)
    search_version = version if version else slug_info["latest"]
    versions = slug_info["versions"]
    target_version = next(version for version in versions if version["version"] == search_version)
    target_dist = next(dist for dist in target_version["dists"] if dist["file_type"] == "tar.gz")

    return {
        "vendor": slug_info["vendor"],
        "image_type": slug_info["image_type"],
        "features": slug_info["features"],
        "jvm_impl": slug_info["jvm_impl"],
        "major_version": slug_info["major_version"],
        "java_version": target_version["java_version"],
        "version": target_version["version"],
    } | target_dist


def cleanup_cache():
    log(f"cleanup_cache()")

    for cached in CACHE_DIR.iterdir():
        shutil.rmtree(cached) if cached.is_dir() else cached.unlink()
        log(f"Remove: {cached}")

