"""SelfImproving 決定寫入：`decide`（逐字稿載體）與 `card --issue`（TCS-P2 R70、R80、R81）。

能力類別 `rw`：引言驗證與前提判定呼叫 `ro` 模組（`decverify`、`decgrammar`、`fold`、`card`），
寫入只經 `evwrite.append_event`（寫入鎖內重驗後單次追加）。`preconditions` 是寫入端的前提判定，
與 `fold` 重放端共用 `fold.transition_of` 這一份實作（AT-240-2-E-3 以格點差分釘住兩者一致）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import card as si_card
from . import consoleaudit, decgrammar, decverify, evwrite, obsrows
from . import events as si_events
from . import fold as si_fold
from . import transcript as si_transcript
from . import writeverbs as wv
from .git import Git

UNATTENDED_ENV = "AUTOSDD_UNATTENDED"
_NEEDS_CLASS = ("reject", "decline-promote", "return")
_CARD_STATES = ("proposed", "verified", "promoted", "measuring", "closed")
_KEYS = ("event_max_bytes", "stop_after_bad")
_WHY = {
    "NOT-SUSPENDED": "迴圈目前不在 SUSPENDED，沒有可恢復的運轉",
    "RUN-MISMATCH": "RUN 不等於折疊出的 SUSPENDED 所在運轉（舊回覆重播？）",
    "ROUTE-HANDOFF": "route 為 handoff:* 的 PROP 只能轉交，不可核准或晉升",
    "NOT-IN-COOLDOWN": "PROP 不在冷卻中（未被否決或已解除）",
    "PROMOTE-FORM-MISMATCH": "晉升的式與 verdict 不符（PASS 前式、NE 後式、FAIL 不收）",
    "PROMOTE-PREMISE-ROLLBACK": "最近一筆 app.sandbox 的 rollback_ok 不為 true",
    "PROMOTE-PREMISE-TOUCHED": "最近一筆 app.sandbox 的 touched_ok 不為 true",
    "PRECONDITION-VERDICT": "verified 的 verdict 不允許退回（須 FAIL 或沙盒失敗的 NE）",
    "PRECONDITION-STATE": "PROP 的態不在此決定的前提態內（R75）",
}
UsageError = wv.UsageError


@dataclass
class Out(wv.Out):
    err: str = ""


def _fmt(v) -> str:
    if v is True or v is False:
        return "true" if v else "false"
    if v is None:
        return "null"
    return ",".join(map(str, v)) or "-" if isinstance(v, (list, tuple)) else str(v)


def ok_out(kind: str, seq: int, ident: str | None, extras: list, as_json: bool) -> Out:
    """R69 成功輸出：單行 `ok <kind> seq=<N> [id=<ID>] <附加欄>`（布林 true／false、空值 null、清單
    以逗號連接而空清單印 `-`）；`--json` 為鍵序 ok、kind、seq、id、其後附加欄的物件。"""
    if as_json:
        obj = {"ok": True, "kind": kind, "seq": seq, "id": ident, **dict(extras)}
        return Out(0, json.dumps(obj, ensure_ascii=False) + "\n")
    parts = [f"ok {kind} seq={seq}"] + ([f"id={ident}"] if ident else [])
    return Out(0, " ".join(parts + [f"{k}={_fmt(v)}" for k, v in extras]) + "\n")


def refuse_unattended(repo: Path, verb: str, as_json: bool) -> wv.Out | None:
    """R70：`AUTOSDD_UNATTENDED` 存在且值非空（含字面 `0`）⇒ rc 1、零寫入；先於其他一切前置檢查。"""
    if not os.environ.get(UNATTENDED_ENV):
        return None
    codes = [("UNATTENDED-REFUSED", f"{UNATTENDED_ENV} 有設，{verb} 一律拒收")]
    return wv.reject(repo, verb, codes, as_json)


def preconditions(f: si_fold.Folded, target: str, dkind: str, flags) -> list[str]:
    """R75 末段：寫入端前提判定（空＝成立）；與重放端共用 `fold.transition_of`。"""
    if dkind == "resume":
        if f.suspended is None:
            return ["NOT-SUSPENDED"]
        return [] if f.suspended["run"] == target else ["RUN-MISMATCH"]
    p = f.props.get(target)
    if p is None:
        return ["PROP-NOT-FOUND"]
    flags = list(flags)
    if si_fold.transition_of(p, dkind, flags) is not None:
        return []
    if p.route.startswith("handoff:") and dkind in ("approve", "promote"):
        return ["ROUTE-HANDOFF"]
    if dkind == "unblock":
        return ["NOT-IN-COOLDOWN"]
    if dkind == "promote" and p.state == "verified":
        ack = "unverified_ack" in flags
        out = [] if (p.verdict == "PASS" and not ack) or (p.verdict == "NE" and ack) \
            else ["PROMOTE-FORM-MISMATCH"]
        out += ["PROMOTE-PREMISE-ROLLBACK"] if p.rollback_ok is not True else []
        return out + (["PROMOTE-PREMISE-TOUCHED"] if p.touched_ok is not True else [])
    if dkind == "return" and p.state == "verified":
        return ["PRECONDITION-VERDICT"]
    return ["PRECONDITION-STATE"]


def _label(value: str, what: str) -> None:
    if not si_events.valid_by(value):
        raise UsageError(f"{what} 須為非空、無空白、≤32 字元的標籤")


def _usage(ns) -> None:
    _label(ns.by, "--by")
    if not (si_events.PROP_RE.match(ns.id) or si_events.RUN_RE.match(ns.id)):
        raise UsageError("位置參數須為 PROP-SI-NNN 或 RUN-SI-NNN（至少 3 位數字）")
    if ns.carrier == "console":
        if any(v is not None for v in (ns.kind, ns.sid, ns.line, ns.reason_class)):
            raise UsageError("--carrier console 不收 --kind／--sid／--line／--reason-class")
        if ns.audit_ref is None or not si_events.valid_uuid(ns.audit_ref):
            raise UsageError("--carrier console 須帶 --audit-ref（UUID）")
        return
    if ns.audit_ref is not None:
        raise UsageError("--audit-ref 只配 --carrier console")
    if ns.sid is None or not si_events.valid_uuid(ns.sid):
        raise UsageError("--sid 須為 UUID 正規形")
    if ns.line is None or ns.line < 1:
        raise UsageError("--line 須為整數 ≥1")
    if ns.kind is None:
        raise UsageError("--kind 必給（逐字稿載體）")


def _stage_one(repo: Path, ns) -> tuple:
    """逐字稿層（階段一）：遇第一個失敗即回 (None, [(碼, 說明)])；成功回 (資料, None)。"""
    try:
        records = si_transcript.load(si_transcript.path_for(repo, ns.sid))
        if not 1 <= ns.line <= len(records):
            raise si_transcript.TranscriptError("LINE-OUT-OF-RANGE", f"--line {ns.line} 超界")
        human = si_transcript.human_of(records[ns.line - 1])
        parsed = decgrammar.parse(human.text)
    except si_transcript.TranscriptError as exc:
        return None, [(exc.code, exc.detail)]
    except decgrammar.GrammarError as exc:
        return None, [(exc.code, exc.detail)]
    want = "RUN" if parsed.verb == "恢復" else "PROP"
    if not ns.id.startswith(want + "-SI-"):
        return None, [("ID-KIND", f"引言動詞 {parsed.verb} 要 {want} 號，位置參數是 {ns.id}")]
    if parsed.id != ns.id:
        return None, [("ID-MISMATCH", f"引言的 ID {parsed.id} 不等於位置參數 {ns.id}")]
    return (records, human, parsed), None


def _derive_kind(parsed: decgrammar.Parsed, state: str | None) -> tuple[str | None, str]:
    if parsed.verb != "否決":
        return parsed.kind_candidates[0], ""
    mapped = {"proposed": "reject", "verified": "decline-promote"}.get(state or "")
    return mapped, ("" if mapped else f"否決只收 proposed 或 verified，PROP 為 {state}")


def _enclosing(records, human, dkind: str) -> tuple:
    """卡面送達的訊息文字；回 (文字, 階段一碼, 階段二碼)：`ATTACHMENT-TIME-UNKNOWN` 屬階段一，
    `CARD-NOT-DELIVERED` 屬階段二（與其他政策與狀態碼一併回報）。"""
    if dkind == "resume":
        return None, None, None
    try:
        return si_transcript.find_enclosing(records, human), None, None
    except si_transcript.TranscriptError as exc:
        pair = [(exc.code, exc.detail)]
        return (None, pair, None) if exc.code == "ATTACHMENT-TIME-UNKNOWN" else (None, None, pair)


def _reason_codes(dkind: str, parsed: decgrammar.Parsed, reason_class: str | None) -> list:
    if dkind in _NEEDS_CLASS:
        if reason_class is None:
            return [("REASON-CLASS-MISSING", f"{dkind} 須給 --reason-class")]
        if (parsed.trailing == "未說明") != (reason_class == "未說明"):
            return [("REASON-CLASS-MISMATCH", "引言尾隨句恰為「未說明」者只准理由類「未說明」")]
        return []
    if reason_class is not None:
        return [("REASON-CLASS-UNEXPECTED", f"{dkind} 不收 --reason-class")]
    return []


def _card_layer(repo: Path, git: Git, events: list, f, pid: str, params: dict) -> tuple:
    """R80 (f)：回 (碼清單, 最近一筆 card 事件或 None)；不含 CARD-NOT-DELIVERED。"""
    cards = [e for e in events if e["kind"] == "card" and e.get("prop") == pid]
    if not cards:
        return [("CARD-NOT-ISSUED", f"{pid} 沒有任何 card 事件")], None
    last, p = cards[-1], f.props[pid]
    if last.get("digest") != p.digest:
        return [("STALE-CARD", "最近一筆 card 的 digest 不等於 PROP 當下 digest")], last
    try:
        then = decverify.rebuild_card(decverify.Ctx(repo, events, git, params), last["seq"], pid)
        now = si_card.build(repo, git, events, f, pid, params)
    except si_card.CardError as exc:
        return [("CARD-CHANGED", f"卡面無法重算（{exc.code}）")], last
    if decverify.card_text_sha(then.text) != last.get("card_sha256"):
        return [("CARD-CHANGED", "card 事件的 card_sha256 與當時前綴重建的卡面不符")], last
    if decverify.core_of(then.text) != decverify.core_of(now.text):
        return [("CARD-CHANGED", "卡面核心區自上次發卡後已變（例如驗證欄），須重新上卡")], last
    return [], last


def _local_iso(ts: str | None) -> str:
    when = si_transcript.parse_ts(ts)
    return when.astimezone().isoformat(timespec="seconds") if when else evwrite.now_iso()


def decide(repo: Path, ns, as_json: bool) -> wv.Out:
    _usage(ns)
    params = wv.params_for(repo, *_KEYS)
    refused = refuse_unattended(repo, "decide", as_json)
    if refused:
        return refused
    if ns.carrier == "console":
        return _decide_console(repo, ns, params, as_json)
    ledger = repo / si_events.LEDGER_REL
    events = si_events.load_sound_events(ledger) or []
    f = si_fold.fold(events, params["stop_after_bad"])
    is_run = ns.id.startswith("RUN-")
    if is_run and ns.id not in f.runs:
        return wv.reject(repo, "decide", [("RUN-NOT-FOUND", f"{ns.id} 沒有 run.open")], as_json)
    if not is_run and ns.id not in f.props:
        return wv.reject(repo, "decide", [("PROP-NOT-FOUND", f"{ns.id} 不存在")], as_json)
    got, codes = _stage_one(repo, ns)
    if codes:
        return wv.reject(repo, "decide", codes, as_json)
    records, human, parsed = got
    prop = None if is_run else f.props[ns.id]
    dkind, why = _derive_kind(parsed, prop.state if prop else None)
    if dkind is None:
        return wv.reject(repo, "decide", [("PRECONDITION-STATE", why)], as_json)
    if ns.kind != dkind:
        return wv.reject(repo, "decide", [("KIND-MISMATCH", f"--kind {ns.kind} 不等於由引言與態"
                                                              f"導出的 {dkind}")], as_json)
    enclosing, early, late = _enclosing(records, human, dkind)
    if early:
        return wv.reject(repo, "decide", early, as_json)
    flags = list(parsed.flags)
    stage2 = [(c, _WHY.get(c, c)) for c in preconditions(f, ns.id, dkind, flags)]
    if prop is not None:
        route = prop.route.startswith("handoff:")
        if (parsed.verb == "否決" and route) or (parsed.verb == "不轉交" and not route):
            stage2.append(("ROUTE-VERB-MISMATCH", f"{parsed.verb} 與 route {prop.route} 不配"))
    stage2 += _reason_codes(dkind, parsed, ns.reason_class)
    git = Git(repo)
    event = {"kind": "dec", "by": ns.by, "id": "", "dkind": dkind}
    if prop is not None:
        card_codes, last = _card_layer(repo, git, events, f, ns.id, params)
        stage2 += card_codes
        event.update(_body(prop, parsed, ns, flags, last, human))
        if not card_codes and late:
            stage2 += late
        elif not card_codes:
            v = decverify.delivered(decverify.Ctx(repo, events, git, params), event, enclosing)
            stage2 += [(v.code, v.detail)] if v.status != "ok" else []
    else:
        event.update(run=ns.id, reason=parsed.trailing, quote=parsed_line(human, parsed),
                     sid=ns.sid, line=ns.line, decider="掌舵者",
                     decided_at=_local_iso(human.ts))
    if stage2:
        return wv.reject(repo, "decide", stage2, as_json)
    return _write(repo, ns, params, event, prop, as_json)


def _console_body_codes(body: dict, dkind) -> list:
    """Console `body` 的決定欄位規則（R94 欄位表）；回 (碼, 說明) 清單。"""
    bad = dkind not in si_events.DKINDS or not (
        isinstance(body.get("run" if dkind == "resume" else "prop"), str)
        and (dkind == "resume" or dkind not in si_fold._DIGEST_KINDS
             or isinstance(body.get("digest"), str))
        and isinstance(body.get("flags", []), list)
        and all(isinstance(f, str) for f in body.get("flags", []))
        and (dkind not in si_events._WITH_REASON or isinstance(body.get("reason"), str)))
    if bad:
        return [("AUDIT-BODY-INVALID", "decide 的 body 欄位不合（dkind、對象、digest、reason）")]
    rc = body.get("reason_class")
    if dkind in _NEEDS_CLASS:
        if rc is None:
            return [("REASON-CLASS-MISSING", f"{dkind} 須帶 reason_class")]
        return [] if rc in si_events.REASON_CLASSES else [
            ("REASON-CLASS-INVALID", f"reason_class {rc} 不在詞彙")]
    return [("REASON-CLASS-UNEXPECTED", f"{dkind} 不收 reason_class")] if rc is not None else []


def _decide_console(repo: Path, ns, params: dict, as_json: bool) -> wv.Out:
    """`decide --carrier console`（R95）：稽核檔經 HMAC 驗證，其後與逐字稿載體同一組狀態層前提；
    不驗卡面送達（Console 路徑沒有逐字稿）。入帳不是回查：金鑰缺一律拒收。"""
    try:
        audit = consoleaudit.verify(consoleaudit.audit_path(si_events.si_dir(), ns.audit_ref))
    except consoleaudit.AuditError as exc:
        return wv.reject(repo, "decide", [(exc.code, exc.detail)], as_json)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    body = audit.body
    early = []
    if obsrows.ref_used(repo, events, ns.audit_ref):
        early = [("AUDIT-REF-REUSED", f"audit_ref {ns.audit_ref} 已入帳過")]
    elif body["kind"] != "decide":
        early = [("AUDIT-KIND-MISMATCH", f"稽核檔 kind 為 {body['kind']}，decide 只收 decide")]
    elif audit.outer["subject"] != ns.id:
        early = [("AUDIT-SUBJECT-MISMATCH", "位置參數不等於稽核檔的 subject")]
    if early:
        return wv.reject(repo, "decide", early, as_json)
    dkind = body.get("dkind")
    codes = _console_body_codes(body, dkind)
    f = si_fold.fold(events, params["stop_after_bad"])
    is_run = dkind == "resume"
    prop = None if is_run else f.props.get(ns.id)
    if not codes and not is_run and prop is None:
        codes = [("PROP-NOT-FOUND", f"{ns.id} 不存在")]
    elif not codes and is_run and ns.id not in f.runs:
        codes = [("RUN-NOT-FOUND", f"{ns.id} 沒有 run.open")]
    if not codes:
        flags = list(body.get("flags", []))
        codes = [(c, _WHY.get(c, c)) for c in preconditions(f, ns.id, dkind, flags)]
        if prop is not None and dkind in si_fold._DIGEST_KINDS and body["digest"] != prop.digest:
            codes.append(("STALE-CARD", "body.digest 不等於 PROP 當下 digest"))
    if codes:
        return wv.reject(repo, "decide", codes, as_json)
    event = {"kind": "dec", "by": ns.by, "id": "", "dkind": dkind}
    event.update({("run" if is_run else "prop"): ns.id})
    if dkind in si_fold._DIGEST_KINDS:
        event["digest"] = prop.digest
    event.update({k: body[k] for k in ("reason", "reason_class") if k in body})
    if body.get("flags"):
        event["flags"] = list(body["flags"])
    event.update(carrier="console", audit_ref=ns.audit_ref, audit_sha256=audit.sha,
                 key_id=audit.key_id, decider=body["user"], decided_at=body["time"])
    return _write(repo, ns, params, event, prop, as_json)


def parsed_line(human, parsed: decgrammar.Parsed) -> str:
    return human.text.replace("\r\n", "\n").strip().split("\n")[parsed.line_no - 1].strip()


def _body(prop, parsed: decgrammar.Parsed, ns, flags: list, last: dict | None, human) -> dict:
    dk = ns.kind
    out: dict = {"prop": prop.id}
    if dk in si_fold._DIGEST_KINDS:
        out["digest"] = prop.digest
    if parsed.trailing and dk in ("reject", "decline-promote", "return", "rollback"):
        out["reason"] = parsed.trailing
    if dk in _NEEDS_CLASS:
        out["reason_class"] = ns.reason_class
    if flags:
        out["flags"] = flags
    out.update(quote=parsed_line(human, parsed), sid=ns.sid, line=ns.line,
               card_seq=last["seq"] if last else 0, decider="掌舵者",
               decided_at=_local_iso(human.ts))
    return out


def _write(repo: Path, ns, params: dict, event: dict, prop, as_json: bool) -> wv.Out:
    def build(state):
        f2 = si_fold.fold(state.events, params["stop_after_bad"])
        cur = f2.props.get(ns.id) if prop is not None else None
        stale = (prop is not None and (cur is None or cur.state != prop.state
                                       or cur.digest != prop.digest))
        if stale or (prop is None and f2.suspended is None):
            raise evwrite.Reject([("STATE-CHANGED", "寫入鎖內重驗：PROP 態或 digest 已變")])
        if event.get("audit_ref") and any(e.get("audit_ref") == event["audit_ref"]
                                          for e in state.events):
            raise evwrite.Reject([("AUDIT-REF-REUSED", "寫入鎖內重驗：audit_ref 已入帳")])
        nums = [int(e["id"].rsplit("-", 1)[1]) for e in state.events if e["kind"] == "dec"]
        return {**event, "id": f"DEC-SI-{max(nums, default=0) + 1:03d}"}

    def render(e):
        extras = [("prop", e["prop"]) if "prop" in e else ("run", e["run"]), ("dkind", e["dkind"])]
        if prop is not None:  # 無 digest 欄的 rollback／unblock 也印 PROP 當下 digest 的前 8 碼
            extras.append(("digest8", prop.digest.split(":", 1)[-1][:8]))
        return wv.ok_text("dec", e["seq"], e["id"], extras, as_json)
    return wv.append(repo, "decide", build, params, as_json, render)


def issue_card(repo: Path, ns, as_json: bool) -> Out:
    """`card --issue`（R81）：寫入鎖內重算卡面並追加 `card` 事件；stdout 與不帶旗標逐位元組相同。"""
    _label(ns.by, "--by")
    refused = refuse_unattended(repo, "card", as_json)
    if refused:
        return Out(refused.rc, refused.text)
    params = wv.params_for(repo, "event_max_bytes", "stop_after_bad", "card_line_max")
    git = Git(repo)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    f = si_fold.fold(events, params["stop_after_bad"])
    try:
        si_card.build(repo, git, events, f, ns.prop, params)
    except si_card.CardError as exc:
        raise UsageError(f"{exc.code} {exc.detail}".strip()) from exc
    p = f.props[ns.prop]
    if p.state not in _CARD_STATES and not (p.state == "rejected" and not p.unblocked):
        out = wv.reject(repo, "card", [("STATE-ILLEGAL", f"{p.id} 為 {p.state}，不在卡面前提態")],
                        as_json)
        return Out(out.rc, out.text)
    box: dict = {}

    def build(state):
        f2 = si_fold.fold(state.events, params["stop_after_bad"])
        try:
            res = si_card.build(repo, git, state.events, f2, ns.prop, params)
        except si_card.CardError as exc:
            raise evwrite.Reject([(exc.code, exc.detail)]) from exc
        box["res"] = res
        return {"kind": "card", "by": ns.by, "prop": res.prop, "rev": res.rev,
                "digest": res.digest, "card_sha256": decverify.card_text_sha(res.text)}

    def render(e):
        res = box["res"]
        box["seq"] = e["seq"]
        if as_json:
            obj = {"schema_rev": 1, "prop": res.prop, "rev": res.rev, "digest": res.digest,
                   "core_lines": res.core_lines, "text": res.text, "parsed": res.parsed,
                   "issued": {"seq": e["seq"], "card_sha256": e["card_sha256"]}}
            return json.dumps(obj, ensure_ascii=False) + "\n"
        return res.text
    out = wv.append(repo, "card", build, params, as_json, render)
    if out.rc != 0:
        return Out(out.rc, out.text)
    digest8 = box["res"].digest.split(":", 1)[-1][:8]
    return Out(0, out.text, f"ok card seq={box['seq']} prop={ns.prop} digest8={digest8}\n")
