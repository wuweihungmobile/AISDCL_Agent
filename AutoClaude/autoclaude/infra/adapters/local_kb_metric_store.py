"""LocalKbMetricStore — IKbMetricStore File 後端（F-C3 / ADR-SD09-006 §2.2）。

storage.mode == 'yaml_only' 路由（factory.build_kb_metric_store）。
落地：`{checkpoint_dir}/.kb_metrics_local.jsonl`（flush 時 append 一行快照；
建構時讀末筆恢復 counters → 重啟不清零，解 SD_08 L2 限制）。

JSONL 行格式：
  {"ts": "<ISO8601 UTC>", "window_start_at": "<ISO8601>",
   "counters": {name: value, ...}, "histograms": {name: {"p95": x, "count": n}}}
"""
from __future__ import annotations

import json
import logging
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

# R85（訴求 2）：_p95／_HISTOGRAM_WINDOW 原為本檔私有定義，與 pg_kb_metric_store
# 逐字重複；已收斂至 ports SSOT，這裡只保留原私有名以免動到呼叫端與既有測試。
from ...core.ports.kb_metric_store import HISTOGRAM_WINDOW as _HISTOGRAM_WINDOW
from ...core.ports.kb_metric_store import MetricValue
from ...core.ports.kb_metric_store import p95 as _p95

logger = logging.getLogger("autoclaude.infra.adapters.local_kb_metric_store")


class LocalKbMetricStore:
    """File 後端：記憶體累計 + JSONL 快照持久化。"""

    def __init__(self, path: str):
        self._path = Path(path)
        self._counters: dict[str, float] = {}
        self._histograms: dict[str, deque] = {}
        self._window_start = datetime.now(UTC)
        self._restore_from_last_snapshot()

    # ── IKbMetricStore Protocol ──────────────────────────────
    def record_counter(
        self, name: str, delta: int, *, tags: dict[str, str] | None = None
    ) -> None:
        self._counters[name] = self._counters.get(name, 0.0) + delta

    def record_histogram(
        self, name: str, value: float, *, tags: dict[str, str] | None = None
    ) -> None:
        window = self._histograms.setdefault(name, deque(maxlen=_HISTOGRAM_WINDOW))
        window.append(float(value))

    def snapshot(self) -> dict[str, MetricValue]:
        now = datetime.now(UTC)
        result: dict[str, MetricValue] = {}
        for name, value in self._counters.items():
            result[name] = MetricValue(
                metric_name=name, value=value,
                window_start_at=self._window_start, window_end_at=now,
            )
        for name, window in self._histograms.items():
            result[name] = MetricValue(
                metric_name=name, value=_p95(list(window)),
                window_start_at=self._window_start, window_end_at=now,
            )
        return result

    def flush(self) -> None:
        """append 一行完整快照；寫入失敗 warning 不中斷主流程（與 KB 寫入一致）。"""
        line = {
            "ts": datetime.now(UTC).isoformat(),
            "window_start_at": self._window_start.isoformat(),
            "counters": dict(self._counters),
            "histograms": {
                name: {"p95": _p95(list(w)), "count": len(w)}
                for name, w in self._histograms.items()
            },
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("KB metrics flush 失敗（warning，繼續主流程）: %s", exc)

    def query_window(self, metric: str, since: datetime) -> list[MetricValue]:
        """讀取歷史快照行，回傳 since 之後該 metric 的時序值。"""
        results: list[MetricValue] = []
        if not self._path.exists():
            return results
        try:
            with self._path.open(encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    row = json.loads(raw)
                    ts = datetime.fromisoformat(row["ts"])
                    if ts < since:
                        continue
                    start = datetime.fromisoformat(
                        row.get("window_start_at", row["ts"])
                    )
                    if metric in row.get("counters", {}):
                        results.append(MetricValue(
                            metric_name=metric, value=float(row["counters"][metric]),
                            window_start_at=start, window_end_at=ts,
                        ))
                    elif metric in row.get("histograms", {}):
                        results.append(MetricValue(
                            metric_name=metric,
                            value=float(row["histograms"][metric]["p95"]),
                            window_start_at=start, window_end_at=ts,
                        ))
        except (OSError, ValueError, KeyError) as exc:
            logger.warning("KB metrics query_window 讀取失敗: %s", exc)
        return results

    # ── 內部 ─────────────────────────────────────────────────
    def _restore_from_last_snapshot(self) -> None:
        """讀末筆快照恢復 counters（histogram 為短期窗口，不恢復）。"""
        if not self._path.exists():
            return
        last: dict | None = None
        try:
            with self._path.open(encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if raw:
                        last = json.loads(raw)
        except (OSError, ValueError) as exc:
            logger.warning("KB metrics 恢復失敗（以零起算）: %s", exc)
            return
        if last and isinstance(last.get("counters"), dict):
            self._counters = {k: float(v) for k, v in last["counters"].items()}


__all__ = ["LocalKbMetricStore"]
