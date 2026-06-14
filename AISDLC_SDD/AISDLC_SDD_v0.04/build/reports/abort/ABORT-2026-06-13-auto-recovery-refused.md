# SDD Abort Report — auto-recovery-refused

**建立時間**: 2026-06-13T15:56:36+00:00
**觸發原因**: auto_recovery refused: Rule 9.14.3: diagnostic category=structural (sub_type=spec_conflict) is not auto-recoverable
**current_state**: `ESCALATION_FINAL`
**project**: g8-wire

---

## 觸發上下文
- **refusal_reason**: Rule 9.14.3: diagnostic category=structural (sub_type=spec_conflict) is not auto-recoverable

## 🧭 舵手交接（Steersman Handoff）

🛑 系統已**優雅停機**（已證明非無限重試，token 已保全）。

【根因分類】`spec_conflict`（structural，不可自動修復）／信心 0.85

【你是舵手，不是修碼員】系統缺的不是「再試一次」，而是：
  👉 **AI 缺「正確且自洽的規格」——目前的 AC 與 INV 相互矛盾，任何實作都無法同時滿足。**
  👉 請 **sa-analyst**：請提供修正後的 AC（解除與 INV 的矛盾），或澄清此需求的真實意圖。

【恢復路徑】補上上述環境/規格後，輸入「確認恢復」→ 進入 `RESUME_VERIFICATION`。

---

## 當前 Retry 計數
- SCG_VALIDATION: 0
- PR_REVIEW: 0
- RTM_VERIFY: 0

## 累積歷史
- escalation_count: 0
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
