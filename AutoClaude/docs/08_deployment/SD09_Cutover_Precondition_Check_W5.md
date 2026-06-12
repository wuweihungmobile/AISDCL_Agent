# SD_09 W5 PG db_only 切換前置條件齊備檢查（F-08）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v0.1（W0 stub；W5 切換前由 Tech Lead 填寫實測值）** |
| 建立日期 | 2026-05-20 |
| 對應 | [ADR-SD09-001 §2.5/§2.6](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) / [SD_Improving_09.md §1.1 議題 A](../04_planning/SD_Improving_09.md) |
| 引用工具 | `tools/observability_ga_check.py`（雙條件 1a 唯一取證）+ alembic / drift_log SQL 查詢 |
| 適用 Gate | SD09-G5（W5 切換前最後形式關卡）|

---

## 1. 切換前必檢清單（**逐項打勾才可啟動切換**）

### 1.1 雙條件 1a — 可觀測性 30 天 GA

```
[ ] 1a-1：tools/observability_ga_check.py --window 30 exit code = 0
[ ] 1a-2：.observability_history.jsonl ≥ 30 筆記錄（每日一筆）
[ ] 1a-3：所有記錄 emit_count > 0、trace_id_continuity == true
[ ] 1a-4：KB metric 4 項 snapshot 完整（hit_rate / query_p95_ms / strategy_rotation / cache_eviction）
```

實際指令：
```bash
python tools/observability_ga_check.py --window 30 --json | jq .
# 預期：{"status": "ready", "green_streak": 30, ...}
```

### 1.2 雙條件 1b — drift_log 30 天零事件

```
[ ] 1b-1：SELECT COUNT(*) FROM drift_log WHERE detected_at >= NOW() - INTERVAL '30 days' AND severity != 'info' = 0
[ ] 1b-2：drift_log 表結構齊備（alembic_version >= 0014）
[ ] 1b-3：dual_state mode 過去 30 天連續啟用（無 mode 切換事件）
```

實際指令（PG 環境內）：
```sql
SELECT
  COUNT(*) FILTER (WHERE severity != 'info') AS drift_count,
  MIN(detected_at) AS earliest_record,
  MAX(detected_at) AS latest_record
FROM drift_log
WHERE detected_at >= NOW() - INTERVAL '30 days';
-- 預期：drift_count = 0
```

場景 A（個人開發無 PG）fall-back：載入 `tests/contract/fixtures/drift_log_30day_zero.json` 確認形式。

### 1.3 紅線 ❌21 三項齊備

```
[ ] ❌21-1：staging ≥ 1M 列實測（tests/integration/fixtures/fk_staging_1m_wrapper.py）
[ ] ❌21-2：人類 DBA 親演完成（docs/06_quality/SD09_DBA_DryRun_Sign_W4.md 已簽）
[ ] ❌21-3：人類 PM 親簽 release approval（docs/06_quality/SD09_PM_Release_Approval_W5.md 已簽）
```

### 1.4 SOP §4-§8 落地

```
[ ] 4-1：Production_Migration_SOP.md §4 切換時序章節落地
[ ] 4-2：Production_Migration_SOP.md §5 rollback 章節落地（含 tools/pg_dump_to_yaml.py）
[ ] 4-3：Production_Migration_SOP.md §6 監控 dashboard 章節落地
[ ] 4-4：Production_Migration_SOP.md §7 RACI 章節落地
[ ] 4-5：Production_Migration_SOP.md §8 演練回顧章節落地
```

### 1.5 ADR / 風險登記齊備

```
[ ] ADR-SD09-001 PM 形式核准（commit SHA 已填）
[ ] ADR-SD09-005 PG canary 三階梯閾值已落地（10%/24h + 50%/48h + 100%/7d + 三觸發回滾條件）
[ ] risk_log.md §15 R-SD09-A-1~A-5 風險全數 🟢 緩解或 ⚠️ 可接受
```

---

## 2. 切換決議格式

由 Tech Lead 在 W5 G5 簽核前填寫並送 PM 親簽：

```
切換時間：____________________
切換版本（git SHA）：____________________
切換負責人（DBA）：____________________
PM 親簽（release approval）：____________________

雙條件齊備：
  1a observability GA：☐ 通過 / ☐ 未達 / ☐ 例外條款（ADR-SD09-001 §2.3）
  1b drift_log 30 天零：☐ 通過 / ☐ 未達 / ☐ 例外條款

紅線 ❌21 三項：
  1M 列實測：☐ / DBA 親演：☐ / PM 親簽：☐

決議：☐ 啟動切換 / ☐ 推遲切換（理由：____________________）
```

---

## 3. 失敗回退（ADR-SD09-001 §2.4 / §2.6）

| 觸發條件 | 自動 / 人工 | 動作 |
|---------|-----------|------|
| drift severity != 'info' | 自動 | ≤ 3 min 觸發 rollback；≤ 30 min 完成取證 |
| WAL lag CRITICAL | 自動 | 暫停 cutover，調降 canary 比例 |
| 連線數異常 | 自動 | 限流，由 DBA 介入分析 |
| 1a 或 1b 任一未達 | 人工 | W5 G5 改 conditional pass；切換延 SD_10 |

---

## 4. 切換後 7 天觀察期

```
[ ] 連續 7 天 drift_log severity != 'info' COUNT(*) = 0
[ ] 連續 7 天 WAL lag p95 < 1s
[ ] 連續 7 天 application_log error_rate < 0.1%
[ ] tools/pg_dump_to_yaml.py drill 演練成功（rollback 可用）
```

未達任一項 → 觸發 ADR-SD09-001 §2.5 物理回退範圍限制條款。

---

## 5. 參考文件

- [ADR-SD09-001 PG db_only 切換不可逆轉折點](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md)
- [ADR-SD09-005 PG canary 三階梯閾值](../04_planning/ADR/ADR-SD09-005-pg-canary-stage-thresholds.md)
- [Production_Migration_SOP.md](Production_Migration_SOP.md)
- [SD09_DBA_DryRun_Sign_W4.md](../06_quality/SD09_DBA_DryRun_Sign_W4.md)
- [SD09_PM_Release_Approval_W5.md](../06_quality/SD09_PM_Release_Approval_W5.md)
- [risk_log.md §15](../05_development/risk_log.md)
- [gate_audit.md §1-septies SD09-G5](../05_development/gate_audit.md)

---

**文檔元數據**：v0.1 stub | 建立 2026-05-20（SD_09 W0 zero-trust audit P1 修復）| W5 G5 切換前 Tech Lead 填寫實測值 + PM 親簽
