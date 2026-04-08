import json
import re
from pathlib import Path
from typing import Any

import typer
from rich.pretty import pretty_repr

from .catalog import fetch_slugs
from .config import MANAGED_JVM_DB
from .console import log, out, MARK_INVALID, st_emp, st_div
from .utils import version_key


_managed_cache: dict[str, dict[str, Any]] = {}

def _read_managed() -> dict[str, dict[str, Any]]:
    if _managed_cache:
        return _managed_cache
    if MANAGED_JVM_DB.is_file():
        return json.loads(MANAGED_JVM_DB.read_text())
    return _write_managed({})

def _write_managed(managed: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    global _managed_cache
    _managed_cache = managed
    MANAGED_JVM_DB.write_text(json.dumps(managed))
    return managed


def add_installed(slug: str, dist_info: dict[str, Any], installed_dir: Path):
    log(f"add_installed()")
    log(f"  slug: {slug}")
    log(f"  dist_info: {pretty_repr(dist_info)}")
    log(f"  installed_dir: {installed_dir}")

    managed = _read_managed()
    installed = managed["installed"]
    installed[slug] = dist_info | {
        "location": str(installed_dir)
    }

    del installed[slug]["file_type"]
    del installed[slug]["url"]
    del installed[slug]["checksum"]
    del installed[slug]["created_at"]

    _write_managed(managed)


def del_installed(slug: str):
    log(f"del_installed()")
    log(f"  slug: {slug}")

    managed = _read_managed()
    installed = managed["installed"]
    installed.pop(slug)

    _write_managed(managed)


def add_alias(alias: str, slug: str):
    log(f"add_alias()")
    log(f"  alias: {alias}")
    log(f"  slug: {slug}")

    managed = _read_managed()
    aliases = managed["aliases"]
    aliases[alias] = slug

    _write_managed(managed)


def del_alias(alias: str):
    log(f"del_alias()")
    log(f"  alias: {alias}")

    managed = _read_managed()
    aliases = managed["aliases"]
    aliases.pop(alias)

    _write_managed(managed)


def installed_sort_key(installed_item: tuple[str, dict[str, Any]]):
    slug, installed_info = installed_item
    return (
        installed_info["vendor"],
        installed_info["image_type"],
        installed_info["features"][0] if installed_info["features"] else "",
        installed_info["jvm_impl"],
        installed_info["major_version"],
    )


def get_installed(sort: bool = False) -> dict[str, dict[str, Any]]:
    log(f"get_installed()")
    log(f"  sort: {sort}")

    managed = _read_managed()
    installed = managed["installed"]
    return dict(sorted(installed.items(), key=installed_sort_key)) if sort else installed


def get_aliases(sort: bool = False) -> dict[str, str]:
    log(f"get_aliases()")

    managed = _read_managed()
    aliases = managed["aliases"]
    return dict(sorted(aliases.items())) if sort else aliases


def get_managed(sort: bool = False, divided: bool = False) -> dict[str, Any]:
    log(f"get_managed()")

    managed = _read_managed()
    installed: dict[str, Any] = managed["installed"]
    aliases: dict[str, str] = managed["aliases"]

    if sort:
        installed = dict(sorted(installed.items(), key=installed_sort_key))
        aliases = dict(sorted(aliases.items()))

    if divided:
        return {
            "installed": installed,
            "aliases": aliases,
        }
    return installed | aliases


def get_installed_slug(slug: str):
    log(f"get_installed_slug()")
    log(f"  slug: {slug}")

    installed = get_installed()
    if slug not in installed:
        out(f"{MARK_INVALID} {st_emp(slug)} is not installed!", highlight=False)
        raise typer.Exit(code=-1)

    return installed[slug]


def get_outdated() -> dict[str, dict[str, Any]]:
    log(f"get_outdated()")

    slugs = fetch_slugs()
    return {
        slug: {
            "installed": managed_info["version"],
            "latest": slugs[slug]["latest"],
        }
        for slug, managed_info in get_installed().items()
        if version_key(managed_info["version"]) < version_key(slugs[slug]["latest"])
    }


def list_vendors() -> list[str]:
    log(f"list_vendors()")

    return sorted({slug_info["vendor"] for slug_info in fetch_slugs().values()})


def list_editions() -> list[str]:
    log(f"list_editions()")

    # mise ls-remote java | grep -o '^[a-zA-Z0-9-]*-[a-zA-Z0-9]*' | sed 's/-[0-9].*//' | sort -u | grep -v '^$'
    return list(dict.fromkeys(re.sub(r'-\d+$', '', slug) for slug in fetch_slugs(sort=True).keys()))


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
        out(f"{MARK_INVALID} {st_div(slug)} is invalid!", highlight=False)
        raise typer.Exit(code=-1)

    return slugs[slug]


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

