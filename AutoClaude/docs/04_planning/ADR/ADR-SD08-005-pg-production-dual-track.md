# ADR-SD08-005：PG Production 雙軌制 — AI-Agent 演練 + 人類 DBA 親簽（SD_09 啟用前置條件）

| 項目 | 內容 |
|------|------|
| 狀態 | **APPROVED for SD_08 framework（PM 形式核准 / 場景 A 個人開發 dev 自核 2026-05-18；W5 G5 簽核紀錄 2026-05-18 落地：WAL lag adapter / pg_health.py / Production_Migration_SOP.md §1-§3 三項齊備）；SD_09 啟用前需人類 DBA + 人類 PM 最終簽核** |
| 建立日期 | 2026-05-18 |
| 對應 PM 拍板 | SD_08 PM #4（PG production SOP **延至 SD_09**；SD_08 W5 僅做前置 WAL lag adapter + 本 ADR 草案）|
| 提案人 | Architect / SD（雙方共識）|
| 核准日期 | 2026-05-18（SD_08 W0 T0-ADR5 草案；W5 G5 T5-H6 形式核准三項齊備）|

---

## 1. 背景

- SD_06 W3 §7.2 + PM W-1 紅線：⛔ Production 真正上線前必須由**人類 DBA**在公司 staging（≥ 1M 真實列）重跑 dry-run + **人類 PM** 親簽 release approval
- SD_06 W3 已完成 AI-Agent 三方模擬演練（DBA-Agent / Tech-Lead-Agent / PM-Agent 三方簽核 2026-05-17，演練紀錄於 `SD06_FK_DryRun_Report.md`）
- **Architect 警示**：若 SD_08 未鎖死 dual-state drift 觀測閾值，SD_09 將無「客觀切換條件」可依，極易因業務壓力而提前切換造成資料不可逆汙染

## 2. 決議

### 2.1 雙軌制定義（互補非互斥）

| 軌道 | 性質 | 主導角色 | 完成時機 |
|------|------|---------|---------|
| **(1) AI-Agent 演練**（已 SD_06 W3 完成）| 自動化、可重跑、回退劇本驗證 | DBA-Agent / Tech-Lead-Agent / PM-Agent 三方 | ✅ **2026-05-17** |
| **(2) 人類 DBA 親簽**（待 SD_09 觸發）| 業務責任歸屬、不可省 | **人類 DBA + 人類 PM** | ⏳ SD_09 W?? |

**邏輯關係**：AI-Agent 演練是人類簽核的**前置必要條件**（不可省的暖機 + 演練紀錄），但 AI-Agent 演練本身**無法替代**人類簽核（業務責任 + 法律歸屬）。

### 2.2 SD_09 啟用雙條件（不可逆轉折點）

PG production 從 `both`（File 主 + PG 影）切換至 `db_only`（PG 主，不可逆）需**同時**滿足：

| 條件 | 量測指標 | 通過門檻 | 量測檔 |
|------|---------|---------|--------|
| **(a) 可觀測性 GA** | IObservabilityPort + LocalLogger + 4 KB metric + trace_id 端對端 | ADR-SD08-004 W4 完成 + 30 天無 trace_id 斷鏈事件 | `tests/integration/test_observability_e2e.py`（SD_09 新建）|
| **(b) 30 天零 drift** | `drift_log` 連續 30 天 = 0 事件（含 datetime/UUID/Enum/set 4 種正規化）| `SELECT count(*) FROM drift_log WHERE detected_at > NOW() - INTERVAL '30 days'` = 0 | `tools/drift_log_zero_check.py`（SD_09 新建）|

**任一條件未達 → SD_09 不可啟動 db_only 切換**。

### 2.3 SD_08 W5 前置交付（本 ADR 落地）

SD_08 W5 強制交付 3 項，作為 SD_09 啟用前置：

| 交付項 | 檔案 | 用途 |
|--------|------|------|
| **(i) WAL lag adapter** | `autoclaude/infra/observability/pg_health.py` | `PgHealthMonitor.get_wal_lag_seconds()` / `get_active_connections()` — 告警 lag > 2s warn / > 10s critical |
| **(ii) 本 ADR 草案** | `docs/04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md` | 明文 SD_09 啟用條件 + 雙軌制定義 |
| **(iii) Production_Migration_SOP.md 草案** | `docs/08_deployment/Production_Migration_SOP.md` §1-§3 | yaml_only → both → db_only 灰度推進步驟（SD_09 補完 §4-§8）|

### 2.4 WAL lag adapter 設計

```python
# autoclaude/infra/observability/pg_health.py（W5 落地）
from typing import Protocol

class PgHealthMonitor(Protocol):
    async def get_wal_lag_seconds(self) -> float:
        """查詢 pg_last_wal_replay_lsn() 計算 replication lag。"""

    async def get_active_connections(self) -> int:
        """查詢 pg_stat_activity 統計目前 active 連線。"""

class DefaultPgHealthMonitor:
    async def get_wal_lag_seconds(self) -> float:
        query = """
            SELECT EXTRACT(EPOCH FROM (NOW() - pg_last_xact_replay_timestamp()))
            AS lag_seconds
        """
        # ...
```

**告警閾值**：

| 閾值 | 等級 | CI / metric 行為 |
|------|------|------------------|
| **lag < 2s** | 🟢 正常 | 無動作 |
| **2s ≤ lag < 10s** | 🟡 警告 | emit_counter("pg_wal_lag_warn") + log warning |
| **lag ≥ 10s** | 🔴 critical | emit_counter("pg_wal_lag_critical") + 告警通道 + 觸發降級至 yaml_only |

**lag > 2s warn**：取自 SD_06 W5 既有 dual_state reconcile drain SLA。

### 2.5 風險覆蓋優先順序（Architect 共識）

| 優先 | 風險 | 影響 | SD_08 W5 涵蓋 |
|------|------|------|---------------|
| **1（高）** | WAL replication lag | RPO（資料遺失視窗）| ✅ WAL lag adapter |
| **2（中）** | 雲端 IOPS 配額 | 可用性 | ⏳ SD_09 補完（含 cloud provider 監控整合）|
| **3（低）** | 並發負載 | 可由 advisory lock 緩解（SD_06 W4 已預埋）| ⏳ SD_09 補完（locust 100→500→1000 三階梯）|

### 2.6 灰度推進 SOP 雛形（Production_Migration_SOP.md §1-§3 草案）

```
§1. 前置確認（SD_08 W5 落地）
  [  ] AI-Agent 演練紀錄 ≥ 1 次（SD_06 W3 完成 ✅）
  [  ] WAL lag adapter 就位 ≤ 2s warn / ≤ 10s critical（SD_08 W5）
  [  ] ADR-SD08-005 PM 形式核准（SD_08 W5）

§2. yaml_only → both（staging 灰度啟動）
  [  ] config.mode = "both" + dual_write_strict = "fail_loud"
  [  ] 連續 7 天 drift_log = 0 事件
  [  ] reconcile_queue depth p95 < 10

§3. both → db_only（production 切換，不可逆）— 待 SD_09 補完
  [  ] **雙條件確認**：可觀測性 GA + 30 天零 drift
  [  ] 人類 DBA staging 跑 ≥ 1M 真實列 dry-run + 親簽
  [  ] 人類 PM release approval
  [  ] config.mode = "db_only" + 監控 24h smoke + rollback plan ready
```

## 3. 落地 Checklist（W5 task breakdown）

```
[  ] T5-H1 新建 autoclaude/infra/observability/__init__.py
[  ] T5-H2 新建 autoclaude/infra/observability/pg_health.py（PgHealthMonitor Protocol + DefaultPgHealthMonitor 實作）
[  ] T5-H3 PgHealthMonitor 透過 IObservabilityPort emit_counter("pg_wal_lag_warn") / emit_counter("pg_wal_lag_critical")
[  ] T5-H4 補 tests/infra/test_pg_health.py（≥ 5 case：lag < 2s 正常 / 2-10s warn / > 10s critical / connection count / fixture mock pg）
[  ] T5-H5 新建 docs/08_deployment/Production_Migration_SOP.md §1-§3 草案
[  ] T5-H6 本 ADR-SD08-005 PM 形式核准（W5 G5 簽核紀錄）
[  ] T5-H7 補 tests/contract/test_pg_migration_sop_dry_run.py（≥ 2 case：§1 前置確認 checklist 全綠 / §2 灰度啟動 dual_write_strict）
```

## 4. 退化風險緩解（連動 R-SD08-H-1 / R-SD08-PM-#4）

| 風險 | 緩解 |
|------|------|
| SD_08 未鎖死 drift 觀測閾值，SD_09 無客觀切換條件 | §2.2 明文「30 天零 drift」量測指標 + 量測檔 |
| SD_09 啟動時人類 DBA / PM 簽核流程不明 | §2.6 SOP §3 明文「人類 DBA staging ≥ 1M 真實列 dry-run + 親簽」+「人類 PM release approval」|
| 業務壓力下提前切換 db_only 造成資料不可逆汙染 | §2.2 雙條件同時達成 + §2.4 lag ≥ 10s critical 自動降級至 yaml_only |
| W5 ADR-SD08-005 草案落空，SD_09 啟動條件不明 | R-SD08-PM-#4：W5 強制交付 3 項（WAL lag adapter / 本 ADR / SOP §1-§3 草案）|

## 5. SD_09 啟用觸發條件（最終決議）

SD_09 PG production 切換 sprint 啟動需**同時滿足**：

1. ✅ SD_08 W4 可觀測性 GA（IObservabilityPort + LocalLogger + 4 KB metric + trace_id 端對端）
2. ✅ SD_08 W5 WAL lag adapter 就位
3. ✅ both mode staging 部署 ≥ 30 天連續零 drift 事件
4. ⏳ 業務層產生 production 切換需求（如真實業務量上線）
5. ⏳ 公司 DBA / PM 資源 ≥ 4 PD 可投入

任一未達 → SD_09 不啟動，由本 ADR 標 `DEFERRED` 並重新評估。

## 6. 簽核

| 角色 | 狀態 | 日期 |
|------|------|------|
| Architect | ✅ 共識（議題 3 推薦 b 延 SD_09）| 2026-05-18 |
| SD | ✅ 共識（WAL lag adapter 實作就緒）| 2026-05-18 |
| PM | ✅ 形式核准 framework（場景 A 個人開發 dev 自核）| 2026-05-18 |
| 人類 DBA | ⏳ SD_09 啟動時最終簽核（紅線：staging ≥ 1M 真實列重跑）| — |
| 人類 PM | ⏳ SD_09 production release 親簽 | — |

---

**相關文件**：
- [SD_Improving_08.md](../SD_Improving_08.md) v1.0 §6 PM 拍板 #4 + §7 三方意見
- [Phase6_PG_Stakeholder_Signoff.md](../../08_deployment/Phase6_PG_Stakeholder_Signoff.md) — SD_06 W3 簽核紀錄
- [SD06_FK_DryRun_Report.md](../../08_deployment/SD06_FK_DryRun_Report.md) — AI-Agent 三方演練紀錄（2026-05-17）
- [risk_log.md §8](../../05_development/risk_log.md) R-P6-04 — Production 上線前四方重新審查
