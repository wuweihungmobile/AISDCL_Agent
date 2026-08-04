#!/usr/bin/env python3
"""平台判斷 + hook 腳本 I/O 初始化共用模組
（monorepo 根層共用，AutoClaude 與 AISDLC_SDD 兩側皆可用）。

收斂背景：`_init_utf8_streams()` 曾被複製貼上到至少 8 個檔案，其中 6 份漏了
`sys.platform != "win32"` 守衛，在 macOS/Linux 上也會無條件把 sys.stdout/stderr
換成新的 TextIOWrapper——POSIX 終端機預設已是 UTF-8，重新包裝除了改變
buffering 行為（TextIOWrapper 預設非 line-buffered）、丟棄原始 stream 物件外
沒有任何好處，是純粹的行為分歧風險。本模組以「有守衛」版本為唯一正確實作。

只依賴 stdlib：供 AutoClaude/tools/hooks/ 下的 hook 腳本以
`sys.path.insert(0, str(repo_root / "tools" / "lib"))` 方式 import——hook 腳本
執行環境不保證能 import 完整 autoclaude 套件，僅假設 stdlib + repo 根目錄可達。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def is_windows() -> bool:
    return sys.platform == "win32"


# 供 venv_python_path() 內部呼叫的別名（R17 DEF-101-231 觀察點 1+2）：該函式的
# `is_windows` 參數名與本函式同名，函式體內 `is_windows` 一律指向參數（區域變數
# 遮蔽全域函式，Python 詞法範圍規則），故需在此另存一個不同名稱的參照才能在
# 參數為 None 時呼叫到真正的平台判斷。
_is_windows = is_windows


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_posix() -> bool:
    return sys.platform != "win32"


def os_label() -> str:
    """三態標籤：windows/mac/linux（同 tools/dev_start.py 的 `_now_label()`）。"""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def venv_python_path(venv_dir: Path, is_windows: bool | None = None) -> Path:
    """venv_dir 內對應本平台的直譯器路徑：windows → Scripts/python.exe，否則 bin/python。

    收斂背景（R17 DEF-101-231 觀察點 1+2）：`tools/dev_start.py::_venv_python_at()`
    與 `tools/bootstrap_core.py::venv_python_path()` 各自獨立寫了同一款
    「Scripts/python.exe vs bin/python」判斷，本函式收斂為單一真相源。

    `is_windows` 參數為 `None`（預設）時呼叫本模組的 `is_windows()` 判斷目前執行
    平台；保留可覆寫參數是因為呼叫端（如 dev_start.py 的 venv 換手快取邏輯）需要
    針對「目標平台形狀」而非「目前執行平台」算路徑（例：判斷另一平台快取目錄內
    的直譯器是否存在），與目前程序實際執行的平台無關。
    """
    if is_windows is None:
        is_windows = _is_windows()
    return venv_dir / "Scripts" / "python.exe" if is_windows else venv_dir / "bin" / "python"


# ── 「強制 stdout/stderr 為 UTF-8」：本檔**只委派**，實作不在這裡（R75 去重）────────
#
# 🔴 缺陷本體：同一份知識先前有**兩個各自宣稱是 SSOT 的家**——本檔的
# `init_utf8_streams()`（`io.TextIOWrapper` 換掉串流、只在 `__main__` 呼叫）與
# `tools/_stdio_utf8.py::reconfigure_stdio_utf8()`（`.reconfigure()` 就地改、import 期
# 即生效），而後者的檔頭逐字自稱「本模組把該段保護收斂為單一 helper」。兩者實作／啟用
# 時機／對測試替身的行為三者皆不同，消費端分屬兩群（本檔 8 支 AutoClaude hook 與工具／
# 那支 15 支根層 tools），**換用另一支會靜默改變行為**，而兩把鎖都只守自己那一支。
# R74 的 P0（`sys.stderr` 預設 `errors='backslashreplace'` 讓 hook 中文指引在非 CJK
# codepage 降解）正好就落在這一層。
#
# 🔴 **SSOT 為何是那一支、不是本檔**（R75 第一版選反了、當回合被實測打回）：
# `tools/_stdio_utf8.py` 的既有契約**包含「被複製到別處單獨執行」**——
# `AISDLC_SDD/scripts/tests/test_copy_on_evolve.py`／`test_ntfs_length_gate.py` 會把
# `tools/check_ntfs_paths.py` 連同它複製進 tmp 沙箱 repo（**不含 `tools/lib/`**）再以
# 子行程執行。第一版把實作搬進本檔、讓那支改成 `from platform_utils import …`，於是沙箱
# 裡 import 期 `ModuleNotFoundError`、6 支測試當場紅。
# ⇒ 可搬遷性是**硬約束**，而只有自我完備的那一支能滿足它 ⇒ **自我完備的那一支就是
#   SSOT，本檔委派過去**。方向由約束決定，不是由「哪一層比較像共用層」決定。
#
# 委派刻意做成**惰性**（在函式體內解析、而非模組層 import）：本檔同時被
# `bootstrap_core`／`dev_start`／`integration_gate_core`／`snapshot_sync` 為了
# `is_windows()` 而 import，而 `_stdio_utf8` 的 import **本身就是副作用**；模組層 import
# 會讓「只想問平台」的消費者也被動手術（pytest 擷取期尤其不可）。
#
# 兩件事由 `tools/tests/test_platform_utils_dedup.py::TestR75StdioUtf8HasOneImplementation`
# 機械釘住：① 本檔不得含任何強制 stdio 的**機制**（只准委派）；② SSOT 的可搬遷契約
# （複製到 tmp 後單獨 import、以 cp1252 子行程實跑中文不降解）。


def _stdio_utf8_impl():
    """取 SSOT（`tools/_stdio_utf8.py`）的 `reconfigure_stdio_utf8`；取不到回 `None`。

    以 `importlib` 由**絕對路徑**載入並註冊進 `sys.modules["_stdio_utf8"]`，而不是
    `sys.path.insert(tools/)`：後者會把根層 `tools/` 底下十幾支 CLI 模組掛上 hook 行程的
    import 面（hook 的執行環境刻意維持最小，見本檔檔頭），且註冊進 `sys.modules` 讓之後
    任何 `import _stdio_utf8` 拿到**同一個模組物件**（否則會有兩份、各自套用一次）。
    """
    mod = sys.modules.get("_stdio_utf8")
    if mod is None:
        # 本檔住 `<repo>/tools/lib/` ⇒ parents[1] 就是 `<repo>/tools/`。
        path = Path(__file__).resolve().parents[1] / "_stdio_utf8.py"
        if not path.is_file():  # pragma: no cover - 完整 checkout 下必然存在
            return None
        try:
            spec = importlib.util.spec_from_file_location("_stdio_utf8", path)
            if spec is None or spec.loader is None:
                return None
            mod = importlib.util.module_from_spec(spec)
            sys.modules["_stdio_utf8"] = mod
            spec.loader.exec_module(mod)  # ← import 期即套用一次（那就是它的契約）
        except Exception:  # noqa: BLE001 — 保護性程式碼不得反過來讓呼叫端崩潰
            sys.modules.pop("_stdio_utf8", None)
            return None
    return getattr(mod, "reconfigure_stdio_utf8", None)


def init_utf8_streams() -> None:
    """把 sys.stdout/stderr 強制為 UTF-8（`errors="replace"`），不分平台。

    **公開名與呼叫契約完全不變**（8 支 AutoClaude hook／工具沿用），行為改為委派到唯一
    實作 `tools/_stdio_utf8.py::reconfigure_stdio_utf8`——三條分支（就地 reconfigure／
    wrapper 回退／安全 no-op）與 R16 訂正的完整理由都寫在該函式的 docstring，本處不複寫
    （複寫就是下一次漂移）。

    取不到 SSOT 時**靜默不動**而非拋例外：本函式的呼叫端全是 `__main__` 進入點的保護性
    前置，保護件自己把行程弄掛是最糟的失敗模式。完整 checkout 下取不到是不可能的
    （同 repo 的兄弟檔），故這條路徑沒有需要嚷嚷的情境。
    """
    impl = _stdio_utf8_impl()
    if impl is not None:
        impl()
