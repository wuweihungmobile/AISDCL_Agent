"""SD_Improving_06 W0-T0-2：PII / secret / normal 三態分類 ENUM

對應 PM 拍板 #11（2026-05-17）：PII hybrid 策略
    - W0：ENUM schema 一次到位（含 RESERVED 後擴位）
    - W3：在 drift_log / config_audit_log / yaml_import_diffs 寫入前
          套用過濾器（依本 ENUM 分類動作）

法務 / Security 共審範圍（SD_06 §11 §12 §6.5 PII 過濾 AC）：
    NORMAL  → 可入庫、無遮罩
    PII     → 入庫前必須遮罩（hash 或 partial mask）
    SECRET  → 完全禁止入庫（drop / abort write）

紅線（SD_06 §7 ❌12 衍生 + §11 PII 規則）：
    任何寫入 drift_log / config_audit_log / yaml_import_diffs 之前，
    呼叫端必須先以本 ENUM 對欄位分類並執行對應動作；
    違反者由 W3 PII filter 中介層 raise PIIFilterViolation。
"""
from __future__ import annotations

from enum import Enum
from typing import Final


class PIIClassification(str, Enum):
    """PII 三態分類（hybrid 策略：ENUM 結構 + W3 過濾器行為）。

    繼承 ``str`` 是為了 JSON / YAML 持久化時直接序列化為字串值，
    避免在 alembic / Pydantic round-trip 時出現 enum-vs-str 比較陷阱。
    """

    NORMAL = "normal"
    """一般資料：可入庫、無遮罩需求。"""

    PII = "pii"
    """個人識別資訊：入庫前必須遮罩（SHA-256 hash 或保留前 4 後 4 partial mask）。

    範例：email / phone / IP / user_id / device_id。
    """

    SECRET = "secret"
    """機密資訊：完全禁止入庫（W3 過濾器 drop write 並寫 audit log）。

    範例：API key / password / token / signing key / TLS 私鑰。
    """

    RESERVED_1 = "_reserved_1"
    """後擴位（PM #11 hybrid 預留）：W3+ 若新增 LEGAL_HOLD / GDPR_DSAR 等
    細分類別，可由本欄改寫；現階段不可被生產碼引用。
    """

    RESERVED_2 = "_reserved_2"
    """同 RESERVED_1：後擴第 2 位，現階段禁止引用。"""


# 對應動作宣告（W3 過濾器 SSOT；W0 階段僅作 ENUM + 動作表入庫）
PIIFilterAction: Final[dict[PIIClassification, str]] = {
    PIIClassification.NORMAL: "passthrough",
    PIIClassification.PII: "mask",
    PIIClassification.SECRET: "drop",
    PIIClassification.RESERVED_1: "abort",  # 未定義 → fail-loud
    PIIClassification.RESERVED_2: "abort",
}


def is_active_classification(value: PIIClassification) -> bool:
    """W3+ 過濾器使用：判斷分類是否為生產可用（非 RESERVED 後擴位）。

    Why: RESERVED_1/2 屬未來擴充佔位，W0 寫入規則必須對其 raise，
    避免 schema 漂移期被誤用而出現未定義行為。
    """
    return not value.value.startswith("_reserved_")


__all__ = [
    "PIIClassification",
    "PIIFilterAction",
    "is_active_classification",
]
