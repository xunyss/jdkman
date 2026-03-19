import json
import shutil
from pathlib import Path

from .catalog import fetch_slugs, sort_slugs
from .config import CACHE_DIR, MANAGED_JVM_DB
from .console import log, out
from .utils import version_key


def _read_managed() -> dict:
    if MANAGED_JVM_DB.is_file():
        return json.loads(MANAGED_JVM_DB.read_text())
    return _write_managed({})


def _write_managed(managed: dict) -> dict:
    MANAGED_JVM_DB.write_text(json.dumps(managed))
    return managed


def managed_add(slug:str, dist_info: dict, installed_dir: Path):
    managed = _read_managed()
    managed[slug] = dist_info | {
        "location": str(installed_dir)
    }
    del managed[slug]["file_type"]
    del managed[slug]["url"]
    del managed[slug]["checksum"]
    del managed[slug]["created_at"]
    _write_managed(managed)


def managed_del(slug:str):
    managed = _read_managed()
    managed.pop(slug)
    _write_managed(managed)


def get_installed():
    return _read_managed()


def get_outdated():
    return {
        slug: {
            "installed": managed_info["version"],
            "latest": slug_info["latest"],
        }
        for slug, managed_info in get_installed().items()
        if version_key(managed_info["version"]) < version_key((slug_info := get_slug(slug))["latest"])
    }


def cleanup_cache():
    log(f"cleanup_cache()")

    for cached in CACHE_DIR.iterdir():
        shutil.rmtree(cached) if cached.is_dir() else cached.unlink()
        out(f"Remove: {cached}")


def list_vendors() -> list[str]:
    return sorted({slug_info["vendor"] for slug_info in fetch_slugs().values()})


def get_slugs(include_jre: bool, include_feature: bool, major_version: str | None) -> dict[str, dict]:
    return {
        slug: slug_info
        for slug, slug_info in sort_slugs(fetch_slugs()).items()
        if (include_jre or slug_info["image_type"] == "jdk")
           and (include_feature or not slug_info["features"])
           and (not major_version or major_version == str(slug_info["major_version"]))
    }


def get_slug(slug: str) -> dict:
    return fetch_slugs().get(slug)


def get_dist(slug: str, version: str | None = None) -> dict:
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

