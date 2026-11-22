"""watch 的額度牆與主載具接線（R218 Q2；DES §5.7、§6.5；REQ-QW-17／18／29）。

自 `watch.py` 抽出（LOC 分級；判準本體在 `kw_wake`／`qw_plan`，這裡只做 watch 專屬的接線）：
  · `PlanCache`：額度牆 `plan` 的節流讀取（每 `PLAN_EVERY_SECONDS` 一次；補量由 `qw_wall` 的
    S-23 年齡規則決定，零 token）。
  · `quota_key`：額度事件的閂鎖鍵，帶級四級 prepare＜nodispatch＜close＜halt（階段來自 `plan`，
    不另算第二套）；`quota_disposal`：處置依階段（nodispatch／close 不再出現「快完成 ⇒ 重掛」）。
  · `WakeCtl`：watch 持有保溫錨時的叫醒控制——有目標（`wake_target`）時用同一份 `schedule`、
    牆內延後、`resume`、交棒重判（REQ-QW-29）；無目標時退回 R216 的 periodic（叫醒預算 cap／idle）。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import holder, keepwarm, kw_ledger, kw_run, kw_wake, qw_calc, qw_plan, roster, seal, switch

PLAN_EVERY_SECONDS = 120.0
_RANK = {"prepare": 1, "nodispatch": 2, "close": 3, "halt": 4}
CLOSE_STEPS = ("TaskStop 全部在飛代理（成品留工作樹）→ 封存（`handoff --finalize`）→ "
               "`park` → 掛 `sessionctl keepwarm`（run_in_background）")
QUOTA_DISPOSAL = {
    "nodispatch": "已進擋派區：不再派新代理（PreToolUse 會擋）；在飛代理照跑、主控自己的工作照做；"
                  "重掛同一條 watch（同一 reset 窗同一帶不會再觸發）",
    "close": f"已進收尾區：{CLOSE_STEPS}",
    "halt": f"額度已到停止線：{CLOSE_STEPS}",
}


def quota_disposal(band: str) -> str | None:
    """依階段的處置；`prepare`（或未知帶級）回 `None`＝沿用既有處置表。"""
    return QUOTA_DISPOSAL.get(band)


class PlanCache:
    """`plan_fn(now)` 的節流：同一 `every` 秒內回上次結果（`force` 重算）。"""

    def __init__(self, plan_fn, every: float = PLAN_EVERY_SECONDS) -> None:
        self.plan_fn, self.every, self.at, self.plan = plan_fn, every, None, None

    def get(self, now: float, *, force: bool = False):
        if force or self.plan is None or self.at is None or now - self.at >= self.every:
            self.plan, self.at = self.plan_fn(now), now
        return self.plan


def quota_key(now: float | None, plan=None) -> tuple[str, str] | None:
    """額度事件閂鎖鍵 `(帶級, reset 分鐘)`。候選＝①原始讀數 ≥ prepare 門檻（`park.prepare_hits`，
    讀到 halt 門檻為 `halt`、否則 `prepare`）；②`plan.stage` 為 `nodispatch`／`close`。
    取級別最高者；沒命中／讀不到／牆中（`wall` 不判事件）／任何例外 ⇒ `None`。"""
    try:
        from . import park  # noqa: PLC0415 — lazy：park 吃 quota 模組，監督迴圈不該為此付匯入成本

        when = datetime.fromtimestamp(now).astimezone() if now else datetime.now().astimezone()
        band, reset = None, None
        policy = park._policy()
        hits = park.prepare_hits(park._pace_state(when), policy, when)
        if hits:
            band = "halt" if max(a.pct for a in hits) >= policy.halt_pct else "prepare"
            at = park.reset_of(hits)
            reset = (at.astimezone().replace(second=0, microsecond=0).isoformat()
                     if at else "unknown")
        if plan is not None and plan.stage == qw_plan.WALL:
            return None
        if plan is not None and plan.stage in ("nodispatch", "close") and (
                band is None or _RANK[plan.stage] > _RANK[band]):
            band = plan.stage
            if plan.reset is not None:
                reset = kw_wake.dt_of(plan.reset).replace(second=0, microsecond=0).isoformat()
        return None if band is None else (band, reset or "unknown")
    except Exception:  # noqa: BLE001 — 額度快取讀不到不得讓監督崩潰
        return None


class WakeCtl:
    """watch 持有保溫錨時的叫醒控制（見檔頭）。`start` 在取得保溫錨後呼叫一次。"""

    def __init__(self, sid, transcript_fn, env, cfg, budget, anchor_fn, *, read_quota=None,
                 refresh=None) -> None:
        self.sid, self.transcript_fn, self.env, self.cfg = sid, transcript_fn, env, cfg
        self.budget, self.anchor_fn = budget, anchor_fn
        self.read_quota, self.refresh = read_quota, refresh
        self.car, self.pid = None, 0

    def start(self, now: float, pid: int) -> None:
        self.pid = pid
        tx, soft = self.transcript_fn(), "no_usage"
        try:  # 與 `keepwarm.skip_reason` 同一判準：量不到／太小只讓它不付費 ping（仍單跳到目標）
            ctx = roster._scan(Path(tx), False)["ctx_tokens"] if tx is not None else None
            if ctx is not None:
                small = ctx < switch.threshold(keepwarm.MIN_CTX_KEY, self.env)[0]
                soft = "small_ctx" if small else ""
        except Exception:  # noqa: BLE001
            pass
        self.car = kw_wake.begin(self.sid, tx, self.env, now, self.cfg.keepwarm_min,
                                 qw_calc.IDLE_LIMIT_MIN, soft=soft, read_quota=self.read_quota,
                                 refresh=self.refresh, anchor_fn=self.anchor_fn)
        self._publish()

    def _publish(self) -> None:
        """有目標時把主載具計畫寫進 holder 列（`wake_at`／`mode`／`target_source`，S-12）。"""
        if self.targeted():
            extra = kw_wake.holder_extra(self.car, self.due())
            if extra is not None:
                holder.acquire(self.sid, self.pid, extra=extra)

    def targeted(self) -> bool:
        return self.car is not None and not self.car.periodic

    def due(self) -> float | None:
        """有目標時的下一個叫醒時刻（排程序列第一個）；無目標 ⇒ `None`（照 R216：錨點＋T_kw）。"""
        return kw_wake.next_due(self.car) if self.targeted() else None

    def classify(self, now: float, state: dict, budget_kind) -> str | None:
        """`decide` 的 `kw_verdict`：回 `keepwarm`｜`cap`｜`idle`｜`resume`｜`handed_over`；
        牆內延後／牆中 reset 不明 ⇒ `None`（本輪不判）。`budget_kind()`＝叫醒預算判決（R216：
        `keepwarm`／`cap`／`idle`，依錨點快取）；有目標時 `cap` 不適用（只屬於 periodic）。"""
        if self.targeted():
            oc = kw_wake.at_due(self.car, now, self.due() or now)
            state["oc"] = oc
            if oc.kind in ("defer", "wait"):
                if oc.kind == "defer":
                    self._publish()
                return None
            if oc.kind in ("handed_over", "early", "resume"):
                return "handed_over" if oc.kind == "handed_over" else "resume"
            kind = budget_kind()
            return "keepwarm" if kind == "cap" else kind
        if seal.handed_over(self.sid, self.env) is not None:
            return "handed_over"
        return budget_kind()

    def settle(self, event: str, now: float, state: dict) -> str:
        """判決成立後的帳務；回最終事件名（記帳失敗 ⇒ `cap`，失效往少花走）。"""
        if event == "resume":
            ctx = int(state.get("ctx") or 0)
            kw_ledger.clear(self.sid, self.transcript_fn(), ctx, keepwarm.n_star(ctx))
            kw_run.mark_resumed_if_owner(self.sid, self.env)
            return event
        if event != "keepwarm":
            return event
        plan = kw_wake._measure(self.car, now) if self.car is not None else None
        if isinstance(self.budget, keepwarm.WakeBudget):
            ok = self.budget.charge(state["pings"], state["ctx"], state["star"], plan=plan, now=now)
        else:
            ok = self.budget.charge(state["pings"], state["ctx"], state["star"])
        return "keepwarm" if ok else "cap"

    def trace_early(self, now: float, state: dict) -> None:
        oc = state.get("oc")
        if oc is not None and oc.kind == "early":
            switch.trace(kw_wake.EV_EARLY_RESET, sid=self.sid,
                         reset=getattr(oc.plan, "reset", None))
