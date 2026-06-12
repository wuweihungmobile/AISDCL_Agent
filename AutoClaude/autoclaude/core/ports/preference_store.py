"""IPreferenceStore — 使用者偏好記憶 Port（F-C1 / ADR-AGT-003 L3）。

Improving_012 Phase 1（SCG-1 凍結於 SRD_AGT_Phase1_Memory.md §2.1）：
  - FilePreferenceStore（yaml_only）落地 `preferences.jsonl`（append + last-wins）
  - PgPreferenceStore（both/db_only）落地 `user_preferences` 表（alembic 0016，UPSERT）
  - scope: "global" 或 "playbook:{project}"；讀取時 playbook scope 覆寫 global
  - value: str（複雜值由呼叫端 JSON 編碼；不做泛型序列化）

寫入僅由確定性程式碼路徑執行（config seed / API）；Brain 輸出不得自動回寫
（ADR-AGT-003 §2 原則 3，防自我放大）。

設計原則（data tier ≤ 150）：純 Protocol，零實作、零外部依賴。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IPreferenceStore(Protocol):
    """使用者偏好 key-value 儲存抽象（L3 記憶層）。"""

    def get(self, key: str, scope: str = "global") -> str | None:
        """讀取單一偏好；不存在回 None（不做 scope fallback，由呼叫端決定）。"""

    def set(self, key: str, value: str, scope: str = "global") -> None:
        """寫入/覆寫偏好（last-wins / UPSERT 語意）。"""

    def list(self, scope: str | None = None) -> dict[str, str]:
        """列出偏好。scope=None 回所有 scope 合併視圖（playbook:* 覆寫 global 同名鍵）；
        指定 scope 時僅回該 scope。"""


__all__ = ["IPreferenceStore"]
