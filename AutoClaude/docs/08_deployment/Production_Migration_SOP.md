# Production Migration SOP — yaml_only → both → db_only 灰度推進（草案 v0.1）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v0.1（SD_08 W5 §1–§3 草案；§4–§8 待 SD_09 補完）** |
| 建立日期 | 2026-05-18 |
| 對應 ADR | [ADR-SD08-005](../04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md) PG production 雙軌制 |
| 對應 Sprint | SD_Improving_08 W5（前置）+ SD_Improving_09（正式 SOP） |
| 文件狀態 | **DRAFT — §1–§3 W5 落地草案；正式 SOP 待 SD_09 啟動觸發** |

> ⛔ **紅線**：本 SOP §3 production 切換步驟在 SD_09 啟用前 **禁止實作或試跑**（SD_08 紅線 ❌20 / ADR-SD08-005 §2.2 雙條件未達禁切換）。本檔僅為「前置設計藍本」。

---

## §1. 前置確認（SD_08 W5 落地完成則此節打勾）

```
[✅] (a) AI-Agent 演練紀錄 ≥ 1 次（SD_06 W3 完成 2026-05-17）
       — 紀錄檔：docs/08_deployment/SD06_FK_DryRun_Report.md

[✅] (b) WAL lag adapter 就位（SD_08 W5 T5-H2 完成）
       — 實作：autoclaude/infra/observability/pg_health.py
       — 告警閾值：lag < 2s 正常 / 2-10s warn / ≥ 10s critical
       — Metric：pg_wal_lag_seconds histogram / pg_wal_lag_warn|critical counter

[✅] (c) ADR-SD08-005 PM 形式核准（SD_08 W5 T5-H6 完成）
       — 場景 A 個人開發 dev 自核 2026-05-18

[  ] (d) [SD_09 啟動前必跑] 可觀測性 GA — IObservabilityPort + LocalLogger + 4 KB metric
        + trace_id 端對端 + 30 天無 trace_id 斷鏈事件
       — 量測檔：tests/integration/test_observability_e2e.py（SD_09 新建）

[  ] (e) [SD_09 啟動前必跑] drift_log 連續 30 天零事件
       — 量測：SELECT count(*) FROM drift_log WHERE detected_at > NOW() - INTERVAL '30 days' = 0
       — 工具：tools/drift_log_zero_check.py（SD_09 新建）
```

**通過條件**：(a)–(c) 已完成（SD_08 W5）；(d)–(e) 為 SD_09 啟用 §2 灰度的前置阻塞。

---

## §2. yaml_only → both（staging 灰度啟動）

> 本節在 SD_08 W5 末已**可技術上執行**（File backend 仍主寫；PG 為影子），但**生產資料**等 SD_09 啟用條件達成後才執行。

### §2.1 啟動條件
- §1 (a)–(c) 全綠
- staging 環境 PG 17 + pgvector 已建（SD_06 W3 完成）
- alembic chain 0001–0014 已套用

### §2.2 切換步驟（staging 順序）

```
[  ] 1. 備份 File backend 全部 yaml（snapshot：autoclaude_state_${date}.tar.gz）
[  ] 2. 確認 alembic head 對齊：alembic current → 0014_xxx
[  ] 3. 修改 config.yaml：
        storage:
          mode: "both"                   # 從 yaml_only 改為 both
          db_dsn: "postgresql://..."
          dual_write_strict: "fail_loud" # 任何 drift 立即 raise（不容忍）
[  ] 4. 重啟 autoclaude；觀察 startup log 確認雙寫成功
[  ] 5. 連續 7 天監控（每天人工檢查）：
        - drift_log = 0 事件
        - reconcile_queue depth p95 < 10
        - pg_wal_lag_seconds < 2s
        - 無 fail_loud 拋出
```

### §2.3 §2 灰度 SLA（任一違反必回退 yaml_only）

| 指標 | SLA | 違反處置 |
|------|-----|---------|
| `drift_log` 事件 | = 0 / 7 天 | 回退 yaml_only 並開 P1 issue |
| `reconcile_queue` depth p95 | < 10 | 警告 + 增加 drain worker |
| `pg_wal_lag_seconds` | < 2s | 警告 + DBA 介入排查 |
| `pg_wal_lag_seconds` | ≥ 10s | **自動降級 yaml_only**（ADR-SD08-005 §2.4 critical 行為） |
| `dual_write_strict` raise | 0 次 | **立即停機** + 業務通知 |

### §2.4 監控儀表板（手動 query）
- WAL lag：透過 `DefaultPgHealthMonitor.sample()` → `pg_wal_lag_seconds`
- drift：`SELECT count(*) FROM drift_log WHERE detected_at > NOW() - INTERVAL '1 day'`
- reconcile：`SELECT count(*) FROM reconcile_queue WHERE status = 'pending'`

---

## §3. both → db_only（production 切換，不可逆）

> ⛔ **SD_08 W5 不執行本節**；本節為設計藍本，正式步驟 SD_09 補完。

### §3.1 啟動雙條件（同時達成 ADR-SD08-005 §2.2）

| # | 條件 | 量測檔 |
|---|------|--------|
| 1 | 可觀測性 GA + 30 天無 trace_id 斷鏈事件 | `tests/integration/test_observability_e2e.py`（SD_09 新建） |
| 2 | drift_log 連續 30 天零事件 | `tools/drift_log_zero_check.py`（SD_09 新建） |

任一未達 → 不可啟動 §3 切換。

### §3.2 人類簽核（不可由 AI-Agent 替代）

```
[  ] 人類 DBA 在公司 staging（≥ 1M 真實列）重跑 dry-run
[  ] 人類 DBA 親簽 release approval
[  ] 人類 PM 親簽 production release
[  ] 簽核紀錄存於 docs/08_deployment/SD09_Production_Cutover_Signoff.md（SD_09 新建）
```

### §3.3 切換步驟（SD_09 補完）

```
[  ] 1. 停機公告（≥ 24h 提前）
[  ] 2. 最後一次 reconcile_queue drain（waiting=0）
[  ] 3. 修改 config.yaml：storage.mode = "db_only"
[  ] 4. 重啟 + 24h smoke
[  ] 5. rollback plan ready（保留 §2 both 配置可即時切回）
```

---

## §4–§8（SD_09 補完）

- §4. Rollback Playbook（自動 + 手動兩條路徑）
- §5. 災難恢復（PG primary 失效 → standby 切換）
- §6. SLA 監控與告警（Grafana / PagerDuty 整合）
- §7. 後續維護（VACUUM / ANALYZE / 索引重建週期）
- §8. 退役 yaml_only（資料保留 ≥ 90 天後實體刪除）

---

## §9. 風險登記（連動 ADR-SD08-005 §2.5）

| 優先 | 風險 | SD_08 W5 涵蓋 |
|------|------|---------------|
| 1（高） | WAL replication lag | ✅ pg_health.py WAL lag adapter |
| 2（中） | 雲端 IOPS 配額 | ⏳ SD_09 補完（雲服務 API 整合） |
| 3（低） | 並發負載 | ⏳ SD_09 locust 100→500→1000 三階梯 |

---

## §10. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v0.1 | 2026-05-18 | SD_08 W5 T5-H5 §1–§3 草案落地；§4–§8 待 SD_09 補完 |
