"""DB Schema adapter — verify `<!-- anchor:db:<table> -->` aligns with FRD data needs.

ACT-031 (Phase F M3 D-31.4). Rule: SLV-010 (D-31.11).

Supports two schema formats under `docs/07_design/db/`:
  schema.sql — `CREATE TABLE <name> (col1 TYPE, col2 TYPE, ...);`
  *.yaml     — `<table>: { columns: [name, ...] }`  or  `tables: { <name>: ... }`

Public:
  resolve_db_target(db_root, table_name) -> (path, columns) | (None, [])
  validate_anchor(*, table_name, frd_text, db_root) -> DBConsistencyReport
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc


@dataclasses.dataclass
class DBConsistencyReport:
    table_name: str
    target_path: Optional[Path]
    columns: List[str]
    consistent: bool
    missing_columns: List[str] = dataclasses.field(default_factory=list)
    error: Optional[str] = None


_SQL_CREATE_TABLE_RE = re.compile(
    r'CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+[`"\']?(\w+)[`"\']?\s*\(([^;]+?)\);',
    re.IGNORECASE | re.DOTALL,
)


def _parse_sql(text: str) -> dict:
    """{table_name: [column_name, ...]}"""
    out: dict = {}
    for m in _SQL_CREATE_TABLE_RE.finditer(text):
        name = m.group(1)
        body = m.group(2)
        cols: List[str] = []
        for line in body.splitlines():
            stripped = line.strip().rstrip(",")
            if not stripped or stripped.upper().startswith(("PRIMARY KEY", "FOREIGN KEY", "CONSTRAINT", "UNIQUE", "INDEX", "KEY ", "--")):
                continue
            col_match = re.match(r'[`"\']?(\w+)[`"\']?\s+\w+', stripped)
            if col_match:
                cols.append(col_match.group(1))
        out[name] = cols
    return out


def _parse_yaml_schema(doc: dict) -> dict:
    """Accept either top-level `tables: {users: {columns: [...]}}` or
    flat `users: {columns: [...]}` form."""
    out: dict = {}
    if not isinstance(doc, dict):
        return out
    tables = doc.get("tables") if isinstance(doc.get("tables"), dict) else doc
    for name, spec in tables.items():
        if not isinstance(spec, dict):
            continue
        cols = spec.get("columns") or []
        if isinstance(cols, list):
            out[str(name)] = [str(c) for c in cols]
        elif isinstance(cols, dict):
            out[str(name)] = list(cols.keys())
    return out


def resolve_db_target(
    db_root: Path,
    table_name: str,
) -> Tuple[Optional[Path], List[str]]:
    """Search SQL + YAML schema files; return first match's columns."""
    base = Path(db_root)
    if not base.exists():
        return None, []

    # 1) SQL files
    for p in base.rglob("*.sql"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tables = _parse_sql(text)
        if table_name in tables:
            return p, tables[table_name]

    # 2) YAML files
    for p in base.rglob("*.yaml"):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError):
            continue
        tables = _parse_yaml_schema(doc)
        if table_name in tables:
            return p, tables[table_name]
    return None, []


def _required_fields_from_frd(frd_text: str) -> List[str]:
    """Heuristic: pick out lower-case alpha tokens after Chinese/English
    label words that hint at fields (e.g., '欄位:', 'fields:', 'column:').

    Falls back to listing inline-code identifiers like `email`, `created_at`.
    """
    if not frd_text:
        return []
    fields = set()
    # Inline backtick identifiers — most reliable signal for field names.
    for m in re.finditer(r"`([a-z_][a-z0-9_]+)`", frd_text):
        fields.add(m.group(1))
    return sorted(fields)


def validate_anchor(
    *,
    table_name: str,
    frd_text: str,
    db_root: Path,
) -> DBConsistencyReport:
    target, columns = resolve_db_target(db_root, table_name)
    if target is None:
        return DBConsistencyReport(
            table_name=table_name, target_path=None, columns=[],
            consistent=False, error="missing_anchor_target",
        )
    expected = _required_fields_from_frd(frd_text)
    if not expected:
        # No declared expectations → only verify table exists.
        return DBConsistencyReport(
            table_name=table_name, target_path=target, columns=columns,
            consistent=True,
        )
    columns_lower = {c.lower() for c in columns}
    missing = [f for f in expected if f.lower() not in columns_lower]
    return DBConsistencyReport(
        table_name=table_name,
        target_path=target,
        columns=columns,
        consistent=not missing,
        missing_columns=missing,
        error=None if not missing else "schema_mismatch",
    )
