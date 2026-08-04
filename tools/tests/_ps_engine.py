#!/usr/bin/env python3
"""PowerShell 引擎能力述詞 SSOT（R60 Scan-E E-A-03）。

WHY：`tools/tests/` 內對「本機有哪個 PowerShell 引擎、要拿哪一個去跑」這件事，
R60 實查有 **6 個檔案／10 處行內寫法／5 種語意**，無具名 SSOT、也沒有任何鎖防止
第 N+1 份選錯（而「選錯」在本 repo 已有兩次實證：DEF-101-285、DEF-101-509）：

  語意①「生產引擎，5.1 優先」`which("powershell") or which("pwsh")`——6 處。
  語意②「有沒有任一引擎」（skip 述詞）`which(...) is None and which(...) is None`——5 處。
  語意③「在 Windows 且有任一引擎」（`.cmd`／PATHEXT 語意測試專用）——2 處。
  語意④「只認原生 5.1，不得 fallback」`which("powershell")` 單獨用——2 處。
  語意⑤「**pwsh 7 優先**」`which("pwsh") or which("powershell")`——1 處（3 個消費點）。

⑤ 與 R59 **DEF-101-509 拍板的判準方向相反**。該判準原文（`test_install_windows_nightly.py`
的 WHY 區塊）：「生產是以 `powershell -ExecutionPolicy Bypass -File` 執行＝5.1，而 `pwsh`
解析用的是 PS 7 文法…本檔所在的 `tools/` 樹受 `test_ps51_compat.py` 的『PS 5.1 相容』
政策約束，故以 5.1 優先解析與該政策一致」。⑤ 會靜默 fallback 到另一個引擎、測不出差別；GitHub-hosted
runner、任何 `winget install Microsoft.PowerShell` 過的開發機、以及 `brew install
powershell` 過的 macOS 開發機都同時有兩者（🔴 **R69 訂正、R74 改寫**：本段原先把撰寫
當下那台機器的引擎清單寫成了本檔的常數，R69 在 macOS 真機上實測推翻。引擎可用性是
**機器屬性**，一律現查 `available_engines()`；R74 另把原訂正註記裡逐字保留的那句舊話
一併刪除——留著它等於在樹裡多存一句假話，而擴射程後的鎖正好抓到它），
於是會用 **PS 7** 去驗一支受 5.1 政策約束的檔案——與 DEF-101-509 修掉的是同一類判準
錯誤、只是方向相反。本檔因此把「生產引擎＝5.1 優先」寫成唯一的
具名述詞（`production_engine()`），讓「選誰」這件事只有一處可改、且有鎖看著。

**為何另立一支模組、不塞進 `_platform_helpers.py`**：該檔 docstring 自己已明列收納
契約僅兩類（跨平台測試 fixture、供靜態鎖消費的原始碼解析 SSOT），並記載 R57 因塞進
第三類而出現「雜物抽屜的早期訊號」的教訓。引擎述詞既非 fixture 也非原始碼解析器，
故比照同目錄 `_ci_scan_anchors.py` 的先例，單一關注點獨立成檔。

守門：`tools/tests/test_ps_engine_ssot.py`
  - 優先序（含「兩引擎都在」的合成情境——合成是為了讓判準在**任何**機器上都測得到
    方向，不依賴該機器剛好裝了哪些引擎；R69 訂正：原註記把引擎可用性寫成了本機常數。
    🔴 R73 補記（DEF-101-777）：該註記的訂正只涵蓋本檔，射程外的同型句子四輪後同時
    變成假事實——鎖已擴至整個 `tools/` 樹，見 `test_ps_engine_ssot.py`
    `TestNoStaleLocalEngineClaims`）
  - `native_ps51()` 不得 fallback
  - repo-wide 反增生掃描：`tools/tests/*.py` 不得再出現行內引擎挑選（附具名豁免＋stale
    自檢）。**判定走 `ast`**（R60 round-2 訂正）：只認真正的 `shutil.which("powershell"
    |"pwsh")` 呼叫節點，docstring／註解／字串常數內拿舊實作當史料引述**不算命中**。
    先前的逐行文字判定會被史料引述誤命中，使檔案級豁免永遠退不了場、被豁免的檔案
    零覆蓋（ARCH-R60-06／SA-R60-03／SD-R60-03／QA-R60-07 四方獨立命中）。
  - 正向委派鎖：已遷移消費檔的引擎述詞函式本體必須呼叫 `production_engine()`、
    不得回退成行內 `shutil.which`（import 級鎖看不到「留 import、改本體」這條路）

執行：python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import platform
import shutil
import sys

# 生產引擎優先序（R59 DEF-101-509 拍板）：Windows 內建的 Windows PowerShell 5.1 在前，
# pwsh 7 只作「本機根本沒有 5.1」（macOS/Linux）時的兜底。**順序即判準，不得對調。**
PRODUCTION_ENGINE_PRECEDENCE: tuple[str, ...] = ("powershell", "pwsh")

# 原生 Windows PowerShell 5.1 的可執行檔名（語意④專用：刻意不接受 pwsh 兜底）。
NATIVE_PS51_EXE = "powershell"


def available_engines() -> dict[str, str]:
    """`{引擎名: 解析到的路徑}`；本機缺席的引擎不入 dict（供診斷訊息與鎖使用）。"""
    found: dict[str, str] = {}
    for name in PRODUCTION_ENGINE_PRECEDENCE:
        path = shutil.which(name)
        if path:
            found[name] = path
    return found


def production_engine() -> str | None:
    """**生產引擎**路徑：Windows PowerShell 5.1 優先，pwsh 7 兜底；皆無則 None。

    語意①。凡「要真的拿一個 PowerShell 去執行／解析受 `tools/` 5.1 政策約束的腳本」
    一律用本述詞——不要在呼叫端自己寫 `which(...) or which(...)`，那正是 R60 E-A-03
    要收斂掉的形態（曾出現 pwsh 優先的第 5 種語意，方向與 DEF-101-509 相反）。
    """
    for name in PRODUCTION_ENGINE_PRECEDENCE:
        path = shutil.which(name)
        if path:
            return path
    return None


def any_engine_available() -> bool:
    """語意②：本機是否有任一 PowerShell 引擎（`skipIf`／`skipUnless` 述詞用）。"""
    return production_engine() is not None


def windows_with_engine() -> bool:
    """語意③：在 Windows 平台**且**有可用引擎。

    僅供依賴 Windows PATHEXT／`.cmd` 解析語意的測試使用：那類測試用 `.cmd` 假直譯器
    讓 `Get-Command python3`／`& python3` 命中它，而 `.cmd` 需要 `cmd.exe` 解譯——
    在裝有 pwsh 的 macOS/Linux 開發機上呼叫 `.cmd` 會靜默無回應（無輸出、
    `$LASTEXITCODE` 為空），使測試確定性失敗而非雜訊。故「有引擎」不足以排除那類
    機器，**必須同時檢查平台本身**（這正是語意②與③不可合併的理由）。
    """
    return sys.platform.startswith("win") and any_engine_available()


def native_ps51() -> str | None:
    """語意④：**只**認原生 Windows PowerShell 5.1，缺席即 None（刻意不 fallback 到 pwsh）。

    用於「PATH 分隔符／反斜線正規化」這類**只在原生 5.1 上才成立**的行為驗證——
    用 pwsh 7 跑會得到不同語意，fallback 等於讓載具失去鑑別力。
    """
    return shutil.which(NATIVE_PS51_EXE)


def windows_with_native_ps51() -> bool:
    """語意④的 skip 述詞：在 Windows 平台且原生 5.1 真的解析得到。"""
    return platform.system() == "Windows" and native_ps51() is not None
