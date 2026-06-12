"""SD_Improving_06 W0-T0-2 配套契約測試：PII 三態分類 ENUM

對應 G0 驗證命令：
    python -m pytest tests/contract/test_pii_classification.py -v   # ≥ 6 case

驗證面向：
    1. 三態 + 兩個 RESERVED 後擴位皆存在
    2. ENUM 序列化為 str（避免 alembic / Pydantic round-trip 陷阱）
    3. PIIFilterAction 動作表完整對應所有 ENUM 成員
    4. is_active_classification 對 RESERVED 後擴位返回 False
    5. PIIFilterAction 的動作字串為已知 ID（passthrough / mask / drop / abort）
"""
from __future__ import annotations

import pytest

from autoclaude.models.pii_classification import (
    PIIClassification,
    PIIFilterAction,
    is_active_classification,
)


class TestPIIClassificationEnum:
    def test_three_active_classifications_exist(self) -> None:
        assert PIIClassification.NORMAL.value == "normal"
        assert PIIClassification.PII.value == "pii"
        assert PIIClassification.SECRET.value == "secret"

    def test_reserved_slots_exist(self) -> None:
        """RESERVED 後擴位必須存在（PM #11 hybrid 預留）。"""
        assert PIIClassification.RESERVED_1.value == "_reserved_1"
        assert PIIClassification.RESERVED_2.value == "_reserved_2"

    def test_str_subclass_for_serialization(self) -> None:
        """str 子類別 → JSON / YAML 直接持久化為字串。"""
        assert isinstance(PIIClassification.PII, str)
        assert PIIClassification.PII == "pii"

    def test_filter_action_table_covers_all_members(self) -> None:
        """W3 過濾器 SSOT：動作表必須覆蓋所有 ENUM 成員。"""
        for member in PIIClassification:
            assert member in PIIFilterAction, f"{member} 未在動作表中"

    def test_filter_actions_are_known_ids(self) -> None:
        """動作字串必須為已知 ID（防 typo）。"""
        known = {"passthrough", "mask", "drop", "abort"}
        for action in PIIFilterAction.values():
            assert action in known, f"unknown action: {action}"

    def test_reserved_classifications_are_not_active(self) -> None:
        """W0 寫入規則：RESERVED 後擴位禁止生產使用。"""
        assert not is_active_classification(PIIClassification.RESERVED_1)
        assert not is_active_classification(PIIClassification.RESERVED_2)

    def test_active_classifications_are_active(self) -> None:
        assert is_active_classification(PIIClassification.NORMAL)
        assert is_active_classification(PIIClassification.PII)
        assert is_active_classification(PIIClassification.SECRET)

    @pytest.mark.parametrize(
        "member,expected_action",
        [
            (PIIClassification.NORMAL, "passthrough"),
            (PIIClassification.PII, "mask"),
            (PIIClassification.SECRET, "drop"),
            (PIIClassification.RESERVED_1, "abort"),
            (PIIClassification.RESERVED_2, "abort"),
        ],
    )
    def test_each_member_maps_to_expected_action(
        self, member: PIIClassification, expected_action: str
    ) -> None:
        """三態 + 兩 RESERVED 後擴位 → 對應動作明確。"""
        assert PIIFilterAction[member] == expected_action
