# ADR-SD09-006 — KB metric 落地與 IKbMetricStore Port

| 項目 | 內容 |
|------|------|
| 編號 | ADR-SD09-006 |
| 狀態 | **ACCEPTED — PM 形式核准 2026-05-20（場景 A dev 自核）**（W0 範圍：ADR + Port 介面契約 + schema 草案；W2 落地 Protocol stub + alembic 0015 + adapter；W3 落地 importlinter Rule 7→8 升級）|
| **W0 v.s. W2~W3 範圍釐清** | **W0 落地**：ADR 草案 + Port 介面契約 + schema 草案文字（本文件）。**W2 落地**：`autoclaude/core/ports/kb_metric_store.py` Protocol stub + `alembic/versions/0015_kb_metrics.py` + `autoclaude/infra/adapters/{pg,local}_kb_metric_store.py`。**W3 落地**：importlinter Rule 7→8 升級 + plugin 路由路徑改造。Architect zero-trust audit 2026-05-20 確認 Port stub 為 W2 工程交付物，非 W0 阻塞項。 |
| 提出者 | SD-architect / SA 二輪四方審查 SD-C4 修復 + zero-trust audit fix agent |
| 提出日期 | 2026-05-20 |
| 對應議題 | SD_Improving_09 議題 G — KB metric 落地（SD_08 L2 限制處理）|
| 相依 ADR | ADR-SD08-004（IObservabilityPort 邊界）/ ADR-SD09-001 §2.5（W5 雙條件 1a 取證）|

---

## 1. 背景

SD_08 W4 落地 `KnowledgeBaseMetrics` 4 項 snapshot（hit_rate / query_p95_ms / strategy_rotation / cache_eviction）作為 IObservabilityPort 純記憶體統計。重啟即清零 = 跨 session 統計不可行 → 限制 (L2)。

SD_09 議題 G PM 拍板 **(a) PG 落地**：新增 `IKbMetricStore` port + `Pg` / `Local` 雙 adapter，落地 `kb_metrics` 表（alembic 0015），同時保留 yaml_only 模式之 `LocalKbMetricStore` fall-back，確保 storage.mode 切換時 metric 不孤兒。

## 2. 決策

> **命名 canonical 修訂（R41 軸 D #2 預研，2026-05-28）**：本 ADR 草案原用 `IObservabilityMetricStore` / `observability_metric_store.py`，與 Execution Guide T2-G1/G2 驗證 + R40 NextAction §5 的 `IKbMetricStore` / `kb_metric_store.py` 漂移。**經 R41 軸 D 預研拍定 canonical = `kb_metric_store.py` / `IKbMetricStore`**（語意更精確 + 與實作任務 / 驗證 grep 一致）；`observability_metric_store` 為 deprecated 草案別名。詳見 [SD09_AxisD_Prep_Research.md §B.1](../../06_quality/SD09_AxisD_Prep_Research.md)。

### 2.1 Port 介面（新增第 10 個 port）

```python
# autoclaude/core/ports/kb_metric_store.py
from typing import Protocol, runtime_checkable
from datetime import datetime
from dataclasses import dataclass

@dataclass(frozen=True)
class MetricValue:
    metric_name: str
    value: float
    window_start_at: datetime
    window_end_at: datetime
    run_id: str | None = None
    tags: dict[str, str] | None = None


@runtime_checkable
class IKbMetricStore(Protocol):
    """KB metric 跨 session 統計儲存抽象（議題 G W0 拍板 (a)）。"""

    def record_counter(self, name: str, delta: int, *, tags: dict[str, str] | None = None) -> None:
        """計數器累加（hit_count / strategy_rotation 等）。"""

    def record_histogram(self, name: str, value: float, *, tags: dict[str, str] | None = None) -> None:
        """直方圖樣本（query_p95_ms / cache_eviction_size 等）。"""

    def snapshot(self) -> dict[str, MetricValue]:
        """當前快照（用於 IObservabilityPort.emit_counter 路由）。"""

    def flush(self) -> None:
        """強制寫入後端（避免 buffer in-memory 丟失）。"""

    def query_window(self, metric: str, since: datetime) -> list[MetricValue]:
        """視窗查詢（GA 30 天連續綠取證使用）。"""
```

### 2.2 雙 adapter 設計

| Adapter | 後端 | 路由條件 |
|---------|------|---------|
| `LocalKbMetricStore` | 記憶體 + `.kb_metrics_local.jsonl` 落地 | `storage.mode == 'yaml_only'` |
| `PgKbMetricStore` | PG `kb_metrics` 表（alembic 0015） | `storage.mode in ('both', 'db_only')` |

工廠選擇於 `autoclaude/infra/repositories/factory.py` 對齊既有 storage.mode 三後端模式。

### 2.3 PG schema（alembic 0015 落地）

```sql
CREATE TABLE kb_metrics (
  metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_name text NOT NULL,
  value double precision NOT NULL,
  window_start_at timestamptz NOT NULL,
  window_end_at timestamptz NOT NULL,
  run_id uuid,
  tags jsonb DEFAULT '{}'::jsonb,
  recorded_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kb_metrics_name_window ON kb_metrics (metric_name, window_end_at DESC);
CREATE INDEX idx_kb_metrics_run_id ON kb_metrics (run_id) WHERE run_id IS NOT NULL;
```

`window_start_at` / `window_end_at` 採 `[start, end)` 半開區間以便聚合避免重複。

### 2.4 importlinter Rule 8 升級條目

新增 contract：
```ini
[importlinter:contract:no-direct-kb-metric-store-import]
name = Plugin must not directly import IKbMetricStore (use IObservabilityPort routing)
type = forbidden
source_modules =
    autoclaude.plugins
forbidden_modules =
    autoclaude.core.ports.kb_metric_store
    autoclaude.infra.adapters.pg_kb_metric_store
    autoclaude.infra.adapters.local_kb_metric_store
ignore_imports =
    autoclaude.core.event_bus -> autoclaude.core.ports.kb_metric_store
```

升級後 importlinter rules：7 → **8 kept**。

> **與 ADR-SD09-004 §3.1 Rule 8 候選釐清（zero-trust audit 2026-05-20 補述）**：ADR-SD09-004 提出的「Rule 8 候選」為 plugin 不可直接 import `autoclaude.utils.trace_context`，PM #4 拍板 (b) W3C TraceContext 後**已取消新增該 Rule 8，改採 contract test `test_trace_context_plugin_isolation.py` 覆蓋**（193 LOC / 3 case）。本 ADR §2.4 的 Rule 8 升級為**獨立** contract（針對 IKbMetricStore 路由邊界），二者不衝突；W3 落地時為 importlinter 從 7→8 條的唯一新增來源。

### 2.5 Snapshot 第 10 個 port

CLAUDE.md `[Architecture Snapshot]` Port 列表 9 → 10：
```
- brain
- embedder
- evaluator
- executor
- kb_metric_store  ← 新增（議題 G PM 拍板 (a)；R41 canonical 命名）
- memory_store
- observability
- playbook_repository
- state_repository
- vector_search
```

由 `tools/snapshot_sync.py` 自動同步（無需手動更新）。

## 3. 替代方案考量

| 方案 | 採用 | 不採用理由 |
|------|-----|-----------|
| **(a) PG kb_metrics 表 + Port** | ✅ | 同 storage.mode 三後端架構；跨 session 持久化；30 天 query_window 支援 GA 取證 |
| (b) 刪除（不落地） | ❌ | 議題 G 設計動機（L2 限制）未解；可觀測性 GA 取證孤兒 |
| (c) 延 SD_10 OTel + Prometheus | ❌ | 議題 F multi-process trace_id 拍板 (b) 已新增 OTel 過渡計畫；G (a) 立即落地不與之衝突 |
| (d) SQLite 獨立表 | ❌ | 首輪 SD M2 評估破壞 SD_06 storage.mode 三後端架構（新增第四種儲存源）|

## 4. 後果

### 4.1 正面

- 跨 session KB metric 持久化（重啟不清零，解 SD_08 L2 限制）
- W5 雙條件 1a 取證有實質統計來源（observability_ga_check.py 可呼叫 query_window）
- importlinter Rule 8 升級堵 plugin 直接 import 後門（與 Rule 7 對 trace_context 對齊）
- 與 SD_06 storage.mode 三後端架構相容（yaml_only/both/db_only 三路）

### 4.2 負面

- 新增 alembic 0015 migration（PG schema 增量）
- 新增 1 個 port（9→10）+ 2 個 adapter（Pg/Local）+ 1 個 importlinter rule（7→8）
- 增加 W2~W3 Wave 工程量（約 +5 case + +5 PD）

### 4.3 風險登記

對應 [risk_log.md §15 R-SD09-G-1](../../05_development/risk_log.md)：KB metric 落地 PG 後跨 storage.mode 三後端切換時 PG metric 表孤兒 → 緩解：本 ADR §2.2 雙 adapter 設計 + factory 路由。

## 5. 參考

- [SD_Improving_09.md §1.7 議題 G](../SD_Improving_09.md)
- [ADR-SD08-004 IObservabilityPort](ADR-SD08-004-observability-port.md)
- [risk_log.md §15 R-SD09-G-1](../../05_development/risk_log.md)
- [SD09_Pre_W0_Audit_Findings.md F-10](../../05_development/SD09_Pre_W0_Audit_Findings.md)

---

**文檔元數據**：v1.0 ACCEPTED | 建立 2026-05-20 | PM 形式核准 2026-05-20（場景 A dev 自核）| W2 PG 落地後升 production-ready
