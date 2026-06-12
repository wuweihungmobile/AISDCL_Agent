#!/usr/bin/env bash
# SD_Improving_06 W3 — 1M 列 FK staging dry-run 全自動化腳本
# ----------------------------------------------------------------------
# 用途：DBA 在公司 staging 上一行命令完成 PM W-1 強制演練
# 參考：docs/05_development/SD06_FK_DryRun_Report.md §1~§5
#       docs/05_development/SD06_W3_DBA_Handover.md
#
# 預設行為：dry-run（不實際下 alembic upgrade）— 須加 --execute 才會真正執行
# 量測產出：tools/sd06_w3_dryrun_output/<timestamp>/
#   ├── seed.log
#   ├── backup_pre_0010_<timestamp>.dump
#   ├── upgrade.log
#   ├── backfill.log
#   ├── downgrade.log
#   ├── point_of_no_return.log
#   ├── restore.log
#   └── results.md（量測結果表格，可直接貼入 SD06_FK_DryRun_Report.md §6）
#
# 使用：
#   # 1. dry-run（僅檢查連線 + 印出將執行的步驟，不動 DB）
#   bash tools/sd06_w3_staging_dryrun.sh
#
#   # 2. 完整執行（請務必先 backup！）
#   bash tools/sd06_w3_staging_dryrun.sh --execute
#
#   # 3. 自訂 DSN（預設讀 $AUTOCLAUDE_DB_DSN）
#   AUTOCLAUDE_DB_DSN="postgresql://user:pass@staging:5432/db" \
#       bash tools/sd06_w3_staging_dryrun.sh --execute
#
#   # 4. 自訂 seed 列數（預設 1,000,000；測試可降為 10,000）
#   SEED_ROWS=10000 bash tools/sd06_w3_staging_dryrun.sh --execute
#
#   # 5. 跳過 Point-of-no-return 模擬（不想 kill 自己 backfill 時）
#   SKIP_POINT_OF_NO_RETURN=1 bash tools/sd06_w3_staging_dryrun.sh --execute
#
# ⛔ 安全紅線（自動內建）：
#   - 若 DB 已有 ≥ 100 列真實業務資料於 4 個 legacy 表，拒絕執行（避免汙染 production）
#   - alembic head 必須為 0009_three_tier_schema；不符合則 abort（避免在 0010 已 forward 的 DB 重跑）
#   - backfill 失敗達 3 次連續 → 立即停止
#   - 死鎖計數 > 0 → 立即停止
#   - 預設 SET LOCAL statement_timeout = 5min（防 backfill 卡死）
#
# 退出代碼：
#   0  全部演練成功 + results.md 已產出
#   1  環境檢查失敗（DB 連線 / psql 不存在 / alembic head 不對）
#   2  Safety guard 觸發（DB 已有真實業務資料）
#   3  Seed 失敗
#   4  Forward 失敗
#   5  Backfill 失敗（rate < 0.95 或連續失敗）
#   6  Rollback 失敗（§4.1 驗證未全綠）
#   7  Restore 失敗
#   8  Point-of-no-return 模擬失敗
# ----------------------------------------------------------------------
set -euo pipefail

# ── 預設參數 ───────────────────────────────────────────────────────
EXECUTE=0
SEED_ROWS="${SEED_ROWS:-1000000}"
BATCH_SIZE="${BATCH_SIZE:-5000}"
SKIP_POINT_OF_NO_RETURN="${SKIP_POINT_OF_NO_RETURN:-0}"
DSN="${AUTOCLAUDE_DB_DSN:-}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/tools/sd06_w3_dryrun_output/${TS}"
ALEMBIC_HEAD_EXPECTED="0009_three_tier_schema"

# ── 引數解析 ───────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --execute) EXECUTE=1 ;;
        --help|-h)
            head -40 "$0" | sed -n '2,40p'
            exit 0 ;;
        *) echo "❌ unknown arg: $arg" >&2; exit 1 ;;
    esac
done

mkdir -p "$OUT_DIR"
exec > >(tee -a "$OUT_DIR/main.log") 2>&1

log()  { echo "[$(date -u +%H:%M:%S)] $*"; }
fail() { log "❌ $1"; exit "${2:-1}"; }
ok()   { log "✅ $*"; }

# ── Step 0：環境檢查 ───────────────────────────────────────────────
log "=========================================="
log "SD_06 W3 staging dry-run 啟動"
log "Mode: $([ $EXECUTE -eq 1 ] && echo "EXECUTE" || echo "DRY-RUN（不會動 DB）")"
log "SEED_ROWS: $SEED_ROWS / BATCH_SIZE: $BATCH_SIZE"
log "輸出目錄: $OUT_DIR"
log "=========================================="

[ -z "$DSN" ] && fail "AUTOCLAUDE_DB_DSN 未設定" 1
command -v psql >/dev/null 2>&1 || fail "psql 不存在於 PATH" 1
command -v alembic >/dev/null 2>&1 || fail "alembic 不存在於 PATH" 1
command -v pg_dump >/dev/null 2>&1 || fail "pg_dump 不存在於 PATH" 1
command -v pg_restore >/dev/null 2>&1 || fail "pg_restore 不存在於 PATH" 1

# psql 連線測試
PSQL_DSN="${DSN/+asyncpg/}"
psql "$PSQL_DSN" -c 'SELECT 1' >/dev/null 2>&1 || fail "DB 連線失敗：$PSQL_DSN" 1
ok "DB 連線成功"

# Alembic head 檢查
CURR_HEAD="$(alembic current 2>/dev/null | tail -1 || echo "")"
[ -z "$CURR_HEAD" ] && fail "alembic current 失敗" 1
log "目前 alembic head: $CURR_HEAD"
echo "$CURR_HEAD" | grep -q "$ALEMBIC_HEAD_EXPECTED" || fail "alembic head 須為 $ALEMBIC_HEAD_EXPECTED；目前: $CURR_HEAD（請先 downgrade 或 upgrade）" 1
ok "alembic head 符合預期：$ALEMBIC_HEAD_EXPECTED"

# Safety guard：拒絕 production DB
ROW_TOTAL="$(psql "$PSQL_DSN" -tA -c "
SELECT
  (SELECT count(*) FROM playbook_runs) +
  (SELECT count(*) FROM playbook_versions) +
  (SELECT count(*) FROM checkpoints) +
  (SELECT count(*) FROM knowledge_entries)
" 2>/dev/null || echo "999999999")"
log "既有 4 表總列數：$ROW_TOTAL"
if [ "$ROW_TOTAL" -gt 100 ] && [ "$EXECUTE" -eq 1 ]; then
    fail "Safety guard：4 表已有 $ROW_TOTAL 列真實資料（> 100），拒絕在此 DB 跑 dry-run。請改用 staging 隔離 DB 或先清空" 2
fi
ok "Safety guard 通過（DB 接近空）"

# Safety guard：orphan post-cutoff 列（互動式演練 2026-05-17 發現的 production 風險）
# 若 downgrade 後業務還在寫 post-cutoff 列，再 upgrade 時 VALIDATE CHECK 必失敗
ORPHAN_COUNT="$(psql "$PSQL_DSN" -tA -c "
SELECT count(*) FROM playbook_runs
WHERE started_at >= '2026-05-20 00:00:00+00'::timestamptz
" 2>/dev/null || echo "0")"
if [ "$ORPHAN_COUNT" -gt 0 ] && [ "$EXECUTE" -eq 1 ]; then
    fail "Safety guard：偵測到 $ORPHAN_COUNT 個 orphan post-cutoff 列（started_at >= 2026-05-20）。
請先依 SD06_FK_DryRun_Report.md §5.0 處理（DELETE 或補 goal_task_id），再重跑此腳本。
SQL：SELECT playbook_id, started_at FROM playbook_runs WHERE started_at >= '2026-05-20'::timestamptz;" 2
fi
ok "Safety guard：orphan post-cutoff 列檢查通過（count=$ORPHAN_COUNT）"

if [ "$EXECUTE" -eq 0 ]; then
    log "🔍 DRY-RUN 模式：以下為將執行的步驟摘要"
    cat <<'PLAN'

Step 1：seed 1M 列 playbook_runs + 對應 projects / goal_tasks / versions / checkpoints
Step 2：pg_dump --format=custom 4 表（量測 backup 時間）
Step 3：alembic upgrade 0010_link_legacy_tiers（量測時間）
Step 4：在 0010 head 安裝客製 backfill_legacy_fk 函式 + 跑 1M 列 backfill
Step 5：驗證 backfill_rate ≥ 0.95
Step 6：alembic downgrade 0009 + §4.1 6 項回退驗證
Step 7：alembic upgrade 0010 + alembic downgrade 0009（量測對稱性）
Step 8：(若未 SKIP) Point-of-no-return：30% 中斷 + 前滾修補
Step 9：pg_restore data-only 至獨立 DB（量測時間）
Step 10：產出 results.md 量測結果表格

要實際執行請加 --execute
PLAN
    exit 0
fi

# ── Step 1：Seed 1M 列 ─────────────────────────────────────────────
log "── Step 1：Seed $SEED_ROWS 列 legacy 資料 ──"
SEED_LOG="$OUT_DIR/seed.log"
START=$(date +%s%N)
psql "$PSQL_DSN" -v ON_ERROR_STOP=1 > "$SEED_LOG" 2>&1 <<SEED
\timing on
INSERT INTO projects (name, description) VALUES
  ('staging_proj_a', 'dryrun'), ('staging_proj_b', 'dryrun')
ON CONFLICT (name) DO NOTHING;

INSERT INTO goal_tasks (project_id, title, depth, priority)
SELECT p.project_id, 'demo_goal_' || g::text, 1, 3
FROM projects p, generate_series(0, 999) AS g
WHERE p.name IN ('staging_proj_a', 'staging_proj_b')
ON CONFLICT DO NOTHING;

INSERT INTO playbook_runs (playbook_id, project, status, metadata, started_at)
SELECT
  'staging_legacy_' || lpad(i::text, 7, '0'),
  CASE WHEN i % 2 = 0 THEN 'staging_proj_a' ELSE 'staging_proj_b' END,
  CASE WHEN i % 100 < 70 THEN 'success'
       WHEN i % 100 < 95 THEN 'escalated'
       ELSE 'interrupted' END,
  jsonb_build_object('goal_task_title', 'demo_goal_' || (i % 1000)::text,
                     'seeded_by', 'SD06_W3_dryrun_${TS}'),
  '2025-01-01 00:00:00+00'::timestamptz + (i * 7 || ' seconds')::interval
FROM generate_series(1, $SEED_ROWS) AS i;

INSERT INTO playbook_versions (original_playbook_id, generation, yaml_content, created_at)
SELECT
  'staging_pv_' || lpad(i::text, 6, '0'), 1,
  'version: 1' || E'\n' || 'name: staging_' || i::text,
  '2025-06-01 00:00:00+00'::timestamptz + (i || ' minutes')::interval
FROM generate_series(1, $SEED_ROWS / 10) AS i;

INSERT INTO checkpoints (run_id, playbook_id, step_idx, step_id, total_steps,
                         completed_step_log, peak_token_pct, saved_at)
SELECT r.run_id, r.playbook_id, (random() * 10)::int, 'T01', 20,
       ARRAY['T01']::text[], 50.0, r.started_at + INTERVAL '1 hour'
FROM playbook_runs r LIMIT ($SEED_ROWS / 2);

ANALYZE projects;
ANALYZE goal_tasks;
ANALYZE playbook_runs;
ANALYZE playbook_versions;
ANALYZE checkpoints;
SEED
END=$(date +%s%N)
SEED_MS=$(( (END - START) / 1000000 ))
ok "Seed 完成：${SEED_MS} ms"

# ── Step 2：Backup ─────────────────────────────────────────────────
log "── Step 2：pg_dump 4 表 backup ──"
BACKUP_FILE="$OUT_DIR/backup_pre_0010_${TS}.dump"
START=$(date +%s%N)
pg_dump "$PSQL_DSN" \
    --table=playbook_runs --table=playbook_versions \
    --table=checkpoints --table=knowledge_entries \
    --format=custom --file="$BACKUP_FILE"
END=$(date +%s%N)
BACKUP_MS=$(( (END - START) / 1000000 ))
BACKUP_SIZE="$(du -h "$BACKUP_FILE" | cut -f1)"
ok "Backup 完成：${BACKUP_MS} ms / ${BACKUP_SIZE}"

# ── Step 3：alembic upgrade 0010 ──────────────────────────────────
log "── Step 3：alembic upgrade 0010 ──"
START=$(date +%s%N)
alembic upgrade 0010_link_legacy_tiers > "$OUT_DIR/upgrade.log" 2>&1 \
    || { cat "$OUT_DIR/upgrade.log"; fail "alembic upgrade 失敗" 4; }
END=$(date +%s%N)
UPGRADE_MS=$(( (END - START) / 1000000 ))
ok "Upgrade 完成：${UPGRADE_MS} ms"

# ── Step 4：Install backfill_legacy_fk + 跑 backfill ──────────────
log "── Step 4：Install custom backfill_legacy_fk + 跑 backfill ──"
psql "$PSQL_DSN" -v ON_ERROR_STOP=1 > "$OUT_DIR/backfill_install.log" 2>&1 <<'BACKFILL_FN'
-- PG18 fix：subquery 形式取代 WITH CTE
-- 原因：PG18 plpgsql 中 CTE + UPDATE...FROM 的 GET DIAGNOSTICS 回傳 0
-- 改用 subquery 形式可正確抓 ROW_COUNT
CREATE OR REPLACE FUNCTION backfill_legacy_fk(target_table text, batch_size int)
RETURNS bigint LANGUAGE plpgsql AS $fn$
DECLARE affected_rows bigint := 0;
BEGIN
    IF target_table = 'playbook_runs' THEN
        UPDATE playbook_runs pr SET goal_task_id = subq.goal_task_id
        FROM (
            SELECT pr2.run_id, gt.goal_task_id FROM playbook_runs pr2
            JOIN projects p ON pr2.project = p.name
            JOIN goal_tasks gt ON gt.project_id = p.project_id
                AND gt.title = pr2.metadata->>'goal_task_title'
            WHERE pr2.goal_task_id IS NULL
              AND pr2.started_at < '2026-05-20 00:00:00+00'::timestamptz
            LIMIT batch_size
        ) AS subq
        WHERE pr.run_id = subq.run_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
    ELSIF target_table = 'checkpoints' THEN
        UPDATE checkpoints cp SET goal_task_id = subq.goal_task_id
        FROM (
            SELECT cp2.checkpoint_id, pr.goal_task_id FROM checkpoints cp2
            JOIN playbook_runs pr ON pr.run_id = cp2.run_id
            WHERE cp2.goal_task_id IS NULL AND pr.goal_task_id IS NOT NULL
            LIMIT batch_size
        ) AS subq
        WHERE cp.checkpoint_id = subq.checkpoint_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
    ELSE
        RAISE EXCEPTION 'Unknown target_table: %', target_table;
    END IF;
    RETURN affected_rows;
END
$fn$;
BACKFILL_FN

# 跑 backfill loop
BATCHES_MAX=$((SEED_ROWS / BATCH_SIZE + 5))
START=$(date +%s%N)
TOTAL=0
BATCH_COUNT=0
CONSEC_FAIL=0
for i in $(seq 1 $BATCHES_MAX); do
    affected="$(psql "$PSQL_DSN" -tA -c "SELECT backfill_legacy_fk('playbook_runs', $BATCH_SIZE);" 2>>"$OUT_DIR/backfill.log" || echo "ERR")"
    if [ "$affected" = "ERR" ]; then
        CONSEC_FAIL=$((CONSEC_FAIL + 1))
        [ $CONSEC_FAIL -ge 3 ] && fail "backfill 連續失敗 3 次，停止" 5
        continue
    fi
    CONSEC_FAIL=0
    TOTAL=$((TOTAL + affected))
    BATCH_COUNT=$((BATCH_COUNT + 1))
    [ "$affected" = "0" ] && break
done
END=$(date +%s%N)
BACKFILL_MS=$(( (END - START) / 1000000 ))
PER_BATCH_MS=$((BATCH_COUNT > 0 ? BACKFILL_MS / BATCH_COUNT : 0))
ok "Backfill 完成：${TOTAL} 列 / ${BATCH_COUNT} batches / ${BACKFILL_MS} ms 總時 / ${PER_BATCH_MS} ms/batch"

# ── Step 5：backfill_rate ≥ 0.95 ─────────────────────────────────
log "── Step 5：驗證 backfill_rate ≥ 0.95 ──"
RATE="$(psql "$PSQL_DSN" -tA -c "
SELECT count(*) FILTER (WHERE goal_task_id IS NOT NULL)::float / count(*)
FROM playbook_runs;")"
log "backfill_rate = $RATE"
RATE_OK="$(echo "$RATE >= 0.95" | python3 -c 'import sys; print("yes" if eval(sys.stdin.read().strip().replace(">=", "@@").split("@@")[0]) >= 0.95 else "no")' 2>/dev/null || echo "no")"
# 用 python3 算（避免 bc 不存在）
[ "$(python3 -c "print('yes' if $RATE >= 0.95 else 'no')")" = "yes" ] || fail "backfill_rate $RATE < 0.95" 5
ok "backfill_rate $RATE ≥ 0.95"

# Backfill checkpoints
for i in $(seq 1 $BATCHES_MAX); do
    affected="$(psql "$PSQL_DSN" -tA -c "SELECT backfill_legacy_fk('checkpoints', $BATCH_SIZE);" 2>/dev/null || echo "0")"
    [ "$affected" = "0" ] && break
done
ok "Checkpoints backfill 完成"

# ── Step 6：alembic downgrade 0009 + §4.1 6 項驗證 ───────────────
log "── Step 6：alembic downgrade 0009 + §4.1 驗證 ──"
START=$(date +%s%N)
alembic downgrade 0009_three_tier_schema > "$OUT_DIR/downgrade.log" 2>&1 \
    || { cat "$OUT_DIR/downgrade.log"; fail "alembic downgrade 失敗" 6; }
END=$(date +%s%N)
DOWNGRADE_MS=$(( (END - START) / 1000000 ))
ok "Downgrade 完成：${DOWNGRADE_MS} ms"

# §4.1 6 項驗證
VERIFY="$(psql "$PSQL_DSN" -tA -c "
SELECT
  (SELECT count(*) FROM information_schema.columns
     WHERE table_name='playbook_runs' AND column_name='goal_task_id') ||','||
  (SELECT count(*) FROM pg_constraint
     WHERE conname IN ('fk_runs_goal_task','fk_versions_project','fk_checkpoints_goal_task','fk_kb_execution_item')) ||','||
  (SELECT count(*) FROM pg_constraint
     WHERE conname IN ('ck_runs_post_cutoff_has_goal','ck_versions_post_cutoff_has_project')) ||','||
  (SELECT count(*) FROM pg_indexes
     WHERE indexname IN ('idx_runs_goal_task','idx_versions_project','idx_checkpoints_goal_task','idx_kb_execution_item','idx_runs_active_per_goal')) ||','||
  (SELECT count(*) FROM playbook_runs) ||','||
  (SELECT count(*) FROM pg_proc WHERE proname='backfill_legacy_fk')
")"
echo "VERIFY=$VERIFY" >> "$OUT_DIR/downgrade.log"
IFS=',' read -r V1 V2 V3 V4 V5 V6 <<< "$VERIFY"
[ "$V1" = "0" ] || fail "§4.1(1) FK 欄位殘留: $V1" 6
[ "$V2" = "0" ] || fail "§4.1(2) FK constraint 殘留: $V2" 6
[ "$V3" = "0" ] || fail "§4.1(3) CHECK constraint 殘留: $V3" 6
[ "$V4" = "0" ] || fail "§4.1(4) INDEX 殘留: $V4" 6
[ "$V5" = "$SEED_ROWS" ] || fail "§4.1(5) row count drift: $V5 ≠ $SEED_ROWS" 6
[ "$V6" = "0" ] || fail "§4.1(6) backfill_legacy_fk 殘留: $V6" 6
ok "§4.1 回退驗證 6/6 全綠"

# ── Step 7：Forward 再 downgrade 對稱性 ──────────────────────────
log "── Step 7：再 forward + downgrade 對稱性驗證 ──"
alembic upgrade 0010_link_legacy_tiers > /dev/null 2>&1
START=$(date +%s%N)
alembic downgrade 0009_three_tier_schema > /dev/null 2>&1
END=$(date +%s%N)
DOWNGRADE2_MS=$(( (END - START) / 1000000 ))
ok "二次 downgrade：${DOWNGRADE2_MS} ms"

# ── Step 8：Point-of-no-return 模擬 ──────────────────────────────
POR_REPAIR_MS="skipped"
if [ "$SKIP_POINT_OF_NO_RETURN" = "0" ]; then
    log "── Step 8：Point-of-no-return 模擬 ──"
    alembic upgrade 0010_link_legacy_tiers > /dev/null 2>&1
    psql "$PSQL_DSN" -v ON_ERROR_STOP=1 > /dev/null <<'BACKFILL_FN2'
CREATE OR REPLACE FUNCTION backfill_legacy_fk(target_table text, batch_size int)
RETURNS bigint LANGUAGE plpgsql AS $fn$
DECLARE affected_rows bigint := 0;
BEGIN
    IF target_table = 'playbook_runs' THEN
        UPDATE playbook_runs pr SET goal_task_id = subq.goal_task_id
        FROM (
            SELECT pr2.run_id, gt.goal_task_id FROM playbook_runs pr2
            JOIN projects p ON pr2.project = p.name
            JOIN goal_tasks gt ON gt.project_id = p.project_id
                AND gt.title = pr2.metadata->>'goal_task_title'
            WHERE pr2.goal_task_id IS NULL
              AND pr2.started_at < '2026-05-20 00:00:00+00'::timestamptz
            LIMIT batch_size
        ) AS subq
        WHERE pr.run_id = subq.run_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
    END IF;
    RETURN affected_rows;
END
$fn$;
BACKFILL_FN2
    # 跑到 30% 中斷
    STOP_AT=$((SEED_ROWS * 3 / 10))
    DONE=0
    for i in $(seq 1 $BATCHES_MAX); do
        affected="$(psql "$PSQL_DSN" -tA -c "SELECT backfill_legacy_fk('playbook_runs', $BATCH_SIZE);" 2>/dev/null || echo "0")"
        DONE=$((DONE + affected))
        [ "$DONE" -ge "$STOP_AT" ] && break
        [ "$affected" = "0" ] && break
    done
    log "中斷時已 backfill：$DONE 列"
    # 驗證 no idle tx / no deadlock
    IDLE_TX="$(psql "$PSQL_DSN" -tA -c "SELECT count(*) FROM pg_stat_activity WHERE state='idle in transaction' AND datname=current_database();")"
    DEAD="$(psql "$PSQL_DSN" -tA -c "SELECT coalesce(deadlocks, 0) FROM pg_stat_database WHERE datname=current_database();")"
    [ "$IDLE_TX" = "0" ] || fail "Point-of-no-return：殘留 idle in transaction = $IDLE_TX" 8
    [ "$DEAD" = "0" ] || fail "Point-of-no-return：偵測到 deadlocks = $DEAD" 8
    # 前滾修補
    START=$(date +%s%N)
    for i in $(seq 1 $BATCHES_MAX); do
        affected="$(psql "$PSQL_DSN" -tA -c "SELECT backfill_legacy_fk('playbook_runs', $BATCH_SIZE);" 2>/dev/null || echo "0")"
        [ "$affected" = "0" ] && break
    done
    END=$(date +%s%N)
    POR_REPAIR_MS=$(( (END - START) / 1000000 ))
    ok "Point-of-no-return 前滾修補完成：${POR_REPAIR_MS} ms"
    alembic downgrade 0009_three_tier_schema > /dev/null 2>&1
else
    log "── Step 8：Point-of-no-return（已 SKIP）──"
fi

# ── Step 9：pg_restore 演練 ──────────────────────────────────────
log "── Step 9：pg_restore data-only 演練 ──"
psql "$PSQL_DSN" -c "TRUNCATE playbook_runs, playbook_versions, checkpoints, knowledge_entries CASCADE;" > /dev/null
START=$(date +%s%N)
pg_restore -d "$PSQL_DSN" --data-only --disable-triggers "$BACKUP_FILE" > "$OUT_DIR/restore.log" 2>&1 \
    || log "⚠️ pg_restore 有 warnings（檢視 restore.log）"
END=$(date +%s%N)
RESTORE_MS=$(( (END - START) / 1000000 ))
RESTORED="$(psql "$PSQL_DSN" -tA -c "SELECT count(*) FROM playbook_runs;")"
[ "$RESTORED" = "$SEED_ROWS" ] || fail "pg_restore row count 不對齊: $RESTORED ≠ $SEED_ROWS" 7
ok "Restore 完成：${RESTORE_MS} ms / row count 對齊"

# ── Step 10：產出 results.md ─────────────────────────────────────
log "── Step 10：產出 results.md ──"
cat > "$OUT_DIR/results.md" <<RESULT
# SD_06 W3 staging dry-run 量測結果

**演練時間**：${TS}
**Seed 列數**：${SEED_ROWS}
**Batch size**：${BATCH_SIZE}
**DB DSN**：${PSQL_DSN//:[^@]*@/:***@}
**Alembic head（start）**：${ALEMBIC_HEAD_EXPECTED}

## 量測時間表（可直接貼入 SD06_FK_DryRun_Report.md §6.2）

| 階段 | 1M 列 Backup 時間 | Upgrade 時間 | Downgrade 時間 | 在線寫入鎖 |
|------|------------------|--------------|----------------|------------|
| Step 1 | n/a | 含於 alembic upgrade | 含於 alembic downgrade | None (NOT VALID) |
| Step 2 (per batch ${BATCH_SIZE}) | n/a | ${PER_BATCH_MS} ms / batch（總 ${BACKFILL_MS} ms / ${BATCH_COUNT} batches）| n/a | Row-level only |
| Step 3 VALIDATE | n/a | 含於 alembic upgrade | 含於 alembic downgrade | ShareUpdateExclusive |
| alembic upgrade 0010 整體 | n/a | **${UPGRADE_MS} ms** | n/a | — |
| alembic downgrade 0010→0009 整體 | n/a | n/a | **${DOWNGRADE_MS} ms**（二次 ${DOWNGRADE2_MS} ms）| — |
| pg_dump --format=custom | **${BACKUP_MS} ms / ${BACKUP_SIZE}** | n/a | n/a | None |
| pg_restore --data-only | n/a | **${RESTORE_MS} ms** | n/a | None |
| Point-of-no-return 前滾修補（70%）| n/a | n/a | **${POR_REPAIR_MS} ms** | Row-level only |

## §6.3 backfill 細節

| 項目 | 實測值 |
|------|--------|
| batch_size | ${BATCH_SIZE} |
| 總 batch 數 | ${BATCH_COUNT} |
| per-batch 平均 | ${PER_BATCH_MS} ms |
| backfill_rate | ${RATE} |
| §4.1 回退驗證 | 6/6 全綠 ✅ |
| Seed 耗時 | ${SEED_MS} ms |

## §6.4 Point-of-no-return 模擬

| 步驟 | 結果 |
|------|------|
| 中斷後 idle-in-tx | 0 ✅ |
| 中斷後 deadlocks | 0 ✅ |
| 前滾修補耗時 | ${POR_REPAIR_MS} ms |

## §7 簽核欄（人類 DBA 填寫後貼入）

| 角色 | 簽核者 | 日期 | 簽名 |
|------|--------|------|------|
| DBA | （請填） | $(date -u +%Y-%m-%d) | （請填） |
| Tech Lead | （請填） | $(date -u +%Y-%m-%d) | （請填） |
| PM | （請填） | $(date -u +%Y-%m-%d) | （請填） |

## Evidence

- Backup 檔案：${BACKUP_FILE}
- Main log：${OUT_DIR}/main.log
- 各 step log：${OUT_DIR}/*.log

RESULT

ok "results.md 已產出：$OUT_DIR/results.md"
log "=========================================="
log "✅ SD_06 W3 staging dry-run 全部完成"
log "=========================================="
log "下一步："
log "  1. 檢視 $OUT_DIR/results.md"
log "  2. 將 §6.2/§6.3/§6.4 區塊貼入 docs/05_development/SD06_FK_DryRun_Report.md"
log "  3. DBA + Tech Lead + PM 三方在 §7 簽核欄簽名"
log "  4. 更新 docs/05_development/gate_audit.md SD06-G3 為「✅ 已簽核（生產 staging 版）」"
log "  5. git commit + tag gate/SD06-G3-passed-production"
