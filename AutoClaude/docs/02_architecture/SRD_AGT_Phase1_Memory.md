# SRD 增補 — Improving_012 Phase 1 記憶基座（C 能力）

**版本**: v1.0 | **建立日期**: 2026-06-13 | **建立者**: sd-architect
**對應計畫**: [AutoClaude_Improving_012.md](../04_planning/AutoClaude_Improving_012.md)（SCG-0 已凍結）
**閘門**: SCG-1（SRD 增補 + Port 介面規格）🔴 人工確認後凍結
**涵蓋**: F-C3（KB metrics 持久化）/ F-C1（PreferenceStore）/ F-C2（GoalProgressLedger）

---

## 0. 衝突整併聲明（Rule 7）

F-C3 與既有 **ACCEPTED** 之 [ADR-SD09-006](../04_planning/ADR/ADR-SD09-006-kb-metric-port.md)（SD_09 議題 G，W2/W3 工程從未落地）目標相同。本 SRD 採 **ADR-SD09-006 為 canonical**（更具體且先 ACCEPTED）：

| 項目 | Improving_012 原文 | ADR-SD09-006 canonical（本 SRD 採用） |
|------|-------------------|--------------------------------------|
| Port | 未提（僅 +ToolInvocation/+PreferenceStore） | 新增 `IKbMetricStore`（`core/ports/kb_metric_store.py`） |
| File 落地檔名 | `.kb_metrics.jsonl` | `.kb_metrics_local.jsonl` |
| alembic | 未指定 | ADR 原寫 0015，**已被 `0015_merge_sd06_optional_gin` 佔用 → 改 0016** |
| importlinter | 未提 | Rule 8 新增（plugins 禁直接 import kb_metric_store）→ 7→8 kept |

→ Phase 1 後 ports **10 → 12**（+kb_metric_store, +preference_store）；Phase 3 +tool_invocation → 13。此為對凍結計畫 §2「10→12」的精化（kb_metric_store 由 ACCEPTED ADR 強制），非範圍變更（F-C3 本就在凍結範圍內）。

## 1. F-C3 — KB Metrics 持久化

### 1.1 Port（依 ADR-SD09-006 §2.1，凍結後才實作 adapter = SCG-3）

`autoclaude/core/ports/kb_metric_store.py`（data tier ≤150）：介面簽名完全依 ADR-SD09-006 §2.1（`MetricValue` dataclass + `IKbMetricStore` Protocol：`record_counter` / `record_histogram` / `snapshot` / `flush` / `query_window`）。

### 1.2 Adapter 與路由

| Adapter | 位置 | 後端 | 路由（factory.py） |
|---------|------|------|------|
| `LocalKbMetricStore` | `infra/adapters/local_kb_metric_store.py` | 記憶體累計 + `{checkpoint_dir}/.kb_metrics_local.jsonl`（flush 時 append 快照；load 時讀末筆恢復 counters） | `storage.mode == 'yaml_only'` |
| `PgKbMetricStore` | `infra/adapters/pg_kb_metric_store.py` | PG `kb_metrics` 表（alembic **0016**，schema 依 ADR §2.3） | `storage.mode in ('both','db_only')` |

### 1.3 整合點

- `FailureKnowledgeBase.__init__` 新增可選參數 `metric_store: Optional[IKbMetricStore]`（utils → core.ports type 依賴，合法）。
- 啟動時：自 metric_store 末筆快照恢復 4 counters（`total_queries`/`total_hits`/`strategy_rotation_count`/`cache_eviction_count`）；latency 滑動窗口**不恢復**（短期統計，重啟重算）。
- `record_query`/`record_strategy_rotation`/`record_cache_eviction` 即時轉送 `record_counter`（記憶體 buffer）；**flush 時機 = KernelPhase.POST_RUN**（KnowledgeBasePlugin 經注入之 KB 物件觸發，plugin 不直接 import kb_metric_store，符合 Rule 8）。
- wiring：依 storage.mode 建構 adapter 注入 `FailureKnowledgeBase`。

### 1.4 驗收（對應凍結計畫 Phase 1 驗收一）

重啟（新建 FailureKnowledgeBase 實例指向同 checkpoint_dir）後 `metrics.snapshot()` 之 4 counters 不清零。

## 2. F-C1 — PreferenceStore（US-AGT-003）

### 2.1 Port

`autoclaude/core/ports/preference_store.py`（data tier ≤150）：

```python
@runtime_checkable
class IPreferenceStore(Protocol):
    def get(self, key: str, scope: str = "global") -> Optional[str]: ...
    def set(self, key: str, value: str, scope: str = "global") -> None: ...
    def list(self, scope: Optional[str] = None) -> dict[str, str]: ...
```

- `scope`: `"global"` 或 `"playbook:{project}"`（per-playbook 覆寫 global，讀取時 playbook scope 優先）。
- `value`: str（複雜值由呼叫端 JSON 編碼；Rule 2 不做泛型序列化）。

### 2.2 Adapter 與路由

| Adapter | 位置 | 後端 |
|---------|------|------|
| `FilePreferenceStore` | `infra/adapters/file_preference_store.py` | `{checkpoint_dir}/preferences.jsonl`（append + load 時 last-wins） |
| `PgPreferenceStore` | `infra/adapters/pg_preference_store.py` | PG `user_preferences` 表（alembic 0016）：PK `(scope, key)` + `value text` + `updated_at timestamptz`，UPSERT |

路由同 §1.2（yaml_only→File；both/db_only→Pg）。

### 2.3 Plugin 與 Brain 注入點

> **實作修正（2026-06-13，凍結後介面精化非範圍變更）**：實證發現 `PRE_CORRECTION` phase 於 hookspec 有定義但 Kernel **從未 dispatch**（凍結時本節假設有誤）。實作改為：(a) Kernel 於 `brain.decide_correction` 前補發 PRE_CORRECTION（hookspec 既有 phase，首次發布）；(b) plugin 回傳 `PromptInjectionResult`（hookspec 對此 phase 宣告的 expected result）而非寫 payload；(c) 注入參數鏈為 `IBrain.decide_correction(preferences_section: str = "")` → MinimaxBrainAdapter → MinimaxClient → `build_correction_message`。Kernel 僅於區段非空時傳遞 kwarg，fake/舊 Brain 實作零修改向下相容。

- 新 plugin `preference_memory_plugin.py`（plugin_entry ≤250），wiring `_REGISTER_ORDER` 插於 `knowledge_base` 之後；constructor 注入 `IPreferenceStore` 實例。
- 訂閱 `PRE_CORRECTION`：將 `store.list()`（global + 該 playbook scope 合併，playbook 覆寫，上限 10 鍵）格式化為 `## 使用者偏好` 區段，以 `PromptInjectionResult` 回傳。
- `decision/prompt_builder.build_correction_message` 新增可選參數 `preferences_section: str = ""`（插於 `## 系統總目標` 之後、`## 失敗步驟` 之前）。
- 偏好寫入：本 Phase 提供程式 API（`store.set()`）+ config 載入（`config.yaml` 可選 `preferences:` 區段於啟動時 seed，冪等 last-wins）；不做 NL 自動萃取（Phase 3 後評估）。
- 範圍註記：`playbook_runner.py` backward-compat 路徑（`_minimax.decide_correction`）不注入偏好（行為不變）；主路徑為 Kernel。

### 2.4 驗收（對應凍結計畫 Phase 1 驗收二）

偏好可寫可讀；設定偏好後 correction prompt 內出現 `## 使用者偏好` 區段與該值。

## 3. F-C2 — GoalProgressLedger（US-AGT-004）

### 3.1 設計（無新 port，依凍結計畫 §2 僅 +2 ports）

- `autoclaude/utils/goal_progress.py`：`GoalProgressLedger`（File 實作）— `record(entry)` append `{checkpoint_dir}/goal_progress.jsonl`；`summarize(goal_task_id) -> dict`（彙總 completed_features 聯集、run 數、最新 progress_pct）。
- PG 對等：`infra/adapters/pg_goal_progress_ledger.py`，PG `goal_progress` 表（alembic 0016）：`goal_task_id text NOT NULL` + `playbook_id text` + `run_id uuid NULL` + `completed_features jsonb` + `progress_pct double precision` + `recorded_at timestamptz`，索引 `(goal_task_id, recorded_at DESC)`。
- 鍵 fallback：checkpoint `goal_task_id` 為 None（yaml_only 常態）時以 `project:{playbook.project}` 為鍵，確保 yaml_only 模式仍可跨 run 彙總。
- **進度口徑（複驗 P1-1 修正，2026-06-13）**：POST_RUN 的 `completed_step_ids` = resume 前已完成步驟（`start_idx` 語意 = 其前步驟皆完成）+ 本次 run 完成步驟（保序去重，GOTO 回跳防 >100%）；halt/escalate 提前 return 不發 POST_RUN（只記完成的 run）。`KernelResult.completed_steps` 維持「本次 run」口徑，兩者語意刻意不同。`run_id` 欄位目前恆 None，為 Phase 3 Coordinator 三層任務模型預留接縫（複驗 P2-1 明示）。

### 3.2 Plugin

新 plugin `goal_progress_plugin.py`（plugin_entry ≤250），wiring 插於 `goal_synthesis` 之後；訂閱 `POST_RUN`：取 `completed_step_ids` / `total_steps` 計算 `progress_pct` 並 `record()`。wiring 依 storage.mode 注入 File 或 Pg ledger。

### 3.3 驗收（對應凍結計畫 Phase 1 驗收三）

跨 ≥2 個 playbook run（同 goal_task_id 或同 project fallback 鍵）後 `summarize()` 回傳聯集 features 與整體達成度。

## 4. 共通約束

- **DAL 簡化決策**：三類新資料**不走** DualStateRepository 影子複寫（that 機制為 checkpoint 專屬）；`both` 模式下直接路由 PG（與 ADR-SD09-006 §2.2 一致）。
- **LOC**: ports ≤150（data）/ adapters ≤400 / plugins ≤250；`.importlinter` 7→8（Rule 8 依 ADR-SD09-006 §2.4）。
- **測試**: 每支新模組對應 `tests/`（coverage ≥90%）；contract test 覆蓋 File/Pg adapter 對等行為（PG 以 mock/SQLite 不可行則 pg_real marker）。
- **回滾**: 三功能皆為純新增（KB 整合點為可選參數，預設 None = 原行為），無 feature flag 需求。

---

**SCG-1 🔴 人工確認**：koalawu 2026-06-13 核准凍結（含 F-C3 採 ADR-SD09-006 canonical、ports 10→12、importlinter 7→8、F-C2 project fallback 鍵）。
