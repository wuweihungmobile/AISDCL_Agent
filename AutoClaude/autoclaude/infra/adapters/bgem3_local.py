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
from ...utils.config import EmbedderConfig


class BGEM3LocalAdapter:
    """IEmbedder 實作：本地 TEI 容器 + BGE-M3（1024 維）。"""

    _BACKEND = "bge_m3_local"
    _DEFAULT_DIM = 1024

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
        dimension: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        config: Optional[EmbedderConfig] = None,
        http_client: Any = None,
    ) -> None:
        # 設定來源優先序（improving_92 W-92-2，對齊 improving_91 minimax_embedder 治理）：
        #   建構參數 > env > config 兜底 > 硬編預設。config=None + 無 env 時兜底鏈塌回硬編
        #   （byte-level 零退化：model_id=BAAI/bge-m3、dimension=1024、base_url 硬編、timeout=30.0）。
        # model：DEF-92-001 修復——補 TEI_MODEL_ID env 讀取（先前簽章硬編、env 從未生效）
        self.model_id = (
            model_id
            or os.environ.get("TEI_MODEL_ID")
            or (config.bge_m3_model if config else None)
            or "BAAI/bge-m3"
        )
        self._base_url = (
            base_url
            or os.environ.get("TEI_URL")
            or (config.bge_m3_url if config else None)
            or "http://localhost:8080"
        ).rstrip("/")
        # dimension：DEF-92-002 修復——補 TEI_EMBED_DIMENSIONS env 讀取（先前簽章硬編、env 從未生效）
        dim_env = os.environ.get("TEI_EMBED_DIMENSIONS", "").strip()
        if dimension is not None:
            self.dimension = int(dimension)
        elif dim_env.isdigit():
            self.dimension = int(dim_env)
        elif config is not None:
            self.dimension = int(config.bge_m3_dimension)
        else:
            self.dimension = self._DEFAULT_DIM
        # timeout：參數 > config 兜底 > 硬編 30.0
        if timeout_seconds is not None:
            self._timeout = timeout_seconds
        elif config is not None:
            self._timeout = config.bge_m3_timeout_seconds
        else:
            self._timeout = 30.0
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
