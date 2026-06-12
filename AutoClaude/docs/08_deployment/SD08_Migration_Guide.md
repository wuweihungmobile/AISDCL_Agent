# SD_Improving_08 Migration Guide v1.0

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0（W6 G6 收尾交付，2026-05-18）** |
| 建立日期 | 2026-05-18 |
| 前置文件 | [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0 / [SD08_Execution_Guide.md](../05_development/SD08_Execution_Guide.md) v1.0 / [SD07_Migration_Guide.md](SD07_Migration_Guide.md) v1.0 |
| 對應 ADR | [ADR-SD08-001](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) ~ [005](../04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md) 共 5 條 |
| 適用版本 | Sprint sd_08_phase8（G0~G6 已通過 2026-05-18）|
| 撰寫者 | Tech Lead（場景 A：個人開發 dev 自核）|

---

## §1. W0~W6 完成範圍

| Wave | Gate | 通過日 | 測試基線 | 主要交付 |
|------|------|-------|---------|---------|
| W0 | G0 | 2026-05-18 | 2,028 passed | CLAUDE.md 714→324 行（≤ 400）+ Snapshot SSOT + sprint_history.md v1.0（SD_03~SD_05 完整下沉）+ ADR-SD08-001~005 落地 + `claude-md-budget` CI + `snapshot_sync.py` + `check_loc_budget SPECIAL_FILES` + `test_claude_md_budget.py` 16 case |
| W1 | G1 | 2026-05-18 | 2,028 passed | v2 backlog 三項決議（`_impl.py` 維持合規 / `_runner_internals` 永久維護 / `prompt_builder.py` 維持 override）+ `Runner_Internals_Anti_Resurrection_Guard.md` v1.0 + `SD08_V2_Backlog_Evaluation.md` v1.0 |
| W2 | G2 | 2026-05-18 | 2,034 passed（+6）| `ac4_nightly_collector.py` + `ac4_progress_check.py`（recall σ / green streak / 黃線 3 / 紅線 5）+ `pg-e2e-on-label.yml` workflow（label 觸發）+ `test_ac4_progress_check.py` 6 case |
| W3 | G3 | 2026-05-18 | 2,045 passed（+11）| mutation pilot CI（TokenGuardPlugin only + `--paths-to-mutate` + `-p no:xdist`）+ `mutation_baseline_lock.py`（連續 7 次達標寫 baseline 取 min）+ `mutation_analysis.py`（survived 自動分類）+ `.mutation_baseline.toml` + `SD08_Mutation_Baseline_Report.md` v0.1 + `test_mutation_baseline_lock.py` 11 case |
| W4 | G4 | 2026-05-18 | 2,079 passed（+34）| **核心 Wave**：`core/ports/observability.py` IObservabilityPort + ISpan + NullObservability + `infra/adapters/observability/local_logger.py` LocalLogger + `utils/trace_context.py` ContextVar + `utils/knowledge_base_metrics.py` 4 metric + EventBus auto trace_id inject + importlinter **Rule 7** + FailureKnowledgeBase 整合 emit + NonBlockingStreamReader `copy_context()` 包裝 + AutoResumeMetrics `esc_f12 / manual` wake_kinds 擴展 + 34 case 新增 |
| W5 | G5 | 2026-05-18 | 2,094 passed（+15）| `utils/perf_baseline.py` + 4 場景 perf 測試 + `perf_regression_check.py` 三級告警（annotation + PR comment）+ `perf-baseline-nightly` CI job + `.perf_baseline.toml` + `infra/observability/pg_health.py` WAL lag adapter（三閾值 + 自動降級）+ `Production_Migration_SOP.md` §1-§3 草案 + ADR-SD08-005 W5 G5 簽核 |
| **W6** | **G6** | **2026-05-18** | **≥ 2,100 passed** | **本檔（Migration Guide v1.0）** + SD08 AC Matrix v1.0 實測回填（29 條 ≥ 27）+ 四方審查 + PM 簽核 + SD_06 滾動下沉至 sprint_history.md §1.4 + SD_Improving_09.md 大綱 |

---

## §2. Breaking Changes

### §2.1 新增 importlinter Rule 7（W4）

`.importlinter` 新增 forbidden contract — **Plugins 不可直接 import `utils.knowledge_base_metrics` / `utils.trace_context`** — 必須透過建構式注入 `IObservabilityPort`。

**影響**：
- 既有 Plugin 若直接呼叫 `utils.observability` 將觸發 importlinter broken
- aggregator（`knowledge_base/__init__.py`）+ 框架層 lazy import（`event_bus.py`）以 `ignore_imports` 豁免

**遷移方式**：見 §4.1

### §2.2 CLAUDE.md ≤ 400 行強制（W0）

`tools/check_loc_budget.py` 新增 `SPECIAL_FILES = {"CLAUDE.md": 400}`；CI 新增 `claude-md-budget` job（wc -l + Snapshot freshness ≤ 7 天 + `snapshot_sync.py --check`）。

**影響**：
- 違反規則的 PR 將被 CI 阻擋
- SD_06 摘要於 W6 末由 CLAUDE.md 下沉至 `sprint_history.md §1.4`（滾動窗口 N=2 僅保留 SD_07 + SD_08）

### §2.3 mutation pilot 限定 TokenGuardPlugin（W3）

`.github/workflows/ci.yml` `mutation-test-nightly` job — GoalSynthesis / Coordinator 兩 step **暫停** 至 SD_09；W3 pilot 範圍限定 TokenGuardPlugin（`--paths-to-mutate=autoclaude/plugins/token_guard --tests-dir=tests/plugins/token_guard --no-progress -p no:xdist`）。

**影響**：
- 既有 nightly job 若依賴其他 plugin 的 mutation log 將收到空檔
- `.mutation_baseline.toml` 初始僅含 token_guard scoring；其他模組於 SD_09 接續

### §2.4 PG db_only 切換禁止（W5 + ADR-SD08-005）

H. 議題群「PG production SOP」**延 SD_09**；ADR-SD08-005 §2.2 明文 SD_09 啟用雙條件：
1. 可觀測性 GA（IObservabilityPort + KB metric + trace_id 已於 W4 落地，剩 nightly 觀察期）
2. 30 天零 drift（`drift_log` SLA）

**影響**：
- SD_08 期間 `storage.mode` 維持 `yaml_only`（預設）或 `both`（影子驗證）
- ⛔ **絕對禁止**：SD_08 期間任何 PR 將 `storage.mode` 設為 `db_only`

---

## §3. 新增 API

### §3.1 `IObservabilityPort` Protocol（W4 / ADR-SD08-004）

**路徑**：`autoclaude/core/ports/observability.py`（167 LOC，contract tier）

```python
from typing import Protocol, Mapping, Optional

class ISpan(Protocol):
    def __enter__(self) -> "ISpan": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def add_attribute(self, key: str, value: object) -> None: ...

class IObservabilityPort(Protocol):
    def emit_counter(self, name: str, value: int = 1, tags: Optional[Mapping[str, str]] = None) -> None: ...
    def emit_histogram(self, name: str, value: float, tags: Optional[Mapping[str, str]] = None) -> None: ...
    def start_span(self, name: str, **attrs: object) -> ISpan: ...
    def record_event(self, name: str, payload: Optional[Mapping[str, object]] = None) -> None: ...
```

**fallback**：`NullObservability` no-op 實作（在無注入時保證呼叫端不 crash）。

**Adapter**：`autoclaude/infra/adapters/observability/local_logger.py`（192 LOC，adapter tier） — structured log via `logging.extra` + metric_name 命名規避 LogRecord 內建欄位衝突。

### §3.2 `trace_context` 工具（W4 / ADR-SD08-004 §2.3）

**路徑**：`autoclaude/utils/trace_context.py`（141 LOC）

```python
from autoclaude.utils.trace_context import (
    trace_id,                          # ContextVar[Optional[str]]
    with_trace_id,                     # context manager
    run_in_thread_with_context,        # 同步包裝 copy_context().run()
    start_thread_with_context,         # daemon thread + copy_context() 一站式 helper
)
```

**用途**：
- `EventBus.dispatch` 自動讀取 `trace_id` ContextVar 並注入事件 payload `_trace_id`（顯式 > ContextVar > uuid fallback）
- PTY daemon thread（如 `NonBlockingStreamReader`）必須以 `start_thread_with_context()` 包裝以避免 trace_id 斷鏈（caller thread 拷貝 context，新 thread 內 `ctx.run()` 執行）

### §3.3 `KnowledgeBaseMetrics`（W4）

**路徑**：`autoclaude/utils/knowledge_base_metrics.py`（121 LOC，data tier）

提供 4 個 metric `snapshot() -> dict`：
- `hit_rate`：查詢命中比率（hit / total）
- `query_p95_ms`：200-window p95 查詢延遲
- `strategy_rotation_count`：策略輪換次數（per error_class）
- `cache_eviction_count`：LRU 淘汰累計

與 `AutoResumeMetrics` 一致的 snapshot 模式；在無 `IObservabilityPort` 注入時仍純記憶體累計。

### §3.4 `PgHealthMonitor`（W5 / ADR-SD08-005）

**路徑**：`autoclaude/infra/observability/pg_health.py`（214 LOC，adapter tier）

```python
from autoclaude.infra.observability.pg_health import (
    PgHealthMonitor,         # Protocol
    DefaultPgHealthMonitor,  # asyncpg adapter
)

monitor = DefaultPgHealthMonitor(connection_factory=..., observability=obs_port)
lag_seconds = await monitor.get_wal_lag_seconds()
classification = monitor.classify_lag(lag_seconds)   # NORMAL / WARN / CRITICAL
```

**三閾值（環境變數可調）**：
- `< 2s` NORMAL — 僅 emit_histogram `pg_wal_lag_seconds` 趨勢
- `2s ≤ lag < 10s` WARN — emit_counter `pg_wal_lag_warn`
- `lag ≥ 10s` CRITICAL — emit_counter `pg_wal_lag_critical` + record_event `pg_degrade_yaml_only` 觸發自動降級

### §3.5 `PerfBaseline`（W5 / ADR-SD08-003）

**路徑**：`autoclaude/utils/perf_baseline.py`（137 LOC）

```python
from autoclaude.utils.perf_baseline import PerfBaseline, measure, write_baseline

baseline = measure(scenario="dry_run_e2e", fn=run_scenario, runs=7)
write_baseline(".perf_baseline.toml", baseline)
```

純 stdlib（`statistics` + `perf_counter_ns`）零相依；連跑 N 次取 p50/p95/p99 + git SHA 標記。

### §3.6 AutoResumeMetrics `wake_kinds` 擴展（W4）

新增兩個 wake_kind：
- `"esc_f12"`：HotkeyPlugin ESC+F12 中斷觸發
- `"manual"`：CLI/API 顯式 `auto_resume_service.wake(kind="manual")` 觸發

對應 `snapshot()` 新增 `esc_f12_resumes` / `manual_resumes` 計數欄位。

---

## §4. 升級步驟

### §4.1 Plugin 改建構式注入 `IObservabilityPort`

**舊寫法**（W4 之前）：
```python
class MyPlugin:
    def on_step_complete(self, ctx):
        from autoclaude.utils.knowledge_base_metrics import counter
        counter.inc("my_metric")
```

**新寫法**（W4 之後 — Rule 7 強制）：
```python
class MyPlugin:
    def __init__(self, observability: IObservabilityPort | None = None):
        self._obs = observability or NullObservability()

    def on_step_complete(self, ctx):
        self._obs.emit_counter("my_metric", tags={"step": ctx.step_id})
```

**註冊至 wiring**（`autoclaude/core/wiring.py`）：
```python
# _build_plugin_set 與 build_kernel 兩條路徑皆已注入 IObservabilityPort
my_plugin = MyPlugin(observability=obs_port)
```

### §4.2 PTY daemon thread 包裝

任何 daemon thread 處理 trace_id 必須以 `copy_context()` 顯式包裝：

```python
from autoclaude.utils.trace_context import start_thread_with_context

# 舊（trace_id 斷鏈）
thread = threading.Thread(target=worker, daemon=True)
thread.start()

# 新（trace_id 不斷鏈）
thread = start_thread_with_context(target=worker, daemon=True)
thread.start()
```

### §4.3 CLAUDE.md 行數壓縮

- 任何 PR 將 CLAUDE.md > 400 行 → CI `claude-md-budget` job 阻擋
- 滾動下沉動作（每 Sprint W6 末）：將最舊 sprint 完整段落從 CLAUDE.md 搬移至 `sprint_history.md §1.x`，CLAUDE.md 留一行 link
- Architecture Snapshot 區段不可手改 — 必須跑 `python tools/snapshot_sync.py` 自動同步（從 `wiring.py` / `core/ports/` / `infra/repositories/factory.py` / `.importlinter` AST 解析）

### §4.4 PG e2e 測試開啟（labeled PR 觸發）

當 AC4 14 天 nightly 觀察期通過後（`tools/ac4_progress_check.py --json` 回報 `ready_for_labeled_pr=true`）：

1. 手動啟用 `.github/workflows/pg-e2e-on-label.yml` workflow
2. 在需跑 PG e2e 的 PR 加 `needs-pg-e2e` label 即觸發
3. 預期 +8-12 min CI 時間 — 避免每 PR 跑（月度額度爆預算）

### §4.5 perf baseline 寫入流程

1. 本機跑 `pytest -m perf tests/perf/` 取得 4 場景 PerfBaseline
2. CI `perf-baseline-nightly` job 在 ubuntu-latest runner 連跑 7 次後寫入 `.perf_baseline.toml`
3. PR 上 `tools/perf_regression_check.py` 比對 baseline：
   - p95 增量 `< 10%` PASS
   - `10-15%` WARN（GitHub Actions `::warning::` annotation + PR comment）
   - `≥ 15%` BLOCK（`::error::` annotation + PR comment）
4. pgvector 場景僅在 perf machine 跑（CI runner `PG_REAL_ENABLED` 未設則 SKIP）

---

## §5. SD_09 延期清單

以下項目 SD_08 已交付**前置 / 草案**，正式啟用延至 SD_09：

| # | 項目 | SD_08 完成度 | SD_09 觸發條件 |
|---|------|-------------|---------------|
| **1** | **PG production SOP 完整啟用**（議題 H）| §1-§3 草案落地（`Production_Migration_SOP.md` v0.1）+ WAL lag adapter + ADR-SD08-005 雙軌制（AI-Agent 演練 + 人類 DBA 親簽）| **雙條件齊備**：(a) 可觀測性 GA（IObservabilityPort + KB metric + trace_id 30 天 nightly 全綠）+ (b) 30 天零 drift（`drift_log` SLA）|
| **2** | **mutation pilot 擴展至 GoalSynthesis + Coordinator**（議題 D）| TokenGuardPlugin 單模組 pilot（W3 觀察期 2026-05-19 起；首次評估 2026-05-25；W3 末判定 2026-06-01）| TokenGuardPlugin 連續 7 次達 ≥ 70% 鎖定 `.mutation_baseline.toml`，再擴展兩模組（分批 nightly）|
| **3** | **perf machine 採購評估**（議題 G）| CI runner 跑 3 場景 CPU-bound（dry_run / TokenHalt / decide_correction）；pgvector 場景 SKIP 強制延 perf machine | 採購預算評估 + 季度校準排程確認 |
| **4** | **AC4 labeled PR 觸發升級**（議題 C）| `pg-e2e-on-label.yml` workflow 就位（待手動啟用）+ collector / progress_check 工具落地 | 14 天 nightly 全綠 + `ready_for_labeled_pr=true` |
| **5** | **OpenTelemetry 外掛**（議題 F 延伸）| 階段性混合（IObservabilityPort + LocalLogger adapter）= SD_10 後再外掛 OTel | SD_10 後啟動（分散式部署需求觸發）|
| **6** | **dual_state drift_log 30 天零事件 SLA**（議題 H 前置）| `drift_log` partition 365 天 + dual_write_strict=fail_loud 已於 SD_06 完成 | nightly 連續 30 天 `drift_count=0`（W5 觀察期啟動 2026-05-18）|

---

## §6. G6 實測結果

| 項目 | W5 G5 末（2026-05-18）| **W6 G6 末（2026-05-18，本次）** | 增量 |
|------|------------------------|--------------------------------|------|
| 全測 passed | 2,094 | **詳見 §6.1 實測** | — |
| 全測 skipped | 122 | **詳見 §6.1 實測** | — |
| importlinter | 7 kept / 0 broken | **7 kept / 0 broken** ✅ | 持平 |
| LOC violations | 0（total=14933 / baseline=14058 / cap=16869）| **0** ✅ | 持平 |
| equivalence | 83/83 | **83/83** ✅ | 持平 |
| CLAUDE.md | 326 行 | **≤ 400 行（W6 滾動下沉 SD_06 後再次驗證）** | — |
| NOTE(SD_08) | 0 | **0** ✅ | 持平 |
| AC Matrix 條目 | SD_07 19 + SD_08 10 = 29 | **29 條（≥ 27 門檻）** ✅ | 持平 |
| ADR 數 | 5（SD08-001~005）| **5** ✅ | 持平 |

### §6.1 W6 G6 末實測值（gate_audit.md SD08-G6 補登）

**測試基線**：見 `gate_audit.md §1-sexies SD08-G6` 簽核紀錄。
**四方審查**：見 §7 簽核狀態。

---

## §7. 已知限制（W6 收尾揭露）

| # | 限制項 | 影響 | 緩解 / SD_09 處理 |
|---|--------|------|------------------|
| **L1** | `trace_id` 在 multi-process subprocess 邊界不傳播（ContextVar 限同 process）| 子 process（如 `subprocess.run`）內 emit 的 metric 無 trace 串接 | SD_10 OTel 整合時透過 W3C TraceContext header 解決；SD_08 限定單 process 場景 |
| **L2** | `KnowledgeBaseMetrics` 為純記憶體統計（重啟即清零）| 跨 session 統計需依賴 nightly 採集 | SD_09 視需求決定是否落地到 PG（SLA 不變）|
| **L3** | `perf_baseline.py` 為 ubuntu-latest runner 量測（非 perf machine）| pgvector 場景 p95 變異 ±50% | pgvector 跑 perf machine（季度校準）— SD_09 採購評估後啟動 |
| **L4** | mutation pilot 僅 TokenGuardPlugin（GoalSynthesis / Coordinator 延 SD_09）| 其他模組 mutation score 未知 | W3 連續 7 次達標鎖定後 SD_09 接續 |
| **L5** | `Production_Migration_SOP.md` 僅 §1-§3 草案（§4-§8 待 SD_09）| 真實 PG production 切換 SOP 不完整 | SD_09 補完 §4 切換時序 / §5 回退 / §6 監控 / §7 RACI / §8 演練回顧 |
| **L6** | CLAUDE.md 滾動窗口 N=2 對新 onboarding 工程師需參考 sprint_history.md | 初期 context 不完整 | 頂端「快速導覽」3 行已就位 + sprint_history.md §2 議題索引表 reverse-link |

---

## §8. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| **v1.0** | **2026-05-18** | **W6 G6 收尾交付** — §1 W0~W6 完成範圍 + §2 Breaking Changes（importlinter Rule 7 / CLAUDE.md ≤ 400 / mutation pilot / PG db_only 禁切換）+ §3 新增 API（IObservabilityPort / trace_context / KnowledgeBaseMetrics / PgHealthMonitor / PerfBaseline / wake_kinds 擴展）+ §4 升級步驟 + §5 SD_09 延期清單 + §6 G6 實測 + §7 已知限制 |

---

## §9. 對應參考文件

- [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0 — Sprint 主規劃
- [SD08_Execution_Guide.md](../05_development/SD08_Execution_Guide.md) v1.0 — Wave 執行協議
- [SD08_AC_Matrix.md](../03_testing/SD08_AC_Matrix.md) v1.0 — 10 條 AC 實測回填
- [ADR-SD08-001-claude-md-budget.md](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) — CLAUDE.md ≤ 400 + Snapshot SSOT
- [ADR-SD08-002-mutation-baseline.md](../04_planning/ADR/ADR-SD08-002-mutation-baseline.md) — mutation 分模組目標
- [ADR-SD08-003-perf-regression-policy.md](../04_planning/ADR/ADR-SD08-003-perf-regression-policy.md) — perf p95 < 15%
- [ADR-SD08-004-observability-port.md](../04_planning/ADR/ADR-SD08-004-observability-port.md) — IObservabilityPort 設計
- [ADR-SD08-005-pg-production-dual-track.md](../04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md) — PG 雙軌制 SD_09 啟用
- [Production_Migration_SOP.md](Production_Migration_SOP.md) v0.1 — §1-§3 草案
- [SD08_Mutation_Baseline_Report.md](../06_quality/SD08_Mutation_Baseline_Report.md) v0.1 — pilot observing
- [SD08_Perf_Baseline_Report.md](../06_quality/SD08_Perf_Baseline_Report.md) v1.0 — 4 場景 baseline
- [Runner_Internals_Anti_Resurrection_Guard.md](../06_quality/Runner_Internals_Anti_Resurrection_Guard.md) v1.0 — 三層防護文件化
- [SD08_V2_Backlog_Evaluation.md](../06_quality/SD08_V2_Backlog_Evaluation.md) v1.0 — v2 backlog 三項決議
- [sprint_history.md §1.4 ~ §1.6](../05_development/sprint_history.md) — SD_06~SD_08 完整紀錄
- [gate_audit.md §1-sexies](../05_development/gate_audit.md) — SD08-G0~G6 簽核
- [risk_log.md §14](../05_development/risk_log.md) — R-SD08-* 風險登記
- [SD_Improving_09.md](../04_planning/SD_Improving_09.md) — 後續 Sprint 大綱（W6 同步交付）

---

**簽核**：

| 角色 | 狀態 | 日期 | 簽核摘要 |
|------|------|------|----------|
| Architect | ✅ APPROVED | 2026-05-18 | §2 Breaking Changes 完備 / §3 新增 API 對齊 ADR-SD08-001~005 |
| SA | ✅ APPROVED | 2026-05-18 | §4 升級步驟可操作 / §5 SD_09 延期清單明確 / §7 已知限制揭露完整 |
| SD | ✅ APPROVED | 2026-05-18 | §3 API 簽名與程式碼一致 / §4.1 plugin 注入模式正確 / §4.2 PTY 包裝範例可用 |
| QA | ✅ APPROVED | 2026-05-18 | §6 G6 實測結構就位 / AC Matrix 29 條 ≥ 27 / 量測命令對齊 |
| PM | ✅ APPROVED | 2026-05-18 | 場景 A 個人開發 dev 自核；對應 PM 8 項拍板（#1~#8）全數對齊 |

---

**文檔元數據**：v1.0 | 建立 2026-05-18 | 撰寫者 Tech Lead | 適用 sd_08_phase8 G0~G6
