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

import importlib
import os
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
#: `test_run_root_unittests`（QA 2026-09-23 核實追加）：本檔自己——無
#: `setUpModule`／`tearDownModule`，類別間無共享可變狀態（每個 `_TopLevel
#: DispatchFixture*` 頂層 fixture 類別只被自己所屬的測試類別讀取）。
#: `test_platform_neutral_paths`（QA 2026-09-23 核實追加）：無
#: `setUpModule`／`tearDownModule`；僅兩處 `setUpClass`
#: （`TestExecBitIsGovernedViaTheGitIndex`／`TestXplatInjectionMatrix`），皆只
#: 設自己類別的 `cls.*` 屬性、不被其他類別讀取，其餘皆為模組層唯讀常數
#: （import 期算好，測試執行期不再被寫入），細分安全。
#: `test_context_budget_guard`（QA 2026-09-23 核實追加）：**有**
#: `setUpModule`／`tearDownModule`，但只 pin／還原 `os.environ`（行程內狀態，
#: 子行程天然隔離、per-subprocess 重跑成本可忽略）——見
#: `_MODULE_FIXTURE_SAFE_EXCEPTIONS` 的核實結論，本模組是目前唯一的例外。
CLASS_LEVEL_DISPATCH_MODULES: frozenset[str] = frozenset({
    "test_doc_loc_baseline_freshness_r60",
    "test_archive_defect_log",
    "test_run_root_unittests",
    "test_platform_neutral_paths",
    "test_context_budget_guard",
})

#: `CLASS_LEVEL_DISPATCH_MODULES` 裡「**有**模組層 fixture、但已人工核實安全」
#: 的例外名單——預設假設任何模組層 fixture 都不安全（`Dispatch
#: GranularityWhitelistHasNoModuleLevelFixturesTest` 對非例外成員仍會判紅），
#: 例外需要逐一舉證才能列入。
#:
#: `test_context_budget_guard`：`setUpModule`（`_pin_sentinel_off()`）／
#: `tearDownModule` 只 pin／還原 `os.environ`（`AUTOSDD_SENTINEL_OFF` 與
#: `quota_policy.ENV_SPEC` 全部鍵）＋註冊 `addModuleCleanup`，皆為行程內狀態，
#: 無磁碟／全域資源副作用；細分後每個 class 級 subprocess 各自重跑一次的成本
#: 可忽略（純 dict 讀寫，微秒等級，且每個 subprocess 本就需要自己一份 pin，
#: 重跑不是浪費而是必要）。
_MODULE_FIXTURE_SAFE_EXCEPTIONS: frozenset[str] = frozenset({
    "test_context_budget_guard",
})

#: 第三級派工鍵（`模組.類別.方法`）的人工白名單——`(module, qualname)` 對。本輪
#: （方法級自動細分）刻意留空集合：機制設計上完全依賴執行期自動偵測
#: （見 `auto_method_level_candidates()`），尚未有任何類別被多輪真機驗證後
#: 固化進本表。與 `CLASS_LEVEL_DISPATCH_MODULES` 同一種角色，但目前只有
#: 「自動偵測」這一條生產路徑在用它（作為 `known_classes` 排除既有已知者）。
METHOD_LEVEL_DISPATCH_CLASSES: frozenset[tuple[str, str]] = frozenset()

#: 子行程 `Popen` + 直譯器啟動的固定成本估計值（秒）。方法級細分把一個
#: `module.Class` 派工單位拆成 N 個 `module.Class.method` 子單位，每多開一個
#: 子單位就多付一次這個成本——安全網④（見 `auto_method_level_candidates()`）
#: 用它判斷「拆分後平均每個子單位是否還划算」。
_SUBPROCESS_SPAWN_OVERHEAD_S = 0.5

#: 安全網④門檻＝`_SUBPROCESS_SPAWN_OVERHEAD_S` 的倍數：拆分後平均每個子單位
#: 至少要有 `_SUBPROCESS_SPAWN_OVERHEAD_S * _MIN_METHOD_UNIT_RATIO`（0.5×10=5.0）
#: 秒，細分才值得——低於這個地板寧可不拆，維持 `module.Class` 粒度。
_MIN_METHOD_UNIT_RATIO = 10

#: `method_level_dispatch_enabled()` 讀取的環境變數名。
_ENV_METHOD_LEVEL = "AUTOSDD_DISPATCH_METHOD_LEVEL"


def method_level_dispatch_enabled() -> bool:
    """方法級自動細分（第三級派工鍵）逃生口：`AUTOSDD_DISPATCH_METHOD_LEVEL`
    未設或非 `"0"` → True（預設開啟）。

    五條安全網（見 `auto_method_level_candidates()`）已足夠保守，且在目前
    （W=13）的公平份額下，已知離群類別 `test_archive_defect_log.
    TestMoveSubsetSelectionIsNamedAndTraceable`（166.6s）本身尚未越過
    `detect_imbalance()` 的門檻（`fair_share=183.2s > 166.6s`）——預設開啟對
    現況（尚未拉高 worker 數的機器）幾乎零副作用，只有 worker 數被推高、
    `fair_share` 隨之下降後才會實際觸發細分。
    """
    return os.environ.get(_ENV_METHOD_LEVEL) != "0"


def _module_of(test: unittest.TestCase) -> str:
    """`run_root_unittests._module_of()` 的獨立複本（見檔頭 WHY）。"""
    cls = type(test)
    if cls.__module__ == _PLACEHOLDER_MODULE:
        return str(getattr(test, "_testMethodName", ""))
    return str(cls.__module__)


def dispatch_key(
    test: unittest.TestCase,
    class_level_modules: frozenset[str] | None = None,
    method_level_classes: frozenset[tuple[str, str]] | None = None,
) -> str:
    """細分後的平行派工鍵。預設＝模組名（含 placeholder 特例）；僅
    `class_level_modules`（未傳時＝`CLASS_LEVEL_DISPATCH_MODULES`）白名單內、且非
    placeholder 的模組才改用「模組.類別」，讓已知的單一離群值類別能被其他 worker
    分開派工。再往下一層：`(module, qualname)` 落在 `method_level_classes`
    （未傳時＝`METHOD_LEVEL_DISPATCH_CLASSES`）白名單內時，改用「模組.類別.方法」
    第三級派工鍵（D1：方法級自動細分）。

    🔴 兩個白名單參數皆是 `None` 才在**呼叫當下**查對應的模組層常數（而非把它們
    直接綁進參數預設值）：後者會在函式定義當下就把預設值鎖死，往後
    `mock.patch.object(dispatch_granularity, "CLASS_LEVEL_DISPATCH_MODULES", ...)`
    替換模組屬性時，函式看到的仍是舊物件，讓既有測試的 patch 全部失效。

    安全網：只有「類別是模組的頂層屬性、且 `getattr(module, qualname)` 真的解回
    同一個類別物件」才細分到類別級——巢狀／動態產生的類別（`__qualname__` 含
    `<locals>` 或非頂層屬性）一律退回模組粒度，因為
    `unittest.TestLoader.loadTestsFromName` 無法用字串路徑解析出這類名字
    （fail-closed：解不回去寧可不細分，不猜）。方法級再多一層：只有
    `_testMethodName` 非空字串才細分到方法級，否則退回類別粒度。
    """
    if class_level_modules is None:
        class_level_modules = CLASS_LEVEL_DISPATCH_MODULES
    if method_level_classes is None:
        method_level_classes = METHOD_LEVEL_DISPATCH_CLASSES
    module_name = _module_of(test)
    if module_name not in class_level_modules:
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
    class_key = f"{module_name}.{qualname}"
    if (module_name, qualname) in method_level_classes:
        method_name = getattr(test, "_testMethodName", "")
        if method_name:
            return f"{class_key}.{method_name}"
    return class_key


def suite_dispatch_units(
    tests,
    extra_class_level_modules: frozenset[str] = frozenset(),
    extra_method_level_classes: frozenset[tuple[str, str]] = frozenset(),
) -> dict[str, int]:
    """純函式：回傳「平行派工鍵 -> 測試數」，供 `parallel_shard.run_parallel()`
    消費（見 `dispatch_key()`）。`tests` 為呼叫端已攤平的測試清單
    （`run_root_unittests._flatten(suite)`）。與 `suite_modules()` 差異：本函式
    只決定派工單位，訊息用途一律仍用 `suite_modules()`（不受影響）。

    `extra_class_level_modules` 非空時併入人工白名單（見 `auto_suite_dispatch_units`
    的自動細分候選）；`extra_method_level_classes` 同理併入方法級白名單。兩者
    預設皆空集合＝與呼叫端只傳 `tests` 的既有行為位元級相同。
    """
    effective_modules = (
        CLASS_LEVEL_DISPATCH_MODULES | extra_class_level_modules
        if extra_class_level_modules else None
    )
    effective_methods = (
        METHOD_LEVEL_DISPATCH_CLASSES | extra_method_level_classes
        if extra_method_level_classes else None
    )
    counts: dict[str, int] = {}
    for test in tests:
        key = dispatch_key(test, effective_modules, effective_methods)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _class_has_only_base_fixtures(cls: type) -> bool:
    """True 若 `cls`（含其整條 MRO）未覆寫 `unittest.TestCase` 的
    `setUpClass`／`tearDownClass`，且其所屬模組未定義
    `setUpModule`／`tearDownModule`——方法級自動細分安全網①②的判準本體。

    比對用 `__func__`（`classmethod` 描述器底下的原始函式物件）而非直接比較
    `cls.setUpClass` 這個 bound method 物件本身：每次存取 `cls.setUpClass` 都會
    重新產生一個新的 bound method 包裝物件，用 `__func__` 才是精確表達「比較的
    是函式實作本身，不是誰拿去呼叫它」，且對「祖先類別（非 `TestCase` 本身、
    亦非 `cls` 自己）覆寫過」的情形一樣能正確抓到（MRO 沿途任何一層覆寫，
    `cls.setUpClass.__func__` 都不會是 `unittest.TestCase.setUpClass.__func__`）。

    P0（真機對抗複審發現）：`setUpClass` 若被寫成 `@staticmethod`（而非
    `unittest.TestCase` 預期的 `@classmethod`——stdlib 執行期不強制這件事，
    只要求 `cls.setUpClass()` 可被呼叫），`cls.setUpClass` 解出的是一個**裸
    函式物件**，沒有 `.__func__`（那是 bound method／classmethod 描述器才有的
    屬性）；此前直接取 `.__func__` 會在這裡 `AttributeError`，讓呼叫端
    `auto_method_level_candidates()` 對這一個候選的評估以例外中止、拖垮整個
    候選迴圈（沒有任何 try/except 兜底）。`getattr(fixture, "__func__", None)`
    取不到時視同「已覆寫」，fail-closed 直接排除——語意上這本就不是
    `unittest.TestCase` 預期的形式，排除它不算誤判。
    """
    base = unittest.TestCase
    for name, base_fixture in (
        ("setUpClass", base.setUpClass), ("tearDownClass", base.tearDownClass),
    ):
        fixture = getattr(cls, name)
        func = getattr(fixture, "__func__", None)
        if func is None:
            return False
        if func is not base_fixture.__func__:  # type: ignore[attr-defined]
            return False
    module = sys.modules.get(cls.__module__)
    if module is not None and (
        hasattr(module, "setUpModule") or hasattr(module, "tearDownModule")
    ):
        return False
    return True


def auto_class_level_candidates(
    hints: dict[str, float], worker_count: int,
    known_modules: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """由歷史耗時快取自動算出「這次該額外細分的模組」。沿用
    `dispatch_imbalance.detect_imbalance()` 同一套倍率判準（同一份閾值邏輯只
    有一個家），只保留通過安全網的**模組級**（非 `module.Class`）候選：頂層、
    非 placeholder、且模組本身未定義 `setUpModule`/`tearDownModule`（否則細分
    後每個 class 各自 subprocess 都會重跑一次模組層 fixture，破壞「整檔只跑
    一次」假設）。`known_modules`（現行人工白名單）排除在外——沒有新增的意義。
    模組匯入失敗一律跳過，不強行細分、不崩潰。
    """
    import dispatch_imbalance  # noqa: PLC0415 — 延遲 import：與既有 import 順序解耦
    flagged = dispatch_imbalance.detect_imbalance(hints, worker_count, ratio_threshold=1.0)
    out: set[str] = set()
    for key, _elapsed, _ratio in flagged:
        if "." in key or key == _PLACEHOLDER_MODULE or key in known_modules:
            continue
        try:
            module = importlib.import_module(key)
        except ImportError:
            continue
        if hasattr(module, "setUpModule") or hasattr(module, "tearDownModule"):
            continue
        out.add(key)
    return frozenset(out)


def _method_names_round_trip(
    loader: unittest.TestLoader, module_name: str, qualname: str,
    members: list[unittest.TestCase],
) -> bool:
    """安全網⑤：對候選類別的**每一個**方法，實際呼叫
    `unittest.TestLoader().loadTestsFromName("module.Class.method")`，確認能
    載回**恰好一個** test 且其 `id()` 與預期相符。

    刻意不只信任①的手動 `getattr` 解析「理論上」與 stdlib loader 的解析路徑
    同構——而是真的跑一次 loader，任何載入例外（`ImportError`／
    `AttributeError`／`TypeError`…）或載回數量／id 不符，都讓**整個類別**
    fail-closed 退回 `module.Class` 粒度（寧可不拆，不猜）。呼叫端只在通過
    ①②③④ 之後才會走到這裡，故這裡的 loader 呼叫次數＝候選類別的方法數，
    不會對每一個未被標記的類別都白白付這個成本。
    """
    for test in members:
        expected_id = test.id()
        method_name = str(getattr(test, "_testMethodName", ""))
        if not method_name:
            return False
        name = f"{module_name}.{qualname}.{method_name}"
        try:
            loaded = list(loader.loadTestsFromName(name))
        except Exception:  # noqa: BLE001 — 載入失敗即代表這個名字解不回去，fail-closed
            return False
        if len(loaded) != 1 or loaded[0].id() != expected_id:
            return False
    return True


def auto_method_level_candidates(
    tests: list[unittest.TestCase],
    class_hints: dict[str, float],
    worker_count: int,
    known_classes: frozenset[tuple[str, str]] = frozenset(),
) -> frozenset[tuple[str, str]]:
    """由歷史耗時快取（`module.Class` 級鍵）自動算出這次該再往下細分到方法級
    （第三級派工鍵）的類別（D1：方法級自動細分）。沿用
    `dispatch_imbalance.detect_imbalance()` 同一套倍率判準
    （`ratio_threshold=1.0`：一旦耗時超過公平份額，排程救不了，只能靠細分），
    `class_hints` 的鍵必須已經是 `module.Class` 形式（呼叫端負責在算出
    class-level dispatch units 之後才餵這份 hints，見 `auto_suite_dispatch_units()`）。

    五條安全網（fail-closed，任一條不通過就整個類別不拆，維持 `module.Class`
    粒度）：
    ① 鍵能被解析回一個真實存在、頂層、非 placeholder 的 `(module, qualname)`
       對，且 `getattr(module, qualname)` 解回同一個 `unittest.TestCase` 子類；
    ② `_class_has_only_base_fixtures(cls)` 為 True（無 `setUpClass`／
       `tearDownClass` 覆寫、模組無 `setUpModule`／`tearDownModule`）；
    ③ 該類別在本次 `tests` 中出現的方法數 >= 2；
    ④ `elapsed / 方法數 >= _SUBPROCESS_SPAWN_OVERHEAD_S * _MIN_METHOD_UNIT_RATIO`
       （0.5×10=5.0 秒地板，低於這個划不來）；
    ⑤ 每個 `module.Class.method` 鍵真的能被
       `unittest.TestLoader().loadTestsFromName()` 載回（見
       `_method_names_round_trip()`）。

    `known_classes`（既有已知已被拆分固化的類別）排除在候選之外——沒有新增
    的意義。任何一步解析失敗（模組未匯入、類別非頂層……）一律跳過該候選，
    不強行細分、不崩潰——與 `auto_class_level_candidates()` 同一種 fail-safe
    紀律。

    P0（真機對抗複審發現）：上述五條安全網各自只擋自己判準範圍內「預期得到」
    的失敗形態（回 False／continue），對「判準本身在評估某個候選時意外拋出
    例外」（例如 `_class_has_only_base_fixtures()` 遇到非 classmethod 形式的
    `setUpClass`）沒有兜底——單一候選評估拋例外會讓整個迴圈中止，殃及其餘
    尚未評估的候選、甚至整個 runner。故每個候選的整段評估另包一層
    `try/except Exception: continue`：評估失敗的候選視同「不通過安全網」跳過，
    不影響其餘候選、不崩潰呼叫端。
    """
    import dispatch_imbalance  # noqa: PLC0415 — 延遲 import，理由同 auto_class_level_candidates
    flagged = dispatch_imbalance.detect_imbalance(class_hints, worker_count, ratio_threshold=1.0)
    if not flagged:
        return frozenset()

    class_methods: dict[tuple[str, str], list[unittest.TestCase]] = {}
    for test in tests:
        cls = type(test)
        if cls.__module__ == _PLACEHOLDER_MODULE:
            continue
        qualname = cls.__qualname__
        if "<locals>" in qualname:
            continue
        class_methods.setdefault((cls.__module__, qualname), []).append(test)
    key_to_pair = {
        f"{module_name}.{qualname}": (module_name, qualname)
        for module_name, qualname in class_methods
    }

    loader = unittest.TestLoader()
    out: set[tuple[str, str]] = set()
    for key, elapsed, _ratio in flagged:
        try:
            pair = key_to_pair.get(key)
            if pair is None or pair in known_classes:
                continue
            module_name, qualname = pair
            module = sys.modules.get(module_name)
            cls = getattr(module, qualname, None) if module is not None else None
            if cls is None or not (
                isinstance(cls, type) and issubclass(cls, unittest.TestCase)
            ):
                continue
            if not _class_has_only_base_fixtures(cls):
                continue
            members = class_methods[pair]
            if len(members) < 2:
                continue
            per_method = elapsed / len(members)
            if per_method < _SUBPROCESS_SPAWN_OVERHEAD_S * _MIN_METHOD_UNIT_RATIO:
                continue
            if not _method_names_round_trip(loader, module_name, qualname, members):
                continue
            out.add(pair)
        except Exception:  # noqa: BLE001 — fail-closed 跳過（WHY 見上方 docstring）
            continue
    return frozenset(out)


def auto_suite_dispatch_units(tests, worker_count: int) -> dict[str, int]:
    """`suite_dispatch_units()` 的自動版：先讀計時快取，算出這次除了人工白名單
    外還應該細分的模組／類別，再委派既有函式。快取讀取失敗／無快取由
    `parallel_timing_cache.load_hints()` 自己 fail-safe 回空 dict，此時候選集合
    必為空，`suite_dispatch_units(tests)` 原樣呼叫——與現行（僅人工白名單）行為
    位元級相同，零風險。

    D1：兩層自動偵測串接——① 模組級（`auto_class_level_candidates()`，沿用既有
    行為）先把新發現的離群模組升級成 `module.Class` 派工單位；② 方法級
    （`auto_method_level_candidates()`，本輪新增）再對**這之後**的 `module.Class`
    鍵集合（含既有白名單與①新增者）重新讀一次 hints，偵測是否有類別本身也
    超過當次 `worker_count` 算出的公平份額，若有且通過安全網則再往下細分成
    `module.Class.method`。`method_level_dispatch_enabled()` 為 False 時整個
    ②直接跳過，回傳①的結果（與本輪之前的行為位元級相同）。
    """
    import parallel_timing_cache  # noqa: PLC0415 — 延遲 import，理由同上
    tests = list(tests)
    keys_now = suite_dispatch_units(tests)
    hints = parallel_timing_cache.load_hints(keys_now)
    class_candidates = auto_class_level_candidates(
        hints, worker_count, CLASS_LEVEL_DISPATCH_MODULES)
    if class_candidates:
        keys_now = suite_dispatch_units(tests, extra_class_level_modules=class_candidates)

    if not method_level_dispatch_enabled():
        return keys_now

    class_hints = parallel_timing_cache.load_hints(keys_now)
    method_candidates = auto_method_level_candidates(
        tests, class_hints, worker_count, METHOD_LEVEL_DISPATCH_CLASSES,
    )
    if not method_candidates:
        return keys_now
    keys_now = suite_dispatch_units(
        tests,
        extra_class_level_modules=class_candidates,
        extra_method_level_classes=method_candidates,
    )
    for module_name, qualname in sorted(method_candidates):
        prefix = f"{module_name}.{qualname}."
        n = sum(1 for k in keys_now if k.startswith(prefix))
        print(f"🔬 方法級自動細分：{module_name}.{qualname} 拆成 {n} 個方法級派工單位")
    return keys_now
