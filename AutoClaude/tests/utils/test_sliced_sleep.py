"""improving_113 W3：引擎等待改為分片休眠（PRD §4.5.2）＋ 過長的等待不在行程內硬等（PRD §4.5.5）。

驗證意圖（Rule 9）：修前兩處等待都是單次 `time.sleep(wait)`——機器睡著後醒來嚴重超時、
時鐘跳躍無法修正、等待期間沒有任何檢查點可收中斷、超過上限的等待仍在行程內硬等。
本檔守的是這四件事會不會**回來**，而不是 `sliced_sleep` 的實作細節：
  1. 純函式層（注入式時鐘、不真睡）：睡滿／跳躍重算／中斷／零等待／任何 sleep 替身下必然終止；
  2. 服務層：兩處等待真的走分片（吃設定值）、>max_inprocess 拒絕且 checkpoint 已落（續跑時刻
     是真實的等待終點）、中斷優雅返回；
  3. 接線鎖：auto_resume.py 不得再直接呼叫 `time.sleep`；main.py 把 hotkey.triggered 注入服務
     （注入點已接；入口目前未呼叫 hotkey.register()，事件源是否被設定不在本檔射程）；
     TokenGuardConfig 三欄的預設值（與 PRD 對齊／刻意偏離各自釘死）與邊界。
"""
from __future__ import annotations

import ast
import logging
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.ports.quota_meter import QuotaReading
from autoclaude.core.services import auto_resume as auto_resume_mod
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.in_memory_state_repository import (
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from autoclaude.utils.config import AppConfig, TokenGuardConfig
from autoclaude.utils.sliced_sleep import SleepOutcome, sliced_sleep

TESTS_DIR = Path(__file__).resolve().parent.parent
SIMPLE_PB = str(TESTS_DIR / "equivalence" / "fixtures" / "01_simple_2_step.yaml")
PKG_DIR = TESTS_DIR.parent / "autoclaude"


class _FakeClock:
    """注入式時鐘：`sleep` 只推進假時間、不真睡。

    `wall_extra={第幾次 sleep 呼叫: 額外牆鐘秒數}` 模擬「sleep 期間機器睡著／NTP 校時」：
    牆鐘多走（或倒退）、單調鐘不動——正是兩個時鐘增量差的來源。
    """

    def __init__(self, wall_extra: dict[int, float] | None = None):
        self.w = 1_000_000.0
        self.m = 500.0
        self.calls: list[float] = []
        self._extra = dict(wall_extra or {})

    def wall(self) -> float:
        return self.w

    def mono(self) -> float:
        return self.m

    def sleep(self, secs: float) -> None:
        self.calls.append(secs)
        self.w += secs + self._extra.get(len(self.calls), 0.0)
        self.m += secs


def _run(clock: _FakeClock, wait: float, *, slice_s: float = 60.0, tol: float = 5.0,
         stop=lambda: False) -> SleepOutcome:
    return sliced_sleep(wait, slice_s, tol, wall=clock.wall, mono=clock.mono,
                        sleep=clock.sleep, stop=stop)


# ══════════════════════════════════════════════════════════════════════════════
# 一、純函式層（注入式時鐘，不真睡）
# ══════════════════════════════════════════════════════════════════════════════
class TestSlicedSleepPure:
    def test_a_wait_is_slept_in_slices_until_it_is_full(self):
        clock = _FakeClock()
        out = _run(clock, 150)
        assert clock.calls == [60, 60, 30], "每片不得長於 slice；最後一片只睡剩餘"
        assert out == SleepOutcome(150.0, False, False, 0.0)

    @pytest.mark.parametrize("wait", [1, 59.5, 60, 61, 600, 7200])
    def test_the_slices_always_add_up_to_the_wait_when_no_clock_jumps(self, wait):
        clock = _FakeClock()
        out = _run(clock, wait)
        assert math.isclose(sum(clock.calls), wait) and max(clock.calls) <= 60
        assert out.remaining_seconds == 0.0 and not out.interrupted

    @pytest.mark.parametrize("wait", [0, -1, -3600.0])
    def test_a_wait_that_is_not_positive_never_sleeps(self, wait):
        clock = _FakeClock()
        out = _run(clock, wait)
        assert clock.calls == [], "wait<=0 卻 sleep 了 ⇒ 已過期的排程時刻被硬等"
        assert out == SleepOutcome(0.0, False, False, 0.0)

    def test_a_wall_clock_jump_beyond_tolerance_ends_the_wait_early(self, caplog):
        """機器在第 2 片期間睡著（牆鐘多走 2 小時、單調鐘不動）⇒ 剩餘改以牆鐘重算。

        修前的單次 `time.sleep(3600)` 在這個情境會把整個 3600 秒的單調鐘時間照睡完，
        醒來時牆鐘已超過目標時刻 2 小時以上；紅綠對照＝下一格（跳躍在容忍內時全片照睡）。
        """
        clock = _FakeClock(wall_extra={2: 7200.0})
        with caplog.at_level(logging.WARNING, logger="autoclaude"):
            out = _run(clock, 3600)
        assert clock.calls == [60, 60], "偵測到跳躍後必須提早結束，不得再睡剩下 58 片"
        assert out.clock_jump_detected and not out.interrupted
        assert out.remaining_seconds == 0.0
        assert out.slept_seconds == 60 + (60 + 7200)
        assert "剩餘改以牆鐘重算" in caplog.text and "忽略牆鐘倒退" not in caplog.text

    def test_a_jump_within_tolerance_is_not_a_jump(self):
        clock = _FakeClock(wall_extra={2: 3.0})          # 容忍 5 秒：3 秒是時鐘雜訊
        out = _run(clock, 3600)
        assert len(clock.calls) == 60 and not out.clock_jump_detected

    @pytest.mark.parametrize("extra,calls,jumped", [
        (5.0, [60, 60], False), (5.5, [60, 54.5], True),
    ])
    def test_the_tolerance_boundary_is_strictly_greater_than(self, extra, calls, jumped):
        """邊界方向鎖：規格是「增量差 > tol」才算跳躍。恰等於 tol 仍是時鐘雜訊、不入帳；
        `>` 被改成 `>=` 時第一格轉紅（該片多扣 tol 秒、calls 變 [60, 55]、旗標亮起）。"""
        clock = _FakeClock(wall_extra={1: extra})        # |dw − dm| = extra；tol = 5.0
        out = _run(clock, 120, tol=5.0)
        assert out.clock_jump_detected is jumped and clock.calls == calls

    def test_a_partial_jump_only_shortens_the_remaining_by_the_wall_delta(self):
        """跳躍不一定吃光剩餘：牆鐘多走 300 秒 ⇒ 剩餘扣 300 秒，其餘照常分片睡完。"""
        clock = _FakeClock(wall_extra={2: 300.0})
        out = _run(clock, 600)
        assert clock.calls == [60, 60, 60, 60, 60]       # 600 − (60 + 360) = 180 ⇒ 3 片
        assert out.clock_jump_detected and out.remaining_seconds == 0.0
        assert out.slept_seconds == 600

    def test_a_backward_wall_step_never_extends_the_wait(self, caplog):
        """牆鐘被往回撥（NTP 校時）時寧可早醒、不得因此多睡：早醒的代價是再 halt 一次、
        多睡的代價是真實閒置時間。偵測旗標仍要亮（可診斷），只是不改剩餘；而且訊息必須與實際
        動作一致——這裡實作是「忽略牆鐘」，不能說成「剩餘改以牆鐘重算」。"""
        clock = _FakeClock(wall_extra={1: -3600.0})
        with caplog.at_level(logging.WARNING, logger="autoclaude"):
            out = _run(clock, 300)
        assert clock.calls == [60, 60, 60, 60, 60]
        assert out.clock_jump_detected and out.remaining_seconds == 0.0
        assert "忽略牆鐘倒退" in caplog.text and "剩餘改以牆鐘重算" not in caplog.text

    def test_a_stop_before_the_first_slice_exits_without_sleeping(self):
        clock = _FakeClock()
        out = _run(clock, 300, stop=lambda: True)
        assert clock.calls == []
        assert out == SleepOutcome(0.0, True, False, 300.0)

    def test_a_stop_in_the_middle_exits_gracefully_with_the_unslept_remainder(self):
        clock = _FakeClock()
        out = _run(clock, 300, stop=lambda: len(clock.calls) >= 2)
        assert clock.calls == [60, 60], "中斷後不得再睡下一片"
        assert out.interrupted and out.remaining_seconds == 180.0
        assert out.slept_seconds == 120.0

    def test_a_late_stop_does_not_turn_a_finished_wait_into_an_interrupted_one(self):
        clock = _FakeClock()
        answers = iter([False, True, True])               # 睡完那一刻才亮中斷
        out = _run(clock, 60, stop=lambda: next(answers))
        assert clock.calls == [60]
        assert not out.interrupted and out.remaining_seconds == 0.0

    def test_a_sleep_stand_in_that_moves_no_clock_still_terminates(self):
        """🔴 既有 7 支測試檔用 `patch("...time.sleep")` 把 sleep 換成立即返回的替身、時鐘照走真的。

        進度若只靠量測時鐘，替身下單調鐘一輪只前進數微秒 ⇒ 等待要轉極大量圈數 ＝ 測試實質掛死。
        所以計入量下限必須是「請求的片長」：任何 sleep 替身下恰好 ceil(wait/slice) 圈。
        """
        calls: list[float] = []
        # stop 只是護欄：退化時在 50 圈後快速轉紅，而不是把整個測試行程掛死。
        out = sliced_sleep(300, 60, 5, wall=lambda: 1.0, mono=lambda: 1.0,
                           sleep=calls.append, stop=lambda: len(calls) >= 50)
        assert calls == [60.0] * 5 and out.remaining_seconds == 0.0

    def test_a_process_stall_longer_than_the_slice_is_counted_by_the_monotonic_clock(self):
        """SIGSTOP／Ctrl-Z 一段時間：兩個時鐘一起走、不是跳躍，但剩餘仍要照實扣。"""
        clock = _FakeClock()
        real_sleep = clock.sleep

        def stalled_sleep(secs):
            real_sleep(secs)
            if len(clock.calls) == 1:
                clock.w += 500.0
                clock.m += 500.0

        out = sliced_sleep(600, 60, 5, wall=clock.wall, mono=clock.mono,
                           sleep=stalled_sleep, stop=lambda: False)
        assert not out.clock_jump_detected
        assert len(clock.calls) == 1 + math.ceil((600 - 560) / 60)

    @pytest.mark.parametrize("bad", [0, -1])
    def test_a_non_positive_slice_fails_loud_instead_of_spinning(self, bad):
        with pytest.raises(ValueError, match="slice_seconds"):
            _run(_FakeClock(), 60, slice_s=bad)


# ══════════════════════════════════════════════════════════════════════════════
# 二、服務層：兩處等待真的走分片，且 >max_inprocess 拒絕行程內長睡
# ══════════════════════════════════════════════════════════════════════════════
def _time_passes(elapsed):
    """讓測試裡的「睡了」等於「時間過了」：倒數用的時鐘＝真實 now ＋ elapsed()。

    DEF-200-511：`--fresh` 修前會一路漏進續跑輪，續跑輪因此不讀 halt 剛存的 checkpoint；
    下面幾支測試靠這個漏洞才沒碰到「sleep 被替身換掉 ⇒ 排程時刻仍在未來 ⇒ 續跑輪的
    checkpoint_resume 又等一次」。真實執行裡睡完那一刻排程已過期、續跑輪的等待為 0；
    本 helper（patch resume_clock.datetime）把測試環境拉回與真實一致，各測試對「第一次
    （halt）等待」的斷言因此原封不動。
    """
    real = datetime

    class _Advanced(real):
        @classmethod
        def now(cls, tz=None):
            return real.now(tz) + timedelta(seconds=elapsed())

    return patch("autoclaude.utils.resume_clock.datetime", _Advanced)


class _HaltingKernel:
    """每次都回 halted（halt_step_idx=1 ⇒ AutoResumeService 會先存 checkpoint）。"""

    def __init__(self):
        self.calls = 0

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.calls += 1
        return KernelResult.halted_(
            completed_steps=1, total_steps=2, step_log=["[T01] done"],
            completed_step_ids=["T01"], halt_step_idx=1, peak_token_pct=93.0,
        )


class _HaltingWithoutStepIdxKernel:
    """halt 但不帶 halt_step_idx：AutoResumeService 不會替它存 checkpoint（既有契約）。"""

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        return KernelResult.halted_(
            completed_steps=1, total_steps=2, step_log=["[T01] done"],
            completed_step_ids=["T01"], peak_token_pct=93.0,
        )


class _OkKernel:
    def __init__(self):
        self.starts: list[int] = []

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.starts.append(start_idx)
        return KernelResult(success=True, completed_steps=2, total_steps=2, reason="success")


def _cfg(delay_minutes: int = 1, **token_guard) -> AppConfig:
    cfg = AppConfig()
    cfg.notification.enabled = False        # 通知背景執行緒會污染被 patch 的 time.sleep
    cfg.token_guard.auto_resume = True
    cfg.token_guard.max_auto_resumes = 1
    cfg.token_guard.resume_delay_minutes = delay_minutes
    for key, value in token_guard.items():
        setattr(cfg.token_guard, key, value)
    return cfg


def _playbook_id(cfg: AppConfig) -> str:
    from autoclaude.infra.repositories.factory import canonical_playbook_id
    return canonical_playbook_id(SIMPLE_PB, mode=cfg.storage.mode)


class TestTheHaltWaitIsSliced:
    def test_the_wait_is_cut_by_the_configured_slice_and_adds_up_to_the_wait(self):
        cfg = _cfg(delay_minutes=1, sleep_slice_seconds=10)
        svc = AutoResumeService(_HaltingKernel(), cfg, state_repository=InMemoryStateRepository())
        slept: list[float] = []
        with patch("autoclaude.core.services.auto_resume.time.sleep", slept.append), \
                _time_passes(lambda: sum(slept)):
            svc.run(SIMPLE_PB, fresh=True)
        assert slept and max(slept) <= 10, f"沒有吃 sleep_slice_seconds：{slept}"
        assert 55 < sum(slept) <= 61, "1 分鐘的 resume_delay 該睡滿（排程時刻取到秒，截斷 <1s）"

    def test_the_service_hands_the_config_values_to_the_sleeper(self):
        """接線鎖：三個旋鈕必須是設定值，不是寫死在服務裡的常數。"""
        cfg = _cfg(delay_minutes=1, sleep_slice_seconds=7, clock_jump_tolerance_seconds=3)
        svc = AutoResumeService(_HaltingKernel(), cfg, state_repository=InMemoryStateRepository())
        seen: list[tuple] = []
        real = auto_resume_mod.sliced_sleep

        def spy(wait, slice_s, tol, **kw):
            seen.append((slice_s, tol))
            return real(wait, slice_s, tol, **kw)

        with patch("autoclaude.core.services.auto_resume.time.sleep"), \
                patch("autoclaude.core.services.auto_resume.sliced_sleep", spy):
            svc.run(SIMPLE_PB, fresh=True)
        # DEF-200-511：--fresh 只管第一輪，續跑輪會讀 halt 剛存的 checkpoint 而多一次
        # checkpoint_resume 等待（也走分片）。接線鎖的意圖是「每一次等待都吃設定值」。
        assert seen and set(seen) == {(7, 3)}

    def test_a_wall_clock_jump_during_the_wait_resumes_early_and_says_so(self, caplog):
        """服務層端到端：機器在等待中睡著 ⇒ 醒來後不再硬睡完 1 小時，直接續跑。"""
        cfg = _cfg(delay_minutes=60, sleep_slice_seconds=60)   # 釘住片長：下面的 [60, 60] 才是算術
        kernel = _HaltingKernel()
        svc = AutoResumeService(kernel, cfg, state_repository=InMemoryStateRepository())
        clock = _FakeClock(wall_extra={2: 4000.0})
        real = auto_resume_mod.sliced_sleep

        def with_fake_clocks(wait, slice_s, tol, **kw):
            return real(wait, slice_s, tol, wall=clock.wall, mono=clock.mono,
                        sleep=clock.sleep, stop=kw["stop"])

        wall0 = clock.w
        with caplog.at_level(logging.WARNING, logger="autoclaude"), \
                patch("autoclaude.core.services.auto_resume.sliced_sleep", with_fake_clocks), \
                _time_passes(lambda: clock.w - wall0):
            svc.run(SIMPLE_PB, fresh=True)
        assert clock.calls == [60, 60], "跳躍後仍照睡剩下的片 ⇒ 時鐘跳躍沒有被修正"
        assert kernel.calls == 2, "提早醒來後必須續跑（max_auto_resumes=1 ⇒ 共 2 輪）"
        assert "時鐘跳躍" in caplog.text, "偵測到跳躍卻沒有任何痕跡 ⇒ 不可診斷"


class _LongQuotaMeter:
    """額度軸量到 session 視窗、約 2 小時後 reset：`_halt_wait_seconds` 會回 7200 秒上下的等待。"""

    def read(self):
        return QuotaReading(96.0, "session", (datetime.now(UTC) + timedelta(hours=2)).isoformat())


class TestALongWaitIsRefusedInProcess:
    """PRD §4.5.5：等待 > max_inprocess_wait_seconds 不在行程內硬等。"""

    def test_a_halt_wait_above_the_cap_is_refused_with_the_checkpoint_on_disk(self, caplog):
        cfg = _cfg(delay_minutes=5, max_inprocess_wait_seconds=60)
        repo, kernel = InMemoryStateRepository(), _HaltingKernel()
        svc = AutoResumeService(kernel, cfg, state_repository=repo)
        slept: list[float] = []
        with caplog.at_level(logging.ERROR, logger="autoclaude"), \
                patch("autoclaude.core.services.auto_resume.time.sleep", slept.append):
            result = svc.run(SIMPLE_PB, fresh=True)
        assert slept == [], "拒絕長睡卻還是睡了"
        assert result.success is False and result.halted is True, "必須是非零 rc 的結果"
        assert result.reason == "external_resume_required"
        assert kernel.calls == 1, "拒絕後不得續跑"
        ck = repo.load_checkpoint(_playbook_id(cfg))
        assert ck is not None and ck.step_idx == 1 and ck.scheduled_resume_at, (
            "拒絕的前提是 checkpoint 已落地（含排程時刻），否則外部沒有東西可以續")
        assert result.scheduled_resume_at == ck.scheduled_resume_at, "結果沒有帶續跑時刻"
        assert "需外部續跑" in caplog.text and "已落地" in caplog.text
        assert svc.metrics["total_wakes"] == 0, "沒有發生的喚醒不得記成一次喚醒"

    def test_a_quota_axis_refusal_pins_the_real_resume_time_into_the_checkpoint(self, caplog):
        """額度軸上 checkpoint 內的 scheduled_resume_at 原本是 resume_delay_minutes 推算的（這裡
        5 分鐘後），與要等的 2 小時無關——外部續跑者若以 checkpoint 為準會早醒近 2 小時、再 halt
        一次。拒絕時必須改寫成真實的等待終點，且結果與 ERROR 行帶同一個時刻。"""
        cfg = _cfg(delay_minutes=5, max_inprocess_wait_seconds=60)
        repo = InMemoryStateRepository()
        svc = AutoResumeService(_HaltingKernel(), cfg, state_repository=repo,
                                quota_meter=_LongQuotaMeter())
        t0 = datetime.now()
        with caplog.at_level(logging.ERROR, logger="autoclaude"), \
                patch("autoclaude.core.services.auto_resume.time.sleep") as slept:
            result = svc.run(SIMPLE_PB, fresh=True)
        assert slept.call_count == 0 and result.reason == "external_resume_required"
        ck = repo.load_checkpoint(_playbook_id(cfg))
        # 與後端同為 naive 本地時間的算術（跨 DST 不偏）：預期＝t0 + 2 小時
        lag = (datetime.fromisoformat(ck.scheduled_resume_at) - (t0 + timedelta(hours=2))
               ).total_seconds()
        # 區間 [-1, 62)：就是 reset 時刻、向上取整到分鐘（寧晚勿早；-1 是 ISO 字串截到秒）。
        # 未改寫時是 resume_delay 的 5 分鐘後（lag≈-6900）；取整改向下則 lag≈-60。
        assert -1 <= lag < 62, f"續跑時刻應＝額度 reset 且不早於它，實際差 {lag:+.0f}s"
        assert ck.step_idx == 1, "只改寫續跑時刻，不得動到 halt 點"
        assert result.scheduled_resume_at == ck.scheduled_resume_at, "結果與 checkpoint 時刻不同"
        assert ck.scheduled_resume_at in caplog.text, "ERROR 行沒有帶續跑時刻"

    def test_a_refusal_never_fabricates_a_checkpoint_it_could_not_read_back(self, caplog):
        """halt 不帶 halt_step_idx、磁碟上其實沒有 checkpoint：拒絕時若為了「改寫續跑時刻」直接呼叫
        schedule_resume，後端會憑空造出一份 step_idx=0 的空 checkpoint，外部續跑者就會從頭重跑。
        只准改寫讀得回來的那一份；讀不回來就老實說「未確認落地」、不帶時刻。"""
        cfg = _cfg(delay_minutes=0, max_inprocess_wait_seconds=60)
        repo = InMemoryStateRepository()
        svc = AutoResumeService(_HaltingWithoutStepIdxKernel(), cfg, state_repository=repo,
                                quota_meter=_LongQuotaMeter())
        with caplog.at_level(logging.ERROR, logger="autoclaude"), \
                patch("autoclaude.core.services.auto_resume.time.sleep"):
            result = svc.run(SIMPLE_PB, fresh=True)
        assert result.reason == "external_resume_required"
        assert repo.load_checkpoint(_playbook_id(cfg)) is None, "拒絕路徑憑空造出了 checkpoint"
        assert result.scheduled_resume_at is None
        assert "未確認落地" in caplog.text

    def test_control_the_same_wait_at_or_below_the_cap_is_slept_not_refused(self):
        """控制組（本判準最貴的假紅方向）：上限內的等待必須照常睡完並續跑。"""
        cfg = _cfg(delay_minutes=5, max_inprocess_wait_seconds=600)
        kernel = _HaltingKernel()
        svc = AutoResumeService(kernel, cfg, state_repository=InMemoryStateRepository())
        slept: list[float] = []
        with patch("autoclaude.core.services.auto_resume.time.sleep", slept.append), \
                _time_passes(lambda: sum(slept)):
            result = svc.run(SIMPLE_PB, fresh=True)
        assert 295 < sum(slept) <= 301 and kernel.calls == 2
        assert result.reason != "external_resume_required"

    def test_without_a_state_repository_the_refusal_says_the_checkpoint_is_unconfirmed(
            self, caplog):
        cfg = _cfg(delay_minutes=0)                      # 無 repo 時以額度軸量得到的等待觸發
        cfg.token_guard.max_inprocess_wait_seconds = 60
        svc = AutoResumeService(_HaltingKernel(), cfg, quota_meter=_LongQuotaMeter())
        with caplog.at_level(logging.ERROR, logger="autoclaude"), \
                patch("autoclaude.core.services.auto_resume.time.sleep") as slept:
            result = svc.run(SIMPLE_PB, fresh=True)
        assert slept.call_count == 0 and result.reason == "external_resume_required"
        assert "未確認落地" in caplog.text, "沒有 state_repository 卻說 checkpoint 已落地 ⇒ 謊報"

    def test_a_far_scheduled_checkpoint_is_refused_before_the_kernel_runs(self):
        """第二處等待（checkpoint 續跑）同樣適用，且在 Kernel 啟動之前就返回。"""
        cfg = _cfg(delay_minutes=0, max_inprocess_wait_seconds=60)
        repo, kernel = InMemoryStateRepository(), _OkKernel()
        # 刻意不取整分鐘（10 分 17 秒）：若拒絕路徑誤把它改寫（向上取整到分鐘 ⇒ 11 分鐘），
        # 下面「checkpoint 時刻不變」的斷言就會偵測得到（取整到整分鐘的值不會留下可偵測的差）
        sched = (datetime.now() + timedelta(minutes=10, seconds=17)).isoformat(timespec="seconds")
        repo.save_checkpoint(_playbook_id(cfg), PlaybookCheckpoint(
            playbook_path=SIMPLE_PB, step_idx=1, step_id="T02", total_steps=2,
            scheduled_resume_at=sched))
        svc = AutoResumeService(kernel, cfg, state_repository=repo)
        with patch("autoclaude.core.services.auto_resume.time.sleep") as slept:
            result = svc.run(SIMPLE_PB, fresh=False)
        assert slept.call_count == 0 and kernel.starts == []
        assert result.success is False and result.halted is True
        assert result.reason == "external_resume_required"
        assert result.scheduled_resume_at == sched and result.completed_steps == 1
        assert repo.load_checkpoint(_playbook_id(cfg)).scheduled_resume_at == sched, (
            "checkpoint 自己的續跑時刻已是真相，拒絕時不得改寫它")
        assert svc.metrics["total_wakes"] == 0


class TestAnInterruptDuringTheWaitExitsGracefully:
    def test_the_interrupt_stops_the_wait_between_slices_and_returns_a_result(self):
        cfg = _cfg(delay_minutes=5, sleep_slice_seconds=60)    # 釘住片長：下面的 [60, 60] 才是算術
        kernel = _HaltingKernel()
        slept: list[float] = []
        svc = AutoResumeService(kernel, cfg, state_repository=InMemoryStateRepository(),
                                is_interrupted=lambda: len(slept) >= 2)
        with patch("autoclaude.core.services.auto_resume.time.sleep", slept.append):
            result = svc.run(SIMPLE_PB, fresh=True)
        assert slept == [60, 60], "中斷後必須在片與片之間停下，不得睡完整段"
        assert result.reason == "interrupted_during_wait" and result.success is False
        assert kernel.calls == 1, "被中斷後不得續跑"

    def test_without_an_interrupt_source_nothing_changes(self):
        cfg = _cfg(delay_minutes=1)
        kernel = _HaltingKernel()
        svc = AutoResumeService(kernel, cfg, state_repository=InMemoryStateRepository())
        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            svc.run(SIMPLE_PB, fresh=True)
        assert kernel.calls == 2


# ══════════════════════════════════════════════════════════════════════════════
# 三、接線鎖與設定邊界
# ══════════════════════════════════════════════════════════════════════════════
def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return ""


class TestWiringLocks:
    def test_auto_resume_never_calls_a_sleep_function_directly(self):
        """原始碼層鎖：兩處等待不得退回直接睡。只允許 `time.sleep` 以值的形態被注入
        給 `sliced_sleep(sleep=...)`——那是注入點，不是呼叫。"""
        tree = ast.parse(Path(auto_resume_mod.__file__).read_text(encoding="utf-8"))
        direct = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and (
            _dotted(n.func).endswith(".sleep") or _dotted(n.func) == "sleep")]
        assert direct == [], f"auto_resume.py 直接呼叫了 sleep（行 {direct}）"
        injected = {id(kw.value) for c in ast.walk(tree)
                    if isinstance(c, ast.Call) and _dotted(c.func) == "sliced_sleep"
                    for kw in c.keywords if kw.arg == "sleep"}
        refs = [n for n in ast.walk(tree) if _dotted(n) == "time.sleep"]
        assert injected, "auto_resume.py 沒有任何 sliced_sleep(sleep=...) 呼叫 ⇒ 等待被拿掉了"
        assert all(id(r) in injected for r in refs), "time.sleep 出現在注入點以外的地方"

    def test_the_real_clocks_are_what_the_service_injects(self):
        tree = ast.parse(Path(auto_resume_mod.__file__).read_text(encoding="utf-8"))
        kw = {k.arg: _dotted(k.value) for c in ast.walk(tree)
              if isinstance(c, ast.Call) and _dotted(c.func) == "sliced_sleep"
              for k in c.keywords}
        assert kw["wall"] == "time.time" and kw["mono"] == "time.monotonic"
        assert kw["sleep"] == "time.sleep", "測試靠 patch time.sleep 攔截，注入點須取呼叫當下屬性"

    def test_main_wires_the_hotkey_into_the_service(self):
        """機制蓋好沒接電：服務有中斷注入點，入口就必須把 hotkey.triggered 接上去（本鎖只守接線）。
        🔴 接線≠事件源有效：main() 目前沒有呼叫 hotkey.register()，全域熱鍵尚未註冊、triggered
        實際不會被設定——那是既存缺口，不在本鎖射程；本綠燈不得被讀成「按 ESC+F12 會中斷」。"""
        tree = ast.parse((PKG_DIR / "main.py").read_text(encoding="utf-8"))
        calls = [c for c in ast.walk(tree)
                 if isinstance(c, ast.Call) and _dotted(c.func) == "AutoResumeService"]
        assert len(calls) == 1
        kw = {k.arg: k.value for k in calls[0].keywords}
        assert "is_interrupted" in kw, "main.py 沒有把中斷來源交給 AutoResumeService"
        assert "hotkey" in ast.dump(kw["is_interrupted"])

    def test_utils_sliced_sleep_imports_nothing_from_core_or_infra(self):
        tree = ast.parse((PKG_DIR / "utils" / "sliced_sleep.py").read_text(encoding="utf-8"))
        mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not [m for m in mods if "autoclaude" in m or m.startswith(".")]


class TestTokenGuardSleepKnobs:
    def test_the_slice_default_matches_prd_section6_block9(self):
        """PRD §6 設定檔區塊 9「重置、休眠與喚醒」：SLEEP_SLICE_SECONDS=30。與 PRD 對齊的預設，
        釘死以免被悄悄改掉（改它＝改熱鍵／中斷的反應延遲上界）。"""
        assert TokenGuardConfig().sleep_slice_seconds == 30

    def test_the_defaults_that_deliberately_deviate_from_the_prd_are_pinned(self):
        """出廠值**刻意偏離** PRD §6 區塊 9 的兩個旋鈕（理由住 config.py 該欄註解）：
        tolerance 5（PRD 120）、max_inprocess 18000（PRD 7200）。釘死＝有人想把它們「改回對齊
        PRD」就得先回頭讀理由：120 讓容忍內的每片差累積成數小時晚醒；7200 讓真實額度等待（本機
        實測 54.5／189.6／224.2 分鐘）頻繁被拒絕，而本版沒有任何元件自動承接被拒絕的等待。"""
        cfg = TokenGuardConfig()
        assert cfg.clock_jump_tolerance_seconds == 5
        assert cfg.max_inprocess_wait_seconds == 18000
        assert cfg.max_inprocess_wait_seconds >= 224.2 * 60, "上限須蓋過本機實測最長的一次額度等待"

    @pytest.mark.parametrize("field,bad", [
        ("sleep_slice_seconds", 0), ("sleep_slice_seconds", 601),
        ("clock_jump_tolerance_seconds", 0), ("clock_jump_tolerance_seconds", 3601),
        ("max_inprocess_wait_seconds", 59), ("max_inprocess_wait_seconds", 86401),
    ])
    def test_out_of_range_values_are_rejected(self, field, bad):
        with pytest.raises(ValidationError):
            TokenGuardConfig(**{field: bad})

    @pytest.mark.parametrize("field,edge", [
        ("sleep_slice_seconds", 1), ("sleep_slice_seconds", 600),
        ("clock_jump_tolerance_seconds", 1), ("clock_jump_tolerance_seconds", 3600),
        ("max_inprocess_wait_seconds", 60), ("max_inprocess_wait_seconds", 86400),
    ])
    def test_the_range_edges_are_accepted(self, field, edge):
        assert getattr(TokenGuardConfig(**{field: edge}), field) == edge

    def test_a_per_step_override_may_not_smuggle_a_typo_of_the_new_knobs(self):
        """新欄位進了每步驟 token_guard 覆寫的白名單，拼錯仍被攔下。"""
        from autoclaude.models.playbook import PlaybookTask
        PlaybookTask(step_id="T1", name="n", prompt="p", token_guard={"sleep_slice_seconds": 30})
        with pytest.raises(ValidationError):
            PlaybookTask(step_id="T1", name="n", prompt="p", token_guard={"sleep_slice": 30})
