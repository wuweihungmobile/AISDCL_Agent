# PG_Role_Setup.md — PostgreSQL 最小權限配置指南

**對應**：Phase 6 P1 #6（Security review 要求）
**最後更新**：2026-05-15（R-P6-02 密碼輪換完成；R-P6-01 sslmode=require 啟用）

---

## 1. 角色設計原則

遵循最小權限原則（Principle of Least Privilege）：

| 角色 | 用途 | 建立時機 |
|------|------|----------|
| `autoclaude_migrate` | 執行 alembic migration（DDL 權限） | 初始化 / CI 部署 |
| `autoclaude_runtime` | AutoClaude 應用程式執行時讀寫 | 應用程式啟動 |

---

## 2. Migration 角色（`autoclaude_migrate`）

需要 DDL 權限，**僅限 CI/CD pipeline 使用，禁止放入應用程式 DSN**。

```sql
-- 建立 migration 專用角色（一次性）
CREATE ROLE autoclaude_migrate WITH LOGIN PASSWORD 'CHANGE_ME_MIGRATE';

-- 賦予 schema 使用權 + DDL 權限
GRANT CONNECT ON DATABASE autoclaude TO autoclaude_migrate;
GRANT USAGE, CREATE ON SCHEMA public TO autoclaude_migrate;

-- alembic 版本追蹤表（全 CRUD）
GRANT ALL PRIVILEGES ON TABLE alembic_version TO autoclaude_migrate;

-- 序列（serial / uuid_generate_v4 等）
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO autoclaude_migrate;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO autoclaude_migrate;
```

---

## 3. Runtime 角色（`autoclaude_runtime`）

**狀態**：✅ 已建立（2026-05-14）；✅ 密碼輪換完成（2026-05-15，R-P6-02）

**僅** SELECT / INSERT / UPDATE / DELETE，無 DDL 權限。
此角色對應環境變數 `AUTOCLAUDE_DB_DSN`。

```sql
-- 建立 runtime 專用角色（一次性）
-- 密碼請使用強密碼（≥20 字元）；實際密碼存於 config.local.yaml（gitignored，不提交）
-- 輪換方式：ALTER ROLE autoclaude_runtime PASSWORD '${NEW_STRONG_PASS}';
CREATE ROLE autoclaude_runtime WITH LOGIN PASSWORD '${STRONG_RUNTIME_PASS}';

-- 基本連線權（DB 名稱：aisdlc）
GRANT CONNECT ON DATABASE aisdlc TO autoclaude_runtime;
GRANT USAGE ON SCHEMA public TO autoclaude_runtime;

-- 資料表讀寫（執行 alembic migration 後執行）
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE playbook_runs     TO autoclaude_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE checkpoints       TO autoclaude_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE knowledge_entries TO autoclaude_runtime;

-- 序列（UUID 主鍵自動產生）
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO autoclaude_runtime;

-- 明確拒絕 DDL（防止意外建表/改表）
REVOKE CREATE ON SCHEMA public FROM autoclaude_runtime;
```

**DSN（應用程式使用）**：
```
postgresql://autoclaude_runtime:${STRONG_RUNTIME_PASS}@192.168.1.133/aisdlc?sslmode=require
```
密碼存於 `config.local.yaml`（gitignored）。R-P6-01（2026-05-15）起正式啟用 sslmode=require。

---

## 4. DSN 設定對照

| 環境 | 角色 | 環境變數 |
|------|------|---------|
| CI migration job | `autoclaude_migrate` | `AUTOCLAUDE_MIGRATE_DSN` |
| 應用程式（both / db_only） | `autoclaude_runtime` | `AUTOCLAUDE_DB_DSN` |

`.github/workflows/autoclaude-ci.yml` pg-contract job 範例（已實作，見 `.github/workflows/autoclaude-ci.yml`）：
```yaml
env:
  AUTOCLAUDE_DB_DSN: postgresql+asyncpg://autoclaude_runtime:...@localhost/autoclaude?sslmode=require
```

---

## 5. 驗證腳本

```sql
-- 確認 runtime 角色無 DDL 權限
\dp playbook_runs
\dp checkpoints

-- 測試 runtime 無法 DROP TABLE
SET ROLE autoclaude_runtime;
DROP TABLE checkpoints;  -- 應拋 ERROR: permission denied
RESET ROLE;
```

---

## 6. 金鑰輪換（R-P6-02 已完成 2026-05-15）

輪換步驟：
1. 產生強密碼（≥20 字元，僅含 URL-safe 字元：`[A-Za-z0-9\-_]`）
2. 在 DB 主機執行：`ALTER ROLE autoclaude_runtime PASSWORD '新強密碼';`
3. 更新 `config.local.yaml`（gitignored）中的 db_dsn 密碼欄位
4. 重啟 AutoClaude 服務（factory.py startup smoke test 會立即驗證連線）
5. 通知 Security 確認 P0 解除（R-P6-02 關閉）

---

**文檔元數據**：
- 撰寫者：Phase 6 P1 #6 Security review
- 審查：Security（P1 #6 採納方）
