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
    "DEF-101-324": Waiver(
        frozenset({"C1"}),
        "R60 前的舊列（2026-07-24）且**形態與 §4.3 不同**：本列是檔名淨化「多對一碰撞」的"
        " backlog，範圍是**全部凍結版連同 LATEST 一致存在**（版本數以"
        " `AISDLC_SDD/FRAMEWORK_STATUS.md` 現查為準，那裡是版本計數的唯一真相源；"
        "此處刻意不引數字——round 3 SD-R60R3-05 抓到的就是這一句寫死了當時的版本數）"
        "，不是「LATEST 已修、凍結版殘留」"
        "——放進 §9〈凍結版豁免與平台限制〉表會是一列**假的**凍結版缺口。它之所以落入"
        " §4.3.1，是因為狀態欄引用了 DEF-101-358 的 wontfix 判例字樣。C2 本列自己已滿足"
        "（狀態欄逐字「本輪重新評估後確認此範圍擴大不改變既有 wontfix/backlog 定性」）。",
        "承接輪次：**未指派**（觸發點＝任何輪次下次檢視 DEF-101-324 的 backlog 時，二擇一"
        "——判定確實需要 §9 列則補列（並刪本登記）；或在 ADR §4.3.1 之外另立「全版本一致"
        "存在」的分類，使本列不再落入 §4.3）",
    ),
    # R74 刪除一筆：該列已隨本輪歸檔離開主檔 ⇒ 已在本鎖射程外，登記若留著就是在遮蔽一個
    # 不存在的標的（本鎖自帶的 stale 自檢會判紅，正確處置是刪登記而非放寬判準）。
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

# 🔴🔴 R67 round 2（SA-R67-08）凍結基準：兩個 shrink-only 常數的「上一版」不再由 git 導出。
#
# 病灶（SA 沙箱實證，非推論）：舊實作以 `git show HEAD:<本檔>` 取上一版。未 commit 時它確實
# 有牙（改大即紅），但**每一個真正消費本鎖 rc 的閘門都跑在 commit 之後**——`tools/git-hooks/
# pre-push` 的 root-infra leg 走 `run_root_unittests.py`，而 push 必然發生在 commit 之後；CI
# 更是乾淨 checkout。commit 一落地，HEAD 就等於工作樹 ⇒ previous == current ⇒ 恆真。SA 實測
# 把 `_MAX_BASELINE_ENTRIES` 放大十餘倍後 commit，本類全綠、鎖檔內容與門檻的對照零訊號。
#
# 為什麼凍結常數不會重蹈恆真覆轍：git 導出的基準會被「commit」這個動作自己同步過去，而
# 每個閘門都在那之後才跑；簽入原始碼的字面常數則 commit 不動它、checkout 不動它、CI 乾淨樹
# 也不動它——只有人手改那一行才會變。於是「門檻」與「基準」是兩個獨立可變的量，比較在任何
# 時點、任何消費者（髒樹／pre-commit／pre-push／CI）都非退化。整條 git 依賴一併消失，
# 連帶消滅舊實作的另一面 fail-open：`previous is None`（git 取不到）時整支 skip。
# 論證與形狀逐字同 `tools/check_script_parity.py` 的 `_TIER_BASELINE`（R67-H14），
# 該處是照抄本檔而來的下游——本輪把上游本體也修了。
#
# 殘餘面（誠實揭露，與 R67-H14 同一句）：同一個 commit 內**同時**改門檻與本組凍結基準仍可
# 通過——這是所有釘選式棘輪共有的邊界，與「零成本、隱形、自動」的舊行為是不同量級；且本組
# 是純量，調升在 diff 上就是一個變大的數字，方向一望即知（不像 tier 名稱那樣需要對照表）。
# 本性質有機械鎖：`TestShrinkOnlyRatchet::test_ratchet_is_independent_of_git_state`
# （禁用 subprocess 仍須完整運作），舊實作在該鎖下會直接紅。
# 另有一道獨立張力：`_BASELINE_ID_CEILING` 同時被 `TestCriterionIsBoundToAdrProse` 綁在
# ADR §4.3.4 的宣告句上 ⇒ 調升它還得動 ADR，那是本檔之外的第三個站點。
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
# 🔴 本輪落地物（掌舵者親自拍板）：這個位置原本是一個**純量檔數**棘輪——
# `tools/tests/` 的鎖檔支數只准往下。它擋的是「一個 finding 一支新鎖檔」的檔案增生，
# 而長期實測的結論是**它把病換了個地方長**：歷次取樣的支數一格不動，同期行數卻翻倍有餘
# （現值現查 `live_triplet()` 的 glc 兩欄）。舊訊息指示「擴充進既有鎖檔」，增量因此被擠進
# 少數 mega-file，而護欄層**行數**在全 repo 一個消費者都沒有——
# `AutoClaude/tools/check_loc_budget.py` 把 `tools/tests/` 排除在 tier 檢查外，其理由欄
# 指向的兩道機制一個量的是檔數、一個量的是行**長度**，都不是行數。
#
# ⇒ 一進一出、機制數不變：純量檔數 → **逐檔行數表**。新表同時承接三件事：
#   (a) `DEF-101-561③`「禁止新增鎖檔、只准合併／刪除」——新檔在表上沒有列，且只要
#       淨行數上升就紅；淨額不上升的合併／改名照舊合法（那是該裁決指定的動作）。
#   (b) 護欄層**行數**第一次有判準在讀（`guard_line_problems`／`glc_growth_problem`）。
#   (c) ADR §4.3 的 GLC 行數與本表是**同一個家**：`live_triplet().glc_lines` 與
#       `sum(_FROZEN_GUARD_LINES.values())` 走同一個 glob，不再是兩個各自漂移的站點。
#
# 🔴 方向是**收緊**：改版前「一輪加三萬行全綠」，改版後「淨增一行即紅」。
# 🔴 重釘紀律（照抄 `run_root_unittests.MIN_TESTS` 的既有慣例，不另立體例）：值一律是
# **當回合實測**、零加減推算；多包並行的輪次由**收尾包在所有包停工後**重釘一次，
# 並在 `_GUARD_LINES_REPIN_LOG` 補一列（不補即紅——淨額因此在結構上不可能缺席）。
# 現查／重釘用：`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`
# （🔴 R78 ARCH-02：這個旗標在 R77 只存在於紅燈訊息裡，實跑 rc=2 `unrecognized arguments`；
#   本輪補上 `__main__` 分派，並由 `TestRepinCommandIsReal` 雙向釘住「訊息教的指令必須真的
#   跑得動」——否則棘輪一紅，唯一出路是逐列手改整張凍結表，而那樣改的人不會順手算淨額）。

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
#: 🔴 為何檔數棘輪要退場、而這張表是它的接手者：檔數被釘住之後，護欄層的成長並沒有停，
#: 只是全部灌進既有巨檔——同期行數翻倍而唯一的通過判準（檔數相等＋glob 非空）全程綠。
#: 「只准變少」預設了「變多是安全的」，而那個預設在這一層被實測推翻。行數面把成長本身
#: 變成會轉紅的事件，方向仍是收緊（成長側零容忍，見 `glc_growth_problem`）。
#:
#: 維護方式（不是「調高就好」）：合法縮小後**必須**同步下修本表，否則餘裕就是日後無聲
#: 加回去的破口（`[基準過時]` 那一款在守這件事）。真的必須長大時，重釘本表並在交件回報
#: 寫出淨額與理由——讓方向在 diff 上一望即知。
#: 🔴 本表含**本檔自己**，所以動本檔就會動到本表 ⇒ 改完必須重跑一次並用實測值收斂。
_FROZEN_GUARD_LINES: dict[str, int] = {
    "_platform_helpers.py": 519,
    "_ps_engine.py": 115,
    "test_act_local_runner_image.py": 322,
    "test_adr_xplat001_c1c2_lock.py": 4158,
    "test_archive_defect_log.py": 3786,
    "test_bash32_compat.py": 609,
    "test_bash_probe_spec_contract.py": 960,
    "test_bootstrap_core.py": 439,
    "test_bootstrap_ps1.py": 160,
    "test_check_defect_log_crossref.py": 2770,
    "test_check_gha_action_versions.py": 295,
    "test_check_hooks_liveness.py": 1930,
    "test_check_pytest_baseline_sites.py": 297,
    "test_check_script_parity.py": 1973,
    "test_check_wrapper_thinness.py": 1316,
    "test_component_sanitizer_shared_layer_lock.py": 293,
    "test_context_budget_guard.py": 1427,
    "test_defect_id_reference_integrity.py": 261,
    "test_dev_start.py": 6686,
    "test_dev_start_ps1_lastexitcode.py": 462,
    "test_doc_env_prefix_platform_parity_r60.py": 332,
    "test_doc_loc_baseline_freshness_r60.py": 5896,
    "test_extras_quoting_zsh_safety.py": 402,
    "test_find_git_bash_parity.py": 1225,
    "test_gha_action_versions.py": 703,
    "test_git_hooks_install_common.py": 521,
    "test_install_windows_nightly.py": 1469,
    "test_macos_smoke_skip_honesty.py": 225,
    "test_maturity_criteria_r79.py": 427,
    "test_nightly_interpreter_determinism.py": 278,
    "test_no_invalid_escape_sequences.py": 329,
    "test_ntfs_trailing_space_device_name.py": 772,
    "test_onboarding_parity_interlock.py": 235,
    "test_platform_neutral_paths.py": 4092,
    "test_platform_utils_dedup.py": 1103,
    "test_pre_commit_dispatcher_sigpipe.py": 498,
    "test_pre_push_dispatcher.py": 798,
    "test_ps1_bom.py": 204,
    "test_ps51_compat.py": 621,
    "test_ps_engine_ssot.py": 933,
    "test_python_c_percent_shim.py": 119,
    "test_root_infra_parity.py": 441,
    "test_run_root_unittests.py": 1730,
    "test_sanitize_component_frozen_sdd_versions_lock.py": 375,
    "test_schedule_capability_parity.py": 591,
    "test_script_scan_surface_ssot.py": 391,
    "test_smoke_ci_sync.py": 1355,
    "test_stdio_utf8.py": 76,
    "test_subprocess_encoding_hygiene.py": 1525,
    "test_windows_forbidden_filename_parity.py": 1043,
    "test_windows_nightly_anchor_parity.py": 135,
    "test_windows_smoke_heartbeat_doc_sync.py": 197,
    "test_windowsapps_guard_bash_parity.py": 956,
    "test_windowsapps_guard_cross_consistency.py": 2222,
    "test_workflow_permission_concurrency_lock.py": 1357,
    "test_workflow_schedule_sync.py": 309,
    "test_workflow_timeout_coverage.py": 158,
}


#: 重釘稽核痕跡（**append-only**）：`(輪號, 舊總量, 新總量, 淨額, 理由)`。
#:
#: 🔴 R78 ARCH-01 的落地物。缺陷本體：舊的檔數棘輪重釘是**一個**數字，一望即知方向；
#: 換成逐檔行數表之後，重釘變成「整張表同時變」，而**淨額不出現在任何地方**——
#: 實測 `a7a3080` 這一個 commit 內量測面 54188 → 57693（+3505），閘門全程 rc=0。
#: 也就是說「重釘」在機械上與「順手更新一下」無法區分，棘輪的張力全靠人自律。
#:
#: 本表把淨額變成**結構上不可能缺席**的東西：`test_the_repin_log_accounts_for_the_frozen_table`
#: 斷言「表尾那一列的新總量必須逐字等於 `sum(_FROZEN_GUARD_LINES.values())`」⇒ 動了那張表
#: 而不補一列理由，當場紅；補了列卻算錯淨額，也紅（逐列自洽 ＋ 首尾相接）。
#: 維護方式：`--print-guard-lines` 會連這一列的草稿一起印出來，照貼即可。
_GUARD_LINES_REPIN_LOG: tuple[tuple[str, int, int, int, str], ...] = (
    (
        "R77", 54188, 57693, 3505,
        "PKG-GUARD／R77-24：檔數棘輪退場、逐檔行數表接手。本列是回填的**起點列**——"
        "R77 當輪並沒有稽核痕跡這回事（那正是 R78 ARCH-01 的缺陷本體），"
        "兩個數字取自 skeptic 對 a7a3080 的實測，非事後推算。",
    ),
    (
        "R78", 57693, 59936, 2243,
        "R78 四方複審後的五個修復包，加上兩支新機械物，"
        "由收尾者在所有包停工後一次重釘。"
        "淨額歸因（各包自陳，可回查各自交件回報）："
        "A-lint +129（把「只測會過的那幾種寫法」的回歸鎖，"
        "換成漏擋與誤擋兩個方向逐一注入的判準表，"
        "另加別名與全名的對稱性判準）；"
        "D-doc +315（成熟度 SSOT 新鮮度鎖、交棒書宣稱可查性鎖、"
        "pytest 基線簡寫形態判準）；"
        "E-posttooluse +237（PostToolUse 註冊面 shrink-only 鎖，"
        "該面此前完全無人守；hook 路徑去重的納管面"
        "由寫死名單改為目錄列舉減具名排除表）；"
        "C-ghost（幽靈符號判準射程由「反引號路徑」"
        "擴到「反引號 Python 識別字」——那正是懸空引用逃逸的縫；"
        "另含本表本體與 guard_baseline_gaps 實作）；"
        "B-audit（probe 逐工具計數與 per-session 崩塌判準的回歸鎖）。"
        "另新增兩個鍵：act 自建映像的一致性與雙平台旗標對等鎖、"
        "session context 水位守衛的回歸鎖（值見上方凍結表）。"
        "🔴 本輪未刪任何行換取餘裕、未調高任何門檻；"
        "成長全部是新判準，且每一道都附"
        "「改壞→紅→還原→驗乾淨」的注入證明。",
    ),
    (
        "R79", 59936, 61421, 1485,
        "R79 十維掃描後的七個修復包，由收斂包在所有包停工後的單人窗口一次重釘。"
        "本輪同時發生兩個相反方向的大額變動，故淨額不代表任何單一包的行為："
        "**減**＝架構包讓 .ps1 掃描面的三份獨立實作收成一份（CI 的 pwsh 解析步驟與 "
        "Windows smoke 改呼叫 Python SSOT），連帶讓「偵測三份是否同步」的對抗式正則錨整組退場；"
        "**增**＝跨平台包在既有鎖檔內落地四個新機械物（工作樹行尾、git 索引 exec bit、"
        "會改動目錄項的 Windows 鎖檔原語、站點級 AST 守衛）與其紅綠自證，"
        "觀測者包把 PowerShell 攔截器與量測器的判別力鎖補齊，"
        "context 水位包補上 window 交叉否決與 PreToolUse 阻斷的成對注入，"
        "清債包補上帳本逐列位元組上限的四向注入，"
        "收斂包補上重釘稽核痕跡的 append-only 兩款、逐檔漂移款、"
        "幽靈符號鎖的 docs 引用面與豁免天花板、以及 hook 文件宣稱的第三向。"
        "🔴 本輪未為了讓數字好看而調高任何門檻：唯一破線的 LOC 棘輪"
        "（tools/check_script_parity.py）是以同一次變更內刪等量行收斂的，非重釘。",
    ),
    (
        "R79", 61421, 61829, 408,
        "R79 續航包（ADR-XPLAT-004）：Token 額度續航協定落地後的第二次重釘。"
        "**淨額幾乎全部集中在單一支鎖檔**（現查 `--print-guard-lines` 的 DIFF 欄為準；"
        "另一部分是本檔自己被這一列撐大的量），因為本包的硬約束是**新增檔案數＝零**："
        "額度事件的判讀住既有的 context_budget_guard.py（逐字稿掃描的實作已經在那裡）、"
        "CLI 與排程編排住既有的 session_resume_planner.py（run_powershell／schtasks／"
        "next_run_time 取證閘已經在那裡），測試依 DEF-101-561③ 併進既有鎖檔。"
        "成長內容＝新判準各自的成對注入："
        "額度事件分類（session 額度 vs 月度支出上限——兩者的字面前綴相同，"
        "只比對前綴會把「等待無效」那一類判成可等待，比例見 ADR-XPLAT-004 §2.2）；"
        "reset 時刻算術（不帶日期不帶年 ⇒ 「下一個尚未發生的該時刻」，含跨午夜與 12am/12pm）；"
        "續航狀態塊的體檢（缺鍵／無 NextRunTime 憑證卻宣稱已排程／猜出來的 reset 拿去武裝）；"
        "醒來後的分支判定（續跑／硬停／短退避／依新觀測重排／拒絕猜測）；"
        "以及水位計在額度耗盡當刻讀成 0% 的修復（合成記錄的 usage 欄全為零，"
        "使「量不到」被讀成「量到零」，計數以 ADR-XPLAT-004 §5 的現查為準）。"
        "🔴 本輪未刪任何行換取餘裕、未調高任何門檻；"
        "tools/session_resume_planner.py 一度破 guardrail_cli 那一格，"
        "是以**同一次變更內收掉重複實作**收斂的（schtasks 腳本產生器由兩份併成一份，"
        "順帶修掉舊那份「把整份任務書內嵌進 -Command 當 prompt」的缺陷），非重釘。",
    ),
    (
        "R79", 61829, 62439, 610,
        "R79 **四方複審後的修復包**（四方皆 APPROVE_WITH_CONDITIONS），"
        "由收斂包在四包停工後的單人窗口一次重釘。"
        "🔴 本列刻意不逐檔登載數字——逐檔淨額現查 `--print-guard-lines` 的 DIFF 欄，"
        "寫進理由欄就是再造一個沒有人會回頭改的量測站點（本檔通篇在治的病）。"
        "成長歸因（各包自陳，可回查交件回報）："
        "鎖的鑑別力包＝把掃描面 SSOT 的必要旗標補進判準、"
        "成熟度 M1 由「二擇一」改成合取並補上判準本體的鎖、"
        "工作樹行尾政策改由 .gitattributes 現查（除掉第二個家）；"
        "skipped 機制包＝skip 分群普查接上兩條 push 通道，"
        "並把「量測塌掉時印共零支而回綠」改成以 pytest 自己的摘要行對帳；"
        "收斂包＝續航排程腳本五個內插點的單引號跳脫回歸鎖（判產出不判呼叫，"
        "與真 tokenizer 兩地對照過）、交棒書鎖的巢狀標題射程修復與三向自檢。"
        "🔴 本輪未刪任何行換取餘裕、未調高任何門檻、未放寬任何棘輪；"
        "唯一因本輪變更而破線的是 ONBOARDING 表② 指紋，"
        "處置是在**出廠乾淨 venv**（無 PG extras、無 sdk extra）重量後回填，"
        "而不是用手上這支裝了 extras 的直譯器加旗標繞過那道拒跑守衛——"
        "後者會讓表② 宣告的「出廠環境」語意在沒有人察覺的情況下換掉。",
    ),
    (
        "R79", 62439, 62781, 342,
        "R79 **續航哨兵（預防性武裝）與其接電點**，由收尾者在所有 agent 停工後的"
        "單人窗口一次重釘。逐檔淨額現查 `--print-guard-lines` 的 DIFF 欄，本列不登載。"
        "成長歸因：哨兵在既有鎖檔內落地五分支判定（依觀測 reset 重排／探測／續巡／"
        "自我解除／月度上限硬停）的逐支注入鎖，以及兩個閾值的**量測依據**鎖——"
        "巡邏間隔必須大於實測最短的「撞線到 reset」窗（否則「精確重排」那一支在最短窗下"
        "結構上不可達），自我解除門檻必須大於一個完整額度視窗（否則等額度期間逐字稿"
        "不更新，會被誤判成工作已結束而自拆）；收尾者另補一列 hook 註冊基準與其理由。"
        "🔴 **為何本列不走「同一次變更內刪等量行」那個合法出口**："
        "本包治的正是「機制蓋好沒接電」——同一輪內連撞兩次額度而續航協定零作用，"
        "根因是它只有手動武裝入口，而額度耗盡是 API 層失敗、"
        "在 hook 體系裡沒有任何觸發點 ⇒「撞到才反應」結構上不可能成立。"
        "刪掉別處的判準來換這裡的額度，等於用一個已經守住的面換一個新開的面，"
        "淨鑑別力不升反降。未調高任何門檻、未放寬任何棘輪、未動漂移容忍值。",
    ),
    (
        "R79", 62781, 62821, 40,
        "R79 收輪後的靜默修復（掌舵者當場回報：哨兵每 15 分鐘彈出一個 console 視窗）。"
        "🔴 本列的價值在於**任務書給的根因是錯的**：舵手判定「LogonType 沒對齊既有兩支」，"
        "而修復者當回合實測打掉了這個前提——註冊 S4U 需要提權，非提權下 Register-ScheduledTask "
        "直接存取被拒、工作根本不會建立；而哨兵的主要武裝路徑是 SessionStart hook＝一律非提權，"
        "只掛 S4U 會把「彈視窗」換成「整條武裝不起來」。真正的解在**載具**："
        "python.exe 是 CONSOLE 子系統、pythonw.exe 是 GUI 子系統，後者 OS loader 不配置 console，"
        "不論 LogonType 為何都不彈。成長即這兩條鎖（無 console 直譯器、S4U 先試非提權回退）"
        "與其成對注入。同一趟另修掉一個同型缺陷：Register-ScheduledTask 失敗後仍印 REGISTER_OK"
        "（非終止錯誤沒中斷 scriptblock）＝本 repo 反覆在治的「真紅讀成綠」。"
        "🔴 未調高任何門檻；planner 一度 750/750 滿載，是以壓縮接續行與 docstring 騰出空間"
        "（`count_loc` 排除空行與註解行，所以把註解搬進 ADR 一行都省不到——這一點也是實測得知）。",
    ),
)


#: 逐檔漂移的容忍筆數（R79 收斂包）。**釘 0，且沒有理由留餘裕**——重釘時
#: `--print-guard-lines` 會把整張表逐檔照貼，餘裕只會替下一次「淨額為零的 A 減 B 增」
#: 預先開門，而那個對調正是 R79 在乾淨 HEAD 上實測到的既成事實（三支檔失真、閘門全綠）。
_GUARD_LINE_DRIFT_TOLERANCE = 0

#: **凍結前綴**的長度與內容指紋——把 `_GUARD_LINES_REPIN_LOG` 檔頭那句「**append-only**」
#: 由散文變成機械事實。前綴內的任何一列被改寫（改數字／改理由／兩列合併成一列／整段砍掉），
#: 指紋當場不同；而**追加**新列不動前綴，指紋不變 ⇒ 正常的每輪重釘零額外維護。
#:
#: 為何是「固定長度的前綴」而不是「除最後一列外」：後者在追加時前綴會跟著長大，於是每一輪
#: 都得改一次 sha 常數——那種鎖實務上一定被改寬（本 repo 對「維護成本過高的鎖」有判例）。
#: 代價是**尾端最多一列不受指紋保護**，由 `_REPIN_LOG_MAX_UNFROZEN_TAIL` 把那個窗口釘死：
#: 追加當輪不必動指紋（一列寬限），下一輪要再追加就必須先把前一列納入前綴並重釘，
#: 否則 `[前綴過期]` 轉紅。草稿兩個值都由 `--print-guard-lines` 印出
#: （ARCH-02 的教訓：紅了卻沒有出路的鎖會被關掉）。
_REPIN_LOG_FROZEN_PREFIX_LEN = 7
_REPIN_LOG_MAX_UNFROZEN_TAIL = 1
_REPIN_LOG_HISTORY_SHA256 = (
    "9d140759e87e04579bd32d7ac4460ac47db5bd30fab1b89dd4db9285dd39c726")


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


def repin_log_problems(
    log: Sequence[tuple[str, int, int, int, str]],
    frozen_total: int,
    *,
    history_digest: str | None = None,
    prefix_len: int = 0,
    max_unfrozen_tail: int | None = None,
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

    🔴 **(6)(7) 是 R79 收斂包補的，它們治的是這張表自己的假話**：檔頭逐字寫著
    「**append-only**」，而 R79 掃描實測 append-only **零機械強制**——把 R77＋R78 兩列
    壓成一列、把起點的舊總量從 54188 改成任意數字（實測 90000），(1)~(5) 全部沉默、
    `rc=0`。而本表存在的唯一理由是「讓淨額在結構上不可能缺席」，壓平歷史比不補一列
    更難看見（表上永遠都有一列）。**合併歷史與追加新列在機械上原本無法區分**——那正是
    R78 ARCH-01 對「重釘 vs 順手更新一下」下過的同一句判詞，只是這次長在防它的機制上。

    兩個參數刻意可傳（不讀模組常數）：注入測試要能拿合成表的指紋當基準，否則它們只在
    「真表剛好等於常數」時才有鑑別力——同 `iron_law3_ratchet_problems()` 已寫過的理由。

    誠實劃界：本判準保證「有一列、算術自洽、與凍結表對得上、既有列沒被動過」，
    **不保證那個理由是好理由**（那是人審責任，同 C2 只保證字樣在、不保證觸發條件寫得對）。
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
    if log[-1][2] != frozen_total:
        problems.append(
            f"[未對帳] 稽核痕跡表尾的新總量 {log[-1][2]} 不等於 _FROZEN_GUARD_LINES 實際總量 "
            f"{frozen_total}——改了凍結表就必須同一次變更補一列 "
            f"(輪號, {log[-1][2]}, {frozen_total}, {frozen_total - log[-1][2]}, '理由')；"
            "少了這條，整張表同時變而淨額不出現在任何地方（R78 ARCH-01）。"
            "草稿：python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines")
    return problems


def guard_baseline_gaps() -> list[str]:
    """檔數面有、行數面看不到的鎖檔（正常為空清單）——兩個掃描面的**涵蓋關係**證明。

    🔴 R78 ARCH-04：`_GUARD_LINE_PATTERN` 上方那句「涵蓋關係改由 `guard_baseline_gaps()`
    證明」在 R77 寫下時，這個函式**並不存在**（全庫 AST 零定義）。兩個面刻意不同——
    檔數面是遞迴 `test_*.py`（閘門會跑哪幾支），行數面是非遞迴 `*.py`（這一層有多大）——
    而「不同」與「有東西從縫裡掉出去」是兩件事，後者需要有人算。

    本函式算的就是那個縫：閘門會跑、但行數棘輪量不到的檔 ⇒ 它的成長不會讓任何東西轉紅。
    與 `guard_surface_escapes()` 的分工：那一支問「子目錄裡有沒有 .py」（行數面的已知代價），
    本函式問「檔數面的每一支是不是都被行數面數到了」（兩面之間的涵蓋關係）。今天兩者的
    答案同源（唯一的逃逸方式就是落進子目錄），但它們是**不同的問句**——把它們併成一個，
    日後任一 glob 改動時就會有一個問題沒人問。
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

    🔴 **(6) 為何非補不可（它不是潔癖，是已發生的實況）**：本函式原本的誠實劃界段逐字
    寫著「淨額為零的『A 減 B 增』對調…(4)(5) 都不會說話」——而 R79 掃描在**乾淨 HEAD**
    上實測到那個盲區已經是現況：三支檔（−11／+7／+4，淨額 0）與磁碟不符，棘輪與
    `--print-guard-lines` 雙雙印綠，照流程走的人只會看到「不需要重釘」。劃界不等於防護。
    後果有兩層：①凍結表的逐檔數字不再能當基線用，「哪支檔長了多少」的歸因全錯；
    ②在總量守恆的前提下，任一支護欄檔可以無限膨脹只要別支等量縮水——那正是**檔數棘輪
    退場時列出的原始病灶**（「成長全部灌進既有巨檔」），換到行數面之後只是把巨檔換成整層。

    容忍度是**參數**不是常數（同 `iron_law3_ratchet_problems()`）：注入測試拿現況當基準，
    活體判準拿釘住的 `_GUARD_LINE_DRIFT_TOLERANCE` 當基準。現行釘 0——重釘時逐檔照貼，
    容忍度就沒有存在的理由；留餘裕等於替下一次「淨額為零的對調」預先開門。

    誠實劃界（本判準**仍**抓不到的）：本函式只讀兩張表，看不到「某支檔改了 10 行、
    同一支檔又刪了 10 行」這種檔內互抵——那要 diff 才看得到，不在行數面的定義域內。
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

    WHY（ARCH-R60R3-04）：`DEF-101-561③` 在 R60 round 3 被訂正為「**現在即判定已觸發**：
    R61 開輪即進入禁止新增鎖檔、只准合併／刪除」。Architect 全 repo 實查該裁決的落地狀況，
    結果是它只活在帳本一格散文與一行註解裡——**零機械強制**。而本檔檔頭自己立的標準是
    「把 §4.3 的兩條件做成機械鎖才叫落地——沒有這道鎖，§4.3 就只是散文，本輪已經自證」。
    同一把尺量回這條裁決，結論一樣：沒有鎖，它就只是散文。本類就是那道鎖。

    🔴 **量測面在 R77 換過一次，語意跟著換了**（動它之前先搞清楚現在管的是什麼）：
      · **舊**：純量「鎖檔支數」，只准往下 ⇒ 讀起來就是「禁止新增鎖檔」。長期實測的結論是
        它把病換了個地方長——支數一格不動，同期行數翻倍有餘，判準全程綠。
      · **現**：`_FROZEN_GUARD_LINES` 逐檔行數表，判準是**淨行數不得上升**
        （`guard_line_problems`／`glc_growth_problem`）。
      · 🔴 因此接手者的語意**不是**「禁止新增檔案」：新增一支鎖檔，只要同一次變更內刪掉
        等量以上的行就合法（那正是該裁決指定的「合併」動作）；反之只改既有巨檔卻淨增一行
        照樣紅。**R78 ARCH-03 實查到散落各處的引用仍逐字寫著舊語意**，那是對已移除機制的
        複述，不是接手者的規則——看到那種寫法請一併訂正，不要照著做。
      · 重釘不是「調高就好」：`--print-guard-lines` 產出新表，並在 `_GUARD_LINES_REPIN_LOG`
        補一列（含淨額與理由），不補即紅（R78 ARCH-01）。

    本類仍保留兩支**檔案面**的自錨（`guard_files_in_worktree()` 與根層閘門 pattern 的
    SSOT 綁定）：行數面是非遞迴 `*.py`、檔案面是遞迴 `test_*.py`，兩個面的涵蓋關係由
    `guard_baseline_gaps()` 證明。`_*.py` 這種**共享零件不進檔案面**：`DEF-101-561①`
    指定的 R61 合併動作本身就是「把四支 AST helper 抽成一支共享剝除層」，把零件算進來
    會讓那個**被裁決指定的合併動作自己翻紅**（獎勵把重複貼回各鎖檔、懲罰抽共用層）。
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
            max_unfrozen_tail=_REPIN_LOG_MAX_UNFROZEN_TAIL)
        self.assertEqual(problems, [], "重釘稽核痕跡不合規：\n  " + "\n  ".join(problems))

    def test_repinning_without_logging_a_reason_is_red(self) -> None:
        """注入①：凍結表被改動（總量 +1）卻沒補一列 ⇒ `[未對帳]` 必紅。"""
        total = sum(_FROZEN_GUARD_LINES.values())
        problems = repin_log_problems(_GUARD_LINES_REPIN_LOG, total + 1)
        self.assertTrue(problems, "改了凍結表而不補稽核列竟然放行 ⇒ ARCH-01 沒有被修")
        self.assertTrue(any("[未對帳]" in p for p in problems), problems)

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

    def test_appending_one_row_keeps_the_history_digest_stable(self) -> None:
        """對照組：**追加一列**是每輪的正常動作，指紋與判準都不得因此說話。

        少了這一條，上面兩支「注入必紅」可能只是因為指紋對任何變動都紅——那樣的鎖
        會讓每一輪的正常重釘都得改一個 sha 常數，實務上一定被改寬。
        """
        total = sum(_FROZEN_GUARD_LINES.values())
        appended = (*_GUARD_LINES_REPIN_LOG,
                    ("R99", total, total + 5, 5,
                     "合成的下一輪重釘，理由長度足以通過 [無理由] 那一款"))
        self.assertEqual(
            repin_log_history_digest(appended, _REPIN_LOG_FROZEN_PREFIX_LEN),
            _REPIN_LOG_HISTORY_SHA256,
            "追加一列竟然改變了前綴指紋 ⇒ 每輪都要改 sha 常數，這道鎖會被關掉")
        self.assertEqual(
            repin_log_problems(
                appended, total + 5,
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
# 🔴 本段落地的是 **SA-R67-03**：`ADR-XPLAT-002` §9.1 與 `CrossPlatform_Scan_Dimensions.md`
# 〈常設自檢〉把本輪三項頭號架構異動（Phase 3 解封／平台前提中立化／§8 交棒表機制化）的
# **唯一防回流機制**寫成了幾條 grep 指令，而那些指令在全 repo **沒有任何可執行消費者**——
# 複審員注入違規形態後，根層測試與根層工具全數綠燈。依 `CrossPlatform_Scan_Dimensions.md`
# Scan-H 判準⑤「可重跑但沒有任何閘門看它的 rc ＝ 不可重跑」，它們嚴格說是「規格 ＋ 已驗證
# 的實作」，**不是活體守門**。本段把它們接上閘門的 rc（本檔在 `run_root_unittests.py` 的
# discover 收集面內 ⇒ 自動被 pre-push root-infra leg 與三支 CI 消費）。
#
# 宿主選擇（§9.1 末段已具名指派，本段沿用）：**擴充本檔而非新增鎖檔**——
# `TestGuardLayerRatchet` 的護欄層棘輪要求 `tools/tests/` 的**淨行數**不得上升
# （DEF-101-561③；新增檔案本身不違規，淨額上升才違規），
# 且 `ADR-XPLAT-002` §4.2 rule 1 明文「不要一個 finding 一支鎖」。
#
# 🔴 從 shell 規格搬進 Python 時**刻意改掉的語意**（照抄原形態會得到假鎖）：
#   (1) SC-7 的規格形態尾巴掛著 `| grep .`，因為 `comm` **無論有無差集都 exit 0**，直接讀它的
#       rc 會恆綠（規格自己已逐字警告這一點）。本檔改用 **Python 集合差集**，不依賴 shell 方言
#       （規格末段也建議這麼搬），rc 語意由「回傳的違規清單是否為空」決定。
#   (2) 其餘各條的規格形態是 `grep`（rc=1 且零輸出＝通過）。本檔一律回傳「違規說明字串的
#       list」，空 list ＝通過——測試失敗訊息因此能逐條印出違規行，比一個 rc 更能指路。
#   (3) 各條的**掃描面崩塌**（章節標題被改寫、帳本家族枚舉壞掉、維度表表頭形態被改）一律
#       回報成違規而非靜默零命中：`grep`／`awk` 對「找不到區段」回的是空輸出＝在原語意下
#       等同通過，那正是本 repo 已多次踩到的 fail-open。
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
# 🔴 R67 round 4（SA2-R67-01）把 SC-2／SC-3 的下界由 `_SEC8_END_ALL` 收窄到此。原版掃 §8 全區，
# 於是 §8.3——本 repo 自己指定的「逐字保全散文區」——也落在射程內，而這三條**都沒有同行豁免**
# （只有 SC-1／SC-4 走 `_line_hits_with_waiver`）。後果可列舉：下一次照本輪體例把一句含
# `**R62+**` 或千分位常數的 §8 原文保全進 §8.3，該鎖即**永紅**，而唯二出路都是本 repo 已判過
# 更糟的——改寫保全原文（違反逐字保全紀律），或臨時加豁免（「誤報的鎖最後一定被加豁免繞過，
# 比沒有鎖更糟」，見本檔多處與 `DEF-101-700` 的拒收理由）。
# ⇒ 豁免路徑刻意**不是**新加一枚標記，而是沿用 §9.1 邊界 (b) 已裁決的既有出口：**把逐字原句
#   移進 §8.3 散文區**。界線對齊後，「§8.3 是這幾條共同的保全區」才從口號變成一句真話。
# `_SEC8_END_ALL` 保留給 `test_the_scan_surface_did_not_collapse`——它以「全區嚴格長於本體」
# 反證 `### 8.1` 界線還活著（界線一旦失效，這幾條會一起退化回掃全區，正是本次修掉的形態）。
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
    """
    rounds = _coverage_table_rounds(c.adr2)
    if not rounds:
        return ["SC-10：§6 抽不到任何 `| R<n>` 覆蓋表列 — 掃描面已崩塌（表被改名／改格式？）"]
    current = _current_round_from_ledger(c)
    if current is None:
        return []  # 帳本推不出輪次時不猜（無訊號 ≠ 壞訊號），與 ci_liveness 同紀律
    if current in rounds:
        return []
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
)


def _drop_current_round_row(c: Corpus) -> Corpus:
    """把當前輪那一列從 §6 覆蓋表刪掉＝R74 開輪時的實況（表停在 R72、缺 R73）。"""
    current = _current_round_from_ledger(c)
    assert current is not None, "SC-10 注入需要帳本能推出輪次"
    kept = [ln for ln in c.adr2.splitlines()
            if not re.match(rf"^\s*\|\s*R{current}\b", ln)]
    assert len(kept) < len(c.adr2.splitlines()), f"注入未刪到任何 R{current} 列"
    return c._replace(adr2="\n".join(kept))


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


def _print_guard_lines() -> None:
    """印出可直接貼回 `_FROZEN_GUARD_LINES` 的 dict 字面 ＋ 淨額 ＋ 稽核列草稿。

    三段輸出對應重釘要動的三個地方，照貼即可：淨額註解行、新的凍結表、
    `_GUARD_LINES_REPIN_LOG` 的新列（理由欄留空給人填——**刻意不代填**，
    ARCH-01 要的就是有人為那個淨額負責）。
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
