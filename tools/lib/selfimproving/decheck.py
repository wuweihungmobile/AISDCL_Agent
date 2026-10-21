"""SelfImproving `check` 的 P2 追加項：`events.dec_quote`、`events.dec_console`、`events.verdict`、
`obs.console_audit`（TCS-SelfImproving-P2 R98）。

唯讀、不連網；載體缺席一律 nonblocking NE（`CARRIER-NOT-ESTABLISHED`，由 `evcheck` 填）。回傳
「項目 ID → findings」，判級與輸出由 `check.py` 組裝。偵測型（D）：事後標紅，不是被擋住的寫入。
"""

from __future__ import annotations

from pathlib import Path

from . import consoleaudit, decverify, verdict
from . import events as si_events
from . import fold as si_fold
from . import params as si_params
from . import refs as si_refs
from . import rows as si_rows
from .git import Git
from .ledger import Finding

P2_ITEMS = ("events.dec_quote", "events.dec_console", "events.verdict", "obs.console_audit")
_MISMATCH = "CONSOLE-AUDIT-MISMATCH"
_NE_KEY = decverify.Verdict("ne", "CONSOLE-KEY-MISSING", "金鑰環未設、為空或沒有對應 key_id 的金鑰")


def to_finding(subject: str, v: decverify.Verdict) -> Finding:
    """`Verdict` → Finding：fail ⇒ fail；ne ⇒ info（是否阻塞由 `check._NONBLOCKING` 定）。"""
    return Finding(subject, v.code, "fail" if v.status == "fail" else "info", v.detail)


def dec_quote(repo: Path, events: list[dict], params: dict, git: Git) -> list[Finding]:
    """R98 (a)：對每筆 `carrier` 缺或為 `transcript` 的 `dec`，以 `verify_dec` 重跑 ①～③。"""
    ctx = decverify.Ctx(repo, events, git, params)
    out = []
    for e in events:
        if e["kind"] == "dec" and e.get("carrier", "transcript") == "transcript":
            v = decverify.verify_dec(e, ctx)
            if v.status != "ok":
                out.append(to_finding(f"seq={e['seq']}", v))
    return out


def _mac_verdict(audit: consoleaudit.Audit) -> decverify.Verdict:
    """金鑰缺或 key_id 不在環＝nonblocking NE；HMAC 不符＝fail（R95、R98）。"""
    try:
        consoleaudit.check_mac(audit, consoleaudit.key_ring())
    except consoleaudit.AuditError as exc:
        if exc.code in ("AUDIT-KEY-MISSING", "AUDIT-KEY-UNKNOWN"):
            return _NE_KEY
        return decverify.Verdict("fail", _MISMATCH, exc.code)
    return decverify.OK


def _load_audit(ref) -> consoleaudit.Audit | decverify.Verdict:
    """稽核檔就位且結構合法時回 `Audit`；不在場＝NE `CONSOLE-AUDIT-MISSING`；結構不合＝fail。"""
    path = consoleaudit.audit_path(si_events.si_dir(), str(ref))
    if not path.is_file():
        return decverify.Verdict("ne", "CONSOLE-AUDIT-MISSING", f"稽核檔 {path.name} 不在場")
    try:
        return consoleaudit.parse(path)
    except consoleaudit.AuditError as exc:
        return decverify.Verdict("fail", _MISMATCH, f"{exc.code} {exc.detail}".strip())


def _dec_diffs(event: dict, body: dict) -> list[str]:
    run = event.get("dkind") == "resume"
    pairs = [("kind", body.get("kind"), "decide"), ("dkind", body.get("dkind"), event.get("dkind")),
             ("run" if run else "prop", body.get("run" if run else "prop"),
              event.get("run" if run else "prop")),
             ("decider", body.get("user"), event.get("decider")),
             ("decided_at", body.get("time"), event.get("decided_at")),
             ("reason", body.get("reason"), event.get("reason")),
             ("reason_class", body.get("reason_class"), event.get("reason_class")),
             ("flags", body.get("flags", []), event.get("flags") or [])]
    if event.get("dkind") in si_fold._DIGEST_KINDS:
        pairs.append(("digest", body.get("digest"), event.get("digest")))
    return [k for k, a, b in pairs if a != b]


def verify_console(event: dict, ctx: decverify.Ctx) -> decverify.Verdict:
    """R95：Console 載體 `dec` 的回查（`verify_dec` 的 console 分支）：稽核檔在場、`audit_sha256`、
    `key_id` 與 body 逐欄相符，金鑰在場再驗 HMAC。欄位不符先於金鑰缺席判。"""
    audit = _load_audit(event.get("audit_ref"))
    if isinstance(audit, decverify.Verdict):
        return audit
    why = _dec_diffs(event, audit.body)
    if audit.sha != event.get("audit_sha256"):
        why.append("audit_sha256")
    if audit.key_id != event.get("key_id"):
        why.append("key_id")
    if why:
        return decverify.Verdict("fail", _MISMATCH, "稽核檔與事件不符：" + "、".join(why))
    return _mac_verdict(audit)


def dec_console(repo: Path, events: list[dict], params: dict, git: Git) -> list[Finding]:
    """R98 (b)：對每筆 `carrier` 為 `console` 的 `dec` 回查（R95）。"""
    ctx = decverify.Ctx(repo, events, git, params)
    out = []
    for e in events:
        if e["kind"] == "dec" and e.get("carrier") == "console":
            v = verify_console(e, ctx)
            if v.status != "ok":
                out.append(to_finding(f"seq={e['seq']}", v))
    return out


def _row_diffs(row, event: dict, body: dict) -> list[str]:
    cells, marks = row.cells, si_rows.row_marks(row)
    pairs = [("time", consoleaudit.row_time(body.get("time", "")), cells[1]),
             ("context", str(body.get("context", "")).strip(), cells[2]),
             ("symptom", str(body.get("symptom", "")).strip(), cells[3]),
             ("evidence", str(body.get("evidence", "")).strip(), cells[4]),
             ("category", body.get("category"), cells[5]),
             ("severity", body.get("severity"), cells[6]),
             ("face", body.get("face"), marks.get("面", ("", 0))[0]),
             ("exposure", body.get("exposure", ""), marks.get("暴露", ("", 0))[0]),
             ("external_derived", bool(body.get("external_derived")), "外部衍生" in marks),
             ("user", body.get("user"), marks.get("回報者", ("", 0))[0]),
             ("decider", body.get("user"), event.get("decider"))]
    return [k for k, a, b in pairs if a != b]


def _console_add(row, adds: list[dict], ref: str) -> list[Finding]:
    ev = next((e for e in adds if e.get("obs") == row.ident and e.get("audit_ref") == ref), None)
    if ev is None:
        return [Finding(row.ident, "CONSOLE-EVENT-MISSING", "fail", "帶 carrier=console 的列沒有"
                                                                    "對應的 obs.add 事件")]
    audit = _load_audit(ref)
    if isinstance(audit, decverify.Verdict):
        return [to_finding(row.ident, audit)]
    why = _row_diffs(row, ev, audit.body)
    why += [k for k, a, b in (("kind", audit.body.get("kind"), "obs-add"),
                              ("audit_sha256", audit.sha, ev.get("audit_sha256")),
                              ("key_id", audit.key_id, ev.get("key_id"))) if a != b]
    if why:
        return [Finding(row.ident, _MISMATCH, "fail", "稽核檔、列與事件不符：" + "、".join(why))]
    return [to_finding(row.ident, v) for v in (_mac_verdict(audit),) if v.status != "ok"]


def _console_close(ev: dict, row) -> list[Finding]:
    sub = f"seq={ev['seq']}"
    if row is None or row.cells[7] == "open":
        why = f"{ev.get('obs')} 的處置未改為終值"
        return [Finding(sub, "CONSOLE-CLOSE-NOT-APPLIED", "fail", why)]
    audit = _load_audit(ev.get("audit_ref"))
    if isinstance(audit, decverify.Verdict):
        return [to_finding(sub, audit)]
    body = audit.body
    why = [k for k, a, b in (("kind", body.get("kind"), "obs-close"),
                             ("obs_id", body.get("obs_id"), ev.get("obs")),
                             ("disposition", body.get("disposition"), row.cells[7]),
                             ("decider", body.get("user"), ev.get("decider")),
                             ("audit_sha256", audit.sha, ev.get("audit_sha256")),
                             ("key_id", audit.key_id, ev.get("key_id"))) if a != b]
    if why:
        return [Finding(sub, _MISMATCH, "fail", "稽核檔、列與事件不符：" + "、".join(why))]
    return [to_finding(sub, v) for v in (_mac_verdict(audit),) if v.status != "ok"]


def obs_console_audit(repo: Path, events: list[dict]) -> list[Finding]:
    """R98 (d)：Console 寫入 OBS 的對帳。稽核檔不在場／金鑰缺＝nonblocking NE（不是零筆通過）。"""
    rows = si_refs.obs_rows(repo)
    adds = [e for e in events if e["kind"] == "obs.add"]
    out: list[Finding] = []
    for row in rows.values():
        marks = si_rows.row_marks(row)
        if marks.get("carrier", ("", 0))[0] == "console" and "audit_ref" in marks:
            out += _console_add(row, adds, marks["audit_ref"][0])
    for ev in (e for e in events if e["kind"] == "obs.close"):
        out += _console_close(ev, rows.get(ev.get("obs")))
    return out


def _before(events: list[dict], seq: int, kind: str, prop: str, rev=None) -> dict | None:
    hits = [e for e in events if e["kind"] == kind and e.get("prop") == prop and e["seq"] < seq
            and (rev is None or e.get("rev") == rev)]
    return hits[-1] if hits else None


def verdict_item(events: list[dict], params: dict, valid: set[str]) -> list[Finding]:
    """R98 (c)：對每筆 `app.verify` 以 `verdict_of` 由記錄欄位重算並比對（欄位全部自洽的偽 PASS 不被
    偵測，誠實劃界）；`min_heldout` 或 `verify_runs_max` 無效時不判（NE）。"""
    if not {"min_heldout", "verify_runs_max"} <= valid:
        return si_params.ne_findings("min_heldout 或 verify_runs_max 無效，無法重算 verdict")
    out = []
    for e in events:
        if e["kind"] != "app.verify":
            continue
        sb = _before(events, e["seq"], "app.sandbox", e["prop"], e["rev"])
        fr = _before(events, e["seq"], "heldout.freeze", e["prop"])
        want_v, want_r = verdict.verdict_of(sb, e, fr, params["min_heldout"])
        rec = e["reasons"]
        why = []
        if want_v != e["verdict"]:
            why.append(f"verdict 記 {e['verdict']}，重算為 {want_v}")
        if not set(want_r) <= set(rec):
            why.append(f"reasons 缺重算得出的碼 {sorted(set(want_r) - set(rec))}")
        extra = set(rec) - set(want_r) - set(verdict.RECORDED_ONLY)
        if extra:
            why.append(f"reasons 含無法由欄位導出的碼 {sorted(extra)}")
        if verdict.sandbox_layer(sb) is not None and (e["probes_n"] != 0
                                                      or e["verify_sha256"] is not None):
            why.append("沙盒失敗（⓪）而 probes_n 不為 0 或 verify_sha256 不為 null")
        if why:
            out.append(Finding(f"seq={e['seq']}", "VERDICT-MISMATCH", "fail", "；".join(why)))
    return out


def helmsman_refs(repo: Path, events: list[dict]) -> list[Finding]:
    """R98 (e)：`research.skip`（`helmsman`）的 `sid`／`line` 只驗真人載體與文字非空。"""
    out = []
    for e in events:
        if e["kind"] == "research.skip" and e.get("reason") == "helmsman":
            v = decverify.verify_human_ref(repo, str(e.get("sid")), e.get("line") or 0)
            if v.status == "fail":
                out.append(Finding(f"seq={e['seq']}", "HELMSMAN-REF-INVALID", "fail",
                                   f"{v.code} {v.detail}".strip()))
            elif v.status == "ne":
                out.append(to_finding(f"seq={e['seq']}", v))
    return out
