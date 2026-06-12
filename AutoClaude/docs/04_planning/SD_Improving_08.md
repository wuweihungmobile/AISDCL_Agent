# SD_Improving_08 — 精進 Sprint 規劃（v1.0）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0（三方獨立研究 + QA 量測可行性 + PM 4 項拍板，2026-05-18）** |
| 建立日期 | 2026-05-18 |
| 前置文件 | [SD_Improving_07.md](SD_Improving_07.md) v1.1（W6 G6 通過 ✅ 2,012 passed / 121 skipped 2026-05-18）/ [SD07_Migration_Guide.md](../08_deployment/SD07_Migration_Guide.md) v1.0 §5 §7 |
| 文件狀態 | **APPROVED — 待 G0 啟動準備** |
| 啟動日（PM 拍板）| **2026-05-21**（前置：2026-05-20 EOD 完成 W0 task breakdown + ADR-SD08-001~005 草案）|

---

## 0. 觸發 SD_08 的事實依據（三方共識確認）

| 觸發來源 | 證據 | 性質 | 對應議題群 |
|---------|------|------|----------|
| SD_07 遺留延期 | 四方審查 m-Arch3 + m-SD3（PM 拍板 SD_08 W0 處理）| 短期收尾 | A |
| Migration Guide §5 v2 backlog | 3 項非阻塞優化（`_impl.py` 物理行精簡 / `_runner_internals` contract 防復活柵欄 doc 化 / `prompt_builder.py` 416 LOC 拆 package 決議）| 美學改善 | B |
| AC4-1 / AC4-2 nightly pending | SD_07 W2 真實 PG e2e 改 nightly pending；採集首次 nightly CI 實測 | 數據採集 | C |
| mutation-test-nightly baseline 未設 | SD_07 W5 T5-6 已建 job，但未設 mutation score 目標 | 品質深化 | D |
| CLAUDE.md 肥胖 712 行 | SD_03~SD_07 各段 ~100~200 行；可讀性下降 | 文件治理 | E |
| 真實 PG production 上線紅線 | SD_06 W3 §7.2 + PM W-1：人類 DBA staging（≥1M 真實列）+ 親簽未完成 | 生產就緒 | H（延 SD_09）|
| 可觀測性債務 | EventBus trace_id 端對端未整合 / KB 命中率無 metric / AutoResume 健壯化 | 維運能力 | F |
| 性能 baseline 缺失 | e2e 執行時間無 baseline；無回歸告警 | 性能監控 | G |

---

## 1. Sprint 範圍（PM 拍板優先順序 A→F→D→C→E→B→G→H）

| 優先 | 議題群 | 範圍 | 對應 Wave |
|-----|--------|------|----------|
| **1** | **A. SD_07 遺留收尾**（m-Arch3 + m-SD3）| 拔除史註解集中 / CLAUDE.md W4「9 處 patch path」校準 | W0 |
| **1** | **F. 可觀測性升級**（議題 4 為 H 前置）| 新建 `IObservabilityPort` + LocalLogger adapter / trace_id 端對端 (`contextvars.ContextVar`) / KB metric 4 項 / AutoResume 健壯化 | W4 |
| **2** | **D. mutation-test baseline**（議題 1）| W3 pilot TokenGuardPlugin 兩週 → 連續 7 次達標 +0%/-5% 才寫 `.mutation_baseline.toml` / continue-on-error 維持 | W3 |
| **2** | **C. AC4 nightly 結果採集 + 升級評估**（議題 6）| 14 天 nightly 採集 / recall@10 + p95 + recall σ + CircuitBreaker open=0 / 漸進式升級為 labeled PR 觸發 | W2 |
| **3** | **E. CLAUDE.md 文件治理**（議題 2）| ≤ 400 行 + `[Architecture Snapshot]` SSOT 區段 + 滾動窗口 N=2 + sprint_history.md 交叉索引 | W0 |
| **4** | **B. Migration Guide v2 backlog 評估**（3 項）| 評估後 2 項合規即可延 SD_09 / `_runner_internals` contract 文件化必做 | W1 |
| **4** | **G. 性能 baseline 與回歸監控**（議題 5）| CI runner nightly 連跑 7 次 + 4 場景 / perf machine 季度校準 / p95 < 15% / GitHub Actions annotation + PR comment 雙通道 | W5 |
| **4** | **H. 真實 PG production SOP**（議題 3，**PM 拍板延 SD_09**）| **SD_08 僅做前置**：WAL lag adapter（`pg_health.py`）+ 雙軌制 ADR-SD08-005 草案 / 完整 SOP 待 SD_09 觸發 | W5 |

---

## 2. 6 大議題對應 + SD_08 強化方向

| 議題 | SD_07 完成度 | SD_08 強化方向（PM 拍板後）|
|------|-------------|---------------|
| **#0 Minimax/Claude Code 分工** | ✅ W2 e2e 10 case | **F**：trace_id `contextvars.ContextVar` 端對端可觀測 + EventBus 自動注入 |
| **#1 肥胖檔案** | ✅ W1 _impl.py 邏輯行 ≤ 500 | **B**：v2 backlog 第 1 項評估（物理行精簡）+ `_runner_internals` contract 文件化（防復活柵欄） |
| **#2 Plugin 架構** | ✅ W5 14 plugin walk-through + Rule 6 | **D**：mutation pilot TokenGuard 補漏測 + 分模組目標 75/70/65% |
| **#3 PG 三層任務模型** | ✅ SD_06 W3 完成 | **H（延 SD_09）+ F**：SD_08 僅做 WAL lag adapter + ADR-SD08-005 雙軌制草案 |
| **#4 向量檢索** | ⏳ AC4 nightly pending | **C**：14 天 nightly 採集 + AC Matrix 填入 + 升級為 labeled PR 觸發 |
| **#5 狀態保存恢復** | ✅ W2 multi_run 10 case | **F**：AutoResume 健壯化（超時 + 恢復點優化 + wake_kinds 擴展） |
| **#6 ConfigResolver** | ✅ W2 14 case | **E**：CLAUDE.md 文件治理（meta 配置可讀性） |

---

## 3. Wave 規劃（6 Wave；範圍與 Gate 對齊）

| Wave | 範圍 | 對應議題群 | 預估 Gate 測試基線 |
|------|------|----------|------------------|
| **W0** | SD_07 遺留收尾 + CLAUDE.md 精簡 ≤ 400 行 + Architecture Snapshot SSOT + sprint_history.md 下沉 + ADR-SD08-001~005 落地 + `tools/snapshot_sync.py` 與 CI 行數檢查 | A + E | ≥ 2,012（持平）|
| **W1** | v2 backlog 三項評估 + 必要時拆解 + `_runner_internals` contract 文件化（防復活柵欄） | B | ≥ 2,012 |
| **W2** | AC4 nightly 14 天採集 + recall σ + CircuitBreaker open=0 + `needs-pg-e2e` labeled PR 觸發 + `gh run` 統計工具 | C | ≥ 2,025 |
| **W3** | mutation pilot TokenGuardPlugin 兩週 + 補漏測 + `.mutation_baseline.toml` 寫入 + `-p no:xdist` 鎖定 | D | ≥ 2,050 |
| **W4** | **核心**：`IObservabilityPort` 新建（core/ports/）+ LocalLogger adapter（infra/adapters/observability/）+ trace_id contextvars + KB metric 4 項 + AutoResume 健壯化 | F | ≥ 2,080 |
| **W5** | 性能 baseline 4 場景 + nightly 連跑 7 次 + perf annotation + WAL lag adapter（`pg_health.py`）+ ADR-SD08-005 SD_09 前置 | G + H 前置 | ≥ 2,095 |
| **W6** | 四方審查 + Migration Guide v1.0 + Sprint 收尾 | 收尾 | ≥ 2,100 |

---

## 4. 預期關鍵交付物

### 4.1 程式碼與工具
- `autoclaude/core/ports/observability.py`（新 — `IObservabilityPort` Protocol：`emit_counter` / `emit_histogram` / `start_span` / `record_event`）
- `autoclaude/infra/adapters/observability/local_logger.py`（新 — LocalLogger adapter）
- `autoclaude/utils/trace_context.py`（新 — `trace_id: ContextVar[Optional[str]]` + `with_trace_id()` helper + daemon thread `copy_context().run()` 包裝）
- `autoclaude/utils/knowledge_base_metrics.py`（新 — `hit_rate / query_p95_ms / strategy_rotation_count / cache_eviction_count` + `snapshot() -> dict` 一致 AutoResumeMetrics 模式）
- `autoclaude/infra/observability/pg_health.py`（新 — `PgHealthMonitor.get_wal_lag_seconds()` / `get_active_connections()` — SD_09 前置）
- `autoclaude/utils/perf_baseline.py`（新 — 4 場景 e2e 量測 + p95/p99 採集 + JSON 落地）
- `tools/mutation_analysis.py`（新 — 解析 `mutation_*.log` + survived diff 補測建議）
- `tools/perf_regression_check.py`（新 — GitHub Actions annotation + PR comment 雙通道告警）
- `tools/snapshot_sync.py`（新 — 從程式碼自動回填 `[Architecture Snapshot]` 區段 + 7 天 freshness 檢查）

### 4.2 CI / 自動化
- `mutation-test-nightly` job：W3 pilot TokenGuardPlugin 改用 `--paths-to-mutate=autoclaude/plugins/token_guard --tests-dir=tests/plugins/token_guard --no-progress -p no:xdist`，連續 7 次達標後寫 `.mutation_baseline.toml`
- `pg-e2e-nightly` 累積 14 天全綠後升級為 **labeled PR 觸發**（`needs-pg-e2e` label）
- 新增 `perf-baseline-nightly` job（連跑 7 次取中位數 + p95）
- 新增 `claude-md-budget` job（CI 強制 `wc -l CLAUDE.md` ≤ 400 + Snapshot freshness ≤ 7 天告警）

### 4.3 文件
- `docs/04_planning/SD_Improving_08.md` v1.0（本檔）
- `docs/05_development/sprint_history.md`（新 — SD_03~SD_07 歷史下沉 + 交叉索引：sprint 編號 + 議題索引表 reverse-link）
- `docs/06_quality/SD08_Mutation_Baseline_Report.md`（新 — W3 末產出）
- `docs/06_quality/SD08_Perf_Baseline_Report.md`（新 — W5 末產出）
- `docs/08_deployment/Production_Migration_SOP.md`（新 — yaml_only → both → db_only 灰度，**SD_08 僅出草案，正式版於 SD_09**）
- `docs/08_deployment/SD08_Migration_Guide.md`（新 — W6 末產出）
- `CLAUDE.md` 精簡至 ≤ 400 行 + `[Architecture Snapshot]` SSOT 區段

### 4.4 ADR（PM 拍板後落地）
- **`ADR-SD08-001`**：CLAUDE.md sprint 歷史下沉策略 + Snapshot SSOT 滾動窗口 N=2
- **`ADR-SD08-002`**：mutation score baseline 分模組目標（75/70/65%）+ pilot 策略 + 連續 7 次達標鎖定
- **`ADR-SD08-003`**：性能回歸告警閾值（p95 增量 < 15% / GitHub Actions annotation）
- **`ADR-SD08-004`**：`IObservabilityPort` 設計（trace_id contextvars + 階段性混合 + SD_10 OTel 遷移策略）
- **`ADR-SD08-005`**：PG production 雙軌制（AI-Agent 演練前置 + 人類 DBA 親簽）— SD_09 啟用前置條件

---

## 5. 已知風險（連動 risk_log §14）

| ID | 風險 | 嚴重度 | 緩解方向 |
|----|------|--------|---------|
| R-SD08-A-1 | CLAUDE.md 歷史下沉後對話初始 context 缺失 | 🟠 | sprint_history.md 保留 SD_06+SD_07 完整摘要（滾動窗口 N=2）+ 頂端「快速導覽」3 行指引 |
| R-SD08-C-1 | AC4 nightly 連續 14 天仍 SKIP（PG 環境未啟用）| 🟠 | W2 開工前確認 `pg-e2e-nightly` 至少跑 1 次成功；nightly fail 連續 3 次黃線告警 |
| R-SD08-D-1 | mutation score 首測 < 65%（coverage 100% ≠ mutation 100%）| 🔴 | W3 pilot 單模組 + survived diff 補測；分模組差異化目標；W3 不設阻塞門檻 |
| R-SD08-D-2 | mutmut nightly 單模組超 45 min 上限 | 🔴 | `--paths-to-mutate` + `--tests-dir` 縮限 + `-p no:xdist`；單模組 wall time AC ≤ 40 min |
| R-SD08-F-1 | trace_id daemon thread 邊界斷鏈（`NonBlockingStreamReader`）| 🟠 | `copy_context().run()` 顯式包裝 + 單元測試覆蓋 PTY 邊界 |
| R-SD08-F-2 | `IObservabilityPort` 放錯層（utils 而非 core/ports）退化為散裝技術債 | 🔴 | ADR-SD08-004 明文 core/ports/ + importlinter Rule 7 禁 plugin 直接 import utils.observability |
| R-SD08-G-1 | perf baseline 在 GitHub Actions runner pgvector 場景變異 ±50% | 🔴 | pgvector p95 baseline 跑專用 perf machine（季度校準），CI 僅跑 CPU-bound 場景（dry_run/TokenHalt） |
| R-SD08-H-1 | SD_08 未鎖死 dual-state drift 觀測閾值，SD_09 無客觀切換條件 | 🔴 | W5 落地 WAL lag adapter + drift_log 30 天零事件 SLA + ADR-SD08-005 草案明文 SD_09 啟用條件 |
| R-SD08-E-1 | CLAUDE.md ≤ 400 行 CI 強制檢查未建立，6 個月後再次膨脹 | 🟠 | W0 同步交付 `claude-md-budget` CI job + Snapshot 7 天 freshness 告警 |

---

## 6. PM 拍板決議（2026-05-18）

| # | 項目 | PM 決議 | 影響 |
|---|------|---------|------|
| **1** | CLAUDE.md 精簡幅度（議題 2）| ✅ **(b) ≤ 400 行 + Snapshot SSOT + 滾動窗口 N=2**（Architect/SA 雙方共識）| W0 文件治理 + `claude-md-budget` CI |
| **2** | AC4 nightly 升級判準（議題 6）| ✅ **漸進式升級**：14 天 nightly + 兩者皆需 + recall σ ≤ 0.02 + CircuitBreaker open=0；初期非阻塞，全綠後改 **labeled PR 觸發**（`needs-pg-e2e`）| W2 採集 + CI 額外時間僅落於 labeled PR |
| **3** | mutation baseline 目標（議題 1）| ✅ **(c) 分模組差異化**：TokenGuard ≥ 75% / GoalSynthesis ≥ 70% / Coordinator ≥ 65%；W3 pilot 單模組兩週；continue-on-error 維持；連續 7 次達標鎖定 baseline | W3 不設阻塞門檻（揭露門檻）|
| **4** | PG production SOP 啟動時機（議題 3）| ✅ **延至 SD_09**；SD_08 W5 僅做 WAL lag adapter + ADR-SD08-005 雙軌制草案；綁定「可觀測性 GA + 30 天零 drift」雙條件 | SD_08 範圍縮小 + SD_09 啟動條件明文 |
| **5** | 可觀測性升級範圍（議題 4）| ✅ **(c) 階段性混合**：W4 新建 `IObservabilityPort`（core/ports/）+ LocalLogger adapter + trace_id `contextvars.ContextVar`；SD_10 後再外掛 OTel | W4 為議題 #0/#3/#5 共同前置 |
| **6** | 性能 baseline 採集環境（議題 5）| ✅ **(b)+(c) 雙軌**：CI nightly 連跑 7 次（CPU-bound 場景）+ 季度 perf machine 校準（pgvector p95）；p95 增量 < 15% | W5 落地 + perf machine 採購延 SD_09 評估 |
| **7** | 議題群優先順序 | ✅ **A→F→D→C→E→B→G→H**（必做先行 / 品質深化 / 文件治理 / 評估性 / H 延 SD_09）| 不管 PD 預算 |
| **8** | SD_08 啟動日 | ✅ **2026-05-21**（2026-05-20 EOD 前完成 W0 task breakdown + ADR-SD08-001~005 草案；無 production smoke 需求；沿用個人開發場景 A）| W0 立即啟動 |

---

## 7. 三方獨立研究意見摘要（2026-05-18 並行收集）

### 7.1 Architect 意見（議題 2/3/4）
- **議題 2**：推薦 (b) ≤ 400 行；新增 `[Architecture Snapshot]` SSOT；滾動窗口 N=2；CI 強制 + 7 天 freshness 告警
- **議題 3**：推薦 (b) 延 SD_09；雙條件綁定（可觀測性 GA + 30 天零 drift）；雙軌制 ADR（AI-Agent 演練 + 人類 DBA 親簽）；風險順序 WAL lag > IOPS 配額 > 並發負載
- **議題 4**：推薦 (c) 階段性混合；**必須**新建 `IObservabilityPort`（core/ports/）；EventBus 為消費者而非實作者（單一職責）

### 7.2 SA 意見（議題 2/6）
- **議題 2**：推薦 (b) ≤ 400 行；sprint_history.md 交叉索引（主目錄 sprint 編號 + 議題索引表 reverse-link）；CLAUDE.md 必留：語言規範 / 開發-編譯-測試循環 / 文檔目錄 / Agent 載入 / 核心目錄結構
- **議題 6**：推薦 (c)+(d) 兩者皆需 + recall σ ≤ 0.02；漸進式升級避免一次性 PR cycle time 拖累；告警分級（黃 2 次 / 紅 3 次阻塞 / P1 5 次）

### 7.3 SD 意見（議題 3/4/5）
- **議題 3**：pg_stat_statements + 自建 `PgHealthMonitor` 雙層；WAL lag adapter 放 `infra/observability/`（不放 repositories）；告警 2s warn / 10s critical；並發測試 locust + 100→500→1000 三階梯
- **議題 4**：`contextvars.ContextVar` + EventBus 自動注入混合；KB metric 4 項（`hit_rate / query_p95_ms / strategy_rotation_count / cache_eviction_count`，不含 cache_size）；daemon thread 邊界需 `copy_context().run()` 包裝
- **議題 5**：(b)+(c) 雙軌；量測 4 場景；p95 增量 < 15%（比 20% 收緊 5%）；annotation + PR comment 雙通道

### 7.4 QA 意見（議題 1/6 + 量測可行性）
- **議題 1 可行性**：3 模組同時 nightly 風險過高 → pilot 單模組兩週；`--paths-to-mutate` + `--tests-dir` 縮限至 30-50 min/模組；鎖 `-p no:xdist` 避 hash 衝突
- **議題 1 baseline**：(c) 分模組差異化（75/70/65%）；W3 揭露門檻 + 連續 7 次達標 -5% 才鎖定；預期 token_guard 首測落 65-72%
- **議題 6**：(c)+(d) 兩者皆需 + 0 flaky + recall σ ≤ 0.02；14 天觀察期；改 **labeled PR 觸發**（`needs-pg-e2e`）避免每 PR +8-12 min CI 月度額度爆預算

---

## 8. SD_07 結尾狀態快照（前置基線）

| 項目 | 實測 |
|------|------|
| 全測基線 | **2,012 passed / 121 skipped** |
| equivalence | **83/83** |
| importlinter | **6 kept / 0 broken**（含 Rule 6 `runner-no-checkpoint-logic`）|
| LOC violations | **0**（total=14058 / baseline=14058 永久鎖定 / cap=16869）|
| NOTE(SD_07) | **0**（autoclaude/ + tests/）|
| 四方審查 W6 G6 | **4/4 APPROVED** |

---

## 9. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v0.1 | 2026-05-18 | 精進大綱草案 — 8 議題群（A~H）+ 6 Wave 預估 + 4 ADR 預埋 + 6 三方待答議題 |
| **v1.0** | 2026-05-18 | **三方獨立研究 + QA 量測可行性 + PM 8 項拍板 → 正式 Sprint 規劃**（議題群優先 A→F→D→C→E→B→G→H；mutation 分模組目標；CLAUDE.md ≤ 400 行 + Snapshot SSOT；AC4 漸進式升級；PG production 延 SD_09；可觀測性 W4 階段性混合 + IObservabilityPort；性能雙軌；ADR 擴增至 5 條；啟動日 2026-05-21）|

---

**對應參考文件**：
- [SD_Improving_07.md](SD_Improving_07.md) v1.1 — 前置 Sprint 主規劃
- [SD07_Migration_Guide.md](../08_deployment/SD07_Migration_Guide.md) v1.0 §5 v2 backlog + §7 已知限制
- [ADR-SD07-001-loc-policy.md](ADR/ADR-SD07-001-loc-policy.md) v1.0 — LOC 分級政策（SD_08 沿用）
- [SD07_AC_Matrix.md](../03_testing/SD07_AC_Matrix.md) v1.1 — 19 條 AC（SD_08 將擴增至 ≥ 27 條）
- [risk_log.md](../05_development/risk_log.md) §14 — SD_08 風險登記（R-SD08-A-1~H-1）
- [gate_audit.md](../05_development/gate_audit.md) §1-sexies — SD08-G0~G6 簽核紀錄

**G0 啟動條件**（2026-05-20 EOD 前）：
1. Tech Lead 提交 W0 task breakdown + ADR-SD08-001~005 草案（PM 形式核准）
2. `tools/check_loc_budget.py` 加入 `CLAUDE.md ≤ 400` 規則
3. `claude-md-budget` CI job 設計就位
4. `sprint_history.md` 骨架建立（保留 SD_03~SD_05 完整下沉 + SD_06/SD_07 摘要留 CLAUDE.md）
