"""Media Store size lint — enforce CLAUDE.md Rule 9.13.5 / OPEN-F.4.

ACT-031 (Phase F M3+M4) declared `docs/99_media/` as the unified store for
non-textual artefacts (UI mockups, ER diagrams, C4 diagrams, flows). The
governing invariants:

  - WARN if any single file ≥ 300 KB (300 * 1024 bytes)
  - FAIL if any single file ≥ 500 KB (500 * 1024 bytes) — hard upper bound

This module is the runtime gate that prevents accidental Git LFS bloat from
sneaking in, paired with the `Multimodal SpecTrace` CI step in
`cicd/SDD_CICD_BASE_LAYER.md`.

Public API (importable for tests):
  scan_media(root: Path) -> ScanReport
    └ returns { warnings: [...], failures: [...], scanned_files: int }

CLI (intended for CI):
  python -m tools.fsm_runtime.media_size_check                      # warn-only
  python -m tools.fsm_runtime.media_size_check --strict             # fail PR if any failure
  python -m tools.fsm_runtime.media_size_check --root <path>        # custom root
  python -m tools.fsm_runtime.media_size_check --json               # machine-readable

Exit codes:
  0 — no failures (warnings allowed in non-strict mode; in strict mode also no warnings)
  1 — at least one file ≥ 500 KB (always fails)
  2 — invocation error (root missing, etc.)
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import List

WARN_BYTES = 300 * 1024   # 300 KB
HARD_BYTES = 500 * 1024   # 500 KB
DEFAULT_MEDIA_ROOT_REL = "docs/99_media"


@dataclasses.dataclass(frozen=True)
class MediaSizeHit:
    path: str
    size_bytes: int
    severity: str   # "warn" or "fail"


@dataclasses.dataclass
class ScanReport:
    scanned_files: int
    warnings: List[MediaSizeHit]
    failures: List[MediaSizeHit]

    @property
    def has_failures(self) -> bool:
        return bool(self.failures)

    def to_dict(self) -> dict:
        return {
            "scanned_files": self.scanned_files,
            "warnings": [dataclasses.asdict(w) for w in self.warnings],
            "failures": [dataclasses.asdict(f) for f in self.failures],
        }


def scan_media(root: Path) -> ScanReport:
    """Walk `root` recursively and classify every file by size.

    Hidden files (`.gitkeep`, `.DS_Store`) and `README.md` files are skipped —
    those are governance artefacts, not media.
    """
    warnings: List[MediaSizeHit] = []
    failures: List[MediaSizeHit] = []
    scanned = 0
    if not root.exists():
        return ScanReport(scanned_files=0, warnings=warnings, failures=failures)

    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        name = p.name
        if name.startswith(".") or name.lower() == "readme.md":
            continue
        size = p.stat().st_size
        scanned += 1
        rel = str(p.relative_to(root)).replace("\\", "/")
        if size >= HARD_BYTES:
            failures.append(MediaSizeHit(path=rel, size_bytes=size, severity="fail"))
        elif size >= WARN_BYTES:
            warnings.append(MediaSizeHit(path=rel, size_bytes=size, severity="warn"))

    return ScanReport(scanned_files=scanned, warnings=warnings, failures=failures)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="media_size_check")
    parser.add_argument(
        "--root",
        default=None,
        help="media store root (default: <repo>/docs/99_media)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero on warnings as well (CI strict mode)",
    )
    parser.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        help="emit machine-readable JSON to stdout",
    )
    args = parser.parse_args(argv)

    if args.root:
        root = Path(args.root).resolve()
    else:
        # Repo-relative default: walk up to find AISDLC_SDD_v0.01/.
        from .state_loader import REPO_ROOT  # type: ignore
        root = REPO_ROOT / DEFAULT_MEDIA_ROOT_REL

    if not root.exists():
        print(f"[media-size] root does not exist: {root}", file=sys.stderr)
        return 2

    report = scan_media(root)

    if args.emit_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"[media-size] scanned {report.scanned_files} files under {root}")
        for w in report.warnings:
            print(f"  WARN  {w.size_bytes:>8} B  {w.path}  (≥ {WARN_BYTES} B)")
        for f in report.failures:
            print(f"  FAIL  {f.size_bytes:>8} B  {f.path}  (≥ {HARD_BYTES} B)", file=sys.stderr)

    if report.has_failures:
        return 1
    if args.strict and report.warnings:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
