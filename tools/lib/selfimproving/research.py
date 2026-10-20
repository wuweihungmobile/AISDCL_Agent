"""SelfImproving `research --fetch`：鎖外抓取、鎖內重驗與追加（TCS-SelfImproving-P1 R57、R58）。

能力類別 `net`（因 import `fetch` 而歸此類；本檔自身不直接 import 網路模組）。流程：預檢（發出任何
請求之前，任一失敗＝整次拒收、零請求、零事件）→ 依來源表順序逐一抓取（不併發、不持鎖）→ 取寫入鎖
→ 鎖內重驗（運轉仍 open、仍無研究事件、來源表雜湊未變）→ 以鎖內最新事件重算 `changed` → 追加
`research.scan`。失敗的來源不入事件、不以舊 digest 代填；成功的來源檔先落地、事件後追加。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import events as si_events
from . import evwrite
from . import fetch as si_fetch
from . import fold as si_fold
from . import sources as si_sources
from .git import Git
from .writeverbs import Out, UsageError, append, draft_for, obs_top, ok_text, params_for, reject

_KEYS = ("research_fetch_max", "research_bytes_max", "research_timeout_seconds", "event_max_bytes")
_NE_COMMIT = {"field": "sources-commit-check", "reason": "git-unavailable"}


def _precheck(repo: Path, run: str, params: dict, git: Git) -> tuple[list, bytes | None, list]:
    """預檢：回（問題碼, 換行正規化後的來源表位元組, ne 提示）。"""
    codes: list = []
    ne: list = []
    f = si_fold.fold(si_events.load_sound_events(repo / si_events.LEDGER_REL) or [])
    r = f.runs.get(run)
    if r is None or r.closed_seq is not None:
        codes.append(("RUN-NOT-OPEN", f"{run} 不是已開未關的運轉"))
    if any(rn == run for _, _, rn, _ in f.research_events):
        codes.append(("RESEARCH-ALREADY", f"{run} 已有研究事件"))
    path = repo / si_sources.SOURCES_REL
    if not path.is_file():
        return codes + [("SOURCES-ABSENT", "來源表不存在")], None, ne
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    codes += [(code, f"{sub} {detail}") for code, sub, detail in
              si_sources.validate_table(raw, si_sources.DEFAULT_POLICY)]
    active = si_sources.active_entries(raw)
    if len(active) > params["research_fetch_max"]:
        codes.append(("FETCH-MAX", f"現役來源 {len(active)} 筆 > {params['research_fetch_max']}"))
    if git.available:
        head = git.show("HEAD", si_sources.SOURCES_REL)
        if head is None or head.replace("\r\n", "\n").encode("utf-8") != raw:
            codes.append(("SOURCES-UNCOMMITTED", "來源表有未提交的改動（或未入 HEAD）"))
    else:
        ne.append(dict(_NE_COMMIT))
    if not active:
        codes.append(("ZERO-SUCCESS", "沒有現役來源可抓"))
    return codes, raw, ne


def _land(si: Path, ident: str, raw: bytes) -> str:
    sha = hashlib.sha256(raw).hexdigest()
    folder = si / "research" / ident
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{sha[:12]}.txt").write_bytes(raw)
    (folder / "latest").write_bytes(sha[:12].encode("ascii"))
    return sha


def _lines(ok: list[dict], failed: list[dict], order: list[str]) -> list[str]:
    by_id = {s["id"]: s for s in ok} | {f["id"]: f for f in failed}
    out = []
    for ident in order:
        s = by_id[ident]
        if "reason" in s:
            out.append(f"source {ident} FAIL {s['reason']}" + (f" {s['detail']}" if s["detail"]
                                                              else ""))
        else:
            out.append(f"source {ident} ok sha256={s['sha256'].split(':')[1][:12]} "
                       f"bytes={s['bytes']} changed={'true' if s['changed'] else 'false'}")
    return out


def run_fetch(repo: Path, run: str, as_json: bool) -> Out:
    if not si_events.RUN_RE.match(run):
        raise UsageError("--run 須為 RUN-SI-NNN")
    params = params_for(repo, *_KEYS)
    git = Git(repo)
    codes, raw, ne = _precheck(repo, run, params, git)
    if codes:
        out = reject(repo, "research", codes, as_json, extra={"ne": ne} if as_json else None)
        return Out(1, out.text + "".join(f"ne {n['field']} {n['reason']}\n" for n in ne
                                         if not as_json))
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise UsageError(f"HOME-UNWRITABLE {exc}") from exc
    active = si_sources.active_entries(raw)
    table_sha = si_sources.sha256_lf(raw)
    allowed = {si_fetch.host_port(e["url"]) for e in active}
    got: list[dict] = []
    failed: list[dict] = []
    for e in active:
        try:
            res = si_fetch.fetch_source(
                e["url"], policy=si_sources.DEFAULT_POLICY,
                timeout=params["research_timeout_seconds"],
                max_bytes=params["research_bytes_max"], allowed_hosts=allowed)
        except si_fetch.FetchError as exc:
            failed.append({"id": e["id"], "reason": exc.reason, "detail": exc.detail})
            continue
        sha = _land(si, e["id"], res.raw)
        got.append({"id": e["id"], "sha256": f"sha256:{sha}", "bytes": len(res.raw),
                    "http_status": res.status})
    order = [e["id"] for e in active]
    if not got:
        return _failure(repo, "ZERO-SUCCESS", "零來源成功，未寫事件（可改記 skip offline）",
                        order, failed, as_json, ne)
    return _commit(repo, run, params, table_sha, got, failed, order, as_json, ne)


def _drafts(repo: Path, failed: list[dict], rc: int) -> list[str]:
    top = obs_top(repo)
    return [draft_for(repo, "research", [], num=top + 1 + i, rc=rc,
                      symptom=f"si research --fetch 來源 {f['id']} 失敗（{f['reason']}）")
            for i, f in enumerate(failed)]


def _failure(repo, code, detail, order, failed, as_json, ne) -> Out:
    drafts = _drafts(repo, failed, 1) or None
    extra = {"failed": failed, "obs_drafts": drafts or [], "ne": ne}
    out = reject(repo, "research", [(code, detail)], as_json, drafts, extra if as_json else None)
    if as_json:
        return out
    return Out(1, "\n".join(_lines([], failed, order)) + "\n" + out.text)


def _commit(repo, run, params, table_sha, got, failed, order, as_json, ne) -> Out:
    path = repo / si_sources.SOURCES_REL

    def build(state):
        f = si_fold.fold(state.events)
        r = f.runs.get(run)
        codes = []
        if r is None or r.closed_seq is not None:
            codes.append(("RUN-NOT-OPEN", f"{run} 於抓取期間已不是 open 運轉"))
        if any(rn == run for _, _, rn, _ in f.research_events):
            codes.append(("RESEARCH-ALREADY", f"{run} 於抓取期間已有研究事件"))
        now = path.read_bytes() if path.is_file() else b""
        if si_sources.sha256_lf(now) != table_sha:
            codes.append(("SOURCES-CHANGED", "來源表於抓取期間被改動"))
        if codes:
            raise evwrite.Reject(codes)
        prior: dict[str, str] = {}
        for ev in state.events:
            if ev.get("kind") == "research.scan":
                for s in ev.get("sources", []):
                    prior[s["id"]] = s["sha256"]
        srcs = [{"id": s["id"], "sha256": s["sha256"], "bytes": s["bytes"],
                 "changed": prior.get(s["id"]) != s["sha256"], "http_status": s["http_status"]}
                for s in got]
        return {"kind": "research.scan", "by": "researcher", "run": run, "sources": srcs,
                "sources_sha256": table_sha, "fetched_at": evwrite.now_iso()}
    rc_after = 2 if failed else 0

    def render(ev) -> str:
        drafts = _drafts(repo, failed, rc_after)
        if as_json:
            return json.dumps({"ok": True, "kind": "research.scan", "seq": ev["seq"], "id": None,
                               "run": run, "rc": rc_after, "sources": ev["sources"],
                               "failed": failed, "obs_drafts": drafts, "ne": ne},
                              ensure_ascii=False) + "\n"
        text = "\n".join(_lines(ev["sources"], failed, order)) + "\n"
        text += ok_text("research.scan", ev["seq"], None, [("run", run)], False)
        text += "".join(f"ne {n['field']} {n['reason']}\n" for n in ne)
        return text + ("obs-draft:\n" + "\n".join(drafts) + "\n" if failed else "")
    out = append(repo, "research", build, params, as_json, render)
    if out.rc == 0:
        return Out(rc_after, out.text)
    return Out(1, "\n".join(_lines(_ok_stub(got), failed, order)) + "\n" + out.text) \
        if not as_json else out


def _ok_stub(got: list[dict]) -> list[dict]:
    return [{**s, "changed": True} for s in got]
