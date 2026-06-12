"""
ErrorBudget — 語意錯誤預算管理器（Gap-010-A）。

依 error_class 設定個別重試上限，避免低複雜度錯誤（SyntaxError）浪費
與高複雜度錯誤（AssertionError）不足的情況。
"""
from __future__ import annotations

from typing import ClassVar


class ErrorBudget:
    """依 error_class 限制有效重試次數的語意預算管理器。"""

    BUDGETS: ClassVar[dict[str, int]] = {
        "environment": 0,  # 環境錯誤：立即 ESCALATE（ConvergenceMonitor 已優先處理）
        "syntax":      2,  # 語法錯誤：2 次修正（低複雜度）
        "import":      2,  # 依賴問題：2 次
        "type":        3,  # 型別錯誤：3 次（需理解函式簽名）
        "assertion":   5,  # 斷言失敗：5 次（需理解業務語意）
        "timeout":     1,  # 超時：1 次（需效能優化）
        "unknown":     3,  # 未知：預設 3 次
    }

    def effective_max_retries(
        self,
        global_max: int,
        current_error_class: str,
        attempt: int,
    ) -> int:
        """
        返回當前錯誤類型的有效重試上限。

        邏輯：
        - 取 global_max 與 (attempt + class_budget) 的最小值
        - 確保不會超過全域設定，也不會給低複雜度錯誤過多機會

        Args:
            global_max: Playbook 全域重試上限
            current_error_class: ErrorClassifier 分類結果（syntax/import/assertion/...）
            attempt: 目前的 attempt 編號（0-based）

        Returns:
            有效最大重試次數（若已超出，呼叫方應提前 ESCALATE）
        """
        if global_max <= 0:
            return 0
        class_budget = self.BUDGETS.get(current_error_class, self.BUDGETS["unknown"])
        return min(global_max, attempt + class_budget)
