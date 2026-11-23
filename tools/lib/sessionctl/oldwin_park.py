"""park 到點「同 sid 續跑」前的舊視窗處置（DES §7.1「先關再開」；REQ-WP-54、57、88、98）。

`park_cli._cmd_fire` 在選到 `FIRE_RESUME`（`claude -r` 原 sid）之後、呼叫 `spawn_resume` 之前問
`resume_gate`；本檔把判準與重排放在這裡，是因為 `park_cli` 的行數貼著天花板。任何情形都不得讓同一個
sid 同時有兩個 claude 行程：
· 同 sid 有活著的 `entrypoint=sdk-cli` 行程 ⇒ 視同 `live_driver`，`skip`（不關也不開）。
· 否決（`留：`）⇒ `skip(kept_by_user)`，不 `claude -r`、不重排（掌舵者正在舊窗裡，舊窗本身就是
  駕駛），
  另寫 handback 說明。
· 有活著的互動舊窗 ⇒ 預設**不關**、回 `fork`（`claude -r <sid> --fork-session` 開新窗；舊窗保留）。
  只有呼叫端判主載具卡死、標記 `close_stuck_window` 為真（`stuck_close=True`）且 R217 五條件
  （`close_if_eligible(same_sid=True)`）全成立才關窗，關成功 ⇒ `go`（接普通 `-r`）；缺一仍 `fork`。
  WHY（2026-11-20 22:42）：舊設計「先關再開」遇映像改名即失敗且無備援，掌舵者斷線。
· 沒有任何活著的舊窗 ⇒ `go`（普通 `-r`）。
回 `{"act": "go"|"skip"|"fork", "reason": str}`；`_rearm` 供 §7.3 主載具讓路重排用。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from . import oldwin, park, procstop, se_gate


def _rearm(sid: str, pkg, when: float, env, now: datetime, S: dict,
           extra: dict | None = None) -> str:
    """把 park 到點排程重排到 `when`（新名字＝含新觸發分鐘）。回 `ok`｜`refused`（L1 拒絕，終局）｜
    `failed`（憑證取不到 ⇒ 舊排程保留）。`extra`＝併進標記的欄位（讓路重排的次數與新備援時刻）。"""
    import engine_resume_job as erj  # noqa: PLC0415

    from . import park_cli  # noqa: PLC0415 — lazy：park_cli 反向呼叫本檔

    marker = park.read_marker(sid)
    if marker is None or marker.get("status") != "armed":
        return "failed"
    fire = erj.fire_time(datetime.fromtimestamp(when).astimezone(), 0, now)
    reg = se_gate.register("oldwin_park._rearm", repo=park_cli._REPO, pkg=pkg, fire=fire, env=env,
                           sid=sid, claude=marker.get("claude"))
    if reg.rc:
        return "refused"  # L1 拒絕：呼叫端終局 refused（不重排、不進失敗鏈）
    label = park_cli.job_label(sid, fire)
    rc, cred = (S.get("arm") or erj.arm_oneshot)(
        label, park_cli.job_argv(label, sid, pkg, fire, reg.extra), str(park_cli._REPO), fire,
        interactive=True, **({"expire_at": reg.expire} if reg.expire else {}))
    if rc != 0 or not str(cred).strip():
        return "failed"
    job = {"label": label, "role": "primary", "fire_at": fire.isoformat(), "credential": str(cred)}
    ok, _msg = park.write_marker(dict(
        marker, fire_at=fire.isoformat(), jobs=[job],
        valid_until=(fire + timedelta(seconds=park.YIELD_GRACE_SECONDS)).isoformat(),
        **(extra or {})))
    return "ok" if ok else "failed"


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


def resume_gate(sid: str, pkg, env, now: datetime, S: dict | None = None,
                stuck_close: bool = False) -> dict:
    """見模組說明。`S`＝`park_cli` 測試縫字典（`oldwin`＝`close_if_eligible` 的 kwargs）。
    `stuck_close`＝呼叫端判主載具卡死且標記 `close_stuck_window` 為真（QW §7.4）；其餘一律不關。"""
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
    if not stuck_close:
        return {"act": "fork", "reason": "live_window_kept"}  # 預設不關：fork 新窗
    try:
        res = oldwin.close_if_eligible(sid, sid, pkg, same_sid=True, env=env, now=now,
                                       **(S.get("oldwin") or {}))
    except Exception as exc:  # noqa: BLE001 — 不確定舊窗是否還在 ⇒ 寧可 fork（新 sid，不會雙開同 sid）
        return {"act": "fork", "reason": f"oldwin_error:{type(exc).__name__}"}
    if res["closed"]:
        return {"act": "go", "reason": "closed_old_window"}
    if res["reason"] == "kept_by_user":
        return {"act": "skip", "reason": res["reason"]}
    return {"act": "fork", "reason": res["reason"]}  # 五條件缺一 ⇒ 不關、fork
