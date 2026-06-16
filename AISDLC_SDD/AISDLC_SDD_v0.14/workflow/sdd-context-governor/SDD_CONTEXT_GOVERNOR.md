# SDD 上下文預算管理規格
# SDD Context Window Governor

**版本**: v1.0
**建立日期**: 2026-04-18
**文件類型**: 工作流程規格
**所屬分類**: workflow/sdd-context-governor/
**對應藍圖**: build/planning/active/SDD_improving_Automation_01.md（Phase B）

---

## 🎯 目的

在長週期 SDD 任務（如 Greenfield Stage 0~11）中，**主動監控並管理 LLM Context Window 使用量**，
防止上下文污染導致後期 Agent 決策品質下降，並在預算耗盡前優雅地觸發接力機制。

---

## 📊 預算閾值定義

```yaml
context_budget:
  model_reference: "claude-sonnet-4-6（200K token window）"
  
  thresholds:
    green:
      range: "0% ~ 69%"
      status: "正常運作"
      action: "無需干預"
      
    warn:
      at: 70%
      status: "⚠️ 警告"
      action:
        - "開始對已凍結 Stage 的詳細規格使用摘要替代"
        - "移除已完成 Stage 的完整文件內容，保留 ID 清單與摘要"
        - "輔助文件（ADR、過往 RTM 版本）改為按需讀取"
      
    compress:
      at: 85%
      status: "🟡 強制壓縮"
      action:
        - "執行 stage-compaction Skill"
        - "確認所有文件已持久化至 docs/ 目錄"
        - "上下文只保留：當前 Stage Summary + Active Spec + RTM ID List"
        - "清除所有 SCG 失敗記錄的詳細內容"

    auto_compact:
      at: 90%
      status: "🟠 自動接管（Auto-Compact Protocol）"
      action:
        - "Hook 自動產出 Pre-Emptive Context Snapshot（build/reports/abort/CONTEXT-SNAPSHOT-{date}-auto.md）"
        - "FSM 進入 AUTO_COMPACT_PENDING 狀態"
        - "PreToolUse Hook 僅允許 Skill(stage-compaction) / Read(docs, reports) / Write(snapshot) 通過，其餘 deny"
        - "以 additionalContext 強制指示 Claude 下一步必須呼叫 /stage-compaction"
        - "Compaction 完成後，FSM 自動轉回原 state，清除 ledger cumulative（保留檔案歷史）繼續執行"
      rationale: |
        - 95% 才產出 Snapshot 可能來不及（最後一次 Read/Write 可能超標）
        - 90% 提前主動持久化狀態，即使 Claude 無法繼續，下次可透過 session_resume 恢復
        - 90% 自動觸發 compact 後若成功即可繼續，避免每次都進入 ESCALATION 需人工介入

    hard_stop:
      at: 95%
      status: "🔴 緊急停止"
      action:
        - "立即暫停所有工作"
        - "產出 Context Snapshot（見下方格式）"
        - "進入 ESCALATION（見 SDD_ESCALATION_PROTOCOL.md）"
```

### 閾值遷移對照

| 閾值 | 行為變更 | 可恢復性 |
|------|---------|---------|
| 70% | warn（不變） | ✅ |
| 85% | warn + 建議執行 /stage-compaction（不變） | ✅ |
| **90%**（新增） | **自動 Snapshot + 強制 Auto-Compact + 成功後繼續** | ✅ 同 session 或下次 session |
| 95% | TOKEN_BUDGET_CRITICAL → ESCALATION（不變，作為最後防線） | 🟡 需人工介入 |

---

## 🧹 Stage 間強制 Context Compaction

**觸發時機**：每次通過 🔴 Human Checkpoint（SPEC_FROZEN milestone）後自動執行

### 執行步驟

```yaml
stage_compaction_protocol:
  step_1_persist:
    name: "文件持久化確認"
    action: "確認所有當前 Stage 文件已寫入 docs/ 目錄"
    verify:
      - "docs/ 中存在對應 Stage 的所有文件"
      - "文件狀態為 Approved / Frozen"
    
  step_2_summarize:
    name: "產出 Stage Summary"
    target_tokens: "~2000 tokens"
    format: |
      # Stage {N} Summary — {Stage Name}
      **狀態**: FROZEN
      **日期**: {YYYY-MM-DD}
      
      ## 完成文件
      - {文件路徑} — {一行摘要}
      
      ## 關鍵決策
      - ADR-{NNN}: {決策摘要一行}
      
      ## RTM 狀態
      - EPIC: N個 | Feature: N個 | US: N個 | AC: N個
      - AT 覆蓋率: XX%
      - 未覆蓋項目: {列出 ID}
      
      ## API Contract 狀態
      - 凍結端點: N個
      - 待凍結端點: N個
      
      ## 下一 Stage 起點
      - 前置條件: {列出}
      - 首要任務: {描述}
      
      ## 已知風險
      - {如有}
    
  step_3_clear:
    name: "清除冗余上下文"
    retain:
      - "當前 Stage Summary（~2K tokens）"
      - "RTM ID 清單（不含詳細 AC/AT 內容）"
      - "Active ADR 編號與狀態清單"
      - "API 端點清單（不含 Schema 詳細）"
      - "當前活躍的 Agent 配置"
    remove:
      - "完整 PRD / FRD 文字內容"
      - "C4 圖詳細描述文字"
      - "完整 OpenAPI Schema"
      - "過往所有 SCG 失敗記錄"
      - "已完成 Stage 的完整文件內容"
      - "對話歷史中的重複資訊"
    
  step_4_verify:
    name: "驗證後續可用性"
    checks:
      - "確認下一 Stage 所需資訊可從 docs/ 按需讀取"
      - "確認 Stage Summary 包含足夠的接力資訊"
```

---

## 🔁 Auto-Compact Protocol（90% 自動接管）

```yaml
auto_compact_flow:
  trigger:
    source: ".claude/hooks/context_ledger_post.py"
    condition: "cumulative_ratio ≥ 0.90 且 < 0.95"
    idempotent: true  # 已進入 AUTO_COMPACT_PENDING 不重複觸發

  step_1_snapshot:
    actor: "post hook（無需 Claude 參與）"
    action: "呼叫 FSMRuntime.save_auto_snapshot() 寫入 CONTEXT-SNAPSHOT-{date}-auto.md"
    guarantee: "即使後續失敗，此 Snapshot 已持久化 → 下次 session_resume 可讀取"

  step_2_fsm_transition:
    actor: "post hook"
    action: "FSMRuntime.trigger_auto_compact() → 將 fsm.current_state 轉為 AUTO_COMPACT_PENDING"
    persist: "FSM-STATE-*.yaml 記錄 auto_compact_triggered_at + resume_state"

  step_3_force_claude:
    actor: "post hook 的 additionalContext"
    message: |
      [SDD-CTX][AUTO-COMPACT] context ratio ≥ 90%。
      已自動產出 Context Snapshot。FSM: AUTO_COMPACT_PENDING。
      下一步必須立即呼叫 Skill: stage-compaction。
      其餘工具呼叫將被 PreToolUse 阻擋。

  step_4_gated_execution:
    actor: "pre hook（下次工具呼叫時）"
    rule: |
      if fsm.state == AUTO_COMPACT_PENDING:
        allow: Skill(stage-compaction), Read(docs/, build/reports/), Write(CONTEXT-SNAPSHOT*)
        deny: all others

  step_5_resume:
    actor: "stage-compaction Skill（Step 5 必執行 Bash）"
    cli_command: |
      cd AISDLC_SDD_v0.01 && python -m tools.fsm_runtime.fsm_runtime complete-auto-compact
    action:
      - "FSMRuntime.complete_auto_compact() → 轉回 auto_compact_state.resume_state"
      - "_reset_today_ledger() → 當日 CONTEXT-LEDGER-*.yaml.cumulative_tokens 歸零（entries 保留 + 寫入 phase=compact-reset 稽核紀錄）"
      - "繼續原工作（resumed_to 即下一個應進入的狀態）"
    expected_output: |
      {"resumed_to": "<resume_state>", "ledger": {"reset": true, "path": "...", "previous_cumulative": <n>}}
    noop_case: |
      若回傳 {"noop": true, ...}，表示 FSM 不在 AUTO_COMPACT_PENDING（一般 SPEC_FROZEN 觸發），Step 5 跳過。
```

> **注意**：Hook 無法主動執行 Skill，因此 `step_3` 透過 `additionalContext` 強指示 + `step_4` 透過 deny 阻斷其他操作，實務上達到「半自動」效果。Claude 看到指示後會立即呼叫 `/stage-compaction`。
>
> **🔴 閉環收尾必須**：stage-compaction Skill 的 Step 5 透過 Bash 執行 CLI `complete-auto-compact`。若省略此步驟，FSM 會永遠卡在 AUTO_COMPACT_PENDING 且 Ledger 不歸零，下次 PreToolUse 仍 ≥ 90% → 進入無限觸發迴圈。e2e 測試 `test_s10_auto_compact_full_loop_resets_ledger_and_resumes` 守護此閉環。

---

## 📸 Context Snapshot 格式

**用途**：Token 耗盡時（> 95%）或系統終止時，供下一個 conversation 接手
**90% 自動版**：Hook 在 90% 時自動產出 `CONTEXT-SNAPSHOT-{date}-auto.md`（標示 `trigger: auto_90_percent`）

```markdown
# SDD Context Snapshot
**建立時間**: {YYYY-MM-DD HH:MM}
**觸發原因**: {Token 耗盡 / 系統中止 / 人工要求}

## 當前 FSM 狀態
- **狀態**: {FSM State Name}
- **Stage**: {N — Stage Name}
- **專案情境**: {greenfield/brownfield/...}

## 已完成 Stage
| Stage | 狀態 | 關鍵文件路徑 |
|-------|------|------------|
| Stage 0 | ✅ FROZEN | docs/... |
| Stage 1 | ✅ FROZEN | docs/... |
| Stage 2 | 🔄 進行中 | — |

## 未完成工作
- [ ] {待完成項目 1}
- [ ] {待完成項目 2}

## 所有凍結文件
- docs/01_requirements/FRD-{system}.md
- docs/02_architecture/SRD-{system}.md
- docs/02_architecture/adr/ （N 個 ADR）
- docs/03_testing/RTM-{system}.md

## Retry 狀態
- SCG_VALIDATION retry_count: {N}
- PR_REVIEW retry_count: {N}

## 恢復指引
1. 在新 conversation 中讀取 AISDLC_SDD_INIT.md
2. 讀取此 Snapshot 文件
3. 讀取最後一個 Stage Summary
4. 從 {RESUME_STATE} 繼續執行
```

---

## 🔍 Incremental Review 策略

**核心原則**：只讀取 DIFF，不重讀全文

```yaml
incremental_review:
  pr_review:
    bad:  "每次 PR Review 都重新讀取完整 SRD + FRD + API Spec"
    good: "讀取 PR 變更的端點清單，針對性查詢對應 AC 和 Contract 段落"
    
  scg_validation:
    bad:  "每次 SCG 驗證都載入所有 51 個模板"
    good: "只載入對應當前 Stage 的模板，用 ID 查詢追溯鏈"
    
  rtm_update:
    bad:  "每次 RTM 更新都讀取完整 FRD"
    good: "只讀取變更的 US/AC ID，更新對應 RTM 行"
```

---

## 📏 各 Stage 預估 Token 消耗

| Stage | 預估 Token | 累計 | 剩餘% |
|-------|------------|------|------|
| Stage 0（INIT + 框架） | ~5K | ~5K | 97.5% |
| Stage 1（PRD） | ~15K | ~20K | 90% |
| Stage 2（FRD + RTM） | ~30K | ~50K | 75% ⚠️ |
| Stage 3（SRD + C4 + ADRs） | ~40K | ~90K | 55% |
| **Compaction 後** | -60K | ~30K | 85% → 15K 後 ✅ |
| Stage 4（API Contract） | ~20K | ~50K | 75% ⚠️ |
| Stage 5（Test Contract） | ~25K | ~75K | 62.5% |
| **Compaction 後** | -50K | ~25K | 87.5% → 12.5% 後 ✅ |
| Stage 6（Security） | ~20K | ~45K | 77.5% |
| Stage 7~11（Implementation） | 按需讀取 | 動態管理 | — |

> **關鍵洞察**：在 Stage 2 結束（PRD + FRD + RTM 寫入後）和 Stage 5 結束（所有規格凍結後），
> 各執行一次 Compaction，可將 Context 從 ~90K 壓縮至 ~15K，騰出充足空間給實作階段。

---

## 🔗 相關文件

- [SDD_FSM_ENGINE.md](../sdd-fsm-engine/SDD_FSM_ENGINE.md) — SPEC_FROZEN 觸發 Compaction
- [SDD_ESCALATION_PROTOCOL.md](../sdd-escalation/SDD_ESCALATION_PROTOCOL.md) — 95% 時進入 ESCALATION
- [stage-compaction SKILL](../../.claude/skills/stage-compaction/SKILL.md) — Compaction 執行 Skill
