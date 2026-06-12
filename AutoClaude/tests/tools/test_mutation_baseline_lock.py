"""tests/tools/test_mutation_baseline_lock.py — SD_09 W2 audit P0-AUDIT-07 修復。

紀律 #4「驗證鏡子自身要被驗證」— mutation_baseline_lock.py 是「mutmut log → kill_rate」
的真實性鏡子，必須有單元測試證明「假 PASS 場景能被拒絕」。

涵蓋：
  - parse_mutmut_log marker-based 優先 + fallback 「取最後一筆」
  - 空 log / 缺檔 → ValueError / FileNotFoundError
  - calc_kill_rate 邊界（0 / 全 killed / 全 survived / 含 skipped 不計入 denom）
  - append_history 同 module + 同 UTC date 去重（M-05 修復）
  - should_lock 連續 7 次達標才鎖定
  - SD_09 W2 P0-AUDIT-04：marker 區段被「最後一筆」混淆時，marker 優先取勝
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from tools.mutation_baseline_lock import (
    CONSECUTIVE_RUNS,
    EXTRA_TOLERANCE,
    TARGETS,
    TOLERANCE,
    append_history,
    calc_kill_rate,
    compute_consistency_warning,
    parse_mutmut_log,
    read_baseline,
    should_lock,
    write_baseline,
)


# ----- parse_mutmut_log -----


def test_parse_marker_section_is_single_source_of_truth(tmp_path: Path) -> None:
    """SD_09 W2 P0-AUDIT-04：marker 區段為單一真相，優先於 raw section。

    raw 區段刻意放錯誤計數（Survived 999），marker 區段是真實計數（Survived 38）。
    fix 前「取最後一筆」會拿 marker 內 Skipped 後最後一個 = 真值，
    但若 mutmut 後續調整輸出順序（counts 在前、raw 在後），舊邏輯會被 raw 蓋掉。
    """
    log = tmp_path / "mutmut.log"
    log.write_text(
        "Killed 🎉 (999)\n"  # raw 誤導
        "Survived 🙁 (999)\n"  # raw 誤導
        "--- mutmut full counts (from cache; SD_09 P0-G) ---\n"
        "Killed (111)\n"
        "Survived (38)\n"
        "Timeout (0)\n"
        "Suspicious (0)\n"
        "Skipped (0)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    counts = parse_mutmut_log(log)
    assert counts["killed"] == 111
    assert counts["survived"] == 38
    assert counts["timeout"] == 0


def test_parse_fallback_to_last_when_no_marker(tmp_path: Path) -> None:
    """marker 缺失時 fallback「取最後一筆」（向下相容舊 log）。"""
    log = tmp_path / "old.log"
    log.write_text(
        "Killed mutants. The goal (legend)\n"  # legend 無數字，不該匹配
        "Killed (5)\n"
        "Killed (10)\n"  # 最後一筆 — 應取 10
        "Survived (3)\n",
        encoding="utf-8",
    )
    counts = parse_mutmut_log(log)
    assert counts["killed"] == 10
    assert counts["survived"] == 3


def test_parse_empty_log_raises_value_error(tmp_path: Path) -> None:
    """空 log 必須拋 ValueError — 不能污染 history 為 0%（SD_09 Pre-W0 audit P0-01）。"""
    log = tmp_path / "empty.log"
    log.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty mutmut log"):
        parse_mutmut_log(log)


def test_parse_help_fallback_raises_value_error(tmp_path: Path) -> None:
    """help fallback log（無數字計數）必須拒絕。"""
    log = tmp_path / "help.log"
    log.write_text(
        "usage: mutmut [-h]\n"
        "To apply a mutant on disk: mutmut apply <id>\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        parse_mutmut_log(log)


def test_parse_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_mutmut_log(tmp_path / "nonexistent.log")


# ----- calc_kill_rate -----


def test_calc_kill_rate_basic() -> None:
    assert calc_kill_rate({"killed": 80, "survived": 20, "timeout": 0, "suspicious": 0}) == 0.8


def test_calc_kill_rate_skipped_not_in_denom() -> None:
    """skipped 不計入 denom（mutmut 標準行為）。"""
    rate = calc_kill_rate(
        {"killed": 10, "survived": 0, "timeout": 0, "suspicious": 0, "skipped": 90}
    )
    assert rate == 1.0


def test_calc_kill_rate_zero_denom() -> None:
    """0 denom 回 0.0（避免 div by zero）。"""
    assert calc_kill_rate({"killed": 0, "survived": 0, "timeout": 0, "suspicious": 0}) == 0.0


def test_calc_kill_rate_timeout_count_as_unkilled() -> None:
    """ADR-SD09-009 v1.0：timeout 仍算未殺死；suspicious 改算 0.5 半 kill。

    killed=50, survived=20, timeout=20, suspicious=10, denom=100
    numerator = 50 + 0.5*10 = 55 → rate = 0.55
    """
    rate = calc_kill_rate(
        {"killed": 50, "survived": 20, "timeout": 20, "suspicious": 10}
    )
    assert rate == 0.55


# ----- ADR-SD09-009 v1.0：suspicious 0.5 半 kill + ±2pp tolerance（T1-M3）-----


def test_calc_kill_rate_suspicious_half_kill_basic() -> None:
    """ADR-SD09-009 §6 選項 A：suspicious 計 0.5 killed 至分子。

    Round 14 第 9 跑真實 counts：killed=109, survived=38, suspicious=2, denom=149
    舊公式 = 109/149 = 73.15%；新公式 = (109 + 0.5*2)/149 = 110/149 ≈ 73.83%（+0.67pp）
    """
    rate = calc_kill_rate(
        {"killed": 109, "survived": 38, "timeout": 0, "suspicious": 2, "skipped": 0}
    )
    assert abs(rate - 110 / 149) < 1e-9


def test_calc_kill_rate_no_suspicious_backward_compatible() -> None:
    """ADR-SD09-009 §5.2 紅線：suspicious=0 時退化為原公式（向下相容歷史 jsonl 4 筆）。

    Round 13 第 8 跑 counts：killed=111, survived=38, suspicious=0, denom=149
    舊公式 = 111/149 = 74.50%；新公式 = (111 + 0)/149 = 74.50%（等價）
    """
    rate = calc_kill_rate(
        {"killed": 111, "survived": 38, "timeout": 0, "suspicious": 0, "skipped": 0}
    )
    assert abs(rate - 111 / 149) < 1e-9


def test_calc_kill_rate_r9_to_r11_three_option_equivalence_at_zero_suspicious() -> None:
    """ADR-SD09-009 §3.1 立論：當 suspicious=0 時，選項 A/B/C 三選項數學等價。

    Round 11 第 6 跑：killed=111, survived=38, suspicious=0 → 74.50% 三選項相同。
    這證明新公式對「無 bounce flake 狀態」零影響，僅對 suspicious>0 情況差異。
    """
    counts = {"killed": 111, "survived": 38, "timeout": 0, "suspicious": 0}
    # 選項 A（新）: (killed + 0.5*susp) / denom
    rate_a = calc_kill_rate(counts)
    # 選項 C（忽略 susp）: killed / (killed + survived + timeout)
    denom_c = counts["killed"] + counts["survived"] + counts["timeout"]
    rate_c = counts["killed"] / denom_c
    # 等價驗證
    assert abs(rate_a - rate_c) < 1e-9


def test_should_lock_with_extra_tolerance_bounce_buffer(tmp_path: Path) -> None:
    """ADR-SD09-009 §5.5 ±2pp tolerance：68% 在 bounce 區應仍鎖定（不被 flake 重計）。

    Round 9~11 觀察：suspicious bounce 7→4→0 致 kill_rate 在 [69.80%, 74.50%] 區間飄動。
    新門檻 = 75% - 5% - 2% = 68%，bounce 區任一筆仍 ≥ 68% → lock 不重計。
    """
    target = TARGETS["token_guard"]
    effective_threshold = target - TOLERANCE - EXTRA_TOLERANCE
    assert abs(effective_threshold - 0.68) < 1e-9
    # 模擬 7 筆全在 [0.68, 0.75] 區間（bounce 最低 = 0.69，仍 ≥ 0.68）
    history = [
        {"kill_rate": 0.69 + 0.001 * i, "module": "token_guard", "source_sha256": f"u{i:015d}"}
        for i in range(CONSECUTIVE_RUNS)
    ]
    locked, value = should_lock(history, "token_guard")
    assert locked is True
    assert abs(value - 0.69) < 1e-9


def test_should_lock_below_extra_tolerance_still_rejects(tmp_path: Path) -> None:
    """ADR-SD09-009 §5.5 紅線：低於 effective threshold 仍拒絕鎖定（67% < 68%）。

    證明 ±2pp tolerance 不是無條件放寬 — 跌破 effective threshold 仍守住。
    """
    history = [
        {"kill_rate": 0.71, "module": "token_guard", "source_sha256": f"u{i:015d}"}
        for i in range(6)
    ]
    history.append({"kill_rate": 0.67, "module": "token_guard", "source_sha256": "u006"})  # 第 7 筆 67% < 68%
    locked, value = should_lock(history, "token_guard")
    assert locked is False
    assert value is None


def test_should_lock_old_70pct_threshold_no_longer_strict() -> None:
    """ADR-SD09-009 §9.1 後果：原 70% 嚴格門檻已放寬至 68%。

    Round 9 第 4 跑 69.80%（舊公式 70% 不到 → reject；新公式 + ±2pp = 68% → lock 達標）。
    驗證新 policy 對 Round 9 真實案例的修復力。
    """
    # 模擬 Round 9 連續 7 次都 69.80%（舊邏輯 reject）
    history = [
        {"kill_rate": 0.6980, "module": "token_guard", "source_sha256": f"r9u{i:013d}"}
        for i in range(CONSECUTIVE_RUNS)
    ]
    locked, value = should_lock(history, "token_guard")
    # 新公式 + ±2pp tolerance：69.80% ≥ 68% → lock
    assert locked is True
    assert abs(value - 0.6980) < 1e-9


# ----- append_history 同日去重 -----


def test_append_history_same_date_overwrites(tmp_path: Path) -> None:
    """M-05 修復：同 module + 同 UTC date 重複寫入只保留最後一筆。"""
    hist = tmp_path / "history.jsonl"
    rec1 = {
        "timestamp": "2026-05-21T08:00:00+00:00",
        "module": "token_guard",
        "kill_rate": 0.5,
    }
    rec2 = {
        "timestamp": "2026-05-21T20:00:00+00:00",
        "module": "token_guard",
        "kill_rate": 0.7,
    }
    append_history(hist, rec1)
    append_history(hist, rec2)
    records = [json.loads(ln) for ln in hist.read_text().splitlines() if ln.strip()]
    assert len(records) == 1
    assert records[0]["kill_rate"] == 0.7


def test_append_history_different_dates_preserve_all(tmp_path: Path) -> None:
    hist = tmp_path / "history.jsonl"
    for day in range(1, 4):
        rec = {
            "timestamp": f"2026-05-{day:02d}T08:00:00+00:00",
            "module": "token_guard",
            "kill_rate": 0.6 + 0.05 * day,
        }
        append_history(hist, rec)
    records = [json.loads(ln) for ln in hist.read_text().splitlines() if ln.strip()]
    assert len(records) == 3


def test_append_history_different_modules_dont_overwrite(tmp_path: Path) -> None:
    """同日不同 module 不應彼此覆寫。"""
    hist = tmp_path / "history.jsonl"
    rec_tg = {"timestamp": "2026-05-21T08:00:00+00:00", "module": "token_guard", "kill_rate": 0.7}
    rec_gs = {"timestamp": "2026-05-21T08:00:00+00:00", "module": "goal_synthesis", "kill_rate": 0.6}
    append_history(hist, rec_tg)
    append_history(hist, rec_gs)
    records = [json.loads(ln) for ln in hist.read_text().splitlines() if ln.strip()]
    assert len(records) == 2


# ----- should_lock -----


def test_should_lock_requires_7_consecutive(tmp_path: Path) -> None:
    """只有 6 筆 → 不鎖。"""
    history = [
        {"kill_rate": 0.75, "module": "token_guard"} for _ in range(6)
    ]
    locked, value = should_lock(history, "token_guard")
    assert locked is False


def test_should_lock_at_threshold(tmp_path: Path) -> None:
    """連續 7 次 ≥ (0.75 - 0.05) = 0.70 → 鎖定，取 min。

    Round 4 P0-AUDIT-R3-2：補 unique sha 以滿足新增的紀律 #12 強制 unique 檢查。
    """
    history = [
        {"kill_rate": 0.71, "module": "token_guard", "source_sha256": f"u{i:015d}"}
        for i in range(CONSECUTIVE_RUNS)
    ]
    locked, value = should_lock(history, "token_guard")
    assert locked is True
    assert value == 0.71


def test_should_lock_one_below_threshold_fails(tmp_path: Path) -> None:
    """7 筆中 1 筆未達 → 不鎖。"""
    history = [{"kill_rate": 0.75, "module": "token_guard"} for _ in range(6)]
    history.append({"kill_rate": 0.65, "module": "token_guard"})  # 第 7 筆未達
    locked, _ = should_lock(history, "token_guard")
    assert locked is False


def test_should_lock_takes_min_as_baseline() -> None:
    """達標時取 min 為最保守 baseline。

    Round 4 P0-AUDIT-R3-2：補 unique sha 以滿足紀律 #12。
    """
    rates = [0.85, 0.80, 0.72, 0.78, 0.81, 0.79, 0.83]
    history = [
        {"kill_rate": rate, "module": "token_guard", "source_sha256": f"u{i:015d}"}
        for i, rate in enumerate(rates)
    ]
    locked, value = should_lock(history, "token_guard")
    assert locked is True
    assert value == 0.72


def test_should_lock_unknown_module_returns_false() -> None:
    locked, value = should_lock([{"kill_rate": 0.9}] * 10, "nonexistent_module")
    assert locked is False
    assert value is None


def test_should_lock_uses_only_tail_n() -> None:
    """只看最後 7 筆，前面失敗的不影響。

    Round 4 P0-AUDIT-R3-2：tail 7 筆補 unique sha 以滿足紀律 #12。
    """
    history = [{"kill_rate": 0.0, "module": "token_guard"} for _ in range(5)]
    history.extend([
        {"kill_rate": 0.85, "module": "token_guard", "source_sha256": f"u{i:015d}"}
        for i in range(CONSECUTIVE_RUNS)
    ])
    locked, _ = should_lock(history, "token_guard")
    assert locked is True


# ----- baseline read/write roundtrip -----


def test_baseline_write_read_roundtrip(tmp_path: Path) -> None:
    bl = tmp_path / "baseline.toml"
    write_baseline(bl, "token_guard", 0.7234)
    written = read_baseline(bl)
    assert "token_guard" in written
    assert abs(written["token_guard"] - 0.7234) < 1e-4


def test_baseline_upsert_preserves_other_modules(tmp_path: Path) -> None:
    bl = tmp_path / "baseline.toml"
    write_baseline(bl, "token_guard", 0.72)
    write_baseline(bl, "goal_synthesis", 0.65)
    written = read_baseline(bl)
    assert "token_guard" in written
    assert "goal_synthesis" in written


# ----- SD_09 W3 Round 2 audit P0-5: source_sha256 + 7 unique 強制 -----


def test_same_source_sha_7_times_should_not_lock() -> None:
    """同 source 跑 7 次（kill_rate 達標）— P0-5 修復後應拒絕鎖定。

    紀律：避免「同 commit 重跑 7 次騙過 lock」。
    """
    history = [
        {"kill_rate": 0.80, "module": "token_guard", "source_sha256": "deadbeef00000000"}
        for _ in range(CONSECUTIVE_RUNS)
    ]
    locked, value = should_lock(history, "token_guard")
    assert locked is False, "同 source 7 次不應鎖定（紀律：避免假鎖）"


def test_seven_unique_source_sha_should_lock() -> None:
    """7 個不同 source_sha256 + kill_rate 達標 → 鎖定。"""
    history = [
        {
            "kill_rate": 0.80,
            "module": "token_guard",
            "source_sha256": f"sha{i:013d}",  # 16 chars unique
        }
        for i in range(CONSECUTIVE_RUNS)
    ]
    locked, value = should_lock(history, "token_guard")
    assert locked is True
    assert value == 0.80


def test_all_records_missing_sha_should_not_lock() -> None:
    """SD_09 W3 Round 4 audit P0-AUDIT-R3-2 修復：

    全部缺 sha 紀錄 → 應拒絕鎖定（紀律 #12 強化）。

    原 Round 2 設計「tail 含任一缺 sha → 跳過 unique 檢查」過寬：
    若 7 筆全缺欄位，無法驗證是否「同 commit 重跑」→ 不應鎖定。

    取證情境：初次部署 + 同 commit 連跑 7 次（測試環境常見）→ 不可假鎖定。
    """
    history = [
        {"kill_rate": 0.80, "module": "token_guard"}  # 缺欄位
        for _ in range(CONSECUTIVE_RUNS)
    ]
    locked, _ = should_lock(history, "token_guard")
    assert locked is False, "全部缺 sha 紀錄不應鎖定（Round 4 強化：避免初次部署假鎖定）"


def test_partial_missing_sha_with_same_remaining_should_not_lock() -> None:
    """SD_09 W3 Round 4 P0-AUDIT-R3-2 修復：

    部分缺 sha 紀錄 + non-None 部分含重複 sha → 拒絕鎖定。

    取證情境：前 N 筆缺欄位（舊紀錄相容）+ 後 M 筆同 commit 重複跑 →
    若放行則「同 commit 跑 5 次 + 2 筆舊紀錄 = 假鎖定」可實作。
    """
    history = [
        {"kill_rate": 0.80, "module": "token_guard"},  # 缺欄位 ×2
        {"kill_rate": 0.80, "module": "token_guard"},
        # 後 5 筆同 sha → non-None unique=1 < non-None count=5
        *[
            {"kill_rate": 0.80, "module": "token_guard", "source_sha256": "samesha000000000"}
            for _ in range(5)
        ],
    ]
    assert len(history) == CONSECUTIVE_RUNS
    locked, _ = should_lock(history, "token_guard")
    assert locked is False, "部分缺 sha + non-None 部分含重複 → 拒絕（Round 4 強化）"


def test_partial_missing_sha_with_enough_unique_should_lock() -> None:
    """SD_09 W3 Round 21 audit Architect P1 #2 收緊（原 Round 4 P0-AUDIT-R3-2）：

    部分缺 sha + non-None 部分全 unique 且 ≥ N - MAX_BACKWARD_COMPAT_MISSING = 5 → 寬鬆鎖定。

    取證情境：sha 欄位導入過渡期（前 2 筆舊紀錄缺欄位 5/20-5/21 + 後 5 筆每筆不同 commit）→ 允許鎖定。
    """
    history = [
        {"kill_rate": 0.80, "module": "token_guard"},  # 缺欄位 ×2（前置 legacy）
        {"kill_rate": 0.80, "module": "token_guard"},
        # 後 5 筆全 unique sha → non-None unique=5 = non-None count=5, ≥ 5 收緊門檻
        *[
            {"kill_rate": 0.80, "module": "token_guard", "source_sha256": f"unique{i:010d}"}
            for i in range(5)
        ],
    ]
    assert len(history) == CONSECUTIVE_RUNS
    locked, value = should_lock(history, "token_guard")
    assert locked is True, "2 missing + 5 unique sha → 寬鬆鎖定（向下相容過渡）"
    assert value == 0.80


def test_partial_missing_sha_below_min_threshold_should_not_lock() -> None:
    """SD_09 W3 Round 21 audit Architect P1 #2 收緊：

    non-None 部分 < N - MAX_BACKWARD_COMPAT_MISSING = 5 → 拒絕（即使 unique）。

    取證情境：歷史中 6 筆缺欄位 + 僅 1 筆有 sha → 取證資料不足 → 不可鎖定。
    """
    history = [
        {"kill_rate": 0.80, "module": "token_guard"} for _ in range(6)
    ] + [
        {"kill_rate": 0.80, "module": "token_guard", "source_sha256": "onesha0000000000"}
    ]
    assert len(history) == CONSECUTIVE_RUNS
    locked, _ = should_lock(history, "token_guard")
    assert locked is False, "non-None < 5 → 取證不足拒絕（Round 21 收緊）"


def test_partial_missing_sha_three_missing_four_unique_should_not_lock_round21() -> None:
    """SD_09 W3 Round 21 audit Architect P1 #2 修復（核心 adversarial 情境）：

    Architect 指出原 ceil(N/2)=4 寬鬆規則允許 3 missing + 4 unique sha 鎖定，
    比預期 7 unique 弱 43%。收緊 Round 21 後改為 min_non_none=5，此情境應 REJECT。
    """
    history = [
        {"kill_rate": 0.80, "module": "token_guard"} for _ in range(3)
    ] + [
        {"kill_rate": 0.80, "module": "token_guard", "source_sha256": f"unique{i:010d}"}
        for i in range(4)
    ]
    assert len(history) == CONSECUTIVE_RUNS
    locked, _ = should_lock(history, "token_guard")
    assert locked is False, (
        "Round 21 收緊：3 missing + 4 unique sha 應拒絕（原 ceil(N/2)=4 過寬，"
        "收緊為 N-MAX_MISSING=5；Architect P1 #2 修復）"
    )


def test_compute_source_sha256_stable_and_distinguishes_changes(tmp_path: Path) -> None:
    """compute_source_sha256：同 source 同 sha；改 source 換 sha。"""
    from tools.mutation_baseline_lock import compute_source_sha256

    module_dir = tmp_path / "mock_module"
    module_dir.mkdir()
    (module_dir / "a.py").write_text("x = 1\n", encoding="utf-8")
    (module_dir / "b.py").write_text("y = 2\n", encoding="utf-8")
    sha1 = compute_source_sha256(module_dir)
    sha2 = compute_source_sha256(module_dir)
    assert sha1 == sha2
    assert len(sha1) == 16

    (module_dir / "a.py").write_text("x = 999\n", encoding="utf-8")
    sha3 = compute_source_sha256(module_dir)
    assert sha3 != sha1


def test_compute_source_sha256_missing_dir_returns_unknown(tmp_path: Path) -> None:
    from tools.mutation_baseline_lock import compute_source_sha256

    sha = compute_source_sha256(tmp_path / "nonexistent")
    assert sha == "unknown"


# ----- P1-2: log mtime guard -----


def test_log_mtime_guard_rejects_stale_log(tmp_path: Path) -> None:
    """log mtime > N 秒 → main() 應 return 1。"""
    import os
    import time

    from tools.mutation_baseline_lock import main as lock_main

    log = tmp_path / "stale.log"
    log.write_text(
        "--- mutmut full counts (test) ---\n"
        "Killed (10)\nSurvived (1)\nTimeout (0)\nSuspicious (0)\nSkipped (0)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    # 把 mtime 設為 2 小時前
    old = time.time() - 7200
    os.utime(log, (old, old))

    rc = lock_main([
        "token_guard",
        "--log", str(log),
        "--history", str(tmp_path / "h.jsonl"),
        "--baseline", str(tmp_path / "b.toml"),
        "--require-log-mtime-within-seconds", "3600",
    ])
    assert rc == 1


def test_log_mtime_guard_passes_fresh_log(tmp_path: Path) -> None:
    """log mtime 在 N 秒內 → main() return 0（觀察期累積中）。"""
    from tools.mutation_baseline_lock import main as lock_main

    log = tmp_path / "fresh.log"
    log.write_text(
        "--- mutmut full counts (test) ---\n"
        "Killed (10)\nSurvived (1)\nTimeout (0)\nSuspicious (0)\nSkipped (0)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    rc = lock_main([
        "token_guard",
        "--log", str(log),
        "--history", str(tmp_path / "h.jsonl"),
        "--baseline", str(tmp_path / "b.toml"),
        "--require-log-mtime-within-seconds", "3600",
    ])
    assert rc == 0


# ----- SD_09 W3 Round 8 audit P2-NEW-1：stderr 拒鎖理由標籤 -----


def test_should_lock_stderr_reason_insufficient_runs(capsys: pytest.CaptureFixture[str]) -> None:
    """Round 8 P2-NEW-1：未滿 7 筆時印 reason=insufficient_runs。"""
    history = [{"kill_rate": 0.80, "module": "token_guard"} for _ in range(3)]
    locked, _ = should_lock(history, "token_guard")
    assert locked is False
    err = capsys.readouterr().err
    assert "reason=insufficient_runs" in err
    assert "count=3/7" in err


def test_should_lock_stderr_reason_kill_rate_below_threshold(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Round 8 P2-NEW-1：kill_rate 跌破 threshold 印 reason=kill_rate_below_threshold。

    對應本輪 audit 發現：kill_rate=0.6979 < threshold=0.70 → 即使 unique sha
    後續達標也永遠拒鎖；以往無 stderr 取證 → 使用者誤判進度為「unique sha 不足」。
    """
    # 6 筆達標 + 1 筆跌破 → 拒鎖；reason 必須指向 kill_rate
    # ADR-SD09-009 §5.5 ±2pp tolerance：effective threshold = 0.75 - 0.05 - 0.02 = 0.68
    # 7th rate 0.6779 < 0.68 → 仍拒鎖（守住新門檻）
    history = [
        {"kill_rate": 0.80, "module": "token_guard", "source_sha256": f"sha{i:013d}"}
        for i in range(6)
    ] + [
        {"kill_rate": 0.6779, "module": "token_guard", "source_sha256": "sha9999999999999"}
    ]
    assert len(history) == CONSECUTIVE_RUNS
    locked, _ = should_lock(history, "token_guard")
    assert locked is False
    err = capsys.readouterr().err
    assert "reason=kill_rate_below_threshold" in err
    assert "threshold=0.6800" in err
    assert "below_count=1/7" in err
    assert "min_score=0.6779" in err


def test_should_lock_stderr_reason_sha_not_unique_full(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Round 8 P2-NEW-1：全 sha 但有重複 → reason=sha_not_unique_full。"""
    history = [
        {"kill_rate": 0.80, "module": "token_guard", "source_sha256": "samesha000000000"}
        for _ in range(7)
    ]
    locked, _ = should_lock(history, "token_guard")
    assert locked is False
    err = capsys.readouterr().err
    assert "reason=sha_not_unique_full" in err
    assert "unique=1/7" in err


def test_should_lock_stderr_reason_sha_partial_below_min(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Round 8 P2-NEW-1 + Round 21 Architect P1 #2 收緊：
    non-None < N - MAX_BACKWARD_COMPAT_MISSING = 5 → reason=sha_partial_below_min。"""
    history = [
        {"kill_rate": 0.80, "module": "token_guard"} for _ in range(6)
    ] + [
        {"kill_rate": 0.80, "module": "token_guard", "source_sha256": "onesha0000000000"}
    ]
    locked, _ = should_lock(history, "token_guard")
    assert locked is False
    err = capsys.readouterr().err
    assert "reason=sha_partial_below_min" in err
    assert "non_none=1/5" in err  # Round 21 收緊：min_non_none = 7-2 = 5


def test_should_lock_stderr_reason_sha_partial_duplicate(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Round 8 P2-NEW-1：部分缺 sha + non-None 含重複 → reason=sha_partial_duplicate。"""
    history = [
        {"kill_rate": 0.80, "module": "token_guard"} for _ in range(2)
    ] + [
        {"kill_rate": 0.80, "module": "token_guard", "source_sha256": "samesha000000000"}
        for _ in range(5)
    ]
    locked, _ = should_lock(history, "token_guard")
    assert locked is False
    err = capsys.readouterr().err
    assert "reason=sha_partial_duplicate" in err
    assert "unique=1/5" in err


def test_should_lock_unknown_module_stderr_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Round 8 P2-NEW-1：未知 module 印 reason=unknown_module。"""
    locked, _ = should_lock([{"kill_rate": 0.9}] * 10, "nonexistent_module")
    assert locked is False
    err = capsys.readouterr().err
    assert "reason=unknown_module" in err


# ----- SD_09 W3 Round 31 audit P1-R31-2：multi-run consistency check（紀律 #12 強化）-----


def test_consistency_warning_high_variance_same_sha() -> None:
    """R31 P1-R31-2：同 sha 兩筆 kill_rate 0.85 / 0.75（stddev ≈ 5pp > 3pp）→ triggered。

    取證情境（R30 vs R31）：sha=20940e1b 第 1 筆 85.57%、第 2 筆同 sha 復跑 74.83%
    → variance > 3pp 應印 WARN，標示 mutmut suspicious 非確定性風險。
    """
    history = [
        {"module": "token_guard", "kill_rate": 0.85, "source_sha256": "20940e1b903dc19d"},
        {"module": "token_guard", "kill_rate": 0.75, "source_sha256": "20940e1b903dc19d"},
    ]
    triggered, msg = compute_consistency_warning(history, "token_guard")
    assert triggered is True
    assert "sha=20940e1b903dc19d" in msg
    assert "runs=2" in msg
    assert "stddev=" in msg
    assert "mutmut suspicious non-determinism" in msg


def test_consistency_warning_low_variance_same_sha() -> None:
    """R31 P1-R31-2：同 sha 兩筆 kill_rate 0.75 / 0.76（stddev ≈ 0.5pp < 3pp）→ no trigger。

    證明 ±3pp threshold 容忍 mutmut 正常採樣噪音（ADR-SD09-009 ±2pp tolerance 同精神）。
    """
    history = [
        {"module": "token_guard", "kill_rate": 0.75, "source_sha256": "samesha000000000"},
        {"module": "token_guard", "kill_rate": 0.76, "source_sha256": "samesha000000000"},
    ]
    triggered, msg = compute_consistency_warning(history, "token_guard")
    assert triggered is False
    assert msg == ""


def test_consistency_warning_different_sha_no_check() -> None:
    """R31 P1-R31-2：不同 sha 各 1 筆 → 無法比對 variance → no trigger。

    取證情境：每筆 sha 唯一即 R29 SP-1 落地後的健康狀態，不該誤觸 WARN。
    """
    history = [
        {"module": "token_guard", "kill_rate": 0.85, "source_sha256": "sha_a00000000000"},
        {"module": "token_guard", "kill_rate": 0.65, "source_sha256": "sha_b00000000000"},
    ]
    triggered, msg = compute_consistency_warning(history, "token_guard")
    assert triggered is False
    assert msg == ""


def test_consistency_warning_module_filter_isolation() -> None:
    """R31 P1-R31-2：他模組同 sha 變異不應影響當前 module 判定。"""
    history = [
        {"module": "goal_synthesis", "kill_rate": 0.95, "source_sha256": "shared0000000000"},
        {"module": "goal_synthesis", "kill_rate": 0.50, "source_sha256": "shared0000000000"},
        {"module": "token_guard", "kill_rate": 0.75, "source_sha256": "shared0000000000"},
    ]
    triggered, _ = compute_consistency_warning(history, "token_guard")
    assert triggered is False


def test_consistency_warning_missing_sha_skipped() -> None:
    """R31 P1-R31-2：缺 sha 的 record 跳過（向下相容 legacy 紀錄）。"""
    history = [
        {"module": "token_guard", "kill_rate": 0.85},  # 缺 sha
        {"module": "token_guard", "kill_rate": 0.75},  # 缺 sha
    ]
    triggered, _ = compute_consistency_warning(history, "token_guard")
    assert triggered is False


def test_consistency_warning_custom_threshold() -> None:
    """R31 P1-R31-2：threshold 可調 — 同 sha 1pp variance 用 0.5pp threshold 應 trigger。"""
    history = [
        {"module": "token_guard", "kill_rate": 0.75, "source_sha256": "samesha000000000"},
        {"module": "token_guard", "kill_rate": 0.76, "source_sha256": "samesha000000000"},
    ]
    triggered, msg = compute_consistency_warning(history, "token_guard", threshold=0.005)
    assert triggered is True
    assert "threshold 0pp" in msg or "threshold 1pp" in msg  # 0.005 → 0% 或 1% 格式
