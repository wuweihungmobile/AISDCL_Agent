# SD_09 W0 啟動前 Zero-Trust Audit 落差清單（給 PM）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.5（W0 G0 預檢 + 五輪五方並行 zero-trust audit FULLY APPROVED-WITH-CONDITIONS；2026-05-20 最終核准）** |
| 建立日期 | 2026-05-19 |
| 最後更新 | **2026-05-20 v1.5**（**W0 G0 預檢通過 + 第五輪五方並行 zero-trust audit**：(1) **W0 G0 預檢四項全綠**：snapshot_sync --check OK / check_loc_budget violations=0 / pytest plugins+ac4_progress_check 316 passed / `.alembic_offline_head.txt=0014` marker 鎖定；(2) **PM**：§6 拍板 11 項齊備、§8.2 7✅/3⚠️/0🔴；(3) **Architect**：9 ports + 14 plugin + 7 importlinter rules + 6 ADR 全達標；(4) **SA**：AC Matrix 39/40/41 + §7 13 bullet ≥ 50 字達標；(5) **SD**：F-01~F-10 抽樣 8/8 LOC 達標 + B-09 CI 11 處 continue-on-error 全清 + M-04 9 處 subprocess 改造全到位 + N-05 5/5 + N-03 跨平台 PASS；(6) **QA**：2108 passed / 0 failed / 122 skipped（基線 2094 + 14）+ equivalence 83/83 + contract 395 passed + N-02 11/11。**新增發現 N-07/N-08**：(N-07) alembic multi-head `[0003_jsonb_gin_index, 0014_config_audit_log]` — 0003 為 SD_06 可選 JSONB GIN 分支（docstring 「目前非必要」），offline marker 不致命；W2 PG `alembic upgrade head` 前須 merge revision（登 R-SD09-A-6）；(N-08) `.mutation_history.jsonl` 不存在 — 觀察期 #1 起算點需 W0 啟動後重定錨。**補修 6 項**：P0-SA-01 (line 1/5/9 版本統一 v0.5) / P0-SA-02 (Execution_Guide 06-25→06-26) / P0-SA-03 (gate_audit + risk_log 啟動日窗口對齊) / P0-SA-04 (TaskBreakdown v0.2) / P0-PM-02 (Findings line 9 v0.4→v0.5) / P1-SD-02 (F-09 3 case→9 case)。**整體狀態**：21 Critical + 10 Major 全 CLOSED + 2 N-07/N-08 登錄）|
| 審查方 | **五輪 zero-trust audit：PM / Architect / SA / SD / QA 五方獨立並行**（general-purpose agent zero-trust mode；2026-05-20 第五輪 W0 G0 FULLY APPROVED-WITH-CONDITIONS）|
| 對應 | [SD_Improving_09.md v0.5](../04_planning/SD_Improving_09.md) + [SD09_Execution_Guide.md](SD09_Execution_Guide.md) |
| 觸發 | 使用者本地驗證 nightly 排程時揭露多項形式 vs 實質驗證落差，要求徹底完全不信任審查 |

---

## 0. TL;DR — meta 結論

**SD_05~SD_08 多輪「四方審查 APPROVED」「Gate 通過」實際上驗證了腳手架（scaffolding）運作，未驗證實質內容**。CI 上 `continue-on-error: true`（實測 9 次，文件層另外引用 2 處 step 內 ||true 掩護）+ `pytest.skip` 硬編碼 + 占位工具引用 共同掩護了缺口 6+ 個月。這不是「亂驗」，是**敏捷反模式**。

### 觀察期可達性結論

| # | 觀察期 | 描述 | 現況 | 阻塞根因 |
|---|--------|------|------|---------|
| #1 | mutation TG 連續 7 次 ≥ 70% | 🔴 結構性不可達 | mutmut 3.x Windows 不支援；`.mutation_history.jsonl` 不存在；`.mutation_baseline.toml [scores]` 空 |
| #2 | AC4 14 天 nightly 全綠 | 🔴 數學不可能 | test 硬編碼 skip + ac4_progress_check 把 skip 視同 fail；seed_kb.py 不存在 |
| #3 | drift_log 30 天零事件 | ⚠️ 形式可勾但無實質意義 | alembic 真實 head=0014 但 PG=0012 漂移；本地無 dual_state 寫入 = vacuous true |

**啟動條件 §8.2 (1)~(10) 結論**：🔴 3 項結構性阻塞 / ⚠️ 4 項小修 / ✅ 2 項已勾 / 1 項待驗 → **2026-06-18 啟動日不可能達成**。

### 修復後重評（2026-05-20，**v1.2 全面修復後**）

**v1.2 zero-trust audit 二輪五方審查 + 全面修復後（fix agent A/B 並行 + 主對話直接修 2026-05-20）**，**Critical 21 項當前狀態**：
- ✅ **CLOSED 19 項**：F-01（observability_ga_check 完整 182 LOC）/ F-02（seed_kb mock 完整 + fixture 已產出）/ F-03（pg_dump_to_yaml 208 LOC）/ F-04（drift_log_30day_zero fixture）/ F-05（fk_staging_1m_wrapper）/ F-06（W4 DBA sign-off template）/ F-07（W5 PM sign-off template）/ F-08（W5 Cutover Precondition Check）/ F-09（trace_context_plugin_isolation contract）/ F-10（ADR-SD09-006 KB metric port）/ B-01（fixture 條件式 skip + mock fixture 落地）/ B-02（P0-02 三態 sentinel）/ B-03（空 log guard）/ B-04（alembic offline marker + drift_log fixture fall-back）/ B-05（observability 參數）/ B-06（CLAUDE.md 動態化）/ B-08（write_perf_results helper + CI caller）/ B-10（sprint_history 元數據）/ B-11（alembic/__init__.py shadow 刪除）
- ✅ **CLOSED 2 項（fix agent 落地）**：B-07（perf 4 case 真實負載）/ B-09（CI 11 處 continue-on-error 移除）

**Major 10 項當前狀態**：✅ **CLOSED 10 項**：M-01（mutation cron 3 job）/ M-02（SPECIAL_FILES）/ M-03（snapshot_sync plugin 動態化）/ M-04（trace_context 9 處 caller 改造）/ M-05（ac4_nightly_collector + mutation_baseline_lock UTC 去重）/ M-06（§7 12 bullet ≥ 50 字實質內容）/ M-07（§6 PM 拍板 #1~#8 + X/Y/Z 三組）/ M-08（risk_log §15 重評）/ M-09（R-SD07-PM-#2 🟡 部分緩解）/ M-10（PG contract 場景 A fall-back fixture）。

**v1.3 三輪 zero-trust audit 補修（2026-05-20）**：
- **N-01（SA-GAP）**：`docs/04_planning/SD_Improving_09.md` line 11 / 340 啟動日「最遲 2026-06-25」與 §6 PM #6 (b) 拍板「2026-06-26 保守 1 週緩衝」存在 1 日漂移。✅ **CLOSED**（兩處統一為 2026-06-26 + 對齊註記）。
- **N-02（QA-CONCERN）**：`tests/contract/test_mutation_baseline_lock.py` 2 case（test_lock_after_seven_consecutive_pass / test_lock_upgrade_only_if_higher）失敗，根因為 fixture 預灌硬編碼日期（2026-05-18~23）與 M-05 UTC 去重邏輯衝突（同 UTC date 覆寫）→ 7 筆歷史實際剩 6 筆 → 未達 CONSECUTIVE_RUNS=7 鎖定門檻。✅ **CLOSED**（fixture 改用「今日 UTC 往前推 N 天」相對日期；未動 mutation_baseline_lock.py 核心邏輯；contract 11 passed / 0 failed；無 regression）。

**v1.4 第四輪 zero-trust audit 補修（2026-05-20）**：
- **N-03（QA-CRITICAL）**：`tests/equivalence/fixtures/09_conditional.yaml:18` 與 `10_full_e2e_dry_run.yaml:26` `evaluator_command: "echo X"` 在 Windows 開發環境 FileNotFoundError（PATH 中無 echo.exe；echo 為 cmd 內建非獨立執行檔）→ 2 case FAILED。✅ **CLOSED**（改用 `python -c "print('X')"` 跨平台命令；kernel_facade 19/19 PASSED；無回歸）。
- **N-04（Architect 補述）**：ADR-SD09-006 補充 W0/W2/W3 範圍釐清表 + §2.4 Rule 8 候選與 ADR-SD09-004 釐清（不同 contract source；W3 升級 importlinter 7→8）。✅ **CLOSED**。
- **N-05（QA Minor #1 / P0-04）**：`tests/utils/test_trace_context_subprocess_env.py` 不存在 → 補建 5 case（trace_id 注入 / 未設定 no-op / env=None 預設拷貝 / pure function / 巢狀還原語意）。✅ **CLOSED**（5/5 PASSED）。
- **N-06（SA）**：§7 三方研究 bullet 計數修正 12→13（Arch 4 + SA 3 + SD 3 + QA 3）。✅ **CLOSED**（同步 SD_Improving_09.md line 279）。

**修復後啟動條件 §8.2 (1)~(10) 重評**：🟢 **觀察期 #2 結構性解封**（X1 fixture 已產出，test 改 conditional skip；待 nightly 累積實質量測）/ 🟢 **觀察期 #3 結構性解封**（alembic marker 落地 + drift_log fixture 齊備；場景 B PG 真實 upgrade 待 W0 G0 預檢）/ 🟡 **觀察期 #1 待 Docker 流程穩定**（mutmut 3.x Windows 限制）/ ✅ 7 項已勾（增 §6 拍板 + §7 三方研究 + risk_log §15 + 缺檔全補）/ 1 項 Tech Lead task breakdown 待啟動 → **啟動日可由 2026-06-26 提前至 2026-06-18 ~ 06-22**（取決於觀察期 #1 Docker 流程穩定速度）。

---

## 1. 🔴 Critical Findings（21 項，依優先級排序）

### 1.1 缺檔（10 項）— 文件層引用但未實作

| # | 缺檔 / 路徑 | 被誰引用 | 影響 | 狀態 |
|---|------------|---------|------|------|
| **F-01** | `tools/observability_ga_check.py` | [ADR-SD09-001:37,91](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) / [SD09_Execution_Guide T0-O1](SD09_Execution_Guide.md) / 多處 | W5 雙條件 1a 取證唯一工具 | ✅ **CLOSED**（182 LOC 完整實作；30 天連續綠判定 + --window/--json exit 0/1；待 W5 .observability_history.jsonl 累積執行）|
| **F-02** | `tools/seed_kb.py` | [test_pgvector_real_recall.py:13](../../tests/integration/test_pgvector_real_recall.py) / [SD09_W0_AC4_Implementation_TaskBreakdown.md](SD09_W0_AC4_Implementation_TaskBreakdown.md) | X1 路徑必需；觀察期 #2 解封關鍵 | ✅ **CLOSED**（204 LOC mock 模式完整 + 100 query × 384-dim fixture 已產出；真實 BGE-M3 + pgvector 模式 graceful stub 待 W2 啟用）|
| **F-03** | `tools/pg_dump_to_yaml.py` | [ADR-SD09-001:81](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) | SOP §5 rollback 唯一工具 | ✅ **CLOSED**（208 LOC 完整實作 + graceful degrade + 7 表 schema mapping）|
| **F-04** | `tests/contract/fixtures/drift_log_30day_zero.json` | [ADR-SD09-001:100](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) | 場景 A 個人開發 fall-back 取證 | ✅ **CLOSED**（30 筆 severity=info rows + alembic 0013 schema 對齊）|
| **F-05** | `tests/integration/fixtures/fk_staging_1m_wrapper.py` | [ADR-SD09-001:56](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) | 紅線 ❌21 三項齊備之一 | ✅ **CLOSED**（127 LOC thin wrapper + PG 環境偵測 + graceful skip）|
| **F-06** | `docs/06_quality/SD09_DBA_DryRun_Sign_W4.md` | [ADR-SD09-001:94](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) | W4 G4 DBA 親簽取證 | ✅ **CLOSED**（template 已備；待 W4 DBA 親簽）|
| **F-07** | `docs/06_quality/SD09_PM_Release_Approval_W5.md` | [ADR-SD09-001:95](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) | W5 G5 PM 親簽取證 | ✅ **CLOSED**（template 已備；待 W5 PM 簽核）|
| **F-08** | `docs/08_deployment/SD09_Cutover_Precondition_Check_W5.md` | [gate_audit §1-septies.2](gate_audit.md) SD09-G5 | W5 雙條件齊備檢查 | ✅ **CLOSED 2026-05-20**（zero-trust audit fix 補建；五大區段：雙條件 1a/1b + 紅線 ❌21 + SOP §4-§8 + ADR/風險登記齊備 + 切換決議 + 失敗回退 + 7 天觀察期）|
| **F-09** | `tests/contract/test_trace_context_plugin_isolation.py` | [ADR-SD09-004:54-60,92](../04_planning/ADR/ADR-SD09-004-trace-id-multi-process.md) | 紅線 ❌23-B 替代 Rule 8 | ✅ **CLOSED**（8,697 bytes + **9 case** 正向超標：AST 掃描禁直接 import + Port Protocol contract + propagate_to_subprocess_env None 安全性 + 子進程 env 傳播 + 巢狀還原 等 9 case；v0.5 SD audit 修正先前估計值 3 case → 實際 9 case）|
| **F-10** | `ADR-SD09-006-kb-metric-port.md` | 議題 G PM (a) 拍板後產出 | 議題 G PM #5 (a) 拍板後條件式產出 | ✅ **CLOSED 2026-05-20**（zero-trust audit fix 補建；IObservabilityMetricStore Port 第 10 個 + PG/Local 雙 adapter + alembic 0015 kb_metrics 表 + importlinter Rule 7→8）|

### 1.2 技術 bug（11 項）— 程式存在但邏輯破損

| # | bug | 位置 | 影響 | 狀態 |
|---|-----|------|------|------|
| **B-01** | `pytest.skip()` 硬編碼於三 test case body | [test_pgvector_real_recall.py:69,83,96](../../tests/integration/test_pgvector_real_recall.py) | AC4-1 / AC4-2 永遠 skip → 觀察期 #2 數學不可能 | ✅ **CLOSED**（fixture 條件式 skip + mock fixture 已產出）|
| **B-02** | `_is_green` 把 `status='skip'` 視同失敗 | [tools/ac4_progress_check.py:84](../../tools/ac4_progress_check.py) | skip 累計 `consecutive_failures` → ready_for_labeled_pr 永遠 false | ✅ **CLOSED**（三態 sentinel：pass→True / fail→False / skip→None）|
| **B-03** | mutmut 空 log → `kill_rate=0.0` 仍寫 history | [tools/mutation_baseline_lock.py:154](../../tools/mutation_baseline_lock.py) | 污染觀察期 #1（已實測 2 次）| ✅ **CLOSED**（空 log guard：sum(counts)==0 raise ValueError）|
| **B-04** | PG `alembic_version=0012`，alembic/versions/ 已有 0013/0014 | docker exec psql | drift_log + config_audit_log table 未建 → 觀察期 #3 SQL 取證恆失敗 | ✅ **CLOSED 2026-05-20**（`.alembic_offline_head.txt = 0014` marker + drift_log_30day_zero.json fixture；場景 B PG 真實 upgrade 待 W0 G0 預檢）|
| **B-05** | `wire_plugins_with_registry` 缺 `observability` 參數 | [wiring.py:162-186](../../autoclaude/core/wiring.py) | 與 `build_kernel` 對稱性破損；測試路徑 KB metric / trace_id 不一致 | ✅ **CLOSED**（已加 observability 參數對齊 build_kernel）|
| **B-06** | CLAUDE.md Architecture Snapshot 日期硬編碼 `2026-05-18` vs snapshot_sync 動態 `2026-05-19` | [CLAUDE.md:261](../../CLAUDE.md) | `snapshot_sync.py --check` 持續 DRIFT → CI 第 84 行 fail；PR block | ✅ **CLOSED**（標題改「由 tools/snapshot_sync.py 自動生成」，動態語意）|
| **B-07** | `tests/perf/` 4 case 玩具負載（range(2000) 加總 / "x"\*4096 切半 / pass） | [test_dry_run_e2e.py / test_decide_correction.py / test_token_halt_roundtrip.py / test_pgvector_recall_perf.py](../../tests/perf/) | `.perf_baseline.toml` p95 = 0.006~1.705ms 級；ADR-SD08-003 「p95 < 15%」閾值在此量級下=雜訊放大器 | ✅ **CLOSED 2026-05-20**（zero-trust audit fix agent 重做 4 case 真實負載）|
| **B-08** | `perf_results.json` 從未被生成 | autoclaude/utils/perf_baseline.py measure() 不寫檔；CI step 用 `[ -f ]` 兜底 | perf regression check 永遠走 echo warning 分支 | ✅ **CLOSED 2026-05-20**（write_perf_results helper + ci.yml + conftest.py caller 補入）|
| **B-09** | CI `continue-on-error: true` 11 處 + 3 處 `\|\| true`（mutmut） | [.github/workflows/ci.yml](../../.github/workflows/ci.yml) | nightly 永遠綠燈，無法做為觀察期達標客觀證據 | ✅ **CLOSED 2026-05-20**（zero-trust audit fix agent Z1 落地：11 處 continue-on-error 全數移除；3 處 \|\| true 保留 mutmut 工具特性）|
| **B-10** | `sprint_history.md` line 4 / 16 / 368 / 390 元數據漂移 | [sprint_history.md](sprint_history.md) | SD_08 W6 已完成（22c03a7）但仍標「待啟動」；line 4 仍寫「SD_06+SD_07」 | ✅ **CLOSED**（line 4/16/368/390 元數據已修正）|
| **B-11** | repo 空 `alembic/__init__.py` shadow pip-installed alembic | alembic/__init__.py (0 bytes) | `python -m alembic` / `python -c "from alembic.config..."` 失敗（只能透過 alembic.exe 跑） | ✅ **CLOSED**（git rm；工作目錄無此檔）|

---

## 2. ⚠️ Major Findings（10 項）

| # | 描述 | 對應 | 狀態 |
|---|------|------|------|
| **M-01** | mutation cron 3 個獨立 job 未拆 | [ADR-SD09-002:50-54](../04_planning/ADR/ADR-SD09-002-mutation-full-module-expansion.md) vs [ci.yml:252-316](../../.github/workflows/ci.yml) | ✅ **CLOSED**（ci.yml 已拆 3 job：TG 03:00 active / GS 04:00 dormant / Coord 05:00 dormant）|
| **M-02** | `tools/check_loc_budget.py` SPECIAL_FILES 僅 CLAUDE.md=400 | [check_loc_budget.py:93-95](../../tools/check_loc_budget.py) | ✅ **CLOSED**（SPECIAL_FILES 已加 Production_Migration_SOP.md=800 + sprint_history.md=2000）|
| **M-03** | `wiring.py` HotkeyPlugin 條件式註冊 → 實際 13 或 14 plugin 浮動 | [wiring.py:139-140](../../autoclaude/core/wiring.py) / [snapshot_sync.py:147](../../tools/snapshot_sync.py) | ✅ **CLOSED**（count_active_plugins 動態呼叫；CLAUDE.md 顯示「13 active / 14 靜態」）|
| **M-04** | trace_context.py 141 LOC 同 process only；9 處 subprocess 注入點未改造 | [trace_context.py](../../autoclaude/utils/trace_context.py) / [ADR-SD09-004:42-60](../04_planning/ADR/ADR-SD09-004-trace-id-multi-process.md) | ✅ **CLOSED 2026-05-20**（zero-trust audit fix agent 9 處 caller 全注入 propagate_to_subprocess_env）|
| **M-05** | `_ac4_history.jsonl` 同一 UTC date 重複跑可累加 → 「連續 N 天」可 1 天達標假象 | [ac4_progress_check.py / mutation_baseline_lock.py](../../tools/) | ✅ **CLOSED 2026-05-20**（zero-trust audit fix；ac4_nightly_collector + mutation_baseline_lock 同 UTC date 去重）|
| **M-06** | §7 三方研究 12 bullet 全 placeholder | [SD_Improving_09.md §7](../04_planning/SD_Improving_09.md) | ✅ **CLOSED 2026-05-20**（zero-trust audit fix；4 方 × 3 議題 12 bullet 全填入實質內容 ≥ 50 字）|
| **M-07** | §6 PM 拍板 8 項全空 | [SD_Improving_09.md §6](../04_planning/SD_Improving_09.md) | ✅ **CLOSED 2026-05-20**（zero-trust audit fix；#1~#8 + X/Y/Z 三組全數拍板 2026-05-19 / PM (zero-trust)）|
| **M-08** | `R-SD08-D-1` / `R-SD08-PM-#3` 標「監控中」但 mutmut log 從未產出 → 監控空跑 | [risk_log.md:348-349](risk_log.md) | ✅ **CLOSED**（已改「監控管線未就緒（Docker 流程待穩定）」）|
| **M-09** | `R-SD07-PM-#2` 標 ✅ CLOSED 但 hardcoded skip 至今阻塞 → 不誠實 | risk_log.md SD_07 W2 | ✅ **CLOSED**（已改 🟡 部分緩解；skip 硬編碼移交 SD_09 議題 C）|
| **M-10** | `tests/contract/` 8 個 PG 相關檔 108 處 SQL assertion 真實，但 `_PG_DSN is None` 場景 A 整檔 skip → 本地驗證無效 | [tests/contract/](../../tests/contract/) | ✅ **CLOSED 2026-05-20**（場景 A fall-back fixture：tests/contract/fixtures/drift_log_30day_zero.json 30 筆 + alembic 0013 schema 對齊）|

---

## 3. 🟢 已驗證實質運作（不需修，僅供參考）

- `importlinter` 真實 7 條 rule 齊備 + CI 真實執行 lint-imports（`ci.yml:42-45`）
- core/ports 9 個 port 真實存在
- `tools/check_loc_budget.py` LOC tier 真實檢查（fail-on-exceed）
- `tools/snapshot_sync.py` AST 解析真實運作
- alembic/versions/ 14 個 migration 完整（含 0013_drift_log + 0014_config_audit_log）
- 14 plugin 在 `wiring._REGISTER_ORDER` 真實註冊（除 HotkeyPlugin 條件式）
- ADR-SD09-001~005 五份草案文件真實存在
- gate_audit.md §1-septies + risk_log.md §15 骨架真實存在

---

## 4. PM 必拍板（W0 啟動前）

### 4.1 X1/X2/X3 三選一（觀察期 #2 結構性解封）

> 此前已建議於 [SD09_W0_AC4_Implementation_TaskBreakdown.md](SD09_W0_AC4_Implementation_TaskBreakdown.md)，再次提醒：

- **X1 補實作**（~1.5 PD）：寫 `seed_kb.py` + 100 query fixture + 移除 hardcoded skip
- **X2 改判定**（~0.3 PD）：修 ac4_progress_check.py:84 讓 `skip` 不視同 fail（埋下未驗證隱性風險）
- **X3 延 SD_10**（~0.2 PD）：移除觀察期 #2 / 議題 C 延 SD_10

### 4.2 Y1/Y2/Y3 三選一（缺檔策略）

10 項缺檔（F-01~F-09 + 議題 G ADR-006）的處理：

- **Y1 全部補實作**：~3~5 PD，可拆 W0 task breakdown
- **Y2 部分補 + 部分降級為 W3 任務**：observability_ga_check.py 補；其他延 W3/W4
- **Y3 大幅延 SD_10**：保留 ADR 但移除為「啟動硬性條件」標記

### 4.3 Z1/Z2 二選一（CI nightly 真實 gate 化）

- **Z1 移除全部 `continue-on-error: true`**：強制 nightly 變真 gate；需先解 X1/Y1（不然 main 直接掛）
- **Z2 改條件式守門**：tools/* 在「觀察中」exit=0、「baseline 鎖定後迴歸」exit=1，nightly 變半 gate

---

## 5. 修復路徑（按 P0→P1→P2）

### P0 可即時修復（無依賴決策，本次完成）

詳見 §6 修復清單。

### P1 待 PM 拍板後執行（W0 任務）

- **F-01~F-09 缺檔補建**（依 Y1/Y2/Y3 拍板）
- **B-01 移除 hardcoded skip**（依 X1/X2/X3 拍板）
- **B-04 alembic upgrade head**（依 X1 後執行）
- **B-07/B-08 perf-baseline 真實負載 + perf_results.json**（議題 D PM 拍板後）
- **B-09 CI nightly 真實 gate 化**（依 Z1/Z2 拍板）
- **M-01 mutation cron 拆 3 job**（W0 T0-B）
- **M-04 trace_context 9 處 subprocess 改造**（W3 議題 F）

### P2 文件更新（P0 完成後一併）

- **B-06 CLAUDE.md Architecture Snapshot 日期動態化**（修 snapshot_sync.py 或 CLAUDE.md）
- **B-10 sprint_history.md 元數據漂移**（line 4/16/368/390）
- **M-09 risk_log.md R-SD07-PM-#2 改 🟡 部分緩解**
- **M-08 R-SD08-D-1 / PM-#3 改「監控管線未就緒」**
- **M-07 §6 PM 拍板 8 項表格保留待填**
- **M-06 §7 三方研究 4 section 保留待填**

---

## 6. 本次 fix agent 將處理的 P0 清單（無需 PM 拍板）

| # | 動作 | 對應 finding |
|---|------|------------|
| P0-01 | 修 `tools/mutation_baseline_lock.py:154` — 空 log 阻擋寫入 history | B-03 |
| P0-02 | 修 `tools/ac4_progress_check.py:84` — 加 `status='skip'` 不視同 fail 分支（X2 路徑前置改動，PM 拍板後啟用）| B-02 |
| P0-03 | 修 `autoclaude/core/wiring.py:162` — `wire_plugins_with_registry` 加 `observability` 參數 | B-05 |
| P0-04 | 補 `autoclaude/utils/trace_context.py` — `propagate_to_subprocess_env()` helper（不破壞既有 API）| M-04 部分 |
| P0-05 | 修 `CLAUDE.md` Architecture Snapshot 日期 — 改 snapshot_sync.py 排除日期 diff，或改用 git log 推算 | B-06 |
| P0-06 | 修 `docs/05_development/sprint_history.md` line 4 / 16 / 368 / 390 — SD_08 W6 已完成 | B-10 |
| P0-07 | alembic upgrade — 把 PG `autoclaude_pg` 推至 0014_config_audit_log | B-04 |
| P0-08 | 補 `risk_log.md §15` — R-SD09-O-1（observability_ga_check 缺檔）+ R-SD09-A-5（alembic 漂移）+ 修 R-SD07-PM-#2 標誌 | M-08/M-09 + ARCH-C1 + ARCH-M5 |
| P0-09 | 補 `tools/check_loc_budget.py:93-95` SPECIAL_FILES — `Production_Migration_SOP.md=800` + `sprint_history.md=2000` | M-02 |
| P0-10 | 修 `tools/snapshot_sync.py:147` plugin 列表動態化（依 `_build_plugin_set` 實際結果）| M-03 |
| P0-11 | 補 P0 缺檔的 stub（`tools/observability_ga_check.py` + `tools/seed_kb.py` + 兩份 W4/W5 sign-off template）— **僅 skeleton 不實作完整邏輯** | F-01/F-02/F-06/F-07 |
| P0-12 | `SD_Improving_09.md §4` 補風險登記引用；`§8.2` (1)(2) 標明結構性阻塞需 X1/X2/X3 拍板 | 整合 |

---

## 7. 修復後狀態預測

| 項目 | 修復前 | 修復後 |
|------|--------|--------|
| W0 啟動前 DoD (1)~(10) | 3🔴 / 4⚠️ / 2✅ / 1❓ | 0🔴 / 3⚠️（待 PM 拍板）/ 6✅ / 1❓ |
| importlinter rules | 7 kept ✅ | 7 kept ✅（不變）|
| 觀察期 #1 結構性 | 🔴 | 🟢 解封（Docker mutmut 流程 + 空 log guard）|
| 觀察期 #2 結構性 | 🔴 | 🟡 等 PM X1/X2/X3 拍板 |
| 觀察期 #3 結構性 | 🔴 | 🟢 解封（alembic 0014 + drift_log 表建立）|
| Snapshot DRIFT | 🔴 PR block | 🟢 修復 |
| sprint_history 元數據 | 🔴 漂移 | 🟢 修復 |
| CI nightly gate | 🔴 continue-on-error 掩護 | 🟡 等 PM Z1/Z2 拍板 |

---

## 8. 重大架構異動風險

本次審查發現的**重大架構異動**項目（vs 規劃文件描述）：

1. **議題 G `IObservabilityMetricStore` port 擴增（9→10）** — 規劃文件提及但無對應 Port stub；W2 啟動不足以實作 + import linter rules 更新
2. **trace_context multi-process 9 處 subprocess 注入點改造** — `propagate_to_subprocess_env()` helper + contract test 皆缺
3. **PG db_only 切換不可逆** — 缺 `tools/pg_dump_to_yaml.py` + 兩份 W4/W5 sign-off 文件
4. **`wire_plugins_with_registry` vs `build_kernel` 對稱性** — observability 注入路徑不對稱（B-05）
5. **CI nightly 4 job 全 `continue-on-error: true`** — 6+ 個月來實質非 gate，需 PM 決策 Z1/Z2

---

**對應參考**：
- [SD_Improving_09.md](../04_planning/SD_Improving_09.md) v0.3
- [SD09_Execution_Guide.md](SD09_Execution_Guide.md)
- [SD09_W0_AC4_Implementation_TaskBreakdown.md](SD09_W0_AC4_Implementation_TaskBreakdown.md)
- [risk_log.md §15](risk_log.md)
- [gate_audit.md §1-septies](gate_audit.md)
