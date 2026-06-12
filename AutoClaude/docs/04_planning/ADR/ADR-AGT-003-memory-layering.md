# ADR-AGT-003 — Agentic 記憶分層（Memory Layering）

| 項目 | 內容 |
|------|------|
| 編號 | ADR-AGT-003 |
| 狀態 | **ACCEPTED — koalawu 2026-06-13（SCG-2 🔴 人工確認）** |
| 提出者 | sd-architect（Improving_012 Phase 1） |
| 提出日期 | 2026-06-13 |
| 對應計畫 | [AutoClaude_Improving_012.md](../AutoClaude_Improving_012.md) §SCG-2（SCG-0 已凍結） |
| 相依 ADR | ADR-SD09-006（IKbMetricStore canonical）/ ADR-SD08-004（IObservabilityPort 邊界） |

## 1. 背景

Improving_012 判定 C 能力（長期記憶）🟡：checkpoint / KB JSONL / DAL 三後端已存在，但缺使用者偏好、跨 playbook 進度彙總，且 KB metrics 重啟清零。需一個明確的記憶分層模型，避免新記憶體零散落地、互相重疊。

## 2. 決策 — 四層記憶模型

| 層 | 內容 | 生命週期 | 落地（File / PG） | 既有/新增 |
|----|------|---------|------------------|----------|
| L1 執行狀態 | PlaybookCheckpoint（step_idx、counters、failure_history） | 單 playbook run（跨 halt/resume） | `*.checkpoint.json` / `checkpoints` 表 | 既有 |
| L2 經驗記憶 | FailureKnowledgeBase（error_signature→strategy）+ **KB metrics（F-C3）** | 跨 run 累積 | `failure_knowledge_base.jsonl` + `.kb_metrics_local.jsonl` / `knowledge_entries` + `kb_metrics` 表 | 既有 + F-C3 補 metrics |
| L3 使用者偏好 | PreferenceStore（修正策略偏好、報告格式、資料來源）（F-C1） | 跨專案長期 | `preferences.jsonl` / `user_preferences` 表 | 🆕 |
| L4 目標進度 | GoalProgressLedger（goal_task_id→features 聯集、達成度）（F-C2） | 跨 playbook、至 goal 完成 | `goal_progress.jsonl` / `goal_progress` 表 | 🆕 |

分層原則：
1. **一層一落地**：每層獨立檔案/表，禁止跨層混寫（如偏好不得塞進 checkpoint）。
2. **Port 邊界**：L2 metrics 走 `IKbMetricStore`、L3 走 `IPreferenceStore`（均為 core/ports 抽象）；L4 無 port（plugin 經 wiring 注入 ledger，僅 2 個呼叫點，Rule 2 不過度抽象——若 Phase 3 出現第 3 個呼叫端再升格 port）。
3. **讀取注入單向**：記憶 → Brain prompt 為唯讀注入（L3 入 correction prompt、L2 入 KB strategy hint）；Brain 輸出**不得**自動回寫 L3/L4（防自我放大，對齊 R-9.23 有界性）。寫入僅由確定性程式碼路徑（plugin hook / 使用者 config / API）執行。
4. **storage.mode 路由一致**：yaml_only→File、both/db_only→PG（三類新資料不走 Dual 影子，見 SRD §4）。

## 3. 替代方案

| 方案 | 採用 | 理由 |
|------|-----|------|
| (a) 四層分離模型（本案） | ✅ | 對齊既有 DAL 三後端與 ADR-SD09-006；每層可獨立測試/回滾 |
| (b) 統一 MemoryService 單一抽象 | ❌ | 抹平語意差異（執行狀態 vs 偏好生命週期完全不同）；god-object 風險 |
| (c) 全部塞 checkpoint 擴欄位 | ❌ | checkpoint 是 run-scoped，跨 run 記憶塞入會破壞其生命週期語意 |
| (d) 向量化長期記憶（embedding recall） | ❌ 本期 | 已有 pgvector 基建，但 F-C1/C2 為結構化 key-value/ledger，語意檢索無需求即不加（Rule 2） |

## 4. 後果

- 正面：C 能力缺口三項各有明確歸屬層；新增 2 port + 4 adapter + 2 plugin + alembic 0016（3 表）。
- 負面：ports 10→12、importlinter 7→8，架構面積擴大；PG schema 增量 1 migration。
- 風險：偏好注入使 correction prompt 變長 → 緩解：偏好區段上限 10 鍵（超出取最新），prompt_builder 截斷。

## 5. 參考

- [SRD_AGT_Phase1_Memory.md](../../02_architecture/SRD_AGT_Phase1_Memory.md)（SCG-1 介面規格）
- [ADR-SD09-006](ADR-SD09-006-kb-metric-port.md) / [ADR-SD08-004](ADR-SD08-004-observability-port.md)

---

**文檔元數據**：v1.0 ACCEPTED | 建立 2026-06-13 | SCG-2 🔴 確認欄：koalawu 2026-06-13（互動確認，與表頭狀態一致）
