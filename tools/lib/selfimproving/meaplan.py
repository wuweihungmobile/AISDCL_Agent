"""SelfImproving `measure` 的規劃與 `pending`／晚到確認的 `mea.amend` 判準（TCS-P3 R120～R122）。

能力類別 `ro`、純函式：`measure`、`attr-confirm`／`attr-reject` 的同鎖追加、`status.measure.due` 與
量測探針共用同一份（單一窗規則實作，不得有第二份）。每個 promoted PROP 一次至多產出一個「下一個
應追加的事件」：基線報告 → 開窗 → 關窗 → 更正（amend）；事件 dict 不含 `seq`、`t`、`by`。
"""

from __future__ import annotations

from . import fold as si_fold
from . import mea as si_mea
from . import meacheck

REASONS = ("ANCHOR-UNAVAILABLE", "OBS-LEDGER-UNAVAILABLE", "DEFECT-LEDGER-UNAVAILABLE")


def amend_for(ctx: si_mea.Ctx, p: si_mea.Prop, win: dict) -> dict | None:
    """R121 (b)(c)：已關閉窗的更正；生效結果為 `recurred` 者不再更正。"""
    eff, at = win["effective"], si_mea.parse_t(win["at"])
    if eff == "recurred" or at is None:
        return None
    states = [(r, *si_mea.cand_state(ctx, r.id)) for r in ctx.rows
              if r.at > p.at and (o := si_mea.owner_of(ctx, r)) is not None and o.id == p.id]
    if eff == "pending":
        mine = [(s, q) for r, s, q in states if r.at <= at]
        if not mine or any(s == "open" for s, _ in mine):
            return None
        to = "recurred" if any(s == "confirmed" for s, _ in mine) else "clean"
        cause = max(q for _, q in mine)
    else:
        late = [q for r, s, q in states if s == "confirmed" and r.at < at and q > win["seq"]]
        if not late:
            return None
        to, cause = "recurred", min(late)
    return {"kind": "mea.amend", "prop": p.id, "window": win["seq"], "from": eff, "to": to,
            "cause": cause}


def _baseline_event(ctx: si_mea.Ctx, p: si_mea.Prop) -> dict:
    prm, b = ctx.params, si_mea.baseline(ctx, p)
    return {"kind": "mea.report", "prop": p.id, "report": "baseline", "promote_seq": p.seq,
            "opp": b["opp"], "events": b["events"], "pending": b["pending"],
            "w_opp": prm["w_opp"], "w_evt": prm["w_evt"], "w_min": prm["w_min"],
            "anchor": b["anchor"]}


def baselines(ctx: si_mea.Ctx) -> dict:
    """每個 PROP 的第一筆基線報告事件。"""
    out: dict = {}
    for e in ctx.events:
        if e["kind"] == "mea.report" and e.get("report") == "baseline":
            out.setdefault(e.get("prop"), e)
    return out


def first_windows(ctx: si_mea.Ctx) -> dict:
    """每個 PROP 的第一個已關閉窗（含 `effective` 生效結果、`n_opp`、`at`、`seq`）。"""
    out: dict = {}
    for w in si_fold.effective_windows(ctx.f):
        out.setdefault(w["prop"], w)
    return out


def rollback_pending(ctx: si_mea.Ctx) -> list[str]:
    """R123 (a)：生效結果為 `recurred` 且尚無 `dec(rollback)` 的 promoted PROP（依 PROP 號）。"""
    wins = first_windows(ctx)
    return [p.id for p in ctx.props if p.id in wins and wins[p.id]["effective"] == "recurred"
            and not ctx.rollbacks.get(p.id)]


def plan(ctx: si_mea.Ctx) -> list[dict]:
    """R122 (a)：依 PROP 號升冪、每個 promoted PROP 的下一個應追加事件（無則略過）。"""
    base = baselines(ctx)
    opens: dict = {}
    for e in ctx.events:
        if e["kind"] == "mea.open":
            opens.setdefault(e.get("prop"), e.get("w_opp"))
    wins = first_windows(ctx)
    out: list[dict] = []
    for p in ctx.props:
        state = ctx.f.props[p.id].state
        if p.id not in base:
            out.append(_baseline_event(ctx, p))
        elif state == "promoted":
            out.append({"kind": "mea.open", "prop": p.id, "w_opp": ctx.params["w_opp"],
                        "promote_seq": p.seq})
        elif p.id not in wins:
            w_opp = opens.get(p.id)
            close = si_mea.window(ctx, p, w_opp)["close"] if isinstance(w_opp, int) else None
            if close is not None:
                out.append({"kind": "mea.close", "prop": p.id, **close})
        elif (ev := amend_for(ctx, p, wins[p.id])) is not None:
            out.append(ev)
    return out


def input_problems(ctx: si_mea.Ctx, events: list[dict]) -> list[str]:
    """R122 (d)：要追加事件卻缺輸入時的拒收碼（無事件＝不需任何輸入）。"""
    if not events:
        return []
    out = []
    if any(e["kind"] == "mea.report" and e.get("anchor") is None for e in events):
        out.append(REASONS[0])
    if not ctx.obs_ok:
        out.append(REASONS[1])
    if not ctx.def_ok:
        out.append(REASONS[2])
    return out

def window_rows(ctx: si_mea.Ctx) -> list[dict]:
    """有 `mea.open` 的 PROP 的窗摘要（依 PROP 號）：狀態、生效結果、機會列數、基線與未決候選數。"""
    opens: dict = {}
    for e in ctx.events:
        if e["kind"] == "mea.open":
            opens.setdefault(e.get("prop"), e)
    base, wins = baselines(ctx), first_windows(ctx)
    out = []
    for p in ctx.props:
        op = opens.get(p.id)
        if op is None or ctx.f.props[p.id].state not in ("measuring", "closed"):
            continue
        w, b = wins.get(p.id), base.get(p.id)
        live = si_mea.window(ctx, p, op["w_opp"]) if w is None else None
        out.append({
            "prop": p.id, "state": "pending" if w and w["effective"] == "pending"
            else ctx.f.props[p.id].state, "result": w["effective"] if w else None,
            "n_opp": w["n_opp"] if w else live["opp"], "w_opp": op["w_opp"],
            "baseline": {"events": b["events"], "opp_n": len(b["opp"]), "pending": b["pending"]}
            if b else None, "unsettled": len(live["pending"]) if live else 0,
            "opened_seq": op["seq"], "closed_seq": w["seq"] if w else None})
    return out


def unsettled_candidates(ctx: si_mea.Ctx) -> int:
    """歸屬於某 promoted PROP 而尚未落定的 OBS 候選數。"""
    return sum(1 for r in ctx.rows if si_mea.owner_of(ctx, r) is not None
               and si_mea.cand_state(ctx, r.id)[0] == "open")

def export_window(events: list[dict], f: si_fold.Folded, prop: str) -> dict | None:
    """R130 (e)：`export` proposals 的 `window`（只讀事件、不讀帳本）；無 `mea.open` 為 None。"""
    opened = next((e for e in events if e["kind"] == "mea.open" and e.get("prop") == prop), None)
    if opened is None or {None, prop} & meacheck.bad_props(events):
        return None
    win = next((w for w in si_fold.effective_windows(f) if w["prop"] == prop), None)
    base = next((e for e in events if e["kind"] == "mea.report" and e.get("report") == "baseline"
                 and e.get("prop") == prop), None)
    state = "pending" if win and win["effective"] == "pending" else f.props[prop].state
    return {"state": state, "opened_seq": opened["seq"],
            "closed_seq": win["seq"] if win else None, "result": win["effective"] if win else None,
            "n_opp": win["n_opp"] if win else None,
            "baseline": {"events": base["events"], "opp_n": len(base["opp"]),
                         "pending": base["pending"]} if base else None}
