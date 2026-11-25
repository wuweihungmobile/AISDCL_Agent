"""QuotaWall 計畫：`plan`、`plan_lines`、`wake_target`（R218 Q1；DES §3～§4）。

`plan` 只看**短窗軸**（`park.short_axes`／伺服器原值）；不讀 `quota_policy.decide` 的 band、配速床、
趕工戳記。階段依序：`none`（量不到／reset 不明／舊窗讀數／模式非 auto 且非 notify／無人窗口）→
`wall` → `close`（R ≤ V）→ `nodispatch`（R ≤ L）→ `free`。任何例外 ⇒ `none`（fail-open）。
本檔不擋、不推、不寫檔（痕跡除外）；擋與推在 `qw_verdict`，接線在 Q4。
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import procstop, qw_calc, qw_schema, qw_wall, roster, switch

NONE, WALL, CLOSE, NODISPATCH, FREE = "none", "wall", "close", "nodispatch", "free"
STAGES = (NONE, WALL, CLOSE, NODISPATCH, FREE)
UNATTENDED_ENV = "AUTOSDD_UNATTENDED"


@dataclass(frozen=True)
class Plan:
    stage: str
    reason: str = ""
    d_min: float | None = None       # D：到 reset 的分鐘
    k: int = 0
    v: float | None = None
    limit: float | None = None       # L
    r: float | None = None           # R（stale 時為外推後的 R_eff）
    reset: float | None = None       # 短窗 reset（epoch；觀測值）
    ctx: int | None = None
    calibrated: bool = False         # ping_pp 鍵是否已校準
    cal_burn: bool = False
    cal_agent: bool = False
    invariant: str = "ok"
    reading_at: float | None = None
    reading_age: int | None = None
    stale: bool = False
    ping_pp: float | None = None     # ping_pp_eff（S-25）
    ping_pp_src: str = "scaled"
    wall: dict | None = None
    n_live: int | None = None        # N：在飛子代理＋背景 claude 行程；None＝量不到（算 0）


def _warn(msg: str) -> None:
    print(f"⚠️ {msg}", file=sys.stderr)


#: 行程列舉要起 powershell／ps（數百毫秒），hook 與 watch 每輪都會算 plan ⇒ 短期快取。
_PROC_TTL_SEC = 20.0
_proc_cache: list = [0.0, None]
_outlier_seen: set = set()


def _background_claude(sid: str) -> int | None:
    """背景真 `claude` 行程數（`claude -p` 形態、命令列不含本 sid；與互動視窗無關——額度是帳號
    共用，真機驗證／無人窗口燒的是同一池）。行程身分判準＝`procstop`；列舉失敗 ⇒ None。"""
    now = time.monotonic()
    if _proc_cache[1] is None or now - _proc_cache[0] > _PROC_TTL_SEC:
        _proc_cache[:] = [now, procstop.list_processes()]
    procs = _proc_cache[1]
    if procs is None:
        return None
    return sum(1 for p in procs if procstop.is_claude(p)
               and procstop._PRINT_RE.search(p["cmd"]) and sid not in p["cmd"])


def live_count(sid: str, transcript) -> tuple[int, bool]:
    """W11c①的 N：在飛背景子代理（`roster.running`，純讀檔）＋背景 claude 行程；不含主控與待派者。
    回 `(N, 量得到)`；任一半量不到 ⇒ 該半算 0 且第二值 False（PLAN 行標 `n_live=?`）。零 token。"""
    try:
        slug_dir = Path(transcript).parent if transcript is not None else None
        agents = len(roster.running(sid, projects_dir=slug_dir))
        procs = _background_claude(sid)
        return agents + (procs or 0), procs is not None
    except Exception:  # noqa: BLE001 — fail-open：量不到＝不加燒量（與 r8 公式同）
        return 0, False


def _ledger_row(sid: str) -> dict:
    """本 sid 保溫帳（讀實測 `ping_costs` 用；讀不到＝空）。"""
    try:
        from . import keepwarm  # noqa: PLC0415

        row = json.loads(keepwarm.ledger_path(sid).read_text(encoding="utf-8"))
        return row if isinstance(row, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _prepare_pct(env) -> float:
    try:
        import quota_policy  # noqa: PLC0415

        return float(quota_policy.load_policy(env)[0].prepare_pct)
    except Exception:  # noqa: BLE001
        return 85.0


def _ctx_of(transcript) -> int | None:
    if transcript is None or not Path(transcript).is_file():
        return None
    try:
        return roster._scan(Path(transcript), False)["ctx_tokens"]
    except Exception:  # noqa: BLE001
        return None


def _note_outlier(sid: str, costs, scaled: float) -> None:
    """乾淨樣本夠數卻整批離群 ⇒ 落 `ping_cost_outlier` 痕跡（同一批只落一次；plan 每輪重算）。"""
    key = (sid, tuple(costs))
    if key in _outlier_seen:
        return
    _outlier_seen.add(key)
    switch.trace("ping_cost_outlier", sid=sid, samples=list(costs), scaled=scaled,
                 x=qw_calc.OUTLIER_X)


def plan(sid: str, transcript, env, now: datetime, *, read_quota=None, refresh=None,
         ledger=None, live_fn=None) -> Plan:
    """見檔頭。縫：`read_quota(now)`、`refresh(now)`（補量一次）、`ledger`（保溫帳列，缺＝讀檔）、
    `live_fn(sid, transcript)->(N, 量得到)`（在飛單位數，缺＝`live_count`）。"""
    try:
        env = os.environ if env is None else env
        if env.get(UNATTENDED_ENV):
            return Plan(NONE, "unattended")
        if switch.switch_mode(env) not in ("auto", "notify"):
            return Plan(NONE, "mode_off")
        reading = qw_wall.fresh_reading(read_quota, refresh, now)
        if reading.state is None:
            switch.trace("quotawall_unmeasured", sid=sid, reason=reading.reason)
            wall = qw_wall.wall_state(transcript, now, read_quota=lambda _n: None)
            if wall["wall"]:  # 牆的①②只需要逐字稿；額度量不到不等於沒有牆
                return Plan(WALL, reading.reason or "unmeasured", wall=wall)
            return Plan(NONE, reading.reason or "unmeasured")
        _, live = qw_wall._classify(reading.state, now)
        pct = max(a.pct for a in live)
        reset = max(qw_wall._reset_epoch(a) for a in live)
        ctx = _ctx_of(transcript)
        cv = qw_calc.calibrated_value
        burn, cal_burn = cv(env, qw_calc.KEY_BURN, qw_calc.BURN_DEFAULT_PP_PER_MIN)
        agent, cal_agent = cv(env, qw_calc.KEY_AGENT, qw_calc.AGENT_EST_DEFAULT_PP)
        scaled, cal_pp = qw_calc.ping_pp(ctx, env)
        row = ledger if ledger is not None else _ledger_row(sid)
        costs = qw_schema.ping_costs(row)
        pp, src = qw_calc.ping_pp_eff(scaled, costs)
        if qw_calc.is_outlier(scaled, costs):
            _note_outlier(sid, costs, scaled)
        n_live, n_known = (live_fn or live_count)(sid, transcript)
        r = max(0.0, 100.0 - pct)
        age = None if reading.age is None else int(reading.age)
        if reading.stale:
            r = qw_wall.extrapolate(r, reading.age, burn)
        d_min = (reset - now.timestamp()) / 60.0
        k = qw_calc.k_of(d_min, ctx, env)
        v = qw_calc.v_of(k, pp, burn)
        limit = qw_calc.limit_of(v, agent, burn, n_live, d_min)
        invariant = "ok" if v < 100.0 - _prepare_pct(env) else "broken"
        if invariant == "broken":
            _warn(f"額度牆 invariant=broken：V={v:.2f} ≥ 100−準備門檻（k={k}、ping_pp={pp:.3f}）"
                  " ⇒ close 時讀數可能尚未進準備帶；判準照算")
        wall = qw_wall.wall_state(transcript, now, read_quota=lambda _n: reading.state)
        stage = (WALL if wall["wall"] else CLOSE if r <= v else NODISPATCH if r <= limit else FREE)
        return Plan(stage, "", d_min, k, v, limit, r, reset, ctx, cal_pp, cal_burn, cal_agent,
                    invariant, reading.reading_at, age, reading.stale, pp, src, wall,
                    n_live if n_known else None)
    except Exception as exc:  # noqa: BLE001 — fail-open：量不到＝不擋
        switch.trace("quotawall_unmeasured", sid=sid, reason=f"error:{type(exc).__name__}")
        return Plan(NONE, "error")


def _yn(flag: bool) -> str:
    return "yes" if flag else "no"


def plan_lines(p: Plan) -> list[str]:
    """人讀一行＋機器一行（末行 `QUOTAWALL_PLAN=stage=…`；watch／status／`quotawall` 動詞共用）。"""
    if p.stage == NONE:
        return [f"額度牆：量不到（{p.reason}）", f"QUOTAWALL_PLAN=stage=none reason={p.reason}"]
    stale = f"stale={_yn(p.stale)}" + (f" reading_age={p.reading_age}" if p.stale else "")
    human = (f"額度牆：{p.stage}｜R={p.r:.1f}pp V={p.v:.2f} L={p.limit:.2f}｜D={p.d_min:.0f} 分 "
             f"k={p.k}｜ping_pp={p.ping_pp:.3f}（{p.ping_pp_src}）")
    machine = (f"QUOTAWALL_PLAN=stage={p.stage} D={p.d_min:.0f} k={p.k} V={p.v:.2f} "
               f"L={p.limit:.2f} "
               f"R={p.r:.1f} ctx={p.ctx if p.ctx is not None else 'unknown'} "
               f"calibrated={_yn(p.calibrated)} burn_calibrated={_yn(p.cal_burn)} "
               f"agent_calibrated={_yn(p.cal_agent)} invariant={p.invariant} {stale} "
               f"ping_pp={p.ping_pp:.3f} ping_pp_src={p.ping_pp_src} "
               f"n_live={'?' if p.n_live is None else p.n_live}")
    return [human, machine]


def _pkg_live(marker) -> bool:
    """標記的交接包還是 live：檔在、無 `.resumed`、無 `.ack`（Q3 併進 credential_ok）。"""
    try:
        pkg = Path(marker["pkg"])
        return pkg.is_file() and not pkg.with_suffix(".resumed").exists() \
            and not pkg.with_suffix(".ack").exists()
    except (KeyError, TypeError, OSError):
        return False


def wake_target(sid: str, transcript, env, now: datetime, *, marker=None,
                plan_: Plan | None = None, ruling=None,
                **plan_seams) -> tuple[float | None, str, tuple]:
    """§3：回 `(epoch｜None, source∈{park,ruling_wait_reset,reset,none}, ref)`。優先序：本 sid park
    標記 armed 且其交接包 live ⇒ 標記 `primary_wake_at`；否則**判決 WAIT_RESET**（QVD §3.6；來源
    `ruling_wait_reset`：`win＋s`，只單跳不 ping）；否則 stage ∈ {close, wall} 且 reset 已知 ⇒
    reset＋s；否則無。`ref`＝`(ref_reset, ref_pct, ref_at)`（S-19／S-23⑥）：來源 reset／判決 ⇒ 該
    reset、當下讀數、讀數時刻；來源 park 且 `primary_source=reset` ⇒ `primary_wake_at−s`；
    `primary_source=at` 或無目標 ⇒ 全 None（S-19 不適用）。`ruling`＝已算好的判決（缺＝當下取）。"""
    from . import park  # noqa: PLC0415

    empty = (None, None, None)
    try:
        env = os.environ if env is None else env
        marker = park.read_marker(sid) if marker is None else marker
        p = plan_ or plan(sid, transcript, env, now, **plan_seams)
        pct = None if p.r is None else 100.0 - p.r
        if park.credential_ok(marker, now)[0] and _pkg_live(marker):
            prim = qw_schema.marker_primary(marker)
            if prim.wake_at is not None:
                ref = (prim.wake_at - qw_calc.skew_min() * 60, pct, p.reading_at) \
                    if prim.source == "reset" else empty
                return prim.wake_at, "park", ref
        win = _wait_reset_win(sid, transcript, env, now, ruling, p, plan_seams.get("read_quota"))
        if win is not None:
            return win + qw_calc.skew_min() * 60, "ruling_wait_reset", (win, pct, p.reading_at)
        if p.stage in (CLOSE, WALL) and p.reset is not None:
            return p.reset + qw_calc.skew_min() * 60, "reset", (p.reset, pct, p.reading_at)
    except Exception:  # noqa: BLE001
        pass
    return None, "none", empty


def _wait_reset_win(sid, transcript, env, now: datetime, ruling, p, read_quota) -> float | None:
    """判決為 `WAIT_RESET` 時的短窗 reset（epoch）；否則／取不到 ⇒ None（不擋其餘來源）。"""
    try:
        if ruling is None:
            from . import ruling_io  # noqa: PLC0415 — lazy：ruling_io 依賴本檔

            ruling = ruling_io.current(sid, transcript, env, now, read_quota=read_quota,
                                       plan=p).ruling
        if getattr(ruling, "action", None) != "WAIT_RESET" or not ruling.win:
            return None
        return datetime.fromisoformat(ruling.win).timestamp()
    except Exception:  # noqa: BLE001 — 判決取不到不得讓保溫崩潰
        return None

def trace_plan(sid: str, p: Plan, caller: str) -> None:
    """`quotawall_plan` 痕跡（`caller`＝呼叫端；一律只寫持久痕跡目錄）。"""
    try:
        switch.trace("quotawall_plan", sid=sid, caller=caller, stage=p.stage, reason=p.reason,
                     r=p.r, v=p.v, limit=p.limit, k=p.k, stale=p.stale)
    except OSError:
        pass


__all__ = ["Plan", "plan", "plan_lines", "wake_target", "trace_plan", "STAGES"]
