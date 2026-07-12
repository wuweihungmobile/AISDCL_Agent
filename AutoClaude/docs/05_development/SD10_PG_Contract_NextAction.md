# SD_10 PG-track Next-Action — 補完三層 goal_task_id 接線（DEF-101-051）

> **狀態**：open（SD_10 PG-track；**本輪維持非阻塞** — `autoclaude-ci.yml` pg-contract job `continue-on-error: true`，第 170 行）。
> **方向已定案**：**反向補完三層功能**（run 應有 goal_task_id 為正確設計意圖）；**非**放寬約束（見下方「已否決」）。
> **為何本輪不落地**：屬跨 plugin/DB/契約測試的真功能開發 + 需新設計 orphan-run 政策，非可草率修掉的 bug；PG production 尚未上線（ADR-SD09-001 仍 gated），零資料風險，適合排程 SD_10 正式處理。帳本 DEF-101-051 如實記 open。

## 精確根因 — 「三層 goal_task_id 是半成品功能」

schema 側齊全、應用層從未接線：

| 面向 | 現況 | 佐證 |
|------|------|------|
| Schema / 約束 | `playbook_runs.goal_task_id` FK 欄 + `ck_runs_post_cutoff_has_goal` CHECK 已建且 validated | `alembic/versions/0010_link_legacy_to_tiers.py:56-69,175-178` |
| 約束契約測試 | 明文斷言 CHECK 存在、validated、且「post-cutoff + NULL → 必 raise」 | `tests/contract/test_alembic_0010_fk_three_step.py` T8/T9/T10（:204-233） |
| **應用層填值** | **全庫零賦值** — `cp.goal_task_id` 從未被 assign；`playbook_runs.goal_task_id` 無任何寫入路徑 | `grep "goal_task_id ="` 於 `autoclaude/` 空；`_ensure_run_id` 裸 INSERT（`pg_state_repository.py:397-407`）；`PlaybookRun` ORM model 連該欄都沒定義（`_pg_models.py:42-62`） |
| ORM 缺欄 | `PlaybookRun` model 無 `goal_task_id` 屬性 → repository 就算想寫也無從寫 | `_pg_models.py:42-62` |
| 現行 run↔goal 關聯 | 走**另一張 `goal_progress` 表**（goal_task_id/playbook_id/run_id），非 `playbook_runs.goal_task_id` | `infra/adapters/pg_goal_progress_ledger.py:51` |

**後果**：cutoff（2026-05-20＝migration 撰寫日）過後，**100% 的 checkpoint save 都撞 CHECK**（非邊角）。兩支 contract test 因此**要求互斥**：`test_alembic_0010` 要求「裸 run 必須被拒」、`test_pg_state_repository_contract`（M4）要求「save_checkpoint 必須成功建裸 run」。現況 **5 passed / 7 CheckViolation / 1 skipped**。

## SD_10 Work Items（補完功能）

1. **ORM 補欄**：`PlaybookRun` model 加 `goal_task_id`（nullable，對齊 0010 FK）。
2. **端到端接線**：goal_synthesis / OrchestrationCoordinator 產出 goal_task 後，把 `goal_task_id` 一路帶進 `PlaybookCheckpoint.goal_task_id`，再由 `_ensure_run_id` 傳入 `playbook_runs` INSERT。
3. **orphan-run 政策（關鍵設計決策）**：決定 plain-playbook（無 goal 分解、`cp.goal_task_id=None`）在 db_only/both 模式 post-cutoff 的語意 —— 三選一：(a) db_only 強制三層（plain playbook 走 file backend）；(b) 為 orphan run 綁定 default/synthetic goal_task；(c) CHECK 加「僅對三層 run 生效」的判別欄。此決策定調後才動 schema。
4. **兩套關聯機制收斂**：`playbook_runs.goal_task_id` FK vs `goal_progress` ledger —— 定 canonical，避免雙軌漂移。
5. **契約測試對齊**：`test_pg_state_repository_contract` fixture 建 goal_tasks FK 列 + 設 `cp.goal_task_id`，使 run 合規（**須反映真實流程**，不得造 fake 路徑 — Rule 9）。
6. **收尾**：全 12 案綠後，移除 pg-contract job `continue-on-error: true`（`autoclaude-ci.yml:170`，檔頭第 168-169 行明訂之解除條件），pg-contract 轉硬閘。
7. **cutoff 語意複審**：現 CHECK 綁 migration 撰寫日；SD_10 應改綁**真實 PG cutover 日**（ADR-SD09-001 DBA 親簽日），消除時間炸彈。

## 已否決方向（存證，防後續 session 回頭提）

- **放寬 / drop 約束**：使用者定案「run 應有 goal_task_id 為正確設計意圖」，放寬等於放棄三層追蹤能力，故否決。約束保留，改為**補完應用層**使其可被滿足。

## 追蹤

- 帳本：DEF-101-051（open，SD_10 PG-track）
- SD_10 尚無 `SD_Improving_10.md`（`SD_Improving_09.md:30` 僅預告 W6 末建大綱）；本檔為 SD_10 PG-track 具體種子項，開 track 時併入 backlog 並依 G0~G6 展開。
