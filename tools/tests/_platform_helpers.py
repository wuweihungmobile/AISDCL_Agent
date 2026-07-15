#!/usr/bin/env python3
"""tools/tests 共用的跨平台測試 fixture 輔助函式。

四方複審 S21（architecture-review-own-finding）落地：F2（_copy_functional_interpreter）
與 F3（symlink 建立失敗 → skipTest）都是同一類「測試 fixture 對開發者本機環境有隱性
假設」的問題，且都只有在真的於目標作業系統上跑一次才會顯形（見
docs/06_quality/AutoSDD_Defect_Log.md DEF-101-064／DEF-101-069）。集中在本檔，供
tools/tests/ 內未來新測試直接複用，不必重新踩雷。

若 AutoClaude/tests 出現對等需求（同款「複製直譯器模擬健康 venv」或「建立 symlink」
情境），比照本檔邏輯在 AutoClaude/tests/conftest.py 加對稱 fixture 並互相加文件連結
——兩套測試框架 pytest root 不同，不強求單一檔案共用，但邏輯必須一致。
"""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path


def copy_functional_interpreter(dest: Path) -> None:
    """把目前真正在跑的直譯器複製到 dest，供測試偽裝成「健康的既有 venv」。

    真實 Windows 機器踩到的落差（tools/tests 首次真跑於本機 venv-launcher
    佈局才顯形，Mock/CI 環境不重現）：Windows 上（尤其 uv/`python -m venv`
    建立的 `.venv/Scripts/python.exe`）sys.executable 常是依賴同層
    `pyvenv.cfg`（記錄 `home=` 指回真正安裝目錄）才能運作的轉導 stub，並非
    完整直譯器本體；只複製這個 exe、不帶走 pyvenv.cfg，會得到一個檔案存在
    但 subprocess 執行 rc=106（"No pyvenv.cfg file"）的壞掉直譯器，讓本應
    測「健康」情境的測試誤判為「不健康」。一併複製 pyvenv.cfg（若源頭存在）
    並維持同層相對位置（dest 上一層），讓複製後的直譯器仍可正確解析 home=。
    """
    shutil.copy(sys.executable, dest)
    src_cfg = Path(sys.executable).resolve().parent.parent / "pyvenv.cfg"
    if src_cfg.is_file():
        shutil.copy(src_cfg, dest.parent.parent / "pyvenv.cfg")


def create_symlink_or_skip(
    test_case: unittest.TestCase,
    link_path: Path,
    target: Path,
    *,
    target_is_directory: bool = False,
) -> None:
    """建立測試用 symlink；本機無權限（Windows 未開發者模式/非管理者，WinError 1314）
    時 skipTest 而非算失敗。

    這是測試 fixture 本身的前置需求做不到，不是 production 邏輯需要建立 symlink
    的權限（production 只需偵測/清除既有 symlink，不需要建立）。
    """
    try:
        link_path.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as e:
        test_case.skipTest(f"本機無建立 symlink 權限（{e}），略過 symlink 情境")
