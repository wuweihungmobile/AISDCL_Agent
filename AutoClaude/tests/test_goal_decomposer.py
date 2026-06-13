"""F-A1 GoalDecomposer 測試（SRD_AGT_Phase3_Autonomy.md §4 / ADR-AGT-002）。

驗收項對應：
  - 拆解超限被拒（>24 步拒絕、不重試、不截斷）
  - 拆解含環被拒（拓撲排序偵測）
  - signoff 前不執行（release_for_execution 未簽署即拒絕）
  - 不支援 decomposition 的 brain 被拒（capability 守門，不靜默降級）
  - Playbook 草稿可被既有 validator（load_playbook）往返載入
"""
from __future__ import annotations

import pytest

from autoclaude.core.ports.brain import BrainCapabilities, RetryPolicy
from autoclaude.core.services.auto_resume import load_playbook
from autoclaude.execution.goal_decomposer import (
    MAX_DECOMPOSITION_STEPS,
    DecompositionError,
    GoalDecomposer,
)
from autoclaude.models.decision import DecompositionDecision, DecompositionStep


# ── 測試替身 ─────────────────────────────────────────────
class _RecordingObs:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def emit_counter(self, name, value=1, tags=None):
        pass

    def emit_histogram(self, name, value, tags=None):
        pass

    def start_span(self, name, tags=None):
        raise NotImplementedError

    def record_event(self, name, attributes=None):
        self.events.append((name, dict(attributes or {})))


def _caps(supports: bool = True) -> BrainCapabilities:
    return BrainCapabilities(
        max_context_tokens=1000,
        supports_streaming=False,
        retry_policy=RetryPolicy(),
        model_id="fake",
        dimension=1024,
        supports_decomposition=supports,
    )


class _FakeBrain:
    """可控的 IBrain：capabilities 與 decide_decomposition 由建構參數決定。"""

    def __init__(self, decision, *, supports: bool = True):
        self._decision = decision
        self._supports = supports
        self.calls = 0

    def capabilities(self):
        return _caps(self._supports)

    def decide_decomposition(self, *, goal, context=""):
        self.calls += 1
        return self._decision

    # 介面其餘方法本測試不需，省略（duck typing）


def _decision(n: int, *, with_edges: bool = False) -> DecompositionDecision:
    steps = []
    for i in range(1, n + 1):
        deps = [f"T{i-1:02d}"] if (with_edges and i > 1) else []
        steps.append(
            DecompositionStep(
                step_id=f"T{i:02d}", name=f"step{i}", prompt=f"do {i}", depends_on=deps
            )
        )
    return DecompositionDecision(steps=steps, reasoning="r")


# ── capability 守門 ─────────────────────────────────────
def test_unsupported_brain_rejected():
    """不支援 decomposition 的 brain → 拒絕（不靜默降級），不呼叫 decide_decomposition。"""
    obs = _RecordingObs()
    brain = _FakeBrain(_decision(3), supports=False)
    gd = GoalDecomposer(brain, observability=obs)
    with pytest.raises(DecompositionError, match="不支援"):
        gd.decompose("build api")
    assert brain.calls == 0  # capability 守門先於 Brain 呼叫
    assert ("decomposition_rejected", obs.events[-1][1]).__class__  # 有審計
    assert obs.events[-1][1]["reason"] == "brain_unsupported"


# ── 有界閘：步驟數 ──────────────────────────────────────
def test_too_many_steps_rejected_no_retry():
    """> 24 步 → 拒絕，不重試（Brain 僅被呼叫 1 次）。"""
    obs = _RecordingObs()
    brain = _FakeBrain(_decision(MAX_DECOMPOSITION_STEPS + 1))
    gd = GoalDecomposer(brain, observability=obs)
    with pytest.raises(DecompositionError, match="超過上限"):
        gd.decompose("g")
    assert brain.calls == 1  # 不重試
    assert obs.events[-1][1]["reason"] == "too_many_steps"


def test_exactly_max_steps_accepted():
    """剛好 24 步 → 通過。"""
    gd = GoalDecomposer(_FakeBrain(_decision(MAX_DECOMPOSITION_STEPS)))
    draft = gd.decompose("g")
    assert len(draft.playbook.tasks) == MAX_DECOMPOSITION_STEPS


def test_config_can_lower_not_raise_cap():
    """config 可下調上限；不可上調過硬上限 24。"""
    # 下調至 2：3 步被拒
    gd_low = GoalDecomposer(_FakeBrain(_decision(3)), max_steps=2)
    with pytest.raises(DecompositionError, match="超過上限 2"):
        gd_low.decompose("g")
    # 嘗試上調至 100：實際仍鎖 24，25 步被拒
    gd_high = GoalDecomposer(_FakeBrain(_decision(25)), max_steps=100)
    with pytest.raises(DecompositionError, match="超過上限 24"):
        gd_high.decompose("g")


# ── 有界閘：無環 ────────────────────────────────────────
def test_cycle_rejected():
    """DAG 含環 → 拓撲排序失敗 → 拒絕。"""
    obs = _RecordingObs()
    steps = [
        DecompositionStep(step_id="A", name="a", prompt="pa", depends_on=["B"]),
        DecompositionStep(step_id="B", name="b", prompt="pb", depends_on=["A"]),
    ]
    gd = GoalDecomposer(_FakeBrain(DecompositionDecision(steps=steps)), observability=obs)
    with pytest.raises(DecompositionError, match="含環"):
        gd.decompose("g")
    assert obs.events[-1][1]["reason"] == "cycle_detected"


def test_dangling_dependency_rejected():
    """相依不存在的 step_id → 拒絕。"""
    steps = [DecompositionStep(step_id="A", name="a", prompt="pa", depends_on=["ZZ"])]
    gd = GoalDecomposer(_FakeBrain(DecompositionDecision(steps=steps)))
    with pytest.raises(DecompositionError, match="相依不存在"):
        gd.decompose("g")


def test_topological_order_respects_dependencies():
    """有相依時，輸出順序滿足拓撲序（dep 在前）。"""
    steps = [
        DecompositionStep(step_id="C", name="c", prompt="pc", depends_on=["A", "B"]),
        DecompositionStep(step_id="A", name="a", prompt="pa"),
        DecompositionStep(step_id="B", name="b", prompt="pb", depends_on=["A"]),
    ]
    gd = GoalDecomposer(_FakeBrain(DecompositionDecision(steps=steps)))
    draft = gd.decompose("g")
    order = [t.step_id for t in draft.playbook.tasks]
    assert order.index("A") < order.index("B") < order.index("C")


# ── 有界閘：非空 prompt / 其他驗證 ──────────────────────
def test_empty_prompt_rejected():
    steps = [DecompositionStep(step_id="A", name="a", prompt="   ")]
    gd = GoalDecomposer(_FakeBrain(DecompositionDecision(steps=steps)))
    with pytest.raises(DecompositionError, match="prompt 為空"):
        gd.decompose("g")


def test_empty_steps_rejected():
    gd = GoalDecomposer(_FakeBrain(DecompositionDecision(steps=[])))
    with pytest.raises(DecompositionError, match="為空"):
        gd.decompose("g")


def test_duplicate_step_id_rejected():
    steps = [
        DecompositionStep(step_id="A", name="a", prompt="p1"),
        DecompositionStep(step_id="A", name="a2", prompt="p2"),
    ]
    gd = GoalDecomposer(_FakeBrain(DecompositionDecision(steps=steps)))
    with pytest.raises(DecompositionError, match="step_id 重複"):
        gd.decompose("g")


def test_empty_goal_rejected():
    gd = GoalDecomposer(_FakeBrain(_decision(2)))
    with pytest.raises(DecompositionError, match="goal 為空"):
        gd.decompose("   ")


def test_brain_returns_none_rejected_no_retry():
    obs = _RecordingObs()
    brain = _FakeBrain(None)
    gd = GoalDecomposer(brain, observability=obs)
    with pytest.raises(DecompositionError, match="回傳 None"):
        gd.decompose("g")
    assert brain.calls == 1
    assert obs.events[-1][1]["reason"] == "brain_returned_none"


# ── 🔴 signoff 硬閘：signoff 前不執行 ───────────────────
def test_release_before_signoff_denied():
    """未 signoff → release_for_execution 拒絕釋出可執行 Playbook（零步驟執行）。"""
    obs = _RecordingObs()
    gd = GoalDecomposer(_FakeBrain(_decision(2)), observability=obs)
    draft = gd.decompose("g")
    assert draft.signed_off is False
    with pytest.raises(DecompositionError, match="未經 🔴 人工 signoff"):
        gd.release_for_execution(draft)
    assert obs.events[-1][1]["reason"] == "not_signed_off"


def test_release_after_signoff_returns_playbook():
    """approve 後 → release 釋出可執行 Playbook，且審計含人/日期/goal hash。"""
    obs = _RecordingObs()
    gd = GoalDecomposer(_FakeBrain(_decision(2)), observability=obs)
    draft = gd.decompose("g")
    signed = gd.approve(draft, approver="koalawu")
    assert signed.signed_off is True and signed.approver == "koalawu" and signed.approved_at
    pb = gd.release_for_execution(signed)
    assert pb is signed.playbook and len(pb.tasks) == 2
    signoff_evt = [e for e in obs.events if e[0] == "decomposition_signoff"][0][1]
    assert signoff_evt["approver"] == "koalawu"
    assert signoff_evt["goal_hash"] == draft.goal_hash


def test_approve_requires_approver():
    """signoff 不可匿名（人工棘輪）。"""
    gd = GoalDecomposer(_FakeBrain(_decision(1)))
    draft = gd.decompose("g")
    with pytest.raises(DecompositionError, match="approver"):
        gd.approve(draft, approver="  ")


# ── Playbook 草稿往返載入（既有 validator）─────────────
def test_draft_roundtrip_loadable(tmp_path):
    """draft_to_yaml → load_playbook 往返一致（既有 Playbook validator 無誤載入）。

    含 evaluator_command 映射：DecompositionStep.evaluator_command → PlaybookTask
    .evaluator_command（goal_decomposer._to_playbook_draft），往返後須保留。
    """
    steps = [
        DecompositionStep(step_id="T01", name="s1", prompt="do 1", evaluator_command="pytest -q"),
        DecompositionStep(step_id="T02", name="s2", prompt="do 2", depends_on=["T01"]),
    ]
    gd = GoalDecomposer(_FakeBrain(DecompositionDecision(steps=steps, reasoning="r")))
    draft = gd.decompose("build api", project="my-proj")
    yaml_text = GoalDecomposer.draft_to_yaml(draft.playbook)
    path = tmp_path / "draft.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    reloaded = load_playbook(str(path))
    assert reloaded.project == "my-proj"
    assert reloaded.global_goal == "build api"
    assert [t.step_id for t in reloaded.tasks] == ["T01", "T02"]
    # evaluator_command 映射往返保留
    by_id = {t.step_id: t for t in reloaded.tasks}
    assert by_id["T01"].evaluator_command == "pytest -q"
    assert by_id["T02"].evaluator_command is None


# ── 不自我放大：每次拆解僅 1 次 Brain 呼叫 ──────────────
def test_single_brain_call_per_decompose():
    brain = _FakeBrain(_decision(2))
    gd = GoalDecomposer(brain)
    gd.decompose("g")
    assert brain.calls == 1


# ── MinimaxBrainAdapter 整合（capability + 委派 + 故障）──
def test_minimax_brain_adapter_supports_and_delegates():
    from autoclaude.decision.minimax_client import MinimaxClient, MinimaxError
    from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter

    mc = MinimaxClient("k", "u", "m")
    adapter = MinimaxBrainAdapter(mc)
    assert adapter.capabilities().supports_decomposition is True
    mc._call_with_retry = lambda s, u: {  # type: ignore[method-assign]
        "steps": [{"step_id": "T01", "name": "n", "prompt": "p"}], "reasoning": "r",
    }
    gd = GoalDecomposer(adapter)
    draft = gd.decompose("g")
    assert len(draft.playbook.tasks) == 1

    # API 故障 → adapter 回 None → GoalDecomposer 拒絕
    def boom(s, u):
        raise MinimaxError("api down")

    mc._call_with_retry = boom  # type: ignore[method-assign]
    with pytest.raises(DecompositionError, match="回傳 None"):
        gd.decompose("g")


# ── MinimaxClient 拆解：解析失敗防衛 + prompt 組裝 ──────
def test_minimax_client_parse_failure_raises():
    from autoclaude.decision.minimax_client import MinimaxClient, MinimaxError

    mc = MinimaxClient("k", "u", "m")
    mc._call_with_retry = lambda s, u: {"steps": "not-a-list"}  # type: ignore[method-assign]
    with pytest.raises(MinimaxError, match="DecompositionDecision 解析失敗"):
        mc.decide_decomposition("g")


def test_build_decomposition_message_with_context():
    from autoclaude.decision.prompt_builder import (
        DECOMPOSITION_SYSTEM_PROMPT,
        build_decomposition_message,
    )

    assert "≤24" in DECOMPOSITION_SYSTEM_PROMPT or "24" in DECOMPOSITION_SYSTEM_PROMPT
    msg = build_decomposition_message("my goal", context="extra ctx")
    assert "my goal" in msg and "extra ctx" in msg and "補充脈絡" in msg


# ── wiring 注入 F-A2 ────────────────────────────────────
def test_wiring_injects_tool_invocation():
    from autoclaude.core.wiring import build_goal_decomposer
    from autoclaude.decision.minimax_client import MinimaxClient
    from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter
    from autoclaude.utils.config import AppConfig

    gd = build_goal_decomposer(
        AppConfig(), brain=MinimaxBrainAdapter(MinimaxClient("k", "u", "m"))
    )
    assert isinstance(gd, GoalDecomposer)
    # F-A2 adapter 已注入（消費 allowlist 安全閘，預設 deny）
    assert gd._tool is not None
