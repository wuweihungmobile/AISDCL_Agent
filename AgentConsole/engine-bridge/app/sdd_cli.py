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

研究面（ResearchToPRD；ADR-XPLAT-017 D2、D4）：檔尾另有**獨立**的研究面動詞表 `RESEARCH_VERBS`
（`show`、`transition`、`gate`、`spec-frozen`、`spec-refreeze`）、旗標白名單
`_RESEARCH_VERB_FLAGS`、檢查函式 `check_research_allowed`、組裝函式與執行入口
`run_research_verb`。上面的 `ALLOWED_VERBS`、`_VERB_FLAGS`、`run_verb` 一字不動：研究面動詞只對
`/research/*` 開放，不開放給 `:freeze` 與 `/autoclaude/runs` 的 `sdd` 區塊；`resume-from-escalation`
永不入表（ESCALATION 只有人能解）。外環鍵（`research-<slug>`）的每次呼叫環境固定
`SDD_ENABLE_AUTO_RECOVERY=0`。
"""
from __future__ import annotations

import json
import logging
import os
import re
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


# ══ 研究面（ResearchToPRD；ADR-XPLAT-017 D2、D4、§4）══════════════════════════════════════════
# 獨立於上面的 ALLOWED_VERBS／_VERB_FLAGS／run_verb（那三者零改動）。研究面動詞只對 `/research/*`
# 開放；每個值域都表驅動，越界在送出前就 500 `sdd_cli_usage`、且不起子行程。
RESEARCH_VERB_SHOW = "show"
RESEARCH_VERB_TRANSITION = "transition"
RESEARCH_VERB_GATE = "gate"
RESEARCH_VERB_SPEC_FROZEN = VERB_SPEC_FROZEN
RESEARCH_VERB_SPEC_REFREEZE = "spec-refreeze"

#: 研究面動詞表。`resume-from-escalation`、`reconcile`、`spec-audit`、`check-impl`、
#: `complete-auto-compact`、`reset-ledger`、`negotiate-*`、`delegate-*` 一律不入表。
RESEARCH_VERBS: frozenset[str] = frozenset({
    RESEARCH_VERB_SHOW, RESEARCH_VERB_TRANSITION, RESEARCH_VERB_GATE,
    RESEARCH_VERB_SPEC_FROZEN, RESEARCH_VERB_SPEC_REFREEZE,
})

#: 每個動詞可帶的旗標（`--project`／`--must-exist` 由 `run_research_verb` 自己加，呼叫端不得帶）。
_RESEARCH_VERB_FLAGS: dict[str, frozenset[str]] = {
    RESEARCH_VERB_SHOW: frozenset(),
    RESEARCH_VERB_TRANSITION: frozenset({"--to", "--reason", "--trigger"}),
    RESEARCH_VERB_GATE: frozenset({"--gate", "--result", "--reason"}),
    RESEARCH_VERB_SPEC_FROZEN: frozenset({"--stage", "--doc", "--digest", "--root", "--reason",
                                          "--approver", "--json"}),
    RESEARCH_VERB_SPEC_REFREEZE: frozenset({"--doc", "--root", "--reason", "--approver"}),
}
_RESEARCH_REPEATABLE_FLAGS = frozenset({"--doc"})

#: `transition --trigger` 的固定值（decision_trace 的來源標記）。
RESEARCH_TRIGGER = "research_bridge"
#: 外環鍵 `research-<slug>[-g<N>]`（世代鍵 `-g<N>` 是換世代的新鍵）；其餘鍵一律視為內環鍵。
OUTER_KEY_RE = re.compile(r"^research-[a-z0-9][a-z0-9-]{0,29}(-g[0-9]+)?$")
#: `transition --to` 的值域：外環只准前五值；內環另准 SPEC_AUDIT、PR_REVIEW、RELEASE。
OUTER_TRANSITION_TARGETS: frozenset[str] = frozenset({
    "SCENARIO_DETECT", "AGENT_LOAD", "SPEC_DRAFTING", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK"})
INNER_TRANSITION_TARGETS: frozenset[str] = OUTER_TRANSITION_TARGETS | {
    "SPEC_AUDIT", "PR_REVIEW", "RELEASE"}
#: 內環鍵的基線採納路徑：現態為 SCG_VALIDATION 時 `--to HUMAN_PENDING`，且 `--reason` 以此起頭。
BASELINE_ADOPTION_TARGET = "HUMAN_PENDING"
BASELINE_ADOPTION_REASON_PREFIX = "baseline adoption"
OUTER_GATES: frozenset[str] = frozenset({"SCG_VALIDATION"})
INNER_GATES: frozenset[str] = frozenset({"PR_REVIEW", "RTM_VERIFY", "RELEASE_READY"})
GATE_RESULTS: tuple[str, ...] = ("PASS", "FAIL")
#: `spec-frozen --stage` 的值域：外環只准 Gate-0、Gate-0-SCR<n>、Stage-1；內環只准 Stage-1。
OUTER_FREEZE_STAGE_RE = re.compile(r"^(Gate-0(-SCR[0-9]+)?|Stage-1)$")
INNER_FREEZE_STAGES: frozenset[str] = frozenset({"Stage-1"})
#: 核准人（`--approver`）：JWT subject，由 console-api 轉入；Bridge 再驗一次。
RESERVED_APPROVERS: frozenset[str] = frozenset({"bridge", "agent", "system"})
APPROVER_MAX_CHARS = 100
_APPROVER_RE = re.compile(r"^[A-Za-z0-9._@-]+$")
#: 外環鍵的子行程環境固定關閉自動恢復（審查分數不足不得被自動恢復；R-9.5、禁令 6）。
RESEARCH_AUTO_RECOVERY_ENV = "SDD_ENABLE_AUTO_RECOVERY"
_TRANSITION_OK_RE = re.compile(r"^OK transitioned to (\S+)\s*$")


def is_outer_key(key: str) -> bool:
    return OUTER_KEY_RE.fullmatch(key) is not None


#: 內環鍵（D-119）：`^[a-z][a-z0-9-]{1,99}$` 且不是外環鍵形態（軌道 A＝`<module>-<slug>`、軌道 B＝
#: `<project_name>`）。建檔只在分流（`research/adopt.py`）以 `inner_create=True` 明示。
INNER_KEY_RE = re.compile(r"^[a-z][a-z0-9-]{1,99}$")


def is_inner_key(key: str) -> bool:
    return INNER_KEY_RE.fullmatch(key) is not None and not is_outer_key(key)


def validate_research_approver(raw: object) -> str:
    """核准人驗證：非空、非保留字（`bridge`／`agent`／`system`，不分大小寫）、≤100 字、只含
    `[A-Za-z0-9._@-]`（所以空白與 `+` 皆不合）、且不得以 `-` 起頭（argv 注入）。不合＝422
    `invalid_request`（`violations[{field,rule,message}]`）；合格原樣回傳（不 strip）。"""
    value = raw if isinstance(raw, str) else ""
    rules: list[tuple[str, str]] = []
    if not value:
        rules.append(("required", "approver 必填"))
    else:
        if value.casefold() in RESERVED_APPROVERS:
            rules.append(("reserved", "approver 不得是保留字 bridge／agent／system"))
        if len(value) > APPROVER_MAX_CHARS:
            rules.append(("too_long", f"approver 不得超過 {APPROVER_MAX_CHARS} 字元"))
        if not _APPROVER_RE.fullmatch(value):
            rules.append(("invalid_chars", "approver 只准 [A-Za-z0-9._@-]（不含空白與 +）"))
        if value.startswith("-"):
            rules.append(("leading_dash", "approver 不得以 - 起頭"))
    if rules:
        raise ApiError(422, "invalid_request", violations=[
            {"field": "approver", "rule": rule, "message": message} for rule, message in rules])
    return value


def research_transition_args(*, to: str, reason: str) -> list[str]:
    return ["--to", to, "--reason", reason, "--trigger", RESEARCH_TRIGGER]


def research_gate_args(*, gate: str, result: str, reason: str) -> list[str]:
    return ["--gate", gate, "--result", result, "--reason", reason]


def research_freeze_args(*, stage: str, docs: Sequence[str], root: str, reason: str,
                         approver: str) -> list[str]:
    """`spec-frozen` 的研究面 argv（含 `--digest --json`）。核准人在**這個函式內**驗證並組進 argv
    （驗證與組裝不拆開：沒有「驗過」與「組的」兩份不同的值）。"""
    checked = validate_research_approver(approver)
    args = ["--stage", stage]
    for doc in docs:
        args += ["--doc", doc]
    return [*args, "--digest", "--root", root, "--reason", reason, "--approver", checked,
            "--json"]


def research_refreeze_args(*, docs: Sequence[str], root: str, reason: str,
                           approver: str) -> list[str]:
    checked = validate_research_approver(approver)
    args: list[str] = []
    for doc in docs:
        args += ["--doc", doc]
    return [*args, "--root", root, "--reason", reason, "--approver", checked]


def check_research_allowed(verb: str, args: Sequence[str], *, key: str) -> None:
    """研究面動詞、旗標與值域的檢查（表驅動；依鍵類別＝外環或內環）。越界一律 500
    `sdd_cli_usage`（Bridge 自己的 bug；測試必須零次出現），且在起子行程之前。

    呼叫端不得帶 `--project`、`--must-exist`（由 `run_research_verb` 加）；每個旗標至多一次
    （`--doc` 可重複）；值原樣吃掉（含以 `--` 起頭的理由）。"""
    if verb not in RESEARCH_VERBS:
        raise _usage(f"verb not allowed: {verb!r}")
    allowed = _RESEARCH_VERB_FLAGS[verb]
    outer = is_outer_key(key)
    seen: dict[str, list[str]] = {}
    i = 0
    while i < len(args):
        flag = str(args[i])
        if flag not in allowed:
            raise _usage(f"flag not allowed for {verb}: {flag!r}")
        if flag in _BOOL_FLAGS:
            if flag in seen:
                raise _usage(f"flag {flag} for {verb} given twice")
            seen[flag] = [""]
            i += 1
            continue
        if i + 1 >= len(args):
            raise _usage(f"flag {flag} for {verb} has no value")
        value = str(args[i + 1])
        if "\x00" in value:
            raise _usage(f"flag {flag} for {verb} has a NUL in its value")
        if flag in seen and flag not in _RESEARCH_REPEATABLE_FLAGS:
            raise _usage(f"flag {flag} for {verb} given twice")
        seen.setdefault(flag, []).append(value)
        i += 2

    def one(flag: str) -> str | None:
        values = seen.get(flag)
        return values[0] if values else None

    def need_text(flag: str) -> str:
        value = one(flag)
        if value is None or not value.strip():
            raise _usage(f"{verb} requires a non-empty {flag}")
        return value

    if verb == RESEARCH_VERB_TRANSITION:
        target, reason = one("--to"), need_text("--reason")
        if one("--trigger") != RESEARCH_TRIGGER:
            raise _usage(f"transition requires --trigger {RESEARCH_TRIGGER}")
        if target == BASELINE_ADOPTION_TARGET:
            if outer or not reason.startswith(BASELINE_ADOPTION_REASON_PREFIX):
                raise _usage("transition --to HUMAN_PENDING is only the inner-key baseline "
                             f"adoption path (reason must start with "
                             f"{BASELINE_ADOPTION_REASON_PREFIX!r})")
        elif target not in (OUTER_TRANSITION_TARGETS if outer else INNER_TRANSITION_TARGETS):
            raise _usage(f"transition --to {target!r} is not allowed for this key class")
    elif verb == RESEARCH_VERB_GATE:
        need_text("--reason")
        if one("--gate") not in (OUTER_GATES if outer else INNER_GATES):
            raise _usage(f"gate --gate {one('--gate')!r} is not allowed for this key class")
        if one("--result") not in GATE_RESULTS:
            raise _usage("gate --result must be PASS or FAIL")
    elif verb == RESEARCH_VERB_SPEC_FROZEN:
        stage = one("--stage")
        if stage is None or not (OUTER_FREEZE_STAGE_RE.fullmatch(stage) if outer
                                 else stage in INNER_FREEZE_STAGES):
            raise _usage(f"spec-frozen --stage {stage!r} is not allowed for this key class")
        for flag in ("--reason", "--approver", "--root"):
            need_text(flag)
        if not seen.get("--doc") or "--digest" not in seen or "--json" not in seen:
            raise _usage("spec-frozen requires --doc (at least one), --digest and --json")
    elif verb == RESEARCH_VERB_SPEC_REFREEZE:
        for flag in ("--reason", "--approver", "--root"):
            need_text(flag)
        if not seen.get("--doc"):
            raise _usage("spec-refreeze requires at least one --doc")


def build_research_argv(verb: str, args: Sequence[str], project: str, *,
                        create: bool = False) -> list[str]:
    """研究面的 argv（列表、不經 shell）。`create`＝建檔專用的 `show`：**唯一不帶 `--must-exist`**
    的形態（缺檔時框架 CLI 依模板建出 INIT 狀態檔）；其餘一律恆附 `--must-exist`。"""
    guard = [] if create else ["--must-exist"]
    return [sys.executable, "-W", "ignore::RuntimeWarning", "-m", CLI_MODULE, verb,
            "--project", project, *guard, *args]


def build_research_env(base: Mapping[str, str], *, sdd_root: Path, state_dir: Path,
                       project: str) -> dict[str, str]:
    """`build_cli_env` 的固定環境，外環鍵另加 `SDD_ENABLE_AUTO_RECOVERY=0`（ADR-XPLAT-017 D4）。
    `BRIDGE_*`、`SDD_*`（除固定集合）、`PYTHONPATH` 一律先移除再重建。"""
    env = build_cli_env(base, sdd_root=sdd_root, state_dir=state_dir, project=project)
    if is_outer_key(project):
        env[RESEARCH_AUTO_RECOVERY_ENV] = "0"
    return env


def _research_payload(verb: str, stdout: str) -> dict[str, Any] | None:
    """各動詞的成功輸出形態不同：`show` 是多行 JSON（整段解析）、`transition` 是純文字
    `OK transitioned to X`、其餘是單行 JSON。解不出來＝None（呼叫端回 502，不靜默通過）。"""
    if verb == RESEARCH_VERB_SHOW:
        try:
            doc = json.loads(stdout)
        except ValueError:
            return None
        return doc if isinstance(doc, dict) else None
    if verb == RESEARCH_VERB_TRANSITION:
        lines = [ln for ln in stdout.splitlines() if ln.strip()]
        match = _TRANSITION_OK_RE.match(lines[-1]) if lines else None
        return {"ok": True, "verb": verb, "current_state": match.group(1)} if match else None
    return _last_json_line(stdout)


def run_research_verb(verb: str, args: Sequence[str], *, sdd_root: Path | None, state_dir: Path,
                      project: str, create: bool = False, timeout: float | None = None,
                      audit: AuditLog | None = None, approver: str | None = None,
                      context: Mapping[str, Any] | None = None,
                      inner_create: bool = False) -> dict[str, Any]:
    """以子行程跑一個研究面動詞，回傳解析後的輸出（物件）。失敗一律是 `ApiError`。

    研究面的**唯一**執行入口（與 `run_verb` 平行、互不呼叫）。rc→HTTP 與 `run_verb` 同表
    （1→502 `sdd_cli_failed`、2→500 `sdd_cli_usage`、3→409 `fsm_state_conflict`、4→422
    `sdd_invalid_argument`、5→404／422、逾時→504 `sdd_cli_timeout`）；每次呼叫都記一筆稽核
    `sdd_cli`（不含環境、權杖與 `--reason` 文字）。`create=True` 只准 `show` 且須是外環鍵。
    呼叫端要序列化就自己包 `state_guard`（可重入）。"""
    check_research_allowed(verb, args, key=project)
    if create and not (verb == RESEARCH_VERB_SHOW and (
            is_outer_key(project) or (inner_create and is_inner_key(project)))):
        raise _usage("create is only for `show` on an outer key (or an inner key with "
                     "inner_create=True)")
    if timeout is None:
        timeout = DEFAULT_TIMEOUT_SECONDS
    if sdd_root is None or not Path(sdd_root).is_dir():
        raise ApiError(503, "sdd_unavailable",
                       detail="找不到 AISDLC_SDD 目錄；請設定 SDD_ROOT（Docker 需掛載）")
    argv = build_research_argv(verb, args, project, create=create)
    env = build_research_env(os.environ, sdd_root=Path(sdd_root), state_dir=Path(state_dir),
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
    rc = proc.returncode
    if rc == 0:
        payload = _research_payload(verb, stdout)
        if payload is None:
            audit_call("bad_output", rc, stderr)
            raise ApiError(502, "sdd_cli_failed",
                           detail=f"{verb} succeeded but its stdout is not the expected shape")
        audit_call("ok", rc)
        return payload
    failure = _map_failure(verb, project, rc, _last_json_line(stdout))
    audit_call(f"rc={rc}:{failure.body['reason']}", rc, stderr)
    raise failure
