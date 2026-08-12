"""
ConvergenceMonitor — 統一收斂評估，整合 FailureTracker 三個偵測方法。
取代 PlaybookRunner 中分散的 suspect_test_file / is_stuck / is_diverging 三個 if 分支。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .error_classifier import ErrorClass, ErrorClassifier

# R85（訴求 2）：本檔原持有一份與 failure_tracker 逐字相同的 _FAIL_COUNT_PATTERNS，
# 該檔註解自陳理由是「各自持有副本避免循環 import」——實查該理由今天不成立：
# failure_tracker.py 的 import 只有 __future__／re／dataclasses／typing，**零** repo 內
# 模組，故 convergence_monitor → failure_tracker 這個方向不可能成環。收斂為單向 import；
# `convergence_monitor._FAIL_COUNT_PATTERNS` 這個名字仍可解析，呼叫端與測試不需改動。
# 同輪連帶拔掉本檔已無消費者的 `import re`（原本只為那份副本而存在）。
from .failure_tracker import _FAIL_COUNT_PATTERNS

if TYPE_CHECKING:
    from .failure_tracker import FailureTracker


@dataclass
class ConvergenceReport:
    score: float                            # 0.0 = 完全卡死, 1.0 = 完全收斂
    trend: str                              # "improving" | "stuck" | "diverging" | "unknown"
    failed_tests_history: list[int | None] = field(default_factory=list)
    recommendation: str = "continue"        # "continue" | "escalate" | "change_strategy"
    reasoning: str = ""


_classifier = ErrorClassifier()

class ConvergenceMonitor:
    """
    綜合評估跨 attempt 的錯誤收斂趨勢。
    優先級順序：environment > suspect_test_file > is_stuck > is_diverging > 趨勢分析
    """

    def evaluate(self, tracker: FailureTracker) -> ConvergenceReport:
        history = tracker.history
        if not history:
            return ConvergenceReport(0.5, "unknown", [], "continue", "無歷史記錄")

        fail_counts = [self._extract_fail_count(r.eval_output) for r in history]
        last = history[-1]

        # 優先級 0：環境錯誤（AutoClaude 無法修復，直接 ESCALATE）
        error_class = _classifier.classify(last.eval_output, last.exit_code)
        if error_class == ErrorClass.ENVIRONMENT:
            return ConvergenceReport(
                0.0, "environment_error", fail_counts, "escalate",
                "環境錯誤（FileNotFoundError/PermissionError）：AutoClaude 無法修復，需人工介入",
            )

        # 優先級 1：疑似測試檔本身有錯誤
        if tracker.suspect_test_file_error():
            return ConvergenceReport(
                0.0, "diverging", fail_counts, "escalate",
                "錯誤始終指向測試檔，修改實作無效",
            )

        # 優先級 1.5：Gap-008-C 語意測試錯誤（AssertionError 基線不匹配）
        if tracker.suspect_assertion_baseline_mismatch():
            return ConvergenceReport(
                0.1, "assertion_baseline_mismatch", fail_counts, "escalate",
                (
                    "所有失敗都是 AssertionError 且多次修改實作無效。"
                    "⚠️ 高度懷疑測試期望值本身有誤——請人工確認 assert 的期望值是否正確。"
                ),
            )

        # 優先級 2：特徵碼相同（卡死）
        if tracker.is_stuck():
            if self._is_count_improving(fail_counts):
                return ConvergenceReport(
                    0.4, "stuck", fail_counts, "change_strategy",
                    "特徵碼相同但失敗數減少，嘗試不同修正策略",
                )
            return ConvergenceReport(
                0.0, "stuck", fail_counts, "escalate",
                "特徵碼連續相同且無數量改善",
            )

        # 優先級 2.5：振盪（兩個特徵碼交替，比單純卡死更難察覺）
        if tracker.is_oscillating():
            unique_sigs = set(r.error_signature for r in tracker.history[-4:])
            return ConvergenceReport(
                0.0, "oscillating", fail_counts, "escalate",
                f"錯誤在 {len(unique_sigs)} 個特徵碼間交替振盪，Minimax 策略互相衝突",
            )

        # 優先級 2.6：多向振盪（ABCABC 等 3 路以上週期循環）
        if tracker.is_cycling(window=6):
            unique_count = len(set(r.error_signature for r in tracker.history[-6:]))
            return ConvergenceReport(
                0.0, "cycling", fail_counts, "escalate",
                f"錯誤在 {unique_count} 個特徵碼間週期循環，Minimax 策略互相干擾",
            )

        # 優先級 3：exit_code 嚴格遞增（惡化）
        if tracker.is_diverging():
            return ConvergenceReport(
                0.0, "diverging", fail_counts, "escalate",
                "exit_code 嚴格遞增，修正方向錯誤",
            )

        # 優先級 3.5：Gap-008-A 失敗數嚴格遞增（Minimax 幻覺修復使情況惡化）
        if tracker.is_worsening():
            return ConvergenceReport(
                0.0, "worsening", fail_counts, "escalate",
                f"失敗數嚴格遞增（{fail_counts[-3:]}），Minimax 策略持續惡化問題，需人工介入",
            )

        # 趨勢分析
        if self._is_count_improving(fail_counts):
            return ConvergenceReport(
                0.7, "improving", fail_counts, "continue",
                f"失敗數持續減少: {fail_counts}",
            )

        return ConvergenceReport(0.5, "unknown", fail_counts, "continue", "無法判定趨勢，繼續重試")

    @staticmethod
    def _extract_fail_count(eval_output: str) -> int | None:
        for pattern in _FAIL_COUNT_PATTERNS:
            m = pattern.search(eval_output)
            if m:
                return int(m.group(1))
        return None

    @staticmethod
    def _is_count_improving(counts: list[int | None]) -> bool:
        valid = [c for c in counts if c is not None]
        if len(valid) < 2:
            return False
        if len(valid) == 2:
            return valid[-1] < valid[-2]
        # 多點：線性回歸斜率，避免雙點比較被噪音誤導
        n = len(valid)
        x_mean = (n - 1) / 2
        y_mean = sum(valid) / n
        numerator = sum((i - x_mean) * (valid[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return False
        slope = numerator / denominator
        return slope < -0.5  # 斜率明顯下降（每次 attempt 平均減少 0.5+ 個失敗）
