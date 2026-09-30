#!/usr/bin/env python3
"""PowerShell 引擎能力述詞 SSOT（R60 Scan-E E-A-03）。

WHY：`tools/tests/` 對「本機有哪個 PowerShell 引擎、拿哪一個去跑」曾散落 6 檔／10 處／5 種語意而無
具名 SSOT，「選錯」已有兩次實證（DEF-101-285、DEF-101-509）。現行政策：`production_engine()` ＝生
產引擎、**5.1 優先**（`PRODUCTION_ENGINE_PRECEDENCE` 順序即判準，不得對調），pwsh 7 只作本機根本沒
有 5.1 時的兜底；`native_ps51()`（語意④）不得 fallback；引擎可用性是**機器屬性**，一律現查
`available_engines()`，不得寫成常數。另立模組而非塞進 `_platform_helpers.py`（其收納契約只有兩
類）。語意①~⑤ 清單、與 DEF-101-509 的方向衝突、R69／R73 訂正全文搬至
Guard_Line_History_2.md〈R186 淨減法搬遷〉§2。  round-label-ok

守門：`tools/tests/test_ps_engine_ssot.py`（優先序含兩引擎都在的合成情境、`native_ps51()` 不得
fallback、repo-wide 反增生掃描走 `ast`、正向委派鎖）。

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
