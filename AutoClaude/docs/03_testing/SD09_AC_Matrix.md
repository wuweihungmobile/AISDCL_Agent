# SD_Improving_09 AC Matrix（W0 v1.0；SD_07 19 + SD_08 10 + SD_09 動態 12 = 41 條）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0 PM 拍板 (b) finalized 2026-05-20（W0 task list 22/22 CLOSED + 五方終審 APPROVED）** |
| 建立日期 | 2026-05-19 |
| 對應規劃 | [SD_Improving_09.md](../04_planning/SD_Improving_09.md) v1.0 + [SD09_Execution_Guide.md](../05_development/SD09_Execution_Guide.md) v1.0 |
| 依據 | SD_07 19 條（[SD07_AC_Matrix.md](SD07_AC_Matrix.md)）+ SD_08 10 條繼承（[SD08_AC_Matrix.md](SD08_AC_Matrix.md)）+ SD_09 動態 12 條 = **合計 41 條（PM 拍板 (b) finalized）≥ 35 門檻 ✅** |
| W0 預檢基線 | 主規劃 §1.4 W0 實測 **2,403 passed / 122 skipped**（W0 補測落地，較 SD_08 W6 G6 末 2,094 +309）；W6 軟目標 **≥ 2,420** / 硬底線 **≥ 2,410** |

---

## 0. SD_07 / SD_08 繼承（共 29 條）

| 來源 | 條目數 | link |
|------|--------|------|
| SD_07 AC | 19 條（AC0×3 + AC1×3 + AC2×2 + AC3×2 + AC4×2 + AC5×3 + AC6×3 + AC-LOC-1）| [SD07_AC_Matrix.md](SD07_AC_Matrix.md) |
| SD_08 AC | 10 條（AC4×2 + AC7×3 + AC8×2 + AC9×2 + AC10×1 + AC-LOC×2 = 12 列；其中 AC-LOC×2 為 SD_07 AC-LOC-1 延伸，**淨增 10 條**）| [SD08_AC_Matrix.md](SD08_AC_Matrix.md) |
| **合計** | **29 條基底** | — |

> **繼承規則**：SD_07 / SD_08 AC 持續沿用，W0~W6 各 Gate 仍須通過；本表新增 AC-SD09-* 為 SD_09 議題 A~G 量身訂做。

---

## 1. SD_09 議題對應與覆蓋表

| 議題 | AC 編號 | Wave | 阻塞門 | PM 路徑依賴 |
|------|---------|------|--------|--------------|
| A — PG production SOP 完整啟用 | AC-SD09-01 ~ AC-SD09-05 | W3~W5 | G3/G4/G5 | 啟動雙條件齊備 |
| B — mutation pilot 擴展 | AC-SD09-06 ~ AC-SD09-07 | W1~W2 | G1/G2 | TG 退出/鎖定 |
| C — AC4 labeled PR 觸發升級 | AC-SD09-08 | W0 | G0 | 觀察期 #2 ready_for_labeled_pr=true |
| D — perf machine 採購評估與啟用 | AC-SD09-09 ~ AC-SD09-10 | W2/W4 | G2/G4 | PM #3 預算簽核 |
| E — CLAUDE.md 滾動下沉維護 | AC-SD09-11 | W0/W6 | G0/G6 | — |
| F — trace_id multi-process 邊界 | AC-SD09-12 | W0/W3 | G0/G3 | PM #4 三選項 (a)/(b)/(c) |
| G — KB metric 落地 | AC-SD09-13 ~ AC-SD09-14 | W0/W2~W3 | G0/G2/G3 | PM #5 (a)/(b)/(c) |
| W0 zero-trust audit P0 修補 | AC-SD09-15 ~ AC-SD09-16 | W0 | G0 | 必做 |

---

## 2. AC 詳表（SD_09 動態條目）

### AC-SD09-01：PG production SOP §4-§5 補完（議題 A / Wave W3）

| 欄位 | 內容 |
|------|------|
| 描述 | `Production_Migration_SOP.md` §4 canary 三階梯時序 + §5 rollback 範本 + PG dump → YAML import script |
| 對應 test 檔 | `tests/contract/test_pg_production_sop_section_4_5.py`（≥ 6 case 綠：canary 三階梯 / rollback SQL / drift_log 取證 / dump→yaml roundtrip / 業務不可逆語意 / RACI 矩陣完整） |
| 驗收門檻 | 6/6 PASSED + `Production_Migration_SOP.md` 行數 ≥ 200（含 §4-§5）+ `tools/pg_dump_to_yaml.py` 落地 |
| 對應 ADR | [ADR-SD09-001](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) §2.3 / [ADR-SD09-005](../04_planning/ADR/ADR-SD09-005-pg-canary-stage-thresholds.md) |

### AC-SD09-02：PG production SOP §6-§8 補完 + DBA 親演（議題 A / Wave W4）

| 欄位 | 內容 |
|------|------|
| 描述 | SOP §6 監控 dashboard（WAL lag / 連線數 / drift 計數）+ §7 RACI + §8 演練回顧；人類 DBA 親演 + 簽核 `SD09_DBA_DryRun_Sign_W4.md` |
| 對應 test 檔 | `tests/contract/test_pg_production_sop_section_6_8.py`（≥ 6 case 綠：dashboard config / RACI 完整 / 演練回顧模板 / DBA signed-off 驗證 / pg_health 三閾值串接 / SD09_DBA_DryRun_Sign_W4 schema） |
| 驗收門檻 | 6/6 PASSED + DBA signed-off（GPG / 平台徽章）+ AI-Agent dry-run（≥ 1M 列）成功 |
| 對應 ADR | ADR-SD09-001 §2.3 紅線 ❌21 + [ADR-SD08-005](../04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md) |

### AC-SD09-03：真實 PG production 上線雙條件驗證（議題 A / Wave W5）

| 欄位 | 內容 |
|------|------|
| 描述 | 條件 1a（IObservabilityPort + trace_id ContextVar 30 天 nightly 全綠）+ 條件 1b（KB metric 觀察）+ 條件 2（drift_log 30 天零事件）齊備驗證 |
| 對應 test 檔 | `tests/contract/test_cutover_precondition_w5.py`（≥ 4 case 綠：1a 取證 / 1b 三路徑分流 / 條件 2 SQL / 三條件 AND 邏輯） |
| 驗收門檻 | 4/4 PASSED + `python tools/observability_ga_check.py --window 30 --json` 回報 `green_streak >= 30` + drift_log SQL `count=0` + `SD09_Cutover_Precondition_Check_W5.md` 落地 |
| 對應 ADR | ADR-SD09-001 §2.2（雙條件分拆 1a/1b 修復）|

### AC-SD09-04：PG canary 三階梯閾值執行（議題 A / Wave W5）

| 欄位 | 內容 |
|------|------|
| 描述 | 10%/24h + 50%/48h + 100%/7d 三階梯切換；三觸發回滾條件（drift severity != info / WAL lag CRITICAL / 連線數異常）；自動回退 ≤ 3 min + 取證歸檔 ≤ 30 min |
| 對應 test 檔 | `tests/contract/test_pg_canary_stages.py`（≥ 5 case 綠：階梯 10%→50% / 50%→100% / 三觸發 race condition / 自動 rollback SLA / 取證 SLA） |
| 驗收門檻 | 5/5 PASSED + canary 三階梯實際執行紀錄 |
| 對應 ADR | ADR-SD09-005 §2.2 + §2.3（rollback SLA 拆兩段 Arch-M4 修復）|

### AC-SD09-05：人類 PM 親簽 release approval（議題 A / Wave W5）

| 欄位 | 內容 |
|------|------|
| 描述 | W5 切換前 PM 親簽 `SD09_PM_Release_Approval_W5.md`（signed-off / GPG）；紅線 ❌21 三項齊備之三 |
| 對應 test 檔 | `tests/contract/test_pm_release_approval_schema.py`（≥ 2 case 綠：schema 完整 / signed-off 驗證） |
| 驗收門檻 | 2/2 PASSED + `SD09_PM_Release_Approval_W5.md` 落地（GPG-verified） |
| 對應 ADR | ADR-SD09-001 §2.3 紅線 ❌21 第 3 項 |

### AC-SD09-06：GoalSynthesisPlugin mutation pilot ≥ 65%（議題 B / Wave W1）

| 欄位 | 內容 |
|------|------|
| 描述 | GoalSynthesisPlugin mutation pilot 兩週連續達 ≥ 65% kill rate；TG 退出 nightly 改週 baseline 抽測 |
| 對應 test 檔 | `tests/contract/test_mutation_baseline_lock.py`（GS 模組 ≥ 4 case 補入） + `.mutation_baseline.toml [scores.goal_synthesis_plugin]` 鎖定值 |
| 驗收門檻 | mutation kill rate ≥ 65% 連續 7 次 + `.mutation_baseline.toml` 寫入 + Report 落地（SD09_Mutation_GoalSynthesis_Report.md） |
| 對應 ADR | [ADR-SD09-002](../04_planning/ADR/ADR-SD09-002-mutation-full-module-expansion.md) §2.1.1 + §2.3 |

### AC-SD09-07：OrchestrationCoordinator mutation pilot ≥ 60%（議題 B / Wave W2）

| 欄位 | 內容 |
|------|------|
| 描述 | Coordinator 單檔精準 `--paths-to-mutate=autoclaude/core/orchestration/coordinator.py` 兩週 ≥ 60%（GS 鎖定後立即進入，**禁止並行** R-SD09-B-2）|
| 對應 test 檔 | `tests/contract/test_mutation_baseline_lock.py`（Coordinator 模組 ≥ 4 case 補入）|
| 驗收門檻 | mutation kill rate ≥ 60% 連續 7 次 + `.mutation_baseline.toml` 寫入 + Report 落地 |
| 對應 ADR | ADR-SD09-002 §2.4（單檔精準）+ §2.6（nightly 超時護欄）|

### AC-SD09-08：AC4 labeled PR 觸發啟用（議題 C / Wave W0）

| 欄位 | 內容 |
|------|------|
| 描述 | 觀察期 #2 達標（`ready_for_labeled_pr=true`）後啟用 `pg-e2e-on-label.yml` workflow（dormant → active）|
| 對應 test 檔 | `tests/contract/test_ac4_progress_check.py`（既有 6 case + 新增 ≥ 2 case：labeled PR 啟用 / 黃線紅線告警）|
| 驗收門檻 | `tools/ac4_progress_check.py --json` 回報 `ready_for_labeled_pr=true` + workflow `on: pull_request labeled` 啟用 + 1 次成功 labeled PR run |
| 阻塞 | 觀察期 #2 阻塞於 `tools/seed_kb.py` 缺實作 + `test_pgvector_real_recall.py` 3 case `pytest.skip` 硬編碼（R-SD09-CI-2）|

### AC-SD09-09：perf machine 採購評估報告 + PM 預算簽核（議題 D / Wave W2）

| 欄位 | 內容 |
|------|------|
| 描述 | 採購評估報告（CPU bare metal vs 雲端 GPU instance vs $200/月租用三方案比較）+ 季度校準 schedule + PM 預算簽核（commit signed-off）|
| 對應 test 檔 | `tests/contract/test_perf_machine_procurement.py`（≥ 3 case 綠：採購報告 schema / PM 簽核驗證 / 季度校準排程）|
| 驗收門檻 | 3/3 PASSED + 採購報告落地 + PM 簽核 commit |
| 對應 ADR | [ADR-SD09-003](../04_planning/ADR/ADR-SD09-003-perf-three-track.md) + 緊急路徑 |

### AC-SD09-10：perf machine 上架 + pgvector baseline 鎖定（議題 D / Wave W4）

| 欄位 | 內容 |
|------|------|
| 描述 | perf machine 上架 self-hosted runner + `@pytest.mark.perf_machine_only` marker 啟用 + `.perf_baseline.toml` 補入 `pgvector_recall_perf` 鎖定值；季度校準首跑 7 次 |
| 對應 test 檔 | `tests/perf/test_pgvector_recall_perf.py`（marker 對齊 `pyproject.toml [tool.pytest.ini_options]`）+ `tests/contract/test_perf_three_track.py`（≥ 3 case 綠）|
| 驗收門檻 | pgvector p95 baseline 鎖定 + 3/3 contract PASSED + p95 < 50ms（AC4-2 對齊） |
| 對應 ADR | ADR-SD09-003 §2.2（marker pyproject.toml 配置）|

### AC-SD09-11：sprint_history.md §1.5 SD_07 擴寫至 ≥ 300 行（議題 E / Wave W6）

| 欄位 | 內容 |
|------|------|
| 描述 | sprint_history.md §1.5 SD_07 擴寫為完整 W0~W6 紀錄（≥ 300 行，仿 §1.4 SD_06 200+ 行格式）；CLAUDE.md 維持單行 link；wc -l CLAUDE.md ≤ 400 |
| 對應 test 檔 | `tests/contract/test_claude_md_budget.py`（既有 16 case）+ `tests/contract/test_sprint_history_section_lines.py`（≥ 2 case 綠：§1.5 ≥ 300 行 / awk 排除空白行）|
| 驗收門檻 | `awk '/^### 1\.5/,/^### 1\.6/' sprint_history.md | grep -cv '^$' >= 300` + CLAUDE.md ≤ 400 + 16+2 contract PASSED |
| 對應 ADR | [ADR-SD08-001](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) 滾動下沉延續 |

### AC-SD09-12：trace_id multi-process 邊界傳播（議題 F / Wave W3，**動態條目**）

> **PM #4 路徑依賴**：(a) 環境變數 → AC16=2；(b) W3C TraceContext → AC16=3；(c) 延 SD_10 → AC16=1（延期決議紀錄）

#### 路徑 (a)：環境變數 `AUTOCLAUDE_TRACE_ID`

| 欄位 | 內容 |
|------|------|
| 描述 | `propagate_to_subprocess_env(env)` helper 內聚 `autoclaude/utils/trace_context.py`；9 處 subprocess 注入點統一呼叫；importlinter Rule 7 覆蓋 |
| 對應 test 檔 | `tests/utils/test_trace_context_subprocess.py`（≥ 3 case 綠：env 傳播 / 9 注入點覆蓋 / caller override 不覆蓋）|
| 驗收門檻 | 3/3 PASSED + 9 處檔案均呼叫 helper + `lint-imports --config .importlinter` Rule 7 kept |

#### 路徑 (b)：W3C TraceContext header（為 SD_10 OTel 過渡）

| 欄位 | 內容 |
|------|------|
| 描述 | 自建 W3C TraceContext parser 內聚 `trace_context.py`（不新建模組）；`TRACEPARENT` env 傳播；contract test 取代 importlinter Rule 8（Arch-M3 修復）|
| 對應 test 檔 | `tests/contract/test_trace_context_plugin_isolation.py`（≥ 2 case 綠 + 補 4 case：TRACEPARENT parser / 9 注入點覆蓋 / caller override 不覆蓋 / contract 替代 Rule 8）|
| 驗收門檻 | 4/4 PASSED + `trace_context.py` LOC ≤ 750 absolute_limit（contract tier 鎖 ≤ 400）+ 紅線 ❌23-A/B 不違反 |

#### 路徑 (c)：延 SD_10 OTel 整合一次處理

| 欄位 | 內容 |
|------|------|
| 描述 | W3 任務全刪；本 Sprint 不落地；議題群降級為 SD_10 backlog 評估報告 |
| 對應 test 檔 | （無；SD_10 backlog）|
| 驗收門檻 | `docs/04_planning/SD_Improving_10.md` 大綱 §F 條目（延期決議紀錄）|

### AC-SD09-13：KB metric 落地（議題 G / Wave W2~W3，**動態條目**）

> **PM #5 路徑依賴**：(a) PG kb_metrics 表 → AC13/14 共 2 條；(b) 刪除 → AC13/14 全刪；(c) 延 SD_10 → AC13/14 全刪

#### 路徑 (a)：PG kb_metrics 表 + alembic 0015

| 欄位 | 內容 |
|------|------|
| 描述 | `IKbMetricStore` port + Pg adapter + alembic 0015 migration + nightly aggregation；yaml_only 模式 fall-back `LocalKbMetricStore` |
| 對應 test 檔 | `tests/contract/test_kb_metric_port.py`（≥ 4 case 綠：port spec / Pg adapter / Local fall-back / snapshot/flush/query_window 5 方法）|
| 驗收門檻 | 4/4 PASSED + alembic 0015 落地 + Snapshot Port 列表 9 → 10 對齊 |
| 對應 ADR | ADR-SD09-006（PM (a) 拍板後產出）+ 主規劃 §1.7 |

### AC-SD09-14：KB metric 跨 storage.mode 三後端孤兒驗證（議題 G / Wave W3，路徑 (a) 才適用）

| 欄位 | 內容 |
|------|------|
| 描述 | yaml_only / both / db_only 三模式切換時 metric 不孤兒；LocalKbMetricStore（in-memory or jsonl）正確路由 |
| 對應 test 檔 | `tests/integration/test_kb_metric_dual_state.py`（≥ 3 case 綠：三模式切換 / metric 不丟失 / jsonl roundtrip）|
| 驗收門檻 | 3/3 PASSED + R-SD09-G-1 緩解就位 |

### AC-SD09-15：W0 zero-trust audit P0 缺檔補建（議題 W0 強制 / Wave W0）

| 欄位 | 內容 |
|------|------|
| 描述 | F-01 ~ F-10 共 10 項缺檔補實作（observability_ga_check.py / seed_kb.py / pg_dump_to_yaml.py / drift_log_30day_zero.json fixture / fk_staging_1m_wrapper.py / SD09_DBA_DryRun_Sign_W4.md / SD09_PM_Release_Approval_W5.md / SD09_Cutover_Precondition_Check_W5.md / test_trace_context_plugin_isolation.py / ADR-SD09-006-kb-metric-port.md）|
| 對應 test 檔 | `tests/contract/test_w0_critical_files_present.py`（≥ 10 case 綠：每 F-* 一條 path 存在 + 非空 + 可執行（py）/ schema 對齊（md/json））|
| 驗收門檻 | 10/10 PASSED + 10 檔案落地（F-10 ADR-SD09-006 v1.0 ACCEPTED 已落地）|
| 對應風險 | R-SD09-O-1 / R-SD09-A-5 / R-SD09-CI-3（[risk_log.md §15](../05_development/risk_log.md)）|

### AC-SD09-16：W0 三方研究意見補完 + CI 驗證（議題 W0 強制 / Wave W0）

| 欄位 | 內容 |
|------|------|
| 描述 | 主規劃 §7 三方研究 **13 bullet（Arch 4 + SA 3 + SD 3 + QA 3）** 全填入實質內容 ≥ 50 字；新建 `tools/check_research_completion.py` 驗證；W0 G0 啟動前簽核引用 |
| 對應 test 檔 | `python tools/check_research_completion.py` exit 0 + `tests/contract/test_research_completion.py`（≥ 2 case 綠：**13 bullet** ≥ 50 字 / placeholder 殘留偵測）|
| 驗收門檻 | **13/13 bullet** ≥ 50 字 + `tools/check_research_completion.py` exit 0 + 2/2 contract PASSED |
| 對應 audit | M-06（[SD09_Pre_W0_Audit_Findings.md](../05_development/SD09_Pre_W0_Audit_Findings.md) §2）|

---

## 3. 動態條目總計（PM 拍板 (b) 後單一路徑 v1.0）

| 路徑 | F (議題 F) | G (議題 G) | SD_09 動態條目數 | 累計 AC 數 |
|------|-----------|-----------|-----------------|-----------|
| **(b) — PM #4 拍板 finalized 2026-05-20** | F=b W3C TraceContext header parser | G=a PG kb_metrics 落地 | 13 條 | **41 條（29 + 12）≥ 35 門檻 ✅** |

> **PM 拍板 (b) finalized 2026-05-20**：路徑 (a) 環境變數 / (c) 延 SD_10 已被否決；本表已收斂為單一路徑 v1.0。AC-SD09-12 採路徑 (b) W3C TraceContext parser 4 case；AC-SD09-13/14 採路徑 (a) PG kb_metrics 落地。詳見 [ADR-SD09-004 v1.0](../04_planning/ADR/ADR-SD09-004-trace-id-multi-process.md) + [ADR-SD09-006 v1.0](../04_planning/ADR/ADR-SD09-006-kb-metric-port.md)。

> **澄清 SA-C1 修復**：PM 拍板 (b) 後本表已收斂為單一路徑 v1.0；歷史三路徑骨架評估保留於 §3.A 附錄供決策追溯。

---

## 3.A 附錄：PM 拍板前的路徑選項評估（歷史紀錄）

> **僅供決策追溯；v1.0 後本表非單一真相**。PM #4/#5 於 2026-05-20 拍板 (b) 路徑後此區段凍結。

| 路徑 | F (議題 F) | G (議題 G) | SD_09 動態條目數 | 累計 AC 數 |
|------|-----------|-----------|-----------------|-----------|
| **(a)** | F=a 環境變數（AC-SD09-12 路徑 a）| G=a PG 落地（AC-SD09-13 + AC-SD09-14）| 11 + 1 + 2 + 2 = 16 → 動態 **11 條** | **40 條**（29 + 11）|
| **(b) ✅ 採用** | F=b W3C（AC-SD09-12 路徑 b，AC16=3）| G=a PG 落地（AC-SD09-13 + AC-SD09-14）| 動態 **12 條**（含 AC16=3 W3C parser 4 case）| **41 條**（29 + 12）|
| **(c)** | F=c 延 SD_10（AC-SD09-12 路徑 c，AC16=1）| G=b/c 刪除或延（AC-SD09-13 + AC-SD09-14 全刪）| 動態 **10 條**（AC16=1 延期決議紀錄；G 條目全刪 -2）| **39 條**（29 + 10）|

> **歷史對應主規劃 §2 footer 三路徑敏感性**：
> - 路徑 (a)：W6 ≥ 2,125；累計 AC 40 條
> - 路徑 (b)：W6 ≥ 2,126；累計 AC 41 條（含 AC16=3 W3C TraceContext header parser）✅ 採用
> - 路徑 (c)：W6 ≥ 2,122；累計 AC 39 條（AC16=1）
> - **最壞情境**：F=c + G=b/c → 累計 39 條（仍 ≥ 35 門檻 ✅）

---

## 4. 阻塞 / 非阻塞 規則

| 嚴重度 | 行為 |
|--------|------|
| 🔴 阻塞 | Critical AC 任一 fail → 對應 Gate 不放行（git revert） |
| 🟠 警示 | mutation kill rate fall-back（< 60% baseline）→ 議題 B 改 Report 補測 backlog，不阻塞 Gate |

**Critical AC**：AC-SD09-01~05（議題 A，紅線 ❌21）/ AC-SD09-15~16（W0 zero-trust）/ AC-SD09-03（雙條件齊備）

---

## 5. 維護規則

1. 每個 Wave G-Gate 通過後，在「實測」欄填入結果（`✅ passed (數字)` 或 `⚠️ 部分通過`）
2. PM #4/#5 路徑拍板後，本表「動態條目總計」收斂為單一路徑（39 / 40 / 41 擇一）
3. AC 與 [risk_log.md §15](../05_development/risk_log.md) 雙向映射（risk → mitigation AC）

---

## 6. 簽核（W0 G0 末五方終審 APPROVED 2026-05-20）

| 角色 | 狀態 | 日期 | 簽核摘要 |
|------|------|------|----------|
| Architect | ✅ APPROVED | 2026-05-20 | §7.1 4 bullet 填實；ADR-SD09-001~006 PM 形式核准；alembic 0015 merge revision 落地 |
| SA | ✅ APPROVED | 2026-05-20 | SA-C1 五欄拆分對齊；AC11×3 拆分；§7.2 3 bullet 填實 |
| SD | ✅ APPROVED | 2026-05-20 | 9 處 subprocess 注入點集中式 helper + drift_log SQL 對齊；§7.3 3 bullet 填實 |
| QA | ✅ APPROVED | 2026-05-20 | 35 條門檻單路徑 (b) 驗證可重現；observability_ga_check.py 182 LOC 落地；§7.4 3 bullet 填實 |
| PM | ✅ APPROVED | 2026-05-20 | PM 拍板 #1~#8 + X/Y/Z 三組新增齊備；六份 ADR 形式核准（場景 A dev 自核）|

> 對應 [gate_audit.md §1-septies SD09-G0](../05_development/gate_audit.md) 五方終審紀錄。

---

**相關文件**：
- [SD_Improving_09.md](../04_planning/SD_Improving_09.md) v0.4 — 主規劃
- [SD09_Execution_Guide.md](../05_development/SD09_Execution_Guide.md) — 執行計畫
- [SD09_Pre_W0_Audit_Findings.md](../05_development/SD09_Pre_W0_Audit_Findings.md) — zero-trust audit 落差清單
- [SD07_AC_Matrix.md](SD07_AC_Matrix.md) — SD_07 19 條 AC（前置基底）
- [SD08_AC_Matrix.md](SD08_AC_Matrix.md) — SD_08 10 條 AC（前置基底）
- [ADR-SD09-001](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) ~ [005](../04_planning/ADR/ADR-SD09-005-pg-canary-stage-thresholds.md)

---

**文檔元數據**：**v1.0** | 建立 2026-05-19（W0 zero-trust audit SA-C1 修復）| 升 v1.0 2026-05-20（PM 拍板 (b) finalized + W0 task list 22/22 CLOSED + 五方終審 APPROVED）| 場景 A 個人開發

### 版本紀錄

| 版本 | 日期 | 內容 |
|------|------|------|
| **v0.4** | **2026-05-19** | W0 zero-trust audit SA-C1 五欄拆分修復；三路徑骨架（39/40/41）展開待 PM 拍板 |
| **v1.0** | **2026-05-20** | PM 拍板 (b) finalized：F=b W3C TraceContext + G=a PG kb_metrics → 單一路徑 41 條收斂；§3 收斂 + §3.A 附錄保留歷史三路徑評估；§6 簽核表五方 APPROVED；AC-SD09-15 F-09→F-10；AC-SD09-16 12→13 bullet；W0 補測落地基線升至 2,403 / W6 軟目標 ≥ 2,420 / 硬底線 ≥ 2,410 |
