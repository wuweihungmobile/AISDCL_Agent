---
name: database-migration
description: 資料庫平台遷移規劃與執行，支援 Oracle/MySQL/MSSQL → PostgreSQL/MySQL 等遷移
user-invocable: true
disable-model-invocation: false
argument-hint: "<source-db: Oracle/MySQL/MSSQL> <target-db: PostgreSQL/MySQL>"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Database Migration 資料庫遷移

規劃並執行資料庫平台遷移，包含 Schema 轉換、SQL 語法改寫、Stored Procedure 遷移、資料搬移與驗證。

---

## 觸發方式

```bash
/database-migration Oracle PostgreSQL
/database-migration MySQL PostgreSQL
/database-migration MSSQL PostgreSQL
```

---

## 執行流程

### 階段 1: 現況分析 🔴

**必要資訊**:
- [ ] 來源資料庫類型與版本
- [ ] 目標資料庫類型與版本
- [ ] Schema DDL 匯出檔案（或存取權限）
- [ ] 資料量估算（表數量、總行數、總大小）

**分析項目**:
- [ ] 表/欄位/約束/索引清單
- [ ] Stored Procedure / Function / Trigger 清單
- [ ] View / Materialized View 清單
- [ ] Sequence / 自增機制
- [ ] 平台特有功能使用清單
- [ ] 資料型別映射表

🔴 **確認點**: 現況分析結果是否完整，是否有遺漏的平台特有功能

---

### 階段 2: Schema 轉換

**資料型別映射**（以 Oracle → PostgreSQL 為例）:

```sql
-- Oracle → PostgreSQL 常見型別映射
NUMBER(p,s)    → NUMERIC(p,s)
VARCHAR2(n)    → VARCHAR(n)
CHAR(n)        → CHAR(n)
CLOB           → TEXT
BLOB           → BYTEA
DATE           → TIMESTAMP    -- Oracle DATE 含時間部分
LONG           → TEXT
RAW(n)         → BYTEA
FLOAT          → DOUBLE PRECISION
INTEGER        → INTEGER
```

**約束與索引轉換**:
```sql
-- Oracle 語法 → PostgreSQL 語法
CREATE SEQUENCE seq_name START WITH 1 INCREMENT BY 1;  -- 相同
-- Oracle PARTITION → PostgreSQL PARTITION (語法略有差異)
-- Oracle BITMAP INDEX → PostgreSQL 不支援，改用 GIN INDEX
```

---

### 階段 3: SQL 語法轉換

**常見轉換對照表**:

| Oracle | PostgreSQL | 說明 |
|--------|-----------|------|
| `NVL(a, b)` | `COALESCE(a, b)` | 空值替代 |
| `DECODE(a,b,c,d)` | `CASE WHEN a=b THEN c ELSE d END` | 條件判斷 |
| `ROWNUM <= n` | `LIMIT n` | 限制行數 |
| `SYSDATE` | `NOW()` / `CURRENT_TIMESTAMP` | 當前時間 |
| `TO_DATE('...','YYYY-MM-DD')` | `TO_DATE('...','YYYY-MM-DD')` | 相同 |
| `TO_CHAR(date,'YYYY')` | `TO_CHAR(date,'YYYY')` | 相同 |
| `(+)` | `LEFT JOIN` / `RIGHT JOIN` | 外連接 |
| `CONNECT BY PRIOR` | `WITH RECURSIVE` | 遞迴查詢 |
| `SELECT ... FROM DUAL` | `SELECT ...` | 不需 DUAL |
| `SUBSTR(s,p,l)` | `SUBSTRING(s FROM p FOR l)` | 子字串 |
| `INSTR(s,sub)` | `POSITION(sub IN s)` | 搜尋位置 |
| `||` | `||` | 字串串接(相同) |

---

### 階段 4: Stored Procedure 遷移

**遷移策略決策**:

```
SP 是否包含業務邏輯？
├─ 是 → 遷移至應用層 (Java Service / Python Service)
│       ✅ 可測試、可維護、與 DB 解耦
└─ 否 → 純資料處理
        ├─ 邏輯簡單？ → 轉為 PL/pgSQL
        └─ 不再需要？ → 移除
```

**PL/SQL → PL/pgSQL 語法差異**:
```sql
-- PL/SQL
CREATE OR REPLACE PROCEDURE proc_name(p_id IN NUMBER) AS
  v_name VARCHAR2(100);
BEGIN
  SELECT name INTO v_name FROM users WHERE id = p_id;
  DBMS_OUTPUT.PUT_LINE(v_name);
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    DBMS_OUTPUT.PUT_LINE('Not found');
END;

-- PL/pgSQL
CREATE OR REPLACE FUNCTION proc_name(p_id INTEGER)
RETURNS VOID AS $$
DECLARE
  v_name VARCHAR(100);
BEGIN
  SELECT name INTO v_name FROM users WHERE id = p_id;
  RAISE NOTICE '%', v_name;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE NOTICE 'Not found';
END;
$$ LANGUAGE plpgsql;
```

---

### 階段 5: 資料遷移與驗證

**遷移步驟**:
1. 建立目標 Schema (DDL)
2. 遷移靜態資料（主檔/參數檔）
3. 遷移動態資料（交易資料）
4. 建立索引與約束
5. 驗證資料完整性

**驗證清單**:
- [ ] 逐表行數比對
- [ ] 主鍵完整性（無重複、無缺失）
- [ ] 外鍵參照完整性
- [ ] 金額欄位加總比對
- [ ] 日期欄位精度驗證
- [ ] NULL 值一致性
- [ ] 抽樣明細比對（隨機 100 筆）

**推薦工具**:
- **ora2pg**: Oracle → PostgreSQL 專用遷移工具
- **pgloader**: 多源 → PostgreSQL 載入工具
- **AWS DMS**: 雲端資料庫遷移服務
- **Flyway / Liquibase**: Schema 版本管理

---

## 常見陷阱

| 問題 | 解決方案 |
|------|---------|
| Oracle DATE 含時間，PostgreSQL DATE 不含 | 使用 TIMESTAMP 替代 DATE |
| Oracle 空字串等同 NULL | PostgreSQL 空字串 ≠ NULL，需檢查相關邏輯 |
| Oracle SEQUENCE 值不連續 | PostgreSQL SERIAL 也不保證連續，行為一致 |
| Oracle 大小寫不敏感 | PostgreSQL 預設大小寫敏感，需加 LOWER() 或 citext |
| PL/SQL PACKAGE 無對應 | 改用 PostgreSQL Schema 或應用層 Service 分組 |

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| 資料型別映射表 | `docs/02_architecture/DB_Type_Mapping.md` |
| SQL 語法轉換對照表 | `docs/02_architecture/SQL_Syntax_Conversion.md` |
| SP 遷移計畫 | `docs/02_architecture/SP_Migration_Plan.md` |
| 資料遷移驗證報告 | `docs/03_testing/DB_Migration_Verification.md` |

---

## 相關 Skill

- `/integration-database` - 資料庫整合服務設定
- `/sd-architect` - 架構設計（含資料層）
- `/testing-strategy` - 測試策略（含資料驗證）

---

## 相關檔案

- SOP 參考: `scenarios/migration/SOP.md`
- QuickRef: `scenarios/migration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Migration 情境
