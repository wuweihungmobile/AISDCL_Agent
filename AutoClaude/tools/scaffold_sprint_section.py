#!/usr/bin/env python
"""scaffold_sprint_section — Sprint W0 第一步自動建立 sprint_history.md §1.N 骨架。

對應 ADR-SD08-001 v1.1 §9（W 期間骨架先行 SOP）。

使用：
  python tools/scaffold_sprint_section.py --sprint 10 --title "<主軸>"
  python tools/scaffold_sprint_section.py --sprint 10 --title "<主軸>" --dry-run

行為：
  - 解析 sprint_history.md 現有 §1.X 編號 → 自動取下一個 X
  - 在 §1.X SD_Improving_NN 不存在時，於 `## 2. 議題索引表` 前插入骨架段
  - 若已存在 → exit 1（拒絕覆寫）
  - --dry-run：印骨架不寫檔
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT.parent / "tools" / "lib"))
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)

SPRINT_HISTORY = PROJECT_ROOT / "docs" / "05_development" / "sprint_history.md"

SPRINT_H3_PATTERN = re.compile(r"^### 1\.(\d+) SD_Improving_(\d+)")
ISSUES_INDEX_H2 = "## 2. 議題索引表"


def build_skeleton(sprint_nn: str, section_x: int, title: str, today: str) -> str:
    """產生 §1.N SD_Improving_NN 完整骨架（W0~W6 + W3 audit 累積區）。"""
    return f"""### 1.{section_x} SD_Improving_{sprint_nn}（{title}）— 🟡 W0 啟動 {today}（W 期間骨架先行 SOP，依 ADR-SD08-001 v1.1 §9）

**主軸**：<填入 1-2 句主軸描述>。詳見 [SD_Improving_{sprint_nn}.md](../04_planning/SD_Improving_{sprint_nn}.md)（W0 撰寫中）。

> **§9 W 期間骨架先行 SOP**：本 §1.{section_x} 在 SD_{sprint_nn} W0 即建立，所有 W 期間 Round / audit 紀錄直接寫入本檔 §1.{section_x}.3（W3 累積區），**不再走 CLAUDE.md → G6 下沉路徑**；CLAUDE.md SD_{sprint_nn} H3 段永遠保持「摘要 + 連結」≤ 15 行。

#### 1.{section_x}.1 W0 主軸啟動

<W0 任務 / 觀察期 / 修復閉環紀錄>

#### 1.{section_x}.2 W1 主軸推進

<W1 主要交付>

#### 1.{section_x}.3 W3 zero-trust audit Round 累積區

> 本子段是 SD_{sprint_nn} W3 zero-trust audit 持續累積區；每輪新 Round 紀錄直接寫入此處，**不寫入 CLAUDE.md**。

<W3 Round N zero-trust audit 紀錄依序追加>

#### 1.{section_x}.4 W2~W6 預留骨架

- **W2**：<主題>
- **W4**：<主題>
- **W5**：<主題>
- **W6**：<Migration Guide vN.0 + AC Matrix + SD_{int(sprint_nn) + 1} 大綱>

#### 1.{section_x}.5 進度追蹤

| Wave | Gate | 狀態 | 通過日 | 測試基線 | 重點交付 |
|------|------|------|-------|---------|---------|
| W0 | G0 | 🟡 進行中 | — | — | <重點交付> |

#### 1.{section_x}.6 G0 啟動條件

<列出 G0 達標條件 + 預估達標日>

---

"""


def find_existing(content: str, sprint_nn: str) -> tuple[int | None, int]:
    """回傳 (existing_X, max_X)：若 SD_NN 已存在 → existing_X = 該編號；否則 None。
    max_X = 目前最大 §1.X。
    """
    existing_x: int | None = None
    max_x = 0
    for line in content.splitlines():
        m = SPRINT_H3_PATTERN.match(line)
        if not m:
            continue
        x = int(m.group(1))
        nn = m.group(2)
        max_x = max(max_x, x)
        if nn == sprint_nn:
            existing_x = x
    return existing_x, max_x


def insert_skeleton(content: str, skeleton: str) -> str:
    """在 `## 2. 議題索引表` 行之前插入骨架。"""
    idx = content.find(ISSUES_INDEX_H2)
    if idx == -1:
        # 兜底：append 至文件末尾
        return content.rstrip() + "\n\n" + skeleton
    # 找到 `## 2. 議題索引表` 前最近的 `---\n` 之前插入
    head = content[:idx]
    tail = content[idx:]
    # 在 head 末段插入骨架 + ---
    head_stripped = head.rstrip()
    return head_stripped + "\n\n" + skeleton + tail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sprint", required=True, help="Sprint 編號（如 10）")
    parser.add_argument("--title", required=True, help="Sprint 主軸（短句）")
    parser.add_argument("--dry-run", action="store_true", help="僅印骨架不寫檔")
    parser.add_argument(
        "--date", default=None, help="覆寫今日日期（測試用，格式 YYYY-MM-DD）"
    )
    args = parser.parse_args()

    sprint_nn = args.sprint.zfill(2)  # 09 / 10 / 11 ...
    title = args.title
    today = args.date or datetime.now(UTC).strftime("%Y-%m-%d")

    if not SPRINT_HISTORY.exists():
        print(
            f"[scaffold_sprint_section] 找不到 sprint_history.md: {SPRINT_HISTORY}",
            file=sys.stderr,
        )
        return 1

    content = SPRINT_HISTORY.read_text(encoding="utf-8")
    existing_x, max_x = find_existing(content, sprint_nn)
    if existing_x is not None:
        print(
            f"[scaffold_sprint_section] §1.{existing_x} SD_Improving_{sprint_nn} "
            f"已存在；拒絕覆寫。",
            file=sys.stderr,
        )
        return 1

    next_x = max_x + 1
    skeleton = build_skeleton(sprint_nn, next_x, title, today)

    if args.dry_run:
        print(skeleton)
        print(
            f"[scaffold_sprint_section] DRY-RUN: 將於 §1.{next_x} 插入 "
            f"SD_Improving_{sprint_nn} 骨架",
            file=sys.stderr,
        )
        return 0

    updated = insert_skeleton(content, skeleton)
    SPRINT_HISTORY.write_text(updated, encoding="utf-8")
    try:
        display_path = SPRINT_HISTORY.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        display_path = str(SPRINT_HISTORY)
    print(
        f"[scaffold_sprint_section] OK — §1.{next_x} SD_Improving_{sprint_nn} 骨架已寫入"
        f" {display_path}。\n"
        f"  下一步：依 docs/05_development/Sprint_Round_Recording_SOP.md §2.2 在 CLAUDE.md 加 H3。"
    )
    return 0


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
