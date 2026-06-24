"""Subagent Dispatch Contract (ACT-020, Phase E M2).

Problem (see §E-01): when main session dispatches a subagent, the subagent
may work off a stale FSM-STATE snapshot. If the main FSM transitions to
ESCALATION / TERMINATED mid-flight, the subagent should *not* continue
producing artifacts under the assumption it is still IMPLEMENTATION.

This module provides:

1. `enter_subagent(name, stage)` — take a frozen FSM view before dispatch
   and record the contract entry to DISPATCH-LOG.
2. `verify_action_allowed(name, action, target=None)` — check the frozen
   view + live FSM agreement; returns (ok, reason).
3. `exit_subagent(name, result)` — write completion / failure back, track
   bypass events.

Rollout follows §9.2 of Automation_04 (Shadow → Soft → Hard):

    SDD_SUBAGENT_CONTRACT=0     → fully disabled (off entirely)
    SDD_SUBAGENT_CONTRACT=warn  → Shadow mode (log only, never blocks)
    SDD_SUBAGENT_CONTRACT=1     → Soft/Hard (default: Soft — can bypass via
                                   SDD_SUBAGENT_CONTRACT_BYPASS=<reason>)

All enforcement here is advisory — `verify_action_allowed` returns ok=False
so the caller can decide. Blocking in hooks is done via the existing FSM
guardrail, not by this module.
"""
from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .fsm_runtime import FSMRuntime
from .state_loader import REPO_ROOT

DISPATCH_LOG_DIR = REPO_ROOT / "build" / "reports" / "test-analysis"
BYPASS_LOG_DIR = REPO_ROOT / "build" / "reports" / "fsm"

# Registered subagent names (kept small to start — matches orchestrator).
REGISTERED: set[str] = {
    "dev-senior",
    "sa-analyst",
    "qa-tester",
    "qa-lead",
    "qa-automation",
    "devops-engineer",
    "sdd-orchestrator",
    "sdd-diagnostic",
    "code-analyzer",
    "technical-writer",
    "sd-architect",
    "pm-po",
    "security-engineer",
    "performance-engineer",
    "integration-specialist",
    "sdd-evaluator",   # Phase H M1 / ACT-046 — execution-grounded Evaluator
    "sdd-gc",          # Phase H M5 / ACT-055 — resident Scaffold GC agent
}

# Non-blocking terminal states — contract must refuse new dispatches.
# ESCALATION_FINAL added per Rule §9.14.4: failed auto-recovery must block all
# tool calls equivalently to ESCALATION (Phase G M1).
_BLOCKING_STATES = {"ESCALATION", "ESCALATION_FINAL", "TERMINATED", "TOKEN_BUDGET_CRITICAL"}

# Stage → allowed target prefixes for Write/Edit. Everything else is outside
# the agent's remit for that stage (matches FSM guardrail in fsm_runtime).
_STAGE_SPEC_STATES = {
    "SPEC_DRAFTING", "SPEC_AUDIT", "SPEC_REGRESSION_CHECK",
    "RESUME_VERIFICATION", "INIT", "SCENARIO_DETECT", "AGENT_LOAD",
}
_SPEC_TARGET_PREFIXES = (
    "docs/01_requirements/",
    "docs/02_architecture/",
    "docs/03_testing/",
)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def mode() -> str:
    """Resolve current enforcement mode from env. Returns one of:
       'off', 'shadow', 'soft', 'hard'.

    Priority order matches §9.2: env → default=soft.
    """
    raw = os.environ.get("SDD_SUBAGENT_CONTRACT", "").strip().lower()
    if raw == "0":
        return "off"
    if raw == "warn":
        return "shadow"
    if raw in {"hard", "enforce"}:
        return "hard"
    # "1" or empty -> soft by default
    return "soft"


def _dispatch_log_path() -> Path:
    DISPATCH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return DISPATCH_LOG_DIR / f"DISPATCH-LOG-{_dt.date.today().isoformat()}.yaml"


def _bypass_log_path() -> Path:
    BYPASS_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return BYPASS_LOG_DIR / f"SUBAGENT-BYPASS-{_dt.date.today().isoformat()}.yaml"


def _append_yaml(path: Path, key: str, entry: Dict[str, Any]) -> None:
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return
    doc: Dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    items: List[Dict[str, Any]] = doc.get(key) or []
    items.append(entry)
    doc[key] = items
    doc.setdefault("date", _dt.date.today().isoformat())
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, path)


def enter_subagent(
    agent_name: str,
    stage: Optional[str] = None,
    *,
    runtime: Optional[FSMRuntime] = None,
) -> Dict[str, Any]:
    """Snapshot the FSM before a subagent starts.

    Returns a frozen view: {"fsm_state": ..., "stage": ..., "entered_at": ...}
    Callers persist this dict and pass it to `verify_action_allowed`.
    """
    rt = runtime or FSMRuntime.bootstrap()
    view = {
        "agent": agent_name,
        "fsm_state": rt.state.current,
        "stage": stage or rt.current_stage_key(),  # QA Round-3 P2-03
        "entered_at": _now(),
        "mode": mode(),
        "registered": agent_name in REGISTERED,
    }
    _append_yaml(_dispatch_log_path(), "dispatches", {**view, "phase": "enter"})
    return view


def _maybe_soft_bypass(
    m: str,
    agent_name: str,
    action: str,
    target: Optional[str],
    refuse_reason: str,
) -> Optional[Tuple[bool, str]]:
    """If mode==soft and SDD_SUBAGENT_CONTRACT_BYPASS=<reason> is set, allow
    the action, audit it, and return (True, "[bypass] ..."). Hard mode never
    bypasses. Off/shadow handled by callers (do not reach here).
    """
    if m != "soft":
        return None
    bypass_value = os.environ.get("SDD_SUBAGENT_CONTRACT_BYPASS", "").strip()
    if not bypass_value:
        return None
    record_bypass(
        agent_name, action, target,
        reason=refuse_reason,
        env_value=bypass_value,
    )
    return True, f"[bypass] {refuse_reason}"


def verify_action_allowed(
    agent_name: str,
    action: str,
    target: Optional[str] = None,
    *,
    frozen_view: Optional[Dict[str, Any]] = None,
    runtime: Optional[FSMRuntime] = None,
) -> Tuple[bool, str]:
    """Return (ok, reason). `ok=False` means the contract rejects the action.

    Mode semantics:
    - off/shadow: always returns ok=True but `reason` may carry a warning
      for logging; callers should not block.
    - soft: returns ok=False when contract is violated, UNLESS env
      `SDD_SUBAGENT_CONTRACT_BYPASS=<reason>` is set — then audits as bypass
      and returns ok=True with `[bypass]` prefix.
    - hard: returns ok=False when contract is violated; bypass is impossible.
    """
    m = mode()
    rt = runtime or FSMRuntime.bootstrap()
    live_state = rt.state.current
    frozen_state = (frozen_view or {}).get("fsm_state")

    # Rule 1: live state is blocking — always refuse (even in shadow we warn).
    if live_state in _BLOCKING_STATES:
        reason = (
            f"live FSM state {live_state} blocks subagent actions "
            f"(agent={agent_name}, action={action})"
        )
        if m in {"off", "shadow"}:
            return True, f"[shadow] {reason}"
        bypass = _maybe_soft_bypass(m, agent_name, action, target, reason)
        if bypass is not None:
            return bypass
        return False, reason

    # Rule 2: if a frozen view was taken and the live state has moved to
    # a stricter state, refuse Write/Edit on spec files.
    if action in {"Write", "Edit"} and target:
        normalized = (target or "").replace("\\", "/")
        if any(p in normalized for p in _SPEC_TARGET_PREFIXES):
            if live_state not in _STAGE_SPEC_STATES:
                reason = (
                    f"spec write forbidden in state {live_state} "
                    f"(frozen_state={frozen_state}, agent={agent_name})"
                )
                if m in {"off", "shadow"}:
                    return True, f"[shadow] {reason}"
                bypass = _maybe_soft_bypass(m, agent_name, action, target, reason)
                if bypass is not None:
                    return bypass
                return False, reason

    # Rule 3: if frozen view drifted (e.g. entered IMPLEMENTATION, now in
    # ESCALATION) — already handled by Rule 1; anything else is ok.
    return True, "ok"


def record_bypass(
    agent_name: str,
    action: str,
    target: Optional[str],
    reason: str,
    *,
    env_value: Optional[str] = None,
) -> Optional[Path]:
    """Append a bypass audit entry. Called when hooks let an action through
    despite the contract refusing it (either via dry-run, shadow, or
    explicit SDD_SUBAGENT_CONTRACT_BYPASS=<reason>).

    In hard mode bypass is impossible — this function returns None without
    writing any audit entry, so callers cannot fabricate a bypass trail
    that contradicts the hard-mode contract (Rule 9.8.4).
    """
    if mode() == "hard":
        # Hard mode: no bypass allowed → no audit log written.
        # Surface a stderr warn so accidental callers are visible.
        import sys as _sys
        _sys.stderr.write(
            f"[SDD-SUBAGENT-CONTRACT][hard] record_bypass refused "
            f"(agent={agent_name}, action={action})\n"
        )
        return None
    path = _bypass_log_path()
    _append_yaml(path, "bypasses", {
        "ts": _now(),
        "agent": agent_name,
        "action": action,
        "target": target,
        "reason": reason,
        "env_value": env_value or os.environ.get("SDD_SUBAGENT_CONTRACT_BYPASS", ""),
        "mode": mode(),
    })
    return path


def exit_subagent(
    agent_name: str,
    result: str,
    *,
    frozen_view: Optional[Dict[str, Any]] = None,
) -> None:
    """Record subagent completion. `result` is free-form (PASS/FAIL/SKIP/...)."""
    entry = {
        "agent": agent_name,
        "phase": "exit",
        "result": result,
        "exited_at": _now(),
    }
    if frozen_view:
        entry["frozen_view"] = frozen_view
    _append_yaml(_dispatch_log_path(), "dispatches", entry)


def injection_hint_for_task(agent_name: str) -> Optional[str]:
    """Return text to inject into a Task prompt prefix.

    Hooks call this when the pre-tool event sees `tool_name == Task` and the
    subagent_type is registered. Shadow mode emits a reminder; soft/hard
    adds a stronger contract-binding notice.
    """
    if agent_name not in REGISTERED:
        return None
    m = mode()
    if m == "off":
        return None
    base = (
        f"[SDD-SUBAGENT-CONTRACT] agent={agent_name} — "
        "在開工前必須先讀取最新 FSM-STATE（tools/fsm_runtime），"
        "若 live 狀態 ∈ {ESCALATION, TERMINATED, TOKEN_BUDGET_CRITICAL} 請立即停止，"
        "不得在 IMPLEMENTATION 期間寫入 docs/01_requirements/ docs/02_architecture/ docs/03_testing/。"
    )
    if m == "shadow":
        return base + "\n[mode=shadow] 違反僅記錄於 SUBAGENT-BYPASS，不阻擋。"
    if m == "hard":
        return base + "\n[mode=hard] 違反將立即拒絕，需人工 override。"
    return base + "\n[mode=soft] 違反會被拒絕；如需繞過請設定 SDD_SUBAGENT_CONTRACT_BYPASS=<reason>。"


# ---------------------------------------------------------------- CLI helpers

def _cli() -> int:
    import argparse, json as _json
    parser = argparse.ArgumentParser(description="SDD Subagent Contract CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_enter = sub.add_parser("enter")
    p_enter.add_argument("--agent", required=True)
    p_enter.add_argument("--stage", default=None)
    p_exit = sub.add_parser("exit")
    p_exit.add_argument("--agent", required=True)
    p_exit.add_argument("--result", required=True)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--agent", required=True)
    p_verify.add_argument("--action", required=True)
    p_verify.add_argument("--target", default=None)
    args = parser.parse_args()

    if args.cmd == "enter":
        view = enter_subagent(args.agent, args.stage)
        print(_json.dumps(view, ensure_ascii=False))
    elif args.cmd == "exit":
        exit_subagent(args.agent, args.result)
        print("OK")
    elif args.cmd == "verify":
        ok, reason = verify_action_allowed(args.agent, args.action, args.target)
        print(_json.dumps({"ok": ok, "reason": reason, "mode": mode()}, ensure_ascii=False))
    return 0


EVAL_AGREEMENT_DIR = REPO_ROOT / "build" / "reports" / "eval"


def record_test_standard_agreement(
    *,
    contract_ref: str,
    acceptance_criteria: List[str],
    generator: str = "dev-senior",
    evaluator: str = "sdd-evaluator",
    generator_signed: bool = False,
    frozen_spec_sha: Optional[str] = None,
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Phase H M2 / ACT-050 — record the Dev↔QA Test-Contract negotiation.

    落實 SDD_improving_Automation_08.md §G3：IMPLEMENTATION 前，Evaluator 草擬
    每條 AC 的 pass/fail oracle，Generator 形式簽署。本函式把該共識持久化為
    TEST-CONTRACT-AGREEMENT-{date}.yaml，供 git 留痕 + 後續審計。

    `generator_signed=False` 代表 Generator 尚未簽署 → caller 不得進入 IMPLEMENTATION。

    Phase I M1 / ACT-063（PI-2 oracle stale）：新增 `frozen_spec_sha` — oracle
    凍結時對應的 spec 雜湊。進 EXECUTION_EVALUATION 前由 oracle_freshness.check()
    比對當前 spec sha；不符 → oracle stale → 回 TEST_CONTRACT_NEGOTIATED 重談判
    （評估器拿舊考卷改新答案的盲區，Phase H 完全沒檢測）。
    """
    target_dir = out_dir or EVAL_AGREEMENT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    date = _dt.date.today().isoformat()
    path = target_dir / f"TEST-CONTRACT-AGREEMENT-{date}.yaml"
    record = {
        "contract_ref": contract_ref,
        "generator": generator,
        "evaluator": evaluator,
        "acceptance_criteria": list(acceptance_criteria),
        "generator_signed": bool(generator_signed),
        "frozen_spec_sha": frozen_spec_sha,
        "recorded_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "ready_for_implementation": bool(generator_signed) and bool(acceptance_criteria),
    }
    import json as _json
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(_json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    record["path"] = str(path)
    return record


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
