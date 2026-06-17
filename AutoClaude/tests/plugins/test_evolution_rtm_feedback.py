"""EvolutionPlugin × RTM 反饋諮詢接入測試（AutoSDD_improving_27 W1c）。

RTM AT 對應：
  - AT-27-4-1：flag OFF → rationale 無 RTM 註記（零退化，現況行為不變）
  - AT-27-4-2：flag ON ∧ 注入 source ∧ SDD step ∧ 上次有 gap → rationale 附諮詢摘要
  - AT-27-4-3：flag ON 但非 SDD step / 無 source / 上次已全覆蓋 → 無註記
  - AT-27-4-4：read_report 拋例外 → fail-soft（無註記、不阻斷演化）

紅線驗證：RTM 反饋僅增補 rationale（諮詢），不改 mutation 決策本身。
"""
from __future__ import annotations

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.core.ports.rtm_sink import RtmCoverageReport
from autoclaude.evolution.playbook_evolver import PlaybookEvolutionProposal
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.evolution_plugin import EvolutionPlugin


def _gap_report() -> RtmCoverageReport:
    """未完全覆蓋（AC-001-1 僅 1/2 AT 通過）。"""
    return RtmCoverageReport(
        scenario="brownfield", spec_digest="sha256:x",
        total_at=3, passed_at=2, failed_at_ids=("AT-001-1-2",),
        ac_coverage=(("AC-001-1", 1, 2), ("AC-001-2", 1, 1)),
    )


def _full_report() -> RtmCoverageReport:
    return RtmCoverageReport(
        scenario="brownfield", spec_digest="sha256:x",
        total_at=2, passed_at=2, failed_at_ids=(),
        ac_coverage=(("AC-001-1", 1, 1), ("AC-001-2", 1, 1)),
    )


def _ac_report(covered: int, total: int) -> RtmCoverageReport:
    """ac_coverage_pct = covered/total×100 的快照（供趨勢測試）。"""
    ac = tuple((f"AC-{i}", 1, 1) for i in range(covered)) + tuple(
        (f"AC-{covered + i}", 0, 1) for i in range(total - covered)
    )
    return RtmCoverageReport(
        scenario="brownfield", spec_digest="x",
        total_at=total, passed_at=covered, ac_coverage=ac,
    )


class _FakeFeedback:
    def __init__(self, report=None, *, raises=False, history=(), raises_history=False):
        self._r = report
        self._raises = raises
        self._history = history
        self._raises_history = raises_history

    def read_report(self, project):
        if self._raises:
            raise RuntimeError("boom")
        return self._r

    def read_history(self, project, *, limit=0):
        if self._raises_history:
            raise RuntimeError("boom-history")
        return self._history


class _StubEvolver:
    """固定回一個 INJECT_STEP proposal，使 _handle_propose 必產出 MutationProposal。"""

    def propose_evolution(self, *, playbook, failed_step_idx, escalation_dump,
                          escalation_history=None):
        return PlaybookEvolutionProposal(
            evolution_type="INJECT_STEP", inject_before_idx=0, reasoning="base reason",
            new_step=PlaybookTask(step_id="fix-1", name="fix", prompt="do fix"),
        )


def _pb(project="Demo") -> Playbook:
    return Playbook(version="1.0", project=project,
                    global_invariants=GlobalInvariants(),
                    tasks=[PlaybookTask(step_id="sdd-brownfield-at-001-1-2",
                                        name="AT-001-1-2", prompt="x")])


def _ctx(task_step_id="sdd-brownfield-at-001-1-2") -> HookContext:
    task = PlaybookTask(step_id=task_step_id, name="t", prompt="x") if task_step_id else None
    return HookContext(
        phase=KernelPhase.ON_ESCALATION, playbook=_pb(), task=task,
        payload={"escalation_dump": object(), "failed_step_idx": 0},
    )


def _plugin(*, feedback=None, enabled=False) -> EvolutionPlugin:
    return EvolutionPlugin(rule_evolver=_StubEvolver(), rtm_feedback=feedback,
                           enable_rtm_feedback=enabled)


class TestAnnotationBranches:
    def test_flag_off_no_annotation(self):
        """AT-27-4-1：flag OFF → 空註記（零退化）。"""
        assert _plugin(feedback=_FakeFeedback(_gap_report()), enabled=False) \
            ._rtm_gap_annotation(_ctx()) == ""

    def test_no_source_no_annotation(self):
        """AT-27-4-3：flag ON 但無注入 source → 空。"""
        assert _plugin(feedback=None, enabled=True)._rtm_gap_annotation(_ctx()) == ""

    def test_non_sdd_step_no_annotation(self):
        """AT-27-4-3：失敗步驟非 SDD step（無 sdd- 前綴）→ 空。"""
        p = _plugin(feedback=_FakeFeedback(_gap_report()), enabled=True)
        assert p._rtm_gap_annotation(_ctx(task_step_id="T01")) == ""

    def test_fully_covered_no_annotation(self):
        """AT-27-4-3：上次已 100% 覆蓋 → 無 gap → 空。"""
        p = _plugin(feedback=_FakeFeedback(_full_report()), enabled=True)
        assert p._rtm_gap_annotation(_ctx()) == ""

    def test_gap_produces_annotation(self):
        """AT-27-4-2：flag ON ∧ SDD step ∧ 有 gap → 諮詢摘要含覆蓋率與未通過 AT。"""
        p = _plugin(feedback=_FakeFeedback(_gap_report()), enabled=True)
        ann = p._rtm_gap_annotation(_ctx())
        assert "RTM 反饋" in ann
        assert "AT-001-1-2" in ann
        assert "不自動套用" in ann  # 紅線標記

    def test_read_error_fail_soft(self):
        """AT-27-4-4：read_report 拋例外 → fail-soft 回空、不 raise。"""
        p = _plugin(feedback=_FakeFeedback(raises=True), enabled=True)
        assert p._rtm_gap_annotation(_ctx()) == ""


class TestTrendAnnotation:
    """W-28-1：跨輪覆蓋趨勢諮詢註記（消費 read_history，閉合 W3 冷資料斷鏈）。"""

    _DECLINING = (_ac_report(5, 5), _ac_report(4, 5), _ac_report(2, 5))  # 100→80→40

    def test_flag_off_no_trend(self):
        """flag OFF → 空趨勢註記（零退化）。"""
        p = _plugin(feedback=_FakeFeedback(history=self._DECLINING), enabled=False)
        assert p._rtm_trend_annotation(_ctx()) == ""

    def test_no_source_no_trend(self):
        """flag ON 但無注入 source → 空。"""
        assert _plugin(feedback=None, enabled=True)._rtm_trend_annotation(_ctx()) == ""

    def test_non_sdd_step_no_trend(self):
        """非 SDD step（無 sdd- 前綴）→ 空。"""
        p = _plugin(feedback=_FakeFeedback(history=self._DECLINING), enabled=True)
        assert p._rtm_trend_annotation(_ctx(task_step_id="T01")) == ""

    def test_single_round_no_trend(self):
        """history <2 輪（無上輪可比）→ 空。"""
        p = _plugin(feedback=_FakeFeedback(history=(_ac_report(2, 5),)), enabled=True)
        assert p._rtm_trend_annotation(_ctx()) == ""

    def test_declining_trend_produces_annotation(self):
        """flag ON ∧ SDD step ∧ ≥2 輪下降 → 諮詢註記含趨勢、連續下降、紅線標記。"""
        p = _plugin(feedback=_FakeFeedback(history=self._DECLINING), enabled=True)
        ann = p._rtm_trend_annotation(_ctx())
        assert "跨輪覆蓋趨勢" in ann
        assert "上輪 80.0%" in ann and "本輪 40.0%" in ann
        assert "下降" in ann
        assert "連續 2 輪下降" in ann
        assert "不自動套用" in ann  # 紅線標記

    def test_read_history_error_fail_soft(self):
        """read_history 拋例外 → fail-soft 回空、不 raise。"""
        p = _plugin(feedback=_FakeFeedback(raises_history=True), enabled=True)
        assert p._rtm_trend_annotation(_ctx()) == ""

    def test_trend_in_end_to_end_rationale(self):
        """端到端：flag ON ∧ 下降趨勢 → on_event 回的 rationale 含趨勢諮詢（不改 mutation）。"""
        p = _plugin(feedback=_FakeFeedback(history=self._DECLINING), enabled=True)
        result = p.on_event(_ctx())
        assert result is not None
        assert "base reason" in result.rationale
        assert "跨輪覆蓋趨勢" in result.rationale
        assert result.mutation is not None  # 紅線：決策本身未被趨勢更動


class TestEndToEndRationale:
    def test_flag_on_rationale_includes_feedback(self):
        """AT-27-4-2 端到端：on_event(ON_ESCALATION) 回 MutationProposal.rationale 含原因+RTM 反饋。"""
        p = _plugin(feedback=_FakeFeedback(_gap_report()), enabled=True)
        result = p.on_event(_ctx())
        assert result is not None
        assert "base reason" in result.rationale
        assert "RTM 反饋" in result.rationale
        # 紅線：mutation 決策本身未被 RTM 反饋更動（仍是 stub 的 INJECT → INJECT_BEFORE）
        assert result.mutation is not None

    def test_flag_off_rationale_unchanged(self):
        """AT-27-4-1 端到端：flag OFF → rationale 僅原因，無 RTM 反饋（零退化）。"""
        p = _plugin(feedback=_FakeFeedback(_gap_report()), enabled=False)
        result = p.on_event(_ctx())
        assert result is not None
        assert result.rationale == "base reason"
