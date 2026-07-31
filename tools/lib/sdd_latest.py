#!/usr/bin/env python3
"""AISDLC_SDD LATEST 版本解析共用模組（ADR-XPLAT-002 Phase 2-C/2-D，R66 收斂，DEF-101-624）。

背景：「呼叫 `AISDLC_SDD/scripts/sdd_version.py` SSOT subprocess 解析 LATEST 版本」
這段邏輯（Phase 2-C）與「凍結版本路徑/目錄名 regex 判斷＋排除」這段邏輯（Phase 2-D）
逐字複製到 10 支 `tools/tests/*.py` 測試檔，僅回傳投影不同（版本名字串／版本根目錄
`Path`／`fsm_runtime/tests` 子目錄 `Path`）。本模組收斂為單一真相源，供各測試檔
改為呼叫，而非各自維護一份 subprocess 樣板或一份 regex。

只依賴 stdlib：供 `sys.path.insert(0, str(repo_root / "tools" / "lib"))` 方式
import（同 `tools/lib/platform_utils.py`／`tools/lib/bash_probe_spec.py` 既有慣例）。

只提供 raise 版入口（`resolve_latest_name`/`resolve_latest_root`）——這是 10 支
測試檔唯一共用的契約（解析失敗即 `AssertionError`，掃描邊界不得靜默縮小）。
`tools/check_script_parity.py::_find_latest_sdd_version()` 另有一份「解析失敗回
`None`」的軟失敗契約，該檔本身不在本輪收斂範圍（不強行統一兩種契約，亦不在本模組
新增一個目前沒有任何呼叫端的 Optional 版入口——沒有呼叫端的分支寫了也測不到）。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# 凍結／LATEST 版本「目錄名本身」全字串比對——呼叫端一律用 `.fullmatch()`（R66
# DEF-101-624 修正：舊有 2 份複本〔test_component_sanitizer_shared_layer_lock.py／
# test_sanitize_component_frozen_sdd_versions_lock.py〕誤用 `.match()`——Python 的
# `$` 錨在非 MULTILINE 模式下對「字串結尾前恰有一個換行字元」的位置也視為滿足，
# 而 `.match()` 不要求吃光整個輸入，故 `re.match(r'^AISDLC_SDD_v\d+\.\d+$',
# 'AISDLC_SDD_v0.30\n')` 會誤判命中；`.fullmatch()` 要求輸入從頭到尾整段對齊
# pattern，同一輸入下正確地不命中）。
#
# 🔴 既知缺口（DEF-101-500 third item／DEF-101-521，未隨本次收斂修復，仍 open）：
# `\d+\.\d+` 抓不到三段版號（如 v1.0.1），非本次收斂範圍——本次只收斂「重複定義」
# 與「.match()/.fullmatch() 缺口」，不變更版號 pattern 本身。
FROZEN_VERSION_DIR_RE = re.compile(r"^AISDLC_SDD_v\d+\.\d+$")

# 凍結版本「路徑前綴」比對——呼叫端一律用 `.match()`（非 `.fullmatch()`）：比對
# 對象是完整相對路徑（如 "AISDLC_SDD/AISDLC_SDD_v0.30/tools/foo.py"），只要求
# 前綴命中、其後仍有更多路徑片段，與 FROZEN_VERSION_DIR_RE（比對單一目錄名本身、
# 要求整段對齊）語意不同，非同一個 `.match()` 缺口。
FROZEN_SDD_PATH_PREFIX_RE = re.compile(r"^AISDLC_SDD/(AISDLC_SDD_v\d+\.\d+)/")


def resolve_latest_name(sdd_root: Path) -> str:
    """LATEST 版本名（`sdd_version.py` SSOT；解析失敗即 `AssertionError`，
    掃描邊界不得靜默縮小）。"""
    resolver = sdd_root / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(sdd_root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return name


def resolve_latest_root(sdd_root: Path) -> Path:
    """LATEST 版根目錄（`sdd_root / resolve_latest_name(sdd_root)`）；解析
    失敗即 `AssertionError`（同 `resolve_latest_name`）。"""
    return sdd_root / resolve_latest_name(sdd_root)


def exclude_frozen_sdd_versions(paths: list[str], latest_name: str) -> list[str]:
    """排除 AISDLC_SDD 凍結版本路徑（v0.01 ~ 除 LATEST 以外者）——凍結版依
    Copy-on-Evolve 鐵律不應被新規則追殺歷史快照。"""
    kept = []
    for rel in paths:
        m = FROZEN_SDD_PATH_PREFIX_RE.match(rel)
        if m and m.group(1) != latest_name:
            continue
        kept.append(rel)
    return kept
