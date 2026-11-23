"""UserPromptSubmit 的 park 失敗提示（QuotaWall DES §7.5 第 3 步、S-11；REQ-QW-35；R218 Q4）。

WHY（2026-11-20 22:42 真事件）：park 到點失敗鏈全數失敗，主控斷線也沒有人知道。桌面通知照使用者偏好
預設關（掌舵者直接指令），所以必達管道是「人眼必經的兩個入口」：開新窗（SessionStart 公告 handback，
既有）與在任一視窗打字（本檔）。對**同專案任一視窗**、**同一個失敗**只注入一次——失敗＝標記
`status=failed` 的 `outcome.at`；已提示者記在 `trace_dir()/park_failure_notice.json`
（`{sid: outcome.at}`）。
只對真人提示出聲（`<task-notification>` 等機器注入不算）；無人窗口、`AUTOSDD_SESSIONCTL_GUARD_OFF`、
模式 off 不出聲。任何例外 ⇒ 不出聲（fail-open：提示壞了不得擋住使用者打字）。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import endurance_env
import transcript_activity

from . import park, qw_schema, roster, switch

EV_NOTICE = "park_failure_notice"
SEEN_NAME = "park_failure_notice.json"
#: 失敗列的有效期：park 最遠只能登記到 `AT_MAX_SECONDS` 之後，更舊的失敗早已超過任何人會關心的時間。
MAX_AGE_SECONDS = park.AT_MAX_SECONDS


def _seen() -> dict:
    try:
        path = endurance_env.trace_dir_peek()[0] / SEEN_NAME
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _mark_seen(rows: dict) -> None:
    try:
        path = endurance_env.trace_dir() / SEEN_NAME
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError:
        pass  # 寫不進去 ⇒ 下一次還會提示（寧可多說一次，不漏說）


def failed_markers(now: datetime, seen: dict, project: Path | None,
                   projects_dir=None) -> list[tuple[str, dict]]:
    """尚未提示、在有效期內、屬於本專案（或查不出專案）的失敗標記 `(sid, marker)`。"""
    folder = endurance_env.trace_dir_peek()[0] / park.PARK_DIR
    found: list[tuple[str, dict]] = []
    try:
        names = sorted(p.stem for p in folder.glob("*.json"))
    except OSError:
        return []
    for sid in names:
        marker = park.read_marker(sid)
        if marker is None or marker.get("status") != "failed":
            continue
        outcome = marker.get("outcome") if isinstance(marker.get("outcome"), dict) else {}
        at = qw_schema.parse_epoch(outcome.get("at"))
        if (at is None or now.timestamp() - at > MAX_AGE_SECONDS
                or seen.get(sid) == outcome.get("at")):
            continue
        transcript = roster._main_transcript(roster._projects(projects_dir), sid)  # noqa: SLF001
        if project is not None and transcript is not None and transcript.parent != project:
            continue
        found.append((sid, marker))
    return found


def _line(sid: str, marker: dict) -> str:
    tried = (marker.get("outcome") or {}).get("attempts") or []
    routes = "、".join(f"{a.get('route')}({a.get('reason') or 'rc=' + str(a.get('rc'))})"
                      for a in tried if isinstance(a, dict)) or "（無嘗試記錄）"
    pkg = marker.get("pkg") or "<交接包>"
    return (f"🔴 park 到點續航失敗：session {sid[:8]} 的備援排程到點後所有嘗試都失敗（{routes}）。"
            f"沒有人會自動接手——請手動 `claude -r {sid}` 回舊 session，或 "
            f"`python tools/sessionctl.py handoff --spawn {pkg}`；"
            "細節見 handback（`<sid>_park_failed`）與 `python tools/sessionctl.py status`。")


def failure_notice(payload: dict, env=None, *, now: datetime | None = None,
                   projects_dir=None) -> str:
    """真人提示時回要注入的提示文字（同一失敗只一次）；沒有／不適用 ⇒ `""`。"""
    env = os.environ if env is None else env
    try:
        if (not isinstance(payload, dict) or not isinstance(payload.get("prompt"), str)
                or env.get("AUTOSDD_UNATTENDED") or env.get("AUTOSDD_SESSIONCTL_GUARD_OFF")
                or switch.switch_mode(env) == "off"
                or not transcript_activity.is_forwardable_prompt(payload["prompt"])):
            return ""
        raw = payload.get("transcript_path")
        project = Path(raw).parent if isinstance(raw, str) and raw.strip() else None
        now = now or datetime.now().astimezone()
        seen = _seen()
        rows = failed_markers(now, seen, project, projects_dir)
        if not rows:
            return ""
        for sid, marker in rows:
            seen[sid] = (marker.get("outcome") or {}).get("at")
            switch.trace(EV_NOTICE, sid=roster._payload_sid(payload), failed_sid=sid)  # noqa: SLF001
        _mark_seen(seen)
        return "\n".join(_line(sid, marker) for sid, marker in rows)
    except Exception:  # noqa: BLE001 — fail-open
        return ""
