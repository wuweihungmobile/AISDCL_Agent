#!/usr/bin/env python3
"""缺陷帳本 × 高風險文件「狀態宣稱」跨文件一致性機械守護（DEF-101-068(e) 落地）。

🔴 本工具的邊界（務必先讀，比照 `check_script_parity.py` docstring 風格誠實承認侷限）：
本工具**不理解自然語言**，只做「正則抽取 + 關鍵字比對」兩件事：
  1. 在掃描目標文件中找出「一個或多個 `DEF-\\d+-\\d+` 緊接著一個括號」的樣式
     （括號可為全形｀（）｀或半形｀()｀；ID 前後允許 markdown 粗體 `**`）。
  2. 從該括號內文字裡找出**最早出現**的已知狀態關鍵字
     （`open` / `routed` / `fixed` / `wontfix` / `closed-by-decision`，
     對應帳本《格式定義》§ 狀態欄的合法值），視為該文件對這個/這些 DEF ID 的「狀態宣稱」。
  3. 與 `docs/06_quality/AutoSDD_Defect_Log.md` 表格中該 ID 「狀態」欄的最新紀錄
     （同樣取表格該欄文字中最早出現的關鍵字）比對，不一致即回報。

**不做**、也**做不到**的事（誠實劃界，勿誤讀為完整性保證）：
  - 沒有括號緊跟在 ID 後面的單純引用（例如「見 DEF-101-058」）**不會被檢查**——
    這類引用未對狀態做任何明確宣稱，強行判讀等同瞎猜，故刻意略過以避免假陽性。
  - 括號內文字**巢狀提及**另一個 DEF ID 的狀態（例如 A 的括號內順帶一句「其根因 B
    已 fixed」）不會被拆成 B 的獨立宣稱——只有「緊鄰括號」的最外層 ID 才會被判讀。
  - 帳本表格若同一 ID 出現多列（理論上 append-only 帳本不應如此，但若發生），
    僅取**最後一列**的狀態為準（視為對前列的訂正）——即使最後一列的狀態欄文字無法
    辨識任何已知關鍵字，也視為「該 ID 目前狀態不明」而非沿用更早一列的舊值
    （獨立複審 finding：舊實作在此情境下會靜默沿用前一列，與本條承諾矛盾，已修正）。
  - 掃描範圍限縮於 `ONBOARDING.md` + `.github/workflows/{windows,macos}-compat-ci.yml`
    （DEF-101-066 這類「改帳本忘同步姊妹文件」真實復發過一次的高風險文件；R4 複審
    QA 發現 windows-compat-ci.yml 的 R4 複審修正段落明確引用 DEF-101-067⑤ 卻未同步
    更新帳本狀態，補入此二檔擴大覆蓋），非涵蓋 repo 全部文件；未來如需擴大範圍，
    加入 `_CROSSREF_TARGETS` 即可，不需改動核心比對邏輯。

為何需要：DEF-101-066 實際發生過一次——commit 只改帳本把 DEF-101-058 標記 fixed，
`ONBOARDING.md` §9 卻仍宣稱該 ID open，兩份文件對同一 ID 各說各話卻無任何機械訊號。
本腳本把「發現即記」這類跨文件漂移的偵測，從「靠人工複審碰運氣」提升為可重複執行的
機械檢查。

另一件本檔**會**做的事（R60 round 2 SA-R60R2-06 新增，與上述跨文件比對相互獨立）：
帳本每一列**狀態欄首詞**必須落在《格式定義》宣告的合法值集合內，不合法即 rc=1。
合法值集合與主檔散文**雙向綁定**（見 `_STATUS_FIRST_WORDS` 與 `status_first_word_problems`）。
為何必須另立這一項：`_classify()` 只找「最早出現的已知關鍵字」，`partially-fixed` 這種
寫法會靜默命中 `fixed`（`-fixed` 對邊界 lookaround 成立），於是「只修了一部分」在閘門
眼中等於「已修」，而本檔對非法首詞原本一句話都不說。

第三件本檔**會**做的事（R60 round 3 Pkg-P6 新增，且是上面兩件事的**前提**）：
每一缺陷列切出的欄數必須等於表頭欄數（`row_arity_problems()`），且「狀態欄」一律由
**表頭**定位（`_table_layout()`）而非取 `cells[-1]`。
為何必須另立這一項——舊實作切欄寫成
`[c.strip() for c in re.split(...) if c.strip()]`，`if c.strip()` 會把**空欄整個濾掉**，
且全程沒有任何「欄數 == 表頭欄數」的檢查，於是狀態欄留空時 `cells[-1]` 會靜默**位移**
到「分流去向」欄。本包實測構造輸入（未動主檔）：
  - 狀態欄空白 ＋ 分流去向＝「已於上游 fixed 故不另修」
    ⇒ `_load_ledger_status()` 回 `{'DEF-01-001': 'fixed'}`，而該 ID 狀態欄其實是空的。
  - 最壞複合：狀態欄空白 ＋ 分流去向以合法關鍵字開頭（`open 待下輪處理`）
    ⇒ `status_first_word_problems()` 回 `[]` ⇒ **上面兩道檢查同時完全放行、零訊號**。
即「抓跨文件假綠」的工具自己長了一個同型假綠面。修法選 (乙)＝表頭定位而非位置依賴：
`[-1]` 這種位置依賴本身就是脆弱來源，且保留空欄後 `[-1]` 會變成 markdown 表格尾端的
空片段，非改不可。實查帳本家族 32 檔的表頭**欄數全部同形**（9 個切片＝首尾空片段 ＋
7 個資料欄，狀態欄恆為最後一個資料欄；只有第 4 欄欄名有兩種寫法，不影響定位），
故表頭定位對本 repo 既有表格形態安全。

⚠️ arity 檢查的作用範圍**僅主檔**（`_DEFECT_LOG`）——本檔對 archive 只 `stat()` 量大小、
從不解析其表格列，故 `DEF-101-560` 具名不修的 archive 側 14 列（含未轉義字面豎線、
被切成 10~11 欄）不會被本檢查誤紅；那 14 列今日零活體後果且已在帳本具名記載。
這**不是**對整個檔的靜默豁免：那些列本來就不在本檔的解析面內，一旦被搬進主檔就會當場紅。

使用：
  python3 tools/check_defect_log_crossref.py   # 於 repo 內任意 cwd；不一致印清單並 exit 1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFECT_LOG = _REPO_ROOT / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
_CROSSREF_TARGETS = [
    _REPO_ROOT / "ONBOARDING.md",
    _REPO_ROOT / ".github" / "workflows" / "windows-compat-ci.yml",
    _REPO_ROOT / ".github" / "workflows" / "macos-compat-ci.yml",
    # 2026-07-16 四方複審 SA 發現：本檔會對 DEF-101-051 等 PG-track 缺陷做明確狀態宣稱
    # （曾實際自相矛盾——同檔第 3 行宣稱 fixed、第 52 行「追蹤」段落仍宣稱 open，且與
    # 帳本最新狀態不一致），先前不在掃描範圍內故未被機械鎖抓到。只新增此一檔，不擴大為
    # 全 repo 掃描（那是架構層級更大改動，非本輪範圍）。
    _REPO_ROOT / "AutoClaude" / "docs" / "05_development" / "SD10_PG_Contract_NextAction.md",
]

_ID_RE = re.compile(r"DEF-\d+-\d+")
_ROW_RE = re.compile(r"^\|\s*DEF-\d+-\d+\s*\|")
# 一個或多個「(粗體)DEF-id(粗體)(分隔符)」緊接一個括號 → 該括號內文字視為這些 ID 的狀態宣稱。
# 括號內容不設人為字數上限：曾以 {0,150} 限制，結果本 repo 慣用的長句敘述（例如
# DEF-101-057 的括號內容實測 186 字元）一旦超過上限便整段比對失敗、被靜默略過，
# 且不會有任何警告——等同複製本工具本應防止的 DEF-101-066 doc-drift 假綠情境
# （複審實測：帳本刻意設為與文件矛盾的狀態，_scan_target 仍回報空清單）。
# 改用 `[^）()]*`：因排除左右括號字元本身，最多只會掃到下一個括號為止，屬線性掃描、
# 無 catastrophic backtracking 風險，可安全移除上限。
_CLAIM_RE = re.compile(
    r"((?:\*{0,2}DEF-\d+-\d+\*{0,2}[、，,／/\s]*)+)[（(]([^）()]*)[）)]"
)

# ---------------------------------------------------------------- 表格欄位切分 + 表頭定位（Pkg-P6）
# 只把「未被反斜線前導」的豎線當分隔符（欄內字面豎線須寫成 `\|`，見 DEF-101-560）。
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
# 表頭列＝第一個資料欄為 `ID`。帳本家族 32 檔實查皆為此形態（欄數全數同形）。
_HEADER_RE = re.compile(r"^\|\s*ID\s*\|")
_ID_HEADER = "ID"
_STATUS_HEADER = "狀態"


def _row_cells(line: str) -> list[str]:
    """切出表格列的**全部**欄位並各自 strip，**保留空欄**（含首尾的空片段）。

    🔴 絕對不可再寫回 `[... for c in ... if c.strip()]`：`if c.strip()` 把空欄濾掉，
    欄位索引就會隨「該列有幾個空欄」浮動，於是狀態欄留空時 `cells[-1]` 靜默位移到
    左邊的「分流去向」欄（Pkg-P6 修的正是這個；復現輸入見模組 docstring 第三件事）。
    保留首尾空片段是刻意的：拿它跟表頭的切片數直接對齊即為 arity 檢查，不需另外
    猜「這列有沒有寫尾端豎線」。
    """
    return [c.strip() for c in _CELL_SPLIT_RE.split(line)]


def _table_layout(ledger_text: str) -> tuple[int, int, int] | None:
    """回傳帳本表頭的 `(切片數, ID 欄索引, 狀態欄索引)`；找不到合格表頭回 `None`。

    取**第一個**合格表頭：主檔實查只有一個（`:34`）。刻意用欄名（`ID`／`狀態`）定位而
    非寫死索引，欄序若被調動也能跟上；欄名被改寫則回 `None` → 呼叫端 fail-loud。
    """
    for line in ledger_text.splitlines():
        if not _HEADER_RE.match(line):
            continue
        cells = _row_cells(line)
        if _ID_HEADER in cells and _STATUS_HEADER in cells:
            return len(cells), cells.index(_ID_HEADER), cells.index(_STATUS_HEADER)
    return None


def _no_header_problem() -> str:
    return (
        f"{_DEFECT_LOG.name} 找不到合格表頭（需為 `| ID | … | 狀態 | …` 形態：第一個資料欄"
        f"為 {_ID_HEADER!r} 且列中含 {_STATUS_HEADER!r} 欄）— 欄位定位失去依據。"
        "本檔刻意**不**退回 `cells[-1]` 位置猜測：那正是「狀態欄空白時靜默位移到分流"
        "去向欄」的成因（Pkg-P6）。請確認主檔表頭未被改寫，或同步本檔 _HEADER_RE／"
        "_ID_HEADER／_STATUS_HEADER"
    )


def _cells_digest(cells: list[str], per_cell: int = 40) -> str:
    """把一列切出的欄位**逐欄**列出（每欄截斷但不省略任何一欄）。

    P6-2：凡涉及「欄位定位」的訊息都要讓人一眼看出「切成幾欄、每欄是什麼」。修復前的
    訊息只印 `cells[-1]`，於狀態欄空白時會誤植成「狀態欄原文開頭：'去向'」——讀者會照
    著錯的欄位去查，比完全沒擋更危險。
    """
    parts = [
        f"#{i}={(c if len(c) <= per_cell else c[:per_cell] + '…')!r}"
        for i, c in enumerate(cells)
    ]
    return f"共 {len(cells)} 個切片 [" + ", ".join(parts) + "]"


def _arity_problem(lineno: int, cells: list[str], expected: int) -> str:
    return (
        f"帳本 :{lineno} 表格列切出 {len(cells)} 個切片 ≠ 表頭 {expected} 個"
        f"（欄位定位失效，「狀態欄」位置不可信任，故本列不做狀態判讀）。"
        f"該列切出的全部欄位＝{_cells_digest(cells)}。"
        "常見成因：欄內含未轉義的字面豎線（須寫成 `\\|`，見 DEF-101-560）、"
        "或漏寫／多寫欄分隔符"
    )


def row_arity_problems(ledger_text: str) -> list[str]:
    """帳本每一缺陷列切出的欄數必須等於表頭欄數（純函式；Pkg-P6 P6-1）。

    回傳問題清單（空＝全部合列）。抽成純函式的理由同 `status_first_word_problems()`：
    可直接以構造輸入證明它有牙，不必真的弄壞一份帳本。

    🔴 這道斷言與 `_table_layout()` 是一組的：表頭定位解決「狀態欄在哪」，arity 檢查
    解決「這列到底有沒有按表頭切成該有的欄數」。少了後者，一列多／少一個豎線就會讓
    表頭索引指到別欄，而且**一句話都不會說**（DEF-101-560 的主檔那一列即為實例：
    狀態 `no_action_needed` 被讀成 `open`，兩道閘門一致誤判）。
    """
    layout = _table_layout(ledger_text)
    if layout is None:
        return [_no_header_problem()]
    ncols = layout[0]
    problems: list[str] = []
    for lineno, line in enumerate(ledger_text.splitlines(), 1):
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if len(cells) != ncols:
            problems.append(_arity_problem(lineno, cells, ncols))
    return problems

# 狀態關鍵字（對應帳本《格式定義》§ 狀態欄合法值）；用各自獨立 regex 各找最早出現位置，
# 而非 alternation 依 dict 順序短路——wontfix 不含 "fixed" 子字串，兩者互不干擾。
# 邊界改用 (?<![A-Za-z0-9])...(?![A-Za-z0-9]) 而非 \b：Python re 預設 Unicode 語意下 \b 把
# CJK 表意文字也視為 word 字元，中文字緊貼英文狀態詞（如「修復後open尚待驗證」）時兩側都判
# 定為非邊界，導致 \b 比對靜默找不到（已用 _classify() 實測重現）；改成明確只把 ASCII
# 英數字視為邊界字元，CJK／標點／空白都視為合法邊界，才能正確比對中英夾雜文字。
_STATUS_KEYWORDS: dict[str, re.Pattern[str]] = {
    "wontfix": re.compile(r"wontfix"),
    # `no_action_needed`／`no action needed`（帳本實例：DEF-101-077）＝查證後決定
    # 不需修復 → 歸類 closed-by-decision（R9 跨平台複審：原詞彙表缺此詞導致該列
    # 被計入「有效狀態紀錄」卻實為 None 含糊）。
    "closed-by-decision": re.compile(r"closed-by-decision|no[_ ]action[_ ]needed"),
    "routed": re.compile(r"(?<![A-Za-z0-9])routed(?![A-Za-z0-9])"),
    "fixed": re.compile(r"(?<![A-Za-z0-9])fixed(?![A-Za-z0-9])"),
    # `workaround`（帳本實例：DEF-101-089 workaround-applied）＝以流程繞過、
    # 程式碼缺陷本身仍在 → 歸類 open（workaround 非程式修復）。
    "open": re.compile(r"(?<![A-Za-z0-9])open(?![A-Za-z0-9])|workaround"),
}


# -------------------------------------------- 狀態欄首詞合法值（與帳本散文雙向綁定）
# 🔴 本常數**不是權威來源**：權威是帳本主檔《格式定義》裡「**合法首詞**＝…」那一句散文，
# `_prose_status_first_words()` 會把它抽出來與本常數逐字互比，任一邊被改動而另一邊沒跟
# → rc=1 並印出兩邊差集（手法比照 `tools/tests/test_adr_xplat001_c1c2_lock.py::
# TestCriterionIsBoundToAdrProse`）。只寫一份程式常數而不綁散文，就只是多造一個 stale 站點。
#
# 刻意**不含** `workaround`：依本檔 `_STATUS_KEYWORDS` 自己的判例，`workaround` 歸類為
# `open`（以流程繞過、程式碼缺陷本身仍在），故正規寫法是 `open（workaround-applied …）`
# 而不是把 `workaround-applied` 當首詞。落地時實查主檔 94 列零命中此形態，不影響存量。
_STATUS_FIRST_WORDS = frozenset({
    "open", "routed", "fixed", "wontfix",
    "closed-by-decision", "no_action_needed", "partial",
})

# 散文抽取樣式：帳本《格式定義》§ 狀態必須有一句「**合法首詞**＝`a`／`b`／…。」
_STATUS_PROSE_RE = re.compile(r"\*\*合法首詞\*\*＝(?P<toks>[^。\n]+)。")
# 首詞＝剝掉開頭的 markdown 強調／反引號／空白後，第一段 ASCII 字母開頭的識別字。
# `[A-Za-z0-9_-]` 刻意含 `-` 與 `_`：`closed-by-decision`／`no_action_needed` 是整體一個
# 首詞；同時這也是 `partially-fixed` 被判非法的機制（它整體不在合法集合內，而**不會**
# 像 `_classify` 那樣因為尾端含 `-fixed` 就被當成 `fixed`）。
_FIRST_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_LEADING_DECOR_RE = re.compile(r"^[\s*`＊]+")


def _status_first_word(status_cell: str) -> str | None:
    """取狀態欄首詞（先剝掉 markdown 強調／反引號／空白）；辨識不出回 None。"""
    m = _FIRST_WORD_RE.match(_LEADING_DECOR_RE.sub("", status_cell))
    return m.group(0) if m else None


def _prose_status_first_words(ledger_text: str) -> tuple[frozenset[str], str | None]:
    """從帳本《格式定義》抽出散文宣告的合法首詞；抽不到回 `(frozenset(), 錯誤說明)`。

    抽不到一律 fail-loud（不得靜默退化成空集合或「全部放行」）：空集合會讓每一列都非法
    ⇒ 一次紅全部；靜默放行則讓整道鎖蒸發。兩種都是壞的失敗模式，故明確回錯誤說明。
    """
    m = _STATUS_PROSE_RE.search(ledger_text)
    if m is None:
        return frozenset(), (
            "帳本《格式定義》§ 狀態抽不到「**合法首詞**＝…。」那一句 — 狀態欄合法值的"
            "權威散文不存在或被改寫，本檔 _STATUS_FIRST_WORDS 便無從綁定。請在主檔"
            "《格式定義》的狀態條目補回該句（格式：**合法首詞**＝`open`／`routed`／…。），"
            "或同步 _STATUS_PROSE_RE 的抽取樣式"
        )
    toks = {t.strip().strip("`*＊ ") for t in m.group("toks").split("／")}
    return frozenset(t for t in toks if t), None


def status_first_word_problems(ledger_text: str) -> list[str]:
    """帳本每一列狀態欄**首詞**必須落在《格式定義》宣告的合法值集合內（純函式）。

    🔴 為何要另立這道硬斷言，而不是「`_classify` 認得就算合法」（R60 round 1 已證）：
    `_classify` 做的是「找出最早出現的已知關鍵字」，對 `partially-fixed`／`partial` 這類
    寫法，`fixed` 的邊界 lookaround 在 `-fixed` 上是成立的 ⇒ 一列「只修了一部分」在閘門
    眼中等於「已修」，而且**一句話都不會說**。本輪已把 4 筆存量非法首詞清乾淨
    （`DEF-101-556`），所以這道鎖是**零白名單**上線的——沒有任何「暫時容忍」清單可腐化。

    回傳問題清單（空＝全部合法）。抽成純函式的理由同 `archive_defect_log.
    conservation_problems()`：可直接以構造輸入證明它有牙，不必真的弄壞一份帳本。
    """
    layout = _table_layout(ledger_text)
    if layout is None:
        return [_no_header_problem()]
    ncols, id_idx, status_idx = layout
    declared, prose_problem = _prose_status_first_words(ledger_text)
    if prose_problem:
        return [prose_problem]
    problems: list[str] = []
    if declared != _STATUS_FIRST_WORDS:
        problems.append(
            f"狀態欄合法首詞的散文與程式不一致（雙向綁定失效）："
            f"散文有而程式沒有 {sorted(declared - _STATUS_FIRST_WORDS)}；"
            f"程式有而散文沒有 {sorted(_STATUS_FIRST_WORDS - declared)}。"
            f"權威是主檔《格式定義》那句散文，請把兩邊改成一致"
            f"（程式側＝{Path(__file__).name} 的 _STATUS_FIRST_WORDS）"
        )
    # 兩邊不一致時取交集當有效集合（最嚴解讀）——刻意**不**因綁定失效就跳過逐列比對，
    # 否則「改壞散文」就成了關掉整道鎖的捷徑。
    effective = declared & _STATUS_FIRST_WORDS
    for lineno, line in enumerate(ledger_text.splitlines(), 1):
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        # 欄數不符 ⇒ 表頭索引指到的不見得是狀態欄，故**不**在此列產出首詞裁決（那會是
        # 猜的），改為指名 arity 問題。這道 continue 不是靜默豁免：問題照樣進清單，且
        # `main()` 另有 `row_arity_problems()` 硬閘會先 rc=1。
        if len(cells) != ncols:
            problems.append(_arity_problem(lineno, cells, ncols))
            continue
        if not _ID_RE.fullmatch(cells[id_idx]):
            continue
        status_cell = cells[status_idx]
        first = _status_first_word(status_cell)
        if first in effective:
            continue
        # 空狀態欄要明說是「空的」：這正是 Pkg-P6 修的那個形態，若只印「首詞 None 不合法」，
        # 讀者仍可能去查左鄰的「分流去向」欄（修復前的訊息就是那樣誤導人的）。
        blank_hint = (
            f"⚠️ 該列狀態欄（第 {status_idx} 個切片）是**空的**——請填狀態，"
            f"不要誤讀左鄰欄位的文字為狀態。" if not status_cell else ""
        )
        problems.append(
            f"帳本 :{lineno} {cells[id_idx]}：狀態欄（表頭第 {status_idx} 個切片）首詞 "
            f"{first!r} 不是合法值。{blank_hint}"
            f"合法首詞＝{sorted(effective)}（權威＝主檔《格式定義》的「**合法首詞**＝…」句）。"
            f"該列切出的全部欄位＝{_cells_digest(cells)}"
        )
    return problems


def _classify(text: str) -> str | None:
    """回傳 text 中『最早出現』的已知狀態關鍵字類別；找不到回 None。"""
    best_pos: int | None = None
    best_label: str | None = None
    for label, pat in _STATUS_KEYWORDS.items():
        m = pat.search(text)
        if m and (best_pos is None or m.start() < best_pos):
            best_pos = m.start()
            best_label = label
    return best_label


def _load_ledger_status() -> dict[str, str | None]:
    """解析缺陷帳本表格列，回傳 {DEF-ID: 狀態分類}。同 ID 重複出現時，以最後一列為準——

    最後一列一律覆寫（即使該列狀態欄無法辨識任何已知關鍵字，此時存 None，代表
    「該 ID 目前狀態不明」），不會靜默沿用更早一列的舊分類值。

    狀態欄由**表頭**定位（`_table_layout()`）而非 `cells[-1]`（Pkg-P6）：保留空欄後
    `[-1]` 是表格尾端的空片段，而濾掉空欄則會讓索引隨空欄數浮動、把「分流去向」欄
    當成狀態欄讀（構造輸入實測回過 `{'DEF-01-001': 'fixed'}`，該列狀態欄其實是空的）。
    表頭抽不到時回空 dict，由 `main()` 的「解析結果為空」硬閘接手 fail-loud。
    """
    status: dict[str, str | None] = {}
    text = _DEFECT_LOG.read_text(encoding="utf-8-sig")
    layout = _table_layout(text)
    if layout is None:
        return status
    ncols, id_idx, status_idx = layout
    for line in text.splitlines():
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if id_idx >= len(cells) or not _ID_RE.fullmatch(cells[id_idx]):
            continue
        # 欄數不符 ⇒ 狀態欄位置不可信，一律記 None（狀態不明）而**不**去讀某個猜測的欄位；
        # 「不明」會被 main() 以 warning 列出，且 row_arity_problems() 已先 rc=1（第二層防線）。
        status[cells[id_idx]] = (
            _classify(cells[status_idx]) if len(cells) == ncols else None
        )
    return status


def _scan_target(path: Path, ledger: dict[str, str | None]) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8-sig")
    for m in _CLAIM_RE.finditer(text):
        ids_blob, claim_text = m.group(1), m.group(2)
        claimed = _classify(claim_text)
        if not claimed:
            continue
        for def_id in _ID_RE.findall(ids_blob):
            if def_id not in ledger:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，但缺陷帳本查無此 ID"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
                continue
            actual = ledger[def_id]
            if actual is None:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，但缺陷帳本裡該 ID 最後"
                    f"一列的狀態欄文字無法辨識任何已知關鍵字，帳本自身狀態含糊"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
            elif actual != claimed:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，帳本實際狀態為「{actual}」"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
    return problems


# 帳本輪替界線（DEF-99-001 政策：主檔 < 256KB Read 上限；DEF-101-123 機械化——
# R9 發現主檔已默默長到 272KB 超線，政策沒有任何機械守門）。
# 逼近（>= _LEDGER_WARN_BYTES）印 warning；超線（>= _LEDGER_FAIL_BYTES）直接 fail，
# 強制執行既定輪替程序（已結列搬遷 archive_NN）。
_LEDGER_WARN_BYTES = 240 * 1024
_LEDGER_FAIL_BYTES = 256 * 1024

# 🔴 R60 round 3（DEF-101-587）：體積守門的涵蓋面由「帳本家族」擴到**具名治理文件**。
#
# 為何需要：本輪把帳本改為「兩層化」——帳本列只寫摘要、完整證據（bug-injection 紅綠、
# 逐條指令與真實輸出）落在 `CrossPlatform_R60_Fix_Evidence*.md`。那些檔於是承擔了與帳本
# **同等**的可讀性義務（四方複審者要逐條重驗就得讀它們），卻**完全不在任何體積守門的
# 涵蓋面內**——實測它一度達 260,963 bytes、距上限僅 1,181 bytes。這與 `DEF-99-001`／
# `DEF-101-123` 完全同型：**政策有上限、卻無機械守門**（R9 就是這樣讓帳本默默長到 272KB）。
# 把資料搬到另一支檔就繞過守門，等於守門只綁在**檔名**上、沒綁在**義務**上。
#
# 為何用具名常數而不是 glob 整個 docs/：glob 會把不相干的檔一起管、製造誤紅，且
# 「哪些檔承擔了帳本級的可讀性義務」是**判斷**，判斷要具名、要能被 review 看見。
# 新增治理文件時在此加一筆，並在該檔內寫明它為何屬於這一類。
# 🔴 路徑刻意**不**由 `_DEFECT_LOG.parent` 推導，而是各自獨立解析：治理文件在哪，
# 與帳本主檔在哪是兩件事。前者一旦綁上後者，測試把 `_DEFECT_LOG` mock 到暫存目錄時，
# 這些檔會跟著「搬去」一個不存在的位置而被判為缺席 ⇒ 7 支既有測試假紅（落地時實際踩到）。
_GOVERNANCE_DOCS = (
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R60_Fix_Evidence.md",
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R60_Fix_Evidence_r3.md",
)


def oversize_problems(paths: list[Path]) -> tuple[list[str], list[str]]:
    """回傳 `(fail 訊息, warn 訊息)`。純函式化的理由同 `conservation_problems()`：
    可直接以構造輸入證明它有牙，不必真的把 repo 檔案養大。

    門檻與帳本共用 `_LEDGER_*_BYTES`——**因為上限的來源是同一個**：262,144 是
    **Read 工具單次讀取上限**（不是 git、不是 markdown 的限制），對帳本與對證據檔
    是同一條物理界線。共用常數即「同一個量只有一個答案」。
    """
    fails, warns = [], []
    for p in paths:
        if not p.exists():
            fails.append(
                f"具名治理文件不存在：{p.name} — 涵蓋面已與磁碟脫節，拒絕靜默跳過"
                f"（跳過就等於這一份檔的體積守門被悄悄拿掉）"
            )
            continue
        n = p.stat().st_size
        if n >= _LEDGER_FAIL_BYTES:
            fails.append(
                f"{p.name} {n} bytes ≥ 上限 {_LEDGER_FAIL_BYTES}（Read 工具單次讀取上限）"
                f"——複審者將無法一次讀完本檔。請比照 DEF-101-587 的做法拆分："
                f"原檔留在原地當**入口**（帳本有多處指向它，改名會讓那些指針全部失實），"
                f"新增姊妹檔承載較新的節，並在入口檔開頭維護「哪些 DEF-ID 在哪一份檔」對照表"
            )
        elif n >= _LEDGER_WARN_BYTES:
            warns.append(
                f"{p.name} {n} bytes 已逼近上限 {_LEDGER_FAIL_BYTES}"
                f"（距 {_LEDGER_FAIL_BYTES - n} bytes），請規劃拆分——"
                f"append 前務必先 `wc -c`"
            )
    return fails, warns


def main() -> int:
    if not _DEFECT_LOG.exists():
        print(f"❌ 找不到缺陷帳本：{_DEFECT_LOG}", file=sys.stderr)
        return 1
    ledger_bytes = _DEFECT_LOG.stat().st_size
    if ledger_bytes >= _LEDGER_FAIL_BYTES:
        print(f"❌ 缺陷帳本主檔 {ledger_bytes} bytes ≥ 輪替上限 {_LEDGER_FAIL_BYTES}"
              "（DEF-99-001 政策 <256KB）——請將已結列搬遷至下一個 "
              "AutoSDD_Defect_Log_archive_NN.md（參照 DEF-101-123 之 R9 輪替程序）",
              file=sys.stderr)
        return 1
    if ledger_bytes >= _LEDGER_WARN_BYTES:
        print(f"⚠️  缺陷帳本主檔 {ledger_bytes} bytes 已逼近輪替上限 "
              f"{_LEDGER_FAIL_BYTES}（DEF-99-001 政策），請規劃已結列搬遷 archive",
              file=sys.stderr)
    # DEF-99-001 政策同時要求「每一個 archive 檔」< 256KB（單一 archive 逼近即拆下
    # 一個 archive）——Architect 二審 OBS-3：守門不可只量主檔。
    for arch in sorted(_DEFECT_LOG.parent.glob("AutoSDD_Defect_Log_archive_*.md")):
        arch_bytes = arch.stat().st_size
        if arch_bytes >= _LEDGER_FAIL_BYTES:
            print(f"❌ 帳本歸檔 {arch.name} {arch_bytes} bytes ≥ 上限 "
                  f"{_LEDGER_FAIL_BYTES}（DEF-99-001 政策）——請拆分至下一個 archive_NN",
                  file=sys.stderr)
            return 1
        if arch_bytes >= _LEDGER_WARN_BYTES:
            print(f"⚠️  帳本歸檔 {arch.name} {arch_bytes} bytes 已逼近上限 "
                  f"{_LEDGER_FAIL_BYTES}（DEF-99-001 政策），請規劃拆分", file=sys.stderr)
    # 具名治理文件的體積（DEF-101-587）——與帳本同一條物理界線，見 `oversize_problems()`。
    gov_fails, gov_warns = oversize_problems(list(_GOVERNANCE_DOCS))
    for w in gov_warns:
        print(f"⚠️  治理文件 {w}", file=sys.stderr)
    if gov_fails:
        for f in gov_fails:
            print(f"❌ 治理文件 {f}", file=sys.stderr)
        return 1
    ledger_text = _DEFECT_LOG.read_text(encoding="utf-8-sig")

    # 欄位切分結構硬閘（Pkg-P6）——擺在**所有**解析之前：表頭定位或欄數一旦不對，
    # 「狀態欄」讀到的可能根本是別欄，下游兩道檢查的結論就都建立在錯欄位上
    # （修復前實測：狀態欄空白 + 分流去向以 `open` 開頭 ⇒ 兩道檢查同時零訊號）。
    arity_problems = row_arity_problems(ledger_text)
    if arity_problems:
        print(f"❌ 帳本表格欄位切分結構不合（{len(arity_problems)} 筆）：", file=sys.stderr)
        for p in arity_problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    ledger = _load_ledger_status()
    if not ledger:
        print("❌ 缺陷帳本解析結果為空 — 表格格式可能已改版導致比對邏輯失效，"
              "請同步本腳本的 _ROW_RE / 欄位解析", file=sys.stderr)
        return 1

    # 狀態欄首詞合法值硬斷言（SA-R60R2-06）——擺在跨文件比對**之前**：帳本自身的狀態欄
    # 若寫得不合法，跨文件一致性的結論就建立在含糊的基礎上（round 1 已證 `partially-fixed`
    # 會靜默命中 `fixed`，而本檔對非法首詞原本一句話都不說）。
    first_word_problems = status_first_word_problems(ledger_text)
    if first_word_problems:
        print(f"❌ 帳本狀態欄首詞不合法（{len(first_word_problems)} 筆）：", file=sys.stderr)
        for p in first_word_problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    # 「有效」與「含糊」分開呈現（R9 跨平台複審：舊版把 _classify 回 None 的列
    # 也一併計入「有效狀態紀錄」總數，帳本自身品質問題被靜默吞掉）。
    # 含糊 >0 只印 warning 不 fail：這是帳本品質提示，非跨文件矛盾。
    vague_ids = sorted(def_id for def_id, cls in ledger.items() if cls is None)
    if vague_ids:
        print(f"⚠️  帳本狀態含糊 {len(vague_ids)} 筆（狀態欄辨識不出已知關鍵字）："
              f"{'、'.join(vague_ids)}", file=sys.stderr)

    all_problems: list[str] = []
    for target in _CROSSREF_TARGETS:
        if not target.exists():
            print(f"❌ 找不到掃描目標：{target}", file=sys.stderr)
            return 1
        all_problems.extend(_scan_target(target, ledger))

    if all_problems:
        print(f"❌ 缺陷帳本跨文件狀態不一致（{len(all_problems)} 筆）：", file=sys.stderr)
        for p in all_problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    vague_note = f"（另 {len(vague_ids)} 筆狀態含糊，見 warning）" if vague_ids else ""
    print(f"✅ 缺陷帳本跨文件狀態一致：帳本 {len(ledger) - len(vague_ids)} 筆有效狀態紀錄"
          f"{vague_note}、{len(_CROSSREF_TARGETS)} 份掃描目標皆無矛盾；"
          f"另全部表格列的狀態欄首詞皆落在《格式定義》宣告的 {len(_STATUS_FIRST_WORDS)} 個"
          "合法值內（散文與程式常數雙向綁定）；"
          "全部表格列的欄數皆等於表頭欄數、狀態欄由表頭定位（非 cells[-1] 位置猜測）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
