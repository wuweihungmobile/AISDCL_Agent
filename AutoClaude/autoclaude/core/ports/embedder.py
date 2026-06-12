"""IEmbedder — Embedding 模型抽象 Port（SD_Improving_06 W3-T3-16）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-1 ~ AC4-3
  - ADR-SD06-001 §6.2 BrainCapabilities.dimension 對齊
  - PM #1 拍板：C 方案 IEmbedder port + 雙 adapter（BGE-M3 1024 維預設 + Minimax API 備援）

設計原則：
  - Protocol structural typing；adapter 不需顯式繼承
  - 同步介面（W3 階段 1，避免 asyncio 漣漪到 sync runner）；W4+ 視需要再補 async
  - dimension / model_id 屬性 SSOT，供寫入路徑 (T3-20) 與 contract 測試 (T3-25) 對齊

實作（W3 階段 B/C）：
  - autoclaude.infra.adapters.bgem3_local.BGEM3LocalAdapter (BGE-M3 1024 維本地 TEI 容器)
  - autoclaude.infra.adapters.minimax_embedder.MinimaxEmbedderAdapter (Minimax embo-01 備援)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class EmbedderError(Exception):
    """Embedder 通用錯誤基底類。"""


class EmbedderUnavailableError(EmbedderError):
    """後端服務不可用（網路 / 連線 / 健康檢查失敗）。

    觸發 CircuitBreaker 切換備援 adapter（見 T3-19）。
    """


class EmbedderDimensionMismatchError(EmbedderError):
    """回傳向量維度與宣告 dimension 不符（防止髒資料污染 pgvector 欄位）。"""


@dataclass(frozen=True)
class EmbedderHealth:
    """health_check() 回傳值。"""
    healthy: bool
    backend: str
    dimension: int
    latency_ms: float
    detail: str = ""


@runtime_checkable
class IEmbedder(Protocol):
    """Embedding 模型契約（W3 階段 1 同步版本）。

    必要屬性：
      dimension : int   — 向量維度（必對齊 alembic 0008 halfvec(N) 欄寬）
      model_id  : str   — 模型識別碼（寫入 embedding_model_id 欄位作 filter 鍵）

    必要方法：
      embed_one(text)   → list[float]
      embed(texts)      → list[list[float]]
      health_check()    → EmbedderHealth
    """

    dimension: int
    model_id: str

    def embed_one(self, text: str) -> list[float]:
        """單筆文字 → 向量。

        Raises:
            EmbedderUnavailableError: 後端不可用
            EmbedderDimensionMismatchError: 維度不符
            ValueError: text 為空字串
        """
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批次 → 向量陣列。失敗模式同 embed_one；保留輸入順序。"""
        ...

    def health_check(self) -> EmbedderHealth:
        """探活；不可拋例外（內部捕獲後填入 healthy=False + detail）。"""
        ...
