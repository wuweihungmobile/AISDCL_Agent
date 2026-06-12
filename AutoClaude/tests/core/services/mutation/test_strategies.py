"""7 個 IMutationStrategy 單元測試（Phase 2）。

驗證每個 strategy 的 can_handle 與 apply 行為。
"""
from __future__ import annotations

from autoclaude.core.services.mutation import (
    ConditionalStrategy,
    DeleteStepStrategy,
    GotoStepStrategy,
    InjectAfterStrategy,
    InjectBeforeStrategy,
    MutationApplyService,
    NoOpStrategy,
    ReviseCurrentStrategy,
    SkipToStrategy,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.models.step_mutation import StepMutation, StepMutationType


def _t(step_id: str, prompt: str = "p") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name=step_id, prompt=prompt)


def _pb(*tasks) -> Playbook:
    return Playbook(version="1.0", project="test",
                    global_invariants=GlobalInvariants(), tasks=list(tasks))


class TestReviseCurrentStrategy:
    def test_can_handle_revise(self):
        s = ReviseCurrentStrategy()
        m = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="x")
        assert s.can_handle(m) is True

    def test_cannot_handle_inject(self):
        s = ReviseCurrentStrategy()
        m = StepMutation(mutation_type=StepMutationType.INJECT_AFTER)
        assert s.can_handle(m) is False

    def test_apply_replaces_current_prompt(self):
        s = ReviseCurrentStrategy()
        pb = _pb(_t("T01", "old"), _t("T02"))
        m = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="new")
        ok = s.apply(m, pb, current_idx=0)
        assert ok is True
        assert pb.tasks[0].prompt == "new"

    def test_apply_returns_false_when_no_revised_prompt(self):
        s = ReviseCurrentStrategy()
        pb = _pb(_t("T01"))
        m = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt=None)
        assert s.apply(m, pb, 0) is False


class TestInjectAfterStrategy:
    def test_inserts_after_current(self):
        s = InjectAfterStrategy()
        pb = _pb(_t("T01"), _t("T02"))
        m = StepMutation(
            mutation_type=StepMutationType.INJECT_AFTER,
            new_step_id="T_NEW", new_step_name="N", new_step_prompt="p",
        )
        ok = s.apply(m, pb, current_idx=0)
        assert ok is True
        assert len(pb.tasks) == 3
        assert pb.tasks[1].step_id == "T_NEW"
        assert pb.tasks[2].step_id == "T02"

    def test_rejects_missing_new_step_id(self):
        s = InjectAfterStrategy()
        pb = _pb(_t("T01"))
        m = StepMutation(mutation_type=StepMutationType.INJECT_AFTER,
                         new_step_id=None, new_step_prompt="x")
        assert s.apply(m, pb, 0) is False


class TestInjectBeforeStrategy:
    def test_inserts_before_current(self):
        s = InjectBeforeStrategy()
        pb = _pb(_t("T01"), _t("T02"))
        m = StepMutation(
            mutation_type=StepMutationType.INJECT_BEFORE,
            new_step_id="T_PRE", new_step_name="N", new_step_prompt="p",
        )
        ok = s.apply(m, pb, current_idx=1)
        assert ok is True
        assert len(pb.tasks) == 3
        assert pb.tasks[1].step_id == "T_PRE"
        assert pb.tasks[2].step_id == "T02"


class TestGotoStepStrategy:
    def test_validates_existing_target(self):
        s = GotoStepStrategy()
        pb = _pb(_t("T01"), _t("T02"), _t("T03"))
        m = StepMutation(mutation_type=StepMutationType.GOTO_STEP, goto_step_id="T01")
        assert s.apply(m, pb, current_idx=2) is True

    def test_rejects_nonexistent_target(self):
        s = GotoStepStrategy()
        pb = _pb(_t("T01"))
        m = StepMutation(mutation_type=StepMutationType.GOTO_STEP, goto_step_id="T99")
        assert s.apply(m, pb, 0) is False


class TestSkipToStrategy:
    def test_accepts_forward_target(self):
        s = SkipToStrategy()
        pb = _pb(_t("T01"), _t("T02"), _t("T03"))
        m = StepMutation(mutation_type=StepMutationType.SKIP_TO, skip_to_step_id="T03")
        assert s.apply(m, pb, current_idx=0) is True

    def test_rejects_backward_target(self):
        s = SkipToStrategy()
        pb = _pb(_t("T01"), _t("T02"), _t("T03"))
        m = StepMutation(mutation_type=StepMutationType.SKIP_TO, skip_to_step_id="T01")
        assert s.apply(m, pb, current_idx=2) is False

    def test_rejects_self_target(self):
        s = SkipToStrategy()
        pb = _pb(_t("T01"), _t("T02"))
        m = StepMutation(mutation_type=StepMutationType.SKIP_TO, skip_to_step_id="T01")
        assert s.apply(m, pb, current_idx=0) is False


class TestDeleteStepStrategy:
    def test_removes_target_step(self):
        s = DeleteStepStrategy()
        pb = _pb(_t("T01"), _t("T02"), _t("T03"))
        m = StepMutation(mutation_type=StepMutationType.DELETE_STEP, delete_step_id="T02")
        ok = s.apply(m, pb, current_idx=0)
        assert ok is True
        assert len(pb.tasks) == 2
        assert [t.step_id for t in pb.tasks] == ["T01", "T03"]

    def test_refuses_to_delete_current_step(self):
        s = DeleteStepStrategy()
        pb = _pb(_t("T01"), _t("T02"))
        m = StepMutation(mutation_type=StepMutationType.DELETE_STEP, delete_step_id="T01")
        # current_idx=0 對應 T01，不可刪除自己
        assert s.apply(m, pb, current_idx=0) is False
        assert len(pb.tasks) == 2


class TestNoOpStrategy:
    def test_can_handle_anything(self):
        s = NoOpStrategy()
        m = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT)
        assert s.can_handle(m) is True

    def test_apply_always_true(self):
        s = NoOpStrategy()
        pb = _pb(_t("T01"))
        m = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT)
        assert s.apply(m, pb, 0) is True


class TestMutationApplyService:
    def test_routes_revise(self):
        svc = MutationApplyService()
        pb = _pb(_t("T01", "old"))
        m = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="new")
        assert svc.apply(m, pb, 0) is True
        assert pb.tasks[0].prompt == "new"

    def test_routes_inject_after(self):
        svc = MutationApplyService()
        pb = _pb(_t("T01"))
        m = StepMutation(
            mutation_type=StepMutationType.INJECT_AFTER,
            new_step_id="T_NEW", new_step_prompt="p",
        )
        assert svc.apply(m, pb, 0) is True
        assert len(pb.tasks) == 2

    def test_routes_delete(self):
        svc = MutationApplyService()
        pb = _pb(_t("T01"), _t("T02"), _t("T03"))
        m = StepMutation(mutation_type=StepMutationType.DELETE_STEP, delete_step_id="T03")
        assert svc.apply(m, pb, 0) is True
        assert len(pb.tasks) == 2

    def test_validate_batch_compatible(self):
        svc = MutationApplyService()
        ms = [
            StepMutation(
                mutation_type=StepMutationType.INJECT_AFTER,
                new_step_id="A", new_step_prompt="x",
            ),
            StepMutation(
                mutation_type=StepMutationType.INJECT_AFTER,
                new_step_id="B", new_step_prompt="y",
            ),
        ]
        assert svc.validate_batch(ms) is True

    def test_validate_batch_rejects_inject_and_delete_same_id(self):
        svc = MutationApplyService()
        ms = [
            StepMutation(
                mutation_type=StepMutationType.INJECT_AFTER,
                new_step_id="X", new_step_prompt="x",
            ),
            StepMutation(
                mutation_type=StepMutationType.DELETE_STEP,
                delete_step_id="X",
            ),
        ]
        assert svc.validate_batch(ms) is False

    def test_validate_batch_empty_returns_true(self):
        svc = MutationApplyService()
        assert svc.validate_batch([]) is True


class TestConditionalStrategy:
    """Gap-021 / SD_05 W4-1：CONDITIONAL 分支突變。"""

    def _make_cond(self, *, true_branch=None, false_branch=None, cmd="exit 0"):
        return StepMutation(
            mutation_type=StepMutationType.CONDITIONAL,
            condition_evaluator=cmd,
            true_mutation=true_branch,
            false_mutation=false_branch,
        )

    def test_can_handle_only_conditional(self):
        s = ConditionalStrategy()
        assert s.can_handle(self._make_cond()) is True
        assert s.can_handle(
            StepMutation(mutation_type=StepMutationType.REVISE_CURRENT)
        ) is False

    def test_apply_returns_false_when_no_evaluator(self):
        s = ConditionalStrategy()
        m = StepMutation(mutation_type=StepMutationType.CONDITIONAL)
        assert s.apply(m, _pb(_t("T01")), 0) is False

    def test_apply_rejects_unsafe_command(self):
        s = ConditionalStrategy()
        # SD_05 W4 三方審查 SA-M1：擴張至 ≥ 12 種 unsafe pattern（含 backtick / redirect / newline / heredoc / history expansion）
        unsafe_cases = [
            "ls | grep x",              # 管線
            "echo $HOME",               # 變數展開
            "$(whoami)",                # 子 shell（$）
            "rm -rf /; ls",             # 多指令（;）
            "a && b",                   # 條件鏈（&&）
            "`whoami`",                 # 反引號（command substitution）
            "ls > out.txt",             # output redirect
            "cat < in.txt",             # input redirect
            "test -f a\nrm b",          # newline
            "test !x",                  # bash history expansion（!）
            "cd ~",                     # tilde 展開
            "test \\(x\\)",             # backslash escape
            "",                          # 空字串
            "  ",                        # 純空白
        ]
        for unsafe in unsafe_cases:
            m = StepMutation(
                mutation_type=StepMutationType.CONDITIONAL,
                condition_evaluator=unsafe,
            )
            assert s.apply(m, _pb(_t("T01")), 0) is False, f"unsafe={unsafe!r}"

    def test_apply_selects_true_branch_on_exit_zero(self):
        # 注入假 evaluator 避免真 IO
        s = ConditionalStrategy(evaluator=lambda cmd, t: 0)
        svc = MutationApplyService(strategies=[
            ReviseCurrentStrategy(),
            InjectAfterStrategy(),
            InjectBeforeStrategy(),
            GotoStepStrategy(),
            SkipToStrategy(),
            DeleteStepStrategy(),
            s,
        ])
        pb = _pb(_t("T01", "old"), _t("T02"))
        true_branch = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="NEW",
        )
        false_branch = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="WRONG",
        )
        m = self._make_cond(true_branch=true_branch, false_branch=false_branch)
        assert svc.apply(m, pb, 0) is True
        assert pb.tasks[0].prompt == "NEW"

    def test_apply_selects_false_branch_on_nonzero_exit(self):
        s = ConditionalStrategy(evaluator=lambda cmd, t: 1)
        svc = MutationApplyService(strategies=[
            ReviseCurrentStrategy(),
            InjectAfterStrategy(),
            InjectBeforeStrategy(),
            GotoStepStrategy(),
            SkipToStrategy(),
            DeleteStepStrategy(),
            s,
        ])
        pb = _pb(_t("T01", "old"), _t("T02"))
        true_branch = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="WRONG",
        )
        false_branch = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="FALSE_BRANCH",
        )
        m = self._make_cond(true_branch=true_branch, false_branch=false_branch)
        assert svc.apply(m, pb, 0) is True
        assert pb.tasks[0].prompt == "FALSE_BRANCH"

    def test_apply_returns_true_when_branch_is_none(self):
        # condition 已 evaluate，但所選分支為 None → 視為 no-op success
        s = ConditionalStrategy(evaluator=lambda cmd, t: 0)
        svc = MutationApplyService(strategies=[ReviseCurrentStrategy(), s])
        pb = _pb(_t("T01"))
        m = self._make_cond(true_branch=None, false_branch=None)
        assert svc.apply(m, pb, 0) is True

    def test_evaluator_exception_treated_as_false_branch(self):
        # SD_05 W4-1：使用 _default_evaluator 預設行為 — 例外 → exit=1 → false 分支
        # SD_05 W4 修復：shell=False + shlex.split，"false" 被當 argv[0]
        from autoclaude.core.services.mutation._conditional_evaluator import _default_evaluator
        # 不存在的 binary → subprocess 失敗 → 視為 false 分支
        assert _default_evaluator("nonexistent_cmd_xyz", timeout=5) == 1

    def test_default_evaluator_handles_shlex_error(self):
        # SD_05 W4：shlex.split 對未閉合引號拋 ValueError → 視為 false 分支
        from autoclaude.core.services.mutation._conditional_evaluator import _default_evaluator
        assert _default_evaluator("test 'unclosed", timeout=5) == 1

    def test_apply_blocks_nested_conditional_exceeding_max_depth(self):
        # SD_05 W4 SD-M1：巢狀深度上限防護
        s = ConditionalStrategy(evaluator=lambda c, t: 0)
        svc = MutationApplyService(strategies=[
            ReviseCurrentStrategy(),
            InjectAfterStrategy(),
            InjectBeforeStrategy(),
            GotoStepStrategy(),
            SkipToStrategy(),
            DeleteStepStrategy(),
            s,
        ])
        # 構造 6 層巢狀（超過 _MAX_RECURSION_DEPTH=4）
        innermost = StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="DEEP",
        )
        current = innermost
        for _ in range(6):
            current = StepMutation(
                mutation_type=StepMutationType.CONDITIONAL,
                condition_evaluator="exit 0",
                true_mutation=current,
            )
        pb = _pb(_t("T01", "old"))
        result = svc.apply(current, pb, 0)
        # 深度超限後深層的 REVISE_CURRENT 不被套用，prompt 保持 "old"
        assert result is False or pb.tasks[0].prompt == "old"

    def test_service_recursive_apply_via_set_service(self):
        # SD_05 W4-1：service 註冊時應自動注入自身至 ConditionalStrategy._service
        svc = MutationApplyService()
        cond_strategy = next(
            s for s in svc._strategies if isinstance(s, ConditionalStrategy)
        )
        assert cond_strategy._service is svc

    def test_service_recursive_into_inject_after(self):
        s = ConditionalStrategy(evaluator=lambda cmd, t: 0)
        svc = MutationApplyService(strategies=[
            ReviseCurrentStrategy(),
            InjectAfterStrategy(),
            InjectBeforeStrategy(),
            GotoStepStrategy(),
            SkipToStrategy(),
            DeleteStepStrategy(),
            s,
        ])
        pb = _pb(_t("T01"), _t("T02"))
        inject = StepMutation(
            mutation_type=StepMutationType.INJECT_AFTER,
            new_step_id="T01_INJ", new_step_prompt="injected",
        )
        m = self._make_cond(true_branch=inject, false_branch=None)
        assert svc.apply(m, pb, 0) is True
        assert any(t.step_id == "T01_INJ" for t in pb.tasks)
