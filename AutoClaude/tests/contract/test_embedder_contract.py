"""SD_Improving_06 W3-T3-25 — IEmbedder Port 契約測試（AC4-1）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-1：BGEM3LocalAdapter.dimension == 1024
  - autoclaude/core/ports/embedder.py 介面契約
  - 雙 adapter 對齊：BGE-M3 預設 + Minimax 備援

驗證項目（≥ 6 case）：
  T1 IEmbedder Protocol runtime_checkable 結構（dimension / model_id / embed / embed_one / health_check）
  T2 BGEM3LocalAdapter.dimension == 1024 預設
  T3 BGEM3LocalAdapter 注入 fake httpx → 回傳 list[list[float]] 順序保留
  T4 BGEM3LocalAdapter 維度不符 → EmbedderDimensionMismatchError
  T5 MinimaxEmbedderAdapter API key 缺 → EmbedderUnavailableError
  T6 MinimaxEmbedderAdapter dimension 與 BGE-M3 對齊（預設 1024）
  T7 BGEM3LocalAdapter.health_check() 不可拋例外（內部捕獲）
  T8 BGEM3LocalAdapter embed_one 空字串 → ValueError
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from autoclaude.core.ports.embedder import (
    EmbedderDimensionMismatchError,
    EmbedderHealth,
    EmbedderUnavailableError,
    IEmbedder,
)
from autoclaude.infra.adapters.bgem3_local import BGEM3LocalAdapter
from autoclaude.infra.adapters.minimax_embedder import MinimaxEmbedderAdapter


class _FakeResp:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeHttpClient:
    def __init__(self, post_payload: Any = None, get_payload: Any = None, raise_on_post: bool = False) -> None:
        self.post_payload = post_payload
        self.get_payload = get_payload
        self.raise_on_post = raise_on_post
        self.calls: list[tuple[str, dict]] = []

    def post(self, url: str, json: dict = None, headers: dict = None) -> _FakeResp:  # noqa: A002
        self.calls.append((url, json or {}))
        if self.raise_on_post:
            raise RuntimeError("simulated network error")
        return _FakeResp(self.post_payload)

    def get(self, url: str) -> _FakeResp:
        return _FakeResp(self.get_payload or {"ok": True})


def test_iembedder_protocol_runtime_check():
    """T1 IEmbedder Protocol 結構檢查；缺方法的物件不通過。"""
    adapter = BGEM3LocalAdapter(http_client=_FakeHttpClient())
    assert isinstance(adapter, IEmbedder)


def test_bge_dimension_default_1024():
    """T2 BGE-M3 預設維度鎖死 1024（AC4-1 SSOT）。"""
    adapter = BGEM3LocalAdapter(http_client=_FakeHttpClient())
    assert adapter.dimension == 1024


def test_bge_embed_preserves_order_and_count():
    """T3 batch embed 回傳順序與筆數需對齊輸入。"""
    fake = _FakeHttpClient(post_payload=[
        [0.0] * 1024,
        [0.1] * 1024,
        [0.2] * 1024,
    ])
    adapter = BGEM3LocalAdapter(http_client=fake)
    vecs = adapter.embed(["a", "b", "c"])
    assert len(vecs) == 3
    assert all(len(v) == 1024 for v in vecs)
    assert vecs[1][0] == pytest.approx(0.1)


def test_bge_dim_mismatch_raises():
    """T4 TEI 回傳維度不符 → EmbedderDimensionMismatchError（防髒資料）。"""
    fake = _FakeHttpClient(post_payload=[[0.0] * 512])
    adapter = BGEM3LocalAdapter(http_client=fake)
    with pytest.raises(EmbedderDimensionMismatchError):
        adapter.embed_one("hi")


def test_minimax_missing_api_key(monkeypatch):
    """T5 Minimax API key 缺 → 觸發 breaker.failure + raise（不可悄悄繼續）。"""
    # hermetic（取證紀律 #16）：adapter 對 api_key="" 會 fallback 到環境變數
    # （minimax_embedder.py:44 `api_key or os.environ.get("MINIMAX_API_KEY")`），
    # 故須清除 ambient MINIMAX_API_KEY，否則開發者 shell export 或 act 載入 repo .env
    # 時，env 內真實 key 會讓本測試偽 fail（DID NOT RAISE）。
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    fake = _FakeHttpClient(post_payload={"vectors": [[0.0] * 1024]})
    adapter = MinimaxEmbedderAdapter(
        api_key="",
        group_id="G1",
        http_client=fake,
    )
    with pytest.raises(EmbedderUnavailableError):
        adapter.embed_one("hi")


def test_minimax_default_dim_aligns_with_bge():
    """T6 Minimax 預設維度 1024（與 BGE-M3 對齊；env 未實測時的安全預設）。"""
    adapter = MinimaxEmbedderAdapter(
        api_key="dummy",
        group_id="G1",
        http_client=_FakeHttpClient(),
    )
    assert adapter.dimension == 1024


def test_bge_health_check_swallows_exception():
    """T7 health_check() 不可拋例外；後端壞掉時應回 healthy=False。"""
    fake = _FakeHttpClient()

    def _raise_get(_url):
        raise RuntimeError("connection refused")

    fake.get = _raise_get  # type: ignore[assignment]
    adapter = BGEM3LocalAdapter(http_client=fake)
    h = adapter.health_check()
    assert isinstance(h, EmbedderHealth)
    assert h.healthy is False
    assert "RuntimeError" in h.detail


def test_bge_embed_one_empty_text_raises_value_error():
    """T8 空字串輸入 → ValueError（防止寫入路徑誤入空 prompt）。"""
    adapter = BGEM3LocalAdapter(http_client=_FakeHttpClient())
    with pytest.raises(ValueError):
        adapter.embed_one("")


def test_minimax_breaker_records_failure_on_http_error():
    """T9 Minimax HTTP 失敗時 breaker 累積失敗計數。"""
    fake = _FakeHttpClient(raise_on_post=True)
    adapter = MinimaxEmbedderAdapter(
        api_key="dummy",
        group_id="G1",
        http_client=fake,
    )
    for _ in range(3):
        with pytest.raises(EmbedderUnavailableError):
            adapter.embed_one("hi")
    assert adapter.breaker.state == "open"
