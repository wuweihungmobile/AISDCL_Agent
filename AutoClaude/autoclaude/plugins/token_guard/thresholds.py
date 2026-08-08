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

    公式：base - (attempt / max_retries) * decay_factor，下限 floor（且 floor 不得高於 base）。
    """
    if max_retries <= 0:
        return base_threshold
    # DEF-84-001（improving_84 真跑 dogfooding 揭露）：decay floor 不得高於 base_threshold。
    # 否則 base_threshold < floor 時，max(..., floor) 會把使用者於 config 設定的低 compact
    # 門檻（如 compact_threshold_pct=1）默默夾到 floor（65），形同忽略 config、違反契約。
    # 夾住 effective_floor ≤ base 使動態門檻恆 ≤ base、誠實 honor config；base ≥ floor 的
    # production 預設（base=80）不受影響：min(65, 80)=65，回傳值與修前完全一致（零退化）。
    effective_floor = min(floor, base_threshold)
    ratio = min(attempt / max_retries, 1.0)
    return max(base_threshold - ratio * decay_factor, effective_floor)


def should_compact_decision(
    *, token_pct: float, threshold: float,
    in_correction_loop: bool, correction_history_len: int,
) -> bool:
    """對齊 PlaybookRunner._should_compact_now 邏輯。

    🔴 DEF-100-002（R80 收掉，improving_100 已備妥等價性鎖）：此處原有一個死分支
    `if in_correction_loop and correction_history_len <= 1: return token_pct >= threshold`
    ——走到那一行時上面的 `token_pct < threshold` 已把 `<` 全部 return 掉，故
    `token_pct >= threshold` 恆為 True ⇒ 該分支 ≡ `return True` ≡ 下方的 `return True`。
    兩個參數因此對結果零影響（簽章保留：呼叫端與 `_should_compact_now` 契約不變）。
    移除後 `.mutmut-cache` #122-124（`and`→`or`、`<=`→`<`、`1`→`2`）那三個等價變異
    連變異點都不存在了。等價性由
    `tests/plugins/token_guard/test_thresholds_mutation.py::
    TestShouldCompactL49DeadBranchEquivalence`（in_loop × hist 全組合）釘住。
    """
    if token_pct < threshold:
        return False
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
