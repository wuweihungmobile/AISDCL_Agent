"""
⚠️ Phase 5 起 deprecated（@deprecated v2.0）：
   請使用 autoclaude.infra.repositories.FileMemoryStore（IMemoryStore 後端）
   或 InMemoryMemoryStore（測試夾具）。
   保留此 alias 以維持 PlaybookRunner 內部呼叫與既有測試耦合。

FailureKnowledgeBase — 跨 Session 失敗模式快取。

Gap-009-E：以 JSONL 格式儲存已知 error_signature → 有效修正策略的映射，
讓 AutoClaude 在新 Session 中能直接跳至已知有效策略，而非每次從零學習。

儲存路徑：{checkpoint_dir}/failure_knowledge_base.jsonl
查詢 key："{error_class}:{error_signature[:60]}"（最多 72 字）
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .knowledge_base_metrics import KnowledgeBaseMetrics

if TYPE_CHECKING:
    from ..core.ports.kb_metric_store import IKbMetricStore
    from ..core.ports.observability import IObservabilityPort

logger = logging.getLogger("autoclaude.utils.knowledge_base")

_MAX_ENTRIES = 1000  # 防止無限增長


class FailureKnowledgeBase:
    """
    跨 Session 的失敗模式快取。
    儲存格式：每行一個 JSON（JSONL），key 為 error_class:error_signature[:60]（最多 72 字）。

    查詢命中 → 直接跳至歷史有效策略，跳過已知無效策略。
    寫入時機：步驟成功（record_success）或 ESCALATION（record_escalation）。

    SD_08 W4 / ADR-SD08-004 §2.4：可選注入 IObservabilityPort 發送 4 項 metric
      - kb_hit_total counter（tags={"hit": "true|false"}）
      - kb_query_latency_ms histogram
      - kb_strategy_rotation_count counter
      - kb_cache_eviction_count counter
    未注入時 metrics 純記憶體累計，metrics 物件仍可 snapshot() 供測試斷言。
    """

    def __init__(
        self,
        kb_path: str,
        observability: IObservabilityPort | None = None,
        metric_store: IKbMetricStore | None = None,
    ):
        self._path = Path(kb_path)
        self._cache: dict[str, dict] = {}
        # SD_08 W4：4 metric 純記憶體累計（永遠存在；observability 為可選 emit）
        self._metrics = KnowledgeBaseMetrics()
        self._observability = observability
        # F-C3 / ADR-SD09-006：可選注入 IKbMetricStore → 跨 session 持久化（重啟不清零）
        self._metric_store = metric_store
        self._restore_metrics_from_store()
        self._load()

    @property
    def metrics(self) -> KnowledgeBaseMetrics:
        """SD_08 W4：取得 metrics 物件（測試 / monitoring 用）。"""
        return self._metrics

    def metrics_snapshot(self) -> dict:
        """SD_08 W4：與 AutoResumeMetrics 一致的 snapshot 模式。"""
        return self._metrics.snapshot()

    def persist_metrics(self) -> None:
        """F-C3：將 metrics 累計值 flush 至 IKbMetricStore 後端（POST_RUN 觸發）。

        未注入 metric_store 時 no-op（向下相容：原純記憶體行為不變）。
        """
        if self._metric_store is None:
            return
        try:
            self._metric_store.flush()
        except Exception as exc:
            logger.warning("KB metrics persist 失敗（warning，繼續主流程）: %s", exc)

    # F-C3：KnowledgeBaseMetrics 欄位 ↔ IKbMetricStore counter 名稱映射
    _METRIC_NAME_MAP = {
        "total_queries": "kb_queries_total",
        "total_hits": "kb_hits_total",
        "strategy_rotation_count": "kb_strategy_rotation_total",
        "cache_eviction_count": "kb_cache_eviction_total",
    }

    def _restore_metrics_from_store(self) -> None:
        """F-C3：自 metric_store 末筆快照恢復 4 counters（重啟不清零）。

        latency 滑動窗口為短期統計不恢復（SRD_AGT_Phase1_Memory §1.3）。
        """
        if self._metric_store is None:
            return
        try:
            snap = self._metric_store.snapshot()
        except Exception as exc:
            logger.warning("KB metrics 恢復失敗（以零起算）: %s", exc)
            return
        for attr, name in self._METRIC_NAME_MAP.items():
            if name in snap:
                setattr(self._metrics, attr, int(snap[name].value))

    def _record_store_counter(self, attr: str, *, delta: int = 1) -> None:
        """F-C3：counter 變動同步轉送 metric_store（記憶體 buffer，flush 才落地）。"""
        if self._metric_store is None:
            return
        try:
            self._metric_store.record_counter(self._METRIC_NAME_MAP[attr], delta)
        except Exception as exc:
            logger.warning("KB metric_store 轉送失敗: %s", exc)

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        key = entry.get("error_sig", "")
                        if key:
                            self._cache[key] = entry
        except Exception as exc:
            logger.warning("知識庫載入失敗（將以空庫啟動）: %s", exc)

    def query(self, error_signature: str) -> dict | None:
        """查詢已知的錯誤模式。回傳 entry dict 或 None。

        SD_08 W4：每次 query 累計 metrics（hit/miss + latency）+ emit observability。
        """
        key = error_signature[:80]
        start_ns = time.monotonic_ns()
        result = self._cache.get(key)
        latency_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        hit = result is not None
        self._metrics.record_query(hit=hit, latency_ms=latency_ms)
        # F-C3：同步累計至 metric_store buffer（POST_RUN persist_metrics 落地）
        self._record_store_counter("total_queries")
        if hit:
            self._record_store_counter("total_hits")
        if self._metric_store is not None:
            try:
                self._metric_store.record_histogram("kb_query_latency_ms", latency_ms)
            except Exception as exc:
                logger.warning("KB metric_store histogram 轉送失敗: %s", exc)
        if self._observability is not None:
            try:
                self._observability.emit_counter(
                    "kb_hit_total", value=1, tags={"hit": "true" if hit else "false"}
                )
                self._observability.emit_histogram(
                    "kb_query_latency_ms", value=latency_ms
                )
            except (OSError, ValueError, RuntimeError) as exc:
                logger.warning("KB observability emit 失敗（warning，繼續主流程）: %s", exc)
        return result

    def get_strategy_priority(self, error_class: str) -> list[str]:
        """
        Gap-010-F：根據歷史成功記錄，返回針對特定 error_class 的策略優先順序。
        若歷史數據不足（< 3 筆成功），回傳預設順序（PINPOINT→REWRITE→...）。

        SD_08 W4：每次呼叫視為一次策略輪換決策，累計 metrics。
        """
        from ..execution.failure_tracker import STRATEGY_TYPES
        # SD_08 W4：strategy rotation 累計（next_strategy/get_strategy_priority 觸發）
        self._metrics.record_strategy_rotation()
        self._record_store_counter("strategy_rotation_count")
        if self._observability is not None:
            try:
                self._observability.emit_counter(
                    "kb_strategy_rotation_count", tags={"error_class": error_class}
                )
            except (OSError, ValueError, RuntimeError) as exc:
                logger.warning("KB strategy rotation emit 失敗: %s", exc)

        strategy_stats: dict[str, int] = {}
        for entry in self._cache.values():
            if entry.get("outcome") == "success":
                ec = entry.get("error_class", "unknown")
                strat = entry.get("successful_strategy", "")
                if ec == error_class and strat:
                    strategy_stats[strat] = strategy_stats.get(strat, 0) + 1

        if len(strategy_stats) < 3:
            return list(STRATEGY_TYPES)  # 數據不足，使用預設順序

        return sorted(STRATEGY_TYPES, key=lambda s: strategy_stats.get(s, 0), reverse=True)

    def record_success(
        self, error_signature: str, successful_strategy: str, step_id: str,
        error_class: str = "unknown",  # Gap-010-F: 新增 error_class 供元學習使用
    ) -> None:
        """記錄成功修正的策略，供後續 Session 優先使用。"""
        key = error_signature[:80]
        existing_skip = self._cache.get(key, {}).get("skip_strategies", [])
        entry = {
            "error_sig": key,
            "successful_strategy": successful_strategy,
            "error_class": error_class,  # Gap-010-F
            "step_id": step_id,
            "skip_strategies": existing_skip,
            "timestamp": time.time(),
            "outcome": "success",
        }
        self._cache[key] = entry
        self._append(entry)
        logger.debug("知識庫記錄成功: sig=%s strategy=%s", key[:40], successful_strategy)

    def record_escalation(
        self, error_signature: str, failed_strategies: list[str], step_id: str
    ) -> None:
        """記錄 ESCALATION 時所有失敗的策略（供後續 Playbook 跳過）。"""
        key = error_signature[:80]
        existing_skip = self._cache.get(key, {}).get("skip_strategies", [])
        all_failed = list(set(existing_skip + failed_strategies))
        entry = {
            "error_sig": key,
            "successful_strategy": None,
            "step_id": step_id,
            "skip_strategies": all_failed,
            "timestamp": time.time(),
            "outcome": "escalation",
        }
        self._cache[key] = entry
        self._append(entry)
        logger.debug("知識庫記錄 ESCALATION: sig=%s failed=%s", key[:40], all_failed)

    def _append(self, entry: dict) -> None:
        try:
            if len(self._cache) > _MAX_ENTRIES:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                # SD_08 W4：LRU 淘汰累計 metrics
                self._metrics.record_cache_eviction()
                self._record_store_counter("cache_eviction_count")
                if self._observability is not None:
                    try:
                        self._observability.emit_counter("kb_cache_eviction_count")
                    except (OSError, ValueError, RuntimeError) as exc:
                        logger.warning("KB eviction emit 失敗: %s", exc)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # MEDIUM-2：若 key 已存在（更新而非新增），做完整 rewrite 以防止重複行累積
            key = entry.get("error_sig", "")
            if key in self._cache and len(self._cache) > 1:
                self._rewrite()
            else:
                with self._path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("知識庫寫入失敗: %s", exc)

    def _rewrite(self) -> None:
        """將整個 cache 重新寫入檔案，防止重複 key 的行累積。"""
        try:
            with self._path.open("w", encoding="utf-8") as f:
                for entry in self._cache.values():
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("知識庫 rewrite 失敗: %s", exc)
