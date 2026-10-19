"""SelfImproving 協定參數對表、判準指紋與協定目錄副本判準（TCS-SelfImproving-P0 R7、R21～R24）。"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from lib.si_ledger import Finding, split_lines

PROTOCOL_REL = "docs/06_quality/SelfImproving_Protocol"
CHECK_RULES_REV = 1

# 鍵 → 型別規則：int1＝整數 ≥1；ratio＝數值 0<x≤1；sha＝字串或 null；strs＝非空字串陣列
PARAM_SPECS: dict[str, str] = {
    "row_max_bytes": "int1", "w_n": "int1", "w_min": "int1", "w_evt": "int1", "w_opp": "int1",
    "max_proposals_per_run": "int1", "max_revisions": "int1", "churn_max": "int1",
    "min_heldout": "int1", "max_touch_ratio": "ratio", "max_new_entries": "int1",
    "stop_after_bad": "int1", "cap_frac": "ratio", "max_archive_entries_per_card": "int1",
    "card_line_max": "int1", "event_max_bytes": "int1", "metrics_rev": "int1",
    "min_obs_rows": "int1", "ledger_warn_bytes": "int1", "ledger_fail_bytes": "int1",
    "migration_base_sha": "sha", "spec_body_globs": "strs", "non_evolvable_globs": "strs",
}
_LABEL_RE = re.compile(r"\((?:i|ii|iii|iv|v)\) $")
_BRACE_RE = re.compile(
    r"^(?P<dir>[^{}\s]+/)\{(?P<names>[^{}\s]+)\}(?P<ext>\.[A-Za-z0-9]+)$")
_METRIC_ROW_RE = re.compile(r"^\| \*\*(?:結果指標|資訊欄)\*\*[^|]* \| \*\*M([1-5]) ")
PRD_REL = "docs/01_requirements/SelfImproving_PRD.md"


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def param_findings(params: dict) -> list[Finding]:
    out: list[Finding] = []
    for key, kind in PARAM_SPECS.items():
        if key not in params:
            out.append(Finding(key, "PARAM-MISSING", "fail", "必備鍵缺少"))
            continue
        v = params[key]
        code = None
        if kind == "int1":
            if isinstance(v, bool) or not isinstance(v, int):
                code = "PARAM-TYPE"
            elif v < 1:
                code = "PARAM-RANGE"
        elif kind == "ratio":
            if not _is_num(v):
                code = "PARAM-TYPE"
            elif not 0 < v <= 1:
                code = "PARAM-RANGE"
        elif kind == "sha":
            if v is not None and not isinstance(v, str):
                code = "PARAM-TYPE"
        elif not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            code = "PARAM-TYPE"
        elif not v:
            code = "PARAM-RANGE"
        if code:
            out.append(Finding(key, code, "fail", f"{key} 的型別或範圍不符（{kind}）"))
    return out


def valid_keys(params: dict) -> set[str]:
    bad = {f.subject for f in param_findings(params)}
    return set(PARAM_SPECS) - bad


def ne_findings(detail: str) -> list[Finding]:
    return [Finding("-", "SOURCE-UNAVAILABLE", "info", detail)]


def required_globs(repo: Path) -> set[str] | None:
    """PRD 的 `**實體 glob**` 行加根 CLAUDE.md `守衛面＝` 行的大括號展開；讀不到回 None。"""
    try:
        prd = (repo / PRD_REL).read_text(encoding="utf-8")
        claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    pl = next((ln for ln in split_lines(prd) if "**實體 glob**" in ln), None)
    cl = next((ln for ln in split_lines(claude) if "守衛面＝" in ln), None)
    if pl is None or cl is None:
        return None
    need: set[str] = set()
    for m in re.finditer(r"`([^`]+)`", pl):
        pre = pl[:m.start()]
        if pre.endswith(("、", "；")) or _LABEL_RE.search(pre):
            need.add(m.group(1))
    for m in re.finditer(r"`([^`]+)`", cl):
        b = _BRACE_RE.match(m.group(1))
        if b:
            need.update(f"{b['dir']}{n}{b['ext']}" for n in b["names"].split(","))
    return need


def glob_findings(params: dict, valid: set[str], repo: Path) -> list[Finding]:
    need = required_globs(repo)
    if need is None or "non_evolvable_globs" not in valid:
        return ne_findings("PRD 或根 CLAUDE.md 讀不到／找不到標記行，或 non_evolvable_globs 無效")
    got = params["non_evolvable_globs"]
    missing, extra = sorted(need - set(got)), sorted(set(got) - need)
    dups = sorted({g for g in got if got.count(g) > 1})
    if not (missing or extra or dups):
        return []
    return [Finding("non_evolvable_globs", "GLOBS-SET-MISMATCH", "fail",
                    f"缺少 {missing} 多出 {extra} 重複 {dups}")]


def coupling_findings(params: dict, valid: set[str]) -> list[Finding]:
    if not {"w_opp", "w_min", "ledger_warn_bytes", "ledger_fail_bytes"} <= valid:
        return ne_findings("參與耦合的鍵無效")
    out = []
    if params["w_opp"] < params["w_min"]:
        out.append(Finding("w_opp", "COUPLING-W-OPP-LT-W-MIN", "fail", "w_opp 不得小於 w_min"))
    if params["ledger_warn_bytes"] >= params["ledger_fail_bytes"]:
        out.append(Finding("ledger_warn_bytes", "COUPLING-WARN-GE-FAIL", "fail",
                           "ledger_warn_bytes 須小於 ledger_fail_bytes"))
    return out


def fingerprint(repo: Path, params: dict) -> tuple[str, dict]:
    pdir = repo / PROTOCOL_REL
    found = pdir.rglob("*") if pdir.is_dir() else []
    files = [p for p in found if p.is_file() and p.name[0] != "."]
    man = sorted((p.relative_to(pdir).as_posix(),
                  hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest())
                 for p in files)
    manifest = hashlib.sha256(json.dumps(man, ensure_ascii=False).encode("utf-8")).hexdigest()
    rev = params.get("metrics_rev")
    rev = rev if isinstance(rev, int) and not isinstance(rev, bool) else None
    parts = {"manifest": manifest, "metrics_rev": rev, "check_rules_rev": CHECK_RULES_REV}
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest(), parts


def params_file_problems(raw: bytes) -> list[str]:
    """R24：UTF-8（無 BOM）、LF、結尾換行、頂層鍵依位元組序遞增。"""
    out = []
    if raw.startswith(b"\xef\xbb\xbf"):
        out.append("有 BOM")
    if b"\r" in raw:
        out.append("含 CR")
    if not raw.endswith(b"\n"):
        out.append("結尾無換行")
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        return out + ["不是 UTF-8 JSON"]
    if not isinstance(obj, dict):
        return out + ["頂層不是物件"]
    keys = list(obj)
    if keys != sorted(keys, key=lambda k: k.encode("utf-8")):
        out.append("頂層鍵未依位元組序遞增")
    return out


def metrics_problems(prd_text: str, metrics_text: str) -> list[str]:
    """R24：PRD §1.3 的 M1～M5 指標列與 M1 判定細則區段須逐字出現在 metrics.md，
    且指標列順序為 M1 至 M5。"""
    prd, met = split_lines(prd_text), split_lines(metrics_text)
    rows = [(m.group(1), ln) for ln in prd if (m := _METRIC_ROW_RE.match(ln))]
    if [r[0] for r in rows] != ["1", "2", "3", "4", "5"]:
        return ["PRD 指標列不是 M1～M5 各恰一列"]
    start = next((i for i, ln in enumerate(prd) if ln.strip().startswith("**M1 判定細則**")), None)
    if start is None:
        return ["PRD 找不到 **M1 判定細則** 標題行"]
    end = next((i for i in range(start + 1, len(prd)) if prd[i].startswith("#### ")), len(prd))
    detail = [ln for ln in prd[start:end] if ln.strip()]
    out, last = [], -1
    for _, ln in rows:
        idx = met.index(ln) if ln in met else -1
        if idx < 0:
            out.append(f"指標列缺少：{ln[:40]}")
        elif idx < last:
            out.append(f"指標列順序錯：{ln[:40]}")
        last = max(last, idx)
    out += [f"判定細則缺少：{ln[:40]}" for ln in detail if ln not in met]
    return out
