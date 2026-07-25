"""Hub Conflict Resolver — 3-way merge for SLV/FPL rule files.

ACT-030 (Phase F M2 D-30.8).

Spec: knowledge/hub/trust-ladder.md §陸 (3-way merge algorithm)

Behaviour matrix:
  - Hub pull external rule vs local missing                 → fast-forward
  - Hub external vs local external (same content as base)   → fast-forward
  - Hub external vs local external (local diverged)         → conflict
  - Hub external vs local proposed                          → conflict
  - Hub external vs local **verified**                      → BLOCKED
       (RuleOverwriteProtected; do not auto-overwrite)

When conflict is detected, the resolver writes
`knowledge/hub/CONFLICTS/{rule_id}-{timestamp}.yaml` with three-way diff
metadata so a human can decide. Caller (hub_sync) then signals FSM via
`exit_hub_sync("partial")` → HUMAN_PENDING.

Public API:
  detect_conflict(rule_id, *, local, base, remote) -> ConflictReport
  resolve_or_record(rule_id, ...) -> ResolutionOutcome
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import difflib
from enum import Enum
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

from .state_loader import REPO_ROOT, _sanitize_component


DEFAULT_CONFLICTS_DIR = REPO_ROOT / "knowledge" / "hub" / "CONFLICTS"


class MergeOutcome(str, Enum):
    FAST_FORWARD = "fast_forward"
    NO_OP = "no_op"
    CONFLICT = "conflict"
    BLOCKED_VERIFIED = "blocked_verified"   # local is verified — never overwrite
    BASE_MISSING_NEW_RULE = "fast_forward_new"  # local doesn't exist; safe write


class RuleOverwriteProtected(RuntimeError):
    """Raised by callers if they attempt to overwrite a verified local rule."""


@dataclasses.dataclass
class ConflictReport:
    rule_id: str
    outcome: MergeOutcome
    local_trust: Optional[str]
    remote_trust: Optional[str]
    base_trust: Optional[str]
    written_path: Optional[Path] = None
    summary: str = ""


def _read_yaml(path: Optional[Path]) -> Optional[dict]:
    if path is None or not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _trust(doc: Optional[dict]) -> Optional[str]:
    if not doc:
        return None
    return str(doc.get("trust_level", "")) or None


def _semantic_key(doc: Optional[dict]) -> tuple:
    """Hashable signature of a rule's *semantic* fields (ignore review_history)."""
    if not doc:
        return tuple()
    keys = ("id", "name", "scope", "severity", "pattern_yaml", "description")
    return tuple(str(doc.get(k, "")) for k in keys)


def detect_conflict(
    rule_id: str,
    *,
    local: Optional[Path],
    base: Optional[Path],
    remote: Optional[Path],
    conflicts_dir: Optional[Path] = None,
) -> ConflictReport:
    """Decide what to do about a Hub rule vs local rule, given the cached base.

    Inputs:
      local   — current state of the rule on disk (None if absent)
      base    — last-pulled snapshot in cache (None if first pull)
      remote  — newly fetched rule from Hub
    """
    local_doc = _read_yaml(local)
    base_doc = _read_yaml(base)
    remote_doc = _read_yaml(remote)
    local_trust = _trust(local_doc)
    remote_trust = _trust(remote_doc)
    base_trust = _trust(base_doc)

    # Case 1: local missing → safe write
    if local_doc is None:
        return ConflictReport(
            rule_id=rule_id,
            outcome=MergeOutcome.BASE_MISSING_NEW_RULE,
            local_trust=None, remote_trust=remote_trust, base_trust=base_trust,
            summary="local rule does not exist → fast-forward write",
        )

    # Case 2: local verified → never overwrite
    if local_trust == "verified":
        report = ConflictReport(
            rule_id=rule_id,
            outcome=MergeOutcome.BLOCKED_VERIFIED,
            local_trust=local_trust, remote_trust=remote_trust, base_trust=base_trust,
            summary="local rule is trust_level=verified — RuleOverwriteProtected",
        )
        report.written_path = _write_conflict_report(
            rule_id, local_doc, base_doc, remote_doc, report,
            conflicts_dir=conflicts_dir,
        )
        return report

    local_sig = _semantic_key(local_doc)
    remote_sig = _semantic_key(remote_doc)
    base_sig = _semantic_key(base_doc)

    # Case 3: local == remote → no-op
    if local_sig == remote_sig:
        return ConflictReport(
            rule_id=rule_id,
            outcome=MergeOutcome.NO_OP,
            local_trust=local_trust, remote_trust=remote_trust, base_trust=base_trust,
            summary="local and remote share the same semantic fields",
        )

    # Case 4: local == base, remote diverged → fast-forward
    if base_doc is not None and local_sig == base_sig:
        return ConflictReport(
            rule_id=rule_id,
            outcome=MergeOutcome.FAST_FORWARD,
            local_trust=local_trust, remote_trust=remote_trust, base_trust=base_trust,
            summary="local unchanged since last pull → fast-forward to remote",
        )

    # Case 5: both diverged or no base → conflict
    report = ConflictReport(
        rule_id=rule_id,
        outcome=MergeOutcome.CONFLICT,
        local_trust=local_trust, remote_trust=remote_trust, base_trust=base_trust,
        summary=(
            "local and remote diverged from base — manual review required"
            if base_doc is not None
            else "no base snapshot, cannot 3-way merge — manual review required"
        ),
    )
    report.written_path = _write_conflict_report(
        rule_id, local_doc, base_doc, remote_doc, report,
        conflicts_dir=conflicts_dir,
    )
    return report


def _yaml_dump(doc: Optional[dict]) -> str:
    if doc is None:
        return ""
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def _write_conflict_report(
    rule_id: str,
    local: Optional[dict],
    base: Optional[dict],
    remote: Optional[dict],
    report: ConflictReport,
    *,
    conflicts_dir: Optional[Path] = None,
) -> Path:
    target_dir = Path(conflicts_dir) if conflicts_dir else DEFAULT_CONFLICTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Path traversal defence: rule_id is externally-controlled (R44
    # cross-platform review fix; see state_loader.py _sanitize_component()).
    safe_rule_id = _sanitize_component(rule_id)
    out = target_dir / f"{safe_rule_id}-{ts}.yaml"

    local_yaml = _yaml_dump(local)
    base_yaml = _yaml_dump(base)
    remote_yaml = _yaml_dump(remote)

    diff_local_remote = "".join(difflib.unified_diff(
        base_yaml.splitlines(keepends=True),
        remote_yaml.splitlines(keepends=True),
        fromfile="base", tofile="remote",
    ))
    diff_base_local = "".join(difflib.unified_diff(
        base_yaml.splitlines(keepends=True),
        local_yaml.splitlines(keepends=True),
        fromfile="base", tofile="local",
    ))

    payload = {
        "conflict_id": f"{rule_id}-{ts}",
        "detected_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "rule_id": rule_id,
        "outcome": report.outcome.value,
        "local_trust": report.local_trust,
        "remote_trust": report.remote_trust,
        "base_trust": report.base_trust,
        "summary": report.summary,
        "local_snapshot": local,
        "base_snapshot": base,
        "remote_snapshot": remote,
        "diff_base_to_remote": diff_local_remote,
        "diff_base_to_local": diff_base_local,
        "resolution_status": "pending",
        "resolved_by": None,
        "resolved_at": None,
        "decision": None,
        "notes": None,
    }
    out.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return out


def apply_fast_forward(remote_path: Path, local_target: Path) -> None:
    """Copy remote content to local target — caller must have verified outcome
    is FAST_FORWARD or BASE_MISSING_NEW_RULE first."""
    local_target.parent.mkdir(parents=True, exist_ok=True)
    local_target.write_text(remote_path.read_text(encoding="utf-8"), encoding="utf-8")
