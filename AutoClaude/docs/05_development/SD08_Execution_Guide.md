# SD_Improving_08 嚴格執行大綱（Opus 4.7 操作指南）

| 項目 | 內容 |
|------|------|
| 目標文件 | [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0（PM 8 項拍板 APPROVED 2026-05-18）|
| 執行基線 | **2,012 passed / 121 skipped**（SD_07 W6 G6 末，2026-05-18 確認）|
| 預估終線 | W6 末 ≥ **2,100 passed**（QA 估算 +88 case）|
| 執行模型 | Claude Opus 4.7（標準模式，**不要用 /fast**） |
| 總範圍 | 8 議題群（A→F→D→C→E→B→G→H）/ 7 Wave |
| G0 啟動日 | **2026-05-21（週四）** |
| 建立日期 | 2026-05-18 |
| 對應 ADR | [ADR-SD08-001](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) ~ [005](../04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md) 共 5 條 |

---

## 0. G0 啟動前置 DoD（2026-05-20 EOD 前必完成）

```
[  ] Tech Lead 提交 W0 task breakdown（A + E 議題群 detail tasks，本文件 §3 W0 已含）
[✅] ADR-SD08-001 ~ 005 草案落地（2026-05-18 完成；待 PM 形式核准）
[  ] PM 對 5 條 ADR 形式核准（W0 啟動前）
[  ] 確認 git branch 已切至 sprint/sd_08_phase8（或沿用 sprint/sd_07_phase7）
[  ] 確認 SD_07 W6 G6 commit 已 tag 為 sd_07_w6_g6_pass
```

每次開啟新 session 前必跑：

```bash
# 1. 測試基線
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 2,012 passed / 121 skipped

# 2. importlinter
PYTHONUTF8=1 lint-imports --config .importlinter
# 期望：6 kept / 0 broken（W4 後 7 kept）

# 3. LOC 預算（W0 升級後含 CLAUDE.md ≤ 400）
python tools/check_loc_budget.py
# W0 前：violations=0（baseline=14058 永久鎖定）
# W0 後（含 CLAUDE.md ≤ 400 規則）：CLAUDE.md 從 712 → ≤ 400 後 violations=0

# 4. 關鍵檔案 LOC（追蹤進度）
wc -l CLAUDE.md \
      autoclaude/core/ports/observability.py 2>/dev/null \
      autoclaude/utils/trace_context.py 2>/dev/null \
      autoclaude/utils/knowledge_base_metrics.py 2>/dev/null \
      autoclaude/infra/observability/pg_health.py 2>/dev/null
# W0 起點：CLAUDE.md=712 / 其餘 N/A
# W0 末：CLAUDE.md ≤ 400
# W4 末：observability.py + trace_context.py + KB metrics 就位
# W5 末：pg_health.py 就位

# 5. NOTE(SD_08) 殘留
grep -rn "NOTE(SD_08)" autoclaude/ tests/ | wc -l
# W0 起點：0
# W6 末：0

# 6. 議題對應狀態
ls docs/04_planning/ADR/ADR-SD08-*.md | wc -l
# W0 末：5（001~005 全數 PM 形式核准）

ls docs/05_development/sprint_history.md
# W0 末：存在（含 SD_03~SD_05 完整下沉）

wc -l docs/05_development/sprint_history.md
# W0 末：≥ 600（SD_03/SD_04/SD_05 各 200 行詳細紀錄）
```

---

## 1. 全程絕對規則（違反即停止）

```
[  ] 每完成一個交付物 → 立即跑全測，全綠才繼續
[  ] equivalence snapshot 83 fixture 任一斷裂 → 立刻停止，不得繞過
[  ] importlinter 出現 broken → 立刻停止並還原
[  ] LOC 超分級 budget → 立刻拆 package 或在 .loc-budget.toml 加 override（雙簽）
[  ] CLAUDE.md > 400 行 → 立刻下沉至 sprint_history.md（ADR-SD08-001 §2.1 強制）
[  ] Plugin 不可互相 import；不可直接 import utils.observability（W4 新增 Rule 7）
[  ] W4 IObservabilityPort 必須放在 core/ports/（不可放 utils/）— ADR-SD08-004 §2.1 強制
[  ] W3 mutation pilot 僅 TokenGuardPlugin 單模組（不可一次啟用 3 模組 nightly）— ADR-SD08-002 §2.2
[  ] W5 PG production 切換**禁止**（H 議題群延 SD_09）— ADR-SD08-005 §2.2 雙條件未達
```

---

## 2. 架構紅線（繼承 SD_07 §2 + 新增 4 條，共 20 條）

繼承 SD_07 §2 全部 16 條（❌1~❌16）+ SD_08 新增 4 條：

| # | 禁止行為 |
|---|---------|
| ❌1~❌16 | （繼承 SD_07 §2）|
| ❌17 | CLAUDE.md > 400 行（ADR-SD08-001 強制；W0 落地後 CI 阻擋）|
| ❌18 | `IObservabilityPort` 放在 `utils/` 而非 `core/ports/`（ADR-SD08-004 §2.1）|
| ❌19 | W3 mutation pilot 一次啟用 3 模組 nightly（必須單模組 TokenGuardPlugin 兩週）|
| ❌20 | SD_08 W5 內推進 PG db_only 切換（H 議題群延 SD_09；ADR-SD08-005 §2.2 雙條件未達禁切換）|

⚠️ **`autoclaude.execution._runner_internals` importlinter contract 持續保留為防復活柵欄**（SD_07 W5 Rule 6，SD_08 不拔除）。

---

## 3. Wave 執行協議（A→F→D→C→E→B→G→H 優先順序）

### ── W0：SD_07 遺留收尾 + CLAUDE.md 精簡 + ADR 落地（A + E 議題群）──

**目標**：
- m-Arch3 + m-SD3 拔除史註解集中（A 議題群）
- CLAUDE.md ≤ 400 行 + `[Architecture Snapshot]` SSOT 區段（E 議題群）
- `sprint_history.md` 完整下沉 SD_03~SD_05（保留 SD_06/SD_07 滾動窗口）
- `tools/snapshot_sync.py` + `claude-md-budget` CI job 落地
- ADR-SD08-001~005 PM 形式核准

**逐項打勾**：
```
# A 議題群：SD_07 遺留收尾
[  ] T0-A1 grep -rn "NOTE(SD_07) m-Arch3\|NOTE(SD_07) m-SD3" autoclaude/ tests/ → 盤點殘留
[  ] T0-A2 拔除史註解集中（移至 sprint_history.md SD_07 段落或刪除已落地項）
[  ] T0-A3 校準 CLAUDE.md W4「9 處 patch path」實測為 5 處（已於 SD_07 W4 完成，本項僅 doc 校對）

# E 議題群：CLAUDE.md 文件治理（ADR-SD08-001）
[  ] T0-E1 升級 tools/check_loc_budget.py 加入 SPECIAL_FILES = {"CLAUDE.md": 400}
[  ] T0-E2 新建 tools/snapshot_sync.py（從 wiring.py / ports/ / factory.py 自動回填 Snapshot 區段）
[  ] T0-E3 .github/workflows/autoclaude-ci.yml 新增 claude-md-budget job（ADR-SD08-001 §4）
[  ] T0-E4 CLAUDE.md 重整：
       (a) 加入頂端「快速導覽」3 行（規範看本檔 / sprint 脈絡看 sprint_history.md / 架構決策看 ADR/）
       (b) 加入 [Architecture Snapshot] SSOT 區段（LOC tiers + importlinter rules + Plugin list + Port list + DAL mode 矩陣）
       (c) SD_03 / SD_04 / SD_05 完整段落下沉至 sprint_history.md（保留一行 link）
       (d) 保留 SD_06 + SD_07 完整摘要（滾動窗口 N=2）
       (e) 驗證 wc -l CLAUDE.md ≤ 400
[  ] T0-E5 sprint_history.md 完整下沉 SD_03~SD_05（W0 骨架階段 v0.1 → v1.0）
[  ] T0-E6 補 tests/contract/test_claude_md_budget.py（≥ 3 case：wc-l ≤ 400 / Snapshot 區段格式 / 必留章節存在）

# ADR 落地
[  ] T0-ADR1 PM 形式核准 ADR-SD08-001（CLAUDE.md ≤ 400 + Snapshot SSOT）
[  ] T0-ADR2 PM 形式核准 ADR-SD08-002（mutation baseline 分模組目標）
[  ] T0-ADR3 PM 形式核准 ADR-SD08-003（perf regression p95 < 15%）
[  ] T0-ADR4 PM 形式核准 ADR-SD08-004（IObservabilityPort 設計）
[  ] T0-ADR5 PM 形式核准 ADR-SD08-005（PG 雙軌制 SD_09 啟用條件）

[  ] T0-9 撰寫 SD_08 AC Matrix scaffolding（≥ 8 條新增：AC7×3 可觀測性 / AC8×2 mutation / AC9×2 性能 / AC10×1 PG 前置）
[  ] T0-10 .env.example 補 OBSERVABILITY_BACKEND=local_logger + PG_WAL_LAG_WARN_SECONDS=2.0 + PG_WAL_LAG_CRITICAL_SECONDS=10.0
```

**G0 驗證**：
```bash
[  ] wc -l CLAUDE.md                                                       # ≤ 400
[  ] python tools/check_loc_budget.py                                       # violations=0（含 CLAUDE.md ≤ 400）
[  ] python -m pytest tests/contract/test_claude_md_budget.py -v            # ≥ 3 case 綠
[  ] ls docs/04_planning/ADR/ADR-SD08-*.md | wc -l                          # = 5
[  ] ls docs/05_development/sprint_history.md                               # 存在
[  ] grep -E "^### 1\.[1-3] SD_Improving_(03|04|05)" docs/05_development/sprint_history.md   # 3 行命中（完整下沉）
[  ] grep -rn "NOTE(SD_07) m-Arch3\|NOTE(SD_07) m-SD3" autoclaude/ tests/   # = 0（A 議題群完成）
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,015 passed（+3 W0 新測）
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # 6 kept / 0 broken
[  ] grep -E "claude-md-budget" .github/workflows/autoclaude-ci.yml                    # 命中
```

**G0 通過條件**：CLAUDE.md ≤ 400 ✅ / Snapshot SSOT 就位 / 5 條 ADR PM 形式核准 / sprint_history.md SD_03~SD_05 完整下沉 / claude-md-budget CI job 就位

---

### ── W1：Migration Guide v2 backlog 評估 + `_runner_internals` contract 文件化（B 議題群）──

**目標**：
- SD_07 Migration Guide §5 v2 backlog 三項各自決議
- `_runner_internals` contract 防復活柵欄文件化
- 必要時拆解 `_impl.py` / `pg_state` / `prompt_builder`（合規或加 override 書面理由）

**逐項打勾**：
```
[  ] T1-B1 git tag sd_08_w0_g0_pass（W1 前快照）
[  ] T1-B2 v2 backlog 第 1 項：_impl.py 進一步精簡（530 wc-l 邏輯行 ≤ 500 已合規 service tier）
       決議：(a) 合規即可，延 SD_09；或 (b) 進一步拆 _attempt_loop.py + _state_transitions.py（W1 PD 預估 2）
       建議：(a) 合規（PM 拍板優先 G+H 議題群，本項可延）
[  ] T1-B3 v2 backlog 第 2 項：`_runner_internals` contract 防復活柵欄文件化
       (a) 撰寫 docs/06_quality/Runner_Internals_Anti_Resurrection_Guard.md（importlinter Rule 3 + 6 + grep-based test 三層防護）
       (b) 引用 CLAUDE.md [Architecture Snapshot] importlinter rules 區段（W0 已建立）
[  ] T1-B4 v2 backlog 第 3 項：prompt_builder.py 416 LOC（純函數庫 ≤ 300 budget；W0 已 override service tier）
       決議：(a) 維持 .loc-budget.toml override（書面理由：純函式集中可讀性高於分散）；或 (b) 拆 _correction.py + _compact.py + _global_goal.py
       建議：(a) 維持 override（PM 拍板 G+H 優先）
[  ] T1-B5 撰寫 docs/06_quality/SD08_V2_Backlog_Evaluation.md（3 項決議紀錄）
[  ] T1-B6 importlinter 6 kept / 0 broken 維持
[  ] T1-B7 LOC violations=0 維持
```

**G1 驗證**：
```bash
[  ] ls docs/06_quality/Runner_Internals_Anti_Resurrection_Guard.md         # 存在
[  ] ls docs/06_quality/SD08_V2_Backlog_Evaluation.md                       # 存在
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # 6 kept / 0 broken
[  ] python tools/check_loc_budget.py                                       # violations=0
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,015 passed（持平 W0）
```

---

### ── W2：AC4 nightly 14 天採集 + labeled PR 觸發（C 議題群）──

**目標**：
- 14 天 nightly 連跑（recall@10 ≥ 0.95 + p95 < 50ms + recall σ ≤ 0.02 + CircuitBreaker open=0）
- 漸進式升級為 `needs-pg-e2e` labeled PR 觸發
- AC Matrix AC4-1/AC4-2 填入實測

**逐項打勾**：
```
[  ] T2-C1 git tag sd_08_w1_g1_pass
[  ] T2-C2 新建 tools/ac4_nightly_collector.py：
       - 解析 pg-e2e-nightly artifact（test_pgvector_real_recall.py 結果）
       - 累計 recall@10 / p95 / CircuitBreaker open 次數
       - 寫入 .ac4_history.jsonl（git ignore）
[  ] T2-C3 新建 tools/ac4_progress_check.py：
       - 讀 .ac4_history.jsonl 最近 14 天
       - 計算 recall σ_14d + 全綠連續天數
       - 判定告警等級（黃 3 次 / 紅 5 次）
[  ] T2-C4 .github/workflows/autoclaude-ci.yml 修正 pg-e2e-nightly job：
       - 加入 T2-C2 collector step（每 nightly 跑完寫入 history）
       - 加入 T2-C3 check step（告警通道）
[  ] T2-C5 新建 .github/workflows/autoclaude-pg-e2e-on-label.yml：
       - 觸發：pull_request types=[labeled]
       - condition: github.event.label.name == 'needs-pg-e2e'
       - 跑 tests/integration/test_pgvector_real_recall.py（已存在）
       - 14 天全綠後啟用此 workflow（W2 末 manual enable）
[  ] T2-C6 14 天觀察期執行（W2 排程連續 14 天 nightly；可與 W3-W6 並行）
[  ] T2-C7 W2 末 AC Matrix AC4-1/AC4-2 填入實測（推遲：實測需 14 天觀察期）
[  ] T2-C8 補 tests/contract/test_ac4_progress_check.py（≥ 4 case：未達 14 天 / 達 14 天 / 單日抖動 / CircuitBreaker open 觸發紅線）
```

**G2 驗證**：
```bash
[  ] ls tools/ac4_nightly_collector.py tools/ac4_progress_check.py          # 兩檔存在
[  ] ls .github/workflows/autoclaude-pg-e2e-on-label.yml                               # 存在
[  ] python -m pytest tests/contract/test_ac4_progress_check.py -v          # ≥ 4 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,025 passed（+10）
```

> **AC4 14 天全綠達標可延 W3-W6 並行觀察**；G2 通過僅需「工具就位 + 觀察期啟動 + 黃線告警設計」即可。

---

### ── W3：Mutation pilot — TokenGuardPlugin 單模組（D 議題群）──

**目標**：
- TokenGuardPlugin pilot 兩週 + 連續 7 次達 ≥ 70%（目標 -5%）
- 鎖定 `.mutation_baseline.toml`
- 補測 backlog 自動產出（survived diff 分類）

**逐項打勾**：
```
[  ] T3-D1 git tag sd_08_w2_g2_pass
[  ] T3-D2 修正 .github/workflows/autoclaude-ci.yml `mutation-test-nightly` job：
       - 限定 pilot 範圍：僅 TokenGuardPlugin（暫停 GoalSynthesis + Coordinator nightly）
       - 加入 -p no:xdist 鎖序列（ADR-SD08-002 §2.3）
       - 加入 --paths-to-mutate=autoclaude/plugins/token_guard --tests-dir=tests/plugins/token_guard
[  ] T3-D3 新建 tools/mutation_baseline_lock.py（ADR-SD08-002 §2.4 連續 7 次達標鎖定邏輯）
[  ] T3-D4 新建 tools/mutation_analysis.py（ADR-SD08-002 §2.5 survived diff 分類 + 補測 backlog 產出）
[  ] T3-D5 新建 .mutation_baseline.toml（初始空檔，W3 末寫入 token_guard 鎖定值）
[  ] T3-D6 新建 .mutation_history.jsonl（git ignore，CI artifact 累計）
[  ] T3-D7 W3 兩週 nightly 連跑（與 W4-W6 並行）
[  ] T3-D8 W3 末產出 docs/06_quality/SD08_Mutation_Baseline_Report.md（含 survived diff 分析 + 補測 backlog）
[  ] T3-D9 補 tests/contract/test_mutation_baseline_lock.py（≥ 4 case：未達 7 次 / 達 7 次 / 抖動單日不鎖 / 鎖後升級）
```

**G3 驗證**：
```bash
[  ] grep -E "paths-to-mutate=autoclaude/plugins/token_guard" .github/workflows/autoclaude-ci.yml   # 命中
[  ] grep -E "no:xdist" .github/workflows/autoclaude-ci.yml                            # 命中
[  ] ls tools/mutation_baseline_lock.py tools/mutation_analysis.py          # 兩檔存在
[  ] ls docs/06_quality/SD08_Mutation_Baseline_Report.md                    # 存在
[  ] python -m pytest tests/contract/test_mutation_baseline_lock.py -v      # ≥ 4 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,040 passed（+15）
```

> **G3 fall-back（R-SD08-PM-#3）**：若 W3 兩週仍未達 60% baseline，W3 末僅產出 Report 含 backlog，不阻塞 W4-W6；SD_09 接續 pilot。

---

### ── W4：可觀測性升級主項（F 議題群，核心 Wave）──

**目標**：
- 新建 `IObservabilityPort` + LocalLogger adapter（core/ports/ + infra/adapters/observability/）
- `trace_id: ContextVar` + EventBus 自動注入 + daemon thread 包裝
- KB metric 4 項（hit_rate / query_p95_ms / strategy_rotation_count / cache_eviction_count）
- AutoResume 健壯化（wake_kinds 擴展）
- importlinter Rule 7 強制 plugin 不可直接 import utils.observability

**W4 切兩階段**（連動 R-SD08-PM-#5 / #7）：

#### W4 上半（P0 必做）

```
# W4 上半（P0 必做，W4 中段必須完成，給 W5 WAL lag adapter 有 port 可依）
[  ] T4-F1 新建 autoclaude/core/ports/observability.py（IObservabilityPort Protocol + ISpan，≤ 150 LOC contract tier）
[  ] T4-F2 新建 autoclaude/infra/adapters/observability/__init__.py
[  ] T4-F3 新建 autoclaude/infra/adapters/observability/local_logger.py（LocalLogger 實作，≤ 200 LOC adapter tier）
[  ] T4-F4 新建 autoclaude/utils/trace_context.py（trace_id ContextVar + with_trace_id + run_in_thread_with_context，≤ 100 LOC）
[  ] T4-F5 autoclaude/core/wiring.py 注入 IObservabilityPort（建構式注入至 Kernel）
[  ] T4-F6 autoclaude/core/event_bus.py 修正 dispatch 自動注入 _trace_id（ADR-SD08-004 §2.3）
[  ] T4-F7 .importlinter 新增 Rule 7 plugin-no-utils-observability-direct-import
[  ] T4-F8 補 tests/core/test_observability_port.py（≥ 6 case：Protocol 合約 + LocalLogger emit / ContextVar 傳遞 / daemon thread 包裝）
```

#### W4 下半（P1 增強，可彈性延 SD_09）

```
[  ] T4-F9 新建 autoclaude/utils/knowledge_base_metrics.py（4 metric snapshot dict，≤ 100 LOC）
[  ] T4-F10 FailureKnowledgeBase 整合 emit_counter("kb_hit_total") + emit_histogram("kb_query_latency_ms")
[  ] T4-F11 NonBlockingStreamReader 改用 run_in_thread_with_context 包裝（PTY 邊界 trace_id 不斷鏈）
[  ] T4-F12 AutoResumeService 整合 emit_event("autoresume_wake") + wake_kinds 擴展
[  ] T4-F13 補 tests/utils/test_knowledge_base_metrics.py（≥ 4 case：4 metric 計算 / snapshot 一致 / hit_rate 邊界 0/1 / eviction 累計）
[  ] T4-F14 補 tests/utils/test_trace_context_daemon_thread.py（≥ 3 case：PTY daemon thread 不斷鏈 / copy_context() 顯式 / 並發 thread isolation）
```

**G4 驗證**：
```bash
# P0 必做
[  ] ls autoclaude/core/ports/observability.py                              # 存在
[  ] ls autoclaude/infra/adapters/observability/local_logger.py             # 存在
[  ] ls autoclaude/utils/trace_context.py                                   # 存在
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # 7 kept / 0 broken（Rule 7 新增）
[  ] python -m pytest tests/core/test_observability_port.py -v              # ≥ 6 case 綠

# P1 增強（若 W4 完整完成）
[  ] ls autoclaude/utils/knowledge_base_metrics.py                          # 存在
[  ] python -m pytest tests/utils/test_knowledge_base_metrics.py -v         # ≥ 4 case 綠
[  ] python -m pytest tests/utils/test_trace_context_daemon_thread.py -v    # ≥ 3 case 綠

[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,065 passed（+25）
[  ] python tools/check_loc_budget.py                                       # violations=0
```

**⚠️ G4 強制阻塞**：紅線 ❌18 違反（IObservabilityPort 放錯層）→ G4 不放行 + git revert HEAD

---

### ── W5：性能 baseline + WAL lag adapter + ADR-SD08-005 草案（G + H 前置議題群）──

**目標**：
- `tools/perf_baseline.py` + 4 場景量測 + `perf-baseline-nightly` CI job
- `tools/perf_regression_check.py`（annotation + PR comment 雙通道，p95 < 15%）
- `autoclaude/infra/observability/pg_health.py` WAL lag adapter（SD_09 前置）
- `ADR-SD08-005` PM 形式核准 + `Production_Migration_SOP.md` §1-§3 草案

**逐項打勾**：
```
# G 議題群：性能 baseline（ADR-SD08-003）
[  ] T5-G1 新建 autoclaude/utils/perf_baseline.py（PerfBaseline dataclass + measure() helper，≤ 150 LOC）
[  ] T5-G2 新建 tests/perf/test_dry_run_e2e.py（≥ 1 case，pytest-benchmark）
[  ] T5-G3 新建 tests/perf/test_token_halt_roundtrip.py（≥ 1 case）
[  ] T5-G4 新建 tests/perf/test_decide_correction.py（≥ 1 case）
[  ] T5-G5 新建 tests/perf/test_pgvector_recall_perf.py（≥ 1 case，pg_real marker，僅 perf machine 跑）
[  ] T5-G6 新建 tools/perf_regression_check.py（annotation + PR comment 雙通道）
[  ] T5-G7 .github/workflows/autoclaude-ci.yml 新增 perf-baseline-nightly job（ADR-SD08-003 §3）
[  ] T5-G8 W5 首次跑 7 次連續，鎖定 .perf_baseline.toml
[  ] T5-G9 補 tests/contract/test_perf_regression_check.py（≥ 4 case：通過 / 警告 / 阻塞 / 缺 baseline）
[  ] T5-G10 產 docs/06_quality/SD08_Perf_Baseline_Report.md

# H 議題群前置：WAL lag adapter（ADR-SD08-005）
[  ] T5-H1 新建 autoclaude/infra/observability/__init__.py
[  ] T5-H2 新建 autoclaude/infra/observability/pg_health.py（PgHealthMonitor Protocol + DefaultPgHealthMonitor，≤ 200 LOC adapter tier）
[  ] T5-H3 PgHealthMonitor 透過 IObservabilityPort emit_counter("pg_wal_lag_warn") / emit_counter("pg_wal_lag_critical")
[  ] T5-H4 補 tests/infra/test_pg_health.py（≥ 5 case：lag < 2s 正常 / 2-10s warn / > 10s critical / connection count / fixture mock pg）
[  ] T5-H5 新建 docs/08_deployment/Production_Migration_SOP.md §1-§3 草案
[  ] T5-H6 ADR-SD08-005 PM 形式核准（W5 G5 簽核紀錄）
[  ] T5-H7 補 tests/contract/test_pg_migration_sop_dry_run.py（≥ 2 case：§1 前置 checklist / §2 灰度啟動 dual_write_strict）
```

**G5 驗證**：
```bash
# G 議題群
[  ] ls autoclaude/utils/perf_baseline.py tools/perf_regression_check.py    # 兩檔存在
[  ] ls tests/perf/*.py | wc -l                                             # ≥ 4
[  ] ls .perf_baseline.toml                                                 # 存在（W5 末鎖定）
[  ] grep -E "perf-baseline-nightly" .github/workflows/autoclaude-ci.yml               # 命中
[  ] python -m pytest tests/contract/test_perf_regression_check.py -v       # ≥ 4 case 綠

# H 議題群前置
[  ] ls autoclaude/infra/observability/pg_health.py                         # 存在
[  ] python -m pytest tests/infra/test_pg_health.py -v                      # ≥ 5 case 綠
[  ] ls docs/08_deployment/Production_Migration_SOP.md                      # 存在
[  ] python -m pytest tests/contract/test_pg_migration_sop_dry_run.py -v    # ≥ 2 case 綠

[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,085 passed（+20）
```

> **W5 強制交付**（R-SD08-PM-#4）：(a) pg_health.py + (b) ADR-SD08-005 PM 核准 + (c) SOP §1-§3 草案。三項缺一不可。

---

### ── W6：Migration Guide v1.0 + Sprint 收尾 + 四方審查 ──

**目標**：
- 撰寫 docs/08_deployment/SD08_Migration_Guide.md v1.0
- AC Matrix 擴增至 ≥ 27 條（SD_07 19 + SD_08 新增 ≥ 8 條）
- 四方審查（Architect / SA / SD / QA）APPROVED + PM 簽核
- gate_audit + risk_log 完成更新
- 滾動下沉：SD_06 完整摘要從 CLAUDE.md 下沉至 sprint_history.md（保留 SD_07 + SD_08 滾動窗口）

**逐項打勾**：
```
[  ] T6-1 git tag sd_08_w5_g5_pass（W6 收尾前快照）
[  ] T6-2 撰寫 docs/08_deployment/SD08_Migration_Guide.md v1.0：
       - §1 W0~W6 完成範圍
       - §2 Breaking Changes（IObservabilityPort 新增 + Rule 7 importlinter / CLAUDE.md ≤ 400 / mutation pilot 啟用）
       - §3 新增 API（IObservabilityPort / trace_id ContextVar / KnowledgeBaseMetrics / PgHealthMonitor / PerfBaseline）
       - §4 升級步驟（plugin 改建構式注入 IObservabilityPort + PTY daemon thread 包裝 + CLAUDE.md 行數壓縮）
       - §5 SD_09 延期清單（H 議題群完整 SOP + mutation 擴展至 GoalSynthesis + Coordinator + perf machine 採購評估）
       - §6 G6 實測結果
       - §7 已知限制（trace_id 在 multi-process subprocess 邊界不傳播 / KB metric 純記憶體統計）
       - §8 文件版本歷史
[  ] T6-3 撰寫 docs/03_testing/SD08_AC_Matrix.md：
       - AC7×3 可觀測性（IObservabilityPort Protocol / trace_id daemon thread 不斷鏈 / KB metric 4 項）
       - AC8×2 mutation（TokenGuardPlugin ≥ 70% / .mutation_baseline.toml 鎖定）
       - AC9×2 性能（4 場景 baseline 鎖定 / p95 < 15% 告警）
       - AC10×1 PG 前置（pg_health.py WAL lag 三閾值）
[  ] T6-4 更新 CLAUDE.md：
       (a) 加入 SD_Improving_08 W0~W6 摘要區段
       (b) 將 SD_06 完整摘要下沉至 sprint_history.md §1.4（滾動窗口 N=2，CLAUDE.md 僅留 SD_07 + SD_08）
       (c) 同步 [Architecture Snapshot] SSOT 區段（執行 python tools/snapshot_sync.py）
       (d) 驗證 wc -l CLAUDE.md ≤ 400
[  ] T6-5 更新 gate_audit.md §1-sexies 補 SD08-G0~G6 簽核
[  ] T6-6 更新 risk_log.md §14 標所有 R-SD08-* 為 CLOSED（依 Wave 完成）
[  ] T6-7 更新 sprint_history.md：
       - SD_06 完整摘要從 CLAUDE.md 搬移至 §1.4（W6 滾動下沉動作）
       - SD_Improving_08 §1.6 補完（W0~W6 詳細紀錄）
       - 議題索引表 §2 新增 SD_08 對應條目
[  ] T6-8 四方審查（Architect / SA / SD / QA 4/4 APPROVED）
[  ] T6-9 PM 簽核（場景 A：個人開發）
```

**G6 最終驗證**：
```bash
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,100 passed
[  ] python -m pytest tests/equivalence/ -q --tb=no                         # 83/83 全綠（無變動）
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # 7 kept / 0 broken
[  ] python tools/check_loc_budget.py                                       # violations=0
[  ] wc -l CLAUDE.md                                                        # ≤ 400
[  ] grep -rn "NOTE(SD_08)" autoclaude/ tests/ | wc -l                      # = 0
[  ] ls autoclaude/core/ports/observability.py                              # 存在
[  ] ls autoclaude/utils/trace_context.py autoclaude/utils/knowledge_base_metrics.py   # 存在
[  ] ls autoclaude/infra/observability/pg_health.py                         # 存在
[  ] ls .perf_baseline.toml .mutation_baseline.toml                         # 存在
[  ] ls docs/08_deployment/SD08_Migration_Guide.md                          # 存在
[  ] ls docs/03_testing/SD08_AC_Matrix.md                                   # 存在
[  ] ls docs/08_deployment/Production_Migration_SOP.md                      # 存在（§1-§3 草案）
[  ] grep -E "^### 1\.4 SD_Improving_06" docs/05_development/sprint_history.md   # 命中（SD_06 已下沉）
[  ] grep -E "^### 1\.6 SD_Improving_08" docs/05_development/sprint_history.md   # 命中（SD_08 已補完）
```

---

## 4. 波次間 Session 切換協議

每個 Wave 開始前（切換新 Opus 4.7 session）：

```
我正在執行 SD_Improving_08 [W編號]（[波次名稱]）。

當前狀態：
- 測試基線：[當前 passed 數] / [skipped 數]
- 前一 Gate 已通過：G[n]
- 當前 Wave 目標：[複製上方 Wave 目標清單]
- PM 拍板事項：[列出本 Wave 對應 PM 決議]
- 對應 ADR：[列出本 Wave 對應 ADR-SD08-XXX]

請先執行 §0 前置確認：
python -m pytest tests/ -q --tb=no | tail -3
PYTHONUTF8=1 lint-imports --config .importlinter
python tools/check_loc_budget.py
wc -l CLAUDE.md

確認後依照 SD08_Execution_Guide.md W[n] 逐項打勾執行。
```

---

## 5. 緊急停止與回退協議

| 觸發條件 | 立即執行 |
|---------|---------|
| equivalence 83 fixture 任一斷裂 | `git revert HEAD`；找 SA + QA 雙簽才可重啟 |
| importlinter broken | `git stash`；找 Architect 確認再重試 |
| 全測數量下降 | `git stash`；找出哪個測試被移除/跳過 |
| CLAUDE.md > 400 行 | 立即下沉至 sprint_history.md（紅線 ❌17）|
| W4 IObservabilityPort 放錯層（utils 而非 core/ports）| `git revert HEAD`（紅線 ❌18）找 Architect 確認 |
| W3 mutation 一次啟用 3 模組 | `git revert HEAD`（紅線 ❌19）回 pilot 單模組 |
| W5 內推進 PG db_only 切換 | `git revert HEAD`（紅線 ❌20）切換禁止延 SD_09 |
| W4 P0 部分超預期 | 切「P0 必做」上半 + 「P1 增強」下半 + 1.5 PD contingency；P1 可延 SD_09（R-SD08-PM-#5/#7）|
| W3 mutation < 60% baseline | Fall-back：W3 末僅產出 Report 含 backlog，不阻塞 W4-W6（R-SD08-PM-#3）|
| 任何 3 個連續 commit 仍紅 | 停止當前 Wave，回退至前一 G-gate commit |

```bash
# 找到前一 Gate 的 commit
git log --oneline | grep "G[0-6]\|sd_08"

# 回退（確認無誤後）
git reset --hard <commit-hash>
```

---

## 6. 進度追蹤表

| Wave | 狀態 | 通過日期 | 測試基線 | PM 對應項 | 對應 ADR | 備注 |
|------|------|---------|---------|----------|---------|------|
| W0 | 📋 啟動日 2026-05-21 | — | 2,012 → 預估 +3 | #1 CLAUDE.md / #7 優先順序 | ADR-SD08-001 | SD_07 遺留 + CLAUDE.md ≤ 400 + sprint_history.md + 5 ADR PM 核准 |
| W1 | 📋 待 W0 | — | 預估 ≥ 2,015（持平）| — | — | Migration Guide v2 backlog 評估 + `_runner_internals` 文件化 |
| W2 | 📋 待 W1 | — | 預估 ≥ 2,025 | #2 AC4 漸進式 | — | AC4 nightly 14 天採集 + labeled PR 觸發 |
| W3 | 📋 待 W2 | — | 預估 ≥ 2,040 | #3 mutation 分模組 | ADR-SD08-002 | TokenGuardPlugin pilot 兩週 + baseline 鎖定 |
| W4 | 📋 待 W3 | — | 預估 ≥ 2,065 | #5 可觀測性階段性混合 | ADR-SD08-004 | IObservabilityPort + trace_id + KB metric + Rule 7（核心 Wave）|
| W5 | 📋 待 W4 | — | 預估 ≥ 2,085 | #4 PG 延 SD_09 / #6 perf 雙軌 | ADR-SD08-003 + 005 | perf baseline 4 場景 + WAL lag adapter + SOP 草案 |
| W6 | 📋 待 W5 | — | 預估 ≥ 2,100 | — | — | Migration Guide v1.0 + 四方審查 + SD_06 滾動下沉 |

---

## 7. 前置已就緒項目（無需重做）

| 項目 | 狀態 | 說明 |
|------|------|------|
| ADR-SD08-001 ~ 005 草案 | ✅ | 2026-05-18 完成（待 W0 PM 形式核准）|
| sprint_history.md 骨架 v0.1 | ✅ | 2026-05-18 完成（待 W0 T0-E5 完整下沉 SD_03~SD_05 → v1.0）|
| OrchestrationCoordinator | ✅ | SD_06 W1 G1 已就位（232 LOC ≤ 250）|
| PG 三層 schema | ✅ | SD_06 W3 G3 已就位（alembic 0007-0014） |
| IEmbedder/IVectorSearch + 雙 adapter | ✅ | SD_06 W3 G3 已就位（CircuitBreaker） |
| ExecutionContext + dual_state drift + drift_log | ✅ | SD_06 W5 G5 已就位（365 天 partition） |
| ConfigResolver 4 層 + Pydantic v2 invariants | ✅ | SD_06 W5 G5 已就位 |
| ADR-SD07-001 LOC 政策 | ✅ | SD_07 W0 已三方共識 + PM 形式核准 |
| importlinter 6 kept + LOC baseline 永久鎖定 14058 | ✅ | SD_07 W5 完成 |
| mutation-test-nightly + pg-e2e-nightly CI job | ✅ | SD_07 W2/W5 已建立（W3 修正為 pilot，W2 修正為 labeled PR）|
| PM 拍板 8 項（SD_08）| ✅ | 2026-05-18 全數 APPROVED |
| 三方獨立研究 + QA 量測可行性 | ✅ | 2026-05-18 完成（Architect/SA/SD/QA 四方）|

---

## 8. 關鍵風險即時監控（每 Wave 末複查）

```
[ Wave W0 ] R-SD08-A-1 — sprint_history.md 是否完整下沉 SD_03~SD_05？快速導覽 3 行是否就位？
[ Wave W0 ] R-SD08-E-1 — claude-md-budget CI 是否強制 ≤ 400？snapshot_sync.py 是否可運作？
[ Wave W1 ] — Migration Guide v2 backlog 3 項是否各有決議文件？
[ Wave W2 ] R-SD08-C-1 — pg-e2e-nightly 是否至少跑 1 次成功？14 天觀察期是否啟動？
[ Wave W3 ] R-SD08-D-1/D-2 — mutmut wall time ≤ 40 min？token_guard 首測是否 ≥ 65%？
[ Wave W4 ] R-SD08-F-1/F-2 — trace_id 在 PTY daemon thread 是否不斷鏈？IObservabilityPort 是否在 core/ports/？
[ Wave W4 ] R-SD08-PM-#5/#7 — P0 上半是否 W4 中段完成？P1 下半是否需延 SD_09？
[ Wave W5 ] R-SD08-G-1 — pgvector p95 是否強制延 perf machine？CI 僅跑 CPU-bound？
[ Wave W5 ] R-SD08-H-1/PM-#4 — pg_health.py + ADR-SD08-005 + SOP §1-§3 草案是否三項齊備？
[ Wave W6 ] — SD_06 完整摘要是否滾動下沉？SD_08 §1.6 是否補完？議題索引表是否更新？
```

---

**對應參考文件**：
- [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0 — 主規劃文件
- [ADR-SD08-001-claude-md-budget.md](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) — CLAUDE.md ≤ 400 + Snapshot SSOT
- [ADR-SD08-002-mutation-baseline.md](../04_planning/ADR/ADR-SD08-002-mutation-baseline.md) — mutation 分模組目標 + pilot
- [ADR-SD08-003-perf-regression-policy.md](../04_planning/ADR/ADR-SD08-003-perf-regression-policy.md) — perf p95 < 15% + 雙軌
- [ADR-SD08-004-observability-port.md](../04_planning/ADR/ADR-SD08-004-observability-port.md) — IObservabilityPort 設計
- [ADR-SD08-005-pg-production-dual-track.md](../04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md) — PG 雙軌制 SD_09 啟用條件
- [SD07_Execution_Guide.md](SD07_Execution_Guide.md) v1.0 — 前置 Sprint 執行範本
- [sprint_history.md](sprint_history.md) v0.1 — SD_03 起完整紀錄（W0 完整下沉）
- [risk_log.md](risk_log.md) §14 — SD_08 風險條目
- [gate_audit.md](gate_audit.md) §1-sexies — SD_08 Gates

---

**文檔元數據**：
- 文件版本：v1.0
- 建立日期：2026-05-18
- 對應規劃版本：SD_Improving_08.md v1.0
- G0 啟動日：2026-05-21
- 維護者：Tech Lead + PM 共同維護
