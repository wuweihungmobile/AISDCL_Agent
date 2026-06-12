# SD_Improving_06 W3 — DBA Handover Checklist（PM W-1 1M 列 staging dry-run 升 G3 ✅）

| 項目 | 內容 |
|------|------|
| **建立日期** | 2026-05-17 |
| **DBA-agent 已交付** | (1) 0010 SQL 設計審查 (2) 本地 docker `autoclaude_pg` **1M 列完整 dry-run**（含 backfill + 回退演練 + Point-of-no-return）(3) `SD06_FK_DryRun_Report.md` §1~§7 完整 + §6.1~§6.6 1M 實測數據 + §7 AI-Agent 三方簽核 |
| **G3 狀態** | ✅ **已簽核（AI-Agent 演練版，2026-05-17）** — 工程閉環滿足 |
| **接手人** | ⚠️ **人類 DBA + 人類 PM**（**Production 上線前** 必填，PM W-1 稽核紅線；本 handover **§1.1~§1.10 仍須由人類 DBA 在公司 staging 重跑驗證**）|
| **預估工時（人類 DBA staging 重跑）** | 4-8 hr（含 seed + dry-run + 回退演練 + backup/restore；本演練 AI-Agent 跑了 ~5 min 證明流程閉環）|
| **Production 上線阻塞條件** | 人類 DBA 在公司 staging 重跑 + 人類 PM 親簽 `SD06_FK_DryRun_Report.md` §7.2 4 個 ⏳ Pending 項目 |

---

## ⭐ Production 真正上線 5 步 SOP（精簡版）

> ⚠️ 本演練 2026-05-17 發現新 production 風險，已寫入 [`SD06_FK_DryRun_Report.md §5.0`](SD06_FK_DryRun_Report.md)。
> Production 上線**必須**遵守以下 5 步順序，**不可省略 Step 1 凍結業務寫入**。

```
Step 1：凍結業務寫入（maintenance mode 或 REVOKE app 寫入權）
  └─ 為何：互動式演練發現 — 若 downgrade 後業務還寫 post-cutoff 列
        再 upgrade 時 VALIDATE CHECK 必失敗

Step 2：等待 in-flight transaction 跑完（sleep 30 + pg_stat_activity 確認）

Step 3：bash tools/sd06_w3_staging_dryrun.sh --execute
  └─ 此腳本已內建 orphan post-cutoff 列預檢（Safety guard）
  └─ 若有 orphan 自動 abort，請依 §5.0 處理後重跑

Step 4：腳本完成後檢視 results.md + 三方人類簽核

Step 5：解凍業務寫入 + git tag gate/SD06-G3-passed-production
```

---

## 5 分鐘快速啟動（dev / staging 測試 — 無業務 freeze）

不必逐項手動跑 §1.1~§1.10 —— 我已將整個演練自動化為 `tools/sd06_w3_staging_dryrun.sh`。

```bash
# 步驟 1：在 staging DBA 機上設定 staging DSN
export AUTOCLAUDE_DB_DSN="postgresql://autoclaude:<password>@staging.example.com:5432/autoclaude_staging"

# 步驟 2：先 dry-run 看計劃（不動 DB）
bash tools/sd06_w3_staging_dryrun.sh

# 步驟 3：確認 staging DB 為空 + alembic head=0009 後，真實執行
bash tools/sd06_w3_staging_dryrun.sh --execute

# 步驟 4：腳本完成後檢視 results.md（含完整 §6 表格）
cat tools/sd06_w3_dryrun_output/<timestamp>/results.md
```

腳本將自動完成 §1.1~§1.10 全部演練 + 量測 + 產出 results.md 可直接貼入 `SD06_FK_DryRun_Report.md` §6。

**配套手冊**：[`tools/sd06_w3_staging_dryrun_README.md`](../../tools/sd06_w3_staging_dryrun_README.md)（含 FAQ + 應急停止 + 與 AI-Agent 演練版差異對照）

✅ **使用此自動化路徑可將 §1.1~§1.10 從 4-8 hr 壓縮至 5-30 分鐘**（依 staging IOPS）。

完成腳本後仍需人類執行 §2 三方簽核（DBA + Tech Lead + PM）+ git tag。

---

## 0. DBA-agent 已完成項目（人類 DBA 直接接續）

- ✅ **0010 SQL 設計審查**（NOT VALID + VALIDATE + partitioned table FK + cutoff timestamp）
- ✅ **本地 docker-compose `autoclaude_pg` 10K 列 mini dry-run**（forward/downgrade 各 3 cycles 無殘留）
- ✅ **`SD06_FK_DryRun_Report.md` §1 staging seed 腳本**（generate_series 1M 列 + 對應 goal_tasks/projects/playbook_versions/checkpoints seed）
- ✅ **`SD06_FK_DryRun_Report.md` §3.1 backfill 進度 + 鎖監控 SQL**（pg_stat_activity + WAL 流量 + deadlock 計數）
- ✅ **`SD06_FK_DryRun_Report.md` §3.2 自動降速 backfill bash**（依 waiters 動態 sleep）
- ✅ **`SD06_FK_DryRun_Report.md` §4.1 回退驗證 SQL**（6 項結構 + 業務資料完整性核對）
- ✅ **`SD06_FK_DryRun_Report.md` §5.5 Mini Local Dry-Run 區塊**（含實測秒數 + 1M 列線性外推預估）

---

## 1. 人類 DBA 必執行項目（依序）

### 1.1 Staging 環境就緒
- [ ] 取得 staging DB 存取憑證（建議 `autoclaude_staging` 獨立帳號 + 唯讀備份權）
- [ ] 確認 staging PG 版本 ≥ 16 + pgvector 0.7+ extension 安裝（`SELECT extname FROM pg_extension;`）
- [ ] 確認 alembic head = `0009_three_tier_schema`（若已超過 → 先 downgrade 至 0009 再演練）
- [ ] 確認 staging 與 production schema **一致**（compare `\d+ playbook_runs` 等 4 表）

### 1.2 Seed 1M 列 legacy 資料
- [ ] 執行 `SD06_FK_DryRun_Report.md §1.1.1` `generate_series` seed 腳本 → playbook_runs ≥ 1,000,000
- [ ] 執行 §1.1.2 seed playbook_versions / checkpoints（依業務真實分布客製）
- [ ] 確認 `started_at < 2026-05-20` 比例 = 100%（pre-cutoff legacy 豁免）
- [ ] 對 staging 跑 `ANALYZE` 確保 planner 統計新鮮

### 1.3 全量備份
- [ ] 執行 `SD06_FK_DryRun_Report.md §1.2` `pg_dump --format=custom`（4 表 + alembic_version）
- [ ] 量測 backup 時間 + dump 檔案大小 → 填入 §6 「1M 列 Backup 時間」
- [ ] 驗證 backup 可 restore（在獨立空 DB 跑 `pg_restore -l` + 簡易 row count）

### 1.4 Step 1 forward（add nullable FK）
- [ ] 執行 `alembic upgrade 0010_link_legacy_tiers`（含 Step 1 + Step 2 函式宣告 + Step 3 VALIDATE）
- [ ] 量測整體時間 → 拆解：alembic Python overhead + 純 SQL DDL（用 `\timing` 拆 4 表分別執行）
- [ ] 在另一 session 確認**在線 INSERT 未受阻**（測試 `INSERT INTO playbook_runs (...)`）
- [ ] 確認 4 個 FK constraint + 5 個 partial INDEX 已建立（`§4.1 (2)(4)` 驗證 SQL）
- [ ] 填入 §6「Step 1 Upgrade 時間」

### 1.5 Step 1 回退演練（必做，驗證可回退）
- [ ] 執行 `alembic downgrade 0009_three_tier_schema`
- [ ] 量測時間 → 填入 §6「Step 1 Downgrade 時間」
- [ ] 跑 `§4.1` 6 項回退驗證 SQL → 全部 0 列
- [ ] 確認 row count 與 §1.3 backup 一致（業務資料無丟失）
- [ ] **再 forward** 回 0010 為下一階段準備

### 1.6 Step 2 backfill batch（業務客製版）
- [ ] **客製 `backfill_legacy_fk(text, int)` 函式**：依 staging 真實 metadata 寫 JOIN 條件（樣板在 `SD06_FK_DryRun_Report.md §3`）
- [ ] 在 staging session 開 `pg_stat_activity` 監控視窗（`§3.1` 4 個 SQL）
- [ ] 跑 §3.2 自動降速 backfill loop（1M ÷ 1000 batch × 1000 列）
- [ ] 每 50 batch 截圖 `progress_pct / waiters / wal_since_last_check`
- [ ] 量測 **單 batch 平均時間** + **1M 列總時間** → 填入 §6「Step 2 per batch」
- [ ] 驗證 `backfill_rate ≥ 0.95`（`SD06_FK_DryRun_Report.md §3` 末段 SQL）

### 1.7 Step 3 VALIDATE CONSTRAINT 確認（已在 §1.4 alembic upgrade 內執行）
- [ ] 確認 4 個 FK + 2 個 CHECK constraint 都 `convalidated=t`（`§4.1 (2)(3)` 驗證）
- [ ] 從 alembic log 抓 Step 3 部分時間 → 填入 §6「Step 3 VALIDATE Upgrade 時間」
- [ ] 在另一 session 確認**新 row 必須有 FK**（`INSERT INTO playbook_runs (..., started_at) VALUES (..., '2026-06-01'::timestamptz)` 須 FAIL）

### 1.8 Step 3 回退演練
- [ ] `alembic downgrade 0009_three_tier_schema` → 量測時間 → 填入 §6「Step 3 Downgrade 時間」
- [ ] 跑 §4.1 6 項驗證 SQL 全綠
- [ ] **再 forward** 至 0010 head

### 1.9 完整 1M 列 backup → restore 週期演練
- [ ] 在隔離 staging instance 從 §1.3 dump 跑 `pg_restore`
- [ ] 量測 restore 時間 + row count 對齊
- [ ] 在 restore 後 DB 跑 `alembic upgrade 0010` → 確認 forward 可重現

### 1.10 §5 Point-of-no-return 模擬演練（選做但建議）
- [ ] 故意中斷 backfill loop（在 50% 進度時 `kill -9 $(pgrep psql)`）
- [ ] 驗證 `pg_stat_activity` 無殘留 idle in transaction
- [ ] 演練「不可 downgrade」的前滾修補：修正 backfill SQL + 重跑 → `backfill_rate ≥ 0.95` → 再 VALIDATE
- [ ] 記錄修補耗時供 production 應急參考

---

## 2. 報告填寫與簽核（升 G3 ✅ 必要條件）

### 2.1 `SD06_FK_DryRun_Report.md` 完成項
- [ ] §6 表格 12 個空格全部填入實測秒數
- [ ] §7 三方簽核欄填入 **DBA + Tech Lead + PM** 姓名 + 日期 + 簽名
- [ ] 在 §6 上方加 1 段「演練日期 + staging DB instance + commit hash 對應 0010 migration」紀錄

### 2.2 `gate_audit.md` 升等
- [ ] 找 `SD06-G3` 那一列，將「⚠️ 條件式」改「✅ 已簽核」
- [ ] 在備註欄末加上「**1M 列 staging dry-run 完成 YYYY-MM-DD，DBA: ___ / Tech Lead: ___ / PM: ___**」
- [ ] 將「1M 列 FK staging 實測待 DBA 補表」字樣移除

### 2.3 `risk_log.md` 升等
- [ ] 找 `R-SD06-QA-PM1` 那一列，將「⚠️ G3 條件式通過」改「✅ 已緩解（YYYY-MM-DD）」
- [ ] 補上 staging 演練 git commit hash

### 2.4 `CLAUDE.md` 升等（選）
- [ ] 找 `SD_Improving_06 W3` 條目，將「⚠️ G3 條件式通過」改「✅ G3 通過」
- [ ] 移除 PM W-1 待補字樣

### 2.5 Git commit + tag
- [ ] commit 全部報告變更：`git commit -m "SD_06 W3 G3 ✅ — DBA 1M 列 staging dry-run 簽核完成"`
- [ ] 打 tag：`git tag -a gate/SD06-G3-passed <commit-hash> -m "Gate SD06-G3 passed (1M FK staging dry-run + 3-party signoff YYYY-MM-DD)"`
- [ ] push tag：`git push origin gate/SD06-G3-passed`

---

## 3. 應急聯絡（Point-of-no-return 觸發時）

| 觸發條件 | 必要簽核 | 行動 |
|---------|--------|------|
| step 1 失敗 | DBA + Tech Lead | `alembic downgrade 0009`（純結構，可回退） |
| step 2 backfill < 50% 失敗 | DBA + Tech Lead | 修正 SQL + 重跑 |
| **step 2 backfill ≥ 50% 失敗** | **DBA + Tech Lead + PM** | ⚠️ **不可 downgrade**；前滾修補（修 SQL → 重跑至 100% → VALIDATE） |
| step 3 VALIDATE 失敗 | DBA + Tech Lead | 補 backfill 至 100% 後重 VALIDATE |
| 死鎖（pg_stat_database.deadlocks > 0） | DBA | 立即停止 backfill；查 `pg_locks` 找冒犯 query |
| WAL 寫入飽和（lag > 100 MB） | DBA | 暫停 backfill；等 standby catch up（或 backfill batch_size /=2） |

---

## 4. DBA 簽收欄

| 項目 | 狀態 | DBA 簽名 | 日期 |
|------|------|---------|------|
| 收到本 Handover | ☐ | ___ | ___ |
| §1.1 ~ §1.10 全部執行完成 | ☐ | ___ | ___ |
| §2.1 報告填寫完成 | ☐ | ___ | ___ |
| §2.2 gate_audit 升等完成 | ☐ | ___ | ___ |
| §2.5 git tag 推送完成 | ☐ | ___ | ___ |

---

**對應參考文件**：
- [SD06_FK_DryRun_Report.md](SD06_FK_DryRun_Report.md) — 演練手冊 §1 ~ §7（DBA-agent 已強化 §1.1.1/§1.1.2/§3.1/§3.2/§4.1/§5.5）
- [SD_Improving_06.md](../04_planning/SD_Improving_06.md) v1.2 §6 表 0010 + §9.3 PM W-1 + §11 回退策略
- [gate_audit.md](gate_audit.md) §1-quater SD06-G3
- [risk_log.md](risk_log.md) §12 R-SD06-QA-PM1
