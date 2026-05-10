"""
Tests for jdkman/env_hook.py

env_hook 은 stdlib만 사용하는 독립 모듈이다.
Path.home() 과 platform.system() 을 monkeypatch 하여
실제 홈 디렉토리나 플랫폼에 영향 없이 테스트한다.
"""
import json
import sys
from pathlib import Path

import pytest

from jdkman.env_hook import main


# ── helpers ───────────────────────────────────────────────────────────────────

def _setup_db(home: Path, is_macos: bool, installed: dict, aliases: dict = None) -> Path:
    """tmp home 아래에 managed DB 파일을 생성한다."""
    db_dir = home / ".config" / "jdkman"
    db_dir.mkdir(parents=True, exist_ok=True)
    db = db_dir / "managed"
    db.write_text(json.dumps({
        "installed": installed,
        "aliases": aliases or {},
    }))
    return db_dir


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    return tmp_path


# ── macOS: JAVA_HOME = location/Contents/Home ─────────────────────────────────

def test_macos_java_home_has_contents_home_suffix(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    location = str(fake_home / "Library/Java/JavaVirtualMachines/zulu-21.jdk")
    _setup_db(fake_home, is_macos=True, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out
    assert f'export JAVA_HOME="{location}/Contents/Home"' in out


# ── Linux: JAVA_HOME = location ───────────────────────────────────────────────

def test_linux_java_home_is_location_directly(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    location = str(fake_home / ".jdk/zulu-21")
    _setup_db(fake_home, is_macos=False, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out
    assert f'export JAVA_HOME="{location}"' in out


# ── alias resolution ──────────────────────────────────────────────────────────

def test_alias_resolves_to_installed_slug(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    location = str(fake_home / ".jdk/zulu-21")
    _setup_db(
        fake_home, is_macos=False,
        installed={"zulu-21": {"location": location}},
        aliases={"21": "zulu-21"},
    )
    monkeypatch.setattr(sys, "argv", ["jdk", "21"])

    main()

    out = capsys.readouterr().out
    assert f'export JAVA_HOME="{location}"' in out


def test_alias_chain_resolves_correctly(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    location = str(fake_home / ".jdk/temurin-17")
    _setup_db(
        fake_home, is_macos=False,
        installed={"temurin-17": {"location": location}},
        aliases={"lts": "temurin-17", "17": "temurin-17"},
    )
    monkeypatch.setattr(sys, "argv", ["jdk", "lts"])

    main()

    out = capsys.readouterr().out
    assert f'export JAVA_HOME="{location}"' in out


# ── error cases ───────────────────────────────────────────────────────────────

def test_missing_db_exits_with_error(fake_home, monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    # DB 파일 없이 디렉토리만 생성
    (fake_home / ".config" / "jdkman").mkdir(parents=True)
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == -1


def test_slug_not_installed_exits_with_error(fake_home, monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    _setup_db(fake_home, is_macos=False, installed={})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == -1


def test_alias_pointing_to_uninstalled_slug_exits(fake_home, monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    _setup_db(fake_home, is_macos=False, installed={}, aliases={"21": "zulu-21"})
    monkeypatch.setattr(sys, "argv", ["jdk", "21"])

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == -1


def test_no_argv_exits_with_error(fake_home, monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    _setup_db(fake_home, is_macos=False, installed={})
    monkeypatch.setattr(sys, "argv", ["jdk"])  # env_tag 없음

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == -1


# ── output format ─────────────────────────────────────────────────────────────

def test_output_is_valid_shell_export(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.delenv("_JDKMAN_SHELL", raising=False)
    location = "/some/path/zulu-21"
    _setup_db(fake_home, is_macos=False, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out.strip()
    assert out.startswith("export JAVA_HOME=")
    assert '"' in out  # 따옴표로 감싸져 있어야 함


# ── macOS: PATH는 출력하지 않음 ───────────────────────────────────────────────

def test_macos_does_not_export_path(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.delenv("_JDKMAN_SHELL", raising=False)
    location = str(fake_home / "Library/Java/JavaVirtualMachines/zulu-21.jdk")
    _setup_db(fake_home, is_macos=True, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out
    assert "PATH" not in out


# ── Linux: PATH export ────────────────────────────────────────────────────────

def test_linux_exports_path_with_bin_suffix(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.delenv("_JDKMAN_SHELL", raising=False)
    location = "/some/path/zulu-21"
    _setup_db(fake_home, is_macos=False, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out
    assert f'export PATH="{location}/bin:' in out


def test_linux_path_includes_orig_path(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setenv("_JDKMAN_ORIG_PATH", "/usr/bin:/usr/local/bin")
    monkeypatch.delenv("_JDKMAN_SHELL", raising=False)
    location = "/some/path/zulu-21"
    _setup_db(fake_home, is_macos=False, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out
    assert f'export PATH="{location}/bin:/usr/bin:/usr/local/bin"' in out


# ── fish shell output ─────────────────────────────────────────────────────────

def test_fish_macos_uses_set_gx_syntax(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setenv("_JDKMAN_SHELL", "fish")
    location = str(fake_home / "Library/Java/JavaVirtualMachines/zulu-21.jdk")
    _setup_db(fake_home, is_macos=True, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out
    assert f'set -gx JAVA_HOME "{location}/Contents/Home"' in out


def test_fish_macos_does_not_export_path(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setenv("_JDKMAN_SHELL", "fish")
    location = str(fake_home / "Library/Java/JavaVirtualMachines/zulu-21.jdk")
    _setup_db(fake_home, is_macos=True, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out
    assert "PATH" not in out


def test_fish_linux_uses_set_gx_syntax(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setenv("_JDKMAN_SHELL", "fish")
    location = str(fake_home / ".jdk/zulu-21")
    _setup_db(fake_home, is_macos=False, installed={"zulu-21": {"location": location}})
    monkeypatch.setattr(sys, "argv", ["jdk", "zulu-21"])

    main()

    out = capsys.readouterr().out
    assert f'set -gx JAVA_HOME "{location}"' in out
    assert f'set -gx PATH "{location}/bin"' in out
