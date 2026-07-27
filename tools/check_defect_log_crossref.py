#!/usr/bin/env python3
"""缺陷帳本 × 高風險文件「狀態宣稱」跨文件一致性機械守護（DEF-101-068(e) 落地）。

本工具目前承擔四類守門（彼此獨立，任一紅即 exit 1）：
  A. 跨文件「狀態宣稱」一致性（本 docstring 主體，DEF-101-068(e)）。
  B. 帳本體積輪替界線（主檔與每一個 archive 檔 < 256KB；DEF-99-001／DEF-101-123）。
  C. 帳本〈已歸檔內容〉索引 vs 磁碟實際 archive 檔的完整性（DEF-101-510；
     見 `_check_archive_index()` docstring）。
  D. **反向**懸空引用：程式碼／文件引用的 DEF 編號必須在帳本查得到表格列
     （SA-R58R1-03；見 `_check_reverse_refs()` docstring）。A 類是「帳本 → 四份指定
     文件」的正向狀態比對，對「引用了一個帳本根本沒有的編號」零鑑別力；D 類補的正是
     這個反向方向。

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
  - 沒有括號緊跟在 ID 後面的單純引用（例如「見 DEF-101-058」）**不做狀態比對**——
    這類引用未對狀態做任何明確宣稱，強行判讀等同瞎猜，故刻意略過以避免假陽性。
    （但這類裸引用的**編號存在性**由下方 D 類守門檢查，不再是完全的盲區。）
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

使用：
  python3 tools/check_defect_log_crossref.py   # 於 repo 內任意 cwd；不一致印清單並 exit 1
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterable
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
    """
    status: dict[str, str | None] = {}
    text = _DEFECT_LOG.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        if not _ROW_RE.match(line):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line) if c.strip()]
        if len(cells) < 2:
            continue
        def_id, status_cell = cells[0], cells[-1]
        if not _ID_RE.fullmatch(def_id):
            continue
        status[def_id] = _classify(status_cell)
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

# ── 帳本歸檔索引完整性（DEF-101-510）──────────────────────────────────────────
# WHY：主檔〈已歸檔內容〉節以「**N 檔**」開頭並逐檔列出 archive 條目，但「索引條目
# vs 磁碟實際 archive 檔」此前**零機械守門**——本工具只量各檔體積（上方 B 類守門），
# 不查索引完整性。實害已發生：R56 真的漏登過一檔（DEF-101-476，造成引用鏈斷裂），
# R57 起連三輪只能靠人工核對「索引條目數 == 磁碟檔數」。靠人記得＝必然腐化，故機械化。
_ARCHIVE_GLOB = "AutoSDD_Defect_Log_archive_*.md"
_ARCHIVE_FILE_RE = re.compile(r"^AutoSDD_Defect_Log_archive_(\d+)\.md$")
# 索引節標題樣式：`> **已歸檔內容**（**二十八檔**；…`（括號全／半形皆收）。
# 數字部分刻意收得寬（任意 CJK 而非只收合法中文數字）：寫法錯誤時要落到
# `_cn_to_int` 去 fail loud，而不是整條 header regex 比不到、被當成「沒有索引節」。
_ARCHIVE_INDEX_HEADER_RE = re.compile(
    r"\*\*已歸檔內容\*\*[（(]\s*\*\*([一-鿿]+)檔\*\*"
)
# 索引條目樣式：`> - **`AutoSDD_Defect_Log_archive_01.md`**（…`
# 刻意綁定行首 `>` + `-` + 反引號包裹的完整檔名：散文中順帶提及 `archive_01.md`
# （帳本〈已知歷史重疊〉段落就有）不會被誤計為索引條目。
_ARCHIVE_INDEX_ENTRY_RE = re.compile(
    r"^>\s*-\s*\*\*`(AutoSDD_Defect_Log_archive_(\d+)\.md)`\*\*"
)

# 中文數字↔阿拉伯數字（供索引節標題「N 檔」比對）。支援到「千」位（≈9999 檔），
# 遠超實際需求；**超出支援範圍一律 fail loud 而非靜默略過**——靜默略過等於這道鎖
# 將來自己失效（本 repo 反覆踩過「守門靜默縮面」）。「零」視為佔位符跳過，
# 才能正確解析「一百零五」這類寫法。
_CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}


def _cn_to_int(text: str) -> int | None:
    """中文數字字串 → int；寫法不支援或超出「千」位範圍回 None（呼叫端須 fail loud）。"""
    total = 0
    pending: int | None = None
    for ch in text:
        if ch == "零":
            continue
        if ch in _CN_DIGITS:
            if pending is not None:
                return None  # 相鄰兩個數字（如「一二」）非合法中文數字寫法
            pending = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            total += (1 if pending is None else pending) * _CN_UNITS[ch]
            pending = None
        else:
            return None  # 含「萬」等未支援字元 → 由呼叫端要求擴充本轉換
    if pending is not None:
        total += pending
    return total


def _int_to_cn(n: int) -> str | None:
    """int → 中文數字字串（1~9999）；超出範圍回 None。用於產生「該改成什麼」的可行動訊息。"""
    if not 1 <= n <= 9999:
        return None
    digits = "零一二三四五六七八九"
    units = ["", "十", "百", "千"]
    out: list[str] = []
    s = str(n)
    for i, ch in enumerate(s):
        d, pos = int(ch), len(s) - i - 1
        if d == 0:
            out.append("零")
        elif d == 1 and pos == 1 and not out:
            out.append(units[pos])  # 中文慣寫「十八」而非「一十八」
        else:
            out.append(digits[d] + units[pos])
    text = "".join(out)
    while "零零" in text:
        text = text.replace("零零", "零")
    return text.rstrip("零") or "零"


def _check_archive_index() -> list[str]:
    """核對帳本〈已歸檔內容〉索引與磁碟實際 archive 檔，回傳問題清單（空＝通過）。

    三道檢查（各自 fail loud，訊息含「要改哪裡、怎麼改」）：
      1. **雙向對應**：磁碟上每個 archive 檔都須有索引條目；索引列了但磁碟不存在的
         stale 條目同樣紅。
      2. **標題新鮮度**：索引節標題的中文數字「N 檔」須等於實際條目數。
      3. **編號連續性**：archive_01~archive_NN 不得缺號（缺號＝有檔被誤刪或誤命名）。

    涵蓋面（三段式）：
      - 已實測涵蓋：漏登條目、stale 條目、標題數字 stale、缺號、索引節整段消失
        （磁碟有 archive 卻無標題）、中文數字寫法不支援。
      - 已實測不涵蓋：條目**內文敘述**是否與該 archive 實際內容相符（本工具不理解
        自然語言，同上方 A 類守門的既有邊界）；archive 之間內容重疊
        （帳本〈已知歷史重疊〉段落記載的既有情形）。
      - 未窮舉：檔名非 `archive_<純數字>.md` 的其他變形命名（會被列為「命名不符」而紅，
         但未逐一枚舉所有可能變形）。
    """
    problems: list[str] = []
    disk: dict[int, str] = {}
    for path in sorted(_DEFECT_LOG.parent.glob(_ARCHIVE_GLOB)):
        matched = _ARCHIVE_FILE_RE.match(path.name)
        if not matched:
            problems.append(
                f"磁碟檔名不符 archive 命名規則：{path.name}"
                "（應為 AutoSDD_Defect_Log_archive_<數字>.md；請更名或移出本目錄）"
            )
            continue
        num = int(matched.group(1))
        if num in disk:  # 例如同時存在 archive_7.md 與 archive_07.md
            problems.append(
                f"archive 編號 {num} 對應多個檔案（{disk[num]} 與 {path.name}）"
                "——請統一為單一零補位命名"
            )
            continue
        disk[num] = path.name

    text = _DEFECT_LOG.read_text(encoding="utf-8-sig")
    entries: list[str] = []
    for line in text.splitlines():
        matched = _ARCHIVE_INDEX_ENTRY_RE.match(line)
        if matched:
            entries.append(matched.group(1))

    header = _ARCHIVE_INDEX_HEADER_RE.search(text)
    if header is None:
        if disk or entries:
            problems.append(
                f"帳本找不到〈已歸檔內容〉索引節標題（樣式：`**已歸檔內容**（**N 檔**；…`），"
                f"但磁碟有 {len(disk)} 個 archive 檔／文中有 {len(entries)} 筆條目"
                "——請補回索引節，勿讓歸檔失去索引"
            )
        return problems  # 零 archive 且無索引節＝一致（尚未開始輪替），非缺陷

    dupes = sorted({name for name in entries if entries.count(name) > 1})
    if dupes:
        problems.append(
            f"索引節同一 archive 重複列出 {len(dupes)} 檔（{'、'.join(dupes)}）"
            "——請刪除重複條目"
        )

    entry_names = set(entries)
    disk_names = set(disk.values())
    missing = sorted(disk_names - entry_names)
    if missing:
        problems.append(
            f"磁碟存在但索引節未登記 {len(missing)} 檔（{'、'.join(missing)}）"
            "——請在〈已歸檔內容〉節依樣式補上條目 "
            "`> - **`檔名`**（建立輪次／時間／搬移對象／體積變化）：…`"
            "（R56 DEF-101-476 即為此類漏登，造成引用鏈斷裂）"
        )
    stale = sorted(entry_names - disk_names)
    if stale:
        problems.append(
            f"索引節登記但磁碟不存在 {len(stale)} 檔（{'、'.join(stale)}）"
            "——請確認檔案是否被誤刪／誤更名，或刪除該 stale 條目"
        )

    claimed_cn = header.group(1)
    claimed = _cn_to_int(claimed_cn)
    actual_cn = _int_to_cn(len(entries))
    if claimed is None:
        problems.append(
            f"索引節標題的中文數字「{claimed_cn}檔」無法解析"
            "——請改用本工具 `_cn_to_int` 支援的寫法（一~九、十、百、千組合），"
            "或擴充該轉換函式的支援範圍（刻意不靜默略過，避免這道鎖自己失效）"
        )
    elif claimed != len(entries):
        suggestion = f"「{actual_cn}檔」" if actual_cn else f"{len(entries)}（超出中文數字轉換範圍）"
        problems.append(
            f"索引節標題宣稱「{claimed_cn}檔」（＝{claimed}），實際條目數 {len(entries)}"
            f"——請把標題數字改為{suggestion}"
        )

    if disk:
        expected = set(range(1, max(disk) + 1))
        gaps = sorted(expected - set(disk))
        if gaps:
            problems.append(
                f"archive 編號不連續，缺號 {gaps}（現存最大號 {max(disk)}）"
                "——缺號代表有檔案被誤刪或誤命名，請補回檔案或重整編號"
            )
    return problems


# ── D. 反向懸空引用掃描（SA-R58R1-03）─────────────────────────────────────────
# WHY：A 類只做「帳本 → 四份指定文件」的正向狀態比對，對反向的懸空引用**零鑑別力**
# ——程式碼／文件寫了某個 DEF 編號、帳本（含 archive）根本查無此號，本工具照樣 rc=0。
# 實害已發生：R58 SA 實測 `DEF-101-507` 被 13 處生產測試碼與規範判例文件引用，帳本
# 卻查無 507／509／511 任何一號，工具全綠。「程式碼指向不存在的缺陷編號」在本 repo
# 從來沒有任何機械訊號，故補此反向掃描。
#
# ⚠️ 已知連動（落地時實測確認，非推測）：`tools/tests/test_stdio_utf8.py` 的
# `test_real_cli_tool_survives_legacy_locale` 拿**本 CLI** 當 production 載具並斷言
# `rc == 0`。因此只要 D 類是紅的（＝有編號還沒補進帳本），那條鎖也會連帶紅。
# 這不是缺陷、也不該靠改那條鎖來繞過：把帳本條目補齊、D 類轉綠，它自然回綠
# （實測：動工前版本 9 tests OK → 本類落地後 1 failure，全數來自 rc 斷言）。
#
# 收集合法編號時**不能**沿用 A 類的 `_ROW_RE`：實測 `AutoSDD_Defect_Log_archive_02.md`
# 用的是 blockquote 壓縮表格（`> | **DEF-54-001** | P3 | … |`），`_ROW_RE`（綁行首 `|`、
# 不吃粗體）對它一列都比不到——若直接沿用，會把 archive_02 全部條目誤判為「懸空」而
# 製造大量假紅（實測差距：permissive 前 618 個已知編號 → 後 623 個）。故另立一支
# 較寬鬆的 `_LEDGER_ROW_ANY_RE` 專供本類使用，A 類的 `_ROW_RE` 保持原樣不動
# （它另有「最後一欄＝狀態」的語意需求，收寬會引入別的風險）。
_LEDGER_ROW_ANY_RE = re.compile(r"^\s*>?\s*\|\s*\*{0,2}(DEF-\d+-\d+)\*{0,2}\s*\|")

# 引用樣式：`DEF-\d+-\d+`，但右側緊接 x/X/n/N 者排除——本 repo 慣以 `DEF-101-3xx`／
# `DEF-94-NN` 表示「系列／佔位」而非具體編號（實測 `AISDLC_SDD_v0.30/tools/fsm_runtime/
# tests/test_phase_i.py:341` 就寫 `DEF-101-3xx`，裸 regex 會把它截斷成一個三位數只剩
# 首位的幻影編號並回報懸空）。本註解刻意不寫出那個幻影編號字面值：寫了就等於在本檔
# 自製一筆真的懸空引用（本次落地實測踩到過一次，由本鎖自己抓出來）。
# 只排掉這四個字母：實測掃描面內無任何真編號右接 x/X/n/N（`DEF-10-002a` 這類子編號變體
# 右接 `a`，仍會正確抽出母號 `DEF-10-002` 並比對）。
_REVERSE_ID_RE = re.compile(r"DEF-\d+-\d+(?![xXnN])")

# 掃描面＝**全 repo git-tracked 檔案**，唯一剔除 `AISDLC_SDD/AISDLC_SDD_v0.NN/`。
# 決定依據（實測數字，非猜測）：
#   - git-tracked 27,440 檔中 26,072 檔（95%）位於 `AISDLC_SDD_v0.NN/`；剔除後只剩
#     1,368 檔，全 repo 掃描的成本因此可忽略——這是「為何敢擴到全 repo」的理由。
#   - 剔除的理由是**紅了無法修**：這些目錄依 Copy-on-Evolve 紀律不回改，其中實測有
#     2 個懸空編號（一個是上述 `DEF-101-3xx` 佔位寫法被截斷後的幻影；另一個是
#     improving_95 輪某筆只寫在敘事段落、從未登錄成帳本表格列的編號，在各版
#     `EVOLUTION_LOG.md` 被引用 16 處），納入即成永久假紅。LATEST 版（目前 v0.30）雖仍在演進，
#     其內容係從前一凍結版逐字複製而來，懸空引用屬「繼承而來的歷史敘述」而非本輪新寫，
#     同樣不該由本鎖阻擋，故一併剔除、不做「只放行 LATEST」的特例。
#   - 擴到全 repo 的效益（實測）：required 最小面（tools/**、docs/06_quality/**、
#     AutoClaude/tools/**、AutoClaude/docs/**、AISDLC_SDD/scripts/**）之外還撈到
#     `AutoClaude/autoclaude/artifact_check.py`（生產碼）、`docs/04_planning/**`、
#     `docs/03_testing/**` 的引用點；且**未新增任何一個** required 面沒有的懸空編號
#     ——代表擴面不增加補帳負擔，只讓同一批編號的引用位置全部現形。
_REVERSE_SCAN_EXCLUDE_RE = re.compile(r"^AISDLC_SDD/AISDLC_SDD_v0\.\d+/")

# 每個懸空編號最多列出幾個引用位置（其餘以「另 N 處」帶過）——訊息要可行動但不可
# 變成一面牆（實測單一懸空編號最多達 40 處引用）。
_REVERSE_MAX_SITES_PER_ID = 5

# 廢號白名單：「帳本查無此號，但該引用屬合法」的**顯式**豁免。key＝編號、value＝理由。
# 三道自檢（見 `_check_retired_whitelist()`）：理由為空即紅、編號其實存在於帳本即紅
# （代表白名單過期）、key 非 `DEF-數字-數字` 形狀即紅（打錯字的 key 永遠不會命中，
# 看起來有豁免其實沒有）。
# 🔴 白名單**不是**「還沒寫帳本」的擋紅工具：本輪新產生的編號一律該去補帳本條目，
# 塞進這裡等於把假綠制度化。
_RETIRED_DEF_IDS: dict[str, str] = {
    "DEF-88-001": (
        "非真實缺陷編號，是 DEF-101-084 該列描述 bug 重現手法時虛構的示例："
        "`ledger.get('DEF-88-001')` 仍回傳 'fixed'。實測全 repo 僅此 1 處引用"
        "（docs/06_quality/AutoSDD_Defect_Log_archive_04.md 該表格列內文），"
        "已歸檔不回改，且它本來就不該有帳本條目。"
    ),
    "DEF-99-999": (
        "本工具自身單元測試（tools/tests/test_check_defect_log_crossref.py）"
        "刻意用來測 `_scan_target` 的『帳本查無此 ID』分支的合成編號，"
        "非真實缺陷。新增測試 fixture 若需要一個『帳本查無』的編號，"
        "請沿用本號，勿再新增白名單條目。"
    ),
}


def _collect_known_def_ids() -> set[str]:
    """收集主帳本＋全部 archive 的表格列編號＝「合法 DEF 編號」全集。

    刻意只認**表格列**（`_LEDGER_ROW_ANY_RE`）而非散文提及：帳本的敘事段落本身就會
    提到一堆編號，若把散文也算「已登錄」，本鎖就退化成「只要在帳本裡出現過就放行」，
    完全抓不到「narrative-only、從未登錄成列」這個真實存在的漏登形狀（實測 improving_94／
    improving_95 兩輪合計 5 筆缺陷編號即屬此類：只寫在 archive 的敘事段落裡，全 repo
    找不到任何一列表格列；此處刻意不列出編號字面值，否則本檔自己就成為懸空引用來源）。
    """
    known: set[str] = set()
    for path in [_DEFECT_LOG, *sorted(_DEFECT_LOG.parent.glob(_ARCHIVE_GLOB))]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            matched = _LEDGER_ROW_ANY_RE.match(line)
            if matched:
                known.add(matched.group(1))
    return known


def _tracked_scan_paths() -> tuple[list[str], str | None]:
    """git-tracked 檔案的 POSIX 相對路徑清單（已剔除凍結版目錄）。

    回傳 `(paths, error)`；`error` 非 None 時 `paths` 無意義，呼叫端須把 error 當紅燈。
    刻意用 `git ls-files` 而非目錄走訪：未追蹤的暫存筆記／衍生產物若被掃到會製造
    無人負責的假紅，而「tracked」正是「這份引用有人負責維護」的界線。
    空清單一律視為錯誤（fail loud）——git 壞掉或剔除規則寫過頭時，靜默回空等於這道鎖
    自己失效（本 repo 反覆踩過「守門靜默縮面」）。
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            check=False,
        )
    except OSError as exc:  # git 不存在／不可執行
        return [], (
            f"無法執行 `git ls-files`（{exc}）——反向懸空引用掃描需要可用的 git 工作樹；"
            "請在 git checkout 內執行本工具"
        )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace").strip()
        return [], f"`git ls-files` 失敗（rc={proc.returncode}）：{stderr}"
    rels = [r for r in proc.stdout.decode("utf-8", "replace").split("\0") if r]
    if not rels:
        return [], "`git ls-files` 回傳空清單——本 repo 不可能零追蹤檔案，請檢查 git 狀態"
    kept = [r for r in rels if not _REVERSE_SCAN_EXCLUDE_RE.match(r)]
    if not kept:
        return [], (
            f"剔除凍結版目錄後掃描面歸零（原 {len(rels)} 檔）"
            "——`_REVERSE_SCAN_EXCLUDE_RE` 疑似寫過頭，請修正"
        )
    return kept, None


def _scan_reverse_refs(
    root: Path, rel_paths: Iterable[str], known: set[str]
) -> list[str]:
    """在 `root` 下逐一讀 `rel_paths`，回報引用了帳本查無編號的位置（空＝通過）。

    純函式（不碰模組層路徑常數），故可用合成 fixture 完整測試邏輯，不依賴真實帳本狀態。

    涵蓋面（三段式）：
      - 已實測涵蓋：懸空編號（含同號多處引用的聚合與「另 N 處」截斷）、白名單豁免、
        帳本存在即放行、二進位檔跳過、`DEF-101-3xx` 佔位寫法不誤抽幻影編號。
      - 已實測不涵蓋：區間寫法 `DEF-101-502~505` 只會檢查頭一個編號（`505` 缺
        `DEF-` 前綴，本 regex 抽不到），故區間尾端的懸空無法偵測；非 `DEF-數字-數字`
        形狀的編號家族（實測存在 `DEF-CLDREV-026`、`DEF-101-B`）不在本鎖範圍；
        「已配號但全 repo 尚無任何引用」的編號**不會**被回報（本輪實測就有一個這種
        號：帳本 0 列、引用 0 處）——本鎖守的是「引用指向不存在的編號」，不是
        「配出去的號有沒有用掉」，後者要靠人工或另一支工具。
      - 未窮舉：`_REVERSE_SCAN_EXCLUDE_RE` 剔除面之外的其他「紅了不該修」情境
        （目前只實測認定凍結版目錄一類）。
    """
    sites: dict[str, list[str]] = {}
    for rel in rel_paths:
        path = root / rel
        try:
            raw = path.read_bytes()
        except OSError:
            # git index 有、磁碟沒有（sparse checkout／剛刪未 commit）——不是本鎖職責，
            # 且硬要紅會讓正常的刪檔流程卡住。
            continue
        if b"\x00" in raw:
            continue  # 二進位檔，比照 `git grep -I` 的判定方式
        text = raw.decode("utf-8-sig", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            for def_id in _REVERSE_ID_RE.findall(line):
                if def_id in known or def_id in _RETIRED_DEF_IDS:
                    continue
                sites.setdefault(def_id, []).append(f"{rel}:{lineno}")

    problems: list[str] = []
    for def_id in sorted(sites):
        locs = sites[def_id]
        shown = "、".join(locs[:_REVERSE_MAX_SITES_PER_ID])
        rest = len(locs) - _REVERSE_MAX_SITES_PER_ID
        more = f"（另 {rest} 處）" if rest > 0 else ""
        problems.append(
            f"{def_id}：帳本（主檔＋archive_NN）查無此編號的表格列，卻有 {len(locs)} 處"
            f"引用 → {shown}{more}"
            "；請在缺陷帳本補上該編號的表格列，或（確為廢號／示例號時）"
            "加入 `_RETIRED_DEF_IDS` 並寫明理由"
        )
    return problems


def _check_retired_whitelist(known: set[str]) -> list[str]:
    """廢號白名單自檢：理由為空、編號其實已登錄帳本（過期）、key 形狀錯誤 → 皆紅。"""
    problems: list[str] = []
    for def_id, reason in _RETIRED_DEF_IDS.items():
        if not _ID_RE.fullmatch(def_id):
            problems.append(
                f"廢號白名單 key「{def_id}」不是 `DEF-<數字>-<數字>` 形狀"
                "——形狀錯誤的 key 永遠不會命中任何引用，看似有豁免其實沒有，請訂正"
            )
        if not reason.strip():
            problems.append(
                f"廢號白名單 {def_id} 的理由為空——每一筆都必須寫明「為何帳本查無此號"
                "仍屬合法引用」，否則等同無條件豁免，白名單會淪為擋紅後門"
            )
        if def_id in known:
            problems.append(
                f"廢號白名單 {def_id} 其實存在於帳本表格列——白名單已過期"
                "（該號已補登錄，或當初判定有誤），請刪除此筆讓正常守門接手"
            )
    return problems


def _check_reverse_refs() -> list[str]:
    """D 類守門總入口：回傳問題清單（空＝通過）。

    順序刻意先跑白名單自檢再掃引用：白名單過期時，被它豁免掉的引用本來就不該再豁免，
    先把「豁免機制自己壞了」講清楚，比先吐一串引用位置更容易處置。
    """
    known = _collect_known_def_ids()
    problems = _check_retired_whitelist(known)
    if not known:
        problems.append(
            "帳本表格列解析結果為空——`_LEDGER_ROW_ANY_RE` 疑似與帳本格式脫節，"
            "此時任何引用都會被判懸空，本鎖已失去意義，請先修正解析"
        )
        return problems
    rel_paths, error = _tracked_scan_paths()
    if error:
        problems.append(error)
        return problems
    problems.extend(_scan_reverse_refs(_REPO_ROOT, rel_paths, known))
    return problems


_EXPECTED_ROW_CELLS = 7  # ID／發現日期／發現情境／缺陷描述／優先級／處置去向／狀態
# 位置性斷言用（見 `_check_row_shape` 內註解）：只認機械可判的形狀，不解讀語意。
_DATE_CELL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
# 帳本現況允許的優先級寫法：`P0`~`P4`（後可接說明）、或流程紀錄用的 `—`／`N/A`。
_PRIORITY_CELL_RE = re.compile(r"^(?:P[0-4]|—|-|N/A)")


def _check_row_shape() -> list[str]:
    """每一列表格必須恰為 7 欄——**欄位內部的裸 `|` 必須轉義成 `\\|`**。

    **為什麼需要這道鎖（R58 落地，立案於一筆既有事故）**：markdown 表格以 `|` 分欄，而
    `_load_ledger_status()` 取 `cells[-1]` 當狀態欄。若某列的內容含未轉義的 `|`
    （寫 shell pipeline `git ls-files … | grep …` 或貼測試輸出 `'Object[]|1 True'` 時極易發生），
    該列會被切成 8+ 欄，`cells[-1]` **不再是狀態欄** → 該列的狀態被靜默誤讀成別的欄位內容。

    症狀很輕（只在 warning 裡出現一行「狀態含糊」），所以會被忽略；而後果是**該列從此不受
    跨文件狀態一致性比對保護**。R58 寫入新條目時踩到兩次，並在修正時**順帶發現 R57 寫的
    `DEF-101-498` 早已是同一形態**（自 R57 起一直被誤讀，無人察覺）——這正是本鎖存在的理由：
    當初若有它，該列在寫入的那一刻就會紅。

    刻意判「恰為 7」而非「至少 7」：欄位少了也是壞（表格結構破損），兩個方向都要抓。
    """
    problems: list[str] = []
    for lineno, line in enumerate(_DEFECT_LOG.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not _ROW_RE.match(line):
            # **粗掃（R58 round 3 SD-R58R3-02）**：`_ROW_RE` 要求 `| DEF-…-… |`，故「ID 後
            # 第一個真分隔符被誤轉義成 `\|`」的列**連 `_ROW_RE` 都不 match** ⇒ 對本函式完全
            # 隱形，同時也從 `_load_ledger_status()` 的狀態解析中靜默消失（該 ID 從此不受
            # 跨文件比對保護，且只有在它剛好有外部引用時才會被懸空引用檢查間接兜底）。
            # 故對「以 `|` 起頭且含 DEF-ID 但不被 `_ROW_RE` 認出」的行獨立報一次。
            if line.startswith("|") and _ID_RE.search(line):
                problems.append(
                    f"L{lineno}：本行以 `|` 起頭且含 DEF-ID，卻不被缺陷列樣式認出"
                    "——疑似 ID 欄後的真分隔符被誤轉義成 `\\|`（該列會從狀態解析中靜默消失）"
                )
            continue
        # 前後各有一個空字串（列以 `|` 起訖），故合法總數為 7 + 2
        cells = re.split(r"(?<!\\)\|", line)
        def_id = line.split("|")[1].strip()
        if len(cells) != _EXPECTED_ROW_CELLS + 2:
            problems.append(
                f"L{lineno} {def_id}：切出 {len(cells) - 2} 欄，應為 {_EXPECTED_ROW_CELLS} 欄"
                "——若是內容含裸 `|`（shell pipeline／測試輸出），請改寫成 `\\|`"
            )
            continue
        # **位置性斷言**（R58 round 2 QA-R58R2-02）：只數欄數時，**兩個相反方向的錯誤會互相
        # 抵銷**——把真分隔符誤轉義（欄位被併掉，-1）同時內容留著裸 `|`（欄位被切開，+1），
        # 欄數恰好湊回 7 而語意整體位移。本輪 `DEF-101-527` 那一列自己就是這個存在性反證：
        # 第一版「修好」後欄數為 7、crossref rc=0，但第 4 欄被切開、第 6/7 欄被併掉。
        # 故再驗兩個機械可判的欄位形狀（成本三行、零假陽性）。
        if not _DATE_CELL_RE.match(cells[2].strip()):
            problems.append(
                f"L{lineno} {def_id}：第 2 欄（發現日期）為 {cells[2].strip()[:24]!r}，"
                "不符 `YYYY-MM-DD`——欄數對不代表欄位對，請檢查是否把真正的分隔符誤轉義成 `\\|`"
            )
        if not _PRIORITY_CELL_RE.match(cells[5].strip()):
            problems.append(
                f"L{lineno} {def_id}：第 5 欄（優先級）為 {cells[5].strip()[:24]!r}，"
                "不符 `P0`~`P4` 或 `—`／`N/A`——欄數對不代表欄位對，"
                "請檢查是否把真正的分隔符誤轉義成 `\\|`"
            )
    return problems


# 「自身全部條目（DEF-101-NNN 起）完整留在主檔」宣稱的錨。**刻意只抓起點、不抓終點**——
# 見 `retained_range_problems()` docstring〈為什麼終點不再入帳〉。
# 刻意用 `自身全部條目`（而非較寬的 `自身條目`）：後者會命中帳本內**引述歷史錯誤原文**的
# 訂正痕跡，那些該保留、不該翻紅。
# 🔴 `[*_\s]*` 是必要的（round 10 三方各自抓到）：**本帳本的家規就是把關鍵數字加粗**，
# 而 round 9 落地時自己寫的那個站點正是 `（**DEF-101-507 起**）` ⇒ 初版述詞 4 個站點只認 3 個，
# 而 docstring 卻寫「現存站點皆命中」。這是「述詞漏一種拼法就漏一個站點」在本鎖上的**第 3 次**
# 復發（round 7 漏 `\s*` 抓 2/3、round 8 輪次歸屬雙向壞、round 10 漏粗體抓 3/4）。
# 同檔姊妹述詞 `_CLAIM_RE` 早已用 `\*{0,2}` 處理粗體，本述詞當時沒沿用。
_RETAINED_START_RE = re.compile(
    r"自身全部條目[*_\s]*[（(]?[*_\s]*(?:DEF-101-)?(\d{3})\s*起"
)


def _row_first_cell_def101(line: str) -> int | None:
    r"""表格列的**第一欄**若為 `DEF-101-NNN` 則回傳 NNN，否則 None。

    round 10 SA／QA 各自指出：原本用 `re.search(r"DEF-101-(\d{3})", line)` 掃整行，等於取
    「該列第一個 DEF-101 **提及**」而非該列的 ID。archive 內 ID 非 `DEF-101-*` 的列
    （如 archive_29 的 DEF-95-001／002）若敘述中提到 `DEF-101-≥起點`，會被登記成幻影
    「已歸檔編號」→ 假紅。今日良性（實測零命中），但方向錯，落地當下即改。
    """
    cells = line.split("|")
    if len(cells) < 2:
        return None
    m = re.fullmatch(r"\s*DEF-101-(\d{3})\s*", cells[1])
    return int(m.group(1)) if m else None


def retained_range_problems(ledger_text: str, sources: dict[str, str]) -> list[str]:
    """驗證「R<N> 自身全部條目（DEF-101-<起點> 起）完整留在主檔」這類宣稱。

    判準（**兩個半邊，零啟發式**）：宣稱起點以後的每一個 DEF-101 編號都必須**還在主檔**。
    這句話有兩半，round 9 初版**只實作了反向那半**：

      * **反向**：`>= 起點` 的編號不得出現在任何 archive 檔的表格列裡（有人把該範圍內某列
        搬進 archive，而宣稱沒跟著改）。
      * **正向**（round 10 ARCHITECT-R58R10-01 補上）：`[起點, 主檔最大編號]` 之間不得斷號。
        round 9 初版把 `ledger_text` 收在簽章裡卻**一次都沒讀**（三方以
        `retained_range_problems("", sources)` 與餵垃圾字串結果全等坐實），於是
        **「範圍內某列被整列刪除」（非搬進 archive）完全靜默**——而那正是原鎖守得住、
        拆掉後失去的東西，且 docstring 用一個「換言之」把正反兩半當等價，實測為假。
        **這是「宣稱涵蓋面 > 實測涵蓋面」長在本輪修復本體裡**，故補實作而非改小宣稱。

    訊息刻意區分兩種缺法（搬進 archive／不在任何地方），因為修法不同：前者是訂正宣稱或
    確認誤搬，後者是該列被誤刪、要從 git 歷史找回。

    ## 🔴 為什麼終點不再入帳（round 9 拆掉輪次界判準的理由）

    round 7 立這個鎖時，判準是「宣稱終點 == 主檔全域最大列」。round 8 四方全數 REJECT：
    那個不變式只在「本輪是最新輪」的前提下成立，下一輪必然失效，而守門訊息會**逼維護者
    宣稱本輪擁有下一輪的條目**。round 8 我改成「輪次界」——只對持有最大列的那一輪要求等值，
    輪次歸屬取帳本列標題欄的第一個 `R<數字>`。**round 9 四方又全數 REJECT，五項同一根因**：

      * **假紅未消滅、只被收窄**：本帳本開輪列的慣例正是「標題先提上一輪」
        （真檔 DEF-101-509／514／518／519 四列即如此）。下一輪首列若寫成
        「R58 backlog 的 R59 落地」，`owner_round` 仍算成 58 ⇒ 三個站點照樣假紅。
      * **更糟的是假綠**：若某輪的**最高號列**標題先提上一輪，判準就完全不開火
        ⇒ **原立案病灶（同輪端點過期）靜默穿過**。三方各以紅綠對照坐實。
      * 我為它寫的 7 支自驗全用「R59 某事」這種本家慣例不會出現的標題 ⇒ 恆綠、
        對真實語料的形態零覆蓋；QA 另實測「刪掉不變式 (2) 整段分支，7 支自驗全數仍綠」。

    **結論不是再補一次述詞，而是承認問題出在「把一個會過期的衍生數字寫進散文」**。
    終點從宣稱裡移除後：句子永遠為真、無需輪次概念、無需啟發式、沒有 fail-open 分支，
    這條剩下的判準也就變成零啟發式的事實比對。這是本 repo 一貫政策
    「**數字只准住一個家**」的更強版本——**能不寫的衍生數字就不要寫**。

    ## 掃描面（三段式）

    **已實測涵蓋**：`R<N> 自身全部條目（DEF-101-<起點> 起` 字面（**含粗體變體**；round 10
    落地當下實測 4/4 站點命中，並配「寬 grep 命中數 == 述詞命中數」的平價鎖，見
    `tools/tests/test_check_defect_log_crossref.py::TestRetainedRangeClaims`），以及該範圍內
    任一列**被搬進 archive**或**被整列刪除**兩種缺法（各有紅向自驗，另有兩支綠向邊界自驗）。
    **已實測不涵蓋**：改用別的措辭表達同一宣稱者——`自身全部條目` 是**承重字面**，
    換句話說即失去守門（刻意取捨：比對照全部自然語言寫法的假陽性成本低）。
    **未窮舉**：不宣稱除此之外無盲區。
    """
    problems: list[str] = []
    if not any("archive" not in name for name in sources):
        # fail-loud（round 10 SD-R58R10 #2）：`sources` 若只有 archive、沒有主檔來源，
        # 正向半邊會拿不到母體而靜默零回報——那正是誘發假綠的形狀。
        raise ValueError("sources 必須含至少一個非 archive 的主檔來源，否則正向檢查無母體")

    archived: dict[int, str] = {}
    for name, text in sources.items():
        if "archive" not in name:
            continue
        for line in text.splitlines():
            if not _ROW_RE.match(line):
                continue
            num = _row_first_cell_def101(line)
            if num is not None:
                archived.setdefault(num, name)

    present = {
        num
        for name, text in sources.items()
        if "archive" not in name
        for line in text.splitlines()
        if _ROW_RE.match(line)
        for num in [_row_first_cell_def101(line)]
        if num is not None
    }
    top = max(present) if present else None

    for name, text in sources.items():
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in _RETAINED_START_RE.finditer(line):
                start = int(m.group(1))
                head = (
                    f"{name}:{lineno} 宣稱「自身全部條目（DEF-101-{start} 起）**完整**留在主檔」"
                )
                strays = sorted(n for n in archived if n >= start)
                if strays:
                    where = "、".join(f"DEF-101-{n}（在 {archived[n]}）" for n in strays)
                    problems.append(
                        f"{head}，但下列編號已被搬進 archive：{where}"
                        "——請訂正該宣稱，或確認那幾列是否被誤搬"
                    )
                if top is not None:
                    gone = sorted(
                        n for n in range(start, top + 1)
                        if n not in present and n not in archived
                    )
                    if gone:
                        problems.append(
                            f"{head}，但 [{start}, {top}] 之間下列編號**不在主檔、也不在任何 "
                            f"archive**：{gone}——該列疑似被整列刪除，請從 git 歷史找回或訂正宣稱"
                        )
    return problems


def _check_retained_range_claims() -> list[str]:
    """磁碟版薄包裝：讀主檔與全部 archive，委派 `retained_range_problems()`。"""
    ledger_text = _DEFECT_LOG.read_text(encoding="utf-8", errors="replace")
    sources = {_DEFECT_LOG.name: ledger_text}
    for arch in sorted(_DEFECT_LOG.parent.glob("AutoSDD_Defect_Log_archive_*.md")):
        sources[arch.name] = arch.read_text(encoding="utf-8", errors="replace")
    return retained_range_problems(ledger_text, sources)


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
    # R58 round 7 SA-R58R7-01：範圍端點宣稱獨立守門（訊息與索引問題分開印，免誤導）。
    range_problems = _check_retained_range_claims()
    if range_problems:
        # round 10 QA-R58R10-02：本表頭原寫「範圍端點過期」，而端點概念已於 round 9 移除
        # ⇒ 維護者照訊息會去找一個不存在的數字（守門訊息自證為假，同 ARCH-R58R4-01 形態）。
        print(f"❌ 帳本「自身全部條目…完整留在主檔」宣稱與實況不符（{len(range_problems)} 筆）：",
              file=sys.stderr)
        for problem in range_problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    # DEF-101-510：索引完整性與體積守門相互獨立——體積全綠不代表索引沒漏登。
    index_problems = _check_archive_index()
    if index_problems:
        print(f"❌ 帳本歸檔索引與磁碟不一致（{len(index_problems)} 筆）：", file=sys.stderr)
        for problem in index_problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    shape_problems = _check_row_shape()
    if shape_problems:
        print(f"❌ 帳本表格列欄數不正確（{len(shape_problems)} 筆）：", file=sys.stderr)
        for problem in shape_problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    ledger = _load_ledger_status()
    if not ledger:
        print("❌ 缺陷帳本解析結果為空 — 表格格式可能已改版導致比對邏輯失效，"
              "請同步本腳本的 _ROW_RE / 欄位解析", file=sys.stderr)
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

    # A 類與 D 類刻意都跑完才決定 exit code（不因 A 類先紅就 early return）：
    # 兩類問題來源不同、處置動作也不同（改文件狀態 vs 補帳本條目），一次全部吐出
    # 才不會讓人「修完 A 再 push 又被 D 攔一次」來回兩趟。
    reverse_problems = _check_reverse_refs()

    if all_problems:
        print(f"❌ 缺陷帳本跨文件狀態不一致（{len(all_problems)} 筆）：", file=sys.stderr)
        for p in all_problems:
            print(f"  - {p}", file=sys.stderr)
    if reverse_problems:
        print(f"❌ 引用了帳本查無的 DEF 編號（懸空引用 {len(reverse_problems)} 筆）：",
              file=sys.stderr)
        for p in reverse_problems:
            print(f"  - {p}", file=sys.stderr)
    if all_problems or reverse_problems:
        return 1

    vague_note = f"（另 {len(vague_ids)} 筆狀態含糊，見 warning）" if vague_ids else ""
    archive_count = len(list(_DEFECT_LOG.parent.glob(_ARCHIVE_GLOB)))
    print(f"✅ 缺陷帳本跨文件狀態一致：帳本 {len(ledger) - len(vague_ids)} 筆有效狀態紀錄"
          f"{vague_note}、{len(_CROSSREF_TARGETS)} 份掃描目標皆無矛盾、"
          f"歸檔索引與磁碟 {archive_count} 檔一致、"
          f"全 repo 引用的 DEF 編號皆可在帳本查得表格列")
    return 0


if __name__ == "__main__":
    sys.exit(main())
