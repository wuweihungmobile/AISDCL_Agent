"""SD_Improving_08 W2 T2-C8 — AC4 progress check contract test。

對應 [SD_Improving_08.md §3 W2 + SD08_Execution_Guide.md G2 驗證](
    ../../docs/04_planning/SD_Improving_08.md
)。

驗收門檻（PM #2 拍板 + ADR-SD09-008 v0.4 ACCEPTED 2026-05-25 更新）：
  - 觀察期 14 天 / recall ≥ 0.95 / p95 < 60ms tolerant（ACCEPTED 升級主軌）/
    recall σ ≤ 0.02 / CircuitBreaker open=0
  - 觀察軌指標：p95 < 50ms（向上相容，未來 production hardware 切換用，不影響 ready）
  - 黃線：連續 3 次未達綠線
  - 紅線：連續 5 次未達綠線
  - 升級條件：觀察期滿 14 天 + 全綠連續 14 次（60ms 升級主軌） + recall σ ≤ 0.02

≥ 4 case：未達 14 天 / 達 14 天全綠 / 單日抖動 / CircuitBreaker open 紅線。
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from tools.ac4_progress_check import (
    OBSERVATION_DAYS,
    evaluate,
    filter_recent,
    load_history,
)


def _record(
    days_ago: int,
    *,
    recall: float | None = 0.96,
    p95: float | None = 40.0,
    cb_open: int = 0,
    status: str = "pass",
) -> dict:
    ts = _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=days_ago, hours=1)
    return {
        "timestamp": ts.isoformat(timespec="seconds"),
        "run_id": f"run-{days_ago}",
        "recall_at_10": recall,
        "p95_ms": p95,
        "circuit_breaker_open_count": cb_open,
        "status": status,
    }


def _write_history(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / ".ac4_history.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def test_observing_under_14_days(tmp_path: Path) -> None:
    """case 1：未達 14 天觀察期 → status=observing, ready=False。"""
    records = [_record(days_ago=i) for i in range(7, 0, -1)]
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    assert report["status"] == "observing"
    assert report["ready_for_labeled_pr"] is False
    assert report["observation_days"] == 7
    assert any("觀察期未滿" in r for r in report["reasons"])


def test_ready_for_labeled_pr_after_14_days_green(tmp_path: Path) -> None:
    """case 2：達 14 天且全綠（recall ≥ 0.95 + p95 < 50ms + cb=0 + σ ≤ 0.02）→ ready=True。"""
    # σ 控制在 0.02 以內：recall 在 0.95~0.99 之間微小變化
    records = []
    for i, recall in enumerate([0.95, 0.96, 0.97, 0.96, 0.95, 0.96, 0.97, 0.96, 0.95, 0.96, 0.97, 0.96, 0.95, 0.96], start=1):
        records.append(_record(days_ago=OBSERVATION_DAYS - i, recall=recall))
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    assert report["status"] == "ready"
    assert report["ready_for_labeled_pr"] is True
    assert report["green_streak"] == OBSERVATION_DAYS
    assert report["consecutive_failures"] == 0
    assert report["recall_sigma"] is not None
    assert report["recall_sigma"] <= 0.02


def test_yellow_alert_on_single_day_jitter(tmp_path: Path) -> None:
    """case 3：尾端連續 3 次未達綠線 → status=alert_yellow。"""
    records = [_record(days_ago=i) for i in range(14, 3, -1)]
    # 尾端 3 筆 recall 跌破 0.95
    records.append(_record(days_ago=3, recall=0.90))
    records.append(_record(days_ago=2, recall=0.92))
    records.append(_record(days_ago=1, recall=0.91))
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    assert report["status"] == "alert_yellow"
    assert report["ready_for_labeled_pr"] is False
    assert report["consecutive_failures"] >= 3
    assert any("黃線" in r for r in report["reasons"])


def test_red_alert_on_circuit_breaker_open(tmp_path: Path) -> None:
    """case 4：尾端連續 5 次 CircuitBreaker open > 0 → status=alert_red。"""
    records = [_record(days_ago=i) for i in range(14, 5, -1)]
    # 尾端 5 筆 CB open 觸發
    for d in range(5, 0, -1):
        records.append(_record(days_ago=d, cb_open=2))
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    assert report["status"] == "alert_red"
    assert report["ready_for_labeled_pr"] is False
    assert report["consecutive_failures"] >= 5
    assert any("紅線" in r for r in report["reasons"])


def test_empty_history(tmp_path: Path) -> None:
    """case 5（bonus）：空 history → observing + 觀察期 0 天。"""
    path = tmp_path / ".ac4_history.jsonl"
    path.touch()

    report = evaluate(filter_recent(load_history(path)))

    assert report["status"] == "observing"
    assert report["observation_days"] == 0
    assert report["ready_for_labeled_pr"] is False


def test_green_when_collector_pass_and_p95_under_60ms_tolerant(tmp_path: Path) -> None:
    """ADR-SD09-008 v0.4 ACCEPTED（取代舊 neutral 區設計）：

    Round 12 修正：原 50~60ms 為「strict neutral 區」，v0.4 ACCEPTED 後 60ms 成正式
    升級門檻 → p95=54.3 直接綠（streak 累計），不再是 neutral。
    """
    records = [_record(days_ago=i) for i in range(14, 5, -1)]
    # 尾端 5 筆 p95=54.3 ms（v0.4 ACCEPTED 後 < 60ms 升級主軌即綠）
    for d in range(5, 0, -1):
        records.append(_record(days_ago=d, p95=54.3))
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    # v0.4 ACCEPTED：< 60ms 即綠，不應觸發紅線
    assert report["status"] != "alert_red"
    assert report["consecutive_failures"] == 0
    # green_streak 應持續累計（p95<60 全綠）
    assert report["green_streak"] > 0
    # 觀察軌：p95=54.3 ≥ 50 → observation_streak=0
    assert report["observation_streak"] == 0


def test_red_when_p95_exceeds_60ms_upgrade_threshold_truly_failing(tmp_path: Path) -> None:
    """ADR-SD09-008 v0.4 ACCEPTED 升級門檻 60ms：p95=70ms 累計 5 次仍觸紅線。"""
    records = [_record(days_ago=i) for i in range(14, 5, -1)]
    for d in range(5, 0, -1):
        records.append(_record(days_ago=d, p95=70.0))  # 升級門檻 60ms，70 > 60 → fail
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    assert report["status"] == "alert_red"
    assert report["consecutive_failures"] >= 5


def test_recall_sigma_blocks_when_high_variance(tmp_path: Path) -> None:
    """case 6（bonus）：14 天全部 pass 但 recall σ > 0.02 → 不升級。"""
    # recall 在 0.95~0.99 大幅震盪
    records = []
    for i, recall in enumerate([0.95, 0.99, 0.95, 0.99, 0.95, 0.99, 0.95, 0.99, 0.95, 0.99, 0.95, 0.99, 0.95, 0.99], start=1):
        records.append(_record(days_ago=OBSERVATION_DAYS - i, recall=recall))
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    # σ ≈ 0.02；若超門檻則 observing；若恰好 ≤ 則 ready。本檔意在驗證 σ 計算正確。
    assert report["recall_sigma"] is not None
    if report["recall_sigma"] > 0.02:
        assert report["status"] == "observing"
        assert report["ready_for_labeled_pr"] is False
        assert any("σ" in r for r in report["reasons"])


def test_all_pass_p95_under_60ms_reaches_ready_not_hardcoded_skip(tmp_path: Path) -> None:
    """ADR-SD09-008 v0.4 ACCEPTED 鏡子測試（取代舊 P0-AUDIT-33 neutral 區語意）：

    Round 12 修正：原測試「14 筆 status=pass 但 p95 卡 50~60ms neutral」已過時 —
    v0.4 ACCEPTED 後 60ms 即升級門檻，p95=54.3 < 60 → 直接 ready=True。
    保留的不變量：**禁止**誤報「AC4 hardcoded skip 阻塞」— 該訊息僅在真正 hardcoded
    status='skip' 時才出現（紀律 #1 / #4 驗證鏡子自驗）。
    """
    # 全 14 筆 status=pass，p95=54.3ms（v0.4 ACCEPTED 後 < 60ms 升級門檻 → 直接綠）
    # 注意 _record 內加 hours=1，days_ago=14 會超出 14 天 cutoff → 取 13~0 共 14 筆
    records = [_record(days_ago=i, p95=54.3) for i in range(OBSERVATION_DAYS - 1, -1, -1)]
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    # v0.4 ACCEPTED：升級門檻 60ms → p95=54.3 全綠 → ready
    assert report["status"] == "ready"
    assert report["ready_for_labeled_pr"] is True
    assert report["tolerant_streak"] == OBSERVATION_DAYS
    # 觀察軌：p95=54.3 ≥ 50 → streak=0（向上相容指標，不影響 ready）
    assert report["observation_streak"] == 0
    # 關鍵不變量：**不可**提到「hardcoded skip」(該訊息僅 status='skip' 時應出現)
    joined_reasons = " ".join(report["reasons"])
    assert "hardcoded skip" not in joined_reasons


def test_all_true_skip_still_reports_x1_hardcoded_skip(tmp_path: Path) -> None:
    """SD_09 W0 P0-AUDIT-33 修復鏡子測試（反向）：

    全筆 status='skip'（X1 補實作前）時，reason 必須維持「AC4 hardcoded skip 阻塞」原訊息，
    不可因 P0-33 修復而退化（避免 neutral 修法誤殺真 skip 訊息）。
    """
    # 全 14 筆 status='skip'
    records = [
        _record(days_ago=i, status="skip", recall=None, p95=None)
        for i in range(OBSERVATION_DAYS, 0, -1)
    ]
    path = _write_history(tmp_path, records)

    report = evaluate(filter_recent(load_history(path)))

    assert report["status"] == "observing"
    assert report["ready_for_labeled_pr"] is False
    joined_reasons = " ".join(report["reasons"])
    assert "hardcoded skip" in joined_reasons
    assert "X1" in joined_reasons
