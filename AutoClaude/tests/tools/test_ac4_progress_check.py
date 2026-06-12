"""tests/tools/test_ac4_progress_check.py — SD_09 W3 Round 3 audit P0-1 補建。

對應 tools/ac4_progress_check.py（觀察期 #2 升級判定工具）。
紀律 #4「驗證鏡子自身要被驗證」— 雙軌設計必須有單元測試覆蓋。

對應修復來源：
- SD_09 W3 Round 3 audit P0-1（tolerant p95 雙軌設計）
- ADR-SD09-008 v0.1 PROPOSED（雙軌設計理由）
- SD_09 W3 Round 6 audit P0-AUDIT-R5-B（time-flaky main test — 改相對 now 避免跨日 cutoff race）
- SD_09 W3 Round 12 P0-R12-1（ADR-SD09-008 v0.4 ACCEPTED 拍板實作落地：升 60ms tolerant 為主軌）
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from tools.ac4_progress_check import (
    P95_MAX_MS,
    P95_OBSERVATION_MS,
    _is_green,
    _is_green_observation,
    _is_green_tolerant,
    evaluate,
    main,
)


def _rec(*, p95: float, recall: float = 0.999, cb: int = 0,
         status: str = "pass", ts: str = "2026-05-24T00:00:00+00:00") -> dict:
    return {
        "timestamp": ts,
        "run_id": "test",
        "recall_at_10": recall,
        "p95_ms": p95,
        "circuit_breaker_open_count": cb,
        "status": status,
    }


# ========== _is_green_tolerant 單筆（向下相容；ADR v0.4 ACCEPTED 後保留供舊呼叫） ==========

def test_tolerant_green_under_threshold() -> None:
    """p95 < tolerant 門檻 → 綠（True）。"""
    assert _is_green_tolerant(_rec(p95=55.0), tolerant_p95_ms=60.0) is True


def test_tolerant_green_at_upgrade_threshold_zone() -> None:
    """ADR v0.4 ACCEPTED 後：升級主軌 _is_green 已是 60ms tolerant。

    Round 12 修正：原測試假設 50~60ms 為「strict neutral 區」，
    但 ADR v0.3 後 60ms 已成正式升級門檻，p95=52.49 < 60ms → 直接綠（True）。
    """
    # 升級主軌：p95=52.49 < P95_MAX_MS (60ms ACCEPTED) → True
    assert _is_green(_rec(p95=52.49)) is True
    # 兼容呼叫 _is_green_tolerant(60) 同樣為 True
    assert _is_green_tolerant(_rec(p95=52.49), tolerant_p95_ms=60.0) is True
    # 觀察軌：p95=52.49 ≥ P95_OBSERVATION_MS (50ms) → False（向上相容指標未達）
    assert _is_green_observation(_rec(p95=52.49)) is False


def test_tolerant_fails_when_p95_exceeds() -> None:
    """p95 > tolerant 門檻 → fail。"""
    assert _is_green_tolerant(_rec(p95=65.0), tolerant_p95_ms=60.0) is False


def test_tolerant_status_skip_returns_none() -> None:
    """status=skip → None（中性 sentinel 保留）。"""
    assert _is_green_tolerant(_rec(p95=10.0, status="skip"), tolerant_p95_ms=60.0) is None


def test_tolerant_does_not_relax_recall() -> None:
    """recall 不達標 → fail（tolerant 軌僅放寬 p95，不放寬 recall）。"""
    assert _is_green_tolerant(_rec(p95=10.0, recall=0.5), tolerant_p95_ms=60.0) is False


# ========== _is_green_observation 觀察軌（ADR v0.4 ACCEPTED 新增） ==========


def test_observation_green_under_50ms() -> None:
    """p95 < P95_OBSERVATION_MS (50ms) → 觀察軌綠。"""
    assert _is_green_observation(_rec(p95=45.0)) is True


def test_observation_fails_at_50ms_and_above() -> None:
    """p95 ≥ 50ms → 觀察軌 fail（未來 production hardware 切換後可重新判定）。"""
    assert _is_green_observation(_rec(p95=50.0)) is False
    assert _is_green_observation(_rec(p95=55.0)) is False


# ========== evaluate dual track ==========

def test_evaluate_dual_track_strict_pass_tolerant_pass() -> None:
    """升級門檻 + 觀察軌全綠 → ready=True，兩 streak 都累計。"""
    records = [_rec(p95=45.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = evaluate(records, tolerant_p95_ms=60.0)
    assert rpt["tolerant_streak"] == 14
    assert rpt["observation_streak"] == 14  # p95=45 < 50 → 觀察軌綠
    assert rpt["green_streak"] == 14
    assert rpt["ready_for_labeled_pr"] is True


def test_evaluate_dual_track_upgrade_pass_observation_fail() -> None:
    """ADR v0.4 ACCEPTED 核心場景：真實機器 p95 51-53ms。

    Round 12 修正：原 strict 50ms 已升級為 60ms tolerant 主軌，
    p95=52 → 升級門檻綠（streak=14, ready=True）+ 觀察軌 fail（streak=0）。
    """
    records = [_rec(p95=52.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = evaluate(records, tolerant_p95_ms=60.0)
    assert rpt["tolerant_streak"] == 14, "升級門檻 60ms tolerant → streak=14"
    assert rpt["observation_streak"] == 0, "觀察軌 50ms → p95=52 不達標 streak=0"
    # ADR v0.4 ACCEPTED：60ms 為升級門檻，ready 由升級門檻決定 → True
    assert rpt["ready_for_labeled_pr"] is True, "ADR v0.4 ACCEPTED 後 60ms 即升級門檻"


def test_evaluate_dual_track_both_fail() -> None:
    """p95=70 > 兩軌 → 兩 streak=0 / ready=False。"""
    records = [_rec(p95=70.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = evaluate(records, tolerant_p95_ms=60.0)
    assert rpt["tolerant_streak"] == 0
    assert rpt["observation_streak"] == 0
    assert rpt["green_streak"] == 0
    assert rpt["ready_for_labeled_pr"] is False


def test_evaluate_no_tolerant_uses_default_60ms() -> None:
    """未傳 tolerant_p95_ms → tolerant_streak 同 green_streak（升級門檻預設 60ms）。"""
    records = [_rec(p95=45.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = evaluate(records)
    # ADR v0.4 ACCEPTED：未傳 tolerant_p95_ms 時，tolerant_streak = green_streak（= P95_MAX_MS 控制）
    assert rpt["tolerant_streak"] == 14
    assert rpt["tolerant_p95_ms"] == P95_MAX_MS
    assert rpt["green_streak"] == 14
    # observation_streak（50ms）— p95=45 < 50 → 14
    assert rpt["observation_streak"] == 14


# ========== SD_09 W3 Round 12 P0-R12-1 新增（ADR-SD09-008 v0.4 ACCEPTED 強制驗證） ==========


def test_round12_case_a_p95_55ms_tolerant_pass_observation_fail() -> None:
    """Round 12 P0-R12-1 case A：p95=55ms tolerant_pass=True observation_pass=False。

    驗證 ADR v0.4 ACCEPTED 拍板實作落地：
        - 升級門檻 60ms → p95=55 < 60 → 綠（升級條件達成）
        - 觀察軌 50ms → p95=55 ≥ 50 → fail（觀察指標未達）
        - ready_for_labeled_pr=True（由升級門檻 60ms 決定）
    """
    records = [_rec(p95=55.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = evaluate(records)
    assert rpt["tolerant_streak"] == 14, "升級門檻 60ms tolerant: p95=55<60 → streak=14"
    assert rpt["observation_streak"] == 0, "觀察軌 50ms: p95=55≥50 → streak=0"
    assert rpt["tolerant_p95_ms"] == 60.0
    assert rpt["observation_p95_ms"] == 50.0
    assert rpt["ready_for_labeled_pr"] is True, "ADR v0.3：60ms 升級門檻達標 → ready"


def test_round12_case_b_p95_45ms_dual_track_pass_streak_sync() -> None:
    """Round 12 P0-R12-1 case B：p95=45ms tolerant_pass + observation_pass 雙軌同步累計。

    驗證未來 production hardware 切換情境的向上相容性：
        - 升級門檻 60ms → 綠（streak=14）
        - 觀察軌 50ms → 綠（streak=14）
        - 兩軌 streak 同步累計，提供 PM 後續是否需重新拍板回 50ms 的資料依據
    """
    records = [_rec(p95=45.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = evaluate(records)
    assert rpt["tolerant_streak"] == 14, "升級門檻 60ms: p95=45<60 → streak=14"
    assert rpt["observation_streak"] == 14, "觀察軌 50ms: p95=45<50 → streak=14"
    assert rpt["tolerant_streak"] == rpt["observation_streak"], "雙軌同步累計"
    assert rpt["ready_for_labeled_pr"] is True


def test_round12_case_c_p95_65ms_dual_track_zero_both() -> None:
    """Round 12 P0-R12-1 case C：p95=65ms 雙軌歸零。

    驗證升級門檻 60ms 後仍有真正失敗的場景（防止「升 60ms = 永遠綠」誤判）：
        - 升級門檻 60ms → p95=65 ≥ 60 → fail（streak=0）
        - 觀察軌 50ms → p95=65 ≥ 50 → fail（streak=0）
        - ready_for_labeled_pr=False
    """
    records = [_rec(p95=65.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = evaluate(records)
    assert rpt["tolerant_streak"] == 0, "升級門檻 60ms: p95=65≥60 → streak=0"
    assert rpt["observation_streak"] == 0, "觀察軌 50ms: p95=65≥50 → streak=0"
    assert rpt["ready_for_labeled_pr"] is False


# ========== main CLI 整合 ==========

def test_main_default_60ms_upgrade_threshold(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """main 不傳 --tolerant-p95-ms → JSON 含 tolerant_streak（預設 60ms 升級門檻）。

    SD_09 W3 Round 12 P0-R12-1：ADR v0.4 ACCEPTED 後升級門檻已固定 60ms，
    p95=52 場景 ready_for_labeled_pr=True（升級門檻達標）。
    """
    history = tmp_path / "ac4.jsonl"
    now = _dt.datetime.now(tz=_dt.timezone.utc)
    records = [
        _rec(
            p95=52.0,
            ts=(now - _dt.timedelta(days=13 - i)).isoformat(timespec="seconds"),
        )
        for i in range(14)
    ]
    history.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    rc = main(["--history", str(history), "--json"])
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    # ADR v0.4 ACCEPTED：升級主軌 60ms tolerant → p95=52 達標
    assert report["tolerant_streak"] == 14
    assert report["tolerant_p95_ms"] == P95_MAX_MS  # 60.0
    assert report["observation_streak"] == 0  # p95=52 ≥ 50ms 觀察軌不達
    assert report["observation_p95_ms"] == 50.0
    assert report["ready_for_labeled_pr"] is True
    # exit 0：ready（達標）
    assert rc == 0


def test_main_tolerant_flag_backward_compat(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """向下相容：傳 --tolerant-p95-ms 60 行為與 ADR v0.3 預設一致。"""
    history = tmp_path / "ac4.jsonl"
    now = _dt.datetime.now(tz=_dt.timezone.utc)
    records = [
        _rec(
            p95=52.0,
            ts=(now - _dt.timedelta(days=13 - i)).isoformat(timespec="seconds"),
        )
        for i in range(14)
    ]
    history.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    rc = main(["--history", str(history), "--json", "--tolerant-p95-ms", "60"])
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["tolerant_streak"] == 14
    assert report["tolerant_p95_ms"] == 60.0
    assert report["ready_for_labeled_pr"] is True
    assert rc == 0


# ========== R33 audit P1-R33-1 修復：env-precedence WARN 取證 ==========


def test_resolve_strict_threshold_strict_env_no_warn(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """strict 專用 env 有值 → 直接使用，無 WARN。"""
    from tools.ac4_progress_check import _resolve_strict_p95_threshold
    monkeypatch.setenv("AUTOCLAUDE_STRICT_P95_THRESHOLD_MS", "60")
    monkeypatch.delenv("AUTOCLAUDE_TEST_P95_THRESHOLD_MS", raising=False)
    val = _resolve_strict_p95_threshold()
    assert val == 60.0
    captured = capsys.readouterr()
    assert "WARN" not in captured.err


def test_resolve_strict_threshold_legacy_env_emits_warn(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """strict 未設 + legacy 有值 → stderr WARN 取證（紀律 #6）。"""
    from tools.ac4_progress_check import _resolve_strict_p95_threshold
    monkeypatch.delenv("AUTOCLAUDE_STRICT_P95_THRESHOLD_MS", raising=False)
    monkeypatch.setenv("AUTOCLAUDE_TEST_P95_THRESHOLD_MS", "80")
    val = _resolve_strict_p95_threshold()
    assert val == 80.0
    captured = capsys.readouterr()
    assert "WARN" in captured.err
    assert "AUTOCLAUDE_STRICT_P95_THRESHOLD_MS unset" in captured.err
    assert "R33 audit P1" in captured.err


def test_resolve_strict_threshold_no_env_default_no_warn(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """無任何 env → 預設 60ms，無 WARN（純預設值不算 hijacking）。"""
    from tools.ac4_progress_check import _resolve_strict_p95_threshold
    monkeypatch.delenv("AUTOCLAUDE_STRICT_P95_THRESHOLD_MS", raising=False)
    monkeypatch.delenv("AUTOCLAUDE_TEST_P95_THRESHOLD_MS", raising=False)
    val = _resolve_strict_p95_threshold()
    assert val == 60.0
    captured = capsys.readouterr()
    assert "WARN" not in captured.err
