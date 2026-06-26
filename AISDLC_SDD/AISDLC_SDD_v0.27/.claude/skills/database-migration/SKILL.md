---
name: database-migration
description: 規劃並執行資料庫平台遷移，整合 MCM Validate 閘門，產出 DB Schema Contract 和 Migration ADR
user-invocable: true
disable-model-invocation: false
argument-hint: "<source-db: Oracle|MySQL|MSSQL> <target-db: PostgreSQL|MySQL>"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Database Migration Skill（SDD 原生）

資料庫遷移在 SDD 中屬於 Brownfield/Refactoring 場景的核心動作。本 Skill 引入 MCM（Migration Completeness Milestone）Validate 閘門，確保每個遷移階段有規格依據，DB Schema Contract 在遷移實作前凍結。

---

## 觸發方式

```bash
/database-migration Oracle PostgreSQL
/database-migration MySQL PostgreSQL
/database-migration MSSQL PostgreSQL
```

---

## 前置條件（SDD Spec-First）

| 閘門/文件 | 說明 | 驗證方式 |
|---------|------|---------|
| As-Is SRD 存在 | 現有 DB 架構已文件化 | `docs/02_architecture/AS-IS-SRD-{System}.md`（來自 `/brownfield-analysis`） |
| DB Schema As-Is 文件 | 現有 Schema 已記錄 | `docs/07_design/DB-SCHEMA-AS-IS-{System}.md` |
| Migration ADR | 遷移決策已記錄 | `/adr-generate "資料庫平台遷移"` 已執行 |

---

## MCM Validate 閘門定義

資料庫遷移特有的驗證閘門（補充 SCG 之外的遷移專屬檢查點）：

| MCM | 名稱 | 說明 |
|-----|------|------|
| MCM-1 | Schema Freeze | DB Schema Contract 凍結（類比 SCG-3） |
| MCM-2 | Migration Script Validate | 遷移腳本驗證（Staging 環境） |
| MCM-3 | Data Integrity Check | 資料完整性驗證（遷移後） |
| MCM-4 | Rollback Validate | 回滾腳本驗證 |

---

## 執行流程

### 階段 1：現況分析（As-Is DB Schema 確認）

讀取現有 As-Is SRD，確認 DB 部分完整：
- 表格清單（含欄位/型別/約束/索引）
- Stored Procedure / Function / Trigger 清單
- View / Materialized View
- 資料量估算（影響遷移策略選擇）

**資料型別映射表**（依來源 DB 不同）：

| Oracle/MySQL/MSSQL 型別 | PostgreSQL 映射 | 注意事項 |
|------------------------|----------------|---------|
| NUMBER(10) | INTEGER | 精度確認 |
| VARCHAR2(N) | VARCHAR(N) | 無差異 |
| CLOB / LONGTEXT | TEXT | 大物件處理 |
| DATE（含時間）| TIMESTAMP | Oracle DATE 含時間部分 |
| ROWNUM | ROW_NUMBER() | 需改寫 |

🔴 確認點：所有平台特有語法已識別（未識別的會導致遷移失敗）。

---

### 階段 2：DB Schema Contract 設計（MCM-1 前置）

**文件路徑**：`docs/07_design/DB-SCHEMA-CONTRACT-{SystemName}.md`

```markdown
# DB Schema Contract — {SystemName}

**版本**: {N}.{N}
**來源 DB**: {Oracle/MySQL/MSSQL} → **目標 DB**: {PostgreSQL/MySQL}
**狀態**: Draft → Frozen（MCM-1 後）

## 表格定義

### {TableName}
| 欄位 | 原始型別 | 目標型別 | 約束 | 索引 | 備註 |
|------|---------|---------|------|------|------|
| {col} | {type} | {type} | NOT NULL | INDEX | {說明} |

## 不相容清單（需手動處理）
| 項目 | 問題描述 | 處理方式 |
|------|---------|---------|
| {SP_name} | Oracle 特有語法 | 改寫為 PostgreSQL 函數 |
```

執行 `/spec-compliance-check docs/07_design/DB-SCHEMA-CONTRACT-{SystemName}.md`

**MCM-1：Schema Freeze 🔴**

```
MCM-1 通過條件：
- [ ] 所有表格定義完整
- [ ] 型別映射確認無誤
- [ ] 不相容清單已完整識別
- [ ] 索引策略已確認
```

🔴 MCM-1 通過前不可開始撰寫遷移腳本。

---

### 階段 3：遷移 ADR 產出

呼叫 `/adr-generate "資料庫平台遷移策略"`：

```markdown
# ADR-{NNN}: 資料庫遷移策略

## Decision
選擇 {Big Bang / 分批遷移 / 雙寫策略} 方式

## Rationale
- Big Bang：停機遷移，適合小型 DB（< {N}GB）
- 分批：零停機，適合大型 DB，需雙寫過渡期
- 雙寫：最安全，成本最高
```

---

### 階段 4：遷移腳本撰寫

**遷移腳本結構**：

```
migrations/
├── 001_create_tables.sql         # Schema 建立
├── 002_create_indexes.sql        # 索引建立
├── 003_data_migration.sql        # 資料搬移
├── 004_stored_procedures.sql     # SP/Function 改寫
└── rollback/
    ├── rollback_003.sql          # 對應回滾腳本
    └── rollback_004.sql
```

每個腳本必須有：
- 冪等性（重複執行安全）
- 回滾腳本（對應 `rollback/` 目錄）
- 執行前/後驗證查詢

---

### 階段 5：MCM-2 遷移腳本驗證（Staging）

在 Staging 環境執行遷移，驗證：

```markdown
## MCM-2 驗證清單

- [ ] 所有遷移腳本在 Staging 執行成功（無錯誤）
- [ ] 遷移後 Schema 與 DB Schema Contract 一致
- [ ] 回滾腳本在 Staging 測試通過
- [ ] 遷移時間估算符合 SLA（停機窗口內）
```

🔴 MCM-2 未通過 → 修正腳本後重新執行，不可強行進入 Production。

---

### 階段 6：MCM-3 資料完整性驗證

```markdown
## MCM-3 資料完整性驗證

- [ ] 行數驗證：每個表格的行數與遷移前一致
- [ ] 關鍵業務資料抽樣驗證（Business Invariants）
- [ ] 外鍵約束驗證
- [ ] RTM 更新：資料遷移相關 TC 全部通過
```

---

### 階段 7：RTM 更新 🔴

```bash
/rtm-generate update   # 更新與 DB 遷移相關的 TC 狀態
/spec-compliance-check docs/07_design/DB-SCHEMA-CONTRACT-{SystemName}.md
```

🔴 確認點：MCM-3 驗證結果需 DBA 確認。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應閘門 |
|--------|------|---------|
| DB Schema Contract | `docs/07_design/DB-SCHEMA-CONTRACT-{System}.md` | MCM-1 |
| Migration ADR | `docs/02_architecture/adr/ADR-{NNN}-db-migration.md` | SCG-2 |
| Migration Scripts | `migrations/` | MCM-2 |
| Rollback Scripts | `migrations/rollback/` | MCM-4 |

---

## 後置動作

```
/rtm-generate update      # 更新 DB 遷移相關 TC
/sdd-gate SCG-4           # 遷移實作後的 PR Review
/release-management       # 遷移上線（含 MCM Validate）
```

🔷 **本 Skill 協助通過**：SCG-3（DB Schema Contract 凍結）、SCG-4（遷移實作 Review）

---

## 相關 Skill

- `/brownfield-analysis` — 提供 As-Is DB 基線（前置）
- `/adr-generate` — 遷移策略決策 ADR（在本 Skill 中呼叫）
- `/integration-database` — ORM 層整合（遷移後更新）
- `/release-management` — 遷移上線流程

---

**基於**: AISDLC-SDD v0.27
**對應場景**: `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`
**對應 CI/CD 規格**: `cicd/SDD_MIGRATION_CICD.md`
