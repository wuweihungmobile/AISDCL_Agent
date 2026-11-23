"""QuotaWall 純算術：常數、k／V／L、ping_pp 縮放、affordable、schedule、early_reset（R218 Q1）。

只做算術、不讀額度、不讀檔。常數的**唯一真相源**取自既有模組（`keepwarm`／`quota_messages`／
`quota_gate`／`watch`），本檔在**呼叫時**以模組屬性讀（測試可替換；AT-QW-04）。`keepwarm` 在 Q2 起
會 import `quotawall` 門面，所以這裡對 `keepwarm` 一律函式內 lazy import（不是偷懶：反向依賴在 Q2
成立，頂層 import 會成環）。時間一律 epoch 秒（float），分鐘用 `*_min`／`d_min` 標示。
"""
from __future__ import annotations

import math
import sys

from . import qw_schema

# ── 程式常數（DES §4；其餘跨包欄名在 qw_schema）
IDLE_LIMIT_MIN = 50          # L_idle：最後一段閒置上限（＜55 harness 閒置壓縮＜60 快取）
W_CLOSE = 4                  # 收尾回合（封存＋park＋掛 keepwarm）的保溫等價次數
BACKUP_GRACE_MIN = 10        # park 備援到點＝主載具預定醒來＋此寬限
OBSERVE_SEC = 180            # 讓路觀察期
PING_PP_REF = 0.5            # 未校準的每次保溫 pp（c ≤ C_REF 時）
C_REF = 230_000              # PING_PP_REF 量測區間下緣（縮放基準）
MAC_HEARTBEAT_MIN = 10       # darwin keepwarm 心跳間隔
LATCH_RESET_TOL_MIN = 60     # S-18 閂鎖視窗：已過閂鎖 reset＋此分鐘必屬新窗
BURN_DEFAULT_PP_PER_MIN = 1.0
AGENT_EST_DEFAULT_PP = 5.0
T_OBS = 30                   # W11c①：在飛者燒量觀察窗（分鐘）；只准下修（過大＝大 D 恆 nodispatch）
MIN_CLEAN_SAMPLES = 3        # W11c③：量測值採用的乾淨樣本下限；只准上修
OUTLIER_X = 3                # W11c③：量測均值超過縮放／校準值×此倍數即整批離群；只准下修
KEY_PP = "AUTOSDD_QUOTAWALL_PP_PER_KUNIT"
KEY_BURN = "AUTOSDD_QUOTAWALL_BURN_PP_PER_MIN"
KEY_AGENT = "AUTOSDD_QUOTAWALL_AGENT_EST_PP"
OFF_ENV = "AUTOSDD_QUOTAWALL_OFF"  # 只關擋派與推回；牆中偵測／延後／靜音是正確性，不受影響


def _warn(msg: str) -> None:
    print(f"⚠️ {msg}", file=sys.stderr)


def _kw():
    from . import keepwarm  # noqa: PLC0415 — Q2 起 keepwarm import quotawall，頂層會成環

    return keepwarm


def p_of(ctx) -> float:
    """一次保溫的加權單位 `p(c)＝2·W_CR·c＋P_FIX`（`keepwarm` 同式）。"""
    kw = _kw()
    return 2 * kw.W_CR * max(int(ctx or 0), 0) + kw.P_FIX


def calibrated_value(env, key: str, default: float) -> tuple[float, bool]:
    """env 鍵值：空＝未校準（回預設）；非 >0 有限數＝視為未校準並出聲。"""
    raw = str(env.get(key) or "").strip()
    if not raw:
        return default, False
    try:
        val = float(raw)
    except ValueError:
        val = float("nan")
    if not (math.isfinite(val) and val > 0):
        _warn(f"{key}={raw!r} 不是 >0 的有限數 ⇒ 視為未校準，沿用預設 {default:g}")
        return default, False
    return val, True


def ping_pp(ctx, env) -> tuple[float, bool]:
    """未校準：`PING_PP_REF·max(1, p(c)/p(C_REF))`（S-3；c ≤ 23 萬恆 0.5，之上隨 p(c) 放大）；
    已校準：`p(c)/1000·鍵值`。回 `(pp, calibrated)`。"""
    base = PING_PP_REF * max(1.0, p_of(ctx) / p_of(C_REF))
    per_kunit, cal = calibrated_value(env, KEY_PP, math.nan)
    return (p_of(ctx) / 1000.0 * per_kunit, True) if cal else (base, False)


def qualified_mean(scaled: float, clean_costs) -> float | None:
    """W11c③：合格的量測均值；乾淨樣本不足 `MIN_CLEAN_SAMPLES`、或均值超過縮放×`OUTLIER_X`
    （整批離群）⇒ None。`clean_costs`＝`qw_schema.ping_costs` 的乾淨 pp 串。"""
    if len(list(clean_costs)) < MIN_CLEAN_SAMPLES:
        return None
    mean = qw_schema.measured_mean(clean_costs)
    return None if mean is None or mean > scaled * OUTLIER_X else mean


def is_outlier(scaled: float, clean_costs) -> bool:
    """乾淨樣本夠數、但均值超過縮放×`OUTLIER_X`（呼叫端落 `ping_cost_outlier` 痕跡）。"""
    if len(list(clean_costs)) < MIN_CLEAN_SAMPLES:
        return False
    mean = qw_schema.measured_mean(clean_costs)
    return mean is not None and mean > scaled * OUTLIER_X


def ping_pp_eff(scaled: float, clean_costs) -> tuple[float, str]:
    """S-25＋W11c③：`max(縮放／校準值, 合格量測均值)`，只抬不降（低於縮放值的量測不降估值）；
    無合格量測 ⇒ 縮放／校準值。回 `(值, "scaled"|"measured")`。"""
    mean = qualified_mean(scaled, clean_costs)
    if mean is not None and mean > scaled:
        return mean, "measured"
    return scaled, "scaled"


def limit_of(v: float, agent: float, burn: float, n_live: int, d_min: float) -> float:
    """W11c①：`L＝V＋AGENT_EST＋burn×N×min(D, T_OBS)`；N＝在飛單位數（不含主控與待派者），
    `N＝0` ⇒ 與 r8 的 `V＋AGENT_EST` 逐位相同。"""
    return v + agent + burn * max(int(n_live), 0) * min(max(d_min, 0.0), T_OBS)


def skew_min() -> float:
    import quota_messages  # noqa: PLC0415 — lazy

    return quota_messages.HALT_RESET_SKEW_SECONDS / 60.0


def detect_min() -> int:
    """`DETECT_MIN＝ceil((QUOTA_CACHE_TTL_SECONDS＋watch.POLL_SECONDS)/60)`（現查 180＋30 ⇒ 4）。"""
    import quota_gate  # noqa: PLC0415 — lazy

    from . import watch  # noqa: PLC0415

    return math.ceil((quota_gate.QUOTA_CACHE_TTL_SECONDS + watch.POLL_SECONDS) / 60)


def stale_age_seconds() -> float:
    """讀數年齡上限（S-23）：`TTL＋watch POLL`（現查 210 秒）；超過即補量。"""
    import quota_gate  # noqa: PLC0415

    from . import watch  # noqa: PLC0415

    return float(quota_gate.QUOTA_CACHE_TTL_SECONDS + watch.POLL_SECONDS)


def k_of(d_min: float, ctx, env, *, t_kw_min: float | None = None, idle: float = IDLE_LIMIT_MIN,
         s_min: float | None = None) -> int:
    """S-1：`k(D)＝max(0, ceil((D＋s−L_idle)/T_kw))`；上下文量不到或 < MIN_CTX ⇒ 0。"""
    kw = _kw()
    if ctx is None or ctx < kw.switch.threshold(kw.MIN_CTX_KEY, env)[0]:
        return 0
    t_kw = kw.t_kw_minutes(env) if t_kw_min is None else t_kw_min
    s = skew_min() if s_min is None else s_min
    return max(0, math.ceil((d_min + s - idle) / t_kw))


def v_of(k: int, pp: float, burn: float, detect: int | None = None) -> float:
    """`V(k)＝(k＋W_CLOSE)·ping_pp＋DETECT_MIN·burn`。"""
    return (k + W_CLOSE) * pp + (detect_min() if detect is None else detect) * burn


def affordable(r: float, k: int, pp: float, ctx) -> bool:
    """S-24：有目標時只算**未來** k 次——`R ≥ k·ping_pp_eff ∧ k ≤ n*(c)`；保溫帳歷史 pings 不進式子
    （目標已知時過去的 ping 是沉沒成本；`cap` 只屬於無目標的 `periodic`）。k＝0 恆真。"""
    return k <= 0 or (r >= k * pp and k <= _kw().n_star(ctx))


def choose_mode(target, can_afford: bool) -> str:
    """無目標 ⇒ periodic（R216 行為）；有目標 ∧ 付得起 ⇒ chain；否則 single（零付費、不得不掛）。"""
    return "periodic" if target is None else ("chain" if can_afford else "single")


def schedule(anchor: float, target: float | None, k: int | None, can_afford: bool,
             t_kw_min: float, s_min: float, idle: float = IDLE_LIMIT_MIN) -> list[float]:
    """叫醒時刻序列（epoch；keepwarm 與 watch 共用，DES §5.2）。
    · 無目標 ⇒ `[anchor＋T_kw]`（R216 的截止，到 n* 才 cap 由呼叫端判）；
    · 有目標 ∧ 付不起 ⇒ `[target]`（單跳）；
    · 有目標 ∧ 付得起 ⇒ k 個付費 ping＋末跳恰在 target：ping i 在 `anchor＋i·T_kw`，第 k 個若會越過
      「target−idle」之後則夾在 `target−idle`（使最後一段閒置恰 ≤ idle）；每段 ≤ max(T_kw, idle)。
    `target` 已含 s；`k` 為 None 時以 S-1 由 `(target−anchor)` 推回。"""
    if target is None:
        return [anchor + t_kw_min * 60]
    if not can_afford:
        return [target]
    if k is None:  # D＝到 reset 的分鐘；target＝reset＋s ⇒ D＝(target−anchor)/60−s
        d_min = (target - anchor) / 60 - s_min
        k = max(0, math.ceil((d_min + s_min - idle) / t_kw_min))
    pings: list[float] = []
    for i in range(1, k + 1):
        at = anchor + i * t_kw_min * 60
        if i == k:  # 最後一個 ping 之後只剩一跳 ≤ idle
            at = min(at, target - idle * 60)
            at = max(at, pings[-1] + 1 if pings else anchor)
        pings.append(at)
    return [*pings, target]


def early_reset(ref, obs_reset, obs_pct, obs_at) -> bool:
    """S-19／S-23⑥：提前重置＝`ref_reset` 非空 ∧ 觀測 reset 晚於它 ∧ 觀測讀數 < min(ref_pct, 100)
    （同窗讀數單調不減，降＝換窗）。`ref`＝`(ref_reset, ref_pct, ref_at)`；任一輸入缺 ⇒ False；
    讀數時刻早於 `ref_at` ⇒ False（舊讀數不得判換窗）。
    reset 變晚而讀數未降（估早了、視窗沒翻）⇒ False。"""
    try:
        ref_reset, ref_pct, ref_at = ref
    except (TypeError, ValueError):
        return False
    if None in (ref_reset, ref_pct, obs_reset, obs_pct):
        return False
    if obs_at is not None and ref_at is not None and obs_at < ref_at:
        return False
    return obs_reset > ref_reset and obs_pct < min(ref_pct, 100)
