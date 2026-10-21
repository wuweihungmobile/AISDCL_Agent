"""SelfImproving 拒絕後的同型冷卻（TCS-SelfImproving-P2 R82；FR-SI-13）。

純函式：`prop-new`／`prop-revise` 的前置檢查呼叫它（`props.evaluate`）。
同型＝`cls` 相同 ∧ `target` 路徑集合相同 ∧（根因鍵集合有交集 ∨ 證據座標集合有交集）。
冷卻中的同型提案被擋，除非 (a) `dec(unblock)`，或 (b-2) 否決後新立、同根因（已確認）而證據不相交的
OBS 列；「未說明」的否決採最嚴冷卻（只能解除）。再提案（含已解除者）須附非空的 `reject_response`。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import fold as si_fold
from .rows import TIME_RE, coord_set

Code = tuple[str, str]
STRICT_CLASS = "未說明"


def row_time(cell: str) -> datetime | None:
    """OBS 列 `時間` 欄的起點（aware）；無 offset 者視為本機時區。"""
    m = TIME_RE.match(cell)
    if not m:
        return None
    y, mo, d, h, mi, s, off = m.groups()
    try:
        naive = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
    except ValueError:
        return None
    if not off:
        return naive.astimezone()
    sign = -1 if off.strip().startswith("-") else 1
    hh, mm = off.strip()[1:].split(":")
    return naive.replace(tzinfo=timezone(sign * timedelta(hours=int(hh), minutes=int(mm))))


def _coords(c, sources: list[str]) -> set[str]:
    out: set[str] = set()
    for s in sources:
        row = c.obs_rows.get(s)
        text = row.cells[4] if row is not None and row.nine else (c.def_evidence or {}).get(s, "")
        out |= coord_set(text)
    return out


def _decided_at(events: list[dict], pid: str) -> datetime | None:
    for e in reversed(events):
        if (e.get("kind") == "dec" and e.get("prop") == pid
                and e.get("dkind") in ("reject", "decline-promote")):
            try:
                return datetime.fromisoformat(e["decided_at"])
            except (KeyError, ValueError):
                return None
    return None


def _confirmed(f: si_fold.Folded) -> dict[str, set[str]]:
    """OBS ID → 經 `attr.confirm` 確認的根因鍵集合。"""
    out: dict[str, set[str]] = {}
    for a in f.atts.values():
        cause = a.ev.get("root_cause")
        if a.type == "root" and a.settled and a.settled[0] == "attr.confirm" and cause:
            for obs in a.ev.get("obs") or []:
                out.setdefault(obs, set()).add(cause)
    return out


def new_evidence(c, p: si_fold.Prop) -> bool:
    """(b-2)：否決後新立的 OBS 列，其根因鍵經確認且等於原 PROP 的根因鍵之一、證據座標集合不相交。"""
    if p.reject_class == STRICT_CLASS:
        return False
    decided = _decided_at(c.events, p.id)
    roots = set(si_fold.prop_root_causes(c.folded, p.sources))
    old = _coords(c, p.sources)
    confirmed = _confirmed(c.folded)
    for oid, row in c.obs_rows.items():
        when = row_time(row.cells[1]) if row.nine else None
        if decided is None or when is None or when < decided:
            continue
        if confirmed.get(oid, set()) & roots and not (coord_set(row.cells[4]) & old):
            return True
    return False


def same_type_rejected(c, cls: str) -> list[si_fold.Prop]:
    f = c.folded
    mine_roots = set(si_fold.prop_root_causes(f, c.sources))
    mine_coords = _coords(c, c.sources)
    out = []
    for p in f.props.values():
        if (p.id == c.self_prop or p.state != "rejected" or p.cls != cls
                or set(p.target) != set(c.targets)):
            continue
        if mine_roots & set(si_fold.prop_root_causes(f, p.sources)) \
                or mine_coords & _coords(c, p.sources):
            out.append(p)
    return out


def codes(c, cls: str) -> list[Code]:
    """`COOLDOWN`（冷卻中且 (b-2) 不成立）與 `REJECT-RESPONSE-MISSING`（再提案缺逐項回應）。"""
    if c.obs_rows is None:
        return []
    same = same_type_rejected(c, cls)
    if not same:
        return []
    out: list[Code] = [("COOLDOWN", f"與冷卻中的 {p.id} 同型，且無解除或新證據（R82）")
                       for p in same if not p.unblocked and not new_evidence(c, p)]
    if not str(c.fields.get("reject_response", "")).strip():
        ids = "、".join(p.id for p in same)
        out.append(("REJECT-RESPONSE-MISSING", f"存在同型的被否決提案 {ids}，本文欄位表須有"
                                               "非空的 reject_response"))
    return out
