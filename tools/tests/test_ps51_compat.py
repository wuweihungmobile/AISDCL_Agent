#!/usr/bin/env python3
"""Windows PowerShell 5.1 相容性行級機械守門（R56，SA／SD 掃描候選第 14 項落地）。

WHY：Windows 11 內建的是 **Windows PowerShell 5.1**（Desktop edition，隨 OS 凍結），
而本 repo 文件（`ONBOARDING.md`／`CLAUDE.md`／`docs/AISDLC_Agent_UserGuide.md`）教
使用者用的正是 `powershell -ExecutionPolicy Bypass -File …`＝5.1。PS 6/7-only 語法
（`??`／`?.`／`&&`／`||` 鏈接／`-AsHashtable`／`ForEach-Object -Parallel`／
`$IsWindows`…）在 5.1 上多半是 **parse error 或執行期才炸**，而既有防護全部驗不到：

  - `root-infra-ci.yml` 第 2 道的 `Parser::ParseFile` 跑在 `runs-on: ubuntu-latest`
    ＝PowerShell 7 Core 的 parser，結構上驗的是 7 的文法，不是 5.1 的。
  - `windows-compat-ci.yml` 在 windows-latest 上的**預設**引擎是 `shell: pwsh`
    （＝PowerShell 7 Core），少數刻意例外：windows-smoke 有走 `shell: bash` 的
    dispatcher hooks 步驟，windows-nightly-full 有走 `shell: powershell`（＝原生
    5.1）的步驟實跑 bootstrap.ps1／dev_start.ps1／install_post_commit.ps1。
    （R57 QA-R57-04 訂正：本段原文「全部 step 一律 `shell: pwsh`（＝7），只有
    windows-nightly-full 有**一支** `shell: powershell` 步驟」與 workflow 實況
    不符——bash 例外未提、5.1 步驟已不只一支。此處刻意不寫死各引擎的步驟支數，
    以免再次靜默過期；逐 job 的 shell 分佈以 workflow 檔本身為準。）
  - 其餘只有 `windows-compat-ci.yml` 檔頭 R5 段落的**人工宣稱**（當時列名七支
    「均未見 PS7-only 語法」），該宣稱立於 2026-07-14、13+ 輪未複驗，實測 active
    `.ps1` 已 21 支＝涵蓋率 7/21，且會隨新增檔案靜默過期。

平台待遇不對稱是本檔存在的直接理由：macOS 側的同構風險（系統 /bin/bash 3.2 vs
ubuntu bash 5.x）早已有 `tools/tests/test_bash32_compat.py` 機械鎖，Windows 側對應物
此前不存在。本檔骨架刻意鏡射該檔（行級 regex ＋ 剝註解/字串 ＋ per-tree 檔數下限
釘選 ＋ 行尾具名豁免 ＋ stale 自檢），維持兩平台守門同構、便於交叉覆核。

判準（行級 regex；先剝「註解 + 字串字面值 + here-string + 區塊註解」再掃）：
  A 語法/運算子組（5.1 直接 parse error）：`??`／`??=`／`?.`／`?[`／
    `&&`／`||` 管線鏈接運算子／`? :` 三元運算子
  B 參數/自動變數組（5.1 無此參數或變數 → 執行期炸或靜默取到 $null）：
    `-AsHashtable`／`-Parallel`／`-AsByteStream`／`-SkipHttpErrorCheck`／
    `utf8NoBOM`／`$IsWindows`|`$IsLinux`|`$IsMacOS`|`$IsCoreCLR`
  C PS6/7-only cmdlet：`Join-String`／`Get-Uptime`／`Test-Json`／`Get-Error`／
    `ConvertFrom-Markdown`／`Remove-Alias`／`Get-SecureRandom`

剝除策略（比 bash32 版**多剝字串**，刻意，非疏漏）：本 repo 的 `.ps1` 大量以字串
與 here-string **產生 bash 腳本內容**（`install_post_commit.ps1` 的 here-string 內就
有 `|| true`），只剝註解會立刻假紅。實測（2026-07-27，四棵樹 21 支）此策略零命中；
未剝字串則 4 筆偽陽性（2 筆 here-string 內的 bash `|| true`、2 筆變數名
`$utf8NoBom` 撞 `utf8NoBOM` 關鍵字——後者另以「前一字元不得為 `$`/單字元」的
negative lookbehind 收斂）。
代價（如實揭露）：真的寫在字串裡、之後 `Invoke-Expression` 執行的 PS7-only 語法
掃不到；行級 regex 無語法樹，屬 heuristic 邊界。該邊界的兩個**具名子情形**
（R56 round 5 由 QA／SD 實測補列，避免下一輪重新「發現」後誤判為新缺陷）：
  - here-string 誤啟（QA B-2）：`_HERE_STRING_RE` 只認 `@"`／`@'` 這兩個字元組合、
    不分辨其是否位於行尾。**行內**出現的 `@"`（如 `Write-Host "user@"`）或 `@'`
    （如 `.Split('@')`）會被當成 here-string 起點，一路吃到下一個行首 `"@`／`'@`，
    **遮蔽其間的真違規**（純函式探針實證：緊接其後一行的 `$IsWindows` 掃不到）。
    刻意不改 regex：實害目前為零（R56 round 5 訂正、分列口徑實測——四棵樹 21 支共
    3550 行中，**here-string 規則單獨**只清空 18 個非空行（span 19 行），
    block-comment 規則另清空 311 個非空行（span 362 行），兩者合計 329；原文把合計
    值 329 掛在「本規則」名下，把 here-string 規則的覆蓋面誇大約 17 倍。且
    **四棵樹掃描面內**「非行尾的 `@"`／`@'`」只有 2 處（LATEST 版
    `install_post_commit.ps1:116/117`），兩處都已落在既開啟的 here-string 區內；
    凍結版 v0.01~v0.29 的同名檔另有 47 處同形，惟凍結版不在掃描面內），
    而收緊判準所引入的偽陽性風險高於這個零實害的漏判。
  - 三元判準的 `?` 別名區辨（SD P3-SD-1）：實際把別名寫法擋在門外的是「同一行
    後方必須另有 ` : `」這個條件——PowerShell **程式碼**層級的「空白 冒號 空白」
    幾乎只出現在三元（`$env:X`／`C:\\`／`:label`／`${function:f}` 的冒號兩側都無
    空白）。`(?<!\\|)` 是額外的前瞻性防護（擋 `| ? { … }` 同行寫法），但**現行
    21 支 active `.ps1` 的 code 段連一處「空白 `?` 空白」都沒有**（2026-07-27
    實掃），故它今天不被任何真實檔案行使，偽陽性回歸鎖也**驗不到它**——如實記載，免得
    後續審查員誤以為該 lookbehind 已受測試保護（同輪 QA B-3 名實不符的教訓）。
    已知殘餘缺口（**偽陽性**方向）：管線換行後另起一行只寫 `? { … }`（行首無 `|`）
    且該行另含 ` : ` 時仍會偽陽性。
    已知殘餘缺口（**假陰性**方向。R56 round 5 SA 補列，round 6 Architect／SD／SA
    三方各自獨立以 pwsh 7.6.3 `Parser::ParseInput` + `FindAll(TernaryExpressionAst)`
    複驗、主控再親跑一次後訂正——原列的四例中有一例其實不成立，見下）：
    本判準 `(?<!\\|)\\s\\?\\s.*?\\s:\\s` 要求「`?` 後有空白**且**冒號兩側皆有空白」，
    但 PS7 語法不要求冒號兩側有空白——故下列**六例**皆為合法 `TernaryExpressionAst`
    （在 PS 5.1 必 parse error＝正是本鎖守備目標）卻**不命中**（兩項都實測過：
    pwsh AST errs=0／ternary=1，且本檔 `scan_source()` hits=0）：
    `$c ? 1:2`／`$c ?1 : 2`／`$c ? 1 :2`／`$c ? $a :$b`／`$c ? 1:$b`／`$c ? ($a):($b)`。
    **R56 round 7 二次訂正**：round 6 原列的第七例 `$c ? 'a':'b'` 其實**會命中**
    （`scan_source()` hits=1，`$x = $c ? "a":"b"`／`Write-Host ($c ? 'yes':'no')`
    亦同）——`split_code_comment()` 把字串字面值抹成等長空白後，該行變成
    `$x = $c ?  : `，反而製造出判準所需的 ` ? … : `。故「**兩分支皆為引號字串
    字面值**」的形態是**已被涵蓋**、不是缺口。此例由 Architect 與 QA 於 round 7
    各自獨立實測揪出，主控複驗確認（並發現自己首次複驗時把 `scan_source(source, rel)`
    的參數傳反、掃到檔名字串而得出全 0 的假結論——**驗證手法本身無鑑別力**的同型
    錯誤，同輪已在 venv 污染檢查上犯過一次，見帳本 DEF-101-461）。
    教訓：驗證「合法三元」（AST 面）與驗證「本鎖是否真的漏抓」（掃描器面）是
    **兩件事**，round 6 只驗了前者就下結論，故連續兩輪都在同一清單上出錯。
    **不需涵蓋、非缺口的三種形態**（實測皆非 `TernaryExpressionAst`）：
      - `$true?1:2` —— 全無空白，PS7 根本不解析為三元（errs=0／ternary=0）。
      - `$c ? $a:$b`／`$c ? $a: $b` —— 真值分支以**變數**結尾且緊接 `:` 時，
        `$a:` 被當成 scope-qualified 變數（`$scope:name`），PS7 本身即 parse error
        （errs=3／ternary=0：「Variable reference is not valid. ':' was not
        followed by a valid variable name character.」）。**R56 round 6 訂正**：
        此例原被誤列為假陰性，三方 AST 複驗證偽。留著會反向製造假缺口，誘使
        後續維護者去放寬 regex——而放寬正是下一段明確裁定不做的事，且 `$a:$b`
        恰恰就是那段所警告的 `$var:NAME` 形狀（自我矛盾）。
    故真正的判準不是「冒號兩側有無空白」，而是**冒號左側是否為變數**
    （`$c ? 1:$b` 成立、`$c ? $a:1` 不成立）。
    刻意不放寬冒號空白條件：實測放寬為 `\\s\\?\\s*.*?\\s*:\\s*` 雖對現行 21 支 active
    `.ps1` 仍零命中，但會讓 `… | ? { $_ -ne $env:TEMP }` 這類「Where-Object 別名
    ＋ `$env:X`」的同行寫法變成偽陽性，收緊代價高於收益。
    **因此檔頭「A 語法/運算子組」所列的 `? :` 僅涵蓋全空白形態**，非該禁令的完整
    機械化；`tools/windows_smoke_local.ps1` 檔頭列的 4 項禁令中，三元這一項仍部分
    依賴人工複核。

🔴 **本檔行級掃描架構上抓不到的一整類 5.1 缺陷（R71／DEF-101-760，誠實劃界）**：
「原生指令引數的引號傳遞」。Windows PowerShell 5.1 把參數交給**原生執行檔**
（非 cmdlet）時，會自行重組一次命令列字串再讓 `CommandLineToArgvW` 拆解，過程中
**吃掉字串內嵌的雙引號**（本機真機實測：送 `A""B`、收到 `AB`）。
`tools/lib/WindowsAppsGuard.ps1` 的版本探測碼原本寫 `else ""`，於是每個 Python 候選
都收到 `unterminated string literal` ⇒ rc=1 ⇒ `Get-PythonGeMin` 恆回 $null ⇒
全新 Windows 機器的 `dev_start.ps1` 開箱路徑整條是死的，而本檔 12 條判準**一條都
不會響**。原因是結構性的、不是漏列一條 regex：上方 `scan_source()` 掃的是
`split_code_comment()` **把字串字面值抹成空白之後**的 code 段，而缺陷本體就住在
那個被抹掉的字串裡——「加一條 regex 抓內嵌雙引號」在這個掃描器裡無從實作。
故該類別改由 `TestPs51NativeArgvRoundTrip` 以**真的起一支 powershell.exe 做 argv
round-trip** 看守（行為鎖，不是字面掃描）。

豁免機制：違規行行尾加註 `# ps7-ok: <WHY>`（WHY 必填，留空視同無豁免力）。
stale 自檢：帶標記的行掃不到任何被壓下的違規（已改寫／標記放錯行）→ fail-loud
指名該行請移除標記，防豁免清單腐化（語意對齊 bash4-ok／encoding-ok 慣例）。

掃描樹（四棵，與 `root-infra-ci.yml` 第 2 道 pwsh parse 同一組；皆遞迴）：
根 `tools/`、`AutoClaude/tools/`、`AISDLC_SDD/scripts/`、LATEST 版（LATEST 以
`scripts/sdd_version.py` SSOT subprocess 解析，失敗 fail-loud 不得縮面；凍結版
v0.01~v0.(N-1) 依鐵律不掃、也不可修）。per-tree 檔數下限釘選＝2026-07-27 實掃數
（8/7/2/4），防單樹靜默縮面；樹清單本體另由 `TestPs51ScanConfigPinning` 釘選。
"""
from __future__ import annotations

import platform
import re
import subprocess
import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_OK_MARKER = "ps7-ok:"

# R60 Scan-E E-A-01：掃描樹本體改取 SSOT（WHY 見該模組 docstring）。
sys.path.insert(0, str(_REPO_ROOT / "tools"))
from _script_scan_surface import (  # noqa: E402
    LATEST_TREE_KEY,
    SCRIPT_SCAN_ROOTS,
)

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

# （regex, 說明）；掃描對象為剝掉註解/字串後的 code 段
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # ── A 語法/運算子組（PS 5.1 parse error）─────────────────────────────────
    (re.compile(r"\?\?"), "?? / ??= null 合併運算子（PS 7.0+）"),
    (re.compile(r"\?\.|\?\["), "?. / ?[] null 條件成員存取（PS 7.1+）"),
    # R56 round 5 修正（SD P3-SD-1）：`windows_smoke_local.ps1:13` 自述禁令為 4 項
    # （`&&`/`||` 鏈接、**三元**、`??`、`?.`），本鎖原只涵蓋 3 項——而本鎖存在的
    # 理由正是「不再依賴人工宣稱」。`(?<!\|)` 排除 PS 5.1 合法的 `| ? { … }`
    # Where-Object 別名（其邊界見檔頭「代價」段）。實測 21 支 active .ps1 零命中。
    (
        re.compile(r"(?<!\|)\s\?\s.*?\s:\s"),
        "? : 三元運算子（PS 7.0+；5.1 的 `?` 是 Where-Object 別名 → parse error）",
    ),
    (re.compile(r"(?<![|&])&&(?!&)"), "&& 管線鏈接運算子（PS 7.0+；請用 if $LASTEXITCODE）"),
    (re.compile(r"(?<!\|)\|\|(?!\|)"), "|| 管線鏈接運算子（PS 7.0+；請用 if $LASTEXITCODE）"),
    # ── B 參數/自動變數組（PS 5.1 無此參數/變數）──────────────────────────
    (re.compile(r"-AsHashtable\b", re.I), "-AsHashtable（ConvertFrom-Json，PS 6.0+）"),
    (re.compile(r"-Parallel\b", re.I), "ForEach-Object -Parallel（PS 7.0+）"),
    (re.compile(r"-AsByteStream\b", re.I), "-AsByteStream（Get/Set-Content，PS 6.0+；5.1 用 -Encoding Byte）"),
    (re.compile(r"-SkipHttpErrorCheck\b", re.I), "-SkipHttpErrorCheck（Invoke-WebRequest，PS 7.0+）"),
    (re.compile(r"(?<![$\w])utf8NoBOM", re.I), "-Encoding utf8NoBOM（PS 6.0+；5.1 需 UTF8Encoding($false)）"),
    (
        re.compile(r"\$Is(Windows|Linux|MacOS|CoreCLR)\b", re.I),
        "$IsWindows/$IsLinux/$IsMacOS/$IsCoreCLR 自動變數（PS 6.0+；5.1 恆 $null → 判斷靜默走錯分支）",
    ),
    # ── C PS6/7-only cmdlet ───────────────────────────────────────────────
    (
        re.compile(
            r"\b(Join-String|Get-Uptime|Test-Json|Get-Error|ConvertFrom-Markdown"
            r"|Remove-Alias|Get-SecureRandom)\b",
            re.I,
        ),
        "PS 6/7-only cmdlet（5.1 無此指令）",
    ),
]

_BLOCK_COMMENT_RE = re.compile(r"<#.*?#>", re.DOTALL)
# here-string：`@"` … 行首 `"@`（與 `@'` … 行首 `'@`）。替換為等量換行以保住行號。
_HERE_STRING_RE = re.compile(r"@([\"'])[\s\S]*?^\1@", re.MULTILINE)


def _latest_root() -> Path:
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。委派
    tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")


def _git_tracked_ps1(rel_prefix: str) -> list[str]:
    """該樹下 git-tracked `*.ps1` 相對路徑（git 失敗即 AssertionError）。"""
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false",
         "ls-files", "--", f"{rel_prefix}/*.ps1"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（{rel_prefix}；rc={proc.returncode}；"
            f"stderr={proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return sorted(line for line in proc.stdout.splitlines() if line)


# per-tree 檔數下限＝2026-07-27 實掃數，刻意留在本檔（各鎖自己的靈敏度參數，非共用
# 掃描面定義——見 `tools/_script_scan_surface.py` docstring「不收錄什麼」）。三棵固定樹
# 的**樹名本體**自 R60 Scan-E E-A-01 起取自 SSOT；SSOT 新增一棵樹而本表未同步時
# `_TREE_FLOORS[root]` 直接 KeyError＝fail-loud，不會靜默把新樹當 floor 0 放過。
_TREE_FLOORS = {
    "tools": 8,
    # AutoClaude/tools：R76 由 7 下修為 6——reschedule_g0_gatecheck.ps1 整支刪除
    # （真孤兒，它要重排的 AutoClaude_SD09_G0_GateCheck 於 R71 已從本機移除）。
    "AutoClaude/tools": 6,
    "AISDLC_SDD/scripts": 2,
    LATEST_TREE_KEY: 4,
}


def scan_trees() -> list[tuple[str, list[str], int]]:
    """（樹 key, `.ps1` 相對路徑清單, 檔數下限）。LATEST key 正規化為 `LATEST`，
    升版（Copy-on-Evolve 建 v0.(N+1)）不失效。

    R60 Scan-E E-A-01：三棵固定樹改由 `tools/_script_scan_surface.SCRIPT_SCAN_ROOTS`
    SSOT 提供（原為本檔自持字面值），與 `tools/check_script_parity.py` 的 enrollment
    掃描面同源；形狀一致性另由 `test_script_scan_surface_ssot.py` 機械斷言。
    """
    latest = _latest_root()
    specs = [(root, root, _TREE_FLOORS[root]) for root in SCRIPT_SCAN_ROOTS]
    specs.append(
        (LATEST_TREE_KEY, f"AISDLC_SDD/{latest.name}", _TREE_FLOORS[LATEST_TREE_KEY])
    )
    return [(key, _git_tracked_ps1(prefix), floor) for key, prefix, floor in specs]


def _strip_text_level(text: str) -> str:
    """剝區塊註解與 here-string；以等量換行取代，保住行號對應。"""
    text = _BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _HERE_STRING_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def split_code_comment(line: str) -> tuple[str, str]:
    """單行拆（code 段, 註解段）；code 段內的字串字面值一併以空白取代。

    PowerShell 字串規則：單引號內無跳脫（`''` 為字面單引號）；雙引號內以反引號
    `` ` `` 跳脫（`""` 亦為字面雙引號）。`#` 僅在引號外且位於字首或
    空白/`;`/`|`/`(`/`{`/`,` 之後才算註解起點（避免誤剝 `$#`、`c#` 這類字元）。
    """
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "'":
            i += 1
            while i < n:
                if line[i] == "'":
                    if i + 1 < n and line[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append(" ")
            continue
        if ch == '"':
            i += 1
            while i < n:
                if line[i] == "`":
                    i += 2
                    continue
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append(" ")
            continue
        if ch == "#":
            prev = out[-1] if out else ""
            if prev in ("", " ", "\t", ";", "|", "(", "{", ","):
                return "".join(out), line[i:]
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), ""


def scan_source(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心（供直接單元測試）：回傳 (offenders, stale_markers)。

    stale＝標記存在但該行沒有被壓下的違規（含 WHY 留空）→ 必須清掉或補 WHY。
    """
    offenders: list[str] = []
    stale: list[str] = []
    for lineno, line in enumerate(_strip_text_level(source).splitlines(), start=1):
        code, comment = split_code_comment(line)
        why: str | None = None
        if _OK_MARKER in comment:
            why = comment.split(_OK_MARKER, 1)[1].strip()
        hits = [desc for pattern, desc in _PATTERNS if pattern.search(code)]
        if hits:
            if why:
                continue
            offenders.extend(
                f"{rel}:{lineno}: {desc}（Windows PowerShell 5.1 不相容）" for desc in hits
            )
            if why is not None:
                stale.append(f"{rel}:{lineno}: ps7-ok 標記 stale（WHY 留空，無豁免力）")
        elif why is not None:
            stale.append(f"{rel}:{lineno}: ps7-ok 標記 stale（該行無被壓下的違規）")
    return offenders, stale


# R56 round 6（QA B-1）：CI 第 2 道掃描樹抽取式。字元類必須容納 `.`／`-`，
# 否則 `.github/scripts` 這類路徑被插進 CI 時本鎖靜默失效（實測 11 支全綠）。
# R57 修正（A2）：抽取式與計數錨原本在本檔／test_ps1_bom／test_smoke_ci_sync 三份
# 逐字複製且皆硬綁 `-Path` 具名參數，位置參數形態（`-Path` 省略）可完全繞過；
# 已收斂進 `_ci_scan_anchors` SSOT（WHY 見該模組 docstring）。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ci_scan_anchors import (  # noqa: E402
    EXPECTED_CI_GCI_CALLS,
    EXPECTED_CI_SCAN_STATEMENTS,
    ci_fixed_trees,
    ci_gci_call_count,
    ci_scan_statement_count,
)


class TestPs51Compat(unittest.TestCase):
    def test_active_ps1_trees_have_no_ps7_only_usage(self) -> None:
        """四棵樹 active `.ps1` 不得使用 PS 6/7-only 語法（per-tree 下限釘選防縮面）。"""
        offenders: list[str] = []
        stale: list[str] = []
        read_failures: list[str] = []
        for key, files, floor in scan_trees():
            self.assertGreaterEqual(
                len(files), floor,
                f"掃描樹 {key} 只找到 {len(files)} 支 .ps1 < 下限 {floor}——目錄搬家或"
                f"ls-files 樣式疑似被改壞（靜默縮面）；刻意刪減請同步下修 scan_trees()",
            )
            for rel in files:
                try:
                    source = (_REPO_ROOT / rel).read_text(encoding="utf-8-sig")
                except (OSError, UnicodeDecodeError) as exc:
                    read_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
                    continue
                off, st = scan_source(source, rel)
                offenders.extend(off)
                stale.extend(st)
        self.assertEqual(
            read_failures, [],
            f"讀檔失敗（不得靜默跳過，否則等同縮面）：{read_failures}",
        )
        self.assertEqual(
            offenders, [],
            "偵測到 Windows PowerShell 5.1 不相容寫法（文件教使用者用的正是 5.1；"
            "CI 的 pwsh parser 是 7，驗不到）——確有必要請於該行行尾加 "
            "`# ps7-ok: <WHY>`：\n  " + "\n  ".join(offenders),
        )
        self.assertEqual(
            stale, [],
            "ps7-ok 豁免標記已 stale（該行無被壓下的違規，或 WHY 留空）——請移除"
            "標記或補 WHY，防豁免清單腐化：\n  " + "\n  ".join(stale),
        )

    def test_scan_source_detects_each_pattern(self) -> None:
        """鑑別力自檢：每條判準至少有一個最小樣本會被抓到（regex 寫壞即紅）。

        Rule 9（測意圖非僅行為）：上一支測試在乾淨的樹上恆綠，本身無法證明
        regex 還活著——R43/R56 都實證過「防增生鎖看似綠燈實則零訊號」。
        """
        samples = [
            "$x = $a ?? $b",
            "$x = $a?.Length",
            "$x = $c ? 'a' : 'b'",
            "$x = $c ? 1 : 2",
            # R56 round 7（Architect／QA／SD 三方交叉發現）：兩分支皆為引號字串
            # 字面值的三元**會被涵蓋**，但那是 `split_code_comment()` 把字串抹成
            # 空白後意外製造出 ` ? … : ` 的副作用，非判準本意。釘成常駐樣本，
            # 免得日後把字串替換成「空字串」而非「空白」時這份覆蓋靜默消失。
            "$x = $c ? 'a':'b'",
            "git status && echo ok",
            "git status || echo bad",
            "$h = $j | ConvertFrom-Json -AsHashtable",
            "1..3 | ForEach-Object -Parallel { $_ }",
            "Get-Content f -AsByteStream",
            "Invoke-WebRequest $u -SkipHttpErrorCheck",
            "Set-Content f -Encoding utf8NoBOM",
            "if ($IsWindows) { 1 }",
            "$s = 1,2 | Join-String -Separator ,",
        ]
        for line in samples:
            off, _stale = scan_source(line + "\n", "sample.ps1")
            self.assertNotEqual(
                off, [], f"判準失效：樣本未被偵測到 → {line!r}（regex 疑似寫壞/被刪）"
            )

    def test_string_and_here_string_content_is_not_flagged(self) -> None:
        """偽陽性回歸鎖：字串/here-string 內產生 bash 內容不得誤判。

        錨定 R56 實測到的四筆偽陽性形狀（否則本鎖第一天就假紅，見檔頭）。
        """
        cases = [
            '$utf8NoBom = New-Object System.Text.UTF8Encoding($false)',
            '$bytes = $utf8NoBom.GetBytes($Content)',
            'Write-Host "bash 寫法是 cmd || true"',
            "$c = @\"\n\"`$PY\" \"$Hook\" \"`$@\" || true\n\"@\n",
        ]
        for src in cases:
            off, _stale = scan_source(src + "\n", "sample.ps1")
            self.assertEqual(
                off, [], f"偽陽性：字串/here-string 內容被誤判 → {src!r}；命中={off}"
            )

    def test_ternary_pattern_does_not_flag_where_object_alias(self) -> None:
        """R56 round 5 新增：三元判準的偽陽性回歸鎖（獨立於上一支 string/here-string
        版——名實相符，見 TestPs51ScanConfigPinning 同輪修正的 QA B-3 教訓）。

        `?` 在 PS 5.1 是 `Where-Object` 的合法別名；三元判準若寫得太寬會把這些行
        一次打成假紅、逼人加豁免標記，整把鎖的可信度就沒了。本測試釘住「別名寫法
        不得命中」這個意圖。

        **本鎖的鑑別力邊界（如實揭露，bug-injection 實測而非推測）**：真正被鎖住的
        是判準中「同一行後方必須另有 ` : `」這個條件——把它拿掉（判準退化為
        `\\s\\?\\s`）本測試立刻紅。前綴的 `(?<!\\|)` lookbehind **驗不到**：下方每個
        別名樣本都沒有 code 段的 ` : `，拿掉 lookbehind 後仍全綠（實測 failures=0）。
        故 lookbehind 屬前瞻性防護、非本測試的保護標的，詳見檔頭「代價」段。
        """
        cases = [
            "Get-Item | ? { $_.Name -eq 'x' }",
            "Get-ChildItem | ? Name -eq 'x'",
            # 刻意用「`|` 與 `?` 之間兩個空白」：lookbehind 看的是 `?` 前那一個
            # 空白字元的前一字元（此時是空白、不是 `|`），故本樣本繞過 lookbehind、
            # 只靠 ` : ` 條件擋下——它就是上面所說「有牙齒」的那一個。
            "Get-ChildItem |  ? { $_.Name -eq 'x' }",
            "$h = @{ a = 1 }",
            "$script:Total = $script:Total + 1",
        ]
        for src in cases:
            off, _stale = scan_source(src + "\n", "sample.ps1")
            self.assertEqual(
                off, [], f"偽陽性：PS 5.1 合法寫法被三元判準誤判 → {src!r}；命中={off}"
            )

    def test_ok_marker_exempts_and_stale_marker_is_reported(self) -> None:
        """豁免與 stale 自檢雙向：帶 WHY 的標記壓下違規；空 WHY／無違規即列 stale。"""
        off, stale = scan_source("git a && git b  # ps7-ok: 僅在 nightly 的 pwsh7 內執行\n", "s.ps1")
        self.assertEqual((off, stale), ([], []), "帶 WHY 的 ps7-ok 標記應完全豁免該行")

        off, stale = scan_source("git a && git b  # ps7-ok:\n", "s.ps1")
        self.assertNotEqual(off, [], "WHY 留空的標記不得有豁免力")
        self.assertTrue(any("WHY 留空" in s for s in stale), f"應列為 stale：{stale}")

        off, stale = scan_source("Write-Host ok  # ps7-ok: 已改寫但標記沒清\n", "s.ps1")
        self.assertEqual(off, [])
        self.assertTrue(any("無被壓下的違規" in s for s in stale), f"應列為 stale：{stale}")


class TestPs51ScanConfigPinning(unittest.TestCase):
    def test_tree_keys_and_floors_pinned(self) -> None:
        """樹清單本體＋per-tree 下限釘選——刪掉 scan_trees() 一列整棵樹會靜默出界，
        且上一支測試仍全綠（同 test_bash32_compat.TestScanConfigPinning 的存在理由）。

        R56 round 5 修正（QA B-3）：本方法名為 `keys_and_floors_pinned`，實作卻只
        比 keys、`_floor` 從未進入斷言——名實不符會誤導後續審查員以為下限已受保護
        （現況 8/7/2/4 與實數零餘裕，縮面雖仍會被上一支測試的 assertGreaterEqual
        擋下，但「下限值本身被下修」這條路徑當時零訊號）。改為連 floor 一起釘。
        """
        keys_floors = [(key, floor) for key, _files, floor in scan_trees()]
        self.assertEqual(
            keys_floors,
            # R76：AutoClaude/tools 由 7 下修為 6（reschedule_g0_gatecheck.ps1 整支刪除，
            # 真孤兒）——第三份硬編實作在 tools/windows_smoke_local.ps1 [1/9] $ps1Trees，已同步。
            [("tools", 8), ("AutoClaude/tools", 6), ("AISDLC_SDD/scripts", 2), ("LATEST", 4)],
            "掃描樹清單或 per-tree 檔數下限被改動——四棵樹必須與 root-infra-ci.yml "
            "第 2 道 pwsh parse 的掃描面一致（該 step 是本鎖在 CI 上的姊妹守門），"
            "下限值則與 tools/windows_smoke_local.ps1 [1/9] 的 $ps1Trees Floor 逐值"
            "相同（見 tools/tests/test_smoke_ci_sync.py 的三向鎖）；刻意調整請同步四處樹清單站點（下限值僅本檔與 $ps1Trees 兩處持有，另見 test_ps1_bom._scan_prefixes()）",
        )

    def test_tree_set_matches_root_infra_ci_pwsh_step(self) -> None:
        """與 root-infra-ci.yml 第 2 道的掃描面機械互鎖：該 step 以
        `Get-ChildItem -Path <樹>` 列舉，本鎖的樹清單必須是同一組（LATEST 以
        `sdd_version.py` 解析的動態路徑，比對時正規化為佔位符）。"""
        ci = (_REPO_ROOT / ".github" / "workflows" / "root-infra-ci.yml").read_text(
            encoding="utf-8"
        )
        step = re.search(
            r"^ +- name: pwsh 語法解析.*?(?=^ +- name: )", ci, re.MULTILINE | re.DOTALL
        )
        self.assertIsNotNone(step, "root-infra-ci.yml 找不到 pwsh 語法解析 step——結構已變動")
        # R56 round 6 修正（QA B-1）：字元類擴充納入 `.`／`-`，堵住「含點路徑的第 5
        # 棵樹插進 CI 卻完全隱形」的 fail-open（下方等值斷言即為數量下限）。
        paths = ci_fixed_trees(step.group(0))
        # R60 Scan-E E-A-01：期望值改引 `_script_scan_surface.SCRIPT_SCAN_ROOTS` SSOT
        # （原為本檔第三份硬編字面集合）。這一行同時是 E-A-01 要求的**形狀一致性鎖**
        # ——`tools/check_script_parity.py` 的 enrollment 掃描面自此與 CI 第 2 道共用
        # 同一份名冊，任一方增刪樹即在此翻紅。本鎖刻意放在本檔而非另立新檔：本檔已是
        # `_ci_scan_anchors` 的登記呼叫端（`test_ci_scan_anchors._SSOT_CALLERS`）且已
        # 接滿三條抽取錨，另立第 4 份呼叫端只會複製同一組錨、重演 R56 的三複本盲點。
        self.assertEqual(
            paths, set(SCRIPT_SCAN_ROOTS),
            f"root-infra-ci.yml 第 2 道的固定掃描樹已變動：{sorted(paths)}"
            f"（SSOT 名冊＝{sorted(SCRIPT_SCAN_ROOTS)}）——本鎖與該 step 自述同掃描面，"
            f"且 check_script_parity 的 enrollment 面同源，任一方增刪必須同步",
        )
        # R56 round 7 修正（Architect F2 ／ QA ② 交叉發現）：上面的 `len(ci_trees)`
        # 等值斷言只對「_CI_TREE_RE 抽得到的樹」有效，對「抽不到的形態」天生零訊號
        # ——實測 `-Path "docs/scripts"`（引號界定）與 `-Path (Join-Path ".github"
        # "scripts")`（計算式，該 step 第 4 棵樹就是這種寫法、照抄最自然）插入第 5 棵
        # 樹時三支鎖全綠。故補一條**與字元類完全無關**的出現次數斷言。（round 6 宣稱
        # 「補抽取數量下限堵 fail-open」不精確——QA 實證那條下限被既有 set-equality
        # 涵蓋、是冗餘的，真正生效的只有字元類擴充。）
        # R57 訂正（A2）：round 7 原文宣稱「不論路徑長什麼樣，多一棵樹必紅」是**假
        # 宣稱**——舊錨硬綁 `-Path` 具名參數，而它是 PowerShell 位置參數可省略；實測
        # 插入 `Get-ChildItem docs/scripts -Recurse -Filter *.ps1 -File` 時三份共 20 支
        # 測試仍全綠。改錨 `-Recurse -Filter *.ps1 -File`：因尾巴不含路徑，故涵蓋
        # 具名/位置/引號/Join-Path 計算式任一種路徑寫法；但 filter 自身加引號、改用
        # -Include、三參數順序對調則抓不到（由下方 cmdlet 計數錨兜底）。
        self.assertEqual(
            ci_scan_statement_count(step.group(0)), EXPECTED_CI_SCAN_STATEMENTS,
            "root-infra-ci.yml 第 2 道的 `.ps1` 遞迴掃描語句數已變動（預期 4＝三棵固定樹＋LATEST 計算式樹）——本斷言涵蓋具名/位置/引號/Join-Path 任一種路徑寫法，請同步四處樹清單站點",
        )
        # R57 四方複審 ARCH-01 訂正：上一版在此寫「任何參數形態的掃描樹增刪都會命中」
        # 是假宣稱——實測 `-Filter "*.ps1"`／`-Include *.ps1`／`gci` 別名／`-Filter`
        # 寫在 `-Recurse` 前，四種形態全部逃逸，其中三種還是 R56 舊錨抓得到的＝淨退化。
        # R57 round 2 ARCH-01 再訂正：三條錨原本大小寫敏感，`get-childitem …
        # -recurse -filter *.ps1 -file` 全小寫實測全綠逃逸；SSOT 已加 re.IGNORECASE。
        self.assertEqual(
            ci_gci_call_count(step.group(0)), EXPECTED_CI_GCI_CALLS,
            "root-infra-ci.yml 第 2 道的 Get-ChildItem（含 gci/dir/ls 別名，皆不分大小寫）出現次數已變動（預期 4）——本斷言不解析參數，已實測涵蓋：引號 filter／-Include／參數重排／Join-Path 計算式路徑／全小寫或全大寫寫法；已實測不涵蓋（未窮舉）：[System.IO.Directory]::GetFiles、Get-Item、Resolve-Path 這三種非 Get-ChildItem 列舉途徑；整行 # 註解由 SSOT 統一剝除故不計入",
        )
        self.assertIn(
            'Join-Path "AISDLC_SDD" $latestName', step.group(0),
            "root-infra-ci.yml 第 2 道未見 LATEST 樹（Join-Path AISDLC_SDD $latestName）"
            "——第 4 棵樹疑似被移除",
        )


# ─────────────────────────────────────────────────────────────────────────────
# R71（DEF-101-760）：「原生指令引數的引號傳遞」行為鎖。
#
# WHY 是行為鎖而不是第 13 條 regex：見檔頭同名段落——缺陷住在字串字面值裡，而本檔
# 的掃描器在比對前就把字串抹成空白了，結構上看不見。ADR-XPLAT-002 §3.2 的紀律
# 也指同一件事：字面比對型 parity 不算機械釘選，`.ps1` 得真的被執行過。
# ─────────────────────────────────────────────────────────────────────────────

sys.path.insert(0, str(_TESTS_DIR))
from _ps_engine import native_ps51, windows_with_native_ps51  # noqa: E402

_GUARD_PS1 = _REPO_ROOT / "tools" / "lib" / "WindowsAppsGuard.ps1"

# 回聲程式：把收到的第一個「-c 之後的位置引數」原封不動寫回 stdout（不加換行，
# 免得比對還要處理行尾）。**本身刻意不含任何引號字元**——載具若自己踩進待測的
# 缺陷，量到的就是載具的假紅（R71 實測踩過一次：`print("MM=%d.%d" % …)` 當場
# 被吃掉引號變成 `SyntaxError`）。
_ARGV_ECHO = "import sys;sys.stdout.write(sys.argv[1])"

# 明知會被 5.1 吃掉的樣本（負控用）。`A""B` 在 PowerShell 單引號字串裡是逐字四字元。
_QUOTE_BEARING_SAMPLE = 'A""B'


def _parse_sent_got(stdout: str) -> tuple[str, str]:
    """從 `SENT=`／`GOT=` 兩行取回原值與回聲值（缺行即 KeyError，由呼叫端 fail-loud）。"""
    found: dict[str, str] = {}
    for line in stdout.splitlines():
        for key in ("SENT=", "GOT="):
            if line.startswith(key):
                found[key.rstrip("=")] = line[len(key):]
    return found["SENT"], found["GOT"]


@unittest.skipUnless(
    windows_with_native_ps51(),
    "[WINDOWS-NATIVE-ONLY] 需要 Windows 真機上的原生 powershell.exe（5.1）："
    "本鎖量的是 5.1 專屬的原生引數重組行為，pwsh 7.3+ 已改用新的 argv 傳遞、"
    "在它身上跑會恆綠＝零鑑別力（刻意不 fallback，理由同 _ps_engine 語意④）",
)
class TestPs51NativeArgvRoundTrip(unittest.TestCase):
    """交給原生 exe 的生產字串，必須原封不動抵達對方的 `argv`。

    誠實劃界：本鎖**只在 Windows 原生 5.1 上有鑑別力**，macOS/Linux 一律 skip。
    恆會執行的靜態備援＝`tools/tests/test_dev_start.py::TestMinPythonVersionSsotSync
    ::test_version_probe_has_no_embedded_double_quote`（不需要任何引擎）。兩者是
    「行為證據」與「不依賴環境的近似」的分工，缺一都會退回 DEF-101-760 的狀態。
    """

    def _round_trip(self, ps_expr_defining_sent: str):
        """跑一次 round-trip；`ps_expr_defining_sent` 需把待測字串放進 `$sent`。"""
        snippet = (
            f"{ps_expr_defining_sent} "
            f"$got = & '{sys.executable}' -c '{_ARGV_ECHO}' $sent; "
            "'SENT=' + $sent; 'GOT=' + $got"
        )
        proc = subprocess.run(
            [native_ps51(), "-NoProfile", "-Command", snippet],
            capture_output=True, encoding="utf-8", errors="replace", timeout=180,
        )
        self.assertEqual(proc.returncode, 0, f"載具故障：stderr={proc.stderr!r}")
        try:
            return _parse_sent_got(proc.stdout)
        except KeyError as exc:  # pragma: no cover - 載具壞掉才會走到
            raise AssertionError(
                f"載具故障：stdout 缺 {exc} 行（不得當成通過）\nstdout={proc.stdout!r}"
            ) from exc

    def test_production_version_probe_survives_native_argv_round_trip(self) -> None:
        """本體：生產探測碼交給 python.exe 後，`sys.argv` 收到的必須逐字相同。

        刻意 dot-source **真的**那支 `WindowsAppsGuard.ps1` 並取 `$script:
        PythonGeMinProbe`，而不是在本檔複製一份字面值——複製品會與生產值漂移，
        鎖就變成在驗自己（同 ADR-XPLAT-002 §3.2 對「兩邊都寫了看起來很像的東西」
        的裁定）。
        """
        sent, got = self._round_trip(f". '{_GUARD_PS1}'; $sent = $script:PythonGeMinProbe;")
        self.assertTrue(sent, "沒讀到 $script:PythonGeMinProbe——宣告被改名？")
        self.assertEqual(
            got, sent,
            "生產探測碼在 PS 5.1 → 原生 exe 的邊界上被改寫了（典型是內嵌雙引號被吃掉"
            "一個）。後果：python 收到語法錯誤的程式碼 → rc=1 → Get-PythonGeMin 的"
            "每個候選都被判不合格 → 恆回 $null → 全新 Windows 機器 dev_start.ps1 "
            "開箱路徑整條死掉（DEF-101-760）。修法：字串內不要用雙引號，空字串寫 "
            f"`str()`。\n  送出：{sent!r}\n  收到：{got!r}",
        )

    def test_carrier_has_teeth_embedded_double_quotes_really_are_eaten(self) -> None:
        """負控（鏡子自證）：明知有害的樣本必須真的被改寫，否則上一支恆綠。

        沒有這一支，上一支在「載具其實根本沒走到原生邊界」時同樣是綠的——那正是
        DEF-101-760 能出貨的原因（唯一有行為鑑別力的鎖被 skip 在門外，剩下的全是
        文字比對）。本測試把「這個危害在本機仍然存在」變成可觀測的事實。
        """
        sent, got = self._round_trip(f"$sent = '{_QUOTE_BEARING_SAMPLE}';")
        self.assertEqual(sent, _QUOTE_BEARING_SAMPLE, f"載具沒送對樣本：{sent!r}")
        self.assertNotEqual(
            got, sent,
            "PS 5.1 竟原封不動傳遞了內嵌雙引號——本鎖假設的危害不存在了（引擎換版？）"
            "；請重新量測並改寫本檔檔頭的判斷，不要留一支恆綠的鎖",
        )
        self.assertNotIn(
            '"', got,
            f"實測形態變了：雙引號沒有被完全吃掉（送 {sent!r} 收 {got!r}）"
            "——上一支主鎖的診斷訊息需同步更新",
        )


class TestPs51BehaviouralLockCannotSilentlyVanish(unittest.TestCase):
    """R71：`TestPs51NativeArgvRoundTrip` 的 skip 述詞在 Windows 上**不得**成立。

    WHY（本鎖補的是上面那把鎖自己的 fail-open）：`TestPs51NativeArgvRoundTrip` 是本
    repo 唯一具**行為**鑑別力的 PS 5.1 守門，而它掛在 `skipUnless(windows_with_native_
    ps51())` 上。該述詞 ＝「在 Windows」且「`shutil.which('powershell')` 命中」——後者
    一旦因 PATH 被改、映像變更、或 System32 被移出搜尋路徑而落空，整把鎖就**靜默 skip**：
    `run_root_unittests.py` 只會多印一行 `[WINDOWS-NATIVE-ONLY]` 明細，rc 仍為 0。
    也就是說「唯一的行為鎖消失」這件事在本 repo 現行機制下**不會變紅**——這正是
    DEF-101-760 得以出貨的那個形狀（唯一有鑑別力的鎖被 skip 在門外，剩下的全是文字比對），
    只是換成從環境側觸發。

    判準邊界（誠實劃界）：本鎖只在 Windows 上說話。非 Windows 平台沒有 5.1、skip 是
    正確語意，不是覆蓋損失（該方向的可見度由 `run_root_unittests.report_all_skips`
    承接）。本鎖也不驗那支測試「跑完是對的」，只驗它**不會沒跑**。
    """

    @unittest.skipUnless(
        platform.system() == "Windows",
        "[WINDOWS-NATIVE-ONLY] 本鎖問的是「Windows 上 5.1 行為鎖有沒有被 skip 掉」，"
        "非 Windows 平台不適用（該平台上 skip 是正確語意，不是覆蓋損失）",
    )
    def test_native_ps51_predicate_holds_on_windows(self) -> None:
        self.assertTrue(
            windows_with_native_ps51(),
            "本機是 Windows，卻解析不到原生 powershell.exe ⇒ "
            "TestPs51NativeArgvRoundTrip（唯一具行為鑑別力的 PS 5.1 守門）本次被靜默 "
            "skip，PS 5.1 覆蓋退回純靜態掃描。powershell.exe 是 Windows 內建、且是本 "
            "repo 文件教使用者用的引擎，解析不到代表 PATH 已壞（典型：System32 被移出 "
            "PATH）——請修環境，不要改本鎖的述詞",
        )


if __name__ == "__main__":
    unittest.main()
