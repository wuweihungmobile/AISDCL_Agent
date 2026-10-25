"""SelfImproving `measure`：採納量測窗的寫入端（TCS-P3 R111、R112、R121～R123）。

能力類別 `rw`：只追加 `mea.report`、`mea.open`、`mea.close`、`mea.amend` 四種事件，
絕不下決定、不改工作樹與任何帳本。逐事件鎖內重算：反覆「取寫入鎖 → 以鎖內最新事件帳本與當下
OBS／DEF 帳本重算規劃 → 追加規劃的第一個事件 → 放鎖」直到規劃為空（冪等）。
`plan_amends` 供 `attr-confirm`／`attr-reject` 同鎖追加（R121 (e)）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import card as si_card
from . import events as si_events
from . import evwrite, meacheck, meaplan, meastat
from . import mea as si_mea
from . import props as si_props
from . import writeverbs as wv
from .git import Git

_PARAM_KEYS = ("w_opp", "w_evt", "w_min", "w_n", "stop_after_bad", "event_max_bytes",
               "metrics_rev", "card_line_max")
_CUT = "--- 以下不計入核心區 ---"
_WIN_KEYS =("prop", "state", "result", "n_opp", "w_opp", "baseline", "unsettled")


@dataclass
class Result:
    rc: int
    text: str
    obj: dict | None = None


class _Done(Exception):
    """鎖內重算得規劃為空：沒有東西要追加（不寫位元組）。"""


def plan_amends(repo: Path, events: list[dict]) -> list[dict]:
    """R121 (e)：`events`（含剛落定的事件）重算出的 `mea.amend`（不含 seq、t、by）；輸入不可用或
    無任何窗時回空清單（絕不使 attr 動詞拒收）。"""
    try:
        params = wv.params_for(repo, *_PARAM_KEYS)
        ctx = si_mea.build_ctx(repo, Git(repo), params, si_events.sound(events))
    except (wv.UsageError, OSError, ValueError):
        return []
    if ctx.bad or not ctx.obs_ok or not ctx.def_ok:
        return []
    return [e for e in meaplan.plan(ctx) if e["kind"] == "mea.amend"]


def _fit(text: str, limit: int) -> str:
    while si_card.width(text) > limit:
        text = text[:-2] + "…"
    return text


def _card_text(repo: Path, ctx: si_mea.Ctx, p: si_mea.Prop, win: dict, limit: int) -> str:
    at = si_mea.parse_t(win["at"])
    rec = [r for r in ctx.rows if r.at > p.at and (o := si_mea.owner_of(ctx, r)) is not None
           and o.id == p.id and si_mea.cand_state(ctx, r.id)[0] == "confirmed"
           and at is not None and r.at <= at]
    pe = max((e for e in ctx.events if e["kind"] == "prop" and e.get("id") == p.id),
             key=lambda e: e["rev"])
    why = "（無）"
    if rec:
        att = min((a for a in ctx.links.get(rec[0].id, []) if a.settled
                   and a.settled[0] == "attr.confirm"), key=lambda a: a.settled[1])
        why = f"{rec[0].id}（證據 {rec[0].coords}）｜歸因 {att.id}｜確認者 {att.settled[2]}"
    try:
        body = (repo / si_events.PROPOSALS_REL / p.id / f"r{pe['rev']}.md").read_text("utf-8")
        recipe = si_props.parse_body(body)[1].get("rollback") or "量不到（rollback 欄為空）"
    except OSError:
        recipe = "量不到（PROP-FILE-MISSING）"
    head = f"[{p.id}] 回滾提案｜窗：recurred｜digest：{pe['digest'].split(':', 1)[-1][:8]}"
    core = [head, f"一、再現：{why}",
            f"二、已採納：觸及 {pe['touched_count']} 個檔案｜app.promote seq={p.seq}",
            f"三、回滾配方：{recipe}"]
    lines = [core[0], *[_fit(c, limit) for c in core[1:]], _CUT,
             f"決定：回滾 {p.id} <一句理由>"]
    return "\n".join(lines) + "\n"


def _cards(repo: Path, ctx: si_mea.Ctx) -> list[dict]:
    wins, limit = meaplan.first_windows(ctx), ctx.params["card_line_max"]
    return [{"prop": pid, "text": _card_text(repo, ctx, next(p for p in ctx.props if p.id == pid),
                                              wins[pid], limit)}
            for pid in meaplan.rollback_pending(ctx)]


def _render(obj: dict, as_json: bool) -> str:
    if as_json:
        return json.dumps(obj, ensure_ascii=False) + "\n"
    lines = [f"ok measure events={obj['events']} props={obj['props']}"]
    for w in obj["windows"]:
        b = w["baseline"]
        lines.append(f"window {w['prop']} state={w['state']} result={w['result'] or '-'} "
                     f"n_opp={w['n_opp']}/{w['w_opp']} baseline="
                     f"{b['events'] if b else '-'}/{b['opp_n'] if b else '-'}")
    for c in obj["rollback_cards"]:
        lines.append(c["text"].rstrip("\n"))
    if obj["check_report"] is not None:
        lines.append(f"check-report appended={str(obj['check_report']['appended']).lower()}")
    return "\n".join(lines) + "\n"


def measure(repo: Path, *, by: str = "main", record_check: bool = False,
            as_json: bool = False) -> Result:
    """R122：規劃至收斂；回 `Result`（rc 0＝已重算、1＝拒收、輸入或用法錯誤拋 `UsageError`）。"""
    if not si_events.valid_by(by):
        raise wv.UsageError("--by 須為非空、無空白、≤32 字元的標籤")
    params = wv.params_for(repo, *_PARAM_KEYS)
    if os.environ.get("AUTOSDD_UNATTENDED"):
        return _reject(repo, [("UNATTENDED-REFUSED", "measure 於無人值守環境一律拒收")], as_json)
    si, git = si_events.si_dir(), Git(repo)
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise wv.UsageError(f"HOME-UNWRITABLE {exc}") from exc
    ledger = repo / si_events.LEDGER_REL
    path = evwrite.lock_path_for(si, ledger)
    first = si_mea.build_ctx(repo, git, params, si_events.load_sound_events(ledger) or [])
    cap, appended = 5 * len(first.props), []

    def build(state):
        ctx = si_mea.build_ctx(repo, git, params, state.events)
        if ctx.bad:
            raise evwrite.Reject(meacheck.reject_codes(ctx.bad))
        events = meaplan.plan(ctx)
        bad = meaplan.input_problems(ctx, events)
        if bad:
            raise evwrite.Reject([(c, f"{c} 缺少輸入，不寫出不可恢復的紀錄") for c in bad])
        if not events:
            raise _Done
        if len(appended) >= cap:
            raise evwrite.Reject([("MEASURE-NOT-CONVERGING", f"追加數已達 {cap} 仍未收斂")])
        return {**events[0], "by": by}

    def run(builder) -> bool:
        try:
            appended.append(evwrite.append_event(ledger, path, builder,
                                                 max_bytes=params["event_max_bytes"]))
        except _Done:
            return False
        return True
    try:
        while run(build):
            pass
        check = None
        if record_check:
            check = {"appended": run(lambda st: _check_event(repo, git, params, st, by))}
    except evwrite.Reject as exc:
        return _reject(repo, exc.codes, as_json)
    except evwrite.LockBusyError as exc:
        return _reject(repo, [("LOCK-BUSY", str(exc))], as_json)
    except OSError as exc:
        raise wv.UsageError(f"事件追加失敗（{exc.__class__.__name__}），帳本未變動") from exc
    ctx = si_mea.build_ctx(repo, git, params, si_events.load_sound_events(ledger) or [])
    obj = {"ok": True, "kind": "measure", "events": len(appended), "props": len(ctx.props),
           "appended": [{"seq": e["seq"], "kind": e["kind"], "prop": e.get("prop")}
                        for e in appended],
           "windows": [{k: w[k] for k in _WIN_KEYS} for w in meaplan.window_rows(ctx)],
           "rollback_cards": _cards(repo, ctx),
           "check_report": check}
    return Result(0, _render(obj, as_json), obj)


def _check_event(repo: Path, git: Git, params: dict, state, by: str) -> dict:
    ctx = si_mea.build_ctx(repo, git, params, state.events)
    ev = meastat.check_report(repo, params, meastat.metrics(repo, git, ctx, True))
    last = next((e for e in reversed(state.events) if e["kind"] == "mea.report"
                 and e.get("report") == "check"), None)
    if last is not None and {k: v for k, v in last.items() if k not in ("seq", "t", "by")} == ev:
        raise _Done
    return {**ev, "by": by}


def _reject(repo: Path, codes: list, as_json: bool) -> Result:
    out = wv.reject(repo, "measure", codes, as_json)
    return Result(out.rc, out.text)
