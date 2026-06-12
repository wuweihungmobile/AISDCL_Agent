# SD_09 W3 Round 2 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — 派 PM + Architect/SA/SD/QA 全能專家 zero-trust audit 並徹底修復 |
| Audit Round | W3 Round 2（2026-05-24 22:30） |
| Audit 發現 | 28 項（P0=7 / P1=10 / P2=11） |
| 真實修復 | 8 項（P0-2/3/5/6 + P1-1/2/7/8） |
| 推翻 | 3 項（P0-4 / P0-7 / P0-1 由 clean run 證實已 OK） |
| 列入 W1 backlog | 11 項（P2-1 ~ P2-11） |
| Commit / Tag | `686542f` / `v2026.05.24-03` |
| Merge main | `49ec3d1` |
| Nightly 取證 | `logs/nightly_2026-05-24_230843.log:L242` `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0` |

---

## 1. 主執行檔案

| 檔案 | 內容 |
|------|------|
| [docs/05_development/SD09_Execution_Guide.md](SD09_Execution_Guide.md) v1.0 | SD_09 W0~W6 詳細執行計畫 |
| [docs/04_planning/SD_Improving_09.md](../04_planning/SD_Improving_09.md) v1.2 | 主規劃（v1.2 含 W3 Round 2 audit 紀錄） |
| [docs/05_development/SD09_W0_Nightly_RootCause_Report.md](SD09_W0_Nightly_RootCause_Report.md) §4.7 | W3 Round 2 audit 完整修法 / 取證 |

---

## 2. 接下來 30 天執行大綱（觀察期累積 + W1 啟動準備）

| # | 時間窗 | 動作 | 依賴檔案 |
|---|--------|------|---------|
| 1 | **每日 02:00**（Windows Task Scheduler `AutoClaude_Nightly`） | 自動執行 `tools\run_local_nightly.ps1` 採集 3 觀察期 jsonl + perf + obs | [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1) |
| 2 | **2026-06-01**（觀察期 #1 完成日） | 驗證 `.mutation_history.jsonl` token_guard 連續 7 次 ≥ 70% **且** unique source_sha256 ≥ 7（P0-5 新規）→ 鎖定 `.mutation_baseline.toml` | [tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py) |
| 3 | **2026-06-02**（觀察期 #2 完成日） | `tools/ac4_progress_check.py --json` 回 `ready_for_labeled_pr=true`（目前 p95=51.7ms neutral 區；嚴格 50ms 仍差 1.7ms 累計中）；F2 告警就位：true 時 nightly WARN 提示 PM 拍板啟用 `pg-e2e-on-label.yml` | [tools/ac4_progress_check.py](../../tools/ac4_progress_check.py) |
| 4 | **2026-06-17**（觀察期 #3 完成日） | `.drift_log_history.jsonl` 連續 30 天 `severity_non_info_count=0`；可用 **新工具** `tools/drift_log_ga_check.py --window 30` 自動驗證（P0-3 新建） | [tools/drift_log_ga_check.py](../../tools/drift_log_ga_check.py) |
| 5 | **2026-06-18 ~ 2026-06-26**（G0 啟動窗口） | SD_09 W0 task list 22/22 已 CLOSED → 進入 W1 GoalSynthesisPlugin mutation pilot | [SD09_Execution_Guide.md §3 W1](SD09_Execution_Guide.md) |
| 6 | **每次新 session 前** | 依 §0.3 5 條檢查（pytest / lint-imports / loc_budget / wc CLAUDE.md / observability_ga_check） | [SD09_Execution_Guide.md §0.3](SD09_Execution_Guide.md) |

---

## 3. W1 啟動前 backlog 更新

### 3.1 W3 Round 2 真實修復（本次 commit 已 CLOSED）

| ID | 狀態 | 說明 |
|----|------|------|
| P0-2 Add-LogLineSafe | ✅ CLOSED 2026-05-24 | FileShare.ReadWrite + retry 5 次解 tail -F 衝突 |
| P0-3 drift_log_ga_check + snapshot prefer table_exists | ✅ CLOSED 2026-05-24 | 新建 166 LOC 工具 + 14 case test |
| P0-5 mutation source_sha256 | ✅ CLOSED 2026-05-24 | history 加 sha 欄位 + lock 要求 7 unique |
| P0-6 perf 三態 | ✅ CLOSED 2026-05-24 | rc 0/2/1 + summary 區分；nightly 實證 perf=2 |
| P1-1 emit_real strict | ✅ CLOSED 2026-05-24 | 最新 3 筆 strict + backfill script |
| P1-2 log mtime guard | ✅ CLOSED 2026-05-24 | `--require-log-mtime-within-seconds 3600` |
| P1-7 samples=20 邊界 | ✅ CLOSED 2026-05-24 | test_check_block_at_min_samples_exact |
| P1-8 emit 三段拆分 | ✅ CLOSED 2026-05-24 | 每段 try/except + partial success |

### 3.2 W1 P2 待處理（11 項；不阻塞 W1 G0 啟動）

| ID | 說明 |
|----|------|
| P2-1 | nightly 多輪同日 history 「最後贏」設計需文件化於 ADR-SD09-002 §2.3 |
| P2-2 | `tools\run_local_nightly.ps1` 加 `Set-StrictMode -Version Latest` |
| P2-3 | `Invoke-Stage` rc 字串 'SKIP' 與整數混雜 → summary 改 JSON 格式 |
| P2-4 | W1 補 audit `tools\hooks\enforce_docs_path.py` / `claude_md_freshness.py` 5 hook test 交叉驗證 |
| P2-5 | `mutation_analysis.py` warning 文字對人類解讀加強 |
| P2-6 | `perf_baseline_lock.py::reset_baseline` noop case 回傳值區分 |
| P2-7 | `observability_ga_check.py` `--window` 預設 30 補 docstring 提示 cutoff |
| P2-8 | `tests\tools\test_drift_log_snapshot.py` 補「pass 流程 + ga_check 閉環」測試 |
| P2-9 | 新建 `tools\nightly_consistency_check.py` 跨檔 mtime 對齊 assertion |
| P2-10 | `.claude\settings.json` Hook PostToolUse matcher 順序文件化 |
| P2-11 | SD_Improving_09.md v1.2 元數據加 caveat 說明 W3 Round 1 APPROVED 範圍 |

### 3.3 W2+ 既有 backlog（v1.1 列入，本次未動）

| ID | 狀態 | 說明 |
|----|------|------|
| P1-DOCKER-RC | 🟡 W1 待處理 | Docker-PG stage 內 sub-step rc 誠實化（docker run 失敗 / PG 60s 未就緒） |
| P1-JSONL-GIT | 🟡 W1 待處理 | history jsonl 遠端備份方案評估（CI artifact 35 天 vs sub-branch push） |
| P2-1/2/3 | 🟡 W2+ 待處理 | stage rc 型別統一封裝 / KB metric PG 持久化（議題 G 待 PM #5 拍板） |

---

## 4. 手動驗證指令（複現本次取證）

```powershell
# 1. 跑 nightly（耗時 6 分鐘）— 不可同時 tail -F 防 Add-Content 衝突（P0-2 修復後支援，但安全起見）
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\run_local_nightly.ps1

# 期望最末行：
# [YYYY-MM-DD HH:MM:SS][INFO] END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0
# perf=2 為 P0-6 修復生效（samples<20 時 WARN 黃色，不再給綠燈假象）

# 2. 全測（耗時 1.5 分鐘）— 期望 2,492 passed / 122 skipped / 0 failed
python -m pytest tests/ -p no:randomly -q --tb=no

# 3. importlinter — 期望 7 kept / 0 broken
PYTHONUTF8=1 lint-imports --config .importlinter

# 4. LOC 預算 — 期望 violations=0
python tools\check_loc_budget.py

# 5. CLAUDE.md ≤ 400 — 期望 391
wc -l CLAUDE.md

# 6. 三觀察期 GA 取證工具
python tools\drift_log_ga_check.py --window 30 --json
python tools\observability_ga_check.py --window 30 --json
python tools\ac4_progress_check.py --json
```

---

## 5. 風險登記（沿用 risk_log.md §15）

| 風險 | 狀態 |
|------|------|
| R-SD09-A-1 ~ A-6 | 持續觀察（觀察期 #1/#2/#3 累積中） |
| R-SD09-O-1 | 🟢 緩解 — `tools/observability_ga_check.py` + `_backfill_emit_real.py` 已就位 |
| R-SD09-CI-3 | 🟡 W1 處理 — Z1/Z2/Z3 待 PM 拍板 continue-on-error 移除 |
| **新增** R-SD09-NIGHTLY-1 | 🟡 觀察 — Windows file lock 在 PS 5.1 下需 Add-LogLineSafe retry；長遠考慮遷 pwsh 7+ |

---

**文檔元數據**：v1.0 | 2026-05-24 23:30 | SD_09 W3 Round 2 後續行動 | 對應 commit 686542f / tag v2026.05.24-03 / merge main 49ec3d1
