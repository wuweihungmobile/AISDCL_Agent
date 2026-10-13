"""PRD §11.8（引擎層）24 小時端到端模擬：跨 4 次 5 小時視窗 reset，0 遺失、0 重複、0 髒污。

PRD §11.8 原文：「24 小時連續運行，跨越至少 4 次 5 小時視窗重置。判準：0 次非預期任務截斷、
0 次髒污工作區、`U7d` 未觸及 `WEEKLY_HALT`、有效工作時間佔比（非等待時間 / 總時間）達成設定目標。」

🔴 **這是模擬時鐘，不是真的 24 小時牆鐘**：`time.time`／`monotonic`／`sleep` 與三處 `datetime`
都換成同一個模擬時鐘，24 小時的等待在毫秒內走完。被測的是**真的** kernel、真的
TokenGuardPlugin（撞線文字 ⇒ halt）、真的 AutoResumeService（存 halt checkpoint、依觀測
`resets_at` 分片休眠、讀 checkpoint 續跑、成功後清 checkpoint）、真的 state repository
（記憶體與檔案兩後端）；替身只有執行器（不啟動 claude）、額度讀數（QuotaMeterPort）、時鐘，
與 CrossStepValidator 的 `git status` 子行程（不是被測面，且每步一次太慢）。

本檔守引擎層（AutoClaude 自己的長時續跑）；根層政策管線＋接力狀態機的 24 小時模擬在
`tools/probe/day_long_relay_sim.py`。`U7d`／`WEEKLY_HALT` 是根層配速的事（引擎層沒有週軸判準），
本檔不重複；有效工作佔比取「非等待時間／總時間」（PRD 括號寫法）。

PRD 句 ↔ 測試：
  · 24 小時、跨 ≥4 次重置 → `test_the_day_spans_24_hours_and_four_resets`
  · 0 次非預期截斷（每步恰完成一次）→ `test_every_step_completes_exactly_once`
  · 0 次髒污工作區 → `test_a_halt_leaves_a_checkpoint_and_completion_clears_it`
  · 喚醒接對的 `interrupted_step`、不早於 reset → `test_each_wake_resumes_on_the_interrupted_step`
  · 有效工作時間佔比 ≥ 目標 → `test_the_non_waiting_share_meets_the_target`
  · 偵測器自證（紅綠）→ `test_a_regression_*`／`test_without_the_quota_axis_*`：把引擎行為在行程內
    換成壞的（不改任何檔），對應斷言必須轉紅。
"""
from __future__ import annotations

import subprocess
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from autoclaude.core import wiring
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.core.ports.observability import NullObservability
from autoclaude.core.ports.quota_meter import QuotaReading, quota_refusal
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator
from autoclaude.infra.repositories.factory import canonical_playbook_id
from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.infra.repositories.in_memory_state_repository import InMemoryStateRepository
from autoclaude.utils.config import AppConfig, PlaybookConfig

#: 有效工作時間佔比（非等待時間／總時間）的設定目標。出廠 0.80 的來源：本情境四次等待共約
#: 135 分鐘（撞線後等到 reset；額度路徑以 reset 為準、不再被 `resume_delay_minutes`
#: 墊高）占 24.7 小時的一成，
#: 理論值約 0.89；取其 90% 向下取整到 0.05。換情境（撞線頻率、步長）要連帶重訂。
_TARGET_NON_WAIT_SHARE = 0.80
_STEP_S, _N_STEPS = 20 * 60, 64                  # 每步 20 分鐘、共 64 步（模擬）
_DAY_S = 24 * 3600
#: (撞線時刻, 該視窗 reset 時刻)，模擬秒。各落在 5h 視窗尾段，等待長度各異：25／40／15／55 分。
_HITS = ((16500, 18000), (33600, 36000), (53100, 54000), (68700, 72000))
_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_LIMIT_TEXT = "You've hit your usage limit reached · resets at the top of the next window"


class _SimClock:
    """模擬時鐘（秒）。`sleep` 只前進時鐘；首次睡眠時抓取「halt 後的 checkpoint」快照。"""

    def __init__(self) -> None:
        self.t, self.slept, self.on_first_sleep = 0.0, 0.0, None

    def sleep(self, seconds: float) -> None:
        if self.on_first_sleep is not None:
            self.on_first_sleep()
        self.t, self.slept = self.t + seconds, self.slept + seconds

    def iso(self, seconds: float) -> str:
        return (_T0 + timedelta(seconds=seconds)).isoformat()


def _sim_datetime(clock: _SimClock) -> type:
    class _Sim(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206 — 與 datetime.now 同簽章
            moment = _T0 + timedelta(seconds=clock.t)
            return moment.astimezone(tz) if tz else moment.replace(tzinfo=None)

    return _Sim


class _DayExecutor:
    """假執行器：每步耗 20 模擬分鐘；撞線時刻落在步內 ⇒ 做到撞線那一刻、步驟中斷；額度窗
    用盡期間（到 reset 前）任何執行都立刻回撞線。全程逐筆記帳 `(label, 起, 迄, 結果)`。"""

    def __init__(self, clock: _SimClock) -> None:
        self.clock, self.pending, self.log = clock, list(_HITS), []
        self.exhausted_until: float | None = None

    def exhausted(self) -> bool:
        return self.exhausted_until is not None and self.clock.t < self.exhausted_until

    def _refuse(self, label: str, outcome: str) -> ExecutionOutput:
        self.log.append((label, self.clock.t, self.clock.t, outcome))
        return ExecutionOutput(text=_LIMIT_TEXT, exit_code=1, completed=False,
                               quota_refusal=quota_refusal(_LIMIT_TEXT))

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        start = self.clock.t
        if self.exhausted():
            return self._refuse(label, "refused")
        hit = next((h for h in self.pending if h[0] < start + _STEP_S), None)   # 不漏掉任何排定撞線
        if hit is not None:
            self.pending.remove(hit)
            self.clock.t, self.exhausted_until = max(start, float(hit[0])), float(hit[1])
            return self._refuse(label, "hit")
        self.clock.t = start + _STEP_S
        self.log.append((label, start, self.clock.t, "ok"))
        return ExecutionOutput(text=f"[STEP_OK] {label}")


class _DayMeter:
    """QuotaMeterPort 替身：額度窗用盡期間回 100%（resets_at＝該窗 reset），其餘回低水位。"""

    def __init__(self, clock: _SimClock, executor: _DayExecutor) -> None:
        self._clock, self._ex = clock, executor

    def read(self):
        if self._ex.exhausted():
            return QuotaReading(100.0, "five_hour", self._clock.iso(self._ex.exhausted_until))
        return QuotaReading(35.0, "five_hour", self._clock.iso(self._clock.t + 3600))

    read_worst_pct = read


def _run_day(tmp_path: Path, monkeypatch, *, backend: str = "in_memory",
             with_quota_axis: bool = True) -> SimpleNamespace:
    """跑完整個模擬日；回所有取證所需的物件（斷言一律事後讀它）。"""
    clock = _SimClock()
    executor = _DayExecutor(clock)
    meter = _DayMeter(clock, executor) if with_quota_axis else None
    fake_time = SimpleNamespace(time=lambda: 1.7e9 + clock.t, monotonic=lambda: clock.t,
                                sleep=clock.sleep)
    sim_dt = _sim_datetime(clock)
    for module in ("autoclaude.utils.resume_clock", "autoclaude.core.ports.quota_meter",
                   "autoclaude.infra.repositories.in_memory_state_repository",
                   "autoclaude.infra.repositories.file_state_repository"):
        monkeypatch.setattr(f"{module}.datetime", sim_dt)
    monkeypatch.setattr("autoclaude.core.services.auto_resume.time", fake_time)
    monkeypatch.setattr(wiring, "build_quota_meter", lambda *a, **k: meter)
    # 跨步驟污染偵測（CrossStepValidator）每步跑一次 `git status`：不是被測面，且在大 repo 裡每次
    # 約 0.13 秒、64 步就把一個測試拖到 20 秒。換成「非 git 環境」的回應（它的既有略過路徑）。
    monkeypatch.setattr("autoclaude.execution.cross_step_validator.subprocess", SimpleNamespace(
        run=lambda *a, **k: subprocess.CompletedProcess(a, 128, "", "not a git repository"),
        TimeoutExpired=subprocess.TimeoutExpired))

    playbook = tmp_path / "day_long.yaml"
    playbook.write_text(yaml.safe_dump({
        "version": "1.0", "project": "day_long_prd11_8",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 0},
        "tasks": [{"step_id": f"T{i:02d}", "name": f"step {i}", "prompt": f"do step {i}",
                   "expected_output_regex": r"\[STEP_OK\]"} for i in range(1, _N_STEPS + 1)],
    }, allow_unicode=True), encoding="utf-8", newline="\n")
    cfg = AppConfig(checkpoint_dir=str(tmp_path / "ckpt"))
    cfg.notification.enabled = False
    cfg.token_guard.auto_resume = True
    cfg.token_guard.quota_throttle_pct, cfg.token_guard.quota_halt_pct = 70.0, 95.0
    repo = (FileStateRepository(cfg.checkpoint_dir) if backend == "file"
            else InMemoryStateRepository())
    kernel = wiring.build_kernel(cfg, executor=executor, evaluator=ShellEvaluator(PlaybookConfig()),
                                 state_repository=repo, observability=NullObservability())
    service = AutoResumeService(kernel, cfg, state_repository=repo, quota_meter=meter)
    pid = canonical_playbook_id(str(playbook), mode=cfg.storage.mode)

    snaps: list[tuple] = []

    def snapshot() -> None:                          # 每次 halt 後的第一次睡眠前：checkpoint 在不在
        hits_so_far = sum(1 for e in executor.log if e[3] == "hit")
        if len(snaps) < hits_so_far:
            ck = repo.load_checkpoint(pid)
            snaps.append((clock.t, None if ck is None else (ck.step_idx, ck.step_id)))

    clock.on_first_sleep = snapshot
    result = service.run(str(playbook), fresh=False)
    return SimpleNamespace(clock=clock, executor=executor, repo=repo, pid=pid, snaps=snaps,
                           result=result, service=service, cfg=cfg)


def _hits_and_wakes(day: SimpleNamespace) -> list[dict]:
    """每次排定撞線 ⇒ `{被中斷的步, 撞線時刻, reset, 喚醒後第一次執行的步與時刻}`。"""
    log, out = day.executor.log, []
    for i, (label, at, _end, outcome) in enumerate(log):
        if outcome != "hit":
            continue
        later = next(((lb, st) for lb, st, _e, oc in log[i + 1:] if oc in ("ok", "refused")),
                     (None, None))
        out.append({"label": label, "at": at, "reset": _HITS[len(out)][1],
                    "wake_label": later[0], "wake_at": later[1]})
    return out


def _check_each_step_once(day: SimpleNamespace) -> None:
    done = Counter(label for label, _s, _e, outcome in day.executor.log if outcome == "ok")
    expected = {f"T{i:02d}": 1 for i in range(1, _N_STEPS + 1)}
    assert done == expected, (f"遺失 {sorted(set(expected) - set(done))}、"
                              f"重複 {sorted(k for k, v in done.items() if v > 1)}")


def _check_checkpoints(day: SimpleNamespace) -> None:
    wakes = _hits_and_wakes(day)
    assert len(day.snaps) == 4 and all(snap[1] is not None for snap in day.snaps), day.snaps
    for snap, hit in zip(day.snaps, wakes, strict=True):
        index = int(hit["label"][1:]) - 1
        assert snap[1] == (index, hit["label"]), f"checkpoint {snap[1]} 不是被中斷的步 {hit}"
    assert day.repo.load_checkpoint(day.pid) is None, "成功收尾後 checkpoint 沒被清掉"
    if isinstance(day.repo, FileStateRepository):
        left = [p.name for p in Path(day.cfg.checkpoint_dir).glob("*.tmp")]
        assert left == [], f"留下暫存殘檔 {left}"


def _check_wakes(day: SimpleNamespace) -> None:
    for hit in _hits_and_wakes(day):
        assert hit["wake_label"] == hit["label"], f"喚醒接錯步：{hit}"
        assert hit["wake_at"] >= hit["reset"], f"早於 reset 喚醒（會再撞一次）：{hit}"
        gap_min = (hit["wake_at"] - hit["reset"]) / 60
        # 寬上界：對照組（無額度軸）也要走得到下一條「早於 reset」斷言
        limit = day.cfg.token_guard.resume_delay_minutes + 1
        assert gap_min <= limit, f"喚醒比 reset 晚了 {gap_min:.1f} 分鐘（> {limit}，超過補足）"


@pytest.fixture(params=["in_memory", "file"])
def day(request, tmp_path, monkeypatch):
    return _run_day(tmp_path, monkeypatch, backend=request.param)


def test_the_day_spans_24_hours_and_four_resets(day):
    assert day.result.success is True and day.result.halted is False
    assert day.clock.t >= _DAY_S, f"模擬牆鐘只有 {day.clock.t / 3600:.2f} 小時，不足 24 小時"
    assert sum(1 for e in day.executor.log if e[3] == "hit") == 4
    assert day.service.metrics["halt_resumes"] == 4, "四次撞線必須各產生一次 halt 喚醒"
    lags = [(h["wake_at"] - h["reset"]) / 60 for h in _hits_and_wakes(day)]
    assert max(lags) <= 2, f"R213 F4 後喚醒不得晚於 reset 超過一片分片休眠：{lags}"
    print(f"\n[PRD §11.8 引擎層] 模擬牆鐘 {day.clock.t / 3600:.2f} 小時、撞線 4 次、喚醒 "
          f"{day.service.metrics['total_wakes']} 次、"
          f"喚醒晚於 reset 分鐘 {lags}")


def test_every_step_completes_exactly_once(day):
    """0 次非預期截斷的引擎層定義：撞線中斷的那一步沒有遺失、也沒有被重複完成。"""
    _check_each_step_once(day)


def test_a_halt_leaves_a_checkpoint_and_completion_clears_it(day):
    """0 次髒污工作區（引擎層＝進度檔）：每次 halt 後 checkpoint 已落地且指向被中斷的步；
    整條 playbook 成功後 checkpoint 被清掉（不留下一次不加 --fresh 會從舊斷點重跑的殘骸）。"""
    _check_checkpoints(day)


def test_each_wake_resumes_on_the_interrupted_step(day):
    """喚醒接的是被中斷的那一步（`interrupted_step`），且不早於額度視窗 reset。"""
    _check_wakes(day)


def test_the_non_waiting_share_meets_the_target(day):
    total, waited = day.clock.t, day.clock.slept
    share = (total - waited) / total
    effective = sum(e - s for _l, s, e, oc in day.executor.log if oc == "ok") / total
    print(f"\n[PRD §11.8 引擎層] 非等待時間佔比 {share:.3f}（目標 ≥ {_TARGET_NON_WAIT_SHARE}）、"
          f"完成步驟時長佔比 {effective:.3f}、等待 {waited / 60:.0f} 分／總計 {total / 60:.0f} 分")
    assert share >= _TARGET_NON_WAIT_SHARE
    slack = day.cfg.token_guard.sleep_slice_seconds * day.service.metrics["total_wakes"]
    assert waited == pytest.approx(day.service.metrics["total_wait_seconds"], abs=slack)


# ══════════════════════════════════════════════════════════════════════════════
# 偵測器自證：把引擎行為在行程內換成壞的（不改任何檔），對應斷言必須轉紅
# ══════════════════════════════════════════════════════════════════════════════
def test_without_the_quota_axis_the_wake_is_premature(tmp_path, monkeypatch):
    """拿掉額度軸，引擎只剩 `resume_delay_minutes=30` 的猜測——撞線後還要等 40／55 分鐘才
    reset 的兩次會早醒、再撞一次。「不早於 reset」那條斷言必須看得到這件事。"""
    control = _run_day(tmp_path, monkeypatch, with_quota_axis=False)
    assert len([e for e in control.executor.log if e[3] == "refused"]) >= 2
    with pytest.raises(AssertionError, match="早於 reset"):
        _check_wakes(control)


def test_a_regression_that_never_clears_the_checkpoint_is_detected(tmp_path, monkeypatch):
    """DEF-200-510 的回歸形態（成功收尾不清 checkpoint）⇒ 髒污斷言必須轉紅。"""
    monkeypatch.setattr(AutoResumeService, "_clear_finished_checkpoints", lambda self, paths: None)
    with pytest.raises(AssertionError, match="沒被清掉"):
        _check_checkpoints(_run_day(tmp_path, monkeypatch))


def test_a_regression_that_restarts_from_step_zero_is_detected(tmp_path, monkeypatch):
    """喚醒不讀 checkpoint、每次從頭重跑 ⇒ 前面的步驟被重複完成，「恰完成一次」必須轉紅。"""
    monkeypatch.setattr(AutoResumeService, "_resolve_start",
                        lambda self, path, fresh: (0, [], False, None))
    with pytest.raises(AssertionError, match="重複"):
        _check_each_step_once(_run_day(tmp_path, monkeypatch))


def test_a_regression_that_skips_the_interrupted_step_is_detected(tmp_path, monkeypatch):
    """喚醒從被中斷那一步的下一步續跑 ⇒ 該步遺失，「恰完成一次」必須轉紅。"""
    original = AutoResumeService._resolve_start

    def skipping(self, path, fresh):
        start, log, has_ck, sched = original(self, path, fresh)
        return (start + 1 if has_ck else start), log, has_ck, sched

    monkeypatch.setattr(AutoResumeService, "_resolve_start", skipping)
    with pytest.raises(AssertionError, match="遺失"):
        _check_each_step_once(_run_day(tmp_path, monkeypatch))
