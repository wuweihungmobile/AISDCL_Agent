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
  `TestThisLockObeysItsOwnNoHardcodedCountRule` 機械自檢——round 2 的版本在宣告這條紀律的
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
        由 `TestShrinkOnlyRatchet` 對**簽入本檔的凍結基準**機械比對。
        🔴 round 2 的版本這一條只是**人審慣例冒充機制**：它只斷言「筆數 ≤ 上限」，SD 實測把
        上限改大**不會紅**（改小才紅）。
        🔴🔴 R67 round 2（SA-R67-08）**再次訂正比對基準**：改真棘輪時照抄的是
        `git show HEAD:<本檔>` 形狀，而該形狀在**真正消費它的時點**（pre-push 必然發生在
        commit 之後、CI 更是乾淨 checkout）HEAD 逐字等於工作樹 ⇒ 比較退化、恆真。SA 沙箱
        實證：`_MAX_BASELINE_ENTRIES` 由現值改成放大十餘倍後 commit，本類全綠零訊號。
        這與同輪 R67-H14 在 `tools/check_script_parity.py` 修掉的是同一個病（那一支是照抄
        本檔而來的），本輪把本體也修了：基準改為簽入本檔的凍結常數，整條 git 依賴移除。
    (d) **護欄層行數棘輪**（`TestGuardLayerRatchet`，round 3 ARCH-R60R3-04 立案、R77 換量）：
        `DEF-101-561③` 裁定「R61 開輪即禁止新增鎖檔、只准合併／刪除」，而該裁決原本零機械
        強制。R77 把量測面由「檔數」換成逐檔行數表（`_FROZEN_GUARD_LINES`）——檔數被釘住之後
        成長全部灌進既有巨檔，同期行數翻倍而唯一的判準全程綠。
        🔴 **接手者的語意不是「禁止新增檔案」**（R78 ARCH-03：散落各處的引用逐字這樣寫，那是
        對已移除機制的複述）：新表管的是**淨行數**，新增鎖檔只要同一次變更內刪掉等量以上的
        行就合法；反之只改既有檔卻淨增一行照樣紅。重釘須留稽核痕跡，見 `_GUARD_LINES_REPIN_LOG`。

另加一組**標的是 `ADR-XPLAT-002` §9.1 與 `CrossPlatform_Scan_Dimensions.md`〈常設自檢〉**的
常設不變式（`TestSection91*` 三類，R67 round 2 SA-R67-03 的落地）：那兩處把跨平台三項頭號
架構異動的防回流判準寫成 grep 指令，卻**零可執行消費者**（注入違規形態後全 repo 綠燈）。
本檔是 §9.1 末段**具名指派**的承接容器。細節見檔內「ADR §9.1／掃描維度 常設自檢（SC-*）」段。

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
     🔴 **這個繞道的可觸達性不是理論**（round 3 SD-R60R3-06 以生產物件實算）：
     **上界以下的未使用號碼現查即有**一批空號可用，不需要任何運氣——SD 逐一驗過三種構造：
     (i) 只回填空號＝綠（設計上放行）；(ii) 空號＋不晚於上界列的日期＝**綠，雙欄位造假成立**；
     (iii) 空號＋誠實日期＝紅（輔助判準擋掉單欄位造假那一半）。
     擋住它的是**可見度**不是稀缺性：光加一筆豁免登記還不夠（`test_baseline_waivers_are_not_stale`
     會把找不到對應 §4.3.1 標的的登記判為多餘而紅），必須連帶在帳本偽造一列，那是刻意動作、
     diff 上看得見。空號的**數量與號碼由 `unused_ids_below_ceiling()` 現算**，刻意不寫進這段
     散文——寫了就是下一個 stale 站點（帳本開新號就會少一個），而且會立刻被本檔自己的
     `TestThisLockObeysItsOwnNoHardcodedCountRule` 判為犯規；這段措辭與現況是否同步由
     `TestIdCeilingBypassReachabilityIsLive` 雙向機械綁定。
  ❌ **兩道棘輪都只保證「淨額不惡化」，不保證每一列在每個時點與磁碟逐字相符**：常數棘輪比的
     是簽入本檔的凍結常數（R67 round 2 起整條 git 依賴已移除，不再有「首個 commit 空轉」
     那個舊形態），行數棘輪比的是 `_FROZEN_GUARD_LINES` 這張表的**總量**——淨額為零的
     「A 減 B 增」對調兩者都不會說話（見 `guard_line_problems` 的誠實劃界段）。
     兩者的鑑別力皆以合成注入永久釘住，不依賴工作樹當下剛好處於哪個狀態。
  ⚠️ **不要因為這道鎖是綠的就以為 §4.3 已被完全保證。**

執行：python tools/run_root_unittests.py
      python -m unittest tools.tests.test_adr_xplat001_c1c2_lock -v
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import re
import sys
import unittest
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import NamedTuple
from unittest import mock

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
_MAX_BASELINE_ENTRIES = 2

_BASELINE_WAIVERS: dict[str, Waiver] = {
    # R74 刪除一筆：該列已隨本輪歸檔離開主檔 ⇒ 已在本鎖射程外，登記若留著就是在遮蔽一個
    # 不存在的標的（本鎖自帶的 stale 自檢會判紅，正確處置是刪登記而非放寬判準）。
    # 本輪刪除一筆（`DEF-101-324`）：ADR-XPLAT-011 §2 正式裁決後，帳本狀態欄已改寫為
    # 「closed-by-decision｜ADR-XPLAT-011 §2 正式裁決」，不再出現「凍結基線」與
    # 「wontfix」同格字樣 ⇒ 該列**已不落入 §4.3.1**（同 `_BASELINE_ID_CEILING` 上方
    # DEF-101-534／552 的先例：敘述已據實訂正，不是條件被 grandfather 掉，正確處置是
    # 刪登記而非放寬判準）。孤兒自檢 `test_baseline_entries_still_exist_in_the_main_
    # ledger_and_still_fall` 當場攔下並逐字指名，即本次修復依據。
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


# 檔頭邊界①（「ID 上界擋不住雙欄位造假」）對**可觸達性**的揭露錨點。
# `TestIdCeilingBypassReachabilityIsLive` 以雙條件把這句話與 `unused_ids_below_ceiling()`
# 的現查結果綁在一起：空號還在就必須留著這句、空號用光就必須改寫它。
_REACHABILITY_DISCLOSURE = "上界以下的未使用號碼現查即有"


def unused_ids_below_ceiling(index: dict[str, tuple[str, Row]], ceiling: str) -> list[str]:
    """`ceiling` 同一輪次底下、帳本家族**從未使用過**的流水號（由小到大）。

    兩個用途：
      ① 注入測試需要「一個保證不撞到真實列的上界內號碼」時現查取號——寫死號碼會被長大的
         帳本用掉（`test_baseline_admission_also_rejects_a_back_numbered_late_row` 初版就
         撞上過真實列）。
      ② 讓檔頭邊界①「ID 上界擋不住兩個欄位同時造假」那句話的**可觸達性是活的**：空號有
         幾個、是哪幾個，由本函式現算，一律不寫進散文（round 3 SD-R60R3-06）。

    號碼字串一律交給 `_synthetic_id()` 組（它就是本檔的 ID 格式器）。此處組出來的號碼
    依定義是帳本家族查無的空號，所以仍然不構成對任何真實缺陷的引用——
    `test_defect_id_reference_integrity.py` 的全庫 DEF-ID 稽核不會被它踩到。
    """
    round_no, ceiling_seq = _id_key(ceiling)
    return [
        sid
        for sid in (_synthetic_id(round_no, n) for n in range(1, ceiling_seq))
        if sid not in index
    ]


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


# ---------------------------------------------------------------- shrink-only 棘輪（對凍結基準比對）
_SELF_REL = f"tools/tests/{_HERE.name}"  # git 路徑一律 posix，不用 os.sep
_RATCHET_MAX_RE = re.compile(r"^_MAX_BASELINE_ENTRIES\s*=\s*(\d+)", re.M)
_RATCHET_CEILING_RE = re.compile(r"^_BASELINE_ID_CEILING\s*=\s*\"(DEF-\d+-\d+)\"", re.M)

# 🔴🔴 R67 round 2（SA-R67-08）凍結基準：兩個 shrink-only 常數的「上一版」不再由 git 導出
# ——git 導出基準對跑在 commit 之後的每個閘門恆真（SA 沙箱實證＝Guard_Repin 證據檔 §B-11），
# 簽入字面常數才讓「門檻」與「基準」是兩個獨立可變的量。病灶、殘餘面（同 commit 內同時改
# 門檻與基準仍可通過——釘選式棘輪共有邊界）與 `_BASELINE_ID_CEILING` 連動 ADR §4.3.4 的
# 第三站點張力，全文搬至 CrossPlatform_Guard_Line_History.md〈凍結基準不由 git 導出 WHY〉節。
# 機械鎖＝`TestShrinkOnlyRatchet::test_ratchet_is_independent_of_git_state`
# （禁用 subprocess 仍須完整運作），舊實作在該鎖下會直接紅。
_FROZEN_MAX_BASELINE_ENTRIES = 2
_FROZEN_BASELINE_ID_CEILING = "DEF-101-526"


def _shrink_only_problems(
    previous_max: int | None, previous_ceiling: str | None,
    current_max: int, current_ceiling: str,
) -> list[str]:
    """判準核心（唯一實作）：比對「上一版」與現版的兩個 shrink-only 常數。

    `previous_*` 為 `None` 代表**抽取失敗**（常數被改名／改寫），一律當違規報出來，
    不得靜默略過——那是最需要被看見的失敗模式（同型教訓＝`_PENDING_MIGRATION_SITES`
    靠「不加自檢」變成永久豁免）。

    `ratchet_problems()`（合成上一版原始碼，鑑別力載具）與 `frozen_ratchet_problems()`
    （凍結基準，production 路徑）共用本函式——判準只有一份，不會出現「測試驗的那條路和
    production 走的那條路判準不同」。
    """
    problems: list[str] = []
    if previous_max is None:
        problems.append(
            "上一版抽不到 _MAX_BASELINE_ENTRIES —— 常數被改名／改寫？棘輪等於失效，拒絕靜默通過"
        )
    elif current_max > previous_max:
        problems.append(
            f"_MAX_BASELINE_ENTRIES 由 {previous_max} 調升為 {current_max} —— 本常數只准往下改"
        )
    if previous_ceiling is None:
        problems.append(
            "上一版抽不到 _BASELINE_ID_CEILING —— 常數被改名／改寫？棘輪等於失效，拒絕靜默通過"
        )
    elif _id_key(current_ceiling) > _id_key(previous_ceiling):
        problems.append(
            f"_BASELINE_ID_CEILING 由 {previous_ceiling} 調升為 {current_ceiling} —— 調升上界"
            "等於為 ADR 落地後的新列開門"
        )
    return problems


def ratchet_problems(previous_source: str, current_max: int, current_ceiling: str) -> list[str]:
    """**鑑別力載具**：比對任意一份「上一版原始碼」與現版常數；空清單＝只降不升。

    🔴 R67 round 2：production **不再**把 `git show HEAD:<本檔>` 餵進來（見上方凍結基準
    區塊的恆真論證）。本函式保留的職責是「抽取器 + 判準」的鑑別力載具：測試以合成的
    上一版原始碼逐一注入調升／下修／改名形態，證明會紅／不會誤紅；而判準核心
    `_shrink_only_problems()` 與 production 的 `frozen_ratchet_problems()` 是同一份實作。
    """
    m = _RATCHET_MAX_RE.search(previous_source)
    previous_max = int(m.group(1)) if m else None
    m = _RATCHET_CEILING_RE.search(previous_source)
    previous_ceiling = m.group(1) if m else None
    return _shrink_only_problems(previous_max, previous_ceiling, current_max, current_ceiling)


def frozen_ratchet_problems(
    current_max: int | None = None, current_ceiling: str | None = None,
    frozen_max: int | None = None, frozen_ceiling: str | None = None,
) -> list[str]:
    """**production 棘輪**：現行門檻 vs 簽入本檔的凍結基準（R67 round 2 SA-R67-08）。

    刻意**不呼叫 git**：基準是簽入的字面常數，故本函式在髒樹／乾淨樹／CI checkout 行為
    完全相同。`test_ratchet_is_independent_of_git_state` 以「禁用 subprocess」機械守住。
    """
    return _shrink_only_problems(
        _FROZEN_MAX_BASELINE_ENTRIES if frozen_max is None else frozen_max,
        _FROZEN_BASELINE_ID_CEILING if frozen_ceiling is None else frozen_ceiling,
        _MAX_BASELINE_ENTRIES if current_max is None else current_max,
        _BASELINE_ID_CEILING if current_ceiling is None else current_ceiling,
    )


# ---------------------------------------------------------------- 護欄層掃描面（DEF-101-561③）
_GUARD_DIR_REL = "tools/tests"
# 計數面＝根層閘門的 discovery pattern。這裡的字面值由
# `TestGuardLayerRatchet::test_the_counted_surface_is_the_root_gate_pattern`
# 與 `run_root_unittests._PATTERN` 雙向綁定（那支才是 SSOT，本常數只是不想在 import 期
# 付 `_stdio_utf8` 的副作用代價而做的鏡像；兩邊漂移即紅）。
_GUARD_FILE_PATTERN = "test_*.py"
# 列舉時要跳過的快取目錄：它們不進版控，算進工作樹側會讓兩邊基準不同。
_CACHE_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})


def guard_files_in_worktree() -> frozenset[str]:
    """工作樹現況的鎖檔集合（相對 repo 根的 posix 路徑）。

    兩個刻意的選擇：
      · **含未追蹤檔**：新鎖一落到磁碟上就該被算進去，不必等 commit——否則「先加檔、
        收輪時才一起 commit」可以整輪繞過本棘輪。
      · **遞迴列舉**：非遞迴 glob 對「新增子目錄裡的鎖檔」是漏的，同輪 SD-R60R3-03 在
        `sync_onboarding_baselines._FINGERPRINT_TREES` 上實測過這種漏法（改 top-level
        檔→紅、新增 top-level 檔→紅、**新增子目錄檔→綠**）。那一筆的修法是「把不對稱
        消掉」，本檔新加的東西沒有理由再引進同一個形狀。
    """
    root = _REPO / _GUARD_DIR_REL
    return frozenset(
        p.relative_to(_REPO).as_posix()
        for p in root.rglob(_GUARD_FILE_PATTERN)
        if not _CACHE_DIR_NAMES & set(p.parts)
    )


# ------------------------------------------- 護欄層逐檔行數棘輪（本輪；接手 DEF-101-561③）
# 🔴 立案 WHY（純量檔數棘輪→逐檔行數表的動機、(a)(b)(c) 三件承接、重釘紀律）全文搬至
# CrossPlatform_R97_Scan_Findings.md〈護欄層逐檔行數棘輪 WHY〉節（本輪收斂 +1023 超額
# 動作之一，純敘事搬遷、判準與行為不變）。重釘指令仍是：
# `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`

#: 行數面的 glob——**非遞迴 `*.py`**，逐字等於 ADR §4.3 GLC 現查指令用的那一個。
#: 刻意與 `_GUARD_FILE_PATTERN`（遞迴 `test_*.py`）分開：後者是「閘門會跑哪幾支」，
#: 前者是「這一層有多大」。兩個量不同名也不同義，混用會讓 ADR 的指令與本檔的數字對不
#: 起來；涵蓋關係改由 `guard_baseline_gaps()` 證明，而不是把兩個面硬併成一個
#: （🔴 R78 ARCH-04：R77 寫下這句時那個函式並不存在——AST 實查零定義。本輪補上實作＋
#:  `test_the_two_surfaces_have_no_coverage_gap`，讓這句宣稱有東西承接）。
_GUARD_LINE_PATTERN = "*.py"

#: 基準與實況的**縮小**容忍帶。🔴 這不是成長緩衝——成長側零容忍（見 `glc_growth_problem`）。
#: 形狀照抄 `test_subprocess_encoding_hygiene.tree_count_verdict()` 的雙邊帶：單邊棘輪
#: 只會腐化，縮下來卻不重釘的話，餘裕就是日後無聲加回去的破口（同 SA-R67-08 的裁決）。
_GUARD_LINE_STALE_SLACK = 0.02

#: 逐檔行數的**凍結基準**（R77 PKG-GUARD／R77-24：取代已於同輪移除的檔數棘輪常數）。
#: 取值紀律同 `_TIER_BASELINE`：**當回合實測直接填入、零加減推算、不留成長緩衝**。
#:
#: 🔴 為何檔數棘輪退場、行數表接手（成長全部灌進既有巨檔而閘門全程綠）——立案原文＝
#: Guard_Repin 證據檔 §B-2；方向仍是收緊（成長側零容忍，見 `glc_growth_problem`）。
#:
#: 維護方式（不是「調高就好」）：合法縮小後**必須**同步下修本表，否則餘裕就是日後無聲
#: 加回去的破口（`[基準過時]` 那一款在守這件事）。真的必須長大時，重釘本表並在交件回報
#: 寫出淨額與理由——讓方向在 diff 上一望即知。
#: 🔴 本表含**本檔自己**，所以動本檔就會動到本表 ⇒ 改完必須重跑一次並用實測值收斂。
_FROZEN_GUARD_LINES: dict[str, int] = {
    "_platform_helpers.py": 407,
    "_ps_engine.py": 115,
    "test_act_local_runner_image.py": 322,
    "test_adr_xplat001_c1c2_lock.py": 7278,
    "test_apply_lock.py": 167,
    "test_archive_apply_locked.py": 102,
    "test_archive_defect_log.py": 3839,
    "test_bash32_compat.py": 1020,
    "test_bash_probe_spec_contract.py": 865,
    "test_block_destructive_git_r83.py": 2288,
    "test_bootstrap_core.py": 439,
    "test_bootstrap_ps1.py": 160,
    "test_check_archive_required.py": 160,
    "test_check_defect_log_crossref.py": 3891,
    "test_check_gha_action_versions.py": 295,
    "test_check_hooks_liveness.py": 3296,
    "test_check_pytest_baseline_sites.py": 301,
    "test_check_script_parity.py": 2098,
    "test_check_wrapper_thinness.py": 1234,
    "test_claim_provenance_r86.py": 618,
    "test_component_sanitizer_shared_layer_lock.py": 293,
    "test_context_budget_guard.py": 9902,
    "test_defect_id_reference_integrity.py": 281,
    "test_dev_start.py": 6527,
    "test_dev_start_ps1_lastexitcode.py": 548,
    "test_doc_env_prefix_platform_parity_r60.py": 340,
    "test_doc_loc_baseline_freshness_r60.py": 7131,
    "test_extras_quoting_zsh_safety.py": 365,
    "test_failure_log_rotation.py": 80,
    "test_find_git_bash_parity.py": 1264,
    "test_gha_action_versions.py": 703,
    "test_git_hooks_install_common.py": 393,
    "test_guard_line_taxonomy_r99.py": 148,
    "test_install_windows_nightly.py": 1385,
    "test_mac_endurance_r83.py": 1784,
    "test_mac_readiness_r82.py": 621,
    "test_macos_smoke_skip_honesty.py": 225,
    "test_maturity_criteria_r79.py": 431,
    "test_negative_existence_claims_r82.py": 380,
    "test_nightly_interpreter_determinism.py": 278,
    "test_no_invalid_escape_sequences.py": 329,
    "test_ntfs_trailing_space_device_name.py": 760,
    "test_onboarding_parity_interlock.py": 233,
    "test_platform_neutral_paths.py": 5720,
    "test_platform_utils_dedup.py": 1104,
    "test_pre_commit_dispatcher_sigpipe.py": 964,
    "test_pre_push_dispatcher.py": 686,
    "test_ps1_bom.py": 248,
    "test_ps51_compat.py": 610,
    "test_ps_engine_ssot.py": 954,
    "test_python_c_percent_shim.py": 119,
    "test_quota_policy.py": 3406,
    "test_root_infra_parity.py": 441,
    "test_run_root_unittests.py": 2428,
    "test_sanitize_component_frozen_sdd_versions_lock.py": 340,
    "test_schedule_capability_parity.py": 626,
    "test_script_scan_surface_ssot.py": 391,
    "test_skip_ceiling_ratchet_direction.py": 700,
    "test_skip_discoverability_r83.py": 744,
    "test_smoke_ci_sync.py": 1353,
    "test_stdio_utf8.py": 76,
    "test_subprocess_encoding_hygiene.py": 1599,
    "test_windows_forbidden_filename_parity.py": 1025,
    "test_windows_nightly_anchor_parity.py": 135,
    "test_windows_smoke_heartbeat_doc_sync.py": 197,
    "test_windowsapps_guard_bash_parity.py": 973,
    "test_windowsapps_guard_cross_consistency.py": 2183,
    "test_workflow_permission_concurrency_lock.py": 1417,
    "test_workflow_schedule_sync.py": 309,
    "test_workflow_timeout_coverage.py": 158,
    "test_worktree_paths.py": 104,
}


#: 重釘稽核痕跡（**append-only**）：`(輪號, 舊總量, 新總量, 淨額, 理由)`。
#:
#: 🔴 R78 ARCH-01 的落地物（缺陷本體：整張表同時變而淨額不出現在任何地方，與「順手
#: 更新一下」機械上無法區分）——立案實測原文＝Guard_Repin 證據檔 §B-1。
#:
#: 本表把淨額變成**結構上不可能缺席**的東西：`test_the_repin_log_accounts_for_the_frozen_table`
#: 斷言「表尾那一列的新總量必須逐字等於 `sum(_FROZEN_GUARD_LINES.values())`」⇒ 動了那張表
#: 而不補一列理由，當場紅；補了列卻算錯淨額，也紅（逐列自洽 ＋ 首尾相接）。
#: 維護方式：`--print-guard-lines` 會連這一列的草稿一起印出來，照貼即可。
_GUARD_LINES_REPIN_LOG: tuple[tuple[str, int, int, int, str], ...] = (
    (
        "R81", 65390, 67759, 2369,
        "R81 **十一個並行包的一次性重釘**，由收尾者在全部包停工後的單人窗口做 ⇒ rc 可歸因。"
        "🔴 **[非淨減法輪]** —— 逐檔清單與逐項必要性辯護落在 "
        "docs/06_quality/CrossPlatform_R81_Scan_Findings.md 的 §B（沿用 R80 §B 系列的體例："
        "同一件事只有一個家；本列刻意不逐檔登載數字，那會再造一個沒有人會回頭改的量測站點）。"
        "🔴 **誠實歸因：成長全在護欄層（測試），而生產碼是淨減的**——hook payload 的"
        "手抄本全數收斂進共用層（`tools/lib/platform_utils.py`）在生產側淨 −39 行，其中收尾者"
        "本人刪掉 `context_budget_guard.py` 的 21 行。護欄層之所以只增不減，是因為本輪"
        "新開的判準面此前**一個觀測者都沒有**，沒有等量的舊判準可以退場去換："
        "額度節流的 80/95 兩道門（額度與 context 是兩個分母，撞額度那刻水位可能僅 ~18%，"
        "每一道 context 守衛都會放行）；跨平台 5 類新登記危害的門（`$env:TEMP`／`TMP` 站點級、"
        "`Get-Command` 裸解析只准住 SSOT、bash 3.2 語法面、以及**自陳沒人守的證偽探針**——"
        "後者治的是低報分子，它與過報同樣讓「還有幾類沒人守」這個治理數字失真）；"
        "Q4 的首道宣稱對帳機械物（本輪重跑失誤分群後最大桶＝宣稱先於查證，而那一桶"
        "此前完全沒有機械物：它發生在 inline 指令字串與 rc 讀數上，永遠不會變成 repo 裡的"
        "檔案，所有靜態掃描器結構上看不到）；`.sh`／`.ps1` 行為等價；"
        "以及 hook payload SSOT 的回歸鎖（各檔手抄本實測已彼此漂移，其中阻斷級"
        "`enforce_docs_path.py` 餵頂層非 object 的合法 JSON 時 rc=1 AttributeError＝"
        "守衛還在、判定沒產出）。"
        "🔴 本輪未刪任何行換取餘裕、未調高任何門檻、未放寬任何棘輪、未動漂移容忍值。"
        "唯一往**下**釘的是 `OVERSIZE_ROW_EXCESS_CEILING`（138938→138936，−2），"
        "來源是收尾者訂正 `DEF-101-870` 一列的兩處措辭，理由見同一份文件的 §C。",
    ),
    ("R81", 67759, 67908, 149,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R81_Scan_Findings.md"),
    ("R81", 67908, 67950, 42,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R81_Scan_Findings.md"),
    ("R81", 67950, 68393, 443,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R81_Scan_Findings.md"),
    ("R81", 68393, 68423, 30,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R81_Scan_Findings.md"),
    ("R82", 68423, 72098, 3675,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R82_Scan_Findings.md"),
    ("R82", 72098, 73766, 1668,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R82_Scan_Findings.md"),
    ("R82", 73766, 73823, 57,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R82_Scan_Findings.md"),
    ("R83", 73823, 79083, 5260,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R83_Scan_Findings.md"),
    ("R84", 79083, 81738, 2655,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R84_Scan_Findings.md"),
    ("R84", 81738, 82838, 1100,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R84_Scan_Findings.md"),
    ("R85", 82838, 82838, 0,
     "逐檔清單＝CrossPlatform_R85_Scan_Findings.md"),
    ("R85", 82838, 83320, 482,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R85_Guard_Repin_Evidence.md"),
    ("R85", 83320, 83475, 155,
     "[非淨減法輪] 逐檔清單＝CrossPlatform_R85_Guard_Repin_Evidence.md"),
    ("R86", 83475, 83470, -5,
     "[到期兌現] `_NET_SUBTRACTION_DUE_ROUND` 的到期輪，且是本表歷來第一個淨額 < 0 的輪次。"
     "動用的是棘輪 `[歷史變短]` 自己指定的出口（把史前列與史料搬出量測面）。逐項出口與行數、"
     "以及「量測面內的減法 ≠ 總量的減法」這條劃界，"
     "逐字見 CrossPlatform_R86_Guard_Repin_Evidence.md 與 CrossPlatform_R86_Scan_Findings.md §F-1。"
     ""),
    ("R87", 83470, 83610, 140,
     "[非淨減法輪] 逐檔清單與立案＝CrossPlatform_R87_Guard_Repin_Evidence.md"),
    ("R88", 83610, 83670, 60,
     "[非淨減法輪] 單人收斂輪（額度 halt ⇒ 零並行包，重釘由唯一窗口做一次）。"
     "成長面：test_check_hooks_liveness.py +51（DEF-200-104 的**第三個掃描面**＝SDD LATEST "
     "hook 樹的 console-spawn 判準＋反空轉＋SSOT 版號解析，該面此前一個觀測者都沒有，"
     "沒有等量舊判準可退場去換）／test_context_budget_guard.py +3（DEF-200-104 站點修復"
     "連帶的 patch 位址註解）。逐筆立案＝CrossPlatform_R88_Closure_Evidence.md"),
    ("R89", 83670, 83670, 0,
     "[淨額 0] 憲法裁決落地輪：新增 DEF-200-112 回歸鎖與 FALLBACK_KINDS 專屬鎖、R87 鎖改"
     "判準，並兌現款(12) 到期義務（追加更小的單輪上限，那一列自己也佔行）；成長全數以四段"
     "史料搬遷等量抵銷（原文逐字＝CrossPlatform_R89_Closure_Evidence.md），計數因此歸零。"),
    ("R89", 83670, 83578, -92,
     "[淨減法] R89 收尾單人窗口。動因是**分桶棘輪**（`prose` 桶）而不是總量棘輪——"
     "而立案查證推翻了「散文成長」這個假設：+157 全部來自 chunk 粒度的**重新歸類**"
     "（三塊在 HEAD 為 selfcontained，因搬遷體例留下的一行 `docs/` 指標而整塊改記入 prose，"
     "行數合計反而只 +6）。處置照棘輪自己列的第三條出口做，未動任何門檻、未重釘桶基準："
     "①把散落各鎖檔、屬「哪一輪發生過什麼／實測數字多少」的史料段逐字遷入 "
     "CrossPlatform_R89_Closure_Evidence.md，判準與判準的理由**一行都沒搬**——這是本列 "
     "-105 行的來源，逐段清單見該檔〈護欄層史料搬遷（R89 收尾窗口批）〉；"
     "②`test_quota_policy.py` 的完整路徑指標收斂成檔頭唯一一處（其餘三處改用同檔既有的"
     "短指稱），三塊因而回到 HEAD 時的歸屬。分桶讀數 4276→4009（相對 HEAD 基準 4119 為 "
     "-110），量測與逐筆歸因逐字見該檔〈分桶棘輪：+157 全部來自重新歸類〉。"),
    ("R90", 83578, 83739, 161,
     "[非淨減法輪] R90 收尾單人窗口（靜止樹、零並行包 ⇒ rc 可歸因）。成長面全數落在"
     "「R89 觀測欄（`is_active`／`severity`）接好卻沒有電」那組回歸鎖，逐檔清單＝"
     "CrossPlatform_R90_Guard_Repin_Evidence.md。三條合法出口**逐條實查**後才重釘："
     "①刪死碼＝0（新增的每一個 helper 都有實際消費者，實查零孤兒）；"
     "②搬史料**已由前段包用盡**（+253→+149，−41%）——殘餘散文 26 行中 8 行已是"
     "指向 `tools/lib/quota_meter.py`〈R89 觀測欄〉的指標、18 行是判準理由，"
     "而「判準與判準的理由」不在棘輪自列的出口內（R89 那一列同一句話）；"
     "③抽共用層（判準本體下沉 `tools/lib/quota_criteria.py`，該檔檔頭自訂的體例）"
     "只涵蓋約 11 行／7%，且要動 `tools/lib/` 另一個 LOC 預算面 ⇒ 收尾窗口刻意不做，"
     "列為交棒項。代價側現查：R90 上限 2000（`net_cap_for_round(90)`）、"
     "連升 streak 因 R89 的 -92 已歸零 ⇒ 本輪為第 1／2 輪，款(10)(11) 皆未觸發。"),
    ("R91", 83739, 84149, 410,
     "[非淨減法輪] R91 單人窗口（靜止樹、零並行包 ⇒ rc 可歸因）。成長面**全部一支檔**："
     "test_context_budget_guard.py——75% 提示的送達形態鎖（事件名回聲＋雙發言者必須併成"
     "單一 JSON）／warn 帶取樣與閂鎖拆成兩條誠實的名字／PRD 前置條件三條（額度已越 DRAIN "
     "線時不得勸壓縮）／PRD↔band 對映三條／單一 flush 站點三條／逃生口宣告一條。"
     "三條合法出口逐條實查後才重釘，逐項＝CrossPlatform_R91_Scan_Findings.md §C："
     "①刪死碼＝0（新增的三個 helper 都有實際消費者）；②**搬史料已用，但它落在量測面外**"
     "——本輪把 .claude/hooks/context_budget_guard.py 的六節模組史料搬進該檔 §A"
     "（raw 1072→1085，新增功能與判準只淨增 13 行而不是 +40），而棘輪只量 tools/tests/*.py "
     "⇒ 那筆減法抵銷不了本表淨額，照實記；③抽共用層抽的是 production 側"
     "（platform_utils.emit_to_model），判準本體留在測試面才是對的位置。"
     "代價側現查：本輪為款(12) 到期輪 ⇒ 單輪上限 2000→1600 並就地重新武裝下一段；"
     "連升 streak 第 2／2 ⇒ **R92 必須淨額 ≤ 0**。"),
    ("R92", 84149, 84142, -7,
     "[淨減法] R92 收尾窗口最終定案（覆寫草稿列）。SD 複審修復包（D3/D2/D4）貢獻"
     "test_context_budget_guard.py +85；六段純敘事 docstring（98 行）搬進"
     "CrossPlatform_R91_Scan_Findings.md §I-18~§I-23 抵銷，淨額 -7，streak 歸零。"
     "容量自適應攤提工作獨立拆入下方 R93。逐項立案見該檔 §I-24。"),
    ("R93", 84142, 84367, 225,
     "[非淨減法輪] 容量自適應攤提落地（DEF-200-122／DEF-200-114／ADR-XPLAT-009；帳本"
     "首列 DEF-200-139）。收尾窗口動工期間該工作線仍在延伸（account-key 追加），"
     "經三次靜止檢查定案：test_quota_policy.py +134、test_context_budget_guard.py "
     "account-key 部分 +78、本表自身編修 +12。streak 因 R92 淨額 -7 已歸零 ⇒ 本輪為"
     "第 1／2 輪。逐次量測與三條合法出口不適用之理由見"
     "CrossPlatform_R91_Scan_Findings.md §I-24／§I-25。"),
    ("R94", 84367, 84406, 39,
     "[非淨減法輪] D1（獨立 SD 複審阻塞項）：account_key 缺席退化路徑補 "
     "note_degraded() 觀測性＋命名回歸鎖（詳細支數見 §J-2），test_context_budget_guard.py +34、"
     "本表自身編修 +5。streak 因 R93 為第 1／2 輪，本輪為第 2／2 輪（R95 起若再正"
     "淨額需搬史料抵銷）。詳見 CrossPlatform_R91_Scan_Findings.md §J。"),
    ("R95", 84406, 84362, -44,
     "[淨減法] R95 收尾單人窗口。三並行包（Pkg-B 治理檔禁寫／Pkg-C 配速致動器／Pkg-D "
     "喚醒選路）合計 +454，全數以史料搬遷抵銷再淨減（R89 體例：判準與判準理由零搬動，"
     "七檔逐檔淨額、搬遷塊清單與逐塊原文＝CrossPlatform_R95_Guard_Repin_Evidence.md "
     "§A/§B/§D/§E 與三份 R95 證據檔）。連升 streak（R93/R94 第 2／2 輪）於本輪歸零；"
     "同輪兌現款(12)：上限表追加 (95, 1100)，並重武裝下一段（到期輪 97、目標 950）。"),
    ("R95", 84362, 84399, 37,
     "[非淨減法輪] R95 複審修復包批（M2 撕裂任務書第四分形／m5 病態環境值退回內建預設／"
     "M3 `.env` 同義繞行面／m4 `.autoclaude/` 前綴先釘）於首列 −44 凍結後才落地，當時未"
     "同步重釘＝複審唯一封鎖項。收尾窗口按 R89 體例搬史料：M2/m5 修前敘事→Resume 證據檔 "
     "§L-4.29／§L-4.30、M3 QA 實證→GovWrite 證據檔 §6.10（m4 括號句是判準理由不搬）；"
     "受 E501 顯示寬度棘輪約束實抵 2 行（m5 ±0），殘額 +29 全為判準與斷言本體照實記，"
     "本表自身編修 +8。逐檔清單＝CrossPlatform_R95_Guard_Repin_Evidence.md §F。R95 整輪"
     "合計 84406→84399（−7）仍為淨減；連升 streak 不進位（同輪多列合併後淨額 < 0）。"),
    ("R96", 84399, 84806, 407,
     "[非淨減法輪] R96 收尾單人窗口一次定案（覆寫草稿列，體例同 R92）。本輪重釘**分三批**："
     "①Windows 真機切換輪（mac→Windows，前 13 輪皆在 macOS）的八筆跨平台修復，已按 R89 "
     "體例先搬 22 行長 WHY 進證據檔；②**第一輪**四方複審（Architect／SA／SD／QA 全數 "
     "REJECT）後的包 A（只動 docs、不進量測面）與包 B；③**第二輪**四方複審（四方全數 "
     "APPROVE_WITH_CONDITIONS）後的包 C1（docs）與包 C2（程式／測試）。"
     "🔴 成長**全在新增的判準本體**、不是敘事：`pace_line` 公式邊界鎖、`_isolated_env` "
     "沙箱鎖、四支跨層對帳鎖（`--pace` 與守衛同刻說不同話）、`PermissionError` 那一臂、"
     "tempdir 判準改整棵樹快照、兩支平台中性 worktree 形態鎖。"
     "逐檔漂移、三批相加對帳、三條合法出口的逐條實查與代價側現查（cap 1100／streak 1of2／"
     "到期輪 R97 未到）＝CrossPlatform_R96_Scan_Findings.md §D；閘門重跑取證＝該輪 "
     "Closure_Evidence §8。"),
    ("R97", 84806, 85085, 279,
     "[非淨減法輪] R97 單人收尾窗口（2026-08-19，議題獨立於 R71~R96 跨平台複審系列——"
     "額度哨兵無人看管耗用 token）。Architect/SA/SD/QA 四方獨立審查修復缺陷並補回歸測試，"
     "成長全數落判準本體與 fixture，零散文。三條合法出口逐條實查：刪死碼＝0、搬史料不適用、"
     "抽共用層代價大於收益（drift_tolerance=0 使局部壓縮無法讓逐檔漂移歸零）。"
     "逐檔清單、必要性辯護與代價側現查（含款(12) 到期兌現：上限表追加 (97, 950)、"
     "重新武裝下一段到期輪 99 目標 850）＝CrossPlatform_R97_Scan_Findings.md。"
     "連升 streak：本輪為第 2／2 輪 ⇒ R98 起必須出現一次淨額 ≤ 0。"),
    ("R97", 85085, 85394, 309,
     "[非淨減法輪][同輪追加] R97 收尾窗口後續四方複審修復（commit 9ef67f8）：P0-1 資安修復"
     "把 worktree 路徑處理抽成共用模組 `tools/lib/worktree_paths.py`（回歸測試 "
     "`test_worktree_paths.py` +103）；P2-1/P2-2 新增失敗紀錄輪替方向鎖與其測試 "
     "`test_failure_log_rotation.py`（+81）；帳本判準過期缺陷回歸測試 "
     "`test_skip_ceiling_ratchet_direction.py`（+107）；既有 "
     "`test_block_destructive_git_r83.py` 補 worktree \"..\" 穿越洞回歸測試 +18。"
     "三項成長全落判準本體與 fixture，零散文膨脹。合法出口逐條實查：刪死碼不適用（皆為"
     "新缺陷的必要回歸覆蓋）、抽共用層已是本輪動作本身（worktree_paths.py 即抽出結果）。"
     "逐檔清單、必要性辯護同前列＝CrossPlatform_R97_Scan_Findings.md。"
     "本列與前一列同屬 R97（收尾當輪連續追加、依 `repin_round_nets()` 同輪合併語意"
     "計為同一輪淨額 279+309=588，未產生第三個連續上升輪，streak 仍為 2／2）。"),
    ("R97", 85394, 85418, 24,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：前一列落地後 `--print-guard-lines` "
     "覆核發現本檔與另外三支被本輪動到的鎖檔（`test_platform_neutral_paths.py`／"
     "`test_subprocess_encoding_hygiene.py`／`test_worktree_paths.py`）逐檔漂移——"
     "護欄層守自己（本表、腐化上界重釘註解、platform-ok 豁免行）的成長，同 R95/R96 體例"
     "的「本表自身編修」。合法出口逐條實查：刪死碼不適用（皆為本輪修復留下的必要註記）、"
     "抽共用層不適用（純數字與註解，無可抽結構）。逐檔清單同前列＝"
     "CrossPlatform_R97_Scan_Findings.md。與前兩列同屬 R97，三列合計淨額 "
     "279+309+24=612，streak 仍為兩輪（R96／R97），未產生第三個連續上升輪。"),
    ("R97", 85418, 85429, 11,
     "[非淨減法輪][同輪追加] 護欄層自身編修（見前列 CrossPlatform_R97_Scan_Findings.md）。"),
    ("R97", 85429, 85695, 266,
     "[非淨減法輪][同輪追加] PRD §4.5.7／§4.5.8 落地：`test_context_budget_guard.py` 新增"
     "三支測試類別（B1/B2/B3 分支開關紅綠自證 ＋ armed stamp 漂移自癒的漂移／未漂移／"
     "量不到三組控制對照），並含本表自身編修（重釘理由＋更新 `_FROZEN_GUARD_LINES`／"
     "`_REPIN_LOG_FROZEN_PREFIX_LEN`／sha 常數）的連帶漂移，同 R95/R96/R97 既有體例。"
     "合法出口逐條實查：刪死碼不適用（皆為新功能的必要回歸覆蓋）；抽共用層不適用"
     "（生產碼側已先抽——`tools/session_resume_planner.py` guardrail_cli 750/750 零餘裕，"
     "淨額為 0，新邏輯全落有餘裕的 `tools/lib/quota_escalation.py`）。"
     "逐檔清單見 CrossPlatform_R97_Scan_Findings.md。"),
    ("R97", 85695, 85813, 118,
     "[非淨減法輪][同輪追加] 四方最終複審收斂修復：①DEF-200-160 二審——QA 親測揪出方向鎖"
     "假鎖（`_FROZEN_CEILING_MAX` 原用 `copy.deepcopy(即時匯入值)`，套套邏輯零鑑別力），"
     "改為原始碼字面凍結（比照 `skip_tag_policy._POSIX_TAG_RATCHET_CEILING` 既有做法），"
     "`test_skip_ceiling_ratchet_direction.py` +58；②DEF-200-163 補測試覆蓋——"
     "`tools/lib/ledger_staleness.py::uncommitted_problems()` 落地時零測試，"
     "`test_check_defect_log_crossref.py` 新增 `TestLedgerStalenessUncommittedProblems`"
     "（乾淨／未 commit／git 不可用三分支）+61；③`test_failure_log_rotation.py` 移除未用"
     "`import time` −1。合法出口逐條實查：刪死碼不適用（皆為新缺陷必要回歸覆蓋）、"
     "搬史料不適用（判準與回歸鎖同次落地）、抽共用層不適用（drift_tolerance=0）。"
     "紅綠雙向驗證（把真實常數 41→999 重跑方向鎖轉紅、改回後轉綠）與逐檔清單見"
     "CrossPlatform_R97_Scan_Findings.md「同輪追加④」。"),
    ("R97", 85813, 85829, 16,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：前一列落地後 `--print-guard-lines` 覆核"
     "發現本檔自己（新增的稽核列本身）逐檔漂移 +16，同 R95/R96/R97 既有體例。"
     "逐檔清單見 CrossPlatform_R97_Scan_Findings.md「同輪追加④」。"),
    ("R97", 85829, 85672, -157,
     "[同輪追加] 護欄層散文搬遷抵銷（收尾單人窗口）：追加④之後本輪累積 +1023 超過同輪"
     "到期上限 950。本檔（test_adr_xplat001_c1c2_lock.py）自 R77~R85 累積的純敘事性 WHY "
     "註解／docstring（設計取捨、立案沿革、歷史訂正說明）全文搬進 "
     "CrossPlatform_R97_Scan_Findings.md「同輪追加⑤」節，原處各留一行指標，測試覆蓋與"
     "判準行為零影響。逐段清單、搬遷前後行數與三條合法出口逐條實查見該節。本輪累計 "
     "279+309+24+11+266+118+16-157=866，低於到期上限 950。"),
    ("R97", 85672, 85679, 7,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：前一列落地後 `--print-guard-lines` 覆核"
     "發現本檔自己（新增的稽核列＋prefix_len 更新本身）逐檔漂移 +7，同 R95/R96/R97 既有"
     "體例。逐檔清單見 CrossPlatform_R97_Scan_Findings.md「同輪追加⑤」。"),
    ("R97", 85679, 85687, 8,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：前一列落地後 `--print-guard-lines` 覆核"
     "再次發現本檔自己逐檔漂移 +8（收斂尾段：新增稽核列＋prefix_len／digest 更新自身佔行），"
     "同 R95/R96/R97 既有體例。逐檔清單見 CrossPlatform_R97_Scan_Findings.md「同輪追加⑤」。"),
    ("R98", 85687, 85687, 0,
     "R98：tools/lib 拆分子模組觸發重釘 30→41；同輪壓縮舊史料換取淨額。逐檔清單見 "
     "CrossPlatform_R98_Scan_Findings.md。"),
    ("R98", 85687, 85238, -449,
     "R98 第二次收斂：DEF-101-941 BSD regex 修復再度讓 test_bash32_compat.py +23 行、"
     "第四次撞上護欄層行數棘輪。改採結構性減法：test_platform_neutral_paths.py 內"
     "20 段逐輪判準歷史敘事原文搬至 docs/06_quality/CrossPlatform_Guard_Line_History.md"
     "（僅留判準邏輯＋指標），淨額 -472。兩者相抵，總淨額為負，非壓線打平。"
     "逐檔清單見 CrossPlatform_R98_Scan_Findings.md「第二次收斂」節。"),
    ("R98", 85238, 85248, 10,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：本檔新增本列＋上一列稽核列＋"
     "prefix_len/digest 更新，本檔自身逐檔漂移 +10（5353→5363），同 R95/R96/R97 既有"
     "體例。逐檔清單見 CrossPlatform_R98_Scan_Findings.md「第二次收斂·同輪追加」。"),
    ("R99", 85248, 85915, 667,
     "[非淨減法輪] 多包並行波留下的既有成長，由收尾單人窗口在全部包停工後一次重釘："
     "test_check_defect_log_crossref.py +237（淨額棘輪／外部阻塞軌／收輪接線三個新測試類別）、"
     "test_archive_defect_log.py +162（`--repin-oversize` 帳本超標三常數自動重釘回歸鎖）、"
     "新檔 test_guard_line_taxonomy_r99.py +148（`tools/lib/guard_line_taxonomy.py` 觀察模式"
     "回歸鎖，ADR-XPLAT-012 落地）、test_quota_policy.py +106（額度門檻新判準回歸鎖）、"
     "test_ps_engine_ssot.py +21。逐項立案見 docs/06_quality/CrossPlatform_R99_Ledger_Closure.md。"
     "🔴 本檔自身淨 −8（收尾者刪除已閉合的 `DEF-101-324` 基線豁免登記，見 "
     "`_BASELINE_WAIVERS` 與 ADR-XPLAT-001 §7 同步訂正）。"),
    ("R99", 85915, 85932, 17,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：本檔新增上一列＋本稽核列＋"
     "`_REPIN_NET_CAP_SCHEDULE` 到期義務兌現列 `(99, 850)`，本檔自身逐檔漂移 +17"
     "（5356→5373），同 R95～R98 既有體例。逐項立案見 "
     "docs/06_quality/CrossPlatform_R99_Ledger_Closure.md「同輪追加」。"),
    ("R99", 85932, 86090, 158,
     "[非淨減法輪][同輪追加] 收斂波四方複審對抗包一次修完：test_check_defect_log_"
     "crossref.py +51（R-01 具名阻塞源正則改 fullmatch 防繞過／R-02 淨額棘輪 "
     "fail-open 補 stderr 警告／R-09 CI 無參數 main() 併印外部阻塞軌筆數，各附回歸"
     "測試）；本檔自身 +107（R-10：新增 `frozen_prefix_rewrite_problems()` 機制——"
     "凍結前綴指紋改由跨檔 DEF-ID 錨點把關協同改寫，附回歸測試與本列自身編修，"
     "同步重釘 `_REPIN_LOG_FROZEN_PREFIX_LEN`／`_REPIN_LOG_HISTORY_SHA256`）。"
     "逐項立案見 CrossPlatform_R99_Ledger_Closure.md「收斂波」節。"),
    ("R99", 86090, 86097, 7,
     "[非淨減法輪] 收尾併帳（詳見 CrossPlatform_R99_Scan_Findings.md「收尾」節）："
     "freshness 檔依出口③刪 18 行搬遷散文，淨額 +3；本檔自身逐檔漂移 +4；合計 +7。"),
    ("R100", 86097, 86438, 341,
     "[非淨減法輪] ADR-XPLAT-013 計價規則改為 assertion-only（Phase 2 方向 (a)）："
     "本檔新增兩組載體——計價規則變更輪的零緩衝豁免（`pricing_exemption_problems()`）與"
     "觀察模式 5 輪時效的到期判準（`phase2_review_problems()`），兩者皆含方向鎖與紅綠"
     "注入自證；`test_block_destructive_git_r83.py` 的 tier 鎖語意訂正 +9。"
     "合法出口逐條實查：刪死碼不適用（兩組皆為此前不存在的判準面，沒有等量舊判準可退場）、"
     "抽共用層已做（兩者共用的輪次時鐘抽成具名函式 `live_repin_round()`，避免第二份手抄本）。"
     "逐檔清單與立案實測見 CrossPlatform_R100_Scan_Findings.md。"),
    ("R100", 86438, 86452, 14,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：前一列落地後 `--print-guard-lines` 覆核"
     "發現本檔自己逐檔漂移——來源是兩個重釘數字、新增的稽核列本身、以及 prefix_len／digest"
     "的更新所佔的行，同 R95~R98 既有體例（合法出口逐條實查：無死碼可刪、純數字與註解"
     "無可抽結構）。逐檔清單見 CrossPlatform_R100_Scan_Findings.md。"),
    ("R101", 86452, 87784, 1332,
     "[非淨減法輪] R101四方複審核准DEF-200-208一次性例外：一次性收斂既有鎖檔跨多輪陳舊"
     "逐檔漂移（ADR-XPLAT-013 落地後首次被 `--print-guard-lines` 覆核揪出，此前歷輪"
     "重釘皆未處理，+1092），加上本檔自身修復 `pricing_exemption_problems()` "
     "provenance 缺陷 ＋ 新增 `_REPIN_APPROVED_ROUND_OVERAGE` 一次性例外機制（含其"
     "回歸測試）的編修（+233）。真實淨額遠超單輪上限與連續上升上限，四方複審核准本輪"
     "不計入款(10)(11)，同輪一併兌現 `_REPIN_NET_CAP_DUE_ROUND` 到期義務。"
     "合法出口逐條實查：刪死碼不適用、抽共用層不適用（詳見理由）。"
     "逐檔清單與必要性辯護見 CrossPlatform_R101_Scan_Findings.md。"),
    ("R102", 87784, 88356, 572,
     "[非淨減法輪] DEF-200-204 新增 PRD §4.2.4 動態配速平穩性機制的合法功能成長（四方"
     "終審 4/4 APPROVE_WITH_FIXES）：`test_quota_policy.py` +561（可得性軸遲滯／死區·"
     "變化率限制·最小停留時間／啟動自檢的回歸測試，2432→2993）、"
     "`test_context_budget_guard.py` +11（同批持久狀態隔離治具）。淨額 572 < 該輪上限"
     " 750（`net_cap_for_round(102)`），且緊接 R101 的一次性核准例外之後——"
     "`repin_growth_problems()` 的連續上升計數在核准輪重置為零，本輪視為 streak 第 1 "
     "輪，未撞款(11)。無需 `_REPIN_APPROVED_ROUND_OVERAGE` 例外。逐檔清單見 "
     "CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88356, 88372, 16,
     "[非淨減法輪] 本檔自身逐檔漂移——來源是上一列新增的稽核列本身，同 R95~R98 既有"
     "體例（合法出口逐條實查：無死碼可刪、純數字與註解無可抽結構）。逐檔清單見 "
     "CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88372, 88387, 15,
     "[非淨減法輪][R102 收尾] 修復 push 被擋下的既存缺陷（DEF-200-218）：`test_check_"
     "pytest_baseline_sites.py` 的 `_SCAN_FILES` 漏納管 R100 新增、含與 `quota_meter.py` "
     "同型的『誤配 pytest 摘要字面』反例引文的回歸測試 "
     "`test_r100_quota_refusal_false_positive.py`，"
     "未納管站點棘輪因此由 114 上升為 115（該檔 299→301，+2）。其餘 +13 為本檔自身逐檔"
     "漂移——`--print-guard-lines` 反覆覆核收斂：重釘數字、新增稽核列與 `_FROZEN_PREFIX_"
     "REWRITE_LEDGER` 追加列本身、以及 prefix_len／digest 更新所佔的行，同 R95~R101 既有"
     "體例。合法出口逐條實查：無死碼可刪、抽共用層不適用（純新增一筆納管清單條目、其 WHY "
     "註解，及本身重釘）。逐檔清單見 CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88387, 88400, 13,
     "[非淨減法輪] test_the_next_round_cannot_reuse_the_exemption 訂正：R102 收尾四方核准"
     "並執行 --repin-cap／--update 後，provenance 合法轉為已重釘，該測試原借磁碟真實狀態"
     "當『未重釘』反面測資的前提不復存在，改用合成注入訂正，不動 _PRICING_CHANGE_EXEMPT_"
     "ROUND、不改判準本體。合法出口逐條實查：無死碼可刪、抽共用層不適用（純測試資料來源"
     "訂正＋docstring 因果說明，含本檔自身逐檔漂移收斂列）。逐檔清單見 "
     "CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88400, 88389, -11,
     "[淨減法輪] 收斂列：把上一輪重釘過程中先前散落的多筆逐檔漂移收斂列合併為一筆，"
     "淨減 11 行。逐檔清單見 CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88389, 88403, 14,
     "[非淨減法輪] 收斂列，本檔自身逐檔漂移。逐檔清單見 CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88403, 88405, 2,
     "[非淨減法輪] 收斂列。逐檔清單見 CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88405, 88407, 2,
     "[非淨減法輪] 收斂列。逐檔清單見 CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88407, 88415, 8,
     "[非淨減法輪] 收斂列。逐檔清單見 CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88415, 88425, 10,
     "[非淨減法輪][同輪追加] DEF-200-219：R71 全樹掃描抓到 `6fea8a3` 新增的多處 R102 "
     "註解漏帶 `round-label-ok`；補標後一行顯示寬度超線觸發 `test_e501_debt_only_shrinks`，"
     "拆行修復＋本表與重釘史料自身編修合計本檔逐檔漂移。逐項見 "
     "CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88425, 88429, 4,
     "[非淨減法輪] 帳本收斂輪（archive_67）：`OVERSIZE_ROW_CEILING` 封印延伸至 62 後"
     "尾端相鄰（63,62）使兩支既有測試（`TestR82SealedHistoryPrefix._relaxed`／"
     "`TestR82ComplexReviewSealTableIntegrity."
     "test_rewriting_a_seal_in_place_is_red_even_though_the_length_is_unchanged`）"
     "整數中點注入退化為 no-op，修復為相鄰時取 `_SEAL[-2]`，本檔 3615→3619（+4）。"
     "合法出口逐條實查：無死碼可刪、抽共用層不適用。逐檔清單見 "
     "CrossPlatform_R102_Scan_Findings.md。"),
    ("R102", 88429, 88445, 16,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：上一列新增本身＋本稽核列，"
     "本檔自身逐檔漂移，同 R95~R102 既有體例。逐檔清單見 "
     "CrossPlatform_R102_Scan_Findings.md。"),
    ("R103", 88445, 88548, 103,
     "[非淨減法輪] DEF-200-221（四方複審發現）：ArchiveGate 包在 "
     "test_check_defect_log_crossref.py 新增 TestArchiveRequiredProblems 整個測試類別"
     "（3619→3722，+103），未回頭同步本表——LedgerClose 包稍早只為自己那筆 +4 行重釘，"
     "兩包並行動同一支鎖檔卻只有一包重釘（同 CLAUDE.md 鐵律七）。R102 已收尾交棒"
     "（R102_HANDOFF.md），本批是四方複審在 R103 窗口對其收尾整合缺口的訂正，故用新"
     "輪號、不追溯改寫 R102 的稽核列。收尾單人窗口一次性訂正。逐項見 "
     "CrossPlatform_R102_Scan_Findings.md。"),
    ("R103", 88548, 88574, 26,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：上一列新增本身＋本稽核列＋到期義務"
     "重新武裝（_REPIN_NET_CAP_SCHEDULE 追加一列＋重新武裝下一段），"
     "本檔自身逐檔漂移，同 R95~R102 既有體例。逐檔清單見 "
     "CrossPlatform_R102_Scan_Findings.md。"),
    ("R104", 88574, 88556, -18,
     "[淨減法] PRD §4.2.5／§4.2.1 BURSTING/EWMA（只算不接線）：test_quota_policy.py "
     "+62（bursting_ok()/ewma_burn_rate() 回歸測試，2993→3055）；_platform_helpers.py "
     "三段 forensic 沿革（usable_bash_for_fixture／PS_UTF8_PRELUDE／_PS_COMMENT_LEAD）"
     "搬遷至 CrossPlatform_R104_Scan_Findings.md，537→446；本檔自身新增兩列（本列＋"
     "DEF-200-223 凍結前綴延伸列）+11。三者相抵：62-91+11=-18，streak 因淨額 ≤0 歸零。"
     "逐檔清單見 CrossPlatform_R104_Scan_Findings.md。"),
    ("R105", 88556, 88556, 0,
     "[淨零] 四檔新增 DEF-200-158/012/196/015/173 回歸測試 +34（block_destructive_git_r83"
     " +8／context_budget_guard +16／defect_id_reference_integrity +1／"
     "mac_endurance_r83 +9）；strip_ps_comments 已知不涵蓋沿革搬遷至 "
     "CrossPlatform_R105_Scan_Findings.md，446→403（-43）；本檔自身新增本列＋"
     "DEF-200-224 到期義務兌現 +9，三者相抵：34-43+9=0。"),
    ("R105", 88556, 88605, 49,
     "[非淨減法輪][同輪追加] 四方複審 REJECT 修復（DEF-200-202）：quota_gate.py 補齊 "
     "active_model 接線＋新增回歸測試，逐項見 CrossPlatform_R105_FourParty_Fix.md。"),
    ("R105", 88605, 88617, 12,
     "[非淨減法輪][同輪追加] 護欄層重釘自身編修：上一列新增本身＋本稽核列＋凍結前綴"
     "延伸（`_REPIN_LOG_FROZEN_PREFIX_LEN` 63→65，一次涵蓋上一列與本列）＋"
     "`_FROZEN_PREFIX_REWRITE_LEDGER` 追加一列，本檔自身逐檔漂移，同 R95~R105 既有"
     "體例。逐項見 CrossPlatform_R105_FourParty_Fix.md。"),
    ("R105", 88617, 88645, 28,
     "[非淨減法輪][同輪追加] 四方複審修復續：`_platform_helpers.py` 的 `strip_ps_comments`"
     " docstring 折長行（403→407，+4）＋`test_defect_id_reference_integrity.py`"
     " DEF-200-015 姊妹帳本（`AutoSDD_External_Blocked_Log.md`）擴面（262→274，+12）＋"
     "本檔自身編修 +12。逐項見 CrossPlatform_R105_FourParty_Fix.md。"),
    ("R105", 88645, 88656, 11,
     "[非淨減法輪][同輪追加] 帳本狀態欄回填 fixed@R105 觸發 test_platform_neutral_paths.py"
     " 的 _DIRENT_UNGUARDED_DEBT（41→42，新增回歸測試多用一次既有 .replace() 慣用句式）＋"
     "本檔自身編修 +8。逐項見 CrossPlatform_R105_FourParty_Fix.md。"),
    ("R106", 88656, 88674, 18,
     "[非淨減法輪] windows-compat-ci／root-infra-ci 兩筆真缺陷修復（R105 交接留給 Windows"
     "11 輪的兩個獨立問題）：test_check_hooks_liveness.py +6（Stop guard 的 native／alien"
     "分類測試補平台感知——真子行程無 on_windows 注入接縫，原版寫死 POSIX 方向在"
     "windows-compat-ci 真機上必然反過來）；test_run_root_unittests.py +3"
     "（_WINDOWS_SKIP_TAG_EXEMPT 補上具名豁免後首次非空，兩處合成樹測試需隔離活體"
     "全域表避免被污染而假紅）；本檔自身 +9（本稽核列本身）。合法出口逐條實查：無死碼"
     "可刪、抽共用層不適用（皆為既有測試方法內針對真實平台差異的修正，無等量舊邏輯可"
     "退場）。逐項見 CrossPlatform_R106_Scan_Findings.md。"),
    ("R106", 88674, 88679, 5,
     "[非淨減法輪][同輪追加] 本檔自身逐檔漂移——來源是 _FROZEN_PREFIX_REWRITE_LEDGER"
     "追加列（DEF-101-561）與本稽核列本身。逐項見 CrossPlatform_R106_Scan_Findings.md。"),
    ("R106", 88679, 88685, 6,
     "[非淨減法輪][同輪追加] 本檔自身逐檔漂移——來源是 _PHASE2_REVIEW_LOG 追加列"
     "（重新武裝下一個 5 輪視窗）與本稽核列本身。逐項見 CrossPlatform_R106_Scan_Findings.md。"),
    ("R106", 88685, 88698, 13,
     "[非淨減法輪][同輪追加] windows-compat-ci 真缺陷二次驗證抓到漏網之魚："
     "test_run_root_unittests.py +8（三處合成樹測試補隔離活體 _WINDOWS_SKIP_TAG_EXEMPT"
     "表，避免非 Windows 平台被污染而假紅）；本檔自身 +5（本稽核列本身）。逐項見"
     "CrossPlatform_R106_Scan_Findings.md。"),
    ("R106", 88698, 88817, 119,
     "[非淨減法輪] DEF-101-752 收斂：多支 tools/tests/ 掃描面站點由 tracked-only 改為"
     "tracked ∪ untracked-not-ignored（`git ls-files` ∪ `git ls-files -o "
     "--exclude-standard`），逐處補 WHY 註解與雙次列舉迴圈；另含本檔自身逐檔漂移（新增"
     "稽核列＋凍結表數字更新＋凍結前綴延伸所需的 _FROZEN_PREFIX_REWRITE_LEDGER 追加列，"
     "含收斂重釘過程本身的多輪迭代）。合法出口逐條實查：刪死碼不適用（新增的是此前不"
     "存在的 untracked 覆蓋，無等量舊邏輯可退場）、抽共用層不適用（同 repo 既有慣例，"
     "R70 起的先例皆各自就地實作、未抽共用層）。逐項見 CrossPlatform_R106_Scan_Findings.md。"),
    ("R106", 88817, 89104, 287,
     "[非淨減法輪][同輪追加] 帳本結案輪修復包補 DEF-101-752 問題 3 的殘餘：四方複審點名"
     "的 8 站點（test_windowsapps_guard_cross_consistency.py／test_ps1_bom.py／"
     "test_bash32_compat.py／test_ps51_compat.py／test_windows_forbidden_filename_"
     "parity.py／test_find_git_bash_parity.py／test_workflow_permission_concurrency_"
     "lock.py／test_windowsapps_guard_bash_parity.py）各自補一個永久回歸測試類別（驗證"
     "untracked 探針真的被掃描面看見），落地時未重釘本表 ⇒ 淨額 +287 一度不出現在任何"
     "地方（ARCH-01 同型復發）。合法出口逐條實查：刪死碼不適用（新增的是此前不存在的"
     "永久回歸鎖，無等量舊邏輯可退場）、抽共用層不適用（逐站各自守自己站點的既有 union"
     "掃描面，測試形狀各異無法合併）。逐項見 CrossPlatform_R106_Scan_Findings.md。"),
    ("R106", 89104, 89114, 10,
     "[非淨減法輪][同輪追加] 本檔自身逐檔漂移——來源是上一列新增稽核列本身的行數。"
     "逐項見 CrossPlatform_R106_Scan_Findings.md。"),
    ("R106", 89114, 89125, 11,
     "[非淨減法輪][同輪追加] 本檔自身逐檔漂移——來源是前兩列新增稽核列＋"
     "_FROZEN_PREFIX_REWRITE_LEDGER 追加列（DEF-101-752）。"
     "逐項見 CrossPlatform_R106_Scan_Findings.md。"),
    ("R107", 89125, 89124, -1, "帳本結案包 #3 四筆判準落地（DEF-200-166／171／225、"
     "DEF-101-950），同輪兌現 (107, 630) 到期義務並重新武裝 (109, 610)。淨額 ≤ 0 的抵銷＝"
     "八段散文搬遷 CrossPlatform_Guard_Line_History.md〈站點級守衛四種罩法 WHY〉至〈SC-2/3/5 "
     "射程收窄 WHY〉八節（原文全文保全、知識零刪除；僅指稱詞隨載體必要調整）；逐檔對照見 "
     "CrossPlatform_R106_Scan_Findings.md 的 R107 標記行。"),
    ("R108", 89124, 89218, 94,
     "[非淨減法輪] DEF-200-230 回歸鎖落地（PRD §15.5 紅線 1 條件 (b) 的機械面）："
     "test_quota_policy.py 新增「額度取數端點字面只准住一個家」判準——純函式 "
     "usage_url_homes()＋整棵樹 tracked *.py 掃描面現查＋合成注入紅綠自證（第二個家出現"
     "即紅、判準寬到誤收 /v1/messages 亦紅），3071→3152（+81）；本檔自身 +13＝本稽核列＋"
     "_FROZEN_PREFIX_REWRITE_LEDGER 追加列＋凍結前綴延伸（_REPIN_LOG_FROZEN_PREFIX_LEN "
     "76→77，涵蓋本列本身）。合法出口逐條實查：無死碼可刪；抽共用層不適用（判準只有一個"
     "消費端，抽層只會多一個沒人維護的家）；散文搬遷不適用（新增全是判準本體與注入語料，"
     "本輪未新增可搬的史料散文）。逐檔清單見 CrossPlatform_R108_Review.md"
     "〈護欄層重釘逐檔清單〉節。"),
    ("R108", 89218, 89314, 96,
     "[非淨減法輪][同輪追加] DEF-200-233 修復（macos-compat-ci 連續紅的真因）："
     "`exemption_problems()` 的 stale 面把「豁免指向的測試在本平台**沒 skip**（它跑了）」"
     "讀成「豁免過期」，於是 darwin 把整批仍在 linux 承重的豁免全判 stale ＝假紅。"
     "test_run_root_unittests.py 2201→2283（+82）＝一支 R108 方向鎖（測試跑掉≠豁免過期）"
     "＋一支消失面補位鎖＋一支消失面關閉對照＋一支 known_ids 接線鎖，另兩處既有注入改指向"
     "「本次真的 skip 掉」的 id（否則新判準正確地回空、接線鎖退化成恆綠）；本檔自身 +14＝"
     "本稽核列＋_FROZEN_PREFIX_REWRITE_LEDGER 追加列＋凍結前綴延伸（77→78 涵蓋本列）。"
     "合法出口逐條實查：無死碼可刪；抽共用層不適用（判準只有 report_windows_skip_tag_"
     "exemption_problems 一個消費端）；散文搬遷不適用（新增全是判準本體與注入語料）。"
     "逐檔清單見 CrossPlatform_R108_Review.md〈護欄層重釘逐檔清單〉節。"),
    ("R109", 89314, 89430, 116,
     "[非淨減法輪] Gap C 單一窗口：ONBOARDING §7 表② 指紋檢查接進 dev_start [6/7]"
     "（邏輯本體住 tools/lib/onboarding_snapshot_note.py；dev_start.py raw-line 持平——"
     "新增行以史料搬遷 CrossPlatform_Guard_Line_History.md〈dev_start 史料搬遷〉節抵銷）："
     "test_dev_start.py 新增 TestOnboardingSnapshotProbe（rc 三態、逾時降級、整合、佈線"
     "存在鎖）＋既有 step_platform 測試補 mock 隔離真 subprocess；"
     "test_platform_neutral_paths.py 重釘 tools/lib 掃描面下限帶（新 lib 檔落地越過腐化"
     "上界，重釘值＝下限帶訊息逐字要求）；本檔自身＝本稽核列＋rewrite ledger 追加列＋"
     "(109, 610) 到期義務兌現與重新武裝＋凍結前綴延伸。合法出口逐條實查：無死碼可刪；"
     "抽共用層不適用（哨兵只有 step_platform 一個消費端）；散文搬遷已做在 dev_start.py "
     "側。逐檔行數對照見 CrossPlatform_R106_Scan_Findings.md 的 R109 標記行。"),
    ("R109", 89430, 89467, 37,
     "[非淨減法輪][同輪追加] F2 三次量測矛盾診斷修復（根因＝測試不 hermetic，活體態滲入）："
     "test_context_budget_guard.py 8157→8178（+21）＝兩處活體隔離夾具："
     "①QuotaDegradationIsAudibleTest.setUp 補 swap endurance_env.trace_dir／trace_dir_status"
     "（availability／stability 兩台狀態機的持久檔住帳號級 trace_dir，qg 六個 swap 蓋不到；"
     "真 hook 釘下的 stability cap=0 滲入 ⇒ unmeasured 封鎖放寬 ⇒ live(1)>cap(0) ⇒ rc=2，"
     "同一棵樹紅綠隨活體檔內容翻動）；②QuotaEnvFileIsActuallyLoadedTest.setUp 補 ENV_SPEC "
     "鍵刷除（同檔既有判例同型）：planner.main() 的 apply_env_defaults(os.environ) 把真 "
     ".env 鍵永久灌進行程 ⇒ pytest 定義序紅／unittest 字母序綠。不改守衛行為、不改測試錨。"
     "本檔自身 +16＝本稽核列＋rewrite ledger 追加列＋凍結前綴延伸（79→80）。合法出口"
     "逐條實查：無死碼可刪；抽共用層不適用（兩處隔離夾具各只有一個消費類）；散文搬遷"
     "不適用（新增全是隔離夾具本體與 WHY）。逐檔行數對照見 "
     "CrossPlatform_R106_Scan_Findings.md 的 R109 標記行。"),
    ("R111", 89467, 89452, -15,
     "R111 護欄層判準修補輪（單人窗口；DEF-200-116/121/129/195/209/212/213④）。淨額為負："
     "16 塊史料搬遷 CrossPlatform_Guard_Line_History.md（〈R67-C19 覆蓋差集登記表 WHY〉起"
     "16 節）抵掉全部新增判準，連續上升計數（R108 +190、R109 +153）歸零。新增面：116 "
     "headroom 值域紅綠＋213④ 薄調用（test_quota_policy.py 3152→3198）；129/195 "
     "_receipt_rounds() 取數面＋2×2（test_check_defect_log_crossref.py 3722→3794；129 "
     "自列出口暫未接線＝cur 滯後窗口的轉紅名單逐字在案，載體 DEF-200-129 回執）；209 "
     "同步鎖兩支（test_subprocess_encoding_hygiene.py 1599 持平＝同檔搬遷抵銷）；121 "
     "lookahead 後設鎖＋紅綠＋兌現 (111, 595) 並重新武裝 113／585（步伐 10<15）。"
     "本檔自身＝搬遷 −21 ＋ 121 面 +57 ＋ 本稽核列、rewrite ledger 追加與凍結前綴延伸"
     "（80→81）。逐檔清單見 CrossPlatform_R106_Scan_Findings.md 的 R111 標記行。"),
    ("R113", 89452, 89592, 140,
     "[非淨減法輪] R113 結構性長債分軌輪（收尾單人窗口；掌舵者 2026-08-30 核准，存證＝"
     "AutoSDD_TechDebt_Paydown_Playbook.md §6 第 3 條）。新增面：TestStructuralDebtLog "
     "九支（scoped source_re 紅綠／兩軌枚舉互斥／交叉鎖／成長棘輪／真檔 well-formed／"
     "print 可見性）＋外部軌真檔測試拆 date.today() 日期引信＋三支既有 print 測試擴斷言"
     "（test_check_defect_log_crossref.py 3794→3906）；姊妹帳本擴面 _SISTER_LEDGER_RELS"
     "（test_defect_id_reference_integrity.py 274→281）；本檔自身＝本稽核列＋兌現 "
     "(113, 585) 並重新武裝 115／577（步伐 8<10）。淨額為正＝streak 第 1 輪（前一輪 "
     "-15 已歸零），未逾每輪上限。逐檔清單見 CrossPlatform_R106_Scan_Findings.md 的 "
     "R113 標記行。"),
    ("R113", 89592, 89733, 141,
     "[非淨減法輪][同輪追加] v2.1.13 G1 V-a 測試落地（喚醒鏈最後一哩實作批 (a)；施工圖＝"
     "PRD_Amendment_R113_WakeChain_LastMile.md §3(a)／§4）：test_context_budget_guard.py "
     "8178→8307（+129）＝UnattendedPermissionPostureTest 六格（V-a1 兩路 argv 權限姿態、"
     "V-a2 A-PRE 缺席／壞檔拒 spawn＋通過面 mkdir handback、V-a4 allow＝L2×雙載具雙向對齊、"
     "V-a3 靜態半格 deny 三檔×三寫入形態；V-a1／V-a2 皆突變驗紅後還原）＋resume_route lib "
     "import。本檔自身 +12＝本稽核列＋rewrite ledger 追加列＋凍結前綴延伸（82→83）。合法"
     "出口逐條實查：無死碼可刪；抽共用層不適用（判準只有 resume_route 一個消費端）；散文"
     "搬遷不適用（新增全是判準本體）。逐檔清單見 CrossPlatform_R106_Scan_Findings.md 的 R113 標記行。"),
    ("R113", 89733, 89910, 177,
     "[非淨減法輪][同輪追加] v2.1.13 G2 handback 落地（喚醒鏈最後一哩實作批 (b)；施工圖＝"
     "PRD_Amendment_R113_WakeChain_LastMile.md §3(b)／§4 V-b1~V-b3）："
     "test_context_budget_guard.py 8307→8468（+161）＝HandbackVisibilityTest 三格"
     "（V-b1 合規交接四 marker＋resumed 記欄、V-b2 沒寫交接逐字 handback_missing＋alert "
     "憑證欄〔突變驗紅後以 Edit 還原〕、stale 半格舊檔不得冒充）＋"
     "HandbackSessionStartAnnounceTest 三格（V-b3 未讀出聲含「下一步指令」節＋.ack 轉安靜、"
     "emit 拒收不落 .ack、guard.main() SessionStart 接線實跑）＋_isolated_env 補 "
     "AUTOSDD_HANDBACK_DIR 隔離。本檔自身 +16＝本稽核列＋rewrite ledger 追加列＋"
     "凍結前綴延伸（83→84）。合法出口逐條實查：無死碼可刪；抽共用層已做（判準本體住 "
     "resume_route／endurance_env／sentinel_lifecycle，hook 與 planner 只接線且 raw 淨 0）；"
     "散文搬遷不適用（新增全是判準本體與注入語料）。逐檔清單見 "
     "CrossPlatform_R106_Scan_Findings.md 的 R113 標記行。"),
    ("R114", 89910, 90351, 441,
     "[非淨減法輪] v2.1.13 G3+G4 接力狀態機＋哨兵自癒落地（喚醒鏈最後一哩實作批 (c)+(d)；"
     "施工圖＝PRD_Amendment_R113_WakeChain_LastMile.md §3(c)/(d)／§4 V-c1~V-d4）。標號改用 "
     "R114（非回頭改寫 R113 三列：R113 淨額合計 458 已逼近其上限 585，本輪 441 若仍記 "
     "R113 會單輪超出上限；R114 語意對應 PRD §0「四方複審後落款、G1~G4 實作批解凍」時點）。"
     "淨額 441＝test_context_budget_guard.py +427（RelayStateMachineTruthTableTest／"
     "RelayProgressAndCapTest／RelaySettleWindowTest／RelayFailurePathsTest／"
     "SentinelArmingCriterionTest 擴面、兩處既有 spawn-mock 補 git 快照分流、E501 存量債"
     "棘輪兩處折行）＋本檔自身 +14（本稽核列＋rewrite ledger 接鏈列 DEF-200-234＋凍結"
     "前綴延伸 84→85）。逐檔清單見 CrossPlatform_R106_Scan_Findings.md 的 R114 標記行。"),
    ("R115", 90351, 90340, -11,
     "[收斂棒] 棒A／棒B／治理批累積漂移一次性收束："
     "test_block_destructive_git_r83.py +93（DEF-200-238＋R115 L3 保護面新增二檔）、"
     "test_context_budget_guard.py 原始 +684（R115 修復 F1~F4／DEF-200-239／v2.1.13 C5），"
     "以類級 docstring 沿革搬遷抵銷 -930（三檔合計，全文搬至 "
     "CrossPlatform_Guard_Line_History.md〈R115 追加〉節，程式碼內只留一行指標；"
     "三支補回一句真實 root_infra 路徑指標，修復分桶棘輪 `prose` 桶誤判 +6；"
     "全部指標行因 E501 折成兩行 +111；DEF-200-239 現查測試補 encoding= 與 "
     "_ps_engine SSOT 各 +3，修復 subprocess 編碼／ps_engine 存量鎖）"
     "＋本檔自身 +22。淨額 -11，兌現款(11)（終止 R113/R114 連兩輪上升 streak）；"
     "同輪兌現款(12)：cap 585→577，重新武裝 117／570。doc_loc 同輪修復 "
     "_GHOST_SYMBOL_BASELINE 30→29（史料搬遷後唯一引用歸零，依 stale 向指示刪除）。"
     "逐項見 CrossPlatform_R106_Scan_Findings.md 的 R115 標記行。"),
    ("R115", 90340, 90350, +10,
     "[非淨減法輪][同輪追加] 雲端首紅修復：假 scheduler 後端 credential_key 由硬編 "
     "schtasks 家改為 sb.select().credential_key 對齊當平台 production 後端（posix 讀 "
     "launchd 憑證欄、硬編致空憑證紅）＋DEF-200-239 skip 補 [WINDOWS-NATIVE-ONLY] 標籤"
     "（cbg +3 含 skip 行 EAW 寬度折行）＋本稽核列與 rewrite ledger 接鏈列自身（本檔 "
     "+7）；同輪合併淨額 -11+10=-1 仍 ≤0。逐項見 CrossPlatform_R115_Debt_Closure.md。"),
    ("R115", 90350, 90344, -6,
     "[收輪補釘二] posix 雲端紅第二根因（DEF-200-239 姊妹漏網）："
     "SpendLimitReachesAHumanTest._tick 未隨 239 注入假 scheduler 後端，posix "
     "NoCarrierBackend（list_jobs 確定空＋arm 恆敗）走進 _heal_armed_drift 新 loud 分支"
     "誤觸兩測試（cbg +11）；同批搬遷兩塊 WHY 散文 -24 抵銷＋本稽核列與接鏈列自身（本檔 "
     "+7）。同輪合併淨額 -1-6=-7 仍 ≤0。逐項見 CrossPlatform_R115_Debt_Closure.md。"),
    ("R116", 90344, 90917, 573,
     "[非淨減法輪] ADR-XPLAT-013 Phase2 (b)(c) 分軌計價落地（DEF-200-211；裁決存證＝"
     "AutoSDD_Adjudication_Record_R110.md §1.4 D-1~D-6）：D-1(S-2) 回歸鎖軌分軌計價"
     "（新平行表 _REGRESSION_LANE_LOG＋lane_split_problems()＋repin_growth_problems() "
     "擴 regression_lane 參數，已接進生產閘門）；D-2 M1 拆雙指標（既有門檻不動）；"
     "D-3 ruff S102 接 .claude/hooks/／tools/／AutoClaude/（既有 compile+exec 慣用句"
     "補 noqa 理由）；D-4 (c) 降級觀測欄（guard_line_composition()，只印不擋）；"
     "D-5 U6 核准現值門檻／U7 方針定案（逐一改寫，落地未完成）／U9 到期輪常數機械"
     "保底（真拆未做）；D-6 回歸鎖軌上限實測取值（`_regression_lane_cap_basis()`）。"
     "合法出口逐條實查：刪死碼不適用；抽共用層不適用（各自單一消費端）；散文搬遷"
     "不適用（新增皆判準本體與注入語料）。本檔自身編修含本稽核列與凍結前綴延伸。"
     "逐檔清單見 CrossPlatform_R116_Scan_Findings.md。"),
    ("R116", 90917, 90921, 4,
     "[非淨減法輪] Architect 鏡一審承接（同輪補釘，含本稽核列與接鏈列自身）：A-1 三行 "
     "E501 縮短（行數不變）＋A-2 到期輪 lookahead 後設鎖（紅綠自證）＋N-1 cap_basis "
     "失蹤兜底；散文壓縮抵銷後 +577＝cap 貼線。CrossPlatform_R116_Scan_Findings.md。"),
    ("R117", 90921, 91210, 289,
     "[非淨減法輪] P1-2/P1-3 喚醒鏈落地（DEF-200-234/236 驗收批）：巡邏 tick 無主分支＋"
     "持久 notify_queue 的落款驗收回歸鎖記回歸鎖軌（軌表同輪申報 238，分軌第一次實戰"
     "消費；功能軌淨額＝稽核與儀式行＋複審承接 A-2/N-3/SD-1 自身）；同輪兌現款(12)"
     "＝(117,570) 並重新武裝 119/564（步伐 6<7）。CrossPlatform_R116_Scan_Findings.md。"),
    ("R117", 91210, 91253, 43,
     "[非淨減法輪][全額功能軌] P1-4 D3 檢查表規則鎖落地（DEF-101-886 檢查表形態解）："
     "dispatch_checklist_problems() 節內判準＋紅綠自證（首版全檔搜尋 vacuous 被突變"
     "驗紅抓到後收窄）＋本稽核列與接鏈列自身。CrossPlatform_R116_Scan_Findings.md。"),
    ("R118", 91253, 91269, 16,
     "[非淨減法輪] DEF-200-212 P1-5 收尾批：crossref 原始 +129、doc_loc +12；"
     "crossref 十七支 class-level docstring（Rule 9 意圖敘事非判準本體）原文分四"
     "批搬至 CrossPlatform_Guard_Line_History.md 抵銷 -184。R118 全輪七列合計 -6"
     "（raw 已 ≤0，兌現款(11)：終止 R116/R117 連兩輪上升）；另 16 行守欄不變式"
     "測試記帳歸回歸鎖軌（記帳誠實度，非必要湊額）。逐項見 "
     "CrossPlatform_R118_Debt_Closure.md。"),
    ("R118", 91269, 91287, 18,
     "[非淨減法輪][同輪追加] 本表自身編修：新增上一列稽核列＋回歸鎖軌新列＋凍結表二值"
     "（本檔 +18）；以下一列史料搬遷抵銷。逐項見 CrossPlatform_R118_Debt_Closure.md。"),
    ("R118", 91287, 91264, -23,
     "[同輪追加] 第二批史料搬遷：crossref 再搬三支 class-level docstring（"
     "TestEveryLegalFirstWordIsClassifiable／TestVagueBucketCountingStillWorksWhenReached／"
     "TestClosingRoundProblemsWiring，皆 Rule 9 意圖敘事非判準本體）至 "
     "CrossPlatform_Guard_Line_History.md 同節，crossref 再減 -26；抵銷上一列自身"
     "落地後的殘餘量測差 +3（上一列文字本身的行數在落地當下已與宣告淨額有 3 行"
     "落差，一併於本列吸收）。逐項見 CrossPlatform_R118_Debt_Closure.md。"),
    ("R118", 91264, 91273, 9,
     "[非淨減法輪][同輪追加] 本表自身收尾編修：新增本列與 frozen 表值同步（本檔 +9）。"
     "逐項見 CrossPlatform_R118_Debt_Closure.md。"),
    ("R118", 91273, 91265, -8,
     "[同輪追加] 第三批史料搬遷 crossref -12（兩支）；含本列與首列文字訂正 +4。"
     "逐項見 CrossPlatform_R118_Debt_Closure.md。"),
    ("R118", 91265, 91265, 0,
     "[同輪追加] 前五列文字訂正（補 [非淨減法輪] 標記與逐檔清單指標）與本列自身"
     "相抵，本檔淨額不變。逐項見 CrossPlatform_R118_Debt_Closure.md。"),
    ("R118", 91265, 91247, -18,
     "[同輪追加] 第四批史料搬遷 crossref -21（三支）；含本列自身 +3。逐項見 "
     "CrossPlatform_R118_Debt_Closure.md。"),
    ("R119", 91247, 91384, 137,
     "[非淨減法輪][全額功能軌] P1-6 落地：skip 天花板①②③與 M6 落款④共同變更鎖，逐項見 "
     "CrossPlatform_R119_Guard_Repin_Evidence.md（test_skip_ceiling_ratchet_direction.py "
     "165→302，+137）。"),
    ("R119", 91384, 91402, 18,
     "[非淨減法輪] 本表自身編修（新增上一列稽核列＋本列自身＋凍結表值同步＋"
     "_REPIN_NET_CAP_SCHEDULE 到期義務兌現列 `(119, 564)` 與重新武裝註解＋"
     "_FROZEN_PREFIX_REWRITE_LEDGER 新列），逐項見 "
     "CrossPlatform_R119_Guard_Repin_Evidence.md（本檔 +18：7122→7140）。"),
    ("R119", 91402, 91410, 8,
     "[非淨減法輪] test_subprocess_encoding_hygiene 覆審揪出 "
     "_origin_main_head_diff() 兩處 subprocess.run(text=True) 缺 encoding，補 "
     "encoding=\"utf-8\", errors=\"replace\"（+2：302→304）＋本表本列自身編修＋"
     "凍結表值同步，逐項見 "
     "CrossPlatform_R119_Guard_Repin_Evidence.md（本檔 +6：7140→7146）。"),
    ("R119", 91410, 91417, 7,
     "[非淨減法輪] 前綴協同改寫帳本新列＋本表值同步，逐項見 "
     "CrossPlatform_R119_Guard_Repin_Evidence.md（本檔 +7：7146→7153）。"),
    ("R119", 91417, 91621, 204,
     "[非淨減法輪] P1-6 批修復包（DEF-200-240 同批延續，push 被 pre-push 擋下後修復）："
     "F1 共同變更鎖判準粒度由檔案級改為剖面鍵值級——原判準連自己新增這道鎖的變更"
     "（`a1fbbba`）都誤判為違規（層③檔案被 touch 但 `_FROZEN_CEILING_MAX` 字面零"
     "變動），新增 `_extract_dict_literal`／`_dict_literal_changed`／"
     "`_source_path_value_changed` 等取數函式與五格反事實測試（含真實重演 "
     "`7f8c96a`／`origin/main..HEAD`）；F2 為 `governance_docs.py` E501 拆行，"
     "零貢獻本檔。逐項見 CrossPlatform_R119_Guard_Repin_Evidence.md"
     "（test_skip_ceiling_ratchet_direction.py 304→508，+204）。"),
    ("R119", 91621, 91630, 9,
     "[非淨減法輪][同輪追加] 本表自身編修（新增上一列稽核列＋凍結表值同步＋"
     "prefix_len 更新本身），同 R95~R101 既有體例。逐項見 "
     "CrossPlatform_R119_Guard_Repin_Evidence.md（本檔 +9：7153→7162）。"),
    ("R119", 91630, 91634, 4,
     "[非淨減法輪][同輪追加] 本表自身編修（上一列稽核列自身＋凍結表值同步），"
     "同 R95~R101 既有體例。逐項見 CrossPlatform_R119_Guard_Repin_Evidence.md"
     "（本檔 +4：7162→7166）。"),
    ("R119", 91634, 91646, 12,
     "[非淨減法輪][同輪追加] 本表自身編修收斂（上一列稽核列自身 +4／"
     "_FROZEN_PREFIX_REWRITE_LEDGER 新列 +4／本列自身 +4），逐項見 "
     "CrossPlatform_R119_Guard_Repin_Evidence.md（本檔 +12：7166→7178）。"),
    ("R120", 91646, 91776, 130,
     "[非淨減法輪][全額功能軌] P1-7 SD-4/SD-8 落地：RELAY_NEXT 排程失敗視同停止次態"
     "重掛哨兵＋settle_window 外圈例外兜底（新測試三案＋突變六發驗紅，+126）；"
     "SA-4 實彈取證揪出 deny 死規則，va3 鎖改為 Edit 規則承重語意（+4）。逐項見 "
     "CrossPlatform_R120_Debt_Closure.md（test_context_budget_guard.py 9645→9775）。"),
    ("R120", 91776, 91785, 9,
     "[非淨減法輪][同輪追加] 本表自身編修（上一列稽核列＋本列自身＋凍結表值同步＋"
     "prefix_len 更新），同既有體例。逐項見 CrossPlatform_R120_Debt_Closure.md"
     "（本檔 +9：7178→7187）。"),
    ("R120", 91785, 91793, 8,
     "[非淨減法輪][同輪追加] 全套揪出 sha 鏈未接：_FROZEN_PREFIX_REWRITE_LEDGER 追加本輪"
     "鏈接一筆（4554dbed→現值）＋本稽核列＋凍結表值同步＋prefix_len 109→110，逐項見 "
     "CrossPlatform_R120_Debt_Closure.md（本檔 +8：7187→7195）。"),
    ("R122", 91793, 92646, 853,
     "[非淨減法輪][全額功能軌] 精準修復輪三筆 fixed 落地——DEF-200-169 扇出視窗剩餘秒數"
     "（test_context_budget_guard.py +131）／DEF-200-170 MIN_TESTS 判準改綁零相依餘裕軸"
     "（test_run_root_unittests.py +286）／DEF-200-222 archive 併發鎖與縮窄阻斷面（新檔 "
     "test_apply_lock.py +167、test_check_archive_required.py +160、"
     "test_archive_apply_locked.py +102，既有 test_check_defect_log_crossref.py +7）。"
     "逐項見 CrossPlatform_R122_Debt_Closure.md。"),
    ("R122", 92646, 92660, 14,
     "[非淨減法輪][同輪追加] 本表自身編修：凍結表值同步、上一列與本列自身、"
     "prefix_len 110→112，同 R119／R120 既有體例（貼表當下本檔尚未含這兩列，故淨額分兩"
     "列記）。逐項見 CrossPlatform_R122_Debt_Closure.md（本檔 7195→7209）。"),
    ("R122", 92660, 91649, -1011,
     "[淨減法] 護欄層散文搬遷抵銷（款(10)(11) 的合法出口，同 R89／R104 判例）：下列鎖檔"
     "的歷史沿革段落逐塊逐字保全搬至 CrossPlatform_R122_Guard_Prose_Migration.md——"
     "test_check_hooks_liveness.py 3581→3296／test_archive_defect_log.py 3989→3839／"
     "test_run_root_unittests.py 2558→2422／test_bash_probe_spec_contract.py 983→865／"
     "test_dev_start.py 6636→6527／test_install_windows_nightly.py 1469→1385／"
     "test_smoke_ci_sync.py 1334→1258／test_context_budget_guard.py 9906→9835。與本輪"
     "前兩列合計淨額 ≤0 ⇒ 款(11) 連續上升 streak 歸零；同輪兌現 _REPIN_NET_CAP_SCHEDULE "
     "到期義務 (122, 559)。搬遷安全邊界、rejected 清單（四支檔整檔排除＋七段就地還原，"
     "皆因該段落是別的機械物的逐字比對面）與保全檢查見該搬遷檔檔頭。"),
    ("R122", 91649, 91668, 19,
     "[非淨減法輪][同輪追加] 本檔自身編修：兩筆到期義務就地兌現（`_PHASE2_REVIEW_LOG` "
     "追加 `[維持觀察]` 列／`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 具名展延並把理由逐字"
     "寫在該常數旁）＋凍結表值同步＋prefix_len 與指紋鏈同步＋本列自身＋裸計數措辭訂正"
     "（本檔自訂紀律「散文不得寫死可機械算出的計數」在上一列落地的當回合把作者抓到一次，"
     "照實記）。逐項見 CrossPlatform_R122_Debt_Closure.md。"),
    ("R123", 91668, 91990, 322,
     "[非淨減法輪][全額功能軌] 精準修復輪第二棒落地：DEF-200-200「已過期」述詞四層共用並"
     "分流時刻已過去／時鐘偏移兩義（test_quota_policy.py 3198→3316）／DEF-200-183 剖面鍵"
     "文法 SSOT＋pgextras 軸＋方向鎖 re-key 破洞（test_skip_ceiling_ratchet_direction.py "
     "508→700）／DEF-200-205 PRD §6.2 與 §4.5.9 的模組接上生產呼叫端（回歸鎖落 "
     "AutoClaude/tests，不計本層）。🔴 為何另立輪號而非併入上一棒：上一棒已 commit／push／"
     "雲端全綠＝已收輪，本棒是其後的新一批；併列會讓上一棒的 -125 被本棒抵銷回正、款(11) "
     "的 streak 歸零判定失實——判準本身把「拆輪次」列為合法出口（拆輪次不是拆列）。"
     "逐項見 CrossPlatform_R123_Debt_Closure.md。"),
    ("R126", 91990, 92306, 316,
     "[非淨減法輪][全額功能軌] 落地輪：R121 裁決包 needs-dev 五筆（241／137／244／243 過四方"
     "設計複審後動碼；213 隨 241 治本解除死結）＋八筆小項的回歸鎖同批落地（含本檔自身重釘 +20）——"
     "test_check_defect_log_crossref.py 3858→3891（241 done_ids 兩判準）／"
     "test_context_budget_guard.py 9835→9902（257 等待窗方向鎖＋137 PRD 邊際）／"
     "test_quota_policy.py 3316→3406（244 gate_excluded＋243 tightest 掃描鎖）／"
     "test_smoke_ci_sync.py 1258→1353（951 skip 模組清單同步鎖）／test_run_root_unittests.py "
     "2422→2428（803 具名 fail）／test_doc_loc_baseline_freshness_r60.py 7126→7131（247 幽靈路徑"
     "基線一筆）。款(11)：R123 為連續上升第 1 輪、R124／R125 淨額 0 未記列，本輪為第 2 輪 ⇒ "
     "下一輪淨額必須 ≤ 0（交棒書已明寫）。同輪兌現到期義務 (126, 555) 並重新武裝 128／552。"
     "逐項見 CrossPlatform_R126_Debt_Closure.md。"),
)


#: 生效輪次 81：**刻意不追溯到 R80 自己**（現存每一列都落在款(7) 凍結前綴內，回頭改會先撞
#: append-only 指紋）。WHY 全文（R80 包 C／+1528 承認）搬至 CrossPlatform_R97_Scan_Findings.md
#: 〈_NET_DELTA_ACCOUNTING_SINCE WHY〉節；史料原家＝AutoSDD_improving_104.md §1 Q2。
_NET_DELTA_ACCOUNTING_SINCE = 81

#: R84 ARCH-01：重釘的「代價」機制。形狀選擇＝(b) 每輪淨額上限＋方向鎖（非 (a) 配對制——
#: 配對制會讓本輪合法的重釘做不到，ARCH-02 已判過這種紅了沒出路的鎖會被關掉）。
#: 兩常數只准下修：`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`＝連兩輪上升、第三輪必須 ≤0；
#: `SINCE` 只准調小（生效點更早＝更嚴）。R85 起加上分段上限表（下方），解的是「下修不追溯」
#: 與 append-only 指紋互斥的結構性死結。設計取捨全文、(a)(b) 兩案評估、R84 F3/B-1 起算錨
#: 注入實測，搬至 CrossPlatform_R97_Scan_Findings.md〈R84 ARCH-01 代價機制 WHY〉節。
_REPIN_NET_CAP_SCHEDULE: tuple[tuple[int, int], ...] = (
    (84, 5400),   # R84：款(10) 上線，取歷來單輪最大淨額（今天零假紅、明天只准更緊）
    (85, 3200),   # R85：兌現款(12) 的到期義務（見下方 `_REPIN_NET_CAP_DUE_*`）
    (87, 2600),   # R87：到期輪下修。本輪自身淨額遠低於此（事故鎖 ＋ 派工前置檢查兩組）
    (89, 2000),   # R89：到期輪下修。本輪淨額 ≤ 0（史料搬遷抵銷新判準，兌現款(11)）
    (91, 1600),   # 到期輪下修（款(12)）。步伐 400 < 前一段的 600：見上方「步伐刻意變小」
    (93, 1300),   # 到期輪下修（款(12)）。步伐 300 < 前一段的 400，續守「步伐刻意變小」
    (95, 1100),   # 到期輪下修（款(12)）。步伐 200 < 前一段的 300，續守「步伐刻意變小」
    (97, 950),    # 到期輪下修（款(12)）。步伐 150 < 前一段的 200，續守「步伐刻意變小」；
                  # 恰好落在到期目標 950（`_REPIN_NET_CAP_DUE_TARGET` 兌現前的值）
    (99, 850),    # 到期輪兌現：`_REPIN_NET_CAP_DUE_ROUND`/`_REPIN_NET_CAP_DUE_TARGET` 到期
                  # 義務本列（前一段到期輪就寫好、本輪兌現）。本輪淨額 667 遠低於新上限，
                  # 兌現後未緊接著再排下一段到期義務——步伐是否續縮留給下一次到期輪決定
    (101, 750),   # 到期輪兌現：`_REPIN_NET_CAP_DUE_ROUND=101` 本輪剛好到期，cap 降到
                  # `_REPIN_NET_CAP_DUE_TARGET` 本身（同 R99 判例：兌現值可以恰好貼齊
                  # 到期目標）。本輪同時落地 DEF-200-208 一次性例外（見
                  # `_REPIN_APPROVED_ROUND_OVERAGE`）——兩件事互相獨立：降 cap 是照既有
                  # 到期義務的例行維護，例外表管的是「這一輪的真實淨額超過新 cap 時
                  # 不計入款(10)(11)」，前者完全不放寬任何門檻。
    (103, 700),   # 到期輪兌現：`_REPIN_NET_CAP_DUE_ROUND=103` 本輪剛好到期（DEF-200-221
                  # 收尾單人窗口重釘落在本輪），cap 降到 `_REPIN_NET_CAP_DUE_TARGET`
                  # 本身（同 R99／R101 判例：兌現值可以恰好貼齊到期目標）。同輪就地 round-label-ok
                  # 重新武裝下一段：步伐 40 < 前一段的 50，續守「步伐刻意變小」。
    (105, 660),   # 到期輪兌現（DEF-200-224）：cap 降到 `_REPIN_NET_CAP_DUE_TARGET` round-label-ok
                  # 本身。同輪重新武裝下一段：步伐 30 < 前一段的 40，續守「步伐變小」。
    (107, 630),   # 到期輪兌現（DEF-200-166／171 結案窗口）：cap 降到到期目標本身。
                  # 同輪重新武裝下一段：步伐 20 < 前一段的 30，續守「步伐變小」。
    (109, 610),   # 到期輪兌現（Gap C 接線窗口）：cap 降到到期目標本身。
                  # 同輪重新武裝下一段：步伐 15 < 前一段的 20，續守「步伐變小」。
    (111, 595),   # 到期輪兌現（DEF-200-121 修復窗口）：cap 降到到期目標本身（同 R99 判例）。
                  # 同輪重新武裝下一段：步伐 10 < 前一段的 15，續守「步伐變小」；並補上
                  # 到期輪自身的 lookahead 後設鎖（見 `_REPIN_DUE_ROUND_MAX_LOOKAHEAD`）。
    (113, 585),   # 到期輪兌現（結構性長債分軌輪，2026-08-30）：cap 降到到期目標本身。
                  # 同輪重新武裝下一段：步伐 8 < 前一段的 10，續守「步伐變小」，見 due 常數旁註。
    (115, 577),   # 到期輪兌現（收斂棒，三個修復棒＋治理批累積漂移一次性合法收束）：
                  # cap 降到到期目標本身（同 R99/R101/R113 判例 round-label-ok）。
                  # 同輪重新武裝下一段：步伐 7 < 前一段的 8，續守「步伐刻意變小」，見 due 常數旁註。
    (117, 570),   # 到期輪兌現（P1-2/P1-3 喚醒鏈批）：cap 降到到期目標本身 round-label-ok
                  # （同 R99/R101/R115 判例 round-label-ok）。同輪重新武裝：步伐 6 < 前段 7，
                  # 續守「步伐刻意變小」，見 due 常數旁註。
    (119, 564),   # 到期輪兌現（P1-6 skip 天花板①②③與 M6 落款④共同變更鎖批）：cap 降到
                  # 到期目標本身（同 R99/R101/R115/R117 判例 round-label-ok）。同輪重新
                  # 武裝下一段：步伐 5 < 前段 6，續守「步伐刻意變小」，見 due 常數旁註。
    (122, 559),   # 到期輪兌現（精準修復輪：三筆缺陷回歸鎖＋護欄層散文搬遷抵銷）：cap 降到
                  # 到期目標本身（同 R99/R101/R115/R117/R119 判例 round-label-ok）。上一段
                  # 到期輪落在稽核痕跡未走到的輪次，本輪是它之後第一次重釘故就地兌現。
                  # 同輪重新武裝下一段：步伐 4 < 前段 5，續守「步伐刻意變小」，見 due 常數旁註。
    (126, 555),   # 到期輪兌現（落地輪：結案批的回歸鎖同批落地）：到期輪 124 落在稽核痕跡未走到的
                  # 輪次（R124／R125 淨額 0 未記列 round-label-ok），本輪首次重釘就地兌現，cap 降到
                  # 到期目標本身（同 R99/R101/R115/R117/R119/R122 判例 round-label-ok）。
                  # 同輪重新武裝下一段：步伐 3 < 前段 4，續守「步伐刻意變小」，見 due 常數旁註。
)
#: 生效點＝首列輪號、現行上限＝末列上限，**皆由表導出不另立常數**（R73 判例：一份知識一個家）。
_REPIN_ROUND_CAP_SINCE = _REPIN_NET_CAP_SCHEDULE[0][0]
_REPIN_ROUND_NET_CAP = _REPIN_NET_CAP_SCHEDULE[-1][1]
_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2
_FROZEN_REPIN_NET_CAP_SCHEDULE = ((84, 5400), (85, 3200), (87, 2600))
_FROZEN_REPIN_ROUND_CAP_SINCE = 84
_FROZEN_REPIN_ROUND_NET_CAP = 2600
_FROZEN_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2

#: 🔴 DEF-200-208：四方複審核准的**一次性**單輪 cap／連續上升例外登記表——名冊不是開關：
#: 只赦免「指名輪號＋精確淨額」逐字對上的那一個真實事件，未列名輪次（含未來任何一輪、
#: 含合成語料撞同輪號）原判準不受影響；門檻本體與判準邏輯一個字未動。立案三事實、裁決
#: 理由與「為何 key 綁精確淨額」全文搬至 CrossPlatform_Guard_Line_History.md
#: 〈DEF-200-208 一次性例外名冊 WHY〉節（本檔不複寫）。
_REPIN_APPROVED_ROUND_OVERAGE: dict[str, tuple[int, str]] = {
    "R101": (1332, (
        "四方複審核准 DEF-200-208 一次性例外：本輪同時①兌現 _REPIN_NET_CAP_DUE_ROUND "
        "到期義務（cap 850→750）②收斂既有鎖檔跨多輪陳舊逐檔漂移（ADR-XPLAT-013 落地後首次 "
        "被 --print-guard-lines 覆核揪出，此前歷輪重釘皆未處理過）③本檔自身修復 "
        "pricing_exemption_problems() provenance 判準與本例外機制自身的編修，真實淨額 "
        "+1332 因此遠超任何單輪上限，且緊接 R99／R100 兩輪連續上升之後。裁決：一次性收斂"
        "優於放寬門檻本體或讓漂移繼續累積，故核准本輪不計入款(10)(11)；net_cap_for_round() "
        "與 _REPIN_MAX_CONSECUTIVE_RISING_ROUNDS 的判準邏輯與門檻數字本輪一個字未動，"
        "本表只涵蓋 R101 這一個精確淨額，往後任何一輪（含日後再標成 R101 的合成語料）"
        "的違規照樣原判準阻擋。"
    )),
}
#: 一次性例外必須真的只有一次——超過這個數字就不再是例外，是變相把整套 cap／streak
#: 機制改成「寫張條子就能繞過」。**只准調小**（收緊；理論下限 0＝永遠不再核准新例外）。
_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES = 1
#: 核准理由的最短長度（同 `phase2_review_problems()` 款(4) 的「延期兩個字不是理由」）。
_REPIN_APPROVED_ROUND_OVERAGE_MIN_REASON_LEN = 20


# ══════════════════════════════════════════════════════════════════════════════
# ADR-XPLAT-013 Phase 2 (b)：回歸鎖軌分軌計價（D-1＝S-2，DEF-200-211 落地批；R116） round-label-ok
# ══════════════════════════════════════════════════════════════════════════════
# 立案＝ADR-XPLAT-013_Phase2_Proposal_R108.md §0~§1；裁決＝AutoSDD_Adjudication_
# Record_R110.md §1.4 D-1/D-2/D-6（皆住 docs/04_planning/）。射程只延伸記帳語意，
# raw-line 度量一字不動：款(10)(11) 的輸入從「主表淨額」改為「主表淨額 − 同輪
# 回歸鎖軌淨額」，回歸鎖軌另有自己上限、且不受款(11) 連續上升鎖管（結案的證據理應
# 連續增加）。🔴 不得在 `_GUARD_LINES_REPIN_LOG` 加欄（撞指紋）：改用平行表
# `_REGRESSION_LANE_LOG`，與主表以輪號對帳（`lane_split_problems()`）。

#: 平行表：`(輪號, 該輪回歸鎖軌淨額, 理由)`，append-only。**刻意從空表開始**——
#: 不追溯既有歷史（§1.4：「生效輪次，不追溯」），落地當輪（R116）自己的工作全額算進 round-label-ok
#: 功能軌（見 `_REGRESSION_LANE_SINCE` 的 WHY：不得用自己剛開的減免軌豁免自己）。
_REGRESSION_LANE_LOG: tuple[tuple[str, int, str], ...] = (
    ("R117", 238, "P1-2/P1-3 落款 PRD/ADR 指定驗收測試（ADR-XPLAT-014 §4 紅綠＋"
     "v2.1.12 §3-4 notify_rc=-2 重演＝OrphanModeWatchTest＋NotifyQueueRedeliveryTest "
     "兩類全體，全數住 test_context_budget_guard.py 測試行；分軌機制第一次實戰消費）"),
    ("R118", 16, "DEF-200-212 D4 裁決的具名豁免面工程解，其守欄不變式驗證測試："
     "test_the_exemption_registry_stays_within_its_shrink_only_cap（9 行）＋"
     "test_every_exemption_reason_meets_the_minimum_length（7 行，同一守欄機制"
     "另一半不變式），合計 16 行歸本軌（記帳誠實度分類，非必要湊額——本輪史料"
     "搬遷後主表淨額已是 -6，raw 本身即 ≤0）。"),
)

#: 生效輪次＝落地輪（R116）之後的下一輪。**只准調大**——它閘的是一條**減免軌**： round-label-ok
#: 輪號 ≥ 本值才享有「回歸鎖軌淨額不算進款(10)(11)」這個減免，調小＝把減免向更早的
#: 輪次追溯延伸＝追溯放寬（三審 A2 訂正：上一版誤把它與課稅軌類常數共用「只准調小」，
#: 極性抄反——`_NET_DELTA_ACCOUNTING_SINCE` 那種課稅軌調小才是更嚴，本常數相反）。
_REGRESSION_LANE_SINCE = 117
_FROZEN_REGRESSION_LANE_SINCE = 117

#: D-6：回歸鎖軌單輪上限，取值紀律＝「落地時實測直接填入、零加減推算、不留成長緩衝」
#: （ADR-XPLAT-012 條文五 §3；**禁止沿用** R108 提案的舊快照 287）。基準＝ round-label-ok
#: `_regression_lane_cap_basis()` 現查得到的 R97 那一列（見該函式 docstring 的
#: 逐項算術驗證）。只准往下改（同 `_REPIN_ROUND_NET_CAP` 款式）。
_REGRESSION_LANE_ROUND_CAP = 309
_FROZEN_REGRESSION_LANE_ROUND_CAP = 309

#: 形狀照抄 `_REPIN_APPROVED_ROUND_OVERAGE`（誤課稅的具名出口）：空表起始，只有指名
#: 輪號＋精確淨額＋≥20 字理由才赦免，其餘一律原判準阻擋。
_REGRESSION_LANE_APPROVED_OVERAGE: dict[str, tuple[int, str]] = {}
_REGRESSION_LANE_APPROVED_OVERAGE_MAX_ENTRIES = 1
_REGRESSION_LANE_APPROVED_OVERAGE_MIN_REASON_LEN = 20

#: 款「軌別未申報」的明文出口：主表某輪淨額 > 0 而回歸鎖軌表無對應列時，允許在**主表**
#: 那一列的理由欄寫這個字面標記，宣告該輪全額歸功能軌（不必為淨額 0 的規律結案輪
#: 硬擠一列進 `_REGRESSION_LANE_LOG`）。申報是強制的，不是選填——見 §1.5 第四道套利門。
_LANE_FULL_FUNCTIONAL_TOKEN = "[全額功能軌]"


def _regression_lane_cap_basis() -> tuple[str, int]:
    """D-6 取值基準——回傳撐起 `_REGRESSION_LANE_ROUND_CAP` 的那一列（證明非憑空取數）。

    候選＝歷來單列淨額**全部**由回歸鎖新增組成的列：R97 +309（103+81+107+18=309，
    與列淨額逐字相等）；R106 +287 同型但較小（cap 語意＝實測最大，故取 R97）；其餘 round-label-ok
    含「回歸」字樣的更大列皆混合列，整列採計會把功能成長算進減稅軌（§1.5 套利門方向）。
    誠實劃界：不是候選 2（C1~C4）全自動分類器（未做，登記在提案 §4 item 2）；只重驗
    這一列自陳成分算術與淨額相符。N-1（Architect 鏡承接）：列失蹤時拋可讀訊息。
    """
    row = next((r for r in _GUARD_LINES_REPIN_LOG if r[0] == "R97" and r[3] == 309), None)
    # N-4（SA 鏡登記，未修）：本分支缺合成注入紅側測試——cap 貼線故延後，收尾窗口再評。
    if row is None:
        raise AssertionError("[cap 基準失蹤] _GUARD_LINES_REPIN_LOG 找不到取值基準（R97 "
                             "那一列）——cap 基準浮動，須重新實測取值並同步更新本函式與常數")
    return row[0], row[3]


# ══════════════════════════════════════════════════════════════════════════════
# ADR-XPLAT-013 §9.3／U9（D-5 裁決，R116 round-label-ok）：四支 `[ROOT-TOOLS]` 檔舊尺債到期輪。
# 本批只落地「到期輪常數＋機械保底」半格；真拆未做、over_by 現查 187（逐檔數字、判準
# 出處與惡化態勢＝`CrossPlatform_R116_Scan_Findings.md` §D-5，本檔不重抄史料）。
# 🔴 精準修復輪具名展延 121 → 127（判準出口②，**不得靜默沿用**故理由逐字寫在這裡）：
# 本輪標的是帳本三筆缺陷結案，四支 `[ROOT-TOOLS]` 檔的真拆屬獨立重構持有面——依鐵律七，
# 其常數／史料／消費端跨檔，任一並行包手上都做不完，只能由獨立的收尾單人窗口做。本輪實際
# 完成的是**同族的另一半**：護欄層散文搬遷抵銷（見 `_GUARD_LINES_REPIN_LOG` 末列），它證實
# 「把史料逐字搬進具名證據檔」在本 repo 是可行且安全的路徑，而那正是真拆要用的手法 ⇒ 展延
# 換到的不是時間而是一個已驗證的手法。取 `_ROOT_TOOLS_DEBT_DUE_MAX_LOOKAHEAD` 的上界而非
# 更近的輪次，理由是真拆需要一個不與缺陷結案競爭的獨立窗口；再展延須另附理由，不得沿用本段。
_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND = 127
#: 清償旗標——真拆完成後改 True。刻意用布林而非重建舊尺計數器（ADR §9.3「舊尺已廢」）。
_ROOT_TOOLS_OLD_SCALE_DEBT_RESOLVED = False
#: A-2 後設鎖：到期輪只准落在「現查輪＋lookahead」內，推遠（如 9999）當場紅；shrink-only
#: 凍結雙生子（同 `_REPIN_DUE_ROUND_MAX_LOOKAHEAD`／DEF-200-121 同族）。
_ROOT_TOOLS_DEBT_DUE_MAX_LOOKAHEAD = 5
_FROZEN_ROOT_TOOLS_DEBT_DUE_MAX_LOOKAHEAD = 5


def root_tools_debt_due_problems(
    resolved: bool = _ROOT_TOOLS_OLD_SCALE_DEBT_RESOLVED,
    due_round: int = _ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND,
    latest_round: int | None = None,
) -> list[str]:
    """空＝通過。純函式，紅綠由合成注入自證。機械保底不是「已真拆」的證明——只保證
    「到了到期輪還沒清償」不被靜默遺忘（紀律同 `_REPIN_NET_CAP_DUE_ROUND`：可延期的
    到期日不是到期日，出口只有清償或由複審具名展延且仍受 lookahead 界約束）。"""
    live = live_repin_round() if latest_round is None else latest_round
    bound = live + _ROOT_TOOLS_DEBT_DUE_MAX_LOOKAHEAD
    if due_round > bound:
        return [f"[到期輪超界] U9 到期輪 R{due_round} > 現查輪＋lookahead（R{bound}）——"
                "展延必須具名寫理由且仍受本界約束，不得把常數推遠"]
    if not resolved and live >= due_round:
        return [
            f"[技術債逾期] ADR-XPLAT-013 §9.3／U9 的四支 [ROOT-TOOLS] 檔舊尺技術債"
            f"到期輪已是 R{due_round}（現查 R{live}）而尚未清償——出口二擇一："
            "①真拆到舊尺不破線後把 `_ROOT_TOOLS_OLD_SCALE_DEBT_RESOLVED` 改 True"
            "（同批訂正現查 over_by 為 0）；②由下一次複審具名展延"
            "（追加更大的 `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 並寫明理由，"
            "不得靜默沿用）"
        ]
    return []


def net_cap_for_round(no: int, schedule: Sequence[tuple[int, int]] | None = None) -> int:
    """輪號 `no` 當時在位的單輪淨額上限（表為輪號遞增；早於第一列者沿用第一列）。"""
    table = _REPIN_NET_CAP_SCHEDULE if schedule is None else schedule
    cap = table[0][1]
    for since, value in table:
        if no >= since:
            cap = value
    return cap


def net_cap_schedule_problems(
    schedule: Sequence[tuple[int, int]] | None = None,
    frozen: Sequence[tuple[int, int]] | None = None,
) -> list[str]:
    """分段上限表的形狀鎖（空＝通過）：append-only、輪號遞增、上限只准遞減。

    WHY 三條缺一不可：少了 append-only，把 `(84, 5400)` 就地改成 `(84, 99999)` 就能讓
    款(10) 對整段歷史失效；少了輪號遞增，`net_cap_for_round()` 的「末列在位」語意不成立；
    少了只准遞減，追加一列更寬的上限＝放寬，而那是純量後設鎖擋不到的地方。
    """
    table = list(_REPIN_NET_CAP_SCHEDULE if schedule is None else schedule)
    base = list(_FROZEN_REPIN_NET_CAP_SCHEDULE if frozen is None else frozen)
    problems: list[str] = []
    if table[:len(base)] != base:
        problems.append(
            f"[上限表被改寫] 前 {len(base)} 列已不等於簽入的凍結基準 {base}"
            f"（實得 {table[:len(base)]}）——本表 append-only：下修請**追加**一列"
            "（新輪號＋更小的上限）。改寫既有列＝回頭改變已收輪次當時受判的尺，"
            "而那些輪次的稽核列受款(7) 指紋保護、補不回來")
    for (r0, c0), (r1, c1) in zip(table, table[1:]):
        if r1 <= r0:
            problems.append(
                f"[上限表輪號未遞增] R{r0} 之後又出現 R{r1}——`net_cap_for_round()` "
                "靠順序決定「誰在位」，輪號不遞增時最後一列的語意不成立")
        if c1 > c0:
            problems.append(
                f"[上限表被放寬] R{r1} 的上限 {c1} 大於前一段的 {c0}——本表只准遞減。"
                "追加更寬的上限＝取消「重釘要付代價」（R84 ARCH-01），而它繞過的正是"
                "`_FROZEN_REPIN_ROUND_NET_CAP` 那道只看純量的後設鎖")
    return problems


#: R84 F3/A-03：現行上限的到期義務（R85 起每次兌現就地重新武裝下一段）。機制：稽核痕跡
#: 出現輪號 ≥ `_REPIN_NET_CAP_DUE_ROUND` 而上限未降到 `_REPIN_NET_CAP_DUE_TARGET` 以下即紅；
#: 出口＝往 `_REPIN_NET_CAP_SCHEDULE` 追加更小上限（刻意不留延期參數）。立案理由、步伐遞減
#: 設計（5400→3200 起）與 R89 互斥推導全文搬至
#: CrossPlatform_R97_Scan_Findings.md〈到期義務與重新武裝 WHY〉節；R101 起歷次兌現的 round-label-ok
#: 逐段沿革搬至 CrossPlatform_Guard_Line_History.md〈到期義務兌現沿革〉節。
#: 本次兌現（結構性長債分軌輪，2026-08-30）：cap 降到目標本身（585，見 `(113, 585)` 列），
#: 同輪重新武裝下一段：步伐 8 < 前一段的 10，續守「步伐刻意變小」且目標嚴格低於現行 cap。
#: R115 收斂棒兌現 round-label-ok：cap 降到目標本身（577，見 `(115, 577)` 列），同輪重新武裝下一段：
#: 步伐 7 < 前一段的 8，續守「步伐刻意變小」且目標嚴格低於現行 cap。
#: R117 喚醒鏈批兌現 round-label-ok：cap 降到目標本身（570，見 `(117, 570)` 列），同輪重新武裝：
#: 步伐 6 < 前一段的 7，續守「步伐刻意變小」且嚴格低於現行 cap。
#: R119 P1-6 批兌現 round-label-ok：cap 降到目標本身（564，見 `(119, 564)` 列），同輪重新武裝：
#: 步伐 4 < 前一段的 5（R122 兌現於 `(122, 559)`，重新武裝 124／555 round-label-ok）。
#: R126 落地輪兌現 round-label-ok：cap 降到目標本身（555，見 `(126, 555)` 列），同輪重新武裝：
_REPIN_NET_CAP_DUE_ROUND = 128  # round-label-ok：到期輪＝兌現輪+2（lookahead 判準的活體對照）
_REPIN_NET_CAP_DUE_TARGET = 552  # 步伐 3 < 前一段的 4，續守「步伐刻意變小」且嚴格低於現行 cap

#: DEF-200-121：到期輪自身的後設鎖——`_REPIN_NET_CAP_DUE_ROUND` 只准落在「最近稽核輪
#: ＋ lookahead」以內（歷史母體 85..113 的到期輪一律＝上一次兌現輪 +2）。可延期的到期日
#: 不是到期日：帳本注入實測「到期輪改 9999 紅 0」＝款(12) 的 `live_round >= due_round`
#: 永假、靜默熄滅，而同檔逐字宣稱「刻意沒有『延期』參數」。lookahead 自身 shrink-only。
_REPIN_DUE_ROUND_MAX_LOOKAHEAD = 2
_FROZEN_REPIN_DUE_ROUND_MAX_LOOKAHEAD = 2

#: R85：款(11)／ADR-XPLAT-002 §8.1 item 15「必須出現一次淨額 ≤ 0」的到期輪，搬成具名常數
#: 理由同上（義務要能被看見、要有到期時點；`DEF-101-757`）。只准往前挪（更早到期＝更嚴），
#: 刻意不留延期參數。沿革（此前寄生在斷言裡且一度誤寫「已達成」）全文搬至
#: CrossPlatform_R97_Scan_Findings.md〈淨減法到期輪沿革 WHY〉節。
_NET_SUBTRACTION_DUE_ROUND = 86

_DELETION_CLAIM_RE = re.compile(r"刪(?:除|掉)?\s*(\d+)\s*行")
_NOT_NET_SUBTRACTION_TOKEN = "[非淨減法輪]"
_PER_FILE_LIST_RE = re.compile(r"CrossPlatform_R\d+_\w+\.md")

#: R80 二審（NEW-SA2-01＝QA2-N2）：文件側累積總量對帳的三個常數與掃描面，判準本體見
#: `doc_guard_total_problems()`。標記形態＝「冒號後綴＋輪號」住 HTML 註解（R84 ZT-04 收窄，
#: 治假紅：`ADR-XPLAT-006`／`R83_HANDOFF.md` 指路散文曾被誤判 `[形態不符]`，收窄後假紅
#: 4→0）。收窄前後對照與擴面前置量測全文搬至
#: CrossPlatform_R97_Scan_Findings.md〈文件總量標記形態 WHY〉節。
_GUARD_TOTAL_DOC_MARK = "guard-total:"
_GUARD_TOTAL_MARK_RE = re.compile(r"<!--\s*guard-total:(R\d+)\s*-->")
#: R85 訂正：正則原本只認 `+`，讓淨減法輪的負淨額宣稱結構上讀不出三元組（判準預設「總量
#: 只會長大」，正是 M1 要消滅的假設）。符號進 group(3)、數值進 group(4)；`−`（U+2212）一併收。
_GUARD_TOTAL_TRIPLE_RE = re.compile(
    r"(\d{4,6})\s*→\s*(\d{4,6})\D{0,16}([-+−])\s*(\d{1,6})")


def guard_total_triple(mo: re.Match[str]) -> tuple[int, int, int]:
    """`(起點, 總量, **帶號**淨額)`——符號與數值分屬兩個 group，此處是唯一的組回處。"""
    return (int(mo.group(1)), int(mo.group(2)),
            int(mo.group(4)) * (-1 if mo.group(3) in "-−" else 1))
#: 兩份：計畫書（人讀的結論）與掃描發現文件（逐檔清單的家）。**兩邊都要有**——
#: 只有一邊時，刪掉那一邊就等於關掉本判準。
_GUARD_TOTAL_DOC_MIN_SITES = 2
#: R84 ZT-04 擴面立案與 F3/B-2 訂正（ADR 面已移除——ADR-XPLAT-006 合成語料結構上永遠
#: 咬不到）：交棒書那一半改由不靠標記的款(5) 真正接手（`handoff_guard_total_problems()`）。
#: 訂正沿革全文搬至 CrossPlatform_R97_Scan_Findings.md〈文件總量掃描面訂正 WHY〉節。
_GUARD_TOTAL_DOC_GLOBS = (
    "docs/04_planning/AutoSDD_improving_*.md",
    "docs/06_quality/CrossPlatform_R*_Scan_Findings.md",
    "docs/04_planning/R*_HANDOFF.md",
)

#: 交棒書檔名裡的輪號——款(5) 靠它把「這份文件在講哪一輪」變成可判的事實，
#: 而不是靠人記得標記。`R84_HANDOFF.md` ⇒ 84。
_HANDOFF_ROUND_RE = re.compile(r"(?:^|/)R(\d+)_HANDOFF\.md$")
#: 款(5) 的生效輪次。**不追溯**，理由同款(9)(10)：實查 `R74`~`R82` 九份交棒書內
#: 三元組數＝0（一個護欄層數字都沒寫過），追溯等於要求回頭替九份史料補寫一個當年
#: 根本不存在的欄位；而 `R83` 是第一份自己寫出三元組的交棒書（也正是自陳「沒人在守」
#: 的那一份）⇒ 生效點取 83，今天 R83／R84 兩份皆已相符，假紅存量 0。
_HANDOFF_RECONCILE_SINCE = 83

#: 逐檔漂移的容忍筆數（R79 收斂包）。**釘 0，且沒有理由留餘裕**——重釘時
#: `--print-guard-lines` 會把整張表逐檔照貼，餘裕只會替下一次「淨額為零的 A 減 B 增」
#: 預先開門，而那個對調正是 R79 在乾淨 HEAD 上實測到的既成事實（三支檔失真、閘門全綠）。
_GUARD_LINE_DRIFT_TOLERANCE = 0

#: **凍結前綴**的長度與內容指紋——把 append-only 由散文變成機械事實：前綴內任何一列被
#: 改寫，指紋當場不同；追加新列不動前綴。為何「固定長度前綴」而非「除最後一列外」、
#: `_REPIN_LOG_MAX_UNFROZEN_TAIL` 尾端寬限窗口的設計全文搬至
#: CrossPlatform_R97_Scan_Findings.md〈凍結前綴指紋設計 WHY〉節。兩個值皆由
#: `--print-guard-lines` 印出。
_REPIN_LOG_FROZEN_PREFIX_LEN = 116
_REPIN_LOG_MAX_UNFROZEN_TAIL = 1
_REPIN_LOG_HISTORY_SHA256 = (
    "faddc843e04246118915d909fc68085a7bb3b1f343a7bcb9dc40bf091d537743")


def repin_log_history_digest(
    log: Sequence[tuple[str, int, int, int, str]], prefix_len: int
) -> str:
    """稽核痕跡**前 `prefix_len` 列**內容的指紋（append-only 的機械面）。

    **追加一列是每輪的正常動作，改寫既有列不是**——前綴長度固定，追加時本指紋不變
    （零維護成本）；一旦有人動到前綴內任何一列的任何欄位（改數字、改理由、把兩列合併
    成一列、把整段歷史刪掉只留一列），指紋當場不同。

    用 `repr` 而不是自訂分隔字串：理由欄本身含全形標點與換行，任何自訂分隔符都可能
    在未來某列的理由裡出現而讓兩張不同的表算出同一個指紋（本 repo 對「分隔符碰撞」
    已有判例）。`repr` 對 `tuple[str, int, int, int, str]` 是無歧義且跨版本穩定的。
    """
    return hashlib.sha256(repr(tuple(log[:prefix_len])).encode("utf-8")).hexdigest()


#: R-10（收斂波機制缺口）：`[歷史被改寫]` 只驗「指紋是否等於 `log` 現況」——資料與
#: 指紋同檔同 commit，誰能改前綴內一列就能同時重算指紋讓兩者自洽（實測：既有回歸
#: 測試同步後全綠，非零星幾支）。修法接一個**不受本檔單一 commit 控制**的外部錨點：指紋每變一次
#: 就追加一列，且該列 DEF-ID 須真的存在於缺陷帳本——協同改寫從此變成跨檔協同，比
#: 「同一份檔案自己說自己對」成本高一個量級（誠實劃界：非密碼學級不可繞過證明，
#: 帳本仍可能被另外偽造一筆，但那已是**兩個治理面**）。捨棄任務書另一案（數值／敘事
#: 指紋分離）：兩者仍同檔同 commit，未解決協同改寫，只是拆成兩句自圓其說。
_FROZEN_PREFIX_REWRITE_LEDGER: tuple[tuple[str, str, str, str], ...] = (
    ("R99", "9106b9c01f1c", "23c0e49b2c63", "DEF-101-561"),
    ("R100", "23c0e49b2c63", "423d63fddc0a", "DEF-200-042"),
    # DEF-200-208：本輪把凍結前綴延伸到涵蓋新追加的 R101 那一列本身（依既有體例 round-label-ok
    # 「追加後立即自我凍結」——見 `_REPIN_LOG_FROZEN_PREFIX_LEN` 旁註），此前既有
    # 前綴內容逐字未動，但 `prefix_len` 本身改變即讓 `repin_log_history_digest()`
    # 算出不同指紋，故仍須在此留痕（判準不分辨「延伸」與「改寫」，兩者都是指紋變動）。
    ("R101", "423d63fddc0a", "44008855c9e8", "DEF-200-208"),
    # DEF-200-204：R102 收尾重釘，同 R101 體例「追加後立即自我凍結」——本輪追加兩列 round-label-ok
    # （功能成長 +572 ＋ 本檔自身編修 +11），prefix_len 47→49 涵蓋兩列本身。
    ("R102", "44008855c9e8", "c44b6a066da8", "DEF-200-204"),
    # DEF-200-218：R102 收尾修復 push 被擋下的三項既存缺陷，同體例「追加後立即自我 round-label-ok
    # 凍結」——本輪追加一列（納管漏檔 +2 ＋ 本檔自身編修 +10），prefix_len 49→50 涵蓋該列本身。
    ("R102", "c44b6a066da8", "605806a0d4aa", "DEF-200-218"),
    # DEF-200-207：R102 收尾（四方核准並執行 --repin-cap／--update 後）訂正 round-label-ok
    # test_the_next_round_cannot_reuse_the_exemption 的合成注入前提，同體例「追加後
    # 立即自我凍結」——本輪追加多列（測試訂正＋本檔自身逐檔漂移收斂），
    # prefix_len 50→56 涵蓋全部新列本身。
    ("R102", "605806a0d4aa", "23b5b6fcc0a2", "DEF-200-207"),
    # DEF-200-219：R71 全樹掃描抓到漏帶 round-label-ok 的既存缺陷，同體例「追加後立即
    # 自我凍結」——本輪追加一列（補標＋E501拆行＋本表自身編修合計 +5），
    # prefix_len 56→57 涵蓋該列本身。
    ("R102", "23b5b6fcc0a2", "cb643af00b7a", "DEF-200-219"),
    # DEF-200-220：帳本收斂輪（archive_67）修復兩支相鄰封印值失明的既有測試， round-label-ok
    # 同體例「追加後立即自我凍結」——本輪追加兩列（crossref 檔 +4 ＋ 本檔自身編修
    # +12），prefix_len 57→59 涵蓋兩列本身。
    ("R102", "cb643af00b7a", "bc7080dcd3f2", "DEF-200-220"),
    # DEF-200-221：R102 收尾後的四方複審發現護欄層行數棘輪未隨 ArchiveGate 對 round-label-ok
    # test_check_defect_log_crossref.py 的新增測試類別同步重釘（同 CLAUDE.md 鐵律七：
    # 鎖檔持有面被切給不同並行包）；R102 已收尾交棒，本批改標 R103（不追溯改寫 round-label-ok
    # R102 既有列），同體例「追加後立即自我凍結」——本輪追加兩列（crossref 檔 round-label-ok
    # +103 ＋ 本檔自身編修 +18），prefix_len 59→61 涵蓋兩列本身。
    ("R103", "bc7080dcd3f2", "b698a52087af", "DEF-200-221"),
    # DEF-200-223：R104 PRD §4.2.5／§4.2.1 BURSTING/EWMA 落地，同體例「追加後立即  round-label-ok
    # 自我凍結」——本輪淨額 -18：測試 +62 與搬遷散文 -91 相抵後，本檔自身兩列
    # （稽核列＋本凍結前綴延伸列）+11，prefix_len 61→62 涵蓋兩列本身。
    ("R104", "b698a52087af", "967b8b322da4", "DEF-200-223"),
    # DEF-200-224：R105 淨額 34-43+9=0，prefix_len 62→63 涵蓋本列本身，逐項見 _GUARD_LINES_REPIN_LOG 同輪列。round-label-ok
    ("R105", "967b8b322da4", "cae90354814a", "DEF-200-224"),
    # DEF-200-202：四方複審 REJECT 修復（quota_gate.py 補 active_model 接線＋  round-label-ok
    # 回歸測試），同體例「追加後立即自我凍結」——本輪追加兩列（功能淨額 +49 ＋
    # 本檔自身編修 +12），prefix_len 63→65 一次涵蓋兩列本身。
    ("R105", "cae90354814a", "763624f17dde", "DEF-200-202"),
    # DEF-200-202：四方複審修復續（`_platform_helpers.py` 折長行＋  round-label-ok
    # `test_defect_id_reference_integrity.py` DEF-200-015 姊妹帳本擴面），同體例
    # 「追加後立即自我凍結」——本輪追加一列，prefix_len 65→66 涵蓋本列本身。
    ("R105", "763624f17dde", "a520bdcef8b7", "DEF-200-202"),
    # DEF-200-202：帳本狀態欄回填 fixed@R105 觸發 dirent-primitive 債表 round-label-ok
    # 微幅上升，同體例「追加後立即自我凍結」——本輪追加一列，prefix_len 66→67
    # 涵蓋本列本身。
    ("R105", "a520bdcef8b7", "a64463e662c1", "DEF-200-202"),
    ("R106", "a64463e662c1", "76bb05948f27", "DEF-101-561"),
    # DEF-101-752：R82 收斂殘餘承接站點，同體例「追加後立即自我凍結」——本輪追加一列
    # （多支 tools/tests/ 掃描面站點改為 tracked ∪ untracked-not-ignored，含本檔自身
    # 逐檔漂移，逐筆重釘過程已收斂合併為單列），prefix_len 71→72 涵蓋該列本身。
    ("R106", "76bb05948f27", "026523f64c92", "DEF-101-752"),
    # DEF-101-752 問題 3 收斂（帳本結案輪修復包重釘漏補）：8 站點永久回歸測試類別 round-label-ok
    # 落地時未重釘本表（ARCH-01 同型復發），本輪補一列（含本檔自身逐檔漂移的兩列
    # 追加），prefix_len 73→75 涵蓋全部新列本身。
    ("R106", "026523f64c92", "6d3be18839b6", "DEF-101-752"),
    # 帳本結案包 #3（DEF-200-166 窗口）：追加本輪稽核列並把它納入前綴（prefix_len 75→76）。
    ("R107", "6d3be18839b6", "b42d19e1db20", "DEF-200-166"),
    ("R107", "b42d19e1db20", "abd0dc217e2b", "DEF-200-141"),  # B2/B3 措辭與指針訂正（2026-08-28）
    # DEF-200-230 回歸鎖窗口：追加本輪稽核列並把它納入前綴（prefix_len 76→77），同體例
    # 「追加後立即自我凍結」——延伸本身即讓指紋改變，故仍須在此留痕。
    ("R108", "abd0dc217e2b", "21c85dff06f9", "DEF-200-230"),
    # DEF-200-233 修復窗口（macos-compat-ci）：追加本輪稽核列並把它納入前綴 round-label-ok
    # （prefix_len 77→78），同體例「追加後立即自我凍結」——延伸本身即讓指紋改變，故留痕。
    ("R108", "21c85dff06f9", "4e0397833463", "DEF-200-233"),
    # DEF-101-747 換載體（Gap C：表② 指紋 stale 的發現時點提前到 dev_start [6/7]）：
    # 追加本輪稽核列並把它納入前綴（prefix_len 78→79），同體例「追加後立即自我凍結」。
    ("R109", "4e0397833463", "dc62ee5d1822", "DEF-101-747"),
    # F2 修復窗口（quota 測試活體態滲入；載體＝DEF-200-232）：R109 追加本輪稽核列 round-label-ok
    # 並把它納入前綴（prefix_len 79→80），同體例「追加後立即自我凍結」。
    ("R109", "dc62ee5d1822", "42b28e14a0b8", "DEF-200-232"),
    # DEF-200-121 修復窗口（護欄層判準修補輪）：追加本輪稽核列並把它納入前綴
    # （prefix_len 80→81），同體例「追加後立即自我凍結」——延伸本身即讓指紋改變，故留痕。
    ("R111", "42b28e14a0b8", "db3448c59433", "DEF-200-121"),
    # 結構性長債分軌輪（2026-08-30）：追加本輪稽核列並依「追加後立即自我凍結」判例
    # 延伸前綴涵蓋該列本身（81→82）；Phase2 到期義務同窗記入 [提案]，載體＝該 DEF。
    ("R113", "db3448c59433", "369320d0f7f9", "DEF-200-211"),
    # v2.1.13 G1 實作批 (a)（喚醒鏈最後一哩）：追加本輪稽核列並依「追加後立即自我凍結」
    # 判例延伸前綴涵蓋該列本身（82→83）；載體＝DEF-200-231②（headless 窗口許可層）。
    ("R113", "369320d0f7f9", "7301deef344e", "DEF-200-231"),
    # v2.1.13 G2 實作批 (b)（handback 交接可見性）：追加本輪稽核列並依「追加後立即
    # 自我凍結」判例延伸前綴涵蓋該列本身（83→84）；載體＝DEF-200-236（交接可見面）。
    ("R113", "7301deef344e", "4b6d79935d12", "DEF-200-236"),
    # v2.1.13 G3+G4 實作批 (c)+(d)（接力狀態機＋哨兵自癒）：追加本輪稽核列並依「追加
    # 後立即自我凍結」判例延伸前綴涵蓋該列本身（84→85）；標號改用 R114（理由見 round-label-ok
    # `_GUARD_LINES_REPIN_LOG` 該列）；載體＝DEF-200-234（受統籌自循環，PRD §3(c)）。
    ("R114", "4b6d79935d12", "ea038ea6ff4e", "DEF-200-234"),
    # R115 收斂棒 round-label-ok（三個修復棒＋治理批累積漂移一次性合法收束）：追加本輪稽核列並依
    # 「追加後立即自我凍結」判例延伸前綴涵蓋該列本身（85→86）；載體＝DEF-200-239
    # （排程孤兒回歸鎖，本輪 test_context_budget_guard.py 內容主要新增項之一）。
    ("R115", "ea038ea6ff4e", "4e5f11565d23", "DEF-200-239"),
    ("R115", "4e5f11565d23", "0c0aa4967799", "DEF-200-239"),
    ("R115", "0c0aa4967799", "9316ce4e91ed", "DEF-200-239"),
    # ADR-XPLAT-013 Phase2 (b)(c) 分軌計價落地：追加本輪稽核列並依「追加後立即自我
    # 凍結」判例延伸前綴涵蓋該列本身（88→89）；載體＝DEF-200-211。
    ("R116", "9316ce4e91ed", "1bd8f0d4e396", "DEF-200-211"),
    # Architect 鏡一審承接補釘，同體例「追加後立即自我凍結」（prefix_len 89→90 涵蓋 round-label-ok
    # 該列本身；A-1/A-2/N-1 詳 CrossPlatform_R116_Scan_Findings.md）。
    ("R116", "1bd8f0d4e396", "a08e0c7043be", "DEF-200-211"),
    # P1-2/P1-3 批追加 R117 稽核紀錄＋分軌首次申報，同體例「追加後立即自我凍結」。round-label-ok
    ("R117", "a08e0c7043be", "d16dc6498956", "DEF-200-234"),
    # P1-4 檢查表規則鎖批追加稽核紀錄，同體例「追加後立即自我凍結」（91→92）。round-label-ok
    ("R117", "d16dc6498956", "f37361174a7f", "DEF-101-886"),
    # DEF-200-212 P1-5 收尾批：追加五列（落地＋自身編修＋三批史料搬遷）並依「追加後 round-label-ok
    # 立即自我凍結」判例延伸前綴涵蓋全部新列本身（92→97）。
    ("R118", "f37361174a7f", "862ff00ae26d", "DEF-200-212"),
    # P1-6 批：skip 天花板①②③與 M6 落款④共同變更鎖落地，追加本輪稽核紀錄（落地＋
    # 本表自身編修二列）並依「追加後立即自我凍結」判例延伸前綴涵蓋全部新列本身
    # （99→101）；載體＝DEF-200-240。
    ("R119", "862ff00ae26d", "7f11c682ae08", "DEF-200-240"),
    # P1-6 批續（round-label-ok）：全套背景跑揪出兩項真違規（R119_HANDOFF.md 零 stale
    # 宣稱、subprocess text=True 缺 encoding）修復後追加稽核列，依「追加後立即自我
    # 凍結」判例延伸前綴涵蓋本列本身（101→102）；載體＝DEF-200-240（同批延續）。
    ("R119", "7f11c682ae08", "21bdbf9b9595", "DEF-200-240"),
    # P1-6 批修復包（DEF-200-240 同批延續）：F1 共同變更鎖判準粒度由檔案級改為剖面
    # 鍵值級，F2 governance_docs.py E501 拆行，同體例「追加後立即自我凍結」——
    # 本輪追加三列（落地列＋本表自身編修二列）並延伸前綴涵蓋全部新列本身（103→107）。
    ("R119", "21bdbf9b9595", "4554dbed8bf5", "DEF-200-240"),
    # R120 收尾：212 結案批＋P1-7 SD-4/SD-8＋SA-4 的守衛線重釘使 round-label-ok
    # `_REPIN_LOG_HISTORY_SHA256` 前進，同體例「追加後立即自我凍結」——本輪追加
    # 本列＋一個 repin 稽核列，prefix_len 109→110 涵蓋新 repin 列本身。
    ("R120", "4554dbed8bf5", "dc94d1a10d4f", "DEF-200-241"),
    # 精準修復輪收尾：三筆缺陷落地＋散文搬遷抵銷的守衛線重釘使 round-label-ok
    # `_REPIN_LOG_HISTORY_SHA256` 前進，同體例「追加後立即自我凍結」——本輪追加三個
    # repin 稽核列＋本列，prefix_len 110→113 涵蓋全部新列本身。
    ("R122", "dc94d1a10d4f", "7d9eb06de5a7", "DEF-200-222"),
    # 精準修復輪第二棒收尾：三筆落地的守衛線重釘使指紋前進，同體例 round-label-ok
    # 「追加後立即自我凍結」——本棒追加一個 repin 稽核列＋本列，prefix_len 114→115。
    ("R123", "7d9eb06de5a7", "4ec1e958f341", "DEF-200-205"),
    # 落地輪收尾：結案批回歸鎖＋到期義務兌現的守衛線重釘使指紋前進，同體例 round-label-ok
    # 「追加後立即自我凍結」——本輪追加一個 repin 稽核列＋本列，prefix_len 115→116。
    ("R126", "4ec1e958f341", "faddc843e042", "DEF-200-241"),
)

#: 本機制上線當下的指紋快照（**永不隨 `_REPIN_LOG_HISTORY_SHA256` 之後的異動而動**）。
#: 往後指紋每變一次，都要能從本值出發、經 `_FROZEN_PREFIX_REWRITE_LEDGER` 逐列鏈接
#: 到當時的新值；鏈斷了就是有一次指紋變動沒有留痕。
_FROZEN_PREFIX_REWRITE_LAUNCH_SHA = (
    "9106b9c01f1c47ef9e013e5f36854d5ff950cd7a5439f2870b49d3c760a023e4")


def _def_id_exists_in_ledger(def_id: str) -> bool:
    """預設查核：`def_id` 是否出現在缺陷帳本家族全檔（主檔＋全部 archive）。"""
    return any(def_id in text for _name, text in read_family())


def frozen_prefix_rewrite_problems(
    rewrite_ledger: Sequence[tuple[str, str, str, str]],
    *, current_sha: str, launch_sha: str = _FROZEN_PREFIX_REWRITE_LAUNCH_SHA,
    def_id_exists: Callable[[str], bool] = _def_id_exists_in_ledger,
) -> list[str]:
    """凍結前綴指紋的「協同改寫」機械物（回空＝通過）。純函式，紅綠由合成注入自證。

    鏈路：`launch_sha` 是起點，`rewrite_ledger` 逐列 `(輪次, 舊指紋前12碼, 新指紋
    前12碼, DEF-ID)` 必須首尾相接，最後一列的新指紋須接上 `current_sha` 現值。
    表空且 `current_sha == launch_sha`（從未變動）視為合規。每一列的 DEF-ID 皆須
    通過 `def_id_exists()`（預設查真實缺陷帳本家族全檔，可注入偽造版做純函式測試）。
    """
    cur12, launch12 = current_sha[:12], launch_sha[:12]
    if not rewrite_ledger:
        if cur12 == launch12:
            return []
        return [f"[缺一即紅] 指紋由 {launch12} 變為 {cur12}，但 "
                "_FROZEN_PREFIX_REWRITE_LEDGER 一列都沒有——任何指紋變動都必須留痕"]
    problems: list[str] = []
    prev = launch12
    for rnd, old12, new12, def_id in rewrite_ledger:
        if old12 != prev:
            problems.append(f"[斷鏈] {rnd} 列宣稱舊指紋 {old12}，與前一環 {prev} 不符")
        if not ADL.gate._ID_RE.fullmatch(def_id):
            problems.append(f"[DEF-ID 格式不合法] {rnd} 列：{def_id!r}")
        elif not def_id_exists(def_id):
            problems.append(f"[DEF-ID 查無此列] {rnd} 列指名 {def_id}，缺陷帳本家族"
                            "全檔查無此 ID")
        prev = new12
    if prev != cur12:
        problems.append(f"[未接上現值] 帳本鏈路終點指紋 {prev} 不等於現值 {cur12}——"
                        "現值變了卻沒有對應的最後一列，或最後一列的新指紋抄錯")
    return problems


def repin_round_nets(
    log: Sequence[tuple[str, int, int, int, str]]
) -> list[tuple[int, int]]:
    """`[(輪號, 該輪淨額合計)]`，順序保留、**同輪連續多列合併**。

    為何以「輪」而不是以「列」為單位（這一點決定判準有沒有牙）：一輪可以有多次重釘
    （實測 R79 六列、R81 五列、R82 三列），逐列判上限等於「拆成兩次就過了」，
    而拆列的成本是零。輪號無法解析的列（合成注入用的 `Rx`／`Ry`）刻意跳過——
    它們是純函式測試的語料，不是真實輪次。
    """
    out: list[tuple[int, int]] = []
    for rnd, _old, _new, delta, _reason in log:
        if not (rnd[:1] == "R" and rnd[1:].isdigit()):
            continue
        no = int(rnd[1:])
        if out and out[-1][0] == no:
            out[-1] = (no, out[-1][1] + delta)
        else:
            out.append((no, delta))
    return out


def repin_growth_problems(
    log: Sequence[tuple[str, int, int, int, str]],
    *,
    since: int = _REPIN_ROUND_CAP_SINCE,
    net_cap: int | None = None,
    max_consecutive_rising: int = _REPIN_MAX_CONSECUTIVE_RISING_ROUNDS,
    approved_overage: Mapping[str, tuple[int, str]] | None = None,
    regression_lane: Sequence[tuple[str, int, str]] | None = None,
    regression_lane_since: int = _REGRESSION_LANE_SINCE,
) -> list[str]:
    """R84 ARCH-01：重釘的**代價**（空＝通過）。純函式，紅綠由合成注入自證。

    🔴 ADR-XPLAT-013 Phase2 (b)（D-1＝S-2）：`regression_lane` 不傳或傳空 ⇒ 行為與分軌前
    **逐字相同**（`test_the_split_does_not_widen_the_functional_lane` 的機械面）——這是
    刻意的向後相容設計，不是巧合。傳入時，款(10)(11) 判的淨額改為「該輪主表淨額 −
    該輪回歸鎖軌淨額」，但只對 `no >= regression_lane_since` 的輪次生效：
    `regression_lane_since` 之前的輪次即使回歸鎖軌表宣告了淨額也**不會被扣**——這是
    「(b) 不得用自己剛落地的減免軌豁免自己」（§1.6.3 第 3 題）的機械面：落地輪本身
    永遠落在 SINCE 之前，把落地輪自己的淨額謊報成回歸鎖軌也救不了它。

    兩款，各帶方括號標籤（本檔的零串音紀律）：
      (10) `[超出每輪上限]` 某一輪的淨額合計 > **該輪當時在位的**上限
           （`net_cap_for_round()`；`net_cap` 顯式傳入時改為對所有輪套用同一個值，
           那是注入測試用的，見 `_REPIN_NET_CAP_SCHEDULE` 的 WHY：下修不追溯）。
      (11) `[只升不降]` 連續 `max_consecutive_rising + 1` 輪淨額為正 —— **本款是主牙**：
           它把「淨行數只准往下」這句從 R77 起就寫在檔頭、卻每一列都在上升的話，
           變成一件會擋下 push 的事。合法出口只有一個：讓某一輪的淨額 ≤ 0
           （刪行／合併鎖檔／把散文搬進帳本），連續計數當場歸零。
    款(12) `[到期未下修]`（`net_cap` 自己的到期義務）刻意**不住在這裡**，住在
    `repin_cost_ratchet_problems()`：它判的是「常數該不該被下修了」，與傳進來的那張表
    無關——放在本函式會讓每一份輪號較大的**合成語料**都跟著鳴叫
    （實測：R99 的追加對照組  round-label-ok
    當場轉紅），而那是串音，不是鑑別力。

    只判輪號 ≥ `since` 的輪次（不追溯，WHY 見常數區塊）；`since` 本身只准調小，看著它的是
    `repin_cost_ratchet_problems()`。四個參數刻意可傳，供注入測試用小值造出紅綠兩側。

    🔴 DEF-200-208：`approved_overage`（預設 `_REPIN_APPROVED_ROUND_OVERAGE`）是**指名
    輪號 ＋ 精確淨額**的一次性例外名冊——凡「輪號」與「該輪淨額」逐字對得上冊上那一列，
    該輪的款(10)(11) 一律不計入回傳，其餘輪次（含未來任何一輪、含日後合成測試恰好用到
    同一個輪號但淨額不同的樣本）原判準邏輯不受影響。「連淨額都要對上」不是畫蛇添足：
    `test_a_round_that_exceeds_the_net_cap_is_red` 會拿 `_REPIN_NET_CAP_SCHEDULE[-1]`
    的輪號造合成樣本，而那個輪號在到期義務兌現時**恰好**就是本例外核准的那個輪號
    （R101）——若 key 只認輪號不認淨額，那支測試的紅燈會被本表意外熄滅。這與調高 round-label-ok
    `net_cap`／`max_consecutive_rising` 有本質差異：後者放寬的是**所有輪次往後永遠
    適用**的門檻，前者只赦免**指名的那一個精確事件**，且赦免與否寫在名冊裡、可被
    單獨稽核（`TestApprovedRoundOverageIsScoped`）。

    誠實劃界：本判準看的是**表上宣告的淨額**，不是磁碟——成長挪到 `tools/tests/` 以外的樹
    時本款不會說話，那是量測面邊界（`_GUARD_DIR_REL`／`_GUARD_LINE_PATTERN`），不是漏洞。
    """
    approved = _REPIN_APPROVED_ROUND_OVERAGE if approved_overage is None else approved_overage
    problems: list[str] = []
    nets = [(no, delta) for no, delta in repin_round_nets(log) if no >= since]
    if regression_lane:
        lane_nets = {no: d for no, d in regression_lane_round_nets(regression_lane)
                     if no >= regression_lane_since}
        nets = [(no, delta - lane_nets.get(no, 0)) for no, delta in nets]

    def _overridden(no: int, delta: int) -> bool:
        entry = approved.get(f"R{no}")
        if entry is None:
            return False
        expected_delta, reason = entry
        return (delta == expected_delta
                and len(reason.strip()) >= _REPIN_APPROVED_ROUND_OVERAGE_MIN_REASON_LEN)

    for no, delta in nets:
        cap_here = net_cap_for_round(no) if net_cap is None else net_cap
        if delta > cap_here and not _overridden(no, delta):
            problems.append(
                f"[超出每輪上限] R{no} 的重釘淨額合計 +{delta} 超過該輪上限 {cap_here}"
                "——該上限是歷來單輪最大淨額的實測值、且只准下修"
                f"（`repin_cost_ratchet_problems()` 看著）。出口不是調高它："
                "同一輪內把等量以上的行刪掉／合併鎖檔／把史料搬進帳本，"
                "或把這一輪的成長拆給下一輪（拆輪次不是拆列，同輪多列會被合併計算），"
                "或走 DEF-200-208 的一次性例外名冊（`_REPIN_APPROVED_ROUND_OVERAGE`，"
                "須具名理由且經四方複審核准，不得自行加註）")
    run: list[int] = []
    worst: list[int] = []
    for no, delta in nets:
        if delta > 0 and not _overridden(no, delta):
            run.append(no)
            if len(run) > len(worst):
                worst = list(run)
        else:
            run = []
    if len(worst) > max_consecutive_rising:
        problems.append(
            f"[只升不降] 連續 {len(worst)} 輪的重釘淨額都是正的"
            f"（R{'／R'.join(str(n) for n in worst)}），上限是 {max_consecutive_rising} 輪"
            "——這正是 R84 ARCH-01 的缺陷本體：本表自稱「淨行數只准往下」，"
            "而立案當時表上每一列都是上升、零列下降（R77→R83 共 +24,895／+46%），"
            "重釘的唯一成本是「補一列紀錄」。合法出口只有一個：讓某一輪的淨額 ≤ 0"
            "（刪行／合併鎖檔／把 WHY 與史料搬進 `docs/06_quality/AutoSDD_Defect_Log.md`），"
            "連續計數即歸零。**不要調高這兩個常數**——它們只准下修，"
            "而放寬會讓成熟度 M1（總量連續三輪不上升）永遠只是一句話")
    return problems


def repin_cost_ratchet_problems(
    current_cap: int | None = None,
    current_run: int | None = None,
    current_since: int | None = None,
    *,
    frozen_cap: int | None = None,
    frozen_run: int | None = None,
    frozen_since: int | None = None,
    latest_round: int | None = None,
    due_round: int = _REPIN_NET_CAP_DUE_ROUND,
    due_target: int = _REPIN_NET_CAP_DUE_TARGET,
    due_lookahead: int = _REPIN_DUE_ROUND_MAX_LOOKAHEAD,
    frozen_lookahead: int = _FROZEN_REPIN_DUE_ROUND_MAX_LOOKAHEAD,
) -> list[str]:
    """R84 ARCH-01 的**後設鎖**：三個代價常數只准往「更嚴」的方向改（空＝通過）。

    `SINCE` 只准調小（更早生效＝涵蓋更多輪＝更嚴，它調的是分母）；款(12)
    `[到期未下修]` 也住這裡（判「尺自己該不該被下修」，放進 `repin_growth_problems()`
    會對輪號較大的合成語料串音）。形狀刻意照 `frozen_ratchet_problems()`：基準是簽入
    本檔的字面常數，比較在任何時點都非退化（若改用 git 導出基準，commit 一落地基準就
    等於現值）。殘餘面（同 `_FROZEN_MAX_BASELINE_ENTRIES` 那一組）：同一 commit 內同時
    改門檻與基準仍可通過，調升在 diff 上是兩個一起變大的數字，方向一望即知。
    立案沿革（F3/B-1 注入實測、Guard_Repin 證據檔 §B-7）搬至
    CrossPlatform_R97_Scan_Findings.md〈代價常數後設鎖 WHY〉節。
    """
    cap = _REPIN_ROUND_NET_CAP if current_cap is None else current_cap
    run = (_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS
           if current_run is None else current_run)
    base_cap = _FROZEN_REPIN_ROUND_NET_CAP if frozen_cap is None else frozen_cap
    base_run = (_FROZEN_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS
                if frozen_run is None else frozen_run)
    since = _REPIN_ROUND_CAP_SINCE if current_since is None else current_since
    base_since = (_FROZEN_REPIN_ROUND_CAP_SINCE
                  if frozen_since is None else frozen_since)
    problems: list[str] = []
    problems += net_cap_schedule_problems()
    if since > base_since:
        problems.append(
            f"_REPIN_ROUND_CAP_SINCE 由 R{base_since} 推遲為 R{since}——本常數只准調小"
            "（更早生效＝涵蓋更多輪＝判準更嚴）。它不是門檻而是**分母**：把生效點推到"
            "未來，款(10)(11) 就沒有任何一列可判，等於一行 diff 關掉整段代價機制"
            "（F3／B-1 注入實測：改成 R99 之後那四支測試仍全數通過）")
    live_round = (max((no for no, _d in repin_round_nets(_GUARD_LINES_REPIN_LOG)),
                      default=0) if latest_round is None else latest_round)
    if live_round >= due_round and cap > due_target:
        problems.append(
            f"[到期未下修] 稽核痕跡已經走到 R{live_round}（到期輪＝R{due_round}），"
            f"而現行上限仍是 {cap}、高於到期目標 {due_target}——款(10) 問「這一輪長太多了"
            "嗎」，本款問「**那把尺自己是不是還停在當初取的最寬值**」（逐輪淨額現查 "
            "`repin_round_nets(_GUARD_LINES_REPIN_LOG)`，本訊息刻意不複寫那張表：前一輪抄了"
            "一份，抄完當輪就被自己的第二次重釘證偽）。出口只有一個且永遠開著："
            f"往 _REPIN_NET_CAP_SCHEDULE 追加一列 (R<本輪>, ≤{due_target})"
            "（分段生效⇒下修不追溯，不會把已收輪次回頭判紅；後設鎖只擋調升）。"
            "刻意沒有「延期」參數——可延期的到期日不是到期日")
    # DEF-200-121：款(12) 的 `live_round >= due_round` 對「到期輪自己被推遲」全盲——
    # 改 9999 即永假（帳本注入實測紅 0），於是上一句「刻意沒有延期參數」只是散文。
    if due_round > live_round + due_lookahead:
        problems.append(
            f"[到期日被推遲] 到期輪 R{due_round} 距最近稽核輪 R{live_round} 超過 "
            f"{due_lookahead} 輪——可延期的到期日不是到期日（DEF-200-121：把到期輪改成"
            "遠未來，款(12) 的比較式永假、靜默熄滅）。出口＝先兌現現行到期義務再重新"
            f"武裝下一段，且新到期輪只能落在「兌現輪＋{due_lookahead}」以內"
            "（歷史母體：85 起每一段到期輪一律＝上一次兌現輪 +2）")
    if due_lookahead > frozen_lookahead:
        problems.append(
            f"_REPIN_DUE_ROUND_MAX_LOOKAHEAD 由 {frozen_lookahead} 調升為 {due_lookahead}"
            "——本常數只准下修（同 `_REPIN_ROUND_CAP_SINCE` 款式）：調大它＝把"
            "「不可延期」改寫成「可以晚一點」，款(12) 的到期語意跟著蒸發")
    if cap > base_cap:
        problems.append(
            f"_REPIN_ROUND_NET_CAP 由 {base_cap} 調升為 {cap}——本常數只准往下改。"
            "調高它就是把「重釘要付代價」這件事本身取消掉（R84 ARCH-01）")
    if run > base_run:
        problems.append(
            f"_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS 由 {base_run} 調升為 {run}"
            "——本常數只准往下改。它是成熟度 M1「連續三輪不上升」的機械面，"
            "放寬等於把 M1 的達標條件改寫成一句永遠成立的話")
    return problems


def regression_lane_round_nets(
    log: Sequence[tuple[str, int, str]]
) -> list[tuple[int, int]]:
    """`_REGRESSION_LANE_LOG` 版的 `repin_round_nets()`——三欄表（無 old/new 鏈，只有淨額），
    同輪連續多列合併，輪號無法解析的列（合成語料）跳過。理由同 `repin_round_nets()`。
    """
    out: list[tuple[int, int]] = []
    for rnd, delta, _reason in log:
        if not (rnd[:1] == "R" and rnd[1:].isdigit()):
            continue
        no = int(rnd[1:])
        if out and out[-1][0] == no:
            out[-1] = (no, out[-1][1] + delta)
        else:
            out.append((no, delta))
    return out


def lane_split_problems(
    main_log: Sequence[tuple[str, int, int, int, str]] | None = None,
    lane_log: Sequence[tuple[str, int, str]] | None = None,
    *,
    since: int = _REGRESSION_LANE_SINCE,
    frozen_since: int = _FROZEN_REGRESSION_LANE_SINCE,
    cap: int = _REGRESSION_LANE_ROUND_CAP,
    frozen_cap: int = _FROZEN_REGRESSION_LANE_ROUND_CAP,
    approved_overage: Mapping[str, tuple[int, str]] | None = None,
    latest_round: int | None = None,
) -> list[str]:
    """(b) D-1(S-2) 分軌申報守衛（空＝通過）。純函式，紅綠合成注入自證（提案 §5.1）。

    六款（標籤唯一、零串音；規格 SSOT＝提案 §5.1 的表，本處只留標籤與一句話，詳述
    不重抄——第 6 款是 §1.6.3 第 3 題的機械面，§5.1 沒單獨編號故延伸標號）：
      1. `[空表]` 生效輪後主表有非零淨額而軌表整張不存在（生效輪前表空合規）。
      2. `[軌別未申報]` 主表淨額 > 0 而軌表無列、理由欄也無全額功能軌標記（§1.5）。
      3. `[子項大於母項]` 軌淨額 > 同輪主表淨額；僅判母項 > 0（母項負＝淨減法輪，
         子集上界語意失效，套利面由款 4 承接——SD-1）。
      4. `[回歸鎖軌超上限]` 軌淨額 > `cap` 且不在具名核准名冊。
      5. `[減免軌被追溯]`／`[上限被放寬]` 方向鎖：`since` 只准大、`cap` 只准小。
      6. `[生效前宣告]` 軌表宣告 `since` 前輪次——不追溯，封死落地輪自我豁免
         （`repin_growth_problems()` 減法側同步過濾，本款是申報面回聲）。

    誠實劃界：只看表上宣告淨額，不驗分類本身（C1~C4 分類器未落地，提案 §4 item 2）。
    """
    main = _GUARD_LINES_REPIN_LOG if main_log is None else main_log
    lane = _REGRESSION_LANE_LOG if lane_log is None else lane_log
    approved = (_REGRESSION_LANE_APPROVED_OVERAGE if approved_overage is None
                else approved_overage)
    problems: list[str] = []

    if since < frozen_since:
        problems.append(
            f"[減免軌被追溯] _REGRESSION_LANE_SINCE 由 R{frozen_since} 調小為 R{since}"
            "——只准調大：調小＝把減免向更早輪次追溯延伸，等於追溯放寬")
    if cap > frozen_cap:
        problems.append(
            f"[上限被放寬] _REGRESSION_LANE_ROUND_CAP 由 {frozen_cap} 調升為 {cap}"
            "——只准往下改（同 `_REPIN_ROUND_NET_CAP` 款式）")

    live = live_repin_round(main) if latest_round is None else latest_round
    main_nets = dict(repin_round_nets(main))
    lane_nets = dict(regression_lane_round_nets(lane))

    for no in lane_nets:
        if no < since:
            problems.append(
                f"[生效前宣告] 回歸鎖軌表對 R{no} 有宣告，但生效輪是 R{since}——本軌"
                "刻意不追溯（落地輪不得用自己剛開的減免軌豁免自己，見 "
                "ADR-XPLAT-013_Phase2_Proposal_R108.md §1.6.3 第 3 題）。"
                f"R{since} 之前的輪次一律全額算進功能軌，不接受任何回歸鎖軌宣告")

    if not lane:
        if live >= since and any(no >= since and d != 0 for no, d in main_nets.items()):
            problems.append(
                f"[空表] _REGRESSION_LANE_LOG 一列都沒有，而稽核痕跡已走到 R{live}"
                f"（生效輪 R{since}）——本輪之後只要主表淨額非零就必須申報屬於哪一軌"
                "（見 `[軌別未申報]`）。整張表都不存在，是比漏報單一輪更粗的 fail-open")
        return problems

    for no, delta in main_nets.items():
        if no < since or delta <= 0:
            continue
        if no in lane_nets:
            continue
        reasons = [r for rnd, _o, _n, _d, r in main if rnd == f"R{no}"]
        if any(_LANE_FULL_FUNCTIONAL_TOKEN in r for r in reasons):
            continue
        problems.append(
            f"[軌別未申報] R{no} 主表淨額 +{delta}，回歸鎖軌表無對應列，理由欄也沒有 "
            f"`{_LANE_FULL_FUNCTIONAL_TOKEN}` 標記——申報是強制的，不是選填：要嘛在 "
            "_REGRESSION_LANE_LOG 補一列（哪怕淨額 0），要嘛在主表理由欄寫明"
            f"`{_LANE_FULL_FUNCTIONAL_TOKEN}`")

    for no, lane_delta in lane_nets.items():
        if no < since:
            continue
        main_delta = main_nets.get(no, 0)
        if main_delta > 0 and lane_delta > main_delta:
            problems.append(
                f"[子項大於母項] R{no} 回歸鎖軌淨額 {lane_delta:+d} 大於同輪主表淨額 "
                f"{main_delta:+d}——回歸鎖軌是主表的子集，不能比母項還大")

    for no, lane_delta in lane_nets.items():
        if no < since:
            continue
        entry = approved.get(f"R{no}")
        overridden = (entry is not None and lane_delta == entry[0]
                      and len(entry[1].strip())
                      >= _REGRESSION_LANE_APPROVED_OVERAGE_MIN_REASON_LEN)
        if lane_delta > cap and not overridden:
            problems.append(
                f"[回歸鎖軌超上限] R{no} 回歸鎖軌淨額 +{lane_delta} 超過上限 {cap}——"
                "出口：同輪把等量以上的行刪掉／合併鎖檔，或走 "
                "_REGRESSION_LANE_APPROVED_OVERAGE 的一次性例外名冊（須具名理由且經"
                "四方複審核准）")

    return problems


def repin_log_problems(
    log: Sequence[tuple[str, int, int, int, str]],
    frozen_total: int,
    *,
    history_digest: str | None = None,
    prefix_len: int = 0,
    max_unfrozen_tail: int | None = None,
    cost_since: int = _REPIN_ROUND_CAP_SINCE,
    net_cap: int | None = None,
    max_consecutive_rising: int = _REPIN_MAX_CONSECUTIVE_RISING_ROUNDS,
    regression_lane: Sequence[tuple[str, int, str]] | None = None,
) -> list[str]:
    """重釘稽核痕跡的違規清單（空＝通過）。純函式，紅綠由合成注入自證。

    七款，各帶方括號標籤（本檔的零串音紀律）：
      (1) `[空表]` 一列都沒有 —— 整張表被刪掉時，下面幾條全部無事可判＝fail-open。
      (2) `[淨額不符]` 某列的 `新總量 - 舊總量 != 淨額` —— 手抄淨額算錯。
      (3) `[斷鏈]` 某列的舊總量 != 前一列的新總量 —— 中間漏記了一次重釘。
      (4) `[未對帳]` 表尾的新總量 != `sum(_FROZEN_GUARD_LINES.values())` —— **本判準的主牙**：
          改了凍結表卻沒補一列理由（或補了列卻沒真的改表）。
      (5) `[無理由]` 理由欄過短 —— 「重釘」三個字不算理由；淨額要有人負責解釋。
      (6) `[歷史變短]` 列數少於凍結前綴長度 —— 把兩列合併成一列、或整段砍掉。
      (7) `[歷史被改寫]` 前綴指紋不符 —— 前綴內既有列的任何欄位被動過。
      (8) `[前綴過期]` 未受指紋保護的尾端列數超過寬限 —— 追加了新列卻一直不把前一列
          納入前綴，久了整段尾巴又回到「可自由改寫」的狀態。
      (9) `[未附刪除清單]` 淨額為正、卻沒有量化刪除交代／沒有明文承認不是淨減法輪／
          沒有指名逐檔清單住哪 —— **本款把「調高基線要附刪除清單」由訊息文字升為判準**。
      (10)(11) `[超出每輪上限]`／`[只升不降]` —— R84 ARCH-01，實作在
          `repin_growth_problems()`（那裡有完整立案量測與形狀取捨）。款(9) 強制的是
          **承認**，不是不准成長；這兩款是第一次讓「不准無限成長」有機械面。

    (6)(7) 是 R79 收斂包補的，治的是這張表自己的假話（append-only 零機械強制、壓平歷史
    rc=0，立案沿革搬至 CrossPlatform_R97_Scan_Findings.md〈稽核痕跡假話治理 WHY〉節）。
    兩個 digest 參數刻意可傳（不讀模組常數），供注入測試用合成表指紋當基準。

    誠實劃界：本判準保證「有一列、算術自洽、與凍結表對得上、既有列沒被動過」，
    **不保證那個理由是好理由**（那是人審責任）。
    """
    problems: list[str] = []
    if not log:
        return ["[空表] _GUARD_LINES_REPIN_LOG 一列都沒有——重釘的淨額又回到「不出現在任何"
                "地方」的狀態（R78 ARCH-01 的缺陷本體）。至少要有一列起點列。"]
    if len(log) < prefix_len:
        problems.append(
            f"[歷史變短] 稽核痕跡只剩 {len(log)} 列，少於凍結前綴長度 {prefix_len}——"
            "既有列只准被**追加**，不准被合併或刪除。檔頭逐字寫著 append-only，"
            "而 R79 實測那句話在此之前零機械強制（整段壓成一列仍 rc=0）。"
            "真的要縮短（例如把史前列搬進 ADR）時，請同時下修 _REPIN_LOG_FROZEN_PREFIX_LEN "
            "並在交件回報寫出搬去哪裡")
    elif history_digest is not None:
        live = repin_log_history_digest(log, prefix_len)
        if live != history_digest:
            problems.append(
                f"[歷史被改寫] 稽核痕跡前 {prefix_len} 列的指紋 {live[:12]} 不等於釘住的 "
                f"{history_digest[:12]}——凍結前綴內某一列的內容被動過"
                "（改數字／改理由／把兩列合併成一列）。正常的追加不會碰到前綴。"
                "草稿：python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines")
    if max_unfrozen_tail is not None and len(log) - prefix_len > max_unfrozen_tail:
        problems.append(
            f"[前綴過期] 有 {len(log) - prefix_len} 列在凍結前綴之外（寬限 "
            f"{max_unfrozen_tail}）——那幾列今天可以被自由改寫。追加新列時請把前一列"
            f"納入前綴：_REPIN_LOG_FROZEN_PREFIX_LEN 調成 {len(log) - max_unfrozen_tail}"
            " 並重釘 _REPIN_LOG_HISTORY_SHA256（`--print-guard-lines` 會印草稿）")
    for i, (rnd, old, new, delta, reason) in enumerate(log):
        if new - old != delta:
            problems.append(
                f"[淨額不符] {rnd} 那一列：{old}→{new} 的淨額應為 {new - old}，表上寫 {delta}")
        if i and old != log[i - 1][2]:
            problems.append(
                f"[斷鏈] {rnd} 那一列的舊總量 {old} 不等於前一列（{log[i - 1][0]}）的新總量 "
                f"{log[i - 1][2]} —— 中間有一次重釘沒有留下痕跡")
        if len(reason.strip()) < 20:
            problems.append(
                f"[無理由] {rnd} 那一列的理由欄只有 {len(reason.strip())} 字——"
                "淨額要有人負責解釋，「重釘」兩個字不是理由")
        if delta > 0 and rnd[1:].isdigit() and int(rnd[1:]) >= _NET_DELTA_ACCOUNTING_SINCE:
            claim = _DELETION_CLAIM_RE.search(reason)
            deleted_enough = claim is not None and int(claim.group(1)) >= delta
            if not (deleted_enough or _NOT_NET_SUBTRACTION_TOKEN in reason) \
                    or not _PER_FILE_LIST_RE.search(reason):
                problems.append(
                    f"[未附刪除清單] {rnd} 那一列淨額 +{delta}：理由欄必須①有量化的刪除交代"
                    f"（`刪 N 行`，且 N ≥ {delta}）或明文標記 `{_NOT_NET_SUBTRACTION_TOKEN}`，"
                    "**且**②指名一份 `CrossPlatform_R<輪號>_*.md` 當逐檔清單的家。"
                    "在 R80 之前這件事只是印在 glc_growth_problem() 失敗訊息裡的建議——"
                    "訊息沒有牙，於是同一輪內可以反覆自助放行（掃描 S5-02：收費站不是棘輪）")
    problems.extend(repin_growth_problems(
        log, since=cost_since, net_cap=net_cap,
        max_consecutive_rising=max_consecutive_rising,
        regression_lane=regression_lane))
    if log[-1][2] != frozen_total:
        problems.append(
            f"[未對帳] 稽核痕跡表尾的新總量 {log[-1][2]} 不等於 _FROZEN_GUARD_LINES 實際總量 "
            f"{frozen_total}——改了凍結表就必須同一次變更補一列 "
            f"(輪號, {log[-1][2]}, {frozen_total}, {frozen_total - log[-1][2]}, '理由')；"
            "少了這條，整張表同時變而淨額不出現在任何地方（R78 ARCH-01）。"
            "草稿：python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines")
    return problems


def doc_guard_total_problems(
    docs: Mapping[str, str],
    frozen_total: int,
    latest_round: str,
    *,
    min_sites: int = _GUARD_TOTAL_DOC_MIN_SITES,
) -> list[str]:
    """文件側引用的護欄層**累積總量**對帳（空＝通過）。純函式，紅綠由注入自證。

    四款，形狀照款(4)`[未對帳]`（那一款守的是稽核痕跡 ↔ 凍結表，本款守的是
    **人讀的那個數字** ↔ 凍結表）：
      (1) `[未登記]` 帶本輪標記的**相異檔數**少於 `min_sites` —— 沒有站點就沒有東西可判，
          而「把那一行刪掉」正是最省力的滿足方式（同款(1)`[空表]` 的理由）。
          🔴 DEF-200-166：數行數時同檔兩行即滿足（R87／R89~R96 九輪實況），刪那一份檔
          就關掉判準 ⇒ 改數相異檔（同檔重複標記不重複計）。
      (2) `[形態不符]` 標記行上讀不出 `<起點> → <總量>（+<淨額>` 三元組。
      (3) `[總量不符]` 標記行引用的總量 != `sum(_FROZEN_GUARD_LINES.values())`。
      (4) `[淨額不符]` 該行自己的算術不自洽（終點 − 起點 != 行上宣告的淨額）。

    立案（R80 二審 NEW-SA2-01＝QA2-N2）、為何靠「帶輪號的標記」而不掃全部箭頭、誠實劃界
    （保證「標出來的那行算術自洽」不保證「漏標」）與 R84 F3/B-2（漏標半改由款(5) 接手）
    全文搬至 CrossPlatform_R97_Scan_Findings.md〈文件總量對帳判準 WHY〉節。
    """
    problems: list[str] = []
    sites: set[str] = set()
    for rel in sorted(docs):
        for lineno, line in enumerate(docs[rel].splitlines(), 1):
            mark = _GUARD_TOTAL_MARK_RE.search(line)
            if mark is None or mark.group(1) != latest_round:
                continue
            sites.add(rel)
            triple = _GUARD_TOTAL_TRIPLE_RE.search(line)
            if triple is None:
                problems.append(
                    f"[形態不符] {rel}:{lineno} 帶著 {_GUARD_TOTAL_DOC_MARK}{latest_round} "
                    "標記，卻讀不出「<起點> → <總量>（+<淨額>」三元組——這個標記的意思就是"
                    "「本行引用的是現行累積總量」，讀不出來就無從對帳（等同沒有標）")
                continue
            start, total, delta = guard_total_triple(triple)
            if total != frozen_total:
                problems.append(
                    f"[總量不符] {rel}:{lineno} 引用的護欄層總量 {total} 不等於 "
                    f"_FROZEN_GUARD_LINES 實際總量 {frozen_total}——重釘之後文件沒跟上。"
                    "草稿：python tools/tests/test_adr_xplat001_c1c2_lock.py "
                    "--print-guard-lines")
            if total - start != delta:
                problems.append(
                    f"[淨額不符] {rel}:{lineno} 的 {start} → {total} 淨額應為 "
                    f"{total - start}，行上寫 {delta}——三個數字擺在同一行卻對不起來，"
                    "正是 R80 二審抓到的那個形態（兩次重釘相加算錯）")
    if len(sites) < min_sites:
        problems.append(
            f"[未登記] 帶 `{_GUARD_TOTAL_DOC_MARK}{latest_round}` 標記的**相異檔**只有 "
            f"{len(sites)} 份（{sorted(sites) or '無'}），少於 {min_sites} —— 本輪的累積"
            f"淨額必須在**兩份不同的檔**都寫得出來；同一份檔內寫兩行不算兩站點"
            f"（DEF-200-166：刪那一份檔即關掉本判準）。"
            f"掃描面：{'、'.join(_GUARD_TOTAL_DOC_GLOBS)}")
    return problems


def handoff_guard_total_problems(
    docs: Mapping[str, str],
    log: Sequence[tuple[str, int, int, int, str]],
    *,
    since: int = _HANDOFF_RECONCILE_SINCE,
) -> list[str]:
    """款(5) `[交棒書未對帳]`：交棒書的護欄層三元組 ↔ 稽核痕跡（空＝通過）。純函式。

    為何不沿用標記機制（標記要人記得寫，而「沒寫」正是失效形態本身）、改用檔名輪號當錨、
    為何不是「掃到三元組就對帳」（假紅來源與駁回理由）、假紅存量實測與誠實劃界（漏標／
    ADR 不在射程）全文搬至 CrossPlatform_R97_Scan_Findings.md〈交棒書對帳判準 WHY〉節
    （立案＝R84 F3/B-2，Guard_Repin 證據檔 §B-9）。
    """
    agg: dict[int, tuple[int, int, int]] = {}
    for rnd, old, new, delta, _reason in log:
        if not (rnd[:1] == "R" and rnd[1:].isdigit()):
            continue
        no = int(rnd[1:])
        agg[no] = ((agg[no][0], new, agg[no][2] + delta) if no in agg
                   else (old, new, delta))
    problems: list[str] = []
    for rel in sorted(docs):
        mo = _HANDOFF_ROUND_RE.search(rel)
        if mo is None or int(mo.group(1)) < since:
            continue
        want = agg.get(int(mo.group(1)))
        if want is None:
            continue
        found = [guard_total_triple(t)
                 for t in _GUARD_TOTAL_TRIPLE_RE.finditer(docs[rel])]
        if want in found:
            continue
        problems.append(
            f"[交棒書未對帳] {rel} 讀不到本輪護欄層三元組 "
            f"{want[0]} → {want[1]}（{want[2]:+d}）——那是稽核痕跡替 R{mo.group(1)} 算出來的"
            f"合計（同輪多列已合併）。實得三元組：{found or '一組都沒有'}。"
            "交棒書是呈給掌舵者的那個數字，而在本款之前它是全庫唯一「寫在活文件上、"
            "沒有任何東西看得到」的護欄層宣稱（F3／B-2 立案：改成全錯值仍 rc=0）。"
            "修法：重釘之後把交棒書那一行同步成上面的三個數字"
            "（草稿：python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines）")
    return problems


def guard_total_docs_in_worktree() -> dict[str, str]:
    """文件側對帳的掃描面現查：`{repo 相對路徑: 全文}`。

    刻意用 glob 而不是寫死輪號檔名：寫死的那一刻它就綁在 R80 上，而輪號每輪會變——
    本 repo 對「把當下機器的偶然事實寫成常數」已有多次判例。掃不到檔時回空 dict，
    由 `[未登記]` 那一款 fail-loud（不是靜默放行）。
    """
    return {
        p.relative_to(_REPO).as_posix(): p.read_text(encoding="utf-8-sig")
        for pattern in _GUARD_TOTAL_DOC_GLOBS
        for p in sorted(_REPO.glob(pattern))
    }


def guard_baseline_gaps() -> list[str]:
    """檔數面有、行數面看不到的鎖檔（正常為空清單）——兩個掃描面的**涵蓋關係**證明。

    本函式算的是「閘門會跑、但行數棘輪量不到的檔」（檔數面遞迴 `test_*.py` vs 行數面
    非遞迴 `*.py` 兩面之間的涵蓋關係），與 `guard_surface_escapes()`（問「子目錄裡有沒有
    .py」）分工不同、刻意不併成一個判準。R78 ARCH-04 立案沿革搬至
    CrossPlatform_R97_Scan_Findings.md〈涵蓋關係判準 WHY〉節。
    """
    line_face = set(guard_lines_in_worktree())
    return sorted(
        rel for rel in guard_files_in_worktree()
        if rel.rsplit("/", 1)[-1] not in line_face
    )


def guard_lines_in_worktree() -> dict[str, int]:
    """`tools/tests/*.py` 的 {檔名: 行數}（非遞迴、含未追蹤檔）。

    兩個刻意的選擇，與 `guard_files_in_worktree()` 同一組理由：
      · **含未追蹤檔**：行一落到磁碟上就該被算進去，不必等 commit。
      · **檔名當鍵**：非遞迴面上檔名唯一；子目錄逃逸另由 `guard_surface_escapes()`
        fail-loud，不靠鍵的形態去兼職偵測那件事。
    """
    root = _REPO / _GUARD_DIR_REL
    return {
        p.name: len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        for p in sorted(root.glob(_GUARD_LINE_PATTERN))
    }


def guard_surface_escapes() -> list[str]:
    """落在子目錄、因而逃出非遞迴行數面的 `.py`（正常為空清單）。

    WHY：行數面刻意非遞迴（要與 ADR §4.3 的指令逐字相同），代價是「新增子目錄裡的檔」
    對它隱形——`sync_onboarding_baselines._FINGERPRINT_TREES` 實測過這種漏法。這裡把
    那個代價變成**會轉紅的事件**而不是靜默盲區。
    """
    root = _REPO / _GUARD_DIR_REL
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*.py")
        if p.parent != root and not _CACHE_DIR_NAMES & set(p.parts)
    )


def glc_growth_problem(frozen_total: int, current_total: int) -> str | None:
    """護欄層總行數的成長判準——**單一實作，兩個消費者**（本層棘輪與 Scan-H 判準）。

    `None`＝未成長。刻意不做「成長多少以內免談」的緩衝：那個數字沒有任何實測依據，
    而它一旦存在，下一輪的增量就會剛好長到緩衝的上緣（本 repo 對下限型判準的既有判例）。
    """
    if current_total <= frozen_total:
        return None
    delta = current_total - frozen_total
    return (
        f"[成長] 護欄層行數由 {frozen_total} 增為 {current_total}（+{delta}）——"
        "DEF-101-561③ 的語意本輪由「檔數」升級為「行數」：擴充既有鎖檔一樣要付代價。"
        "合法出口＝同一次變更內把等量以上的行刪掉／抽成共用層——"
        "🔴 注意本裁決的語意**不是**「禁止新增鎖檔」（那是已退場的檔數棘輪；R78 ARCH-03 抓到"
        "散落各處的引用仍在複述舊語意）：新增檔案只要淨額不上升就合法。"
        "真的必須長大時：`--print-guard-lines` 重釘 _FROZEN_GUARD_LINES、"
        "在 _GUARD_LINES_REPIN_LOG 補一列（含淨額與理由，不補即紅），並在交件回報寫出淨額"
        "（重釘一律由收尾包在所有包停工後做一次，同 MIN_TESTS 慣例）。"
    )


def guard_line_drift(
    frozen: Mapping[str, int], current: Mapping[str, int]
) -> list[tuple[str, int, int]]:
    """兩表**共同鍵**上值不同的逐筆清單 `(檔名, 基準值, 實況值)`（排序、可直接印）。

    刻意只看共同鍵：新增／消失的鍵由 `[新增]`／`[基準過時]` 兩款各自負責，
    在這裡重複收會讓同一筆違規印兩次（本檔的零串音紀律）。
    """
    return sorted(
        (name, frozen[name], current[name])
        for name in set(frozen) & set(current)
        if frozen[name] != current[name]
    )


def guard_line_problems(
    frozen: Mapping[str, int],
    current: Mapping[str, int],
    escapes: Sequence[str] = (),
    *,
    drift_tolerance: int = 0,
) -> list[str]:
    """護欄層逐檔行數棘輪的違規清單（空＝通過）。純函式，紅綠由合成注入自證。

    六款，各帶方括號標籤讓注入測試能斷言「紅的是對的那一款」（本檔的零串音紀律）：

    (1) `[崩塌]` 量測面為空 —— glob 寫壞／目錄改名時，`sum({}) <= frozen` 在原語意下
        是通過，那正是 fail-open。空集合一律紅。
    (2) `[逃逸]` 子目錄裡出現 `.py` —— 非遞迴面看不到它，等於一條合法的繞道。
    (3) `[新增]` 表上沒有列的檔案，且淨行數上升 —— `DEF-101-561③` 的機械面。
        淨額不上升時**不判違規**：那是該裁決明文指定的合併／改名，判紅就是超譯。
    (4) `[成長]` 淨行數上升（`glc_growth_problem`）—— 本輪新增的牙。
    (5) `[基準過時]` 鍵集合改變、或總量比基準低超過 `_GUARD_LINE_STALE_SLACK` ——
        棘輪的餘裕就是它的破口，縮下來不重釘等於替日後的無聲加回開門。
    (6) `[逐檔漂移]` 共同鍵上與磁碟不符的筆數 > `drift_tolerance` —— **R79 收斂包新增**。

    (6) 為何非補不可（R79 在乾淨 HEAD 上實測到「淨額為零的 A 減 B 增」對調盲區已是現況、
    棘輪雙雙印綠）、容忍度為何是參數不是常數、與本判準仍抓不到「檔內互抵」的誠實劃界，
    全文搬至 CrossPlatform_R97_Scan_Findings.md〈逐檔漂移判準 WHY〉節。
    """
    problems: list[str] = []
    if not current:
        return [
            f"[崩塌] 行數面抽不到任何 {_GUARD_DIR_REL}/{_GUARD_LINE_PATTERN}——"
            "掃描面崩塌（目錄改名／glob 寫壞？）。空清單在原語意下等同「零行」＝假綠。"
        ]
    if escapes:
        problems.append(
            f"[逃逸] {_GUARD_DIR_REL} 子目錄內出現 .py：{sorted(escapes)}——"
            "行數面刻意非遞迴（對齊 ADR §4.3 指令），子目錄因此是繞道。"
            "請把它移回 tools/tests/ 頂層，或連同 ADR 的指令一起改成遞迴。"
        )
    frozen_total = sum(frozen.values())
    current_total = sum(current.values())
    newcomers = sorted(set(current) - set(frozen))
    vanished = sorted(set(frozen) - set(current))
    if newcomers and current_total > frozen_total:
        problems.append(
            f"[新增] 基準表沒有這幾支：{newcomers}——DEF-101-561③ 已裁定"
            "「R61 開輪即禁止新增鎖檔、只准合併／刪除」，而本次淨行數也上升。"
            "現查：`git status --porcelain tools/tests/`＋`git diff --stat`。"
            "合法作法：把新判準擴充進既有鎖檔，或先合併／刪除等量的舊鎖檔再加。"
        )
    grown = glc_growth_problem(frozen_total, current_total)
    if grown:
        top = sorted(
            ((n, v - frozen.get(n, 0)) for n, v in current.items() if v > frozen.get(n, 0)),
            key=lambda pair: -pair[1],
        )[:5]
        problems.append(grown + f" 成長最多的幾支：{top}")
    if newcomers or vanished:
        problems.append(
            f"[基準過時] 鍵集合已漂移（新增 {newcomers}／消失 {vanished}）——"
            "改名／合併本身不是違規，但基準表必須同一次變更跟著改，否則棘輪張力靠餘裕撐。"
        )
    floor = int(frozen_total * (1 - _GUARD_LINE_STALE_SLACK))
    if current_total < floor:
        problems.append(
            f"[基準過時] 實況 {current_total} 已低於基準 {frozen_total} 的容忍下界 {floor}"
            "——縮下來要同步重釘，否則這段餘裕日後可被無聲地加回去。"
            "重釘：python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines"
        )
    drift = guard_line_drift(frozen, current)
    if len(drift) > drift_tolerance:
        problems.append(
            f"[逐檔漂移] {len(drift)} 支檔的基準值與磁碟不符（容忍 {drift_tolerance}）："
            f"{[f'{n} {old}→{new}' for n, old, new in drift[:8]]}"
            f"{' …' if len(drift) > 8 else ''}——**淨額可以是 0 而這一款照樣說話**，"
            "那正是它存在的理由：R79 在乾淨 HEAD 上實測到三支檔（−11／+7／+4）"
            "與磁碟不符而棘輪印綠。逐檔數字一旦失真，「哪支檔長了多少」的歸因全錯，"
            "而在總量守恆下任一支護欄檔可以無限膨脹只要別支等量縮水。"
            "重釘：python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines"
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
        # 現查一個「上界內但尚未被用掉」的流水號——刻意不寫死號碼：帳本會繼續長，
        # 寫死的空號隨時可能被真的用掉（本測試初版就撞上真實列）。
        # round 3 起共用 `unused_ids_below_ceiling()`：同一段「找空號」邏輯本檔原本有兩份
        # （這裡一份、可觸達性揭露一份），收成一支＝本輪「只准合併」的同一條紀律。
        free = unused_ids_below_ceiling(self.index, _BASELINE_ID_CEILING)
        sid = free[0] if free else None
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


class TestIdCeilingBypassReachabilityIsLive(unittest.TestCase):
    """檔頭邊界①「ID 上界擋不住雙欄位造假」的**可觸達性**必須是現算的，不是散文估計。

    WHY（round 3 SD-R60R3-06）：SD 以生產物件實算，逐一驗過三種構造——
    (i) 只回填一個未用過的號碼 ⇒ 綠（設計上放行，那是舊列）；
    (ii) 空號 ＋ 回填一個不晚於上界列的發現日期 ⇒ **綠**（雙欄位造假成立）；
    (iii) 空號 ＋ 誠實日期 ⇒ 紅（輔助判準擋掉單欄位造假那一半）。
    原檔頭只寫「擋不住雙欄位造假」，讀者容易把它讀成「那需要運氣」；事實是**現查就有一批
    空號可用**，門一直是開的。擋住它的是可見度（必須連帶偽造帳本列，diff 上看得見），
    不是稀缺性。這一段落差不改變風險等級（SD 判 P4），改變的是讀者對它的認知。

    為何做成測試而不是在檔頭補一個數字：空號數量會隨帳本開新號而變動（用掉一個就少一個），
    寫進散文就是又一個 stale 站點——而且會立刻被本檔自己的
    `TestThisLockObeysItsOwnNoHardcodedCountRule` 判為犯規（量詞「個」本來就在集合裡）。
    所以：數字現算、散文只留「以現查為準」的措辭，兩者由本類雙向綁定。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = family_row_index(read_family())

    def test_the_enumerator_agrees_with_the_real_ledger(self) -> None:
        """正控（真實資料）：現查出來的每個空號都真的不在家族索引內、且都在上界之下。"""
        ceiling_key = _id_key(_BASELINE_ID_CEILING)
        for sid in unused_ids_below_ceiling(self.index, _BASELINE_ID_CEILING):
            with self.subTest(sid=sid):
                self.assertNotIn(sid, self.index, "被報成空號的號碼其實有對應列")
                self.assertLess(_id_key(sid), ceiling_key, "空號不得越過上界")

    def test_the_enumerator_has_teeth_on_a_synthetic_index(self) -> None:
        """注入：合成一個「號碼連續無洞」的索引 ⇒ 空清單；挖掉一個 ⇒ 恰好報那一個。

        這支才是鑑別力來源：真實資料只能證明「現在有空號」，證不了「沒有空號時會回空」。
        """
        ceiling = _synthetic_id(1, 5)
        full = {
            _synthetic_id(1, n): (MAIN_LEDGER_NAME,
                                  Row(def_id=_synthetic_id(1, n), date="2026-01-01",
                                      triage="x", status="y", lineno=n))
            for n in range(1, _id_key(ceiling)[1])
        }
        self.assertEqual(unused_ids_below_ceiling(full, ceiling), [])
        hole = _synthetic_id(1, 3)
        punched = {k: v for k, v in full.items() if k != hole}
        self.assertEqual(unused_ids_below_ceiling(punched, ceiling), [hole])

    def test_the_header_discloses_the_bypass_while_free_numbers_remain(self) -> None:
        """雙向綁定：還有空號 ⟺ 檔頭必須寫著那句可觸達性揭露。

        · 空號還在卻把揭露刪掉／改寫 ⇒ 紅（讀者會回到「需要運氣」的誤讀）。
        · 空號真的用光了卻還留著「現查即有」⇒ 紅（那句話變成不實陳述）。
        刻意寫成雙條件而不是 `if free: assert ...`——後者在空號用光後就退化成恆綠空測試，
        正是本檔 `test_baseline_disclosure_in_adr_section_7_is_biconditional` 已經處理過的
        同一種假綠形態。
        """
        free = unused_ids_below_ceiling(self.index, _BASELINE_ID_CEILING)
        disclosed = _REACHABILITY_DISCLOSURE in (__doc__ or "")
        self.assertEqual(
            bool(free), disclosed,
            f"檔頭邊界①的可觸達性揭露與現況不一致：現查空號存在={bool(free)}、"
            f"檔頭有揭露={disclosed}。空號還在就必須留著「{_REACHABILITY_DISCLOSURE}」"
            "那句；空號用光了就必須改寫它（並在此說明是哪一輪把它填滿的）。"
            "🔴 訂正時**不要**在散文裡補上數量——現查值是 "
            f"{len(free)}，寫進去就是下一個 stale 站點，且會被本檔的"
            " TestThisLockObeysItsOwnNoHardcodedCountRule 當場判為犯規。",
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

    def test_constants_never_increase_versus_frozen_baseline(self) -> None:
        """真棘輪（R67 round 2 起）：與**簽入本檔的凍結基準**比對，與 git 狀態無關。

        取代原本的 `test_constants_never_increase_versus_head`：那一支在它唯一被消費的
        時點（pre-push／CI，皆在 commit 之後）恆真，SA 沙箱實證門檻可被單方面放大十餘倍
        而全綠。現版在髒樹／乾淨樹／CI checkout 行為完全相同，也不再有「取不到基準 ⇒
        skip」的 fail-open 分支可走。
        """
        problems = frozen_ratchet_problems()
        self.assertEqual(
            problems, [],
            "shrink-only 棘輪被違反（與凍結基準比對）：\n  " + "\n  ".join(problems)
            + "\n這兩個常數是「哪些列算舊列」與「能登記幾筆」的唯一開關，調升等於為新列開門。",
        )

    def test_ratchet_is_independent_of_git_state(self) -> None:
        """🔴 核心結構鎖（SA-R67-08）：棘輪全程不得呼叫外部行程（git）。

        舊實作在此鎖下必紅（它跑 `git show HEAD:<本檔>`）。這一條同時封死兩件事：
        (1) 基準被 commit 自我對齊的恆真陷阱；(2)「git 取不到基準 ⇒ 整支 skip」的
        fail-open。只鎖某幾個常數值是不夠的——那樣任何人把基準改回 git 導出量都沒有訊號。
        """
        def _boom(*_a, **_kw):  # pragma: no cover - 只為證明沒被呼叫
            raise AssertionError(
                "棘輪呼叫了外部行程——基準又變回 git 導出量了（SA-R67-08 回歸）"
            )

        with mock.patch("subprocess.run", _boom), \
             mock.patch("subprocess.check_output", _boom), \
             mock.patch("subprocess.Popen", _boom):
            self.assertEqual(frozen_ratchet_problems(), [])
            # 護欄層那一側的同型斷言：檔數棘輪本輪已由行數棘輪取代（見 `guard_line_problems`
            # 上方區塊註解），此處改驗接手者同樣不碰外部行程。
            self.assertEqual(
                guard_line_problems(
                    _FROZEN_GUARD_LINES, guard_lines_in_worktree(), guard_surface_escapes(),
                    drift_tolerance=_GUARD_LINE_DRIFT_TOLERANCE,
                ),
                [],
            )

    def test_raising_a_constant_is_red_even_when_the_worktree_is_clean(self) -> None:
        """缺陷注入（本次修法存在的理由）：只改門檻、基準不動 ⇒ 必紅。

        這正是舊實作在 commit 之後會放行的情境（SA 沙箱：改大→commit→全綠）。現在與 git
        狀態無關，恆紅。兩個常數各注入一次，證明不是只有其中一個掛著鎖。
        """
        raised = frozen_ratchet_problems(current_max=_FROZEN_MAX_BASELINE_ENTRIES + 1)
        self.assertTrue(
            any("_MAX_BASELINE_ENTRIES" in p for p in raised),
            f"調升 _MAX_BASELINE_ENTRIES 未被偵測，實得：{raised}",
        )
        moved = frozen_ratchet_problems(
            current_ceiling=_synthetic_id(999, 1),
        )
        self.assertTrue(
            any("_BASELINE_ID_CEILING" in p for p in moved),
            f"調升 _BASELINE_ID_CEILING 未被偵測，實得：{moved}",
        )

    def test_frozen_baseline_matches_the_live_thresholds(self) -> None:
        """基準新鮮度：凍結基準必須與現行門檻逐字相等。

        WHY（維持張力，同 `_TIER_BASELINE` 的新鮮度鎖）：門檻合法下修後若不同步下修基準，
        基準就會停在舊高點，之後可以無聲地把門檻「調回」那個高點——棘輪的餘裕就是它的破口。
        要求相等 ⇒ 任何門檻異動都必須動到基準那一行，方向在 diff 上一望即知。
        """
        self.assertEqual(_MAX_BASELINE_ENTRIES, _FROZEN_MAX_BASELINE_ENTRIES)
        self.assertEqual(_BASELINE_ID_CEILING, _FROZEN_BASELINE_ID_CEILING)


class TestGuardLayerRatchet(unittest.TestCase):
    """(d) 護欄層棘輪：`tools/tests/` 這一層的**淨行數**只准往下走（`DEF-101-561③`）。

    量測面在 R77 換過一次：舊＝純量鎖檔支數（病換地方長，支數不動行數翻倍）；現＝
    `_FROZEN_GUARD_LINES` 逐檔行數表，判準是淨行數不得上升（`guard_line_problems`／
    `glc_growth_problem`）。接手者語意**不是**「禁止新增檔案」：新增鎖檔只要同一次變更內
    刪掉等量以上的行就合法；重釘須在 `_GUARD_LINES_REPIN_LOG` 補一列，不補即紅（R78
    ARCH-01）。ARCH-R60R3-04 立案沿革與 R78 ARCH-03 舊語意訂正全文搬至
    CrossPlatform_R97_Scan_Findings.md〈護欄層棘輪 WHY〉節。

    本類仍保留兩支**檔案面**的自錨（`guard_files_in_worktree()` 與根層閘門 pattern 的
    SSOT 綁定）：行數面是非遞迴 `*.py`、檔案面是遞迴 `test_*.py`，兩個面的涵蓋關係由
    `guard_baseline_gaps()` 證明。`_*.py` 這種共享零件不進檔案面（理由見上述搬遷節）。
    """

    def test_the_worktree_enumerator_is_not_vacuous(self) -> None:
        """正控：列舉器必須至少找得到**本檔自己**，且自比自為零違規。

        自錨（用本檔的相對路徑）而不是釘一個數字：數字是 stale 站點，而「本檔存在」是
        這支測試正在執行這件事的必然推論 ⇒ 永不過期，卻仍能抓到 pattern／路徑寫壞
        （寫壞就列不到自己，紅）。
        """
        current = guard_files_in_worktree()
        self.assertIn(
            _SELF_REL, current,
            f"工作樹列舉器找不到本檔（{_SELF_REL}）——pattern／路徑寫壞了？"
            "列舉器一旦回空集合，棘輪比較會恆真通過＝靜默失效",
        )

    def test_the_counted_surface_is_the_root_gate_pattern(self) -> None:
        """SSOT 綁定：計數面必須等於根層閘門 discover 用的 pattern，兩邊漂移即紅。

        WHY：本棘輪的正當性完全建立在「數的就是閘門會跑的那批鎖檔」上。閘門改 pattern
        而這裡沒跟，數的就是另一個集合，裁決的射程會靜默偏掉。
        延後 import：`run_root_unittests` 於 import 期會做 stdio 手術（`_stdio_utf8`），
        不進本檔的 import 期路徑；同 `test_doc_loc_baseline_freshness_r60.py` 的既有作法。
        """
        import run_root_unittests  # noqa: PLC0415

        self.assertEqual(
            _GUARD_FILE_PATTERN, run_root_unittests._PATTERN,
            "本檔的計數 pattern 與 run_root_unittests._PATTERN 已漂移——"
            "後者是 SSOT，請改本檔這一側",
        )

    def test_the_line_ratchet_took_over_and_has_teeth(self) -> None:
        """接手證明：檔數棘輪退場後，行數棘輪必須真的在守，且注入會紅。

        WHY 這一支存在：R77 移除檔數棘輪的理由是它**把病換了個地方長**——檔數被釘住，
        成長就全部灌進既有巨檔（同期行數翻倍而判準全程綠）。移除一道鎖若不同時證明接手者
        有牙，等於淨損一道防護；這支測試就是那個證明。
        """
        current = guard_lines_in_worktree()
        self.assertEqual(
            guard_line_problems(_FROZEN_GUARD_LINES, current, guard_surface_escapes(),
                                drift_tolerance=_GUARD_LINE_DRIFT_TOLERANCE),
            [],
            "行數棘輪對現況應為零違規（控制組）",
        )
        shrunk = dict(_FROZEN_GUARD_LINES)
        first = sorted(shrunk)[0]
        shrunk[first] = max(0, shrunk[first] - 1000)
        self.assertTrue(
            guard_line_problems(shrunk, current),
            "把凍結基準人為壓低 1000 行（＝製造一次淨成長）後行數棘輪仍不紅 ⇒ 它沒有牙，"
            "檔數棘輪的退場就變成淨損一道防護",
        )

    # ── R79 收斂包：淨額為零的「A 減 B 增」對調必須說話 ──────────────────────
    def test_a_net_zero_swap_is_red(self) -> None:
        """🔴 注入＝**乾淨 HEAD 上的實況重演**：兩支檔一增一減、總量不變 ⇒ `[逐檔漂移]` 必紅。

        R79 掃描實測：乾淨 HEAD 的凍結表已有三支檔與磁碟不符（−11／+7／+4，淨額 0），
        而 `(4) [成長]` 與 `(5) [基準過時]` 兩款結構上都不會說話——本函式原本的
        「誠實劃界」段逐字寫著這個盲區，而那個盲區在鎖落地的同一輪就已經被踩進去且入庫。
        用**真表**做注入基底：合成表證明不了「這道判準對 repo 現有的那張表有牙」。
        """
        current = dict(guard_lines_in_worktree())
        names = sorted(set(_FROZEN_GUARD_LINES) & set(current))
        self.assertGreaterEqual(len(names), 2, "共同鍵不足兩支，注入基底已失效")
        swapped = dict(current)
        swapped[names[0]] -= 7
        swapped[names[1]] += 7
        self.assertEqual(
            sum(swapped.values()), sum(current.values()), "注入本身必須是淨額為零的對調")
        problems = guard_line_problems(
            _FROZEN_GUARD_LINES, swapped, drift_tolerance=_GUARD_LINE_DRIFT_TOLERANCE)
        self.assertTrue(
            any("[逐檔漂移]" in p for p in problems),
            f"淨額為零的 A 減 B 增仍被放行 ⇒ 這就是 R79 抓到的既成事實；實得：{problems}")
        self.assertFalse(
            [p for p in problems if "[成長]" in p or "[基準過時]" in p],
            "本注入不該驚動 (4)(5)，否則證明不了是新那一款在說話（零串音）")

    def test_the_drift_criterion_does_not_fire_on_a_matching_table(self) -> None:
        """對照組：表與磁碟逐檔相符時不得說話——否則新款只是恆紅（那種鎖會被整道關掉）。"""
        current = guard_lines_in_worktree()
        self.assertEqual(guard_line_drift(current, current), [])
        self.assertEqual(
            guard_line_problems(current, current, drift_tolerance=0), [])

    def test_the_repin_command_shows_the_drift_even_at_net_zero(self) -> None:
        """R79：重釘入口自己必須看得見那個盲區。

        修前實況：三支檔失真而 `--print-guard-lines` 首行印 `(+0)`、尾行印 `+0` 的稽核列
        草稿 ⇒ 照流程走的人只會看到「不需要重釘」。一個看不見自己盲區的入口，會讓盲區
        永遠留在原地。這裡不真跑子行程（那由 `TestRepinCommandIsReal` 端到端驗），只斷言
        輸出裡確實有那一行、且它的計數來自 `guard_line_drift`（同一份實作，非第二份）。
        """
        import io  # noqa: PLC0415
        from contextlib import redirect_stdout  # noqa: PLC0415

        buf = io.StringIO()
        with redirect_stdout(buf):
            _print_guard_lines()
        body = buf.getvalue()
        live = guard_line_drift(_FROZEN_GUARD_LINES, guard_lines_in_worktree())
        self.assertIn(f"# 逐檔漂移 {len(live)} 支", body)
        for name, before, after in live:
            self.assertIn(f"#   DIFF {name} {before} -> {after}", body)

    # ── R78 ARCH-01：重釘必須留下淨額與理由 ────────────────────────────────
    def test_the_repin_log_accounts_for_the_frozen_table(self) -> None:
        """主牙：稽核痕跡表尾的新總量必須逐字等於凍結表實際總量。

        WHY：逐列手改整張表與「順手更新一下」在機械上原本無法區分（實測 `a7a3080` 一個
        commit 內量測面 +3505 而閘門 rc=0）。要求對帳之後，重釘不寫理由＝紅。
        """
        problems = repin_log_problems(
            _GUARD_LINES_REPIN_LOG, sum(_FROZEN_GUARD_LINES.values()),
            history_digest=_REPIN_LOG_HISTORY_SHA256,
            prefix_len=_REPIN_LOG_FROZEN_PREFIX_LEN,
            max_unfrozen_tail=_REPIN_LOG_MAX_UNFROZEN_TAIL,
            regression_lane=_REGRESSION_LANE_LOG)
        self.assertEqual(problems, [], "重釘稽核痕跡不合規：\n  " + "\n  ".join(problems))

    def test_repinning_without_logging_a_reason_is_red(self) -> None:
        """注入①：凍結表被改動（總量 +1）卻沒補一列 ⇒ `[未對帳]` 必紅。"""
        total = sum(_FROZEN_GUARD_LINES.values())
        problems = repin_log_problems(_GUARD_LINES_REPIN_LOG, total + 1)
        self.assertTrue(problems, "改了凍結表而不補稽核列竟然放行 ⇒ ARCH-01 沒有被修")
        self.assertTrue(any("[未對帳]" in p for p in problems), problems)

    # ── R80 收尾包：款(9) 的紅側自證（落地當輪只有綠側對照組，等於沒有牙）────────
    def test_a_positive_repin_without_a_deletion_account_is_red(self) -> None:
        """🔴 注入＝款(9) 的**紅側**：淨額為正卻沒交代刪了什麼 ⇒ `[未附刪除清單]` 必紅。

        WHY 這一格非補不可：款(9) 落地當輪（R80 包 C）全檔只有一個綠側對照組
        （`test_appending_one_row_keeps_the_history_digest_stable` 的合成列剛好帶著兩個
        記號），紅側零注入 ⇒ 判準寫成恆綠（例如條件寫反、或 regex 永不命中）不會有任何
        東西說話。本 repo 對「只測會過的那幾種寫法」已有判例（R78 A-lint）。

        三種**半套**形態各自注入一次——半套比全缺更危險，因為它看起來像已經照做了：
          · 兩個記號都沒有 ⇒ 紅
          · 承認了是 `[非淨減法輪]`、卻沒指名逐檔清單住哪 ⇒ 紅（清單無家＝沒有清單）
          · 指名了清單、卻既沒承認也沒有足量刪除交代（`刪 3 行` < 淨額）⇒ 紅
        另兩格證明它不是恆紅：足量刪除交代＋指名清單 ⇒ 綠；淨額為負 ⇒ 本款不說話。
        """
        def _judge(rnd: str, delta: int, reason: str) -> list[str]:
            row = (rnd, 1000, 1000 + delta, delta, reason)
            return [p for p in repin_log_problems((row,), 1000 + delta)
                    if "[未附刪除清單]" in p]

        home = "CrossPlatform_R81_Scan_Findings.md"
        long_enough = "理由夠長夠長夠長夠長夠長夠長夠長夠長，"
        self.assertTrue(_judge("R81", 500, long_enough), "兩個記號都沒有竟然放行")
        self.assertTrue(
            _judge("R81", 500, long_enough + _NOT_NET_SUBTRACTION_TOKEN),
            "承認了是非淨減法輪、卻沒指名逐檔清單的家竟然放行——清單無家＝沒有清單")
        self.assertTrue(
            _judge("R81", 500, f"{long_enough}刪 3 行，清單見 {home}"),
            "刪除交代（3 行）遠少於淨額（500）竟然放行 ⇒ 數量比較沒有真的在做")
        self.assertFalse(
            _judge("R81", 500, f"{long_enough}刪 500 行，逐檔清單見 {home}"),
            "足量刪除交代＋指名清單是本款指定的合法形態，判紅就是恆紅（那種鎖會被關掉）")
        self.assertFalse(
            _judge("R81", -5, long_enough), "淨額為負仍被本款判紅 ⇒ 它在懲罰正確方向")

    # ── R84 ARCH-01：重釘要付代價（款(10)(11)＋後設鎖）────────────────────────
    def _rising(self, no: int, delta: int = 100) -> tuple[str, int, int, int, str]:
        """一列「淨額為正且已交代」的合成重釘（供款(10)(11) 的紅綠兩側共用）。"""
        return (f"R{no}", 1000, 1000 + delta, delta,
                f"合成列，理由夠長夠長夠長 {_NOT_NET_SUBTRACTION_TOKEN} "
                f"CrossPlatform_R{no}_Scan_Findings.md")

    def test_the_real_repin_log_stays_inside_the_cost_envelope(self) -> None:
        """綠側（真表）：款(10)(11) 對現況零違規——**且這正是「不追溯」的證據**。

        WHY 這一格非有不可：真表**每一列都在上升**（立案量測：R77→R83 +24,895／零列
        下降）。若判準沒有 `_REPIN_ROUND_CAP_SINCE` 這道生效點，它上線的當回合就會把
        整段歷史判紅，而那些列受款(7) 的 append-only 指紋保護、沒有任何人補得回來 ⇒
        下一個人唯一的出路是把整道鎖刪掉（ARCH-02 已判過這個形狀）。
        """
        self.assertEqual(
            repin_growth_problems(_GUARD_LINES_REPIN_LOG), [],
            "款(10)(11) 對真表說話了——它們刻意不追溯到 "
            f"R{_REPIN_ROUND_CAP_SINCE} 之前，請檢查生效點是否被改動")
        nets = repin_round_nets(_GUARD_LINES_REPIN_LOG)
        self.assertTrue(nets, "稽核痕跡空了 ⇒ 淨額又回到「不出現在任何地方」")
        #: 🔴 R85 收尾單人窗口訂正（把動工中的預測寫成契約、當輪即被證偽）——立案原文＝
        #: Guard_Repin 證據檔 §B-12。「為何是訂正不是放寬」三條論證（要求保留／到期時點
        #: 釘死於 `_NET_SUBTRACTION_DUE_ROUND` 且不留延期參數、刻意不複寫該字面以免超前
        #: 帳本輪號／斷言由「已達成」改「尚未到期」）與「R85 為何達不到（算術非判斷）」
        #: 全文搬至 CrossPlatform_Guard_Line_History.md〈淨減法到期斷言訂正 WHY〉節。
        latest_round = max(no for no, _ in nets)
        self.assertTrue(
            any(delta <= 0 for _no, delta in nets)
            or latest_round < _NET_SUBTRACTION_DUE_ROUND,
            f"整段稽核痕跡至今**一列都沒有下降過**（實得逐輪淨額 {nets}），"
            f"而最新列已是 R{latest_round} ≥ 到期輪 R{_NET_SUBTRACTION_DUE_ROUND}"
            "——款(11)／ADR-XPLAT-002 §8.1 item 15 的淨減法義務**到期未兌現**。"
            "出口只有一個：讓某一輪的逐輪加總 ≤ 0（見 Architect R85 的分桶建議："
            "把 `_FROZEN_GUARD_LINES` 按『守生產碼／守散文／守自己』拆開，"
            "後兩桶 shrink-only——那才是能真的往下走的結構）")

    def test_a_third_consecutive_rising_round_is_red(self) -> None:
        """🔴 注入＝款(11) 的主牙：連續三輪淨額為正 ⇒ `[只升不降]` 必紅。

        這是 ARCH-01 的缺陷本體本身：立案時「重釘」的唯一成本是補一列紀錄，於是每一次
        都通過。三格一組（兩輪綠／三輪紅／中間插一輪 ≤ 0 又綠）證明它既有牙、又不是
        恆紅——出口存在且明確（讓某一輪淨額 ≤ 0），這是本 repo 對「紅了要有出路」的要求。
        """
        since = _REPIN_ROUND_CAP_SINCE
        two = tuple(self._rising(since + i) for i in range(2))
        self.assertEqual(
            [p for p in repin_growth_problems(two) if "[只升不降]" in p], [],
            f"連兩輪上升就判紅 ⇒ 比宣告的上限 {_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS} 更嚴，"
            "本輪合法的重釘會做不到")
        three = (*two, self._rising(since + 2))
        problems = repin_growth_problems(three)
        self.assertTrue(
            any("[只升不降]" in p for p in problems),
            f"連續三輪只升不降竟然放行 ⇒ ARCH-01 沒有被修；實得：{problems}")
        self.assertFalse(
            [p for p in problems if "[超出每輪上限]" in p],
            "本注入不該驚動款(10)，否則證明不了是方向那一款在說話（零串音）")
        healed = (*two,
                  (f"R{since + 2}", 1000, 900, -100, "合成列：把兩支鎖檔合併，淨額為負"),
                  self._rising(since + 3))
        self.assertEqual(
            [p for p in repin_growth_problems(healed) if "[只升不降]" in p], [],
            "中間插入一輪淨額 ≤ 0 之後仍紅 ⇒ 連續計數沒有歸零，那條出口是假的")

    def test_a_round_that_exceeds_the_net_cap_is_red(self) -> None:
        """注入＝款(10)：單輪淨額超過上限 ⇒ `[超出每輪上限]` 必紅（踩線那格為綠）。

        另一格證明**同輪多列會被合併計算**：拆成兩列各半、合計仍超限 ⇒ 照樣紅。
        少了這一格，繞過本款的成本是「多打一列」，而那正是款(4) 當年沒有守住的形狀。

        🔴 合成輪號取**上限表最後一列的輪號**而不是生效點：R85 起上限分段生效，
        生效點那一輪（R84）在位的是舊上限 5400，用它造樣本會量到另一把尺。
        """
        since, cap = _REPIN_NET_CAP_SCHEDULE[-1]
        at_par = (self._rising(since, cap),)
        self.assertEqual(
            [p for p in repin_growth_problems(at_par) if "[超出每輪上限]" in p], [],
            "淨額等於上限竟然判紅 ⇒ 上限的語意變成「嚴格小於」，與訊息文字不符")
        over = (self._rising(since, cap + 1),)
        self.assertTrue(
            any("[超出每輪上限]" in p for p in repin_growth_problems(over)),
            "淨額超過上限竟然放行 ⇒ 款(10) 沒有牙")
        split = (self._rising(since, cap // 2 + 1), self._rising(since, cap // 2 + 1))
        self.assertTrue(
            any("[超出每輪上限]" in p for p in repin_growth_problems(split)),
            "把一輪的成長拆成兩列就繞過上限 ⇒ 計數單位必須是「輪」而不是「列」")

    def test_the_effective_round_anchor_is_the_widest_escape_hatch(self) -> None:
        """🔴 F3／B-1 注入：`_REPIN_ROUND_CAP_SINCE` 一旦被推遲，款(10)(11) 整段失效。

        本格先證明那個逃生口**是真的**（否則下一格的後設鎖是在守一件不存在的事），
        再由下一格證明它已經被鎖住。分兩格而不是併成一格：一格證「病在」、一格證「藥有效」，
        併起來的話藥失效時病那半仍會綠（本檔零串音紀律的同一句話）。
        """
        since = _REPIN_ROUND_CAP_SINCE
        rising = tuple(self._rising(since + i) for i in range(4))
        self.assertTrue(
            any("[只升不降]" in p for p in repin_growth_problems(rising)),
            "四輪連升在現行生效點下竟然放行 ⇒ 這一格的前提不成立，後面證不了逃生口")
        self.assertEqual(
            repin_growth_problems(rising, since=since + 4), [],
            "把生效點推到那四輪之後竟然還判得到 ⇒ 本格對「分母被清空」這件事失明，"
            "請確認 `since` 真的在過濾輪次")

    def test_the_cost_constants_can_only_be_tightened(self) -> None:
        """後設鎖：三個代價常數只准往更嚴的方向改（放寬即紅、收緊為綠）。

        WHY：款(10)(11) 的門檻若可以順手調高，它們與「補一列紀錄」這道零成本手續就沒有
        差別了——那正是 ARCH-01 在治的病。形狀照 `frozen_ratchet_problems()`（凍結基準版，
        不走 git；理由見那支的 docstring）。

        🔴 **R84 F3／B-1：第三個常數 `_REPIN_ROUND_CAP_SINCE` 原本不在本格射程內**，
        而它是三者中威力最大的——另外兩個調門檻，它調**分母**。Architect 注入實測：
        副本的 `SINCE` 由 84 改成 99，`-k "cost_envelope or rising or net_cap or
        tightened"` 仍 rc=0／4 passed ⇒ 一行 diff 關掉整段代價機制、無一物轉紅。
        """
        self.assertEqual(
            repin_cost_ratchet_problems(), [],
            "現行代價常數已高於簽入的凍結基準——調升被禁止，請改回或連同基準一起下修")
        self.assertTrue(
            repin_cost_ratchet_problems(current_cap=_FROZEN_REPIN_ROUND_NET_CAP + 1),
            "調高每輪淨額上限竟然放行 ⇒ 後設鎖沒有牙")
        self.assertTrue(
            repin_cost_ratchet_problems(
                current_run=_FROZEN_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS + 1),
            "調高「連續上升輪數」上限竟然放行 ⇒ M1 的機械面可以被一行字取消掉")
        self.assertTrue(
            repin_cost_ratchet_problems(
                current_since=_FROZEN_REPIN_ROUND_CAP_SINCE + 1),
            "把生效輪次往後推竟然放行 ⇒ 上一格證明的那個逃生口仍然開著："
            "門檻守得再嚴，判準的分母可以被一行 diff 清空")
        self.assertEqual(
            repin_cost_ratchet_problems(
                current_cap=_FROZEN_REPIN_ROUND_NET_CAP - 1,
                current_run=max(0, _FROZEN_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS - 1),
                current_since=_FROZEN_REPIN_ROUND_CAP_SINCE - 1,
                # 零串音：本格只問「三個常數是否被判成更嚴」，`current_cap` 用的是
                # 遠早於現行到期義務的歷史凍結值（2600 那個量級），與「到期輪 R101 round-label-ok
                # 是否已兌現」是完全不同的問題（後者已由
                # `test_the_net_cap_carries_a_due_date_that_turns_red_on_its_own`
                # 專責覆蓋）。不隔開的話，一旦稽核痕跡走到 due_round，這裡的合成
                # 值就會被款(12) 意外串音，證明不了是「方向」那三款在說話。
                latest_round=_REPIN_NET_CAP_DUE_ROUND - 1),
            [], "把三個常數都往更嚴的方向改竟然判紅 ⇒ 後設鎖在懲罰正確方向"
                "（`SINCE` 的「更嚴」方向是**變小**——更早生效＝涵蓋更多輪）")

    def test_the_net_cap_schedule_can_only_grow_tighter_and_never_be_rewritten(
        self,
    ) -> None:
        """🔴 R85：分段上限表的三條形狀鎖各自紅綠自證（真表為綠）。

        WHY 分三種注入：改寫既有列＝回頭改變已收輪次當時受判的尺（那些列補不回來）；輪號
        不遞增＝`net_cap_for_round()` 的「末列在位」語意不成立；追加更寬的上限＝繞過只看
        純量的 `_FROZEN_REPIN_ROUND_NET_CAP`。任一失效，款(10) 就能被一行 diff 關掉。
        """
        base = _FROZEN_REPIN_NET_CAP_SCHEDULE
        self.assertEqual(net_cap_schedule_problems(), [], "真表被形狀鎖判紅")
        self.assertEqual(
            net_cap_for_round(base[0][0]), base[0][1],
            "生效點那一輪拿到的不是它當時在位的上限 ⇒ 下修變成追溯，"
            "而被追溯的那些列受款(7) 指紋保護、補不回來（R85 立案事實）")
        rewritten = ((base[0][0], base[0][1] + 1), *base[1:])
        self.assertTrue(
            any("[上限表被改寫]" in p
                for p in net_cap_schedule_problems(rewritten, base)),
            "就地把既有列的上限改寬竟然放行 ⇒ append-only 只是一句話")
        self.assertTrue(
            any("[上限表輪號未遞增]" in p for p in net_cap_schedule_problems(
                (*base, (base[-1][0], base[-1][1])), base)),
            "輪號沒有遞增竟然放行 ⇒ 「最後一列在位」的語意不成立")
        self.assertTrue(
            any("[上限表被放寬]" in p for p in net_cap_schedule_problems(
                (*base, (base[-1][0] + 1, base[-1][1] + 1)), base)),
            "追加一列更寬的上限竟然放行 ⇒ 純量後設鎖看不到表，代價機制被繞過")
        self.assertEqual(
            net_cap_schedule_problems(
                (*base, (base[-1][0] + 1, base[-1][1] - 1)), base), [],
            "照正確方向追加（更晚的輪號＋更小的上限）竟然判紅 ⇒ 這道鎖沒有出口")

    def test_the_net_cap_carries_a_due_date_that_turns_red_on_its_own(self) -> None:
        """🔴 F3／A-03 款(12)：`_REPIN_ROUND_NET_CAP` 的到期義務是閘門，不是散文。

        WHY 這一格非有不可：款(10) 的上限當初取的是**歷來單輪最大值**（逐輪淨額現查
        `repin_round_nets()`，本檔不複寫——前一輪抄成散文，抄完當輪就被自己的第二次
        重釘證偽），所以它今天不擋任何行為。而「下一輪再下修」這種到期義務，本 repo
        已實證散文形態的攔阻力為 0（鐵律一那一節：最大桶是「宣稱先於查證」）。

        四格一組：今天為綠（R85 已兌現、下一段到期輪尚未到）／到期而未下修為紅／
        到期且已下修回綠／到期目標必須嚴格低於現行上限（否則款(12) 是一句永遠成立的話）。
        """
        self.assertEqual(
            [p for p in repin_cost_ratchet_problems() if "[到期未下修]" in p], [],
            "真表今天就被款(12) 判紅 ⇒ 到期輪設得太早，本輪自己付不出來；"
            f"最新列＝{_GUARD_LINES_REPIN_LOG[-1][0]}、到期輪＝R{_REPIN_NET_CAP_DUE_ROUND}")
        overdue = _REPIN_NET_CAP_DUE_TARGET + 1
        self.assertTrue(
            any("[到期未下修]" in p for p in repin_cost_ratchet_problems(
                current_cap=overdue, frozen_cap=overdue,
                latest_round=_REPIN_NET_CAP_DUE_ROUND)),
            "稽核痕跡已走到到期輪、上限卻還高於目標，竟然放行 ⇒ 到期義務又退回散文")
        self.assertEqual(
            repin_cost_ratchet_problems(
                current_cap=_REPIN_NET_CAP_DUE_TARGET,
                latest_round=_REPIN_NET_CAP_DUE_ROUND), [],
            "已經下修到目標值卻仍判紅 ⇒ 這道鎖沒有出口，實務上一定被整個關掉（ARCH-02）")
        self.assertLess(
            _REPIN_NET_CAP_DUE_TARGET, _REPIN_ROUND_NET_CAP,
            "到期目標不低於現行上限 ⇒ 款(12) 是一句永遠成立的話（R85 兌現 5400→3200 之後"
            "必須就地重新武裝下一段，否則這款從此恆綠＝機制靜默退役）")

    def test_the_due_round_itself_cannot_be_postponed(self) -> None:
        """🔴 DEF-200-121：到期輪自己被推遲時必須有東西轉紅（帳本立案那把注入的常駐化）。

        立案注入實測：到期輪改 500 紅 0、改 9999 紅 0、到期目標 1600→1999 紅 0——
        款(12) 的 `live_round >= due_round` 對「把到期日搬到遠未來」永假，而同檔逐字
        宣稱「刻意沒有『延期』參數」。與 F3／B-1（`_REPIN_ROUND_CAP_SINCE`）逐字同型：
        修了 SINCE、沒修 DUE_ROUND。四格：立案那把注入轉紅／合法重新武裝（兌現輪+2）
        為綠／真常數今天為綠／lookahead 自身 shrink-only。
        """
        live = max(no for no, _d in repin_round_nets(_GUARD_LINES_REPIN_LOG))
        self.assertTrue(
            any("[到期日被推遲]" in p for p in repin_cost_ratchet_problems(
                due_round=9999, latest_round=live)),
            "到期輪改成 9999 竟然紅 0 ⇒ 帳本立案的那把注入原樣復活"
            "（款(12) 永假、到期義務靜默熄滅）")
        self.assertEqual(
            [p for p in repin_cost_ratchet_problems(
                due_round=live + _REPIN_DUE_ROUND_MAX_LOOKAHEAD, latest_round=live)
             if "[到期日被推遲]" in p], [],
            "兌現輪＋lookahead 的合法重新武裝竟然判紅 ⇒ 這道鎖沒有出口（ARCH-02 形態）")
        self.assertEqual(
            [p for p in repin_cost_ratchet_problems() if "[到期日被推遲]" in p], [],
            f"真常數今天就被判紅——DUE_ROUND=R{_REPIN_NET_CAP_DUE_ROUND}、"
            f"最新稽核輪=R{live}、lookahead={_REPIN_DUE_ROUND_MAX_LOOKAHEAD}")
        self.assertTrue(
            any("_REPIN_DUE_ROUND_MAX_LOOKAHEAD" in p for p in repin_cost_ratchet_problems(
                due_lookahead=_FROZEN_REPIN_DUE_ROUND_MAX_LOOKAHEAD + 1)),
            "lookahead 被調大竟然放行 ⇒ 「不可延期」可以被一行 diff 改寫成「可以晚一點」")

    # ── R80 二審（NEW-SA2-01＝QA2-N2）：文件側引用的累積總量也要對帳 ────────────
    def _latest_round(self) -> str:
        return _GUARD_LINES_REPIN_LOG[-1][0]

    def _marked_docs(self, rewrite: Callable[[str], str]) -> dict[str, str]:
        """真文件、記憶體內改字：只動本輪標記行，其餘位元組不動。

        刻意**不寫磁碟**：注入載體若要還原就有崩潰安全問題（本 repo 已有判例——
        `git checkout --` 型的還原會連未提交工作一起抹）。純函式吃字串，注入零副作用。
        """
        docs = guard_total_docs_in_worktree()
        latest, touched, out = self._latest_round(), 0, {}
        for rel, text in docs.items():
            lines = text.splitlines()
            for i, line in enumerate(lines):
                mark = _GUARD_TOTAL_MARK_RE.search(line)
                if mark is not None and mark.group(1) == latest:
                    lines[i], touched = rewrite(line), touched + 1
            out[rel] = "\n".join(lines)
        self.assertGreaterEqual(
            touched, _GUARD_TOTAL_DOC_MIN_SITES,
            f"掃描面上找不到 {_GUARD_TOTAL_DOC_MARK}{latest} 的標記行 ⇒ 注入在對空氣做，"
            "下面那幾個 assert 會恆綠")
        return out

    def test_the_docs_cite_the_live_guard_total(self) -> None:
        """真表＋真文件（**綠側**）：本輪標記行引用的總量必須等於凍結表實際總量。"""
        problems = doc_guard_total_problems(
            guard_total_docs_in_worktree(), sum(_FROZEN_GUARD_LINES.values()),
            self._latest_round())
        self.assertEqual(problems, [], "文件側累積總量不合規：\n  " + "\n  ".join(problems))

    def test_a_stale_total_in_the_real_docs_is_red(self) -> None:
        """注入①（**紅側**，真文件）：把總量寫錯一位 ⇒ `[總量不符]` 必紅。

        這正是 R80 二審抓到的形態：重釘了、文件沒跟上，而在本款之前**沒有任何東西**
        看得到 `.md` ⇒ 三個站點同時錯了一整輪都沒有轉紅。
        """
        bad = self._marked_docs(lambda line: _GUARD_TOTAL_TRIPLE_RE.sub(
            lambda m: f"{m.group(1)} → {int(m.group(2)) + 1}（{m.group(3)}{m.group(4)}",
            line, count=1))
        problems = doc_guard_total_problems(
            bad, sum(_FROZEN_GUARD_LINES.values()), self._latest_round())
        self.assertTrue(any("[總量不符]" in p for p in problems),
                        f"文件把總量寫錯竟然放行：{problems}")

    def test_a_broken_arithmetic_in_the_real_docs_is_red(self) -> None:
        """注入②（真文件）：總量對、但「+淨額」那一格加錯 ⇒ `[淨額不符]` 必紅。

        與注入① 分開是因為它們是**不同的錯**：① 是「文件沒跟上重釘」，
        ② 是「同一行的三個數字自己對不起來」——R80 二審實測的 `+2029` 就是後者
        （兩次重釘 1528＋595＝2123，差 94）。只測 ① 的話 ② 會整類漏掉。
        """
        bad = self._marked_docs(lambda line: _GUARD_TOTAL_TRIPLE_RE.sub(
            lambda m: f"{m.group(1)} → {m.group(2)}（{m.group(3)}{int(m.group(4)) + 94}",
            line, count=1))
        problems = doc_guard_total_problems(
            bad, sum(_FROZEN_GUARD_LINES.values()), self._latest_round())
        self.assertTrue(any("[淨額不符]" in p for p in problems),
                        f"同一行的算術對不起來竟然放行：{problems}")

    def test_removing_the_marker_is_red_and_history_rounds_do_not_count(self) -> None:
        """注入③④：拿掉標記 ⇒ `[未登記]`；把標記改成**舊輪號** ⇒ 同樣 `[未登記]`。

        ③ 擋的是「最省力的滿足方式」（刪掉那一行，判準就沒有東西可判＝fail-open）。
        ④ 證明輪號真的在分**史料 vs 現行宣稱**：舊輪的行不該讓本輪過關，否則
        下一輪只要不寫，就自動繼承上一輪的綠。
        """
        total, latest = sum(_FROZEN_GUARD_LINES.values()), self._latest_round()
        gone = self._marked_docs(
            lambda line: line.replace(_GUARD_TOTAL_DOC_MARK, "was-guard-total:"))
        self.assertTrue(
            any("[未登記]" in p for p in doc_guard_total_problems(gone, total, latest)),
            "把標記整個拿掉竟然放行 ⇒ 本判準可以靠刪一行關掉")
        # 🔴 R84：替換文字必須**保留 HTML 註解形態**（判準自 R84 起只認註解內的標記）。
        # 寫成裸 `guard-total:R01` 會讓這一注入退化成「標記整個消失」＝與上一格同款，
        # 而本格要驗的是「標記在、但輪號是舊的」這個**不同**的形態（零串音）。
        aged = self._marked_docs(
            lambda line: _GUARD_TOTAL_MARK_RE.sub("<!-- guard-total:R01 -->", line))
        self.assertTrue(
            any("[未登記]" in p for p in doc_guard_total_problems(aged, total, latest)),
            "只有舊輪號的標記竟然算本輪達標 ⇒ 綠會被上一輪繼承下去")

    def test_the_extended_doc_surface_covers_the_handoff_without_false_reds(
            self) -> None:
        """🔴 R84 ZT-04（F3／B-2 訂正版）：擴面必須**真的**含交棒書，且對現況零假紅。

        立案（`R83_HANDOFF.md` §2.3 自陳「唯一刻意寫死、且沒有機械物在守」，實查為真）：
        舊的兩個 glob 一份交棒書都不匹配 ⇒ 呈給掌舵者的三元組可以全錯而無一物轉紅。
        本格把「擴面」與「零假紅」兩件事一起釘住，因為它們互為對方的前提：
          · 擴面若沒生效（glob 寫壞／檔名慣例變了），下面那個「零假紅」會恆綠＝假的安心；
          · 收窄若沒生效，擴面當回合的每一筆命中都是假紅（`R83_HANDOFF.md` 為了指路而
            逐字寫出標記＋輪號），而假紅會逼下一輪關掉整道鎖。

        🔴 **F3／B-2：本格原本還斷言掃描面含 `docs/04_planning/ADR/`，而那一面是空的**——
        帶標記的站點全數落在舊的兩個 glob 內，ADR 一處都沒有，也永遠不會有
        （`ADR-XPLAT-006` 已裁定不得給 ADR 補標記）。於是本格當時斷言的是「檔案被讀進來
        了」，而不是「有東西被判到」，read 起來卻像後者。ADR glob 已移除，改由本格第一段
        釘住「不准再加回來」——要加回來得先有一個不與該 ADR 打架的載體。
        """
        docs = guard_total_docs_in_worktree()
        self.assertTrue(
            [rel for rel in docs if "_HANDOFF.md" in rel],
            "擴面沒生效：掃描面內找不到任何交棒書——glob 寫壞或檔名慣例變了；"
            f"現行掃描面＝{_GUARD_TOTAL_DOC_GLOBS}")
        self.assertEqual(
            # 鍵由 guard_total_docs_in_worktree() 的 as_posix() 產生，非 os.sep
            [rel for rel in docs if "/ADR/" in rel], [],  # posix-abs-ok: as_posix 鍵
            "ADR 又被加回掃描面了——它在標記機制下結構上零站點（ADR-XPLAT-006 裁定不得補"
            "標記），而該目錄內僅有的三元組是刻意寫壞的注入語料 ⇒ 加回來只會讓下一個讀者"
            "以為 ADR 有人對帳（F3／B-2 立案的「有鎖在守假話」本體）。真的要納入，"
            "請先給它一個不與 ADR-XPLAT-006 打架的載體，並在本格寫出那個載體是什麼")
        self.assertEqual(
            doc_guard_total_problems(
                docs, sum(_FROZEN_GUARD_LINES.values()), self._latest_round()),
            [],
            "擴面後的文件側對帳出現違規——若是那幾行「為了指路而逐字寫出標記」的散文被算成"
            "站點，請確認 `_GUARD_TOTAL_MARK_RE` 仍只認 HTML 註解形態（R84 ZT-04 的收窄）")
        # 🔴 刻意**不綁本輪輪號**：那 4 行是 R83 的史料，會一直留在樹裡；綁本輪的話，
        # 下一次收尾重釘（輪號一換）就會讓這一格因為「找不到本輪的散文」而紅，而那與
        # 鑑別力毫無關係——一個會在正常流程下自己轉紅的鎖，實務上一定被關掉（ARCH-02）。
        prose = [
            (rel, lineno)
            for rel, text in docs.items()
            for lineno, line in enumerate(text.splitlines(), 1)
            if re.search(rf"{_GUARD_TOTAL_DOC_MARK}R\d+", line)
            and _GUARD_TOTAL_MARK_RE.search(line) is None
        ]
        self.assertTrue(
            prose,
            "掃描面內已經沒有任何「行內逐字提到標記＋輪號」的散文了——擴面當回合那些假紅的"
            "來源消失，本格的第二段斷言退化為恆綠。請改以合成語料保住鑑別力，"
            "或確認擴面是否已漂移")

    # ── R84 F3／B-2：交棒書的三元組（款(5)，不靠標記） ──────────────────────────
    def _live_handoff(self) -> tuple[str, tuple[int, int, int]]:
        """掃描面上「輪號最大且稽核痕跡算得出合計」的那份交棒書 ＋ 它該寫的三元組。

        刻意現查而不寫死 `R84_HANDOFF.md`：輪號每輪會變，寫死的那一刻本組注入就綁在
        某一輪上（本 repo 對「把當下的偶然事實寫成常數」已有多次判例）。
        """
        docs = guard_total_docs_in_worktree()
        agg: dict[int, tuple[int, int, int]] = {}
        for rnd, old, new, delta, _r in _GUARD_LINES_REPIN_LOG:
            if rnd[:1] == "R" and rnd[1:].isdigit():
                no = int(rnd[1:])
                agg[no] = ((agg[no][0], new, agg[no][2] + delta) if no in agg
                           else (old, new, delta))
        cands = [(int(m.group(1)), rel) for rel in docs
                 if (m := _HANDOFF_ROUND_RE.search(rel))
                 and int(m.group(1)) >= _HANDOFF_RECONCILE_SINCE
                 and int(m.group(1)) in agg]
        self.assertTrue(
            cands,
            "掃描面上找不到任何「輪號 ≥ 生效點且稽核痕跡有該輪列」的交棒書 ⇒ 款(5) 的"
            f"分母是空的、綠側恆綠。現行生效點＝R{_HANDOFF_RECONCILE_SINCE}")
        no, rel = max(cands)
        return rel, agg[no]

    def test_the_round_handoff_reconciles_its_guard_triplet(self) -> None:
        """綠側（真交棒書＋真稽核痕跡）：款(5) 對現況零違規，且分母非空。

        立案見 `handoff_guard_total_problems()` 的 docstring：ZT-04 把交棒書納入掃描面，
        但判準只認標記，而交棒書從來沒有人標 ⇒ 擴面對它自己立案的缺陷零效果
        （Architect 注入：把 `R84_HANDOFF.md` 三元組改成全錯值，舊判準回 `[]`）。
        """
        rel, want = self._live_handoff()
        self.assertEqual(
            handoff_guard_total_problems(
                guard_total_docs_in_worktree(), _GUARD_LINES_REPIN_LOG), [],
            f"交棒書側對帳不合規——最新一份是 {rel}，它該寫的是 "
            f"{want[0]} → {want[1]}（+{want[2]}）")

    def test_a_wrong_triplet_in_the_real_handoff_is_red(self) -> None:
        """🔴 注入（真檔、記憶體內改字）＝款(5) 的主牙：三元組寫錯 ⇒ 必紅。

        這正是 Architect 那筆 blocking 的複現：同一個注入在舊判準（`doc_guard_total_
        problems()`）下回 `[]`，因為交棒書一個標記都沒有。本格改用檔名輪號當錨，
        所以「沒人記得標」不再等於「沒有東西可判」。

        注入刻意**只改數字、保留三元組形態**：真實失效形態是「重釘了、交棒書沒跟上」，
        那時檔上仍有一組看起來很像的數字。把三元組整組刪掉是另一種形態（誠實劃界寫在
        判準的 docstring 裡：那等於不再宣稱，本款不管）。
        """
        rel, want = self._live_handoff()
        docs = guard_total_docs_in_worktree()
        bad = dict(docs, **{rel: _GUARD_TOTAL_TRIPLE_RE.sub(
            lambda m: f"{m.group(1)} → {int(m.group(2)) + 1}（{m.group(3)}{m.group(4)}",
            docs[rel])})
        self.assertNotEqual(bad[rel], docs[rel],
                            f"注入沒有改到任何位元組（{rel} 內讀不出三元組？）⇒ 下面恆綠")
        problems = handoff_guard_total_problems(bad, _GUARD_LINES_REPIN_LOG)
        self.assertTrue(
            any("[交棒書未對帳]" in p and rel in p for p in problems),
            f"交棒書把 {want[0]} → {want[1]}（+{want[2]}）寫錯竟然放行 ⇒ ZT-04 擴面依然"
            f"只是「檔案被讀進來了」；實得：{problems}")

    def test_the_handoff_criterion_is_deliberately_not_retroactive(self) -> None:
        """射程鎖＋假紅實量：生效點之前的交棒書一律不判，且**它們確實一個三元組都沒有**。

        兩段缺一不可：只驗「不判」的話，判準若寫錯成全不判也照樣綠；第二段直接量磁碟，
        把「假紅存量 0」由交件宣稱升為可重跑的事實（同鐵律四：宣稱要附當回合的量測）。
        """
        docs = guard_total_docs_in_worktree()
        old = {rel: text for rel, text in docs.items()
               if (m := _HANDOFF_ROUND_RE.search(rel))
               and int(m.group(1)) < _HANDOFF_RECONCILE_SINCE}
        self.assertTrue(old, "掃描面上沒有任何生效點之前的交棒書 ⇒ 本格證不了不追溯")
        self.assertEqual(
            handoff_guard_total_problems(old, _GUARD_LINES_REPIN_LOG), [],
            "款(5) 追溯到了生效點之前——那幾份交棒書當年根本沒有寫過這個數字，"
            "回頭補寫等於改寫史料")
        carriers = {rel: len(_GUARD_TOTAL_TRIPLE_RE.findall(text))
                    for rel, text in old.items()}
        self.assertEqual(
            [rel for rel, n in carriers.items() if n], [],
            f"生效點之前的交棒書已經出現三元組了（實得 {carriers}）——立案當回合實測全為 0，"
            "若這是真的新增，請重新量一次假紅存量再決定要不要把生效點往前挪")

    def test_a_marked_line_without_the_triple_is_red_and_the_judgment_is_not_always_red(
            self) -> None:
        """合成語料：標了卻讀不出三元組 ⇒ `[形態不符]`；正確形態 ⇒ 空清單（證明非恆紅）。

        合成而非真文件的理由與款(9) 那一格相同——要造「標記在、三元組不在」這種半套形態，
        在真文件上就得先把正確的那一行弄壞，而那正是上面兩支已經在做的事。
        """
        good = {"a.md": "x <!-- guard-total:R99 --> 1000 → 1500（**+500**）",
                "b.md": "y <!-- guard-total:R99 --> 1000 → 1500（+500 兩次重釘）"}
        self.assertEqual(doc_guard_total_problems(good, 1500, "R99"), [],
                         "本款對正確形態判紅 ⇒ 恆紅的鎖會被關掉")
        vague = dict(good, **{"a.md": "x <!-- guard-total:R99 --> 淨額請見附錄"})
        self.assertTrue(
            any("[形態不符]" in p for p in doc_guard_total_problems(vague, 1500, "R99")),
            "標了卻讀不出三元組竟然放行 ⇒ 標記變成一句不必兌現的宣告")

    def test_two_marks_in_one_file_are_still_one_site(self) -> None:
        """DEF-200-166：「兩邊都寫得出來」數的是**相異檔數**——同檔兩行＝刪一檔即關判準。"""
        same = {"a.md": "x <!-- guard-total:R99 --> 1000 → 1500（**+500**）\n"
                        "y <!-- guard-total:R99 --> 1000 → 1500（+500 兩次重釘）"}
        self.assertTrue(
            any("[未登記]" in p for p in doc_guard_total_problems(same, 1500, "R99")),
            "同一份檔擠兩行標記竟然滿足兩站點門檻——R87／R89~R96 九輪就是這樣全綠的")

    def test_the_criterion_is_deliberately_not_retroactive(self) -> None:
        """射程鎖：`_NET_DELTA_ACCOUNTING_SINCE` 之前的輪次不受款(9) 管，**這是刻意的**。

        理由不是寬容，是**兩道鎖的合法動作互為對方違規**（R76 Scan-H⑥ 的同型）：現存每一
        列都落在款(7) 的凍結前綴內，替它們補上記號＝改寫既有列＝先撞 `[歷史被改寫]`，
        而 append-only 比款(9) 更根本。少了這一格，下一個人會把「舊列沒有記號」讀成漏洞
        並回頭補寫，當場踩爆指紋。
        """
        bare = "理由夠長夠長夠長夠長夠長夠長夠長夠長，沒有任何記號"
        old = (f"R{_NET_DELTA_ACCOUNTING_SINCE - 1}", 1000, 1500, 500, bare)
        new = (f"R{_NET_DELTA_ACCOUNTING_SINCE}", 1000, 1500, 500, bare)
        self.assertFalse(
            [p for p in repin_log_problems((old,), 1500) if "[未附刪除清單]" in p],
            "生效輪次之前的列被追溯判紅 ⇒ 補救動作會先撞 append-only 指紋，死路一條")
        self.assertTrue(
            [p for p in repin_log_problems((new,), 1500) if "[未附刪除清單]" in p],
            "生效輪次當輪就該有牙，否則這個常數只是把判準無限期延後")

    def test_every_per_file_list_named_by_a_real_row_exists_on_disk(self) -> None:
        """🔴 款(9) 的**射程另一半**：判準本身只看檔名形狀，真實性由本格對磁碟驗。

        為何分成兩處而不是把存在性塞進 `repin_log_problems()`：那支是**純函式**，合成注入
        （上面那幾格與 `[前綴過期]` 那一格）都拿虛構的 `CrossPlatform_R9x_*.md` 當語料；
        要求檔案存在會讓合成語料全部翻紅，於是判準的紅綠自證就得先在磁碟上造檔——測試
        造出真檔來滿足自己的判準，那是本 repo 最不想要的形狀。
        ⇒ 形狀歸純函式、存在性歸這一格（只掃**真表**）。少了這一格，款(9) 可以用一個
        從來不存在的檔名滿足——那正是本 repo 反覆在治的幽靈引用。
        """
        named = sorted({
            m.group(0) for _rnd, _o, _n, _d, reason in _GUARD_LINES_REPIN_LOG
            for m in _PER_FILE_LIST_RE.finditer(reason)})
        self.assertTrue(named, "真表裡一份逐檔清單都沒指名——款(9) 從未真的被滿足過？")
        missing = [n for n in named if not (_REPO / "docs" / "06_quality" / n).is_file()]
        self.assertEqual(
            missing, [],
            f"稽核列指名的逐檔清單在 docs/06_quality/ 找不到：{missing}——"
            "款(9) 被一個不存在的檔名滿足了（幽靈引用），逐檔淨額實際上沒有家")

    # ── R79 收斂包：append-only 由散文變成機械事實 ────────────────────────────
    def test_collapsing_the_whole_history_into_one_row_is_red(self) -> None:
        """🔴 注入＝R79 掃描實測的繞道：把整段歷史壓成一列、起點改成任意數字。

        修前實況（實測逐字）：`(("R79", 54188, 90000, 35812, 理由),)` ＋ frozen_total=90000
        餵進本判準回 `[]`、`rc=0`——(1)~(5) 五款全部沉默。而本表存在的唯一理由就是
        「讓淨額在結構上不可能缺席」；壓平歷史比不補一列更難看見，因為表上永遠有一列。
        兩款各自獨立說話：`[歷史變短]`（列數）與 `[歷史被改寫]`（內容指紋）。
        """
        collapsed = (("R79", 54188, 90000, 35812,
                      "把兩列合併成一列，順手把起點改成一個好看的數字"),)
        problems = repin_log_problems(
            collapsed, 90000,
            history_digest=_REPIN_LOG_HISTORY_SHA256,
            prefix_len=_REPIN_LOG_FROZEN_PREFIX_LEN,
            max_unfrozen_tail=_REPIN_LOG_MAX_UNFROZEN_TAIL)
        self.assertTrue(
            any("[歷史變短]" in p for p in problems),
            f"整段歷史被壓成一列仍未轉紅 ⇒ append-only 還是一句散文；實得：{problems}")

    def test_editing_an_existing_row_in_place_is_red(self) -> None:
        """注入：**只**改前綴內某一列的一個字（列數不變、算術仍自洽）⇒ 只有 `[歷史被改寫]` 說話。

        這是「壓平歷史」的隱形版本：列數對、首尾相接、與凍結表也對得上，前五款全綠。
        零串音斷言在此特別重要——若 `[歷史變短]` 也跟著響，就證明不了是指紋在說話。
        """
        rows = list(_GUARD_LINES_REPIN_LOG)
        head = rows[0]
        rows[0] = (head[0], head[1], head[2], head[3], head[4] + "（有人事後補了一句）")
        problems = repin_log_problems(
            tuple(rows), sum(_FROZEN_GUARD_LINES.values()),
            history_digest=_REPIN_LOG_HISTORY_SHA256,
            prefix_len=_REPIN_LOG_FROZEN_PREFIX_LEN,
            max_unfrozen_tail=_REPIN_LOG_MAX_UNFROZEN_TAIL)
        self.assertEqual(
            [p for p in problems if "[歷史被改寫]" in p], problems,
            f"應恰為 [歷史被改寫] 一款（零串音）；實得：{problems}")

    def test_coordinated_rewrite_defeats_the_digest_alone(self) -> None:
        """R-10 前提自證：**同時**改前綴內一列並重算指紋 ⇒ `[歷史被改寫]` 不再說話
        （對照上一支：只改內容不改指紋才抓得到）。證明「資料與指紋同檔同 commit」
        本身防不住協同改寫，`frozen_prefix_rewrite_problems()` 的存在理由正是補這格。
        """
        rows = list(_GUARD_LINES_REPIN_LOG)
        head = rows[0]
        rows[0] = (head[0], head[1], head[2], head[3], head[4] + "（協同改寫：連指紋一起改）")
        coordinated_digest = repin_log_history_digest(tuple(rows), _REPIN_LOG_FROZEN_PREFIX_LEN)
        problems = repin_log_problems(
            tuple(rows), sum(_FROZEN_GUARD_LINES.values()),
            history_digest=coordinated_digest, prefix_len=_REPIN_LOG_FROZEN_PREFIX_LEN,
            max_unfrozen_tail=_REPIN_LOG_MAX_UNFROZEN_TAIL)
        self.assertEqual(problems, [], "前提不成立：協同改寫本該讓既有判準沉默")

    def test_frozen_prefix_rewrite_ledger_chains_and_validates_def_ids(self) -> None:
        """R-10 主牙：上一支證明沉默之後，`frozen_prefix_rewrite_problems()` 必須用
        **跟資料不同檔**的錨點把協同改寫抓出來。五格併一支（比照本檔既有體例
        `test_a_miscomputed_net_or_a_broken_chain_is_red`）：缺一列／鏈路完整＋DEF-ID
        查得到（綠對照組）／DEF-ID 虛構／斷鏈／格式不合法／最後一列沒接上現值。
        """
        launch12, new_sha = _FROZEN_PREFIX_REWRITE_LAUNCH_SHA[:12], "d" * 64
        good = ("R100", launch12, new_sha[:12], "DEF-1-001")
        self.assertTrue(any("[缺一即紅]" in p for p in frozen_prefix_rewrite_problems(
            (), current_sha="c0ffee" * 10 + "abcd")))
        self.assertEqual(frozen_prefix_rewrite_problems(
            (good,), current_sha=new_sha, def_id_exists=lambda _d: True), [])
        self.assertTrue(any("[DEF-ID 查無此列]" in p for p in frozen_prefix_rewrite_problems(
            (good,), current_sha=new_sha, def_id_exists=lambda _d: False)))
        broken = ("R100", "0" * 12, new_sha[:12], "DEF-1-001")
        self.assertTrue(any("[斷鏈]" in p for p in frozen_prefix_rewrite_problems(
            (broken,), current_sha=new_sha, def_id_exists=lambda _d: True)))
        bad_id = ("R100", launch12, new_sha[:12], "not-a-defid")
        self.assertTrue(any("[DEF-ID 格式不合法]" in p for p in frozen_prefix_rewrite_problems(
            (bad_id,), current_sha=new_sha, def_id_exists=lambda _d: True)))
        stale = ("R100", launch12, "a" * 12, "DEF-1-001")
        self.assertTrue(any("[未接上現值]" in p for p in frozen_prefix_rewrite_problems(
            (stale,), current_sha="b" * 64, def_id_exists=lambda _d: True)))
        # wiring：真實常數此刻必須合規——落地時指紋與啟動快照逐字相同，帳本理應是空的。
        real = frozen_prefix_rewrite_problems(
            _FROZEN_PREFIX_REWRITE_LEDGER, current_sha=_REPIN_LOG_HISTORY_SHA256)
        self.assertEqual(real, [], real)

    def test_appending_one_row_keeps_the_history_digest_stable(self) -> None:
        """對照組：**追加一列**是每輪的正常動作，指紋與判準都不得因此說話。

        少了這一條，上面兩支「注入必紅」可能只是因為指紋對任何變動都紅——那樣的鎖
        會讓每一輪的正常重釘都得改一個 sha 常數，實務上一定被改寬。
        """
        total = sum(_FROZEN_GUARD_LINES.values())
        #: 🔴 R85 收尾訂正：合成列的淨額由 `+5` 改為 **0**。原值讓這支**對照組**自己撞上款(11)
        #: 的連續上升上限——真表 R84／R85 已是連兩輪上升（`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`
        #: ＝2），再合成一列上升就是第三輪 ⇒ `[只升不降]` 說話，而本測試的主題是**指紋穩定性**，
        #: 兩件事被混在一起。改用 0 不是為了讓它變綠：**下一輪真正合法的重釘本來就必須非上升**
        #: （款(11) 現況如此），所以 0 才是「正常的下一輪」該有的形狀，`+5` 反而是不合法的合成。
        #: 🔴 鑑別力未減：款(11) 自己的主牙住 `test_a_third_consecutive_rising_round_is_red`
        #: （三格一組：兩輪綠／三輪紅／中間插一輪 ≤0 又綠），本測試從來不是它的載具。
        appended = (*_GUARD_LINES_REPIN_LOG,
                    ("R99", total, total, 0,
                     "合成的下一輪重釘，理由長度足以通過 [無理由] 與 [未附刪除清單] 兩款"
                     "[非淨減法輪] CrossPlatform_R99_Scan_Findings.md"))
        self.assertEqual(
            repin_log_history_digest(appended, _REPIN_LOG_FROZEN_PREFIX_LEN),
            _REPIN_LOG_HISTORY_SHA256,
            "追加一列竟然改變了前綴指紋 ⇒ 每輪都要改 sha 常數，這道鎖會被關掉")
        self.assertEqual(
            repin_log_problems(
                # 🔴 表總量必須逐字等於合成列的**新總量**（款「未對帳」判的就是這件事）。
                # R85 訂正合成列淨額時漏改這裡，於是這支對照組被自己要對照的那一款打中
                # ——正是它存在的理由：判準真的會說話。
                appended, total,
                history_digest=_REPIN_LOG_HISTORY_SHA256,
                prefix_len=_REPIN_LOG_FROZEN_PREFIX_LEN,
                max_unfrozen_tail=_REPIN_LOG_MAX_UNFROZEN_TAIL),
            [], "追加一列是正常動作，不得有任何一款說話")

    def test_letting_the_unfrozen_tail_grow_is_red(self) -> None:
        """注入：連續追加兩輪而不把前一列納入前綴 ⇒ `[前綴過期]` 必紅。

        這一款是「固定長度前綴」這個設計付出的代價的**上限器**：沒有它，尾巴會越長
        越長，久了整段又回到可自由改寫的狀態——那正是本節要治的病換個速度重演。
        """
        total = sum(_FROZEN_GUARD_LINES.values())
        reason = "合成列，理由長度足以通過 [無理由] 那一款的下限"
        two = (*_GUARD_LINES_REPIN_LOG,
               ("R98", total, total + 1, 1, reason),
               ("R99", total + 1, total + 2, 1, reason))
        problems = repin_log_problems(
            two, total + 2,
            history_digest=_REPIN_LOG_HISTORY_SHA256,
            prefix_len=_REPIN_LOG_FROZEN_PREFIX_LEN,
            max_unfrozen_tail=_REPIN_LOG_MAX_UNFROZEN_TAIL)
        self.assertTrue(any("[前綴過期]" in p for p in problems), problems)
        self.assertFalse(
            [p for p in problems if "[歷史被改寫]" in p],
            "追加不該驚動指紋那一款，否則證明不了是尾巴長度在說話（零串音）")

    def test_the_frozen_prefix_covers_every_row_this_round(self) -> None:
        """自緊：本輪落地時，凍結前綴必須**涵蓋現有全部列**。

        寬限一列是給「追加當輪」用的，不是給收輪者用的：收輪者手上就有 `--print-guard-lines`
        印出的草稿，沒有理由留一列不受保護。留餘裕就是替下一次改寫預先開門
        （同 `_FROZEN_GUARD_LINES` 的 `[基準過時]`）。
        """
        self.assertEqual(
            _REPIN_LOG_FROZEN_PREFIX_LEN, len(_GUARD_LINES_REPIN_LOG),
            "凍結前綴沒有涵蓋全部稽核列——收輪時請把 _REPIN_LOG_FROZEN_PREFIX_LEN "
            "調成現有列數並重釘 _REPIN_LOG_HISTORY_SHA256"
            "（`--print-guard-lines` 會印出兩個值）")

    def test_a_miscomputed_net_or_a_broken_chain_is_red(self) -> None:
        """注入②③：淨額算錯／中間漏記一次重釘，各自必紅（且是對的那一款）。"""
        reason = "理由夠長夠長夠長夠長夠長夠長夠長夠長"
        bad_net = (("Rx", 100, 200, 99, reason),)
        self.assertTrue(any("[淨額不符]" in p for p in repin_log_problems(bad_net, 200)))
        broken = (("Rx", 100, 200, 100, reason), ("Ry", 300, 400, 100, reason))
        self.assertTrue(any("[斷鏈]" in p for p in repin_log_problems(broken, 400)))

    def test_an_empty_or_unreasoned_log_is_red(self) -> None:
        """注入④⑤：整張表被刪掉／理由欄敷衍了事，都不得靜默通過。"""
        self.assertTrue(any("[空表]" in p for p in repin_log_problems((), 0)))
        self.assertTrue(any("[無理由]" in p for p in repin_log_problems(
            (("Rx", 0, 1, 1, "重釘"),), 1)))

    def test_a_correct_repin_is_green(self) -> None:
        """對照組：算術自洽、首尾相接、與凍結表對得上 ⇒ 綠。

        少了這一支，上面四支「注入必紅」可能只是因為本判準恆紅（無鑑別力）。
        """
        reason = "把兩支鎖檔合併，淨額為零但鍵集合改變，故一併重釘"
        good = (("Rx", 100, 200, 100, reason), ("Ry", 200, 190, -10, reason))
        self.assertEqual(repin_log_problems(good, 190), [])

    # ── R78 ARCH-04：兩個掃描面的涵蓋關係必須有人算 ──────────────────────
    def test_the_two_surfaces_have_no_coverage_gap(self) -> None:
        """檔數面（遞迴 `test_*.py`）的每一支都必須被行數面（非遞迴 `*.py`）數到。

        WHY：閘門會跑、行數棘輪卻量不到的檔＝它的成長不會讓任何東西轉紅。R77 宣稱這件事
        由 `guard_baseline_gaps()` 證明，而那個函式當時並不存在（R78 ARCH-04）。
        """
        gaps = guard_baseline_gaps()
        self.assertEqual(
            gaps, [],
            f"這幾支鎖檔在閘門的收集面內、卻不在行數棘輪的量測面內：{gaps}——"
            "它們可以無限長大而不會有任何東西轉紅。修法：移回 tools/tests/ 頂層，"
            "或連同 ADR §4.3 的現查指令一起把行數面改成遞迴",
        )

    def test_the_gap_detector_is_not_vacuous(self) -> None:
        """自錨：涵蓋關係函式必須真的在比兩個面，而不是恆回空清單。

        用**真實**的兩個面做正控：檔數面非空、且它的每一支都能在行數面找到同名鍵——
        兩個條件同時成立，上一支的「零缺口」才是量出來的，不是 glob 寫壞後的假綠。
        """
        files = guard_files_in_worktree()
        line_face = guard_lines_in_worktree()
        self.assertTrue(files, "檔數面為空 ⇒ 涵蓋關係恆真通過（fail-open）")
        self.assertTrue(line_face, "行數面為空 ⇒ 涵蓋關係會把每一支都判成缺口")
        self.assertIn(
            _SELF_REL.rsplit("/", 1)[-1], line_face,
            "行數面連本檔都沒數到——glob 寫壞了？",
        )


# ================================================================ ADR §9.1／掃描維度 常設自檢（SC-*）
# SA-R67-03 立案（grep 指令零可執行消費者＝非活體守門）、宿主選擇（DEF-101-561③ 棘輪）
# 與 shell 規格搬 Python 時刻意改掉的三處語意，全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈ADR §9.1 常設自檢落地沿革〉節。
# 一處**刻意不改**：SC-2／SC-3／SC-5 的區段界線逐字複刻 `awk` 的 range pattern 語意
# （含兩端界線列、且區段結束後可再次觸發），見 `awk_range()`——判準搬家不得順手改語意。
_ADR2 = (_REPO / "docs" / "04_planning" / "ADR"
         / "ADR-XPLAT-002-platform-surface-reduction.md")
_SCAN_DIMS = _REPO / "docs" / "06_quality" / "CrossPlatform_Scan_Dimensions.md"

# 規格出處標籤。ADR 側宣告的 `# SC-N` 集合必須與本檔實作的集合**逐字相等**（雙向），
# 由 `TestSection91SpecIsBoundToTheseLocks` 機械綁定；條數一律現查，本檔不得寫死
# ——SC-6 管的正是「把 §9.1 的條數寫死」這件事，本段自己先遵守。
_SPEC_ADR2 = "ADR-XPLAT-002 §9.1"
_SPEC_SCAN = "CrossPlatform_Scan_Dimensions.md〈常設自檢〉"

# §8 的區段界線。SC-2／SC-3／SC-5 **一律**只掃「交棒表本體」（`## 8.` 起至 `### 8.1` 止）：
# §8 表頭規則 1／3 的標的逐字就是表內的「承接者欄」與「完成判準欄」，規則 2 的容器是 §8.1。
#
# 🔴 R67 round 4（SA2-R67-01）把 SC-2／SC-3 的下界由 `_SEC8_END_ALL` 收窄到此：原版掃 §8
# 全區會讓 §8.3 逐字保全散文區落入無豁免射程 ⇒ 永紅；豁免路徑刻意沿用既有出口（原句移進
# §8.3），不新加標記。後果列舉與拒收理由全文搬至 CrossPlatform_Guard_Line_History.md
# 〈SC-2/3/5 射程收窄 WHY〉節。`_SEC8_END_ALL` 保留給 `test_the_scan_surface_did_not_collapse`
# ——以「全區嚴格長於本體」反證 `### 8.1` 界線還活著。
_SEC8_START = r"^## 8\."
_SEC8_END_ALL = r"^## 9\."
_SEC8_END_TABLE = r"^### 8\.1"

# ADR §9.1 的區段界線與 SC 條目宣告樣式（`# SC-1  標的：…`）。
_ADR2_SEC91_HEAD = "### 9.1 "
_ADR2_SEC91_END = "## 10."
_SC_DECL_RE = re.compile(r"^# (SC-\d+)\b", re.M)
# 掃描維度檔〈常設自檢〉的區段界線。
_SCAN_SELFCHECK_HEAD = "## 常設自檢"
_SCAN_SELFCHECK_END = "## 邊界"


class Corpus(NamedTuple):
    """SC-* 各條的掃描面。注入測試一律以 `_replace()` 換掉其中一份，**不碰磁碟**。"""

    adr2: str
    adr1: str
    scan: str
    family: tuple[tuple[str, str], ...]
    governance: tuple[tuple[str, str], ...]
    wide: tuple[tuple[str, str], ...]


def read_governance() -> list[tuple[str, str]]:
    """具名治理文件的 `(檔名, 內容)`，**排除維度表本身**。

    🔴 為何 SC-7 的使用面非擴到這裡不可（R69 P3；修前實況）：R68 把整輪掃描發現以
    「主檔留指針、詳情外置」寫進 `CrossPlatform_R68_Scan_Findings.md`，帳本主檔只剩一列
    指針。SC-7 當時的使用面**只有帳本家族**，於是「某輪用了一個維度表沒定義的代號」這個
    病只要換一種放法（放進詳情外置檔）就整個逸出——與它原本要治的 `Scan-M` 是同一個病、
    只是換皮。擴的是**既有 SSOT**（`ADL._GOVERNANCE_DOCS`，也就是 `--check` 判準④⑥ 與
    體積守門共用的那一份清單），不是本檔自生的第二條 glob；新的詳情外置檔一旦建立，
    `unregistered_governance_docs()` 會逼它登記進那份清單，於是**自動**進入本掃描面。

    ⚠️ 刻意排除維度表自己：它是**定義側**，把它算進使用側會把定義變成自我循環，且它的
    散文為了說明長名截斷邊界而逐字寫著 `Scan-S`／`Scan-P`（實測：納入即誤紅這兩個）——
    誤報的鎖最後一定被加豁免繞過，比沒有鎖更糟。
    """
    return [
        (p.name, p.read_text(encoding="utf-8-sig"))
        for p in ADL._GOVERNANCE_DOCS
        if p.name != _SCAN_DIMS.name
    ]


_ADR3 = (_REPO / "docs" / "04_planning" / "ADR"
         / "ADR-XPLAT-003-autoclaude-platform-capability-layer.md")
# SC-9 的掃描面：**平台覆蓋宣稱會出現的所有活文件與源碼**。
#
# 🔴 為何非擴到這麼寬不可（DEF-101-757）：SC-4 的掃描面只有兩份 ADR，於是同一句錯話換一個
# 檔案就整個逸出——R69/R70 把「Windows 零真機」寫得橫跨 docs 與 `.py`（註解與 docstring 都有）
# 而零告警。平台覆蓋宣稱不挑檔案住，鎖就不能挑檔案掃。
_SC9_DIRS: tuple[str, ...] = ("AutoClaude/autoclaude", "AutoClaude/tests", "tools")


def read_wide() -> list[tuple[str, str]]:
    """SC-9 掃描面的 `(相對路徑, 內容)`。枚舉全部走既有 SSOT／glob，不手列檔名。"""
    paths = [_ADR2, _ADR3, _ADR, _SCAN_DIMS]
    paths += list(ADL._GOVERNANCE_DOCS) + list(ADL._family_files())
    # 🔴 `rglob` 而非 `glob`（R72）：迭代計畫結案後會搬進 `04_planning/Archive/`，
    # 用非遞迴 glob 等於「一歸檔就退出 SC-9 掃描面」——那正是 DEF-101-757 的形狀
    # （同一句錯話換個位置就整個逸出），只是這次搬走它的是歸檔慣例而不是作者。
    # 落地前實測：把 Archive/ 併入後 SC-9 problems 仍為 0，故納入不引入存量紅。
    paths += sorted((_REPO / "docs" / "04_planning").rglob("AutoSDD_improving_*.md"))
    for rel in _SC9_DIRS:
        paths += sorted((_REPO / rel).rglob("*.py"))
    out: dict[str, str] = {}
    root = _REPO.resolve()
    for p in paths:
        if not p.is_file():
            continue
        rel_path = p.resolve().relative_to(root).as_posix()
        if rel_path not in out:
            out[rel_path] = p.read_text(encoding="utf-8-sig")
    return list(out.items())


def read_corpus() -> Corpus:
    """現查掃描面。帳本家族枚舉仍走 `read_family()`（＝`ADL._family_files()` 家族 SSOT）；
    治理文件枚舉走 `ADL._GOVERNANCE_DOCS`（同一份具名清單 SSOT）。"""
    return Corpus(
        adr2=_ADR2.read_text(encoding="utf-8-sig"),
        adr1=_ADR.read_text(encoding="utf-8-sig"),
        scan=_SCAN_DIMS.read_text(encoding="utf-8-sig"),
        family=tuple(read_family()),
        governance=tuple(read_governance()),
        wide=tuple(read_wide()),
    )


def awk_range(text: str, start: str, end: str) -> list[tuple[int, str]]:
    """複刻 `awk '/start/,/end/'` 的逐行選取語意，回傳 `(原始行號, 行內容)`（行號自 1 起）。

    為何不用既有的 `_slice_section()`：後者以 `startswith` 取**單一**區段，而 awk 的 range
    pattern 在區段結束後**可再次觸發**，且「同一列同時符合兩端」時只選該列。SC-2／SC-3／SC-5
    的規格逐字寫的是 awk 形態，判準搬家不得順手改語意（改了就不再是「照抄即可」的規格）。
    抓不到區段時回空 list——**呼叫端必須把空 list 當成掃描面崩塌回報**，見 `_section8_hits()`。
    """
    start_re, end_re = re.compile(start), re.compile(end)
    out: list[tuple[int, str]] = []
    inside = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if not inside:
            if start_re.search(line):
                out.append((lineno, line))
                inside = not end_re.search(line)
            continue
        out.append((lineno, line))
        if end_re.search(line):
            inside = False
    return out


def _section8_hits(
    adr2: str, end: str, pattern: re.Pattern[str], sc: str, what: str
) -> list[str]:
    """§8 某種切法內的樣式命中；**區段抽不到就回報違規**，不得靜默零命中假綠。"""
    rows = awk_range(adr2, _SEC8_START, end)
    if not rows:
        return [
            f"{sc}：ADR-XPLAT-002 抓不到 {_SEC8_START!r}…{end!r} 這段區間 — 掃描面已崩塌"
            "（章節標題被改寫？），本判準拒絕靜默通過；請同步本檔的 _SEC8_* 界線常數"
        ]
    return [
        f"{sc} ADR-XPLAT-002:{lineno}：{what} ← {line.strip()}"
        for lineno, line in rows
        if pattern.search(line)
    ]


def _line_hits_with_waiver(
    docs: tuple[tuple[str, str], ...], pattern: str | re.Pattern[str],
    waiver: str, sc: str, what: str,
) -> list[str]:
    """逐行掃 `docs`，命中 `pattern` 且**同一行**沒有 `waiver` 標記者即違規。

    🔴 豁免必須**逐行**判定：這兩份 ADR 內有**單行巨欄**（表格狀態欄一格上千字、在檔案裡
    就是一行），若容許跨行豁免，一個標記會把整格放行。落地本段的前一包第一版即踩過這個坑，
    改成「逐字原句移到散文區、不掛豁免」才修掉。

    🔴 已掛豁免者另要求**標記後面必須有理由**（規格逐字：「掛豁免**並寫理由**」「理由必須
    寫在標記後面」）——`grep` 形態表達不了這一條，搬進 Python 才做得到。射程刻意只到
    「**同時**含違規 token 與標記」的行：規格自己的 grep 指令與說明散文也會出現標記字串，
    把它們一起判進來就是自製誤報，而誤報的鎖最後一定被加豁免繞過（比沒有鎖更糟）。
    """
    def hit(line: str) -> bool:
        if isinstance(pattern, re.Pattern):
            return pattern.search(line) is not None
        return pattern in line

    problems = []
    for label, text in docs:
        for lineno, line in enumerate(text.splitlines(), 1):
            if not hit(line):
                continue
            if waiver not in line:
                problems.append(f"{sc} {label}:{lineno}：{what} ← {line.strip()}")
                continue
            reason = line.split(waiver, 1)[1].strip().removesuffix("-->").strip()
            if not reason:
                problems.append(
                    f"{sc} {label}:{lineno}：豁免標記 `{waiver}` 後面沒有理由 — "
                    f"無理由的豁免就是後門，不是豁免 ← {line.strip()}"
                )
    return problems


def _adr_pair(c: Corpus) -> tuple[tuple[str, str], ...]:
    return (("ADR-XPLAT-002", c.adr2), ("ADR-XPLAT-001", c.adr1))


# ---- SC-1：兩份 ADR 不得殘留未加引號的 `--include=<glob>` --------------------------------
_SC1_BAD_TOKEN = "--include=*"
_SC1_WAIVER = "zsh-glob-ok:"


def sc1_no_unquoted_include_glob(c: Corpus) -> list[str]:
    """WHY：zsh 預設 `nomatch`，未加引號的 glob 在 **grep 被呼叫之前**就讓整條指令 abort
    （DEF-101-479／507／508 同族）。ADR 是寫給未來每一輪照抄重跑的，抄到壞形態的人看到的
    是與判準本身無關的怪錯。豁免標記沿用 `test_extras_quoting_zsh_safety.py` 的語言中立慣例。
    """
    return _line_hits_with_waiver(
        _adr_pair(c), _SC1_BAD_TOKEN, _SC1_WAIVER, "SC-1",
        f"未加引號的 {_SC1_BAD_TOKEN}（zsh nomatch）；要逐字引述壞形態請在**同一行**"
        f"掛 `{_SC1_WAIVER} <理由>`",
    )


# ---- SC-2：§8 全區不得出現 `**R<數字>+**` 形態的承接者 -----------------------------------
_SC2_RE = re.compile(r"\*\*R[0-9]+\+\*\*")


def sc2_no_open_ended_owner_in_section_8(c: Corpus) -> list[str]:
    """WHY：`**R<n>+**` 是**永不到期的開放下界**，任何一輪都「還沒到」⇒ 交棒列永遠不會逾期
    （§8 表頭規則 1）。射程＝§8 **交棒表本體**，因為規則 1 管的就是表內的承接者欄。

    🔴 射程自述訂正（SA2-R67-01 以注入實測**證偽**原文）：原 docstring 逐字寫「刻意只抓粗體
    形態：歷史列的刪除線與內文引述屬史料，不在射程內」。實測**只有前半為真**——`~~R64+~~`
    （純刪除線、未加粗）確實逃逸，但 `~~**R62+**~~`（刪除線包住粗體）仍被 `_SC2_RE` 命中，
    因為判準看的是內層那對星號。⇒ **刪除線不是豁免**。要逐字保全一句含粗體開放下界的原文，
    出口是把它移進 §8.3 散文區（本條止於 `### 8.1`），不是包一層刪除線了事。
    """
    return _section8_hits(
        c.adr2, _SEC8_END_TABLE, _SC2_RE, "SC-2",
        "§8 交棒表本體出現永不到期的開放下界承接者"
        "（規則 1 要求寫存在的輪次或明標「未指派」；逐字保全的原句請移入 §8.3 散文區）",
    )


# ---- SC-3：§8 全區不得寫死千分位量測常數 -------------------------------------------------
_SC3_RE = re.compile(r"[0-9]{1,3},[0-9]{3}")


def sc3_no_thousand_separated_constant_in_section_8(c: Corpus) -> list[str]:
    """WHY：§8 表頭規則 3 明文「完成判準欄禁止寫死量測常數」——寫死的數字必過期，取值一律
    走 §8.2 的 M-1~M-3 現查指令。同 `run_root_unittests.py::MIN_TESTS` 註記的 (b) 條紀律。

    射程＝§8 **交棒表本體**（規則 3 管的就是表內的完成判準欄）；`### 8.1` 之後的子節刻意排除，
    理由與 SC-2 同——§8.2 本來就在登載現查指令，§8.3 是逐字保全散文區（SA2-R67-01）。
    ⚠️ 誠實劃界：本條只掃 §8 交棒表本體，**§4.3／§4.3.1 兩節裡的量測數字沒有機械承接者**
    （ARCH-R67R2-01 即在該處抓到一個當輪就過期的成長率常數）。那是**已劃界的殘餘**、不是
    隱形缺口，§9.1 邊界 (d) 已同步登記。
    """
    return _section8_hits(
        c.adr2, _SEC8_END_TABLE, _SC3_RE, "SC-3",
        "§8 交棒表本體寫死了千分位量測常數（規則 3 要求改寫成 §8.2 的現查指令）",
    )


# ---- SC-4：兩份 ADR 不得出現活的平台前提 -------------------------------------------------
_SC4_RE = re.compile(r"本機(?:是|有|沒有|沒|為|只有|上有)")
_SC4_WAIVER = "stale-premise-ok:"


def sc4_no_live_platform_premise(c: Corpus) -> list[str]:
    """WHY：把「當下這台機器是什麼平台」寫成 ADR 的常數，正是 §6 邊界 1 那句硬編前提能存活
    七輪的病灶本身（平台缺席是**輪次屬性**，不是文件常數）。訂正段必須逐字引述被推翻的原句
    才能讓讀者辨認版本，故提供同行豁免；動詞列舉的窄射程是規格已明載的邊界（ARCH-R67-02
    即因原版少列一個動詞而讓一句活的前提整輪存活）。
    """
    return _line_hits_with_waiver(
        _adr_pair(c), _SC4_RE, _SC4_WAIVER, "SC-4",
        f"疑似活的平台前提；訂正段的逐字引述請在**同一行**掛 `{_SC4_WAIVER} <理由>`",
    )


# ---- SC-9：不得出現「某平台零真機」的**無輪次界定**宣稱 -----------------------------------
#
# 🔴 **本條是 SC-4 已知射程缺口的補完，不是新發明**（DEF-101-757）。§9.1 邊界 (d) 逐字寫著
# SC-4「同義寫法（『零真機』『這台機器』…）**抓不到**」，`DEF-101-643` 的結案敘述也逐字
# 重複一次——**缺口被寫成政策、而不是被補上**。代價已實測：R69/R70 把「Windows 零真機」
# 寫得橫跨 docs 與 `.py` 且零告警，主控再據以向使用者宣稱  # stale-premise-ok: 逐字保全原話
# 「Windows 側從未有真機輪」，  # stale-premise-ok: 同上，本條的立案樣本
# 被使用者當場以開發史駁回（`DEF-101-756`）。本 repo 自己在 `improving_103` §8.2 寫過的那句
# 在此第三次應驗：**被寫成政策的缺陷比沒被寫下的更難發現**。
#
# 判準的核心是**輪次界定**，不是「不准提平台」——這正是 `ADR-XPLAT-002` §6 邊界 1 的既有
# 裁決：「平台覆蓋是**輪次屬性**，不是治理文件的常數」。故
#   「本輪無 Windows 真機」   ＝ 合法（帶輪次界定；實測現存的這一類寫法全部屬此形）
#   「Windows 零真機」  ＝ 違規  # stale-premise-ok: 判準說明須逐字寫出要抓的形態
#                       （讀起來是永久屬性，而它是假的）
#
# 🔴 **射程是實測收斂出來的，不是想像的**（兩個方向都貼過輸出）：
#   - 只用「否定詞＋真機」：**52 命中**，其中「檔名零改動）＋真機取證」「無法真機驗證」
#     「有無真機量測」「無真機輪一律標 SKIP」這類**規則句與跨標點誤配**佔多數 ⇒ 噪音鎖。
#   - 加上「平台名須相鄰」＋「同行無輪次界定」＋間隔字元限縮為 `[A-Za-z0-9 有側過的]`：
#     **9 命中、零誤報**（全部是真違規或需具名豁免的逐字引述）。
#   - 另**刻意不納入**「這台機器」：實測命中裡**多數是誤報**（`test_ps_engine_ssot.py`
#     「說通則而非說這台機器」等），而 ADR 內真正該管的那一種已由 SC-4 的 `本機是/為` 覆蓋。
#     誤報的鎖最後一定被加豁免繞過，比沒有鎖更糟——本檔多處已判過。
#   - 同理**刻意不把 SC-4 的舊樣式擴到本條的寬掃描面**：實測那樣會多出**一整批誤報**
#     （`dev_start.py`「本機是否有 nightly 正在跑」這類與平台前提無關的散文）。
_SC9_CLAIM_RE = re.compile(
    r"(?:零|無|沒有|未曾|從未|不曾|沒)[A-Za-z0-9 有側過的]{0,12}(?:真機|實機)"
)
_SC9_PLATFORM_RE = re.compile(r"Windows|macOS|Mac\b|Darwin|win32|darwin|PowerShell")
_SC9_ROUND_SCOPE_RE = re.compile(
    r"本輪|該輪|當輪|這一輪|本次|本包|R\d{1,3}|某輪|每一輪|哪一輪|輪次|各輪"
)
_SC9_WAIVER = "stale-premise-ok:"
_SC9_NEAR = 18  # 平台名須落在命中詞前後這個字元窗內，才算「在講那個平台」


def sc9_no_unscoped_zero_real_machine_claim(c: Corpus) -> list[str]:
    """WHY 見上方區塊註解。回空 list ＝通過。

    豁免沿用 SC-4 的 `stale-premise-ok:`（**具名＋同行**）：訂正段必須能逐字引述被推翻的
    原句才讓讀者辨認版本，而整檔豁免會讓一個標記放行整份文件——本檔對單行巨欄已踩過。
    """
    problems: list[str] = []
    for rel, text in c.wide:
        for lineno, line in enumerate(text.splitlines(), 1):
            if _SC9_ROUND_SCOPE_RE.search(line):
                continue  # 帶輪次界定＝本 repo 明訂的正確寫法
            for m in _SC9_CLAIM_RE.finditer(line):
                window = line[max(0, m.start() - _SC9_NEAR):m.end() + _SC9_NEAR]
                if not _SC9_PLATFORM_RE.search(window):
                    continue
                if _SC9_WAIVER in line:
                    break
                problems.append(
                    f"SC-9 {rel}:{lineno}：無輪次界定的「某平台零真機」宣稱"
                    f"（平台覆蓋是輪次屬性，不是常數）；史料逐字引述請在**同一行**掛 "
                    f"`{_SC9_WAIVER} <理由>` ← {line.strip()[:160]}"
                )
                break
    return problems


# ---- SC-5：§8 交棒表本體不得出現外部環境當時狀態 -----------------------------------------
_SC5_RE = re.compile(r"停擺|帳單|帳務|額度")


def sc5_no_environment_state_in_the_handoff_table(c: Corpus) -> list[str]:
    """WHY（ARCH-R67-04）：交棒表寫的是「誰接、接什麼」，而外部環境當時狀態（服務中斷、
    計費、配額…）是會過期的**輪次資料**；混進交棒表就會讓一列因為環境敘述過期而整列失實。
    環境狀態一律登記在 §6 邊界 1 的逐輪覆蓋表，逐字保全的歷史原句移入 §8.3 散文區。
    射程刻意只到 `### 8.1`：8.1~8.3 是子節，不是交棒表本體。R67 round 4 起 SC-2／SC-3 也
    對齊到同一條界線（SA2-R67-01），§8.3 因此是這幾條共同的保全出口，而非只對本條有效。
    """
    return _section8_hits(
        c.adr2, _SEC8_END_TABLE, _SC5_RE, "SC-5",
        "§8 交棒表本體出現外部環境當時狀態字樣（請移入 §8.3 散文區或 §6 邊界 1 覆蓋表）",
    )


# ---- SC-6：ADR 全檔不得寫死 §9.1 的條數 --------------------------------------------------
# 🔴 R69（DEF-101-702／R68-27）：原樣式是**列舉式** `(?:三|四|五|六)條`，而 §9.1 的條數
# 早已成長到 8 ⇒ 今天唯一寫得出來的違規形態（「七條」「八條」「8 條」）全部漏抓，鎖對它
# 自己要守的那個數字失去鑑別力。改為**不依賴列舉**：任何 CJK 數字或阿拉伯數字（含中間的
# 半形／全形空白）緊鄰「不變式／可轉紅」即命中。實測對現行 ADR 全檔零誤報。
_SC6_RE = re.compile(
    r"[〇零一二三四五六七八九十百\d]+[\s ]*條.{0,12}(?:不變式|可轉紅)"
    r"|(?:不變式|可轉紅).{0,12}[〇零一二三四五六七八九十百\d]+[\s ]*條"
)


def sc6_no_hardcoded_invariant_count(c: Corpus) -> list[str]:
    """WHY（QA-R67-02）：一份自稱「搬進測試時逐字照抄即可」的規格若把自己的條目數寫錯，
    照著標題辦事的人會**少搬一條，而少搬哪一條無從判定**。理由與 §8 表頭規則 3 同源：
    寫死的數字必過期，而條數正是可現查的量（本檔的 `_SECTION_91_CHECKS` 與 `_SC_DECL_RE`
    兩側都用現查，不寫死）。
    """
    return [
        f"SC-6 ADR-XPLAT-002:{lineno}：寫死了 §9.1 的條數（條數請現查，勿寫進散文） ← "
        f"{line.strip()}"
        for lineno, line in enumerate(c.adr2.splitlines(), 1)
        if _SC6_RE.search(line)
    ]


# ---- SC-7：帳本用過的每個單字母 Scan-<X> 代號都必須在維度表有定義列 ----------------------
# `Scan-[A-Z][a-zA-Z]*` 先貪婪吃完整個代號，再只留「恰好單字母」者——這一步等價於規格裡的
# `grep -xE 'Scan-[A-Z]'`，**不可省**：少了它，`Scan-Shell`／`Scan-Python` 這類 R14 期的
# 臨時長名會被截斷成單字母而誤報（規格自陳實測踩過一次）。
_SCAN_CODE_RE = re.compile(r"Scan-[A-Z][a-zA-Z]*")
_SCAN_DEFINED_RE = re.compile(r"^\| \*\*(Scan-[A-Z])\*\*")
_SCAN_CODE_LEN = len("Scan-") + 1


def scan_codes_used(surface: tuple[tuple[str, str], ...]) -> set[str]:
    """`surface` 內用過的單字母維度代號（`surface` ＝ `(檔名, 內容)` 序列）。"""
    return {
        m.group(0)
        for _name, text in surface
        for m in _SCAN_CODE_RE.finditer(text)
        if len(m.group(0)) == _SCAN_CODE_LEN
    }


def scan_table_lines(scan_text: str) -> list[str]:
    """維度表**同一段連續 markdown 表格**的行（自表頭列起、遇第一個非 `|` 開頭行止）。

    🔴 為何不是「整檔逐行 regex」（R69 P3；修前實況）：R68 新增 `Scan-N`／`Scan-T` 兩列時
    在 `Scan-M` 之後多打了一個空行，於是那兩列在 GitHub 上**脫出表格**、渲染成兩段裸文字，
    而當時的 `scan_codes_defined()` 是整檔逐行比對 ⇒ **鎖對這件事完全不說話**：程式讀得到、
    人讀到的卻是壞掉的表。這與本檔反覆在治的「規格與實作各說各話」同型，只是這次不一致的
    兩造是「解析器」與「渲染器」。改以連續區塊界定定義面之後，任何一列被空行截出表格，
    它就不再算「已定義」⇒ SC-7 當場紅並指名該代號（修前實測：`['Scan-N', 'Scan-T']`）。

    抓不到表頭一律回空 list——呼叫端把空 list 當掃描面崩塌回報（同 `_section8_hits()` 紀律）。
    """
    lines = scan_text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if ln.startswith("| 維度 |")),
        None,
    )
    if start is None:
        return []
    out: list[str] = []
    for ln in lines[start:]:
        if not ln.startswith("|"):
            break
        out.append(ln)
    return out


def scan_codes_defined(scan_text: str) -> set[str]:
    """`CrossPlatform_Scan_Dimensions.md` 維度表已定義的單字母代號。"""
    return {
        m.group(1)
        for line in scan_table_lines(scan_text)
        if (m := _SCAN_DEFINED_RE.match(line))
    }


def sc7_every_used_scan_code_is_defined(c: Corpus) -> list[str]:
    """WHY（SA-R67-04）：Scan-M 產出四筆缺陷卻在維度表零定義，唯一痕跡是同輪即被歸檔的
    帳本檔——維度定義只活在某一輪的歸檔帳本裡＝把它綁死在該輪，下一輪掃描員讀維度表根本
    看不到它。

    🔴 **本條與規格形態的唯一差異就在 rc 語意**：規格寫成 `comm -23 <(…) <(…) | grep .`，
    末尾那個 `| grep .` 不是裝飾——`comm` 無論有無差集都 exit 0，拿掉即成假驗證（恆綠）。
    搬進 Python 後改用集合差集，「回傳空 list ＝通過」，不再有任何 rc 陷阱，也不依賴
    `<(...)` 這個非 POSIX 的 process substitution。
    """
    used = scan_codes_used(c.family + c.governance)
    defined = scan_codes_defined(c.scan)
    if not used:
        return [
            "SC-7：帳本家族 ∪ 具名治理文件內找不到任何單字母 Scan-<X> 代號 — 掃描面已崩塌"
            "（家族／治理文件枚舉 SSOT 或代號樣式壞了？），本判準拒絕靜默通過"
        ]
    if not defined:
        return [
            "SC-7：維度表抽不到任何**位於連續表格區塊內**的 `| **Scan-<X>**` 定義列 — "
            "表頭被改寫，或整張表被空行截斷？本判準拒絕靜默通過；"
            "請同步本檔的 _SCAN_DEFINED_RE／scan_table_lines()"
        ]
    missing = sorted(used - defined)
    if not missing:
        return []
    return [
        f"SC-7：已使用但維度表未定義的代號 {missing} — 維度定義不得只活在某一輪的帳本／"
        f"某一輪的詳情外置檔裡，請補進 {_SCAN_DIMS.name} 的維度表"
        f"（若該列已在檔內、卻仍被指名，先確認它沒有被空行截出 markdown 表格）"
    ]


# ---- SC-8：兩份 ADR 不得掛出無人消費的豁免標記 -------------------------------------------
# 只認 HTML 註解形態——散文以反引號提到標記名稱者不算，否則規格說明段自己會被判成死信
# （自製誤報，而誤報的鎖最後一定被加豁免繞過，比沒有鎖更糟）。
_OK_MARKER_RE = re.compile(r"<!--\s*([a-z][a-z-]*-ok:)")


def sc8_no_dead_letter_waiver_marker(c: Corpus) -> list[str]:
    """WHY（SA2-R67-02）：`env-transient-ok:` 曾以豁免姿態寫在 §8.3，**全庫零程式消費者**，
    而它宣稱對應的 SC-5 走 `_section8_hits()`、簽章裡根本沒有 waiver 參數 ⇒ 與 `DEF-101-688`
    （pre-push 指名一支從未存在的測試檔）同型的死信，只是死的不是檔名而是豁免標記。
    危害具體：下一個編輯者看到旁邊兩枚都有牙，會合理推定它也有，於是寫下違規句再掛上它，
    換來一次**無豁免可用**的硬紅；那時人多半會回頭把鎖關掉。

    ⚠️ 誠實劃界（一向不對稱，刻意的）：本條只驗「**文件端不得多**」。反向（本檔有 waiver
    常數而文件端零使用）**不驗**——那是「未使用」而非「死信」，判它紅會逼人刪掉仍被豁免
    紅綠測試依賴的常數。另：本條只認 HTML 註解形態的標記，換別種寫法（例如寫在表格欄位裡
    的裸標記）抓不到，屬 §9.1 邊界 (d) 已載明的列舉式窄射程。
    """
    consumed = {_SC1_WAIVER, _SC4_WAIVER}
    found: list[tuple[str, str]] = [
        (label, m)
        for label, text in _adr_pair(c)
        for m in _OK_MARKER_RE.findall(text)
    ]
    if not found:
        return [
            "SC-8：兩份 ADR 內找不到任何 `<!-- <名稱>-ok: -->` 標記 — 標記形態被改寫？"
            "本判準拒絕靜默通過；請同步本檔的 _OK_MARKER_RE"
        ]
    return [
        f"SC-8 {label}：豁免標記 `{marker}` 無任何程式消費者（本檔實際消費的是 "
        f"{sorted(consumed)}）— 讀者會誤以為它有牙。修法二擇一：刪標記改以散文說明"
        f"「這裡為何不需要豁免」，或把對應判準接上 waiver 參數讓它真的有牙"
        for label, marker in sorted(set(found))
        if marker not in consumed
    ]


# ---- SC-10：§6 邊界 1 的逐輪覆蓋表必須有當前輪次那一列（本檔第一條**缺席型**判準）------
# 🔴 R74（本輪 P0 的一半）：§6 邊界 1 的 R70 段落逐字寫著「逐輪補列是收輪必做項（缺列比
# 欄位寫錯更難發現：缺列不會有任何東西轉紅）」，而該診斷接下來就在 R73 上再度成立——
# R74 開輪時該表停在 R72。SC-1~SC-9 全是「壞形態不得出現」，對「該出現的沒出現」零覆蓋。
# 輪號**現查**（帳本「發現情境」欄最大 `R\d+`），寫死就是下一輪的 stale 站點。
_SC10_ROW_RE = re.compile(r"^\s*\|\s*R(\d+)", re.M)
#: 🔴 DEF-200-171：當前輪那一列的**內容**禁詞（缺席型判準的另一半）。R96 實例逐字掛著
#: 「本列為進行中輪次、收輪時必須複驗本列」直到四方複審才被指出；R85／R90／R91 三列同形。
_SC10_DRAFT_TOKENS = ("進行中", "待補齊", "收輪時必須複驗")


def _coverage_table_rounds(adr2: str) -> set[int]:
    """§6 邊界 1 逐輪覆蓋表已登記的輪號集合。

    刻意取**整節**而非精準切表：該表的列以 `| R<n>` 開頭，而 §6 其餘散文不會這樣起行
    （實測對現行 ADR 只抽到覆蓋表的列）。切得太精準的判準會在表格縮排微調時靜默崩塌，
    而崩塌的方向是「抽到空集合 ⇒ 恆紅」——那還好；反之若寫成 `if rows:` 就會恆綠。
    """
    section = awk_range(adr2, r"^## 6\.", r"^## 7\.")
    return {int(m) for m in _SC10_ROW_RE.findall("\n".join(ln for _, ln in section))}


def sc10_coverage_table_has_a_row_for_the_current_round(c: Corpus) -> list[str]:
    """WHY：那張表的唯一用途是回答「哪一輪在哪個平台、雲端 CI 什麼狀態」。缺當前輪的列，
    讀者就會改用別的來源反推——`DEF-101-756` 就是這樣得出與開發史相反的結論的。
    🔴 DEF-200-171：純缺席型之外補**內容**判準——當前輪那一列不得含 `_SC10_DRAFT_TOKENS`
    草稿字樣（自稱未定案的列照樣全綠＝R96 實況）；史料輪的列刻意不判（那些警語在
    它們身上是誠實的歷史，回頭改寫＝改史料）。
    """
    rounds = _coverage_table_rounds(c.adr2)
    if not rounds:
        return ["SC-10：§6 抽不到任何 `| R<n>` 覆蓋表列 — 掃描面已崩塌（表被改名／改格式？）"]
    current = _current_round_from_ledger(c)
    if current is None:
        return []  # 帳本推不出輪次時不猜（無訊號 ≠ 壞訊號），與 ci_liveness 同紀律
    if current in rounds:
        row_re = re.compile(rf"^\s*\|\s*R{current}\b")
        return [
            f"SC-10：§6 R{current} 列（ADR 第 {lineno} 行）含草稿字樣「{tok}」——當前輪"
            "列自稱未定案卻能全綠，正是 DEF-200-171 的缺陷本體（R96 該列掛到四方複審"
            "才被指出）；收輪窗口須先把該列定案，或先不要建列"
            for lineno, ln in awk_range(c.adr2, r"^## 6\.", r"^## 7\.")
            if row_re.match(ln)
            for tok in _SC10_DRAFT_TOKENS if tok in ln
        ]
    return [
        f"SC-10：§6 邊界 1 逐輪覆蓋表缺 R{current} 那一列（現有最大 R{max(rounds)}）。"
        f"該表自陳「逐輪補列是收輪必做項」，而缺列此前不會讓任何東西轉紅 ⇒ R73 就是這樣"
        f"漏掉的（連帶漏查雲端 CI，該輪收官 commit 的 windows-compat-ci 為紅）。"
        f"輪次權威源＝tools/check_defect_log_crossref.py::current_round（帳本「發現情境」欄）"
    ]


def _current_round_from_ledger(c: Corpus) -> int | None:
    """從語料裡的帳本主檔推當前輪次；權威源是既有函式，本檔不自寫第二份判準。"""
    import check_defect_log_crossref as CDX  # noqa: PLC0415  # 延後 import：避開 stdio 手術

    for name, body in c.family:
        if name.endswith(MAIN_LEDGER_NAME):
            return CDX.current_round(body)
    return None


class Check(NamedTuple):
    """一條常設不變式：`sc` 代號、規格出處、判準本體（回空 list ＝通過）。"""

    sc: str
    spec: str
    fn: Callable[[Corpus], list[str]]


_SECTION_91_CHECKS: tuple[Check, ...] = (
    Check("SC-1", _SPEC_ADR2, sc1_no_unquoted_include_glob),
    Check("SC-2", _SPEC_ADR2, sc2_no_open_ended_owner_in_section_8),
    Check("SC-3", _SPEC_ADR2, sc3_no_thousand_separated_constant_in_section_8),
    Check("SC-4", _SPEC_ADR2, sc4_no_live_platform_premise),
    Check("SC-5", _SPEC_ADR2, sc5_no_environment_state_in_the_handoff_table),
    Check("SC-6", _SPEC_ADR2, sc6_no_hardcoded_invariant_count),
    Check("SC-7", _SPEC_SCAN, sc7_every_used_scan_code_is_defined),
    Check("SC-8", _SPEC_ADR2, sc8_no_dead_letter_waiver_marker),
    Check("SC-9", _SPEC_ADR2, sc9_no_unscoped_zero_real_machine_claim),
    Check("SC-10", _SPEC_ADR2, sc10_coverage_table_has_a_row_for_the_current_round),
)


def check_by_id(sc: str) -> Check:
    return next(c for c in _SECTION_91_CHECKS if c.sc == sc)


def adr2_section_91(adr2: str) -> str:
    return _slice_section(adr2, _ADR2_SEC91_HEAD, _ADR2_SEC91_END, "ADR-XPLAT-002 §9.1 常設自檢")


def scan_selfcheck_section(scan_text: str) -> str:
    return _slice_section(
        scan_text, _SCAN_SELFCHECK_HEAD, _SCAN_SELFCHECK_END,
        f"{_SCAN_DIMS.name}〈常設自檢〉",
    )


# ---------------------------------------------------------------- 單點注入（每條各一，驗零串音）
# 各注入形態一律取自**規格自己記載的修復前實況**，不是憑空捏的樣本：規格已逐條留下
# 「修復前命中幾行、修復後零輸出」的紀錄，本表把那些形態永久釘成回歸測試。
_SC1_INJECT = "$ grep -rln 'SC-1' --include=*.py ."
_SC2_INJECT = "| item | 完成判準 | 承接輪次 **R64+** |"
_SC3_INJECT = "| item | 護欄層行數降到 4,096 以下 | 未指派 |"
_SC4_INJECT = "本機是 macOS，故 Windows 側標的本輪整批不驗。"
_SC5_INJECT = "| item | 待 CI 額度恢復後再議；期間排程停擺 | 未指派 |"
# 🔴 R69（DEF-101-702／R68-27）：原為固定字串「本節共**四**條…」＝凍在歷史值上的樣本。
# §9.1 條數成長後，那個樣本驗的是「四年前有人可能寫的錯值」，不是「今天最可能被寫下的
# 那個值」。改為**以現查條數合成**，使注入樣本永遠等於今天的高風險形態。
_SC6_CJK_DIGITS = "〇一二三四五六七八九十"


def _sc6_inject(corpus: Corpus) -> str:
    """以 §9.1 現查條數合成 SC-6 注入樣本（寫死任何數字都是違規，寫對的也是）。"""
    n = len(_SC_DECL_RE.findall(adr2_section_91(corpus.adr2)))
    token = _SC6_CJK_DIGITS[n] if 0 <= n < len(_SC6_CJK_DIGITS) else str(n)
    return f"本節共{token}條可轉紅不變式，逐條照抄即可。"
# 未定義的代號：刻意選一個維度表不會有的字母，注入後 SC-7 必須指名它。
_SC7_INJECT_CODE = "Scan-Z"
# 對照組：規格明文排除的 R14 期臨時長名，**不得**被截斷成單字母而誤報。
_SC7_LONG_FORM_CODE = "Scan-Shell"
# §8.3（逐字保全散文區）用的對照載荷，同時含 SC-2／SC-3／SC-5 三種違規形態。它驗的是
# **位置**而非內容：同一段字放進交棒表本體必須全紅，放進 §8.3 必須全綠（R67 round 4）。
_SEC83_PRESERVED = (
    "> 逐字保全原句（史料，不得改寫）：「| 9 | 判準 | 承接輪次 **R62+**；"
    "額度停擺期間護欄層行數壓到 1,024 以下 |」"
)
# SC-8 的注入形態＝R67r2 真的寫過的那一枚死信（同其餘各條：注入取自規格記載的修復前實況）。
_SC8_INJECT = "> 原句保全  <!-- env-transient-ok: 訂正段必須逐字引述被移出的原句 -->"


# SC-9 的注入形態＝R70 真的寫過的那一句（`ADR-XPLAT-003:83` 逐字）。
# stale-premise-ok: 下一行的注入樣本必須逐字等於修復前實況，否則驗的不是真形態
_SC9_INJECT = (
    "不在 import 期快取。理由：Windows 零真機，"  # stale-premise-ok: 逐字樣本
    "模擬平台的測試會失效。"
)


def _append_to_wide(c: Corpus, payload: str) -> Corpus:
    """附加到**只屬於 SC-9 掃描面**的那一份檔（ADR-XPLAT-003）。

    刻意選它而不是 `adr2`：`adr2` 同時是 SC-1~SC-6／SC-8 的掃描面，注入其上會讓
    `test_only_the_matching_check_reds` 的「零串音」判準測不出真正的串音（載體本身共用）。
    ADR-XPLAT-003 不在其餘任一條的射程內 ⇒ 只有 SC-9 該轉紅。
    """
    rel = _ADR3.resolve().relative_to(_REPO.resolve()).as_posix()
    wide = tuple(
        (name, body + "\n" + payload + "\n") if name == rel else (name, body)
        for name, body in c.wide
    )
    assert any(name == rel for name, _ in wide), f"SC-9 注入載體 {rel} 不在掃描面內"
    return c._replace(wide=wide)


def _append_to_adr2(c: Corpus, payload: str) -> Corpus:
    """附加在檔尾——刻意落在 §8／§9.1 兩個區段之外，讓「整檔逐行」與「區段內」兩種判準
    的射程差異在注入時就看得見（SC-1／SC-4／SC-6 是整檔逐行，附加即應命中）。"""
    return c._replace(adr2=c.adr2 + "\n" + payload + "\n")


def _insert_into_section_8(c: Corpus, payload: str) -> Corpus:
    """插在 `## 8.` 標題的下一行——同時落在「§8 全區」與「交棒表本體」兩種切法內。"""
    lines = c.adr2.splitlines()
    start_re = re.compile(_SEC8_START)
    idx = next((i for i, ln in enumerate(lines) if start_re.search(ln)), None)
    if idx is None:
        raise RuntimeError(
            "注入器找不到 ADR-XPLAT-002 的 §8 標題 — 注入基底已失效，"
            "拒絕做一次「注入了什麼都不知道」的無效注入"
        )
    lines.insert(idx + 1, payload)
    return c._replace(adr2="\n".join(lines))


_SEC83_START = r"^### 8\.3"


def _insert_into_section_8_3(c: Corpus, payload: str) -> Corpus:
    """插在 `### 8.3` 標題的下一行——刻意落在「交棒表本體之外、§8 全區之內」。

    這個位置就是 SC-2／SC-3／SC-5 的豁免出口本身：本 repo 的訂正體例是逐字保全被推翻的原句，
    而保全區被指定在 §8.3。抓不到該標題即 `raise`，不做一次「注入了什麼都不知道」的無效注入。
    """
    lines = c.adr2.splitlines()
    start_re = re.compile(_SEC83_START)
    idx = next((i for i, ln in enumerate(lines) if start_re.search(ln)), None)
    if idx is None:
        raise RuntimeError(
            "注入器找不到 ADR-XPLAT-002 的 §8.3 逐字保全散文區 — 該小節已不存在或改名，"
            "而 SC-2／SC-3／SC-5 的豁免出口就是它；請同步本檔的 _SEC83_START"
        )
    lines.insert(idx + 1, payload)
    return c._replace(adr2="\n".join(lines))


def _synthetic_scan_row(code: str) -> str:
    """用到 `code` 的合成列（不含任何 DEF-ID 字面——`test_defect_id_reference_integrity.py`
    會全庫 grep DEF-ID 並要求每個都有對應主鍵列）。"""
    return f"| 合成注入列 | 發現情境：R00 {code} | 本列只為驗證 SC-7 的鑑別力 |"


def _inject_scan_code(c: Corpus, code: str) -> Corpus:
    """把合成列追加在**帳本家族**尾端。"""
    return c._replace(family=c.family + (("<注入>合成帳本檔", _synthetic_scan_row(code)),))


def _inject_scan_code_into_governance(c: Corpus, code: str) -> Corpus:
    """把同一列追加在**具名治理文件**（詳情外置檔）那一側——R69 P3 新增的掃描面。"""
    return c._replace(
        governance=c.governance + (("<注入>合成詳情外置檔", _synthetic_scan_row(code)),)
    )


def _break_scan_table_before(scan_text: str, code: str) -> str:
    """在 `code` 定義列**之前**插一個空行 — 逐字重演 R68 `Scan-N`／`Scan-T` 的修復前實況
    （markdown 表格被空行截斷，該列在 GitHub 上不再渲染成表格列）。"""
    lines = scan_text.splitlines()
    idx = next(
        (i for i, ln in enumerate(lines) if ln.startswith(f"| **{code}**")),
        None,
    )
    if idx is None:
        raise RuntimeError(
            f"注入器在維度表找不到 {code} 的定義列 — 注入基底已失效，"
            "拒絕做一次「注入了什麼都不知道」的無效注入"
        )
    lines.insert(idx, "")
    return "\n".join(lines)


class Injection(NamedTuple):
    sc: str
    why: str
    mutate: Callable[[Corpus], Corpus]


_SECTION_91_INJECTIONS: tuple[Injection, ...] = (
    Injection("SC-1", "規格記載的修復前實況：兩份 ADR 各有未加引號的 glob",
              lambda c: _append_to_adr2(c, _SC1_INJECT)),
    Injection("SC-2", "規格記載的修復前實況：§8 兩列以開放下界當承接者",
              lambda c: _insert_into_section_8(c, _SC2_INJECT)),
    Injection("SC-3", "規格記載的修復前實況：§8 兩列在完成判準欄寫死量測常數",
              lambda c: _insert_into_section_8(c, _SC3_INJECT)),
    Injection("SC-4", "規格記載的修復前實況：§6 邊界 1 把平台寫成文件常數",
              lambda c: _append_to_adr2(c, _SC4_INJECT)),
    Injection("SC-5", "規格記載的修復前實況：§8 交棒表混入外部環境當時狀態",
              lambda c: _insert_into_section_8(c, _SC5_INJECT)),
    Injection("SC-6", "規格記載的修復前實況：標題寫死條數而與實際交付數不符",
              lambda c: _append_to_adr2(c, _sc6_inject(c))),
    Injection("SC-7", "規格記載的修復前實況：Scan-M 產出缺陷卻在維度表零定義",
              lambda c: _inject_scan_code(c, _SC7_INJECT_CODE)),
    Injection("SC-8", "規格記載的修復前實況：§8.3 掛著一枚全庫零消費者的豁免標記",
              lambda c: _append_to_adr2(c, _SC8_INJECT)),
    Injection("SC-9", "規格記載的修復前實況：R69/R70 把「Windows 零真機」寫得橫跨 docs 與 .py",
              lambda c: _append_to_wide(c, _SC9_INJECT)),
    Injection("SC-10", "規格記載的修復前實況：§6 逐輪覆蓋表停在較早輪次、缺當前輪那一列",
              lambda c: _drop_current_round_row(c)),
    Injection("SC-10", "DEF-200-171 的修復前實況：當前輪列逐字自稱草稿（R96 掛到複審才被指出）",
              lambda c: _taint_current_round_row(c)),
)


def _drop_current_round_row(c: Corpus) -> Corpus:
    """把當前輪那一列從 §6 覆蓋表刪掉＝R74 開輪時的實況（表停在 R72、缺 R73）。"""
    current = _current_round_from_ledger(c)
    assert current is not None, "SC-10 注入需要帳本能推出輪次"
    kept = [ln for ln in c.adr2.splitlines()
            if not re.match(rf"^\s*\|\s*R{current}\b", ln)]
    assert len(kept) < len(c.adr2.splitlines()), f"注入未刪到任何 R{current} 列"
    return c._replace(adr2="\n".join(kept))


def _taint_current_round_row(c: Corpus) -> Corpus:
    """往當前輪那一列**行內**補上 R96 逐字警語＝DEF-200-171 立案的修復前實況。"""
    current = _current_round_from_ledger(c)
    assert current is not None, "SC-10 注入需要帳本能推出輪次"
    lines = c.adr2.splitlines()
    idx = next((i for i, ln in enumerate(lines)
                if re.match(rf"^\s*\|\s*R{current}\b", ln)), None)
    assert idx is not None, f"注入找不到 R{current} 列——基底失效，拒絕無效注入"
    lines[idx] += " ⚠️ 本列為進行中輪次，收輪時必須複驗本列 |"
    return c._replace(adr2="\n".join(lines))


class TestApprovedRoundOverageIsScoped(unittest.TestCase):
    """🔴 DEF-200-208：`_REPIN_APPROVED_ROUND_OVERAGE` 的一次性例外**名冊本身**必須有牙——

    一個「寫張條子就能繞過 cap／streak」的機制，若名冊本身沒有機械物看著它，
    今天赦免一輪的立案理由，明天就會變成「反正上次也是這樣過的」的先例。
    本類專守名冊本身，不重複驗 `repin_growth_problems()` 款(10)(11) 的一般邏輯
    （那兩款仍由 `TestGuardLayerRatchet` 既有測試守著，本類只加「例外表存在時」這一維）。
    """

    def _synthetic_log(self, no: int, delta: int) -> tuple[tuple[str, int, int, int, str], ...]:
        return ((f"R{no}", 1000, 1000 + delta, delta,
                 f"合成列，理由夠長夠長夠長 {_NOT_NET_SUBTRACTION_TOKEN} "
                 f"CrossPlatform_R{no}_Scan_Findings.md"),)

    def test_an_override_suppresses_only_the_named_round(self) -> None:
        """核准表命中時，該輪的款(10)(11) 都不出現；未命中的輪次完全不受影響。"""
        table = {"R900": (5000, "合成核准理由，字數足夠通過長度檢查，供純函式注入測試用。")}
        over_cap = self._synthetic_log(900, 5000)
        self.assertEqual(
            repin_growth_problems(over_cap, approved_overage=table), [],
            "已核准的輪次仍被款(10) 擋下 ⇒ 名冊沒有真的接進判準")
        # 對照組：換一個沒被列名的輪號，同樣的超額必須照樣紅。
        not_listed = self._synthetic_log(901, 5000)
        self.assertTrue(
            any("[超出每輪上限]" in p
                for p in repin_growth_problems(not_listed, approved_overage=table)),
            "沒被列名的輪次竟然也被放行 ⇒ 名冊變成了對所有輪次生效的降權，"
            "而不是指名的一次性例外")

    def test_the_override_requires_an_exact_delta_match(self) -> None:
        """🔴 主牙：核准的是**精確淨額**，不是輪號本身——淨額對不上就不算數。

        立案理由見 `_REPIN_APPROVED_ROUND_OVERAGE` 上方 WHY：既有測試 fixture
        `test_a_round_that_exceeds_the_net_cap_is_red` 會拿 schedule 最後一列的輪號
        造合成樣本，若本表只認輪號，那支測試的紅燈會被本表意外熄滅。
        """
        table = {"R900": (5000, "合成核准理由，字數足夠通過長度檢查，供純函式注入測試用。")}
        wrong_delta = self._synthetic_log(900, 5001)
        self.assertTrue(
            any("[超出每輪上限]" in p
                for p in repin_growth_problems(wrong_delta, approved_overage=table)),
            "同一輪號、不同淨額竟然也被放行 ⇒ 名冊變成「這個輪號往後怎麼標都算數」，"
            "不再是指名的那一個精確事件")

    def test_a_short_reason_does_not_count_as_approval(self) -> None:
        """理由欄過短 ⇒ 視同未核准（同 `phase2_review_problems()` 款(4) 的「延期」判例）。"""
        table = {"R900": (5000, "核准")}
        over_cap = self._synthetic_log(900, 5000)
        self.assertTrue(
            any("[超出每輪上限]" in p
                for p in repin_growth_problems(over_cap, approved_overage=table)),
            "兩個字的核准理由竟然也算數 ⇒ 一次性例外可以不具名地被批量核發")

    def test_the_override_also_breaks_the_rising_streak(self) -> None:
        """核准的一輪不計入款(11) 的連續上升計數（否則例外只解 cap 卻仍撞 streak）。"""
        since = _REPIN_ROUND_CAP_SINCE
        rising_two = tuple(self._rising_row(since + i) for i in range(2))
        table = {f"R{since + 2}": (
            100, "合成核准理由，字數足夠通過長度檢查，供純函式注入測試用途。")}
        third = self._rising_row(since + 2)
        problems = repin_growth_problems((*rising_two, third), approved_overage=table)
        self.assertFalse(
            [p for p in problems if "[只升不降]" in p],
            f"核准的第三輪仍被計入連續上升 ⇒ 例外沒有真的涵蓋款(11)；實得：{problems}")

    def _rising_row(self, no: int, delta: int = 100) -> tuple[str, int, int, int, str]:
        return (f"R{no}", 1000, 1000 + delta, delta,
                f"合成列，理由夠長夠長夠長 {_NOT_NET_SUBTRACTION_TOKEN} "
                f"CrossPlatform_R{no}_Scan_Findings.md")

    def test_the_registry_stays_a_one_time_exception(self) -> None:
        """🔴 結構性防重用：名冊筆數不得超過 `_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES`。

        這條鎖擋的不是任何一次核准的內容，是「這張表本身變成慣例」的那個趨勢——
        每多一筆都要讓這個斷言先失敗，逼下一個人先來改這個上限（＝多一次可見的決策），
        而不是悄悄追加第二個 key。"""
        self.assertLessEqual(
            len(_REPIN_APPROVED_ROUND_OVERAGE), _REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES,
            "一次性例外名冊筆數超過上限 ⇒ 「一次性」已經名不符實")

    def test_removing_the_live_entry_reproduces_the_original_deadlock(self) -> None:
        """🔴 紅綠自證（DEF-200-208 落地本身的回歸鎖）：拿掉 R101 這筆核准 round-label-ok，
        真表立刻復發 款(10)(11) 的原始死結——證明本表不是恰好沒被用到，而是真的在擋著。
        """
        problems = repin_growth_problems(_GUARD_LINES_REPIN_LOG, approved_overage={})
        self.assertTrue(
            any("[超出每輪上限]" in p for p in problems),
            "拿掉核准名冊後，真表的 R101 竟然沒有觸發 [超出每輪上限] ⇒ "
            "本表這次落地前根本沒有真的擋住什麼（DEF-200-208 死結未曾真實存在？）")
        self.assertTrue(
            any("[只升不降]" in p for p in problems),
            "拿掉核准名冊後，R99／R100／R101 連續三輪上升竟然沒有觸發 [只升不降] ⇒ "
            "DEF-200-208 記載的死結另一半（streak）本表也沒有真的在擋")


class TestSection91InvariantsAreLive(unittest.TestCase):
    """各條在**真實文件**上現跑（這一步就是 SA-R67-03 缺的那個「可執行消費者」）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.live = read_corpus()

    def test_every_declared_invariant_holds_on_the_real_documents(self) -> None:
        for chk in _SECTION_91_CHECKS:
            with self.subTest(sc=chk.sc):
                self.assertEqual(
                    chk.fn(self.live), [],
                    f"{chk.sc}（規格出處：{chk.spec}）在現行文件上違規；"
                    f"判準與修法見本檔 {chk.fn.__name__} 的 docstring",
                )

    def test_the_scan_surface_did_not_collapse(self) -> None:
        """反空轉：掃描面一旦崩塌，上一支測試會**全部靜默通過**，故另立此支 fail-loud。

        三份文件與帳本家族都必須非空；`§8 全區` 與 `交棒表本體` 都必須抽得到，且本體必須
        **嚴格短於**全區——兩者相等即代表 `### 8.1` 界線失效、SC-5 已退化成掃 §8 全區
        （那會讓 §8.3 刻意保全的歷史原句誤紅，而誤紅的鎖最後一定被加豁免繞過）。
        """
        for what, text in (("ADR-XPLAT-002", self.live.adr2), ("ADR-XPLAT-001", self.live.adr1),
                           (_SCAN_DIMS.name, self.live.scan)):
            self.assertTrue(text.strip(), f"{what} 讀進來是空的 — 掃描面崩塌")
        self.assertTrue(self.live.family, "帳本家族枚舉為空 — SC-7 的掃描面崩塌")
        self.assertTrue(
            self.live.governance,
            "具名治理文件枚舉為空 — SC-7 的『詳情外置』掃描面崩塌"
            "（`ADL._GOVERNANCE_DOCS` 只剩維度表自己？）",
        )
        self.assertTrue(
            scan_table_lines(self.live.scan),
            f"{_SCAN_DIMS.name} 抽不到連續的維度表區塊 — 表頭 `| 維度 |` 已改名？",
        )
        whole = awk_range(self.live.adr2, _SEC8_START, _SEC8_END_ALL)
        body = awk_range(self.live.adr2, _SEC8_START, _SEC8_END_TABLE)
        self.assertTrue(whole, "§8 全區抽不到")
        self.assertTrue(body, "§8 交棒表本體抽不到")
        self.assertLess(
            len(body), len(whole),
            "§8 交棒表本體未嚴格短於 §8 全區 ⇒ `### 8.1` 子節界線已失效，"
            "SC-5 會退化成掃全區並對 §8.3 的逐字保全原句誤紅",
        )


class TestSection91InvariantsHaveTeeth(unittest.TestCase):
    """單點注入紅綠自證 ＋ **零串音**：注入 SC-N 的違規形態時只有 SC-N 轉紅。

    🔴 為何每一條都非注入不可：本段承接的前一包交付過一版「看起來會擋」的鎖——它把某條
    設計成「含關鍵字的行必須同時含某字樣」，注入後**不轉紅**，因為注入點落在一個已含該
    字樣的單行巨欄內、整行被放行。改成計數／差集形態後才真的有牙。⇒ 沒有注入證明的鎖
    一律視為 `NOT-PROVEN`（`CrossPlatform_Scan_Dimensions.md` Scan-H 判準①）。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.live = read_corpus()

    def test_every_check_has_a_named_injection(self) -> None:
        """雙向：少一條注入＝那條鎖沒有鑑別力證明；多一條＝指向已不存在的判準。"""
        self.assertEqual(
            {i.sc for i in _SECTION_91_INJECTIONS}, {c.sc for c in _SECTION_91_CHECKS},
            "注入表與判準表不對稱 — 每一條判準都必須有自己的單點注入",
        )

    def test_each_injection_turns_exactly_its_own_check_red(self) -> None:
        """本類的主體：紅（有牙）＋ 零串音（紅燈能指出是哪一種違規）一次驗完。"""
        for inj in _SECTION_91_INJECTIONS:
            with self.subTest(sc=inj.sc, why=inj.why):
                mutated = inj.mutate(self.live)
                reds = {c.sc for c in _SECTION_91_CHECKS if c.fn(mutated)}
                self.assertEqual(
                    reds, {inj.sc},
                    f"注入 {inj.sc} 的違規形態後轉紅的判準是 {sorted(reds)}；"
                    f"應恰為 {{'{inj.sc}'}}——空集合＝該鎖無牙，多出來的＝判準間有串音",
                )

    def test_every_check_has_a_real_exemption_path(self) -> None:
        """豁免機制必須真的能放行，否則逐字引述壞形態的訂正段會被判**永紅**。

        本檔有兩種豁免形態，兩種都要驗：
        · **同行標記**（SC-1／SC-4，走 `_line_hits_with_waiver`）。
        · **區段位置**（SC-2／SC-3／SC-5：射程止於 `### 8.1`，逐字原句移進 §8.3 即出射程）。
          🔴 R67 round 4 之前 SC-2／SC-3 掃 §8 全區且無任何豁免路徑，SA2-R67-01 以注入實測
          證明「照本輪體例保全一句 §8 原文即永紅」。本段的正控／反控刻意成對：綠必須來自
          **位置**，而不是判準對那段字失明 ⇒ 同一段載荷放進交棒表本體必須全紅。
        「文件端掛出無人消費的豁免標記」這件事本身另立為 **SC-8**（SA2-R67-02），走與其餘
        各條同一條路（宣告集合綁定 ＋ 單點注入 ＋ 零串音），不在本支內另開一套判準——
        新不變式若只藏在某支測試裡而不進宣告集合，正是同輪 SD-R67R2-04 抓到的形態。
        """
        for sc, payload, waiver in (
            ("SC-1", _SC1_INJECT, _SC1_WAIVER),
            ("SC-4", _SC4_INJECT, _SC4_WAIVER),
        ):
            with self.subTest(sc=sc, path="同行標記"):
                waived = _append_to_adr2(
                    self.live, f"{payload}  <!-- {waiver} 逐字引述壞形態以說明缺陷本身 -->"
                )
                self.assertEqual(check_by_id(sc).fn(waived), [], f"{sc} 的同行豁免失效")

        preserved = _insert_into_section_8_3(self.live, _SEC83_PRESERVED)
        control = _insert_into_section_8(self.live, _SEC83_PRESERVED)
        for sc in ("SC-2", "SC-3", "SC-5"):
            with self.subTest(sc=sc, path="§8.3 區段豁免"):
                self.assertEqual(
                    check_by_id(sc).fn(preserved), [],
                    f"{sc} 對 §8.3 逐字保全散文區裡的原句轉紅 ⇒ 保全體例與本鎖互斥，"
                    f"下一次保全一句 §8 原文即永紅（射程應止於 `### 8.1`）",
                )
                self.assertTrue(
                    check_by_id(sc).fn(control),
                    f"{sc} 對放進交棒表本體的**同一段**載荷不轉紅 ⇒ 上一句的綠是判準失明，"
                    f"不是區段豁免；本鎖拒絕以假綠冒充豁免",
                )

        # 自綁：ADR §9.1 邊界 (d-1) 具名指向本支當機械承接者。具名而指不到就是死信
        # ——正是本支自己在治的形態，故本支不得自己犯（改名時請同步該處散文）。
        me = self._testMethodName
        self.assertTrue(
            [label for label, text in _adr_pair(self.live) if me in text],
            f"兩份 ADR 都沒提到 {me} — 該處的具名承接已失聯",
        )

    def test_a_waiver_on_a_neighbouring_line_does_not_shield(self) -> None:
        """🔴 單行巨欄陷阱：豁免只准放行**同一行**。

        這兩份 ADR 的表格狀態欄一格上千字、在檔案裡就是一行；若容許跨行豁免，一個標記會
        把整格放行。本支把「鄰行的標記不算數」永久釘住。
        """
        for sc, payload, waiver in (
            ("SC-1", _SC1_INJECT, _SC1_WAIVER),
            ("SC-4", _SC4_INJECT, _SC4_WAIVER),
        ):
            with self.subTest(sc=sc):
                neighbour = _append_to_adr2(
                    self.live, f"<!-- {waiver} 上一行的理由，不該及於下一行 -->\n{payload}"
                )
                self.assertTrue(
                    check_by_id(sc).fn(neighbour),
                    f"{sc} 被鄰行的豁免標記放行 ⇒ 單行巨欄裡一個標記就能放行整格",
                )

    def test_a_waiver_without_a_reason_is_rejected(self) -> None:
        """規格逐字要求「掛豁免**並寫理由**」——無理由的豁免是後門，不是豁免。

        `grep` 形態表達不了這一條（它只看得到標記在不在），所以這是搬進 Python 才補上的
        判準。同時驗**反面**：規格自己的說明散文與 grep 指令裡也有標記字串，那些行不含
        違規 token，不得因此被判為「無理由的豁免」（那會是自製誤報）。
        """
        for sc, payload, waiver in (
            ("SC-1", _SC1_INJECT, _SC1_WAIVER),
            ("SC-4", _SC4_INJECT, _SC4_WAIVER),
        ):
            with self.subTest(sc=sc):
                bare = _append_to_adr2(self.live, f"{payload}  <!-- {waiver} -->")
                problems = check_by_id(sc).fn(bare)
                self.assertTrue(problems, f"{sc} 放行了沒有理由的豁免")
                self.assertIn("沒有理由", problems[0])
                # 反面：只提到標記字串、不含違規 token 的散文行不得被判違規
                mention = _append_to_adr2(self.live, f"要豁免請在同一行掛 `{waiver} <理由>`。")
                self.assertEqual(
                    check_by_id(sc).fn(mention), [],
                    f"{sc} 對「只是提到標記名稱」的散文行誤報 — 誤報的鎖會被加豁免繞過",
                )

    def test_losing_the_section_anchor_is_reported_not_silently_green(self) -> None:
        """區段界線失效時，`awk`／`grep` 的原語意是「零輸出＝通過」＝ fail-open。

        本段刻意把它改成違規回報（`_section8_hits`）。這一支證明改的有效：把 §8 標題改名後
        SC-2／SC-3／SC-5 全部轉紅並指名掃描面崩塌，而非靜默全綠。
        （這是**共用錨點**的預期連動，與上面的零串音不衝突——那支驗的是內容形態的注入。）
        """
        broken = self.live._replace(adr2=self.live.adr2.replace("\n## 8. ", "\n## 8x_renamed "))
        self.assertNotEqual(broken.adr2, self.live.adr2, "注入基底失效：ADR 內找不到 §8 標題")
        for sc in ("SC-2", "SC-3", "SC-5"):
            with self.subTest(sc=sc):
                problems = check_by_id(sc).fn(broken)
                self.assertTrue(problems, f"{sc} 在區段抽不到時靜默通過 ⇒ fail-open")
                self.assertIn("掃描面已崩塌", problems[0])

    def test_sc7_reports_a_collapsed_scan_surface_on_either_side(self) -> None:
        """SC-7 是「差集為空＝通過」，故**任一側掃描面歸零都會讓它恆綠**——兩側各驗一次。

        使用側自 R69 P3 起是「帳本家族 ∪ 具名治理文件」，故歸零要兩者同時清空才算掃描面
        崩塌（只清其一仍有代號可比對，不該報崩塌，那會是自製誤報）。
        """
        for what, corpus in (
            ("使用面（帳本家族＋治理文件）", self.live._replace(family=(), governance=())),
            ("維度表", self.live._replace(scan="")),
        ):
            with self.subTest(side=what):
                problems = check_by_id("SC-7").fn(corpus)
                self.assertTrue(problems, f"{what} 歸零時 SC-7 靜默通過 ⇒ fail-open")
                self.assertIn("拒絕靜默通過", problems[0])

    def test_sc7_names_the_undefined_code_it_found(self) -> None:
        """紅燈必須指路：訊息要逐字說出是哪個代號沒定義，而不是只說「有差集」。

        🔴 R69 P3：**兩側各注一次**。治理文件那一側就是 R68 造出來的逸出路徑——帳本主檔
        只留一列指針、逐筆詳情全在 `CrossPlatform_R68_Scan_Findings.md`，於是「用了未定義
        代號」只要寫在詳情外置檔就整個逸出 SC-7（同一個病換皮即復發）。
        """
        for side, mutate in (
            ("帳本家族", _inject_scan_code),
            ("具名治理文件（詳情外置檔）", _inject_scan_code_into_governance),
        ):
            with self.subTest(side=side):
                problems = check_by_id("SC-7").fn(mutate(self.live, _SC7_INJECT_CODE))
                self.assertTrue(problems, f"{side} 側注入未定義代號後 SC-7 仍靜默通過")
                self.assertIn(_SC7_INJECT_CODE, problems[0])

    def test_sc7_reds_when_a_definition_row_is_broken_out_of_the_markdown_table(self) -> None:
        """🔴 R69 P3：定義列被空行截出 markdown 表格 ⇒ 它就不算「已定義」。

        修前實況（本鎖落地前）：`scan_codes_defined()` 是整檔逐行 regex，於是 R68 在
        `Scan-M` 之後多打的那個空行讓 `Scan-N`／`Scan-T` 在 GitHub 上渲染成兩段裸文字，
        而任何鎖都不會說話——程式讀得到、人讀到的是壞掉的表。本支對每一個現行定義列逐一
        注入該形態，確保這件事在任何一列上都轉紅（不是只對當初那兩列有效）。

        🔴 **本輪：注入面必須是「已定義 ∩ 已使用」，不是全部已定義**。SC-7 判的是
        「**用了**卻沒定義」，所以一個**剛定義、還沒有任何帳本列或治理文件用到**的代號
        被空行截出表格時，SC-7 依定義沒有話說——本支若照舊對它斷言必紅，就是拿一個
        SC-7 從未承諾的性質去要求它。實證：本輪依規定**先**把當輪兩個新代號補進維度表
        （不先補，代號一寫進帳本就擋住每一次 push），本支當場對那兩列判 FAIL——
        **一道鎖要求你做的動作，讓同一支鎖檔的另一支測試轉紅**，即維度表 Scan-H 必跑項⑥
        的形態。修法刻意不是「把新列排在別的列前面」（那樣的綠來自「後面那些已使用的列
        一起被截斷」，是位置的巧合，而且會在下一個依慣例把新列附加在表尾的人身上復發），
        而是把注入面對齊判準自己的語意。尚未被使用的代號在有人用它的那一刻自動回到注入面。
        """
        defined = sorted(scan_codes_defined(self.live.scan))
        self.assertTrue(defined, "維度表抽不到任何定義列 — 注入基底已失效")
        used = scan_codes_used(self.live.family + self.live.governance)
        targets = sorted(set(defined) & used)
        self.assertTrue(
            targets,
            f"已定義與已使用的代號零交集 — 注入基底已失效（defined={defined}）",
        )
        for code in targets:
            with self.subTest(code=code):
                broken = self.live._replace(
                    scan=_break_scan_table_before(self.live.scan, code)
                )
                problems = check_by_id("SC-7").fn(broken)
                self.assertTrue(
                    problems, f"{code} 被空行截出表格後 SC-7 仍靜默通過 ⇒ 渲染面與解析面各說各話"
                )

    def test_sc7_does_not_flag_the_documented_long_form_codes(self) -> None:
        """對照組（規格明載的邊界）：R14 期的臨時長名不得被截斷成單字母而誤報。

        少了 `grep -xE 'Scan-[A-Z]'` 那一步（本檔的 `_SCAN_CODE_LEN` 過濾），`Scan-Shell`
        會被讀成 `Scan-S` 而製造假紅。誤報的鎖最後一定被加豁免繞過，比沒有鎖更糟。
        """
        self.assertEqual(
            check_by_id("SC-7").fn(_inject_scan_code(self.live, _SC7_LONG_FORM_CODE)), [],
            f"{_SC7_LONG_FORM_CODE} 被截斷成單字母而誤報 — 長名排除那一步失效",
        )


def section91_consumer_classes() -> tuple[str, ...]:
    """現查本檔定義的 `TestSection91*` 消費者類別名。名單與數量一律不寫死（同 SC-6 紀律）。"""
    return tuple(sorted(
        name for name, obj in globals().items()
        if name.startswith("TestSection91") and isinstance(obj, type)
    ))


class TestSection91SpecIsBoundToTheseLocks(unittest.TestCase):
    """規格散文 ↔ 本檔實作雙向綁定（手法照抄 `TestCriterionIsBoundToAdrProse`）。

    🔴 為何非綁不可：本段的判準**一條也不是本檔自己編的**，全部逐字取自 §9.1／〈常設自檢〉。
    規格改字而程式沒跟（或反之）就會退化成「散文與程式各走各的」——那正是本 repo 反覆在治的病。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.live = read_corpus()

    def test_the_adr_declares_exactly_the_invariants_implemented_here(self) -> None:
        """雙向且**條數現查**：ADR 新增一條 `# SC-N` 而沒人實作 → 紅；本檔刪一條 → 紅。

        這同時是 SC-6 的正面版本：本鎖對「§9.1 有幾條」一律現查，不在任何一側寫死。

        🔴 R67 round 4 拿掉 `c.spec == _SPEC_ADR2` 過濾（SD-R67R2-04）。原版只把規格住在 ADR
        的那些條目納入比對，於是 SC-7（規格本體住在 `CrossPlatform_Scan_Dimensions.md`
        〈常設自檢〉）**結構上被排除**：SD 用突變實測證明「把 SC-7 連同它的專屬測試一起刪掉，
        全套測試零訊號」——七條不變式裡最新的一條保護等級最低，而它守的正是缺陷帳本與維度表
        之間的 SSOT 對應。同時 Scan_Dimensions 那句「本不變式即該 ADR §9.1 所列的 SC-7」是
        死信（ADR 全檔零次提及 SC-7）。⇒ 改為全集比對，並要求 §9.1 為每個規格住在他處的條目
        指名其規格出處檔——跨檔的宣告集合也要綁得住，否則「宣告集合雙向綁定」只是半句真話。
        """
        section = adr2_section_91(self.live.adr2)
        declared = set(_SC_DECL_RE.findall(section))
        implemented = {c.sc for c in _SECTION_91_CHECKS}
        self.assertEqual(
            declared, implemented,
            "ADR §9.1 宣告的 SC 條目與本檔實作的判準集合不一致 — "
            "規格新增條目時必須同步落成機械鎖，否則它又會是一條零消費者的死信；"
            "反之刪掉實作而 §9.1 仍宣告，也是同一種失聯",
        )
        for chk in _SECTION_91_CHECKS:
            if chk.spec == _SPEC_ADR2:
                continue
            host = chk.spec.split("〈", 1)[0]
            with self.subTest(sc=chk.sc, spec=chk.spec):
                self.assertIn(
                    host, section,
                    f"{chk.sc} 的規格本體住在 {host}，而 ADR §9.1 沒指名它 — "
                    f"讀者無從知道該去哪裡看判準，交叉引用即成死信",
                )

    def test_the_adr_still_names_this_file_as_the_host(self) -> None:
        """§9.1 末段具名指派本檔為承接容器；本檔改名／§9.1 改指他處都必須被發現。"""
        self.assertIn(
            _HERE.name, adr2_section_91(self.live.adr2),
            f"ADR §9.1 未指名 {_HERE.name} 為承接容器 — 具名交棒失聯",
        )

    def test_the_adr_names_the_live_consumers_it_now_claims_to_have(self) -> None:
        """🔴 R67 round 3：§9.1 散文已從「零可執行消費者」改寫為「已是活體守門」，本支把
        **那句新宣稱**綁回它指名的東西上——散文換了說法，就得有東西看著新說法。

        為何做成**正面綁定**，而不是「散文不得再出現『零消費者』字樣」的黑名單：
        · 本 repo 的訂正體例是**逐字保全被推翻的原句**（§8.3、以及 §9.1／〈常設自檢〉這兩處
          訂正段本身都是這樣寫的）。黑名單會對這些刻意保全的史料永遠說紅——〈常設自檢〉
          自己就警告過「歷史檔逐字保全 ⇒ 舊列永遠留著死信字樣 ⇒ 閘門永紅」，而本檔多處已
          載明：誤報的鎖最後一定被加豁免繞過，比沒有鎖更糟。
        · 字樣黑名單換個措辭（「尚未接線」「無人消費」）就逸出，正是 §9.1 邊界 (d) 已明載的
          列舉式窄射程。
        正面綁定沒有這兩個毛病：把消費者從散文刪掉、或在本檔改名／新增而散文沒跟，都會紅，
        且對保全下來的原句完全無感。
        """
        consumers = section91_consumer_classes()
        self.assertTrue(
            consumers,
            "本檔已找不到任何 `TestSection91*` 消費者類別 — 枚舉面崩塌，本鎖拒絕空轉通過",
        )
        section = adr2_section_91(self.live.adr2)
        for name in consumers:
            with self.subTest(consumer=name):
                self.assertIn(
                    name, section,
                    f"ADR §9.1 未指名消費者 {name} — 該節現在自稱「已是活體守門」，"
                    f"這句宣稱就必須逐一指得出消費者；新增／改名消費者類別時請同步該節散文",
                )

    def test_the_scan_selfcheck_keeps_the_pieces_this_lock_depends_on(self) -> None:
        """〈常設自檢〉裡有三樣東西是本檔 SC-7 實作的前提，刪掉任一樣都會讓下一個人改壞它。

        · `comm`／恆綠：規格逐字警告「`comm` 無論有無差集都 exit 0」，本檔正因此改用集合差集；
          警告消失後，下一個人很可能「簡化」回 comm 形態而得到一個恆綠的假鎖。
        · `Scan-[A-Z]` 的逐字比對範圍：本檔 `_SCAN_CODE_LEN` 過濾就是它的 Python 版。
        · `Scan-Shell`：規格明載的長名排除案例，本檔的誤報對照組直接依賴它。
        · 規格住在本檔以外的那些 SC 代號（現查，不寫死）：〈常設自檢〉自稱「本不變式即該 ADR
          §9.1 所列的 SC-N」，這句交叉引用要成立，該節就得逐字說得出是哪一個代號。R67 round 4
          之前 ADR 側零次提及 SC-7，那句話是死信（SD-R67R2-04）；本支釘住另一半。
        """
        section = scan_selfcheck_section(self.live.scan)
        scan_specced = tuple(c.sc for c in _SECTION_91_CHECKS if c.spec == _SPEC_SCAN)
        for token in ("comm", "恆綠", "Scan-[A-Z]", _SC7_LONG_FORM_CODE, *scan_specced):
            with self.subTest(token=token):
                self.assertIn(
                    token, section,
                    f"〈常設自檢〉已不再載明 {token!r} — 本檔 SC-7 的實作前提失去散文依據",
                )


# 本檔自己也受「散文不得寫死可機械算出的計數」這條紀律管（P2-6）。量詞集合的來源有二：
#   ① round 2 實際犯規處用過的量詞（一處寫死豁免筆數、一處寫死帳本列數、一處寫死
#      「一次紅 N 個」）——即 `筆列個支處`。
#   ② round 3 SD-R60R3-05 用加寬集合對本檔全掃，抓到的**檔內現存實例**：`DEF-101-324`
#      的登記散文寫死了 AISDLC_SDD 的凍結版版本數，而量詞「版」不在集合裡 ⇒ 本鎖對它
#      不會說話，AISDLC_SDD 每加一版那句就 stale 一次。這使「換個量詞就逸出」從理論邊界
#      變成已發生事實，故把 `版檔份道項次` 一併納入（這幾個字是本 repo 治理散文最常用的
#      量詞：檔數／份數／第 N 道閘門／第 N 項／第 N 次）。
# `(?<![§\d])` 用來排除節號引用（例：§9 後面接「列」字）。
_BARE_COUNT_RE = re.compile(r"(?<![§\d])\d+\s*[筆列個支處版檔份道項次]")


class TestThisLockObeysItsOwnNoHardcodedCountRule(unittest.TestCase):
    """本檔檔頭訂了「筆數不寫在散文裡」，round 2 的版本自己在幾十行後違反了它。

    ARCH-R60R2-04／SD-R60-R2-06 逐字抓到三處：寫死豁免筆數（實況已與之不符）、寫死帳本
    列數（實況已與之不符）、以及「一次紅 N 個」。訂正方式不是「把數字改成新的正確值」
    ——那只是把過期時點往後挪一輪——而是改成不引數字的寫法。本類把這條紀律機械化。

    邊界（誠實劃界）：只擋「阿拉伯數字＋`_BARE_COUNT_RE` 列舉的那組量詞」的寫法，**不是**
    通用的「散文寫死數字」偵測器。寫成中文數字、或把計數藏進變數名仍抓不到；真正通用的
    判準需要語意理解，本鎖不假裝有。門檻常數自己（例如上限與掃描面下限）不受此限——它們
    是該數字的唯一真相源，不是散文複本。

    🔴 round 3 收緊（SD-R60R3-05）：「換個量詞就逸出」原本只是上面這段誠實劃界裡的理論
    邊界，SD 用加寬集合實掃後證明它**已經在本檔內發生**（`DEF-101-324` 登記散文寫死凍結版
    版本數）。性質不同 ⇒ 量詞集合擴充、那句散文同步改成不引數字的寫法。訂正方向仍是
    「改成不引數字」而不是「把舊數字換成新數字」——後者只是把過期時點往後挪一輪，本輪已
    為同型問題裁決過一次。收緊後全檔零命中（`test_no_bare_count_with_a_measure_word_anywhere_in_this_file`
    就是那個零命中的機械證明）。
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

    def test_the_detector_catches_the_round3_widened_measure_words(self) -> None:
        """注入（SD-R60R3-05）：加寬進來的量詞必須真的有牙。

        第一筆就是 `DEF-101-324` 登記散文修掉之前的**逐字原形**——它在 round 2 的偵測器下
        是綠的，躺在本檔裡等著 AISDLC_SDD 下一次加版就過期。其餘四筆是本 repo 治理散文
        會用到的同型量詞，一併釘住，避免「只補了踩到的那一個」。
        """
        for sample in (
            "範圍是全 " + str(30) + " 版（含 LATEST）一致存在",
            "護欄層現為 " + str(56) + " 檔",
            "帳本家族 " + str(33) + " 份",
            "接 root-infra-ci 第 " + str(14) + " 道",
            "必跑項第 " + str(4) + " 項",
            "已重演 " + str(3) + " 次",
        ):
            with self.subTest(sample=sample):
                self.assertTrue(
                    _BARE_COUNT_RE.search(sample),
                    "加寬後的量詞集合對真實犯規形態仍失效",
                )

    def test_the_detector_does_not_flag_section_references(self) -> None:
        """對照組：`§9 列`／`§10 列` 這類節號引用不得誤報（本檔散文大量使用）。"""
        for sample in ("補一列進 §9 列表", "見 §10 列的敘述"):
            with self.subTest(sample=sample):
                self.assertIsNone(_BARE_COUNT_RE.search(sample))

    def test_the_widened_detector_does_not_flag_narrative_round_references(self) -> None:
        """對照組（round 3 收緊的誤紅面）：`round 2 的版本` 這類**敘事引用**不是計數。

        加寬前本檔有三處「round＋輪次號」緊接「版本」二字的寫法，加寬後會被判為
        「數字＋版」而誤紅——那是把「第幾輪的版本」誤讀成「幾個版本」。
        修法選**改寫散文**（在輪次號與「版本」之間插一個「的」）而不是在
        偵測器裡開豁免：豁免表本身就是下一個 stale 站點（本檔判準(1) 的錯誤訊息就是這麼
        寫的，round 3 四方複審又在判準(2) 的 `Spec.historical` 上重演了一次）。
        本支釘住「改寫後的寫法確實不再命中」，改回去就會紅。
        """
        for sample in (
            "round 2 的版本這一條只是人審慣例冒充機制",
            "見 round 3 的版本說明",
            "ADR §4.3 的兩條件",
        ):
            with self.subTest(sample=sample):
                self.assertIsNone(_BARE_COUNT_RE.search(sample))


class TestSc6PatternIsNotEnumerationBound(unittest.TestCase):
    """R69（DEF-101-702／R68-27）：SC-6 的樣式不得再退回「列舉幾個數字」的寫法。

    WHY（為何這支測試存在，而不只是改個 regex 就算了）：SC-6 要守的**就是「條數」這個
    會成長的量**，而它自己的偵測樣式卻把數字寫死成 `三|四|五|六`——於是 §9.1 長到 8 條
    之後，今天唯一寫得出來的違規形態（七／八／阿拉伯數字）全部從鎖底下走掉，鎖只對
    「已經不可能發生的歷史錯值」有效。這是 Scan-H 判準②「鎖自己也會 stale」的樣本：
    一支鎖若對它所守護對象的**當前值**沒有鑑別力，綠燈不代表合規。
    """

    def test_forms_writable_today_are_all_detected(self) -> None:
        """今天最可能被寫下的六種形態必須全部命中（修前：後五種全部漏抓）。"""
        for sample in (
            "本節共四條可轉紅不變式，逐條照抄即可。",   # 歷史錯值（修前唯一抓得到的）
            "本節共七條可轉紅不變式。",
            "本節共八條可轉紅不變式。",
            "本節共十條可轉紅不變式。",
            "本節共 8 條可轉紅不變式。",
            "§9.1 的可轉紅不變式共 12 條。",
        ):
            with self.subTest(sample=sample):
                self.assertIsNotNone(
                    _SC6_RE.search(sample),
                    "SC-6 樣式漏抓一個今天寫得出來的條數宣稱 —— 樣式又被寫成列舉了？",
                )

    def test_the_real_adr_stays_green(self) -> None:
        """反誤紅：泛化後對真實 ADR 全檔不得有任何命中（命中數現查，本處刻意不寫）。"""
        self.assertEqual(sc6_no_hardcoded_invariant_count(read_corpus()), [])

    def test_inject_sample_tracks_the_live_count(self) -> None:
        """注入樣本必須跟著 §9.1 現查條數走，不得凍在某個歷史值上。"""
        corpus = read_corpus()
        live_n = len(_SC_DECL_RE.findall(adr2_section_91(corpus.adr2)))
        self.assertGreater(live_n, 0, "§9.1 抽不到任何 `# SC-N` 宣告 —— 掃描面崩塌")
        token = _SC6_CJK_DIGITS[live_n] if live_n < len(_SC6_CJK_DIGITS) else str(live_n)
        self.assertIn(f"共{token}條", _sc6_inject(corpus))


# ================================================ Scan-H 三元組（UEP／AC／GLC）的機械承接者
# 🔴 R75（本輪 BLOCKING 的落地物）：`CrossPlatform_Scan_Dimensions.md` Scan-H 的通過判準在
# R74 被改寫成「三元組**逐輪登記**完整 ＋ 反位移未發生 ＋ 護欄層規模趨勢有量測」，而「逐輪
# 登記」的承接者是**人**——每輪收尾把三個數字手抄進 `ADR-XPLAT-002` §4.3.1 的表。實況：該表
# 自 R69 之後零新增列，其後連續數輪零登記 ⇒ **新判準在寫下的當輪即不成立**。同一輪對孿生案例
# （§6 邊界 1 覆蓋表缺列）正確地上了 SC-10，卻把這一半留成散文交棒 ⇒ 同一個「缺席型漏做不會
# 轉紅」的病治了一邊，而留下的那邊剛好就是新判準本身。
#
# 🔴 為何**不**仿 SC-10 再加一條「當前輪沒有登記列即紅」的缺席型判準（架構決定，ADR §4.3.1
# R75 裁決；本段是那道裁決的機械面）：那會讓一道鎖去**強制製造手抄常數**。§9.1 邊界 (d-2)
# 逐字記載 §4.3／§4.3.1 的量測數字沒有機械承接者，而 ARCH-R67R2-01 在 §4.3.1 抓到的正是一個
# 「量測 → 寫進文件 → 同輪後續波次讓它失真」的常數，當時的處置是**移除常數、改指現查指令**；
# 逼人逐輪手抄＝把那次處置反向執行。且現存兩組配對量測的段首都自陳「量測面髒 ⇒ 不得作為新
# 基線」、GLC 行數欄從一開始就只寫「見上列指令」⇒ 這個儀式在最順利的情況下，產出的也是自陳
# 不可用的資料。⇒ 判準改為「三元組**由機械物一次取齊且不退化**」，由本段承接。
class Triplet(NamedTuple):
    """Scan-H 三元組的現查值（同一個工作樹、同一次呼叫取齊——跨時點取值本身即無效）。"""

    uep: int
    ac: int
    glc_files: int
    glc_lines: int


def live_triplet() -> Triplet:
    """三元組一次取齊。

    UEP／AC 一律走生產碼 `check_script_parity` 的**同一份計算**（`_EXEMPT_PAIRS` 與
    `ac_registries()`），本檔不重寫公式：§4.2 的 AC 早在 R67-H34 就從寫死算式改為對具名清單
    動態求值，照抄算式等於把那次修復退回去，並多開一個會漂移的站點。
    GLC 用的 glob 逐字等於 ADR §4.3／§4.3.1 現查指令裡那一個（`tools/tests/*.py`，非遞迴），
    刻意**不**重用 `guard_files_in_worktree()`——後者遞迴且只數 `test_*.py`（護欄層檔數棘輪的
    量測面），兩個量不同名也不同義，混用會讓 ADR 的指令與本檔的數字對不起來。
    """
    import check_script_parity as P  # noqa: PLC0415  # 延後 import：避開 import 期副作用

    files = sorted((_REPO / _GUARD_DIR_REL).glob("*.py"))
    return Triplet(
        uep=len(P._EXEMPT_PAIRS),
        ac=sum(len(reg) for reg in P.ac_registries().values()),
        glc_files=len(files),
        glc_lines=sum(
            len(f.read_text(encoding="utf-8", errors="replace").splitlines()) for f in files
        ),
    )


# 🔴 凍結對＝R75 落地當回合的現查值，**不做任何推算**（同 `_FROZEN_GUARD_LINES` 的
# 「填實測值」紀律：R57 三度用算式推 `MIN_TESTS`，三度當場與實況不符）。
# 這兩個常數是本檔對該量的**唯一宣告**、不是散文複本；與現況的一致性由
# `test_the_frozen_pair_matches_the_live_values` 強制（多退少補都紅），所以「凍結值停在舊
# 高點、餘裕變成破口」在本檔結構上留不住（同 SA-R67-08 對可被自由調高的假棘輪的裁決）。
_FROZEN_SCAN_H_UEP = 5
# R76：AC 由 48 下修為 47——`_SINGLE_SIDED_EXEMPT` 少一筆（reschedule_g0_gatecheck.ps1
# 整支刪除，真孤兒）。方向是**下降**＝收斂，非 §4.2 規則 2 所管的上升情形；下降時本值
# 必須跟著降，否則凍結值停在舊高點、餘裕就成了日後無聲加回一筆豁免的破口。
_FROZEN_SCAN_H_AC = 47


def synthetic_at_par() -> Triplet:
    """紅綠自證用的**合成**基底：恰好等於凍結對、GLC 量測面非空 ⇒ 自身零違規。

    🔴 刻意不用現查值當基底（本段落地時第一版就是那樣寫的，注入實測當場暴露問題）：一旦
    工作樹真的退化，那幾支「注入後必紅」與「對照組必綠」會**跟著一起紅**——它們的基底被
    污染了。後果不是漏抓而是**紅燈失去指向性**：一筆真實的 UEP 回歸會同時點亮數支測試，
    讀者無從判斷哪一支在講真實違規、哪一支只是基底被帶壞。本檔對「零串音」的要求
    （見 `test_only_the_matching_check_reds`）在這裡是同一條紀律。
    GLC 兩欄只要非零即可——它們在本函式的用途是「量測面沒崩塌」的哨兵，不是量測值。
    """
    return Triplet(uep=_FROZEN_SCAN_H_UEP, ac=_FROZEN_SCAN_H_AC, glc_files=1, glc_lines=1)


def scan_h_problems(frozen_uep: int, frozen_ac: int, current: Triplet) -> list[str]:
    """Scan-H 判準的違規清單（空＝通過）。三款逐字對應 ADR §4.2 判定規則與 §4.3 的報表定位。

    (1) **UEP 不得上升**：UEP 量的是「零機械守門的雙平台等價宣稱」數，上升＝豁免列長回來。
        刻意不要求「必須下降」——§4.1 的地板是可辯護殘留，要求下降會讓本維度依定義不可能
        通過，那正是 R74 認定舊判準不可達的理由。
    (2) **AC 上升時必須同時有 UEP 下降**（§4.2 判定規則 2 的逐字機械化）。只擋「UEP 未降而
        AC 上升」，**不擋**規則 2 明文允許的「類別升級帶動 AC 上升」——把後者也判紅就是把
        「不計為收斂成果」超譯成「禁止」（同 `guard_count_problems` 不把改名判紅的理由）。
    (3) **GLC 量測面不得崩塌**：GLC 是報表、不設上限（§4.3 已用兩組實測否決兩種上限設計），
        但「算不出來」必須 fail-loud——glob 對錯路徑回空清單，在原語意下等同「零行」＝假綠。
    """
    problems: list[str] = []
    if current.uep > frozen_uep:
        problems.append(
            f"UEP 由 {frozen_uep} 上升為 {current.uep} —— ADR-XPLAT-002 §4.1 的 UEP 只准往下，"
            "上升代表又多了一份沒有任何機械守門的雙平台等價宣稱。"
            "現查：python tools/check_script_parity.py --print-collapse"
        )
    if current.ac > frozen_ac and current.uep >= frozen_uep:
        problems.append(
            f"AC 由 {frozen_ac} 上升為 {current.ac}，而 UEP 未下降（仍為 {current.uep}）——"
            "§4.2 判定規則 2 判定為「換個地方複雜」：每一筆 AC 上升必須在同一個 commit 內"
            "具名對應一筆 UEP 下降。合法出口＝同 commit 讓 UEP 降下來，並同步下修本檔凍結對。"
        )
    if current.glc_files <= 0:
        problems.append(
            f"GLC 量測面抽不到任何 {_GUARD_DIR_REL}/*.py —— 掃描面崩塌（目錄改名／glob 寫壞？）。"
            "GLC 不設上限，但算不出來一律紅：空清單在原語意下等同「零行」＝假綠。"
        )
    return problems


class TestScanHTripletIsTheLiveCriterion(unittest.TestCase):
    """Scan-H 通過判準的可執行本體（R75 起取代 §4.3.1 的逐輪手抄登記）。

    WHY：判準若只是散文，缺席型的漏做不會讓任何東西轉紅——那正是本判準上一版在寫下的當輪
    就已不成立的機制。本類把「三元組一次取齊 ＋ 不退化」接上閘門的 rc，並在 `setUpClass`
    印出單行報表：§4.3.1 建立時要的「三個數字同時出現」自此由**每次跑閘門**承接，而不是
    由「某人每輪記得抄」承接。
    """

    live: Triplet

    @classmethod
    def setUpClass(cls) -> None:
        cls.live = live_triplet()
        # 報表行刻意全 ASCII：本檔的消費者含 Windows 排程環境（console codepage 950），
        # 一行報表不該成為編碼事故的來源。
        print(
            f"[Scan-H triplet] UEP={cls.live.uep} AC={cls.live.ac} "
            f"GLC_FILES={cls.live.glc_files} GLC_LINES={cls.live.glc_lines}"
        )

    def test_the_live_triplet_satisfies_the_scan_h_criterion(self) -> None:
        """判準必須在**本 commit** 上成立——這一支就是「判準不是寫下來就過期」的那條證據。"""
        problems = scan_h_problems(_FROZEN_SCAN_H_UEP, _FROZEN_SCAN_H_AC, self.live)
        self.assertEqual(
            problems, [],
            "Scan-H 判準在現行工作樹上不成立：\n  " + "\n  ".join(problems),
        )

    def test_the_frozen_pair_matches_the_live_values(self) -> None:
        """自緊：凍結對必須與現況逐字相等（多退少補都紅）。

        WHY：只擋「上升」的棘輪會累積餘裕——UEP／AC 降下來之後若不同步下修凍結值，之後可以
        無聲地把它們「加回」那個舊高點。這與 `guard_line_problems` 的 `[基準過時]` 那一款
        是同一個形狀、同一個理由。
        """
        self.assertEqual(
            (self.live.uep, self.live.ac), (_FROZEN_SCAN_H_UEP, _FROZEN_SCAN_H_AC),
            "凍結對與現況已漂移——UEP／AC 降下來後請同步下修本檔的 _FROZEN_SCAN_H_* 以維持"
            "棘輪張力；若是上升，請先讀 ADR-XPLAT-002 §4.2 判定規則 2（AC 上升必須具名對應"
            "一筆 UEP 下降）。現查：python tools/check_script_parity.py --print-collapse",
        )

    def test_the_synthetic_base_is_itself_green(self) -> None:
        """反空轉：合成基底自己必須零違規，否則下面各支「注入後必紅」全部無鑑別力（恆紅）。"""
        self.assertEqual(
            scan_h_problems(_FROZEN_SCAN_H_UEP, _FROZEN_SCAN_H_AC, synthetic_at_par()), [],
            "合成基底自身即違規 —— 注入測試會恆紅，等於沒有鑑別力",
        )

    def test_a_uep_rise_is_red(self) -> None:
        """注入①：UEP 長回一階（＝把一對已納管的腳本退回零守門的決策豁免）必須紅。"""
        risen = synthetic_at_par()._replace(uep=_FROZEN_SCAN_H_UEP + 1)
        problems = scan_h_problems(_FROZEN_SCAN_H_UEP, _FROZEN_SCAN_H_AC, risen)
        self.assertTrue(problems, "UEP 上升未被偵測 —— 棘輪失效")
        self.assertIn("UEP", problems[0])

    def test_an_ac_rise_without_a_uep_drop_is_red(self) -> None:
        """注入②：反位移（AC 上升而 UEP 不動）必須紅——這是 §4.2 判定規則 2 的射程。"""
        displaced = synthetic_at_par()._replace(ac=_FROZEN_SCAN_H_AC + 1)
        problems = scan_h_problems(_FROZEN_SCAN_H_UEP, _FROZEN_SCAN_H_AC, displaced)
        self.assertTrue(problems, "反位移未被偵測 —— 判定規則 2 沒有機械面")
        self.assertIn("AC", problems[0])

    def test_an_ac_rise_paired_with_a_uep_drop_is_accepted(self) -> None:
        """對照組：AC 上升**且** UEP 同時下降＝§4.2 判定規則 2 明文允許的類別升級 ⇒ 綠。

        測意圖：擋的是「換個地方複雜」，不是「AC 不准動」。若這裡誤紅，下一個人為了做
        「零守門 → hash 釘選」的升級就得先把鎖關掉——本檔檔頭反覆講的那種賠掉全部價值的
        失敗模式。
        """
        upgraded = synthetic_at_par()._replace(
            ac=_FROZEN_SCAN_H_AC + 4, uep=_FROZEN_SCAN_H_UEP - 1,
        )
        self.assertEqual(
            scan_h_problems(_FROZEN_SCAN_H_UEP, _FROZEN_SCAN_H_AC, upgraded), [],
            "把規則 2 允許的類別升級判成違規＝超譯裁決",
        )

    def test_a_collapsed_glc_measurement_surface_is_red(self) -> None:
        """注入③：GLC 量測面歸零（目錄改名／glob 寫壞）必須紅，不得靜默當成「零行」。"""
        collapsed = synthetic_at_par()._replace(glc_files=0, glc_lines=0)
        problems = scan_h_problems(_FROZEN_SCAN_H_UEP, _FROZEN_SCAN_H_AC, collapsed)
        self.assertTrue(problems, "GLC 掃描面崩塌未被偵測 —— fail-open")
        self.assertIn("GLC", problems[0])

    def test_both_specs_name_this_carrier(self) -> None:
        """規格 ↔ 實作雙向綁定：ADR 與維度表都必須指名本類。

        WHY：本輪修的病就是「判準寫在散文裡、承接者不存在」。若兩份規格說得出通過判準卻
        指不出承接者，或本類改名而散文沒跟，那句宣稱又會變成死信（同 SC-8 的形態，只是死
        的不是豁免標記而是承接者）。
        """
        for path in (_ADR2, _SCAN_DIMS):
            with self.subTest(spec=path.name):
                self.assertIn(
                    type(self).__name__, path.read_text(encoding="utf-8"),
                    f"{path.name} 未指名 Scan-H 三元組的承接者 {type(self).__name__} —— "
                    f"判準與承接者失聯；本類改名時請同步兩份規格",
                )


# ══════════════════════════════════════════════════════════════════ R78 ARCH-02：重釘入口
# 🔴 缺陷本體：棘輪的紅燈訊息（`guard_line_problems` 的 `[基準過時]`／`glc_growth_problem`）
# 逐字教操作者跑 `--print-guard-lines`，而 R77 從未實作它——skeptic 實跑 rc=2
# `unrecognized arguments`，AST 側證全檔沒有任何 `argparse`。後果不是「少個小工具」：
# 棘輪一紅，唯一出路變成**逐列手改整張凍結表**，而那樣改的人不會順手算淨額
# ⇒ 這條缺口與 ARCH-01（淨額無處可見）是同一件事的兩端。
#
# 刻意**不引入 argparse**：本檔是 unittest 檔，多一個 parser 就多一條會與 `unittest.main()`
# 搶 `sys.argv` 的路徑。旗標集合是一個 frozenset，判準讀它。
_DISPATCHED_FLAGS: frozenset[str] = frozenset({"--print-guard-lines"})
#: 「本檔自己被指名要怎麼跑」的形狀——只認**指名本檔**的呼叫，別的工具的旗標不歸本判準管。
_SELF_INVOCATION_RE = re.compile(r"test_adr_xplat001_c1c2_lock\.py\s+(--[a-z][a-z0-9-]*)")


def self_invocation_flag_problems(text: str, dispatched: Iterable[str]) -> list[str]:
    """**雙向**：訊息教的旗標必須跑得動，宣告的旗標必須有人教（空＝通過）。

    (1) `[死指令]` 文字裡出現「指名本檔 ＋ 一個旗標」的呼叫，而那個旗標沒被分派
        ⇒ 照著做會拿到 rc=2。這是 R78 ARCH-02 的修前實況。
        （本段刻意不示範一個假旗標字面：掃描面就是本檔全文，示範會讓活體判準自己轉紅。）
    (2) `[孤兒旗標]` 分派了卻沒有任何一行教人用 ⇒ 沒有消費者的入口會靜默腐爛，
        而下一個人讀紅燈訊息時仍然找不到路（同一個病的另一面）。

    誠實劃界：本判準保證「旗標名對得上」，**不保證那個旗標印出來的東西是對的**——
    後者由 `test_the_repin_command_emits_a_pastable_table` 真跑一次來證。
    """
    named = set(dispatched)
    mentioned = set(_SELF_INVOCATION_RE.findall(text))
    problems = [
        f"[死指令] 文字教人跑 `{flag}`，但 __main__ 沒有分派它——照著做會拿到 rc=2 "
        f"`unrecognized arguments`（R78 ARCH-02 的修前實況）"
        for flag in sorted(mentioned - named)
    ]
    problems += [
        f"[孤兒旗標] `{flag}` 已分派卻沒有任何一行教人用——入口會靜默腐爛"
        for flag in sorted(named - mentioned)
    ]
    return problems


# ══════════════════════════════════════════════════════════════════════════════
# ADR-XPLAT-013：計價規則變更的**豁免載體** ＋ 觀察模式 5 輪時效的**到期載體**
# ══════════════════════════════════════════════════════════════════════════════
# 兩者共用同一個「現在是第幾輪」的時鐘＝`_GUARD_LINES_REPIN_LOG` 末列的輪號（同
# `repin_cost_ratchet_problems()` 的 `live_round`）。刻意不另開第二個輪次時鐘：本 repo
# 已有判例（`run_root_unittests.py` 的 MIN_TESTS 註記）記載「在 .py 裡開第二個輪次
# 時鐘」的代價。

#: 條文三：**計價規則變更輪**的零緩衝豁免到期時點。豁免的內容只有一件事——那一輪不必
#: 把 `AutoClaude/.loc_baseline` 重釘為改後 total 的實測值（ADR-XPLAT-012 條文五 §3 的
#: 「當回合實測直接填入、零加減推算、不留成長緩衝」）。掌舵者裁決的理由：換計價器當輪的
#: total 位移不是「這一輪長了多少」，立刻重釘會把整段位移一次性沒收，而改前餘裕的實測值
#: 是 12 行（後續包連接線都加不進去）。
#: 🔴 判準＝`pricing_exemption_problems()`：稽核痕跡走到本值**之後**，`.loc_baseline`
#: 仍高於實測 total 即紅。出口是一行 diff（`python AutoClaude/tools/check_loc_budget.py
#: --update`），永遠開著。本常數只准調小（更早到期＝更嚴），刻意不留延期參數——可延期的
#: 到期日不是到期日（同 `_REPIN_NET_CAP_DUE_ROUND` 的設計）。
_PRICING_CHANGE_EXEMPT_ROUND = 100
#: 方向鎖的基準（形狀照 `frozen_ratchet_problems()`：基準是簽入本檔的字面常數，比較在
#: 任何時點都非退化；若改用 git 導出基準，commit 一落地基準就等於現值）。
_FROZEN_PRICING_CHANGE_EXEMPT_ROUND = 100

#: 條文五 §6「5 輪時效」的機械載體——ADR-XPLAT-012 自己的〈未解決缺口〉節逐字自陳
#: 「散文寫了 5 輪、沒有具名常數與判準」，本表即那一項的承接。**append-only**：
#: `(輪號, 結局標記, 理由)`。結局標記取封閉表 `_PHASE2_OUTCOMES`——§6 只給兩條合法出路
#: （提出 Phase 2 提案並走複審／具名記錄「決定維持觀察模式」的理由並重新武裝下一個視窗），
#: 第三個是「已落地」。首列是視窗的起算錨（Phase 1 觀察模式落地的那一輪）。
_PHASE2_OUTCOMES: tuple[str, ...] = ("[提案]", "[維持觀察]", "[落地]")
#: 視窗長度＝條文五 §6 的字面「5 輪」。只准調小（視窗更短＝更嚴）。
_PHASE2_REVIEW_WINDOW = 5
_FROZEN_PHASE2_REVIEW_WINDOW = 5
#: 連續「維持觀察」的上限。**這是本表真正的牙**：§6 允許「重新武裝下一個視窗」，若不設
#: 上限，每一輪貼一行 `[維持觀察]` 就能無限期買下去——那正是 §6 自己寫的「不留無限期
#: 空轉的觀察機制」要防的事。只准調小（同 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`）。
_PHASE2_MAX_CONSECUTIVE_DEFERRALS = 1
_FROZEN_PHASE2_MAX_CONSECUTIVE_DEFERRALS = 1
_PHASE2_REVIEW_LOG: tuple[tuple[int, str, str], ...] = (
    (99, "[維持觀察]",
     "Phase 1 觀察模式落地（ADR-XPLAT-012 條文五 §1，只印不擋）——條文五 §6 的 5 輪視窗"
     "自本列起算。當輪未提出 Phase 2 提案，該 ADR 的〈狀態〉節逐字寫「Phase 2（阻斷模式）："
     "未落地、未提案」。"),
    (100, "[落地]",
     "Phase 2 方向 (a) 落地（ADR-XPLAT-013）：`check_loc_budget.count_loc()` 改為以分類器的"
     "斷言桶計價 ⇒ 觀測欄位自此參與 rc／violations，阻斷模式對這一個方向已生效。方向 (b)(c) "
     "未落地、交棒收尾單人窗口，故視窗依 §6 重新武裝一次（到期輪隨末列前移）。"),
    (106, "[維持觀察]",
     "本輪是 windows-compat-ci／root-infra-ci 兩筆跨平台缺陷修復輪，未觸碰 ADR-XPLAT-013"
     "方向 (b)(c)，亦未提出新 Phase 2 提案，依 §6 重新武裝下一個視窗。"),
    (113, "[提案]",
     "掌舵者已裁決 ADR-XPLAT-013 三方向全做（存證＝AutoSDD_TechDebt_Paydown_Playbook.md"
     " §6 第 1 條：Phase 1 assertion-only 已落地；(b)(c) 為到期義務、載體 DEF-200-211，"
     "『維持觀察』名額已被上一列用罄——該條逐字寫『到期只能提案或落地』）。本列把該既存"
     "裁決記入機械載體＝提案成立；四方複審與 (b)(c) 落地由 DEF-200-211 承接（與 "
     "DEF-200-207 ADR 轉 Accepted 同批四方複審），不隨結構性長債分軌輪落地。"),
    (116, "[落地]",
     "(b) 分軌計價落地（D-1＝S-2）：`_REGRESSION_LANE_LOG`／`lane_split_problems()`／"
     "`repin_growth_problems(regression_lane=...)`，`_REGRESSION_LANE_SINCE=117`"
     "（不追溯）；D-2 M1 拆雙指標；D-6 cap 實測取值 309。(c) 依 D-4 裁決**降級為觀測"
     "欄**（`guard_line_composition()`，只印不擋）而非全量落地——裁決存證＝"
     "AutoSDD_Adjudication_Record_R110.md §1.4；(c) 是否轉阻斷留待 R117+ 依觀測資料"
     "再議，不再佔用本表的『維持觀察』名額。"),
    (122, "[維持觀察]",
     "本輪是精準修復輪（帳本三筆缺陷結案＋護欄層散文搬遷抵銷），未觸碰 ADR-XPLAT-013 "
     "方向 (c) 是否由觀測轉阻斷的議題，亦未提出新 Phase 2 提案。(c) 依 R110 §1.4 裁決"
     "仍為觀測欄，其轉阻斷所需的觀測資料由 `guard_line_composition()` 持續累積（本輪"
     "收尾窗口的觀測欄實測值見 `--print-guard-lines` 末行）。上一列是 `[落地]` ⇒ 款(5) "
     "的連續『維持觀察』計數自本列起算為一，未觸上限。依 §6 重新武裝下一個視窗。"),
)
#: 到期輪由末列導出、不另立常數（一份知識一個家；同 `_REPIN_NET_CAP_SCHEDULE` 的
#: 「生效點＝首列、現值＝末列，皆由表導出」）。
_PHASE2_DUE_ROUND = _PHASE2_REVIEW_LOG[-1][0] + _PHASE2_REVIEW_WINDOW


def live_repin_round(log: Sequence[tuple[str, int, int, int, str]] | None = None) -> int:
    """稽核痕跡上的最大輪號＝本檔各到期判準共用的時鐘（推不出回 0）。

    抽成具名函式而不是各處重寫一遍 `max(...)`：`repin_cost_ratchet_problems()` 早已
    在做同一件事，第二份手抄本就是本檔一路在治的病。
    """
    rows = _GUARD_LINES_REPIN_LOG if log is None else log
    return max((no for no, _d in repin_round_nets(rows)), default=0)


def pricing_exemption_problems(
    latest_round: int | None = None,
    baseline: int | None = None,
    total: int | None = None,
    *,
    exempt_round: int = _PRICING_CHANGE_EXEMPT_ROUND,
    frozen_exempt_round: int = _FROZEN_PRICING_CHANGE_EXEMPT_ROUND,
    baseline_policy_version: str | None = None,
    current_policy_version: str | None = None,
) -> list[str]:
    """計價規則變更豁免的到期判準（空＝通過）。純函式，紅綠由合成注入自證。

    三款，各帶方括號標籤（本檔的零串音紀律）：
      (1) `[量不到]` `baseline`／`total` 任一取不到 —— 取不到就沒有東西可判，而
          「讓它取不到」正是最省力的滿足方式（同 `repin_log_problems()` 款(1) 的理由）。
      (2) `[豁免過期]` 稽核痕跡已走到豁免輪**之後**，而 baseline 的 provenance
          （`baseline_policy_version`）不等於目前這把尺（`current_policy_version`）——
          出口＝重釘 baseline（`--update`，一行 diff，同時寫回 provenance），永遠開著。
          🔴 **DEF-200-208 訂正**：改前的判準是 `baseline > total`（大小關係），把
          「已重釘」判成「baseline ≤ total」——這個不等式在計價規則本身改變時**沒有
          固定方向**：R100 §E-4 全樹實測 `total` 反而由 17032 升為 17079（+47，並非
          預期中的下降），於是「未重釘」與「total 長過陳舊 baseline」在這組真實資料上
          變成**同一個條件的兩種相反解讀**，`baseline > total` 對兩者都判 False ⇒
          本款結構上恆假、永久靜音（`test_the_next_round_cannot_reuse_the_exemption`
          的前提斷言 `assertGreater(baseline, total)` 因此直接炸掉，而不是判準本身
          發現任何東西）。改為 provenance 比對後，判準只問「這份 baseline 是不是用
          現在這把尺釘的」，不再從數字大小反推狀態，兩個方向都接得住。
      (3) `[豁免被延期]` 豁免輪被調大 —— 本常數只准調小。調大它就是把「豁免只限一輪」
          這件事本身取消掉，而「口頭承諾＝零機制＝真的空轉」在本 repo 已有實證。

    誠實劃界：本判準保證「豁免不會活過那一輪」，**不保證那一輪的豁免是對的**（那是
    修憲程序與人審的責任），也不看 `TOTAL_INCREASE_LIMIT` 那 20% 的結構性緩衝——那是
    ADR-SD07-001 的既有設計，不在本條文射程內。`baseline_policy_version`／
    `current_policy_version` 任一為 `None`（含兩個都沒傳——呼叫端忘記接線的預設狀態）
    一律判定**未重釘**（安全預設：無法確認就當沒發生，不是放行）。
    """
    problems: list[str] = []
    if exempt_round > frozen_exempt_round:
        problems.append(
            f"[豁免被延期] 豁免輪由 {frozen_exempt_round} 推遲為 {exempt_round}——"
            "本常數只准調小。它不是門檻而是**到期日**：往後挪等於把「只限計價規則變更"
            "當輪」磨成一個永久豁免，而那正是本載體立案要防的形態（沒有機械載體的豁免"
            "＝口頭承諾，本 repo 已實證會真的空轉）")
    if not baseline or not total:
        problems.append(
            f"[量不到] baseline={baseline}／total={total} 任一為 0 或 None ⇒ 本判準沒有"
            "母體可判。現查：`python AutoClaude/tools/check_loc_budget.py --json` 的 "
            "`baseline`／`total` 兩欄；讀不到檔或掃不到檔一律當失效，不是放行")
        return problems
    live = live_repin_round() if latest_round is None else latest_round
    policy_repinned = (
        baseline_policy_version is not None
        and current_policy_version is not None
        and baseline_policy_version == current_policy_version
    )
    if live > exempt_round and not policy_repinned:
        problems.append(
            f"[豁免過期] 稽核痕跡已走到 R{live}（豁免輪＝R{exempt_round}，只涵蓋那一輪），"
            f"而 AutoClaude/.loc_baseline 的 provenance＝{baseline_policy_version!r}，"
            f"不等於目前這把尺 {current_policy_version!r}（baseline={baseline}／"
            f"total={total} 僅供對照，本判準不再從兩者大小反推狀態——見上方 DEF-200-208"
            "訂正）。出口只有一個且永遠開著：`python AutoClaude/tools/check_loc_budget.py "
            "--update`（一行 diff，同時重釘 baseline 數值與 provenance）。"
            "🔴 反向出口已封：不得調大 _PRICING_CHANGE_EXEMPT_ROUND 讓紅字消失"
            "（款(3) 的方向鎖只准調小），也不得偽造 baseline_policy_version")
    return problems


def phase2_review_problems(
    log: Sequence[tuple[int, str, str]] | None = None,
    latest_round: int | None = None,
    *,
    window: int = _PHASE2_REVIEW_WINDOW,
    frozen_window: int = _FROZEN_PHASE2_REVIEW_WINDOW,
    max_deferrals: int = _PHASE2_MAX_CONSECUTIVE_DEFERRALS,
    frozen_max_deferrals: int = _FROZEN_PHASE2_MAX_CONSECUTIVE_DEFERRALS,
) -> list[str]:
    """ADR-XPLAT-012 條文五 §6「5 輪時效」的判準（空＝通過）。純函式，紅綠由注入自證。

    六款：
      (1) `[空表]` 一列都沒有 —— 整張表被刪掉時下面幾條全部無事可判＝fail-open。
      (2) `[輪號未遞增]` —— 到期輪由**末列**導出，輪號不遞增時「誰在位」的語意不成立。
      (3) `[結局不在封閉表]` —— §6 只給兩條出路（＋「已落地」），開放式字串等於沒有分類，
          款(5) 的連續計數就無從判起。
      (4) `[無理由]` 理由欄過短 —— 「延期」兩個字不是理由（同 `repin_log_problems()` 款(5)）。
      (5) `[連續空轉]` 連續 `[維持觀察]` 超過上限 —— §6 允許重新武裝視窗，本款讓
          「每輪貼一行就能無限期買下去」有代價。
      (6) `[時效逾期]` 稽核痕跡已走過末列 ＋ 視窗 —— 到期而無任何 §6 決議。
      (7) `[視窗被放寬]`／`[上限被放寬]` 兩個代價常數被調大 —— 只准調小。
    """
    rows = list(_PHASE2_REVIEW_LOG if log is None else log)
    problems: list[str] = []
    if window > frozen_window:
        problems.append(
            f"[視窗被放寬] 視窗由 {frozen_window} 輪放寬為 {window} 輪——只准調小。"
            "放寬它就是把條文五 §6 的「5 輪」改成一句可以自己改的話")
    if max_deferrals > frozen_max_deferrals:
        problems.append(
            f"[上限被放寬] 連續維持觀察上限由 {frozen_max_deferrals} 調升為 "
            f"{max_deferrals}——只准調小。調高它＝把「不留無限期空轉的觀察機制」取消掉")
    if not rows:
        problems.append(
            "[空表] _PHASE2_REVIEW_LOG 一列都沒有——條文五 §6 的時效又回到「只寫在散文裡」"
            "的狀態（該 ADR 自己的〈未解決缺口〉節就是在說這件事）。至少要有起算錨那一列")
        return problems
    for (r0, _o0, _x0), (r1, _o1, _x1) in zip(rows, rows[1:]):
        if r1 <= r0:
            problems.append(
                f"[輪號未遞增] R{r0} 之後又出現 R{r1}——到期輪由末列導出，"
                "輪號不遞增時末列的語意不成立（同 `net_cap_schedule_problems()`）")
    run = 0
    for rnd, outcome, reason in rows:
        if outcome not in _PHASE2_OUTCOMES:
            problems.append(
                f"[結局不在封閉表] R{rnd} 的結局標記 {outcome!r} 不在 {_PHASE2_OUTCOMES}"
                "——封閉表刻意禁止擴表：開放式字串會讓款(5) 的連續計數無從判起")
        if len(reason.strip()) < 20:
            problems.append(
                f"[無理由] R{rnd} 那一列的理由欄只有 {len(reason.strip())} 字——"
                "「延期」兩個字不是理由；每一次重新武裝都要有人負責解釋")
        run = run + 1 if outcome == "[維持觀察]" else 0
        if run > max_deferrals:
            problems.append(
                f"[連續空轉] 到 R{rnd} 已連續 {run} 次 `[維持觀察]`，上限是 "
                f"{max_deferrals} 次——條文五 §6 逐字寫「不留無限期空轉的觀察機制」。"
                "合法出口：提出 Phase 2 提案（`[提案]`）或讓某個方向真的落地（`[落地]`），"
                "連續計數即歸零。**不要調高上限**——它只准下修")
    live = live_repin_round() if latest_round is None else latest_round
    due = rows[-1][0] + window
    if live > due:
        problems.append(
            f"[時效逾期] 稽核痕跡已走到 R{live}，超過到期輪 R{due}"
            f"（末列 R{rows[-1][0]} ＋ 視窗 {window} 輪）而 _PHASE2_REVIEW_LOG 沒有新列。"
            "條文五 §6 給的兩條合法出路：①提出 Phase 2 提案並走條文六的四方複審"
            "（追加一列 `[提案]`）；②具名記錄「決定維持觀察模式」的理由並重新武裝下一個"
            "視窗（追加一列 `[維持觀察]`，但受款(5) 的連續上限管）。"
            "刻意沒有「延期」參數——可延期的到期日不是到期日")
    return problems


def _loc_pricing_facts() -> tuple[int, int, str | None]:
    """現查 `(baseline, total, baseline_policy_version)`——三個都是量測值，刻意不寫死
    在本檔（DEF-200-208 追加第三項：baseline 是用哪一把尺釘的 provenance）。

    走 `AutoClaude/tools/check_loc_budget.py` 的公開面（`read_baseline()` ＋
    `build_reports()` ＋ `read_baseline_policy_version()`），與
    `test_block_destructive_git_r83.py` 取用該模組的方式同一條路。
    """
    sys.path.insert(0, str(_REPO / "AutoClaude" / "tools"))
    import check_loc_budget as CLB  # noqa: PLC0415
    baseline = CLB.read_baseline() or 0
    total = sum(r.loc for r in CLB.build_reports(CLB.load_overrides()))
    return baseline, total, CLB.read_baseline_policy_version()


def _current_policy_version() -> str:
    """現查 `check_loc_budget.POLICY_VERSION`——「目前這把尺叫什麼名字」的單一出處。

    抽成具名函式而不是在三個呼叫點各自 import 一次：本檔已有的教訓（同一模組匯入
    散落多處）就是下一輪會漂移的複本。
    """
    sys.path.insert(0, str(_REPO / "AutoClaude" / "tools"))
    import check_loc_budget as CLB  # noqa: PLC0415
    return CLB.POLICY_VERSION


class TestPricingChangeExemptionExpiresOnItsOwn(unittest.TestCase):
    """🔴 ADR-XPLAT-013 條文三：計價規則變更豁免的**機械載體**。

    WHY 這一格非有不可：本輪的豁免內容是「不把 `.loc_baseline` 重釘為改後實測 total」，
    釋出的餘裕行數是四位數（現值一律現查 `--json` 的 `cap - total`，本檔不寫死）。散文
    形態的「只限這一輪」在本 repo 已實證攔阻力為 0（記憶索引那條「承諾沒機制會真的空轉」
    ＝三小時真空轉的實測）。所以豁免必須自己會過期。

    紅綠對照：今天為綠（豁免輪就是本輪）／走過豁免輪而 baseline 的 provenance 未指向
    目前這把尺為紅／重釘之後回綠（鎖有出口）／豁免輪被調大為紅（方向鎖）／
    量不到為紅（fail-loud）。
    """

    def test_the_exemption_is_green_only_inside_its_own_round(self) -> None:
        baseline, total, baseline_policy_version = _loc_pricing_facts()
        self.assertGreater(total, 0, "掃不到 total ⇒ 本組鎖沒有母體（fail-loud，不是放行）")
        self.assertEqual(
            pricing_exemption_problems(
                baseline=baseline, total=total,
                baseline_policy_version=baseline_policy_version,
                current_policy_version=_current_policy_version()),
            [],
            f"真表今天就被判紅 ⇒ 豁免輪設得太早，本輪自己付不出來；稽核痕跡最新輪＝"
            f"R{live_repin_round()}、豁免輪＝R{_PRICING_CHANGE_EXEMPT_ROUND}、"
            f"baseline={baseline}／total={total}／"
            f"baseline_policy_version={baseline_policy_version!r}")

    def test_the_next_round_cannot_reuse_the_exemption(self) -> None:
        """🔴 主牙：時鐘走過豁免輪之後，provenance 未指向目前這把尺的 baseline 必紅。

        R102 訂正：原本借磁碟真實狀態（尚未執行 `--update`）當「未重釘」的反面測資； round-label-ok
        R102 收尾四方核准並執行 `--repin-cap`＋`--update` 後， round-label-ok
        磁碟合法轉為「已重釘」，
        該巧合資料不復存在（這正是本鎖 §D-14 訂正段落自己記載的「出口永遠開著」被
        真的走過一次）。改為合成注入一個與 `current_policy_version` 不同的
        `baseline_policy_version`，繼續驗證同一段判準邏輯，不再依賴磁碟暫態——比照
        `test_repinning_the_baseline_is_a_real_exit`／`test_postponing_the_exemption_round_is_red`
        既有的合成注入模式，不改判準本體、不動 `_PRICING_CHANGE_EXEMPT_ROUND`。
        """
        _baseline, total, _bpv = _loc_pricing_facts()
        current_policy_version = _current_policy_version()
        stale_policy_version = f"{current_policy_version}-r102-synthetic-stale"
        self.assertTrue(
            any("[豁免過期]" in p for p in pricing_exemption_problems(
                latest_round=_PRICING_CHANGE_EXEMPT_ROUND + 1,
                baseline=total, total=total,
                baseline_policy_version=stale_policy_version,
                current_policy_version=current_policy_version)),
            "下一輪還帶著 provenance 未指向目前這把尺的 baseline 竟然放行 ⇒ "
            "豁免又退回口頭承諾")

    def test_repinning_the_baseline_is_a_real_exit(self) -> None:
        _baseline, total, _bpv = _loc_pricing_facts()
        current_policy_version = _current_policy_version()
        self.assertEqual(
            pricing_exemption_problems(
                latest_round=_PRICING_CHANGE_EXEMPT_ROUND + 1,
                baseline=total, total=total,
                baseline_policy_version=current_policy_version,
                current_policy_version=current_policy_version), [],
            "已把 baseline 的 provenance 重釘為目前這把尺卻仍判紅 ⇒ 這道鎖沒有出口，"
            "實務上一定被整個關掉（ARCH-02 判例）")

    def test_postponing_the_exemption_round_is_red(self) -> None:
        self.assertTrue(
            any("[豁免被延期]" in p for p in pricing_exemption_problems(
                latest_round=_PRICING_CHANGE_EXEMPT_ROUND + 1,
                baseline=1, total=1,
                exempt_round=_FROZEN_PRICING_CHANGE_EXEMPT_ROUND + 1)),
            "把豁免輪往後挪竟然放行 ⇒ 一行 diff 就能把單輪豁免磨成永久豁免")

    def test_an_unmeasurable_surface_fails_loud(self) -> None:
        self.assertTrue(
            any("[量不到]" in p for p in pricing_exemption_problems(
                latest_round=_PRICING_CHANGE_EXEMPT_ROUND + 1, baseline=0, total=0)),
            "量不到竟然當成通過 ⇒ 「讓它量不到」就是最省力的滿足方式（fail-open）")


class TestPhase2FiveRoundDeadlineIsMechanical(unittest.TestCase):
    """🔴 ADR-XPLAT-012 條文五 §6 的 5 輪時效——該 ADR 自陳「零具名常數與判準」的那一項。

    WHY：§6 逐字寫「不留無限期空轉的觀察機制——同本 repo `_REPIN_NET_CAP_DUE_ROUND`
    的到期義務設計哲學：義務要能被看見、要有到期時點」，而它自己當輪並沒有那個東西。
    本組鎖就是把那句話兌現成一個會紅的東西。
    """

    def test_the_live_log_is_green_and_the_due_round_is_derived(self) -> None:
        self.assertEqual(
            phase2_review_problems(), [],
            f"真表今天就被判紅——稽核痕跡最新輪＝R{live_repin_round()}、"
            f"到期輪＝R{_PHASE2_DUE_ROUND}、末列＝{_PHASE2_REVIEW_LOG[-1][:2]}")
        self.assertEqual(
            _PHASE2_DUE_ROUND, _PHASE2_REVIEW_LOG[-1][0] + _PHASE2_REVIEW_WINDOW,
            "到期輪必須由末列導出——寫死第二份就是「一份知識兩個家」，兩份必然漂移")

    def test_running_past_the_due_round_without_a_decision_is_red(self) -> None:
        self.assertTrue(
            any("[時效逾期]" in p for p in phase2_review_problems(
                latest_round=_PHASE2_DUE_ROUND + 1)),
            "走過到期輪而表上沒有新列竟然放行 ⇒ 5 輪時效又只是散文")

    def test_appending_a_decision_rearms_the_window(self) -> None:
        rearmed = (*_PHASE2_REVIEW_LOG,
                   (_PHASE2_DUE_ROUND + 1, "[提案]",
                    "合成語料：本輪提出 Phase 2 阻斷模式提案並送條文六的四方複審。"))
        self.assertEqual(
            phase2_review_problems(rearmed, latest_round=_PHASE2_DUE_ROUND + 1), [],
            "照 §6 追加一列決議竟然仍判紅 ⇒ 這道鎖沒有出口")

    def test_two_consecutive_deferrals_are_red(self) -> None:
        """🔴 本表真正的牙：靠貼 `[維持觀察]` 無限期買下去必須有代價。"""
        anchor = _PHASE2_REVIEW_LOG[-1][0]
        deferrals = (
            (anchor + 1, "[維持觀察]", "合成語料：本輪決定維持觀察模式，理由 A 夠長可過款(4)。"),
            (anchor + 2, "[維持觀察]", "合成語料：本輪又決定維持觀察模式，理由 B 夠長可過款(4)。"),
        )
        self.assertTrue(
            any("[連續空轉]" in p for p in phase2_review_problems(
                deferrals, latest_round=anchor + 2)),
            "連續兩次維持觀察竟然放行 ⇒ 「不留無限期空轉」沒有機械面")

    def test_the_two_cost_constants_only_shrink(self) -> None:
        self.assertTrue(
            any("[視窗被放寬]" in p for p in phase2_review_problems(
                latest_round=0, window=_FROZEN_PHASE2_REVIEW_WINDOW + 1)),
            "視窗被放寬竟然放行 ⇒ 條文五 §6 的「5 輪」變成一句可以自己改的話")
        self.assertTrue(
            any("[上限被放寬]" in p for p in phase2_review_problems(
                latest_round=0,
                max_deferrals=_FROZEN_PHASE2_MAX_CONSECUTIVE_DEFERRALS + 1)),
            "連續空轉上限被調高竟然放行 ⇒ 款(5) 的代價可以一行 diff 取消")

    def test_a_malformed_row_is_red(self) -> None:
        bad_outcome = ((99, "[隨便寫]", "合成語料：結局標記不在封閉表內，理由欄夠長。"),)
        self.assertTrue(
            any("[結局不在封閉表]" in p for p in phase2_review_problems(
                bad_outcome, latest_round=0)),
            "開放式結局字串竟然放行 ⇒ 款(5) 的連續計數無從判起")
        no_reason = ((99, "[維持觀察]", "延期"),)
        self.assertTrue(
            any("[無理由]" in p for p in phase2_review_problems(no_reason, latest_round=0)),
            "「延期」兩個字被當成理由 ⇒ 每一次重新武裝就沒有人負責解釋")
        self.assertTrue(
            any("[空表]" in p for p in phase2_review_problems((), latest_round=0)),
            "空表竟然放行 ⇒ 把整張表刪掉就是最省力的滿足方式（fail-open）")

    def test_a_non_increasing_round_is_red(self) -> None:
        flat = (*_PHASE2_REVIEW_LOG,
                (_PHASE2_REVIEW_LOG[-1][0], "[提案]",
                 "合成語料：輪號與末列相同，末列語意不成立，理由欄夠長可過款(4)。"))
        self.assertTrue(
            any("[輪號未遞增]" in p for p in phase2_review_problems(flat, latest_round=0)),
            "輪號不遞增竟然放行 ⇒ 「到期輪由末列導出」的語意不成立")


def guard_line_composition() -> dict[str, tuple[int, int]]:
    """ADR-XPLAT-013 Phase2 (c)（D-4：降級為觀測欄）：逐檔 `(def test* 函式數,
    assert 呼叫數)`——提案 §2.1 候選 c1／c2，**只印不擋、不接任何棘輪**。裁決理由
    （`AutoSDD_Adjudication_Record_R110.md` §1.4 D-4）：換算係數跨檔離散度達 6.52×，
    單一實測上限在半數母體上必然失準，先觀察一輪再由四方裁定是否轉阻斷。誠實劃界：
    `assert` 判準＝裸 `assert` ∪ `.assertXxx(` 呼叫，`subTest` 站點不併計（同提案）。
    """
    root = _REPO / _GUARD_DIR_REL
    out: dict[str, tuple[int, int]] = {}
    for p in sorted(root.glob(_GUARD_LINE_PATTERN)):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        test_count = sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name.startswith("test"))
        assert_count = sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.Assert)
            or (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr.startswith("assert")))
        out[p.name] = (test_count, assert_count)
    return out


def _print_guard_lines() -> None:
    """印出可直接貼回 `_FROZEN_GUARD_LINES` 的 dict 字面 ＋ 淨額 ＋ 稽核列草稿。

    三段輸出對應重釘要動的三個地方，照貼即可：淨額註解行、新的凍結表、
    `_GUARD_LINES_REPIN_LOG` 的新列（理由欄留空給人填——**刻意不代填**，
    ARCH-01 要的就是有人為那個淨額負責）。第四段是 (c) 觀測欄（D-4），純印出、
    不影響前三段的任何判準或數字。
    """
    current = guard_lines_in_worktree()
    old, new = sum(_FROZEN_GUARD_LINES.values()), sum(current.values())
    print(f"# 淨額 {old}→{new} ({new - old:+d})")
    # 🔴 R79：逐檔漂移**一律印**，即使淨額為 0。修前實況：乾淨 HEAD 上有三支檔與磁碟
    # 不符而淨額恰為 0，本工具首行印 `(+0)`、尾行印 `+0` 的稽核列草稿 ⇒ 照流程走的人
    # 只會看到「不需要重釘」。一個看不見自己盲區的重釘入口，會讓盲區永遠留在原地。
    drift = guard_line_drift(_FROZEN_GUARD_LINES, current)
    print(f"# 逐檔漂移 {len(drift)} 支"
          + ("（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）" if new == old else ""))
    for name, before, after in drift:
        print(f"#   DIFF {name} {before} -> {after} ({after - before:+d})")
    print("_FROZEN_GUARD_LINES: dict[str, int] = {")
    for name, n in sorted(current.items()):
        print(f'    "{name}": {n},')
    print("}")
    print(f'# _GUARD_LINES_REPIN_LOG 新列：("R<n>", {old}, {new}, {new - old:+d}, "<理由>"),')
    # append-only 的機械面（R79）：草稿一律以「追加那一列之後」的狀態算——
    # 前綴涵蓋含新列在內的全部列，指紋即該張表的指紋。追加後照貼這兩行即可。
    after = len(_GUARD_LINES_REPIN_LOG) + 1
    print(f"# _REPIN_LOG_FROZEN_PREFIX_LEN = {after}  # 追加新列後的總列數")
    print("#   （下面這個 sha 要在**貼上新列之後**重跑本指令才算得出來；"
          "本次印的是尚未追加時的值）")
    print(f'# _REPIN_LOG_HISTORY_SHA256 = "'
          f'{repin_log_history_digest(_GUARD_LINES_REPIN_LOG, after)}"')
    for label, items in (("逃逸", guard_surface_escapes()), ("涵蓋缺口", guard_baseline_gaps())):
        if items:
            print(f"# [{label}] {items}")
    comp = guard_line_composition()
    total_tests = sum(t for t, _a in comp.values())
    total_asserts = sum(a for _t, a in comp.values())
    print(f"# [觀測欄][D-4] test 函式數={total_tests} assert 呼叫數={total_asserts}"
          "（只印不擋，ADR-XPLAT-013 Phase2 (c) 降級觀測；不接任何棘輪）")


class TestRegressionLaneSplit(unittest.TestCase):
    """ADR-XPLAT-013 Phase2 (b)（D-1＝S-2）：回歸鎖軌／功能軌分軌計價（DEF-200-211）。

    驗收判準對齊 `ADR-XPLAT-013_Phase2_Proposal_R108.md` §5.1／§5.2；裁決存證見
    `AutoSDD_Adjudication_Record_R110.md` §1.4 D-1/D-6。落地輪＝R116； round-label-ok
    `_REGRESSION_LANE_SINCE = 117`（下一輪起才真的生效，落地輪自己不追溯）。
    """

    # ── 真實資料現查（生產閘門）──────────────────────────────────────────
    def test_the_real_tables_pass_the_split_guard(self) -> None:
        problems = lane_split_problems()
        self.assertEqual(problems, [], "分軌申報守衛：\n  " + "\n  ".join(problems))

    # ── §5.1 五款逐款突變驗紅 ────────────────────────────────────────────
    def test_clause_1_empty_table_past_since_is_red(self) -> None:
        main = (("R117", 100, 150, 50, "[非淨減法輪] 逐檔清單＝x.md 全額功能軌工作"),)
        problems = lane_split_problems(main, (), since=117, latest_round=117)
        self.assertTrue(any("[空表]" in p for p in problems), problems)

    def test_clause_1_green_before_since(self) -> None:
        main = (("R116", 100, 150, 50, "[非淨減法輪] 逐檔清單＝x.md"),)
        problems = lane_split_problems(main, (), since=117, latest_round=116)
        self.assertFalse([p for p in problems if "[空表]" in p], problems)

    def test_clause_2_unreported_lane_is_red(self) -> None:
        """🔴 `lane` 帶一列占位（R118 round-label-ok）避撞款1——本款測「表非空但這輪沒申報」。"""
        main = (
            ("R117", 100, 150, 50, "[非淨減法輪] 逐檔清單＝x.md"),
            ("R118", 150, 200, 20, "[非淨減法輪][全額功能軌] 逐檔清單＝x.md"),
        )
        lane = (("R118", 20, "占位列：R118 全額回歸鎖軌，僅用來讓表非空"),)
        problems = lane_split_problems(main, lane, since=117, latest_round=118)
        self.assertTrue(any("[軌別未申報]" in p for p in problems), problems)

    def test_clause_2_green_with_full_functional_marker(self) -> None:
        main = (
            ("R117", 100, 150, 50, "[非淨減法輪][全額功能軌] 逐檔清單＝x.md"),
            ("R118", 150, 200, 20, "[非淨減法輪] 逐檔清單＝x.md"),
        )
        lane = (("R118", 20, "占位列：R118 全額回歸鎖軌，僅用來讓表非空"),)
        problems = lane_split_problems(main, lane, since=117, latest_round=118)
        self.assertFalse([p for p in problems if "[軌別未申報]" in p], problems)

    def test_clause_2_green_with_lane_entry(self) -> None:
        main = (("R117", 100, 150, 50, "[非淨減法輪] 逐檔清單＝x.md"),)
        lane = (("R117", 30, "逐檔清單＝x.md 回歸鎖軌部分"),)
        problems = lane_split_problems(main, lane, since=117, latest_round=117)
        self.assertFalse([p for p in problems if "[軌別未申報]" in p], problems)

    def test_clause_3_lane_exceeding_parent_is_red(self) -> None:
        main = (("R117", 100, 150, 50, "[非淨減法輪] 逐檔清單＝x.md"),)
        lane = (("R117", 60, "逐檔清單＝x.md（刻意大於母項，驗證款3）"),)
        problems = lane_split_problems(main, lane, since=117, latest_round=117)
        self.assertTrue(any("[子項大於母項]" in p for p in problems), problems)

    def test_clause_3_green_when_lane_equals_parent(self) -> None:
        main = (("R117", 100, 150, 50, "[非淨減法輪] 逐檔清單＝x.md"),)
        lane = (("R117", 50, "逐檔清單＝x.md 全額回歸鎖軌"),)
        problems = lane_split_problems(main, lane, since=117, latest_round=117)
        self.assertFalse([p for p in problems if "[子項大於母項]" in p], problems)

    def test_clause_3_negative_main_round_skips_the_subset_bound(self) -> None:
        """SD-1（R117 合成 round-label-ok）：母項負⇒款3綠（誠實毛增量）；套利面款4承接。"""
        main = (("R117", 500, 450, -50, "[非淨減法輪] 淨減法輪誠實申報，逐檔清單＝x.md"),)
        ok = lane_split_problems(main, (("R117", 30, "毛增量申報"),),
                                 since=117, latest_round=117)
        self.assertFalse([p for p in ok if "[子項大於母項]" in p], ok)
        hot = lane_split_problems(main, (("R117", 999, "母項為負而子項爆表"),),
                                  since=117, cap=309, latest_round=117)
        self.assertFalse([p for p in hot if "[子項大於母項]" in p], hot)
        self.assertTrue(any("[回歸鎖軌超上限]" in p for p in hot), hot)

    def test_clause_4_lane_over_cap_is_red(self) -> None:
        main = (("R117", 100, 500, 400, "[非淨減法輪] 逐檔清單＝x.md"),)
        lane = (("R117", 400, "逐檔清單＝x.md（刻意超過上限，驗證款4）"),)
        problems = lane_split_problems(main, lane, since=117, cap=309, latest_round=117)
        self.assertTrue(any("[回歸鎖軌超上限]" in p for p in problems), problems)

    def test_clause_4_green_when_pinned_to_the_cap(self) -> None:
        """貼齊上限即合法（同 R99/R101/R113 判例：兌現值可以恰好貼齊到期目標）。round-label-ok"""
        main = (("R117", 100, 409, 309, "[非淨減法輪] 逐檔清單＝x.md"),)
        lane = (("R117", 309, "逐檔清單＝x.md 全額回歸鎖軌"),)
        problems = lane_split_problems(main, lane, since=117, cap=309, latest_round=117)
        self.assertFalse([p for p in problems if "[回歸鎖軌超上限]" in p], problems)

    def test_clause_4_approved_overage_is_the_named_escape(self) -> None:
        main = (("R117", 100, 500, 400, "[非淨減法輪] 逐檔清單＝x.md"),)
        lane = (("R117", 400, "逐檔清單＝x.md"),)
        overage = {"R117": (400, "合成注入測試：核准 R117 回歸鎖軌一次性例外")}
        problems = lane_split_problems(main, lane, since=117, cap=309,
                                        approved_overage=overage, latest_round=117)
        self.assertFalse([p for p in problems if "[回歸鎖軌超上限]" in p], problems)

    def test_clause_5_since_decreased_is_red(self) -> None:
        problems = lane_split_problems((), (), since=116, frozen_since=117, latest_round=116)
        self.assertTrue(any("[減免軌被追溯]" in p for p in problems), problems)

    def test_clause_5_since_increased_or_same_is_green(self) -> None:
        problems = lane_split_problems((), (), since=118, frozen_since=117, latest_round=116)
        self.assertFalse([p for p in problems if "[減免軌被追溯]" in p], problems)
        problems = lane_split_problems((), (), since=117, frozen_since=117, latest_round=116)
        self.assertFalse([p for p in problems if "[減免軌被追溯]" in p], problems)

    def test_clause_5_cap_increased_is_red(self) -> None:
        problems = lane_split_problems((), (), cap=400, frozen_cap=309, latest_round=116)
        self.assertTrue(any("[上限被放寬]" in p for p in problems), problems)

    def test_clause_5_cap_decreased_or_same_is_green(self) -> None:
        problems = lane_split_problems((), (), cap=300, frozen_cap=309, latest_round=116)
        self.assertFalse([p for p in problems if "[上限被放寬]" in p], problems)
        problems = lane_split_problems((), (), cap=309, frozen_cap=309, latest_round=116)
        self.assertFalse([p for p in problems if "[上限被放寬]" in p], problems)

    # ── 延伸款：[生效前宣告]（§1.6.3 第 3 題的申報面） ────────────────────
    def test_clause_6_pre_since_lane_declaration_is_red(self) -> None:
        main = (("R116", 100, 350, 250, "[非淨減法輪] 落地輪本身逐檔清單＝x.md"),)
        lane = (("R116", 250, "刻意把落地輪自己的淨額全記進回歸鎖軌，驗證款6"),)
        problems = lane_split_problems(main, lane, since=117, latest_round=116)
        self.assertTrue(any("[生效前宣告]" in p for p in problems), problems)

    def test_clause_6_green_at_or_after_since(self) -> None:
        main = (("R117", 100, 350, 250, "[非淨減法輪] 逐檔清單＝x.md"),)
        lane = (("R117", 250, "逐檔清單＝x.md 全額回歸鎖軌"),)
        problems = lane_split_problems(main, lane, since=117, latest_round=117)
        self.assertFalse([p for p in problems if "[生效前宣告]" in p], problems)

    # ── §5.2 分軌不放寬既有門檻的機械自證 ─────────────────────────────────
    def test_the_split_does_not_widen_the_functional_lane(self) -> None:
        """空的回歸鎖軌表 ⇒ `repin_growth_problems()` 的結果必須與分軌前逐字相同。"""
        before = repin_growth_problems(_GUARD_LINES_REPIN_LOG)
        after = repin_growth_problems(_GUARD_LINES_REPIN_LOG, regression_lane=())
        self.assertEqual(before, after,
                          "傳空的回歸鎖軌表卻改變了判定結果 ⇒ 分軌退化為現制這件事沒有做到")
        after_none = repin_growth_problems(_GUARD_LINES_REPIN_LOG, regression_lane=None)
        self.assertEqual(before, after_none)

    def test_the_split_cannot_be_used_by_its_own_landing_round(self) -> None:
        """落地輪（R116 round-label-ok）不得把淨額全記回歸鎖軌豁免自己（§1.6.3 第 3 題）。

        注入面：合成一張主表，其唯一一輪就是落地輪字面 116，淨額 +400（遠超上限）；
        回歸鎖軌表把這 +400 全額申報。用 `latest_round=116` 呼叫
        （**不從 `_REGRESSION_LANE_SINCE` 算出**，避免 R75 頭號教訓：比較對象隨被判的
        常數一起滑走）：必須紅（因為 116 < SINCE=117，減法不生效）。第二臂
        `latest_round=117`（SINCE 本身）：同一張表必須綠（減法生效，證明紅不是無條件的）。
        """
        main = (("R116", 100, 500, 400, "[非淨減法輪] 落地輪本體：分軌判準與平行表本身"),)
        lane = (("R116", 400, "刻意把落地輪全部淨額謊報成回歸鎖軌，驗證自我豁免防線"),)
        red = repin_growth_problems(main, since=100, net_cap=300,
                                     regression_lane=lane, regression_lane_since=117)
        self.assertTrue(any("[超出每輪上限]" in p for p in red), red)
        green = repin_growth_problems(main, since=100, net_cap=300,
                                       regression_lane=lane, regression_lane_since=116)
        self.assertFalse([p for p in green if "[超出每輪上限]" in p], green)

    def test_the_regression_lane_cap_is_taken_from_measurement_not_invention(self) -> None:
        """cap 常數必須等於一個可由 `_GUARD_LINES_REPIN_LOG` 現查導出的實測值（零加減推算）。"""
        basis_round, basis_delta = _regression_lane_cap_basis()
        self.assertEqual(basis_delta, _REGRESSION_LANE_ROUND_CAP)
        matches = [r for r in _GUARD_LINES_REPIN_LOG
                   if r[0] == basis_round and r[3] == basis_delta]
        self.assertTrue(matches, f"{basis_round} 那一列（淨額 {basis_delta}）"
                        "已不在 _GUARD_LINES_REPIN_LOG 裡 ⇒ cap 的取值基準憑空浮動")

    # ── 對抗性探針（逐形態，不只量一種——ADR §1.5 教訓）─────────────────────
    def test_adversarial_probe_functional_code_written_as_test_method_is_not_a_free_pass(
        self,
    ) -> None:
        """探針①：把一輪的功能成長申報成回歸鎖軌（純靠嘴說「這是回歸測試」）不能豁免上限——
        `lane_split_problems()` 的款「回歸鎖軌超上限」只認淨額與名冊，不採信理由欄的自稱。
        """
        main = (("R117", 100, 900, 800,
                 "[非淨減法輪] 全部宣稱為回歸測試，實為新判準面（探針①語料）"),)
        lane = (("R117", 800, "全部宣稱為回歸測試（探針①：口頭宣稱不是名冊核准）"),)
        problems = lane_split_problems(main, lane, since=117, cap=309, latest_round=117)
        self.assertTrue(any("[回歸鎖軌超上限]" in p for p in problems), problems)

    def test_adversarial_probe_round_and_lane_split_combo_is_caught(self) -> None:
        """探針④：拆輪次 × 拆軌別組合套利——把功能成長全塞進回歸鎖軌、企圖用「回歸鎖軌
        不受連續上升鎖管」躲開款(11)。本探針宣告的回歸鎖軌淨額同時大於同輪主表淨額
        （款3 該擋）且超過上限（款4 該擋），驗證兩款同時開火時不會互相掩蓋——不能靠
        觸發其中一款掩護另一款失效。
        """
        main = (("R117", 100, 900, 800, "[非淨減法輪] 逐檔清單＝x.md"),)
        lane = (("R117", 850, "刻意宣告超過母項，企圖以回歸鎖軌吃下全部再豁免自己"),)
        problems = lane_split_problems(main, lane, since=117, cap=309, latest_round=117)
        self.assertTrue(any("[子項大於母項]" in p for p in problems), problems)
        self.assertTrue(any("[回歸鎖軌超上限]" in p for p in problems), problems)

    def test_adversarial_probe_exec_docstring_arbitrage_is_a_known_gap(self) -> None:
        """探針②（誠實劃界，非通過項）：`exec(__doc__)` 把功能碼藏進敘事載體、執行期才
        取出——`lane_split_problems()`／候選 2 的 C2~C4 掃的是 AST 節點與字面，看不到
        字串內容。此格明文記為已知缺口而非通過，承接＝ADR-XPLAT-013 Phase2 D-3
        （ruff S102，DEF-200-209／DEF-200-217 E2）——本測試只確認「本判準確實對此
        沒有鑑別力」這件事被誠實記著，不假裝已經擋住。
        """
        main = (
            ("R117", 100, 150, 50,
             '[非淨減法輪][全額功能軌] exec(__doc__) 型套利語料（探針②）'),
            ("R118", 150, 170, 20, "[非淨減法輪] 逐檔清單＝x.md"),
        )
        # lane 帶一列占位（避免撞款1）；R117（round-label-ok）主表已標「全額功能
        # 軌」，本判準結構上看不出這行理由背後藏著 exec(__doc__)——這正是本探針要誠實
        # 記錄的缺口：判準綠燈，缺口仍在。
        lane = (("R118", 20, "占位列：R118 全額回歸鎖軌，僅用來讓表非空"),)
        problems = lane_split_problems(main, lane, since=117, latest_round=118)
        self.assertEqual(problems, [],
                          "本判準對 exec(__doc__) 套利沒有鑑別力是已知且誠實登記的缺口，"
                          "若此斷言開始失敗代表判準行為已變化，請回頭核對本測試是否仍對應"
                          "誠實劃界的敘述")


class TestObservationColumnsAreDisplayOnly(unittest.TestCase):
    """ADR-XPLAT-013 Phase2 (c)（D-4）：觀測欄只印不擋（`guard_line_composition()`）。"""

    def test_composition_reports_plausible_numbers_for_this_file(self) -> None:
        comp = guard_line_composition()
        self.assertIn(_HERE.name, comp)
        test_count, assert_count = comp[_HERE.name]
        self.assertGreater(test_count, 0, "本檔明明有大量 test 方法，卻算出 0")
        self.assertGreater(assert_count, 0, "本檔明明有大量斷言，卻算出 0")

    def test_print_guard_lines_includes_the_observation_line(self) -> None:
        """(c) 的輸出必須真的印得出來（同 ARCH-02 的既有紀律：宣稱的東西要真的跑得動）。"""
        import io  # noqa: PLC0415
        from contextlib import redirect_stdout  # noqa: PLC0415

        buf = io.StringIO()
        with redirect_stdout(buf):
            _print_guard_lines()
        self.assertIn("[觀測欄][D-4]", buf.getvalue())

    def test_the_observation_line_does_not_gate_anything(self) -> None:
        """反 vacuity：`guard_line_composition()` 只能被 `_print_guard_lines()` 消費——
        任何一支 `*_problems()` 判準函式的原始碼裡都不得出現這個名字，否則「只印不擋」
        就只是文件宣稱，不是結構事實（D-4 裁決：不換分母、不全量落地，只加觀測欄）。
        """
        text = _HERE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        offenders = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.endswith("_problems")
            and "guard_line_composition" in (ast.get_source_segment(text, node) or "")
        ]
        self.assertEqual(offenders, [],
                          f"這些判準函式引用了觀測欄：{offenders} ⇒ (c) 不再是「只印不擋」")


class TestRootToolsOldScaleDebtDueRound(unittest.TestCase):
    """ADR-XPLAT-013 §9.3／U9（D-5）：技術債到期輪的機械保底（不是「已真拆」的證明）。"""

    def test_the_real_state_is_not_yet_due(self) -> None:
        """生產閘門：R116 現查未清償，但到期輪 R121 尚未到，故現在必須是綠的。round-label-ok"""
        problems = root_tools_debt_due_problems()
        self.assertEqual(problems, [], "\n  ".join(problems))

    def test_unresolved_past_due_is_red(self) -> None:
        problems = root_tools_debt_due_problems(resolved=False, due_round=121,
                                                 latest_round=121)
        self.assertTrue(any("[技術債逾期]" in p for p in problems), problems)

    def test_resolved_past_due_is_green(self) -> None:
        problems = root_tools_debt_due_problems(resolved=True, due_round=121,
                                                 latest_round=121)
        self.assertEqual(problems, [])

    def test_unresolved_before_due_is_green(self) -> None:
        problems = root_tools_debt_due_problems(resolved=False, due_round=121,
                                                 latest_round=116)
        self.assertEqual(problems, [])

    def test_the_due_round_cannot_be_silently_pushed_out(self) -> None:
        """A-2 後設鎖紅綠自證：到期輪推到 9999 必紅；真實模組常數必須在界內。"""
        hits = root_tools_debt_due_problems(due_round=9999, latest_round=116)
        self.assertTrue(any("[到期輪超界]" in h for h in hits), hits)
        real = [h for h in root_tools_debt_due_problems() if "[到期輪超界]" in h]
        self.assertEqual(real, [], real)
        self.assertLessEqual(_ROOT_TOOLS_DEBT_DUE_MAX_LOOKAHEAD,
                             _FROZEN_ROOT_TOOLS_DEBT_DUE_MAX_LOOKAHEAD)


class TestRepinCommandIsReal(unittest.TestCase):
    """R78 ARCH-02：棘輪紅燈訊息裡具名的重釘指令必須真的跑得動。

    WHY 這一類存在：一道「紅了卻沒有出路」的棘輪，實務上等同一道會被關掉的棘輪。
    R77 的紅燈訊息教人跑一個不存在的旗標，操作者拿到 rc=2 之後唯一的路是逐列手改整張
    凍結表——而那樣改的人不會順手算淨額（ARCH-01 的成因）。
    """

    def test_every_flag_this_file_tells_you_to_run_is_dispatched(self) -> None:
        """雙向綁定：訊息教的旗標必須被分派，分派的旗標必須有人教。"""
        text = _HERE.read_text(encoding="utf-8")
        problems = self_invocation_flag_problems(text, _DISPATCHED_FLAGS)
        self.assertEqual(problems, [], "本檔的自呼叫指令與 __main__ 不符：\n  "
                         + "\n  ".join(problems))

    def test_the_flag_scanner_is_not_vacuous(self) -> None:
        """自錨：抽取器至少要在本檔真的抓到一個自呼叫旗標，否則上一支對任何內容恆綠。"""
        found = set(_SELF_INVOCATION_RE.findall(_HERE.read_text(encoding="utf-8")))
        self.assertTrue(found, "本檔找不到任何「指名自己 ＋ 旗標」的行 ⇒ 抽取器已空轉")
        self.assertTrue(found & _DISPATCHED_FLAGS)

    def test_a_dead_command_in_a_red_message_is_red(self) -> None:
        """注入＝修前實況：訊息教一個沒被分派的旗標 ⇒ `[死指令]` 必紅。

        🔴 合成字串刻意**接起來**而不是寫成一個字面：本判準的掃描面就是本檔全文，
        寫成完整字面會讓上面那支活體測試在本檔裡抓到這個假旗標而紅（自我違規）。
        """
        text = "重釘：python tools/tests/" + _HERE.name + " --no-such-flag"
        problems = self_invocation_flag_problems(text, _DISPATCHED_FLAGS)
        self.assertTrue(any("[死指令]" in p for p in problems), problems)
        self.assertTrue(any("--no-such-flag" in p for p in problems), problems)

    def test_an_undocumented_dispatched_flag_is_red(self) -> None:
        """注入②：分派了卻沒人教 ⇒ `[孤兒旗標]` 必紅（同一個病的另一面）。"""
        problems = self_invocation_flag_problems("", {"--print-guard-lines"})
        self.assertTrue(any("[孤兒旗標]" in p for p in problems), problems)

    def test_another_tools_flag_is_not_this_locks_business(self) -> None:
        """對照組：別的工具的旗標不歸本判準管（誤報的鎖最後一定被整道關掉）。"""
        problems = self_invocation_flag_problems(
            "現查：python tools/check_script_parity.py --print-collapse", _DISPATCHED_FLAGS)
        self.assertFalse(
            [p for p in problems if "[死指令]" in p],
            f"別的工具的旗標被誤判成本檔的死指令：{problems}")

    def test_the_repin_command_emits_a_pastable_table(self) -> None:
        """端到端真跑：rc 必須是 0，且輸出的 dict 字面必須 `ast.literal_eval` 得回來。

        🔴 不用 mock：ARCH-02 的病灶就是「訊息宣稱的東西沒人真的跑過」，用 mock 驗證
        等於再犯一次。子行程刻意帶 `PYTHONUTF8=1`——本檔的消費者含 console codepage 950
        的 Windows 排程環境，那裡預設編碼會把輸出讀成亂碼（本 repo 已為此付過學費）。
        """
        import os  # noqa: PLC0415
        import subprocess  # noqa: PLC0415

        env = {**os.environ, "PYTHONUTF8": "1"}
        proc = subprocess.run(
            [sys.executable, str(_HERE), "--print-guard-lines"],
            capture_output=True, text=True, encoding="utf-8", env=env, check=False)
        self.assertEqual(
            proc.returncode, 0,
            f"重釘指令實跑失敗（rc={proc.returncode}）：{proc.stderr[-800:]}")
        body = proc.stdout
        self.assertRegex(body.splitlines()[0], r"^# 淨額 \d+→\d+ \([+-]\d+\)$")
        self.assertIn("_GUARD_LINES_REPIN_LOG 新列：", body)
        start = body.index("{")
        end = body.index("\n}") + 2
        table = ast.literal_eval(body[start:end])
        self.assertEqual(
            table, guard_lines_in_worktree(),
            "印出來的表與現況不符 ⇒ 貼回去也還是錯的")


#: 🔴 R82／Q2-06：根 CLAUDE.md 不得**逐字複寫** LOC 分級表。這個形態在本 repo 已判過兩次
#: （R77 的 ruff 規則集複本、R73 的 `Find-GitBash` 路徑常數），兩次的成因都一樣：同一份知識
#: 住兩個家，而只有一個家會被人改。判準刻意只認「tier 名 ＋ 比較號 ＋ 數字」這個複寫形態，
#: 不認 tier 名本身（`infra/adapters/` 這種目錄名滿篇都是，判它就是整片假紅）。
_LOC_TIER_COPY_RE = re.compile(
    r"(?:data|plugin_entry|strategy|adapter|contract|service|絕對紅線)\s*(?:≤|<=)\s*\d+")
_LOC_BUDGET_SSOT_REL = "AutoClaude/tools/check_loc_budget.py"


def _loc_tier_ssot() -> tuple[dict, int]:
    """自 SSOT 檔讀 `LOC_TIERS`／`ABSOLUTE_LIMIT`（AST，不執行那支檔）。"""
    tree = ast.parse((_REPO / _LOC_BUDGET_SSOT_REL).read_text(encoding="utf-8"))
    tiers, limit = {}, 0
    for node in tree.body:
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target.id
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
                node.targets[0], ast.Name):
            target = node.targets[0].id
        if target == "LOC_TIERS" and node.value is not None:
            tiers = ast.literal_eval(node.value)
        elif target == "ABSOLUTE_LIMIT" and node.value is not None:
            limit = ast.literal_eval(node.value)
    return tiers, limit


class TestLocTierTableHasOnlyOneHome(unittest.TestCase):
    """LOC 分級表在根 CLAUDE.md 只准是**指標**，不准是複本（R82／Q2-06）。"""

    def test_the_ssot_really_defines_the_table(self) -> None:
        """反 vacuity：判準掃的東西必須真的存在，否則它只是一條恆綠的正則。"""
        tiers, limit = _loc_tier_ssot()
        self.assertGreaterEqual(len(tiers), 5, "SSOT 讀不到分級表 ⇒ 本鎖失去比較對象")
        self.assertGreater(limit, 0, "SSOT 讀不到絕對紅線")
        for name, spec in tiers.items():
            with self.subTest(tier=name):
                self.assertIsInstance(spec.get("budget"), int)

    def test_the_root_claude_md_points_at_the_ssot_instead_of_restating_it(self) -> None:
        text = (_REPO / "CLAUDE.md").read_text(encoding="utf-8")
        hits = _LOC_TIER_COPY_RE.findall(text)
        self.assertEqual(hits, [], "根 CLAUDE.md 又把 LOC 分級表逐字複寫了一份"
                                   f"（命中 {hits}）⇒ 同一份知識兩個家，"
                                   f"唯一真相源是 {_LOC_BUDGET_SSOT_REL}")
        # 光是「沒有複本」還不夠：整段被刪掉時上面那條也會綠。指標必須真的在。
        self.assertIn(_LOC_BUDGET_SSOT_REL, text,
                      "複本刪了、指標也沒留 ⇒ 讀者連去哪裡查都不知道")


#: 🔴 R82／Q2-04：重釘稽核列**是索引不是報告**。缺陷本體：這張 log 住在它自己在量的那支
#: 檔裡，而每一輪至少要 append 一列 ⇒ 量測器每輪把自己量的數字推高（現查：
#: `_GUARD_LINES_REPIN_LOG` 的 AST 起訖行）。**本鎖不改寫任何既有列**——那張表由
#: `_REPIN_LOG_FROZEN_PREFIX_LEN` 的
#: append-only 指紋守著，改寫歷史正是它存在的理由；本鎖只約束**新列**，讓成長從這裡停住。
#: 上限沿用本 repo 既有的同型判例（缺陷帳本「列是索引不是報告」＝700 bytes，詳情進具名
#: 證據檔），不另發明一個數字；逐檔清單與必要性辯護的家仍是 `CrossPlatform_R*_*.md`。
_REPIN_REASON_CAP_SINCE = 82
_REPIN_REASON_MAX_CHARS = 700


class TestRepinReasonStaysAnIndexNotAReport(unittest.TestCase):
    """新的重釘列不得再夾帶整段敘事（R82／Q2-04 的**可做的那一半**）。"""

    def _new_rows(self) -> list[tuple]:
        return [r for r in _GUARD_LINES_REPIN_LOG
                if int(str(r[0]).lstrip("Rr") or 0) >= _REPIN_REASON_CAP_SINCE]

    def test_new_rows_are_bounded_and_point_at_the_findings_doc(self) -> None:
        for row in self._new_rows():
            with self.subTest(round=row[0]):
                reason = str(row[4])
                self.assertLessEqual(
                    len(reason), _REPIN_REASON_MAX_CHARS,
                    f"R{row[0]} 的重釘理由 {len(reason)} 字元 > "
                    f"{_REPIN_REASON_MAX_CHARS} ⇒ 量測器又在推高自己量的數字；"
                    "逐檔清單與必要性辯護請落在 CrossPlatform_R*_Scan_Findings.md")
                self.assertRegex(reason, _PER_FILE_LIST_RE,
                                 "縮短了但沒有指向逐檔清單的家 ⇒ 資訊真的掉了，"
                                 "那不是減法是刪證據")

    def test_the_cap_only_binds_forward_and_grandfathers_the_frozen_prefix(self) -> None:
        """反 vacuity 的另一半：舊列**刻意**不受本鎖約束，且那不是漏看。

        既有列全部落在 append-only 指紋的凍結前綴內，改寫其中任何一列會先撞那道更根本的
        鎖。本測試把「舊列超標是已知且被接受的」釘成事實——否則下一個人會以為本鎖恆綠。
        """
        old = [r for r in _GUARD_LINES_REPIN_LOG
               if int(str(r[0]).lstrip("Rr") or 0) < _REPIN_REASON_CAP_SINCE]
        self.assertTrue(old, "凍結前綴空了 ⇒ 有人改寫了歷史")
        self.assertTrue(any(len(str(r[4])) > _REPIN_REASON_MAX_CHARS for r in old),
                        "舊列全都在上限之內 ⇒ 本鎖的立案前提（敘事把量測器撐大）已不成立，"
                        "該重新談這條規則而不是留著一條沒有分母的鎖")
        self.assertLessEqual(_REPIN_REASON_CAP_SINCE, 82,
                             "生效輪次被往後推 ⇒ 等於把已經該受約束的列放出去")


class TestGuardBucketRatchet(unittest.TestCase):
    """**分桶棘輪**——總量棘輪之外**額外加嚴**的第二道判準（`DEF-200-103`）。

    立案：上一輪 Architect 的架構判讀是「單一總量棘輪讓最便宜的那一桶（守散文）永遠贏」，
    因為「加一支守散文的鎖」與「加一支守生產碼的鎖」在單一總量下付**一樣**的代價。
    本族讓兩者付不同的代價：守真程式碼那幾桶可以長，守散文／守自己那兩桶只准往下。

    🔴 **本族不取代、不放寬總量棘輪**（掌舵者裁決）：`TestGuardLayerRatchet` 那一族與
    淨額 ≤ 0 的到期義務一字未動 ⇒ 通過條件是兩道**同時**成立，淨效果只能更嚴。

    🔴 判準／常數／桶定義**都不住本檔**，住 `tools/lib/guard_bucket_policy.py`。兩個理由：
    ① probe 與棘輪必須讀同一份桶定義，否則「印的比例」與「判的比例」是兩個數；
    ② `tools/tests/*.py` 就是被量的那個面，判準寫在這裡會讓本機制每長一行就把自己要管的
       分子做大一行。本檔只留消費端（同 `test_schedule_capability_parity._SCAN_FLOOR`
       取消第二個家的既有體例）。
    """

    @staticmethod
    def _policy():
        sys.path.insert(0, str(_REPO / "tools" / "lib"))
        import guard_bucket_policy
        return guard_bucket_policy

    def test_shrink_only_buckets_did_not_grow(self) -> None:
        """守散文／守自己兩桶只准往下（主牙）。"""
        gbp = self._policy()
        problems = gbp.bucket_ratchet_problems(gbp.measure_shrink_only(_REPO))
        self.assertEqual(problems, [], "分桶棘輪：\n" + "\n".join(problems))

    def test_the_ratchet_actually_bites_when_a_prose_bucket_grows(self) -> None:
        """注入自證：合成一筆散文桶成長必須轉紅（否則本鎖是恆真的裝飾）。"""
        gbp = self._policy()
        base = dict(gbp._FROZEN_SHRINK_ONLY_BUCKET_LINES)
        grown = {b: n + 1 for b, n in base.items()}
        self.assertTrue(gbp.bucket_ratchet_problems(grown, frozen=base),
                        "散文桶 +1 竟未轉紅 ⇒ 判準沒有鑑別力")
        self.assertEqual(gbp.bucket_ratchet_problems(base, frozen=base), [],
                         "實測等於基準竟轉紅 ⇒ 判準會製造假紅")
        # 缺席那一向：拿掉一列不得靜默通過（少一列＝那一桶不受判準）。
        short = {b: n for b, n in base.items() if b != gbp.SHRINK_ONLY_BUCKETS[0]}
        self.assertTrue(gbp.bucket_ratchet_problems(short, frozen=short),
                        "凍結表少一個 shrink-only 桶竟通過 ⇒ 桶可被靜默拿掉")

    def test_the_classifier_discriminates_prose_growth_from_code_growth(self) -> None:
        """端到端注入 ＋ **對照組**：真的長一支「只守散文」的鎖必須紅，「只守生產碼」必須綠。

        WHY 上一向不夠：那一向注入的是**字典**，只證明比較運算會動；本向注入的是**檔案**，
        證明分類器真的把兩種成長分開——沒有對照組的注入自證只能說明「會紅」，不能說明
        「不該紅的時候不紅」，而後者才是這道鎖能不能活過一輪的條件。
        """
        import tempfile
        gbp = self._policy()
        stub = ('class T:\n    """守 {ref} 的合成鎖。"""\n'
                + "".join(f"    # {{ref}} 第 {i} 條\n" for i in range(40)))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tools" / "tests").mkdir(parents=True)
            base = gbp.measure_shrink_only(root)
            for ref, expect_red in (("docs/06_quality/x.md", True),
                                    ("AutoClaude/autoclaude/core/kernel.py", False)):
                target = root / "tools" / "tests" / "test_injected.py"
                target.write_text(stub.format(ref=ref), encoding="utf-8")
                got = gbp.bucket_ratchet_problems(gbp.measure_shrink_only(root), frozen=base)
                self.assertEqual(bool(got), expect_red,
                                 f"注入只守 `{ref}` 的鎖：預期{'紅' if expect_red else '綠'}"
                                 f"，實得 {got or '綠'} ⇒ 分類器沒有鑑別力")
                target.unlink()

    def test_growth_allowed_buckets_are_the_code_guarding_ones(self) -> None:
        """方向鎖：允許成長的桶必須是**守真程式碼**那幾桶，且與 shrink-only 集合互斥。

        沒有這一向，把 `prose` 搬進允許成長那一組就能讓紅變綠，而那與「為了讓紅變綠而改成
        不比較」只有一線之隔（上一輪四方複審已對同型動作下過判決）。
        """
        gbp = self._policy()
        self.assertEqual(gbp.GROWTH_ALLOWED_BUCKETS,
                         frozenset({"production", "root_infra", "sdd"}))
        self.assertFalse(gbp.GROWTH_ALLOWED_BUCKETS & set(gbp.SHRINK_ONLY_BUCKETS))
        self.assertIn("prose", gbp.SHRINK_ONLY_BUCKETS)
        self.assertIn("guard_self", gbp.SHRINK_ONLY_BUCKETS)
        # 後設向：登記了卻抓不到的樹前綴＝該族被靜默排除在分母外（本輪實測發生過）。
        self.assertEqual(gbp.dead_tree_prefixes(), [],
                         "BUCKET_TREES 有樹前綴永遠抓不到 ⇒ 那一族不在任何桶的分母裡，"
                         "而掃描器照跑照回數字，失明是靜默的")

    def test_the_probe_default_grain_equals_the_ratchet_basis(self) -> None:
        """probe 印的粒度必須等於棘輪判的粒度——否則兩邊講的是兩件事。

        WHY 這一向非有不可：**檔級**的 `exclusive` 歸屬對 `prose` 桶實測回零——本層的鎖檔
        絕大多數同時參照根層基礎設施、護欄層自己與散文三者，所以「只參照一棵樹」在檔級
        幾乎不成立（比例一律現查 `python tools/probe/guard_layer_bucket_census.py --grain file`
        的 `exclusive` 欄）。⇒ 若 probe 預設檔級而棘輪吃檔級，shrink-only 判準會是恆真的
        裝飾。粒度是這道鎖有沒有牙的分水嶺，不是顯示選項。
        """
        gbp = self._policy()
        src = (_REPO / "tools" / "probe" / "guard_layer_bucket_census.py").read_text(
            encoding="utf-8")
        grain, estimator = gbp.GUARD_BUCKET_RATCHET_BASIS
        self.assertIn(f'choices=("chunk", "file"), default="{grain}"', src,
                      f"probe 的 --grain 預設值必須是 {grain}（棘輪判的粒度）")
        self.assertIn(estimator, ("exclusive", "firstmatch", "dominant", "any"))


if __name__ == "__main__":  # pragma: no cover
    # R78：`--print-guard-lines` 的輸出含中文（淨額註解行與稽核列草稿），而
    # `test_subprocess_encoding_hygiene` 判準四要求「被當成 Python child 起的檔必須自帶
    # UTF-8 stdio 保護」——否則非 CJK locale 逃脫成 \uXXXX、非 UTF-8 locale 給亂碼、
    # stdout 更是 errors='strict' 直接崩潰。
    # 🔴 刻意放在 `__main__` 內而非模組層：本檔被當測試模組 import 時**不付**
    # `_stdio_utf8` 的副作用代價（同檔既有註解已載明那個代價是刻意迴避的），
    # 只有真的被當 child 起來印東西時才需要它。也刻意**不用**就地 reconfigure ——
    # 那會讓 `_FROZEN_STDIO_FORCE_TREES['tools']` 這個「複本數只准變少」的棘輪 +1，
    # 而這裡明明有唯一實作可用。
    import _stdio_utf8  # noqa: F401
    _flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if "--print-guard-lines" in _flags:
        _print_guard_lines()
    else:
        unittest.main(verbosity=2)
