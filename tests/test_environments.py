"""
Tests for jdkman/environments.py

주의: 실제 파일시스템의 ~/.java-version, ~/.config/jdkman 등을 건드리지 않도록
모든 경로를 monkeypatch로 tmp_path 아래로 리다이렉트한다.
"""
import json
from pathlib import Path

import pytest
import typer

import jdkman.environments as environments
import jdkman.registry as registry


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def managed_db(tmp_path, monkeypatch):
    """설치된 JVM이 하나 있는 DB."""
    db = tmp_path / ".jdkman"
    db.write_text(json.dumps({
        "installed": {
            "zulu-21": {
                "vendor": "zulu",
                "image_type": "jdk",
                "features": [],
                "jvm_impl": "hotspot",
                "major_version": 21,
                "java_version": "21.0.5",
                "version": "21.0.5+11",
                "location": str(tmp_path / "zulu-21.jdk"),
            }
        },
        "aliases": {}
    }))
    monkeypatch.setattr(registry, "MANAGED_JVM_DB", db)
    return db


@pytest.fixture
def global_env_file(tmp_path, monkeypatch):
    """글로벌 .java-version 파일 경로를 tmp로 리다이렉트."""
    env_file = tmp_path / "config" / ".java-version"
    env_file.parent.mkdir(parents=True)
    monkeypatch.setattr(environments, "GLOBAL_ENV_FILE", env_file)
    return env_file


# ── find_env_file ─────────────────────────────────────────────────────────────

def test_find_env_file_returns_global(global_env_file):
    result = environments.find_env_file(is_global=True)
    assert result == global_env_file


def test_find_env_file_returns_local_in_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = environments.find_env_file(is_global=False)
    assert result == tmp_path / ".java-version"


# ── get_env_tag_local ─────────────────────────────────────────────────────────

def test_get_env_tag_local_finds_in_cwd(monkeypatch, tmp_path):
    (tmp_path / ".java-version").write_text("zulu-21\n")
    monkeypatch.chdir(tmp_path)
    tag, src = environments.get_env_tag_local()
    assert tag == "zulu-21"
    assert src == tmp_path / ".java-version"


def test_get_env_tag_local_strips_whitespace(monkeypatch, tmp_path):
    (tmp_path / ".java-version").write_text("  temurin-17  \n")
    monkeypatch.chdir(tmp_path)
    tag, _ = environments.get_env_tag_local()
    assert tag == "temurin-17"


def test_get_env_tag_local_finds_in_parent_dir(monkeypatch, tmp_path):
    (tmp_path / ".java-version").write_text("temurin-17\n")
    subdir = tmp_path / "project" / "src" / "main"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)
    tag, src = environments.get_env_tag_local()
    assert tag == "temurin-17"
    assert src == tmp_path / ".java-version"


def test_get_env_tag_local_child_overrides_parent(monkeypatch, tmp_path):
    (tmp_path / ".java-version").write_text("temurin-17\n")
    subdir = tmp_path / "project"
    subdir.mkdir()
    (subdir / ".java-version").write_text("zulu-21\n")
    monkeypatch.chdir(subdir)
    tag, _ = environments.get_env_tag_local()
    assert tag == "zulu-21"


def test_get_env_tag_local_empty_file_skipped(monkeypatch, tmp_path):
    (tmp_path / ".java-version").write_text("")
    monkeypatch.chdir(tmp_path)
    tag, src = environments.get_env_tag_local()
    assert tag is None
    assert src is None


def test_get_env_tag_local_no_file_returns_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    tag, src = environments.get_env_tag_local()
    assert tag is None
    assert src is None


# ── get_env_tag_global ────────────────────────────────────────────────────────

def test_get_env_tag_global_returns_tag(global_env_file):
    global_env_file.write_text("zulu-21\n")
    tag, src = environments.get_env_tag_global()
    assert tag == "zulu-21"
    assert src == global_env_file


def test_get_env_tag_global_strips_whitespace(global_env_file):
    global_env_file.write_text("  temurin-17  \n")
    tag, _ = environments.get_env_tag_global()
    assert tag == "temurin-17"


def test_get_env_tag_global_no_file_returns_none(global_env_file):
    # 파일 없음 — 부모 디렉토리만 존재
    tag, src = environments.get_env_tag_global()
    assert tag is None
    assert src is None


def test_get_env_tag_global_empty_file_returns_none(global_env_file):
    global_env_file.write_text("")
    tag, src = environments.get_env_tag_global()
    assert tag is None
    assert src is None


# ── get_env_tag (combined) ────────────────────────────────────────────────────

def test_get_env_tag_returns_both_when_set(managed_db, global_env_file, monkeypatch, tmp_path):
    global_env_file.write_text("zulu-21\n")
    (tmp_path / ".java-version").write_text("temurin-17\n")
    monkeypatch.chdir(tmp_path)

    result = environments.get_env_tag()
    assert result["global"]["tag"] == "zulu-21"
    assert result["global"]["source"] == global_env_file
    assert result["local"]["tag"] == "temurin-17"


def test_get_env_tag_returns_none_when_not_set(managed_db, global_env_file, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = environments.get_env_tag()
    assert result["global"]["tag"] is None
    assert result["local"]["tag"] is None


def test_get_env_tag_only_global_set(managed_db, global_env_file, monkeypatch, tmp_path):
    global_env_file.write_text("zulu-21\n")
    monkeypatch.chdir(tmp_path)
    result = environments.get_env_tag()
    assert result["global"]["tag"] == "zulu-21"
    assert result["local"]["tag"] is None


# ── set_env_tag ───────────────────────────────────────────────────────────────

def test_set_env_tag_local_creates_file(managed_db, global_env_file, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    env_file = environments.set_env_tag("zulu-21", is_global=False)
    assert env_file == tmp_path / ".java-version"
    assert env_file.read_text().strip() == "zulu-21"


def test_set_env_tag_global_creates_file(managed_db, global_env_file):
    env_file = environments.set_env_tag("zulu-21", is_global=True)
    assert env_file == global_env_file
    assert env_file.read_text().strip() == "zulu-21"


def test_set_env_tag_invalid_slug_exits(managed_db, global_env_file, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit):
        environments.set_env_tag("nonexistent-99", is_global=False)


def test_set_env_tag_alias_accepted(managed_db, global_env_file, monkeypatch, tmp_path):
    # alias "21" → "zulu-21" 이 managed 에 있으면 set_env_tag 가 허용
    registry.add_aliases("21", "zulu-21")
    monkeypatch.chdir(tmp_path)
    env_file = environments.set_env_tag("21", is_global=False)
    assert env_file.read_text().strip() == "21"


# ── unset_env_tag ─────────────────────────────────────────────────────────────

def test_unset_env_tag_clears_local(managed_db, global_env_file, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".java-version").write_text("zulu-21\n")
    env_file = environments.unset_env_tag(is_global=False)
    assert env_file.read_text() == ""


def test_unset_env_tag_clears_global(managed_db, global_env_file):
    global_env_file.write_text("zulu-21\n")
    env_file = environments.unset_env_tag(is_global=True)
    assert env_file.read_text() == ""


# ── set_env_alias ─────────────────────────────────────────────────────────────

def test_set_env_alias_creates_alias(managed_db, monkeypatch):
    monkeypatch.setattr(environments, "get_slug", lambda slug: {"vendor": "zulu"})
    environments.set_env_alias("21", "zulu-21")
    assert registry.get_aliases().get("21") == "zulu-21"


def test_set_env_alias_conflicts_with_installed_slug(managed_db, monkeypatch):
    monkeypatch.setattr(environments, "get_slug", lambda slug: {"vendor": "zulu"})
    # "zulu-21" 은 이미 installed 에 존재하므로 alias 이름으로 쓸 수 없음
    with pytest.raises(typer.Exit):
        environments.set_env_alias("zulu-21", "zulu-21")


# ── unset_env_alias ───────────────────────────────────────────────────────────

def test_unset_env_alias_removes_alias(managed_db):
    registry.add_aliases("21", "zulu-21")
    environments.unset_env_alias("21")
    assert "21" not in registry.get_aliases()


def test_unset_env_alias_not_found_exits(managed_db):
    with pytest.raises(typer.Exit):
        environments.unset_env_alias("nonexistent")


# ── get_env_aliases ───────────────────────────────────────────────────────────

def test_get_env_aliases_returns_list(managed_db):
    registry.add_aliases("21", "zulu-21")
    registry.add_aliases("lts", "zulu-21")
    aliases = environments.get_env_aliases()
    alias_names = [a["alias"] for a in aliases]
    assert "21" in alias_names
    assert "lts" in alias_names


def test_get_env_aliases_includes_version(managed_db):
    registry.add_aliases("21", "zulu-21")
    aliases = environments.get_env_aliases()
    entry = next(a for a in aliases if a["alias"] == "21")
    assert entry["slug"] == "zulu-21"
    assert entry["version"] == "21.0.5+11"


def test_get_env_aliases_empty(managed_db):
    result = environments.get_env_aliases()
    assert result == []


def test_get_env_aliases_uninstalled_slug_version_is_none(managed_db):
    # alias 가 설치되지 않은 slug 를 가리킬 때 version은 None
    registry.add_aliases("ghost", "liberica-21")
    aliases = environments.get_env_aliases()
    entry = next(a for a in aliases if a["alias"] == "ghost")
    assert entry["version"] is None
