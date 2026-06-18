"""UI/Mockup adapter — verify UI artifact aligns with FRD AC.

ACT-031 (Phase F M3 D-31.2). Rule: SLV-008 (D-31.9).

Flow:
  1. Read FRD markdown; locate `<!-- anchor:ui:<id> -->`
  2. Resolve target: docs/99_media/ui/<kebab(id)>.{html,md,png,...}
  3. Backend.extract_widget_tree(target) → WidgetTree
  4. Backend.compare_widgets_to_ac(widgets, ac_text) → ComparisonResult
  5. Emit UIConsistencyReport per anchor.

Public:
  resolve_ui_target(media_root, anchor_id) -> Path | None
  validate_anchor(frd_path, ac_text, anchor_id, *, backend, media_root)
      -> UIConsistencyReport
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import List, Optional

from .llm_backend import (
    ModalityBackend,
    WidgetTree,
    ComparisonResult,
    get_backend,
)


# Recognised file extensions for UI artifacts (priority order).
_UI_EXTENSIONS = (".html", ".htm", ".md", ".svg", ".png", ".jpg", ".jpeg", ".gif")


@dataclasses.dataclass
class UIConsistencyReport:
    anchor_id: str
    target_path: Optional[Path]
    consistent: bool
    missing_widgets: List[str] = dataclasses.field(default_factory=list)
    extra_widgets: List[str] = dataclasses.field(default_factory=list)
    error: Optional[str] = None
    backend: str = ""
    confidence: float = 1.0

    @property
    def has_target(self) -> bool:
        return self.target_path is not None and self.target_path.exists()


def _kebab(name: str) -> str:
    """`LoginScreen` → `login-screen`; `Order_Flow` → `order-flow`."""
    out = re.sub(r"(?<!^)(?=[A-Z])", "-", name)
    out = re.sub(r"[\s_]+", "-", out)
    return out.lower().strip("-")


def resolve_ui_target(media_root: Path, anchor_id: str) -> Optional[Path]:
    """Look for `<media_root>/ui/<kebab(anchor_id)>.<ext>` in priority order."""
    base = Path(media_root) / "ui"
    stem = _kebab(anchor_id)
    if not base.exists():
        return None
    for ext in _UI_EXTENSIONS:
        candidate = base / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    # Loose fallback — allow already-kebab id with same letters
    for child in base.iterdir():
        if child.is_file() and child.stem.lower() == stem and child.suffix.lower() in _UI_EXTENSIONS:
            return child
    return None


def validate_anchor(
    *,
    ac_text: str,
    anchor_id: str,
    backend: Optional[ModalityBackend] = None,
    media_root: Path,
) -> UIConsistencyReport:
    """Validate one `<!-- anchor:ui:<id> -->` against an AC sentence."""
    bk = backend or get_backend()
    target = resolve_ui_target(media_root, anchor_id)
    if target is None:
        return UIConsistencyReport(
            anchor_id=anchor_id,
            target_path=None,
            consistent=False,
            error="missing_anchor_target",
            backend=getattr(bk, "name", "unknown"),
        )
    try:
        widgets: WidgetTree = bk.extract_widget_tree(target)
    except FileNotFoundError as exc:
        return UIConsistencyReport(
            anchor_id=anchor_id, target_path=target,
            consistent=False, error=str(exc),
            backend=getattr(bk, "name", "unknown"),
        )
    except NotImplementedError as exc:
        return UIConsistencyReport(
            anchor_id=anchor_id, target_path=target,
            consistent=False,
            error=f"backend_not_implemented: {exc}",
            backend=getattr(bk, "name", "unknown"),
        )

    cmp_result: ComparisonResult = bk.compare_widgets_to_ac(widgets, ac_text)
    return UIConsistencyReport(
        anchor_id=anchor_id,
        target_path=target,
        consistent=cmp_result.consistent,
        missing_widgets=list(cmp_result.missing),
        extra_widgets=list(cmp_result.extra),
        backend=cmp_result.backend_name or getattr(bk, "name", "unknown"),
        confidence=cmp_result.confidence,
    )
