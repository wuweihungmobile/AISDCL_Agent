# SDD Context Snapshot (Auto-Generated at 90%)

**建立時間**: 2026-04-21T15:49:17+00:00
**觸發原因**: auto_90_percent（Token ratio = 92.00%, cumulative = 184000）
**產生者**: context_ledger_post.py hook（非 Claude 主動產出）

---

## 當前 FSM 狀態

- **current_state**: `AUTO_COMPACT_PENDING`
- **resume_state**（compact 完成後回到）: `SPEC_DRAFTING`
- **project**: greenfield-autocompact
- **session_id**: 8c334ddb-eb3f-4cf0-9e11-b7ea9ebc7279

## 已完成 Stage（凍結）

| Stage | 凍結時間 | Compaction 報告 |
|-------|---------|----------------|
| (無) | — | — |

## 當前 Retry 計數

- SCG_VALIDATION: 0
- PR_REVIEW: 0
- RTM_VERIFY: 0

## 累積歷史

- total_scg_retries_all_time: 0
- total_spec_frozen_count: 0
- escalation_count: 0

## Pending CI Events

  - (無)

## 最近 20 筆 Decision Trace（ACT-025）

| ts | from | to | trigger | reason | spec_refs |
|----|------|----|---------|--------|-----------|
| (無) | — | — | — | — |

---

## 恢復指引

### 情境 A：同 session 內恢復（Auto-Compact 成功）

1. Claude 會自動看到 `additionalContext` 指示
2. 立即呼叫 Skill: `stage-compaction`
3. Skill 完成後，FSMRuntime.complete_auto_compact() 自動執行：
   - 歸零當日 CONTEXT-LEDGER cumulative_tokens
   - FSM 轉回 `SPEC_DRAFTING`
4. 繼續原工作

### 情境 B：跨 session 恢復（Auto-Compact 失敗 / session 中止）

1. 新 conversation 讀取 `AISDLC_SDD_INIT.md`
2. 偵測到本 snapshot 存在，進入 `session_resume` 流程
3. 讀取此 Snapshot + 最新 Stage Summary
4. 轉入 `RESUME_VERIFICATION` 閘，人工確認後從 `SPEC_DRAFTING` 繼續

---

**相關文件**：
- `workflow/sdd-context-governor/SDD_CONTEXT_GOVERNOR.md` — Auto-Compact Protocol
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` — AUTO_COMPACT_PENDING state
- `AISDLC_SDD_INIT.md` — session_resume 流程
