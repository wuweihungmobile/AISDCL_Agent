"""tests/tools/test_drift_log_snapshot.py — SD_09 W2 nightly audit P1-5 補建。

對應 tools/drift_log_snapshot.py（≥ 3 case，紀律 #4 驗證鏡子要被驗證）：
  1. test_basic_append              — 第一次寫入必須產生 1 筆 record
  2. test_same_day_deduplication    — 同 UTC date 兩筆 → 第二筆覆寫第一筆
  3. test_table_missing_marks_fail  — table_missing=True → passed=False（不視為觀察期一天）
  4. test_non_info_count_blocks_pass — severity_count > 0 → passed=False（紀律 #1）
  5. test_cli_invocation             — CLI 入口 main() 可執行
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.drift_log_snapshot import (
    append_snapshot,
    build_record,
    main,
)


def test_basic_append(tmp_path: Path) -> None:
    history = tmp_path / ".drift.jsonl"
    record = build_record(severity_non_info_count=0, table_exists=True)
    action = append_snapshot(history, record)

    assert action == "appended"
    assert history.exists()
    lines = [
        ln for ln in history.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["severity_non_info_count"] == 0
    assert parsed["passed"] is True


def test_same_day_deduplication(tmp_path: Path) -> None:
    history = tmp_path / ".drift.jsonl"

    r1 = build_record(severity_non_info_count=0, ts="2026-05-21T01:00:00+00:00")
    r2 = build_record(severity_non_info_count=0, ts="2026-05-21T23:00:00+00:00")
    r3 = build_record(severity_non_info_count=0, ts="2026-05-22T05:00:00+00:00")

    assert append_snapshot(history, r1) == "appended"
    assert append_snapshot(history, r2) == "replaced"
    assert append_snapshot(history, r3) == "appended"

    lines = [
        json.loads(ln)
        for ln in history.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(lines) == 2


def test_table_missing_marks_fail() -> None:
    """drift_log 表不存在 → passed=False（避免 alembic 落後被計入觀察期）。"""
    record = build_record(severity_non_info_count=0, table_exists=False)
    assert record["drift_log_table_exists"] is False
    assert record["passed"] is False, (
        "table_exists=False 必須 passed=False；否則 alembic 落後會被誤計入觀察期天數"
    )


def test_non_info_count_blocks_pass() -> None:
    """嚴重事件存在 → passed=False。"""
    record = build_record(severity_non_info_count=3, table_exists=True)
    assert record["passed"] is False
    assert record["severity_non_info_count"] == 3


def test_cli_invocation(tmp_path: Path, capsys) -> None:
    history = tmp_path / ".drift_cli.jsonl"
    rc = main(["--history", str(history), "--severity-count", "0"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "drift_log-snapshot" in out
    assert history.exists()


def test_same_day_prefers_table_exists(tmp_path: Path) -> None:
    """SD_09 W3 Round 2 audit P0-3 修復（紀律 #9）：同日真實取值不被 SKIP 覆寫。

    場景：當日先跑真實取值（table_exists=True, passed=True）→ Docker 重啟後同日重跑
    （table_missing=True, passed=False）。原邏輯會被覆寫 → 觀察期 #3 該日斷掉假象。
    """
    history = tmp_path / ".drift.jsonl"

    # 第一筆：真實取值
    r_real = build_record(
        severity_non_info_count=0, table_exists=True, ts="2026-05-24T01:00:00+00:00"
    )
    assert append_snapshot(history, r_real) == "appended"

    # 第二筆：同日 SKIP（table_missing=True）→ 必須 kept_existing 不覆寫
    r_skip = build_record(
        severity_non_info_count=0, table_exists=False, ts="2026-05-24T23:00:00+00:00"
    )
    assert append_snapshot(history, r_skip) == "kept_existing"

    # 驗證真實取值仍留存
    raw = history.read_text(encoding="utf-8")
    lines = [json.loads(ln) for ln in raw.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert lines[0]["passed"] is True
    assert lines[0]["drift_log_table_exists"] is True


def test_same_day_skip_can_be_upgraded_to_real(tmp_path: Path) -> None:
    """同日先 SKIP，後續真實取值應升級覆寫。"""
    history = tmp_path / ".drift.jsonl"

    r_skip = build_record(
        severity_non_info_count=0, table_exists=False, ts="2026-05-24T01:00:00+00:00"
    )
    assert append_snapshot(history, r_skip) == "appended"

    r_real = build_record(
        severity_non_info_count=0, table_exists=True, ts="2026-05-24T20:00:00+00:00"
    )
    # 不能 kept_existing：舊紀錄是 SKIP，新紀錄是真實取值 → 必須 replaced
    assert append_snapshot(history, r_real) == "replaced"

    raw = history.read_text(encoding="utf-8")
    lines = [json.loads(ln) for ln in raw.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert lines[0]["passed"] is True
