# Migration 技術棧遷移 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2026-04-16
**適用對象**: 系統架構師、資深開發者、DevOps 工程師、技術負責人
**建議閱讀**: 先閱讀 `SOP_QuickRef.md` 和 `SOP.md`
**對應 SDD 增強**: `SDD_MIGRATION_ENHANCEMENT.md`
**文檔類型**: 技術參考、深度執行指引

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 執行大規模技術棧遷移（前端+後端+DB 同時遷移）
- 需要零停機（Zero-Downtime）切換策略
- 資料庫平台遷移（如 MySQL → PostgreSQL）
- 需要制定 Migration Contract Map（MCM）
- 遷移過程涉及多個外部系統 API 契約
- 需要設計回滾（Rollback）與 Cutover 規格

❌ **不建議閱讀的情況**:
- 初次執行 Migration 專案（請閱讀 `SOP.md`）
- 快速流程參考（請閱讀 `SOP_QuickRef.md`）
- 簡單的套件版本升級（屬於 Brownfield 範疇）

### 文檔結構

```
Part 1: Migration Contract Map（MCM）設計
Part 2: 資料庫遷移深度技術
Part 3: API 契約凍結與 Strangler Fig 模式
Part 4: 並行運行（Dual-Write）策略
Part 5: Cutover 規格與零停機切換
Part 6: 回滾（Rollback）規格設計
Part 7: 資料完整性驗證策略
Part 8: SDD SCG 閘門執行細則
Part 9: 常見遷移反模式與解法
Part 10: 真實遷移案例參考
```

---

## Part 1: Migration Contract Map（MCM）設計

### 1.1 MCM 是什麼

MCM（Migration Contract Map）是 SDD Migration 情境的**核心規格文件**，定義：
- **源系統（Source）** 到 **目標系統（Target）** 的映射關係
- 資料欄位轉換規則
- API 端點對應關係
- 業務邏輯等價聲明（Behavioral Equivalence）

> ⚠️ **SDD 強制要求**：MCM 必須在 SCG-2（架構凍結）前完成，禁止在 MCM 未凍結前開始實作。

### 1.2 MCM 模板使用

```
框架模板：AISDLC_SDD_v0.01/docs_template/sdd/architecture/MIGRATION-CONTRACT-MAP-TEMPLATE.md
產出位置：AISDLC_SDD_v0.01/docs/02_architecture/migration/MCM-{SystemName}.md
```

### 1.3 MCM 關鍵欄位

| 欄位 | 說明 | 範例 |
|------|------|------|
| `source_entity` | 源系統實體名稱 | `users` 表（MySQL） |
| `target_entity` | 目標系統實體名稱 | `account` 表（PostgreSQL） |
| `transform_rule` | 轉換規則（SQL/函式） | `CONCAT(first_name, ' ', last_name)` |
| `validation_query` | 驗證查詢 | `SELECT COUNT(*) FROM ... WHERE ...` |
| `null_handling` | NULL 值處理策略 | `DEFAULT 'unknown'` |
| `data_type_mapping` | 型別映射 | `INT → BIGINT`、`TINYINT(1) → BOOLEAN` |

---

## Part 2: 資料庫遷移深度技術

### 2.1 遷移方法選擇矩陣

| 方法 | 適用場景 | 停機時間 | 複雜度 |
|------|---------|---------|-------|
| Big Bang Migration | 小型 DB（< 10GB）、可接受停機 | 數小時 | 低 |
| Trickle Migration | 大型 DB、零停機要求 | 接近 0 | 高 |
| Dual-Write + Cutover | 中型 DB、並行運行期 | 分鐘級 | 中 |
| Shadow Mode Migration | 高風險遷移、需驗證一致性 | 0 | 極高 |

### 2.2 Dual-Write 雙寫策略

```
應用層
  │
  ├──► 寫入 Source DB（舊）
  │
  └──► 寫入 Target DB（新）
          │
          └──► 非同步驗證一致性
```

**實作要點**：
1. 雙寫期間以 Source DB 為**主系統**（Write Master）
2. Target DB 為驗證對象，差異記錄至 `migration_diff_log`
3. Cutover 前確認 diff_log 為空（或差異可接受）
4. Cutover 後立即切換 Write Master 至 Target DB

### 2.3 Schema 演進策略（零停機）

```sql
-- Step 1: 新增欄位（可 NULL，不影響現有功能）
ALTER TABLE orders ADD COLUMN new_status VARCHAR(50) NULL;

-- Step 2: 背景遷移資料（批次更新，避免鎖表）
UPDATE orders SET new_status = old_status 
WHERE id BETWEEN ? AND ? AND new_status IS NULL;

-- Step 3: 應用程式雙讀（讀舊欄位，寫新欄位）
-- Step 4: 應用程式切換至讀新欄位
-- Step 5: 刪除舊欄位（下次部署）
ALTER TABLE orders DROP COLUMN old_status;
```

### 2.4 資料庫平台遷移型別對應（常見）

| MySQL 型別 | PostgreSQL 型別 | 注意事項 |
|-----------|----------------|---------|
| `TINYINT(1)` | `BOOLEAN` | MySQL 0/1 → PG true/false |
| `DATETIME` | `TIMESTAMP` | 時區處理需確認 |
| `TEXT` | `TEXT` | 相容 |
| `JSON` | `JSONB` | PG JSONB 效能更好 |
| `AUTO_INCREMENT` | `SERIAL` 或 `IDENTITY` | 需確認序列初始值 |
| `ENUM` | `VARCHAR` + CHECK | PG ENUM 修改成本高 |

---

## Part 3: API 契約凍結與 Strangler Fig 模式

### 3.1 Strangler Fig 遷移模式

```
第一階段：Proxy 路由（並行）
  Client → Proxy → 舊系統（100%）
                 → 新系統（0%，僅驗證）

第二階段：灰度切換
  Client → Proxy → 舊系統（70%）
                 → 新系統（30%）

第三階段：完全切換
  Client → Proxy → 新系統（100%）
  舊系統保留 30 天作回滾備用
```

### 3.2 API 廢棄聲明（API-COMPAT 規格）

```
產出文件：AISDLC_SDD_v0.01/docs/02_architecture/api/API-COMPAT-{Module}.md
```

關鍵欄位：
- `deprecated_at`：廢棄宣告日期
- `sunset_at`：正式下線日期（建議廢棄後 90 天）
- `replacement_endpoint`：替代端點路徑
- `migration_guide_url`：遷移指引連結

### 3.3 Consumer-Driven Contract（CDC）

Migration 情境中，每個 API 消費端必須簽訂 CDC：

```
工具選擇：Pact（Node.js/Java）、Spring Cloud Contract（Java）
產出位置：docs/03_testing/contracts/CDC-{Consumer}-{Provider}.json
SCG 閘門：SCG-3（Contract Freeze）前完成所有 CDC 驗證
```

---

## Part 4: 並行運行（Dual-Write）策略

### 4.1 並行運行決策

| 條件 | 建議策略 |
|------|---------|
| DB 資料量 < 1GB，允許 2 小時停機 | Big Bang，無需並行 |
| DB 資料量 1-100GB，允許 30 分鐘停機 | Dual-Write 2 週 + Cutover |
| DB 資料量 > 100GB，零停機 | Shadow Mode + 漸進 Cutover |
| 外部系統依賴多（> 5 個） | Strangler Fig + CDC |

### 4.2 並行運行監控指標

必須追蹤以下指標：
- `migration_lag_seconds`：兩系統資料延遲（目標 < 5s）
- `diff_count`：不一致記錄數（目標 = 0 才可 Cutover）
- `error_rate_new`：新系統錯誤率（目標 = 舊系統的 ±0.1%）
- `p99_latency_new`：新系統 P99 延遲（目標 ≤ 舊系統 × 1.2）

---

## Part 5: Cutover 規格與零停機切換

### 5.1 Cutover Spec 必要內容

```
框架模板：docs_template/sdd/deployment/CUTOVER-SPEC-TEMPLATE.md
產出位置：docs/08_deployment/CUTOVER-SPEC-{SystemName}.md
SCG 閘門：SCG-6（發布前）必須完成 Cutover Spec 審查
```

**Cutover 規格核心段落**：

```markdown
## Cutover 執行序列
T-24h: 停止所有非關鍵批次作業
T-4h:  最終資料一致性驗證（diff_count = 0）
T-1h:  通知所有相關方，啟動 Cutover Watch
T-0:   執行流量切換（Proxy 設定更新）
T+15m: 驗證新系統關鍵功能（Smoke Test）
T+1h:  全面功能驗證（Regression Subset）
T+24h: 確認回滾窗口關閉

## 回滾觸發條件
- 新系統錯誤率 > 1%（持續 5 分鐘）
- 關鍵 API P99 > SLO × 2
- 任何 INV-XXX 不變量被違反
```

---

## Part 6: 回滾（Rollback）規格設計

### 6.1 Rollback Spec 三層設計

**Layer 1 — 即時回滾（< 5 分鐘）**：
- 流量切回舊系統（Proxy 設定）
- 適用於 Cutover 後 24 小時內

**Layer 2 — 資料回滾（< 2 小時）**：
- 從 Dual-Write 期間的快照恢復
- 需要確認回滾後的資料一致性

**Layer 3 — 完整回滾（< 1 天）**：
- 完整恢復至遷移前狀態
- 需要事前備份驗證（Backup Drill）

### 6.2 不可回滾的操作清單

在遷移前必須識別並記錄以下**不可逆操作**：
- 外部通知（Email/SMS 已發送）
- 第三方支付交易
- 法規要求的不可刪除記錄
- 已公開的 API 行為變更

---

## Part 7: 資料完整性驗證策略

### 7.1 三層驗證框架

```
Layer 1 — 統計驗證（快速）
  ├─ 記錄數量比對
  ├─ NULL 值分布比對
  └─ 關鍵欄位總和/平均值比對

Layer 2 — 樣本驗證（中等）
  ├─ 隨機樣本逐筆比對（建議 1000 筆或 1%）
  ├─ 邊界值比對（最大/最小值記錄）
  └─ 業務關鍵記錄比對（VIP 客戶、最近 30 天訂單）

Layer 3 — 全量驗證（完整）
  ├─ 全表逐筆比對（僅於 Cutover 前執行）
  └─ 外鍵完整性驗證
```

### 7.2 Data Integrity Test Spec

```
框架模板：docs_template/sdd/testing/DATA-INTEGRITY-TEST-SPEC-TEMPLATE.md
產出位置：docs/03_testing/DATA-INTEGRITY-TEST-SPEC-{SystemName}.md
```

---

## Part 8: SDD SCG 閘門執行細則

### Migration 情境 SCG 完整流程

```
SCG-1: 需求規格凍結
  ✅ MCM 草稿完成
  ✅ 遷移範圍聲明（In-Scope / Out-of-Scope）
  ✅ 業務不變量（INV-XXX）清單確認
  🔴 Human 確認：需求凍結 Sign-off

SCG-2: 架構設計凍結
  ✅ MCM 最終版本（所有映射規則確認）
  ✅ Migration ADR 完成（遷移方法決策）
  ✅ 並行運行策略確認
  🔴 Human 確認：架構凍結 Sign-off

SCG-3: API 契約凍結
  ✅ 所有受影響端點的 API-COMPAT 聲明
  ✅ CDC（Consumer-Driven Contract）全部通過
  ✅ OpenAPI 3.1 Diff 報告審查
  🔴 Human 確認：Contract Freeze Sign-off

SCG-4: PR Review（每個遷移 PR）
  ✅ 實作與 MCM 一致性檢查
  ✅ 無破壞性 Schema 變更未聲明

SCG-5: 交付前驗證
  ✅ Data Integrity Test Spec 全部通過
  ✅ Cutover Spec 審查完成
  ✅ Rollback Spec 審查完成
  ✅ RTM 100% 覆蓋

SCG-6: 發布前
  ✅ Cutover Drill（演練）完成
  ✅ Rollback Drill（演練）完成
  ✅ 監控告警驗證（migration_lag、diff_count）
  🔴 Human 確認：發布 Go/No-Go 決策
```

---

## Part 9: 常見遷移反模式與解法

| 反模式 | 症狀 | 解法 |
|--------|------|------|
| Schema 衝動遷移 | 先改 DB 再改應用程式 | 應用程式先相容新舊 Schema，再遷移 DB |
| 無 MCM 直接開發 | 遷移映射規則散落在程式碼中 | 強制 SCG-2 前完成 MCM |
| Big Bang 迷信 | 所有系統一次性切換 | 按業務模組漸進切換（Strangler Fig） |
| 忽略外部依賴 | 遷移後第三方無法連接 | 提前 30 天發送 API Deprecation Notice |
| 無 Cutover Drill | 切換當天才發現流程問題 | 必須執行 2 次完整 Cutover 演練 |
| 資料驗證不足 | Cutover 後才發現資料遺漏 | 三層驗證框架 + diff_count = 0 才 Cutover |
| 回滾沒有測試 | 回滾時失敗加劇事故 | Rollback Drill 是 SCG-6 的前置條件 |

---

## Part 10: 真實遷移案例參考

### 案例 A：MySQL → PostgreSQL（電商訂單系統）

**規模**：DB 85GB、日訂單 10 萬筆、7 個外部系統依賴

**關鍵決策**（對應 ADR）：
- 採用 Dual-Write + 4 週並行運行（ADR-001）
- ENUM 欄位改為 VARCHAR + CHECK CONSTRAINT（ADR-002）
- 使用 Debezium CDC 進行即時資料同步（ADR-003）

**執行時間線**：
- Week 1-2：MCM 設計 + SCG-1/2
- Week 3：API-COMPAT 聲明 + CDC 驗證（SCG-3）
- Week 4-7：並行運行期（Dual-Write）
- Week 8：Cutover Drill × 2
- Week 9：正式 Cutover（零停機，30 分鐘切換窗口）

**教訓**：`ENUM` 型別遷移比預估多花 3 天，應在 MCM 階段提前識別。

---

### 案例 B：Java Spring Boot → Node.js（微服務拆分）

**規模**：單體應用 → 5 個微服務、30 個 API 端點

**關鍵決策**：
- Strangler Fig 模式，按業務域逐步切換（ADR-001）
- BFF（Backend for Frontend）層作為路由 Proxy（ADR-002）
- 每個微服務獨立 CDC 驗證（ADR-003）

**執行時間線**：
- 每個微服務獨立完成 SCG-1~SCG-6
- 整體遷移耗時 16 週（5 個微服務並行 + 依序 Cutover）

**教訓**：跨服務事務（Distributed Transaction）設計應在 MCM 階段明確聲明補償策略。

---

**維護者**：AISDLC-SDD Framework Team
**最後更新**：2026-04-16
**版本**：v0.01
**基於**：AISDLC-SDD v0.01 | Migration 情境 SDD Enhancement
