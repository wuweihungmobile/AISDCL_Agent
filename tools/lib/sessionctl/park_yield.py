"""park 到點的主載具讓路（QuotaWall DES §7.3；R218 Q3）。

主載具＝同 session 內的 `keepwarm`（它持有 holder 記錄）。到點時 park 是備援，先看主載具還在不在：
· A 活著且還沒到（`wake_at > now`）：重排到 `wake_at＋BACKUP_GRACE_MIN`（每標記至多
`MAX_RESCHEDULES`
  次；第 4 次往下走，舊窗晚醒時由 keepwarm 的交棒重判兜住）。
· B 活著且已過：觀察 `OBSERVE_SEC`（每 `OBSERVE_STEP` 秒重看 driver 與 holder）；出現 driver ⇒
  `primary_woke`；觀察期內 holder 記錄消失 ⇒ 轉 C 重判；期滿仍無 ⇒ 判卡死（S6），往下走。
· C 正常釋放（holder 記錄不存在，且痕跡有本 sid 晚於 park 登記的 `keepwarm_verdict`）：`handed_over`
  ⇒ skip；其他 ⇒ 觀察等 driver，出現 ⇒ `primary_woke`，期滿無記錄 ⇒ 往下走（主控被叫醒卻沒寫記錄：
  視窗
  卡死或已關）。
· D 已死或從未掛（記錄存在但 `is_live` 假，或記錄不存在且無判決痕跡）⇒ 往下走。
回 `{"act": "go"|"skip"|"rearm", "reason", "stuck", "when"}`；`stuck`＝往下走的原因是「疑似卡死」
（B 期滿、C 期滿），只有它與標記 `close_stuck_window` 同時成立才可能殺窗（DES §7.4）。
"""
from __future__ import annotations

import time
from datetime import datetime

from . import holder, park_chain, qw_schema, switch
from .qw_calc import BACKUP_GRACE_MIN, OBSERVE_SEC

MAX_RESCHEDULES = 3
OBSERVE_STEP = 10
RESCHEDULES_KEY = "reschedules"
EV_YIELD = "park_yield_primary"


def _verdict_marks(sid: str, marker: dict) -> list[dict]:
    """本 sid 在 park 登記之後的 `keepwarm_verdict` 列（舊→新）。"""
    parked = qw_schema.parse_epoch(marker.get("parked_at")) or 0.0
    return [r for r in park_chain.trace_rows("keepwarm_verdict")
            if r.get("sid") == sid and (qw_schema.parse_epoch(r.get("at")) or 0.0) >= parked]


def _go(reason: str = "", stuck: bool = False) -> dict:
    return {"act": "go", "reason": reason, "stuck": stuck, "when": None}


def _skip(reason: str) -> dict:
    return {"act": "skip", "reason": reason, "stuck": False, "when": None}


def _observe(sid: str, marker: dict, find, now_fn, sleep, S: dict, *, row_gone: bool) -> dict:
    """觀察期：每 `OBSERVE_STEP` 秒重看 driver 與 holder；回判決（B／C 共用）。"""
    import transcript_activity  # noqa: PLC0415

    read, start = S.get("holder") or holder.read, now_fn()
    while True:
        now = now_fn()
        driver = transcript_activity.live_driver(find(sid), now)
        if driver is not None:
            return _skip("primary_woke")
        if not row_gone and read(sid) is None:  # B 期間記錄消失 ⇒ 轉 C 重判
            return _branch_c(sid, marker, find, now_fn, sleep, S)
        if (now_fn() - start).total_seconds() >= OBSERVE_SEC:
            return _go("primary_stuck", stuck=True)
        sleep(OBSERVE_STEP)


def _branch_c(sid: str, marker: dict, find, now_fn, sleep, S: dict) -> dict:
    marks = _verdict_marks(sid, marker)
    if not marks:
        return _go("no_primary")  # D：沒有任何判決痕跡
    if marks[-1].get("verdict") == "handed_over":
        return _skip("handed_over")
    return _observe(sid, marker, find, now_fn, sleep, S, row_gone=True)


def decide(sid: str, marker: dict, env, S: dict, clock, find) -> dict:
    """見模組說明。`S` 縫：`holder`（讀記錄）、`holder_live`（`is_live`）、`sleep`。"""
    sleep = S.get("sleep") or time.sleep
    row = (S.get("holder") or holder.read)(sid)
    wake = qw_schema.holder_wake(row).wake_at if row is not None else None
    if row is None:
        return _branch_c(sid, marker, find, clock, sleep, S)
    if not (S.get("holder_live") or holder.is_live)(row):
        return _go("primary_dead")  # D
    if wake is not None and wake > clock().timestamp():  # A
        done = int(marker.get(RESCHEDULES_KEY) or 0)
        if done < MAX_RESCHEDULES:
            return {"act": "rearm", "reason": "primary_alive", "stuck": False,
                    "when": wake + BACKUP_GRACE_MIN * 60, "done": done}
        return _go("yield_exhausted")
    return _observe(sid, marker, find, clock, sleep, S, row_gone=False)


def rearm_fields(marker: dict, when: float) -> dict:
    """重排時併進標記的欄位：次數＋新的備援到點（欄名住 `qw_schema`）。"""
    return {RESCHEDULES_KEY: int(marker.get(RESCHEDULES_KEY) or 0) + 1,
            qw_schema.MK_BACKUP_FIRE_AT: qw_schema.iso(when)}


def trace_yield(sid: str, label: str, decision: dict, now: datetime) -> None:
    switch.trace(EV_YIELD, sid=sid, job=label, reason=decision["reason"],
                 rearm_to=qw_schema.iso(decision["when"]), done=decision.get("done", 0),
                 now=now.isoformat())
