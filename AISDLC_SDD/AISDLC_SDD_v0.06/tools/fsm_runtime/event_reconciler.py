"""CI-EVENT reconciler — consumes build/reports/fsm/CI-EVENT-*.yaml."""
from __future__ import annotations

import datetime as _dt
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required") from exc

from .state_loader import FSMState, save_state

EVENTS_GLOB_PATTERN = "CI-EVENT-*.yaml"

# Mapping rules from SDD_CICD_BASE_LAYER.md §ci_to_fsm_bridge
_UPDATE_RULES = {
    "DocLint": {"update_retry_count": False, "target": None},
    "SpecTrace": {"update_retry_count": False, "target": None},
    "SLV": {"update_retry_count": True, "target": "SCG_VALIDATION"},
    "OpenAPI": {"update_retry_count": True, "target": "SCG_VALIDATION"},
    "RTM": {"update_retry_count": False, "target": None},
}


def _load_event(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_event(path: Path, doc: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, path)


def _content_hash(doc: Dict[str, Any]) -> str:
    """Stable content fingerprint for idempotency (ACT-029 P1-02).

    Two CI-EVENT files with different filenames but identical payload
    (pipeline_id + stage + result + failure_reason + scg_gate + timestamp)
    must be treated as a single event — the reconciler incrementally
    records the first and skips the rest. Prevents retry_count drift
    caused by CI retries writing duplicate events.
    """
    parts = [
        str(doc.get("pipeline_id", "")),
        str(doc.get("stage", "")),
        str(doc.get("result", "")).upper(),
        str(doc.get("failure_reason", "")),
        str(doc.get("scg_gate", "")),
        str(doc.get("timestamp", "")),
    ]
    blob = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def reconcile(state: FSMState, events_dir: Path | None = None) -> List[str]:
    """Apply all unprocessed CI-EVENT files to state. Returns applied event filenames.

    Idempotency (ACT-029 P1-02): within a single reconcile call, events
    sharing the same content hash are processed exactly once. Duplicates
    are still marked `processed=True` so subsequent reconciles are no-ops,
    but they do **not** re-increment retry_count.
    """
    events_dir = events_dir or state.path.parent
    applied: List[str] = []
    # ACT-029 P1-02: in-call dedup ledger. Persisted across calls via the
    # per-event `processed` flag, but we also need intra-call dedup because
    # duplicate CI writes typically arrive in the same batch.
    seen_hashes: set[str] = set()
    ledger = state.root.setdefault("ci_event_seen_hashes", []) or []
    # Trim historical ledger to last 500 entries to bound state growth.
    if len(ledger) > 500:
        del ledger[:-500]
    persisted_hashes = set(ledger)
    for event_path in sorted(events_dir.glob(EVENTS_GLOB_PATTERN)):
        doc = _load_event(event_path)
        if doc.get("processed"):
            continue
        digest = _content_hash(doc)
        duplicate = digest in seen_hashes or digest in persisted_hashes
        if not duplicate:
            stage = doc.get("stage", "")
            result = (doc.get("result") or "").upper()
            rule = _UPDATE_RULES.get(stage)
            if rule and rule["update_retry_count"] and result == "FAIL":
                gate = rule["target"]
                reason = doc.get("failure_reason") or f"CI {stage} FAIL"
                scg = doc.get("scg_gate")
                state.increment_retry(gate, reason, scg_gate=scg)
            seen_hashes.add(digest)
            ledger.append(digest)
            # QA Round-5 P1: persist state (retry_count + ledger) BEFORE
            # saving the event file. If _save_event fails, the on-disk
            # state already carries the dedup digest, so next reconcile
            # treats the event as duplicate and will not re-increment —
            # preventing transactional drift between state and event flags.
            state.root["ci_event_seen_hashes"] = ledger
            save_state(state)
        # Mark processed whether or not it was a duplicate — prevents
        # re-scan churn and keeps the ledger semantics consistent.
        doc["processed"] = True
        doc["processed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        doc["content_hash"] = digest
        if duplicate:
            doc["dedup_skipped"] = True
        _save_event(event_path, doc)
        applied.append(event_path.name)
    # Final state save covers the case where only duplicates were seen
    # (no per-event save inside the loop was triggered) but we still want
    # `updated_at` to advance. Idempotent with the in-loop saves above.
    state.root["ci_event_seen_hashes"] = ledger
    if applied:
        save_state(state)
    return applied
