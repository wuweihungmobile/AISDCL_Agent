# SD_Improving_08 Mutation Baseline Report — TokenGuardPlugin Pilot

| 項目 | 內容 |
|------|------|
| 文件版本 | v0.1（W3 G3 工具就位版本，2026-05-18） |
| 對應 Wave | SD_08 W3（D 議題群 — mutation pilot） |
| 對應 ADR | [ADR-SD08-002](../04_planning/ADR/ADR-SD08-002-mutation-baseline.md) v1.0 |
| 狀態 | **工具就位 + observing**（兩週 nightly 觀察期啟動，與 W4-W6 並行累計） |
| Pilot 範圍 | **僅 TokenGuardPlugin SSOT**（`autoclaude/plugins/token_guard/`，5 子模組） |

---

## 1. 背景與目標

SD_07 W5 T5-6 已建 `mutation-test-nightly` CI job（3 模組 SSOT），但未設 kill rate baseline。QA 量測可行性研究指出：
- mutmut 每 mutation 跑全測 ~100s，3 模組同時 nightly 風險過高（11-17 hr 遠超 45 min 上限）
- 語意等價突變使 coverage 100% ≠ mutation 100%（boundary `>=` vs `>` / dead branch）

PM 拍板（SD_08 #3）：**分模組差異化目標 + W3 pilot 單模組兩週 + continue-on-error 維持非阻塞**。

### 1.1 分模組目標（ADR-SD08-002 §2.1）

| 模組 | LOC | 目標 kill rate | 容忍門檻（鎖定條件） |
|------|-----|---------------|--------------------|
| **TokenGuardPlugin**（pilot）| ~250 | ≥ 75% | 連續 7 次 ≥ 70% |
| GoalSynthesisPlugin（延 SD_09）| ~180 | ≥ 70% | 連續 7 次 ≥ 65% |
| OrchestrationCoordinator（延 SD_09）| ~230 | ≥ 65% | 連續 7 次 ≥ 60% |

---

## 2. W3 落地（2026-05-18 T3-D 任務完成）

### 2.1 CI job 修正（T3-D2）

`.github/workflows/autoclaude-ci.yml` `mutation-test-nightly` job：
- **Pilot 限定**：僅跑 TokenGuardPlugin（GoalSynthesis / Coordinator 兩個 step 暫停，延至 SD_09 啟用）
- **mutmut 參數鎖定**：
  - `--paths-to-mutate=autoclaude/plugins/token_guard`（範圍縮限）
  - `--tests-dir=tests/plugins/token_guard`（對位測試集）
  - `--no-progress`（CI 無 TTY）
  - `-p no:xdist`（鎖序列避免 hash 衝突）
- **新增 steps**：
  - `python tools/mutation_baseline_lock.py token_guard` — 連續 7 次達標鎖定
  - `python tools/mutation_analysis.py token_guard` — survived diff 分類補測 backlog

### 2.2 工具落地

| 檔案 | 行為 | 對應 task |
|------|------|----------|
| `tools/mutation_baseline_lock.py` | 解析 mutmut log → kill_rate → 累計 `.mutation_history.jsonl` → 連續 7 次達標寫入 `.mutation_baseline.toml`（取 min 最保守） | T3-D3 |
| `tools/mutation_analysis.py` | 解析 survived mutation → 分類（boundary / constant / dead_branch / string_literal） → 產出 `mutation_backlog_*.md` 補測 backlog | T3-D4 |
| `.mutation_baseline.toml` | baseline 鎖定值（初始空 `[scores]`） | T3-D5 |
| `.mutation_history.jsonl` | 歷次 kill_rate 累計（git ignore，CI artifact 為 SSOT） | T3-D6 |
| `tests/contract/test_mutation_baseline_lock.py` | 11 case：4 主流程 + 7 補強（parse / classify / lock 邏輯） | T3-D9 |

---

## 3. 觀察期啟動（2026-05-19 nightly 起算）

### 3.1 連續 7 次達標鎖定邏輯（ADR-SD08-002 §2.4）

```python
# 簡化版邏輯（tools/mutation_baseline_lock.py:should_lock）
if len(history) >= 7 and all(rate >= TARGET[m] - 0.05 for rate in history[-7:]):
    baseline = min(history[-7:])  # 取最保守值（避免單日抖動誤鎖過嚴）
    write_baseline(baseline)
```

**目標 -5% 容忍**：TokenGuard 目標 75% → 連續 7 次 ≥ 70% 才鎖定。

### 3.2 觀察期里程碑

| 日期 | nightly 次數 | 預期狀態 |
|------|-------------|---------|
| 2026-05-19 | 1/7 | observing |
| 2026-05-25 | 7/7 | 首次評估鎖定 |
| 2026-06-01 | 14/14（兩週末）| W3 末判定鎖定/fall-back |

### 3.3 Fall-back 策略（R-SD08-PM-#3）

若 W3 兩週仍未達 60% baseline：
- W3 末 G3 僅產出 Report 含 backlog，**不阻塞** W4-W6
- 補測 backlog 進入 SD_09 接續 pilot
- `.mutation_baseline.toml` 維持空 `[scores]`

---

## 4. survived diff 分類策略（ADR-SD08-002 §2.5）

`tools/mutation_analysis.py` 對 survived mutation 自動分類：

| 分類 | 範例 | 處理動作 |
|------|------|---------|
| **boundary** | `>=` ↔ `>` / `<` ↔ `<=` | ✅ 必補 — boundary 條件補測 |
| **constant** | `True` ↔ `False` / `0` ↔ `1` / `None` | ✅ 必補 — 常量翻轉斷言 |
| **dead_branch** | `if/elif` 永真/永假 | ✅ 必補 — 分支可達性測試 |
| **string_literal** | log/error message 文字替換 | ⏭️ ignore — 語意無關 |
| **other** | 其他 | 🟡 人工分類 |

產出路徑：CI artifact `mutation_backlog_token_guard.md`（30 天 retention）。

---

## 5. 紅線監控（每 nightly 末複查）

| 紅線 | 觸發條件 | 處理 |
|------|---------|------|
| ❌19 | mutation pilot 一次啟用 3 模組 nightly | `git revert HEAD` 回 pilot 單模組 |
| R-SD08-D-1 | 首測 < 65%（語意等價突變過多）| 補測 backlog 自動產出；W3 不阻塞 |
| R-SD08-D-2 | 單模組 wall time > 45 min | `--paths-to-mutate` + `--tests-dir` 對位縮限至 30-50 min |
| 抖動誤鎖 | 連續 7 次達標被單日峰值誤鎖過嚴 | 目標 -5% 容忍 + 取 min 為 baseline |

---

## 6. SD_09 延期清單

| 項目 | 延期理由 |
|------|---------|
| GoalSynthesisPlugin nightly mutmut | W3 pilot 單模組驗證模式可行性後再啟用 |
| OrchestrationCoordinator nightly mutmut | 同上；phase routing 天然難殺，預期 baseline 較低 |
| 升級為 PR 阻塞門 | 任一模組 baseline 鎖定後，SD_10+ 視結果決議 |
| mutation report 自動評論 PR | SD_09 結合 GitHub Action annotation 雙通道 |

---

## 7. 簽核

| 角色 | 狀態 | 日期 |
|------|------|------|
| QA | ✅ 量測可行性主導 + contract test 設計 | 2026-05-18 |
| SD | ✅ 補測策略共識 | 2026-05-18 |
| Architect | ✅ pilot 範圍限定共識 | 2026-05-18 |
| PM | ✅ 形式核准（場景 A 個人開發 dev 自核）| 2026-05-18 |

---

## 8. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v0.1 | 2026-05-18 | W3 G3 工具就位版本 — CI job 修正 / 2 tool 落地 / 11 contract case 全綠 / 觀察期啟動 |
| v1.0（預計）| 2026-06-01 | W3 末實測：基線鎖定 OR fall-back 至 SD_09 |

---

**相關文件**：
- [ADR-SD08-002-mutation-baseline.md](../04_planning/ADR/ADR-SD08-002-mutation-baseline.md) v1.0
- [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0 §6 PM #3
- [SD08_Execution_Guide.md](../05_development/SD08_Execution_Guide.md) v1.0 §3 W3
- `.github/workflows/autoclaude-ci.yml` `mutation-test-nightly` job
