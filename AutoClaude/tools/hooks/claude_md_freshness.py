#!/usr/bin/env python
"""Stop 事件 — 檢查 CLAUDE.md 是否新鮮（snapshot 同步 + 行數 ≤ 400）。

對應 ADR-SD08-001。

退出碼：
  0  全 OK，或 Snapshot 漂移（提醒走 stdout 單一 JSON `additionalContext`，不佔結束碼；
     DEF-200-447：CC 只認 0／2，exit 1 會被顯示成 hook error）
  2  CLAUDE.md > 400 行（阻斷）

Stop+additionalContext 會讓模型多跑一回合（模型可據以執行 snapshot_sync），故夾在
`stop_hook_active` 上：為真時只寫 stderr（debug log）、不發射（同 check_claim_provenance）。

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
from platform_utils import emit_to_model, read_hook_payload  # noqa: E402
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)

CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
SNAPSHOT_TOOL = PROJECT_ROOT / "tools" / "snapshot_sync.py"
MAX_LINES = 400  # ADR-SD08-001 §2.1
_ADVISORIES: list[str] = []  # 提醒型（severity 1）訊息；main() 送出，提醒不是結束碼


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
        msg = (
            "[claude_md_freshness] WARN: Architecture Snapshot 漂移；"
            "請執行 `python tools/snapshot_sync.py` 重新生成。\n"
            f"  snapshot_sync 輸出: {snippet.strip()[:300]}"
        )
        print(msg, file=sys.stderr)  # exit 0 下只進 debug log
        _ADVISORIES.append(msg)
        return 1  # severity（helper 內部值），main() 不把它當結束碼
    return 0


def main() -> int:
    payload = read_hook_payload()
    if check_line_count() == 2:
        return 2
    check_snapshot_drift()
    if _ADVISORIES and not payload.get("stop_hook_active"):
        # 事件名取 payload 原值（約束①）；stop_hook_active 為真＝這一回合是 Stop hook 造成的
        # 續跑，再發射會讓模型再多跑一回合、結束又觸發 Stop（自燒額度迴圈），所以夾住。
        event = str(payload.get("hook_event_name") or "Stop")
        emit_to_model(event, "\n".join(_ADVISORIES))
    return 0


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
