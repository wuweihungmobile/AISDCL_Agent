"""MinimaxEmbedderAdapter — IEmbedder 的 Minimax embo-01 API 實作（SD_Improving_06 W3-T3-19）。

對應規格：
  - SD_Improving_06.md §9.1 PM #1 拍板：BGE-M3 預設 + Minimax 備援（雙 adapter）
  - SD_Improving_06.md §11 黃線：CircuitBreaker 連續 3 fail → 切備援 < 60s
  - .env.example：MINIMAX_EMBED_BASE_URL / MINIMAX_EMBED_MODEL / MINIMAX_GROUP_ID / MINIMAX_EMBED_DIMENSIONS

設計重點：
  - dimension 經 .env / 建構參數注入（未實測 embo-01 維度時呼叫端必填）
  - GroupId 必填（API 必須以 query param 傳遞，否則 base_resp 錯誤）
  - 內含 CircuitBreaker：HTTP 失敗 / latency > 200ms 累積觸發
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
from .circuit_breaker import CircuitBreaker


class MinimaxEmbedderAdapter:
    """IEmbedder 實作：Minimax embo-01（HTTP API）+ CircuitBreaker。"""

    _BACKEND = "minimax_api"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
        dimension: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        config: Optional[EmbedderConfig] = None,
        http_client: Any = None,
        breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        # 設定來源優先序（improving_91 W-91-2，對齊 chat env>config 治理）：
        #   建構參數 > env > config 兜底 > 硬編預設。config=None 時兜底鏈塌回原 or 鏈（byte-level 零退化）。
        self._api_key = (
            api_key
            or os.environ.get("MINIMAX_API_KEY")
            or (config.api_key if config else None)
            or ""
        )
        # group_id 為帳號識別（機密邊界，見 EmbedderConfig docstring）：維持只走參數 / env，不吃 config
        self._group_id = group_id or os.environ.get("MINIMAX_GROUP_ID", "")
        self._base_url = (
            base_url
            or os.environ.get("MINIMAX_EMBED_BASE_URL")
            or (config.base_url if config else None)
            or "https://api.minimax.io/v1/embeddings"
        )
        # model：DEF-91-002 修復——補 MINIMAX_EMBED_MODEL env 讀取 + config 兜底（先前簽章硬編 embo-01、env 從未生效）
        self.model_id = (
            model_id
            or os.environ.get("MINIMAX_EMBED_MODEL")
            or (config.model if config else None)
            or "embo-01"
        )
        # dimension：優先建構參數 → env → config 兜底 → 預設 1024（與 BGE-M3 對齊）
        dim_env = os.environ.get("MINIMAX_EMBED_DIMENSIONS", "").strip()
        if dimension is not None:
            self.dimension = int(dimension)
        elif dim_env.isdigit():
            self.dimension = int(dim_env)
        elif config is not None:
            self.dimension = int(config.dimension)
        else:
            self.dimension = 1024
        # timeout：參數 > config 兜底 > 硬編 30.0
        if timeout_seconds is not None:
            self._timeout = timeout_seconds
        elif config is not None:
            self._timeout = config.timeout_seconds
        else:
            self._timeout = 30.0
        self._client = http_client
        self.breaker = breaker or CircuitBreaker(
            failure_threshold=3,
            latency_threshold_ms=200.0,
            slow_call_threshold=3,
            recovery_seconds=60.0,
        )

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise EmbedderUnavailableError("httpx 未安裝") from exc
        self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def embed_one(self, text: str) -> list[float]:
        if not text or not isinstance(text, str):
            raise ValueError("text 必須為非空字串")
        return self.embed([text])[0]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(t, str) or not t for t in texts):
            raise ValueError("texts 內容必須全為非空字串")
        if not self.breaker.allow_request():
            raise EmbedderUnavailableError(
                f"Minimax breaker={self.breaker.state}（連續失敗或慢呼叫累積）"
            )
        if not self._api_key:
            self.breaker.record_failure()
            raise EmbedderUnavailableError("MINIMAX_API_KEY 未設定")
        if not self._group_id:
            self.breaker.record_failure()
            raise EmbedderUnavailableError("MINIMAX_GROUP_ID 未設定")

        client = self._get_client()
        url = f"{self._base_url}?GroupId={self._group_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": self.model_id,
            "texts": texts,
            "type": "db",
        }
        start = time.perf_counter()
        try:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            self.breaker.record_failure()
            raise EmbedderUnavailableError(
                f"Minimax API {self._base_url} 不可用：{exc}"
            ) from exc
        latency_ms = (time.perf_counter() - start) * 1000.0

        base_resp = data.get("base_resp", {}) if isinstance(data, dict) else {}
        if base_resp.get("status_code", 0) != 0:
            self.breaker.record_failure()
            raise EmbedderUnavailableError(
                f"Minimax base_resp 失敗：{base_resp}"
            )
        vectors = data.get("vectors") or []
        if len(vectors) != len(texts):
            self.breaker.record_failure()
            raise EmbedderUnavailableError(
                f"Minimax 回傳 {len(vectors)} ≠ inputs {len(texts)}"
            )
        out: list[list[float]] = []
        for i, vec in enumerate(vectors):
            if not isinstance(vec, list) or len(vec) != self.dimension:
                self.breaker.record_failure()
                raise EmbedderDimensionMismatchError(
                    f"Minimax vector[{i}] dim={len(vec) if isinstance(vec, list) else 'NA'} ≠ {self.dimension}"
                )
            out.append([float(x) for x in vec])
        self.breaker.record_success(latency_ms=latency_ms)
        return out

    def health_check(self) -> EmbedderHealth:
        start = time.perf_counter()
        try:
            # 用最短文字觸發一次 embed 當探活；fail 路徑由 embed() 自身寫 breaker
            self.embed_one("ping")
            latency_ms = (time.perf_counter() - start) * 1000.0
            return EmbedderHealth(
                healthy=True,
                backend=self._BACKEND,
                dimension=self.dimension,
                latency_ms=latency_ms,
                detail=f"breaker={self.breaker.state}",
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


class DualEmbedderRouter:
    """雙 adapter fallback router（W3-T3-19 對齊 SD_06 §11 黃線）。

    策略：primary breaker open → 自動切 fallback；fallback 仍 fail 才 raise。
    回傳的 model_id 永遠對應實際命中的 adapter（供寫入路徑 embedding_model_id 欄位）。
    """

    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    @property
    def dimension(self) -> int:
        return self.primary.dimension

    @property
    def model_id(self) -> str:
        return self.primary.model_id

    def _select(self):
        if hasattr(self.primary, "breaker") and not self.primary.breaker.allow_request():
            return self.fallback
        return self.primary

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def embed(self, texts: list[str]) -> list[list[float]]:
        active = self._select()
        try:
            return active.embed(texts)
        except EmbedderUnavailableError:
            other = self.fallback if active is self.primary else self.primary
            return other.embed(texts)

    def health_check(self) -> EmbedderHealth:
        h = self.primary.health_check()
        if h.healthy:
            return h
        return self.fallback.health_check()

    def resolve_active_backend(self) -> str:
        return getattr(self._select(), "_BACKEND", "unknown")
