#!/usr/bin/env python3
"""ADR-XPLAT-001 §4.3 的 C1／C2 機械鎖（R60 ARCH-R60-05 ⑤ 的根治）。

🔴 本檔刻意寫成 `unittest.TestCase` 類別風格：根層四道閘門（`tools/run_root_unittests.py`
＋ pre-push root-infra leg ＋ `root-infra-ci.yml` ＋ 兩份 compat-ci）走的是 **unittest
discover**，pytest 函式風格的測試檔會被**整檔零收集**（R60 Scan-C 的 C-01 就是這個病）。

WHY（為何非得有這道鎖）：
  `docs/04_planning/ADR/ADR-XPLAT-001-…md` §4.3 訂了兩條「只動 LATEST 時的強制條件」——
  C1（known-gap 必須寫進 `ONBOARDING.md` §9）與 C2（帳本分流／狀態欄必須寫出重新評估的
  觸發條件）。**該 ADR 落地的同一輪（R60）就自己兩條全違反**（`DEF-101-534`／`552`），
  §4.3.4 當時也如實自陳「只有人工自檢，沒有機械鎖」。四方複審 ARCH-R60-05 的裁決是：
  「把 §4.3 的兩條件做成機械鎖才叫落地——沒有這道鎖，§4.3 就只是散文，本輪已經自證。」
  本檔就是那道鎖。

三件事（對應 ADR §4.3.4 逐字列的三點）：
  1. **判準與 ADR 散文雙向綁定**（`TestCriterionIsBoundToAdrProse`）：判準字樣與基線 ID 上界
     都不是本檔自己編的，是從 ADR §4.3.1／C2／§4.3.4 的句子裡**抽出來**再與本檔常數互相
     比對。ADR 改字而程式沒跟（或反之）→ 紅，並印出兩邊差集。這是為了避免本 repo 已犯過的
     「散文與程式各走各的」。
  2. **硬擋新列**（`TestHardBlockOnUnwaivedRows`）：落入 §4.3.1 而 C1／C2 未滿足的帳本列
     一律紅，逐列指名缺哪一項。合法出口有兩個：補齊條件，或依 §4.3.3 把狀態降為
     `partial@R<n>（§4.3 條件未滿足）`——**後者不需要任何豁免登記**。
     掃描面＝**帳本家族全檔**（主檔＋全部 archive，枚舉一律用 `archive_defect_log._family_files()`
     這個家族 SSOT）。WHY 見下方「射程」段：只掃主檔時「新增違規列＋同輪歸檔」可整條繞過。
  3. **具名基線豁免（grandfathered）＋三道防永久化自檢**（`TestBaselineWaiverHygiene`
     ＋ `TestShrinkOnlyRatchet`）。

🔴 為什麼採「具名基線豁免 ＋ 只對新列硬擋」而不是一上線就全紅（本檔最重要的設計說明）：
  本 ADR 是 R60 才寫成的，而落入 §4.3.1 的列大多在它之前（2026-07-09～07-26）就已判定；
  更關鍵的是 **C2 這條規則本身是 R60 寫 ADR 時，從 `DEF-101-056`／`057` 的既有寫法反推
  成明文的**——那批舊列成立時世界上還沒有這條要求，缺 C2 是規則追溯適用，不是當時漏辦。
  若鎖一上線就對全部舊列翻紅，下一個人會直接把鎖關掉／加 `@skip`，那道鎖就等於沒加，
  而且會連「硬擋新列」這個真正的價值一起賠掉。
  所以：舊列以**具名清單**登記（每筆必附「為何當時沒滿足」與「承接者」），新列一律硬擋。
  （筆數不寫在散文裡——`_BASELINE_WAIVERS` 自己就是唯一真相源，寫死數字只會多一個 stale
  站點，那正是同輪 SD-R60-08 抓到的病。本檔對這條規則的遵守由
  `TestThisLockObeysItsOwnNoHardcodedCountRule` 機械自檢——round 2 版本在宣告這條紀律的
  幾十行後自己就寫死了豁免筆數與帳本列數兩處，被 ARCH-R60R2-04／SD-R60-R2-06 逐字抓出。）

  ⚠️ 但「具名豁免」本身就是 R60 被四方拆穿的病灶（`test_ps_engine_ssot.py` 的
  `_PENDING_MIGRATION_SITES`：掛著 pending 名義、**刻意不加 stale 自檢**，於是事實上是
  永久豁免）。本表用三道自檢確保不重犯，三道都各有測試：
    (a) **stale 自檢**：被豁免的那一項一旦真的滿足了 → 紅，並指名「刪掉這筆登記」。
        豁免只能因為「條件還沒補」而存在，不能因為「沒人記得回收」而存在。
    (b) **基線 ID 上界**：每筆登記的帳本 ID 必須 ≤ `_BASELINE_ID_CEILING`（＝ADR 落地前的
        最後一筆列）。ADR 落地後開的列 ID 必然大於它 ⇒ **結構上不可能被塞進基線**。
        🔴 這裡原本是「發現日期 ≤ ADR 落地日」，round 3 改掉（SD-R60-R2-05 ①）：ADR 落地日
        與本輪全部新列的發現日期**是同一天**，嚴格大於比較對「同日新列」完全不設防——SD 以
        monkeypatch 實測「日期填落地日＋登記進表＋上限 +1」可讓全檔綠燈，那句「日界之後的
        新列在結構上不可能被塞進基線」對本輪自己的產出根本不成立。改用與日曆脫鉤的單調量
        （帳本 ID），同 `ADR-SD09-011` 把「源碼演進證據」從「日曆天數」解綁的先例。
    (c) **shrink-only 棘輪**：`_MAX_BASELINE_ENTRIES` 與 `_BASELINE_ID_CEILING` 皆只准往下改，
        由 `TestShrinkOnlyRatchet` 以 `git show HEAD:<本檔>` 取上一版常數機械比對。
        🔴 round 2 版本這一條只是**人審慣例冒充機制**：它只斷言「筆數 ≤ 上限」，SD 實測把
        上限改大**不會紅**（改小才紅）。現版才是真棘輪。

射程（scope，round 3 新增；SA-R60R2-04）：
  · **ADR 落地後的新列（ID > `_BASELINE_ID_CEILING`）＝家族全檔硬擋，且不接受任何豁免登記。**
    WHY：落入 §4.3.1 的列典型狀態是 `wontfix`，而 `tools/archive_defect_log.py` 判準① 對
    `wontfix` 是**允許搬遷**的 ⇒ 只掃主檔時，「新增一筆違規列＋同輪把它歸檔」可以完整繞過
    硬擋。把掃描面擴到家族全檔後這條路關掉。
  · **ADR 落地前的舊列**：在主檔者要嘛合規、要嘛具名登記（＝上面那張表）；已歸檔者不在射程。
  · SA 劃界誠實記錄：這個繞道面**在被發現時尚未被利用**——本包獨立以家族全檔重驗，落地後
    新列中落入 §4.3.1 者只有 `DEF-101-534` 且 C1／C2 皆已滿足；archive 側落入 §4.3.1 而條件
    未滿足者只有 `DEF-43-011`（archive_01）與 `DEF-101-357`（archive_22），兩者都遠早於 ADR
    落地、屬設計上不追溯範圍 ⇒ 擴面後零假紅。

判準邊界（誠實劃界，勿超譯——同 `test_defect_id_reference_integrity.py` 已劃的同型邊界）：
  ✅ C1 保證「該 `DEF-ID` 出現在 `ONBOARDING.md` §9 區段內」＝追溯鏈存在。§9 的表列與其
     下方「對應缺陷帳本」註腳都算——`DEF-101-003`／`004` 的 ID 就只寫在註腳裡，這是 §9
     既有的記法，也是 ADR C1 逐字點名的正例，判準必須容納它。
  ❌ 不保證那一列描述的就是同一個缺口（語意對應是人審責任）。
  ❌ C2 只保證「重新評估／屆時」字樣在，不保證那句觸發條件寫得好、寫得對。
  ❌ **ADR 落地前的 archive 列不在射程**（見上）。因此把一筆**已具名豁免的舊列**歸檔，會讓
     它離開射程並連帶要求刪掉登記——對已 grandfather 的列這是等價交換、不是新破口；但對
     **新列**歸檔無效（仍硬擋）。
  ❌ **ID 上界擋不住「兩個欄位同時造假」**：回填一個未用過的舊號碼、且把發現日期也填成上界
     列當天或更早，仍可繞過（鎖另以上界列自身的發現日期作輔助判準，只擋「舊號碼＋晚日期」
     這半）。要繞過得同時偽造帳本主鍵與日期，那在 diff 與 `check_defect_log_crossref.py`
     面前不是靜默動作。
  ❌ **shrink-only 棘輪在本檔的首個 commit 上是空轉的**（HEAD 還沒有本檔可比），該情形會
     `skipTest` 並印出理由（`run_root_unittests.py` 會逐處列印全部 skip）；鑑別力另以合成
     上一版永久釘住。
  ⚠️ **不要因為這道鎖是綠的就以為 §4.3 已被完全保證。**

執行：python tools/run_root_unittests.py
      python -m unittest tools.tests.test_adr_xplat001_c1c2_lock -v
"""
from __future__ import annotations

import ast
import inspect
import re
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "tools"))

# 帳本列的切格判準（跳脫 pipe 感知）與**帳本家族枚舉**一律用歸檔工具的 SSOT，不自寫第二份
# ——R60 SA 複審實測 naive `split('|')` 會把含 `\|` 的列誤判成 8~9 欄（帳本真有這種列）；
# 家族枚舉另有 ARCH-R60-09 的明文批評「一個 finding 一支鎖、掃描面各自為政」，故 `_family_files()`
# 是家族 SSOT，本檔只 import、不另寫 glob。
import archive_defect_log as ADL  # noqa: E402

_LEDGER = _REPO / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
MAIN_LEDGER_NAME = _LEDGER.name
_ONBOARDING = _REPO / "ONBOARDING.md"
_ADR = (_REPO / "docs" / "04_planning" / "ADR"
        / "ADR-XPLAT-001-copy-on-evolve-frozen-baseline-backport.md")

# ---------------------------------------------------------------- 判準常數（與 ADR 散文雙向綁定）
# 這三組字樣的**唯一權威來源是 ADR §4.3.1／C2 的句子**；`TestCriterionIsBoundToAdrProse`
# 會把 ADR 那幾句話裡的字樣抽出來與這裡逐字比對，任一邊被改動都會紅。
_FROZEN_TOKENS = ("凍結版", "凍結基線")
_WONTFIX_TOKENS = ("不回補", "wontfix")
_REEVAL_TOKENS = ("重新評估", "屆時")

# 帳本《格式定義》的欄位順序。這個 tuple 就是本檔對欄序的唯一宣告（原本是一行散文註解，
# 而散文與寫死索引之間沒有任何機械關係）：`TestHardBlockOnUnwaivedRows::
# test_column_indices_agree_with_the_real_ledger_header` 會把它與**主檔表頭現查**逐字比對，
# 並驗證下面每個索引常數確實指到它該指的欄名，兩邊漂移即紅。
# 🔴 第四欄逐字是 `現象與證據（file:line）`——被取代的那行散文註解寫的是「現象與證據」，
# 與磁碟上的真表頭**不符**。這道新斷言落地的第一次執行就把它抓出來（在真實資料上、非合成
# 情境），如實記錄：那正是「散文複本沒有機械關係就會靜默過期」的又一個現行樣本。
_COL_HEADERS = (
    "ID", "發現日期", "發現情境", "現象與證據（file:line）", "嚴重度", "分流去向", "狀態",
)
_N_COLS = 7
_IDX_ID, _IDX_DATE, _IDX_TRIAGE, _IDX_STATUS = 0, 1, 5, 6

# §4.3.3 的合法降級出口：狀態寫 `partial@R<n>` 且明示掛在 §4.3。
_PARTIAL_RE = re.compile(r"partial@R\d+")
_SECTION_43_MARK = "4.3"

# ONBOARDING §9 區段邊界（抽不到就 fail-loud，絕不靜默退化成空字串或全檔——
# 前者會讓所有列一起紅、後者會讓所有列一起假綠，兩種都是壞的失敗模式）。
_SEC9_HEAD = "## 9. "
_SEC9_END = "## 10."
# ADR §7「未結落差」區段邊界（provisional 登記必須在那裡有具名承接列）。
_ADR_SEC7_HEAD = "## 7. "
_ADR_SEC7_END = "## 8."

# 反空轉下限：帳本掃描面崩塌（正則寫壞／路徑錯／檔案被清空）時 fail-loud，不會靜默
# 「零違規」假綠。
# 🔴 round 3 改釘在**帳本家族總列數**而非主檔列數（SA-R60R2-04 ③）：主檔列數會因歸檔
# **結構性下降**，round 2 的主檔下限餘裕只剩個位數、再歸檔一次就會誤紅或失去鑑別力；
# 而家族總列數受帳本「只增不刪」政策 ＋ `archive_defect_log.conservation_problems()` 的
# 搬遷守恆保護，只增不減 ⇒ 下限釘在實測值之後，餘裕只會隨時間變大。
# 值＝R60 round 3 落地當下 `family_row_total(read_family())` 的實測結果，不做任何加減推算
# （同 `run_root_unittests.py::MIN_TESTS` 的「填實測值」重釘紀律）。
_MIN_FAMILY_ROWS = 665


class Row(NamedTuple):
    """帳本一列的取用視圖（只留判準要用的欄位）。"""

    def_id: str
    date: str
    triage: str
    status: str
    lineno: int


class Finding(NamedTuple):
    """家族掃描的一筆結果：這列住在哪一份檔、未滿足哪些條件。"""

    source: str
    row: Row
    unmet: frozenset[str]


class Waiver(NamedTuple):
    """基線豁免登記：豁免了哪幾項、為何當時沒滿足、由誰承接。"""

    waived: frozenset[str]
    why: str
    owner: str


_ID_KEY_RE = re.compile(r"^DEF-(\d+)-(\d+)$")


def _id_key(def_id: str) -> tuple[int, int]:
    """帳本 ID 的排序鍵（`DEF-<輪次>-<流水號>`，見帳本《格式定義》）。

    輪次號與流水號都隨時間單調遞增，故 `(輪次, 流水號)` 的字典序即「誰比較新」。
    這是本檔基線上界之所以能與日曆脫鉤的物理前提。
    """
    m = _ID_KEY_RE.match(def_id)
    if m is None:
        raise ValueError(f"非帳本 ID 形態：{def_id!r}（格式定義＝DEF-<輪次>-<流水號>）")
    return int(m.group(1)), int(m.group(2))


def _synthetic_id(round_no: int, seq: int) -> str:
    """組出「保證不是引用真實缺陷」的合成 ID，**刻意不在原始碼留字面**。

    `tools/tests/test_defect_id_reference_integrity.py` 會 `git grep --untracked` 全庫的
    DEF-ID 引用並要求每一個都在帳本家族有對應主鍵列，寫死合成號會讓那道鎖翻紅
    （本檔初版就是這樣被它抓到十幾處的——那道鎖有牙，如實記錄）。
    """
    return f"DEF-{round_no:02d}-{seq:03d}"


_OLD_ROW_C2_RETRO = (
    "R60 前的舊列：C1 已滿足（§9 表列／註腳逐字點名本 ID）。C2「必須寫出重新評估觸發條件」"
    "這條規則是 R60 寫 ADR-XPLAT-001 時，從 DEF-101-056／057 的既有寫法**反推**成明文的，"
    "本列成立時尚不存在此要求 ⇒ 缺 C2 是規則追溯適用的結果，不是當時漏辦。"
)
# 🔴 承接者一律寫成「承接輪次：**未指派**」＋可執行的觸發點：本輪新訂的硬規則②
# （`docs/06_quality/CrossPlatform_Scan_Dimensions.md`：任何 deferred／backlog 必須指向一個
# 存在的輪次或明確標為「未指派」）。round 2 寫的「下次觸及本列的輪次」是**非具名輪次**，
# 既不是存在的輪次也沒明標未指派，正是該規則要擋的形態。
_OLD_ROW_C2_OWNER = (
    "承接輪次：**未指派**（本登記無專屬承接輪；觸發點＝任何輪次下次觸及本列時，"
    "在分流或狀態欄順手補一句觸發條件——一行字，非專案級工作——並刪除本登記；"
    "stale 自檢會在補完的同時指名要刪的是哪一筆）"
)

# ---------------------------------------------------------------- 具名基線豁免（shrink-only）
# 🔴 加一筆進來之前先讀本檔檔頭「為什麼採具名基線豁免」那一段，以及：
#    ① 你的列若是 `_BASELINE_ID_CEILING` 之後才開的，**加不進來**（上界自檢會紅）；
#    ② 你有一條不需要任何豁免的合法出口＝ADR §4.3.3：狀態改寫成
#       `partial@R<n>（§4.3 條件未滿足）`。請走那條。
#
# `_BASELINE_ID_CEILING`＝ADR-XPLAT-001 落地前的最後一筆帳本列（R59 收尾列；下一號起就是
# R60＝落地本 ADR 的那一輪）。它同時寫在 ADR §4.3.4 並由本檔雙向比對，改一邊即紅。
# 兩個常數都只准往下改，由 `TestShrinkOnlyRatchet` 對 HEAD 版本機械比對（不是人審慣例）。
_BASELINE_ID_CEILING = "DEF-101-526"
_MAX_BASELINE_ENTRIES = 8

_BASELINE_WAIVERS: dict[str, Waiver] = {
    "DEF-101-003": Waiver(frozenset({"C2"}), _OLD_ROW_C2_RETRO, _OLD_ROW_C2_OWNER),
    "DEF-101-004": Waiver(frozenset({"C2"}), _OLD_ROW_C2_RETRO, _OLD_ROW_C2_OWNER),
    "DEF-101-019": Waiver(frozenset({"C2"}), _OLD_ROW_C2_RETRO, _OLD_ROW_C2_OWNER),
    "DEF-101-020": Waiver(frozenset({"C2"}), _OLD_ROW_C2_RETRO, _OLD_ROW_C2_OWNER),
    "DEF-101-040": Waiver(frozenset({"C2"}), _OLD_ROW_C2_RETRO, _OLD_ROW_C2_OWNER),
    "DEF-101-359": Waiver(frozenset({"C2"}), _OLD_ROW_C2_RETRO, _OLD_ROW_C2_OWNER),
    "DEF-101-324": Waiver(
        frozenset({"C1"}),
        "R60 前的舊列（2026-07-24）且**形態與 §4.3 不同**：本列是檔名淨化「多對一碰撞」的"
        " backlog，範圍是全 30 版（含 LATEST v0.30）一致存在，不是「LATEST 已修、凍結版殘留」"
        "——放進 §9〈凍結版豁免與平台限制〉表會是一列**假的**凍結版缺口。它之所以落入"
        " §4.3.1，是因為狀態欄引用了 DEF-101-358 的 wontfix 判例字樣。C2 本列自己已滿足"
        "（狀態欄逐字「本輪重新評估後確認此範圍擴大不改變既有 wontfix/backlog 定性」）。",
        "承接輪次：**未指派**（觸發點＝任何輪次下次檢視 DEF-101-324 的 backlog 時，二擇一"
        "——判定確實需要 §9 列則補列（並刪本登記）；或在 ADR §4.3.1 之外另立「全版本一致"
        "存在」的分類，使本列不再落入 §4.3）",
    ),
    "DEF-101-393": Waiver(
        frozenset({"C1", "C2"}),
        "R60 前的舊列（2026-07-26）且是**帳本記載完整性補記列**：它把 DEF-101-382 只記"
        " `.sh` 側的缺口補上 `.ps1` 側，現象欄逐字「套用同一 DEF-101-056/057 既有 wontfix"
        " 判例」——實質的 §9 列與重新評估條件都掛在 056／057 那兩列上（兩者 C1／C2 皆已滿足），"
        "本列自己沒有獨立的一組。P3 且明載「不影響任何現行測試/CI 判準」。",
        "承接輪次：**未指派**（觸發點＝任何輪次下次觸及 DEF-101-382／393 家族時，二擇一"
        "——把 `.ps1` 側併入 056／057 的 §9 列敘述並於本列補觸發條件；或為 `.ps1` 側補"
        "獨立 §9 列。兩者任一完成即刪本登記）",
    ),
}

# 🔴 R60 本輪自己的兩列（`DEF-101-534`／`DEF-101-552`）**刻意不在上表內**——它們是
# ARCH-R60-05 的原始標的，最後是「真的補齊」而不是「被 grandfather 掉」：
#   · `DEF-101-534`：C1（§9 表末列已回指本 ID）＋ C2（狀態欄列出重新評估觸發條件）
#     皆由帳本／ONBOARDING 獨佔包在本輪補齊，本鎖實測兩項皆通過。
#   · `DEF-101-552`：實查 `requires_docker_success` 在 v0.01~v0.29 **全部凍結版零命中**、
#     v0.30 才有（本包獨立以逐版 grep 覆核）⇒ 該缺陷**不存在凍結版落差**，§4.3 對它是 N/A
#     而非豁免，§9 不該為它虛構一列；該列敘述已據實訂正，因此不再落入 §4.3.1。
# 這兩筆一度以 provisional 形態登記在上表，本鎖的 stale 自檢在兩包落地的當下就翻紅並
# 逐字指名要刪哪一筆——**這道自檢的鑑別力是在真實資料上、非合成情境下被證實的**。
# 附帶意義：兩者的 ID 都在 `_BASELINE_ID_CEILING` 之後，改用 ID 上界後它們**結構上已不可能**
# 再被登記進表——round 2 的日期日界對它們（發現日期＝ADR 落地當日）完全不設防。


# ---------------------------------------------------------------- 判準本體（純函式，可直接呼叫）
def row_cells(line: str) -> list[str]:
    """把帳本表格列切成「位置對齊」的欄位串列（首尾的空格子已去掉，中間**不**丟）。

    切欄一律委派閘門 SSOT `ADL.gate._row_cells()`——它**保留空欄**，正是本鎖要的語意
    （判準讀的是分流去向欄與狀態欄的位置，中間任一欄留空而被濾掉就整排左移、改讀別欄）。
    本函式只負責去掉首尾那兩個空片段（`| a | b |` 切出 `['', 'a', 'b', '']`），讓索引與
    `_COL_HEADERS` 的欄序 0-based 對齊；`_row_cells()` 之所以保留首尾片段，是為了讓切片數
    能直接與表頭比對做 arity 檢查（那是閘門那一側的需求，不是本鎖的）。

    🔴 這裡**曾**寫成 `ADL._CELL_SPLIT_RE.split(line)` 再自行 strip，理由是當時上游的
    `ADL._cells()` 會用 `if c.strip()` 丟掉空欄、不能用，所以只借它的正則零件、不借它的
    函式。Pkg-P7 把 `_cells()`／`_CELL_SPLIT_RE` 一併收斂進閘門後，那個名稱在本檔懸空、
    根層全套於 import 期整批翻紅（`DEF-101-581`）。現在改為消費上游的**函式**而不是它的
    零件：`_row_cells()` 早已被 `DEF-101-580` 修成保留空欄，當初繞開它的唯一理由已經不
    存在，於是「自己再切一次」這個中間層可以整個拿掉——引用面愈少零件，愈不容易被上游
    重構打斷。等價性（與修前語意逐列相同）與空欄鑑別力見
    `TestCriterionHasTeethOnSyntheticInput::test_an_empty_cell_neither_hides_nor_shifts_the_row`。
    """
    return ADL.gate._row_cells(line)[1:-1]


def ledger_rows(text: str) -> dict[str, Row]:
    """解析帳本文字，回傳 `{DEF-ID: Row}`（只收欄數正確的表格列）。"""
    out: dict[str, Row] = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        if not ADL.gate._ROW_RE.match(line):
            continue
        cells = row_cells(line)
        if len(cells) != _N_COLS:
            continue
        def_id = cells[_IDX_ID]
        if not ADL.gate._ID_RE.fullmatch(def_id):
            continue
        out[def_id] = Row(
            def_id=def_id,
            date=cells[_IDX_DATE],
            triage=cells[_IDX_TRIAGE],
            status=cells[_IDX_STATUS],
            lineno=lineno,
        )
    return out


def _has_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(tok in text for tok in tokens)


def falls_into_adr_431(row: Row) -> bool:
    """ADR §4.3.1 逐字：分流欄**或**狀態欄**同時**出現「凍結版／凍結基線」與「不回補／wontfix」。"""
    return any(
        _has_any(cell, _FROZEN_TOKENS) and _has_any(cell, _WONTFIX_TOKENS)
        for cell in (row.triage, row.status)
    )


def satisfies_c1(def_id: str, onboarding_section_9: str) -> bool:
    """C1：該 DEF-ID 在 `ONBOARDING.md` §9 區段內被點名（表列或註腳皆算，見檔頭邊界）。"""
    return def_id in onboarding_section_9


def satisfies_c2(row: Row) -> bool:
    """C2：分流欄或狀態欄寫出重新評估的觸發條件（字樣＝「重新評估／屆時」）。"""
    return any(_has_any(cell, _REEVAL_TOKENS) for cell in (row.triage, row.status))


def downgraded_per_adr_433(row: Row) -> bool:
    """§4.3.3 的合法出口：狀態已降為 `partial@R<n>（§4.3 條件未滿足）`。"""
    return bool(_PARTIAL_RE.search(row.status)) and _SECTION_43_MARK in row.status


def unmet_conditions(row: Row, onboarding_section_9: str) -> frozenset[str]:
    """回傳該列未滿足的條件集合；已依 §4.3.3 降級者視為無未滿足項。"""
    if downgraded_per_adr_433(row):
        return frozenset()
    unmet = set()
    if not satisfies_c1(row.def_id, onboarding_section_9):
        unmet.add("C1")
    if not satisfies_c2(row):
        unmet.add("C2")
    return frozenset(unmet)


def audit(ledger_text: str, onboarding_text: str) -> dict[str, frozenset[str]]:
    """單一份帳本文字的判準結果；**落入者一律入表**（合規者值為空集合）。"""
    sec9 = onboarding_section_9(onboarding_text)
    return {
        def_id: unmet_conditions(row, sec9)
        for def_id, row in ledger_rows(ledger_text).items()
        if falls_into_adr_431(row)
    }


def audit_family(family: list[tuple[str, str]], onboarding_text: str) -> dict[str, Finding]:
    """家族全檔的判準結果 `{DEF-ID: Finding}`；家族內若有重複 ID 以先出現者為準
    （`_family_files()` 把主檔排在最前，故主檔優先）。"""
    sec9 = onboarding_section_9(onboarding_text)
    out: dict[str, Finding] = {}
    for name, text in family:
        for def_id, row in ledger_rows(text).items():
            if def_id in out or not falls_into_adr_431(row):
                continue
            out[def_id] = Finding(name, row, unmet_conditions(row, sec9))
    return out


def family_row_index(family: list[tuple[str, str]]) -> dict[str, tuple[str, Row]]:
    """`{DEF-ID: (檔名, Row)}`（同 `audit_family`：主檔優先），供孤兒／上界錨點查詢。"""
    out: dict[str, tuple[str, Row]] = {}
    for name, text in family:
        for def_id, row in ledger_rows(text).items():
            out.setdefault(def_id, (name, row))
    return out


def family_row_total(family: list[tuple[str, str]]) -> int:
    """家族全檔解析出的帳本列總數（反掃描面崩塌用；不去重，逐檔相加）。"""
    return sum(len(ledger_rows(text)) for _, text in family)


def is_post_adr(def_id: str) -> bool:
    """該列是否是 ADR 落地**之後**才開的（＝ID 超過基線上界）。"""
    return _id_key(def_id) > _id_key(_BASELINE_ID_CEILING)


def hard_block_offenders(
    result: dict[str, Finding], waivers: dict[str, Waiver]
) -> dict[str, Finding]:
    """回傳應被硬擋的列（見檔頭「射程」段的兩層規則）。

    · ADR 落地後的新列（家族任一份檔）：條件未滿足即擋，**豁免登記對它無效**
      ——這正是「新增違規列＋同輪歸檔」繞道面被關掉的地方。
    · ADR 落地前的舊列：只有住在帳本**主檔**且未具名登記者才擋；已歸檔者不在射程。
    """
    offenders: dict[str, Finding] = {}
    for def_id, finding in result.items():
        if not finding.unmet:
            continue
        if is_post_adr(def_id):
            offenders[def_id] = finding
        elif finding.source == MAIN_LEDGER_NAME and def_id not in waivers:
            offenders[def_id] = finding
    return offenders


def baseline_admission_problems(
    waivers: dict[str, Waiver], index: dict[str, tuple[str, Row]]
) -> list[str]:
    """回傳「結構上不得入表」的登記；空清單＝全部登記都是 ADR 落地前的舊列。

    主判準＝ID ≤ `_BASELINE_ID_CEILING`（與日曆脫鉤，見檔頭 (b)）。
    輔助判準＝發現日期不得晚於上界列自身的發現日期（**從帳本現查，不寫死日期常數**），
    用來擋「回填一個未用過的舊號碼」這種繞法的一半；兩個欄位都造假仍可逃過（檔頭邊界已載）。
    """
    if _BASELINE_ID_CEILING not in index:
        return [
            f"基線上界 {_BASELINE_ID_CEILING} 在帳本家族查無此列——上界失去錨點，"
            "本鎖拒絕在無法驗證上界的情況下放行任何登記"
        ]
    ceiling_key = _id_key(_BASELINE_ID_CEILING)
    ceiling_date = index[_BASELINE_ID_CEILING][1].date
    problems: list[str] = []
    for def_id in sorted(waivers, key=_id_key):
        if _id_key(def_id) > ceiling_key:
            problems.append(
                f"{def_id}：ID 超過基線上界 {_BASELINE_ID_CEILING} ⇒ 這是 ADR 落地後才開的列，"
                "結構上不得入表"
            )
            continue
        entry = index.get(def_id)
        if entry is not None and entry[1].date > ceiling_date:
            problems.append(
                f"{def_id}：ID 雖在上界內，但發現日期（{entry[1].date}）晚於上界列"
                f" {_BASELINE_ID_CEILING}（{ceiling_date}）⇒ 疑似回填未用號碼的新列"
            )
    return problems


def _slice_section(text: str, head: str, end: str, what: str) -> str:
    """抓 `head` 起、`end` 止的區段；抓不到就丟例外（不得靜默回空字串或全檔）。"""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(head)), None)
    if start is None:
        raise RuntimeError(f"找不到 {what} 的起始標題 {head!r} — 判準來源已失效，拒絕靜默通過")
    stop = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(end)), None)
    if stop is None:
        raise RuntimeError(f"找不到 {what} 的結束標題 {end!r} — 判準來源已失效，拒絕靜默通過")
    return "\n".join(lines[start:stop])


def onboarding_section_9(onboarding_text: str) -> str:
    return _slice_section(onboarding_text, _SEC9_HEAD, _SEC9_END, "ONBOARDING.md §9 已知缺口")


def adr_section_7(adr_text: str) -> str:
    return _slice_section(adr_text, _ADR_SEC7_HEAD, _ADR_SEC7_END, "ADR-XPLAT-001 §7 未結落差")


# ---------------------------------------------------------------- 讀檔（可 monkeypatch 供注入測試）
def read_ledger() -> str:
    return _LEDGER.read_text(encoding="utf-8-sig")


def read_family() -> list[tuple[str, str]]:
    """帳本家族全檔的 `(檔名, 內容)`；枚舉走 `ADL._family_files()`（家族 SSOT）。"""
    return [(p.name, p.read_text(encoding="utf-8-sig")) for p in ADL._family_files()]


def read_onboarding() -> str:
    return _ONBOARDING.read_text(encoding="utf-8-sig")


def read_adr() -> str:
    return _ADR.read_text(encoding="utf-8-sig")


# ---------------------------------------------------------------- shrink-only 棘輪（對 HEAD 比對）
_SELF_REL = f"tools/tests/{_HERE.name}"  # git 路徑一律 posix，不用 os.sep
_RATCHET_MAX_RE = re.compile(r"^_MAX_BASELINE_ENTRIES\s*=\s*(\d+)", re.M)
_RATCHET_CEILING_RE = re.compile(r"^_BASELINE_ID_CEILING\s*=\s*\"(DEF-\d+-\d+)\"", re.M)


def read_previous_self_source() -> str | None:
    """本檔在 HEAD 的內容；HEAD 沒有本檔（新增檔／首版）時回 `None`。"""
    proc = subprocess.run(
        ["git", "-C", str(_REPO), "show", f"HEAD:{_SELF_REL}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.stdout if proc.returncode == 0 else None


def ratchet_problems(previous_source: str, current_max: int, current_ceiling: str) -> list[str]:
    """比對上一版與現版的兩個 shrink-only 常數；回傳違規說明（空＝只降不升）。

    抽不到常數時**紅而不是略過**：常數被改名／改寫就等於棘輪失效，那是最需要被看見的
    失敗模式（同型教訓＝`_PENDING_MIGRATION_SITES` 靠「不加自檢」變成永久豁免）。
    """
    problems: list[str] = []
    m = _RATCHET_MAX_RE.search(previous_source)
    if m is None:
        problems.append(
            "上一版抽不到 _MAX_BASELINE_ENTRIES —— 常數被改名／改寫？棘輪等於失效，拒絕靜默通過"
        )
    elif current_max > int(m.group(1)):
        problems.append(
            f"_MAX_BASELINE_ENTRIES 由 {m.group(1)} 調升為 {current_max} —— 本常數只准往下改"
        )
    m = _RATCHET_CEILING_RE.search(previous_source)
    if m is None:
        problems.append(
            "上一版抽不到 _BASELINE_ID_CEILING —— 常數被改名／改寫？棘輪等於失效，拒絕靜默通過"
        )
    elif _id_key(current_ceiling) > _id_key(m.group(1)):
        problems.append(
            f"_BASELINE_ID_CEILING 由 {m.group(1)} 調升為 {current_ceiling} —— 調升上界"
            "等於為 ADR 落地後的新列開門"
        )
    return problems


def _fmt(items: dict[str, Finding]) -> str:
    return "\n".join(
        f"  · {k}（{v.source}:{v.row.lineno}）：缺 {sorted(v.unmet)}"
        for k, v in sorted(items.items())
    )


class TestCriterionIsBoundToAdrProse(unittest.TestCase):
    """判準字樣不是本檔自己編的——它必須與 ADR §4.3.1／C2 的句子逐字一致（雙向）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.adr = read_adr()

    def test_frozen_and_wontfix_tokens_match_adr_431_sentence(self) -> None:
        m = re.search(r"「(?P<frozen>[^」]+)」與「(?P<wontfix>[^」]+)」兩類\s*字樣", self.adr)
        self.assertIsNotNone(
            m, "ADR §4.3.1 的觸發判準句抽不到——句子被改寫了？請同步本檔 _FROZEN_TOKENS／"
               "_WONTFIX_TOKENS 與此處的抽取樣式"
        )
        assert m is not None
        self.assertEqual(
            set(m.group("frozen").split("／")), set(_FROZEN_TOKENS),
            "ADR §4.3.1 的『凍結』字樣與本檔 _FROZEN_TOKENS 不一致 — 散文與程式必須同步",
        )
        self.assertEqual(
            set(m.group("wontfix").split("／")), set(_WONTFIX_TOKENS),
            "ADR §4.3.1 的『不回補』字樣與本檔 _WONTFIX_TOKENS 不一致 — 散文與程式必須同步",
        )

    def test_reeval_tokens_match_adr_c2_definition(self) -> None:
        m = re.search(r"C2 的「重新評估的觸發條件」判準字樣＝「(?P<toks>[^」]+)」", self.adr)
        self.assertIsNotNone(m, "ADR §4.3.1 裡的 C2 判準字樣定義句抽不到")
        assert m is not None
        self.assertEqual(
            set(m.group("toks").split("／")), set(_REEVAL_TOKENS),
            "ADR 的 C2 判準字樣與本檔 _REEVAL_TOKENS 不一致 — 散文與程式必須同步",
        )

    def test_baseline_id_ceiling_matches_adr_prose(self) -> None:
        """基線上界也走雙向綁定：要調升它就得同時改 ADR §4.3.4（治理文件裡藏不住）。

        WHY 這條是必要的（SD-R60-R2-05 ①）：上界是「哪些列算舊列」的唯一開關，只放在
        測試檔裡改動成本太低。綁到 ADR 後，調升上界＝改治理文件＋改鎖＋過 shrink-only
        棘輪三道，缺一即紅。
        """
        m = re.search(
            r"\*\*ID 上界\*\*＝`(?P<ceiling>DEF-\d+-\d+)`（鎖內 `_BASELINE_ID_CEILING`）",
            self.adr,
        )
        self.assertIsNotNone(
            m, "ADR §4.3.4 的『**ID 上界**＝`DEF-…`（鎖內 `_BASELINE_ID_CEILING`）』宣告句"
               "抽不到——句子被改寫或刪掉了？散文與程式必須同步"
        )
        assert m is not None
        self.assertEqual(
            m.group("ceiling"), _BASELINE_ID_CEILING,
            "ADR §4.3.4 宣告的基線 ID 上界與本檔 _BASELINE_ID_CEILING 不一致 — 兩邊必須同步",
        )

    def test_adr_does_not_still_claim_a_calendar_freeze_boundary(self) -> None:
        """ADR 不得殘留「發現日期 ≤ 落地日」那條已被證偽的判準敘述（否則散文回頭騙人）。"""
        self.assertNotIn(
            "_BASELINE_FROZEN_AT", self.adr,
            "ADR 仍在引用已移除的日期日界常數 _BASELINE_FROZEN_AT——該判準對『同日新列』"
            "無效（SD-R60-R2-05 ①），§4.3.4 應已改寫為 ID 上界",
        )

    def test_adr_c1_targets_onboarding_section_9(self) -> None:
        self.assertIn(
            "C1｜known-gap 必須寫進根層 `ONBOARDING.md` §9", self.adr,
            "ADR C1 的目標文件／章節被改了，本檔的 satisfies_c1 掃描面必須同步",
        )

    def test_adr_c2_scope_is_triage_or_status_not_status_only(self) -> None:
        """C2 掃描面必須是「分流欄或狀態欄」——只認狀態欄會把 ADR 自己舉的正例判不合格。"""
        self.assertIn(
            "C2｜帳本分流欄或狀態欄必須寫出重新評估的觸發條件", self.adr,
            "ADR C2 的掃描面敘述與本檔 satisfies_c2（分流欄 or 狀態欄）不一致",
        )

    def test_adr_labels_line_based_grep_as_prefilter_only(self) -> None:
        """§4.3.2 ① 的整列 grep 比 §4.3.1 寬，ADR 必須標明它只是粗篩。"""
        self.assertIn("①只是粗篩，不是判準", self.adr)
        self.assertIn("DEF-101-358", self.adr, "粗篩假陽性的具名案例不得被刪掉")

    def test_adr_names_this_lock_file(self) -> None:
        """ADR §4.3.4／§7／§8 必須指名本檔——改名或刪檔會讓 ADR 敘述失實，故雙向釘住。"""
        self.assertGreaterEqual(
            self.adr.count(_HERE.name), 2,
            f"ADR 未（或只有一處）指名 {_HERE.name}；§4.3.4 與 §8 都應引用它",
        )
        self.assertNotIn(
            "沒有機械鎖", self.adr,
            "ADR 仍自陳『沒有機械鎖』，與本檔存在的事實矛盾（§4.3.4 應已改寫）",
        )


class TestCriterionHasTeethOnSyntheticInput(unittest.TestCase):
    """判準的鑑別力用**合成輸入**釘住（不受帳本歸檔／列數變動影響）。

    這是把 bug-injection ①（構造一筆落入 §4.3.1 但既不在 §9 也無重新評估字樣的新列）
    永久固定成回歸測試——判準若退化成「恆回空集合」或「恆合規」，本類必紅。
    合成 ID 一律由 `_synthetic_id()` 在**執行期**組出，原始碼裡不留字面（見該函式 docstring）。
    """

    @staticmethod
    def _syn(n: int) -> str:
        return _synthetic_id(101, n)

    @classmethod
    def setUpClass(cls) -> None:
        cls.ONB = (
            "## 9. 已知缺口（known-gap）\n"
            "| 缺口 | 影響 | 緩解 |\n"
            "|---|---|---|\n"
            f"| 合成缺口一（{cls._syn(901)}） | — | — |\n"
            "\n## 10. 下一節\n"
        )

    def _ledger(self, *rows: str) -> str:
        head = "| ID | 發現日期 | 發現情境 | 現象與證據 | 嚴重度 | 分流去向 | 狀態 |\n"
        return head + "".join(rows)

    def _row(self, def_id: str, triage: str, status: str, evidence: str = "evidence") -> str:
        return f"| {def_id} | 2026-08-01 | ctx | {evidence} | P3 | {triage} | {status} |\n"

    def test_violating_row_is_reported_with_both_conditions_unmet(self) -> None:
        sid = self._syn(902)
        led = self._ledger(self._row(sid, "凍結版依紀律不回補", "wontfix+凍結版紀律"))
        self.assertEqual(audit(led, self.ONB), {sid: frozenset({"C1", "C2"})})

    def test_row_in_section_9_with_reeval_is_compliant(self) -> None:
        sid = self._syn(901)
        led = self._ledger(self._row(
            sid, "凍結版依紀律不回補", "wontfix+凍結版紀律（…屆時重新評估是否回補）"))
        self.assertEqual(audit(led, self.ONB), {sid: frozenset()})

    def test_tokens_must_co_occur_in_the_same_cell(self) -> None:
        """「凍結版」在分流欄、「不回補」在狀態欄 ⇒ 依 §4.3.1 逐字**不**落入本節。"""
        led = self._ledger(self._row(
            self._syn(903), "凍結版相關敘述", "open（不回補待評估）"))
        self.assertEqual(audit(led, self.ONB), {})

    def test_evidence_column_hit_does_not_fall_into_431(self) -> None:
        """字樣只落在現象欄 ⇒ 不落入本節（＝§4.3.2 ① 整列 grep 的那個假陽性形態）。"""
        led = self._ledger(self._row(
            self._syn(904), "抽共享層", "fixed@R45", evidence="凍結版同檔同缺、不回補"))
        self.assertEqual(audit(led, self.ONB), {})

    def test_downgraded_status_is_an_accepted_alternative(self) -> None:
        """§4.3.3 出口：`partial@R<n>（§4.3 條件未滿足）` 免豁免、免 §9 列即算合規。"""
        sid = self._syn(905)
        led = self._ledger(self._row(
            sid, "凍結版依紀律不回補", "partial@R61（§4.3 條件未滿足）"))
        self.assertEqual(audit(led, self.ONB), {sid: frozenset()})

    def test_partial_without_section_marker_is_not_an_escape(self) -> None:
        """光寫 `partial@R61` 不算——必須明示掛在 §4.3，否則就是含糊狀態夾帶。"""
        sid = self._syn(906)
        led = self._ledger(self._row(sid, "凍結版依紀律不回補", "partial@R61"))
        self.assertEqual(audit(led, self.ONB), {sid: frozenset({"C1", "C2"})})

    def test_escaped_pipe_inside_a_cell_does_not_shift_columns(self) -> None:
        """帳本真有跳脫 pipe 寫法；切格若退回 naive split 會錯位，判準跟著失效。"""
        sid = self._syn(907)
        led = self._ledger(self._row(
            sid, "凍結版依紀律不回補", "wontfix+凍結版紀律", evidence="`a \\| b` 證據"))
        self.assertEqual(audit(led, self.ONB), {sid: frozenset({"C1", "C2"})})

    def test_an_empty_cell_neither_hides_nor_shifts_the_row(self) -> None:
        """空欄不得讓該列從掃描面消失，也不得讓 §4.3.3 的降級出口被左鄰欄冒充。

        這是 `DEF-101-580`（閘門側的假綠）在本鎖上的同型鑑別力證明。取「狀態欄留空、
        分流去向欄寫著 `partial@R<n>（§4.3 …）`」這個形態，因為 `downgraded_per_adr_433()`
        是本鎖**唯一只看狀態欄**的判準——欄位一左移，分流欄的降級字樣就會被當成狀態欄的
        合法出口，一列條件未滿足的新列直接變成合規（假綠）。判準的其餘部分（落入 §4.3.1
        與 C2）掃的是「分流或狀態」兩欄的聯集，對左移天然免疫，所以拿它們證不出鑑別力
        ——這一點如實記錄，不假裝整支判準都靠這個測試守住。

        反事實用**現行語意的反向重算**釘住（不改任何檔案）：舊的「濾掉空欄」寫法會讓本列
        少切出一欄 ⇒ `ledger_rows()` 在 `len(cells) != _N_COLS` 處靜默跳過整列。兩種失敗
        模式（左移讀錯欄／整列隱形）都是假綠，現行的保留空欄語意兩者皆無。
        """
        sid = self._syn(908)
        triage = "凍結版不回補；partial@R61（§4.3 條件未滿足）"
        led = self._ledger(self._row(sid, triage, ""))
        line = led.splitlines()[1]

        cells = row_cells(line)
        self.assertEqual(len(cells), _N_COLS, "保留空欄語意下本列必須切出完整欄數")
        self.assertEqual(cells[_IDX_STATUS], "", "狀態欄必須讀成空字串，而不是左鄰欄的內容")
        self.assertEqual(cells[_IDX_TRIAGE], triage, "分流去向欄不得被右鄰的空欄吸走")
        self.assertEqual(
            audit(led, self.ONB), {sid: frozenset({"C1", "C2"})},
            "狀態欄為空 ⇒ §4.3.3 降級出口不成立，兩條件都該判未滿足",
        )

        filtered = [c.strip() for c in ADL.gate._CELL_SPLIT_RE.split(line) if c.strip()]
        self.assertNotEqual(
            len(filtered), _N_COLS,
            "反事實前提失效：本列在『濾掉空欄』語意下欄數竟仍正確，本測試失去鑑別力",
        )
        self.assertEqual(
            filtered[-1], triage,
            "反事實前提失效：濾掉空欄後 `cells[-1]`（＝被刪掉的 `ADL._cells()` 取狀態欄的"
            "方式）竟不是分流去向的內容 ⇒ 左移形態沒被示範",
        )

    def test_missing_section_9_heading_fails_loud(self) -> None:
        with self.assertRaises(RuntimeError):
            onboarding_section_9("# 沒有第九節的文件\n")


# -------------------------------------------------------- 上游 SSOT 引用面契約（DEF-101-581）
# 事故形態（本檔親身受害）：A 檔把某個名稱當 SSOT 公開 → B 檔照紀律引用它 → A 檔重構時
# 沒有任何機制知道 B 在引用 ⇒ 名稱一消失，B 在 import 期就炸，而 A 檔自己的測試與兩道
# 帳本閘門全數照印 rc=0。既成先例是 `tools/tests/test_archive_defect_log.py` 的
# `_GATE_SSOT_CONTRACT`（手維護一張「上游必須有這些名稱」的表）。本檔沿用它的形狀但補掉
# 它的缺口：**引用面從本檔 AST 現查，不手維護名單**——手維護的表對「漏登記的引用」零保護，
# 而本檔正是因為某一處引用沒被任何名單涵蓋才被打斷的。
_UPSTREAM_ROOT_ALIAS = "ADL"


def upstream_refs(source: str) -> dict[str, list[int]]:
    """抽出 `source` 裡所有以 `ADL` 為根的屬性引用鏈 → `{點分名稱: [行號, …]}`。

    巢狀鏈會連中間節點一起收（`ADL.gate._row_cells` 同時登記 `ADL.gate`），因為
    `gate` 這個別名本身也是上游的公開名稱、同樣會被重構掉。
    """
    out: dict[str, list[int]] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Attribute):
            continue
        chain: list[str] = []
        cur: ast.expr = node
        while isinstance(cur, ast.Attribute):
            chain.append(cur.attr)
            cur = cur.value
        if not isinstance(cur, ast.Name) or cur.id != _UPSTREAM_ROOT_ALIAS:
            continue
        out.setdefault(".".join([cur.id, *reversed(chain)]), []).append(node.lineno)
    return out


def dangling_upstream_refs(refs: dict[str, list[int]], root: object) -> list[str]:
    """逐條解析引用鏈；回傳解析不到的清單，每筆指名**斷在哪個名稱**與本檔的引用行號。"""
    problems: list[str] = []
    for dotted, linenos in sorted(refs.items()):
        parts = dotted.split(".")
        obj: object = root
        walked = [parts[0]]
        for part in parts[1:]:
            if not hasattr(obj, part):
                problems.append(
                    f"{'.'.join(walked)} 已無屬性 `{part}`（完整引用 `{dotted}`，"
                    f"本檔引用行號 {sorted(set(linenos))}）"
                )
                break
            obj = getattr(obj, part)
            walked.append(part)
    return problems


def incompatible_upstream_calls(source: str, root: object) -> list[str]:
    """檢查本檔對上游的每個**呼叫點**是否還跟現行簽名對得上；回傳不相容清單。

    🔴 這是「名稱還在但簽名變了」那一半，也是本契約鎖裡真正難抓的一半：名稱消失是
    `AttributeError`、在 import 期就炸；簽名改變是 `TypeError`，**只在那一行真的被求值
    時才炸**。冷路徑上的呼叫點（只有某個分支或某個 skip 條件不成立才走到）會一路綠到
    有人第一次真的走那條路。本函式用 AST 靜態取出引數形狀再 `Signature.bind`，
    **不需要執行到那一行**就能判定，於是冷熱路徑一律等同受檢。

    誠實劃界：`*args`／`**kwargs` 展開的呼叫點靜態無法判定 arity，一律略過（不假裝
    有覆蓋）；型別不相容（傳對數量但傳錯型別）也不在射程——那要靠行為測試。
    """
    problems: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        chain: list[str] = []
        cur: ast.expr = node.func
        while isinstance(cur, ast.Attribute):
            chain.append(cur.attr)
            cur = cur.value
        if not isinstance(cur, ast.Name) or cur.id != _UPSTREAM_ROOT_ALIAS:
            continue
        dotted = ".".join([cur.id, *reversed(chain)])
        obj: object = root
        for part in reversed(chain):
            if not hasattr(obj, part):
                obj = None
                break
            obj = getattr(obj, part)
        if obj is None or not callable(obj):
            continue  # 名稱面的問題由 dangling_upstream_refs() 負責，此處不重複回報
        if any(isinstance(a, ast.Starred) for a in node.args) or any(
                k.arg is None for k in node.keywords):
            continue
        try:
            sig = inspect.signature(obj)
        except (TypeError, ValueError):
            continue  # C 實作的內建（例如已編譯正則的方法）取不到簽名
        kwargs = {k.arg: "<probe>" for k in node.keywords if k.arg}
        try:
            sig.bind(*(["<probe>"] * len(node.args)), **kwargs)
        except TypeError as exc:
            problems.append(
                f"`{dotted}` 的簽名已與本檔呼叫點不相容（本檔 :{node.lineno} 傳入 "
                f"{len(node.args)} 個位置引數、關鍵字 {sorted(kwargs)}；"
                f"上游現行簽名 {sig}）⇒ {exc}"
            )
    return problems


class _UpstreamStandin:
    """`ADL` 的唯讀替身：除了指定拔掉／換簽名的名稱之外一律轉發給真模組（巢狀遞迴包裝）。

    🔴 刻意用替身而不是對真模組 `delattr`／`setattr`：本 repo 已因「就地改再改回」出過
    事故，突變一律關在沙箱物件裡——真模組、`sys.modules` 與磁碟全程零觸碰。
    """

    def __init__(self, real: object, drop: str = "", resign: dict[str, object] | None = None):
        self._real = real
        self._drop = drop
        self._resign = resign or {}

    def __getattr__(self, name: str) -> object:
        if name == self._drop:
            raise AttributeError(f"沙箱替身刻意移除 `{name}`")
        if name in self._resign:
            return self._resign[name]
        obj = getattr(self._real, name)
        if isinstance(obj, ModuleType):
            return _UpstreamStandin(obj, self._drop, self._resign)
        return obj


class TestArchiveIsNotAnEscapeHatch(unittest.TestCase):
    """把「新增違規列 ＋ 同輪歸檔」這條繞道面永久釘死（SA-R60R2-04）。

    成因：落入 §4.3.1 的列典型狀態是 `wontfix`，而 `archive_defect_log.py` 判準① 對
    `wontfix` 是**允許搬遷**的。round 2 的鎖只掃主檔 ⇒ 把列搬進 archive 就出了掃描面。
    現版掃家族全檔，並以「ADR 落地後的新列」為硬擋條件（ID > 基線上界）。
    """

    def _syn(self, n: int) -> str:
        return _synthetic_id(101, n)

    def _finding(self, def_id: str, source: str, unmet: frozenset[str]) -> Finding:
        row = Row(def_id=def_id, date="2026-08-01", triage="凍結版不回補",
                  status="wontfix+凍結版紀律", lineno=1)
        return Finding(source, row, unmet)

    def test_post_adr_violating_row_hidden_in_an_archive_is_still_blocked(self) -> None:
        sid = self._syn(999)  # ID 遠大於基線上界 ⇒ 定義上是 ADR 落地後的新列
        self.assertTrue(is_post_adr(sid), "合成 ID 必須落在基線上界之後，否則本測試沒有意義")
        result = {sid: self._finding(sid, "AutoSDD_Defect_Log_archive_31.md",
                                     frozenset({"C1", "C2"}))}
        self.assertEqual(sorted(hard_block_offenders(result, {})), [sid])

    def test_a_waiver_cannot_shield_a_post_adr_row_even_in_the_main_ledger(self) -> None:
        """新列連「登記進豁免表」都遮不住（雙保險：admission 檢查另外會紅）。"""
        sid = self._syn(998)
        result = {sid: self._finding(sid, MAIN_LEDGER_NAME, frozenset({"C1", "C2"}))}
        waivers = {sid: Waiver(frozenset({"C1", "C2"}), "x" * 41, "y" * 13)}
        self.assertEqual(sorted(hard_block_offenders(result, waivers)), [sid])

    def test_pre_adr_archive_row_is_out_of_scope_by_design(self) -> None:
        """對照組（誠實劃界）：ADR 落地前的 archive 列不擋——設計上不追溯，見檔頭邊界。"""
        old = _synthetic_id(1, 1)
        self.assertFalse(is_post_adr(old))
        result = {old: self._finding(old, "AutoSDD_Defect_Log_archive_01.md",
                                     frozenset({"C1", "C2"}))}
        self.assertEqual(hard_block_offenders(result, {}), {})

    def test_pre_adr_main_row_still_needs_a_named_waiver(self) -> None:
        """對照組：ADR 落地前的**主檔**列沒登記照擋（具名豁免的壓力不因擴面而鬆掉）。"""
        old = _synthetic_id(1, 2)
        result = {old: self._finding(old, MAIN_LEDGER_NAME, frozenset({"C2"}))}
        self.assertEqual(sorted(hard_block_offenders(result, {})), [old])
        waivers = {old: Waiver(frozenset({"C2"}), "x" * 41, "y" * 13)}
        self.assertEqual(hard_block_offenders(result, waivers), {})

    def test_family_enumeration_comes_from_the_archive_tool_ssot(self) -> None:
        """家族枚舉必須是 `ADL._family_files()`（ARCH-R60-09：掃描面不得各自為政）。"""
        expected = [p.name for p in ADL._family_files()]
        self.assertEqual([name for name, _ in read_family()], expected)
        self.assertEqual(expected[0], MAIN_LEDGER_NAME, "主檔必須排在家族第一位（主檔優先語意）")
        self.assertGreater(len(expected), 1, "家族只剩主檔——archive 檔案枚舉疑似失效")

    # ---- 上游 SSOT 引用面契約：本類是本檔既有的「對上游模組的依賴」斷言居所（上面那條
    # 家族枚舉 SSOT 就在這裡），故引用面契約併入本類，不另立鎖檔／鎖類（ARCH-R60-09 明文
    # 批評「一個 finding 一支鎖、掃描面各自為政」）。
    def test_every_upstream_ssot_reference_in_this_file_resolves(self) -> None:
        """本檔對上游（`archive_defect_log` 及其 `gate`）的每一處引用都必須解析得到。

        `DEF-101-581` 的根因級防復發：那次是上游收斂 SSOT 時刪掉本檔正在引用的名稱，
        而**兩道帳本閘門（`--check` 與 `check_defect_log_crossref`）都照印 rc=0**——它們
        稽核的是帳本內容，不是模組介面，結構上看不到跨檔引用。本鎖把「被引用的名稱消失」
        從「某天有人跑到那條路徑才發現」變成「當輪立刻紅並指名是哪個名稱、被哪幾行引用」。
        """
        problems = dangling_upstream_refs(upstream_refs(_HERE.read_text(encoding="utf-8")), ADL)
        self.assertEqual(
            problems, [],
            "本檔引用的上游 SSOT 名稱已不存在（上游重構未同步本檔引用面）：\n  "
            + "\n  ".join(problems)
            + "\n合法出口二擇一：①上游保留同一物件的公開別名（re-export，不是複本）；"
              "②本檔改引用等價的新名稱。引用面由 AST 現查，新增引用自動納保。",
        )

    def test_upstream_reference_extraction_is_not_vacuous(self) -> None:
        """正控：抽取器對本檔現行原始碼必須抽到判準真正在用的引用，否則上一條是空轉。

        逐字釘住的這幾個名稱就是判準本體實際消費的上游介面；`ADL.gate._row_cells` 更是
        `DEF-101-581` 的傷口所在（修法＝從借正則零件改成借函式），必須在保護範圍內。
        """
        refs = upstream_refs(_HERE.read_text(encoding="utf-8"))
        self.assertTrue(refs, "抽取器對本檔一無所獲 ⇒ 引用面契約整條空轉")
        for expected in ("ADL.gate", "ADL.gate._row_cells", "ADL.gate._ROW_RE",
                         "ADL.gate._ID_RE", "ADL._family_files"):
            with self.subTest(ref=expected):
                self.assertIn(expected, refs, f"抽取器沒抽到 `{expected}` ⇒ 該引用不受保護")

    def test_a_vanished_upstream_name_is_named_together_with_its_consumers(self) -> None:
        """鑑別力：沙箱拔掉一個**真的被引用**的名稱，契約鎖必須紅且指名該名稱與引用行號。

        對照組＝什麼都不拔的同型替身 ⇒ 零問題，證明紅是「拔掉」造成的而不是替身本身
        不透明。受害名稱刻意涵蓋三種形狀：巢狀函式（`_row_cells`，即真實事故那一處）、
        頂層函式（`_family_files`）、以及模組別名本身（`gate`，斷在鏈的中間節點）。
        """
        refs = upstream_refs(_HERE.read_text(encoding="utf-8"))
        self.assertEqual(
            dangling_upstream_refs(refs, _UpstreamStandin(ADL, "")), [],
            "對照組：未拔任何名稱的替身竟報出問題 ⇒ 替身不透明，本測試的紅沒有鑑別力",
        )
        for victim in ("_row_cells", "_family_files", "gate"):
            with self.subTest(victim=victim):
                problems = dangling_upstream_refs(refs, _UpstreamStandin(ADL, victim))
                self.assertTrue(problems, f"拔掉 `{victim}` 竟然沒紅 ⇒ 本契約鎖沒有牙")
                joined = "\n".join(problems)
                self.assertIn(f"`{victim}`", joined, "問題訊息未逐字指名消失的那個屬性")
                self.assertRegex(joined, r"本檔引用行號 \[\d+", "問題訊息未指出本檔的引用點")
        self.assertTrue(
            hasattr(ADL, "_family_files") and hasattr(ADL.gate, "_row_cells"),
            "真模組被本測試污染了——替身本該是唯讀轉發，突變不得外洩",
        )

    def test_every_upstream_call_site_still_matches_the_current_signature(self) -> None:
        """本檔對上游的每個呼叫點都必須與現行簽名相容（名稱面之外的另一半）。

        `DEF-101-581` 是名稱消失、import 期就炸、當場可見。**簽名改變不會這麼客氣**：
        同一輪 Pkg-P7 就給 `classify_row()`／`_row_id()` 各加了一個 `layout` 參數——那種
        變更打斷的呼叫點是 `TypeError`，只在該行真的被求值時才炸，藏在冷路徑（只有
        `--apply` 才走到、或某個 skip 條件不成立才求值）的話會一路綠下去。本鎖靜態判定，
        冷熱路徑等同受檢。
        """
        problems = incompatible_upstream_calls(_HERE.read_text(encoding="utf-8"), ADL)
        self.assertEqual(
            problems, [],
            "本檔的上游呼叫點與上游現行簽名不相容（上游改簽名未同步呼叫端）：\n  "
            + "\n  ".join(problems)
            + "\n這類斷裂不會在 import 期出現，只在該行被求值時才 TypeError——"
              "冷路徑上的呼叫點可能一直綠到有人第一次走那條路，故以靜態判定攔在當輪。",
        )

    def test_a_changed_upstream_signature_is_reported_with_the_call_site(self) -> None:
        """鑑別力：沙箱把某個被呼叫的上游函式換成多一個必填參數的版本 ⇒ 必須紅並指名。

        突變對象刻意選 `_row_cells`——本檔 `row_cells()` 正是以單一位置引數呼叫它，
        而 Pkg-P7 對 `classify_row()`／`_row_id()` 做的就是這個形狀的變更（加一個必填
        `layout`）。對照組＝未換簽名的同型替身 ⇒ 零問題。
        """
        source = _HERE.read_text(encoding="utf-8")
        self.assertEqual(
            incompatible_upstream_calls(source, _UpstreamStandin(ADL)), [],
            "對照組：未動任何簽名的替身竟報出不相容 ⇒ 替身不透明，本測試的紅沒有鑑別力",
        )

        def _needs_layout(line: str, layout: tuple[int, int, int]) -> list[str]:
            raise AssertionError("本替身只供簽名檢查，不該被真的呼叫")

        problems = incompatible_upstream_calls(
            source, _UpstreamStandin(ADL, resign={"_row_cells": _needs_layout}))
        self.assertTrue(problems, "上游多要一個必填參數竟然沒紅 ⇒ 簽名契約沒有牙")
        joined = "\n".join(problems)
        self.assertIn("`ADL.gate._row_cells`", joined, "訊息未逐字指名簽名改變的那個引用")
        self.assertRegex(joined, r"本檔 :\d+ 傳入", "訊息未指出本檔的呼叫點行號")
        self.assertEqual(
            list(inspect.signature(ADL.gate._row_cells).parameters), ["line"],
            "真模組 `_row_cells` 的簽名被本測試污染了——替身突變不得外洩",
        )


class TestHardBlockOnUnwaivedRows(unittest.TestCase):
    """真實帳本家族：落入 §4.3.1 而條件未滿足的列，依射程規則該擋的就紅。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.family = read_family()
        cls.result = audit_family(cls.family, read_onboarding())

    def test_no_row_in_scope_violates_c1_or_c2(self) -> None:
        offenders = hard_block_offenders(self.result, _BASELINE_WAIVERS)
        self.assertEqual(
            offenders, {},
            "以下帳本列走 ADR-XPLAT-001 §4.3（凍結版不回補）但未滿足 C1／C2：\n"
            f"{_fmt(offenders)}\n"
            "C1＝該 DEF-ID 必須出現在 ONBOARDING.md §9 區段；"
            "C2＝分流或狀態欄必須寫出「重新評估／屆時」觸發條件。\n"
            "🔴 合法出口有兩個，都不需要動本鎖的豁免表："
            "①補齊 C1／C2；②依 §4.3.3 把狀態降為 `partial@R<n>（§4.3 條件未滿足）`。\n"
            f"（ADR 落地後的新列＝ID > {_BASELINE_ID_CEILING} 者，**不接受**豁免登記，"
            "搬進 archive 也一樣擋。）",
        )

    def test_waived_rows_do_not_fail_beyond_what_was_waived(self) -> None:
        """豁免是逐條件的：登記只寫 C2 的列若連 C1 也開始不合格，一樣要紅。"""
        overrun = {
            def_id: Finding(f.source, f.row, f.unmet - _BASELINE_WAIVERS[def_id].waived)
            for def_id, f in self.result.items()
            if def_id in _BASELINE_WAIVERS and f.unmet - _BASELINE_WAIVERS[def_id].waived
        }
        self.assertEqual(
            overrun, {},
            f"以下列的未滿足項超出其基線登記所豁免的範圍（逐條件豁免，不是整列免死）：\n"
            f"{_fmt(overrun)}",
        )

    def test_family_scan_surface_did_not_collapse(self) -> None:
        total = family_row_total(self.family)
        self.assertGreaterEqual(
            total, _MIN_FAMILY_ROWS,
            f"帳本家族只解析出 {total} 筆帳本列 < 下限 {_MIN_FAMILY_ROWS}——切格判準、"
            "家族枚舉或路徑疑似失效；本鎖拒絕在掃不到東西的情況下印綠燈。"
            "（帳本『只增不刪』＋歸檔守恆 ⇒ 這個總數只會往上；真的往下就是掃描面壞了。）",
        )

    def test_column_indices_agree_with_the_real_ledger_header(self) -> None:
        """寫死的欄位索引必須與**主檔表頭現查**一致，並與閘門的表頭定位結果對得上。

        本鎖的 `_IDX_*` 是寫死的位置索引，而閘門那側已改成由表頭欄名定位
        （`_table_layout()`，`DEF-101-580`）。兩邊漂移時的失敗模式都是靜默的：欄序被
        調動 ⇒ 判準改讀別欄（假綠或假紅）；欄數被調動 ⇒ 每一列都在
        `len(cells) != _N_COLS` 處被跳過。這道斷言把「散文寫的欄序」「寫死的索引」
        「磁碟上的真表頭」「閘門的定位結果」四者釘在一起，漂移當場紅。
        """
        text = _LEDGER.read_text(encoding="utf-8-sig")
        header = next((ln for ln in text.splitlines() if ADL.gate._HEADER_RE.match(ln)), None)
        self.assertIsNotNone(
            header, f"{MAIN_LEDGER_NAME} 查無合格表頭 ⇒ 本鎖的欄位定位失去依據")
        names = row_cells(header)
        self.assertEqual(
            (len(names), tuple(names)), (_N_COLS, _COL_HEADERS),
            f"主檔表頭與本檔宣告的欄序不一致：磁碟現查={tuple(names)}，"
            f"本檔 _COL_HEADERS={_COL_HEADERS}。\n"
            "改法：同步 _COL_HEADERS 與 _N_COLS／_IDX_ID／_IDX_DATE／_IDX_TRIAGE／_IDX_STATUS。",
        )
        self.assertEqual(
            tuple(_COL_HEADERS[i] for i in (_IDX_ID, _IDX_DATE, _IDX_TRIAGE, _IDX_STATUS)),
            (ADL.gate._ID_HEADER, "發現日期", "分流去向", ADL.gate._STATUS_HEADER),
            "索引常數沒有指到它該指的欄名（ID／發現日期／分流去向／狀態）",
        )
        self.assertEqual(
            ADL.gate._table_layout(text), (_N_COLS + 2, _IDX_ID + 1, _IDX_STATUS + 1),
            "閘門由表頭定位出的版面與本檔寫死的索引換算結果不一致"
            "（切片索引比欄位索引各多一，因 `_row_cells()` 保留首尾空片段）",
        )

    def test_adr_cited_exemplars_are_recognised_as_falling_rows(self) -> None:
        """ADR C1 逐字點名的 004／019／020／040 必須被判為落入 §4.3.1（判準與 ADR 對得上）。

        ADR 用縮寫連寫（`DEF-101-004／019／020／040`），故先對那整串字面做斷言，
        再逐一驗分類——避免用 `"DEF-101-019" in adr` 這種在縮寫下必然假紅的寫法。
        """
        self.assertIn(
            "DEF-101-004／019／020／040 的統一處置", read_adr(),
            "ADR C1 的統一處置正例清單被改寫了，請同步本測試的 cited 清單",
        )
        for def_id in ("DEF-101-004", "DEF-101-019", "DEF-101-020", "DEF-101-040"):
            with self.subTest(def_id=def_id):
                self.assertIn(
                    def_id, self.result,
                    f"{def_id} 是 ADR C1 逐字點名的統一處置正例，卻沒被判為落入 §4.3.1"
                    "——判準與 ADR 已脫鉤",
                )

    def test_adr_c2_exemplars_are_fully_compliant(self) -> None:
        """056／057 是 ADR C2 例文的來源（例文逐字抄它們），必須實測完全合規＝正控。"""
        for def_id in ("DEF-101-056", "DEF-101-057"):
            with self.subTest(def_id=def_id):
                finding = self.result.get(def_id)
                self.assertIsNotNone(
                    finding, f"{def_id} 是 ADR C2 的正例來源，卻沒被判為落入 §4.3.1"
                )
                assert finding is not None
                self.assertEqual(
                    finding.unmet, frozenset(),
                    f"{def_id} 是 ADR C2 的正例來源，若它都不合規，判準必有錯"
                    "（或該列被改壞了）",
                )
                self.assertNotIn(
                    def_id, _BASELINE_WAIVERS,
                    f"{def_id} 完全合規，不該出現在基線豁免表裡",
                )


class TestBaselineWaiverHygiene(unittest.TestCase):
    """具名基線豁免的防永久化自檢 ＋ 登記內容完整性。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.family = read_family()
        cls.index = family_row_index(cls.family)
        cls.result = audit_family(cls.family, read_onboarding())

    def test_baseline_waivers_are_not_stale(self) -> None:
        """(a) 被豁免的那一項一旦真的滿足了 → 紅，並指名刪掉該筆登記。"""
        stale: dict[str, list[str]] = {}
        for def_id, waiver in _BASELINE_WAIVERS.items():
            finding = self.result.get(def_id)
            if finding is None:
                continue  # 孤兒由下一支測試處理（那裡的訊息更精確）
            redundant = sorted(waiver.waived - finding.unmet)
            if redundant:
                stale[def_id] = redundant
        self.assertEqual(
            stale, {},
            "以下基線豁免已 stale（被豁免的條件現在已經滿足了）——**這是好消息，紅燈只是要你"
            "回收登記**：\n"
            + "\n".join(
                f"  · {k}：已滿足 {v} ⇒ "
                + ("整筆刪除" if set(v) == set(_BASELINE_WAIVERS[k].waived)
                   else f"把 {v} 從該筆的 waived 移除")
                for k, v in sorted(stale.items())
            )
            + f"\n改法：編輯 {_HERE.name}::_BASELINE_WAIVERS（整筆刪除時同步下修 "
              "_MAX_BASELINE_ENTRIES），無需改動任何生產碼或帳本。\n"
              "（豁免只能因為『條件還沒補』而存在，不能因為『沒人記得回收』而存在——"
              "這正是 R60 `_PENDING_MIGRATION_SITES` 被四方拆穿的形態。）",
        )

    def test_baseline_entries_still_exist_in_the_main_ledger_and_still_fall(self) -> None:
        """孤兒自檢：登記的列必須仍在**主檔**、且仍落入 §4.3.1（否則登記早該刪）。

        為何要求「在主檔」：本鎖對 ADR 落地前的 archive 列不設射程（見檔頭邊界），
        列一旦被歸檔，登記就不再遮蔽任何東西 ⇒ 留著等於憑空豁免，也會遮蔽「判準整體
        失效」這種假綠。
        """
        problems = []
        for def_id in sorted(_BASELINE_WAIVERS, key=_id_key):
            entry = self.index.get(def_id)
            finding = self.result.get(def_id)
            if entry is None:
                problems.append(f"{def_id}：帳本家族查無此列（改號／被刪？）")
            elif entry[0] != MAIN_LEDGER_NAME:
                problems.append(
                    f"{def_id}：該列已歸檔至 {entry[0]} ⇒ 已離開本鎖射程，此登記不再遮蔽"
                    "任何東西，必須刪除"
                )
            elif finding is None:
                problems.append(f"{def_id}：該列已不落入 §4.3.1（欄位敘述已改？）")
        self.assertEqual(
            problems, [],
            "以下基線豁免已無對應標的，登記必須刪除：\n  " + "\n  ".join(problems),
        )

    def test_baseline_cannot_admit_post_adr_rows(self) -> None:
        """(b) 基線 ID 上界：登記的每一列都必須是 ADR 落地前開的列。"""
        problems = baseline_admission_problems(_BASELINE_WAIVERS, self.index)
        self.assertEqual(
            problems, [],
            "以下登記結構上不得入表——**ADR 落地後的新列不得被 grandfather**。請走 "
            "ADR §4.3.3 的合法出口（狀態降為 `partial@R<n>（§4.3 條件未滿足）`）或直接"
            "補齊 C1／C2：\n  " + "\n  ".join(problems),
        )

    def test_baseline_admission_has_teeth_on_a_post_adr_row(self) -> None:
        """(b) 的鑑別力注入：這正是 SD-R60-R2-05 ① 用來證偽 round 2 日期日界的那個構造。

        SD 的構造＝「合成列的發現日期填 ADR 落地當日 ＋ 登記進表 ＋ 上限 +1」⇒ round 2
        全綠。改用 ID 上界後，同一個構造在**日期完全合法**（甚至等於上界列當天）的情況下
        仍必須紅，因為新列的 ID 必然大於上界。
        """
        ceiling_row = self.index.get(_BASELINE_ID_CEILING)
        self.assertIsNotNone(
            ceiling_row, f"基線上界 {_BASELINE_ID_CEILING} 必須是帳本家族裡真實存在的列"
        )
        assert ceiling_row is not None
        same_day = ceiling_row[1].date
        sid = _synthetic_id(101, _id_key(_BASELINE_ID_CEILING)[1] + 1)
        index = dict(self.index)
        index[sid] = (
            MAIN_LEDGER_NAME,
            Row(def_id=sid, date=same_day, triage="凍結版不回補",
                status="wontfix+凍結版紀律", lineno=1),
        )
        waivers = {**_BASELINE_WAIVERS,
                   sid: Waiver(frozenset({"C1", "C2"}), "x" * 41, "y" * 13)}
        problems = baseline_admission_problems(waivers, index)
        self.assertEqual(len(problems), 1, f"預期只指名合成新列一處，實得：{problems}")
        self.assertIn(sid, problems[0])
        self.assertIn("ADR 落地後才開的列", problems[0])

    def test_baseline_admission_also_rejects_a_back_numbered_late_row(self) -> None:
        """輔助判準的鑑別力：ID 回填成上界內的未用號碼，但發現日期晚於上界列 ⇒ 仍紅。"""
        ceiling_row = self.index[_BASELINE_ID_CEILING][1]
        ceiling_seq = _id_key(_BASELINE_ID_CEILING)[1]
        # 現查一個「上界內但尚未被用掉」的流水號——刻意不寫死號碼：帳本會繼續長，
        # 寫死的空號隨時可能被真的用掉（本測試初版就撞上真實列）。
        sid = next(
            (s for s in (_synthetic_id(101, n) for n in range(1, ceiling_seq))
             if s not in self.index),
            None,
        )
        self.assertIsNotNone(sid, "上界內找不到任何未用號碼——本測試的前提不成立")
        assert sid is not None
        index = dict(self.index)
        index[sid] = (
            MAIN_LEDGER_NAME,
            Row(def_id=sid, date="2099-01-01", triage="凍結版不回補",
                status="wontfix+凍結版紀律", lineno=1),
        )
        self.assertLess(ceiling_row.date, "2099-01-01", "合成日期必須晚於上界列日期")
        problems = baseline_admission_problems(
            {sid: Waiver(frozenset({"C2"}), "x" * 41, "y" * 13)}, index)
        self.assertEqual(len(problems), 1, f"預期只指名合成列一處，實得：{problems}")
        self.assertIn("疑似回填未用號碼的新列", problems[0])

    def test_baseline_admission_fails_loud_when_the_ceiling_is_unanchored(self) -> None:
        """上界本身抽不到對應列（打錯字／被刪）時必須紅，不得靜默放行全部登記。"""
        problems = baseline_admission_problems(_BASELINE_WAIVERS, {})
        self.assertEqual(len(problems), 1)
        self.assertIn("上界失去錨點", problems[0])

    def test_baseline_size_does_not_exceed_the_cap(self) -> None:
        """筆數不得超過上限常數。

        ⚠️ 這一支**只**保證「≤ 上限」；「上限只准往下改」由 `TestShrinkOnlyRatchet`
        機械保證。round 2 只有這一支卻在檔頭宣稱有 shrink-only 機制，SD 實測把上限改大
        不會紅（改小才紅）＝宣稱與實作不符，故拆成兩件事並各自說清楚。
        """
        self.assertLessEqual(
            len(_BASELINE_WAIVERS), _MAX_BASELINE_ENTRIES,
            f"基線豁免筆數 {len(_BASELINE_WAIVERS)} > 上限 {_MAX_BASELINE_ENTRIES}。"
            "要往上改請先讀本檔檔頭的設計說明並在 PR 說明為何 §4.3.3 的降級出口不適用"
            "（且棘輪會擋下調升）",
        )

    def test_every_waiver_documents_why_and_owner(self) -> None:
        """登記必附「為何當時沒滿足」與「承接者」，且豁免項只能是 C1／C2。"""
        for def_id, waiver in sorted(_BASELINE_WAIVERS.items()):
            with self.subTest(def_id=def_id):
                self.assertTrue(waiver.waived, "豁免項不得為空集合（那是無意義的登記）")
                self.assertLessEqual(waiver.waived, {"C1", "C2"})
                self.assertGreaterEqual(len(waiver.why), 40, "『為何當時沒滿足』太短，不算交代")
                self.assertGreaterEqual(len(waiver.owner), 12, "『承接者』必須具名到人／包")

    def test_every_waiver_owner_names_a_round_or_declares_unassigned(self) -> None:
        """承接者必須指向存在的輪次或明標「未指派」（R59 硬規則②，見 Scan_Dimensions）。

        round 2 寫「下次觸及本列的輪次」＝非具名輪次，兩者皆不是 ⇒ 正是該規則要擋的死信。
        """
        for def_id, waiver in sorted(_BASELINE_WAIVERS.items()):
            with self.subTest(def_id=def_id):
                named_round = re.search(r"R\d+", waiver.owner) is not None
                self.assertTrue(
                    named_round or "未指派" in waiver.owner,
                    f"{def_id} 的承接者既未指名輪次（R<n>）也未明標「未指派」："
                    f"{waiver.owner!r}",
                )

    def test_baseline_disclosure_in_adr_section_7_is_biconditional(self) -> None:
        """基線豁免存在 ⟺ ADR §7「未結落差」必須揭露它（**雙向**，故永不空轉）。

        · 表裡還有登記卻把 ADR §7 的揭露列刪掉 ⇒ 紅（豁免只活在程式碼裡、外部看不到）。
        · 表已清空卻還留著揭露列 ⇒ 紅（違反 ADR §7 自訂的「閉合即刪，不留歷史狀態」）。
        這是刻意寫成雙條件而非 `if waivers: assert ...`——後者在表清空後就變成恆綠空測試，
        正是 R60 四方複審拆穿的那類假綠。
        """
        sec7 = adr_section_7(read_adr())
        self.assertEqual(
            "_BASELINE_WAIVERS" in sec7, bool(_BASELINE_WAIVERS),
            "ADR §7 對本檔基線豁免的揭露與實況不一致："
            f"表內筆數={len(_BASELINE_WAIVERS)}、§7 提及={'_BASELINE_WAIVERS' in sec7}。"
            "還有豁免就必須在 §7 具名揭露；豁免清空了就必須把那一列刪掉（§7 自訂規則：閉合即刪）。",
        )


class TestShrinkOnlyRatchet(unittest.TestCase):
    """(c) shrink-only 棘輪：兩個門檻常數只准往下改，對 HEAD 版本機械比對。

    WHY 這一類必須存在（SD-R60-R2-05 ②）：round 2 的「shrink-only」只是檔頭的一句宣稱，
    唯一的斷言是「筆數 ≤ 上限」——SD 實測把上限往上改**不會紅**。宣稱有機制而實際沒有，
    比老實承認是人審慣例更糟，因為它讓讀者停止懷疑。
    """

    def test_extraction_is_not_vacuous_on_the_current_source(self) -> None:
        """正控：抽取器對本檔現行原始碼必須抽得到兩個常數，且自比自為零違規。

        這支的作用是防「正則被改壞 ⇒ 抽不到 ⇒ 棘輪永遠沉默」：抽不到會被
        `ratchet_problems` 當違規報出來，故本斷言同時覆蓋抽取器本身。
        """
        self.assertEqual(
            ratchet_problems(_HERE.read_text(encoding="utf-8"),
                             _MAX_BASELINE_ENTRIES, _BASELINE_ID_CEILING),
            [],
        )

    def test_raising_either_constant_is_detected(self) -> None:
        """注入：餵一份「上一版較低」的合成原始碼 ⇒ 兩個常數的調升都必須被逐一指名。"""
        prev = (
            "_MAX_BASELINE_ENTRIES = 1\n"
            f'_BASELINE_ID_CEILING = "{_synthetic_id(1, 1)}"\n'
        )
        problems = ratchet_problems(prev, _MAX_BASELINE_ENTRIES, _BASELINE_ID_CEILING)
        self.assertEqual(len(problems), 2, f"預期兩個常數各報一處，實得：{problems}")
        self.assertIn("_MAX_BASELINE_ENTRIES", problems[0])
        self.assertIn("_BASELINE_ID_CEILING", problems[1])

    def test_lowering_or_keeping_constants_is_accepted(self) -> None:
        """對照組：上一版較高（＝本版下修）或完全相同 ⇒ 零違規。"""
        higher = (
            f"_MAX_BASELINE_ENTRIES = {_MAX_BASELINE_ENTRIES + 1}\n"
            f'_BASELINE_ID_CEILING = "{_synthetic_id(999, 1)}"\n'
        )
        self.assertEqual(
            ratchet_problems(higher, _MAX_BASELINE_ENTRIES, _BASELINE_ID_CEILING), [])

    def test_renaming_a_constant_is_reported_not_silently_skipped(self) -> None:
        """改名／改寫常數不得讓棘輪靜默失效——抽不到就是紅。"""
        problems = ratchet_problems("# 上一版把常數改名了\n",
                                    _MAX_BASELINE_ENTRIES, _BASELINE_ID_CEILING)
        self.assertEqual(len(problems), 2)
        for problem in problems:
            self.assertIn("棘輪等於失效", problem)

    def test_constants_never_increase_versus_head(self) -> None:
        """真棘輪：與 HEAD 版本比對。

        HEAD 尚無本檔（新增檔／首版）時 `skipTest`——**不是靜默 return**：
        `run_root_unittests.py::report_all_skips` 會逐處印出全部 skip 的 id 與理由，
        所以這個 fallback 在每一次閘門輸出裡都看得見。它也不是永久逃生口：本檔一旦進入
        HEAD，棘輪即永久生效，要再回到此分支必須在 diff 裡把本檔從版控刪掉（藏不住）。
        鑑別力另由本類的合成上一版測試永久釘住，不依賴 git 狀態。
        """
        previous = read_previous_self_source()
        if previous is None:
            self.skipTest(
                f"HEAD 尚無 {_SELF_REL}（本檔為未提交的新增檔）⇒ 無上一版可比，棘輪本輪空轉；"
                "commit 後即永久生效。鑑別力見 test_raising_either_constant_is_detected"
            )
        problems = ratchet_problems(previous, _MAX_BASELINE_ENTRIES, _BASELINE_ID_CEILING)
        self.assertEqual(
            problems, [],
            "shrink-only 棘輪被違反（與 HEAD 版本比對）：\n  " + "\n  ".join(problems)
            + "\n這兩個常數是「哪些列算舊列」與「能登記幾筆」的唯一開關，調升等於為新列開門。",
        )


# 本檔自己也受「散文不得寫死可機械算出的計數」這條紀律管（P2-6）。量詞白名單刻意窄：
# 這幾個字就是 round 2 實際犯規處用的量詞（一處寫死豁免筆數、一處寫死帳本列數、
# 一處寫死「一次紅 N 個」）。`(?<![§\d])` 用來排除節號引用（例：§9 後面接「列」字）。
_BARE_COUNT_RE = re.compile(r"(?<![§\d])\d+\s*[筆列個支處]")


class TestThisLockObeysItsOwnNoHardcodedCountRule(unittest.TestCase):
    """本檔檔頭訂了「筆數不寫在散文裡」，round 2 版本自己在幾十行後違反了它。

    ARCH-R60R2-04／SD-R60-R2-06 逐字抓到三處：寫死豁免筆數（實況已與之不符）、寫死帳本
    列數（實況已與之不符）、以及「一次紅 N 個」。訂正方式不是「把數字改成新的正確值」
    ——那只是把過期時點往後挪一輪——而是改成不引數字的寫法。本類把這條紀律機械化。

    邊界（誠實劃界）：只擋「阿拉伯數字＋筆／列／個／支／處」這幾種量詞的寫法，**不是**
    通用的「散文寫死數字」偵測器。換量詞、寫成中文數字、或把計數藏進變數名都抓不到；
    真正通用的判準需要語意理解，本鎖不假裝有。門檻常數自己（例如上限與掃描面下限）不受
    此限——它們是該數字的唯一真相源，不是散文複本。
    """

    def test_no_bare_count_with_a_measure_word_anywhere_in_this_file(self) -> None:
        hits = []
        for lineno, line in enumerate(_HERE.read_text(encoding="utf-8").splitlines(), 1):
            for m in _BARE_COUNT_RE.finditer(line):
                hits.append(f"{_HERE.name}:{lineno}：{m.group(0)!r} ← {line.strip()}")
        self.assertEqual(
            hits, [],
            "本檔散文寫死了可機械算出的計數（違反自己檔頭訂的紀律）：\n  "
            + "\n  ".join(hits)
            + "\n改法：改成不引數字的寫法（例：「表內每一筆登記都會找不到對應列 ⇒ 一次全紅」"
              "／「列數以 family_row_total() 現查為準」），**不要**把舊數字改成新數字"
              "——那只是把過期時點往後挪一輪。",
        )

    def test_the_detector_itself_has_teeth(self) -> None:
        """注入：把 round 2 真正寫過的兩種形態餵進偵測器，必須全部命中。"""
        for sample in (
            "# 掃描面一崩塌，" + str(10) + " 筆登記會同時找不到對應列 ⇒ 一次紅 " + str(10) + " 個",
            "# R60 round 2 實測 " + str(115) + " 列",
        ):
            with self.subTest(sample=sample):
                self.assertTrue(_BARE_COUNT_RE.search(sample), "偵測器對真實犯規形態失效")

    def test_the_detector_does_not_flag_section_references(self) -> None:
        """對照組：`§9 列`／`§10 列` 這類節號引用不得誤報（本檔散文大量使用）。"""
        for sample in ("補一列進 §9 列表", "見 §10 列的敘述"):
            with self.subTest(sample=sample):
                self.assertIsNone(_BARE_COUNT_RE.search(sample))


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
