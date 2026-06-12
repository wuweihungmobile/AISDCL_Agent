"""state_normalize — SD_Improving_06 W5-T5-4：統一狀態正規化 helper。

對應規格：
  - SD_Improving_06.md v1.2 §3 §5 R-SD06-5-1（dual_state drift 全欄比對）
  - SD06_Execution_Guide.md W5 T5-4：`_normalize()` helper
    （datetime → ISO8601 UTC / UUID → str / Enum → value）
  - SD06_Execution_Guide.md W5 T5-1：ExecutionContext round-trip property-based test 共用

紅線：
  - datetime 一律輸出為 UTC ISO8601（``Z`` 後綴或 ``+00:00``）；無 tzinfo 時視為 UTC
  - UUID → str；Enum → .value；set → 排序後 list；frozenset → 排序後 list
  - 巢狀 dict / list / tuple 遞迴正規化
  - 對未知物件 fallback ``str()`` 並寫 logger.debug（避免 silent data drift）
"""
from __future__ import annotations

import logging
from datetime import datetime, date, timezone
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


def normalize_value(value: Any) -> Any:
    """將值正規化為 JSON / drift-log 可比對的純資料表示。

    - datetime / date → ISO8601 UTC 字串（無 tz 視為 UTC）
    - UUID → str
    - Enum → value
    - set / frozenset → 排序後 list
    - dict / list / tuple → 遞迴正規化
    - bytes / bytearray → utf-8 decode（失敗 fallback hex）
    - 其他 dataclass-like → dict 形式遞迴（呼叫端負責先 asdict）
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (set, frozenset)):
        return sorted([normalize_value(v) for v in value], key=lambda x: str(x))
    if isinstance(value, dict):
        return {str(k): normalize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_value(v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    if isinstance(value, (str, int, float, bool)):
        return value
    logger.debug("normalize_value | 未知型別 %s 走 str() fallback", type(value).__name__)
    return str(value)


def normalize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """將整個 dict 正規化（key→str, value→normalize_value）。"""
    if data is None:
        return {}
    return {str(k): normalize_value(v) for k, v in data.items()}


def diff_normalized(left: dict[str, Any], right: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """比對兩個已正規化 dict 的欄位差異。

    Returns:
        {field_path: {"left": ..., "right": ...}} — 僅含不一致欄位
    """
    left_n = normalize_dict(left)
    right_n = normalize_dict(right)
    keys = set(left_n.keys()) | set(right_n.keys())
    drift: dict[str, dict[str, Any]] = {}
    for k in sorted(keys):
        lv = left_n.get(k)
        rv = right_n.get(k)
        if lv != rv:
            drift[k] = {"left": lv, "right": rv}
    return drift


__all__ = ["normalize_value", "normalize_dict", "diff_normalized"]
