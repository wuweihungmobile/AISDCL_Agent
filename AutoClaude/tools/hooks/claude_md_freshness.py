#!/usr/bin/env python
"""Stop 事件 — 檢查 CLAUDE.md 是否新鮮（snapshot 同步 + 行數 ≤ 400）。

對應 ADR-SD08-001。

退出碼：
  0  全 OK
  1  Snapshot 漂移（warn，不阻斷下一輪 Stop）
  2  CLAUDE.md > 400 行（阻斷）

fail-open：
  - tools/snapshot_sync.py 不存在 → exit 0
  - CLAUDE.md 不存在 → exit 0
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT.parent / "tools" / "lib"))
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)

CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
SNAPSHOT_TOOL = PROJECT_ROOT / "tools" / "snapshot_sync.py"
MAX_LINES = 400  # ADR-SD08-001 §2.1


def count_raw_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with p.open(encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def check_line_count() -> int:
    if not CLAUDE_MD.exists():
        return 0  # fail-open
    actual = count_raw_lines(CLAUDE_MD)
    if actual > MAX_LINES:
        print(
            f"[claude_md_freshness] BLOCK: CLAUDE.md 行數 {actual} > 上限 {MAX_LINES}"
            f"（ADR-SD08-001 §2.1）。請精簡。",
            file=sys.stderr,
        )
        return 2
    return 0


def check_snapshot_drift() -> int:
    if not SNAPSHOT_TOOL.exists():
        return 0  # fail-open
    try:
        result = subprocess.run(
            [sys.executable, str(SNAPSHOT_TOOL), "--check"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover
        print(f"[claude_md_freshness] 跳過 snapshot 檢查：{exc}", file=sys.stderr)
        return 0
    if result.returncode != 0:
        snippet = (result.stdout or "") + (result.stderr or "")
        print(
            "[claude_md_freshness] WARN: Architecture Snapshot 漂移；"
            "請執行 `python tools/snapshot_sync.py` 重新生成。\n"
            f"  snapshot_sync 輸出: {snippet.strip()[:300]}",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> int:
    rc_line = check_line_count()
    if rc_line == 2:
        return 2
    rc_snap = check_snapshot_drift()
    return max(rc_line, rc_snap)


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
