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

R76 追加（掃描發現 R76-13）：
  9. test_thirty_consecutive_days_is_green      — 30 天每天一筆 → ready
 10. test_thirty_records_with_a_hole_is_sparse  — 30 筆但中間空 12 天 → sparse（rc=1）
 11. test_stale_evidence_is_not_ready           — streak 夠但採集停擺 → stale（rc=1）
 12. test_stale_takes_precedence_over_sparse    — 兩者同時成立時的狀態優先序
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from tools.drift_log_ga_check import (
    STALENESS_MAX_DAYS,
    WINDOW_SPAN_MAX_FACTOR,
    _compute_green_streak,
    _is_green,
    evaluate,
    main,
)

#: 注入式時鐘（ac4_progress_check.py 的同款作法）：staleness／窗內連續性都是時間判準，
#: 要有雙向鑑別力就必須能穩定驗紅與驗綠，而真實時鐘做不到。
_NOW = _dt.datetime(2026, 6, 30, 12, 0, tzinfo=_dt.UTC)


def _ts_before(days: int, *, now: _dt.datetime = _NOW) -> str:
    """相對某個「現在」往回 N 天的 UTC 時間戳。"""
    return (now - _dt.timedelta(days=days)).isoformat(timespec="seconds")


def _recent_ts(days_ago: int) -> str:
    """相對**真實**現在往回 N 天——給走 `main()`（真實時鐘）的整合測試用。

    🔴 R76 起 GA 判準含 staleness，寫死日期的 fixture 會隨時間腐化成 stale：那時紅的是
    測試自己過期，不是被測物壞掉，而訊息會指向錯的方向。故凡斷言 `rc==0` 或斷言
    `status`／`last_failure_reason` 具體值的整合測試，一律改用相對時間戳。
    """
    return _ts_before(days_ago, now=_dt.datetime.now(tz=_dt.UTC))


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
    records = [_green_record(_recent_ts(d)) for d in range(4, -1, -1)]
    _write_jsonl(hist, records)
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "observing"
    assert payload["green_streak"] == 5


def test_streak_eq_window_returns_0(tmp_path: Path, capsys) -> None:
    hist = tmp_path / "h.jsonl"
    records = [_green_record(_recent_ts(d)) for d in range(29, -1, -1)]
    _write_jsonl(hist, records)
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert payload["green_streak"] == 30


def test_streak_gt_window_returns_0(tmp_path: Path, capsys) -> None:
    hist = tmp_path / "h.jsonl"
    records = [_green_record(_recent_ts(d)) for d in range(31, -1, -1)]
    _write_jsonl(hist, records)
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["green_streak"] == 32


def test_failure_in_middle_only_counts_tail(tmp_path: Path, capsys) -> None:
    """中間 failure 不影響：streak 一律從 tail 數連續綠。"""
    hist = tmp_path / "h.jsonl"
    records = [_green_record(_recent_ts(d)) for d in range(14, 5, -1)]
    records.append(_severity_record(_recent_ts(5), n=2))  # break
    records.extend(_green_record(_recent_ts(d)) for d in range(4, -1, -1))
    _write_jsonl(hist, records)
    rc = main(["--history", str(hist), "--window", "30", "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["green_streak"] == 5
    assert "severity_non_info_count" in payload["last_failure_reason"]


# ----- R76：筆數 ≠ 天數（掃描發現 R76-13）----- #


def test_thirty_consecutive_days_is_green() -> None:
    """✅ 綠向：30 筆鋪在 30 個**連續**日曆天上 → ready。

    意圖（Rule 9）：這一格是 sparse/stale 兩條新判準的「不得誤殺」邊界。少了它，
    「把門檻收緊」很容易被實作成「任何窗都判紅」，那會讓 GA 永遠到不了。
    """
    records = [_green_record(_ts_before(d)) for d in range(29, -1, -1)]
    report = evaluate(records, window=30, now=_NOW)
    assert report["status"] == "ready", report["last_failure_reason"]
    assert report["green_streak"] == 30
    assert report["window_span_days"] == 30
    assert report["window_max_gap_days"] == 1
    assert report["staleness_days"] == 0


def test_thirty_records_with_a_hole_is_sparse() -> None:
    """🔴 紅向：一樣 30 筆全綠，但窗內有一段 12 天全黑 → sparse（rc≠0）。

    這正是實測抓到的形態：observability 以「30 筆橫跨 58 天、含 12 天全黑」宣告
    「30 天零事件取證通過」。筆數判準對「整段沒跑」零偵測，兩者只在真的天天跑時相等。
    """
    # 舊區塊 13 筆（days_ago 41..29）→ 中間 12 天全黑（28..17）→ 新區塊 17 筆（16..0）
    days = [*range(41, 28, -1), *range(16, -1, -1)]
    records = [_green_record(_ts_before(d)) for d in days]
    report = evaluate(records, window=30, now=_NOW)
    assert len(records) == 30
    assert report["green_streak"] == 30, "筆數判準本身仍然是滿的——紅必須來自天數這一面"
    assert report["status"] == "sparse", report
    assert report["window_span_days"] == 42, "42 天塞 30 筆＝12 天沒量到"
    assert report["window_max_gap_days"] == 13, "相鄰兩筆差 13 天＝中間 12 天全黑"
    assert report["window_span_max_days"] == 40, "window=30 × 4/3 = 40，門檻本身也要被釘住"
    assert "筆數夠不代表天數夠" in report["last_failure_reason"]


def test_stale_evidence_is_not_ready() -> None:
    """🔴 紅向：streak 與跨度都完美，但整批是 STALENESS_MAX_DAYS 以前的舊帳 → stale。

    意圖：streak 回答「證據夠不夠」，staleness 回答「證據還算不算數」。採集器死掉時
    streak 不會退步，只會**停住**——而停住看起來與「還在觀察」一模一樣。
    """
    offset = STALENESS_MAX_DAYS + 5
    records = [_green_record(_ts_before(offset + d)) for d in range(29, -1, -1)]
    report = evaluate(records, window=30, now=_NOW)
    assert report["green_streak"] == 30
    assert report["window_span_days"] == 30, "跨度這一面是乾淨的——紅必須來自新鮮度"
    assert report["status"] == "stale", report
    assert report["staleness_days"] == offset


def test_stale_takes_precedence_over_sparse() -> None:
    """兩條都不成立時報 stale：稀疏只是採集停擺的症狀，先報停擺才指得到正確修法。"""
    offset = STALENESS_MAX_DAYS + 5
    days = [offset + d for d in (60, 50, 40, 30, 20, 10, 0)]
    records = [_green_record(_ts_before(d)) for d in days]
    report = evaluate(records, window=7, now=_NOW)
    assert report["window_span_days"] > int(7 * WINDOW_SPAN_MAX_FACTOR)
    assert report["status"] == "stale", report


# ══════════════════════════════════════════════════════════════════════════════
# R76 四方複審 SD-04：兩支 GA checker 的時間窗判準必須是**同一個物件**
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體：R76 落地首版讓兩支 checker 各自帶一份逐字相同的 112 行實作、零 parity 鎖。
# 實測把 drift 的 `STALENESS_MAX_DAYS` 單邊改成 45（兩支測試檔都用相對寫法
# `STALENESS_MAX_DAYS + 5`，所以改了也不會紅），三支相關測試檔仍 `108 passed rc=0`
# ——沒有任何東西會叫。而 nightly 的 G0 是拿 obs／drift 兩軌**一起**判的，兩支各說各話
# 會讓 `.g0_readiness.json` 自我矛盾。
#
# 更難看的是它在同一輪就已經走岔：obs 的 `_parse_ts` **沒做 tz 正規化**（本檔那份有），
# 於是兩支「逐字相同」的 `evaluate()` 餵同一筆 naive 時戳，drift 回 ready、obs 直接
# `TypeError`。這正是 `DEF-101-778`「同一份知識住兩個家、只有一個家被修」的復發。
#
# 修法＝抽 `tools/ga_window.py` 共用層，兩支 re-export。本組鎖用 `assertIs` 綁住
# 「是同一個物件」，讓「又抄了一份」在下一次就當場紅（宣告意圖的註解不是機械物）。
_GA_SHARED_NAMES = (
    ("STALENESS_MAX_DAYS", "STALENESS_MAX_DAYS"),
    ("WINDOW_SPAN_MAX_FACTOR", "WINDOW_SPAN_MAX_FACTOR"),
    ("_parse_ts", "parse_ts"),
    ("_staleness_days", "staleness_days"),
    ("_window_calendar_span", "window_calendar_span"),
)


def test_both_ga_checkers_share_one_time_window_implementation() -> None:
    """兩支 checker 的時間窗常數與函式必須逐一 `is` 共用層的那一個。"""
    from tools import drift_log_ga_check as drift
    from tools import ga_window
    from tools import observability_ga_check as obs

    for tool in (drift, obs):
        for local, shared in _GA_SHARED_NAMES:
            assert hasattr(tool, local), f"{tool.__name__} 缺 {local}"
            assert getattr(tool, local) is getattr(ga_window, shared), (
                f"{tool.__name__}.{local} 不是 tools/ga_window.{shared} 那一個物件 "
                "⇒ 又出現第二份複本。單邊改動不會有任何東西叫，而 nightly 的 G0 是拿"
                "兩軌一起判的（見本區塊 WHY）"
            )


def test_the_two_checkers_agree_on_a_naive_timestamp() -> None:
    """行為層對照（不是只驗身分）：同一筆 **naive** 時戳，兩支必須給同一個答案。

    這正是 R76 走岔的那一格——修好之前 drift 回 ready、obs 擲 TypeError。
    """
    from tools import drift_log_ga_check as drift
    from tools import observability_ga_check as obs

    naive = _NOW.replace(tzinfo=None).isoformat(timespec="seconds")
    assert "+" not in naive and not naive.endswith("Z"), naive
    parsed = [tool._parse_ts({"ts": naive}) for tool in (drift, obs)]
    assert parsed[0] == parsed[1], f"兩支對同一筆 naive 時戳解析不一致：{parsed}"
    assert parsed[0] is not None and parsed[0].tzinfo is not None, (
        "naive 時戳必須被補上 UTC——否則與模組內其他 aware 常數比較會擲 TypeError")


def test_evaluate_still_injects_each_tools_own_green_criterion() -> None:
    """反向：共用層不得把兩支**不同**的綠判準也合併掉（那會是另一種缺陷）。

    drift 看 `drift_log_table_exists`／`severity_non_info_count`；obs 看 KB metric 與
    legacy／strict 的 ts cutoff。合成一個帶旗標的函式只會兩邊都不對。
    """
    from tools import drift_log_ga_check as drift
    from tools import observability_ga_check as obs

    assert drift._compute_green_streak is not obs._compute_green_streak
    rec = [{"ts": _ts_before(0), "passed": True, "drift_log_table_exists": True,
            "severity_non_info_count": 0}]
    # 同一筆紀錄：drift 判綠，obs 因缺 KB metric 判紅 ⇒ 綠判準確實仍各自獨立。
    assert drift.evaluate(rec, window=1, now=_NOW)["green_streak"] == 1
    assert obs.evaluate(rec, window=1, now=_NOW)["green_streak"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 🔴 DEF-101-887：`tools/ga_window.evaluate` 在算任何判準前先剔除中間態樣本
# ══════════════════════════════════════════════════════════════════════════════
# 與 ac4 那支同一件事、同一組意圖（見 test_ac4_progress_check.py 檔尾同編號段）：
# `tree.valid is False`（非乾淨工作樹所採）的樣本不得影響 streak／staleness／sparse
# 三個判準；缺 `tree` 的舊樣本與 `valid=None` 保留；剔除如實回報，全部被剔除時明說
# 「證據不足」而不是被讀成 stale（採集器壞掉）。共用層住 ga_window，這裡以 drift 的綠
# 判準注入驗證；obs 那條注入路徑見 test_observability_ga_check.py 檔尾。


def _dirty(rec: dict) -> dict:
    return {**rec, "tree": {"valid": False, "state": "dirty"}}


def _unmark(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k != "tree"}


def _thirty_consecutive_days() -> list[dict]:
    """最舊→最新、每天一筆的 30 筆綠紀錄（最新一筆＝_NOW 當天）。"""
    return [_green_record(_ts_before(d)) for d in range(29, -1, -1)]


def test_a_red_sample_from_a_dirty_tree_does_not_break_the_ga_streak() -> None:
    records = _thirty_consecutive_days()
    red = _missing_table_record(_ts_before(10).replace("T12", "T18"))
    records.insert(20, _dirty(red))  # 夾在第 20、21 筆之間（時間上也在 10 天前那一格）

    result = evaluate(records, window=30, now=_NOW)

    assert result["excluded_dirty"] == 1
    assert result["total_records"] == 30, "total_records 是剔除後的筆數"
    assert result["green_streak"] == 30 and result["status"] == "ready"

    # 對照組：同一筆紅燈沒有髒樹標記 ⇒ 真紅，streak 從它之後重新數
    control = evaluate([_unmark(r) for r in records], window=30, now=_NOW)
    assert control["excluded_dirty"] == 0
    assert control["green_streak"] == 10 and control["status"] == "observing"


def test_a_green_sample_from_a_dirty_tree_does_not_count_toward_the_ga_streak() -> None:
    records = _thirty_consecutive_days()
    records = records[:25] + [_dirty(r) for r in records[25:]]  # 最近 5 晚都是髒樹

    result = evaluate(records, window=30, now=_NOW)

    assert result["excluded_dirty"] == 5
    assert result["green_streak"] == 25
    assert result["status"] == "observing"

    control = evaluate([_unmark(r) for r in records], window=30, now=_NOW)
    assert control["green_streak"] == 30 and control["status"] == "ready"


def test_a_dirty_sample_does_not_keep_ga_evidence_looking_fresh() -> None:
    """最後一筆有效樣本已是 50 天前；昨天那筆髒樹樣本不得替它續命。"""
    old = [_green_record(_ts_before(d)) for d in range(79, 49, -1)]  # 79..50 天前，30 筆
    latest = _green_record(_ts_before(1))

    result = evaluate([*old, _dirty(latest)], window=30, now=_NOW)

    assert result["status"] == "stale"
    assert result["staleness_days"] == 50, "新鮮度要從最後一筆**有效**樣本起算"

    control = evaluate([*old, latest], window=30, now=_NOW)
    assert control["staleness_days"] == 1 and control["status"] != "stale"


def test_all_samples_dirty_is_insufficient_evidence_not_stale_and_never_ready() -> None:
    records = [_dirty(_green_record(_ts_before(d))) for d in (2, 1, 0)]

    result = evaluate(records, window=3, now=_NOW)

    assert result["excluded_dirty"] == 3 and result["total_records"] == 0
    assert result["status"] == "observing", "採集器活著、只是樣本無效，不是 stale"
    assert result["green_streak"] == 0
    assert "證據不足" in result["last_failure_reason"]
    assert "excluded_dirty=3" in result["last_failure_reason"]
    assert result["window_span_days"] is None and result["staleness_days"] is None
    # fail-closed：就算 window 被設成 0（`streak >= window` 恆真），沒有有效證據也不得 ready
    assert evaluate(records, window=0, now=_NOW)["status"] != "ready"


def test_ga_history_without_tree_is_untouched_by_exclusion() -> None:
    result = evaluate(_thirty_consecutive_days(), window=30, now=_NOW)

    assert result["excluded_dirty"] == 0
    assert result["total_records"] == 30 and result["status"] == "ready"


def test_ga_cli_json_carries_excluded_dirty_and_all_dirty_does_not_crash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """全部被剔除時 `window_span_days`／`staleness_days` 都是 None——兩種輸出都不得炸。"""
    history = tmp_path / ".drift.jsonl"
    _write_jsonl(history, [_dirty(_green_record(_recent_ts(d))) for d in (2, 1, 0)])

    rc_json = main(["--window", "3", "--history", str(history), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc_json == 1
    assert payload["excluded_dirty"] == 3 and payload["status"] == "observing"

    rc_human = main(["--window", "3", "--history", str(history)])
    err = capsys.readouterr().err
    assert rc_human == 1
    assert "status=observing" in err and "證據不足" in err
