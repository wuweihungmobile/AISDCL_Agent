# SD_Improving_03 Sprint Retrospective

**Sprint**：SD_Improving_03 v1.1（Phase 4 Facade 切換 + DAL 接通生產路徑）
**週期**：W0~W5（2026-05-08 ~ 2026-05-12）
**Sprint Owner**：wuweihungmobile（Tech Lead）
**FTE**：1.5（單人 + pair review）
**關閉日期**：2026-05-12

---

## 1. Sprint 成果摘要

| Week | 主要交付物 | 測試新增 | 狀態 |
|------|-----------|---------|------|
| W0a | SD_03 v1.1 文件 + KickOff | — | ✅ |
| W0b | 13 golden fixture 補建（Stage A equivalence 基礎）| 13 | ✅ |
| W0c | `check_no_internal_alias.py` + `tests/test_no_internal_alias.py` | 10 | ✅ |
| W1a | `_runner_impl` internal alias 全消除 | 10 | ✅ |
| W1b | `CheckpointManager` → `FileStateRepository` 反向委派 + DeprecationWarning | 8 | ✅ |
| W2 | `MutationApplyService` 注入 Kernel（M2）+ Plugin emit 順序契約測 + Token payload 契約測 | 13 | ✅ |
| W3 | `AutoResumeService` Layer 2 + dry_run Kernel 端對端測試 | 17 | ✅ |
| W4 | M1 shim（3 方法）+ `check_frozen_surface_shim.py` + F3 main.py 注入 + M6 deprecated 標記 | 9 | ✅ |
| W5 | M4 alembic migration + DBA 審查修復 + P1 #1~#5 + DBA 簽核 | +3 contract | ✅ |

**最終測試基線**：1006 passed / 11 skipped（W5 PG 契約測在 CI PG service container 執行）

---

## 2. Gate 簽核狀態

| Gate | 最終狀態 | 簽核日期 |
|------|---------|---------|
| G3 Facade 切換（PM 強制簽核）| ✅ 三方全綠 | 2026-05-12 |
| G5 PG backend GA | ✅ 無條件通過（P1 #1~#5 完成）| 2026-05-12 |

---

## 3. DBA W5 審查發現與修復

| ID | 類別 | 問題 | 修復 |
|----|------|------|------|
| C1 | Critical | `checkpoints.run_id` FK 為 NULLABLE | `_pg_models.py` 加 `nullable=False` + 0002 migration |
| C2 | Critical | `_save()` 從不 INSERT `playbook_runs` | 新增 `_ensure_run_id()` + `_run_cache` | 
| C3 | Critical | `total_steps` 漏在 UPSERT `set_` dict | 補入 UPSERT set_ |
| M1 | Major | 契約測 `_truncate` 只清 `checkpoints` | 改為 `TRUNCATE playbook_runs CASCADE` |
| M2 | Major | `_row_to_checkpoint()` 欄位不完整 | 補全所有 `CheckpointRow` 欄位 |

---

## 4. P1 Backlog #1~#5 完成狀態

| # | 項目 | 完成日 |
|---|------|--------|
| #1 | `docker-compose.yml`（postgres:17 + healthcheck）+ `config.yaml.example` | 2026-05-12 |
| #2 | CI workflow `pg-contract` job（postgres:17 service container）| 2026-05-12 |
| #3 | PG startup smoke test（SELECT 1 + alembic head check）| 2026-05-12 |
| #4 | tenacity retry decorator（OperationalError max 3 backoff）| 2026-05-12 |
| #5 | `DualMetrics` hook（dual_write_success/failure + shadow_drift + shadow_load_failure）| 2026-05-12 |

---

## 5. 亮點

- **Strangler Fig 完整閉環**：`use_kernel_path=True` 現在正式可用；Kernel + AutoResumeService + Plugin 已接通生產入口
- **DBA 審查在 W5 發現 3 個 Critical 問題**，全部在同一天修復並通過 DBA 簽核，驗證了 Gate 流程的有效性
- **測試覆蓋**：1006 pass，從 W0 的 927 base 新增 79 tests，覆蓋率完整

## 6. 改善空間

- M6 `_runner_impl.py` 刪除需等待 193 處測試耦合遷移（長期項，已標記 `@deprecated(v2.0)`）
- P1 #7（`last_correction_prompt` redaction）、#8（asyncio 相容）為下一個 sprint backlog
- `db_only` production 切換需 ≥ 24h staging `dual_write_strict=true` 驗證

---

**文檔元數據**：
- 撰寫日期：2026-05-12
- Sprint：SD_Improving_03 v1.1 W5 末
- 對應規格：SD_Improving_03.md v1.1 §5 DoD §6 Sprint Retrospective
