"""Anonymizer — replace L1 (internal) tokens with placeholders.

ACT-030 (Phase F M2 D-30.7).

Spec: docs/06_quality/HUB-GOVERNANCE-SPEC.md §4.2 / 4.3
Rules: tools/fsm_runtime/anonymizer_rules.yaml

Behaviour:
  - Loads rules from anonymizer_rules.yaml.
  - For each L1 rule, replaces matches with `<CATEGORY_X>` placeholders;
    X is per-category alphabetical sequence (A, B, C, ...). Same matched
    string within one anonymize() call always maps to the same placeholder.
  - Tokens in `allow_list` are never replaced (case-insensitive match).
  - Per HUB-GOVERNANCE-SPEC §4.3 the *semantic skeleton* (regex pattern,
    qualifier fields, scope) is preserved; we only operate on raw text body.

Public API:
  load_rules(path: Path) -> AnonymizerConfig
  anonymize(text: str, *, config: AnonymizerConfig | None = None)
      -> AnonymizeResult(text=..., substitutions=[...])
"""
from __future__ import annotations

import dataclasses
import re
import string
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES_PATH = REPO_ROOT / "tools" / "fsm_runtime" / "anonymizer_rules.yaml"


@dataclasses.dataclass(frozen=True)
class L1Rule:
    rule_id: str
    category: str
    pattern: re.Pattern
    placeholder: str   # may contain `{N}` for per-category sequence
    description: str = ""


@dataclasses.dataclass(frozen=True)
class AnonymizerConfig:
    l1_rules: Tuple[L1Rule, ...]
    allow_list: Tuple[str, ...]    # canonical lower-case tokens never replaced
    rules_path: Path

    def is_allowed(self, token: str) -> bool:
        return token.lower() in self.allow_list


@dataclasses.dataclass
class Substitution:
    rule_id: str
    category: str
    original_redacted: str  # log only the redacted form, never raw (HUB-GOVERNANCE §5.1)
    placeholder: str
    count: int


@dataclasses.dataclass
class AnonymizeResult:
    text: str
    substitutions: List[Substitution]

    @property
    def changed(self) -> bool:
        return any(sub.count > 0 for sub in self.substitutions)


def _compile_pattern(pattern_str: str, case_insensitive: bool) -> re.Pattern:
    flags = re.IGNORECASE if case_insensitive else 0
    return re.compile(pattern_str, flags)


def load_rules(path: Optional[Path] = None) -> AnonymizerConfig:
    """Load L1 rules and allow-list from anonymizer_rules.yaml.

    L2 rules (PII / quarantine) are consumed by pii_scanner.py, not here.
    """
    rules_path = Path(path) if path else DEFAULT_RULES_PATH
    if not rules_path.exists():
        raise FileNotFoundError(f"anonymizer rules not found: {rules_path}")
    doc = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}

    l1_rules: List[L1Rule] = []
    for rule in doc.get("rules", []) or []:
        if rule.get("level") != "L1":
            continue
        pattern_str = rule.get("pattern") or ""
        if not pattern_str:
            # dynamic rules (e.g., empty-pattern deny-list) handled by pii_scanner
            continue
        l1_rules.append(L1Rule(
            rule_id=str(rule.get("id", "")),
            category=str(rule.get("category", "")),
            pattern=_compile_pattern(pattern_str, bool(rule.get("case_insensitive", False))),
            placeholder=str(rule.get("placeholder", f"<{rule.get('category', 'TOKEN').upper()}_{{N}}>")),
            description=str(rule.get("description", "")),
        ))

    allow_set: set[str] = set()
    for _, items in (doc.get("allow_list") or {}).items():
        for item in items or []:
            allow_set.add(str(item).lower())

    return AnonymizerConfig(
        l1_rules=tuple(l1_rules),
        allow_list=tuple(sorted(allow_set)),
        rules_path=rules_path,
    )


def _next_label(seq: int) -> str:
    """Map 0->A, 1->B, ..., 25->Z, 26->AA, 27->AB, ..."""
    if seq < 0:
        raise ValueError(f"seq must be non-negative: {seq}")
    letters = string.ascii_uppercase
    out = ""
    n = seq
    while True:
        out = letters[n % 26] + out
        n = n // 26 - 1
        if n < 0:
            break
    return out


def _redact_for_log(text: str) -> str:
    """Hash-style redaction so quarantine logs never carry raw PII."""
    if not text:
        return ""
    # First/last char + length only — enough for debugging without leaking content.
    if len(text) <= 2:
        return f"<len={len(text)}>"
    return f"{text[0]}…{text[-1]}<len={len(text)}>"


def anonymize(
    text: str,
    *,
    config: Optional[AnonymizerConfig] = None,
) -> AnonymizeResult:
    """Replace L1 patterns in `text` with placeholders.

    Behaviour notes:
      - Within one call, the same matched string maps to the same placeholder
        (per category counter). Across calls, counter resets — see
        HUB-GOVERNANCE-SPEC §behavior.cross_session_persist=false.
      - allow_list members are NEVER replaced (case-insensitive).
      - Rules apply in declaration order; earlier rules win on overlap.
    """
    if config is None:
        config = load_rules()

    if not text:
        return AnonymizeResult(text=text, substitutions=[])

    # category -> {original -> placeholder}
    category_seq: Dict[str, int] = {}
    seen: Dict[str, Dict[str, str]] = {}
    sub_log: Dict[Tuple[str, str], Substitution] = {}

    # Apply rules sequentially; capture matches and replace.
    out = text
    for rule in config.l1_rules:
        def _replace(match: re.Match, _rule=rule) -> str:
            raw = match.group(0)
            # Allow-list bypass — keep token as-is.
            if config.is_allowed(raw):
                return raw
            cat_map = seen.setdefault(_rule.category, {})
            if raw in cat_map:
                placeholder = cat_map[raw]
            else:
                seq = category_seq.get(_rule.category, 0)
                label = _next_label(seq)
                category_seq[_rule.category] = seq + 1
                placeholder = _rule.placeholder.replace("{N}", label)
                cat_map[raw] = placeholder
            key = (_rule.rule_id, raw)
            if key in sub_log:
                sub_log[key].count += 1
            else:
                sub_log[key] = Substitution(
                    rule_id=_rule.rule_id,
                    category=_rule.category,
                    original_redacted=_redact_for_log(raw),
                    placeholder=placeholder,
                    count=1,
                )
            return placeholder

        out = rule.pattern.sub(_replace, out)

    return AnonymizeResult(text=out, substitutions=list(sub_log.values()))


# CLI for quick smoke tests / pre-push manual check.
def _cli() -> int:
    import argparse
    import json
    import sys
    parser = argparse.ArgumentParser(description="Anonymize text per HUB-GOVERNANCE-SPEC §4.2")
    parser.add_argument("--input", "-i", help="input file (default: stdin)")
    parser.add_argument("--rules", help="path to anonymizer_rules.yaml")
    parser.add_argument("--report", action="store_true", help="emit substitution report on stderr")
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    cfg = load_rules(Path(args.rules)) if args.rules else load_rules()
    result = anonymize(text, config=cfg)
    sys.stdout.write(result.text)
    if args.report:
        report = {
            "rules_path": str(cfg.rules_path),
            "changed": result.changed,
            "substitution_count": sum(s.count for s in result.substitutions),
            "substitutions": [dataclasses.asdict(s) for s in result.substitutions],
        }
        sys.stderr.write(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys as _sys
    _sys.exit(_cli())
