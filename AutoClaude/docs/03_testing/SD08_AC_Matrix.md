# SD_Improving_08 AC Matrix（W6 G6 末實測回填 v1.0；SD_07 19 + SD_08 10 = 29 ≥ 27）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0（W6 G6 末實測全數回填，2026-05-18）** |
| 建立日期 | 2026-05-18 |
| 對應規劃 | [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0 |
| 依據 | SD_07 AC Matrix 結構（19 條）+ SD_08 新增 10 條 = **合計 29 條 ≥ 27 門檻 ✅** |
| W6 G6 量測（2026-05-18）| AC4-1/AC4-2 工具 6/6 PASSED + observing；AC7-1 9/9 / AC7-2 7/7 / AC7-3 6/6；AC8-2 contract 11/11；AC9-1 4 baseline lock；AC9-2 contract 4/4；AC10-1 pg_health 6/6；AC-LOC-1 contract 16/16；AC-LOC-2 3/3 sprint_history 命中 |

---

## AC4 PG e2e 漸進式升級（W2 議題群 C，2 條）

### AC4-1：recall@10 ≥ 0.95（**SD_09 T0-C3 升級為實測門檻**）

- **對應**：PM 拍板 #2 / W2 T2-C2 + T2-C3 / SD_09 T0-C3
- **量測**：
  - `python tools/ac4_nightly_collector.py --junit-xml .ac4_junit.xml`（nightly 累計）
  - `python tools/ac4_progress_check.py --json`（讀 `.ac4_history.jsonl` 評估，回傳 `ready_for_labeled_pr=true`）
- **通過門檻（SD_09 T0-C3 升級實測語意）**：14 天 nightly 全綠連續 + **實測 recall@10 ≥ 0.95** + recall σ ≤ 0.02（**非工具就位即視為通過**，須觀察期累計實測數據）
- **W2 G2 實測（2026-05-18）**：工具就位 ✅ + observing 觀察期啟動。**SD_09 W0 補述（2026-05-20）**：觀察期 #2 阻塞於 `tests/integration/test_pgvector_real_recall.py` 3 case 硬編碼 `pytest.skip` 與 `tools/seed_kb.py` 未實作（PM 拍板 X1 — 2026-05-19 已落地 fixture + `tools/seed_kb.py` 204 LOC + conditional skip），SD_09 W0 起 nightly 可實質採集 recall 數據；達標日預估 2026-06-02（觀察期 #2 結束）
- **檔位**：`tools/ac4_nightly_collector.py` + `tools/ac4_progress_check.py` + `.github/workflows/ci.yml` `pg-e2e-nightly` job + `tests/fixtures/pgvector_real_queries.json` + `tests/fixtures/pgvector_real_ground_truth.json`（X1 落地）
- **升級條件**：`tools/ac4_progress_check.py` 回報 `ready_for_labeled_pr=true` 後手動啟用 `pg-e2e-on-label.yml` workflow（SD_09 T0-C2）

### AC4-2：p95 latency < 50ms + CircuitBreaker open=0（**SD_09 T0-C3 升級為實測門檻**）

- **對應**：PM 拍板 #2 / W2 T2-C5 + T2-C8 / SD_09 T0-C3
- **量測**：
  - `python -m pytest tests/contract/test_ac4_progress_check.py -v`（contract 工具行為）
  - `python tools/ac4_progress_check.py --json` 輸出 `green_streak` + `consecutive_failures` + `recall_sigma` + `ready_for_labeled_pr` + `reasons`（**W1 補 `p95_latency_ms` + `cb_open_count` + `recall_p10` 三鍵匯出**對齊本門檻；目前工具讀取 nightly fields 但未上拋至 JSON top-level，SD_09 W0 QA zero-trust audit 已登 P1 修補）
- **通過門檻（SD_09 T0-C3 升級實測語意）**：≥ 4 case 綠（未達 14 天 / 達 14 天全綠 / 黃線 3 次 / 紅線 5 次 CircuitBreaker open）+ **實測 p95 latency < 50ms** + **實測 cb_open_count = 0** 連續 14 天（**非工具就位即視為通過**，須觀察期累計實測數據）
- **W2 G2 實測（2026-05-18）**：**6/6 PASSED ✅**（含 σ 邊界 + 空 history 兩條 bonus）。**SD_09 W0 補述（2026-05-20）**：observing 累計待 nightly 跑滿後評估 p95 < 50ms / cb_open=0；達標日預估 2026-06-02（與 AC4-1 同步觀察期 #2 結束）
- **檔位**：`.github/workflows/pg-e2e-on-label.yml`（needs-pg-e2e label 觸發；觀察期 #2 通過後啟用，SD_09 T0-C2 dormant → active）
- **告警閾值**：黃線 ≥ 3 次未達綠線 / 紅線 ≥ 5 次未達綠線（自動 PR 評論）

---

## AC7 可觀測性（W4 議題群 F，3 條）

### AC7-1：IObservabilityPort Protocol 合約

- **對應**：ADR-SD08-004 §2.1 / W4 T4-F1
- **量測**：`python -m pytest tests/core/ports/test_observability_port.py -v`
- **通過門檻**：≥ 6 case 綠（Protocol 合約 + LocalLogger emit + ContextVar 傳遞 + daemon thread 包裝 + Rule 7 違規偵測 + emit_counter/histogram/event API 對齊）
- **W4 G4 實測（2026-05-18）**：**9/9 PASSED ✅**（含 NullObservability no-op + span context manager + 例外傳播 3 個 bonus）
- **檔位**：`autoclaude/core/ports/observability.py` 167 LOC（contract tier ≤ 400 ✅）

### AC7-2：trace_id daemon thread 不斷鏈

- **對應**：ADR-SD08-004 §2.3 / W4 T4-F11 + T4-F14
- **量測**：`python -m pytest tests/utils/test_trace_context_daemon_thread.py -v`
- **通過門檻**：≥ 3 case 綠（PTY daemon thread 不斷鏈 / `copy_context()` 顯式 / 並發 thread isolation）
- **W4 G4 實測（2026-05-18）**：**7/7 PASSED ✅**（含 raw Thread 對照組驗證斷鏈動機 + 巢狀還原 + run_in_thread_with_context 同步包裝 4 個 bonus；R-SD08-F-1 緩解就位）
- **檔位**：`autoclaude/utils/trace_context.py` 141 LOC ≤ 150 ✅

### AC7-3：KB metric 4 項

- **對應**：ADR-SD08-004 §2.4 / W4 T4-F9 + T4-F10
- **量測**：`python -m pytest tests/utils/test_knowledge_base_metrics.py -v`
- **通過門檻**：≥ 4 case 綠（hit_rate / query_p95_ms / strategy_rotation_count / cache_eviction_count；snapshot 一致；hit_rate 邊界 0/1；eviction 累計）
- **W4 G4 實測（2026-05-18）**：**6/6 PASSED ✅**（含 200-window 上限 + p95 大樣本百分位 2 個 bonus；補 `tests/utils/test_knowledge_base_observability.py` 4 case `hit/miss/rotation/無 obs 仍累計`）
- **檔位**：`autoclaude/utils/knowledge_base_metrics.py` 121 LOC ≤ 150 ✅（data tier）

---

## AC8 mutation pilot（W3 議題群 D，2 條）

### AC8-1：TokenGuardPlugin mutation kill rate ≥ 70%

- **對應**：ADR-SD08-002 §2.2 / W3 T3-D2 + T3-D7
- **量測**：CI nightly 連跑 14 天 + 連續 7 次達標寫入 `.mutation_baseline.toml`
- **通過門檻**：mutation kill rate ≥ 70%（pilot 目標 -5%；正式目標 75%）；連續 7 次達標
- **W3 G3 實測（2026-05-18，observing 觀察期）**：工具就位 ✅；observing 觀察期啟動 2026-05-19；首次評估鎖定 2026-05-25；W3 末判定 2026-06-01；continue-on-error=true 不阻塞；**fall-back（< 60%）→ SD_09 接續**（R-SD08-D-1）
- **檔位**：`autoclaude/plugins/token_guard/` + `tests/plugins/token_guard/`

### AC8-2：`.mutation_baseline.toml` 鎖定

- **對應**：ADR-SD08-002 §2.4 / W3 T3-D3
- **量測**：`python -m pytest tests/contract/test_mutation_baseline_lock.py -v`
- **通過門檻**：≥ 4 case 綠（未達 7 次 / 達 7 次 / 抖動單日不鎖 / 鎖後升級）；`.mutation_baseline.toml` 存在 + 含 token_guard 欄位
- **W3 G3 實測（2026-05-18）**：**11/11 PASSED ✅**（4 主流程 + 7 補強：parse emoji format / kill_rate 排除 skipped / should_lock 取 min / 分類 boundary/constant/string_literal ignore / 空 log 邊界）；`.mutation_baseline.toml` 初始空 `[scores]` 區段就位（等待 observing 觀察期填入）

---

## AC9 性能 baseline（W5 議題群 G，2 條）

### AC9-1：4 場景 baseline 鎖定

- **對應**：ADR-SD08-003 §2 / W5 T5-G1~T5-G8
- **量測**：CI nightly 連跑 7 次 + `.perf_baseline.toml` 鎖定（dry_run_e2e / token_halt_roundtrip / decide_correction / pgvector_recall_perf 共 4 場景）
- **通過門檻**：4 場景各自鎖定 p95 baseline；perf machine 季度校準（pgvector p95 為標的）
- **W5 G5 實測（2026-05-18）**：**3 場景 baseline 首次鎖定 ✅**（dry_run_e2e p95=0.258ms / token_halt_roundtrip p95=0.006ms / decide_correction p95=1.705ms；本機 git e65bcee；正式 baseline 待 ubuntu-latest nightly 連跑 7 次覆寫 — ADR-SD08-003 §2.6）；pgvector_recall_perf pg_real marker 強制延 perf machine（R-SD08-G-1）
- **檔位**：`tests/perf/test_*.py` + `autoclaude/utils/perf_baseline.py` 137 LOC ≤ 150 ✅

### AC9-2：p95 < 15% 告警

- **對應**：ADR-SD08-003 §3 / W5 T5-G6 + T5-G9
- **量測**：`python -m pytest tests/contract/test_perf_regression_check.py -v`
- **通過門檻**：≥ 4 case 綠（通過 / 警告 / 阻塞 / 缺 baseline）；annotation + PR comment 雙通道
- **W5 G5 實測（2026-05-18）**：**4/4 PASSED ✅**（pass +5% / warn +12% / block +20% + PR comment 寫出 / missing baseline → exit=1）；三級告警 `< 10% pass / 10-15% warn / ≥ 15% block` 收緊 5% vs 業界 20%
- **檔位**：`tools/perf_regression_check.py` 193 LOC

---

## AC10 PG 前置（W5 議題群 H，1 條）

### AC10-1：pg_health.py WAL lag 三閾值

- **對應**：ADR-SD08-005 §2 / W5 T5-H1~T5-H4
- **量測**：`python -m pytest tests/infra/test_pg_health.py -v`
- **通過門檻**：≥ 5 case 綠（lag < 2s 正常 / 2-10s warn / > 10s critical / connection count / fixture mock pg）
- **W5 G5 實測（2026-05-18）**：**6/6 PASSED ✅**（NORMAL 無告警 / WARN emit counter / CRITICAL emit event 降級 / active_connections 透傳 / classify_lag 8 邊界 / NullObservability fallback）；ADR-SD08-005 W5 G5 簽核（三項齊備）
- **檔位**：`autoclaude/infra/observability/pg_health.py` 214 LOC ≤ 400 ✅（adapter tier）
- **延期至 SD_09**：人類 DBA staging 重跑 + 人類 PM 親簽（紅線禁 SD_08 切換 PG db_only — ADR-SD08-005 §2.2 雙條件未達）

---

## AC-LOC 橫切議題群 E（W0 + W6 共 2 條）

### AC-LOC-1：CLAUDE.md ≤ 400 行 + Snapshot SSOT 同步

- **對應**：ADR-SD08-001 §2.1 + §3 / W0 T0-E1~T0-E6
- **量測**：
  - `wc -l CLAUDE.md`（≤ 400）
  - `python tools/check_loc_budget.py`（special violations=0）
  - `python tools/snapshot_sync.py --check`（exit 0）
  - `python -m pytest tests/contract/test_claude_md_budget.py -v`
- **通過門檻**：CLAUDE.md ≤ 400 / snapshot reproducible / contract ≥ 3 case 綠
- **W0 實測**：CLAUDE.md=**303 lines** ✅ / violations=**0** ✅ / contract **16 case** PASSED ✅

### AC-LOC-2：sprint_history.md SD_03~SD_05 完整下沉

- **對應**：ADR-SD08-001 §2.3 + §2.4 / W0 T0-E5
- **量測**：`grep -E "^### 1\.[1-3] SD_Improving_(03|04|05)" docs/05_development/sprint_history.md`
- **通過門檻**：3 行命中（SD_03 §1.1 / SD_04 §1.2 / SD_05 §1.3 全部存在）
- **W0 實測**：3/3 命中 ✅；sprint_history.md=**399+ lines**（含 §1.4 SD_06 / §1.5 SD_07 / §1.6 SD_08 滾動窗口）

---

## 簽核（W6 G6 末四方審查 + PM）

| 角色 | 狀態 | 日期 | 簽核摘要 |
|------|------|------|----------|
| Architect | ✅ APPROVED | 2026-05-18 | AC7×3 對齊 ADR-SD08-004；AC9×2 對齊 ADR-SD08-003；AC10×1 對齊 ADR-SD08-005 |
| SA | ✅ APPROVED | 2026-05-18 | 10 條 AC 量測命令完整；W2/W3 fall-back 路徑明文 |
| SD | ✅ APPROVED | 2026-05-18 | AC7-1/AC7-2/AC7-3 程式碼覆蓋對齊；AC10-1 三閾值與 pg_health.py 一致 |
| QA | ✅ APPROVED | 2026-05-18 | 29 條 AC（SD_07 19 + SD_08 10）≥ 27 門檻；W3/W5 fall-back 預埋；test 命令可重現 |
| PM | ✅ APPROVED | 2026-05-18 | 場景 A 個人開發 dev 自核；對應 PM 8 項拍板（#1~#8）全數對齊 |

> **後續 Wave 更新規則**：每完成 1 Wave，由該 Wave 末 G-gate 簽核流程填入「實測欄」；**W6 G6 末已全數回填實測值（2026-05-18）**。

---

**相關文件**：
- [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0
- [SD07_AC_Matrix.md](SD07_AC_Matrix.md) — SD_07 19 條 AC（前置 baseline）
- [ADR-SD08-001](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) ~ [005](../04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md)
