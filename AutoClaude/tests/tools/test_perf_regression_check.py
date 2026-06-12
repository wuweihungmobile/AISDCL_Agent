"""tests/tools/test_perf_regression_check.py — W1 backlog P1-TEST-MIRROR-1 補建。

對應 tools/perf_regression_check.py（ADR-SD08-003 perf regression policy）。
紀律 #4「驗證鏡子自身要被驗證」— 升級判定工具必須有單元測試覆蓋 fake-PASS 拒絕。

對應修復來源：
- SD_09 W1 backlog P1-TEST-MIRROR-1（W3 zero-trust audit 識別）
- ADR-SD08-003 §2.4 三級告警 / §2.6 baseline samples < 20 BLOCK→WARN
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.perf_regression_check import (
    BLOCK_THRESHOLD,
    MIN_BASELINE_SAMPLES,
    SUBMS_JITTER_FLOOR_MS,
    WARN_THRESHOLD,
    build_pr_comment,
    check,
    classify,
    load_baseline,
    load_results,
)


# === classify 三級判定 ===

def test_classify_green_under_warn_threshold() -> None:
    """增量 < 10% → green。"""
    assert classify(0.0) == "green"
    assert classify(0.05) == "green"
    assert classify(WARN_THRESHOLD - 0.001) == "green"


def test_classify_warn_at_warn_threshold() -> None:
    """10% ≤ 增量 < 15% → warn。"""
    assert classify(WARN_THRESHOLD) == "warn"
    assert classify(0.12) == "warn"
    assert classify(BLOCK_THRESHOLD - 0.001) == "warn"


def test_classify_block_at_block_threshold() -> None:
    """增量 ≥ 15% → block。"""
    assert classify(BLOCK_THRESHOLD) == "block"
    assert classify(0.20) == "block"
    assert classify(1.0) == "block"


def test_classify_negative_delta_is_green() -> None:
    """負增量（效能改善）→ green。"""
    assert classify(-0.10) == "green"
    assert classify(-0.50) == "green"


# === load_baseline / load_results ===

def test_load_baseline_returns_empty_when_missing(tmp_path: Path) -> None:
    """不存在的 baseline → 回空 dict（不 raise）。"""
    assert load_baseline(tmp_path / "nonexistent.toml") == {}


def test_load_results_simple_format(tmp_path: Path) -> None:
    """格式 A: {scenario: p95_ms} 數字值。"""
    p = tmp_path / "results.json"
    p.write_text(json.dumps({"scenario_a": 100.5, "scenario_b": 50.0}), encoding="utf-8")
    results = load_results(p)
    assert results == {"scenario_a": 100.5, "scenario_b": 50.0}


def test_load_results_nested_format(tmp_path: Path) -> None:
    """格式 B: {scenario: {p95_ms: ...}} 巢狀 dict（write_perf_results 輸出）。"""
    p = tmp_path / "results.json"
    p.write_text(
        json.dumps({"scenario_a": {"p95_ms": 200.0, "p50_ms": 100.0}}),
        encoding="utf-8",
    )
    results = load_results(p)
    assert results == {"scenario_a": 200.0}


def test_load_results_pytest_benchmark_format(tmp_path: Path) -> None:
    """pytest-benchmark 格式：{benchmarks: [{name, stats: {mean}}]}。"""
    p = tmp_path / "results.json"
    p.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {"name": "bench_a", "stats": {"mean": 0.1}},  # 0.1s → 100ms
                    {"name": "bench_b", "stats": {"mean": 0.05}},
                ]
            }
        ),
        encoding="utf-8",
    )
    results = load_results(p)
    assert results == {"bench_a": 100.0, "bench_b": 50.0}


def test_load_results_returns_empty_when_missing(tmp_path: Path) -> None:
    """不存在 results → 回空 dict。"""
    assert load_results(tmp_path / "nonexistent.json") == {}


# === check 主流程 ===

def test_check_fails_when_baseline_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """baseline 不存在 → exit 1（紀律 #7 cache fresh + 紀律 #1 fail-loud）。"""
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"s": 100.0}), encoding="utf-8")

    rc = check(results, tmp_path / "nonexistent.toml")
    assert rc == 1
    captured = capsys.readouterr()
    assert "baseline 不存在或為空" in captured.out


def test_check_fails_when_results_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """results 空 → exit 1。"""
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        "[scenario_a]\np95_ms = 100.0\nsamples = 25\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text("{}", encoding="utf-8")

    rc = check(results, baseline)
    assert rc == 1
    captured = capsys.readouterr()
    assert "perf_results 為空" in captured.out


def test_check_green_when_under_warn_threshold(tmp_path: Path) -> None:
    """current < baseline×1.10 → green，exit 0。"""
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        "[scenario_a]\np95_ms = 100.0\nsamples = 25\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"scenario_a": 105.0}), encoding="utf-8")  # +5%

    rc = check(results, baseline)
    assert rc == 0


def test_check_warn_returns_rc_2_three_state(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """SD_09 W3 Round 2 audit P0-6：三態 rc — warn → rc=2（不阻塞但區分真綠）。

    紀律 #1「stage rc 必須反映真實狀態」— warn 與 green 必須以不同 rc 區分，
    上游 ps1 summary 才能正確顯示 perf=2 而非 perf=0 假象。
    """
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        "[scenario_a]\np95_ms = 100.0\nsamples = 25\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"scenario_a": 112.0}), encoding="utf-8")  # +12%

    rc = check(results, baseline)
    assert rc == 2, "warn 場景必須 rc=2 三態 (P0-6)"
    captured = capsys.readouterr()
    assert "::warning::" in captured.out


def test_check_block_returns_exit_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """增量 ≥ 15% + baseline samples ≥ 20 → block，exit 1。"""
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        "[scenario_a]\np95_ms = 100.0\nsamples = 25\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"scenario_a": 120.0}), encoding="utf-8")  # +20%

    rc = check(results, baseline)
    assert rc == 1
    captured = capsys.readouterr()
    assert "::error::" in captured.out


def test_check_block_downgrades_to_warn_when_undersampled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR-SD08-003 §2.6 — baseline samples < 20 時 BLOCK 退化為 WARN（語意一致）。

    紀律 #1：「stage rc 必須區分真實失敗 vs 工具標準回報」— samples 不足
    時不誠實標 fail（統計噪音偽陽率高）。

    SD_09 W3 Round 2 audit P0-6：BLOCK→WARN 退化 rc 從 0 升至 2（三態）。
    """
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        f"[scenario_a]\np95_ms = 100.0\nsamples = {MIN_BASELINE_SAMPLES - 1}\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"scenario_a": 120.0}), encoding="utf-8")  # +20% block

    rc = check(results, baseline)
    assert rc == 2, "samples 不足 BLOCK→WARN 應 rc=2 三態 (P0-6)"
    captured = capsys.readouterr()
    assert "BLOCK→WARN downgrade" in captured.out
    assert "statistical noise high" in captured.out


def test_check_block_at_min_samples_exact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SD_09 W3 Round 2 audit P1-7 邊界：samples = MIN_BASELINE_SAMPLES (20) 必須 BLOCK 不退化。

    紀律 #6「採集寬鬆 vs 升級嚴格分軌」— 達 20 是嚴格門檻起點，不應退化。
    """
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        f"[scenario_a]\np95_ms = 100.0\nsamples = {MIN_BASELINE_SAMPLES}\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"scenario_a": 120.0}), encoding="utf-8")  # +20% block

    rc = check(results, baseline)
    assert rc == 1, "samples=20 必須觸發真 BLOCK rc=1（邊界 P1-7）"
    captured = capsys.readouterr()
    assert "::error::" in captured.out
    assert "BLOCK→WARN downgrade" not in captured.out


def test_check_warn_alone_emits_rc_2_three_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P0-6 三態：純 warn (+12%) 無 block → rc=2 而非 rc=0。"""
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        f"[s1]\np95_ms = 100.0\nsamples = {MIN_BASELINE_SAMPLES}\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"s1": 113.0}), encoding="utf-8")  # +13%
    rc = check(results, baseline)
    assert rc == 2


def test_check_undersampled_warning_emitted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SD_09 W0 P1-F：baseline samples < 20 印 warning（即使 green）。"""
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        "[scenario_a]\np95_ms = 100.0\nsamples = 7\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"scenario_a": 102.0}), encoding="utf-8")  # +2% green

    rc = check(results, baseline)
    assert rc == 0
    captured = capsys.readouterr()
    assert "statistical noise high" in captured.out
    assert "not blocking" in captured.out


def test_check_subms_jitter_treated_as_green(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SD_09 R52 sub-ms deadlock 修復：token_halt_roundtrip 0.489→0.782ms（相對 +60%，
    絕對差 0.293ms < SUBMS_JITTER_FLOOR_MS 0.5）→ green rc=0（量測噪音非真實 regression）。

    取代 R31 P2-R31-2 純標籤路線（已證會造成 perf_baseline_lock 永遠 deadlock）。
    """
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        "[token_halt_roundtrip]\np95_ms = 0.489\nsamples = 7\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"token_halt_roundtrip": 0.782}), encoding="utf-8")

    rc = check(results, baseline)
    assert rc == 0, "sub-ms jitter（abs<0.5）應 green rc=0"
    captured = capsys.readouterr()
    assert "sub-ms jitter" in captured.out
    # 無 regression 級 annotation（emit_annotation 印 `title=Perf Warning/Regression`）；
    # 注意 samples<20 的統計噪音 `::warning::` 仍會印但不影響判定，故只檢 title=Perf。
    assert "title=Perf" not in captured.out
    assert "::error::" not in captured.out


def test_check_subms_real_regression_above_floor_not_masked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """floor 不遮蔽真退化：sub-ms baseline 但 current 跳至 3.0ms（abs 2.5 ≥ floor）→ 仍 block。

    samples=20（非 undersampled）→ 真 BLOCK rc=1，確保 floor 僅吸收噪音不掩蓋真實慢化。
    """
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        f"[token_halt_roundtrip]\np95_ms = 0.5\nsamples = {MIN_BASELINE_SAMPLES}\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"token_halt_roundtrip": 3.0}), encoding="utf-8")

    rc = check(results, baseline)
    assert rc == 1, "abs ≥ floor 的真實 sub-ms regression 仍須 block rc=1（不可遮蔽）"
    captured = capsys.readouterr()
    assert "::error::" in captured.out


def test_check_large_baseline_unaffected_by_subms_floor(tmp_path: Path) -> None:
    """回歸防護：100ms baseline +12%（abs 12ms >> floor）維持 warn rc=2，不被 floor 影響。"""
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        f"[s]\np95_ms = 100.0\nsamples = {MIN_BASELINE_SAMPLES}\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"s": 112.0}), encoding="utf-8")
    assert check(results, baseline) == 2


def test_check_writes_pr_comment(tmp_path: Path) -> None:
    """warn / block 場景應產出 PR comment markdown。"""
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        "[scenario_a]\np95_ms = 100.0\nsamples = 25\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"scenario_a": 112.0}), encoding="utf-8")  # +12% warn

    comment_path = tmp_path / "perf_regression_comment.md"
    rc = check(results, baseline, comment_out=comment_path)
    # SD_09 W3 Round 2 audit P0-6：warn 場景 rc=2 三態
    assert rc == 2
    assert comment_path.exists()
    content = comment_path.read_text(encoding="utf-8")
    assert "Perf Regression Alert" in content
    assert "scenario_a" in content


def test_check_no_pr_comment_when_all_green(tmp_path: Path) -> None:
    """全綠不寫 PR comment（避免訊號噪音）。"""
    baseline = tmp_path / "baseline.toml"
    baseline.write_text(
        "[scenario_a]\np95_ms = 100.0\nsamples = 25\n", encoding="utf-8"
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"scenario_a": 100.0}), encoding="utf-8")

    comment_path = tmp_path / "perf_regression_comment.md"
    rc = check(results, baseline, comment_out=comment_path)
    assert rc == 0
    assert not comment_path.exists(), "全綠時不應產出 PR comment"


def test_build_pr_comment_has_all_levels() -> None:
    """PR comment markdown 範本包含 ADR 引用 + 三級告警 emoji。"""
    rows = [
        {
            "scenario": "s1",
            "baseline_ms": 100.0,
            "current_ms": 105.0,
            "delta_pct": 0.05,
            "level": "green",
        },
        {
            "scenario": "s2",
            "baseline_ms": 100.0,
            "current_ms": 112.0,
            "delta_pct": 0.12,
            "level": "warn",
        },
        {
            "scenario": "s3",
            "baseline_ms": 100.0,
            "current_ms": 120.0,
            "delta_pct": 0.20,
            "level": "block",
        },
    ]
    md = build_pr_comment(rows)
    assert "ADR-SD08-003" in md
    assert "🟢" in md
    assert "🟡" in md
    assert "🔴" in md
    assert "+20.0%" in md
