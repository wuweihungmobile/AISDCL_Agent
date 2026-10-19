"""SelfImproving 的缺陷帳本（DEF）解析：狀態分類與表格列讀取（TCS-SelfImproving-P1 R45、R59）。

只讀、純標準庫。`classify_status`／`load_ledger_status` 與 `tools/check_defect_log_crossref.py`
的 `_classify`／`_load_ledger_status()` 逐筆差分一致（ADR-SI-05；AT-131-2-E-2 鎖死）：本檔不
import 該檔（它的 import 面不屬 `ro` 類登記），分類樣式是同一份規則的並列實作、由差分測試對拍。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ID_RE = re.compile(r"DEF-\d+-\d+")
_ROW_RE = re.compile(r"^\|\s*DEF-\d+-\d+\s*\|")
_HEADER_RE = re.compile(r"^\|\s*ID\s*\|")
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
_ID_HEADER, _STATUS_HEADER = "ID", "狀態"
_STATUS_KEYWORDS: dict[str, re.Pattern[str]] = {
    "wontfix": re.compile(r"wontfix"),
    "closed-by-decision": re.compile(r"closed-by-decision|no[_ ]action[_ ]needed"),
    "routed": re.compile(r"(?<![A-Za-z0-9])routed(?![A-Za-z0-9])"),
    "fixed": re.compile(r"(?<![A-Za-z0-9])fixed(?![A-Za-z0-9])"),
    "open": re.compile(
        r"(?<![A-Za-z0-9])open(?![A-Za-z0-9])|workaround"
        r"|(?<![A-Za-z0-9])partial(?![A-Za-z0-9])"
    ),
}
CLOSED_CLASSES = frozenset({"fixed", "wontfix", "closed-by-decision", "routed"})


@dataclass(frozen=True)
class DefRow:
    ident: str
    date: str
    severity: str
    status: str | None
    evidence: str


def classify_status(text: str) -> str | None:
    """text 中最早出現的狀態關鍵字類別（open／fixed／wontfix／closed-by-decision／routed）。"""
    best_pos: int | None = None
    best_label: str | None = None
    for label, pat in _STATUS_KEYWORDS.items():
        m = pat.search(text)
        if m and (best_pos is None or m.start() < best_pos):
            best_pos, best_label = m.start(), label
    return best_label


def _row_cells(line: str) -> list[str]:
    return [c.strip() for c in _CELL_SPLIT_RE.split(line)]


def _header_cells(text: str) -> list[str] | None:
    for line in text.splitlines():
        if _HEADER_RE.match(line):
            cells = _row_cells(line)
            if _ID_HEADER in cells and _STATUS_HEADER in cells:
                return cells
    return None


def columns(path: Path) -> list[str] | None:
    """缺陷帳本第一個合格表頭的欄名；檔不存在、讀不到或無表頭回 None。"""
    try:
        return _header_cells(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError):
        return None


def load_rows(path: Path) -> list[DefRow]:
    """帳本檔的資料列（同號後列不覆寫、原序全收）；表頭定位欄位，欄數不符的列狀態記 None。
    檔不存在、讀不到或無表頭回空串列。"""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return []
    head = _header_cells(text)
    if head is None:
        return []
    idx = {name: head.index(name) for name in head if name}
    out = []
    for line in text.splitlines():
        if not _ROW_RE.match(line):
            continue
        cells = _row_cells(line)
        i_id = idx[_ID_HEADER]
        if i_id >= len(cells) or not _ID_RE.fullmatch(cells[i_id]):
            continue
        ok = len(cells) == len(head)

        def cell(name: str, cells=cells, ok=ok) -> str:
            return cells[idx[name]] if ok and name in idx else ""

        status = classify_status(cell(_STATUS_HEADER)) if ok else None
        out.append(DefRow(cells[i_id], cell("發現日期"), cell("嚴重度"), status,
                          cell("現象與證據（file:line）")))
    return out


def load_ledger_status(path: Path) -> dict[str, str | None]:
    """{DEF 號: 分類}；同號後列覆寫前列、欄數與表頭不符的列記 None、無表頭回空 dict。"""
    return {r.ident: r.status for r in load_rows(path)}
