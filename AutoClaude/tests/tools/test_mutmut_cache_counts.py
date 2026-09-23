"""tests/tools/test_mutmut_cache_counts.py — DEF-200-365 CI mutation kill_rate 恆 0.00% 修復鎖。

WHY（Rule 9 測意圖非僅行為）：`mutmut results`（mutmut 2.4.3 `cache.py::print_result_cache`）
結構上永不印 Killed，四處 CI job 只跑它 ⇒ `mutation_baseline_lock.py` 讀不到 Killed
恆 0% ⇒ 觀察期／連續 7 次達標鎖定機制永遠不會被真實 kill_rate 觸發（雲端 run
35678026352 逐字 `Survived 🙁 (59)` / `kill_rate=0.00%` 為證）。`tools/mutmut_cache_counts.py`
從 mutmut `.mutmut-cache`（sqlite）直查 `Mutant.status` 補上 marker 段。

本測試鎖五件事：
  1. 正常路徑：sqlite status 計數 → 五類 label 逐字對應。
  2. CLI 逐字輸出格式（`mutation_baseline_lock` 必認的 marker 段單一真相）。
  3. 全 killed 邊界值（`Survived (0)`）不誤判為 empty。
  4. fail-loud：cache 不存在／不是檔案／不是合法 mutmut cache 皆 rc=2、stdout 空、stderr 非空。
  5. 整合鏈路：helper 輸出接得上 `mutation_baseline_lock.parse_mutmut_log` /
     `calc_kill_rate`；且 status label_map 與 `run_mutmut_in_docker.sh` 內嵌 python 同步。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.mutation_baseline_lock import calc_kill_rate, parse_mutmut_log
from tools.mutmut_cache_counts import (
    _STATUS_LABEL_MAP,
    format_marker_section,
    main,
    read_status_counts,
)

_AUTOCLAUDE_ROOT = Path(__file__).resolve().parents[2]


def _make_cache(path: Path, status_rows: dict[str, int]) -> None:
    """建一份最小 mutmut `.mutmut-cache` 相容 sqlite：`Mutant(id, status)`。"""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE Mutant (id INTEGER PRIMARY KEY, status TEXT)")
        row_id = 0
        for status, count in status_rows.items():
            for _ in range(count):
                row_id += 1
                conn.execute(
                    "INSERT INTO Mutant (id, status) VALUES (?, ?)", (row_id, status)
                )
        conn.commit()
    finally:
        conn.close()


# ----- 分支 1: 正常路徑（sqlite status → label 對應） -----


def test_read_status_counts_maps_raw_status_to_labels(tmp_path: Path) -> None:
    cache = tmp_path / ".mutmut-cache"
    _make_cache(
        cache,
        {"ok_killed": 13, "bad_survived": 59, "bad_timeout": 1, "ok_suspicious": 2},
    )
    counts = read_status_counts(cache)
    assert counts == {
        "killed": 13,
        "survived": 59,
        "timeout": 1,
        "suspicious": 2,
        "skipped": 0,
    }


def test_main_prints_exact_marker_section(tmp_path: Path, capsys) -> None:
    cache = tmp_path / ".mutmut-cache"
    _make_cache(
        cache,
        {"ok_killed": 13, "bad_survived": 59, "bad_timeout": 1, "ok_suspicious": 2},
    )
    rc = main(["--cache-path", str(cache)])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out == (
        "\n"
        "--- mutmut full counts (from cache; mutmut_cache_counts.py) ---\n"
        "Killed (13)\n"
        "Survived (59)\n"
        "Timeout (1)\n"
        "Suspicious (2)\n"
        "Skipped (0)\n"
        "--- mutmut full counts (end) ---\n"
    )
    assert captured.err == ""


# ----- 分支 2: 全 killed 邊界值 —— Survived (0) 不誤判為 empty -----


def test_all_killed_prints_survived_zero(tmp_path: Path, capsys) -> None:
    cache = tmp_path / ".mutmut-cache"
    _make_cache(cache, {"ok_killed": 42})
    rc = main(["--cache-path", str(cache)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Killed (42)" in captured.out
    assert "Survived (0)" in captured.out


def test_all_killed_output_not_misread_as_empty_by_parse_mutmut_log(
    tmp_path: Path,
) -> None:
    """全 killed（Survived (0)／Timeout (0)／Suspicious (0)／Skipped (0)）時，
    marker 段 sum（=killed 數）> 0，`parse_mutmut_log` 走 marker 分支而非
    誤判為空 log（不應拋 ValueError）。"""
    cache = tmp_path / ".mutmut-cache"
    _make_cache(cache, {"ok_killed": 42})
    counts = read_status_counts(cache)
    log_path = tmp_path / "mutation_all_killed.log"
    log_path.write_text(format_marker_section(counts), encoding="utf-8")

    parsed = parse_mutmut_log(log_path)
    assert parsed == {
        "killed": 42,
        "survived": 0,
        "timeout": 0,
        "suspicious": 0,
        "skipped": 0,
    }
    assert calc_kill_rate(parsed) == pytest.approx(1.0)


# ----- 分支 3: fail-loud —— 缺檔／非檔案／非合法 cache 皆 rc=2 -----


def test_missing_cache_returns_rc_2_and_empty_stdout(tmp_path: Path, capsys) -> None:
    rc = main(["--cache-path", str(tmp_path / "nonexistent-cache")])
    assert rc == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err != ""
    assert "ERROR" in captured.err


def test_cache_path_is_a_directory_returns_rc_2(tmp_path: Path, capsys) -> None:
    """`--cache-path` 誤指到目錄（存在但不是檔案）同樣 fail-loud。"""
    directory = tmp_path / "not-a-file"
    directory.mkdir()
    rc = main(["--cache-path", str(directory)])
    assert rc == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ERROR" in captured.err


def test_read_status_counts_raises_filenotfounderror_directly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_status_counts(tmp_path / "nope")


def test_sqlite_query_failure_returns_rc_2(tmp_path: Path, capsys) -> None:
    """檔存在但不是合法 mutmut cache（缺 Mutant 表）→ sqlite 查詢失敗 → rc=2。"""
    bogus = tmp_path / ".mutmut-cache"
    conn = sqlite3.connect(str(bogus))
    try:
        conn.execute("CREATE TABLE NotMutant (id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()
    rc = main(["--cache-path", str(bogus)])
    assert rc == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ERROR" in captured.err


# ----- format_marker_section 純函式邊界（缺 key 時預設 0） -----


def test_format_marker_section_defaults_missing_keys_to_zero() -> None:
    text = format_marker_section({})
    assert "Killed (0)" in text
    assert "Survived (0)" in text
    assert "Timeout (0)" in text
    assert "Suspicious (0)" in text
    assert "Skipped (0)" in text
    assert text.startswith(
        "\n--- mutmut full counts (from cache; mutmut_cache_counts.py) ---\n"
    )
    assert text.endswith("--- mutmut full counts (end) ---\n")


# ----- 分支 4: 整合鎖 —— 與 mutation_baseline_lock.parse_mutmut_log / calc_kill_rate 串接 -----


def test_helper_output_feeds_mutation_baseline_lock_parse_and_kill_rate(
    tmp_path: Path,
) -> None:
    """把「假 raw results（只含 `Survived 🙁 (59)` 與 dash range `1-59`，缺 Killed）」
    ＋本 helper 輸出寫成一份 log，模擬 DEF-200-365 修復後的真實 CI log 型態；
    `mutation_baseline_lock.parse_mutmut_log` 須讀到 killed=13（來自 marker 段，
    非 raw results），`calc_kill_rate` 依 ADR-SD09-009 公式算出
    (13 + 0.5*2) / (13+59+1+2)。
    """
    cache = tmp_path / ".mutmut-cache"
    _make_cache(
        cache,
        {"ok_killed": 13, "bad_survived": 59, "bad_timeout": 1, "ok_suspicious": 2},
    )
    counts = read_status_counts(cache)
    marker_section = format_marker_section(counts)

    raw_results_section = (
        "\n--- mutmut results raw (begin) ---\n"
        "Survived 🙁 (59)\n"
        "\n"
        "1-59\n"
        "\n"
        "--- mutmut results raw (end) ---\n"
    )
    log_path = tmp_path / "mutation_token_guard.log"
    log_path.write_text(raw_results_section + marker_section, encoding="utf-8")

    parsed = parse_mutmut_log(log_path)
    assert parsed == {
        "killed": 13,
        "survived": 59,
        "timeout": 1,
        "suspicious": 2,
        "skipped": 0,
    }
    kill_rate = calc_kill_rate(parsed)
    expected = (13 + 0.5 * 2) / (13 + 59 + 1 + 2)
    assert kill_rate == pytest.approx(expected)


# ----- 分支 5: label_map 與 run_mutmut_in_docker.sh 一致鎖 -----


def test_status_label_map_matches_run_mutmut_in_docker_sh() -> None:
    """`run_mutmut_in_docker.sh` L151-157 的 label_map 五個 status 字面，必須全部出現
    在本 helper 的 `_STATUS_LABEL_MAP`（兩份實作刻意並存，見本模組檔頭〈誠實劃界〉：
    `.sh` label_map 若漂移，本測試先紅）。
    """
    sh_path = _AUTOCLAUDE_ROOT / "tools" / "run_mutmut_in_docker.sh"
    sh_text = sh_path.read_text(encoding="utf-8")

    helper_status_keys = {status_key for status_key, _ in _STATUS_LABEL_MAP}
    expected_status_keys = {
        "ok_killed",
        "bad_survived",
        "bad_timeout",
        "ok_suspicious",
        "skipped",
    }
    assert helper_status_keys == expected_status_keys
    for status_key in expected_status_keys:
        assert status_key in sh_text, (
            f"{status_key!r} 不在 run_mutmut_in_docker.sh 內——label_map 可能已漂移，"
            "需回頭核對兩份實作是否仍指同一組 mutmut status 字面"
        )
