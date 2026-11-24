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


def quota_keys(now: float | None, plan=None) -> list[tuple]:
    """額度事件閂鎖鍵 `[(帶級, reset 分鐘, 原始讀數 pct｜None), …]`，兩條序列各至多一把（r9 W11d）：
    ①原始讀數序列＝讀數 ≥ prepare 門檻（`park.prepare_hits`，讀到 halt 門檻為 `halt`、否則
    `prepare`，pct 帶最高讀數）；②計畫序列＝`plan.stage` 為 `nodispatch`／`close`（pct 為 `None`）。
    沒命中／讀不到／牆中（`wall` 不判事件）／任何例外 ⇒ `[]`。"""
    try:
        from . import park  # noqa: PLC0415 — lazy：park 吃 quota 模組，監督迴圈不該為此付匯入成本

        if plan is not None and plan.stage == qw_plan.WALL:
            return []
        when = datetime.fromtimestamp(now).astimezone() if now else datetime.now().astimezone()
        keys: list[tuple] = []
        policy = park._policy()
        hits = park.prepare_hits(park._pace_state(when), policy, when)
        if hits:
            top = max(a.pct for a in hits)
            at = park.reset_of(hits)
            keys.append(("halt" if top >= policy.halt_pct else "prepare",
                         at.astimezone().replace(second=0, microsecond=0).isoformat() if at
                         else "unknown", top))
        if plan is not None and plan.stage in ("nodispatch", "close"):
            keys.append((plan.stage, kw_wake.dt_of(plan.reset).replace(
                second=0, microsecond=0).isoformat() if plan.reset is not None else "unknown",
                None))
        return keys
    except Exception:  # noqa: BLE001 — 額度快取讀不到不得讓監督崩潰
        return []


def norm_hits(hit) -> list[tuple]:
    """`quota_fn` 縫的回傳統一成 `[(帶級, reset, pct｜None), …]`：`None`／假值＝無；`True`＝無鍵的
    `prepare`；二元組（舊縫）補 `pct=None`；list／tuple 的 list＝多把鍵。"""
    if not hit:
        return []
    if hit is True:
        return [("prepare", "unknown", None)]
    rows = [hit] if isinstance(hit, tuple) else list(hit)
    return [tuple(r) + (None,) * (3 - len(r)) for r in rows]


def fire_hits(sid: str, hits: list[tuple], n: int | None) -> list[tuple]:
    """逐鍵過閂鎖（`keepwarm.quota_latch`，序列各自閂鎖）；回「該觸發」的鍵。`n`＝在飛代理數，只有
    計畫序列（stage ≥ nodispatch 才有鍵）用它做新派工重判。"""
    return [h for h in hits if keepwarm.quota_latch(sid, h[0], h[1], n=n)]


def top_band(hits: list[tuple]) -> str:
    return max((h[0] for h in hits), key=lambda b: _RANK.get(b, 0))


def quota_detail(fired: list[tuple], plan=None) -> str:
    """事件文案依來源分開（REQ-QW-77）：原始讀數序列觸發才寫「短窗原始讀數…已達」；計畫序列觸發寫
    「額度牆判 …（R／L／ping_pp 來源）」；兩條同時成立兩句並陳。"""
    parts = []
    for band, _reset, pct in fired:
        if keepwarm.SERIES.get(band) == "raw":
            head = (f"短窗原始讀數 {pct:.0f}% 已達" if isinstance(pct, (int, float))
                    else "短窗額度原始讀數已達")
            parts.append(f"{head} {band} 門檻（reset 在未來）")
        else:
            facts = ""
            if plan is not None and plan.stage == band and plan.r is not None \
                    and plan.limit is not None:
                facts = f"（R={plan.r:.1f}pp、L={plan.limit:.2f}；ping_pp 來源={plan.ping_pp_src}"
                facts += f"；在飛 N={plan.n_live}）" if plan.n_live is not None else "）"
            parts.append(f"額度牆判 {band}{facts}")
    return "；".join(parts) or "額度事件成立（短窗額度）"


def due_merge(sid: str, transcript, agents: list, env, verdict, family: tuple):
    """`switch_due`（DES §7.4；REQ-CTL-24）：回 `(有效 pending｜None, 合併後判決)`。代理全數交卷且有
    有效硬線 pending ⇒ `("switch_due", 明細)`（只勝過「沒事」與保溫族）；否則判決逐字不變。
    惰性建立 pending 也在這裡（watch 輪詢是 `ensure_pending` 的呼叫點之一）。"""
    from . import switchfacts, switchplan  # noqa: PLC0415 — lazy：switchfacts 吃 park／quota 匯入鏈

    pend, due = switchfacts.watch_state(sid, transcript, len(agents), env)
    return pend, switchplan.merge(verdict, due, family)


def due_suffix(sid: str, event: str, pend, agents: list) -> str:
    """處置字尾：`switch_due` 落 `pending_switch_due` 痕跡；待換已逾 `DRAIN_MAX_MIN` 仍有在飛代理 ⇒
    任一判決加一行提示（只改文字）。"""
    from . import switchplan  # noqa: PLC0415 — lazy：同上

    return switchplan.on_verdict(sid, event, pend, len(agents))


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
