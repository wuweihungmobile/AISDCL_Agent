#!/usr/bin/env python3
"""tools/lib/parallel_shard.py — `tools/run_root_unittests.py` 的本機平行執行（opt-in）。

WHY（DEF-200-274，P3）：全套 4000+ 支測試序列跑約 12~13 分鐘，Mac 多核心未被利用。
本模組在 `AUTOSDD_PARALLEL_TESTS=1` 時把 discover 完（尚未 `run()`）的 suite 依**模組**
拆成獨立派工單位，塞進一個共用佇列；最多 `worker_count()` 條 thread 各自不斷認領
佇列裡的下一個模組、自己起**獨立 subprocess** 真跑該模組、自己 `communicate()` 等
結果，再把每個模組印出的一行 JSON 彙總成一個只實作呼叫端所需介面的
`_MergedResult`（動態工作竊取／work-stealing，細節見 `run_parallel()` docstring 的
DEF-200-274 第四輪一節；取代舊版「依測試方法數貪婪裝箱成 N 個固定 shard」的
`weighted_shards()`，已刪除）。預設（未設環境變數）完全不觸碰這條路徑。

為何用 subprocess 而非 `multiprocessing.Pool`：Windows 強制 `spawn`、macOS 3.8+
預設也是 `spawn`——`spawn` 會重新 import 主模組，且傳給 worker 的函式必須是模組層級、
可被 pickle 的（不能傳 `TestSuite`/`TestCase`，也不能用 closure）。獨立 subprocess
呼叫全新直譯器與 CI 既有的行程隔離方式一致，Windows/macOS 語意相同，不吃
spawn/pickle 的坑。

彙總協定：每個模組各自的 subprocess 印一行 JSON 到 stdout：
    {"testsRun": int,
     "skipped"/"errors"/"failures": [[test_id, reason_或_tb, is_fixture], ...],
     "unexpectedSuccesses": [test_id, ...]}
parent 用**自己**discovery 階段（尚未 `run()` 過）的 suite 建 `id -> TestCase` 字典，
把非 fixture 條目重建成 `(真 TestCase 實例, reason/tb)`（天然滿足
`isinstance(test, TestCase)` 與 `test.id()`）；fixture 條目建一個非 `TestCase`、帶
`.description` 的 stub——與 stdlib `unittest.result._ErrorHolder` 同一種可辨識方式。

任一模組的 subprocess 回傳非法 JSON 或非零 exit code：立即 fail-loud，印出該模組名與
完整 stdout/stderr，並在彙總結果的 `errors` 補一筆崩潰條目（讓 `wasSuccessful()`
為 False）而非 `raise SystemExit`——後者會讓 `run_parallel()` 的呼叫方
`sentinel_lifecycle.leak_fence()` 的 `rc = run()` 這一行被例外打斷，使其收尾快照／
洩漏比對整段失靈（DEF-200-274 收尾複審發現，見 `run_parallel()` docstring）。不嘗試
拼出「看起來過得去」的部分報告——崩潰的那個模組涵蓋的測試仍然「沒有跑」，只是這件
事現在由回傳值而非例外來傳達。
"""
from __future__ import annotations

import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

# 🔴 本檔既是被 `run_parallel()` 以 `python <本檔>` 生出的 child target，自己也在
# `run_parallel()` 裡印中文錯誤訊息——兩者都要求 child/entry 端有 UTF-8 stdio 保護
# （同 DEF-101-798 那一族；`tools/tests/test_subprocess_encoding_hygiene.py`）。
# `platform_utils` 與本檔同住 `tools/lib/`，subprocess 直跑時其目錄天然在 sys.path[0]，
# 被 import 時 `run_root_unittests.py` 已把 `tools/lib` 插進 sys.path，兩種情境都找得到。
try:
    from platform_utils import init_utf8_streams  # noqa: PLC0415

    init_utf8_streams()
except Exception:  # noqa: BLE001 — 保護性前置，任何失敗都不得影響本檔功能本身
    pass

_ENV_ON = "AUTOSDD_PARALLEL_TESTS"
_ENV_WORKERS = "AUTOSDD_PARALLEL_TESTS_WORKERS"


def enabled() -> bool:
    """讀 `AUTOSDD_PARALLEL_TESTS` 開關；純函式化以利測試注入。未設或非 "1" 皆為 False。"""
    return os.environ.get(_ENV_ON) == "1"


def worker_count(cpu_count: int | None = None) -> int:
    """`AUTOSDD_PARALLEL_TESTS_WORKERS` 可覆寫；未設時＝`max(1, min(8, cpu-1))`：
    保留一核心給前景，上限 8（subprocess 開銷＋少數大檔主導總時長，切太細邊際效益低）。
    覆寫值非正整數時忽略、退回預設公式（壞掉的旗標不該讓平行模式整支炸掉）。
    """
    override = os.environ.get(_ENV_WORKERS)
    if override:
        try:
            parsed = int(override)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed
    cpu = cpu_count if cpu_count is not None else (os.cpu_count() or 2)
    return max(1, min(8, cpu - 1))


def _flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    out: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            out.extend(_flatten(item))
        else:
            out.append(item)
    return out


class _FixtureStub:
    """非 `TestCase` 的 fixture 層條目 stub（`setUpClass`／`setUpModule` 失敗或 skip）。

    介面逐字比照 stdlib `unittest.suite._ErrorHolder`（`isinstance(x, TestCase)` 為
    False 即可被 `fixture_level_entries` 等呼叫端辨識）：`.id()` 不可少——
    `skip_runtime_report.all_skips()` 對 `result.skipped` 的每一筆一律呼叫
    `test.id()`，序列模式下真的是 `_ErrorHolder`（有 `.id()`），漏掉這個方法會讓
    平行模式在遇到任何 fixture 層 skip／error 時當場 `AttributeError` 崩潰。
    """

    def __init__(self, description: str) -> None:
        self.description = description

    def id(self) -> str:
        return self.description

    def shortDescription(self) -> str | None:
        return None

    def __str__(self) -> str:
        return self.description


class _MergedResult:
    """只實作呼叫端（`run_root_unittests.py` 各 `report_*` 函式）消費的介面。"""

    def __init__(self) -> None:
        self.testsRun = 0
        self.skipped: list[tuple[object, str]] = []
        self.errors: list[tuple[object, str]] = []
        self.failures: list[tuple[object, str]] = []
        self.unexpectedSuccesses: list[object] = []
        #: {模組名: wall-clock 秒數}，供 `report_module_timings()` 消費（第五輪）。
        self.module_timings: dict[str, float] = {}

    def wasSuccessful(self) -> bool:
        return not self.failures and not self.errors and not self.unexpectedSuccesses


def merge_results(
    shard_payloads: list[dict], known_tests_by_id: dict[str, unittest.TestCase]
) -> _MergedResult:
    """純函式：把各 shard 的 JSON payload 彙總成一個 `_MergedResult`。

    非 fixture 條目查 `known_tests_by_id` 重建成真 `TestCase` 實例；查不到（理論上
    不該發生——id 來自 parent 自己 discovery 出的同一棵 suite）時退回 stub 而不吞掉
    這筆，讓「找不到」本身可見而非靜默消失。
    """
    merged = _MergedResult()
    for payload in shard_payloads:
        merged.testsRun += payload["testsRun"]
        for name, bucket in (
            ("skipped", merged.skipped),
            ("errors", merged.errors),
            ("failures", merged.failures),
        ):
            for test_id, reason_or_tb, is_fixture in payload[name]:
                test = _FixtureStub(test_id) if is_fixture else known_tests_by_id.get(test_id)
                bucket.append((test if test is not None else _FixtureStub(test_id), reason_or_tb))
        for test_id in payload["unexpectedSuccesses"]:
            test = known_tests_by_id.get(test_id)
            merged.unexpectedSuccesses.append(test if test is not None else _FixtureStub(test_id))
    return merged


def _entries(bucket) -> list[list[object]]:
    out: list[list[object]] = []
    for test, reason_or_tb in bucket:
        is_fixture = not isinstance(test, unittest.TestCase)
        test_id = str(getattr(test, "description", test)) if is_fixture else test.id()
        out.append([test_id, reason_or_tb, is_fixture])
    return out


def _worker_main(start_dir: str, modules: list[str]) -> int:
    """在獨立 subprocess 內真跑一組模組，把結果序列化成一行 JSON 印到 stdout。

    worker 本身崩潰（未預期例外）＝exit(3)＋`shard_crashed` 旗標；測試失敗但 worker
    活著＝永遠 exit 0，兩者由 `run_parallel` 分開判斷（見該函式）。

    🔴 stdout 是與 parent 之間唯一的協定通道（單行 JSON），而本 repo 有測試會**自己
    spawn 子行程**（`test_pre_push_dispatcher`／`test_bootstrap_core` 等）且不重導向
    其 stdout——那個孫行程直接繼承本 worker 的 OS fd 1，寫進去的任何位元組都會與我們
    自己印的 JSON 那一行混在同一個管線裡（`sys.stdout` 換掉沒有用：那只換 Python 端
    的物件，子行程繼承的是作業系統層級的 fd，實測命中：`merge_results()` 對摻雜行
    `json.loads` 出一個沒有 `testsRun` 鍵的字典而 `KeyError` 崩潰）。故在真正執行
    測試**之前**把 fd 1 導向 devnull、留一份原始 fd 的副本，測試跑完只用那份副本
    寫出協定行——不管測試本身或它的子行程往「stdout」寫了什麼，都進 devnull。
    """
    # 靜態可解析形態（AISDLC_SDD test_ci_paths_cover_root_consumers.py 的
    # _eval_path_expr 要求）：`start_dir` 本身來自 argv、無法靜態解析；但本 worker
    # 在生產路徑上恆被叫來跑 tools/tests（見 run_root_unittests._TESTS_DIR），
    # 故改用可靜態解析的同義表達式，`start_dir` 僅留作跑偏時的 fail-loud 對帳。
    tests_dir = str(Path(__file__).resolve().parents[1] / "tests")
    assert start_dir == tests_dir, (
        f"parallel_shard worker 收到非預期的 start_dir={start_dir!r}"
        f"（預期 {tests_dir!r}）——本 worker 目前只為 tools/tests 設計"
    )
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    protocol_fd = os.dup(1)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 1)
    os.close(devnull_fd)

    def _emit(payload: dict) -> None:
        os.write(protocol_fd, (json.dumps(payload) + "\n").encode("utf-8"))
        os.close(protocol_fd)

    try:
        loader = unittest.TestLoader()
        suite = unittest.TestSuite(loader.loadTestsFromName(m) for m in modules)
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    except BaseException as exc:  # noqa: BLE001 — worker 崩潰須完整回報，故意不窄化
        _emit({"shard_crashed": True, "modules": modules, "tb": repr(exc)})
        return 3
    unexpected = [
        t.id() if hasattr(t, "id") else str(t)
        for t in getattr(result, "unexpectedSuccesses", ())
    ]
    _emit({
        "testsRun": result.testsRun,
        "skipped": _entries(result.skipped),
        "errors": _entries(result.errors),
        "failures": _entries(result.failures),
        "unexpectedSuccesses": unexpected,
    })
    return 0


def _crash_fallback(started: list[subprocess.Popen], exc: BaseException) -> _MergedResult:
    """`run_parallel()` 的收尾共用邏輯：kill 已啟動的孤兒子行程＋印診斷＋把這次崩潰
    包成一筆 `errors` 條目，讓呼叫端讀到的 rc 依然非零而不是把例外拋出去。

    🔴 第四輪第二次對抗式複審 Architect finding 1(a) 收斂：刻意收 `exc: BaseException`（不是
    `Exception`）且**不靠任何 `except` 子句篩選型別就直接呼叫**——見 `run_parallel()`
    docstring〈例外安全網〉一節，worker thread 內部用 `except BaseException` 攔下的
    例外，型別上可能是非 `Exception` 子類的 `SystemExit`／`GeneratorExit`。舊寫法是
    「合成後 `raise`、交外層 `except Exception` 接住」，若 `exc` 剛好是這類非
    `Exception` 子類，`raise` 出去會直接穿透外層的 `except Exception`、逃出
    `run_parallel()`。本函式讓呼叫端在拿到例外物件的當下直接收尾，不經過任何一次
    型別檢查，缺口因此消除。
    """
    for proc in started:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001 — 收尾動作本身不得再拋例外
            pass
    print(
        f"❌ run_parallel() 本身發生未預期例外（非個別模組崩潰，已啟動的子行程已"
        f" kill）：{exc!r}",
        file=sys.stderr,
    )
    fallback = _MergedResult()
    fallback.errors.append((
        _FixtureStub("shard_crash::run_parallel"),
        f"run_parallel() 本身發生未預期例外（非個別模組崩潰，已啟動的子行程已"
        f" kill）：{exc!r}",
    ))
    return fallback


def run_parallel(
    suite: unittest.TestSuite, start_dir: Path, module_counts: dict[str, int]
) -> _MergedResult:
    """discover 完（尚未 `run()`）的 `suite` 依模組動態派工、subprocess 平行真跑後彙總。

    DEF-200-274 第四輪：改用**動態工作竊取**（work-stealing）取代舊版「依測試方法數
    貪婪裝箱成 N 個固定 shard」（`weighted_shards()`，已刪除）。舊版權重＝測試方法數
    （現成、免費，但與真實耗時無關），導致「方法數少但單次耗時極長」的全樹掃描型
    模組（如 `test_doc_loc_baseline_freshness_r60.py`）被誤判成輕量、跟其他模組綁進
    同一個 shard，實測 4-worker 平行幾乎零加速比（見
    `docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`）。新設計把
    每個模組都當成一個獨立派工單位塞進共用佇列，最多 `worker_count()` 條 thread 各自
    不斷認領佇列裡的下一個模組、自己 Popen＋自己 communicate——不管哪個模組實際耗時
    多長，它只會拖累「認領到它的那一條 thread」，其餘 thread 照樣持續消化佇列，總
    耗時趨近 `max(單一最重模組耗時, 總工作量/N)`，不再依賴權重估計準不準。

    任一模組 crash 或印出非法 JSON：立即印出模組名＋完整 stdout/stderr（fail-loud），
    但**不** `raise SystemExit`——改為在回傳的彙總結果裡補一筆 `errors` 條目描述這次
    崩潰，讓 `wasSuccessful()` 因此變 False、呼叫方（`run_with_floor`）讀到的 rc 依然
    非零。改法理由（DEF-200-274 收尾複審發現）：呼叫鏈是
    `sentinel_lifecycle.leak_fence(lambda: run_with_floor(...))`，`leak_fence()` 內
    `rc = run()` 這一行沒有 try/except——`SystemExit` 會直接穿透，讓 `leak_fence()`
    收尾快照／洩漏比對整段沒執行，監控機制反而在「測試套件本身崩潰」這種最需要它的
    情況下失靈。正常 return 讓 `rc = run()` 完整跑完，`leak_fence()` 的收尾邏輯不受
    影響。
    worker 的 `env` 是 `os.environ` 的複本、只拔掉 `AUTOSDD_PARALLEL_TESTS`（其餘一律
    照抄，讓 leak_fence 已 `setdefault` 的 `AUTOSDD_SENTINEL_OFF` 之類變數照常透傳）：
    `tools/tests/test_run_root_unittests.py` 有多支測試會在**自己的行程內**直接呼叫
    `run_with_floor()` 對一棵合成小樹跑（`CollectionIntegrityTest`／`ExecutionGapTest`
    等），若那支測試恰好被分派到某個 worker 裡執行，而 worker 繼承了外層的
    `AUTOSDD_PARALLEL_TESTS=1`，該次呼叫會**遞迴**再開一層 subprocess 平行——對一棵
    只有 1 支模組的合成樹毫無意義，且實測確實讓 `CollectionIntegrityTest.
    test_module_level_skiptest_collapses_module_and_is_named` 當場 rc=1 崩潰。拔掉
    這個變數讓 worker 內的任何遞迴呼叫都乖乖走序列路徑，行為與「不開平行模式」時
    逐字相同。

    🔴 Popen 失敗的**偵測時效**（第四輪動態佇列相對第三輪序列迴圈的非功能性變化，
    Architect 提醒）：第三輪是主 thread 序列 for 迴圈啟動 Popen，任何一次失敗立即
    中止後續 shard 的啟動；第四輪每條 worker thread 各自從共用佇列認領模組，某條
    thread 撞見 Popen 失敗只會讓「那一條 thread」停止，其餘 thread 仍會繼續認領
    佇列、啟動並等待可能長時間執行的子行程，直到所有 thread 都 `join()` 完成後才
    統一浮現這次失敗。最終正確性不受影響（仍會 kill 已啟動的子行程、仍會回報
    失敗），但「多快知道失敗」變慢了——特意記在這裡讓讀者不必自己重新推導。

    🔴 例外安全網（第三輪複審 Problem 2，動態佇列下延伸；第四輪第二次對抗式複審 Architect
    finding 1(a) 再收斂型別缺口）：`merge_results()` 對缺鍵 payload 用中括號直接
    存取（無 `.get()` 防護）會拋 `KeyError`——這類例外並非 `SystemExit`，一樣會
    穿透 `leak_fence()` 的 `rc = run()` 而讓收尾整段失靈，故本函式主體（起
    thread／join／`merge_results`）外層包 `try/except Exception`：任何
    **`Exception` 子類**都會被 `_crash_fallback()` 收攏成一筆 `errors` 條目後正常
    return，維持 `wasSuccessful()`＝False 語意。

    worker thread 內部的例外（如 `Popen()` 失敗）不會自動傳到主 thread，故每條
    thread 用 `except BaseException` 接住後塞進 `thread_errors` 佇列——這裡刻意收
    `BaseException` 而非 `Exception`：worker thread 執行的是使用者程式碼
    （`unittest` runner／`subprocess`），理論上仍可能拋出非 `Exception` 子類的
    `SystemExit`／`GeneratorExit`。主 thread `join()` 完畢後若該佇列非空即**整個
    排空**（見下），直接呼叫 `_crash_fallback(started, combined)` 收尾——**不**經過
    `raise` 再依賴外層 `except Exception` 接住。第四輪初版曾經是「合成後 `raise`、
    交外層 `except Exception` 收」，但若 `collected` 混進非 `Exception` 子類的
    `BaseException`，`raise` 出去會直接穿透外層的 `except Exception`、逃出
    `run_parallel()`，違反上一段自己宣稱的「任何 `Exception` 子類都不可讓
    `leak_fence` 失靈」這個不變量——第四輪第二次對抗式複審 Architect finding 1(a) 點名的正是
    這個型別缺口，改為呼叫端直接拿到例外物件、不靠任何 `except` 子句篩選型別即可
    收尾，缺口因此消除（回歸鎖：`ParallelShardWorkerThreadBaseExceptionDoesNotEscapeTest`，
    用 `SystemExit` 這個非 `Exception` 子類驗證，`OSError` 換不出這個型別缺口）。
    對 `started`（多條 thread 併發寫入、用 `started_lock` 保護）裡已啟動的子行程
    逐一 `kill()`＋`wait()`，避免半途放生的孤兒子行程（`_crash_fallback()` 內完成）。

    🔴 本函式對「main thread 自己被 Ctrl-C 中斷」（`t.join()` 期間收到
    `KeyboardInterrupt`）**不會靜默吞掉、假裝成一筆測試失敗**——最終仍然
    `raise`。第五輪：此前完全不清理就讓它穿透，其餘活著的 worker thread 會繼續
    開新 Popen、且非 daemon thread 卡住直譯器退出；現包一層
    `except KeyboardInterrupt`：立旗標、排空 `pending`、kill 已啟動的子行程、
    等 thread 真的結束，才 `raise`——清理，不吞例外。

    🔴 第四輪對抗式複審 Architect 發現（動態佇列下的新失效面，序列版不可能發生）：
    兩條以上 worker thread 幾乎同時失敗時（例如系統性 Popen 設定錯誤讓多條 thread
    撞見同一種 OSError），此前只用 `thread_errors.get_nowait()` 取**第一筆**就
    `raise`，其餘例外物件永遠留在佇列裡、從未被 drain、也從未被印出——診斷資訊
    真的遺失，違反本檔案通篇的 fail-loud 紀律。修法：join 完後把 `thread_errors`
    整個排空，逐筆印到 stderr（不遺漏任何一筆），只有一筆時保留原始例外型別、兩筆
    以上合成一個 `RuntimeError` 把全部 `repr()` 串在訊息裡，交給 `_crash_fallback()`
    統一寫進最終的 `errors` 條目，讓「看得到幾筆失敗」這件事不必再靠猜。
    """
    known_tests_by_id = {t.id(): t for t in _flatten(suite)}
    # 排序純粹是「疑似最重先派」的啟發式（縮短 tail latency），不影響正確性——
    # work-stealing 的負載平衡保證不依賴這個猜測準不準。
    modules_sorted = sorted(module_counts, key=lambda m: (-module_counts[m], m))
    pending: queue.Queue[str] = queue.Queue()
    for module in modules_sorted:
        pending.put(module)

    child_env = dict(os.environ)
    child_env.pop(_ENV_ON, None)

    started: list[subprocess.Popen] = []
    started_lock = threading.Lock()
    results: queue.SimpleQueue = queue.SimpleQueue()
    thread_errors: queue.SimpleQueue = queue.SimpleQueue()
    #: Ctrl-C 收尾用（見下方 `except KeyboardInterrupt`）；平常路徑恆為 False。
    stop_event = threading.Event()

    def _worker_thread_loop() -> None:
        try:
            while True:
                try:
                    module = pending.get_nowait()
                except queue.Empty:
                    return
                if stop_event.is_set():
                    return
                proc = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), str(start_dir), module],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    encoding="utf-8", errors="replace", env=child_env,
                )
                with started_lock:
                    started.append(proc)
                # Popen 與 communicate 在同一條 thread 內緊接著呼叫，兩者之間沒有
                # 「先把全部 process 開好、再排隊處理」的視窗——這正是 stderr
                # backpressure 修復的關鍵性質（每個活著的子行程恆有專屬 thread
                # 正在排空它的 pipe），比舊版「先併發開好全部 Popen、事後才配
                # thread 平行 communicate」的兩階段模式更直接。
                started_at = time.monotonic()
                stdout, stderr = proc.communicate()
                elapsed = time.monotonic() - started_at
                results.put((module, proc.returncode, stdout, stderr, elapsed))
        except BaseException as exc:  # noqa: BLE001 — 蒐集後交主 thread 直接收尾，故意不窄化
            thread_errors.put(exc)

    try:
        n = min(worker_count(), len(modules_sorted)) or 1
        threads = [threading.Thread(target=_worker_thread_loop) for _ in range(n)]
        for t in threads:
            t.start()
        try:
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            # 清理後 re-raise（不吞例外）：立旗標阻新 Popen→排空 pending→kill 已
            # 啟動的子行程→等 thread 真的結束。窄殘留窗見 docstring 上方一節。
            stop_event.set()
            while True:
                try:
                    pending.get_nowait()
                except queue.Empty:
                    break
            with started_lock:
                snapshot = list(started)
            for proc in snapshot:
                try:
                    proc.kill()
                    proc.wait(timeout=5)
                except Exception:  # noqa: BLE001 — 收尾動作本身不得再拋例外
                    pass
            for t in threads:
                t.join()
            raise
        if not thread_errors.empty():
            collected: list[BaseException] = []
            while not thread_errors.empty():
                collected.append(thread_errors.get_nowait())
            for exc in collected:
                print(f"❌ worker thread 未預期例外（已收集，見下方合併結果）：{exc!r}",
                      file=sys.stderr)
            combined: BaseException = (
                collected[0] if len(collected) == 1
                else RuntimeError(
                    f"{len(collected)} 條 worker thread 同時發生未預期例外："
                    + "；".join(repr(exc) for exc in collected)
                )
            )
            with started_lock:
                started_snapshot = list(started)
            return _crash_fallback(started_snapshot, combined)

        payloads: list[dict] = []
        crashes: list[tuple[str, int, str, str]] = []
        module_timings: dict[str, float] = {}
        while not results.empty():
            module, rc, stdout, stderr, elapsed = results.get_nowait()
            module_timings[module] = elapsed
            parsed = None
            if rc == 0 and stdout.strip():
                try:
                    parsed = json.loads(stdout.strip().splitlines()[-1])
                except json.JSONDecodeError:
                    parsed = None
            if parsed is None or parsed.get("shard_crashed"):
                print(f"❌ 平行分片失敗（模組：{module}，rc={rc}）：", file=sys.stderr)
                print(f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}", file=sys.stderr)
                crashes.append((module, rc, stdout, stderr))
                continue
            payloads.append(parsed)
        merged = merge_results(payloads, known_tests_by_id)
        merged.module_timings = module_timings
        for module, rc, stdout, stderr in crashes:
            reason = (
                f"平行分片崩潰（模組：{module}，rc={rc}）\n"
                f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
            )
            merged.errors.append((_FixtureStub(f"shard_crash::{module}"), reason))
        return merged
    except Exception as exc:  # noqa: BLE001 — 見上方 docstring：任何 Exception 子類都不得穿透 leak_fence
        # `_crash_fallback()` 逐一 kill `started` 時不持鎖，傳入前先在鎖下拍照（第五輪）。
        with started_lock:
            started_snapshot = list(started)
        return _crash_fallback(started_snapshot, exc)


if __name__ == "__main__":
    sys.exit(_worker_main(sys.argv[1], sys.argv[2:]))
