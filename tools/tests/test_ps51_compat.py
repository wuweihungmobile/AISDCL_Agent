#!/usr/bin/env python3
"""Windows PowerShell 5.1 相容性行級機械守門（R56，SA／SD 掃描候選第 14 項落地）。

WHY：Windows 11 內建的是 **Windows PowerShell 5.1**（Desktop edition，隨 OS 凍結），
而本 repo 文件（`ONBOARDING.md`／`CLAUDE.md`／`docs/AISDLC_Agent_UserGuide.md`）教
使用者用的正是 `powershell -ExecutionPolicy Bypass -File …`＝5.1。PS 6/7-only 語法
（`??`／`?.`／`&&`／`||` 鏈接／`-AsHashtable`／`ForEach-Object -Parallel`／
`$IsWindows`…）在 5.1 上多半是 **parse error 或執行期才炸**，而既有防護全部驗不到：

  - `root-infra-ci.yml` 第 2 道的 `Parser::ParseFile` 跑在 `runs-on: ubuntu-latest`
    ＝PowerShell 7 Core 的 parser，結構上驗的是 7 的文法，不是 5.1 的。
  - `windows-compat-ci.yml` 全部 step 一律 `shell: pwsh`（＝7），只有
    windows-nightly-full 有一支 `shell: powershell` 步驟實跑 bootstrap/dev_start 兩支。
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
    本判準 `(?<!\|)\s\?\s.*?\s:\s` 要求「`?` 後有空白**且**冒號兩側皆有空白」，
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
    刻意不放寬冒號空白條件：實測放寬為 `\s\?\s*.*?\s*:\s*` 雖對現行 21 支 active
    `.ps1` 仍零命中，但會讓 `… | ? { $_ -ne $env:TEMP }` 這類「Where-Object 別名
    ＋ `$env:X`」的同行寫法變成偽陽性，收緊代價高於收益。
    **因此檔頭「A 語法/運算子組」所列的 `? :` 僅涵蓋全空白形態**，非該禁令的完整
    機械化；`tools/windows_smoke_local.ps1` 檔頭列的 4 項禁令中，三元這一項仍部分
    依賴人工複核。

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

import re
import subprocess
import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_OK_MARKER = "ps7-ok:"

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
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。"""
    sdd_root = _REPO_ROOT / "AISDLC_SDD"
    resolver = sdd_root / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(sdd_root)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return sdd_root / name


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


def scan_trees() -> list[tuple[str, list[str], int]]:
    """（樹 key, `.ps1` 相對路徑清單, 檔數下限）。LATEST key 正規化為 `LATEST`，
    升版（Copy-on-Evolve 建 v0.(N+1)）不失效。"""
    latest = _latest_root()
    specs = [
        ("tools", "tools", 8),
        ("AutoClaude/tools", "AutoClaude/tools", 7),
        ("AISDLC_SDD/scripts", "AISDLC_SDD/scripts", 2),
        ("LATEST", f"AISDLC_SDD/{latest.name}", 4),
    ]
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
_CI_TREE_RE = r"Get-ChildItem -Path ([A-Za-z0-9_.\-/]+) -Recurse"

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
            [("tools", 8), ("AutoClaude/tools", 7), ("AISDLC_SDD/scripts", 2), ("LATEST", 4)],
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
        paths = set(re.findall(_CI_TREE_RE, step.group(0)))
        self.assertEqual(
            paths, {"tools", "AutoClaude/tools", "AISDLC_SDD/scripts"},
            f"root-infra-ci.yml 第 2 道的固定掃描樹已變動：{sorted(paths)}——"
            f"本鎖與該 step 自述同掃描面，任一方增刪必須同步",
        )
        # R56 round 7 修正（Architect F2 ／ QA ② 交叉發現）：上面的 `len(ci_trees)`
        # 等值斷言只對「_CI_TREE_RE 抽得到的樹」有效，對「抽不到的形態」天生零訊號
        # ——實測 `-Path "docs/scripts"`（引號界定）與 `-Path (Join-Path ".github"
        # "scripts")`（計算式，該 step 第 4 棵樹就是這種寫法、照抄最自然）插入第 5 棵
        # 樹時三支鎖全綠。故補一條**與字元類完全無關**的出現次數斷言：不論路徑長什麼
        # 樣，多一棵樹必紅。（round 6 宣稱「補抽取數量下限堵 fail-open」不精確——
        # QA 實證那條下限被既有 set-equality 涵蓋、是冗餘的，真正生效的只有字元類擴充。）
        self.assertEqual(
            len(re.findall(r"Get-ChildItem\s+-Path", step.group(0))), 4,
            "root-infra-ci.yml 第 2 道的 `Get-ChildItem -Path` 出現次數已變動（預期 4＝三棵固定樹＋LATEST 計算式樹）——任何形態的掃描樹增刪都會命中此斷言，請同步四處樹清單站點",
        )
        self.assertIn(
            'Join-Path "AISDLC_SDD" $latestName', step.group(0),
            "root-infra-ci.yml 第 2 道未見 LATEST 樹（Join-Path AISDLC_SDD $latestName）"
            "——第 4 棵樹疑似被移除",
        )


if __name__ == "__main__":
    unittest.main()
