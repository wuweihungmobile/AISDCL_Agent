"""引擎行程樹的資源取樣（契約 v1.3 §3.1.2；D-12；US-M-10）。

三層：
  ① TreeSampler 對「假行程世界」的單元測試——最重要的一條是「跨 tick 持有同一個 Process 物件」：
     psutil 的 `cpu_percent(interval=None)` 是與同一個物件上一次呼叫的差值，而 `children()`
     每次又回新物件，取樣器若每輪重建物件，CPU 就永遠是 0.0。假世界照這個語意實作，
     重建物件的退化會直接測紅。
  ② 同一批語意對**真的** psutil 行程各驗一次（繁忙的子行程 CPU 要大於 0；已消失的 pid 不炸）。
  ③ ResourceSampler（過期門檻、換 pid、停止追蹤、背景執行緒）與經真 HTTP 的 E2E
     （含 PAUSED 與終態）。
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

import psutil
import pytest

import app.resources as resources_module
from app import procutil
from app.resources import ResourceSample, ResourceSampler, TreeSampler
from app.runstate import RunPaths, RunRecord, save_record
from tests.conftest import TERMINAL

_CONTRACT_KEYS = {"cpu_percent", "rss_bytes", "process_count", "sampled_at"}
_FIXED_NOW = datetime(2026, 10, 16, 3, 21, 45, 123456, tzinfo=UTC)


# ── ① 假行程世界（照 psutil 的語意：children() 回新物件、cpu_percent 以「物件」為基準）──────────
class _Mem(NamedTuple):
    rss: int


class _State:
    def __init__(self, ppid: int, *, busy: float, rss: int, create_time: float) -> None:
        self.ppid = ppid
        self.busy = busy                  # 之後每次 cpu_percent 回報的值（第一次呼叫恆為 0.0）
        self.rss = rss
        self.create_time = create_time
        self.cpu_error: Exception | None = None
        self.mem_error: Exception | None = None


class FakeWorld:
    def __init__(self) -> None:
        self.states: dict[int, _State] = {}
        self.children_error: Exception | None = None
        self.constructed: list[int] = []            # process() 被呼叫的 pid（只有根會走這條）

    def spawn(self, pid: int, ppid: int = 0, *, busy: float = 0.0, rss: int = 1000,
              create_time: float = 1.0) -> None:
        self.states[pid] = _State(ppid, busy=busy, rss=rss, create_time=create_time)

    def kill(self, pid: int) -> None:
        self.states.pop(pid, None)

    def process(self, pid: int) -> FakeProc:
        self.constructed.append(pid)
        if pid not in self.states:
            raise psutil.NoSuchProcess(pid)
        return FakeProc(self, pid)

    def descendants(self, pid: int) -> list[int]:
        found: list[int] = []
        for child, state in self.states.items():
            if state.ppid == pid:
                found += [child, *self.descendants(child)]
        return found


class FakeProc:
    def __init__(self, world: FakeWorld, pid: int) -> None:
        self._world = world
        self.pid = pid
        self._create_time = world.states[pid].create_time     # 與 psutil 一樣：建構時就記下
        self._cpu_calls = 0

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, FakeProc)
                and (self.pid, self._create_time) == (other.pid, other._create_time))

    def __hash__(self) -> int:
        return hash((self.pid, self._create_time))

    def _state(self) -> _State:
        state = self._world.states.get(self.pid)
        if state is None or state.create_time != self._create_time:
            raise psutil.NoSuchProcess(self.pid)
        return state

    def is_running(self) -> bool:
        state = self._world.states.get(self.pid)
        return state is not None and state.create_time == self._create_time

    def children(self, recursive: bool = False) -> list[FakeProc]:
        self._state()
        if self._world.children_error is not None:
            raise self._world.children_error
        return [FakeProc(self._world, pid) for pid in self._world.descendants(self.pid)]

    def cpu_percent(self, interval: float | None = None) -> float:
        state = self._state()
        if state.cpu_error is not None:
            raise state.cpu_error
        self._cpu_calls += 1
        return 0.0 if self._cpu_calls == 1 else state.busy

    def memory_info(self) -> _Mem:
        state = self._state()
        if state.mem_error is not None:
            raise state.mem_error
        return _Mem(state.rss)


def _tree(world: FakeWorld, root: int = 100, *, cpus: int = 4) -> TreeSampler:
    return TreeSampler(root, cpu_count=cpus, process_factory=world.process,
                       wall_clock=lambda: _FIXED_NOW)


def _two_process_world() -> FakeWorld:
    world = FakeWorld()
    world.spawn(100, busy=60.0, rss=5000)
    world.spawn(101, ppid=100, busy=40.0, rss=3000)
    return world


def _sample(tree: TreeSampler) -> ResourceSample:
    sample = tree.sample()
    assert sample is not None
    return sample


def test_cpu_comes_from_the_same_process_objects_across_ticks() -> None:
    """🔴 契約 §3.1.2 的陷阱：children() 每次回新物件；取樣器若每輪重建，第二筆也是 0.0。"""
    tree = _tree(_two_process_world())
    first = _sample(tree)
    assert first.cpu_percent == 0.0, "每個物件的第一筆 CPU 是 0.0（基準）"
    second = _sample(tree)
    assert second.cpu_percent == (60.0 + 40.0) / 4, "第二筆必須吃到兩個『被持有的』物件的差值"
    assert (second.rss_bytes, second.process_count) == (8000, 2)
    assert _sample(tree).cpu_percent == 25.0


def test_the_root_object_is_built_once_not_every_tick() -> None:
    world = _two_process_world()
    tree = _tree(world)
    for _ in range(4):
        _sample(tree)
    assert world.constructed == [100], "根的 Process 物件只建一次、之後一直持有"


def test_a_new_child_starts_from_zero_while_old_processes_keep_their_baseline() -> None:
    world = FakeWorld()
    world.spawn(100, busy=60.0)
    tree = _tree(world)
    _sample(tree)
    assert _sample(tree).cpu_percent == 15.0                    # 只有根：60 ÷ 4
    world.spawn(101, ppid=100, busy=40.0)
    assert _sample(tree).cpu_percent == 15.0, "新出現的行程第一筆 CPU 是 0.0（契約：可接受）"
    assert _sample(tree).cpu_percent == 25.0


def test_a_pid_reused_with_another_create_time_is_treated_as_a_new_process() -> None:
    world = _two_process_world()
    tree = _tree(world)
    _sample(tree)
    assert _sample(tree).cpu_percent == 25.0
    world.kill(101)
    world.spawn(101, ppid=100, busy=40.0, create_time=2.0)      # 同 pid、另一個行程
    assert _sample(tree).cpu_percent == 15.0, "不能沿用舊行程的基準（那會算出垃圾）"
    assert _sample(tree).cpu_percent == 25.0


def test_processes_that_vanish_or_cannot_be_read_are_skipped_not_fatal() -> None:
    world = _two_process_world()
    world.spawn(102, ppid=100, busy=10.0, rss=700)
    world.spawn(103, ppid=100, busy=10.0, rss=700)
    world.states[102].cpu_error = psutil.NoSuchProcess(102)     # 列舉後、取樣前消失
    world.states[103].mem_error = psutil.AccessDenied(103)
    tree = _tree(world)
    _sample(tree)
    sample = _sample(tree)
    assert sample.process_count == 2, "取不到的行程不計入（契約：只略過該行程，不讓整筆失敗）"
    assert sample.rss_bytes == 8000 and sample.cpu_percent == 25.0


def test_a_failing_descendant_listing_still_samples_the_root() -> None:
    world = _two_process_world()
    world.children_error = psutil.AccessDenied(100)
    tree = _tree(world)
    _sample(tree)
    sample = _sample(tree)
    assert (sample.process_count, sample.rss_bytes, sample.cpu_percent) == (1, 5000, 15.0)


def test_a_tree_where_nothing_can_be_read_is_none() -> None:
    world = _two_process_world()
    for state in world.states.values():
        state.cpu_error = psutil.AccessDenied(1)
    assert _tree(world).sample() is None, "全部取不到＝引擎行程樹不存活（契約）→ resources 為 null"


def test_a_root_that_is_gone_or_never_existed_is_none_and_stays_none() -> None:
    world = _two_process_world()
    tree = _tree(world)
    _sample(tree)
    world.kill(100)
    assert tree.sample() is None
    world.spawn(100, busy=99.0, create_time=5.0)                # pid 被別的行程重用
    assert tree.sample() is None, "根已死就是死了：重用同一個 pid 的陌生行程不是我們的引擎"
    assert _tree(FakeWorld(), root=4242).sample() is None


def test_cpu_is_normalised_by_logical_cores_clamped_and_rounded_to_one_decimal() -> None:
    world = FakeWorld()
    world.spawn(100, busy=400.0)
    tree = _tree(world, cpus=2)
    _sample(tree)
    assert _sample(tree).cpu_percent == 100.0, "夾在 100：多執行緒行程的原始值可超過 100×核心數"
    fractional = FakeWorld()
    fractional.spawn(100, busy=33.37)
    tree = _tree(fractional, cpus=4)
    _sample(tree)
    assert _sample(tree).cpu_percent == 8.3, "33.37 ÷ 4＝8.3425 → 小數 1 位"


def test_an_unknown_logical_core_count_is_treated_as_one(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: None)
    world = FakeWorld()
    world.spawn(100, busy=33.37)
    tree = TreeSampler(100, process_factory=world.process, wall_clock=lambda: _FIXED_NOW)
    _sample(tree)
    assert _sample(tree).cpu_percent == 33.4, "取不到核心數時視為 1（契約 §3.1.2），不得除以零"


def test_the_sample_dict_has_exactly_the_contract_fields_and_a_utc_timestamp() -> None:
    tree = _tree(_two_process_world())
    _sample(tree)
    body = _sample(tree).as_dict()
    assert set(body) == _CONTRACT_KEYS, "不含 pid、命令列、環境變數"
    assert isinstance(body["cpu_percent"], float) and isinstance(body["rss_bytes"], int)
    assert isinstance(body["process_count"], int)
    assert body["sampled_at"] == "2026-10-16T03:21:45.123456+00:00"
    assert datetime.fromisoformat(body["sampled_at"]).utcoffset() == timedelta(0)


# ── ② 對真的 psutil 行程各驗一次 ─────────────────────────────────────────────────────
_PARENT_WITH_CHILD = (
    "import subprocess, sys, time\n"
    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
    "print(child.pid, flush=True)\n"
    "time.sleep(60)\n")
_BUSY = "while True:\n    pass\n"


def _kill_tree(proc: subprocess.Popen[Any]) -> None:
    """整棵樹都收掉（Windows 的 venv 啟動器會多一層殼：只殺根會留下繁忙的孫行程）。"""
    victims = procutil.begin_terminate(proc.pid)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    procutil.force_kill(procutil.survivors(victims, exclude_pid=proc.pid))


def test_a_real_process_tree_is_sampled_with_the_contract_types() -> None:
    parent = subprocess.Popen([sys.executable, "-c", _PARENT_WITH_CHILD], stdout=subprocess.PIPE,
                              text=True, **procutil.popen_platform_kwargs())
    try:
        assert parent.stdout is not None
        child_pid = int(parent.stdout.readline())
        sample = TreeSampler(parent.pid).sample()
        assert sample is not None
        assert isinstance(sample.cpu_percent, float) and 0.0 <= sample.cpu_percent <= 100.0
        assert isinstance(sample.rss_bytes, int) and sample.rss_bytes > 0
        # 下界而不是精確值：Windows 的 venv 啟動器會讓兩個直譯器對應 4 個行程（契約 §3.1.2）。
        assert isinstance(sample.process_count, int) and sample.process_count >= 2
        assert psutil.pid_exists(child_pid)
        stamp = datetime.fromisoformat(sample.sampled_at)
        assert stamp.utcoffset() == timedelta(0)
        assert abs((datetime.now(UTC) - stamp).total_seconds()) < 30
    finally:
        _kill_tree(parent)


def test_a_busy_real_process_shows_cpu_on_the_second_tick_because_objects_are_held() -> None:
    busy = subprocess.Popen([sys.executable, "-c", _BUSY], **procutil.popen_platform_kwargs())
    try:
        tree = TreeSampler(busy.pid)
        seen: list[float] = []
        for _ in range(8):
            sample = tree.sample()
            assert sample is not None
            seen.append(sample.cpu_percent)
            if len(seen) > 1 and sample.cpu_percent > 0.0:
                break
            time.sleep(0.8)
        # 第一筆一定是 0.0（基準）。繁忙的那個行程可能在第一筆之後才被啟動器 spawn 出來
        # （Windows 的 venv 殼），它自己的第一筆也是 0.0，所以給它幾輪：只要物件被持有，
        # 後面某一筆必定 > 0；若取樣器每輪重建物件，每一筆都會是 0.0。
        # 滿載的單執行緒行程只占整機的 1/核心數，所以只有幾 %。
        assert seen[0] == 0.0
        assert any(c > 0.0 for c in seen[1:]), seen
        assert all(0.0 <= c <= 100.0 for c in seen)
    finally:
        _kill_tree(busy)


def test_a_real_pid_that_is_already_gone_does_not_blow_up() -> None:
    done = subprocess.Popen([sys.executable, "-c", "pass"])
    done.wait()
    assert TreeSampler(done.pid).sample() is None
    assert TreeSampler(2**22 + 12345).sample() is None            # 不存在的 pid


def test_a_real_tree_whose_root_exits_between_ticks_becomes_none() -> None:
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                               **procutil.popen_platform_kwargs())
    tree = TreeSampler(sleeper.pid)
    try:
        assert tree.sample() is not None
    finally:
        _kill_tree(sleeper)
    assert tree.sample() is None


# ── ③ ResourceSampler：過期、換 pid、停止追蹤、背景執行緒 ────────────────────────────────
class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class FakeTree:
    """`ResourceSampler` 要的最小介面：`root_pid` 與 `sample()`。"""

    def __init__(self, pid: int, *, cpu: float = 1.0) -> None:
        self.root_pid = pid
        self.cpu = cpu
        self.calls = 0
        self.dead = False

    def sample(self) -> ResourceSample | None:
        self.calls += 1
        return ResourceSample(self.cpu, 10_000, 3, _FIXED_NOW.isoformat())


def _fake_tree(pid: int) -> Any:
    return FakeTree(pid)


def _sampler(targets: dict[str, int], clock: FakeClock, *,
             trees: list[FakeTree] | None = None) -> ResourceSampler:
    def factory(pid: int) -> Any:
        tree = FakeTree(pid)
        if trees is not None:
            trees.append(tree)
        return tree

    return ResourceSampler(lambda: dict(targets), clock=clock, tree_factory=factory)


def test_there_is_no_sample_until_the_first_tick() -> None:
    sampler = _sampler({"run-1": 10}, FakeClock())
    assert sampler.latest("run-1", 10) is None, "還沒有第一筆樣本＝null"


def test_the_latest_sample_is_served_for_15_seconds_then_it_is_null() -> None:
    clock = FakeClock(1000.0)
    sampler = _sampler({"run-1": 10}, clock)
    sampler.tick()
    served = sampler.latest("run-1", 10)
    assert served is not None and set(served) == _CONTRACT_KEYS
    clock.now = 1015.0
    assert sampler.latest("run-1", 10) is not None, "剛好 15 秒仍新鮮（契約：超過 15 秒才過期）"
    clock.now = 1015.1
    assert sampler.latest("run-1", 10) is None, "取樣器卡住時寧可回 null，也不回過期的數字"
    sampler.tick()                                               # 取樣器恢復
    assert sampler.latest("run-1", 10) is not None


def test_a_sample_of_an_earlier_engine_process_is_never_served_for_a_respawned_run() -> None:
    clock = FakeClock()
    targets = {"run-1": 10}
    trees: list[FakeTree] = []
    sampler = _sampler(targets, clock, trees=trees)
    sampler.tick()
    assert sampler.latest("run-1", 10) is not None
    assert sampler.latest("run-1", 11) is None, "resume 後根 pid 變了：舊樣本不屬於新行程"
    targets["run-1"] = 11
    sampler.tick()
    assert [t.root_pid for t in trees] == [10, 11], "根 pid 變了就換一個新的取樣器（舊物件丟掉）"
    assert sampler.latest("run-1", 11) is not None and sampler.latest("run-1", 10) is None


def test_a_run_whose_engine_stops_loses_its_sample_and_its_held_objects() -> None:
    """PAUSED、終態、剛結束：`targets()` 不再列它 → 樣本與持有的 Process 物件都丟掉。"""
    targets = {"run-1": 10, "run-2": 20}
    sampler = _sampler(targets, FakeClock())
    sampler.tick()
    del targets["run-1"]
    sampler.tick()
    assert sampler.latest("run-1", 10) is None
    assert sampler.latest("run-2", 20) is not None
    assert list(sampler._trees) == ["run-2"]


def test_a_tick_that_finds_nothing_readable_clears_the_previous_sample() -> None:
    clock = FakeClock()
    sampler = _sampler({"run-1": 10}, clock)
    sampler.tick()
    tree = sampler._trees["run-1"]
    assert isinstance(tree, FakeTree)
    tree.sample = lambda: None                                   # type: ignore[method-assign]
    sampler.tick()
    assert sampler.latest("run-1", 10) is None, "行程樹內全部取不到＝不存活，不留上一輪的數字"


def test_a_new_only_tick_samples_runs_without_a_tree_and_leaves_the_others_alone() -> None:
    targets = {"run-1": 10}
    trees: list[FakeTree] = []
    sampler = _sampler(targets, FakeClock(), trees=trees)
    sampler.tick()
    targets["run-2"] = 20
    sampler.tick(new_only=True)
    assert [(t.root_pid, t.calls) for t in trees] == [(10, 1), (20, 1)], \
        "spawn 後補第一筆：只動新的，不拿既有 run 的基準去算一段很短的 CPU"
    assert sampler.latest("run-2", 20) is not None


def test_one_sampling_failure_is_logged_without_the_psutil_message_and_does_not_stop_others(
        caplog: pytest.LogCaptureFixture) -> None:
    clock = FakeClock()
    trees: list[FakeTree] = []
    sampler = _sampler({"bad": 10, "good": 20}, clock, trees=trees)
    sampler.tick()
    bad = sampler._trees["bad"]
    assert isinstance(bad, FakeTree)

    def explode() -> ResourceSample:
        raise psutil.AccessDenied(10, name="SECRET-PROCESS-NAME")

    bad.sample = explode                                         # type: ignore[method-assign]
    caplog.set_level(logging.DEBUG, logger="bridge.resources")
    sampler.tick()
    sampler.tick()                                               # 同一分鐘內不洗版
    assert sampler.latest("good", 20) is not None, "一個 run 取樣失敗不得連累別的 run"
    assert sampler.latest("bad", 10) is None
    lines = [r.getMessage() for r in caplog.records if r.name == "bridge.resources"]
    assert len(lines) == 1 and "AccessDenied" in lines[0] and "bad" in lines[0]
    assert "SECRET-PROCESS-NAME" not in caplog.text, "日誌不寫 psutil 例外的訊息（含行程名稱）"


def test_the_background_thread_survives_a_failing_targets_call_and_keeps_sampling() -> None:
    calls = {"n": 0}

    def flaky_targets() -> dict[str, int]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("targets() 第一次就炸")
        return {"run-1": 10}

    sampler = ResourceSampler(flaky_targets, interval=0.05, tree_factory=_fake_tree)
    sampler.start()
    thread = sampler._thread
    assert thread is not None and thread.is_alive()
    try:
        deadline = time.monotonic() + 5
        while sampler.latest("run-1", 10) is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert sampler.latest("run-1", 10) is not None, "取樣器自己的例外不得讓執行緒死掉"
        assert calls["n"] >= 2
    finally:
        sampler.stop()
    assert not thread.is_alive(), "stop() 要把背景執行緒收乾淨"
    sampler.stop()                                               # 重複 stop 無害
    sampler.start()
    sampler.stop()


def test_request_sample_wakes_the_thread_long_before_the_next_full_round() -> None:
    targets: dict[str, int] = {}
    sampler = ResourceSampler(lambda: dict(targets), interval=60.0, tree_factory=_fake_tree)
    sampler.start()
    try:
        time.sleep(0.2)                                  # 第一輪（空的）已做完，下一輪在 60 秒後
        targets["run-1"] = 10
        sampler.request_sample()
        deadline = time.monotonic() + 5
        while sampler.latest("run-1", 10) is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert sampler.latest("run-1", 10) is not None, "spawn 後要立刻補一筆，不等 5 秒"
    finally:
        sampler.stop()


# ── ③ 經真 HTTP 的 E2E（真引擎＋mock claude）──────────────────────────────────────────
def _poll_resources(bridge: Any, run_id: str, *, present: bool, timeout: float = 20.0
                    ) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = bridge.get_run(run_id)
        if (last["resources"] is not None) == present:
            return last
        if last["status"] in TERMINAL and present:
            break
        time.sleep(0.05)
    raise AssertionError(f"{timeout:g}s 內 resources 沒有{'出現' if present else '消失'}：{last}")


@pytest.fixture
def fast_sampler(monkeypatch: pytest.MonkeyPatch) -> None:
    """把取樣間隔縮到 0.3 秒（模組常數在 RunManager 建構時才讀，所以要在 make_bridge 之前設）。"""
    monkeypatch.setattr(resources_module, "SAMPLE_INTERVAL_SECONDS", 0.3)


def test_a_running_run_exposes_resources_and_they_disappear_when_it_ends(
        fast_sampler, make_bridge: Callable[..., Any], run_body) -> None:
    live = make_bridge()
    info = live.post_run(run_body(delay="30")).json()
    rid = info["run_id"]
    try:
        run = _poll_resources(live, rid, present=True)
        res = run["resources"]
        assert set(res) == _CONTRACT_KEYS, "resources 不含 pid、命令列、環境變數（契約 §3.1.2）"
        assert isinstance(res["cpu_percent"], float) and 0.0 <= res["cpu_percent"] <= 100.0
        assert isinstance(res["rss_bytes"], int) and res["rss_bytes"] > 0
        assert isinstance(res["process_count"], int) and res["process_count"] >= 1
        stamp = datetime.fromisoformat(res["sampled_at"])
        assert stamp.utcoffset() == timedelta(0)
        assert abs((datetime.now(UTC) - stamp).total_seconds()) < 15, "樣本要是新鮮的"
        assert run["pid"] == info["pid"], "既有的 pid 欄位照舊（只增不減）"
        first = res["sampled_at"]
        deadline = time.monotonic() + 10
        while ((live.get_run(rid)["resources"] or {}).get("sampled_at")) in (first, None):
            assert time.monotonic() < deadline, "sampled_at 沒有前進：背景取樣沒有在跑"
            time.sleep(0.1)
    finally:
        live.client.post(f"/autoclaude/runs/{rid}:stop")
    final = live.wait_status(rid, {"CANCELLED"})
    assert final["resources"] is None, "終態沒有行程可取樣"
    assert live.get_run(rid)["resources"] is None


def test_the_first_sample_is_taken_right_after_spawn_not_at_the_next_five_second_round(
        monkeypatch: pytest.MonkeyPatch, make_bridge: Callable[..., Any], run_body) -> None:
    """契約 §3.1.2 的建議：spawn 後立刻補一筆（CPU 0.0），讓第一次輪詢就有值。
    取樣間隔設成 60 秒、Bridge 先空轉一輪之後才建 run：看到值只可能是 spawn 時的喚醒補的。"""
    monkeypatch.setattr(resources_module, "SAMPLE_INTERVAL_SECONDS", 60.0)
    live = make_bridge()
    time.sleep(0.3)                                   # 背景執行緒的第一輪（空的）已做完
    rid = live.post_run(run_body(delay="30")).json()["run_id"]
    try:
        run = _poll_resources(live, rid, present=True, timeout=5.0)
        assert run["resources"]["cpu_percent"] == 0.0, "第一筆的 CPU 是 0.0（基準）"
    finally:
        live.client.post(f"/autoclaude/runs/{rid}:stop")
        live.wait_status(rid, {"CANCELLED"})


def test_resources_are_null_while_paused_and_come_back_after_resume(
        fast_sampler, make_bridge: Callable[..., Any], run_body) -> None:
    """pause 會終止整棵引擎行程樹（ADR-001 D8）：暫停中沒有資源可言；續跑是新行程、新取樣器。"""
    live = make_bridge()
    rid = live.post_run(run_body(delay="1.5")).json()["run_id"]
    _poll_resources(live, rid, present=True)
    assert live.client.post(f"/autoclaude/runs/{rid}:pause").status_code == 202
    paused = live.wait_status(rid, {"PAUSED"})
    assert paused["resources"] is None and paused["pid"] is None

    assert live.client.post(f"/autoclaude/runs/{rid}:resume").status_code == 202
    resumed = _poll_resources(live, rid, present=True)
    assert resumed["resources"]["process_count"] >= 1 and resumed["status"] != "PAUSED"
    final = live.wait_status(rid, TERMINAL)
    assert final["status"] == "COMPLETED" and final["resources"] is None


def test_a_run_that_was_never_spawned_by_this_bridge_has_null_resources(
        make_bridge: Callable[..., Any], settings, project_dir: Path) -> None:
    """Bridge 重啟後從磁碟載回的 run（沒有行程可取樣）：欄位存在、值為 null。"""
    run_id = str(uuid.uuid4())
    paths = RunPaths(settings.engine_workspace / run_id)
    paths.run_dir.mkdir(parents=True)
    save_record(paths, RunRecord(
        run_id=run_id, project="old", execution_path=str(project_dir), status="COMPLETED",
        created_at=datetime.now(UTC).isoformat(), total_steps=1))
    live = make_bridge()
    body = live.client.get(f"/autoclaude/runs/{run_id}").json()
    assert "resources" in body and body["resources"] is None, json.dumps(body)[:200]


def test_the_openapi_document_describes_resources_as_nullable_with_the_four_fields(
        bridge) -> None:
    doc = bridge.client.get("/openapi.json").json()
    schemas = doc["components"]["schemas"]
    assert set(schemas["ResourcesOut"]["properties"]) == _CONTRACT_KEYS
    assert set(schemas["ResourcesOut"]["required"]) == _CONTRACT_KEYS
    field = schemas["RunStateOut"]["properties"]["resources"]
    refs = [item.get("$ref", item.get("type")) for item in field["anyOf"]]
    assert refs == ["#/components/schemas/ResourcesOut", "null"]
    # 只增不減：既有欄位一個都沒少
    assert {"run_id", "status", "pid", "last_event_seq", "attempt"} <= set(
        schemas["RunStateOut"]["properties"])
