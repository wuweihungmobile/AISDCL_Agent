"""Unit tests for ACT-021 Semantic Same-Pattern Detection (Phase E M2)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.pattern_matcher import (  # noqa: E402
    best_match,
    is_same_pattern,
    normalize,
    similarity,
)
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state  # noqa: E402


# Pairs that mean the SAME thing — matcher must return True.
SEMANTIC_SAME_PAIRS = [
    (
        "test_login_p95 > 200ms at concurrency 100",
        "test_login_p95 exceeded 200ms under 100 concurrent users",
    ),
    (
        "FRD-005 missing quantitative NFR-PERF target",
        "FRD 005 missing quantitative NFR PERF target value",
    ),
    (
        "bcrypt cost factor 12 causes login p95 > 300ms",
        "bcrypt cost factor 12 causes login p95 above 300ms",
    ),
    (
        "AC-010-1 not testable: success undefined",
        "AC 010 1 not testable success undefined",
    ),
    (
        "retry_count exceeded limit 3 at SCG-0",
        "retry count exceeded limit 3 for SCG 0",
    ),
]

# P1-A：繁中專案的中文 paraphrase 對。CLAUDE.md Rule 1 強制繁中回覆，
# pattern_matcher 必須能在中文 failure reason 之間判定語意同模式，否則
# Rule 9.1「相同模式 × 3 進入 SPEC_AUDIT」於繁中專案會 false negative。
SEMANTIC_SAME_PAIRS_ZH = [
    (
        "登入 p95 超過 200ms 在並發 100 時",
        "登入 p95 大於 200ms 在同時 100 時",
    ),
    (
        "RTM 覆蓋率低於 100%",
        "RTM 覆蓋率小於 100%",
    ),
    (
        "bcrypt 成本因子 12 導致登入 p95 超過 300ms",
        "bcrypt 成本因子 12 導致登入 p95 高於 300ms",
    ),
    (
        "AC-010-1 不可測試 success 未定義",
        "AC 010 1 不可測試 success 未定義",
    ),
]

# Pairs that genuinely differ — matcher must return False.
DIFFERENT_PAIRS = [
    (
        "test_login_p95 > 200ms at concurrency 100",
        "test_checkout failed with HTTP 500 on cart submit",
    ),
    (
        "RTM coverage 87% below 100% threshold",
        "OpenAPI 3.1 schema missing POST /orders endpoint",
    ),
    (
        "INV-003 violated: balance must be non-negative",
        "Stripe webhook signature mismatch on /webhook/v2",
    ),
    (
        "Integration test: Redis connection refused",
        "ADR-002 superseded by ADR-007",
    ),
    (
        "Docker build failed — base image digest mismatch",
        "SCG-3 OpenAPI contract not frozen yet",
    ),
]


class PatternMatcherTests(unittest.TestCase):
    def test_normalize_strips_timestamps_and_paths(self) -> None:
        raw = "2026-04-20T10:00:00Z failure in /repo/tools/fsm/runtime.py line 42"
        norm = normalize(raw)
        self.assertNotIn("2026", norm)
        self.assertNotIn("repo", norm)
        self.assertNotIn("42", norm)
        self.assertIn("failure", norm)

    def test_similarity_identical_strings_is_one(self) -> None:
        self.assertEqual(similarity("abc", "abc"), 1.0)

    def test_similarity_empty_handling(self) -> None:
        self.assertEqual(similarity(None, None), 1.0)
        self.assertEqual(similarity("abc", ""), 0.0)
        self.assertEqual(similarity("", "abc"), 0.0)

    def test_semantic_same_pairs_match(self) -> None:
        for i, (a, b) in enumerate(SEMANTIC_SAME_PAIRS):
            with self.subTest(pair=i):
                self.assertTrue(
                    is_same_pattern(a, b),
                    msg=f"pair {i} expected SAME but similarity={similarity(a, b):.2f}",
                )

    def test_semantic_same_pairs_zh_match(self) -> None:
        """P1-A：繁中 paraphrase 必須被判為相同模式。"""
        for i, (a, b) in enumerate(SEMANTIC_SAME_PAIRS_ZH):
            with self.subTest(zh_pair=i):
                self.assertTrue(
                    is_same_pattern(a, b),
                    msg=(
                        f"zh-pair {i} expected SAME but similarity="
                        f"{similarity(a, b):.2f}\n  a={a!r}\n  b={b!r}"
                    ),
                )

    def test_chinese_synonym_canonicalisation(self) -> None:
        """P1-A：中文同義詞短語必須被折射為英文 canonical token。"""
        # 大於家族
        for word in ("超過", "大於", "高於", "多於", "超出"):
            norm = normalize(f"延遲 {word} 200ms")
            self.assertIn("gt", norm.split(),
                          f"中文 '{word}' 應折射為 'gt'，實得：{norm!r}")
        # 小於家族
        for word in ("低於", "小於", "少於", "不足"):
            norm = normalize(f"覆蓋率 {word} 100%")
            self.assertIn("lt", norm.split(),
                          f"中文 '{word}' 應折射為 'lt'，實得：{norm!r}")
        # concurrency 家族
        for phrase in ("並發 100", "併發 100", "同時 100"):
            norm = normalize(phrase)
            self.assertIn("concurrency", norm.split(),
                          f"中文 {phrase!r} 應折射為 'concurrency'，實得：{norm!r}")

    def test_chinese_stopword_removal(self) -> None:
        """P1-A：中文停用詞必須被 normalize 過濾。"""
        for sw in ("的", "之", "了", "為", "於", "在", "是", "則", "與", "及"):
            norm_tokens = normalize(f"檢查 {sw} 失敗").split()
            self.assertNotIn(
                sw, norm_tokens,
                msg=f"中文停用詞 '{sw}' 未被濾除，實得：{norm_tokens!r}",
            )

    def test_different_pairs_do_not_match(self) -> None:
        for i, (a, b) in enumerate(DIFFERENT_PAIRS):
            with self.subTest(pair=i):
                self.assertFalse(
                    is_same_pattern(a, b),
                    msg=f"pair {i} expected DIFFERENT but similarity={similarity(a, b):.2f}",
                )

    def test_best_match_returns_index(self) -> None:
        history = [
            "ADR-002 superseded by ADR-007",
            "test_login_p95 exceeded 200ms under 100 concurrent users",
            "Docker build failed — base image digest mismatch",
        ]
        curr = "test_login_p95 > 200ms at concurrency 100"
        idx = best_match(curr, history)
        self.assertEqual(idx, 1)

    def test_threshold_env_override(self) -> None:
        prev = os.environ.pop("SDD_PATTERN_MATCH_THRESHOLD", None)
        try:
            os.environ["SDD_PATTERN_MATCH_THRESHOLD"] = "0.99"
            # Under super-strict threshold even a paraphrase should fail
            self.assertFalse(
                is_same_pattern(
                    "test_login_p95 > 200ms at concurrency 100",
                    "test_login_p95 exceeded 200ms under 100 concurrent users",
                )
            )
        finally:
            if prev is None:
                os.environ.pop("SDD_PATTERN_MATCH_THRESHOLD", None)
            else:
                os.environ["SDD_PATTERN_MATCH_THRESHOLD"] = prev

    def test_synonym_canonicalisation(self) -> None:
        """P2-06 focused test for _SYNONYMS mapping.

        greater-than family, less-than family, and concurrency phrasing must
        normalise to the same canonical tokens so paraphrases compare as
        identical strings after `normalize`."""
        # greater-than family → "gt"
        for word in ("exceeded", "above", "greater"):
            norm = normalize(f"latency {word} 200ms")
            self.assertIn("gt", norm.split(),
                          f"'{word}' should canonicalise to 'gt', got: {norm!r}")
        # '>' symbol
        self.assertIn("gt", normalize("latency > 200ms").split())
        # less-than family → "lt"
        for word in ("below", "under"):
            norm = normalize(f"throughput {word} 50 rps")
            self.assertIn("lt", norm.split(),
                          f"'{word}' should canonicalise to 'lt', got: {norm!r}")
        # concurrency phrasing → "concurrency"
        for phrase in ("100 concurrent users", "concurrency 100"):
            norm = normalize(phrase)
            self.assertIn("concurrency", norm.split(),
                          f"{phrase!r} should canonicalise to 'concurrency', got: {norm!r}")

    def test_stopword_removal(self) -> None:
        """P2-06 focused test: stopwords ('the', 'a', 'is', 'at', 'on', 'of',
        'to', 'for', 'with', etc.) must be stripped by `normalize` so filler
        variance does not dilute similarity."""
        for sw in ("the", "a", "is", "at", "on", "of", "to", "for", "with"):
            norm_tokens = normalize(f"check {sw} failure").split()
            self.assertNotIn(
                sw, norm_tokens,
                msg=f"stopword '{sw}' leaked into normalised output: {norm_tokens!r}",
            )
        # Two phrases differing only by stopword padding must normalise to
        # the same token bag.
        a = normalize("the login failure is at the gateway")
        b = normalize("login failure gateway")
        self.assertEqual(set(a.split()), set(b.split()),
                         msg=f"stopword removal mismatch: {a!r} vs {b!r}")

    def test_threshold_clamp(self) -> None:
        """P2-06 focused test: SDD_PATTERN_MATCH_THRESHOLD must clamp to [0, 1]
        even when user sets out-of-range values. We probe behaviour indirectly
        through is_same_pattern because `_load_threshold` is private."""
        prev = os.environ.pop("SDD_PATTERN_MATCH_THRESHOLD", None)
        try:
            # Upper clamp: 2.0 → 1.0. Only truly identical strings match.
            os.environ["SDD_PATTERN_MATCH_THRESHOLD"] = "2.0"
            self.assertTrue(is_same_pattern("abc xyz", "abc xyz"))
            self.assertFalse(is_same_pattern(
                "test_login_p95 > 200ms at concurrency 100",
                "test_login_p95 exceeded 200ms under 100 concurrent users",
            ), "at threshold=1.0 paraphrase must not match")

            # Lower clamp: -0.5 → 0.0. Any non-empty pair matches.
            os.environ["SDD_PATTERN_MATCH_THRESHOLD"] = "-0.5"
            self.assertTrue(is_same_pattern("abc", "xyz"),
                            "at threshold=0.0 any non-empty pair must match")
            self.assertTrue(is_same_pattern(
                "completely unrelated one",
                "completely unrelated two",
            ))
        finally:
            if prev is None:
                os.environ.pop("SDD_PATTERN_MATCH_THRESHOLD", None)
            else:
                os.environ["SDD_PATTERN_MATCH_THRESHOLD"] = prev


class FSMRuntimePatternIntegrationTests(unittest.TestCase):
    """Verifies fsm_runtime uses the matcher for PR_REVIEW failures."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-pm.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _boot(self) -> FSMRuntime:
        state = load_state("pm-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "PR_REVIEW"
        return rt

    def test_paraphrased_failures_trigger_same_pattern(self) -> None:
        rt = self._boot()
        rt.record_gate_result("PR_REVIEW", "FAIL", reason="test_login_p95 > 200ms at concurrency 100")
        rt.state.current = "PR_REVIEW"  # simulate retry returning to PR_REVIEW
        rt.record_gate_result(
            "PR_REVIEW", "FAIL",
            reason="test_login_p95 exceeded 200ms under 100 concurrent users",
        )
        rt.state.current = "PR_REVIEW"
        rt.record_gate_result("PR_REVIEW", "FAIL", reason="login p95 above 200ms with 100 concurrency")
        entry = rt.state.root["retry_history"]["PR_REVIEW"]
        self.assertGreaterEqual(entry["same_pattern_count"], 3)
        self.assertEqual(len(entry["patterns"]), 3)
        self.assertTrue(entry["patterns"][-1]["matched_prev"])

    def test_different_failures_reset_same_pattern(self) -> None:
        rt = self._boot()
        rt.record_gate_result("PR_REVIEW", "FAIL", reason="test_login_p95 > 200ms at concurrency 100")
        rt.state.current = "PR_REVIEW"
        rt.record_gate_result("PR_REVIEW", "FAIL", reason="ADR-002 superseded by ADR-007")
        entry = rt.state.root["retry_history"]["PR_REVIEW"]
        self.assertEqual(entry["same_pattern_count"], 1)
        self.assertFalse(entry["patterns"][-1]["matched_prev"])


if __name__ == "__main__":
    unittest.main()
