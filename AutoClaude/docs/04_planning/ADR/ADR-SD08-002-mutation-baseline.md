# ADR-SD08-002：Mutation Score Baseline — 分模組差異化 + W3 pilot + 連續 7 次達標鎖定

| 項目 | 內容 |
|------|------|
| 狀態 | **APPROVED（PM 形式核准 / 場景 A 個人開發 dev 自核 2026-05-18）** |
| 建立日期 | 2026-05-18 |
| 對應 PM 拍板 | SD_08 PM #3（分模組差異化 + W3 pilot + continue-on-error 維持）|
| 提案人 | QA（量測可行性主導）|
| 核准日期 | 2026-05-18（SD_08 W0 T0-ADR2）|

---

## 1. 背景

- SD_07 W5 T5-6 已建 `mutation-test-nightly` CI job（cron + workflow_dispatch + continue-on-error=true 非阻塞）
- 3 目標 SSOT：TokenGuardPlugin / GoalSynthesisPlugin / OrchestrationCoordinator
- **QA 量測可行性警示**：3 模組同時 nightly 風險過高（mutmut 每 mutation 跑全測 2,012 case ~100s，token_guard 預估 400-600 mutation × 100s = 11-17 hr，遠超 45 min 上限）
- **語意等價突變**：coverage 100% ≠ mutation 100%（boundary `>=` vs `>` / dead branch），預期 token_guard 首測落 65-72%

## 2. 決議

### 2.1 分模組差異化目標

| 模組 | LOC | 目標 kill rate | 理由 |
|------|-----|---------------|------|
| **TokenGuardPlugin SSOT**（`autoclaude/plugins/token_guard/`）| ~250 | **≥ 75%** | 邏輯密度高 + 既有 coverage 100% + 5 子模組純函式為主，較易殺 |
| **GoalSynthesisPlugin SSOT**（`autoclaude/plugins/goal_synthesis_plugin.py`）| ~180 | **≥ 70%** | 字串處理 + prompt 拼接，部分突變語意等價 |
| **OrchestrationCoordinator SSOT**（`autoclaude/core/orchestration/`）| ~230 | **≥ 65%** | phase routing + enum 比較天然難殺（return 順序、enum 等價）|

統一 70% 對 Coordinator 過嚴、對 TokenGuard 過鬆 → 必須差異化。

### 2.2 W3 pilot 策略（單模組兩週）

W3 不一次啟用 3 模組 nightly mutmut，改為：

| Phase | Wave | 範圍 | 目標 |
|-------|------|------|------|
| **Pilot** | SD_08 W3（2 週）| 僅 **TokenGuardPlugin** 跑 nightly mutmut | 連續 7 次達 ≥ 70%（目標 -5% 為鎖定門檻）|
| **W3 末** | SD_08 W3 G3 | 鎖定 `.mutation_baseline.toml` 寫入 token_guard 實測值 | 揭露門檻（continue-on-error 維持）|
| **擴展** | SD_09 | 啟用 GoalSynthesis + Coordinator nightly mutmut | 同模式分批 pilot |
| **阻塞** | SD_10+ | 任一模組 baseline 達標後升級為 PR 阻塞門 | 視 SD_09 結果決議 |

### 2.3 mutmut 參數鎖定（必要縮限）

W3 強制使用以下 mutmut 命令（避免單模組超 45 min 上限）：

```bash
mutmut run \
  --paths-to-mutate=autoclaude/plugins/token_guard \
  --tests-dir=tests/plugins/token_guard \
  --no-progress \
  -p no:xdist  # 鎖 pytest 序列執行避免 hash 衝突（QA 警示）
```

**禁止**：
- ❌ `--paths-to-mutate=autoclaude/`（範圍過大，必爆 45 min）
- ❌ 跑全測 `--tests-dir=tests/`（mutation 與 test 必須**對位**至 SSOT 測試集）
- ❌ 平行執行（mutmut 多執行緒 hash 衝突，cosmic-ray 雖較穩但學習成本高 W3 不切換）

### 2.4 連續 7 次達標鎖定

W3 期間每 nightly 跑完後：

```python
# tools/mutation_baseline_lock.py（W3 新建）
def update_baseline(module: str, current_score: float):
    history = load_history(module)  # 讀 .mutation_history.jsonl 最近 7 次
    history.append(current_score)

    if len(history) >= 7 and all(s >= TARGET[module] - 0.05 for s in history[-7:]):
        # 連續 7 次達標（目標 -5% 容忍）→ 寫入 baseline
        baseline = min(history[-7:])  # 取最保守值
        write_baseline(module, baseline)
        print(f"::notice::{module} baseline locked at {baseline:.2%}")
```

**目標 -5% 容忍**：TokenGuard 目標 75% → 連續 7 次 ≥ 70% 才鎖（避免單日抖動誤鎖過嚴）

### 2.5 補測策略（survived diff）

W3 末若 score < 目標：

```bash
# tools/mutation_analysis.py（W3 新建）
# 1. 解析 mutation_token_guard.log
# 2. 分類 survived mutation：
#    (a) boundary（>=/> / </<=）
#    (b) constant（True/False / 0/1）
#    (c) dead_branch（if/elif 永真/永假）
#    (d) string_literal（log/error message）
# 3. 對 (a)/(b)/(c) 自動產 補測 backlog（tests/plugins/token_guard/test_<submodule>_mutation_補.py 草稿）
# 4. (d) 標 "ignore"（語意無關）
```

## 3. CI Job 修正

`.github/workflows/ci.yml` 既有 `mutation-test-nightly` job 微調（W3 落地）：

```yaml
mutation-test-nightly:
  # W3 修正：先僅跑 TokenGuardPlugin pilot
  steps:
    - name: Run mutation test - TokenGuardPlugin SSOT (pilot)
      run: |
        mutmut run --paths-to-mutate=autoclaude/plugins/token_guard \
                   --tests-dir=tests/plugins/token_guard \
                   --no-progress \
                   -p no:xdist || true
        mutmut results | tee mutation_token_guard.log

    # SD_09 啟用後再恢復 GoalSynthesis + Coordinator 兩 steps
    # - name: Run mutation test - GoalSynthesisPlugin SSOT
    # - name: Run mutation test - OrchestrationCoordinator SSOT

    - name: Lock baseline if 7 consecutive runs ≥ target
      run: python tools/mutation_baseline_lock.py token_guard
```

## 4. 落地 Checklist（W3 task breakdown）

```
[  ] T3-D1 既有 mutation-test-nightly job 修正為 pilot 模式（限 TokenGuardPlugin）
[  ] T3-D2 新建 tools/mutation_baseline_lock.py（連續 7 次達標鎖定邏輯）
[  ] T3-D3 新建 tools/mutation_analysis.py（survived diff 分類 + 補測 backlog 產出）
[  ] T3-D4 新建 .mutation_baseline.toml（W3 末寫入 token_guard 鎖定值）
[  ] T3-D5 新建 .mutation_history.jsonl 持久化最近 7 次 score（git ignore，CI artifact）
[  ] T3-D6 補 tests/contract/test_mutation_baseline_lock.py（≥ 4 case：未達 7 次 / 達 7 次 / 抖動單日不鎖 / 鎖後升級）
[  ] T3-D7 產 docs/06_quality/SD08_Mutation_Baseline_Report.md（W3 末，含 survived diff 分析）
```

## 5. 退化風險緩解（連動 R-SD08-D-1 / R-SD08-D-2）

| 風險 | 緩解 |
|------|------|
| 首測 < 65%（語意等價突變）| 補測 backlog 自動產出 + W3 不阻塞（揭露門檻）|
| 單模組超 45 min CI 上限 | `--paths-to-mutate` + `--tests-dir` 縮限至對位測試集（30-50 min/模組）|
| mutmut hash 衝突 | `-p no:xdist` 鎖序列 |
| 連續 7 次達標被單日抖動誤鎖 | 目標 -5% 容忍 + 取最保守值（min 取代 avg）|
| W3 兩週仍未達 60% baseline | Fall-back（R-SD08-PM-#3）：W3 末僅產出 Report 含 backlog，不阻塞 W4-W6；SD_09 接續 pilot |

## 6. 簽核

| 角色 | 狀態 | 日期 |
|------|------|------|
| QA | ✅ 量測可行性主導 | 2026-05-18 |
| SD | ✅ 共識（補測策略一致）| 2026-05-18 |
| PM | ✅ 形式核准（場景 A 個人開發 dev 自核）| 2026-05-18 |

---

**相關文件**：
- [SD_Improving_08.md](../SD_Improving_08.md) v1.0 §6 PM 拍板 #3
- `.github/workflows/ci.yml` `mutation-test-nightly` job（SD_07 W5 T5-6 既建）
