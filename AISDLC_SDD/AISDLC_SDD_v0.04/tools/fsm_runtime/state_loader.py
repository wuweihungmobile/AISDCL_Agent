"""FSM-STATE-{project}.yaml 讀寫器。

Source of truth: build/reports/fsm/FSM-STATE-TEMPLATE.yaml
"""
from __future__ import annotations

import copy
import datetime as _dt
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install with: pip install pyyaml"
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = REPO_ROOT / "build" / "reports" / "fsm" / "FSM-STATE-TEMPLATE.yaml"
DEFAULT_STATE_DIR = REPO_ROOT / "build" / "reports" / "fsm"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _sanitize_component(name: str) -> str:
    """消毒檔名片段，防止誤傳整段路徑當 project/track_id。

    根因防護（arch_fitness FF-3）：曾有呼叫端把整段相對路徑
    （build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml）當 project 傳入，使
    _default_state_path 產生巢狀 FSM-STATE-build/reports/fsm/...yaml.yaml，
    其 .tmp 殘留無法被 save_state 的 reap 回收。剝除路徑分隔符後，
    任何誤用都退化為單層平坦檔名，不再洩漏孤兒。
    """
    return str(name).replace("/", "_").replace("\\", "_").strip()


def _default_state_path(project: str) -> Path:
    return DEFAULT_STATE_DIR / f"FSM-STATE-{_sanitize_component(project)}.yaml"


# Phase I M5 / ACT-070：艦隊並行的 track 維度 state key。
# 單軌時 track_id=None → FSM-STATE-{project}.yaml（向後相容）；
# 多 feature 並行時每軌獨立 FSM-STATE-{project}-{track_id}.yaml，互不污染。
def track_state_path(project: str, track_id: Optional[str] = None) -> Path:
    if not track_id:
        return _default_state_path(project)
    safe = _sanitize_component(track_id)
    return DEFAULT_STATE_DIR / f"FSM-STATE-{_sanitize_component(project)}-{safe}.yaml"


def load_track_state(
    project: str,
    track_id: Optional[str] = None,
    *,
    create_if_missing: bool = True,
) -> "FSMState":
    """載入指定 track 的 FSM 狀態（ACT-070）。track_id=None 等同單軌 load_state。"""
    return load_state(project, path=track_state_path(project, track_id),
                      create_if_missing=create_if_missing)


class FSMState:
    """Thin wrapper over the FSM state YAML document."""

    def __init__(self, doc: Dict[str, Any], path: Path):
        self._doc = doc
        self.path = path

    # ---------- convenience accessors ----------
    @property
    def root(self) -> Dict[str, Any]:
        return self._doc.setdefault("fsm_state", {})

    @property
    def current(self) -> str:
        return self.root.get("current_state", "INIT")

    @current.setter
    def current(self, value: str) -> None:
        self.root["current_state"] = value
        self.root["updated_at"] = _now()

    def retry(self, gate: str) -> Dict[str, Any]:
        return self.root.setdefault("retry_history", {}).setdefault(gate, {})

    def cumulative(self) -> Dict[str, Any]:
        return self.root.setdefault("cumulative_history", {})

    def implementation_budget(self) -> Dict[str, Any]:
        return self.root.setdefault("implementation_budget", {})

    # Phase E / ACT-025：Decision Trace accessor
    def decision_trace(self) -> list:
        return self.root.setdefault("decision_trace", [])

    def append_decision_trace(
        self,
        *,
        from_state: str,
        to_state: str,
        reason: str = "",
        spec_refs: Optional[list] = None,
        agents_consulted: Optional[list] = None,
        trigger: str = "transition",
        max_keep: int = 50,
    ) -> Dict[str, Any]:
        """Append one decision trace entry; keep the latest max_keep (default 50).

        Older entries are flushed to cold tier via move-into 'decision_trace_flushed'
        so the active list remains bounded without losing history.
        """
        trace = self.decision_trace()
        entry: Dict[str, Any] = {
            "ts": _now(),
            "from": from_state,
            "to": to_state,
            "reason": reason or f"auto transition {from_state}->{to_state}",
            "spec_refs": spec_refs or [],
            "agents_consulted": agents_consulted or [],
            "trigger": trigger,
        }
        trace.append(entry)
        if len(trace) > max_keep:
            flushed = self.root.setdefault("decision_trace_flushed", [])
            overflow = len(trace) - max_keep
            flushed.extend(trace[:overflow])
            self.root["decision_trace"] = trace[overflow:]
        self.root["updated_at"] = _now()
        return entry

    # ---------- mutations ----------
    def increment_retry(self, gate: str, failure_reason: str, scg_gate: Optional[str] = None) -> int:
        # ACT-029 P1-01: tamper defence.
        # Attackers (or corrupted state) may set `current_count` to a negative
        # number to earn free retries, or to an absurdly large number to skip
        # retries entirely. Defend both ends:
        #   1. `max(0, prior)` floors negative values at zero so they cannot
        #      silently buy back retries.
        #   2. If the prior value is outside the legal band [0, limit), snap
        #      the new count directly to `limit` so the very next gate check
        #      escalates — it is safer to stop once than to over-retry.
        #   3. Record the tamper detection in history.failure_reason for
        #      audit so reviewers can see the original poisoned value.
        from .transition_rules import RETRY_LIMITS  # local to avoid cycles
        entry = self.retry(gate)
        prior_raw = entry.get("current_count", 0)
        try:
            prior = int(prior_raw)
        except (TypeError, ValueError):
            prior = 0
        limit = RETRY_LIMITS.get(gate)
        tamper = False
        tamper_note = ""
        if prior < 0:
            tamper = True
            tamper_note = f"(tamper detected: prior_count={prior_raw}, floored to 0)"
            sanitized = 0
        elif limit is not None and prior >= limit:
            tamper = True
            tamper_note = f"(tamper detected: prior_count={prior_raw} ≥ limit={limit})"
            sanitized = prior  # keep as-is; current will be snapped to limit below
        else:
            sanitized = prior
        current = sanitized + 1
        # When tamper detected and we know the gate's limit, snap to limit so
        # the very next escalation check triggers regardless of the poisoned
        # starting value.
        if tamper and limit is not None:
            current = limit
        entry["current_count"] = current
        history = entry.setdefault("history", []) or []
        recorded_reason = failure_reason
        if tamper_note:
            recorded_reason = f"{failure_reason} {tamper_note}".strip()
        history.append(
            {
                "attempt": current,
                "date": _now(),
                "failure_reason": recorded_reason,
                "scg_gate": scg_gate,
            }
        )
        entry["history"] = history
        cum = self.cumulative()
        if gate == "SCG_VALIDATION":
            cum["total_scg_retries_all_time"] = int(cum.get("total_scg_retries_all_time", 0)) + 1
        elif gate == "PR_REVIEW":
            cum["total_pr_review_retries"] = int(cum.get("total_pr_review_retries", 0)) + 1
        self.root["updated_at"] = _now()
        return current

    def reset_retry(self, gate: str) -> None:
        entry = self.retry(gate)
        entry["current_count"] = 0
        entry.setdefault("history", [])

    def record_spec_frozen(self, stage: str, spec_docs: list[str], compaction_report: Optional[str] = None) -> None:
        stages = self.root.setdefault("frozen_stages", []) or []
        stages.append(
            {
                "stage": stage,
                "frozen_at": _now(),
                "compaction_report": compaction_report,
                "spec_docs": spec_docs,
            }
        )
        self.root["frozen_stages"] = stages
        cum = self.cumulative()
        cum["total_spec_frozen_count"] = int(cum.get("total_spec_frozen_count", 0)) + 1
        # Reset current_count for every gate but keep cumulative_history.
        for gate_name in ("SCG_VALIDATION", "PR_REVIEW", "RTM_VERIFY"):
            self.reset_retry(gate_name)

    def record_escalation(self, reason: str) -> None:
        history = self.root.setdefault("escalation_history", []) or []
        history.append(
            {
                "triggered_at": _now(),
                "trigger_reason": reason,
                "resolved_at": None,
                "resolution": None,
            }
        )
        self.root["escalation_history"] = history
        cum = self.cumulative()
        cum["escalation_count"] = int(cum.get("escalation_count", 0)) + 1
        self.current = "ESCALATION"

    # QA Round-3 P2-02: `add_pending_ci_event` / `remove_pending_ci_event` were
    # unused (event_reconciler relies on `ci_event_seen_hashes`, not the pending
    # list). The `ci_events_pending` field is retained in state because snapshot
    # renders it, but the mutators were dead code and have been removed.

    # ---------- serialization ----------
    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self._doc)


def _load_template() -> Dict[str, Any]:
    with TEMPLATE_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _classify_state_file(path: Path) -> tuple[Optional[Dict[str, Any]], str]:
    """Parse a state file and return (doc_or_none, reason_code).

    P2-03: reason codes let load_state build a specific ValueError instead
    of a generic "unreadable" message, so operators can tell parse errors
    apart from schema mismatches.

    Reason codes:
        ok            — parsed into a valid FSMState doc
        read_error    — IOError / permission / decoding failure
        yaml_error    — YAML syntax / parse failure
        non_dict      — parsed to something other than a mapping
        missing_root  — dict but no top-level ``fsm_state`` key (or not dict)
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
    except (UnicodeDecodeError, OSError):
        return None, "read_error"
    except yaml.YAMLError:
        return None, "yaml_error"
    if not isinstance(doc, dict):
        return None, "non_dict"
    if "fsm_state" not in doc or not isinstance(doc.get("fsm_state"), dict):
        return None, "missing_root"
    return doc, "ok"


def _try_parse_state_file(path: Path) -> Optional[Dict[str, Any]]:
    """Backwards-compatible shim: return the parsed doc or None."""
    doc, _reason = _classify_state_file(path)
    return doc


def load_state(project: str, path: Optional[Path] = None, create_if_missing: bool = True) -> FSMState:
    """Load an FSM state document; initialize from template when missing.

    ACT-029 chaos recovery: if the primary YAML is corrupted (parse error /
    non-dict / missing `fsm_state`), fall back to the sibling `.bak` snapshot
    written by :func:`save_state`. The recovered document is copied back over
    the primary so subsequent reads are consistent.
    """
    target = path or _default_state_path(project)
    if target.exists():
        primary_doc, primary_reason = _classify_state_file(target)
        if primary_doc is not None:
            return FSMState(primary_doc, target)
        bak = target.with_suffix(target.suffix + ".bak")
        bak_reason = "absent"
        if bak.exists():
            bak_doc, bak_reason = _classify_state_file(bak)
            if bak_doc is not None:
                shutil.copy2(bak, target)
                return FSMState(bak_doc, target)
        # P2-03: Primary unparseable and no usable backup — surface both
        # failure reasons so operators triaging RESUME_VERIFICATION can
        # tell "corrupt YAML" from "schema drift" at a glance.
        raise ValueError(
            f"FSM-STATE unreadable and no usable .bak (primary={primary_reason}, "
            f"bak={bak_reason}): {target}"
        )
    if not create_if_missing:
        raise FileNotFoundError(f"FSM-STATE file not found: {target}")
    doc = _load_template()
    root = doc.setdefault("fsm_state", {})
    root["project"] = project
    root["session_id"] = str(uuid.uuid4())
    now = _now()
    root["created_at"] = now
    root["updated_at"] = now
    root["current_state"] = "INIT"
    target.parent.mkdir(parents=True, exist_ok=True)
    state = FSMState(doc, target)
    save_state(state)
    return state


def save_state(state: FSMState) -> None:
    """Atomically persist state to disk (backup the previous file).

    P2-02: the `.bak` rotation is now atomic too. We copy the existing
    primary to `{suffix}.bak.tmp` and then `os.replace` it into `.bak`, so
    a crash between copy and replace leaves the previous `.bak` intact
    rather than a half-written file. Without this, a mid-copy crash could
    corrupt `.bak` and defeat the ACT-029 chaos recovery path.

    QA Round-3 P2-08: reap any stale `.bak.tmp` / `.tmp` left by a prior
    interrupted save before starting a new one. Without this, repeated
    crashes during `shutil.copy2` could leak tmp files on disk-full
    volumes; the next `save_state` call now always starts clean.
    """
    target = state.path
    target.parent.mkdir(parents=True, exist_ok=True)
    bak_tmp = target.with_suffix(target.suffix + ".bak.tmp")
    tmp = target.with_suffix(target.suffix + ".tmp")
    # Reap leftovers from a crashed prior save (QA Round-3 P2-08).
    for stale in (bak_tmp, tmp):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass
    if target.exists():
        bak = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, bak_tmp)
        os.replace(bak_tmp, bak)
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(state.to_dict(), f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, target)


def project_from_env(default: str = "default") -> str:
    """Resolve project name from env; fall back to repo folder name."""
    override = os.environ.get("SDD_PROJECT")
    if override:
        return override
    return REPO_ROOT.parent.name or default
