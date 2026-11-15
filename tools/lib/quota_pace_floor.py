"""窗內配速床（pace floor）：把窗內「超前」由出聲變成 cap 的煞車力——純函式、零 I/O、零時鐘。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這一支檔存在（ADR-XPLAT-004 §2.15 D1；TCS-TokenWaste-20261114 §10）
# 缺口：`quota_pace.burn_step` 判超前只把該軸視野夾到 far（乘數 0.5），而 free 帶（<50）的
# `_base_cap` 是 `None`，`None × 0.5` 仍是 `None` ⇒ 超前在 free 帶對 cap 零煞車力。實測事故點：
# 38pp／剩 247 分（已過 53 分）、43pp／244 分、48pp／230 分，三個點的 cap 都是 `None`。
#
# 機制（只抬高餵給 `pct_band` 的水位、永不調低；方向鎖＝`apply()` 一律 `max`）：
#   允許線 allowed ＝ 100 × elapsed_frac ＋ burst；over ＝ pct − allowed。
#   over ≤ 0 不動；0 < over ≤ step ⇒ 水位至少 converge；over > step ⇒ 至少 prepare；上界 halt − 1。
#   elapsed_frac 與超前量一律走 `quota_pace.lead_pp`（不另寫第二份算式）。
#
# 🔴 為何獨立成檔、`quota_pace.resolve` 一個字不動：`quota_pace` 餘裕個位數；床是 `resolve` 之後
#   的**後處理**（`quota_policy.axes_of` 先 resolve、再 `apply`），兩者各只有一個家。
# 🔴 免套用（回原值，逐位元等於無本功能）：① 趕工戳記有效 ② 更長窗軸先於本窗 reset（長窗在本短窗
#   內翻頁＝用掉不留）③ 窗長或距離不明 ④ 清倉授權對該軸 hold。順序固定、各有 state 字面。
# 🔴 本檔零 I/O、零時鐘、不讀環境：環境只能經 `Policy` 進場、時間只能經 `now` 進場；
#   與 `quota_policy` 同樣維持 Python 3.9 可載入（不用 `slots=`／`zip(strict=)`／執行期 `A|B`）。
from __future__ import annotations

import math
from typing import NamedTuple

import quota_pace as W

#: 趕工戳記有效期上限（秒）＝5 小時。只准下修；`quota_rush.issue` 的 hours 上限由它導出。
RUSH_MAX_SECONDS = 18000.0
#: 「短窗」的窗長上界（分鐘，一日）。床只作用在窗內速率軸；最短窗軸若長於此值（例：只剩週軸，
#: 因為 session 與 five_hour 都缺席）就不是短窗——對週軸套床會與「週額度用滿」目標直接相抗。
SHORT_WINDOW_MAX_MINUTES = 1440.0
#: 併入逐軸 note 與 `Decision.reason` 的字面。
NOTE_PACE = "pace-floor"
STATE_LIFTED, STATE_WITHIN, STATE_UNKNOWN, STATE_NA = "lifted", "within", "unknown", "n/a"
STATE_RUSH, STATE_WEEKLY, STATE_HOLD = "exempt-rush", "exempt-weekly-reset", "exempt-hold"
#: 比較前的捨入位數：邊界點（over 恰為 0 或 S）不得被浮點誤差推過線（AT-QP-02／03）。
_ROUND = 9


class PaceFloor(NamedTuple):
    """單一軸的床判準結果。`level` 只有 `lifted` 才有值。"""

    kind: str
    pct: float
    minutes: float | None
    window: float | None
    allowed_pp: float | None
    over_pp: float | None
    level: float | None
    state: str


def pace_floor(pct, minutes, window, burst, step, converge, prepare, halt):
    """餵入水位下限；`None`＝不抬。永不為負、不低於 converge、不高於 `halt − 1`。"""
    lead = W.lead_pp(pct, minutes, window)
    if lead is None:
        return None
    over = round(lead - float(burst), _ROUND)
    if over <= 0:
        return None
    level = float(prepare) if over > float(step) else float(converge)
    return min(level, float(halt) - 1.0)


def rush_active(policy, now) -> bool:
    """趕工戳記（`Policy.pace_rush_until`，epoch 秒）此刻是否有效：`0 < until − now ≤ 上限`。"""
    until = getattr(policy, "pace_rush_until", None)
    if until is None:
        return False
    try:
        left = float(until) - now.timestamp()
    except (TypeError, ValueError, OverflowError):
        return False
    return 0.0 < left <= RUSH_MAX_SECONDS


def _num(value):
    """有限數字或 `None`（畸形輸入不拋）。"""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _one(row, delta, win, shortest, longer_minutes, policy, rush, held):
    kind, raw_pct, _at, _note = row
    minutes = delta[0] if delta[0] is None or _num(delta[0]) is not None else None
    if shortest is None or win is None or win != shortest:
        return PaceFloor(str(kind), raw_pct, minutes, win, None, None, None, STATE_NA)
    pct = _num(raw_pct)
    if pct is None or minutes is None or minutes < 0:
        return PaceFloor(str(kind), raw_pct, minutes, win, None, None, None,
                         STATE_RUSH if rush else STATE_UNKNOWN)
    elapsed = min(1.0, max(0.0, 1.0 - float(minutes) / float(win)))
    allowed = 100.0 * elapsed + float(policy.pace_burst_pp)
    over = pct - allowed
    head = (str(kind), pct, float(minutes), float(win), allowed, over)
    if rush:
        return PaceFloor(*head, None, STATE_RUSH)
    if held:
        return PaceFloor(*head, None, STATE_HOLD)
    if any(0.0 <= m < float(minutes) for m in longer_minutes):
        return PaceFloor(*head, None, STATE_WEEKLY)
    level = pace_floor(pct, minutes, win, policy.pace_burst_pp, policy.pace_step_pp,
                       policy.converge_pct, policy.prepare_pct, policy.halt_pct)
    if level is None:
        return PaceFloor(*head, None, STATE_WITHIN)
    return PaceFloor(*head, level, STATE_LIFTED)


def evaluate(rows, deltas, policy, now, *, skip=(), hold=()):
    """逐軸判床。`rows`＝`quota_policy._rows` 形狀；`deltas`＝`[(帶號分鐘|None, note)]`，同序。

    只有**最短窗軸**（遮罩後窗長最小者）會得到 lifted／within／exempt-*／unknown；其餘軸 `n/a`。
    """
    rows, deltas = tuple(rows), tuple(deltas)
    wins = W.mask_windows(W.windows(tuple((r[0], r[2]) for r in rows)), tuple(skip))
    known = [w for w in wins if w is not None and w > 0]
    shortest = min(known) if known else None
    if shortest is not None and shortest > SHORT_WINDOW_MAX_MINUTES:
        shortest = None  # 只剩日窗以上的軸（例：僅週軸）⇒ 沒有「短窗」，床不套用（不與週用滿相抗）
    longer = tuple(d[0] for d, w in zip(deltas, wins)
                   if shortest is not None and w is not None and w > shortest
                   and d[0] is not None and _num(d[0]) is not None)
    rush = rush_active(policy, now)
    holds = tuple(hold) if hold else (False,) * len(rows)
    return tuple(_one(r, d, w, shortest, longer, policy, rush, bool(h))
                 for r, d, w, h in zip(rows, deltas, wins, holds))


def apply(resolved, floors):
    """`resolve` 輸出疊上床：`lifted` 軸 `feed = max(feed, level)`，真的抬了才併 note。"""
    resolved = tuple(resolved)
    if not floors:
        return resolved
    out = []
    for item, floor in zip(resolved, floors):
        feed, horizon, minutes, note = item
        if floor.state == STATE_LIFTED and floor.level is not None and floor.level > feed:
            out.append((float(floor.level), horizon, minutes,
                        "+".join(x for x in (note, NOTE_PACE) if x)))
        else:
            out.append(item)
    return tuple(out)


def _phrase(f) -> str:
    when = "reset 距離不明" if f.minutes is None else f"剩 {int(max(0.0, f.minutes))} 分鐘"
    used = _num(f.pct)
    head = f"  配速床：kind={f.kind} {when}，已用 {f.pct if used is None else f'{used:.0f}'}pp，"
    if f.state == STATE_LIFTED:
        return (head + f"超過允許線 {f.allowed_pp:.0f}pp（超線 {f.over_pp:.1f}pp）"
                f"⇒ 餵入水位至少抬到 {f.level:.0f}pp 帶；急用可趕工（sessionctl rush）\n")
    if f.state == STATE_WITHIN:
        return head + f"允許線 {f.allowed_pp:.0f}pp ⇒ 未超線，床不動\n"
    if f.state == STATE_RUSH:
        return head + "趕工戳記生效中 ⇒ 配速床暫停（到期自動恢復）\n"
    if f.state == STATE_WEEKLY:
        return head + "更長窗軸先 reset ⇒ 本窗用掉不留，床不套用\n"
    if f.state == STATE_HOLD:
        return head + "清倉授權中 ⇒ 操作者明示要用盡，床不套用\n"
    return head + "窗長或 reset 距離不明 ⇒ 不明則不抬水位\n"


def line(floors) -> str:
    """`--pace` 的配速床一段（每個最短窗軸一行；無最短窗軸回空字串）。全文不含 `%`，一律 pp。"""
    return "".join(_phrase(f) for f in (floors or ()) if f.state != STATE_NA)
