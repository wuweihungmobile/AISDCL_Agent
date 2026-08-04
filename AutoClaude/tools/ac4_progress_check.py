"""SD_Improving_08 W2 T2-C3 — AC4 14 天 nightly 觀察期進度檢查。

對應 [SD_Improving_08.md §3 W2 + PM #2 漸進式升級](../docs/04_planning/SD_Improving_08.md)。

職責：
    1. 讀 .ac4_history.jsonl **全史**紀錄（ADR-SD09-012 L-1；滾動窗降為資訊欄）
    2. 計算 recall σ（最近 OBSERVATION_REQUIRED_RUNS 筆）+ 連續全綠**筆數**
    3. 判定告警等級（黃 3 次 / 紅 5 次 / 阻塞 P1）
    4. 判定證據新鮮度（ADR-SD09-012 L-7 staleness；採集停擺不得假綠）
    5. 連續 14 筆全綠 → 輸出 ready_for_labeled_pr=true（升級條件達成）

通過門檻（PM #2 拍板 + ADR-SD09-008 v0.4 ACCEPTED 2026-05-25
        + ADR-SD09-012 ACCEPTED 2026-08-03 PM 拍板落地）：
    recall@10 ≥ 0.95
    p95 latency < 60ms（升級門檻；ADR-SD09-008 v0.4 ACCEPTED 自 50ms 升 60ms tolerant）
    observation p95 < 50ms（觀察軌指標；向上相容，未來 production hardware 切換用）
    recall σ ≤ 0.02（取最近 OBSERVATION_REQUIRED_RUNS 筆）
    CircuitBreaker open=0
    **連續 14 筆綠紀錄**（gap-tolerant green_streak；ADR-SD09-012 §3.2）
    最新一筆距今 ≤ STALENESS_MAX_DAYS（ADR-SD09-012 L-7）

🔴 ADR-SD09-012 判準單位變更（PM 2026-08-03 拍板 §7.0）：
    達標條件由「14 筆須落在最近 14 個**連續日曆天**」改為「連續 14 **筆**綠紀錄」。
    門檻數值不變（仍是 14），改的只有計量單位。反作弊未放寬——writer 端
    ac4_nightly_collector 的 M-05「同 UTC 日去重」原封不動，每 UTC 日上限 1 筆，
    故「14 筆」在數學上仍蘊含「≥ 14 個不同 UTC 日期」，時間跨度一天沒少；
    被移除的只有「這 14 天必須相鄰」（＝量使用者開機作息，不量系統品質）。
    配套的 L-7 staleness 判準是**必要條件不是加分項**：舊判準的 filter_recent()
    是 evaluate() 唯一參照「現在」的項，把它移出閘門路徑會讓達標退化成純檔案
    內容函式（採集器無聲死掉 → green_streak 永久凍結 → 永遠回 ready=True）。

退出碼：
    0  observing（連續全綠未滿）/ ready（達標可升級）
    1  alert（黃線 3 次以上 / 紅線 5 次以上）/ stale（證據過期，採集可能已停擺）

JSONL schema：由 tools/ac4_nightly_collector.py 產出。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_HISTORY = _REPO_ROOT / ".ac4_history.jsonl"

# PM #2 拍板門檻
#
# SD_09 W2 audit P0-AUDIT-08 修復（紀律 #6：採集 vs 升級必須分軌）：
#   升級判定強制嚴格 50ms（PM #2 拍板）；不再共用採集端 env。
#   優先 AUTOCLAUDE_STRICT_P95_THRESHOLD_MS（升級專用）；
#   未設則用舊共用 env AUTOCLAUDE_TEST_P95_THRESHOLD_MS；都未設則 50ms。
#
# 此前 collector 與 progress_check 共用同一 env 導致 collector 標 pass 後
# progress_check 看的就是已被寬鬆標 pass 的歷史紀錄 → 升級條件假性達標。
#
# SD_09 W3 Round 12 P0-R12-1（ADR-SD09-008 v0.4 ACCEPTED 拍板實作落地）：
#   升級門檻自 50ms 改為 60ms tolerant（PM 2026-05-25 拍板選項 (a)）；
#   strict 50ms 軌降為「觀察品質指標」，持續採集寫入 jsonl summary，
#   未來 production hardware 切換後若 < 50ms 可作為升級依據（向上相容）。
#   - _resolve_strict_p95_threshold() 預設 60.0（升級判定門檻；舊名保留，向下相容）
#   - _resolve_observation_p95_threshold() 預設 50.0（觀察軌指標，不阻塞）
RECALL_MIN = 0.95


def _resolve_strict_p95_threshold() -> float:
    """升級門檻（ADR-SD09-008 v0.4 ACCEPTED：60ms tolerant）。

    解析優先序：strict 專用 env > 舊共用 env > 預設 60ms。
    舊預設值 50ms 已於 2026-05-25 PM 拍板升為 60ms（紀律 #6 採集 vs 升級分軌；
    真實機器 7 筆樣本 max 53.21ms / σ 0.73ms → 60ms 緩衝 12.8%）。

    SD_09 W3 Round 33 audit P1-R33-1 修復（紀律 #6 採集寬鬆 vs 升級嚴格分軌）：
    當 strict 專用 env 未設、僅 legacy 共用 env 有值時，stderr WARN 取證 —
    避免 nightly 外人工執行 progress_check 時誤以採集寬鬆值（如 80ms）作升級判定。
    """
    strict_env = os.environ.get("AUTOCLAUDE_STRICT_P95_THRESHOLD_MS")
    if strict_env:
        return float(strict_env)
    legacy_env = os.environ.get("AUTOCLAUDE_TEST_P95_THRESHOLD_MS")
    if legacy_env:
        sys.stderr.write(
            "[ac4_progress_check] WARN: AUTOCLAUDE_STRICT_P95_THRESHOLD_MS unset; "
            f"falling back to legacy AUTOCLAUDE_TEST_P95_THRESHOLD_MS={legacy_env}ms. "
            "This may hijack strict upgrade threshold with collector-relaxed value — "
            "set strict env explicitly per ADR-SD09-008 v0.4 (R33 audit P1).\n"
        )
        return float(legacy_env)
    return 60.0


def _resolve_observation_p95_threshold() -> float:
    """觀察軌指標門檻（ADR-SD09-008 v0.4 ACCEPTED：strict 50ms 降為觀察用）。

    解析優先序：observation 專用 env > 預設 50ms。
    觀察軌僅寫入 jsonl summary `observation_streak`，**不影響** ready_for_labeled_pr。
    """
    obs_env = os.environ.get("AUTOCLAUDE_OBSERVATION_P95_THRESHOLD_MS")
    if obs_env:
        return float(obs_env)
    return 50.0


P95_MAX_MS = _resolve_strict_p95_threshold()
P95_OBSERVATION_MS = _resolve_observation_p95_threshold()
RECALL_SIGMA_MAX = 0.02
CB_OPEN_MAX = 0
# ADR-SD09-012 L-2：判準的計量單位是「綠紀錄筆數」，不是日曆天。舊名保留為別名，
# 免得打斷既有 import（tests/contract 與 run_local_nightly 都讀過舊名）。
OBSERVATION_REQUIRED_RUNS = 14
OBSERVATION_DAYS = OBSERVATION_REQUIRED_RUNS
# ADR-SD09-012 L-7 / §7.5 S4：證據新鮮度上限（PM 建議值 30 = window 14 的約 2 倍）。
#
# 為何不是 14：這台機器近 75 天只活 52 天、7/22、7/29、8/1 各一次冷開機（ADR §2.5/§2.6
# 實測）。N 取 14 等於把剛拆掉的「機器要天天開機」換個名字裝回來，AC4 會再次卡死。
# N 的職責**只有一個**：區分「使用者放了個長假」與「採集器死了」，不是重新量作息。
STALENESS_MAX_DAYS = 30
ALERT_YELLOW_THRESHOLD = 3  # 連續 3 次未達 → 黃線
ALERT_RED_THRESHOLD = 5  # 連續 5 次未達 → 紅線


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _parse_ts(record: dict[str, Any]) -> _dt.datetime | None:
    """SD_09 W2 audit P1-AUDIT-15 修復：collector 寫入已含 +00:00，
    .replace("Z", "+00:00") 為 dead code；但其他寫入端（手動 / 早期格式）可能用 'Z'，
    保留兼容處理但 None-safe。
    """
    ts = record.get("timestamp")
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def filter_recent(
    records: list[dict[str, Any]],
    days: int = OBSERVATION_REQUIRED_RUNS,
    *,
    now: _dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """取最近 `days` 天的紀錄（依 timestamp 排序）。

    SD_09 W2 audit P2-AUDIT-25 修復：對 _parse_ts 回 None 的 record 印 WARN 到 stderr，
    不再靜默丟掉壞 timestamp 紀錄（避免歷史資料因格式錯誤被悄悄忽略）。

    ADR-SD09-012 L-1：本函式**已不在閘門路徑上**，退為資訊欄（`observation_days`）
    與人類判讀用的滾動窗計數器。閘門改由 `evaluate()` 的 green_streak + staleness 決定。
    `now` 可注入，讓 staleness／滾動窗兩者的測試不必依賴真實時鐘（ADR L-7 要求
    staleness 有雙向鑑別力測試，注入時鐘是唯一能穩定驗紅／驗綠的方式）。
    """
    now = now or _dt.datetime.now(tz=_dt.UTC)
    cutoff = now - _dt.timedelta(days=days)
    recent: list[dict[str, Any]] = []
    dropped = 0
    for r in records:
        ts = _parse_ts(r)
        if ts is None:
            dropped += 1
            continue
        if ts >= cutoff:
            recent.append(r)
    if dropped > 0:
        sys.stderr.write(
            f"[ac4_progress_check] WARN: dropped {dropped} records with unparseable timestamp\n"
        )
    recent.sort(key=lambda r: _parse_ts(r) or now)
    return recent


def sort_by_timestamp(
    records: list[dict[str, Any]], *, now: _dt.datetime | None = None
) -> list[dict[str, Any]]:
    """依 timestamp 升冪排序**全史**（ADR-SD09-012 L-1 配套）。

    為何需要：green_streak 與 consecutive_failures 都是「自尾端往前數」，其正確性
    完全依賴呼叫端已排序。舊路徑靠 `filter_recent()` 順手排序；它退出閘門路徑後，
    全史若不排序，jsonl 內任何一筆順序異常都會讓 streak 從錯的地方起算。
    壞 timestamp 的紀錄排到最後（與 filter_recent 的 `or now` 同慣例，不另立第二套）。
    """
    now = now or _dt.datetime.now(tz=_dt.UTC)
    return sorted(records, key=lambda r: _parse_ts(r) or now)


def latest_timestamp(records: list[dict[str, Any]]) -> _dt.datetime | None:
    """全史中最新的可解析 timestamp；全部不可解析或空 history → None。"""
    parsed = [ts for ts in (_parse_ts(r) for r in records) if ts is not None]
    return max(parsed) if parsed else None


def _is_green(record: dict[str, Any]) -> bool | None:
    """判定一筆紀錄是否全綠（升級門檻 P95_MAX_MS）。

    SD_09 W3 Round 12 P0-R12-1 修復（ADR-SD09-008 v0.4 ACCEPTED 落地）：
        升級門檻自 50ms 改為 60ms tolerant；原 50~60ms neutral 三段式設計取消
        （因為 60ms 已成正式升級門檻，不再需要 1.0~1.2 倍 neutral buffer）。

    回傳值（保留三態 sentinel）：
        True  → 綠（4 條件達成 + p95 < P95_MAX_MS）
        False → 紅（status=fail / 缺值 / recall 或 CB 未達 / p95 ≥ P95_MAX_MS）
        None  → 中性（status=skip）— 不算綠亦不累計 fail streak

    路徑說明：
        - status='skip' → None（觀察期 X1 補實作前的 hardcoded skip 情境保留）
        - status='pass' + 4 條件達標 + p95 < 60ms → True（升級條件達成）
        - 其餘 → False（包含 collector 寬鬆 pass 但 p95 ≥ 60ms 的 alert 場景）
        - observation 軌（< 50ms）由 _is_green_observation 處理，**不影響** ready 判定
    """
    # P0-02 三態 sentinel：skip 視為中性，不污染 fail streak / green streak
    if record.get("status") == "skip":
        return None
    if record.get("status") != "pass":
        return False
    recall = record.get("recall_at_10")
    p95 = record.get("p95_ms")
    cb = record.get("circuit_breaker_open_count", 0) or 0
    if recall is None or p95 is None:
        return False
    # 必要綠燈條件：recall + cb 達標（兩項由 PM #2 拍板必要）
    if not (recall >= RECALL_MIN and cb <= CB_OPEN_MAX):
        return False
    # 升級門檻判定：< P95_MAX_MS (60ms ACCEPTED) → 綠；≥ P95_MAX_MS → fail
    if p95 < P95_MAX_MS:
        return True
    return False


def _is_green_observation(record: dict[str, Any]) -> bool | None:
    """SD_09 W3 Round 12 P0-R12-1：觀察軌綠標判定（50ms 觀察指標）。

    與 ``_is_green`` 同樣回三態，唯一差別：p95 < P95_OBSERVATION_MS（預設 50ms）才算綠。
    用途：未來 production hardware 切換後若 < 50ms 可作為升級依據（向上相容紅線 ❌4）。
    **不影響** ``ready_for_labeled_pr``（仍由 P95_MAX_MS 60ms 升級門檻決定）。
    """
    if record.get("status") == "skip":
        return None
    if record.get("status") != "pass":
        return False
    recall = record.get("recall_at_10")
    p95 = record.get("p95_ms")
    cb = record.get("circuit_breaker_open_count", 0) or 0
    if recall is None or p95 is None:
        return False
    if not (recall >= RECALL_MIN and cb <= CB_OPEN_MAX):
        return False
    if p95 < P95_OBSERVATION_MS:
        return True
    return False


def _consecutive_failures_from_tail(records: list[dict[str, Any]]) -> int:
    """從尾端往前計算連續未達綠線的次數。

    SD_09 Pre-W0 audit P0-02：遇 None（skip）→ continue 不累計，不中斷 streak。
    """
    count = 0
    for r in reversed(records):
        verdict = _is_green(r)
        if verdict is None:
            # skip：中性，不累計也不中斷
            continue
        if verdict:
            break
        count += 1
    return count


def _is_green_tolerant(record: dict[str, Any], tolerant_p95_ms: float) -> bool | None:
    """SD_09 W3 Round 3 audit P0-1 雙軌綠標判定（向下相容保留）。

    與 ``_is_green`` 同樣回三態（True/False/None），唯一差別：
        p95 < tolerant_p95_ms → 算綠（True）
        其餘 recall / cb 條件相同
        status=='skip' → None（中性，保留 sentinel 行為）

    ADR-SD09-008 v0.4 ACCEPTED 後（2026-05-25 PM 拍板）：
        升級門檻已正式採納 60ms（即 P95_MAX_MS 預設值），由 ``_is_green`` 直接控制升級。
        本函數保留供 evaluate 接收 ``tolerant_p95_ms`` 參數時計算舊呼叫站期望的 streak
        （測試與 nightly script 向下相容）。
    """
    if record.get("status") == "skip":
        return None
    if record.get("status") != "pass":
        return False
    recall = record.get("recall_at_10")
    p95 = record.get("p95_ms")
    cb = record.get("circuit_breaker_open_count", 0) or 0
    if recall is None or p95 is None:
        return False
    if not (recall >= RECALL_MIN and cb <= CB_OPEN_MAX):
        return False
    if p95 < tolerant_p95_ms:
        return True
    return False


def _compute_green_streak_from_tail(records: list[dict[str, Any]], judge) -> int:
    """從尾端往前計算 streak；遇 None continue（中性），遇 False break。"""
    streak = 0
    for r in reversed(records):
        verdict = judge(r)
        if verdict is None:
            continue
        if verdict:
            streak += 1
        else:
            break
    return streak


def evaluate(
    records: list[dict[str, Any]],
    *,
    tolerant_p95_ms: float | None = None,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """評估觀察期狀態（ADR-SD09-008 v0.4 + ADR-SD09-012 ACCEPTED 語意）。

    Args:
        records: **全史**紀錄（ADR-SD09-012 L-1；不再是「滾動 14 天窗內的紀錄」）。
            仍可傳入已過濾的子集（舊呼叫站行為不會炸），但那樣會少算 green_streak。
        tolerant_p95_ms: 向下相容參數；若提供，額外計算 tolerant_streak。
            ADR v0.4 ACCEPTED 後 tolerant 軌已成為升級主軌（預設 60ms），
            本參數保留兼容舊呼叫站；新呼叫可不傳。
        now: 可注入的「現在」（ADR-SD09-012 L-7）。staleness 判準需要時鐘，
            注入才能對它做雙向鑑別力測試。

    回傳 dict（v0.4 ACCEPTED + ADR-SD09-012 schema）：
        status: observing | ready | alert_yellow | alert_red | stale
        observation_days: 滾動 14 日曆天窗內筆數（**資訊欄**，ADR-SD09-012 L-4 (a)
            語意凍結——它**不是**閘門值，閘門值是 green_streak）
        gate_basis: 'green_streak'（明示閘門依據，供下游不必猜哪個欄位是判準）
        green_streak_required: 達標所需連續綠筆數（= OBSERVATION_REQUIRED_RUNS）
        total_records: 全史筆數
        staleness_days: 最新一筆距今天數（None＝無可解析 timestamp）
        staleness_max_days: 上限（超過即 status='stale'）
        green_streak: 連續全綠**筆數**（= 升級門檻 streak，ADR-SD09-012 唯一達標閘門）
        tolerant_streak: 升級門檻連續綠（P95_MAX_MS=60ms ACCEPTED）
        observation_streak: 觀察軌連續綠（P95_OBSERVATION_MS=50ms，向上相容指標，不影響 ready）
        strict_streak: 向下相容別名（= tolerant_streak；舊呼叫站讀此欄）
        tolerant_p95_ms: 採用的升級門檻（即 P95_MAX_MS）
        observation_p95_ms: 採用的觀察軌門檻（即 P95_OBSERVATION_MS）
        consecutive_failures: 連續未達次數
        recall_sigma: 14 天 recall σ
        ready_for_labeled_pr: 是否可升級（由升級門檻 60ms 決定，ADR v0.4 ACCEPTED）
        reasons: list[str] 不可升級的原因
    """
    now = now or _dt.datetime.now(tz=_dt.UTC)
    n = len(records)
    consecutive_failures = _consecutive_failures_from_tail(records)

    # 升級門檻 streak（從尾端往前算連續綠；ADR v0.4 ACCEPTED：60ms）
    # P0-02：None（skip）→ continue（中性），不破壞 streak；False（fail）→ break
    green_streak = _compute_green_streak_from_tail(records, _is_green)

    # 觀察軌 streak（向上相容指標；不影響 ready）
    observation_streak = _compute_green_streak_from_tail(records, _is_green_observation)

    # 向下相容：tolerant_p95_ms 參數若傳入，計算對應 streak（舊呼叫站行為）；
    # 否則 tolerant_streak = green_streak（= 升級門檻 60ms streak）
    if tolerant_p95_ms is not None:
        tolerant_streak: int = _compute_green_streak_from_tail(
            records, lambda r: _is_green_tolerant(r, tolerant_p95_ms)
        )
        effective_tolerant_p95 = tolerant_p95_ms
    else:
        tolerant_streak = green_streak
        effective_tolerant_p95 = P95_MAX_MS

    # SD_09 W0 P0-AUDIT-33 修復：拆 None 為兩態，避免訊息漂移
    #   true_skip   = status=='skip'（X1 補實作前的 hardcoded skip）
    #   ADR v0.4 ACCEPTED 後不再有 neutral_p95 區（60ms 已成升級門檻，非 neutral buffer）
    # ADR-SD09-012 L-5：改吃全史後語意由「窗內全 skip」變成「**史上全 skip**」。
    # 實務上只在冷啟動期成立（第一筆真量測寫進來就不再成立），但屬語意變更，
    # 故明示於此並在 tests/contract 補一個「全史含真量測 → 不得誤報 skip 阻塞」的 case。
    all_true_skip = n > 0 and all(r.get("status") == "skip" for r in records)

    # ADR-SD09-012 L-3：σ 取樣集合＝**最近 N 筆**，不是全史。
    # 🔴 這是本次落地最容易漏、且會靜默削弱反漂移的一處：全史傳進來後若不切片，
    # σ 會變成對 40+ 筆求標準差＝偷偷放大取樣窗、把漂移平均掉。ADR §3.3 ② 明載
    # 「σ 的統計內容不變，只是取樣集合從日曆窗換成最近 N 筆」。
    sigma_window = records[-OBSERVATION_REQUIRED_RUNS:]
    recalls = [r["recall_at_10"] for r in sigma_window if r.get("recall_at_10") is not None]
    if len(recalls) >= 2:
        recall_sigma = statistics.pstdev(recalls)
    else:
        recall_sigma = None

    # ADR-SD09-012 L-7：證據新鮮度（liveness）——**與 green_streak 完全無關的獨立判準**。
    # green_streak 回答「證據夠不夠」，staleness 回答「證據還算不算數」；兩者混成一個
    # 變數就會重演「一個變數兼兩個職責」那個病（舊 filter_recent 同時當窗口與時鐘）。
    latest_ts = latest_timestamp(records)
    staleness_days: int | None = None
    if latest_ts is not None:
        staleness_days = max(0, (now - latest_ts).days)
    # 有紀錄卻連一筆可解析 timestamp 都沒有＝採集端壞掉，fail-closed 當 stale 處理。
    is_stale = n > 0 and (staleness_days is None or staleness_days > STALENESS_MAX_DAYS)

    reasons: list[str] = []
    ready = False
    status = "observing"

    if is_stale:
        # 排在最前面：證據不新鮮的話，後面每個判定都是在對死資料下結論。
        status = "stale"
        if staleness_days is None:
            reasons.append("證據時間戳全數無法解析，採集可能已停擺（無法判定新鮮度）")
        else:
            reasons.append(
                f"證據過期（最新一筆距今 {staleness_days} 天 > {STALENESS_MAX_DAYS} 天），"
                "採集可能已停擺"
            )
    elif all_true_skip:
        # AC4 hardcoded skip 情境（X1 補實作前）
        status = "observing"
        reasons.append("AC4 hardcoded skip 阻塞，需 X1 補實作")
    elif consecutive_failures >= ALERT_RED_THRESHOLD:
        status = "alert_red"
        reasons.append(f"連續 {consecutive_failures} 次未達綠線（紅線 ≥ {ALERT_RED_THRESHOLD}）")
    elif consecutive_failures >= ALERT_YELLOW_THRESHOLD:
        status = "alert_yellow"
        reasons.append(f"連續 {consecutive_failures} 次未達綠線（黃線 ≥ {ALERT_YELLOW_THRESHOLD}）")
    elif green_streak < OBSERVATION_REQUIRED_RUNS:
        # ADR-SD09-012 L-2：此分支是**唯一**達標閘門。
        # 舊版另有一道「n < 門檻」分支（n＝滾動 14 日曆天窗內筆數）——它要求 14 筆落在
        # 14 個相鄰日曆天，也就是零缺口，等於把「使用者有沒有天天開機」寫進系統品質判準
        # （這台機器的期望達標時間 1.5～89 年，ADR §2.5）。單位一併從「天」改成「筆」。
        reasons.append(f"連續全綠不足（{green_streak}/{OBSERVATION_REQUIRED_RUNS} 筆）")
    elif recall_sigma is not None and recall_sigma > RECALL_SIGMA_MAX:
        reasons.append(f"recall σ={recall_sigma:.4f} > {RECALL_SIGMA_MAX}")
    else:
        status = "ready"
        ready = True

    # ADR-SD09-012 L-4 (a)【落地輪拍板採 (a)】：`observation_days` **語意凍結**＝滾動
    # 14 日曆天窗計數，維持原義不漂移；閘門值改由新欄 `green_streak` + `gate_basis`
    # 明示。理由：該欄有三個下游消費者（run_local_nightly 的 Get-Ac4Gate、END 進度行、
    # F2 區塊）。若改成全史筆數，它們會印出 `ac4=43/14` 這種「看起來超標三倍」的數字
    # ——那正是 ADR §2.8 記載、R69 剛修好的假達標誤導，不能由我們自己再造一次。
    rolling_window_count = len(filter_recent(records, now=now))

    result: dict[str, Any] = {
        "status": status,
        "observation_days": rolling_window_count,
        "total_records": n,
        "gate_basis": "green_streak",
        "green_streak_required": OBSERVATION_REQUIRED_RUNS,
        "staleness_days": staleness_days,
        "staleness_max_days": STALENESS_MAX_DAYS,
        "green_streak": green_streak,
        "tolerant_streak": tolerant_streak,
        "observation_streak": observation_streak,
        "strict_streak": tolerant_streak,  # 向下相容別名
        "tolerant_p95_ms": effective_tolerant_p95,
        "observation_p95_ms": P95_OBSERVATION_MS,
        "consecutive_failures": consecutive_failures,
        "recall_sigma": recall_sigma,
        "ready_for_labeled_pr": ready,
        "reasons": reasons,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            pass
    parser = argparse.ArgumentParser(description="AC4 14 天 nightly 進度檢查 (SD_08 W2 T2-C3).")
    parser.add_argument(
        "--history",
        type=Path,
        default=_DEFAULT_HISTORY,
        help="JSONL 累計檔（預設 .ac4_history.jsonl）",
    )
    parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")
    parser.add_argument(
        "--tolerant-p95-ms",
        type=float,
        default=None,
        help=(
            "向下相容參數（ADR-SD09-008 v0.4 ACCEPTED 後升級門檻已固定 60ms，由 P95_MAX_MS 控制）。"
            "若提供則 tolerant_streak 用本值計算（舊呼叫站行為）；否則同 P95_MAX_MS。"
        ),
    )
    args = parser.parse_args(argv)

    # ADR-SD09-012 L-1：閘門吃**全史**（先排序，理由見 sort_by_timestamp）。
    # filter_recent 仍被 evaluate() 內部用來算資訊欄 observation_days，這裡不再預先過濾
    # ——預先過濾就是把剛拆掉的「零缺口」要求裝回去。
    records = sort_by_timestamp(load_history(args.history))
    report = evaluate(records, tolerant_p95_ms=args.tolerant_p95_ms)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        # SD_09 W3 Round 12 P0-R12-1（ADR-SD09-008 v0.4 ACCEPTED）：
        # 升級門檻 60ms tolerant 為主軌；50ms observation 軌為觀察指標
        print(f"[AC4 progress] status={report['status']}")
        # ADR-SD09-012 §7.4 DoD #5：切換當下印一行 [MIGRATION] 取證，同時列出
        # **舊口徑**（滾動窗筆數）與**新口徑**（green_streak），供日後稽核判準是何時、
        # 從哪個數字換到哪個數字。刻意不寫死任何數字——ADR 起草期間該對數字已從
        # 7/14→8/14→9/14 漂移過三次，寫死必過期。
        print(
            f"  [MIGRATION] gate_basis={report['gate_basis']} "
            f"(ADR-SD09-012 ACCEPTED)：新口徑 green_streak="
            f"{report['green_streak']}/{report['green_streak_required']} 筆；"
            f"舊口徑 observation_days={report['observation_days']}/{OBSERVATION_REQUIRED_RUNS} "
            f"rolling-window-days（已降為資訊欄，不再是閘門）"
        )
        print(
            f"  staleness_days={report['staleness_days']}"
            f"/{report['staleness_max_days']} (L-7 獨立判準；超過即 status=stale)"
        )
        print(f"  total_records={report['total_records']}")
        print(
            f"  tolerant_streak={report['tolerant_streak']} "
            f"(p95 < {report['tolerant_p95_ms']:.0f}ms; ADR-SD09-008 v0.4 ACCEPTED 升級門檻)"
        )
        print(
            f"  observation_streak={report['observation_streak']} "
            f"(p95 < {report['observation_p95_ms']:.0f}ms; 觀察軌指標，不影響 ready)"
        )
        print(f"  consecutive_failures={report['consecutive_failures']}")
        print(f"  recall_sigma={report['recall_sigma']}")
        print(f"  ready_for_labeled_pr={report['ready_for_labeled_pr']}")
        if report["reasons"]:
            print("  reasons:")
            for r in report["reasons"]:
                print(f"    - {r}")

    # 'stale' 一併回 1：採集停擺與告警一樣「需要人去修」，不是「再等等就好」。
    if report["status"] in ("alert_yellow", "alert_red", "stale"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
