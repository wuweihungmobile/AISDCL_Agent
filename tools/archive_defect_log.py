#!/usr/bin/env python3
"""缺陷帳本歸檔輪替工具 — 把「每輪即興重寫一次搬遷腳本」變成有載具、可測試的 SSOT。

🔴 為何需要這支工具（R60 立帳，DEF-101-527／528）：

帳本主檔受 `check_defect_log_crossref.py` 的 256KB 硬閘管制（`_LEDGER_FAIL_BYTES`），
歷輪反覆撞閘（R56 一輪兩次、R57 三次、R59 兩次、R60 動工前一次），而**搬遷判準與保全
檢查每一輪都是在對話裡臨時寫一支腳本**、跑完即丟。後果在 R60 當場兌現，被四方掃描抓到三件事：

  1. `archive_29`／`archive_30` 標頭都宣稱「由歸檔腳本以閘門自身邏輯機械檢查、逐筆顯式
     assert」，但 **repo 內零載具** — 那個「腳本」只存在於某一次 session 的暫存目錄。
     宣稱一道機械檢查存在、而它不可重跑，等同沒有檢查（Scan-D 反駁者 D-refuter-1）。
  2. 標頭散文所載的判準與實際執行的判準**不是同一個東西**。例：判準②若照字面（子字串包含）
     機械執行，會把狀態欄含 `OpenMutexW` 的 `DEF-101-504` 誤判為「含 open 活躍字樣」而擋下；
     實際執行的版本用的是 ASCII 邊界 lookaround，不會誤判（Scan-G 反駁者 G-refuter-4）。
     **文件所載判準必須就是被執行的那一個** — 故本工具把判準寫成程式，標頭改為引用本檔。
  3. 舊判準只看「狀態欄關鍵字」，對**散文裡的活 backlog 全盲**。R60 動工前那次歸檔因此把
     `DEF-101-517`（散文明寫「下一輪先評估這兩條較便宜的路徑」）與 `DEF-101-526`
     （散文明寫「R60 候選」）當一般已結列搬走，主檔零承接者（Scan-G G-01）。

另外一件事本工具刻意用程式擋掉：R60 動工前那支臨時腳本用 `Path.write_text()` 寫檔，
其 `newline` 預設為 `None`，在 Windows 上把 LF 譯成 `os.linesep`（CRLF），
於是整份帳本從 `w/lf` 變成 `w/crlf`、與 `.gitattributes` 宣告的 `eol=lf` 相反，
還讓「位元組總量守恆」那項自我斷言在最終產物上按字面重驗為假（多出的位元組正是每行一個 `\\r`）。
本檔一律走 bytes 層寫入並在落地後**顯式檢查**磁碟實體零 `\\r`
（R60 round 1 起刻意不用 `assert`：`python -O` 會把 assert 整條編譯掉，而這些檢查
守的是「就地覆寫帳本主檔」這個破壞性動作，見 `conservation_problems()` 檔頭）。

## 判準（程式即權威；散文說明僅供閱讀）

一筆缺陷總表列可被搬遷，需同時滿足：
  ① 狀態欄分類 ∈ {fixed, wontfix, closed-by-decision}（沿用閘門的 `_classify`）
  ② 狀態欄**不含**活躍字樣 open／routed／deferred／watch／workaround
     —— 用 ASCII 邊界 lookaround，**不是**子字串包含（見上方第 2 點）
  ③ 不在「四份 crossref 掃描目標對其做出可辨識狀態宣稱」的 ID 集合內
     —— 以閘門自身的 `_CLAIM_RE` + `_classify` + `_ID_RE` 實算
  ④ 整列散文（不只狀態欄）不含「向未來輪次交棒」的字樣；命中者**不自動搬**，
     必須由操作者以 `--ack-handoff <ID,...>` 逐筆具名承認才會搬。
     這一條刻意設計成「需具名承認」而非「硬擋」：硬擋會讓帳本永遠搬不動
     （歷史已結列的散文常提到 backlog），而完全不管就是 R60 踩到的靜默埋葬。
  ⑤ 該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）
  ⑥ 帳本家族與具名治理文件內**沒有**任何指針宣稱該 ID 現居主檔（DEF-101-612，
     「指針反向依賴」）；命中者**硬擋、不接受 `--ack` 繞過**——這條與④相反：
     交棒是主觀判斷才需要人承認，指針居所是可驗證的事實陳述，允許承認後照搬
     等於讓操作者親手重演 R60 撞到的「搬走 3 筆列、11 處指針同時失實」事故

## 🔴 第三種「立帳見」方言：擴稽核面，**不**禁用（R60 round 2 ARCH-R60R2-05，方案甲）

本輪在帳本家族**外**造出第三種方言：`CrossPlatform_R60_Fix_Evidence.md` 與
`CrossPlatform_Scan_Dimensions.md` 都寫「立帳見缺陷帳本 `DEF-...`」。以生產物件實測，
它當時**完全逸出稽核**：`POINTER_RE.findall()` 回 `[]`（scope 群組只收 `本表|主檔`）、
`POINTER_VERB in line` 為 True、`_quotation_kind()` 回 None、檔案又不在 `_family_files()`
內 ⇒ 同一個動詞在家族內是硬錯誤、在家族外零檢查。

處置**不是禁用該語法**（那個方向已被實測駁回，理由記在此處以免復辟）：
  (a) 禁用會製造大量誤紅——`CrossPlatform_R60_Fix_Evidence.md` 本身就是「討論指針修復」
      的證據檔，實測全檔「立帳見」字樣**絕大多數不是活體指針**，而是 code fence／表格
      backtick 內的**逐字引述**（稽核輸出貼上、修復對照表）。各類命中的實數不寫在此處：
      `--check` 每次執行都會印出「指針數／引述數」與逐處清單（Scan-H #3：鎖的散文不得
      寫死可由程式現查的數字）。
  (b) **更關鍵：禁用會把偵測面一起丟掉。** `CrossPlatform_Scan_Dimensions.md` 指向的
      `DEF-101-555` 是判準④ 攔下、留在主檔待 R61 承接的**活列**；一旦 R61 把它搬進
      archive_32，那句就靜默變成失實指針——與 `archive_26`／`27` 的 `DEF-101-493`
      完全同一個劇本，而 493 正是 ARCH-R60-01 的原始案例。
故改為：`POINTER_RE` 的 scope 增收 `缺陷帳本`（語意等同「主檔」），且**稽核面由「帳本
家族」擴為「帳本家族 ∪ 具名治理文件集合」**（`_GOVERNANCE_DOCS`，與 `_family_files()`
併成單一 SSOT `_pointer_audit_files()`，工具內不另生第二條 glob）。

## 🔴 切欄／欄位定位一律走閘門 SSOT，本檔零複本（R60 round 3 Pkg-P7）

本檔**曾**自帶一份切欄實作（`_CELL_SPLIT_RE` ＋ `_cells()`），寫成
`[c.strip() for c in _CELL_SPLIT_RE.split(line) if c.strip()]`——`if c.strip()` 把**空欄
整個濾掉**，欄位索引於是隨「該列有幾個空欄」浮動，而 `classify_row()` 又取 `cells[-1]`
當狀態欄。Pkg-P6 已在 `check_defect_log_crossref.py` 修掉同型缺陷，但**同一個 bug 的複本
不會自動被傳染修好**：本檔實測（未動任何 tracked 檔，構造輸入）

  · 狀態欄空白 ＋ 分流去向＝「已於上游 fixed 故不另修」
    ⇒ `classify_row()` 回 `cls='fixed'`、`blockers=[]` ⇒ **該列被判為可搬**。
    危害比閘門那一側更重：閘門只是把狀態讀錯，本檔會**真的把它寫進 archive**——
    一筆狀態欄空白（＝狀態不明）的缺陷就此靜默下葬，正是 R60 立本工具要消滅的病。
  · 狀態欄空白 ＋ 分流去向＝「open 待下輪處理」
    ⇒ 誤讀成 `cls='open'`，恰好擋下，但擋下的理由是錯的（讀的是別欄）。

故本檔的切欄與欄位定位全部委派 `gate._row_cells()`／`gate._table_layout()`／
`gate.row_arity_problems()`，本地零複本，並由
`tools/tests/test_archive_defect_log.py::TestGateSsotCouplingContract` 以 AST 斷言
「本檔不得再長出第二份切欄邏輯」（`_GATE_SSOT_CONTRACT` ＋ `_local_cell_split_sites()`）。
形狀沿用本 repo 既有的「N 份 → 1 份 SSOT」先例（`tools/tests/_ps_engine.py`、
`tools/_script_scan_surface.py`），不另創第二種收斂方式。

使用：
  python tools/archive_defect_log.py --plan
  python tools/archive_defect_log.py --apply --archive-num 31 [--ack-handoff DEF-101-517,...]
  python tools/archive_defect_log.py --check      # 事後保全稽核（項數＝ `CHECK_CRITERIA`）

`--apply` 除了搬列，**還會自己把該次歸檔的索引 bullet 寫進歸檔索引檔**
（`AutoSDD_Defect_Log_archive_INDEX.md`；R69 DEF-101-734 前寫在主檔內）
（判準⑤ 的根因級修法）：建立 archive 的那支程式同時負責註冊，「歸檔完忘記更新索引」
就不再是一條靜默路徑。R60 收輪前那次 `archive_31` 走的是人工歸檔、漏了登記，
而 `--check` 當時的四項判準完全不看索引段，照印 rc=0（四方 round 2 全數命中）。

`--check` 是 root-infra 閘門的一員（`tools/git-hooks/pre-push` 的守門迴圈 ＋
`.github/workflows/root-infra-ci.yml` 的一道 step；**接線位置以那兩支檔現查為準，此處不寫
序號**——序號會隨其他守門增刪而 stale，且由
`TestCheckIsWiredIntoGates` 驗「有沒有接上」而非「接在第幾位」），與 `check_defect_log_crossref.py`
同級——R60 round 1 ARCH-R60-02／QA-R60-01 實證「可重跑但沒有任何閘門看它的 rc」
與「不可重跑」是同一個病的兩種形狀，故本輪把 rc 真正接上閘門。
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護
import check_defect_log_crossref as gate  # noqa: E402  # 判準 SSOT：不自己另寫一份正則
from lib import defect_ledger_index as _ledger_index  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
_QUALITY_DIR = _REPO_ROOT / "docs" / "06_quality"
_LEDGER = _QUALITY_DIR / "AutoSDD_Defect_Log.md"
_ARCHIVE_GLOB = "AutoSDD_Defect_Log_archive_*.md"

# 歸檔索引檔（R69 `DEF-101-734`）——常數／解析／插入基元一律再匯出自 `tools/lib`，
# 本檔不另寫一份（WHY 與外移理由見該模組 docstring；兩支工具共用同一個物件）。
_ARCHIVE_INDEX_NAME = _ledger_index.ARCHIVE_INDEX_NAME
ARCHIVE_INDEX_BULLET_RE = _ledger_index.ARCHIVE_INDEX_BULLET_RE
index_bullet_lines = _ledger_index.index_bullet_lines
insert_index_bullet = _ledger_index.insert_index_bullet


def ARCHIVE_INDEX_DOC() -> Path:
    """歸檔索引檔路徑。刻意是**函式**：測試沙箱 monkeypatch 的是 `_QUALITY_DIR`，
    模組常數會在 import 時就綁死 repo 內的真檔，注入測試會寫穿 tracked 檔。
    """
    return _ledger_index.archive_index_doc(_QUALITY_DIR)


CLOSED_CLASSES = frozenset({"fixed", "wontfix", "closed-by-decision"})

# 🔴 **再匯出（re-export），不是複本**：`= gate._CELL_SPLIT_RE` 綁的是**同一個物件**
# （由 `TestGateSsotCouplingContract::test_cell_split_alias_is_the_gate_object_itself`
# 以 `assertIs` 鎖住，所以它永遠不可能漂移成第二份實作）。
# 為何留這個名字：`tools/tests/test_adr_xplat001_c1c2_lock.py:278` 已經在消費
# `ADL._CELL_SPLIT_RE`，而該檔的 `row_cells()` docstring 逐字寫著「刻意不直接用
# `ADL._cells()`：那支會用 `if c.strip()` 丟掉空格子——中間任一欄留空就整排錯位」
# ——它**早就獨立踩到並繞開了本輪 Pkg-P7 修的同一個 bug**，只是繞法是自己再切一次。
# 該檔不在本包所有權內，直接移除本名稱會讓根層測試套件紅一批（實測；筆數不寫死，套件
# 規模每輪都在變），故本輪以
# 再匯出維持相容，並把「該檔應改用 `gate._row_cells(line)[1:-1]`」列為跨包請求。
_CELL_SPLIT_RE = gate._CELL_SPLIT_RE

# 判準② — ASCII 邊界，故 `OpenMutexW`／`reopened` 不會誤命中（G-refuter-4）。
ACTIVE_STATUS_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:open|routed|deferred|watch)(?![A-Za-z0-9])|workaround"
)

# 判準④ — 「向未來輪次交棒」的散文標記。刻意保守（寧可多攔下來要求具名承認）。
# SA-R63-01：原清單遺漏「留待」「承接者」「改派」三種同語意交棒措辭——
# DEF-101-614（「…留待 R62」）／DEF-101-615（「…承接者改派 R63」）兩筆歸檔列
# 經 SA 複審親跑正則證實未命中（人工覆核確認兩列本身標的已完成、不算誤歸檔，
# 但正則本身確有此盲區，見 DEF-101-616）。
HANDOFF_PROSE_RE = re.compile(
    r"R\d+\s*候選"          # 「R60 候選」
    r"|下一?輪"              # 「下一輪」「下輪」
    r"|解鎖條件"
    r"|留待"                # 「留待後續」「留待 R62」
    r"|承接者"               # 「承接者為 XX」「承接者改派」
    r"|改派"                # 「改派給 YY」
    r"|(?<![A-Za-z0-9])deferred(?![A-Za-z0-9])"
    r"|(?<![A-Za-z0-9])backlog(?![A-Za-z0-9])"
)

# ---------------------------------------------------------------- 判準清單 SSOT（Pkg-P7 P7-4）
# 🔴 這兩個常數是「本工具有哪些判準」的**唯一**真相源：`check()` 的成功訊息與 `apply()` 寫進
# archive 標頭的散文**全部由它們生成**，不得手寫第二份清單。
#
# WHY 必須生成而不是各寫一份：R60 round 2 主控推翻方案(乙)、刪掉 `check()` 的第(7)項「具名
# 治理文件無家族專用語法的指針宣稱」反向鎖，卻**漏改 `apply()` 標頭裡手寫的「共七項」清單**。
# 而 archive 是**零刪除的史料檔** ⇒ 每跑一次 `--apply` 就把那份失實宣稱複製成一份新的永久
# 紀錄。這與本工具立帳要消滅的病（「宣稱一道機械檢查存在而它不存在」）完全同型，且是在同一
# 輪、同一支工具身上復發（P7-4 實查坐實）。改為生成之後，「兩份說法」在結構上不可能出現。
#
# 對應機械鎖：`tools/tests/test_archive_defect_log.py::TestCriteriaListIsASingleSsot`
#   (a) `check()` docstring 的 `(N) 標題` 逐項與本常數**雙向**互比（手法比照
#       `check_defect_log_crossref._prose_status_first_words` 把程式常數綁死在散文上）；
#   (b) 每一項都必須在 `check()` 實作裡有 `# (N)` 段落標記 ⇒ 宣稱一項就得有一段程式；
#   (c) `apply()` 產生的標頭必須逐字含每一項標題，且不得出現超出項數的項次編號。
CHECK_CRITERIA: tuple[tuple[str, str], ...] = (
    ("行尾", "帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）"),
    ("重複列", "同一 ID 在同一份檔內不得出現兩列"),
    ("跨檔矛盾", "同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話"),
    ("立帳指針", "稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致"),
    ("歸檔索引涵蓋性",
     "磁碟上每支 archive 都要在歸檔索引檔有一條以它為主體的 bullet（雙向）"),
    ("非「立帳見」方言的居所宣稱",
     "`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；"
     "裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID"),
    ("表格列欄數", "每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免"),
    # 🔴 (8) R68 新增（DEF-101-676）：搬遷判準③ 由「被宣稱過就硬擋」改寫為「搬後宣稱仍
    # 解析得到」之後，那個「仍解析得到」不能只是**斷言**——本工具立帳要消滅的病就是
    # 「宣稱一道機械檢查存在而它不存在」（見 CHECK_CRITERIA 上方 P7-4 的 WHY）。本項就是
    # 那道檢查本體：對四份掃描目標的每一句可辨識狀態宣稱，實跑帳本家族解析，任何一句
    # 解析不到（或解析到的狀態與宣稱不符）即 rc=1。它同時是判準③ 改寫的**安全網**：
    # 一旦 archive fallback 哪天失效（glob 改壞、archive 表頭改版），本項當場轉紅，
    # 而不是等到某個讀者只讀主檔而誤判某缺陷「查無此 ID」。
    ("跨檔宣稱可解析",
     "掃描目標的每一句狀態宣稱都要能在帳本家族（主檔 ∪ archive）解析到，且狀態一致"
     "（判準③ 改寫後的事後條件，R68）"),
)

# 搬遷判準（`classify_row()` ①②③⑤ ＋ `plan()` ④⑥）。同樣由本常數生成 archive 標頭散文。
#
# 🔴 第⑥項（DEF-101-612，「指針反向依賴」）：R60 收尾包執行 `--apply` 時實際撞到
# ——判準①②③④⑤ 只看該列**自身**狀態，完全不看「有沒有別的檔指著這一列」。搬走
# `DEF-101-529`／`555`／`558` 後，家族與治理文件內共 11 處「立帳見主檔」／「見主檔」
# 指針當場失實，而**當時**這件事只有 `--check`（事後稽核）才抓得到——`plan()`／`apply()`
# 本身對此毫無鑑別力，等於先製造缺陷、再靠下一次事後稽核去發現它。
# 本項把同一組掃描搬到搬遷**之前**：`_external_residence_claims_for()` 共用 `check()`
# 判準(4)(6) 已在用的同一批基元（`POINTER_RE`／`NONVERB_RESIDENCE_RE`／`_quotation_kind`／
# `_fenced_line_numbers`／`_CODE_SPAN_RE`），而不是另寫一份掃描規則——否則帳本／治理文件
# 內逐字引用判準語法的段落（例如 `CrossPlatform_R60_Fix_Evidence.md` 圍籬區塊內逐字重現
# 的舊指針清單）會被誤判為對某 ID 的真實居所宣稱，重演 Pkg-P12「載具自己假紅」的形狀。
# 刻意設計成**硬擋、不提供 `--ack` 繞過**（與判準④ 的交棒偵測不同）：交棒是主觀判斷，
# 需要人具名承認「已有承接者」；但指針居所是可驗證的事實陳述，允許「承認後照搬」等於
# 讓操作者親手重演本項要消滅的事故。正確路徑是先把外部指針改成正確居所（或改寫成
# 「現居 archive_NN」指向即將建立的目的檔），該列才會回到可搬狀態。
#
# 🔴 R68 修訂第②③ 兩項（DEF-101-676 容量政策解）——兩項原文都把「疑似」當「成立」，
# 合計把 55922 bytes 的**已結**列永久釘在主檔，使輪替吞吐趨近零：
#   ② 原文「狀態欄無活躍字樣」是對整欄裸掃描，實測 16 筆已結列命中的是 `open(` 這個
#      Python 內建函式、或本列自己被推翻的舊狀態引述（詳見 `active_status_hit()`）。
#      改為「排除程式碼片段與角引號引述之後仍無活躍字樣」——收窄的是**誤報面**，
#      裸散文與判準④ 兩道鑑別力原封不動。
#   ③ 原文「未被 crossref 掃描目標做過可辨識狀態宣稱」把「有人提過這一列」當成不可搬，
#      但真正的危害從來不是「被提過」，而是「搬走後那句話解析不到」。該缺口的根因在
#      `check_defect_log_crossref._load_ledger_status()` **只讀主檔**；R68 補上
#      `_load_archive_status()` 後帳本 SSOT 才是它一直宣稱的「主檔 ∪ archive 家族」，
#      本項於是改寫成「搬走後宣稱仍解析得到」這個**可驗證的事後條件**，並由 `--check`
#      判準(8) 逐筆實跑驗證（不是把檢查刪掉——刪掉才是本工具立帳要消滅的那種病）。
MOVE_CRITERIA: tuple[str, ...] = (
    "狀態欄分類已結（fixed／wontfix／closed-by-decision）",
    "狀態欄無活躍字樣（open／routed／deferred／watch／workaround，ASCII 邊界非子字串；"
    "程式碼片段與角引號引述內的字樣不算，R68 收窄）",
    "被 crossref 掃描目標宣稱過狀態者可搬，但搬後該宣稱必須仍解析得到"
    "（帳本家族＝主檔 ∪ archive；由 --check 判準(8) 實跑驗證，R68 改寫）",
    "散文帶交棒字樣者需 `--ack-handoff` 具名承認",
    "該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）",
    "無外部居所指針宣稱本列現居主檔（指針反向依賴，DEF-101-612；有則硬擋，"
    "須先訂正該指針，不接受 --ack 繞過）",
)

_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"

#: DEF-101-676 的解鎖判準門檻（R67 round 4 訂）：`--plan` 印出的「搬後主檔約 N bytes」
#: 距 `gate._LEDGER_FAIL_BYTES` 必須 ≥ 本值。**這是判準門檻本身、不是量測快照**——原始
#: 解鎖條件寫的是「可搬筆數 > 0」，那是 fail-open（當輪多寫一列已結列就自己變 True，
#: 量的是「有沒有可搬的列」而不是「輪替還買不買得到餘裕」）。放在程式常數而非散文裡，
#: 是為了讓「解鎖了沒」每跑一次 `--plan` 就當場現算，不必有人記得去翻帳本對數字。
_UNLOCK_HEADROOM_BYTES = 10240

# ---------------------------------------------------- 判準(7) 的既有列具名基線（Pkg-P7 P7-2）
# 🔴 帳本家族 archive 側實查有一批列的欄內含**未轉義的字面豎線**（須寫成 `\|`），因而被
# 多切出欄位。**逐檔筆數就是下方這張表本身**（本表即該數字的唯一真相源，散文不複寫一份，
# 否則就是 Scan-H #3 講的第二個 stale 站點）。`DEF-101-560` 已逐筆具名**不修**
# （史料檔逐字保全、今日零活體
# 後果），而 `check_defect_log_crossref.py` 之所以不誤紅是因為它**從不解析 archive 的表格
# 列**（只 `stat()` 量大小）——本檔的 `check()` 會解析家族每一份檔，故必須明確處置。
#
# 處置＝方案(丙) 具名基線，**不是** (甲) 只警告不阻擋、也**不是** (乙) 去改史料檔：
#   · (甲) 被否決：「archive 側只警告」等於把整個 archive 面的欄數腐化永久降級成雜訊，
#     而下一輪把一列壞列搬進 archive_32 時它同樣只是警告 ⇒ 硬擋面等於沒有。
#   · (乙) 被否決：那些列都在 archive 檔內、`DEF-101-560` 已具名不修，且那些檔不在本包的
#     所有權內；改史料檔要另行核准，本包無權推翻該決定。
#   · (丙) 採用：形狀比照 `tools/tests/test_adr_xplat001_c1c2_lock.py::_BASELINE_WAIVERS`
#     ——具名、逐檔、帶 stale 自檢（實測少於登記數即紅並要求把數字改小／刪掉），且每次
#     執行都逐檔列印（豁免看得見才不是靜默豁免口，同 `check_pytest_baseline_sites.py`）。
#
# 🔴 「歷史列不追溯、新列硬擋」為何在結構上成立（同 ADR C1/C2 鎖的形狀）：
#   · **主檔零登記**（且 `check()` 另有顯式守門拒絕為主檔登記豁免）⇒ 任何壞列一進主檔就紅。
#   · archive 是**只新建、不回頭改**的史料：`apply()` 只會建**新**檔，而新檔名不在本字典內
#     ⇒ 把一列壞列搬進 archive_32 一律硬擋。
#   · 既有檔的數字**只准往下改**：實測數 > 登記數即紅（新增壞列）、< 登記數亦紅（stale）。
# ⚠️ 誠實劃界：本基線鍵在「檔名 + 筆數」而非「檔名 + DEF-ID」——因為檢查本體一律用閘門的
#    `gate.row_arity_problems()`（不在本檔重跑第二次逐列判定），而該純函式回傳的是訊息清單、
#    不回傳 ID。代價是「同一檔內把一列壞列換成另一列壞列」筆數不變而不被本項抓到；那種動作
#    要改動逐字保全的史料檔，會被 git diff 與 `conservation_problems()` 的位元組守恆擋在前面。
_ARITY_BASELINE: dict[str, int] = {
    "AutoSDD_Defect_Log_archive_03.md": 3,
    "AutoSDD_Defect_Log_archive_04.md": 3,
    "AutoSDD_Defect_Log_archive_09.md": 5,
    "AutoSDD_Defect_Log_archive_16.md": 1,
    "AutoSDD_Defect_Log_archive_23.md": 1,
    "AutoSDD_Defect_Log_archive_28.md": 1,
}

# 「立帳見」指針：歸檔索引列與 archive 標頭都會指向一筆說明該次歸檔的缺陷條目。
# 合法形態 = 四種 scope × 有無「現居」註記：
#   `立帳見本表 DEF-x`        ＝宣稱該 ID 就在**指針所在的那份檔**（寫在主檔內即主檔）
#   `立帳見主檔 DEF-x`        ＝宣稱該 ID 在帳本主檔（archive 檔內慣用此形態）
#   `立帳見缺陷帳本 DEF-x`    ＝同「主檔」（治理文件內慣用此形態；ARCH-R60R2-05 新增）
#   `立帳見 DEF-x`（無 scope）＝同「主檔」
#   任一形態加「（現居 archive_NN）」＝宣稱它已歸檔至該檔；此註記優先於 scope
# 全部形態都會被 `--check` 在 `_pointer_audit_files()` 的**每一份檔**上驗證居所，
# 所以歸檔動作把某筆「立帳」條目搬走時無法靜默留下失實指針。
#
# 🔴 R60 round 1 四方複審 ARCH-R60-01／QA-R60-02 實證前一版的兩個洞（本行的存在理由）：
#   (a) 稽核面只掃主檔 → archive 檔內的指針一律不驗；
#   (b) 樣式不認 `立帳見主檔` → 即使掃了也不命中。
# 兩洞疊加的後果是 `archive_26`／`archive_27` 各有一處 `立帳見主檔 DEF-101-493`
# （實居 archive_28）逃過稽核，而 `--check` 照印 ✅ rc=0。
# 🔴 round 2 ARCH-R60R2-05 再補第三種 scope `缺陷帳本`：家族外的治理文件用的是這個
# 寫法，scope 群組不收就等於整句逸出（見本檔 docstring「方案甲」段的實測）。
# `[`*]{0,2}`＝容許 markdown 強調包住 ID／archive 標籤。帳本實際慣用 `` `DEF-101-555` ``
# （反引號）與 `**DEF-101-555**`，樣式若只認裸 ID，這些真指針會被硬要求誤判為「無 ID
# 散句」——本輪實測踩到：帳本寫入 7 處 `立帳見本表 `DEF-101-555`` 時全部誤報。
POINTER_RE = re.compile(
    r"立帳見(?P<scope>本表|主檔|缺陷帳本)?\s*[`*]{0,2}(?P<id>DEF-\d+-\d+)[`*]{0,2}"
    r"(?:（現居\s*[`*]{0,2}(?P<archive>archive_\d+)[`*]{0,2}）)?"
)

# 「立帳見」動詞本身＝硬要求的偵測面：凡出現此字樣，其後**必須**跟得上可解析的
# DEF-ID。沒有這條硬要求，寫成「立帳見本表 R57 條目」這類無 ID 散句就是永久豁免口
# ——前一版程式碼自己在錯誤訊息裡警告「改成無註記散句只會讓檢查失效」，卻沒有任何
# 鎖擋這種寫法，而樹上當時真有三處（主檔 ×2、archive_25 ×1）（ARCH-R60-01 ③）。
POINTER_VERB = "立帳見"

# 硬要求有且僅有四種例外，四種都**逐處列印**（見 `check()` 的引述清單）：
#
#  (甲) 動詞落在 **inline code span**（單反引號成對）內 ⇒ 引述指針語法。帳本的缺陷
#       條目本來就會逐字引述判準（敘述本輪 ARCH-R60-01 時寫 `` `立帳見主檔` ``、
#       `` `立帳見主檔 DEF-101-493`（實居 archive_28） ``），把這些當宣稱會讓帳本
#       永遠無法談論自己的判準。
#  (乙) 動詞後緊接 `」` 或 `』`（即 `「立帳見」`／`『立帳見』` 這種**術語提及**）
#       ⇒ 結構上不可能是宣稱：引號當場閉合，後面沒有 ID 槽位。本 repo 中英夾雜的
#       敘述習慣大量使用 `「立帳見」字樣` 這種寫法（本檔自己的錯誤訊息就是），一律
#       誤報會逼人改寫正確的散文。這條例外無法被濫用——沒有 ID 就沒有宣稱可以夾帶。
#       （`』` 於 round 2 擴稽核面時補入：實測 `CrossPlatform_R60_Fix_Evidence.md:825`
#       用的是巢狀引號 `『立帳見』`，與 `」` 是同一個結構、同一個論證。）
#  (丙) 動詞落在 **``` 圍籬區塊**內 ⇒ 逐字重現原文／工具輸出。與 (甲) 同原理，只是
#       圍籬跨行、必須用行狀態機才判得出（見 `_fenced_line_numbers()`）。實測
#       `CrossPlatform_R60_Fix_Evidence.md:830~836` 就是把 `--check` 的實測輸出與舊的
#       失實寫法逐字貼上當證據——那是證據，不是宣稱。
#  (丁) **僅限具名治理文件**（`_GOVERNANCE_DOCS`）：動詞後未跟可解析 DEF-ID、**且該處
#       落在同一行的「」或『』引號內**的提及。
#       ⚠️ 這條**刻意不適用於帳本家族**——家族內的無 ID 散句正是 ARCH-R60-01 ③ 的
#       原始缺陷（樹上當時真有三處），那裡它必須是硬錯誤。治理文件的角色不同：它們
#       在**討論這個語法本身**，`CrossPlatform_R60_Fix_Evidence.md` 的訂正註段甚至逐字
#       記著「訂正註若把舊的失實形態逐字重寫…指針稽核會把那段引用當成一個新的失實指針
#       而報紅——我第一版就這樣自己觸發了一次」。對這種散文硬要求 ID，等於逼人改寫
#       **正確的**紀錄。它也無法夾帶宣稱：沒有 ID 就沒有居所可宣稱。
#
#       🔴 **round 3 收窄為「必須落在「」或『』內」（SA-R60R3-06；三方判斷不一致，主控裁決）**
#       —— 三方對**事實**一致：治理文件內一句未加引號、非 code span、非圍籬的散句
#       `立帳見主檔 <非 ID 字樣>` 會被 (丁) 放行（rc=0）。分歧純在**價值判斷**：
#         · Architect：撤回「(丁) 重開了 ARCH-R60-01③」的疑慮（實測只命中一處且不適用家族）。
#         · SD：以四發注入判定 **(丁) 沒有重開** ARCH-R60-01③（家族內同句仍 RED、治理文件
#           內帶真實 ID 的正確指針 GREEN、帶失實 ID 的 RED），只豁免「無 ID 因而無物可稽核」。
#         · SA：判定**重開**——例外開得比需要寬，形態級模糊仍在。
#       **主控裁決：採納 SA 的收窄**。理由：代價僅一行判準，而現存唯一 (丁) 用例本就落在
#       「」內 ⇒ **零誤紅**（落地實測 `--check` rc=0、既有引述清單筆數不變），收窄能消掉
#       一個形態級模糊。ARCH／SD 的相反判斷同時記錄在案，**不得**改寫成「四方一致認為」。
#       收窄後的邊界更清楚：引號與 (甲) 反引號、(丙) 圍籬同屬**看得見的刻意標記**，
#       「這是在提及一個語法」於是有了三種一致的表達方式，而不是「沒跟 ID 就算」。
#
# 🔴 為何這四條不是新的豁免口：(a) 前三條都是**看得見的刻意標記**（反引號渲染成等寬
# code、`」` 是閉合引號、圍籬區塊在渲染後自成一塊），第四條的邊界是「沒有 ID」＝結構上
# 沒有宣稱可夾帶，與原始缺陷「長得像活指針卻不可稽核」的靜默退化完全不同型；
# (b) `check()` **每一次執行都會逐處列印**被視為例外的位置、原文與**憑哪一條**（比照
# `check_pytest_baseline_sites.py` 的 `baseline-ok:` 豁免逐次列印稽核慣例），
# 所以拿反引號夾帶一個真指針來規避，會在每一次閘門輸出裡現形，不可能靜默。
# 🔴 **再匯出（re-export），不是複本**（R68）：`= gate._CODE_SPAN_RE` 綁的是**同一個
# 物件**，形狀沿用本檔既有的 `_CELL_SPLIT_RE = gate._CELL_SPLIT_RE` 先例。R68 在
# `check_defect_log_crossref.status_variant_problems()` 也需要「反引號內是逐字引述、
# 不算宣稱」這條判準；同一個判準寫兩份正是本 repo 反覆在治的複本型缺陷，故收斂為
# 一份 SSOT（方向必然是 gate → 本檔：本檔 import gate，反向會是循環 import）。
_CODE_SPAN_RE = gate._CODE_SPAN_RE
_TERM_MENTION_SUFFIXES = ("」", "』")
# 例外 (丁) 收窄用（SA-R60R3-06）：同一行的成對轉角引號。與 `_CODE_SPAN_RE` 同形狀——
# 兩者都是「看得見的刻意標記」，故用同一種判定方式（掃出成對區間、看該處落不落在區間內）。
_CORNER_QUOTE_RE = re.compile(r"「[^「」]*」|『[^『』]*』")

# 判準④ 的稽核面第二半：具名治理文件集合（ARCH-R60R2-05 方案甲）。
# 這些檔不是帳本，**不參與**居所判定的來源（居所一律由帳本家族的表格列決定），只是
# 「會寫出指針宣稱」的地方，故納入指針稽核而不納入 (1)(2)(3)(5) 那幾項帳本結構判準。
#
# 🔴 **再匯出（re-export），不是複本**（R60 round 3 SA-R60R3-01，BLOCKING）：
# `= gate._GOVERNANCE_DOCS` 綁的是**同一個 tuple 物件**，由
# `tools/tests/test_archive_defect_log.py::TestGovernanceDocsAreOneSharedSsotObject`
# 以 `assertIs` 鎖住，所以它永遠不可能漂移成第二份清單。形狀沿用本檔既有的
# `_CELL_SPLIT_RE = gate._CELL_SPLIT_RE` 先例（「N 份 → 1 份 SSOT」）。
#
# 原始缺陷：本行**曾經**自己寫一份 `(Evidence.md, Scan_Dimensions.md)`，與閘門那份
# `(Evidence.md, Evidence_r3.md)` **同名而成員不同、各缺對方一支**。後果：本輪新生的
# 姊妹證據檔 `CrossPlatform_R60_Fix_Evidence_r3.md` 進了體積閘門卻**完全不在本檔的指針
# 稽核面**（主控實測 `r3 in _pointer_audit_files()` 為 False），其中十餘處指針方言零檢查；
# 對稱地 `CrossPlatform_Scan_Dimensions.md` 進了指針稽核卻不在體積守門內。
# 沙箱注入證明**鎖本身有完整牙齒**，缺的純粹是稽核面沒收進去——正是 `DEF-101-587`
# 講的「搬到另一支檔就繞過守門」，這次繞過的是指針鎖。
# 兩項義務為何是同一個集合（而非兩個不同名字的常數），逐條 WHY 寫在閘門那一側的定義處。
#
# 路徑仍以 `_REPO_ROOT` 為基準而**不是** `_QUALITY_DIR`（閘門那側同樣如此）：測試沙箱會
# monkeypatch `_QUALITY_DIR`／`_LEDGER` 把家族搬到 tmp，若這幾支跟著搬走就會在沙箱裡
# 「查無此檔」，把一道真鎖變成沙箱內的假訊號。要在測試裡替換它請直接 monkeypatch 本常數
# （rebind 本模組的名字即可，不會動到閘門那一側）。
_GOVERNANCE_DOCS = gate._GOVERNANCE_DOCS

# 判準⑥ — **非**「立帳見」方言的居所宣稱。SA-R60R2-03 實證的逸出面：`archive_26` 寫
# 「見主檔 `DEF-101-481`」（實居 archive_27），比 `立帳見` 少兩個字就完全逃過判準④，
# 於是 `--check` 印「19/19 皆…居所宣稱與實況一致」——在它自己界定的範圍內為真，
# 但讀起來像整個類別已閉合。
#
# 判定面刻意窄：只有**帶 scope（`主檔`）或帶「現居」註記**的形態才算做出居所宣稱。
#   `見主檔 DEF-x`            → 宣稱在主檔
#   `見 DEF-x（現居 archive_NN）` → 宣稱在該 archive
#   `見 DEF-x`（兩者皆無）     → **不算宣稱**，刻意跳過（比照 crossref 閘門「沒有明確
#                              狀態宣稱就不強行判讀」的誠實劃界，強判等同瞎猜）
# `(?<!立帳)` 是為了不與判準④ 重複報同一處（`立帳見…` 由判準④ 全權管）。
# ⚠️ 時態性敘述不會被誤收：實測家族內「**5 列刻意留在主檔**：`DEF-101-460`…」、
# 「`archive_27` 標頭與主檔 DEF-101-493」這類**當時決策紀錄**都沒有 `見` 緊接 `主檔`，
# 本樣式對它們零命中（若把樣式放寬成「主檔 … DEF-x」，這些歷史紀錄會全部翻紅，
# 而歷史檔是逐字保全的 ⇒ 閘門永紅，那是壞的失敗模式）。
NONVERB_RESIDENCE_RE = re.compile(
    r"(?<!立帳)見\s*(?P<scope>主檔)?\s*[`*]{0,2}(?P<id>DEF-\d+-\d+)[`*]{0,2}"
    r"(?:（現居\s*[`*]{0,2}(?P<archive>archive_\d+)[`*]{0,2}）)?"
)

# ------------------------------------------- 判準⑥ 第三種方言：**裸**「現居」（SA-R60R3-05）
# 🔴 結構論證（SA 完整方言普查的結論，值得逐字留著）：`立帳見` 有 `POINTER_VERB` 這道
# 硬要求（動詞在、後面沒跟可解析 ID 即紅，正是 ARCH-R60-01③ 的修法），但**真正承載
# 「居所」語意的 token 其實是「現居」，而它沒有對等的硬要求**。於是不帶 `見` 動詞的裸
# `現居 archive_NN`（例如「本列 …，現居 archive_27」）兩道正則皆不命中 ⇒ 注入失實宣稱
# `--check` 回 rc=0、零訊號。磁碟現況此形態**零命中**（實查全部 `現居 archive_NN` 都長在
# `見`／`立帳見` 構句內）⇒ 是 **latent 缺口**，但結構上一直開著。
#
# 為何對「現居」下硬要求是安全的，而對「見」不是（判準⑥ docstring 原本的反對理由）：
# `見` 是中文常用單字，對它下硬要求會把整個 repo 的散文變成錯誤；`現居` 不是——實查
# 稽核面內它**只**出現在居所敘述裡。故本項對它比照 `POINTER_VERB` 立硬要求。
RESIDENCE_TOKEN = "現居"
BARE_RESIDENCE_RE = re.compile(
    r"現居\s*[`*]{0,2}(?P<archive>archive_\d+)[`*]{0,2}"
)
# 「鄰近」＝同一行、該註記**之前**最靠近的可解析 DEF-ID，且中間相隔不超過視窗字數。
_NEARBY_ID_RE = re.compile(r"[`*]{0,2}(?P<id>DEF-\d+-\d+)[`*]{0,2}")
_BARE_RESIDENCE_ID_WINDOW = 40
#
# ⚠️ **誠實劃界（勿誤讀為「現居 全類別已閉合」）**：本樣式只認 `現居` 緊接
# `archive_<數字>` 的形態。刻意**不**擴及兩種相近寫法，各有理由：
#   · `現居 [`AutoSDD_Defect_Log_archive_NN.md`](連結)`（完整檔名 ＋ markdown 連結）——
#     主檔現有一處，它是對「本輪**一批**已結條目」的集合式指路，**沒有**單一 DEF-ID 可
#     供比對；硬要求會當場製造誤紅，而那句話本身並非對某個 ID 的居所宣稱。
#   · `現居 archive_NN`（字面 `NN`，非數字）——那是**引述本判準語法本身**的寫法，
#     家族與治理文件內多處在講判準時這樣寫，不是宣稱。
# 這兩種若哪天真的被拿來夾帶失實宣稱，本項抓不到；記在這裡以免下一輪誤以為已覆蓋。



def criteria_sentence() -> str:
    """把 `CHECK_CRITERIA` 攤成一句「本次稽核查了哪幾件事」——成功訊息的唯一來源。

    P7-4：手寫這句話的版本曾與實作脫節（成功訊息與 archive 標頭各說各話）。生成之後
    「宣稱的項數」與「登記的項數」在結構上不可能不一致。
    """
    return "、".join(
        f"({i}){label}：{desc}" for i, (label, desc) in enumerate(CHECK_CRITERIA, 1)
    )


def move_criteria_sentence() -> str:
    """把 `MOVE_CRITERIA` 攤成一句（`apply()` 寫進 archive 標頭用）。"""
    return "／".join(f"{_CIRCLED[i]}{c}" for i, c in enumerate(MOVE_CRITERIA))


def _no_layout_problem(name: str, n_rows: int) -> str:
    """「有缺陷列卻查無合格表頭」的 fail-loud 訊息（判準(7) 與 `plan()` 共用）。

    刻意**不**退回 `cells[-1]`／`cells[0]` 位置猜測：那正是「狀態欄空白時靜默位移到分流
    去向欄」的成因（見模組 docstring 的 Pkg-P7 段）。零缺陷列的檔不走這條路——家族內實查
    有一批純散文 archive（零表格列，實數以 `_family_files()` 現查為準），
    對它們要求表頭就是自製誤紅。
    """
    return (
        f"{name}：檔內有 {n_rows} 筆缺陷列卻查無合格表頭（需 `| ID | … | 狀態 | …` 形態）"
        "— 欄位定位失去依據，本工具拒絕退回位置猜測。請確認表頭未被改寫，或同步 "
        "check_defect_log_crossref 的 _HEADER_RE／_ID_HEADER／_STATUS_HEADER"
    )


def _status_claimed_ids() -> set[str]:
    """以閘門自身邏輯算出「真正被掃描目標做過可辨識狀態宣稱」的 ID 集合（判準③）。

    防呆：四份掃描目標必須全部存在。路徑打錯時會得到空集合，那個空集合讀起來與
    「沒有任何 ID 被宣稱」一模一樣，會讓所有列都通過判準③而誤搬（R59 主控第一版
    查詢即因漏接條件而誤列候選，故此處用顯式例外而非靜默回空）。
    """
    missing = [str(t) for t in gate._CROSSREF_TARGETS if not t.exists()]
    if missing:
        raise FileNotFoundError(f"crossref 掃描目標不存在，拒絕繼續（避免假結論誤搬）：{missing}")
    claimed: set[str] = set()
    for target in gate._CROSSREF_TARGETS:
        text = target.read_text(encoding="utf-8-sig")
        for m in gate._CLAIM_RE.finditer(text):
            if gate._classify(m.group(2)):
                claimed.update(gate._ID_RE.findall(m.group(1)))
    if not claimed:
        raise RuntimeError(
            "狀態宣稱集合為空 — 判準③ 的比對邏輯極可能已失效（掃描目標改版？），拒絕繼續"
        )
    return claimed


def active_status_hit(status_cell: str) -> re.Match[str] | None:
    """判準② 的實際判讀入口：**排除程式碼片段與角引號引述之後**再找活躍字樣（R68）。

    🔴 為何非收窄不可（DEF-101-676 實測，2026-08-01 於主檔 109 列現查）——判準② 原本是
    對整個狀態欄做裸掃描，於是把以下三類**與本列現況無關**的字元一律當成「本列還活著」：

      · **程式碼片段裡的 Python 內建函式 `open`**。實例 `DEF-101-391`：狀態欄寫
        `` fixed@R48：`python3 -c "import yaml; yaml.safe_load(open('...yml'))"` ``——
        命中的 `open` 是 `open()` 呼叫。`DEF-101-524` 同型（`open(..., newline="")`）。
        這與本判準 ASCII 邊界那一版要消滅的 `OpenMutexW` 誤報**完全同型**，只是逸出面
        從「英文字母相鄰」換成「反引號內」。
      · **引述本列自己被推翻的舊狀態**。實例 `DEF-101-554`：`` 本欄原文為「`open`（待
        主控還原）」…（污染已還原，後續輪不需再執行任何動作） ``；`DEF-101-581`：
        `` 原記狀態 `open（未指派）` ``。這些字面出現的用途正是**宣告它已不成立**，
        判準② 卻把它讀成「還成立」——語意剛好相反。
      · **在講別的 DEF-ID**。實例 `DEF-101-541`／`564`／`565`：`routed` 指的是被拆出去
        的另一列（`DEF-101-559` 等），不是本列。

    後果不是「多攔幾筆」而是**結構性死結**：這 16 筆全是 `_classify` 已判已結（fixed／
    closed-by-decision）、只被判準② 一項擋住的列，合計 **39705 bytes** 永久卡在主檔，
    使輪替吞吐趨近零、主檔單調逼近 256KB 硬線（DEF-101-676）。

    收窄手法刻意**復用本工具既有基元**（`_CODE_SPAN_RE`／`_CORNER_QUOTE_RE`，判準④⑥
    已在用），不另寫一套規則——否則就是製造第二份說法，重演 P7-4「兩份清單」病。

    🔴 **鑑別力不得因此流失**，三道保留：
      (a) 裸散文裡的活躍字樣照樣命中（未加反引號、未加角引號者一律算數）；
      (b) 判準① 仍先要求狀態欄首詞分類為已結，本判準只是第二層；
      (c) 判準④（`HANDOFF_PROSE_RE`：下輪／留待／解鎖條件／承接者／改派／backlog／
          deferred）完全不受本次收窄影響，且它掃的是**整列**而非狀態欄——真正的活交棒
          仍會被攔下要求 `--ack-handoff` 具名承認。實測本次放行的 6 筆中，`DEF-101-521`
          （backlog）／`524`（解鎖條件）／`554`（backlog）三筆仍落在判準④ 手上。
    對應機械鎖：`tools/tests/test_defect_log_capacity_policy_r68.py::TestCriterion2Narrowing`
    """
    masked = list(status_cell)
    for pattern in (_CODE_SPAN_RE, _CORNER_QUOTE_RE):
        for m in pattern.finditer(status_cell):
            # 以空白覆蓋（等長置換，保住 offset 與長度，便於報告引用原字串位置）
            for i in range(m.start(), m.end()):
                masked[i] = " "
    return ACTIVE_STATUS_RE.search("".join(masked))


def classify_row(line: str, claimed: set[str], layout: tuple[int, int, int]) -> dict:
    """對單一表格列套用搬遷判準 ①②⑤，回傳結構化裁決（④ 由 `plan()` 依 ack 判）。

    `layout` ＝ `gate._table_layout()` 回傳的 `(表頭欄數, ID 欄索引, 狀態欄索引)`。
    🔴 **必須由呼叫端傳入而不是在此猜**：狀態欄一律由**表頭欄名**定位，不再取 `cells[-1]`
    ——後者在狀態欄留空時會靜默位移到左邊的「分流去向」欄，實測讓一列「狀態欄空白 ＋ 分流
    去向寫『已於上游 fixed 故不另修』」被判成 `cls='fixed'`、`blockers=[]` ⇒ **可搬**
    （見模組 docstring 的 Pkg-P7 段；本檔會真的把它寫進 archive，不只是讀錯）。
    """
    ncols, id_idx, status_idx = layout
    cells = gate._row_cells(line)
    def_id = cells[id_idx] if id_idx < len(cells) else ""
    if len(cells) != ncols:
        # 判準⑤：欄數對不上表頭 ⇒ 狀態欄位置不可信任，一律**不判讀狀態、不可搬**。
        # 這正是「新搬進來的壞列硬擋」那一半（判準(7) 管既有列，本分支管搬遷動作本身）。
        return {
            "id": def_id, "line": line, "bytes": len(line.encode("utf-8")), "cls": None,
            "blockers": [f"⑤該列切出 {len(cells)} 欄 ≠ 表頭 {ncols} 欄"
                         "（欄位定位失效，狀態不判讀；欄內字面豎線須寫成 `\\|`）"],
            "handoff_marker": None,
        }
    status_cell = cells[status_idx]
    cls = gate._classify(status_cell)
    active = active_status_hit(status_cell)
    handoff = HANDOFF_PROSE_RE.search(line)
    blockers: list[str] = []
    if cls not in CLOSED_CLASSES:
        blockers.append(f"①狀態分類非已結（cls={cls}）")
    if active:
        blockers.append(f"②狀態欄含活躍字樣 {active.group(0)!r}"
                        "（已排除程式碼片段與角引號引述後仍命中）")
    # 🔴 判準③ 自 R68 起**不再是 blocker**（DEF-101-676）：`def_id in claimed` 只保留為
    # `--plan` 的資訊欄位，不進 `blockers`。WHY 見 MOVE_CRITERIA 第③項；一句話版本＝
    # 「被宣稱過」從來就不是不該搬的理由，真正的理由是「搬走後宣稱會解析不到」，而那個
    # 缺口已在 `check_defect_log_crossref._load_archive_status()` 補上（主檔 ∪ archive）。
    return {
        "id": def_id,
        "line": line,
        "bytes": len(line.encode("utf-8")),
        "cls": cls,
        "blockers": blockers,
        "handoff_marker": handoff.group(0) if handoff else None,
        # 判準③ 的資訊欄位（非 blocker，R68）：搬走這一列時，掃描目標內對它的狀態宣稱
        # 會改由 archive fallback 解析——`--check` 判準(8) 逐筆驗這件事真的成立。
        "claimed": def_id in claimed,
    }


def load_rows(text: str) -> list[str]:
    """該份帳本檔的缺陷表格列。ID 欄由**表頭**定位；查無合格表頭一律回空清單（不猜位置）。

    回空而非拋例外，是因為家族內實查有一批**零表格列**的純散文 archive
    （實數現查，不寫死）；「有列卻沒表頭」
    這個真異常由判準(7) 與 `plan()` 各自 fail-loud（見 `_no_layout_problem()`）。
    """
    layout = gate._table_layout(text)
    if layout is None:
        return []
    return [ln for ln in text.splitlines()
            if gate._ROW_RE.match(ln) and _row_id(ln, layout) is not None]


def _row_id(line: str, layout: tuple[int, int, int]) -> str | None:
    """取該列 ID 欄（索引由表頭定位，非 `cells[0]`）；欄數不足或非 ID 形態回 None。"""
    id_idx = layout[1]
    cells = gate._row_cells(line)
    if id_idx >= len(cells):
        return None
    return cells[id_idx] if gate._ID_RE.fullmatch(cells[id_idx]) else None


def plan(ack: frozenset[str] = frozenset()) -> dict:
    claimed = _status_claimed_ids()
    text = _LEDGER.read_text(encoding="utf-8-sig")
    layout = gate._table_layout(text)
    if layout is None:
        # 主檔沒有表頭就沒有欄位定位依據，而 `plan()` 的下游是**就地覆寫主檔**的 `apply()`。
        raise RuntimeError(_no_layout_problem(
            _LEDGER.name, sum(1 for ln in text.splitlines() if gate._ROW_RE.match(ln))))
    verdicts = [classify_row(ln, claimed, layout) for ln in load_rows(text)]
    # 判準⑥（DEF-101-612，指針反向依賴）：只讀一次全部稽核面全文，供下面逐列查詢
    # 「有沒有別的檔宣稱這個 ID 現居主檔」——這正是判準①②③⑤ 完全看不到的那一面
    # （它們只看該列自身狀態），也是 R60 `--apply` 搬走 529／555／558 後 11 處指針
    # 同時失實的根本成因（見 `MOVE_CRITERIA` 上方 WHY）。
    pointer_texts = _read_pointer_audit_texts()
    movable, needs_ack, blocked = [], [], []
    for v in verdicts:
        if v["blockers"]:
            blocked.append(v)
            continue
        if v["handoff_marker"] and v["id"] not in ack:
            needs_ack.append(v)
            continue
        claims = _external_residence_claims_for(v["id"], pointer_texts)
        if claims:
            # 硬擋、不接受 `--ack` 繞過（WHY 見 `MOVE_CRITERIA` 上方註解）：這與判準④
            # 的交棒偵測不同——交棒是主觀判斷，指針居所是可驗證的事實陳述。
            v["blockers"] = [
                "⑥有外部居所指針宣稱本列現居主檔，搬遷會使其立即失實（指針反向依賴，"
                "DEF-101-612）：" + "；".join(claims)
                + "。請先把該指針訂正為正確居所（或改寫成「現居 archive_NN」指向即將"
                "建立的目的檔），此列才會回到可搬狀態"
            ]
            blocked.append(v)
            continue
        movable.append(v)
    movable.sort(key=lambda v: -v["bytes"])
    return {
        "claimed_count": len(claimed),
        "movable_claimed": sum(1 for v in movable if v["claimed"]),
        "total_rows": len(verdicts),
        "movable": movable,
        "needs_ack": needs_ack,
        "blocked": blocked,
        "ledger_bytes": _LEDGER.stat().st_size,
    }


def _print_plan(p: dict) -> None:
    print(f"帳本主檔 {p['ledger_bytes']} bytes｜表格列 {p['total_rows']} 筆"
          f"｜judge 線 warn={gate._LEDGER_WARN_BYTES} fail={gate._LEDGER_FAIL_BYTES}")
    print(f"判準③ 實算：{p['claimed_count']} 個 ID 被掃描目標做過可辨識狀態宣稱"
          f"（R68 起**不再是 blocker**；其中 {p['movable_claimed']} 個落在本次可搬清單，"
          "搬後由帳本家族 archive fallback 解析，`--check` 判準(8) 逐筆驗證）")
    total = sum(v["bytes"] for v in p["movable"])
    after = p["ledger_bytes"] - total
    headroom = gate._LEDGER_FAIL_BYTES - after
    print(f"\n可搬（①②③⑤⑥ 判準全過）：{len(p['movable'])} 筆／{total} bytes"
          f" → 搬後主檔約 {after} bytes")
    # DEF-101-676 的解鎖判準（R67 round 4 訂為可機械查）：搬後主檔距 fail 線 ≥ 10240。
    print(f"   距 fail 線 {headroom} bytes"
          f"｜DEF-101-676 解鎖判準（≥ {_UNLOCK_HEADROOM_BYTES}）："
          f"{'✅ 成立' if headroom >= _UNLOCK_HEADROOM_BYTES else '❌ 不成立'}")
    for v in p["movable"]:
        print(f"  {v['id']:<14} {v['bytes']:>6} B  cls={v['cls']}")
    print(f"\n⚠️  需具名承認（判準④ 散文帶交棒字樣）：{len(p['needs_ack'])} 筆")
    for v in p["needs_ack"]:
        print(f"  {v['id']:<14} {v['bytes']:>6} B  marker={v['handoff_marker']!r}"
              f"  → 確定已有承接者才加 --ack-handoff {v['id']}")
    print(f"\n不可搬：{len(p['blocked'])} 筆")
    for v in p["blocked"]:
        print(f"  {v['id']:<14} {'; '.join(v['blockers'])}")


def _family_files() -> list[Path]:
    """帳本家族＝主檔 ＋ 全部 archive（排序穩定）。稽核面 SSOT，勿在別處重列一份。"""
    return [_LEDGER, *sorted(_QUALITY_DIR.glob(_ARCHIVE_GLOB))]


def _pointer_audit_files() -> list[Path]:
    """判準④ 的指針稽核面＝帳本家族 ∪ 具名治理文件（單一 SSOT，工具內不另生 glob）。

    刻意與 `_family_files()` 分成兩支而不是把治理文件塞進家族：家族是**居所的定義處**
    （(2) 同檔 ID 唯一、(3) 跨檔狀態矛盾、(5) 歸檔索引涵蓋性都只對它成立），治理文件
    只是**會寫出指針宣稱的地方**。若把兩者混為一談，治理文件裡任何 `| DEF-xxx |` 形狀
    的表格列都會被當成一筆缺陷紀錄，居所判定當場失真。
    """
    return [*_family_files(), *_GOVERNANCE_DOCS]


def _quotation_kind(line: str, idx: int, in_fence: bool = False,
                    governance: bool = False) -> str | None:
    """該處「立帳見」是否屬硬要求的四種例外；回傳例外種類供列印，非例外回 None。

    種類字串會出現在 `--check` 的引述清單裡，讓讀者一眼看出這處是憑哪一條被豁免
    （見 `_CODE_SPAN_RE` 上方註解的 (甲)(乙)(丙)(丁) 與「為何不是豁免口」）。

    `in_fence`＝該行落在 ``` 圍籬區塊內（由 `_fenced_line_numbers()` 算，跨行狀態）。
    `governance`＝該檔屬 `_GOVERNANCE_DOCS`；只有這種檔才適用例外 (丁)，帳本家族內的
    無 ID 散句必須維持硬錯誤（ARCH-R60-01 ③ 的原始缺陷型）。(丁) 的判定放在呼叫端
    （那裡才知道這一處有沒有跟得上可解析 DEF-ID），本函式只負責 (甲)(乙)(丙)。
    """
    if in_fence:
        return "``` 圍籬區塊內（逐字重現原文／工具輸出）"
    if any(m.start() <= idx < m.end() for m in _CODE_SPAN_RE.finditer(line)):
        return "code span 引述"
    if line[idx + len(POINTER_VERB):].startswith(_TERM_MENTION_SUFFIXES):
        return "術語提及（「立帳見」／『立帳見』）"
    return None


def _in_corner_quotes(line: str, idx: int) -> bool:
    """該處是否落在同一行的成對「」／『』內 —— 例外 (丁) 收窄後的必要條件（SA-R60R3-06）。

    刻意與 `_quotation_kind()` 的 (甲) code span 用同一種判定形狀（掃出成對區間、看位置
    落不落在區間內）：兩者守的是同一個直覺——「這是在提及一個語法」必須有**看得見的
    刻意標記**，而不是靠「後面剛好沒跟 ID」這種缺席條件。
    """
    return any(m.start() <= idx < m.end() for m in _CORNER_QUOTE_RE.finditer(line))


def _fenced_line_numbers(text: str) -> set[int]:
    """回傳落在 ``` 圍籬區塊內的行號（1-based；圍籬行自身也算）。

    判準(4) 的例外 (丙) ＋ 判準(6) 的對稱例外用（P7-4 訂正：原註寫「判準⑦ 用」，
    而第(7)項「家族專用語法反向鎖」是 round 2 被主控推翻的方案(乙)、程式早已刪除，
    這行註解是收斂不完整的殘留；現行第(7)項是表格列欄數）。
    圍籬區塊是**逐字保全的工具輸出／原文重現**，把它當宣稱會逼人改寫真實的
    實測輸出（本輪 `CrossPlatform_R60_Fix_Evidence.md` 的「修復前／修復後」計數區塊內
    就逐字重現了三處舊的失實寫法，那是證據不是宣稱）。與 `_quotation_kind()` 的 (甲)
    inline code span 同一個原理，只是圍籬跨行、必須用行狀態機才判得出來。
    """
    inside, out = False, set()
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            out.add(lineno)
            inside = not inside
            continue
        if inside:
            out.add(lineno)
    return out


def _pointer_problems(src: Path, m: re.Match, where: dict[str, list[str]],
                      lineno: int) -> list[str]:
    """驗一處居所指針（判準④ 的「立帳見…」或判準⑥ 的「見主檔…」）宣稱與實況是否一致。"""
    target, archive = m.group("id"), m.group("archive")
    actual = where.get(target) or []
    if archive:
        expected, claim = f"AutoSDD_Defect_Log_{archive}.md", f"「現居 {archive}」註記"
    elif m.group("scope") == "本表":
        expected, claim = src.name, "「本表」scope"
    else:
        expected, claim = _LEDGER.name, "「主檔」scope（無 scope 字樣者同此）"
    if expected in actual:
        return []
    hint = f"實居 {actual}" if actual else "全帳本家族查無此 ID"
    return [
        f"{src.name}:{lineno}：居所指針「{m.group(0)}」失實 — 依{claim}，該 ID 應在 "
        f"{expected}，{hint}。該 ID 若已歸檔，請改寫為「見 {target}（現居 archive_NN）」"
        "——此形態仍會被本稽核驗證，改成無 ID 散句只會讓檢查失效（已被硬要求擋下）"
    ]


def _bare_residence_problems(src: Path, m: re.Match, line: str,
                             where: dict[str, list[str]], lineno: int) -> list[str]:
    """驗一處**裸**「現居 archive_NN」（前方無 `見`／`立帳見` 動詞）；判準⑥ 的硬要求那半。

    與 `_pointer_problems()` 分開寫，是因為兩者拿 ID 的方式不同：那支的 ID 由正則自己
    的 `id` 群組給（形態完整），本支必須**回頭找**同一行前方最靠近的可解析 DEF-ID
    ——找不到就是「宣稱了居所卻無物可稽核」，比照 `POINTER_VERB` 的硬要求判為錯誤。
    """
    archive = m.group("archive")
    expected = f"AutoSDD_Defect_Log_{archive}.md"
    near = [
        im for im in _NEARBY_ID_RE.finditer(line)
        if im.end() <= m.start() and m.start() - im.end() <= _BARE_RESIDENCE_ID_WINDOW
    ]
    if not near:
        return [
            f"{src.name}:{lineno}：「{RESIDENCE_TOKEN}」居所註記「{m.group(0)}」前方同一行 "
            f"{_BARE_RESIDENCE_ID_WINDOW} 字內找不到可解析的 DEF-ID（原文片段 "
            f"{line[max(0, m.start() - 30):m.start() + 24]!r}）。宣稱了居所卻無物可稽核"
            "＝失實時零訊號，與「立帳見」後不跟 ID 是同一個形狀。請改寫為"
            "「見 DEF-xxx-xxx（現居 archive_NN）」這種本稽核驗得動的形態"
        ]
    target = near[-1].group("id")
    actual = where.get(target) or []
    if expected in actual:
        return []
    hint = f"實居 {actual}" if actual else "全帳本家族查無此 ID"
    return [
        f"{src.name}:{lineno}：居所註記「{m.group(0)}」失實 — 依「{RESIDENCE_TOKEN}」註記，"
        f"其前方最鄰近的 {target} 應在 {expected}，{hint}。"
        "此形態不帶「見」動詞，判準④／⑥ 的完整形態正則皆不命中，故由本硬要求接手"
    ]


def _read_pointer_audit_texts() -> dict[str, str]:
    """讀出 `_pointer_audit_files()`（帳本家族 ∪ 具名治理文件）全部檔案的全文。

    `plan()` 判準⑥（指針反向依賴，DEF-101-612）的讀檔入口。缺檔一律 fail-loud
    （比照 `_status_claimed_ids()` 的既有防呆姿態）：稽核面若與磁碟脫節卻靜默略過，
    等同悄悄拔掉一份檔的指針反向依賴檢查——那正是本項要消滅的病的另一種形狀。
    """
    missing = [str(p) for p in _pointer_audit_files() if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"指針反向依賴檢查的稽核面缺檔，拒絕繼續（避免悄悄漏面）：{missing}"
        )
    return {p.name: p.read_text(encoding="utf-8-sig") for p in _pointer_audit_files()}


def _external_residence_claims_for(def_id: str, texts: dict[str, str]) -> list[str]:
    """回傳 `texts`（`_pointer_audit_files()` 讀出的 `{檔名: 全文}`）中，現況宣稱
    `def_id` 目前居所為**主檔**的指針描述清單（`file:line：原文`）；空清單＝目前無人
    做出這類宣稱，搬走它不會讓任何既有指針當場失實。

    判準⑥（`plan()`，DEF-101-612「指針反向依賴」）：`check()` 只能在搬遷**之後**抓到
    「某指針宣稱的居所與實況不符」；本函式把同一組掃描基元搬到搬遷**之前**——`plan()`
    據此把這種列直接判為不可搬，而不是任由 `--apply` 先搬、留給下一次 `--check` 事後
    才報紅（R60 實際發生：`--apply` 搬走 `DEF-101-529`／`555`／`558` 後 11 處居所指針
    同時失實，詳見 `MOVE_CRITERIA` 上方的 WHY）。

    **刻意不重寫掃描規則**：呼叫的是 `check()` 判準(4)(6) 已在用的同一批基元
    （`POINTER_RE`／`NONVERB_RESIDENCE_RE`／`_quotation_kind`／`_fenced_line_numbers`／
    `_CODE_SPAN_RE`），否則帳本／治理文件內逐字引用判準語法的段落會被本函式誤判為對
    某 ID 的真實居所宣稱，重演 Pkg-P12「載具自己假紅」的形狀。

    只回傳「宣稱居所 == 主檔」的出現處（裸『現居 archive_NN』恆為 archive 宣稱，
    與主檔居所無關，不掃；`_pointer_problems()` 已印證這點——它的 `expected` 只要見到
    `archive` 群組就直接採信）：
      · `立帳見`（`POINTER_RE`）：`archive` 群組為空，且 scope ∈ {None, 主檔, 缺陷帳本}，
        或 scope == 本表 且該行所在檔本身就是主檔（`_pointer_problems()` 的同一條規則）。
      · `見主檔`（`NONVERB_RESIDENCE_RE`）：`archive` 群組為空且 `scope == 主檔`
        （`見 DEF-x` 無 scope／archive 者是單純引用、非宣稱，同 `check()` 既有的
        誠實劃界，見該正則上方 docstring）。
    """
    hits: list[str] = []
    for fname, text in texts.items():
        fenced = _fenced_line_numbers(text)
        for lineno, line in enumerate(text.splitlines(), 1):
            if POINTER_VERB in line:
                for m in POINTER_RE.finditer(line):
                    if m.group("id") != def_id or m.group("archive"):
                        continue
                    if _quotation_kind(line, m.start(), in_fence=lineno in fenced) is not None:
                        continue  # (甲)(乙)(丙) 引述／術語提及／圍籬，非宣稱
                    if m.group("scope") == "本表" and fname != _LEDGER.name:
                        continue  # 宣稱「這份文件裡」，而這份文件不是主檔
                    hits.append(f"{fname}:{lineno}：「{m.group(0)}」（立帳見・宣稱現居主檔）")
            for m in NONVERB_RESIDENCE_RE.finditer(line):
                if (m.group("id") != def_id or m.group("archive")
                        or m.group("scope") != "主檔" or lineno in fenced):
                    continue
                spans = [(sp.start(), sp.end()) for sp in _CODE_SPAN_RE.finditer(line)]
                if any(s <= m.start() < e for s, e in spans):
                    continue  # code span 引述，非宣稱
                hits.append(f"{fname}:{lineno}：「{m.group(0)}」（見主檔・宣稱現居主檔）")
    return hits


def check() -> int:
    """事後保全稽核。逐項定義如下，**每一項都是實作**。

    🔴 項數與各項標題一律以 `CHECK_CRITERIA` 為**唯一**真相源（P7-4）：成功訊息與 `apply()`
    寫進 archive 標頭的散文都由該常數生成，本 docstring 的 `(N) 標題` 則被
    `TestCriteriaListIsASingleSsot` 逐項雙向綁定。故此處**刻意不寫「共 N 項」的數字**——
    那會是第二個 stale 站點，而第(7)項曾經是被推翻的方案(乙)反向鎖、刪了程式卻留著散文，
    正是這種寫死數字的清單腐化出來的（見 `CHECK_CRITERIA` 上方的 WHY）。

      (1) 行尾  — 帳本家族每一份檔在磁碟上不得含 CR（.gitattributes 宣告 eol=lf）
      (2) 重複列 — 同一 ID 在**同一份檔**內不得出現兩列
      (3) 跨檔矛盾 — 同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話
      (4) 立帳指針 — 帳本家族**每一份檔**內每一處「立帳見」都必須跟得上可解析的
          DEF-ID（硬要求），且該 ID 的實際居所必須與指針宣稱一致。例外共四種
          （(甲) 動詞落在 inline code span 內＝引述語法；(乙) 動詞後緊接 `」`＝術語提及；
          (丙) 落在 ``` 圍籬區塊內＝逐字重現的原文／工具輸出；(丁) **僅限治理文件**內
          未跟可解析 DEF-ID **且落在同一行「」／『』內**的提及＝談論這個語法本身），
          且例外**每次執行都逐處列印**，不得靜默——見 `_CODE_SPAN_RE` 上方說明。
          (丁) 的引號要求為 round 3 收窄（SA-R60R3-06；ARCH／SD 判定「未重開缺陷」、
          SA 判定「重開」，主控裁決採 SA 的收窄，三方判斷逐字記在該處）
      (5) 歸檔索引涵蓋性 — 磁碟上每一支 archive 都必須在歸檔索引檔（R69 前為主檔）有一條
          以它為主體的 bullet，且 bullet 數 == 實查 archive 檔數（雙向：多出的
          bullet 也是失實）。**份數刻意不與中文數詞比對**：主檔那句「N 檔」在這份
          檔案已 stale 過三次（R56 註自己就記著「原寫二十一檔在 HEAD 時點即已
          stale」），故份數改為由本判準現場核算，散文不再寫死
      (6) 非「立帳見」方言的居所宣稱 — `見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）`
          同樣要驗居所。SA-R60R2-03：`archive_26` 的「見主檔 `DEF-101-481`」比
          `立帳見` 少兩個字就完全逸出判準④，而稽核照印「19/19 皆…一致」。
          🔴 稽核面自 round 3（P7-5）起與判準(4) **同一份 SSOT**（`_pointer_audit_files()`）：
          先前它只掃 `_family_files()`，於是治理文件裡的同一形態**零檢查**。實測重現
          （沙箱複本、未動 tracked 檔）：在治理文件寫一句非 code span、非圍籬的
          `見主檔 DEF-101-481`（該 ID 實居 archive_27）⇒ `NONVERB_RESIDENCE_RE` 命中、
          而 `check()` 仍回 rc=0、零訊號。例外沿用判準(4) 的 (甲) code span ＋ (丙) 圍籬
          （同一個 WHY：圍籬與 code span 內是逐字重現的工具輸出／原文，是證據不是宣稱；
          實測現行治理文件的命中全數落在這兩種例外內 ⇒ 擴面後零誤紅）。
          **刻意不設 (丁) 對等例外**：(丁) 是為了「動詞在、卻沒跟 ID」這種硬要求誤報而開，
          而本項的 `NONVERB_RESIDENCE_RE` 沒有 ID 就根本不命中（`見` 是常用單字，對它下
          硬要求會把整個 repo 的中文散文都變成錯誤），故該例外在本項無對應物可開。
          🔴 **第三種方言的硬要求（round 3，SA-R60R3-05）**：不帶「見」動詞的裸
          `現居 archive_NN` 兩道正則皆不命中 ⇒ 注入失實宣稱時 rc=0、零訊號。真正承載
          居所語意的 token 是「現居」，故對它比照 `POINTER_VERB` 立**對等硬要求**：凡出現
          該字樣，同一行前方視窗內必須跟得上可解析 DEF-ID 且居所一致，例外沿用 (甲)(丙)。
          對「現居」下硬要求安全、對「見」不安全的差別在於它不是中文常用單字（實查稽核面
          內只出現在居所敘述裡）。未涵蓋的兩種相近寫法逐條記在 `BARE_RESIDENCE_RE` 上方
      (7) 表格列欄數 — 每一列切出的欄數必須等於**該檔表頭**欄數（`gate.row_arity_problems()`，
          檢查本體在閘門，本檔不寫第二份）。這是 (2)(3) 與搬遷判準的**前提**：欄數對不上時
          表頭索引會指到別欄，而修復前一句話都不會說。archive 側既有異常列由
          `_ARITY_BASELINE` 具名基線處置（逐檔列印、只准往下改、stale 即紅），
          **主檔與新建 archive 零豁免**
      (8) 跨檔宣稱可解析 — 四份 crossref 掃描目標內的**每一句**可辨識狀態宣稱，都必須能
          在帳本家族（主檔 ∪ archive）解析到該 ID，且解析出的狀態分類與宣稱一致
          （R68，DEF-101-676）。這是搬遷判準③ 由「被宣稱過就硬擋」改寫為「搬後仍解析
          得到」之後，那個事後條件的**實作本體**——沒有它，判準③ 的改寫就只是一句斷言。
          解析面由 `gate._load_ledger_status()`（主檔）＋ `gate._load_archive_status()`
          （全部 archive，各自用自己的表頭定位）組成，比對本體直接呼叫 `gate._scan_target()`
          （**不寫第二份宣稱解析**，理由同 (7) 的欄數檢查）。掃描目標不齊時一律報問題，
          不以「沒跑」冒充「通過」
    判準④ 的稽核面自 round 2（ARCH-R60R2-05）起＝`_pointer_audit_files()`＝帳本家族
    ∪ 具名治理文件（`_GOVERNANCE_DOCS`）。**不是**「禁止家族外使用該語法」——那個
    方案（主控初裁）會讓治理文件裡的指針完全失去居所稽核，等於把偵測面一起丟掉；
    改採擴面後例外多一種 (丁)（治理文件內未跟 DEF-ID 的提及＝談論語法，放行但列印），
    家族內同一形態維持硬錯誤

    🔴 措辭紀律（R60 round 1 SD-R60-02）：前一版印「N 個 ID 無重複」卻**從未檢查
    重複**——在主檔注入同 ID 重複列後 rc=0 且照樣印那句話。也在 docstring 宣稱查
    「列不重複不遺失」，而「不遺失」根本無法在事後單檔稽核中判定（需要搬遷前基線，
    那是 `apply()` 的 `conservation_problems()` 在管）。宣稱一道檢查存在而它沒寫，
    與本工具立帳要消滅的病（宣稱存在而不可重跑）同型，故本輪二選一走「真的實作」。
    同一條紀律在 round 2 又抓到三個「範圍內為真、讀起來像類別已閉合」的成功訊息
    （缺的正是後來補上的判準(5)(6) 與判準④ 的治理文件稽核面）：所以成功訊息現在逐項
    列出每一件事，講不出來的就不准出現在那句話裡（現在那句話由 `CHECK_CRITERIA` 生成，
    所以「訊息宣稱的項數」與「常數登記的項數」在結構上不可能不一致）。

    🔴 **`governance` 分流（round 3，勿誤放寬）**：例外 (丁) 只對 `_GOVERNANCE_DOCS`
    開放，帳本家族內「動詞後未跟可解析 DEF-ID」維持**硬錯誤**——那正是 ARCH-R60-01 ③
    的原始缺陷型。把 (丁) 下沉進 `_quotation_kind()` 會讓它失去「後面有沒有 ID」這個
    資訊、於是必然一起豁免掉家族內的散句，故該判定刻意留在本函式（呼叫端）。
    """
    problems: list[str] = []
    files = _family_files()
    if _LEDGER.name in _ARITY_BASELINE:
        problems.append(
            f"_ARITY_BASELINE 為主檔 {_LEDGER.name} 登記了欄數異常豁免 — 結構性禁止："
            "主檔是唯一會新增／接收表格列的檔，替它開豁免就等於把判準(7) 的硬擋面拆掉"
            "（歷史列不追溯、新列硬擋的邊界就靠『主檔零豁免』撐住）"
        )

    # (1) 行尾
    for p in files:
        raw = p.read_bytes()
        if b"\r" in raw:
            problems.append(f"{p.name}：磁碟實體含 CR（{raw.count(bytes([13]))} 處），"
                            "違反 .gitattributes 的 eol=lf；寫檔請走 bytes 層或 newline=''")

    # (2)(3)(4) 共用的資料收集：逐檔解析表格列，記下每個 ID 出現在哪些檔（含同檔重複，
    #     故用 list 不用 set）、各檔的狀態分類，以及各檔全文（指針稽核要用）。
    #
    #     (3) 的判準：同一 ID 若同時存在主檔與 archive，兩邊的**狀態分類**不得互相矛盾。
    #     刻意不把「同時存在」本身當問題——那是本帳本的合法樣式：主檔留一列 live 追蹤樁、
    #     archive 存完整史料，樁的狀態欄會明寫「（archive_NN …段）」指路
    #     （實例：`DEF-42-001` 主檔 routed 樁 ↔ archive_01 完整記錄，兩者狀態一致）。
    #     真正該抓的是**兩邊各說各話**（例如主檔還寫 open、archive 已記 fixed），
    #     這正是 R60 在 `DEF-101-434` 撞到的形態：主檔停在 `open（deferred）`，
    #     而其結案記錄 `DEF-101-490`（「DEF-101-434 至此結案，原 open→fixed@R57」）
    #     隨 archive_27 歸檔，只讀主檔者（含 crossref 閘門）一律誤判為未修。
    #
    #     🔴 全文一次讀進 `texts`，稽核面＝`_pointer_audit_files()`（家族 ∪ 治理文件）：
    #     判準(4) 與 (6) 都要用治理文件全文（P7-5 起兩者共用同一份稽核面 SSOT），
    #     而 (1)(2)(3)(5)(7) 只跑家族。缺檔一律 fail-loud，不得靜默跳過。
    where: dict[str, list[str]] = {}
    status_by: dict[str, dict[str, str | None]] = {}
    texts: dict[str, str] = {}
    layouts: dict[str, tuple[int, int, int] | None] = {}
    #     欄數對不上表頭的列：狀態欄位置不可信任 ⇒ (3) 一律跳過該 (ID, 檔) 組合，
    #     由判準(7) 專責報它。不這樣分工的話同一列會同時被 (3) 誤報成「跨檔矛盾」。
    unreadable: set[tuple[str, str]] = set()
    for p in _pointer_audit_files():
        if not p.exists():
            problems.append(
                f"{p} 不存在 — 稽核面已與磁碟脫節，拒絕靜默跳過"
                "（跳過就等於這一份檔上的指針稽核被悄悄拿掉）"
            )
            continue
        texts[p.name] = p.read_text(encoding="utf-8-sig")
    for p in files:
        if p.name not in texts:
            continue
        layouts[p.name] = layout = gate._table_layout(texts[p.name])
        if layout is None:
            continue  # 零表格列的純散文 archive（家族內實查有一批）；有列卻沒表頭由 (7) fail-loud
        for ln in load_rows(texts[p.name]):
            def_id = _row_id(ln, layout)
            where.setdefault(def_id, []).append(p.name)
            cells = gate._row_cells(ln)
            ok = len(cells) == layout[0]
            if not ok:
                unreadable.add((def_id, p.name))
            status_by.setdefault(def_id, {})[p.name] = (
                gate._classify(cells[layout[2]]) if ok else None
            )

    # (2) 同檔內 ID 唯一 —— `where[id]` 出現同一檔名 ≥2 次即重複列。
    #     重複列會讓 crossref 閘門的「有效狀態紀錄」計數與歸檔守恆算式同時失真，
    #     且前一版的 (3) 段對 `files=[主檔,主檔]` 會走進空迭代 → 零 problem（SD-R60-02）。
    for def_id, homes in sorted(where.items()):
        for fname in sorted(set(homes)):
            if homes.count(fname) > 1:
                problems.append(
                    f"{def_id}：在 {fname} 內出現 {homes.count(fname)} 列 — 同檔內 ID 必須"
                    "唯一。重複列會讓 crossref 閘門的有效狀態紀錄計數與歸檔的位元組／列數"
                    "守恆算式同時失真（R45 判例：誤歸檔 3 筆 open 列）"
                )

    # (3) 跨檔狀態分類不得矛盾
    for def_id, homes in sorted(where.items()):
        if _LEDGER.name not in homes or len(set(homes)) == 1:
            continue
        if (def_id, _LEDGER.name) in unreadable:
            continue
        main_cls = status_by[def_id][_LEDGER.name]
        for fname in sorted({f for f in homes if f != _LEDGER.name}):
            if (def_id, fname) in unreadable:
                continue
            if status_by[def_id][fname] != main_cls:
                problems.append(
                    f"{def_id}：主檔狀態分類為 {main_cls!r}，但 {fname} 記為 "
                    f"{status_by[def_id][fname]!r} — 兩邊各說各話，只讀主檔者會誤判"
                )

    # (4)「立帳見 …」指針：稽核面是**帳本家族每一份檔**（不只主檔），且「立帳見」
    #     後面必須跟得上可解析的 DEF-ID（硬要求）。歸檔動作會讓既有指針當場失實，
    #     而 R60 round 1 前的版本只掃主檔、又不認 `立帳見主檔`，兩處失實指針因此
    #     長期逃過稽核（ARCH-R60-01；archive_26／27 → DEF-101-493 實居 archive_28）。
    #     逐行掃（不掃全文）：指針不跨行，逐行才能給出精確行號，也才能判斷動詞是否
    #     落在該行的 inline code span 內。
    #     🔴 round 2 ARCH-R60R2-05：稽核面由「帳本家族」擴為 `_pointer_audit_files()`
    #     ＝家族 ∪ 具名治理文件。裁決過程留在此處以免下一輪重辯：主控最初裁定方案(乙)
    #     「立帳見＝家族專用語法、家族外一律禁用」，隨後**自己推翻**——(乙) 會讓那兩處
    #     指針**完全失去居所稽核**，而 ARCH 的證據正指出 `DEF-101-555` 是待 R61 承接的
    #     活列，一旦被搬走該句就靜默失實（與 archive_26/27 → `DEF-101-493` 同一劇本，
    #     而 493 正是 ARCH-R60-01 的原始案例）。把語法禁掉＝把偵測面一起丟掉，故改採
    #     (甲) 擴面：scope 增收 `缺陷帳本`、稽核面納入治理文件、例外 (丁) 只對治理文件
    #     開放（家族內的無 ID 散句維持硬錯誤）。
    pointer_count = 0
    quoted: list[str] = []
    governance_names = {p.name for p in _GOVERNANCE_DOCS}
    fences: dict[str, set[int]] = {}
    for p in _pointer_audit_files():
        if p.name not in texts:
            continue  # 缺檔已在上方資料收集處 fail-loud，不重複報同一件事
        text = texts[p.name]
        is_governance = p.name in governance_names
        fences[p.name] = fenced = _fenced_line_numbers(text)
        for lineno, line in enumerate(text.splitlines(), 1):
            if POINTER_VERB not in line:
                continue
            by_start = {m.start(): m for m in POINTER_RE.finditer(line)}
            idx = line.find(POINTER_VERB)
            while idx != -1:
                m = by_start.get(idx)
                kind = _quotation_kind(line, idx, in_fence=lineno in fenced,
                                      governance=is_governance)
                if kind is not None:
                    quoted.append(f"{p.name}:{lineno}  [{kind}] {line[idx:idx + 30]!r}")
                elif m is not None:
                    pointer_count += 1
                    problems.extend(_pointer_problems(p, m, where, lineno))
                elif is_governance and _in_corner_quotes(line, idx):
                    # 例外 (丁)：治理文件裡「立帳見」後未跟可解析 DEF-ID、**且落在同一行的
                    # 「」／『』內** ＝在**談論**這個語法（本 repo 的治理文件本來就要談它），
                    # 不是做出宣稱。放行但逐處列印。家族內同一形態維持硬錯誤（下方 else）
                    # ——ARCH-R60-01 ③ 的原始缺陷型。引號要求為 round 3 收窄（SA-R60R3-06，
                    # 主控裁決；ARCH／SD 判定相反，理由記在 `_CODE_SPAN_RE` 上方 (丁) 條）。
                    quoted.append(f"{p.name}:{lineno}  [(丁) 治理文件內非宣稱提及"
                                  f"（未跟 DEF-ID，落在「」／『』內）] {line[idx:idx + 30]!r}")
                else:
                    hint = (
                        "；本檔屬具名治理文件，若這裡是在**提及**這個語法而非做出宣稱，"
                        "請把整段提及放進同一行的「」或『』內（例外 (丁) 自 round 3 起"
                        "要求引號——未加引號的散句與真宣稱長得一模一樣）"
                        if is_governance else ""
                    )
                    problems.append(
                        f"{p.name}:{lineno}：「{POINTER_VERB}」後未跟可解析的 DEF-ID"
                        f"（原文片段 {line[idx:idx + 24]!r}）。無 ID 散句會讓本稽核對該指針"
                        "完全失效，請補上具體 ID：「立帳見主檔 DEF-xxx-xxx」／"
                        "「立帳見 DEF-xxx-xxx（現居 archive_NN）」；若這裡是**引述判準語法**"
                        f"而非做出指針宣稱，請用 markdown inline code（反引號）包住整段引文{hint}"
                    )
                idx = line.find(POINTER_VERB, idx + 1)

    # (5) 歸檔索引涵蓋性 —— 掃描面沿用 `_family_files()`（不新增掃描面），比對的是
    #     「磁碟上有哪些 archive」對「索引檔登記了哪些」。R60 收輪前人工建了
    #     `archive_31` 卻沒登記，而當時的四項判準完全不看索引段，`--check` 照印 rc=0；
    #     主檔標題還寫死「**三十檔**」。份數一律現場核算，不與中文數詞比對（見 docstring (5)）。
    #     🔴 R69 `DEF-101-734`：索引段已外移，bullet 解析對象改為索引檔；該檔本身以**檔名
    #     常數**（非「零表格列」這種會吞掉真事故的模糊判準）自 archive 清單排除——它是目錄
    #     不是史料檔，要求它替自己登記 bullet 是自我指涉的假需求。
    archives = [p.name for p in files if p.name not in (_LEDGER.name, _ARCHIVE_INDEX_NAME)]
    if _ARCHIVE_INDEX_NAME not in texts:
        problems.append(
            f"{_ARCHIVE_INDEX_NAME} 不存在 — 歸檔索引段自 R69（DEF-101-734）起外移至該檔，"
            "缺檔＝判準⑤ 失去比對對象。拒絕靜默退化成「零 bullet 也算通過」"
            "（上方稽核面缺檔硬閘應已先報一次；本句是判準⑤ 自己的第二道防線）"
        )
    bullets = index_bullet_lines(texts.get(_ARCHIVE_INDEX_NAME, ""))
    listed = [name for _, name in bullets]
    for name in archives:
        if name not in listed:
            problems.append(
                f"{name}：磁碟上存在，但 {_ARCHIVE_INDEX_NAME} 索引段查無以它為主體的 "
                f"bullet（樣式 `> - **`{name}`**（…）：…`）。歸檔而不登記＝該批史料在"
                "帳本的目錄上不存在，讀者只看主檔會以為它沒發生；`--apply` 現在會自動"
                "註冊，人工歸檔請補上這一條"
            )
    for name in listed:
        if name not in archives:
            problems.append(
                f"索引段登記了 `{name}` 的 bullet，但 {_QUALITY_DIR} 下查無此檔 — "
                "索引指向不存在的 archive（改名／刪檔？），比對雙向都必須成立"
            )
    if len(bullets) != len(archives):
        problems.append(
            f"歸檔索引 bullet 數 {len(bullets)} ≠ 實查 archive 檔數 {len(archives)} — "
            "索引段與磁碟實況不符。份數不寫死在散文裡（現場核算），故此處不比對中文數詞"
        )

    # (6) 非「立帳見」方言的居所宣稱（SA-R60R2-03）——樣式與跳過條件見 NONVERB_RESIDENCE_RE。
    #     🔴 P7-5：稽核面由 `_family_files()` 改為 `_pointer_audit_files()`，與判準(4) 共用
    #     同一份 SSOT。原本兩者不對稱＝治理文件裡的同一形態**零檢查**（沙箱實測：治理文件寫
    #     一句非 code span、非圍籬的失實 `見主檔 DEF-101-481` ⇒ 正則命中、check() 仍 rc=0）。
    #     例外沿用判準(4) 的 (甲) code span ＋ (丙) 圍籬：同一個 WHY（兩者內都是逐字重現的
    #     工具輸出／原文＝證據，不是宣稱），實測現行治理文件的命中全落在這兩種例外內、
    #     家族側的命中則零處落在圍籬 ⇒ 補上 (丙) 對家族既有稽核面零削弱（各面實數現查，
    #     `--check` 的引述清單每次執行都逐處列印）。
    #     刻意不設 (丁) 對等例外（WHY 見 docstring (6)：沒有 ID 就根本不命中，無物可豁免）。
    #     🔴 SA-R60R3-05（本輪新增的第三種方言）：不帶 `見` 動詞的**裸**「現居 archive_NN」
    #     兩道正則皆不命中 ⇒ 注入失實宣稱零訊號。真正承載居所語意的 token 是「現居」，
    #     而它先前沒有 `立帳見` 那樣的硬要求。故本項第二段對它立對等硬要求：凡出現該字樣，
    #     鄰近必須跟得上可解析 DEF-ID 且居所一致；例外沿用 (甲) code span ＋ (丙) 圍籬。
    #     已被上方完整形態（判準④／⑥ 的正則）涵蓋到的那一處一律跳過，避免同一處報兩次。
    nonverb_count = 0
    bare_residence_count = 0
    for p in _pointer_audit_files():
        if p.name not in texts:
            continue
        fenced = fences.get(p.name) or _fenced_line_numbers(texts[p.name])
        for lineno, line in enumerate(texts[p.name].splitlines(), 1):
            spans = [(sp.start(), sp.end()) for sp in _CODE_SPAN_RE.finditer(line)]
            covered: list[tuple[int, int]] = []
            for m in NONVERB_RESIDENCE_RE.finditer(line):
                covered.append((m.start(), m.end()))
                if not (m.group("scope") or m.group("archive")):
                    continue  # 「見 DEF-x」＝單純引用，未做居所宣稱（誠實劃界，不強判）
                if lineno in fenced:
                    quoted.append(f"{p.name}:{lineno}  [``` 圍籬區塊內（判準(6) 形態）] "
                                  f"{m.group(0)!r}")
                    continue
                if any(s <= m.start() < e for s, e in spans):
                    quoted.append(f"{p.name}:{lineno}  [code span 引述（判準(6) 形態）] "
                                  f"{m.group(0)!r}")
                    continue
                nonverb_count += 1
                problems.extend(_pointer_problems(p, m, where, lineno))
            covered.extend((m.start(), m.end()) for m in POINTER_RE.finditer(line))
            for m in BARE_RESIDENCE_RE.finditer(line):
                if any(s <= m.start() < e for s, e in covered):
                    continue  # 已由判準④／⑥ 的完整形態管，不重複報同一處
                if lineno in fenced:
                    quoted.append(f"{p.name}:{lineno}  [``` 圍籬區塊內（裸「"
                                  f"{RESIDENCE_TOKEN}」形態）] {m.group(0)!r}")
                    continue
                if any(s <= m.start() < e for s, e in spans):
                    quoted.append(f"{p.name}:{lineno}  [code span 引述（裸「"
                                  f"{RESIDENCE_TOKEN}」形態）] {m.group(0)!r}")
                    continue
                bare_residence_count += 1
                problems.extend(_bare_residence_problems(p, m, line, where, lineno))

    # (7) 表格列欄數 == 該檔表頭欄數。檢查本體一律用閘門的純函式 `gate.row_arity_problems()`
    #     ——本檔**不寫第二份**（Pkg-P7 的整個立意就是切欄／欄位定位只准有一份實作）。
    #     archive 側既有異常列走 `_ARITY_BASELINE` 具名基線（筆數以該表為唯一真相源；
    #     處置理由與「歷史列不追溯、
    #     新列硬擋」為何結構上成立，見該常數上方）。
    waived_arity: list[str] = []
    for p in files:
        if p.name not in texts:
            continue
        text = texts[p.name]
        if layouts.get(p.name) is None:
            n_rows = sum(1 for ln in text.splitlines() if gate._ROW_RE.match(ln))
            if n_rows:
                problems.append(_no_layout_problem(p.name, n_rows))
            continue
        found = gate.row_arity_problems(text)
        waived_n = _ARITY_BASELINE.get(p.name, 0)
        if len(found) > waived_n:
            for pb in found:
                problems.append(f"{p.name}：{pb}")
            problems.append(
                f"{p.name}：欄數異常的表格列實測 {len(found)} 筆 > 具名基線 {waived_n} 筆"
                "（基線＝`DEF-101-560` 逐筆具名不修的既有 archive 列）— 新增或搬進來的列"
                "一律硬擋：請把該列欄內的字面豎線轉義成 `\\|`。**不要**改大 _ARITY_BASELINE，"
                "那個字典只准往下改（既有列修好就減、歸零就刪整筆）"
            )
        elif len(found) < waived_n:
            problems.append(
                f"{p.name}：_ARITY_BASELINE 登記 {waived_n} 筆欄數異常列，實測只有 "
                f"{len(found)} 筆（stale 自檢）— 有人修好了其中幾列卻沒回收登記。請把 "
                f"_ARITY_BASELINE[{p.name!r}] 改成 {len(found)}（為 0 時整筆刪掉）。"
                "豁免只准因為「還沒修」存在，不准因為「沒人記得回收」存在"
            )
        elif waived_n:
            waived_arity.append(
                f"{p.name}：{waived_n} 筆表格列欄數 ≠ 表頭欄數，屬 `DEF-101-560` 具名不修"
                "的既有史料列（狀態一律不判讀）"
            )
    for name in _ARITY_BASELINE:
        if name not in {p.name for p in files}:
            problems.append(
                f"_ARITY_BASELINE 登記了 {name}，但帳本家族查無此檔 — 登記與磁碟脫節"
                "（改名／刪檔？）。stale 登記會讓下一支同名檔一落地就自帶豁免"
            )

    # (8) 跨檔宣稱可解析（R68，DEF-101-676）——搬遷判準③ 改寫後的事後條件本體。
    #     刻意**直接呼叫閘門的 `_scan_target()`**（而非另寫一份宣稱解析）：判準③ 當初就是
    #     用 `gate._CLAIM_RE`／`gate._classify` 算出「被宣稱過」的，事後條件若改用第二份
    #     實作，兩邊對「什麼算一句宣稱」的認定一旦分歧，這道網就會在自己看不見的地方破洞。
    claim_problems: list[str] = []
    if all(t.exists() for t in gate._CROSSREF_TARGETS):
        main_status = gate._load_ledger_status()
        arch_status = gate._load_archive_status()
        for target in gate._CROSSREF_TARGETS:
            claim_problems.extend(gate._scan_target(target, main_status, arch_status))
        problems.extend(f"跨檔宣稱：{c}" for c in claim_problems)
        print(f"ℹ️  判準(8) 實算：主檔 {len(main_status)} 列 ＋ archive "
              f"{len(arch_status)} 列＝帳本家族解析面；四份掃描目標的狀態宣稱"
              f"{'全部可解析且一致' if not claim_problems else f'有 {len(claim_problems)} 筆問題'}")
    else:
        problems.append(
            "判準(8) 無法執行：crossref 掃描目標不齊 —— 拒絕以「沒跑」冒充「通過」"
            f"（缺：{[str(t) for t in gate._CROSSREF_TARGETS if not t.exists()]}）"
        )

    # 判準(7) 的具名基線逐檔列印（每次執行都印）——同下方引述清單的理由：豁免看得見。
    if waived_arity:
        print(f"ℹ️  {len(waived_arity)} 份 archive 帶具名的欄數異常基線"
              "（逐檔列出以免靜默豁免；主檔與新建 archive 零豁免）：")
        for w in waived_arity:
            print(f"  · {w}")

    # 引述／豁免逐處列印（每次執行都印，無論通過與否）——比照 check_pytest_baseline_sites.py
    # 的 `baseline-ok:` 豁免稽核慣例：豁免必須看得見，才不會變成靜默豁免口。
    if quoted:
        print(f"ℹ️  {len(quoted)} 處「{POINTER_VERB}」／居所指針字樣屬引述或非宣稱提及"
              "（code span／``` 圍籬／術語提及／未跟 DEF-ID），視為談論判準而非做出宣稱，"
              "未稽核其居所（逐處列出以免靜默豁免）：")
        for q in quoted:
            print(f"  · {q}")

    if problems:
        print(f"❌ 帳本保全稽核不通過（{len(problems)} 筆）：", file=sys.stderr)
        for pb in problems:
            print(f"  - {pb}", file=sys.stderr)
        return 1
    print(f"✅ 帳本保全稽核通過（{len(files)} 檔／{len(where)} 個 ID／"
          f"{pointer_count} 個「立帳見」指針＋{nonverb_count} 個「見主檔／現居」居所指針"
          f"＋{bare_residence_count} 個裸「{RESIDENCE_TOKEN}」居所註記"
          f"＋{len(quoted)} 處引述；歸檔索引 {len(bullets)} 條 bullet 對 "
          f"{len(archives)} 支 archive）：{criteria_sentence()}；"
          f"判準(4)(6) 稽核面含 {len(_GOVERNANCE_DOCS)} 份具名治理文件（scope `缺陷帳本`）")
    return 0


def conservation_problems(orig_text: str, new_main: str, move_lines: list[str],
                          expected_rows: int, released: int, added: int = 0) -> list[str]:
    """`apply()` 落地前的四項資料完整性不變量 — 純函式，回傳問題清單（空＝全部成立）。

    `added` ＝本次寫入**主動加進主檔**的位元組數（目前唯一來源是判準⑤ 的歸檔索引
    bullet：`apply()` 自己會把它寫進主檔）。**WHY 要把它算進帳而不是繞過守恆**：
    位元組守恆式原本是 `新主檔 + 釋出 == 舊主檔`，`apply()` 一旦自己往主檔加東西，
    這條式子就會被自己的新寫入破掉；此時有兩條路——(a) 把守恆檢查移到插入 bullet
    之前（＝那段新寫入從此零保全，正是本工具立帳要消滅的形狀），或 (b) 把新增量
    顯式列進算式。走 (b)：式子改為 `新主檔 + 釋出 == 舊主檔 + 新增`，於是「bullet
    的長度」本身也被守恆管著——bullet 少寫一個字、或除了 bullet 之外還偷偷改了主檔
    別的地方，都會讓這條不變量不成立而拒絕落地。`added` 預設 0 使既有呼叫端與
    構造輸入測試不受影響。

    🔴 為何**不用 `assert`**（R60 round 1 ARCH-R60-07／SD-R60-07／QA-R60-08）：
    `python -O`／`PYTHONOPTIMIZE=1` 會把 assert 整條編譯掉，而 `apply()` 緊接著就
    `write_bytes()` **就地覆寫帳本主檔**——保全在一個解譯器旗標下整組消失、工具照寫
    不誤（複審實測 `python -O tools/archive_defect_log.py --plan` 可正常啟動、
    `python -O -c "assert False"` rc=0）。一支「立帳理由就是『宣稱的機械檢查必須真的
    會執行』」的工具，其根治手段自己可被環境變數關掉，是同類風險。

    抽成純函式的第二個理由是**可直接以構造輸入測到**：不必真的破壞一份帳本，就能
    驗這四條有沒有牙（見 `tools/tests/test_archive_defect_log.py`
    `TestConservationGuardsAreExplicitNotAssert`，該鎖另以 AST 斷言本檔零 `assert`）。
    """
    problems: list[str] = []
    got_rows = len(load_rows(new_main))
    if got_rows != expected_rows:
        problems.append(f"列數不守恆：搬後主檔 {got_rows} 列，應為 {expected_rows} 列")
    for ln in move_lines:
        if ln not in orig_text:
            problems.append(f"搬出的列在原主檔中找不到逐字對應：{ln[:70]!r}")
        if ln in new_main:
            problems.append(f"該列未從主檔移除：{ln[:70]!r}")
    got_bytes = len(new_main.encode("utf-8")) + released
    want_bytes = len(orig_text.encode("utf-8")) + added
    if got_bytes != want_bytes:
        problems.append(
            f"位元組總量不守恆：搬後主檔 {len(new_main.encode('utf-8'))} + 釋出 {released}"
            f" = {got_bytes} ≠ 原主檔 {len(orig_text.encode('utf-8'))} + 新增 {added}"
            f" = {want_bytes}"
        )
    return problems


def _index_bullet(dest: Path, move_ids: list[str], orig_bytes: int, released: int,
                  archive_bytes: int, needs_ack: list[dict], note: str) -> str:
    """組出該次歸檔的索引 bullet（體例照 archive_30 那條；R69 起寫進歸檔索引檔）。

    載明：建立時點／筆數／ID 清單／bytes 變化／判準④ 攔下哪幾筆／操作備註。

    🔴 刻意**不寫「搬後主檔 N bytes」**：本 bullet 自己就要寫進主檔，寫上去之前算不出
    搬後實數（循環依賴），而用「先算再插」湊一個數字必然差在 bullet 自身長度上。
    故只寫「搬前」與「釋出」（兩者在此刻皆為確定值），搬後實數指向工具實跑——這與帳本
    「不對餘裕做定性宣稱／不快照可漂移數字」的既有紀律同向（R59 SA-R59-P2-1）。
    """
    held = "、".join(f"`{v['id']}`" for v in needs_ack) or "（無）"
    return (
        f"> - **`{dest.name}`**（`tools/archive_defect_log.py --apply` 於 "
        f"{_date.today().isoformat()} 建立，{archive_bytes} bytes）："
        f"**{len(move_ids)} 筆已結列**逐字搬移"
        f"（{'／'.join(move_ids)}）。"
        f"**位元組變化**：搬前主檔 {orig_bytes} bytes、本次釋出 {released} bytes"
        f"（搬後實數以 `python tools/check_defect_log_crossref.py` 實跑為權威——本 bullet"
        f"自身的寫入也計入主檔體積，故不在此寫死搬後數字）。"
        f"**判準④ 攔下、刻意未加 `--ack-handoff` 而留在主檔者**：{held}。"
        f"**本次操作備註**：{note}"
    )


def apply(archive_num: int, ack: frozenset[str], header_note: str) -> int:
    dest = _QUALITY_DIR / f"AutoSDD_Defect_Log_archive_{archive_num:02d}.md"
    if dest.exists():
        print(f"❌ {dest.name} 已存在，拒絕覆蓋", file=sys.stderr)
        return 1
    p = plan(ack)
    if not p["movable"]:
        print("❌ 無任何可搬列，拒絕產生空 archive", file=sys.stderr)
        return 1

    orig = _LEDGER.read_bytes()
    text = orig.decode("utf-8-sig" if orig.startswith(b"\xef\xbb\xbf") else "utf-8")
    if "\r" in text:
        print("❌ 主檔磁碟實體含 CR，請先正規化為 LF 再歸檔（避免搬遷混入行尾變動）",
              file=sys.stderr)
        return 1

    move_lines = [v["line"] for v in p["movable"]]
    move_ids = [v["id"] for v in p["movable"]]
    released = sum(len(ln.encode("utf-8")) + 1 for ln in move_lines)  # +1 ＝該列的 LF

    kept = [ln for ln in text.split("\n") if ln not in set(move_lines)]
    rows_removed = "\n".join(kept)

    # 🔴 判準清單一律由 `MOVE_CRITERIA`／`CHECK_CRITERIA` 生成，**不得手寫**（P7-4）：
    # archive 是零刪除的史料檔，手寫清單一旦與實作脫節，每次 `--apply` 都會把那份失實宣稱
    # 複製成一份新的永久紀錄（本輪實際發生過：第(7)項「家族專用語法反向鎖」程式已刪、
    # 標頭仍寫「共七項」並照舊列出它）。
    header = (
        f"# AutoSDD Defect Log — Archive {archive_num}\n\n"
        f"> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 **{len(move_ids)} 筆已結列**。\n>\n"
        f"> **搬遷判準的權威來源是 `tools/archive_defect_log.py`**"
        f"（程式即判準，本標頭不重述細則）。\n"
        f"> 該工具落實 {len(MOVE_CRITERIA)} 項搬遷判準（{move_criteria_sentence()}），\n"
        f"> 並在落地後以 `--check` 稽核 {len(CHECK_CRITERIA)} 項保全判準："
        f"{criteria_sentence()}\n"
        f"> （本段由該檔的 `MOVE_CRITERIA`／`CHECK_CRITERIA` 常數機械生成，逐項定義見\n"
        f"> `check()` docstring；**勿手改**——手寫版曾與實作脫節而被複製成永久史料）。\n"
        f"> **歷輪標頭曾宣稱有這樣一支腳本但 repo 內無載具**，\n"
        f"> 且散文所載判準與實際執行的判準不一致——R60 起改為引用可重跑的工具，"
        f"見該檔 docstring。\n>\n"
        f"> **搬遷清單**：{'、'.join(f'`{i}`' for i in move_ids)}\n>\n"
        f"> **本次操作備註**：{header_note}\n>\n"
        f"> 餘裕一律以 `python tools/check_defect_log_crossref.py` 的實跑訊號為權威，\n"
        f"> 本標頭**不對餘裕做定性宣稱**"
        f"（R59 SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被推翻）。\n>\n"
        f"> **原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。"
        f"查詢缺陷現況一律先看主檔缺陷總表。\n\n"
        f"## 缺陷總表（已結列，逐字保全）\n\n"
        f"| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |\n"
        f"|---|---|---|---|---|---|---|\n"
    )
    archive_body = (header + "\n".join(move_lines) + "\n").encode("utf-8")

    # 判準⑤ 的根因級修法：建立 archive 的同一支程式負責把索引 bullet 寫進索引檔，
    # 「歸檔完忘記更新索引」不再是一條靜默路徑。插入點＝索引段最後一條 bullet 之後。
    # 🔴 R69 DEF-101-734：bullet 的落點由主檔改為索引檔，故本次歸檔對主檔而言**只減不增**
    # （守恆式的 `added` 回到 0）。索引檔仍在家族體積守門內，差別在於它與缺陷總表**不再共用
    # 同一份餘裕**，而缺陷總表的餘裕才是「還能不能記下一筆缺陷」的那一個。
    new_main = rows_removed
    index_doc = ARCHIVE_INDEX_DOC()
    index_orig_bytes = index_doc.stat().st_size if index_doc.exists() else 0
    bullet = _index_bullet(dest, move_ids, len(orig), released, len(archive_body),
                           p["needs_ack"], header_note)
    bullet_bytes = len(bullet.encode("utf-8")) + 1
    new_index, index_problem = _ledger_index.prepare_index_insert(index_doc, bullet)
    if index_problem or new_index is None:
        print(f"❌ {index_problem}，**未寫入任何檔案**", file=sys.stderr)
        return 1

    # 保全不變量（顯式檢查 + return 1，**不是 assert** —— 見 conservation_problems 檔頭：
    # assert 在 python -O 下整組消失，而下一步就是就地覆寫帳本主檔）。
    # 🔴 `added=0`（R69 DEF-101-734）：bullet 已改寫進索引檔，主檔不再被 `apply()` 主動
    # 加東西，故守恆式回到最嚴的「新主檔 + 釋出 == 舊主檔」——主檔只要被多改一個字就紅。
    # bullet 那一側的守恆由上面索引檔的顯式檢查接手（兩邊都被管著，沒有無人看守的縫）。
    guard_problems = conservation_problems(
        text, new_main, move_lines, p["total_rows"] - len(move_ids), released,
        added=0,
    )
    if guard_problems:
        print(f"❌ 落地前保全不變量不成立（{len(guard_problems)} 筆），**未寫入任何檔案**：",
              file=sys.stderr)
        for pb in guard_problems:
            print(f"  - {pb}", file=sys.stderr)
        return 1

    # bytes 層寫入：不經 os.linesep 翻譯（Windows 上 write_text 會把 LF 變 CRLF）
    dest.write_bytes(archive_body)
    _LEDGER.write_bytes(new_main.encode("utf-8"))
    index_doc.write_bytes(new_index.encode("utf-8"))
    for p2 in (dest, _LEDGER, index_doc):
        if b"\r" in p2.read_bytes():
            print(f"❌ {p2.name} 落地後含 CR — 寫入路徑被 os.linesep 翻譯，落地檔已受污染；"
                  "請立即 git 還原後排查（同樣不用 assert：-O 下會整條消失）",
                  file=sys.stderr)
            return 1

    print(f"✅ {dest.name}：{len(move_ids)} 筆、{dest.stat().st_size} bytes")
    print(f"✅ 主檔 {len(orig)} → {_LEDGER.stat().st_size} bytes（釋出 {released}，"
          f"自 R69 起 bullet 不再寫進主檔故淨變動 == -{released}）")
    print(f"✅ {index_doc.name} {index_orig_bytes} → {index_doc.stat().st_size} bytes"
          f"（索引 bullet 新增 {bullet_bytes}）")
    print(f"✅ 已自動在 {index_doc.name} 登記索引 bullet（判準⑤）：{bullet[:60]}…")
    if p["needs_ack"]:
        print(f"ℹ️  {len(p['needs_ack'])} 筆因散文帶交棒字樣未搬："
              f"{', '.join(v['id'] for v in p['needs_ack'])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="缺陷帳本歸檔輪替工具")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true", help="乾跑：列出可搬／需承認／不可搬")
    g.add_argument("--apply", action="store_true", help="實際搬遷")
    g.add_argument("--check", action="store_true", help="事後保全稽核")
    ap.add_argument("--archive-num", type=int, help="--apply 時的 archive 編號")
    ap.add_argument("--ack-handoff", default="",
                    help="逗號分隔的 DEF-ID，具名承認搬遷帶交棒字樣的列")
    ap.add_argument("--note", default="（未填）", help="--apply 時寫入 archive 標頭的操作備註")
    a = ap.parse_args(argv)
    ack = frozenset(x.strip() for x in a.ack_handoff.split(",") if x.strip())

    if a.check:
        return check()
    if a.plan:
        _print_plan(plan(ack))
        return 0
    if a.archive_num is None:
        ap.error("--apply 需要 --archive-num")
    return apply(a.archive_num, ack, a.note)


if __name__ == "__main__":
    sys.exit(main())
