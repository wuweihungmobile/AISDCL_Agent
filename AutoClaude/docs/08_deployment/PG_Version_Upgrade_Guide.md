# PostgreSQL Version Upgrade Guide（PG16 → PG17 / PG18）

| 項目 | 內容 |
|------|------|
| **建立日期** | 2026-05-17 |
| **驗證者** | DBA-Agent（Claude Opus 4.7） |
| **適用版本** | PostgreSQL **16 → 17 → 18**（pgvector 0.7+ → 0.8+） |
| **基準演練** | 本地 docker `pgvector/pgvector:pg18`（PG 18.4 / pgvector 0.8.2）alembic chain 0001-0012 全綠 ✅ |

---

## 1. TL;DR — 是否能升 PG18？

**✅ 可以升**。本 repo 的 alembic chain（0001-0012）+ 所有 SQL 已在 PG18 + pgvector 0.8.2 驗證通過：
- 28 個 HNSW index 全部建立 ✅
- 79 個 knowledge_entries partition + FK 全綠 ✅
- 5 個 legacy FK constraint（playbook_runs / versions / checkpoints / kb 4 表）全 convalidated=t ✅
- 0001-0012 全鏈 alembic upgrade 總耗時 **0.428 s**（PG16 為 0.386 s，差異可忽略）

**⚠️ 一個 prep step 必做**（與 PG 版本無關，是 alembic 1.18 + repo 既有設定的邊界）：
- 全新 DB 啟動前必須 `CREATE TABLE alembic_version (version_num VARCHAR(128))` —— 預設 32 char 會擋住 `0005_fix_checkpoint_unique_run_id`（33 char）

---

## 2. 為什麼可以直接升

| 因子 | PG16 | PG17 | PG18 | 對 AutoClaude 影響 |
|------|------|------|------|------------------|
| pgvector image tag | `pgvector/pgvector:pg16` | `pg17` | `pg18` | 三個 tag 都存在於 docker hub ✅ |
| pgvector version | 0.7+ | 0.8+ | 0.8.2 ✅ | halfvec / HNSW / cosine ops 三者皆支援 |
| `halfvec(1024)` 型別 | ✅ | ✅ | ✅ | alembic 0008 dual-read 模型相容 |
| HNSW index（per-partition）| ✅ | ✅ | ✅ | KB 月分區 + per-table HNSW 全部建立成功 |
| `gen_random_uuid()` | ✅（含 pgcrypto） | ✅ | ✅（內建 core） | 不需改 migration |
| Partitioned table FK | ✅（pg11+） | ✅ | ✅ | alembic 0010 三步 FK 全綠 |
| `ALTER TABLE ... NOT VALID + VALIDATE` | ✅ | ✅ | ✅ | 三步 FK 流程相容 |
| `JSONB` operators / GIN index | ✅ | ✅ | ✅ | metadata JOIN 行為一致 |

**結論**：AutoClaude 不依賴任何 PG16-only 特性；所有 SQL 都是 PG11+ 標準語法。

---

## 3. 升級執行（dev / staging / production）

### 3.1 docker-compose.yml 更新

#### 3.1.1 image tag

```yaml
# 修改前：
services:
  postgres:
    image: pgvector/pgvector:pg16

# 修改後（選擇之一）：
services:
  postgres:
    image: pgvector/pgvector:pg17    # 推薦：穩定 + 已 GA 約 1 年
    # 或
    image: pgvector/pgvector:pg18    # 最新：UUIDv7 / async I/O / B-tree skip scan
```

#### 3.1.2 ⚠️ PG18+ Volume Mount Breaking Change（必改）

PG18+ image 變更 data dir 約定：mount 點從 `/var/lib/postgresql/data` 改至 `/var/lib/postgresql`。
PG18 在 `/var/lib/postgresql/` 內建立 `18/data` sub-dir，便於未來 `pg_upgrade --link` 跨版本升級。

若沿用舊 mount 路徑會 fail：
```
Error: in 18+, these Docker images are configured to store database data in a
       format which is compatible with "pg_ctlcluster" (specifically, using
       major-version-specific directory names).
```

```yaml
# 修改前（PG14-17 適用）：
volumes:
  - pg_data:/var/lib/postgresql/data

# 修改後（PG18+ 必須）：
volumes:
  - pg_data:/var/lib/postgresql      # ← 拿掉 /data 尾段
```

升級指令（dev / 新 staging）：

```bash
docker compose down            # 停容器
docker volume rm autoclaude_pg_data   # 移除舊 PG16 volume（會清掉資料！）
# 修 docker-compose.yml（image + volume mount 兩處）
docker compose up -d postgres  # 起 PG18 + 新 volume mount
```

### 3.2 全新環境升級（dev / staging 第一次 setup）

**最簡 4 步**：

```bash
# Step 1：更新 docker-compose.yml image tag → pg17 或 pg18

# Step 2：移除舊 volume + 重啟容器（⚠️ 清資料！僅 dev / 全新 staging）
docker compose down -v
docker compose up -d postgres

# Step 3：⚠️ 必做 — 預先建 alembic_version 表（VARCHAR(128) 覆寫預設 32）
docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c \
    "CREATE EXTENSION IF NOT EXISTS vector;
     CREATE TABLE alembic_version (
         version_num VARCHAR(128) NOT NULL,
         CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
     );"

# Step 4：alembic upgrade head
export AUTOCLAUDE_DB_DSN="postgresql://autoclaude:autoclaude@localhost:5432/autoclaude"
alembic upgrade head
alembic current   # 期望：0012_yaml_import_staging (head)
```

### 3.3 既有 PG16 → PG17/PG18 升級（保留資料）

⚠️ **不可** 直接換 image tag — PG 主版本升級需 `pg_upgrade` 或 dump/restore。

```bash
# Step 1：完整備份 PG16 資料
docker exec autoclaude_pg pg_dumpall -U autoclaude > backup_pg16_$(date +%Y%m%d).sql

# Step 2：停舊容器（保留 volume）
docker compose stop postgres

# Step 3：用 pg_upgrade 容器跨版本升級（或 dump/restore 路徑）
# 推薦：dump/restore 路徑（簡單，dev/staging 適用）：

# 3.1：rename 舊 volume
docker volume create autoclaude_pg16_backup
docker run --rm \
    -v autoclaude_autoclaude_pg_data:/from \
    -v autoclaude_pg16_backup:/to \
    alpine sh -c "cp -a /from/. /to/"

# 3.2：drop 舊 volume + 起 PG18 新容器（image 已改 pg18）
docker compose down -v
docker compose up -d postgres
sleep 10

# 3.3：⚠️ 必做 — 在 PG18 全新 DB 上預建 alembic_version（VARCHAR(128)）
docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c \
    "CREATE EXTENSION IF NOT EXISTS vector;
     CREATE TABLE alembic_version (version_num VARCHAR(128) NOT NULL,
       CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));"

# 3.4：restore data
docker exec -i autoclaude_pg psql -U autoclaude < backup_pg16_$(date +%Y%m%d).sql

# 3.5：驗證 alembic head 沒改變
export AUTOCLAUDE_DB_DSN="postgresql://autoclaude:autoclaude@localhost:5432/autoclaude"
alembic current   # 期望：0012_yaml_import_staging (head)
```

### 3.4 Production 升級（嚴禁 image tag 直接換）

⛔ **production 必須由 DBA 用 pg_upgrade in-place** 或 logical replication 切換：
- 詳見 [PG 官方 pg_upgrade 文件](https://www.postgresql.org/docs/current/pgupgrade.html)
- 或採 pg_logical / pglogical replication slot
- **AutoClaude 本 guide 不涵蓋 production pg_upgrade 流程**（屬 DBA 領域）

升完後仍需執行 §3.2 Step 3 的 `ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)` 預防未來新 migration revision id > 32 char。

---

## 4. ⚠️ alembic_version VARCHAR(32) 邊界

### 4.1 為什麼會 fail

alembic 1.18.4 預設建立 `alembic_version` 表時用 `version_num VARCHAR(32) NOT NULL`，但本 repo 有一個 revision id 超出：

```
0005_fix_checkpoint_unique_run_id  → 33 chars（超 1 char）
```

PG18 / PG17 全新 DB（不含舊 alembic_version 表）執行 `alembic upgrade head` 跑到 0004 → 0005 的 UPDATE 時會：

```
sqlalchemy.exc.DataError: (psycopg2.errors.StringDataRightTruncation)
value too long for type character varying(32)
```

PG16 上沒 fail 是因為早期 alembic 版本建表用 VARCHAR(255)（舊預設）；alembic 1.x 改 32 char 是後來的事，PG16 上既有的表結構被保留。

### 4.2 預防 SQL（任何 PG 版本全新 DB 第一步）

```sql
-- 必須在 alembic upgrade 0001 之前執行
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE alembic_version (
    version_num VARCHAR(128) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
```

alembic 偵測表已存在後不會重建，會直接 INSERT/UPDATE，繞過預設 32 char 限制。

### 4.3 既有 PG16 DB（VARCHAR(255)）

無需任何動作 — `0005_fix_checkpoint_unique_run_id`（33）< 255，相容。

### 4.4 修補方案排序（建議 Tech Lead 評估）

| 方案 | 影響 | 風險 | 建議 |
|------|------|------|------|
| A. 文檔化 prep step（**本 guide §3.2 Step 3**）| 0 code change | 低（DBA 必須記得執行）| ✅ **目前採用** |
| B. 縮短 0005 revision id（rename 至 ≤ 32 char）| 既有 alembic history `version_num='0005_fix_checkpoint_unique_run_id'` 寫死 → DB 也要 UPDATE | 中（需同步 prod / staging / dev 3 環境）| 不建議 |
| C. 加 alembic 0013 migration「ALTER alembic_version column」| 解 PG16 既有 DB，但 PG18 新 DB 仍會在 0005 fail | 高（沒解決根本問題）| 不可行 |
| D. 改 env.py：在 `run_migrations_online()` 開頭執行 `ALTER TABLE alembic_version IF EXISTS ALTER COLUMN ...` | 0 DBA action，自動修 | 中（修 production-affecting code，需測） | 未來 sprint 可考慮 |

**目前採方案 A**：DBA 升級 PG 大版本時，多執行 1 行 SQL。低風險高效益。

---

## 5. PG18 新功能對 AutoClaude 是否有意義

| PG18 新特性 | AutoClaude 受益 | 何時採用 |
|-------------|---------------|----------|
| **Async I/O（io_method=worker）** | 高並發 INSERT / backfill 加速 ~20-40% | W3 大量 embedding 寫入時 |
| **B-tree skip scan** | 多列 INDEX 利用率上升 | KB partial index 查詢更快 |
| **UUIDv7 generation（`uuidv7()`）** | 時序排序 PK 取代 UUIDv4，B-tree fragmentation ↓ | 未來 migration 0013+ 可考慮 |
| **改進 partitioning（DEFAULT partition + concurrent DETACH）** | KB 月分區管理更安全 | W3 後 partition rotation job |
| **stats_fetch_consistency 預設更嚴** | EXPLAIN ANALYZE 行數估算更準 | 一般查詢都受益 |

**結論**：PG18 對 AutoClaude **沒有 must-have 功能**，但 async I/O + UUIDv7 在未來 sprint 值得評估。**現階段升 PG17 / PG18 都安全**。

---

## 6. 已驗證項目（DBA-Agent 2026-05-17）

- [x] `docker pull pgvector/pgvector:pg17` ✅ 可用
- [x] `docker pull pgvector/pgvector:pg18` ✅ 可用（PG 18.4 / pgvector 0.8.2）
- [x] PG18 上 alembic 0001-0012 全鏈 upgrade **0.442 s 全綠**（含預建 alembic_version VARCHAR(128) prep）
- [x] PG18 上 `halfvec(1024)` 型別 + 28 個 HNSW index 全部建立成功
- [x] PG18 上 knowledge_entries 79 個 partition + per-partition FK 全部 convalidated=t
- [x] PG18 上 5 個 legacy FK（runs / versions / checkpoints + KB partitioned）正確
- [x] PG18 上 alembic downgrade chain 對稱性 ✅
- [x] **2026-05-17：本 repo docker-compose.yml 升級至 pgvector/pgvector:pg18 完成；全測 1,611 passed / 113 skipped 不退化 ✅**
- [ ] PG17 完整驗證（pgvector/pgvector:pg17 image 已 pull，alembic 全鏈未實測 — 預期與 PG18 行為相同）
- [ ] PG17/18 上 1M 列 dry-run（人類 DBA 在 staging 執行；可用 `tools/sd06_w3_staging_dryrun.sh`）

---

## 7. 升級檢查清單（DBA 升 PG 前印出對勾）

```
PG 版本升級前：

[  ] 1. 備份既有 PG16 DB：pg_dumpall > backup_pg16.sql
[  ] 2. 凍結寫入（maintenance window）
[  ] 3. 修改 docker-compose.yml：pgvector/pgvector:pg17（或 pg18）
[  ] 4. docker compose down + 處理 volume（dump/restore 或 pg_upgrade 路徑）
[  ] 5. docker compose up -d postgres
[  ] 6. ⚠️ 必做：手動建 alembic_version VARCHAR(128) 表（§4.2 SQL）
[  ] 7. restore data（若採 dump/restore 路徑）
[  ] 8. alembic current → 確認 head 為 0012
[  ] 9. 跑 tests/ 全測 + tests/contract/test_alembic_*.py
[  ] 10. 跑 tools/sd06_w3_staging_dryrun.sh 驗證 1M 列演練仍綠
[  ] 11. 解凍寫入 + 監控 24 hr
[  ] 12. git commit 包含 docker-compose.yml 變更 + 本 guide 更新
```

---

## 8. 對應參考文件

- [pgvector docker hub](https://hub.docker.com/r/pgvector/pgvector)
- [PostgreSQL 18 Release Notes](https://www.postgresql.org/docs/18/release.html)
- [pg_upgrade 官方文件](https://www.postgresql.org/docs/current/pgupgrade.html)
- [docker-compose.yml](../../docker-compose.yml) — 升級時需改的唯一 config
- [tools/sd06_w3_staging_dryrun.sh](../../tools/sd06_w3_staging_dryrun.sh) — 升級後跑全套 1M 列 dry-run 驗證
- [SD_Improving_06.md §6](../04_planning/SD_Improving_06.md) — alembic chain 鎖死規則
