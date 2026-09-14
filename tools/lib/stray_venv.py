#!/usr/bin/env python3
"""雜散 venv 偵測（純讀、零寫、零刪；DEF-200-297）。

背景：DEF-200-294 事故起因是子專案（AutoClaude/、AISDLC_SDD/**）底下悄悄長出
第二顆 `.venv`，子 hook 候選鏈把它撿去當直譯器用而跑錯環境。單一 .venv 設計
（見根 ONBOARDING §2.1）要求全樹只有 `<root>/.venv` 這一顆開發 venv；本模組
只負責「開工當下有沒有雜散 venv／殘留」的**唯讀**偵測與可複製刪除指令產生，
真正的刪除一律由使用者自行執行（fail loud 優於本模組代勞誤刪）。

刻意不用任何單平台 API：`is_windows` 由呼叫端傳入，本模組零 `sys.platform`
分支（鐵律三）。所有函式皆為純讀取（`Path.glob`／`Path.is_dir`／`Path.is_file`／
`Path.iterdir`），不含 `os.replace`／`rename`／`shutil.move`／`unlink`／`rmtree`。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

# 子專案雜散 venv 的掃描面：兩個子專案根目錄的直接子目錄，外加 AISDLC_SDD 底下
# 逐版目錄（如 AISDLC_SDD_v0.01/）各自的直接子目錄——版本目錄本身可能各帶一顆。
_SCAN_GLOBS: tuple[str, ...] = ("AutoClaude/*", "AISDLC_SDD/*", "AISDLC_SDD/*/*")


def find_stray_venvs(root: Path) -> list[Path]:
    """掃 `root` 下子專案目錄，回傳含 `pyvenv.cfg` 的目錄（以標記檔判定，不看
    目錄名）。排除 `root/.venv` 本尊與 `root/.venv-cache-*`（同一顆 venv 換平台
    時的暫存身分，不算第二顆）——兩者理論上不落在掃描面內，此處僅作明確自證。
    """
    root_venv = root / ".venv"
    found: set[Path] = set()
    for pattern in _SCAN_GLOBS:
        for cand in root.glob(pattern):
            if cand == root_venv or cand.name.startswith(".venv-cache-"):
                continue
            if not cand.is_dir():
                continue
            if (cand / "pyvenv.cfg").is_file():
                found.add(cand)
    return sorted(found)


def find_temp_cleanvenvs() -> list[Path]:
    """`%TEMP%`／`$TMPDIR` 下名稱含 `cleanvenv` 的殘留目錄（DEF-200-294 事故的
    另一半：§7 回填用的乾淨 venv 用完未刪）。名稱可能不含 `pyvenv.cfg`（半殘
    複製），故按名稱而非標記檔判定。
    """
    try:
        entries = list(Path(tempfile.gettempdir()).iterdir())
    except OSError:
        return []
    return sorted(p for p in entries if p.is_dir() and "cleanvenv" in p.name)


def advisory_lines(root: Path, is_windows: bool) -> list[str]:
    """每筆雜散 venv／殘留一行警告＋可直接複製的刪除指令。空清單回空。"""
    lines: list[str] = []
    for p in [*find_stray_venvs(root), *find_temp_cleanvenvs()]:
        cmd = f'Remove-Item -Recurse -Force "{p}"' if is_windows else f'rm -rf "{p}"'
        lines.append(
            f"偵測到雜散 venv／殘留：{p}"
            f"（單一 .venv 設計，見 ONBOARDING §2.1）— 建議刪除：{cmd}"
        )
    return lines
