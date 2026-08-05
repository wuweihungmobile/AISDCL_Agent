"""tests/tools/test_observability_ga_check.py — W1 backlog P1-TEST-MIRROR-1 補建。

對應 tools/observability_ga_check.py（W5 雙條件 (1a) 30 天取證唯一工具）。
紀律 #4「驗證鏡子自身要被驗證」— 升級判定工具必須有單元測試覆蓋 fake-PASS 拒絕。

對應修復來源：
- SD_09 W1 backlog P1-TEST-MIRROR-1（W3 zero-trust audit 識別）
- SD_09 W3 zero-trust audit F1（observability_emit_real 欄位 fallback 拒絕）

R76 追加（掃描發現 R76-13）：window 量的是**筆數**不是日曆天 ⇒ 新增 staleness／窗內連續性
兩個獨立判準的雙向鑑別力測試（連續 30 天 → 綠；30 筆但中間空 12 天 → 紅）。
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from tools.observability_ga_check import (
    KB_METRIC_REQUIRED_KEYS,
    STALENESS_MAX_DAYS,
    _compute_green_streak,
    _is_green,
    _load_history,
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
    測試自己過期，不是被測物壞掉，而訊息會指向錯的方向。
    """
    return _ts_before(days_ago, now=_dt.datetime.now(tz=_dt.UTC))


def _make_record(
    *,
    emit_count: int = 3,
    emit_real: bool | None = True,
    trace_continuity: bool = True,
    kb_keys: set[str] | None = None,
    ts: str = "2026-05-24T00:00:00+00:00",
    invalid: bool = False,
) -> dict:
    """製造一筆 observability snapshot record。"""
    if invalid:
        return {"_invalid": True, "_raw": "broken"}
    kb_keys = kb_keys if kb_keys is not None else set(KB_METRIC_REQUIRED_KEYS)
    record = {
        "ts": ts,
        "observability_emit_count": emit_count,
        "trace_id_continuity": trace_continuity,
        "kb_metric_snapshot": {k: 0.0 for k in kb_keys},
    }
    if emit_real is not None:
        record["observability_emit_real"] = emit_real
    return record


# === _is_green 單筆判定 ===

def test_is_green_happy_path() -> None:
    """完整綠標：count>0 + emit_real=True + trace_continuity=True + kb 4 keys 齊備。"""
    ok, reason = _is_green(_make_record())
    assert ok is True
    assert reason == ""


def test_is_green_rejects_emit_count_zero() -> None:
    """count=0 → 拒絕（fake-PASS 場景 #1）。"""
    ok, reason = _is_green(_make_record(emit_count=0))
    assert ok is False
    assert "observability_emit_count" in reason


def test_is_green_rejects_emit_real_false() -> None:
    """F1 修復驗證 — emit_real=False fallback 路徑必須拒絕（fake-PASS 場景 #2）。

    這是 F1 修復的核心：原本 fallback `count=1` 與真實 emit 1 次無法區分，
    現在加入 emit_real 欄位後 ga_check 可拒絕 fallback 路徑。
    """
    ok, reason = _is_green(_make_record(emit_real=False, emit_count=1))
    assert ok is False
    assert "observability_emit_real" in reason
    assert "fallback" in reason.lower() or "not real emit" in reason.lower()


def test_is_green_legacy_record_without_emit_real() -> None:
    """向後相容：舊紀錄無 emit_real 欄位（2026-05-21 前）以 True 寬鬆處理。

    F1 修復策略：避免歷史累計被新欄位打斷（已寫入 jsonl 數筆無此欄位）。
    """
    record = _make_record(emit_real=None)  # 不寫入 emit_real 欄位
    assert "observability_emit_real" not in record
    ok, reason = _is_green(record)
    assert ok is True, f"舊紀錄應寬鬆通過；reason={reason}"


def test_is_green_rejects_trace_continuity_false() -> None:
    """trace_id_continuity != True → 拒絕。"""
    ok, reason = _is_green(_make_record(trace_continuity=False))
    assert ok is False
    assert "trace_id_continuity" in reason


def test_is_green_rejects_missing_kb_keys() -> None:
    """KB metric snapshot 缺必要 keys → 拒絕。"""
    ok, reason = _is_green(_make_record(kb_keys={"hit_rate"}))  # 只給 1 個，缺 3
    assert ok is False
    assert "kb_metric_snapshot" in reason
    assert "missing" in reason.lower()


def test_is_green_rejects_invalid_json() -> None:
    """壞 JSON record → 拒絕。"""
    ok, reason = _is_green(_make_record(invalid=True))
    assert ok is False
    assert "invalid" in reason.lower()


# === _compute_green_streak 連續綠計算 ===

def test_green_streak_consecutive() -> None:
    """連續綠 → streak = 紀錄筆數。"""
    records = [_make_record(ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(1, 6)]
    streak, judgements = _compute_green_streak(records)
    assert streak == 5
    assert all(j["green"] for j in judgements)


def test_green_streak_breaks_at_last_fail() -> None:
    """末筆失敗 → streak=0；前面綠不算。"""
    records = [
        _make_record(ts="2026-05-01T00:00:00+00:00"),
        _make_record(ts="2026-05-02T00:00:00+00:00"),
        _make_record(ts="2026-05-03T00:00:00+00:00", emit_real=False),  # 末筆 fail
    ]
    streak, _ = _compute_green_streak(records)
    assert streak == 0


def test_green_streak_partial_recovery() -> None:
    """中間失敗後恢復 → streak 從末筆往回算，碰到失敗即停止。"""
    records = [
        _make_record(ts="2026-05-01T00:00:00+00:00"),
        _make_record(ts="2026-05-02T00:00:00+00:00", emit_real=False),  # 中間 fail
        _make_record(ts="2026-05-03T00:00:00+00:00"),
        _make_record(ts="2026-05-04T00:00:00+00:00"),
    ]
    streak, _ = _compute_green_streak(records)
    assert streak == 2, "從末筆往回算碰到失敗停止 → 2 筆綠"


# === main CLI 整合 ===

def test_main_passes_when_streak_meets_window(tmp_path: Path) -> None:
    """main --window 3 + 5 筆全綠 → exit 0。"""
    history = tmp_path / "history.jsonl"
    records = [_make_record(ts=_recent_ts(d)) for d in range(4, -1, -1)]
    history.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    rc = main(["--window", "3", "--history", str(history), "--json"])
    assert rc == 0


def test_main_fails_when_no_history(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """main 找不到 history → exit 1（紀律 #1：採集未啟動誠實回報 fail）。"""
    history = tmp_path / "nonexistent.jsonl"
    rc = main(["--window", "30", "--history", str(history), "--json"])
    assert rc == 1


def test_main_fails_when_fallback_emit_in_streak() -> None:
    """F1 整合驗證：末筆 fallback emit → 非 ready（fake-PASS 場景被拒絕）。

    🔴 R76 改走 `evaluate(now=…)`：原本走 `main()` 配寫死的 2026-05 日期，加了 staleness
    之後它會因為「證據過期」而 rc=1——**答案對、理由錯**，等於這支測試從此不再守
    emit_real 那一格。注入時鐘讓紅的理由回到 streak 本身。
    """
    records = [
        _make_record(ts=_ts_before(2)),
        _make_record(ts=_ts_before(1)),
        _make_record(ts=_ts_before(0), emit_real=False),  # 末筆 fallback
    ]
    report = evaluate(records, window=2, now=_NOW)
    assert report["status"] == "observing", report
    assert report["green_streak"] == 0, "末筆 emit_real=False 應中斷 streak"
    assert "observability_emit_real" in report["last_failure_reason"]


#: cutoff 相關的兩支測試必須用**真實歷史日期**（EMIT_REAL_REQUIRED_FROM=2026-05-24 是
#: 寫死的日期），故它們的「現在」得跟著釘在那段期間，否則 staleness 會先把它們判紅
#: （答案對、理由錯 ⇒ 這兩支從此不再守 cutoff 那一格）。
_CUTOFF_ERA_NOW = _dt.datetime(2026, 5, 28, 12, 0, tzinfo=_dt.UTC)


def test_strict_cutoff_rejects_missing_emit_real_after_cutoff() -> None:
    """SD_09 W3 Round 3 audit P1-2：ts >= 2026-05-24 cutoff 缺 emit_real → fail。

    取代 W3 Round 2 P1-1 滑動窗口設計（最新 3 筆 strict）：
    cutoff-based 語意明確（一個明確日期判定），不會因 history 長度而漂移。
    """
    records = [
        # 舊紀錄（cutoff 前）缺 emit_real → 寬鬆通過
        _make_record(ts="2026-05-21T00:00:00+00:00", emit_real=None),
        _make_record(ts="2026-05-22T00:00:00+00:00", emit_real=None),
        _make_record(ts="2026-05-23T00:00:00+00:00", emit_real=None),
        # 2026-05-24 起 strict：最後一筆缺 emit_real → fail → streak=0
        _make_record(ts="2026-05-25T00:00:00+00:00", emit_real=True),
        _make_record(ts="2026-05-26T00:00:00+00:00", emit_real=None),
    ]
    report = evaluate(records, window=2, now=_CUTOFF_ERA_NOW)
    assert report["status"] == "observing", report
    assert report["green_streak"] == 0, "cutoff 後缺 emit_real strict 模式應中斷 streak"
    assert "observability_emit_real missing" in report["last_failure_reason"]


def test_legacy_records_before_cutoff_lenient_pass(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """P1-2：cutoff 前舊紀錄缺 emit_real 寬鬆放行，cutoff 後紀錄有 emit_real=True → 全綠。

    且 stderr 印 warning（紀律 #10：不可 backfill 偽造欄位，需明確告知 lenient 路徑）。
    """
    records = [
        # cutoff 前舊紀錄缺欄位（寬鬆）
        _make_record(ts=f"2026-05-{d:02d}T00:00:00+00:00", emit_real=None)
        for d in range(21, 24)
    ]
    # cutoff 後紀錄有 emit_real=True（strict 通過）
    records.extend(
        _make_record(ts=f"2026-05-{d:02d}T00:00:00+00:00", emit_real=True)
        for d in range(24, 28)
    )
    report = evaluate(records, window=7, now=_CUTOFF_ERA_NOW)
    captured = capsys.readouterr()
    assert report["status"] == "ready", f"舊寬鬆 + 新 strict 全通過 → 7 筆綠；{report}"
    # 紀律 #10：lenient 路徑必須印 warning（不可悄悄通過）
    assert "legacy record" in captured.err.lower()
    assert "lenient pass" in captured.err.lower()


# ----- R76：筆數 ≠ 天數（掃描發現 R76-13）----- #


def test_thirty_consecutive_days_is_green() -> None:
    """✅ 綠向：30 筆鋪在 30 個**連續**日曆天上 → ready。

    意圖（Rule 9）：這一格是 sparse/stale 兩條新判準的「不得誤殺」邊界。少了它，
    「把門檻收緊」很容易被實作成「任何窗都判紅」，那會讓 GA 永遠到不了。
    """
    records = [_make_record(ts=_ts_before(d)) for d in range(29, -1, -1)]
    report = evaluate(records, window=30, now=_NOW)
    assert report["status"] == "ready", report["last_failure_reason"]
    assert report["green_streak"] == 30
    assert report["window_span_days"] == 30
    assert report["window_max_gap_days"] == 1
    assert report["staleness_days"] == 0


def test_thirty_records_with_a_hole_is_sparse() -> None:
    """🔴 紅向：一樣 30 筆全綠，但窗內有一段 12 天全黑 → sparse（rc≠0）。

    這正是 2026-08-05 在本機實測到的形態：obs 以「30 筆橫跨 58 個日曆天、含
    `2026-06-29 -> 2026-07-11 = 12 天`全黑」宣告「30 天零事件 GA 取證通過」。
    """
    # 舊區塊 13 筆（days_ago 41..29）→ 中間 12 天全黑（28..17）→ 新區塊 17 筆（16..0）
    days = [*range(41, 28, -1), *range(16, -1, -1)]
    records = [_make_record(ts=_ts_before(d)) for d in days]
    report = evaluate(records, window=30, now=_NOW)
    assert len(records) == 30
    assert report["green_streak"] == 30, "筆數判準本身仍然是滿的——紅必須來自天數這一面"
    assert report["status"] == "sparse", report
    assert report["window_span_days"] == 42, "42 天塞 30 筆＝12 天沒量到"
    assert report["window_max_gap_days"] == 13, "相鄰兩筆差 13 天＝中間 12 天全黑"
    assert report["window_span_max_days"] == 40, "window=30 × 4/3 = 40，門檻本身也要被釘住"
    assert "筆數夠不代表天數夠" in report["last_failure_reason"]


def test_stale_evidence_is_not_ready() -> None:
    """🔴 紅向：streak 與跨度都完美，但整批是 STALENESS_MAX_DAYS 以前的舊帳 → stale。"""
    offset = STALENESS_MAX_DAYS + 5
    records = [_make_record(ts=_ts_before(offset + d)) for d in range(29, -1, -1)]
    report = evaluate(records, window=30, now=_NOW)
    assert report["green_streak"] == 30
    assert report["window_span_days"] == 30, "跨度這一面是乾淨的——紅必須來自新鮮度"
    assert report["status"] == "stale", report
    assert report["staleness_days"] == offset


def test_load_history_skips_blank_lines(tmp_path: Path) -> None:
    """jsonl 空行 / 壞行容錯：壞行標 _invalid 並不阻塞讀取。"""
    history = tmp_path / "history.jsonl"
    history.write_text(
        json.dumps(_make_record(ts="2026-05-01T00:00:00+00:00")) + "\n"
        + "\n"
        + "not-json-line\n"
        + json.dumps(_make_record(ts="2026-05-02T00:00:00+00:00")) + "\n",
        encoding="utf-8",
    )
    records = _load_history(history)
    assert len(records) == 3  # 1 good + 1 invalid + 1 good
    assert records[1].get("_invalid") is True
