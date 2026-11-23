"""被切／被 TaskStop／殘局代理的三處出聲接線（Control_Handover DES §6.4、REQ-CTL-20、裁10）。

三處呼叫點（Stop `roster.stop_message`、`watch` 判決處置字尾、SessionStart `briefline`）用**同一個**
文字函式 `agentbrief.render_cut(rows)`；判準用 `agentbrief.cut_kind`
（DES 原寫 `rosterscope.cut_kind`，實作住 `agentbrief`）。**不自動重派**——只出聲，重派由主控決定。

WHY 獨立成檔：`roster.py`／`watch.py`／`briefline.py` 各只能加極少行（DES §21 行數牆），判準與閂鎖
一律放在這裡；所有函式 fail-open（出聲失敗不得擋回合結束／簡報／判決）。
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

from . import agentbrief, roster

CUT_STATUSES = ("cut", "stopped", "residue")
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
LATCH_DIR = "control"  # `<trace>/control/<sid>.cutseen`（與 statusLine 區段快取同目錄）


def _latch_path(sid: str) -> Path | None:
    if not _SID_RE.match(sid or ""):
        return None
    import endurance_env  # noqa: PLC0415 — lazy

    return endurance_env.trace_dir_peek()[0] / LATCH_DIR / f"{sid}.cutseen"


def _seen(path: Path | None) -> set[str]:
    try:
        return set(json.loads(path.read_text(encoding="utf-8"))) if path else set()
    except (OSError, ValueError, TypeError):
        return set()


def _key(row: dict) -> str:
    return f"{row['id']}:{row['kind']}"


def _cut_rows(agents: list[dict], sid: str, transcript, projects, *, full: bool) -> list[dict]:
    rows = agentbrief.collect(agents, sid, transcript, full=full, projects=projects)
    return [r for r in rows if r["status"] in CUT_STATUSES]


def stop_text(payload: dict, *, env: Mapping | None = None, now=None) -> str:
    """Stop `systemMessage` 的被切清單：該 sid 每支代理每種被切**只提示一次**
    （閂鎖寫不進去 ⇒ 不出聲，寧缺勿每回合洗版）；沒有新的被切 ⇒ `""`。"""
    try:
        sid, projects = roster._payload_sid(payload), roster._payload_projects(payload)
        latch = _latch_path(sid)
        if latch is None:
            return ""
        proj = roster._projects(projects)
        transcript = roster._main_transcript(proj, sid)
        agents = roster.snapshot(sid, projects_dir=projects, now=now, full=False)["agents"]
        light = _cut_rows(agents, sid, transcript, projects, full=False)
        seen = _seen(latch)
        fresh_ids = {r["id"] for r in light if _key(r) not in seen}
        if not fresh_ids:
            return ""
        keep = [a for a in agents if str(a.get("id")) in fresh_ids]
        rows = [r for r in _cut_rows(keep, sid, transcript, projects, full=True)
                if r["id"] in fresh_ids]
        text = agentbrief.render_cut(rows)
        if not text:
            return ""
        latch.parent.mkdir(parents=True, exist_ok=True)
        latch.write_text(json.dumps(sorted(seen | {_key(r) for r in rows})), encoding="utf-8",
                         newline="\n")
        return text
    except Exception:  # noqa: BLE001 — 見檔頭 fail-open 紀律
        return ""


def watch_text(agents: list[dict], sid: str, transcript, projects=None) -> str:
    """`watch` 判決處置之後的字尾（每次判決都帶、不過閂鎖——主控被叫醒時要看到全貌）；
    有內容時以換行結尾，沒有 ⇒ `""`。"""
    try:
        text = agentbrief.render_cut(_cut_rows(agents, sid, transcript, projects, full=True))
        return text + "\n" if text else ""
    except Exception:  # noqa: BLE001
        return ""


def _cut_orphans(orphans: list[dict]) -> list[dict]:
    """名冊列自帶 `kind` 者照算，否則讀代理逐字稿尾端判（名冊快照本身不帶 `kind`）。"""
    return [r for r in orphans if (r.get("kind") or agentbrief.cut_kind(
        agentbrief.agent_file(str(r.get("owner_sid") or ""), str(r.get("id") or ""), None)
    )) == "usage_limit"]


def orphan_count(orphans: list[dict]) -> int:
    """SessionStart 殘局公告的「被額度切斷」計數。"""
    try:
        return len(_cut_orphans(orphans))
    except Exception:  # noqa: BLE001
        return 0


def brief_text(orphans: list[dict], sid: str | None) -> str:
    """SessionStart 公告的被切清單（只列被額度切斷者；殘局本身由既有一行公告）；沒有 ⇒ `""`。"""
    try:
        rows = [r for r in agentbrief.collect(_cut_orphans(orphans), sid or "", None, full=True)
                if r["status"] == "cut"]
        return ("\n" + agentbrief.render_cut(rows)) if rows else ""
    except Exception:  # noqa: BLE001
        return ""
