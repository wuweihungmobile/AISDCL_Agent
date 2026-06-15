"""PII Scanner — detect L2 (confidential) hits & quarantine artifact.

ACT-030 (Phase F M2 D-30.6).

Spec: docs/06_quality/HUB-GOVERNANCE-SPEC.md §4.1, §伍 (Quarantine 流程)
Rules: tools/fsm_runtime/anonymizer_rules.yaml (level: L2 entries + deny lists)

Behaviour:
  - Loads L2 rules from anonymizer_rules.yaml plus per-project deny_lists.
  - scan(text) returns ScanResult with all hits (no replacement — L2 hits
    must trigger quarantine and abort the push, per G-30.1 / G-30.2).
  - scan_artifact(path, ...) writes QUARANTINE-{date}-{seq}.yaml when hits
    are found, with the schema defined in HUB-GOVERNANCE-SPEC §5.1
    (matched body redacted by anonymizer._redact_for_log).
  - For credit-card pattern, applies Luhn check to reduce false positives
    (HUB-GOVERNANCE §4.1 footnote: "PII Scanner 二次以 Luhn 演算法確認").

Public API:
  load_l2_rules(path) -> tuple[L2Rule, ...]
  scan(text, *, rules=None) -> ScanResult
  scan_artifact(artifact_path, *, quarantine_dir, rules=None) -> ScanArtifactResult
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import re
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

from .anonymizer import _redact_for_log, REPO_ROOT, DEFAULT_RULES_PATH


@dataclasses.dataclass(frozen=True)
class L2Rule:
    rule_id: str
    category: str
    pattern: re.Pattern
    description: str = ""


@dataclasses.dataclass
class Hit:
    rule_id: str
    category: str
    line: int
    matched_redacted: str   # never the raw text


@dataclasses.dataclass
class ScanResult:
    hits: List[Hit]
    rules_path: Path

    @property
    def clean(self) -> bool:
        return not self.hits


@dataclasses.dataclass
class ScanArtifactResult:
    scan: ScanResult
    quarantine_path: Optional[Path]
    artifact_path: Path


def _luhn_valid(digits_only: str) -> bool:
    if not digits_only or len(digits_only) < 13:
        return False
    total = 0
    parity = len(digits_only) % 2
    for i, ch in enumerate(digits_only):
        if not ch.isdigit():
            return False
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _compile_pattern(pattern_str: str, case_insensitive: bool) -> re.Pattern:
    flags = re.IGNORECASE if case_insensitive else 0
    return re.compile(pattern_str, flags)


def _build_deny_list_pattern(items: Sequence[str]) -> Optional[re.Pattern]:
    cleaned = [re.escape(s.strip()) for s in items if s and str(s).strip()]
    if not cleaned:
        return None
    return re.compile(r"(?:" + "|".join(cleaned) + r")", re.IGNORECASE)


def load_l2_rules(path: Optional[Path] = None) -> Tuple[Tuple[L2Rule, ...], dict]:
    """Return (rules tuple, raw_doc) so callers can read deny-list state."""
    rules_path = Path(path) if path else DEFAULT_RULES_PATH
    if not rules_path.exists():
        raise FileNotFoundError(f"anonymizer rules not found: {rules_path}")
    doc = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}

    rules: List[L2Rule] = []
    for rule in doc.get("rules", []) or []:
        if rule.get("level") != "L2":
            continue

        # Static-pattern L2 rules
        pattern_str = rule.get("pattern") or ""
        if pattern_str:
            rules.append(L2Rule(
                rule_id=str(rule.get("id", "")),
                category=str(rule.get("category", "")),
                pattern=_compile_pattern(pattern_str, bool(rule.get("case_insensitive", False))),
                description=str(rule.get("description", "")),
            ))
            continue

        # Dynamic deny-list rules (empty pattern + dynamic_source key)
        dyn_src = rule.get("dynamic_source")
        if dyn_src:
            items = doc.get(dyn_src) or []
            compiled = _build_deny_list_pattern(items)
            if compiled is not None:
                rules.append(L2Rule(
                    rule_id=str(rule.get("id", "")),
                    category=str(rule.get("category", "")),
                    pattern=compiled,
                    description=f"deny_list: {dyn_src}",
                ))
            # Empty deny_list is intentional (OPEN-G.1 default empty); skip silently.

    return tuple(rules), doc


def scan(
    text: str,
    *,
    rules: Optional[Sequence[L2Rule]] = None,
    rules_path: Optional[Path] = None,
) -> ScanResult:
    """Scan `text` for L2 hits. Returns all hits (does not stop at first)."""
    if rules is None:
        rules, _ = load_l2_rules(rules_path)
    if not text:
        return ScanResult(hits=[], rules_path=Path(rules_path or DEFAULT_RULES_PATH))

    hits: List[Hit] = []
    lines = text.splitlines() or [text]

    for rule in rules:
        for lineno, line in enumerate(lines, start=1):
            for m in rule.pattern.finditer(line):
                raw = m.group(0)
                # Luhn refinement for credit-card category (reduce false-positive on
                # plain integers).
                if rule.category == "financial":
                    digits = re.sub(r"[^\d]", "", raw)
                    if not _luhn_valid(digits):
                        continue
                hits.append(Hit(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    line=lineno,
                    matched_redacted=_redact_for_log(raw),
                ))
    return ScanResult(hits=hits, rules_path=Path(rules_path or DEFAULT_RULES_PATH))


def _next_quarantine_seq(quarantine_dir: Path, today: str) -> int:
    """Return next sequence number for QUARANTINE-{today}-{seq}.yaml."""
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    pattern = f"QUARANTINE-{today}-"
    existing = [
        p for p in quarantine_dir.glob(f"{pattern}*.yaml")
        if p.name.startswith(pattern)
    ]
    if not existing:
        return 1
    seqs: List[int] = []
    for p in existing:
        try:
            tail = p.stem[len(pattern):]
            seqs.append(int(tail))
        except (ValueError, IndexError):
            continue
    return (max(seqs) + 1) if seqs else 1


def write_quarantine(
    artifact_path: Path,
    scan_result: ScanResult,
    *,
    quarantine_dir: Path,
    trigger: str = "pre_push_pii_scan",
) -> Path:
    """Write QUARANTINE-{date}-{seq}.yaml per HUB-GOVERNANCE-SPEC §5.1."""
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    seq = _next_quarantine_seq(quarantine_dir, today)
    qid = f"QUARANTINE-{today}-{seq:03d}"
    out_path = quarantine_dir / f"{qid}.yaml"

    payload = {
        "quarantine_id": qid,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "trigger": trigger,
        "artifact_path": str(artifact_path),
        "hit_patterns": [
            {
                "pattern_id": h.rule_id,
                "category": h.category,
                "line": h.line,
                "matched": h.matched_redacted,
            } for h in scan_result.hits
        ],
        "resolution_status": "pending",
        "resolved_by": None,
        "resolved_at": None,
        "notes": None,
    }
    # Custom YAML emit: avoid yaml.safe_dump default sort to keep schema order.
    out_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return out_path


def scan_artifact(
    artifact_path: Path,
    *,
    quarantine_dir: Optional[Path] = None,
    trigger: str = "pre_push_pii_scan",
    rules_path: Optional[Path] = None,
) -> ScanArtifactResult:
    """Scan a file; if any L2 hits, write quarantine YAML and return path."""
    if not artifact_path.exists():
        raise FileNotFoundError(f"artifact not found: {artifact_path}")

    text = artifact_path.read_text(encoding="utf-8", errors="replace")
    rules_tuple, _ = load_l2_rules(rules_path)
    result = scan(text, rules=rules_tuple, rules_path=rules_path)

    qpath: Optional[Path] = None
    if not result.clean:
        qdir = quarantine_dir or (REPO_ROOT / "build" / "reports" / "hub")
        qpath = write_quarantine(
            artifact_path, result,
            quarantine_dir=qdir, trigger=trigger,
        )

    return ScanArtifactResult(
        scan=result,
        quarantine_path=qpath,
        artifact_path=artifact_path,
    )


def _cli() -> int:
    import argparse
    import json
    import sys
    parser = argparse.ArgumentParser(description="Scan text for L2 PII hits (HUB-GOVERNANCE-SPEC §4.1)")
    parser.add_argument("artifact", nargs="?", help="path to artifact (default: stdin scan-only mode)")
    parser.add_argument("--rules", help="path to anonymizer_rules.yaml")
    parser.add_argument("--quarantine-dir", help="dir to write quarantine YAML when hits found")
    parser.add_argument("--no-quarantine", action="store_true", help="report-only, do not write YAML")
    parser.add_argument("--trigger", default="cli_manual", help="trigger label (audit log)")
    args = parser.parse_args()

    if args.artifact:
        path = Path(args.artifact)
        result = scan_artifact(
            path,
            quarantine_dir=Path(args.quarantine_dir) if args.quarantine_dir else None,
            trigger=args.trigger,
            rules_path=Path(args.rules) if args.rules else None,
        )
        sys.stdout.write(json.dumps({
            "clean": result.scan.clean,
            "hit_count": len(result.scan.hits),
            "quarantine_path": str(result.quarantine_path) if result.quarantine_path else None,
            "hits": [dataclasses.asdict(h) for h in result.scan.hits],
        }, ensure_ascii=False, indent=2))
        if args.no_quarantine and result.quarantine_path:
            result.quarantine_path.unlink(missing_ok=True)
        return 0 if result.scan.clean else 1

    text = sys.stdin.read()
    rules_tuple, _ = load_l2_rules(Path(args.rules) if args.rules else None)
    res = scan(text, rules=rules_tuple)
    sys.stdout.write(json.dumps({
        "clean": res.clean,
        "hit_count": len(res.hits),
        "hits": [dataclasses.asdict(h) for h in res.hits],
    }, ensure_ascii=False, indent=2))
    return 0 if res.clean else 1


if __name__ == "__main__":  # pragma: no cover
    import sys as _sys
    _sys.exit(_cli())
