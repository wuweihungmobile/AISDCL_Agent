"""thresholds.py — token 門檻純函式判斷（SD_06 W2-T2-13）。

無狀態純函式，無 IO，可單獨單元測試。

對應 SD_05 W2 公開 API：
  - get_dynamic_compact_threshold (Gap-009-F)
  - should_compact_decision (對齊 _should_compact_now)
  - should_halt_decision

SD_09 W3 SP-1 引用點：本模組為 mutation pilot 觀察期 #1 baseline 目標
之一（`.mutation_baseline.toml` token_guard.kill_rate ≥ 70%）。
"""
from __future__ import annotations

__all__ = [
    "get_dynamic_compact_threshold",
    "should_compact_decision",
    "should_halt_decision",
    "verify_act_first_ordering",
]


def get_dynamic_compact_threshold(
    *, base_threshold: float, attempt: int, max_retries: int,
    floor: float = 65.0, decay_factor: float = 15.0,
) -> float:
    """Gap-009-F：依重試進度動態降低 compact 門檻。

    公式：base - (attempt / max_retries) * decay_factor，下限 floor。
    """
    if max_retries <= 0:
        return base_threshold
    ratio = min(attempt / max_retries, 1.0)
    return max(base_threshold - ratio * decay_factor, floor)


def should_compact_decision(
    *, token_pct: float, threshold: float,
    in_correction_loop: bool, correction_history_len: int,
) -> bool:
    """對齊 PlaybookRunner._should_compact_now 邏輯。"""
    if token_pct < threshold:
        return False
    if in_correction_loop and correction_history_len <= 1:
        return token_pct >= threshold
    return True


def should_halt_decision(*, token_pct: float, halt_threshold: float) -> bool:
    return token_pct >= halt_threshold


def verify_act_first_ordering(
    *, autocompact_threshold_tokens: int, max_tokens: int, halt_pct: float,
) -> bool:
    """improving_68 W-68-1：驗證 AutoClaude Token Guard 是否「先於」SDK autocompact 觸發。

    整合 Claude Agent SDK 後，SDK 內建 autocompact 會在 `autoCompactThreshold`（token 數）
    觸發壓縮。為保住 AutoClaude 形式化門檻（halt_pct，預設 90%）的權威——使 AutoClaude
    先 checkpoint/halt、SDK 來不及自行壓縮——AutoClaude halt 換算的 token 數必須**嚴格小於**
    SDK 的 autocompact 門檻。

    回傳 True＝排序安全（act-first 成立）；False＝不安全（SDK 可能搶先壓縮，撞掉形式化門檻），
    呼叫端（SdkExecutorAdapter 啟動檢查）應 fail-closed warn 或拒絕以該設定啟用 SDK 後端。

    防呆：max_tokens<=0 或 autocompact_threshold_tokens<=0 視為無法判定 → 回 False（fail-closed，
    寧可保守擋下也不放行可能搶先壓縮的設定）。
    """
    if max_tokens <= 0 or autocompact_threshold_tokens <= 0:
        return False
    halt_tokens = (halt_pct / 100.0) * max_tokens
    return halt_tokens < autocompact_threshold_tokens
