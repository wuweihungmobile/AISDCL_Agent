# SD_09 W0 DoD — 觀察期正式操作手冊

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0** |
| 建立日期 | 2026-05-19 |
| 最後更新 | **2026-05-20**（W0 task list 22/22 CLOSED；五方終審 APPROVED；升正式版） |
| 對應 | [SD_Improving_09.md v1.0](../04_planning/SD_Improving_09.md) §8 + [ADR-SD09-001](../04_planning/ADR/ADR-SD09-001-pg-production-cutover.md) §2.2 + [risk_log.md §15](risk_log.md) |
| Git 狀態 | tag **v2026.05.20-02** → main（commit 4cf3fd4） |

---

## §1. W0 完成狀態（全部 CLOSED — 2026-05-20）

> W0 task list 22/22 項目全部關閉，五方（PM / Architect / SA / SD / QA）終審 APPROVED。
> 以下為歷史紀錄，**不再有待辦**。

| 項目 | 狀態 | 說明 |
|------|------|------|
| ADR-SD09-001~006 全部 ACCEPTED | ✅ CLOSED | 六份 ADR 全數形式核准 2026-05-20 |
| SD_Improving_09.md 升 v1.0 | ✅ CLOSED | §7 13 bullet 全填實 + §9 版本列 |
| ADR-SD09-004 路徑 (a)/(c) 刪除 | ✅ CLOSED | 路徑 (b) W3C TraceContext 唯一保留 |
| .env.example 新增兩個 SD_09 env var | ✅ CLOSED | PG_PRODUCTION_CUTOVER_GUARD + AUTOCLAUDE_TRACE_ID_SUBPROCESS_PROPAGATION |
| SD08_AC_Matrix AC4-1/AC4-2 升語意 | ✅ CLOSED | 改為實際量測門檻語意 |
| sprint_history.md §1.5 SD_07 骨架 | ✅ CLOSED | §1.5.1~§1.5.7 W0~W6 填入 |
| tools/run_local_nightly.ps1 | ✅ 已建立 | mutation Docker 化 + pg-e2e + perf + drift |
| gate_audit.md §1-septies SD09-G0 | ✅ CLOSED | 22/22 CLOSED + 五方 APPROVED |
| git tag v2026.05.20-02 + merge main | ✅ CLOSED | annotated tag 已推送 |

---

## §2. 現在的狀態：三條觀察期同步進行中

觀察期於 2026-05-20 正式啟動，**被動自動採集**，不需人工干預每次採集。
每天凌晨 02:00 由 Windows 排程器自動執行 `tools/run_local_nightly.ps1`。

```
今天 2026-05-20
│
├─ 觀察期 #1 ─ mutation TG 連續 ≥ 7 次達 70%  ───────────► 預計達標 2026-06-01
├─ 觀察期 #2 ─ AC4 pgvector 14 天全綠             ──────────► 預計達標 2026-06-02
└─ 觀察期 #3 ─ drift_log 30 天零 severity≠info    ──────────► 預計達標 2026-06-17
```

---

## §3. 核心執行檔案一覽

| 檔案 | 用途 | 執行時機 |
|------|------|---------|
| [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1) | **主入口**：一次跑三條觀察期採集 | 每日 02:00 自動 / 手動驗證 |
| [tools/ac4_progress_check.py](../../tools/ac4_progress_check.py) | 觀察期 #2 進度查詢（14 天 AC4） | 每日早上人工抽查 |
| [tools/observability_ga_check.py](../../tools/observability_ga_check.py) | 觀察期 #3 進度查詢（30 天 drift） | 每日早上人工抽查 |
| [tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py) | 觀察期 #1 mutation TG 記錄鎖定 | 由 nightly 腳本自動呼叫 |
| [tools/mutation_analysis.py](../../tools/mutation_analysis.py) | mutation backlog 分析報告 | 由 nightly 腳本自動呼叫 |
| [tools/ac4_nightly_collector.py](../../tools/ac4_nightly_collector.py) | 將 pytest JUnit XML 轉為 JSONL | 由 nightly 腳本自動呼叫 |

### 採集輸出檔（累積型，請勿刪除）

| 檔案 | 對應觀察期 | 說明 |
|------|-----------|------|
| `.mutation_history.jsonl` | #1 | mutation TG 每日紀錄 |
| `.mutation_baseline.toml` | #1 | mutation baseline 鎖定值 |
| `mutation_backlog_token_guard.md` | #1 | mutation backlog 報告 |
| `.ac4_history.jsonl` | #2 | AC4 每日 recall/p95 紀錄 |
| `.observability_history.jsonl` | #3 | 可觀測性 + drift 每日紀錄 |
| `logs/nightly_YYYY-MM-DD.log` | 全部 | 每日執行詳細日誌 |

---

## §4. 環境設定（首次執行必做）

### 4.1 前置條件

| 項目 | 要求 | 檢查指令 |
|------|------|---------|
| Docker Desktop | 已安裝且開機常駐 | `docker info` |
| Python 3.11+ | 已安裝且在 PATH | `python --version` |
| repo dev 依賴 | 已安裝 | `python -m pytest --version` |
| Docker pgvector image | 已 pull 或首次啟動會自動 pull | `docker images pgvector/pgvector` |

### 4.2 Windows 排程器設定（一次性）

```powershell
# 建立每日 02:00 排程
schtasks /create /SC DAILY /ST 02:00 /TN "AutoClaude_Nightly" `
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"d:\CursorProject\AutoClaude\tools\run_local_nightly.ps1`"" `
  /F

# 確認建立成功
schtasks /query /TN "AutoClaude_Nightly" /FO LIST
```

**重要**：排程器 GUI → 找到 `AutoClaude_Nightly` → 條件分頁 → 勾選「喚醒電腦執行此工作」（否則電腦休眠時排程不會觸發）。

### 4.3 首次手動驗證

```powershell
# 從 repo 根目錄執行（耗時約 20~35 分鐘）
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\run_local_nightly.ps1
```

執行完成後，確認最後一行 log（**SD_09 W0 P1-AUDIT-35 修復：補 `obs=` 欄位 + mutation 三態說明**）：
```
[INFO] END nightly summary: mutation=<rc> pg-e2e=0 perf=0 drift=0 obs=0
```

各欄位語意（對齊 CLAUDE.md §Nightly / CI 取證紀律 #1「stage rc 必須區分『真實失敗』vs『工具標準回報』」）：

| 欄位 | 0 = 成功 | 非 0 = 容忍 | 非 0 = 真實失敗 |
|------|---------|------------|----------------|
| `mutation` | mutmut 跑完 + validate 通過 | `SKIP`（Docker 未啟動）| `2`（validate 拒絕假 pass — 載具故障，依 P0-AUDIT-31 修 `.gitattributes` + `.sh` LF）|
| `pg-e2e`   | AC4 collector 寫入成功 | — | ≠ 0 必修（PG 連線 / migration 失敗）|
| `perf`     | regression_check 全綠或 observing | — | ≠ 0 為 BLOCK 真實退化 |
| `drift`    | drift_log severity!='info' = 0 | — | ≠ 0 為紅線 ❌（觀察期 #3 違反）|
| `obs`      | observability_snapshot 寫入成功 | — | ≠ 0 必修（IObservabilityPort 失能）|

---

## §5. 每日維護 SOP（約 1~3 分鐘）

### 5.1 早上健康檢查指令（三條觀察期一次看完）

```powershell
# --- 觀察期 #2 AC4 進度 ---
python tools/ac4_progress_check.py --history .ac4_history.jsonl

# --- 觀察期 #3 可觀測性 GA 進度 ---
python tools/observability_ga_check.py --history .observability_history.jsonl

# --- 觀察期 #1 mutation TG 最近 3 筆 ---
Get-Content .mutation_history.jsonl -ErrorAction SilentlyContinue | Select-Object -Last 3

# --- 昨天 nightly log 摘要 ---
$yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
Select-String "END nightly summary|WARN|ERROR" "logs\nightly_$yesterday.log" -ErrorAction SilentlyContinue
```

### 5.2 輸出解讀

**AC4 進度（ac4_progress_check.py）**

```
[AC4 progress] status=observing    ← 正常（還在累積）
  observation_days=3/14            ← 已累積 3 天
  green_streak=3                   ← 連續全綠 3 天（好）
  consecutive_failures=0           ← 無連續失敗（好）
  recall_sigma=None                ← 資料不足，尚未計算
  ready_for_labeled_pr=False       ← 尚未達 14 天
```

`status=ready` + `ready_for_labeled_pr=True` = 觀察期 #2 達標。

**異常狀態速查**

| status | 含義 | 處置 |
|--------|------|------|
| `observing` | 正常累積中 | 每天確認 green_streak 遞增 |
| `alert_yellow` | 連續 3 次未達綠線 | 查 `.ac4_history.jsonl` 最後幾筆，看 recall_at_10 / p95_ms |
| `alert_red` | 連續 5 次失敗 | 停計數，查 `logs/nightly_*.log` 詳細錯誤修復 |
| `no_history` | 採集未開始 | 確認排程器是否啟動，手動跑一次 nightly |

**可觀測性 GA 進度（observability_ga_check.py）**

```
[FAIL] green_streak=5 < window=30 (total 5 records)   ← 正常（累積中）
[PASS] green_streak=30 >= window=30 (total 31 records) ← 達標
```

---

## §6. 達標後行動清單

### 觀察期 #1 達標（mutation TG 連續 7 次 ≥ 70%，預計 2026-06-01）

- [ ] 記錄達標日期至 [gate_audit.md §1-septies](gate_audit.md) SD09-G0 列
- [ ] 啟動 W1 P2-2：GoalSynthesis mutation pilot（ADR-SD09-002 §2.3）
- [ ] 更新 risk_log.md §15 R-SD09-CI-1 → CLOSED

### 觀察期 #2 達標（AC4 14 天全綠，預計 2026-06-02）

- [ ] 執行確認指令：`python tools/ac4_progress_check.py --history .ac4_history.jsonl --json`
- [ ] 確認輸出 `"ready_for_labeled_pr": true`
- [ ] 建立 `needs-pg-e2e` labeled PR 觸發完整 e2e（`.github/workflows/ci.yml` on-label trigger）
- [ ] 更新 SD08_AC_Matrix.md AC4-2 行 → 實測達標日期 + 數值

### 觀察期 #3 達標（drift_log 30 天清零，預計 2026-06-17）

- [ ] 執行確認指令：`python tools/observability_ga_check.py --history .observability_history.jsonl`
- [ ] 確認輸出 `[PASS] green_streak=30 >= window=30`
- [ ] 連同 #1 mutation 取證結果，一起作為 **W5 db_only 切換雙條件**（ADR-SD09-001 §2.2）
- [ ] 人類 PM 親簽 release approval（Production 上線紅線）
- [ ] 人類 DBA 在 staging (≥1M 列) 重跑 alembic migration

---

## §7. 平行進行：W1 開發工作

三條觀察期是「被動等待」，W1 開發可立即平行啟動：

| W1 任務 | 參考 | 優先順序 |
|--------|------|---------|
| T1-1 GoalSynthesis Port + IGoalSynthesisPort | [SD09_Execution_Guide.md §3 W1](SD09_Execution_Guide.md) | P1 |
| T1-2 OrchestrationCoordinator MAX_ACTIVE_RUNS guard | 同上 | P1 |
| T1-3 enqueue 佇列 （MAX_ACTIVE_RUNS_PER_GOAL=5） | 同上 | P2 |
| QA-1 遺留：ac4_progress_check.py 補三鍵 export | W1 補登 | P2 |

QA-1 遺留說明：`tools/ac4_progress_check.py` 目前 JSONL schema 不匯出 `p95_latency_ms` / `cb_open_count` / `recall_p10` 三個 key（AC4-2 門檻項目），需在 W1 內由 `ac4_nightly_collector.py` 補寫入。

---

## §8. 風險與 fall-back

| 風險 ID | 情境 | fall-back |
|--------|------|----------|
| R-SD09-CI-1 | 本地排程連續 3 天未跑（電腦關機 / Docker crash） | 觀察期延長至下次連續 14/30 天綠；手動補跑補資料 |
| R-SD09-A-6 | alembic multi-head | 已解：0015_merge_sd06_optional_gin offline marker 就位 |
| mutation #1 < 60% | kill_rate 不足 | 議題 B（mutation 擴展）延 SD_10；不阻塞其他觀察期 |
| drift_log 非零事件 | 30 天計數歸零 | 查 config_audit_log 寫入路徑；修復後重新起算 |
| AC4 alert_red | 連續 5 天失敗 | 停計數，修復 pgvector recall/p95 問題後重啟採集 |

---

## §9. 快速指令速查表

```powershell
# === 每日健康檢查（複製貼上整段執行）===
python tools/ac4_progress_check.py --history .ac4_history.jsonl
python tools/observability_ga_check.py --history .observability_history.jsonl
Get-Content .mutation_history.jsonl -ErrorAction SilentlyContinue | Select-Object -Last 3

# === 手動觸發 nightly（Docker 必須先啟動）===
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\run_local_nightly.ps1

# === 觀察期 #2 期末確認 ===
python tools/ac4_progress_check.py --history .ac4_history.jsonl --json

# === 觀察期 #3 期末確認 ===
python tools/observability_ga_check.py --history .observability_history.jsonl --json

# === 排程器狀態查詢 ===
schtasks /query /TN "AutoClaude_Nightly" /FO LIST

# === 查看最近 nightly log ===
$today = (Get-Date).ToString("yyyy-MM-dd")
Get-Content "logs\nightly_$today.log" -ErrorAction SilentlyContinue | Select-Object -Last 20
```

---

## §10. 版本歷史

| 版本 | 日期 | 更新說明 |
|------|------|---------|
| v0.1 | 2026-05-19 | 初版（W0 啟動前置 DoD，含 §2.4 待辦清單） |
| **v1.0** | **2026-05-20** | **W0 22/22 CLOSED；五方終審 APPROVED；改寫為觀察期正式操作手冊；新增 §5 每日 SOP / §6 達標行動 / §7 W1 平行 / §8 風險 / §9 速查表；mutation 改 Docker 策略（不再需要 WSL2）** |

---

**對應參考**：
- [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1)（主要執行入口）
- [SD09_Execution_Guide.md §3](SD09_Execution_Guide.md)（W1~W6 詳細任務）
- [ADR-SD09-001 §2.2](../04_planning/ADR/ADR-SD09-001-pg-production-cutover.md)（W5 db_only 雙條件）
- [SD_Improving_09.md §8.1](../04_planning/SD_Improving_09.md)（三條觀察期說明）
- [gate_audit.md §1-septies](gate_audit.md)（SD09-G0~G6 簽核記錄）
- [risk_log.md §15](risk_log.md)（R-SD09-CI-1 等風險項）
