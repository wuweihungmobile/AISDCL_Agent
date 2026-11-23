"""哨兵接手 park 失敗（QuotaWall DES §7.6；R218 Q3）。

park 到點的 job 是一次性排程，失敗或崩潰後沒有第二道網。額度哨兵本來就每個巡邏間隔醒一次，順手多讀
本 sid 的 park 標記：
· `status=failed` ∧ `outcome.at` 晚於上次巡邏（且尚未接手過）⇒ 依 §7.3 讓路判準看一次，
未讓路再跑一次
  §7.4～§7.5 的失敗鏈（**不殺窗**；`claude` 取標記 `claude` 欄——哨兵 job 的 argv 不帶它）。
· `refused` 不接手（L1 拒絕＝目標不合法，不是續航失敗）；哨兵未武裝＝本函式根本不會被呼叫。
· 標記仍 armed、但痕跡有本包已逾 `SPAWN_INTENT_TTL_SEC` 的 `session_switch_spawning` 意圖且同
attempt
  沒有成功列（job 在開窗途中崩潰）⇒ 先查「前次其實成功」（意圖之後專案目錄出現 stem ≠ 原 sid
  的新逐字稿）：
  有 ⇒ 補寫成功列、標記 `fired`、**不再 spawn**（防雙駕駛）；無 ⇒ 標記改 `failed`（attempts 追加
  `intent_expired`）、出聲、再接手一次。
哨兵行程是排程器跑的真環境行程；本檔是 `sandbox_scope.SITES` 的 tick 站點（先過 L1，沙盒租約過期
＝標記 `refused`）。任何例外一律吞掉並留痕跡——接手分支不得讓哨兵巡邏自己死掉。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from . import (
    handoff,
    park,
    park_announce,
    park_chain,
    park_yield,
    qw_schema,
    se_gate,
    switch,
)

EV_TAKEOVER = "sentinel_park_takeover"
_REPO = Path(__file__).resolve().parents[3]


def last_patrol_at(log: Path) -> float | None:
    """哨兵稽核日誌最後一筆 `sentinel_woken` 的時刻（epoch）；讀不到 ⇒ None。"""
    try:
        lines = Path(log).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    stamps = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("event") == "sentinel_woken":
            when = qw_schema.parse_epoch(rec.get("at"))
            if when is not None:
                stamps.append(when)
    return stamps[-1] if stamps else None


def _stale_intents(pkg: str, now: float) -> list[dict]:
    rows = [r for r in park_chain.trace_rows(qw_schema.EV_SPAWNING, "session_switch_spawned")
            if str(park_chain._pkg_of(r)) == pkg]  # noqa: SLF001
    if any(r.get("event") == "session_switch_spawned" and r.get("ok") is True for r in rows):
        return []
    failed = {r.get(qw_schema.SPAWN_ATTEMPT_KEY) for r in rows if qw_schema.is_failure_row(r)}
    return [r for r in rows if r.get("event") == qw_schema.EV_SPAWNING
            and not qw_schema.is_failure_row(r) and r.get(qw_schema.SPAWN_ATTEMPT_KEY) not in failed
            and (stamp := qw_schema.parse_epoch(r.get("at"))) is not None
            and now - stamp > qw_schema.SPAWN_INTENT_TTL_SEC]


def _recovered(sid: str, intent: dict, S: dict) -> str | None:
    """意圖之後專案目錄出現 stem ≠ 原 sid、含記錄的新逐字稿 ⇒ 回其 stem。"""
    if intent.get("route") != park.FIRE_FRESH and not intent.get("fork"):
        return None  # 普通 -r 不產生新 sid 檔；有人在動由 live_driver 兜住
    proj = Path(S["projects_dir"]) if S.get("projects_dir") else handoff._project_dir(_REPO)
    since = qw_schema.parse_epoch(intent.get("at")) or 0.0
    try:
        for path in sorted(proj.glob("*.jsonl")):
            if path.stem != sid and path.stat().st_size > 0 and path.stat().st_mtime >= since:
                return path.stem
    except OSError:
        return None
    return None


def _write(marker: dict, status: str, event: str, attempts: list, **extra) -> dict:
    outcome = {"at": datetime.now().astimezone().isoformat(), "event": event,
               "detail": str(extra), "attempts": attempts, "takeover": extra.get("takeover", "")}
    new = dict(marker, status=status, outcome=outcome)
    park.write_marker(new)
    return new


def _chain(sid: str, marker: dict, pkg: Path, env, S: dict, clock) -> str:
    from . import park_cli  # noqa: PLC0415 — lazy：park_cli 反向呼叫本檔所在的套件

    now = clock()
    prior = list((marker.get("outcome") or {}).get("attempts") or [])
    row = next((r for r in handoff.list_handoffs(env=env) if r["path"] == pkg), None)
    if row is None or row["state"] != "live":
        _write(marker, marker["status"], "takeover_skipped", prior, takeover="skipped:expired")
        return "skipped:expired"
    import transcript_activity  # noqa: PLC0415

    find = S.get("transcript") or (lambda s: park_cli._find_transcript(s, env))
    transcript = find(sid)
    if transcript_activity.live_driver(transcript, now) is not None:
        _write(marker, marker["status"], "takeover_skipped", prior, takeover="skipped:live_driver")
        return "skipped:live_driver"
    if handoff._duplicate_refusals(pkg, now, S.get("alive") or handoff._alive):
        _write(marker, marker["status"], "takeover_skipped", prior, takeover="skipped:spawned")
        return "skipped:spawned"
    verdict = park_yield.decide(sid, marker, env, S, clock, find)
    if verdict["act"] != "go":
        return f"yield:{verdict['reason']}"  # 不寫接手旗：主載具還活著，之後由它或下次巡邏處理
    claude = marker.get("claude")
    route, _why, _held = park_cli._fire_route(transcript, env, now)
    out = park_chain.run(sid, pkg, route, claude=claude, env=env, S=S, clock=clock,
                         stuck_close=False)
    attempts = prior + out.attempts
    if out.kind == "fired":
        _write(marker, "fired", out.event, attempts, takeover="fired")
        return "fired"
    if out.kind == "refused":
        _write(marker, "refused", "sideeffect_refused", attempts, takeover="refused")
        return "refused"
    if out.kind == "skipped":
        _write(marker, marker["status"], "takeover_skipped", prior,
               takeover=f"skipped:{out.reason}")
        return f"skipped:{out.reason}"
    new = _write(marker, "failed", "park_chain_failed", attempts, takeover="failed_final")
    switch.trace("park_chain_failed", sid=sid, pkg=str(pkg), attempts=attempts, takeover=True)
    park_announce.announce(sid, pkg, new, attempts, claude=claude, env=env, notify=S.get("notify"),
                           repo=park_cli._REPO)  # noqa: SLF001
    return "failed_final"


def _expired(sid: str, marker: dict, pkg: Path, now: float, S: dict) -> str | None:
    """過期意圖：回 `recovered`｜`intent_expired`（標記已改 failed，呼叫端再接手一次）｜None。"""
    stale = _stale_intents(str(pkg), now)
    if not stale or marker["status"] != "armed":
        return None
    intent = stale[-1]
    stem = _recovered(sid, intent, S)
    if stem is not None:
        switch.trace("session_switch_spawned", sid=sid, handoff=str(pkg), ok=True, recovered=True,
                     new_sid=stem, route=intent.get("route"),
                     **{qw_schema.SPAWN_ATTEMPT_KEY: intent.get(qw_schema.SPAWN_ATTEMPT_KEY)})
        _write(marker, "fired", "park_spawn_recovered", [], takeover="recovered")
        switch.trace("park_spawn_recovered", sid=sid, pkg=str(pkg), new_sid=stem)
        return "recovered"
    attempts = [{"route": intent.get("route"), "attempted": True, "rc": None,
                 "reason": "intent_expired", "fork": bool(intent.get("fork"))}]
    switch.trace("park_intent_expired", sid=sid, pkg=str(pkg),
                 **{qw_schema.SPAWN_ATTEMPT_KEY: intent.get(qw_schema.SPAWN_ATTEMPT_KEY)})
    new = _write(marker, "failed", "park_intent_expired", attempts, takeover="")
    park_announce.announce(sid, pkg, new, attempts, claude=marker.get("claude"))
    return "intent_expired"


def on_patrol(sid: str, log: Path, *, env=None, S: dict | None = None, clock=None) -> str | None:
    """哨兵每次巡邏呼叫一次。回結局字串（留給稽核）；沒有動作 ⇒ None；任何例外 ⇒ None 並留痕跡。"""
    env, S = os.environ if env is None else env, dict(S or {})
    clock = clock or (lambda: datetime.now().astimezone())
    try:
        marker = park.read_marker(sid)
        if marker is None or marker["status"] not in ("armed", "failed") or not marker.get("pkg"):
            return None
        pkg = Path(marker["pkg"])
        if se_gate.check("park_takeover.on_patrol", repo=_REPO, pkg=pkg, sid=sid,
                         claude=marker.get("claude")):
            _write(marker, "refused", "sideeffect_refused", [], takeover="refused")
            return "refused"
        result = _expired(sid, marker, pkg, clock().timestamp(), S)
        if result == "recovered":
            switch.trace(EV_TAKEOVER, sid=sid, result=result)
            return result
        marker = park.read_marker(sid) or marker
        outcome = marker.get("outcome") or {}
        patrol = last_patrol_at(log)
        done_at = qw_schema.parse_epoch(outcome.get("at"))
        if (marker["status"] != "failed" or outcome.get("takeover") or done_at is None
                or (patrol is not None and done_at <= patrol)) and result is None:
            return None
        result = _chain(sid, marker, pkg, env, S, clock)
        switch.trace(EV_TAKEOVER, sid=sid, result=result)
        return result
    except Exception as exc:  # noqa: BLE001 — 接手分支不得讓哨兵巡邏死掉
        switch.trace(EV_TAKEOVER, sid=sid, result=f"error:{type(exc).__name__}")
        return None
