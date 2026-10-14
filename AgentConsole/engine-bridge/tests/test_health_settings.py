"""設定載入（環境變數表）與 /health。"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import app.settings as settings_module
from app.settings import BRIDGE_DIR, REPO_ROOT, SettingsError, load_settings


def test_defaults_match_the_documented_table() -> None:
    cfg = load_settings({})
    assert cfg.port == 8081
    assert cfg.host == "127.0.0.1"
    assert cfg.engine_workspace == (BRIDGE_DIR / ".workspace").resolve()
    assert cfg.autoclaude_root == (REPO_ROOT / "AutoClaude").resolve()
    assert cfg.db_dsn is None
    assert cfg.db_schema == "console"
    assert cfg.stop_grace_seconds == 30.0
    assert cfg.outbound_allowlist == ("api.minimax.io", "api.minimax.chat", "localhost",
                                      "127.0.0.1")
    assert cfg.engine_workspace in cfg.allowed_path_roots
    assert REPO_ROOT.resolve() in cfg.allowed_path_roots
    assert cfg.bridge_instance and len(cfg.bridge_instance) <= 100
    assert cfg.sdd_root is not None and cfg.sdd_root.name.startswith("AISDLC_SDD_v")


def test_overrides_are_applied_and_parsed(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    cfg = load_settings({
        "BRIDGE_PORT": "9000", "BRIDGE_HOST": "0.0.0.0", "ENGINE_WORKSPACE": str(a),
        "BRIDGE_DB_DSN": "postgresql://u@h/db", "BRIDGE_DB_SCHEMA": "console_test",
        "BRIDGE_STOP_GRACE_SECONDS": "2.5", "BRIDGE_INSTANCE": "x" * 300,
        "BRIDGE_ALLOWED_PATH_ROOTS": os.pathsep.join([str(a), str(b)]),
        "BRIDGE_OUTBOUND_ALLOWLIST": " Example.COM. , 10.0.0.1 ,, ",
        "SDD_ROOT": str(tmp_path / "sdd"),
    })
    assert (cfg.port, cfg.host) == (9000, "0.0.0.0")
    assert cfg.db_dsn == "postgresql://u@h/db"
    assert cfg.db_schema == "console_test"
    assert cfg.stop_grace_seconds == 2.5
    assert len(cfg.bridge_instance) == 100
    assert cfg.allowed_path_roots == (a.resolve(), b.resolve())
    assert cfg.outbound_allowlist == ("example.com", "10.0.0.1")
    assert cfg.sdd_root == (tmp_path / "sdd").resolve()


def test_sdd_root_may_be_a_version_dir_or_the_parent_that_holds_the_versions(
        tmp_path: Path) -> None:
    parent = tmp_path / "mounted-as-sdd"                  # Docker 掛載點的目錄名不是版本名
    for name in ("AISDLC_SDD_v0.9", "AISDLC_SDD_v0.30", "AISDLC_SDD_v0.29"):
        (parent / name).mkdir(parents=True)
    from_parent = load_settings({"SDD_ROOT": str(parent)}).sdd_root
    assert from_parent == (parent / "AISDLC_SDD_v0.30").resolve()
    exact = load_settings({"SDD_ROOT": str(parent / "AISDLC_SDD_v0.9")}).sdd_root
    assert exact == (parent / "AISDLC_SDD_v0.9").resolve(), "明確指定版本目錄就用它，不自作主張換版"
    lone = tmp_path / "just-a-dir"
    lone.mkdir()
    assert load_settings({"SDD_ROOT": str(lone)}).sdd_root == lone.resolve()


@pytest.mark.parametrize(("name", "value"), [
    ("BRIDGE_PORT", "abc"), ("BRIDGE_PORT", "0"), ("BRIDGE_PORT", "70000"),
    ("BRIDGE_STOP_GRACE_SECONDS", "0"), ("BRIDGE_STOP_GRACE_SECONDS", "-3"),
    ("BRIDGE_STOP_GRACE_SECONDS", "soon"),
    ("BRIDGE_DB_SCHEMA", "bad-name"), ("BRIDGE_DB_SCHEMA", 'x"; DROP TABLE y; --'),
    ("BRIDGE_DB_SCHEMA", "1abc"),
])
def test_invalid_values_fail_loud_at_startup(name: str, value: str) -> None:
    with pytest.raises(SettingsError):
        load_settings({name: value})


def test_a_filesystem_root_is_never_an_acceptable_allowlist_root() -> None:
    with pytest.raises(SettingsError):
        load_settings({"BRIDGE_ALLOWED_PATH_ROOTS": Path(Path.cwd().anchor).as_posix()})
    with pytest.raises(SettingsError):
        load_settings({"BRIDGE_ALLOWED_PATH_ROOTS": os.pathsep})


def test_outside_a_monorepo_the_default_roots_are_only_the_workspace(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """容器內 parents[1] 會是 `/`：絕不能因此把整個檔案系統放進白名單。"""
    monkeypatch.setattr(settings_module, "REPO_ROOT", tmp_path)
    cfg = load_settings({"ENGINE_WORKSPACE": str(tmp_path / "ws")})
    assert cfg.allowed_path_roots == ((tmp_path / "ws").resolve(),)


def test_health_has_the_contract_shape(bridge) -> None:
    import autoclaude

    resp = bridge.client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["bridge_instance"] == "test-bridge"
    assert body["engines"]["autoclaude"]["ok"] is True
    assert body["engines"]["autoclaude"]["version"] == autoclaude.__version__
    assert body["engines"]["sdd"]["ok"] is True
    assert body["engines"]["sdd"]["latest"].startswith("AISDLC_SDD_v")
    assert body["db"] == {"enabled": False, "schema": None, "ok": None}
