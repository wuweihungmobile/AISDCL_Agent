"""drift_monitor.py — Phase G M4 / ACT-039/040 Continuous Drift Monitor

Computes spec ↔ code drift score per commit. Used by:
  - .claude/hooks/post_commit_drift.py (post-commit advisory)
  - daily 02:30 UTC cron job (DAILY-{date}.md rolling 7 days)

Public surface:
    DriftReport               — dataclass {api_drift, type_drift, total_score, ...}
    compute_drift(...)        — main entry; returns DriftReport
    check_consecutive_drift() — Rule 9.17.3 (3-in-a-row → SPEC_AUDIT)
    write_commit_report(...)  — persist COMMIT-{sha}.yaml
    write_daily_report(...)   — rolling 7-day DAILY-{date}.md

Formula (per cicd/SDD_DRIFT_MONITOR.md):
    api_drift  = |spec △ code| / max(|spec ∪ code|, 1)
    type_drift = sum(missing_fields) / max(total_spec_fields, 1)
    drift_score = 0.6 * api_drift + 0.4 * type_drift
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

# ─────────────────────────────────────────────────────────────
# Patterns
# ─────────────────────────────────────────────────────────────

_OPENAPI_PATH_PATTERN = re.compile(r"^\s{2}(/[\w\-/{}.:]+):\s*$", re.MULTILINE)
_OPENAPI_METHOD_PATTERN = re.compile(
    r"^\s{4}(get|post|put|patch|delete|head|options):\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# FastAPI / Flask / Express route patterns (best-effort)
_CODE_ROUTE_PATTERNS = [
    # FastAPI:  @app.get("/path")  / @router.post("/path")
    re.compile(
        r"@(?:app|router)\.(get|post|put|patch|delete|head|options)\s*\(\s*[\"']([^\"']+)[\"']",
        re.IGNORECASE,
    ),
    # Flask: @app.route("/path", methods=["POST"])
    re.compile(
        r"@(?:app|blueprint|bp)\.route\s*\(\s*[\"']([^\"']+)[\"'][^)]*methods\s*=\s*\[\s*[\"'](\w+)",
        re.IGNORECASE,
    ),
    # Express: app.get('/path', ...) / router.post('/path', ...)
    re.compile(
        r"\b(?:app|router)\.(get|post|put|patch|delete|head|options)\s*\(\s*[\"']([^\"']+)[\"']",
        re.IGNORECASE,
    ),
]

_FRD_TYPE_PATTERN = re.compile(
    r"###\s*type:\s*(\w+).*?\{([^}]+)\}",
    re.DOTALL | re.IGNORECASE,
)
_CODE_CLASS_PATTERN = re.compile(
    r"^\s*(?:class|interface)\s+(\w+)\s*[\(:]",
    re.MULTILINE,
)
_CODE_FIELD_PATTERN = re.compile(r"^\s+(\w+)\s*[:=]", re.MULTILINE)


# ─────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────


@dataclass
class DriftReport:
    commit_sha: str
    api_drift: float = 0.0
    type_drift: float = 0.0
    total_score: float = 0.0
    spec_endpoints: int = 0
    code_endpoints: int = 0
    missing_in_code: List[str] = field(default_factory=list)
    missing_in_spec: List[str] = field(default_factory=list)
    spec_types: int = 0
    type_field_misses: int = 0
    elapsed_ms: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────────────────────


def _extract_openapi_endpoints(openapi_text: str) -> Set[str]:
    """Return set of '{METHOD} {path}' from openapi yaml text."""
    out: Set[str] = set()
    lines = openapi_text.splitlines()
    current_path: Optional[str] = None
    for i, line in enumerate(lines):
        if re.match(r"^\s{2}(/[\w\-/{}.:]+):\s*$", line):
            current_path = line.strip().rstrip(":")
            continue
        m = re.match(r"^\s{4}(get|post|put|patch|delete|head|options):\s*$", line, re.IGNORECASE)
        if m and current_path:
            out.add(f"{m.group(1).upper()} {current_path}")
    return out


def _extract_code_routes(code_dir: Path) -> Set[str]:
    """Scan code dir for route declarations, return {METHOD path} set."""
    out: Set[str] = set()
    if not code_dir.exists():
        return out
    for ext in ("*.py", "*.js", "*.ts"):
        for f in code_dir.rglob(ext):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat in _CODE_ROUTE_PATTERNS:
                for m in pat.finditer(text):
                    g = m.groups()
                    # FastAPI/Express: (method, path); Flask reversed
                    if g[0].lower() in {"get", "post", "put", "patch", "delete", "head", "options"}:
                        method, path = g[0].upper(), g[1]
                    else:
                        path, method = g[0], g[1].upper()
                    out.add(f"{method} {path}")
    return out


def _extract_frd_types(frd_text: str) -> Dict[str, Set[str]]:
    """Return {TypeName: {fields}} from FRD ### type: declarations."""
    out: Dict[str, Set[str]] = {}
    for m in _FRD_TYPE_PATTERN.finditer(frd_text):
        name = m.group(1)
        body = m.group(2)
        fields = {f.strip() for f in re.split(r"[,\n]", body) if f.strip()}
        out[name] = fields
    return out


def _extract_code_classes(code_dir: Path) -> Dict[str, Set[str]]:
    """Return {ClassName: {fields}} from code class definitions."""
    out: Dict[str, Set[str]] = {}
    if not code_dir.exists():
        return out
    for ext in ("*.py", "*.ts"):
        for f in code_dir.rglob(ext):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            classes = list(_CODE_CLASS_PATTERN.finditer(text))
            for i, cm in enumerate(classes):
                name = cm.group(1)
                start = cm.end()
                end = classes[i + 1].start() if i + 1 < len(classes) else len(text)
                body = text[start:end]
                fields = set(_CODE_FIELD_PATTERN.findall(body))
                out.setdefault(name, set()).update(fields)
    return out


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────


def compute_drift(
    commit_sha: str,
    *,
    openapi_path: Optional[Path] = None,
    frd_dir: Optional[Path] = None,
    code_dir: Optional[Path] = None,
) -> DriftReport:
    """Compute drift_score for a given commit."""
    started = datetime.now(timezone.utc)
    spec_endpoints: Set[str] = set()
    code_endpoints: Set[str] = set()
    spec_types: Dict[str, Set[str]] = {}
    code_classes: Dict[str, Set[str]] = {}

    if openapi_path and openapi_path.exists():
        spec_endpoints = _extract_openapi_endpoints(
            openapi_path.read_text(encoding="utf-8", errors="ignore")
        )
    if code_dir and code_dir.exists():
        code_endpoints = _extract_code_routes(code_dir)
    if frd_dir and frd_dir.exists():
        for f in frd_dir.glob("FRD-*.md"):
            spec_types.update(_extract_frd_types(f.read_text(encoding="utf-8", errors="ignore")))
    if code_dir and code_dir.exists():
        code_classes = _extract_code_classes(code_dir)

    sym_diff = spec_endpoints.symmetric_difference(code_endpoints)
    union = spec_endpoints | code_endpoints
    api_drift = round(len(sym_diff) / max(len(union), 1), 4)

    total_spec_fields = sum(len(v) for v in spec_types.values())
    misses = 0
    for name, fields in spec_types.items():
        code_fields = code_classes.get(name, set())
        misses += len(fields - code_fields)
    type_drift = round(misses / max(total_spec_fields, 1), 4)

    total = round(0.6 * api_drift + 0.4 * type_drift, 4)
    elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

    return DriftReport(
        commit_sha=commit_sha,
        api_drift=api_drift,
        type_drift=type_drift,
        total_score=total,
        spec_endpoints=len(spec_endpoints),
        code_endpoints=len(code_endpoints),
        missing_in_code=sorted(spec_endpoints - code_endpoints),
        missing_in_spec=sorted(code_endpoints - spec_endpoints),
        spec_types=len(spec_types),
        type_field_misses=misses,
        elapsed_ms=elapsed_ms,
        timestamp=started.isoformat(),
    )


def write_commit_report(report: DriftReport, *, repo_root: Optional[Path] = None) -> Path:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "build" / "reports" / "drift"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"COMMIT-{report.commit_sha[:12]}.yaml"
    p.write_text(yaml.safe_dump(report.to_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def check_consecutive_drift(
    repo_root: Optional[Path] = None,
    *,
    window: int = 3,
    threshold: float = 0.3,
) -> Tuple[bool, List[str]]:
    """Rule 9.17.3 — return (escalate?, sha_list) if last `window` commits all >= threshold."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "build" / "reports" / "drift"
    if not out_dir.exists():
        return False, []
    files = sorted(out_dir.glob("COMMIT-*.yaml"), key=lambda f: f.stat().st_mtime)
    if len(files) < window:
        return False, []
    last = files[-window:]
    shas: List[str] = []
    for f in last:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return False, []
        if data.get("total_score", 0) < threshold:
            return False, []
        shas.append(data.get("commit_sha", "unknown"))
    return True, shas


def write_daily_report(
    repo_root: Optional[Path] = None,
    *,
    date: Optional[str] = None,
    rolling_days: int = 7,
) -> Path:
    """Rule 9.17.4 — daily rolling 7-day drift report."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = repo_root / "build" / "reports" / "drift"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(out_dir.glob("COMMIT-*.yaml"), key=lambda f: f.stat().st_mtime)
    if rolling_days > 0:
        files = files[-rolling_days * 50:]  # cap
    rows: List[dict] = []
    for f in files:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        rows.append(data)
    p = out_dir / f"DAILY-{date}.md"
    body = ["# Drift Daily Report — " + date, "", f"Rolling window: last {rolling_days} days", ""]
    body.append("| commit | total_score | api_drift | type_drift | timestamp |")
    body.append("|--------|-------------|-----------|------------|-----------|")
    for r in rows:
        body.append(
            f"| {str(r.get('commit_sha', ''))[:12]} | {r.get('total_score', 0):.4f} | "
            f"{r.get('api_drift', 0):.4f} | {r.get('type_drift', 0):.4f} | {r.get('timestamp', '')} |"
        )
    p.write_text("\n".join(body) + "\n", encoding="utf-8")
    return p
