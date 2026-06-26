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
  - compact prompt 為 core-local 結構化保留提示常數（與 token_guard.compactor 同精神；
    棄用路徑的 memory-anchor enrichment 本輪未移植，見 improving_79 §8 誠實標記）。
  - marker 格式對齊 A/B 載具解析（``"TOKEN_COMPACT" in line`` 計 compact_count、行內
    ``NN%`` 餵 peak、``[Sxx]`` 做 per-step 歸因）。
"""
from __future__ import annotations

import logging

from ._token_observer import TokenObserver
from .ports.executor import IExecutor

logger = logging.getLogger("autoclaude.core.kernel")

# core-local 結構化 /compact 提示（對齊 token_guard.compactor.build_compact_prompt 之保留策略，
# 但不含 memory-anchor；不 import plugin 以維持 core-purity）。
_COMPACT_PROMPT = (
    "/compact\n"
    "請在壓縮時優先保留：\n"
    "1. 目前正在實作的檔案清單與關鍵函式名稱\n"
    "2. 測試案例的名稱與期望行為\n"
    "3. 最近一次的錯誤訊息（精確的 SyntaxError / AssertionError 位置）\n"
    "可以丟棄：完整的 stdout log、已完成步驟的詳細操作記錄。"
)


def perform_compact(
    executor: IExecutor, *, step_id: str, peak_pct: float, timeout: int = 60,
) -> float:
    """送 /compact 並印真誠 TOKEN_COMPACT marker；回傳 compact 後觀測到的 token% 峰值。

    Args:
        executor: Kernel 持有的 IExecutor（與步驟執行同一受信 executor）。
        step_id: 當前步驟 id（marker [Sxx] 歸因用）。
        peak_pct: 觸發 compact 的步驟峰值 token%（marker 顯示用）。
        timeout: /compact 執行逾時秒數（預設 60，對齊棄用路徑）。

    Returns:
        compact 執行後 fresh observer 觀測到的 token% 峰值（無 token 訊號回 0.0）。
    """
    logger.info(
        "=== STATE: TOKEN_COMPACT | [%s] context %.0f%% >= compact 門檻 ===",
        step_id, peak_pct,
    )
    post_observer = TokenObserver()
    executor.execute(
        _COMPACT_PROMPT, maintain_context=True, timeout=timeout,
        label=f"{step_id}_compact", on_event=post_observer,
    )
    return post_observer.peak_pct
