"""引擎行程樹的資源取樣（契約 v1.3 §3.1.2；D-12；US-M-10）。

背景執行緒每 5 秒對每個「引擎行程樹存活」的 run 取一次樣本，只留最近一筆。行程樹＝`python -m
autoclaude` 與它的全部子孫（含 claude 或 mock claude），不含 Bridge 自己、也不含別的 run。
請求路徑（`GET /autoclaude/runs/{id}`）只讀那一筆：從不取樣、不阻塞。樣本超過 15 秒沒更新就當
它不存在——取樣器卡住或掛掉時，寧可回 null，也不回過期的數字。

🔴 陷阱：`Process.cpu_percent(interval=None)` 是「與**同一個 Process 物件**上一次呼叫之間」的差值。
`Process.children()` 每次都回新物件，所以 `TreeSampler` 跨 tick 持有每個 pid 的物件（以 pid＋
create_time 判斷是不是同一個行程，pid 被重用就換新物件），重建物件＝每次都是第一筆＝CPU 永遠 0.0。
新出現的行程第一筆 CPU 為 0.0 屬預期。

`cpu_percent` 是整機正規化：行程樹各行程 cpu_percent 的總和 ÷ 邏輯核心數，夾在 0～100、四捨五入到
小數 1 位（100＝整台機器所有邏輯核心被占滿；與 top 的單核 100% 不同）。`rss_bytes` 是各行程 RSS
的總和（共用頁會重複計入，所以是上界估計）。`process_count` 是取樣成功的行程數（含根）。
`resources` 不含 pid、命令列、環境變數。

Windows 行為＝只走 psutil（不用 os.kill、不讀 /proc）；用 venv 的 python.exe 啟動的行程會多一層
啟動器殼（兩個直譯器對應 4 個行程），所以 process_count 比直覺大，測試只能斷言下界。
"""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psutil

logger = logging.getLogger("bridge.resources")

#: 契約 §3.1.2：取樣間隔 5 秒；最近一筆超過 15 秒沒更新＝過期（回 null）。
SAMPLE_INTERVAL_SECONDS = 5.0
STALE_AFTER_SECONDS = 15.0
#: 取樣器自己的例外只記 log，同一個地方最多每 60 秒一行（5 秒一輪，不然會洗版）。
_LOG_EVERY_SECONDS = 60.0
#: 單一行程取不到（剛結束、權限不足、殭屍）只略過它，不讓整筆樣本失敗。
_PER_PROCESS_ERRORS = (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ResourceSample:
    cpu_percent: float
    rss_bytes: int
    process_count: int
    sampled_at: str          # ISO-8601，一律 UTC（`+00:00`），與 Bridge 其他時間戳一致

    def as_dict(self) -> dict[str, Any]:
        return {"cpu_percent": self.cpu_percent, "rss_bytes": self.rss_bytes,
                "process_count": self.process_count, "sampled_at": self.sampled_at}


class TreeSampler:
    """單一行程樹（以根 pid 為準）的取樣器：跨 tick 持有每個 pid 的 `Process` 物件。"""

    def __init__(self, root_pid: int, *, cpu_count: int | None = None,
                 process_factory: Callable[[int], Any] = psutil.Process,
                 wall_clock: Callable[[], datetime] = _utc_now):
        self.root_pid = root_pid
        self._factory = process_factory
        self._wall_clock = wall_clock
        # 取不到邏輯核心數時視為 1（契約 §3.1.2）。
        self._cpus = max(1, cpu_count or psutil.cpu_count(logical=True) or 1)
        self._root: Any | None = None
        self._held: dict[int, Any] = {}          # pid → 同一個 Process 物件（跨 tick 持有）
        #: 根行程已結束（或根本不存在）。一旦為 True 就不復活：之後同一個 pid 若又出現，是別的行程
        #: （pid 被重用或 run 重新 spawn），由 ResourceSampler 換一個新的 TreeSampler 去接。
        self.dead = False

    def _root_process(self) -> Any | None:
        if self.dead:
            return None
        if self._root is None:
            try:
                self._root = self._factory(self.root_pid)
            except psutil.Error:
                return self._bury()
            self._held[self._root.pid] = self._root
        try:
            if self._root.is_running():          # 內含 create_time 比對：pid 被重用就是 False
                return self._root
        except psutil.Error:
            pass
        return self._bury()

    def _bury(self) -> None:
        self.dead = True
        self._root = None
        self._held.clear()
        return None

    def sample(self) -> ResourceSample | None:
        """取一筆樣本；根不存活或整棵樹都取不到＝None（契約：行程樹不存活）。"""
        root = self._root_process()
        if root is None:
            return None
        try:
            descendants = root.children(recursive=True)
        except _PER_PROCESS_ERRORS:              # 列舉子孫失敗不可連根都不取樣
            descendants = []
        held: dict[int, Any] = {}
        total_cpu = 0.0
        total_rss = 0
        counted = 0
        for found in [root, *descendants]:
            # children() 回的永遠是新物件：只有「同一個行程」才沿用先前持有的那個，否則 cpu_percent
            # 的基準會被丟掉。`==` 比 pid＋create_time（pid 被重用就不相等）。
            known = self._held.get(found.pid)
            current = known if known is not None and known == found else found
            try:
                cpu = current.cpu_percent(interval=None)
                rss = int(current.memory_info().rss)
            except _PER_PROCESS_ERRORS:
                continue                         # 兩項都讀到才計入，免得 CPU 算進去、行程數卻沒算
            total_cpu += cpu
            total_rss += rss
            held[found.pid] = current
            counted += 1
        self._held = held                        # 已消失的 pid 就此丟掉
        if counted == 0:
            return None
        cpu = round(min(100.0, max(0.0, total_cpu / self._cpus)), 1)
        return ResourceSample(cpu, total_rss, counted, self._wall_clock().isoformat())


class ResourceSampler:
    """背景取樣器：每 `interval` 秒對 `targets()` 回報的每個 run 取一筆樣本，只留最近一筆。

    `targets()`＝{run_id: 引擎根 pid}（只含引擎行程樹存活的 run；由 RunManager 提供）。
    `latest()` 是請求路徑唯一會碰的函式：讀一個 dict、不取樣、不碰行程。
    """

    def __init__(self, targets: Callable[[], Mapping[str, int]], *,
                 interval: float | None = None, stale_after: float | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 tree_factory: Callable[[int], TreeSampler] = TreeSampler):
        self._targets = targets
        self._interval = SAMPLE_INTERVAL_SECONDS if interval is None else interval
        self._stale_after = STALE_AFTER_SECONDS if stale_after is None else stale_after
        self._clock = clock
        self._tree_factory = tree_factory
        self._lock = threading.Lock()            # 保護 _latest（請求路徑與取樣執行緒共用）
        self._tick_lock = threading.Lock()       # 讓 tick 一次只有一個在跑（_trees 只在 tick 內動）
        self._trees: dict[str, TreeSampler] = {}
        self._latest: dict[str, tuple[int, float, ResourceSample]] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._last_log = float("-inf")

    # ── 請求路徑 ─────────────────────────────────────────────────────────────
    def latest(self, run_id: str, root_pid: int) -> dict[str, Any] | None:
        """最近一筆樣本；根 pid 對不上（run 重新 spawn 過）或已過期＝None。"""
        with self._lock:
            entry = self._latest.get(run_id)
        if entry is None:
            return None
        pid, taken, sample = entry
        if pid != root_pid or self._clock() - taken > self._stale_after:
            return None
        return sample.as_dict()

    # ── 取樣 ─────────────────────────────────────────────────────────────────
    def tick(self, *, new_only: bool = False) -> None:
        """同步取一輪樣本。`new_only`＝只補還沒有取樣器的 run（spawn 後立刻補一筆，CPU 為
        0.0），不去動既有 run 的基準。"""
        with self._tick_lock:
            targets = dict(self._targets())
            if not new_only:
                for run_id in [r for r in self._trees if r not in targets]:
                    del self._trees[run_id]      # 暫停、終態、已結束：不再持有它的 Process 物件
                    with self._lock:
                        self._latest.pop(run_id, None)
            for run_id, pid in targets.items():
                tree = self._trees.get(run_id)
                if tree is not None and tree.root_pid == pid and not tree.dead:
                    if new_only:
                        continue
                else:       # 新 run、重新 spawn（根 pid 變了），或舊樹的根已死而 pid 又被重用
                    tree = self._trees[run_id] = self._tree_factory(pid)
                try:
                    sample = tree.sample()
                except Exception as exc:         # noqa: BLE001 — 取樣器的任何例外都不得外洩
                    self._log_failure(run_id, exc)
                    sample = None
                with self._lock:
                    if sample is None:
                        self._latest.pop(run_id, None)
                    else:
                        self._latest[run_id] = (pid, self._clock(), sample)

    def _log_failure(self, run_id: str, exc: Exception) -> None:
        now = self._clock()
        if now - self._last_log >= _LOG_EVERY_SECONDS:
            self._last_log = now
            # 只記例外的類別：psutil 例外的訊息帶行程名稱，這裡不需要也不想把它寫進日誌。
            logger.warning("資源取樣失敗（run=%s）：%s", run_id, type(exc).__name__)

    # ── 背景執行緒 ───────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="bridge-resources")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=5)

    def request_sample(self) -> None:
        """新 spawn 的 run 要求立刻補一筆（只喚醒執行緒，不在呼叫端的執行緒取樣、不阻塞）。"""
        self._wake.set()

    def _safe_tick(self, *, new_only: bool) -> None:
        try:
            self.tick(new_only=new_only)
        except Exception as exc:                 # noqa: BLE001 — targets() 等取樣器自己的例外
            self._log_failure("*", exc)

    def _run(self) -> None:
        next_full = self._clock()                # 第一輪立刻做
        while not self._stop.is_set():
            woken = self._wake.wait(timeout=max(0.0, next_full - self._clock()))
            if self._stop.is_set():
                break
            if woken:
                self._wake.clear()
                self._safe_tick(new_only=True)   # 不重設 next_full：連續 spawn 不能餓死整輪取樣
            else:
                self._safe_tick(new_only=False)
                next_full = self._clock() + self._interval
