"""sessionctl 成本模型（R216；設計 SessionSwitch_CostModel_Design §3／§4.4／§11 掌舵者裁決）。

只留裁決後仍有作用對象的部分：快取**已經冷了**之後，續跑與換新誰便宜（F4），加上硬線不變式。
軟線 `T_soft`／hold 依掌舵者裁決（D-1＝③ 不設軟線、D-2＝hold 不實作）不在此，所以參數表
也不含 `B`、`N_lo`（那兩個只餵 F3）。純函式＋讀 env，不寫檔、不 spawn。

單位與 `tools/lib/wastecensus/reader.py` 同一組加權：cache_read 0.1／cache_write(1h) 2.0／
cache_write(5m) 1.25。一個上下文 c token 的 session，快取過期後同 session 續跑必整份重寫
＝ `W_CC1·c`（主控 1 小時層）；開新 session 的接手成本＝ `F·(1+q)`（F＝實測接手成本，
q＝失去上下文的品質損失係數，q=1 治理決定，設計 §3.2）。
"""
from __future__ import annotations

import math
import os
import sys

#: 加權單位（設計 §3.1）。`keepwarm.py` 另有同值的 `W_CR`／`W_CC1`（該檔本棒不動）；
#: 兩處相等由 `test_sessionctl_costmodel.py` 斷言，改一處不改另一處即紅。
W_CR, W_CC1, W_CC5 = 0.1, 2.0, 1.25

FRESH_COST_KEY = "AUTOSDD_SWITCH_FRESH_COST_UNITS"
VALUE_Q_KEY = "AUTOSDD_SWITCH_CONTEXT_VALUE_Q"

#: 觀測到的「流程內 autocompact」最小上下文（設計 §1.4-1：881,938）。硬線必須嚴格小於它，
#: 否則 autocompact 會搶在主動交棒之前把上下文砍到 1～2 萬（比交接包更失真，設計 X-2）。
#: 這是量測值不是定律：重量後只准上修，並同步 `quota_policy_env` 的 HARD 出廠值檢查。
OBSERVED_AUTOCOMPACT_MIN = 881_938


def _factory(name: str) -> float:
    import quota_policy_env  # noqa: PLC0415 — lazy：純資料模組，只有取出廠值時才需要

    return float(next(spec.default for spec in quota_policy_env.ENV_SPEC if spec.name == name))


def _param(name: str, env, *, minimum: float) -> float:
    """一個有限實數參數：env 缺席／空＝出廠值；非數字、NaN／inf、< `minimum` 一律退回出廠值
    並 stderr 出聲一次（同 `switch.threshold` 的紀律；壞值不拋、不靜默吞）。"""
    base = _factory(name)
    raw = str((os.environ if env is None else env).get(name) or "").strip()
    if not raw:
        return base
    try:
        val = float(raw)
    except ValueError:
        val = math.nan
    if math.isfinite(val) and val >= minimum:
        return val
    print(f"⚠️ {name}={raw!r} 不是 ≥ {minimum:g} 的有限數 ⇒ 退回出廠值 {base:g}", file=sys.stderr)
    return base


def fresh_cost(env=None) -> float:
    """`F`：新 session 接手成本（加權單位；出廠 480,000＝實測中位）。必須 ≥ 1。"""
    return _param(FRESH_COST_KEY, env, minimum=1.0)


def value_q(env=None) -> float:
    """`q`：上下文價值係數（出廠 1.0；0＝只看 token 成本）。必須 ≥ 0。"""
    return _param(VALUE_Q_KEY, env, minimum=0.0)


def fresh_total(env=None) -> float:
    """`F·(1+q)`：換新 session 的總代價（含失去上下文的品質損失）。"""
    return fresh_cost(env) * (1.0 + value_q(env))


def fresh_ctx_threshold(env=None) -> float:
    """F4 的臨界上下文 `F(1+q)/W_CC1`（出廠 480,000 token）：c 超過它，冷快取下續跑的重寫
    成本就高過換新。"""
    return fresh_total(env) / W_CC1


def fresh_is_cheaper(c: int | float | None, *, cold: bool, env=None) -> bool:
    """(F4) 快取**已冷**時，換新 session 是否比同 session 續跑便宜：`W_CC1·c > F(1+q)`。

    · 快取仍熱 ⇒ 一律 False（讀價 `0.1c` 必小於 F；不是這條要判的情境）；
    · c 量不到（None／非正）⇒ False（FRESH 的代價是丟上下文，量不到不該單方面造成資訊損失）；
    · 邊界：c＝臨界值時相等 ⇒ False（嚴格大於才換新，與設計 §3.3 不等號一致）。
    """
    if not cold or c is None or c <= 0:
        return False
    return W_CC1 * c > fresh_total(env)


def f4_reason(c: int | float, env=None) -> str:
    """命中時給人看的理由字串（`fresh_reasons` 逐條列出用）。"""
    return (f"F4 快取已冷且續跑重寫 {W_CC1 * c:,.0f} 單位 > 換新 {fresh_total(env):,.0f} 單位"
            f"（上下文 {c:,} > 臨界 {fresh_ctx_threshold(env):,.0f} tokens）")
