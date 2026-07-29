#!/usr/bin/env python3
"""tools/tests 全套 unittest 執行器（含測試數量下限釘選）— R10 QA-2（DEF-101-127）。

為何存在：`python -m unittest discover` 對「發現 0 個測試」回 rc=0
（`Ran 0 tests ... OK`，Python 3.11 實測）。tools/tests/ 目錄改名、測試檔改名
不符 `test_*.py`、或 `-s` 路徑打錯 → 全部回歸鎖同時靜默消失，而四處 gate
（pre-push root-infra leg、root-infra-ci step 8、windows/macos smoke）依然全綠、
無任何 diff 訊號。R9 已給 parity 抽取加 `_MIN_EXTRACT_COUNTS` 下限釘選，同構
風險在 unittest 這裡原本沒有對等防護。

行為：discover 後先斷言 countTestCases() >= MIN_TESTS 再執行；低於下限 exit 1
（測試根本不跑——數量崩塌本身就是失敗）。刻意刪減測試時須同步下修 MIN_TESTS
（比照 check_script_parity._MIN_EXTRACT_COUNTS 的紅燈指路慣例）。

R60 Pkg-P8 補三層——因為「下限」語意只擋得住「掉太多」，擋不住「悄悄少幾支而總數
仍在下限之上」（實測當時 916 支 vs 下限 845 ⇒ 可靜默蒸發 71 支仍印 ✅）：
  ① `inventory_fingerprint`：把「這個數字是哪一份磁碟狀態產生的」一起印出來，
     讓兩次數字不同時能當場分辨「樹變了」還是「同一棵樹量到不同數字」。
  ② `collection_gaps`：斷言磁碟上每支 test_*.py 都至少貢獻一支測試（集合比對，
     不是總數比大小），並把 discovery 佔位測試（`_FailedTest`／`ModuleSkipped`）
     點名成硬失敗——後者原本 rc 仍為 0，是真的 fail-open。
  ③ `report_execution_gap`：比較**收集數**與**實際執行數**。`setUpClass` 拋
     SkipTest 會讓整個類別一支都不跑而 `countTestCases()` 完全不變，下限守門
     結構性看不到（實測：收集 11／執行 2／rc=0）。

呼叫端（取代裸 `python -m unittest discover -s tools/tests`）：
  tools/git-hooks/pre-push（root-infra leg ②）、.github/workflows/root-infra-ci.yml
  step 8、windows-compat-ci.yml、macos-compat-ci.yml 對應 step。

使用：python tools/run_root_unittests.py（repo 內任意 cwd；路徑以本檔自身定位）
測試：tools/tests/test_run_root_unittests.py
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_TESTS_DIR = Path(__file__).resolve().parent / "tests"

# 下限釘選：低於此數＝測試大規模靜默消失（目錄/pattern/路徑壞掉），紅燈。
# 刻意刪減測試時同步下修；新增測試在 `RATCHET_STALE_RATIO` 倍以內不需動（下限
# 語意），超過即**必須**重釘，否則保鮮期斷言會讓閘門變紅（見下方兩層設計說明）。
MIN_TESTS = 1069  # R60 round 3 **主控收輪重釘**（R59 為 661、R57 為 616；R60 中途曾釘 756、845、994、1063——994 是 round 3 修復波開跑前的值，1063 是 Pkg-F 交件時的值而 Pkg-H 之後又淨增 6 支，兩者都在「還有包在跑」的時點量測，故皆非最終值）。R58 整輪作廢故無 R58 值。R57 收尾重釘（動工前為 R15 釘的 290，對當時實況 530 已鑑別力失效 45%＝可靜默蒸發 240 支仍綠）。本值由主控在**所有並行修復包與四方複審 agent 全部停工後**，於最終工作樹實跑 `python3 tools/run_root_unittests.py` 取其印出的「發現 N 個測試」直接填入，不做任何加減推算——R57 過程中兩度用算式推得 552／558，兩次都當場就與實況不符（SD-R57-01／QA-R57-07 抓出），故本行的重釘判準明定為「填實測值」

# R57 修正：「人工 ratchet」本身就是缺陷來源——R15 釘完後連續 11 輪沒人重釘，
# 下限與實況愈拉愈開、鑑別力單調衰減，而且**沒有任何訊號**提醒該重釘（下限語意
# 天生只在往下掉時說話）。故設**兩層**、且刻意用**不同**門檻：
#   ① WARN 層（本檔 `warn_ratchet_drift`，只印不擋）：實況 > 下限 × 1.10 即在
#      終端印一行「該重釘了」。這一層才是真正的「只 WARN 不 fail」。
#   ② 保鮮期層（`tools/tests/test_run_root_unittests.py::
#      test_current_pin_is_not_already_stale`，會讓閘門變紅）：實況 > 下限 ×
#      1.25 即 FAIL。純 WARN 擋不住「11 輪沒人重釘」的心理機制（常亮的警告＝
#      背景噪音），必須有一道會紅的線。
# 兩層門檻必須不同，否則 WARN 一響就等於閘門已紅，①的存在毫無意義——R57
# round 1（ARCH-06）實測 `ratchet_drift_message(698, 558)` 非 None ⇒ 當時單一
# 1.25 門檻下「只 WARN 不 fail」的註解與行為互相打臉。現行設計給的是 [1.10,
# 1.25] 這段緩衝：先被提醒、還沒被擋，收輪時順手重釘即可。
# 代價（明說）：累積新增超過 MIN_TESTS × 0.25 支測試就**必須**重釘，這是刻意
# 承受的維護負擔，換到的是下限不會再腐化 11 輪。
RATCHET_WARN_RATIO = 1.10
RATCHET_STALE_RATIO = 1.25

# R43 Architect P1（DEF-101-348 方向①）：DEF-101-343~345 揪出 5 支 Windows 專屬
# 回歸測試連續 5+ 輪「全 APPROVE」卻從未在原生 Windows 上真正跑過——`unittest`
# 預設摘要（`skipped=N`）不區分「一般性 skip」與「這支測試的驗證價值僅在原生
# Windows 上成立、這次環境不符沒跑」，是造成該漏洞連續多輪未被發現的根因之一。
# 凡 skip 理由帶此標籤的測試，於摘要末另印一段醒目清單，供複審者一眼辨識。
WINDOWS_NATIVE_SKIP_TAG = "[WINDOWS-NATIVE-ONLY]"


_PATTERN = "test_*.py"

# discovery 佔位測試（`_FailedTest`／`ModuleSkipped`）都是在 `unittest.loader`
# 裡動態造出來的類別，用 `__module__` 即可與真實測試模組區分。
_PLACEHOLDER_MODULE = "unittest.loader"

# 具名例外：磁碟上符合 `_PATTERN` 但**合法**不貢獻任何測試的檔案。
# 現況為空集合（R60 實測 53 支 `test_*.py` 每支都至少貢獻 1 支測試）。刻意保留這個
# 空常數而非省略：例外必須**逐檔具名並附理由**，不接受「整批略過」的通用開關——
# 那等於把缺口洗掉。註：helper 檔（`_ci_scan_anchors.py`／`_platform_helpers.py`／
# `_ps_engine.py`）不符 `test_*.py`，本來就不在收集面內，無需列名。
_COLLECTION_EXEMPT: frozenset[str] = frozenset()


def discover_suite(start_dir: Path) -> unittest.TestSuite:
    # 每次新建 TestLoader：defaultTestLoader 有狀態（_top_level_dir 殘留），
    # 同進程第二次對不同目錄 discover 會炸 "Start directory is not importable"。
    return unittest.TestLoader().discover(str(start_dir), pattern=_PATTERN)


def inventory_fingerprint(start_dir: Path, pattern: str = _PATTERN) -> tuple[int, str]:
    """回傳 `(檔數, 指紋)`；指紋＝`(檔名, 位元組大小)` 排序後 sha256 前 12 碼。

    WHY（R60 Pkg-P8 主修，對症的是**真正**的根因）：本 runner 印出的「發現 N 個
    測試」過去是**不可跨次比較**的裸數字——它沒有記錄「這個 N 是由哪一份磁碟狀態
    產生的」。R60 並行修復期間三次量測分別得到 894／906／916，被當成「並行負載下
    收集數不決定性」立案追查；實際上三者是 865 ＋ {29, 41, 51}——865 是另外 52 支
    檔的固定貢獻，{29, 41, 51} 則是**同一支** `test_check_defect_log_crossref.py`
    被另一個並行包從 29 支逐步擴充到 51 支的三個時間切片（29 支＝該檔
    `git show HEAD:` 版本實測值）。沒有任何一次是 race，缺的 12 支從來不存在。
    印出指紋後，兩次數字不同時可**當場**分辨「樹變了」與「同一棵樹量到不同數字」
    ——只有後者才是真的非決定性、才值得追。成本＝一行輸出。
    """
    rows = sorted((p.name, p.stat().st_size) for p in start_dir.glob(pattern))
    blob = "\n".join(f"{name}:{size}" for name, size in rows)
    return len(rows), hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    out: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            out.extend(_flatten(item))
        else:
            out.append(item)
    return out


def _module_of(test: unittest.TestCase) -> str:
    cls = type(test)
    if cls.__module__ == _PLACEHOLDER_MODULE:
        # 佔位測試把「原本該被載入的模組名」放在方法名上（`_FailedTest(name, …)`）。
        return str(getattr(test, "_testMethodName", ""))
    return str(cls.__module__)


def suite_modules(suite: unittest.TestSuite) -> dict[str, int]:
    """純函式（無 I/O 副作用）：回傳 `模組名 -> 該模組被收集到的測試數`。"""
    counts: dict[str, int] = {}
    for test in _flatten(suite):
        name = _module_of(test)
        counts[name] = counts.get(name, 0) + 1
    return counts


def collection_gaps(
    suite: unittest.TestSuite,
    start_dir: Path,
    pattern: str = _PATTERN,
    exempt: frozenset[str] = _COLLECTION_EXEMPT,
) -> list[str]:
    """純函式：磁碟上符合 `pattern` 卻**一支測試都沒被收集到**的檔名（去 exempt）。

    WHY：`MIN_TESTS` 是**下限**語意，只擋「掉太多」，擋不住「悄悄少收幾支而總數
    仍在下限之上」——R60 當下實況 916 支 vs 下限 845 ⇒ **可靜默蒸發 71 支仍印 ✅**，
    且沒被收集的測試不會出現在 `skipped=N`、不會出現在 `report_all_skips` 明細、
    不會出現在任何一行輸出裡（它從來沒被 loader 交給 runner）。

    而 `unittest` discovery 確實有一條**完全靜默**的丟檔路徑（Python 3.11.9 實查
    `unittest/loader.py::TestLoader._find_test_path`）：`os.path.isfile()` 與
    `os.path.isdir()` 皆為 False 時走結尾的 `else: return None, False`——不拋例外、
    不進 `loader.errors`、不印任何東西。而 `os.path.isfile()` 內部
    `except (OSError, ValueError): return False` 會把 stat 失敗吞成「不是檔案」；
    `_find_tests()` 又只在開頭做一次 `sorted(os.listdir())` 之後才逐檔 import，
    故「listdir 已看到、輪到它時檔案不在了」的窗口 ≈ 整段 discovery 時長。
    （本包實測**排除**兩個曾被懷疑的觸發條件：另一行程持 exclusive handle
    `dwShareMode=0`、以及 delete-pending `FILE_FLAG_DELETE_ON_CLOSE`，兩者
    `os.path.isfile()` 皆仍回 True——Windows 對 `FILE_READ_ATTRIBUTES` 永不衝突。
    只有「該瞬間檔案真的不在」才會觸發。）

    故本層改成**集合比對**「磁碟每支 test_*.py 是否都至少貢獻一支測試」，抓的是
    「有檔沒被收到」而非「總數掉太多」，鑑別力與 `MIN_TESTS` 正交。
    """
    on_disk = {p.stem for p in start_dir.glob(pattern)}
    return sorted(on_disk - set(suite_modules(suite)) - exempt)


def discovery_placeholders(suite: unittest.TestSuite) -> list[tuple[str, str]]:
    """純函式：回傳 `(模組名, 佔位類別名)`——被 discovery 換成佔位測試的模組。

    兩種佔位都會讓「一支檔的 N 支測試塌成 1 支」，計數靜默 -(N-1)：
      `_FailedTest`（import 失敗）——執行時必紅，但**計數**的塌陷無聲；
      `ModuleSkipped`（模組層 `raise SkipTest`）——**rc 仍為 0**，該模組整份覆蓋
      無聲消失，是真正的 fail-open。
    兩者都不該混在總數裡看不見，故一律點名並讓 rc 為 1。
    """
    out = [
        (_module_of(t), type(t).__name__)
        for t in _flatten(suite)
        if type(t).__module__ == _PLACEHOLDER_MODULE
    ]
    return sorted(out)


def fixture_level_entries(result: unittest.TestResult) -> list[str]:
    """純函式：回傳 class／module 層 fixture（`setUpClass`／`setUpModule`）產生的條目。

    `unittest` 用 `_ErrorHolder` 承載這類條目，而它**不是** `TestCase` 子類，故以
    `isinstance(..., unittest.TestCase)` 為 False 即可辨識，無需 import 私有名稱。
    """
    out: list[str] = []
    for bucket in (result.skipped, result.errors, result.failures):
        for entry in bucket:
            test = entry[0]
            if not isinstance(test, unittest.TestCase):
                out.append(str(getattr(test, "description", test)))
    return sorted(out)


def report_execution_gap(collected: int, result: unittest.TestResult) -> int:
    """印出「收集到」與「真正執行」的差額；回傳差額（為 0 時完全靜音）。

    WHY（R60 Pkg-P8，本包最重的發現）：`MIN_TESTS`／ratchet 守的是
    `countTestCases()`＝**收集數**，但真正跑了幾支是 `result.testsRun`，而
    **這兩個數字可以差很多，且原本沒有任何一處比較它們**。

    機制（Python 3.11.9 實查 `unittest/suite.py::TestSuite.run`）：`setUpClass`／
    `setUpModule` 失敗或 `raise SkipTest` 時，`_handleClassSetUp` 設下
    `_classSetupFailed`／`_moduleSetUpFailed`，接著 `run` 對該類別每一支測試走
    `continue`——`test(result)` **根本沒被呼叫**，故 `testsRun` 完全不增加，而
    `countTestCases()` 早在 discovery 時就把它們算進去了。

    實測（沙箱，9 支方法 + setUpClass 拋 SkipTest）：收集 11／執行 2／未執行 9，
    `result.skipped` 只多**一筆** `setUpClass (…)`，`wasSuccessful()` 仍為 True
    ⇒ **rc=0**。也就是說整個類別的覆蓋可以無聲消失，而下限守門結構性看不到
    （它守的數字沒變），`skipped=N` 也只多 1、完全不提「這一筆吃掉了 9 支」。
    對照：方法層 skip（`@skipUnless`）**會**計入 `testsRun`（`TestCase.run` 先
    `startTest()` 才判 skip），所以只有 fixture 層會造成這個差額。
    本 repo 現正使用該模式（`test_macos_smoke_skip_honesty.TestSummaryTailRealRun.
    setUpClass` 在找不到 bash 時 `raise SkipTest`），故這不是理論風險。

    設計取捨：**不**把差額一律判紅——上述環境條件式整類 skip 是本 repo 刻意採用的
    合法模式，一律判紅會在缺工具的機器上製造假紅。改為「差額必須被點名、且必須有
    fixture 層條目可歸因」，把判斷交給讀者；無法歸因的差額（例如 `result.stop()`
    中途中止）才判紅。這與 DEF-101-510「不得只印計數」同一精神，只是把它從 skip
    維度延伸到**執行**維度。
    """
    gap = collected - result.testsRun
    if gap > 0:
        print(
            f"⚠️  收集 {collected} 支、實際執行 {result.testsRun} 支——有 {gap} 支"
            f"**從未被執行**（下限守門看的是收集數，結構性抓不到這件事）。"
            f"可歸因的 class／module 層 fixture 條目："
        )
        for description in fixture_level_entries(result) or ["（無——差額無法歸因）"]:
            print(f"   - {description}")
    return gap


def report_collection_gaps(gaps: list[str], start_dir: Path) -> None:
    if gaps:
        print(
            f"❌ 收集面完整性失敗：{start_dir} 底下有 {len(gaps)} 支 {_PATTERN} "
            f"檔案一支測試都沒被收集到——這類「有檔沒被收到」不會出現在總數下限、"
            f"不會出現在 skipped 明細、不會出現在任何輸出裡（見 collection_gaps "
            f"docstring 的 stdlib 靜默丟檔路徑）：",
            file=sys.stderr,
        )
        for name in gaps:
            print(f"   - {name}.py", file=sys.stderr)
        print(
            "   若某支檔案確實刻意不含任何測試，請把它**具名**加入 "
            "run_root_unittests._COLLECTION_EXEMPT 並註明理由。",
            file=sys.stderr,
        )


def report_discovery_placeholders(suite: unittest.TestSuite) -> list[tuple[str, str]]:
    placeholders = discovery_placeholders(suite)
    if placeholders:
        print(
            f"❌ discovery 佔位測試 {len(placeholders)} 筆：下列模組的測試**沒有**"
            f"被真正載入，整份覆蓋塌成一支佔位測試（計數靜默減少）：",
            file=sys.stderr,
        )
        for module, kind in placeholders:
            print(f"   - {module}（{kind}）", file=sys.stderr)
    return placeholders


def run_with_floor(start_dir: Path, min_tests: int) -> int:
    """discover → 數量下限守門 → 收集面完整性守門 → 執行；回傳 exit code。"""
    suite = discover_suite(start_dir)
    count = suite.countTestCases()
    if count < min_tests:
        print(
            f"❌ unittest 數量下限釘選失敗：{start_dir} 只發現 {count} 個測試 "
            f"< 下限 {min_tests}——測試疑似大規模靜默消失（目錄改名/pattern 不符/"
            f"路徑錯）；若為刻意刪減請同步下修 MIN_TESTS",
            file=sys.stderr,
        )
        return 1
    print(f"✅ unittest 數量下限釘選通過：發現 {count} 個測試（下限 {min_tests}）")
    nfiles, fingerprint = inventory_fingerprint(start_dir)
    print(
        f"🧾 收集面盤存：{nfiles} 支 {_PATTERN} 檔／指紋 {fingerprint}"
        f"（跨次數字可比較用，見 inventory_fingerprint docstring）"
    )
    gaps = collection_gaps(suite, start_dir)
    if gaps:
        report_collection_gaps(gaps, start_dir)
        return 1  # 量測本身已不可信，fail-closed：不放行、也不假裝跑完
    placeholders = report_discovery_placeholders(suite)
    warn_ratchet_drift(count, min_tests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    report_windows_native_skips(result)
    report_all_skips(result)
    # 無法歸因的「收集了卻沒執行」＝量測不完整（例如 result.stop() 中途中止）。
    # 可歸因者（fixture 層 skip／error）只點名不判紅，理由見 report_execution_gap。
    unexplained_gap = report_execution_gap(count, result) > 0 and not fixture_level_entries(result)
    if not result.wasSuccessful():
        dump_failure_detail(result)
    # 佔位測試刻意**不**提早 return：讓 suite 照跑，`_FailedTest` 才會把真正的
    # ImportError traceback 交給 `dump_failure_detail` 落檔（提早 return 會丟掉
    # 唯一的診斷資訊）；rc 則在此與 `wasSuccessful()` 一起收斂。
    return 0 if (result.wasSuccessful() and not placeholders and not unexplained_gap) else 1


def ratchet_drift_message(
    count: int, min_tests: int, ratio: float = RATCHET_WARN_RATIO
) -> str | None:
    """純函式（無 I/O 副作用，比照 `windows_native_skips` 慣例）：實況相對下限
    漂移超過 `ratio` 倍時回傳提醒字串，否則 None。R57 新增，WHY 見
    `RATCHET_WARN_RATIO`。`ratio` 參數化是為了讓兩層共用同一段判定與訊息：
    runner 用預設的 WARN 倍數，保鮮期斷言傳 `RATCHET_STALE_RATIO`。"""
    if count <= min_tests * ratio:
        return None
    return (
        f"⚠️  測試數量下限已過期：實況 {count} 個 > 下限 {min_tests} × "
        f"{ratio}——下限的鑑別力只剩「可靜默蒸發 {count - min_tests} "
        f"個測試仍不紅」，請把 tools/run_root_unittests.py 的 MIN_TESTS 重釘為 {count}"
    )


def warn_ratchet_drift(count: int, min_tests: int) -> str | None:
    msg = ratchet_drift_message(count, min_tests)
    if msg is not None:
        print(msg)
    return msg


# R57 round 3 ARCH-R57R3-03：Architect 獨立重跑本 runner 14 次，其中 **1 次**出現
# `Ran 610 tests / FAILED (failures=4, skipped=4)`，其餘 13 次全綠；三種針對性重現
# （連跑 6 次／兩實例並行／8 顆 CPU 燒滿）皆未重現，而**本 runner 不保留失敗細節**，
# 該次的失敗測試名隨 process 消失，故無法歸因。方向為 fail-closed（假紅、不放行缺陷），
# 但「下次再發生仍然無法診斷」本身是可以現在就消除的缺口。
# 落檔而非改判邏輯：不動 rc、不動任何斷言，只在已經要回 1 的路徑上多寫一份明細。
_FAILURE_LOG = Path(__file__).resolve().parent / ".last_failure.log"


def dump_failure_detail(result: unittest.TestResult, path: Path | None = None) -> Path:
    """把失敗/錯誤的 test id 與 traceback 落檔，供下次非決定性翻紅時定位。

    只在 `wasSuccessful()` 為 False 時被呼叫。回傳寫入的路徑（測試用）。
    寫檔失敗不得影響 runner 的 rc——診斷輔助不應反過來變成新的失敗來源。
    """
    target = path or _FAILURE_LOG
    # R57 round 4 SA-R57R4-01：`wasSuccessful()` 在 `unexpectedSuccesses` 非空時
    # 也回 False，原版只讀 failures/errors ⇒ 該模式下 rc=1 卻落一份**不指名任何
    # 測試的空明細**，正是本機制立意要消除的「無法歸因」狀態（實測產出僅 60 bytes
    # 的 `（0 failures / 0 errors）` 標頭）。三個 bucket 一併納入。
    unexpected = list(getattr(result, "unexpectedSuccesses", ()) or ())
    lines = [f"# run_root_unittests 失敗明細（{len(result.failures)} failures / "
             f"{len(result.errors)} errors / {len(unexpected)} unexpected successes）"]
    for label, bucket in (("FAIL", result.failures), ("ERROR", result.errors)):
        for test, tb in bucket:
            lines.append(f"\n===== {label}: {test.id()} =====\n{tb}")
    for test in unexpected:
        # unexpectedSuccesses 沒有 traceback，只有測試本身（標了 expectedFailure 卻通過）
        tid = test.id() if hasattr(test, "id") else str(test)
        lines.append(f"\n===== UNEXPECTED SUCCESS: {tid} =====\n"
                     "（標記 expectedFailure 但實際通過——該缺陷可能已修好，請移除標記）")
    return _write_failure_log(target, "\n".join(lines))


def _write_failure_log(target: Path, body: str) -> Path:
    """落檔並回報。與 `dump_failure_detail` 分離＝比照本檔 `windows_native_skips`／
    `report_windows_native_skips` 的既有慣例（R57 round 4 SA-R57R4-02／QA-R57R4-02：
    print 副作用寫在被單元測試直接呼叫的函式內，會讓每次**全綠**執行的終端輸出混入
    fixture 產生的落檔訊息與 ⚠️ 警告，混淆複審者對「本次是否真有失敗」的判讀——與
    R43 二審 SA 對 `windows_native_skips` 揪出的問題同型）。"""
    try:
        target.write_text(body, encoding="utf-8")
        print(f"🔍 失敗明細已落檔：{target}（供非決定性翻紅時定位，見 DEF-101-499）")
    except OSError as exc:  # 診斷輔助失敗不得升級為 runner 失敗
        print(f"⚠️  失敗明細落檔失敗（{exc}）——不影響 rc", file=sys.stderr)
    return target


def windows_native_skips(result: unittest.TestResult) -> list[str]:
    """純函式（無 I/O 副作用）：從 `result.skipped` 篩出帶 `[WINDOWS-NATIVE-ONLY]`
    標籤者，回傳測試 id 清單。與 `report_windows_native_skips` 分離（R43 二審 SA
    複查揪出：原本印出副作用寫在同一函式內，導致 `test_run_root_unittests.py::
    ReportWindowsNativeSkipsTest` 自測時直接呼叫它，會把 fixture 用的假測試 id
    也印到 `python tools/run_root_unittests.py` 的真實終端輸出裡，混淆複審者
    對「本次是否真有 Windows 專屬測試未驗證」的判讀——測試應只斷言回傳值，不該
    觸發生產端的列印副作用）。"""
    tagged = [test for test, reason in result.skipped if WINDOWS_NATIVE_SKIP_TAG in reason]
    return [test.id() for test in tagged]


def report_windows_native_skips(result: unittest.TestResult) -> list[str]:
    """在一般 `skipped=N` 摘要之外，另印出「僅原生 Windows 上才具驗證價值」
    的 skip 清單（DEF-101-348 方向①）；回傳被標記的測試 id 清單。"""
    tagged_ids = windows_native_skips(result)
    if tagged_ids:
        print(
            f"⚠️  {len(tagged_ids)} 個 Windows 專屬測試本次「未在原生 Windows 環境驗證」"
            f"（非一般 skip，見 DEF-101-348/R43）："
        )
        for test_id in tagged_ids:
            print(f"   - {test_id}")
    return tagged_ids


def all_skips(result: unittest.TestResult) -> list[tuple[str, str]]:
    """純函式（無 I/O 副作用，比照 `windows_native_skips` 慣例）：回傳本次全部
    skip 的 `(test_id, reason)`，含已被 `WINDOWS_NATIVE_SKIP_TAG` 標記者。"""
    return [(test.id(), reason) for test, reason in result.skipped]


def report_all_skips(result: unittest.TestResult) -> list[tuple[str, str]]:
    """印出本次**全部** skip 的 id 與理由。

    WHY（DEF-101-510，R59 於真 Windows 11 實機量到）：`report_windows_native_skips`
    只照亮**一個方向**——「這支測試只在原生 Windows 才有驗證價值，這次環境不符」。
    反方向（**因為我們正跑在 Windows，所以失去了某些覆蓋**）完全沒有標籤、沒有摘要、
    沒有計數，只會併進 `unittest` 預設的 `skipped=N` 一個數字裡。R59 實測：本 runner
    在 Windows 11 上 `skipped=11`，**11 支全部無標籤**，其中兩支是真正的覆蓋損失而非
    平台語意使然——
      ① `test_install_windows_nightly` 的語法解析因本機無 pwsh 7 而 skip（DEF-101-509，
         一支 Windows 專屬腳本的語法閘門恰在 Windows 上不跑），
      ② `test_env_changed_removes_cache_dir_and_symlink` 因無 symlink 權限
         （`[WinError 1314]`，標準未提權 Windows 11 的預設狀態）而 skip。
    這正是 DEF-101-343~345 那條「Windows 專屬測試連續 5+ 輪全 APPROVE 卻從未真的在
    Windows 跑過」的缺陷類別，只是方向相反；R43 只補了一半。

    設計取捨（刻意選最笨的做法）：不再發明第二套標籤分類（那需要為每一支 skip 判定
    「by-design 平台語意」vs「環境降級」，判準本身就會成為新的漂移來源），改為**全部
    印出來**，把分類交給讀取者。成本是每輪多 N 行輸出（實測 11 行），換到的是
    「任何 skip 都不可能再隱形」——與紀律 #2「log 必須含完整統計，不信任預設 dump」
    同一精神，也等於把 pytest `-rs` 早就免費提供的東西補進這個 unittest runner。
    """
    entries = all_skips(result)
    if entries:
        tagged = set(windows_native_skips(result))
        print(f"ℹ️  本次 skip 明細（共 {len(entries)} 支；DEF-101-510 要求全列不得只印計數）：")
        for test_id, reason in entries:
            mark = "[已標籤]" if test_id in tagged else "[未標籤]"
            print(f"   - {mark} {test_id}\n       理由：{reason}")
    return entries


def main() -> int:
    if not _TESTS_DIR.is_dir():
        print(f"❌ 測試目錄不存在：{_TESTS_DIR}", file=sys.stderr)
        return 1
    return run_with_floor(_TESTS_DIR, MIN_TESTS)


if __name__ == "__main__":
    sys.exit(main())
