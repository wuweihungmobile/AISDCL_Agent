"""SelfImproving `export`：唯讀序列化帳本給 Console（TCS-SelfImproving-P1 R61）。

離線、只用標準庫、不讀不印家目錄；與 `status`、`card`、`check` 共用 `fold`／`card`／`status`
（不得有第二份折疊或卡面實作）。單一 JSON 文件，位元組直寫、鍵序固定、無 BOM。`ne` 逐一列出量不到
的欄位，`problems` 列帳本結構層問題（壞列、壞行）；兩者非空都不是錯誤。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import card as si_card
from . import events as si_events
from . import fold as si_fold
from . import issues as si_issues
from . import meaplan as si_meaplan
from . import paths as si_paths
from . import refs as si_refs
from . import rows as si_rows
from . import scan as si_scan
from . import status as si_status
from .git import Git
from .ledger import parse_ledger

KINDS = ("observations", "events", "proposals", "runs", "status", "issues")
_CARRIER = {"field": "events", "reason": "carrier-not-established"}


def _num(ident: str) -> int:
    tail = ident.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _observations(repo: Path, problems: list) -> list[dict]:
    text = si_refs.obs_ledger_text(repo)
    out = []
    for row in parse_ledger(text).rows if text else []:
        if not row.nine:
            out.append({"line": row.lineno, "raw": row.raw, "valid": False,
                        "_cursor": _num(row.ident)})
            problems.append({"subject": row.subject, "code": "ROW-ARITY",
                             "detail": "欄數不是 9 或行未以 | 結尾"})
            continue
        keys = ("id", "time", "context", "symptom", "evidence", "category", "severity",
                "disposition", "marks")
        item = dict(zip(keys, row.cells))
        item["marks_kv"] = {k: v for k, (v, _) in si_rows.row_marks(row).items()}
        item["line"] = row.lineno
        found = {si_scan.bucket_of(p) for p in si_rows.path_fragments(row.cells[4])}
        item["buckets"] = [b for b in (*si_scan.BUCKETS, "未分類") if b in found] or ["未分類"]
        item["_cursor"] = _num(row.ident)
        out.append(item)
    return out


def _events(repo: Path, problems: list) -> list[dict]:
    path = repo / si_events.LEDGER_REL
    if not path.is_file():
        return []
    out = []
    for ln in si_events.read_lines(path.read_bytes()):
        if ln.obj is None:
            problems.append({"subject": f"L{ln.no}", "code": "EVENT-PARSE",
                             "detail": "空白行或非 JSON 物件的行"})
        else:
            out.append({**ln.obj, "_cursor": ln.obj.get("seq", 0)
                        if isinstance(ln.obj.get("seq"), int) else 0})
    return out


def _proposals(repo: Path, git: Git, events: list[dict], f: si_fold.Folded,
               params: dict, ne: list) -> list[dict]:
    out = []
    for p in f.props.values():
        patch = repo / si_events.PROPOSALS_REL / p.id / f"r{p.rev}.patch"
        try:
            touched = si_paths.touched_of(patch.read_bytes())
        except (OSError, si_paths.PatchError) as exc:
            touched = None
            why = "PATCH-UNREADABLE" if isinstance(exc, OSError) else "PATCH-INVALID"
            ne.append({"field": f"proposals.{p.id}.touched", "reason": why})
        try:
            card = si_card.build(repo, git, events, f, p.id, params).text
        except si_card.CardError as exc:
            card = None
            ne.append({"field": f"proposals.{p.id}.card", "reason": exc.code})
        cool = next((c for c in f.cooldowns if c["prop"] == p.id), None)
        out.append({"id": p.id, "state": p.state, "route": p.route, "cls": p.cls,
                    "action": p.action, "run": p.run, "rev": p.rev, "digest": p.digest,
                    "target": p.target, "touched": touched,
                    "touched_count": len(touched) if touched is not None else None,
                    "sources": p.sources, "created_seq": p.created_seq, "last_seq": p.last_seq,
                    "verdict": p.verdict, "flags": p.flags, "cooldown": cool, "card": card,
                    "window": si_meaplan.export_window(events, f, p.id), "_cursor": _num(p.id)})
    return out


def _runs(f: si_fold.Folded) -> list[dict]:
    return [{"id": r.id, "opened_seq": r.opened_seq, "closed_seq": r.closed_seq,
             "trigger": r.trigger, "head_sha": r.head_sha,
             "research": {"kind": r.research[0], "seq": r.research[1]} if r.research else None,
             "prop_ids": list(r.prop_ids), "outcome": r.outcome, "_cursor": _num(r.id)}
            for r in f.runs.values()]


def build(repo: Path, git: Git, params: dict, kind: str, since: int | None,
          limit: int | None, ident: str | None, statuses=None, sources=None) -> dict:
    """匯出物件（鍵序固定）。用法錯誤由呼叫端先擋（rc 3）。`issues` 轉呼叫議題中心的同一個
    `issues.build`（`statuses`、`sources` 只配該 kind）。"""
    if kind == "issues":
        return si_issues.build(repo, git, params, since=since, limit=limit, ident=ident,
                               statuses=statuses, sources=sources)
    problems: list[dict] = []
    ne: list[dict] = []
    head = git.head()
    if head is None:
        ne.append({"field": "head_sha", "reason": "git-unavailable"})
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL)
    f = si_fold.fold(events or [], params.get("stop_after_bad"))
    if events is None and kind != "observations":
        ne.append(dict(_CARRIER))
    if kind == "observations":
        items = _observations(repo, problems)
    elif kind == "events":
        items = _events(repo, problems)
    elif kind == "proposals":
        items = _proposals(repo, git, events or [], f, params, ne)
    elif kind == "runs":
        items = _runs(f)
    else:
        items = [si_status.build(repo, git, params, read_home=False)]
    nxt, truncated = None, False
    if kind != "status":
        items.sort(key=lambda i: i["_cursor"])
        if ident is not None:
            items = [i for i in items if i.get("id") == ident]
        if since is not None:
            items = [i for i in items if i["_cursor"] > since]
        cap = limit or params["export_limit_max"]
        truncated = len(items) > cap
        items = items[:cap]
        nxt = items[-1]["_cursor"] if truncated else None
        for i in items:
            i.pop("_cursor", None)
    return {"schema_rev": 1, "kind": kind,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "head_sha": head, "items": items, "next_since": nxt, "truncated": truncated,
            "ne": ne, "problems": problems}


def render(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"
