"""Phase I M2 / ACT-064 — Runtime Monitor Synthesis（設計時證明 → 執行期 monitor）.

落實 SDD_improving_Automation_09.md §4.4 / PI-8：目前 retry/recovery 上限靠手寫
imperative if-check（fsm_runtime / auto_recovery），可與 SDD_FSM.tla 的 4 條 safety
invariant 靜默漂移。本模組把 .tla 的 4 條 safety invariant 編譯成「執行期 assertion」，
掛在 FSMRuntime.transition() 每次轉移後（env SDD_SPEC_MONITOR=1 啟用）：

  TypeOK          — state ∈ 合法狀態集；retry ∈ [0,MAX_RETRY]；recovery ∈ [0,MAX_RECOVERY]
  RetryBounded    — 任一 gate retry_count ≤ MAX_RETRY
  RecoveryBounded — session AUTO_RECOVERY_ATTEMPT 次數 ≤ MAX_RECOVERY
  NotInBothSets   — ObservationStates ∩ Terminals = ∅（結構性互斥）

違反 → 寫 build/reports/fsm/MONITOR-VIOLATION-{date}.yaml → FSMRuntime.enter_monitor_violation
→ ESCALATION。讓「證明與執行對齊」成為持續性質而非一次性。

常數 MAX_RETRY=5 / MAX_RECOVERY=3 與 SDD_FSM.cfg 同源。
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .transition_rules import (
    OBSERVATION_STATES,
    RETRY_LIMITS,
    _HAPPY_PATH,
    _EMERGENCY_TARGETS,
)

# 與 SDD_FSM.cfg CONSTANTS 同源（Rule 9.18.1 雙源一致性的執行期對映）。
MAX_RETRY = 5
MAX_RECOVERY = 3

_TERMINALS = frozenset({"RELEASE", "TERMINATED", "ESCALATION_FINAL"})


def _valid_states() -> frozenset:
    states = set(_HAPPY_PATH.keys()) | set(_EMERGENCY_TARGETS)
    for dsts in _HAPPY_PATH.values():
        states |= dsts
    states |= set(OBSERVATION_STATES)
    states |= {"AUTO_COMPACT_PENDING"}
    return frozenset(states)


@dataclass
class MonitorResult:
    ok: bool
    violations: List[str] = field(default_factory=list)
    report_path: Optional[str] = None


def check_invariants(state) -> MonitorResult:
    """對 FSMState 執行 4 條 .tla safety invariant 的執行期 assertion。

    純函式（不改 state、不寫檔）。回傳 MonitorResult.violations。
    """
    violations: List[str] = []
    root = getattr(state, "root", {}) or {}

    # ---- TypeOK：state 合法 ----
    cur = getattr(state, "current", None)
    if cur not in _valid_states():
        violations.append(f"TypeOK: state {cur!r} 不在合法狀態集")

    # ---- RetryBounded：任一 gate retry_count ≤ MAX_RETRY ----
    retry_hist = root.get("retry_history", {}) or {}
    for gate, entry in retry_hist.items():
        try:
            cnt = int((entry or {}).get("current_count", 0))
        except (TypeError, ValueError):
            violations.append(f"TypeOK/RetryBounded: gate {gate} current_count 非整數")
            continue
        limit = RETRY_LIMITS.get(gate, MAX_RETRY)
        if cnt < 0:
            violations.append(f"TypeOK: gate {gate} retry_count={cnt} < 0")
        if cnt > MAX_RETRY:
            violations.append(
                f"RetryBounded: gate {gate} retry_count={cnt} > MAX_RETRY={MAX_RETRY}"
            )
        elif cnt > limit:
            # 超過該 gate 自身上限亦屬越界（imperative 與 .tla 漂移的徵兆）
            violations.append(
                f"RetryBounded: gate {gate} retry_count={cnt} > RETRY_LIMITS[{gate}]={limit}"
            )

    # ---- RecoveryBounded：session AUTO_RECOVERY_ATTEMPT 次數 ≤ MAX_RECOVERY ----
    rec = root.get("recovery_state", {}) or {}
    try:
        sess = int(rec.get("session_attempt_count", 0))
        if sess < 0 or sess > MAX_RECOVERY:
            violations.append(
                f"RecoveryBounded: session_attempt_count={sess} 越界 [0,{MAX_RECOVERY}]"
            )
    except (TypeError, ValueError):
        violations.append("TypeOK/RecoveryBounded: session_attempt_count 非整數")

    # ---- NotInBothSets：ObservationStates ∩ Terminals = ∅（結構性）----
    overlap = set(OBSERVATION_STATES) & _TERMINALS
    if overlap:
        violations.append(f"NotInBothSets: 觀測態與 terminal 集合重疊 {sorted(overlap)}")

    return MonitorResult(ok=not violations, violations=violations)


def write_violation_report(
    result: MonitorResult,
    *,
    state_name: str = "",
    today: Optional[str] = None,
    out_dir: Optional[Path] = None,
) -> Optional[str]:
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    if out_dir is None:
        from .state_loader import REPO_ROOT
        out_dir = REPO_ROOT / "build" / "reports" / "fsm"
    out_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.date.today().isoformat()
    path = out_dir / f"MONITOR-VIOLATION-{date}.yaml"
    doc = {
        "detected_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "state": state_name,
        "violations": result.violations,
        "synthesized_from": "tools/fsm_runtime/formal/SDD_FSM.tla (TypeOK/RetryBounded/RecoveryBounded/NotInBothSets)",
        "required_action": "MONITOR_VIOLATION → ESCALATION（runtime monitor 補位，不可恢復）",
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(path)
    return str(path)


def enabled() -> bool:
    """env SDD_SPEC_MONITOR=1 啟用 transition() 後置自動斷言（預設關閉，避免擾動
    既有測試與 chaos；orchestrator / 驗收流程顯式開啟）。"""
    return os.environ.get("SDD_SPEC_MONITOR", "").strip() in {"1", "true", "on", "hard"}
