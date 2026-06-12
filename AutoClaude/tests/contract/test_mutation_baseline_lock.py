"""SD_Improving_08 W3 T3-D9 — mutation baseline lock contract test。

對應 [ADR-SD08-002 §2.4 + §2.5](../../docs/04_planning/ADR/ADR-SD08-002-mutation-baseline.md)
與 [SD08_Execution_Guide.md G3 驗證](../../docs/05_development/SD08_Execution_Guide.md)。

驗收門檻：
  - 連續 7 次達 (TARGET - 0.05) → 鎖定 baseline，取 min 為最保守值
  - 抖動單日不鎖（任一 < threshold 即不滿足）
  - 未達 7 次仍 observing
  - 鎖後僅在新 baseline 高於舊值時升級（不退步）

≥ 4 case：未達 7 次 / 達 7 次鎖定 / 抖動單日不鎖 / 鎖後升級。
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from tools.mutation_baseline_lock import (
    CONSECUTIVE_RUNS,
    TARGETS,
    TOLERANCE,
    calc_kill_rate,
    parse_mutmut_log,
    read_baseline,
    run,
    should_lock,
    write_baseline,
)
from tools.mutation_analysis import (
    analyze,
    classify_diff,
    extract_survived_ids,
)


def _write_mutmut_log(path: Path, killed: int = 75, survived: int = 20, timeout: int = 3, suspicious: int = 2,
                     skipped: int = 0) -> None:
    """模擬 mutmut results 輸出（涵蓋 emoji 與純文字兩種格式）。"""
    path.write_text(
        f"""Legend for output:
🎉 Killed mutants. The goal is for everything to end up in this bucket.
⏰ Timeout. Test suite took 10 times as long as the baseline so were killed.
🤔 Suspicious. Tests took a long time, but not long enough to be fatal.
🙁 Survived. This means your tests need to be expanded.
🔇 Skipped. Skipped.

🎉 Killed ({killed})
🙁 Survived ({survived})
⏰ Timeout ({timeout})
🤔 Suspicious ({suspicious})
🔇 Skipped ({skipped})
""",
        encoding="utf-8",
    )


def _append_history(history_path: Path, module: str, kill_rates: list[float]) -> None:
    """預灌歷史紀錄。

    日期從「今日 UTC」往前推 len(kill_rates) 天，避免與 run() 寫入的當日紀錄
    觸發 M-05 同 UTC date 去重邏輯（tools/mutation_baseline_lock.py:121-128）。

    SD_09 W3 Round 4 audit P0-AUDIT-R3-2 修復：每筆預灌紀錄附 unique sha，
    滿足新增的紀律 #12 強制 unique 檢查，且不破壞 contract 既有測試意圖。
    """
    today = _dt.datetime.now(tz=_dt.timezone.utc).date()
    n = len(kill_rates)
    with history_path.open("w", encoding="utf-8") as f:
        for i, rate in enumerate(kill_rates):
            # 倒推：第 0 筆為 n 天前，第 n-1 筆為 1 天前；今日由 run() 寫入
            day = today - _dt.timedelta(days=n - i)
            rec = {
                "timestamp": f"{day.isoformat()}T02:00:00+00:00",
                "module": module,
                "kill_rate": rate,
                "counts": {"killed": int(rate * 100), "survived": int((1 - rate) * 100)},
                "source_sha256": f"preload{i:09d}",  # Round 4 P0-AUDIT-R3-2 unique sha
            }
            f.write(json.dumps(rec) + "\n")


# ====================== T3-D9 必備 4 case ======================


def test_observing_under_seven_runs(tmp_path: Path) -> None:
    """case 1：累積 < 7 次 → observing，不寫 baseline。"""
    log = tmp_path / "mutation_token_guard.log"
    _write_mutmut_log(log)
    history = tmp_path / ".mutation_history.jsonl"
    baseline = tmp_path / ".mutation_baseline.toml"

    result = run("token_guard", log, history, baseline)

    assert result["status"] == "observing"
    assert result["runs_collected"] == 1
    assert result["runs_needed"] == CONSECUTIVE_RUNS - 1
    assert not baseline.exists() or "token_guard" not in read_baseline(baseline)


def test_lock_after_seven_consecutive_pass(tmp_path: Path) -> None:
    """case 2：連續 7 次均 ≥ (target - tolerance) → 鎖定 baseline。"""
    log = tmp_path / "mutation_token_guard.log"
    history = tmp_path / ".mutation_history.jsonl"
    baseline = tmp_path / ".mutation_baseline.toml"

    threshold = TARGETS["token_guard"] - TOLERANCE  # 0.70
    # 預灌 6 次達標紀錄
    _append_history(history, "token_guard", [threshold + 0.02] * 6)
    # 第 7 次跑：剛好達標
    _write_mutmut_log(log, killed=72, survived=28, timeout=0, suspicious=0)

    result = run("token_guard", log, history, baseline)

    assert result["status"] == "locked"
    assert result["baseline"] >= threshold
    locked = read_baseline(baseline)
    assert "token_guard" in locked
    assert locked["token_guard"] >= threshold


def test_no_lock_on_single_day_dip(tmp_path: Path) -> None:
    """case 3：6 次達標 + 1 次低於門檻（抖動）→ 不鎖定。"""
    log = tmp_path / "mutation_token_guard.log"
    history = tmp_path / ".mutation_history.jsonl"
    baseline = tmp_path / ".mutation_baseline.toml"

    threshold = TARGETS["token_guard"] - TOLERANCE
    # 預灌 1 次低於門檻 + 5 次達標 → 第 7 次無論如何都不能鎖
    _append_history(history, "token_guard", [threshold - 0.10] + [threshold + 0.02] * 5)
    _write_mutmut_log(log, killed=72, survived=28)

    result = run("token_guard", log, history, baseline)

    assert result["status"] == "observing"
    locked = read_baseline(baseline)
    assert "token_guard" not in locked


def test_lock_upgrade_only_if_higher(tmp_path: Path) -> None:
    """case 4：鎖定後僅在新值高於舊 baseline 時升級（不退步）。"""
    history = tmp_path / ".mutation_history.jsonl"
    baseline = tmp_path / ".mutation_baseline.toml"

    # 初始 baseline 設為 0.75
    write_baseline(baseline, "token_guard", 0.75)
    assert read_baseline(baseline)["token_guard"] == pytest.approx(0.75)

    threshold = TARGETS["token_guard"] - TOLERANCE  # 0.70
    # 連續 7 次都剛好達 0.71 → 達標但低於舊 0.75 → 不升級
    _append_history(history, "token_guard", [0.71] * 6)
    log = tmp_path / "mutation_token_guard.log"
    _write_mutmut_log(log, killed=71, survived=29, timeout=0, suspicious=0)

    result = run("token_guard", log, history, baseline)

    assert result["status"] == "locked"
    # 不升級：舊 baseline 0.75 維持
    assert read_baseline(baseline)["token_guard"] == pytest.approx(0.75)


# ====================== 補強 case：解析 + 分類 ======================


def test_parse_mutmut_log_emoji_format(tmp_path: Path) -> None:
    log = tmp_path / "mutation_token_guard.log"
    _write_mutmut_log(log, killed=80, survived=15, timeout=2, suspicious=3, skipped=1)
    counts = parse_mutmut_log(log)
    assert counts["killed"] == 80
    assert counts["survived"] == 15
    assert counts["timeout"] == 2
    assert counts["suspicious"] == 3
    assert counts["skipped"] == 1


def test_calc_kill_rate_excludes_skipped() -> None:
    # skipped 不計入分母；ADR-SD09-009 v1.0：suspicious 計 0.5 killed 半 kill
    counts = {"killed": 75, "survived": 20, "timeout": 3, "suspicious": 2, "skipped": 50}
    rate = calc_kill_rate(counts)
    # (75 + 0.5*2) / (75 + 20 + 3 + 2) = 76 / 100 = 0.76
    assert rate == pytest.approx((75 + 0.5 * 2) / (75 + 20 + 3 + 2))


def test_should_lock_takes_min_as_baseline() -> None:
    # 7 次 [0.72, 0.71, 0.73, 0.70, 0.75, 0.71, 0.74] → min=0.70（取最保守）
    # Round 4 P0-AUDIT-R3-2：補 unique sha 滿足紀律 #12
    rates = [0.72, 0.71, 0.73, 0.70, 0.75, 0.71, 0.74]
    history = [
        {"kill_rate": v, "source_sha256": f"u{i:015d}"} for i, v in enumerate(rates)
    ]
    locked, baseline = should_lock(history, "token_guard")
    assert locked is True
    assert baseline == pytest.approx(0.70)


def test_mutation_analysis_classify_boundary() -> None:
    diff = "- if x >= 10:\n+ if x > 10:\n"
    assert classify_diff(diff) == "boundary"


def test_mutation_analysis_classify_constant() -> None:
    diff = "- enabled = True\n+ enabled = False\n"
    assert classify_diff(diff) == "constant"


def test_mutation_analysis_string_literal_ignored() -> None:
    diff = '- logger.warning("token usage high")\n+ logger.warning("XXtoken usage highXX")\n'
    assert classify_diff(diff) == "string_literal"


def test_mutation_analysis_empty_log(tmp_path: Path) -> None:
    log = tmp_path / "empty.log"
    log.write_text("", encoding="utf-8")
    ids = extract_survived_ids(log)
    assert ids == []
    out = tmp_path / "backlog.md"
    summary = analyze(log, "token_guard", out, skip_show=True)
    assert all(v == 0 for v in summary.values())
    assert out.exists()
