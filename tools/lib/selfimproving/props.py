"""SelfImproving 提案前置檢查（純函式）與 digest（TCS-SelfImproving-P1 R49～R55）。

階段一（輸入類：patch 解析、本文形態）收到即回；階段二（政策與狀態類）全部收集後一併回報。
本檔不做 I/O：patch 位元組、本文、base 快照與帳本狀態皆由呼叫端（`writeverbs`）以參數或回呼供應，
測試因而能直接餵合成輸入。卡面高寬判準屬 `card.py`、寫入屬 `writeverbs.py`。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from fractions import Fraction

from . import churn, cooldown, retire
from . import fold as si_fold
from . import paths as si_paths
from .events import DEF_ID_RE, OBS_ID_RE
from .ledger import split_cells

HEADS = ("反例證據", "Before", "After", "影響面", "欄位")
REQUIRED = ("symptom", "risk", "rollback", "budget", "result_label", "scope")
M_FIELDS = ("result_label", "scope", "source_obs", "retire_when")
LABELS = ("失敗", "成功", "升級")
TRUST_RE = re.compile(r"^\s*trust_level:\s*proposed\s*$", re.M)
_ACTIVE_RE = re.compile(r"^\s*maturity:\s*active\b", re.M)
_MATURITY_RE = re.compile(r"^\s*maturity:", re.M)
_GROUP_RE = re.compile(r"\((i|ii|iii|iv|v)\) |`([^`]+)`")
_SPEC_PATCH_GLOB = "**/docs/01_requirements/SPEC-PATCH-*.md"
Code = tuple[str, str]


def sha256_of(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def body_sha256(body_text: str) -> str:
    return sha256_of(body_text.replace("\r\n", "\n").encode("utf-8"))


def parse_body(text: str) -> tuple[list[str], dict[str, str]]:
    """（缺的骨架標題, 欄位表鍵→值）；欄位表取標題含「欄位」之節的第一個 Markdown 表。"""
    lines = text.replace("\r\n", "\n").split("\n")
    heads = [(i, ln[3:].strip()) for i, ln in enumerate(lines) if ln.startswith("## ")]
    missing = [h for h in HEADS if not any(h in t for _, t in heads)]
    fields: dict[str, str] = {}
    start = next((i for i, t in heads if "欄位" in t), None)
    if start is None:
        return missing, fields
    end = next((i for i, _ in heads if i > start), len(lines))
    rows = [split_cells(ln) for ln in lines[start + 1:end] if ln.lstrip().startswith("|")]
    for cells in rows[2:]:
        if cells and len(cells) >= 2:
            fields.setdefault(cells[0].strip("` "), cells[1].strip())
    return missing, fields


def input_problems(patch: bytes, body_text: str, cls: str) -> tuple[list[Code], dict, list]:
    """階段一：回（問題碼, 欄位表, patch 區塊）。patch 與本文各自獨立判、一併回報。"""
    out: list[Code] = []
    blocks: list = []
    try:
        blocks = si_paths.parse_patch(patch)
    except si_paths.PatchError as exc:
        out.append((exc.code, exc.detail or "patch 無法解析"))
    missing, fields = parse_body(body_text)
    if missing:
        out.append(("BODY-SKELETON", "缺 ## 標題：" + "、".join(missing)))
        return out, fields, blocks
    need = [k for k in REQUIRED if not (cls == "M" and k in ("result_label", "scope"))
            and not fields.get(k, "").strip()]
    if need:
        out.append(("BODY-FIELD-MISSING", "欄位表缺或空：" + "、".join(need)))
    label = fields.get("result_label", "").strip()
    if label and label not in LABELS:
        out.append(("BODY-FIELD-VALUE", f"result_label 須為 {'、'.join(LABELS)}，收到 {label!r}"))
    return out + retire.field_codes(fields, cls), fields, blocks


def m_field_problems(fields: dict, sources: list[str]) -> list[Code]:
    bad = [k for k in M_FIELDS if not fields.get(k, "").strip()]
    obs = [t for t in re.split(r"[、,，]", fields.get("source_obs", "")) if t.strip()]
    if "source_obs" not in bad and not (obs and all(
            OBS_ID_RE.match(t.strip()) and t.strip() in sources for t in obs)):
        bad.append("source_obs")
    return [("M-FIELD-MISSING", "M 類四欄缺、空或來源對不上：" + "、".join(bad))] if bad else []


def glob_groups(prd_text: str) -> dict[str, str]:
    """PRD `**實體 glob**` 行的 glob → 群組標籤（i～v）；與 P0 `required_globs` 同一抽取規則。"""
    line = next((ln for ln in prd_text.replace("\r\n", "\n").split("\n")
                 if "**實體 glob**" in ln), "")
    out: dict[str, str] = {}
    cur = ""
    for m in _GROUP_RE.finditer(line):
        if m.group(1):
            cur = m.group(1)
        elif line[:m.start()].endswith(("、", "；")) or re.search(
                r"\((?:i|ii|iii|iv|v)\) $", line[:m.start()]):
            out[m.group(2)] = cur
    return out


def mark_cls(cls: str, hit_globs: list[str], groups: dict[str, str]) -> str:
    """命中的 glob 屬 (iii) ⇒ evaluator-change；屬 (iv) ⇒ loop-self（兩者取前者）；其餘保持。"""
    labels = {groups.get(g) for g in hit_globs}
    return "evaluator-change" if "iii" in labels else "loop-self" if "iv" in labels else cls


@dataclass
class Ctx:
    """`evaluate` 的輸入快照（呼叫端在寫入鎖內以最新事件帳本組出）。"""
    cls: str
    action: str
    targets: list[str]
    sources: list[str]
    run: str
    proposer: str
    reviewer: str | None
    handoff: str | None
    fields: dict
    blocks: list
    params: dict
    folded: si_fold.Folded
    repo_real: str
    latest_name: str | None
    groups: dict[str, str]
    base_lines: dict[str, int | None]
    base_text: object  # 回呼 (path) -> str | None：base 快照的檔內容（R-*.yaml 條件式用）
    resolve: object  # 回呼 (id) -> bool | None：None＝查無；True＝內部來源
    memory_dir_ok: bool = True
    self_prop: str | None = None
    events: list = field(default_factory=list)
    obs_rows: dict | None = None  # OBS ID → 列；None＝不判同型冷卻（P1 單元測試的合成輸入）
    def_evidence: dict | None = None  # DEF ID → 「現象與證據」欄文字


@dataclass
class Decision:
    codes: list[Code] = field(default_factory=list)
    route: str = "loop"
    cls: str = ""
    touched: list[str] = field(default_factory=list)
    preimage: dict | None = None


def _hits(c: Ctx, touched: list[str]) -> tuple[bool, list[str], list[Code]]:
    """（是否任一路徑命中不可進化面／合法根／規格本體或別名, 命中的 glob 清單, 政策碼）。"""
    hit, globs, codes = False, [], []
    spec_ok = (c.cls == "D" and c.action == "add" and len(touched) == 1
               and si_paths.glob_match(_SPEC_PATCH_GLOB, touched[0].replace("\\", "/")))
    for p in touched:
        if si_paths.alias_reason(p):
            hit = True
            continue
        norm = si_paths.normalize(p, c.repo_real)
        if norm is None or (c.cls == "M" and not norm.startswith("memory/")):
            hit = True
            continue
        for g in c.params["non_evolvable_globs"]:
            if g.casefold() == si_paths.RULE_GLOB.casefold():
                if si_paths.glob_match(g, norm) and _rule_hit(c, p):
                    hit = True
                    globs.append(g)
            elif si_paths.is_frozen_version_hit(g, norm, c.latest_name):
                hit = True
                globs.append(g)
        if not spec_ok and any(si_paths.glob_match(g, norm) for g in c.params["spec_body_globs"]):
            hit = True
    for b in c.blocks:
        for p in b.paths:
            if si_paths.glob_match(si_paths.RULE_GLOB, p) and c.cls == "R" and b.new_file \
                    and b.new == p and c.base_text(p) is None \
                    and not TRUST_RE.search("\n".join(b.added)):
                codes.append(("R-NOT-PROPOSED", f"新增規則檔 {p} 不含 trust_level: proposed"))
    return hit, globs, codes


def reverify_paths(c: Ctx, touched: list[str]) -> tuple[bool, list[str]]:
    """`promote` 的 `NON-EVOLVABLE-NOW`（TCS-P2 R91）：以當下參數與 LATEST、與 `prop-new` 同一函式
    重驗全部路徑；回（是否命中, 命中的 glob）。"""
    hit, globs, _ = _hits(c, touched)
    return hit, globs


def _rule_hit(c: Ctx, path: str) -> bool:
    """R-*.yaml 內容條件式：base 已存在者只在 `maturity: active` 或讀不出 maturity 時命中。"""
    text = c.base_text(path)
    if text is None:
        return False
    return bool(_ACTIVE_RE.search(text)) or not _MATURITY_RE.search(text)


def _state_codes(c: Ctx) -> list[Code]:
    f, out = c.folded, []
    run = f.runs.get(c.run)
    if run is None or run.closed_seq is not None:
        out.append(("RUN-NOT-OPEN", f"{c.run} 不是 open 運轉"))
    if not any(r == c.run for _, _, r, _ in f.research_events):
        out.append(("RESEARCH-MISSING", f"{c.run} 內沒有研究事件"))
    if f.suspended is not None:
        out.append(("SUSPENDED", f"連續壞窗（所在運轉 {f.suspended['run']}），須先 dec resume"))
    if c.self_prop is None:
        n = len({e["id"] for e in c.events if e.get("kind") == "prop" and e.get("rev") == 1
                 and e.get("run") == c.run})
        if n >= c.params["max_proposals_per_run"]:
            out.append(("BUDGET-PROPOSALS", f"{c.run} 已有 {n} 個新 PROP（上限 "
                                            f"{c.params['max_proposals_per_run']}）"))
    return out


def _dup_code(c: Ctx, cls: str) -> list[Code]:
    mine = si_fold.prop_root_causes(c.folded, c.sources)
    for p in c.folded.props.values():
        if p.id == c.self_prop or p.state not in si_fold.ACTIVE_STATES or p.cls != cls \
                or set(p.target) != set(c.targets):
            continue
        theirs = si_fold.prop_root_causes(c.folded, p.sources)
        if set(theirs) & set(mine) or (not theirs and not mine):
            return [("DUPLICATE-TYPE", f"與活躍的 {p.id} 同型（cls、target、根因鍵）")]
    return []


def _source_codes(c: Ctx) -> list[Code]:
    res = {s: c.resolve(s) for s in c.sources}
    out: list[Code] = []
    bad = [s for s, v in res.items() if v is None]
    if bad:
        out.append(("SOURCE-UNRESOLVED", "查無來源：" + "、".join(bad)))
    if not any(v for v in res.values()):
        out.append(("NO-INTERNAL-SOURCE", "解析成功的來源中沒有內部來源（外部衍生列不算）"))
    return out


def archive_moved(blocks: list) -> int | None:
    """M 類歸檔型（R54 (c)）：索引檔只刪行（可增指標行）、歸檔檔只增行、被刪行逐字搬入歸檔檔。"""
    idx = [b for b in blocks if (b.new or b.old or "").rsplit("/", 1)[-1] == "MEMORY.md"]
    arc = [b for b in blocks if (b.new or b.old or "").rsplit("/", 1)[-1].startswith(
        "archive-index-") and (b.new or b.old or "").endswith(".md")]
    if len(idx) != 1 or len(arc) != 1 or len(blocks) != 2 or arc[0].removed:
        return None
    pool: dict[str, int] = {}
    for line in arc[0].added:
        pool[line] = pool.get(line, 0) + 1
    for line in idx[0].removed:
        if pool.get(line, 0) < 1:
            return None
        pool[line] -= 1
    return len(idx[0].removed)


def _delta_codes(c: Ctx) -> list[Code]:
    out: list[Code] = []
    p = c.params
    moved = archive_moved(c.blocks) if c.cls == "M" else None
    entries = si_paths.new_entries(c.blocks, only=("MEMORY.md" if moved is not None else None))
    if moved is not None:
        if moved > p["max_archive_entries_per_card"]:
            lim = p["max_archive_entries_per_card"]
            out.append(("ARCHIVE-ENTRIES", f"搬移 {moved} 行 > {lim}"))
    else:
        ratio = si_paths.touch_ratio(c.blocks, c.base_lines)
        if ratio is not None and ratio > Fraction(str(p["max_touch_ratio"])):
            out.append(("TOUCH-RATIO", f"觸及比例 {float(ratio):.3f} > {p['max_touch_ratio']}"))
    if entries > p["max_new_entries"]:
        out.append(("NEW-ENTRIES", f"新增條目 {entries} > {p['max_new_entries']}"))
    return out


def preimage_of(blocks: list, touched: list[str]) -> dict[str, str]:
    removed: dict[str, list[str]] = {}
    for b in blocks:
        owner = b.old or b.new
        if owner and b.removed:
            removed.setdefault(owner, []).extend(b.removed)
    return {t: sha256_of(("".join(x + "\n" for x in removed.get(t, []))).encode("utf-8"))
            for t in touched}


def evaluate(c: Ctx) -> Decision:
    """階段二：政策與狀態類碼全部收集；導出 route、標記後 cls、touched 與 M 類 preimage。"""
    d = Decision(touched=sorted({p for b in c.blocks for p in b.paths}))
    hit, globs, codes = _hits(c, d.touched)
    d.cls = mark_cls(c.cls, globs, c.groups)
    d.codes += codes + _state_codes(c) + _dup_code(c, d.cls) + cooldown.codes(c, d.cls)
    d.codes += _source_codes(c) + retire.target_codes(c) + churn.codes(c)
    if c.reviewer is not None and c.reviewer == c.proposer:
        d.codes.append(("REVIEWER-IS-PROPOSER", "審查者不得等於提案者"))
    handoff = hit or d.cls not in ("M", "P", "R", "D")
    d.route = "handoff:" + (c.handoff or "") if handoff else "loop"
    if handoff and not c.handoff:
        d.codes.append(("HANDOFF-CHANNEL-MISSING", "導出為 handoff，須給 --handoff"))
    if not handoff and c.handoff:
        d.codes.append(("HANDOFF-CHANNEL-UNEXPECTED", "導出為 loop，不得給 --handoff"))
    if c.cls == "M":
        d.codes += m_field_problems(c.fields, c.sources)
        d.preimage = preimage_of(c.blocks, d.touched)
        if not c.memory_dir_ok:
            d.codes.append(("MEMORY-DIR-MISSING", "M 類須給 --memory-dir"))
    if c.memory_dir_ok or c.cls != "M":
        d.codes += _delta_codes(c)
    return d


def _canon(x) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_digest(*, pid: str, rev: int, cls: str, action: str, target: list[str],
                   touched: list[str], base: str, preimage: dict | None, patch_sha: str,
                   body_sha: str, fields: dict) -> str:
    """R55 (a)：15 個鍵的正規化 JSON 之 sha256；`touched` 保留原大小寫。"""
    core = {"id": pid, "rev": rev, "cls": cls, "action": action, "target": sorted(set(target)),
            "touched": sorted(set(touched)), "touched_count": len(set(touched)), "base": base,
            "preimage": preimage if cls == "M" and preimage is not None else base,
            "patch_sha256": patch_sha, "body_sha256": body_sha,
            "rollback": fields.get("rollback"), "retire_when": fields.get("retire_when"),
            "reopen_symptom": fields.get("reopen_symptom"), "budget": fields.get("budget")}
    return sha256_of(_canon(core))


__all__ = ["DEF_ID_RE", "OBS_ID_RE", "evaluate", "input_problems", "compute_digest",
           "reverify_paths"]
