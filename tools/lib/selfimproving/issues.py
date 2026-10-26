"""SelfImproving 議題中心：聚合、篩選分頁、摘要與文字表（TCS-IssueCenter R-IC-10～R-IC-44）。

唯讀：在三類帳本（觀察、缺陷含兩條姊妹軌、事件）之上建一層人看得懂的議題視角，不寫任何檔、不碰
網路與子行程、不讀家目錄（PRD §5、§6）。本檔負責所有接縫——讀檔與可用性判斷、`fold`、`card`、
`status`、`events`，一律以模組屬性呼叫，測試才注入得進去——與對外輸出；議題物件的建構住
`issues_items.py`，狀態詞、結果、句型與封閉詞彙一律取自 `issuemap.py`，本檔不持有第二份。
`export --kind issues` 與 `issues` 動詞取同一個物件。
"""

from __future__ import annotations

import posixpath
import re
from datetime import datetime
from pathlib import Path

from . import card as si_card
from . import check as si_check
from . import defs as si_defs
from . import events as si_events
from . import fold as si_fold
from . import issuemap as im
from . import issues_items as items
from . import ledger as si_ledger
from . import scan as si_scan
from . import status as si_status
from .git import Git

ID_RE = re.compile(f"^{items.ID_RE.pattern}$")  # `--id` 的三種議題 ID 格式（大小寫敏感）
ARCHIVE_GLOB = "SelfImproving_Observation_Ledger_archive*.md"
SIBLINGS = ("AutoSDD_External_Blocked_Log.md", "AutoSDD_Structural_Debt_Log.md")
SIBLING_COLUMNS = ("DEF-ID", "解鎖條件（可機械查）", "最近複查日")
_QUALITY = posixpath.dirname(si_check.LEDGER_REL)
_RULE = re.compile(r":?-{3,}:?")  # 表格分隔列的一格


def _read(path: Path) -> str | None:
    """整檔 UTF-8 文字；缺檔、不可讀（含同名目錄）、非 UTF-8 一律 None＝該帳本不可用（D-R13）。"""
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _load_events(ctx: items.Ctx, repo: Path) -> list[dict] | None:
    """事件帳本的合格事件；不可用回 None。結構問題另讀原始行（D-R14，不經接縫 S3）。"""
    path = repo / si_events.LEDGER_REL
    events = si_events.load_sound_events(path)
    if events is None:
        ctx.note("ledger.events", "EVENT-LEDGER-UNAVAILABLE")
        return None
    try:
        lines = si_events.read_lines(path.read_bytes())
    except OSError:
        return events
    for ln in lines:
        if ln.obj is None:
            ctx.problem(f"L{ln.no}", "EVENT-PARSE", "空白行或非 JSON 物件的行")
        elif si_events.validate(ln.obj):
            ctx.problem(f"L{ln.no}", "EVENT-UNSOUND", "事件未通過 events.validate，已略過")
    return events


def _obs_rows(ctx: items.Ctx, text: str, rel: str, env: items.Env, seen: set) -> None:
    for row in si_ledger.parse_ledger(text).rows:
        if not row.nine:
            ctx.problem(row.subject, "ROW-ARITY", "欄數與表頭不符")
        elif row.kind != 1 or not si_ledger.ID_RE.match(row.ident):
            ctx.problem(row.subject, "ROW-ARITY", "ID 欄不合 OBS-SI-NNN")
        elif ctx.admit(seen, row.ident, int(row.ident.rsplit("-", 1)[1])):
            items.obs_item(ctx, row, rel, env)


def _load_obs(ctx: items.Ctx, repo: Path, env: items.Env) -> tuple[bool, bool]:
    """觀察主檔加依檔名排序的歸檔檔（先中者勝）；回（主檔可讀, 主檔與歸檔檔都讀得到）。"""
    main = repo / si_check.LEDGER_REL
    text = _read(main)
    if text is None:
        ctx.note("ledger.observation", "OBS-LEDGER-UNAVAILABLE")
        return False, False
    seen: set = set()
    _obs_rows(ctx, text, si_check.LEDGER_REL, env, seen)
    complete = True
    for path in sorted(main.parent.glob(ARCHIVE_GLOB)):
        text = _read(path)
        if text is None:
            ctx.note(f"ledger.observation.{path.name}", "OBS-LEDGER-UNAVAILABLE")
            complete = False
        else:
            _obs_rows(ctx, text, f"{_QUALITY}/{path.name}", env, seen)
    return True, complete


def _sibling_table(text: str):
    """姊妹軌〈缺陷總表〉：（表頭欄名, [(行號, 欄值)…]）；表頭須含三個欄名，其餘表（例「格式定義」
    的兩欄表）不是資料表。無合格表頭回 None。"""
    lines = si_ledger.split_lines(text)
    for i, line in enumerate(lines):
        head = si_ledger.split_cells(line)
        if head and set(SIBLING_COLUMNS) <= set(head):
            body = []
            for j in range(i + 1, len(lines)):
                cells = si_ledger.split_cells(lines[j])
                if cells is None:
                    break
                if not all(_RULE.fullmatch(c) for c in cells):
                    body.append((j + 1, cells))
            return head, body
    return None


def _siblings(ctx: items.Ctx, repo: Path) -> tuple[bool, list[dict]]:
    """兩條姊妹軌的資料列（欄數不符者不採用；兩檔重複的 ID 後者不收）；回（皆可用, 列）。"""
    ok, recs, seen = True, [], set()
    for idx, name in enumerate(SIBLINGS):
        rel = f"{_QUALITY}/{name}"
        text = _read(repo / rel)
        table = None if text is None else _sibling_table(text)
        if table is None:
            ctx.note(f"ledger.sibling.{name}", "SIBLING-LEDGER-UNAVAILABLE")
            ok = False
            continue
        head, body = table
        for lineno, cells in body:
            where = f"{name}:L{lineno}"
            if len(cells) != len(head):
                ctx.problem(where, "ROW-ARITY", "欄數與表頭不符")
                continue
            d = dict(zip(head, cells))
            ident, unlock, review = (d[c] for c in SIBLING_COLUMNS)
            if items.DEF_RE.fullmatch(ident) and ctx.admit(seen, ident, lineno, where):
                recs.append({"id": ident, "unlock": unlock, "review": review, "file": rel,
                             "line": lineno, "labels": head, "cells": cells,
                             "cursor": (3 + idx) * items.S + lineno})
    return ok, recs


def _load_defects(ctx: items.Ctx, repo: Path, sibs: list[dict]) -> bool:
    """缺陷主檔（不讀歸檔檔）；DEF-ID 在姊妹軌有列者狀態覆蓋為延後，主檔找不到的姊妹軌列成孤列。"""
    rel = si_scan.DEFECT_LOG_REL
    text = _read(repo / rel)
    cols = None if text is None else si_defs.columns(repo / rel)
    if text is None or cols is None:
        ctx.note("ledger.defect", "DEFECT-LEDGER-UNAVAILABLE")
        return False
    lines, labels = text.removeprefix("﻿").splitlines(), [c for c in cols if c]
    by_sib, seen, rows = {s["id"]: s for s in sibs}, set(), si_defs.load_rows(repo / rel)
    for row in rows:
        if not row.arity_ok:
            ctx.problem(row.ident, "ROW-ARITY", "欄數與表頭不符")
        elif ctx.admit(seen, row.ident, row.lineno):
            cells = si_ledger.split_cells(lines[row.lineno - 1]) or []
            items.def_item(ctx, row, rel, by_sib.get(row.ident), (labels, cells))
    listed = {r.ident for r in rows}
    for sib in sibs:
        if sib["id"] not in listed:
            items.orphan_item(ctx, sib, sib["cursor"])
    return True


class _Progress:
    """量測窗進度（R-IC-32）：有提案停在量測中時才呼叫一次 `status.measure_value`（接縫 S5）。"""

    def __init__(self, repo: Path, git: Git, params: dict, events: list[dict]) -> None:
        self.args, self.windows, self.w_opp = (repo, git, params, events), None, {}
        for e in events:
            if e["kind"] == "mea.open":
                self.w_opp.setdefault(e.get("prop"), e.get("w_opp"))

    def lookup(self, prop_id: str) -> tuple[int, int] | None:
        if self.windows is None:
            got = si_status.measure_value(*self.args)
            self.windows = ({w["prop"]: w["n_opp"] for w in got["windows"]}
                            if got.get("status") == "read" else {})
        n_opp, w_opp = self.windows.get(prop_id), self.w_opp.get(prop_id)
        return (n_opp, w_opp) if isinstance(n_opp, int) and isinstance(w_opp, int) else None


def _load_props(ctx: items.Ctx, repo: Path, git: Git, params: dict, events: list[dict],
                f: si_fold.Folded, obs_ok: bool) -> None:
    windows: dict = {}
    for w in si_fold.effective_windows(f):
        windows.setdefault(w["prop"], w["effective"])  # 首窗的生效結果（D-R9）
    rollbacks: dict = {}
    for e in events:
        if e["kind"] == "dec" and e.get("dkind") == "rollback":
            rollbacks.setdefault(e.get("prop"), []).append(e["seq"])
    stamps, cooling = {e["seq"]: e["t"] for e in events}, {c["prop"] for c in f.cooldowns}
    progress = _Progress(repo, git, params, events)
    for p in f.props.values():
        try:
            card = si_card.build(repo, git, events, f, p.id, params)
            symptom, text = card.fields.get("symptom", ""), card.text
        except si_card.CardError:
            symptom = text = None
        after = p.promote_seq  # D-R3：已決定回滾＝promote 之後的 dec(rollback) 筆數
        decided = 0 if after is None else sum(1 for s in rollbacks.get(p.id, ()) if s > after)
        items.prop_item(ctx, p, {
            "symptom": symptom, "card_text": text, "window": windows.get(p.id),
            "decided": decided, "progress": progress.lookup, "last_t": stamps.get(p.last_seq),
            "cooldown": "cooled" if p.unblocked else ("cooling" if p.id in cooling else None),
            "obs_ok": obs_ok})


def _summary(ctx: items.Ctx, whole: dict) -> dict:
    """整本帳計數（不受篩選、`since`、`limit` 影響）；讀不到的帳本所擋的格為 null（D-R5）。"""
    by_status = dict.fromkeys(im.STATUSES, 0)
    unmapped = 0
    for item in ctx.items.values():
        if item["status"] in by_status:
            by_status[item["status"]] += 1
        else:
            unmapped += 1
    dead = not (whole["obs"] and whole["events"])
    dead_split = dead or not (whole["defects"] and whole["siblings"])
    by_tab = {t: None if dead or (dead_split and t != im.TABS[1])
              else sum(by_status[s] for s in im.TAB_MEMBERS[t]) for t in im.TABS}
    return {"total": sum(by_status.values()) + unmapped, "by_status": by_status,
            "by_tab": by_tab, "unmapped": unmapped}


def build(repo: Path, git: Git, params: dict, *, since: int | None = None,
          limit: int | None = None, ident: str | None = None, statuses=None,
          sources=None) -> dict:
    """議題匯出物件（鍵序固定，TCS §C1）。用法錯誤由呼叫端先擋（rc 3）。`statuses`、`sources`＝
    旗標值串列（`statuses` 可含「待處理」別名）；`ident` 給定為單筆（加 raw、timeline，無 legend、
    summary）。游標序、篩選先於分頁、`problems` 與 `ne` 為整本帳一份。"""
    ctx = items.Ctx()
    if (head := git.head()) is None:
        ctx.note("head_sha", "git-unavailable")
    events = _load_events(ctx, repo)
    f = None if events is None else si_fold.fold(events, params.get("stop_after_bad"))
    env = items.Env() if f is None else items.Env(
        items.confirmed_obs(f.atts.values()), items.close_dates(events))
    obs_ok, obs_complete = _load_obs(ctx, repo, env)
    sibs_ok, sibs = _siblings(ctx, repo)
    defects_ok = _load_defects(ctx, repo, sibs)
    if f is not None:
        _load_props(ctx, repo, git, params, events, f, obs_ok)
        items.link_attrs(ctx, f.atts.values())
    items.finish(ctx)
    want = None if not statuses else {s for v in statuses for s in im.TAB_MEMBERS.get(v, (v,))}
    keep = [i for i in sorted(ctx.items, key=ctx.cursor.__getitem__)
            if (ident is None or i == ident) and (since is None or ctx.cursor[i] > since)
            and (want is None or ctx.items[i]["status"] in want)
            and (not sources or ctx.items[i]["source"] in sources)]
    cap = limit or params["export_limit_max"]
    truncated = ident is None and len(keep) > cap
    keep = keep[:cap] if ident is None else keep
    page = ([items.detail(ctx, i, events or [], f.props[i].run if f and i in f.props else None)
             for i in keep] if ident is not None else [ctx.items[i] for i in keep])
    obj = {"schema_rev": 1, "kind": "issues",
           "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
           "head_sha": head, "items": page,
           "next_since": ctx.cursor[keep[-1]] if truncated else None, "truncated": truncated,
           "ne": ctx.ne, "problems": ctx.problems}
    if ident is None:
        obj["legend"] = im.labels()
        obj["summary"] = _summary(ctx, {"obs": obs_complete, "events": events is not None,
                                        "defects": defects_ok, "siblings": sibs_ok})
    return obj


def parse_filters(status_arg: str | None, source_arg: str | None):
    """`--status`、`--source` 旗標值 → 值串列（None＝不篩）。逗號取聯集、值須全等（不去空白、
    不折疊全半形）、重複值去重；不合法值拋 ValueError，訊息列出合法值（呼叫端轉 rc 3）。"""
    def split(arg, legal, flag):
        if arg is None:
            return None
        pieces = arg.split(",")
        bad = [repr(v) for v in pieces if v not in legal]
        if bad:
            raise ValueError(f"{flag} 的值不合法：{'、'.join(bad)}；合法值：{'、'.join(legal)}")
        return list(dict.fromkeys(pieces))

    return (split(status_arg, (*im.STATUSES, im.TABS[0]), "--status"),
            split(source_arg, im.SOURCES, "--source"))


def sort_for_display(items_: list[dict], rule: str) -> list[dict]:
    """頁內顯示序（PRD §5.3、R-IC-33）。`pending`：順位（無順位或非 rankable 最後）→ 嚴重度 →
    最後更新（最久沒動在前）→ 編號，null 一律最後；`done`：最後更新新→舊（null 最後）→ 編號。"""
    base = sorted(items_, key=lambda i: i["id"])
    if rule == "done":
        dated = sorted((i for i in base if i["updated_at"]), key=lambda i: i["updated_at"],
                       reverse=True)
        return dated + [i for i in base if not i["updated_at"]]

    def key(i: dict) -> tuple:
        pri = i.get("priority") if i["rankable"] else None
        sev, day = i["severity_rank"], i["updated_at"]
        return (pri is None, pri or 0, sev is None, sev or 0, day is None, day or "", i["id"])

    return sorted(items_, key=key)


def render_text(obj: dict, statuses=None) -> str:
    """純文字中文表：每議題一行「編號、來源、嚴重度、狀態[・結果]、最後更新、標題→下一步」，前五欄依顯示
    寬度對齊（欄間兩空白、null 為「—」）；末行「共 N 件；問題 M 筆」。頁內序依 D-R6。"""
    rule = "pending" if statuses and all(v in im.PENDING_VIEW for v in statuses) else "done"
    ordered = sort_for_display(obj["items"], rule)
    cells = [[i["id"], i["source"] or "—", i["severity"] or "—",
              i["status"] + (f"・{i['result']}" if i["result"] else ""), i["updated_at"] or "—"]
             for i in ordered]
    wide = [max((si_card.width(r[c]) for r in cells), default=0) for c in range(5)]
    lines = ["  ".join(v + " " * (w - si_card.width(v)) for v, w in zip(row, wide))
             + f"  {item['title']}→{item['next_step']}" for row, item in zip(cells, ordered)]
    tail = f"共 {len(cells)} 件；問題 {len(obj['problems'])} 筆"
    if obj["truncated"]:
        tail += f"；尚有更多，--since {obj['next_since']}"
    return "\n".join([*lines, tail]) + "\n"
