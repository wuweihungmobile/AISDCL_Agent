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
    from . import othersession  # noqa: PLC0415 — WP-SW REQ-CTL-52：同專案另一 session 在動（惰性：不進頂層閉包）

    other = othersession.active(transcript.parent if transcript is not None else None, sid, now)
    if other is not None:
        done = int(marker.get(othersession.DEFERS_KEY) or 0)
        if done < othersession.OTHER_SESSION_MAX_DEFERS:  # 延後：沿用 park_yield 的重排原語，計數欄分開
            when = now.timestamp() + othersession.SENTINEL_INTERVAL_SECONDS
            res = oldwin_park._rearm(sid, pkg, when, env, handoff._aware(now), S,  # noqa: SLF001
                                     extra=othersession.rearm_fields(marker, when))
            if res == "refused":
                return finish(0, "refused", "sideeffect_refused", reason="rearm_refused")
            if res == "ok":
                othersession.trace("defer", sid, other, n=done + 1)
                return finish(0)
        othersession.trace("skip", sid, other, n=done)  # 用盡（或排不出重排）⇒ 終局 skip，且必須出聲
        rc = skip("other_session", other_sid=other["sid"])
        park_announce.announce(
            sid, pkg, marker, [], claude=opts.claude, env=env, notify=S.get("notify"),
            repo=park_cli._REPO,  # noqa: SLF001
            title="park 接手已放棄：他 session 在動、交接包待人接", tail="park_other_session",
            body=(f"session {sid[:8]} 的 park 到點時另一個 session（{other['sid'][:8]}）仍在動，延後 {done} 次後放棄；"
                  f"手動接手：python tools/sessionctl.py handoff --spawn {pkg}"),
            handback_text=("## 做了什麼\npark 到點時偵測到同專案另一個 session 在動，延後後終局 skip。\n\n"
                           f"## 驗了什麼\nother_sid={other['sid']}、other_at={other['at']}、延後 {done} 次。\n\n"
                           f"## 卡在哪\n交接包 {pkg} 無人接。\n\n## 下一步指令\n"
                           f"`python tools/sessionctl.py handoff --spawn {pkg}`，或 `claude -r {sid}`。\n"))
        return rc
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
