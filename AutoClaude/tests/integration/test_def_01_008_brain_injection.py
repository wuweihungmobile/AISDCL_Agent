"""DEF-01-008（P1）flag-gated brain 注入 —— 整合驗證（AutoSDD_improving_03 W1）。

驗證意圖（WHY，非僅 WHAT）：
  DEF-01-008 = production 入口 `main.py` 呼叫 `build_kernel` 未傳 `brain=`，致
  `kernel.decide_correction`（kernel.py:198）與 `SddGovernancePlugin.decide_escalation`
  （sdd_governance_plugin.py:198）兩條 brain 消費路徑在正式 CLI 為**死碼**。
  improving_03 §2.2 採 **flag-gated 落地**：`MinimaxConfig.enable_kernel_brain`（預設
  False）為唯一開關。本測試鎖定三件不可回退的契約：
    (1) **預設零退化**：flag 預設 False；brain=None 時兩消費者皆 None（= 當前 production 行為）。
    (2) **flag-on 雙效耦合**：注入 brain 時，同一 brain 必須同時抵達 kernel 與 SddGovernance
        （improving_03 §2.1 開檔實證之 wiring.py:307/315 雙下發）。
    (3) **死碼轉活 + 新語意鎖定**：brain 存在時 correction 諮詢可達；Minimax API 故障
        （decide_correction→None）觸發 ESCALATE（§2.1 新行為，operator 須知悉）。
"""
from __future__ import annotations

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.brain import CorrectionResult
from autoclaude.core.wiring import _build_plugin_set, build_kernel
from autoclaude.decision.minimax_client import MinimaxClient
from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter
from autoclaude.plugins.sdd_governance_plugin import SddGovernancePlugin
from autoclaude.utils.config import AppConfig, MinimaxConfig
from tests.plugins._template import (
    FakeBrain,
    FakeEvaluator,
    FakeExecutor,
    make_ctx,
    sample_playbook,
    sample_task,
)
from autoclaude.core.hookspec import KernelPhase


def _cfg(tmp_path) -> AppConfig:
    cfg = AppConfig()
    cfg.checkpoint_dir = str(tmp_path / "ckpts")
    return cfg


class _SpyBrain:
    """記錄 decide_escalation / decide_correction 是否被諮詢。"""

    def __init__(self):
        self.escalation_calls: list[dict] = []
        self.correction_calls: list[dict] = []

    def decide_escalation(self, **kwargs):
        self.escalation_calls.append(kwargs)
        return None

    def decide_correction(self, **kwargs):
        self.correction_calls.append(kwargs)
        return None


# ─────────────────────────────────────────────────────────────
# 契約 (1)：預設零退化
# ─────────────────────────────────────────────────────────────
class TestZeroRegressionDefault:
    def test_flag_default_is_false(self):
        """WHY：預設必須 False，否則所有既有部署在升級後行為突變（破零退化）。"""
        assert MinimaxConfig().enable_kernel_brain is False

    def test_brain_none_reaches_neither_consumer(self, tmp_path):
        """WHY：flag-off（brain=None）時，kernel 與 SddGovernance 皆 None
        ＝當前 production 死碼狀態，證明預設路徑零行為變更。"""
        cfg = _cfg(tmp_path)
        plugins = _build_plugin_set(cfg, brain=None, state_repository=None)
        assert plugins["sdd_governance"]._brain is None

        kernel = build_kernel(
            cfg, executor=FakeExecutor(), evaluator=FakeEvaluator(), brain=None,
        )
        assert kernel._brain is None


# ─────────────────────────────────────────────────────────────
# 契約 (2)：flag-on 雙效耦合（同一 brain 同時抵達兩消費者）
# ─────────────────────────────────────────────────────────────
class TestBrainInjectedToBothConsumers:
    def test_same_brain_reaches_kernel_and_governance(self, tmp_path):
        """WHY：improving_03 §2.1 實證 build_kernel 把 brain 同時下發 kernel(:315)
        與 SddGovernancePlugin(:307→202)；此耦合是 flag-on 修死碼的核心，也是
        flag-off 之所以能零退化的同一條線。"""
        cfg = _cfg(tmp_path)
        brain = FakeBrain()
        plugins = _build_plugin_set(cfg, brain=brain, state_repository=None)
        assert plugins["sdd_governance"]._brain is brain

        kernel = build_kernel(
            cfg, executor=FakeExecutor(), evaluator=FakeEvaluator(), brain=brain,
        )
        assert kernel._brain is brain


# ─────────────────────────────────────────────────────────────
# 契約：main.py flag→brain 映射（複刻 main.py 之構造式，鎖定 config→kernel 全鏈）
# ─────────────────────────────────────────────────────────────
class TestMainFlagMapping:
    @staticmethod
    def _brain_from_cfg(cfg: AppConfig):
        """複刻 main.py 之 flag-gated 構造（main.py ~:96）。"""
        client = MinimaxClient(api_key="dummy-key", base_url="http://x", model="m", timeout=1)
        return MinimaxBrainAdapter(client) if cfg.minimax.enable_kernel_brain else None

    def test_flag_true_builds_adapter_and_reaches_kernel(self, tmp_path):
        cfg = _cfg(tmp_path)
        cfg.minimax.enable_kernel_brain = True
        brain = self._brain_from_cfg(cfg)
        assert isinstance(brain, MinimaxBrainAdapter)
        kernel = build_kernel(
            cfg, executor=FakeExecutor(), evaluator=FakeEvaluator(), brain=brain,
        )
        assert isinstance(kernel._brain, MinimaxBrainAdapter)

    def test_flag_false_yields_none(self, tmp_path):
        cfg = _cfg(tmp_path)
        cfg.minimax.enable_kernel_brain = False
        assert self._brain_from_cfg(cfg) is None


# ─────────────────────────────────────────────────────────────
# 契約 (3)：死碼轉活 + 新語意鎖定
# ─────────────────────────────────────────────────────────────
class TestDeadCodeBecomesReachable:
    def test_kernel_correction_consulted_when_brain_present(self):
        """WHY：brain 存在時 kernel.decide_correction 必須被諮詢（死碼轉活，kernel 側）。"""
        brain = FakeBrain(next_decisions=[CorrectionResult(correction_prompt="fix", reasoning="r")])
        evaluator = FakeEvaluator(next_results=[("regex 不符", "boom", 1), (None, "", 0)])
        kernel = PlaybookKernel(
            executor=FakeExecutor(), evaluator=evaluator, bus=EventBus(), brain=brain,
        )
        result = kernel.run(sample_playbook(n_tasks=1))
        assert result.success
        assert any(c.name == "decide_correction" for c in brain.calls)

    def test_api_failure_escalates(self):
        """WHY：decide_correction 回 None（Minimax API 故障）→ ESCALATE。
        此為 flag-on 後新增語意（brain=None 時不存在），須被測試鎖定（§2.1）。"""
        brain = FakeBrain(next_decisions=[])  # decide_correction → None
        evaluator = FakeEvaluator(next_results=[("regex 不符", "boom", 1)])
        kernel = PlaybookKernel(
            executor=FakeExecutor(), evaluator=evaluator, bus=EventBus(), brain=brain,
        )
        result = kernel.run(sample_playbook(n_tasks=1))
        assert not result.success
        assert any(c.name == "decide_correction" for c in brain.calls)

    def test_governance_escalation_consulted_when_brain_present(self):
        """WHY：brain 存在 + 違反達 threshold → SddGovernance.decide_escalation 可達
        （死碼轉活，governance 側）。"""
        spy = _SpyBrain()
        plugin = SddGovernancePlugin(brain=spy, escalation_threshold=2)
        plugin._active = True
        plugin._gate_of_step = {"T01": "SCG-4"}
        plugin._state["contract_violations"] = [
            {"step_id": "T01"}, {"step_id": "T01"},
        ]
        ctx = make_ctx(phase=KernelPhase.ON_FAILURE, task=sample_task("T01"))
        plugin.on_event(ctx)
        assert len(spy.escalation_calls) == 1

    def test_governance_no_escalation_when_brain_none(self):
        """WHY：flag-off（brain=None）即使達 threshold 也不諮詢、不崩潰（零退化保證）。"""
        plugin = SddGovernancePlugin(brain=None, escalation_threshold=2)
        plugin._active = True
        plugin._gate_of_step = {"T01": "SCG-4"}
        plugin._state["contract_violations"] = [
            {"step_id": "T01"}, {"step_id": "T01"},
        ]
        ctx = make_ctx(phase=KernelPhase.ON_FAILURE, task=sample_task("T01"))
        # 不得拋例外，且無諮詢（純 return）
        assert plugin.on_event(ctx) is None
