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


# 平台中立的假「絕對」repo 根（R11 真 Mac 首跑實證，抽自 test_check_hooks_liveness.py）：
# 受測函式常依賴「repo_root / 絕對路徑 → 直接取代」的 pathlib join 語意，但 "D:/repo"
# 只在 Windows 是絕對路徑；POSIX 上 join 會變成 D:/repo/D:/repo/…、resolve 後恆不相等
# → Windows 全綠、Mac/Linux 假紅。凡測試需要「絕對路徑」語意者一律用本常數，
# 不可寫死磁碟機代號（tools/tests/test_platform_neutral_paths.py 機械掃描守護）。
ABS_FAKE_REPO = Path("D:/repo") if sys.platform == "win32" else Path("/repo")


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

    R21 四方一審（Architect/SA/SD/QA）追加（DEF-101-256）：當 sys.executable
    本身**不是**透過 venv 執行時（任何未啟用 venv 的官方支援直譯器安裝
    路徑皆會命中同一情境——pyenv-win、winget／python.org 安裝器版型，見
    ONBOARDING.md §1；uv 管理的直譯器因走上面 pyvenv.cfg 分支已被涵蓋），
    複製出的直譯器旁邊沒有同層相依 DLL（`python3*.dll`／`vcruntime140*.dll`），
    在 Windows 上啟動會因 STATUS_DLL_NOT_FOUND（0xC0000135）失敗
    （rc=3221225781）。修法無條件（不做任何 `if is_windows()` 平台分支）
    從 exe 本身同層 glob 具名 DLL pattern 並複製到 dest 同層——macOS/Linux
    上 sys.executable 同層通常沒有 `.dll` 副檔名檔案，glob 自然空手，本身
    即是安全的 no-op，三平台行為天生一致，不需要平台條件判斷（避開
    R19/R20 QA 抓到過的「條件分支寫反/從未真正執行卻沒人發現」風險形態）。
    刻意使用具名 glob pattern（非裸 `*.dll` 全複製）避免誤複製到
    sqlite3/libssl/tcl-tk 等不必要的 DLL（增加 I/O 與被鎖檔風險）。
    """
    shutil.copy(sys.executable, dest)
    src_cfg = Path(sys.executable).resolve().parent.parent / "pyvenv.cfg"
    if src_cfg.is_file():
        shutil.copy(src_cfg, dest.parent.parent / "pyvenv.cfg")

    # DLL 來源目錄變數與上面 pyvenv.cfg 分支的 src_cfg 目錄變數完全分開、
    # 獨立命名（SD 指出的關鍵風險：混用同一個 `.parent.parent` 表達式會
    # 讓 glob 恆空，看起來改了程式碼但實際上什麼都沒複製到，比現狀更
    # 隱蔽的退化）——DLL 與 exe 本體同層，用 exe 本身的 `.parent`，
    # 不是 venv 根目錄層級的 `.parent.parent`。
    interpreter_dll_dir = Path(sys.executable).parent
    for dll_pattern in ("python3*.dll", "vcruntime140*.dll"):
        for dll_src in interpreter_dll_dir.glob(dll_pattern):
            shutil.copy(dll_src, dest.parent / dll_src.name)


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
