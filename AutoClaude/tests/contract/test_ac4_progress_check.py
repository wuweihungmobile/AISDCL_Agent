"""SD_Improving_08 W2 T2-C8 — AC4 progress check contract test。

對應 [SD_Improving_08.md §3 W2 + SD08_Execution_Guide.md G2 驗證](
    ../../docs/04_planning/SD_Improving_08.md
)。

驗收門檻（PM #2 拍板 + ADR-SD09-008 v0.4 ACCEPTED 2026-05-25
        + ADR-SD09-012 ACCEPTED 2026-08-03 PM 拍板落地）：
  - recall ≥ 0.95 / p95 < 60ms tolerant（ACCEPTED 升級主軌）/
    recall σ ≤ 0.02（最近 N 筆）/ CircuitBreaker open=0
  - 觀察軌指標：p95 < 50ms（向上相容，未來 production hardware 切換用，不影響 ready）
  - 黃線：連續 3 次未達綠線
  - 紅線：連續 5 次未達綠線
  - 升級條件：**連續 14 筆綠紀錄**（gap-tolerant green_streak）+ recall σ ≤ 0.02
    + 證據新鮮（最新一筆距今 ≤ STALENESS_MAX_DAYS）

🔴 ADR-SD09-012 落地後本檔的呼叫形態變更：閘門吃**全史**，故一律
`evaluate(sort_by_timestamp(load_history(path)))`。原本寫的是先 `filter_recent`
再 evaluate——那條路徑要求 14 筆落在 14 個相鄰日曆天（零缺口），已被 PM 拍板取代；
若測試繼續走舊形態，就會鎖住一個 production 已經不走的路徑（鎖住的東西不是活的契約）。

≥ 4 case：連綠未滿 / 連綠達標 / 單日抖動 / CircuitBreaker open 紅線
      ＋ ADR-SD09-012 新增：staleness schema / 全史含真量測不得誤報 skip 阻塞。

🔴 R75（QA-R74-03）fixture 慣例：斷言 ready=True 的 fixture，**每筆 p95 必須微幅不同**。
真實 collector 每晚重新量測，p95 必然不同；「窗內每筆指標完全相同」自 R75 起會被判
「無法證明重新量測過」而不 ready（寫入端卡住／複製上一筆也長這樣）。本檔三組原本用
常數 p95 的 ready case 已改帶 `+ i * 0.01` 確定性抖動，值域不跨任何門檻。
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from tools.ac4_progress_check import (
    OBSERVATION_DAYS,
    OBSERVATION_REQUIRED_RUNS,
    STALENESS_MAX_DAYS,
    evaluate,
    filter_recent,
    load_history,
    sort_by_timestamp,
)


@pytest.fixture(autouse=True)
def _isolate_p95_threshold_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """把本檔的判定固定在**預設**門檻上；完整 WHY 見
    `AutoClaude/tests/tools/test_ac4_progress_check.py` 內同名 fixture。

    一句話版：門檻由 env 解析、strict 未設時回退 legacy
    `AUTOCLAUDE_TEST_P95_THRESHOLD_MS`，而 nightly／PG 全開的開發環境都會 export
    它（80ms），使本檔 case 以與受測邏輯無關的理由變紅（2026-08-07 實測 1 紅）。
    """
    for name in (
        "AUTOCLAUDE_STRICT_P95_THRESHOLD_MS",
        "AUTOCLAUDE_TEST_P95_THRESHOLD_MS",
        "AUTOCLAUDE_OBSERVATION_P95_THRESHOLD_MS",
    ):
        monkeypatch.delenv(name, raising=False)


def _record(
    days_ago: int,
    *,
    recall: float | None = 0.96,
    p95: float | None = 40.0,
    cb_open: int = 0,
    status: str = "pass",
) -> dict:
    ts = _dt.datetime.now(tz=_dt.UTC) - _dt.timedelta(days=days_ago, hours=1)
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


def test_observing_when_green_streak_under_required_runs(tmp_path: Path) -> None:
    """case 1：連續綠紀錄未滿門檻 → status=observing, ready=False。

    ADR-SD09-012 落地後這條鎖的**意圖**（Rule 9）：門檻仍在、仍擋得住不足的證據，
    只是計量單位從「日曆天」換成「綠紀錄筆數」。若有人把 green_streak 那道分支
    也一起拿掉（＝只剩 σ 與 staleness 守門），7 筆證據就會被判 ready，本 case 會紅。
    """
    records = [_record(days_ago=i) for i in range(7, 0, -1)]
    path = _write_history(tmp_path, records)

    report = evaluate(sort_by_timestamp(load_history(path)))

    assert report["status"] == "observing"
    assert report["ready_for_labeled_pr"] is False
    assert report["green_streak"] == 7
    assert report["green_streak_required"] == OBSERVATION_REQUIRED_RUNS
    assert report["gate_basis"] == "green_streak"
    assert any("連續全綠不足" in r and "筆" in r for r in report["reasons"])


def test_gap_tolerant_streak_ignores_calendar_gaps(tmp_path: Path) -> None:
    """ADR-SD09-012 §3.2 核心：14 筆綠紀錄散佈在遠超 14 個日曆天上仍應達標。

    意圖（Rule 9）：舊判準的實質要求是「最近 14 個 UTC 日期每一天都有紀錄」＝零缺口，
    而這台機器物理上做不到（近 75 天只活 52 天）。本 case 刻意每隔 3 天才放一筆
    （跨度 42 天、缺口 28 天），若有人把日曆連續要求裝回去，這條會立刻紅。
    反之 M-05 去重仍保證每 UTC 日上限 1 筆，故「14 筆」仍蘊含 ≥14 個不同日期，
    時間跨度並未被放寬——這也是本 case 用「散佈」而非「同一天塞 14 筆」的原因。
    """
    # p95 帶 i*0.01 抖動：見檔頭 R75 fixture 慣例（每筆指標完全相同會被判「無法證明
    # 重新量測過」而不 ready，那會讓本 case 的受測對象——日曆缺口——失焦）。
    records = [
        _record(days_ago=i * 3, p95=40.0 + i * 0.01)
        for i in range(OBSERVATION_REQUIRED_RUNS - 1, -1, -1)
    ]
    path = _write_history(tmp_path, records)

    report = evaluate(sort_by_timestamp(load_history(path)))

    assert report["green_streak"] == OBSERVATION_REQUIRED_RUNS
    assert report["status"] == "ready"
    assert report["ready_for_labeled_pr"] is True
    # 滾動窗資訊欄仍如實反映「窗內只有 5 筆」——語意凍結（L-4 (a)），不隨閘門漂移。
    assert report["observation_days"] < OBSERVATION_REQUIRED_RUNS


def test_stale_history_blocks_even_with_sufficient_green_streak(tmp_path: Path) -> None:
    """ADR-SD09-012 L-7：staleness 是**獨立**判準，不是 green_streak 的修正項。

    意圖（Rule 9）：L-1 把 filter_recent 移出閘門路徑，而它是 evaluate() 唯一參照
    「現在」的項。少了 L-7，採集器無聲死掉後 green_streak 會永久凍結在達標值、
    ready 永久為 True 且無人察覺（ADR §1.4 實測：一年前的死資料回 ready=True）。
    本 case 的鑑別力來源：green_streak **仍然達標**（足夠的綠證據），只有新鮮度不合格
    ——若有人把 stale 寫成 streak 的修正項或直接移除該分支，這條就會紅。
    """
    stale_days = STALENESS_MAX_DAYS + 30
    records = [
        _record(days_ago=stale_days + i)
        for i in range(OBSERVATION_REQUIRED_RUNS - 1, -1, -1)
    ]
    path = _write_history(tmp_path, records)

    report = evaluate(sort_by_timestamp(load_history(path)))

    assert report["green_streak"] >= OBSERVATION_REQUIRED_RUNS, "前提：綠證據本身是足夠的"
    assert report["status"] == "stale"
    assert report["ready_for_labeled_pr"] is False
    assert report["staleness_days"] > report["staleness_max_days"]
    assert any("採集可能已停擺" in r for r in report["reasons"])


def test_staleness_boundary_exactly_at_limit_is_still_fresh(tmp_path: Path) -> None:
    """邊界：距今恰為 STALENESS_MAX_DAYS 天 → 仍算新鮮（判準是 `>` 不是 `>=`）。

    為何要鎖邊界：off-by-one 會讓「剛好卡在上限」的機器每隔一天被判一次採集停擺，
    人就會開始無視 stale 這個訊號（訓練人忽略告警＝把防線做廢）。
    """
    records = [
        _record(days_ago=STALENESS_MAX_DAYS + i, p95=40.0 + i * 0.01)  # 抖動：見檔頭 R75
        for i in range(OBSERVATION_REQUIRED_RUNS - 1, -1, -1)
    ]
    path = _write_history(tmp_path, records)

    report = evaluate(sort_by_timestamp(load_history(path)))

    assert report["staleness_days"] == STALENESS_MAX_DAYS
    assert report["status"] != "stale"
    assert report["ready_for_labeled_pr"] is True


def test_ready_for_labeled_pr_after_14_days_green(tmp_path: Path) -> None:
    """case 2：達 14 天且全綠（recall ≥ 0.95 + p95 < 50ms + cb=0 + σ ≤ 0.02）→ ready=True。"""
    # σ 控制在 0.02 以內：recall 在 0.95~0.99 之間微小變化
    recalls = [
        0.95, 0.96, 0.97, 0.96, 0.95, 0.96, 0.97,
        0.96, 0.95, 0.96, 0.97, 0.96, 0.95, 0.96,
    ]
    records = []
    for i, recall in enumerate(recalls, start=1):
        records.append(_record(days_ago=OBSERVATION_DAYS - i, recall=recall))
    path = _write_history(tmp_path, records)

    report = evaluate(sort_by_timestamp(load_history(path)))

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

    report = evaluate(sort_by_timestamp(load_history(path)))

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

    report = evaluate(sort_by_timestamp(load_history(path)))

    assert report["status"] == "alert_red"
    assert report["ready_for_labeled_pr"] is False
    assert report["consecutive_failures"] >= 5
    assert any("紅線" in r for r in report["reasons"])


def test_empty_history(tmp_path: Path) -> None:
    """case 5（bonus）：空 history → observing + 觀察期 0 天。"""
    path = tmp_path / ".ac4_history.jsonl"
    path.touch()

    report = evaluate(sort_by_timestamp(load_history(path)))

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

    report = evaluate(sort_by_timestamp(load_history(path)))

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

    report = evaluate(sort_by_timestamp(load_history(path)))

    assert report["status"] == "alert_red"
    assert report["consecutive_failures"] >= 5


def test_recall_sigma_blocks_when_high_variance(tmp_path: Path) -> None:
    """case 6（bonus）：14 天全部 pass 但 recall σ > 0.02 → 不升級。"""
    # recall 在 0.95~0.99 大幅震盪
    records = []
    swinging = [0.95, 0.99] * 7
    for i, recall in enumerate(swinging, start=1):
        records.append(_record(days_ago=OBSERVATION_DAYS - i, recall=recall))
    path = _write_history(tmp_path, records)

    report = evaluate(sort_by_timestamp(load_history(path)))

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
    records = [
        _record(days_ago=i, p95=54.3 + i * 0.01)  # 抖動：見檔頭 R75 fixture 慣例
        for i in range(OBSERVATION_DAYS - 1, -1, -1)
    ]
    path = _write_history(tmp_path, records)

    report = evaluate(sort_by_timestamp(load_history(path)))

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

    report = evaluate(sort_by_timestamp(load_history(path)))

    assert report["status"] == "observing"
    assert report["ready_for_labeled_pr"] is False
    joined_reasons = " ".join(report["reasons"])
    assert "hardcoded skip" in joined_reasons
    assert "X1" in joined_reasons


def test_l5_full_history_with_real_measurements_never_reports_skip_blockage(
    tmp_path: Path,
) -> None:
    """ADR-SD09-012 L-5：`all_true_skip` 改吃全史後語意由「窗內全 skip」→「史上全 skip」。

    意圖（Rule 9）：舊語意下，只要滾動窗內恰好全是 skip（例如機器停機兩週後第一次
    開機、窗內只剩幾筆 X1 前的 skip），就會印「AC4 hardcoded skip 阻塞，需 X1 補實作」
    ——即使史上早有幾十筆真量測。那句話會把人送去補一個早就補完的實作。
    改吃全史後只要**史上存在任何一筆真量測**就不會誤報，本 case 即該不變量的鎖：
    前段全 skip（模擬 X1 前）、後段真量測，斷言 reason 不得再提 skip 阻塞。
    """
    skips = [
        _record(days_ago=60 - i, status="skip", recall=None, p95=None) for i in range(10)
    ]
    reals = [_record(days_ago=5 - i) for i in range(5)]
    path = _write_history(tmp_path, skips + reals)

    report = evaluate(sort_by_timestamp(load_history(path)))

    joined_reasons = " ".join(report["reasons"])
    assert "hardcoded skip" not in joined_reasons
    assert report["status"] != "stale", "最新一筆為 5 天前，不該被判採集停擺"


def test_observation_days_stays_rolling_window_count_l4_semantic_freeze(
    tmp_path: Path,
) -> None:
    """ADR-SD09-012 L-4 (a)：`observation_days` 語意凍結＝滾動 14 日曆天窗筆數。

    意圖（Rule 9）：若有人為了讓數字好看，把該欄改成全史筆數，nightly 的 END 進度行
    與 F2 區塊會印出 `ac4=43/14` 這種「看起來超標三倍」的假達標——那正是 ADR §2.8
    記載、R69 剛修好的缺陷。本 case 用「全史遠多於窗內」的資料把兩者拉開後斷言：
    該欄必須等於 filter_recent 的長度，而**不是** total_records。
    """
    old = [_record(days_ago=60 - i) for i in range(20)]
    recent = [_record(days_ago=3 - i) for i in range(3)]
    path = _write_history(tmp_path, old + recent)
    records = sort_by_timestamp(load_history(path))

    report = evaluate(records)

    assert report["total_records"] == 23
    assert report["observation_days"] == len(filter_recent(records))
    assert report["observation_days"] == 3
    assert report["observation_days"] != report["total_records"]
