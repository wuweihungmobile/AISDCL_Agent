#!/usr/bin/env python3
"""觀察期 GA 判準的**時間窗**共用層（`observability_ga_check` ／ `drift_log_ga_check`）。

🔴 為何存在（R76 四方複審 SD-04）：R76 給兩支 GA checker 各自加了 staleness ＋ 窗內
連續性判準，兩份實作**逐字相同**（difflib 實測單一區塊 112 行完全一致），而且**零 parity
鎖**——實測把 drift 的 `STALENESS_MAX_DAYS` 單邊改成 45、兩支公然不一致的狀態下，
相關三支測試檔仍 `108 passed rc=0`，沒有任何東西會叫。

更難看的是它**在落地的同一輪就已經走岔了**：新貼進 obs 的 `_staleness_days`／
`_window_calendar_span` 消費的是 obs **沒被動過的舊 `_parse_ts`**（不做 tz 正規化），
而 drift 版的 `_parse_ts` 多一行 `return parsed if parsed.tzinfo else parsed.replace(...)`。
結果：兩支「逐字相同」的 `evaluate()` 餵同一筆 naive 時間戳，drift 回 `status=ready`、
obs 直接 `TypeError: can't compare offset-naive and offset-aware datetimes`。
「同一份知識住兩個家、只有一個家被修」——`DEF-101-778` 的教科書級復發。

本模組是那份知識的唯一的家。兩支 checker 改為 re-export（先例：
`tools/archive_defect_log.ACTIVE_STATUS_RE = _ledger_index.ACTIVE_STATUS_RE`），
並由 `AutoClaude/tests/tools/test_drift_log_ga_check.py` 尾端那組鎖以 `is` 綁住
「兩支拿到的是同一個物件」（刻意併入既有測試檔，不新增鎖檔）。

刻意**不**收進來的部分：`_is_green()` 與 `_compute_green_streak()`。兩支的綠判準本來就
不同（obs 有 legacy／strict 的 ts cutoff、drift 看 `drift_log_table_exists`），硬合併會
變成一個帶旗標的四不像。`evaluate()` 因此把「怎麼算 streak」當**參數**收進來。
"""
from __future__ import annotations

import datetime as _dt
from collections.abc import Callable
from fractions import Fraction
from typing import Any

# ── 兩個「時間」面的門檻（語意與值皆抄 ac4_progress_check.py，不另發明第三套）────────
#
# ① 證據新鮮度上限。值＝ac4_progress_check.STALENESS_MAX_DAYS，連同它的 WHY 一起沿用：
#    這台機器近 75 天只活 52 天，N 取太小等於把「機器要天天開機」換個名字裝回來，
#    觀察期會再次卡死。本值的職責**只有一個**：區分「使用者放了個長假」與「採集器死了」。
STALENESS_MAX_DAYS = 30

# ② 窗內連續性上限係數。K 不是手感值，是從一句可辯護的政策推出來的：**last-window 內
#    至少 3/4 的日曆天要有實際量測**，否則「N 天零事件」這張證書講的其實是一段比它
#    自稱短得多的期間。⇒ K = 1 / (3/4) = 4/3；window=30 時跨度上限＝40 個日曆天。
#    window 不被 3 整除時 int() 往下取（略嚴），刻意如此：門檻寧可嚴一天。
#    用 Fraction 而不是 float 的理由是**訊息可讀性**（本值會被插進 FAIL 訊息：float 印成
#    `window×1.3333333333333333`，Fraction 印成 `window×4/3`），**不是精度**——R76 實測
#    `int(30*(4/3)) == 40`、window 掃 1..1000 兩種寫法零筆不一致。
#
#    為何**不**用「機器開機率 52/75 ≈ 0.69 ⇒ K≈1.45」那條線：那是長期平均、含多日長假，
#    而長假已經由上面的 staleness 專門處理。本判準問的是**另一個**問題——窗內的覆蓋密度。
#
#    🔴 實測：本機 last-30 的 span 是 58 天 > 40 ⇒ 判 sparse，也就是這條一上線就會把 obs
#    從「已達標」翻回「未達標」。那是**正確**方向：原本的達標是把 58 天讀成 30 天。
#    **不得為了讓數字好看而調高本值**（砸溫度計）；唯一正路是讓 nightly 真的每天跑。
WINDOW_SPAN_MAX_FACTOR = Fraction(4, 3)


def parse_ts(record: dict[str, Any]) -> _dt.datetime | None:
    """取 record 的 UTC 時間戳；取不到／解析不了回 None（由呼叫端 fail-closed 處置）。

    🔴 **naive 時間戳一律補 UTC**（R76 複審 SD-04 統一）：少了這一步，回傳值會與同模組
    其他 aware 常數（例如 obs 的 `EMIT_REAL_REQUIRED_FROM`）比不了，當場
    `TypeError: can't compare offset-naive and offset-aware datetimes`。
    兩支 checker 的寫入端目前都產 aware 時戳，所以這是**潛伏**缺陷——但兩份實作對它的
    答案不同這件事本身就是缺陷，不是「還沒發生」。
    """
    ts = record.get("ts") or record.get("timestamp") or record.get("date")
    if not isinstance(ts, str) or not ts:
        return None
    try:
        parsed = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=_dt.UTC)


def staleness_days(records: list[dict[str, Any]], now: _dt.datetime) -> int | None:
    """最後一筆紀錄距今的 UTC 天數；一筆可解析時間戳都沒有回 None。

    **有號**（未來時間戳為負）。刻意不夾 0：R75 在 ac4 那支證實過 `max(0, …)` 會讓
    夾過的值恆為 0＝永久新鮮，採集器死掉也不會轉 stale。
    """
    stamps = [ts for ts in (parse_ts(r) for r in records) if ts is not None]
    return (now - max(stamps)).days if stamps else None


def window_calendar_span(
    records: list[dict[str, Any]], window: int
) -> tuple[int | None, int | None]:
    """last-window 筆紀錄的 (日曆跨度, 窗內最大 gap)；可解析日期不足 2 個回 (None, None)。

    跨度定義＝最後一筆日 − 第一筆日 + 1（含頭尾），與 window 同單位才好比較。
    只有 1 個日期時「跨度」沒有意義（也不可能有 gap），此時交給 staleness 那一面去攔。
    """
    days = sorted({
        ts.astimezone(_dt.UTC).date()
        for ts in (parse_ts(r) for r in records[-window:] if window > 0)
        if ts is not None
    })
    if len(days) < 2:
        return None, None
    span = (days[-1] - days[0]).days + 1
    max_gap = max((b - a).days for a, b in zip(days, days[1:], strict=False))
    return span, max_gap


StreakFn = Callable[[list[dict[str, Any]]], "tuple[int, list[dict[str, Any]]]"]


def evaluate(
    records: list[dict[str, Any]],
    *,
    window: int,
    streak_fn: StreakFn,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """純函式判定（`now` 可注入，讓 staleness／span 的雙向鑑別力測試不依賴真實時鐘）。

    三個判準**互相獨立**，任一不成立即非 ready：
      · green_streak >= window   ——「證據夠不夠」
      · 非 stale                 ——「證據還算不算數」（採集器是不是死了）
      · 非 sparse                ——「這 N 筆是不是真的鋪在 N 天上」

    狀態優先序 stale > sparse > observing：採集停擺時「窗內稀疏」只是它的症狀，
    先報停擺才指得到正確的修法（修排程／修載具，而不是再等幾天）。

    `streak_fn` 由呼叫端注入＝兩支 checker 唯一真正不同的那一塊（見模組 docstring）。
    """
    now = now or _dt.datetime.now(tz=_dt.UTC)
    streak, judgements = streak_fn(records)

    stale_days = staleness_days(records, now)
    clock_anomaly = stale_days is not None and stale_days < 0
    # 有紀錄卻連一筆可解析時間戳都沒有＝採集端壞掉，fail-closed 當 stale（同 ac4）。
    is_stale = stale_days is None or stale_days > STALENESS_MAX_DAYS or clock_anomaly
    span_days, max_gap_days = window_calendar_span(records, window)
    span_max_days = int(window * WINDOW_SPAN_MAX_FACTOR)
    is_sparse = span_days is not None and span_days > span_max_days

    passed = streak >= window and not is_stale and not is_sparse
    if is_stale:
        status = "stale"
    elif is_sparse:
        status = "sparse"
    else:
        status = "ready" if passed else "observing"

    last_failure_reason = ""
    if not passed:
        for j in reversed(judgements):
            if not j["green"]:
                last_failure_reason = j["reason"]
                break
    if is_stale:
        last_failure_reason = (
            f"clock_anomaly: 最後一筆時間戳在未來（now - ts = {stale_days} 天）"
            if clock_anomaly else
            "採集端壞掉：有紀錄但一筆可解析時間戳都沒有" if stale_days is None else
            f"證據過期：最後一筆距今 {stale_days} 天 > {STALENESS_MAX_DAYS}"
        )
    elif is_sparse:
        last_failure_reason = (
            f"窗內不連續：last-{window} 筆橫跨 {span_days} 個日曆天 > "
            f"{span_max_days}（window×{WINDOW_SPAN_MAX_FACTOR}），最大 gap {max_gap_days} 天"
            "——筆數夠不代表天數夠"
        )

    return {
        "status": status,
        "green_streak": streak,
        "window": window,
        "total_records": len(records),
        "last_failure_reason": last_failure_reason,
        "staleness_days": stale_days,
        "staleness_max_days": STALENESS_MAX_DAYS,
        "window_span_days": span_days,
        "window_span_max_days": span_max_days,
        "window_max_gap_days": max_gap_days,
    }
