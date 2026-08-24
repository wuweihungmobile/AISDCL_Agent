"""R16／PRD §15.7：動態配速跨模組不變式（H6／H7）的啟動自檢。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 落點在這裡、WHY 不是模組載入時機、WHY 呼叫端是 `session_resume_planner.py`
# ---------------------------------------------------------------------------
# 本 repo 沒有常駐 daemon——每一次「要不要多派 agent」都是**重新起一個行程**去問
# `quota_gate.quota_gate()`／`--pace`，結構上沒有一個天然的「daemon 啟動」時刻。
#
# 🔴 為什麼不是 `quota_gate.py` 模組頂層（載入即驗、越界即 raise）：
#   `context_budget_guard.py` 對 `quota_gate` 的 import 是 `try/except → None`
#   （見該檔檔頭「①能力提供者一律 try/except，不可達時該軸退化成量不到」）——如果自檢
#   的 `raise` 釘在 `quota_gate.py` 模組頂層，`import quota_gate` 失敗會被那個
#   `except` 吞掉，效果是**整條額度軸靜默不啟用**（額度守衛的呼叫點直接被跳過，見該檔
#   `if measuring and quota_gate is not None and (...)`）——這與 R16「越界即拒絕啟動」
#   的意圖恰好相反：不是拒絕，是**悄悄關掉守衛本身**（fail-open，不是 fail-safe）。
# 🔴 為什麼不是 `quota_gate.quota_gate()` 熱路徑內 raise：
#   `context_budget_guard.main()` 的呼叫外層有一道刻意的 `except Exception`
#   （該檔逐字「fail-open 是刻意的，見模組 docstring 的 P0」），任何從熱路徑丟出的例外
#   結構上都會被那一層吞掉、變成放行——一樣到不了「拒絕」。
# ⇒ 唯一「真的會被人／CI 觀察到 rc」的入口是**顯式的 CLI**：
#   `tools/session_resume_planner.py` 的 `main()`（已是 `--pace`／`--check` 等既有人機
#   入口，且已 hard import `quota_gate`）。本檔只提供純函式；那支檔只加最少幾行呼叫
#   ——它是 `guardrail_cli` tier，落地當回合餘裕僅個位數（見
#   `python AutoClaude/tools/check_loc_budget.py --json`），機制本體不可能塞在那裡。
#
# 🔴 為什麼是純函式、吃注入值，不在本檔 import `quota_gate`／`session_resume_planner`：
#   三個時間常數分別住在三個不同的家（`quota_gate.QUOTA_CACHE_TTL_SECONDS`／
#   `.FANOUT_WINDOW_SECONDS`、`session_resume_planner.SENTINEL_INTERVAL_SECONDS`、
#   `Policy.availability_min_dwell_seconds`），而那三個家彼此的既有依賴方向是
#   `session_resume_planner → quota_gate → quota_policy`——本檔若回頭 import 任一個
#   hub 模組，會是新增的反向依賴。改為讓呼叫端把值算好餵進來（同
#   `quota_availability.advance()`／`quota_policy.axis_cap()` 的既有分工：判讀本體吃
#   值，不吃「該去哪裡問值」）。
#
# 🔴 H7「單一 Step 中位牆鐘執行時間」目前**沒有** P0 觀測資料（PRD §15.7 逐字要求
#   「若無現成量測值，可先用一個保守預設值並在報告中明確標注」）：下面的常數是**占位值**，
#   不是量出來的——待正式觀測資料校準前，任何讀到這個數字的人都不應該把它當成已驗證的
#   量測結果。
from __future__ import annotations

#: 🔴 待校準占位值（不是量測值，見檔頭最後一段）：假設一個 Step 的中位牆鐘執行時間為
#: 60 秒（保守側——真實值若更長，H7 會更容易越界而被抓到；此值若更短則相反，故標成
#: 「保守」是相對於「寧可誤報也不要漏報」的方向，不是絕對意義上的保守）。
STEP_MEDIAN_WALL_SECONDS_PLACEHOLDER = 60.0


def dynamic_pacing_invariant_problems(
        availability_min_dwell_seconds: float, *,
        cache_ttl_seconds: float,
        sentinel_interval_seconds: float,
        fanout_window_seconds: float,
        availability_exit_streak: int = 2,
        step_median_wall_seconds: float = STEP_MEDIAN_WALL_SECONDS_PLACEHOLDER) -> list[str]:
    """H6／H7 兩條不變式；純函式，全部門檻由呼叫端注入（可合成注入自證）。

    空清單＝全部通過。同 `quota_policy.policy_monotonicity_problems()` 的既有慣例
    （回「問題清單」而非布林，讀者一次看得到**哪一條**越界，不必再猜）。

    🔴 R102 修復（四方審查 F5/F17/F25）：§6.1 不變式 4 逐字是**雙邊**要求——dwell 三明治  round-label-ok
    不等式（H6）**且** `AVAILABILITY_EXIT_STREAK ≥ 2`。此前只驗了前半，後半只靠
    `quota_policy_env.py` 的 `EnvVar(lo=2.0)` 在 `.env` 解析層擋——但那條路徑對越界值是
    **靜默 clamp 回預設**，正是 §6.1 明文禁止的姿態（「不得以預設值靜默帶過」），且任何
    直接構造 `Policy(availability_exit_streak=1)` 的呼叫點會完全繞過那一層、也不會被
    這支自檢攔下。`availability_exit_streak` 帶預設值 2 只是為了不打斷既有呼叫端
    （同本函式其餘欄位的既有先例），不代表「越界時可以悄悄退回 2」——這裡的預設值只在
    「呼叫端沒有值可餵」時才生效，一旦餵了一個 <2 的值就會被下面這一格擋下。
    """
    problems = []
    if not cache_ttl_seconds <= availability_min_dwell_seconds <= sentinel_interval_seconds:
        problems.append(
            "[H6] 不變式 QUOTA_CACHE_TTL_SECONDS"
            f"({cache_ttl_seconds}) ≤ AVAILABILITY_MIN_DWELL_SECONDS"
            f"({availability_min_dwell_seconds}) ≤ SENTINEL_INTERVAL_SECONDS"
            f"({sentinel_interval_seconds}) 不成立")
    if availability_exit_streak < 2:
        problems.append(
            f"[H6] 不變式 AVAILABILITY_EXIT_STREAK({availability_exit_streak}) ≥ 2 不成立")
    if fanout_window_seconds < cache_ttl_seconds:
        problems.append(
            f"[H7] FANOUT_WINDOW_SECONDS({fanout_window_seconds}) < "
            f"QUOTA_CACHE_TTL_SECONDS({cache_ttl_seconds})——控制週期比量測還快"
            "（積分飽和：cap 會在還沒有新讀數之前就被重新判定）")
    if fanout_window_seconds < 2 * step_median_wall_seconds:
        problems.append(
            f"[H7] FANOUT_WINDOW_SECONDS({fanout_window_seconds}) < 2×單一 Step 中位牆鐘"
            f"執行時間({step_median_wall_seconds})——後者為待校準占位值，見 PRD §15.7，"
            "本行本身即為「尚未有真實觀測資料」的證據")
    return problems


def validate_dynamic_pacing_invariants(gate, sentinel_interval_seconds: float, *,
        step_median_wall_seconds: float = STEP_MEDIAN_WALL_SECONDS_PLACEHOLDER) -> list[str]:
    """R16 啟動自檢的**唯一正規入口**。`gate`＝已 import 的 `quota_gate` 模組（依賴注入，
    見檔頭 WHY——本檔不自己 import 它）。回問題清單；空＝可以啟動，非空＝呼叫端應拒絕。
    """
    policy = gate.quota_policy.load_policy(gate.policy_env())[0]
    return dynamic_pacing_invariant_problems(
        policy.availability_min_dwell_seconds,
        cache_ttl_seconds=gate.QUOTA_CACHE_TTL_SECONDS,
        sentinel_interval_seconds=sentinel_interval_seconds,
        fanout_window_seconds=gate.FANOUT_WINDOW_SECONDS,
        availability_exit_streak=policy.availability_exit_streak,
        step_median_wall_seconds=step_median_wall_seconds)
