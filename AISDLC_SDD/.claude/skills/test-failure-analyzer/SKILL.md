---
name: test-failure-analyzer
description: 測試失敗 → Spec 自動映射橋接（TFA）：查詢 RTM 將失敗 test case 映射回 AC/US/FRD，分類根本原因（修程式碼 vs 修 Spec），供 sdd-orchestrator 閉環消費（Phase D ACT-004）
user-invocable: true
disable-model-invocation: false
argument-hint: "<test_id 或 failure log 路徑>"
allowed-tools:
  - Read
---

# test-failure-analyzer Skill
# 測試失敗 → Spec 自動映射橋接

**Skill ID**: `test-failure-analyzer`
**版本**: v1.0
**建立日期**: 2026-04-19
**觸發命令**: `/test-failure-analyzer`
**對應 ACT**: ACT-004（SDD_improving_Automation_02.md）
**所屬分類**: `.claude/skills/test-failure-analyzer/`

---

## 🎯 目的

當 CI/CD 測試失敗時，自動查詢 RTM 將失敗 test case 映射回對應的 AC/US/FRD，
協助 AI 判斷根本原因分類，並建議正確的修正方向（修程式碼 vs 修 Spec）。

---

## 🔗 觸發時機

| 觸發條件 | 說明 |
|---------|------|
| 單元測試失敗（Unit Test FAIL） | CI 回報失敗 test case ID |
| 整合測試失敗（Integration Test FAIL） | 跨模組測試失敗 |
| PR Review 相同模式失敗 × 2 | FSM SPEC_AUDIT 前置分析 |
| IMPLEMENTATION 測試失敗計數達上限 | FSM `test_fail_without_spec_change ≥ 5` |

---

## 📋 執行步驟

```yaml
test_failure_analyzer:
  
  input:
    required:
      - test_id: "失敗的 test case ID（格式：TC-XXX-Y-Z）"
      - failure_message: "CI 輸出的失敗訊息（assertion error / exception）"
    optional:
      - test_report_path: "JUnit XML 或 pytest JSON 報告路徑"
      - rtm_path: "RTM 文件路徑（預設：docs/03_testing/RTM-*.md）"

  process:
    step_1_rtm_lookup:
      action: "從 RTM 查詢 test_id → AC_id → US_id → F_id"
      source: "docs/03_testing/RTM-{SystemName}.md"
      output: "追溯鏈：{test_id} → {AC_id} → {US_id} → {F_id}"
      on_not_found: |
        若 RTM 中找不到 test_id：
        → 輸出警告：「RTM 缺少此 test case 追溯記錄，可能是 SpecTrace 問題」
        → 分類為 Type-D（環境/配置問題），建議先更新 RTM

    step_2_ac_retrieval:
      action: "讀取 FRD 中對應 AC 的 Given/When/Then 定義"
      source: "docs/01_requirements/FRD-{SystemName}.md"
      target: "{AC_id}"

    step_3_assertion_comparison:
      action: "比對失敗 assertion 與 AC 期望行為"
      comparison_points:
        - "測試的 When 條件是否與 AC Given/When 一致"
        - "測試斷言的期望值是否與 AC Then 描述一致"
        - "測試前置條件是否可達（SLV-005 可達性）"

    step_4_root_cause_classification:
      action: "AI 判斷根本原因分類"
      categories:
        type_A:
          label: "實作錯誤"
          description: "Spec AC 正確，程式碼實作不符合 AC 期望"
          confidence_signal: "assertion 期望值與 AC Then 一致，但程式碼輸出不同"
          recommended_action: "退回 IMPLEMENTATION，依照 AC 修正程式碼"
          fsm_impact: "不觸發 SPEC_AUDIT，繼續 IMPLEMENTATION"
          
        type_B:
          label: "AC 邏輯模糊"
          description: "AC Given/When/Then 定義不明確，導致測試無法確定正確行為"
          confidence_signal: "無法判斷期望值，AC 有多種合理解釋"
          recommended_action: "觸發 SPEC_AUDIT，重新審查 FRD[AC_id]，可能需更新 Spec"
          fsm_impact: "觸發 FSM SPEC_AUDIT（test_fail_without_spec_change++）"
          
        type_C:
          label: "測試前置條件問題"
          description: "測試本身的前置條件設定有誤（測試資料、Mock 設定等）"
          confidence_signal: "AC 邏輯正確，但 Given 條件在測試環境無法成立"
          recommended_action: "修正測試前置條件，不修改 Spec 或程式碼"
          fsm_impact: "不計入 test_fail_without_spec_change"
          
        type_D:
          label: "環境問題"
          description: "CI 環境、網路、資料庫連線等基礎設施問題"
          confidence_signal: "測試間歇性失敗，或失敗訊息包含 timeout/connection refused"
          recommended_action: "排查 CI 環境問題，不修改 Spec 或程式碼"
          fsm_impact: "不計入任何 FSM 計數器"

  output:
    report_path: "build/reports/test-analysis/TFA-{date}-{test_id}.md"
    report_content:
      - "失敗 test_id 與追溯鏈（AC_id → US_id → F_id）"
      - "AC 原始定義（Given/When/Then）"
      - "失敗 assertion 訊息"
      - "根本原因分類（A/B/C/D）與信心度（High/Medium/Low）"
      - "建議行動"
      - "FSM 影響（是否觸發 SPEC_AUDIT 或 ESCALATION）"
      - "auto_dispatch（見下方規則）"

  # ⭐ Phase D（ACT-013）新增：分類 → 自動派遣 subagent
  auto_dispatch_rules:
    enabled_by_default: true
    orchestrator: "sdd-orchestrator-zh"   # 見 agent/specialized/sdd-orchestrator-zh.yaml
    rules:
      classification_A:
        label: "實作錯誤"
        dispatch_to: "dev-senior-zh"
        input_contract:
          - "TFA 報告路徑（build/reports/test-analysis/TFA-*.md）"
          - "失敗 test case 路徑 + 期望 AC Given/When/Then"
          - "當前 FSM state（必為 IMPLEMENTATION 或其子狀態 AUTO_FIX_ATTEMPT）"
        max_attempts: 3
        fsm_on_success: "回 UNIT_TEST 重跑"
        fsm_on_exhaust: "ESCALATION，需人工介入"
        guardrail: "禁止修改 docs/01_requirements/ 與 docs/03_testing/（由 PreToolUse Hook 強制）"
      classification_B:
        label: "AC 邏輯模糊"
        dispatch_to: "sa-analyst-zh"
        pre_action:
          - "呼叫 /spec-logical-validator 重跑 SLV-002（Given/When/Then 完整性）"
          - "呼叫 /spec-logical-validator 重跑 SLV-005（前置條件可達性）"
        fsm_transition: "SPEC_AUDIT"
        input_contract:
          - "TFA 報告 + SLV 失敗細節"
          - "FRD 當前 AC 條文"
        max_attempts: 2
        fsm_on_success: "SPEC_REGRESSION_CHECK → SPEC_FROZEN"
      classification_C:
        label: "測試前置條件問題"
        dispatch_to: "qa-tester-zh"
        input_contract:
          - "TFA 報告 + Test Contract 當前版本"
        max_attempts: 2
        fsm_impact: "不累計 IMPLEMENTATION 預算"
      classification_D:
        label: "環境問題"
        action: "標記 flaky → 重跑 3 次取多數結果"
        dispatch_to: null
        rerun_policy:
          attempts: 3
          quorum: 2   # 2/3 通過即視為 PASS
        on_persistent_fail: "升級至 devops-engineer-zh 排查 CI 環境"
        fsm_impact: "不計入任何重試計數"

  dispatch_log:
    path: "build/reports/test-analysis/DISPATCH-LOG-{date}.yaml"
    schema:
      - ts
      - tfa_report
      - classification
      - dispatched_agent
      - attempt_no
      - outcome        # SUCCESS | FAIL | ESCALATED
      - fsm_state_after
```

---

## 📊 輸出報告模板

```markdown
# Test Failure Analysis Report
# 測試失敗根因分析報告

**報告 ID**: TFA-{date}-{test_id}
**建立時間**: {ISO8601}
**觸發狀態**: {IMPLEMENTATION / PR_REVIEW / SPEC_AUDIT}

## 追溯鏈
{test_id} → {AC_id} → {US_id} → {F_id}

## AC 原始定義
- **Given**: {條件}
- **When**: {操作}
- **Then**: {期望結果}

## 失敗訊息
```
{assertion error message}
```

## 根本原因分類
**分類**: Type-{A/B/C/D} — {標籤}
**信心度**: {High / Medium / Low}
**判斷依據**: {描述}

## 建議行動
{具體行動描述}

## FSM 影響
{是否更新 FSM 計數器，觸發哪個狀態轉換}
```

---

## 🔗 相關文件

- [SDD_FSM_ENGINE.md](../../../workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md) — FSM 狀態與 implementation_budget
- [spec-logical-validator SKILL](../spec-logical-validator/SKILL.md) — SLV-005 可達性驗證
- [FSM-STATE-TEMPLATE.yaml](../../../tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml) — 狀態持久化
- [SDD_improving_Automation_02.md](../../../build/planning/archive/SDD_improving_Automation_02.md) — 設計依據（已歸檔 archive/）

---

**基於**: AISDLC-SDD v0.22
