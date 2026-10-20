"""SelfImproving `scan`：模組體檢的確定性半（TCS-SelfImproving-P1 R59）。

唯讀、離線、無狀態、不寫事件、不碰家目錄；唯一的子行程出口是 `git.py`。彙整本地證據（缺陷帳本、
OBS 帳本與 commit、事件帳本、測試報告與探針產物）印 OBS 候選草稿列；零候選＝「無事件」，
量不到的來源逐一標出原因、不併入零，也從不印成通過。`status` 共用本檔的起算點與缺陷判定。
"""

from __future__ import annotations

import fnmatch
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from . import defs as si_defs
from . import events as si_events
from . import fold as si_fold
from . import refs as si_refs
from . import rows as si_rows
from .git import Git
from .ledger import max_valid_id, parse_ledger

DEFECT_LOG_REL = "docs/06_quality/AutoSDD_Defect_Log.md"
PROBE_OUTPUT_GLOBS = ("**/misstep_attribution*.jsonl",)
BUCKETS = ("SelfImproving", "AutoClaude", "AISDLC_SDD", "AgentConsole", "根層")
_NEED_COLS = ("ID", "發現日期", "嚴重度", "狀態")
_PRUNE = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache"}
_ARTIFACT_EXT = (".xml", ".json", ".log", ".txt")
_MAX_PATHS = 3


def bucket_of(path: str) -> str:
    """路徑 → 模組桶（SelfImproving → AutoClaude → AISDLC_SDD → AgentConsole → 根層）；
    非 repo 相對形態（絕對、含 `..`、磁碟機代號、空字串）歸 `未分類`。"""
    p = path.replace("\\", "/")
    if not p or p.startswith("/") or ":" in p or ".." in p.split("/"):
        return "未分類"
    name = p.rsplit("/", 1)[-1]
    if (p.startswith(("tools/lib/selfimproving/", "tools/probe/selfimproving_",
                      "tools/tests/test_selfimproving_")) or p == "tools/selfimproving.py"
            or (p.startswith("docs/") and "SelfImproving" in name)):
        return "SelfImproving"
    for root, bucket in (("AutoClaude/", "AutoClaude"), ("AISDLC_SDD/", "AISDLC_SDD"),
                         ("AgentConsole/", "AgentConsole")):
        if p.startswith(root):
            return bucket
    return "根層"


def _utc(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat(timespec="seconds")


def anchor(git: Git, events: list[dict] | None, params: dict, since: str | None) -> dict:
    """起算點：`--since` 的 commit ＞ 最近 `run.close` 的 `t` ＞ `migration_base_sha` 提交時間。"""
    none = {"kind": None, "time": None, "epoch": None}
    if since is not None:
        ct = git.commit_time(since)
        return {"kind": "since", "time": _utc(ct), "epoch": ct} if ct is not None else none
    closes = [e for e in events or [] if e.get("kind") == "run.close"]
    if closes:
        try:
            return {"kind": "run.close", "time": closes[-1]["t"],
                    "epoch": datetime.fromisoformat(closes[-1]["t"]).timestamp()}
        except (KeyError, TypeError, ValueError):
            pass
    sha = params.get("migration_base_sha")
    ct = git.commit_time(sha) if isinstance(sha, str) and git.available else None
    return {"kind": "migration_base_sha", "time": _utc(ct), "epoch": ct} if ct is not None else none


def defect_hits(repo: Path, a: dict) -> tuple[list, str | None]:
    """缺陷帳本主檔中：嚴重度 P1／P2、狀態分類 open、發現日期不早於起算日（UTC）的列。
    回（DefRow 串列, 量不到的原因碼）。"""
    path = repo / DEFECT_LOG_REL
    if not path.is_file():
        return [], "ledger-missing"
    cols = si_defs.columns(path)
    if cols is None or not set(_NEED_COLS) <= set(cols):
        return [], "ledger-header"
    if a["epoch"] is None:
        return [], "anchor-unavailable"
    day = _utc(a["epoch"])[:10]
    return [r for r in si_defs.load_rows(path)
            if r.severity in ("P1", "P2") and r.status == "open" and r.date[:10] >= day], None


def _commits(git: Git, a: dict, since: str | None) -> list[tuple[str, list[str]]] | None:
    args = ["-c", "core.quotepath=false", "log", "--format=%x01%H %ct", "--name-only"]
    cp = git.run(*args, f"{since}..HEAD") if since else git.run(*args)
    if cp is None or cp.returncode != 0:
        return None
    out = []
    for chunk in cp.stdout.split("\x01")[1:]:
        head, *files = chunk.split("\n")
        sha, ct = head.split()
        if since or int(ct) > a["epoch"]:
            out.append((sha, [f for f in files if f.strip()]))
    return out


def _walk_count(repo: Path, keep) -> int:
    n = 0
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in _PRUNE]
        rel = Path(root).relative_to(repo).as_posix()
        n += sum(1 for f in files if keep(f if rel == "." else f"{rel}/{f}"))
    return n


def _obs_in_window(repo: Path, a: dict) -> int:
    text = si_refs.obs_ledger_text(repo)
    n = 0
    for r in parse_ledger(text).rows if text else []:
        m = si_rows.TIME_RE.match(r.cells[1]) if r.nine else None
        if not m:
            continue
        try:
            off = m[7] or "+00:00"
            when = datetime.fromisoformat(f"{m[1]}-{m[2]}-{m[3]}T{m[4]}:{m[5]}:00{off}")
        except ValueError:
            continue
        n += 1 if when.timestamp() >= a["epoch"] else 0
    return n


def _events_source(events: list[dict] | None, params: dict) -> dict:
    if events is None:
        return {"id": "event_ledger", "status": "unavailable", "reason": "carrier-not-established"}
    f = si_fold.fold(events, params.get("stop_after_bad"))
    pending = sum(1 for p in f.props.values() if p.state in ("proposed", "verified"))
    return {"id": "event_ledger", "status": "read",
            "count": pending + (1 if f.suspended else 0) + len(f.cooldowns)}


def _bucket_candidates(commits: list, num: int, limit: int) -> list[dict]:
    per: dict[str, dict] = {}
    for sha, files in commits:
        for b in {bucket_of(f) for f in files}:
            d = per.setdefault(b, {"shas": [], "paths": set()})
            d["shas"].append(sha)
            d["paths"].update(f for f in files if bucket_of(f) == b)
    out = []
    for b in (*BUCKETS, "未分類"):
        if b not in per:
            continue
        paths, k, sha = sorted(per[b]["paths"])[:_MAX_PATHS], len(per[b]["shas"]), per[b]["shas"][0]
        for n in range(len(paths), -1, -1):  # 過長的路徑清單逐個縮短，守住列位元組上限
            tail = f"（{'、'.join(paths[:n])}）" if n else ""
            text = si_rows.draft_row(num + len(out), "si scan（自動草稿）",
                                     f"{b} 窗內有 {k} 個 commit 觸及{tail}", f"commit {sha[:12]}",
                                     "scan")
            if len(text.encode("utf-8")) <= limit:
                break
        out.append({"bucket": b, "row": text})
    return out


def run(repo: Path, git: Git, params: dict, since: str | None) -> dict:
    """掃描結果物件（鍵序同 `--json` 輸出：schema_rev、status、unavailable_count、anchor、
    sources、candidates、buckets）。"""
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL)
    a = anchor(git, events, params, since)
    text = si_refs.obs_ledger_text(repo)
    num = (max_valid_id(parse_ledger(text)) if text else 0) + 1
    src: list[dict] = []
    cands: list[dict] = []
    hits, why = defect_hits(repo, a)
    src.append({"id": "defects", "status": "unavailable", "reason": why} if why else
               {"id": "defects", "status": "read", "count": len(hits)})
    for r in hits:
        cands.append({"bucket": "defects", "row": si_rows.draft_row(
            num, "si scan（自動草稿）", f"缺陷帳本新立 {r.severity} 未結列 {r.ident}", r.ident,
            "scan")})
        num += 1
    commits = _commits(git, a, since) if git.available and a["epoch"] is not None else None
    if commits is None:
        src.append({"id": "observations", "status": "unavailable",
                    "reason": "anchor-unavailable" if git.available else "git-unavailable"})
    else:
        src.append({"id": "observations", "status": "read",
                    "count": _obs_in_window(repo, a) + len(commits)})
        cands += _bucket_candidates(commits, num, params["row_max_bytes"])
    src.append(_events_source(events, params))
    probe = tuple(g.split("/", 1)[1] for g in PROBE_OUTPUT_GLOBS)
    for sid, keep in (
            ("build_reports", lambda p: "build/reports/" in p and p.endswith(_ARTIFACT_EXT)),
            ("probe_outputs", lambda p: any(fnmatch.fnmatch(p.rsplit("/", 1)[-1], g)
                                            for g in probe))):
        n = _walk_count(repo, keep)
        src.append({"id": sid, "status": "read", "count": n} if n else
                   {"id": sid, "status": "unavailable", "reason": "no-artifacts"})
    buckets: dict[str, int] = {}
    for c in cands:
        if c["bucket"] != "defects":
            buckets[c["bucket"]] = buckets.get(c["bucket"], 0) + 1
    return {"schema_rev": 1, "status": "candidates" if cands else "no-event",
            "unavailable_count": sum(1 for s in src if s["status"] == "unavailable"),
            "anchor": {"kind": a["kind"], "time": a["time"]}, "sources": src,
            "candidates": cands, "buckets": buckets}


def render_text(res: dict) -> str:
    lines = [f"source {s['id']} 讀到 {s['count']} 筆" if s["status"] == "read"
             else f"source {s['id']} 量不到：{s['reason']}" for s in res["sources"]]
    k = res["unavailable_count"]
    if res["candidates"]:
        lines += ["candidates:", *[c["row"] for c in res["candidates"]],
                  f"候選 {len(res['candidates'])} 筆"]
    else:
        lines.append("無事件" + (f"（{k} 個來源量不到）" if k else ""))
    return "\n".join(lines) + "\n"


def render_json(res: dict) -> str:
    return json.dumps(res, ensure_ascii=False) + "\n"
