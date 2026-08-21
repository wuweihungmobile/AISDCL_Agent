"""tools/perf_baseline_lock.py 單元測試 — SD_09 W2-#1（驗證鏡子；CLAUDE.md 紀律 #4）。

對應 [SD_Improving_09.md §W2 範圍外](../../docs/04_planning/SD_Improving_09.md)。
驗證 lock policy 能拒絕：(a) samples < 20；(b) 連續 < 7；(c) 增量 ≥ 15%。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.perf_baseline_lock import (
    CONSECUTIVE_RUNS,
    MIN_SAMPLES,
    append_history,
    load_baseline,
    load_history,
    load_results,
    reset_baseline,
    run,
    should_lock,
    write_baseline,
)


def _make_scen(p95: float, samples: int = MIN_SAMPLES) -> dict:
    return {"p50_ms": p95 * 0.5, "p95_ms": p95, "p99_ms": p95 * 1.1, "samples": samples}


def _write_results(path: Path, scenarios: dict) -> None:
    path.write_text(json.dumps(scenarios), encoding="utf-8")


def test_load_results_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_results(tmp_path / "missing.json")


def test_load_baseline_empty_when_missing(tmp_path):
    assert load_baseline(tmp_path / "nx.toml") == {}


def test_append_history_same_utc_date_dedup(tmp_path):
    """M-05 對齊：同 UTC date 多次 run 僅保留最新（不污染觀察期計數）。"""
    h = tmp_path / "hist.jsonl"
    append_history(
        h, {"timestamp": "2026-05-21T01:00:00+00:00", "scenarios": {"s": _make_scen(100)}}
    )
    append_history(
        h, {"timestamp": "2026-05-21T05:00:00+00:00", "scenarios": {"s": _make_scen(120)}}
    )
    records = load_history(h)
    assert len(records) == 1
    assert records[0]["scenarios"]["s"]["p95_ms"] == 120


def test_append_history_different_date_keeps_both(tmp_path):
    h = tmp_path / "hist.jsonl"
    append_history(
        h, {"timestamp": "2026-05-21T01:00:00+00:00", "scenarios": {"s": _make_scen(100)}}
    )
    append_history(
        h, {"timestamp": "2026-05-22T01:00:00+00:00", "scenarios": {"s": _make_scen(110)}}
    )
    assert len(load_history(h)) == 2


def test_should_lock_requires_consecutive_runs(tmp_path):
    """不足 CONSECUTIVE_RUNS=7 不可 lock。"""
    history = [
        {"scenarios": {"s": _make_scen(100)}} for _ in range(CONSECUTIVE_RUNS - 1)
    ]
    locked, _ = should_lock(history, "s", None)
    assert locked is False


def test_should_lock_rejects_low_samples(tmp_path):
    """samples < MIN_SAMPLES=20 任一筆 → 拒鎖。"""
    history = [
        {"scenarios": {"s": _make_scen(100)}} for _ in range(CONSECUTIVE_RUNS)
    ]
    history[3]["scenarios"]["s"]["samples"] = 15  # 一筆低於 MIN_SAMPLES
    locked, _ = should_lock(history, "s", None)
    assert locked is False


def test_should_lock_succeeds_without_baseline(tmp_path):
    """首次採集（無 baseline）連續 7 次 samples≥20 即 lock；取 max p95（最保守）。"""
    history = [
        {"scenarios": {"s": _make_scen(100 + i)}} for i in range(CONSECUTIVE_RUNS)
    ]
    locked, new_p95 = should_lock(history, "s", None)
    assert locked is True
    assert new_p95 == 100 + (CONSECUTIVE_RUNS - 1)  # 取 tail max


def test_should_lock_rejects_when_regression_exceeds_block(tmp_path):
    """既有 baseline 100ms，新 7 筆有任一 p95 ≥ 115ms（+15%）→ 拒鎖。"""
    history = [
        {"scenarios": {"s": _make_scen(110)}} for _ in range(CONSECUTIVE_RUNS - 1)
    ]
    history.append({"scenarios": {"s": _make_scen(116)}})  # +16% > BLOCK
    locked, _ = should_lock(history, "s", baseline_p95=100.0)
    assert locked is False


def test_should_lock_allows_within_tolerance(tmp_path):
    """既有 baseline 100ms，新 7 筆均 ≤ 114ms（< 115ms BLOCK）→ 允許 lock。"""
    history = [
        {"scenarios": {"s": _make_scen(100 + i)}} for i in range(CONSECUTIVE_RUNS)
    ]  # 100..106 均 < 115
    locked, new_p95 = should_lock(history, "s", baseline_p95=100.0)
    assert locked is True
    assert new_p95 == 106


def test_write_baseline_merges_existing(tmp_path):
    """新 lock 場景與既有 baseline 場景合併（不覆蓋未變更場景）。"""
    b = tmp_path / "base.toml"
    write_baseline(b, {"old_s": {"p50_ms": 1, "p95_ms": 2, "p99_ms": 3, "samples": MIN_SAMPLES}})
    write_baseline(b, {"new_s": {"p50_ms": 10, "p95_ms": 20, "p99_ms": 30, "samples": MIN_SAMPLES}})
    data = load_baseline(b)
    assert set(data.keys()) == {"old_s", "new_s"}
    assert data["old_s"]["p95_ms"] == 2
    assert data["new_s"]["p95_ms"] == 20


def test_reset_baseline_creates_backup(tmp_path):
    b = tmp_path / "p.toml"
    b.write_text("[s]\np95_ms = 1\n", encoding="utf-8")
    backup = reset_baseline(b)
    assert backup.exists()
    assert not b.exists()
    assert backup.read_text(encoding="utf-8") == "[s]\np95_ms = 1\n"


def test_reset_baseline_noop_when_missing(tmp_path):
    b = tmp_path / "missing.toml"
    backup = reset_baseline(b)
    # noop — 回傳原 path，無 file 寫入
    assert not backup.exists() or backup == b


def test_run_rejects_all_samples_low(tmp_path):
    """所有場景 samples<MIN → 印 warning 並 raise ValueError（不污染 history）。"""
    r = tmp_path / "res.json"
    _write_results(r, {"s": _make_scen(100, samples=10)})
    h = tmp_path / "h.jsonl"
    b = tmp_path / "b.toml"
    with pytest.raises(ValueError, match="no scenarios"):
        run(r, h, b)


def test_run_lock_after_seven_runs(tmp_path):
    """連續 7 次 samples=20 + 無 baseline → 一次 lock。"""
    r = tmp_path / "res.json"
    h = tmp_path / "h.jsonl"
    b = tmp_path / "b.toml"
    # 預灌 6 筆歷史（不同日）
    for i in range(CONSECUTIVE_RUNS - 1):
        append_history(
            h,
            {
                "timestamp": f"2026-05-{10 + i:02d}T01:00:00+00:00",
                "scenarios": {"s": _make_scen(100)},
            },
        )
    # 第 7 筆透過 run() 觸發
    _write_results(r, {"s": _make_scen(100)})
    result = run(r, h, b)
    assert result["status"] == "locked"
    assert "s" in result["locked"]
    assert b.exists()
    baseline = load_baseline(b)
    assert baseline["s"]["samples"] == MIN_SAMPLES


def test_run_lock_fields_come_from_same_record_def_200_164(tmp_path):
    """DEF-200-164：p50/p95/p99/samples 必須同出一次量測，不得出現 p99 < p95。

    tail 中 p95 最大的一筆（idx=3）刻意帶*不同*的 samples（25，非 MIN_SAMPLES）；
    tail 最後一筆（舊邏輯的 `tail_last`）刻意帶*較低* p95/p99（90/99 < 150）。
    舊邏輯（p50/p99 取 tail 最後一筆、samples 硬寫 MIN_SAMPLES）會寫出
    p99(99) < p95(150) 的自相矛盾 baseline，且 samples 與貢獻 p95 的那一筆對不上。
    """
    r = tmp_path / "res.json"
    h = tmp_path / "h.jsonl"
    b = tmp_path / "b.toml"
    for i in range(CONSECUTIVE_RUNS - 1):
        scen = _make_scen(150, samples=25) if i == 3 else _make_scen(100)
        append_history(
            h,
            {"timestamp": f"2026-05-{10 + i:02d}T01:00:00+00:00", "scenarios": {"s": scen}},
        )
    _write_results(r, {"s": _make_scen(90)})  # 最後一筆（tail_last）刻意最低
    result = run(r, h, b)
    assert result["status"] == "locked"
    baseline = load_baseline(b)["s"]
    assert baseline["p95_ms"] == 150
    assert baseline["p99_ms"] >= baseline["p95_ms"], "p99 倒掛 p95——分位數取自不同記錄"
    assert baseline["samples"] == 25, "samples 須為貢獻該 p95 那一筆的真實樣本數"


def test_should_lock_allows_subms_jitter_despite_relative_excess(tmp_path):
    """SD_09 R52 sub-ms deadlock 修復：baseline 0.489ms，tail 含 0.782ms（相對 +60%
    超 BLOCK_THRESHOLD，但絕對差 0.293ms < SUBMS_JITTER_FLOOR_MS 0.5）
    → 視為 jitter 容忍 → 允許 re-lock。

    這正是 token_halt_roundtrip 永遠卡 samples=7 的根因；
    修復後 baseline 得以 re-lock 至 samples=20。
    """
    # tail 7 筆模擬真實 token_halt jitter（0.47~0.782），全部 abs<0.5ms of 0.489 baseline
    jitter = [0.47, 0.489, 0.551, 0.771, 0.782, 0.46, 0.5]
    history = [{"scenarios": {"s": _make_scen(p)}} for p in jitter]
    locked, new_p95 = should_lock(history, "s", baseline_p95=0.489)
    assert locked is True, "sub-ms jitter（abs<0.5）即使相對超標仍應允許 re-lock"
    assert new_p95 == max(jitter)  # 取最保守 max


def test_should_lock_rejects_real_subms_regression_above_floor(tmp_path):
    """sub-ms 場景的「真實」regression（abs ≥ floor）仍須拒鎖 — 確保 floor 不遮蔽真退化。

    baseline 0.489ms，tail 含 2.0ms（abs 1.511 ≥ 0.5 floor 且相對 +309%）→ 拒鎖。
    """
    history = [{"scenarios": {"s": _make_scen(0.49)}} for _ in range(CONSECUTIVE_RUNS - 1)]
    history.append({"scenarios": {"s": _make_scen(2.0)}})  # abs 1.511 > floor
    locked, _ = should_lock(history, "s", baseline_p95=0.489)
    assert locked is False, "abs ≥ floor 的真實 sub-ms regression 仍須拒鎖（不可遮蔽）"


def test_subms_floor_does_not_affect_large_baseline_scenarios(tmp_path):
    """回歸防護：大基線場景（100ms）不受 sub-ms floor 影響 — +16% 相對（abs 16ms >> 0.5）仍拒鎖。"""
    history = [{"scenarios": {"s": _make_scen(110)}} for _ in range(CONSECUTIVE_RUNS - 1)]
    history.append({"scenarios": {"s": _make_scen(116)}})  # +16%, abs 16 >> floor
    locked, _ = should_lock(history, "s", baseline_p95=100.0)
    assert locked is False


def test_run_observing_when_baseline_regression_too_large(tmp_path):
    """既有 baseline 100ms，新一筆 130ms (+30%) → observing（拒 lock）。"""
    r = tmp_path / "res.json"
    h = tmp_path / "h.jsonl"
    b = tmp_path / "b.toml"
    b.write_text("[s]\np50_ms = 50\np95_ms = 100\np99_ms = 110\nsamples = 20\n", encoding="utf-8")
    _write_results(r, {"s": _make_scen(130)})
    result = run(r, h, b)
    assert result["status"] == "observing"
    assert "s" in result["observing"]
    # 增量太大 → runs_collected 中斷在第 1 筆即 break
    assert result["observing"]["s"]["runs_collected"] == 0
