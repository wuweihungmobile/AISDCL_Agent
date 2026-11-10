"""SelfImproving `registry-ingest`：Console 登記稽核檔入帳為唯讀鏡像＋`research.registry` 事件
（AC-SI-45-1、45-2；P6）。

能力類別 `rw`：寫研究來源登記鏡像（`registry.REGISTRY_REL`）與事件帳本（經 `wv.append` 的寫入鎖）。
驗證順序見 `_checks`；第一個不符即 rc 1、零寫入。寫入＝鎖內重驗 `audit_ref` 與單調性 → 鏡像以
tmp＋fsync＋`os.replace` 原子換檔（內容未變不改檔）→ 追加事件；事件失敗以 `State.cleanups` 還原
鏡像（入帳前不存在則刪除；盡力而為）。內容未變照寫事件（`changed=false`）：使該 `audit_ref` 被事件
用掉，巡邏不重複嘗試。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import consoleaudit, evwrite, registry
from . import events as si_events
from . import writeverbs as wv
from .decwrite import refuse_unattended
from .obswrite import _atomic_write

PAUSE_HOOK = None  # 測試鉤子：全部驗證完成之後、鎖內寫鏡像之前（不沿用 evwrite.PAUSE_HOOK）
_VERB = "registry-ingest"


def _when(text) -> float | None:
    try:
        return datetime.fromisoformat(text).timestamp()
    except (TypeError, ValueError):
        return None


def _stale(events: list[dict], body: dict) -> list[tuple[str, str]]:
    """單調性（D-EQA-17）：body.time 早於最新 `research.registry` 的 audit_time（絕對時刻）。"""
    last = registry.latest_event(events)
    now, prev = _when(body.get("time")), _when(last.get("audit_time") if last else None)
    if now is not None and prev is not None and now < prev:
        return [("REG-STALE", f"稽核檔 time {body['time']} 早於已入帳的 {last['audit_time']}")]
    return []


def _ref_used(events: list[dict], ref: str) -> bool:
    return any(e.get("kind") == "research.registry" and e.get("audit_ref") == ref for e in events)


def _checks(path: Path, ref: str, events: list[dict]):
    """回（Audit, 錯誤碼清單）；碼序＝大小→R94 鏈→kind→ref 已用→body→大小→sha→REG-*→REG-STALE。"""
    try:
        size = path.stat().st_size
    except OSError:
        size = None
    if size is not None and size > registry.AUDIT_FILE_MAX:
        return None, [("AUDIT-FILE-TOO-LARGE", f"稽核檔 {size} 位元組 > {registry.AUDIT_FILE_MAX}")]
    try:
        audit = consoleaudit.verify(path)
    except consoleaudit.AuditError as exc:
        return None, [(exc.code, exc.detail)]
    if audit.body["kind"] != "src-registry":
        return audit, [("AUDIT-KIND-MISMATCH",
                        f"稽核檔 kind 為 {audit.body['kind']}，{_VERB} 只收 src-registry")]
    if _ref_used(events, ref):
        return audit, [("AUDIT-REF-REUSED", f"audit_ref {ref} 已入帳過")]
    bad = registry.body_codes(audit.body)
    if bad:
        return audit, bad
    reg = registry.validate(audit.body["registry_text"].encode("utf-8"))
    if reg:
        return audit, [(code, f"{sub} {detail}") for code, sub, detail in reg]
    return audit, _stale(events, audit.body)


def _event(audit: consoleaudit.Audit, by: str, prev: dict | None, obj: dict, sha: str) -> dict:
    watch = obj["watch"]
    return {"kind": "research.registry", "by": by, "audit_ref": audit.body["audit_ref"],
            "audit_sha256": audit.sha, "key_id": audit.key_id, "decider": audit.body["user"],
            "carrier": "console", "audit_time": audit.body["time"], "registry_sha256": sha,
            "hosts_n": len(obj["hosts"]), "watch_n": len(watch),
            "watch_on": sum(1 for w in watch if w["enabled"]),
            "changed": prev is None or prev.get("registry_sha256") != sha}


def _render(as_json: bool):
    def render(ev: dict) -> str:
        if as_json:
            return json.dumps({"ok": True, "kind": "research.registry", "seq": ev["seq"],
                               "id": None, "audit_ref": ev["audit_ref"],
                               "changed": ev["changed"], "watch_n": ev["watch_n"],
                               "watch_on": ev["watch_on"], "hosts_n": ev["hosts_n"]},
                              ensure_ascii=False) + "\n"
        return (f"ok research.registry seq={ev['seq']} audit_ref={ev['audit_ref']} "
                f"changed={'true' if ev['changed'] else 'false'} "
                f"watch={ev['watch_n']}/{ev['watch_on']} hosts={ev['hosts_n']}\n")
    return render


def ingest(repo: Path, ref: str, by: str, as_json: bool = False) -> tuple[int, str]:
    out = _ingest(repo, ref, by, as_json)
    return out.rc, out.text


def _ingest(repo: Path, ref: str, by: str, as_json: bool) -> wv.Out:
    refused = refuse_unattended(repo, _VERB, as_json)
    if refused:
        return refused
    params = wv.params_for(repo, "event_max_bytes")
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise wv.UsageError(f"HOME-UNWRITABLE {exc}") from exc
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    audit, codes = _checks(consoleaudit.audit_path(si, ref), ref, events)
    if codes:
        return wv.reject(repo, _VERB, codes, as_json)
    if PAUSE_HOOK is not None:
        PAUSE_HOOK()
    text = audit.body["registry_text"]
    raw, sha = text.encode("utf-8"), registry.sha_of(text.encode("utf-8"))
    obj, path = json.loads(text), repo / registry.REGISTRY_REL

    def build(state):
        if _ref_used(state.events, ref):
            raise evwrite.Reject([("AUDIT-REF-REUSED", "寫入鎖內重驗：audit_ref 已入帳")])
        stale = _stale(state.events, audit.body)
        if stale:
            raise evwrite.Reject(stale)
        old = registry.read_mirror(repo)
        if old != raw:
            path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(path, raw)
            state.cleanups.append(_restore(path, old))
        return _event(audit, by, registry.latest_event(state.events), obj, sha)

    return wv.append(repo, _VERB, build, params, as_json, _render(as_json))


def _restore(path: Path, old: bytes | None):
    def undo() -> None:
        if old is None:
            path.unlink(missing_ok=True)
        else:
            try:
                _atomic_write(path, old)
            except evwrite.Reject:
                pass  # 還原是盡力而為：失敗不得遮蔽使事件追加失敗的原例外
    return undo


__all__ = ["PAUSE_HOOK", "ingest"]
