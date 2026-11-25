"""watch 的額度牆與主載具接線（R218 Q2；DES §5.7、§6.5；REQ-QW-17／18／29）。

自 `watch.py` 抽出（LOC 分級；判準本體在 `kw_wake`／`qw_plan`，這裡只做 watch 專屬的接線）：
  · `PlanCache`：額度牆 `plan` 的節流讀取（每 `PLAN_EVERY_SECONDS` 一次；補量由 `qw_wall` 的
    S-23 年齡規則決定，零 token）。
  · `quota_keys`：額度事件的閂鎖鍵＝單一權威判決（QVD §3.5 C4：`(acct, ACTION, win)`，
    不另算第二套）；`quota_disposal`：處置依判決動作（一個動作一列）。
  · `WakeCtl`：watch 持有保溫錨時的叫醒控制——有目標（`wake_target`）時用同一份 `schedule`、
    牆內延後、`resume`、交棒重判（REQ-QW-29）；無目標時退回 R216 的 periodic（叫醒預算 cap／idle）。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import holder, keepwarm, kw_ledger, kw_run, kw_wake, qw_calc, qw_plan, roster, seal, switch

PLAN_EVERY_SECONDS = 120.0
_RANK = {"NODISPATCH": 1, "WAIT_RESET": 2, "PARK": 3, "HALT_WEEKLY": 4}
#: 觸發 watch 額度事件的判決動作（QVD §3.5 C4；CONTINUE 不觸發）。
EVENT_ACTIONS = tuple(_RANK)
RECOMPUTE = ("先 `python tools/sessionctl.py quota` 重算（判決過期一律重算，舊 vid 不據以行動），"
             "再依新 ACTION：")
CLOSE_STEPS = ("TaskStop 全部在飛代理（成品留工作樹）→ 封存（`handoff --finalize`）→ "
               "`sessionctl park` → 掛 `sessionctl keepwarm`（run_in_background）")
#: 處置表：一個判決動作一列（QVD C4；`WAIT_RESET` 列不含停工排程字樣，AC-QV-05b）。
QUOTA_DISPOSAL = {
    "NODISPATCH": RECOMPUTE + ("仍 NODISPATCH ⇒ 不再派新代理（派工閘會擋）；在飛代理照跑、主控"
                               "自己的工作照做；重掛同一條 watch（同窗同動作不會再觸發）"),
    "WAIT_RESET": RECOMPUTE + ("仍 WAIT_RESET ⇒ 短窗即將重置：不派新、在飛照跑；掛 `sessionctl "
                               "keepwarm`（run_in_background；判決來源 ruling_wait_reset 只單跳到"
                               "重置後叫醒、不付費）；重掛 watch"),
    "PARK": RECOMPUTE + f"仍 PARK ⇒ {CLOSE_STEPS}",
    "HALT_WEEKLY": RECOMPUTE + f"仍 HALT_WEEKLY ⇒ {CLOSE_STEPS}（週重置用 `park --at <週 reset>`）",
}


def quota_disposal(action: str) -> str | None:
    """依判決動作的處置；未知動作回 `None`＝沿用既有處置表。"""
    return QUOTA_DISPOSAL.get(action)


class PlanCache:
    """`plan_fn(now)` 的節流：同一 `every` 秒內回上次結果（`force` 重算）。"""

    def __init__(self, plan_fn, every: float = PLAN_EVERY_SECONDS) -> None:
        self.plan_fn, self.every, self.at, self.plan = plan_fn, every, None, None

    def get(self, now: float, *, force: bool = False):
        if force or self.plan is None or self.at is None or now - self.at >= self.every:
            self.plan, self.at = self.plan_fn(now), now
        return self.plan


def quota_keys(sid: str, transcript, env, now: float | None, plan=None,
               read_quota=None) -> list[tuple]:
    """額度事件閂鎖鍵（QVD §3.5 C4：**單一序列**，只由判決觸發）：
    `[(ACTION, reset 分鐘, acct, vid, expires_at, 判決行)]`，至多一把。只有
    `WAIT_RESET｜PARK｜HALT_WEEKLY｜NODISPATCH` 觸發；牆中（`wall`）不判；讀不到／例外 ⇒ `[]`。
    縫：`read_quota(now)` 換讀數（同一條派工閘管線組 cap）；缺＝`ruling_io.gather`。"""
    try:
        import quota_ruling as QR  # noqa: PLC0415

        from . import ruling_io  # noqa: PLC0415 — lazy：判決取數吃 quota 匯入鏈

        if plan is not None and plan.stage == qw_plan.WALL:
            return []
        when = datetime.fromtimestamp(now).astimezone() if now else datetime.now().astimezone()
        if read_quota is not None:
            import quota_gate  # noqa: PLC0415

            run_env = dict(quota_gate.policy_env())
            run_env.update(env or {})
            state = read_quota(when)
            dec = quota_gate.dispatch_decision(state, when, run_env, peek=True)
            r = ruling_io.compose(state, dec, when, sid=sid, transcript=transcript, env=run_env,
                                  plan=plan).ruling
        else:
            r = ruling_io.gather(sid, transcript, now=when).ruling
        if r.action not in EVENT_ACTIONS:
            return []
        at = QR._aware(r.wk if r.action == QR.HALT_WEEKLY else r.win)  # noqa: SLF001
        reset = at.replace(second=0, microsecond=0).isoformat() if at else "unknown"
        return [(r.action, reset, r.acct, r.vid, r.expires_at, QR.line(r))]
    except Exception:  # noqa: BLE001 — 額度快取讀不到不得讓監督崩潰
        return []


def norm_hits(hit) -> list[tuple]:
    """`quota_fn` 縫的回傳統一成 `[(ACTION, reset, acct, vid, expires_at, 判決行), …]`：`None`／
    假值＝無；`True`＝無鍵的 `NODISPATCH`；短元組補 `None`。"""
    if not hit:
        return []
    if hit is True:
        return [("NODISPATCH", "unknown", None, None, None, None)]
    rows = [hit] if isinstance(hit, tuple) else list(hit)
    return [tuple(r) + (None,) * (6 - len(r)) for r in rows]


def fire_hits(sid: str, hits: list[tuple], n: int | None) -> list[tuple]:
    """逐鍵過閂鎖（`keepwarm.quota_latch`，單一序列 `(acct, ACTION, win)`）；回「該觸發」的鍵。"""
    return [h for h in hits if keepwarm.quota_latch(sid, h[0], h[1], acct=h[2], n=n)]


def top_band(hits: list[tuple]) -> str:
    return max((h[0] for h in hits), key=lambda b: _RANK.get(b, 0))


def quota_detail(fired: list[tuple], plan=None) -> str:
    """事件文案＝判決行（單一序列：一個判決、一句話；QVD C4）。"""
    top = max(fired, key=lambda h: _RANK.get(h[0], 0))
    return top[5] or f"額度判決 {top[0]}"


def verdict_tail(fired: list[tuple]) -> str:
    """`WATCH_VERDICT=quota` 末行的附加欄：`action=<A> vid=<v> expires_at=<t>`。"""
    top = max(fired, key=lambda h: _RANK.get(h[0], 0))
    return f" action={top[0]} vid={top[3] or 'none'} expires_at={top[4] or 'none'}"

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
