"""BGEM3LocalAdapter — IEmbedder 的本地 TEI 容器實作（SD_Improving_06 W3-T3-18）。

對應規格：
  - SD_Improving_06.md §9.1 PM #1 拍板：BGE-M3 1024 維預設
  - .env.example：TEI_URL / TEI_MODEL_ID / TEI_EMBED_DIMENSIONS=1024
  - PM #9：embedding_status 三態 + 5 次告警（retry 政策見 service 層 T3-21）

設計重點：
  - 同步 HTTP（httpx.Client）：W3 階段 1 與 sync runner 一致
  - dimension SSOT：建構時鎖死 1024，回傳維度不符即 raise
  - health_check() 不拋例外（內部捕獲後填入 healthy=False + detail）
  - 與 TEI（Text Embeddings Inference）相容：POST /embed body={"inputs": [...]}
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

from ...core.ports.embedder import (
    EmbedderDimensionMismatchError,
    EmbedderHealth,
    EmbedderUnavailableError,
)


class BGEM3LocalAdapter:
    """IEmbedder 實作：本地 TEI 容器 + BGE-M3（1024 維）。"""

    _BACKEND = "bge_m3_local"
    _DEFAULT_DIM = 1024

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model_id: str = "BAAI/bge-m3",
        dimension: int = _DEFAULT_DIM,
        timeout_seconds: float = 30.0,
        http_client: Any = None,
    ) -> None:
        self.dimension = int(dimension)
        self.model_id = model_id
        self._base_url = (
            base_url
            or os.environ.get("TEI_URL")
            or "http://localhost:8080"
        ).rstrip("/")
        self._timeout = timeout_seconds
        # http_client 注入點供測試 mock；正式使用 httpx.Client（lazy import 避免裝置缺套件即崩）
        self._client = http_client

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise EmbedderUnavailableError(
                "httpx 未安裝；請 pip install httpx 或注入 http_client 進行測試"
            ) from exc
        self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def embed_one(self, text: str) -> list[float]:
        if not text or not isinstance(text, str):
            raise ValueError("text 必須為非空字串")
        result = self.embed([text])
        return result[0]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(t, str) or not t for t in texts):
            raise ValueError("texts 內容必須全為非空字串")

        client = self._get_client()
        try:
            resp = client.post(
                f"{self._base_url}/embed",
                json={"inputs": texts},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise EmbedderUnavailableError(
                f"TEI {self._base_url} 不可用：{exc}"
            ) from exc

        # TEI /embed 回傳格式：[[float, ...], [float, ...]]
        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbedderUnavailableError(
                f"TEI 回傳格式異常：expected list of {len(texts)} vectors, got {type(data)}"
            )

        vectors: list[list[float]] = []
        for i, vec in enumerate(data):
            if not isinstance(vec, list):
                raise EmbedderUnavailableError(
                    f"TEI vector[{i}] 不是 list：{type(vec)}"
                )
            if len(vec) != self.dimension:
                raise EmbedderDimensionMismatchError(
                    f"TEI vector[{i}] dim={len(vec)} ≠ declared {self.dimension}"
                )
            vectors.append([float(x) for x in vec])
        return vectors

    def health_check(self) -> EmbedderHealth:
        start = time.perf_counter()
        try:
            client = self._get_client()
            resp = client.get(f"{self._base_url}/health")
            resp.raise_for_status()
            latency_ms = (time.perf_counter() - start) * 1000.0
            return EmbedderHealth(
                healthy=True,
                backend=self._BACKEND,
                dimension=self.dimension,
                latency_ms=latency_ms,
                detail="ok",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return EmbedderHealth(
                healthy=False,
                backend=self._BACKEND,
                dimension=self.dimension,
                latency_ms=latency_ms,
                detail=f"{type(exc).__name__}: {exc}",
            )
