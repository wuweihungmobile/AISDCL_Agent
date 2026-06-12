"""T6（SD_04 §3 / M-10）：PgStateRepository._run_cache TTLCache + LRU fallback 行為測試。

涵蓋兩條分支：
  - 主路徑：cachetools.TTLCache（maxsize=256, ttl=3600）
  - Fallback：_BoundedLRUCache（maxsize=256，無 TTL，純標準庫 LRU）
"""
from __future__ import annotations

import time

import pytest

from autoclaude.infra.repositories.pg_state_repository import (
    _BoundedLRUCache,
    _make_run_cache,
    _TTLCACHE_AVAILABLE,
)


# ══════════════════════════════════════════════
# Fallback：_BoundedLRUCache
# ══════════════════════════════════════════════

class TestBoundedLRUCacheFallback:
    def test_basic_set_get(self):
        c = _BoundedLRUCache(maxsize=3)
        c["a"] = 1
        c["b"] = 2
        assert c["a"] == 1
        assert c["b"] == 2

    def test_eviction_at_capacity(self):
        """超過 maxsize 時驅逐最舊項。"""
        c = _BoundedLRUCache(maxsize=3)
        c["a"] = 1
        c["b"] = 2
        c["c"] = 3
        c["d"] = 4  # 應驅逐 'a'
        assert "a" not in c
        assert dict(c) == {"b": 2, "c": 3, "d": 4}

    def test_lru_promotion_on_get(self):
        """讀取應將 key 提升為最新（避免被驅逐）。"""
        c = _BoundedLRUCache(maxsize=3)
        c["a"] = 1
        c["b"] = 2
        c["c"] = 3
        _ = c["a"]  # 提升 a 至最新
        c["d"] = 4  # 應驅逐 'b'（次舊）
        assert "a" in c
        assert "b" not in c

    def test_lru_promotion_on_set_existing(self):
        """覆寫既有 key 不應改變 maxsize 行為。"""
        c = _BoundedLRUCache(maxsize=3)
        c["a"] = 1
        c["b"] = 2
        c["a"] = 99  # 重設 a，提升至最新
        c["c"] = 3
        c["d"] = 4  # 應驅逐 'b'
        assert c["a"] == 99
        assert "b" not in c

    def test_pop_clears_order_state(self):
        """pop() 必須同步清理 _order，避免 state 不一致。"""
        c = _BoundedLRUCache(maxsize=3)
        c["a"] = 1
        c["b"] = 2
        c.pop("a")
        assert "a" not in c
        # 加滿到 maxsize 不應誤驅逐已 pop 的 key
        c["c"] = 3
        c["d"] = 4
        assert dict(c) == {"b": 2, "c": 3, "d": 4}

    def test_pop_default_when_missing(self):
        c = _BoundedLRUCache(maxsize=3)
        assert c.pop("missing", "default") == "default"
        assert c.pop("missing", None) is None

    def test_maxsize_one(self):
        """maxsize=1 退化為單元素快取。"""
        c = _BoundedLRUCache(maxsize=1)
        c["a"] = 1
        c["b"] = 2
        assert dict(c) == {"b": 2}

    def test_len_reflects_eviction(self):
        c = _BoundedLRUCache(maxsize=3)
        for i in range(10):
            c[f"k{i}"] = i
        assert len(c) == 3


# ══════════════════════════════════════════════
# 主路徑：TTLCache（cachetools 裝後驗證）
# ══════════════════════════════════════════════

@pytest.mark.skipif(not _TTLCACHE_AVAILABLE, reason="cachetools 未安裝")
class TestTTLCacheMainPath:
    def test_make_run_cache_returns_ttlcache(self):
        from cachetools import TTLCache
        c = _make_run_cache()
        assert isinstance(c, TTLCache)
        assert c.maxsize == 256
        assert c.ttl == 3600

    def test_ttlcache_basic_get_set(self):
        c = _make_run_cache()
        c["pid_1"] = "run_uuid_1"
        assert c["pid_1"] == "run_uuid_1"

    def test_ttlcache_maxsize_eviction(self):
        """TTLCache 容量上限 256 會驅逐舊項。"""
        from cachetools import TTLCache
        # 用較小 maxsize 加速測試
        c = TTLCache(maxsize=3, ttl=3600)
        for i in range(5):
            c[f"k{i}"] = i
        assert len(c) == 3
        # 最舊的 k0 / k1 應已被驅逐
        assert "k0" not in c
        assert "k1" not in c

    def test_ttlcache_ttl_expiry(self):
        """TTL 過期項目自動消失（用短 TTL 驗證）。"""
        from cachetools import TTLCache
        c = TTLCache(maxsize=10, ttl=0.1)  # 100ms TTL
        c["pid_temp"] = "run_x"
        assert "pid_temp" in c
        time.sleep(0.2)  # 等過 TTL
        # 觸發 expire
        with pytest.raises(KeyError):
            _ = c["pid_temp"]


# ══════════════════════════════════════════════
# _make_run_cache：選型保護
# ══════════════════════════════════════════════

class TestMakeRunCacheFactory:
    def test_returns_some_mapping(self):
        c = _make_run_cache()
        # 行為相容：可 setitem / getitem / pop / in
        c["x"] = "y"
        assert c["x"] == "y"
        assert "x" in c
        c.pop("x", None)
        assert "x" not in c

    def test_consistent_type_per_environment(self):
        """同一環境下兩次呼叫應回傳相同型別。"""
        a = _make_run_cache()
        b = _make_run_cache()
        assert type(a) is type(b)
