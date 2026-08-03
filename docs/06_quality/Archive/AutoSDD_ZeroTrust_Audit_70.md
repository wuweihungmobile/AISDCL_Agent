# AutoSDD ZeroTrust Audit 70 — act-first warn→硬擋（W-70-1）

> **對應計畫**：[AutoSDD_improving_70.md](../04_planning/AutoSDD_improving_70.md) ｜ **日期**：2026-06-26 ｜ **柱位**：C 軌
> **審查方法**：階段一零信任重偵察（三 Explore agent 並行）+ 結案三鏡（Architect / SA-SD / QA）主樹並行，全部退出碼直取、禁 `| tail` 遮蔽、禁 worktree（tracked 未 commit 修改依 DEF-24-001 走主樹）。

---

## 1. 階段一：基線重實測（硬閘）

| 項目 | 命令 | 實測輸出（尾段） |
|------|------|----------------|
| AutoClaude pytest | `python -m pytest tests/ -q` | `3349 passed, 122 skipped in 73.03s` |
| lint-imports | `PYTHONUTF8=1 lint-imports` | `Contracts: 8 kept, 0 broken.` |
| LOC | `python tools/check_loc_budget.py` | `total=19367 baseline=17032 cap=20438 violations=0` |
| snapshot | `python tools/snapshot_sync.py --check` | `OK — Snapshot 區段 + sprint 骨架對齊一致` |
| SDD ci-gate | `bash scripts/ci-gate.sh` | PASS（v0.01:1478 / v0.26:1665 / scripts:129；arch_fitness fail=0、warn=3 advisory） |
| SDD 版本 | 磁碟 vs FRAMEWORK_STATUS | v0.26 == v0.26（無漂移） |

**硬閘判定**：基線零退化、無 failed、= 上輪 floor 3349 → 准進階段二。

**上輪構件核對（零信任，開檔驗證）**：W-69-1/2 四構件（`sdk_tool_allowlist`/`build_tool_allowlist_predicate`/main.py 接線/`_wrap_can_use_tool`）全部真實存在、測試覆蓋完整、查無虛報；W-69-3 誠實標延後、無實作痕跡。

---

## 2. 階段三/四：實作後實測

| 項目 | 實測 |
|------|------|
| act-first 單檔（5 測） | `5 passed, 13 deselected` |
| 全套 pytest（結案） | `3351 passed, 122 skipped in 68.53s` |
| lint-imports | `8 kept, 0 broken` |
| LOC（adapter 行數） | 318 行 < 400 tier；violations=0 |
| snapshot | FRESH |

**淨測試增量**：floor 3349 → 3351（+2）。act-first 測試由舊 3 測（unsafe_warns/safe_no_warn/skipped_when_missing）改寫為 5 測（unsafe_raises/unsafe_fails_closed/safe_does_not_raise/missing_fields/usage_exception）。

---

## 3. 突變實證（測試非空殼）

- **突變操作**：`_verify_act_first` 內 `raise ActFirstOrderingError(...)` → 暫改 `logger.warning("MUTATION: ...")`（模擬退回 warn-only 舊行為）。
- **突變態結果**：`2 failed, 2 passed, 13 deselected` — `test_act_first_unsafe_raises_actfirst_error` + `test_act_first_unsafe_fails_closed_via_execute` 準確轉紅；safe / missing_fields 維持綠（正確，不依賴硬擋）。
- **還原**：以 Edit 精確還原多行 raise（**禁 git checkout**，遵 [[git-checkout-mutation-revert-hazard]]）→ 複跑 `17 passed`（單檔）/ 全套 3351。
- **QA 鏡獨立重做**：QA 親自重跑突變（改 pass）→ 2 failed，Edit 還原 → 4 passed（補測前）；確認 git CLEAN。

---

## 4. 結案三鏡 Zero-Trust（主樹並行，全 OVERALL PASS、P0=P1=0）

### 4.1 Architect 鏡
- 架構純潔性 PASS：`ActFirstOrderingError` 定義於 adapter 模組（邊界產生點，合理）；`playbook_runner.py` 未修改（Thin Facade 維持）。
- 微核心紅線 PASS：無新跨層 import（imports 僅 `core.ports.executor` + `plugins.token_guard.thresholds` 純函式）；例外傳播 `_verify_act_first→_run_async→anyio.run→execute except` 乾淨，Coordinator 只見 ExecutionOutput、永不見 ActFirstOrderingError。
- 無關閉鍵 PASS：grep `skip/disable/allow_act_first|act_first.*flag` 無結果；raise 無 try-except 捕捉（與 get_context_usage 失敗放行線路獨立）。
- 零退化 PASS：`config.py` 預設 `backend="pty"`（實測 `AppConfig().executor.backend=='pty'`），預設路徑不觸碰 adapter。
- LOC PASS：318 行 < 400 tier；IExecutor 簽名完整。

### 4.2 SA-SD 鏡（9.5/10 → 補測後 10/10）
- fail-closed 語義 PASS：三「無法判定」路徑（get_context_usage 例外 L240-243 / 非 dict L244-245 / 缺欄位 L248-249）早返放行；唯 `safe=False` raise；無遺漏路徑讓不安全漏過。
- 守門時序 PASS：raise 在 `client.query(prompt)` 之前；測試證 `fake.query_prompts == []`（硬擋阻止任務啟動）。
- 判定權威源 PASS：`verify_act_first_ordering` 本輪 `git diff` 無輸出（逐字未動）；公式 + 防呆（負數視為不安全 fail-closed）完整保留。
- Rule 9 測試覆蓋 PASS：測試不僅驗 raise 型別，更驗 query 未送出、completed=False；有「安全不誤擋」「無法判定不誤擋」反向測試。
- **GAP（已當場補）**：get_context_usage 本身拋例外路徑無顯式測試 → 補 `test_act_first_usage_exception_does_not_raise`（驗 best-effort 放行）。

### 4.3 QA 鏡（5 項全 PASS）
- 全套 pytest 親跑 3350→（補測後）3351/122/0，無 failed。
- act-first 5 測全綠（unsafe_raises / unsafe_fails_closed / safe_does_not_raise / missing_fields / usage_exception）。
- 突變複核：退回 pass → 2 failed；Edit 還原 → 復綠 git CLEAN。
- lint-imports 8 kept / 0 broken。
- 誠實性檢查：act-first 測試皆純 `def`、無 skip/xfail/skipif/註解規避；`importorskip` 僅 anyio + claude_agent_sdk 型別測試（非 act-first 測試）。

---

## 5. 缺陷帳本處置

- **本輪無新框架缺陷**（純 AutoClaude C 軌 additive 升級、SDD 本體零變更）。
- SA-SD 鏡提出的測試覆蓋缺口屬本輪實作的測試完整性，當場補測非框架缺陷，不入帳本（於 §4.2 + 計畫 §7 留證）。
- 上輪 open 3 / routed 3（全 P3）本輪未觸碰、無重現惡化，carried。
- Defect_Log append recap（本輪 recap 條目）。

---

## 6. 誠實級別結論

本輪＝**C 軌 act-first 安全閘 warn→硬擋加固輪，非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。三鏡全 PASS、P0=P1=0、突變實證測試非空殼、SA-SD 缺口當場補齊。免 Copy-on-Evolve、免五軌 TLC（未碰 SDD 本體/`*.tla`/FSM）。
