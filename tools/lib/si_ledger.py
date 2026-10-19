"""SelfImproving 觀察帳本解析與結構判準（TCS-SelfImproving-P0 R9／R10 的 tz 宣告）。

只讀、純標準庫：本檔不開檔、不碰 git，輸入是帳本全文字串。逐列欄位判準住
`si_rows.py`，歷史比對住 `si_history.py`。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

COLUMNS = ("ID", "時間", "情境", "症狀", "證據座標", "分類", "嚴重度", "處置", "標記")
ID_RE = re.compile(r"^OBS-SI-\d{3,}$")
_DECL_RE = re.compile(r"^<!--\s*si-ledger:\s*(.*?)\s*-->\s*$")
_TZ_RE = re.compile(r"(?:^|[\s;,])tz=([+-](?:0\d|1[0-4]):[0-5]\d)(?=$|[\s;,])")
_HEADER_RE = re.compile(r"^\|\s*ID\s*\|")
_OBS_ROW_RE = re.compile(r"^\|\s*OBS-SI-")
_SEP_CELL_RE = re.compile(r"^:?-{3,}:?$")
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")


@dataclass
class Finding:
    subject: str
    code: str
    level: str = "fail"
    detail: str = ""


@dataclass
class Row:
    lineno: int
    raw: str
    cells: list[str] | None
    ident: str
    kind: int  # 1＝ID 欄以 OBS-SI- 起頭；2＝表內其餘資料列（ID 視為不合法）

    @property
    def subject(self) -> str:
        return self.ident if self.kind == 1 else f"L{self.lineno}"

    @property
    def nine(self) -> bool:
        return self.cells is not None and len(self.cells) == len(COLUMNS)


@dataclass
class Ledger:
    rows: list[Row] = field(default_factory=list)
    tz: str | None = None
    header_found: bool = False
    header_ok: bool = False
    tz_malformed: bool = False


def split_cells(line: str) -> list[str] | None:
    """以未跳脫的 `|` 切欄；行不以 `|` 起頭並結尾回 None。"""
    s = line.strip()
    if len(s) < 2 or not s.startswith("|") or not s.endswith("|"):
        return None
    return [c.replace("\\|", "|").strip() for c in _CELL_SPLIT_RE.split(s[1:-1])]


def _is_sep(cells: list[str]) -> bool:
    return bool(cells) and all(_SEP_CELL_RE.match(c) for c in cells)


def split_lines(text: str) -> list[str]:
    if text.startswith("﻿"):
        text = text[1:]
    lines = text.split("\n")
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]


def _make_row(lineno: int, line: str, kind: int) -> Row:
    cells = split_cells(line)
    if cells is not None:
        ident = cells[0]
    else:
        parts = line.strip().lstrip("|").split("|", 1)
        ident = parts[0].strip()
    return Row(lineno, line, cells, ident, kind)


def parse_ledger(text: str) -> Ledger:
    lines = split_lines(text)
    led = Ledger()
    decls = [_DECL_RE.match(ln) for ln in lines]
    decls = [m for m in decls if m]
    if len(decls) == 1:
        tzm = _TZ_RE.search(decls[0].group(1))
        if tzm:
            led.tz = tzm.group(1)
        else:
            led.tz_malformed = True
    elif len(decls) > 1:
        led.tz_malformed = True
    header_idx = next((i for i, ln in enumerate(lines) if _HEADER_RE.match(ln)), None)
    picked: dict[int, int] = {}
    for i, ln in enumerate(lines):
        if _OBS_ROW_RE.match(ln):
            picked[i] = 1
    if header_idx is not None:
        led.header_found = True
        hc = split_cells(lines[header_idx])
        led.header_ok = hc is not None and tuple(hc) == COLUMNS
        for j in range(header_idx + 1, len(lines)):
            ln = lines[j]
            if not ln.strip() or not ln.lstrip().startswith("|"):
                break
            cells = split_cells(ln)
            if cells is not None and _is_sep(cells):
                continue
            picked.setdefault(j, 2)
    for i in sorted(picked):
        led.rows.append(_make_row(i + 1, lines[i], picked[i]))
    return led


def structure_findings(led: Ledger) -> list[Finding]:
    out: list[Finding] = []
    if not led.header_ok:
        out.append(Finding("-", "HEADER-COLS", "fail", "表頭缺少或欄名序列不是九欄定稿"))
    seen: set[str] = set()
    top = -1
    for row in led.rows:
        if not row.nine:
            out.append(Finding(row.subject, "ROW-ARITY", "fail", "欄數不是 9 或行未以 | 結尾"))
            continue
        if row.kind != 1 or not ID_RE.match(row.ident):
            out.append(Finding(row.subject, "ROW-ID-FORMAT", "fail", "ID 欄不合 OBS-SI-NNN"))
            continue
        if row.ident in seen:
            out.append(Finding(row.subject, "ROW-ID-DUP", "fail", "ID 重複"))
            continue
        seen.add(row.ident)
        num = int(row.ident.rsplit("-", 1)[1])
        if num <= top:
            out.append(Finding(row.subject, "ROW-ID-ORDER", "fail", "ID 數值未嚴格遞增"))
            continue
        top = num
    return out


def max_valid_id(led: Ledger) -> int:
    best = 0
    for row in led.rows:
        if row.kind == 1 and ID_RE.match(row.ident):
            best = max(best, int(row.ident.rsplit("-", 1)[1]))
    return best
