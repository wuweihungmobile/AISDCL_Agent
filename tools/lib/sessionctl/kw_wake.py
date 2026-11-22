"""主載具叫醒判準（R218 Q2；DES §5.2、§5.4、§5.5、§8、S-13／S-19／S-23／S-24／S-25）。

`keepwarm.run`（`kw_run`）與 `watch.run` 共用同一份：計畫（`begin`）、下一個叫醒時刻
（`next_due`）、叫醒當下的判決（`at_due`）、defer 期間的提前重置輪詢（`poll_early`）、ping 實測 Δ
（`ping_cost`）。零 token；時鐘、讀數、補量全由參數注入。

每個叫醒時刻的次序（S-23⑤、S-13）：先 `seal.handed_over`（已交棒 ⇒ `handed_over`、不 ping、不記
續跑）→ 補量讀短窗 → 牆內不結束（延到 reset＋s，`defer`）→ 提前重置（S-19，`early`）→ 到目標
（`resume`）或 `ping`。chain／single 只看**未來** k（S-24：保溫帳歷史是沉沒成本）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from . import qw_calc, qw_plan, qw_schema, seal, switch

HARD_SKIPS = ("unattended", "mode", "off", "handed_over")
EV_DEFER, EV_EARLY_RESET = "keepwarm_defer", "keepwarm_early_reset"
EV_PING_COST = "keepwarm_ping_cost"


class Outcome(NamedTuple):
    """kind：`handed_over`｜`defer`｜`wait`｜`early`｜`resume`｜`ping`。"""

    kind: str
    detail: str = ""
    plan: object = None


@dataclass
class Carrier:
    """一個主載具行程（keepwarm 或 watch 持錨者）的計畫狀態。"""

    sid: str
    transcript: object
    env: object
    t_kw: float
    idle: float
    read_quota: object = None
    refresh: object = None
    soft: str = ""                      # `no_usage`／`small_ctx`：付不起 ping，仍單跳到目標
    anchor_fn: object = None            # 錨點讀取縫（watch 注入）；缺＝讀 keepwarm.anchor
    target: float | None = None
    source: str = "none"
    ref: tuple = (None, None, None)     # (ref_reset, ref_pct, ref_at)；ref_reset 空＝S-19 不適用
    plan: object = None
    deferred: bool = False

    @property
    def early(self) -> bool:
        return self.ref[0] is not None

    @property
    def periodic(self) -> bool:
        return self.target is None


def dt_of(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch).astimezone()


def _anchor(c: Carrier):
    if c.anchor_fn is not None:
        return c.anchor_fn()
    from . import keepwarm  # noqa: PLC0415 — keepwarm 的 run 委派本檔，頂層 import 會成環

    return keepwarm.anchor(c.transcript)


def _measure(c: Carrier, now: float):
    """補量讀短窗後的 `Plan`（S-23：陳舊先補量一次）；記在 `c.plan`。"""
    c.plan = qw_plan.plan(c.sid, c.transcript, c.env, dt_of(now), read_quota=c.read_quota,
                          refresh=c.refresh)
    return c.plan


def begin(sid, transcript, env, now: float, t_kw: float, idle: float, *, soft: str = "",
          read_quota=None, refresh=None, anchor_fn=None) -> Carrier:
    """啟動時讀一次 `plan` 與 `wake_target`（DES §5.2）。"""
    c = Carrier(sid, transcript, env, t_kw, idle, read_quota, refresh, soft, anchor_fn)
    p = _measure(c, now)
    c.target, c.source, c.ref = qw_plan.wake_target(sid, transcript, env, dt_of(now), plan_=p)
    return c


def _pct(p) -> float | None:
    return None if p is None or p.r is None else 100.0 - p.r


def kind_of(c: Carrier, anchor) -> tuple[str, int, bool]:
    """`(mode, k, 付得起)`：periodic（無目標）｜chain（付得起且 k>0）｜single（零付費一跳）。"""
    if c.target is None:
        return "periodic", 0, False
    p = c.plan
    if anchor is None or p is None or p.r is None or c.soft:
        return "single", 0, False
    k = qw_calc.k_of((c.target - anchor) / 60 - qw_calc.skew_min(), p.ctx, c.env,
                     t_kw_min=c.t_kw, idle=c.idle)
    ok = qw_calc.affordable(p.r, k, p.ping_pp, p.ctx)
    return ("chain" if ok and k > 0 else "single"), k, ok


def next_due(c: Carrier) -> float | None:
    """下一個叫醒時刻（epoch）：periodic＝錨點＋T_kw；chain／single＝排程序列的第一個（最後一個
    恆為目標）。錨點每輪重讀：主控有新記錄 ⇒ 錨點後移、重算。量不到錨點且無目標 ⇒ None。"""
    anchor = _anchor(c)
    if c.target is None:
        return None if anchor is None else anchor + c.t_kw * 60
    if anchor is None:
        return c.target
    mode, k, ok = kind_of(c, anchor)
    seq = qw_calc.schedule(anchor, c.target, k, ok and mode == "chain", c.t_kw,
                           qw_calc.skew_min(), c.idle)
    return seq[0]


def plan_fields(c: Carrier, due: float | None) -> dict:
    """`KEEPWARM_PLAN` 與 holder 列要寫的值：`wake_at`＝目標（chain／single）或下一個 ping
    （periodic）。"""
    anchor = _anchor(c)
    mode, k, _ = kind_of(c, anchor)
    wake = c.target if c.target is not None else due
    return {"mode": mode, "k": k, "when": wake, "source": c.source,
            "early": "on" if c.early else "off"}


def holder_extra(c: Carrier, due: float | None) -> dict | None:
    f = plan_fields(c, due)
    return None if f["when"] is None else qw_schema.holder_extra(
        f["when"], f["mode"], f["source"])


def _same_window(ref_reset: float, obs_reset: float) -> bool:
    return abs(obs_reset - ref_reset) <= qw_calc.LATCH_RESET_TOL_MIN * 60


def _check_early(c: Carrier, now: float) -> bool:
    """S-19／S-23⑥：以本次讀數判提前重置；順手把同窗較高讀數併進參照。"""
    p = c.plan
    pct = _pct(p)
    if not c.early or pct is None or p.reset is None:
        return False
    if qw_calc.early_reset(c.ref, p.reset, pct, p.reading_at):
        return True
    ref_reset, ref_pct, ref_at = c.ref
    if (_same_window(ref_reset, p.reset) and (p.reading_at is None or ref_at is None
                                              or p.reading_at >= ref_at)):
        c.ref = (ref_reset, max(ref_pct if ref_pct is not None else 0.0, pct),
                 max(filter(None, (ref_at, p.reading_at)), default=None))
    return False


def poll_early(c: Carrier, now: float) -> Outcome | None:
    """defer 期間每輪讀一次短窗（同一快取、不另付 token）判提前重置。"""
    if not c.early or not c.deferred:
        return None
    _measure(c, now)
    if _check_early(c, now):
        return Outcome("early", "提前重置：reset 晚於參照且讀數已降", c.plan)
    return None


def at_due(c: Carrier, now: float, due: float) -> Outcome:
    """叫醒當下的判決（見檔頭次序）。"""
    handed = seal.handed_over(c.sid, c.env)
    if handed is not None:
        return Outcome("handed_over", f"交接包已交棒（{handed}）")
    p = _measure(c, now)
    wall = p.wall if p.stage == qw_plan.WALL and p.wall else None
    if wall is not None:
        reset = wall.get("reset")
        if reset is None:
            return Outcome("wait", "牆內且 reset 不明（不猜時刻）", p)
        new = reset + qw_calc.skew_min() * 60
        if new > now:  # 牆內不結束：延到 reset＋s，不 ping、不記帳
            keep_ref = c.ref[0] is not None or c.source != "park"  # `park --at` 不適用 S-19
            c.target, c.source, c.deferred = new, "reset", True
            if keep_ref:
                c.ref = (reset, 100.0, p.reading_at)
            return Outcome("defer", f"牆內：延到 reset＋s（{qw_schema.iso(new)}）", p)
    # 「提前」＝早於目標：到了目標時刻才看到新窗是準時，不記 `keepwarm_early_reset`
    if (c.target is None or now < c.target - 1.0) and _check_early(c, now):
        return Outcome("early", "提前重置：reset 晚於參照且讀數已降", p)
    if c.target is not None and abs(due - c.target) < 1.0:
        return Outcome("resume", "到預定時刻", p)
    return Outcome("ping", "保溫點", p)


def ping_cost(sid: str, row: dict, p, now: float):
    """S-25：相鄰兩次 ping 叫醒的讀數差。回 `(last, costs, last_reset)` 供寫帳。Δ 只在上一筆存在、
    兩筆皆非 stale、同一視窗、Δ ≥ 0 時入 `ping_costs`；本次讀數 stale／量不到 ⇒ `last` 清空。"""
    costs, prev = list(row["costs"]), row["last"]
    pct = _pct(p)
    if p is None or pct is None or p.reset is None or p.stale:
        return None, costs, None
    if (prev is not None and row["last_reset"] is not None
            and _same_window(row["last_reset"], p.reset) and pct - prev[0] >= 0):
        delta = pct - prev[0]
        costs = qw_schema.append_cost(costs, delta)
        switch.trace(EV_PING_COST, sid=sid, delta=delta, pct=pct)
    return (pct, now), costs, p.reset
