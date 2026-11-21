"""OIR fold：事件序列→每個 OI 的現態與「有沒有有效驅動器」（DES §3.3；REQ-WP-01／03／27／28）。

純函式：不讀檔、不呼叫排程器、不看時鐘。排程工作存不存在由呼叫端以 `sched_exists(task)` 注入
（`True`／`False`／`None`＝快取過期或讀不到）；觸發後的有效性只看帳本（`start`／`attempt`），
完全不讀 `NextRunTime`（Windows 一次性排程觸發後為空、macOS 無此值，所以兩平台同一張表）。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .ledger import parse_ts

TERMINAL = ("closed", "retired")


@dataclass
class Folded:
    items: dict[str, dict] = field(default_factory=dict)
    orphans: int = 0  # 指向不存在的 OI、或對終態項目的事件（資訊用）

    def undriven(self) -> list[dict]:
        return [i for i in self.items.values() if i["undriven"]]


def _sort_key(ev: dict) -> tuple[datetime, int]:
    return parse_ts(ev["ts"]), ev["seq"]


def _new_item(ev: dict) -> dict:
    kind = ev.get("kind")
    return {
        "id": ev["id"], "title": ev.get("title", ""), "source": ev.get("source", ""),
        "scope": ev.get("scope", ""), "kind": kind, "check": ev.get("check"), "due": ev.get("due"),
        "why_not_auto": ev.get("why_not_auto"), "opened": ev["ts"], "opened_seq": ev["seq"],
        "state": "listed" if kind in ("human", "k1") else "open",
        "attempts": 0, "deferrals": 0, "drive": None, "start": None, "attempt": None,
        "evidence": None, "undriven": False, "undriven_reason": "",
    }


def _reset_life(item: dict) -> None:
    item.update(drive=None, start=None, attempt=None, attempts=0, deferrals=0)


def _apply(item: dict, ev: dict) -> bool:
    """把一個事件套到項目上；回 `False`＝事件被忽略（終態項目、或對不上目前的 drive）。"""
    kind = ev["ev"]
    if item["state"] in TERMINAL:
        return False
    if kind == "drive":
        if item["kind"] not in ("auto", "observe") or item["state"] == "escalated":
            return False
        item.update(state="driven", drive=ev, start=None, attempt=None)
    elif kind == "start":
        d = item["drive"]
        if not d or ev.get("drive_seq") != d["seq"]:
            return False
        item["start"] = ev
    elif kind == "attempt":
        d = item["drive"]
        if ev.get("result") == "fail":
            item["attempts"] += 1
        elif ev.get("result") == "deferred" and ev.get("reason") == "interactive":
            item["deferrals"] += 1  # 只有 interactive 計；quota／busy／window_cap 不計（D-11）
        if not d or ev.get("drive_seq") != d["seq"]:
            return False
        item["attempt"] = ev
    elif kind == "close":
        item.update(state="closed", evidence=ev.get("evidence"))
    elif kind == "retire":
        item["state"] = "retired"
    elif kind == "escalate":
        item["state"] = "escalated"
    elif kind == "convert":
        item["kind"] = ev["kind"]
        item["check"] = ev.get("check", item["check"])
        item["due"] = ev.get("due", item["due"])
        item["why_not_auto"] = ev.get("why", item["why_not_auto"]) if ev["kind"] in (
            "human", "k1") else item["why_not_auto"]
        _reset_life(item)
        item["state"] = "listed" if ev["kind"] in ("human", "k1") else "open"
    return True


def driven_verdict(item: dict, params: dict, now: datetime,
                   sched_exists: Callable[[str], bool | None] | None) -> tuple[bool, str]:
    """`driven` 項目的憑證此刻是否有效；回 `(有效, 無效原因)`（DES §3.3 對帳表）。"""
    d, s, a = item["drive"], item["start"], item["attempt"]
    at = parse_ts(d.get("at")) if d else None
    if at is None:
        return False, "drive_without_at"
    if a is not None:  # attempt 之後 run-driver 還沒接上後續事件：只給 followup_grace
        ok = now < parse_ts(a["ts"]) + timedelta(minutes=params["followup_grace_minutes"])
        return ok, "" if ok else "followup_lapsed"
    if s is not None:  # 有 start 無 attempt：以 start 宣告的預算為界（pid 存活只作輔證，不作判準）
        ok = now < parse_ts(s["ts"]) + timedelta(minutes=s["budget_minutes"])
        return ok, "" if ok else "run_budget_exceeded"
    if now < at:
        alive = sched_exists(d.get("task", "")) if sched_exists else None
        return (alive is not False), "" if alive is not False else "scheduled_task_missing"
    ok = now < at + timedelta(minutes=params["start_grace_minutes"])
    return ok, "" if ok else "never_started"


def fold(events: list[dict], params: dict, now: datetime,
         sched_exists: Callable[[str], bool | None] | None = None) -> Folded:
    out = Folded()
    for ev in sorted(events, key=_sort_key):
        item = out.items.get(ev["id"])
        if ev["ev"] == "open":
            if item is None:
                out.items[ev["id"]] = _new_item(ev)
            else:
                out.orphans += 1  # 同 id 重複 open：以第一筆為準
            continue
        if item is None or not _apply(item, ev):
            out.orphans += 1
    for item in out.items.values():
        if item["state"] == "open":
            item["undriven"], item["undriven_reason"] = True, "no_drive"
        elif item["state"] == "driven":
            ok, why = driven_verdict(item, params, now, sched_exists)
            item["undriven"], item["undriven_reason"] = (not ok), why
    return out
