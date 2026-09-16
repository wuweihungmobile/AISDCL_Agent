#!/usr/bin/env python3
"""單一 .venv「身分」判準（DEF-200-301；純函式、不碰磁碟）。

WHY 這支非有不可（與既有 `hook_wiring.carrier_liveness_problems` 的職責分工）：
`carrier_liveness_problems` 只問「宣告的載具展開後**存不存在**」——若某台機器上
真的在子專案目錄底下手動 `python -m venv` 建了一顆 `.venv`（單一 .venv 設計下
不該存在，但磁碟上確實存在），existence 判準會轉綠，因為那個路徑**存在**。
但那仍是錯的第二顆 venv：hook 載具應恆指向 repo 唯一的根層 `.venv`，不是「隨便
一顆存在的 venv」。本模組補的是這一格——**身分**（是不是那唯一一顆），不是
**存在性**（見 F1 立案筆記；DEF-200-294 的原始事故正是「AutoClaude 子專案底下
長出第二顆 venv、hook 候選鏈把它撿去用」）。2026-09-15 起 POSIX 載具也改釘根層
`.venv`（掌舵者裁決，見 `tools/lib/hook_wiring.POSIX_CARRIER_REL`），身分鎖同步
擴到 POSIX 半邊：判準對稱、訊息對稱。

刻意只依賴 stdlib＋`hook_wiring` 既有公開純函式（`expand_tokens`／
`declared_win_carriers`／`win_carrier_kind`），不碰磁碟——合成 `settings` dict
即可驗紅，不需要真檔案（比照 `hook_wiring.hook_form_problems` 的既有風格）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hook_wiring  # noqa: E402


def single_venv_identity_problems(
    settings: dict, project_dir: str, repo_root: str
) -> list[str]:
    """宣告的 Windows venv 載具與 POSIX 載具，用**這份 settings 自己的專案根**展開＋
    normpath 後，必須分別等於 `<repo_root>/.venv/Scripts/pythonw.exe` 與
    `<repo_root>/.venv/bin/python`——同一顆 repo 唯一 venv 的兩個平台半邊。

    Windows 只判 `win_carrier_kind() == "venv"` 的載具；PATH 版（`pythonw.exe` 字面）
    的實況取決於 session 的 PATH，沒有固定身分可比，射程外（同
    `hook_wiring.carrier_liveness_problems` 既有的劃界）。POSIX 側判
    `declared_posix_carriers()` 的每一筆——該函式本身已只認 `is_exec_form` ＋
    `is_command_hook` 的條目，沒有 PATH 版分歧，不需要額外過濾。
    """
    canonical_win = os.path.normcase(
        os.path.normpath(os.path.join(repo_root, hook_wiring.WIN_CARRIER_REL))
    )
    canonical_posix = os.path.normcase(
        os.path.normpath(os.path.join(repo_root, hook_wiring.POSIX_CARRIER_REL))
    )
    problems: list[str] = []
    for carrier in sorted(hook_wiring.declared_win_carriers(settings)):
        if hook_wiring.win_carrier_kind(carrier) != "venv":
            continue
        resolved = os.path.normcase(
            os.path.normpath(hook_wiring.expand_tokens([carrier], project_dir)[0])
        )
        if resolved != canonical_win:
            problems.append(
                f"宣告的 Windows venv 載具 {carrier!r} 用本份 settings 的專案根展開＋"
                f"normpath 後為 {resolved}，非 repo 唯一的根層 venv {canonical_win}——"
                "單一 .venv 設計下這是第二顆 venv（或指向不存在的分身）"
            )
    for carrier in sorted(hook_wiring.declared_posix_carriers(settings)):
        resolved = os.path.normcase(
            os.path.normpath(hook_wiring.expand_tokens([carrier], project_dir)[0])
        )
        if resolved != canonical_posix:
            problems.append(
                f"宣告的 POSIX venv 載具 {carrier!r} 用本份 settings 的專案根展開＋"
                f"normpath 後為 {resolved}，非 repo 唯一的根層 venv {canonical_posix}——"
                "單一 .venv 設計下這是第二顆 venv（或指向不存在的分身）"
            )
    return problems
