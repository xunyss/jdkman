import json
from pathlib import Path

import pytest

import jdkman.registry as registry


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def managed_db(tmp_path, monkeypatch):
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


# ── _read_managed / _write_managed ───────────────────────────────────────────

def test_read_managed_creates_file_when_missing(managed_db):
    result = registry._read_managed()
    assert result == {}
    assert managed_db.exists()
    assert json.loads(managed_db.read_text()) == {}


def test_read_managed_returns_existing_data(managed_db):
    data = {"zulu-21": {"version": "21.0.5", "location": "/path"}}
    managed_db.write_text(json.dumps(data))
    assert registry._read_managed() == data


def test_write_managed_persists(managed_db):
    data = {"temurin-17": {"version": "17.0.11", "location": "/path"}}
    registry._write_managed(data)
    assert json.loads(managed_db.read_text()) == data


def test_write_managed_returns_data(managed_db):
    data = {"zulu-21": {"version": "21.0.5"}}
    result = registry._write_managed(data)
    assert result == data


# ── managed_add / managed_del ────────────────────────────────────────────────

def test_managed_add(managed_db, sample_dist):
    install_dir = Path("/Library/Java/JavaVirtualMachines/zulu-21.jdk")
    registry.add_installed("zulu-21", sample_dist, install_dir)

    stored = registry._read_managed()
    assert "zulu-21" in stored

    entry = stored["zulu-21"]
    assert entry["version"] == "21.0.5+11"
    assert entry["location"] == str(install_dir)
    # 설치 후 불필요한 필드는 제거됨
    for removed in ("file_type", "url", "checksum", "created_at"):
        assert removed not in entry


def test_managed_del(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/some/path"))
    registry.del_installed("zulu-21")
    assert "zulu-21" not in registry._read_managed()


def test_managed_del_other_entries_intact(managed_db, sample_dist):
    registry.add_installed("zulu-21", sample_dist, Path("/path/a"))
    registry.add_installed("temurin-17", {**sample_dist, "version": "17.0.11"}, Path("/path/b"))
    registry.del_installed("zulu-21")

    stored = registry._read_managed()
    assert "zulu-21" not in stored
    assert "temurin-17" in stored


# ── list_vendors ─────────────────────────────────────────────────────────────

def test_list_vendors(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda: sample_slugs)
    result = registry.list_vendors()
    assert result == ["temurin", "zulu"]


def test_list_vendors_unique(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda: sample_slugs)
    result = registry.list_vendors()
    assert len(result) == len(set(result))


# ── get_slugs ────────────────────────────────────────────────────────────────

def test_get_slugs_excludes_jre_by_default(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda: sample_slugs)
    result = registry.get_slugs(include_jre=False, include_feature=False, major_version=None)
    assert all(info["image_type"] == "jdk" for info in result.values())


def test_get_slugs_includes_jre_when_requested(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda: sample_slugs)
    result = registry.get_slugs(include_jre=True, include_feature=False, major_version=None)
    image_types = {info["image_type"] for info in result.values()}
    assert "jre" in image_types


def test_get_slugs_filters_by_major_version(monkeypatch, sample_slugs):
    monkeypatch.setattr(registry, "fetch_slugs", lambda: sample_slugs)
    result = registry.get_slugs(include_jre=True, include_feature=True, major_version="17")
    assert all(info["major_version"] == 17 for info in result.values())


def test_get_slugs_excludes_feature_by_default(monkeypatch):
    slugs = {
        "zulu-21":        {"vendor": "zulu", "image_type": "jdk", "features": [],         "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
        "zulu-javafx-21": {"vendor": "zulu", "image_type": "jdk", "features": ["javafx"], "jvm_impl": "hotspot", "major_version": 21, "latest": "21.0.5", "versions": []},
    }
    monkeypatch.setattr(registry, "fetch_slugs", lambda: slugs)
    result = registry.get_slugs(include_jre=False, include_feature=False, major_version=None)
    assert "zulu-javafx-21" not in result
    assert "zulu-21" in result

