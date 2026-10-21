"""SelfImproving 事件折疊：事件序列 → PROP／RUN／ATT／SUSPENDED／冷卻（TCS-P1 R34、R35）。

純函式、純標準庫：`status`、`card`、`export`、`check` 共用這一份折疊（不得有第二份）。輸入是依檔案
順序排列的事件 dict（形態問題由 `events.validate` 判；`fold` 只吃通過它的事件，其餘略過、
絕不拋例外），輸出的 `problems` 是 `events.transitions` 的原料（碼, subject, 說明）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import events as si_events

ACTIVE_STATES = ("proposed", "returned", "approved", "sandboxed", "verified")
_BAD_RESULTS = ("recurred", "rolled-back")
_NEEDS_PROP = ("card", "app.rollback", "mea.amend", "mea.report", "heldout.freeze", "app.sandbox",
               "app.verify", "app.promote", "mea.open", "mea.close")
_RETURN_NE = ("SANDBOX-NOT-APPLIED", "TOUCHED-SUPERSET", "SANDBOX-EXPORT-FAILED",
              "SANDBOX-APPLY-TIMEOUT")
_DIGEST_KINDS = ("approve", "reject", "return", "promote", "decline-promote", "ack-handoff")
_POST_PROMOTE = ("promoted", "measuring", "closed")


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
    reasons: list = field(default_factory=list)
    rollback_ok: bool | None = None
    touched_ok: bool | None = None
    proposer: str = ""
    bases: dict = field(default_factory=dict)
    reject_class: str | None = None
    pending_promote: list | None = None
    pending_rollbacks: int = 0
    promote_pre: str | None = None
    promote_post: str | None = None
    freeze_seq: int | None = None
    sandbox_seq: int | None = None
    verify_counts: dict = field(default_factory=dict)


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
    warns: list = field(default_factory=list)
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
                  digest=str(ev.get("digest")), last_seq=ev["seq"], verdict=None, flags=[],
                  reasons=[], rollback_ok=None, touched_ok=None,
                  proposer=str(ev.get("proposer")))
    if cur is None:
        _cooldown_bypass(f, pid, fields)
        cur = f.props[pid] = Prop(id=pid, created_seq=ev["seq"], **fields)
    else:
        for k, v in fields.items():
            setattr(cur, k, v)
    cur.bases[rev] = str(ev.get("base"))
    if run is not None and pid not in run.prop_ids:
        run.prop_ids.append(pid)


def _cooldown_bypass(f: Folded, pid: str, fields: dict) -> None:
    """R82 (f)：新 `prop`（rev 1）之前已有同型（cls、target、根因鍵相交）且冷卻中的 PROP。"""
    roots = set(_prop_root_causes(f, fields["sources"]))
    for q in f.props.values():
        if (q.state == "rejected" and not q.unblocked and q.cls == fields["cls"]
                and sorted(set(q.target)) == sorted(set(fields["target"]))
                and roots & set(_prop_root_causes(f, q.sources))):
            f.warns.append(("COOLDOWN-BYPASS-SUSPECT", pid,
                            f"與冷卻中的 {q.id} 同型（cls、target、根因鍵相交）而再出現"))


def transition_of(p: Prop, dk: str, flags: list) -> str | None:
    """R75 的 `dec` 前提判定（唯一實作；`decide` 寫入端與重放共用）：回結果態，不合回 None。"""
    ack = "unverified_ack" in flags
    st, form_ok = p.state, (p.verdict == "PASS" and not ack) or (p.verdict == "NE" and ack)
    if dk == "approve" and st == "proposed" and p.route == "loop":
        return "approved"
    if st == "proposed" and dk in ("reject", "return"):
        return "rejected" if dk == "reject" else "returned"
    if dk == "ack-handoff" and st == "proposed" and p.route.startswith("handoff:"):
        return "handed-off"
    if dk == "return" and st == "verified" and (
            p.verdict == "FAIL" or (p.verdict == "NE" and set(p.reasons) & set(_RETURN_NE))):
        return "returned"
    if dk == "decline-promote" and st == "verified":
        return "rejected"
    if dk == "unblock" and st == "rejected" and not p.unblocked:
        return "rejected"
    if dk == "promote" and st == "verified" and form_ok:
        return "verified" if p.rollback_ok is True and p.touched_ok is True else None
    if dk == "rollback" and st in _POST_PROMOTE:
        return st
    return None


def _dec_flags(ev: dict) -> list:
    return _lst(ev.get("flags"))  # `sound()` 已保證元素皆 str（裸字串不是合法形態）


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
    seq, flags = ev["seq"], _dec_flags(ev)
    if dk in _DIGEST_KINDS and ev.get("digest") != p.digest:
        f.problems.append(("DEC-TARGET-MISMATCH", p.id, f"seq={seq} dec 的 digest 不等於當時 PROP"))
    new = transition_of(p, dk, flags)
    if new is None:
        return _illegal(f, p.id, ev, p.state)
    if new == "rejected" and dk != "unblock":
        p.rejected_seq, p.unblocked = seq, False
        p.reject_class = ev.get("reason_class") if isinstance(ev.get("reason_class"), str) else None
    if dk == "unblock":
        p.unblocked = True
    if dk == "promote":
        p.pending_promote = flags
    elif dk == "rollback":
        p.pending_rollbacks += 1
    else:
        p.pending_promote = None
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


def _apply(f: Folded, ev: dict, vmax: int | None = None) -> None:
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
        _prop_transition(f, ev, kind, vmax)


def _bad(f: Folded, p: Prop, ev: dict, code: str, why: str) -> None:
    f.problems.append((code, p.id, f"seq={ev.get('seq')} {why}"))


def _sandbox(f: Folded, ev: dict, p: Prop) -> None:
    if p.freeze_seq is None:
        _bad(f, p, ev, "HELDOUT-AFTER-SANDBOX", "app.sandbox 之前沒有 heldout.freeze")
    if p.bases.get(ev.get("rev")) != ev.get("base"):
        _bad(f, p, ev, "SANDBOX-BASE-MISMATCH", "app.sandbox.base 不等於該 rev 的 prop.base")
    p.rollback_ok, p.touched_ok = ev.get("rollback_ok"), ev.get("touched_ok")
    p.sandbox_seq = p.sandbox_seq if p.sandbox_seq is not None else ev["seq"]


def _verify(f: Folded, ev: dict, p: Prop, vmax: int | None) -> None:
    n = p.verify_counts[ev.get("rev")] = p.verify_counts.get(ev.get("rev"), 0) + 1
    if _i(vmax) and n > vmax:
        _bad(f, p, ev, "VERIFY-RUNS-EXCEEDED", f"同 (prop, rev) 的 app.verify 第 {n} 筆 > {vmax}")
    p.verdict, p.reasons = ev["verdict"], _lst(ev.get("reasons"))


def _promote(f: Folded, ev: dict, p: Prop) -> bool:
    if p.pending_promote is None:
        _illegal(f, p.id, ev, p.state)
        return False
    if bool(ev.get("unverified_ack")) != ("unverified_ack" in p.pending_promote):
        _bad(f, p, ev, "PROMOTE-ACK-MISMATCH", "unverified_ack 不等於所消費 dec(promote) 的 flags")
    p.pending_promote, p.promote_pre, p.promote_post = None, ev.get("pre_sha256"), ev.get(
        "post_sha256")
    return True


def _rollback(f: Folded, ev: dict, p: Prop) -> None:
    if p.state not in _POST_PROMOTE or p.pending_rollbacks < 1:
        return _illegal(f, p.id, ev, p.state)
    p.pending_rollbacks -= 1
    if ev.get("pre_sha256") != p.promote_post or ev.get("post_sha256") != p.promote_pre:
        _bad(f, p, ev, "ROLLBACK-MANIFEST-MISMATCH", "pre／post 與 app.promote 的 post／pre 不符")


def _freeze(f: Folded, ev: dict, p: Prop) -> None:
    if ev.get("frozen_by") == p.proposer:
        _bad(f, p, ev, "FROZEN-BY-PROPOSER", "凍結者等於該 PROP 的提案者")
    if p.freeze_seq is not None:
        _bad(f, p, ev, "HELDOUT-DUP", "同一 PROP 已有 heldout.freeze")
    if p.sandbox_seq is not None:
        _bad(f, p, ev, "HELDOUT-AFTER-SANDBOX", "heldout.freeze 晚於 app.sandbox")
    p.freeze_seq = p.freeze_seq if p.freeze_seq is not None else ev["seq"]


def _prop_transition(f: Folded, ev: dict, kind: str, vmax: int | None = None) -> None:
    table = {"app.sandbox": ("approved", "sandboxed"), "app.promote": ("verified", "promoted"),
             "mea.open": ("promoted", "measuring")}
    if kind == "app.verify":
        p = _step(f, ev, "", None)
        if p is None or p.state not in ("sandboxed", "verified"):
            return None if p is None else _illegal(f, p.id, ev, p.state)
        _verify(f, ev, p, vmax)
        p.state = "verified"
    elif kind in table:
        p = _step(f, ev, *table[kind])
        if p is None or (kind == "app.promote" and not _promote(f, ev, p)):
            return
        if kind == "app.sandbox":
            _sandbox(f, ev, p)
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
        if p is None:
            return
        if kind == "mea.amend" and _i(ev.get("window")):
            f.amends[ev["window"]] = ev.get("to")
        elif kind == "app.rollback":
            _rollback(f, ev, p)
        elif kind == "heldout.freeze":
            _freeze(f, ev, p)


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
                                "rejected_seq": p.rejected_seq,
                                "reason_class": p.reject_class})
    by_obs: dict[str, list] = {}
    for a in f.atts.values():
        if a.type == "root" and isinstance(a.ev.get("root_cause"), str):
            for obs in _lst(a.ev.get("obs")):
                by_obs.setdefault(obs, []).append((a.seq, a.ev["root_cause"]))
    for seq_causes in by_obs.values():
        causes = [c for _, c in sorted(seq_causes)]
        f.root_cause_changes += sum(1 for x, y in zip(causes, causes[1:]) if x != y)


def fold(events: list[dict], stop_after_bad: int | None = None,
         verify_runs_max: int | None = None) -> Folded:
    f = Folded()
    for ev in si_events.sound(events):
        _apply(f, ev, verify_runs_max)
    _finish(f, stop_after_bad)
    return f


def effective_windows(f: Folded) -> list[dict]:
    return _effective_windows(f)
