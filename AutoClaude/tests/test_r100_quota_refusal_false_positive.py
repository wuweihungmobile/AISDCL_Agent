"""R100 P2-C（PRD §8-1 的 AutoClaude 半）：執行器對 429 的**假陽性成功**。

立案（本輪逐行複驗 `PtyExecutor.execute()`，不是引述稽核）：`completed` 初值 True，
四個寫成 False 的地方全是 hotkey／interrupt／timeout／啟動失敗；CLI 撞 429 之後是
**正常退出** ⇒ 走 `if not pty.is_alive: break`（或 `line is None`）那兩條 break，
一個字都不動 completed ⇒ 回 `completed=True, exit_code=0`。而 `ShellEvaluator` 對
「無 expected_output_regex 且無 evaluator_command」的 task 恆回 `(None, "", 0)`＝成功
⇒ Kernel 記 ✓、ADVANCE。

本檔的紅綠自證（D-式對照組，不可省）：
  · `test_a_real_fake_cli_that_prints_429_and_exits_zero_is_not_completed`
    ——真的起一個子行程（`sys.executable <fake_cli.py>`），印 429 後 `sys.exit(0)`。
  · `test_removing_the_fix_restores_the_false_positive`
    ——把判準函式 monkeypatch 成修法前的行為（恆回「沒有跡證」）⇒ 必須退回
      `completed is True`。退不回去就表示上一格沒有在測它宣稱要測的東西。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.core.ports.quota_meter import (
    QUOTA_REFUSAL_PREFIX,
    is_quota_limit_text,
    quota_refusal,
)
from autoclaude.infra.adapters.pty_executor import PtyExecutor
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator
from autoclaude.models.playbook import Playbook, PlaybookTask
from autoclaude.utils.config import ClaudeConfig, LoopConfig, PlaybookConfig

# 逐字取自 Anthropic API／Claude Code CLI 真的會吐的形態（母體是 CLI 輸出，不是我們造的字）。
_REAL_429 = 'API Error: 429 {"type":"error","error":{"type":"rate_limit_error"}}'
_REAL_529 = 'API Error: 529 {"type":"error","error":{"type":"overloaded_error"}}'


def _fake_cli(tmp_path: Path, message: str, exit_code: int = 0) -> Path:
    """寫一支真的可執行的假 CLI：印 message 後以 exit_code 退出。"""
    script = tmp_path / "fake_claude_cli.py"
    script.write_text(
        "import sys\n"
        f"sys.stdout.write({message!r} + chr(10))\n"
        "sys.stdout.flush()\n"
        f"sys.exit({exit_code})\n",
        encoding="utf-8",
    )
    return script


def _executor(tmp_path: Path, script: Path) -> PtyExecutor:
    cfg = ClaudeConfig(
        command=sys.executable,
        extra_args=[str(script)],
        continue_flag="",        # 假 CLI 不吃 --continue
        output_format="",        # 純文字路徑：撞線訊息不是 JSON
    )
    return PtyExecutor(cfg, LoopConfig(), log_dir=str(tmp_path / "logs"))


# ══════════════════════════════════════════════════════════════════════════════
# 詞表：辨識詞表必須真的認得 429／529（發現波把這一格標成 partial）
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("text", [
    _REAL_429,
    _REAL_529,
    "Error code: 429",
    "HTTP 429 Too Many Requests",
    "429 rate limit exceeded, retry after 60s",
    "Claude usage limit reached",
])
def test_the_vocabulary_recognises_the_real_forms(text):
    assert is_quota_limit_text(text) is True, text


@pytest.mark.parametrize("text", [
    # 🔴 假紅控制組：這些都含「429」的字面，但沒有一個是撞線。
    # 判準若退回 `"429" in text`，本組會全部轉紅——而假紅會讓整道判準被關掉。
    'File "runner.py", line 429, in main',
    "4290 passed, 62 skipped",  # baseline-ok: 反例引文（引的是會誤命中的形態，不是基線值）
    "AssertionError: assert x == 429",
    "commit 429abc0 deadbeef",
    "",
])
def test_the_vocabulary_does_not_fire_on_look_alikes(text):
    assert is_quota_limit_text(text) is False, text


def test_the_refusal_prefix_is_recognised_by_the_same_judgement():
    # 這一格是「執行器 → TokenGuardPlugin.evaluate_quota」那條縫本身：plugin 只讀
    # failure_reason，前綴若不含任何撞線字彙，plugin 結構上看不見執行器的判定。
    assert is_quota_limit_text(QUOTA_REFUSAL_PREFIX) is True


# ══════════════════════════════════════════════════════════════════════════════
# 假陽性止血：真子行程，輸出含 429、exit code 為 0
# ══════════════════════════════════════════════════════════════════════════════
def test_a_real_fake_cli_that_prints_429_and_exits_zero_is_not_completed(tmp_path):
    ex = _executor(tmp_path, _fake_cli(tmp_path, _REAL_429, exit_code=0))
    out = ex.execute("hi", maintain_context=False, timeout=30, label="r100c")
    assert "429" in out.text                    # 前提：輸出真的到手了
    assert out.completed is not True            # 任務書逐字要求的斷言方向
    assert out.exit_code != 0
    assert QUOTA_REFUSAL_PREFIX in out.quota_refusal


def test_removing_the_fix_restores_the_false_positive(tmp_path, monkeypatch):
    # 紅綠自證的對照組：把判準退回修法前的行為（執行器不看輸出內容）。
    monkeypatch.setattr(
        "autoclaude.infra.adapters.pty_executor.quota_refusal", lambda _t: "")
    ex = _executor(tmp_path, _fake_cli(tmp_path, _REAL_429, exit_code=0))
    out = ex.execute("hi", maintain_context=False, timeout=30, label="r100c-ctrl")
    assert "429" in out.text
    assert out.completed is True                # ← 這就是被修掉的那個假陽性
    assert out.quota_refusal == ""


def test_a_clean_cli_run_is_still_completed(tmp_path):
    # 控制組：沒有撞線跡證的正常輸出**不得**被判成拒工（本修法只准更嚴，不准更寬）。
    ex = _executor(tmp_path, _fake_cli(tmp_path, "all good, 3 passed", exit_code=0))
    out = ex.execute("hi", maintain_context=False, timeout=30, label="r100c-ok")
    assert out.completed is True
    assert out.quota_refusal == ""


# ══════════════════════════════════════════════════════════════════════════════
# 第二半：Kernel 不得再問 evaluator（否則 ShellEvaluator 會把撞線判成 ✓）
# ══════════════════════════════════════════════════════════════════════════════
class _RefusingExecutor:
    def __init__(self, refusal: str):
        self._refusal = refusal
        self.calls = 0

    def execute(self, prompt, **_kw):
        self.calls += 1
        return ExecutionOutput(text=_REAL_429, exit_code=1, completed=False,
                               quota_refusal=self._refusal)

    def send_interrupt(self, reason: str = "") -> bool:
        return True


def _one_step_playbook() -> Playbook:
    return Playbook(
        version="1.0", project="r100c", global_goal="g",
        tasks=[PlaybookTask(step_id="S1", name="one", prompt="do it", max_retries=0)],
    )


def _run(executor) -> object:
    kernel = PlaybookKernel(executor=executor,
                            evaluator=ShellEvaluator(PlaybookConfig()),
                            bus=EventBus())
    return kernel.run(_one_step_playbook())


def test_kernel_does_not_mark_a_refused_step_as_success():
    # 這個 task 既無 expected_output_regex 也無 evaluator_command
    # ⇒ 修法前 ShellEvaluator 恆回成功，撞線那一步被記成 ✓。
    result = _run(_RefusingExecutor(quota_refusal(_REAL_429)))
    assert result.completed_step_ids == []
    assert "S1" not in result.completed_step_ids


def test_kernel_still_trusts_the_evaluator_when_there_is_no_refusal():
    # 對照組：沒有拒工跡證時，evaluator 仍是唯一裁判（零退化）。
    result = _run(_RefusingExecutor(""))
    assert result.completed_step_ids == ["S1"]
