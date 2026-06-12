"""可觀測性 Adapter 集合（SD_Improving_08 W4 / ADR-SD08-004 §2.1）。

W4 唯一實作：
  - LocalLogger：以 stdlib logging 為後端（無外部相依）

未來（SD_10+）：
  - OpenTelemetry adapter（otel.py）以平行 adapter 形式並存
"""
from .local_logger import LocalLogger, LocalLoggerSpan

__all__ = ["LocalLogger", "LocalLoggerSpan"]
