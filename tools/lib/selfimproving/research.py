"""SelfImproving `research --fetch`：鎖外抓取、鎖內重驗與追加（AC-SI-30-2～30-9；P6 改寫）。

能力類別 `net`（因 import `fetch` 而歸此類；本檔自身不直接 import 網路模組）。流程：預檢（發出任何
請求之前，任一失敗＝整次拒收、零請求、零事件；讀 Console 登記鏡像，不讀凍結舊表）→ 依鏡像順序逐一
抓取（不併發、不持鎖；每筆啟用來源再驗 host ∈ 鏡像網域）→ 文章展開（每次掃描都做）→ 取寫入鎖 →
鎖內重驗（運轉仍 open、仍無研究事件、鏡像仍綁定同一筆 `research.registry`）→ 以鎖內最新事件重算
`changed` → 追加 `research.scan`（新格式：`registry_seq`／`registry_sha256`，無 `sources_sha256`）。
失敗的來源不入事件、不以舊 digest 代填；成功的來源檔先落地、事件後追加。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from . import events as si_events
from . import evwrite, expand, htmltext, registry
from . import fetch as si_fetch
from . import fold as si_fold
from .writeverbs import Out, UsageError, append, draft_for, obs_top, ok_text, params_for, reject

_KEYS = ("research_fetch_max", "research_bytes_max", "research_timeout_seconds", "event_max_bytes")
SCAN_WALL_SECONDS = 600
PAUSE_HOOK = None  # 測試鉤子：全部來源抓取完成、取寫入鎖之前（不沿用 evwrite.PAUSE_HOOK）
CLOCK = time.monotonic  # 單調時鐘縫（測試注入偽時鐘）
now_iso = evwrite.now_iso
_HTML = ("text/html", "application/xhtml+xml")


def _precheck(repo: Path, run: str, params: dict) -> tuple[list, bytes | None, dict | None]:
    """預檢：回（問題碼, 鏡像位元組, 鏡像物件）。碼序見 AC-SI-30-2。"""
    codes: list = []
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    f = si_fold.fold(events)
    r = f.runs.get(run)
    if r is None or r.closed_seq is not None:
        codes.append(("RUN-NOT-OPEN", f"{run} 不是已開未關的運轉"))
    if any(rn == run for _, _, rn, _ in f.research_events):
        codes.append(("RESEARCH-ALREADY", f"{run} 已有研究事件"))
    raw = registry.read_mirror(repo)
    if raw is None:
        absent = ("REGISTRY-ABSENT", "研究來源登記鏡像不存在（由 Console 同步入帳）")
        return codes + [absent], None, None
    bad = registry.validate(raw)
    codes += [(code, f"{sub} {detail}") for code, sub, detail in bad]
    ev = registry.latest_event(events)
    if ev is None or ev.get("registry_sha256") != registry.sha_of(raw):
        codes.append(("REGISTRY-UNBOUND", "鏡像位元組雜湊不等於最新 research.registry 事件"))
    obj = None if bad else registry.parse(raw)
    if obj is not None:
        on = [w for w in obj["watch"] if w["enabled"]]
        if len(on) > params["research_fetch_max"]:
            codes.append(("FETCH-MAX", f"啟用來源 {len(on)} 筆 > {params['research_fetch_max']}"))
        if not on:
            codes.append(("ZERO-SUCCESS", "沒有啟用來源可抓"))
    return codes, raw, obj


def _land(folder: Path, raw: bytes, ctype: str, latest: bool) -> tuple[str, str | None]:
    """原始位元組落地 `<sha12>.txt`（HTML 類另落確定性純文字旁檔）；回（sha256, 純文字 sha）。"""
    sha = hashlib.sha256(raw).hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{sha[:12]}.txt").write_bytes(raw)
    plain = None
    if ctype in _HTML:
        text = htmltext.to_plain(raw)
        (folder / f"{sha[:12]}.plain.txt").write_bytes(text)
        plain = hashlib.sha256(text).hexdigest()
    if latest:
        (folder / "latest").write_bytes(sha[:12].encode("ascii"))
    return sha, plain


def _prev_items(si: Path, events: list[dict]) -> dict[str, str]:
    """上一次有明細的掃描：url → sha256；明細檔缺或雜湊不符＝空（全部 changed）。"""
    for ev in sorted(events, key=lambda e: -e["seq"]):
        if ev.get("kind") == "research.scan" and "articles_sha256" in ev:
            try:
                raw = (si / "research" / "_scans" / f"{ev['run']}.json").read_bytes()
                if registry.sha_of(raw) != ev["articles_sha256"]:
                    return {}
                return {i["url"]: i["sha256"] for i in json.loads(raw)["items"] if "sha256" in i}
            except (OSError, ValueError, KeyError, TypeError):
                return {}
    return {}


class _Scan:
    """一次掃描的可變狀態：牆鐘、已抓來源、失敗、文章明細。"""

    def __init__(self, si: Path, params: dict, hosts: set, prev: dict[str, str]) -> None:
        self.si, self.params, self.hosts, self.prev = si, params, hosts, prev
        self.deadline = CLOCK() + SCAN_WALL_SECONDS
        self.got: list[dict] = []
        self.failed: list[dict] = []
        self.items: list[dict] = []

    def get(self, url: str):
        if CLOCK() >= self.deadline:
            raise si_fetch.FetchError("timeout", "整次掃描牆鐘已到")
        return si_fetch.fetch_chain(url, hosts=self.hosts, clock=CLOCK,
                                    timeout=self.params["research_timeout_seconds"],
                                    max_bytes=self.params["research_bytes_max"])

    def source(self, w: dict) -> None:
        try:
            res = self.get(w["url"])
        except si_fetch.FetchError as exc:
            self.failed.append({"id": w["id"], "reason": exc.reason, "detail": exc.detail})
            return
        sha, _ = _land(self.si / "research" / w["id"], res.raw, res.ctype, True)
        self.got.append({"id": w["id"], "sha256": f"sha256:{sha}", "bytes": len(res.raw),
                         "http_status": res.status})
        if w["expand"]:
            self.articles(w, res)

    def articles(self, w: dict, res) -> None:
        ex, ident = w["expand"], w["id"]
        try:
            ents = (expand.sitemap_entries(res.raw) if ex["mode"] == "sitemap"
                    else expand.link_targets(res.raw, res.ctype, w["url"]))
        except expand.ExpandRefused:
            self.items.append({"source": ident, "status": "expand-refused"})
            return
        except expand.ExpandFailed:
            self.items.append({"source": ident, "status": "expand-failed"})
            return
        for rank, url in enumerate(expand.select(ents, w["url"], ex["prefix"], ex["max"]), 1):
            item = {"source": ident, "url": url, "rank": rank}
            try:
                art = self.get(url)
            except si_fetch.FetchError as exc:
                self.items.append({**item, "status": exc.reason})
                self.failed.append({"id": f"{ident}#{rank}", "reason": exc.reason,
                                    "detail": exc.detail, "article": True})
                continue
            sha, plain = _land(self.si / "research" / ident / "articles", art.raw, art.ctype, False)
            self.items.append({**item, "sha256": f"sha256:{sha}", "bytes": len(art.raw),
                               "plain_sha256": None if plain is None else f"sha256:{plain}",
                               "changed": self.prev.get(url) != f"sha256:{sha}", "status": "ok"})


def _write_items(si: Path, run: str, items: list[dict]) -> str:
    """篇目明細 `research/_scans/<RUN>.json`（UTF-8、LF）；回位元組 sha256（`sha256:` 前綴）。"""
    raw = (json.dumps({"schema_rev": 1, "run": run, "items": items}, ensure_ascii=False,
                      indent=2, sort_keys=True) + "\n").encode("utf-8")
    folder = si / "research" / "_scans"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{run}.json").write_bytes(raw)
    return registry.sha_of(raw)


def _lines(ok: list[dict], failed: list[dict], order: list[str]) -> list[str]:
    by_id = {s["id"]: s for s in ok} | {f["id"]: f for f in failed if not f.get("article")}
    out = []
    for ident in order:
        s = by_id[ident]
        if "reason" in s:
            out.append(f"source {ident} FAIL {s['reason']}" + (f" {s['detail']}" if s["detail"]
                                                              else ""))
        else:
            out.append(f"source {ident} ok sha256={s['sha256'].split(':')[1][:12]} "
                       f"bytes={s['bytes']} changed={'true' if s['changed'] else 'false'}")
    out += [f"article {f['id']} FAIL {f['reason']}" for f in failed if f.get("article")]
    return out


def run_fetch(repo: Path, run: str, as_json: bool) -> Out:
    if not si_events.RUN_RE.match(run):
        raise UsageError("--run 須為 RUN-SI-NNN")
    params = params_for(repo, *_KEYS)
    codes, raw, obj = _precheck(repo, run, params)
    if codes:
        return reject(repo, "research", codes, as_json)
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise UsageError(f"HOME-UNWRITABLE {exc}") from exc
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    reg_ev = registry.latest_event(events)
    hosts = {h["host"] for h in obj["hosts"]}
    scan = _Scan(si, params, hosts, _prev_items(si, events))
    active = [w for w in obj["watch"] if w["enabled"]]
    for w in active:
        scan.source(w)
    order = [w["id"] for w in active]
    if not scan.got:
        return _failure(repo, "ZERO-SUCCESS", "零來源成功，未寫事件（可改記 skip offline）",
                        order, scan.failed, as_json)
    arts = None
    if scan.items:
        arts = (len(scan.items), _write_items(si, run, scan.items))
    if PAUSE_HOOK is not None:
        PAUSE_HOOK()
    return _commit(repo, run, params, (reg_ev["seq"], registry.sha_of(raw)), scan, arts, order,
                   as_json)


def _drafts(repo: Path, failed: list[dict], rc: int) -> list[str]:
    top = obs_top(repo)
    src = [f for f in failed if not f.get("article")]
    return [draft_for(repo, "research", [], num=top + 1 + i, rc=rc,
                      symptom=f"si research --fetch 來源 {f['id']} 失敗（{f['reason']}）")
            for i, f in enumerate(src)]


def _failure(repo, code, detail, order, failed, as_json) -> Out:
    drafts = _drafts(repo, failed, 1) or None
    extra = {"failed": failed, "obs_drafts": drafts or []}
    out = reject(repo, "research", [(code, detail)], as_json, drafts, extra if as_json else None)
    if as_json:
        return out
    return Out(1, "\n".join(_lines([], failed, order)) + "\n" + out.text)


def _commit(repo, run, params, reg, scan: _Scan, arts, order, as_json) -> Out:
    reg_seq, reg_sha = reg
    path = repo / registry.REGISTRY_REL

    def build(state):
        f = si_fold.fold(state.events)
        r = f.runs.get(run)
        codes = []
        if r is None or r.closed_seq is not None:
            codes.append(("RUN-NOT-OPEN", f"{run} 於抓取期間已不是 open 運轉"))
        if any(rn == run for _, _, rn, _ in f.research_events):
            codes.append(("RESEARCH-ALREADY", f"{run} 於抓取期間已有研究事件"))
        now = registry.latest_event(state.events)
        cur = path.read_bytes() if path.is_file() else b""
        if registry.sha_of(cur) != reg_sha or now is None or now["seq"] != reg_seq:
            codes.append(("REGISTRY-CHANGED", "登記鏡像於抓取期間被改動或重新入帳"))
        if codes:
            raise evwrite.Reject(codes)
        prior: dict[str, str] = {}
        for ev in state.events:
            if ev.get("kind") == "research.scan":
                for s in ev.get("sources", []):
                    prior[s["id"]] = s["sha256"]
        srcs = [{"id": s["id"], "sha256": s["sha256"], "bytes": s["bytes"],
                 "changed": prior.get(s["id"]) != s["sha256"], "http_status": s["http_status"]}
                for s in sorted(scan.got, key=lambda x: x["id"].encode("utf-8"))]
        ev = {"kind": "research.scan", "by": "researcher", "run": run, "sources": srcs,
              "registry_seq": reg_seq, "registry_sha256": reg_sha, "fetched_at": now_iso()}
        if arts:
            ev.update({"articles_n": arts[0], "articles_sha256": arts[1]})
        return ev
    rc_after = 2 if scan.failed else 0

    def render(ev) -> str:
        drafts = _drafts(repo, scan.failed, rc_after)
        if as_json:
            return json.dumps({"ok": True, "kind": "research.scan", "seq": ev["seq"], "id": None,
                               "run": run, "rc": rc_after, "sources": ev["sources"],
                               "failed": scan.failed, "obs_drafts": drafts},
                              ensure_ascii=False) + "\n"
        text = "\n".join(_lines(ev["sources"], scan.failed, order)) + "\n"
        text += ok_text("research.scan", ev["seq"], None, [("run", run)], False)
        return text + ("obs-draft:\n" + "\n".join(drafts) + "\n" if drafts else "")
    out = append(repo, "research", build, params, as_json, render)
    if out.rc == 0:
        return Out(rc_after, out.text)
    return out


__all__ = ["run_fetch", "SCAN_WALL_SECONDS", "PAUSE_HOOK", "CLOCK"]
