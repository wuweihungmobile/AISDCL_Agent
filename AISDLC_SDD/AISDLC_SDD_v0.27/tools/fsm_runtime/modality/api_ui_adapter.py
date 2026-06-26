"""OpenAPI ↔ UI adapter — verify each `<!-- anchor:api:<METHOD> <PATH> -->`
points to a real OpenAPI endpoint AND that the UI form referenced from the
same AC segment carries the request body fields.

ACT-031 (Phase F M3 D-31.3). Rule: SLV-009 (D-31.10).

Public:
  resolve_api_target(api_root, method, path)
      -> (yaml_path, operation_object) | (None, None)
  validate_anchor(*, ac_text, method, path, ui_widgets, api_root)
      -> APIConsistencyReport
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

from .llm_backend import WidgetTree


@dataclasses.dataclass
class APIConsistencyReport:
    method: str
    path: str
    yaml_path: Optional[Path]
    consistent: bool
    missing_request_fields: List[str] = dataclasses.field(default_factory=list)
    error: Optional[str] = None


def _load_openapi_files(api_root: Path) -> List[Tuple[Path, dict]]:
    out: List[Tuple[Path, dict]] = []
    if not api_root.exists():
        return out
    for p in api_root.rglob("*.yaml"):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict) and "paths" in doc:
            out.append((p, doc))
    return out


def resolve_api_target(
    api_root: Path,
    method: str,
    path: str,
) -> Tuple[Optional[Path], Optional[dict]]:
    """Find the operation object for `<METHOD> <PATH>` across all OpenAPI files."""
    method_lower = method.strip().lower()
    target_path = path.strip()
    for yaml_path, doc in _load_openapi_files(Path(api_root)):
        paths = (doc.get("paths") or {})
        op = paths.get(target_path)
        if not isinstance(op, dict):
            continue
        operation = op.get(method_lower)
        if isinstance(operation, dict):
            return yaml_path, operation
    return None, None


def _request_body_fields(operation: dict) -> List[str]:
    """Pull required field names from the JSON request body schema."""
    rb = operation.get("requestBody") or {}
    content = (rb.get("content") or {})
    # Prefer application/json; fall back to first available
    schema_holder = content.get("application/json") or next(iter(content.values()), {})
    schema = (schema_holder.get("schema") or {})
    properties = list((schema.get("properties") or {}).keys())
    required = list(schema.get("required") or [])
    # Prefer required when declared, else properties
    return required or properties


def validate_anchor(
    *,
    method: str,
    path: str,
    ui_widgets: Optional[WidgetTree] = None,
    api_root: Path,
    ac_text: str = "",
) -> APIConsistencyReport:
    """Validate `<!-- anchor:api:<METHOD> <PATH> -->`.

    Two checks:
      1. Endpoint exists in OpenAPI files under api_root → otherwise
         missing_anchor_target.
      2. If a UI WidgetTree is supplied (typically the same screen referenced
         by an `anchor:ui` in the same AC), every required request-body field
         must have a matching `input(name=<field>)` widget — otherwise
         emit `missing_request_fields`.
    """
    yaml_path, operation = resolve_api_target(api_root, method, path)
    if operation is None:
        return APIConsistencyReport(
            method=method.upper(),
            path=path,
            yaml_path=None,
            consistent=False,
            error="missing_anchor_target",
        )
    fields = _request_body_fields(operation)
    missing: List[str] = []
    if ui_widgets is not None:
        widget_names_lower = {w.name.strip().lower() for w in ui_widgets.widgets}
        for f in fields:
            if not any(f.lower() in n for n in widget_names_lower):
                missing.append(f)
    return APIConsistencyReport(
        method=method.upper(),
        path=path,
        yaml_path=yaml_path,
        consistent=not missing,
        missing_request_fields=missing,
    )
