"""SelfImproving 抖動防護與 capability-delta（TCS-P3 R128）。

能力類別 `ro`、純函式：`props.evaluate` 的階段二政策碼。群＝promoted PROP 中 `target` 路徑集合相同、
根因鍵有交集（或皆為空）者；循環數＝群內「晉升的 `add`，其之前已有晉升的 `retire` 且該 `retire` 之後
尚無其他 `add`」的筆數。只在 `prop-new`（rev 1）的 `add` 判；與冷卻、`DUPLICATE-TYPE` 互不取代。
"""

from __future__ import annotations

from pathlib import Path

from . import fold as si_fold
from . import mea as si_mea
from . import rows as si_rows

Code = tuple[str, str]


def _paths(targets) -> frozenset:
    return frozenset(t.replace("\\", "/").casefold() for t in targets)


def group_of(c) -> list:
    """新提案所屬群的 promoted PROP（依 `app.promote` 的 seq 排序）。"""
    mine = _paths(c.targets)
    keys = si_fold.confirmed_root_causes(c.folded, c.sources)
    out = []
    for p in c.folded.props.values():
        if p.promote_seq is None or _paths(p.target) != mine:
            continue
        theirs = si_fold.confirmed_root_causes(c.folded, p.sources)
        if theirs & keys or (not theirs and not keys):
            out.append(p)
    return sorted(out, key=lambda p: p.promote_seq)


def cycles(group: list) -> int:
    n, retired = 0, False
    for p in group:
        if p.action == "retire":
            retired = True
        elif p.action == "add" and retired:
            n, retired = n + 1, False
    return n


def _new_evidence(c, group: list) -> bool:
    """R128 (d)：來源中至少一列的 instant 晚於群最近一筆 `retire` 的晉升時刻、且其證據座標集合與
    群內全部既有 PROP 之 `sources` 的座標聯集不相交。"""
    rows = si_mea.universe(Path(c.repo_real))
    since = si_mea.parse_t(next(p.promote_t for p in reversed(group) if p.action == "retire"))
    seen = {x for p in group for s in p.sources if s in rows
            for x in si_rows.coord_set(rows[s].coords)}
    return since is not None and any(
        s in rows and rows[s].at > since and not si_rows.coord_set(rows[s].coords) & seen
        for s in c.sources)


def codes(c) -> list[Code]:
    if c.action != "add" or c.self_prop is not None:
        return []
    group = group_of(c)
    if not group or group[-1].action != "retire":
        return []
    out: list[Code] = []
    limit = c.params["churn_max"]
    if cycles(group) + 1 > limit:
        out.append(("CHURN-EXCEEDED", f"同群循環數 {cycles(group)} 加 1 超過 churn_max {limit}"))
    if not _new_evidence(c, group):
        out.append(("CAPABILITY-DELTA-MISSING", "再提已退役工件須附退役後的新證據"))
    return out
