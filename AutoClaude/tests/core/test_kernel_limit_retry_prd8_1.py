"""PRD §8 列 1「非預期 429（推論端）」的 kernel 機制與接線：原地退避、重跑同一個 attempt。

決策（解析 Retry-After／上界／額度硬線／jitter）住 plugin，見
`tests/plugins/token_guard/test_limit_retry_prd8_1.py`；本檔守 kernel 的**機制**
與 `build_kernel` 的接線：

  (a) 429 帶短 Retry-After ⇒ 退避後重跑**同一個 attempt**：不消耗 attempt、不問 Brain、
      prompt 不被改寫；
  (b) 有界：第 1～5 次重試之後第 6 次仍撞線 ⇒ 既有 halt 路徑；重試預算是每個 step 一份、
      跨 attempt 累計；
  (c) 缺席／過長／額度已撞硬線 ⇒ 立即 halt、一次都不睡——既有行為逐位元不變；
  (d) 接線：`build_kernel` 把 plugin 的決策接進 kernel，睡法是分片休眠並讓 ESC+F12 能打斷。
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from autoclaude.core import wiring
from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.core.ports.observability import NullObservability
from autoclaude.core.ports.quota_meter import QuotaReading, quota_refusal
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin
from autoclaude.utils.config import AppConfig, TokenGuardConfig

_RA60 = "API Error: 429 rate limit exceeded. Retry-After: 60"
_NO_RA = "API Error: 429 rate limit exceeded"


class _ScriptedExecutor:
    """依腳本逐次回輸出；撞線輸出帶 `quota_refusal`（與真 PtyExecutor 同一個產生器）。"""

    def __init__(self, *script: str):
        self._script = list(script)
        self.calls: list[str] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        self.calls.append(prompt)
        text = self._script.pop(0) if len(self._script) > 1 else self._script[0]
        return ExecutionOutput(text=text, quota_refusal=quota_refusal(text))


class _Evaluator:
    """含 `BAD` 的輸出判失敗（一般失敗，不是撞線）；其餘成功。"""

    def evaluate(self, task, output):
        return ("bad output", "", 1) if "BAD" in output else (None, "", 0)


class _Brain:
    def __init__(self):
        self.calls = 0

    def decide_correction(self, **kwargs):
        self.calls += 1
        return None


class _Meter:
    def __init__(self, pct=None):
        self._r = None if pct is None else QuotaReading(pct, "five_hour", None)

    def read(self):
        return self._r

    def read_worst_pct(self):
        return self._r


def _playbook(max_retries: int = 2) -> Playbook:
    return Playbook(version="1.0", project="p", global_invariants=GlobalInvariants(
        max_retries_per_step=max_retries),
        tasks=[PlaybookTask(step_id="T01", name="n", prompt="do the thing")])


def _kernel(executor, *, meter=None, brain=None, with_gate=True, **cfg):
    cfg.setdefault("quota_halt_pct", 95.0)
    cfg.setdefault("quota_throttle_pct", 70.0)
    plugin = TokenGuardPlugin(TokenGuardConfig(**cfg), quota_meter=meter, rand=lambda: 0.0)
    bus = EventBus()
    bus.register(plugin)
    sleeps: list[float] = []
    kernel = PlaybookKernel(
        executor, _Evaluator(), bus=bus, brain=brain,
        **({"limit_retry": plugin.limit_retry_wait, "limit_sleep": sleeps.append}
           if with_gate else {}))
    return kernel, sleeps


# ══════════════════════════════════════════════════════════════════════════════
# (a) 重跑同一個 attempt
# ══════════════════════════════════════════════════════════════════════════════
def test_a_429_with_a_short_retry_after_is_retried_in_place_and_the_step_succeeds():
    ex = _ScriptedExecutor(_RA60, _RA60, "all good")
    kernel, sleeps = _kernel(ex)
    result = kernel.run(_playbook(max_retries=0))        # 一個正常 attempt 都不給
    assert result.success is True and result.halted is False
    assert len(ex.calls) == 3 and len(set(ex.calls)) == 1, "重跑必須送同一個 prompt"
    assert sleeps == [60.0, 60.0]
    assert result.completed_step_ids == ["T01"]


def test_the_retry_does_not_consume_a_normal_attempt():
    """max_retries=0 ⇒ 只有 attempt 0。重跑若吃掉 attempt 就會 max_retries_exhausted 升級。"""
    kernel, _ = _kernel(_ScriptedExecutor(_RA60, "ok"))
    assert kernel.run(_playbook(max_retries=0)).escalated is False


def test_the_brain_is_not_consulted_and_the_prompt_is_not_rewritten_for_a_retried_429():
    """429 不是這一步的錯：Brain 不該拿它去改寫 prompt（修前每次撞線都會多燒一次 Brain 呼叫）。"""
    brain = _Brain()
    ex = _ScriptedExecutor(_RA60, "ok")
    kernel, _ = _kernel(ex, brain=brain)
    assert kernel.run(_playbook()).success is True
    assert brain.calls == 0
    assert set(ex.calls) == {"do the thing"}


def test_each_retry_leaves_a_greppable_marker(caplog):
    kernel, _ = _kernel(_ScriptedExecutor(_RA60, "ok"))
    with caplog.at_level(logging.WARNING, logger="autoclaude.core.kernel"):
        kernel.run(_playbook())
    assert "LIMIT_RETRY" in caplog.text and "T01" in caplog.text and "60" in caplog.text


# ══════════════════════════════════════════════════════════════════════════════
# (b) 有界
# ══════════════════════════════════════════════════════════════════════════════
def test_after_five_retries_the_sixth_429_takes_the_existing_halt_path():
    """核心判準：Retry-After 60 ⇒ 第 1～5 次重試、第 6 次撞線即 halt。總共 6 次執行、5 次睡眠。"""
    ex = _ScriptedExecutor(_RA60)                      # 永遠撞線
    kernel, sleeps = _kernel(ex)
    result = kernel.run(_playbook())
    assert result.halted is True and result.success is False
    assert len(ex.calls) == 6
    assert len(sleeps) == 5
    assert result.completed_step_ids == []


def test_the_retry_budget_is_per_step_and_carries_across_attempts():
    """預算是每個 step 一份：中間夾一次一般失敗（消耗 attempt）也不會讓預算重置。"""
    ex = _ScriptedExecutor(_RA60, "BAD", _RA60, _RA60)
    kernel, sleeps = _kernel(ex, max_limit_retries=2)
    result = kernel.run(_playbook(max_retries=3))
    assert result.halted is True
    assert len(ex.calls) == 4 and len(sleeps) == 2


def test_the_budget_resets_for_the_next_step():
    pb = Playbook(version="1.0", project="p",
                  global_invariants=GlobalInvariants(max_retries_per_step=1),
                  tasks=[PlaybookTask(step_id="T01", name="a", prompt="p1"),
                         PlaybookTask(step_id="T02", name="b", prompt="p2")])
    ex = _ScriptedExecutor(_RA60, "ok", _RA60, "ok")
    kernel, sleeps = _kernel(ex, max_limit_retries=1)
    result = kernel.run(pb)
    assert result.success is True and len(sleeps) == 2


def test_the_knob_turns_the_whole_mechanism_off():
    ex = _ScriptedExecutor(_RA60)
    kernel, sleeps = _kernel(ex, max_limit_retries=0)
    assert kernel.run(_playbook()).halted is True
    assert len(ex.calls) == 1 and sleeps == []


# ══════════════════════════════════════════════════════════════════════════════
# (c) 既有行為逐位元不變
# ══════════════════════════════════════════════════════════════════════════════
def test_without_a_retry_after_the_halt_is_immediate_and_nothing_sleeps():
    ex = _ScriptedExecutor(_NO_RA)
    kernel, sleeps = _kernel(ex)
    result = kernel.run(_playbook())
    assert result.halted is True and len(ex.calls) == 1 and sleeps == []


def test_a_retry_after_beyond_the_bound_halts_immediately():
    ex = _ScriptedExecutor("429 rate limit exceeded retry-after: 301")
    kernel, sleeps = _kernel(ex)
    assert kernel.run(_playbook()).halted is True
    assert len(ex.calls) == 1 and sleeps == []


def test_a_quota_the_meter_says_is_exhausted_is_not_retried_even_with_a_short_retry_after():
    ex = _ScriptedExecutor(_RA60)
    kernel, sleeps = _kernel(ex, meter=_Meter(pct=96.0))
    assert kernel.run(_playbook()).halted is True
    assert len(ex.calls) == 1 and sleeps == []


def test_a_kernel_built_without_the_gate_behaves_exactly_as_before():
    """零附帶面：不注入 limit_retry（既有呼叫端與所有既有測試的形態）⇒ 位元級同修前。"""
    ex = _ScriptedExecutor(_RA60)
    kernel, sleeps = _kernel(ex, with_gate=False)
    result = kernel.run(_playbook())
    assert result.halted is True and len(ex.calls) == 1 and sleeps == []


def test_an_ordinary_failure_is_not_a_429_and_follows_the_normal_retry_path():
    ex = _ScriptedExecutor("BAD", "BAD", "BAD")
    kernel, sleeps = _kernel(ex)
    result = kernel.run(_playbook(max_retries=2))
    assert result.escalated is True and "max_retries_exhausted" in result.reason
    assert len(ex.calls) == 3 and sleeps == []


# ══════════════════════════════════════════════════════════════════════════════
# (d) 接線：build_kernel
# ══════════════════════════════════════════════════════════════════════════════
class _Hotkey:
    def __init__(self):
        self.triggered = False


def _built(tmp_path, monkeypatch, executor, hotkey=None, **tg):
    monkeypatch.setattr(wiring, "build_quota_meter", lambda *a, **k: _Meter())
    cfg = AppConfig(checkpoint_dir=str(tmp_path), token_guard=TokenGuardConfig(
        quota_halt_pct=95.0, quota_throttle_pct=70.0, **tg))
    return wiring.build_kernel(cfg, executor=executor, evaluator=_Evaluator(), hotkey=hotkey,
                               observability=NullObservability())


def test_build_kernel_wires_the_plugin_decision_into_the_kernel(tmp_path, monkeypatch):
    """拿掉 build_kernel 的接線 ⇒ 429+Retry-After 直接 halt、calls==1 ⇒ 紅。"""
    ex = _ScriptedExecutor(_RA60, "ok")
    kernel = _built(tmp_path, monkeypatch, ex)
    with patch("time.sleep") as slept:
        result = kernel.run(_playbook())
    assert result.success is True and len(ex.calls) == 2
    assert slept.call_count >= 2, "60 秒的等待必須切片（出廠每片 30 秒）而不是單次長睡"
    assert all(c.args[0] <= 30 for c in slept.call_args_list)


def test_the_backoff_sleeps_in_slices_so_esc_f12_can_cut_it_short(tmp_path, monkeypatch):
    """退避期間按 ESC+F12：睡眠在片與片之間收到中斷提早返回，之後 PRE_ATTEMPT 的 HotkeyPlugin
    veto ⇒ 升級中止，而不是把剩下的整段等待睡完再重打一次。"""
    hk = _Hotkey()
    ex = _ScriptedExecutor(_RA60, "ok")
    kernel = _built(tmp_path, monkeypatch, ex, hotkey=hk)

    def _press_during_the_first_slice(seconds):
        # 只在退避切片（≥1 秒）才模擬按鍵：Linux CI 上子行程輪詢以 time.sleep(0.x) 等待，
        # 若任何 sleep 都算按鍵，hotkey 會在第一片退避之前就於 pre_attempt 觸發，
        # 切片數變 0 而假紅（雲端 run 39284357343 實況）；按鍵語意＝「第一片退避睡到一半被按」。
        if float(seconds) >= 1.0:
            hk.triggered = True
    with patch("time.sleep", side_effect=_press_during_the_first_slice) as slept:
        result = kernel.run(_playbook())
    # 只數退避切片（≥1 秒）：Linux CI 上另有子行程輪詢以 time.sleep(0.x) 等待，
    # 會把 call_count 灌到 230（R213 雲端首跑實況），那不是第二片退避。
    slices = [c for c in slept.call_args_list if c.args and float(c.args[0]) >= 1.0]
    assert len(slices) == 1, f"按鍵之後不得再睡第二片：{[c.args[0] for c in slices]}"
    assert result.escalated is True and "ESC+F12" in result.reason
    assert len(ex.calls) == 1, "被中斷後不得再重打一次"


def test_the_wired_sleeper_honours_the_configured_slice_length(tmp_path, monkeypatch):
    kernel = _built(tmp_path, monkeypatch, _ScriptedExecutor(_RA60, "ok"), sleep_slice_seconds=10)
    with patch("time.sleep") as slept:
        kernel.run(_playbook())
    assert slept.call_count >= 6 and all(c.args[0] <= 10 for c in slept.call_args_list)


@pytest.mark.parametrize("name", ["limit_retry", "limit_sleep"])
def test_the_kernel_constructor_keeps_both_new_arguments_optional(name):
    import inspect
    param = inspect.signature(PlaybookKernel.__init__).parameters[name]
    assert param.default is None
