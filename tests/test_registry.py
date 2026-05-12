import json
from pathlib import Path

import pytest

import jdkman.registry as registry


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def managed_db(tmp_path, monkeypatch):
    """Pre-initialized DB with proper structure: {installed, aliases}."""
    db = tmp_path / ".jdkman"
    db.write_text(json.dumps({"installed": {}, "aliases": {}}))
    monkeypatch.setattr(registry, "MANAGED_JVM_DB", db)
    return db


@pytest.fixture
def empty_managed_db(tmp_path, monkeypatch):
    """DB path with no file — tests missing-file behavior."""
    db = tmp_path / ".jdkman"
    monkeypatch.setattr(registry, "MANAGED_JVM_DB", db)
    return db


@pytest.fixture
def sample_slugs():
    def _info(vendor, image_type="jdk", features=None, major_version=21):
        return {
            "vendor": vendor,
            "image_type": image_type,
            "features": features or [],
            "jvm_impl": "hotspot",
            "major_version": major_version,
            "latest": "21.0.5",
            "versions": [],
        }
    return {
        "zulu-21":        _info("zulu"),
        "zulu-jre-21":    _info("zulu", image_type="jre"),
        "temurin-21":     _info("temurin"),
        "zulu-17":        _info("zulu", major_version=17),
    }


@pytest.fixture
def sample_dist():
    return {
        "vendor": "zulu",
        "image_type": "jdk",
        "features": [],
        "jvm_impl": "hotspot",
        "major_version": 21,
        "java_version": "21.0.5",
        "version": "21.0.5+11",
        "file_type": "tar.gz",
        "url": "https://example.com/zulu.tar.gz",
        "checksum": "sha256:abc123",
        "created_at": "2024-01-01T00:00:00",
    }


# ── _read_managed ─────────────────────────────────────────────────────────────

def test_read_managed_creates_file_when_missing(empty_managed_db):
    expected = {"installed": {}, "aliases": {}}
    result = registry._read_managed()
    assert result == expected
    assert empty_managed_db.exists()
    assert json.loads(empty_managed_db.read_text()) == expected


def test_read_managed_returns_existing_data(managed_db):
    data = {"installed": {"zulu-21": {"version": "21.0.5"}}, "aliases": {}}
    managed_db.write_text(json.dumps(data))
    assert registry._read_managed() == data


# ── _write_managed ────────────────────────────────────────────────────────────

def test_write_managed_persists(managed_db):
    data = {"installed": {"temurin-17": {"version": "17.0.11"}}, "aliases": {}}
    registry._write_managed(data)
    assert json.loads(managed_db.read_text()) == data


def test_write_managed_returns_data(managed_db):
    data = {"installed": {"zulu-21": {"version": "21.0.5"}}, "aliases": {}}
    result = registry._write_managed(data)
    assert result == data


# ── add_installed / del_installed ─────────────────────────────────────────────

def test_add_installed_stored_correctly(managed_db, sample_dist):
    install_dir = Path("/Library/Java/JavaVirtualMachines/zulu-21.jdk")
    registry.add_installed("zulu-21", sample_dist, install_dir)

    installed = registry.get_installed()
    assert "zulu-21" in installed
    assert installed["zulu-21"]["version"] == "21.0.5+11"
    assert installed["zulu-21"]["location"] == str(install_dir)


def test_add_installed_removes_transient_fields(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/some/path"))

    entry = registry.get_installed()["zulu-21"]
    for removed in ("file_type", "url", "checksum", "created_at"):
        assert removed not in entry


def test_del_installed(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/some/path"))
    registry.del_installed("zulu-21")
    assert "zulu-21" not in registry.get_installed()


def test_del_installed_leaves_other_entries(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/path/a"))
    registry.add_installed("temurin-17", {**sample_dist, "version": "17.0.11"}, Path("/path/b"))
    registry.del_installed("zulu-21")

    installed = registry.get_installed()
    assert "zulu-21" not in installed
    assert "temurin-17" in installed


# ── add_aliases / del_aliases ─────────────────────────────────────────────────

def test_add_aliases(managed_db):
    registry.add_alias("21", "zulu-21")
    assert registry.get_aliases()["21"] == "zulu-21"


def test_add_aliases_multiple(managed_db):
    registry.add_alias("21", "zulu-21")
    registry.add_alias("lts", "temurin-21")
    aliases = registry.get_aliases()
    assert aliases["21"] == "zulu-21"
    assert aliases["lts"] == "temurin-21"


def test_del_aliases(managed_db):
    registry.add_alias("21", "zulu-21")
    registry.del_alias("21")
    assert "21" not in registry.get_aliases()


def test_del_aliases_leaves_other_entries(managed_db):
    registry.add_alias("21", "zulu-21")
    registry.add_alias("lts", "temurin-21")
    registry.del_alias("21")
    assert "21" not in registry.get_aliases()
    assert registry.get_aliases()["lts"] == "temurin-21"


# ── get_aliases ───────────────────────────────────────────────────────────────

def test_get_aliases_unsorted(managed_db):
    registry.add_alias("zz", "zulu-21")
    registry.add_alias("aa", "temurin-21")
    aliases = registry.get_aliases(sort=False)
    # 순서 보장 없음 — 키 존재만 확인
    assert set(aliases.keys()) == {"zz", "aa"}


def test_get_aliases_sorted(managed_db):
    registry.add_alias("zz", "zulu-21")
    registry.add_alias("aa", "temurin-21")
    registry.add_alias("mm", "liberica-21")
    aliases = registry.get_aliases(sort=True)
    assert list(aliases.keys()) == ["aa", "mm", "zz"]


# ── get_installed ─────────────────────────────────────────────────────────────

def test_get_installed_empty(managed_db):
    assert registry.get_installed() == {}


def test_get_installed_sorted(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/path/z"))
    registry.add_installed("temurin-21", {**sample_dist, "vendor": "temurin"}, Path("/path/t"))
    installed = registry.get_installed(sort=True)
    assert list(installed.keys()) == ["temurin-21", "zulu-21"]


# ── get_installed_slug ────────────────────────────────────────────────────────

def test_get_installed_slug_found(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/path/zulu"))
    info = registry.get_installed_slug("zulu-21")
    assert info["version"] == "21.0.5+11"


# ── get_managed ───────────────────────────────────────────────────────────────

def test_get_managed_flat(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/path"))
    registry.add_alias("21", "zulu-21")
    merged = registry.get_managed()
    assert "zulu-21" in merged
    assert "21" in merged


def test_get_managed_divided(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/path"))
    registry.add_alias("21", "zulu-21")
    result = registry.get_managed(divided=True)
    assert "installed" in result
    assert "aliases" in result
    assert "zulu-21" in result["installed"]
    assert "21" in result["aliases"]


def test_get_managed_sorted_divided(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/path/z"))
    registry.add_installed("temurin-21", {**sample_dist, "vendor": "temurin"}, Path("/path/t"))
    result = registry.get_managed(sort=True, divided=True)
    assert list(result["installed"].keys()) == ["temurin-21", "zulu-21"]


# ── installed_sort_key ────────────────────────────────────────────────────────

def test_installed_sort_key_ordering():
    items = [
        ("zulu-21",    {"vendor": "zulu",    "image_type": "jdk", "features": [],         "jvm_impl": "hotspot", "major_version": 21}),
        ("temurin-21", {"vendor": "temurin", "image_type": "jdk", "features": [],         "jvm_impl": "hotspot", "major_version": 21}),
        ("zulu-17",    {"vendor": "zulu",    "image_type": "jdk", "features": [],         "jvm_impl": "hotspot", "major_version": 17}),
    ]
    sorted_items = sorted(items, key=registry.installed_sort_key)
    slugs = [s for s, _ in sorted_items]
    assert slugs == ["temurin-21", "zulu-17", "zulu-21"]


# ── list_vendors ──────────────────────────────────────────────────────────────

def test_list_vendors(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda: sample_slugs)
    result = registry.list_vendors()
    assert result == ["temurin", "zulu"]


def test_list_vendors_unique(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda: sample_slugs)
    result = registry.list_vendors()
    assert len(result) == len(set(result))


# ── list_editions ─────────────────────────────────────────────────────────────

def test_list_editions(monkeypatch):
    slugs = {
        "temurin-21":     {"vendor": "temurin", "image_type": "jdk", "features": [], "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
        "zulu-21":        {"vendor": "zulu",    "image_type": "jdk", "features": [], "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
        "zulu-17":        {"vendor": "zulu",    "image_type": "jdk", "features": [], "jvm_impl": "hotspot", "major_version": 17, "latest": "17.0.11", "versions": []},
        "zulu-javafx-21": {"vendor": "zulu",    "image_type": "jdk", "features": ["javafx"], "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
    }
    monkeypatch.setattr(registry, "fetch_slugs", lambda sort=False: slugs)
    editions = registry.list_editions()
    assert "temurin" in editions
    assert "zulu" in editions
    assert "zulu-javafx" in editions
    # major version 숫자 suffix는 제거됨
    assert not any(e.endswith("-21") or e.endswith("-17") for e in editions)


def test_list_editions_no_duplicates(monkeypatch):
    slugs = {
        "zulu-21": {"vendor": "zulu", "image_type": "jdk", "features": [], "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
        "zulu-17": {"vendor": "zulu", "image_type": "jdk", "features": [], "jvm_impl": "hotspot", "major_version": 17, "latest": "17.0.11", "versions": []},
    }
    monkeypatch.setattr(registry, "fetch_slugs", lambda sort=False: slugs)
    editions = registry.list_editions()
    assert editions.count("zulu") == 1


# ── get_slugs ─────────────────────────────────────────────────────────────────

def test_get_slugs_excludes_jre_by_default(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda sort=False: sample_slugs)
    result = registry.get_slugs(include_jre=False, include_feature=False, major_version=None)
    assert all(info["image_type"] == "jdk" for info in result.values())


def test_get_slugs_includes_jre_when_requested(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda sort=False: sample_slugs)
    result = registry.get_slugs(include_jre=True, include_feature=False, major_version=None)
    image_types = {info["image_type"] for info in result.values()}
    assert "jre" in image_types


def test_get_slugs_filters_by_major_version(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda sort=False: sample_slugs)
    result = registry.get_slugs(include_jre=True, include_feature=True, major_version="17")
    assert all(info["major_version"] == 17 for info in result.values())


def test_get_slugs_excludes_feature_by_default(monkeypatch):
    slugs = {
        "zulu-21":        {"vendor": "zulu", "image_type": "jdk", "features": [],         "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
        "zulu-javafx-21": {"vendor": "zulu", "image_type": "jdk", "features": ["javafx"], "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
    }
    monkeypatch.setattr(registry, "fetch_slugs", lambda sort=False: slugs)
    result = registry.get_slugs(include_jre=False, include_feature=False, major_version=None)
    assert "zulu-javafx-21" not in result
    assert "zulu-21" in result


def test_get_slugs_notarized_included_without_feature_flag(monkeypatch):
    slugs = {
        "kona-21": {"vendor": "kona", "image_type": "jdk", "features": ["notarized"], "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
    }
    monkeypatch.setattr(registry, "fetch_slugs", lambda sort=False: slugs)
    result = registry.get_slugs(include_jre=False, include_feature=False, major_version=None)
    assert "kona-21" in result


# ── get_outdated ──────────────────────────────────────────────────────────────

def test_get_outdated_returns_stale(managed_db, sample_dist, monkeypatch):
    # 설치된 버전은 21.0.3, 최신은 21.0.5
    old_dist = {**sample_dist, "version": "21.0.3+9", "java_version": "21.0.3"}
    registry.add_installed("zulu-21", old_dist, Path("/path"))

    slugs = {
        "zulu-21": {
            "vendor": "zulu", "image_type": "jdk", "features": [], "jvm_impl": "hotspot",
            "major_version": 21, "latest": "21.0.5+11", "versions": [],
        }
    }
    monkeypatch.setattr(registry, "fetch_slugs", lambda: slugs)

    outdated = registry.get_outdated()
    assert "zulu-21" in outdated
    assert outdated["zulu-21"]["installed"] == "21.0.3+9"
    assert outdated["zulu-21"]["latest"] == "21.0.5+11"


def test_get_outdated_excludes_current(managed_db, sample_dist, monkeypatch):
    # 설치 버전 == 최신 버전
    registry.add_installed("zulu-21", sample_dist, Path("/path"))

    slugs = {
        "zulu-21": {
            "vendor": "zulu", "image_type": "jdk", "features": [], "jvm_impl": "hotspot",
            "major_version": 21, "latest": "21.0.5+11", "versions": [],
        }
    }
    monkeypatch.setattr(registry, "fetch_slugs", lambda: slugs)

    outdated = registry.get_outdated()
    assert "zulu-21" not in outdated


# ── get_dist ──────────────────────────────────────────────────────────────────

def test_get_dist_returns_merged_info(monkeypatch):
    slugs = {
        "zulu-21": {
            "vendor": "zulu",
            "image_type": "jdk",
            "features": [],
            "jvm_impl": "hotspot",
            "major_version": 21,
            "latest": "21.0.5+11",
            "versions": [
                {
                    "java_version": "21.0.5",
                    "version": "21.0.5+11",
                    "dists": [
                        {"file_type": "tar.gz", "url": "https://example.com/zulu.tar.gz", "checksum": "abc", "created_at": "2024-01-01"},
                        {"file_type": "zip",    "url": "https://example.com/zulu.zip",    "checksum": "xyz", "created_at": "2024-01-02"},
                    ],
                }
            ],
        }
    }
    monkeypatch.setattr(registry, "fetch_slugs", lambda: slugs)

    dist = registry.get_dist("zulu-21")
    assert dist["vendor"] == "zulu"
    assert dist["version"] == "21.0.5+11"
    assert dist["file_type"] == "tar.gz"
    assert dist["url"] == "https://example.com/zulu.tar.gz"

