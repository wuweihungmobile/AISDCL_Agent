# ADR-SD09-002 — mutation 全模組擴展策略

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0（PM 形式核准 2026-05-20）** |
| 建立日期 | 2026-05-19 |
| 最後更新 | **2026-05-20**（T0-7 PM 形式核准）（二輪四方審查修復：TG fall-back 處理矩陣 + UTC cron 排程 + 多檔模式 + nightly 失敗處理）|
| 狀態 | **ACCEPTED — PM 形式核准 2026-05-20（場景 A dev 自核）** |
| 對應 Sprint | SD_Improving_09 議題 B（mutation pilot 擴展）|
| 前置 | [ADR-SD08-002](ADR-SD08-002-mutation-baseline.md) v1.0 |

---

## §1. 背景

SD_08 W3 完成 TokenGuardPlugin mutation pilot（觀察期 2026-05-19~2026-06-01）；SD_09 W1-W2 擴展至 GoalSynthesisPlugin + OrchestrationCoordinator。

首輪四方審查（Architect M2 / QA M6）指出：**並行 nightly 超時風險** — TokenGuard + GoalSynthesis + Coordinator 三 step 串聯極可能超 45 min；ADR-SD08-002 §2.2「一次不啟用 ≥ 2 模組 nightly」與 SD_09 並行擴展衝突。

---

## §2. 決策

### §2.1 單模組 active pilot 規則（紅線 ❌19）

任何時刻，nightly mutation job 僅 **1 個 active pilot module**：
- W1：GoalSynthesisPlugin 為 active；TokenGuardPlugin **退出 nightly** 改週 baseline 抽測
- W2：GoalSynthesisPlugin 鎖定或退出（依結果）→ OrchestrationCoordinator 為 active
- 違反此規則觸發紅線 ❌19 → `git revert HEAD`

### §2.1.1 TG fall-back 處理矩陣（**Arch-C3 修復**）

W1 啟動前若 TokenGuardPlugin 連續 7 次達 ≥ 70% 條件**未達**（< 60% baseline）：
- **二選一**（不可同時 TG SD_10 pilot active + W1 GS active，違紅線 ❌19 候補）：
  - **(a) W1 GS 延後進入**：等 TG 達標或正式退出 pilot 後再啟動 GS
  - **(b) TG 繼續 active**（不退出 nightly）：W1 GS 排程整體延 SD_10；不啟動新 active module
- SD_09.md §1.2「前置條件」改寫為「TG 鎖定 **或** 明確退出 pilot 二選一」

### §2.2 三階段排程

| 階段 | 時間 | TokenGuard | GoalSynthesis | Coordinator |
|------|------|------------|---------------|-------------|
| SD_08 W3~W6 | 觀察期 #1 | nightly active | — | — |
| SD_09 W1 | GS pilot | **週 baseline** | nightly active | — |
| SD_09 W2 | Coord pilot | 週 baseline | nightly active 或退出 | nightly active |
| SD_09 W3+ | 鎖定後 | 週 baseline | 週 baseline | 週 baseline |

### §2.3 GHA cron job 拆分

`.github/workflows/ci.yml` 拆分為 **3 個獨立 schedule cron job**（不同小時觸發，避免並行；**Arch-M2 修復：明訂 UTC 排程基準**）：
- `mutation-token-guard-weekly`：每週日 00:00 UTC（TG 鎖定後）
- `mutation-active-pilot-nightly`：每日 02:00 UTC（active pilot module，W1=GS / W2=Coord）
- `mutation-coordinator-pilot`：W2 啟用（單 active 規則）
- **Coordinator cron 排程**：每日 **04:00 UTC**（與 GS active 錯開 2 小時）
- 觀察期 #1 統計**以 UTC 日界為準**（SD_09.md §1.2 觀察期計數對齊）

### §2.4 單檔精準 mutation 路徑

OrchestrationCoordinator 使用單檔精準路徑（避免誤觸發其他 core 模組）：
- 預設：`--paths-to-mutate=autoclaude/core/orchestration/coordinator.py`（**非整目錄**）
- `--tests-dir=tests/core/orchestration`
- 預檢：`ls tests/core/orchestration/ && find autoclaude/core/orchestration -name '*.py'`

**多檔模式**（**SD-M1 修復**）：
- 若 W0 T2-B 預檢確認 `coordinator.py` + 子模組緊耦合（同包多檔互相依賴）
- 改用顯式列舉：`--paths-to-mutate=autoclaude/core/orchestration/coordinator.py,autoclaude/core/orchestration/<sub>.py`
- 預檢命令：`find autoclaude/core/orchestration -name '*.py' | head -5` → 若 > 1 個檔案，評估是否列入
- 不可使用 wildcard `--paths-to-mutate=autoclaude/core/orchestration/`（會觸發整目錄）

### §2.5 分模組差異化目標（繼承 ADR-SD08-002）

| Plugin | 目標 | 鎖定條件 |
|--------|------|---------|
| TokenGuardPlugin | ≥ 75%（鎖定 -5% = 70%）| 連續 7 次達標（觀察期 #1）|
| GoalSynthesisPlugin | ≥ 70%（鎖定 -5% = 65%）| 連續 7 次達標（W1 兩週 pilot）|
| OrchestrationCoordinator | ≥ 65%（鎖定 -5% = 60%）| 連續 7 次達標（W2 兩週 pilot）|

---

### §2.6 nightly 失敗 / timeout 處理（**QA-M5 修復**）

nightly job 失敗 / timeout（wall time > 45 min）：
- GitHub Actions `workflow_run` event 觸發 alert
- 寫入 `.mutation_failure.log`（含 module / timestamp / exit_code / wall_time）
- `mutation_baseline_lock.py` 補「**連續 3 次缺記錄即重置觀察期**」判定（缺記錄 = 失敗 / 超時 / 未跑）— **落地時機：W1 T1-B5 新增子任務 T1-B5a「擴充 mutation_baseline_lock.py 缺記錄判定 + 單元測試 ≥ 3 case」**（2026-05-21 W0 校正 — 原描述「補」字易誤解為已完成；實際 `tools/mutation_baseline_lock.py` 2026-05-21 grep 確認無 `consecutive_missing` / `reset_window` 邏輯，W0 待補入 T1 task list）
- R-SD09-B-2 緩解措施：W1 中段抽檢 nightly wall time > 30 min → **立即拆分 `-p no:xdist --paths-to-mutate=<sub-module>`**（不等到 W1 末才處理）

### §2.7 Windows 開發者本地 fall-back（2026-05-19 新增 / 2026-05-19 修訂為 Docker 解，R-SD09-CI-1 對應）

**情境**：個人開發場景下 GitHub Actions 額度受限 → 改用本地 nightly 排程（`tools/run_local_nightly.ps1`）。

**Windows 原生限制與解決**：
- `mutmut 3.x` 因 [issue #397](https://github.com/boxed/mutmut/issues/397) 不支援 Windows 原生
- **解決**：本地 nightly 腳本 Stage 1 透過 `docker run python:3.11-slim` 在 Linux container 內跑 mutmut；本地 Python 跑 `baseline_lock` + `analysis`（不需 mutmut）
- pip 依賴掛載 `${USERPROFILE}\.cache\pip` → `/root/.cache/pip` 避免每次重抓
- → **觀察期 #1 維持原始定義**：每日累積，連續 7 次 ≥ 70% 鎖定 baseline

**對應實作**：[tools/run_local_nightly.ps1 Stage 1](../../../tools/run_local_nightly.ps1)（Docker / Linux mutmut stage）

**fall-back**：若本機 Docker Desktop 異常或 pip cache 損毀導致連續 3 天 mutation 未產出 log → 同 §2.6 「連續 3 次缺記錄即重置觀察期」判定。

**觀察期 #2 / #3 採集環境**：本地 PowerShell 腳本 Stage 2 / drift_log-scan 採集，與 mutation 解耦。

---

## §3. fall-back（R-SD09-B-1）

若某模組首測 < 60% baseline：
- W1/W2 末僅產 Report 含 backlog；不阻塞下一 Wave
- 該模組延 SD_10 接續 pilot
- continue-on-error=true 維持

---

## §4. 對應參考

- [SD_Improving_09.md](../SD_Improving_09.md) §1.2 議題 B
- [SD09_Execution_Guide.md](../../05_development/SD09_Execution_Guide.md) W1/W2
- [ADR-SD08-002](ADR-SD08-002-mutation-baseline.md) v1.0

---

**簽核**：✅ ACCEPTED — 2026-05-21（SD_09 W0 T0-7 PM 形式核准；場景 A 個人開發 dev 自核 commit）
