# SD_Improving_09 — 精進 Sprint 規劃（v1.0）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.2（W3 nightly system zero-trust audit Round 2 修復 2026-05-24；v1.1 → v1.2）** |
| 建立日期 | 2026-05-18 |
| 最後更新 | **2026-05-24**（**v1.2 升版** — Round 2 audit 28 項發現 → 真實修復 8 項：P0-2 Add-Content FileShare.ReadWrite + retry / P0-3 drift_log_ga_check.py 新建 + snapshot 同日去重優先 table_exists / P0-5 mutation source_sha256 + 7 unique sha lock / P0-6 perf rc 三態 (0/2/1) / P1-1 emit_real strict 最新 3 筆 / P1-2 mutation log mtime guard 3600s / P1-7 samples=20 邊界 case / P1-8 emit 三段拆分 partial success；4 項由 clean run 推翻（P0-1 part / P0-4 / P0-7）；11 項 P2 列 W1 backlog）|
| 前置文件 | [SD_Improving_08.md](SD_Improving_08.md) v1.0（W6 G6 通過 ✅ 2026-05-18）/ [SD08_Migration_Guide.md](../08_deployment/SD08_Migration_Guide.md) v1.0 §5 SD_09 延期清單 + §7 L1~L6 限制 |
| 文件狀態 | **v1.0（W0 task list 22/22 CLOSED + 5 方終審 APPROVED 2026-05-20 → 待 W0 G0 預檢與三觀察期累積 → W1 啟動）** |
| 啟動條件 | 詳見 §8（三觀察期 + 三方研究 + PM 形式核准 + Tech Lead task breakdown）|
| 預估啟動日 | **2026-06-18 或之後**（最晚觀察期結束日 2026-06-17 + ≥ 1 工作日提前期；最遲 2026-06-26，對齊 §6 PM #6 (b) 拍板）|

---

## 0. SD_08 結尾遺留與精進來源

| 來源 | 內容 | SD_08 完成度 | SD_09 觸發點 |
|------|------|-------------|---------------|
| **SD_08 W5 H 議題群延期** | PG production SOP 完整啟用（dual_state → db_only 切換）| 草案 §1-§3 落地 + WAL lag adapter + ADR-SD08-005 雙軌制 | 雙條件齊備：(a) 可觀測性 GA（同 process trace_id + KB metric + IObservabilityPort 30 天 nightly 全綠）+ (b) 30 天零 drift |
| **SD_08 W3 D 議題群 observing** | mutation pilot 擴展至 GoalSynthesis + Coordinator | TokenGuardPlugin observing 觀察期啟動 2026-05-19 | TokenGuardPlugin 連續 7 次達 ≥ 70% 鎖定 → 兩模組分批 nightly |
| **SD_08 W2 C 議題群 labeled PR 升級** | AC4 14 天 nightly 全綠 → labeled PR 觸發啟用 | `autoclaude-pg-e2e-on-label.yml` workflow 就位（dormant 待啟用）| `tools/ac4_progress_check.py` 回報 `ready_for_labeled_pr=true` |
| **SD_08 W5 G 議題群 perf machine** | pgvector 性能 baseline 採購 perf machine + 季度校準 | CI runner 跑 3 場景 CPU-bound；pgvector SKIP 強制延 perf machine | 採購預算評估 + 季度校準排程確認 |
| **SD_08 W4 F 議題群延伸 (L1)** | trace_id 多 process 邊界傳播（subprocess 邊界斷鏈）| 階段性混合 IObservabilityPort + LocalLogger 已落地（**僅同 process**）| SD_09 W0 三方研究 + W3 落地 OR 延 SD_10 |
| **SD_08 W4 限制 (L2)** | KB metric 純記憶體統計（重啟即清零）| `KnowledgeBaseMetrics` snapshot 4 項已落地（**僅記憶體**）| SD_09 W0 三方研究 + W2~W3 落地 OR 延 SD_10 |
| **SD_08 W5 限制 (L3)** | perf_baseline 為 ubuntu-latest runner 量測（非 perf machine）| 3 場景 baseline 鎖定（pgvector 延 perf machine） | SD_09 W2 採購評估 + W4 啟用 |
| **SD_08 W3 限制 (L4)** | mutation pilot 僅 TokenGuardPlugin | observing 觀察期啟動 | SD_09 W1 GoalSynthesis + W2 Coordinator |
| **SD_08 W5 限制 (L5)** | Production_Migration_SOP.md 僅 §1-§3 草案 | §1-§3 落地 | SD_09 W3-W4 補完 §4-§8 |
| **SD_08 W0 限制 (L6)** | CLAUDE.md 滾動窗口 N=2 對新 onboarding 工程師需參考 sprint_history.md | 快速導覽 3 行 + §2 議題索引表 reverse-link 已就位 | **處理方式**：議題 E（CLAUDE.md 滾動下沉維護）+ 「快速導覽」3 行持續強化；不視為阻塞 |

**SD_10 預告觸發來源**（W6 末同步建立 SD_Improving_10.md 大綱）：
- OpenTelemetry 外掛（議題 F W3C TraceContext 落地後過渡）
- 議題 G KB metric 落地（若 W0 PM 拍板延 SD_10）
- 議題 F multi-process trace_id 30 天觀察期（若 W5 改為「同 process GA」則 multi-process GA 延 SD_10）
- mutation pilot 全模組擴展完成後 GA（若 W3 fall-back）
- perf machine 採購延期（若 W2 PM 預算未簽核）

---

## 1. 議題群提案（待 W0 三方研究 + PM 拍板）

### 1.1 議題 A：PG production SOP 完整啟用（**SD_08 H 議題群正式啟動**）

**主軸**：完成 `Production_Migration_SOP.md` §4-§8 + 真實 PG production 上線。

**Wave 預估**：W3~W5 共 3 Wave。

**核心交付**：
- `Production_Migration_SOP.md` §4 切換時序（yaml_only → both → db_only 灰度三階梯 10%/50%/100%）
- §5 回退（rollback 範本 + drift_log 取證 + **PG dump → YAML import script**，明訂「不可逆 = 業務語意」非物理不可逆）
- §6 監控（WAL lag / 連線數 / drift 計數 dashboard）
- §7 RACI（DBA / SRE / Tech Lead / PM）
- §8 演練回顧（30 天觀察期 + AI-Agent 模擬 + 人類 DBA 親演）
- 真實 staging（≥ 1M 列）跑 + 人類 DBA 親簽 release approval
- ADR-SD09-001：PG db_only 切換不可逆轉折點（業務語意）
- ADR-SD09-005：PG canary 三階梯閾值（10%/24h + 50%/48h + 100%/7d + 三觸發回滾條件）

**啟動雙條件**（ADR-SD08-005 §2.2，**SD_09 ADR-SD09-001 §2 明訂同 process trace_id GA = W5 條件**；multi-process GA 視議題 F PM 拍板延 W6 / SD_10）：
1. 可觀測性 GA（**同 process** IObservabilityPort + KB metric + trace_id ContextVar 30 天 nightly 全綠 — SD_08 W4 起 2026-05-18 → 2026-06-17）
2. 30 天零 drift（`drift_log` SLA — SD_08 W5 起 2026-05-18 → 2026-06-17）

### 1.2 議題 B：mutation pilot 擴展（**SD_08 D 議題群延伸 / L4**）

**主軸**：TokenGuardPlugin pilot 鎖定後擴展至 GoalSynthesis + Coordinator（分批 nightly，**單模組不並行**）。

**Wave 預估**：W1（GoalSynthesis）+ W2（Coordinator）共 2 Wave。

**核心交付**：
- GoalSynthesisPlugin mutation pilot 兩週（目標 ≥ 65%）
- OrchestrationCoordinator mutation pilot 兩週（目標 ≥ 60%，**單檔精準 `--paths-to-mutate=autoclaude/core/orchestration/coordinator.py`**）
- `.mutation_baseline.toml` 補入兩模組鎖定值
- `SD09_Mutation_*_Report.md`（含 survived diff 分析 + 補測 backlog）
- ADR-SD09-002：mutation 全模組擴展策略（**TokenGuardPlugin 鎖定後從 nightly 移除改為週 baseline 抽測；單一時間僅 1 個 active pilot module；W1/W2 三階段排程：TG 退出 + GS 進入 → GS 鎖定 + Coord 進入**）

**前置條件**（**Arch-C3 修復：TG fall-back 處理矩陣**）：TokenGuardPlugin **鎖定**（連續 7 次達 ≥ 70%）**或** **明確退出 pilot**（< 60% baseline 移交 SD_10）— **二選一**，不可同時 TG SD_10 pilot active + W1 GS active（違紅線 ❌19 候補）。詳見 ADR-SD09-002 §2.1.1。

> **觀察期 #1 統計以 UTC 日界為準**（Arch-M2 修復；對應 ADR-SD09-002 §2.3）。

### 1.3 議題 C：AC4 labeled PR 觸發啟用（**SD_08 C 議題群升級**）

**主軸**：14 天 nightly 全綠後手動啟用 `autoclaude-pg-e2e-on-label.yml` workflow（將 dormant trigger 啟動）。

**Wave 預估**：W0 啟動任務（無獨立 Wave）。

**核心交付**：
- `autoclaude-pg-e2e-on-label.yml` workflow 由 dormant 切換為 active（`on: pull_request labeled` 啟用）
- AC Matrix AC4-1/AC4-2 升級為「實測 recall ≥ 0.95 + p95 < 50ms + cb_open=0」
- `tools/ac4_dashboard.py`（CI artifact 累計可視化，可選）

**前置條件**：`tools/ac4_progress_check.py` 回報 `ready_for_labeled_pr=true`（觀察期 #2 通過）。

### 1.4 議題 D：perf machine 採購評估與啟用（**SD_08 G 議題群延伸 / L3**）

**主軸**：採購評估 + 季度校準排程 + pgvector 場景 baseline 鎖定。

**Wave 預估**：W2（採購評估 + PM 預算簽核）+ W4（上架啟用）共 2 Wave。

**核心交付**：
- 採購評估報告（GPU? CPU bare metal? 雲端 GPU instance? 預算評估）
- 季度校準 schedule（每季首週末跑 7 次 + 鎖定 baseline）
- `tests/perf/test_pgvector_recall_perf.py` 改用 `@pytest.mark.perf_machine_only` marker + **`pyproject.toml [tool.pytest.ini_options]` `addopts` 預設 deselect**（**SD-M3 修復**：專案無 pytest.ini；marker 須補註冊；**取代既有 `PG_REAL_ENABLED` gate**），CI runner 不會誤跑
- 補入 `.perf_baseline.toml` pgvector_recall_perf 鎖定值
- ADR-SD09-003：perf 雙軌轉三軌（CI nightly + perf machine 季度 + 開發機驗證 + **緊急路徑：W2 採購未簽核 → 議題群整體延 SD_10，G4 不阻塞**）

### 1.5 議題 E：CLAUDE.md 滾動下沉維護（**SD_08 E 議題群持續維護 / L6**）

**主軸**：SD_09 W6 末**擴寫** `sprint_history.md §1.5` 為 SD_07 完整 W0~W6 紀錄（≥ 300 行），CLAUDE.md 維持單行 link（滾動窗口 N=2 → 保留 SD_08 + SD_09）。

> **澄清**（首輪審查 Architect C1 + SA M1 修正）：SD_07 完整段落在 CLAUDE.md 早於 SD_08 W6 已壓縮為一行摘要（`CLAUDE.md:160-164`），sprint_history.md §1.5 目前亦為摘要狀態。**真實工作 = 擴寫 §1.5 至完整 W0~W6**，素材來源：`SD_Improving_07.md` 各 Wave + `SD07_Migration_Guide.md` §1 完成範圍 + `gate_audit.md §1-quinquies` 簽核細節。

**Wave 預估**：W0（骨架）+ W6（完成）共 2 端點。

**核心交付**：
- `sprint_history.md` v1.2 — §1.5 SD_07 完整 W0~W6 詳細紀錄（≥ 300 行，仿 §1.4 SD_06 200+ 行格式）
- CLAUDE.md 維持單行 link（SD_07 → §1.5）
- `wc -l CLAUDE.md ≤ 400` 維持
- 議題索引表 §2 新增 SD_09 對應條目

### 1.6 議題 F：trace_id multi-process 邊界（**SD_08 L1 限制處理**）

**主軸**：解決 `trace_id` 在 subprocess 邊界不傳播問題。

**Wave 預估**：W0（三方研究 + PM 拍板）+ W3（落地，依路徑而定）。

**評估方向**（**擇一，不可組合**；ADR-SD09-004 §2 明訂）：
- **(a)** 透過環境變數 `AUTOCLAUDE_TRACE_ID` 跨 subprocess 傳播；importlinter Rule 7 覆蓋；T3-F* 新增 3 case；**AC16=2**（SA-M5 條件式條目；對應路徑 a）
- **(b)** 自建 W3C TraceContext header 解析（為 SD_10 OTel 過渡）；**Rule 8 取消新增**（Arch-M3 / SD-M2 修復；Rule 7 已覆蓋；改採 contract test `test_trace_context_plugin_isolation.py` ≥ 2 case）；T3-F* 新增 4 case；**AC16=3**（路徑 b）
- **(c)** 延 SD_10 OTel 整合一次處理；本 Sprint 不落地；**議題群降級為 SD_10 backlog 評估報告**（不佔 SD_09 Wave 範圍）；W3 任務全刪；**AC16=1**（路徑 c — 延期決議紀錄）

**subprocess 注入點全覆蓋清單**（路徑 a/b 共用；**SD-C5 修復：9 處檔案明確列舉**）：
1. `autoclaude/perception/pty_wrapper.py`（PTY subprocess 啟動）
2. `autoclaude/execution/cross_step_validator.py`（git status 偵測 subprocess）
3. `autoclaude/execution/pre_run_validator.py`（pre-run 環境檢查）
4. `autoclaude/execution/evaluator.py`（evaluator_command 子進程）
5. `autoclaude/execution/mutation_applier/_conditional.py`（mutation 條件評估）
6. `autoclaude/plugins/fast_path_plugin.py`（fast-path 子進程）
7. `autoclaude/plugins/token_guard/git_verifier.py`（git verifier subprocess）
8. `autoclaude/decision/prompt_builder.py`（prompt 建構 subprocess 呼叫）
9. `autoclaude/core/services/mutation/_conditional_evaluator.py`（mutation 條件評估）

**集中式 helper（補強建議 1）**：避免 9 處散裝改動遺漏，於 `autoclaude/utils/trace_context.py` 內聚 `propagate_to_subprocess_env(env: dict) -> dict` helper；9 處統一呼叫。

**env override 衝突處理**：caller 已設 `AUTOCLAUDE_TRACE_ID` 時不覆蓋（路徑 a）；caller 已設 `TRACEPARENT` 時不覆蓋（路徑 b）。

**前置研究**：SD_09 W0 三方獨立評估三選項可行性 + PM 拍板。

### 1.7 議題 G：KB metric 落地（**SD_08 L2 限制處理**）

**主軸**：`KnowledgeBaseMetrics` 純記憶體統計 → 落地（跨 session 統計）。

**Wave 預估**：W0（三方研究 + PM 拍板）+ W2~W3（若落地）。

**評估方向**（**擇一，不可組合**；不破壞 SD_06 storage.mode 三後端架構）：
- **(a)** PG `kb_metrics` 表 + alembic 0015 migration + nightly aggregation；新增 `IKbMetricStore` port + Pg adapter（**R41 canonical 命名訂正**：SD-C4 原改名歸 `IObservabilityMetricStore` 之理由「避免與 memory_store 衝突」經 R41 軸 D 預研判定不成立 — `kb_metric_store` 與 `memory_store` 實際無命名衝突，且 Execution Guide T2-G1/G2 + R40 NextAction + 用戶口徑一致用 `kb_metric_store`，故 canonical 回正為 `IKbMetricStore`，詳見 [SD09_AxisD_Prep_Research.md §B.1](../06_quality/SD09_AxisD_Prep_Research.md)）；**Snapshot Port 列表 9 → 10**（Arch-M5 修復）
- **(b)** **刪除**（首輪 SD M2 建議刪除 SQLite 選項，避免破壞架構）
- **(c)** 延 SD_10 OTel + Prometheus 替代；本 Sprint 不落地；**議題群降級為 SD_10 backlog 評估報告**（不佔 SD_09 Wave 範圍）；W2~W3 任務全刪

**IKbMetricStore port spec 草案**（**SD-C4 修復；R41 canonical 命名訂正**；W0 三方研究 + PM 拍板選 (a) 後落地 `ADR-SD09-006-kb-metric-port.md`）：

| 方法 | 簽名 | 用途 |
|------|------|------|
| `record_counter` | `record_counter(name: str, delta: int) -> None` | 計數器累加 |
| `record_histogram` | `record_histogram(name: str, value: float) -> None` | 直方圖樣本 |
| `snapshot` | `snapshot() -> dict[str, MetricValue]` | 當前快照 |
| `flush` | `flush() -> None` | 強制寫入後端 |
| `query_window` | `query_window(metric: str, since: datetime) -> list[MetricValue]` | 視窗查詢 |

**kb_metrics 表欄位**（議題 G 選 (a) 時 alembic 0015 落地）：
```sql
CREATE TABLE kb_metrics (
  metric_id uuid PRIMARY KEY,
  metric_name text NOT NULL,
  value double precision NOT NULL,
  window_start_at timestamptz NOT NULL,
  window_end_at timestamptz NOT NULL,
  run_id uuid,
  tags jsonb DEFAULT '{}'::jsonb
);
```

**yaml_only 模式 fall-back**：路由至 `LocalKbMetricStore`（in-memory or jsonl 寫入 `.kb_metrics_local.jsonl`）；確保 `storage.mode` 切換時 metric 不孤兒（對應 R-SD09-G-1 緩解）。

**前置條件**：SD_08 觀察期 30 天統計需求評估（若 SLA 不變則可延 SD_10）。

---

## 2. Wave 預估（待三方研究 + PM 拍板細化）

| Wave | 範圍 | 對應議題群 | 預估 Gate 測試基線 |
|------|------|----------|------------------|
| **W0** | SD_08 收尾 + ADR-SD09-001~005 草案 + AC4 labeled PR 啟用（議題 C）+ F/G 三方研究 + PM 拍板 | C + E（骨架）+ F + G + 規劃 | ≥ 2,094（持平）|
| **W1** | mutation pilot 擴展 GoalSynthesis（議題 B 上半，TG 退出 nightly）| B | ≥ 2,098（+4 contract test）|
| **W2** | mutation 擴展 Coordinator（議題 B 下半，GS 鎖定後）+ perf machine 採購評估（議題 D 上半，PM 預算簽核）+ KB metric 落地若 (a)（議題 G）| B + D + G(若 a) | **G(a) +5 case / fall-back +3 case / G(b)/(c) +3 case**（SD-m3 修復）≥ 2,103 / 2,101 |
| **W3** | PG production SOP §4-§5 補完（議題 A 上半）+ AI-Agent dry-run + trace_id multi-process 落地（議題 F 若 a/b）| A + F(若 a/b) | ≥ 2,110（+7：6 SOP contract + 3 trace 或 4 trace；分項 = contract + utils + integration test，SD-M5 修復）|
| **W4** | PG production SOP §6-§8 補完（議題 A 中半）+ perf machine 啟用（議題 D 下半）+ 人類 DBA 親演 | A + D | ≥ 2,120（+10：6 SOP §6-§8 contract + 3 perf 三軌 + 1 DBA dry-run）|
| **W5** | 真實 PG production 上線（議題 A 下半，雙條件齊備 + 人類 PM 親簽）| A | ≥ 2,123（+3：4 cutover_precondition contract）|
| **W6** | SD_09 Migration Guide v1.0 + SD_07 滾動下沉至 sprint_history §1.5（議題 E 完成）+ 四方審查 + SD_10 大綱 | 收尾 + E | **≥ 2,523 軟目標 / ≥ 2,513 硬底線**（W3 Round 4 audit P0-AUDIT-R3-2 修復後實測 2,505 已超 SD_08 W6 基線 2,094 + 411；含 ADR-SD09-008 ac4 雙軌測試 +10 + Round 4 mutation sha 強化 +3 case）|

> **基線變動敏感性**（**W3 Round 4 audit P0-AUDIT-R3-2 修復後再次校準**）：
> - **(b) PM 拍板路徑（finalized 2026-05-20）**：W6 軟目標 ≥ 2,523 / 硬底線 ≥ 2,513；累計 AC 41 條（不含 ADR-SD09-008 待 PM 拍板）
> - **W3 Round 4 實測基線**：2,505 passed / 122 skipped（W0 補測 +319 + W3 Round 3 ac4 雙軌 +10 + W3 Round 4 mutation sha 強化 +3 case）
> - **歷史三路徑骨架**（PM 拍板前評估，保留 §3.A AC Matrix 附錄）：(a) ≥ 2,125 / (b) ≥ 2,126 / (c) ≥ 2,122
>
> **AC16 動態條目數對照（SA-C1 修復）**：路徑 a → 累計 40；路徑 b → 累計 41；路徑 c → 累計 39（皆 ≥ 35 門檻 ✅）。

---

## 3. 預期 ADR（W0 啟動前 PM 形式核准）

- **`ADR-SD09-001`**：PG db_only 切換不可逆轉折點（業務語意；接續 ADR-SD08-005 §2.2）；§2 明訂同 process trace_id GA = W5 條件 / multi-process GA 延 W6 / SD_10；§2.5 物理回退範圍限制
- **`ADR-SD09-002`**：mutation 全模組擴展策略（**單一時間 1 個 active pilot module**；TG 鎖定後改週 baseline 抽測；W1/W2/W3 三階段排程；UTC cron 排程）
- **`ADR-SD09-003`**：perf 雙軌轉三軌（CI + perf machine + 開發機驗證；**緊急路徑明訂**；marker 配置走 pyproject.toml）
- **`ADR-SD09-004`**：trace_id multi-process 邊界傳播方案 — **§2 明訂三選項擇一 + 對應 importlinter contract 結果矩陣**（a → Rule 7 覆蓋；b → Rule 7 已覆蓋改 contract test，**Rule 8 取消新增**；c → 0 變動）+ §3 W3C parser 內聚 `trace_context.py` 不新建模組 + §3.0 LOC 影響分析（建議標 contract tier ≤ 400）
- **`ADR-SD09-005`**：PG canary 三階梯閾值 — 10% / 24h + 50% / 48h + 100% / 7d + 三觸發回滾條件（drift `severity != 'info'` / WAL lag CRITICAL / 連線數異常）+ rollback SLA 拆兩段（自動 ≤ 3min / 取證 ≤ 30min）+ race condition 處理
- **`ADR-SD09-006`**（**SD-C4 新增條目；R41 canonical 命名訂正**；**僅在 W0 PM 拍板議題 G 選 (a) 後產出**）：`IKbMetricStore` port + kb_metrics 表 schema + LocalKbMetricStore fall-back；草案位置 `docs/04_planning/ADR/ADR-SD09-006-kb-metric-port.md`

---

## 4. 已知風險（暫定，待 SD_09 W0 啟動時補入 risk_log §15）

| ID（暫）| 風險 | 嚴重度 | 緩解方向 |
|--------|------|--------|---------|
| R-SD09-A-1 | 真實 staging（≥ 1M 列）跑 失敗或 drift_log > 0 | 🔴 | W3 前 dry-run 演練（AI-Agent 模擬）+ 人類 DBA 親演前置 |
| R-SD09-A-2 | 人類 DBA 親簽延期超過 SD_09 範圍 | 🟠 | W4 中段必須完成 DBA 親演 → 不阻塞 W5 上線；fall-back：DBA 親演失敗 → W5 推遲至 SD_10，W6 仍可收尾文件與 mutation |
| R-SD09-A-3 (**新增**) | W3 AI-Agent dry-run 失敗（≥ 1M 列模擬失敗）| 🔴 | fall-back：回 W2 修補 schema/index → 不阻塞 W4 SOP §6-§8 文件補完，但阻塞 DBA 親演（紅線 ❌21） |
| R-SD09-A-4 (**新增**) | W5 雙條件未達（可觀測性 GA OR drift_log 任一未達）| 🔴 | fall-back：不切換 db_only，維持 `both` mode；W5 G5 改判 conditional pass；切換動作延 SD_10；ADR-SD09-001 §2.3 明訂例外條款 |
| R-SD09-B-1 | GoalSynthesis 首測 mutation < 60% baseline | 🟠 | 同 SD_08 fall-back（產出 Report + 補測 backlog）；W2 Coordinator 不受阻 |
| R-SD09-B-2 (**新增**) | mutation 並行 nightly 超時（GS + Coord 同時跑 > 45 min）| 🔴 | ADR-SD09-002 §2.3 拆 3 個獨立 cron job + TG 退出 nightly；單 nightly job 僅 1 module step |
| R-SD09-D-1 | perf machine 採購延期超 W4 上線時程 | 🔴 | W2 上半確定預算 + 採購方案；緊急路徑：採購未簽核 → 議題群整體延 SD_10，W4 G4 不阻塞 |
| R-SD09-F-1 | trace_id multi-process 方案選 (b) 自建 TraceContext 超出 W3 估算 | 🟠 | W0 三方研究 + PM 拍板選 (a) 或延 SD_10 |
| R-SD09-F-2 (**新增**) | multi-process trace_id 30 天觀察視窗無法在 W5 達成 | 🔴 | ADR-SD09-001 §2 明訂 W5 = 同 process trace_id GA 即可（multi-process GA 延 W6 / SD_10） |
| R-SD09-G-1 (**新增**) | KB metric 落地 PG 後跨 storage.mode 三後端切換時 PG metric 表孤兒 | 🟠 | ADR-SD09 補設計「IKbMetricStore port + Local/Pg adapter 雙軌」確保 yaml_only 模式仍可運作 |
| R-SD09-O-1 (**v0.4 zero-trust audit 新增**) | `tools/observability_ga_check.py` 不存在，但 ADR-SD09-001 §2.5/§2.6 + SD09_Execution_Guide T0-O1 列為 W5 切換硬性條件唯一取證工具 | 🔴 W0 啟動前必修 | (a) W0 T0-O1 補 stub W0 完成；(b) 完整實作延 SD_10。詳見 [risk_log.md §15](../05_development/risk_log.md) + [SD09_Pre_W0_Audit_Findings.md](../05_development/SD09_Pre_W0_Audit_Findings.md) |
| R-SD09-A-5 (**v0.4 zero-trust audit 新增**) | `alembic_version=0012_yaml_import_staging`，但 0013_drift_log + 0014_config_audit_log 已落地未跑 → 觀察期 #3 取證 SQL 恆失敗 | 🔴 → 🟢 **根因已消除 2026-08-03** | ~~W0 G0 預檢加 `alembic upgrade head` step~~ → **改列獨立前置動作 `P-0`，不再掛在 G0 底下**（死鎖解除，見 §8.3 D-2）；補 fixture 場景 A fall-back。**事實層**：唯讀實查 `alembic_version=0018_version_kind_discriminator`＝鏈頭、`drift_log` 表存在 ⇒ P-0 對本機為 no-op。詳見 [risk_log.md §15](../05_development/risk_log.md) + [SD09_Pre_W0_Audit_Findings.md](../05_development/SD09_Pre_W0_Audit_Findings.md) |
| R-SD09-CI-3 (**v0.4 zero-trust audit 新增**) | CI nightly 4 個 job 全 `continue-on-error: true` 共 11 次掩護失敗 6+ 個月；R-SD08-D-1 / PM-#3 監控空跑 = 虛假狀態 | 🔴 重大架構異動風險 | 待 PM 拍板 Z1/Z2/Z3 後執行。詳見 [risk_log.md §15](../05_development/risk_log.md) + [SD09_Pre_W0_Audit_Findings.md](../05_development/SD09_Pre_W0_Audit_Findings.md) |
| R-SD09-A-5-LOOP (**2026-08-03 新增；同日處置；§8.3 D-2**) | **R-SD09-A-5 的緩解措施自身構成死鎖**：觀察期 #3 達標 ← drift_log 表存在 ← `alembic upgrade head` ← 該緩解措施 (d) 明載「待 **W0 G0 預檢**執行」 ← W0 G0 需 #3 達標。**已實際發生**：2026-06-02 那筆 `drift_log_table_exists=false` 打斷 green_streak，是 #3 未達標的唯一原因 | 🔴 → 🟢 **已解** | **【已落實】把 `alembic upgrade head` 從「W0 G0 預檢」前移為與 G0 無關的獨立前置動作 `P-0`**（不需 G0 授權、不吃 W0 資源、不改應用碼）。同型（閘門擺錯位置）先例＝[ADR-SD09-013](ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md)。**事實層另已解除**：2026-08-03 唯讀實查 `alembic_version=0018_version_kind_discriminator`＝鏈頭、`drift_log` 表存在 ⇒ P-0 對本機為 no-op，#3 只需再累積 **4 筆**綠紀錄。詳見 §8.3 D-2 + [SD09_Execution_Guide.md §0.1-P0](../05_development/SD09_Execution_Guide.md) + [risk_log.md §15](../05_development/risk_log.md) |
| R-SD09-GATE-NOCARRIER (**2026-08-03 新增；§8.3 D-4/D-5**) | **判準／deadline 沒有偵測者**：(a) `tools/drift_log_ga_check.py`（#3 權威判準）零 production caller；(b) 舊載體 `g0_gate_check.ps1:41/63` 標籤寫 `#3 obs/drift` 但只查 obs GA；(c) 新載體 nightly G0 三軌 = mutation/ac4/**obs_ga**，不含 drift，且進度行印原始列數 `drift=34/30`（誤導為已達標）與較嚴 counter `mutation=5/7`（誤導為未達標）；(d) §6 PM #6(b)「最遲 2026-06-26」逾期 38 天無人察覺 | 🔴 → 🟡 **部分緩解 2026-08-03** | ✅ **(a)(c)(d 之偵測面) 已修（R71 G-1/G-3）**：`drift_log_ga_check.py` 已由 `Get-DriftGaPass` 接進 nightly 收尾、G0 擴為四軌、進度行四軌分子一律取權威判準值、`$G0_MUTATION_UNIQUE_SHA_TARGET` 已刪改問 `should_lock`（ADR-SD09-013 §3.3 L-3 落地）。<br>🟡 **殘留**：(b) 舊載體 `g0_gate_check.ps1` 標籤錯置（已非唯一管道，危害降級）；**(d) deadline 逾期本身仍無偵測者**（§8.3 D-4 規格已交付、實作未落地）。詳見 [risk_log.md §15](../05_development/risk_log.md) |

---

## 5. 對應 SD_08 風險收尾移交

從 [risk_log.md §14](../05_development/risk_log.md) 移交 SD_09 監控：

| ID | 移交說明 |
|----|----------|
| **R-SD08-D-1** | mutation score 首測 < 65%（observing 2026-05-19~2026-06-01）→ SD_09 §1.2 議題 B 接續 |
| **R-SD08-PM-#3** | mutation pilot 單模組 fall-back（< 60%）→ SD_09 §1.2 議題 B 接續 |

---

## 6. PM 拍板決議（待 W0 拍板，**新增章節 — SA C2 修復**）

仿 SD_08 v1.0 §6 結構；W0 啟動前 PM 形式核准後填入。

| # | 項目 | PM 待決選項 | 影響 | 拍板日 | 拍板人 | commit SHA |
|---|------|------------|------|--------|--------|-----------|
| **1** | 議題群優先順序 | **(a) A→B→C→D→E→F→G**（本文件預設） | Wave 範圍 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **2** | mutation 擴展批次（議題 B）| **(a) W1 GS + W2 Coord 嚴格序列**（紅線 ❌19 禁並行）| W1~W2 排程 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **3** | perf machine 預算上限（議題 D）| **(b) ≤ $200/月租用**（成本/訊號平衡）| W2 採購評估 + W4 啟用 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **4** | 【擇一】trace_id multi-process 三選項（議題 F）| **(b) W3C TraceContext**（相容 OTel 過渡；Rule 8 取消改 contract test）| W3 落地範圍 + AC16=3 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **5** | 【擇一】KB metric 落地（議題 G）| **(a) PG 落地**（W2~W3 補 Wave + Snapshot Port 9→10 + ADR-SD09-006）| W2~W3 範圍 + AC 條目數 +1 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **6** | 啟動日 | **(b) 2026-06-26 硬 deadline**（觀察期 #1/#2/#3 三項全達時可提前至 2026-06-18~22；保守 1 週緩衝指「PM 決策緩衝」非觀察期緩衝。v1.4 zero-trust audit SA 補述語意精準化）| Sprint 時程 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **7** | PG db_only 灰度百分比階梯（議題 A）| **(a) 10/50/100 × 24h/48h/7d**（本文件預設）| SOP §4 + ADR-SD09-005 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **8** | DBA 親演排程（議題 A）| **(a) W4 中段**（紅線 ❌21 順序合規）| W4 G4 阻塞條件 + R-SD09-A-2 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **X** | 觀察期 #2 解封路徑（**Pre-W0 audit 新增**）| **X1 補實作 seed_kb.py + 100 query fixture**（~1.5 PD；唯一保留 AC4 真實驗證信號）**— v1.4 SA 補述**：PM 已明確授權 X1 路徑執行；`tools/seed_kb.py`（204 LOC mock 完整 + BGE-M3 graceful stub）+ `tests/fixtures/pgvector_real_queries.json` / `pgvector_real_ground_truth.json` 已 commit；hardcoded skip 已改 conditional fixture-side skip | R-SD09-CI-2 → 🟢 緩解 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **Y** | 10 項缺檔策略（**Pre-W0 audit 新增**）| **Y1 全部補實作**（F-01~F-09 + ADR-SD09-006；~3~5 PD）| W0 啟動阻塞解除；紅線 ❌21 三項齊備 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **Z** | CI nightly gate 化（**Pre-W0 audit 新增**）| **Z1 全面移除 continue-on-error**（11 處 + 3 處 \|\| true 保留 mutmut 特性）| R-SD09-CI-3 → 🟢 緩解 | 2026-05-19 | PM (zero-trust) | 7883fe3+ |
| **9** | 觀察期 #1 unique sha 入場死鎖處置（**2026-08-03 新增**）| **(b) 判定為條件設計缺陷 — 以「kill_rate streak 7/7 已達標」放行 W1；unique source_sha256 ≥ 7 移為 W1 內部（出場）驗收**。理由：一個必須先啟動才能滿足的啟動條件，本身就不是有效的啟動條件。<br>否決之選項：(a) 維持現狀繼續等（數學上不可解，見 [ADR-SD09-013](ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md) §1.1）| **W1 入場解除阻塞**；⚠️ **這是放寬**：文件字面／nightly G0 counter 的入場門檻由 7 unique sha 降為 5（差額 2 個相異源碼版本移至出場補齊，並新增 X-2「每個 sha 需對應一筆實質變更 commit」之取證要求）。風險承擔者＝PM，風險評估 🟡 中低，見 ADR-SD09-013 §6.2 | **2026-08-03** | **PM（掌舵者）** | *待填* |

> **2026-05-19 PM zero-trust audit 拍板補述（編號 1~8 全數定案 + X/Y/Z 三組新增）**：使用者明確授權「不顧預算徹底補做」 → X/Y/Z 三組皆採最完整路徑；W0 工程量估 4.5~6.5 PD（X1 1.5 + Y1 3~5）；啟動日 2026-06-26 已含緩衝。**Tech Lead 收到本拍板後即可啟動 W0 task breakdown**。
> 編號 1~8 PM 預設選項拍板理由：(1)(a) 維持原規劃；(2)(a) 紅線 ❌19 禁並行；(3)(b) ≤$200/月租用平衡成本/訊號；(4)(b) W3C TraceContext 相容 OTel；(5)(a) PG 落地 + Port 9→10 + ADR-SD09-006；(6)(b) 2026-06-26 保守緩衝；(7)(a) 10/50/100 × 24h/48h/7d 預設；(8)(a) W4 中段紅線 ❌21 合規。
> **W0 啟動條件**：11 項 PM 拍板完成 + 本文件升至 **v1.0**。

---

## 7. 三方獨立研究意見摘要（**v1.0 T0-1 已填實 13 bullet** — SA C2 修復新增章節）

仿 SD_08 v1.0 §7 結構；Architect / SA / SD / QA 四方獨立研究後填入。

> **填寫狀態**：**13 bullet 全 CLOSED**（每 bullet ≥ 50 字含建議方案 + 取捨理由 + 風險指認；T0-1 v1.0 2026-05-20）。
>
> **v1.4 zero-trust audit SA 補述（2026-05-20）**：本章節實際 13 bullet（Arch 4 + SA 3 + SD 3 + QA 3）— Architect 對議題 A/D/F/G 各 1（共 4）+ SA 對議題 A/B/C 各 1（共 3）+ SD 對議題 A/B/G 各 1（共 3）+ QA 對議題 B/F + W5 雙條件可測性 各 1（共 3）= 13。先前文件多處沿用「12 bullet」係 M-06 修復初期估算未含 QA 議題 H bullet，本次補正。

### 7.1 Architect 意見（議題 A/D/F/G）

- **議題 A**：canary 三階梯 10/50/100 × 24h/48h/7d 經 ADR-SD09-005 §2.2 race condition 處理後可控；RACI 矩陣已銜接 SD_08 W5 SOP §1-§3（DBA / SRE / Tech Lead / PM 四角色）；業務不可逆語意（ADR-SD09-001 §2.5）明訂 pgvector embeddings 物理回退損失場景由 PG → YAML dump 工具 (`tools/pg_dump_to_yaml.py`) graceful degrade 涵蓋；零信任 audit 確認工具完整實作（208 LOC）。**風險指認**：30 天觀察期間若任一階梯 drift severity != 'info'，rollback SLA 拆 ≤3min（自動）+ ≤30min（取證）。
- **議題 D**：採購方案經 PM #3 拍板 (b) ≤ $200/月雲端 GPU instance（建議 AWS g4dn.xlarge 或 Azure NC6s_v3）；CPU bare metal 對 pgvector HNSW recall p95 影響顯著（業界基準 GPU vs CPU 3~5× 加速）；季度校準週期對齊既有 nightly perf machine 排程（每季首週末 7 runs 鎖 baseline）；緊急路徑 R-SD09-D-1 明訂預算未簽核 → 議題 D 延 SD_10、W4 G4 不阻塞。
- **議題 F**：PM #4 拍板 (b) W3C TraceContext；OTel 相容性透過 `propagate_to_subprocess_env()` helper + `TRACEPARENT` 格式內聚 `trace_context.py`，無需新增模組；ADR-SD09-004 §3.1 取消 Rule 8 改 contract test `test_trace_context_plugin_isolation.py`（193 LOC，3 case）；9 處 subprocess 注入點集中式 helper 設計避免散裝改動遺漏，每處統一呼叫 `propagate_to_subprocess_env(env)`；env override 衝突處理：caller 已設 `TRACEPARENT` 時不覆蓋。
- **議題 G**：PM #5 拍板 (a) PG 落地，新增 ADR-SD09-006 `IKbMetricStore` port（第 10 個）+ `Pg`/`Local` 雙 adapter + alembic 0015 `kb_metrics` 表 + importlinter Rule 7→8；`LocalKbMetricStore` yaml_only fall-back 完整度：路由至 `.kb_metrics_local.jsonl` 落地；factory.py 對齊 storage.mode 三後端模式；跨 storage.mode 切換時 R-SD09-G-1 mitigation 為雙 adapter 設計保證 metric 不孤兒。

### 7.2 SA 意見（議題 A/B/C）

- **議題 A**：SOP §4-§8 文件結構：§4 切換時序（10%/50%/100% 灰度三階梯）/ §5 回退（drift_log 取證 + PG → YAML import 工具）/ §6 監控 dashboard（WAL lag / 連線數 / drift 計數）/ §7 RACI（DBA / SRE / Tech Lead / PM）/ §8 演練回顧（30 天觀察期 + AI-Agent 模擬 + 人類 DBA 親演）；三階梯時間表合理性：ADR-SD09-005 §2.1 對齊業界 canary deployment 最佳實踐（24h/48h/7d）；DBA RACI 與既有 SD_08 W5 SOP §1-§3 銜接點明訂於 `Production_Migration_SOP.md` §0.4 RACI 表格。
- **議題 B**：mutation 排程拆分策略已落地 (autoclaude-ci.yml 3 個獨立 cron jobs)：TG 03:00 UTC active / GS 04:00 UTC dormant / Coord 05:00 UTC dormant；TG fall-back 矩陣（ADR-SD09-002 §2.1.1）對 W1 進入點影響：若 TG < 60% baseline → W1 改進入 SD_10 pilot active，GS 直接啟用 W1 nightly；UTC 日界統計實作以 `_utc_date_of()` helper 同 module + 同 UTC date 去重，避免重複跑刷數（M-05 修復）。
- **議題 C**：AC4 labeled PR 升級時機 = 觀察期 #2 14 天 nightly 全綠（PM #2 拍板門檻 recall@10 ≥ 0.95 / p95 < 50ms / cb_open = 0 / σ_14d ≤ 0.02）；達標判定由 `tools/ac4_progress_check.py` 回報 `ready_for_labeled_pr=true`；黃線 3 次 / 紅線 5 次告警閾值對齊 SD_08 W2 T2-C3 既有規範；零信任 audit X1 路徑落地後 fixture (`pgvector_real_queries.json` + `pgvector_real_ground_truth.json`) 已 commit 至 repo，nightly 可實質執行 recall 量測。

### 7.3 SD 意見（議題 A/F/D）

- **議題 A**：canary 路由設計採 PostgreSQL `pg_hba.conf` + connection pool 雙閘；rollback SQL 範本由 ADR-SD09-005 §2.3 規範（`UPDATE config SET storage_mode='both' WHERE id=1`），自動 ≤ 3 min 觸發；PG dump → YAML 工具 (`tools/pg_dump_to_yaml.py`) schema mapping 表對齊 7 個表（playbook_runs / checkpoints / knowledge_entries / playbook_versions / drift_log / config_audit_log / kb_metrics）；datetime → ISO-8601 / UUID → str / JSONB → dict；graceful degrade（無 DSN / sqlalchemy / 連線失敗 → 寫 dump_metadata.json 標 unable + exit 0）。
- **議題 F**：9 處 subprocess 注入點全覆蓋清單已落地（pty_wrapper / cross_step_validator / pre_run_validator / evaluator / mutation_applier/_conditional / fast_path_plugin / token_guard/git_verifier / prompt_builder / services/mutation/_conditional_evaluator）；集中式 helper `propagate_to_subprocess_env()` 內聚於 `autoclaude/utils/trace_context.py`；contract test 替代 Rule 8 覆蓋完整度：AST 掃描禁直接 import + IObservabilityPort Protocol contract + propagate_to_subprocess_env None 安全性 3 case 全覆蓋。
- **議題 D**：perf machine self-hosted runner 採 GitHub Actions self-hosted runner（ssh 手動風險：跑完忘記停機 → 月租超支）；pyproject.toml marker 配置以 `[tool.pytest.ini_options]` `markers` 註冊 `pgvector_perf_machine_only` + addopts `-m "not pgvector_perf_machine_only"` deselect 預設；既有 `pg_real` marker 行為相互作用：兩 marker 互斥不同時觸發，避免 nightly CI runner 誤跑 GPU 測試。

### 7.4 QA 意見（議題 B/F + 量測可行性）

- **議題 B 可行性**：wall time 估算 — TG single nightly run 25~35 min / GS estimated 30 min / Coord estimated 40 min（單檔精準 `--paths-to-mutate=autoclaude/core/orchestration/coordinator.py`）；`-p no:xdist` 鎖序列避免 hash 衝突（mutmut 3.x 工具特性）；nightly 拆分 PD 估算：3 jobs 並行 cron 排程（03/04/05 UTC），單檔 timeout-minutes 45 涵蓋；mutation_baseline_lock.py 連續 3 次缺記錄重置觀察期判定可行性：M-05 修復後 UTC date 去重 + 空 log guard（B-03）兩重保護，連續 7 次達 ≥ 70% 鎖定 baseline 為硬條件。
- **議題 F**：contract test case 設計三大類別：(1) AST 掃描禁直接 import / (2) Port Protocol contract / (3) Helper 安全性；fixture 規範：`tests/contract/test_trace_context_plugin_isolation.py` 193 LOC ≤ 400 contract tier；9 處 subprocess 注入點覆蓋驗證方法：每處 caller 跑單元測試確認 `env=propagate_to_subprocess_env(...)` 已傳入；端對端跨進程驗證透過 `tests/integration/test_trace_id_subprocess_e2e.py`（W3 補建）以子進程啟動 + stdout 解析驗證 trace_id 傳播。
- **W5 雙條件齊備可測性**：30 天 jsonl fixture（`.observability_history.jsonl`）採 daily append 邏輯，schema 鎖定於 `tools/observability_ga_check.py` `_is_green()` 函式（emit_count > 0 + trace_id_continuity == true + KB metric 4 鍵齊備）；drift_log mock 設計透過 `tests/contract/fixtures/drift_log_30day_zero.json`（30 筆 severity=info rows，alembic 0013 schema 對齊）；個人開發 fall-back fixture 路徑：場景 A 無 PG 時跑 `_PG_DSN is None` 整檔 skip → 改以 fixture 加載驗證形式（drift_log_30day_zero.json + observability_history fixture）作為 vacuous true 替代。

---

## 8. 啟動條件清單（**SA C4/C5 + QA M3/M4 修復**）

### 8.1 三觀察期一覽表

> **🔴 SSOT 註記（R42 audit 修復，2026-05-28）**：本 §8.1/§8.2 為 2026-05-20 v1.0 快照，觀察期條件/日期之 **live SSOT 以 [SD09_Execution_Guide.md §0.1](../05_development/SD09_Execution_Guide.md) + 最新 RoundXX NextAction 為準**。下表已同步以下後續拍板：(1) **#2 已由 [ADR-SD09-008 v0.4](ADR/ADR-SD09-008-ac4-tolerant-track.md) 2026-05-25 拍板**改為 **60ms tolerant 升級門檻、結束日原投影 2026-06-08 → R55 forensic 訂正 ~2026-06-16**（`ac4_progress_check.filter_recent` 為過去 14 日曆天滾動窗口需 14 連續筆，對 schtasks 漏跑日 05-22/23、05-30/31、06-02 高度敏感，非「+1/日」累計；最後缺口 06-02 → 需 06-03~06-16 連續無缺口，任一漏跑即順延）（原「pg_real skip 阻塞 / X1-X3 拍板」缺口已透過 tolerant 雙軌制解決，不再阻塞）；(2) **#1 已由 [ADR-SD09-013](ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md) 2026-08-03 PM 拍板 (b) 解除入場阻塞**（unique sha ≥ 7 移為 W1 出場驗收；R47 audit §11.6「需 W1 active 改源碼、idle 凍結」之敘述經 2026-08-03 實查已被事實推翻——W1 未啟動期間 token_guard 源碼仍自然演進出 4 個新 sha）。

| # | 觀察期 | 起算日 | 結束日 | 失敗回退 |
|---|--------|--------|--------|---------|
| **#1** | mutation pilot TokenGuardPlugin 連續 7 次達 ≥ 70%（target 75% − tolerance 5% − ±2pp = **68% effective threshold**）。**✅ 已達標，不再阻塞 W1**（[ADR-SD09-013](ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md) 2026-08-03 PM 拍板 (b)）：入場判準 = E-1 tail 7 筆 kill_rate 全 ≥ 68%（實測最小 **0.7071**）+ E-2 `should_lock()` 回 `True` 且 baseline 已寫入（實測 `(True, 0.7071…)`；`.mutation_baseline.toml` `token_guard = 0.7071` **鎖定於 2026-07-22**，取證 `logs/nightly_2026-07-22_183551.log:261`）。**紀律 #12 tail 7 筆 unique source_sha256 ≥ 7 已移為 W1 出場驗收 X-1/X-2**（現值 5 unique + 2 筆 legacy 缺欄位）。本地透過 Docker / Linux mutmut，見 ADR-SD09-002 §2.7 | 2026-05-19 | **✅ 2026-07-22 達標（baseline locked）** | < 60% → SD_10 接續 pilot（不阻塞 SD_09 W0；R-SD08-PM-#3 + R-SD09-CI-1）；W1 出場 X-1 未達 → ADR-SD09-013 §5.1 三階梯處置 |
| **#2** | AC4 14 天 nightly 全綠（本地 `tools/run_local_nightly.ps1` artifact 累計）— **升級門檻 p95 < 60ms tolerant**（ADR-SD09-008 v0.4 ACCEPTED 2026-05-25）；strict 50ms 降為觀察指標 `strict_streak` 持續採集。**⏳ 未達標：2026-08-03T02:57Z 實測 `observation_days=8/14`、`ready_for_labeled_pr=false`**；判準本身之日曆連續問題由 [ADR-SD09-012](ADR/ADR-SD09-012-ac4-observation-decouple-calendar.md) 處理 — **PM 已於 2026-08-03 拍板**採用 gap-tolerant green_streak（門檻仍 14、反作弊零改動），🔴 **判準 code 尚未實作（NOT LANDED）**，落地清單見該 ADR §7.1 | **2026-05-26**（新口徑首筆 jsonl）| ~2026-06-16（R55 forensic 訂正；實際未達，滾動窗口任一漏跑即順延）| 黃線 3 次 / 紅線 5 次告警；未達 → W0 T0-C2 延期或議題 C 延 SD_10 |
| **#3** | drift_log 30 天零事件（SD_08 W5 落地起算；本地腳本 drift_log-scan stage 每日掃描）。**⏳ 未達標，但已無阻礙、會自然到達**（見下方 🔴 #3 複核註記 + §8.3 D-2）| 2026-05-18 | **未達**（2026-08-03T02:57Z 實測 `green_streak=26 < window=30`，rc=1）→ **尚差 4 筆綠紀錄**；根因（alembic head 落後）**已消除**，**不需人工介入**，最快 4 個採集日達標 | 任一 drift > 0 → W5 雙條件未達 → fall-back R-SD09-A-4 |

> **🔴 #3 複核註記（2026-08-03 zero-trust 複核，推翻先前「早已達標」之口語判斷）**
>
> 判準原文為「30 **天**零事件」，其**權威判定工具**為 [`tools/drift_log_ga_check.py`](../../tools/drift_log_ga_check.py)：
> `green_streak` = 由最後一筆往回**連續** `passed=true` 的**紀錄筆數**（每筆 = 一個 UTC 採集日，同日去重），需 ≥ `--window`（預設 **30**）。
> `passed` 之定義來自 [`tools/drift_log_snapshot.py:55`](../../tools/drift_log_snapshot.py) `build_record()`：`drift_log_table_exists AND severity_non_info_count == 0`。
>
> **初次實跑**（`.venv/Scripts/python.exe tools/drift_log_ga_check.py --json`，rc=1；**⚠️ 此為 02:00 nightly 寫入前之值，已被下方複核重測取代**）：
> ```json
> {"status": "observing", "green_streak": 25, "window": 30, "total_records": 34,
>  "last_failure_reason": "drift_log_table_exists=False (alembic head 落後)"}
> ```
> **🔄 2026-08-03T02:57Z 複核重測**（同指令、於 `AutoClaude/` 下執行，rc=**1**）：
> ```json
> {"status": "observing", "green_streak": 26, "window": 30, "total_records": 35,
>  "history_path": ".drift_log_history.jsonl",
>  "last_failure_reason": "drift_log_table_exists=False (alembic head 落後)"}
> ```
> 差異來源＝**2026-08-03 02:00 那輪 nightly**（`logs/nightly_2026-08-03_020001.log`）寫入第 35 筆（綠）⇒ streak 25 → **26**，**距門檻 30 尚差 4 筆**。
> ⚠️ `last_failure_reason` 仍顯示舊訊息屬**正常**：該欄描述的是**歷史上打斷 streak 的那一筆**（2026-06-02），不是現況；alembic head 現已在鏈頭（見 §8.3 D-2）。
>
> **判準比對（以複核重測值為準）**：`.drift_log_history.jsonl` **35 筆**（2026-05-21 ~ 2026-08-02；初次實跑時為 34 筆），
> **`severity_non_info_count` 全 35 筆皆為 0** — 真實漂移事件數確為零；
> **但** 2026-06-02 那筆 `drift_log_table_exists: false` / `passed: false`（採集失敗，非漂移事件），
> 依 `_compute_green_streak` 語意**打斷 streak**，其後只累積到 **26** 筆 → **26/30 未達標，不可打勾**。
>
> **✅ 2026-08-03 後續（D-2 已解）**：alembic head 落後這個根因**現已不存在** —— 唯讀實查 `alembic_version = 0018_version_kind_discriminator`＝`alembic/versions/` 鏈頭、`drift_log` 表已建（total=0 / non_info=0）。
> 治理層亦已修：`alembic upgrade head` 移出 G0 前置改列獨立 `P-0`。
> ⇒ **#3 不需任何人工介入，只要再累積 4 筆綠紀錄（最快 4 個採集日）即自然達標**；✅ **且已有偵測者會通知你它到了**（D-5 已於 R71 G-3 解除，nightly G0 四軌納入 drift）。詳見 §8.3 D-2 處置框。
>
> **⚠️ 這筆採集失敗正是 [R-SD09-A-5](../05_development/risk_log.md) 風險的實際發生**（alembic head 落後 → drift_log 表不存在），
> 而該風險的緩解措施 (d) 明載「待 **W0 G0 預檢**執行 `alembic upgrade head`」— W0 G0 又需 #3 達標 → **同型死鎖第二例**（見 §8.3）。
>
> **🔴 治理缺口（為何一個「看起來達標」的觀察期兩個月無人處理）— 2026-08-03 收尾複核：4 項中 3 項已修**：
> 1. ✅ **已修（R71 G-3）**。〔原述〕`tools/drift_log_ga_check.py` 自 2026-05 建立至今 **零 production caller**。
>    〔現況實查〕`run_local_nightly.ps1` 新增 **`Get-DriftGaPass`**，以 `--json` 呼叫該工具並做 rc↔status 一致性檢查（三態 `Ok/Pass/Error`）。**判準工具現在每晚都被呼叫。**
> 2. 🔴 **仍未修**。舊載體 `tools/g0_gate_check.ps1:41/63` 把該檢查標為 `#3 observability/drift`，但實際只查 `observability_ga_check`（可觀測性 GA 軌）— **標籤與內容不符**，#3 被 obs 軌頂替。
>    〔2026-08-03 實查確認仍為真〕該檔 L41 註解 `--- #3 observability/drift (need green_streak>=30) ---`、L63 `#3 obs/drift not ready`，其 VERDICT 只判 `$ac4_ready -and $obs_pass`，**不含 drift**。
>    ⚠️ 惟其**危害已大幅下降**：新載體（nightly）已獨立涵蓋 drift 軌，舊載體不再是唯一管道。**建議處置：標籤改為 `#3 observability GA（非 drift）`，或直接標記該檔為 superseded。**
> 3. ✅ **已修（R71 G-3）**。〔原述〕新載體 G0 判定為 **mutation / ac4 / obs_ga** 三軌，不含 drift。
>    〔現況實查〕已擴為 **四軌**：`$g0MutOk -and $g0Ac4Ok -and $g0ObsOk -and $g0DriftOk`；drift 未達標時會列入 `$g0Gaps` 並印出
>    `drift_log GA green_streak {n} < window {m}（採集失敗＝table_missing 也會打斷 streak，未必是真漂移事件）`。**#3 的達標與否現在有偵測者。**
> 4. ✅ **已修（R71 G-1 / G-3）**。〔原述〕進度行 `drift=34/30` 印原始列數（方向：看似達標）、`mutation=5/7 unique-sha` 比權威 `should_lock` 嚴（方向：看似未達標）——一行同時兩個方向失真。
>    〔現況實查〕`END observation progress:` 四軌分子**一律取權威判準值**：`drift={green_streak}/{window}`、`mutation={should_lock 布林判定}`（`tail unique-sha n/7` 降為併印進度、明文註記「那**不是**判準本身」）；
>    `records=` 保留為 jsonl 原始列數，**僅供 delta 取證、絕不當分子**。ac4 軌亦已標明 `rolling-window-days` 語意（R69 S-1b）。

> **採集環境變更（2026-05-19）**：GitHub Actions 額度受限 → 三觀察期改本地 `tools/run_local_nightly.ps1`（Windows Task Scheduler 每日 02:00 排程）；觀察期 #1 mutmut 透過 Docker `python:3.11-slim` 跑解 Windows 原生限制。觀察期 #2 原阻塞於 SD_07 PM #2 遺留缺口（seed_kb.py + 100 query fixture），**已透過 ADR-SD09-008 v0.4 tolerant 雙軌制（60ms tolerant 升級門檻 + strict/observation 觀察指標）於 2026-05-25 解除阻塞**，2026-05-26 起以新口徑累計；詳見 [SD09_W0_AC4_Implementation_TaskBreakdown.md](../05_development/SD09_W0_AC4_Implementation_TaskBreakdown.md) + R-SD09-CI-1。

> **觀察期未達標處理矩陣**（M2 修復）：
> - **達標**：W0 啟動條件對應 (1)/(2)/(3) 打勾，啟動日 ≥ 2026-06-18
> - **抖動**（單日異常但連續恢復）：延長觀察期至下次連續達標日，啟動日順延
> - **未達**（連續紅線告警）：對應議題群降級或延 SD_10；不阻塞其他議題群

### 8.2 啟動條件清單

```
[x] (1) 觀察期 #1 mutation TokenGuardPlugin ≥ 70% — ✅ **已達標 2026-07-22**（ADR-SD09-013 PM 拍板 (b)）
        E-1 tail 7 筆 kill_rate 全 ≥ 68% effective threshold（實測最小 0.7071；tail7 = 0.745/0.745/0.7517/0.7651/0.7625/0.7174/0.7071）
        E-2 should_lock() = (True, 0.7071428571428572) + .mutation_baseline.toml token_guard = 0.7071
            取證：logs/nightly_2026-07-22_183551.log:261 `::notice::token_guard baseline locked at 70.71%`
                  logs/nightly_2026-08-01_101807.log:375（同）；baseline commit 3c612ad
        ⚠️ unique source_sha256 ≥ 7 **已移為 W1 出場驗收 X-1/X-2**（現值 5 unique + 2 筆 legacy）— 這是放寬，非修 bug，見 ADR-SD09-013 §6
[  ] (2) 觀察期 #2 AC4 14 天 nightly 全綠 ⏳ **未達標**（2026-08-03T02:57Z 實測 observation_days=8/14、ready_for_labeled_pr=false、reasons=["觀察期未滿（8/14 天）"]）
        → **W1 啟動的唯一「無爭議」剩餘阻塞項**；判準之日曆連續問題由 ADR-SD09-012 處理 — **PM 已拍板 2026-08-03**，🔴 判準 code 待實作（ADR §7.1 L-1~L-7）
        🔴 **拍板後訂正（2026-08-03 Architect 實測）**：該方案另有第二處放寬＝**證據新鮮度**（移除 `filter_recent` 即移除 `evaluate()` 唯一時鐘，採集停擺會永久假綠）。
           **方向不變，但落地必須連 L-7 獨立 staleness 判準一起做**；只做 L-1 不做 L-7 = 淨拆一道防線
[  ] (3) 觀察期 #3 drift_log 30 天零事件 ⏳ **未達標但已無阻礙**（2026-08-03T02:57Z 實測 green_streak=**26** < window=30；total_records=**35**；
        last_failure_reason="drift_log_table_exists=False (alembic head 落後)"，2026-06-02 採集失敗打斷 streak）→ **尚差 4 筆**
        註：severity_non_info_count 全 35 筆皆 0 — 真實漂移事件數為零，破 streak 者為採集失敗而非漂移
        ✅ **根因已消除（§8.3 D-2）**：唯讀實查 alembic_version=0018_version_kind_discriminator＝鏈頭、drift_log 表已建；
           `alembic upgrade head` 已移出 G0 前置改列獨立 P-0。**不需人工介入，最快 4 個採集日自然達標。**
           ⚠️ `last_failure_reason` 仍印舊訊息屬正常（描述的是歷史那一筆，非現況）；✅ **已有載體會通知達標**（D-5 已修，R71 G-3 接入 nightly 四軌）
        ⚠️ **判準衝突未決（不自行折衷，提請 PM）**：依本 §8.2 字面，(3) 是 W0/W1 啟動條件之一 → **未達標即阻塞 W1**；
           ✅ **nightly 活載體現已把 drift 納入 G0 判定**（四軌 = mutation / ac4 / obs_ga / **drift**，R71 G-3；原三軌不含 drift 的敘述已過期），
           **即活載體現在的立場是「#3 算 W1 入場條件」**；但 ADR-SD09-001 §2 / R-SD09-A-4 把 #3 定位為 **W5 db_only 切換雙條件**。
           ⇒ **衝突並未消失，只是換了形狀**：原本是「載體不判 vs 文件說要判」，現在是「載體判了 vs ADR-001 說那是 W5 條件」。**仍需 PM 裁定歸屬。**
           「#3 究竟是 W1 入場條件還是純 W5 條件」需 PM 裁定——此問題與 ADR-SD09-013 剛處理的 #1 屬**同一類**（閘門擺錯位置）
        判準複核全文與治理缺口見 §8.1 下方 🔴 註記
[x] (4) Tech Lead 提交 SD_09 W0 task breakdown（A + C + E + F 三方研究 + G 三方研究）✅ 2026-05-20
[x] (5) 本文件 §6 PM 拍板 8 項全數填入並形式核准 → v1.0 ✅ 2026-05-20
[x] (6) 本文件 §7 三方研究意見摘要（§7.1~§7.4）填入並四方審查 APPROVED ✅ 2026-05-20（13 bullet）
[x] (7) ADR-SD09-001~006 草案落地（PM 形式核准）✅ 2026-05-20
[x] (8) git tag sd_08_w6_g6_pass 已建立（W6 末快照）✅ 2026-05-18
[x] (9) gate_audit.md §1-septies 骨架建立（SD09-G0~G6 簽核紀錄空表）✅ 2026-05-20
[x] (10) risk_log.md §15 骨架建立（R-SD09-* 風險登記）✅ 2026-05-20
```

> **預估啟動日**：**2026-06-18 或之後**（最晚觀察期結束日 2026-06-17 + ≥ 1 工作日提前期）；最遲 **2026-06-26**（PM 拍板 #6 (b) 保守緩衝）。
> **🔴 逾期實況（2026-08-03）**：最遲啟動日 **2026-06-26 已逾期 38 天**，且**無任何機制偵測此 deadline 被跨過**（deadline 為死信，見 §8.3 D-4）。
> **絕對禁止**：在啟動條件未齊備前推進 PG db_only 切換（ADR-SD08-005 §2.2 雙條件未達禁切換 + ADR-SD09-001 §2 同步）。

### 8.2.1 剩餘阻塞項總結（2026-08-03 實測；每個數字皆本輪真跑）

| 條件 | 權威判準工具 | 實測 | 阻塞 W1？ | 處置 |
|---|---|---|---|---|
| #1 mutation | `mutation_baseline_lock.should_lock()` | `(True, 0.7071…)`；baseline `0.7071` 鎖定於 2026-07-22 | ❌ 不阻塞 | ✅ ADR-SD09-013 已結（PM 拍板 (b)） |
| #2 AC4 | `ac4_progress_check.py --json` | `observation_days=8/14`、`ready_for_labeled_pr=false`（2026-08-03 複核） | ✅ **阻塞** | ADR-SD09-012 **PM 已拍板 2026-08-03**；🔴 **判準 code 待實作**（ADR §7.1 落地清單 L-1~**L-7**）。<br>🔴 **拍板後訂正**：Architect 實測證偽「反作弊零改動」——移除 `filter_recent` 會連帶拆掉 `evaluate()` 唯一的時鐘，採集停擺時將**永久假綠**（一年前舊資料實測回 `ready=True`）。方向不變，但**落地必須加做 L-7 獨立 staleness 判準** |
| #3 drift_log | `drift_log_ga_check.py --json`（**須於 `AutoClaude/` 下執行**，預設 history 為相對路徑） | `green_streak=26 < window=30`（rc=1，2026-08-03 複核）→ **尚差 4 筆** | ⚠️ **爭議中** — §8.2 字面說阻塞、**nightly 活載體現已納入 G0 判定**、ADR-SD09-001 定位為 W5 條件 | **待 PM 裁定歸屬**；✅ **根因已解（D-2）**：alembic 已在鏈頭，不需人工介入、最快 4 個採集日達標；✅ **活載體已補（D-5，R71 G-3）** |
| — | ✅ **已修（R71 G-3）**〔原：活載體缺口〕`drift_log_ga_check.py` 零 production caller | 現況實查：`run_local_nightly.ps1` 的 `Get-DriftGaPass` 以 `--json` 呼叫它並做 rc↔status 一致性檢查 | — | ✅ **已接入 nightly 收尾 G0 四軌判定** |
| — | ✅ **已修（R71 G-1/G-3）**〔原：活載體失真〕nightly 進度行 `drift=34/30`、`mutation=5/7` | 現況實查：`drift={green_streak}/{window}`、`mutation=should_lock 權威判定`；原始列數改以 `records=` 併印且**絕不當分子** | — | ✅ **四軌分子一律取權威判準值** |

**結論**：**W1 啟動的無爭議剩餘阻塞項＝觀察期 #2（AC4 8/14）一項**。判準已由 **PM 於 2026-08-03 拍板**改為 gap-tolerant green_streak（ADR-SD09-012），
🔴 **但判準 code 尚未落地** —— 在落地之前，AC4 仍以舊判準卡在 8/14，**W1 實際上仍未解鎖**。落地清單見 [ADR-SD09-012 §7.1](ADR/ADR-SD09-012-ac4-observation-decouple-calendar.md)（**L-1~L-7**，其中 **L-7 為 L-1 的必要配套**）。

> 🔴 **落地前必讀**：ADR-SD09-012 拍板後經 Architect 實測，發現該方案**另有第二處放寬＝證據新鮮度（liveness）**，
> 且**與安全有關**——`filter_recent` 是 `evaluate()` 唯一參照「現在」的項，移出閘門後達標退化為純檔案內容函式，
> 採集器無聲死掉時 `green_streak` 會永久凍結、`ready` 永久為 `True`（實測：一年前資料回 `ready=True`）。
> **PM 是在不完整的揭露上拍板的。方向（gap-tolerant）仍然有效，但落地 DoD 已加掛 L-7 為必要條件。**

#3 是否同為 W1 入場阻塞項尚有判準衝突，需 PM 一併裁定；無論裁定結果為何：
- #3 目前**確實未達標（26/30，尚差 4 筆）**，且它作為 **W5 雙條件**的角色不受任何裁定影響；
- 但 **#3 已不再需要任何人工動作** —— 死鎖 D-2 已解、alembic 已在鏈頭，只需等 4 個採集日（§8.3 D-2 處置框）。

### 8.3 同型死鎖盤點（2026-08-03 全文掃描 §4 / §6 / §8）

> **形態定義**：「條件 C 的滿足，取決於某活動 A；而 A 又要等 C 通過才會發生。」
> ADR-SD09-013 處理的 #1 是第一例。全文掃描結果如下——**這種形態不只一處**。

| # | 死鎖 | 循環 | 嚴格程度 | 狀態 |
|---|------|------|---------|------|
| **D-1** | 觀察期 #1 unique sha | W1 啟動 ← #1 達標 ← unique sha ≥ 7 ← 改 token_guard 源碼 ← 「唯有 W1 active」（ADR-SD09-009 §11.6） | **文件層為硬循環；現實層為軟循環**（源碼在 W1 外仍會演進，但約每 14 天才 1 個 sha） | ✅ **已解** — ADR-SD09-013（PM 拍板 (b) 2026-08-03） |
| **D-2** | 觀察期 #3 ← alembic head（**R-SD09-A-5**） | #3 達標 ← drift_log 表存在 ← `alembic upgrade head` ← 該緩解措施 (d) 明載「待 **W0 G0 預檢**執行」 ← W0 G0 需 #3 達標 | **硬循環**，且**已實際發生**：2026-06-02 那筆 `drift_log_table_exists=false` 打斷 streak，是 #3 未達標的**唯一原因** | ✅ **已解 2026-08-03**（見下方 D-2 處置框）|
| **D-3** | 觀察期 #2 AC4 滾動窗口（同族，非嚴格循環） | #2 達標 ← 14 個**日曆天連續**無缺口 ← nightly 每天不漏跑 ← schtasks 不受睡眠／補跑跨日／`MultipleInstances=IgnoreNew` 影響（三者皆不在 SD_09 控制範圍） | **非循環，但同族「永遠到不了」**：任一漏跑即整段重算 | 🟡 **判準已由 PM 拍板改為 gap-tolerant（2026-08-03，ADR-SD09-012）**；🔴 **code 尚未落地**，落地後方解。<br>🔴 **注意藥方本身的副作用**：gap-tolerant 拿掉的不只是「相鄰」，還連帶拿掉 `evaluate()` 唯一的時鐘 ⇒ 會從「永遠到不了」翻轉成「**永遠假裝到了**」（D-6 同族反向）。**必須配 ADR-SD09-012 §7.1 L-7 staleness 判準**|
| **D-4** | 啟動 deadline 自身無載體（同族「條件沒有偵測者」） | §6 PM #6(b)「最遲 2026-06-26」 ← 需有人／有機制在該日檢查 ← **無任何載體負責**（原 `AutoClaude_SD09_G0_GateCheck` 為一次性 TimeTrigger，2026-06-29 跑一次後 `NextRunTime` 永久空白） | 已逾期 **38 天**無人察覺 | 🟡 **規格已交付、待實作**（見下方 D-4 規格框）。實作歸屬＝`run_local_nightly.ps1`（gate-align 那一路），**本輪刻意不動該檔以免衝突** |
| **D-5** | #3 權威判準工具無呼叫者（同族「判準沒有載體」） | #3 打勾 ← 有人跑 `drift_log_ga_check.py` ← **零 production caller**；新舊兩個活載體都不查它（舊載體 `g0_gate_check.ps1:41/63` 標籤寫 `#3 obs/drift` 但實際查 obs GA；新載體 nightly G0 三軌 = mutation/ac4/obs_ga） | 兩個月無人打勾／無人發現未達標 | ✅ **已解（R71 G-3，2026-08-03 複核實查）** — nightly 新增 `Get-DriftGaPass` 呼叫該工具，G0 判定由三軌擴為**四軌**（`$g0MutOk -and $g0Ac4Ok -and $g0ObsOk -and $g0DriftOk`），進度行分子改印權威 `green_streak/window`。<br>🟡 **殘留**：舊載體 `g0_gate_check.ps1:41/63` 的標籤錯置仍在（見 §8.1 治理缺口第 2 點），但已非唯一管道，危害降級 |

#### ✅ D-2 處置紀錄（2026-08-03 落實）

**治理修法**：`alembic upgrade head` **自「W0 G0 預檢」移出，改列為獨立前置動作 `P-0`**（[SD09_Execution_Guide.md §0.1-P0](../05_development/SD09_Execution_Guide.md)）。

**判別準則（可複用於其他誤掛的前置項）**：
> **「該動作若提前做，會不會讓 G0 的判定失真？」** —— 否 ⇒ 它就**不該掛在 G0 底下**。
> `alembic upgrade head` 只是把 schema 補到與 `alembic/versions/` 一致，**不改任何應用程式碼、不影響任何觀察期的量測語意**，
> 提前做只會讓 #3 的採集**恢復正常**。把它掛在 G0 下純屬**順手歸類**，卻製造了硬循環。

**事實層複核（唯讀，未執行任何 upgrade）— 2026-08-03T02:57Z**：

| 查核項 | 指令 | 結果 |
|---|---|---|
| DB 目前版本 | `docker exec autoclaude_pg psql -U autoclaude -d autoclaude -tAc "SELECT version_num FROM alembic_version;"` | **`0018_version_kind_discriminator`** |
| `alembic/versions/` 鏈頭 | 解析 18 支 migration 的 `revision`／`down_revision` | **`0018_version_kind_discriminator`**（`0015` 為 merge revision，合併 `0003`+`0014`；其後 `0016→0017→0018` 單線） |
| drift_log 表 | `SELECT to_regclass('public.drift_log');` | **`drift_log`（存在）** |
| drift_log 內容 | `SELECT count(*) , count(*) FILTER (WHERE severity <> 'info') FROM drift_log;` | **total=0 / non_info=0** |

⇒ **「alembic head 落後」這件事現在已不存在。** DB 版本 = 鏈頭，`drift_log` 表已建。

**因此 #3 的結論**：
- 不需要任何人工介入、不需要跑 `alembic upgrade head`（對本機為 **no-op**）；
- `green_streak=26/30`（2026-08-03T02:57Z 實測，rc=1）⇒ **只要再累積 4 筆綠紀錄即自然達標**；
- 每 UTC 日上限 1 筆（M-05）⇒ **最快 4 個採集日**。
- ✅ 且這 4 筆**現在有偵測者了**——D-5 已於 R71 G-3 解除（nightly 收尾 `Get-DriftGaPass` → G0 四軌）。**D-2 與 D-5 皆已解。**

> **仍需使用者執行的指令：無。**
> 若在**全新環境／fresh clone** 上重建（P-0 對該環境非 no-op），才需要：
> ```powershell
> docker compose -f AutoClaude/docker-compose.ci.yml up -d
> $env:AUTOCLAUDE_DB_DSN = "postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude"
> $env:AUTOCLAUDE_ALLOW_INSECURE_DB = "1"
> cd AutoClaude ; alembic upgrade head
> alembic current   # 應印 0018_version_kind_discriminator
> ```

#### 🔴 D-4 規格（deadline 逾期偵測）— **交 gate-align 那一路實作，本輪不動 `run_local_nightly.ps1`**

**問題**：2026-06-26 的啟動 deadline 逾期 **38 天**完全無人察覺。原偵測者是一次性排程任務 `AutoClaude_SD09_G0_GateCheck`（TimeTrigger 2026-06-29 觸發一次後 `NextRunTime` 永久空白），該任務本輪已移除。

**設計原則**：deadline 是**日期條件**，不是量測條件 —— 它不需要新採集、不需要新工具，**只需要一個每晚都會跑的東西去看一眼時鐘**。nightly 收尾的 G0 判定（R71 後為**四軌**：mutation / ac4 / obs_ga / drift）已經是這個活載體，**掛上去即可，不要另造載具**（另造 = 又一個沒人看的載具，重演 D-4 本身）。

| 項目 | 規格 |
|---|---|
| **落點** | `tools/run_local_nightly.ps1`，緊接既有 `[G0-READY]` / `[G0-NOT-READY]` 判定之後（同一區塊，共用已算好的三軌結果） |
| **常數** | `$SD09_G0_DEADLINE = [datetime]'2026-06-26'`（單一來源，對齊 §6 PM #6(b)） |
| **判定** | `$overdueDays = ([datetime]::Now.Date - $SD09_G0_DEADLINE).Days` |
| **輸出（未逾期）** | 不印，或印 INFO `[G0-DEADLINE] 距最遲啟動日 N 天` |
| **輸出（已逾期且 G0 未 READY）** | **`W()` WARN**：`[G0-OVERDUE] SD_09 W0 G0 最遲啟動日 2026-06-26 已逾期 {N} 天，且三軌尚未全綠 — 需 PM 裁示：延期／降級／改判準（gaps: …）` |
| **輸出（已逾期但 G0 已 READY）** | **`W()` WARN**：`[G0-OVERDUE-READY] 已逾期 {N} 天但三軌全綠 — 應立即執行 G0 動作清單並更新 deadline` |
| **rc 影響** | 🔴 **不進 `finalFailures`、不影響 exit code**。理由同既有 G0 判定註解：deadline 逾期是**人工決策訊號**，不是 nightly 健康度；污染 rc 會讓每晚都紅，違反紀律 #1 |
| **WARN 而非 INFO 的理由** | 與 G0-NOT-READY 相反：`NOT-READY` 是**預期中的穩定狀態**（會持續數週，每晚 WARN 會訓練人忽略 WARN），而**逾期是異常且會單調惡化**——它**應該**越來越刺眼。這是本規格與既有 G0 行文刻意分歧之處，**實作者請勿「順手對齊」成 INFO** |
| **測試鎖** | 於 `tests/tools/` 補 pure-function 版判定（例：`sd09_deadline_check.py` 或 ps1 helper 的 Python 對等）≥ 3 case：未逾期／逾期+未 READY／逾期+已 READY。**須做注入退化雙向驗證**（把 deadline 改到未來 → 必不觸發；改到過去 → 必觸發） |

⚠️ **併輪警告**：本規格與 [ADR-SD09-012 §7.1 L-6](ADR/ADR-SD09-012-ac4-observation-decouple-calendar.md)（AC4 判準落地要同步 `Get-Ac4Gate`）**都會動 `run_local_nightly.ps1`**。
該檔本輪實測正在被其他輪次編修（`mtime 2026-08-03 11:01:24`、行數 1,345 → 1,546）。
**兩者請由同一路人依序實作，切勿並行各改各的。** 實作前務必重新 grep 錨點，**不可沿用任何歷史行號**。

> **共通教訓**：D-1/D-2 是「閘門擺錯位置」，D-4/D-5 是「閘門沒有偵測者」。
> 兩者的症狀相同（條件永遠不會被滿足／永遠不會被發現滿足），但藥方不同：
> 前者要**移位**（入場 → 出場，或解除對後續活動的依賴），後者要**補活載體**（把判定接到每晚都會跑的東西上）。
> 開任何新的觀察期／啟動條件之前，應先問兩題：**(a) 這條件在未投入資源時物理上可能成立嗎？(b) 誰會去查它？**

---

## 9. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| **v0.1** | **2026-05-18** | SD_08 W6 G6 同步交付草案 — 7 議題群（A~G）+ 6 Wave 預估 + 4 ADR 預埋 + 5 風險預埋 + SD_08 移交 2 條風險 |
| **v0.2** | **2026-05-19** | **首輪四方審查修復**（Architect REJECTED / SA REJECTED / SD AwC / QA AwC，13 Critical + 22 Major + 15 Minor）— 新增 §6 PM 拍板表 8 項 + §7 三方研究意見摘要骨架（4 section）+ §8 三觀察期一覽表 + L6 處理 + SD_10 預告觸發來源；修正：滾動下沉「擴寫」非「下沉」誤稱 / ADR-SD09-005 canary 閾值 / R-SD09-A-3/A-4/B-2/F-2/G-1 新增 5 條風險 / mutation 排程拆分明訂 / 議題 F/G 「擇一不可組合」+ 延 SD_10 降級路徑 / 啟動日明訂 ≥ 2026-06-18 / 觀察期未達標處理矩陣 / 紅線編號 vs Rule 編號釐清（移至 Execution Guide）|
| **v0.3** | **2026-05-19** | **二輪四方審查修復**（Architect AwC / SA AwC / SD AwC / QA AwC，16 Critical + 25 Major + 21 Minor + 20 補強 = 62 主要項）— 詳見**附錄 A**修復對照表；核心修正：(SD-C1) drift_log SQL 欄位 `created_at`/`drift_count` 不存在 → 改 `detected_at`/`severity != 'info'` 對齊 alembic 0013 真實 schema；(QA-C1) fixture `fk_staging_1m.py` 不存在 → 改 `fk_staging_1m_wrapper.py` 包裝 `tools/sd06_w3_staging_dryrun.sh`；(SD-M3) 全文 `pytest.ini` → `pyproject.toml [tool.pytest.ini_options]`；(QA-C4) `§1.5 SD_07 ≥ 200 行` → `≥ 300 行` 統一；(QA-C5) G2 環境變數 `$PROCURE_OK`/`$KB_METRIC_PATH` → 文件查詢取代；(SD-C5) subprocess 注入點 3 處 → 9 處全列舉 + 集中式 helper；(Arch-C1/SD-C2) trace_context.py LOC tier 釐清 unclassified → 750；(Arch-C2) ADR-SD09-001 §2.5 物理回退範圍限制；(Arch-C3) ADR-SD09-002 TG fall-back 矩陣；(SA-C1/QA-M1) AC 累計動態 39/40/41；(SA-C2) AC11×3 五欄拆分；(SA-C3) sprint_history.md line 4 元數據漂移 T0-S1；(Arch-M3) Rule 8 取消 importlinter 改 contract test，紅線 ❌23 拆 ❌23-A/B；(Arch-M4) rollback SLA 拆 ≤3min+≤30min；(QA-M4) T0-O1 observability_ga_check.py；(QA-M7) G6 軟硬底線判定機制 |
| **v0.4** | **2026-05-19** | **zero-trust audit 修復**（fix agent 文件組執行 P0-D1~D5）— 5 項修復：(P0-D1) CLAUDE.md `[Architecture Snapshot]` 標題日期硬編碼 → 改動態語意（snapshot_sync.py 同步移除 `datetime.now()` 注入）+ `python tools/snapshot_sync.py --check` 確認不再 DRIFT；(P0-D2) sprint_history.md 4 處元數據漂移修正（line 4 / 16 滾動窗口 SD_06+SD_07 → SD_07+SD_08；line 362 SD_07 G6 末 2,012 → 2,094；line 368 SD_08 G5 未啟動 W6 → G6 通過 commit 22c03a7；line 390 W6 待啟動 → 已通過 2,094 passed）；(P0-D3) risk_log §15 新增 3 條風險（R-SD09-O-1 observability_ga_check.py 不存在 / R-SD09-A-5 alembic_version 落後 2 版 / R-SD09-CI-3 CI nightly 4 job continue-on-error 掩護 6+ 月）+ 重評 R-SD07-PM-#2 ✅→🟡 部分緩解（skip 硬編碼移交 SD_09 議題 C） + R-SD08-D-1 / R-SD08-PM-#3 從「觀察期 #1 監控中」→「監控管線未就緒（Docker 流程待穩定）」；(P0-D4) 補 4 個 stub — `tools/observability_ga_check.py` argparse skeleton + exit 1 防誤判 / `tools/seed_kb.py` argparse skeleton + exit 1 / `docs/06_quality/SD09_DBA_DryRun_Sign_W4.md` template / `docs/06_quality/SD09_PM_Release_Approval_W5.md` template；(P0-D5) §4 已知風險清單補引用 R-SD09-O-1 / A-5 / CI-3，§8.2 啟動條件 (1)(2)(3) 末尾加結構性阻塞警示 |
| **v0.5** | **2026-05-20** | **W0 G0 預檢 + 五方並行 zero-trust audit FULLY APPROVED-WITH-CONDITIONS**（PM / Architect / SA / SD / QA 五方獨立 audit；2108 passed / 0 failed / 122 skipped + equivalence 83/83 + contract 395 passed + importlinter 7 kept / 0 broken + snapshot_sync 無 DRIFT + LOC violations=0）— W0 G0 預檢四項全綠：(1) snapshot_sync --check OK；(2) check_loc_budget violations=0；(3) pytest plugins+ac4_progress_check 316 passed；(4) `.alembic_offline_head.txt=0014` marker 鎖定。**新增發現**：(N-07/Arch-SD) alembic multi-head `[0003_jsonb_gin_index, 0014_config_audit_log]` — 0003 為 SD_06 可選 JSONB GIN 分支（docstring 註明「目前非必要」），對 offline marker 不致命但 W2 PG `alembic upgrade head` 前須建立 merge revision（登 R-SD09-A-6）；(N-08/QA) `.mutation_history.jsonl` 不存在 — 觀察期 #1 起算點需 W0 啟動後重定錨。**補修 5 項**：(P0-SA-01) line 1/5/9 三處版本標示統一為 v0.5；(P0-SA-02) SD09_Execution_Guide.md 啟動日 06-25 → 06-26；(P0-SA-03) gate_audit / risk_log 啟動日窗口對齊「2026-06-18~22 提前 / 2026-06-26 deadline」；(P0-SA-04) SD09_W0_AC4_Implementation_TaskBreakdown.md 升 v0.2；(P0-PM-02) SD09_Pre_W0_Audit_Findings line 9 引用 v0.4 → v0.5；(P1-SD-02) Findings F-09 case 數 3 → 9（實 9 case 為正向超標）|
| **v1.0** | **2026-05-20** | **T0-1 升 v1.0 + W0 task list 22/22 CLOSED + 5 方終審 APPROVED** — T0-1 §7.1~§7.4 13 bullet 已填實（Arch 4 + SA 3 + SD 3 + QA 3）；T0-7 PM 形式核准 6 份 ADR（001~006，場景 A dev 自核）；T0-F4 trace_id 路徑 (b) W3C TraceContext finalized（git rm 路徑 (a)/(c) + ADR-SD09-004 升 v1.0 + Execution_Guide W3 對齊）；T0-10 `.env.example` 補 `PG_PRODUCTION_CUTOVER_GUARD=true` + `AUTOCLAUDE_TRACE_ID_SUBPROCESS_PROPAGATION=w3c_traceparent`；T0-C3 SD08_AC_Matrix.md AC4-1/AC4-2 升級實測門檻（recall@10 ≥ 0.95 + p95 < 50ms + cb_open=0 連續 14 天）；T0-E1 sprint_history §1.5 SD_07 W0~W6 骨架建立（W6 末擴寫至 ≥ 300 行）；五方專家 zero-trust audit（PM/Architect/SA/SD/QA）全 APPROVED 2026-05-20 |
| **v1.1** | **2026-05-24** | **W3 nightly system zero-trust audit FULLY APPROVED + F1/F2 修復** — 觸發：使用者要求徹底驗證 nightly 程式與執行結果正確性。**audit 範圍**：9 紀律 × 13 工具 + 9 測試鏡子 + run_local_nightly.ps1 447 行。**驗證結果**：紀律 #1-#9 全綠（bitmask 區分 / sqlite3 完整 counts / RunId log:L 引用 / 鏡子自驗 / 跨工具對齊 / 雙軌 env / cache fresh / .sh LF / SKIP 一致性）；2 條 P1 修復 — **(F1)** `tools/observability_snapshot.py` mock fallback 與真實 emit 1 次無法區分 → 改 `_emit_heartbeat_and_count()` 回 tuple `(count, emit_real)` + jsonl 寫 `observability_emit_real: bool` + `ga_check._is_green()` 拒絕 `emit_real=False`（舊紀錄缺欄寬鬆通過）；**(F2)** AC4 ready_for_labeled_pr 達標時 ps1 主動 WARN 提示 PM approval ceremony（autoclaude-pg-e2e-on-label.yml 雖 trigger active 但需文件記錄）。**新增測試鏡子**：`tests/tools/test_observability_ga_check.py`（14 case）+ `tests/tools/test_perf_regression_check.py`（18 case）+ observability_snapshot 補 2 case（emit_real 雙路徑）= **+34 case**。**CLAUDE.md 新增紀律 #10**「fallback 路徑與真實路徑必須 jsonl 可區分」。**全測 2,465 passed / 0 failed / 122 skipped**（W0 補測基線 2,413 +52）；importlinter 7 kept / 0 broken；LOC violations=0；CLAUDE.md 256 行 ≤ 400 |
| **v1.2** | **2026-05-24** | **W3 nightly system zero-trust audit Round 2 完成 + P0-2/P0-3/P0-5/P0-6 + P1-1/P1-2/P1-7/P1-8 修復** — 觸發：使用者重跑 nightly 觸發 Round 2 audit；Audit Agent 找出 28 項（P0=7 / P1=10 / P2=11），驗證後 P0-4/P0-7 由 clean run 推翻、P0-1 暫時 OK（latest pointer 後續硬化）。**真實修復**：(P0-2) Add-Content 改 `[System.IO.File]::Open` + `FileShare.ReadWrite` + retry 5 次 50/100/150/200/250ms 解 tail -F 衝突，所有 Log/Invoke-Native 改呼叫 `Add-LogLineSafe`；(P0-3) 新建 `tools/drift_log_ga_check.py`（166 LOC ≤ 200 data tier，仿 observability_ga_check 設計）+ drift_log_snapshot 同日去重邏輯改「優先保留 `drift_log_table_exists=True`」（避免 SKIP 覆寫真實）；(P0-5) `mutation_baseline_lock.py` 新增 `compute_source_sha256()` + `should_lock` 強制 tail 7 筆 `unique source_sha256 ≥ 7`（缺欄寬鬆相容）；(P0-6) `perf_regression_check.py` rc 三態 0/2/1（warn → rc=2 而非 rc=0）+ `Invoke-Stage` rc=2 標 WARN 不算 fail；(P1-1) `observability_ga_check._is_green()` 加 `strict_emit_real` 參數，最新 3 筆強制要求欄位存在 + 新建 `tools/_backfill_emit_real.py` 一次性 backfill 工具；(P1-2) `mutation_baseline_lock` 新增 `--require-log-mtime-within-seconds 3600`（ps1 stage 呼叫加此參數）；(P1-7) `test_check_block_at_min_samples_exact`（samples=20 boundary）+ `test_check_warn_alone_emits_rc_2`；(P1-8) `_emit_heartbeat_and_count()` 三段 emit 各自 try/except，count 累計 partial success，避免單一 emit_histogram 失敗整段 fallback。**新增測試鏡子**：drift_log_ga_check 14 case + drift_log_snapshot 補 2 case（prefers_table_exists / upgrade_skip_to_real）+ mutation_baseline_lock 補 7 case（source_sha256 4 + log mtime 2 + 1 邊界）+ perf_regression_check 補 2 case（min_samples_exact / warn_rc_2）+ observability_snapshot 補 2 case（partial_success / all_fail）+ observability_ga_check 補 2 case（strict_recent_3）= **+29 case**。**CLAUDE.md 新增紀律 #11 + #12**（latest log pointer 必須引用完整 run / mutation history 必須有 source_sha256 區分）。**Clean nightly run 取證**：`logs/nightly_2026-05-24_223310.log:L237` `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`（6 stages 全綠，elapsed 5min 46s）。預估全測 ≥ 2,494 passed（v1.1 基線 2,465 +29 新 case）；importlinter 7 kept / 0 broken；LOC violations=0；CLAUDE.md ≤ 400 行 |
| **v1.3** | **2026-08-03** | **觀察期 #1 入場死鎖解除（PM 拍板 (b)）+ #3 判準 zero-trust 複核（推翻先前「早已達標」口語判斷）+ 同型死鎖盤點** — (1) 新增 §6 拍板列 #9 + [ADR-SD09-013](ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md) ACCEPTED：unique `source_sha256` ≥ 7 由**入場條件移為 W1 出場驗收**（X-1/X-2，並新增「每 sha 需對應實質變更 commit」之取證要求）；**明列此為放寬（7→5）非修 bug**，風險承擔者 PM。(2) 起草期間 zero-trust 複核**訂正兩項拍板前提**：`should_lock()` 早已回 `True`、`.mutation_baseline.toml` `token_guard=0.7071` **已於 2026-07-22 鎖定**（`logs/nightly_2026-07-22_183551.log:261`），真正擋 W1 的是文件字面與 nightly counter，不是閘門邏輯；§11.6「idle 凍結」敘述已被事實推翻（W1 未啟動期間仍演進 4 個新 sha）。(3) **#3 複核結果為未達標**（`drift_log_ga_check.py` → `green_streak=25 < 30`，2026-06-02 採集失敗打斷 streak；`severity_non_info_count` 全 34 筆為 0），連帶揭露該工具**零 production caller**、新舊活載體皆不查 drift、nightly 進度行 `drift=34/30` 與 `mutation=5/7` 兩個方向的取證失真。(4) 新增 **§8.2.1 剩餘阻塞項總結** 與 **§8.3 同型死鎖盤點**（D-1 已解 / D-2 R-SD09-A-5 硬循環未解 / D-3 AC4 同族 / D-4 deadline 無偵測者 / D-5 判準無載體）|

| **v1.4** | **2026-08-03** | **#3 誤述訂正 + D-2 死鎖處置 + D-4 規格交付 + ADR-SD09-012 PM 拍板記錄** — (1) **訂正 ADR-SD09-012 §1.1 的 #3 誤述**：原寫「#3 早已達標」為錯（把「真實漂移事件為零」誤推為「判準已通過」）；權威工具當回合實跑 `green_streak=26 < window=30`（rc=1），連帶訂正 §2.1 把 drift 標為 `PASS 34/30` 的同型錯誤（34 是總筆數非 green_streak）。**§3.2 論證經重新檢驗後仍成立但已重寫依據**：達標實例只剩 obs 一軌（42/30, rc=0），drift 改列為「判準保有鑑別力」的正面證據（35 個缺口日照樣累積、卻被一筆真紅正確擋下）。(2) **D-2（R-SD09-A-5-LOOP）已解**：`alembic upgrade head` 自「W0 G0 預檢」移出，改列獨立前置動作 **P-0**（判別準則＝「提前做會不會讓 G0 判定失真？否 ⇒ 不該掛在 G0 底下」）；**事實層另已解除** —— 唯讀實查 `alembic_version=0018_version_kind_discriminator`＝`alembic/versions/` 鏈頭、`drift_log` 表已建（total=0/non_info=0）⇒ P-0 對本機為 no-op，**#3 不需任何人工介入，尚差 4 筆綠紀錄即自然達標**。(3) **D-4 規格交付**（deadline 逾期偵測掛進 nightly 收尾活載體、WARN 不進 rc、三 case 測試鎖），**實作歸屬 gate-align 那一路，本輪刻意不動 `run_local_nightly.ps1`**（實測該檔正被他輪編修：mtime 11:01:24、行數 1,345→1,546）。(4) **ADR-SD09-012 轉 ACCEPTED**（PM 拍板 2026-08-03，採 gap-tolerant green_streak、門檻仍 14、反作弊零改動），🔴 **判準 code 一行未改（NOT LANDED）**，§7.1 交付精確落地清單 L-1~L-6（含最大地雷：`observation_days` 語意若隨全史改變，會讓 nightly 進度行復刻 §2.8 假達標）。(5) 三軌數字全面重測對齊 02:00 nightly 後之值（#2 7→8、#3 25→26、obs 41→42）。**發現但未修（射程外）**：`.alembic_offline_head.txt` 內容 `0015` 已落後真實鏈頭 3 版（無程式消費者，不阻塞） |

| **v1.5** | **2026-08-03** | **R71 收尾訂正 — 「已修好的事，文件仍寫未修」全面清理 + ADR-SD09-012 反作弊揭露補完** — (1) 🔴 **ADR-SD09-012「反作弊零改動」經 Architect 實測證偽**：`filter_recent` 是 `evaluate()` **唯一參照「現在」的項**（`ac4_progress_check.py:141`，全檔唯一 `datetime.now()`），移出閘門後達標退化為**純檔案內容函式** ⇒ 採集器無聲死掉時 `green_streak` 永久凍結、`ready` 永久 `True`。**本輪獨立複跑證實：14 筆全綠但 timestamp 距今 354 天的資料，在提案判準下回 `ready=True`（現行判準回 `False`）。** 處置＝**不推翻拍板方向**（gap-tolerant 仍對），但 ADR §4.3 補列**第二處放寬（證據新鮮度，與安全有關）**、§1.4 日曆窗代理事項由 2 項改 3 項、§7.1 新增 **L-7 獨立 staleness 判準**（`STALENESS_MAX_DAYS` 建議 30，＝window 2 倍；取 14 會重蹈日曆綁定，因本機 8 月只活 2 天）並列入 DoD 必要條件。**PM 是在不完整揭露上拍板的，此點必須訂正。** (2) **五份文件 17+ 處「未修／射程外／待主控協調／⛔」逐處開檔核對後改寫**：✅ ADR-SD09-013 L-3 **已落地**（R71 G-1：`$G0_MUTATION_UNIQUE_SHA_TARGET` 已自 `run_local_nightly.ps1` 刪除，改由 `Get-MutationLockGate` 向 `should_lock` 現場提問）——連帶**刪除已成假且會誤導 PM 的「在 L-3 落地前，G0 放行是人工決策，不是機器判定」**；✅ §8.1 治理缺口 1/3/4 與 §8.2.1 後兩列、§8.3 **D-5 已解**（R71 G-3：`Get-DriftGaPass` 接入、G0 三軌擴為**四軌**、進度行四軌分子一律取權威判準值）；🟡 `R-SD09-GATE-NOCARRIER` 由 🔴 OPEN 降為 **🟡 部分緩解**（殘留＝D-4 deadline 無偵測者 + 舊載體 `g0_gate_check.ps1` 標籤錯置）。**刻意不改**：治理缺口第 2 點（`g0_gate_check.ps1:41/63` 標籤寫 drift 實查 obs）**實查確認仍為真**，維持 🔴。 (3) **數字全面訂正**：drift `green_streak` 25→**26**、`total_records` 34→**35**；AC4 `observation_days` 7→**8**；`.ac4_history.jsonl` 41→**42** 筆（42 個相異 UTC 日期、跨度 74 天、`circuit_breaker_open_count` 全 0——順帶訂正 ADR-012 誤用的欄名 `cb_open`，該 key 在 jsonl 內不存在） |

---

**對應參考文件**（**SA-M6 修復**：補 ADR-SD09-001~005 個別 5 條 link）：
- [SD_Improving_08.md](SD_Improving_08.md) v1.0 — 前置 Sprint 主規劃
- [SD08_Migration_Guide.md](../08_deployment/SD08_Migration_Guide.md) v1.0 §5 SD_09 延期清單 + §7 L1~L6
- [ADR-SD08-005-pg-production-dual-track.md](ADR/ADR-SD08-005-pg-production-dual-track.md) — PG 雙軌制 SD_09 啟用條件
- [ADR-SD09-001-pg-db-only-cutover.md](ADR/ADR-SD09-001-pg-db-only-cutover.md) — PG db_only 切換不可逆轉折點
- [ADR-SD09-002-mutation-full-module-expansion.md](ADR/ADR-SD09-002-mutation-full-module-expansion.md) — mutation 全模組擴展策略
- [ADR-SD09-003-perf-three-track.md](ADR/ADR-SD09-003-perf-three-track.md) — perf 雙軌轉三軌
- [ADR-SD09-004-trace-id-multi-process.md](ADR/ADR-SD09-004-trace-id-multi-process.md) — trace_id multi-process 邊界傳播
- [ADR-SD09-005-pg-canary-stage-thresholds.md](ADR/ADR-SD09-005-pg-canary-stage-thresholds.md) — PG canary 三階梯閾值
- [Production_Migration_SOP.md](../08_deployment/Production_Migration_SOP.md) v0.1 — §1-§3 草案（SD_09 W3-W4 補完 §4-§8）
- [SD08_Mutation_Baseline_Report.md](../06_quality/SD08_Mutation_Baseline_Report.md) v0.1 — pilot observing
- [SD09_Execution_Guide.md](../05_development/SD09_Execution_Guide.md) v1.0 — 對應執行計畫（同步升 v1.0）
- [risk_log.md §14](../05_development/risk_log.md) — SD_08 風險收尾移交來源（§15 W0 同步建立）
- [gate_audit.md §1-sexies SD08-G6](../05_development/gate_audit.md) — SD_08 收尾簽核（§1-septies W0 同步建立）
- [sprint_history.md](../05_development/sprint_history.md) v1.1 — SD_03~SD_06 完整紀錄（v1.2 W6 末擴寫 §1.5 SD_07）

---

## 附錄 A：v0.2 → v0.3 二輪四方審查修復對照表

> 詳細逐條修復位置。簡化版（檔案路徑 + section）。

| 審查方-編號 | 嚴重度 | 問題簡述 | 修復位置 |
|----|----|----|----|
| Arch-C1 | 🔴 | trace_context.py LOC tier 釐清 | trace_context.py L3 docstring + ADR-SD09-004 §3 |
| Arch-C2 | 🔴 | 物理回退範圍限制 | ADR-SD09-001 §2.5（新增）|
| Arch-C3 | 🔴 | TG fall-back vs W1 排程衝突 | ADR-SD09-002 §2.1.1（新增）+ SD_09.md §1.2 |
| Arch-M1 | 🟠 | canary 三觸發 race condition | ADR-SD09-005 §2.2 + Execution Guide T3-A2 |
| Arch-M2 | 🟠 | GHA cron UTC 時區 + Coord 04:00 | ADR-SD09-002 §2.3 |
| Arch-M3 | 🟠 | Rule 8 冗餘改 contract test | ADR-SD09-004 §3.1 + 紅線 ❌23-A/B 拆分 + G3/G6 7 kept 統一 |
| Arch-M4 | 🟠 | rollback SLA 拆 ≤3min+≤30min | ADR-SD09-005 §2.3 |
| Arch-M5 | 🟠 | Snapshot SSOT 條件式更新 | Execution Guide T6-4(d) |
| Arch-M6 | 🟠 | 觀察期 #3 起算日 +1 修正 | SD_09.md §8.1 + ADR-SD09-001 §2.2 |
| SA-C1 | 🔴 | AC 累計 41 條動態 39/40/41 | Execution Guide T6-3 + SD_09.md §2 footer + T0-AC |
| SA-C2 | 🔴 | AC11×3 五欄拆分 | Execution Guide T0-AC + T6-3 |
| SA-C3 | 🔴 | sprint_history line 4 元數據漂移 | Execution Guide T0-S1（新增）+ T6-4/T6-7 |
| SA-M1 | 🟠 | §6 #4/#5 標「擇一」 | SD_09.md §6 表 |
| SA-M2 | 🟠 | §6 #8 DBA 親演 vs ❌21 | SD_09.md §6 表 |
| SA-M3 | 🟠 | 修復對照表附錄 | 本附錄 A |
| SA-M4 | 🟠 | §8.2 三狀態欄 | SD_09.md §8.2 |
| SA-M5 | 🟠 | §2 footer 路徑敏感性 | SD_09.md §2 footer |
| SA-M6 | 🟠 | 參考清單補 ADR link | SD_09.md §9 末（本檔已修）|
| SD-C1 | 🔴 | drift_log SQL 欄位錯（created_at/drift_count → detected_at/severity） | ADR-SD09-001 §3 + ADR-SD09-005 §2.2 + Execution Guide §0.3/T0-6/T3-A2/T5-A2/T5-A6 |
| SD-C2 | 🔴 | trace_context.py 位於 utils/ unclassified → 750 | trace_context.py L3 docstring + ADR-SD09-004 §3 |
| SD-C3 | 🔴 | 雙條件 (1a)/(1b) 拆分 | ADR-SD09-001 §2.2 + Execution Guide T5-A2 |
| SD-C4 | 🔴 | IKbMetricStore port spec 草案 | SD_09.md §1.7 + Execution Guide T2-G1 |
| SD-C5 | 🔴 | subprocess 注入點 9 處全列舉 + 集中式 helper | ADR-SD09-004 §2.3 + §2.5 |
| SD-M1 | 🟠 | mutation 單檔精準 vs 子模組 | ADR-SD09-002 §2.4 |
| SD-M2 | 🟠 | （同 Arch-M3）Rule 8 冗餘 | 同 Arch-M3 |
| SD-M3 | 🟠 | pytest.ini → pyproject.toml + marker 註冊 | 全文 replace + ADR-SD09-003 §2.2 |
| SD-M4 | 🟠 | rollback SQL 工具 T3-A3 拆細 | Execution Guide W3 T3-A3-1/A3-2 |
| SD-M5 | 🟠 | Wave 預估 vs contract test 對齊 | Execution Guide §3 各 G |
| SD-M6 | 🟠 | pg_health.py get_active_connections 驗證 | W0 T0-6 預檢 |
| QA-C1 | 🔴 | fixture `fk_staging_1m.py` 不存在 | Execution Guide T3-A4/T0-A0 + ADR-SD09-001 §2.3 |
| QA-C2 | 🔴 | §0.3 命令健壯性（grep / psql fail） | Execution Guide §0.3 |
| QA-C3 | 🔴 | 觀察期 #3 無 PG 環境 fall-back | ADR-SD09-001 §3 + Execution Guide §0.3 |
| QA-C4 | 🔴 | T6-11 ≥ 200 vs G6 ≥ 300 衝突 | Execution Guide T6-11 + G6 awk |
| QA-C5 | 🔴 | $PROCURE_OK/$KB_METRIC_PATH 未定義 | Execution Guide G2 改文件查詢 |
| QA-M1 | 🟠 | AC16 累計 41 誤導 | 同 SA-C1 |
| QA-M2 | 🟠 | T5-A6 case 4 fixture 規範 | Execution Guide T5-A6 |
| QA-M3 | 🟠 | 觀察期 #1 7 次連續取證 | Execution Guide §0.3 |
| QA-M4 | 🟠 | observability_ga_check.py 新工具 | Execution Guide T0-O1（新增） |
| QA-M5 | 🟠 | mutation nightly 超時護欄 | ADR-SD09-002 §2.6 |
| QA-M6 | 🟠 | R-SD09-A-3 fall-back hotfix 分支 | Execution Guide G3 fall-back |
| QA-M7 | 🟠 | G6 軟硬底線判定機制 | Execution Guide G6 + 條件判定表 |
| Minor + 補強 | 🟡💡 | 21 + 20 項（包含 SA-m1~m5 / SD-m1~m5 / QA-m1~m5 / Arch-m1~m6） | 散落各檔；本表簡化僅列 Critical+Major；Minor 詳見各 ADR/Execution Guide 行內標註 |

**修復統計**：62 項主要項目修復（16 Critical + 25 Major + 21 Minor）；20 項補強建議於 W0 三方研究階段同步處理（非阻塞 v1.0）。

---

## 附錄：觀察期執行記錄 2026-05-20 ~ 2026-05-21

| 項目 | 內容 |
|------|------|
| 採集主檔 | [`tools/run_local_nightly.ps1`](../../tools/run_local_nightly.ps1) — 本地 nightly（取代 GitHub Actions cron） |
| 採集起算 | 2026-05-20（W0 G0 通過後） |
| 最新 nightly | `logs/nightly_latest.log`（每次 run 後自動更新指向最新 RunId log） |
| 觀察期累積 | mutation 1/7（kill_rate=0%）；AC4 1/14（pass）；drift 0/30（待 alembic 補完） |

### W0 首輪修復（已 CLOSED — 2026-05-19/20 audit）

| 級別 | 項目 | 修復內容 |
|------|------|---------|
| P0-1 | mutation-test 完全無法實跑 | `tools/run_mutmut_in_docker.sh` 獨立 shell script（避免 PS here-string 截斷 `--paths-to-mutate`）+ `pyproject.toml` 新增 `[mutation]` extras 鎖 `mutmut==2.4.3` |
| P0-3 | log 編碼污染（UTF-16 LE 混雜） | ps1 全面改用 `Invoke-Native { ... } 2>&1 \| Out-String -Stream \| Add-Content -Encoding utf8` |
| P1-1 | log 檔名缺 RunId | log 改為 `logs/nightly_${Today}_${RunId}.log` + `nightly_latest.log` pointer |
| P1-2 | Stopwatch 精度與 ERROR log | `'hh\:mm\:ss\.fff'` 三位毫秒；stage rc!=0 主動 log `[ERROR]` |
| P1-3 | AC4 collector 偽陽性 pass | `_parse_junit_xml` 套門檻常數 + 空值 fail；新增 8 case |
| P1-4 | alembic 首次 traceback | DSN 預設改為 sync；asyncpg DSN 在 alembic 完成後 lazy swap |
| P2-2 | 文件未對齊 | CLAUDE.md / 本附錄補入 SD_09 段落 |

### W0 二次 zero-trust audit 補修（2026-05-21）

首輪修復只解決載具問題；二次 audit 發現腳本仍把 mutmut baseline crash 當成 pass、perf stage 因樣本不足持續抖動 fail、Python stdout 經 PS 流仍被轉成 cp950。以下為二次補修：

| 級別 | 缺陷 | 修復內容 |
|------|------|---------|
| P0-A | `run_mutmut_in_docker.sh` 用 `exit 0` 蓋過 `mutmut run exit=2`，stage 假 pass；mutmut results 從舊 `.mutmut-cache` 撈出 `Survived 🙁 (64)` 騙過 `validate_mutmut_log.py` | mutmut 之前先 `rm -rf /workspace/.mutmut-cache` 強制 fresh baseline；尾端改 `exit "${MUTMUT_RC}"` 真實 propagate |
| P0-B | `run_local_nightly.ps1:196-197` 以 log validity 蓋過 docker rc | 改為「dockerRc!=0 → 即標 stage fail（不走 baseline_lock / analysis）」 |
| P0-C | 中文亂碼（"比對結果" → "��ﵲ�G�G"） — Python sys.stdout 在 PS pipeline 下用 cp950 編碼 | ps1 開頭設 `[Console]::OutputEncoding=UTF8` + `$OutputEncoding=UTF8` + `$env:PYTHONIOENCODING='utf-8'` + `$env:PYTHONUTF8='1'` |
| P0-D | `mutation_analysis.py` survived=11 vs `mutation_baseline_lock.py` survived=64 數字不一致（dash range token 被 `isdigit()` 排除） | 新增 `_expand_id_tokens` helper 展開 dash range（`12-16` → `[12,13,14,15,16]`）；parsed vs summary 不一致時印 WARN 並以 summary 為單一真相 |
| P0-E | §451 表格自相矛盾（聲稱 perf exit=0、`p95=45.57ms` 但 latest log 為 `perf=1`、`p95=51.5ms`） | 本附錄全段重寫（即此版） |
| P1-F | `perf_regression_check.py` 對 samples=7 baseline 直接判 BLOCK（樣本噪音被誤判 regression） | 新增 `MIN_BASELINE_SAMPLES=20` 警示；baseline samples < 20 印 `::warning::` 但不阻塞 |
| P1-G | `AUTOCLAUDE_TEST_P95_THRESHOLD_MS=80` 同時放水採集與升級門檻 | 雙軌：採集仍 80ms；呼叫 `ac4_progress_check` 前覆寫為嚴格 50ms，call 後恢復 |
| P1-I | drift_log 表不存在 → 視為 0 events（觀察期 #3 假累積） | 先 `information_schema.tables` 驗證；表不存在 → 標 N/A 不計入觀察期 #3 天數 |

### W0 三次 zero-trust audit 補修（2026-05-21，PM 派工）

二次 audit P0-A/B 雖讓 stage 失敗真實暴露，但**過度嚴格**：把 mutmut 2.4.x `exit=2`（標準「有 survived」回報）當 crash → 觀察期 #1 永遠無法累積。實測 mutmut 跑完 149 個 mutation（killed 80~85、survived 64、suspicious 1~5），exit code 為 bitmask，過去判斷錯誤導致 kill_rate=0% 假象。本輪由 PM 派工四方專家修復：

| 級別 | 缺陷 | 修復內容 |
|------|------|---------|
| P0-F | mutmut exit=2 為 bitmask（bit0=exception, bit1=survived, bit2=timeout, bit3=suspicious），二次 audit 誤把 `rc!=0` 都當 crash | `run_mutmut_in_docker.sh` 改用 `(MUTMUT_RC & 1) == 0` 判定正常；`run_local_nightly.ps1` 同步改 `if (($dockerRc -band 1) -ne 0)` 才算真 fail，其他位元視為觀察期預期 |
| P0-G | `mutmut results` 預設只列 Survived 區段，缺 `Killed (N)` → `mutation_baseline_lock.py` 解析 counts.killed=0 → 算出 `kill_rate=0%`（**假象**）；真實是 53~57% | sh 改用 `sqlite3` 直接 query `/workspace/.mutmut-cache` 的 `Mutant` 表，產出完整 5 個 status counts（`Killed (N) / Survived (N) / Timeout (N) / Suspicious (N) / Skipped (N)`）寫在 log **末尾**（保留 raw `Survived 🙁` + dash range 於前段給 mutation_analysis 解析；末尾 5 行給 baseline_lock 解析） |

**P0-F/G 取證（歷史 audit 算式 — 以 .mutation_history.jsonl 為單一真相）**：三次 audit 修復當下手動跑 sh → `Killed (80) Survived (64) Timeout (0) Suspicious (5) Skipped (0) Total=149`；`mutation_baseline_lock.py` 計算 `kill_rate=0.5369=53.69%`（80/149 — 此為 W1 補測前 baseline）；`mutation_analysis.py` parsed survived=64（與 summary 一致）；mutmut 跑 ~4 分鐘屬正常（149 mutation × pytest token_guard <1s/test = 約 3~4 分鐘）。

> **W1+ 真實採集以 `.mutation_history.jsonl` 為單一真相**：本行為三次 audit 修復當下算式紀錄，後續觀察期 #1 達標判定以 jsonl 末筆為準（W1 後實測 74.50% / 71.14%，見下表）。

### PASS / FAIL 狀態（W1 落地後 — 以 `logs/nightly_latest.log` 為單一真相）

| 觀察期 | 真實狀態（2026-05-21 W2 nightly **run_id=172704** — 取證行號 SSOT） | 後續行動 |
|--------|------------------------|---------|
| #1 mutation | ✅ **runs=2/7（以 .mutation_history.jsonl 為單一真相）** — 最新 5/21 17:31 kill_rate=74.50%（`logs/nightly_2026-05-21_172704.log:L151` `::notice::token_guard observing — kill_rate=74.50% runs=2/7 (need 5 more)`）；W1 補前 baseline=53.69%（killed/total=80/149）。W1 補 token_guard 5 子模組共 97 個 mutation-killer test 殺 26 個 survived（64→38）。**P1-2 UTC date 去重補註**：第一筆 `2026-05-20T20:59:23Z` UTC=2026-05-20、第二筆 `2026-05-21T09:14Z` UTC=2026-05-21 → runs=2/7 對應 2 個獨立 UTC date。距離鎖定 baseline 仍需累計 ≥ 7 次達標。 | 觀察期繼續累積至 2026-06-01；殘留 38 survived（policy.py=16 / compactor.py=13 / git_verifier.py=5 / thresholds.py=3 / watcher.py=1）可選擇性續補 |
| #2 AC4 | 🟢 **嚴格門檻已通過一日**（採集中） — 最新 5/21 09:31:58Z `p95_ms=49.14` ✅ **已過嚴格 50ms 門檻一日**（`logs/nightly_2026-05-21_172704.log:L176` `"p95_ms": 49.14, "circuit_breaker_open_count": 0, "status": "pass"`）；累計 2/14 觀察天；歷史 first 5/20 p95=52.49ms 嚴格未過（差 2.49ms） | 雙軌已啟用；繼續累積至 2026-06-02 達標 14 天 |
| #3 drift | ✅ **0 events** — `logs/nightly_2026-05-21_172704.log:L218` `drift_log severity!='info' rows = 0`；累計 2/30 觀察日（**P1-5 修復後 .drift_log_history.jsonl 持久化累計可審計**） | 繼續累積至 2026-06-17 |
| perf | 🟢 **PASS（單次 nightly run rc=0）** — `logs/nightly_2026-05-21_172704.log:L215` `[perf] regression_check_rc=0, baseline_lock_rc=0`；BLOCK→WARN 退化已啟用（samples=7<20 統計噪音）；待 W2 重新採集 samples ≥ 20 baseline | **ADR-SD08-003 v1.1（2026-05-21）已升 samples ≥ 20**；`autoclaude/utils/perf_baseline.py::MIN_RUNS=20`；`write_baseline()` 拒寫 < 20 |
| END summary | ✅ **全綠** — `logs/nightly_2026-05-21_172704.log:L226` `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`（6 stages elapsed 約 6 分鐘）| — |

**單一真相取證**：`logs/nightly_latest.log` 為 truth source；任何 PASS 聲稱必須引用具體 RunId log 行號，不再以歷史某一輪綠燈快照寫入本文件。

**W2 nightly zero-trust audit 修復清單（2026-05-21）**：P0-1 PS5.1 git rev-parse 空字串（改 `2>$null | Out-String | Trim`）/ P0-2 mutation_analysis 移入 docker（host 上 mutmut 不可用 → backlog 全 "other"）/ P0-3 PASS RunId 更新至 172704 / P0-4 RootCause Report 補註轉綠 / P1-1 trace_continuity 改實測（不再寫死 True）/ P1-2 mutation history UTC date 去重補註 / P1-4 AC4 p95=49.14ms 嚴格已過 / P1-5 新增 `tools/drift_log_snapshot.py` + `.drift_log_history.jsonl` 持久化累計（觀察期 #3 30 天可審計）/ P2-A mutmut 版本守門 / P2-B docker ps stderr 重導。

### 結構性問題（S 級 — W1 進度）

- **S-1 觀察期 #1 補測達標** ✅：W1 補 97 mutation-killer test（5 檔），實測 kill_rate 從 57% → **74.50%**（111/149），首次跨越 70% 容忍門檻；距 baseline lock 仍需累計 ≥ 7 次達標。
- **S-2 perf samples=7 統計必然抖動** ✅：ADR-SD08-003 v1.1（2026-05-21）已升 samples ≥ 20；`autoclaude/utils/perf_baseline.py::MIN_RUNS=20` + `write_baseline()` 拒寫 < 20。待 W2 重新採集。
- **S-3 文件與實測脫鉤的紀律失守**（已固化）：自此之後**所有 PASS/FAIL 聲稱必須引用具體 RunId log + 行號**。
- **S-4 採集寬鬆與升級嚴格未分軌** ✅：W0 P1-G 已落地（80ms 採集 + 50ms 升級）。
- **S-5（W1 新增） bitmask 判定 SSOT** ✅：W1 QA #4 將 mutmut exit code bitmask 抽至 `tools/mutmut_exit_code.py`（93 case 單元測試）；`run_local_nightly.ps1` + `run_mutmut_in_docker.sh` 改為呼叫 CLI 而非各自 inline bitmask；對齊紀律 #4「驗證鏡子自身要被驗證」。

### 既知殘留（接受、不於本 Sprint 修）

- (a) `pyproject.toml` perf samples 預設 — 待 W2 採集器同步調整為 `--benchmark-min-rounds=20`
- (b) 自訂 Docker image 預灌依賴（T-7）— 加速優化
- (c) `LASTEXITCODE` 多次 native command race（T-8）— 累計修補
- (d) policy.py 殘留 16 個 survived 集中於 delegation / `_evaluate_resources` 路徑 — 可選擇性續補（kill_rate 已達標）

### W2 zero-trust audit 修復（2026-05-21 — Architect/SA/SD/QA 全能專家三方）

對應 `logs/nightly_2026-05-21_093112.log`（mutation=0/pg-e2e=0/perf=1/drift=0）。Audit 找出 30 個問題（P0=10 / P1=12 / P2=8），全數 P0/P1/P2 範疇內項目已修復、QA 二次審議 APPROVED。

**P0 (Blocker) 全 10 項 CLOSED**：
- P0-AUDIT-01/02/03 — `run_mutmut_in_docker.sh` log append 模式（`tee -a` + `>> "${LOG_FILE}"`）+ 同步清 `.pytest_cache` + `.mutmut-cache`（紀律 #2 / #7）
- P0-AUDIT-04 — `mutation_baseline_lock.py` + `mutation_analysis.py` 同步 marker-based parse（`--- mutmut full counts (from cache;...) ---` 與 `(end)` 之間為單一真相），negative lookahead 排除 end 行誤匹配；對齊紀律 #5 跨工具對齊
- P0-AUDIT-05 — `pg_isready ... 2>&1` 保留 stderr 並 log `lastPgError`（紀律 #1）
- P0-AUDIT-06/07 — 補 `tests/tools/test_mutation_analysis.py` 21 case + `tests/tools/test_mutation_baseline_lock.py` 20 case（紀律 #4 鏡子）；證明能拒絕空 log / help fallback / marker 不一致 / 7 連續未達等假 PASS 場景
- P0-AUDIT-08（**最關鍵 — 紀律 #6 採集/升級分軌**）— `ac4_nightly_collector` 改用獨立 env `AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS`（預設 80ms）；`ac4_progress_check` 改用 `AUTOCLAUDE_STRICT_P95_THRESHOLD_MS`（預設 50ms）；`run_local_nightly.ps1` 同時設兩 env 不再 swap → 升級 progress_check 用嚴格門檻過濾 collector 寬鬆標 pass 的紀錄
- P0-AUDIT-09 — `Invoke-Native` capture native exit code 後寫回 `$global:LASTEXITCODE`（避免 pipeline 末段 cmdlet 覆寫；紀律 #1）
- P0-AUDIT-10（範圍標註） — PASS 引用 RunId log 行號（紀律 #3）由本節落地

**P1 (Major) 7 項 CLOSED**：P1-AUDIT-11/14/15/16/17/19/22（git rev-parse try/catch / marker 對齊 / `_parse_ts` None-safe / sh 不用 `-e` / perf cache fresh / failure reason 保留 / psql stderr 保留）

**P2 (Minor) 4 項 CLOSED**：P2-AUDIT-24/25/28/30（dead code / 壞 timestamp WARN / 重複 import / `MIN_BASELINE_SAMPLES` SSOT 註解）

**測試結果**：`pytest tests/contract/ tests/tools/ -p no:randomly` **567 passed / 111 skipped / 0 fail**；新增 41 case mirror 單元測試全綠。

**範圍外不在本次處理**：W2 待辦三項（perf samples=20 重採 / 觀察期 #1 累計 7 次寫 baseline / AC4 嚴格 50ms PG IO 調校）；P2-AUDIT-27（seed_kb 註解過時）；pytest-randomly 隨機順序 cross-test cwd state leak（pre-existing test isolation 議題）。

### W2 後續處理（2026-05-21 — PM 派工 + zero-trust audit Architect/SA/SD/QA 全能專家）

對應 §523 範圍外五項。PM 派工後另派 zero-trust audit 全面比對「nightly 程式設計意圖 vs 系統現況」，發現 2 P0 + 3 P1 + 3 P2，全數修復後新增 mirror 單元測試 17 case 並通過。

**5 項範圍外處理 — 全數 CLOSED**：

| # | 項目 | 修法 | 取證 |
|---|------|------|------|
| 1 | **W2-#1 perf samples=20 重採** | 新建 [tools/perf_baseline_lock.py](../../tools/perf_baseline_lock.py)（連續 7 次 samples ≥ 20 達標 + 同日去重 M-05 + 增量 < 15% 才寫入）；改 [tests/perf/test_decide_correction.py](../../tests/perf/test_decide_correction.py) / [test_dry_run_e2e.py](../../tests/perf/test_dry_run_e2e.py) / [test_token_halt_roundtrip.py](../../tests/perf/test_token_halt_roundtrip.py) `runs=7 → 20`；[run_local_nightly.ps1](../../tools/run_local_nightly.ps1) perf stage 加 `perf_baseline_lock.py` 子步；ADR-SD08-003 §3 CI yaml 同步 `--benchmark-min-rounds=20` | [tests/tools/test_perf_baseline_lock.py](../../tests/tools/test_perf_baseline_lock.py) 15 case 全綠 |
| 2 | **W2-#2 觀察期 #1 累計 7 次** | 邏輯確認正確（[tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py) `_utc_date_of_record` + `append_history` M-05 同日去重）— 自然累積至 2026-06-01 | `.mutation_history.jsonl` runs=2/7（latest log L151） |
| 3 | **W2-#3 AC4 嚴格 50ms 調校（雙軌語義裂縫修復）** | audit 發現原 collector status=pass + progress_check 嚴格 fail 會雙天累積 → 5 天觸 alert_red 誤報。修 [tools/ac4_progress_check.py](../../tools/ac4_progress_check.py) `_is_green()` 加 p95×1.2 neutral 三段：< 嚴格 → 綠；嚴格~×1.2 → neutral（不污染 fail/green streak）；> ×1.2 → 真 fail | [tests/contract/test_ac4_progress_check.py](../../tests/contract/test_ac4_progress_check.py) 新增 2 case 全綠（neutral / 真 fail 雙軌驗證） |
| 4 | **P2-AUDIT-27 seed_kb 註解過時** | [tools/seed_kb.py](../../tools/seed_kb.py) 第 6 行 `ac4_progress_check.py:84 status 判定` → `_is_green() 三態 sentinel` | 註解已更新（commit pending） |
| 5 | **pytest-randomly cwd leak** | [tests/conftest.py](../../tests/conftest.py) 新增 autouse `_preserve_cwd` fixture：snapshot cwd + 自動還原 + leak 印 WARN | 全 589 passed / 111 skipped 全綠（無打破現有測試） |

**Audit 補充發現（P0/P1 隨修）**：
- P0-W2-#1 重採無工具：已新建 `perf_baseline_lock.py` + 整合 nightly stage 3
- P0-AC4 雙軌裂縫：`_is_green()` 三態 sentinel 修法（neutral 觀察期）
- P1-ground_truth UUID 漂移：列入 **既知殘留**（W3 處理）— `seed_kb.py` 用 PG `gen_random_uuid()` 預設，docker 重啟後 fixture 變動 → 不阻塞 nightly correctness，但污染 git diff；W3 改 `uuid5(NAMESPACE_DNS, f"mock_class_{i}")` deterministic
- P1-cwd autouse 範圍：暫不收窄（實測無 perf 影響）
- P2-ADR-SD08-003 §3 CI yaml：已同步 `--benchmark-min-rounds=20`

**測試結果**：`pytest tests/contract/ tests/tools/ tests/utils/ -p no:randomly` **604+ passed / 111 skipped / 0 fail**（新增 17 case mirror）。

**手動 nightly 驗證**（取證：[logs/nightly_2026-05-21_103755.log](../../logs/nightly_2026-05-21_103755.log)）：

| 觀察期 / Stage | 實測結果 | 對應 log 行號 | 解讀 |
|----------------|---------|---------------|------|
| mutation #1 | kill_rate=71.14% runs=2/7（最新 5/21 02:42；首次 5/20 20:59 為 74.50%；W1 補測前 baseline=53.69% killed/total=80/149，**以 .mutation_history.jsonl 為單一真相**）| L151 | 仍 ≥ 70% 容忍門檻；自然累積至 2026-06-01 |
| AC4 #2 採集 | recall=0.999 p95=53.18ms cb=0 status=pass | L176 | 採集寬鬆 80ms 通過 |
| AC4 #2 升級判定 | consecutive_failures=**0** | L181 | **雙軌裂縫修復成功** — 修復前 consecutive_failures=2 持續累積；修復後 53.18 < 60 (50×1.2) 視為 neutral 不污染 fail streak |
| perf-baseline | stage exit=0 | L218 | W2-#1 整合 `perf_baseline_lock.py` 採集中（首次寫入 history） |
| perf_baseline_lock | decide_correction/dry_run_e2e/token_halt_roundtrip 各 runs=0~1/7 | L215-217 | 首批 samples=20 baseline 已寫 .perf_history.jsonl；連續 7 次達標將 overwrite .perf_baseline.toml |
| drift_log #3 | rows=0 | (END summary L225) | 觀察期 #3 累計 |
| END summary | `mutation=0 pg-e2e=0 perf=0 drift=0` | L225 | 全綠首次 |

**Audit P0/P1 隨修 + 後修**：
- 後修：ps1 perf stage 保留 `regression_check rc` 作 stage rc（紀律 #1）— baseline_lock 是觀察期工具不蓋 regression 信號；本次因 baseline 仍 samples=7 統計噪音 nightly 將仍標 perf=1 直至 W2-#1 連續 7 次 samples=20 lock 完成 overwrite。

**5 項範圍外處理全數 CLOSED + 5 項 audit 缺陷全 CLOSED + nightly 取證 APPROVED**。

#### QA 最終核准（2026-05-21 — Tech Lead 兼 QA zero-trust 核章）

依「nightly 實測 vs 設計意圖」比對核章：

| 審項 | 結果 | 取證 / 理由 |
|------|------|------------|
| A1 W2-#1 lock policy 對齊 ADR-SD08-003 v1.1 §2.6 | ✅ PASS | `MIN_SAMPLES=20` + `CONSECUTIVE_RUNS=7` + `BLOCK_THRESHOLD=0.15` 三常數對齊 ADR 文字定義 |
| A2 perf tests runs=20 不 break 既有 baseline | ✅ PASS | 既有 baseline (samples=7) 不被自動覆寫；`write_baseline` 拒寫 samples<20；新 baseline 將由 lock 工具於連續 7 次達標時 overwrite |
| A3 baseline_lock 不蓋 regression_check rc | ✅ PASS | 後修 ps1 `$regressionRc` 捕獲 + 末段 `$global:LASTEXITCODE = $regressionRc` 還原（紀律 #1） |
| B1 _is_green neutral 邊界 50×1.2=60ms 合理 | ✅ PASS | 20% buffer 比 BLOCK_THRESHOLD 15% 寬一層；對齊「採集寬鬆 / 嚴格判定」雙軌設計 |
| B2 neutral 不破升級條件（潛在 stale 風險） | 🟡 ACCEPTED | 若 p95 永遠在 [50, 60) → green_streak 不漲 → ready 不觸發；但 `reasons` 寫「連續全綠不足」會持續提示 PM 介入，符合 PM #2 「真實 PG 達標才升級」拍板意圖 |
| C1 PASS 聲稱引用 RunId log 行號（紀律 #3） | ✅ PASS | `logs/nightly_2026-05-21_103755.log` L151/176/181/215-218/225 全部引用 |
| C2 雙軌裂縫修復取證真實 | ✅ PASS | L181 `consecutive_failures=0`（修復前該行為 2）— 真實對比可信 |
| D1 P1-ground_truth UUID 漂移列 W3 範疇 | ✅ PASS | 不阻塞 nightly correctness（idempotent 路徑保 UUID 穩定）；僅污染 git diff |
| 全測試 regression | ✅ PASS | `pytest tests/contract/ tests/tools/ tests/utils/ tests/perf/ -p no:randomly` **609 passed / 112 skipped / 0 fail** |
| nightly 全綠首次 | ✅ PASS | `mutation=0 pg-e2e=0 perf=0 drift=0`（L225）|

**核章結論**：✅ **APPROVED** — 5 項範圍外處理 + 5 項 audit 修復全數符合原設計功能意圖。下次 nightly 因 perf baseline 仍 samples=7 統計噪音將仍標 perf=1（regression check 真實 fail 信號），直至 W2-#1 連續 7 次 samples=20 lock 完成 overwrite — 此為「真實 fail 不被工具覆蓋」設計意圖之必然，**不視為 regression**。

---

### W0 收尾 — observability snapshot 採集啟動（2026-05-21）

D-16 落地：新建 `tools/observability_snapshot.py`（≤ 150 LOC data tier）+ `tests/tools/test_observability_snapshot.py`（4 case）+ `run_local_nightly.ps1` stage 5 `observability-snapshot` 介接。

- **30 天起算日**：2026-05-21（`.observability_history.jsonl` 首筆 ts=2026-05-21T07:51:43+00:00；對齊真實寫入日 — SD_09 W0 P1-AUDIT-37 修復）
- **W5 雙條件 (1a) 取證 cutoff**：2026-06-20（2026-05-21 + 30 天；連續綠後 `tools/observability_ga_check.py --window 30 --json` 報 `green_streak >= 30`）
- **schema**：`{ts, observability_emit_count, trace_id_continuity, kb_metric_snapshot{hit_rate, query_p95_ms, strategy_rotation_count, cache_eviction_count, ...}}`
- **同日去重**：UTC date 已存在則覆寫該日最後一筆（紀律 M-05 對齊 ac4_nightly_collector）

對應 ADR-SD09-001 §2.5 / ADR-SD08-004 §2.4 / D-16 修復項。

---

**文檔元數據**：v1.0 + W2 進度附錄（2026-05-21 增量補入，非升版）| 建立 2026-05-18（SD_08 W6 G6 同步交付）| 首輪修復 2026-05-19（首輪四方審查）| 二輪修復 2026-05-19（二輪四方審查 16 Critical + 25 Major + 21 Minor）| **v0.4 zero-trust audit 修復 2026-05-19**（P0-D1~D5 共 5 項；補 3 條風險 + 4 個 stub + 元數據漂移修復）| **觀察期執行附錄補入 2026-05-20 ~ 2026-05-21**（W0 首輪 P0-1/P0-3/P1-1/P1-2/P1-3/P1-4 nightly 三輪修復；**W0 二次 zero-trust audit 2026-05-21** 補修 P0-A/B/C/D/E + P1-F/G/I 共 8 項 + S-1~S-4 結構性問題標註）| **W2 zero-trust audit 2026-05-21** Architect/SA/SD/QA 三方審查 30 項（P0=10 / P1=12 / P2=8）→ 21 項範疇內 CLOSED + 567 tests 全綠 + QA APPROVED；P0-AUDIT-10 引用 log 行號 `logs/nightly_2026-05-21_093112.log` | **v0.5 W2-Followup（範圍外 5 項）2026-05-21** PM 派工 + Architect/SA/SD/QA 全能專家 zero-trust audit（發現 2 P0 + 3 P1 + 3 P2，全 CLOSED）+ 新建 `tools/perf_baseline_lock.py` + 17 case mirror test + `_is_green` 三態 sentinel 雙軌裂縫修復 + ps1 後修保留 regression_check rc；**nightly 首次全綠**（`mutation=0 pg-e2e=0 perf=0 drift=0` @ `logs/nightly_2026-05-21_103755.log` L225）+ 609 tests 全綠 + QA Tech Lead 兼任核章 ✅ APPROVED | **D-16 + D-17 + D-22 W0 收尾補修 2026-05-21**（observability snapshot 採集啟動 + ADR-SD09-007 hook governance v1.0 + CLAUDE.md alembic 0015_merge 記錄）| 撰寫者 Tech Lead | 場景 A 個人開發 | 待觀察期收尾 + W0 PM 拍板 + 二輪四方複審 APPROVED + 二次 audit P0/P1 全 CLOSED → v1.0
