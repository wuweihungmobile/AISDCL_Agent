"""IGoalFreezeGate — 自主拆解草稿的「有界自動凍結 signoff」Port（A 協作 L4 / improving_57）。

improving_57 A 軌（柱③雙向協作，北極星第 3 點）：把 goal→playbook 端到端的人工膠水
（GoalDecomposer.approve 的 🔴 手動 signoff）升級為「有界、可稽核、fail-closed 回退人工」
的自動凍結 signoff——當且僅當可機械證明的有界條件全部成立時自動放行，否則一律拒絕並
回退 🔴 人工 signoff（絕不弱化人工棘輪，僅在可證安全的子集上自動化）。

成熟度語意（AutoSDD_Maturity_Rubric）：
  L3 = 每次釋出皆需人工 signoff（決策在人）
  L4 = 在有界、可稽核、可解釋條件成立時自動決策（決策有界自動 + 全程審計），
       條件不成立 fail-closed 回退人工 → 既自治又不失控（XAI 第一等公民）

設計原則（data tier ≤ 150）：純 Protocol + frozen dataclass，零實作、零外部依賴；
gate 只收原語（goal_hash / step_count / prompts），不 import execution 層
（保 core-purity contract #2：core 不依賴 execution）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class FreezeVerdict:
    """自動凍結裁決（不可變、可解釋）。

    auto_approved: 是否准予自動 signoff 放行
    reason:        裁決理由（人類可讀，審計 + XAI 用）
    conditions:    本次檢查通過/未過的有界條件清單（拓樸可審，杜絕黑箱放行）
    """

    auto_approved: bool
    reason: str
    conditions: tuple[str, ...] = ()


@runtime_checkable
class IGoalFreezeGate(Protocol):
    """拆解草稿自動凍結 signoff 抽象（A 協作 L4）。

    evaluate 為純本地有界判定（不呼叫 Brain、無外部 I/O）：僅在可機械證明之有界
    條件全部成立時回 auto_approved=True；任一不成立即 False（fail-closed 回退人工）。
    """

    def evaluate(
        self, *, goal_hash: str, step_count: int, prompts: tuple[str, ...]
    ) -> FreezeVerdict:
        """裁決是否准予自動 signoff；條件不足一律拒絕，回退 🔴 人工 signoff。"""


__all__ = ["IGoalFreezeGate", "FreezeVerdict"]
