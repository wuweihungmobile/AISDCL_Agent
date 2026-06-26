"""Phase 4 Facade 切換整合測試（SD_Improving_02.md v1.1 §2.6）。

驗證：
  - build_kernel() 工廠成功組裝 Kernel + 12 Plugin
  - Kernel 可使用 13 個 equivalence fixture 跑通（dry_run / fake executor 模式）
  - 12 Plugin 全部正確註冊到 EventBus
  - GotoCounterPlugin <-> CheckpointPlugin 整合（Gap-042/048）

注意：
  - 此整合測試驗證「Kernel 路徑能運作」，不要求 byte-level 等價於舊 PlaybookRunner
  - byte-level 等價驗證留待 Phase 5 末段測試遷移完成後執行
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.core.wiring import build_kernel
from autoclaude.models.playbook import Playbook
from autoclaude.utils.config import AppConfig

FIXTURES_DIR = Path(__file__).parent.parent / "equivalence" / "fixtures"

GOLDEN_PLAYBOOKS = [
    "01_simple_2_step.yaml",
    "02_with_correction.yaml",
    "03_with_mutation.yaml",
    "04_token_halt_resume.yaml",
    "05_evolution_inject.yaml",
    "06_goal_synthesis.yaml",
    "07_goto_step.yaml",
    "08_skip_to.yaml",
    "09_conditional.yaml",
    "10_full_e2e_dry_run.yaml",
    "11_goto_counter_token_halt.yaml",
    "12_evolution_counter_esc_f12.yaml",
    "13_max_goto_per_step_override.yaml",
]


class _RegexMatchingExecutor:
    """從 PlaybookTask.expected_output_regex 反推應該回傳的字串。"""
    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        # label 是 step_id；prompt 含 prompt 本體；我們從 prompt 中嘗試找 [XYZ_DONE] 等 keyword
        # 簡化：尋找 prompt 內的 \[KEYWORD\] 模式並回傳該 keyword
        m = re.search(r'\[([A-Z][A-Z0-9_]+)\]', prompt)
        if m:
            return ExecutionOutput(text=f"[{m.group(1)}]")
        return ExecutionOutput(text="[OK]")


class _PassThroughEvaluator:
    """簡化 evaluator：只比對 expected_output_regex。"""
    def evaluate(self, task, output):
        if task.expected_output_regex:
            if not re.search(task.expected_output_regex, output):
                return f"未符合 regex: {task.expected_output_regex}", "", 0
        return None, "", 0


def _load_playbook(name: str) -> Playbook:
    p = FIXTURES_DIR / name
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Playbook(**raw)


def _make_kernel(cfg: AppConfig) -> PlaybookKernel:
    return build_kernel(
        cfg,
        executor=_RegexMatchingExecutor(),
        evaluator=_PassThroughEvaluator(),
        brain=None,
        hotkey=MagicMock(triggered=False),
        minimax_client=None,
    )


# ──────────────────────────────────────────────
class TestBuildKernel:
    def test_build_kernel_returns_kernel_instance(self, tmp_path):
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        kernel = _make_kernel(cfg)
        assert isinstance(kernel, PlaybookKernel)

    def test_kernel_has_event_bus(self, tmp_path):
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        kernel = _make_kernel(cfg)
        assert kernel.bus is not None

    def test_all_12_plugins_registered(self, tmp_path):
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        kernel = _make_kernel(cfg)
        # 收集所有 phase 訂閱者，去重
        all_plugins = set()
        for hooks in kernel.bus._subscribers.values():
            for h in hooks:
                all_plugins.add(h.name())
        # 12 個 Plugin 應該都在
        expected = {
            "pre_run_validator", "hotkey", "cross_step_validator",
            "token_guard", "global_goal_anchor", "notification",
            "knowledge_base", "goal_synthesis", "convergence",
            "evolution", "goto_counter", "checkpoint",
        }
        assert expected.issubset(all_plugins), \
            f"缺少 plugin: {expected - all_plugins}"

    def test_plugin_priority_ordering(self, tmp_path):
        """驗證 priority 約定表（5/10/15/30/35/50×3/65/70/85/90）。"""
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        kernel = _make_kernel(cfg)
        priorities = {}
        for hooks in kernel.bus._subscribers.values():
            for h in hooks:
                priorities[h.name()] = h.priority()
        assert priorities["pre_run_validator"] == 5
        assert priorities["hotkey"] == 10
        assert priorities["cross_step_validator"] == 15
        assert priorities["token_guard"] == 30
        assert priorities["global_goal_anchor"] == 35
        assert priorities["convergence"] == 65
        assert priorities["evolution"] == 70
        assert priorities["goto_counter"] == 85
        assert priorities["checkpoint"] == 90


# ──────────────────────────────────────────────
class TestKernelRunsAllFixtures:
    @pytest.mark.parametrize("fixture_name", GOLDEN_PLAYBOOKS)
    def test_fixture_can_run_through_kernel(self, fixture_name, tmp_path):
        """每個 fixture 應該能透過 Kernel + 12 Plugin 路徑跑通。"""
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        cfg.token_guard.enabled = False  # 測試不觸發 token guard
        cfg.notification.enabled = False
        kernel = _make_kernel(cfg)

        playbook = _load_playbook(fixture_name)
        result = kernel.run(playbook)

        assert isinstance(result, KernelResult)
        assert result.success is True, \
            f"fixture {fixture_name} 失敗: reason={result.reason}, log={result.step_log}"

    def test_completed_step_ids_match_total(self, tmp_path):
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        cfg.token_guard.enabled = False
        cfg.notification.enabled = False
        kernel = _make_kernel(cfg)

        playbook = _load_playbook("01_simple_2_step.yaml")
        result = kernel.run(playbook)
        assert len(result.completed_step_ids) == len(playbook.tasks)
        assert result.completed_step_ids == [t.step_id for t in playbook.tasks]


# ──────────────────────────────────────────────
class TestGotoCounterIntegration:
    """驗證 GotoCounterPlugin <-> CheckpointPlugin 整合（Gap-042/048）。"""

    def test_pre_run_loads_counter_from_checkpoint(self, tmp_path):
        from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint

        # 預先寫入帶計數器的 checkpoint
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        cp = PlaybookCheckpoint(
            playbook_path="x.yaml", step_idx=0, step_id="T01", total_steps=2,
            goto_counter={"T01": 2},
            step_evolution_counter={"T03": 1},
        )
        mgr.save(cp, "x.yaml")

        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        kernel = _make_kernel(cfg)

        # 取得 GotoCounterPlugin 並透過 CheckpointPlugin 觸發 PRE_RUN 還原
        from autoclaude.core.hookspec import HookContext, KernelPhase
        playbook = _load_playbook("01_simple_2_step.yaml")
        kernel.bus.emit(HookContext(
            phase=KernelPhase.PRE_RUN, playbook=playbook,
            payload={"playbook_path": "x.yaml"},
        ))
        # GotoCounterPlugin 應已被 CheckpointPlugin push 還原
        gc_plugin = kernel.bus.get_plugin("goto_counter")
        snap = gc_plugin.snapshot()
        assert snap.goto_counter == {"T01": 2}
        assert snap.step_evolution_counter == {"T03": 1}
