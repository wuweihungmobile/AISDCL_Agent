"""F-B2 CorrectionVerifier 單元測試（Improving_012 Phase 2 / ADR-AGT-004）。

測試意圖（Rule 9）：
  - 效果歸因必須以「前筆確曾施加修正」為前提，否則 streak 會把與修正無關的
    失敗也算成「修正無效」，導致誤升級。
  - 改善判準三分量（signature / fail_count / exit_code）任一成立即改善——
    防止 Brain 修正方向正確但尚未全綠時被誤判無效。
  - KB 失效回寫保證歷史成功策略失效後不再被 query 直接採用（元學習自我校正）。
"""
from __future__ import annotations

from autoclaude.execution.alert_ladder import AlertLadder
from autoclaude.execution.correction_verifier import (
    CorrectionVerifier,
    verify_and_update,
)
from autoclaude.execution.failure_tracker import FailureTracker


def _track(records: list[dict]) -> FailureTracker:
    """records: [{out, exit, corrected(bool), mutated(bool)}]"""
    t = FailureTracker("T01")
    for i, r in enumerate(records):
        t.record(i, "fail", r.get("out", ""), r.get("exit", 1))
        if r.get("corrected"):
            t.update_last_correction_prompt("修正指令")
        if r.get("mutated"):
            t.history[-1].mutation_applied = True
    return t


class TestAssess:
    def test_less_than_two_records_not_applicable(self):
        t = _track([{"out": "1 failed", "corrected": True}])
        assert CorrectionVerifier.assess(t).applicable is False

    def test_prev_without_correction_not_applicable(self):
        """前筆未施加修正 → 本次失敗無法歸因（防誤計 streak）。"""
        t = _track([{"out": "E1"}, {"out": "E1"}])
        assert CorrectionVerifier.assess(t).applicable is False

    def test_mutation_applied_counts_as_correction(self):
        t = _track([{"out": "ErrorA", "mutated": True}, {"out": "ErrorA"}])
        assert CorrectionVerifier.assess(t).applicable is True

    def test_signature_change_is_improvement(self):
        t = _track([{"out": "TypeError: x", "corrected": True},
                    {"out": "ValueError: y"}])
        eff = CorrectionVerifier.assess(t)
        assert eff.applicable and eff.improved
        assert "signature" in eff.reason

    def test_fail_count_drop_same_signature_is_improvement(self):
        # signature 只取前 200 字；pytest 摘要行（N failed）常在其後 —
        # 構造前 200 字相同、僅尾端 count 不同的輸出驗證 fail_count 分量
        head = "AssertionError: x" + ("=" * 200)
        t = _track([{"out": head + " 5 failed", "corrected": True},
                    {"out": head + " 2 failed"}])
        eff = CorrectionVerifier.assess(t)
        assert eff.improved
        assert "fail_count" in eff.reason

    def test_exit_code_drop_is_improvement(self):
        t = _track([{"out": "ErrorA", "exit": 2, "corrected": True},
                    {"out": "ErrorA", "exit": 1}])
        eff = CorrectionVerifier.assess(t)
        assert eff.improved
        assert "exit_code" in eff.reason

    def test_same_signature_no_drop_is_not_improved(self):
        t = _track([{"out": "ErrorA 3 failed", "corrected": True},
                    {"out": "ErrorA 3 failed"}])
        eff = CorrectionVerifier.assess(t)
        assert eff.applicable and not eff.improved

    def test_fail_count_unextractable_does_not_count_as_improvement(self):
        """任一筆取不到 fail_count → 該分量無資訊，不可誤判改善。"""
        t = _track([{"out": "ErrorA no counts", "corrected": True},
                    {"out": "ErrorA no counts"}])
        assert CorrectionVerifier.assess(t).improved is False


class _SpyKB:
    def __init__(self, raise_on_call: bool = False):
        self.calls: list[tuple] = []
        self._raise = raise_on_call

    def record_strategy_failure(self, key, strategy, step_id):
        if self._raise:
            raise RuntimeError("KB 故障")
        self.calls.append((key, strategy, step_id))


class TestVerifyAndUpdate:
    def test_improvement_resets_streak(self):
        ladder = AlertLadder()
        ladder.set_no_improve_streak("T01", 1)
        t = _track([{"out": "ErrorA", "corrected": True}, {"out": "ErrorB"}])
        streak = verify_and_update(
            tracker=t, ladder=ladder, knowledge_base=_SpyKB(),
            step_id="T01", error_class="assertion", last_strategy="PINPOINT",
        )
        assert streak == 0
        assert ladder.get_no_improve_streak("T01") == 0

    def test_no_improvement_increments_and_writes_kb(self):
        ladder = AlertLadder()
        kb = _SpyKB()
        t = _track([{"out": "ErrorA", "corrected": True}, {"out": "ErrorA"}])
        streak = verify_and_update(
            tracker=t, ladder=ladder, knowledge_base=kb,
            step_id="T01", error_class="assertion", last_strategy="REWRITE",
        )
        assert streak == 1
        key, strategy, step_id = kb.calls[0]
        assert key.startswith("assertion:")
        assert strategy == "REWRITE"
        assert step_id == "T01"

    def test_not_applicable_keeps_streak(self):
        ladder = AlertLadder()
        ladder.set_no_improve_streak("T01", 1)
        t = _track([{"out": "ErrorA"}, {"out": "ErrorA"}])  # 前筆未修正
        streak = verify_and_update(
            tracker=t, ladder=ladder, knowledge_base=_SpyKB(),
            step_id="T01", error_class="assertion", last_strategy="PINPOINT",
        )
        assert streak == 1
        assert _SpyKB().calls == []

    def test_kb_failure_does_not_break_main_flow(self):
        """KB 故障不可阻斷修正主流程（與既有 KB 寫入容錯一致）。"""
        ladder = AlertLadder()
        t = _track([{"out": "ErrorA", "corrected": True}, {"out": "ErrorA"}])
        streak = verify_and_update(
            tracker=t, ladder=ladder, knowledge_base=_SpyKB(raise_on_call=True),
            step_id="T01", error_class="assertion", last_strategy="PINPOINT",
        )
        assert streak == 1  # streak 仍更新，例外被吞並 warning

    def test_two_consecutive_no_improvements_reach_threshold(self):
        """凍結驗收：同 error signature 無改善 N=2 次 → ladder bypass 提前升級。"""
        ladder = AlertLadder(threshold_no_improve=2)
        kb = _SpyKB()
        t = _track([
            {"out": "ErrorA", "corrected": True},
            {"out": "ErrorA", "corrected": True},
            {"out": "ErrorA"},
        ])
        # 模擬兩輪驗證（attempt 2 與 attempt 3 失敗後各跑一次）
        t2 = _track([{"out": "ErrorA", "corrected": True}, {"out": "ErrorA"}])
        verify_and_update(tracker=t2, ladder=ladder, knowledge_base=kb,
                          step_id="T01", error_class="assertion",
                          last_strategy="PINPOINT")
        streak = verify_and_update(tracker=t, ladder=ladder, knowledge_base=kb,
                                   step_id="T01", error_class="assertion",
                                   last_strategy="REWRITE")
        assert streak == 2
        from autoclaude.execution.convergence_monitor import ConvergenceReport
        report = ConvergenceReport(0.0, "stuck", [], "escalate", "x")
        assert ladder.intercept("T01", report, streak).action == "escalate"


class TestKbStrategyFailure:
    def test_record_strategy_failure_merges_skip_and_clears_successful(self, tmp_path):
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        kb.record_success("assertion:sigA", "REWRITE", "T01", error_class="assertion")

        kb.record_strategy_failure("assertion:sigA", "REWRITE", "T01")
        entry = kb.query("assertion:sigA")
        assert entry is not None
        assert entry["outcome"] == "strategy_failure"
        assert "REWRITE" in entry["skip_strategies"]
        # 歷史成功策略失效 → 清除，query 命中不再直接採用
        assert entry["successful_strategy"] is None
        assert entry["error_class"] == "assertion"

    def test_record_strategy_failure_keeps_other_successful(self, tmp_path):
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        kb.record_success("assertion:sigA", "SPLIT", "T01", error_class="assertion")

        kb.record_strategy_failure("assertion:sigA", "REWRITE", "T01")
        entry = kb.query("assertion:sigA")
        assert entry["successful_strategy"] == "SPLIT"  # 不同策略失效不牽連
        assert "REWRITE" in entry["skip_strategies"]

    def test_record_strategy_failure_persists_across_reload(self, tmp_path):
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        path = str(tmp_path / "kb.jsonl")
        kb = FailureKnowledgeBase(path)
        kb.record_strategy_failure("import:sigB", "PINPOINT", "T02")

        kb2 = FailureKnowledgeBase(path)
        entry = kb2.query("import:sigB")
        assert entry is not None
        assert "PINPOINT" in entry["skip_strategies"]
