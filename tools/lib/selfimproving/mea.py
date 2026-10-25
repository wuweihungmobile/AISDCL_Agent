"""SelfImproving 採納後量測窗的列宇宙、再現歸屬、基線窗與採納窗（TCS-SelfImproving-P3 R116～R121）。

能力類別 `ro`：只讀事件與帳本、不寫檔、不呼叫 git 以外的子行程；`measure`、`status`、`export`、
量測探針共用這一份窗規則（單一實作，不得有第二份）。全部時刻是 aware datetime；DEF 列日精度，
一律保守化為發現日期當天 `23:59:59+00:00`。規劃（`mea.plan`）住 `meaplan.py`。
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from . import fold as si_fold
from . import meacheck
from . import refs as si_refs
from .defs import load_rows
from .git import Git
from .ledger import parse_ledger
from .rows import TIME_RE, path_set, row_marks

_QUALITY = "docs/06_quality"
_DEF_REOPEN_RE = re.compile(r"reopens:(DEF-\d+-\d+)")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INVALID = "mea-events-invalid"  # `mea.*` 事件欄位不合 ⇒ 窗與指標不可評估（消費端共用的理由碼）


@dataclass(frozen=True)
class Row:
    id: str
    kind: str  # "OBS" 或 "DEF"
    at: datetime
    day: str  # 列上顯示的日期字面（窗序第一鍵）
    num: int
    paths: frozenset
    coords: str  # 證據座標格原文
    text: str  # 證據座標格 casefold（M 類檔名比對）
    reopens: str | None
    disp: str  # OBS 處置欄／DEF 狀態欄原文
    cls: str | None  # DEF 的結案類


@dataclass
class Prop:
    id: str
    cls: str
    targets: list
    sources: list
    seq: int
    at: datetime
    ack: bool
    dir: str


@dataclass
class Ctx:
    params: dict
    events: list
    f: si_fold.Folded
    rows: list = field(default_factory=list)
    anchor: datetime | None = None
    obs_ok: bool = True
    def_ok: bool = True
    unplaced: int = 0
    obs_n: int = 0
    props: list = field(default_factory=list)
    links: dict = field(default_factory=dict)
    roots: dict = field(default_factory=dict)
    by_id: dict = field(default_factory=dict)
    rollbacks: dict = field(default_factory=dict)
    bad: list = field(default_factory=list)  # meacheck.field_problems：非空＝不可評估


def parse_t(text) -> datetime | None:
    """事件 `t`／`decided_at`（帶 offset 的 ISO 8601）→ aware datetime；不合回 None。"""
    try:
        out = datetime.fromisoformat(text) if isinstance(text, str) else None
    except ValueError:
        return None
    return out if out is not None and out.utcoffset() is not None else None


def iso_utc(at: datetime) -> str:
    return at.astimezone(UTC).isoformat(timespec="seconds")


def _cell_instant(cell: str, tz: str | None) -> tuple[datetime, str] | None:
    m = TIME_RE.match(cell)
    if not m:
        return None
    y, mo, d, h, mi, s, off = m.groups()
    off = (off or tz or "").strip()
    if not off:
        return None
    sign = -1 if off[0] == "-" else 1
    zone = timezone(sign * timedelta(hours=int(off[1:3]), minutes=int(off[4:6])))
    try:
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0), tzinfo=zone), \
            f"{y}-{mo}-{d}"
    except ValueError:
        return None


def _num(ident: str) -> int:
    tail = ident.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _obs_ledger_ok(repo: Path) -> bool:
    """R122 (d)：OBS 主檔存在、為 UTF-8（容 BOM／CRLF）且有合法表頭（有表頭而零列＝合法空帳本）。"""
    try:
        raw = (repo / _QUALITY / "SelfImproving_Observation_Ledger.md").read_bytes()
        return parse_ledger(raw.decode("utf-8")).header_ok
    except (OSError, UnicodeDecodeError):
        return False


def _universe(repo: Path, ctx: Ctx) -> None:
    seen: set[str] = set()
    texts = [si_refs.obs_ledger_text(repo), *si_refs.archive_texts(repo)]
    ctx.obs_ok = _obs_ledger_ok(repo)
    for text in texts:
        led = parse_ledger(text or "")
        for row in led.rows:
            if not (row.nine and row.kind == 1) or row.ident in seen:
                continue
            seen.add(row.ident)
            ctx.obs_n += 1
            placed = _cell_instant(row.cells[1], led.tz)
            if placed is None:
                ctx.unplaced += 1
                continue
            mark = row_marks(row).get("reopens")
            ctx.rows.append(Row(row.ident, "OBS", placed[0], placed[1], _num(row.ident),
                                frozenset(path_set(row.cells[4])), row.cells[4],
                                row.cells[4].casefold(), mark[0] if mark else None,
                                row.cells[7], None))
    qdir = repo / _QUALITY
    files = sorted(qdir.glob("AutoSDD_Defect_Log*.md")) if qdir.is_dir() else []
    files += [qdir / n for n in ("AutoSDD_External_Blocked_Log.md",
                                 "AutoSDD_Structural_Debt_Log.md") if (qdir / n).is_file()]
    ctx.def_ok = bool(files)
    for path in files:
        for r in load_rows(path):
            if r.ident in seen:
                continue
            seen.add(r.ident)
            if not _DATE_RE.match(r.date):
                ctx.unplaced += 1
                continue
            at = parse_t(r.date + "T23:59:59+00:00")
            if at is None:
                ctx.unplaced += 1
                continue
            hit = _DEF_REOPEN_RE.search(r.evidence)
            ctx.rows.append(Row(r.ident, "DEF", at, r.date, _num(r.ident),
                                frozenset(path_set(r.evidence)), r.evidence,
                                r.evidence.casefold(), hit.group(1) if hit else None,
                                r.status_text, r.status))


def universe(repo: Path) -> dict:
    """列宇宙：ID → `Row`（OBS 主檔與 archive、缺陷帳本家族）；`churn` 的 capability-delta 用。"""
    ctx = Ctx({}, [], si_fold.Folded())
    _universe(repo, ctx)
    return {r.id: r for r in ctx.rows}


def _common_dir(targets: list) -> str:
    dirs = [[x for x in posixpath.dirname(t.replace("\\", "/").casefold()).split("/") if x]
            for t in targets]
    common: list = []
    for parts in zip(*dirs) if dirs else ():
        if len(set(parts)) != 1:
            break
        common.append(parts[0])
    return "/".join(common)


def build_ctx(repo: Path, git: Git, params: dict, events: list) -> Ctx:
    f = si_fold.fold(events, params.get("stop_after_bad"), params.get("verify_runs_max"))
    ctx = Ctx(params, events, f)
    ctx.bad = meacheck.field_problems(events)
    _universe(repo, ctx)
    ctx.rows.sort(key=win_key)
    ctx.by_id = {r.id: r for r in ctx.rows}
    sha = params.get("migration_base_sha")
    stamp = git.commit_time(sha) if isinstance(sha, str) and git.available \
        and git.is_commit(sha) else None
    ctx.anchor = datetime.fromtimestamp(stamp, UTC) if stamp is not None else None
    for p in sorted(f.props.values(), key=lambda x: x.id):
        when = parse_t(p.promote_t)
        if p.promote_seq is not None and when is not None:
            ctx.props.append(Prop(p.id, p.cls, list(p.target), list(p.sources), p.promote_seq,
                                  when, p.ack, _common_dir(p.target)))
    for a in f.atts.values():
        if a.type == "link" and isinstance(a.ev.get("from"), str):
            ctx.links.setdefault(a.ev["from"], []).append(a)
        elif a.type == "root":
            for obs in a.ev.get("obs") if isinstance(a.ev.get("obs"), list) else []:
                ctx.roots.setdefault(obs, []).append(a)
    for e in events:
        at = parse_t(e.get("decided_at"))
        if e.get("kind") == "dec" and e.get("dkind") == "rollback" and at is not None:
            ctx.rollbacks.setdefault(e.get("prop"), []).append(at)
    return ctx


def win_key(r: Row) -> tuple:
    """R116 (d)：窗序＝（日期字面, ID 末段數字, ID 全文位元組序）。"""
    return (r.day, r.num, r.id.encode("utf-8"))


def _settled(a, cutoff: int | None):
    s = a.settled
    return s if s is not None and (cutoff is None or s[1] < cutoff) else None


def own_keys(ctx: Ctx, rid: str, cutoff: int | None = None) -> set:
    """R118 (c)：已被 `attr.confirm` 確認（基線計算時須早於 `cutoff`）之 root attr 的根因鍵。"""
    return {a.ev["root_cause"] for a in ctx.roots.get(rid, [])
            if (s := _settled(a, cutoff)) and s[0] == "attr.confirm"
            and isinstance(a.ev.get("root_cause"), str)}


def prop_keys(ctx: Ctx, p: Prop, cutoff: int | None = None) -> set:
    return si_fold.confirmed_root_causes(ctx.f, p.sources, cutoff)


def _links(ctx: Ctx, rid: str, cutoff: int | None) -> list:
    return [a for a in ctx.links.get(rid, []) if cutoff is None or a.seq < cutoff]


def is_candidate(ctx: Ctx, r: Row, cutoff: int | None = None) -> bool:
    return r.kind == "OBS" and (r.reopens is not None or bool(_links(ctx, r.id, cutoff)))


def cand_state(ctx: Ctx, rid: str, cutoff: int | None = None) -> tuple[str, int | None]:
    """R118 (b)：（confirmed／rejected／open, 使其落定的事件 seq）；基線時 `cutoff`＝SP。"""
    ls = _links(ctx, rid, cutoff)
    sets = [_settled(a, cutoff) for a in ls]
    confirms = [s[1] for s in sets if s and s[0] == "attr.confirm"]
    if confirms:
        return "confirmed", min(confirms)
    if ls and all(sets):
        return "rejected", max(s[1] for s in sets)
    return "open", None


def cand_keys(ctx: Ctx, r: Row, cutoff: int | None = None) -> set:
    reopened = {a.ev.get("reopens") for a in _links(ctx, r.id, cutoff)} or {r.reopens}
    return own_keys(ctx, r.id, cutoff).union(*[own_keys(ctx, x, cutoff) for x in reopened if x])


def covers(ctx: Ctx, p: Prop, r: Row, cutoff: int | None = None) -> bool:
    """R117 (a)(b)：機會列涵蓋範圍（不含 (c) 的再現優先）。"""
    if p.cls == "M":
        names = [posixpath.basename(t.replace("\\", "/")).casefold() for t in p.targets]
        keys = cand_keys(ctx, r, cutoff) if is_candidate(ctx, r, cutoff) else own_keys(
            ctx, r.id, cutoff)
        return bool(keys & prop_keys(ctx, p, cutoff)) or any(n and n in r.text for n in names)
    return any(q == p.dir or q.startswith(p.dir + "/") for q in r.paths) if p.dir else bool(
        r.paths)


def owner_of(ctx: Ctx, r: Row) -> Prop | None:
    """R118 (d)：候選歸屬於最近晉升（`app.promote` 的 seq 最大）的、鍵相交且涵蓋它的 PROP。"""
    if not is_candidate(ctx, r):
        return None
    keys = cand_keys(ctx, r)
    hits = [p for p in ctx.props if r.at > p.at and keys & prop_keys(ctx, p)
            and covers(ctx, p, r)]
    return max(hits, key=lambda p: p.seq) if hits else None


def baseline(ctx: Ctx, p: Prop) -> dict:
    """R119：基線窗與基線報告（確定性：只由帳本內容、事件序與 `p.seq` 決定，不讀現在時刻）。"""
    w, sp, keys = ctx.params["w_opp"], p.seq, prop_keys(ctx, p, p.seq)
    opp: list = []
    recurs: list = []
    for r in ctx.rows:
        if r.at >= p.at or (ctx.anchor is not None and r.at < ctx.anchor):
            continue
        hit = is_candidate(ctx, r, sp) and cand_keys(ctx, r, sp) & keys and covers(ctx, p, r, sp)
        state = cand_state(ctx, r.id, sp)[0] if hit else "rejected"
        if hit and state != "rejected":
            recurs.append((r, state))
        elif covers(ctx, p, r, sp):
            opp.append(r)
    opp = opp[-w:]
    start = opp[0].at if len(opp) >= w else ctx.anchor
    ranged = [(r, s) for r, s in recurs if start is None or r.at >= start]
    return {"opp": [r.id for r in opp], "events": sum(1 for _, s in ranged if s == "confirmed"),
            "pending": sum(1 for _, s in ranged if s == "open"),
            "anchor": iso_utc(ctx.anchor) if ctx.anchor is not None else None}


def window(ctx: Ctx, p: Prop, w_opp: int) -> dict:
    """R120：採納窗。回 `{"opp": 目前機會列數, "pending": 候選列, "close": None 或
    {"result", "n_opp", "at"}}`（再現／回滾／滿窗取時點最早者，同刻 再現 > 回滾 > 滿窗）。"""
    opp: list = []
    recurs: list = []
    pend: list = []
    for r in ctx.rows:
        if r.at <= p.at:
            continue
        mine = owner_of(ctx, r)
        state = cand_state(ctx, r.id)[0] if mine is not None and mine.id == p.id else None
        if state == "confirmed":
            recurs.append(r)
        elif state == "open":
            pend.append(r)
        elif covers(ctx, p, r):
            opp.append(r)
    rolls = sorted(t for t in ctx.rollbacks.get(p.id, []) if t > p.at)
    cands = [(recurs[0].at, 0, "recurred")] if recurs else []
    cands += [(rolls[0], 1, "rolled-back")] if rolls else []
    cands += [(opp[w_opp - 1].at, 2, "full")] if len(opp) >= w_opp else []
    out = {"opp": len(opp), "pending": pend, "close": None}
    if not cands:
        return out
    at, _, label = min(cands, key=lambda c: (c[0], c[1]))
    if label == "full":
        result = "pending" if any(r.at <= at for r in pend) else "clean"
        n_opp = w_opp
    else:
        result, n_opp = label, sum(1 for r in opp if r.at < at)
    out["close"] = {"result": result, "n_opp": n_opp, "at": iso_utc(at)}
    return out
