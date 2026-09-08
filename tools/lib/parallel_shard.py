#!/usr/bin/env python3
"""tools/lib/parallel_shard.py — `tools/run_root_unittests.py` 的本機平行執行（opt-in）。

WHY（DEF-200-274，P3）：全套 4000+ 支測試序列跑約 12~13 分鐘，Mac 多核心未被利用。
本模組在 `AUTOSDD_PARALLEL_TESTS=1` 時把 discover 完（尚未 `run()`）的 suite 依模組
切成 N 份，各自用**獨立 subprocess** 真跑，再把每個 shard 印出的一行 JSON 彙總成一個
只實作呼叫端所需介面的 `_MergedResult`。預設（未設環境變數）完全不觸碰這條路徑。

為何用 subprocess 而非 `multiprocessing.Pool`：Windows 強制 `spawn`、macOS 3.8+
預設也是 `spawn`——`spawn` 會重新 import 主模組，且傳給 worker 的函式必須是模組層級、
可被 pickle 的（不能傳 `TestSuite`/`TestCase`，也不能用 closure）。獨立 subprocess
呼叫全新直譯器與 CI 既有的行程隔離方式一致，Windows/macOS 語意相同，不吃
spawn/pickle 的坑。

彙總協定：每個 shard 印一行 JSON 到 stdout：
    {"testsRun": int,
     "skipped"/"errors"/"failures": [[test_id, reason_或_tb, is_fixture], ...],
     "unexpectedSuccesses": [test_id, ...]}
parent 用**自己**discovery 階段（尚未 `run()` 過）的 suite 建 `id -> TestCase` 字典，
把非 fixture 條目重建成 `(真 TestCase 實例, reason/tb)`（天然滿足
`isinstance(test, TestCase)` 與 `test.id()`）；fixture 條目建一個非 `TestCase`、帶
`.description` 的 stub——與 stdlib `unittest.result._ErrorHolder` 同一種可辨識方式。

任一 shard 回傳非法 JSON 或非零 exit code：立即 fail-loud，印出該 shard 的模組清單與
完整 stdout/stderr，並在彙總結果的 `errors` 補一筆崩潰條目（讓 `wasSuccessful()`
為 False）而非 `raise SystemExit`——後者會讓 `run_parallel()` 的呼叫方
`sentinel_lifecycle.leak_fence()` 的 `rc = run()` 這一行被例外打斷，使其收尾快照／
洩漏比對整段失靈（DEF-200-274 收尾複審發現，見 `run_parallel()` docstring）。不嘗試
用其餘 shard 拼出「看起來過得去」的部分報告——崩潰的那個 shard 涵蓋的測試仍然
「沒有跑」，只是這件事現在由回傳值而非例外來傳達。
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
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


def weighted_shards(module_counts: dict[str, int], n: int) -> list[list[str]]:
    """Greedy LPT：模組依測試數（現成權重，免費）由重到輕塞進當下最輕的 bin。純函式。"""
    shards: list[list[str]] = [[] for _ in range(max(1, n))]
    loads = [0] * len(shards)
    for module, count in sorted(module_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        i = loads.index(min(loads))
        shards[i].append(module)
        loads[i] += count
    return [shard for shard in shards if shard]


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
    if start_dir not in sys.path:
        sys.path.insert(0, start_dir)
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


def run_parallel(
    suite: unittest.TestSuite, start_dir: Path, module_counts: dict[str, int]
) -> _MergedResult:
    """discover 完（尚未 `run()`）的 `suite` 依模組切 N 份，subprocess 平行真跑後彙總。

    任一 shard crash 或印出非法 JSON：立即印出該 shard 模組清單＋完整 stdout/stderr
    （fail-loud），但**不再** `raise SystemExit`——改為在回傳的彙總結果裡補一筆
    `errors` 條目描述這次崩潰，讓 `wasSuccessful()` 因此變 False、呼叫方（
    `run_with_floor`）讀到的 rc 依然非零。改法理由（DEF-200-274 收尾複審發現）：
    呼叫鏈是 `sentinel_lifecycle.leak_fence(lambda: run_with_floor(...))`，
    `leak_fence()` 內 `rc = run()` 這一行沒有 try/except——`SystemExit` 會直接
    穿透，讓 `leak_fence()` 收尾快照／洩漏比對整段沒執行，監控機制反而在「測試
    套件本身崩潰」這種最需要它的情況下失靈。正常 return 讓 `rc = run()` 完整
    跑完，`leak_fence()` 的收尾邏輯不受影響。
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
    """
    known_tests_by_id = {t.id(): t for t in _flatten(suite)}
    shards = weighted_shards(module_counts, worker_count())
    child_env = dict(os.environ)
    child_env.pop(_ENV_ON, None)
    procs = [
        (shard, subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), str(start_dir), *shard],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", env=child_env,
        ))
        for shard in shards
    ]
    payloads: list[dict] = []
    crashes: list[tuple[list[str], int, str, str]] = []
    for shard, proc in procs:
        stdout, stderr = proc.communicate()
        parsed = None
        if proc.returncode == 0 and stdout.strip():
            try:
                parsed = json.loads(stdout.strip().splitlines()[-1])
            except json.JSONDecodeError:
                parsed = None
        if parsed is None or parsed.get("shard_crashed"):
            print(
                f"❌ 平行分片失敗（模組：{', '.join(shard)}，rc={proc.returncode}）：",
                file=sys.stderr,
            )
            print(f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}", file=sys.stderr)
            crashes.append((shard, proc.returncode, stdout, stderr))
            continue
        payloads.append(parsed)
    merged = merge_results(payloads, known_tests_by_id)
    for shard, rc, stdout, stderr in crashes:
        reason = (
            f"平行分片崩潰（模組：{', '.join(shard)}，rc={rc}）\n"
            f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
        )
        merged.errors.append((_FixtureStub(f"shard_crash::{','.join(shard)}"), reason))
    return merged


if __name__ == "__main__":
    sys.exit(_worker_main(sys.argv[1], sys.argv[2:]))
