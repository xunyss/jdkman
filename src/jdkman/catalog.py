import json
import time

import requests

from .config import CATALOG_CACHE_FILE, CATALOG_CACHE_TTL, JVM_API_URL
from .console import out
from .utils import version_key


def fetch_artifacts() -> list[dict]:
    """
    {
        "checksum": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "created_at": "2025-03-28T22:02:46.826962",
        "features": [],
        "file_type": "zip",
        "image_type": "jre",
        "java_version": "17.0.2",
        "jvm_impl": "hotspot",
        "url": "https://cdn.azul.com/zulu/bin/zulu17.32.13-ca-jre17.0.2-macosx_aarch64.zip",
        "vendor": "zulu",
        "version": "17.32.13.0"
    }
    """
    if CATALOG_CACHE_FILE.exists() and (time.time() - CATALOG_CACHE_FILE.stat().st_mtime) < CATALOG_CACHE_TTL:
        artifacts = json.loads(CATALOG_CACHE_FILE.read_text())
    else:
        out("==> Fetching JVM Database...")
        response = requests.get(JVM_API_URL, timeout=30)
        response.raise_for_status()
        artifacts: list[dict] = response.json()

        CATALOG_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_CACHE_FILE.write_text(json.dumps(artifacts))

    return artifacts


def fetch_releases():
    """
    {
        "vendor": "zulu",
        "image_type": "jre",
        "features": [],
        "jvm_impl": "hotspot",
        "java_version": "17.0.2",
        "version": "17.32.13.0",
        "dists": [
            {
                "file_type": "zip",
                "url": "https://cdn.azul.com/zulu/bin/zulu17.32.13-ca-jre17.0.2-macosx_aarch64.zip",
                "checksum": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
                "created_at": "2025-03-28T22:02:46.826962"
            },
            ...
        ]
    }
    """
    _group_keys = ("vendor", "image_type", "features", "jvm_impl", "java_version", "version")
    _dist_keys = ("file_type", "url", "checksum", "created_at")
    releases: dict[tuple, dict] = {}
    for artifact in fetch_artifacts():
        key = (artifact["vendor"], artifact["image_type"], tuple(sorted(artifact["features"])), artifact["jvm_impl"], artifact["java_version"], artifact["version"])
        if key not in releases:
            releases[key] = {
                k: artifact[k]
                for k in _group_keys
            } | {
              "dists": []
            }

        releases[key]["dists"].append({
            k: artifact[k] for k in _dist_keys
        })

    return list(releases.values())


def make_slug(release_info: dict) -> str:
    """
    features cases: [
        "[]",
        ["javafx"]",                             # zulu
        ["crac"],                                # zulu
        ["jcef"]",                               # jetbrains
        ["lite"],                                # liberica
        ["javafx", "libericafx", "minimal-vm"],  # liberica
        ["notarized"]                            # kona
    ]
    jvm_impl cases: [
        "hotspot",
        "graalvm",
        "openj9"    # semeru (semeru 의 모든 dist 는 "openj9" 임)
    ]
    """
    feature = release_info["features"][0] if release_info["features"] and release_info["features"] != ["notarized"] else ""
    jvm_impl = release_info["jvm_impl"] if release_info["jvm_impl"] not in ["hotspot", "graalvm"] else ""

    parts = [release_info["vendor"]]
    if release_info["image_type"] == "jre":
        parts.append(release_info["image_type"])
    if feature:
        parts.append(feature)
    if jvm_impl:
        parts.append(jvm_impl)
    parts.append(str(release_info["major_version"]))

    return "-".join(parts)


def fetch_slugs():
    """
    {
        "zulu-jre-17": {
            "vendor": "zulu",
            "image_type": "jre",
            "features": [],
            "jvm_impl": "hotspot",
            "major_version": 17,
            "latest": "17.64.17.0",
            "versions": [
                {
                    "java_version": "17.0.2",
                    "version": "17.64.15.0",
                    "dists": [
                        {
                            "file_type": "tar.gz",
                            "url": "https://cdn.azul.com/zulu/bin/zulu17.64.15-ca-jre17.0.18-macosx_aarch64.tar.gz",
                            "checksum": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
                            "created_at": "2026-01-21T22:04:16.168823"
                        },
                        ...
                    ]
                },
                ...
            ]
        },
        ...
    }
    """
    slugs: dict[str, dict] = {}
    for release in fetch_releases():
        release_info = {
            "vendor": release["vendor"],
            "image_type": release["image_type"],
            "features": release["features"],
            "jvm_impl": release["jvm_impl"],
            "major_version": version_key(release["java_version"])[0][0],
        }
        slug = make_slug(release_info)
        if slug not in slugs:
            slugs[slug] = release_info | {
                "latest": release["version"],
                "versions": [],
            }
        else:
            if version_key(release["version"]) > version_key(slugs[slug]["latest"]):
                slugs[slug]["latest"] = release["version"]

        slugs[slug]["versions"].append({
            "java_version": release["java_version"],
            "version": release["version"],
            "dists": release["dists"]
        })

    return slugs


def sort_slugs(slugs: dict) -> dict:
    # 3. dists 정렬: created_at
    def sort_dists(versions):
        return [
            {
                **version,
                "dists": sorted(version["dists"], key=lambda x: x["created_at"])
            }
            for version in versions
        ]

    # 2. versions 정렬: version
    def sort_versions(versions):
        sorted_versions = sorted(versions, key=lambda x: version_key(x["version"]))
        return sort_dists(sorted_versions)

    # 1. slug 객체 정렬: vendor, image_type, features[0], major_version
    def slug_sort_key(slug_item):
        slug, slug_info = slug_item
        return (
            slug_info["vendor"],
            slug_info["image_type"],
            slug_info["features"][0] if slug_info["features"] else "",
            slug_info["major_version"],
        )

    return {
        slug: {
            **slug_info,
            "versions": sort_versions(slug_info["versions"])
        }
        for slug, slug_info in sorted(slugs.items(), key=slug_sort_key)
    }

