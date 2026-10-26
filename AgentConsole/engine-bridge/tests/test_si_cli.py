"""`app/si_cli.py` 與 `SI_ROOT` 設定的測試（TCS-SelfImprovingMirror-P1b：AT-932-3-1、
AT-932-3-E-1／E-2／E-3、AT-940-1-1、AT-940-2-1、AT-940-2-E-1；TCS-SelfImprovingDecide-P2b：
AT-950-3-1、AT-950-3-E-1）。

全部以假 CLI 樹（tests/fake_si.py）真起子行程：斷言 argv、cwd、環境集合、各失敗形態的 `cause` 與
`detail`、逾時殺整棵行程樹、stdout 上限；不依賴真 CLI。AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import fields, replace
from pathlib import Path
from typing import Any

import httpx
import psutil
import pytest

from app import settings as settings_module
from app import si_cli
from app.errors import ApiError
from app.settings import Settings, SettingsError, load_settings
from tests.fake_si import make_fake_si, read_calls, set_control

SENTINEL = "sentinel-secret-7f3a91"
DETAIL_FORMAT = re.compile(r"^rc=(none|\d+); stderr=", re.S)


def export_object(kind: str = "observations", **over: Any) -> dict[str, Any]:
    obj: dict[str, Any] = {
        "schema_rev": 1, "kind": kind, "generated_at": "2026-10-21T00:00:00+08:00",
        "head_sha": "a" * 40, "items": [], "next_since": None, "truncated": False, "ne": [],
        "problems": []}
    obj.update(over)
    return obj


def fail_of(call: Any) -> ApiError:
    with pytest.raises(ApiError) as caught:
        call()
    return caught.value


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_si(tmp_path)


# ── AT-932-3-1：各失敗形態的 cause 與 detail ──────────────────────────────────────────────
def _no_root(tmp_path: Path, fake: Path, mp: pytest.MonkeyPatch) -> Path | None:
    return None


def _missing_dir(tmp_path: Path, fake: Path, mp: pytest.MonkeyPatch) -> Path | None:
    return tmp_path / "does-not-exist"


def _no_script(tmp_path: Path, fake: Path, mp: pytest.MonkeyPatch) -> Path | None:
    empty = tmp_path / "empty-dir"
    empty.mkdir()
    return empty


def _spawn_error(tmp_path: Path, fake: Path, mp: pytest.MonkeyPatch) -> Path | None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise PermissionError("denied by the test")

    mp.setattr(si_cli.subprocess, "Popen", refuse)
    return fake


def _timeout(tmp_path: Path, fake: Path, mp: pytest.MonkeyPatch) -> Path | None:
    set_control(fake, sleep=30)
    mp.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", 0.5)
    return fake


def _too_large(tmp_path: Path, fake: Path, mp: pytest.MonkeyPatch) -> Path | None:
    set_control(fake, huge=True)
    mp.setattr(si_cli, "SI_STDOUT_MAX_BYTES", 2048)
    return fake


def _control(**knobs: Any) -> Any:
    def prepare(tmp_path: Path, fake: Path, mp: pytest.MonkeyPatch) -> Path | None:
        set_control(fake, **knobs)
        return fake

    return prepare


STDERR_G = "boom：假 CLI 的 stderr"
FAILURE_CASES: list[tuple[str, Any, str, str]] = [
    # (名稱, 準備函式, 期望 cause, 期望 detail 的 rc 段)
    ("a-si-root-none", _no_root, "si_root_unset", "none"),
    ("b-dir-missing", _missing_dir, "si_script_missing", "none"),
    ("c-script-missing", _no_script, "si_script_missing", "none"),
    ("d-spawn-error", _spawn_error, "spawn_failed", "none"),
    ("e-timeout", _timeout, "timeout", "none"),
    ("f-stdout-too-large", _too_large, "stdout_too_large", "none"),
    ("g-nonzero-rc", _control(rc=2, stderr=STDERR_G), "nonzero_rc", "2"),
    ("h-garbage", _control(raw_stdout="這不是 JSON"), "bad_json", "0"),
    ("i-two-documents", _control(raw_stdout='{"a": 1}{"b": 2}'), "bad_json", "0"),
    ("j-array", _control(raw_stdout="[1, 2]\n"), "bad_json", "0"),
    ("k-empty", _control(raw_stdout=""), "bad_json", "0"),
    ("l1-schema-rev-2", _control(schema_rev=2), "schema_rev_mismatch", "0"),
    ("l2-schema-rev-missing", _control(schema_rev=None), "schema_rev_mismatch", "0"),
    ("l3-schema-rev-string", _control(schema_rev="1"), "schema_rev_mismatch", "0"),
    ("l4-schema-rev-bool", _control(schema_rev=True), "schema_rev_mismatch", "0"),
    ("m1-kind-differs", _control(kind="events"), "bad_shape", "0"),
    ("m2-items-not-array", _control(export=export_object(items="nope")), "bad_shape", "0"),
]


@pytest.mark.parametrize("name,prepare,cause,rc_text", FAILURE_CASES,
                         ids=[c[0] for c in FAILURE_CASES])
def test_AT_932_3_1_every_failure_form_maps_to_503_with_cause_and_detail(
        name: str, prepare: Any, cause: str, rc_text: str, tmp_path: Path, fake: Path,
        monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("SI_TEST_SECRET", SENTINEL)
    root = prepare(tmp_path, fake, monkeypatch)
    caplog.set_level(logging.WARNING, logger="bridge.si_cli")
    err = fail_of(lambda: si_cli.run_export(root, "observations"))
    assert (err.status_code, err.body["reason"]) == (503, "si_unavailable"), name
    assert err.body["cause"] == cause, f"{name}：{err.body}"
    detail = err.body["detail"]
    assert DETAIL_FORMAT.match(detail), f"{name}：detail 格式不合 {detail!r}"
    assert detail.startswith(f"rc={rc_text}; stderr="), f"{name}：{detail!r}"
    if cause == "nonzero_rc":
        assert detail == f"rc=2; stderr={STDERR_G}", "尾段必須逐字等於假 CLI 寫的 stderr"
    if cause in ("si_root_unset", "si_script_missing"):
        assert "SI_ROOT" in detail, f"{name}：無行程的失敗要說明 SI_ROOT"
    if cause == "spawn_failed":
        assert "PermissionError" in detail
    mine = [r for r in caplog.records if r.name == "bridge.si_cli" and r.levelno == logging.WARNING]
    assert len(mine) == 1, f"{name}：每個失敗恰一筆 warning，實際 {len(mine)}"
    assert SENTINEL not in caplog.text and SENTINEL not in json.dumps(err.body), \
        f"{name}：日誌與本文不得帶環境值"


def test_AT_932_3_1_bad_callers_are_value_errors_not_503(fake: Path) -> None:
    for kwargs in ({"kind": "nope"}, {"kind": "observations", "ident": "--id"},
                   {"kind": "observations", "ident": ""}):
        with pytest.raises(ValueError):
            si_cli.run_export(fake, **kwargs)
    assert read_calls(fake) == [], "呼叫端 bug 不得啟動子行程"


# ── AT-932-3-E-1：合法輸出不是錯誤 ────────────────────────────────────────────────────────
LEGAL_CASES = {
    "a-empty-items-with-ne-and-problems": {"export": export_object(
        ne=[{"field": "events", "reason": "carrier-not-established"}],
        problems=[{"subject": "L3", "code": "ROW-ARITY", "detail": "欄數不是 9"}])},
    "b-stderr-noise": {"stderr": "雜訊" * 100, "export": export_object(
        items=[{"id": "OBS-SI-001"}])},
    "c-unknown-top-level-key": {"export": export_object(future_key={"x": [1, None]})},
    "d-null-fields": {"export": export_object(head_sha=None, next_since=None, truncated=False)},
}


@pytest.mark.parametrize("name", list(LEGAL_CASES))
def test_AT_932_3_E_1_legal_output_is_never_an_error(
        name: str, fake: Path, settings: Settings, make_bridge: Any) -> None:
    knobs = LEGAL_CASES[name]
    set_control(fake, **knobs)
    got = si_cli.run_export(fake, "observations")
    assert got == knobs["export"], name
    live = make_bridge(replace(settings, si_root=fake))
    resp = live.client.get("/si/observations")
    assert resp.status_code == 200, f"{name}：{resp.text}"
    assert resp.json() == knobs["export"], name
    if name.startswith("a-"):
        assert resp.json()["items"] == [], "空表只在 SI 真的回空時合法，不是 503"


# ── AT-932-3-E-2：逾時殺整棵行程樹 ────────────────────────────────────────────────────────
def _alive(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE      # 殭屍＝已死、只是沒人收
    except psutil.Error:
        return False


def _gone(pid: int, within: float) -> bool:
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return not _alive(pid)


def test_AT_932_3_E_2_timeout_kills_the_whole_process_tree_without_orphans(
        fake: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pids_file = fake / "fake_pids.json"
    # 逾時取 2 秒而非 0.5 秒：假 CLI 要先起來才會生孫行程，慢機器上 0.5 秒會在孫行程出生前就殺掉
    # 它，鑑別力就沒了。仍遠小於它的 30 秒睡眠；孫行程沒出生就換較長的逾時重試，不靠運氣。
    for timeout in (2.0, 6.0):
        pids_file.unlink(missing_ok=True)
        set_control(fake, sleep=30, grandchild=True)
        monkeypatch.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", timeout)
        started = time.monotonic()
        err = fail_of(lambda: si_cli.run_export(fake, "observations"))
        elapsed = time.monotonic() - started
        if pids_file.is_file():
            break
    assert pids_file.is_file(), "假 CLI 在逾時內沒能生出孫行程：環境太慢，無法驗證殺樹"
    assert err.body["cause"] == "timeout"
    assert err.body["detail"].startswith("rc=none; stderr=")
    assert elapsed < 10, f"呼叫必須在有界時間內返回（實際 {elapsed:.1f} 秒）"
    pids = json.loads(pids_file.read_text(encoding="utf-8"))
    recorded = read_calls(fake)[-1]["pid"]
    for label, pid in (("假 CLI", recorded), ("孫行程", pids["grandchild"])):
        assert _gone(pid, 3.0), f"{label}（pid={pid}）逾時後仍存活＝孤兒行程"
    set_control(fake)
    monkeypatch.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", 15.0)
    assert si_cli.run_export(fake, "observations")["kind"] == "observations"


# ── AT-932-3-E-3：stdout 上限，邊讀邊判 ───────────────────────────────────────────────────
def test_AT_932_3_E_3_stdout_beyond_the_cap_kills_the_child_and_stays_bounded(
        fake: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_control(fake, huge=True)
    monkeypatch.setattr(si_cli, "SI_STDOUT_MAX_BYTES", 4096)
    started = time.monotonic()
    err = fail_of(lambda: si_cli.run_export(fake, "observations"))
    assert time.monotonic() - started < 10
    assert err.body["cause"] == "stdout_too_large"
    assert err.body["detail"].startswith("rc=none; stderr=")
    pid = read_calls(fake)[-1]["pid"]
    assert _gone(pid, 3.0), "超量後假 CLI 必須已被終止"
    marks = (fake / "fake_written.txt").read_text(encoding="utf-8").split()
    assert marks, "假 CLI 至少寫過一輪"
    assert int(marks[-1]) <= 1024 * 1024, f"被殺時累計寫出 {marks[-1]} 位元組：Bridge 不是邊讀邊判"


# ── AT-940-1-1：SI_ROOT 設定的七種輸入 ────────────────────────────────────────────────────
def test_AT_940_1_1_si_root_settings_resolution(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mono = tmp_path / "mono"
    (mono / "AutoClaude").mkdir(parents=True)
    (mono / "AgentConsole").mkdir()
    plain = tmp_path / "plain"
    plain.mkdir()
    existing = tmp_path / "somewhere"
    existing.mkdir()
    workspace = tmp_path / "ws"

    def load(env: dict[str, str], repo_root: Path) -> Settings:
        monkeypatch.setattr(settings_module, "REPO_ROOT", repo_root)
        return load_settings({"ENGINE_WORKSPACE": str(workspace), **env})

    cases: list[tuple[str, dict[str, str], Path, Path | None]] = [
        ("a-unset-monorepo", {}, mono, mono.resolve()),
        ("b-unset-container", {}, plain, None),
        ("c-blank-monorepo", {"SI_ROOT": "   "}, mono, mono.resolve()),
        ("c-blank-container", {"SI_ROOT": "   "}, plain, None),
        ("d-relative-dotdot", {"SI_ROOT": os.path.join("some", "..", "rel-dir")}, mono,
         Path(os.path.join("some", "..", "rel-dir")).resolve()),
        ("e-existing-absolute", {"SI_ROOT": str(existing)}, mono, existing.resolve()),
        ("f-missing-absolute", {"SI_ROOT": str(tmp_path / "absent" / "x")}, plain,
         (tmp_path / "absent" / "x").resolve()),
    ]
    only_ws = {"BRIDGE_ALLOWED_PATH_ROOTS": str(workspace)}
    for name, env, repo_root, expected in cases:
        cfg = load(env, repo_root)
        assert cfg.si_root == expected, f"{name}：{cfg.si_root!r} != {expected!r}"
        # 預設白名單根（工作區＋像 monorepo 的 REPO_ROOT）與 SI_ROOT 無關：同一個環境去掉 SI_ROOT 後
        # 白名單根必須一模一樣；明列白名單根時，SI_ROOT 不會自己溜進去。
        bare = {k: v for k, v in env.items() if k != "SI_ROOT"}
        assert cfg.allowed_path_roots == load(bare, repo_root).allowed_path_roots, name
        if cfg.si_root is not None:
            pinned = load({**env, **only_ws}, repo_root)
            assert pinned.allowed_path_roots == (workspace.resolve(),), name
            assert cfg.si_root not in pinned.allowed_path_roots, f"{name}：SI_ROOT 不得併入白名單根"
    anchor = Path(tmp_path.anchor)
    with pytest.raises(SettingsError) as caught:
        load({"SI_ROOT": str(anchor)}, mono)
    assert "SI_ROOT" in str(caught.value)
    # SI_ROOT 明列在 BRIDGE_ALLOWED_PATH_ROOTS 時才算白名單根（兩個設定互不推導）
    both = load({"SI_ROOT": str(existing), "BRIDGE_ALLOWED_PATH_ROOTS": str(existing)}, mono)
    assert both.allowed_path_roots == (existing.resolve(),)
    # 既有欄位不變（對既有環境映射的結果與改動前逐欄相同）
    base = load({"BRIDGE_PORT": "9001", "BRIDGE_INSTANCE": "inst-1"}, mono)
    assert (base.host, base.port, base.engine_workspace, base.db_dsn, base.db_schema,
            base.bridge_instance, base.stop_grace_seconds, base.sdd_write_token, base.log_dir) == (
        "127.0.0.1", 9001, workspace.resolve(), None, "console", "inst-1", 30.0, None, None)
    assert base.allowed_path_roots == (workspace.resolve(), mono.resolve())
    assert base.outbound_allowlist == settings_module.DEFAULT_OUTBOUND_ALLOWLIST
    # P2b 起 Settings 末尾另增 si_write_token（repr=False）與 si_audit_dir；既有欄位的相對順序不變
    assert [f.name for f in fields(Settings)][-5:] == [
        "log_dir", "sdd_write_token", "si_root", "si_write_token", "si_audit_dir"]
    assert "si_root" in repr(base) and "sdd_write_token" not in repr(base)
    assert "si_write_token" not in repr(base) and "si_audit_dir" in repr(base)
    assert (base.si_write_token, base.si_audit_dir) == (None, None), "兩個新設定預設為停用"


# ── AT-940-2-1：argv、cwd、環境與預設常數 ─────────────────────────────────────────────────
ALLOWED_ENV = {"PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL"}
FIXED_ENV = {"PYTHONUTF8", "PYTHONDONTWRITEBYTECODE", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0",
             "GIT_CONFIG_VALUE_0"}
#: 直譯器自己在啟動時會（視平台）加進子行程環境的名稱，不是 Bridge 傳的：macOS 框架版 Python 的
#: 啟動器會設 `__PYVENV_LAUNCHER__`、POSIX 的 C locale 會被 PEP 538 補上 `LC_CTYPE`
#: （本機 Windows 實測兩者皆無，集合只放已知的平台差異，不放行其他任何名稱）。
INTERPRETER_ADDED = {"__PYVENV_LAUNCHER__", "LC_CTYPE"}


def test_AT_940_2_1_argv_cwd_env_and_default_constants(
        fake: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secrets = {"BRIDGE_DB_DSN": "postgresql://u:pw-sentinel@h/db", "MINIMAX_API_KEY": "mm-sentinel",
               "AUTOSDD_SI_DIR": "/x/autosdd-sentinel", "PYTHONPATH": "/x/pythonpath-sentinel",
               "SDD_ROOT": "/x/sdd-sentinel", "CLAUDE_CONFIG_DIR": "/x/claude-sentinel"}
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("LANG", "C.UTF-8")
    assert os.environ.get("PATH"), "測試前提：PATH 在場"
    combos: list[tuple[str, dict[str, Any], list[str]]] = [
        (kind, {}, []) for kind in si_cli.SI_KINDS]
    combos += [("observations", {"since": 7}, ["--since", "7"]),
               ("events", {"limit": 4}, ["--limit", "4"]),
               ("runs", {"since": 3, "limit": 2}, ["--since", "3", "--limit", "2"]),
               ("proposals", {"ident": "PROP-SI-004"}, ["--id", "PROP-SI-004"]),
               ("proposals", {"since": 1, "limit": 9, "ident": "PROP-SI-004"},
                ["--since", "1", "--limit", "9", "--id", "PROP-SI-004"]),
               ("issues", {"status": "待處理"}, ["--status=待處理"]),
               ("issues", {"source": "系統 缺陷"}, ["--source=系統 缺陷"]),
               ("issues", {"since": 1, "limit": 9, "status": "a=b", "source": "-x"},
                ["--since", "1", "--limit", "9", "--status=a=b", "--source=-x"]),
               ("issues", {"ident": "OBS-SI-001"}, ["--id", "OBS-SI-001"])]
    for kind, kwargs, flags in combos:
        si_cli.run_export(fake, kind, **kwargs)
    calls = read_calls(fake)
    assert len(calls) == len(combos)
    script = (fake / "tools" / "selfimproving.py").resolve()
    for (kind, _kwargs, flags), call in zip(combos, calls, strict=True):
        label = f"{kind} {flags}"
        assert call["args"] == ["export", "--json", "--kind", kind, *flags], label
        assert os.path.normcase(call["executable"]) == os.path.normcase(sys.executable), label
        assert Path(call["script"]) == script, label
        assert "--repo" not in call["args"] and "-I" not in call["args"], label
        assert "-P" not in call["args"] and call["safe_path"] is False, label
        assert Path(call["cwd"]).resolve() == fake.resolve(), label
        assert call["stdin_eof"] is True, "stdin 必須是 DEVNULL（讀到立即 EOF）"
        env = call["env"]
        names = {n.upper() for n in env}
        extra = names - ALLOWED_ENV - FIXED_ENV - INTERPRETER_ADDED
        assert not extra, f"{label}：環境出現白名單與固定鍵以外的變數 {sorted(extra)}"
        assert env["PYTHONUTF8"] == "1" and env["PYTHONDONTWRITEBYTECODE"] == "1", label
        assert (env["GIT_CONFIG_COUNT"], env["GIT_CONFIG_KEY_0"], env["GIT_CONFIG_VALUE_0"]) == (
            "1", "safe.directory", str(fake)), label
        blob = json.dumps(env, ensure_ascii=False)
        for name, value in secrets.items():
            assert value not in blob, f"{label}：{name} 的值洩入子行程環境"
        assert env.get("PATH") == os.environ["PATH"] or env.get("Path") == os.environ["PATH"]
        assert env.get("HOME") == str(home) or env.get("USERPROFILE") == str(home)
    assert si_cli.SI_CLI_TIMEOUT_SECONDS == 15.0 and si_cli.SI_CLI_TIMEOUT_SECONDS < 20
    assert si_cli.SI_EXPORT_SCHEMA_REV == 1
    assert si_cli.SI_STDOUT_MAX_BYTES == 8 * 1024 * 1024 == 8388608
    assert si_cli.SI_STDERR_TAIL_CHARS == 1000
    assert si_cli.SI_KINDS == ("observations", "events", "proposals", "runs", "status", "issues")


def test_AT_940_2_1_the_popen_call_uses_devnull_stdin_and_pipes(
        fake: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """管道與 stdin 的形態（假 CLI 只能量到 EOF，pytest 的 fd 擷取下繼承的 stdin 也是 EOF，
    所以另以紀錄器直接看 `Popen` 的關鍵字參數）。"""
    seen: list[dict[str, Any]] = []
    real = subprocess.Popen

    def recorder(argv: Any, **kwargs: Any) -> Any:
        seen.append({"argv": list(argv), **kwargs})
        return real(argv, **kwargs)

    monkeypatch.setattr(si_cli.subprocess, "Popen", recorder)
    si_cli.run_export(fake, "status")
    assert len(seen) == 1
    kw = seen[0]
    assert kw["stdin"] is subprocess.DEVNULL
    assert kw["stdout"] is subprocess.PIPE and kw["stderr"] is subprocess.PIPE
    assert kw.get("shell", False) is False and Path(kw["cwd"]) == fake


# ── AT-940-2-E-1：環境建構純函式 ──────────────────────────────────────────────────────────
def test_AT_940_2_E_1_build_env_whitelist_is_case_insensitive_and_pure(tmp_path: Path) -> None:
    source = {"Path": "/usr/bin", "userprofile": "/home/u", "Lc_All": "C", "BRIDGE_X": "1",
              "bridge_y": "2", "MINIMAX_API_KEY": "k", "Autosdd_Anything": "3",
              "pythonpath": "/p", "SDD_ROOT": "/s", "GIT_DIR": "/g", "GIT_CONFIG_COUNT": "9",
              "KEEP_ME": "yes"}
    snapshot = dict(source)
    got = si_cli.build_env(source, tmp_path)
    assert source == snapshot, "純函式不得改動輸入"
    fixed = {"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_COUNT": "1",
             "GIT_CONFIG_KEY_0": "safe.directory", "GIT_CONFIG_VALUE_0": str(tmp_path)}
    assert got == {"Path": "/usr/bin", "userprofile": "/home/u", "Lc_All": "C", **fixed}
    for dropped in ("BRIDGE_X", "bridge_y", "MINIMAX_API_KEY", "Autosdd_Anything", "pythonpath",
                    "SDD_ROOT", "GIT_DIR", "KEEP_ME"):
        assert dropped not in got
    assert got["GIT_CONFIG_COUNT"] == "1", "來源中的 GIT_CONFIG_COUNT 必須被固定值覆寫"
    assert "SYSTEMROOT" not in got, "白名單中來源沒有的名稱不補空值"
    assert si_cli.build_env({}, tmp_path) == fixed


# ── 補：活 Bridge 上 SI_ROOT 未設的 503 與 200 的形狀（settings → router → si_cli 串接）─────────
def test_AT_932_3_1_a_bridge_without_si_root_answers_503_not_an_empty_list(
        settings: Settings, make_bridge: Any) -> None:
    live = make_bridge(replace(settings, si_root=None))
    resp = live.client.get("/si/observations")
    assert resp.status_code == 503
    body = resp.json()
    assert body["reason"] == "si_unavailable" and body["cause"] == "si_root_unset"
    assert "items" not in body
    assert isinstance(httpx.get(f"{live.base_url}/health").json(), dict), "SI 不可用不影響健康"


# ── AT-950-3-1：`run_validate` 的子行程契約（P2b W4）─────────────────────────────────────────
VALIDATE_ARGS = ["obs-add", "--dry-run", "--body-file", "-", "--json"]
# 與 tests/fake_si.py 的預設預覽物件相同（刻意不寫 OBS 號字面：根層 ref.obs 只准帳本上真有的號）
DEFAULT_DRY_RUN = {"ok": True, "row": "| fake dry-run row |", "row_bytes": 20,
                   "row_max_bytes": 700, "findings": []}


def test_AT_950_3_1_run_validate_feeds_stdin_and_spawns_with_the_whitelisted_environment(
        fake: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secrets = {"BRIDGE_SI_WRITE_TOKEN": "tok-sentinel-" + "z" * 24,
               "AUTOSDD_SI_AUDIT_KEY": "key-sentinel", "AUTOSDD_SI_DIR": "/x/autosdd-sentinel",
               "BRIDGE_DB_DSN": "postgresql://u:pw@h/db", "PYTHONPATH": "/x/pythonpath-sentinel"}
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    seen: list[dict[str, Any]] = []
    real = subprocess.Popen

    def recorder(argv: Any, **kwargs: Any) -> Any:
        seen.append({"argv": list(argv), **kwargs})
        return real(argv, **kwargs)

    monkeypatch.setattr(si_cli.subprocess, "Popen", recorder)
    raw = '{"context":"中文 CJK 內容・含各種字元 \\"引號\\"","symptom":"x"}'.encode()
    assert si_cli.build_validate_argv(fake) == [
        sys.executable, str(fake / "tools" / "selfimproving.py"), *VALIDATE_ARGS]
    result = si_cli.run_validate(fake, raw)
    assert result == DEFAULT_DRY_RUN
    assert len(seen) == 1
    kw = seen[0]
    assert kw["argv"][2:] == VALIDATE_ARGS and kw["stdin"] is subprocess.PIPE
    assert kw["stdout"] is subprocess.PIPE and kw["stderr"] is subprocess.PIPE
    assert kw.get("shell", False) is False and Path(kw["cwd"]) == fake
    call = read_calls(fake)[-1]
    assert call["args"] == VALIDATE_ARGS, "不帶 --repo、-I、-P"
    assert "--repo" not in call["args"] and "-I" not in call["args"] and "-P" not in call["args"]
    assert call["safe_path"] is False
    assert base64.b64decode(call["stdin_b64"]) == raw, "stdin 位元組必須等於 raw"
    assert os.path.normcase(call["executable"]) == os.path.normcase(sys.executable)
    assert Path(call["script"]) == (fake / "tools" / "selfimproving.py").resolve()
    assert Path(call["cwd"]).resolve() == fake.resolve(), "cwd 為 si_root"
    env = call["env"]
    names = {n.upper() for n in env}
    assert not [n for n in names if n.startswith(("BRIDGE_", "AUTOSDD_"))], sorted(names)
    extra = names - ALLOWED_ENV - FIXED_ENV - INTERPRETER_ADDED
    assert not extra, f"環境出現白名單與固定鍵以外的變數 {sorted(extra)}"
    blob = json.dumps(env, ensure_ascii=False)
    for name, value in secrets.items():
        assert value not in blob, f"{name} 的值洩入子行程環境"
    assert (env["GIT_CONFIG_COUNT"], env["GIT_CONFIG_KEY_0"], env["GIT_CONFIG_VALUE_0"]) == (
        "1", "safe.directory", str(fake))


def test_AT_950_3_1_a_large_body_reaches_the_child_intact(fake: Path) -> None:
    raw = ('{"pad":"' + "壹貳參" * 7000 + '"}').encode()          # 約 63 KB：遠大於管道緩衝
    assert 60000 < len(raw) <= 65536
    si_cli.run_validate(fake, raw)
    assert base64.b64decode(read_calls(fake)[-1]["stdin_b64"]) == raw


# ── AT-950-3-E-1：validate 失敗形態 ───────────────────────────────────────────────────────────
VALIDATE_FAILURES: list[tuple[str, Any, str, str]] = [
    # (名稱, 準備函式, 期望 cause, 期望 detail 的 rc 段)
    ("a-nonzero-rc-3", _control(rc=3, stderr=STDERR_G), "nonzero_rc", "3"),
    ("a2-nonzero-rc-2", _control(rc=2, dry_run=DEFAULT_DRY_RUN), "nonzero_rc", "2"),
    ("b-garbage-stdout", _control(raw_stdout="這不是 JSON"), "bad_json", "0"),
    ("b2-garbage-stdout-rc1", _control(raw_stdout="還是垃圾", rc=1), "bad_json", "1"),
    ("b3-array", _control(raw_stdout="[1, 2]\n"), "bad_json", "0"),
    ("b4-two-documents", _control(raw_stdout='{"ok": true}{"ok": false}'), "bad_json", "0"),
    ("c-missing-ok", _control(dry_run={k: v for k, v in DEFAULT_DRY_RUN.items() if k != "ok"}),
     "bad_shape", "0"),
    ("c2-findings-not-array", _control(dry_run={**DEFAULT_DRY_RUN, "findings": "x"}),
     "bad_shape", "0"),
    ("c3-ok-not-bool", _control(dry_run={**DEFAULT_DRY_RUN, "ok": "yes"}), "bad_shape", "0"),
    ("c4-row-bytes-bool", _control(dry_run={**DEFAULT_DRY_RUN, "row_bytes": True}),
     "bad_shape", "0"),
    ("c5-row-max-bytes-missing",
     _control(dry_run={k: v for k, v in DEFAULT_DRY_RUN.items() if k != "row_max_bytes"}),
     "bad_shape", "0"),
    ("c6-row-not-string", _control(dry_run={**DEFAULT_DRY_RUN, "row": 5}), "bad_shape", "0"),
    ("d-stdout-too-large", _too_large, "stdout_too_large", "none"),
    ("e-si-root-none", _no_root, "si_root_unset", "none"),
    ("f-dir-missing", _missing_dir, "si_script_missing", "none"),
    ("g-script-missing", _no_script, "si_script_missing", "none"),
    ("h-spawn-error", _spawn_error, "spawn_failed", "none"),
]


@pytest.mark.parametrize("name,prepare,cause,rc_text", VALIDATE_FAILURES,
                         ids=[c[0] for c in VALIDATE_FAILURES])
def test_AT_950_3_E_1_every_validate_failure_form_maps_to_503_with_a_fixed_cause(
        name: str, prepare: Any, cause: str, rc_text: str, tmp_path: Path, fake: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    root = prepare(tmp_path, fake, monkeypatch)
    err = fail_of(lambda: si_cli.run_validate(root, b'{"user":"admin"}'))
    assert (err.status_code, err.body["reason"]) == (503, "si_unavailable"), name
    assert err.body["cause"] == cause, f"{name}：{err.body}"
    detail = err.body["detail"]
    assert DETAIL_FORMAT.match(detail), f"{name}：detail 格式不合 {detail!r}"
    assert detail.startswith(f"rc={rc_text}; stderr="), f"{name}：{detail!r}"
    if cause == "nonzero_rc" and name.startswith("a-"):
        assert detail == f"rc=3; stderr={STDERR_G}"


def test_AT_950_3_E_1_a_timeout_kills_the_whole_process_tree(
        fake: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pids_file = fake / "fake_pids.json"
    for timeout in (2.0, 6.0):            # 同 export 的逾時測試：孫行程沒出生就換較長的逾時重試
        pids_file.unlink(missing_ok=True)
        set_control(fake, sleep=30, grandchild=True)
        monkeypatch.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", timeout)
        started = time.monotonic()
        err = fail_of(lambda: si_cli.run_validate(fake, b'{"user":"admin"}'))
        elapsed = time.monotonic() - started
        if pids_file.is_file():
            break
    assert pids_file.is_file(), "假 CLI 在逾時內沒能生出孫行程：環境太慢，無法驗證殺樹"
    assert err.body["cause"] == "timeout" and err.body["detail"].startswith("rc=none; stderr=")
    assert elapsed < 10, f"呼叫必須在有界時間內返回（實際 {elapsed:.1f} 秒）"
    pids = json.loads(pids_file.read_text(encoding="utf-8"))
    recorded = read_calls(fake)[-1]["pid"]
    for label, pid in (("假 CLI", recorded), ("孫行程", pids["grandchild"])):
        assert _gone(pid, 3.0), f"{label}（pid={pid}）逾時後仍存活＝孤兒行程"


def test_AT_950_3_E_1_a_child_that_never_reads_stdin_cannot_block_the_timeout(
        fake: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """子行程睡著不讀 stdin、本文又遠大於管道緩衝：餵 stdin 的寫入會卡住，但逾時仍必須準時生效，
    且行程樹被收掉、沒有孤兒。（換掉假 CLI 腳本：標準假 CLI 會先把 stdin 讀完。）"""
    script = fake / "tools" / "selfimproving.py"
    script.write_text("import time\ntime.sleep(60)\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", 1.5)
    raw = ('{"pad":"' + "x" * 300000 + '"}').encode()      # 遠大於任何平台的管道緩衝
    started = time.monotonic()
    err = fail_of(lambda: si_cli.run_validate(fake, raw))
    elapsed = time.monotonic() - started
    assert err.body["cause"] == "timeout" and err.body["detail"].startswith("rc=none; stderr=")
    assert elapsed < 10, f"餵 stdin 的寫入不得拖住逾時（實際 {elapsed:.1f} 秒）"
    stdin_writers = [t for t in threading.enumerate() if t.name == "si-stdin" and t.is_alive()]
    deadline = time.monotonic() + 5
    while stdin_writers and time.monotonic() < deadline:
        time.sleep(0.05)
        stdin_writers = [t for t in threading.enumerate() if t.name == "si-stdin" and t.is_alive()]
    assert not stdin_writers, "子行程被殺後，卡住的 stdin 寫入執行緒必須隨管道關閉而結束"
