# SDD_improving_Automation_07 執行建議書（EXE）

**對應計畫**: `SDD_improving_Automation_07.md`（Phase G Final — M3+M4+M6）
**執行範圍**: 完整重新驗證一輪 + CF-5/CF-6 自然累積等待 + L5 收尾
**規劃日期**: 2026-04-28
**規劃者**: Chief AI Automation Architect (Claude Opus 4.7)
**前提**: `phase-g-final` tag 已存在（fc68851）；M3/M4/M6 程式碼已落地；CLAUDE.md §9.16/§9.17/§9.19/§9.Y 已落字

---

## 1. 執行決策（互動確認結果）

| 決策項 | 選擇 | 影響 |
|--------|------|------|
| 執行範圍 | **完整重新驗證一輪** | 跑全套 pytest / chaos / TLC，確認無 regression |
| CF-5/CF-6 處理 | **等待自然累積至 2026-05-04** | 不偽造樣本；cron + 實際 dispatch 自然觸發 |
| L5 對外宣告形式 | **INIT.md footer 版本字串升級** | 已確認到位，不另發 release notes |
| EXE.md 內容 | **完工度核實表** | 本文件主體 |

---

## 2. 完工度核實表（規劃 vs 實際）

### 2.1 M3 — Spec Ambiguity Quantifier（10 atomic）

| Task ID | 描述 | 狀態 | 證據檔 |
|---------|------|------|--------|
| D-37.1 | 6 維度評分公式定義 | [x] | `docs_template/sdd/requirements/AMBIGUITY-SCORER-SPEC.md` |
| D-37.1.b | SCORER_VERSION = "v1.0" | [x] | 上述 spec 已凍結 |
| D-37.2 | AmbiguityScorer 實作 | [x] | `tools/fsm_runtime/ambiguity_scorer.py`（10207 bytes）|
| D-37.3 | 50 fixture corpus | [x] | `tools/fsm_runtime/tests/fixtures/ambiguity_corpus/` |
| D-37.4 | 測試（準確率 ≥ 80%）| [x] | `test_ambiguity_scorer.py`（31 tests）|
| D-38.1 | SCG-0 整合 ambiguity gate | [x] | `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` step 2a-bis |
| D-38.2 | AMBIGUITY-WAIVER 模板 | [x] | `docs_template/sdd/requirements/AMBIGUITY-WAIVER-TEMPLATE.md` |
| D-38.3 | CLAUDE.md §9.16 落字 | [x] | CLAUDE.md §9.16（4 子規則 + 禁止行為）|
| D-38.4 | INIT.md M3 元件對照 | [x] | INIT.md §Phase G M3 |

### 2.2 M4 — Continuous Drift Monitor（12 atomic）

| Task ID | 描述 | 狀態 | 證據檔 |
|---------|------|------|--------|
| D-39.1 | drift_score 公式凍結 | [x] | `cicd/SDD_DRIFT_MONITOR.md` |
| D-39.2 | PostCommit hook 實作 | [x] | `.claude/hooks/post_commit_drift.py` |
| D-39.3 | install 腳本 | [x] | `tools/install_hooks/install_post_commit.sh` / `.ps1` |
| D-40.1 | drift_monitor.py 實作 | [x] | `tools/fsm_runtime/drift_monitor.py`（12315 bytes）|
| D-40.2 | DRIFT_OBSERVATION 狀態 + TLA+ 同步 | [x] | `transition_rules.py` + `formal/SDD_FSM.tla` ObservationStates |
| D-40.2.b | TLC 重跑 27/27 | [x] | `build/reports/formal/TLC-COVERAGE-2026-04-27.md` |
| D-40.3 | DAILY drift cron job | [x] | `.github/workflows/drift-daily.yml`（02:30 UTC）|
| D-40.4.a | PostCommit < 2s 測試 | [x] | `test_post_commit_drift.py` |
| D-40.4.b | drift_monitor 測試 | [x] | `test_drift_monitor.py`（16 tests）|
| D-40.5 | CLAUDE.md §9.17 落字 | [x] | CLAUDE.md §9.17（4 子規則）|
| D-40.6 | INIT.md M4 元件對照 | [x] | INIT.md §Phase G M4 |

### 2.3 M6 — Cost-Aware Orchestration（10 atomic）

| Task ID | 描述 | 狀態 | 證據檔 |
|---------|------|------|--------|
| D-43.1 | 估算模型凍結 | [x] | `docs_template/sdd/architecture/PATH-COST-MODEL-SPEC.md` |
| D-43.2 | path_cost.py 實作 | [x] | `tools/fsm_runtime/path_cost.py`（12159 bytes）|
| D-43.3 | 冷啟動 default 8000 | [x] | `EstimatedCost(value=8000, source="cold_start")` |
| D-44.1 | Orchestrator step_3_5 整合 | [x] | `agent/specialized/sdd-orchestrator-zh.yaml` |
| D-44.2 | REJECTED log 結構 | [x] | `build/reports/orchestrator/REJECTED-{date}.yaml` |
| D-44.3 | 連續 3 拒絕 → ESCALATION | [x] | `record_dispatch_rejection()` + DiagnosticAgent retry_exhausted |
| D-44.4.a | path_cost 測試 | [x] | `test_path_cost.py`（含 milestone hook 3 tests）|
| D-44.4.b | budget gate 整合測試 | [x] | `test_orchestrator_budget_gate.py` |
| D-44.5 | CLAUDE.md §9.19 落字 | [x] | CLAUDE.md §9.19（4 子規則 + Rule 9.19.5 milestone）|
| D-44.6 | INIT.md M6 元件對照 | [x] | INIT.md §Phase G M6 |

### 2.4 Cross-Cutting Final（CF-1~9）

| CF | 描述 | 原始狀態 | 重驗結果 |
|----|------|----------|---------|
| CF-1 | pytest 全套 | [x] 401 passed | 待重驗 |
| CF-2 | chaos 100 輪 | [x] bounded_ratio=1.0, avg=2074 | 待重驗 |
| CF-3 | TLC 27/27 | [x] | 待重驗 |
| CF-4 | QA Phase G Final 稽核 | [x] | 已完成（一次性，不重做）|
| CF-5 | 7 天 DAILY drift | [~] 已產出首份 + cron 配置 | **等到 2026-05-04 自然累積驗收** |
| CF-6 | rolling-30 校準 | [~] milestone hook + 單元測試 PASS | **等實際 dispatch 自然累積** |
| CF-7 | INIT/CLAUDE Phase G Final 總覽 | [x] §9.Y 已落字 | 一致性檢查 |
| CF-8 | 框架版本聲明 L5 | [x] INIT.md footer 已宣告 | 已確認 |
| CF-9 | PR + tag phase-g-final | [x] fc68851 | 已存在 |

---

## 3. 完整重新驗證一輪（執行步驟）

> 目標：確認 phase-g-final tag 後無 regression，所有驗收憑證仍成立。

### 3.1 步驟清單

- [ ] **V-1** 跑 `pytest tools/fsm_runtime/tests/ -v --tb=short`
  - 預期：≥ 401 passed（M3 +31 / M4 +16 / M6 +14 / 其他）
  - 失敗即 STOP，回報失敗測試 ID
- [ ] **V-2** 跑 `python -m tools.fsm_runtime.chaos_runner --rounds 100`
  - 預期：bounded_ratio == 1.0、avg tokens < 25000（baseline 2100×0.8 = 1680 為下階段門檻，本次仍以 25K 為硬上限）
  - 失敗即 STOP，分析故障注入路徑
- [ ] **V-3** 跑 `tools/fsm_runtime/formal/run_tlc.sh`（或 Windows `.ps1`）
  - 預期：reachable coverage 27/27 = 100%、4 invariant 全 PASS
  - 失敗即 STOP，比對 `_HAPPY_PATH` ↔ `SDD_FSM.tla` 雙源一致性
- [ ] **V-4** 跑 `pytest tools/fsm_runtime/tests/test_md_python_sync.py`（Rule 9.7.1 雙源）
  - 預期：MD 轉換表與 `_HAPPY_PATH` 一致
- [ ] **V-5** Rule 9.16/9.17/9.19/9.Y 落字一致性掃描
  - `grep -c "§9.16\|§9.17\|§9.19\|§9.Y" CLAUDE.md` 應 ≥ 各一處
  - INIT.md `Phase G Final` 區塊存在
- [ ] **V-6** 產出重驗報告 `build/reports/phase/PHASE-G-FINAL-REVERIFY-2026-04-28.md`
  - 格式：V-1~V-5 結果 + 異常項處理建議

### 3.2 失敗時行動

| 失敗項 | 行動 |
|-------|------|
| V-1 pytest 失敗 | 不可進 V-2；先修 regression 後重跑 |
| V-2 chaos 失敗 | 檢查是否新加 state 未對應 TERMINAL_STATES（Rule 9.9.4 違反）|
| V-3 TLC 失敗 | 檢查 `_HAPPY_PATH` 與 `.tla` 同步（Rule 9.18.1）|
| V-4 MD 同步失敗 | 同步 `SDD_FSM_ENGINE.md` 狀態表（Rule 9.7.1）|

---

## 4. 等待事項（CF-5 / CF-6）

### 4.1 CF-5 — 7 天 DAILY drift report 累積

- **觸發機制**: `.github/workflows/drift-daily.yml`（02:30 UTC daily）
- **驗收日**: **2026-05-04**（首份 2026-04-27 + 7 天）
- **驗收方式**: 列出 `build/reports/drift/DAILY-2026-04-27.md` ~ `DAILY-2026-05-03.md` 共 7 份存在
- **本期動作**: 無（cron 自然累積）；2026-05-04 由排程驗收

### 4.2 CF-6 — PathCostEstimator rolling-30 校準

- **觸發機制**: `path_cost.record_sample()` 首次達 30 樣本即一次性產出 `build/reports/orchestrator/CALIBRATION-MILESTONE-{subagent}-{classification}-{date}.yaml`
- **驗收方式**: milestone YAML 檔產出 + Rule 9.19.4 連續 5 次 > 50% 偏差警告機制可觸發
- **本期動作**: 無；由實際 dispatch 自然累積；不可注入合成樣本（Rule 9.19 禁止偽造）

---

## 5. 收尾動作（V-6 通過後執行）

> 條件：完整重新驗證一輪（§3）全部 PASS。

- [ ] **F-1** 確認 INIT.md footer 版本字串為 `AISDLC-SDD v0.01 — Phase G L5 Self-Driving SDD`（已確認到位）
- [ ] **F-2** 將 `SDD_improving_Automation_07.md` 從 `build/planning/active/` 移至 `build/planning/archive/`
- [ ] **F-3** 同步移動 `SDD_improving_Automation_07_EXE.md` 至 archive/（與計畫主檔同進退）
- [ ] **F-4** 提交 commit：`docs(planning): archive Automation_07 after phase-g-final reverification`
- [ ] **F-5** 推送至 `origin/main`（非破壞性，無需 force push）

> CF-5 / CF-6 由排程在 2026-05-04 獨立驗收，不阻擋 §5 收尾。

---

## 6. Token 預算規劃（Pro 限額）

| 階段 | 預估 Token | 說明 |
|------|-----------|------|
| §3 重新驗證 | ~8K | pytest 輸出截短、chaos 統計、TLC summary |
| §3.2 失敗處理 | 視情況 | 若 V-1~V-5 全 PASS 則 0；若失敗則需診斷 |
| §5 收尾 | ~2K | 移檔 + commit + push |
| EXE.md 寫入（本檔）| ~3K | 本次已消耗 |
| **總計** | **~13K** | 全綠路徑 |

> 不全綠路徑由 DiagnosticAgent + Rule 9.14/9.15 防護鏈控制，最大不超過 25K。

---

## 7. 風險與決策紀錄（NA 摘要）

| NA ID | 決議 | 影響 |
|-------|------|------|
| NA-1 | drift-daily.yml cron 配置（02:30 UTC + workflow_dispatch + auto commit）| CF-5 自然累積機制成立 |
| NA-2 | 2026-05-04 排程驗收 7 天 DAILY | CF-5 驗收節點凍結 |
| NA-3 | path_cost milestone hook（首次 30 樣本一次性產出）+ Rule 9.19.5 + 3 tests | CF-6 自動驗收機制成立 |
| NA-4 | 接受 phase-g-final token baseline 2100（DRIFT_OBSERVATION 預期成本），舊 1598 嚴格口徑作廢；下階段門檻 1680 | CF-2 chaos 接受標準明確化 |

---

## 8. 完成定義（DoD）

✅ §3 V-1~V-5 全 PASS + V-6 重驗報告產出
✅ §5 F-1~F-5 全完成
✅ CF-5 / CF-6 由 2026-05-04 排程獨立驗收（不阻擋本期歸檔）
✅ 框架等級維持 **L5 Self-Driving SDD**

---

**規劃版本**: v1.0
**規劃日期**: 2026-04-28
**前置 tag**: `phase-g-final` @ `fc68851`
**對應計畫**: `SDD_improving_Automation_07.md`
**重驗範圍**: pytest 401 / chaos 100 輪 / TLC 27/27 / Rule 落字一致性
**等待事項**: CF-5（2026-05-04）/ CF-6（自然累積）
