"""SelfImproving 量測指標 M1～M5、資訊欄與反證條件、判準指紋（TCS-P3 R124～R126）。

能力類別 `ro`、零 token：`measure --record-check` 與量測探針共用這一份（單一實作）。量不到的欄位一律
`NOT-EVALUABLE` 並帶理由碼，絕不印成 0；M1 只讀已記的基線報告（不重算窗），指標定義變更必改指紋。
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from datetime import UTC, date, datetime

from . import fold as si_fold
from . import mea as si_mea
from . import params as si_params
from . import rows as si_rows
from .git import Git
from .ledger import max_valid_id, parse_ledger
from .refs import obs_ledger_text

_FIXED_RE = re.compile(r"fixed@([0-9a-f]{7,40})")
_FIXED_DEF_RE = re.compile(r"^DEF-\d+-\d+$")
CARRIER = "carrier-not-established"
SAMPLE = "sample-below-w-min"


def fingerprint(repo, params: dict) -> tuple[str, dict]:
    """R126 (c)：`{"manifest","metrics_rev"}` 兩鍵 JSON 的雜湊（不含 `check_rules_rev`）。"""
    _, parts = si_params.fingerprint(repo, params)
    own = {"manifest": parts["manifest"], "metrics_rev": parts["metrics_rev"]}
    blob = json.dumps(own, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest(), own


def _read(value, n: int, reason: str | None) -> dict:
    if reason:
        return {"status": "NOT-EVALUABLE", "reason": reason, "n": n}
    return {"status": "read", "value": value, "n": n}


def _per_prop(ctx: si_mea.Ctx) -> list[dict]:
    prm = ctx.params
    base: dict = {}
    for e in ctx.events:
        if e["kind"] == "mea.report" and e.get("report") == "baseline":
            base.setdefault(e.get("prop"), e)
    wins: dict = {}
    for w in si_fold.effective_windows(ctx.f):
        wins.setdefault(w["prop"], w)
    out = []
    for p in ctx.props:
        b, w = base.get(p.id), wins.get(p.id)
        events = b.get("events") if b else None
        opp_n = len(b.get("opp") or []) if b else None
        eff = w["effective"] if w else None
        reason = ("NO-BASELINE" if b is None else "WINDOW-OPEN" if w is None
                  else "WINDOW-PENDING" if eff == "pending"
                  else "ROLLED-BACK-NO-RECURRENCE" if eff == "rolled-back"
                  else "BASELINE-EVENTS-BELOW-W-EVT" if events < prm["w_evt"]
                  else "BASELINE-ROWS-BELOW-W-MIN" if opp_n < prm["w_min"] else None)
        out.append({"prop": p.id, "result": eff, "events": events, "opp_n": opp_n,
                    "evaluable": reason is None, "reason": reason, "_seq": w["seq"] if w else 0})
    return out


def _why(carrier: bool, bad: bool) -> str:
    return si_mea.INVALID if bad else CARRIER if not carrier else "no-evaluable-window"


def _m1(rows: list[dict], carrier: bool, bad: bool = False) -> dict:
    ok = [r for r in rows if r["evaluable"]]
    per = [{k: v for k, v in r.items() if k != "_seq"} for r in rows]
    if bad or not carrier or not ok:
        return {"status": "NOT-EVALUABLE", "reason": _why(carrier, bad), "n": len(ok),
                "recurred": 0, "per_prop": per}
    rec = sum(1 for r in ok if r["result"] == "recurred")
    return {"status": "read", "n": len(ok), "recurred": rec, "value": rec / len(ok),
            "per_prop": per}


def _falsification(ctx: si_mea.Ctx, rows: list[dict], carrier: bool, bad: bool = False) -> dict:
    ok = {r["prop"]: r for r in rows if r["evaluable"]}
    if bad or not carrier or not ok:
        return {"falsified": None, "falsified_keys": [], "missing": [_why(carrier, bad)]}
    by_key: dict = {}
    for p in ctx.props:
        if p.id in ok:
            for k in si_mea.prop_keys(ctx, p):
                by_key.setdefault(k, []).append(ok[p.id])
    keys = sorted(k for k, rs in by_key.items() if _adjacent(sorted(rs, key=lambda r: r["_seq"])))
    return {"falsified": bool(keys), "falsified_keys": keys, "missing": []}


def _adjacent(rs: list[dict]) -> bool:
    return any(a["result"] == "recurred" and b["result"] == "recurred"
               for a, b in zip(rs, rs[1:], strict=False))


def _m5(ctx: si_mea.Ctx, carrier: bool) -> tuple[dict, int]:
    closed, late, first = [], 0, {}
    for w in si_fold.effective_windows(ctx.f):
        first.setdefault(w["prop"], w)
    for w in first.values():
        if w["effective"] == "pending":
            continue
        at = si_mea.parse_t(w.get("at"))
        rolls = ctx.rollbacks.get(w["prop"], [])
        late += sum(1 for t in rolls if at is not None and t > at)
        hit = at is not None and any(t <= at for t in rolls)
        closed.append((w["prop"], hit))
    ack = {p.id: p.ack for p in ctx.props}
    w_min = ctx.params["w_min"]

    def one(rs: list) -> dict:
        if not carrier:
            return _read(None, len(rs), CARRIER)
        return _read(sum(1 for _, h in rs if h) / len(rs) if len(rs) >= w_min else None, len(rs),
                     None if len(rs) >= w_min else SAMPLE)
    return {"main": one([c for c in closed if not ack.get(c[0])]), "all": one(closed)}, late


def _days(git: Git, sha: str, day: str) -> int | None:
    stamp = git.commit_time(sha)
    if stamp is None:
        return None
    return (datetime.fromtimestamp(stamp, UTC).date() - date.fromisoformat(day)).days


def _median(ctx: si_mea.Ctx, items: list, git: Git) -> dict:
    vals, excluded = [], 0
    for sha, day in items:
        d = _days(git, sha, day) if sha else None
        if d is None:
            excluded += 1
        else:
            vals.append(d)
    ok = len(vals) >= ctx.params["w_min"]
    out = _read(statistics.median(vals) if ok else None, len(vals), None if ok else SAMPLE)
    return {**out, "excluded": excluded}


def _sha_of(text: str) -> str | None:
    m = _FIXED_RE.search(text)
    return m.group(1) if m else None


def _m3_items(ctx: si_mea.Ctx) -> list:
    status = {r.id: r.disp for r in ctx.rows if r.kind == "DEF"}
    items = []
    for r in ctx.rows:
        if r.kind != "OBS" or not si_mea.is_candidate(ctx, r) \
                or si_mea.cand_state(ctx, r.id)[0] != "confirmed":
            continue
        tok = si_rows.disp_token(r.disp) or ""
        items.append((_sha_of(tok) or (_sha_of(status.get(tok, "")) if
                      _FIXED_DEF_RE.match(tok) else None), r.day))
    return items


def _global_m1(ctx: si_mea.Ctx) -> dict:
    if ctx.anchor is None:
        return {"status": "NOT-EVALUABLE", "reason": "anchor-unavailable", "n": 0}
    hit = {a.ev.get("reopens") for atts in ctx.links.values() for a in atts
           if a.settled and a.settled[0] == "attr.confirm"}
    fixed = [r for r in ctx.rows if r.at >= ctx.anchor and (
        (r.kind == "OBS" and (si_rows.disp_token(r.disp) or "").startswith("fixed@"))
        or (r.kind == "DEF" and r.cls == "fixed"))][-ctx.params["w_n"]:]
    n = len(fixed)
    if n < ctx.params["w_min"]:
        return {"status": "NOT-EVALUABLE", "reason": SAMPLE, "n": n}
    return {"status": "read", "value": sum(1 for r in fixed if r.id in hit) / n, "n": n}


def _m4(ctx: si_mea.Ctx, repo, carrier: bool) -> dict:
    bad = [w for w in ctx.f.warns if w[0] == "COOLDOWN-BYPASS-SUSPECT"]
    if not carrier:
        return {"status": "NOT-EVALUABLE", "reason": CARRIER, "drafts": []}
    text = obs_ledger_text(repo)
    top = max_valid_id(parse_ledger(text)) if text else 0
    drafts = [si_rows.draft_row(top + 1 + i, "si 量測（自動草稿）", f"冷卻繞過嫌疑：{w[1]}",
                                w[1], "si-measure", category="process", severity="P3")
              for i, w in enumerate(bad)]
    return {"status": "read", "value": len(bad), "drafts": drafts}


def metrics(repo, git: Git, ctx: si_mea.Ctx, carrier: bool = True) -> dict:
    """`{"success","info","falsification","ne"}`（R125、R126 (b)；`carrier`＝事件帳本在場）。"""
    bad = bool(ctx.bad)  # mea.* 事件欄位不合：窗相關指標一律不可評估（不讀壞欄位）
    rows = [] if bad else _per_prop(ctx)
    m5, late = ({k: _read(None, 0, si_mea.INVALID) for k in ("main", "all")}, 0) if bad \
        else _m5(ctx, carrier)
    decisions: dict = {}
    for e in ctx.events:
        if e["kind"] == "dec" and isinstance(e.get("dkind"), str):
            decisions[e["dkind"]] = decisions.get(e["dkind"], 0) + 1
    defs = {r.id: r for r in ctx.rows if r.kind == "DEF"}
    m2 = _median(ctx, [(_sha_of(r.disp), r.day) for r in defs.values() if _sha_of(r.disp)], git)
    info = {"proposals": len(ctx.f.props), "decisions": dict(sorted(decisions.items())),
            "obs_rows": ctx.obs_n, "closed_by_decision": sum(
                1 for r in defs.values() if r.cls == "closed-by-decision"),
            "unverified_ack": sum(1 for p in ctx.props if p.ack), "late_rollbacks": late,
            "unplaced_rows": ctx.unplaced,
            "unattributable_candidates": sum(1 for r in defs.values() if r.reopens),
            "m2": m2, "m3": _median(ctx, _m3_items(ctx), git), "global_m1": _global_m1(ctx)}
    fals = _falsification(ctx, rows, carrier, bad)
    success = {"m1": _m1(rows, carrier, bad), "m4": _m4(ctx, repo, carrier), "m5": m5}
    flat = [("success.m1", success["m1"]), ("success.m4", success["m4"]),
            ("success.m5.main", m5["main"]), ("success.m5.all", m5["all"]),
            ("info.m2", m2), ("info.m3", info["m3"]), ("info.global_m1", info["global_m1"])]
    ne = [{"field": f, "reason": v["reason"]} for f, v in flat if v["status"] != "read"]
    return {"success": success, "info": info, "falsification": fals, "ne": ne}


def check_report(repo, params: dict, report: dict) -> dict:
    """`measure --record-check` 的 `mea.report`（`report` 為 `check`）事件（不含 seq、t、by）。"""
    s, fp = report["success"], fingerprint(repo, params)[0]

    def val(x):
        return x.get("value") if x["status"] == "read" else None
    missing = sorted({x["reason"] for x in (s["m1"], s["m4"], s["m5"]["main"], s["m5"]["all"])
                      if x["status"] != "read"} | set(report["falsification"]["missing"]))
    return {"kind": "mea.report", "report": "check", "fingerprint": fp,
            "metrics_rev": params["metrics_rev"], "windows": s["m1"]["n"], "m1_n": s["m1"]["n"],
            "m1": val(s["m1"]), "m4": val(s["m4"]), "m5_main": val(s["m5"]["main"]),
            "m5_all": val(s["m5"]["all"]), "m5_n": s["m5"]["all"]["n"],
            "falsified": report["falsification"]["falsified"], "missing": missing}
