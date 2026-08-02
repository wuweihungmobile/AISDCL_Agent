"""缺陷帳本的**歸檔索引**與**散文式結案宣稱**共用基元（R69 `DEF-101-734`／`DEF-101-735`）。

為何獨立成模組（而不是留在兩支工具裡各自長大）：
  · 索引 bullet 的樣式／解析／插入是 `archive_defect_log.py` 判準⑤ 與 `--apply` 自動註冊
    的**同一個**基元，本來就只該有一份。
  · 兩支工具都受 `AutoClaude/tools/check_loc_budget.py` 的 SPECIAL_FILES 行數棘輪管，且
    該棘輪在 R69 以「納管當下實際行數」設定＝**零餘裕**；把共用基元抽出來是該棘輪自己
    指定的第一順位處置（「先刪死碼／抽共用模組」，先例 `tools/lib/ci_liveness.py`），
    優於在帳本裡具名調高門檻。

本模組刻意**零 I/O、零全域狀態**：路徑由呼叫端傳入（測試沙箱 monkeypatch 的是呼叫端的
`_QUALITY_DIR`，基元若自己解析路徑就會繞過沙箱而寫穿 tracked 檔）。
"""

from __future__ import annotations

import re
from pathlib import Path

# --------------------------------------------------------------- 歸檔索引檔（DEF-101-734）
# 🔴 索引段自主檔外移的落點。
#
# WHY：索引 bullet 是**單調增長且永遠無法靠歸檔回收**的一段（每次 `--apply` 往主檔多寫
# 約 0.9KB，近幾輪每輪 3~5 支 archive ⇒ 每輪 3~5KB 只增不減），而主檔受 262,144 bytes
# 硬線（Read 工具單次讀取上限）管。把單調增長項放進有硬上限的檔＝數學上保證撞牆；
# R69 動工時主檔距硬線只剩 250 bytes 而 `--plan` 可搬 0 筆，即此結構的終局。
# 切分後主檔＝缺陷總表（live SSOT），本檔＝歸檔目錄與政策。
#
# 🔴 檔名刻意落在 `AutoSDD_Defect_Log_archive_*.md` glob 內：於是它**自動**屬帳本家族 ⇒
# 判準④⑥ 指針稽核、沙箱複製面、`check_defect_log_crossref.py` 的體積守門、兩支 compat-CI
# 的 `paths:` glob 全部零改動即涵蓋它。改名成不含 `archive_` 的形態會讓這四道守門同時漏掉
# 它——那正是 `DEF-101-587`「搬到另一支檔就繞過守門」的形狀。它本身**不是史料檔**
# （零表格列），故在判準⑤ 的「磁碟 archive 清單」中具名排除。
ARCHIVE_INDEX_NAME = "AutoSDD_Defect_Log_archive_INDEX.md"

# 判準⑤ — 歸檔索引 bullet：歸檔索引檔裡**以某支 archive 檔名為主體**的那一條。
# 樣式刻意只認「`> - ` ＋（可帶粗體的）反引號檔名」開頭：索引段的 bullet 一律長這樣，
# 而散文中順帶提到 `archive_NN` 的句子（例如「比照 archive_23 先例」）不會被誤收。
ARCHIVE_INDEX_BULLET_RE = re.compile(
    r"^>\s*-\s*\*{0,2}`(?P<file>AutoSDD_Defect_Log_archive_\d+\.md)`\*{0,2}"
)


def archive_index_doc(quality_dir: Path) -> Path:
    """歸檔索引檔路徑。路徑由呼叫端傳入（WHY 見模組 docstring 末段）。"""
    return quality_dir / ARCHIVE_INDEX_NAME


def index_bullet_lines(text: str) -> list[tuple[int, str]]:
    """回傳索引段的 `(0-based 行索引, archive 檔名)`，順序即檔內順序。

    判準⑤／`apply()` 自動註冊共用的唯一解析點（勿在別處重寫一份樣式）。
    """
    return [
        (i, m.group("file"))
        for i, line in enumerate(text.split("\n"))
        if (m := ARCHIVE_INDEX_BULLET_RE.match(line))
    ]


def insert_index_bullet(text: str, bullet: str) -> tuple[str, str | None]:
    """把 bullet 插在索引段**最後一條 bullet 之後**；回傳 `(新文字, 錯誤說明或 None)`。

    抓不到任何既有 bullet 就回錯誤而**不是**自己找地方塞：索引段的位置只能由既有
    bullet 認定（標題文字歷輪改過），猜錯地方會把一條索引寫進別的段落，讀者看不到、
    判準⑤ 卻因為「有這條 bullet」而放行 —— 那比不寫更糟。
    """
    bullets = index_bullet_lines(text)
    if not bullets:
        return text, (
            "索引檔查無任何歸檔索引 bullet（樣式 `> - **`AutoSDD_Defect_Log_archive_NN.md`**…`）"
            "——無法判定索引段位置，拒絕猜測插入點（猜錯會寫出一條讀者看不到、判準⑤ 卻放行"
            "的假索引）。請確認歸檔索引檔的索引段是否被改寫，並同步 ARCHIVE_INDEX_BULLET_RE"
        )
    lines = text.split("\n")
    lines.insert(bullets[-1][0] + 1, bullet)
    return "\n".join(lines), None


def prepare_index_insert(index_doc: Path, bullet: str) -> tuple[str | None, str | None]:
    """讀索引檔、插入 bullet、驗位元組守恆；回傳 `(新全文, 錯誤說明)`（二擇一為 None）。

    守恆式＝「新索引 == 舊索引 + bullet」：除了那一條 bullet 之外索引檔不得有任何改動。
    與主檔那側同型的**顯式**檢查，同樣不用 `assert`——`python -O` 會把 assert 整條編譯掉，
    而呼叫端下一步就是覆寫磁碟。
    """
    if not index_doc.exists():
        return None, (f"找不到歸檔索引檔 {index_doc}"
                      "（索引段自 R69 起外移，缺檔即無處登記 bullet）")
    orig = index_doc.read_bytes()
    text = orig.decode("utf-8-sig" if orig.startswith(b"\xef\xbb\xbf") else "utf-8")
    if "\r" in text:
        return None, f"{index_doc.name} 磁碟實體含 CR，請先正規化為 LF 再歸檔"
    new_text, problem = insert_index_bullet(text, bullet)
    if problem:
        return None, f"無法把索引 bullet 寫進 {index_doc.name}：{problem}"
    want = len(orig) + len(bullet.encode("utf-8")) + 1
    if len(new_text.encode("utf-8")) != want:
        return None, (f"{index_doc.name} 位元組不守恆："
                      f"{len(new_text.encode('utf-8'))} ≠ 原 {len(orig)} + bullet")
    return new_text, None


# --------------------------------------------------- 散文式結案宣稱（DEF-101-735）
#: 已結分類（與 `archive_defect_log.CLOSED_CLASSES` 同語意；`partial`／`workaround` 依
#: 帳本 `_STATUS_KEYWORDS` 歸類為 `open`，故不在此集合內——「只修一半」不是結案）。
CLOSED_CLASSES = frozenset({"fixed", "wontfix", "closed-by-decision"})
#: 「結案」前若緊接否定／情態字，整句是在說**沒有**結案，不是宣稱。
CLOSURE_CLAIM_RE = re.compile(r"(?<![不未待可難能該就否])結案")
#: 宣稱與 ID 之間的最大字元距離。刻意窄（同行、往前 30 字）：ADR 的表格列動輒數千字，
#: 放寬會把同一列裡不相干的歷史敘述綁到最後一個出現的 ID 上，製造誤紅。
CLOSURE_CLAIM_WINDOW = 30
_ID_RE = re.compile(r"DEF-\d+-\d+")


def closure_claim_problems(name: str, text: str,
                           status_of: dict[str, str | None]) -> list[str]:
    """散文寫「<DEF-ID> …結案」但帳本判為未結 ⇒ 互斥（純函式，可構造輸入測牙齒）。

    **為何需要這一道**（R69 終審 P2 #17 實證）：`ADR-XPLAT-002` §1 寫「`DEF-101-706`
    隨之結案」，而帳本該列狀態欄是 `partial`（明寫「解鎖條件①未達標故不結案」）。
    `check_defect_log_crossref._scan_target()` 的 `_CLAIM_RE` 只認「DEF-ID 緊接**括號**」
    這一種宣稱形態，而 ADR 的宣稱長在**散文**裡 ⇒ 即使把 ADR 納入掃描目標，那句話依然
    零訊號。**納入掃描面不等於看得見**——這一道補的正是這個差。

    **誠實劃界**：只認「結案」兩個字，不認「已修復／已解決／已完成」等近義詞。實測近義詞
    在本 repo 的活文件裡大量用於描述**動作**（「已修復並驗證」講的是某個修復動作，不是對
    缺陷列的狀態宣稱），擴進來即噪音淹沒訊號；而「結案」在本 repo 是帳本專用術語，語意
    單一。這與 `archive_defect_log` 對「現居」下硬要求、對「見」不下硬要求是同一個判準：
    **術語才可以被機械當成宣稱**。
    """
    problems: list[str] = []
    for lineno, line in enumerate(text.split("\n"), 1):
        for m in CLOSURE_CLAIM_RE.finditer(line):
            ids = _ID_RE.findall(line[max(0, m.start() - CLOSURE_CLAIM_WINDOW):m.start()])
            if not ids or status_of.get(ids[-1]) in CLOSED_CLASSES:
                continue
            actual = status_of.get(ids[-1]) or "帳本查無此 ID"
            problems.append(
                f"{name}:{lineno}：散文宣稱「{ids[-1]} …結案」，但帳本判為 {actual!r} — "
                f"兩份活文件對同一個 ID 各說各話。**一律以帳本為準**：若確實未結，請改寫該句"
                f"（例如「…的收斂標的由本文件落地，但該筆不結案，理由 X」）；若帳本才是過期"
                f"的，請先改帳本狀態欄再回來改這句"
            )
    return problems


def oversize_problems(paths: list[Path], warn_bytes: int,
                      fail_bytes: int) -> tuple[list[str], list[str]]:
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
        if n >= fail_bytes:
            fails.append(
                f"{p.name} {n} bytes ≥ 上限 {fail_bytes}（Read 工具單次讀取上限）"
                f"——複審者將無法一次讀完本檔。請比照 DEF-101-587 的做法拆分："
                f"原檔留在原地當**入口**（帳本有多處指向它，改名會讓那些指針全部失實），"
                f"新增姊妹檔承載較新的節，並在入口檔開頭維護「哪些 DEF-ID 在哪一份檔」對照表"
            )
        elif n >= warn_bytes:
            warns.append(
                f"{p.name} {n} bytes 已逼近上限 {fail_bytes}"
                f"（距 {fail_bytes - n} bytes），請規劃拆分——"
                f"append 前務必先 `wc -c`"
            )
    return fails, warns
