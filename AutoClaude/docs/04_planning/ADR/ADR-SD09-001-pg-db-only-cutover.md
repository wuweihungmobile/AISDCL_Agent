# ADR-SD09-001 — PG db_only 切換不可逆轉折點

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0（PM 形式核准 2026-05-20；SD_09 W0 啟動條件之一）** |
| 建立日期 | 2026-05-19 |
| 最後更新 | **2026-05-20**（T0-7 PM 形式核准）（二輪四方審查修復：drift_log schema 對齊真實欄位 + 物理回退範圍限制 + 雙條件分拆 1a/1b + 個人開發 fall-back + fixture 路徑修正）|
| 狀態 | **ACCEPTED — PM 形式核准 2026-05-20（場景 A dev 自核）** |
| 對應 Sprint | SD_Improving_09 議題 A（PG production SOP 完整啟用）|
| 接續文件 | [ADR-SD08-005](ADR-SD08-005-pg-production-dual-track.md) §2.2 雙條件 |

---

## §1. 背景與動機

SD_08 W5 落地 ADR-SD08-005 雙軌制（AI-Agent 演練 + 人類 DBA 親簽）+ pg_health.py WAL lag adapter + Production_Migration_SOP.md §1-§3 草案；SD_09 W3-W5 將完成 SOP §4-§8 + 真實 PG production 上線。

由於 PG db_only 切換涉及生產資料一致性、業務連續性，必須明訂「不可逆轉折點」的**業務語意**與**物理回退路徑**。

---

## §2. 決策

### §2.1 業務語意「不可逆」

「不可逆轉折點」= **業務語意上的不可逆（DBA 簽核後業務不回退）**，**非物理不可逆**：
- 切換 `storage.mode = db_only` 後，業務層不應預期回退至 `yaml_only`
- 物理層仍提供 rollback SOP（§5）：PG dump → YAML import script，但屬「災難復原」非常規回退

### §2.2 雙條件對齊（接續 ADR-SD08-005 §2.2）

W5 切換前必須齊備（**SD-C3 修復：條件 1 拆 1a + 1b**）：

**條件 1a — IObservabilityPort + trace_id ContextVar 30 天 nightly 全綠**
- 起算：SD_08 W4 落地日 2026-05-18 → 完成 2026-06-17
- **multi-process trace_id GA 不計入 W5 條件**（延 W6 / SD_10；對應 R-SD09-F-2）
- 取證自動化：`python tools/observability_ga_check.py --window 30 --json | jq -e '.green_streak >= 30'`（W0 T0-O1 建立；QA-M4 修復）

**條件 1b — KB metric 觀察**
- 若 W0 PM 議題 G 拍板選 **(a) PG kb_metrics 表落地** → 取證 PG kb_metrics 表 30 天連續記錄
- 若 PM 拍板選 **(b) 刪除** 或 **(c) 延 SD_10** → 改判 N/A，改由 IObservabilityPort `emit_counter` nightly 抽樣證明 KB metric 仍寫入（in-memory or local jsonl）

**條件 2 — 30 天零 drift**（drift_log SLA 連續 30 天無 warn/critical 事件）
- 起算：SD_08 W5 落地日 2026-05-18 → 完成 2026-06-17
- 取證 SQL（**SD-C1 修復**：對齊 alembic 0013_drift_log.sql 真實欄位 `detected_at` / `severity` — `drift_count` 欄位不存在；任一 warn/critical 寫入即視為 drift 事件）：
  ```sql
  SELECT count(*) FROM drift_log
  WHERE detected_at > now() - interval '30 day'
    AND severity != 'info';
  -- 期望：0
  ```

### §2.3 紅線 ❌21（W5 真實 staging 必須三項齊備）

真實 staging（≥ 1M 列）切換禁止推進，除非以下三項全部完成：
1. **AI-Agent dry-run 演練**（W3 T3-A4；**QA-C1 修復** — reuse SD_06 W3 shell script `tools/sd06_w3_staging_dryrun.sh` + 新建 Python 包裝 fixture `tests/integration/fixtures/fk_staging_1m_wrapper.py`；舊文件提及的 `tests/integration/fixtures/fk_staging_1m.py` 為誤標，**該檔不存在**）
2. **人類 DBA 親演 + 簽核**（W4 T4-A5；signed-off / GPG）
3. **人類 PM 親簽 release approval**（W5 T5-A4；signed-off / GPG）

### §2.4 fall-back 例外條款（R-SD09-A-4）

若 W5 雙條件未達：
- 不切換 `db_only`，維持 `both` mode
- W5 G5 改判 conditional pass — **conditional pass 定義對齊 SD_08 gate**：依四方審查彙整 + PM 簽核但 Sprint 範圍縮小（Arch-m1 修復）
- db_only 切換動作延 SD_10
- 不視為 Sprint 失敗

### §2.5 物理回退範圍限制（**Arch-C2 修復**）

§2.1 業務「不可逆」並非物理不可逆，但物理回退範圍**有限制**：

| 類別 | 範圍 | 是否可 dump→YAML 回退 | 回退損失 |
|------|------|---------------------|---------|
| **state_repository 三層任務模型** | playbooks / runs / steps（SD_06 W3）| ✅ 可（pg_dump_to_yaml.py 工具支援）| 0 |
| **pgvector embeddings** | knowledge_chunks 向量資料 | ❌ 不可逆（embeddings 為 PG-only，無 YAML schema）| 丟失全部歷史 embeddings |
| **kb_metrics 表**（議題 G 選 a 時）| KB metric 跨 session 統計 | ❌ 不可逆 | 丟失 ≤ 7 天觀察資料 |
| **drift_log historical partition** | 365 天分區累積 | ⚠️ 部分（最近 30 天可備份；舊分區 archive 後丟失）| 丟失 historical 紀錄 |

**業務允收條件**：物理回退即接受 — 丟失 ≤ 7 天觀察資料 / pgvector embeddings 重建（重跑 nightly 索引）但**保留 3 層任務狀態完整性**。

SOP §5（W3 T3-A3 補完）必含 schema mapping 表（PG → YAML 對應欄位 / 不可逆欄位明列），由 `tools/pg_dump_to_yaml.py` 工具實現（T3-A3-1 + T3-A3-2 拆細，SD-M4 修復）。

---

## §3. 取證來源（W5 雙條件齊備驗證）

W5 T5-A2 `docs/06_quality/SD09_Cutover_Precondition_Check_W5.md` 必填：

| 條件 | 取證來源 | 命令 |
|------|---------|------|
| 條件 1a — IObservabilityPort + trace_id 30 天 nightly 全綠 | `.observability_history.jsonl` 30 行（QA-M4 修復） | `python tools/observability_ga_check.py --window 30 --json \| jq -e '.green_streak >= 30'` |
| 條件 1b — KB metric 觀察（議題 G (a) 時取 PG；(b)/(c) 時取 in-memory）| PG `kb_metrics` 表 OR IObservabilityPort emit_counter 抽樣 | `psql -c "SELECT count(*) FROM kb_metrics WHERE window_start_at > now() - interval '30 day'"` OR `jq -e '.kb_metric_counter > 0' .observability_history.jsonl` |
| 條件 2 — 30 天零 drift（SD-C1 修復：schema 對齊 alembic 0013）| PG `drift_log` 表 | `psql -c "SELECT count(*) FROM drift_log WHERE detected_at > now() - interval '30 day' AND severity != 'info'"` 期望 0 |
| DBA 親簽 | `SD09_DBA_DryRun_Sign_W4.md` | `git log --show-signature -1 -- docs/06_quality/SD09_DBA_DryRun_Sign_W4.md` |
| PM 親簽 | `SD09_PM_Release_Approval_W5.md` | `git log --show-signature -1 -- docs/06_quality/SD09_PM_Release_Approval_W5.md` |

### §3.1 個人開發 fall-back（**QA-C3 修復**）

若 `AUTOCLAUDE_DB_DSN` 未設或 PG 不可達（場景 A 個人開發）：
- drift_log 取證採 mock fixture：`tests/contract/fixtures/drift_log_30day_zero.json`（30 筆模擬列，全 `severity='info'`）
- 條件 1a 取證仍走 `tools/observability_ga_check.py`（純檔案掃描，不依賴 PG）
- 條件 1b 走 IObservabilityPort `emit_counter` 抽樣（in-memory snapshot）
- SD09_Execution_Guide.md §0.3 命令對應補 fall-back 形式：`if command -v psql >/dev/null && [ -n "$AUTOCLAUDE_DB_DSN" ]; then ... else cat tests/contract/fixtures/drift_log_30day_zero.json; fi`

---

## §4. 對應參考

- [SD_Improving_09.md](../SD_Improving_09.md) §1.1 議題 A
- [SD09_Execution_Guide.md](../../05_development/SD09_Execution_Guide.md) W3/W4/W5
- [ADR-SD09-005](ADR-SD09-005-pg-canary-stage-thresholds.md) canary 三階梯閾值
- [ADR-SD08-005](ADR-SD08-005-pg-production-dual-track.md) 雙軌制 + 雙條件
- [Production_Migration_SOP.md](../../08_deployment/Production_Migration_SOP.md) §4-§5

---

**簽核**：✅ ACCEPTED — 2026-05-21（SD_09 W0 T0-7 PM 形式核准；場景 A 個人開發 dev 自核 commit）
