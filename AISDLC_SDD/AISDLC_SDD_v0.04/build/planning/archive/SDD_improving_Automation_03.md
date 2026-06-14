# SDD Agentic 閉環自動化 — Phase D 執行藍圖
# Turing-Completeness Audit & Level 5 Roadmap for AISDLC-SDD

**文件編號**: SDD_improving_Automation_03
**建立日期**: 2026-04-19
**分析對象**: AISDLC-SDD v0.01（Phase A 完成 + Phase B 已落實 + Automation_02 ACT-002~007 已部分落地）

> **🟢 2026-04-19 閉環 QA 補強**：發現「Token 90% Auto-Compact 完整迴圈」缺收尾步驟（FSM 永遠卡 AUTO_COMPACT_PENDING + Ledger 不歸零 → 無限觸發），已修補：
> - `tools/fsm_runtime/fsm_runtime.py` 新增 `_reset_today_ledger()` + `complete_auto_compact()` 預設重置 ledger
> - CLI 新增 `complete-auto-compact` / `reset-ledger` 兩條指令
> - `.claude/skills/stage-compaction/SKILL.md` 加 Bash 至 allowed-tools，新增 Step 5 強制呼叫 CLI
> - `tools/fsm_runtime/tests/test_e2e_smoke.py` 新增 S10 守護完整迴圈（28/28 全綠）
**評審角色**: 首席 AI 自動化架構師（Karpathy 風格）
**前置文件**:
- `SDD_improving_Automation_01.md`（Phase A/B：FSM + ESCALATION + SLV + Compaction）
- `SDD_improving_Automation_02.md`（架構健檢：VUL-001~010 + ACT-001~009）

**核心論斷**:
> 目前框架在「防止 AI 失控」上已達成就業界領先水準（Level 4.3），
> 但距離「AI 自主驅動完整 SDLC」仍差三個要件：
> **(1) 執行層（FSM 從文件升級為 Runtime）；**
> **(2) 調度層（Subagent Orchestrator 實現 Test→AI Fix 自動閉環）；**
> **(3) 學習層（Failure Pattern 回饋到 SLV 規則庫的自我演化）。**

---

## 壹、Self-Verification：極端案例流程推演

### 1.1 案例組：「Spec 寫錯導致測試永遠無法通過」的三種變體

為了避免給自己打高分，我設計了三個難度遞增的變體，讓現有（Phase A+B+C 部分）流程跑一遍。

#### 變體 A — 物理不可行（低階錯誤）
```
FRD AC-003-1: "登入回應時間必須 < 0ms"
```

**流程推演**：
```
SPEC_DRAFTING → SCG-0 前置
  └─ /spec-logical-validator
       └─ SLV-001（NFR 物理可行性）: response_time_ms > 0 → ❌ FAIL
  └─ SCG_VALIDATION retry_count++（1/3）
  └─ 退回 SPEC_DRAFTING 修正
  
→ ✅ 偵測成功。Token 浪費：~2K（僅 SLV 執行成本）
```

**結論**：現有機制可優雅攔截。

---

#### 變體 B — 語義不一致（中階錯誤）
```
FRD AC-003-1: "登入回應時間 P95 < 200ms"
Test Contract: expect(loginTime_ms).toBeLessThan(20)  ← TCS 誤寫為 20ms
SRD: "驗證邏輯含 2 次 bcrypt hashing，單次約 60~80ms"
```

**流程推演**：
```
SCG-0 → SLV-001 PASS（200 > 0）
SCG-3 → SLV-004 PASS（Contract 與 FRD 相容）
SCG-3 → SLV-005（Test 可達性）
  └─ 讀取 TCS: < 20ms
  └─ 比對 SRD: bcrypt ≈ 120ms
  └─ ❌ SLV-005 FAIL: Test assertion 超出架構物理下限
  
→ ✅ 偵測成功（若 SLV-005 推理能讀懂 bcrypt 成本）
```

**風險**：SLV-005 的推理精度依賴 Claude 對 SRD 內容的理解深度。
若 SRD 未明寫 bcrypt 成本（僅寫「使用 bcrypt」），SLV-005 可能 PASS。
進入 IMPLEMENTATION 後依靠 `max_test_fail_without_spec_change: 5` 兜底。

---

#### 變體 C — 時序語義矛盾（高階錯誤，目前 SLV 無法捕獲）
```
FRD AC-015-1: "系統必須保證第 N+1 次相同請求的回應時間
              比第 N 次快至少 50%（除 N=1 外）"
```

這條 AC 在物理上可行（快取機制可使 N+1 更快），但不是可持續的穩態承諾（快取 eviction 後會回升）。

**流程推演**：
```
SLV-001 PASS（無數值 > 0 問題）
SLV-002 PASS（量化：50%、可觀察：時間比率）
SLV-003 PASS（不與其他 INV 直接衝突）
SLV-004 PASS（API 無對應欄位矛盾）
SLV-005 PASS（測試可寫出來）
SLV-006 PASS（無循環依賴）
→ 所有 SLV 通過，SCG-0 PASS，進入凍結

IMPLEMENTATION：
  Dev 寫快取 → Unit Test 第 1 輪通過
  Integration Test: 執行 10 分鐘後觸發 eviction → Test N+1 比 N 慢 → FAIL
  
  PR_REVIEW retry #1 → FAIL（相同 test）
  PR_REVIEW retry #2 → FAIL
  PR_REVIEW retry #3 → pattern_detection 觸發 → SPEC_AUDIT
  
SPEC_AUDIT:
  讀取 AC + Test Contract → 重跑 SLV-001~006
  SLV 全過 → "無矛盾" → 回 PR_REVIEW（retry_count 重置，spec_audit_count=1）
  
PR_REVIEW retry #1（重置後）→ FAIL
PR_REVIEW retry #2 → FAIL
PR_REVIEW retry #3 → SPEC_AUDIT（spec_audit_count=2）
SPEC_AUDIT: max_executions_per_stage=2 已達 → 🚨 ESCALATION
  
→ 系統停止，產出 Abort Report
```

**結論**：**靠 ACT-006（SPEC_AUDIT 次數上限）兜底成功**。
但代價是：消耗 6 次 PR_REVIEW + 2 次 SPEC_AUDIT ≈ 15~25K tokens。
若能由更聰明的 SLV-007+ 在 SCG-0 捕獲，可節省 90%+ 資源。

---

### 1.2 自驗結論

| 錯誤層級 | 現有機制能否優雅攔截 | Token 浪費估算 | 改進方向 |
|---------|----------------|--------------|---------|
| 物理不可行（變體 A） | ✅ SLV-001 直接攔 | ~2K | — |
| 語義不一致（變體 B） | 🟡 依賴 SLV-005 推理深度 | ~5K | SLV-005 強化，對 SRD NFR 章節深度抓取 |
| 時序/業務語義矛盾（變體 C） | 🟡 靠 ACT-006 兜底（非優雅） | ~20K | SLV-007+ 時序矛盾規則、Failure Pattern Library |
| 跨文件隱性矛盾（未列舉） | ❌ 無機制 | 可能無限，直到 ESCALATION | 需要 Cross-Document Semantic Checker |

**Karpathy 式評語**：
> 「系統在『阻止失控』這一層做得很紮實——就像飛機的迎角失速保護。
> 但要達到『自駕』，光有失控保護不夠，還需要高精度的傳感器（更多 SLV 規則）、
> 即時決策（FSM Runtime 而非文件）、與路徑學習（Failure Pattern 回饋）。」

---

## 貳、現況診斷補遺：Automation_01/02 未覆蓋的 10 個結構性缺口

Phase A/B 已解決「無限重試」問題（RC-01），Automation_02 解決「持久化 + 編號一致 + Test 映射」問題（ACT-001~006）。
但以下 10 個缺口仍未觸及：

### RC-11：FSM 是文件，不是執行引擎

**現況**：
```
SDD_FSM_ENGINE.md 是 Markdown。
retry_count 靠 Claude「記得遞增」。
狀態轉換靠 Claude「記得判斷」。
無任何強制機制。
```

**後果**：
- 若 Claude 在某次對話中「忘記」檢查 retry_count（或被 user prompt 誤導），防護機制形同虛設
- 跨 Session 恢復時，retry_count 的讀取依賴人工指示，可能被錯誤重置
- `build/reports/fsm/FSM-STATE-{project}.yaml` 沒有 Consumer，沒有 Producer

**改進方向**：見 ACT-010（FSM Runtime 腳本 + Hooks 強制執行）。

---

### RC-12：CI-EVENT 產出但無 Consumer

**現況**：
```yaml
# SDD_CICD_BASE_LAYER.md
ci_to_fsm_bridge:
  output_event: "build/reports/fsm/CI-EVENT-{date}-{pipeline_id}.yaml"
  fsm_read_timing: "FSM 在每次 SCG_VALIDATION 開始時，掃描所有未處理的 CI-EVENT-*.yaml"
```

**問題**：「FSM」是一個文件，不會「執行」任何動作。SCG_VALIDATION 是一個狀態標籤，不會主動「掃描」文件。實際必須由 Claude 主動讀取——但沒有機制強制 Claude 在進入 SCG_VALIDATION 時讀取 CI-EVENT。

**後果**：CI 失敗事件會無聲堆積，retry_count 永遠不會被外部事件遞增。

**改進方向**：見 ACT-011（SessionStart Hook 自動讀取 CI-EVENT 並 reconcile FSM-STATE）。

---

### RC-13：Token Budget 無實測

**現況**：Governor 定義 70/85/95% 閾值，但 Claude 沒有 API 取得實際 context 使用量。
依賴「每 Stage 預估 Token 消耗表」，誤差可能 20~40%。

**後果**：
- 真正達到 95% 時可能已經「找不到空間」產出 Context Snapshot，優雅中止失敗
- 或提前觸發 Compaction，浪費 Summary 寫入成本

**改進方向**：見 ACT-012（Context Ledger，PreToolUse Hook 累計檔案大小 + 對話字數估算）。

---

### RC-14：test-failure-analyzer 是建議者、不是決策者

**現況**：TFA Skill 產出「分類 A/B/C/D + 建議行動」，但下一步動作仍需人工觸發。

**閉環缺口示意**：
```
現況:  Test FAIL → TFA → 報告 → 👤 人工讀報告 → 👤 人工決策 → 👤 人工派 Agent 修
應為:  Test FAIL → TFA → 分類 B → 🤖 自動觸發 SPEC_AUDIT
                       → 分類 A → 🤖 自動派遣 dev-senior 修復
                       → 分類 D → 🤖 自動標記環境問題並重跑
```

**後果**：Test→Fix 迴圈仍需人工驅動，閉環第 3、4 點（AI 自主修正）無法達成。

**改進方向**：見 ACT-013（TFA 加入 auto_dispatch_rules + Orchestrator）。

---

### RC-15：SPEC_FROZEN 的 retry 重置無「真實修正驗證」

**現況**：SPEC_FROZEN milestone 重置 current_count = 0；cumulative_history 記錄但不阻塞。

**漏洞劇情**：
```
Stage 2 SCG-0 retry_count = 2（已消耗 2/3）
Human 進行「表面修正」但未解決根因 → 強行 approve SPEC_FROZEN
→ current_count 重置為 0
→ 下個 Stage 類似問題再度出現
→ cumulative_total = 5 但仍可繼續
```

**後果**：retry_budget 被策略性繞過（無論是人工疏忽或 AI 誤判）。

**改進方向**：見 ACT-014（SPEC_FROZEN 前插入 Regression SLV check；cumulative 超閾值阻塞）。

---

### RC-16：SLV 規則庫靜態、不自我演化

**現況**：SLV-001~006 寫死在 SKILL.md。若某專案發現新的矛盾模式（如變體 C 的時序語義），該洞察無法 codify 成新規則讓後續專案受益。

**後果**：框架不會「變聰明」；相同錯誤在不同專案重複發生。

**改進方向**：見 ACT-015（Failure Pattern Library + SLV Rule Generator）。

---

### RC-17：Brownfield/場景特化 FSM 路徑不完整

**現況**：FSM 以 Greenfield 為藍本（SPEC_DRAFTING 為起點）。但：
- Brownfield 真實起點：CODE_ANALYSIS → AS_IS_SRD → GAP_ANALYSIS → TO_BE_SRD
- Refactoring 起點：INVARIANT_EXTRACTION → BEFORE_ARCH_SNAPSHOT
- Migration 起點：CURRENT_STATE_INVENTORY → CUTOVER_DESIGN，終點含 ROLLBACK_READY 與 CANARY_COMPLETE

**後果**：10 個場景中，只有 Greenfield 有完整 FSM 保護；其餘場景進入特殊流程時，FSM 狀態不明確，retry budget 無處追蹤。

**改進方向**：見 ACT-016（Scenario FSM Variant — 場景專屬 FSM 子圖）。

---

### RC-18：無「子 FSM」— IMPLEMENTATION 是黑盒

**現況**：
```
FSM: ... → SPEC_FROZEN → IMPLEMENTATION → PR_REVIEW → ...
```

ACT-003 已加 implementation_budget（max_iterations: 20、consecutive_compile_fail: 3、test_fail_without_spec_change: 5），但沒有展開子狀態。

**後果**：在 IMPLEMENTATION 內的決策分支（如「這個測試失敗是 bug 還是 flaky？」「這個編譯錯誤該改 A 還是改 B？」）沒有可追蹤狀態，debug 困難。

**改進方向**：見 ACT-017（IMPLEMENTATION 子 FSM：CODE_GEN → COMPILE → UNIT_TEST → DIAGNOSE → AUTO_FIX → INTEGRATION_TEST）。

---

### RC-19：無生產運行時回饋路徑

**現況**：VUL-010 已識別；Automation_02 列為 P2。
目前部署完成即視為閉環終點，但真實世界 SLO 違反、錯誤率上升、用量超預期等訊號，無法回到 Spec 層觸發 PBS/NFR 更新。

**後果**：框架只到「交付」閉環，不到「運行」閉環。

**改進方向**：見 ACT-018（Production SLO → PBS 自動觸發 + Spec Drift Detection）。

---

### RC-20：Session 恢復無「修正驗證」閘門

**現況**：
```yaml
# AISDLC_SDD_INIT.md session_resume
step_5: "詢問人工確認恢復點：{上次建議的 RESUME_STATE}"
step_6: "重置 retry_count 為 0（人工已介入修復）"
```

人工只要答「確認恢復」即通過，系統沒有驗證「上次中止的根因是否真的被修復」。

**漏洞劇情**：
```
Session 1: ESCALATION（因 SLV-001 FAIL × 3）
Session 2: Human 答「確認恢復」→ retry_count 歸零
          但 FRD 實際未修正 → SLV-001 再度 FAIL → 再 ESCALATION
          cumulative 歷史已 >10 但無阻塞
```

**後果**：同一根因錯誤可被無限「恢復」，各次消耗固定成本但無進度。

**改進方向**：見 ACT-019（Resume Gate — 恢復前強制重跑對應 SLV + diff 檢查）。

---

## 參、FSM 2.0 設計：從文件升級為 Runtime

### 3.1 分層架構（Level 5 Target）

```
┌──────────────────────────────────────────────────────────────────┐
│ Layer 4: Learning Layer（新增）                                  │
│   - Failure Pattern Library                                       │
│   - SLV Rule Generator（AI-assisted）                            │
│   - Cross-Project Spec Anomaly Repository                        │
└──────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│ Layer 3: Production Feedback Layer（新增）                       │
│   - SLO Monitor → PBS Drift Detector                              │
│   - Incident Report → FRD NFR Refresh Queue                       │
│   - Production Metric → Spec Gap Identifier                      │
└──────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│ Layer 2: Orchestration Layer（新增，Level 5 核心）              │
│   - Subagent Dispatcher（sa / sd / dev / qa / reviewer）         │
│   - Test Result Router（TFA → Auto Fix Agent）                   │
│   - Auto Recovery Engine（SPEC_AUDIT → Agent 路由）              │
└──────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│ Layer 1: FSM Runtime Layer（升級，取代目前文件式 FSM）           │
│   - fsm_runtime.py（狀態讀寫 FSM-STATE-{project}.yaml）          │
│   - SessionStart Hook（載入狀態、reconcile CI-EVENT）             │
│   - PreToolUse Hook（驗證狀態允許該操作）                        │
│   - PostToolUse Hook（更新 retry_count、寫入 transition log）     │
│   - Context Ledger（實測 token 使用量）                          │
└──────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│ Layer 0: Foundation Layer（現有，Phase A/B 完成）                │
│   - SDD_FSM_ENGINE.md（狀態定義 — 作為 spec）                    │
│   - SLV-001~006 Skills                                            │
│   - Stage Compaction                                              │
│   - ESCALATION Protocol                                           │
│   - FSM-STATE-TEMPLATE.yaml                                      │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 新增狀態清單（FSM 2.0）

在現有 12 狀態基礎上新增 8 個：

| 編號 | 新狀態 | 類型 | 觸發 | 對應 RC |
|-----|-------|------|------|--------|
| S13 | CODE_GENERATING | IMPLEMENTATION 子狀態 | SPEC_FROZEN 後、進入首次 PR_REVIEW 前 | RC-18 |
| S14 | COMPILE_LOOP | IMPLEMENTATION 子狀態 | 編譯失敗時 | RC-18 |
| S15 | AUTO_DIAGNOSIS | 診斷狀態 | TFA 判斷後路由 | RC-14 |
| S16 | AUTO_FIX_ATTEMPT | IMPLEMENTATION 子狀態 | 分類 A（代碼錯誤） | RC-14 |
| S17 | SPEC_REGRESSION_CHECK | gatekeep | SPEC_FROZEN 前 | RC-15 |
| S18 | RESUME_VERIFICATION | gatekeep | Session resume 時 | RC-20 |
| S19 | PRODUCTION_SIGNAL | 監測狀態 | SLO violation event | RC-19 |
| S20 | LEARNING_COMMIT | 背景狀態 | ESCALATION 結案時 | RC-16 |

### 3.3 核心 FSM Runtime 職責（偽代碼）

```python
# tools/fsm_runtime.py（Phase D 新增，示意）
class FSMRuntime:
    def on_session_start(self):
        state = load_yaml("build/reports/fsm/FSM-STATE-{project}.yaml")
        for event in glob("build/reports/fsm/CI-EVENT-*.yaml"):
            if not event.processed:
                state.apply(event)
                mark_processed(event)
        check_cumulative_budget(state)  # 若超閾值，強制 ESCALATION
        return state
    
    def pre_tool_use(self, tool, params):
        # 驗證狀態允許該動作
        if state.current == "ESCALATION":
            block("ESCALATION 狀態下禁止自動操作，等待人工解除")
        if tool == "Write" and is_spec_file(params.path):
            if state.current not in ["SPEC_DRAFTING", "SPEC_AUDIT"]:
                block(f"當前狀態 {state.current} 不允許修改規格文件")
    
    def post_tool_use(self, tool, params, result):
        # 根據 tool 結果更新 retry_count
        if is_scg_validation_result(result):
            if result.status == "FAIL":
                state.retry_count["SCG_VALIDATION"] += 1
                if state.retry_count["SCG_VALIDATION"] >= 3:
                    transition_to("ESCALATION")
        save_yaml(state)
    
    def context_ledger(self):
        # 累加本 session 已讀文件大小 + tool 回傳 token 估算
        # 達到閾值時產生 compaction 提醒
        pass
```

Runtime 由 settings.json 的 hooks 觸發：

```json
{
  "hooks": {
    "SessionStart": [{"command": "python .claude/hooks/fsm_on_start.py"}],
    "PreToolUse": [{"command": "python .claude/hooks/fsm_pre_tool.py"}],
    "PostToolUse": [{"command": "python .claude/hooks/fsm_post_tool.py"}],
    "UserPromptSubmit": [{"command": "python .claude/hooks/fsm_check_state.py"}]
  }
}
```

### 3.4 完整狀態圖（Level 5）

```
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 1 RUNTIME HOOKS: SessionStart | PreToolUse | PostToolUse     │
│            ↓ 每次 tool call 都讀寫 FSM-STATE.yaml                   │
└────────────────────────────────────────────────────────────────────┘

INIT → SCENARIO_DETECT → AGENT_LOAD ──┐
                                      ↓
                                 ┌────────────────┐
                                 │ SPEC_DRAFTING  │◄───────────────────┐
                                 └───────┬────────┘                    │
                                         ↓                              │
                                 SCG_VALIDATION                         │
                                 （含 SLV 前置）                         │
                                    /       \                           │
                                [PASS]    [FAIL<3] ────────────────────┘
                                   ↓         \
                                   ↓      [FAIL≥3]
                                   ↓         ↓
                              HUMAN_PENDING  ESCALATION ◄────────┐
                                   ↓                              │
                                SPEC_REGRESSION_CHECK ⭐NEW       │
                                （確認修正非表面 patch）            │
                                   ↓                              │
                              SPEC_FROZEN                         │
                              （→ stage-compaction）              │
                                   ↓                              │
                            ┌──────┴──────┐                       │
                            ↓ [subagent dispatch] ⭐NEW          │
                      CODE_GENERATING                             │
                            ↓                                     │
                      COMPILE_LOOP ⭐NEW ──[fail≥3]───────►ESCALATION
                            ↓                                     │
                      UNIT_TEST                                   │
                            ↓                                     │
                      [fail] → AUTO_DIAGNOSIS ⭐NEW                │
                              ↓                                   │
                        ┌─────┴─────┐                             │
                        ↓ classify  ↓                             │
                    [A/C/D]      [B]                              │
                        ↓           ↓                             │
                  AUTO_FIX_ATTEMPT  SPEC_AUDIT                    │
                        ↓           ↓                             │
                      (retry up to 5)                             │
                        ↓                                         │
                      PR_REVIEW ──────────────────────►ESCALATION │
                            ↓                                     │
                      RTM_VERIFY ─────────────────────►ESCALATION │
                            ↓                                     │
                      RELEASE_READY                               │
                            ↓                                     │
                         RELEASE                                  │
                            ↓                                     │
                      PRODUCTION_SIGNAL ⭐NEW                      │
                      （SLO 監測）                                │
                            ↓                                     │
                      [violation] → PBS_REFRESH_QUEUE ────────────┘
                            
                      TERMINATED → LEARNING_COMMIT ⭐NEW
                                   （更新 Failure Pattern Library）
```

---

## 肆、Context & Memory 管理策略 2.0

### 4.1 三層記憶體模型

從「單一上下文視窗」升級為分層：

```yaml
memory_tiers:
  hot:  # 始終在活躍 context
    size: "< 10K tokens"
    contents:
      - "Stage Summary（當前 Stage）"
      - "FSM 當前狀態快照"
      - "正在編輯的 1~3 份文件"
    volatility: "每次工具呼叫可變"
    
  warm:  # 按需載入，Read 即進來
    size: "10K ~ 50K tokens"
    contents:
      - "RTM ID 清單 + 狀態"
      - "Active ADR 索引"
      - "當前 Stage 的前一 Stage Summary"
    volatility: "Stage 間不變"
    
  cold:  # 永不進 context，只寫不讀（除非明確 Read）
    size: "無上限"
    contents:
      - "所有 docs/ 持久化文件"
      - "歷史 FSM transition log"
      - "歷史 SCG 報告"
      - "Failure Pattern Library"
    volatility: "累積不刪"
```

### 4.2 Context Ledger（實測 Token 管理）

現行 Governor 使用「Stage 預估表」，精度差且不適應長尾場景。改進方案：

```python
# .claude/hooks/context_ledger.py（Phase D 新增）
def on_pre_tool(tool, params):
    if tool == "Read":
        estimated_tokens = file_size(params.path) / 4  # ~4 chars per token
        append_to("build/reports/fsm/CONTEXT-LEDGER-{date}.yaml", {
            "timestamp": now(),
            "action": "READ",
            "target": params.path,
            "estimated_tokens": estimated_tokens
        })
    elif tool == "Write":
        estimated_tokens = len(params.content) / 4
        append_to(ledger, ...)

def on_post_tool(tool, params, result):
    result_tokens = len(str(result)) / 4
    append_to(ledger, ...)
    
    cumulative = sum_session_tokens()
    if cumulative > 0.85 * MAX_CONTEXT:
        inject_user_message("⚠️ Context 已達 85%，建議執行 /stage-compaction")
    if cumulative > 0.95 * MAX_CONTEXT:
        block_further_tools()
        trigger_escalation("TOKEN_BUDGET_CRITICAL")
```

### 4.3 Adaptive Compaction 策略

現行 Compaction 只在 SPEC_FROZEN 觸發。升級後依據「成本/收益」動態決策：

```yaml
adaptive_compaction:
  trigger_signals:
    spec_frozen:
      weight: 1.0   # 強制執行
    context_above_70:
      weight: 0.5
    same_file_read_3plus_times:
      weight: 0.7   # 反覆讀同一檔案 → 值得加進 Stage Summary
    stage_transition:
      weight: 0.6
  
  decision:
    if sum(active_signals) >= 1.0:
      execute_compaction()
```

### 4.4 跨 Session 上下文恢復強化

Context Snapshot 升級為包含「決策推理軌跡」：

```markdown
# CONTEXT-SNAPSHOT-{date}.md（新增章節）

## 關鍵決策軌跡（Decision Trace）
| 時間 | 狀態 | 決策 | 推理摘要 | 依據文件 |
|------|-----|------|---------|---------|
| 10:15 | SCG-2 | 採用 PostgreSQL | 符合 NFR-PERF-002 + ADR-001 評估 | ADR-001, NFR-PERF-002 |
| 11:20 | SPEC_AUDIT | 判定無矛盾 | AC-015-1 + INV-003 相容 | FRD L.87, INVARIANT-003 |

## 隱性共識（Implicit Consensus）
- 沿用 REST 而非 GraphQL（未寫入 ADR，但已在對話中確認）
- 延後 i18n 到 v0.02（已決議但未更新 PRD）
```

新 Session 恢復時，必須讀取此軌跡才能做出一致決策。

---

## 伍、Level 5 自治開發流程終極藍圖

### 5.1 自治等級重新定義

| Level | 描述 | 關鍵能力 | 現況 |
|-------|------|---------|------|
| L1 | 純人工 | — | — |
| L2 | AI 輔助 | Copilot | — |
| L3 | AI 完成單任務 | ChatGPT | — |
| L4 | AI 驅動 workflow，人工守閘 | Agentic（現況） | ✅ |
| **L4.3** | L4 + 閉環防護（FSM + SLV + ESCALATION） | **現況真實水準** | ✅ |
| L4.7 | L4.3 + FSM Runtime + Orchestrator | Phase D 目標 | — |
| L5 | 完全閉環，AI 自主決策人工介入時機 | + Learning Layer + Production Feedback | Phase E 目標 |
| L6 | AI 自我演化框架 | 從專案產出改寫 SLV 規則 | 遠景 |

### 5.2 Phase 對應路線圖

```
Phase A（已完成 2026-04-18）
  ✅ SDD_FSM_ENGINE.md 形式化狀態機（文件層）
  ✅ SDD_ESCALATION_PROTOCOL.md 退場機制
  ✅ spec-logical-validator SKILL（SLV-001~006）

Phase B（已完成 2026-04-18）
  ✅ SDD_CONTEXT_GOVERNOR.md 預算定義
  ✅ stage-compaction SKILL
  ✅ SDD_ABORT_REPORT_TEMPLATE.md

Phase C（由 Automation_02 啟動，部分完成 2026-04-19）
  ✅ ACT-001 SCG 編號統一
  ✅ ACT-002 FSM-STATE-TEMPLATE.yaml 持久化 schema
  ✅ ACT-003 IMPLEMENTATION budget
  ✅ ACT-004 test-failure-analyzer SKILL
  ✅ ACT-005 SpecTrace 分階段阻塞
  ✅ ACT-006 SPEC_AUDIT 次數上限
  ✅ ACT-007 CI/CD → FSM Bridge（定義層）
  🟡 ACT-008 cumulative retry 防濫用（僅記錄未阻塞）
  ⏳ ACT-009 Production SLO → PBS（P2）

Phase D — L4.3 → L4.7（本藍圖，預估 3~4 週）
  ⏳ ACT-010 FSM Runtime（tools/fsm_runtime.py）
  ⏳ ACT-011 SessionStart Hook（自動 reconcile CI-EVENT）
  ⏳ ACT-012 Context Ledger（實測 token）
  ⏳ ACT-013 TFA Auto-Dispatch（分類 → 自動路由 subagent）
  ⏳ ACT-014 SPEC_REGRESSION_CHECK gate
  ⏳ ACT-015 初版 Failure Pattern Library（手動 curate）
  ⏳ ACT-016 Scenario FSM Variants（Brownfield/Refactoring/Migration）
  ⏳ ACT-017 IMPLEMENTATION 子 FSM
  ⏳ ACT-019 Resume Verification Gate

Phase E — L4.7 → L5（預估 6~8 週）
  ⏳ ACT-018 Production SLO → PBS Auto-Refresh
  ⏳ ACT-020 SLV Rule Generator（AI 輔助，從 Failure Pattern 產生新規則）
  ⏳ ACT-021 Subagent Orchestrator（sdd-orchestrator agent）
  ⏳ ACT-022 Cross-Project Learning Hub
```

### 5.3 Phase D 詳細 ACT 規格

---

#### ACT-010：FSM Runtime 實作

**目標**：把 FSM 從 Markdown 文件升級為可執行的狀態機引擎。

**交付物**：
```
tools/fsm_runtime/
├── fsm_runtime.py          # 核心引擎
├── state_loader.py         # 讀寫 FSM-STATE.yaml
├── transition_rules.py     # 轉換邏輯（與 SDD_FSM_ENGINE.md 同步）
├── event_reconciler.py     # 處理 CI-EVENT
└── tests/
    └── test_transitions.py # 覆蓋所有狀態轉換
```

**API 規格**：
```python
fsm = FSMRuntime.load("build/reports/fsm/FSM-STATE-{project}.yaml")
fsm.assert_state_allows(action="Write", target="docs/01_requirements/FRD-*.md")
fsm.record_gate_result("SCG_VALIDATION", result="FAIL", reason="...")
if fsm.should_escalate():
    fsm.trigger_escalation(abort_report_path=...)
fsm.save()
```

**驗收標準**：
- 單元測試覆蓋 FSM 定義中所有 state × transition 組合
- 與現有 SDD_FSM_ENGINE.md 文件 100% 同步（測試自動比對）
- 支援 dry-run 模式（驗證不寫入）

---

#### ACT-011：SessionStart Hook + CI-EVENT Reconciler

**目標**：每個新對話自動檢查未處理的 CI-EVENT 並更新 FSM 狀態。

**新增 Hook**：
```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "python .claude/hooks/session_start.py",
        "description": "載入 FSM-STATE、reconcile CI-EVENT、顯示狀態摘要"
      }
    ]
  }
}
```

**行為**：
1. 讀取 `build/reports/fsm/FSM-STATE-{project}.yaml`
2. Glob `build/reports/fsm/CI-EVENT-*.yaml`，過濾 `processed: false`
3. 對每個 event 套用 `fsm_update_rules`
4. 標記 processed
5. 若 `cumulative_history.total_scg_retries_all_time > 10` → 注入提醒至 conversation
6. 顯示當前 FSM 狀態給 Claude（取代 Claude 自行推測）

---

#### ACT-012：Context Ledger（實測 Token）

**目標**：取代預估表，用實測資料判斷 compaction 時機。

**新增 Hook**：
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": {"tool": "Read|Write|Edit"},
        "command": "python .claude/hooks/context_ledger_pre.py"
      }
    ],
    "PostToolUse": [
      {
        "command": "python .claude/hooks/context_ledger_post.py"
      }
    ]
  }
}
```

**輸出**：`build/reports/fsm/CONTEXT-LEDGER-{date}.yaml`，每個動作一行，累計統計。

**告警注入**：當估算累計 > 85%，UserPromptSubmit Hook 自動附加：
```
⚠️ Context 預估使用 88%（實測 175K tokens），建議執行 /stage-compaction
```

---

#### ACT-013：TFA Auto-Dispatch

**目標**：test-failure-analyzer 分類結果直接觸發下一步動作，消除人工中介。

**擴充 test-failure-analyzer SKILL**：
```yaml
auto_dispatch_rules:
  classification_A:  # 實作錯誤
    action: "觸發 dev-senior Agent 修正"
    input: "TFA 報告 + 失敗 test 路徑 + 對應 AC"
    max_attempts: 3
  classification_B:  # AC 模糊
    action: "自動進入 SPEC_AUDIT（FSM 轉換）"
    trigger_slv: ["SLV-002", "SLV-005"]
  classification_C:  # 測試前置條件
    action: "觸發 qa-tester 檢視 Test Contract"
  classification_D:  # 環境
    action: "標記 flaky，重跑 3 次取多數結果"
```

**Orchestrator**：新增 `agent/specialized/sdd-orchestrator-zh.yaml` 作為總指揮 Agent，負責讀 TFA 報告、呼叫對應 subagent。

---

#### ACT-014：SPEC_REGRESSION_CHECK Gate

**目標**：SPEC_FROZEN 前強制驗證「修正非表面 patch」。

**新增 gatekeep 狀態**（放在 HUMAN_PENDING 與 SPEC_FROZEN 之間）：
```yaml
SPEC_REGRESSION_CHECK:
  triggered_if: "retry_count > 0"  # 只在有重試歷史時觸發
  action:
    - "取得本 Stage 歷次 retry 的 failure_reason"
    - "重跑對應 SLV 規則"
    - "若仍有相同分類的失敗 → 回退 HUMAN_PENDING 並標記『修正不完整』"
    - "若通過 → 正式進入 SPEC_FROZEN"
  on_regression_detected:
    increment: "cumulative_history.superficial_fix_count"
    if superficial_fix_count > 2:
      action: "ESCALATION（人工多次表面修正，需深度審查）"
```

---

#### ACT-015：Failure Pattern Library（初版）

**目標**：把各專案遇到的「未被 SLV 捕獲的錯誤模式」集中成可查詢的知識庫。

**結構**：
```
AISDLC_SDD_v0.01/
└── knowledge/
    └── failure-patterns/
        ├── FPL-INDEX.md
        ├── FPL-001-temporal-inconsistency.md
        ├── FPL-002-cache-eviction-assumption.md
        └── templates/
            └── FAILURE-PATTERN-TEMPLATE.md
```

**每個 Pattern 內容**：
```markdown
# FPL-001：時序語義矛盾

## 摘要
AC 描述「第 N+1 次操作必須比第 N 次快 X%」類型，物理可行但無穩態保證。

## 偵測時機
目前 SLV-001~006 無法捕獲。建議在 SLV-007（時序不變量檢查）中補強。

## 歷史案例
- 專案 X（2026-04）：AC-015-1 導致 PR_REVIEW 重試 6 次後 ESCALATION

## 建議 SLV 規則
```yaml
slv_007_rule:
  pattern: "AC 包含「第 N+1 次 vs 第 N 次」比較語句"
  required_qualifier:
    - "明確的穩態條件（如『快取命中時』『連線保持期間』）"
    - "明確的 degradation bound（如『快取失效後回退至 X ms 上限』）"
```

## 修正範本
「使用者的連續操作在相同 session + 相同輸入條件下，第二次起 P95 < 50ms
 （未命中快取時回退至 P95 < 200ms）」
```

**使用方式**：
- `/spec-logical-validator` 執行時，若發現可疑模式，查 FPL 給出建議
- Phase E 的 SLV Rule Generator 從 FPL 自動生成新 SLV 規則

---

#### ACT-016：Scenario FSM Variants

**目標**：為 Brownfield / Refactoring / Migration / Integration 等場景定義 FSM 子圖。

**新增文件**：
```
workflow/sdd-fsm-engine/
├── SDD_FSM_ENGINE.md              # 主 FSM（Greenfield 為基）
├── variants/
│   ├── FSM_BROWNFIELD.md           # + CODE_ANALYSIS / AS_IS_SRD / GAP_ANALYSIS
│   ├── FSM_REFACTORING.md          # + INVARIANT_EXTRACTION / BEFORE_SNAPSHOT / AFTER_VALIDATION
│   ├── FSM_MIGRATION.md            # + CURRENT_INVENTORY / CUTOVER / ROLLBACK_READY
│   ├── FSM_INTEGRATION.md          # + CONSUMER_CONTRACT_DRAFT / PROVIDER_AGREEMENT
│   ├── FSM_SECURITY.md             # + STRIDE_MODEL / PEN_TEST_READY
│   └── FSM_PERFORMANCE.md          # + BASELINE_CAPTURE / PBS_GATE
```

每個 variant 僅描述「額外狀態 + 額外轉換 + 額外 retry budget」，不重複主 FSM。

---

#### ACT-017：IMPLEMENTATION 子 FSM

**目標**：展開 IMPLEMENTATION 黑盒。

**子狀態定義**（放在 `FSM_IMPLEMENTATION_SUB.md`）：
```
IMPLEMENTATION（主 FSM）
    ├── CODE_GENERATING       # 首次由 subagent 產生代碼
    ├── COMPILE_LOOP          # 編譯 → 失敗 → 修正
    │   └── retry_budget: max_consecutive_fail = 3
    ├── UNIT_TEST             # 執行單元測試
    │   └── on_fail → AUTO_DIAGNOSIS
    ├── AUTO_DIAGNOSIS        # 呼叫 test-failure-analyzer
    │   └── branch by classification
    ├── AUTO_FIX_ATTEMPT      # 針對分類 A 自動修復
    │   └── retry_budget: max_attempts = 3
    ├── INTEGRATION_TEST      # 整合測試
    │   └── on_fail → AUTO_DIAGNOSIS（二次路由）
    └── READY_FOR_PR          # 進 PR_REVIEW
```

總 IMPLEMENTATION 預算（已定義）：20 次總迭代、3 連續編譯失敗、5 未修 Spec 測試失敗。

---

#### ACT-019：Resume Verification Gate

**目標**：Session 恢復時，強制重驗原因並檢查修正。

**新增 state**：RESUME_VERIFICATION（放在 session_resume 之後、實際恢復之前）

**邏輯**：
```yaml
resume_verification:
  action:
    step_1: "讀取 CONTEXT-SNAPSHOT-{date}.md 取得 abort_reason"
    step_2: "針對 abort_reason 類型重跑對應驗證"
    step_3: "比對此次結果與上次失敗原因"
    step_4:
      - if same_failure_pattern: 
          "警告人工：修正未生效，請勿確認恢復"
          transition: HUMAN_PENDING（重新等待）
      - if different_or_resolved:
          transition: resume_point_state
          reset current_count
          preserve cumulative_history
```

---

## 陸、Phase D 里程碑與驗收標準

### 6.1 Milestone 時程

| Milestone | 時程 | 交付 | 驗收 |
|-----------|------|------|------|
| M1：FSM Runtime 雛形 | Week 1 | ACT-010 + 單元測試 | `python fsm_runtime.py` 可模擬 FSM 定義中所有路徑 |
| M2：Hooks 整合 | Week 2 | ACT-011 + ACT-012 | 新對話自動顯示 FSM 狀態；Context Ledger 寫入 YAML |
| M3：TFA Auto-Dispatch | Week 3 | ACT-013 + sdd-orchestrator agent | 模擬測試失敗 → 自動派遣修復 Agent |
| M4：防濫用 & 場景 FSM | Week 4 | ACT-014 + ACT-016 + ACT-019 | SPEC_REGRESSION_CHECK 能識別表面修正；Brownfield FSM 獨立運作 |
| M5：實際場景驗收 | Week 4 | 整合測試 | 執行一個真實 Greenfield + 一個 Brownfield 專案，記錄 token 消耗 vs Phase B 的改進比例 |

### 6.2 Phase D 總體驗收（L4.3 → L4.7）

- [ ] 極端案例 B（變體 B — SLV-005 邊緣）token 消耗 < 5K
- [ ] 極端案例 C（變體 C — 時序語義）token 消耗 < 10K（靠 FPL-001 規則在 SCG-0 即捕獲）
- [ ] Test→Fix 自動閉環：單個代碼錯誤（分類 A），不需人工介入即可完成修復
- [ ] 跨 Session 恢復：上次中止原因未解決時，Resume Gate 能阻止盲目繼續
- [ ] FSM-STATE.yaml 與 FSM_ENGINE.md 保持同步（自動測試驗證）
- [ ] Context Ledger 誤差 < 10%（vs Claude 真實回報的餘量）

---

## 柒、對現有文件的非侵入性修改

遵循 Phase A/B 原則：**新增優先於修改**，避免破壞已發布的 v0.01 契約。

### 7.1 新增文件（不修改現有）

```
AISDLC_SDD_v0.01/
├── tools/fsm_runtime/               ⭐ 新
│   ├── fsm_runtime.py
│   ├── state_loader.py
│   └── ...
├── .claude/hooks/                   ⭐ 新
│   ├── session_start.py
│   ├── context_ledger_pre.py
│   ├── context_ledger_post.py
│   └── fsm_check_state.py
├── workflow/sdd-fsm-engine/variants/ ⭐ 新（ACT-016）
│   ├── FSM_BROWNFIELD.md
│   ├── FSM_REFACTORING.md
│   └── ...
├── workflow/sdd-fsm-engine/
│   └── FSM_IMPLEMENTATION_SUB.md    ⭐ 新（ACT-017）
├── knowledge/failure-patterns/      ⭐ 新（ACT-015）
│   ├── FPL-INDEX.md
│   └── FPL-001-temporal-inconsistency.md
├── agent/specialized/
│   └── sdd-orchestrator-zh.yaml     ⭐ 新（ACT-013）
```

### 7.2 需最小幅度增強的既有文件

| 文件 | 增強點 | 大小 |
|------|-------|------|
| `.claude/skills/test-failure-analyzer/SKILL.md` | 加 auto_dispatch_rules 章節 | +30 行 |
| `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` | 加 SPEC_REGRESSION_CHECK 狀態定義（ACT-014）+ RESUME_VERIFICATION（ACT-019） | +50 行 |
| `AISDLC_SDD_INIT.md` | 加 Layer 1 Runtime 說明段落 + Hooks 提示 | +20 行 |
| `CLAUDE.md` | Rule 9 擴充：新增「Hooks 強制執行」段落 | +15 行 |
| `.claude/settings.json` or `settings.local.json` | 註冊 Phase D 新增 Hooks | 新建或擴充 |

### 7.3 禁止修改

- `SDD_FSM_ENGINE.md` 的狀態定義表（保持向後相容，只加新狀態）
- `SDD_CICD_BASE_LAYER.md` 既有 Step 定義
- `AISDLC_SDD_INIT.md` 的 `auto_load_config` schema

---

## 捌、風險與紅隊演練

### 8.1 Phase D 自身風險

| 風險 | 影響 | 紓緩 |
|------|-----|------|
| Hooks 執行失敗導致 Claude 無法啟動 | 🔴 致命 | 每個 Hook 內建 try/except + 靜默失敗 + 警告 |
| FSM Runtime 與 FSM_ENGINE.md 不同步 | 🟡 中 | CI 加入 sync_test（比對兩者） |
| Context Ledger 預估誤差過大 | 🟡 中 | 初期採保守係數（4 chars/token），加驗證回饋循環 |
| TFA 自動派遣誤判 → AI 亂改程式碼 | 🔴 高 | 分類 A 自動修正但限 3 次、每次產 diff 報告待人工審核 |
| sdd-orchestrator 失控派遣 subagent 消耗 token | 🔴 高 | Orchestrator 自身受 implementation_budget 約束 |
| FPL 規則被錯誤 generalize | 🟡 中 | Phase D 的 FPL 全部人工 curate，Phase E 的 auto-gen 需人工 review |

### 8.2 對「Phase D 新增 Hooks 本身」的紅隊審查

**紅隊問題 1**：若 Hook 阻塞 Write 工具，但規則誤判，人工如何覆寫？
**答**：所有 Hook 支援 `SDD_BYPASS=1` 環境變數 + session 內 `/fsm-bypass` slash command。Bypass 事件寫入 FSM-STATE 的 audit_log。

**紅隊問題 2**：Hook 如何避免遞迴呼叫？
**答**：fsm_runtime.py 用 lock file 防止同時執行；Hook 執行超時 5 秒自動放行（fail-open）。

**紅隊問題 3**：若 FSM-STATE.yaml 被手動破壞（格式錯誤）？
**答**：Loader 採用嚴格驗證 + 自動備份（.bak）+ 可從上次 SPEC_FROZEN 重建。

---

## 玖、圖靈完備性最終評估

### 9.1 評分（0~10）

| 維度 | Automation_01 前 | Automation_01/02 後（現況） | Phase D 完成後 |
|------|------------------|-------------------------|--------------|
| 狀態機完備性 | 3 | 8（形式化但文件層） | 10（Runtime） |
| 有界停機 | 2 | 8（retry + ESCALATION） | 9（+ Resume Gate） |
| 上下文管理 | 3 | 7（預估制） | 9（實測 + Adaptive） |
| Spec 邏輯驗證 | 2 | 7（SLV-001~006） | 8.5（+ FPL + SLV-007 雛形） |
| Test→Fix 閉環 | 1 | 4（TFA 建議者） | 8（Auto-Dispatch） |
| 場景覆蓋 | 2 | 4（只 Greenfield） | 8（全 10 場景 FSM） |
| 學習能力 | 0 | 1（手動累計） | 4（FPL 人工 curate） |
| 生產回饋 | 0 | 1（定義未實作） | 2（Phase E 再補） |
| **圖靈完備性總分** | **2/10** | **6.5/10** | **8.3/10** |

### 9.2 Phase D 完成後仍不具備 Level 5 的關鍵差距

1. **SLV Rule Generator 未建** → FPL 擴充仍靠人工
2. **Production Feedback 未啟動** → 交付後閉環斷開
3. **Cross-Project Learning 未建** → 每個專案重新繳學費

這三項屬 Phase E，預估再 6~8 週。

---

## 拾、即刻可啟動的 Quick Win（本週）

若時間有限，以下 3 個 ACT 可在 1 週內先行落地，已能顯著改善現狀：

### QW-1：ACT-014 SPEC_REGRESSION_CHECK（純文件）
只需更新 SDD_FSM_ENGINE.md 加入 state 定義 + SDD_SPEC_FIRST_GATE.md 加入對應步驟。
**工時**：半天。**效果**：立即緩解 RC-15 的策略性重置問題。

### QW-2：ACT-015 FPL 初版（僅建立 FPL-001）
建立 knowledge/failure-patterns/ 目錄 + FPL-INDEX.md + FPL-001。
**工時**：半天。**效果**：為 Phase E 的學習層奠基，同時對當前專案有提示作用。

### QW-3：ACT-019 Resume Verification（純文件）
更新 AISDLC_SDD_INIT.md 的 session_resume 流程，加入 Step 3.5（驗證根因修正）。
**工時**：半天。**效果**：修補 RC-20 的恢復盲點。

三項合計約 1.5 天工時，所有產出為文件，零程式碼風險，對現況有實質補強。

---

## 拾壹、決策建議

**短期（本週）**：先完成 QW-1 + QW-2 + QW-3，提升當前框架的 RC 兜底能力。

**中期（Phase D, 3~4 週）**：啟動 ACT-010~012（FSM Runtime + Hooks + Context Ledger），
這是從 L4.3 → L4.7 的關鍵。此階段完成後，框架才真正具備「機器強制執行」的能力。

**長期（Phase E, 6~8 週）**：ACT-018~022 實現 Learning Layer 與 Production Feedback，
達成 Level 5 自治開發流程。

**最核心的單一改動**：若只能做一件事，選 **ACT-010（FSM Runtime）**。
它是所有其他 ACT 的執行基礎——沒有 Runtime，其他文件再完美也只是描述。

---

## 拾貳、與使用者確認清單

在啟動 Phase D 之前，請使用者確認以下幾點：

- [ ] **作用域**：Phase D 範圍以本藍圖 ACT-010~017 + ACT-019 為準，不含 Production Feedback（ACT-018）
- [ ] **風險承受**：接受「Hooks 有可能阻塞 Claude 工具呼叫」的風險（已設計 bypass 機制）
- [ ] **實作方式**：採用 Python 實作 fsm_runtime（與 .claude/hooks 一致），可接受？
- [ ] **排程**：建議先做 QW-1~3（本週），再評估是否投入 Phase D 全量（3~4 週）
- [ ] **驗收場景**：選擇一個真實 Greenfield 小專案作為 Phase D 整合驗收對象（建議對象？）

---

**文件建立者**: Chief AI Automation Architect（Claude Opus 4.7 視角）
**檢視基礎**: AISDLC-SDD v0.01（Phase A+B 完成 + Automation_02 ACT-001~007 已部分落地）
**下一動作**: 等候使用者確認作用域與風險承受後，啟動 QW-1~3 或 Phase D M1
**相關文件**:
- Phase A/B 基礎：`build/planning/archive/SDD_improving_Automation_01.md`
- Phase C 源頭：`build/planning/archive/SDD_improving_Automation_02.md`
- 執行規格：`workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`、`.claude/skills/test-failure-analyzer/SKILL.md`、`AISDLC_SDD_INIT.md`
