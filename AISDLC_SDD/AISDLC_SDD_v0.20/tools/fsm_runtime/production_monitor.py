"""Production Feedback Layer — ACT-027 / M3 (Level 5 entry).

Implements the file-based Pull architecture decided in
SDD_improving_Automation_04.md §OPEN-10.6:

  data/slo_events/             ← inbox (mock or real SLO violation events, YAML)
  data/slo_events/quarantine/  ← failed signature / schema validation
  data/slo_events/processed/   ← successfully ingested events
  build/reports/fsm/PBS-DRIFT-{date}.yaml   ← rolling drift log
  docs/06_quality/PBS-DRIFT-{date}.md       ← human-readable drift report
  data/slo_events/metric_nfr_map.yaml       ← optional metric→NFR override

Signature scheme (HMAC-SHA256 over a deterministic canonical representation):
  payload = "|".join(str(event[f]) for f in signed_fields_default())
  sig     = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

Events without a valid signature are never applied — they are moved to
``quarantine/`` so an operator can review, and the drift log records them
separately. This mirrors the §10 risk table mitigation:

  | ACT-027 Production Feedback Event | 偽造 SLO event 污染 PBS |
  | 事件需 HMAC 簽章 + 時戳驗證 |
  | 未簽章事件一律存 quarantine，不自動 apply |
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import os
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .state_loader import _sanitize_component

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install with: pip install pyyaml"
    ) from exc


# --------------------------------------------------------------------------- #
# Paths                                                                       #
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INBOX = REPO_ROOT / "data" / "slo_events"
DEFAULT_QUARANTINE = DEFAULT_INBOX / "quarantine"
DEFAULT_PROCESSED = DEFAULT_INBOX / "processed"
DEFAULT_DRIFT_LOG_DIR = REPO_ROOT / "build" / "reports" / "fsm"
DEFAULT_DRIFT_REPORT_DIR = REPO_ROOT / "docs" / "06_quality"
DEFAULT_METRIC_MAP = DEFAULT_INBOX / "metric_nfr_map.yaml"

SECRET_ENV = "SDD_SLO_EVENT_SECRET"
DEV_DEFAULT_SECRET = "aisdlc-sdd-dev-secret"  # for tests / local dev only
STALE_EVENT_HOURS = 72                        # events older than 72h rejected
CLOCK_SKEW_TOLERANCE_SECS = 5 * 60            # allow 5 min future-dated drift
DEFAULT_PERSISTENT_THRESHOLD = 3
DEFAULT_WINDOW_HOURS = 24


# --------------------------------------------------------------------------- #
# Schema                                                                      #
# --------------------------------------------------------------------------- #

REQUIRED_FIELDS = (
    "event_id",
    "timestamp",
    "metric",
    "observed",
    "target",
    "unit",
    "duration_minutes",
)


def signed_fields_default() -> Tuple[str, ...]:
    """Fields included in the HMAC canonicalisation (order matters).

    nfr_id 併入簽章覆蓋範圍（R44 cross-platform review fix）：nfr_id 雖非
    REQUIRED_FIELDS（未提供時由 map_metric_to_nfr() 自動推導），但會被用來
    組出 PBS-DRIFT 報告的檔名（見 _report_path()）；若不納入簽章，攻擊者可
    在既有合法簽章事件上事後夾帶 nfr_id 而不被 HMAC 偵測。
    """
    return REQUIRED_FIELDS + ("nfr_id",)


# --------------------------------------------------------------------------- #
# Result dataclasses                                                          #
# --------------------------------------------------------------------------- #

@dataclass
class IngestResult:
    applied: bool
    event_id: Optional[str]
    reason: str
    nfr_id: Optional[str] = None
    drift_log: Optional[str] = None
    drift_report_path: Optional[str] = None


@dataclass
class ScanReport:
    scanned: int = 0
    applied: int = 0
    quarantined: int = 0
    drift_reports: List[str] = field(default_factory=list)
    details: List[Dict[str, Any]] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Utility                                                                     #
# --------------------------------------------------------------------------- #

def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _parse_ts(value: str) -> Optional[_dt.datetime]:
    """Parse an ISO-8601 timestamp; return None on failure."""
    if not isinstance(value, str):
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        ts = _dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_dt.timezone.utc)
    return ts


def _resolve_secret(secret: Optional[str]) -> str:
    if secret:
        return secret
    return os.environ.get(SECRET_ENV) or DEV_DEFAULT_SECRET


def _canonical_payload(event: Dict[str, Any], fields: Iterable[str]) -> str:
    return "|".join(str(event.get(f, "")) for f in fields)


# --------------------------------------------------------------------------- #
# Signature                                                                   #
# --------------------------------------------------------------------------- #

def sign_event(event: Dict[str, Any], secret: Optional[str] = None) -> str:
    """Produce the expected signature for an event (used by test fixtures)."""
    key = _resolve_secret(secret).encode("utf-8")
    payload = _canonical_payload(event, signed_fields_default()).encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_signature(event: Dict[str, Any], secret: Optional[str] = None) -> Tuple[bool, str]:
    """Return (ok, reason). Constant-time comparison to avoid timing oracles."""
    supplied = str(event.get("signature", ""))
    if not supplied:
        return False, "missing_signature"
    fields = event.get("signed_fields") or list(signed_fields_default())
    # Lock down the signed-fields list — we only accept the canonical tuple
    # so an attacker cannot trim fields out of the signature.
    if tuple(fields) != signed_fields_default():
        return False, "unexpected_signed_fields"
    key = _resolve_secret(secret).encode("utf-8")
    payload = _canonical_payload(event, fields).encode("utf-8")
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        return False, "signature_mismatch"
    return True, "ok"


# --------------------------------------------------------------------------- #
# Schema validation                                                           #
# --------------------------------------------------------------------------- #

def validate_schema(event: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(event, dict):
        return False, "event_not_a_mapping"
    for field_name in REQUIRED_FIELDS:
        if field_name not in event:
            return False, f"missing_field:{field_name}"
    for numeric in ("observed", "target", "duration_minutes"):
        try:
            float(event[numeric])
        except (TypeError, ValueError):
            return False, f"non_numeric:{numeric}"
    return True, "ok"


def validate_timestamp(event: Dict[str, Any], now: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    ts = _parse_ts(event.get("timestamp", ""))
    if ts is None:
        return False, "bad_timestamp"
    ref = now or _now()
    if ts > ref + _dt.timedelta(seconds=CLOCK_SKEW_TOLERANCE_SECS):
        return False, "future_timestamp"
    if ref - ts > _dt.timedelta(hours=STALE_EVENT_HOURS):
        return False, "stale_timestamp"
    return True, "ok"


# --------------------------------------------------------------------------- #
# Metric → NFR mapping                                                        #
# --------------------------------------------------------------------------- #

_BUILTIN_MAP: Dict[str, str] = {
    "p95_login_ms": "NFR-PERF-001",
    "p95_api_ms": "NFR-PERF-002",
    "p99_checkout_ms": "NFR-PERF-003",
    "error_rate_percent": "NFR-PERF-010",
    "throughput_rps": "NFR-PERF-020",
}

_LATENCY_PATTERN = re.compile(r"^p\d{2,3}_[a-z0-9_]+_ms$")


def load_metric_map(path: Optional[Path] = None) -> Dict[str, str]:
    """Load metric→NFR override map. Falls back to the built-in mapping."""
    result = dict(_BUILTIN_MAP)
    target = path or DEFAULT_METRIC_MAP
    if not target.exists():
        return result
    try:
        with target.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return result
    overrides = doc.get("metric_to_nfr") if isinstance(doc, dict) else None
    if isinstance(overrides, dict):
        for k, v in overrides.items():
            if isinstance(k, str) and isinstance(v, str):
                result[k] = v
    return result


def map_metric_to_nfr(metric: str, mapping: Optional[Dict[str, str]] = None) -> Optional[str]:
    if not isinstance(metric, str) or not metric:
        return None
    mp = mapping if mapping is not None else load_metric_map()
    if metric in mp:
        return mp[metric]
    # Generic latency fallback — assign a deterministic NFR-PERF-9xx slot so
    # unknown latency metrics still get a trackable identifier.
    if _LATENCY_PATTERN.match(metric):
        digest = int(hashlib.sha1(metric.encode("utf-8")).hexdigest(), 16)
        return f"NFR-PERF-9{digest % 100:02d}"
    return None


# --------------------------------------------------------------------------- #
# Drift log (rolling YAML)                                                    #
# --------------------------------------------------------------------------- #

def _drift_log_path(day: Optional[_dt.date] = None, root: Optional[Path] = None) -> Path:
    base = root or DEFAULT_DRIFT_LOG_DIR
    target_day = day or _dt.date.today()
    return base / f"PBS-DRIFT-{target_day.isoformat()}.yaml"


def _load_drift_log(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"date": path.stem.replace("PBS-DRIFT-", ""), "entries": []}
    with path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    if "entries" not in doc or not isinstance(doc.get("entries"), list):
        doc["entries"] = []
    return doc


def _save_drift_log(path: Path, doc: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, path)


def _append_drift_entry(log_path: Path, entry: Dict[str, Any]) -> None:
    doc = _load_drift_log(log_path)
    doc["entries"].append(entry)
    _save_drift_log(log_path, doc)


# --------------------------------------------------------------------------- #
# Persistent violation detection                                              #
# --------------------------------------------------------------------------- #

def recent_entries_for_nfr(
    drift_log_root: Optional[Path] = None,
    *,
    nfr_id: str,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    now: Optional[_dt.datetime] = None,
) -> List[Dict[str, Any]]:
    """Collect entries for `nfr_id` across drift logs within the window."""
    root = drift_log_root or DEFAULT_DRIFT_LOG_DIR
    if not root.exists():
        return []
    ref = now or _now()
    cutoff = ref - _dt.timedelta(hours=window_hours)
    collected: List[Dict[str, Any]] = []
    # We only need today + yesterday to cover a 24h rolling window.
    for delta in range(0, 2):
        day = (ref - _dt.timedelta(days=delta)).date()
        path = _drift_log_path(day=day, root=root)
        if not path.exists():
            continue
        doc = _load_drift_log(path)
        for e in doc.get("entries") or []:
            if e.get("nfr_id") != nfr_id:
                continue
            ts = _parse_ts(e.get("timestamp", ""))
            if ts and ts >= cutoff:
                collected.append(e)
    return collected


# --------------------------------------------------------------------------- #
# PBS-DRIFT report (markdown)                                                 #
# --------------------------------------------------------------------------- #

def _report_path(nfr_id: str, day: Optional[_dt.date] = None, root: Optional[Path] = None) -> Path:
    base = root or DEFAULT_DRIFT_REPORT_DIR
    target_day = day or _dt.date.today()
    # Path traversal defence: nfr_id is externally-controlled (R44 cross-platform
    # review fix; see state_loader.py _sanitize_component()).
    safe_nfr_id = _sanitize_component(nfr_id)
    return base / f"PBS-DRIFT-{safe_nfr_id}-{target_day.isoformat()}.md"


def _suggest_nfr_update(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute a naive "bump target to observed" suggestion for the report."""
    if not entries:
        return {"old_target": None, "new_target": None, "delta": None}
    try:
        observed_vals = [float(e["observed"]) for e in entries]
        target_vals = [float(e["target"]) for e in entries]
    except (KeyError, TypeError, ValueError):
        return {"old_target": None, "new_target": None, "delta": None}
    old_target = max(target_vals) if target_vals else None
    # Use 95th-percentile-like observed = max observed in window (conservative bump).
    new_target = max(observed_vals) if observed_vals else None
    delta = None
    if old_target is not None and new_target is not None:
        delta = round(new_target - old_target, 3)
    return {"old_target": old_target, "new_target": new_target, "delta": delta}


def _localize_suspects(nfr_id: str, rtm: Optional[List[Any]]) -> Optional[Any]:
    """以 spec_localizer 對 production drift 定位 suspect 節點（advisory，不自動改 spec）.

    rtm 為 spec_localizer.RTMRow 清單或 RTM markdown 文字；缺 RTM 則回 None
    （維持既有「無 RTM 追溯」行為）。失敗不阻塞報告生成。
    """
    if not rtm:
        return None
    try:
        from tools.fsm_runtime import spec_localizer as SL
        rows = SL.parse_rtm_markdown(rtm) if isinstance(rtm, str) else rtm
        return SL.localize_from_production_drift(nfr_id, rows)
    except Exception:  # noqa: BLE001  定位為 advisory，失敗不阻塞 drift 報告
        return None


def generate_drift_report(
    nfr_id: str,
    metric: str,
    entries: List[Dict[str, Any]],
    *,
    report_root: Optional[Path] = None,
    day: Optional[_dt.date] = None,
    rtm: Optional[List[Any]] = None,
) -> Path:
    """Write a human-readable PBS-DRIFT Markdown report and return its path.

    rtm（可選）：提供 RTM（RTMRow 清單或 markdown）時，自動以 spec_localizer 定位
    suspect spec 節點 + 證據附入報告（ACT-086，advisory，絕不自動改 spec）。
    """
    path = _report_path(nfr_id=nfr_id, day=day, root=report_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    suggestion = _suggest_nfr_update(entries)
    unit = entries[0].get("unit", "") if entries else ""
    localization = _localize_suspects(nfr_id, rtm)

    lines: List[str] = []
    lines.append(f"# PBS-DRIFT Report — {nfr_id}")
    lines.append("")
    lines.append(f"- **Metric**: `{metric}`")
    lines.append(f"- **Window**: last {DEFAULT_WINDOW_HOURS}h")
    lines.append(f"- **Events observed**: {len(entries)}")
    lines.append(f"- **Generated at**: {_now().isoformat(timespec='seconds')}")
    lines.append(f"- **Source**: ACT-027 Production Feedback Layer (HMAC-verified)")
    lines.append("")
    lines.append("## Observed Violations")
    lines.append("")
    lines.append("| # | event_id | timestamp | observed | target | unit | duration_min |")
    lines.append("|---|----------|-----------|----------|--------|------|--------------|")
    for idx, e in enumerate(entries, start=1):
        lines.append(
            "| {i} | {eid} | {ts} | {obs} | {tgt} | {unit} | {dur} |".format(
                i=idx,
                eid=e.get("event_id", "?"),
                ts=e.get("timestamp", "?"),
                obs=e.get("observed", "?"),
                tgt=e.get("target", "?"),
                unit=e.get("unit", "?"),
                dur=e.get("duration_minutes", "?"),
            )
        )
    lines.append("")
    # ACT-086 因果定位（advisory）：有 RTM 時自動附 suspect 節點 + 證據
    if localization is not None and localization.suspects:
        from tools.fsm_runtime import spec_localizer as SL
        top = localization.suspects[0].node_id
        lines.append("## 因果定位（Causal Spec Localization — ACT-086 advisory）")
        lines.append("")
        lines.append(f"已自動定位 suspect=**{top}**（spec_localizer，advisory），請人工確認：")
        lines.append("")
        for s in localization.suspects:
            lines.append(f"- `{s.node_id}` — score {s.score} — {s.evidence}")
        lines.append("")
        lines.append("- Blast radius：" + ", ".join(localization.blast_radius or ["—"]))
        lines.append("")
        lines.append("> advisory（Rule 9.23.5）：僅建議 suspect + 證據，**絕不自動改 spec**，需人工裁決。")
        lines.append("")
    lines.append("## Suggested NFR Update Diff")
    lines.append("")
    if suggestion["new_target"] is not None:
        lines.append("```diff")
        lines.append(f"- {nfr_id}.target_{unit or 'value'}: {suggestion['old_target']}")
        lines.append(f"+ {nfr_id}.target_{unit or 'value'}: {suggestion['new_target']}  # +{suggestion['delta']} ({metric})")
        lines.append("```")
    elif localization is not None and localization.suspects:
        lines.append("（事件資料不足以建議新目標 — 已自動定位 suspect="
                     f"{localization.suspects[0].node_id}，請人工確認）")
    else:
        lines.append("（事件資料不足以建議新目標 — 請 sa-analyst 人工分析）")
    lines.append("")
    lines.append("## Next Actions")
    lines.append("")
    lines.append("1. **sa-analyst** 依據此報告更新 `docs/01_requirements/FRD-*.md` 的 NFR 條目")
    lines.append("2. 透過 `spec-logical-validator` 重跑 SLV-001 確認新目標仍 physically feasible")
    lines.append("3. 若採納建議，commit 時附帶本報告連結，RTM 同步更新追溯")
    lines.append("")
    lines.append("## 規格與實作追溯")
    lines.append("")
    lines.append("| 來源 | 連結 |")
    lines.append("|------|------|")
    day_str = (day or _now().date()).isoformat()
    lines.append(f"| Drift 事件原始紀錄 | `build/reports/fsm/PBS-DRIFT-{day_str}.yaml` |")
    lines.append("| 對應 FRD 段落 | `docs/01_requirements/FRD-{SystemName}.md#" + nfr_id.lower().replace("_", "-") + "` |")
    lines.append("| 對應 PBS | `docs/04_planning/performance/PBS-{SystemName}-*.md` |")
    lines.append("| 觸發的 FSM 決策 | 查詢 `FSM-STATE-{project}.yaml#decision_trace`（trigger=`production_signal_enter`） |")
    lines.append("")
    lines.append("## 治理附註")
    lines.append("")
    lines.append("- 本報告不是自動 apply — **禁止** 直接覆寫 FRD 檔案")
    lines.append("- 若 24h 內產生多份同 NFR 報告，最新版覆寫舊版（歷史保留在 `PBS-DRIFT-{date}.yaml`）")
    lines.append("- 事件簽章失敗者不會出現在此報告（已 quarantine 於 `data/slo_events/quarantine/`）")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> 本報告由 `tools/fsm_runtime/production_monitor.generate_drift_report()` 自動生成。")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Core ingest                                                                 #
# --------------------------------------------------------------------------- #

def ingest_slo_violation(
    event: Dict[str, Any],
    *,
    secret: Optional[str] = None,
    drift_log_root: Optional[Path] = None,
    report_root: Optional[Path] = None,
    metric_map: Optional[Dict[str, str]] = None,
    persistent_threshold: int = DEFAULT_PERSISTENT_THRESHOLD,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    now: Optional[_dt.datetime] = None,
) -> IngestResult:
    """Validate + persist a single SLO violation event.

    Pipeline:
      schema -> timestamp -> signature -> NFR mapping -> append to drift log
      -> if recent entries for that NFR ≥ threshold => generate PBS-DRIFT report
    """
    ok_schema, schema_reason = validate_schema(event)
    if not ok_schema:
        return IngestResult(applied=False, event_id=event.get("event_id") if isinstance(event, dict) else None,
                            reason=schema_reason)
    ok_ts, ts_reason = validate_timestamp(event, now=now)
    if not ok_ts:
        return IngestResult(applied=False, event_id=event.get("event_id"), reason=ts_reason)
    ok_sig, sig_reason = verify_signature(event, secret=secret)
    if not ok_sig:
        return IngestResult(applied=False, event_id=event.get("event_id"), reason=sig_reason)

    nfr_id = event.get("nfr_id") or map_metric_to_nfr(event["metric"], metric_map)
    if not nfr_id:
        return IngestResult(
            applied=False,
            event_id=event.get("event_id"),
            reason=f"no_nfr_mapping_for_metric:{event['metric']}",
        )

    drift_root = drift_log_root or DEFAULT_DRIFT_LOG_DIR
    today = (now or _now()).date()
    log_path = _drift_log_path(day=today, root=drift_root)
    entry = {
        "event_id": event["event_id"],
        "timestamp": event["timestamp"],
        "metric": event["metric"],
        "observed": event["observed"],
        "target": event["target"],
        "unit": event["unit"],
        "duration_minutes": event["duration_minutes"],
        "nfr_id": nfr_id,
        "ingested_at": (now or _now()).isoformat(timespec="seconds"),
    }
    _append_drift_entry(log_path, entry)

    drift_report: Optional[Path] = None
    recent = recent_entries_for_nfr(
        drift_log_root=drift_root,
        nfr_id=nfr_id,
        window_hours=window_hours,
        now=now,
    )
    if len(recent) >= persistent_threshold:
        drift_report = generate_drift_report(
            nfr_id=nfr_id,
            metric=event["metric"],
            entries=recent,
            report_root=report_root,
            day=today,
        )

    return IngestResult(
        applied=True,
        event_id=event["event_id"],
        reason="ok",
        nfr_id=nfr_id,
        drift_log=str(log_path),
        drift_report_path=str(drift_report) if drift_report else None,
    )


# --------------------------------------------------------------------------- #
# Inbox scanner                                                               #
# --------------------------------------------------------------------------- #

def _move_event_file(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        # Disambiguate collisions without clobbering evidence.
        dest = dest_dir / f"{src.stem}-{uuid.uuid4().hex[:8]}{src.suffix}"
    shutil.move(str(src), str(dest))
    return dest


def _load_event_file(path: Path) -> Tuple[Optional[Dict[str, Any]], str]:
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        return None, f"file_error:{exc.__class__.__name__}"
    if not isinstance(doc, dict):
        return None, "non_dict_event"
    return doc, "ok"


def scan_inbox(
    *,
    inbox: Optional[Path] = None,
    quarantine: Optional[Path] = None,
    processed: Optional[Path] = None,
    secret: Optional[str] = None,
    drift_log_root: Optional[Path] = None,
    report_root: Optional[Path] = None,
    persistent_threshold: int = DEFAULT_PERSISTENT_THRESHOLD,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    now: Optional[_dt.datetime] = None,
) -> ScanReport:
    """Ingest every `*.yaml` in the inbox; move events accordingly."""
    ibox = inbox or DEFAULT_INBOX
    qrt = quarantine or DEFAULT_QUARANTINE
    prc = processed or DEFAULT_PROCESSED
    ibox.mkdir(parents=True, exist_ok=True)
    qrt.mkdir(parents=True, exist_ok=True)
    prc.mkdir(parents=True, exist_ok=True)

    report = ScanReport()
    # Only consider direct .yaml files (not files inside quarantine/processed sub-dirs).
    for path in sorted(ibox.glob("*.yaml")):
        # metric_nfr_map.yaml is a config file, not an event.
        if path.name == DEFAULT_METRIC_MAP.name and path.resolve() == DEFAULT_METRIC_MAP.resolve():
            continue
        report.scanned += 1
        event, load_reason = _load_event_file(path)
        if event is None:
            dest = _move_event_file(path, qrt)
            report.quarantined += 1
            report.details.append(
                {"path": path.name, "applied": False, "reason": load_reason, "quarantine": str(dest)}
            )
            continue
        result = ingest_slo_violation(
            event,
            secret=secret,
            drift_log_root=drift_log_root,
            report_root=report_root,
            persistent_threshold=persistent_threshold,
            window_hours=window_hours,
            now=now,
        )
        if result.applied:
            dest = _move_event_file(path, prc)
            report.applied += 1
            detail = {
                "path": path.name,
                "applied": True,
                "event_id": result.event_id,
                "nfr_id": result.nfr_id,
                "drift_log": result.drift_log,
                "drift_report": result.drift_report_path,
                "processed": str(dest),
            }
            # Same NFR within the 24h window writes back to the same report file —
            # dedupe so the scan report reflects unique paths, not append count.
            if result.drift_report_path and result.drift_report_path not in report.drift_reports:
                report.drift_reports.append(result.drift_report_path)
            report.details.append(detail)
        else:
            dest = _move_event_file(path, qrt)
            report.quarantined += 1
            report.details.append(
                {
                    "path": path.name,
                    "applied": False,
                    "event_id": result.event_id,
                    "reason": result.reason,
                    "quarantine": str(dest),
                }
            )
    return report


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #

def _cli() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Production feedback layer (ACT-027)")
    parser.add_argument("command", choices=["scan", "sign", "verify"])
    parser.add_argument("--inbox", default=None, help="Override inbox directory")
    parser.add_argument("--event", default=None, help="Path to a single event YAML (for sign/verify)")
    parser.add_argument("--secret", default=None, help="HMAC secret (default: env SDD_SLO_EVENT_SECRET)")
    args = parser.parse_args()

    if args.command == "scan":
        report = scan_inbox(
            inbox=Path(args.inbox) if args.inbox else None,
            secret=args.secret,
        )
        print(json.dumps(
            {
                "scanned": report.scanned,
                "applied": report.applied,
                "quarantined": report.quarantined,
                "drift_reports": report.drift_reports,
                "details": report.details,
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if args.command in {"sign", "verify"}:
        if not args.event:
            parser.error("--event required")
        event_path = Path(args.event)
        with event_path.open("r", encoding="utf-8") as f:
            event = yaml.safe_load(f) or {}
        if args.command == "sign":
            event["signed_fields"] = list(signed_fields_default())
            event["signature"] = sign_event(event, secret=args.secret)
            with event_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(event, f, allow_unicode=True, sort_keys=False)
            print(json.dumps({"signed": True, "path": str(event_path)}, ensure_ascii=False))
            return 0
        ok, reason = verify_signature(event, secret=args.secret)
        print(json.dumps({"ok": ok, "reason": reason}, ensure_ascii=False))
        return 0 if ok else 1
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
