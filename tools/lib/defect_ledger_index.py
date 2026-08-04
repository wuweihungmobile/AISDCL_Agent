"""缺陷帳本的**歸檔索引**、**散文式結案宣稱**與**未結存量**共用基元
（R69 `DEF-101-734`／`DEF-101-735`；R74 新增未結存量量測入口與「改派／回執」判準本體）。

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
    for w in warns:
        print(f"⚠️  {w}")
    for f in fails:
        print(f"❌ {f}")
    return 1 if fails else 0
