"""Bridge 對 AISDLC_SDD FSM 的**唯一**寫入通道：FSMRuntime CLI 子行程（ADR-XPLAT-016 §3.5、§4.1、
§9）。

Rule 9 絕對禁令 #1（繞過 FSMRuntime 直接讀寫 FSM-STATE-*.yaml）在這裡的落實：
  · Bridge 原始碼不開寫 `FSM-STATE-*.yaml`；所有狀態變更都是
    `python -m tools.fsm_runtime.fsm_runtime
    <動詞> …` 子行程。tests/test_sdd_integration_parity.py 的 AST 鎖掃整個 `app/`（F-4）。
  · **動詞白名單**（`ALLOWED_VERBS`＋每個動詞的旗標白名單）：`spec-frozen`（僅經 `:freeze`）、
    `negotiate-enter`、`negotiate-exit --outcome agreed`、`delegate-enter`、
    `delegate-exit --decision
    done｜failed`。其餘（`transition`、`gate`、`resume-from-escalation`、`negotiate-exit --outcome
    underspecified`…）Bridge 一律不呼叫；越界在**送出前**就 500 `sdd_cli_usage`。
  · 固定環境：以 `os.environ` 為底，**移除所有 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`**，再設
    `PYTHONPATH=<SDD 版本目錄>`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1`、兩個遙測旗標 `0`、
    `SDD_STATE_DIR=<專案根>/build/reports/fsm`、`SDD_PROJECT=<專案鍵>`——不洩漏 DB 密碼與寫入權杖給
    子行程，Docker 唯讀掛載 `/sdd` 下 CLI 也不會寫版本目錄（遙測關、不寫 pyc）。
  · `(狀態目錄, 專案鍵)` 互斥鎖（`state_guard`）同時罩住「CLI 呼叫」與「`GET /sdd/fsm/{project}`
    的檔案讀取」：消除 Bridge 自己「讀的當下被 `os.replace` 換檔」的 Windows 共享違規。

跨平台：子行程旗標走 `procutil.popen_platform_kwargs()`（Windows＝新行程組＋無視窗；POSIX＝新
session）；逾時以行程樹終止（`procutil.begin_terminate`，不直接 `os.kill`）。Windows 行為＝venv 的
`python.exe`是啟動器、真正的直譯器是它的子行程，所以逾時必須殺整棵樹。
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import unicodedata
import weakref
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from . import procutil
from .errors import ApiError, fsm_state_conflict
from .security import AuditLog
from .tracing import trace_id_var

logger = logging.getLogger("bridge.sdd_cli")

#: CLI 模組路徑——整個 `app/` 只有這裡出現這串字面（AST 鎖：唯一的子行程呼叫處）。
CLI_MODULE = "tools.fsm_runtime.fsm_runtime"
DEFAULT_TIMEOUT_SECONDS = 20.0
#: 逾時後等行程樹退出的寬限；仍不退就強殺。
_REAP_GRACE_SECONDS = 3.0
#: 稽核只留 stderr 的尾端這麼多字元（診斷用；回應不含）。
_STDERR_AUDIT_CHARS = 2048

VERB_SPEC_FROZEN = "spec-frozen"
VERB_NEGOTIATE_ENTER = "negotiate-enter"
VERB_NEGOTIATE_EXIT = "negotiate-exit"
VERB_DELEGATE_ENTER = "delegate-enter"
VERB_DELEGATE_EXIT = "delegate-exit"

#: 動詞白名單（ADR §3.5）。新增動詞＝改這裡、改 ADR、改測試；沒有別的路。
ALLOWED_VERBS: frozenset[str] = frozenset({
    VERB_SPEC_FROZEN, VERB_NEGOTIATE_ENTER, VERB_NEGOTIATE_EXIT,
    VERB_DELEGATE_ENTER, VERB_DELEGATE_EXIT,
})

#: 每個動詞可帶的旗標（`--project`／`--must-exist` 由 `run_verb` 自己加，呼叫端不得帶）。
_VERB_FLAGS: dict[str, frozenset[str]] = {
    VERB_SPEC_FROZEN: frozenset({"--stage", "--doc", "--digest", "--root", "--reason",
                                 "--approver", "--json"}),
    VERB_NEGOTIATE_ENTER: frozenset({"--reason", "--contract-ref"}),
    VERB_NEGOTIATE_EXIT: frozenset({"--outcome", "--reason"}),
    VERB_DELEGATE_ENTER: frozenset({"--reason", "--playbook-ref"}),
    VERB_DELEGATE_EXIT: frozenset({"--decision", "--reason"}),
}
_BOOL_FLAGS = frozenset({"--digest", "--json"})
#: 四個新動詞的 `--reason` 必填（它是寫進 decision_trace 的稽核憑證；缺＝CLI rc 4）。
_REASON_REQUIRED = frozenset({VERB_NEGOTIATE_ENTER, VERB_NEGOTIATE_EXIT, VERB_DELEGATE_ENTER,
                              VERB_DELEGATE_EXIT})
NEGOTIATE_EXIT_OUTCOMES: frozenset[str] = frozenset({"agreed"})
DELEGATE_EXIT_DECISIONS: frozenset[str] = frozenset({"done", "failed"})


# ── 參數建構（呼叫端用這些，不手寫 argv 片段）─────────────────────────────────────────────
def freeze_args(*, stage: str, docs: Sequence[str], root: str, reason: str,
                approver: str) -> list[str]:
    args = ["--stage", stage]
    for doc in docs:
        args += ["--doc", doc]
    return [*args, "--digest", "--root", root, "--reason", reason, "--approver", approver, "--json"]


def negotiate_enter_args(*, reason: str, contract_ref: str | None = None) -> list[str]:
    args = ["--reason", reason]
    return [*args, "--contract-ref", contract_ref] if contract_ref else args


def negotiate_exit_args(*, reason: str) -> list[str]:
    return ["--outcome", "agreed", "--reason", reason]


def delegate_enter_args(*, reason: str, playbook_ref: str | None = None) -> list[str]:
    args = ["--reason", reason]
    return [*args, "--playbook-ref", playbook_ref] if playbook_ref else args


def delegate_exit_args(*, decision: str, reason: str) -> list[str]:
    return ["--decision", decision, "--reason", reason]


# ── 白名單檢查 ──────────────────────────────────────────────────────────────────────────
def _usage(detail: str) -> ApiError:
    return ApiError(500, "sdd_cli_usage", detail=detail)


def check_allowed(verb: str, args: Sequence[str]) -> None:
    """動詞與旗標越界一律 500 `sdd_cli_usage`（Bridge 自己的 bug；測試必須零次出現）。"""
    if verb not in ALLOWED_VERBS:
        raise _usage(f"verb not allowed: {verb!r}")
    allowed = _VERB_FLAGS[verb]
    seen: dict[str, list[str]] = {}
    i = 0
    while i < len(args):
        flag = args[i]
        if flag not in allowed:
            raise _usage(f"flag not allowed for {verb}: {flag!r}")
        if flag in _BOOL_FLAGS:
            seen.setdefault(flag, []).append("")
            i += 1
            continue
        if i + 1 >= len(args):
            raise _usage(f"flag {flag} for {verb} has no value")
        seen.setdefault(flag, []).append(str(args[i + 1]))   # 值（含以 `--` 開頭的理由）原樣吃掉
        i += 2
    if verb in _REASON_REQUIRED and not (seen.get("--reason") and seen["--reason"][0].strip()):
        raise _usage(f"{verb} requires a non-empty --reason")
    if verb == VERB_NEGOTIATE_EXIT and seen.get("--outcome") not in (["agreed"],):
        raise _usage("negotiate-exit only allows --outcome agreed")
    if verb == VERB_DELEGATE_EXIT:
        decisions = seen.get("--decision", [])
        if len(decisions) != 1 or decisions[0] not in DELEGATE_EXIT_DECISIONS:
            raise _usage("delegate-exit requires --decision done|failed")


# ── 固定環境 ────────────────────────────────────────────────────────────────────────────
def _is_stripped_name(name: str) -> bool:
    upper = name.upper()           # Windows 的環境變數名不分大小寫：一律照大寫比
    return upper.startswith(("BRIDGE_", "SDD_")) or upper == "PYTHONPATH"


def build_cli_env(base: Mapping[str, str], *, sdd_root: Path, state_dir: Path,
                  project: str) -> dict[str, str]:
    env = {k: v for k, v in base.items() if not _is_stripped_name(k)}
    env.update({
        "PYTHONPATH": str(sdd_root),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "SDD_ENABLE_RULE_FIRE_TELEMETRY": "0",
        "SDD_ENABLE_RULE_CATCH_TELEMETRY": "0",
        "SDD_STATE_DIR": str(state_dir),
        "SDD_PROJECT": project,
    })
    return env


def build_cli_argv(verb: str, args: Sequence[str], project: str) -> list[str]:
    return [sys.executable, "-W", "ignore::RuntimeWarning", "-m", CLI_MODULE, verb,
            "--project", project, "--must-exist", *args]


# ── (狀態目錄, 專案鍵) 互斥鎖 ───────────────────────────────────────────────────────────────
_locks: weakref.WeakValueDictionary[tuple[str, str], Any] = weakref.WeakValueDictionary()
_locks_guard = threading.Lock()


def _lock_key(state_dir: Path, project: str) -> tuple[str, str]:
    # Windows 行為＝路徑與檔名不分大小寫：目錄 normcase、專案鍵 casefold，寧可多互斥也不漏。
    return (os.path.normcase(str(Path(state_dir).resolve())),
            unicodedata.normalize("NFC", project).casefold())


@contextmanager
def state_guard(state_dir: Path, project: str) -> Iterator[None]:
    """行程內以 `(狀態目錄, 專案鍵)` 為鍵的可重入鎖。罩住 CLI 呼叫與狀態檔讀取；呼叫端可在同一個
    臨界區內連續呼叫多次 CLI（可重入）。鎖表是弱參照：沒有人持有時自動回收，不會無限長大。"""
    key = _lock_key(state_dir, project)
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _locks[key] = lock
    with lock:
        yield


# ── 執行 ────────────────────────────────────────────────────────────────────────────────
def _last_json_line(stdout: str) -> dict[str, Any] | None:
    """stdout 取最後一個非空行解析為 JSON 物件；不是就 None（契約：CLI 的 stdout 恰好一行
    JSON）。"""
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        payload = json.loads(lines[-1])
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _ascii(text: Any, limit: int = 200) -> str:
    return str(text).encode("ascii", "replace").decode("ascii")[:limit]


def _reap(proc: subprocess.Popen[bytes]) -> tuple[bytes, bytes]:
    """逾時：先終止整棵行程樹，寬限內不退才強殺，最後收掉殘留輸出。"""
    victims = procutil.begin_terminate(proc.pid)
    try:
        proc.wait(timeout=_REAP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        procutil.force_kill(procutil.survivors(victims))
    try:
        return proc.communicate(timeout=_REAP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        procutil.force_kill(procutil.survivors(victims))
        return b"", b""


def _map_failure(verb: str, project: str, rc: int, payload: dict[str, Any] | None) -> ApiError:
    """rc 表→ApiError（ADR §4.1）。回應只帶 CLI 自己設計成可顯示的 ASCII `error`／`detail`，
    不帶 stderr（stderr 只進稽核）。"""
    error = _ascii(payload.get("error", "")) if payload else ""
    detail = _ascii(payload.get("detail", "")) if payload else ""
    current = payload.get("current_state") if payload else None
    if rc == 3:
        return fsm_state_conflict(current, cli_error=error or "transition_not_allowed",
                                  message=detail)
    if rc == 4:
        return ApiError(422, "sdd_invalid_argument", error=error, detail=detail or f"{verb} rc=4")
    if rc == 5:
        if error == "state_not_found":
            return ApiError(404, "fsm_not_found", project=project)
        return ApiError(422, "fsm_state_unreadable", detail=detail or "state file unreadable")
    if rc == 2:
        return ApiError(500, "sdd_cli_usage",
                        detail=detail or f"{verb} rejected its arguments (rc=2)")
    return ApiError(502, "sdd_cli_failed",
                    detail=detail or f"{verb} exited with rc={rc} (see the Bridge audit log)")


def run_verb(verb: str, args: Sequence[str], *, sdd_root: Path | None, state_dir: Path,
             project: str, timeout: float | None = None,
             audit: AuditLog | None = None, approver: str | None = None,
             context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """以子行程跑一個白名單動詞，回傳 CLI 的單行 JSON（物件）。失敗一律是 `ApiError`。

    · rc 0＝回傳 JSON（含 `"noop": true` 的情形）；1→502 `sdd_cli_failed`；2→500 `sdd_cli_usage`；
      3→409 `fsm_state_conflict`；4→422 `sdd_invalid_argument`；5→404 `fsm_not_found`／422
      `fsm_state_unreadable`；逾時→504 `sdd_cli_timeout`；無法啟動→502 `sdd_cli_failed`。
    · 每次呼叫（成功或失敗）都記一筆稽核 `sdd_cli`：project、approver、動詞、rc、結果、trace_id，
      失敗另附 stderr 尾端；**絕不記環境、權杖、`--reason` 文字**。請求層的決策（`:freeze`、含
      `sdd` 的建立 run；成功或被拒）由路由另記 `sdd_write`（ADR §9），兩者以 trace_id 對得上。
    · 呼叫端要序列化就自己包 `state_guard`（可重入，同一臨界區內可連呼多次）。
    """
    check_allowed(verb, args)
    if timeout is None:                 # 呼叫時才讀常數：測試可以改它，不必等 20 秒
        timeout = DEFAULT_TIMEOUT_SECONDS
    if sdd_root is None or not Path(sdd_root).is_dir():
        raise ApiError(503, "sdd_unavailable",
                       detail="找不到 AISDLC_SDD 目錄；請設定 SDD_ROOT（Docker 需掛載）")
    argv = build_cli_argv(verb, args, project)
    env = build_cli_env(os.environ, sdd_root=Path(sdd_root), state_dir=Path(state_dir),
                        project=project)

    def audit_call(result: str, rc: int | None, stderr: str = "") -> None:
        if audit is None:
            return
        fields: dict[str, Any] = {
            "verb": verb, "project": project, "approver": approver, "result": result, "rc": rc,
            "trace_id": trace_id_var.get(), **(context or {})}
        if stderr:
            fields["stderr_tail"] = stderr[-_STDERR_AUDIT_CHARS:]
        audit.record("sdd_cli", **fields)

    try:
        proc = subprocess.Popen(
            argv, cwd=str(sdd_root), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, **procutil.popen_platform_kwargs())
    except OSError as exc:
        audit_call(f"spawn_error:{type(exc).__name__}", None)
        raise ApiError(502, "sdd_cli_failed",
                       detail=f"cannot start the sdd cli ({type(exc).__name__})") from exc
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        out, err = _reap(proc)
        audit_call("timeout", None, err.decode("utf-8", errors="replace"))
        raise ApiError(504, "sdd_cli_timeout",
                       detail=f"{verb} did not finish within {timeout:g}s") from exc
    stdout, stderr = out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")
    payload = _last_json_line(stdout)
    rc = proc.returncode
    if rc == 0:
        if payload is None:
            audit_call("bad_output", rc, stderr)
            raise ApiError(502, "sdd_cli_failed",
                           detail=f"{verb} succeeded but stdout is not a single JSON line")
        audit_call("ok", rc)
        return payload
    failure = _map_failure(verb, project, rc, payload)
    audit_call(f"rc={rc}:{failure.body['reason']}", rc, stderr)
    raise failure
