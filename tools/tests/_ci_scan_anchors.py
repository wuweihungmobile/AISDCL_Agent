#!/usr/bin/env python3
"""root-infra-ci.yml「pwsh 語法解析」step 掃描面錨點的單一真相源（R57 A2）。

背景（R57 修正的缺陷）：R56 round 6/7 為了鎖住「CI 第 2 道的 .ps1 掃描樹不得被
悄悄增刪」，在 `test_ps1_bom.py`／`test_smoke_ci_sync.py`／`test_ps51_compat.py`
三份測試各自逐字複製了同一組錨：

    _CI_TREE_RE = r"Get-ChildItem -Path ([A-Za-z0-9_.\\-/]+) -Recurse"
    len(re.findall(r"Get-ChildItem\\s+-Path", step)) == 4

兩者都硬綁 `-Path` **具名參數**。但 `-Path` 是 PowerShell 的位置參數（`Get-ChildItem`
的 Position=0），完全可以省略——往該 step 追加一行

    $files += @(Get-ChildItem docs/scripts -Recurse -Filter *.ps1 -File)

即可在三份共 20 支測試全綠的情況下把掃描面擴一棵樹（R57 實測：舊抽取式抽到的樹集合
不變＝仍 3 棵、舊計數錨仍 4）。R56 round 7 在三處註解寫下的「不論路徑長什麼樣，多一棵
樹必紅」因此是**假宣稱**——它只對「有寫 -Path 的形態」成立。

本模組提供三條**互補**的錨並收斂成 SSOT。R57 四方複審 ARCH-01／QA-R57-01 判定：
上一版 docstring 的「與 `-Path` 寫法、引號界定、`Join-Path` 計算式全部無關」是**同款
假宣稱當場復發**（實測 `-Filter "*.ps1"`／`-Include *.ps1`／`gci` 別名／參數重排全部
逃逸，其中三種還是 R56 舊錨抓得到的＝淨退化）。故以下敘述**只寫 `test_ci_scan_anchors.py`
以變異樣本逐一實測釘住的形態**，涵蓋與不涵蓋都逐條列出，不再出現「任何形態必命中」
這類未經窮舉的絕對詞：

  * `ci_fixed_trees()` — 字面路徑樹抽取式；`(?:-Path\\s+)?` 兼容具名/位置兩形態，
    要求路徑 token 後**緊接** `-Recurse`。
    涵蓋：`-Path tools`、`tools`（省略 `-Path` 的位置參數）。
    不涵蓋：引號路徑 `"tools"`、`(Join-Path …)` 計算式路徑、`-Recurse` 未緊接路徑
    的參數重排——這三種一律靠下面兩條錨兜底。
  * `ci_scan_statement_count()` — 計數 `-Recurse -Filter *.ps1 -File` 這串「掃 .ps1
    的必要尾巴」。因尾巴不含路徑，故涵蓋具名/位置/引號/`Join-Path` 計算式**任一種
    路徑寫法**。
    不涵蓋：`-Filter "*.ps1"`（filter 自身加引號）、`-Include *.ps1` 取代 `-Filter`、
    `-Recurse`／`-Filter`／`-File` 三者順序對調。
  * `ci_gci_call_count()` — 該 step 內的 cmdlet 出現次數（`Get-ChildItem` 與常見
    別名 `gci`／`dir`／`ls`）。它**不看任何參數**，因此參數名、參數順序、引號界定、
    計算式路徑一律影響不到它；R57 實測：上面兩條錨全部逃逸的四種形態（filter 加
    引號、`gci` 別名、`-Include`、`Join-Path`＋引號 filter）與 QA 另測的「位置參數
    ＋`-Filter` 寫在 `-Recurse` 前」，在本錨下皆 4 → 5 翻紅。
    別名以 `(?<![\\w$.\\-])` 開界，`$dir`／`$ls`／`.dir`／`-ls` 不算命中。

大小寫（R57 round 2 ARCH-01 修正）：PowerShell 的 cmdlet 名、別名與參數名一律
**不分大小寫**，但上一版三條錨全部大小寫敏感——實測 `get-childitem docs/scripts
-recurse -filter *.ps1 -file`（全小寫）插進真實 step 後三錨皆不變（trees=3 stmt=4
gci=4）＝all-green 逃逸，`GCI`／`Dir`／`Get-Item` 同樣逃逸。故三條錨一律加
`re.IGNORECASE`；加 flag 後在真實 step 上實測仍為 trees=3／stmt=4／gci=4（別名
`gci`／`dir`／`ls` 在該 step 的中英文註解與程式碼中 0 次命中，此數字為量測值而非推算）。

已實測涵蓋（`test_ci_scan_anchors._FORM_EVASIONS` 逐條釘住；下列反引號內的 cmdlet
拼法與參數名由 `test_ci_scan_anchors.TestDocstringClaimsMatchAnchorTables` 與該樣本表
**雙向**核對——樣本引入新拼法／新參數名而此處沒跟、或此處多列一種而無對應樣本，
兩個方向都會翻紅）：`Get-ChildItem`／`get-childitem`／`GET-CHILDITEM` 任一大小寫、
`gci`／`GCI`／`Dir`／`ls` 別名、具名（`-Path`）／位置／引號／`Join-Path` 計算式路徑、
`-Recurse`／`-Filter`／`-File` 任意順序與任意大小寫、`-Include` 取代 `-Filter`。
已實測**不**涵蓋（三條錨皆抓不到，屬已知殘餘風險）——逐項列於下方標記行，與
`test_ci_scan_anchors._KNOWN_UNCOVERED` 由同一測試類**雙向**鎖成等長等內容；
項數刻意不寫成中文數字，因為 R57 round 4 ARCH-R57R4-02 揪出上一版鎖是**單向**的
（只在「錨變強」方向翻紅，對「常數表變長」方向無感），於是 `EnumerateFiles` 補進
常數表後這裡仍寫「這三種」卻零訊號，害下一輪審查者以為殘餘逃逸面只有三種：
  [UNCOVERED] `[System.IO.Directory]::GetFiles(...)` — .NET 靜態方法直接列舉
  [UNCOVERED] `Get-Item`（含 wildcard 形態）
  [UNCOVERED] `Resolve-Path`（含 wildcard 形態）
  [UNCOVERED] `[IO.Directory]::EnumerateFiles(...)` — 上面 GetFiles 的 lazy 同族
未窮舉：PowerShell 列舉檔案的途徑不只上述，本清單只列已實機量測過的形態，不做
「唯一殘餘風險是 X」這類未窮舉的絕對宣稱（R57 round 1／round 2 各因此翻車一次）。

輸入前處理契約（R57 round 2 SA-R57R2-02 修正）：三支函式**內部一律先剝掉整行
`#` 註解**再比對，故餵原文與餵已剝註解的文字（如 `test_smoke_ci_sync._code_only()`
的產物）保證得到相同結果——剝註解是冪等的，f(x) == f(strip(x)) == f(strip(strip(x)))。
這讓「三份呼叫端共用同一組 EXPECTED_* 常數」在機械上不可能因前處理分歧而失效
（上一版 smoke 餵剝註解後的 step、另兩份餵原文，只因該 step 註解恰好 0 次命中才
巧合一致；在 step 尾端加一行 `# TODO 改用 Get-ChildItem` 即 raw=5／code_only=4，
無任何單一常數能同時滿足三份）。此契約由
`test_ci_scan_anchors.TestInputPreprocessingContract` 以性質測試守住。

WHY 收斂成共用模組（R56 曾裁定「三份獨立有其鑑別力價值」，R57 改判的理由）：
那次裁定的前提是「三份互為交叉校驗」，但三份讀的是**同一個檔案的同一個 step**，
彼此不構成獨立觀測——實證就是本次缺陷在三份裡以完全相同的形態同時存在、同時失效，
三份複製只是把同一個盲點抄了三遍。真正的鑑別力來自「錨本身有沒有被鎖」，故本模組
另配 `test_ci_scan_anchors.py`：以合成的變異 step 文字直接斷言「插入位置參數形態的
第 5 棵樹必紅」，這是三份複製從來沒有過的防線。三份呼叫端仍各自持有自己的樹清單
與語意斷言（那部分才是各自獨立的價值），只共用抽取/計數這層機械錨。
"""
from __future__ import annotations

import re

# 固定樹抽取式。`(?:-Path\s+)?` ＝兼容具名與位置兩種參數形態；capture 首字元刻意
# 排除 `-`，避免在位置形態下把 `-Path` 自己當成樹名抓進來。
# `(Join-Path "AISDLC_SDD" $latestName)` 這種計算式樹以 `(` 開頭，天生抽不到
# （由呼叫端另以 `assertIn('Join-Path "AISDLC_SDD" $latestName', step)` 守住）。
CI_TREE_RE = re.compile(
    r"Get-ChildItem\s+(?:-Path\s+)?([A-Za-z0-9_.][A-Za-z0-9_.\-/]*)\s+-Recurse",
    re.IGNORECASE,
)

# 掃描語句計數錨：只認「-Recurse -Filter *.ps1 -File」這串尾巴。因尾巴不含路徑，
# 故路徑寫成具名/位置/引號/Join-Path 計算式皆命中；但 filter 加引號、改用 -Include、
# 或三個參數順序對調則抓不到（→ 由 CI_GCI_CALL_RE 兜底，見模組 docstring）。
CI_SCAN_STMT_RE = re.compile(r"-Recurse\s+-Filter\s+\*\.ps1\s+-File", re.IGNORECASE)

# cmdlet 出現次數錨（R57 ARCH-01）：不看任何參數，故與參數名/順序/引號/計算式路徑
# 全部無關。別名以 `(?<![\w$.\-])` 開界避免 `$dir`／`.ls`／`-dir` 這類偽陽性。
CI_GCI_CALL_RE = re.compile(
    r"Get-ChildItem"
    r"|(?<![\w$.\-])gci(?![\w-])"
    r"|(?<![\w$.\-])dir(?![\w-])"
    r"|(?<![\w$.\-])ls(?![\w-])",
    re.IGNORECASE,
)

# 現況：三棵固定樹（tools / AutoClaude/tools / AISDLC_SDD/scripts）＋ LATEST 計算式樹。
EXPECTED_CI_SCAN_STATEMENTS = 4

# 現況實測（IGNORECASE 下量測，非推算）：`Get-ChildItem` 4 次、`gci`／`dir`／`ls`
# 各 0 次；剝整行註解前後同為 4。
EXPECTED_CI_GCI_CALLS = 4


def strip_line_comments(step_text: str) -> str:
    """剝掉整行 `#` 註解（pwsh 與 yml 同款）——三支錨的統一前處理。

    冪等：`strip_line_comments(strip_line_comments(x)) == strip_line_comments(x)`，
    故呼叫端餵原文或餵已剝註解的文字（`test_smoke_ci_sync._code_only()`）結果一致。
    不處理**尾隨**行內註解（PowerShell 的 `#` 在字串／`--%` 之後不一定是註解，
    無 tokenizer 無法安全判定），故 `Get-ChildItem …  # 說明` 這種行整行保留。
    """
    # 用 `split("\n")` 而非 `splitlines()`：後者會吃掉尾端換行（`"a\n\n"` → `"a\n"`
    # → `"a"`）而破壞冪等性，也會多切 `\x0b`／` ` 等 unicode 行界。
    return "\n".join(
        ln for ln in step_text.split("\n") if not ln.lstrip().startswith("#")
    )


def ci_fixed_trees(step_text: str) -> set[str]:
    """抽出該 step 以字面路徑列舉的固定掃描樹（不含 Join-Path 計算式樹）。

    輸入可為原文或已剝整行註解的文字（內部一律先剝，見 `strip_line_comments`）。
    """
    return set(CI_TREE_RE.findall(strip_line_comments(step_text)))


def ci_scan_statement_count(step_text: str) -> int:
    """該 step 裡寫成 `-Recurse -Filter *.ps1 -File` 的遞迴掃描語句數。

    路徑寫法與大小寫不影響本值；filter 加引號／改 `-Include`／參數順序對調則會
    逸出，須搭配 `ci_gci_call_count()` 一起斷言才構成完整掃描面鎖。
    輸入可為原文或已剝整行註解的文字（內部一律先剝）。
    """
    return len(CI_SCAN_STMT_RE.findall(strip_line_comments(step_text)))


def ci_gci_call_count(step_text: str) -> int:
    """該 step 內 `Get-ChildItem`（含 `gci`／`dir`／`ls` 別名）的出現次數。

    不解析參數且大小寫不敏感，故該 cmdlet 系列的任何參數形態／大小寫寫法增刪
    都會改變本值。輸入可為原文或已剝整行註解的文字（內部一律先剝），故整行註解
    裡提到 cmdlet 字樣**不**計入。
    """
    return len(CI_GCI_CALL_RE.findall(strip_line_comments(step_text)))
