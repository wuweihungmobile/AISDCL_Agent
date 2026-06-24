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


# ── improving_57 A 軌 L4：有界自動凍結 signoff（auto_release）─────────
from autoclaude.core.ports.goal_freeze_gate import FreezeVerdict  # noqa: E402
from autoclaude.infra.adapters.goal_freeze_gate import (  # noqa: E402
    DEFAULT_MAX_AUTO_STEPS,
    BoundedGoalFreezeGate,
)


class _StubGate:
    """可控 IGoalFreezeGate：固定回傳預設 verdict，並記錄被呼叫之原語。"""

    def __init__(self, verdict: FreezeVerdict):
        self._verdict = verdict
        self.calls: list[dict] = []

    def evaluate(self, *, goal_hash, step_count, prompts):
        self.calls.append(
            {"goal_hash": goal_hash, "step_count": step_count, "prompts": prompts}
        )
        return self._verdict


def test_auto_release_no_gate_falls_back_to_manual():
    """未注入 freeze_gate → auto_release 拒絕（回退 🔴 人工 signoff，零行為變更）。"""
    gd = GoalDecomposer(_FakeBrain(_decision(2)))
    draft = gd.decompose("g")
    with pytest.raises(DecompositionError, match="未注入 IGoalFreezeGate"):
        gd.auto_release(draft)
    # 人工路徑仍完好
    pb = gd.release_for_execution(gd.approve(draft, approver="human"))
    assert len(pb.tasks) == 2


def test_auto_release_bounded_gate_approves_small_clean_draft():
    """有界閘對小規模乾淨拆解 → 自動 signoff 釋出；審計記 approver=auto:GoalFreezeGate。"""
    obs = _RecordingObs()
    gd = GoalDecomposer(
        _FakeBrain(_decision(3)), observability=obs,
        freeze_gate=BoundedGoalFreezeGate(),
    )
    draft = gd.decompose("build a small thing")
    pb = gd.auto_release(draft)
    assert pb is draft.playbook and len(pb.tasks) == 3
    # 自動凍結審計（XAI 可解釋：approved + reason + conditions）
    frz = [e for e in obs.events if e[0] == "decomposition_auto_freeze"][0][1]
    assert frz["approved"] is True
    assert frz["goal_hash"] == draft.goal_hash
    assert any("step_count=3" in c for c in frz["conditions"])
    # signoff 審計記自動簽署者（非匿名、可追溯）
    signoff = [e for e in obs.events if e[0] == "decomposition_signoff"][0][1]
    assert signoff["approver"] == "auto:GoalFreezeGate"


def test_auto_release_rejects_oversize_draft_fails_closed():
    """步驟數超自動上限 → 閘拒絕 → auto_release raise（fail-closed 回退人工，不釋出）。"""
    obs = _RecordingObs()
    n = DEFAULT_MAX_AUTO_STEPS + 1  # 13 > 12，仍 ≤ 硬上限 24（decompose 不擋，僅自動閘擋）
    gd = GoalDecomposer(
        _FakeBrain(_decision(n)), observability=obs,
        freeze_gate=BoundedGoalFreezeGate(),
    )
    draft = gd.decompose("g")
    with pytest.raises(DecompositionError, match="自動凍結閘拒絕"):
        gd.auto_release(draft)
    frz = [e for e in obs.events if e[0] == "decomposition_auto_freeze"][0][1]
    assert frz["approved"] is False  # 審計留拒絕痕（誠實，非靜默）
    # fail-closed：未自動釋出，但人工棘輪仍可放行
    pb = gd.release_for_execution(gd.approve(draft, approver="human"))
    assert len(pb.tasks) == n


def test_auto_release_rejects_injection_tainted_prompt():
    """prompt 含注入嫌疑字元 → 閘拒絕 → 回退人工（深度防禦，不自動放行攻擊向量）。"""
    steps = [DecompositionStep(step_id="A", name="a", prompt="rm -rf / && echo $HOME")]
    gd = GoalDecomposer(
        _FakeBrain(DecompositionDecision(steps=steps)),
        freeze_gate=BoundedGoalFreezeGate(),
    )
    draft = gd.decompose("g")
    with pytest.raises(DecompositionError, match="注入嫌疑字元"):
        gd.auto_release(draft)


def test_auto_release_passes_primitives_not_draft_to_gate():
    """auto_release 傳原語（goal_hash/step_count/prompts）給 gate，不傳 execution 物件。"""
    gate = _StubGate(FreezeVerdict(True, "ok", ("c1",)))
    gd = GoalDecomposer(_FakeBrain(_decision(2)), freeze_gate=gate)
    draft = gd.decompose("g")
    gd.auto_release(draft)
    assert gate.calls[0]["goal_hash"] == draft.goal_hash
    assert gate.calls[0]["step_count"] == 2
    assert gate.calls[0]["prompts"] == ("do 1", "do 2")


# ── BoundedGoalFreezeGate 單元（有界條件 + 可解釋裁決）───────────
def test_bounded_gate_approves_within_bounds():
    v = BoundedGoalFreezeGate().evaluate(
        goal_hash="abc", step_count=5, prompts=("clean prompt", "another")
    )
    assert v.auto_approved is True
    assert any("prompts_untainted" == c for c in v.conditions)


def test_bounded_gate_rejects_empty_and_oversize():
    g = BoundedGoalFreezeGate()
    assert g.evaluate(goal_hash="a", step_count=0, prompts=()).auto_approved is False
    over = g.evaluate(
        goal_hash="a", step_count=DEFAULT_MAX_AUTO_STEPS + 1, prompts=("x",)
    )
    assert over.auto_approved is False and "超過自動放行上限" in over.reason


def test_bounded_gate_rejects_missing_goal_hash():
    v = BoundedGoalFreezeGate().evaluate(goal_hash="", step_count=2, prompts=("p",))
    assert v.auto_approved is False and "goal_hash" in v.reason


def test_bounded_gate_max_auto_steps_lowerable_not_raisable():
    """max_auto_steps 可下調不可上調（鎖在 DEFAULT_MAX_AUTO_STEPS 之內）。"""
    low = BoundedGoalFreezeGate(max_auto_steps=2)
    assert low.evaluate(goal_hash="a", step_count=3, prompts=("p",)).auto_approved is False
    high = BoundedGoalFreezeGate(max_auto_steps=999)  # 實際仍鎖 12
    cap = high.evaluate(
        goal_hash="a", step_count=DEFAULT_MAX_AUTO_STEPS, prompts=("p",) * DEFAULT_MAX_AUTO_STEPS
    )
    assert cap.auto_approved is True
    assert high.evaluate(
        goal_hash="a", step_count=DEFAULT_MAX_AUTO_STEPS + 1, prompts=("p",)
    ).auto_approved is False


def test_wiring_injects_freeze_gate():
    """build_goal_decomposer 注入 BoundedGoalFreezeGate（A 軌 L4 自動凍結閘）。"""
    from autoclaude.core.wiring import build_goal_decomposer
    from autoclaude.decision.minimax_client import MinimaxClient
    from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter
    from autoclaude.utils.config import AppConfig

    gd = build_goal_decomposer(
        AppConfig(), brain=MinimaxBrainAdapter(MinimaxClient("k", "u", "m"))
    )
    assert gd._freeze_gate is not None
    assert isinstance(gd._freeze_gate, BoundedGoalFreezeGate)
