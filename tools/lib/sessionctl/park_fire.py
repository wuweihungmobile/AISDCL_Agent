"""park 到點的 job 本體（`park --fire`；QuotaWall DES §7.0～§7.5；R218 Q3）。

自 `park_cli._cmd_fire` 搬出（`_cmd_fire` 仍是站點：入口先過 L1，拒絕＝終局，才呼叫本檔）。
次序是契約：
前置（armed／未 ack／包 live／無 live_driver／未剛 spawn）→ §7.3 主載具讓路 → F4 選路 → §7.5
失敗鏈。
結局只有 skipped／fired／failed／refused：failed 才出聲（handback＋佇列＋依偏好桌面通知）；
refused（L1）永不進失敗鏈、不出聲。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import handoff, park, park_announce, park_chain, park_yield, qw_schema, switch

_RC_REFUSED = 4


def run(opts, sid: str, env, S: dict, clock, marker, label: str, pkg: Path, now: datetime) -> int:
    from . import oldwin_park, park_cli  # noqa: PLC0415 — lazy：兩者反向呼叫本檔

    def finish(rc: int, status: str | None = None, event: str = "", attempts=None, **extra) -> int:
        if marker is not None and marker["status"] == "armed" and status:
            park_chain.settle(marker, status, event, attempts, **extra)
        park_cli._disarm_verified(label, S)  # 自拆（失敗不影響 rc：job 一次性）
        return rc

    def skip(reason: str, **extra) -> int:
        switch.trace("handoff_spawn_skipped", sid=sid, job=label, reason=reason, **extra)
        return finish(0, "skipped", reason)

    mine = marker is not None and label in {j["label"] for j in marker["jobs"]}
    if not mine or marker["status"] != "armed":
        return skip("cancelled" if marker and marker["status"] == "cancelled" else "not_armed")
    if env.get(park.UNATTENDED_ENV):
        return finish(_RC_REFUSED)
    if pkg.with_suffix(".ack").exists():
        return skip("acked")
    row = next((r for r in handoff.list_handoffs(env=env) if r["path"] == pkg), None)
    if row is None or row["state"] != "live":
        return skip("expired")
    import transcript_activity  # noqa: PLC0415

    find = S.get("transcript") or (lambda s: park_cli._find_transcript(s, env))
    transcript = find(sid)
    driver = transcript_activity.live_driver(transcript, now)
    if driver is not None:
        return skip("live_driver", driver_kind=driver["kind"], driver_at=driver["timestamp"])
    if handoff._duplicate_refusals(pkg, now, S.get("alive") or handoff._alive):
        return skip("spawned")  # forward／--spawn 已開出新 session、對方還沒 ack：不再動舊 sid
    verdict = park_yield.decide(sid, marker, env, S, clock, find)
    if verdict["act"] == "skip":
        return skip(verdict["reason"])
    if verdict["act"] == "rearm":
        res = oldwin_park._rearm(sid, pkg, verdict["when"], env, handoff._aware(now), S,  # noqa: SLF001 — 站點本體（SITES 登記名）
                                 extra=park_yield.rearm_fields(marker, verdict["when"]))
        if res == "ok":
            park_yield.trace_yield(sid, label, verdict, now)
            return finish(0)  # 標記已換成新排程；本 job 自拆，不動標記狀態
        if res == "refused":  # 重排前 L1 拒絕＝終局 refused，不進失敗鏈
            return finish(0, "refused", "sideeffect_refused", reason="rearm_refused")
        # failed：排不出重排 ⇒ 不能把備援丟掉，往下走（舊窗晚醒時 keepwarm 的交棒重判兜住）
    stuck = verdict["stuck"] and qw_schema.marker_primary(marker).close_stuck_window
    route, why, held = park_cli._fire_route(transcript, env, now)
    switch.trace("park_route", sid=sid, job=label, route=route, why=why, ctx=held)
    out = park_chain.run(sid, pkg, route, claude=opts.claude, env=env, S=S, clock=clock,
                         stuck_close=stuck)
    if out.kind == "skipped":
        return skip(out.reason)
    if out.kind == "refused":  # spawn 站點 L1 拒絕＝終局，不算失敗、不走另一路
        return finish(0, "refused", "sideeffect_refused", out.attempts, route=route)
    if out.kind == "fired":
        switch.trace(out.event, sid=sid, job=label, pkg=str(pkg), rc=out.attempts[-1]["rc"],
                     route=out.attempts[-1]["route"], fork=out.attempts[-1]["fork"])
        return finish(0, "fired", out.event, out.attempts)
    switch.trace("park_chain_failed", sid=sid, job=label, pkg=str(pkg), attempts=out.attempts)
    park_announce.announce(sid, pkg, marker, out.attempts, claude=opts.claude, env=env,
                           notify=S.get("notify"), repo=park_cli._REPO)  # noqa: SLF001
    return finish(1, "failed", "park_chain_failed", out.attempts)
