"""額度牆判準核心門面（R218 Q1；DES §3～§4；零 token）。

判準分散在六個職責單一的模組（落點＝`Root_Layout_and_Module_Placement.md` §2 函式庫 sessionctl）：
`qw_calc`（常數與算術）、`qw_wall`（讀數年齡與牆偵測）、`qw_plan`（plan／plan_lines／wake_target）、
`qw_latch`（主載具憑證與閂鎖）、`qw_verdict`（擋派／Stop／靜音判決）、`qw_matrix`（情境矩陣）。
本檔只做**重新匯出**，使 DES 與下游（Q2～Q5）一律以 `quotawall.<名>` 取用；常數的**家**仍在上列
各檔，測試要替換常數請替換它的家（不是本門面）。
時間慣例：與 `park`／額度讀數打交道的函式收 `now: datetime`（aware）；純算術與閂鎖收 epoch 秒。
"""
from __future__ import annotations

from . import qw_matrix as continuity
from .qw_calc import (
    AGENT_EST_DEFAULT_PP,
    BACKUP_GRACE_MIN,
    BURN_DEFAULT_PP_PER_MIN,
    C_REF,
    IDLE_LIMIT_MIN,
    KEY_AGENT,
    KEY_BURN,
    KEY_PP,
    LATCH_RESET_TOL_MIN,
    MAC_HEARTBEAT_MIN,
    OBSERVE_SEC,
    OFF_ENV,
    PING_PP_REF,
    W_CLOSE,
    affordable,
    choose_mode,
    detect_min,
    early_reset,
    k_of,
    p_of,
    ping_pp,
    ping_pp_eff,
    schedule,
    v_of,
)
from .qw_latch import (
    latch_grace,
    latch_mark,
    latch_seen,
    primary_live,
    running_supervision,
    same_window,
)
from .qw_plan import (
    CLOSE,
    FREE,
    NODISPATCH,
    NONE,
    STAGES,
    WALL,
    Plan,
    plan,
    plan_lines,
    wake_target,
)
from .qw_verdict import absent_notice, pretool_verdict, stop_mute, stop_verdict
from .qw_wall import Reading, extrapolate, fresh_reading, wall_state

__all__ = [
    "AGENT_EST_DEFAULT_PP", "BACKUP_GRACE_MIN", "BURN_DEFAULT_PP_PER_MIN", "C_REF", "CLOSE",
    "FREE", "IDLE_LIMIT_MIN", "KEY_AGENT", "KEY_BURN", "KEY_PP", "LATCH_RESET_TOL_MIN",
    "MAC_HEARTBEAT_MIN", "NODISPATCH", "NONE", "OBSERVE_SEC", "OFF_ENV", "PING_PP_REF", "Plan",
    "Reading", "STAGES", "WALL", "W_CLOSE", "absent_notice", "affordable", "choose_mode",
    "continuity", "detect_min", "early_reset", "extrapolate", "fresh_reading", "k_of",
    "latch_grace", "latch_mark", "latch_seen", "p_of", "ping_pp", "ping_pp_eff", "plan",
    "plan_lines", "pretool_verdict", "primary_live", "running_supervision", "same_window",
    "schedule", "stop_mute", "stop_verdict", "v_of", "wake_target", "wall_state",
]
