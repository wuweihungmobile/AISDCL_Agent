# SDD Abort Report — auto-compact-rate-limit

**建立時間**: 2026-06-05T15:12:02+00:00
**觸發原因**: auto_compact exceeded 3 per stage 'initial' — 可能引用文件過大或 stage 需拆分；拒絕再次 compact
**current_state**: `ESCALATION`
**project**: rate-limit-proj

---

## 觸發上下文
- **count_per_stage**: 4
- **max_per_stage**: 3
- **stage_key**: initial
- **cumulative_tokens**: 180000
- **ratio**: 0.91
- **suggestions**: 文件過大需拆分 / 引用策略錯 / 考慮手動深度 compaction

## 當前 Retry 計數
- SCG_VALIDATION: 0
- PR_REVIEW: 0
- RTM_VERIFY: 0

## 累積歷史
- escalation_count: 1
- total_scg_retries_all_time: 0
- total_spec_frozen_count: 0

---

## 恢復指引
1. 人工確認 abort 原因（見上）
2. 依 `AISDLC_SDD_INIT.md` §Session 恢復流程進入 `RESUME_VERIFICATION`
3. 修復規格 / 環境 / 運行條件後，呼叫 FSMRuntime 的 resume API

**相關文件**：
- `workflow/sdd-escalation/SDD_ESCALATION_PROTOCOL.md` — ESCALATION / TERMINATED
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` — FSM 狀態轉換表
