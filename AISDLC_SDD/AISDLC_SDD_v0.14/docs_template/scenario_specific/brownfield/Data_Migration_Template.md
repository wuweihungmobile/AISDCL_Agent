# 資料遷移方案模板（Brownfield 專用）
# Data Migration Plan Template (Brownfield)

**專案名稱**: [專案名稱]
**變更描述**: [觸發資料遷移的變更]
**建立日期**: [YYYY-MM-DD]
**負責人**: [Dev-Senior / DBA]

---

## 1. 遷移概述

| 項目 | 說明 |
|------|------|
| **遷移原因** | [Schema 變更 / 資料格式調整 / 業務邏輯變更] |
| **影響資料表** | [列出受影響的表名] |
| **預估資料量** | [行數 / 資料大小] |
| **預估遷移時間** | [分鐘/小時] |
| **停機需求** | [是/否，若是需多長時間] |

---

## 2. Schema 變更清單

| # | 表名 | 變更類型 | 變更內容 | 向下相容 |
|---|------|---------|---------|---------|
| 1 | [table_name] | ADD COLUMN | `ALTER TABLE x ADD COLUMN y ...` | ✅/❌ |
| 2 | [table_name] | MODIFY COLUMN | `ALTER TABLE x ALTER COLUMN y ...` | ✅/❌ |
| 3 | [table_name] | CREATE TABLE | `CREATE TABLE ...` | ✅ |
| 4 | [table_name] | DROP COLUMN | `ALTER TABLE x DROP COLUMN y` | ❌ |

---

## 3. 遷移腳本

### 3.1 正向遷移 (Forward Migration)

```sql
-- Migration: V[版本]__[描述].sql
-- 日期: [YYYY-MM-DD]
-- 說明: [變更目的]

BEGIN;

-- Step 1: Schema 變更
ALTER TABLE [table_name] ADD COLUMN [column] [type] [constraints];

-- Step 2: 資料遷移
UPDATE [table_name] SET [new_column] = [計算邏輯] WHERE [條件];

-- Step 3: 約束新增（Schema 變更完成後）
ALTER TABLE [table_name] ADD CONSTRAINT [name] [約束定義];

COMMIT;
```

### 3.2 回滾腳本 (Rollback Migration)

```sql
-- Rollback: V[版本]__[描述]_rollback.sql
-- ⚠️ 回滾前必須先備份當前狀態

BEGIN;

-- Step 1: 移除約束
ALTER TABLE [table_name] DROP CONSTRAINT IF EXISTS [name];

-- Step 2: 資料還原（如需要）
UPDATE [table_name] SET [column] = [還原邏輯] WHERE [條件];

-- Step 3: Schema 還原
ALTER TABLE [table_name] DROP COLUMN IF EXISTS [column];

COMMIT;
```

---

## 4. 遷移前檢查清單

- [ ] 遷移腳本已在本地環境測試通過
- [ ] 回滾腳本已在本地環境測試通過
- [ ] 遷移腳本冪等性已驗證（可重複執行不出錯）
- [ ] 已確認外鍵約束和索引的影響
- [ ] 大表遷移已規劃分批策略（避免長時間鎖表）
- [ ] Staging 環境已執行完整遷移+回滾測試
- [ ] 生產環境資料備份已排程

---

## 5. 執行計畫

### 5.1 遷移步驟

| 順序 | 步驟 | 預計時間 | 確認 |
|------|------|---------|------|
| 1 | 通知相關人員進入維護窗口 | - | [ ] |
| 2 | 生產環境資料庫完整備份 | [X 分鐘] | [ ] |
| 3 | 驗證備份完整性 | [X 分鐘] | [ ] |
| 4 | 執行正向遷移腳本 | [X 分鐘] | [ ] |
| 5 | 驗證遷移結果（資料正確性） | [X 分鐘] | [ ] |
| 6 | 部署應用程式新版本 | [X 分鐘] | [ ] |
| 7 | Smoke Test 驗證 | [X 分鐘] | [ ] |
| 8 | 通知維護窗口結束 | - | [ ] |

### 5.2 回滾觸發條件

| 條件 | 行動 |
|------|------|
| 遷移腳本執行失敗 | 🔴 立即回滾 |
| 資料驗證不通過（>1% 錯誤率） | 🔴 立即回滾 |
| 應用程式無法啟動 | 🔴 回滾 Schema + 部署舊版 |
| 效能嚴重退化（>50%） | 🟡 評估後決定 |

### 5.3 多表關聯回滾注意事項

> ⚠️ 若遷移涉及多表（外鍵關聯），回滾順序必須是遷移順序的**反向**。

```
遷移順序: 父表 → 子表 → 關聯表
回滾順序: 關聯表 → 子表 → 父表
```

---

## 6. 資料驗證

### 6.1 驗證查詢

```sql
-- 驗證 1: 資料行數一致
SELECT COUNT(*) FROM [table] WHERE [遷移條件];
-- 預期結果: [N]

-- 驗證 2: 資料完整性
SELECT COUNT(*) FROM [table] WHERE [new_column] IS NULL AND [應有值條件];
-- 預期結果: 0

-- 驗證 3: 業務邏輯正確性
SELECT [關鍵欄位] FROM [table] WHERE [測試條件] LIMIT 10;
-- 預期結果: [描述預期值]
```

---

**存放目錄**: `docs/04_planning/`
**關聯文件**: 技術設計文件、影響分析報告
**適用情境**: Brownfield（Schema 變更）、Migration（資料庫遷移）
