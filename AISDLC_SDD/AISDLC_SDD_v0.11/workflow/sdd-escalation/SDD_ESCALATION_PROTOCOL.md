# SDD 退場與升級機制規格
# SDD Escalation & Graceful Exit Protocol

**版本**: v1.0
**建立日期**: 2026-04-18
**文件類型**: 工作流程規格
**所屬分類**: workflow/sdd-escalation/
**對應藍圖**: build/planning/active/SDD_improving_Automation_01.md（Phase A）

---

## 🎯 目的

定義 SDD Agentic 閉環在遭遇**無法自動解決的障礙**時，如何：
1. 優雅停止（不浪費 Token）
2. 產出結構化報告（讓人工快速接手）
3. 記錄可恢復點（讓下一個 conversation 繼續）

---

## 🚨 ESCALATION 觸發條件

| 觸發來源 | 條件 | 嚴重程度 |
|---------|------|---------|
| SCG_VALIDATION 重試耗盡 | retry_count ≥ 3 次仍 FAIL | 🔴 HIGH |
| PR_REVIEW 重試耗盡 | retry_count ≥ 5 次仍 FAIL | 🔴 HIGH |
| PR_REVIEW 異常模式 + SPEC_AUDIT 確認矛盾 | 相同失敗模式 × 3 + 邏輯矛盾確認 | 🔴 HIGH |
| RTM_VERIFY 重試耗盡 | retry_count ≥ 2 次仍 FAIL | 🟡 MEDIUM |
| HUMAN_PENDING 長期無回應 | 逾時 168 小時 | 🟡 MEDIUM |
| Token Budget 嚴重不足 | 使用量 > 95% | 🔴 CRITICAL |
| Spec 邏輯矛盾確認 | SLV 驗證器偵測到不可解矛盾 | 🔴 HIGH |

---

## 📋 ESCALATION 執行流程

```
觸發條件成立
     │
     ▼
Step 1: 立即停止當前工作
     │
     ▼
Step 2: 產出 Abort Report（見模板）
     │  - 問題描述與根本原因
     │  - 已嘗試的解決方案
     │  - 可恢復點（哪個 SPEC_FROZEN 狀態）
     │  - 建議的人工行動
     ▼
Step 3: 識別通知對象
     │  - SCG 規格問題 → sa-analyst / sd-architect
     │  - 實作一致性問題 → tech-lead / dev-senior
     │  - 邏輯矛盾 → sa-analyst（重新審查 FRD）
     │  - Token 不足 → 任意負責人（新 conversation 接手）
     ▼
Step 4: 進入 ESCALATION 阻塞狀態（不可自動退出）
     │
     ▼
Step 5: 等待人工決策
     ├── 選項 A：Human 決定中止 → TERMINATED
     └── 選項 B：Human 修復問題並指示恢復 → 回到可恢復點
```

---

## 📂 Abort Report 產出規格

產出位置：`build/reports/abort/ABORT-{date}-{reason}.md`

使用模板：[SDD_ABORT_REPORT_TEMPLATE.md](../../docs_template/sdd/build/SDD_ABORT_REPORT_TEMPLATE.md)

---

## 🔄 恢復點策略

ESCALATION 解除後，依照下表選擇恢復點：

| 問題類型 | 恢復點 | 說明 |
|---------|--------|------|
| SCG 規格格式錯誤 | SPEC_DRAFTING（當前 Stage） | 修正後重新撰寫規格 |
| Spec 邏輯矛盾 | SPEC_DRAFTING（問題 Stage） | 重新審查並修正 AC |
| Test Contract 與 AC 不同步 | SPEC_DRAFTING（Stage 5） | 更新 Test Contract |
| 實作與規格不一致 | IMPLEMENTATION | 依規格重新實作 |
| RTM 覆蓋不足 | RTM_VERIFY | 補充測試案例 |
| Token 不足 | 最近的 SPEC_FROZEN | 新 conversation，從 Summary 讀取 |

---

## 🛑 TERMINATED 執行動作

```yaml
terminated_actions:
  1_final_report:
    action: "產出最終 Abort Report"
    path: "build/reports/abort/ABORT-FINAL-{date}.md"
    
  2_context_snapshot:
    action: "產出 Context Snapshot"
    content:
      - "FSM 當前狀態"
      - "已完成的 Stage 清單"
      - "未完成的工作項目"
      - "所有已凍結的規格文件路徑"
      - "retry_count 歷史"
      - "建議的下一步行動"
    path: "build/reports/abort/CONTEXT-SNAPSHOT-{date}.md"
    
  3_recovery_guide:
    action: "產出恢復指引"
    content: |
      下一個 conversation 如何從此點繼續：
      1. 讀取 AISDLC_SDD_INIT.md
      2. 執行 AISDLC_SDD_INIT.md 中的「Session 恢復流程（ESCALATION / Token 耗盡後接力）」章節（session_resume）
      3. 讀取 build/reports/abort/CONTEXT-SNAPSHOT-{date}.md 取得 FSM 狀態與恢復點
      4. 從 {RESUME_POINT}（SPEC_FROZEN 或對應狀態）繼續執行
    path: "build/reports/abort/RECOVERY-GUIDE-{date}.md"
```

---

## ⏰ HUMAN_PENDING 逾時管理

```yaml
human_pending_timeout:
  reminder_at_72h:
    action: "發送提醒通知"
    message: |
      🔴 [SDD 人工確認待辦]
      閘門：{SCG-N}
      等待時間：72 小時
      文件：{doc_path}
      請確認後在 conversation 中回覆「通過」或「需修改：{原因}」
    severity: REMINDER
    
  escalation_at_168h:
    action: "升級為 ESCALATION"
    message: |
      🚨 [SDD 嚴重：人工確認嚴重逾時]
      閘門：{SCG-N}
      等待時間：168 小時（7天）
      影響：Agentic 流程已停滯
      建議行動：指派新的審查者或決定放棄此 Sprint
    severity: CRITICAL
```

---

## 📊 Token Budget 緊急處理

```yaml
token_budget_emergency:
  at_95_percent:
    action: "立即停止所有工作"
    steps:
      1: "記錄當前 FSM 狀態"
      2: "列出未完成的工作項目"
      3: "確認所有已完成文件已寫入 docs/"
      4: "產出 Context Snapshot"
      5: "進入 ESCALATION"
    message: |
      ⚠️ [SDD Context Snapshot — 接力指引]
      
      當前狀態：{FSM_STATE}
      已完成：{completed_stages}
      未完成：{pending_items}
      
      下一步：請在新 conversation 中執行：
      1. 讀取 AISDLC_SDD_INIT.md
      2. 讀取 build/reports/abort/CONTEXT-SNAPSHOT-{date}.md
      3. 從 {RESUME_POINT} 繼續
```

---

## 🔗 相關文件

- [AISDLC_SDD_INIT.md](../../AISDLC_SDD_INIT.md) — **Session 恢復流程（session_resume）入口**
- [SDD_FSM_ENGINE.md](../sdd-fsm-engine/SDD_FSM_ENGINE.md) — 狀態機定義
- [SDD_CONTEXT_GOVERNOR.md](../sdd-context-governor/SDD_CONTEXT_GOVERNOR.md) — 上下文管理
- [SDD_ABORT_REPORT_TEMPLATE.md](../../docs_template/sdd/build/SDD_ABORT_REPORT_TEMPLATE.md) — 中止報告模板
- [spec-logical-validator SKILL](../../.claude/skills/spec-logical-validator/SKILL.md) — 邏輯矛盾偵測
