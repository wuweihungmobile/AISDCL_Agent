# SDD Agentic 閉環自動化改進藍圖 v1.0
# Turing-Complete Closed-Loop Verification for AISDLC-SDD

**文件編號**: SDD_improving_Automation_01
**建立日期**: 2026-04-18
**分析對象**: AISDLC-SDD v0.01 整體自動化閉環能力
**角色視角**: Chief AI Automation Architect（Karpathy 風格）
**狀態**: ✅ 已歸檔（Phase A+B 驗證完成 2026-04-19 / Phase C 待實際場景驗收）

---

## 執行摘要

AISDLC-SDD v0.01 具備清晰的規格先行哲學與完整的文件骨架，但**尚未達到圖靈完備的自動化閉環**。
核心缺口集中在三處：（1）狀態機缺乏形式化定義與退場邊界；（2）長任務中無上下文衰減管理機制；
（3）在「邏輯不可解」場景下，系統會陷入無限重試而非優雅中斷。
本文件提供具體修復路徑，將現有框架升級至 Level 5 自治開發流程。

---

## 一、現況診斷：隱性狀態機的漏洞圖譜

### 1.1 已識別的隱性狀態

目前框架透過 Workflow Steps 描述流程，但**非形式化 FSM（Finite State Machine）**。
識別出的 11 個隱性狀態如下：

```
S0:  INIT              → 讀取 AISDLC_SDD_INIT.md
S1:  SCENARIO_DETECT   → 識別情境類型（greenfield / brownfield / ...）
S2:  AGENT_LOAD        → 載入 Primary Agents
S3:  SPEC_DRAFTING     → 規格撰寫工作狀態
S4:  SCG_VALIDATION    → Spec Compliance Gate 自動驗證（🔷）
S5:  HUMAN_PENDING     → 等待人工確認（🔴 阻塞狀態）
S6:  SPEC_FROZEN       → 規格凍結里程碑
S7:  IMPLEMENTATION    → 開發實作工作狀態
S8:  PR_REVIEW         → SCG-4 實作一致性驗證
S9:  RTM_VERIFY        → SCG-5 需求追溯完整性
S10: RELEASE_READY     → SCG-6 發布就緒
```

**關鍵缺口：三個「不存在」的狀態**

| 缺失狀態 | 後果 |
|---------|------|
| `ERROR`（含 retry_count） | 失敗無上界，無限重試耗盡 Token |
| `ESCALATION`（強制人工介入） | 系統無法自主判斷「我解不了這個問題」 |
| `TERMINATED`（優雅中止） | 無法產出 Abort Report，無法讓下一個 Agent 接手 |

---

### 1.2 狀態轉換嚴密性評估

**已有轉換（正向路徑）**：

```
INIT → SCENARIO_DETECT → AGENT_LOAD → SPEC_DRAFTING
SPEC_DRAFTING → SCG_VALIDATION
SCG_VALIDATION [PASS] → HUMAN_PENDING → SPEC_FROZEN
SPEC_FROZEN → IMPLEMENTATION → PR_REVIEW → RTM_VERIFY → RELEASE_READY
```

**缺失轉換（負向路徑）**：

```
SCG_VALIDATION [FAIL] → ???
  現況：「修正後重新執行」（無限迴圈，無上界）
  應有：→ SPEC_DRAFTING（retry_count++）
          if retry_count > 3: → ESCALATION

PR_REVIEW [FAIL N 次] → ???
  現況：→ 修正 → PR_REVIEW（無限）
  應有：if same_failure_pattern > 3: → SPEC_AUDIT
          if SPEC_AUDIT.confirms_contradiction: → ESCALATION

HUMAN_PENDING [timeout > 72h] → ???
  現況：永遠懸掛
  應有：→ REMINDER_NOTIFICATION（第一次）
          if timeout > 168h: → ESCALATION（降級為 P0 事項）

TOKEN_BUDGET_EXCEEDED → ???
  現況：不存在此檢查
  應有：→ IMMEDIATE_ESCALATION（附帶 context_summary）
```

---

## 二、上下文污染與衰減：量化分析

### 2.1 Greenfield 場景 Token 累積估算

```
Stage 0 (INIT):                ~  5,000 tokens
Stage 1 (PRD):                 ~ 15,000 tokens
Stage 2 (FRD + RTM 初版):      ~ 30,000 tokens  ← 追溯鏈龐大
Stage 3 (SRD + C4 + 3 ADRs):   ~ 40,000 tokens
Stage 4 (OpenAPI Contract):     ~ 20,000 tokens（每模組）
Stage 5 (Test Contract + RTM):  ~ 25,000 tokens
Stage 6 (STRIDE + SAD):         ~ 20,000 tokens
SCG 失敗的錯誤訊息積累：        ~  5,000 tokens
Human 修改意見歷史：            ~  5,000 tokens
────────────────────────────────────────────
Stage 6 結束時累計：            ~165,000 tokens

→ 超過 claude-sonnet-4-6 的 200K 上下文視窗的 82.5%
→ 實作階段（Stage 7-11）幾乎無有效餘量
```

### 2.2 現有框架缺失的清理機制

| 問題 | 現況 | 影響 |
|------|------|------|
| Stage 間無 Context Compaction | 舊規格殘留上下文 | 後期 Agent 決策受早期噪音干擾 |
| 失敗記錄積累 | 每次 SCG 失敗都留在 context | 污染後續推理 |
| 按需載入只管「載入」不管「卸載」 | Agent YAML 載入後永遠存在 | 記憶體浪費 |
| 無 Context Budget 監控 | 不知道剩餘容量 | 無預警耗盡 |

---

## 三、停機問題驗證：極端案例模擬

### 3.1 案例：「Spec 寫錯導致測試永遠無法通過」

**初始條件**：SA 在 FRD 中將 AC-003-1 定義為「系統必須在 0ms 內完成登入驗證」

**流程追蹤**：

```
[S4] SCG-1 Validation → ✅ PASS
     原因：格式正確、有 US 追溯、AC 可量化
     漏洞：spec_compliance_check 只驗證「格式完整性」，不驗證「物理可行性」

[S5] 🔴 Human Review → ✅ PASS
     原因：人工審查者認為「0ms 只是佔位符，之後會填實際數值」
     漏洞：未填寫的數值通過了凍結，文件顯示為「已確認」

[S4] SCG-3 API Contract Gate → ✅ PASS
     原因：Response Schema 完整，x-aisdlc 欄位存在

[S5] Test Contract Spec 寫入：
     expect(loginResponseTime_ms).toBeLessThan(0)  ← 物理不可能

[S7] Stage 8：開發實作

[S8] SCG-4 PR Review #1 → ❌ FAIL（測試失敗：time=25ms > 0ms）
[S7] Dev 優化：快取 + 連接池
[S8] SCG-4 PR Review #2 → ❌ FAIL（time=8ms > 0ms）
[S7] Dev 繼續優化：移除所有 I/O
[S8] SCG-4 PR Review #3 → ❌ FAIL（time=2ms > 0ms）
[S7] Dev 開始懷疑環境問題...
[S8] SCG-4 PR Review #4 → ❌ FAIL
...

→ 無限迴圈，直到 Token 耗盡
→ 系統無法識別「這是 Spec 問題，不是代碼問題」
→ 無任何自動退場機制
```

**現行防護評估**：
- 🔴 Human Checkpoint 只在 Stage 3-6，實作迴圈中無定期介入點 → ❌
- 無 max_retry 機制 → ❌
- 無異常模式偵測（連續相同失敗） → ❌
- 無 Token 預算監控 → ❌
- **結論：系統在此案例下無法優雅中斷，必然浪費大量 Token**

---

## 四、Agentic 閉環狀態機設計（改進方案）

### 4.1 形式化 FSM 定義

```yaml
# SDD Formal State Machine v1.0
fsm:
  name: "SDD_Agentic_Loop"
  
  states:
    INIT:
      type: initial
      timeout: none
      
    SCENARIO_DETECT:
      type: transitional
      timeout: none
      
    AGENT_LOAD:
      type: transitional
      timeout: none
      
    SPEC_DRAFTING:
      type: workstate
      max_iterations: 3          # 每個 SCG 週期最多 3 次草稿
      timeout: none
      
    SCG_VALIDATION:
      type: gatekeep
      retry_limit: 3             # 🆕 最多重試 3 次
      on_retry_exceeded: ESCALATION
      
    HUMAN_PENDING:
      type: blocking
      timeout_hours: 72          # 🆕 72小時後觸發提醒
      escalation_hours: 168      # 🆕 168小時後升級
      on_timeout: REMINDER
      on_escalation: ESCALATION
      
    SPEC_FROZEN:
      type: milestone
      action: CONTEXT_COMPACTION  # 🆕 凍結時強制壓縮上下文
      
    IMPLEMENTATION:
      type: workstate
      context_checkpoint: true   # 🆕 每次 commit 前驗證上下文完整性
      
    PR_REVIEW:
      type: gatekeep
      retry_limit: 5             # 🆕 最多重試 5 次
      pattern_detection: true    # 🆕 相同失敗模式偵測
      on_same_pattern_3x: SPEC_AUDIT
      on_retry_exceeded: ESCALATION
      
    SPEC_AUDIT:                  # 🆕 新狀態：規格邏輯審查
      type: diagnostic
      action: "重新讀取原始 AC，對比 Test Contract，執行 Logical Consistency Check"
      on_contradiction_confirmed: ESCALATION
      on_no_contradiction: PR_REVIEW  # 回到正常流程
      
    RTM_VERIFY:
      type: gatekeep
      retry_limit: 2
      on_retry_exceeded: ESCALATION
      
    RELEASE_READY:
      type: milestone
      
    ESCALATION:                  # 🆕 新狀態：強制人工介入
      type: blocking
      notification:
        - channel: "Human-in-Loop"
        - content: "Abort Report with reason + context_summary"
      cannot_auto_exit: true     # 必須人工解除
      
    REMINDER:                    # 🆕 新狀態：提醒但不阻塞
      type: notification
      auto_return_to: HUMAN_PENDING
      
    TERMINATED:                  # 🆕 新狀態：優雅中止
      type: terminal
      action: "產出 Abort Report，存至 build/reports/abort/"
      
    RELEASE:
      type: terminal

  transitions:
    # 正向路徑（Happy Path）
    - from: INIT → SCENARIO_DETECT
    - from: SCENARIO_DETECT → AGENT_LOAD
    - from: AGENT_LOAD → SPEC_DRAFTING
    - from: SPEC_DRAFTING → SCG_VALIDATION
    - from: SCG_VALIDATION [PASS] → HUMAN_PENDING
    - from: HUMAN_PENDING [approved] → SPEC_FROZEN
    - from: SPEC_FROZEN → IMPLEMENTATION
    - from: IMPLEMENTATION → PR_REVIEW
    - from: PR_REVIEW [PASS] → RTM_VERIFY
    - from: RTM_VERIFY [PASS] → RELEASE_READY → RELEASE
    
    # 錯誤路徑（Error Paths）🆕
    - from: SCG_VALIDATION [FAIL, retry_count < 3] → SPEC_DRAFTING (retry_count++)
    - from: SCG_VALIDATION [FAIL, retry_count >= 3] → ESCALATION
    - from: PR_REVIEW [FAIL, same_pattern_3x] → SPEC_AUDIT
    - from: PR_REVIEW [FAIL, retry_count >= 5] → ESCALATION
    - from: SPEC_AUDIT [contradiction] → ESCALATION
    - from: SPEC_AUDIT [no_contradiction] → PR_REVIEW (retry_count=0)
    - from: HUMAN_PENDING [timeout_72h] → REMINDER → HUMAN_PENDING
    - from: HUMAN_PENDING [timeout_168h] → ESCALATION
    - from: ANY_STATE [token_budget > 95%] → IMMEDIATE_ESCALATION
    - from: ESCALATION [human_abort] → TERMINATED
    - from: ESCALATION [human_fix_and_resume] → 回到對應狀態
```

### 4.2 狀態圖（ASCII）

```
                    ┌─────────────────────────────────────┐
                    │         TOKEN BUDGET MONITOR        │
                    │  70%: warn  85%: compress  95%: STOP │
                    └──────────────────┬──────────────────┘
                                       │ 95% → ESCALATION
                                       ↓
INIT → SCENARIO → AGENT_LOAD → SPEC_DRAFTING ←─────────────────┐
                                    │                           │
                               SCG_VALIDATION                   │
                               /        \                       │
                          [PASS]     [FAIL×<3]─────────────────►┘
                            │              \
                            │           [FAIL×≥3]
                            │                ↓
                            │           ESCALATION ←──────────────┐
                            ↓          /         \                 │
                      HUMAN_PENDING  [abort]  [fix+resume]         │
                      /     |    \     ↓          ↓                │
               [approved] [72h] [168h] TERMINATED  (resume state)  │
                  ↓      [remind][escalate]                        │
             SPEC_FROZEN ─────────────────────────────────────     │
             (CONTEXT_COMPACTION HERE)                             │
                  ↓                                                │
            IMPLEMENTATION                                         │
                  ↓                                                │
              PR_REVIEW                                            │
             /    |     \                                          │
        [PASS] [FAIL×<5] [same_pattern×3]                         │
           ↓      ↓           ↓                                    │
      RTM_VERIFY  │      SPEC_AUDIT                               │
           ↓      │      /        \                                │
     RELEASE_READY│  [no_contra] [contradiction]                   │
           ↓      │       ↓            ↓                           │
        RELEASE   └──►PR_REVIEW   ESCALATION ────────────────────►┘
```

---

## 五、上下文與記憶體管理策略

### 5.1 Context Budget Protocol

```yaml
context_budget_protocol:
  name: "SDD Context Window Governor"
  
  monitoring:
    check_frequency: "每次工具呼叫後"
    metric: "estimated_token_count / max_context_window"
  
  thresholds:
    warn:
      at: 70%
      action:
        - "開始對輔助文件（ADR、舊版 RTM）使用摘要替代"
        - "移除已凍結 Stage 的詳細規格，保留摘要 + ID 清單"
    
    compress:
      at: 85%
      action:
        - "執行 Stage Summary Compaction"
        - "所有完整文件確認已持久化至 docs/ 目錄"
        - "上下文只保留：當前 Stage Summary + Active Spec + RTM ID List"
    
    hard_stop:
      at: 95%
      action:
        - "立即暫停所有工作"
        - "產出 Context Snapshot（目前狀態、下一步、未完成項目）"
        - "進入 IMMEDIATE_ESCALATION"
        - "通知：'Token budget 不足，需要新 conversation 接力'"
```

### 5.2 Stage 間強制 Context Compaction

**在每個 🔴 Human Checkpoint 通過後執行：**

```yaml
stage_compaction:
  trigger: "SPEC_FROZEN milestone"
  
  steps:
    1_persist:
      action: "確認所有文件已寫入 docs/ 目錄（不在上下文中）"
      
    2_summarize:
      action: "產出 Stage Summary（~2K tokens）"
      format: |
        # Stage N Summary
        - **狀態**: FROZEN
        - **完成文件**: [列出檔案路徑]
        - **關鍵決策**: [ADR 編號 + 一行摘要]
        - **RTM 覆蓋率**: XX%（AC: N個，AT: N個）
        - **下一 Stage 起點**: [關鍵前置條件]
        - **已知風險**: [如有]
      
    3_clear:
      action: "從工作記憶中移除詳細規格內容，只保留 Summary"
      retain:
        - "當前 Stage Summary"
        - "RTM ID 清單（不含詳細內容）"
        - "Active ADR 編號清單"
        - "API Contract 端點清單（不含 Schema 詳細）"
      remove:
        - "完整 PRD / FRD 文字"
        - "C4 圖詳細描述"
        - "完整 OpenAPI Schema"
        - "過往 SCG 失敗記錄"
        
    4_verify:
      action: "確認後續 Stage 所需資訊可從 docs/ 目錄按需讀取"
```

### 5.3 Incremental Spec Review 策略

**避免每次重新讀取所有文件：**

```yaml
incremental_review:
  principle: "只讀取 DIFF，不讀取全文"
  
  pr_review_protocol:
    bad:  "讀取完整 SRD + FRD + API Spec 來驗證 PR"
    good: "讀取 PR 變更的 API 端點列表，針對性查詢對應 AC 和 Contract"
    
  scg_validation_protocol:
    bad:  "每次驗證都載入所有 51 個模板"
    good: "只載入對應當前 Stage 的模板，用 ID 查詢追溯鏈"
```

---

## 六、Spec Logical Consistency Checker（新增 SCG 前置驗證）

### 6.1 設計原理

現行 `spec_compliance_check` 只驗證「格式/完整性」，不驗證「邏輯一致性」。
需要在 SCG-0（需求凍結）和 SCG-3（Contract Freeze）前增加邏輯驗證層。

### 6.2 驗證規則集

```yaml
spec_logical_validator:
  name: "SDD Spec Logic Consistency Checker"
  run_at: ["SCG-0 前", "SCG-3 前", "SPEC_AUDIT 觸發時"]
  
  checks:
    - id: "SLV-001"
      name: "NFR Physical Feasibility"
      rule: "所有效能指標必須 > 0（如 response_time_ms > 0）"
      error: "NFR 包含物理不可能的數值"
      
    - id: "SLV-002"
      name: "AC Testability"
      rule: "每個 AC 必須包含明確的 Pass/Fail 判定條件（可量化或可觀察）"
      error: "AC 描述模糊，無法翻譯為自動化測試"
      example_bad: "系統應該很快地回應"
      example_good: "系統回應時間 P95 < 200ms"
      
    - id: "SLV-003"
      name: "Business Invariant Non-Contradiction"
      rule: "Business Invariants 清單中，任意兩個 INV 不得互相矛盾"
      error: "INV-XXX 與 INV-YYY 存在邏輯衝突"
      detection: "對每對 INV 執行相容性推理"
      
    - id: "SLV-004"
      name: "API Contract vs FRD Compatibility"
      rule: "API Response Schema 的欄位與 FRD Business Rules 相容"
      error: "API 回傳欄位與業務規則不一致"
      
    - id: "SLV-005"
      name: "Test Contract Reachability"
      rule: "每個 Test Contract 中的 assertion 必須在現有架構下可達"
      error: "Test assertion 需要系統目前不具備的能力"
      
    - id: "SLV-006"
      name: "Dependency Cycle Detection"
      rule: "API 端點之間的呼叫關係不得存在循環依賴"
      error: "API-XXX → API-YYY → API-XXX 循環依賴"

  output:
    on_pass: "SLV-PASS: 所有邏輯一致性檢查通過"
    on_fail:
      - "SLV-REPORT-{date}.md（列出所有失敗項）"
      - "SCG Gate 阻塞（不得進入人工審查）"
      - "分配給對應 Agent 修復（sa-analyst for SLV-001~003）"
```

---

## 七、Level 5 自治開發流程終極優化藍圖

### 7.1 自治等級定義

```
Level 1: 純人工開發（無 AI）
Level 2: AI 輔助（GitHub Copilot）
Level 3: AI 自動完成單一任務（ChatGPT + 人工貼上）
Level 4: 現況 AISDLC-SDD v0.01（AI 驅動 workflow，人工確認閘門）
Level 5: 完全閉環自動化，AI 自主偵測問題並決策是否需要人工介入
```

### 7.2 Level 5 架構（三層設計）

```
┌─────────────────────────────────────────────────────────┐
│                  Layer 3: Oversight Layer                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Token Budget │  │ Retry Budget│  │ Pattern Detector│  │
│  │   Monitor   │  │   Manager  │  │  (Anomaly Detect)│  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         └─────────────────┼──────────────────┘          │
│                     ESCALATION ENGINE                    │
└─────────────────────────────┬───────────────────────────┘
                              │ ESCALATION signals
┌─────────────────────────────▼───────────────────────────┐
│                   Layer 2: Execution Layer               │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Formal FSM Engine                   │   │
│  │   INIT → SPEC → SCG → HUMAN → FROZEN → IMPL → PR│   │
│  │                  ↕ (via Layer 3)                 │   │
│  │   ESCALATION ← ERROR ← RETRY_EXCEEDED            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Spec Logical│  │  Context    │  │   Stage Summary  │  │
│  │  Validator  │  │  Governor   │  │   Compactor     │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────┐
│                   Layer 1: Content Layer                 │
│   SDD Documents │ SCG Gates │ Agents │ Skills │ CI/CD   │
│   （現有 AISDLC-SDD v0.01 框架內容）                    │
└─────────────────────────────────────────────────────────┘
```

### 7.3 新增框架元件清單

| 元件 | 說明 | 實作方式 | 優先級 |
|------|------|---------|------|
| `SDD_FSM_ENGINE.md` | 形式化狀態機定義 | Workflow 文件 | 🔴 P0 |
| `SDD_ESCALATION_PROTOCOL.md` | 退場機制規格 | Workflow 文件 | 🔴 P0 |
| `spec-logical-validator` | Spec 邏輯一致性檢查 | 新增 Skill | 🔴 P0 |
| `SDD_CONTEXT_GOVERNOR.md` | 上下文預算管理 | Workflow 文件 | 🟡 P1 |
| `stage-compaction` | Stage 間上下文壓縮 | 新增 Skill | 🟡 P1 |
| `pattern-detector` | 異常失敗模式偵測 | Agent 能力擴充 | 🟡 P1 |
| `SDD_ABORT_REPORT_TEMPLATE.md` | 優雅中止報告模板 | 文件模板 | 🟢 P2 |
| `token-budget-monitor` | Token 預算監控 Hook | CI/CD 整合 | 🟢 P2 |

### 7.4 實作路線圖

```
Phase A（緊急修復，1-2 Sprint）
  ├── 建立 SDD_FSM_ENGINE.md（形式化狀態機文件）
  ├── 建立 SDD_ESCALATION_PROTOCOL.md（退場機制）
  └── 實作 spec-logical-validator Skill（SLV-001~003 規則）

Phase B（核心能力，2-3 Sprint）
  ├── 實作 SDD_CONTEXT_GOVERNOR.md（Context Budget Protocol）
  ├── 實作 stage-compaction Skill
  ├── 擴充 scg-gate Skill 加入 retry_count 追蹤
  └── 建立 SDD_ABORT_REPORT_TEMPLATE.md

Phase C（智能化，3-4 Sprint）
  ├── 實作 pattern-detector（異常模式識別）
  ├── 完整 SLV-004~006 邏輯驗證規則
  ├── Token Budget Monitor 整合至 CI/CD
  └── Level 5 自治流程整體測試（3 個場景驗收）
```

---

## 八、自驗極端案例：優化後的系統行為

**重新跑「Spec 寫錯導致測試永遠無法通過」案例：**

```
[SLV 前置驗證] SCG-0 前 → spec-logical-validator 執行
  SLV-001 檢查：AC-003-1 "0ms 內完成" → ❌ SLV-001 FAIL
  輸出：SLV-REPORT-20260418.md
  動作：SCG-0 被阻塞，AC-003-1 退回 sa-analyst 修正
  
  → Human 被通知：「AC-003-1 物理不可行，請提供合理數值」
  → Human 修正為 200ms
  → SLV-001 → ✅ PASS
  → 進入正常 SCG-0 流程

  → 整個後續無效工作全部消除
  → Token 浪費：約 2,000（SLV 執行）vs 原本無限迴圈
```

**若 SLV 未能偵測（邊緣案例）：**

```
假設 SLV 未偵測到一個更微妙的邏輯錯誤，進入了 PR_REVIEW 迴圈：

PR_REVIEW #1 → ❌ FAIL
PR_REVIEW #2 → ❌ FAIL（相同測試失敗）
PR_REVIEW #3 → ❌ FAIL（pattern_detection 觸發）
  → 系統偵測到：「相同測試 test_ac_003_1 連續失敗 3 次」
  → 自動進入 SPEC_AUDIT 狀態
  → SPEC_AUDIT 讀取 AC-003-1 原始定義 vs Test Contract assertion
  → 比對發現：AC 要求值（已修正為200ms）但 Test Contract 仍寫著 0ms
  → 輸出：SPEC_AUDIT_REPORT：「Test Contract 未與 AC 同步更新」
  → 分配 qa-tester 修正 Test Contract
  → 修正後 retry_count 重置 → PR_REVIEW 通過

→ 最多消耗：3次PR_REVIEW + 1次SPEC_AUDIT ≈ 可預期的有限損失
→ 未進入無限迴圈
```

**若 SPEC_AUDIT 確認規格本身矛盾（最壞情況）：**

```
SPEC_AUDIT → contradiction_confirmed
→ 進入 ESCALATION
→ 系統產出 Abort Report：
  - 問題位置：AC-003-1
  - 矛盾類型：Test Contract assertion 與 Business Invariant INV-007 衝突
  - 已消耗資源：X tokens，Y 小時
  - 建議行動：SA 重新審查 Stage 2 FRD
  - 可恢復點：SPEC_FROZEN (Stage 2)

→ 人工收到 Abort Report
→ 決定：修正 AC 並從 Stage 2 SPEC_FROZEN 繼續
→ 系統優雅恢復，無需從頭開始
```

---

## 九、對現有 AISDLC-SDD v0.01 的具體修改建議

### 9.1 需要新增的文件（不修改現有文件）

```
AISDLC_SDD_v0.01/
├── workflow/
│   ├── sdd-fsm-engine/
│   │   └── SDD_FSM_ENGINE.md          ← 形式化狀態機
│   └── sdd-escalation/
│       └── SDD_ESCALATION_PROTOCOL.md  ← 退場機制
├── .claude/skills/
│   ├── spec-logical-validator/
│   │   └── SKILL.md                   ← SLV-001~006 規則
│   └── stage-compaction/
│       └── SKILL.md                   ← Context Compaction
└── docs_template/sdd/
    └── build/
        └── SDD_ABORT_REPORT_TEMPLATE.md  ← 中止報告模板
```

### 9.2 需要增強的現有元件

| 元件 | 現況 | 增強點 |
|------|------|-------|
| `sdd-gate/SKILL.md` | 只做 Pass/Fail 判斷 | 加入 retry_count 追蹤、pattern_detection 觸發 |
| `SDD_SPEC_FIRST_GATE.md` | 線性流程 | 加入 FSM 狀態引用、retry_limit 定義 |
| `SDD_CICD_BASE_LAYER.md` | 文件格式驗證 | 加入 token_budget_check step |
| `AISDLC_SDD_INIT.md` | 無狀態恢復機制 | 加入 session_resume 流程（從上次 SPEC_FROZEN 繼續） |

### 9.3 CLAUDE.md 需要新增的規則

```markdown
## 🔴 Rule 9：自動化閉環防護規則（新增）

| 情境 | 規則 |
|------|------|
| SCG 驗證失敗 3 次 | 停止重試，標記為 ESCALATION，等待人工介入 |
| 相同測試失敗 3 次 | 觸發 SPEC_AUDIT，禁止繼續提交代碼 |
| Token 使用 > 85% | 強制執行 Stage Compaction，再繼續 |
| Token 使用 > 95% | 立即停止，產出 Context Snapshot，請求新 conversation |
| Spec 邏輯矛盾確認 | 進入 ESCALATION，產出 Abort Report，禁止繼續開發 |
```

---

## 十、結論：圖靈完備性評估

| 能力維度 | 現況 AISDLC-SDD v0.01 | 改進後（含本文建議）|
|---------|---------------------|-----------------|
| 狀態機完備性 | ⭐⭐（隱性，無邊界） | ⭐⭐⭐⭐⭐（形式化 FSM） |
| 錯誤恢復能力 | ⭐（無 retry limit） | ⭐⭐⭐⭐（retry budget + SPEC_AUDIT） |
| 停機防護 | ⭐（無退場機制） | ⭐⭐⭐⭐⭐（ESCALATION + TERMINATED） |
| 上下文管理 | ⭐⭐（按需載入，無清理） | ⭐⭐⭐⭐（Context Governor + Compaction） |
| Spec 邏輯驗證 | ⭐（格式/完整性） | ⭐⭐⭐⭐（SLV 邏輯一致性 + 物理可行性） |
| 自治等級 | Level 4 | Level 5 目標（Phase C 完成後） |
| 圖靈完備性 | ❌ 不具備（無有界停機） | ✅ 具備（有界重試 + 確定性退場） |

**核心洞察**：圖靈完備的自動化閉環，關鍵不在於「AI 有多強」，而在於「系統知道何時停下來」。
加入有界重試、邏輯一致性驗證、與確定性退場機制後，AISDLC-SDD 可從「可能失控的 AI Workflow」
升級為「可預期、可審計、可恢復的工程系統」。

---

**文件建立者**: Chief AI Automation Architect（Claude Sonnet 4.6）
**審查者**: 待人工確認
**Phase A 完成項目**: SDD_FSM_ENGINE.md + SDD_ESCALATION_PROTOCOL.md + spec-logical-validator Skill
**Phase B 完成項目**: SDD_CONTEXT_GOVERNOR.md + stage-compaction Skill + sdd-gate 強化 + SDD_ABORT_REPORT_TEMPLATE.md + AISDLC_SDD_INIT.md session_resume + CLAUDE.md Rule 9 + SDD_SPEC_FIRST_GATE.md v1.1 + SDD_CICD_BASE_LAYER.md v1.1 + sdd-review FSM 整合
**Phase C 待執行**: Level 5 自治流程整體測試（Greenfield / Brownfield / Refactoring 3 個場景驗收）— 需人工執行實際工作流
**相關文件**: `AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md`, `SDD_SPEC_FIRST_GATE.md`, `SDD_CICD_BASE_LAYER.md`
