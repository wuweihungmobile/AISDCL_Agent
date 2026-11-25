"""QuotaWall 判決：擋派、Stop 推回、牆中靜音（R218 Q1；DES §6、REQ-QW-10～16）。

本檔只回**判決值**（Stop 推回訊息／靜音分類；擋派分支已退役，QVD C2），不 import hook、
不擋任何東西；`converge`、兩支 hook 的接線在 Q4（守衛面，主控親套）。
任何例外 ⇒ 放行（`(0, "")`／`""`）＝fail-open。
`AUTOSDD_QUOTAWALL_OFF` 只關擋派與推回；牆中偵測、牆內延後、牆中靜音是正確性，不受影響。
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from . import holder, qw_calc, qw_latch, qw_plan, qw_schema, qw_wall, roster, switch

DISPATCH_TOOLS = ("Agent", "Task", "Workflow")
_STEPS = ("python tools/sessionctl.py handoff --build", "補完交接包主控層",
          "python tools/sessionctl.py handoff --finalize <包>", "python tools/sessionctl.py park")
_KEEPWARM = "python tools/sessionctl.py keepwarm --sid <sid>（run_in_background、輸出導檔）"


def _off(env) -> bool:
    return bool(env.get(qw_calc.OFF_ENV)) or bool(env.get(qw_plan.UNATTENDED_ENV)) \
        or switch.switch_mode(env) == "off"


def _facts(p: qw_plan.Plan) -> str:
    return (f"階段 {p.stage}｜短窗剩餘 R={p.r:.1f}pp、V={p.v:.2f}、L={p.limit:.2f}"
            f"｜距 reset D={p.d_min:.0f} 分"
            f"｜calibrated={'yes' if p.calibrated else 'no'}")


def snapshot(payload: dict, env, now: datetime, seams: dict | None = None):
    """當下判決快照（QVD §3.5 C2：本檔的提示與靜音一律以判決為準，不另讀計畫自判）。縫：
    `read_quota`（讀數）、`ledger`／`live_fn`（計畫其餘縫）；`refresh` 由同一份讀數代替。"""
    from . import ruling_io  # noqa: PLC0415 — lazy：ruling_io 依賴 qw_plan／keepwarm

    seams = seams or {}
    raw = payload.get("transcript_path") if isinstance(payload, dict) else None
    tx = Path(raw) if isinstance(raw, str) and raw.strip() else None
    extra = {k: seams[k] for k in ("ledger", "live_fn") if seams.get(k) is not None}
    return ruling_io.current(roster._payload_sid(payload), tx, env, now,
                             read_quota=seams.get("read_quota"), plan_seams=extra)


def pretool_verdict(payload: dict, env, now: datetime, **_seams) -> tuple[int, str]:
    """§6.1 擋派分支**退役**（QVD §3.5 C2）：判決第 3、4 列已涵蓋 stage close／wall／nodispatch，
    致動器只留派工閘（C1 `quota_gate(rule=…)`）一處，免得兩支 hook 各擋各的、訊息各說各的。
    保留簽名供既有接線呼叫；恆回 `(0, "")`。"""
    return 0, ""


def _has_park(sid: str, now: datetime) -> bool:
    from . import park  # noqa: PLC0415

    marker = park.read_marker(sid)
    return park.credential_ok(marker, now)[0] and qw_plan._pkg_live(marker)


def stop_verdict(payload: dict, env, now: datetime, *, inflight: bool, snap=None,
                 **seams) -> str:
    """§6.2：回 `decision:block` 的 reason；不推 ⇒ `""`。只在判決 `PARK` 且額度牆 `close` 時推
    （`WAIT_RESET` 由保溫閘推 keepwarm，不推收尾）；訊息附判決行：
    · 在飛側（`inflight`）：要求 TaskStop 全部在飛代理後結束回合（**不得**要求先封存，D-D）；
    · 閒置側：列出尚缺的步驟（build→主控層→finalize→park→keepwarm）；都有 ⇒ 不推；
    · 主載具在跑、只缺 park（S-18）：同一 (sid, 短窗視窗) 只推一次（閂鎖），其後交
      `absent_notice`。"""
    try:
        env = os.environ if env is None else env
        if (not isinstance(payload, dict) or payload.get("stop_hook_active") or _off(env)):
            return ""
        sid = roster._payload_sid(payload)
        snap = snap or snapshot(payload, env, now, seams)
        p, r = snap.plan, snap.ruling
        if r.action != "PARK" or p.stage != qw_plan.CLOSE:
            return ""
        head = f"額度牆（Stop）：{_facts(p)}\n{r.line()}\n"
        if inflight:
            return (head + "先 TaskStop 全部在飛代理（成品留在工作樹），"
                    "然後結束回合；下一次 Stop 會帶你走收尾。（只推這一次。）")
        park_ok, primary_ok = _has_park(sid, now), qw_latch.primary_live(payload, sid, now)
        if park_ok and primary_ok:
            return ""
        if primary_ok and qw_latch.latch_seen(sid, p.reset, 100 - p.r, now.timestamp(),
                                              p.reading_at):
            return ""
        todo = ([] if park_ok else list(_STEPS)) + ([] if primary_ok else [_KEEPWARM])
        if primary_ok:
            qw_latch.latch_mark(sid, p.reset, 100 - p.r, now.timestamp())
        return (head + "收尾還缺：" + " → ".join(todo)
                + "\n（交接包須先寫完主控層；park 只是備援，主載具是 keepwarm。只推這一次。）")
    except Exception:  # noqa: BLE001 — fail-open
        return ""


def absent_notice(payload: dict, env, now: datetime, *, snap=None, **seams) -> str:
    """S-18 閂鎖後的 `systemMessage`（不 block）：判決 `PARK`、主載具在跑、但沒登記 park 備援。"""
    try:
        env = os.environ if env is None else env
        sid = roster._payload_sid(payload)
        snap = snap or snapshot(payload, env, now, seams)
        if (snap.ruling.action != "PARK" or snap.plan.stage != qw_plan.CLOSE or _off(env)
                or _has_park(sid, now) or not qw_latch.primary_live(payload, sid, now)):
            return ""
        row = holder.read(sid)
        wake = qw_schema.holder_wake(row)
        when = qw_schema.iso(wake.wake_at) if wake and wake.wake_at else "?"
        switch.trace("quotawall_backup_absent", sid=sid, wake=when, vid=snap.ruling.vid)
        return (f"備援缺席：主載具在跑（預定 {when} 醒來）；未登記 park 備援，"
                "主載具失效時沒有第二道網。")
    except Exception:  # noqa: BLE001
        return ""


def stop_mute(payload: dict, env, now: datetime, **seams) -> str:
    """§6.4：`"wall"`（牆中：整體靜音，任何模式皆然——那是正確性）｜`"quota"`（判決
    NODISPATCH／WAIT_RESET／PARK：照 §6.2；`QUOTAWALL_OFF` 時不設；QVD C2 以判決為準）｜`""`。"""
    try:
        env = os.environ if env is None else env
        transcript = payload.get("transcript_path") if isinstance(payload, dict) else None
        if qw_wall.wall_state(transcript, now, read_quota=seams.get("read_quota"))["wall"]:
            return "wall"
        if _off(env):
            return ""
        action = snapshot(payload, env, now, seams).ruling.action
        return "quota" if action in ("NODISPATCH", "WAIT_RESET", "PARK") else ""
    except Exception:  # noqa: BLE001
        return ""
