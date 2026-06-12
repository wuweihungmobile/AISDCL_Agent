"""W7（AutoSDD_improving_01 §3.3/§4）：SDD bridge 端到端煙霧測試。

compile-then-run 全鏈路：
  規格 + FSM 凍結狀態 → sdd_compile CLI → 標準 playbook YAML →
  Playbook 載入 → Kernel（真 SddGovernancePlugin + 真 SddToPlaybookAdapter）執行

驗證 wiring：sdd_governance 在 _REGISTER_ORDER 的 45 位插槽 +
wire_plugins_with_registry 真組裝。
"""
from __future__ import annotations

import re

import yaml

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.core.wiring import _REGISTER_ORDER, wire_plugins_with_registry
from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter
from autoclaude.models.playbook import Playbook
from autoclaude.plugins.sdd_governance_plugin import SddGovernancePlugin
from autoclaude.tools.sdd_compile import main as sdd_compile_main
from autoclaude.utils.config import AppConfig
from tests.infra.test_sdd_to_playbook_adapter import _write_fsm_state, _write_spec


class _RegexExecutor:
    """依步驟 regex 合成可通過輸出（煙霧用，不啟動真實 PTY）。"""

    _OUTPUT_BY_STEP = {
        "sdd-brownfield-at-001-1-1": "HTTP 201 Created",
        "sdd-brownfield-at-001-1-2": "錯誤：餘額不足",
        "sdd-brownfield-at-002-1-1": "3 PASSED in 1.2s",
    }

    def execute(self, prompt, *, maintain_context=True, timeout=600, label=""):
        return ExecutionOutput(text=self._OUTPUT_BY_STEP.get(label, "OK"))


class _RegexOnlyEvaluator:
    """只跑 regex 雙重驗證第一層（evaluator_command 留給真實環境）。"""

    def evaluate(self, task, output) -> tuple[str | None, str, int]:
        if task.expected_output_regex and not re.search(
                task.expected_output_regex, output):
            return f"regex 不符: {task.expected_output_regex}", output[-200:], 1
        return None, "", 0


def _compile(tmp_path):
    spec_dir = _write_spec(tmp_path)
    _write_fsm_state(tmp_path)
    out = tmp_path / "sdd_playbook.yaml"
    rc = sdd_compile_main(["--spec-dir", str(spec_dir), "--out", str(out)])
    assert rc == 0
    return Playbook.model_validate(yaml.safe_load(out.read_text(encoding="utf-8")))


class TestBridgeEndToEnd:
    def test_compile_then_run_full_chain_success(self, tmp_path):
        pb = _compile(tmp_path)
        assert pb.workflow_path  # W4↔W6 接縫：規格目錄錨點必須存在
        plugin = SddGovernancePlugin(spec_source=SddToPlaybookAdapter())
        bus = EventBus()
        bus.register(plugin)
        kernel = PlaybookKernel(_RegexExecutor(), _RegexOnlyEvaluator(), bus=bus)
        result = kernel.run(pb)
        assert result.success is True
        assert result.completed_steps == 3
        # plugin 真的啟用且載到凍結規格
        snap = plugin.snapshot()
        assert snap["spec_digest"] and snap["spec_digest"].startswith("sha256:")
        assert snap["contract_violations"] == []

    def test_unfrozen_spec_blocks_run_at_pre_run(self, tmp_path):
        pb = _compile(tmp_path)
        # 凍結狀態檔事後被退回 SPEC_DRAFTING（規格先行硬閘攻防）
        _write_fsm_state(tmp_path, current_state="SPEC_DRAFTING")
        plugin = SddGovernancePlugin(spec_source=SddToPlaybookAdapter())
        bus = EventBus()
        bus.register(plugin)
        kernel = PlaybookKernel(_RegexExecutor(), _RegexOnlyEvaluator(), bus=bus)
        result = kernel.run(pb)
        assert result.success is False
        assert result.reason == "vetoed_at_pre_run"
        assert any("SDD-VIOLATION[SPEC_NOT_FROZEN]" in r
                   for r in result.veto_reasons)
        assert result.completed_steps == 0

    def test_non_sdd_playbook_unaffected_by_plugin(self, tmp_path):
        pb = _compile(tmp_path)
        plain = Playbook(project="plain", workflow_type="auto",
                         tasks=[t for t in pb.tasks])
        plugin = SddGovernancePlugin(spec_source=SddToPlaybookAdapter())
        bus = EventBus()
        bus.register(plugin)
        kernel = PlaybookKernel(_RegexExecutor(), _RegexOnlyEvaluator(), bus=bus)
        result = kernel.run(plain)
        assert result.success is True
        assert plugin.snapshot()["spec_digest"] is None  # 全程 no-op


class TestWiringRegistration:
    def test_register_order_slot_45(self):
        order = list(_REGISTER_ORDER)
        assert order.index("playbook_persistence") < order.index("sdd_governance") \
            < order.index("fast_path")

    def test_wire_plugins_builds_sdd_governance(self):
        bus = EventBus()
        plugins = wire_plugins_with_registry(bus, config=AppConfig())
        sdd = plugins["sdd_governance"]
        assert isinstance(sdd, SddGovernancePlugin)
        assert sdd.priority() == 45
        # 已註冊進 EventBus（get_plugin 為既有公開查詢 API）
        assert bus.get_plugin("sdd_governance") is sdd
