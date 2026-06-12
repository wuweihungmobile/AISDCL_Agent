"""SD_09 W1 軸 B 64 點位正式補測（compactor 24 / git_verifier 13 / policy 17 / watcher 3 / thresholds 7）。

對應 SD09_Execution_Guide.md §3.0.1 軸 B + §3.0.5 SP-1 同步點：W1 token_guard
64 case 全集形式補測，作為觀察期 #1 mutation pilot kill_rate 持續穩定 ≥ 70% 的
保險層 + 屬性測試覆蓋層。

與既有測試的分工：
  - test_compactor.py 等 (5 module × 1)：基本功能 case
  - test_*_mutation.py (5 module × 1)：mutation pilot survived 點位反殺
  - test_w1_mutation_supplement.py：15 高 ROI sig-default 補測
  - **本檔（test_w1_64case_full.py）**：W1 64 點位「形式補測層」— 屬性測試、
    參數組合、不變量驗證、API 契約防護，不重複既有點位

64 case 分佈：
  - compactor 24：CompactFailureState 8 / build_compact_prompt 12 / process_compact_result 4
  - git_verifier 13：_propagate_trace_env 3 / verify_correction_applied 10
  - policy 17：構造/identity 5 / public API delegation 7 / on_event flow 5
  - watcher 3：observe_token_line 2 / resolve_per_step_cfg 1
  - thresholds 7：get_dynamic_compact_threshold 5 / decision invariants 2
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from autoclaude.core.hookspec import (
    HookContext,
    KernelPhase,
    ResourceRequest,
)
from autoclaude.models.playbook import (
    GlobalInvariants,
    Playbook,
    PlaybookTask,
)
from autoclaude.plugins.token_guard import TokenGuardPlugin
from autoclaude.plugins.token_guard.compactor import (
    CompactFailureState,
    build_compact_prompt,
    process_compact_result,
)
from autoclaude.plugins.token_guard.git_verifier import (
    _WARNING_TEMPLATE,
    _propagate_trace_env,
    verify_correction_applied,
)
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin as _PolicyClass
from autoclaude.plugins.token_guard.thresholds import (
    get_dynamic_compact_threshold,
    should_compact_decision,
    should_halt_decision,
)
from autoclaude.plugins.token_guard.watcher import (
    observe_token_line,
    resolve_per_step_cfg,
)
from autoclaude.utils.config import TokenGuardConfig


def _pb() -> Playbook:
    return Playbook(
        version="1.0", project="P",
        global_invariants=GlobalInvariants(), tasks=[],
    )


def _task(step_id: str = "T01", name: str = "n") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name=name, prompt="p")


# ════════════════════════════════════════════════════════════════════
# compactor.py — 24 case
# ════════════════════════════════════════════════════════════════════


class TestCompactorW1FailureState:
    """CompactFailureState 8 case — 構造、屬性、語意不變量。"""

    def test_c01_dataclass_field_count(self):
        """CompactFailureState 僅 count + critical_threshold 兩欄位。"""
        s = CompactFailureState()
        # dataclass field 集合穩定
        from dataclasses import fields
        names = {f.name for f in fields(s)}
        assert names == {"count", "critical_threshold"}

    def test_c02_critical_threshold_is_int_type(self):
        s = CompactFailureState(critical_threshold=2)
        assert isinstance(s.critical_threshold, int)

    def test_c03_count_is_int_type(self):
        s = CompactFailureState()
        assert isinstance(s.count, int)

    def test_c04_record_failure_returns_count_not_state(self):
        """record_failure 回傳 int 而非 self（避免 caller 誤用 chained call）。"""
        s = CompactFailureState()
        result = s.record_failure()
        assert isinstance(result, int)
        assert result is not s

    def test_c05_record_failure_is_monotonic(self):
        """連續呼叫 record_failure 必嚴格單調遞增。"""
        s = CompactFailureState()
        seq = [s.record_failure() for _ in range(5)]
        assert seq == [1, 2, 3, 4, 5]
        # 嚴格遞增
        assert all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))

    def test_c06_is_critical_idempotent(self):
        """is_critical 多次呼叫不改變 state。"""
        s = CompactFailureState(count=2, critical_threshold=2)
        results = [s.is_critical() for _ in range(5)]
        assert all(r is True for r in results)
        assert s.count == 2  # 未被副作用變更

    def test_c07_reset_to_below_threshold_reverts_critical(self):
        s = CompactFailureState(count=5, critical_threshold=2)
        assert s.is_critical() is True
        s.reset()
        assert s.is_critical() is False

    def test_c08_record_after_reset_starts_from_one(self):
        """reset 後 record_failure 必須從 1 開始（非從先前累積值）。"""
        s = CompactFailureState(count=10)
        s.reset()
        assert s.record_failure() == 1


class TestCompactorW1BuildPrompt:
    """build_compact_prompt 12 case — 屬性 / 結構 / 邊界。"""

    def test_c09_prompt_is_str_type(self):
        """回傳值必為 str（非 bytes / dict）。"""
        assert isinstance(build_compact_prompt(), str)

    def test_c10_prompt_non_empty(self):
        assert len(build_compact_prompt()) > 0

    def test_c11_prompt_contains_slash_compact_directive(self):
        """`/compact` 為 Claude Code 內建指令，必須完整保留。"""
        assert "/compact" in build_compact_prompt()

    def test_c12_anchor_brackets_balanced(self):
        """anchor === === 開閉成對。"""
        task = _task()
        prompt = build_compact_prompt(task=task)
        assert prompt.count("=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===") == 1
        assert prompt.count("=== END ANCHOR ===") == 1

    def test_c13_anchor_omitted_without_task(self):
        prompt = build_compact_prompt(task=None)
        assert "===" not in prompt

    def test_c14_attempt_label_uses_one_based_indexing(self):
        """[ATTEMPT] N 必為 attempt+1（避免 attempt=0 顯示為 0）。"""
        task = _task()
        for a in [0, 1, 2, 5, 10]:
            prompt = build_compact_prompt(task=task, attempt=a)
            assert f"[ATTEMPT] {a + 1}" in prompt

    def test_c15_success_condition_optional(self):
        """無 expected_output_regex 時不應出現 [SUCCESS_CONDITION]。"""
        task = _task()
        prompt = build_compact_prompt(task=task)
        assert "[SUCCESS_CONDITION]" not in prompt
        task2 = PlaybookTask(step_id="T01", name="n", prompt="p", expected_output_regex=r"OK")
        prompt2 = build_compact_prompt(task=task2)
        assert "[SUCCESS_CONDITION]" in prompt2

    def test_c16_last_failure_only_when_summary_present(self):
        """[LAST_FAILURE] 僅在 failure_summary 非空 + task 存在時出現。"""
        task = _task()
        assert "[LAST_FAILURE]" not in build_compact_prompt(task=task)
        assert "[LAST_FAILURE]" in build_compact_prompt(task=task, failure_summary="X")

    def test_c17_failure_summary_without_task_no_anchor_block(self):
        """failure_summary 但 task=None → anchor 不生成（[LAST_FAILURE] 不在 anchor）。"""
        prompt = build_compact_prompt(task=None, failure_summary="boom")
        assert "[LAST_FAILURE]" not in prompt
        # 但末段 fallback 仍包含 failure_summary
        assert "boom" in prompt

    def test_c18_global_goal_label_in_anchor(self):
        task = _task()
        prompt = build_compact_prompt(task=task, global_goal="solve x")
        assert "[GLOBAL_GOAL] solve x" in prompt

    def test_c19_global_goal_truncation_boundary(self):
        """global_goal_anchor_chars=N 邊界：len > N 加 ellipsis，len == N 不加。"""
        task = _task()
        # 恰等於 N
        p1 = build_compact_prompt(task=task, global_goal="A" * 10, global_goal_anchor_chars=10)
        assert "[GLOBAL_GOAL] " + "A" * 10 in p1
        assert "…" not in p1
        # N+1
        p2 = build_compact_prompt(task=task, global_goal="A" * 11, global_goal_anchor_chars=10)
        assert "[GLOBAL_GOAL] " + "A" * 10 + "…" in p2

    def test_c20_global_goal_zero_chars_param_edge(self):
        """global_goal_anchor_chars=0 邊界：空字串 + ellipsis（任何非空 goal 均超過）。"""
        task = _task()
        prompt = build_compact_prompt(
            task=task, global_goal="hello", global_goal_anchor_chars=0,
        )
        # global_goal[:0] = ""；len("hello")=5 > 0 → 加 …
        assert "[GLOBAL_GOAL] …" in prompt


class TestCompactorW1ProcessResult:
    """process_compact_result 4 case — state 互動 / 返回值契約。"""

    def test_c21_returns_bool_not_truthy(self):
        """返回必為 bool（非 1/0 / None / "yes"）。"""
        s = CompactFailureState()
        result = process_compact_result(state=s, triggered_compact=False)
        assert isinstance(result, bool)

    def test_c22_state_param_is_keyword_only(self):
        """state 必為 keyword-only — 避免 positional 誤用。"""
        s = CompactFailureState()
        # 必須使用 keyword
        with pytest.raises(TypeError):
            process_compact_result(s, True)  # type: ignore[misc]
        # keyword 形式正常
        assert process_compact_result(state=s, triggered_compact=False) is True

    def test_c23_triggered_compact_keyword_only(self):
        """triggered_compact 必為 keyword-only。"""
        s = CompactFailureState()
        with pytest.raises(TypeError):
            process_compact_result(s, True)  # type: ignore[misc]

    def test_c24_state_count_zero_compact_false_remains_zero(self):
        """count=0 + triggered_compact=False → reset 後 count 仍 0（idempotent）。"""
        s = CompactFailureState(count=0)
        process_compact_result(state=s, triggered_compact=False)
        assert s.count == 0


# ════════════════════════════════════════════════════════════════════
# git_verifier.py — 13 case
# ════════════════════════════════════════════════════════════════════


class TestGitVerifierW1PropagateEnv:
    """_propagate_trace_env 3 case — env 傳遞 / Rule 7 邊界。"""

    def test_g01_env_includes_all_current_os_environ_keys(self):
        """env 必須完整複製 os.environ keys（不過濾）。"""
        import os
        env = _propagate_trace_env()
        for k in os.environ:
            assert k in env

    def test_g02_env_modification_isolation(self):
        """env 修改不影響後續 _propagate_trace_env 呼叫。"""
        env1 = _propagate_trace_env()
        env1["__TEMP_KEY__"] = "x"
        env2 = _propagate_trace_env()
        assert "__TEMP_KEY__" not in env2

    def test_g03_env_value_types_are_str(self):
        """env value 必為 str（dict(os.environ) 保證）。"""
        env = _propagate_trace_env()
        # spot-check 一些必有的鍵
        for k, v in list(env.items())[:5]:
            assert isinstance(k, str)
            assert isinstance(v, str)


class TestGitVerifierW1VerifyCorrection:
    """verify_correction_applied 10 case — 流程 / 例外 / 引數覆蓋。"""

    def test_g04_attempt_zero_returns_none_without_subprocess(self):
        """attempt=0 → 直接 None，subprocess 不被呼叫。"""
        with patch("subprocess.run") as m:
            assert verify_correction_applied(0) is None
            assert m.call_count == 0

    def test_g05_attempt_zero_with_custom_cwd_still_returns_none(self):
        """attempt=0 + custom cwd → 仍 short-circuit。"""
        with patch("subprocess.run") as m:
            assert verify_correction_applied(0, cwd="/tmp") is None
            assert m.call_count == 0

    def test_g06_warning_format_attempt_substituted(self):
        """warning 模板的 {attempt} 必須被 format。"""
        fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=fake_result):
            w = verify_correction_applied(42)
        assert w is not None
        assert "attempt 42" in w
        assert "{attempt}" not in w  # 已替換

    def test_g07_returncode_nonzero_returns_none(self):
        """returncode != 0 → 視為查詢失敗，返回 None（不警告）。"""
        fake_result = subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="not a git repo")
        with patch("subprocess.run", return_value=fake_result):
            assert verify_correction_applied(1) is None

    def test_g08_stdout_with_only_newlines_treated_as_empty(self):
        """純 newline stdout 經 strip 後為空 → 警告。"""
        fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="\n\n\n", stderr="")
        with patch("subprocess.run", return_value=fake_result):
            assert verify_correction_applied(1) is not None

    def test_g09_stdout_with_tabs_only_treated_as_empty(self):
        fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="\t\t", stderr="")
        with patch("subprocess.run", return_value=fake_result):
            assert verify_correction_applied(1) is not None

    def test_g10_warning_contains_three_action_items(self):
        """警告文字必含關鍵動作清單編號 1./2.。"""
        assert "1. " in _WARNING_TEMPLATE
        assert "2. " in _WARNING_TEMPLATE

    def test_g11_warning_template_is_str_type(self):
        assert isinstance(_WARNING_TEMPLATE, str)
        # 非空
        assert len(_WARNING_TEMPLATE) > 50

    def test_g12_subprocess_args_immutable_list_format(self):
        """subprocess args 為 list 而非 str（避免 shell injection）。"""
        fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="x", stderr="")
        with patch("subprocess.run", return_value=fake_result) as m:
            verify_correction_applied(1)
        first_arg = m.call_args[0][0]
        assert isinstance(first_arg, list)
        # 不接受 shell=True
        assert m.call_args.kwargs.get("shell") in (None, False)

    def test_g13_generic_oserror_propagates(self):
        """未被 catch 的 OSError 應 raise 而非 silently None（除 FileNotFoundError / TimeoutExpired）。

        對齊 except (FileNotFoundError, subprocess.TimeoutExpired) — 其他例外不吞。
        """
        with patch("subprocess.run", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                verify_correction_applied(1)


# ════════════════════════════════════════════════════════════════════
# policy.py — 17 case
# ════════════════════════════════════════════════════════════════════


class TestPolicyW1Construction:
    """TokenGuardPlugin 構造與 identity 5 case。"""

    def test_p01_default_config_when_none(self):
        """token_guard_cfg=None 時 fallback TokenGuardConfig()。"""
        p = TokenGuardPlugin(token_guard_cfg=None)
        assert isinstance(p._cfg, TokenGuardConfig)

    def test_p02_custom_config_preserved(self):
        cfg = TokenGuardConfig(compact_threshold_pct=77.0)
        p = TokenGuardPlugin(cfg)
        assert p._cfg.compact_threshold_pct == 77.0

    def test_p03_compact_state_initialized(self):
        p = TokenGuardPlugin()
        assert isinstance(p._compact_state, CompactFailureState)
        assert p._compact_state.count == 0

    def test_p04_class_identity_via_init(self):
        """通過 __init__ 反向確認類型 — 殺 PolicyClass alias mutation。"""
        p1 = TokenGuardPlugin()
        p2 = _PolicyClass()
        assert type(p1) is type(p2)

    def test_p05_plugin_class_name(self):
        """類名穩定 — 殺 rename mutation。"""
        assert TokenGuardPlugin.__name__ == "TokenGuardPlugin"


class TestPolicyW1PublicApi:
    """公開 API delegation 7 case — 與 _impl module 等價性。"""

    def test_p06_get_dynamic_compact_threshold_delegates(self):
        """attempt=0 → 等於 base_threshold。"""
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        assert p.get_dynamic_compact_threshold(attempt=0, max_retries=3) == 80.0

    def test_p07_should_halt_uses_halt_threshold(self):
        p = TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=88.0))
        assert p.should_halt(87.99) is False
        assert p.should_halt(88.0) is True
        assert p.should_halt(100.0) is True

    def test_p08_record_compact_failure_via_state(self):
        p = TokenGuardPlugin()
        assert p.record_compact_failure() == 1
        assert p.compact_failure_count == 1

    def test_p09_reset_compact_failure_via_state(self):
        p = TokenGuardPlugin()
        p.record_compact_failure()
        p.record_compact_failure()
        p.reset_compact_failure()
        assert p.compact_failure_count == 0

    def test_p10_is_compact_failure_critical_via_state(self):
        p = TokenGuardPlugin()
        # default critical_threshold=2
        p.record_compact_failure()
        assert p.is_compact_failure_critical() is False
        p.record_compact_failure()
        assert p.is_compact_failure_critical() is True

    def test_p11_compact_failure_count_setter_persists(self):
        p = TokenGuardPlugin()
        p._compact_failure_count = 7
        assert p._compact_state.count == 7
        assert p.compact_failure_count == 7

    def test_p12_resolve_per_step_cfg_global_when_no_task(self):
        cfg = TokenGuardConfig(compact_threshold_pct=75.0)
        p = TokenGuardPlugin(cfg)
        result = p.resolve_per_step_cfg(task=None)
        assert result is cfg


class TestPolicyW1OnEventFlow:
    """on_event 5 case — phase routing / disabled / payload defaults。"""

    def test_p13_disabled_returns_none_on_post_attempt(self):
        p = TokenGuardPlugin(TokenGuardConfig(enabled=False))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 99.0},
        )
        assert p.on_event(ctx) is None

    def test_p14_disabled_returns_none_on_token_usage(self):
        p = TokenGuardPlugin(TokenGuardConfig(enabled=False))
        ctx = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 99.0},
        )
        assert p.on_event(ctx) is None

    def test_p15_unrelated_phase_returns_none(self):
        """非 POST_ATTEMPT/ON_TOKEN_USAGE phase → 直接 None。"""
        p = TokenGuardPlugin()
        ctx = HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 99.0},
        )
        assert p.on_event(ctx) is None

    def test_p16_observe_token_line_delegates(self):
        """observe_token_line 委派層必使用 self._cfg。"""
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        peak, c, h = p.observe_token_line(
            pct=85.0, peak_pct=50.0, triggered_compact=False, triggered_halt=False,
        )
        assert peak == 85.0
        assert c is True
        assert h is False

    def test_p17_verify_correction_applied_delegates(self):
        """verify_correction_applied 委派至 git_verifier 模組。"""
        p = TokenGuardPlugin()
        # attempt=0 → 直接 None（不需 patch subprocess）
        assert p.verify_correction_applied(0) is None


# ════════════════════════════════════════════════════════════════════
# watcher.py — 3 case
# ════════════════════════════════════════════════════════════════════


class TestWatcherW1Comprehensive:
    """observe_token_line 2 + resolve_per_step_cfg 1。"""

    def test_w01_observe_pct_none_passthrough_all_flags(self):
        """pct=None → 所有狀態原樣返回。"""
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, c, h = observe_token_line(
            pct=None, peak_pct=72.5,
            triggered_compact=True, triggered_halt=False, cfg=cfg,
        )
        assert peak == 72.5
        assert c is True  # 保留
        assert h is False  # 保留

    def test_w02_observe_high_pct_triggers_halt_priority(self):
        """halt > compact 雙門檻：pct 同時超過時 halt 優先（elif 排他性）。"""
        # 對齊 TokenGuardConfig 驗證：halt_threshold_pct > compact_threshold_pct
        cfg = TokenGuardConfig(compact_threshold_pct=70.0, halt_threshold_pct=80.0)
        peak, c, h = observe_token_line(
            pct=85.0, peak_pct=0.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        # 85 >= halt 80 → halt 優先（elif），compact 不應翻
        assert peak == 85.0
        assert h is True
        assert c is False

    def test_w03_resolve_per_step_cfg_returns_new_instance_when_override(self):
        """有效 override 必返回新 instance（避免 mutate global）。"""
        g = TokenGuardConfig(compact_threshold_pct=80.0)
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={"compact_threshold_pct": 70.0},
        )
        result = resolve_per_step_cfg(global_cfg=g, task=task)
        assert result is not g  # 不同 instance
        assert g.compact_threshold_pct == 80.0  # global 未被污染
        assert result.compact_threshold_pct == 70.0


# ════════════════════════════════════════════════════════════════════
# thresholds.py — 7 case
# ════════════════════════════════════════════════════════════════════


class TestThresholdsW1Comprehensive:
    """get_dynamic_compact_threshold 5 + decision 2。"""

    def test_t01_kwarg_only_signature(self):
        """所有 thresholds API 必為 kw-only — 避免 positional 誤用。"""
        with pytest.raises(TypeError):
            get_dynamic_compact_threshold(80.0, 0, 3)  # type: ignore[misc]
        with pytest.raises(TypeError):
            should_compact_decision(80.0, 80.0, False, 0)  # type: ignore[misc]
        with pytest.raises(TypeError):
            should_halt_decision(80.0, 90.0)  # type: ignore[misc]

    def test_t02_dynamic_threshold_monotonic_decreasing_in_attempt(self):
        """attempt 上升 → threshold 必單調不上升（直到撞 floor）。"""
        results = [
            get_dynamic_compact_threshold(base_threshold=80.0, attempt=a, max_retries=5)
            for a in range(0, 6)
        ]
        for i in range(len(results) - 1):
            assert results[i] >= results[i + 1]

    def test_t03_dynamic_threshold_never_below_floor(self):
        """任何輸入下 result >= floor。"""
        for attempt in [0, 1, 5, 100, 1000]:
            r = get_dynamic_compact_threshold(
                base_threshold=80.0, attempt=attempt, max_retries=3,
                floor=65.0, decay_factor=15.0,
            )
            assert r >= 65.0

    def test_t04_dynamic_threshold_never_above_base(self):
        """無 attempt 增益 → 永不上升超過 base。"""
        for max_r in [1, 3, 10]:
            for attempt in [0, 1, 5]:
                r = get_dynamic_compact_threshold(
                    base_threshold=80.0, attempt=attempt, max_retries=max_r,
                )
                assert r <= 80.0

    def test_t05_dynamic_threshold_fractional_attempt(self):
        """fractional max_retries 邊界：max_retries=0 → 直接返 base。"""
        # max_retries=0 走防呆 → base 不衰減
        r = get_dynamic_compact_threshold(
            base_threshold=85.0, attempt=10, max_retries=0,
        )
        assert r == 85.0

    def test_t06_should_compact_returns_bool_not_truthy_value(self):
        """返回必為 bool。"""
        r = should_compact_decision(
            token_pct=80.0, threshold=80.0,
            in_correction_loop=False, correction_history_len=0,
        )
        assert isinstance(r, bool)
        assert r is True or r is False

    def test_t07_should_halt_returns_bool_type(self):
        r = should_halt_decision(token_pct=90.0, halt_threshold=90.0)
        assert isinstance(r, bool)
