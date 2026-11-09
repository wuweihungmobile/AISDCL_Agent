"""SelfImproving 排程寫入：`sched set`、`run-open` 的 `--trigger f`／Console `run-request` 載體與
`sched.skip` 追加（TCS-SelfImproving-P4 R137、R138、R141、R146、R147、R144）。

能力類別 `rw`：判準呼叫 `ro` 模組（`sched`、`consoleaudit`、`unattended`、`decverify`），寫入只經
`evwrite.append_event`（寫入鎖內重驗後單次追加）；零殘留＝拒收時事件帳本位元組不變。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import consoleaudit, decverify, decwrite, evwrite, obsrows
from . import events as si_events
from . import params as si_params
from . import rows as si_rows
from . import sched as si_sched
from . import writeverbs as wv
from .git import Git

UsageError = wv.UsageError
_BASE_KEYS = ("event_max_bytes", *si_params.SCHED_KEYS)


def current_time() -> datetime:
    """`run-open --trigger f` 判本格起點用的現在時刻（唯一讀系統時鐘處；測試以 mock 注入）。"""
    return datetime.now().astimezone()


def _ref_reused(repo: Path, events: list[dict], ref: str) -> bool:
    return any(e.get("audit_ref") == ref for e in events) or obsrows.ref_used(repo, events, ref)


def _console_audit(repo: Path, verb: str, ref: str, kind: str, params: dict, as_json: bool):
    """Console 載體共同前置：回 (稽核檔, 事件) 或拒收 `Out`（驗簽→kind→重複→本文判準）。"""
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise UsageError(f"HOME-UNWRITABLE {exc}") from exc
    try:
        audit = consoleaudit.verify(consoleaudit.audit_path(si, ref))
    except consoleaudit.AuditError as exc:
        return wv.reject(repo, verb, [(exc.code, exc.detail)], as_json)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    early = []
    if _ref_reused(repo, events, ref):
        early = [("AUDIT-REF-REUSED", f"audit_ref {ref} 已入帳過")]
    elif audit.body["kind"] != kind:
        early = [("AUDIT-KIND-MISMATCH", f"稽核檔 kind 為 {audit.body['kind']}，"
                                         f"{verb} 只收 {kind}")]
    bounds = (params["sched_period_minutes_min"], params["sched_period_minutes_max"])
    codes = early or consoleaudit.body_guard(kind, audit.body, bounds=bounds)
    if codes:
        return wv.reject(repo, verb, codes, as_json)
    return audit, events


def _console_keys(audit: consoleaudit.Audit, ref: str) -> dict:
    return {"audit_ref": ref, "audit_sha256": audit.sha, "key_id": audit.key_id,
            "decider": audit.body["user"]}


def _reused_in_lock(state, ref: str) -> None:
    if any(e.get("audit_ref") == ref for e in state.events):
        raise evwrite.Reject([("AUDIT-REF-REUSED", "寫入鎖內重驗：audit_ref 已入帳")])


# ── sched set ─────────────────────────────────────────────────────────────────
def _set_usage(ns) -> None:
    wv._label(ns.by, "--by")
    if ns.carrier == "console":
        if ns.audit_ref is None or not si_events.valid_uuid(ns.audit_ref):
            raise UsageError("--carrier console 須帶 --audit-ref（UUID）")
        given = (ns.sid, ns.line, ns.enabled, ns.period_minutes, ns.reason)
        if any(v is not None for v in given):
            raise UsageError("--carrier console 不收 --enabled／--period-minutes／--reason／"
                             "--sid／--line（內容取自稽核檔）")
        return
    if ns.audit_ref is not None:
        raise UsageError("--audit-ref 只配 --carrier console")
    if ns.enabled is None:
        raise UsageError("sched set 須帶 --enabled {true|false}")
    if (ns.sid is None) != (ns.line is None):
        raise UsageError("--sid 與 --line 須成對")
    if ns.sid is not None and (not si_events.valid_uuid(ns.sid) or ns.line < 1):
        raise UsageError("--sid 須為 UUID 正規形、--line 須為整數 ≥1")


def sched_set(repo: Path, ns, as_json: bool) -> wv.Out:
    _set_usage(ns)
    params = wv.params_for(repo, *_BASE_KEYS)
    refused = decwrite.refuse_unattended(repo, "sched-set", as_json, ns)
    if refused:
        return refused
    if ns.carrier == "console":
        got = _console_audit(repo, "sched", ns.audit_ref, "sched-set", params, as_json)
        if isinstance(got, wv.Out):
            return got
        audit, _ = got
        body = audit.body
        event = {"kind": "sched.set", "by": ns.by, "enabled": body["enabled"],
                 "period_minutes": body["period_minutes"], "carrier": "console",
                 **({"reason": body["reason"]} if "reason" in body else {}),
                 **_console_keys(audit, ns.audit_ref)}
        return _append_set(repo, event, params, as_json, ns.audit_ref)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    st = si_sched.state_of(events, params["sched_period_minutes_default"])
    enabled = ns.enabled == "true"
    period = ns.period_minutes if ns.period_minutes is not None else st.period
    codes = [] if ns.reason is None else consoleaudit.text_codes("reason", ns.reason)
    if not params["sched_period_minutes_min"] <= period <= params["sched_period_minutes_max"]:
        codes.append(("PERIOD-OUT-OF-RANGE", f"period_minutes {period} 不在界內"))
    quote = ns.sid is not None
    if (enabled or period != st.period) and not quote:
        codes.append(("SCHED-QUOTE-REQUIRED", "啟用或改週期須人的引言（--sid／--line）或 Console"))
    if quote and not codes:
        v = decverify.verify_human_ref(repo, ns.sid, ns.line)
        codes += [] if v.status == "ok" else [(v.code, v.detail)]
    if codes:
        return wv.reject(repo, "sched", codes, as_json)
    event = {"kind": "sched.set", "by": ns.by, "enabled": enabled, "period_minutes": period,
             "carrier": "transcript" if quote else "host"}
    if ns.reason is not None:
        event["reason"] = ns.reason
    if quote:
        event.update(sid=ns.sid, line=ns.line)
    return _append_set(repo, event, params, as_json, None)


def _append_set(repo: Path, event: dict, params: dict, as_json: bool, ref: str | None) -> wv.Out:
    def build(state):
        if ref:
            _reused_in_lock(state, ref)
        return dict(event)

    def render(e):
        return decwrite.ok_out("sched.set", e["seq"], None, [
            ("enabled", e["enabled"]), ("period", e["period_minutes"]),
            ("carrier", e["carrier"])], as_json).text
    return wv.append(repo, "sched", build, params, as_json, render)


# ── run-open：--trigger f 與 Console run-request ──────────────────────────────
def _f_codes(events: list[dict], params: dict, ns, now: datetime) -> list[tuple[str, str]]:
    st = si_sched.state_of(events, params["sched_period_minutes_default"])
    codes = []
    if ns.by != "patrol":
        codes.append(("TRIGGER-F-BY", "trigger f 的 --by 必為 patrol"))
    if not st.enabled:
        return codes + [("SCHED-NOT-ENABLED", "排程未啟用")]
    cell = si_sched.cell_bounds(st, now)
    if cell is None or datetime.fromisoformat(ns.due_at) != cell[0]:
        codes.append(("DUE-AT-NOT-CELL-START", "--due-at 須等於當下本格起點"))
    elif si_sched.cell_events(events, "run.open", cell, trigger="f"):
        codes.append(("CELL-ALREADY-RUN", "本格已有 trigger f 的運轉"))
    return codes


def _usage_open(ns) -> None:
    wv._label(ns.by, "--by")
    if (ns.trigger == "f") != (ns.due_at is not None):
        raise UsageError("--due-at 只配 --trigger f，且 trigger f 必帶")
    if ns.due_at is not None:
        try:
            ok = datetime.fromisoformat(ns.due_at).utcoffset() is not None
        except ValueError:
            ok = False
        if not ok:
            raise UsageError("--due-at 須為帶 offset 的 ISO 8601")
    if ns.carrier == "console":
        if ns.trigger != "a" or ns.audit_ref is None or not si_events.valid_uuid(ns.audit_ref):
            raise UsageError("--carrier console 只配 --trigger a 與 --audit-ref（UUID）")
    elif ns.audit_ref is not None:
        raise UsageError("--audit-ref 只配 --carrier console")


def run_open(repo: Path, ns, as_json: bool) -> wv.Out:
    """`run-open` 的 P4 增補路徑（trigger f 或 Console 載體）；其餘維持 `writeverbs.run_open`。"""
    _usage_open(ns)
    params = wv.params_for(repo, *_BASE_KEYS)
    bad = [("COORD-NONE", c) for c in ns.coord if not si_rows.has_coord(c)]
    head = Git(repo).head()
    if head is None:
        bad.append(("GIT-UNAVAILABLE", "git 不可用或無 commit，無法記 head_sha"))
    audit = None
    if ns.carrier == "console":
        got = _console_audit(repo, "run-open", ns.audit_ref, "run-request", params, as_json)
        if isinstance(got, wv.Out):
            return got
        audit = got[0]
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    now = current_time()
    if ns.trigger == "f":
        bad += _f_codes(events, params, ns, now)
    if bad:
        return wv.reject(repo, "run-open", bad, as_json)

    def build(state):
        if audit is not None:
            _reused_in_lock(state, ns.audit_ref)
        if ns.trigger == "f":
            lock_bad = _f_codes(state.events, params, ns, now)
            if lock_bad:
                raise evwrite.Reject(lock_bad)
        others = si_sched.open_runs(state.events)
        if audit is not None and others:
            return _console_skip(state.events, params, audit, ns, now, others)
        rid = f"RUN-SI-{wv._next_num(state.events, 'run.open', 'run', 'RUN-SI-'):03d}"
        ev = {"kind": "run.open", "by": ns.by, "run": rid, "trigger": ns.trigger,
              "coords": ns.coord, "head_sha": head}
        if ns.trigger == "f":
            ev["due_at"] = si_sched.iso(datetime.fromisoformat(ns.due_at))
        if audit is not None:
            ev.update(carrier="console", **_console_keys(audit, ns.audit_ref))
        return ev

    def render(e):
        if e["kind"] == "sched.skip":
            return wv.ok_text("sched.skip", e["seq"], None, [("reason", e["reason"]),
                                                             ("audit_ref", e["audit_ref"])],
                              as_json)
        return wv.ok_text("run.open", e["seq"], e["run"], [("head_sha", head)], as_json)
    return wv.append(repo, "run-open", build, params, as_json, render)


def _console_skip(events: list[dict], params: dict, audit, ns, now: datetime, others) -> dict:
    """R146 (b)：已有未關運轉⇒請求被消耗、改記 `sched.skip`（去重鍵 audit_ref）。"""
    st = si_sched.state_of(events, params["sched_period_minutes_default"])
    cell = si_sched.cell_bounds(st, now)
    due = si_sched.iso(cell[0]) if cell else audit.body["time"]
    return {"kind": "sched.skip", "by": ns.by, "due_at": due, "reason": "run-open",
            "detail": si_sched.line1(f"Console 立即啟動請求被擋：已有未關運轉 {'、'.join(others)}"),
            "carrier": "console", "audit_ref": ns.audit_ref}


# ── sched.skip（巡邏器到期嘗試；同格同因一筆）──────────────────────────────────
def append_skip(repo: Path, now: datetime, reason: str, detail: str,
                params: dict | None = None) -> dict | None:
    """鎖內重算 `skip_plan` 並追加 `sched.skip`；同格同因已有、或停用／無格＝不寫並回 None。"""
    params = params or wv.params_for(repo, *_BASE_KEYS)
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise UsageError(f"HOME-UNWRITABLE {exc}") from exc
    ledger = repo / si_events.LEDGER_REL

    def build(state):
        ev = si_sched.skip_plan(state.events, now, reason, detail, params)
        if ev is None:
            raise evwrite.Reject([("SKIP-NOT-NEEDED", "同格同因已記或排程停用")])
        return ev
    try:
        return evwrite.append_event(ledger, evwrite.lock_path_for(si, ledger), build,
                                    max_bytes=params["event_max_bytes"])
    except evwrite.Reject:
        return None
