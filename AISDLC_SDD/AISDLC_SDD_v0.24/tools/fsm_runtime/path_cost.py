"""path_cost.py — Phase G M6 / ACT-043 PathCostEstimator

Estimates token cost for a (subagent, classification) dispatch using
rolling-30 historical samples + 1.5σ safety margin.

Public surface:
    EstimatedCost          — dataclass {value, source, samples, avg, stddev}
    PathCostEstimator      — estimate / record_sample / load / save
    record_dispatch_rejection(reason, ...) -> Path  — writes REJECTED-*.yaml

Cold-start (Rule 9.19.1): when samples < MIN_SAMPLES, returns conservative
default = COLD_START_DEFAULT_TOKENS (8000).
"""
from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .file_lock import file_lock

ROLLING_WINDOW = 30
MIN_SAMPLES = 10
COLD_START_DEFAULT_TOKENS = 8000  # Rule 9.19.1 / OPEN-G.6
SAFETY_MARGIN_SIGMA = 1.5
GATE_MULTIPLIER = 1.2  # estimated * 1.2 must fit in remaining budget
CALIBRATION_DRIFT_THRESHOLD = 0.50  # Rule 9.19.4
CALIBRATION_WINDOW = 5


# ─────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────


@dataclass
class EstimatedCost:
    subagent: str
    classification: str
    value: int
    source: str  # "rolling_30" | "cold_start"
    samples: int = 0
    avg: float = 0.0
    stddev: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CalibrationStat:
    estimated: int
    actual: int

    @property
    def error_pct(self) -> float:
        if self.estimated == 0:
            return 0.0
        return abs(self.actual - self.estimated) / self.estimated


# ─────────────────────────────────────────────────────────────
# Estimator
# ─────────────────────────────────────────────────────────────


class PathCostEstimator:
    """Rolling-30 estimator with cold-start fallback."""

    def __init__(self, *, repo_root: Optional[Path] = None):
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[2]
        self.repo_root = repo_root
        self.state_path = repo_root / "build" / "state" / "path-cost-rolling.yaml"
        self.calibration_path = repo_root / "build" / "state" / "path-cost-calibration.yaml"

    # ----- I/O -----

    def _load(self) -> Dict[str, Dict[str, list]]:
        if not self.state_path.exists():
            return {}
        try:
            data = yaml.safe_load(self.state_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return {}
        return data

    def _save(self, data: Dict[str, Dict[str, list]]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(self.state_path.with_suffix(".lock")):
            self.state_path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

    # ----- Public API -----

    def record_sample(
        self, subagent: str, classification: str, tokens: int
    ) -> Optional[Path]:
        """Record actual token usage for a dispatch.

        NA-3 (Phase G Final post-CF-6): on first crossing of ROLLING_WINDOW (30)
        samples for a (subagent, classification) pair, emits a one-shot
        CALIBRATION-MILESTONE-{subagent}-{classification}-{date}.yaml so the QA
        loop knows rolling-30 statistics are now meaningful for Rule 9.19.4
        verification. Returns the milestone path on first crossing, else None.
        """
        data = self._load()
        key = f"{subagent}::{classification}"
        bucket = data.setdefault(
            key, {"samples": [], "updated_at": "", "milestone_fired": False}
        )
        samples = list(bucket.get("samples", []))
        samples.append(int(tokens))
        if len(samples) > ROLLING_WINDOW:
            samples = samples[-ROLLING_WINDOW:]
        bucket["samples"] = samples
        bucket["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        milestone_path: Optional[Path] = None
        if (
            not bucket.get("milestone_fired", False)
            and len(samples) >= ROLLING_WINDOW
        ):
            milestone_path = _write_milestone(
                self.repo_root, subagent, classification, samples
            )
            bucket["milestone_fired"] = True

        data[key] = bucket
        self._save(data)
        return milestone_path

    def estimate(self, subagent: str, classification: str) -> EstimatedCost:
        """Return estimated cost (rolling-30 + 1.5σ, or cold-start default)."""
        data = self._load()
        key = f"{subagent}::{classification}"
        samples: List[int] = list(data.get(key, {}).get("samples", []))
        if len(samples) < MIN_SAMPLES:
            return EstimatedCost(
                subagent=subagent,
                classification=classification,
                value=COLD_START_DEFAULT_TOKENS,
                source="cold_start",
                samples=len(samples),
            )
        avg = statistics.mean(samples)
        stddev = statistics.stdev(samples) if len(samples) > 1 else 0.0
        value = int(round(avg + SAFETY_MARGIN_SIGMA * stddev))
        return EstimatedCost(
            subagent=subagent,
            classification=classification,
            value=value,
            source="rolling_30",
            samples=len(samples),
            avg=round(avg, 2),
            stddev=round(stddev, 2),
        )

    def gate_pass(
        self,
        subagent: str,
        classification: str,
        token_remaining: int,
    ) -> Tuple[bool, EstimatedCost]:
        """Returns (pass?, EstimatedCost). pass <-> remaining > estimated × 1.2."""
        est = self.estimate(subagent, classification)
        passes = token_remaining > est.value * GATE_MULTIPLIER
        return passes, est

    # ----- Calibration (Rule 9.19.4) -----

    def record_calibration(
        self,
        subagent: str,
        classification: str,
        estimated: int,
        actual: int,
    ) -> Optional[Path]:
        """Track estimate vs actual; if error > 50% for last 5 samples → warn."""
        data: Dict[str, list] = {}
        if self.calibration_path.exists():
            try:
                data = yaml.safe_load(self.calibration_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                data = {}
        key = f"{subagent}::{classification}"
        rows = list(data.get(key, []))
        rows.append({"estimated": estimated, "actual": actual,
                     "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        if len(rows) > CALIBRATION_WINDOW * 2:
            rows = rows[-CALIBRATION_WINDOW * 2:]
        data[key] = rows
        self.calibration_path.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(self.calibration_path.with_suffix(".lock")):
            self.calibration_path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        # Check last 5 samples
        last5 = rows[-CALIBRATION_WINDOW:]
        if len(last5) < CALIBRATION_WINDOW:
            return None
        bad = sum(1 for r in last5
                  if CalibrationStat(r["estimated"], r["actual"]).error_pct > CALIBRATION_DRIFT_THRESHOLD)
        if bad == CALIBRATION_WINDOW:
            return _write_calibration_warn(self.repo_root, subagent, classification, last5)
        return None


def _write_milestone(
    repo_root: Path,
    subagent: str,
    classification: str,
    samples: list,
) -> Path:
    """NA-3: emit CALIBRATION-MILESTONE on first rolling-30 saturation."""
    out_dir = repo_root / "build" / "reports" / "orchestrator"
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = out_dir / f"CALIBRATION-MILESTONE-{subagent}-{classification}-{date}.yaml"
    avg = statistics.mean(samples)
    stddev = statistics.stdev(samples) if len(samples) > 1 else 0.0
    body = {
        "schema_version": 1,
        "milestone": "rolling_30_saturated",
        "subagent": subagent,
        "classification": classification,
        "samples_count": len(samples),
        "rolling_avg": round(avg, 2),
        "rolling_stddev": round(stddev, 2),
        "rolling_min": min(samples),
        "rolling_max": max(samples),
        "fired_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": (
            "NA-3 (Phase G Final): rolling-30 sample bucket saturated; "
            "Rule 9.19.4 verification now meaningful for this pair."
        ),
    }
    p.write_text(yaml.safe_dump(body, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p


def _write_calibration_warn(
    repo_root: Path,
    subagent: str,
    classification: str,
    samples: list,
) -> Path:
    out_dir = repo_root / "build" / "reports" / "orchestrator"
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = out_dir / f"CALIBRATION-WARN-{date}.yaml"
    body = {
        "schema_version": 1,
        "subagent": subagent,
        "classification": classification,
        "reason": "Rule 9.19.4: estimate error > 50% for 5 consecutive samples",
        "samples": samples,
        "warned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    p.write_text(yaml.safe_dump(body, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p


# ─────────────────────────────────────────────────────────────
# Rejection log (Rule 9.19.2)
# ─────────────────────────────────────────────────────────────


def record_dispatch_rejection(
    *,
    subagent: str,
    classification: str,
    estimated: int,
    remaining: int,
    reason: str,
    proposed_alternative: str = "",
    repo_root: Optional[Path] = None,
) -> Path:
    """Append a rejection record to today's REJECTED-*.yaml."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "build" / "reports" / "orchestrator"
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = out_dir / f"REJECTED-{date}.yaml"
    if p.exists():
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
    else:
        data = {}
    data.setdefault("schema_version", 1)
    rows = list(data.get("rejected", []))
    rows.append({
        "subagent": subagent,
        "classification": classification,
        "estimated": int(estimated),
        "remaining": int(remaining),
        "reason": reason,
        "proposed_alternative": proposed_alternative,
        "rejected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    data["rejected"] = rows
    with file_lock(p.with_suffix(".lock")):
        p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p
