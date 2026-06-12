"""tests/tools/test_drift_log_ga_check.py — SD_09 W3 Round 2 audit P0-3 補建。

對應 tools/drift_log_ga_check.py（≥ 6 case，紀律 #4 驗證鏡子要被驗證）：
  1. test_no_history          — 無檔 → exit 1 + status=no_history
  2. test_empty_history       — 空檔 → exit 1
  3. test_streak_zero         — 全 passed=False → green_streak=0
  4. test_streak_lt_window    — green_streak < window → exit 1
  5. test_streak_eq_window    — green_streak == window → exit 0
  6. test_streak_gt_window    — green_streak > window → exit 0
  7. test_table_missing_breaks_streak — 中間 table_missing → streak 從尾部數
  8. test_severity_count_blocks_pass  — severity_count>0 → green=False 中斷
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.drift_log_ga_check import (
    _compute_green_streak,
    _is_green,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )


def _green_record(ts: str = "2026-05-24T01:00:00+00:00") -> dict:
    return {
        "ts": ts,
        "drift_log_table_exists": True,
        "severity_non_info_count": 0,
        "passed": True,
    }


def _missing_table_record(ts: str = "2026-05-24T01:00:00+00:00") -> dict:
    return {
        "ts": ts,
        "drift_log_table_exists": False,
        "severity_non_info_count": 0,
        "passed": False,
    }


def _severity_record(ts: str = "2026-05-24T01:00:00+00:00", n: int = 3) -> dict:
    return {
        "ts": ts,
        "drift_log_table_exists": True,
        "severity_non_info_count": n,
        "passed": False,
    }


# ----- _is_green ----- #


def test_is_green_passes_when_passed_true() -> None:
    ok, reason = _is_green(_green_record())
    assert ok is True
    assert reason == ""


def test_is_green_fails_when_table_missing() -> None:
    ok, reason = _is_green(_missing_table_record())
    assert ok is False
    assert "table_exists=False" in reason


def test_is_green_fails_when_severity_count_positive() -> None:
    ok, reason = _is_green(_severity_record(n=5))
    assert ok is False
    assert "5" in reason


# ----- _compute_green_streak ----- #


def test_streak_zero_when_all_failing(tmp_path: Path) -> None:
    records = [_missing_table_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(1, 6)]
    streak, _ = _compute_green_streak(records)
    assert streak == 0


def test_streak_counts_from_tail(tmp_path: Path) -> None:
    """前 3 筆 failing + 後 4 筆 passing → streak=4。"""
    records = [_missing_table_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(1, 4)]
    records.extend(_green_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(4, 8))
    streak, _ = _compute_green_streak(records)
    assert streak == 4


def test_severity_count_breaks_streak() -> None:
    records = [_green_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(1, 4)]
    records.append(_severity_record("2026-05-04T01:00:00+00:00", n=1))
    records.append(_green_record("2026-05-05T01:00:00+00:00"))
    streak, _ = _compute_green_streak(records)
    assert streak == 1  # 只算最後一筆 green


# ----- main() CLI ----- #


def test_no_history_returns_1(tmp_path: Path, capsys) -> None:
    rc = main(["--history", str(tmp_path / "nonexistent.jsonl"), "--window", "30", "--json"])
    assert rc == 1
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["status"] == "no_history"
    assert payload["green_streak"] == 0


def test_empty_history_returns_1(tmp_path: Path, capsys) -> None:
    hist = tmp_path / "empty.jsonl"
    hist.write_text("", encoding="utf-8")
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "no_history"


def test_streak_lt_window_returns_1(tmp_path: Path, capsys) -> None:
    hist = tmp_path / "h.jsonl"
    records = [_green_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(1, 6)]
    _write_jsonl(hist, records)
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "observing"
    assert payload["green_streak"] == 5


def test_streak_eq_window_returns_0(tmp_path: Path, capsys) -> None:
    hist = tmp_path / "h.jsonl"
    records = [_green_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(1, 31)]
    _write_jsonl(hist, records)
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert payload["green_streak"] == 30


def test_streak_gt_window_returns_0(tmp_path: Path, capsys) -> None:
    hist = tmp_path / "h.jsonl"
    records = [_green_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(1, 33)]
    _write_jsonl(hist, records)
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["green_streak"] == 32


def test_failure_in_middle_only_counts_tail(tmp_path: Path, capsys) -> None:
    """中間 failure 不影響：streak 一律從 tail 數連續綠。"""
    hist = tmp_path / "h.jsonl"
    records = [_green_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(1, 10)]
    records.append(_severity_record("2026-05-10T01:00:00+00:00", n=2))  # break
    records.extend(_green_record(f"2026-05-{d:02d}T01:00:00+00:00") for d in range(11, 16))
    _write_jsonl(hist, records)
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["green_streak"] == 5
    assert "severity_non_info_count" in payload["last_failure_reason"]
