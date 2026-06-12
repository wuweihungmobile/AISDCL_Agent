# Phase 6 PostgreSQL Backend Activation — Stakeholder Sign-off

**簽核日期**：2026-05-08
**對應 Spec**：[SD_Improving_02.md](../04_planning/SD_Improving_02.md) v1.1 §2.8
**測試基線**：927 passed / 11 skipped（含 +18 storage 開關測試）

---

## 三段開關設計（已實作）

| 模式 | 行為 | 適用情境 |
|------|------|----------|
| `yaml_only`（預設） | 純 File backend；零 PG 依賴 | 開發 / 單機 / v1.x 相容 |
| `both` | File 主寫 + PG 影子寫；File 主讀，PG 災難回復 | PG 上線首兩週灰度驗證 |
| `db_only` | 純 PG backend；yaml 僅供匯入 | Production 穩定後 |

設定位置：[autoclaude/utils/config.py](../../autoclaude/utils/config.py) `StorageConfig`

DSN 解析優先級：環境變數 `AUTOCLAUDE_DB_DSN` > `AUTOCLAUDE_PG_DSN`（deprecation）> `config.storage.db_dsn`

---

## 四方審查結論

| Stakeholder | Verdict | 主要 Findings | 必修 P0 已落實 |
|-------------|---------|---------------|----------------|
| **DBA** | APPROVE WITH CONDITIONS | UPSERT saved_at / asyncio.run / pool / load_checkpoint silent fail / UTC | ✅ 6/8（asyncio.run 與 GIN index 列為 P1） |
| **Infra** | APPROVE WITH CONDITIONS | DSN 環境變數不一致 / alembic.ini 預設 fallback / engine lifecycle / startup smoke test | ✅ 4/7（docker-compose 列為 P1） |
| **SRE** | APPROVE WITH CONDITIONS | silent except / 缺 retry / pool 配置 / 缺 metrics | ✅ 3/5（retry / metrics 列為 P1） |
| **Security** | APPROVE WITH CONDITIONS | TLS 缺強制 / DSN 洩漏風險 / alembic.ini 明文 / docstring 明文密碼 | ✅ 5/8（最小權限文件 / redaction hook 列為 P1） |

---

## P0 已落實（合併前必修，本 commit 完成）

| # | 項目 | 採納方 | 對應檔案 |
|---|------|--------|----------|
| 1 | DSN 環境變數統一為 `AUTOCLAUDE_DB_DSN` | Infra / Security | [factory.py](../../autoclaude/infra/repositories/factory.py)、[alembic/env.py](../../alembic/env.py)、[migrate_file_to_pg.py](../../scripts/migrate_file_to_pg.py) |
| 2 | alembic.ini 移除明文 DSN fallback | Infra / Security | [alembic.ini:1-5](../../alembic.ini) |
| 3 | env.py 缺 DSN 時 fail-loud | Infra | [alembic/env.py:31-39](../../alembic/env.py) |
| 4 | UPSERT `saved_at = func.now()` | DBA | [pg_state_repository.py:120](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 5 | `schedule_resume` 改用 `datetime.now(timezone.utc)` | DBA | [pg_state_repository.py:84](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 6 | load/clear/list 例外分流：OperationalError 降級、ProgrammingError 上拋 | DBA / SRE / Infra | [pg_state_repository.py:55-93](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 7 | `create_async_engine` 補 `pool_pre_ping=True, pool_recycle=300, pool_size=5, max_overflow=10` | DBA / Infra / SRE | [factory.py:80-87](../../autoclaude/infra/repositories/factory.py) |
| 8 | TLS 強制檢查（`sslmode=require` 必要，可被 `AUTOCLAUDE_ALLOW_INSECURE_DB=1` override） | Security | [factory.py:54-69](../../autoclaude/infra/repositories/factory.py) |
| 9 | DSN sanitization：所有例外訊息經 `_redact()` 移除密碼 | Security | [pg_state_repository.py:44-49](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 10 | docstring 範例移除明文密碼，改用 `${PG_USER}:${PG_PASS}` | Security | [pg_state_repository.py:5-10](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 11 | `PgStateRepository.close()` 暴露 engine.dispose() | Infra | [pg_state_repository.py:95-100](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 12 | DualStateRepository fail_loud / yaml_wins / db_wins 三策略 | SRE | [dual_state_repository.py](../../autoclaude/infra/repositories/dual_state_repository.py) |

---

## P1 後續優化（✅ 全部完成 2026-05-15）

| # | 項目 | 採納方 | 完成狀態 | 對應檔案 |
|---|------|--------|---------|---------|
| 1 | **docker-compose.yml**（postgres:17 + healthcheck） | Infra | ✅ 完成（2026-05-12） | [docker-compose.yml](../../docker-compose.yml) |
| 2 | **CI workflow PG service container**（pg-contract job） | Infra | ✅ 完成（2026-05-12） | [.github/workflows/ci.yml:63](../../.github/workflows/ci.yml) |
| 3 | **PG 連線 startup smoke test**（SELECT 1 + alembic head） | Infra | ✅ 完成（2026-05-12） | [factory.py:127-157](../../autoclaude/infra/repositories/factory.py) |
| 4 | **PG 操作 retry 裝飾器**（tenacity max 3 backoff） | SRE | ✅ 完成（2026-05-12） | [pg_state_repository.py:102-115](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 5 | **metrics hook**（dual-write success rate / drift counter） | SRE | ✅ 完成（2026-05-12） | [dual_state_repository.py](../../autoclaude/infra/repositories/dual_state_repository.py) |
| 6 | **PG 最小權限文件**（runtime / migrate 兩組 GRANT 範本） | Security | ✅ 完成（2026-05-14） | [PG_Role_Setup.md](PG_Role_Setup.md) |
| 7 | **`last_correction_prompt` redaction**（Bearer / API key scrub） | Security | ✅ 完成（2026-05-12） | [pg_state_repository.py:68-82](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 8 | **asyncio.run() running event loop 相容**（ThreadPoolExecutor 包裝） | DBA | ✅ 完成（2026-05-12） | [factory.py:115-124](../../autoclaude/infra/repositories/factory.py) + [pg_state_repository.py:85-99](../../autoclaude/infra/repositories/pg_state_repository.py) |
| 9 | **`migrate_file_to_pg.py`**（--skip-existing + KB 遷移 + batch） | DBA | ✅ 完成（2026-05-12） | [scripts/migrate_file_to_pg.py](../../scripts/migrate_file_to_pg.py) |
| 10 | **JSONB GIN index**（counters + failure_history） | DBA | ✅ 完成（2026-05-12）— migration 0003 | [alembic/versions/0003_optional_jsonb_gin_index.py](../../alembic/versions/0003_optional_jsonb_gin_index.py) |

**R-P6-03 關閉（2026-05-15）**：四方安全審查殘餘 10 個 P0 項目全部實作完成並驗證。

---

## 灰度上線 Runbook（建議流程）

```bash
# Phase A：開發 / staging（yaml_only，零 PG 依賴）
storage.mode = "yaml_only"

# Phase B：staging 雙寫驗證（兩週）
export AUTOCLAUDE_DB_DSN="postgresql+asyncpg://${PG_USER}:${PG_PASS}@host/db?sslmode=require"
alembic upgrade head
storage.mode = "both"
storage.dual_write_strict = false  # 容忍 PG 故障，仍以 File 為準
storage.dual_read_resolution = "yaml_wins"

# Phase C：staging 嚴格雙寫驗證（24h）
storage.dual_write_strict = true   # 任一端寫入失敗即 raise
storage.dual_read_resolution = "fail_loud"  # drift 即 raise

# Phase D：production 切換 db_only（需 P1 #1-#5 全到位）
storage.mode = "db_only"
```

---

## 簽核確認

✅ **DBA** — APPROVE WITH CONDITIONS（P0 6/8 已落實，P1 列管）
✅ **Infra** — APPROVE WITH CONDITIONS（P0 4/7 已落實，P1 列管）
✅ **SRE** — APPROVE WITH CONDITIONS（P0 3/5 已落實，P1 列管）
✅ **Security** — APPROVE WITH CONDITIONS（P0 5/8 已落實，P1 列管）

**Phase 6 PostgreSQL backend 啟用條件**：✅ 條件式核准。
- `yaml_only` 模式：✅ 立即可用（已 default、零變更風險）
- `both` 模式：✅ 立即可用於 staging（含 TLS 強制、DSN sanitization、pool 配置、災難回復）
- `db_only` 模式：⚠️ 需完成 P1 #1-#5（CI / smoke test / retry / metrics / docker-compose）方可進 production

---

**文檔元數據**：
- 撰寫者：Phase 6 stakeholder review board
- 簽核日期：2026-05-08
- P1 全部完成：2026-05-15（R-P6-03 關閉）
- 下次審查觸發：Stakeholder C4（正式生產 workload 上線前重新提交四方無條件 APPROVE）
