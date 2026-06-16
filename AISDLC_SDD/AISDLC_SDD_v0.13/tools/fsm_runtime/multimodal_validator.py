"""Multimodal Spec Validator — unified entry for ACT-031 (Phase F M4 D-31.1).

Reads markdown spec(s), extracts `<!-- anchor:<modality>:<id> -->`, dispatches
each anchor to the appropriate adapter, and returns a `MultimodalReport`.

Wired into `spec-logical-validator` Skill (D-31.13). CI step uses this via
the CLI: `python -m tools.fsm_runtime.multimodal_validator <spec_paths...>`.

Public:
  validate_specs(spec_paths, *, project_root=None, backend=None)
      -> MultimodalReport

Anchor grammar: see docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .modality.llm_backend import (
    ModalityBackend,
    WidgetTree,
    get_backend,
)
from .modality import (
    ui_adapter,
    api_ui_adapter,
    db_schema_adapter,
    c4_adapter,
)
from .state_loader import REPO_ROOT


# Anchor: <!-- anchor:ui:LoginScreen --> or <!-- anchor:api:POST /auth/login -->
_ANCHOR_RE = re.compile(
    r"<!--\s*anchor:(?P<modality>ui|api|db|c4):(?P<id>[^\s][^\n]*?)\s*-->"
)


@dataclasses.dataclass
class AnchorRecord:
    spec_path: Path
    modality: str
    raw_id: str           # full string between modality: and -->
    line: int
    section_text: str     # surrounding paragraph (used as ac/srd context)


@dataclasses.dataclass
class AnchorOutcome:
    anchor: AnchorRecord
    consistent: bool
    detail: dict          # adapter-specific report serialised
    error: Optional[str] = None
    backend: str = ""


@dataclasses.dataclass
class MultimodalReport:
    spec_paths: List[Path]
    anchors: List[AnchorRecord]
    outcomes: List[AnchorOutcome]
    backend_name: str

    @property
    def consistent(self) -> bool:
        return all(o.consistent for o in self.outcomes)

    @property
    def issue_count(self) -> int:
        return sum(1 for o in self.outcomes if not o.consistent)

    def to_dict(self) -> dict:
        return {
            "spec_paths": [str(p) for p in self.spec_paths],
            "backend": self.backend_name,
            "anchor_count": len(self.anchors),
            "issue_count": self.issue_count,
            "consistent": self.consistent,
            "outcomes": [
                {
                    "spec_path": str(o.anchor.spec_path),
                    "modality": o.anchor.modality,
                    "anchor_id": o.anchor.raw_id,
                    "line": o.anchor.line,
                    "consistent": o.consistent,
                    "error": o.error,
                    "detail": o.detail,
                    "backend": o.backend,
                }
                for o in self.outcomes
            ],
        }


# ─────────────────────────────────────────────
# Anchor extraction
# ─────────────────────────────────────────────
def _extract_anchors(spec_path: Path) -> List[AnchorRecord]:
    text = spec_path.read_text(encoding="utf-8", errors="replace")
    out: List[AnchorRecord] = []
    lines = text.splitlines()
    line_offsets: List[int] = [0]
    for ln in lines:
        line_offsets.append(line_offsets[-1] + len(ln) + 1)

    for m in _ANCHOR_RE.finditer(text):
        # Locate line number for the anchor
        idx = m.start()
        lineno = next(
            (i for i, off in enumerate(line_offsets) if off > idx),
            len(line_offsets),
        )
        # Section text = paragraph containing the anchor (split on blank lines)
        section = _slice_paragraph(text, idx)
        out.append(AnchorRecord(
            spec_path=spec_path,
            modality=m.group("modality"),
            raw_id=m.group("id").strip(),
            line=max(lineno, 1),
            section_text=section,
        ))
    return out


def _slice_paragraph(text: str, idx: int) -> str:
    """Return the markdown paragraph that hosts the anchor at `idx`, with all
    HTML comments stripped.

    Behaviour:
      - When anchor sits inside a paragraph (no blank line before it), return
        the whole containing paragraph.
      - When anchor follows a blank line (typical: AC paragraph then blank
        then `<!-- anchor:* -->`), return the *previous non-empty* paragraph
        because that's the AC text the author intended to anchor.
    """
    before_text = text[:idx]
    after_text = text[idx:]

    # Walk backwards across blank lines until we hit a non-empty paragraph.
    paragraphs = [p for p in re.split(r"\n\s*\n", before_text) if p.strip()]
    head = paragraphs[-1] if paragraphs else ""

    # Tail = remainder of the same paragraph that started before idx (if any).
    tail = after_text.split("\n\n", 1)[0]

    raw = (head + " " + tail) if head and tail else (head or tail)
    no_comment = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    return no_comment.strip()


# ─────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────
def _dispatch_ui(
    record: AnchorRecord, *, backend: ModalityBackend, project_root: Path,
) -> AnchorOutcome:
    media_root = project_root / "docs" / "99_media"
    rep = ui_adapter.validate_anchor(
        ac_text=record.section_text,
        anchor_id=record.raw_id,
        backend=backend,
        media_root=media_root,
    )
    return AnchorOutcome(
        anchor=record,
        consistent=rep.consistent,
        detail={
            "target_path": str(rep.target_path) if rep.target_path else None,
            "missing_widgets": rep.missing_widgets,
            "extra_widgets": rep.extra_widgets,
            "confidence": rep.confidence,
        },
        error=rep.error,
        backend=rep.backend,
    )


def _dispatch_api(
    record: AnchorRecord, *, backend: ModalityBackend, project_root: Path,
    ui_widgets: Optional[WidgetTree],
) -> AnchorOutcome:
    api_root = project_root / "docs" / "02_architecture" / "api"
    # Parse "POST /auth/login" or "GET /users/{id}"
    parts = record.raw_id.split(None, 1)
    if len(parts) != 2:
        return AnchorOutcome(
            anchor=record,
            consistent=False,
            detail={"reason": f"unparseable api anchor id: {record.raw_id!r}"},
            error="invalid_anchor_format",
            backend=backend.name,
        )
    method, path = parts
    rep = api_ui_adapter.validate_anchor(
        method=method, path=path,
        ui_widgets=ui_widgets, api_root=api_root,
        ac_text=record.section_text,
    )
    return AnchorOutcome(
        anchor=record,
        consistent=rep.consistent,
        detail={
            "method": rep.method,
            "path": rep.path,
            "yaml_path": str(rep.yaml_path) if rep.yaml_path else None,
            "missing_request_fields": rep.missing_request_fields,
        },
        error=rep.error,
        backend=backend.name,
    )


def _dispatch_db(
    record: AnchorRecord, *, backend: ModalityBackend, project_root: Path,
) -> AnchorOutcome:
    db_root = project_root / "docs" / "07_design" / "db"
    rep = db_schema_adapter.validate_anchor(
        table_name=record.raw_id,
        frd_text=record.section_text,
        db_root=db_root,
    )
    return AnchorOutcome(
        anchor=record,
        consistent=rep.consistent,
        detail={
            "target_path": str(rep.target_path) if rep.target_path else None,
            "columns": rep.columns,
            "missing_columns": rep.missing_columns,
        },
        error=rep.error,
        backend=backend.name,
    )


def _dispatch_c4(
    record: AnchorRecord, *, backend: ModalityBackend, project_root: Path,
) -> AnchorOutcome:
    c4_root = project_root / "docs" / "02_architecture"
    rep = c4_adapter.validate_anchor(
        component=record.raw_id,
        srd_text=record.section_text,
        c4_root=c4_root,
    )
    return AnchorOutcome(
        anchor=record,
        consistent=rep.consistent,
        detail={
            "target_path": str(rep.target_path) if rep.target_path else None,
            "matched_in_srd": rep.matched_in_srd,
        },
        error=rep.error,
        backend=backend.name,
    )


# ─────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────
def validate_specs(
    spec_paths: Sequence[Path],
    *,
    project_root: Optional[Path] = None,
    backend: Optional[ModalityBackend] = None,
) -> MultimodalReport:
    bk = backend or get_backend()
    root = Path(project_root) if project_root else REPO_ROOT

    all_anchors: List[AnchorRecord] = []
    for path in spec_paths:
        p = Path(path)
        if not p.exists():
            continue
        all_anchors.extend(_extract_anchors(p))

    # Pre-extract UI WidgetTrees so api dispatch can pair them by spec section.
    # We index by spec_path → first ui anchor's WidgetTree (good enough for the
    # common pattern: one UI anchor per AC section drives any sibling api anchor).
    ui_cache: dict = {}
    for record in all_anchors:
        if record.modality != "ui":
            continue
        target = ui_adapter.resolve_ui_target(
            root / "docs" / "99_media", record.raw_id,
        )
        if target is None:
            continue
        try:
            ui_cache[(record.spec_path, record.section_text)] = bk.extract_widget_tree(target)
        except (FileNotFoundError, NotImplementedError):
            continue

    outcomes: List[AnchorOutcome] = []
    for record in all_anchors:
        if record.modality == "ui":
            outcomes.append(_dispatch_ui(record, backend=bk, project_root=root))
        elif record.modality == "api":
            ui_widgets = ui_cache.get((record.spec_path, record.section_text))
            outcomes.append(_dispatch_api(
                record, backend=bk, project_root=root,
                ui_widgets=ui_widgets,
            ))
        elif record.modality == "db":
            outcomes.append(_dispatch_db(record, backend=bk, project_root=root))
        elif record.modality == "c4":
            outcomes.append(_dispatch_c4(record, backend=bk, project_root=root))
        else:
            outcomes.append(AnchorOutcome(
                anchor=record,
                consistent=False,
                detail={"reason": f"unknown modality {record.modality!r}"},
                error="unknown_modality",
                backend=bk.name,
            ))

    return MultimodalReport(
        spec_paths=[Path(p) for p in spec_paths],
        anchors=all_anchors,
        outcomes=outcomes,
        backend_name=bk.name,
    )


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def _cli() -> int:
    parser = argparse.ArgumentParser(description="Multimodal Spec Validator (ACT-031)")
    parser.add_argument("specs", nargs="+", help="markdown spec files (FRD/SRD)")
    parser.add_argument("--project-root", help="repo root; defaults to AISDLC_SDD_v0.01/")
    parser.add_argument("--backend", help="session | claude-api | minimax")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when any anchor is inconsistent (advisory mode otherwise)")
    args = parser.parse_args()

    try:
        bk = get_backend(args.backend)
    except ValueError as exc:
        print(f"[multimodal] {exc}", file=sys.stderr)
        return 2

    report = validate_specs(
        [Path(s) for s in args.specs],
        project_root=Path(args.project_root) if args.project_root else None,
        backend=bk,
    )
    sys.stdout.write(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if args.strict and not report.consistent:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_cli())
