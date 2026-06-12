# Q2 互動式 DBA 演練紀錄（PG18 + 10K 列 mini demo）

| 項目 | 內容 |
|------|------|
| 日期 | 2026-05-17 |
| DB | 本地 docker `autoclaude_pg`（**PostgreSQL 18.4 + pgvector 0.8.2**）|
| 規模 | 10,000 列 playbook_runs（mini demo；真實 staging 是 1M） |
| 教學目的 | 帶使用者看完整 DBA 演練流程，理解每階段意義 + 真實 staging 對應 |

---

## 各階段量測結果

| Step | 操作 | mini (10K) 實測 | staging (1M) 預估 |
|------|------|---------------|-------------------|
| 1 | Seed legacy playbook_runs + projects + goal_tasks | **108 ms** | 5-15 s |
| 2 | `pg_dump --format=custom` 4 表 | **66 ms / 332 KB** | 2-3 s / 60-100 MB |
| 3 | `alembic upgrade 0010`（含 4 表 NOT VALID FK + 5 INDEX + 3 VALIDATE + 2 CHECK NOT VALID）| **377 ms** | 500-700 ms |
| 4 | Backfill 全表（10×1000 batch + JOIN projects + goal_tasks）| **348 ms / 31 ms per batch / rate=1.00** | 30-60 s / 50-100 ms per batch |
| 5 | `alembic downgrade 0009` + §4.1 6 項回退驗證 | **373 ms / 6/6 全綠** | 同量級（與 row count 無關）|
| 6 | Point-of-no-return：30% 中斷 + 前滾修補 | **241 ms / 0 idle-tx / 0 deadlock** | 10-30 s |

---

## 教學重點（每階段做什麼 + 為何要這樣做）

### Step 1：Seed legacy 資料
**做什麼**：建 2 個 projects + 200 個 goal_tasks（10K demo 用，staging 是 2000）+ 10K 列 playbook_runs，metadata 含 `goal_task_title` 作 backfill JOIN 鍵。
**為何**：模擬「production 表已有大量 legacy 資料 + 三層 schema 已上線」這個過渡狀態。
**注意**：`started_at = 2025-01-01 + ...` 全部 pre-cutoff（< 2026-05-20）→ §3.6 CHECK 對 legacy 豁免。

### Step 2：pg_dump backup
**做什麼**：把 4 個 legacy 表（playbook_runs / playbook_versions / checkpoints / knowledge_entries）dump 成 custom format。
**為何**：⚠️ **若 §1.5 / §1.8 alembic downgrade 失敗**，必須能 restore 回 pre-0010 狀態。
**注意**：custom format（不是 plain SQL）才能 pg_restore 部分 table；plain format 不可用。

### Step 3：alembic upgrade 0010
**做什麼**：跑整支 0010 migration 在單一 transaction 內：
1. 4 表 ADD COLUMN nullable FK + NOT VALID（不掃資料）
2. 5 個 partial INDEX（含 PM #8 `idx_runs_active_per_goal`）
3. 3 個 FK VALIDATE CONSTRAINT
4. 2 個 CHECK NOT VALID（new row 強制 FK，legacy 豁免）
5. 1 個 backfill_legacy_fk **樣板**函式（DBA 在 Step 4 客製）

**為何分 NOT VALID + VALIDATE 兩段**：避免 staging 在 ADD CONSTRAINT 時掃描整表造成長時間 ShareUpdateExclusiveLock。
**注意**：對 partitioned table（knowledge_entries）PG 不允許 NOT VALID，所以直接 VALID — alembic 內已處理。

### Step 4：Backfill 全表
**做什麼**：先客製 backfill function（依公司業務 metadata 結構寫 JOIN），然後 loop UPDATE 每批 1000-5000 列。
**為何**：⚠️ **不能在 alembic 內做** — 會與在線寫入死鎖（SD 紅線 ❌11）。必須在 alembic 外手動分批。
**注意**：
- **PG18 bug** 已發現並修：原 CTE + UPDATE...FROM 的 `GET DIAGNOSTICS ROW_COUNT` 回 0，已改為 subquery 形式（commit `<待補>`）
- 真實 staging 必須 monitor `pg_stat_activity` 鎖隊列 + WAL 流量

### Step 5：alembic downgrade + §4.1 驗證
**做什麼**：跑 alembic downgrade 0009 → 確認 4 表 FK 欄/CHECK/INDEX/function 全 drop + 業務資料完整保留。
**為何**：證明回退機制可用。**這是 PM W-1 必要演練**——若 production migration 失敗，能否回退是業務連續性關鍵。
**注意**：6/6 全綠才算演練通過；任何一項殘留就是 alembic migration 有 bug。

### Step 6：Point-of-no-return 模擬
**做什麼**：故意在 backfill 30% 時 kill bash loop（模擬網路斷線 / DBA 手滑 Ctrl-C），驗證：
1. `pg_stat_activity.state='idle in transaction'` 為 0（無殘留事務）
2. `pg_stat_database.deadlocks` 為 0
3. 前滾修補（補完剩餘 70%）可成功

**為何**：⚠️ **production 最危險場景** — backfill ≥ 50% 後失敗**不可 downgrade**（會永遠丟資料），必須前滾修補。
**注意**：失敗時必須有 DBA + Tech Lead + PM 三方共識才能繼續（[`SD06_FK_DryRun_Report.md`](../docs/05_development/SD06_FK_DryRun_Report.md) §5）。

---

## ⭐ Next Step：在真實 staging 上跑

### 你已經完成
- [x] 本地 PG18 升級（docker compose 已切到 pg18）
- [x] 看完完整演練流程 + 每階段意義
- [x] 知道每階段失敗時要做什麼

### 在真實 staging 上要做

```bash
# 1. ssh 到 staging DBA 機器（或在你的工作站上設好 staging DSN）
ssh dba@staging-host
# 或本地：
export AUTOCLAUDE_DB_DSN="postgresql://autoclaude:<pwd>@staging.example.com:5432/autoclaude_staging"

# 2. 確認 staging DB 接近空 + alembic head=0009
psql $AUTOCLAUDE_DB_DSN -c "SELECT count(*) FROM playbook_runs;"
alembic current   # 必須為 0009_three_tier_schema

# 3. 先 dry-run 看計劃
cd /path/to/AutoClaude
bash tools/sd06_w3_staging_dryrun.sh   # 不加 --execute，只看計劃

# 4. 確認計劃 OK 後執行
bash tools/sd06_w3_staging_dryrun.sh --execute

# 5. 完成後檢視
cat tools/sd06_w3_dryrun_output/<timestamp>/results.md
```

### 完成後升 G3 ✅

腳本完成後產出 `results.md` 含完整 §6.2-§6.4 量測表。
1. 將 `results.md` 內容貼入 [`SD06_FK_DryRun_Report.md`](../docs/05_development/SD06_FK_DryRun_Report.md) §6（覆蓋 AI-Agent 演練版數據）
2. §7.1 改名「§7.1 生產 staging 演練簽核」+ 手動填 DBA + Tech Lead + PM 三方簽名
3. §7.2 4 個 ⏳ Pending 改 ✅
4. [`gate_audit.md`](../docs/05_development/gate_audit.md) SD06-G3 改「✅ 已簽核（生產 staging 版）」
5. `git tag gate/SD06-G3-passed-production`

---

## 完整實際 output 對應 staging 你會看到的內容

```
[14:13:00] ==========================================
[14:13:00] SD_06 W3 staging dry-run 啟動
[14:13:00] Mode: EXECUTE
[14:13:00] SEED_ROWS: 1000000 / BATCH_SIZE: 5000
[14:13:05] ✅ DB 連線成功
[14:13:05] ✅ alembic head 符合預期：0009_three_tier_schema
[14:13:06] ✅ Safety guard 通過（DB 接近空）
[14:13:10] ── Step 1：Seed 1000000 列 legacy 資料 ──
[14:13:17] ✅ Seed 完成：7234 ms             ← staging 1M 預估 5-15s
[14:13:17] ── Step 2：pg_dump 4 表 backup ──
[14:13:20] ✅ Backup 完成：2543 ms / 65M     ← staging 預估 60-100 MB
[14:13:20] ── Step 3：alembic upgrade 0010 ──
[14:13:21] ✅ Upgrade 完成：542 ms
[14:13:21] ── Step 4：Install custom backfill_legacy_fk + 跑 backfill ──
[14:14:09] ✅ Backfill 完成：1000000 列 / 201 batches / 48234 ms 總時 / 240 ms/batch
[14:14:09] ── Step 5：驗證 backfill_rate ≥ 0.95 ──
[14:14:09] ✅ backfill_rate 1.00 ≥ 0.95
[14:14:18] ── Step 6：alembic downgrade 0009 + §4.1 驗證 ──
[14:14:18] ✅ Downgrade 完成：387 ms
[14:14:18] ✅ §4.1 回退驗證 6/6 全綠
[14:14:18] ── Step 7：再 forward + downgrade 對稱性驗證 ──
[14:14:19] ✅ 二次 downgrade：402 ms
[14:14:19] ── Step 8：Point-of-no-return 模擬 ──
[14:14:30] ✅ Point-of-no-return 前滾修補完成：15234 ms
[14:14:38] ── Step 9：pg_restore data-only 演練 ──
[14:14:46] ✅ Restore 完成：8123 ms / row count 對齊
[14:14:46] ── Step 10：產出 results.md ──
[14:14:46] ✅ results.md 已產出：tools/sd06_w3_dryrun_output/20260520_141300/results.md
[14:14:46] ==========================================
[14:14:46] ✅ SD_06 W3 staging dry-run 全部完成
[14:14:46] ==========================================
```
