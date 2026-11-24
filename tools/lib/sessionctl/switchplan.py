"""自動換 session 的決策表（Control_Handover DES §7；REQ-CTL-22～30；W5）。

WHY：換不換 session 的判準原本散在三個閘（封存閘、park 停工閘、保溫閘）與轉送條件 10，沒有任何一處
能回答「此刻整體上該做什麼」，也就無從重放歷史、驗證新判準與舊行為的差異。本檔把它寫成**純函式**
`decide(Inputs) -> Decision`：自上而下第一個命中即回（G0、G1、W、D、H、F、F′、K、Z），輸入全是已有
真相源的量（`switchfacts` 負責讀），本檔不讀檔案系統以外的任何狀態、不 spawn、不呼叫 `handoff.spawn`
（hook 不代主控 finalize／spawn，TH-1）。

葉模組：只 import `switch`／`control`／`costmodel`（含門檻）與 `endurance_env`（痕跡目錄），
**不 import
`seal`／`handoff`／`watch`**——`handoff.advise_once` 要呼叫本檔的 `advise_hook`，反向會成環。
讀取事實（逐字稿、封存、包）的部分住 `switchfacts.py`。

模組常數集合**恰為** `{DEBOUNCE_MIN, DRAIN_MAX_MIN}`（AT-CTL-48）：沒有數值化的上下文門檻、
沒有軟線／
便宜線——硬線與 R2 只能取 `switch.threshold`，換新與否只能問 `costmodel`。要加常數先改 DES。
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import endurance_env

from . import control, costmodel, switch

DEBOUNCE_MIN = 30  # 接手後這麼久之內不連換（D 列；W 不受限、H 列受限）
DRAIN_MAX_MIN = 30  # 硬線待換標記存活超過這麼久、仍有在飛代理 ⇒ 升級提示（只改文字，不新增推回）


class Action:
    """動作值域（字串，JSON 友善）。"""

    STAY, SWITCH_NOW, SWITCH_AFTER_DRAIN = "STAY", "SWITCH_NOW", "SWITCH_AFTER_DRAIN"
    PARK_UNTIL, PARK_POLL = "PARK_UNTIL", "PARK_POLL"


@dataclass(frozen=True)
class Quota:
    """額度面的輸入（DES §7.1）。`stage` 是 QW 的階段字面（none／wall／close／nodispatch／free）；
    `credential`＝本 session 已有有效的續航憑證（`park.credential_ok`）；`wait_min`＝距目標 reset 的
    分鐘；`target_axis`＝short｜weekly｜at（`park --at`）。量不到的欄位保持 `None`，不猜。"""

    stage: str = "none"
    short_pct: float | None = None
    short_reset: str | None = None
    weekly_pct: float | None = None
    weekly_reset: str | None = None
    prepare_pct: float | None = None
    credential: bool = False
    stale: bool = False
    wait_min: float | None = None
    target_axis: str = "short"


@dataclass(frozen=True)
class Inputs:
    """十一項輸入（DES §7.1）。`hard`／`r2` 由呼叫端取自 `switch.threshold`，本檔不寫字面。"""

    ctx: int | None = None
    hard: int | None = None
    compactions: int = 0
    r2: int | None = None
    cache: str = "unknown"  # hot｜cold｜unknown
    account_changed: bool = False
    quota: Quota = field(default_factory=Quota)
    agents: int = 0
    supervision: str = "none"
    tree: str = "unknown"  # clean｜wip_tagged｜dirty｜unknown（只顯示，不參與判準）
    mode: str = "auto"
    unattended: bool = False
    since_takeover_min: float | None = None
    sealed: str = control.SEAL_NONE
    handed_over: bool = False
    pending_age_min: float | None = None  # 有效 pending 標記的年齡（分）；沒有 ⇒ None
    # K 列：主控閒置、無背景任務、非「不掛的情形」（keepwarm.skip_reason 為空）
    keepwarm_ok: bool = False
    env: object = None  # `costmodel` 的門檻注入縫


@dataclass(frozen=True)
class Flags:
    keepwarm: bool = False
    prefer_fresh: bool = False


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    flags: Flags = field(default_factory=Flags)
    carrier: str | None = None
    credential: str | None = None
    target: str | None = None  # PARK_*：目標 reset 的 ISO 字串


def _short_hit(q: Quota) -> bool:
    if q.stage in ("close", "wall"):
        return True
    return (q.short_pct is not None and q.prepare_pct is not None
            and q.short_pct >= q.prepare_pct and not q.credential)


def _wall(i: Inputs, flags: Flags, note: str) -> Decision | None:
    q = i.quota
    weekly = (q.target_axis != "short" and q.weekly_pct is not None and q.prepare_pct is not None
              and q.weekly_pct >= q.prepare_pct and not q.credential)
    if not (_short_hit(q) or weekly):
        return None
    long_wait = q.wait_min is not None and q.wait_min > 6 * 60  # D > 6 小時
    poll = q.target_axis != "short" or long_wait
    reason = ("wall" if q.stage in ("close", "wall") else "prepare_no_credential") + note
    if i.agents > 0:
        reason += "+taskstop_first"  # 先 TaskStop 在飛代理、重派資訊入交接包第 12 欄（QW D-D）
    target = q.weekly_reset if weekly and not _short_hit(q) else q.short_reset
    return Decision(Action.PARK_POLL if poll else Action.PARK_UNTIL, reason, flags,
                    "keepwarm+park", "QW 雙憑證（PARK_VERDICT=armed … next_run=）", target)


def decide(i: Inputs) -> Decision:
    """自上而下第一個命中即回（DES §7.2）。`ctx` 為 None ⇒ H、F 不成立（量不到偏續跑）。"""
    flags = Flags(prefer_fresh=bool(i.r2 and i.compactions >= i.r2))
    note = "(notify)" if i.mode == "notify" else ""  # 模式 notify：只出聲，推回判準不變
    if i.unattended or i.mode == "off":
        return Decision(Action.STAY, "gate", flags)
    if i.handed_over:
        return Decision(Action.STAY, "handed_over", flags, "forward.py", "forward_handed_over")
    if (wall := _wall(i, flags, note)) is not None:
        return wall
    if i.since_takeover_min is not None and i.since_takeover_min < DEBOUNCE_MIN:
        return Decision(Action.STAY, "debounce", flags, None, "switch_plan")
    if i.ctx is not None and i.hard is not None and i.ctx >= i.hard:
        if i.agents <= 0:
            return Decision(Action.SWITCH_NOW, "hard" + note, flags, "seal.stop_verdict",
                            ".sealed／spawn 痕跡")
        if i.pending_age_min is not None and i.pending_age_min > DRAIN_MAX_MIN:
            return Decision(Action.SWITCH_NOW, "drain_overdue+taskstop_first" + note, flags,
                            "seal.stop_verdict", "pending 標記檔")
        return Decision(Action.SWITCH_AFTER_DRAIN, "hard_drain" + note, flags,
                        "seal.stop_verdict＋watch switch_due", "pending 標記檔")
    cold = i.cache == "cold" or i.account_changed  # D-CT-8：換帳號只把快取視為已冷
    if cold and costmodel.fresh_is_cheaper(i.ctx, cold=True, env=i.env):
        if i.sealed == control.SEAL_EFFECTIVE:
            return Decision(Action.SWITCH_NOW, "cold_fresh" + note, flags, "forward.py",
                            "forward_spawned")
        return Decision(Action.STAY, "cold_unsealed", flags)  # F′：無載具（TH-5）
    if i.keepwarm_ok:
        return Decision(Action.STAY, "keepwarm", Flags(True, flags.prefer_fresh), "keepwarm",
                        "holder／KEEPWARM_PLAN")
    return Decision(Action.STAY, "ok", flags)


# ───────────────────────────────────────────────────────── pending_switch（DES §7.4）
def _now(now: datetime | None) -> datetime:
    return (now or datetime.now()).astimezone()


def pending_path(sid: str, base: Path | None = None) -> Path:
    return (base or endurance_env.trace_dir() / "switch") / f"{sid}.pending"


def _load(path: Path) -> dict | None:
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ok = isinstance(row, dict) and row.get("reason") == "hard" and row.get("since")
    return row if ok else None


def ensure_pending(sid: str, *, ctx: int | None, hard: int | None, agents: int,
                   now: datetime | None = None, base: Path | None = None) -> dict | None:
    """惰性冪等建立（D-CT-11）：`ctx ≥ hard ∧ 在飛代理 > 0 ∧ 無檔` 才寫
    `{reason:"hard", since, ctx}`；已有檔不覆寫 `since`（回現有內容）。不經 `advise_once`、
    不依賴 `.advised` 閂鎖。R2 永不寫 pending。"""
    path = pending_path(sid, base)
    if (have := _load(path)) is not None:
        return have
    if ctx is None or hard is None or ctx < hard or agents <= 0:
        return None
    row = {"reason": "hard", "since": _now(now).isoformat(), "ctx": ctx}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row), encoding="utf-8", newline="\n")
    except OSError:
        return None
    switch.trace(control.EV_PENDING_SET, sid=sid, ctx=ctx, hard=hard, agents=agents)
    return row


def read_pending(sid: str, *, ctx: int | None, hard: int | None, sealed: str, handed_over: bool,
                 base: Path | None = None) -> dict | None:
    """有效的 pending 標記，或 `None`。作廢條件：封存有效（`effective`）∨ 已交棒 ∨（`ctx` 量得到 ∧
    `ctx < hard`＝壓縮後）；`invalidated`／`none`／`unreadable` 與 `ctx` 量不到都**不作廢**。作廢＝
    刪檔＋落 `pending_switch_cleared`；作廢後 ctx 又回到 ≥ hard 時 `ensure_pending` 建新標記。"""
    path = pending_path(sid, base)
    row = _load(path)
    if row is None:
        return None
    why = ("sealed" if sealed == control.SEAL_EFFECTIVE else "handed_over" if handed_over
           else "compacted" if ctx is not None and hard is not None and ctx < hard else "")
    if not why:
        return row
    path.unlink(missing_ok=True)
    switch.trace(control.EV_PENDING_CLEARED, sid=sid, why=why)
    return None


def age_min(pending: dict | None, now: datetime | None = None) -> float | None:
    try:
        since = datetime.fromisoformat(str(pending["since"]))  # type: ignore[index]
    except (TypeError, KeyError, ValueError):
        return None
    return max(0.0, (_now(now) - since).total_seconds() / 60)


# ───────────────────────────────────────────────────────── watch 的三個提示掛點
def due_text(pending: dict | None, agents: int) -> str | None:
    """代理全數交卷且有有效 pending ⇒ `switch_due` 的明細；否則 `None`（既有判決不變）。"""
    if not pending or agents > 0:
        return None
    return (f"硬線待換標記（上下文 {pending.get('ctx')}，自 {pending.get('since')} 起）："
            "在飛代理已全數交卷")


def merge(verdict: tuple[str, str] | None, due: str | None,
          family: tuple) -> tuple[str, str] | None:
    """`watch` 的判決合併：`switch_due` 只勝過「沒事」與保溫族（純保溫，任何實質事件都比它重要）；
    額度／預算／停滯／逾時／已交棒等實質判決照舊優先。無 `due` ⇒ 原判決逐字不變。"""
    if due and (verdict is None or verdict[0] in family):
        return "switch_due", due
    return verdict


def on_verdict(sid: str, event: str, pending: dict | None, agents: int,
               now: datetime | None = None) -> str:
    """`watch` 印判決後呼叫：`switch_due` 落 `pending_switch_due` 痕跡；有在飛代理且待換已逾
    `DRAIN_MAX_MIN` ⇒ 回一行處置字尾（任一判決；只改文字，不新增推回、不新增判決）。"""
    if event == "switch_due":
        switch.trace(control.EV_PENDING_DUE, sid=sid, since=(pending or {}).get("since"))
    elif event == "duplicate":  # 入口判決（同 sid 已有活 watch）：另落 `watch_duplicate`
        switch.trace(control.EV_WATCH_DUPLICATE, sid=sid)
    age = age_min(pending, now) if agents > 0 else None
    if age is not None and age > DRAIN_MAX_MIN:
        return (f"待換已逾 {DRAIN_MAX_MIN} 分（{age:.0f} 分）：仍有在飛代理——先 TaskStop 它們、"
                "重派資訊入交接包第 12 欄，再 finalize→spawn（逾期只升級提示，不是新的推回）\n")
    return ""


# ───────────────────────────────────────────────────────── 痕跡
_HITS_CTX = re.compile(r"上下文\s*([\d,]+)")
_HITS_K = re.compile(r"壓縮\s*(\d+)\s*次")


def on_advise(sid: str, reason: str, ctx: int | None, k: int | None, mode: str) -> None:
    """`advise_once` 每次出聲落一列 `switch_advise`（REQ-CTL-29）；不寫 pending。"""
    switch.trace(control.EV_SWITCH_ADVISE, sid=sid, reason=reason, ctx=ctx, k=k, mode=mode)


def advise_hook(sid: str, hits: list[str], mode: str) -> None:
    """`handoff.advise_once` 的一行掛點：從命中理由文字取出原因／上下文／壓縮次數再落痕跡。"""
    text = "；".join(hits)
    got_ctx, got_k = _HITS_CTX.search(text), _HITS_K.search(text)
    reason = "+".join(n for n, hit in (("hard", "硬線" in text), ("r2", "R2" in text)) if hit)
    on_advise(sid, reason or "unknown", int(got_ctx.group(1).replace(",", "")) if got_ctx else None,
              int(got_k.group(1)) if got_k else None, mode)


def trace_plan(sid: str, d: Decision, base: Path | None = None) -> None:
    """`switch_plan`：只記非 STAY，與每 session 首次出現的 STAY 理由（`<sid>.plan_seen`）。"""
    seen_path = (base or endurance_env.trace_dir() / "switch") / f"{sid}.plan_seen"
    seen: list[str] = []
    if d.action == Action.STAY:
        try:
            seen = list(json.loads(seen_path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            seen = []
        if d.reason in seen:
            return
        try:
            seen_path.parent.mkdir(parents=True, exist_ok=True)
            seen_path.write_text(json.dumps([*seen, d.reason]), encoding="utf-8", newline="\n")
        except OSError:
            pass
    switch.trace(control.EV_SWITCH_PLAN, sid=sid,
                 **{k: v for k, v in asdict(d).items() if k != "flags"}, **asdict(d.flags))
