"""DEF-13-004（AutoSDD_improving_13 W-13-2）：演化版重載 L5 signoff 守界。

成熟度量表 L5 要求自演化的「範圍·預算·終止由硬閘＋人工 signoff 守界」。
Gap-012-D 既有自動重載已具預算（max_evolutions）/終止（escalation）硬閘，但
**缺人工 signoff**：演化版直接 auto-reload。本測試鎖定新增之 flag-gated signoff 閘：

  - require_evolution_signoff=False（預設）→ 維持自動重載（零退化）
  - require_evolution_signoff=True → 重載前須過 evolution_approver 核可；
    approver 缺失/拒絕/例外一律 fail-closed 停機不重載

對齊 goal_decomposer signoff 硬閘 + MinimaxConfig.enable_kernel_brain flag-gate 前例。
測試骨架鏡像 tests/test_gap012.py::TestEvolvedPlaybookPath。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from autoclaude.execution.playbook_runner import PlaybookResult, PlaybookRunner
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.utils.config import AppConfig


def _make_runner(*, require_signoff: bool, approver=None) -> PlaybookRunner:
    cfg = AppConfig()
    cfg.playbook.require_evolution_signoff = require_signoff
    hotkey = MagicMock()
    hotkey.triggered = False
    return PlaybookRunner(
        cfg, MagicMock(), hotkey, dry_run=True,
        checkpoint_mgr=MagicMock(), evolution_approver=approver,
    )


def _make_playbook(*step_ids: str) -> Playbook:
    return Playbook(
        project="TestProj",
        global_invariants=GlobalInvariants(max_retries_per_step=3),
        tasks=[PlaybookTask(step_id=s, name=s, prompt=f"do {s}",
                            expected_output_regex=f"done-{s}") for s in step_ids],
    )


_EVOLVED = "evolved_fake.yaml"


def _run_with_evolution(runner: PlaybookRunner):
    """跑一個第一輪觸發演化、演化版會成功的 run()，回傳 (result, call_seq)。"""
    original = _make_playbook("T01")
    evolved = _make_playbook("T00_PRE", "T01")
    call_seq: list[str] = []

    def fake_load_playbook(path):
        call_seq.append(path)
        return evolved if path == _EVOLVED else original

    def fake_run_steps(playbook, path, *a, **kw):
        if path == _EVOLVED:
            return PlaybookResult(True, 2, 2, "done")
        return PlaybookResult(False, 0, 1, "escalation",
                              evolved_playbook_path=_EVOLVED)

    with patch.object(runner, "_load_playbook", side_effect=fake_load_playbook), \
         patch.object(runner, "_validate_evaluator_commands"), \
         patch.object(runner, "_detect_workflow", return_value=MagicMock()), \
         patch.object(runner, "_resolve_start", return_value=(0, [], True, None)), \
         patch.object(runner, "_run_steps", side_effect=fake_run_steps), \
         patch.object(runner, "_notify"), \
         patch.object(runner, "_hotkey") as mock_hotkey:
        mock_hotkey.register = MagicMock()
        mock_hotkey.unregister = MagicMock()
        runner._hotkey = mock_hotkey
        result = runner.run("original.yaml")
    return result, call_seq


class TestEvolutionSignoffGate:
    def test_default_flag_off_auto_reloads(self):
        """預設 require_evolution_signoff=False → 維持自動重載（零退化）。"""
        runner = _make_runner(require_signoff=False)
        result, call_seq = _run_with_evolution(runner)
        assert result.success is True
        assert call_seq == ["original.yaml", _EVOLVED]   # 有重載

    def test_signoff_required_but_no_approver_denies(self):
        """flag=True 但未注入 approver → fail-closed 停機不重載。"""
        runner = _make_runner(require_signoff=True, approver=None)
        result, call_seq = _run_with_evolution(runner)
        assert result.success is False                    # 回報 escalation 結果
        assert result.evolved_playbook_path == _EVOLVED
        assert call_seq == ["original.yaml"]              # 未重載

    def test_signoff_denied_blocks_reload(self):
        """approver 回傳 False → 停機不重載，且 approver 收到 (count=1, path)。"""
        calls: list[tuple] = []

        def deny(count, path):
            calls.append((count, path))
            return False

        runner = _make_runner(require_signoff=True, approver=deny)
        result, call_seq = _run_with_evolution(runner)
        assert result.success is False
        assert call_seq == ["original.yaml"]              # 未重載
        assert calls == [(1, _EVOLVED)]                   # 核可者被諮詢一次

    def test_signoff_granted_allows_reload(self):
        """approver 回傳 True → 放行重載（同預設自動行為），approver 被諮詢。"""
        calls: list[tuple] = []

        def approve(count, path):
            calls.append((count, path))
            return True

        runner = _make_runner(require_signoff=True, approver=approve)
        result, call_seq = _run_with_evolution(runner)
        assert result.success is True
        assert call_seq == ["original.yaml", _EVOLVED]    # 有重載
        assert calls == [(1, _EVOLVED)]

    def test_approver_exception_is_fail_closed(self):
        """approver 拋例外 → fail-closed 停機不重載（不外溢例外）。"""
        def boom(count, path):
            raise RuntimeError("approver 服務中斷")

        runner = _make_runner(require_signoff=True, approver=boom)
        result, call_seq = _run_with_evolution(runner)
        assert result.success is False
        assert call_seq == ["original.yaml"]              # 未重載


class TestSignoffGrantedHelper:
    """_evolution_signoff_granted 四分支單元（與整合測試互補）。"""

    def test_flag_off_always_grants(self):
        runner = _make_runner(require_signoff=False, approver=lambda c, p: False)
        # flag off → 不諮詢 approver，永遠放行
        assert runner._evolution_signoff_granted(1, "x.yaml") is True

    def test_flag_on_no_approver_denies(self):
        runner = _make_runner(require_signoff=True, approver=None)
        assert runner._evolution_signoff_granted(1, "x.yaml") is False

    def test_flag_on_approver_true_grants(self):
        runner = _make_runner(require_signoff=True, approver=lambda c, p: True)
        assert runner._evolution_signoff_granted(2, "x.yaml") is True

    def test_flag_on_approver_false_denies(self):
        runner = _make_runner(require_signoff=True, approver=lambda c, p: False)
        assert runner._evolution_signoff_granted(2, "x.yaml") is False
