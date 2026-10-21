"""SelfImproving `check`：21 項判定的組裝、判級、文字與 JSON 輸出、OBS 草稿列。

規格＝TCS-SelfImproving-P0 R3～R7。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import evcheck as si_evcheck
from . import history as si_history
from . import params as si_params
from . import refs as si_refs
from . import sources as si_sources
from .git import Git
from .ledger import Finding, max_valid_id, parse_ledger, structure_findings
from .rows import evaluate_rows

ITEM_IDS = (
    "ledger.structure", "ledger.time_tz", "row.required", "row.enums", "row.markers",
    "row.provenance", "row.coordinates", "row.bytes", "row.control_chars", "row.fixed_sha",
    "ref.def", "ref.obs", "ref.orig_notes", "ref.carrier_families", "history.migration",
    "history.row_mutated", "params.keys", "params.globs", "params.coupling", "ledger.volume",
    "ledger.vacuity",
) + si_evcheck.ITEM_IDS  # 其後追加 7 項（P1，R36）與 4 項（P2，R98）；前 21 項一字不變
LEDGER_REL = "docs/06_quality/SelfImproving_Observation_Ledger.md"
PARAMS_REL = f"{si_params.PROTOCOL_REL}/params.json"
_NONBLOCKING = frozenset({
    "CARRIER-NOT-ESTABLISHED", "SOURCES-HISTORY-NOT-ESTABLISHED", "CONSOLE-AUDIT-MISSING",
    "CONSOLE-KEY-MISSING", "TRANSCRIPT-UNAVAILABLE", "ORIGIN-MISSING", "ATTACHMENT-TIME-UNKNOWN",
})
_LIST_MAX = 5


class InputError(Exception):
    """檢查器無法執行（rc 3）。"""


@dataclass
class Item:
    id: str
    status: str
    blocking: bool
    detail: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Result:
    items: list[Item]
    rows: int
    overall: str
    rc: int
    fingerprint: str
    parts: dict
    draft: str | None


def read_text(path: Path, what: str) -> tuple[str, int]:
    if not path.is_file():
        raise InputError(f"{what} 不存在或不是檔案：{path}")
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError(f"{what} 讀不到或不是 UTF-8：{path}（{exc.__class__.__name__}）") from exc
    return text, len(raw)


def load_params(path: Path) -> dict:
    text, _ = read_text(path, "params")
    try:
        obj = json.loads(text.lstrip("﻿"))
    except ValueError as exc:
        raise InputError(f"params 不是 JSON：{path}") from exc
    if not isinstance(obj, dict):
        raise InputError(f"params 頂層不是 JSON 物件：{path}")
    return obj


def params_for(repo: Path, *keys: str) -> dict:
    """各動詞只讀它需要的 params 鍵；缺失、無效＝InputError（rc 3），不以預設值頂替。"""
    params = load_params(repo / PARAMS_REL)
    bad = [k for k in keys if k not in si_params.valid_keys(params)]
    if bad:
        raise InputError("params.json 必要鍵缺失或無效：" + "、".join(bad))
    return params


def _item(item_id: str, findings: list[Finding], detail: str = "") -> Item:
    if any(f.level == "fail" for f in findings):
        return Item(item_id, "FAIL", False, detail, findings)
    infos = [f for f in findings if f.level == "info"]
    if infos:
        return Item(item_id, "NE", any(f.code not in _NONBLOCKING for f in infos), detail,
                    findings)
    return Item(item_id, "PASS", False, detail, findings)


def _rel(repo: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return None


def build_items(repo: Path, ledger: Path, params: dict, text: str, size: int,
                git: Git) -> tuple[list[Item], int, int]:
    led = parse_ledger(text)
    valid = si_params.valid_keys(params)
    src_path = repo / si_sources.SOURCES_REL
    src_ids = si_sources.ids_or_none(src_path.read_bytes() if src_path.is_file() else None)
    ev = evaluate_rows(led, params["row_max_bytes"] if "row_max_bytes" in valid else None, src_ids)
    rel = _rel(repo, ledger)
    ev["row.markers"] += si_refs.reopen_findings(repo, rel, led, text, git)
    f: dict[str, list[Finding]] = {"ledger.structure": structure_findings(led), **ev}
    if "row_max_bytes" not in valid:
        f["row.bytes"] = si_params.ne_findings("row_max_bytes 無效，無法判定列位元組")
    f["row.fixed_sha"] = si_refs.fixed_sha_findings(led, git)
    f["ref.def"] = si_refs.def_findings(led, repo)
    events = si_refs.event_ledger(repo)
    f["ref.obs"], f["ref.carrier_families"] = si_refs.obs_findings(
        text, rel, repo, git, established=events is not None)
    if events is not None and git.available:
        f["ref.carrier_families"] += si_refs.family_findings(
            repo, events, [text, *si_refs.archive_texts(repo)])
    f["ref.orig_notes"] = si_refs.orig_findings(led, repo)
    mig = si_history.evaluate_migration(params.get("migration_base_sha"), led, git, rel)
    muts, mut_detail = si_history.evaluate_mutations(git, rel, text, mig)
    f["params.keys"] = si_params.param_findings(params)
    f["params.globs"] = si_params.glob_findings(params, valid, repo)
    f["params.coupling"] = si_params.coupling_findings(params, valid)
    f["ledger.volume"] = _volume(params, valid, size)
    f["ledger.vacuity"] = _vacuity(params, valid, len(led.rows))
    extra = si_evcheck.compute(repo, params, valid, git)
    items = []
    for item_id in ITEM_IDS:
        if item_id == "history.migration":
            items.append(_item(item_id, mig.findings, mig.detail))
        elif item_id == "history.row_mutated":
            items.append(_item(item_id, muts, mut_detail))
        elif item_id in extra:
            items.append(_item(item_id, *extra[item_id]))
        else:
            items.append(_item(item_id, f[item_id]))
    return items, len(led.rows), max_valid_id(led)


def _volume(params: dict, valid: set[str], size: int) -> list[Finding]:
    if not {"ledger_warn_bytes", "ledger_fail_bytes"} <= valid:
        return si_params.ne_findings("體積警戒參數無效")
    if size >= params["ledger_fail_bytes"]:
        return [Finding("-", "VOLUME-FAIL", "fail", f"帳本 {size} 位元組已達 fail 線")]
    if size >= params["ledger_warn_bytes"]:
        return [Finding("-", "VOLUME-WARN", "warn", f"[warn] 帳本 {size} 位元組已達 warn 線")]
    return []


def _vacuity(params: dict, valid: set[str], rows: int) -> list[Finding]:
    if "min_obs_rows" not in valid:
        return si_params.ne_findings("min_obs_rows 無效")
    if rows < params["min_obs_rows"]:
        floor = params["min_obs_rows"]
        return [Finding("-", "LEDGER-BELOW-FLOOR", "info", f"資料列 {rows} 低於下限 {floor}")]
    return []


def _overall(items: list[Item]) -> tuple[str, int]:
    if any(i.status == "FAIL" for i in items):
        return "FAIL", 1
    if any(i.status == "NE" and i.blocking for i in items):
        return "NE", 2
    return "PASS", 0


def _now_cell() -> str:
    z = datetime.now().astimezone()
    off = z.strftime("%z")
    return f"{z.strftime('%Y-%m-%d %H:%M')} {off[:3]}:{off[3:]}"


def obs_draft(items: list[Item], overall: str, rc: int, fp: str, top_id: int) -> str:
    bad = [i.id for i in items if i.status != "PASS"]
    listed = "、".join(bad[:_LIST_MAX]) + (f"…等 {len(bad)} 項" if len(bad) > _LIST_MAX else "")
    cells = [
        f"OBS-SI-{top_id + 1:03d}", _now_cell(), "si check（自動草稿）",
        f"si check 判 {overall}（rc={rc}）：{listed}",
        f"`python tools/selfimproving.py check` rc={rc}；判準指紋 {fp[:19]}",
        "bug", "P3", "open", "面=流程;來源=工具;回報者=si-check",
    ]
    return "| " + " | ".join(cells) + " |"


def run_check(repo: Path, ledger: Path, params: dict, text: str, size: int) -> Result:
    git = Git(repo)
    items, rows, top = build_items(repo, ledger, params, text, size, git)
    overall, rc = _overall(items)
    fp, parts = si_params.fingerprint(repo, params)
    draft = obs_draft(items, overall, rc, fp, top) if rc else None
    return Result(items, rows, overall, rc, fp, parts, draft)


def _one_line(s: str) -> str:
    return " ".join(s.split("\n")).strip()


def render_text(res: Result) -> str:
    out = [f"si-check rows={res.rows} items={len(res.items)}"]
    for it in res.items:
        line = f"{it.status} {it.id}"
        if it.status == "NE":
            line += " blocking" if it.blocking else " nonblocking"
        if it.detail:
            line += f" # {_one_line(it.detail)}"
        out.append(line)
        for fd in it.findings:
            if it.status == "PASS" and fd.level != "warn":
                continue
            out.append(f"  {fd.subject} {fd.code} {_one_line(fd.detail)}".rstrip())
    out.append(f"overall={res.overall} rc={res.rc} fingerprint={res.fingerprint}")
    if res.draft:
        out += ["obs-draft:", res.draft]
    return "\n".join(out) + "\n"


def render_json(res: Result) -> str:
    items = [{
        "id": it.id, "status": it.status, "blocking": it.blocking, "detail": it.detail,
        "findings": [{"subject": f.subject, "code": f.code, "level": f.level, "detail": f.detail}
                     for f in it.findings],
    } for it in res.items]
    obj = {"overall": res.overall, "rc": res.rc, "fingerprint": res.fingerprint,
           "fingerprint_parts": {"manifest": res.parts["manifest"],
                                 "metrics_rev": res.parts["metrics_rev"],
                                 "check_rules_rev": res.parts["check_rules_rev"]},
           "rows": res.rows, "items": items, "obs_draft": res.draft}
    return json.dumps(obj, ensure_ascii=False) + "\n"
