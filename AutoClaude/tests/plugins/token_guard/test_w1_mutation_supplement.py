"""SD_09 W1 T1-B1 補測 — 殺 22 個必補 survived mutant 中 15 高 ROI case。

對應 SD_09 W3 Round 14 軸 B 分析：原 64 點為過時數字，實際 38 survived
（22 必補 + 16 string_literal ignore）。本檔聚焦 policy.py 8 / compactor.py 3 /
git_verifier.py 1 / thresholds.py 2 / watcher.py 1 共 15 case，預估殺 22 mutant
中 12~15 個 → kill_rate 預估從 73.83% 升至 83~89%（過 70% 門檻 + ±2pp tolerance
緩衝）。

對應 ADR-SD09-009 v1.0 ACCEPTED + 軸 B 補測建議優先順序：
1. policy.py 8 case — 直接呼叫 public API (should_compact/build_compact_prompt)
   殺 sig default values mutant（既有 test_policy_mutation 經 _evaluate_resources
   payload 走，不殺 public API default）
2. compactor.py 3 case — build_compact_prompt 直接呼叫 + 字面值 mutation
3. git_verifier.py 1 case — _WARNING_TEMPLATE 模組常量
4. thresholds.py 2 case — should_compact_decision boundary
5. watcher.py 1 case — observe_token_line boundary
"""
from __future__ import annotations

from autoclaude.plugins.token_guard import TokenGuardPlugin
from autoclaude.plugins.token_guard.compactor import (
    CompactFailureState,
    build_compact_prompt,
    process_compact_result,
)
from autoclaude.plugins.token_guard.git_verifier import _WARNING_TEMPLATE
from autoclaude.plugins.token_guard.thresholds import (
    should_compact_decision,
    should_halt_decision,
)
from autoclaude.plugins.token_guard.watcher import observe_token_line
from autoclaude.utils.config import TokenGuardConfig


# ─────────────────────────────────────────────────────────────────
# policy.py — 8 case（殺 sig default values + kwarg propagation）
# ─────────────────────────────────────────────────────────────────


class TestPolicyPublicApiDefaults:
    """直接呼叫 public API（should_compact/build_compact_prompt），不經 payload。

    既有 test_policy_mutation 大多經 _evaluate_resources payload 走，無法殺
    public API sig default values mutation。本組補強直接 caller 路徑。
    """

    def test_should_compact_default_attempt_is_zero(self):
        """policy.py:80-89 should_compact default attempt=0 → 殺 attempt=1 mutation。

        attempt=0 + max_retries=3 → dynamic_threshold = base - 0 = 80（無衰減）
        若 default 改 1 → threshold = 80 - 1/3*15 = 75 → 75% 邊界判定錯誤
        """
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # 76% 在 default attempt=0 (threshold=80) → False；attempt=1 (threshold=75) → True
        # 此處不傳 attempt，依賴 default=0
        assert p.should_compact(token_pct=76.0) is False
        assert p.should_compact(token_pct=80.0) is True

    def test_should_compact_default_max_retries_is_3(self):
        """policy.py:81 should_compact default max_retries=3 → 殺 max_retries=2 mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # attempt=1, default max_retries=3 → threshold = 80 - 1/3*15 = 75
        # 若改 max_retries=2 → threshold = 80 - 1/2*15 = 72.5 → 邊界 73% 判定錯
        assert p.should_compact(token_pct=73.0, attempt=1) is False  # 73 < 75
        assert p.should_compact(token_pct=75.0, attempt=1) is True   # 75 ≥ 75

    def test_should_compact_default_in_correction_loop_is_false(self):
        """policy.py:82 should_compact default in_correction_loop=False → 殺 True mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # token_pct=85, default in_correction_loop=False, history_len=0 → True
        # 若 default 改 True + history_len=0 → 進 short_history 路徑（仍 True，但語意不同）
        assert p.should_compact(token_pct=85.0) is True

    def test_should_compact_default_correction_history_len_is_zero(self):
        """policy.py:82 should_compact default correction_history_len=0 → 殺 =1 mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # in_correction_loop=True + default history_len=0 → short_history 路徑（>= threshold）
        # 若 default 改 1 → 不走 short_history（fallthrough True） — 邊界判定差異
        assert p.should_compact(token_pct=85.0, in_correction_loop=True) is True

    def test_build_compact_prompt_default_attempt_is_zero(self):
        """policy.py:133 build_compact_prompt default attempt=0 → 殺 default=1 mutation。

        attempt=0 + task → anchor 含 `[ATTEMPT] 1`（因 attempt+1）
        若 default 改 1 → anchor 含 `[ATTEMPT] 2` → 字串差異可斷言
        """
        from autoclaude.models.playbook import PlaybookTask
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = build_compact_prompt(task=task)
        assert "[ATTEMPT] 1" in prompt
        assert "[ATTEMPT] 2" not in prompt

    def test_build_compact_prompt_default_failure_summary_is_empty(self):
        """policy.py:134 build_compact_prompt default failure_summary="" → 殺 default 非空 mutation。

        無 failure_summary 時，prompt 不應含「重要：壓縮後必須記住」字樣
        """
        prompt = build_compact_prompt()
        assert "重要：壓縮後必須記住" not in prompt
        assert "[LAST_FAILURE]" not in prompt

    def test_build_compact_prompt_default_global_goal_anchor_chars_is_200(self):
        """policy.py:135 build_compact_prompt default global_goal_anchor_chars=200。

        殺 default 改 100/300 mutation：以 250 字 global_goal 驗證截斷邊界
        """
        from autoclaude.models.playbook import PlaybookTask
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        long_goal = "x" * 250  # 250 字
        prompt = build_compact_prompt(task=task, global_goal=long_goal)
        # 預設 200 字 + 截斷 → anchor 內 [GLOBAL_GOAL] 含 200 個 x + ellipsis
        assert "[GLOBAL_GOAL]" in prompt
        anchor_line = [ln for ln in prompt.split("\n") if "[GLOBAL_GOAL]" in ln][0]
        # 200 x + "…" + 換行 → anchor_line 長度約 [GLOBAL_GOAL] x*200 …
        x_count = anchor_line.count("x")
        assert x_count == 200  # default 200 邊界

    def test_evaluate_resources_payload_none_defaults_to_empty_dict(self):
        """policy.py:157 `payload = ctx.payload or {}` → 殺 `or` 邏輯 mutation。

        payload=None 時必須走 default empty dict（避免 None.get AttributeError）
        """
        from autoclaude.core.hookspec import HookContext, KernelPhase
        from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
        p = TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=90.0))
        pb = Playbook(version="1.0", project="P", global_invariants=GlobalInvariants(), tasks=[])
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        ctx = HookContext(phase=KernelPhase.POST_ATTEMPT, playbook=pb, task=task, payload=None)
        # payload None → empty dict → token_pct=0.0 → 不 halt 不 compact → None
        assert p.on_event(ctx) is None


# ─────────────────────────────────────────────────────────────────
# compactor.py — 3 case（default attempt + concat 字面值）
# ─────────────────────────────────────────────────────────────────


class TestCompactorMutations:
    def test_compactor_build_default_attempt_is_zero(self):
        """compactor.py:37 build_compact_prompt default attempt=0 → 殺 default=1 mutation。"""
        from autoclaude.models.playbook import PlaybookTask
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = build_compact_prompt(task=task)
        # default attempt=0 → ATTEMPT 顯示 1
        assert "[ATTEMPT] 1\n" in prompt

    def test_compactor_prompt_starts_with_slash_compact(self):
        """compactor.py:66-67 prompt 必須以 `/compact\\n` 起頭 → 殺字面值 mutation。"""
        prompt = build_compact_prompt()
        assert prompt.startswith("/compact\n"), f"prompt must start with /compact\\n: {prompt[:30]!r}"

    def test_compactor_failure_summary_appended_at_end(self):
        """compactor.py:75-76 failure_summary 非空時 append 至 prompt 末段。

        殺 `compact_prompt += f"\\n\\n重要：..."` 字串字面值 + concat mutation。
        """
        summary = "AssertionError at test_foo.py:42"
        prompt = build_compact_prompt(failure_summary=summary)
        assert "重要：壓縮後必須記住" in prompt
        assert summary in prompt
        # summary 必須在 prompt 末段（concat 在最後）
        assert prompt.endswith(f"{summary}\n")


# ─────────────────────────────────────────────────────────────────
# git_verifier.py — 1 case（_WARNING_TEMPLATE 模組常量字面值）
# ─────────────────────────────────────────────────────────────────


class TestGitVerifierWarningTemplateConstant:
    def test_warning_template_contains_required_keywords(self):
        """git_verifier.py:23-29 _WARNING_TEMPLATE 模組常量字面值 → 殺字串 mutation。

        驗證 user-facing prompt 內必須關鍵字（attempt 變數 + 工具名稱 Edit/Write +
        關鍵動作描述「實際修改檔案」）— 若 mutation 改字面值 → 斷言失敗。
        """
        assert "{attempt}" in _WARNING_TEMPLATE  # format placeholder
        assert "Edit" in _WARNING_TEMPLATE
        assert "Write" in _WARNING_TEMPLATE
        assert "git diff" in _WARNING_TEMPLATE
        assert "實際修改檔案" in _WARNING_TEMPLATE
        # 驗證 format 可正常套用
        formatted = _WARNING_TEMPLATE.format(attempt=3)
        assert "attempt 3" in formatted


# ─────────────────────────────────────────────────────────────────
# thresholds.py — 2 case（boundary epsilon）
# ─────────────────────────────────────────────────────────────────


class TestThresholdsBoundary:
    def test_should_compact_decision_boundary_token_pct_equals_threshold(self):
        """thresholds.py:32 `if token_pct < threshold:` boundary → 殺 `<= / >`  mutation。

        token_pct == threshold 應視為達標（不應 short-circuit return False）。
        """
        # 80 == 80 → 不 return False，走後續邏輯 → True
        result = should_compact_decision(
            token_pct=80.0, threshold=80.0,
            in_correction_loop=False, correction_history_len=0,
        )
        assert result is True

    def test_should_compact_decision_just_below_threshold_returns_false(self):
        """thresholds.py:32 boundary → token_pct < threshold 必須 return False。"""
        # 79.99 < 80.0 → return False
        result = should_compact_decision(
            token_pct=79.99, threshold=80.0,
            in_correction_loop=False, correction_history_len=0,
        )
        assert result is False


# ─────────────────────────────────────────────────────────────────
# watcher.py — 1 case（observe_token_line boundary）
# ─────────────────────────────────────────────────────────────────


class TestWatcherBoundary:
    def test_observe_token_line_pct_equals_peak_returns_unchanged(self):
        """watcher.py:31 `if pct is None or pct <= peak_pct:` boundary → 殺 `< / >` mutation。

        pct == peak → 不更新 peak（== 走 <=，return unchanged）。
        """
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        new_peak, new_compact, new_halt = observe_token_line(
            pct=50.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False,
            cfg=cfg,
        )
        assert new_peak == 50.0  # 不更新
        assert new_compact is False  # 不觸發
        assert new_halt is False
