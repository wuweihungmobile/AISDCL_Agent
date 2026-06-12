# ADR-SD08-004：IObservabilityPort 設計 — Hexagonal 邊界 + trace_id contextvars + 階段性混合

| 項目 | 內容 |
|------|------|
| 狀態 | **APPROVED（PM 形式核准 / 場景 A 個人開發 dev 自核 2026-05-18）** |
| 建立日期 | 2026-05-18 |
| 對應 PM 拍板 | SD_08 PM #5（階段性混合：W4 自建 IObservabilityPort + LocalLogger；SD_10 OTel）|
| 提案人 | Architect / SD（雙方共識）|
| 核准日期 | 2026-05-18（SD_08 W0 T0-ADR4）|

---

## 1. 背景

- EventBus 已有 trace_id / escalate(N=3) / phase_failure_counts，**未端對端整合**
- AutoResumeMetrics 已有 wake_kinds snapshot；FailureKnowledgeBase **無命中率 metric**
- **Architect 警示**：可觀測性放在 utils/ 而非 core/ports/ 將退化為散裝技術債（6 個月後分散式部署時各 worker 各自實作）
- **SD 警示**：trace_id 在 PTY daemon thread（NonBlockingStreamReader）邊界**不會自動傳播 contextvars**

## 2. 決議

### 2.1 邊界劃分（Hexagonal）

| 層 | 路徑 | 職責 |
|---|------|------|
| **Port（介面）** | `autoclaude/core/ports/observability.py` | `IObservabilityPort` Protocol（emit_counter/emit_histogram/start_span/record_event）|
| **Adapter（實作）** | `autoclaude/infra/adapters/observability/local_logger.py` | LocalLogger adapter（W4 唯一實作）|
| **Adapter（未來）** | `autoclaude/infra/adapters/observability/otel.py` | OpenTelemetry adapter（SD_10+ 外掛）|
| **trace context helper** | `autoclaude/utils/trace_context.py` | `trace_id: ContextVar[Optional[str]]` + `with_trace_id()` helper + daemon thread 包裝 |
| **KB metric** | `autoclaude/utils/knowledge_base_metrics.py` | 4 metric snapshot dict（與 AutoResumeMetrics 一致設計）|

**禁止**：
- ❌ 將 OTel SDK 直接散落於 plugin / service
- ❌ Plugin 直接 import `utils.observability`（必須走 Port 注入）

### 2.2 IObservabilityPort 簽名

```python
# autoclaude/core/ports/observability.py
from typing import Optional, Protocol

class IObservabilityPort(Protocol):
    """可觀測性 Port — Hexagonal 介面，與 BrainPort/ExecutorPort 同層級。"""

    def emit_counter(self, name: str, value: int, tags: dict[str, str]) -> None:
        """累計型 metric（如 kb_hit_total / autoresume_wake_total）。"""

    def emit_histogram(self, name: str, value: float, tags: dict[str, str]) -> None:
        """分布型 metric（如 kb_query_latency_ms / dry_run_duration_ms）。"""

    def start_span(self, name: str, tags: dict[str, str]) -> "ISpan":
        """span 生命週期管理（context manager）；trace_id 由 ContextVar 自動注入。"""

    def record_event(self, name: str, attributes: dict) -> None:
        """事件記錄（如 token_halt / esc_f12_interrupt）。"""
```

### 2.3 trace_id 端對端傳遞（contextvars + EventBus 自動注入）

```python
# autoclaude/utils/trace_context.py
from contextvars import ContextVar, copy_context
from typing import Optional, Iterator
from contextlib import contextmanager
import uuid

trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

@contextmanager
def with_trace_id(tid: Optional[str] = None) -> Iterator[str]:
    """設定 trace_id 並在 context manager 結束時還原。"""
    new_id = tid or str(uuid.uuid4())
    token = trace_id.set(new_id)
    try:
        yield new_id
    finally:
        trace_id.reset(token)

def get_trace_id() -> Optional[str]:
    return trace_id.get()

# daemon thread 邊界包裝（給 NonBlockingStreamReader）
def run_in_thread_with_context(fn, *args, **kwargs):
    """copy_context().run() 顯式包裝；R-SD08-F-1 緩解。"""
    ctx = copy_context()
    return ctx.run(fn, *args, **kwargs)
```

EventBus dispatch 時自動讀取 ContextVar 寫入 event metadata（**不要顯式參數注入**，避免污染 IBrain/IExecutor Port 簽名）：

```python
# autoclaude/core/event_bus.py（W4 修正）
def dispatch(self, phase: KernelPhase, payload: dict, ...):
    payload.setdefault("_trace_id", get_trace_id())  # 自動注入
    ...
```

### 2.4 KB metric 設計（4 項，不含 cache_size）

```python
# autoclaude/utils/knowledge_base_metrics.py
@dataclass
class KnowledgeBaseMetrics:
    hit_rate: float          # KB query 命中率（成功命中 / 總查詢）
    query_p95_ms: float      # KB query latency p95
    strategy_rotation_count: int  # 策略輪換次數（next_strategy() 觸發）
    cache_eviction_count: int     # 記憶體淘汰次數
    # NOT included: cache_size（無 SLO 意義，純記憶體統計）

    def snapshot(self) -> dict:
        """與 AutoResumeMetrics 一致的 snapshot 模式。"""
        return asdict(self)
```

### 2.5 階段性混合策略

| Phase | Sprint | 範圍 |
|-------|--------|------|
| **Phase 1**（自建）| **SD_08 W4**（本 ADR）| IObservabilityPort + LocalLogger adapter + trace_id contextvars + KB metric |
| **Phase 2**（評估）| SD_09 | 評估 OpenTelemetry / Sentry 整合需求 |
| **Phase 3**（外掛）| SD_10+ | 新建 `infra/adapters/observability/otel.py`，與 LocalLogger 並存（adapter 替換成本 ≤ 3 PD）|

### 2.6 W4 切兩階段（Architect 警示連動 R-SD08-PM-#7）

| 階段 | 範圍 | 必要性 |
|------|------|--------|
| **W4 上半（P0 必做）** | `IObservabilityPort` Protocol + LocalLogger adapter + 基礎 emit_counter/histogram | **必做**（給 W5 WAL lag adapter 有 port 可依）|
| **W4 下半（P1 增強）** | trace_id ContextVar 全鏈完整覆蓋 + KB metric 4 項 + AutoResume 健壯化 | **可彈性延 SD_09**（若 W4 PD 超預期）|

## 3. importlinter Rule 7（W4 新增）

`.importlinter` 新增 forbidden contract：

```ini
[importlinter:contract:plugin-no-utils-observability-direct-import]
name = Plugin no direct import utils.observability
type = forbidden
source_modules =
    autoclaude.plugins
forbidden_modules =
    autoclaude.utils.knowledge_base_metrics
    autoclaude.utils.trace_context  # plugin 必須透過建構式注入 IObservabilityPort
```

## 4. 落地 Checklist（W4 task breakdown）

```
# W4 上半（P0 必做）
[  ] T4-F1 新建 autoclaude/core/ports/observability.py（IObservabilityPort Protocol + ISpan）
[  ] T4-F2 新建 autoclaude/infra/adapters/observability/__init__.py
[  ] T4-F3 新建 autoclaude/infra/adapters/observability/local_logger.py（LocalLogger 實作）
[  ] T4-F4 新建 autoclaude/utils/trace_context.py（trace_id ContextVar + with_trace_id + run_in_thread_with_context）
[  ] T4-F5 autoclaude/core/wiring.py 注入 IObservabilityPort（建構式注入至 Kernel）
[  ] T4-F6 autoclaude/core/event_bus.py 修正 dispatch 自動注入 _trace_id
[  ] T4-F7 .importlinter 新增 Rule 7 plugin-no-utils-observability-direct-import
[  ] T4-F8 補 tests/core/test_observability_port.py（≥ 6 case：Protocol 合約 + LocalLogger emit / ContextVar 傳遞 / daemon thread 邊界包裝）

# W4 下半（P1 增強）
[  ] T4-F9 新建 autoclaude/utils/knowledge_base_metrics.py（4 metric snapshot dict）
[  ] T4-F10 FailureKnowledgeBase 整合 emit_counter("kb_hit_total") + emit_histogram("kb_query_latency_ms")
[  ] T4-F11 NonBlockingStreamReader 改用 run_in_thread_with_context 包裝（PTY 邊界 trace_id 不斷鏈）
[  ] T4-F12 AutoResumeService 整合 emit_event("autoresume_wake") + wake_kinds 擴展
[  ] T4-F13 補 tests/utils/test_knowledge_base_metrics.py（≥ 4 case：4 metric 計算 / snapshot 一致 / hit_rate 邊界 0/1 / eviction 累計）
[  ] T4-F14 補 tests/utils/test_trace_context_daemon_thread.py（≥ 3 case：PTY daemon thread 不斷鏈 / copy_context() 顯式 / 並發 thread isolation）
```

## 5. 退化風險緩解（連動 R-SD08-F-1 / R-SD08-F-2）

| 風險 | 緩解 |
|------|------|
| trace_id 在 PTY daemon thread 斷鏈 | `run_in_thread_with_context()` 顯式包裝 + 單元測試覆蓋（T4-F14）|
| `IObservabilityPort` 放錯層退化為散裝技術債 | 本 ADR 明文 `core/ports/` + importlinter Rule 7 強制 |
| EventBus 同時承擔事件廣播與追蹤（單一職責違反）| EventBus 為**消費者**而非實作者；trace_id 注入透過 ContextVar 而非 EventBus 內部生成 |
| W4 PD 超預期連動壓縮 W5/W6 | 切「P0 必做」（上半）vs「P1 增強」（下半）兩階段；P1 可彈性延 SD_09 |

## 6. 簽核

| 角色 | 狀態 | 日期 |
|------|------|------|
| Architect | ✅ 邊界主導 | 2026-05-18 |
| SD | ✅ 實作主導 | 2026-05-18 |
| PM | ✅ 形式核准（場景 A 個人開發 dev 自核）| 2026-05-18 |

---

**相關文件**：
- [SD_Improving_08.md](../SD_Improving_08.md) v1.0 §6 PM 拍板 #5 + §7.3 SD 議題 4 意見
- [ADR-SD06-001-coordinator-layer-boundary.md](ADR-SD06-001-coordinator-layer-boundary.md) — Coordinator/AutoResume 雙層架構（沿用 Hexagonal 邊界原則）
