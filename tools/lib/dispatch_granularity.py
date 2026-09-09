"""tools/lib/dispatch_granularity.py — DEF-200-274 第六輪：平行派工鍵細分邏輯。

WHY 抽成獨立檔：核心邏輯本應留在 `run_root_unittests.py`（緊鄰
`suite_modules()` 呼叫端），但該檔受 `AutoClaude/tools/check_loc_budget.py` 的
special-tier 行數棘輪管制（門檻＝納管當下實際行數，只准往下改），落地當回合已
無餘裕；棘輪的 override_reason 逐字指示「先刪死碼／抽共用模組（先例：
tools/lib/ci_liveness.py）」，故依此慣例把可獨立測試的判準邏輯搬來這裡，呼叫端
只留一行轉呼叫。本檔獨立持有 `_PLACEHOLDER_MODULE`／`_module_of()` 的複本（與
`run_root_unittests.py` 的同名邏輯**刻意不共用**，避免循環 import；兩者是否
仍同步由 `test_run_root_unittests.py::DispatchGranularityPlaceholderConstantStaysInSyncTest`
機械看守，非僅文件宣稱——第六輪四方獨立複審 Architect/SA/SD/QA 皆點名此處
落地當時零測試覆蓋，此為補齊後的狀態；`dispatch_key()` 本身的行為（白名單
細分／fail-closed 安全網／placeholder 特例）另由
`DispatchGranularityDispatchKeyTest` 看守，白名單模組無模組層 fixture 這條
前提由 `DispatchGranularityWhitelistHasNoModuleLevelFixturesTest` 看守）。

WHY 需要「細分派工鍵」這件事本體：實測（2026-09-09，`pytest --durations=30`）
`test_doc_loc_baseline_freshness_r60.py` 全模組 157.52s 裡，
`TestR67R3ThisFileMakesNoUnstatedPlatformAssumption.
test_every_lock_in_this_file_holds_under_every_simulated_platform` 這**一支**
測試就佔 118.49s（≈75%），其餘 276 支測試（35 個類別）合計僅約 39s——這正是
`tools/run_root_unittests.py::parallel_shard.run_parallel()` 先前五輪一直記錄
卻未解決的「頭重腳輕」根因本體（見
docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md 第五輪 QA
發現：「單一模組占平行總耗時 65%」）：舊版把「模組」當成不可分割的最小派工
單位，實際可分割的粒度是「類別」——`unittest.TestLoader.loadTestsFromName()`
原生支援 `module.ClassName` 這種點號路徑，`tools/lib/parallel_shard.py` 的
worker 完全不必改。

WHY 白名單而非全面套用：對其餘 ~300 支測試檔一律零影響（大多數檔案本來就只有
1 個類別，細分後派工鍵字面不同但實質等價於整檔派工）；未列入白名單的檔案即使
有多個類別也維持整模組派工——逐檔核實「類別之間是否有隱性共享狀態依賴」（例如
跨類別依賴的 `setUpClass`／模組層可變快取的填入順序）的成本，遠高於對單一
已知有此問題、且已核實無此類依賴的檔案動手（`test_doc_loc_baseline_freshness_
r60.py` 僅有惰性、鍵值式的模組層快取，各類別各自獨立 populate 不影響正確性，
只多付幾百毫秒重算成本；不同 worker subprocess 各自獨立直譯器，本來就不共享
快取，細分前後對「快取有沒有被重算」這件事沒有差異——差別只在原本 1 個
subprocess 內部循序重算 vs 現在最多 35 個 subprocess 平行各自重算）。
"""
from __future__ import annotations

import sys
import unittest

#: `run_root_unittests._PLACEHOLDER_MODULE` 的獨立複本（見檔頭 WHY，避免循環
#: import）。值＝`unittest.loader._FailedTest`／`_ErrorHolder` 的 `__module__`，
#: 是 stdlib 實作細節、不會隨版本改變。
_PLACEHOLDER_MODULE = "unittest.loader"

#: 已知單一類別耗時遠不成比例、且已核實類別間無隱性共享狀態依賴的檔案白名單
#: （WHY 見本檔檔頭）。未列入本表的檔案一律維持整模組派工。
#: `test_archive_defect_log`（2026-09-09 追加）：修完第一個熱點後，`⏱ 模組耗時
#: 排行` 浮現的**新**單一最重模組（224.5s／全套 4045 支的平行總耗時）。與前者不同
#: profile——無單一離群測試，而是 36 個類別合計 173 支測試普遍偏重（
#: `pytest --durations` 前 15 名散布 6~13s，非集中在一支）；類別間僅有一處
#: `setUpClass`（`TestArchiveFallbackResolvesClaims`），只設自己類別的 `cls.*`
#: 屬性、不被其他類別讀取，細分安全。
CLASS_LEVEL_DISPATCH_MODULES: frozenset[str] = frozenset({
    "test_doc_loc_baseline_freshness_r60",
    "test_archive_defect_log",
})


def _module_of(test: unittest.TestCase) -> str:
    """`run_root_unittests._module_of()` 的獨立複本（見檔頭 WHY）。"""
    cls = type(test)
    if cls.__module__ == _PLACEHOLDER_MODULE:
        return str(getattr(test, "_testMethodName", ""))
    return str(cls.__module__)


def dispatch_key(test: unittest.TestCase) -> str:
    """細分後的平行派工鍵。預設＝模組名（含 placeholder 特例）；僅
    `CLASS_LEVEL_DISPATCH_MODULES` 白名單內、且非 placeholder 的模組才改用
    「模組.類別」，讓已知的單一離群值類別能被其他 worker 分開派工。

    安全網：只有「類別是模組的頂層屬性、且 `getattr(module, qualname)` 真的解回
    同一個類別物件」才細分——巢狀／動態產生的類別（`__qualname__` 含 `<locals>`
    或非頂層屬性）一律退回模組粒度，因為 `unittest.TestLoader.loadTestsFromName`
    無法用字串路徑解析出這類名字（fail-closed：解不回去寧可不細分，不猜）。
    """
    module_name = _module_of(test)
    if module_name not in CLASS_LEVEL_DISPATCH_MODULES:
        return module_name
    cls = type(test)
    if cls.__module__ == _PLACEHOLDER_MODULE:
        return module_name
    qualname = cls.__qualname__
    if "<locals>" in qualname:
        return module_name
    mod = sys.modules.get(cls.__module__)
    if mod is None or getattr(mod, qualname, None) is not cls:
        return module_name
    return f"{module_name}.{qualname}"


def suite_dispatch_units(tests) -> dict[str, int]:
    """純函式：回傳「平行派工鍵 -> 測試數」，供 `parallel_shard.run_parallel()`
    消費（見 `dispatch_key()`）。`tests` 為呼叫端已攤平的測試清單
    （`run_root_unittests._flatten(suite)`）。與 `suite_modules()` 差異：本函式
    只決定派工單位，訊息用途一律仍用 `suite_modules()`（不受影響）。
    """
    counts: dict[str, int] = {}
    for test in tests:
        key = dispatch_key(test)
        counts[key] = counts.get(key, 0) + 1
    return counts
