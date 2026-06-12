# `sd06_w3_staging_dryrun.sh` — PM W-1 staging dry-run 自動化腳本

| 項目 | 內容 |
|------|------|
| **用途** | 一行命令完成 SD_06 W3 G3 升「✅ 已簽核（生產 staging 版）」所需的 1M 列 FK staging dry-run |
| **目標使用者** | 人類 DBA（在公司 staging DB 上執行） |
| **配套** | [SD06_FK_DryRun_Report.md](../docs/05_development/SD06_FK_DryRun_Report.md) §1~§5 / [SD06_W3_DBA_Handover.md](../docs/05_development/SD06_W3_DBA_Handover.md) |
| **預估耗時** | 5-30 分鐘（依 staging DB 性能） |

---

## 1. 前置條件

DBA 機器需有：

- [x] `psql` / `alembic` / `pg_dump` / `pg_restore` / `python3` 在 `$PATH`
- [x] 可連線至 staging DB（建議獨立帳號 + 讀寫權）
- [x] staging DB **alembic head = `0009_three_tier_schema`**（不是 0010+；若已 forward 須先 downgrade）
- [x] staging DB 4 個 legacy 表（`playbook_runs` / `playbook_versions` / `checkpoints` / `knowledge_entries`）**接近空**（< 100 列；腳本內建 Safety guard 防汙染 production）
- [x] staging 環境**確認不是 production**！（腳本不會檢查 DSN 字串，是 DBA 責任）
- [x] AutoClaude repo 已 clone 並 `pip install` 完成（含 `alembic`、`psycopg2-binary`）

---

## 2. 5 分鐘快速啟動

```bash
# 1. 設定 staging DSN（必須）
export AUTOCLAUDE_DB_DSN="postgresql://autoclaude:<password>@staging.example.com:5432/autoclaude_staging"
export AUTOCLAUDE_ALLOW_INSECURE_DB=1   # 若 staging 不用 TLS

# 2. 先跑 dry-run 模式（不動 DB，只印出計劃）
bash tools/sd06_w3_staging_dryrun.sh

# 3. 確認計劃 OK + DB 接近空後，加 --execute 真實執行
bash tools/sd06_w3_staging_dryrun.sh --execute
```

執行完畢會在 `tools/sd06_w3_dryrun_output/<timestamp>/` 產出：

```
sd06_w3_dryrun_output/20260601_140000/
├── main.log                          # 主 log（彩色）
├── seed.log                          # Step 1 seed 紀錄
├── backup_pre_0010_20260601_*.dump   # Step 2 backup（custom format）
├── upgrade.log                       # Step 3 alembic upgrade
├── backfill.log                      # Step 4 backfill 細節
├── downgrade.log                     # Step 6 alembic downgrade + §4.1 驗證
├── restore.log                       # Step 9 pg_restore
└── results.md                        # ⭐ 量測結果（直接貼入 SD06_FK_DryRun_Report.md §6）
```

---

## 3. 環境變數調整

| 變數 | 預設 | 說明 |
|------|------|------|
| `AUTOCLAUDE_DB_DSN` | （必填） | staging DSN（`postgresql://user:pass@host:port/db`，支援 `+asyncpg` 後綴）|
| `SEED_ROWS` | `1000000` | seed playbook_runs 列數；測試可降為 `10000` 加速 |
| `BATCH_SIZE` | `5000` | backfill per-batch 列數；網路慢時降為 `1000` |
| `SKIP_POINT_OF_NO_RETURN` | `0` | 設為 `1` 跳過 Step 8 中斷模擬（不建議；§5 強制要求）|

範例：staging 容量緊張 → 用 100K 列快測：

```bash
SEED_ROWS=100000 BATCH_SIZE=2000 \
    bash tools/sd06_w3_staging_dryrun.sh --execute
```

---

## 4. 內建 Safety Guards（不可繞過）

| Guard | 觸發條件 | 行為 |
|-------|---------|------|
| psql/alembic/pg_dump/pg_restore 缺失 | 任一 binary 不在 `$PATH` | 退出 code 1 |
| DSN 未設 | `AUTOCLAUDE_DB_DSN` 為空 | 退出 code 1 |
| alembic head 不對 | `alembic current` 非 `0009_three_tier_schema` | 退出 code 1 |
| **Production 汙染防護** | 4 表合計 > 100 列且 `--execute` | 退出 code 2（拒絕執行）|
| **backfill 連續失敗** | 連續 3 次 SQL error | 退出 code 5 |
| **§4.1 回退驗證失敗** | downgrade 後 FK 欄/INDEX/constraint 殘留，或 rowcount 漂移 | 退出 code 6 |
| **rate < 0.95** | backfill_rate 未達 PM W-1 門檻 | 退出 code 5 |
| **Point-of-no-return idle-tx / deadlock** | 中斷後殘留 idle-in-tx 或偵測到 deadlocks | 退出 code 8 |

⛔ **不可加 `--force` 繞過 — 這些 guard 是 PM W-1 紅線設計**。

---

## 5. 完成後的 5 步收尾（升 G3 ✅ 生產 staging 版）

```bash
# 1. 檢視量測結果
cat tools/sd06_w3_dryrun_output/<timestamp>/results.md

# 2. 將 §6.2 / §6.3 / §6.4 區塊複製貼入 SD06_FK_DryRun_Report.md
#    取代「§6.2 1M 列實測時間表」整段（覆蓋 AI-Agent 演練版本地數據）
$EDITOR docs/05_development/SD06_FK_DryRun_Report.md

# 3. §7 簽核欄手動補三方簽名（DBA + Tech Lead + PM）
#    建議 §7.1 改名為「§7.1 生產 staging 演練簽核」+ §7.2 標「✅ 已完成」

# 4. 更新 gate_audit.md SD06-G3 為「✅ 已簽核（生產 staging 版）」
$EDITOR docs/05_development/gate_audit.md

# 5. git commit + tag
git add docs/05_development/{SD06_FK_DryRun_Report.md,gate_audit.md,risk_log.md}
git commit -m "SD_06 W3 G3 ✅ — 生產 staging 1M 列 dry-run 三方簽核完成"
git tag -a gate/SD06-G3-passed-production HEAD \
    -m "Gate SD06-G3 passed (production staging $(date -u +%Y-%m-%d)): DBA + Tech Lead + PM 三方簽核"
git push origin gate/SD06-G3-passed-production
```

---

## 6. 應急停止 / 回退（Point-of-no-return 觸發時）

腳本內建保護（exit code 對應）：

```
退出代碼 → 應對策略

5  backfill 失敗（rate < 0.95 / 連續 3 fail）
   → 檢視 backfill.log / 修正 backfill_legacy_fk JOIN 條件
   → 若 ≥ 50% 列已 backfilled：⚠️ 不可 downgrade；前滾修補

6  回退驗證失敗（§4.1 殘留）
   → DBA 手動執行 SD06_FK_DryRun_Report.md §4.1 6 個 SQL 排查殘留
   → 找 Tech Lead 雙簽決定處理路徑

7  pg_restore 失敗
   → 檢視 restore.log；通常是 schema 不對齊（alembic head drift）
   → 確認 staging 與 backup 來源 DB 同 alembic head

8  Point-of-no-return idle-tx / deadlocks 殘留
   → 立即 psql `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle in transaction';`
   → 找 DBA + Tech Lead 排查 lock graph
```

對應 [SD06_FK_DryRun_Report.md §11](../docs/05_development/SD06_FK_DryRun_Report.md) 回退策略 + [SD06_W3_DBA_Handover.md §3](../docs/05_development/SD06_W3_DBA_Handover.md) 應急聯絡表。

---

## 7. 與 AI-Agent 演練版的差異

| 項目 | AI-Agent 演練版（2026-05-17） | 本生產 staging 版 |
|------|---------------------------|------------------|
| 執行環境 | 本地 docker `autoclaude_pg`（pgvector/pgvector:pg16） | 公司 staging 機 |
| 1M 列實測時間 | 基準量級（單機無並發） | **真實量級（含並發 / WAL lag / IOPS 配額）** |
| §7 簽核 | DBA-Agent + Tech-Lead-Agent + PM-Agent | **人類三方** |
| Production 上線授權 | ❌ 不可 | ✅ 可（人類 PM 親簽後）|
| gate_audit 狀態 | ✅ AI-Agent 演練版 | ✅ 已簽核（生產 staging 版）|

---

## 8. FAQ

**Q1: 我可以在 production DB 直接跑嗎？**
A: **絕對不行**。腳本 Safety guard 會擋住（4 表 > 100 列即 exit code 2），但更重要的是 **PM W-1 紅線**：必須在 staging 隔離 DB 跑。

**Q2: 我跑到一半中斷了，如何恢復？**
A: 中斷後 staging DB 可能停在任意 alembic head + 部分 backfilled。建議：
```bash
# 1. 先檢視當前 head
alembic current

# 2. 強制回到 0009（任何 head 都可 downgrade）
alembic downgrade 0009_three_tier_schema

# 3. TRUNCATE 4 表（這是 staging，無業務影響）
psql $AUTOCLAUDE_DB_DSN -c "TRUNCATE playbook_runs, playbook_versions, checkpoints, knowledge_entries CASCADE;"

# 4. 重跑
bash tools/sd06_w3_staging_dryrun.sh --execute
```

**Q3: backfill_legacy_fk JOIN 條件需要客製嗎？**
A: 本腳本內建的是 **本演練 seed metadata 的 JOIN 條件**（`metadata->>'goal_task_title'` + `project=projects.name`）。
真正 production 上線時，DBA 需依公司**實際業務 metadata 結構**改寫 backfill function（樣板見 [SD06_FK_DryRun_Report.md §3](../docs/05_development/SD06_FK_DryRun_Report.md)）。
本腳本演練的是「**流程框架 + 時間預算**」，不是 production backfill 邏輯本身。

**Q4: 我的 staging 用 PG17 / PG18，能跑嗎？**
A: 可以。pgvector 0.8+ 已支援 PG17/18，本 alembic chain 全用標準 SQL。詳見 [`docs/08_deployment/PG_Version_Upgrade_Guide.md`](../docs/08_deployment/PG_Version_Upgrade_Guide.md)。

**Q5: 1M 列預估耗時？**
A: 本地 docker PG16 實測：~70 秒（含 backup + upgrade + backfill + downgrade + restore + POR 模擬）。
公司 staging 預估：**5-30 分鐘**（依 IOPS、並發負載、replication lag）。
