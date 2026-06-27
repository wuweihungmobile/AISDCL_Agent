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
from autoclaude.utils.config import EmbedderConfig


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


def test_bge_dimension_default_1024(monkeypatch):
    """T2 BGE-M3 預設維度鎖死 1024（AC4-1 SSOT）。

    hermetic（improving_92 起 adapter 會讀 TEI_EMBED_DIMENSIONS env）：須清 ambient env，
    否則開發者 shell export TEI_EMBED_DIMENSIONS=512 時本測試偽 fail。
    """
    monkeypatch.delenv("TEI_EMBED_DIMENSIONS", raising=False)
    adapter = BGEM3LocalAdapter(http_client=_FakeHttpClient())
    assert adapter.dimension == 1024


def test_bge_embed_preserves_order_and_count(monkeypatch):
    """T3 batch embed 回傳順序與筆數需對齊輸入。"""
    monkeypatch.delenv("TEI_EMBED_DIMENSIONS", raising=False)  # hermetic：見 T2 說明
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


def test_bge_dim_mismatch_raises(monkeypatch):
    """T4 TEI 回傳維度不符 → EmbedderDimensionMismatchError（防髒資料）。"""
    monkeypatch.delenv("TEI_EMBED_DIMENSIONS", raising=False)  # hermetic：見 T2 說明
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


# ─────────────────────────────────────────────
# improving_91 W-91-2/3：embedder 設定來源優先序（建構參數 > env > config 兜底 > 硬編）
# ─────────────────────────────────────────────

def test_embedder_no_config_backward_compat(monkeypatch):
    """RTM-91-4：config=None（現有所有呼叫端形態）時行為與改版前 byte-level 一致。

    WHY：W-91-2 新增 config 參數必須 additive——若不傳 config，兜底鏈須塌回原
    `or env or 硬編`，否則所有既有呼叫端（皆不傳 config）會行為漂移＝退化。
    清 ambient env 確保斷言的是「硬編預設」而非開發者 shell 殘留值。
    """
    for k in ("MINIMAX_EMBED_BASE_URL", "MINIMAX_EMBED_MODEL", "MINIMAX_EMBED_DIMENSIONS"):
        monkeypatch.delenv(k, raising=False)
    adapter = MinimaxEmbedderAdapter(api_key="dummy", group_id="G1", http_client=_FakeHttpClient())
    # 改版前硬編預設：base_url=api.minimax.io/v1/embeddings、model=embo-01、dim=1024、timeout=30.0
    assert adapter._base_url == "https://api.minimax.io/v1/embeddings"
    assert adapter.model_id == "embo-01"
    assert adapter.dimension == 1024
    assert adapter._timeout == 30.0
    # api_key / group_id 兜底鏈亦本輪改動（api_key 新增 config 分支）：config=None + 顯式參數時，
    # 參數須最優先穿透（坐實「byte-level 零退化」涵蓋全 6 欄，非僅前 4 欄）。
    assert adapter._api_key == "dummy"
    assert adapter._group_id == "G1"


def test_embedder_config_fallback_when_no_env(monkeypatch):
    """RTM-91-3：env 缺席時 config 兜底生效（env > config 之 config 端）。

    WHY：方案 B 的核心價值＝非機密 embedder 設定可集中於 config.yaml。若 config 兜底
    不生效，使用者填了 config.yaml 卻無效＝治理目標落空。
    """
    for k in ("MINIMAX_EMBED_BASE_URL", "MINIMAX_EMBED_MODEL", "MINIMAX_EMBED_DIMENSIONS"):
        monkeypatch.delenv(k, raising=False)
    cfg = EmbedderConfig(
        base_url="https://cfg.example/embeddings",
        model="cfg-model",
        dimension=768,
        timeout_seconds=12.5,
    )
    adapter = MinimaxEmbedderAdapter(api_key="dummy", group_id="G1", config=cfg,
                                     http_client=_FakeHttpClient())
    assert adapter._base_url == "https://cfg.example/embeddings"
    assert adapter.model_id == "cfg-model"
    assert adapter.dimension == 768
    assert adapter._timeout == 12.5


def test_embedder_env_overrides_config(monkeypatch):
    """RTM-91-3：env 優先於 config（與 chat env>config 治理一致）。

    WHY：env 是臨時覆寫管道（切區域/換 model）；若 config 蓋過 env，臨時覆寫失效。
    """
    monkeypatch.setenv("MINIMAX_EMBED_BASE_URL", "https://env.example/embeddings")
    monkeypatch.setenv("MINIMAX_EMBED_MODEL", "env-model")
    monkeypatch.setenv("MINIMAX_EMBED_DIMENSIONS", "256")
    cfg = EmbedderConfig(base_url="https://cfg.example/x", model="cfg-model", dimension=768)
    adapter = MinimaxEmbedderAdapter(api_key="dummy", group_id="G1", config=cfg,
                                     http_client=_FakeHttpClient())
    assert adapter._base_url == "https://env.example/embeddings"
    assert adapter.model_id == "env-model"
    assert adapter.dimension == 256


def test_embedder_ctor_arg_overrides_env_and_config(monkeypatch):
    """RTM-91-3：建構參數最高優先（> env > config）。

    WHY：顯式注入（如測試 fixture / DualEmbedderRouter 組裝）必須能完全主導，
    否則無法在不污染 env 的前提下精準建構特定 adapter。
    """
    monkeypatch.setenv("MINIMAX_EMBED_MODEL", "env-model")
    cfg = EmbedderConfig(model="cfg-model")
    adapter = MinimaxEmbedderAdapter(api_key="dummy", group_id="G1", model_id="arg-model",
                                     config=cfg, http_client=_FakeHttpClient())
    assert adapter.model_id == "arg-model"


def test_embedder_model_from_env(monkeypatch):
    """RTM-91-5 / DEF-91-002：MINIMAX_EMBED_MODEL env 真正被讀取（先前硬編、env 失效）。

    WHY：.env.example 白紙黑字宣告 MINIMAX_EMBED_MODEL，但修復前 adapter `model_id`
    為簽章硬編預設、__init__ 從不讀該 env——文件宣稱可配置實則不可。本測試鎖死
    「env 設了就生效」，使 DEF-91-002 不會復活（回歸防護）。
    """
    monkeypatch.setenv("MINIMAX_EMBED_MODEL", "embo-02-from-env")
    adapter = MinimaxEmbedderAdapter(api_key="dummy", group_id="G1", http_client=_FakeHttpClient())
    assert adapter.model_id == "embo-02-from-env"


# ─────────────────────────────────────────────
# improving_92 W-92-2/3：bge-m3 本地 TEI 設定來源優先序（方案 B 收尾）
#   建構參數 > env（TEI_URL / TEI_MODEL_ID / TEI_EMBED_DIMENSIONS）> config 兜底 > 硬編
# ─────────────────────────────────────────────

_TEI_ENV_KEYS = ("TEI_URL", "TEI_MODEL_ID", "TEI_EMBED_DIMENSIONS")


def test_bge_no_config_backward_compat(monkeypatch):
    """RTM-92-3：config=None + 無 env（現有所有呼叫端形態）時行為與改版前 byte-level 一致。

    WHY：W-92-2 新增 config 參數 + 補 TEI_MODEL_ID/TEI_EMBED_DIMENSIONS env 讀取必須 additive
    ——若不傳 config 且無 env，兜底鏈須塌回原硬編（base_url=localhost:8080、model=BAAI/bge-m3、
    dim=1024、timeout=30.0），否則所有既有呼叫端（皆不傳 config）會行為漂移＝退化。
    清 ambient TEI env 確保斷言的是「硬編預設」而非開發者 shell 殘留值。
    """
    for k in _TEI_ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    adapter = BGEM3LocalAdapter(http_client=_FakeHttpClient())
    assert adapter._base_url == "http://localhost:8080"
    assert adapter.model_id == "BAAI/bge-m3"
    assert adapter.dimension == 1024
    assert adapter._timeout == 30.0


def test_bge_config_fallback_when_no_env(monkeypatch):
    """RTM-92-2：env 缺席時 config 兜底生效（TEI 非機密設定可集中於 config.yaml）。

    WHY：方案 B 的核心價值＝非機密 embedder 設定可集中於 config.yaml。若 config 兜底不生效，
    使用者填了 config.yaml 的 bge_m3_* 卻無效＝治理目標落空。
    """
    for k in _TEI_ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    cfg = EmbedderConfig(
        bge_m3_url="http://cfg-tei:9090",
        bge_m3_model="bge-m3-cfg",
        bge_m3_dimension=768,
        bge_m3_timeout_seconds=12.5,
    )
    adapter = BGEM3LocalAdapter(config=cfg, http_client=_FakeHttpClient())
    assert adapter._base_url == "http://cfg-tei:9090"
    assert adapter.model_id == "bge-m3-cfg"
    assert adapter.dimension == 768
    assert adapter._timeout == 12.5


def test_bge_env_overrides_config(monkeypatch):
    """RTM-92-2：env 優先於 config（與 chat / minimax embedder env>config 治理一致）。

    WHY：env 是臨時覆寫管道（改 TEI 容器位址 / 換 model）；若 config 蓋過 env，臨時覆寫失效。
    """
    monkeypatch.setenv("TEI_URL", "http://env-tei:7070")
    monkeypatch.setenv("TEI_MODEL_ID", "bge-m3-env")
    monkeypatch.setenv("TEI_EMBED_DIMENSIONS", "256")
    cfg = EmbedderConfig(bge_m3_url="http://cfg-tei:9090", bge_m3_model="bge-m3-cfg",
                         bge_m3_dimension=768)
    adapter = BGEM3LocalAdapter(config=cfg, http_client=_FakeHttpClient())
    assert adapter._base_url == "http://env-tei:7070"
    assert adapter.model_id == "bge-m3-env"
    assert adapter.dimension == 256


def test_bge_ctor_arg_overrides_env_and_config(monkeypatch):
    """RTM-92-2：建構參數最高優先（> env > config）。

    WHY：顯式注入（測試 fixture / DualEmbedderRouter 組裝）必須能完全主導，否則無法在不污染
    env 的前提下精準建構特定 adapter。
    """
    monkeypatch.setenv("TEI_MODEL_ID", "bge-m3-env")
    cfg = EmbedderConfig(bge_m3_model="bge-m3-cfg")
    adapter = BGEM3LocalAdapter(model_id="bge-m3-arg", config=cfg, http_client=_FakeHttpClient())
    assert adapter.model_id == "bge-m3-arg"


def test_bge_model_from_env(monkeypatch):
    """RTM-92-4 / DEF-92-001：TEI_MODEL_ID env 真正被讀取（先前硬編、env 失效）。

    WHY：.env.example 白紙黑字宣告 TEI_MODEL_ID，但修復前 adapter `model_id` 為簽章硬編預設、
    __init__ 從不讀該 env——文件宣稱可配置實則不可。本測試鎖死「env 設了就生效」，使
    DEF-92-001 不會復活（回歸防護；MUT-92-1 驗牙）。
    """
    monkeypatch.delenv("TEI_URL", raising=False)
    monkeypatch.setenv("TEI_MODEL_ID", "bge-m3-large-from-env")
    adapter = BGEM3LocalAdapter(http_client=_FakeHttpClient())
    assert adapter.model_id == "bge-m3-large-from-env"


def test_bge_dimension_from_env(monkeypatch):
    """RTM-92-5 / DEF-92-002：TEI_EMBED_DIMENSIONS env 真正被讀取（先前硬編、env 失效）。

    WHY：.env.example 宣告 TEI_EMBED_DIMENSIONS，但修復前 adapter `dimension` 為簽章硬編預設、
    __init__ 從不讀該 env。本測試鎖死「env 設了就生效」，使 DEF-92-002 不會復活
    （回歸防護；MUT-92-2 驗牙）。非數字 env 應被忽略（`.isdigit()` 檢核）回退預設。
    """
    monkeypatch.delenv("TEI_URL", raising=False)
    monkeypatch.setenv("TEI_EMBED_DIMENSIONS", "512")
    adapter = BGEM3LocalAdapter(http_client=_FakeHttpClient())
    assert adapter.dimension == 512
