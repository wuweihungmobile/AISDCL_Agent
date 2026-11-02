"""研究面設定：`BRIDGE_RESEARCH_*` 的預設值、驗證與工作區根的處置（TCS-ResearchToPRD-P0-20261102
AC-960-2、AC-960-3：AT-960-2-3、AT-960-2-E-1、AT-960-3-5）。

只用 `load_settings(<環境映射>)`，不碰真環境：每個測試的環境映射都是自己組的。
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import pytest

import app.settings as settings_module
from app.research import settings as research_settings
from app.research.settings import RESEARCH_ENV_VARS, default_research_root, research_info
from app.settings import (
    REPO_ROOT,
    RESEARCH_DEFAULT_FETCH_ALLOWLIST,
    RESEARCH_DEFAULT_FETCH_MAX_BYTES,
    SettingsError,
    load_settings,
)

PLACEHOLDER = "<YOUR_BRIDGE_RESEARCH_WRITE_TOKEN_MIN_32_CHARS>"
README = Path(__file__).resolve().parents[1] / "README.md"


def _env(tmp_path: Path, **extra: str) -> dict[str, str]:
    """隔離的環境映射：工作區在 tmp、家目錄替身指向 tmp（兩個平台的鍵都給）。"""
    home = tmp_path / "home"
    return {"ENGINE_WORKSPACE": str(tmp_path / "ws"), "HOME": str(home), "USERPROFILE": str(home),
            **extra}


# ── AT-960-2-3：權杖長度與佔位字串在啟動時失敗 ───────────────────────────────────────────────
def test_AT_960_2_3_the_write_token_is_checked_at_startup_like_the_si_token(tmp_path: Path) -> None:
    name = "BRIDGE_RESEARCH_WRITE_TOKEN"
    for bad in ("x" * 31, PLACEHOLDER):
        with pytest.raises(SettingsError) as caught:
            load_settings(_env(tmp_path, **{name: bad}))
        assert name in str(caught.value), "訊息指出變數名"
        assert bad not in str(caught.value), "訊息不得回印值（連佔位也不）"
    good = "k" * 32
    cfg = load_settings(_env(tmp_path, **{name: good}))
    assert cfg.research_write_token == good and cfg.research_write_enabled
    assert good not in repr(cfg), "權杖不出現在 repr（日誌與 print(settings) 不會帶出去）"
    for blank in ("", "   ", "\t "):
        cfg = load_settings(_env(tmp_path, **{name: blank}))
        assert cfg.research_write_token is None and not cfg.research_write_enabled, repr(blank)
    cfg = load_settings(_env(tmp_path))
    assert cfg.research_write_token is None, "未設＝寫入面停用"


# ── AT-960-2-E-1：預設值、越界處置、README 與檔頭同步 ─────────────────────────────────────────
def test_AT_960_2_E_1_the_defaults_are_the_documented_values(tmp_path: Path) -> None:
    cfg = load_settings(_env(tmp_path))
    assert cfg.research_max_concurrent_runs == 1
    assert cfg.research_step_timeout_seconds == 1200
    assert cfg.research_fetch_allowlist == (
        "export.arxiv.org", "arxiv.org", "api.semanticscholar.org", "api.github.com",
        "api.stackexchange.com") == RESEARCH_DEFAULT_FETCH_ALLOWLIST
    assert cfg.research_web_allowlist == (), "Web 層預設關"
    assert cfg.research_fetch_max_bytes == 5242880 == RESEARCH_DEFAULT_FETCH_MAX_BYTES
    assert cfg.research_fetch_timeout_seconds == 20.0
    assert cfg.research_claude_command is None
    assert cfg.research_write_token is None


def test_AT_960_2_E_1_the_default_root_is_outside_the_repo_for_both_platform_shapes(
        tmp_path: Path) -> None:
    home = tmp_path / "fake-home"
    env = {"USERPROFILE": str(home / "win"), "HOME": str(home / "posix")}
    windows = default_research_root(env, windows=True)
    posix = default_research_root(env, windows=False)
    assert windows == home / "win" / ".autosdd" / "my-project", "Windows＝家目錄（USERPROFILE）下"
    assert posix == home / "posix" / ".autosdd" / "my-project", "POSIX＝~/.autosdd/my-project"
    for root in (windows, posix):
        assert not str(root.resolve()).startswith(str(REPO_ROOT.resolve())), "預設根在 repo 外"
    # 環境映射沒給家目錄時退回 Path.home()，不丟例外
    assert default_research_root({}, windows=False) == Path.home() / ".autosdd" / "my-project"


def test_AT_960_2_E_1_a_root_under_the_allowed_roots_passes_and_is_merged_into_them(
        tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    root = allowed / "my-project"
    cfg = load_settings(_env(tmp_path, BRIDGE_ALLOWED_PATH_ROOTS=str(allowed),
                             BRIDGE_RESEARCH_ROOT=str(root)))
    assert cfg.research_root == root.resolve()
    assert cfg.allowed_path_roots == (allowed.resolve(), root.resolve()), \
        "自動併入允許根：工作區根成為它自己的一個根（路徑閘靠它放行 /sdd/fsm?root=）"


def test_AT_960_2_E_1_a_root_outside_the_allowed_roots_fails_loud(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    with pytest.raises(SettingsError) as caught:
        load_settings(_env(tmp_path, BRIDGE_ALLOWED_PATH_ROOTS=str(allowed),
                           BRIDGE_RESEARCH_ROOT=str(tmp_path / "elsewhere")))
    assert "BRIDGE_RESEARCH_ROOT" in str(caught.value)
    # 設了寫入權杖卻沒明設根，而預設根不在明設的允許根之內：同樣大聲失敗（不靜默併入、不靜默放行）
    with pytest.raises(SettingsError) as caught:
        load_settings(_env(tmp_path, BRIDGE_ALLOWED_PATH_ROOTS=str(allowed),
                           BRIDGE_RESEARCH_WRITE_TOKEN="k" * 32))
    assert "預設工作區根" in str(caught.value)


def test_AT_960_2_E_1_a_filesystem_root_is_never_a_research_root(tmp_path: Path) -> None:
    anchor = str(Path(tmp_path.anchor))
    with pytest.raises(SettingsError) as caught:
        load_settings(_env(tmp_path, BRIDGE_RESEARCH_ROOT=anchor))
    assert "BRIDGE_RESEARCH_ROOT" in str(caught.value)
    with pytest.raises(SettingsError):
        load_settings(_env(tmp_path, BRIDGE_ALLOWED_PATH_ROOTS=anchor,
                           BRIDGE_RESEARCH_ROOT=anchor))


def test_AT_960_2_E_1_an_unused_research_surface_leaves_the_allowed_roots_untouched(
        tmp_path: Path) -> None:
    """兩個都沒設（研究面沒啟用）時，允許根與此前逐位元相同：不因預設根在 repo 外而悄悄加一個根。"""
    explicit = tmp_path / "a"
    cfg = load_settings(_env(tmp_path, BRIDGE_ALLOWED_PATH_ROOTS=str(explicit)))
    assert cfg.allowed_path_roots == (explicit.resolve(),)
    bare = load_settings(_env(tmp_path))
    assert cfg.research_root not in bare.allowed_path_roots
    enabled = load_settings(_env(tmp_path, BRIDGE_RESEARCH_WRITE_TOKEN="k" * 32))
    assert enabled.research_root in enabled.allowed_path_roots, "啟用（設了權杖）時預設根併入允許根"


@pytest.mark.parametrize(("name", "value"), [
    ("BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS", "0"), ("BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS", "two"),
    ("BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS", "0"),
    ("BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS", "86401"),
    ("BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS", "1.5"),
    ("BRIDGE_RESEARCH_FETCH_MAX_BYTES", "0"), ("BRIDGE_RESEARCH_FETCH_MAX_BYTES", "-5"),
    ("BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS", "0"), ("BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS", "-1"),
    ("BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS", "nan"),
    ("BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS", "inf"),
    ("BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS", "soon"),
    ("BRIDGE_RESEARCH_FETCH_ALLOWLIST", "https://export.arxiv.org"),
    ("BRIDGE_RESEARCH_FETCH_ALLOWLIST", "arxiv.org:443"),
    ("BRIDGE_RESEARCH_FETCH_ALLOWLIST", "a.example/path"),
    ("BRIDGE_RESEARCH_WEB_ALLOWLIST", "user@host.example"),
    ("BRIDGE_RESEARCH_WEB_ALLOWLIST", "bad host.example"),
])
def test_AT_960_2_E_1_out_of_range_values_fail_loud_and_name_the_variable(
        tmp_path: Path, name: str, value: str) -> None:
    with pytest.raises(SettingsError) as caught:
        load_settings(_env(tmp_path, **{name: value}))
    assert name in str(caught.value)


def test_AT_960_2_E_1_host_lists_are_normalised_deduplicated_and_blank_means_default(
        tmp_path: Path) -> None:
    cfg = load_settings(_env(
        tmp_path, BRIDGE_RESEARCH_FETCH_ALLOWLIST=" ArXiv.ORG. ,arxiv.org,, X.example ",
        BRIDGE_RESEARCH_WEB_ALLOWLIST=" Blog.Example.com "))
    assert cfg.research_fetch_allowlist == ("arxiv.org", "x.example")
    assert cfg.research_web_allowlist == ("blog.example.com",)
    blank = load_settings(_env(tmp_path, BRIDGE_RESEARCH_FETCH_ALLOWLIST="  , ,",
                               BRIDGE_RESEARCH_WEB_ALLOWLIST=""))
    assert blank.research_fetch_allowlist == RESEARCH_DEFAULT_FETCH_ALLOWLIST
    assert blank.research_web_allowlist == ()


def test_AT_960_2_E_1_explicit_values_are_applied(tmp_path: Path) -> None:
    cfg = load_settings(_env(
        tmp_path, BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS="3",
        BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS="600",
        BRIDGE_RESEARCH_FETCH_MAX_BYTES="1048576", BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS="7.5",
        BRIDGE_RESEARCH_CLAUDE_COMMAND="  aisdlc-mock-claude "))
    assert (cfg.research_max_concurrent_runs, cfg.research_step_timeout_seconds,
            cfg.research_fetch_max_bytes, cfg.research_fetch_timeout_seconds,
            cfg.research_claude_command) == (3, 600, 1048576, 7.5, "aisdlc-mock-claude")


def test_AT_960_2_E_1_the_readme_and_the_settings_header_list_every_research_variable() -> None:
    readme = README.read_text(encoding="utf-8")
    header = settings_module.__doc__ or ""
    assert len(RESEARCH_ENV_VARS) == len(set(RESEARCH_ENV_VARS)) == 9
    for var in RESEARCH_ENV_VARS:
        assert var in readme, f"README 環境表缺 {var}"
        assert var in header, f"app/settings.py 檔頭缺 {var}"
    # 反向：README 與檔頭提到的每個 BRIDGE_RESEARCH_ 變數都真的被讀取（不留已刪除變數的說明）
    source = Path(research_settings.__file__).read_text(encoding="utf-8")
    for text, where in ((readme, "README"), (header, "app/settings.py 檔頭")):
        for var in set(re.findall(r"BRIDGE_RESEARCH_[A-Z_]+", text)):
            assert var in RESEARCH_ENV_VARS and var in source, f"{where} 提到未被讀取的 {var}"


# ── AT-960-3-5：預設根在 repo 外且於 /health/deep 揭露；設到允許根外則啟動失敗 ────────────────
def test_AT_960_3_5_the_three_defaults_are_outside_the_monorepo_and_docker_is_composes_value(
        tmp_path: Path) -> None:
    cfg = load_settings(_env(tmp_path))
    home = (tmp_path / "home").resolve()
    assert cfg.research_root == home / ".autosdd" / "my-project"
    assert not str(cfg.research_root).startswith(str(REPO_ROOT.resolve())), "預設根不在 monorepo 內"
    # Docker 模式（只有 /workspace 為允許根）：compose 明設 BRIDGE_RESEARCH_ROOT 於其下
    docker = load_settings(_env(
        tmp_path, BRIDGE_ALLOWED_PATH_ROOTS="/workspace",
        BRIDGE_RESEARCH_ROOT="/workspace/my-project"))
    assert docker.research_root == Path("/workspace/my-project").resolve()
    assert Path("/workspace").resolve() in docker.allowed_path_roots
    with pytest.raises(SettingsError):          # 設到允許根（/workspace）之外：啟動失敗
        load_settings(_env(tmp_path, BRIDGE_ALLOWED_PATH_ROOTS="/workspace",
                           BRIDGE_RESEARCH_ROOT=str(tmp_path / "outside")))


def test_AT_960_3_5_the_health_probe_reveals_the_resolved_root(make_bridge, tmp_path: Path) -> None:
    root = tmp_path / "ws-root" / "my-project"
    cfg = load_settings(_env(tmp_path, BRIDGE_RESEARCH_ROOT=str(root)))
    live = make_bridge(cfg)
    body = live.client.get("/health/deep").json()
    assert body["research"]["root"] == str(cfg.research_root) == str(root.resolve())
    assert research_info(cfg)["root"] == body["research"]["root"]


# ── research_info：固定鍵集合、mode 判定、量不到標 NOT-EVALUABLE ───────────────────────────────
def test_the_info_block_has_the_fixed_key_set_and_marks_unmeasurable_items(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_settings(_env(tmp_path))
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: f"/bin/{name}")
    info = research_info(cfg)
    assert tuple(info) == research_settings.INFO_KEYS
    assert info["mode"] == "local" and info["db"] is False and info["web_layer_enabled"] is False
    assert info["scaffold_templates"] == []
    assert info["claude_cli"] == {"ok": True, "version": "NOT-EVALUABLE"}
    assert info["git"] == {"ok": True, "version": "NOT-EVALUABLE"}
    assert info["gh_cli"] == {"ok": True, "authenticated": "NOT-EVALUABLE"}
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None if name == "claude" else "/x")
    assert research_info(cfg)["mode"] == "mock-only", "找不到 claude＝mock-only"
    assert research_info(cfg)["claude_cli"]["ok"] is False
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    assert research_info(cfg)["mode"] == "mock-only"


def test_the_info_block_never_spawns_a_subprocess(tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """能力登記鎖：研究套件無 git／gh 子行程——探測只看 PATH。"""
    import subprocess

    def refuse(*_a, **_k):
        raise AssertionError("research_info 不得起子行程")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)
    info = research_info(load_settings(_env(tmp_path)))
    assert info["root"] and os.path.isabs(info["root"])
