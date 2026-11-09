"""SelfImproving `check` 的 P4 追加項：`sched.events` 與 `run.trigger_f_has_patrol_by`
（TCS-SelfImproving-P4 R140）。

能力類別 `ro`：只讀事件與 `params.json`（不讀 OBS／DEF 帳本、不呼叫 git、不讀家目錄）。輸入是**未過
單事件判準**的事件（缺鍵的 `run.open(f)` 也要能被判出 `TRIGGER-F-DUE-AT`），本檔只取判準需要的欄位，
型別不合者不參與（形態問題由 `events.structure` 報）。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import events as si_events
from . import params as si_params
from . import sched as si_sched
from .ledger import Finding

ITEMS = ("sched.events", "run.trigger_f_has_patrol_by")
_KEYS = ("sched_period_minutes_default", "sched_period_minutes_min", "sched_period_minutes_max")


def _usable(e: dict) -> bool:
    """能參與判準的事件：共通鍵合法且（sched.set）enabled／period 型別合法。"""
    if not (isinstance(e, dict) and si_events._int(e.get("seq"), 1)
            and si_events.valid_t(e.get("t")) and isinstance(e.get("by"), str)):
        return False
    if e.get("kind") == "sched.set":
        return isinstance(e.get("enabled"), bool) and si_events._int(e.get("period_minutes"), 1)
    return e.get("kind") in ("run.open", "sched.skip")


def _t(text) -> datetime | None:
    return datetime.fromisoformat(text) if si_events.valid_t(text) else None


def _cell_key(events: list[dict], default: int, e: dict):
    """事件 `e` 之前的重置事件所定的格：(origin seq, period, k)；停用／無 origin／倒退＝None。"""
    st = si_sched.state_of(events, default, before_seq=e["seq"])
    cell = si_sched.cell_bounds(st, datetime.fromisoformat(e["t"]))
    if cell is None:
        return None
    return st.origin["seq"], st.period, cell[0]


def sched_events(events: list[dict], params: dict) -> list[Finding]:
    default, lo, hi = (params[k] for k in _KEYS)
    out: list[Finding] = []
    seen_run: dict = {}
    seen_skip: dict = {}
    for e in events:
        sub = f"seq={e['seq']}"
        kind = e["kind"]
        if kind == "sched.set" and not lo <= e["period_minutes"] <= hi:
            out.append(Finding(sub, "SCHED-PERIOD-RANGE", "fail",
                               f"period_minutes {e['period_minutes']} 不在 [{lo}, {hi}]"))
        elif kind == "run.open" and e.get("trigger") == "f":
            key = _cell_key(events, default, e)
            if key is not None and seen_run.setdefault(key, e["seq"]) != e["seq"]:
                out.append(Finding(sub, "SCHED-RUN-DUP", "fail",
                                   "同一格內 trigger f 的運轉不止一筆"))
        elif kind == "sched.skip":
            out += _skip_findings(events, default, e, sub, seen_skip)
    return out


def _skip_findings(events: list[dict], default: int, e: dict, sub: str, seen: dict
                   ) -> list[Finding]:
    if "carrier" in e:  # Console 載體：以 audit_ref 判（同一 audit_ref 超過一筆）
        ref = ("console", e.get("audit_ref"))
        dup = seen.setdefault(ref, e["seq"]) != e["seq"]
        return [Finding(sub, "SCHED-SKIP-DUP", "fail", "同一 audit_ref 的 Console skip 不止一筆")
                ] if dup and e.get("audit_ref") else []
    key = _cell_key(events, default, e)
    due = _t(e.get("due_at"))
    out: list[Finding] = []
    if key is None or due is None or due != key[2]:
        out.append(Finding(sub, "SCHED-SKIP-DUE", "fail", "due_at 不是其 t 所在格的起點"))
    if key is not None and seen.setdefault((key, e.get("reason")), e["seq"]) != e["seq"]:
        out.append(Finding(sub, "SCHED-SKIP-DUP", "fail", "同一格同一 reason 的 skip 不止一筆"))
    return out


def trigger_f(events: list[dict], params: dict) -> list[Finding]:
    default = params["sched_period_minutes_default"]
    out: list[Finding] = []
    for e in events:
        if e["kind"] != "run.open" or e.get("trigger") != "f":
            continue
        sub = f"seq={e['seq']}"
        if e["by"] != "patrol":
            out.append(Finding(sub, "TRIGGER-F-BY", "fail", "trigger f 的 by 不是 patrol"))
        st = si_sched.state_of(events, default, before_seq=e["seq"])
        due, origin = _t(e.get("due_at")), st.origin_dt
        if origin is None:
            out.append(Finding(sub, "TRIGGER-F-NO-ORIGIN", "fail", "之前沒有任何重置事件"))
        elif due is None or due < origin or (due - origin) % timedelta(minutes=st.period):
            out.append(Finding(sub, "TRIGGER-F-DUE-AT", "fail",
                               "due_at 缺或不是 origin 起算的整數個週期"))
    return out


def findings(events: list[dict], params: dict, valid: set[str]) -> dict:
    """項目 ID → (findings, detail)；`events` 為帳本內全部已解析事件（含未過單事件判準者）。"""
    if not set(_KEYS) <= valid:
        ne = si_params.ne_findings("sched 週期參數無效")
        return {i: (list(ne), "") for i in ITEMS}
    use = sorted((e for e in events if _usable(e)), key=lambda e: e["seq"])
    return {ITEMS[0]: (sched_events(use, params), ""), ITEMS[1]: (trigger_f(use, params), "")}
