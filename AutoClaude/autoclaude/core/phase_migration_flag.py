"""T18_P2_PHASES_MIGRATED feature flag — SD_Improving_05 §7 (2) / W0 SD-C7。

回滾協議：W1~W4 mixin 下沉採逐 phase 切換，每個 phase 切換後保留 mixin fallback
≥ 1 個 sub-task 週期（≥ 1 週）才可拔除。本 flag 控制 Kernel 是否走新 Plugin 路徑
（True）或回退 mixin（False）。

讀取優先級：
  1. 程式內 set_migrated_phases() 顯式設定（測試用）
  2. 環境變數 AUTOCLAUDE_T18_P2_PHASES_MIGRATED（逗號分隔）
  3. 預設：空 set（全部走 mixin fallback）

8 個合法 phase 名稱（與 SD_05 §7 (2a) 一致）：
  PRE_COMPACT, POST_COMPACT, ON_PERSISTENCE_REQUEST,
  ON_EVOLUTION_PROPOSE, ON_EVOLUTION_APPLY, ON_AUTO_RESUME_WAKE,
  ON_PROMPT_PREPARED, ON_ESCALATION_DUMP_REQUEST

W6 G6 通過後 ≥ 3 個自然日無 production rollback 才可拔除此 flag。
"""
from __future__ import annotations

import os
from typing import Optional

from .hookspec import KernelPhase


# SD_05 §7 (2a)：8 個合法 phase 名稱
LEGAL_PHASES: frozenset[str] = frozenset({
    "PRE_COMPACT",
    "POST_COMPACT",
    "ON_PERSISTENCE_REQUEST",
    "ON_ESCALATION_DUMP_REQUEST",
    "ON_EVOLUTION_PROPOSE",
    "ON_EVOLUTION_APPLY",
    "ON_AUTO_RESUME_WAKE",
    "ON_PROMPT_PREPARED",
})

_ENV_VAR = "AUTOCLAUDE_T18_P2_PHASES_MIGRATED"
_override: Optional[frozenset[str]] = None


def get_migrated_phases() -> frozenset[str]:
    """取得目前已切換至新 Plugin 路徑的 phase 集合（phase name uppercase）。

    讀取優先級：set_migrated_phases() override > 環境變數 > 空 set。
    """
    if _override is not None:
        return _override
    raw = os.environ.get(_ENV_VAR, "").strip()
    if not raw:
        return frozenset()
    parts = {p.strip().upper() for p in raw.split(",") if p.strip()}
    illegal = parts - LEGAL_PHASES
    if illegal:
        raise ValueError(
            f"{_ENV_VAR} 含非法 phase 名稱：{illegal}；"
            f"合法 phase: {sorted(LEGAL_PHASES)}"
        )
    return frozenset(parts)


def is_phase_migrated(phase: KernelPhase) -> bool:
    """判斷指定 KernelPhase 是否已切換至新 Plugin 路徑。"""
    return phase.name in get_migrated_phases()


def set_migrated_phases(phases: Optional[set[str]]) -> None:
    """測試用：override 環境變數設定。傳 None 還原為讀環境變數。"""
    global _override
    if phases is None:
        _override = None
        return
    illegal = phases - LEGAL_PHASES
    if illegal:
        raise ValueError(f"非法 phase 名稱：{illegal}")
    _override = frozenset(phases)
