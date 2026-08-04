"""tests/tools/test_ac4_progress_check.py — SD_09 W3 Round 3 audit P0-1 補建。

對應 tools/ac4_progress_check.py（觀察期 #2 升級判定工具）。
紀律 #4「驗證鏡子自身要被驗證」— 雙軌設計必須有單元測試覆蓋。

對應修復來源：
- SD_09 W3 Round 3 audit P0-1（tolerant p95 雙軌設計）
- ADR-SD09-008 v0.1 PROPOSED（雙軌設計理由）
- SD_09 W3 Round 6 audit P0-AUDIT-R5-B（time-flaky main test — 改相對 now 避免跨日 cutoff race）
- SD_09 W3 Round 12 P0-R12-1（ADR-SD09-008 v0.4 ACCEPTED 拍板實作落地：升 60ms tolerant 為主軌）
- ADR-SD09-012 ACCEPTED（PM 2026-08-03 拍板落地：gap-tolerant green_streak + L-7 staleness）

🔴 ADR-SD09-012 落地後本檔全部 evaluate 呼叫改走 `_eval()` 注入時鐘（見該函式註解）：
新增的 L-7 staleness 判準會拿「最新一筆 vs 現在」比對，而本檔的 fixture 用的是寫死的
2026-05 日期——不注入時鐘的話，這些 case 會在 2026-06-25 之後開始集體判 stale 而變紅。
那不是測到了缺陷，是測試自己踩到日曆（同 Round 6 P0-AUDIT-R5-B 的 time-flaky 形態）。

🔴 R75（QA-R74-03）fixture 慣例變更：**同一組 fixture 裡每筆 p95 必須微幅不同**。
真實 collector 每晚重新量測，p95 必然不同（實測真實歷史 44 筆全不相同）；而「窗內
每筆指標完全相同」自 R75 起是一個被明確攔下的狀態（＝寫入端卡住／複製上一筆，無法
證明重新量測過）。本檔原有 8 組 fixture 寫 14 筆一模一樣的 p95 並斷言 ready=True
——那正好在複製本輪要修的盲點，故一律改帶 `+ d * 0.01` 這種確定性抖動（值域刻意不
跨任何門檻，各 case 原本的受測對象不變）。要測「零變異」本身的 case 反過來刻意不加
抖動，見檔尾 R75 段。
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

import pytest

from tools.ac4_progress_check import (
    OBSERVATION_REQUIRED_RUNS,
    P95_MAX_MS,
    STALENESS_MAX_DAYS,
    _is_green,
    _is_green_observation,
    _is_green_tolerant,
    evaluate,
    latest_timestamp,
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


def _eval(records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    """evaluate()，`now` 預設鎖在「最新一筆的隔天」。

    為何不用真實時鐘：L-7 的 staleness 判準對時鐘敏感，而本檔 fixture 是寫死日期。
    把 now 綁到資料本身，這些 case 就永久不受日曆影響；要測 staleness 的 case 自己
    顯式傳 now（那才是它們的受測對象）。
    """
    if "now" not in kwargs:
        latest = latest_timestamp(records)
        kwargs["now"] = (
            latest + _dt.timedelta(days=1)
            if latest is not None
            else _dt.datetime.now(tz=_dt.UTC)
        )
    return evaluate(records, **kwargs)


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
    # p95 帶 d*0.01 抖動（45.11~45.24，仍 < 50 兩軌皆綠）——見檔頭 R75 fixture 慣例。
    records = [
        _rec(p95=45.0 + d * 0.01, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)
    ]
    rpt = _eval(records, tolerant_p95_ms=60.0)
    assert rpt["tolerant_streak"] == 14
    assert rpt["observation_streak"] == 14  # p95=45 < 50 → 觀察軌綠
    assert rpt["green_streak"] == 14
    assert rpt["ready_for_labeled_pr"] is True


def test_evaluate_dual_track_upgrade_pass_observation_fail() -> None:
    """ADR v0.4 ACCEPTED 核心場景：真實機器 p95 51-53ms。

    Round 12 修正：原 strict 50ms 已升級為 60ms tolerant 主軌，
    p95=52 → 升級門檻綠（streak=14, ready=True）+ 觀察軌 fail（streak=0）。
    """
    records = [
        _rec(p95=52.0 + d * 0.01, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)
    ]
    rpt = _eval(records, tolerant_p95_ms=60.0)
    assert rpt["tolerant_streak"] == 14, "升級門檻 60ms tolerant → streak=14"
    assert rpt["observation_streak"] == 0, "觀察軌 50ms → p95=52 不達標 streak=0"
    # ADR v0.4 ACCEPTED：60ms 為升級門檻，ready 由升級門檻決定 → True
    assert rpt["ready_for_labeled_pr"] is True, "ADR v0.4 ACCEPTED 後 60ms 即升級門檻"


def test_evaluate_dual_track_both_fail() -> None:
    """p95=70 > 兩軌 → 兩 streak=0 / ready=False。"""
    records = [_rec(p95=70.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = _eval(records, tolerant_p95_ms=60.0)
    assert rpt["tolerant_streak"] == 0
    assert rpt["observation_streak"] == 0
    assert rpt["green_streak"] == 0
    assert rpt["ready_for_labeled_pr"] is False


def test_evaluate_no_tolerant_uses_default_60ms() -> None:
    """未傳 tolerant_p95_ms → tolerant_streak 同 green_streak（升級門檻預設 60ms）。"""
    records = [_rec(p95=45.0, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)]
    rpt = _eval(records)
    # ADR v0.4 ACCEPTED：未傳 tolerant_p95_ms 時
    # tolerant_streak = green_streak（由 P95_MAX_MS 控制）
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
    records = [
        _rec(p95=55.0 + d * 0.01, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)
    ]
    rpt = _eval(records)
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
    records = [
        _rec(p95=45.0 + d * 0.01, ts=f"2026-05-{d:02d}T00:00:00+00:00") for d in range(11, 25)
    ]
    rpt = _eval(records)
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
    rpt = _eval(records)
    assert rpt["tolerant_streak"] == 0, "升級門檻 60ms: p95=65≥60 → streak=0"
    assert rpt["observation_streak"] == 0, "觀察軌 50ms: p95=65≥50 → streak=0"
    assert rpt["ready_for_labeled_pr"] is False


# ========== main CLI 整合 ==========

def test_main_default_60ms_upgrade_threshold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main 不傳 --tolerant-p95-ms → JSON 含 tolerant_streak（預設 60ms 升級門檻）。

    SD_09 W3 Round 12 P0-R12-1：ADR v0.4 ACCEPTED 後升級門檻已固定 60ms，
    p95=52 場景 ready_for_labeled_pr=True（升級門檻達標）。
    """
    history = tmp_path / "ac4.jsonl"
    now = _dt.datetime.now(tz=_dt.UTC)
    records = [
        _rec(
            p95=52.0 + i * 0.01,  # 見檔頭 R75 fixture 慣例（52.00~52.13，仍 <60 ≥50）
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


def test_main_tolerant_flag_backward_compat(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """向下相容：傳 --tolerant-p95-ms 60 行為與 ADR v0.3 預設一致。"""
    history = tmp_path / "ac4.jsonl"
    now = _dt.datetime.now(tz=_dt.UTC)
    records = [
        _rec(
            p95=52.0 + i * 0.01,  # 見檔頭 R75 fixture 慣例（52.00~52.13，仍 <60 ≥50）
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


# ========== ADR-SD09-012 L-7 staleness 三 case（新鮮／N 邊界／超過 N） ==========
#
# 為何這三 case 是本次落地的必要條件而非加分項（ADR §7.4 DoD 1b）：
# L-1 把 filter_recent() 移出閘門路徑，而它是 evaluate() 內**唯一**參照「現在」的項。
# 移走後達標退化成純檔案內容函式——採集器無聲死掉時 green_streak 永久凍結、ready
# 永久為 True，且沒有任何東西會察覺（ADR §1.4 實測：一年前的死資料回 ready=True）。
# 三 case 都刻意讓 green_streak **達標**，把鑑別力集中在「新鮮度」這一個變數上：
# 若有人把 stale 分支拿掉，第三個 case 立刻紅；若寫成 `>=` 而非 `>`，第二個立刻紅。

_STALE_BASE = _dt.datetime(2026, 5, 24, tzinfo=_dt.UTC)


def _fourteen_green() -> list[dict]:
    """14 筆全綠，最新一筆 = _STALE_BASE。

    p95 帶 d*0.01 抖動（45.00~45.13，兩軌皆綠）：見檔頭 R75 fixture 慣例——
    14 筆完全相同的 p95 自 R75 起會被判「無法證明重新量測過」而不 ready，
    那會讓下方 staleness 三 case 失去焦點（它們的受測對象是新鮮度，不是變異）。
    """
    return [
        _rec(p95=45.0 + d * 0.01, ts=(_STALE_BASE - _dt.timedelta(days=d)).isoformat())
        for d in range(OBSERVATION_REQUIRED_RUNS - 1, -1, -1)
    ]


def test_staleness_fresh_history_is_ready() -> None:
    """case 1（新鮮）：最新一筆為昨日 → 不 stale、ready=True。"""
    rpt = evaluate(_fourteen_green(), now=_STALE_BASE + _dt.timedelta(days=1))
    assert rpt["staleness_days"] == 1
    assert rpt["status"] == "ready"
    assert rpt["ready_for_labeled_pr"] is True


def test_staleness_exactly_at_limit_is_still_fresh() -> None:
    """case 2（邊界）：距今恰為上限 → 仍算新鮮（判準是 `>` 不是 `>=`）。"""
    rpt = evaluate(
        _fourteen_green(), now=_STALE_BASE + _dt.timedelta(days=STALENESS_MAX_DAYS)
    )
    assert rpt["staleness_days"] == STALENESS_MAX_DAYS
    assert rpt["status"] == "ready"
    assert rpt["ready_for_labeled_pr"] is True


def test_staleness_beyond_limit_blocks_despite_sufficient_green_streak() -> None:
    """case 3（超過 N）：綠證據**仍然達標**，但採集已停擺 → stale、ready=False。"""
    rpt = evaluate(
        _fourteen_green(), now=_STALE_BASE + _dt.timedelta(days=STALENESS_MAX_DAYS + 1)
    )
    assert rpt["green_streak"] >= OBSERVATION_REQUIRED_RUNS, "前提：綠證據本身是足夠的"
    assert rpt["status"] == "stale"
    assert rpt["ready_for_labeled_pr"] is False
    assert any("採集可能已停擺" in r for r in rpt["reasons"])


def test_staleness_unparseable_timestamps_fail_closed() -> None:
    """全部 timestamp 無法解析 → fail-closed 判 stale，不得因「量不出新鮮度」而放行。

    意圖（Rule 9）：`_parse_ts` 回 None 的紀錄會被 filter_recent 丟掉，若 staleness 也
    比照「丟掉就算了」，寫入端一旦壞掉（時間格式漂移）就會變成無限期假綠——與採集器
    死掉的後果完全相同，只是更難看出來。
    """
    records = [_rec(p95=45.0, ts="not-a-timestamp") for _ in range(OBSERVATION_REQUIRED_RUNS)]
    rpt = evaluate(records, now=_STALE_BASE)
    assert rpt["staleness_days"] is None
    assert rpt["status"] == "stale"
    assert rpt["ready_for_labeled_pr"] is False


# ══════════════════════════════════════════════════════════════════════════════
# 🔴 R75（SD 複審 blocking）：staleness 要量「有沒有新**量測**」，不是「有沒有新**紀錄**」
# ══════════════════════════════════════════════════════════════════════════════
# 為何這組 case 是閘門存活的必要條件（Rule 9）：
#   `ready_for_labeled_pr` 是**拿來擋 labeled PR 的閘門**（PG 真 e2e 升級的入口）。
#   閘門凍在 ready 就不再是閘門而是裝飾品，而凍結**不需要任何人犯錯**：PG／Docker
#   不可用時 nightly 每晚照寫一筆帶當日 timestamp 的 `status='skip'`（run_local_nightly
#   為此另建 `.docker_skip_streak` 計數器，證明這是常態不是邊角），而 skip 對
#   green_streak 是中性、對舊 staleness 又算「有新紀錄」⇒ streak 凍在 14、staleness
#   恆為 1、ready 永久為真。方向在危險側：閘門是**開著**的。
#   L-7 立這條判準時逐字要防的就是這個狀態，但它只堵住「沒有新列」那一半。
_SKIP_STATUS = "skip"


def _skip_rec(ts: str) -> dict:
    """採集器活著、量測沒發生的那種紀錄（collector：pg-e2e 整體未跑 → status='skip'）。

    刻意複製 collector 真實寫入形態（recall/p95 皆 None），不用 _rec 帶假指標值
    ——假指標會讓這組 case 誤過 `_is_measurement` 以外的路徑，測到的就不是本缺陷。
    """
    return {
        "timestamp": ts,
        "run_id": "test",
        "recall_at_10": None,
        "p95_ms": None,
        "circuit_breaker_open_count": 0,
        "status": _SKIP_STATUS,
    }


def test_frozen_ready_when_only_skips_arrive_after_green_streak() -> None:
    """14 綠 ＋ 其後 120 晚全 skip → **不得** ready（本缺陷的正射）。

    鑑別力來源：green_streak 仍然是 14/14（達標），採集器也仍然每晚有新列
    ——唯一變的變數是「最後一筆真量測」有多舊。修復前這組資料回 status=ready。
    """
    records = _fourteen_green()
    days_of_skip = 120
    records += [
        _skip_rec((_STALE_BASE + _dt.timedelta(days=d)).isoformat())
        for d in range(1, days_of_skip + 1)
    ]
    now = _STALE_BASE + _dt.timedelta(days=days_of_skip + 1)

    rpt = evaluate(records, now=now)

    assert rpt["green_streak"] == OBSERVATION_REQUIRED_RUNS, "前提：綠證據本身仍達標"
    assert rpt["record_staleness_days"] == 1, "前提：採集器活著（昨晚才寫過一筆）"
    assert rpt["staleness_days"] == days_of_skip + 1 > STALENESS_MAX_DAYS
    assert rpt["status"] == "stale"
    assert rpt["ready_for_labeled_pr"] is False
    assert any("量測未發生" in r for r in rpt["reasons"]), rpt["reasons"]


def test_skip_gap_shorter_than_limit_keeps_ready() -> None:
    """反向（不得過度殺傷）：量測空窗仍在 N 天內 → 維持 ready。

    意圖：N 的職責只有「區分放長假與量測死掉」。若把任何 skip 都當作破壞新鮮度，
    這台機器（近 75 天只活 52 天）會永遠達不到——那是 ADR-SD09-012 剛拆掉的病。
    """
    records = _fourteen_green()
    records += [
        _skip_rec((_STALE_BASE + _dt.timedelta(days=d)).isoformat())
        for d in range(1, STALENESS_MAX_DAYS)
    ]
    now = _STALE_BASE + _dt.timedelta(days=STALENESS_MAX_DAYS)

    rpt = evaluate(records, now=now)

    assert rpt["staleness_days"] == STALENESS_MAX_DAYS, "邊界：恰在上限（判準是 > 不是 >=）"
    assert rpt["status"] == "ready"
    assert rpt["ready_for_labeled_pr"] is True


def test_recent_real_measurement_after_skip_gap_restores_ready() -> None:
    """14 綠 ＋ 一長段 skip ＋ 近期一筆真量測 → ready（量測恢復就該解鎖）。

    意圖：修法不得變成「一旦出現長 skip 段就永久鎖死」——那會把「修好 Docker 後
    重新開始量測」這條正常復原路徑也堵掉，人只能靠改判準來解鎖（＝砸溫度計）。
    """
    records = _fourteen_green()
    records += [
        _skip_rec((_STALE_BASE + _dt.timedelta(days=d)).isoformat())
        for d in range(1, 61)
    ]
    records.append(_rec(p95=45.0, ts=(_STALE_BASE + _dt.timedelta(days=61)).isoformat()))
    now = _STALE_BASE + _dt.timedelta(days=62)

    rpt = evaluate(records, now=now)

    assert rpt["staleness_days"] == 1
    assert rpt["green_streak"] == OBSERVATION_REQUIRED_RUNS + 1
    assert rpt["status"] == "ready"
    assert rpt["ready_for_labeled_pr"] is True


def test_history_without_any_real_measurement_is_not_punished_as_stale() -> None:
    """史上零真量測（全 skip）→ 維持既有「X1 hardcoded skip 阻塞」語意，不判 stale。

    意圖：全史豁免的存在理由是「還沒有任何真量測就不該罰」。R75 只把「曾經有真量測、
    後來全 skip」從豁免裡拿掉，**不得**順手把冷啟動那格也改判 stale——那會讓一台
    還沒開始量測的機器收到「採集已停擺」這個誤導訊息（送人去修一個沒壞的東西）。
    兩者現在互斥：豁免要求史上零量測、stale 要求史上至少一筆量測。
    """
    records = [
        _skip_rec((_STALE_BASE - _dt.timedelta(days=d)).isoformat()) for d in range(20, 0, -1)
    ]

    rpt = evaluate(records, now=_STALE_BASE + _dt.timedelta(days=200))

    assert rpt["measured_records"] == 0
    assert rpt["staleness_days"] is None
    assert rpt["status"] == "observing"
    assert rpt["ready_for_labeled_pr"] is False
    assert any("hardcoded skip" in r for r in rpt["reasons"])


def test_dead_collector_and_skip_only_collector_give_different_remediation() -> None:
    """兩種停擺形態都要 stale，但**理由必須可區分**（修法不同）。

    意圖：採集器死掉 → 修排程／載具；採集器活著但只寫 skip → 修 PG／Docker。
    兩者印同一句話會把人送去查一個沒壞的東西，而這種誤導在夜間排程情境下代價很高
    （下一次有人看 log 可能是好幾天後）。
    """
    dead = evaluate(
        _fourteen_green(), now=_STALE_BASE + _dt.timedelta(days=STALENESS_MAX_DAYS + 1)
    )

    alive = _fourteen_green()
    alive += [
        _skip_rec((_STALE_BASE + _dt.timedelta(days=d)).isoformat())
        for d in range(1, STALENESS_MAX_DAYS + 2)
    ]
    skip_only = evaluate(alive, now=_STALE_BASE + _dt.timedelta(days=STALENESS_MAX_DAYS + 2))

    assert dead["status"] == skip_only["status"] == "stale"
    assert any("採集可能已停擺" in r for r in dead["reasons"]), dead["reasons"]
    assert not any("採集可能已停擺" in r for r in skip_only["reasons"]), skip_only["reasons"]
    assert dead["reasons"] != skip_only["reasons"]
    # 資訊欄要能讓人一眼分辨是哪一種：採集器活著時 record 很新、量測很舊。
    assert dead["record_staleness_days"] == dead["staleness_days"]
    assert skip_only["record_staleness_days"] < skip_only["staleness_days"]


# ══════════════════════════════════════════════════════════════════════════════
# 🔴 R75 / QA-R74-03：σ 這把尺量到的東西有沒有在動，必須是可見的量測值
# ══════════════════════════════════════════════════════════════════════════════
# QA 對真實歷史實測：recall_at_10 distinct=1（44 筆全為 0.999，跨 75 天）、status
# distinct=1、cb distinct=1，只有 p95 在動 ⇒ `recall ≥ 0.95` 與 `recall σ ≤ 0.02`
# 兩條門檻在這份資料上不可能不通過，而 green_streak（R74 明定的唯一閘門）一半的輸入
# 就是 recall。處置刻意分兩層（見 ac4_progress_check.evaluate 內同編號註解）：
#   ① σ 讀 0 在確定性指標上是**正確讀數**，不改判準內容，改成把「這次是沒變、不是
#      驗過了」印出來（caveats）——不印出來就會變成 QA 點名的「reasons=[] 讓人以為
#      毫無保留就達標」。
#   ② 真正的缺口是「分不出穩定與根本沒重新量測」⇒ 新增一條**收緊**的必要條件。


def test_zero_variance_history_must_not_certify_ready() -> None:
    """14 筆全綠但每筆指標**完全相同** → 不得 ready（新增的收緊條件）。

    意圖（Rule 9）：寫入端卡住／每晚複製上一筆值，長出來的歷史就是這個樣子——
    green_streak 達標、σ=0.0「通過」反漂移、staleness 也新鮮，三道判準全綠而
    系統其實一次都沒重新量測過。這與 skip 凍結是同一族的 liveness 假綠。
    刻意**不加**抖動：本 case 的受測對象就是零變異本身。
    """
    records = [
        _rec(p95=45.0, recall=0.999, ts=(_STALE_BASE - _dt.timedelta(days=d)).isoformat())
        for d in range(OBSERVATION_REQUIRED_RUNS - 1, -1, -1)
    ]

    rpt = evaluate(records, now=_STALE_BASE + _dt.timedelta(days=1))

    assert rpt["green_streak"] == OBSERVATION_REQUIRED_RUNS, "前提：綠證據筆數本身達標"
    assert rpt["recall_sigma"] == 0.0, "前提：σ 這條門檻是「通過」的"
    assert rpt["metric_variance_observed"] is False
    assert rpt["recall_distinct_values"] == 1
    assert rpt["p95_distinct_values"] == 1
    assert rpt["ready_for_labeled_pr"] is False
    assert any("完全相同" in r for r in rpt["reasons"]), rpt["reasons"]


def test_constant_recall_with_moving_p95_is_ready_but_flags_sigma_as_blind() -> None:
    """真實歷史的形態（recall 常數、p95 每晚不同）→ 仍 ready，但必須攤開兩項保留。

    意圖（Rule 9）：這是本機真實資料的形狀，故它**必須**還是 ready——把它判紅等於
    砸溫度計。但 `reasons=[]` 不可以是全部的輸出：
      · σ=0.0 是「recall 沒變」而非「反漂移驗過了」；
      · observation_streak=0 ⇒ ready 完全靠 60ms tolerant 軌成立。
    兩件事讀 log 的人有權當場看到，否則「毫無保留就達標」的誤讀會被寫進結論。
    """
    records = [
        _rec(p95=52.0 + d * 0.01, recall=0.999,
             ts=(_STALE_BASE - _dt.timedelta(days=d)).isoformat())
        for d in range(OBSERVATION_REQUIRED_RUNS - 1, -1, -1)
    ]

    rpt = evaluate(records, now=_STALE_BASE + _dt.timedelta(days=1))

    assert rpt["ready_for_labeled_pr"] is True
    assert rpt["reasons"] == []
    assert rpt["recall_sigma"] == 0.0
    assert rpt["recall_distinct_values"] == 1
    assert rpt["recall_sigma_discriminating"] is False
    assert rpt["metric_variance_observed"] is True, "p95 有在動 ⇒ 有重新量測的痕跡"
    assert rpt["observation_streak"] == 0, "前提：p95≥50ms ⇒ 觀察軌全未達標"
    assert any("沒有鑑別力" in c for c in rpt["caveats"]), rpt["caveats"]
    assert any("觀察軌" in c for c in rpt["caveats"]), rpt["caveats"]


def test_varying_recall_marks_sigma_as_discriminating() -> None:
    """反向（鎖住 caveat 的鑑別力）：recall 真的有變 → 不得再宣稱 σ 沒鑑別力。

    意圖：若有人把 caveat 寫成無條件輸出（反正加一句話很安全），它就會變成永久噪音、
    人開始跳過不讀；caveat 必須只在該狀態成立時出現。
    """
    recalls = [0.96, 0.97] * 7
    records = [
        _rec(p95=45.0 + i * 0.01, recall=recalls[i],
             ts=(_STALE_BASE - _dt.timedelta(days=13 - i)).isoformat())
        for i in range(OBSERVATION_REQUIRED_RUNS)
    ]

    rpt = evaluate(records, now=_STALE_BASE + _dt.timedelta(days=1))

    assert rpt["recall_distinct_values"] == 2
    assert rpt["recall_sigma_discriminating"] is True
    assert rpt["ready_for_labeled_pr"] is True
    assert not any("沒有鑑別力" in c for c in rpt["caveats"]), rpt["caveats"]


# ══════════════════════════════════════════════════════════════════════════════
# 🔴 R75 / QA-R74-07：未來日期的時間戳不得被 max(0, …) 夾成「永久新鮮」
# ══════════════════════════════════════════════════════════════════════════════


def test_future_timestamp_is_reported_not_clamped_to_fresh() -> None:
    """任一筆真量測的時間戳在未來 → stale + clock_anomaly，且天數如實印負值。

    意圖（Rule 9）：舊式 `max(0, (now - latest_ts).days)` 把負值夾成 0 ⇒ staleness
    恆為 0 ⇒ L-7 這條「必要條件不是加分項」的判準永久失效（採集器之後死掉也不會轉
    stale，因為那筆未來日期永遠是「最新」）。時鐘偏移與手改歷史檔都會製造這種資料，
    而它的失效方向是危險側：閘門開著。夾值是把測不準當成沒問題。
    """
    records = _fourteen_green()
    records.append(
        _rec(p95=46.5, ts=(_STALE_BASE + _dt.timedelta(days=400)).isoformat())
    )

    rpt = evaluate(records, now=_STALE_BASE + _dt.timedelta(days=1))

    assert rpt["clock_anomaly"] is True
    assert rpt["staleness_days"] is not None and rpt["staleness_days"] < 0, (
        "負值被夾成 0 了——未來日期一出現就永久新鮮（QA-R74-07 原形）"
    )
    assert rpt["status"] == "stale"
    assert rpt["ready_for_labeled_pr"] is False
    assert any("未來" in r for r in rpt["reasons"]), rpt["reasons"]


def test_no_clock_anomaly_on_normal_history() -> None:
    """反向：正常歷史不得誤報 clock_anomaly（否則每晚都紅＝訓練人忽略）。"""
    rpt = evaluate(_fourteen_green(), now=_STALE_BASE + _dt.timedelta(days=1))
    assert rpt["clock_anomaly"] is False
    assert rpt["status"] == "ready"


def test_green_streak_gate_breaks_on_single_red_at_tail() -> None:
    """green_streak 閘門的牙：尾端一筆 p95 超門檻 → streak 歸零、ready=False。

    意圖（Rule 9）：ADR-SD09-012 放寬的是「缺口零容忍」，**不是**「紅了也算過」。
    這條就是 ADR §7.2 要求的受控突變驗牙——把它與上面的 staleness 三 case 併看，
    才構成「門檻改鬆了，但仍然關得起來」的完整證據。
    """
    records = _fourteen_green()
    records.append(_rec(p95=63.0, ts=(_STALE_BASE + _dt.timedelta(days=1)).isoformat()))
    rpt = evaluate(records, now=_STALE_BASE + _dt.timedelta(days=2))
    assert rpt["green_streak"] == 0
    assert rpt["ready_for_labeled_pr"] is False
    assert any("連續全綠不足" in r for r in rpt["reasons"])
