#!/usr/bin/env python3
"""薄殼 wrapper 退化守門 — 正規化內容 hash 釘選（R10 拍板案(a)，DEF-101-134）。

背景：tools/dev_start.py 是本 repo 首個貫徹「薄殼 + Python 核心」模式的範例
—— tools/dev_start.sh / tools/dev_start.ps1 依其自身 docstring 只做「選直譯器
→ 轉呼叫核心（dev_start.py）→ 視需要啟用 venv」三件事，業務邏輯全部收斂在
dev_start.py。R12（DEF-101-070 ② 收斂案）AutoClaude/tools/local_ci_gate 對子
亦收斂為同模式（核心＝AutoClaude/tools/local_ci_gate.py，薄殼只做「確認直譯器
→ 參數映射 → 轉呼叫核心」）。本工具守護「已經薄殼化」的對子不再退化回去長
業務邏輯。

守門策略演進（R10 拍板案(a)）：
  初版為「業務邏輯樣板關鍵字黑名單」——但列舉惡意是不可判定的軍備競賽，
  三輪複審接連被繞（`for(` 無空格、`python3 -c` 前綴、`.ForEach(` 方法呼叫，
  見 _FORBIDDEN 內逐條史料）。薄殼的本質是「幾乎永不變動」，適合白名單化：
  1. 【權威判定】正規化內容 sha256 釘選（_PINNED_SHA256）：剝除整行註解
     （.ps1 另剝 `<# … #>` 區塊）、行尾空白、空行後取 hash——任何實質內容
     變動（不論用什麼語法）一律紅燈，指路「確認變更仍屬薄殼職責後同步更新
     釘選值」。註解／說明文字調整不觸發（正規化吸收）。
     **例外——首行 shebang 納入 hash 輸入**（R67-H35）：`#!/usr/bin/env bash` 是
     直譯器宣告、不是註解，改成 `#!/bin/sh` 在 dash 下會直接壞掉薄殼三職責的第一項
     （選直譯器），故不得被「剝除註解」吸收。已實測涵蓋：shebang 改動一律紅燈
     （`TestR67ShebangIsNotAComment`）。
  2. 【第二訊號】行數上限（MAX_LINES）：hash 更新後的長期膨脹警戒線。
  3. 【並聯第三訊號】原黑名單不再是權威判定，但**與 hash 釘選並聯**（不論 hash
     是否相符一律執行），命中即列為問題並指路。
     **R60 Scan-E E-A-02 訂正——原本是「串聯」設計缺陷**：這組偵測原先整段巢狀在
     `if actual != pinned:` 內（＝「只在 hash 已紅時」附加印出），於是「更新 pin」
     這個正常維護動作會讓**整組關鍵字偵測同時失效**——把兩道防線接成串聯而非並聯。
     實測後果（R60，探針帶正控）：在 wrapper 內注入 `for ` 迴圈**並同步更新 pin**
     （即 docstring 自己指示的 `--print-hash` 工作流），`check_wrapper_thinness()`
     回傳 `problems=[]`、行數未達 MAX_LINES＝三道訊號全靜音。R60 起改為並聯。
     比對對象是**正規化後的內容**（與 hash 同一份文字，整行註解／空行已剝除），
     故說明性註解裡出現 `for ` 之類字樣不會誤判；殘餘偽陽性面如實揭露：
     `_normalize()` 不剝「行尾行內註解」，`$x = 1  # for the win` 這種寫法仍會命中。
     逃生口（不新增機制，沿用既有手改清單的慣例）：若某關鍵字確屬該薄殼職責所需，
     自該 wrapper 的 `_FORBIDDEN` 條目移除該字並就地補一行 WHY 註解——清單本身就是
     決策紀錄，且改動會出現在 guard 檔的 diff 上被複審看見。
     歷史（為何它先前被降級）：列舉惡意是不可判定的軍備競賽，三輪複審接連被繞
     （`for(` 無空格、`python3 -c` 前綴、`.ForEach(` 方法呼叫）——故**權威判定仍是
     hash**，本項只是並聯的補充訊號，不宣稱完備。

職責邊界（R56 補述，DEF-101-433 兩輪誤判為缺口的根因＝兩支工具的分工從未互相標註）：
  本檔只負責「**已註冊**薄殼不退化」（_PINNED_SHA256 內的對子）。
  「**新增**薄殼是否被註冊」由 tools/check_script_parity.py 反向驗證——它掃描全庫成對
  腳本，未納管者即 fail-loud 並列出三條納管途徑（_MARKER_PAIRS／掛本檔 hash 釘選／
  _EXEMPT_PAIRS 附帳本依據），另有「thinness 交叉鎖」比對雙清單鍵集合一致。
  兩者互補，缺一即出現前瞻盲區；修改任一支的納管邏輯時請同步檢視另一支。

讀檔編碼（R60 P10-1，BOM 盲區）：全檔一律走 `_read_source()`（`utf-8-sig`）——WHY 與
實測見該函式 docstring。**不要**在本檔任何地方另開 `read_text(encoding="utf-8")`：
`.ps1` 帶 UTF-8 BOM 是刻意的，讀取端漏剝就會把編碼構件當成腳本內容。

執行：python tools/check_wrapper_thinness.py
      python tools/check_wrapper_thinness.py --print-hash    # 取新的釘選 hash
      python tools/check_wrapper_thinness.py --print-lines   # 現查各殼行數／上限／餘裕
測試：tools/tests/test_check_wrapper_thinness.py
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli_flags  # noqa: E402  # 未知旗標 rc=2 fail-loud 的 SSOT（見該檔檔頭 WHY）
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

ROOT = Path(__file__).resolve().parent.parent

# 薄殼行數上限（第二訊號；權威判定仍是下方 hash 釘選）。
#
# 🔴 R60 round-2（SD-R60-08）刻意**不再寫死各殼當下行數**：本處原本列了 8 支殼的行數
# 快照，複審逐檔實測**8 支全部 stale**（其中 `local_ci_gate.ps1` 是同輪自己從舊值改到
# 新值卻沒回頭同步；清單還把 `run_act.*` 誤記在 `tools/` 下，實際在 `AutoClaude/tools/`）
# ——與 DEF-101-289／515「文件寫死機器算得出的數字」同一家族。**根治＝不存這種數字**，
# 改由程式現查：
#     python tools/check_wrapper_thinness.py --print-lines
# 印出每支殼的「行數／上限／餘裕」。`tools/tests/test_check_wrapper_thinness.py::
# TestNoHardcodedLineCounts` 機械守著本檔不得再寫回這類快照（寫回即紅並指路本註解）。
MAX_LINES = 100

_PS1_BLOCK_COMMENT_RE = re.compile(r"<#.*?#>", re.DOTALL)

# 正規化內容 sha256 釘選（權威判定）。刻意修改 wrapper 時：先確認變更仍屬
# 「選直譯器／轉呼叫核心／啟用 venv」薄殼職責，再以本檔 --print-hash 取新值
# 同步更新此表（並跑 tools/tests 確認）。
#
# 🔴 R60 P10-1 全面重釘（僅 `.ps1` 側五支）：`_read_source()` 改剝 BOM 後，帶 BOM 的
# `.ps1` 正規化文字少了那一行純 BOM 假行 ⇒ 五支 hash 全變。取證（沙箱腳本實跑）：
# 十支舊 pin 在舊讀法下皆可重現，且「新正規化文字 ≡ 舊正規化文字刪掉該假行」十支皆
# True；`.sh` 側五支無 BOM、hash 逐字不變——差異面恰好落在 BOM 檔上，證明是量對了
# 而非正規化演算法被改壞。
#
# 🔴 R67（R67-H35）重釘（本表 `.sh` 側七支 ＋ check_script_parity._LATEST_PINNED_SHA256
# 的 LATEST run_tlc.sh 一支，共八支）：`_normalize()` 改為保留首行 shebang 後，帶
# shebang 的檔正規化文字多了那一行 ⇒ 這八支 hash 全變。**逐支確認內容未被竄改**
# （真工作樹實跑，2026-08-01；釘選面合計 16 支＝本表 14 + LATEST 表 2）：
# ① 以「舊演算法」（剝掉所有 `#` 開頭行，含 shebang）重算 16 支現行檔案 ⇒ 全部逐字
# 重現舊 pin（`不符者: []`）⇒ 檔案內容一個位元組都沒動，變的只有正規化規則；
# ② `新正規化文字 ≡ 首行 shebang + "\n" + 舊正規化文字`（無 shebang 者 ≡ 舊正規化
# 文字）16 支皆 True；③ hash 變動的恰為有 shebang 的 8 支，未變的恰為無 shebang 的
# 8 支（`.ps1` 首行是 `<#` 區塊註解或一般註解）——差異面與 shebang 有無完全重合，
# 證明是量對了而非演算法被改壞。
_PINNED_SHA256: dict[str, str] = {
    # R43：WindowsApps 空殼排除 guard 收斂為 dot-source tools/lib/windowsapps_guard.sh
    # 共用函式（Scan-B 系統性缺口收斂，DEF-101-353；bash 側對稱 .ps1 側 R37 先例）
    # R69 P2 重釘：選直譯器改委派 SSOT 候選鏈 `pick_python_ge_min`（>= 3.11），
    # 取代原本「`python3`/`python` 命中即用」——後者在 macOS 上恆撿到系統 3.9，
    # 照 ONBOARDING §1 裝完 python@3.11 仍 rc=2（真機重現）。仍屬「選直譯器」
    # 薄殼職責（候選鏈邏輯落在 tools/lib/windowsapps_guard.sh，殼內零迴圈）。
    "tools/dev_start.sh": (
        "b7530b3bed8f5bbb44782e88527085bad9ef9c88ed8f178f872ac8d3ad2ba9d1"
    ),
    # R37：WindowsApps 空殼排除 guard 收斂為 dot-source tools/lib/WindowsAppsGuard.ps1
    # 共用函式（DEF-101-273/279/300/303 反覆復發後的架構收斂）
    # R69 P2 重釘：同 .sh 側，改委派 SSOT 候選鏈 `Get-PythonGeMin`（雙向對等，
    # 兩側同一套候選鏈語意與同一段版本探測碼）。
    "tools/dev_start.ps1": (
        "3217d73ac2cb2a1b136786e300ff7370855d58bb8594c961b7a136a80480fa60"
    ),
    # R12（DEF-101-070 ②）：local_ci_gate 收斂為薄殼＋Python 核心後納入釘選；
    # R43：補上 WindowsApps guard dot-source（同上 DEF-101-353）
    "AutoClaude/tools/local_ci_gate.sh": (
        "8d381f7c83714755b1a320a1af3d98abda64be15620a250db508f6e88f64eff0"
    ),
    # R44：python 前置檢查改走 tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython SSOT
    # R60（F-refuter-1）：$PytestArgs 預設值由寫死的 'tests/ -q --tb=short' 改為 ''
    # ——本檔 hash 釘選只認「殼內容有沒有變」，對「殼內嵌常數與核心常數語意分歧」
    # 天生盲目（R59 核心加 -rs 時本檔全綠、Windows 側靜默少 -rs），語意面另由
    # AutoClaude/tests/tools/test_local_ci_gate_shell_arg_parity.py 跨檔鎖守。
    "AutoClaude/tools/local_ci_gate.ps1": (
        "50c7246079fab0ee522b0d3a787e51bdf949161333b17b2b43300cd7b5e40373"
    ),
    # R16（Architect 建議 B）：bootstrap/integration_gate/run_act 收斂為薄殼＋
    # 各自 Python 核心（bootstrap_core.py／integration_gate_core.py／
    # run_act_core.py）後，由 check_script_parity.py 的 _MARKER_PAIRS 標籤比對
    # 遷移至此 hash 釘選（同 R12 local_ci_gate 先例；gate-call 抽取比對隨之退場）
    # R43：補上 WindowsApps guard dot-source（同上 DEF-101-353）
    "tools/bootstrap.sh": (
        "5d73047f1f81e81ed0b47a8147dbe69801640ee77f727ecc953c51d9eb865857"
    ),
    # R37：WindowsApps 空殼排除 guard 收斂為 dot-source tools/lib/WindowsAppsGuard.ps1
    # 共用函式（DEF-101-273/279/300/303 反覆復發後的架構收斂）
    "tools/bootstrap.ps1": (
        "993b366802dce5763e748247df43ea7fd6c8fd8db593f273892c35f4957bae45"
    ),
    # R43：補上 WindowsApps guard dot-source（同上 DEF-101-353）
    "tools/integration_gate.sh": (
        "3a155b915f7bc42c32c752885a97a38eb9a60a3b411d85c532a8421e4cacfc75"
    ),
    # R44：python 前置檢查改走 tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython SSOT
    "tools/integration_gate.ps1": (
        "ca1c18c920e28398d804e634ab7a7f0f96d213dd346bc93c1ee2981b15bc6c23"
    ),
    # R43：補上 WindowsApps guard dot-source（同上 DEF-101-353）
    "AutoClaude/tools/run_act.sh": (
        "422af63e6e74ef0b88ba4dbc3ca63e893a08470b451118d8f6d388d366fd848b"
    ),
    # R44：python 前置檢查改走 tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython SSOT
    "AutoClaude/tools/run_act.ps1": (
        "a2caf019457ef4c5f32fddfb7babbd01004a1d02625cba0eb51036740c76725b"
    ),
    # R61（ADR-XPLAT-002 Phase 1-B，DEF-101-088 由零守門的 _EXEMPT_PAIRS 決策豁免升級
    # 為 hash 釘選）：業務邏輯本已下沉 tools/git_hooks_install_common.py 單一真相源，
    # 兩份呼叫端僅剩各自平台原生薄殼呈現層；raw 行數 50/65/40/42 皆 ≤ MAX_LINES=100。
    "AutoClaude/tools/install_git_hooks.sh": (
        "b8f4aeb6cdd9b3a3cc1f93fc7ba0415cf8d8c7846e54ce397be59984a3deef18"
    ),
    "AutoClaude/tools/install_git_hooks.ps1": (
        "8133a5d7cd65e0c75a90e92fe3c3cbebdeccab3e73ec69ac08e1cb46cc8b0ce7"
    ),
    "AISDLC_SDD/scripts/install-hooks.sh": (
        "1fd0254e28a13c143d32d44985373e52f26b065529e7c9efc40332eb3bd6833a"
    ),
    "AISDLC_SDD/scripts/install-hooks.ps1": (
        "42b01cc883e29b79405abc0f0db5f2a9bf16e7e0b04ac399c0ddc47b16d03403"
    ),
}

# 業務邏輯樣板關鍵字（診斷輔助；權威判定為上方 hash 釘選）。歷史上三輪被繞的
# 史料保留於此，作為 hash 紅燈時的定位提示。
_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "tools/dev_start.sh": (
        "while ",       # 迴圈：wrapper 不該有迭代式業務邏輯
        "for ",         # 迴圈（bash for）
        "for(",         # C-style for 無空格寫法（2026-07-16 SD 第三輪繞過史料）
        "jq ",          # JSON 解析（外部工具）
        "python -c",    # 內嵌 Python 業務邏輯
        "python3 -c",   # 同上（獨立複審發現的前綴繞過史料）
    ),
    "tools/dev_start.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",  # .NET JSON 反序列化（第三輪繞過史料）
        "foreach (",
        "foreach(",           # 無空格寫法（第三輪繞過史料）
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",          # 陣列方法呼叫（第三輪繞過史料）
    ),
    # local_ci_gate 薄殼沿用 dev_start 同款診斷關鍵字（R12 納入時複製，非新增判準）
    "AutoClaude/tools/local_ci_gate.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "AutoClaude/tools/local_ci_gate.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
    # R16：bootstrap/integration_gate/run_act 薄殼沿用同款診斷關鍵字（複製非新增判準）
    "tools/bootstrap.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "tools/bootstrap.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
    "tools/integration_gate.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "tools/integration_gate.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
    "AutoClaude/tools/run_act.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "AutoClaude/tools/run_act.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
    # R61（ADR-XPLAT-002 Phase 1-B）：沿用既有薄殼同款診斷關鍵字（複製非新增判準）。
    "AutoClaude/tools/install_git_hooks.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "AutoClaude/tools/install_git_hooks.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
    "AISDLC_SDD/scripts/install-hooks.sh": (
        "while ",
        "for ",
        "for(",
        "jq ",
        "python -c",
        "python3 -c",
    ),
    "AISDLC_SDD/scripts/install-hooks.ps1": (
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "[System.Text.Json",
        "foreach (",
        "foreach(",
        "while (",
        "for (",
        "ForEach-Object",
        ".ForEach(",
    ),
}


def _read_source(path: Path) -> str:
    """本檔**唯一**的讀檔口——`utf-8-sig`（開頭 BOM 若在則剝除）。

    🔴 R60 P10-1（BOM 盲區）：原本以 `utf-8` 讀檔，於是 `.ps1` 開頭的 UTF-8 BOM
    （U+FEFF）被當成**內容**：`_normalize()` 剝掉檔頭 `<# … #>` 區塊後那一行只剩 BOM，
    而 `"\\ufeff".strip()` 在 Python 是**非空**（U+FEFF 屬 Cf 類、不算 whitespace），於是
    正規化結果的第一行是一個純 BOM 的假行——正規化行數比實質內容多出一行，釘選的
    sha256 也把「編碼構件」而非腳本內容釘了進去。實測（修前）：`tools/integration_gate.ps1`
    正規化後首行 `repr()` 為 `'\\ufeff'`。

    `.ps1` **帶 BOM 是刻意的**（PS 5.1 對無 BOM 的 UTF-8 檔改用 ANSI codepage 解讀、中文
    全毀，root-infra-ci 有 BOM 守門），故修法是**讀取端正確剝除**，不是拿掉 BOM。

    採 `utf-8-sig` 而非在 bytes 層自剝：`tools/check_script_parity.py::_extract_markers`／
    `_extract_tlc_runner_invocations`（R65 起接手已退場的 `_extract_tlc_tracks`，同樣先剝
    `<# … #>` 再逐行判定，與本檔 `_normalize()` 幾乎同形）早就用 `utf-8-sig`。兩支工具對
    **同一批** `.ps1` 各用一種讀法＝同一個量兩個答案；統一到 repo 既有的多數慣例才把這個
    分歧面消滅，而不是再多一種自製剝法。
    """
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _normalize(text: str, is_ps1: bool) -> str:
    """剝除註解／空行／行尾空白——hash 只反映實質內容。**首行 shebang 除外**。

    前提：`text` 來自 `_read_source()`（BOM 已剝）。本函式刻意**不**自己處理 BOM——
    否則就變成第二個「BOM 該由誰負責」的答案（見 `_read_source()` docstring）。

    🔴 R67（Scan-H R67-H35）：首行 `#!…` **不是註解，是直譯器宣告**——它決定這支殼
    由誰執行，正是「選直譯器／轉呼叫核心／啟用 venv」三項薄殼職責的第一項。原實作
    以 `not line.lstrip().startswith("#")` 一律剝除，於是 8 支釘選 `.sh` 的
    `#!/usr/bin/env bash` 可被改成 `#!/bin/sh` 而 hash 紋風不動（實測 rc=0、
    `tools/tests` 零紅）。`tools/dev_start.sh` 用了 `${BASH_SOURCE[0]}` 與 `local`，
    在 dash（Ubuntu runner 的 /bin/sh）下直接壞掉——守門對象的頭號職責整條在覆蓋面外。
    修法：首行若以 `#!` 起頭則無條件保留、進入 hash 輸入；其餘註解行照舊剝除
    （`test_comment_only_change_does_not_trip_hash` 的自由度不變）。`.ps1` 首行不是
    shebang（帶 BOM，且開頭常為 `<# … #>` 區塊註解），不受影響。
    """
    if is_ps1:
        text = _PS1_BLOCK_COMMENT_RE.sub("", text)
    lines = [line.rstrip() for line in text.splitlines()]
    shebang: list[str] = []
    if lines and lines[0].startswith("#!"):
        shebang = [lines[0]]
        lines = lines[1:]
    kept = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    return "\n".join(shebang + kept)


def normalized_content(path: Path) -> str:
    """正規化後的實質內容——hash 釘選與並聯關鍵字偵測共用**同一份**文字（R60 E-A-02）。"""
    return _normalize(_read_source(path), is_ps1=path.suffix.lower() == ".ps1")


def _sha256_text(norm: str) -> str:
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def normalized_sha256(path: Path) -> str:
    return _sha256_text(normalized_content(path))


def wrapper_line_counts() -> dict[str, int | None]:
    """`{釘選路徑: 當前行數}`（檔案不存在＝`None`）——SD-R60-08 的產生器側。

    WHY 由程式算而非寫在註解裡：行數是機器隨時算得出的量，寫進文件就會 stale
    （本檔原註解 8 支殼行數全數過期）。`--print-lines` 是唯一的取值介面。
    """
    counts: dict[str, int | None] = {}
    for rel in _PINNED_SHA256:
        path = ROOT / rel
        counts[rel] = len(_read_source(path).splitlines()) if path.is_file() else None
    return counts


def check_wrapper_thinness() -> list[str]:
    """回傳違規訊息清單；空清單＝全部通過。"""
    problems: list[str] = []
    for rel, pinned in _PINNED_SHA256.items():
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}：檔案不存在（wrapper 被移除或改名？）")
            continue
        line_count = len(_read_source(path).splitlines())
        if line_count > MAX_LINES:
            problems.append(
                f"{rel}：{line_count} 行超過薄殼上限 {MAX_LINES} 行 —— "
                f"業務邏輯應收斂進 tools/dev_start.py，不應長在 wrapper 內"
            )
        norm = normalized_content(path)
        actual = _sha256_text(norm)
        if actual != pinned:
            problems.append(
                f"{rel}：正規化內容 hash 與釘選不符（釘選 {pinned[:12]}… / 實際 "
                f"{actual[:12]}…）—— wrapper 實質內容變動；若變更仍屬「選直譯器／"
                f"轉呼叫核心／啟用 venv」薄殼職責，請以 --print-hash 取新值同步更新 "
                f"_PINNED_SHA256；否則請把邏輯收斂進 tools/dev_start.py"
            )
        # R60 Scan-E E-A-02：**並聯**（刻意不縮排進上方 if）。原本巢狀在 hash 已紅
        # 分支內＝串聯，一旦有人更新 pin（正常維護動作）整組偵測同時失效。比對
        # 對象為 `norm`（與 hash 同一份正規化文字），註解裡的字樣不誤判。
        for keyword in _FORBIDDEN.get(rel, ()):
            if keyword in norm:
                problems.append(
                    f"{rel}：出現禁止樣板關鍵字 {keyword!r} —— 疑似業務邏輯外溢回 "
                    f"wrapper（與 hash 釘選並聯的第三訊號，pin 已更新亦照樣攔下）；"
                    f"請把邏輯收斂進對應 Python 核心，若該關鍵字確屬本薄殼職責所需，"
                    f"請自 _FORBIDDEN[{rel!r}] 移除該字並就地註明 WHY"
                )
    return problems


#: 本工具接受的全部引數。**新增旗標時必須同步本元組**，否則它自己會被下面那道
#: 未知引數守衛擋下——刻意讓「加了旗標卻沒宣告」立刻可見，而不是靜默生效。
_KNOWN_ARGV: tuple[str, ...] = ("--print-hash", "--print-lines")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    # 未知引數 rc=2 fail-loud（R67-D20 射程擴張）：修前 `--bogus-flag-xyz` 會靜默掉進
    # 下方全檢查路徑並印綠燈 ⇒ 使用者以為自己下的旗標生效了。
    rc = _cli_flags.reject_unknown_argv("check_wrapper_thinness.py", args, _KNOWN_ARGV)
    if rc is not None:
        return rc
    if args == ["--print-hash"]:
        for rel in _PINNED_SHA256:
            path = ROOT / rel
            shown = normalized_sha256(path) if path.is_file() else "（檔案不存在）"
            print(f"{rel}: {shown}")
        return 0
    if args == ["--print-lines"]:
        print(f"# 薄殼行數現查（上限 MAX_LINES={MAX_LINES}）—— 勿把本輸出貼回原始碼註解")
        for rel, count in wrapper_line_counts().items():
            if count is None:
                print(f"{rel}: （檔案不存在）")
            else:
                print(f"{rel}: {count} / {MAX_LINES}（餘裕 {MAX_LINES - count}）")
        return 0
    problems = check_wrapper_thinness()
    if not problems:
        print(f"✅ wrapper 薄殼守門通過（{len(_PINNED_SHA256)} 支殼 hash 釘選 + 行數上限皆正常）")
        return 0
    print("❌ wrapper 薄殼守門失敗：")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
