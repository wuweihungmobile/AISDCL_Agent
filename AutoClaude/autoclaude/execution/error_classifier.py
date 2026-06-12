"""
ErrorClassifier — 對 eval_output 進行語義分類。
輸出 ErrorClass enum，供 ConvergenceMonitor 和 prompt_builder 使用。

優先級（先匹配先返回）：
  SDD_CONTRACT_VIOLATION（結構化標記）> ENVIRONMENT > SYNTAX > IMPORT > TYPE
  > ASSERTION > TIMEOUT > UNKNOWN
"""
from __future__ import annotations
from enum import Enum
import re


class ErrorClass(str, Enum):
    SYNTAX      = "syntax"        # SyntaxError / IndentationError
    IMPORT      = "import"        # ImportError / ModuleNotFoundError
    ASSERTION   = "assertion"     # AssertionError / pytest FAILED
    TYPE        = "type"          # TypeError / AttributeError
    ENVIRONMENT = "environment"   # FileNotFoundError / PermissionError / 環境問題
    TIMEOUT     = "timeout"       # 執行超時（exit_code=124 或特定訊息）
    UNKNOWN     = "unknown"
    # AutoSDD_improving_01 §4.2（W2，additive 第 8 類）：SDD 契約違反。
    # 來源：(1) adapter 生成的 evaluator 包裝層於 AT 失敗時輸出結構化標記
    # "SDD-VIOLATION[{at_id}]"；(2) SddGovernancePlugin PRE_ATTEMPT 越閘 deny。
    SDD_CONTRACT_VIOLATION = "sdd_contract_violation"


_PATTERNS: list[tuple[ErrorClass, re.Pattern]] = [
    # SDD-VIOLATION[...] 為結構化顯式標記，必須先於 ASSERTION 等啟發式規則
    # 匹配（evaluator 輸出常同時含 pytest assertion 痕跡，置後會被吃掉）
    (ErrorClass.SDD_CONTRACT_VIOLATION, re.compile(r'SDD-VIOLATION\[')),
    (ErrorClass.ENVIRONMENT, re.compile(
        r'FileNotFoundError|PermissionError|No such file|Access is denied', re.I)),
    (ErrorClass.SYNTAX,      re.compile(r'SyntaxError|IndentationError', re.I)),
    (ErrorClass.IMPORT,      re.compile(
        r'ImportError|ModuleNotFoundError|No module named', re.I)),
    (ErrorClass.TYPE,        re.compile(r'TypeError|AttributeError', re.I)),
    (ErrorClass.ASSERTION,   re.compile(r'AssertionError|assert |\d+ failed', re.I)),
    (ErrorClass.TIMEOUT,     re.compile(r'Timeout|timed out|exit code.*124', re.I)),
]


class ErrorClassifier:
    """根據 eval_output 和 exit_code 分類錯誤語義。"""

    def classify(self, eval_output: str, exit_code: int = 1) -> ErrorClass:
        for error_class, pattern in _PATTERNS:
            if pattern.search(eval_output):
                return error_class
        return ErrorClass.UNKNOWN
