"""PRD 草稿的確定性預檢（模板 PRD-SPEC-ENGINEERED §0.2 的 P0-1～P0-9）與審查前置否決（P1）。

兩類檢查、兩個後果（不要混）：
  · **草擬預檢 P0**（`precheck_draft`）：結構性，在草稿進入審查**之前**執行；不過＝草稿不進審查、
    FSM 不轉態、不耗審查預算，只列出缺漏。
  · **前置否決 P1**（`precheck_p1`：`SLV-001`／`SLV-002`／`SLV-003`／`AMBIGUITY`）：SCG-0 的條件，
    在 `SCG_VALIDATION` 內、四位審查者開跑之前由程式執行；不過＝本輪不計分、直接 `gate FAIL`
    （計入預算）。

誠實劃界：框架的 SLV 規則檔與模糊度計分器屬於另一個子專案（Bridge 不 import 它們，ADR-XPLAT-010），
所以這裡是**本地鏡像**——SLV 三條對 PRD 內容實作同一份 `required_qualifiers` 條文（只認下列幾種形態，
非標準寫法可能空轉，由 QA 角的 `slv_manual_check` 人讀補位），模糊度計分器逐維度鏡像
`ambiguity_scorer` v1.0（六個維度、字典與權重相同；門檻 0.4）。`tests/test_research_gates.py` 在
`SDD_ROOT` 存在時以真計分器對拍。本檔只讀字串、不讀檔案、不碰網路與資料庫。
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .schemas import Violation

# ── 引用預檢代碼表（PRD §5.1.3 與模板 §0.2 P0-7 同名；增減須兩處與本常數同步，測試逐值對拍）──
CITES_MISSING = "CITES_MISSING"
CITES_V1 = "CITES_V1"
CITES_UNANCHORED = "CITES_UNANCHORED"
CITES_CANDIDATE = "CITES_CANDIDATE"
CITES_CODES: tuple[str, ...] = (CITES_MISSING, CITES_V1, CITES_UNANCHORED, CITES_CANDIDATE)

AMBIGUITY_THRESHOLD = 0.4
ANCHOR_COUNT = 6
_ANCHOR_RE = re.compile(r"<!--\s*r2p:section=(\d+)\s*-->")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_CITE_RE = re.compile(r"\[(E-\d{3,4})\]")
_CHAPTER_NO_RE = re.compile(r"(?<![\d.])(\d{1,2})\.\s")
_REQUIRED_CHAPTERS = (1, 2, 3, 4, 5, 6, 7, 8, 10)
_ID_CLASSES: dict[str, re.Pattern[str]] = {
    "EPIC": re.compile(r"^EPIC-\d{3}$"), "F": re.compile(r"^F-\d{3}$"),
    "US": re.compile(r"^US-\d{3}$"), "AC": re.compile(r"^AC-\d{3}-\d+$"),
    "NFR": re.compile(r"^NFR-\d{3}$"), "INV": re.compile(r"^INV-\d{3}$")}
_ID_CANDIDATE_RE = re.compile(r"(?<![\w-])(EPIC|F|US|AC|NFR|INV)-[0-9][0-9A-Za-z-]*(?![\w-])")
_R2P_RE = re.compile(r"(?<![\w-])[A-Z]+-R2P(?:-[A-Z0-9]+)*(?![\w-])")
_DEF_RE = re.compile(r"^(?:#{2,6}\s*|[-*]\s+(?:\*\*)?)(EPIC|F|US|AC|NFR|INV)-(\d[\d-]*)")


@dataclass(frozen=True)
class PrecheckCheck:
    """前置否決的一項：`id`∈{SLV-001, SLV-002, SLV-003, AMBIGUITY}。"""

    id: str
    passed: bool
    detail: str = ""

    def to_card(self) -> dict[str, Any]:
        return {"id": self.id, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class CiteFinding:
    """一筆引用違規：`code` 取自 `CITES_CODES`，`evidence_no` 是被引用的 `E-NNN`。"""

    code: str
    evidence_no: str
    line: int


# ══ 文件結構工具 ═════════════════════════════════════════════════════════════════════════════
def _lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _headings(lines: Sequence[str]) -> list[tuple[int, int, str]]:
    """`(行索引, 層級, 標題文字)`；略過 fenced code block 內的行。"""
    out, fenced = [], False
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        match = None if fenced else _HEADING_RE.match(line)
        if match:
            out.append((index, len(match.group(1)), match.group(2)))
    return out


def _section_end(headings: Sequence[tuple[int, int, str]], position: int, total: int) -> int:
    """標題 `position` 的章節（含子節）結束行索引（下一個同級或更高級標題之前）。"""
    level = headings[position][1]
    for nxt in headings[position + 1:]:
        if nxt[1] <= level:
            return nxt[0]
    return total


def _has_content(lines: Sequence[str]) -> bool:
    """至少一行非空白、非註解、非標題、非分隔線的內容。"""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("<!--", "#")) or set(stripped) <= {"-", "*", "_"}:
            continue
        return True
    return False


def _anchor_sections(lines: Sequence[str]) -> dict[int, tuple[int, int] | None]:
    """錨點編號 → 其標題章節的 `(起, 迄)` 行索引；標題缺（錨點後第一個非空行不是標題）回 None。"""
    heads = _headings(lines)
    out: dict[int, tuple[int, int] | None] = {}
    for index, line in enumerate(lines):
        match = _ANCHOR_RE.search(line)
        if not match:
            continue
        number = int(match.group(1))
        nxt = next((j for j in range(index + 1, len(lines)) if lines[j].strip()), None)
        position = next((p for p, h in enumerate(heads) if h[0] == nxt), None)
        out.setdefault(number, None if position is None else (
            heads[position][0], _section_end(heads, position, len(lines))))
    return out


def anchor_section_text(text: str, number: int) -> str | None:
    """第 `number` 個錨點所指章節的文字（含標題行）；錨點缺或標題缺回 None。"""
    lines = _lines(text)
    span = _anchor_sections(lines).get(number)
    return None if span is None else "\n".join(lines[span[0]:span[1]])


# ══ 草擬預檢 P0 ═════════════════════════════════════════════════════════════════════════════
def precheck_draft(text: str, *, evidence_rows: Mapping[str, Mapping[str, Any]] | None = None
                   ) -> list[Violation]:
    """P0-1～P0-9。`evidence_rows`（`E-NNN` → `{f7, strength, unanchored}`，最新矩陣版本）給了才判
    P0-7 的 `CITES_*`；研究依據表的子句一律判。"""
    out: list[Violation] = []
    lines = _lines(text)
    out += _p0_anchors(lines)
    out += _p0_required_chapters(lines)
    if "{{" in text or "}}" in text:
        hit = next(i for i, line in enumerate(lines, 1) if "{{" in line or "}}" in line)
        out.append(Violation("P0-4", f"L{hit}", "全文不得殘留範本佔位 {{…}}"))
    out += _p0_ids(lines)
    out += _p0_traceability(lines)
    out += check_citations(text, evidence_rows)
    out += _p0_architecture(lines)
    return out


def _p0_anchors(lines: Sequence[str]) -> list[Violation]:
    out: list[Violation] = []
    found: dict[int, list[int]] = {}
    for index, line in enumerate(lines, 1):
        match = _ANCHOR_RE.search(line)
        if match:
            found.setdefault(int(match.group(1)), []).append(index)
    for number in range(1, ANCHOR_COUNT + 1):
        where = found.get(number, [])
        if len(where) != 1:
            out.append(Violation("P0-1", f"r2p:section={number}",
                                 f"錨點恰須出現一次（現有 {len(where)} 次，行 {where}）"))
    heads = _headings(lines)
    for number, span in sorted(_anchor_sections(lines).items()):
        if span is None:
            out.append(Violation("P0-2", f"r2p:section={number}", "錨點之後的第一個非空行不是標題"))
        elif not _has_content(lines[span[0] + 1:span[1]]):
            title = next((h[2] for h in heads if h[0] == span[0]), "")
            out.append(Violation("P0-2", f"r2p:section={number}", f"錨點下章節「{title}」沒有內容"))
    return out


def _p0_required_chapters(lines: Sequence[str]) -> list[Violation]:
    heads = [h for h in _headings(lines) if h[1] == 2]
    chapters: dict[int, int] = {}
    meta = None
    for position, (_, _, title) in enumerate(heads):
        match = _CHAPTER_NO_RE.search(title)
        if match:
            chapters.setdefault(int(match.group(1)), position)
        if "文檔元數據" in title or "元數據" in title:
            meta = position
    out: list[Violation] = []

    def empty(position: int | None, label: str) -> None:
        if position is None:
            out.append(Violation("P0-3", label, f"缺必讀章：{label}"))
            return
        end = heads[position + 1][0] if position + 1 < len(heads) else len(lines)
        if not _has_content(lines[heads[position][0] + 1:end]):
            out.append(Violation("P0-3", label, f"必讀章為空：{label}"))

    empty(meta, "文檔元數據表")
    for number in _REQUIRED_CHAPTERS:
        empty(chapters.get(number), f"第 {number} 章")
    return out


def _p0_ids(lines: Sequence[str]) -> list[Violation]:
    out: list[Violation] = []
    defined: dict[str, int] = {}
    fenced = False
    for index, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for token in sorted({m.group(0) for m in _R2P_RE.finditer(line)}):
            out.append(Violation("P0-5", f"L{index}",
                                 f"產出 PRD 的 ID 一律 Rule 7 數字制，不得含 R2P：{token}"))
        for match in _ID_CANDIDATE_RE.finditer(line):
            if not _ID_CLASSES[match.group(1)].fullmatch(match.group(0)):
                out.append(Violation("P0-5", f"L{index}", f"ID 位數或格式不合：{match.group(0)}"))
        definition = _DEF_RE.match(line.strip())
        if definition:
            ident = f"{definition.group(1)}-{definition.group(2).rstrip('-')}"
            if ident in defined:
                out.append(Violation(
                    "P0-5", f"L{index}", f"同類 ID 重複定義：{ident}（首見於 L{defined[ident]}）"))
            else:
                defined[ident] = index
    return out


def _blocks(lines: Sequence[str], cls: str) -> list[tuple[str, int, int]]:
    """`(ID, 起, 迄)`：以 2～6 級標題定義的 `cls` 區塊（到下一個同級或更高級標題之前）。"""
    heads = _headings(lines)
    out = []
    for position, (index, _level, title) in enumerate(heads):
        match = re.match(rf"({cls}-\d{{3}}(?:-\d+)?)\b", title)
        if match:
            out.append((match.group(1), index, _section_end(heads, position, len(lines))))
    return out


def _field_ids(block: Sequence[str], label: str, id_re: str) -> list[str] | None:
    """區塊內 `**對應 X**:` 欄位的 ID 清單；欄位不存在回 None。"""
    pattern = re.compile(rf"對應\s*{label}\s*\**\s*[:：](.*)")
    for line in block:
        match = pattern.search(line)
        if match:
            return re.findall(id_re, match.group(1))
    return None


def _boundary_ok(block: Sequence[str]) -> bool:
    for index, line in enumerate(block):
        if "邊界條件" not in line:
            continue
        tail = re.split(r"[:：]", line, maxsplit=1)
        if len(tail) == 2 and tail[1].strip():
            return True
        for follow in block[index + 1:]:
            if re.match(r"^\s*[-*]\s+\*\*", follow) or follow.startswith("#"):
                break
            if follow.strip():
                return True
        return False
    return False


def _p0_traceability(lines: Sequence[str]) -> list[Violation]:
    out: list[Violation] = []
    feats, stories, acs = _blocks(lines, "F"), _blocks(lines, "US"), _blocks(lines, "AC")
    us_ids, ac_ids = {b[0] for b in stories}, {b[0] for b in acs}
    referenced_us: set[str] = set()
    referenced_ac: set[str] = set()
    for ident, start, end in feats:
        block = lines[start:end]
        if not _boundary_ok(block):
            out.append(Violation("P0-6", f"L{start + 1}", f"{ident} 缺非空的「邊界條件」小節"))
        refs = _field_ids(block, "US", r"US-\d{3}")
        if not refs:
            out.append(Violation("P0-6", f"L{start + 1}",
                                 f"{ident} 缺 **對應 US**: 行（至少一個 US）"))
        else:
            referenced_us |= set(refs)
            out += [Violation("P0-6", f"L{start + 1}", f"{ident} 引用不存在的 {r}")
                    for r in refs if r not in us_ids]
    for ident, start, end in stories:
        refs = _field_ids(lines[start:end], "AC", r"AC-\d{3}-\d+")
        if not refs:
            out.append(Violation("P0-6", f"L{start + 1}",
                                 f"{ident} 缺 **對應 AC**: 行（至少一個 AC）"))
        else:
            referenced_ac |= set(refs)
            out += [Violation("P0-6", f"L{start + 1}", f"{ident} 引用不存在的 {r}")
                    for r in refs if r not in ac_ids]
    for ident, start, end in acs:
        body = "\n".join(lines[start + 1:end])
        missing = [k for k in ("Given", "When", "Then") if not re.search(rf"\b{k}\b", body)]
        if missing:
            out.append(Violation("P0-6", f"L{start + 1}",
                                 f"{ident} 的 Gherkin 缺 {'、'.join(missing)}"))
    out += [Violation("P0-6", f"L{s + 1}", f"{i} 沒有被任何 US 引用")
            for i, s, _ in acs if i not in referenced_ac]
    out += [Violation("P0-6", f"L{s + 1}", f"{i} 沒有被任何 Feature 引用")
            for i, s, _ in stories if i not in referenced_us]
    return out


# ── P0-7：引用檢查 ────────────────────────────────────────────────────────────────────────────
def cite_findings(text: str, rows: Mapping[str, Mapping[str, Any]]) -> list[CiteFinding]:
    """全文每個 `[E-NNN]` 引用逐一判定（以引用編號為單位去重）。`CITES_MISSING` 時不再判其餘三項；
    V1 列以 `CITES_V1` 涵蓋（不重複回報 `CITES_CANDIDATE`）。"""
    out: list[CiteFinding] = []
    seen: set[str] = set()
    for index, line in enumerate(_lines(text), 1):
        for number in _CITE_RE.findall(line):
            if number in seen:
                continue
            seen.add(number)
            row = rows.get(number)
            if row is None:
                out.append(CiteFinding(CITES_MISSING, number, index))
                continue
            v1 = row.get("f7") == "V1"
            if v1:
                out.append(CiteFinding(CITES_V1, number, index))
            if row.get("unanchored"):
                out.append(CiteFinding(CITES_UNANCHORED, number, index))
            if row.get("strength") == "CANDIDATE" and not v1:
                out.append(CiteFinding(CITES_CANDIDATE, number, index))
    return out


def _research_table_violations(lines: Sequence[str]) -> list[Violation]:
    """1.2 的「研究依據」表至少一列，且每列至少一個 `[E-NNN]`（缺漏逐項列出，不另設代碼）。"""
    heads = _headings(lines)
    start = next((h[0] for h in heads if h[1] >= 3 and "研究依據" in h[2]
                  and not h[2].lstrip().startswith("F-")), None)
    if start is None:
        return [Violation("P0-7", "1.2", "缺「研究依據」表")]
    rows: list[tuple[int, str]] = []
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("|"):
            rows.append((index + 1, stripped))
        elif rows and stripped:
            break
        elif stripped.startswith("#"):
            break
    data = rows[2:]                                   # 去掉表頭與分隔列
    if not data:
        return [Violation("P0-7", f"L{start + 1}", "「研究依據」表沒有任何資料列")]
    return [Violation("P0-7", f"L{n}", "「研究依據」表的這一列沒有 [E-NNN] 引用")
            for n, row in data if not _CITE_RE.search(row)]


def check_citations(text: str, rows: Mapping[str, Mapping[str, Any]] | None = None
                    ) -> list[Violation]:
    out = _research_table_violations(_lines(text))
    if rows is not None:
        out += [Violation("P0-7", f"L{f.line}", f"{f.code} {f.evidence_no}")
                for f in cite_findings(text, rows)]
    return out


# ── P0-8、P0-9：第 9 章 ───────────────────────────────────────────────────────────────────────
def _p0_architecture(lines: Sequence[str]) -> list[Violation]:
    heads = _headings(lines)
    subs: dict[int, tuple[int, int]] = {}
    for position, (index, level, title) in enumerate(heads):
        match = re.match(r"9\.(\d)\b", title)
        if level == 3 and match:
            subs[int(match.group(1))] = (index, _section_end(heads, position, len(lines)))
    out: list[Violation] = []
    for number, label in ((2, "資料模型"), (3, "API 與 Mermaid"), (4, "外部相依與授權"),
                          (5, "架構決策")):
        span = subs.get(number)
        if span is None:
            out.append(Violation("P0-8", f"9.{number}", f"缺第 9.{number} 節（{label}）"))
        elif not _has_content(lines[span[0] + 1:span[1]]):
            out.append(Violation("P0-8", f"9.{number}", f"第 9.{number} 節（{label}）為空"))
    if 4 in subs:
        out += _license_cells(lines[subs[4][0] + 1:subs[4][1]], subs[4][0] + 1)
    if 3 in subs:
        body = "\n".join(lines[subs[3][0] + 1:subs[3][1]])
        if "```mermaid" not in body and "不適用：" not in body:
            out.append(Violation("P0-9", "9.3", "9.3 須含 mermaid 區塊，或寫「不適用：<理由>」"))
    return out


def _license_cells(block: Sequence[str], offset: int) -> list[Violation]:
    rows = [(offset + i + 1, [c.strip() for c in line.strip().strip("|").split("|")])
            for i, line in enumerate(block) if line.strip().startswith("|")]
    if len(rows) < 3:
        return []
    header = rows[0][1]
    column = next((i for i, cell in enumerate(header) if "授權條款" in cell), None)
    if column is None:
        return [Violation("P0-8", f"L{rows[0][0]}", "外部相依表缺「授權條款」欄")]
    return [Violation("P0-8", f"L{n}", "外部相依表這一列的授權條款為空")
            for n, cells in rows[2:] if column >= len(cells) or not cells[column]]


# ══ AC 機械計數 ═════════════════════════════════════════════════════════════════════════════
def count_acs(text: str) -> int:
    """PRD 5.2 節 `#### AC-` 標題的機械計數（QA 角 `slv_manual_check.ac_total` 必須等於它）。"""
    section = anchor_section_text(text, 4)
    body = text if section is None else section
    return sum(1 for line in _lines(body) if re.match(r"^#{2,4}\s*AC-[\w-]+", line))


# ══ 前置否決 P1（SCG-0 的條件）═══════════════════════════════════════════════════════════════
_NUM = r"(-?\d+(?:\.\d+)?)"
_TIME_KEYS = r"(?:回應時間|響應時間|延遲|response[ _]time|latency|P9[0-9])"
_RULES_NUMERIC: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("response_time", re.compile(rf"{_TIME_KEYS}[^\n]{{0,40}}?{_NUM}\s*(?:ms|毫秒|秒|s)\b", re.I),
     "response_time_ms 必須 > 0"),
    ("throughput", re.compile(rf"(?:吞吐|throughput|rps|qps)[^\n]{{0,40}}?{_NUM}\s*"
                              r"(?:rps|qps|tps|req|requests?|ops|次|頁|筆|個|件|條|文件|/s"
                              r"|每秒|每分鐘|每小時|per)", re.I),
     "throughput_rps 必須 > 0"),
    ("storage", re.compile(rf"(?:儲存|容量|storage)[^\n]{{0,40}}?{_NUM}\s*(?:gb|tb|mb)", re.I),
     "storage_gb 必須 > 0"),
    ("concurrent", re.compile(rf"(?:並發|併發|concurrent)[^\n]{{0,40}}?{_NUM}\s*(?:users?|個|位|人"
                              r"|connections?|連線|sessions?|使用者)", re.I),
     "max_concurrent_users 必須 > 0"),
)
_AVAIL_RE = re.compile(rf"(?:可用性|availability|SLA)[^\n]{{0,40}}?{_NUM}\s*%", re.I)
_ERROR_RE = re.compile(rf"(?:錯誤率|error[ _]rate)[^\n]{{0,40}}?{_NUM}\s*%", re.I)


def _slv001(text: str) -> PrecheckCheck:
    section = anchor_section_text(text, 6)
    body = section if section is not None else text
    problems: list[str] = []
    for line in _lines(body):
        if line.lstrip().startswith((">", "<!--")):      # 引言與註解是填寫指引，不是需求
            continue
        for _key, pattern, rule in _RULES_NUMERIC:
            for match in pattern.finditer(line):
                if float(match.group(1)) <= 0:
                    problems.append(f"{rule}：{match.group(0).strip()}")
        for match in _AVAIL_RE.finditer(line):
            if float(match.group(1)) > 100:
                problems.append(f"availability_percent 必須 ≤ 100：{match.group(0).strip()}")
        for match in _ERROR_RE.finditer(line):
            if not 0 <= float(match.group(1)) <= 100:
                problems.append(f"error_rate_percent 必須在 0～100：{match.group(0).strip()}")
    return PrecheckCheck("SLV-001", not problems, "；".join(problems[:5]))


_VAGUE_TERMS = ("很快", "快速", "適當", "合理", "盡快", "順暢", "流暢", "足夠", "盡量", "盡可能")
_OBSERVABLE = re.compile(r"\d|HTTP|狀態|回傳|回應|顯示|欄位|錯誤|拒絕|出現|寫入|建立|刪除"
                         r"|變為|等於|包含|拋出|清單|不變|更新|儲存|通知|產生", re.I)


def _ac_blocks(text: str) -> list[tuple[str, str]]:
    section = anchor_section_text(text, 4)
    lines = _lines(section if section is not None else text)
    heads = _headings(lines)
    out = []
    for position, (index, _level, title) in enumerate(heads):
        match = re.match(r"(AC-[\w-]+)", title)
        if match:
            out.append((match.group(1),
                        "\n".join(lines[index + 1:_section_end(heads, position, len(lines))])))
    return out


def _slv002(text: str) -> PrecheckCheck:
    problems: list[str] = []
    for ident, body in _ac_blocks(text):
        if not re.search(r"\bGiven\b", body):
            problems.append(f"{ident} 缺 Given（前置條件）")
        then = re.search(r"\bThen\b(.*)", body, re.S)
        if then is None:
            problems.append(f"{ident} 缺 Then（期望結果）")
        elif any(term in then.group(1) for term in _VAGUE_TERMS) and not _OBSERVABLE.search(
                re.sub("|".join(_VAGUE_TERMS), "", then.group(1))):
            problems.append(f"{ident} 的 Then 只用模糊詞，沒有可觀察或可量測的結果")
    return PrecheckCheck("SLV-002", not problems, "；".join(problems[:5]))


_INV_LINE_RE = re.compile(r"(INV-\d{3})\s*[:：]?\s*(.+)")
_UPPER_RE = re.compile(r"^(.+?)\s*(?:≤|<=|<|不得大於|不超過|至多)\s*(-?\d+(?:\.\d+)?)")
_LOWER_RE = re.compile(r"^(.+?)\s*(?:≥|>=|>|不得小於|不低於|至少)\s*(-?\d+(?:\.\d+)?)")
_NONEMPTY_RE = re.compile(r"^(.+?)\s*(?:不得為空|不可為空|不能為空|必填)")
_EMPTYOK_RE = re.compile(r"^(.+?)\s*(?:可為空|可以為空|允許為空|可空)")
_ZEROOK_RE = re.compile(r"^(.+?)\s*(?:可為\s*0|可以為\s*0|允許為\s*0)")
_GT_ZERO_RE = re.compile(r"^(.+?)\s*>\s*0(?![\d.])")
_ORDER_RE = re.compile(r"^(.+?)\s*必須在\s*(.+?)\s*之前")


def _subject(raw: str) -> str:
    return re.sub(r"[\s，,。；;:：「」\"'（）()]", "", raw)


def _slv003(text: str) -> PrecheckCheck:
    invs: dict[str, str] = {}
    for line in _lines(text):
        for match in _INV_LINE_RE.finditer(line):
            invs.setdefault(match.group(1), match.group(2).strip().lstrip("-*· "))
    problems: list[str] = []
    ids = sorted(invs)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            kind = _contradiction(invs[ids[a]], invs[ids[b]])
            if kind:
                problems.append(f"{ids[a]} 與 {ids[b]} 互相矛盾（{kind}）")
    return PrecheckCheck("SLV-003", not problems, "；".join(problems[:5]))


def _same(first: re.Match[str] | None, second: re.Match[str] | None) -> bool:
    return bool(first and second and _subject(first.group(1)) == _subject(second.group(1)))


def _contradiction(first: str, second: str) -> str | None:
    """兩條 INV 的矛盾型：互斥條件（不得為空 vs 可為空）、範圍矛盾（X>0 vs X 可為 0；X≥10 vs X≤5）、
    時序矛盾（A 必須在 B 之前 vs B 必須在 A 之前）。其餘形態本地鏡像看不見，由 QA 角人讀補位。"""
    for one, two in ((first, second), (second, first)):
        if _same(_NONEMPTY_RE.match(one), _EMPTYOK_RE.match(two)):
            return "互斥條件"
        if _same(_GT_ZERO_RE.match(one), _ZEROOK_RE.match(two)):
            return "範圍矛盾"
        low, up = _LOWER_RE.match(one), _UPPER_RE.match(two)
        if _same(low, up) and float(low.group(2)) > float(up.group(2)):  # type: ignore[union-attr]
            return "範圍矛盾"
        o1, o2 = _ORDER_RE.match(one), _ORDER_RE.match(two)
        if o1 and o2 and _subject(o1.group(1)) == _subject(o2.group(2)) and _subject(
                o1.group(2)) == _subject(o2.group(1)):
            return "時序矛盾"
    return None


# ── 模糊度計分器（`ambiguity_scorer` v1.0 的逐維度鏡像）──────────────────────────────────────
SCORER_VERSION = "v1.0"
_QUANTIFIERS = ("快速", "緩慢", "適當", "適度", "適合", "盡可能", "盡量", "足夠", "少量", "大量",
                "大部分", "一些", "若干", "fast", "slow", "appropriate", "reasonable", "sufficient",
                "adequate", "many", "few", "some", "several", "mostly", "partial")
_PASSIVE = (
    re.compile(r"應(被|要被|將被|可被)[一-鿿\w]+"),
    re.compile(r"被[一-鿿\w]+(?=$|，|。|；)"),
    re.compile(r"\b(is|are|shall be|will be|may be|can be)\s+\w+ed\b", re.I))
_NFR_WORDS = ("效能", "延遲", "吞吐", "容量", "可用性", "響應時間", "回應時間", "performance",
              "latency", "throughput", "capacity", "availability", "response time", "rto", "rpo")
_NUMBER_UNIT = re.compile(r"\d+(?:\.\d+)?\s*(?:ms|s|sec|min|h|hr|req|qps|rps|mb|gb|tb|%"
                          r"|百分|秒|分鐘|小時)", re.I)
_CONDITIONS = (re.compile(r"(若|如果|當|除非|否則|在.*情況下|在.*條件下)"),
               re.compile(r"\b(if|when|unless|otherwise|in case)\b", re.I))
_UI_API = ("ui", "畫面", "頁面", "按鈕", "endpoint", "api", "request", "response", "form", "表單",
           "對話框", "modal")
_ANCHOR = re.compile(r"<!--\s*anchor:[\w-]+:[\w-]+\s*-->")
_AMBIGUOUS_REFS = ("如同", "類似", "相應", "相關", "對應", "匹配", "similar to", "corresponding",
                   "related", "matching", "alike")


def ambiguity_score(text: str) -> float:
    """單一 AC 文字的模糊度（0～1，兩位小數）：六維度加總封頂 1.0；與框架計分器同字典同權重。"""
    if not text or not text.strip():
        return 0.0
    lowered = text.lower()
    hits = sum(1 for t in _QUANTIFIERS if t.lower() in lowered)
    d1 = 0.0 if hits == 0 else 0.10 if hits == 1 else 0.25
    sentences = [s for s in re.split(r"[。；;.\n]", text) if s.strip()]
    passive = sum(1 for s in sentences if any(p.search(s) for p in _PASSIVE))
    d2 = min(0.20 * (passive / len(sentences)), 0.20) if sentences else 0.0
    d3 = 0.20 if any(k in lowered for k in _NFR_WORDS) and not _NUMBER_UNIT.search(text) else 0.0
    d4 = 0.0 if any(p.search(text) for p in _CONDITIONS) else 0.15
    d5 = 0.10 if any(k in lowered for k in _UI_API) and not _ANCHOR.search(text) else 0.0
    refs = sum(1 for t in _AMBIGUOUS_REFS if t.lower() in lowered)
    d6 = 0.0 if refs == 0 else 0.05 if refs == 1 else 0.10
    return round(min(d1 + d2 + d3 + d4 + d5 + d6, 1.0), 2)


def _ambiguity(text: str) -> PrecheckCheck:
    scores = [(ident, ambiguity_score(body), body) for ident, body in _ac_blocks(text)]
    blocked = [f"{i} 模糊度 {s:.2f} 不低於 {AMBIGUITY_THRESHOLD}" for i, s, body in scores
               if s >= AMBIGUITY_THRESHOLD and "AMBIGUITY-WAIVER" not in body]
    if blocked:
        return PrecheckCheck("AMBIGUITY", False, "；".join(blocked[:5]))
    top = max((s for _i, s, _b in scores), default=0.0)
    return PrecheckCheck("AMBIGUITY", True, f"最大 AC 模糊度 {top:.2f}，低於 {AMBIGUITY_THRESHOLD}")


def precheck_p1(text: str) -> list[PrecheckCheck]:
    """前置否決四項（固定順序 SLV-001、SLV-002、SLV-003、AMBIGUITY）；PRD 沒有 INV 時 SLV-003 視
    為通過
    （空集合）。"""
    return [_slv001(text), _slv002(text), _slv003(text), _ambiguity(text)]


def precheck_passed(checks: Sequence[PrecheckCheck]) -> bool:
    return all(c.passed for c in checks)
