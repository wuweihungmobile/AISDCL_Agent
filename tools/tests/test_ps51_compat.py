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
    （**R57 QA-R57-04 訂正**了本段原文的過期宣稱；該訂正史料逐字遷至
    `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md` §A-1。此處刻意不寫死
    各引擎的步驟支數，逐 job 的 shell 分佈一律以 workflow 檔本身為準。）
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
有 `|| true`），只剝註解會立刻假紅。
代價（如實揭露）：真的寫在字串裡、之後 `Invoke-Expression` 執行的 PS7-only 語法
掃不到；行級 regex 無語法樹，屬 heuristic 邊界。該邊界的兩個**具名子情形**
（here-string 誤啟 QA B-2／三元 `?` 別名區辨 SD P3-SD-1）的判讀史、逐項實測數字，
以及「刻意不改 regex／不放寬冒號空白條件」的理由，**逐字遷至**
`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md` §A-1；判準本體一行都沒動。
  - 三元判準的 `?` 別名區辨（SD P3-SD-1）：判讀史逐字遷至 §A-1（見上）。結論一句話：
    真正的判準不是「冒號兩側有無空白」，而是**冒號左側是否為變數**。

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
    PS1_TREE_FLOORS,
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


# per-tree 檔數下限。R79 ARCH：本表原為本檔自持的字面值（理由「各鎖自己的靈敏度
# 參數」），已收進 `tools/_script_scan_surface.PS1_TREE_FLOORS` SSOT——原理由在
# `windows_smoke_local.ps1` [1/9] 與 CI 第 2 道改為共用同一份列舉器之後不再成立：
# 下限若分散兩處，就得再養一道「兩份下限同步」的鎖，正是 R79 要消滅的形態。
# SSOT 新增一棵樹而下限表未同步時 `PS1_TREE_FLOORS[root]` 直接 KeyError＝fail-loud。
_TREE_FLOORS = PS1_TREE_FLOORS


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


# R79 ARCH：本處原 import `_ci_scan_anchors` 的三條正則錨，用來比對「CI 第 2 道
# 自己列舉的掃描樹」是否與本檔一致。CI 第 2 道已改為呼叫 `_script_scan_surface.py`
# SSOT，複本消失 ⇒ 沒有東西可比對，那組錨（866 行）連同它自承的三種逃逸形態一併
# 退場。剩下的唯一義務「兩個非 Python 站點真的呼叫 SSOT 且沒有自持第二份列舉」由
# `test_script_scan_surface_ssot.TestNonPythonSitesCallTheSsot` 單點守住。


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
            "掃描樹清單或 per-tree 檔數下限被改動——四棵樹與下限值自 R79 起只有一個"
            "持有者（`tools/_script_scan_surface.py` 的 `SCRIPT_SCAN_ROOTS` ＋ "
            "`PS1_TREE_FLOORS`），root-infra-ci.yml 第 2 道與 tools/windows_smoke_local.ps1 "
            "[1/9] 皆呼叫該 SSOT 取得掃描面；本鎖釘的是 SSOT 值本身（刻意調整時改這一行），"
            "「兩個非 Python 站點真的在呼叫 SSOT」則由 test_script_scan_surface_ssot 守",
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
