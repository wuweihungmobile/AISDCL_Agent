#!/usr/bin/env python3
"""雜散 venv 偵測（純讀、零寫、零刪；DEF-200-297）。

背景：DEF-200-294 事故起因是子專案（AutoClaude/、AISDLC_SDD/**）底下悄悄長出
第二顆 `.venv`，子 hook 候選鏈把它撿去當直譯器用而跑錯環境。單一 .venv 設計
（見根 ONBOARDING §2.1）要求全樹只有 `<root>/.venv` 這一顆開發 venv；本模組
只負責「開工當下有沒有雜散 venv／殘留」的**唯讀**偵測與可複製刪除指令產生，
真正的刪除一律由使用者自行執行（fail loud 優於本模組代勞誤刪）。

2026-09-15 四方審查 M-03：舊版只掃固定兩層（`AutoClaude/*`／`AISDLC_SDD/*`／
`AISDLC_SDD/*/*`），漏收 `.claude/worktrees/x/.venv`、根層 `tools/.venv`、
`AISDLC_SDD/<ver>/tools/.venv`、`AutoClaude/tests/fixtures/.venv` 四類巢狀更深
的雜散 venv。改為對**全樹**（含 `.claude/worktrees`、`tools/`，任何巢狀深度）
遞迴走訪＋就地剪枝：命中 `root/.venv` 本尊、根層的 `.venv-cache-*`（同一顆 venv
換平台身分，不算第二顆）與常見 VCS／套件快取目錄（`.git`／`node_modules`／
`__pycache__`／`.pytest_cache`／`.ruff_cache`／`.hypothesis`／`.mypy_cache`）
一律不下探；命中含 `pyvenv.cfg` 的目錄後同樣不再下探（venv 內部結構無需再
掃）。效能量測依據：對本 repo 整棵樹（剪枝後約 6370 個目錄）實測 `os.walk`
走訪耗時 0.18 秒（2026-09-15），全樹遞迴在此規模下可行——見
`tools/tests/test_dev_start.py::TestStrayVenvScan` 的效能護欄測試。

2026-09-19（B1／SD 1a）：`.venv-cache-*` 前綴豁免收斂為**只准套用在根層**——子專案
底下同名前綴（如 `AutoClaude/.venv-cache-fake/`）是巧合撞名，不是「同一顆 venv
換平台身分」那個語意（那個語意只存在於根層 `.venv-cache-<flavor>/`，見 ONBOARDING
§2.1 ④），故不應被豁免、仍屬雜散 venv。

刻意不用任何單平台 API：`is_windows` 由呼叫端傳入，本模組零 `sys.platform`
分支（鐵律三）。所有函式皆為純讀取（`os.walk`／`Path.is_file`／`Path.iterdir`），
不含 `os.replace`／`rename`／`shutil.move`／`unlink`／`rmtree`。
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

# 遞迴走訪時就地剪枝、不下探的目錄名（VCS／套件管理器／測試快取產物，非子專案
# 候選——與 `.venv-cache-*` 前綴判斷分開處理，因為那個判準是前綴而非全名）。
_PRUNE_DIR_NAMES: frozenset[str] = frozenset({
    ".git", "node_modules", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".hypothesis", ".mypy_cache",
})


def find_stray_venvs(root: Path) -> list[Path]:
    """全樹（任何巢狀深度）遞迴掃描 `root`，回傳含 `pyvenv.cfg` 的目錄（以標記
    檔判定，不看目錄名）。就地剪枝、不下探：`root/.venv` 本尊、**根層底下**任何
    名稱以 `.venv-cache-` 開頭的目錄（同一顆 venv 換平台時的暫存身分，不算第二
    顆——子專案底下同名前綴是巧合撞名，不豁免，見模組 docstring B1／SD 1a）、
    `_PRUNE_DIR_NAMES` 列舉的 VCS／快取目錄；命中 `pyvenv.cfg` 的目錄本身也
    不再下探（其內部結構不是另一個獨立雜散案例）。

    SA 1（SD 1b，2026-09-19 四方複審追加）：`os.walk(followlinks=False)`
    不會走進 symlink 目錄，故指向外部 venv 的**真 symlink**（如
    `AutoClaude/.venv -> D:\\elsewhere\\venv`）是盲區——junction 在 Windows 上
    `Path.is_symlink()` 為 `False`，已被一般路徑掃到而不受影響。剪枝迴圈內對
    每個候選 `name` 額外判斷：若本身是 symlink 且目標含 `pyvenv.cfg`，直接記
    為雜散案例（不下探、不留在 `keep`——`os.walk` 本就不會走進 symlink，留著
    也無意義）。
    """
    root = Path(root)
    found: set[Path] = set()
    for dirpath, dirnames, _filenames in os.walk(root):
        current = Path(dirpath)
        keep: list[str] = []
        for name in dirnames:
            if current == root and name == ".venv":
                continue  # root/.venv 本尊
            if current == root and name.startswith(".venv-cache-"):
                continue  # 同一顆 venv 換平台身分，不算第二顆（僅根層豁免）
            if name in _PRUNE_DIR_NAMES:
                continue
            candidate = current / name
            if candidate.is_symlink() and (candidate / "pyvenv.cfg").is_file():
                found.add(candidate)  # symlink 指向外部 venv：os.walk 走不進去，直接記
                continue
            keep.append(name)
        dirnames[:] = keep
        if current == root:
            continue  # root 本身不是候選目錄（只掃它底下的子目錄）
        if (current / "pyvenv.cfg").is_file():
            found.add(current)
            dirnames[:] = []  # 命中即不下探
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
    """每筆雜散 venv／殘留一行訊息＋可直接複製的刪除指令；空清單回空。這是唯一的
    格式化點（`enforce` 也走這裡），同一份措辭只住一個家。"""
    lines: list[str] = []
    for p in [*find_stray_venvs(root), *find_temp_cleanvenvs()]:
        cmd = f'Remove-Item -Recurse -Force "{p}"' if is_windows else f'rm -rf "{p}"'
        lines.append(
            f"🔴 偵測到雜散 venv／殘留：{p} — 單一 .venv 設計"
            f"（ONBOARDING §2.1）下必須刪除後重跑 dev_start：{cmd}"
        )
    return lines


def enforce(root: Path, is_windows: bool, emit: Callable[[str], None]) -> bool:
    """開工當下擋下雜散 venv／殘留（掌舵者 2026-09-15 裁決：擋下並給刪除指令，
    不自動刪——fail loud 優於本模組代勞誤刪）。對每筆命中呼叫 `emit` 一行，並
    回傳 `False`；乾淨時不呼叫 `emit`、回傳 `True`。"""
    lines = advisory_lines(root, is_windows)
    for line in lines:
        emit(line)
    return not lines


def main(argv: list[str]) -> int:
    """CLI 入口：`python tools/lib/stray_venv.py <repo_root>`（B2／SD 1d）——供
    `tools/git-hooks/pre-commit` 順手掃描用，讓 DEF-200-294 這型事故的攔截點從
    「下次 dev_start」提前到「下次 commit」。乾淨 rc 0；命中即以 `enforce()` 把
    每筆訊息（含可複製的刪除指令）印到 stderr 並回 rc 1。

    UTF-8 stdio 一律委派 `platform_utils.init_utf8_streams()`（唯一實作，見該函式
    docstring）——不得繞過它自行就地改寫 stderr 串流編碼，否則撞
    `tools/tests/test_platform_utils_dedup.py::TestR75StdioUtf8HasOneImplementation`
    棘輪。惰性 import：本模組其餘函式是純讀取，不需要它，只有 CLI 進入點才需要。
    """
    if len(argv) != 1:
        print("用法：python tools/lib/stray_venv.py <repo_root>", file=sys.stderr)
        return 2
    import platform_utils  # noqa: PLC0415

    platform_utils.init_utf8_streams()
    root = Path(argv[0])
    ok = enforce(root, os.name == "nt", lambda m: print(m, file=sys.stderr))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
