"""缺陷帳本的**歸檔索引**、**散文式結案宣稱**、**未結存量**與**狀態欄語意判準**共用基元
（R69 `DEF-101-734`／`DEF-101-735`；R74 新增未結存量量測入口與「改派／回執」判準本體；
R76 自 `archive_defect_log.py` 外移搬遷判準② 的活躍字樣判讀，並新增搬遷子集選取
`select_move_subset()` 與未結存量預警帶 `unresolved_advisory_notes()`）。

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
#: markdown 行內 code span。反引號內是**逐字引述**，不算新的宣稱。
#: 🔴 這是全 repo 唯一一份：`check_defect_log_crossref._CODE_SPAN_RE` 與
#: `archive_defect_log._CODE_SPAN_RE` 都是本物件的**再匯出**（後者以 `assertIs` 鎖住）。
#: R74 從閘門移到本模組，是因為 `reassign_hit()` 也需要同一條判準——判準寫第二份正是
#: 本 repo 反覆在治的複本型缺陷，而依賴方向只能是 lib ← 工具（反向會是循環 import）。
CODE_SPAN_RE = re.compile(r"`[^`]*`")
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


# ------------------------------------ 硬規則② 的「改派／回執」出口判準（R74 PKG-2）
#: 硬規則② 的兩個合法出口 token（`orphan_backlog_problems()`／`lagging_clock_notes()` 消費）。
REASSIGN_RE = re.compile(r"改派|回執")
#: 否定形態：`無回執`／`沒有回執`／`零改派`／`未改派`／`非改派` —— 字面帶 token 而語意
#: **相反**。允許否定詞與 token 間夾少量虛詞（`沒有`／`未任何`），故不是單字元 lookbehind：
#: 那一版實測放行 `沒有回執`（緊接 token 的是「有」而不是否定詞）。
_REASSIGN_NEGATED_RE = re.compile(r"[無零未沒非不][有任何完全]{0,2}\s*(?:改派|回執)")


def reassign_hit(status_cell: str) -> bool:
    """該**狀態欄**是否真的載明「改派／回執」——硬規則② 合法出口的判準本體（R74）。

    🔴 立此函式的原因（R74 逐形態實測，判準原為對**整列**做裸關鍵字比對）：五種形態都能
    白拿豁免，其中**兩種不在**當時的誠實劃界清單內，於是它們既有效又不被承認：
      · **跨欄**：token 落在「發現情境」「現象與證據」「分流去向」任一欄都算數。而合法
        出口的體例是閘門自己的錯誤訊息逐字指定的——「就地於**狀態欄**追加一筆載明
        「改派」的附記」。於是一列只要在證據欄敘述**別人的**改派，就替自己買到了豁免。
        本函式改為只判狀態欄，判定面與體例對齊。
      · **引述**：反引號內是逐字引述（帳本體例；`status_variant_problems()` 的錯誤訊息
        逐字指路「若只是逐字引述舊寫法，請用反引號包住」）。引述一句舊的改派紀錄，
        不是做出一次新的改派。本函式先以 `CODE_SPAN_RE` 遮掉再判。
      · **否定語意**（原已具名為 known-gap，本函式一併收掉）：判定成本只有一個前綴字元
        集合，而它擋掉的是「字面在、語意相反」這種最容易誤讀的形態。

    ⚠️ **誠實劃界**（不做「唯一殘餘風險是 X」這類宣稱）：
      · **跨列**：本函式只看被傳入的那一欄；「哪一列算更新的紀錄、要不要接受它的改派」
        由呼叫端決定（呼叫端仍另行要求該列提及本列 ID）。
      · **散文式改派**（不含這兩個 token，例如「另找人接」）本函式無從辨識。
      · 角引號 `「改派」` 這種**術語提及**不遮罩：它與真宣稱在狀態欄裡難以區分，且遮罩它
        會讓「改派為：未指派」這類正當寫法在有人順手加引號時失效——寧可多算一次豁免，
        也不要把合法出口關掉（方向與 `_HANDOVER_ROUND_RES` 的「寧可漏抓不製造假紅」一致）。
    """
    bare = CODE_SPAN_RE.sub(" ", status_cell)
    return bool(REASSIGN_RE.search(_REASSIGN_NEGATED_RE.sub(" ", bare)))


# --------------------------- 搬遷判準② 的狀態欄活躍字樣判讀（R76 自 archive_defect_log 外移）
# 🔴 為何住這裡而不是留在工具內：本模組已經是「狀態欄語意判準」的家（`reassign_hit()`
# 就在上面，且它與本判準用的是**同一條** `CODE_SPAN_RE` 遮罩基元）。外移的直接觸發因是
# `tools/archive_defect_log.py` 的 raw-line 棘輪餘裕為 0，而該棘輪自己指定的第一順位處置
# 就是「先刪死碼／抽共用模組」（見 `check_loc_budget._ROOT_TOOLS_RATCHET_REASON`）——
# 不是調高門檻。工具側以**再匯出**消費本節，不留第二份實作。
#
#: token 邊界字元集與 gate `_FIRST_WORD_RE`（`[A-Za-z][A-Za-z0-9_-]*`，故
#: `closed-by-decision` 整體是一個詞）**對齊**：`OpenMutexW`／`reopened` 不誤命中
#: （G-refuter-4），`fail-open` 這類設計術語亦然（R74，WHY 見 `active_status_hit()`）。
ACTIVE_STATUS_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:open|routed|deferred|watch)(?![A-Za-z0-9_-])|workaround"
)
#: 角引號引述。與 `CODE_SPAN_RE` 同屬「看得見的刻意標記」，故用同一種遮罩方式。
CORNER_QUOTE_RE = re.compile(r"「[^「」]*」|『[^『』]*』")

#: 第三種「看得見的刻意標記」（R76）：**訂正首詞、原文逐字接於後**的帳本慣用語。
#: 語意＝從該標記之後到下一個 `｜` 分隔（或欄尾）為止，整段是**被推翻的舊狀態逐字引述**，
#: 不是本列現況。三種實際形態（逐字取自主檔，皆命中本樣式）：
#:   · `🔴 R75 訂正首詞（原文逐字接於後）：`
#:   · `🔴 R75 訂正首詞（原文接於後，含原解鎖條件）：`
#:   · `🔴 R60 round 2 補《格式定義》合法首詞（原首詞非合法值，原文完整接於後）：`
#:
#: 🔴 立此遮罩的理由（DEF-101-676 的同型復發，R76 實測）：判準② 對這一整族慣用語誤命中，
#: 把一批**現況已結**的列永久釘死在主檔——它們的首詞已被訂正為合法已結值（判準① 因此
#: 放行），命中的字樣全部落在「本列自己被推翻的舊狀態」那段引文裡，語意剛好與判定相反。
#: 這與 R68 收窄反引號／角引號是同一個病的第三種逸出面（`DEF-101-676` docstring 第②類）。
#:
#: 🔴 邊界刻意停在 `｜` 而**不是**吃到欄尾：帳本體例是「引文之後再以 `｜🔴 …` 追加新註記」
#: （實例：`｜🔴 **R75 複驗（類別 A）**：…`）。吃到欄尾會把那段**現況**敘述一起遮掉，
#: 等於用一句舊引文替整欄買到豁免——那才是真正會讓未結列漏搬的方向。
#:
#: ⚠️ 誠實劃界：樣式要求「首詞」＋「原文…接於後」同時出現，故只認這一族**具名慣用語**。
#: 其他形態的舊狀態引述（例：只寫「原記 open，現已…」而不帶括號註記）本遮罩抓不到，
#: 它們仍會被判準② 擋下＝**保守方向**（多攔不誤放），要放行請改寫成上列慣用語。
VERBATIM_QUOTE_TAIL_RE = re.compile(r"首詞（[^（）]*原文[^（）]*接於後[^（）]*）：")
#: 引文段的結束標記（帳本體例的欄內註記分隔符；欄分隔用的半形 `|` 在帳本列內禁用）。
VERBATIM_QUOTE_STOP = "｜"


def verbatim_quote_spans(status_cell: str) -> list[tuple[int, int]]:
    """回傳「訂正首詞（原文…接於後）：」引文段的 `(起, 迄)` 區間（純函式，可構造輸入驗）。

    起點＝標記本身之後（標記文字自己不含活躍字樣，遮不遮都一樣，留著便於報告引用）；
    迄點＝其後第一個 `｜`，沒有就到欄尾。
    """
    spans: list[tuple[int, int]] = []
    for m in VERBATIM_QUOTE_TAIL_RE.finditer(status_cell):
        stop = status_cell.find(VERBATIM_QUOTE_STOP, m.end())
        spans.append((m.end(), len(status_cell) if stop < 0 else stop))
    return spans


def active_status_hit(status_cell: str) -> re.Match[str] | None:
    """判準② 的實際判讀入口：**排除三種看得見的刻意標記之後**再找活躍字樣。

    🔴 為何非收窄不可（DEF-101-676，R68 立、R76 補第三種）——判準② 原本是對整個狀態欄
    做裸掃描，於是把下列**與本列現況無關**的字元一律當成「本列還活著」
    （項數不寫死：清單會長，寫死就是下一個 stale 站點）：

      · **程式碼片段裡的 Python 內建函式 `open`**。實例 `DEF-101-391`：狀態欄寫
        `` fixed@R48：`python3 -c "import yaml; yaml.safe_load(open('...yml'))"` ``——
        命中的 `open` 是 `open()` 呼叫；與 ASCII 邊界那一版的 `OpenMutexW` 誤報同型。
      · **引述本列自己被推翻的舊狀態**。實例 `DEF-101-554`：`` 本欄原文為「`open`（待
        主控還原）」… ``。這些字面出現的用途正是**宣告它已不成立**。
      · **在講別的 DEF-ID**（`DEF-101-541`／`564`／`565` 的 `routed`）。
      · **以 `-`／`_` 黏成複合 token 的設計術語**（R74 的 `fail-open`）——那一類靠邊界
        字元集對齊 gate `_FIRST_WORD_RE` 解決，**不是**靠遮罩。
      · **「訂正首詞（原文逐字接於後）」之後的整段舊狀態引文**（R76 新增，見
        `VERBATIM_QUOTE_TAIL_RE`）。這一類的規模最大，且會**永久**釘住已結列。

    後果不是「多攔幾筆」而是**結構性死結**：被擋的全是 `_classify` 已判已結、只被判準②
    一項擋住的列，它們合計佔主檔可觀比例卻搬不動 ⇒ 輪替吞吐趨近零、主檔單調逼近硬線。
    實數一律以 `archive_defect_log.py --plan` 現跑為準（此處不寫死，寫死即 stale 站點）。

    🔴 **鑑別力不得因此流失**，四道保留：
      (a) 裸散文裡的活躍字樣照樣命中（未加標記者一律算數）；
      (b) 判準① 仍先要求狀態欄**首詞**分類為已結，本判準只是第二層；
      (c) 判準④（`HANDOFF_PROSE_RE`）掃的是**整列**且不套任何遮罩——真正的活交棒仍會被
          攔下要求 `--ack-handoff` 具名承認；
      (d) 第三種遮罩停在 `｜`，引文之後的**現況**敘述不受遮蔽（見該常數上方）。
    對應機械鎖：`tools/tests/test_archive_defect_log.py::TestCriterion2Narrowing`。
    """
    masked = list(status_cell)
    spans = [(m.start(), m.end()) for pattern in (CODE_SPAN_RE, CORNER_QUOTE_RE)
             for m in pattern.finditer(status_cell)]
    for start, end in spans + verbatim_quote_spans(status_cell):
        # 以空白**等長**置換（保住 offset 與長度，便於報告引用原字串位置）
        for i in range(start, end):
            masked[i] = " "
    return ACTIVE_STATUS_RE.search("".join(masked))


def select_move_subset(
        movable: list[dict], only: frozenset[str],
        keep: frozenset[str]) -> tuple[list[dict], list[dict], list[str]]:
    """從**已通過全部搬遷判準**的清單裡挑子集；回傳 `(選中, 排除, 問題)`（DEF-101-811）。

    🔴 立此入口的理由：`--apply` 原本是全有全無，唯一的「不要搬這一筆」入口是判準④ 的
    `--ack-handoff`（那是**加入**用的，方向相反）⇒ 每輪都得先讓工具把本輪列一起搬走、
    再手工把它們還原回主檔。手工還原一份剛被就地覆寫的帳本，正是本工具立帳要消滅的動作。

    🔴 **為何這不是繞過保全稽核的後門**（設計約束，三條同時成立）：
      (a) 本函式**只在六項搬遷判準全部跑完之後**對結果做集合運算，且只會讓搬遷集合**變小**
          ——它在結構上不可能讓一筆被擋下的列變成可搬（由鎖以「把被擋 ID 餵進 `--only`」
          反向驗證）。安全包絡單調收縮，不擴張。
      (b) 排除是**具名**的：ID 打錯一個字就整批 fail-loud（下方 `unknown`），不會靜默
          少搬一筆。這比照判準④ `--ack-handoff` 的既有體例——差別只在方向。
      (c) 排除**留痕**：呼叫端把 `excluded` 寫進 archive 標頭與歸檔索引 bullet，且
          `--plan` 每次執行都列印。被排除的列仍留在主檔 ⇒ 下一次 `--plan` 照樣把它報成
          可搬，`--check` 的指針／欄數／跨檔判準也照樣看得到它。**沒有任何東西被藏起來。**
    """
    ids = {v["id"] for v in movable}
    unknown = sorted((set(only) | set(keep)) - ids)
    if unknown:
        return movable, [], [
            f"--only／--keep 指名了不在可搬清單內的 ID：{unknown}。可能是打錯字、或該列"
            "本來就被某項判準擋著（`--plan` 會逐筆說明理由）。拒絕靜默忽略：忽略等於"
            "「以為排除了、實際照搬」或「以為指定了、實際全搬」，兩個方向都是無聲的錯"
        ]
    chosen = [v for v in movable
              if (not only or v["id"] in only) and v["id"] not in keep]
    picked = {v["id"] for v in chosen}
    return chosen, [v for v in movable if v["id"] not in picked], []


# ----------------------------------------- 未結存量的唯一量測入口與列數棘輪（R74 PKG-2）
#: 未結案＝仍需要有人接手。`routed` 涵蓋帳本慣用的 `routed（deferred@Rnn）` 寫法；
#: `None`（狀態欄辨識不出關鍵字）一併納入——「看不出結案」不等於「已結案」。
#: 🔴 全 repo 唯一一份：`check_defect_log_crossref._UNRESOLVED_CLASSES` 是本物件的再匯出。
UNRESOLVED_CLASSES: frozenset[str | None] = frozenset({"open", "routed", None})

#: 未結存量（**列數**）的 warn／fail 線 —— R74 新增；在此之前這個量**零機械上限**。
#:
#: 🔴 為何非有不可（R74 動工時的實測形狀）：主檔 bytes 有 warn／fail 線，未結列數什麼都
#: 沒有。而未結列在結構上**不可被歸檔**（`archive_defect_log` 判準① 硬擋已結才准搬），
#: 所以它們是主檔體積的**不可壓縮地板**：一旦「未結列 bytes」逼近 bytes 硬線，就算把
#: 所有已結列搬空也降不下來 ⇒ 「逼近上限唯一出路是歸檔、歸檔又被未結狀態卡住」的死結。
#: R74 動工時量到的正是這個形狀：主檔 248,048 bytes／113 列，其中未結 **93** 列＝
#: **198,271 bytes ＝硬線（262,144）的 75.6%**，而 `--plan` 實算可搬 **0** 筆。
#:
#: 🔴 門檻怎麼算出來的（可重算，不是憑感覺）——把死結條件寫成 bytes 再換回列數：
#:   · 未結列平均 **2,131 bytes**（198,271 ÷ 93，R74 實測）。
#:   · **fail**：未結列 bytes ≥ 硬線 80%（209,715）⇒ 已結列全數搬空後主檔僅剩 20%
#:     （≈52KB ≈ 24 列）餘裕，輪替吞吐結構性見底。209,715 ÷ 2,131 ≈ **98 列**。
#:   · **warn**：≥ 硬線 70%（183,500）⇒ 183,500 ÷ 2,131 ≈ **86 列**。
#:
#: 🔴 **R75 訂正這一段的實測基線（`DEF-101-792` 的同型復發，落在本註解自己身上）**。
#: 本段原先寫的「R74 收輪實測」是一組**中間態**數字——量的是「歸檔已搬出、本輪帳目還沒
#: 寫進去」那個瞬間，而不是 commit `a371068` 的狀態。成因與 R74 commit 訊息裡那組數字同源
#: （同一個中間態被當成收輪值抄了兩處），而它差在**會讓人放心的方向**：照那組數字讀，本鎖
#: 距 fail 還有兩位數的餘裕；`a371068` 的真實狀態是**距 fail 只剩 1 筆**。這正是本模組
#: `report_unresolved()` 存在的理由（唯一量測入口），偏偏它自己的註解沒有走那個入口。
#: R75 收斂後於工作樹實測（指令＝`python tools/check_defect_log_crossref.py
#: --unresolved-count` ＋ `(Get-Item <帳本>).Length`）：
#:   · 主檔 **247,135 bytes／109 列**，其中未結 **81 列／152,287 bytes ＝硬線的 58.1%**，
#:     未結列平均 **1,880 bytes**；距 bytes 硬線餘裕 15,009 ⇒ 按現行均值約可再吃 7~8 列。
#:   · 未結列數 81 **低於 warn 線 86**（R74 收輪是 97、距 fail 僅 1 筆）——死結是靠逐筆回樹
#:     複驗後結案（16 筆）解開的，不是靠調門檻。
#: 🔴 **均值下降但門檻刻意不動**：以 1,880 重算上面那組算式會得到 warn≈97／fail≈111，
#: **比現行的 86／98 寬**。不採用——調寬就是砸溫度計，方向與本棘輪「只准往小走」相反。
#: 這條註解本身就是「量測基線住在註解裡、沒有任何鎖看守」的實例；未接上機械物的誠實劃界
#: 見下方 `UNRESOLVED_ROWS_WARN` 的 R75 附註。
#: 判準面刻意是**列數**而不是 bytes：bytes 已有守門，且它會被歸檔動作攪動，於是「靠歸檔
#: 把數字壓下去」可以掩蓋未結存量持續累積；列數不受歸檔影響，問的正是「還有幾筆缺陷
#: 沒人處理」。平均列大小若大幅改變，請連同上面的算式一起重算再改門檻——**不得**因為
#: 撞線就往上調（同 `_LEDGER_FAIL_BYTES` 的「不得砸溫度計」紀律）。
#: 🔴 **R75 附註：這種「住在註解裡的實測基線」能不能納入機械物？——半可以，本輪只做得到一半。**
#: · **做不到的那半（誠實劃界）**：把上方數字綁成「與 `--unresolved-count` 現值相等」的斷言
#:   會**每輪合法轉紅**（存量本來就會動），而永紅的鎖會被整個關掉——比沒有鎖更糟（同
#:   `ARCH-R59-NB4` 判例）。所以「註解裡的數字自動保鮮」這條路在這裡是死路，不是還沒做。
#: · **做得到的那半**：把上方數字的角色**降格**成「門檻推導的輸入（附量測日期與指令）」，
#:   而「現況是多少」一律只從 `report_unresolved()` 這個唯一入口取——本輪已照此改寫，
#:   於是註解不再有「現況宣稱」可過期。剩下的機械化是**禁止再把現況宣稱寫回本檔註解**
#:   （形態：掃本檔註解不得出現「收輪實測」這類 live 宣稱）。
#: · **本輪未落地該掃描器的理由（非「不值得做」）**：`tools/tests/` 檔數是 shrink-only 棘輪
#:   ⇒ 不得新增 .py，須併入既有檔；而唯一合適的宿主 `test_doc_loc_baseline_freshness_r60.py`
#:   本輪由另一個 agent 持有，併改會撞編輯衝突。已列入 R75 交棒。
UNRESOLVED_ROWS_WARN = 86
UNRESOLVED_ROWS_FAIL = 98


def unresolved_ids(ledger: dict[str, str | None]) -> list[str]:
    """未結存量的**唯一**量測入口：回傳未結列的 ID（已排序）。

    🔴 為何要有「唯一入口」（R74 診斷實測）：同一個問題「未結存量是多少」當時有三個互斥
    答案，而工作樹與上一輪收輪 commit 完全相同 ⇒ 差異全部出自**量測法不一致**，不是資料
    變動。三條臨時路徑各自回答的其實是不同問題：
      (a) 輪次報告裡人工數出來的數字——沒有可重跑的載具，無從複驗；
      (b) `archive_defect_log.py --plan` 的「不可搬」筆數——那是**六項搬遷判準的聯集**
          （含指針反向依賴、欄數、交棒散文），一筆已結列也可能不可搬，與「未結」不同義；
      (c) 逐列 `_classify()` ∈ `UNRESOLVED_CLASSES`——**這一個才是未結列數**。
    本函式即 (c)，並由 `check_defect_log_crossref.py --unresolved-count` 對外暴露成一條
    可重現指令，於是「未結存量」從此只有一個答案，且任何人都能自己跑出來。
    """
    return sorted(i for i, c in ledger.items() if c in UNRESOLVED_CLASSES)


def unresolved_ceiling_problems(
        ledger: dict[str, str | None]) -> tuple[list[str], list[str]]:
    """未結列數的 warn／fail 線；回傳 `(fail 訊息, warn 訊息)`（純函式，可構造輸入驗牙）。

    門檻與其算式見 `UNRESOLVED_ROWS_WARN`／`UNRESOLVED_ROWS_FAIL` 上方。
    """
    n = len(unresolved_ids(ledger))
    common = (
        f"未結列 {n} 筆（量測入口＝`check_defect_log_crossref.py --unresolved-count`；"
        f"未結列在結構上不可歸檔 ⇒ 它們是主檔體積的不可壓縮地板）"
    )
    if n >= UNRESOLVED_ROWS_FAIL:
        return [
            f"{common} ≥ fail 線 {UNRESOLVED_ROWS_FAIL}。🔴 **不要調高本門檻**"
            f"（那是砸溫度計）：正解是把未結列真的結掉或指派出去。到這個點時，"
            f"即使把全部已結列搬進 archive，主檔也只剩約 20% 餘裕 ⇒ 歸檔已買不到"
            f"可用空間，帳本進入「唯一出路是歸檔、歸檔又被未結狀態卡住」的死結。"
            f"門檻的推導算式見 tools/lib/defect_ledger_index.py 該常數上方"
        ], []
    if n >= UNRESOLVED_ROWS_WARN:
        return [], [
            f"{common} 已逼近 fail 線 {UNRESOLVED_ROWS_FAIL}（距 "
            f"{UNRESOLVED_ROWS_FAIL - n} 筆）。請在本輪就結掉／指派掉幾筆，"
            f"不要等撞線——撞線時能做的事跟現在一樣多，只是選擇更少"
        ]
    return [], []


#: warn 線**之下**的預警帶寬度（列）。R76 新增，**不動** warn/fail 兩線。
#:
#: 🔴 為何 warn 線之外還需要這一帶（R76 實測形狀）：bytes 那條線撞到時有洩壓閥——歸檔。
#: 未結列數這條**結構上沒有**：未結列不可搬（判準① 硬擋），所以歸檔一筆都降不下來。
#: 而歸檔動作會讓 bytes 大幅下降 ⇒ 剛跑完歸檔的人看到的訊號是「餘裕變多了」，方向正好
#: 與真正會破的那道閘門相反。本帶的唯一工作就是在那個時刻把這句話講出來：
#: **歸檔不會降低此數，唯一出路是把列真的結掉。**
#:
#: 20 列的來源（可重算，不是憑感覺）：近幾輪每輪淨增未結列在個位數，20 列≈2~3 輪的
#: 前置量——夠一輪把列真的結掉，而不是撞線當下才發現只剩「調門檻或不 push」兩個選項。
#: 🔴 這是**收緊**（多一個更早的非阻斷訊號），不是放寬：warn=86／fail=98 兩個常數與
#: `unresolved_ceiling_problems()` 的 rc 語意完全未動。**不得**以「太吵」為由調大本值。
UNRESOLVED_ROWS_ADVISORY_MARGIN = 20


def unresolved_advisory_notes(ledger: dict[str, str | None]) -> list[str]:
    """warn 線之下、距 fail 線 ≤ `UNRESOLVED_ROWS_ADVISORY_MARGIN` 的**非阻斷**預警。

    刻意與 `unresolved_ceiling_problems()` 分成兩支函式而不是塞進它的 warn 清單：
    後者的 `(fails, warns)` 契約有消費端與鎖在釘（`check_defect_log_crossref.py` 與
    `test_check_defect_log_crossref.py::test_ceiling_is_a_ratchet_with_both_bands`
    逐字驗「warn−1 列時兩邊皆空」），把新訊號塞進去會讓那道鎖**合法轉紅**——而它守的
    是門檻語意，不該為了加一條提示就被改動。純函式，可構造輸入驗牙。

    n ≥ warn 時回空：那一帶已由 `unresolved_ceiling_problems()` 出聲，同一件事報兩次
    只會讓兩個訊號一起被忽略。
    """
    n = len(unresolved_ids(ledger))
    if n >= UNRESOLVED_ROWS_WARN or UNRESOLVED_ROWS_FAIL - n > UNRESOLVED_ROWS_ADVISORY_MARGIN:
        return []
    return [
        f"未結列 {n} 筆，距 fail 線 {UNRESOLVED_ROWS_FAIL} 只剩 "
        f"{UNRESOLVED_ROWS_FAIL - n} 筆（warn 線 {UNRESOLVED_ROWS_WARN}）。"
        f"🔴 **歸檔不會降低此數，唯一出路是把列真的結掉**（或改派給具名承接者）："
        f"未結列在結構上不可搬（搬遷判準① 硬擋），所以 bytes 那條線的洩壓閥對這一條"
        f"完全無效——剛跑完歸檔看到「主檔變小了」時，這個數字一筆都沒動。"
        f"量測入口＝`check_defect_log_crossref.py --unresolved-count`"
    ]


def report_unresolved(ledger: dict[str, str | None]) -> int:
    """`--unresolved-count` 的輸出本體：印出未結列數、門檻與逐筆 ID，回 rc。

    刻意連 ID 一起印：只印一個數字的載具無法被複驗（下一個人只能相信它），而本函式存在
    的理由正是「同一個量有三個互斥答案」。
    """
    ids = unresolved_ids(ledger)
    fails, warns = unresolved_ceiling_problems(ledger)
    print(f"未結列數＝{len(ids)}／全部 {len(ledger)} 列"
          f"｜warn={UNRESOLVED_ROWS_WARN} fail={UNRESOLVED_ROWS_FAIL}")
    print(f"判準＝狀態欄 _classify() ∈ {sorted(str(c) for c in UNRESOLVED_CLASSES)}")
    print("未結列 ID：" + "、".join(ids))
    for w in warns + unresolved_advisory_notes(ledger):
        print(f"⚠️  {w}")
    for f in fails:
        print(f"❌ {f}")
    return 1 if fails else 0


# --------------------------------------- 帳本逐列位元組上限（R79，`DEF-101-890`）
#: 單列上限（UTF-8 bytes）。這條政策自 R76 起被連續三份交棒書寫進「禁止事項」，而 R79
#: 開場實測**全 repo 零機械物**：120 列有 110 列違反、平均 2,089 bytes，主檔因此被推到
#: 距 pre-push 硬閘僅 5,224 bytes（≈2 列）。「政策在、觀測者不在」正是本 repo 反覆診斷
#: 出的頭號缺陷形態，只是這一次連鎖都沒有，而代價是整條 push 通道。
#: 🔴 本值**不重新談**：700 是 R75 訂立、R76~R78 逐字沿用的既有政策，本輪只替它裝上
#: 量測者。判準的意圖是「帳本列是**索引**不是報告」——詳情寫進 `_GOVERNANCE_DOCS` 那
#: 一族具名證據檔（它們自己受 256KB 體積守門），列上只留一句話與檔名指針。
#:
#: 🔴 同一包同時改了消費端的**收斂位置**（`check_defect_log_crossref._CHECK_ORDER`）：
#: 「缺陷帳本主檔體積」原本是 `main()` 的**第二道早退**，一超線就 `return _bail(...)`，
#: 其後十來道（跨文件一致、孤兒承接、未結存量、逐列位元組…）一行都不跑，而讀者拿到的
#: 畫面只是「輸出變短」——診斷與閘門在同一時刻一起消失，方向正是「看起來變乾淨」。
#: 現改為累積到最後一道一起收斂：rc 語意完全不變（超線照樣 1），但體積紅的當回合其餘
#: 判準照跑完。逐列位元組上限同屬「帳本體積」語意，故共用同一個名目、不另立第二種機制。
#: 回歸鎖＝`TestR79RowByteCeiling::test_the_volume_check_no_longer_masks_the_later_checks`。
ROW_MAX_BYTES = 700

#: 表格列的 ID 抽取（與 `check_defect_log_crossref._ROW_RE` 同形，多一個捕獲群）。
_ROW_ID_RE = re.compile(r"^\|\s*(DEF-\d+-\d+)\s*\|")


def row_bytes(ledger_text: str) -> dict[str, int]:
    """主檔逐列的 UTF-8 位元組數（鍵＝DEF-ID）。純函式，可構造輸入驗牙。"""
    out: dict[str, int] = {}
    for line in ledger_text.split("\n"):
        m = _ROW_ID_RE.match(line)
        if m:
            out[m.group(1)] = len(line.encode("utf-8"))
    return out


#: 存量豁免（**具名**，不是計數）：R79 落地當下**仍**超過 `ROW_MAX_BYTES` 的列。
#: 具名而非計數，是因為本鎖的核心設計要求就是「分得開新列與既有列」：
#:   · 超標而**不在**本清單 ⇒ 紅（新列，或既有列被改寫到超標）。
#:   · 在本清單而**已不超標**（或該 ID 已不在主檔）⇒ 紅，要求把它從清單刪掉。
#:     缺這一向，清單會退化成永久額度（判例同 `stale_grandfather_problems()`）。
#: 🔴 一次全紅不是選項：這 105 列是歷史事實，硬擋會讓本鎖上線即永紅，而永紅的鎖會被
#: 整個關掉，比沒有鎖更糟（ARCH-R59-NB4 判例）。
#: 取值紀律同 `_FROZEN_GUARD_LINES`：**當回合實測直接填入、零加減推算、不留成長緩衝**。
#: 🔴 R82 帳本清債包一次移出 **13 筆**（98 → 85）：`DEF-101-055`／`214`／`217`／`296`／
#: `308`／`309`／`313`／`333`／`335`／`348`／`400`／`401`／`412` 全數**結案並瘦身成索引**
#: （逐列 −294 ~ −2896 bytes，原文逐字保全於 `CrossPlatform_R82_Ledger_Closure.md` §8），
#: 瘦身後皆 ≤700 bytes ⇒ 依②向訊息**自己指名**的動作移除，不是放寬。
OVERSIZE_ROW_GRANDFATHERED: frozenset[str] = frozenset("""
DEF-01-009 DEF-100-002 DEF-101-018
DEF-101-060 DEF-101-068 DEF-101-200 DEF-101-205
DEF-101-233 DEF-101-235 DEF-101-238 DEF-101-242
DEF-101-243 DEF-101-263 DEF-101-268 DEF-101-271
DEF-101-278 DEF-101-297
DEF-101-324 DEF-101-336
DEF-101-338 DEF-101-351 DEF-101-377
DEF-101-388 DEF-101-392 DEF-101-398 DEF-101-399
DEF-101-402 DEF-101-415 DEF-101-418
DEF-101-435 DEF-101-470 DEF-101-500 DEF-101-518
DEF-101-550 DEF-101-557 DEF-101-559 DEF-101-560 DEF-101-561
DEF-101-565 DEF-101-596 DEF-101-610 DEF-101-649
DEF-101-675 DEF-101-676 DEF-101-693 DEF-101-701
DEF-101-702 DEF-101-703 DEF-101-726 DEF-101-733
DEF-101-736 DEF-101-739 DEF-101-740 DEF-101-746 DEF-101-747
DEF-101-748 DEF-101-752 DEF-101-755 DEF-101-758 DEF-101-764
DEF-101-769 DEF-101-790 DEF-101-792 DEF-101-794 DEF-101-795
DEF-101-796 DEF-101-797 DEF-101-798 DEF-101-801 DEF-101-802
DEF-101-803 DEF-101-810 DEF-101-856 DEF-101-866 DEF-101-867
DEF-101-870 DEF-101-871 DEF-101-872 DEF-101-876 DEF-101-878
DEF-101-880 DEF-101-886 DEF-101-887 DEF-101-888 DEF-101-889
""".split())

#: 具名清單的**筆數**上限（形狀照抄 `check_defect_log_crossref._UNPINNED_HANDOVER_CEILING`）。
#: 上面兩向擋得住「悄悄膨脹」與「清單過時」，擋不住「膨脹了就順手把 ID 補進清單」——
#: 本常數是那條縫的塞子。**只准往下改**；要往上調必須在缺陷帳本具名理由。
#: 🔴 R80 收尾單人窗口重釘 **105 → 101**（往下改）：`DEF-101-358`／`628`／`680`／`714`
#: 四筆已於本輪開場搬進 `archive_63`，主檔實測查無此 ID ⇒ 豁免過期，留著就是日後無聲
#: 加回去的額度。四筆一併自上方清單移除，本值同步下修為當回合實測筆數。
#: 🔴 本輪開場重釘 **101 → 98**（往下改）：`DEF-01-007`／`DEF-101-274`／`DEF-101-422`
#: 三筆隨本輪開場的 `archive_64`（35 列已結列洩壓）移出主檔，主檔實測查無此 ID ⇒ 豁免
#: 過期。移除＋同步下修正是判準第②向訊息**自己指名**的動作，不是放寬。這裡的錯誤動作
#: **不是**「把 ID 補進清單」（②向恰恰是因為它還在清單裡才紅），而是「留著不刪」或「把
#: 上限往上調」——兩者都是日後無聲加回去的額度。本值＝當回合實測超標列數，零加減推算。
#: 🔴 輪號刻意不寫進本段散文，錨改用磁碟上查得到的 `archive_64`（處置同
#: `check_defect_log_crossref._UNPINNED_HANDOVER_CEILING` 上方那段的既有先例）：程式碼檔
#: 的輪號標籤受 `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 管，不得超前帳本
#: 「發現情境」欄推得的當前輪，而帳本時鐘在本輪第一列落地前仍停在上一輪——本次寫上輪號
#: 即實測當場轉紅。請勿「順手補回輪號」。
#: 🔴 R82 帳本清債包重釘 **98 → 85**（往下改）：13 列結案並瘦身到 700 bytes 以下，見上方
#: 清單的 R82 段。本值＝當回合實測超標列數，零加減推算。
OVERSIZE_ROW_CEILING = 85

#: 存量列的**超標總量**（Σ max(0, 列 bytes − 上限)）上限。上面三條管的是「有幾列超標」，
#: 這一條管的是「超標多少」——少了它，一列 800 bytes 的豁免列可以長到 8,000 bytes 而
#: 前三條全綠，而主檔體積正是被這個量推上硬閘的。**只准往下改，零成長容忍**；合法出口
#: 只有一個：把長列的詳情搬進具名證據檔，讓這個數字真的變小。
#: 🔴 R79 兩度轉動本棘輪：① 補列作業 162282 → 147944（−14338），`DEF-101-263`／`358`／
#: `628` 三列（皆已結案）的欄內長文逐字搬進 `CrossPlatform_R79_Debt_Audit.md`，只留索引；
#: ② 收尾回收 `DEF-101-557`／`680`／`714`，狀態欄改索引 → 147455。兩次都走合法出口。
#: 取值紀律同 `OVERSIZE_ROW_GRANDFATHERED`：**當回合實測直接填入、零加減推算、不留成長
#: 緩衝**（`TestR79RowByteCeiling::test_the_real_ledger_baselines_are_exact_not_padded`
#: 對本值是逐字相等斷言，留任何餘裕都會當場紅）。
#: 🔴 R80 收尾單人窗口重釘 **147455 → 146210**（往下改 −1245，當回合實測值直接填入）。
#: 誠實揭露淨額的兩個來源，方向相反：
#:   · **降**：上述四筆過期豁免隨 `archive_63` 移出主檔；
#:   · **升**：`DEF-101-886`／`887`／`889` 三列因硬規則② 就地追加改派附記（指向下一輪）
#:     而各自長了約 250 bytes（那三列本來就在豁免清單內）。硬規則② 的合法出口逐字要求「就地
#:     於狀態欄追加附記、不要改寫歷史原文」，而本棘輪要求豁免列零成長 ⇒ 兩道鎖在這三列
#:     上互為對方的違規（同 `DEF-101-957` 的形態）。本輪選擇滿足硬規則②，並把成長量寫在
#:     這裡讓它可被看見——**不是**用「淨額仍下降」把它蓋過去。
#: 🔴 R80 包 C 再往下釘 **146210 → 143303**（−2907，當回合實測值直接填入、零推算）。
#: 來源是 SA-R80-04 的八筆結案：`DEF-100-002`／`101-274`／`101-418`／`101-422`／`01-007`／
#: `101-021`／`022`／`025` 的狀態欄原文**逐字搬進** `CrossPlatform_R80_Scan_Findings.md` §C，
#: 列上只留「結案字＋一句實查結論＋檔名指針」。走的正是本判準訊息自己指定的合法出口——
#: 在一個零成長容忍的棘輪上「追加一句結案理由」方向本身就是錯的，所以結案與瘦身必須同一動作。
#: 🔴 本輪開場重釘 **143303 → 140957**（−2346，當回合實測值直接填入、零加減推算；
#: 輪號不寫進散文的理由同 `OVERSIZE_ROW_CEILING` 上方那段）。
#: 下降來源**單一且方向只有降**：上述三筆過期豁免列隨 `archive_64` 離開主檔，其超標量
#: 一併離開分子。已逐筆核對過殘量：三列在 `archive_64` 實測 757／1712／1977 bytes，超標
#: 量 57／1012／1277 合計 2346，`143303 − 2346 = 140957` **恰等於**實測新值 ⇒ 殘量 0，
#: 本輪沒有任何既有豁免列被改長或縮短（若有，這個差就不會歸零，也就不能這樣寫）。
#: 🔴 帳本清債包再往下釘 **140957 → 138938**（−2019，當回合實測值直接填入、零推算）。
#: 這一次的淨額**同時有升有降**，兩邊都寫出來而不是只報淨值：
#:   · **降**：7 列的狀態欄原文逐字搬進 `CrossPlatform_R81_Ledger_Triage.md` §5，列上
#:     只留結案字＋一句當回合實查結論＋檔名指針。其中 `DEF-101-676` 一列就吐出約
#:     9.8KB——它是全主檔最長的一列，而它談的正是「帳本容量的結構解」。
#:   · **升**：22 列依硬規則② 就地追加「改派，承接輪次：<下一輪>」＋一句「為什麼本輪
#:     做不完」（具體輪號只寫在帳本那些列上——程式碼檔寫「下一輪」的輪號會超前帳本時鐘
#:     而被 `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 當場擋下，本輪實測撞到）。
#:     硬規則② 的合法出口逐字要求「就地於狀態欄追加附記、不要改寫歷史原文」，
#:     而本棘輪要求豁免列零成長 ⇒ 兩道鎖在這些列上互為對方的違規（`DEF-101-957` 形態、
#:     R80 已實證一次）。本輪的解法不是選一邊，而是**把結案與瘦身做成同一個動作**：
#:     用搬離的位元組去付追加附記的位元組，淨額仍為負。
#: 🔴 `OVERSIZE_ROW_CEILING` 與具名清單本輪**刻意不動**：沒有任何一列跨過 700 bytes
#: 的邊界（瘦身後的 7 列仍在線上），所以「有幾列超標」不變。少了這一句，下一個人會以為
#: 「excess 降了、筆數卻沒降」是漏改。
#: 🔴 收尾者再往下釘 **138938 → 138936**（−2，當回合實測值直接填入）。來源是單一列：
#: `DEF-101-870` 的 R81 附記為了脫離 ADR-XPLAT-001 §4.3.1 的誤入而改寫措辭（「凍結版
#: 目錄名慣例」→「各版目錄名慣例」，並把 `改派：` 改成 `_handover_rounds()` 認得的
#: 「承接輪次：」）。兩處都是本輪自己寫下的字，不是歷史原文，故就地改而非追加。
#: 淨額為負＝本次沒有用「調高上限」換綠；訂正的完整理由落在
#: `CrossPlatform_R81_Scan_Findings.md` §C（列上不留指針：再犯時 C1／C2 硬擋會逐字指名
#: 本列，那道鎖本身就是這件事的守衛，列上再寫一份就是第二個家）。
#: 🔴 R82 帳本清債包重釘 **138936 → 123867**（−15069，當回合實測值直接填入、零推算）。
#: 淨額**同時有升有降**，兩邊都寫出來而不是只報淨值：
#:   · **降**：15 列結案／降級並把狀態欄長文逐字搬進
#:     `CrossPlatform_R82_Ledger_Closure.md` §8，列上只留「結案字＋一句當回合實查結論＋
#:     檔名指針」（逐列 −294 ~ −2896 bytes）。
#:   · **升**：4 列（`DEF-101-268`／`324`／`392`／`886`）就地追加一句「我吸收了哪一列」，
#:     各長 109~210 bytes；另 `DEF-101-977` 因寫入回執而長 66 bytes。那是併列結案的
#:     **資訊零損失義務**，方向與本棘輪相反，所以它必須被上面那些列吐出來的位元組付掉。
#:   · **升（第二筆，要單獨寫出來）**：`DEF-101-676` 瘦身後又長回 293 bytes——因為它降級為
#:     `partial` 之後**仍是未結列**，硬規則② 因此要求它二擇一，而「未指派＋可執行的解鎖
#:     條件」本身就要佔位元組。誠實記在這裡：本輪淨額 −15069 是付完這兩筆成長之後的數，
#:     不是用「淨額仍下降」把它們蓋過去。
#: 🔴 本值與 `OVERSIZE_ROW_CEILING` 的**方向鎖**（「只准往下改」那句話的觀測者）住在
#: `tools/lib/ledger_rotation.py`：那句話從 R79 起逐輪寫在這裡，而當回合實測它零觀測者
#: （`DEF-101-993`）。分家的理由不是整齊，是本檔的 LOC 棘輪餘裕近乎零，而該棘輪自己指定
#: 的第一順位處置就是抽共用模組。
OVERSIZE_ROW_EXCESS_CEILING = 123867


def oversize_row_problems(ledger_text: str) -> list[str]:
    """單列位元組上限的四向判準（純函式，可構造輸入驗牙；回空＝全部合規）。

    四向＝① 新超標列不在豁免清單、② 豁免清單過時、③ 清單筆數棘輪、④ 超標總量棘輪。
    ①② 互為反向（缺任一向，清單不是變成永久額度就是讓鎖永紅）；③④ 各自堵住
    「膨脹了就把 ID 補進清單」與「豁免列繼續長大」這兩條 ①② 結構上擋不住的繞道。

    🔴 **本函式刻意不含③④ 兩個上限自己的方向鎖**（R82，`DEF-101-993`）：那是對
    **原始碼常數**的斷言，與餵哪一本帳本無關，混進來會讓「把常數 mock 成別的值」的注入
    測試同時撞上方向鎖（判準的比較對象不該隨被它所判的動作而變）。它住在
    `check_defect_log_crossref.ratchet_direction_problems()`，與 `grandfather_ceiling_problems()`
    同一個理由、同一個位置：`main()` 內無條件執行，不受真實主檔守衛約束。
    """
    sizes = row_bytes(ledger_text)
    over = {i: n for i, n in sizes.items() if n > ROW_MAX_BYTES}
    problems = [
        f"{i}：該列 {over[i]} bytes > 單列上限 {ROW_MAX_BYTES} 且不在存量豁免清單內。"
        f"帳本列是**索引**：把「當回合查證」「解鎖條件」這類長文搬進 docs/06_quality/ "
        f"的具名證據檔（受 _GOVERNANCE_DOCS 體積守門），列上只留一句話與檔名指針。"
        f"🔴 不要把 ID 補進 OVERSIZE_ROW_GRANDFATHERED 來讓本道轉綠——那是砸溫度計，"
        f"且 OVERSIZE_ROW_CEILING 會當場擋下"
        for i in sorted(set(over) - OVERSIZE_ROW_GRANDFATHERED)
    ]
    problems += [
        f"{i}：列在 OVERSIZE_ROW_GRANDFATHERED，但主檔實測"
        + ("查無此 ID" if i not in sizes else f"{sizes[i]} bytes ≤ {ROW_MAX_BYTES}")
        + "⇒ 豁免已過期，請把它從清單移除並同步下修 OVERSIZE_ROW_CEILING 與 "
          "OVERSIZE_ROW_EXCESS_CEILING——留著就是日後無聲加回去的額度"
        for i in sorted(OVERSIZE_ROW_GRANDFATHERED - set(over))
    ]
    if len(OVERSIZE_ROW_GRANDFATHERED) > OVERSIZE_ROW_CEILING:
        problems.append(
            f"存量豁免清單 {len(OVERSIZE_ROW_GRANDFATHERED)} 筆 > 棘輪上限 "
            f"{OVERSIZE_ROW_CEILING}（只准往下改）：要新增豁免，先把等量的列真的瘦身")
    excess = sum(n - ROW_MAX_BYTES for n in over.values())
    if excess > OVERSIZE_ROW_EXCESS_CEILING:
        problems.append(
            f"存量列超標總量 {excess} bytes > 棘輪上限 {OVERSIZE_ROW_EXCESS_CEILING}"
            f"（只准往下改、零成長容忍）：既有豁免列被改長了 "
            f"{excess - OVERSIZE_ROW_EXCESS_CEILING} bytes。合法出口＝把該列詳情搬進"
            f"具名證據檔，或在同一次變更內把別的列縮回等量以上")
    return problems
