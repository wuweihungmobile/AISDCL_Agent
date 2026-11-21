"""park 到點「同 sid 續跑」前的舊視窗處置（DES §7.1「先關再開」；REQ-WP-54、57、88、98）。

`park_cli._cmd_fire` 在選到 `FIRE_RESUME`（`claude -r` 原 sid）之後、呼叫 `spawn_resume` 之前問
`resume_gate`；本檔把判準與重排放在這裡，是因為 `park_cli` 的行數貼著天花板。任何情形都不得讓同一個
sid 同時有兩個 claude 行程：
· 同 sid 有活著的 `entrypoint=sdk-cli` 行程 ⇒ 視同 `live_driver`，`skip`（不關也不開）。
· 否決（`留：`）⇒ `skip(kept_by_user)`，不 `claude -r`、不重排（掌舵者正在舊窗裡，舊窗本身就是
  駕駛），
  另寫 handback 說明。
· 有活著的互動舊窗 ⇒ `close_if_eligible(same_sid=True)`：關成功 ⇒ `go`；不成立 ⇒ 把 park 自己的
  到點排程重排到下一個觸發時刻（`retry`，一次重排算一次重試）；滿 3 次 ⇒ `fail`（呼叫端寫
  failed handback）。
· 沒有任何活著的舊窗 ⇒ `go`（原行為）。
回 `{"act": "go"|"skip"|"retry"|"fail", "reason": str}`。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from . import handoff, oldwin, park, procstop


def _rearm(sid: str, pkg, when: float, env, now: datetime, S: dict) -> bool:
    """把 park 到點排程重排到 `when`（新名字＝含新觸發分鐘；憑證取不到 ⇒ `False`、舊排程保留）。"""
    import engine_resume_job as erj  # noqa: PLC0415

    from . import park_cli  # noqa: PLC0415 — lazy：park_cli 反向呼叫本檔

    marker = park.read_marker(sid)
    if marker is None or marker.get("status") != "armed":
        return False
    fire = erj.fire_time(datetime.fromtimestamp(when).astimezone(), 0, now)
    label = park_cli.job_label(sid, fire)
    rc, cred = (S.get("arm") or erj.arm_oneshot)(
        label, park_cli.job_argv(label, sid, pkg, fire), str(park_cli._REPO), fire,
        interactive=True)
    if rc != 0 or not str(cred).strip():
        return False
    job = {"label": label, "role": "primary", "fire_at": fire.isoformat(), "credential": str(cred)}
    ok, _msg = park.write_marker(dict(
        marker, fire_at=fire.isoformat(), jobs=[job],
        valid_until=(fire + timedelta(seconds=park.YIELD_GRACE_SECONDS)).isoformat()))
    if ok:
        oldwin.note_retry(pkg, when, sid, sid, str(cred))
    return ok


def _handback(sid: str, pkg, text: str) -> None:
    import resume_route  # noqa: PLC0415

    try:
        path = resume_route.handback_report(f"{sid}_park_kept")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"## 做了什麼\npark 到點，{text}\n\n## 下一步指令\n"
                        f"`claude -r {sid}` 手動回舊 session，或 "
                        f"`python tools/sessionctl.py handoff --spawn {pkg}`。\n",
                        encoding="utf-8", newline="\n")
    except OSError:
        pass


def resume_gate(sid: str, pkg, env, now: datetime, S: dict | None = None) -> dict:
    """見模組說明。`S`＝`park_cli` 測試縫字典（`arm`；`oldwin`＝`close_if_eligible` 的 kwargs）。"""
    S = S or {}
    pkg = Path(pkg)
    wins = procstop.live_windows_of(sid, folder=S.get("sessions_dir"),
                                    created_of=S.get("created_of"))
    if any(w.get("entrypoint") == "sdk-cli" for w in wins):
        return {"act": "skip", "reason": "live_driver"}
    if oldwin.vetoed(pkg):
        _handback(sid, pkg, "舊窗已被掌舵者以「留：」保留，沒有 claude -r、也不重試。")
        return {"act": "skip", "reason": "kept_by_user"}
    if not any(w.get("entrypoint") == "cli" for w in wins):
        return {"act": "go", "reason": ""}
    try:
        res = oldwin.close_if_eligible(sid, sid, pkg, same_sid=True, env=env, now=now,
                                       **(S.get("oldwin") or {}))
    except Exception as exc:  # noqa: BLE001 — 不確定舊窗是否還在 ⇒ 寧可不開第二個同 sid 視窗
        return {"act": "fail", "reason": f"oldwin_error:{type(exc).__name__}"}
    if res["closed"]:
        return {"act": "go", "reason": "closed_old_window"}
    if res["reason"] in ("identity_unverified", "kept_by_user", "platform_not_windows"):
        return {"act": "skip", "reason": res["reason"]}  # 不關、不重試、只留痕
    if res["abandoned"] or res["retry_at"] is None or not _rearm(sid, pkg, res["retry_at"], env,
                                                                 handoff._aware(now), S):
        return {"act": "fail", "reason": f"oldwin_gave_up:{res['reason']}"}
    return {"act": "retry", "reason": res["reason"]}
