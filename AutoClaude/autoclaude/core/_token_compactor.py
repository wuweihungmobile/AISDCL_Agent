"""_token_compactor — Kernel 路徑的 /compact 動作 helper（improving_79 W-78-2 / DEF-78-001）。

職責（純委派 + 觀測，零 token-guard 決策）：
  - production Kernel 路徑在 token-guard 判 ≥80% compact 門檻（``request_compact``）時，
    送 ``/compact`` 指令給 executor 壓縮 context，並印真誠 ``TOKEN_COMPACT`` marker。
  - 以 fresh ``TokenObserver`` 觀測 compact 執行後的真實 token% 峰值，回傳供呼叫端
    （Kernel ``_handle_compact``）emit ``POST_COMPACT`` 交 TokenGuardPlugin 判 Gap-008-E
    （連續 compact 失敗 2 次 → 強制 HALT）。

背景（DEF-78-001 compact 子路徑）：improving_78 W-78-1 已接 halt 子路徑；本 helper 補
compact 子路徑——production 唯一正式路徑（Kernel）原本零消費 ``request_compact``、不送
/compact，致 compact 編排在 production 結構性死碼、A/B 載具 compact_count 真跑恆 0。

設計原則：
  - 純委派：compact 決策（should_compact / 連續失敗計數）全在 TokenGuardPlugin（SSOT），
    本 helper 不持有任何 token-guard 狀態，亦不 import plugin / infra（維持 core-purity）。
  - compact prompt 由 core 共享 SSOT ``_compact_prompt.build_compact_prompt`` 組裝
    （improving_80 W-80-1：原住 plugin 的純函式上移至 core，core 與 plugin 共用單一實作）；
    帶 task/attempt/global_goal/failure_summary 時附加 ``=== MEMORY ANCHOR ===`` 區塊，
    確保壓縮後關鍵任務記憶存活。task=None 時退回基本保留策略（逐字等價舊 core-local 常數）。
  - marker 格式對齊 A/B 載具解析（``"TOKEN_COMPACT" in line`` 計 compact_count、行內
    ``NN%`` 餵 peak、``[Sxx]`` 做 per-step 歸因）。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ._compact_prompt import build_compact_prompt
from ._token_observer import TokenObserver
from .ports.executor import IExecutor

logger = logging.getLogger("autoclaude.core.kernel")


def perform_compact(
    executor: IExecutor, *, step_id: str, peak_pct: float,
    task: Optional[Any] = None, attempt: int = 0,
    global_goal: Optional[str] = None, failure_summary: str = "",
    timeout: int = 60,
) -> float:
    """送 /compact 並印真誠 TOKEN_COMPACT marker；回傳 compact 後觀測到的 token% 峰值。

    Args:
        executor: Kernel 持有的 IExecutor（與步驟執行同一受信 executor）。
        step_id: 當前步驟 id（marker [Sxx] 歸因用）。
        peak_pct: 觸發 compact 的步驟峰值 token%（marker 顯示用）。
        task: 當前 PlaybookTask（給定時 prompt 附加 MEMORY ANCHOR；None → 基本保留策略）。
        attempt: 當前 attempt（anchor [ATTEMPT] 顯示用，0-based）。
        global_goal: playbook 總目標（anchor [GLOBAL_GOAL] 注入用）。
        failure_summary: 前次 attempt 失敗背景（anchor [LAST_FAILURE] 注入用，可空）。
        timeout: /compact 執行逾時秒數（預設 60，對齊棄用路徑）。

    Returns:
        compact 執行後 fresh observer 觀測到的 token% 峰值（無 token 訊號回 0.0）。
    """
    logger.info(
        "=== STATE: TOKEN_COMPACT | [%s] context %.0f%% >= compact 門檻 ===",
        step_id, peak_pct,
    )
    prompt = build_compact_prompt(
        task=task, attempt=attempt,
        failure_summary=failure_summary, global_goal=global_goal,
    )
    post_observer = TokenObserver()
    executor.execute(
        prompt, maintain_context=True, timeout=timeout,
        label=f"{step_id}_compact", on_event=post_observer,
    )
    return post_observer.peak_pct
