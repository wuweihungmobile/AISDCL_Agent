"""IVectorSearch — pgvector HNSW 查詢抽象 Port（SD_Improving_06 W3-T3-17）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-5（recall@10 ≥ 0.95 + p95 < 50ms）
  - SD_Improving_06.md §6 表 0008 partial HNSW per model_id + dual-read
  - SD_Improving_06.md §6.5 + §11 黃線：fallback_query_path（CircuitBreaker latency > 200ms 降級）

設計原則：
  - 與 IEmbedder 分離：search 端不負責 embed，由呼叫端先 embed 再傳向量
  - VectorHit 為 frozen dataclass（serializable，可直接寫 audit / drift_log）
  - search() 接受 namespace（決定表 / partition），fallback 邏輯下沉 adapter

實作（W3 階段 C）：
  - autoclaude.infra.adapters.pg_vector_search.PgVectorSearchAdapter（W4+ 視需要補；
    W3 階段保留 Port 並由寫入路徑/recall 測試以 mock 驗證契約）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Protocol, runtime_checkable

Namespace = Literal[
    "knowledge_entries",
    "goal_tasks",
    "execution_items",
]


class VectorSearchError(Exception):
    """Vector search 通用錯誤基底類。"""


@dataclass(frozen=True)
class VectorHit:
    """單筆檢索結果（frozen 以利序列化 / drift_log）。

    欄位：
      id            主鍵（uuid / int / str，由 namespace 決定）
      score         相似度分數（cosine 距離→similarity，越大越相似）
      model_id      命中向量的 embedding_model_id（dual-read 時可能為舊或新）
      payload       附加 metadata（title / status 等，供 caller 直接顯示）
      source        ``new`` (halfvec 1024) / ``legacy`` (vector 1536) / ``mock``
    """
    id: str
    score: float
    model_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: Literal["new", "legacy", "mock"] = "new"


@dataclass(frozen=True)
class SearchStats:
    """search() 附帶量測（供 SLO 告警 / fallback 觸發判斷）。"""
    latency_ms: float
    used_fallback: bool
    candidate_count: int
    backend_index: str = ""  # 例如 ``idx_kb_embedding_v_hnsw_2026_05``


@runtime_checkable
class IVectorSearch(Protocol):
    """pgvector HNSW 查詢契約。"""

    def search(
        self,
        *,
        namespace: Namespace,
        query_vector: list[float],
        model_id: str,
        top_k: int = 10,
        ef_search: Optional[int] = None,
        extra_filters: Optional[dict[str, Any]] = None,
    ) -> tuple[list[VectorHit], SearchStats]:
        """執行 HNSW 查詢。

        Args:
            namespace: 目標表（決定 SQL 表名 / HNSW index）
            query_vector: 查詢向量（dimension 必對齊 model_id 註冊維度）
            model_id: 過濾鍵；dual-read 期間可傳 ``"*"`` 表雙模型並讀
            top_k: 回傳前 K 筆
            ef_search: HNSW ``ef_search``（None=用 PG 預設）
            extra_filters: 額外 WHERE 條件（status / project_id 等）

        Returns:
            (hits, stats)；hits 依 score DESC 排序。

        Raises:
            VectorSearchError: 後端錯誤（網路 / SQL）
        """
        ...

    def health_check(self) -> bool:
        """簡單探活；用於 fallback 路徑判斷。"""
        ...
