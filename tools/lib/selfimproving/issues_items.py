"""議題中心的議題物件建構（TCS-IssueCenter R-IC-13～R-IC-32；PRD §5.1、§5.2）。

一個可變容器 `Ctx` 加一組建構函式：本檔不讀檔，也不呼叫 git、fold、card、status——那些接縫住
`issues.py`（以模組屬性呼叫，測試才注入得進去）。建構函式吃已解析的列與查表結果、回議題物件，並把
表外值與量不到的欄位記進整本帳一份的 `problems`、`ne`；狀態詞與句型一律取自 `issuemap`，本檔不持有
第二份（TCS R-IC-73）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from . import issuemap as im
from . import rows as si_rows
from .events import LEDGER_REL as EVENTS_REL
from .ledger import COLUMNS

S = 10_000_000  # 游標基數（D-R4；< 2^31，相容 backend 的 Integer since）
TITLE_MAX, EXCERPT_MAX = 80, 40
ID_RE = re.compile(r"(?:OBS-SI-\d{3,}|PROP-SI-\d{3,}|DEF-\d+-\d+)")
DEF_RE = re.compile(r"DEF-\d+-\d+")
_DAY_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_REOPEN_RE = re.compile(r"^再開症狀\s*[：:]\s*")
_MARKUP = ("**", "__", "~~", "`")


class Ctx:
    """一次 build 的共用可變狀態：議題、游標、關聯、原列，與整本帳一份的 `ne`、`problems`。"""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self.cursor: dict[str, int] = {}
        self.raw: dict[str, tuple[list, list]] = {}
        self.out: dict[str, set[str]] = {}
        self.ne: list[dict] = []
        self.problems: list[dict] = []

    def note(self, field_name: str, reason: str) -> None:
        self.ne.append({"field": field_name, "reason": reason})

    def problem(self, subject: str, code: str, detail: str) -> None:
        self.problems.append({"subject": subject, "code": code, "detail": detail})

    def unmapped(self, subject: str, dim: str, raw: str) -> str:
        """記一筆 UNMAPPED（原值逐字、一值一筆）並回顯示用的「未歸類：<原值>」。"""
        self.problem(subject, "UNMAPPED", f"{dim}：{raw}")
        return im.unmapped(raw)

    def link(self, src: str, dst: str, both: bool = True) -> None:
        if src != dst:
            self.out.setdefault(src, set()).add(dst)
            if both:
                self.out.setdefault(dst, set()).add(src)

    def admit(self, seen: set, ident: str, num: int, subject: str | None = None) -> bool:
        """同編號只收第一列（後列記 ID-DUP）；編號或行號 ≥ S 者游標編不進去，不成議題。"""
        if ident in seen:
            self.problem(ident, "ID-DUP", "同編號多列，只收第一列")
        elif num >= S:
            self.problem(subject or ident, "ROW-ARITY", "編號或行號過大，游標無法編碼")
        else:
            seen.add(ident)
            return True
        return False

    def add(self, item: dict, cursor: int, raw: tuple[list, list]) -> None:
        self.items[item["id"]] = item
        self.cursor[item["id"]] = cursor
        self.raw[item["id"]] = raw


@dataclass
class Env:
    """觀察列判定所需的事件帳本查表。"""

    confirmed: frozenset = frozenset()  # 已確認歸因（路徑 A）的觀察號
    close_date: dict = field(default_factory=dict)  # 觀察號 → 最晚的 obs.close 日期


def clean_title(text: str) -> str:
    """去 markdown 記號、空白折疊；超過 80 個 code point 取前 80 加「…」（「…」不計入）。"""
    for mark in _MARKUP:
        text = text.replace(mark, "")
    text = " ".join(text.split())
    return text if len(text) <= TITLE_MAX else text[:TITLE_MAX] + "…"


def _valid_day(parts) -> str | None:
    try:
        return date(*map(int, parts)).isoformat()
    except ValueError:
        return None


def day_of(text: str | None) -> str | None:
    """字串的日期部分（直取、不換算時區）；解不出回 None。"""
    m = _DAY_RE.match(text or "")
    return _valid_day(m.groups()) if m else None


def _time_day(cell: str) -> str | None:
    m = si_rows.TIME_RE.match(cell)
    return _valid_day(m.groups()[:3]) if m else None


def _status(ctx: Ctx, ident: str, kind: str, key, raw: str, **cond):
    """歸類；表外值 fail-loud（顯示「未歸類：<原值>」並記 UNMAPPED，不歸入任何類、不丟該筆）。"""
    hit = im.classify(kind, key, **cond)
    if hit is None:
        return ctx.unmapped(ident, "狀態", raw), None, "N19"
    if im.is_unmapped(hit[1]):
        ctx.problem(ident, "UNMAPPED", f"結果：{hit[1][len(im.MARK):]}")
    return hit


def _severity(ctx: Ctx, ident: str, group: str, raw: str):
    hit = im.severity_of(group, raw)
    return hit if hit else (ctx.unmapped(ident, "嚴重度", raw), None)


def _updated(ctx: Ctx, ident: str, day: str | None) -> str | None:
    if day is None:
        ctx.note(f"issues.{ident}.updated_at", "TIME-UNPARSEABLE")
    return day


def _compose(ident: str, kind: str, hit: tuple, **f) -> dict:
    """議題物件（鍵序固定，C1.2；`links` 於 `finish` 回填）。"""
    status, result = hit[0], hit[1]
    return {"id": ident, "source": f["source"], "title": f["title"], "severity": f["sev"][0],
            "severity_rank": f["sev"][1], "status": status, "result": result,
            "updated_at": f["day"], "next_step": im.NEXT_STEPS[hit[2]].format(**f["facts"]),
            "origin": f["origin"], "links": [], "rankable": im.rankable(status),
            "action": im.action_of(kind, status)}


def _excerpt(disp: str, token: str) -> str:
    """延後列的處置附加文字：去前導分隔符與「再開症狀：」，截 40 個 code point。"""
    rest = _REOPEN_RE.sub("", disp[len(token):].lstrip(si_rows._LEAD_SEP)).strip()
    return rest[:EXCERPT_MAX] or im.EMPTY_EXCERPT


def obs_item(ctx: Ctx, row, rel: str, env: Env) -> None:
    """觀察帳本的一個合法列（九欄、ID 合 OBS-SI-NNN）成一個議題。"""
    ident, cells = row.ident, row.cells
    marks, token = si_rows.row_marks(row), si_rows.disp_token(cells[7])
    hit = _status(ctx, ident, "obs", token, cells[7], decision=cells[5] == "decision",
                  established=ident in env.confirmed or im.user_marked(marks))
    source = im.source_of(marks, cells[5]) or ctx.unmapped(ident, "來源", cells[5])
    sev = _severity(ctx, ident, "obs", cells[6])
    start = _time_day(cells[1])
    day = None if start is None else max(start, env.close_date.get(ident, ""))
    target = ID_RE.search(token or "")
    if target:
        ctx.link(ident, target.group(0))  # 處置指向的缺陷、被合併者、被轉交的提案：雙向
    for name in ("rel", "reopens"):  # 單向：本列 → 被指者（`rel` 取冒號後的 ID）
        pointed = im.mark_of(marks, name).rsplit(":", 1)[-1]
        if ID_RE.fullmatch(pointed):
            ctx.link(ident, pointed, both=False)
    facts = {"result": hit[1], "target": target.group(0) if target else token,
             "excerpt": _excerpt(cells[7], token) if hit[2] == "N16" else ""}
    origin = {"ledger": im.LEDGER_LABELS["obs"], "file": rel, "line": row.lineno}
    item = _compose(ident, "obs", hit, source=source, title=clean_title(cells[3]), sev=sev,
                    day=_updated(ctx, ident, day), facts=facts, origin=origin)
    ctx.add(item, int(ident.rsplit("-", 1)[1]), (list(COLUMNS), list(cells)))


def _sibling_facts(sib: dict | None) -> dict:
    return {"unlock": (sib or {}).get("unlock", "")[:EXCERPT_MAX],
            "review": (sib or {}).get("review") or "—"}


def def_item(ctx: Ctx, row, rel: str, sib: dict | None, raw: tuple[list, list]) -> None:
    """缺陷主檔的一個資料列成一個議題；`sib`＝姊妹軌的同號列（有則狀態覆蓋為延後）。"""
    ident = row.ident
    hit = _status(ctx, ident, "def", row.status, row.status_text, sibling=sib is not None)
    origin = {"ledger": im.LEDGER_LABELS["def"], "file": rel, "line": row.lineno}
    item = _compose(ident, "def", hit, source=im.source_of({}, "", is_def=True),
                    title=clean_title(row.evidence), sev=_severity(ctx, ident, "def", row.severity),
                    day=_updated(ctx, ident, day_of(row.date)),
                    facts={"result": hit[1], **_sibling_facts(sib)}, origin=origin)
    ctx.add(item, S + row.lineno, raw)


def orphan_item(ctx: Ctx, sib: dict, cursor: int) -> None:
    """姊妹軌的孤列（DEF-ID 在主檔找不到）：系統缺陷、延後、嚴重度量不到、不進 problems。"""
    ident = sib["id"]
    ctx.note(f"issues.{ident}.severity", "SEVERITY-UNAVAILABLE")
    hit = im.classify("def", None, sibling=True)
    origin = {"ledger": im.LEDGER_LABELS["def"], "file": sib["file"], "line": sib["line"]}
    item = _compose(ident, "def", hit, source=im.source_of({}, "", is_def=True),
                    title=im.ORPHAN_TITLE, sev=(None, None),
                    day=_updated(ctx, ident, day_of(sib["review"])),
                    facts={"result": None, **_sibling_facts(sib)}, origin=origin)
    ctx.add(item, cursor, (sib["labels"], sib["cells"]))


def _prop_source(ctx: Ctx, ident: str, sources: list, obs_ok: bool):
    """提案的（來源, 嚴重度）：取 `sources` 判定中順位最前者與最嚴重者（R-IC-16、R-IC-25）。
    來源項目含觀察號而觀察帳本讀不到時兩者皆 None，由整本帳的 ne 說明（R-IC-11）。"""
    names, sevs, lost = [], [], []
    for sid in sources:
        item = ctx.items.get(sid)
        if DEF_RE.fullmatch(sid):
            names.append(im.source_of({}, "", is_def=True))
        elif not obs_ok:
            return None, (None, None)
        elif item is None or im.is_unmapped(item["source"]):
            lost.append(sid)
            continue
        else:
            names.append(item["source"])
        if item is not None and item["severity_rank"] is not None:
            sevs.append((item["severity"], item["severity_rank"]))
    source = min(names, key=im.SOURCES.index) if names else ctx.unmapped(
        ident, "來源", "、".join(lost))
    if not sevs:
        ctx.note(f"issues.{ident}.severity", "SEVERITY-UNAVAILABLE")
    return source, min(sevs, key=lambda s: s[1]) if sevs else (None, None)


def _channel(ctx: Ctx, ident: str, route: str) -> str:
    suffix = route.split(":", 1)[-1]
    return im.route_label(suffix) or ctx.unmapped(ident, "通道", suffix)


def prop_item(ctx: Ctx, p, x: dict) -> None:
    """折疊後的一個提案成一個議題。`x` 為 `issues.py` 以接縫取得的事實：symptom（卡面〈一、症狀〉，
    量不到為 None）、card_text、window（首窗生效結果）、decided（已決定回滾次數）、progress
    （可呼叫：提案號 → (n_opp, w_opp) 或 None）、last_t（最後事件的時間）、cooldown、obs_ok。"""
    ident, num = p.id, int(p.id.rsplit("-", 1)[1])
    if num >= S:
        ctx.problem(ident, "ROW-ARITY", "編號或行號過大，游標無法編碼")
        return
    pend = p.pending_rollbacks
    hit = _status(ctx, ident, "prop", p.state, p.state, route=p.route, window=x["window"],
                  decided=x["decided"], pending=pend, consumed=max(x["decided"] - pend, 0))
    source, sev = _prop_source(ctx, ident, p.sources, x["obs_ok"])
    facts = {"result": hit[1], "rev": p.rev, "cool": im.COOL_TEXT.get(x["cooldown"], "")}
    code = hit[2]
    if code in ("N03", "N18h"):
        facts["channel"] = _channel(ctx, ident, p.route)
    if code == "N15":
        got = x["progress"](ident)
        if got is None:
            ctx.note(f"issues.{ident}.next_step", "MEASURE-UNAVAILABLE")
            code = "N15u"
        else:
            facts["n_opp"], facts["w_opp"] = got
    if x["symptom"] is None:
        ctx.note(f"issues.{ident}.title", "CARD-UNAVAILABLE")
    title = im.CARD_TITLE.format(id=ident) if x["symptom"] is None else clean_title(x["symptom"])
    for src in p.sources:
        ctx.link(ident, src)
    origin = {"ledger": im.LEDGER_LABELS["event"], "file": EVENTS_REL, "seq": p.created_seq}
    item = _compose(ident, "prop", (*hit[:2], code), source=source, title=title, sev=sev,
                    day=_updated(ctx, ident, day_of(x["last_t"])), facts=facts, origin=origin)
    values = [x["card_text"], p.state, p.route, p.cls, p.action, str(p.rev), p.digest,
              "、".join(p.sources)]
    pairs = [(k, v) for k, v in zip(im.PROP_RAW_LABELS, values) if v is not None]
    ctx.add(item, 2 * S + num, ([k for k, _ in pairs], [v for _, v in pairs]))


def confirmed_obs(atts) -> frozenset:
    """已確認歸因（`attr.confirm` 已落定）所指的觀察號：root 的 `obs`、link 的 `from`（路徑 A）。"""
    out: set = set()
    for a in atts:
        if a.settled is not None and a.settled[0] == "attr.confirm":
            out |= set(a.ev.get("obs") or ()) if a.type == "root" else {a.ev.get("from")}
    return frozenset(out)


def close_dates(events: list) -> dict:
    """觀察號 → 該列最晚的 `obs.close` 日期（事件 `t` 的日期部分）。"""
    out: dict = {}
    for e in events:
        if e["kind"] == "obs.close":
            out[e["obs"]] = max(out.get(e["obs"], ""), e["t"][:10])
    return out


def link_attrs(ctx: Ctx, atts) -> None:
    """`attr` link 的 `from` → `reopens`：單向（只有起點含目標）。"""
    for a in atts:
        if a.type == "link" and isinstance(a.ev.get("from"), str):
            ctx.link(a.ev["from"], str(a.ev.get("reopens")), both=False)


def finish(ctx: Ctx) -> None:
    """回填每個議題的 `links`（去重、依 ID 排序）。"""
    for ident, item in ctx.items.items():
        item["links"] = sorted(ctx.out.get(ident, ()))


def _mentions(e: dict, ident: str) -> bool:
    obs = e.get("obs")
    return (ident in (e.get("prop"), e.get("from"), e.get("reopens"), obs)
            or (isinstance(obs, list) and ident in obs)
            or (e["kind"] == "prop" and (ident == e.get("id") or ident in e.get("sources", ())))
            or any(isinstance(x, list) and x[1:] == [ident] for x in e.get("items") or ()))


def _action(ctx: Ctx, ident: str, e: dict) -> str:
    label = im.event_label(e["kind"])
    if label is None:
        return ctx.unmapped(ident, "時間線動作", e["kind"])
    if e["kind"] != "dec":
        return label
    verb = im.dkind_label(e.get("dkind"))
    return im.DEC_PREFIX + (verb or ctx.unmapped(ident, "決定動詞", str(e.get("dkind"))))


def timeline(ctx: Ctx, events: list, ident: str, run: str | None) -> list[dict]:
    """單筆的時間線（R-IC-30）：引用鍵見 PRD §5.1；依 seq 升冪；研究類事件不掛任何議題。"""
    attrs = {e["id"] for e in events if e["kind"] == "attr" and _mentions(e, ident)}
    hits = [e for e in events if not e["kind"].startswith("research.") and (
        _mentions(e, ident) or e.get("att") in attrs
        or (run is not None and e["kind"] in ("run.open", "run.close") and e.get("run") == run))]
    return [{"seq": e["seq"], "t": e["t"], "by": e["by"], "action": _action(ctx, ident, e)}
            for e in sorted(hits, key=lambda e: e["seq"])]


def detail(ctx: Ctx, ident: str, events: list, run: str | None) -> dict:
    """單筆議題：清單項目加 `raw`（帳本原列、標籤為表頭）與 `timeline`（置於 `action` 之後）。"""
    labels, values = ctx.raw[ident]
    return {**ctx.items[ident],
            "raw": [{"label": k, "value": v} for k, v in zip(labels, values)],
            "timeline": timeline(ctx, events, ident, run)}
