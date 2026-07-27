#!/usr/bin/env python3
"""PowerShell 原始碼解析 SSOT：供「錨點只認功能碼、不認註解」的靜態鎖消費。

**為什麼獨立成一支模組（R58 落地 ARCH-R57R3-02／DEF-101-500 ⑤）**：本模組內容原寄居於
`_platform_helpers.py`，但那支模組的收納契約是「跨平台測試 fixture 輔助函式（對開發者本機
環境有隱性假設者）」——一支 PowerShell tokenizer 既不是 fixture、也與本機環境假設無關，卻
佔了該檔一半以上行數，逼得 R57 把模組首句契約改寫成「兩類收納物」。**契約被內容反向牽著改，
就是該拆的訊號**（雜物抽屜的早期形態）。R57 判定拆分「需連動呼叫端鎖翻修」而列 backlog，R58
複核發現成本被高估：R57 自己已把模組名收斂成 `_PS_STRIPPER_SSOT_MODULE` 一個常數，拆分只需
改一個字串 + 兩行 import。

## 兩層防護的分工（R58 架構定案）

第 ① 層 `strip_ps_comments()`＝**近似法**（前導字元白名單）。它有**結構性天花板**：PowerShell
的 `#` 是否為註解取決於 tokenizer 的 command/argument（bareword）對 expression **解析模式**，
與前導字元無關，故前導字元白名單原理上不可能完備（見下方 `strip_ps_comments` docstring
「已知不涵蓋」第 5 條的量測數據）。方向為 **fail-open**（漏剝＝註解冒充功能碼＝靜態鎖假綠）。

第 ② 層 `tools/tests/test_ps_comment_golden.py`＝**離線差分 oracle**。以真 PowerShell parser
（`[System.Management.Automation.Language.Parser]::ParseInput`）對全語料取 Comment token，
凍結成 `ps_comment_golden.json`，測試時離線比對「近似法的輸出」vs「ground truth 的輸出」。

**為什麼是「差分 oracle」而不是「讓消費端直接吃 golden 的 span」**（R58 Scan-E Architect 裁定，
兩案都評估過，此處記下未採用的理由供後續輪引用，不必重辯）：
  * 消費端改吃 golden ⇒ 新增一條「span 與檔案內容必須同步」的資料相依。雖然本模組已用
    per-file sha256 把不同步做成 fail-closed，但那是**多**一道必須自己也正確的機制；而近似法
    無論如何都得繼續維護——`StripPsCommentsTest` 家族的斷言全是**合成字串**（不存在於任何
    `.ps1`、golden 天生沒有它們的條目），故「消費端吃 golden」只會造成「語料走 golden、合成走
    近似」兩條並存路徑，既沒消掉天花板又多一個資料相依。
  * 差分 oracle 則把 fail-open 從「latent（今天剛好沒人踩到）」轉成「**踩到的那一刻立刻翻紅**」
    ——這正是 R57 判定「不在該輪修」所依據的那個前提（全語料洩漏數為 0）失效的瞬間。
  * 代價（明說）：翻紅時紅的是差分測試而不是那支 fail-open 的錨點鎖本身，診斷需多跳一層。
    故差分測試的失敗訊息**必須指名受影響的消費端**——由 `test_ps_comment_golden._at_risk_consumers()`
    **機械 AST 掃出、非寫死名冊**（判例文件明載「過期的名冊指向錯誤檔案比沒有訊息更糟」）。
    （R58 round 2 ARCH-R58R2-03 訂正：本處原寫 `_CONSUMERS_AT_RISK`，全 repo 零命中＝死指標，
    且那個名字看起來像寫死名冊，恰與判例規範讀成相反。）

## 語料正規化契約（踩過的坑，勿自行簡化）

`normalize_ps_source()` 是 golden 的 offset／sha256 唯一合法基準：**跳過 UTF-8 BOM + CRLF→LF**。
  * BOM：本 repo 政策要求「含非 ASCII 的 active `.ps1` 必須帶 BOM」（DEF-101-002；zh-TW Windows
    PS 5.1 無 BOM 會以 CP950 誤讀），故語料內 BOM 有無並存，兩側都必須跳過才對得上。
  * CRLF：`.gitattributes:44` 是 `*.ps1 text eol=crlf`，兩平台工作樹皆為 CRLF；正規化成 LF 使
    golden 不依賴這條設定（未來若改回 eol=lf 也不會整批失效）。
  * 🔴 **UTF-16 vs code point（R58 實測踩到，最隱蔽的一坑）**：.NET 的 `Extent.StartOffset`／
    `EndOffset` 以 **UTF-16 code unit** 計數，Python 字串索引以 **code point** 計數。本 repo 的
    `.ps1` 內含星體平面 emoji（🔴 U+1F534 等，在 .NET 算 2 個單位、Python 算 1 個），直接把
    .NET offset 當 Python 索引用會**靜默錯位**——R58 實測：137 支檔案中 62 支長度不符、逾半數
    span 切出來不是以 `#`／`<#` 開頭（該量測取自落地前語料，僅證明現象存在；**刻意不寫死 span
    總數**，那個數字的唯一真相源是 `ps_comment_golden.json` 本身）。故 golden **一律存 code point
    offset**，轉換在產生器（`tools/gen_ps_comment_golden.py`）內完成、且被回歸測試釘住。
"""
from __future__ import annotations

import json
from pathlib import Path

# golden 檔位置（產生器與差分測試共用此常數，避免兩處各寫一份路徑）。
GOLDEN_PATH = Path(__file__).resolve().parent / "ps_comment_golden.json"
GOLDEN_SCHEMA_VERSION = 1


# `#` 只在引號外、且位於行首或這些字元之後才算註解起點（避免誤剝 `$#`、`c#`）。
#
# R57 round 3 SD-R57R3-01：原集合 `" \t;|({,"` **漏掉右括號類與引號類收尾字元**，
# 使「以 `)`／`}`／`]`／`"`／`'` 結尾的功能碼後緊接的 `#`」不被視為註解起點而原樣保留
# ——「錨點只認功能碼」的鎖因此 fail-open。SD 以 pwsh 7 的真 PowerShell parser
# （`[System.Management.Automation.Language.Parser]::ParseInput` 取 Comment token）
# 取得 ground truth，逐條確認這五種形態在 PowerShell 中**確實都是註解**：
#     Write-Host (1)#c    if ($true) { }#c    $a[0]#c
#     Write-Host "a"#c    Write-Host 'a'#c
# 對照組 `c#`／`$#`／`Write-Host $a#b` 的 Comment token 為空，即現行 lead-char 設計要
# 保護的情形——補上這五個字元不會傷到它們（Architect round 4 以 64 案差分實測
# FAIL_CLOSED=0，零退化）。
#
# **R57 round 4 SD-R57R4-01 訂正「為什麼安全」的理由**（原寫「其前一字元是字母／`$`，
# 仍不在集合內」——該理由與 PowerShell 真實規則**不等價**，被後人採信會導向錯誤修法）：
# 真正的保護來源是 PowerShell 的 **command/argument（bareword）解析模式**——bareword
# 本身可含 `#`，與前導字元無關。同一個 `$x#c` 在 **expression 模式**下 `#` 就**是**註解
# （pwsh 7.6.3 實測：`$c#zz` → Comment@2；`$v = $x#  -WakeToRun` → Comment@7；R58 於
# Windows PowerShell 5.1 獨立複驗同樣結論：`$a = 1#c` → Comment@L1C7）。
# 換言之 `$` 不構成「保護類別」，lead-char 白名單只是對 parse-mode 的近似（見下方
# `strip_ps_comments` docstring「已知不涵蓋」第 5 條的完整量測與 R58 落地的差分 oracle）。
_PS_COMMENT_LEAD = " \t;|({,)}]\"'"
# here-string 起始 token（`@"`／`@'`）只在行首或這些「分隔語境」之後才成立。
# R57 A-R57R2-02：舊版只用 `re.search(r'@(["\'])\s*$', line)` 比對整行行尾，
# `Write-Host "user@"` 這種「普通字串字面值恰以 @ 結尾」即誤開 here-string，
# 而終止條件 `"@` 幾乎不會出現 → 其後整份檔案停止剝註解（latent fail-open）。
_PS_HERE_STRING_LEAD = " \t=(,;|{"


def normalize_ps_source(data: bytes) -> str:
    """把 `.ps1` 的原始 bytes 正規化成 golden 的唯一合法基準文字。

    契約（產生器與所有消費端必須完全一致，否則 offset／sha256 全部錯位）：
      1. 跳過 UTF-8 BOM（`utf-8-sig`）——本 repo 的 `.ps1` BOM 有無並存，見模組 docstring。
      2. CRLF → LF——`.gitattributes` 讓兩平台工作樹皆為 CRLF，正規化後 golden 與該設定解耦。
    刻意**不**做其他處理（不 strip 尾端空白、不統一縮排）：任何額外變換都會讓 offset 與
    「人在編輯器裡看到的位置」脫節，增加診斷成本。
    """
    return data.decode("utf-8-sig").replace("\r\n", "\n")


def _scan_ps_line(line: str, in_block: bool) -> tuple[str, bool, str | None]:
    """單行掃描器：回傳 (剝除註解後保留的片段, 行末是否仍在 `<#…#>` 內, here-string 起始引號)。

    逐字元掃描而非正則，因此**引號感知**貫穿三種註解形態：行內 `#`、區塊
    `<#…#>`、here-string 起始偵測都只在「引號外」才成立（R57 R57R2-QA-01：舊版
    區塊註解用 `re.sub(r"<#.*?#>", "", text, DOTALL)` 不具引號感知，
    `$x = "<# not a comment #>"` 會被吃成 `$x = ""`，且 `$a = "<#"` 會讓其後功能碼
    整段消失）。PowerShell 引號規則：單引號內無跳脫（`''`＝字面單引號）；雙引號
    內以反引號跳脫（`""` 亦為字面雙引號）。
    """
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        if in_block:
            end = line.find("#>", i)
            if end == -1:
                return "".join(out), True, None
            i, in_block = end + 2, False
            continue
        ch = line[i]
        if ch in "'\"":  # 字串字面值整段原樣保留（黑名單比對要看字串內容）
            start, quote, i = i, ch, i + 1
            while i < n:
                if quote == '"' and line[i] == "`":
                    i += 2
                    continue
                if line[i] == quote:
                    if i + 1 < n and line[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append(line[start:i])
            continue
        if (
            ch == "@"
            and i + 1 < n
            and line[i + 1] in "\"'"
            and not line[i + 2 :].strip()
            and (i == 0 or line[i - 1] in _PS_HERE_STRING_LEAD)
        ):
            return "".join(out) + line[i:], in_block, line[i + 1]
        if line.startswith("<#", i):
            i, in_block = i + 2, True
            continue
        if ch == "#" and (i == 0 or line[i - 1] in _PS_COMMENT_LEAD):
            return "".join(out), False, None
        out.append(ch)
        i += 1
    return "".join(out), in_block, None


def strip_ps_comments(text: str) -> str:
    """剝除 PowerShell 註解後回傳「只剩功能碼」的文字（保留字串字面值內容）。

    供「錨點只認功能碼」的靜態鎖使用：註解裡留著舊字樣會讓錨點假陽性（真刪功能碼
    卻全綠）。空行一律濾除。

    **已實測涵蓋**（逐項有回歸測試，見 `test_find_git_bash_parity.py` 的
    `StripPsCommentsTest`／`StripPsCommentsBoundaryTest`）：整行 `#` 註解、尾隨行內
    註解（**前導字元集合＝`_PS_COMMENT_LEAD`：空白／tab／`;`／`|`／`(`／`{`／`,`／
    `)`／`}`／`]`／`"`／`'`**——R57 round 3 SD-R57R3-01 以 pwsh 真 parser 取
    ground truth 後補上後五個；措辭刻意改為明列集合而非籠統的「尾隨行內註解」，
    因為後者曾把「以 `)` 收尾的功能碼後的 `#`」也涵蓋進宣稱而與實作不符）、
    跨行與單行內聯 `<#…#>` 區塊註解、單/雙引號字串內的 `#` 與 `<#`／`#>` 不
    誤剝（含 `''`／`""` 雙寫跳脫、反引號跳脫）、反引號跳脫的 `` `# ``、`$#`／`c#`
    這類無前置分隔的 `#` 不誤剝、here-string（`@"`／`@'` 起、`"@`／`'@` 止）整段
    原樣保留、字串字面值以 `@` 結尾（`"user@"`）不誤開 here-string、註解內容以
    `@"` 結尾不誤開 here-string、單行輸入（原 `cut_ps_inline_comment` 的契約，
    R58 併入本函式，見模組 docstring 與 DEF-101-509）。

    **已知不涵蓋**（逐項實測確認為現行行為，不做全備宣稱；下列形態在本 repo 掃描
    面即 137 支 git 追蹤 `.ps1` 內實掃皆不存在）：
      1. 跨行字串（雙引號字串內含真換行）第二行起的引號狀態不追蹤，該情形下字串
         內的 `#` 可能被誤剝。
      2. stop-parsing 符號 `--%`：其後所有內容原樣傳給原生指令、`#` 不是註解，本
         函式仍會剝除（R57 A-R57R2-04）。**刻意不修**：`--%` 之後不剝＝多留一段
         「其實是註解」的文字當功能碼，等於在鎖上開一條新的 fail-open（本輪
         A-R57R2-02／R57R2-QA-01 修的正是這一類）；反之現行的多剝只會造成假紅
         （fail-closed）。真出現 `--%` 用法時再連同回歸測試一起處理。
      3. `<#` 出現在**未閉合**的字串字面值中（如 `$x = "<# …` 該行無閉合引號）時，
         引號掃描會吃到行尾，`<#` 不被視為區塊起始。
      4. here-string 終止判定較 PowerShell 寬鬆：本函式亦接受縮排後的 `"@`
         （`ln.strip() == '"@'`），PowerShell 只認行首。方向為提早結束＝多剝
         （fail-closed）。
      5. **不在 `_PS_COMMENT_LEAD` 內的前導字元**後的 `#` 一律不視為註解起點。
         **這不是「未來可能」的風險，而是現行、已量測的結構性限制**（R57 round 4
         Architect／SD 交叉實測後改述）：真實規則是 tokenizer 的 command/argument
         對 expression **模式相依**，前導字元白名單原理上不可能完備——expression
         模式下 `#` 幾乎恆為 token 終止＋註解起點，前導字元可以是任意數字／識別字／
         `::`／`]$var`…。Architect 以 pwsh 7.6.3 真 parser 對 64 個實務形態差分得
         **FAIL_OPEN=27**（其中 **20 案 parseErrors=0** ＝完全合法的日常寫法，如
         `$a = 1#c`、`$env:PATH#c`、`$a = [int]$b#c`、`$a = $b?.Length#c`）、
         **FAIL_CLOSED=0**；SD 另以約 130 條探針得 FAIL_OPEN=37，並實證仍可用
         `$note = $x#  -WakeToRun` 繞過 `test_windows_nightly_anchor_parity.py`
         （round 3 修掉的 `Write-Output "note"#…` 手法已確認關閉）。
         **方向為 fail-open**（漏剝＝註解冒充功能碼），故必須明確揭露而非淡化。
         **切勿再往集合裡補字元**——那是 whack-a-mole，本條存在正是為了阻止它。
         🔵 **R58 落地的解法（本條的現況已改變，請連同讀）**：改用**離線差分 oracle**
         而非改進近似法——`tools/tests/test_ps_comment_golden.py` 以真 parser 對全語料
         凍結 Comment token（`ps_comment_golden.json`），比對本函式輸出與 ground truth。
         本條的 fail-open 仍**存在於本函式**，但已不再是**靜默**的：任何真實 `.ps1`
         一旦寫出本函式漏剝的形態，差分測試立即翻紅。R58 實測全語料分歧數為 **0**
         （即 R57 判定「屬 latent」的那個前提，於原生 Windows 11 + Windows PowerShell 5.1
         上獨立複驗成立），故本輪落地的是**訊號**而非行為變更。
         🔴 **不要把「golden 之法」外推到 `_ci_scan_anchors.py`**（R57 docstring 曾宣稱
         「同法亦可解 `_ci_scan_anchors.py` 判例第 (3) 條的同型天花板」，R58 Scan-E
         Architect 判定該宣稱**逾越**）：註解剝除問的是 **token 級事實**（「這個 `#`
         是不是 Comment」是檔案文字的純函式，parser 直接給答案，可完整凍結）；
         `_ci_scan_anchors` 問的是**語意事實**（「這個 step 列舉了哪幾棵掃描樹」）——AST
         不會告訴你 `[System.IO.Directory]::GetFiles()`／`Resolve-Path` 算不算「列舉一棵
         掃描樹」，也不會把 `(Join-Path "AISDLC_SDD" $latestName)` 解成具體路徑（那需要
         執行期變數值）。那是分類問題不是 tokenize 問題，golden 無法凍結一個需要人來
         定義邊界的答案。**golden 只解得掉其 cmdlet 計數錨那一條**（`CommandAst.GetCommandName()`
         可使別名／大小寫歸一），**語意列舉面解不掉**；誤以為做完 golden 就能拆掉那三條錨
         會是淨退化。
      6. `_PS_HERE_STRING_LEAD`（`" \t=(,;|{"`）同樣未含 `]`／`)`，故
         `[string]@"` 這類以 `]` 收尾的 here-string 起始不被辨識。方向為多剝
         （fail-closed，不影響鎖的正確性），一併登記不修（SD-R57R3-01 第 4 點）。

    **未窮舉**：以上兩份清單只列已實機量測過的形態，不做「唯一殘餘風險是 X」這類宣稱。
    """
    out: list[str] = []
    here_delim: str | None = None
    in_block = False
    for ln in text.splitlines():
        if here_delim is not None:  # here-string 內文原樣保留，不剝任何東西
            out.append(ln)
            if ln.startswith(here_delim + "@") or ln.strip() == here_delim + "@":
                here_delim = None
            continue
        cut, in_block, here_delim = _scan_ps_line(ln, in_block)
        if cut != ln:  # 只在真的切掉東西時 rstrip，未命中的行原樣保留
            cut = cut.rstrip()
        out.append(cut)
    return "\n".join(ln for ln in out if ln.strip())


def strip_by_comment_spans(text: str, spans: list[tuple[int, int]]) -> str:
    """用真 parser 給的 comment span（code point offset）挖掉註解，回傳「只剩功能碼」的文字。

    這是 `strip_ps_comments()` 的 **ground truth 對照版**，收尾規則刻意與其**逐條對齊**
    （只在該行真有東西被挖掉時 rstrip、最後濾除空行），使兩者的差異必然來自「哪些字元被
    認定為註解」這唯一一個變因——否則差分測試會被收尾規則的差異淹沒而失去鑑別力。

    以哨兵字元標記待刪位置而非直接切片：span 可能跨行（`<#…#>` 區塊註解），逐行處理時
    需要知道「這一行有沒有被挖過」才能決定是否 rstrip。哨兵用 `\\x00`——`.ps1` 是文字檔，
    NUL 不可能合法出現（若真出現，`normalize_ps_source` 的 UTF-8 解碼階段就會先出問題）。
    """
    buf = list(text)
    for start, end in spans:
        for k in range(start, end):
            buf[k] = "\x00"
    lines: list[str] = []
    for ln in "".join(buf).split("\n"):
        touched = "\x00" in ln
        clean = ln.replace("\x00", "")
        lines.append(clean.rstrip() if touched else clean)
    return "\n".join(ln for ln in lines if ln.strip())


def load_golden() -> dict:
    """讀取 golden；檔案不存在或 schema 版本不符即 `RuntimeError` fail loud。

    刻意不做「檔案不存在就跳過」的寬容處理——那會讓差分保護在 golden 被誤刪時靜默消失，
    正是本 repo 反覆抓到的假綠形態（守門自己不見了卻沒人知道）。
    """
    if not GOLDEN_PATH.is_file():
        raise RuntimeError(
            f"找不到 PowerShell 註解 golden：{GOLDEN_PATH}——請在有 PowerShell 的機器上跑 "
            "`python tools/gen_ps_comment_golden.py` 重生（Windows 出廠的 powershell.exe 即可，"
            "不需要 pwsh 7）"
        )
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if golden.get("schemaVersion") != GOLDEN_SCHEMA_VERSION:
        raise RuntimeError(
            f"golden schemaVersion={golden.get('schemaVersion')} 與本模組期望的 "
            f"{GOLDEN_SCHEMA_VERSION} 不符——產生器與消費端版本不同步，請重生 golden"
        )
    return golden
