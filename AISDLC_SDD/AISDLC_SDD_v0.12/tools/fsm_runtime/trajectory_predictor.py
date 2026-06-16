"""Phase G M2 / ACT-035: TrajectoryPredictor.

從 FSMState 的 retry_history、decision_trace 與 conversation-ledger.yaml 預測
「當前 retry 路徑是否會崩」。輸出三選一決策（continue / switch_to_audit /
abort_early），由 caller（orchestrator / fsm_runtime）執行對應 transition。

設計原則：
- Heuristic v1（無 LLM、無 ML 模型，純 rule-based）
- 4 信號獨立計分，線性加總；保守策略避免 false positive
- 預測結果僅為「建議」；實際 transition 由 caller 觸發
- false-positive 透過 record_miss() 寫入 PREDICTOR-MISS log（per Rule 9.15.3）

Rule 9.15 邊界：
- 9.15.1 retry_count >= 1 才運作（gate 由 caller 指定）
- 9.15.2 abort_early 需 confidence >= 0.8
- 9.15.3 false-positive 必寫 PREDICTOR-MISS log
- 9.15.4 同 stage switch_to_audit <= 1 次（caller 透過 stage tracking 強制）
"""
from __future__ import annotations

import os
import re
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

from .state_loader import FSMState
from .transition_rules import RETRY_LIMITS


Decision = Literal["continue", "switch_to_audit", "abort_early"]


# ---------- thresholds (calibrated per planning §M2; all unit-tested) ----------

S2_RETRY_RATIO_THRESHOLD = 0.6  # retry_count / max_retries 比例觸發點
S3_SPEC_HITS_REQUIRED = 2       # 最近 5 筆 trace 出現 spec 字樣需 ≥ 2 筆
S3_TRACE_WINDOW = 5             # 觀察最近 5 筆 decision_trace
S4_DRIFT_THRESHOLD = 30.0       # rolling-10 drift_pct > 30% 視為異常

SWITCH_THRESHOLD = 2            # signals >= 2 → switch_to_audit
ABORT_THRESHOLD = 3             # signals >= 3 → abort_early
ABORT_CONFIDENCE_FLOOR = 0.8    # Rule 9.15.2

# Patterns indicating spec-layer conflict (S3); broad enough to catch
# 中英文 escalation reasons that diagnostic.py also recognises as spec_conflict.
_SPEC_PATTERNS = re.compile(
    r"(?:SLV-\d{3}|AC[-\s_].*INV|INV[-\s_]\d+|spec[_\s]conflict"
    r"|矛盾|conflict|contradict|inconsistent)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PredictedAction:
    """Predictor output — caller decides whether to act on it."""

    decision: Decision
    confidence: float              # 0.0~1.0 ; signals_triggered / 4
    signals_triggered: List[str]   # subset of ["S1", "S2", "S3", "S4"]
    rationale: str                 # human-readable summary
    next_state_hint: Optional[str] # "SPEC_AUDIT" / "ESCALATION" / None
    gate: str                      # which retry gate was being analysed

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "signals_triggered": list(self.signals_triggered),
            "rationale": self.rationale,
            "next_state_hint": self.next_state_hint,
            "gate": self.gate,
        }


# ---------- signal evaluators (each returns bool) ----------

def _signal_s1_same_pattern(state: FSMState, gate: str) -> bool:
    """S1: 同 pattern 連續 ≥ 2 次（語意相似度由 pattern_matcher 早算好）."""
    retry_entry = state.retry(gate)
    return int(retry_entry.get("same_pattern_count", 0)) >= 2


def _signal_s2_retry_near_limit(state: FSMState, gate: str) -> bool:
    """S2: retry_count / max_retries >= 0.6 且 S1 同時觸發（pattern stable）."""
    limit = RETRY_LIMITS.get(gate)
    if not limit:
        return False
    retry_entry = state.retry(gate)
    current = int(retry_entry.get("current_count", 0))
    if current < 1:
        return False
    if current / limit < S2_RETRY_RATIO_THRESHOLD:
        return False
    # S2 only fires when pattern is also stable — otherwise high retry count
    # may just be unrelated transient failures.
    return _signal_s1_same_pattern(state, gate)


def _signal_s3_spec_in_trace(state: FSMState) -> bool:
    """S3: decision_trace 最近 5 筆中 ≥ 2 筆 reason 帶 spec 字樣."""
    trace = state.decision_trace()
    if not trace:
        return False
    recent = trace[-S3_TRACE_WINDOW:]
    hits = sum(1 for entry in recent if _SPEC_PATTERNS.search(str(entry.get("reason", ""))))
    return hits >= S3_SPEC_HITS_REQUIRED


def _signal_s4_drift_anomaly(ledger_path: Optional[Path]) -> bool:
    """S4: conversation-ledger.yaml rolling_avg_drift_pct_last10 > 30%."""
    if ledger_path is None or not ledger_path.exists():
        return False
    try:
        doc = yaml.safe_load(ledger_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return False
    drift = doc.get("rolling_avg_drift_pct_last10")
    if drift is None:
        return False
    try:
        return float(drift) > S4_DRIFT_THRESHOLD
    except (TypeError, ValueError):
        return False


# ---------- public API ----------

def predict(
    state: FSMState,
    *,
    gate: str = "PR_REVIEW",
    ledger_path: Optional[Path] = None,
) -> PredictedAction:
    """Run all 4 signals and produce a PredictedAction.

    Caller is responsible for honouring Rule 9.15.1 (only call when retry_count ≥ 1)
    and Rule 9.15.4 (track switch_to_audit count per stage).
    """
    retry_entry = state.retry(gate)
    current_count = int(retry_entry.get("current_count", 0))

    # Rule 9.15.1: predictor must not run before any retry has happened.
    if current_count < 1:
        return PredictedAction(
            decision="continue",
            confidence=0.0,
            signals_triggered=[],
            rationale=f"retry_count={current_count} < 1 (Rule 9.15.1: predictor disabled)",
            next_state_hint=None,
            gate=gate,
        )

    triggered: List[str] = []
    if _signal_s1_same_pattern(state, gate):
        triggered.append("S1")
    if _signal_s2_retry_near_limit(state, gate):
        triggered.append("S2")
    if _signal_s3_spec_in_trace(state):
        triggered.append("S3")
    if _signal_s4_drift_anomaly(ledger_path):
        triggered.append("S4")

    confidence = len(triggered) / 4.0

    if len(triggered) >= ABORT_THRESHOLD and confidence >= ABORT_CONFIDENCE_FLOOR:
        decision: Decision = "abort_early"
        next_hint: Optional[str] = "ESCALATION"
        rationale = (
            f"{len(triggered)} signals ({','.join(triggered)}) + "
            f"confidence {confidence:.2f} ≥ {ABORT_CONFIDENCE_FLOOR} → "
            f"abort early per Rule 9.15.2"
        )
    elif len(triggered) >= SWITCH_THRESHOLD:
        decision = "switch_to_audit"
        next_hint = "SPEC_AUDIT"
        rationale = (
            f"{len(triggered)} signals ({','.join(triggered)}) ≥ {SWITCH_THRESHOLD} → "
            f"switch to SPEC_AUDIT (saves retry budget)"
        )
    else:
        decision = "continue"
        next_hint = None
        rationale = (
            f"{len(triggered)} signals ({','.join(triggered) or 'none'}) "
            f"< {SWITCH_THRESHOLD} → continue normal retry"
        )

    return PredictedAction(
        decision=decision,
        confidence=round(confidence, 3),
        signals_triggered=triggered,
        rationale=rationale,
        next_state_hint=next_hint,
        gate=gate,
    )


def should_switch(action: PredictedAction) -> bool:
    """Convenience: True if caller should act on the prediction."""
    return action.decision in ("switch_to_audit", "abort_early")


def record_miss(
    *,
    action: PredictedAction,
    actual_outcome: str,
    miss_dir: Path,
    state_name: str = "",
) -> Path:
    """Record a false-positive (predictor said switch/abort but actual outcome
    showed it was unnecessary) per Rule 9.15.3.

    Writes/appends to build/reports/fsm/PREDICTOR-MISS-YYYY-MM-DD.yaml.
    Returns the path written.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    miss_dir.mkdir(parents=True, exist_ok=True)
    path = miss_dir / f"PREDICTOR-MISS-{today}.yaml"

    existing: List[dict] = []
    if path.exists():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            if isinstance(loaded, list):
                existing = loaded
        except yaml.YAMLError:
            existing = []

    existing.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "state": state_name,
            "predicted": action.to_dict(),
            "actual_outcome": actual_outcome,
        }
    )
    yaml_content = yaml.safe_dump(existing, sort_keys=False, allow_unicode=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml_content, encoding="utf-8")
    os.replace(tmp, path)
    return path


__all__ = [
    "Decision",
    "PredictedAction",
    "predict",
    "should_switch",
    "record_miss",
    "S2_RETRY_RATIO_THRESHOLD",
    "S3_SPEC_HITS_REQUIRED",
    "S3_TRACE_WINDOW",
    "S4_DRIFT_THRESHOLD",
    "SWITCH_THRESHOLD",
    "ABORT_THRESHOLD",
    "ABORT_CONFIDENCE_FLOOR",
]
