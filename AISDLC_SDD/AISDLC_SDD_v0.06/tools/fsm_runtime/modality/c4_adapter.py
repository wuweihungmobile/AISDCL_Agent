"""C4 Diagram adapter — verify `<!-- anchor:c4:<component> -->` is defined in
a Mermaid / PlantUML C4 diagram and the SRD references the same module.

ACT-031 (Phase F M3 D-31.5). Rule: SLV-011 (D-31.12).

Supports component declarations in:
  Mermaid:   `Component(<id>, "<label>", "<tech>", "<desc>")`
             also accepts `flowchart` style: `<id>[<label>]`
  PlantUML:  `Component(<id>, "<label>", "<tech>")` (C4 macro)
             classic: `[<label>] as <id>`

Public:
  collect_components(c4_root) -> {component_name: source_path}
  validate_anchor(*, component, srd_text, c4_root) -> C4ConsistencyReport
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Dict, List, Optional


@dataclasses.dataclass
class C4ConsistencyReport:
    component: str
    target_path: Optional[Path]
    consistent: bool
    error: Optional[str] = None
    matched_in_srd: bool = False


# Match Component(id, "label", ...) OR Component(id, label, ...)
_C4_COMPONENT_RE = re.compile(
    r'Component(?:_\w+)?\s*\(\s*([A-Za-z_][\w]*)\s*,\s*["\']?([^"\',)]+?)["\']?\s*[,)]',
    re.IGNORECASE,
)
# Mermaid flowchart node: id["Label"] or id[Label]
_MERMAID_NODE_RE = re.compile(
    r'\b([A-Za-z_]\w*)\s*\[\s*["\']?([^"\'\]]+)["\']?\s*\]'
)
# PlantUML classic alias: [Label] as Id
_PLANTUML_ALIAS_RE = re.compile(
    r'\[\s*([^\]]+?)\s*\]\s+as\s+(\w+)',
    re.IGNORECASE,
)


def _extract_components(text: str) -> List[str]:
    names: List[str] = []
    for m in _C4_COMPONENT_RE.finditer(text):
        names.append(m.group(1))
        names.append(m.group(2))
    for m in _MERMAID_NODE_RE.finditer(text):
        # Skip diagram syntax keywords — common false positives.
        if m.group(1).lower() in {"graph", "flowchart", "subgraph", "end", "classdef", "click", "linkstyle"}:
            continue
        names.append(m.group(1))
        names.append(m.group(2))
    for m in _PLANTUML_ALIAS_RE.finditer(text):
        names.append(m.group(2))
        names.append(m.group(1))
    return [n.strip() for n in names if n and n.strip()]


def collect_components(c4_root: Path) -> Dict[str, Path]:
    """Walk c4_root, return {normalized_lower_name: first_source_path}."""
    base = Path(c4_root)
    out: Dict[str, Path] = {}
    if not base.exists():
        return out
    candidate_globs = ("*.md", "*.mmd", "*.puml", "*.plantuml")
    for glob in candidate_globs:
        for p in base.rglob(glob):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for name in _extract_components(text):
                key = name.strip().lower()
                if key not in out:
                    out[key] = p
    return out


def validate_anchor(
    *,
    component: str,
    srd_text: str,
    c4_root: Path,
) -> C4ConsistencyReport:
    components = collect_components(c4_root)
    key = component.strip().lower()
    target = components.get(key)
    if target is None:
        return C4ConsistencyReport(
            component=component, target_path=None,
            consistent=False, error="orphan_component",
        )
    # SRD must mention the component name (case-insensitive substring) so the
    # diagram and prose stay paired.
    matched = bool(re.search(re.escape(component), srd_text, re.IGNORECASE)) if srd_text else False
    return C4ConsistencyReport(
        component=component,
        target_path=target,
        consistent=matched,
        matched_in_srd=matched,
        error=None if matched else "srd_missing_module_reference",
    )
