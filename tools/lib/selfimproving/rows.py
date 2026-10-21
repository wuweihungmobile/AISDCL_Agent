"""SelfImproving 觀察帳本逐列判準（TCS-SelfImproving-P0 R10～R16）。

輸入是 `ledger.parse_ledger` 的列；輸出是「項目 ID → Finding 清單」。
只判形態：座標指向的檔案是否真的存在、`fixed@` 的 sha 是否解析得到由別處判。
"""

from __future__ import annotations

import re
from datetime import datetime

from .ledger import COLUMNS, Finding, Ledger, Row

_OFF = r"[+-](?:0\d|1[0-4]):[0-5]\d"
_START = rf"(\d{{4}})-(\d{{2}})-(\d{{2}}) (\d{{2}}):(\d{{2}})(?::(\d{{2}}))?(?: ?({_OFF}))?"
_END = rf"(?:(?:\d{{4}}-)?\d{{2}}-\d{{2}} )?\d{{2}}:\d{{2}}(?::\d{{2}})?(?: ?{_OFF})?"
TIME_RE = re.compile(rf"^{_START}(?:[～~]{_END})?$", re.ASCII)

REQUIRED = {1: "時間", 2: "情境", 3: "症狀", 4: "證據座標", 5: "分類", 6: "嚴重度", 7: "處置"}
_PLACEHOLDERS = {"-", "—", "tbd", "n/a"}
CATEGORIES = {"process", "bug", "tooling", "doc", "decision"}
SEVERITIES = {"P1", "P2", "P3", "P4"}

DISP_TOKEN_RE = re.compile(
    r"^(open|deferred|retired|decided|fixed@\S+?|DEF-\S+?|merged@\S+?|proposed@\S+?)"
    r"(?=$|[：:（(；;，,\s])"
)
FIXED_SHA_RE = re.compile(r"^fixed@[0-9a-f]{7,40}$")
DEF_ID_RE = re.compile(r"^DEF-\d+-\d+$")
_MERGED_RE = re.compile(r"^merged@OBS-SI-\d{3,}$")
_PROPOSED_RE = re.compile(r"^proposed@PROP-SI-\d{3,}$")
_LEAD_SEP = "：:（(；;，, \t　"

_COORD_RES = [re.compile(p) for p in (
    r"(?<![\w.])(?:[A-Za-z0-9_.%\-]+[/\\])+[A-Za-z0-9_.%\-<>*{}\[\]]+\.[A-Za-z0-9]{1,8}"
    r"(?::\d+(?:[–-]\d+)?)?",
    r"(?<![\w./\\-])[A-Za-z0-9_.\-]+\.(?:md|py|json|jsonl|yaml|yml|ps1|sh|bash|toml|ts|tsx|js"
    r"|mjs|java|xml|txt|log|html|css|cfg|ini|lock|patch|csv|tla)(?![A-Za-z0-9])"
    r"(?::\d+(?:[–-]\d+)?)?",
    r"(?<![\w./\\-])(?:docs|tools|AutoClaude|AISDLC_SDD|AgentConsole|\.claude|\.github)/"
    r"[^\s、，；）)`]*",
    r"(?<![0-9A-Za-z-])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}(?![0-9A-Za-z-])",
    r"(?i:commit|sha)\s*[:=]?\s*[0-9a-f]{7,40}(?![0-9A-Za-z])",
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[^；;、\n]{0,40}?"
    r"(?i:line|seq)\s*[:=]?\s*\d+",
    r"(?<![A-Za-z0-9-])(?:(?:OBS|ATT|PROP|DEC|APP|MEA|RUN)-SI-\d{3,}|DEF-\d+-\d+)(?![0-9A-Za-z])",
    r"`(?:python3?|py|git|powershell|pwsh|bash|sh|pytest|ruff|lint-imports|node|npm|npx|docker"
    r"|gh|claude|uv)\b[^`]*`",
    r"§\s?\d|(?:SOP|PRD|TCS|FRD|SRD|BRIDGE|ADR-[A-Z]+-\d+)\b[ \t]*[§\w.\-]*\d",
)]

MARK_KEYS = {"面", "暴露", "來源", "外部衍生", "回報者", "根因", "rel", "reopens", "orig", "span",
             "src", "carrier", "audit_ref"}
_SRC_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_FACES = {"守衛", "產品", "文件", "流程"}
_EXPOSURES = {"a", "b", "c", "無"}
FACES = _FACES
_SOURCES = {"人", "代理", "工具", "逐字稿", "帳本"}
ORIG_AT_RE = re.compile(r"^@[^\s#]+#OBS-SI-\d+$")


def now_cell() -> str:
    """現在本機時間 `YYYY-MM-DD HH:MM ±HH:MM`（帶 offset；絕不輸出 naive 時間戳）。"""
    z = datetime.now().astimezone()
    off = z.strftime("%z")
    return f"{z.strftime('%Y-%m-%d %H:%M')} {off[:3]}:{off[3:]}"


def draft_row(num: int, context: str, symptom: str, evidence: str, who: str, *,
              category: str = "bug", severity: str = "P3", disposition: str = "open") -> str:
    """OBS 草稿列（九欄；預設分類 bug、嚴重度 P3、處置 open；供主控入帳，CLI 不自寫帳本）。
    `scan` 的計數資訊列改 `process`／`P4`／`decided：僅計數`（R103；P1 的拒收草稿列不變）。"""
    cells = [f"OBS-SI-{num:03d}", now_cell(), context, symptom, evidence, category, severity,
             disposition, f"面=流程;來源=工具;回報者={who}"]
    return "| " + " | ".join(cells) + " |"


def has_coord(text: str) -> bool:
    return any(r.search(text) for r in _COORD_RES)


def path_set(cell: str) -> set[str]:
    """證據座標格中 `path`、`file`、`dir` 三形態命中的片段（去結尾行號、`\\` 換 `/`、casefold）。"""
    out = set()
    cell = _COORD_RES[7].sub(" ", cell)  # 反引號包住的指令是第八種座標形態、不是路徑
    for rx in _COORD_RES[:3]:
        for m in rx.finditer(cell):
            out.add(re.sub(r":\d+(?:[–-]\d+)?$", "", m.group(0)).replace("\\", "/").casefold())
    return out


def path_fragments(cell: str) -> list[str]:
    """證據座標格 `path`、`file`、`dir` 三形態的路徑片段原文（保留大小寫、去結尾行號、`\\` 換 `/`；
    不 casefold；R99 (c) 的歸桶輸入），依出現順序、去重。"""
    out: list[str] = []
    cell = _COORD_RES[7].sub(" ", cell)
    for rx in _COORD_RES[:3]:
        for m in rx.finditer(cell):
            frag = re.sub(r":\d+(?:[–-]\d+)?$", "", m.group(0)).replace("\\", "/")
            if frag not in out:
                out.append(frag)
    return out


def coord_set(cell: str) -> set[str]:
    """證據座標格中九形態命中的全部片段（`\\` 換 `/`、casefold；R82 (c) 的證據座標集合）。"""
    return {m.group(0).replace("\\", "/").casefold() for rx in _COORD_RES
            for m in rx.finditer(cell)}


def disp_token(cell: str) -> str | None:
    m = DISP_TOKEN_RE.match(cell)
    return m.group(1) if m else None


def parse_marks(cell: str) -> tuple[dict[str, tuple[str, bool]], list[str]]:
    """回（鍵→(值, 是否引號字串)、語法問題說明清單）。值空的鍵不進字典。"""
    marks: dict[str, tuple[str, bool]] = {}
    problems: list[str] = []
    i, n = 0, len(cell)
    while i < n:
        j = i
        while j < n and cell[j] not in ";=":
            j += 1
        key = cell[i:j].strip()
        if j >= n or cell[j] == ";":
            if key:
                problems.append(f"片段缺少 =：{key}")
            i = j + 1
            continue
        k = j + 1
        while k < n and cell[k] in " \t":
            k += 1
        quoted = k < n and cell[k] == '"'
        flagged = False
        if quoted:
            buf, k = [], k + 1
            while k < n and cell[k] != '"':
                if cell[k] == "\\" and k + 1 < n:
                    k += 1
                buf.append(cell[k])
                k += 1
            if k >= n:
                problems.append(f"引號值未閉合：{key}")
                value, i, flagged = "", n, True
            else:
                value, k = "".join(buf), k + 1
                end = cell.find(";", k)
                end = n if end < 0 else end
                if cell[k:end].strip():
                    problems.append(f"結尾引號之後還有文字：{key}")
                    flagged = True
                i = end + 1
        else:
            end = cell.find(";", k)
            end = n if end < 0 else end
            value = cell[k:end].strip()
            if '"' in value:
                problems.append(f"裸值含引號：{key}")
                value, flagged = "", True
            i = end + 1
        if not value and not flagged:
            problems.append(f"值為空：{key}")
        if key in marks:
            problems.append(f"鍵重複：{key}")
        elif value:
            marks[key] = (value, quoted)
    return marks, problems


def _parse_time(cell: str):
    m = TIME_RE.match(cell)
    if not m:
        return None
    y, mo, d, h, mi, s, off = m.groups()
    try:
        datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
    except ValueError:
        return None
    return off or ""


def _empty(cell: str) -> bool:
    return not cell or cell.lower() in _PLACEHOLDERS


def row_marks(row: Row) -> dict[str, tuple[str, bool]]:
    return parse_marks(row.cells[8])[0] if row.nine else {}


def evaluate_rows(led: Ledger, row_max_bytes: int | None,
                  src_ids: set[str] | None = None) -> dict[str, list[Finding]]:
    """`src_ids`＝研究來源表的全部 id（含 retired）；None＝來源表不存在或無法解析。"""
    out: dict[str, list[Finding]] = {k: [] for k in (
        "ledger.time_tz", "row.required", "row.enums", "row.markers", "row.provenance",
        "row.coordinates", "row.bytes", "row.control_chars")}

    def add(item: str, row: Row, code: str, detail: str, level: str = "fail") -> None:
        out[item].append(Finding(row.subject, code, level, detail))

    if led.tz_malformed:
        out["ledger.time_tz"].append(
            Finding("-", "TZ-HEADER-MALFORMED", "fail", "檔頭 tz 宣告不合法或超過一個"))
    seen_refs: set[str] = set()
    for row in led.rows:
        text = row.raw
        if row_max_bytes is not None and len(text.encode("utf-8")) > row_max_bytes:
            add("row.bytes", row, "ROW-BYTES-OVER", f"列位元組超過 {row_max_bytes}")
        if any(ord(c) < 0x20 or ord(c) == 0x7F for c in text):
            add("row.control_chars", row, "CTRL-CHAR", "列內含控制字元")
        if not row.nine:
            continue
        cells = row.cells
        empties = {i for i in REQUIRED if _empty(cells[i])}
        for i in sorted(empties):
            add("row.required", row, "FIELD-EMPTY", f"欄「{REQUIRED[i]}」為空或佔位值")
        if 1 not in empties:
            off = _parse_time(cells[1])
            if off is None:
                add("ledger.time_tz", row, "TIME-FORMAT", "欄「時間」格式不合或日期不存在")
            elif not off and led.tz is None:
                add("ledger.time_tz", row, "TIME-NO-TZ", "欄「時間」無 offset 且檔頭無有效 tz")
        if 4 not in empties and not has_coord(cells[4]):
            add("row.coordinates", row, "COORD-NONE", "欄「證據座標」不合九種可定位形態")
        if 5 not in empties and cells[5] not in CATEGORIES:
            add("row.enums", row, "ENUM-CATEGORY", "欄「分類」不在枚舉")
        if 6 not in empties and cells[6] not in SEVERITIES:
            add("row.enums", row, "ENUM-SEVERITY", "欄「嚴重度」不在 P1～P4")
        if 7 not in empties:
            _disposition(row, cells[7], add)
        _marks(row, cells, empties, add, src_ids, seen_refs)
    return out


def _disposition(row: Row, disp: str, add) -> None:
    m = DISP_TOKEN_RE.match(disp)
    ok = m is not None
    if m:
        tok = m.group(1)
        if tok.startswith("fixed@"):
            ok = bool(FIXED_SHA_RE.match(tok))
        elif tok.startswith("DEF-"):
            ok = bool(DEF_ID_RE.match(tok))
        elif tok.startswith("merged@"):
            ok = bool(_MERGED_RE.match(tok))
        elif tok.startswith("proposed@"):
            ok = bool(_PROPOSED_RE.match(tok))
    if not ok:
        add("row.enums", row, "DISP-ENUM", "欄「處置」首詞或其參照文法不符")
    elif m.group(1) in ("deferred", "retired", "decided"):
        rest = disp[m.end(1):].lstrip(_LEAD_SEP)
        if not rest or (m.group(1) == "retired" and not has_coord(rest)):
            add("row.enums", row, "DISP-TEXT-MISSING", "欄「處置」缺附加文字或 retired 缺座標")
    if "之後再看" in disp:
        add("row.enums", row, "DISP-DEFER-LATER", "欄「處置」含「之後再看」")


def _src_checks(row: Row, marks: dict, src_ids: set[str] | None, add) -> None:
    """R44：`回報者=研究者` 須帶 外部衍生=是 與 src；任何 src 須屬來源表（含 retired）。"""
    if marks.get("回報者", ("", False))[0] == "研究者":
        if "外部衍生" not in marks:
            add("row.provenance", row, "RESEARCHER-NOT-EXTERNAL", "研究者的列須 外部衍生=是")
        if "src" not in marks:
            add("row.provenance", row, "RESEARCHER-NO-SRC", "研究者的列須帶 src")
    if "src" in marks and _SRC_RE.match(marks["src"][0]):
        if src_ids is None:
            add("row.markers", row, "SOURCE-UNAVAILABLE", "來源表不存在或無法解析", "info")
        elif marks["src"][0] not in src_ids:
            add("row.markers", row, "SRC-UNKNOWN", f"src {marks['src'][0]} 不在來源表")


def _console_marks(row: Row, marks: dict, add, seen_refs: set[str]) -> None:
    """R76：carrier／audit_ref 成對、audit_ref 全帳本唯一（只驗形態，不讀家目錄）。"""
    if ("carrier" in marks) != ("audit_ref" in marks):
        add("row.markers", row, "CONSOLE-MARK-PAIR", "欄「標記」carrier 與 audit_ref 須成對")
    ref = marks.get("audit_ref", ("", False))[0]
    if _UUID_RE.match(ref):
        if ref in seen_refs:
            add("row.markers", row, "CONSOLE-AUDIT-DUP", "欄「標記」audit_ref 與較早的列重複")
        seen_refs.add(ref)


def _marks(row: Row, cells: list[str], empties: set[int], add,
           src_ids: set[str] | None = None, seen_refs: set[str] | None = None) -> None:
    marks, problems = parse_marks(cells[8])
    for p in problems:
        add("row.markers", row, "MARK-SYNTAX", f"欄「標記」{p}")
    _console_marks(row, marks, add, seen_refs if seen_refs is not None else set())
    for key, (value, quoted) in marks.items():
        if key not in MARK_KEYS:
            add("row.markers", row, "MARK-UNKNOWN-KEY", f"欄「標記」未知鍵 {key}")
        elif key == "src" and not _SRC_RE.match(value):
            add("row.markers", row, "MARK-VALUE", "欄「標記」src 的值不合 id 形態")
        elif (key == "carrier" and value != "console") or (
                key == "audit_ref" and not _UUID_RE.match(value)):
            add("row.markers", row, "MARK-VALUE", f"欄「標記」{key} 的值不在值域")
        elif (key == "面" and value not in _FACES) or (key == "暴露" and value not in _EXPOSURES) \
                or (key == "外部衍生" and value != "是"):
            add("row.markers", row, "MARK-VALUE", f"欄「標記」{key} 的值不在值域")
        elif key == "orig" and not quoted and not ORIG_AT_RE.match(value):
            add("row.markers", row, "MARK-ORIG-FORMAT", "欄「標記」orig 形態不合")
    face = marks.get("面", ("", False))[0]
    if "面" not in marks:
        add("row.markers", row, "MARK-FACE-MISSING", "欄「標記」缺 面")
    elif face == "守衛":
        if "暴露" not in marks:
            add("row.markers", row, "GUARD-NO-EXPOSURE", "守衛面缺 暴露")
        elif marks["暴露"][0] == "無" and cells[6] in ("P1", "P2"):
            add("row.markers", row, "GUARD-P12-NO-EXPOSURE", "守衛面 P1／P2 的 暴露 不得為無")
    if "來源" not in marks:
        add("row.provenance", row, "SOURCE-MISSING", "欄「標記」缺 來源")
    elif marks["來源"][0] not in _SOURCES:
        add("row.provenance", row, "SOURCE-VALUE", "欄「標記」來源不在詞彙")
    if "回報者" not in marks:
        add("row.provenance", row, "REPORTER-MISSING", "欄「標記」缺 回報者")
    if not problems:
        _src_checks(row, marks, src_ids, add)


__all__ = ["COLUMNS", "evaluate_rows", "has_coord", "parse_marks", "disp_token", "row_marks"]
