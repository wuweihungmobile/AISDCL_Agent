"""SelfImproving `status`：啟動事件偵測與狀態摘要（TCS-SelfImproving-P1 R60）。

唯讀、離線、無常駐行程；`export --kind status` 的 `items[0]` 由同一個 `build` 產生。事件偵測的
窗＝最近一筆 `run.close` 之後的事件；量不到的來源進 `unavailable`、不併入零；容量事件（e）在
P3 的 `capacity` 動詞建成前印 NOT-EVALUABLE、不得印成零。
"""

from __future__ import annotations

import json
from pathlib import Path

from . import consoleaudit
from . import events as si_events
from . import fold as si_fold
from . import scan as si_scan
from . import transcript as si_transcript
from .git import Git

_REOPENED_STATES = ("promoted", "measuring", "closed")


def _friction(repo: Path) -> dict:
    """交卷對帳（NFR-SI-09-2）：逐字稿目錄取不到＝transcript-unavailable；取得到而 P1 未建解析器
    （「流程摩擦」節項數的解析屬刻意不做，TCS §4）＝transcript-parser-not-established。
    兩者皆 NOT-EVALUABLE、絕不印成 0。"""
    found = si_transcript.transcript_dir(repo).is_dir()
    return {"status": "NOT-EVALUABLE",
            "reason": "transcript-parser-not-established" if found else "transcript-unavailable"}


def _detect(f: si_fold.Folded, window: list[dict], hits: list) -> list[dict]:
    out: list[dict] = []
    for ev in window:
        if ev.get("kind") != "attr.confirm":
            continue
        att = f.atts.get(ev.get("att"))
        if att is None or att.type != "link":
            continue
        out.append({"trigger": "b", "subject": att.id,
                    "detail": f"同一症狀再現、經審查者確認（reopens {att.ev.get('reopens')}）"})
        for p in f.props.values():
            if p.state in _REOPENED_STATES and att.ev.get("reopens") in p.sources:
                out.append({"trigger": "d", "subject": p.id,
                            "detail": f"已確認的復發連結落在已採納的提案（{att.id}）"})
    out += [{"trigger": "c", "subject": r.ident,
             "detail": f"缺陷帳本新立 {r.severity} 未結列（發現日期 {r.date}）"} for r in hits]
    return sorted(out, key=lambda e: (e["trigger"], e["subject"]))


def console_pending(events: list[dict], read_home: bool = True) -> dict:
    """R99 (a)：`<si>/console_audit/<uuid>.json` 中尚無對應事件者（只列檔名與 `kind`）；
    目錄不存在或讀不到＝NOT-EVALUABLE；`export` 不讀家目錄，恆為 `export-reads-no-home`。"""
    if not read_home:
        return {"status": "NOT-EVALUABLE", "reason": "export-reads-no-home"}
    box = si_events.si_dir() / consoleaudit.AUDIT_DIR
    try:
        names = sorted(p for p in box.iterdir() if p.is_file())
    except OSError:
        return {"status": "NOT-EVALUABLE", "reason": "home-unavailable"}
    used = {e.get("audit_ref") for e in events if e["kind"] in ("dec", "obs.add", "obs.close")}
    items = []
    for p in names:
        if p.suffix != ".json" or not si_events.valid_uuid(p.stem) or p.stem in used:
            continue
        try:
            kind = json.loads(p.read_bytes().decode("utf-8")).get("kind")
        except (OSError, ValueError, AttributeError):
            kind = None
        items.append({"audit_ref": p.stem, "kind": kind if kind in consoleaudit.KINDS else None})
    items.sort(key=lambda i: i["audit_ref"])
    return {"status": "read", "count": len(items), "items": items}


def build(repo: Path, git: Git, params: dict, read_home: bool = True) -> dict:
    """狀態物件；鍵序固定（R60；其後附加末鍵 `console_pending`，R99）。"""
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL)
    f = si_fold.fold(events or [], params.get("stop_after_bad"))
    closes = [e["seq"] for e in events or [] if e.get("kind") == "run.close"]
    window = [e for e in events or [] if not closes or e["seq"] > closes[-1]]
    a = si_scan.anchor(git, events, params, None)
    hits, why = si_scan.defect_hits(repo, a)
    unavailable = [{"trigger": "c", "reason": why}] if why else []
    detected = _detect(f, window, hits)
    link_ids = {a_.id for a_ in f.atts.values() if a_.type == "link"}
    return {
        "events_detected": detected,
        "unavailable": unavailable,
        "open_runs": [{"run": r.id, "opened_seq": r.opened_seq,
                       "research": ({"kind": r.research[0], "seq": r.research[1]}
                                    if r.research else None), "props": list(r.prop_ids)}
                      for r in f.runs.values() if r.closed_seq is None],
        "pending_props": [{"id": p.id, "rev": p.rev, "state": p.state, "route": p.route,
                           "digest8": p.digest.split(":", 1)[-1][:8]}
                          for p in f.props.values() if p.state in ("proposed", "verified")],
        "suspended": f.suspended,
        "cooldowns": f.cooldowns,
        "skip_reasons": dict(f.skip_reasons),
        "capacity": {"status": "NOT-EVALUABLE", "reason": "capacity-verb-not-established"},
        "root_cause_changes": f.root_cause_changes,
        "reopen_candidates": {"unsettled": sum(1 for i in link_ids if f.atts[i].settled is None)},
        "pending_windows": f.pending_windows,
        "friction_reconcile": _friction(repo),
        "no_event": not detected,
        "console_pending": console_pending(events or [], read_home),
    }


def render_json(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"


def render_text(obj: dict) -> str:
    k = len(obj["unavailable"])
    lines = [f"events_detected: {len(obj['events_detected'])}"]
    lines += [f"  {e['trigger']} {e['subject']} {e['detail']}" for e in obj["events_detected"]]
    lines += [f"  unavailable {u['trigger']} {u['reason']}" for u in obj["unavailable"]]
    runs = "、".join(f"{r['run']}（props={len(r['props'])}）" for r in obj["open_runs"]) or "無"
    pend = "、".join(f"{p['id']}={p['state']}" for p in obj["pending_props"]) or "無"
    sus = obj["suspended"]["run"] if obj["suspended"] else "null"
    cools = "、".join(c["prop"] for c in obj["cooldowns"]) or "無"
    skips = " ".join(f"{k_}={v}" for k_, v in obj["skip_reasons"].items())
    fr = obj["friction_reconcile"]
    lines += [f"open_runs: {runs}", f"pending_props: {pend}", f"suspended: {sus}",
              f"cooldowns: {cools}", f"skip_reasons: {skips}", "capacity NOT-EVALUABLE "
              f"（{obj['capacity']['reason']}）",
              f"root_cause_changes: {obj['root_cause_changes']}",
              f"reopen_candidates: unsettled={obj['reopen_candidates']['unsettled']}",
              f"pending_windows: {len(obj['pending_windows'])}",
              f"friction_reconcile: {fr['status']}（{fr.get('reason', '')}）"]
    cp = obj["console_pending"]
    lines.append(f"console_pending: {cp['count']}" if cp["status"] == "read"
                 else f"console_pending: NOT-EVALUABLE（{cp['reason']}）")
    if obj["no_event"]:
        lines.append("無事件" + (f"（{k} 個來源量不到）" if k else ""))
    return "\n".join(lines) + "\n"
