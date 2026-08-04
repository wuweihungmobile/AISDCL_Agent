#!/usr/bin/env python3
"""職責③：測試樹的**檔案 I/O**——把樹讀成 `{相對路徑: 原始碼}` 餵給靜態掃描。

WHY 與職責②分家（拆分前兩者同住一檔，且原檔頭自己就宣告「I/O 層與上面三個純函式
分離」）：②是純函式、可用合成 `dict` 注入、三個平台結果相同；本模組碰磁碟、結果隨
checkout 狀態變動。混在一起時，②的單元測試很容易不小心讀到真實磁碟（本 repo 已有
多次「鎖其實在讀真樹、換棵樹就靜默失效」的前例）。分家後「哪一段會碰磁碟」在 import
行上就看得出來。
"""
from __future__ import annotations

from pathlib import Path

from skip_tag_policy import _CACHE_DIR_NAMES, _EXTRA_SCAN_TREES


def read_test_sources(tests_dir: Path, pattern: str) -> dict[str, str]:
    """回傳 `{相對路徑: 原始碼}`。

    `pattern` **不給預設值**：掃描面必須與呼叫端的 discovery pattern 是同一個值
    （`run_root_unittests._PATTERN`），在這裡另立一份預設等於製造第二個會漂移的
    真相源。**遞迴**列舉並跳過快取目錄：非遞迴 glob 對「新增子目錄裡的鎖檔」是漏的，
    `test_adr_xplat001_c1c2_lock.guard_files_in_worktree` 已為同一個不對稱付過代價
    （改 top-level 檔→紅、新增子目錄檔→綠），本掃描沒有理由再引進一次。
    """
    return {
        p.relative_to(tests_dir).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(tests_dir.rglob(pattern))
        if not _CACHE_DIR_NAMES & set(p.parts)
    }


def scan_tree_sources(repo_root: Path, tests_dir: Path, pattern: str) -> dict[str, dict[str, str]]:
    """回傳 `{樹名: {相對樹的路徑: 原始碼}}`——三棵活測試樹（見 `_EXTRA_SCAN_TREES`）。

    `tests_dir` 仍是呼叫端傳進來的主樹（`tools/tests`），其餘由 `repo_root` 推導：
    這樣呼叫端（`tools/run_root_unittests.py`）的簽名完全不用改。
    """
    trees: dict[str, dict[str, str]] = {
        tests_dir.relative_to(repo_root).as_posix(): read_test_sources(tests_dir, pattern),
    }
    for rel in _EXTRA_SCAN_TREES:
        root = repo_root / rel
        trees[rel] = read_test_sources(root, pattern) if root.is_dir() else {}
    return trees
