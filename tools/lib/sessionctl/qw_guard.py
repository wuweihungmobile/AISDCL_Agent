"""QuotaWall 守衛接線（R218 Q4／W11a；DES §6.2～§6.4、S-16、S-18；REQ-QW-12～16、43）。

判準核心在 `quotawall`（Q1，只回判決值）；本檔是 `converge`（sessionctl Stop）與
`check_pending_handoff`（兩支 hook 的跳板）要呼叫的**接線層**，hook 本身零判準：
  · `mute`            §6.4 牆中／準備帶靜音分類＋痕跡 `quotawall_stop_muted`；
  · `inflight`        §6.2 在飛側（close ⇒ TaskStop 全部在飛代理，不得要求先封存，D-D）；
  · `idle`            §6.2 閒置側＋S-16：free／nodispatch 不推 park、close 交 quotawall、
                      none 才走既有 `park.stop_verdict`，並對它套 S-18 閂鎖（主載具在跑只推一次）；
  · `primary_gate`    §6.3 主載具閘（armed park 卻沒有 running 的 keepwarm／watch）；
  · `stop_notice`     S-18 閂鎖之後的 `systemMessage`「備援缺席」（不 block）。
立案證據（QW DES §1 E9、S-18；2026-11-21～23 主控真機）：主載具 keepwarm 已掛著跨 reset，
每個保溫回合 Stop 仍被 `park.stop_verdict` 推回要求 `park`、被半路停工判準當成「沒有背景事件源」。
全部 fail-open（任何例外 ⇒ 不推）；`AUTOSDD_PARK_GUARD_OFF` 一併關閉額度類推回（它本來就是
「額度停工推回」的總開關），牆中靜音不受它影響（那是正確性）。
縫（測試用，皆缺省＝讀真實面）：`now`、`read_quota`、`refresh`、`ledger`、`live_fn`（W11c 在飛單位
數縫，不給就讀真行程表）、`carrier_fn`、`raw_env`。
"""
from __future__ import annotations

import os
from datetime import datetime

from . import (
    keepwarm,
    park,
    quotawall,
    qw_calc,
    qw_latch,
    qw_plan,
    qw_schema,
    qw_verdict,
    roster,
    seal,
    switch,
)

EV_MUTED = "quotawall_stop_muted"
EV_PRIMARY_GATE = "quotawall_primary_gate"
EV_BACKUP_ABSENT = "quotawall_backup_absent"
PLAN_SEAMS = ("read_quota", "refresh", "ledger", "live_fn")


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now().astimezone()


def plan_seams(seams: dict) -> dict:
    """只轉送 `quotawall.plan` 認得的縫（其餘如 `carrier_fn` 不外流）。"""
    return {k: seams[k] for k in PLAN_SEAMS if seams.get(k) is not None}


def pp_source(plan: qw_plan.Plan) -> str:
    """`ping_pp` 的來源三值（H.3 W11a）：已校準 `calibrated`、乾淨樣本合格的實測 `measured`、
    否則按上下文縮放 `scaled`。"""
    return "calibrated" if plan.calibrated else plan.ping_pp_src


def pretool(payload: dict, env=None, *, now: datetime | None = None, **seams) -> tuple[int, str]:
    """§6.1 PreToolUse 擋派**退役**（QVD §3.5 C2）：致動器只留派工閘（C1，依判決擋展開型派工）；
    保留簽名供既有 hook 接線呼叫，恆回 `(0, "")`。"""
    return 0, ""

def mute(payload: dict, env=None, *, now: datetime | None = None, **seams) -> str:
    """§6.4 `stop_mute`：`"wall"`｜`"quota"`｜`""`。牆中落痕跡 `quotawall_stop_muted`。"""
    env = os.environ if env is None else env
    try:
        kind = quotawall.stop_mute(payload, env, _now(now), **plan_seams(seams))
        if kind == "wall":
            switch.trace(EV_MUTED, sid=roster._payload_sid(payload))
        return kind
    except Exception:  # noqa: BLE001 — fail-open：量不到＝不靜音
        return ""


def _quota_on(env) -> bool:
    """額度類 Stop 推回的前提（同 `park.stop_verdict`：無人窗口、總開關、模式）。"""
    if env.get(park.UNATTENDED_ENV) or env.get(park.GUARD_OFF_ENV):
        return False
    return switch.switch_mode(env) == "auto"


def _carrier(carrier_fn=None) -> bool:
    """排程載具探測（唯一家＝`park._has_carrier`）：沒有載具＝park 步驟做不了，不推。"""
    return bool((carrier_fn or park._has_carrier)())  # noqa: SLF001


def _snap(payload: dict, env, now: datetime, seams: dict):
    """當下判決快照（QVD C2：判準只看判決）；`AUTOSDD_QUOTAWALL_OFF` ⇒ `None`（只關推回；牆中
    偵測與靜音不經這裡）。"""
    if env.get(qw_calc.OFF_ENV):
        return None
    return qw_verdict.snapshot(payload, env, now, seams)

def inflight(payload: dict, env=None, *, now: datetime | None = None, **seams) -> str:
    """§6.2 在飛側：`close` ⇒ 先 TaskStop 全部在飛代理再結束回合（訊息不含任何 finalize 字樣）。"""
    env = os.environ if env is None else env
    try:
        if not _quota_on(env) or not _carrier(seams.get("carrier_fn")):
            return ""
        return quotawall.stop_verdict(payload, env, _now(now), inflight=True, **plan_seams(seams))
    except Exception:  # noqa: BLE001
        return ""


def _park_facts(snap):
    """判決 `PARK｜HALT_WEEKLY` 的 S-18 閂鎖讀數面：`(reset epoch, 最高短窗讀數, 讀數時刻)`；
    判決不是停工或 reset 不明 ⇒ None（讀數取自同一份判決快照，不另取數）。"""
    r = getattr(snap, "ruling", None)
    if r is None or r.action not in ("PARK", "HALT_WEEKLY"):
        return None
    reset = qw_schema.parse_epoch(r.win if r.action == "PARK" else r.wk)
    if reset is None:
        return None
    hits = park.measured_short(snap.state, datetime.fromtimestamp(reset - 1).astimezone())
    return (reset, max((a.pct for a in hits), default=100.0),
            qw_schema.parse_epoch(getattr(snap.state, "measured_at", None)))

def _legacy(payload: dict, env, now: datetime, sid: str, seams: dict, snap) -> str:
    """非 close：`park.stop_verdict`（判決 PARK｜HALT_WEEKLY），主載具在跑時套 S-18 閂鎖。"""
    why = park.stop_verdict(payload, env, now=now, read_quota=seams.get("read_quota"),
                            carrier_fn=seams.get("carrier_fn"))
    if not why or not qw_latch.primary_live(payload, sid, now):
        return why
    facts = _park_facts(snap)
    if facts is None:
        return why
    reset, pct, at = facts
    if qw_latch.latch_seen(sid, reset, pct, now.timestamp(), at):
        return ""
    qw_latch.latch_mark(sid, reset, pct, now.timestamp())
    return why


def idle(payload: dict, env=None, *, now: datetime | None = None,
         **seams) -> tuple[str, bool]:
    """§6.2 閒置側＋S-16：回 `(reason, covers_keepwarm)`。`covers_keepwarm` 為真 ⇒ 呼叫端不再另加
    保溫閘文字（close 的推回已列出 keepwarm 步驟，或已確認主載具在跑）。"""
    env = os.environ if env is None else env
    try:
        if not _quota_on(env):
            return "", False
        now, sid = _now(now), roster._payload_sid(payload)
        snap = _snap(payload, env, now, seams)
        if snap is None or snap.plan.stage == qw_plan.WALL:
            return "", False  # 牆中靜音；QUOTAWALL_OFF
        if snap.ruling.action not in ("PARK", "HALT_WEEKLY"):
            return "", False  # S-16：額度照樣用到接近滿；WAIT_RESET 由保溫閘推 keepwarm
        if snap.plan.stage == qw_plan.CLOSE:
            if not _carrier(seams.get("carrier_fn")):
                return "", False
            return quotawall.stop_verdict(payload, env, now, inflight=False, snap=snap), True
        return _legacy(payload, env, now, sid, seams, snap), False
    except Exception:  # noqa: BLE001
        return "", False

def armed_h_marker(sid: str, now: datetime) -> dict | None:
    """本 sid 有效的 H 路 park 標記（armed、未過期、交接包仍 live）；`--done` 標記不算
    （沒有剩餘工作就不需要主載具）。"""
    marker = park.read_marker(sid)
    if marker is None or marker.get("route") != park.ROUTE_H:
        return None
    return marker if park.credential_ok(marker, now)[0] else None


def primary_gate(payload: dict, env=None, *, raw_env=None, now: datetime | None = None,
                 **_seams) -> str:
    """§6.3 主載具閘：armed H 標記 ∧ payload 有 `background_tasks` 且沒有 running 的
    keepwarm／watch shell ∧ 非「不掛的情形」前四項 ⇒ 推回一次。
    `off` 一項以 **hook 行程的原始環境**判（`raw_env`，缺省 `os.environ`）：OIR 讓路注入的
    `AUTOSDD_KEEPWARM_OFF` 不算（它屬保溫閘，主載具閘屬 park 憑證；QA2 P3-3、AT-QW-67）。"""
    env = os.environ if env is None else env
    raw = os.environ if raw_env is None else raw_env
    try:
        if payload.get("stop_hook_active") or roster._tasks(payload) is None:
            return ""
        if (env.get(park.UNATTENDED_ENV) or switch.switch_mode(env) != "auto"
                or raw.get(keepwarm.OFF_ENV)):
            return ""
        sid, now = roster._payload_sid(payload), _now(now)
        if not sid or qw_latch.running_supervision(payload) or seal.handed_over(sid, env):
            return ""
        marker = armed_h_marker(sid, now)
        if marker is None:
            return ""
        wake = qw_schema.marker_primary(marker).wake_at
        switch.trace(EV_PRIMARY_GATE, sid=sid, wake_at=wake)
        return ("主載具閘（Stop）：park 備援已登記，但本 session 沒有在跑的主載具"
                "（keepwarm／watch）。park 只是備援——排程器可能失敗（2026-11-20 22:42 事件）；"
                "主載具才是「這個視窗自己醒來續工」的那一條。\n"
                f"請現在掛上：{keepwarm.CMD} --sid {sid}（Bash／PowerShell 工具用 "
                "run_in_background、輸出導檔），並把背景任務 id 與輸出首行 "
                "`KEEPWARM_PLAN … wake_at=` 一併貼進回覆；宣稱「會自動繼續」時同時貼 park 的 "
                "`PARK_VERDICT … next_run=`（缺哪一份就照實寫缺席）。"
                "（只推回這一次；第二次 Stop 放行。）")
    except Exception:  # noqa: BLE001
        return ""


def stop_notice(payload: dict, env=None, *, now: datetime | None = None, **seams) -> str:
    """S-18：主載具在跑、沒有 park 備援，且已推過一次 ⇒ `systemMessage`「備援缺席」（不 block）。
    只在 Stop 沒有推回時由 hook 呼叫；`stop_hook_active` 的第二次 Stop 不再出聲。"""
    env = os.environ if env is None else env
    try:
        if payload.get("stop_hook_active") or not _quota_on(env):
            return ""
        now, sid = _now(now), roster._payload_sid(payload)
        snap = _snap(payload, env, now, seams)
        if snap is None or snap.ruling.action not in ("PARK", "HALT_WEEKLY"):
            return ""
        if snap.plan.stage == qw_plan.CLOSE:
            return quotawall.absent_notice(payload, env, now, snap=snap)
        if not qw_latch.primary_live(payload, sid, now):
            return ""
        marker = park.read_marker(sid)
        if park.credential_ok(marker, now)[0] or _park_facts(snap) is None:
            return ""
        switch.trace(EV_BACKUP_ABSENT, sid=sid, stage=snap.plan.stage, vid=snap.ruling.vid)
        return "備援缺席：主載具在跑；未登記 park 備援，主載具失效時沒有第二道網。"
    except Exception:  # noqa: BLE001
        return ""
