# Alembic Seed Data 腳本（W4-T15 m-9）

本目錄存放 PostgreSQL 後端的 **示範性 seed 資料 SQL 腳本**，僅供 staging /
demo 環境快速建立測試資料使用，**不可在 production 環境直接執行**。

## 設計原則

1. **不自動執行**：alembic upgrade head 不會觸發此處 SQL。
2. **冪等性**：所有 INSERT 都應使用 `ON CONFLICT DO NOTHING` 或先 `DELETE`，
   方便反覆執行而不破壞既有資料。
3. **顯式呼叫**：開發者需手動執行 `psql -f alembic/seeds/00_initial_data.sql`。
4. **不含敏感資料**：seed 資料僅作示範，不得包含真實 API key / DSN / token。

## 檔案清單

| 檔案 | 用途 | 執行時機 |
|------|------|----------|
| `00_initial_data.sql` | 示範 `playbook_runs` + `checkpoints` + `knowledge_entries` 基線資料 | staging 建立後 |

## 使用範例

```bash
# 確認 schema 已建立（執行 alembic upgrade head 後）
psql "$AUTOCLAUDE_DB_DSN" -c "\dt"

# 載入 seed
psql "$AUTOCLAUDE_DB_DSN" -f alembic/seeds/00_initial_data.sql

# 確認
psql "$AUTOCLAUDE_DB_DSN" -c "SELECT count(*) FROM playbook_runs;"
```

## 與 alembic versions/ 的差異

- `alembic/versions/*.sql`：DDL（schema 變更），由 alembic 框架追蹤版本。
- `alembic/seeds/*.sql`：DML（資料插入），不入版本鏈、不自動執行。

## 後續計畫（SD_Improving_05）

- 提供 `pyproject.toml` script entrypoint `autoclaude-seed` 包裝執行流程。
- 加入 demo playbook fixtures（與 `tests/fixtures/mock_playbook.yaml` 對應）。
