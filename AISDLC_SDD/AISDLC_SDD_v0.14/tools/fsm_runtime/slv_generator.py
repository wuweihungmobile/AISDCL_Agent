"""ACT-028 SLV Rule Generator — Phase E M4 Learning Layer MVP.

Converts FPL (Failure Pattern Library) entries into draft SLV rules that
spec-logical-validator's rule engine can load. Per §OPEN-10.7 user decision,
the LLM backend is **Claude Code Session** (not Claude API) — this module is
therefore *pattern-extraction oriented*: it parses the already-structured
FPL markdown for the `建議 SLV 規則（草案）` block and produces a YAML file
under `.claude/skills/spec-logical-validator/rules/` with strict invariants:

  - `trust_level: proposed`  (never auto-promoted — see §9.11)
  - `reviewed_by: null`      (operator must fill before enforce)
  - `source: "FPL-XXX auto-generated YYYY-MM-DD"`  (audit link)

Design decisions:

1. **No side effects on FSM** — propose_slv_from_fpl() is a pure rule
   synthesizer; the caller (typically /slv-generator Skill or
   LEARNING_COMMIT entry flow) is responsible for state transition.
2. **Idempotent writes** — existing `SLV-XXX.yaml` at `proposed` trust level
   is overwritten; `verified` files are never replaced (raises
   `RuleOverwriteProtected`) to prevent silent regression of reviewed rules.
3. **Minimal dependencies** — PyYAML only. No LLM / embedding at this
   layer; smarter synthesis happens in the Skill-level orchestration.

Public API:

    load_fpl_entry(fpl_id: str) -> FPLEntry
    propose_slv_from_fpl(fpl: FPLEntry, *, slv_id: str = None) -> SLVRuleCandidate
    write_rule_candidate(cand: SLVRuleCandidate, *, overwrite_proposed=True) -> Path
    next_available_slv_id(rules_dir: Path = None) -> str

CLI:

    python -m tools.fsm_runtime.slv_generator propose FPL-001
    python -m tools.fsm_runtime.slv_generator list-fpl
    python -m tools.fsm_runtime.slv_generator list-rules
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required. Install: pip install pyyaml") from exc


REPO_ROOT = Path(__file__).resolve().parents[2]
FPL_DIR = REPO_ROOT / "knowledge" / "failure-patterns"
RULES_DIR = REPO_ROOT / ".claude" / "skills" / "spec-logical-validator" / "rules"

VALID_TRUST_LEVELS = {"verified", "proposed", "external"}
SLV_ID_RE = re.compile(r"^SLV-(\d{3,})$")
FPL_ID_RE = re.compile(r"^FPL-\d{3,}$")


class RuleOverwriteProtected(RuntimeError):
    """Raised when trying to overwrite a verified rule."""


class ImmutableFieldViolation(RuntimeError):
    """Raised when an overwrite attempts to change an immutable field.

    M4 QA Round-6 P0-4：`source` 與 `source_fpl` 是 FPL → SLV 審計鏈的錨點，
    一旦規則落盤即不得被後續 overwrite 改寫。此 exception 作為明確訊號
    讓呼叫方（CLI / Skill / 人工）立即回頭檢查是否誤指向錯誤 FPL。
    """


class SchemaViolation(ValueError):
    """Raised when a rule YAML violates the SLV schema invariants.

    M4 QA Round-6 P1-3：verified 規則必須齊備 reviewed_by / reviewed_at；
    source_fpl / source 型別必須是字串；source_fpl 需符合 `FPL-NNN` 格式。
    """


class FPLNotFound(FileNotFoundError):
    """Raised when an FPL id cannot be resolved to a markdown file."""


@dataclass
class FPLEntry:
    fpl_id: str
    title: str
    path: Path
    summary: str = ""
    regex_pattern: Optional[str] = None
    required_qualifiers: List[str] = field(default_factory=list)
    failure_example: str = ""
    pass_example: str = ""
    raw_yaml_block: Optional[Dict[str, Any]] = None  # parsed yaml fence, if any


@dataclass
class SLVRuleCandidate:
    id: str
    name: str
    source: str
    trust_level: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    scope: str
    purpose: str
    scan_targets: List[str]
    required_qualifiers: List[str]
    failure_examples: List[str]
    pass_examples: List[str]
    severity: str
    blocks_scg: bool
    source_fpl: str
    pattern_regex: Optional[str] = None

    def to_yaml_doc(self) -> Dict[str, Any]:
        """Serialize to the schema used by rules/SLV-00N.yaml."""
        doc: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "trust_level": self.trust_level,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "scope": self.scope,
            "purpose": self.purpose,
            "scan_targets": list(self.scan_targets),
            "required_qualifiers": list(self.required_qualifiers),
            "failure_examples": list(self.failure_examples),
            "pass_examples": list(self.pass_examples),
            "severity": self.severity,
            "blocks_scg": self.blocks_scg,
            "source_fpl": self.source_fpl,
        }
        if self.pattern_regex:
            doc["pattern_regex"] = self.pattern_regex
        return doc


# ---------- FPL parsing ----------

def _fpl_path(fpl_id: str) -> Path:
    if not FPL_ID_RE.match(fpl_id):
        raise ValueError(f"invalid FPL id: {fpl_id!r} (expected FPL-NNN)")
    matches = sorted(FPL_DIR.glob(f"{fpl_id}-*.md"))
    if not matches:
        raise FPLNotFound(f"no FPL markdown for {fpl_id} under {FPL_DIR}")
    return matches[0]


def _extract_yaml_block(text: str, anchor: str) -> Optional[Dict[str, Any]]:
    """Return the first yaml fenced block after an anchor header."""
    idx = text.find(anchor)
    if idx == -1:
        return None
    fence = re.search(r"```yaml\n(.*?)\n```", text[idx:], flags=re.DOTALL)
    if not fence:
        return None
    try:
        return yaml.safe_load(fence.group(1)) or None
    except yaml.YAMLError:
        return None


def _extract_title(text: str) -> str:
    m = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    return m.group(1).strip() if m else ""


def _extract_summary(text: str) -> str:
    m = re.search(r"^##\s+摘要\s*\n(.+?)(?=\n##\s)", text, flags=re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def load_fpl_entry(fpl_id: str) -> FPLEntry:
    path = _fpl_path(fpl_id)
    text = path.read_text(encoding="utf-8")
    title = _extract_title(text)
    summary = _extract_summary(text)
    block = _extract_yaml_block(text, "建議 SLV 規則")
    regex_pattern = None
    required: List[str] = []
    failure_example = ""
    pass_example = ""
    if block and isinstance(block, dict):
        # The top-level key in the block is typically "slv_00N_candidate".
        candidate = next(iter(block.values())) if block else {}
        if isinstance(candidate, dict):
            pattern_block = candidate.get("pattern")
            if isinstance(pattern_block, dict):
                regex_pattern = pattern_block.get("regex")
            required = list(candidate.get("required_qualifier") or [])
            failure_example = str(candidate.get("failure_example") or "").strip()
            pass_example = str(candidate.get("pass_example") or "").strip()
    return FPLEntry(
        fpl_id=fpl_id,
        title=title,
        path=path,
        summary=summary,
        regex_pattern=regex_pattern,
        required_qualifiers=required,
        failure_example=failure_example,
        pass_example=pass_example,
        raw_yaml_block=block,
    )


# ---------- SLV id allocation ----------

def _scan_existing_ids(rules_dir: Path) -> List[int]:
    ids: List[int] = []
    if not rules_dir.exists():
        return ids
    for p in rules_dir.glob("SLV-*.yaml"):
        m = SLV_ID_RE.match(p.stem)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


def next_available_slv_id(rules_dir: Optional[Path] = None) -> str:
    target = rules_dir or RULES_DIR
    ids = _scan_existing_ids(target)
    nxt = (ids[-1] + 1) if ids else 1
    return f"SLV-{nxt:03d}"


# ---------- Proposal synthesis ----------

_SCOPE_HEURISTICS = [
    # (keyword in FPL title/summary/pattern, scope)
    ("時序", "temporal"),
    ("穩態", "temporal"),
    ("快取", "cache"),
    ("cache", "cache"),
    ("contract", "contract"),
    ("invariant", "invariant"),
    ("依賴", "dependency"),
    ("AC", "ac"),
    ("NFR", "nfr"),
    ("test", "test"),
]

_DEFAULT_SCAN_TARGETS = [
    "docs/01_requirements/FRD-*.md",
    "docs/03_testing/contracts/TCS-*.md",
]


def _infer_scope(fpl: FPLEntry) -> str:
    corpus = f"{fpl.title} {fpl.summary} {fpl.regex_pattern or ''}".lower()
    for keyword, scope in _SCOPE_HEURISTICS:
        if keyword.lower() in corpus:
            return scope
    return "generic"


def propose_slv_from_fpl(
    fpl: FPLEntry,
    *,
    slv_id: Optional[str] = None,
    now: Optional[_dt.date] = None,
) -> SLVRuleCandidate:
    """Synthesize an SLV rule candidate from an FPL entry.

    The candidate is always `trust_level: proposed` — commitment to
    `verified` happens after human review (see exit_learning_commit()).
    """
    if not fpl.required_qualifiers and not fpl.regex_pattern:
        raise ValueError(
            f"FPL {fpl.fpl_id} has no `required_qualifier` or `pattern.regex` block "
            "— cannot synthesize SLV candidate. Fix the FPL entry first."
        )
    slv_id = slv_id or next_available_slv_id()
    if not SLV_ID_RE.match(slv_id):
        raise ValueError(f"invalid slv_id: {slv_id!r}")
    today = (now or _dt.date.today()).isoformat()
    scope = _infer_scope(fpl)
    # Title heuristic: strip leading "FPL-NNN：" prefix from fpl.title.
    base_title = re.sub(r"^FPL-\d+[：:]\s*", "", fpl.title).strip()
    name = base_title or f"從 {fpl.fpl_id} 衍生"
    purpose = fpl.summary or name
    # Derive qualifiers — if the FPL already listed them, keep verbatim; else
    # fall back to a single "需補齊" entry that forces human review.
    qualifiers = list(fpl.required_qualifiers) or [
        f"待 sa-analyst review：FPL {fpl.fpl_id} 未列 required_qualifier，請補齊"
    ]
    failures = [fpl.failure_example] if fpl.failure_example else []
    passes = [fpl.pass_example] if fpl.pass_example else []
    return SLVRuleCandidate(
        id=slv_id,
        name=name,
        source=f"{fpl.fpl_id} auto-generated {today}",
        trust_level="proposed",
        reviewed_by=None,
        reviewed_at=None,
        scope=scope,
        purpose=purpose,
        scan_targets=list(_DEFAULT_SCAN_TARGETS),
        required_qualifiers=qualifiers,
        failure_examples=failures,
        pass_examples=passes,
        severity="CRITICAL",
        blocks_scg=True,
        source_fpl=fpl.fpl_id,
        pattern_regex=fpl.regex_pattern,
    )


def write_rule_candidate(
    cand: SLVRuleCandidate,
    *,
    rules_dir: Optional[Path] = None,
    overwrite_proposed: bool = True,
) -> Path:
    """Persist candidate to rules/SLV-00N.yaml.

    Safety:
      - If the target file exists and is `verified`, raise
        RuleOverwriteProtected regardless of `overwrite_proposed`.
      - If it exists and is `proposed`, overwrite only when
        overwrite_proposed=True.
      - M4 QA Round-6 P0-3：整個 read-modify-write 以 `file_lock` 包住，
        與 hooks 寫 CONTEXT-LEDGER 走同一套 sentinel 互斥協定，避免
        並行 CLI 呼叫與 Skill 呼叫同時寫入互相覆蓋。
      - M4 QA Round-6 P0-4：`source` / `source_fpl` 為 FPL→SLV 審計鏈錨
        點；overwrite 時若新 candidate 的這兩欄與磁碟現況不同即 raise
        ImmutableFieldViolation，強制改走新 SLV id。
    """
    from .file_lock import file_lock  # local import：與 hooks 使用同源

    target_dir = rules_dir or RULES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{cand.id}.yaml"
    lock_path = target.with_suffix(target.suffix + ".lock")

    with file_lock(lock_path, timeout=5.0):
        if target.exists():
            try:
                existing = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                existing = {}
            existing_trust = str(existing.get("trust_level", "verified"))
            if existing_trust == "verified":
                raise RuleOverwriteProtected(
                    f"refuse to overwrite verified rule {target} — "
                    "bump SLV id or mark existing as deprecated first"
                )
            if existing_trust == "proposed" and not overwrite_proposed:
                raise RuleOverwriteProtected(
                    f"proposed rule {target} already exists and overwrite_proposed=False"
                )
            # P0-4: immutable audit fields — 不允許 overwrite 改寫 source_fpl / source。
            existing_src_fpl = existing.get("source_fpl")
            existing_src = existing.get("source")
            if existing_src_fpl is not None and existing_src_fpl != cand.source_fpl:
                raise ImmutableFieldViolation(
                    f"refuse to overwrite {target}: source_fpl is immutable "
                    f"(existing={existing_src_fpl!r}, new={cand.source_fpl!r}) "
                    "— allocate a new SLV id instead of remapping FPL source"
                )
            if existing_src is not None and existing_src != cand.source:
                raise ImmutableFieldViolation(
                    f"refuse to overwrite {target}: source is immutable "
                    f"(existing={existing_src!r}, new={cand.source!r}) "
                    "— source encodes the original auto-generation audit trail"
                )
        # Write via tmp + replace for atomicity.
        tmp = target.with_suffix(target.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cand.to_yaml_doc(), f, allow_unicode=True, sort_keys=False)
        import os
        os.replace(tmp, target)
    return target


def load_rule(path: Path) -> Dict[str, Any]:
    """Load and validate a SLV rule YAML file.

    M4 QA Round-6 強化：
      - P1-3：`trust_level: verified` 規則必須填 `reviewed_by` 與
        `reviewed_at`（非空字串）；否則 raise SchemaViolation。
      - P0-4：`source_fpl` / `source` 欄位若存在，型別必須是字串；
        `source_fpl` 額外要求符合 `FPL-NNN` 格式。
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: expected a mapping at top level")
    missing = [k for k in ("id", "name", "trust_level", "scope") if k not in doc]
    if missing:
        raise ValueError(f"{path}: missing required keys {missing}")
    if doc["trust_level"] not in VALID_TRUST_LEVELS:
        raise ValueError(
            f"{path}: invalid trust_level={doc['trust_level']!r} "
            f"(expected one of {sorted(VALID_TRUST_LEVELS)})"
        )
    # P1-3：verified 必帶 reviewer 審計欄位
    # reviewed_at 容許 PyYAML 自動 parse 出的 datetime.date / datetime.datetime
    # （YAML 1.1 把 `2026-04-24` 當成 date literal），同時仍接受字串形式。
    if doc["trust_level"] == "verified":
        reviewed_by = doc.get("reviewed_by")
        reviewed_at = doc.get("reviewed_at")
        if not (isinstance(reviewed_by, str) and reviewed_by.strip()):
            raise SchemaViolation(
                f"{path}: verified rule must set non-empty reviewed_by "
                f"(got {reviewed_by!r})"
            )
        reviewed_at_ok = (
            (isinstance(reviewed_at, str) and reviewed_at.strip())
            or isinstance(reviewed_at, (_dt.date, _dt.datetime))
        )
        if not reviewed_at_ok:
            raise SchemaViolation(
                f"{path}: verified rule must set non-empty reviewed_at "
                f"(got {reviewed_at!r})"
            )
    # P0-4：source_fpl / source 型別 + 格式檢查（若有填）
    source_fpl = doc.get("source_fpl")
    if source_fpl is not None:
        if not isinstance(source_fpl, str):
            raise SchemaViolation(
                f"{path}: source_fpl must be a string (got {type(source_fpl).__name__})"
            )
        if not FPL_ID_RE.match(source_fpl):
            raise SchemaViolation(
                f"{path}: source_fpl={source_fpl!r} does not match FPL-NNN format"
            )
    source = doc.get("source")
    if source is not None and not isinstance(source, str):
        raise SchemaViolation(
            f"{path}: source must be a string (got {type(source).__name__})"
        )
    return doc


def classify_result(rule: Dict[str, Any], fail: bool) -> str:
    """Classify a rule hit outcome as `blocking` / `advisory` / `pass`.

    M4 QA Round-6 P1-4：填補 SKILL.md §Trust Level 語意的執行層缺口。
    規則引擎（或人工調用 /spec-logical-validator）據此決定是否阻塞 SCG：

      * 未命中失敗 → "pass"
      * 命中失敗 + trust_level == "verified" → "blocking"（阻塞 SCG）
      * 命中失敗 + trust_level ∈ {"proposed","external"} → "advisory"
        （報告中標 🟡/🟣，不阻塞 SCG）

    Raises:
        SchemaViolation: 當規則 trust_level 不在 VALID_TRUST_LEVELS 內。
    """
    if not fail:
        return "pass"
    trust_level = rule.get("trust_level")
    if trust_level not in VALID_TRUST_LEVELS:
        raise SchemaViolation(
            f"rule {rule.get('id')!r}: invalid trust_level={trust_level!r} "
            f"(expected one of {sorted(VALID_TRUST_LEVELS)})"
        )
    if trust_level == "verified":
        return "blocking"
    # proposed / external → advisory
    return "advisory"


def iter_rule_files(rules_dir: Optional[Path] = None):
    target_dir = rules_dir or RULES_DIR
    if not target_dir.exists():
        return iter(())
    return sorted(target_dir.glob("SLV-*.yaml"))


# ---------- CLI ----------

def _cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="SLV rule generator (ACT-028)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_propose = sub.add_parser("propose", help="propose an SLV rule from an FPL entry")
    p_propose.add_argument("fpl_id")
    p_propose.add_argument("--slv-id", default=None, help="override auto-allocated SLV id")
    p_propose.add_argument("--dry-run", action="store_true", help="print YAML; don't write file")
    p_propose.add_argument(
        "--no-overwrite",
        action="store_true",
        help="fail if a proposed rule already exists at the target id",
    )

    sub.add_parser("list-fpl", help="list known FPL entries")
    sub.add_parser("list-rules", help="list loaded SLV rule files")

    p_validate = sub.add_parser("validate", help="validate all rule YAML under rules/")
    p_validate.add_argument("--rules-dir", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "propose":
        fpl = load_fpl_entry(args.fpl_id)
        cand = propose_slv_from_fpl(fpl, slv_id=args.slv_id)
        doc = cand.to_yaml_doc()
        if args.dry_run:
            yaml.safe_dump(doc, sys.stdout, allow_unicode=True, sort_keys=False)
            return 0
        path = write_rule_candidate(
            cand, overwrite_proposed=(not args.no_overwrite)
        )
        print(json.dumps({"wrote": str(path), "slv_id": cand.id, "trust_level": cand.trust_level}, ensure_ascii=False))
        return 0
    if args.cmd == "list-fpl":
        entries = sorted(FPL_DIR.glob("FPL-*.md"))
        for p in entries:
            print(p.name)
        return 0
    if args.cmd == "list-rules":
        for p in iter_rule_files():
            doc = load_rule(p)
            print(f"{doc['id']}\t{doc['trust_level']}\t{doc.get('scope', '?')}\t{doc['name']}")
        return 0
    if args.cmd == "validate":
        rules_dir = Path(args.rules_dir) if args.rules_dir else None
        errors: List[str] = []
        for p in iter_rule_files(rules_dir):
            try:
                load_rule(p)
            except ValueError as exc:
                errors.append(f"{p}: {exc}")
        if errors:
            for e in errors:
                print(e, file=sys.stderr)
            return 2
        print(json.dumps({"validated": True}, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
