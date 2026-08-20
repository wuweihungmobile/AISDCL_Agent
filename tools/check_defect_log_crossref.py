#!/usr/bin/env python3
"""缺陷帳本 × 高風險文件「狀態宣稱」跨文件一致性機械守護（DEF-101-068(e) 落地）。

🔴 本工具的邊界（務必先讀，比照 `check_script_parity.py` docstring 風格誠實承認侷限）：
本工具**不理解自然語言**，只做「正則抽取 + 關鍵字比對」兩件事：
  1. 在掃描目標文件中找出「一個或多個 `DEF-\\d+-\\d+` 緊接著一個括號」的樣式
     （括號可為全形｀（）｀或半形｀()｀；ID 前後允許 markdown 粗體 `**`）。
  2. 從該括號內文字裡找出**最早出現**的已知狀態關鍵字
     （`open` / `routed` / `fixed` / `wontfix` / `closed-by-decision`；另有兩個歸類詞
     `workaround` 與 `partial` 一併歸入 `open`，見 `_STATUS_KEYWORDS`），
     視為該文件對這個/這些 DEF ID 的「狀態宣稱」。合法首詞集合的權威在帳本
     《格式定義》散文，且**每一個合法首詞都必須能被 `_classify()` 分類**
     （硬斷言，見 `unclassifiable_first_word_problems()`）。
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

第三件本檔**會**做的事（R60 round 3 Pkg-P6，且是上面兩件事的**前提**）：每一缺陷列切出
的欄數必須等於表頭欄數（`row_arity_problems()`），且「狀態欄」一律由**表頭**定位
（`_table_layout()`）而非取 `cells[-1]`——位置依賴在狀態欄留空時會靜默位移到左鄰的「分流
去向」欄，使上面兩道檢查同時零訊號。構造復現輸入與逐項實測見 `row_arity_problems()`
docstring 與 `tools/tests/test_check_defect_log_crossref.py`
::`TestRowArityAndHeaderAnchoredStatusColumn`。

🔴 **表頭同形性的正確說法（R60 round 3 SA-R60R3-02 訂正）**：該性質只對「具表格表頭的
那些檔」成立——家族內另有一批純散文 archive 根本沒有表格，把它宣稱到整個家族上比數字
過期更重一層。正確斷言＝那些檔的表頭切片數全部同形（首尾空片段 ＋ 資料欄，狀態欄恆為
最後一個資料欄）。檔數與切片數一律**現查**（`archive_defect_log._family_files()`／
`_table_layout()`），本 docstring 不寫死任一個（Scan-H 必跑項 #3）。
機械守門＝`tools/tests/test_check_defect_log_crossref.py::TestFamilyHeaderUniformity`。

⚠️ arity 檢查的作用範圍**僅主檔**（`_DEFECT_LOG`）：`DEF-101-560` 具名不修的 archive 側
既有壞列不會被本檢查誤紅（筆數由 `archive_defect_log._ARITY_BASELINE` 逐檔登記並帶 stale
自檢，本檔不複寫）。這**不是**靜默豁免——那些列一旦被搬進主檔就會當場紅。
（🔴 訂正：本段原稱「本檔對 archive 只量大小、從不解析其表格列」，該句自
`_load_archive_status()` 落地起即為假——archive 會被解析，只是不參與 arity 判定。）

使用：
  python3 tools/check_defect_log_crossref.py   # 於 repo 內任意 cwd；不一致印清單並 exit 1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護
from lib import defect_ledger_index as _ledger_index  # noqa: E402
from lib import governance_docs as _gov_docs  # noqa: E402
from lib import ledger_rotation as _rotation  # noqa: E402
from lib import ledger_staleness as _staleness  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFECT_LOG = _REPO_ROOT / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
# 不可變的預設值副本：`_DEFECT_LOG` 會被測試以 mock 換成合成 fixture，而「存量豁免
# 名單是否已 stale」只在餵真實主檔時才有意義（見 main() 內該道的綁定說明）。
_DEFAULT_DEFECT_LOG = _DEFECT_LOG
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

# 🔴 R69 `DEF-101-735` — ADR 目錄納入掃描面。
#
# 原始缺陷（終審 P2 #17）：`ADR-XPLAT-002`／`ADR-XPLAT-003` 各有一處宣稱「`DEF-101-706` 隨之
# 結案」，而同輪帳本該列狀態欄是 `partial`（明寫「解鎖條件①未達標故不結案」）——兩份活文件
# 對同一個 ID 各說各話，而 ADR 不在掃描面內故**機械上完全盲**（理由同 `SD10_PG_Contract_
# NextAction.md` 當年被納入：該檔也曾同檔內自相矛盾，差別只在沒人想到 ADR 也會做狀態宣稱）。
# **用 glob 不逐支具名**：ADR 持續新增（本輪即新增 XPLAT-003），具名清單必漏掉下一支而漏掉
# 零訊號＝本缺陷的形狀；命名慣例 `ADR-*.md` 本身即註冊機制。**誠實劃界**：只掃根層
# `docs/04_planning/ADR/`；子專案各自的 ADR 不在內——那要先定義「哪一本帳」，是另一個決定。
_ADR_DIR = _REPO_ROOT / "docs" / "04_planning" / "ADR"
_ADR_GLOB = "ADR-*.md"
_CROSSREF_TARGETS += sorted(_ADR_DIR.glob(_ADR_GLOB))

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
# 表頭列＝第一個資料欄為 `ID`。帳本家族內**具表格表頭的**檔皆為此形態、切片數同形
# （SA-R60R3-02 訂正：原寫「家族 32 檔皆為此形態」，家族檔數現查非 32，且家族內另有一批
# 純散文 archive 根本沒有表格 ⇒ 該性質只對「具表頭的檔」成立。檔數／切片數一律現查，
# 見模組 docstring「表頭同形性的正確說法」段）。
_HEADER_RE = re.compile(r"^\|\s*ID\s*\|")
_ID_HEADER = "ID"
_STATUS_HEADER = "狀態"
_CONTEXT_HEADER = "發現情境"


def _row_cells(line: str) -> list[str]:
    """切出表格列的**全部**欄位並各自 strip，**保留空欄**（含首尾的空片段）。

    🔴 絕對不可再寫回 `[... for c in ... if c.strip()]`：`if c.strip()` 把空欄濾掉，
    欄位索引就會隨「該列有幾個空欄」浮動，於是狀態欄留空時 `cells[-1]` 靜默位移到
    左邊的「分流去向」欄（Pkg-P6 修的正是這個；復現輸入見模組 docstring 第三件事）。
    保留首尾空片段是刻意的：拿它跟表頭的切片數直接對齊即為 arity 檢查，不需另外
    猜「這列有沒有寫尾端豎線」。
    """
    return [c.strip() for c in _CELL_SPLIT_RE.split(line)]


def _header_cells(ledger_text: str) -> list[str] | None:
    """回傳帳本**第一個**合格表頭的全部切片；找不到回 `None`。

    抽成獨立函式是為了讓「用欄名定位」這件事有唯一實作：`_table_layout()` 取
    `ID`／`狀態` 三元組，`current_round()` 另需 `發現情境` 欄，兩者若各自重寫一次
    表頭掃描，就是本 repo 反覆在治的複本型缺陷（見 R57「靜態掃描錨為何從三份複本
    收斂為 SSOT」判例：觀測同一對象的複本不產生鑑別力）。
    """
    for line in ledger_text.splitlines():
        if not _HEADER_RE.match(line):
            continue
        cells = _row_cells(line)
        if _ID_HEADER in cells and _STATUS_HEADER in cells:
            return cells
    return None


def _table_layout(ledger_text: str) -> tuple[int, int, int] | None:
    """回傳帳本表頭的 `(切片數, ID 欄索引, 狀態欄索引)`；找不到合格表頭回 `None`。

    取**第一個**合格表頭：主檔實查只有一個（`:34`）。刻意用欄名（`ID`／`狀態`）定位而
    非寫死索引，欄序若被調動也能跟上；欄名被改寫則回 `None` → 呼叫端 fail-loud。
    """
    cells = _header_cells(ledger_text)
    if cells is None:
        return None
    return len(cells), cells.index(_ID_HEADER), cells.index(_STATUS_HEADER)


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
    # `partial`＝只修了一部分，缺陷本身仍在 → 同樣歸類 open（R60 round 3 SA-R60R3-07）。
    # 🔴 為何非補不可：`partial` 是《格式定義》宣告的**合法**首詞，卻沒有任何分類器對應
    # ⇒ `_classify('partial（只修了一半）')` 回 None ⇒ 該列落進 `main()` 的「狀態含糊」桶，
    # 而含糊桶**只印 warning、永不 fail**。DEF-101-556 要消滅的「只修一半被當成已修」
    # 於是並未消失，只是從「靜默算 fixed」搬到「靜默算含糊」——同一個軟出口換個門牌。
    # 歸 `open` 而非另立一類，是照本表既有的 `workaround` 判例（缺陷本體仍在＝未結案），
    # 也讓「文件寫 open、帳本寫 partial」不會變成一筆假矛盾。
    # ⚠️ 邊界：`partially-fixed` **不會**命中此樣式（`partial` 後接 `l` 使 lookahead 不成立），
    # 它仍由 `status_first_word_problems()` 判為非法首詞而硬紅——那道鎖才是它的歸屬。
    "open": re.compile(
        r"(?<![A-Za-z0-9])open(?![A-Za-z0-9])|workaround"
        r"|(?<![A-Za-z0-9])partial(?![A-Za-z0-9])"
    ),
}


# -------------------------------------------- 狀態欄首詞合法值（與帳本散文雙向綁定）
# 🔴 本常數**不是權威來源**：權威是帳本主檔《格式定義》裡「**合法首詞**＝…」那一句散文，
# `_prose_status_first_words()` 會把它抽出來與本常數逐字互比，任一邊被改動而另一邊沒跟
# → rc=1 並印出兩邊差集（手法比照 `tools/tests/test_adr_xplat001_c1c2_lock.py::
# TestCriterionIsBoundToAdrProse`）。只寫一份程式常數而不綁散文，就只是多造一個 stale 站點。
#
# 刻意**不含** `workaround`：依本檔 `_STATUS_KEYWORDS` 自己的判例，`workaround` 歸類為
# `open`（以流程繞過、程式碼缺陷本身仍在），故正規寫法是 `open（workaround-applied …）`
# 而不是把 `workaround-applied` 當首詞。落地時實查主檔零命中此形態，不影響存量。
#
# 🔴 本集合另受一道硬斷言管：**每一個合法首詞都必須能被 `_classify()` 分類**
# （`unclassifiable_first_word_problems()`）。少了它，「加一個合法首詞卻忘了加分類器」
# 這整個類別就會靜默落進 `main()` 的 warning-only 含糊桶——`partial` 正是這樣混進來的
# （SA-R60R3-07）。兩份常數互綁的手法比照本檔既有的「散文 ↔ `_STATUS_FIRST_WORDS`」綁定。
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


def unclassifiable_first_word_problems() -> list[str]:
    """硬斷言：`_STATUS_FIRST_WORDS` 的**每一個**合法首詞都必須能被 `_classify()` 分類。

    🔴 原始缺陷（R60 round 3 SA-R60R3-07）：`partial` 是《格式定義》宣告的合法首詞，
    卻沒有任何 `_STATUS_KEYWORDS` 條目對應 ⇒ `_classify('partial（…）')` 回 `None`
    ⇒ 該列被 `_load_ledger_status()` 記成「狀態不明」，而 `main()` 對含糊列**只印
    warning、永不 fail**。於是 `DEF-101-556` 要消滅的「只修一半被當成已修」並沒有消失，
    只是從「靜默算 fixed」搬到「靜默算含糊」——換個門牌的同一個軟出口。

    🔴 為何要立**這道通用鎖**而不是只補 `partial` 一個分類器（主控與本包的一致判斷）：
    只補分類器修的是**這一個實例**，鎖的是「未來再加一個合法首詞卻忘了加分類器」的
    **整個類別**。兩者不是二擇一——分類器是修復、本鎖是防復發，本包兩件都做：沒有分類器
    修復，本鎖上線當場紅；沒有本鎖，下一個新首詞會用完全一樣的路徑再溜進含糊桶一次。

    手法比照本檔既有的「散文 ↔ `_STATUS_FIRST_WORDS` 雙向綁定」：把兩份程式常數互綁，
    任一邊被改而另一邊沒跟就 fail-loud 並逐字指出是哪一個詞。判定對象刻意是**程式常數**
    而非散文抽出的集合——散文那一側已由 `status_first_word_problems()` 綁住，兩道鎖串起來
    即為「散文 → 程式常數 → 分類器」的完整鏈；任一環斷掉都有一道鎖會說話。

    回傳問題清單（空＝全部可分類）。純函式、零參數：判定只依賴本檔兩份模組常數。
    """
    orphans = sorted(w for w in _STATUS_FIRST_WORDS if _classify(w) is None)
    if not orphans:
        return []
    return [
        f"合法首詞 {orphans} 沒有任何 _STATUS_KEYWORDS 分類器對應 —— "
        f"`_classify()` 對它們回 None，於是這些列會落進 main() 的「狀態含糊」桶，"
        f"而含糊**只印 warning、永不 fail**（＝一個靜默軟出口，SA-R60R3-07）。"
        f"請在 _STATUS_KEYWORDS 補上對應樣式並寫明歸類理由"
        f"（既有判例：`workaround`／`partial` 皆歸 `open`，因為缺陷本體仍在），"
        f"或把該詞從《格式定義》散文與 _STATUS_FIRST_WORDS 一併移除"
    ]


# ------------------------------------------------ 硬規則②：孤兒承接輪次（R67 落地）
# 規格權威＝`docs/06_quality/CrossPlatform_Scan_Dimensions.md`〈使用方式〉硬規則②那一段，
# 逐字判準：「狀態仍為 `open`／`deferred` 的列若提及一個 `R\d+` **承接者**，該輪號必須
# ≥ 當前輪，或該列／有一筆更新的 DEF 條目載明『改派』」。該段同時**指名本檔為宿主**。
# 兩邊由 `tools/tests/test_check_defect_log_crossref.py::TestHardRule2IsBoundToSpecProse`
# 雙向綁定：散文改寫或本函式改名而另一邊沒跟 → 紅。
#
# 🔴 這道鎖非踩不可的坑（R59 二審 ARCH-R59-NB4 明文警告，規格段落亦轉述）：缺陷帳本是
# **逐字保全的歷史檔**，`DEF-101-500` 那列會永遠留著「列 R58 backlog」字樣。所以判準
# **不能**寫成「不得提及不存在的輪次」——那會讓閘門**永紅**。合法出口有二：
#   (a) 該列狀態已非 open／routed（歷史列多半如此，本檔直接排除）；
#   (b) 該列或**更後面**（append-only ⇒ 更新）的任一列載明「改派」／「回執」。
#
# 🔴 第二個坑（R67 落地前實測，掃描員的 proposed_fix 正是踩在這裡）：**不可以拿整列的
# 任一個 `R\d+` 當承接者**。實測把「列內最大 `R\d+`」當承接輪次套回主檔，70 列未結列中
# **60 列**會被判孤兒——因為「發現情境」「R60 實測」「R25 Scan-A 複核」這些是**發現/佐證
# 輪次**，不是承接者。故本檔只認**承接語境**的樣式（下表），寧可漏抓也不製造假紅：一道
# 永紅或大量假紅的閘門會被整個關掉，那比沒有鎖更糟。
_ROUND_RE = re.compile(r"(?<![A-Za-z0-9])R(\d+)(?![0-9])")
# 承接語境與輪號之間允許的裝飾（markdown 粗體／反引號／空白）。
_HANDOVER_DECOR = r"[*＊`\s]{0,4}"
# 🔴 `列` 的否定回顧刻意排除「本列／該列／此列／上列／前列／系列」：實測 `DEF-101-068`
# 的「本列 R14 快照所稱…」是**引述舊快照**，不是交棒；漏掉這個回顧即產生假紅。
_HANDOVER_ROUND_RES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("承接輪次／承接者", re.compile(r"承接(?:輪次|者)?[：:＝=為]?" + _HANDOVER_DECOR + r"R(\d+)")),
    ("R… 承接",
     re.compile(r"R(\d+)\+?" + _HANDOVER_DECOR + r"(?:起)?" + _HANDOVER_DECOR + r"承接")),
    ("列 R…（backlog 指派）", re.compile(r"(?<![本該此上前系])列" + _HANDOVER_DECOR + r"R(\d+)")),
    ("backlog R…", re.compile(r"backlog[\s*＊`]{0,4}R(\d+)")),
    ("交棒／移交／交由 R…",
     re.compile(r"(?:交棒|移交|交由)(?:給|至|到|由)?" + _HANDOVER_DECOR + r"R(\d+)")),
)
# 🔴 刻意**不**把 `routed@R61`／`deferred@R59` 當承接者：實測 `DEF-101-518` 寫
# `**routed（deferred@R59，附解鎖條件）**`，那個 `@R59` 是「在 R59 這一輪被 defer」的
# **時點**，不是被指派的對象（同族寫法 `fixed@R57` 更明顯）。把時點當承接者會製造假紅。
# 🔴 R74 PKG-2：出口判準本體與它五種「白拿豁免」形態的處置外移至
# `_ledger_index.reassign_hit()`（只判**狀態欄**、先遮 code span、擋否定語意）——WHY 見該處。
_REASSIGN_RE, _reassign_hit = _ledger_index.REASSIGN_RE, _ledger_index.reassign_hit
_UNRESOLVED_CLASSES = _ledger_index.UNRESOLVED_CLASSES


def current_round(ledger_text: str) -> int | None:
    """從帳本「發現情境」欄推得**當前輪次**；推不出回 `None`。

    🔴 為何是這個取值方式（三個候選都試過，這是唯一不會 stale 也不會取錯的）：
      · **不寫死常數**——下一輪就過期，正是本 repo 反覆在治的病（`Scan_Dimensions.md`
        開頭那句「本檔刻意不寫死輪號」即為同一個教訓）。
      · **不用 `docs/04_planning/` 現存最大號 `AutoSDD_improving_NN`**（掃描員的建議）：
        兩套編號**不是同一個東西**——實查該目錄最大號已達三位數，而跨平台複審輪號還在
        兩位數。拿它當「當前輪」會讓每一列的承接輪號都遠小於它 ⇒ 整本帳本瞬間全紅。
      · **用「發現情境」欄的最大 `R\\d+`**：`Scan_Dimensions.md` 開頭已明文宣告
        「最新輪次見 `AutoSDD_Defect_Log.md` 最末列」，本函式即該宣告的機械化；取
        **最大值**而非「最末列」是因為 append 順序不保證輪號單調，取最大值只會讓判準
        **更寬**（承接輪號更容易 ≥ 當前輪），只會漏抓、不會假紅。
      · 邊界：帳本輪替（已結列搬 archive）若把最新一輪的列全搬走，本值會**變小**⇒ 判準
        變寬。這是刻意選的失效方向（漏抓而非假紅），且活躍列依政策一律留主檔。
    """
    cells = _header_cells(ledger_text)
    if cells is None or _CONTEXT_HEADER not in cells:
        return None
    ncols, ctx_idx = len(cells), cells.index(_CONTEXT_HEADER)
    best: int | None = None
    for line in ledger_text.splitlines():
        if not _ROW_RE.match(line):
            continue
        row = _row_cells(line)
        if len(row) != ncols:
            continue
        for m in _ROUND_RE.finditer(row[ctx_idx]):
            n = int(m.group(1))
            if best is None or n > best:
                best = n
    return best


def _handover_rounds(line: str) -> list[tuple[str, int, str]]:
    """抽出一列中所有**承接語境**的輪號 `(樣式名, 輪號, 原文片段)`。"""
    found: list[tuple[str, int, str]] = []
    for label, pat in _HANDOVER_ROUND_RES:
        for m in pat.finditer(line):
            snippet = line[max(0, m.start() - 22): m.end() + 14]
            found.append((label, int(m.group(1)), snippet))
    return found


def orphan_backlog_problems(ledger_text: str) -> list[str]:
    """硬規則②的機械化：未結案列指名的承接輪次不得早於當前輪（純函式）。

    回傳問題清單（空＝無孤兒）。純函式化的理由同 `status_first_word_problems()`：
    可直接以構造輸入證明它有牙，不必真的弄壞一份帳本。

    **已實測涵蓋**（每一項都以構造輸入跑過，見 `TestOrphanBacklogProblems`）：
      · `open（承接輪次：**R2**…）`／`承接者＝R2`／`仍待 R2+ 承接者處理`
      · `列 R2 backlog`／`open（backlog R2…）`／`交棒給 R2`
      · 未結案（`open`／`routed`／狀態含糊）才判；已 `fixed`／`wontfix`／
        `closed-by-decision` 的歷史列一律不判（歷史檔逐字保全，見上方第一個坑）。
      · 該列**狀態欄**（或更後面提及本列 ID 的那一列的狀態欄）載明「改派」／「回執」
        即放行；判定走 `_reassign_hit()`（R74 起只判狀態欄、遮 code span、擋否定語意）。
        🔴 R84（`DEF-200-088`）：**跨列**那一半此後同樣要比輪號——該回執列的狀態欄必須
        指名一個 ≥ 當前輪的 `R\\d+`，否則不算出口（回執一寫就永久有效＝同一個洞的另一半）。

    **已實測不涵蓋**（逐項跑過，並釘成常駐斷言）：
      · **跨列**：更後面那一列的認定條件只是「該列提及本列 ID」這個弱條件；「哪一列才算
        更新的紀錄」需要語意判斷，不在逐行正則的能力內（輪號新鮮度已補，見上）。
      · **`status@Rnn` 形態**（`deferred@R59`）刻意不當承接者，理由見 `_REASSIGN_RE`
        上方註解。若未來有人真的用 `@Rnn` 表示指派對象，本鎖抓不到。
      · **散文式指派**（「留給下一輪某人」）無 `R\\d+` ⇒ 由後半句 `unpinned_...()` 接手。
    **未窮舉**：本清單非窮舉，不做「唯一殘餘風險是 X」這類宣稱（R57 判例第 (4) 條）。
    """
    layout = _table_layout(ledger_text)
    if layout is None:
        return [_no_header_problem()]
    ncols, id_idx, status_idx = layout
    rows: list[tuple[int, list[str], str]] = []
    for lineno, line in enumerate(ledger_text.splitlines(), 1):
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if len(cells) != ncols or not _ID_RE.fullmatch(cells[id_idx]):
            continue
        rows.append((lineno, cells, line))

    cur = current_round(ledger_text)
    problems: list[str] = []
    for i, (lineno, cells, line) in enumerate(rows):
        if _classify(cells[status_idx]) not in _UNRESOLVED_CLASSES:
            continue
        handovers = _handover_rounds(line)
        if not handovers:
            continue
        if _reassign_hit(cells[status_idx]):
            continue
        def_id = cells[id_idx]
        # 🔴 R84（`DEF-200-088`）：跨列出口先前只取布林 ⇒ 回執一寫就永久免比輪號。輪號從
        # 回執列狀態欄以 `_ROUND_RE` **粗抓取最大值**（回執體例「一律改派 **R<n>**」不落在
        # `_HANDOVER_ROUND_RES` 的承接樣式內），刻意偏寬＝漏抓而非假紅，同本檔既有方向。
        # 回執寫字面「未指派」者照放——那是硬規則② 後半句自己給的二擇一，判它等於關掉出口。
        floor = cur if cur is not None else -1
        if any(def_id in ln and _reassign_hit(c[status_idx])
               and (_UNASSIGNED_LITERAL in c[status_idx]
                    or max((int(x.group(1)) for x in _ROUND_RE.finditer(c[status_idx])),
                           default=-1) >= floor)
               for _, c, ln in rows[i + 1:]):
            continue
        if cur is None:
            problems.append(
                f"帳本 :{lineno} {def_id}：本列指名了承接輪次"
                f"（{'；'.join(f'[{lb}] R{n}' for lb, n, _ in handovers)}），"
                f"但無法從「{_CONTEXT_HEADER}」欄推得當前輪次 ⇒ 硬規則②「該輪號必須 ≥ "
                f"當前輪」失去比較基準。請確認主檔表頭含「{_CONTEXT_HEADER}」欄、"
                f"且至少一列的該欄寫有 `R<數字>`（權威宣告見 "
                f"CrossPlatform_Scan_Dimensions.md 開頭「最新輪次見帳本最末列」）"
            )
            continue
        newest = max(n for _, n, _ in handovers)
        if newest >= cur:
            continue
        detail = "；".join(f"[{lb}] R{n}：{sn!r}" for lb, n, sn in handovers)
        problems.append(
            f"帳本 :{lineno} {def_id}：狀態仍未結案，卻把承接者指向 **R{newest}**，"
            f"早於當前輪 R{cur} ⇒ 孤兒 backlog（硬規則②，見 "
            f"CrossPlatform_Scan_Dimensions.md〈使用方式〉）。命中片段＝{detail}。"
            f"兩條合法出口（擇一，**不要改寫歷史原文**）："
            f"① 就地於狀態欄追加一筆載明「改派」的附記（體例比照 DEF-101-333／336／338 "
            f"的『改派為：未指派 backlog』＋解鎖條件）；"
            f"② 若該輪已交出成果，就地追加「回執」並把狀態改為已結案的首詞"
        )
    return problems


# -------------------------------- 硬規則② 的**另一半**：二擇一（R68，DEF-101-708）
# 🔴 為何非補不可（R68 沙箱普查實測，HEAD 版工具 × HEAD 版帳本）：硬規則② 的散文是
# 「任何 `deferred`／`backlog` 必須指向一個存在的輪次**或明確標為「未指派」**」，而
# `orphan_backlog_problems()` 只落地了前半句（輪號比大小）。後半句在程式裡的形態是
# `if not handovers: continue` ——**一個短路出口**：整列找不到承接語境輪號就直接放行。
# 實測後果：R68 上線時絕大多數未結列既無承接輪號也無「未指派」，全部從短路出口走掉，
# 其中大半帶「排入下一輪」「擇機」「留待下輪」這類**散文式延後**——規則想擋的正是它們。
# （逐項實數一律現查：`--unresolved-count` ＋ 下方白名單筆數，此處刻意不寫死快照。）
#
# 🔴 為何要 grandfather 白名單而不是直接硬擋（ARCH-R59-NB4 的永紅警告仍然適用）：
# 那批是**存量歷史列**，一次全紅等於閘門上線即永紅，而永紅的閘門會被整個關掉，比沒有鎖
# 更糟。所以照 R59 判例採「釘現況 ＋ 只硬擋新增列」：白名單是**棘輪**，只准變小
# （`_UNPINNED_HANDOVER_CEILING`），且列在裡面卻**已經不需要**豁免的 ID 一律 fail-loud
# 要求刪除（見 `stale_grandfather_problems()`）——沒有這一條它會變成只進不出的死名單。
# 判準沿用 repo 內**既有形態**而非新造：`tools/check_script_parity.py` 的
# `_UNPINNED_EXIT_RE`（`退場：(未指派|R\d+…)`）就是同一個「二擇一」判準的先例。
_UNASSIGNED_LITERAL = "未指派"

#: R68 上線時**釘死現況**的存量未結列（既無承接輪號、也無「未指派」）。
#: 🔴 這張表只准變小。新增未結列一律不得進入本表——那是硬擋的對象。
#: 🔴 R74 首次真正轉動本棘輪（R70~R73 三輪零收縮）：56 → 48。逐筆處置見缺陷帳本各列：
#: `432`／`416` 回樹實查後結案、`417`／`393` 依自述 wontfix 判例訂正首詞、`674` 缺口已
#: 收掉、`271`／`274`／`388` 改走合法出口②「未指派」＋可執行解鎖條件。
#: 🔴 R75 第二次轉動：48 → 36。刪掉的 12 筆全是「早就修好、只有首詞沒跟上」，逐筆回樹複驗
#: 後結案（指令＋rc 見帳本該列「R75 複驗」段）⇒ 依「已結案」條款不再需要豁免。
#: 🔴 第三次轉動：36 → 34。刪掉 `DEF-101-278`（腳本對等閘摘要句）與 `DEF-101-297`
#: （pre-commit 控制字元閘漏內嵌換行）——兩筆皆**真的修掉**並附紅→綠實測，逐筆證據見
#: `docs/06_quality/CrossPlatform_R78_Debt_Audit.md` §一（該檔另載本輪未結的 82 筆分類）。
#: 🔴 輪號刻意不寫進本檔散文：程式碼檔的輪號標籤受
#: `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 管，不得超前帳本「發現情境」欄
#: 推得的當前輪——而帳本時鐘在本輪第一列落地前仍停在上一輪，本次即實測當場轉紅。
#: 🔴 第四次轉動：34 → 28（R80 包 C，見上一段）。
#: 🔴 第五次轉動：28 → 18。刪掉的 10 筆分兩類，都是判準訊息**自己指名**的動作：
#:   · **已結案 2 筆**——`DEF-42-001`（凍結版 v0.17 的 flaky，`closed-by-decision`）與
#:     `DEF-53-001`（`hub_merge._read_yaml` 讀取上限已補，`fixed`）。
#:   · **已補標承接輪號 8 筆**——`DEF-101-018`／`060`／`243`／`268`／`296`／`398`／
#:     `399`／`402` 各自就地寫上「改派，承接輪次：<下一輪>」＋一句「為什麼本輪做不完」，
#:     於是它們滿足了硬規則② 後半句的二擇一，不再需要豁免。
#: 🔴 具體輪號刻意不寫進本檔散文：程式碼檔的輪號標籤受
#: `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 管，不得超前帳本「發現情境」欄
#: 推得的當前輪，而「交棒給下一輪」的輪號依定義就是當前輪＋1 ⇒ 寫進來即當場轉紅
#: （本輪實測撞到）。輪號的唯一真相源是帳本那八列自己。
#: 逐筆理由與當回合實查證據見 `docs/06_quality/CrossPlatform_R81_Ledger_Triage.md` §5。
#: 🔴 第六次轉動：18 → 17。刪掉 `DEF-101-234`——該列自述為 touch-it-fix-it watch、
#: 無獨立行動項也無 owner，帳本清債包實查其前提（`check_script_parity._EXEMPT_PAIRS`
#: 兩對皆仍帶文件化豁免與決策依據，且 `run_self_evolution` 另已補上退出碼契約三方鎖）
#: 後改為 `closed-by-decision`，依「已結案」條款不再需要豁免。刪除＋同步下修正是
#: `stale_grandfather_problems()` 訊息**自己指名**的動作，不是放寬。
#: 🔴 第七次轉動：17 → 6。R82 帳本清債包一次結掉 11 筆（`DEF-101-055`／`214`／`217`／
#: `308`／`309`／`313`／`335`／`348`／`400`／`401`／`412`），逐筆的當回合複驗證據與
#: 原列逐字原文見 `CrossPlatform_R82_Ledger_Closure.md` §8。已結案 ⇒ 依「三選一即算不再
#: 需要豁免」不得留在表內；刪除＋同步下修正是 `stale_grandfather_problems()` 訊息
#: **自己指名**的動作，不是放寬。
#: 🔴 R84 收斂（帳本 `DEF-200-052`）：上一段記載的跨檔耦合**已解**——本檔與
#: `tools/lib/ledger_rotation.py` 同屬帳本包持有面，於是「結案 → 刪豁免 → 下修天花板 →
#: 追加重釘史」四步可在同一次變更內走完。`DEF-101-206`（P4、零行動項）本輪結為 wontfix，
#: 本表 6 → 5、天花板 6 → 5、`UNPINNED_HANDOVER_CEILING_HISTORY` 追加 5（追加後未封印的
#: 尾巴＝1，未逾 `_SEAL_TAIL_MAX`，故封印本身不必動）。這是判準訊息自己指名的動作，不是放寬。
_UNPINNED_HANDOVER_GRANDFATHERED = frozenset({
    "DEF-101-235",
    "DEF-101-324",
})
#: shrink-only 棘輪上限（形狀比照 `tools/tests/` 的檔數棘輪）。只能往小改。
#: 🔴 歷次下修（34→28→…→5→4）的逐筆理由與被刪 ID 一律**不住這裡**：本檔受 LOC 相等棘輪
#: 管、餘裕近乎零，史料逐字保全於 `CrossPlatform_R89_Closure_Evidence.md` 的
#: 〈護欄層史料搬遷（帳本瘦身批）〉節。每一次下修都是判準訊息自己指名的動作，不是放寬。
_UNPINNED_HANDOVER_CEILING = 2

#: 🔴 本天花板的**方向鎖**（`DEF-101-993`）：`grandfather_ceiling_problems()` 判的是
#: 「清單筆數 ≤ 天花板」，對「把天花板往上搬」零判準。判準、重釘史與 WHY 皆住
#: `tools/lib/ledger_rotation.py`（單一實作、單一史料家）。


def unpinned_handover_problems(ledger_text: str) -> list[str]:
    """硬規則② 後半句的機械化：未結案列必須**二擇一**（純函式）。

    二擇一＝(a) 帶可解析的承接語境輪號（`_handover_rounds()`，其輪號另由
    `orphan_backlog_problems()` 判早晚），或 (b) 該列字面寫有「未指派」。
    兩者皆無 ⇒ 這一列的延後**沒有承接者也沒有承認沒有承接者**，正是散文式延後。

    存量豁免見 `_UNPINNED_HANDOVER_GRANDFATHERED`；豁免只對**當時已存在**的 ID 成立，
    新列一律硬擋。回傳問題清單（空＝全部合規）。
    """
    layout = _table_layout(ledger_text)
    if layout is None:
        return [_no_header_problem()]
    ncols, id_idx, status_idx = layout
    problems: list[str] = []
    for lineno, line in enumerate(ledger_text.splitlines(), 1):
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if len(cells) != ncols or not _ID_RE.fullmatch(cells[id_idx]):
            continue
        if _classify(cells[status_idx]) not in _UNRESOLVED_CLASSES:
            continue
        if _handover_rounds(line) or _UNASSIGNED_LITERAL in line:
            continue
        def_id = cells[id_idx]
        if def_id in _UNPINNED_HANDOVER_GRANDFATHERED:
            continue
        problems.append(
            f"帳本 :{lineno} {def_id}：狀態仍未結案，卻**既沒有可解析的承接輪號、"
            f"也沒有字面「{_UNASSIGNED_LITERAL}」** ⇒ 散文式延後（硬規則② 後半句，見 "
            f"CrossPlatform_Scan_Dimensions.md〈使用方式〉）。「排入下一輪」「擇機」"
            f"「留待下輪」都不算指派——它們既不能被機械比較輪號，也沒有承認無人承接。"
            f"兩條合法出口（擇一）：① 寫明承接輪次（體例：`承接輪次：**R{'{n}'}**`）；"
            f"② 誠實寫「承接輪次：**{_UNASSIGNED_LITERAL}**」並附**可直接執行**的解鎖條件。"
            f"⚠️ 不要把本列加進 _UNPINNED_HANDOVER_GRANDFATHERED——那張表是 R68 上線時的"
            f"存量快照、只准變小"
        )
    return problems


def stale_grandfather_problems(ledger_text: str) -> list[str]:
    """棘輪的另一半：白名單裡**已不需要豁免**的 ID 必須刪除（純函式）。

    🔴 沒有這一條，`_UNPINNED_HANDOVER_GRANDFATHERED` 就是一張只進不出的死名單：存量列被
    補標「未指派」或結案之後仍靜靜留在表裡，「還有幾筆存量沒清」就永遠不會下降、棘輪永遠
    不會轉。三選一即算「不再需要豁免」：已不在主檔（歸檔／刪除）／已結案／已滿足二擇一。
    """
    layout = _table_layout(ledger_text)
    if layout is None:
        return [_no_header_problem()]
    ncols, id_idx, status_idx = layout
    still_needed: set[str] = set()
    for line in ledger_text.splitlines():
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if len(cells) != ncols or not _ID_RE.fullmatch(cells[id_idx]):
            continue
        if _classify(cells[status_idx]) not in _UNRESOLVED_CLASSES:
            continue
        if _handover_rounds(line) or _UNASSIGNED_LITERAL in line:
            continue
        still_needed.add(cells[id_idx])
    stale = sorted(_UNPINNED_HANDOVER_GRANDFATHERED - still_needed)
    if not stale:
        return []
    return [
        f"存量豁免名單有 {len(stale)} 筆已不需要豁免（已結案／已補標／已不在主檔），"
        f"請從 {Path(__file__).name} 的 _UNPINNED_HANDOVER_GRANDFATHERED **刪除**它們，"
        f"並把 _UNPINNED_HANDOVER_CEILING 下修為 {len(still_needed)}：{stale}。"
        f"（棘輪只准往小走；不刪＝這張表變成只進不出的死名單，"
        f"「還剩幾筆存量」這個數字就永遠不會下降）"
    ]


def grandfather_ceiling_problems() -> list[str]:
    """棘輪本體：白名單筆數不得超過 `_UNPINNED_HANDOVER_CEILING`（純函式）。

    🔴 缺陷（R69 複審變異測試實證，`DEF-101-731`）：本天花板自 R68 上線起註解自稱
    「shrink-only 棘輪」，**但全檔零比較、零強制**——只被讀進成功訊息裡印出來。實測（本
    函式落地前）：插一列散文式延後的未結列、再把該 ID 加進白名單 ⇒ 成功訊息把「筆數已超過
    上限」這件事原樣印出來而仍 `rc=0`。於是白名單可隨每輪「順手加一筆」無聲膨脹，硬規則②
    後半句被逐列贖回——正是 `stale_grandfather_problems()` 只防住另外半邊的那個形態。

    分工（兩者缺一都不成棘輪）：
      * 本函式擋 **膨脹**（len > ceiling ⇒ 有人偷加豁免而沒有真的去修那一列）。
      * `stale_grandfather_problems()` 擋 **不縮**（豁免已不需要卻仍留在表裡）。

    刻意**不吃參數、不看帳本**：這是對原始碼常數本身的斷言，與餵哪一本帳本無關，因此必須
    在 `main()` 裡**無條件**執行（不受 `_DEFECT_LOG == _DEFAULT_DEFECT_LOG` 守衛約束）
    ——否則換一本帳本就能繞過棘輪，那又是一個假鎖。
    """
    actual = len(_UNPINNED_HANDOVER_GRANDFATHERED)
    if actual <= _UNPINNED_HANDOVER_CEILING:
        return []
    return [
        f"存量豁免名單已膨脹到 {actual} 筆，超過 shrink-only 棘輪上限 "
        f"{_UNPINNED_HANDOVER_CEILING}（超出 {actual - _UNPINNED_HANDOVER_CEILING} 筆）。"
        f"🔴 `_UNPINNED_HANDOVER_GRANDFATHERED` 是 R68 上線時的**存量快照**，只准變小："
        f"新的未結列請走硬規則② 後半句的兩條合法出口（寫明承接輪次／誠實寫"
        f"「{_UNASSIGNED_LITERAL}」＋可執行的解鎖條件），**不是**把它加進豁免名單。"
        f"若你確實刪了名單裡的存量而只是忘了同步下修天花板，請把 "
        f"{Path(__file__).name} 的 _UNPINNED_HANDOVER_CEILING 改成 {actual} 或更小。"
    ]


def ratchet_direction_problems() -> list[str]:
    """三條 shrink-only 棘輪的方向鎖（薄轉呼；判準與史料的家＝`lib/ledger_rotation.py`）。"""
    return _rotation.ratchet_direction_problems(_UNPINNED_HANDOVER_CEILING)


def lagging_clock_notes(ledger_text: str) -> list[str]:
    """`current_round()` 的 fail-open 窗口——把它印出來，而不是留在 docstring 裡。

    🔴 缺陷（R68 Scan-G）：`current_round()` 取自帳本自身「發現情境」欄，所以在新一輪
    **寫入第一列之前**，這個時鐘仍停在**上一輪**。於是「交棒給剛結束的那一輪」在整個
    新輪工作期都合法通過 `newest >= cur`。
    🔴 為何不引入第二個輪次時鐘：那會新造一個 stale 站點（成本高於收益，且第二個時鐘
    同樣要有人記得更新）。取而代之的最小處置是**讓失效方向對讀者可見**：凡未結列把承接
    者指向「恰等於推得值」的那一輪，逐列印出提醒——這正是窗口被利用時會出現的形狀。
    刻意回 note（warning）而非 problem：真交棒給當前輪是**合法**的，硬擋會製造假紅。
    """
    layout = _table_layout(ledger_text)
    if layout is None:
        return []
    ncols, id_idx, status_idx = layout
    cur = current_round(ledger_text)
    if cur is None:
        return []
    notes: list[str] = []
    for lineno, line in enumerate(ledger_text.splitlines(), 1):
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if len(cells) != ncols or not _ID_RE.fullmatch(cells[id_idx]):
            continue
        if _classify(cells[status_idx]) not in _UNRESOLVED_CLASSES:
            continue
        rounds = [n for _, n, _ in _handover_rounds(line)]
        if rounds and max(rounds) == cur and not _reassign_hit(cells[status_idx]):
            notes.append(
                f"帳本 :{lineno} {cells[id_idx]}：承接輪次 R{cur} **恰等於**由「"
                f"{_CONTEXT_HEADER}」欄推得的當前輪 —— 若本輪尚未寫入任何帳本列，"
                f"這個推得值仍停在上一輪，本列實為「交棒給剛結束的那一輪」而硬規則② "
                f"抓不到（fail-open 窗口，於本輪第一列落地時自動關閉）。請確認該輪真的"
                f"還沒結束，或就地追加「回執」／「改派」"
            )
    return notes


# ------------------------ 已結列殘留待辦 ＋ 狀態訂正 token（R68，DEF-101-709／710）
# 🔴 (一) 已結列的殘留待辦：`_UNRESOLVED_CLASSES` 明確排除 `fixed`，所以一列只要首詞是
# `fixed`，它**狀態／分流欄**裡寫的「承接輪次：未指派」「留待下一輪」就**在結構上永遠進
# 不了承接稽核**。`archive_defect_log.py --plan` 的 needs_ack 區塊只列其中一部分、且**只在
# 有人要歸檔時才被看到**；本函式把它接進每次都跑的閘門輸出（warning 不 fail）。
# 🔴 鑑別力訂正見 CrossPlatform_R85_Ledger_Closure.md §17（零資訊字移除、掃描面收窄；34→13）
_RESIDUAL_TODO_RE = re.compile(r"未指派|擇機|留待|下一輪|下輪|尚未|待辦|backlog")
# 🔴 (二) 狀態訂正 token：`_classify()` 取**最早出現**的關鍵字，於是
# `open watch（R55）→ **closed-by-verification@R56**` 這種「先寫舊狀態、箭頭後寫訂正」
# 的寫法會被判成 `open`——一筆已結列被長期計入未結存量（DEF-101-433 實例）。而
# `closed-by-verification` 又**不在**合法首詞集合內，卻因為首詞是 `open` 而躲過首詞鎖。
# 本檔對這一類立兩道：
#   · 硬擋「合法首詞的**連字號／底線變體**」（`closed-by-verification`／`partially-fixed`）
#     ——這種帶連字號的 token 在本帳本方言裡必然是狀態宣稱，不會是普通英文字。
#     刻意**不**把裸 `closed`／`open` 納入：它們在散文裡是普通英文詞（實測 `DEF-19-001`
#     的 `closed@improving_40` 屬另一套里程碑編號），硬擋會製造假紅。
#   · warning 提示「首詞判未結、但狀態欄後段有 `→ 已結token@Rnn` 訂正」的列
#     （實測 `DEF-101-432` 正是這個形狀，其 `fixed` 是合法詞故不會被上面那道硬擋抓到）。
_STATUS_VARIANT_RE = re.compile(
    r"(?<![A-Za-z0-9])((?:closed|fixed|routed|partial|partially|wontfix)"
    r"(?:[-_][A-Za-z]+)+)(?![A-Za-z0-9-])"
)
#: markdown 行內 code span。反引號內是**逐字引述**（例如 `DEF-101-541` 逐字引用它自己
#: 被訂正掉的舊寫法 `partially-fixed`），不算新的狀態宣稱。與
#: `archive_defect_log._CODE_SPAN_RE` 是**同一個物件**——同一個判準只有一份實作；R74 起
#: 本體住 `tools/lib/defect_ledger_index.CODE_SPAN_RE`（`reassign_hit()` 也消費它）。
_CODE_SPAN_RE = _ledger_index.CODE_SPAN_RE
_SUPERSEDE_RE = re.compile(
    r"[→⇒]\s*[*＊`\s]{0,4}(fixed|closed-by-decision|no_action_needed|wontfix)"
    r"(?![A-Za-z0-9-])"
)


def residual_todo_notes(ledger_text: str) -> list[str]:
    """已結案卻仍載有實質待辦字樣的列（純函式；回 warning 用的說明字串）。"""
    layout = _table_layout(ledger_text)
    if layout is None:
        return []
    ncols, id_idx, status_idx = layout
    route = next((i for i, h in enumerate(_header_cells(ledger_text) or [])
                  if h == "分流去向"), status_idx)
    notes: list[str] = []
    for lineno, line in enumerate(ledger_text.splitlines(), 1):
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if len(cells) != ncols or not _ID_RE.fullmatch(cells[id_idx]):
            continue
        cls = _classify(cells[status_idx])
        if cls in _UNRESOLVED_CLASSES:
            continue
        markers = sorted(set(_RESIDUAL_TODO_RE.findall(
            _CODE_SPAN_RE.sub("", f"{cells[status_idx]} {cells[route]}"))))
        if markers:
            notes.append(f":{lineno} {cells[id_idx]}({cls})={'/'.join(markers)}")
    return notes


def status_variant_problems(ledger_text: str) -> list[str]:
    """狀態欄不得出現合法首詞的**連字號／底線變體**（純函式；硬擋）。

    命中即 rc=1：`closed-by-verification`／`partially-fixed` 這類 token 在本帳本方言裡
    必然是狀態宣稱，而它們**不在**合法首詞集合內，卻因為不在首位而躲過
    `status_first_word_problems()`（那道鎖只看首詞）。反引號內的逐字引述不算。
    """
    layout = _table_layout(ledger_text)
    if layout is None:
        return [_no_header_problem()]
    ncols, id_idx, status_idx = layout
    problems: list[str] = []
    for lineno, line in enumerate(ledger_text.splitlines(), 1):
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if len(cells) != ncols or not _ID_RE.fullmatch(cells[id_idx]):
            continue
        bare = _CODE_SPAN_RE.sub("", cells[status_idx])
        for tok in dict.fromkeys(_STATUS_VARIANT_RE.findall(bare)):
            if tok in _STATUS_FIRST_WORDS:
                continue
            problems.append(
                f"帳本 :{lineno} {cells[id_idx]}：狀態欄出現非法狀態 token {tok!r}"
                f"（合法首詞的連字號／底線變體）。合法值＝{sorted(_STATUS_FIRST_WORDS)}"
                f"（權威＝主檔《格式定義》）。這一類不在首位、躲得過首詞鎖，卻會讓讀者"
                f"與 `_classify()` 對本列狀態各說各話（DEF-101-433 判例：一筆已結列因此"
                f"被長期計入未結存量）。請改寫為合法 token；若只是逐字引述舊寫法，"
                f"請用反引號包住"
            )
    return problems


def supersession_notes(ledger_text: str) -> list[str]:
    """首詞判未結、但狀態欄後段有「→ 已結 token」訂正的列（純函式；warning）。

    `_classify()` 取最早出現的關鍵字，這類列於是被記成未結。刻意不硬擋：訂正段落是
    帳本體例（歷史原文逐字保全＋箭頭追記），要改的是**首詞**而不是禁止追記；由本提示
    點名，讓「該把首詞更新了」這件事每輪都被看見。
    """
    layout = _table_layout(ledger_text)
    if layout is None:
        return []
    ncols, id_idx, status_idx = layout
    notes: list[str] = []
    for lineno, line in enumerate(ledger_text.splitlines(), 1):
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        if len(cells) != ncols or not _ID_RE.fullmatch(cells[id_idx]):
            continue
        if _classify(cells[status_idx]) not in _UNRESOLVED_CLASSES:
            continue
        bare = _CODE_SPAN_RE.sub("", cells[status_idx])
        hits = dict.fromkeys(_SUPERSEDE_RE.findall(bare))
        if hits:
            notes.append(
                f"帳本 :{lineno} {cells[id_idx]}：首詞判為未結，狀態欄後段卻有"
                f"「→ {'／'.join(hits)}」訂正 —— `_classify()` 取最早關鍵字，本列因此被"
                f"計入未結存量。若訂正才是現況，請把**首詞**改為該已結 token"
                f"（體例見 DEF-101-433：原文以反引號逐字保留於後）"
            )
    return notes


# ------------------------------ 修復包自報 status ↔ 帳本狀態欄機械對帳（DEF-101-689）
def reconcile_problems(reported: dict[str, str], ledger: dict[str, str | None],
                       archive: dict[str, str | None] | None = None) -> list[str]:
    """把「修復包交件時自報的 status」與帳本家族實況做集合差（純函式）。

    🔴 為何需要（DEF-101-689，R67 提出、R68 落地）：每輪由 N 個並行修復包交件，各自在
    回報裡自陳「這筆我修了／跳過」，主控再據此入帳。**兩邊從來沒有任何機械物對過帳**——
    自報 fixed 而帳本仍 open、或帳本入了帳而沒有任何包自報，兩種漂移都只能靠人眼比對。
    該建議本身還被寫在一列狀態已 `fixed` 的散文裡，於是連承接稽核都進不去。

    `reported` ＝ `{DEF-ID: 自報狀態字串}`；自報字串一律走 `_classify()` 正規化，所以
    `fixed@R68`／`open（待下輪）` 這類真實寫法都能比。查找面＝主檔優先、archive 次之
    （與 `_scan_target()` 同一套規則，避免「歸檔即假紅」——見 `_load_archive_status()`）。

    回傳問題清單（空＝逐筆一致）。刻意**不**檢查「帳本有而報表沒有」：一輪只修一部分
    缺陷是常態，那個方向的差集是雜訊而非訊號。
    """
    problems: list[str] = []
    for def_id in sorted(reported):
        claimed_raw = reported[def_id]
        claimed = _classify(str(claimed_raw))
        if claimed is None:
            problems.append(
                f"{def_id}：自報狀態 {claimed_raw!r} 辨識不出任何已知狀態關鍵字 —— "
                f"請用《格式定義》的合法首詞（{sorted(_STATUS_FIRST_WORDS)}）書寫"
            )
            continue
        if def_id in ledger:
            actual, where = ledger[def_id], "缺陷帳本主檔"
        elif archive is not None and def_id in archive:
            actual, where = archive[def_id], "帳本 archive"
        else:
            problems.append(
                f"{def_id}：修復包自報「{claimed}」，但帳本家族（主檔 ∪ archive）"
                f"查無此 ID —— 修了卻沒入帳，或 ID 打錯"
            )
            continue
        if actual is None:
            problems.append(
                f"{def_id}：修復包自報「{claimed}」，但{where}該列狀態欄辨識不出"
                f"已知關鍵字（帳本自身狀態含糊）"
            )
        elif actual != claimed:
            problems.append(
                f"{def_id}：修復包自報「{claimed}」，{where}實際為「{actual}」 —— "
                f"自報與入帳不一致，請確認是漏入帳還是自報過樂觀"
            )
    return problems


def _run_reconcile(report_path: Path) -> int:
    """`--reconcile <報表.json>` 的入口：JSON ＝ `{DEF-ID: 自報狀態}`。"""
    import json
    if not report_path.exists():
        print(f"❌ 找不到修復包自報報表：{report_path}", file=sys.stderr)
        return 1
    try:
        data = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(f"❌ 報表不是合法 JSON：{report_path}（{exc}）", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        print("❌ 報表格式須為 {\"DEF-101-001\": \"fixed@R68\", …} 的物件"
              "（值一律字串）", file=sys.stderr)
        return 1
    problems = reconcile_problems(data, _load_ledger_status(), _load_archive_status())
    if problems:
        print(f"❌ 修復包自報 status ↔ 帳本狀態不一致（{len(problems)} 筆）：",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"✅ 修復包自報 status 與帳本家族逐筆一致：{len(data)} 筆")
    return 0


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


_ARCHIVE_GLOB = "AutoSDD_Defect_Log_archive_*.md"


def archive_files() -> list[Path]:
    """磁碟上的 archive 檔（排序穩定）。帳本家族的 archive 半邊，SSOT 勿在別處重列 glob。"""
    return sorted(_DEFECT_LOG.parent.glob(_ARCHIVE_GLOB))


def _load_archive_status() -> dict[str, str | None]:
    """解析**全部 archive 檔**的表格列，回傳 {DEF-ID: 狀態分類}（DEF-101-676，R68）。

    🔴 為何需要這一支 —— 帳本 SSOT 的正確定義是「主檔 ∪ archive 家族」，不是「主檔」：
    `_load_ledger_status()` 只讀主檔，於是任何被掃描目標做過狀態宣稱的列**一旦歸檔就
    立刻讓 `_scan_target()` 報「帳本查無此 ID」**。歷輪為了迴避這個假紅，在
    `archive_defect_log.py` 立了搬遷判準③「被 crossref 掃描目標做過狀態宣稱 ⇒ 硬擋」，
    等於用「不准搬」去繞過「搬了會假紅」。後果是帳本的不可搬核心單調成長（R68 動工前
    實測：109 列中 11 列**只**被判準③ 擋著、合計 16217 bytes 永久卡在主檔），主檔逼近
    256KB 硬線後整輪無法收輪（DEF-101-676 死結）。

    正解是把解析面補齊到家族全體，而**不是**放寬一致性要求：歸檔列的狀態宣稱照樣要
    與該列在 archive 內的實際狀態逐筆比對，只是查找範圍從「主檔」擴為「主檔 ∪ archive」。
    真正不存在的 ID（打錯字、從未立帳）仍然報「帳本家族查無此 ID」——鑑別力不減。

    🔴 每份 archive 各自用**自己的表頭**定位狀態欄（`_table_layout(該檔全文)`），不沿用
    主檔 layout：archive 是零刪除史料檔，歷輪表頭欄數不保證與今日主檔相同，沿用主檔
    layout 會讓狀態欄整批位移到別欄（這正是 Pkg-P6 在主檔踩過的同一種錯，不在此重演）。
    抽不到表頭的 archive 一律跳過（不猜位置），其列視為未收錄 ⇒ 退回「查無此 ID」硬報。
    """
    status: dict[str, str | None] = {}
    for arch in archive_files():
        text = arch.read_text(encoding="utf-8-sig")
        layout = _table_layout(text)
        if layout is None:
            continue
        ncols, id_idx, status_idx = layout
        for line in text.splitlines():
            if not _ROW_RE.match(line):
                continue
            cells = _row_cells(line)
            if id_idx >= len(cells) or not _ID_RE.fullmatch(cells[id_idx]):
                continue
            status[cells[id_idx]] = (
                _classify(cells[status_idx]) if len(cells) == ncols else None
            )
    return status


def _scan_target(path: Path, ledger: dict[str, str | None],
                 archive: dict[str, str | None] | None = None) -> list[str]:
    """比對一份掃描目標內的狀態宣稱與帳本實況。

    `archive` 給定時作為**次級**查找面（主檔優先）：主檔查不到才回退 archive，讓已歸檔
    的列仍可被宣稱且仍被逐筆驗證（見 `_load_archive_status()` 的 WHY）。預設 `None`
    ＝不啟用回退，保留「只看主檔」的原語意供既有測試與單檔情境使用。
    """
    problems: list[str] = []
    text = path.read_text(encoding="utf-8-sig")
    for m in _CLAIM_RE.finditer(text):
        ids_blob, claim_text = m.group(1), m.group(2)
        claimed = _classify(claim_text)
        if not claimed:
            continue
        for def_id in _ID_RE.findall(ids_blob):
            # 主檔優先；主檔查無才看 archive（同 ID 兩邊都有時以主檔為準，兩邊矛盾
            # 另由 `archive_defect_log.py --check` 判準(3)「跨檔矛盾」硬擋）。
            if def_id in ledger:
                actual = ledger[def_id]
                where = "缺陷帳本"
            elif archive is not None and def_id in archive:
                actual = archive[def_id]
                where = "帳本 archive"
            else:
                scope = "帳本家族（主檔 ∪ archive）" if archive is not None else "缺陷帳本"
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，但{scope}查無此 ID"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
                continue
            if actual is None:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，但{where}裡該 ID 最後"
                    f"一列的狀態欄文字無法辨識任何已知關鍵字，帳本自身狀態含糊"
                    f"（claim 片段：{claim_text[:60]!r}）"
                )
            elif actual != claimed:
                problems.append(
                    f"{path.name}：{def_id} 宣稱狀態「{claimed}」，{where}實際狀態為"
                    f"「{actual}」（claim 片段：{claim_text[:60]!r}）"
                )
    return problems


# 帳本輪替界線（DEF-99-001 政策：主檔 < 256KB Read 上限；DEF-101-123 機械化——
# R9 發現主檔已默默長到 272KB 超線，政策沒有任何機械守門）。
# 逼近（>= _LEDGER_WARN_BYTES）印 warning；超線（>= _LEDGER_FAIL_BYTES）直接 fail，
# 強制執行既定輪替程序（已結列搬遷 archive_NN）。
#
# 🔴 R68（DEF-101-676 方向③ 評估結論：**駁回調高硬線**）——這條線不是政策自由度，是
# **當下實測的工具事實**。2026-08-01 於 macOS 26.5.2 真機對 Read 工具實跑探針：
#     2097152 bytes 檔 → `File content (2MB) exceeds maximum allowed size (256KB).`
#      307200 bytes 檔 → `File content (300KB) exceeds maximum allowed size (256KB).`
# 兩發皆在「還沒讀到內容」就被工具本身拒絕，且錯誤訊息逐字載明上限 256KB。故 R67 帳本
# 內「現值 262144 綁的是 Read 工具單次讀取上限」之認知**於 R68 仍成立、未過期**，調高
# `_LEDGER_FAIL_BYTES` 等同砸溫度計：閘門會轉綠，而主檔會變成任何 agent 都讀不完整的
# 檔——「讀不完整的 SSOT」比「撞閘門」壞得多（讀者只讀到前半段還以為讀完了，是靜默
# 失效）。容量問題的正解是提高輪替**吞吐**（見 `archive_defect_log.py` 判準②③ 的 R68
# 修訂），不是提高上限。
# 對應機械鎖：`tools/tests/test_archive_defect_log.py::TestHardLineIsToolFact`（R75 訂正）
_LEDGER_WARN_BYTES = 240 * 1024
_LEDGER_FAIL_BYTES = 256 * 1024
#: Read 工具實測單次讀取上限（見上方探針取證）。硬線必須恰等於它——不得「留一點餘裕」
#: 地調低（那會讓政策與工具事實脫鉤、下一輪讀者無從判斷哪個數字才是真的），更不得調高。
_READ_TOOL_MAX_BYTES = 256 * 1024

# 🔴 R80：具名治理文件清單（WHY 全文、成員、命名慣例三者）已下沉 `tools/lib/governance_docs.py`。
# 搬家理由不是整齊，是兩道硬閘互為對方的違規：這張清單**單調增長**（每輪新生的證據檔都要加
# 一筆），而本檔受 SPECIAL_FILES raw-line 棘輪管且餘裕近零 ⇒ `unregistered_governance_docs()`
# 教人「請在 `_GOVERNANCE_DOCS` 補上一筆」，照做即撞棘輪（R80 實測 headroom 3 < 5 而紅）。
# 「抽共用模組」是該棘輪自己指定的第一順位處置，先例 `tools/lib/defect_ledger_index.py`。
# 下方三個名字是**再匯出**（同一個物件，`assertIs` 鎖住），消費端與 monkeypatch 面零改動。
_GOVERNANCE_DOCS = _gov_docs._GOVERNANCE_DOCS
_GOVERNANCE_DOC_GLOB = _gov_docs._GOVERNANCE_DOC_GLOB
_GOVERNANCE_DOC_DIR = _gov_docs._GOVERNANCE_DOC_DIR


def unregistered_governance_docs() -> list[str]:
    """磁碟上符合姊妹檔命名慣例、卻未登記進 `_GOVERNANCE_DOCS` 的檔（空＝全部已登記）。

    🔴 為何需要（SA-R60R3-01 的根因級那一半）：把兩張清單併成一張，消掉的是「同一份檔
    只進了其中一張」；**沒有**消掉「新建一份檔、兩張都沒進」。r3 的真實路徑正是後者——
    有人在本輪把證據檔拆成姊妹檔，體積清單記得加、指針清單忘了加，而**沒有任何機械訊號**。
    合併之後這條路徑只剩一種形狀（整份檔沒登記），本函式就守這一種。

    誠實劃界：判定面＝檔名前綴慣例，**不是**語意判斷。有人把治理文件取名成別的前綴
    （或放到別的目錄）一樣抓不到——那需要理解「這份檔承擔什麼義務」，本鎖不假裝有。
    它擋的是「照慣例命名、卻漏登記」這條**已實際發生過**的復發路徑。
    """
    registered = {p.resolve() for p in _GOVERNANCE_DOCS}
    missing = sorted(
        p.name for p in _GOVERNANCE_DOC_DIR.glob(_GOVERNANCE_DOC_GLOB)
        if p.resolve() not in registered
    )
    if not missing:
        return []
    return [
        f"{name}：符合具名治理文件的命名慣例（{_GOVERNANCE_DOC_GLOB}）卻未登記進 "
        f"{Path(__file__).name} 的 _GOVERNANCE_DOCS —— 未登記＝該檔同時逸出**體積守門**"
        f"與 archive_defect_log 的**指針稽核**（SA-R60R3-01 的原始路徑：本輪新生的姊妹"
        f"證據檔只進了其中一張清單）。請在該常數補上一筆，並在該檔內寫明它為何屬於這一類；"
        f"若它確實不該受治理文件義務管，請改名成不符合該慣例的檔名，讓「不管」也是"
        f"一個看得見的決定"
        for name in missing
    ]


# 散文式結案宣稱（R69 `DEF-101-735`）——判準與純函式住在 `tools/lib`（兩支工具共用、
# 且本檔受 SPECIAL_FILES 行數棘輪管），此處再匯出同一個物件，不另寫一份。
closure_claim_problems = _ledger_index.closure_claim_problems
_CLOSURE_CLAIM_WINDOW = _ledger_index.CLOSURE_CLAIM_WINDOW


def oversize_problems(paths: list[Path]) -> tuple[list[str], list[str]]:
    """帳本家族／具名治理文件的體積守門（純函式本體住 `tools/lib`，門檻由本檔注入）。

    門檻與帳本共用 `_LEDGER_*_BYTES`——**因為上限的來源是同一個**：262,144 是 Read 工具
    單次讀取上限（不是 git、不是 markdown 的限制），對帳本與對證據檔是同一條物理界線。
    """
    return _ledger_index.oversize_problems(
        paths, _LEDGER_WARN_BYTES, _LEDGER_FAIL_BYTES)


_USAGE = (
    "用法：\n"
    "  python3 tools/check_defect_log_crossref.py                 # 全套閘門\n"
    "  python3 tools/check_defect_log_crossref.py --reconcile F.json  # 修復包自報對帳\n"
    "  python3 tools/check_defect_log_crossref.py --unresolved-count  # 未結存量唯一量測入口"
)

#: `main()` 的檢查序（**執行順序即本序**，逐名對應下方每一個早退點）。
#: 🔴 存在理由＝**早退遮蔽**：`main()` 任一道紅就 `return 1`，其後整批檢查一行都不會跑，
#: 而輸出看起來只是「少了幾行」——消失的方向是「看起來變乾淨」，正是本 repo 最怕的假訊號
#: 方向。實測：帳本目錄新增一份未登記的治理文件時，本工具只印 2 行、原本 8 筆孤兒 warning
#: 全數靜默消失，讀者無從得知後面十來道根本沒跑。`_bail()` 依本序把「尚有幾道未執行」逐名
#: 印出來，使早退**可見**而非隱形。新增／調動檢查時必須同步本序（兩邊由
#: `tools/tests/test_check_defect_log_crossref.py::TestEarlyExitAnnouncesUnrunChecks` 綁定）。
#: 🔴 R79：體積改為最後一道收斂、逐列位元組上限共用此名目（WHY 見 lib.ROW_MAX_BYTES）。
_CHECK_ORDER: tuple[str, ...] = (
    "缺陷帳本存在", "帳本歸檔體積",
    "具名治理文件涵蓋面與磁碟脫節", "具名治理文件體積",
    "帳本表格欄位切分結構不合", "帳本解析結果非空", "合法首詞缺分類器對應",
    "帳本狀態欄首詞不合法", "孤兒承接輪次（硬規則②）",
    "未結列缺承接指派（硬規則② 後半句）", "存量豁免棘輪被撐大", "狀態欄非法狀態 token",
    "掃描目標齊備", "缺陷帳本跨文件狀態不一致", "帳本體積與逐列位元組上限",
)


def _bail(header: str, problems: list[str] | None = None, detail: str = "") -> int:
    """印出一道檢查的紅，並**明說後面還有哪幾道沒跑**，恆回 1。

    `problems` 給定時以「`❌ <header>（N 筆）：` ＋ 逐條 `  - `」形態印；`detail` 供
    不成清單的單句紅（體積、缺檔）使用。兩者可並用，也可只給其一。
    """
    if header not in _CHECK_ORDER:  # fail-loud：序漏了一項會讓殘餘清單說謊
        print(f"🔴 內部錯誤：{header!r} 不在 _CHECK_ORDER 內，殘餘檢查清單不可信",
              file=sys.stderr)
    if problems is not None:
        print(f"❌ {header}（{len(problems)} 筆）：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
    if detail:
        print(f"❌ {detail}", file=sys.stderr)
    idx = _CHECK_ORDER.index(header) if header in _CHECK_ORDER else -1
    rest = _CHECK_ORDER[idx + 1:] if idx >= 0 else ()
    if rest:
        print(f"🔴 早退：本次尚有 {len(rest)} 道檢查**未執行**（{'／'.join(rest)}）"
              "——修好上列後請重跑，勿把「輸出只剩這幾行」讀成「其餘都乾淨」",
              file=sys.stderr)
    return 1


def cli(argv: list[str]) -> int:
    """參數分派。刻意**不**寫進 `main()`：既有大批測試直接呼叫 `main()`，若在那裡讀
    `sys.argv`，unittest 自己的參數會被當成本工具的旗標（落地時實測 16 支測試因此
    rc=2 假紅）。也刻意不引 argparse——只有一個旗標，一個 if 就夠。
    """
    if len(argv) == 2 and argv[0] == "--reconcile":
        return _run_reconcile(Path(argv[1]))
    if argv == ["--unresolved-count"]:  # 未結存量的唯一量測入口（R74 PKG-2）
        return _ledger_index.report_unresolved(_load_ledger_status())
    if argv:
        print(f"❌ 無法辨識的參數：{argv}\n{_USAGE}", file=sys.stderr)
        return 2
    return main()


def main() -> int:
    if not _DEFECT_LOG.exists():
        return _bail("缺陷帳本存在", detail=f"找不到缺陷帳本：{_DEFECT_LOG}")
    ledger_bytes = _DEFECT_LOG.stat().st_size
    deferred: list[str] = []  # 末尾一起收斂（見 `_CHECK_ORDER` 上方 R79 段）
    if ledger_bytes >= _LEDGER_FAIL_BYTES:
        deferred.append(f"缺陷帳本主檔 {ledger_bytes} bytes ≥ 輪替上限 {_LEDGER_FAIL_BYTES}"
                        "（DEF-99-001 <256KB）——搬已結列至下個 archive_NN（R9 輪替程序）")
    if ledger_bytes >= _LEDGER_WARN_BYTES:
        print(f"⚠️  缺陷帳本主檔 {ledger_bytes} bytes 已逼近輪替上限 "
              f"{_LEDGER_FAIL_BYTES}（DEF-99-001 政策），請規劃已結列搬遷 archive",
              file=sys.stderr)
    # DEF-99-001 政策同時要求「每一個 archive 檔」< 256KB（單一 archive 逼近即拆下
    # 一個 archive）——Architect 二審 OBS-3：守門不可只量主檔。
    for arch in sorted(_DEFECT_LOG.parent.glob("AutoSDD_Defect_Log_archive_*.md")):
        arch_bytes = arch.stat().st_size
        if arch_bytes >= _LEDGER_FAIL_BYTES:
            return _bail("帳本歸檔體積", detail=(
                f"帳本歸檔 {arch.name} {arch_bytes} bytes ≥ 上限 {_LEDGER_FAIL_BYTES}"
                "（DEF-99-001 政策）——請拆分至下一個 archive_NN"))
        if arch_bytes >= _LEDGER_WARN_BYTES:
            print(f"⚠️  帳本歸檔 {arch.name} {arch_bytes} bytes 已逼近上限 "
                  f"{_LEDGER_FAIL_BYTES}（DEF-99-001 政策），請規劃拆分", file=sys.stderr)
    # 具名治理文件涵蓋面的登記完整性（SA-R60R3-01）——擺在體積檢查**之前**：一份未登記
    # 的檔在體積面與指針面同時是零檢查，先講「涵蓋面對不對」再講「涵蓋面內的檔多大」。
    unregistered = unregistered_governance_docs()
    if unregistered:
        return _bail("具名治理文件涵蓋面與磁碟脫節", unregistered)
    # 具名治理文件的體積（DEF-101-587）——與帳本同一條物理界線，見 `oversize_problems()`。
    gov_fails, gov_warns = oversize_problems(list(_GOVERNANCE_DOCS))
    for w in gov_warns:
        print(f"⚠️  治理文件 {w}", file=sys.stderr)
    if gov_fails:
        return _bail("具名治理文件體積", [f"治理文件 {f}" for f in gov_fails])
    ledger_text = _DEFECT_LOG.read_text(encoding="utf-8-sig")

    # 欄位切分結構硬閘（Pkg-P6）——擺在**所有**解析之前：表頭定位或欄數一旦不對，
    # 「狀態欄」讀到的可能根本是別欄，下游兩道檢查的結論就都建立在錯欄位上
    # （修復前實測：狀態欄空白 + 分流去向以 `open` 開頭 ⇒ 兩道檢查同時零訊號）。
    arity_problems = row_arity_problems(ledger_text)
    if arity_problems:
        return _bail("帳本表格欄位切分結構不合", arity_problems)

    ledger = _load_ledger_status()
    if not ledger:
        return _bail("帳本解析結果非空", detail=(
            "缺陷帳本解析結果為空 — 表格格式可能已改版導致比對邏輯失效，"
            "請同步本腳本的 _ROW_RE / 欄位解析"))

    # 狀態欄首詞合法值硬斷言（SA-R60R2-06）——擺在跨文件比對**之前**：帳本自身的狀態欄
    # 若寫得不合法，跨文件一致性的結論就建立在含糊的基礎上（round 1 已證 `partially-fixed`
    # 會靜默命中 `fixed`，而本檔對非法首詞原本一句話都不說）。
    # 合法首詞 → 分類器的硬綁定（SA-R60R3-07）——擺在逐列首詞檢查**之前**：若有一個合法
    # 首詞根本沒有分類器，逐列檢查會全部放行、而那些列在下游靜默落進 warning-only 的
    # 「狀態含糊」桶。先確定詞彙表本身自洽，再談每一列合不合詞彙表。
    orphan_problems = unclassifiable_first_word_problems()
    if orphan_problems:
        return _bail("合法首詞缺分類器對應", orphan_problems)

    first_word_problems = status_first_word_problems(ledger_text)
    if first_word_problems:
        return _bail("帳本狀態欄首詞不合法", first_word_problems)

    # 孤兒承接輪次硬閘（硬規則②，R67 落地）——擺在跨文件比對**之前**、首詞檢查**之後**：
    # 首詞合法是本檢查的前提（要先能可靠判斷「這列結案了沒」），而本檢查與跨文件一致性
    # 相互獨立。為何非硬閘不可：規則自 R59 訂立後八輪純靠紀律，實測注入「open 且交棒給
    # 一個早已結束的輪次」的合成列，本閘門照樣 rc=0 全綠、還把它算成一筆有效狀態紀錄
    # （Scan-H 必跑項 #5：稽核工具必須有閘門看它的 rc）。
    orphan_problems = orphan_backlog_problems(ledger_text)
    if orphan_problems:
        return _bail("孤兒承接輪次（硬規則②）", orphan_problems)

    # 硬規則② 後半句（二擇一，R68）——緊接在輪號比大小之後：兩者是**同一條規則的兩半**，
    # 前半判「指向的輪次夠不夠新」，後半判「到底有沒有指向任何東西」。少了後半，
    # 未結列只要不寫任何 `R\d+` 就從 `if not handovers: continue` 短路出去（實測 61 筆）。
    # 🔴 本道（含其 stale 自檢）只對**真實主檔**成立：它與 `_UNPINNED_HANDOVER_
    # GRANDFATHERED` 是一體的，而該名單列的是相對於 `docs/06_quality/
    # AutoSDD_Defect_Log.md` 的存量 ID。餵任何其他帳本（測試以 mock 換掉
    # `_DEFECT_LOG` 的合成 fixture）時，名單對該帳本全不匹配 ⇒ 兩個方向同時假紅：
    # fixture 的未結列一律被判「缺承接指派」、名單每一筆一律被判「已 stale」——
    # 兩者都與規則想抓的東西無關。綁定預設路徑而非「有沒有被 mock」，是因為生產
    # 路徑上 `_DEFECT_LOG` 恆為預設值 ⇒ 真 repo 一定跑得到這道，鑑別力不減。
    # 規則本體的鑑別力由 `TestUnpinnedHandoverAndStaleGrandfather` 以純函式直接驗
    # （雙向注入），不經 `main()`——正因為經 `main()` 就得餵合成帳本。
    # 🔴 R74 併入本區塊的第三道＝**未結存量列數棘輪**：門檻按真實主檔平均列大小推得（見
    # `_ledger_index.UNRESOLVED_ROWS_*`），故與上兩道同受預設路徑守衛約束（合成 fixture 的
    # 列數與那組算式無關，硬判會是與規則無關的假紅／假綠）。
    unres_warns: list[str] = []
    unpinned_problems: list[str] = []
    if _DEFECT_LOG == _DEFAULT_DEFECT_LOG:
        unpinned_problems = unpinned_handover_problems(ledger_text)
        unpinned_problems += stale_grandfather_problems(ledger_text)
        unres_fails, unres_warns = _ledger_index.unresolved_ceiling_problems(ledger)
        unpinned_problems += unres_fails
        # 逐列位元組上限同受本守衛（豁免清單綁真實主檔的 ID）；鑑別力見 TestR79RowByteCeiling。
        deferred += _ledger_index.oversize_row_problems(ledger_text)
        # DEF-200-163：帳本相對 git HEAD 若有未 commit 修改，本場結論可能已過期（advisory）。
        for note in _staleness.uncommitted_problems(_DEFECT_LOG, _REPO_ROOT):
            print(f"⚠️  {note}", file=sys.stderr)
    if unpinned_problems:
        return _bail("未結列缺承接指派（硬規則② 後半句）", unpinned_problems)

    # 棘輪本體（R69 假鎖修正，`DEF-101-731`）——**無條件**跑：這是對原始碼常數的斷言，
    # 與餵哪一本帳本
    # 無關，放進上方 `_DEFECT_LOG == _DEFAULT_DEFECT_LOG` 守衛內就等於「換一本帳本即可
    # 繞過棘輪」。R68 只寫了註解與常數、零比較，白名單因此可無聲膨脹（見函式 docstring
    # 的實測復現）。
    ceiling_problems = grandfather_ceiling_problems()
    # 🔴 同一個名目下的另一半（R82，`DEF-101-993`）：上面那道判「清單有沒有超過天花板」，
    # 這一道判「天花板自己有沒有被往上搬」。少了它，三條棘輪都只是收費站——把常數調高到
    # 新實測值即可全綠（實測，見 ratchet_direction_problems docstring）。同樣**無條件**跑。
    ceiling_problems += ratchet_direction_problems()
    if ceiling_problems:
        return _bail("存量豁免棘輪被撐大", ceiling_problems)

    # 狀態 token 變體硬閘（R68）——放在首詞鎖之後：首詞鎖只看第一個詞，
    # `open watch（R55）→ closed-by-verification@R56` 這種訂正 token 躲在後面。
    variant_problems = status_variant_problems(ledger_text)
    if variant_problems:
        return _bail("狀態欄非法狀態 token", variant_problems)

    # 以下三組是 warning（不 fail）——它們指的都是**帳本品質提示**而非跨文件矛盾，
    # 硬擋會製造假紅。但必須每次都印：它們原本全部只活在 docstring 或 `--plan` 裡，
    # 而「只在有人主動去看時才被看到」的清單等於沒有（DEF-101-709 立案理由）。
    for w in unres_warns:
        print(f"⚠️  未結存量逼近列數上限：{w}", file=sys.stderr)
    for note in lagging_clock_notes(ledger_text):
        print(f"⚠️  當前輪時鐘 fail-open 窗口：{note}", file=sys.stderr)
    for note in supersession_notes(ledger_text):
        print(f"⚠️  狀態首詞待更新：{note}", file=sys.stderr)
    residual = residual_todo_notes(ledger_text)
    if residual:
        # 刻意壓成**一行**：18 筆各印一段會把閘門輸出淹掉，而被淹掉的 warning 等於沒印。
        print(f"⚠️  已結列殘留待辦 {len(residual)} 筆（已結分類使它們結構上進不了承接"
              f"稽核；真待辦請拆出獨立 DEF 列承接，敘事引述可忽略）："
              f"{'、'.join(residual)}", file=sys.stderr)

    # 「有效」與「含糊」分開呈現（R9 跨平台複審：舊版把 _classify 回 None 的列
    # 也一併計入「有效狀態紀錄」總數，帳本自身品質問題被靜默吞掉）。
    # 含糊 >0 只印 warning 不 fail：這是帳本品質提示，非跨文件矛盾。
    vague_ids = sorted(def_id for def_id, cls in ledger.items() if cls is None)
    if vague_ids:
        print(f"⚠️  帳本狀態含糊 {len(vague_ids)} 筆（狀態欄辨識不出已知關鍵字）："
              f"{'、'.join(vague_ids)}", file=sys.stderr)

    # 帳本家族的 archive 半邊（DEF-101-676，R68）——主檔查不到的 ID 回退到這裡再驗一次，
    # 讓「被宣稱過的列」不再因為歸檔就假紅。**不是**放寬一致性：回退後照樣逐筆比對狀態。
    archive_status = _load_archive_status()

    all_problems: list[str] = []
    for target in _CROSSREF_TARGETS:
        if not target.exists():
            return _bail("掃描目標齊備", detail=f"找不到掃描目標：{target}")
        all_problems.extend(_scan_target(target, ledger, archive_status))
        # R69 DEF-101-735：`_scan_target` 只認「ID 緊接括號」，散文式「<ID> …結案」它看不見。
        all_problems.extend(closure_claim_problems(
            target.name, target.read_text(encoding="utf-8-sig"), {**archive_status, **ledger}))

    if all_problems:
        return _bail("缺陷帳本跨文件狀態不一致", all_problems)
    if deferred:  # 體積與逐列位元組：最後一道，故不遮蔽任何診斷
        return _bail("帳本體積與逐列位元組上限", deferred)

    vague_note = f"（另 {len(vague_ids)} 筆狀態含糊，見 warning）" if vague_ids else ""
    print(f"✅ 缺陷帳本跨文件狀態一致：帳本 {len(ledger) - len(vague_ids)} 筆有效狀態紀錄"
          f"{vague_note}、{len(_CROSSREF_TARGETS)} 份掃描目標皆無矛盾；"
          f"另全部表格列的狀態欄首詞皆落在《格式定義》宣告的 {len(_STATUS_FIRST_WORDS)} 個"
          "合法值內（散文與程式常數雙向綁定，且每個合法值都有分類器對應）；"
          "全部表格列的欄數皆等於表頭欄數、狀態欄由表頭定位（非 cells[-1] 位置猜測）；"
          f"具名治理文件 {len(_GOVERNANCE_DOCS)} 份皆已登記且未逾體積上限"
          f"（登記面對 {_GOVERNANCE_DOC_GLOB} 發現面雙向核對）；"
          f"全部未結案列的承接輪次皆 ≥ 當前輪 R{current_round(ledger_text)} 或已載明改派"
          "（硬規則②；已實測不涵蓋的形態見 orphan_backlog_problems docstring）；"
          f"未結存量 {len(_ledger_index.unresolved_ids(ledger))} 列（唯一量測入口＝"
          f"`--unresolved-count`；warn {_ledger_index.UNRESOLVED_ROWS_WARN}／fail "
          f"{_ledger_index.UNRESOLVED_ROWS_FAIL} 列）且皆二擇一（承接輪號／字面"
          f"「{_UNASSIGNED_LITERAL}」，存量豁免 {len(_UNPINNED_HANDOVER_GRANDFATHERED)}"
          f" 筆／棘輪上限 {_UNPINNED_HANDOVER_CEILING}，只准變小）"
          f"{f'；另 {len(residual)} 筆已結列殘留待辦，見 warning' if residual else ''}。"
          f"\n🔴 當前輪 R{current_round(ledger_text)} 係由帳本「{_CONTEXT_HEADER}」欄"
          "**現查**推得（不寫死）——本輪若尚未寫入任何帳本列，此值仍停在上一輪，"
          "屆時「交棒給剛結束的那一輪」會合法通過（刻意選的 fail-open 方向：漏抓而非"
          "假紅，窗口於本輪第一列落地時自動關閉，見 lagging_clock_notes()）")
    return 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
