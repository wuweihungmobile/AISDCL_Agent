# SD09 軸 D 預備研究整合報告（#1 SOP §6-§8 / #2 kb_metric port / #3 trace_id mapping）

| 項目 | 內容 |
|------|------|
| 文件狀態 | **v0.1 預研（軸 D，不重置觀察期；不碰紅線區 §3.0.3）** |
| 對應軸 | 軸 D — W2-W6 預備研究（[SD09_Execution_Guide.md §3.0.1](../05_development/SD09_Execution_Guide.md)）|
| 涵蓋項目 | #1 SOP §6-§8 結構預研 / #2 kb_metric_store port 設計 / #3 trace_id mapping 9 處注入點驗證 |
| 建立日期 | 2026-05-28（R41 軸 D 預研）|
| 安全區聲明 | 本文件僅 docs/ 寫入（§3.0.4 並行安全區）；不動 token_guard / alembic / nightly 採集鏈 / 升級判定工具 |

> **軸 D #4 perf machine** 採購評估獨立於 [SD09_Perf_Machine_Procurement_Eval.md](SD09_Perf_Machine_Procurement_Eval.md)。

---

## A. 軸 D #3 — trace_id multi-process 9 處注入點 mapping 驗證（W3 T3-F2b）

> **結論：9/9 注入點已實作覆蓋**（非僅 mapping）。`autoclaude/utils/trace_context.py` W3C helper（`to_traceparent_header` / `from_traceparent_header` / `propagate_to_subprocess_env`，L136-217）就位。本節為 zero-trust 驗證紀錄。

| # | 注入點（ADR-SD09-004 §2.3）| 實作方式 | 證據 file:line |
|---|------|---------|---------------|
| 1 | perception/pty_wrapper.py | 直接呼叫 `propagate_to_subprocess_env(dict(os.environ))` | pty_wrapper.py:17, 71 |
| 2 | execution/cross_step_validator.py | 同上 | cross_step_validator.py:14, 46 |
| 3 | execution/pre_run_validator.py | 同上 | pre_run_validator.py:19, 89 |
| 4 | execution/evaluator.py | 同上 | evaluator.py:11, 39 |
| 5 | execution/mutation_applier/_conditional.py | 同上 | _conditional.py:13, 40 |
| 6 | plugins/fast_path_plugin.py | **plugin 邊界**：本地 `_propagate_trace_env()` 回 `dict(os.environ)`，繼承上層已注入 env（Rule 7 禁 import trace_context）| fast_path_plugin.py:35-43, 70 |
| 7 | plugins/token_guard/git_verifier.py | 同 #6 plugin 邊界 helper | git_verifier.py:13-20, 46 |
| 8 | decision/prompt_builder.py | 直接呼叫 `propagate_to_subprocess_env(dict(os.environ))` | prompt_builder.py:11, 139 |
| 9 | core/services/mutation/_conditional_evaluator.py | 同上 | _conditional_evaluator.py:18, 46 |

**設計正確性驗證**：
- 7 個非 plugin 點直接 import + 呼叫 helper（W3C TRACEPARENT + AUTOCLAUDE_TRACE_ID 雙寫，caller 已設 TRACEPARENT 時不覆蓋 — trace_context.py:214-216）。
- 2 個 plugin 點（#6/#7）受 importlinter Rule 7 約束**不可** import trace_context，改以本地 `_propagate_trace_env()` 繼承 os.environ 中上層已注入的 trace_id → 邊界正確、無違規。
- W3 殘留交付（不在軸 D 範圍，仍受閘門）：T3-F4b `tests/utils/test_trace_context_subprocess_env.py` W3C 區段擴充 + T3-F5b `tests/contract/test_trace_context_plugin_isolation.py`（紅線 ❌23-B）。

**軸 D #3 判定**：✅ mapping 完成 + 實作就位；W3 正式 Wave 僅需補測試覆蓋（受觀察期閘門）。

---

## B. 軸 D #2 — kb_metric_store port 設計（W2 T2-G1，議題 G 路徑 (a)）

> 設計 SSOT 為 [ADR-SD09-006](../04_planning/ADR/ADR-SD09-006-kb-metric-port.md) ACCEPTED。本節為 W2 turnkey 落地清單 + **命名漂移修復決議**。

### B.1 命名漂移修復決議（R41 軸 D 預研發現）

| 來源 | 介面名 | 檔名 |
|------|--------|------|
| ADR-SD09-006 §2.1（草案）| `IObservabilityMetricStore` | `observability_metric_store.py` |
| Execution Guide T2-G1 / G2 驗證 / R40 NextAction / 用戶 | `IKbMetricStore` | `kb_metric_store.py` |

**決議：以 `kb_metric_store.py` / `IKbMetricStore` 為 canonical**。理由：(1) Execution Guide T2-G1 實作任務 + G2 驗證 grep 皆用此名；(2) R40 NextAction §5 + 用戶口徑一致；(3) 語意更精確（KB metric 專用，非泛 observability）；(4) SD-C4 原改名歸 observability 之「避免與 memory_store 衝突」理由不成立（`kb_metric_store` 與 `memory_store` 實際無衝突）。`observability_metric_store` 標記為 deprecated 草案別名。

**全檔同步修正範圍（R41 四方 audit 後完整收尾）**：ADR-SD09-006（標題 / §W0-W2 範圍 / §1 背景 / §2.1 / §2.4 forbidden_modules+rule name / §2.5 Snapshot）+ SD_Improving_09.md（§評估方向 (a) / port spec 草案 / ADR 條目 / 議題 G 收尾）+ SD09_AC_Matrix.md（AC16 描述）。**歷史審查紀錄**（gate_audit.md §SD / SD09_Pre_W0_Audit_Findings.md F-10）保留原 review 當時名稱不追溯竄改（凍結史料）。

### B.2 W2 落地 turnkey 清單（受觀察期閘門，不在軸 D 實作範圍）

```
[ ] autoclaude/core/ports/kb_metric_store.py — IKbMetricStore Protocol（ADR §2.1 簽名）
[ ] autoclaude/infra/adapters/local_kb_metric_store.py — LocalKbMetricStore（yaml_only fallback）
[ ] autoclaude/infra/adapters/pg_kb_metric_store.py — PgKbMetricStore（both/db_only）
[ ] alembic/versions/0015_kb_metrics.py — kb_metrics 表（ADR §2.3 schema）⚠️ 觸碰 alembic = 紅線區（延 W2）
[ ] factory.py 路由（對齊 storage.mode 三後端）
[ ] importlinter Rule 8 — plugin 禁直接 import（ADR §2.4；7→8 kept）
[ ] Snapshot port 列表 9→10（snapshot_sync.py 自動）
[ ] tests/contract/test_kb_metric_persistence.py（≥ 4 case：雙 adapter 切換 / yaml_only fallback / 寫入 / 跨 session 讀取）
```

**軸 D #2 判定**：✅ 設計 SSOT 完備（ADR-SD09-006）+ 命名漂移修復；W2 落地清單就緒（含 alembic 紅線標註延 W2）。

---

## C. 軸 D #1 — Production_Migration_SOP §6-§8 結構預研骨架（W4 T4-A2~A4）

> 現況：`Production_Migration_SOP.md` §4–§8 為單一 placeholder（line 120）。本節為 §6-§8 結構骨架（DBA RACI 草案 / 監控儀表板路徑 / 演練 checklist 骨架），供 W4 填實。**不在 SOP 正文預寫**以免誤判 W4 已完成（閘門紀律）。

### §6 監控（W4 T4-A2 填實）骨架
- WAL lag dashboard（PgHealthMonitor 三閾值 NORMAL/WARNING/CRITICAL）→ 儀表板路徑 placeholder
- 連線數 alert（連線數異常觸發回滾條件之一，ADR-SD09-005 §2.2）
- drift_log 30 天零事件 SLA（`severity != 'info'` 計數 — 對齊 alembic 0013 真實 schema）
- 監控資料來源：`tools/observability_ga_check.py`（`.observability_history.jsonl`）

### §7 RACI 表草案（W4 T4-A3 填實）
| 活動 | DBA | SRE | Tech Lead | PM |
|------|-----|-----|-----------|-----|
| 三階梯 canary 切換（10/50/100）| R/A | C | C | I |
| WAL lag 監控 | R | A | I | I |
| 緊急回滾（rollback SLA 自動 ≤3min + 取證 ≤30min，Arch-M4）| R/A | C | I | I |
| 雙條件齊備驗證 | C | I | R/A | C |
| release approval 親簽 | I | I | C | R/A |

### §8 演練回顧 checklist 骨架（W4 T4-A4 填實）
```
[ ] W3 AI-Agent dry-run（≥1M 列）整合紀錄
[ ] DBA 親演 §4 三階梯 canary 逐階 sign-off
[ ] DBA 親驗 §5 rollback（含 PG dump → YAML import）
[ ] 30 天觀察期統計彙整（#3 drift 零事件）
[ ] checklist 簽核 → SD09_DBA_DryRun_Sign_W4.md
```

**軸 D #1 判定**：✅ §6-§8 結構骨架就緒（RACI + 監控路徑 + checklist）；W4 正式 Wave 填實（受 DBA 親演閘門 ❌21）。

---

## D. 軸 D 預研總結

| 項 | 狀態 | W 正式 Wave 殘留（受閘門）|
|----|------|------------------------|
| #1 SOP §6-§8 骨架 | ✅ 預研完成 | W4 填實 + DBA 親演（❌21）|
| #2 kb_metric port 設計 | ✅ 設計完備 + 命名修復 | W2 Protocol/adapter/alembic 落地 |
| #3 trace_id 9 處 mapping | ✅ 已實作 + 驗證 | W3 補測試覆蓋（❌23-B）|
| #4 perf machine 採購 | ✅ 骨架（獨立文件）| W2 PM 預算簽核（❌22）|

**軸 D 不重置任何觀察期**：本輪純 docs/ 寫入 + ADR/Guide 命名對齊，零源碼異動，零採集鏈異動。

---

**文檔元數據**：v0.1 預研 | 建立 2026-05-28（R41 軸 D #1/#2/#3）| 維護者：Tech Lead
