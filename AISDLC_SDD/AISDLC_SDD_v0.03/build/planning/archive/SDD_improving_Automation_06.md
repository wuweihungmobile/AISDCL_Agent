# Phase G — Level 5 自治升級藍圖（Self-Driving SDD）

**Phase 代號**: Phase G
**目標等級**: L4.9（精準有界停機）→ **L5 自治（Self-Driving / Self-Healing SDD）**
**前置條件**: Phase A~F 已完成（tag: `phase-f-final` @ commit `67d7e38`）
**規劃日期**: 2026-04-26
**規劃者**: Chief AI Automation Architect（Claude Opus 4.7）
**歸檔對象**: 完成後移至 `build/planning/archive/`

---

## 1. 動機與架構診斷

Phase F 完工後系統已具備 **L4.9 精準有界停機**：FSM bounded retry、Chaos 100 輪 100% 停機於 terminal、HMAC-signed Production Feedback、SLV Generator 半自動產出規則、Hub 跨實例共享、多模態驗證。

但 L5 真正自治的最後一哩仍有 **6 道結構性缺口**：

| # | 缺口 | 現況 | L5 需求 |
|---|------|------|--------|
| 1 | ESCALATION 是死局 | 100% 需人工介入 | 暫時性故障 bounded auto-recover；結構性故障才升人工 |
| 2 | Halt 是反應式 | 必須先用滿 retry budget（3 次）才轉 SPEC_AUDIT | 從 trajectory 預測「會崩」並提早切換策略 |
| 3 | Spec 歧義是二元 | SLV 只能 PASS/FAIL | 量化 ambiguity score；SCG-0 加 ambiguity gate |
| 4 | Spec↔Code drift 僅 gate-time 檢查 | SCG-4/5 才抓 | 每個 commit 持續監控；早期警告 |
| 5 | 「有界停機」是經驗性 | Chaos 100 輪 ≠ 對所有 reachable state bounded | TLA+/Alloy 形式化證明 |
| 6 | Token 預算是事後制裁 | Ledger 只記帳 | 派遣前 cost gate、預測性 compact |

**Karpathy-style 診斷**：
> *L5 不是「再多加一層 hook」就能達成。L5 是「系統能自己診斷自己的失敗、自己嘗試修復、修復不了才升人工」。我們現在的瓶頸是：每次 ESCALATION 都默認需要人工 — 這違反了「絕大多數失敗應該自動處理，僅 novel pattern 才升人工」的 L5 哲學。Phase G 的核心命題是：把 ESCALATION 從「停機指令」升級為「待診斷事件」。*

---

## 2. Self-Verification Protocol — 極端案例模擬

> **案例**：Spec 寫錯（AC-001 與 INV-002 互斥），導致測試永遠不會通過。

### 2.1 Phase F 現行流程（baseline）
```
1. dev attempt 1 → test fail (H1)
2. dev attempt 2 → test fail (H1, pattern_match=0.83 ≥ 0.75)
3. dev attempt 3 → test fail (H1)        ← 燒 3 次 token
4. PR_REVIEW retry_count=3 → SPEC_AUDIT
5. SLV 跑全套 → 偵測 AC-001 vs INV-002 矛盾
6. → ESCALATION → 人工
```
**Token 浪費**：3 次無效 dev 嘗試 ≈ 6~8K tokens。

### 2.2 Phase G 強化後流程
```
1. dev attempt 1 → test fail (H1)
2. dev attempt 2 → test fail (H1)
3. [M2 TrajectoryPredictor] decision_trace 顯示
   「IMPLEMENTATION → PR_REVIEW → 同 pattern × 2」
   且 ledger 顯示「retry_count 將在第 3 次到達上限」
   → predicted_action = "switch_to_audit"
   → 不等第 3 次直接 SPEC_AUDIT          ← 省 1 次 dev 嘗試
4. SLV → 偵測矛盾 → escalation_reason = "SPEC_LOGIC_CONFLICT"
5. [M1 DiagnosticAgent] 分類:
   {category: structural, sub_type: spec_conflict,
    auto_recoverable: false, confidence: 1.0,
    rationale: "AC vs INV 互斥屬規格層問題，不可自動修"}
6. → 直接 ESCALATION_FINAL（跳過 AUTO_RECOVERY_ATTEMPT）→ 人工
```
**Token 浪費**：2 次 dev 嘗試 ≈ 4~5K tokens（節省 ~35%）+ 不會誤觸發自動修復。

### 2.3 Halting 證明（M5 形式化）
TLA+ 證明所有從 IMPLEMENTATION 出發的 reachable state 集合 R 滿足：
```
∀ s ∈ R, ∃ n ≤ MAX_DEPTH : transition*(s, n) ∈ {RELEASE, ESCALATION_FINAL, TERMINATED}
```
即「Spec 寫錯」這條路徑在有限步數內必達 terminal — 而非依賴 Chaos 抽樣。

✅ 結論：bounded halting 保住，token 浪費下降，無誤自動修復風險。

---

## 3. Phase G Milestones 規劃（6 個）

### M1 — Self-Healing Layer（自我復原層） 🎯 L5 MVP

**目標**：讓暫時性 ESCALATION 自動復原一次；結構性 ESCALATION 直升人工。

| ACT | 交付物 | 路徑 |
|-----|-------|------|
| **ACT-032** | `DiagnosticAgent` — 6 種 ESCALATION 分類器 | `agent/specialized/sdd-diagnostic-zh.yaml` + `tools/fsm_runtime/diagnostic.py` |
| **ACT-033** | `AUTO_RECOVERY_ATTEMPT` 觀測狀態 + 1-shot bounded recovery | `tools/fsm_runtime/auto_recovery.py` |
| **ACT-034** | `ESCALATION_FINAL` 終局狀態（不可再復原） | `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` §G M1 |

**6 種 ESCALATION 分類**（Diagnostic decision tree）：
| Category | Sub-Type | auto_recoverable | 範例 | Recovery Action |
|----------|----------|------------------|------|-----------------|
| transient | ci_timeout | true | CI runner 暫時 502 | wait 30s + rerun |
| transient | network_flap | true | API call 超時 | rerun with backoff |
| transient | rate_limit | true | LFS upload 429 | wait per Retry-After header |
| structural | spec_conflict | **false** | AC vs INV 矛盾 | escalate human |
| structural | data_corruption | **false** | YAML schema 損毀 | escalate human |
| structural | retry_exhausted | **false** | retry budget 耗盡 + pattern stable | escalate human |

**Rule 9.14 — Self-Healing 邊界**（新增至 CLAUDE.md）：
- 9.14.1 AUTO_RECOVERY_ATTEMPT 全 session **最多 3 次**（不論 stage）
- 9.14.2 同一 ESCALATION reason 全 session **僅允許 1 次** auto-recovery
- 9.14.3 `category=structural` 的 ESCALATION **禁止** AUTO_RECOVERY_ATTEMPT（DiagnosticAgent 強制）
- 9.14.4 AUTO_RECOVERY_ATTEMPT 失敗即進 ESCALATION_FINAL，**不可再嘗試**任何自動處理

**驗收**：
- [ ] DiagnosticAgent 對 fixture 中 30 個 ESCALATION 樣本 ≥ 28 個正確分類（precision ≥ 0.93）
- [ ] AUTO_RECOVERY_ATTEMPT 對 transient 類成功率 ≥ 70%
- [ ] structural 類自動復原次數 = 0（誤觸發=0）
- [ ] Chaos runner 重跑 100 輪後 final_state ∈ {ESCALATION_FINAL, TERMINATED, RELEASE}

---

### M2 — Predictive Halt（預測性停機） 🎯 L5 MVP

**目標**：從 decision_trace + retry pattern 預測「將會崩」，提早切換策略。

| ACT | 交付物 | 路徑 |
|-----|-------|------|
| **ACT-035** | `TrajectoryPredictor` — N-gram + heuristic + last-K window | `tools/fsm_runtime/trajectory_predictor.py` |
| **ACT-036** | Early-switch 機制（PR_REVIEW 同 pattern × 2 即 SPEC_AUDIT） | `tools/fsm_runtime/fsm_runtime.py` 強化 |

**TrajectoryPredictor 演算法**（v1, heuristic）：
```python
def predict(state: FSMState) -> PredictedAction:
    # 信號 1：同 pattern 連續 ≥2 次（語意相似度 ≥ 0.75）
    # 信號 2：retry_count >= 0.6 * max_retries 且 pattern 穩定
    # 信號 3：decision_trace 最近 5 筆 reason 含 "spec_*" 字樣 ≥ 2 筆
    # 信號 4：ledger drift_pct rolling_10 異常上升 (> 30%)
    # → 三/四個信號中 ≥2 個觸發 → switch_to_audit
    # 一個信號 → continue（保守）
```

**新狀態**：`TRAJECTORY_PREDICTED`（observation）
- 入口：任何 retry-prone state（IMPLEMENTATION / PR_REVIEW / RTM_VERIFY / SCG_VALIDATION）
- 出口：`continue`（無強訊號）/ `switch_to_audit`（≥2 信號）/ `abort_early`（≥3 信號）

**Rule 9.15 — Predictive Halt 邊界**：
- 9.15.1 Predictor 僅在 retry_count ≥ 1 時運作（避免 noise）
- 9.15.2 `abort_early` 必須帶 confidence ≥ 0.8 才允許跳過 SPEC_AUDIT 直升 ESCALATION
- 9.15.3 Predictor 預測錯誤（false positive）需記錄至 `build/reports/fsm/PREDICTOR-MISS-{date}.yaml` 供調校
- 9.15.4 同一 stage 內 `switch_to_audit` 僅允許 1 次（避免抖動）

**驗收**：
- [ ] 在 chaos_runner 100 輪中觸發 TRAJECTORY_PREDICTED 的場景 token 消耗 < baseline 的 75%
- [ ] False positive rate < 15%（誤判導致無謂 SPEC_AUDIT）
- [ ] Spec-error fixture 案例中提早終止比 baseline 少 1 次 dev 嘗試

---

### M3 — Spec Ambiguity Quantifier（規格歧義量化）

**目標**：把「Spec 寫得模糊但沒違反 SLV」的灰區拉成量化指標，SCG-0 增加 ambiguity gate。

| ACT | 交付物 | 路徑 |
|-----|-------|------|
| **ACT-037** | `AmbiguityScorer` — 對 FRD 每條 AC 計算 0~1 分數 | `tools/fsm_runtime/ambiguity_scorer.py` |
| **ACT-038** | SCG-0 增加 ambiguity gate（≥0.4 強制人工 review） | `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` 強化 |

**評分維度**（rule-based v1，不依賴外部 LLM）：
| 維度 | 權重 | 信號 |
|------|------|------|
| 量詞缺失 | 0.25 | "快速" / "適當" / "盡可能" 等模糊詞出現次數 |
| 主詞缺失 | 0.20 | passive voice 比例（"應被處理" 等） |
| 數字邊界缺 | 0.20 | NFR 句子缺數字單位（無 ms/req/MB） |
| 否定條件缺 | 0.15 | 只有 happy path，無 "若 X 則 Y" |
| Anchor 缺失 | 0.10 | UI/API 規格無 `<!-- anchor:* -->` |
| 多義詞 | 0.10 | "如同 / 類似 / 相應" 等指代不清 |

**Rule 9.16 — Ambiguity Gate 邊界**：
- 9.16.1 AmbiguityScorer 僅對 FRD 的 AC 段落運作（不對 invariants/architecture 評分）
- 9.16.2 score ≥ 0.4 → SCG-0 fail；< 0.4 才允許往下
- 9.16.3 人工 override 需填寫 `docs/01_requirements/AMBIGUITY-WAIVER-{AC_ID}.md`，附 reviewer 簽名
- 9.16.4 score 計算公式版本變更需 bump `SCORER_VERSION` 並 invalidate 所有快取分數

**驗收**：
- [ ] 對 fixture 中 50 個 AC（25 模糊 + 25 清晰）分類準確率 ≥ 80%
- [ ] SCG-0 拒絕 ambiguity ≥ 0.4 的案例佔比 100%
- [ ] AMBIGUITY-WAIVER 模板可被 docs_template/sdd/requirements/ 複製

---

### M4 — Continuous Drift Monitor（連續漂移監控）

**目標**：每個 commit 後自動檢查 spec ↔ code drift，把 drift 從 gate-time 提前到 commit-time。

| ACT | 交付物 | 路徑 |
|-----|-------|------|
| **ACT-039** | Git PostCommit hook + AST 比對 | `.claude/hooks/post_commit_drift.py` |
| **ACT-040** | `DRIFT_OBSERVATION` 觀測狀態 + 每日漂移報告 | `tools/fsm_runtime/drift_monitor.py` + `build/reports/drift/` |

**Drift 計算**：
- API drift：`docs/02_architecture/api/openapi.yaml` 的 endpoint set 與 code 中實際 routes 的 symmetric_difference / union
- Type drift：FRD 中聲明的 type/enum 與 code 中對應 class/enum 的 missing fields
- Behavior drift：（v2 規劃）AC Given/When/Then 與 test case 的 NLP 比對

**Rule 9.17 — Drift Monitor 邊界**：
- 9.17.1 PostCommit hook 失敗不阻擋 commit（advisory），僅寫 warning 至 `.git/COMMIT_DRIFT_WARNING`
- 9.17.2 drift_score ≥ 0.3 → 自動進 DRIFT_OBSERVATION，FSM 不阻塞但要求下一次 PR_REVIEW 額外驗證
- 9.17.3 連續 3 commits drift_score ≥ 0.3 → 自動轉 SPEC_AUDIT
- 9.17.4 每日 02:30 UTC 產出 `build/reports/drift/DAILY-{date}.md` 滾動 7 天

**驗收**：
- [ ] PostCommit hook 對 100 個 commit 平均執行 < 2s
- [ ] API drift 偵測對 fixture 準確率 ≥ 95%
- [ ] 連續 drift 升級至 SPEC_AUDIT 的場景在 chaos 中正確觸發

---

### M5 — Formal Halt Verification（形式化停機證明） 🎯 L5 MVP

**目標**：把 Chaos 經驗性驗證升級為 TLA+ 形式化證明，給「bounded halting」一個數學憑證。

| ACT | 交付物 | 路徑 |
|-----|-------|------|
| **ACT-041** | TLA+ specification of FSM | `tools/fsm_runtime/formal/SDD_FSM.tla` |
| **ACT-042** | TLC model checker config + CI 整合 | `tools/fsm_runtime/formal/SDD_FSM.cfg` + `cicd/SDD_CICD_BASE_LAYER.md` 新增 step |

**TLA+ 規格大綱**：
```tla
---- MODULE SDD_FSM ----
EXTENDS Naturals, FiniteSets, TLC

VARIABLES state, retry_count, escalation_reason, terminal

States == {"INIT", "SCENARIO_DETECT", "AGENT_LOAD", "SPEC_DRAFTING",
           "SPEC_AUDIT", "SCG_VALIDATION", "SPEC_FROZEN", "IMPLEMENTATION",
           "PR_REVIEW", "RTM_VERIFY", "AUTO_COMPACT_PENDING", "HUMAN_PENDING",
           "PRODUCTION_SIGNAL", "LEARNING_COMMIT", "HUB_SYNC",
           "TRAJECTORY_PREDICTED", "AUTO_RECOVERY_ATTEMPT", "DRIFT_OBSERVATION",
           "ESCALATION", "ESCALATION_FINAL", "TERMINATED", "RELEASE"}

Terminals == {"ESCALATION_FINAL", "TERMINATED", "RELEASE"}

Init == /\ state = "INIT"
        /\ retry_count = 0
        /\ escalation_reason = ""
        /\ terminal = FALSE

Next == \/ state \in Terminals /\ UNCHANGED <<...>>
        \/ ... (transition rules from _HAPPY_PATH)

\* INVARIANT: retry_count never exceeds MAX_RETRIES
RetryBounded == retry_count <= 5

\* THEOREM: every behavior eventually reaches a terminal state
Termination == <>(state \in Terminals)
```

**TLC 配置**：
- 探索深度：50 步
- 變數空間：state × retry_count(0..5) × reason × terminal
- 預期 reachable states ≈ 600~800（含觀測狀態）

**Rule 9.18 — Formal Verification 邊界**：
- 9.18.1 每次 `_HAPPY_PATH` 變更必須同步更新 `SDD_FSM.tla` 並通過 TLC（CI step）
- 9.18.2 TLC 報告 deadlock 或 invariant violation 即 fail PR
- 9.18.3 形式化證明覆蓋率 ≥ 95%（reachable / total）才能宣稱 L5 達成
- 9.18.4 觀測狀態（PRODUCTION_SIGNAL / HUB_SYNC / LEARNING_COMMIT 等）必須被 TLA+ 標記為 transient（不能成為穩定態）

**驗收**：
- [ ] TLC 對所有 reachable state 證明 `[]<> terminal`（必達終態）
- [ ] CI 整合：每個 PR 自動跑 TLC，fail 即 block
- [ ] Reachable states 報告產出於 `build/reports/formal/TLC-COVERAGE-{date}.md`

---

### M6 — Cost-Aware Orchestration（成本感知派遣）

**目標**：orchestrator dispatch 前預估 path token cost，超預算即拒絕並提示替代方案。

| ACT | 交付物 | 路徑 |
|-----|-------|------|
| **ACT-043** | `PathCostEstimator` — 從歷史 ledger 學 baseline | `tools/fsm_runtime/path_cost.py` |
| **ACT-044** | Orchestrator dispatch budget gate | `agent/specialized/sdd-orchestrator-zh.yaml` 強化 |

**估算模型**：
- 每個 (subagent, classification) tuple 維護 rolling-30 平均 token 消耗
- dispatch 前計算 `estimated = avg + 1.5σ`（safety margin）
- gate 條件：`token_remaining > estimated × 1.2`

**Rule 9.19 — Cost-Aware 邊界**：
- 9.19.1 PathCostEstimator 樣本不足（< 10）時，使用保守預設值 `estimated = 8000` tokens
- 9.19.2 dispatch 拒絕需寫入 `build/reports/orchestrator/REJECTED-{date}.yaml`
- 9.19.3 連續 3 次 dispatch 拒絕 → 自動轉 ESCALATION（reason: "budget_exhausted"）
- 9.19.4 estimator 預估誤差 > 50% 連續 5 次 → 警告人工調校

**驗收**：
- [ ] PathCostEstimator 預估誤差 rolling-30 平均 < 30%
- [ ] Budget gate 在 chaos 中正確觸發（token < estimated 時 100% 拒絕）
- [ ] REJECTED log 與 DISPATCH-LOG 互相對齊

---

## 4. 交付排程與依賴

```
G M1 Self-Healing ──┐
                    ├─→ MVP（L5 入口）─→ tag: phase-g-mvp
G M2 Predictive ────┤
                    │
G M5 Formal Verify ─┘

G M3 Ambiguity ─────┐
                    ├─→ L5 成熟期 ─→ tag: phase-g-final
G M4 Drift Monitor ─┤
                    │
G M6 Cost-Aware ────┘
```

| 階段 | 預估工時 | 依賴 |
|------|---------|------|
| G M1 (ACT-032/033/034) | 4d | 無 |
| G M2 (ACT-035/036) | 3d | 需 M1 的 ESCALATION_FINAL state |
| G M5 (ACT-041/042) | 5d | 需 M1+M2 完成的 FSM 狀態圖 |
| **MVP 小計** | **12d** | tag: `phase-g-mvp` |
| G M3 (ACT-037/038) | 3d | 無 |
| G M4 (ACT-039/040) | 3d | 無 |
| G M6 (ACT-043/044) | 3d | 需 M1 的 DiagnosticAgent classification |
| **Final 小計** | **9d** | tag: `phase-g-final` |
| **總計** | **21d** | — |

---

## 5. CLAUDE.md 增補規則總覽

新增 6 條 Rule（9.14 ~ 9.19），對應 Phase G 6 個 milestone。具體條文見上方各 milestone 章節。

**禁止行為彙整**（將寫入 CLAUDE.md §9 Phase G 區塊）：
- 繞過 DiagnosticAgent 直接呼叫 AUTO_RECOVERY_ATTEMPT（破壞 1-shot bounded recovery）
- 對 `category=structural` 的 ESCALATION 強行觸發 auto-recovery
- TrajectoryPredictor `abort_early` 不附 confidence ≥ 0.8 證據卻直升 ESCALATION
- 修改 `_HAPPY_PATH` 但不同步 `SDD_FSM.tla`（破 Rule 9.18.1 雙源一致性）
- AmbiguityScorer 公式變更不 bump `SCORER_VERSION`（cache 中毒）
- PostCommit drift hook 阻擋 commit（必須 advisory，違反 9.17.1）
- PathCostEstimator 樣本不足時用過度樂觀 default（必須 ≥ 8000 保守值）

---

## 6. 風險與緩解

| 風險 | 機率 | 影響 | 緩解 |
|------|------|------|------|
| DiagnosticAgent 誤分類 structural 為 transient（誤自動修復 spec） | 中 | 高 | M1 驗收要求 precision ≥ 0.93；structural→auto_recoverable=false 由 schema 強制 |
| TrajectoryPredictor false positive 過高（過度悲觀） | 中 | 中 | M2 驗收要求 FP rate < 15%；PREDICTOR-MISS log 持續校準 |
| TLA+ 規格與實作脫節（規格演化但 .tla 沒跟） | 高 | 高 | M5 在 CI 強制每次 `_HAPPY_PATH` 變更同步 .tla（Rule 9.18.1） |
| AmbiguityScorer 過度誤判（清晰 AC 被判模糊） | 中 | 中 | M3 提供 AMBIGUITY-WAIVER 通道；fixture 校準 ≥ 80% |
| PostCommit hook 影響 commit 速度 | 低 | 低 | M4 要求 < 2s；超時自動 skip 並警告 |
| PathCostEstimator 冷啟動失準 | 高 | 中 | M6 規定樣本 < 10 時用保守 default 8000 |

---

## 7. 與 Phase A~F 的關係

| Phase | 達成等級 | Phase G 如何延伸 |
|-------|---------|------------------|
| A 紙上規則 | L3 | M5 把 FSM 規則升級為形式化證明 |
| D Runtime Hook | L4 | M1 在 hook 之上加 self-healing layer |
| E M1 精準停機 | L4.5 | M2 把「反應式停機」升級為「預測性停機」 |
| E M2 閉環品質鏈 | L4.7 | M6 利用 ledger drift_pct 做成本預估 |
| E M2.5 Chaos | L4.8 | M5 把 Chaos 經驗證明升級為 TLA+ 形式證明 |
| E M3 Production Feedback | L4.9 入口 | M4 把 SLO drift 概念內化為 Spec↔Code drift |
| E M4 Learning Layer | L4.9 入口 | M1 DiagnosticAgent 可作為 SLV Generator 的下游消費者 |
| F M2 Hub | L4.9 | （無直接互動；Hub 仍走原 push/pull） |
| F M3/M4 多模態 | L4.9 | M3 AmbiguityScorer 可呼叫 multimodal_validator anchor 缺失信號 |

---

## 8. 完成定義（Definition of Done）

### Phase G MVP（L5 入口） — 達成條件
- [ ] M1/M2/M5 全部 ACT 完成且通過驗收
- [ ] Chaos runner 100 輪重跑 final_state ∈ {ESCALATION_FINAL, TERMINATED, RELEASE} 100%
- [ ] 平均 token 消耗 ≤ Phase F baseline 的 80%（節省自動復原與預測停機）
- [ ] TLC 對 reachable state coverage ≥ 95%
- [ ] CLAUDE.md Rule 9.14 / 9.15 / 9.18 落字
- [ ] AISDLC_SDD_INIT.md 新增 Phase G MVP 元件對照表
- [ ] 全部 fsm_runtime/tests 通過（預期 285 → ~330 tests）
- [ ] git tag: `phase-g-mvp`

### Phase G Final（L5 成熟） — 達成條件
- [ ] M3/M4/M6 全部 ACT 完成且通過驗收
- [ ] AmbiguityScorer 對 fixture 準確率 ≥ 80%
- [ ] PostCommit drift hook 平均執行 < 2s
- [ ] PathCostEstimator 預估誤差 rolling-30 < 30%
- [ ] CLAUDE.md Rule 9.16 / 9.17 / 9.19 落字
- [ ] DAILY-{date}.md drift report 連續 7 天產出
- [ ] git tag: `phase-g-final`
- [ ] 框架版本聲明升至 `AISDLC-SDD v0.01 — Phase G L5 Self-Driving`

### 完工後動作
- [ ] 本檔 `SDD_improving_Automation_06.md` 移至 `archive/`
- [ ] 推送至 `wuweihungmobile/AISDLC_SDD` main
- [ ] 更新 INIT 與 CLAUDE.md 的 Phase G 區塊

---

## 9. OPEN QUESTIONS（待 PM 決策）

| ID | 問題 | 預設 | 影響 milestone |
|----|------|------|---------------|
| OPEN-G.1 | DiagnosticAgent 分類器使用 rule-based 還是 LLM 推論？ | rule-based v1（避免成本） | M1 |
| OPEN-G.2 | TrajectoryPredictor 是否需要 ML 模型，或維持 heuristic？ | heuristic v1；觀察 false-positive 後 v2 再決策 | M2 |
| OPEN-G.3 | AmbiguityScorer 是否要呼叫 multimodal_validator 整合 anchor 信號？ | v1 不整合（保持獨立性）；v2 視成熟度納入 | M3 |
| OPEN-G.4 | PostCommit hook 是 git native hook 還是 .claude/hooks 機制？ | git native（與 Claude Code session lifecycle 解耦） | M4 |
| OPEN-G.5 | TLA+ 工具鏈是 TLC（CLI）還是 Apalache？ | TLC（CLI 容易 CI 整合） | M5 |
| OPEN-G.6 | PathCostEstimator 對新 subagent 的冷啟動 default 值是 5000 還是 8000？ | 8000（保守，符合 Rule 9.19.1） | M6 |

---

## 10. 後續 Phase 預留

- **Phase H — Multi-Stream FSM**：支援同一專案多 feature 並行 SDD（branch FSM + join semantics）
- **Phase I — Project Memory**：跨 session 向量索引的 decision archive（取代 CONTEXT-SNAPSHOT 文字摘要）
- **Phase J — Test Oracle Automation**：AC → property-based test 自動產出（metamorphic relations）
- **Phase K — Spec Evolution Audit**：semantic diff for spec changes（自動偵測 breaking spec change → 強制 ADR）

---

**規劃版本**: v1.0
**規劃者**: Chief AI Automation Architect (Claude Opus 4.7)
**規劃日期**: 2026-04-26
**對應 Phase tag**: 完成後 `phase-g-mvp` → `phase-g-final`
**前置 tag**: `phase-f-final` @ `67d7e38`
