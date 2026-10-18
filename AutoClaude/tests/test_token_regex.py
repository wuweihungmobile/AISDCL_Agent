"""T7（SD_04 §3 / M-4）：context_patterns regex 補全驗證。

驗證新增的 3 個 Claude Code 實際輸出格式 regex 能正確萃取百分比，
並確認既有 4 個格式仍然正常運作（回歸防護）。
"""
from __future__ import annotations

from autoclaude.utils.config import TokenGuardConfig
from autoclaude.utils.token_tracker import (
    build_patterns,
    context_pct_from_claude_json,
    extract_context_pct,
)

# ══════════════════════════════════════════════
# 既有 4 種格式回歸測試（避免 T7 補強引入回歸）
# ══════════════════════════════════════════════

class TestLegacyPatternsStillWork:
    def test_percent_context_format(self):
        assert extract_context_pct("Processing... 92% context used") == 92.0

    def test_context_colon_percent_format(self):
        # 既有 pattern2: (?:context|token)\w*[\s:]+(\d+(?:\.\d+)?)\s*%
        # 直接接數字（無 "usage" 中介詞）
        assert extract_context_pct("tokens: 88%") == 88.0
        assert extract_context_pct("context: 95%") == 95.0

    def test_n_over_m_tokens_lowercase(self):
        pct = extract_context_pct("190000 / 200000 tokens")
        assert pct is not None and abs(pct - 95.0) < 0.01

    def test_autoclaude_marker(self):
        assert extract_context_pct("[CONTEXT_USAGE: 87.3%]") == 87.3


# ══════════════════════════════════════════════
# T7 新增 3 種格式
# ══════════════════════════════════════════════

class TestNewClaudeCodeFormats:
    def test_context_window_format(self):
        """Claude Code 'Context window: N / M tokens' 格式。"""
        pct = extract_context_pct("Context window: 150000 / 200000 tokens")
        assert pct is not None
        assert abs(pct - 75.0) < 0.01

    def test_context_window_partial_match(self):
        """確認真實輸出中的 Context window 行能解析。"""
        line = "  > Context window: 95000 / 100000 tokens used"
        pct = extract_context_pct(line)
        assert pct is not None
        assert abs(pct - 95.0) < 0.01

    def test_stats_usage_marker(self):
        """[STATS: usage N%] 簡短標記。"""
        assert extract_context_pct("[STATS: usage 78%]") == 78.0

    def test_stats_usage_marker_decimal(self):
        """[STATS: usage 88.5%] 含小數。"""
        assert extract_context_pct("[STATS: usage 88.5%]") == 88.5

    def test_token_usage_max_format(self):
        """'Token usage: N tokens / max M' 格式。"""
        pct = extract_context_pct("Token usage: 8000 tokens / max 10000")
        assert pct is not None
        assert abs(pct - 80.0) < 0.01

    def test_token_usage_max_full_capacity(self):
        pct = extract_context_pct("Token usage: 100000 tokens / max 100000")
        assert pct is not None
        assert abs(pct - 100.0) < 0.01

    def test_token_usage_max_zero_division_safe(self):
        """分母 0 時不應拋例外。"""
        assert extract_context_pct("Token usage: 0 tokens / max 0") is None


# ══════════════════════════════════════════════
# Multi-pattern interaction
# ══════════════════════════════════════════════

class TestMultiPatternInteraction:
    def test_takes_highest_when_multiple_match(self):
        """同行多個 pattern 命中時取最高值。"""
        line = "Context window: 50000 / 100000 tokens, but [STATS: usage 92%]"
        # window=50%, stats=92% → 取 92
        assert extract_context_pct(line) == 92.0

    def test_no_match_returns_none(self):
        assert extract_context_pct("Compiling source files...") is None

    def test_invalid_percent_out_of_range(self):
        """超出 0-100% 範圍的數值應被忽略。"""
        # "150% context" 雖匹配，但 >100 應被丟棄
        assert extract_context_pct("usage 150% context") is None


# ══════════════════════════════════════════════
# 驗證 TokenGuardConfig 預設值與 _DEFAULT_PATTERNS 一致
# ══════════════════════════════════════════════

class TestConfigSync:
    def test_config_default_patterns_count(self):
        """TokenGuardConfig 預設 patterns 共 7 個（4 舊 + 3 新）。"""
        cfg = TokenGuardConfig()
        assert len(cfg.context_patterns) == 7

    def test_config_patterns_all_compile(self):
        """TokenGuardConfig 所有預設 patterns 必須是合法 regex。"""
        cfg = TokenGuardConfig()
        compiled = build_patterns(cfg.context_patterns)
        # build_patterns 會丟棄無效項；數量應與原本相同
        assert len(compiled) == len(cfg.context_patterns)

    def test_new_patterns_match_real_outputs(self):
        """以 TokenGuardConfig 的 patterns 萃取百分比，覆蓋 3 種新格式。"""
        cfg = TokenGuardConfig()
        compiled = build_patterns(cfg.context_patterns)
        assert extract_context_pct(
            "Context window: 75000 / 100000 tokens", compiled
        ) == 75.0
        assert extract_context_pct("[STATS: usage 65%]", compiled) == 65.0
        pct = extract_context_pct("Token usage: 9000 tokens / max 10000", compiled)
        assert pct is not None and abs(pct - 90.0) < 0.01


# ══════════════════════════════════════════════
# Dev-7：邊界 / ReDoS 防護測試
# ══════════════════════════════════════════════

class TestEdgeCasesAndReDoS:
    def test_empty_string(self):
        """空字串輸入不應拋例外。"""
        assert extract_context_pct("") is None

    def test_whitespace_only(self):
        """純空白輸入回傳 None。"""
        assert extract_context_pct("   \t\n  ") is None

    def test_very_long_input_no_match_runs_fast(self):
        """長字串無 match 時應在合理時間完成（避免 catastrophic backtracking）。"""
        import time
        # 10 KB 隨機文字，無 % 號
        long_input = "abc def " * 1000
        start = time.perf_counter()
        result = extract_context_pct(long_input)
        elapsed = time.perf_counter() - start
        assert result is None
        assert elapsed < 1.0, f"regex 應在 1s 內完成，實際 {elapsed:.3f}s"

    def test_very_long_input_with_match_runs_fast(self):
        """長字串末段有 match 時亦應快速完成。"""
        import time
        long_input = ("noise " * 5000) + "[CONTEXT_USAGE: 67%]"
        start = time.perf_counter()
        result = extract_context_pct(long_input)
        elapsed = time.perf_counter() - start
        assert result == 67.0
        assert elapsed < 1.0

    def test_pathological_repeated_percent(self):
        """重複大量 N% context 模式不應拖慢解析。"""
        import time
        # 100 個重複 pattern 串接
        pathological = "50% context " * 100
        start = time.perf_counter()
        result = extract_context_pct(pathological)
        elapsed = time.perf_counter() - start
        # 取最高值（皆為 50% → 50）
        assert result == 50.0
        assert elapsed < 1.0

    def test_unicode_input_safe(self):
        """含 Unicode（中文 / emoji）的輸入不應拋例外。"""
        assert extract_context_pct("處理中... 92% context 已用 🚀") == 92.0

    def test_negative_number_not_matched(self):
        """負數百分比不應被匹配為合法值（Dev-Minor-7：精準化斷言）。"""
        # 實作層會在 match 前綴偵測到 "-" 直接跳過，預期回傳 None
        result = extract_context_pct("usage -50% context")
        assert result is None

    def test_extreme_n_over_m_ratio(self):
        """N >> M 的異常比率（>100%）應被丟棄。"""
        # 999999 / 100 → 999999%，超出 0~100 範圍應被忽略
        result = extract_context_pct("999999 / 100 tokens")
        assert result is None


# ══════════════════════════════════════════════
# W-82-1 / DEF-81-001：context_pct_from_claude_json（claude -p --output-format json
# 結構化用量推算近似 context%，PTY 訊號源根因修復）
# ══════════════════════════════════════════════

# claude 2.1.144 親跑真實 JSON 樣本（improving_82 §2.3 取證）：
# used = 6 + 21676 + 37121 = 58803；window = max(200000, 1000000) = 1000000 → 5.8803%
_REAL_CLAUDE_JSON = {
    "type": "result",
    "subtype": "success",
    "result": "ok",
    "usage": {
        "input_tokens": 6,
        "cache_creation_input_tokens": 37121,
        "cache_read_input_tokens": 21676,
        "output_tokens": 6,
    },
    "modelUsage": {
        "claude-haiku-4-5-20251001": {"inputTokens": 441, "contextWindow": 200000},
        "claude-opus-4-7[1m]": {"inputTokens": 6, "contextWindow": 1000000},
    },
}


class TestContextPctFromClaudeJson:
    def test_context_pct_from_real_claude_json(self):
        """RTM-82-1：真實 JSON 樣本算出正確近似 context%（≈5.88%）。"""
        pct = context_pct_from_claude_json(_REAL_CLAUDE_JSON)
        assert pct is not None
        assert abs(pct - 5.8803) < 0.001

    def test_context_pct_uses_max_context_window(self):
        """RTM-82-2：多模型取最大 contextWindow（主模型基準），非首個/最小。"""
        # 同一 used，但若誤取 haiku 的 200000 會得 ~29.4% 而非 ~5.88%
        pct = context_pct_from_claude_json(_REAL_CLAUDE_JSON)
        used = 6 + 21676 + 37121
        assert pct is not None and abs(pct - used / 1_000_000 * 100) < 0.001

    def test_context_pct_none_on_missing_usage(self):
        """RTM-82-3：缺 usage → None（訊號源未產出，非 0.0 偽裝）。"""
        assert context_pct_from_claude_json({"modelUsage": {"m": {"contextWindow": 1000}}}) is None

    def test_context_pct_none_on_missing_model_usage(self):
        """RTM-82-3：缺 modelUsage → None。"""
        assert context_pct_from_claude_json({"usage": {"input_tokens": 100}}) is None

    def test_context_pct_none_on_zero_window(self):
        """RTM-82-3：window<=0 → None（不除以零、不偽裝）。"""
        parsed = {"usage": {"input_tokens": 100}, "modelUsage": {"m": {"contextWindow": 0}}}
        assert context_pct_from_claude_json(parsed) is None

    def test_context_pct_none_on_zero_used(self):
        """RTM-82-3：used<=0 → None。"""
        parsed = {"usage": {"input_tokens": 0}, "modelUsage": {"m": {"contextWindow": 1000}}}
        assert context_pct_from_claude_json(parsed) is None

    def test_context_pct_clamped_to_100(self):
        """RTM-82-4：used > window（異常）時 clamp 至 100，不回報 >100。"""
        parsed = {
            "usage": {"input_tokens": 5_000_000},
            "modelUsage": {"m": {"contextWindow": 1_000_000}},
        }
        assert context_pct_from_claude_json(parsed) == 100.0

    def test_context_pct_none_on_non_dict(self):
        """RTM-82-3：非 dict 輸入（None / 字串）→ None，不拋例外。"""
        assert context_pct_from_claude_json(None) is None  # type: ignore[arg-type]
        assert context_pct_from_claude_json("not a dict") is None  # type: ignore[arg-type]


# ══════════════════════════════════════════════
# 整合輪 116 DF-A（DEF-200-550）：頂層 usage 是跨回合累計，目前 context 取 usage.iterations[-1]
# 夾具＝2026-10-18 真實 haiku 在真實 AutoClaude 樹跑 16 回合的 claude -p JSON（去掉 result 長文）：
# 累計 24+1,354,671+110,846 = 1,465,541 → 146.6% 夾成 100%（偽 TOKEN_HALT）；
# iterations[-1] = 2+129,496+625 = 130,123 → 13.0123%。
# ══════════════════════════════════════════════
_HALT_FIXTURE_CLAUDE_JSON = {
    "type": "result",
    "subtype": "success",
    "num_turns": 16,
    "usage": {
        "input_tokens": 24,
        "cache_creation_input_tokens": 110846,
        "cache_read_input_tokens": 1354671,
        "output_tokens": 9093,
        "iterations": [
            {
                "input_tokens": 2,
                "output_tokens": 1312,
                "cache_read_input_tokens": 129496,
                "cache_creation_input_tokens": 625,
                "type": "message",
            }
        ],
    },
    "modelUsage": {
        "claude-haiku-5-5": {"inputTokens": 24, "contextWindow": 1000000},
    },
}


class TestContextPctUsesLatestIteration:
    def test_latest_iteration_not_cumulative(self):
        """DEF-200-550：真實樹 16 回合的夾具必須算成 13.0%，不是累計夾成的 100%。"""
        pct = context_pct_from_claude_json(_HALT_FIXTURE_CLAUDE_JSON)
        assert pct is not None
        assert abs(pct - 13.0123) < 0.001

    def test_cumulative_fallback_when_iterations_absent(self):
        """舊形狀（沒有 iterations）逐字維持累計算法；本夾具去掉 iterations 後仍夾成 100。"""
        cumulative_only = {
            k: v for k, v in _HALT_FIXTURE_CLAUDE_JSON["usage"].items() if k != "iterations"
        }
        parsed = {"usage": cumulative_only, "modelUsage": _HALT_FIXTURE_CLAUDE_JSON["modelUsage"]}
        assert context_pct_from_claude_json(parsed) == 100.0

    def test_cumulative_fallback_when_iterations_unusable(self):
        """iterations 是空 list／末筆不是映射／末筆沒有任何 context 鍵 ⇒ 退回累計值。"""
        base = _HALT_FIXTURE_CLAUDE_JSON["usage"]
        for bad in ([], [None], [{"output_tokens": 1312, "type": "message"}], "x", 7):
            usage = {**base, "iterations": bad}
            parsed = {"usage": usage, "modelUsage": _HALT_FIXTURE_CLAUDE_JSON["modelUsage"]}
            assert context_pct_from_claude_json(parsed) == 100.0, bad

    def test_single_turn_latest_equals_cumulative(self):
        """只跑一回合時最後一回合＝累計（操作員 1 回合實測相等），兩種算法同值。"""
        single = {"input_tokens": 6, "cache_read_input_tokens": 21676,
                  "cache_creation_input_tokens": 37121, "output_tokens": 6}
        parsed = {
            "usage": {**single, "iterations": [dict(single, type="message")]},
            "modelUsage": {"m": {"contextWindow": 1_000_000}},
        }
        pct = context_pct_from_claude_json(parsed)
        assert pct is not None and abs(pct - 5.8803) < 0.001

    def test_latest_iteration_takes_the_last_element(self):
        """多筆 iterations 取**最後**一筆（最新一次 API 呼叫），不是第一筆也不是加總。"""
        parsed = {
            "usage": {
                "input_tokens": 100, "cache_read_input_tokens": 900_000,
                "cache_creation_input_tokens": 0,
                "iterations": [
                    {"input_tokens": 1, "cache_read_input_tokens": 50_000,
                     "cache_creation_input_tokens": 0},
                    {"input_tokens": 1, "cache_read_input_tokens": 80_000,
                     "cache_creation_input_tokens": 0},
                ],
            },
            "modelUsage": {"m": {"contextWindow": 1_000_000}},
        }
        pct = context_pct_from_claude_json(parsed)
        assert pct is not None and abs(pct - 8.0001) < 0.001

    def test_context_pct_ignores_bool_values(self):
        """bool 是 int 子類；usage 欄位為 True/False 時不可誤當 token 數累加。"""
        parsed = {
            "usage": {"input_tokens": True, "cache_read_input_tokens": 500},
            "modelUsage": {"m": {"contextWindow": 1000}},
        }
        # input_tokens=True 被忽略，只算 cache_read 500 → 50%
        assert context_pct_from_claude_json(parsed) == 50.0
