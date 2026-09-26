#!/usr/bin/env python3
"""單一 hook 載具（方案 B／DEF-200-316）：POSIX 上把 Windows 形態路徑
（`.venv/Scripts/pythonw.exe`）做成指向根層 `.venv/bin/python` 的符號連結，
讓兩平台的 `.claude/settings.json` 共用同一條 `command` 宣告——見根 CLAUDE.md
〈hook 載具〉。Windows 上 no-op（原生已有 `pythonw.exe`，沒有半邊可建）。

Fail loud 優於代勞誤刪（同 `tools/lib/stray_venv.enforce()` 既有慣例）：連結
已存在且身分正確 ⇒ 靜默成功；不存在 ⇒ 建立並 emit 一行；存在但不是我們建的
那顆（非符號連結，或連到別處）⇒ **不覆寫**，emit 錯誤並回 `False`。
"""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

#: 兩個檔名同一顆 venv——與 `tools/lib/hook_wiring.WIN_CARRIER_REL`／
#: `POSIX_SYMLINK_TARGET_REL` 同一份知識的建立端（該檔是驗證端，字面須同步）。
_LINK_REL = Path(".venv/Scripts/pythonw.exe")
_TARGET_REL = Path("../bin/python")  # 相對於 .venv/Scripts/ 的相對路徑


def ensure(root: Path, is_windows: bool, emit: Callable[[str], None]) -> bool:
    """冪等建立方案 B 的符號連結。Windows 上 no-op（原生已有 `pythonw.exe`）。

    - 連結已存在且 `readlink` 正確 ⇒ 靜默 `True`（不呼叫 `emit`）。
    - 連結不存在 ⇒ 建立目錄＋建立連結，`emit` 一行說明，回 `True`。
    - 該路徑存在但**不是**符號連結，或是符號連結但指到別處 ⇒ **不覆寫**，
      `emit` 錯誤，回 `False`。
    - 連結目標（`.venv/bin/python`）根本不存在（.venv 尚未建立或不完整）
      ⇒ **不建 dangling symlink**，`emit` 錯誤（含目標路徑＋修法），回 `False`。
    """
    if is_windows:
        return True
    link = root / _LINK_REL
    if link.is_symlink():
        if Path(os.readlink(link)) == _TARGET_REL:
            return True
        emit(f"❌ {link} 是符號連結但指向 {os.readlink(link)}（預期 {_TARGET_REL}）"
             "— 不覆寫，請手動刪除後重跑 dev_start")
        return False
    if link.exists():
        emit(f"❌ {link} 已存在但不是符號連結（可能是舊版殘留）"
             "— 不覆寫，請手動刪除後重跑 dev_start")
        return False
    # 純字面正規化（不觸碰檔案系統），故不要求 link.parent（.venv/Scripts/）
    # 已存在也能正確算出目標的絕對路徑。
    target_abs = Path(os.path.normpath(link.parent / _TARGET_REL))
    if not target_abs.exists():
        emit(f"❌ hook 載具目標不存在：{target_abs}（.venv 尚未建立或不完整）"
             "— 不建立連結，請先跑 dev_start 完成 bootstrap 後重試")
        return False
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(_TARGET_REL)
    except OSError as e:
        emit(f"❌ 建立 hook 載具符號連結失敗（{e}）— {link} → {_TARGET_REL}")
        return False
    emit(f"    已建立 hook 載具符號連結：{link} → {_TARGET_REL}")
    return True
