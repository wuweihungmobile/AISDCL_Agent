"""Phase H M1 / ACT-047 — Output Quality Scorer (OQS).

AmbiguityScorer（Rule 9.16）量化「輸入規格模糊度」；OQS 是它的對稱物，量化
「輸出執行品質」0~1。由 Evaluator 在沙箱實跑後產出，落實 SDD_improving_Automation_08.md
§4.4：讓「主觀產物品質」也被客觀量化（Anthropic 主觀標準量化思維）。

設計：rule-based / 確定性、零 LLM、零外部依賴（沿用 ambiguity_scorer 模式）。
分數越高越好（1.0 = 完美）。SCORER_VERSION 變更須 bump（cache 一致性）。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

SCORER_VERSION = "v1.0"

# 各維度權重（總和 = 1.0）
_WEIGHTS = {
    "test_pass_rate": 0.40,   # 測試通過率
    "runtime_clean": 0.25,    # 無 runtime 錯誤（stderr / exit code）
    "perf_within_pbs": 0.20,  # 效能在 PBS 門檻內
    "ui_assertions": 0.15,    # UI/契約斷言通過率
}

# OQS ≥ BLOCK_THRESHOLD 才視為 pass（EXECUTION_EVALUATION 放行 PR_REVIEW）
BLOCK_THRESHOLD = 0.80


@dataclass
class ExecutionObservation:
    """Evaluator 從沙箱實跑收集的客觀觀測（非 AI 自評）。"""
    tests_total: int = 0
    tests_passed: int = 0
    runtime_errors: int = 0      # stderr error 行數 / 非零 exit / crash
    nonzero_exit: bool = False
    perf_violations: int = 0     # 超出 PBS 的指標數
    perf_checks: int = 0
    ui_assertions_total: int = 0
    ui_assertions_passed: int = 0


@dataclass
class OQSResult:
    score: float
    passed: bool
    verdict: str                 # "pass" | "runtime_fail" | "spec_defect" | "inconclusive"
    dimensions: dict
    scorer_version: str = SCORER_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _ratio(num: int, den: int, *, default: float = 1.0) -> float:
    if den <= 0:
        return default  # 無此維度的觀測 → 不扣分（中性）
    return max(0.0, min(1.0, num / den))


def score(obs: ExecutionObservation, *, spec_defect: bool = False) -> OQSResult:
    """Compute the Output Quality Score from objective sandbox observations.

    Args:
        obs: ExecutionObservation captured by the Evaluator in the sandbox.
        spec_defect: set True when execution PROVED a spec contradiction
            (e.g. an assertion that can never be satisfied — P95 < 0). This
            routes EXECUTION_EVALUATION → SPEC_AUDIT regardless of score.
    """
    d_test = _ratio(obs.tests_passed, obs.tests_total)
    d_runtime = 0.0 if (obs.nonzero_exit or obs.runtime_errors > 0) else 1.0
    d_perf = 1.0 - _ratio(obs.perf_violations, obs.perf_checks, default=0.0)
    d_ui = _ratio(obs.ui_assertions_passed, obs.ui_assertions_total)

    dims = {
        "test_pass_rate": round(d_test, 4),
        "runtime_clean": round(d_runtime, 4),
        "perf_within_pbs": round(d_perf, 4),
        "ui_assertions": round(d_ui, 4),
    }
    total = round(sum(_WEIGHTS[k] * dims[k] for k in _WEIGHTS), 4)

    # H-1 修：執行接地的核心契約 — 「沒有真實觀測」絕不可放行 pass（否則 stub
    # 零觀測會四維皆 default 1.0 → false green，瓦解 Phase H 執行接地目的）。
    # 正向觀測訊號：跑過測試 / UI 斷言 / 效能檢查；失敗訊號：非零 exit / runtime 錯誤。
    has_positive_obs = obs.tests_total > 0 or obs.ui_assertions_total > 0 or obs.perf_checks > 0
    has_failure_signal = obs.nonzero_exit or obs.runtime_errors > 0
    has_observation = has_positive_obs or has_failure_signal

    if spec_defect:
        verdict = "spec_defect"
        passed = False
    elif not has_observation:
        # 沙箱從未真正跑過/壞過 — 無客觀證據，禁止放行（Evaluator 須注入真實觀測）
        verdict = "inconclusive"
        passed = False
    elif total >= BLOCK_THRESHOLD:
        verdict = "pass"
        passed = True
    else:
        verdict = "runtime_fail"
        passed = False

    return OQSResult(score=total, passed=passed, verdict=verdict, dimensions=dims)
