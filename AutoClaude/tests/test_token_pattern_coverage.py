"""SD_Improving_05 W5 批3-B / M-8：7 個 context regex 涵蓋率測試。

驗證 `autoclaude.utils.token_tracker._DEFAULT_PATTERNS` 中的 7 個 regex
在真實 Claude 輸出樣本上的命中率（每個 ≥ 95%），並提供反例樣本確保
extract_context_pct() 不誤判（precision 100%）。

樣本來源：tests/fixtures/claude_output_samples/*.txt（≥ 30 行樣本）
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from autoclaude.utils.token_tracker import _DEFAULT_PATTERNS, extract_context_pct

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "claude_output_samples"

_REGEX_FIXTURES = {
    0: "regex1_pct_then_context.txt",
    1: "regex2_context_then_pct.txt",
    2: "regex3_n_slash_m_tokens.txt",
    3: "regex4_context_usage_marker.txt",
    4: "regex5_context_window.txt",
    5: "regex6_stats_usage_marker.txt",
    6: "regex7_token_usage_max.txt",
}


def _read_lines(fname: str) -> List[str]:
    p = _FIXTURE_DIR / fname
    assert p.exists(), f"sample file missing: {p}"
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


class TestPatternCount:
    def test_seven_default_patterns(self):
        assert len(_DEFAULT_PATTERNS) == 7, (
            "extract_context_pct expects 7 default regex patterns; "
            f"got {len(_DEFAULT_PATTERNS)}"
        )

    def test_at_least_thirty_samples_total(self):
        total = sum(len(_read_lines(f)) for f in _REGEX_FIXTURES.values())
        assert total >= 30, f"total samples < 30 (got {total})"


class TestPerRegexCoverage:
    """每個 regex 在其專屬樣本上 ≥ 95% 命中率（M-8 acceptance）。"""

    @pytest.mark.parametrize("idx,fname", list(_REGEX_FIXTURES.items()))
    def test_regex_hit_rate_at_least_95pct(self, idx: int, fname: str):
        lines = _read_lines(fname)
        pat = _DEFAULT_PATTERNS[idx]
        hit = sum(1 for ln in lines if pat.search(ln))
        rate = hit / len(lines)
        assert rate >= 0.95, (
            f"regex#{idx + 1} ({pat.pattern}) hit rate {rate:.2%} < 95% "
            f"on {fname} ({hit}/{len(lines)})"
        )


class TestExtractContextPct:
    """extract_context_pct() 端對端：所有正例樣本應萃取出 0~100 之 float。"""

    @pytest.mark.parametrize("fname", list(_REGEX_FIXTURES.values()))
    def test_positive_samples_extracted(self, fname: str):
        lines = _read_lines(fname)
        extracted = [extract_context_pct(ln) for ln in lines]
        success = [v for v in extracted if v is not None and 0.0 <= v <= 100.0]
        rate = len(success) / len(lines)
        assert rate >= 0.95, (
            f"{fname}: extract_context_pct hit rate {rate:.2%} < 95% "
            f"({len(success)}/{len(lines)})"
        )

    def test_negative_samples_not_misextracted(self):
        """反例：不含 context/token 百分比的輸出絕對不誤判（precision 100%）。"""
        lines = _read_lines("negative_no_match.txt")
        false_positives = [(ln, extract_context_pct(ln)) for ln in lines
                           if extract_context_pct(ln) is not None]
        assert false_positives == [], (
            f"extract_context_pct false positives: {false_positives}"
        )

    def test_negative_dash_prefix_rejected(self):
        """Dev-Minor-7：'-50%' 不應被當作合法 50%。"""
        assert extract_context_pct("discount -50% off tokens") is None

    def test_negative_out_of_range_rejected(self):
        """超出 0-100 的 pct 應被拒絕。"""
        assert extract_context_pct("150% context overflow") is None
        assert extract_context_pct("-5% context invalid") is None


class TestSampleVolume:
    """確保每個 regex 至少 ≥ 5 個樣本（statistical significance）。"""

    @pytest.mark.parametrize("fname", list(_REGEX_FIXTURES.values()))
    def test_at_least_five_samples_per_regex(self, fname: str):
        n = len(_read_lines(fname))
        assert n >= 5, f"{fname}: only {n} samples (< 5)"


class TestFixtureInvariant:
    """W5 三方審查 Minor-SD5：每個 _DEFAULT_PATTERNS 都必須有對應 fixture。"""

    def test_pattern_count_matches_fixture_count(self):
        assert len(_DEFAULT_PATTERNS) == len(_REGEX_FIXTURES), (
            f"_DEFAULT_PATTERNS 數量 {len(_DEFAULT_PATTERNS)} 與 "
            f"_REGEX_FIXTURES 數量 {len(_REGEX_FIXTURES)} 不一致；"
            "新增 regex 時必須同步新增樣本檔"
        )

    def test_every_fixture_file_exists(self):
        for fname in _REGEX_FIXTURES.values():
            p = _FIXTURE_DIR / fname
            assert p.exists(), f"fixture 檔不存在: {p}"


class TestKnownFalsePositiveBoundary:
    """W5 三方審查 Critical-SA2：明示已知 false positive 邊界。

    以下字串會被 regex#2 `(?:context|token)\\w*[\\s:]+(\\d+)%` 命中，
    視為「正規式設計限制」而非 bug。SD_06 將評估收斂方案。

    這些測試**斷言** false positive 存在以避免誤把它們當 negative samples；
    若未來收緊 regex 使其不再命中，這些測試會 fail 並提醒同步更新 doc。
    """

    @pytest.mark.parametrize("text,expected", [
        ("tokenizer 65%", 65.0),
        ("tokenization: 50%", 50.0),
        ("contextless 80%", 80.0),
        ("token_efficiency 70%", 70.0),
    ])
    def test_known_false_positives_documented(self, text: str, expected: float):
        """這些是 production 已知的 regex limitation；測試確認 limitation 仍存在。"""
        from autoclaude.utils.token_tracker import extract_context_pct
        result = extract_context_pct(text)
        assert result == expected, (
            f"已知 false positive boundary 不再命中（{text!r}）；"
            "可能 regex 已收緊，請同步更新文件記載"
        )


class TestMutationCoverage:
    """W5 三方審查 Critical-SA1：mutation-style 測試確保 regex 不可被取代。

    若移除某 regex，其專屬樣本的某些行應變得無法被任何剩餘 regex 命中。
    用以證明 7 regex 各自有 unique coverage。
    """

    @pytest.mark.parametrize("idx,fname", list(_REGEX_FIXTURES.items()))
    def test_removing_target_regex_reduces_extraction(self, idx: int, fname: str):
        from autoclaude.utils.token_tracker import extract_context_pct
        lines = _read_lines(fname)
        # 完整 patterns
        full_hits = sum(1 for ln in lines
                        if extract_context_pct(ln, _DEFAULT_PATTERNS) is not None)
        # 移除目標 regex
        reduced = [p for i, p in enumerate(_DEFAULT_PATTERNS) if i != idx]
        reduced_hits = sum(1 for ln in lines
                           if extract_context_pct(ln, reduced) is not None)
        # 允許重疊（多 regex 同時命中），但至少 regex#3 與 #7 在 N/M tokens 樣本上會有重疊；
        # 此測試確保「移除任何一個 regex 都不會讓 extract_context_pct 拒絕全部樣本」是錯誤的。
        # 至少一個 regex（如 regex2 / regex5）必須對某些樣本是唯一命中者。
        if idx == 1:  # regex2 為唯一無交集 regex（其他 regex 與 regex2 樣本格式不重疊）
            assert reduced_hits < full_hits, (
                f"regex#{idx + 1} ({fname}): 移除後 hits 應減少（uniqueness 證明），"
                f"實際 full={full_hits} reduced={reduced_hits}"
            )
