#!/usr/bin/env python3
"""tools/tests 共用的跨平台測試 fixture 輔助函式。

**收納契約（單一類）**：只收「對開發者本機作業系統／環境有隱性假設，且只有真的在目標作業
系統上跑一次才會顯形」的測試 fixture 輔助。判準見下段。

**R58 已移出的內容（ARCH-R57R3-02／DEF-101-500 ⑤ 落地）**：`strip_ps_comments` 家族
（PowerShell 原始碼 tokenizer）原寄居本檔，但它既不是 fixture、也與本機環境假設無關，卻佔
全檔一半以上行數——R57 因此被迫把本檔契約改寫成「兩類收納物」，**契約被內容反向牽著改就是
雜物抽屜的早期訊號**。R58 已拆至 `tools/tests/_ps_source.py`（PowerShell 原始碼解析 SSOT），
本檔契約隨之收回單一類。呼叫端鎖 `test_find_git_bash_parity.TestPsCommentStripperSsotCallsiteLock`
的 `_PS_STRIPPER_SSOT_MODULE` 已同步指向新模組——其豁免清單是
`f"{_PS_STRIPPER_SSOT_MODULE}.py"`，故拆分後**本檔從此也不准自帶同名函式**，正是想要的效果。

四方複審 S21（architecture-review-own-finding）落地：F2（_copy_functional_interpreter）
與 F3（symlink 建立失敗 → skipTest）都是同一類「測試 fixture 對開發者本機環境有隱性
假設」的問題，且都只有在真的於目標作業系統上跑一次才會顯形（見
docs/06_quality/AutoSDD_Defect_Log.md DEF-101-064／DEF-101-069）。集中在本檔，供
tools/tests/ 內未來新測試直接複用，不必重新踩雷。

若 AutoClaude/tests 出現對等需求（同款「複製直譯器模擬健康 venv」或「建立 symlink」
情境），比照本檔邏輯在 AutoClaude/tests/conftest.py 加對稱 fixture 並互相加文件連結
——兩套測試框架 pytest root 不同，不強求單一檔案共用，但邏輯必須一致。

歷史（收斂的來由，供理解 `_ps_source.py` 為何存在）：R57 SA-R57R2-03 發現 PowerShell 註解
剝除函式在 `test_find_git_bash_parity.py` 與 `test_windows_nightly_anchor_parity.py` 各存一份
AST 逐字相同的複本、且無一致性鎖，而同輪卻把 `_ci_scan_anchors.py` 的三份複本以「三份複製只是
把同一個盲點抄了三遍」為由收斂，兩套標準；事後被 A-R57R2-02／R57R2-QA-01 證實兩份複本確實
同時帶著同一個 here-string 起始誤判的 fail-open。當時先收進本檔（就近原則），R58 再依契約
拆出 `_ps_source.py`。
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


def powershell_exe() -> str | None:
    """回傳本機可用的 PowerShell 執行檔絕對路徑；都沒有則 None。

    **偏好順序刻意是「Windows 上先找出廠的 `powershell`（5.1），其他平台找 `pwsh`」**，理由
    （R58 DEF-101-507，這是本輪升格為架構判準的那條）：

    1. **可用性必須以目標平台的出廠組態為準，不得以開發機組態為準。** Windows 11 出廠只有
       Windows PowerShell 5.1，`pwsh` 7 需另外安裝（R58 動工的真 Windows 11 Pro 實測即
       `pwsh` NOT FOUND）。此前 `test_install_windows_nightly.py` 寫成
       `skipUnless(shutil.which("pwsh"))`，於是那道「PowerShell 語法解析」守門**在它唯一要
       保護的平台上恆 skip**，卻在裝了 pwsh 的 macOS 開發機上會跑——守門在不需要它的平台
       生效、在需要它的平台失效。病灶不是手誤：那支測試的 skip 理由旁邊就寫著「跨平台安全
       （macOS/Linux pwsh 皆可跑）」，作者當時的參照系是自己的開發機。
    2. **驗語法要用目標引擎。** 這些 `.ps1` 的目標執行環境是使用者的 5.1（repo 另有
       `test_ps51_compat.py` 機械保證 5.1 相容）。若優先用 7 去 parse，只有 7 才接受的語法
       會通過而在使用者機器上炸掉——方向是 fail-open，故 Windows 上以 5.1 為先。
    3. 非 Windows 平台上 `powershell` 這個名字通常不存在（PowerShell Core 的執行檔名就是
       `pwsh`），故順序反轉，實質效果相同：**先找目標引擎，再退回可得的引擎**。

    這條判準的機械強制在 `tools/tests/test_platform_guard_availability.py`，兩道各管一件事：
      * `PwshOnlyGateTest`——前瞻掃描，抓未來新增的「只認 pwsh、不認 powershell」skip 條件。
      * `PowerShellExeSsotCallsiteLock`——**呼叫端鎖**，抓「本函式被 fork 成第二份」。R58
        ARCH-R58R1-03 實證這道鎖非有不可：本函式被立為 SSOT 的**同一輪內**就 fork 成三份
        且行為已分歧（`gen_ps_comment_golden.py` 逐字複製 order tuple；某 AutoClaude 測試
        改用 `platform.system()` 判斷且非 Windows 分支不兜底 `powershell`）。這是
        「SSOT 沒有呼叫端鎖 ＝ 沒有強制力」的第三次同型復發（前兩次：R56 `_CI_TREE_RE`
        抄三份、R57 註解剝除器抄兩份）。**改本函式的簽章或語意前先看那道鎖**。
    """
    order = ("powershell", "pwsh") if sys.platform.startswith("win") else ("pwsh", "powershell")
    for name in order:
        found = shutil.which(name)
        if found:
            return found
    return None


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
