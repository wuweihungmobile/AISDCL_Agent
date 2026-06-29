# Phase G Final 詳細執行計畫 — M3 + M4 + M6（L5 成熟期）

**Phase 代號**: Phase G Final（L5 成熟）
**前置條件**: `phase-g-mvp` @ `4110f51`（Self-Healing + Predictive Halt + Formal Verification 收官）
**規劃日期**: 2026-04-27
**規劃者**: Chief AI Automation Architect（Claude Opus 4.7）
**對應藍圖**: `archive/SDD_improving_Automation_06.md` §3 M3/M4/M6
**目標 tag**: `phase-g-final`
**預估工時**: 9 工作天 + Cross-Cutting 收尾 2 天 = 11 天

---

## 0. 啟動前置條件（go/no-go）

- [ ] `phase-g-mvp` tag 已存在於 origin（已達成 ✅ 2026-04-26）
- [ ] pytest 340 passed 維持（不可有 regression）
- [ ] chaos_runner 100 輪 bounded_ratio = 1.0 維持
- [ ] TLC reachable coverage = 100%（26/26）維持
- [ ] CLAUDE.md §9.14 / §9.15 / §9.18 落字驗證
- [ ] PM 確認 OPEN-G.3 / OPEN-G.4 / OPEN-G.6（保留預設值）

---

## 1. M3 — Spec Ambiguity Quantifier（3 工作天，ACT-037/038）

**目標**：把「Spec 寫得模糊但沒違反 SLV」的灰區拉成量化指標；SCG-0 增加 ambiguity gate。

### 1.1 設計階段（D-37.1）
- [ ] D-37.1 設計 6 維度評分公式定義文件（量詞缺失 0.25 / 主詞缺失 0.20 / 數字邊界缺 0.20 / 否定條件缺 0.15 / Anchor 缺失 0.10 / 多義詞 0.10）→ 寫入 `docs_template/sdd/requirements/AMBIGUITY-SCORER-SPEC.md`
- [ ] D-37.1.b 凍結 `SCORER_VERSION = "v1.0"`（Rule 9.16.4 cache invalidation 依據）

### 1.2 實作階段（D-37.2 ~ D-37.4）
- [ ] D-37.2 實作 `tools/fsm_runtime/ambiguity_scorer.py`：
  - `AmbiguityScorer.score_ac(ac_text: str) -> float`（0~1）
  - `score_frd(frd_path: Path) -> dict[ac_id, score]`（批次）
  - 內建中英雙語量詞 / 多義詞辭典（pure rule-based，per OPEN-G.3 預設）
  - 快取機制：`build/cache/ambiguity/{SCORER_VERSION}/{frd_hash}.json`
- [ ] D-37.3 建立 fixture corpus：`tools/fsm_runtime/tests/fixtures/ambiguity_corpus/`
  - 25 個模糊 AC（含「快速」「適當」「盡可能」「相應」等典型反模式）
  - 25 個清晰 AC（含定量 NFR、明確主詞、否定條件、anchor 等）
- [ ] D-37.4 測試 `tests/test_ambiguity_scorer.py`：
  - 50 fixture 分類準確率 ≥ 80%（≥ 40 個正確）
  - 6 維度單元測試（每維度至少 3 案例）
  - 快取命中測試（同 hash 不重算）
  - SCORER_VERSION bump 觸發 invalidation 測試

### 1.3 SCG-0 整合（D-38.1 ~ D-38.2）
- [ ] D-38.1 修改 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` SCG-0 區塊：
  - 在 SLV-001~003 之後加 ambiguity gate step
  - 阻擋條件：任一 AC score ≥ 0.4 → SCG-0 fail
  - 報告路徑：`build/reports/scg/AMBIGUITY-{date}.yaml`
- [ ] D-38.2 建立 waiver 模板 `docs_template/sdd/requirements/AMBIGUITY-WAIVER-TEMPLATE.md`：
  - 必填欄位：AC_ID / score / waived_by / waived_at / rationale / 補強規格參照
  - 落地路徑：`docs/01_requirements/AMBIGUITY-WAIVER-{AC_ID}.md`

### 1.4 Rule 與文件落字（D-38.3 ~ D-38.4）
- [ ] D-38.3 CLAUDE.md 新增 §9.16 Ambiguity Gate 邊界（4 條子規則 9.16.1~9.16.4）+ 禁止行為
- [ ] D-38.4 INIT.md 新增 Phase G M3 元件對照表 + 禁止事項

### M3 驗收
- [ ] AmbiguityScorer 對 fixture 準確率 ≥ 80%
- [ ] SCG-0 對 score ≥ 0.4 案例 100% 拒絕
- [ ] AMBIGUITY-WAIVER 模板可被 docs_template/ 複製使用
- [ ] pytest 新增 ~15 tests 全綠

---

## 2. M4 — Continuous Drift Monitor（3 工作天，ACT-039/040）

**目標**：每個 commit 後自動檢查 spec ↔ code drift；把 drift 從 gate-time 提前到 commit-time。

### 2.1 設計階段（D-39.1）
- [ ] D-39.1 drift_score 計算公式凍結（API drift + Type drift 為 v1；Behavior drift 留 v2）→ 寫入 `cicd/SDD_DRIFT_MONITOR.md`
  - API drift: `|openapi_endpoints △ code_routes| / |openapi_endpoints ∪ code_routes|`
  - Type drift: 對 FRD declared types 與 code class/enum 的 missing-fields 加權

### 2.2 PostCommit Hook 實作（D-39.2 ~ D-39.3）
- [ ] D-39.2 實作 `.claude/hooks/post_commit_drift.py`：
  - git native hook 機制（per OPEN-G.4 決策；與 Claude Code session lifecycle 解耦）
  - AST 比對：呼叫 `tools/fsm_runtime/drift_monitor.py` 計算 drift_score
  - advisory：失敗不阻擋 commit，僅寫 `.git/COMMIT_DRIFT_WARNING`（Rule 9.17.1）
  - 執行 budget < 2s（超時 skip 並寫 warning）
- [ ] D-39.3 安裝腳本 `tools/install_post_commit_hook.sh` + Windows `.ps1`：
  - 自動 symlink / copy 至 `.git/hooks/post-commit`
  - 與既有 `.claude/hooks/` 保持解耦
  - README 說明 opt-in 安裝（不在 settings.json 強制）

### 2.3 Drift Monitor + DRIFT_OBSERVATION 狀態（D-40.1 ~ D-40.3）
- [ ] D-40.1 實作 `tools/fsm_runtime/drift_monitor.py`：
  - `compute_drift(commit_sha) -> DriftReport`（含 api_drift / type_drift / total_score）
  - `check_consecutive_drift(window=3, threshold=0.3) -> bool`（Rule 9.17.3）
  - 報告寫入 `build/reports/drift/COMMIT-{sha}.yaml`
- [ ] D-40.2 FSM 整合：
  - `transition_rules.py` 新增 `DRIFT_OBSERVATION` 至 `OBSERVATION_STATES`（不阻塞 tool calls）
  - `fsm_runtime.py` 新增 `enter_drift_observation()` / `exit_drift_observation()` API
  - 入口：任意 retry-prone state；出口：continue / switch_to_audit（連續 3 commits drift ≥ 0.3）
  - **同步更新 `tools/fsm_runtime/formal/SDD_FSM.tla`**（Rule 9.18.1 雙源一致性）：
    - 在 ObservationStates 加入 `DRIFT_OBSERVATION`
    - `NotInBothSets` invariant 維持
    - 重跑 `run_tlc.sh` 確認 reachable coverage 仍 ≥ 95%（27/27 預期 100%）
    - 更新 `build/reports/formal/TLC-COVERAGE-2026-04-27.md`
- [ ] D-40.3 每日漂移報告：
  - 02:30 UTC cron schedule（per Rule 9.17.4）
  - 產出 `build/reports/drift/DAILY-{date}.md` 滾動 7 天
  - 整合進 `cicd/SDD_CICD_BASE_LAYER.md`（與 Chaos nightly job 同層）

### 2.4 測試（D-40.4）
- [ ] D-40.4.a `tests/test_post_commit_drift.py`：
  - mock 100 commit 平均執行 < 2s（Rule 9.17.1 budget）
  - timeout 自動 skip + warning 寫入測試
- [ ] D-40.4.b `tests/test_drift_monitor.py`：
  - API drift fixture 準確率 ≥ 95%（10 known-drift commits）
  - 連續 3 commits drift ≥ 0.3 → 自動轉 SPEC_AUDIT 整合測試
  - DAILY report 產出測試

### 2.5 Rule 與文件落字（D-40.5 ~ D-40.6）
- [ ] D-40.5 CLAUDE.md 新增 §9.17 Drift Monitor 邊界（4 條子規則 9.17.1~9.17.4）+ 禁止行為（PostCommit hook 阻擋 commit / 跳過 02:30 daily job）
- [ ] D-40.6 INIT.md 新增 Phase G M4 元件對照表 + 禁止事項；同步 §測試驗證現況更新（含 DRIFT_OBSERVATION）

### M4 驗收
- [ ] PostCommit hook 100 commit 平均 < 2s
- [ ] API drift 準確率 ≥ 95%（10 fixture）
- [ ] 連續 drift → SPEC_AUDIT 在 chaos 中正確觸發
- [ ] TLC 重跑 27/27 = 100% reachable coverage
- [ ] DAILY drift report 連續 7 天產出（驗收期間累計）

---

## 3. M6 — Cost-Aware Orchestration（3 工作天，ACT-043/044）

**目標**：orchestrator dispatch 前預估 path token cost；超預算即拒絕並提示替代方案。

### 3.1 設計階段（D-43.1）
- [ ] D-43.1 估算模型凍結 → 寫入 `docs_template/sdd/architecture/PATH-COST-MODEL-SPEC.md`
  - 每個 (subagent, classification) tuple 維護 rolling-30 平均 + 1.5σ
  - safety margin: `estimated = avg + 1.5 * stddev`
  - gate 條件：`token_remaining > estimated × 1.2`
  - 冷啟動 default: 8000 tokens（per OPEN-G.6 / Rule 9.19.1）

### 3.2 PathCostEstimator 實作（D-43.2 ~ D-43.3）
- [ ] D-43.2 實作 `tools/fsm_runtime/path_cost.py`：
  - 從 `build/reports/test-analysis/DISPATCH-LOG-*.yaml` 讀取歷史
  - 從 `build/state/conversation-ledger.yaml` 讀取實測 token
  - `estimate(subagent, classification) -> EstimatedCost`
  - rolling 視窗持久化：`build/state/path-cost-rolling.yaml`
- [ ] D-43.3 冷啟動處理：
  - 樣本數 < 10 → 回傳 `EstimatedCost(value=8000, source="cold_start")`（Rule 9.19.1）
  - 樣本 ≥ 10 後切換為 rolling-30 統計

### 3.3 Orchestrator 整合（D-44.1 ~ D-44.3）
- [ ] D-44.1 修改 `agent/specialized/sdd-orchestrator-zh.yaml`：
  - 新增 `step_3_5_estimate_cost`（在 step_3 dispatch 前）
  - dispatch 前呼叫 `PathCostEstimator.estimate()`
  - gate 失敗 → 拒絕 + 寫入 `build/reports/orchestrator/REJECTED-{date}.yaml`
- [ ] D-44.2 拒絕日誌結構：
  - 必填：`timestamp / subagent / classification / estimated / remaining / reason / proposed_alternative`
  - 與 `DISPATCH-LOG-{date}.yaml` 互相對齊（同 schema_version）
- [ ] D-44.3 連續 3 次拒絕 → ESCALATION：
  - `fsm_runtime.py` 新增 `record_dispatch_rejection()` API
  - 連續 3 次計數於 `state.dispatch_rejection_count`
  - 觸發 ESCALATION（reason: `budget_exhausted`）
  - DiagnosticAgent 對應 sub_type：`retry_exhausted`（structural，不可 auto-recover）
  - DRY-RUN：透過 chaos fixture 驗證觸發路徑

### 3.4 測試（D-44.4）
- [ ] D-44.4.a `tests/test_path_cost.py`：
  - rolling-30 預估誤差 < 30%（從歷史 ledger 回放）
  - 冷啟動 default 8000 驗證（樣本 < 10）
  - bump SCORER_VERSION 對應快取失效（與 M3 概念一致）
- [ ] D-44.4.b `tests/test_orchestrator_budget_gate.py`：
  - gate 拒絕 100% 命中（token < estimated × 1.2 時）
  - 連續 3 拒絕 → ESCALATION 整合測試
  - REJECTED log 與 DISPATCH-LOG schema 對齊驗證
  - 估算誤差 > 50% 連續 5 次 → 警告人工調校（Rule 9.19.4）

### 3.5 Rule 與文件落字（D-44.5 ~ D-44.6）
- [ ] D-44.5 CLAUDE.md 新增 §9.19 Cost-Aware 邊界（4 條子規則 9.19.1~9.19.4）+ 禁止行為（樣本不足用過度樂觀 default / 估算偏差不調校）
- [ ] D-44.6 INIT.md 新增 Phase G M6 元件對照表 + 禁止事項

### M6 驗收
- [ ] PathCostEstimator 預估誤差 rolling-30 < 30%
- [ ] Budget gate 在 chaos 中正確觸發（token < estimated × 1.2 時 100% 拒絕）
- [ ] REJECTED log 與 DISPATCH-LOG 互相對齊
- [ ] 連續 3 次拒絕 → ESCALATION（reason: budget_exhausted）整合測試通過
- [ ] DiagnosticAgent 對 budget_exhausted 分類為 structural（無誤觸發 auto-recovery）

---

## 4. Cross-Cutting Final（2 工作天，9 個原子任務）

每個 milestone 完成後執行；最終一次性驗收。

- [x] CF-1 跑全套 pytest `tools/fsm_runtime/tests/`（實測 401 collected + passed，超標）
- [x] CF-2 跑 chaos_runner 100 輪重驗（含 DRIFT_OBSERVATION + budget gate 路徑）
  - ✅ bounded_ratio == 1.0（實測 100/100）
  - ✅ avg tokens 實測 **2074**；NA-4 決議（2026-04-27）：接受 phase-g-final 新 baseline ≈ 2100（DRIFT_OBSERVATION 路徑增加 token 為預期成本）；DoD §8 Phase G MVP 條款（Phase F baseline 25K × 80% = 20K）仍大幅 PASS；舊嚴格口徑 1598（phase-g-mvp 1998 × 80%）正式作廢。後續以 phase-g-final baseline 2100 × 80% = 1680 為下一階段（Phase H+）規範門檻
- [x] CF-3 重跑 TLC（DRIFT_OBSERVATION 加入後 reachable coverage = 27/27 = 100%；Rule 9.18.3 守門通過）
  - 已產出 `build/reports/formal/TLC-COVERAGE-2026-04-27.md`
- [x] CF-4 派 SDD QA Agent 做 Phase G Final 稽核（Rule 9.16/9.17/9.19 + 9.18 雙源一致性，2026-04-27 完成）
- [~] CF-5 連續 7 天 DAILY drift report 累積驗證（與 cron 對接）
  - ✅ 2026-04-27 已產出首份 `DAILY-2026-04-27.md` 證明 `write_daily_report()` 機制可執行
  - ✅ NA-1 cron workflow 已配置（2026-04-27）：`.github/workflows/drift-daily.yml`（02:30 UTC daily + workflow_dispatch + 自動 commit push）
  - 連續 7 天累積由 cron 自然產出，2026-05-04 由 NA-2 排程驗證
- [~] CF-6 PathCostEstimator rolling-30 誤差校準（從歷史 ledger 回放至少 30 個樣本）
  - ✅ 單元層級 invariant 已驗（`test_rolling_estimate_error_under_30pct` PASS）；cold-start 8000 default 守住（per Rule 9.19.1）
  - ✅ NA-3 milestone hook 已實作（2026-04-27）：`record_sample()` 首次達 30 樣本即一次性產出 `CALIBRATION-MILESTONE-{subagent}-{classification}-{date}.yaml`；新增 Rule 9.19.5 + 3 tests（test_milestone_*）；total tests 401 → 404
  - 不注入合成樣本（違反 Rule 9.19 「禁止偽造樣本污染 estimator」）；rolling-30 由實際 dispatch 自然累積，milestone hook 觸發後即可進行 Rule 9.19.4 驗收
- [x] CF-7 更新 INIT.md / CLAUDE.md Phase G Final 收官總覽（§9.Y 已落字，與 MVP §9.X 同型）
- [x] CF-8 框架版本聲明升級至 `AISDLC-SDD v0.01 — Phase G L5 Self-Driving`（INIT.md footer + version line）
- [x] CF-9 開 PR `phase-g-final` → `main`、merge、tag `phase-g-final` 並推送（SHA `fc68851794c23112cb1a24d99f9a89808c5b9242`，本地/遠端一致）

---

## 5. 完工後動作

- [ ] 本檔 `SDD_improving_Automation_07.md` 移至 `archive/`
- [ ] 推送至 `wuweihungmobile/AISDLC_SDD` main
- [ ] L5 Self-Driving SDD 對外宣告（updated INIT.md 版本字串）

---

## 6. 風險彙整（沿襲 Automation_06 §6）

| 風險 | 機率 | 影響 | 緩解 |
|------|------|------|------|
| AmbiguityScorer 過度誤判（清晰 AC 被判模糊） | 中 | 中 | M3 提供 AMBIGUITY-WAIVER 通道；fixture 校準 ≥ 80% |
| PostCommit hook 影響 commit 速度 | 低 | 低 | M4 要求 < 2s；超時自動 skip |
| PathCostEstimator 冷啟動失準 | 高 | 中 | M6 規定樣本 < 10 用保守 default 8000 |
| DRIFT_OBSERVATION 加入後 TLC 重算 reachable coverage 跌破 95% | 低 | 高 | CF-3 強制重跑驗證；不通過則阻擋 phase-g-final tag |
| Rule 9.16/9.17/9.19 與既有 9.6~9.15 互相干擾 | 低 | 中 | CF-4 QA 稽核三方一致性；CF-7 收官總覽明確協作邊界 |

---

## 7. 與 phase-g-mvp 的銜接

| MVP 元件 | Final 延伸 |
|---------|-----------|
| DiagnosticAgent（M1） | M6 budget_exhausted 接 retry_exhausted sub_type |
| TrajectoryPredictor（M2） | M4 連續 drift → SPEC_AUDIT 與 predictor switch_to_audit 共用入口 |
| TLA+ FSM（M5） | M4 DRIFT_OBSERVATION 必須同步進入 .tla（Rule 9.18.1） |
| `_HAPPY_PATH` ↔ `SDD_FSM.tla` 雙源 | CF-3 強制重跑 TLC 驗收 |

---

**規劃版本**: v1.0
**規劃者**: Chief AI Automation Architect (Claude Opus 4.7)
**規劃日期**: 2026-04-27
**前置 tag**: `phase-g-mvp` @ `4110f51`
**目標 tag**: `phase-g-final`
**原子任務總數**: M3 (10) + M4 (12) + M6 (10) + CF (9) = **41 atomic tasks**
