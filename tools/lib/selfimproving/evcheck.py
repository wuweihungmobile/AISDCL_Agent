"""SelfImproving `check` 的 P1 追加項：事件帳本重放與研究來源表（TCS-SelfImproving-P1 R36～R43）。

唯讀、不連網；唯一的子行程出口是 `git.py`。回傳「項目 ID → (findings, 項目層 detail)」，
判級與輸出由 `check.py` 組裝。載體缺席一律 nonblocking NE（`CARRIER-NOT-ESTABLISHED`）。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from . import decheck
from . import events as si_events
from . import fold as si_fold
from . import params as si_params
from . import paths as si_paths
from . import sources as si_sources
from .git import Git
from .ledger import Finding
from .refs import git_ne

EVENT_ITEMS = ("events.structure", "events.transitions", "events.mutated", "events.vacuity",
               "events.prop_files", "events.research")
ITEM_IDS = EVENT_ITEMS + ("research.sources",) + decheck.P2_ITEMS
_CARRIER = "CARRIER-NOT-ESTABLISHED"
Result = dict[str, tuple[list[Finding], str]]


def _subject(ln: si_events.Line) -> str:
    seq = ln.obj.get("seq") if ln.obj else None
    return f"seq={seq}" if isinstance(seq, int) and not isinstance(seq, bool) else f"L{ln.no}"


def _disposition_bytes(sub: str, obj: dict, params: dict, valid: set[str]) -> list[Finding]:
    """R72：`obs.close.disposition` 位元組數 ≤ `row_max_bytes`（單事件判準讀不到參數）。"""
    disp = obj.get("disposition")
    if obj.get("kind") != "obs.close" or not isinstance(disp, str) or "row_max_bytes" not in valid:
        return []
    size = len(disp.encode("utf-8"))
    if size <= params["row_max_bytes"]:
        return []
    return [Finding(sub, "EVENT-TYPE", "fail", f"disposition {size} 位元組 > row_max_bytes")]


def _structure(lines: list[si_events.Line], params: dict, valid: set[str]) -> list[Finding]:
    out: list[Finding] = []
    limit = params["event_max_bytes"] if "event_max_bytes" in valid else None
    if limit is None:
        out += si_params.ne_findings("event_max_bytes 無效，無法判定事件行位元組")
    top = 0
    for ln in lines:
        sub = _subject(ln)
        if ln.obj is None:
            out.append(Finding(sub, "EVENT-PARSE", "fail", "空白行或非 JSON 物件的行"))
            continue
        out += [Finding(sub, code, "fail", detail) for code, detail in si_events.validate(ln.obj)]
        out += _disposition_bytes(sub, ln.obj, params, valid)
        if limit is not None and ln.nbytes > limit:
            out.append(Finding(sub, "EVENT-BYTES-OVER", "fail", f"{ln.nbytes} 位元組 > {limit}"))
        seq = ln.obj.get("seq")
        if isinstance(seq, int) and not isinstance(seq, bool) and seq >= 1:
            if seq <= top:
                out.append(Finding(sub, "EVENT-SEQ", "fail", f"seq 非嚴格遞增（前高 {top}）"))
            top = max(top, seq)
    return out


def _transitions(events: list[dict], params: dict, valid: set[str]) -> list[Finding]:
    vmax = params["verify_runs_max"] if "verify_runs_max" in valid else None
    f = si_fold.fold(events, None, vmax)
    out = [Finding(sub, code, "fail", detail) for code, sub, detail in f.problems]
    out += [Finding(sub, code, "warn", f"[warn] {detail}") for code, sub, detail in f.warns]
    if vmax is None:
        out += si_params.ne_findings("verify_runs_max 無效，無法判定 VERIFY-RUNS-EXCEEDED")
    return out


def _seq_of(line: str) -> str | None:
    try:
        seq = json.loads(line).get("seq")
    except (ValueError, AttributeError):
        seq = None
    return f"seq={seq}" if isinstance(seq, int) and not isinstance(seq, bool) else None


def _mutated(repo: Path, git: Git, work: str) -> tuple[list[Finding], str]:
    if not git.available:
        return [git_ne()], ""
    log = git.log_first_parent(si_events.LEDGER_REL)
    if not log:
        return [], "no-history"
    versions = [(log[0][:7], git.show(log[0], si_events.LEDGER_REL) or "")]
    for sha in git.log_first_parent(si_events.LEDGER_REL, f"{log[0]}..HEAD") or []:
        versions.append((sha[:7], git.show(sha, si_events.LEDGER_REL) or ""))
    work = work.replace("\r\n", "\n")
    if work != versions[-1][1].replace("\r\n", "\n"):
        versions.append(("WORKTREE", work))
    out = []
    for (_, old), (label, new) in zip(versions, versions[1:]):
        before, after = _rows(old), _rows(new)
        for i, line in enumerate(before):
            cause = "deleted" if i >= len(after) else ("changed" if after[i] != line else None)
            if cause:
                out.append(Finding(_seq_of(line) or f"L{i + 1}", "ROW-MUTATED", "fail",
                                   f"commit={label} cause={cause} 事件行被改寫，請掌舵者過目"))
    return out, ""


def _rows(text: str) -> list[str]:
    rows = text.replace("\r\n", "\n").split("\n")
    return rows[:-1] if rows and rows[-1] == "" else rows


def _vacuity(events: list[dict], params: dict, valid: set[str]) -> list[Finding]:
    if "min_events" not in valid:
        return si_params.ne_findings("min_events 無效")
    if len(events) < params["min_events"]:
        return [Finding("-", "EVENTS-BELOW-FLOOR", "info",
                        f"事件 {len(events)} 筆低於下限 {params['min_events']}")]
    return []


def _prop_files(repo: Path, events: list[dict]) -> list[Finding]:
    out = []
    for ev in events:
        if ev.get("kind") != "prop" or not isinstance(ev.get("id"), str) \
                or not isinstance(ev.get("rev"), int):
            continue
        sub = f"{ev['id']} r{ev['rev']}"
        d = repo / si_events.PROPOSALS_REL / ev["id"]
        patch, body = d / f"r{ev['rev']}.patch", d / f"r{ev['rev']}.md"
        missing = [p.name for p in (patch, body) if not p.is_file()]
        out += [Finding(sub, "PROP-FILE-MISSING", "fail", f"內容檔缺：{n}") for n in missing]
        if not patch.is_file() and not body.is_file():
            continue
        if patch.is_file():
            out += _patch_findings(sub, ev, patch.read_bytes())
        if body.is_file():
            sha = "sha256:" + hashlib.sha256(body.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            if sha != ev.get("body_sha256"):
                out.append(Finding(sub, "PROP-BODY-SHA-MISMATCH", "fail", ".md 雜湊與事件不符"))
    return out + _verify_files(repo, events)


def _verify_files(repo: Path, events: list[dict]) -> list[Finding]:
    """R90 (a)：`verify_sha256` 非 null 的 `app.verify`（該 PROP 的第 K 筆）須有 `verify<K>.json`，
    且位元組雜湊相符（缺檔沿 `PROP-FILE-MISSING`；不符＝`PROP-VERIFY-SHA-MISMATCH`）。"""
    out, count = [], {}
    for e in events:
        if e.get("kind") != "app.verify":
            continue
        count[e["prop"]] = k = count.get(e["prop"], 0) + 1
        if e.get("verify_sha256") is None:
            continue
        sub = f"{e['prop']} verify{k}"
        path = repo / si_events.PROPOSALS_REL / e["prop"] / f"verify{k}.json"
        if not path.is_file():
            out.append(Finding(sub, "PROP-FILE-MISSING", "fail", f"內容檔缺：{path.name}"))
        elif "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() != e["verify_sha256"]:
            out.append(Finding(sub, "PROP-VERIFY-SHA-MISMATCH", "fail", "驗證檔雜湊與事件不符"))
    return out


def _patch_findings(sub: str, ev: dict, raw: bytes) -> list[Finding]:
    if "sha256:" + hashlib.sha256(raw).hexdigest() != ev.get("patch_sha256"):
        return [Finding(sub, "PROP-PATCH-SHA-MISMATCH", "fail", ".patch 雜湊與事件不符")]
    try:
        touched = si_paths.touched_of(raw)
    except si_paths.PatchError:
        touched = None
    if touched is None or len(touched) != ev.get("touched_count") \
            or si_paths.touched_sha256(touched) != ev.get("touched_sha256"):
        return [Finding(sub, "PROP-TOUCHED-MISMATCH", "fail", "touched 由 .patch 重導出與事件不符")]
    return []


def _research(repo: Path, git: Git, events: list[dict], src_raw: bytes | None) -> list[Finding]:
    f = si_fold.fold(events)
    out: list[Finding] = []
    runs = {r for _, _, r, _ in f.research_events if r} | set(f.runs)
    firsts: dict[str, int] = {}
    for ev in events:
        if ev.get("kind") == "prop" and isinstance(ev.get("run"), str):
            firsts.setdefault(ev["run"], ev.get("seq"))
    for run in sorted(runs):
        rs = [seq for seq, _, r, _ in f.research_events if r == run]
        if len(rs) > 1:
            out.append(Finding(run, "RESEARCH-MULTIPLE", "fail", f"研究事件多於一筆 seq={rs}"))
        if run in firsts and not rs:
            out.append(Finding(run, "RESEARCH-MISSING", "fail", "有 prop 而無研究事件"))
        if len(rs) == 1 and run in f.runs:
            hi = firsts.get(run)
            if not (f.runs[run].opened_seq < rs[0] and (hi is None or rs[0] < hi)):
                out.append(Finding(run, "RESEARCH-ORDER", "fail",
                                   f"研究事件 seq={rs[0]} 不介於 run.open 與第一筆 prop 之間"))
    scans = [ev for _, k, _, ev in f.research_events if k == "research.scan"]
    out += _scan_findings(git, scans, src_raw)
    return out + decheck.helmsman_refs(repo, events)


def _scan_findings(git: Git, scans: list[dict], src_raw: bytes | None) -> list[Finding]:
    if not scans:
        return []
    out: list[Finding] = []
    ids = si_sources.ids_or_none(src_raw)
    if ids is None:
        return [Finding("-", "SOURCE-UNAVAILABLE", "info", "來源表不存在或無法解析")]
    else:
        for ev in scans:
            for s in ev.get("sources") if isinstance(ev.get("sources"), list) else []:
                sid = s.get("id") if isinstance(s, dict) else None
                if sid not in ids:
                    out.append(Finding(f"seq={ev.get('seq')} {sid}", "SRC-UNKNOWN", "fail",
                                       "sources[].id 不在來源表"))
    if not git.available:
        return out + [Finding("-", "SOURCES-HISTORY-NOT-ESTABLISHED", "info", "git 不可用")]
    times = git.log_times(si_sources.SOURCES_REL)
    for ev in scans:
        out += _history_finding(git, ev, times or [])
    return out


def _history_finding(git: Git, ev: dict, times: list[tuple[str, int]]) -> list[Finding]:
    try:
        when = datetime.fromisoformat(ev["t"]).timestamp()
    except (KeyError, TypeError, ValueError):
        return []
    sub = f"seq={ev.get('seq')}"
    older = [(sha, ct) for sha, ct in times if ct <= when]
    if not older:
        return [Finding(sub, "SOURCES-SHA-MISMATCH", "fail", "事件 t 之前沒有任何提交含來源表")]
    sha = max(older, key=lambda p: p[1])[0]
    text = git.show(sha, si_sources.SOURCES_REL)
    got = si_sources.sha256_lf((text or "").encode("utf-8"))
    if got != ev.get("sources_sha256"):
        return [Finding(sub, "SOURCES-SHA-MISMATCH", "fail",
                        f"sources_sha256 與提交 {sha[:7]} 的來源表雜湊不符")]
    return []


def _sources_item(src_raw: bytes | None) -> list[Finding]:
    if src_raw is None:
        return [Finding("-", _CARRIER, "info", "research_sources.json 不存在")]
    return [Finding(sub, code, "fail", detail)
            for code, sub, detail in si_sources.validate_table(src_raw, si_sources.DEFAULT_POLICY)]


def compute(repo: Path, params: dict, valid: set[str], git: Git) -> Result:
    ledger = repo / si_events.LEDGER_REL
    src_path = repo / si_sources.SOURCES_REL
    src_raw = src_path.read_bytes() if src_path.is_file() else None
    out: Result = {"research.sources": (_sources_item(src_raw), "")}
    if not ledger.is_file():
        carrier = [Finding("-", _CARRIER, "info", "事件帳本不存在")]
        out.update({item: (list(carrier), "") for item in EVENT_ITEMS + decheck.P2_ITEMS})
        orphans = decheck.obs_console_audit(repo, [])  # 帶 carrier=console 的列本身就是待對帳的證據
        if orphans:
            out["obs.console_audit"] = (orphans, "")
        return out
    raw = ledger.read_bytes()
    lines = si_events.read_lines(raw)
    events = [ln.obj for ln in lines if ln.obj is not None]
    sound = si_events.sound(events)
    muts, mut_detail = _mutated(repo, git, raw.decode("utf-8", "replace").lstrip("﻿"))
    out.update({
        "events.structure": (_structure(lines, params, valid), ""),
        "events.transitions": (_transitions(sound, params, valid), ""),
        "events.mutated": (muts, mut_detail),
        "events.vacuity": (_vacuity(events, params, valid), ""),
        "events.prop_files": (_prop_files(repo, sound), ""),
        "events.research": (_research(repo, git, sound, src_raw), ""),
        "events.dec_quote": (decheck.dec_quote(repo, sound, params, git), ""),
        "events.dec_console": (decheck.dec_console(repo, sound, params, git), ""),
        "events.verdict": (decheck.verdict_item(sound, params, valid), ""),
        "obs.console_audit": (decheck.obs_console_audit(repo, sound), ""),
    })
    return out
