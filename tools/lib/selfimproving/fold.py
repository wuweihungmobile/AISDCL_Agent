"""SelfImproving 事件折疊：事件序列 → PROP／RUN／ATT／SUSPENDED／冷卻（TCS-P1 R34、R35）。

純函式、純標準庫：`status`、`card`、`export`、`check` 共用這一份折疊（不得有第二份）。輸入是依檔案
順序排列的事件 dict（形態問題由 `events.validate` 判；本檔對缺鍵或型別怪異的事件防禦性略過，
絕不拋例外），輸出的 `problems` 是 `events.transitions` 的原料（碼, subject, 說明）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

ACTIVE_STATES = ("proposed", "returned", "approved", "sandboxed", "verified")
_BAD_RESULTS = ("recurred", "rolled-back")
_NEEDS_PROP = ("card", "app.rollback", "mea.amend", "mea.report", "heldout.freeze", "app.sandbox",
               "app.verify", "app.promote", "mea.open", "mea.close")


@dataclass
class Prop:
    id: str
    rev: int
    state: str
    route: str
    cls: str
    action: str
    target: list
    sources: list
    run: str
    digest: str
    created_seq: int
    last_seq: int
    verdict: str | None = None
    flags: list = field(default_factory=list)
    last_dec: str | None = None
    rejected_seq: int | None = None
    unblocked: bool = False


@dataclass
class Run:
    id: str
    opened_seq: int
    trigger: str
    head_sha: str
    coords: list
    closed_seq: int | None = None
    outcome: object = None
    prop_ids: list = field(default_factory=list)
    research: tuple | None = None


@dataclass
class Att:
    id: str
    seq: int
    by: str
    type: str
    ev: dict
    settled: tuple | None = None


@dataclass
class Folded:
    props: dict = field(default_factory=dict)
    runs: dict = field(default_factory=dict)
    atts: dict = field(default_factory=dict)
    problems: list = field(default_factory=list)
    windows: list = field(default_factory=list)
    amends: dict = field(default_factory=dict)
    resumes: list = field(default_factory=list)
    research_events: list = field(default_factory=list)
    skip_reasons: dict = field(default_factory=lambda: {"quota-band": 0, "offline": 0,
                                                        "helmsman": 0})
    dec_count: int = 0
    suspended: dict | None = None
    cooldowns: list = field(default_factory=list)
    root_cause_changes: int = 0
    pending_windows: list = field(default_factory=list)


def _i(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _str(ev: dict, key: str) -> str | None:
    v = ev.get(key)
    return v if isinstance(v, str) else None


def _lst(v) -> list:
    return list(v) if isinstance(v, list) else []


def _illegal(f: Folded, subject: str, ev: dict, state: str | None = None) -> None:
    extra = f" state={state}" if state else ""
    f.problems.append(("TRANSITION-ILLEGAL", subject,
                       f"seq={ev.get('seq')} kind={ev.get('kind')}{extra}"))


def _orphan(f: Folded, ev: dict, key: str) -> None:
    f.problems.append(("TRANSITION-ORPHAN", f"seq={ev.get('seq')}",
                       f"{ev.get('kind')} 的 {key} 指向不存在的對象"))


def _open_run(f: Folded, ev: dict) -> None:
    rid = _str(ev, "run")
    if rid is None or rid in f.runs:
        return
    f.runs[rid] = Run(rid, ev["seq"], str(ev.get("trigger")), str(ev.get("head_sha")),
                      _lst(ev.get("coords")))


def _close_run(f: Folded, ev: dict) -> None:
    rid = _str(ev, "run")
    run = f.runs.get(rid) if rid else None
    if run is None or run.closed_seq is not None:
        _illegal(f, rid or f"seq={ev.get('seq')}", ev)
        return
    run.closed_seq = ev["seq"]
    run.outcome = "no_event" if ev.get("no_event") is True else ev.get("outcomes")


def _attr(f: Folded, ev: dict) -> None:
    aid = _str(ev, "id")
    if aid and aid not in f.atts:
        f.atts[aid] = Att(aid, ev["seq"], str(ev.get("by")), str(ev.get("type")), ev)


def _settle(f: Folded, ev: dict) -> None:
    aid = _str(ev, "att")
    att = f.atts.get(aid) if aid else None
    if att is None:
        return _orphan(f, ev, "att")
    if att.settled is not None:
        _illegal(f, att.id, ev)
    else:
        att.settled = (ev["kind"], ev["seq"], ev.get("by"))
    if ev.get("by") == att.by:
        f.problems.append(("CONFIRMER-IS-PROPOSER", att.id,
                           f"seq={ev.get('seq')} {ev.get('kind')} 的 by 等於 attr 的 by"))


def _prop_event(f: Folded, ev: dict) -> None:
    pid, rev = _str(ev, "id"), ev.get("rev")
    if pid is None or not _i(rev):
        return
    run = f.runs.get(_str(ev, "run") or "")
    if run is None or run.closed_seq is not None:
        _illegal(f, pid, ev)
    cur = f.props.get(pid)
    ok = (cur is None and rev == 1) or (cur is not None and cur.state == "returned"
                                        and rev == cur.rev + 1)
    if not ok:
        return _illegal(f, pid, ev, cur.state if cur else None)
    fields = dict(rev=rev, state="proposed", route=str(ev.get("route")), cls=str(ev.get("cls")),
                  action=str(ev.get("action")), target=_lst(ev.get("target")),
                  sources=_lst(ev.get("sources")), run=str(ev.get("run")),
                  digest=str(ev.get("digest")), last_seq=ev["seq"], verdict=None, flags=[])
    if cur is None:
        f.props[pid] = Prop(id=pid, created_seq=ev["seq"], **fields)
    else:
        for k, v in fields.items():
            setattr(cur, k, v)
    if run is not None and pid not in run.prop_ids:
        run.prop_ids.append(pid)


def _dec_flags(ev: dict) -> list:
    v = ev.get("flags")
    return [v] if isinstance(v, str) else _lst(v)


def _dec(f: Folded, ev: dict) -> None:
    f.dec_count += 1
    dk = _str(ev, "dkind")
    if dk == "resume":
        rid = _str(ev, "run")
        if rid not in f.runs:
            return _orphan(f, ev, "run")
        f.resumes.append(ev["seq"])
        return
    p = f.props.get(_str(ev, "prop") or "")
    if p is None or dk is None:
        return _orphan(f, ev, "prop" if p is None else "dkind")
    st, seq = p.state, ev["seq"]
    flags = _dec_flags(ev)
    new = None
    if dk == "approve" and st == "proposed" and p.route == "loop":
        new = "approved"
    elif dk == "reject" and st == "proposed":
        new = "rejected"
    elif dk == "decline-promote" and st == "verified":
        new = "rejected"
    elif dk == "return" and (st == "proposed" or (st == "verified" and p.verdict == "FAIL")):
        new = "returned"
    elif dk == "ack-handoff" and st == "proposed" and p.route.startswith("handoff:"):
        new = "handed-off"
    elif dk == "unblock" and st == "rejected":
        new, p.unblocked = "rejected", True
    elif dk == "promote" and st == "verified" and (
            p.verdict == "PASS" or (p.verdict == "NE" and "unverified_ack" in flags)):
        new = "verified"
    elif dk == "rollback" and st in ("promoted", "measuring", "closed"):
        new = st
    if new is None:
        return _illegal(f, p.id, ev, st)
    if new == "rejected" and dk != "unblock":
        p.rejected_seq, p.unblocked = seq, False
    p.state, p.last_dec, p.last_seq = new, dk, seq
    p.flags = sorted(set(p.flags) | set(flags))


def _step(f: Folded, ev: dict, want: str, new: str | None) -> Prop | None:
    p = f.props.get(_str(ev, "prop") or "")
    if p is None:
        _orphan(f, ev, "prop")
        return None
    p.last_seq = ev["seq"]
    if new is not None and p.state != want:
        _illegal(f, p.id, ev, p.state)
        return None
    return p


def _apply(f: Folded, ev: dict) -> None:
    kind = ev["kind"]
    if kind == "run.open":
        _open_run(f, ev)
    elif kind == "run.close":
        _close_run(f, ev)
    elif kind in ("research.scan", "research.skip"):
        f.research_events.append((ev["seq"], kind, _str(ev, "run"), ev))
        run = f.runs.get(_str(ev, "run") or "")
        if run is not None and run.research is None:
            run.research = (kind, ev["seq"])
        if kind == "research.skip" and ev.get("reason") in f.skip_reasons:
            f.skip_reasons[ev["reason"]] += 1
    elif kind == "attr":
        _attr(f, ev)
    elif kind in ("attr.confirm", "attr.reject"):
        _settle(f, ev)
    elif kind == "prop":
        _prop_event(f, ev)
    elif kind == "dec":
        _dec(f, ev)
    elif kind in _NEEDS_PROP:
        _prop_transition(f, ev, kind)


def _prop_transition(f: Folded, ev: dict, kind: str) -> None:
    table = {"app.sandbox": ("approved", "sandboxed"), "app.verify": ("sandboxed", "verified"),
             "app.promote": ("verified", "promoted"), "mea.open": ("promoted", "measuring")}
    if kind in table:
        p = _step(f, ev, *table[kind])
        if p is None:
            return
        if kind == "app.promote" and p.last_dec != "promote":
            return _illegal(f, p.id, ev, p.state)
        if kind == "app.verify":
            if ev.get("verdict") not in ("PASS", "FAIL", "NE"):
                return _illegal(f, p.id, ev, p.state)
            p.verdict = ev["verdict"]
        p.state = table[kind][1]
    elif kind == "mea.close":
        p = _step(f, ev, "measuring", "closed")
        res = ev.get("result")
        if p is None or res not in ("clean", "recurred", "rolled-back", "pending"):
            if p is not None:
                _illegal(f, p.id, ev, p.state)
            return
        f.windows.append({"prop": p.id, "seq": ev["seq"], "result": res})
        p.state = "measuring" if res == "pending" else "closed"
    else:
        p = _step(f, ev, "", None)
        if p is not None and kind == "mea.amend" and _i(ev.get("window")):
            f.amends[ev["window"]] = ev.get("to")


def _effective_windows(f: Folded) -> list[dict]:
    return [dict(w, effective=f.amends.get(w["seq"], w["result"])) for w in f.windows]


def _prop_root_causes(f: Folded, sources: list) -> list[str]:
    out = {a.ev.get("root_cause") for a in f.atts.values()
           if a.type == "root" and set(_lst(a.ev.get("obs"))) & set(sources)
           and isinstance(a.ev.get("root_cause"), str)}
    return sorted(out)


def prop_root_causes(f: Folded, sources: list) -> list[str]:
    """PROP 的根因鍵集合：obs 與該 PROP sources 有交集的 attr（root）事件的 root_cause。"""
    return _prop_root_causes(f, sources)


def _finish(f: Folded, stop_after_bad: int | None) -> None:
    wins = _effective_windows(f)
    f.pending_windows = [{"prop": w["prop"], "close_seq": w["seq"]} for w in wins
                         if w["effective"] == "pending"]
    settled = [w for w in wins if w["effective"] != "pending"]
    if _i(stop_after_bad) and stop_after_bad >= 1 and len(settled) >= stop_after_bad:
        tail = settled[-stop_after_bad:]
        last = tail[-1]["seq"]
        if all(w["effective"] in _BAD_RESULTS for w in tail) and not any(
                s > last for s in f.resumes):
            prior = [r for r in f.runs.values() if r.opened_seq < last]
            if prior:
                f.suspended = {"run": max(prior, key=lambda r: r.opened_seq).id}
    for p in f.props.values():
        if p.state == "rejected" and not p.unblocked and p.rejected_seq is not None:
            f.cooldowns.append({"prop": p.id, "cls": p.cls, "target": list(p.target),
                                "root_cause": _prop_root_causes(f, p.sources),
                                "rejected_seq": p.rejected_seq})
    by_obs: dict[str, list] = {}
    for a in f.atts.values():
        if a.type == "root" and isinstance(a.ev.get("root_cause"), str):
            for obs in _lst(a.ev.get("obs")):
                by_obs.setdefault(obs, []).append((a.seq, a.ev["root_cause"]))
    for seq_causes in by_obs.values():
        causes = [c for _, c in sorted(seq_causes)]
        f.root_cause_changes += sum(1 for x, y in zip(causes, causes[1:]) if x != y)


def fold(events: list[dict], stop_after_bad: int | None = None) -> Folded:
    f = Folded()
    for ev in events:
        if isinstance(ev, dict) and _i(ev.get("seq")) and isinstance(ev.get("kind"), str):
            _apply(f, ev)
    _finish(f, stop_after_bad)
    return f


def effective_windows(f: Folded) -> list[dict]:
    return _effective_windows(f)
