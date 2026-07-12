# SD_10 PG-track Next-Action — 補完三層 goal_task_id 接線（DEF-101-051）

> **狀態**：**✅ 已落地（2026-07-12 · nightly 追查輪 + 四方審查閉環）**。使用者拍板 orphan-run 政策 **(c)＝CHECK 加判別欄**；pg-contract 已由 `continue-on-error` 轉**硬閘**。DEF-101-051 帳本 = fixed。
> **方向定案（已執行）**：**補完三層功能**（run 應有 goal_task_id 為正確設計意圖）；**非**放寬約束（見「已否決」）。
> **落地摘要**：alembic 0017 加 `run_kind` 判別欄、CHECK 改 `run_kind<>'three_tier' OR goal_task_id IS NOT NULL`（無時間依賴，消除時間炸彈）；ORM 補欄；`_ensure_run_id` + 5 條 checkpoint 落地路徑接通 goal_task_id；契約測試對齊 + 硬閘。四方審查（DBA/Dev/QA/Architect）→全修→複審。
> **衍生 follow-up**（見文末）：DEF-101-053（schema_lock QueuePool loop bug + 假綠）、DEF-101-054（playbook_versions 平行時間炸彈）。

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

## SD_10 Work Items（補完功能）— 完成度

1. ✅ **ORM 補欄**：`PlaybookRun` 加 `goal_task_id`（UUID nullable，對齊 0010 FK；不宣告 ORM FK，goal_tasks 非本模組 ORM 模型）+ `run_kind`（`_pg_models.py`）。
2. ✅/🟡 **端到端接線**：`_ensure_run_id` 依 `cp.goal_task_id` 標 `run_kind='three_tier'` + 寫入該欄；5 條 checkpoint 落地路徑（`_builder`/`_token_halt`/`_interrupt`/`_evolution`/`auto_resume`）帶 `task.goal_task_id`。**已通**：離線工具（`three_tier_to_playbook.flatten_project` / `migrate_yaml_to_db`）以**真實 goal_tasks UUID** 產生之三層 playbook 端到端可標 three_tier。**guard**：`_ensure_run_id` 對非 UUID goal_task_id（如 fixture `sample_goal_tasks.yaml` 的 `GT-001-A`）以 `try/except ValueError` 退回 standalone + warn——稽核標記瑕疵不弄垮 checkpoint 續跑韌性（避免 db_only/both 崩、消除與 yaml_only 的 LSP 分歧）。**🟡 已知 gap（2026-07-12 部分收口）**：`GoalDecomposer.decompose()` 已加 optional `goal_task_id` passthrough → 攤平至每個 `PlaybookTask.goal_task_id`（見文末 follow-up）。惟 GoalDecomposer 無 runtime 呼叫者且不自造 UUID，端到端仍待 `OrchestrationCoordinator` 接入並傳入 goal_task UUID——屬另一 runtime 接線工項。
3. ✅ **orphan-run 政策**：**使用者拍板 (c)**——加 `run_kind` 判別欄，CHECK 改「僅 three_tier run 需 goal」；standalone（plain playbook）合法無 goal。alembic **0017** 落地。
4. ✅ **兩套關聯機制 canonical 定案**：`playbook_runs.goal_task_id`（UUID FK→goal_tasks）＝**run 的擁有 goal**（首個 checkpoint 之 goal，best-effort audit 標記，1:1）；`goal_progress` ledger（`goal_task_id` **TEXT**，合成 `GT-{digest}` 形式）＝**per-goal 進度事件流**（N:M append-only）。二者職責不同、非冗餘；⚠️ 兩軌 key 型別不同（UUID vs TEXT），未來若需 join 須先對齊型別。本輪以程式 + 文件定調，不強制物理合併（PG 未上線、無真實 dual-write）。
5. ✅ **契約測試對齊**：`test_pg_state_repository_contract::test_three_tier_run_marks_run_kind` 走真實 `save_checkpoint`（seed 真實 projects→goal_tasks，非 fake — Rule 9）；`test_alembic_0010` T8/T10/T10b/T10c 更新至 0017 語意（含 `match=` 綁 constraint 名）；`test_checkpoint_builder_goal_task` 直測 builder threading 3 case。
6. ✅ **收尾＝轉硬閘**：移除 `autoclaude-ci.yml` pg-contract `continue-on-error`（CI 模擬 13P/1S 綠）。
7. ✅ **cutoff 時間炸彈消除**：0017 新 CHECK 無時間依賴（改 run_kind 判別），**runs 時間炸彈根除**，不再需綁真實 cutover 日。⚠️ `playbook_versions` 平行時間炸彈未處理 → DEF-101-054。

## Follow-up（本輪衍生，SD_10 PG-track）

### ✅ 已結案（2026-07-12 · 四方審查閉環）

- **DEF-101-053**（P2）→ **fixed**：`test_pg_existing_schema_lock.py` CRUD fixture 加 `poolclass=NullPool`（比照 R56 姊妹檔）；另把 4 支 CRUD 的 `pytest.raises(Exception)` 收緊為 `match=` 綁定 **DB 實際 constraint 名**（`playbook_runs_status_check`／`knowledge_entries_outcome_check`／`idx_ck_run_id`），使假綠轉「真測對的原因」。真 pg17 實跑 4/4 CRUD 真綠。**QA 審查揪出** `EXPECTED_CHECK_CONSTRAINT_NAMES` 為死常數（定義但無 assertion 消費）→ 補 parametrized `test_check_constraint_names_match_baseline`，使 4 個判別欄 CHECK（run_kind/three_tier + version_kind/project_scoped）於離線 DDL snapshot 真正上鎖（Rule 9）。
- **DEF-101-054**（P1）→ **fixed**：比照 runs (c) 政策，alembic **0018** 為 `playbook_versions` 加 `version_kind`∈{standalone,project_scoped} 判別欄，CHECK 由時間 cutoff 改 `version_kind<>'project_scoped' OR project_id IS NOT NULL`（無時間依賴→消除 versions 時間炸彈）；`PlaybookVersion` ORM 補 `project_id`（0010 已建 DB 欄、此前 ORM 未映射）+ `version_kind` + 2 CHECK；`.py`/`.sql` 雙路徑。真 pg17：upgrade→head、downgrade 0018→0017 可逆（舊 CHECK 還原 NOT VALID＝陷阱防護）。契約測試 T9→0018 + T13/T13b/T13c。三方審查（DBA/QA/Architect）全 PASS 無 P0/P1/P2。
  - **🔴 DBA production 前置註記**：`_persist` 現不攜 project 脈絡 → PG 落地版本恆 standalone、時間炸彈已消除，故 dormant 前提下無虞。**但上 production 前**應確認 dormancy：`SELECT count(*) FROM playbook_versions WHERE project_id IS NOT NULL`；若非零（既有 project-scoped 列被 0018 預設標 standalone＝語意失真，CHECK 仍過無資料損毀），應評估補 `UPDATE playbook_versions SET version_kind='project_scoped' WHERE project_id IS NOT NULL`。與 runs 端 0017 同類「判別欄由應用層前向設定」之刻意設計。

### 🟡 續辦（本輪部分收口 / 新衍生）

- **#2 runtime gap（部分收口）**：`GoalDecomposer.decompose()` 已加 optional `goal_task_id` passthrough → 攤平至每個 `PlaybookTask.goal_task_id`（對齊離線工具路徑，消除「動態分解 task 恆遺失 goal_task_id」）。**界線（誠實揭露）**：GoalDecomposer 目前**無任何 runtime 呼叫者**（`.decompose()` 在 autoclaude/ 內零呼叫），且不自造 UUID（strategy tier 零 infra 契約）。**真正端到端**仍待呼叫端 `OrchestrationCoordinator` 接入 decompose 並持久化 goal_task 後傳入其 UUID——屬另一 runtime 接線工項（非本輪 scope）。
- **DEF-101-055**（P3，新衍生）：ORM `CheckConstraint(name=...)`（`ck_playbook_runs_status`/`ck_kb_outcome`）與 DB 實際名（`playbook_runs_status_check`/`knowledge_entries_outcome_check`，0001 inline CHECK 之 PG 預設名）分歧；因 schema 由 alembic 建置，此二 ORM name 對 DB 從未實現＝裝飾性。已文件化，CRUD 測試改綁 DB 實際名。未來若需對齊另開 rename migration（cosmetic，PG 未上線無急迫）。
- **goal FK robustness（P3，四方審查殘餘）**：guard 已消除「非 UUID goal」崩潰；但「合法 UUID 格式但不存在於 goal_tasks」仍走 guard 外的 FK `IntegrityError` → save 失敗（fail-loud，屬真正參照完整性錯誤，較可辯護）。PG 未上線、canonical fixture 主要撞擊面已消除，故留註記。

## 已否決方向（存證，防後續 session 回頭提）

- **放寬 / drop 約束**：使用者定案「run 應有 goal_task_id 為正確設計意圖」，放寬等於放棄三層追蹤能力，故否決。約束保留，改為**補完應用層**使其可被滿足。

## 追蹤

- 帳本：DEF-101-051（open，SD_10 PG-track）
- SD_10 尚無 `SD_Improving_10.md`（`SD_Improving_09.md:30` 僅預告 W6 末建大綱）；本檔為 SD_10 PG-track 具體種子項，開 track 時併入 backlog 並依 G0~G6 展開。
