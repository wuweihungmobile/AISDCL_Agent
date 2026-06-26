# AutoSDD_improving_79 — C 軌：production Kernel 路徑 token-guard **compact 子路徑**完整接線（DEF-78-001 全閉合）

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自我精進）**。下一份＝`AutoSDD_improving_80.md`。
> **定位**：接續 improving_78 W-78-1（halt 子路徑），完成 DEF-78-001 的**孿生另一半 W-78-2（compact 子路徑）**——production Kernel 路徑 ≥80% 真實 token% 觸發真誠 `/compact` 動作 + `TOKEN_COMPACT` marker，並**完整移植棄用路徑的 Gap-008-E「連續 compact 失敗 2 次 → 強制 TOKEN_HALT + checkpoint」**業務邏輯（掌舵者 2026-06-26 裁定「完整移植 Gap-008-E」）。做完後 production token churn（compact）維度在真跑轉真值、DEF-78-001 **halt + compact 雙子路徑全接線、全閉合**。
> **成熟度**：`L_合體 = min(A,B,C)` 維持 **L5**（修復 production 編排缺口、恢復文件宣稱行為〔CLAUDE.md「≥80% /compact、≥90% halt」〕，非成熟度推進）。
> **掌舵者拍板（2026-06-26）**：W-78-2 範圍＝**完整移植 Gap-008-E**（不只最小接線；連連續 compact 失敗→HALT 一起做，DEF-78-001 可宣稱 100% 完整接線、零 routed 殘留）。
> **B 軌（dogfooding）**：本輪純 AutoClaude C 軌（生產碼 + 測試），**零碰 `AISDLC_SDD/`**（免 Copy-on-Evolve、免五軌 TLC）。

---

## §1 本輪輸入（自 improving_78 繼承）

1. **上輪（improving_78）已完成 W 項**：**W-78-1 halt 子路徑完整接線**（修 DEF-78-001 halt 半邊）——`core/_token_observer.py` 觀測真實 token% → Kernel `_consult_token_guard` emit `ON_TOKEN_USAGE` → 真 TokenGuardPlugin ≥90% `request_halt` → 印真誠 `TOKEN_HALT` marker + 回 HALT（`KernelResult` additive 帶 `halt_step_idx`/`peak_token_pct`）→ AutoResumeService `_persist_halt_checkpoint` 存 path-aware halt checkpoint。新測 13、全套 3421/122/0、commit 65f2fa5（+ DEF-77-002 housekeeping 3931bcf）已 push。
2. **上輪明標續 routed（本輪標的）**：
   - **DEF-78-001 W-78-2（P2）**：compact 子路徑（≥80% `/compact` 動作）接線——上輪因「屬執行層業務邏輯 + 零退化餘量」誠實延後，明標「未做即續 routed」。**本輪做。**
   - **DEF-76-001（P2）**：partially-fixed（載具側 + halt 維度）；其 compact 維度隨 W-78-2 一併轉真值後可完全閉合。
3. **缺陷帳本 open / routed（本輪複驗維持原狀，非本輪標的）**：DEF-01-007（cc-switch GUI P3）／DEF-01-009（LOC watch P3）／DEF-62-001（auto_recovery 註解 P3）／DEF-17-001・DEF-42-001・DEF-35-001（P2 routed C 軌 SD_09 W1）。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-26，background agent 親跑、parent 複核）

| 項目 | 命令 | 實測結果 | 達標 |
|------|------|---------|------|
| AutoClaude 全套 pytest（硬閘基線） | `PYTHONUTF8=1 python -m pytest tests/ -q` | **3421 passed / 122 skipped / 0 failed**（70.51s） | ✅ = floor 3421，硬閘未觸發 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（197 files / 496 deps） | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19508 / baseline=17032 / cap=20438） | ✅ |
| Snapshot 新鮮度 | `python tools/snapshot_sync.py --check` | **新鮮**（OK，EXIT 0） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **EXIT 0 全綠**（v0.01:1478 + v0.26 LATEST:1665 + scripts/tests:129；arch_fitness exit 0，2 條 FF-16 🟡 advisory 不阻擋） | ✅ |
| 上輪構件存在性 | 直讀生產碼 | W-78-1 三構件存在屬實：`core/_token_observer.py`（TokenObserver）、`kernel.py:274-299`（`_consult_token_guard`）、`auto_resume.py:237-277`（`_persist_halt_checkpoint`，gate `halt_step_idx is not None`） | ✅ |
| 外部工具依賴 (f) | — | 本輪純 production 碼接線，**零新增外部 CLI/服務/訊息平台**；compact 走既有 `IExecutor.execute`（SDK/PTY adapter） | N/A（無外部依賴） |

> **校正**：SDD 最新演化版實測為 **v0.26**（非 SDD-ROUTER 提示預設的 0.18）。本輪零碰 `AISDLC_SDD/`，不受影響。

### 🔴 W-78-2 缺口直讀生產碼（零信任，非採信文件）

| 事實 | 鐵證（file:line） |
|------|------------------|
| Kernel `_consult_token_guard` 只 honor halt、明標 compact 留 W-78-2 | `core/kernel.py:281`「≥compact 門檻的 request_compact 由 W-78-2 執行層處理，本輪 Kernel 不動作」 |
| Kernel emit ON_TOKEN_USAGE 後僅檢 `tu.request_halt` | `kernel.py:292`（無 `tu.request_compact` 分支） |
| TokenGuardPlugin 已會回 request_compact（≥80%）但 production 無人消費 | `token_guard/policy.py:172-181`（`should_compact` → `ResourceRequest(request_compact=True)`） |
| `ExecutionOutput` 刻意精簡無 compact 結果欄 | `core/ports/executor.py:20-30`（只有 text/exit_code/completed）→ Kernel 真實 token% 須靠 W-78-1 的 `TokenObserver` |
| compact 動作（送 /compact）+ marker 真實邏輯只在棄用路徑 | `_impl.py:232-251`（`runner._send_compact` → `compact_controller.send_compact_impl` → `runner._execute_prompt`）；production Kernel 全無 |
| Gap-008-E 連續失敗→HALT 邏輯在 plugin（SSOT）但 production 從未被觸發 | `token_guard/compactor.py:80-93`（`process_compact_result` + `CompactFailureState`）；`compact_controller.py:53-68` 僅棄用路徑呼叫 |
| `POST_COMPACT` phase 已定義、契約 `{ResourceRequest}`、**全 codebase 零 emit 端** | `hookspec.py:52,252`；grep 證 production/棄用路徑皆無 emit POST_COMPACT → 加 plugin handler 對既有行為**零退化風險** |
| 載具已 substring 計 `TOKEN_COMPACT` → compact_count、抓 `NN%` 餵 peak、抓 `[Sxx]` per-step | `tools/ab_compare_backends.py:161,173,177`；但其誠實註解（:149-156）仍記「compact 維度待 W-78-2、production 真跑仍 0」 |

**結論**：W-78-2 缺口＝Kernel 不消費 `request_compact`、無 compact 動作、無 POST_COMPACT emit。三者補齊即 compact 子路徑接線完成。

---

## §3 本輪增量設計（W-78-2 compact 子路徑完整接線 + Gap-008-E）

### `<Architecture_Design_Review>`

1. **架構純潔性（無 God-object / Thin Facade 不破）**：
   - **Kernel 維持純 DAG「觀測 + emit + honor request」角色**——延續 W-78-1：本輪只新增「honor `request_compact`」分支，**送 /compact 的業務邏輯抽至 `core/` helper**（`_token_compactor.perform_compact`，與 `_token_observer.py` 同模式），Kernel 僅委派。Gap-008-E 連續失敗決策**走 EventBus**（emit `POST_COMPACT` → 真 TokenGuardPlugin 判斷），**`CompactFailureState` SSOT 留在 plugin、不外洩到 Kernel**。
   - **零 `core → plugins` / `core → infra` 反向 import**：compact prompt 由 core helper 自建（結構化保留提示，與 `token_guard/compactor.build_compact_prompt` 同精神但 core-local，不 import plugin）；token_guard 決策（should_compact / process_compact_result）全程經 EventBus `ResourceRequest`，Kernel 不持有 plugin 參照。`.importlinter` core-purity（Rule 2）維持。
   - playbook_runner thin facade 不碰、plugin 互不 import（不新增 plugin）。
2. **持久化相容**：Gap-008-E 的 HALT **複用 W-78-1 既有路徑**——`_handle_compact` 回 `StepOutcome(HALT, peak=...)` → `run()` HALT 分支已傳 `halt_step_idx=step_idx`（kernel.py:122）→ `KernelResult.halted_` → AutoResumeService `_persist_halt_checkpoint`（gate `halt_step_idx is not None`，:211）**自動存 path-aware checkpoint，無需新持久化碼**。additive、DAL 三後端零停機維持。
3. **安全防護網**：零新增 CONDITIONAL 指令生成路徑；compact prompt 為靜態常數 + step_id 內插（step_id 來自 playbook 既經 PreRunValidator 驗證），不從外部文件生成指令。
4. **對外 I/O 安全**：零新增 `ToolInvocationPort` 外呼路徑；compact 走既有 `IExecutor.execute`（與步驟執行同一受信 executor）。N/A。

### W-78-2 介面 delta

| 修點 | 檔案 | 介面 delta | 設計 |
|------|------|-----------|------|
| ① compact 動作 helper（新） | 新 `autoclaude/core/_token_compactor.py` | `perform_compact(executor, *, step_id, peak_pct, timeout=60) -> float` | 印真誠 `=== STATE: TOKEN_COMPACT \| [Sxx] context NN% >= compact 門檻 ===`（載具計 compact_count + per-step）；送 `/compact`（結構化保留提示常數）經 `executor.execute(..., on_event=fresh_observer)`；回 compact 後 `fresh_observer.peak_pct`。純委派、零 plugin/infra import |
| ② Kernel honor compact | `core/kernel.py` `_consult_token_guard` + 新 `_handle_compact` | `_consult_token_guard` 加 `if tu.request_compact:` 分支 → 委派 `_handle_compact` | `_handle_compact`：`perform_compact` 取 post_peak → emit `POST_COMPACT{token_pct:post_peak, step_id, max_retries}` → 真 TokenGuardPlugin 判 Gap-008-E → `pc.request_halt` 則印 `TOKEN_HALT` marker（reason 標 Gap-008-E）+ 回 `StepOutcome(HALT, peak=max(peak,post_peak))`；否則 None（compact 成功/未達上限 → 續評估原 output） |
| ③ TokenGuardPlugin POST_COMPACT | `plugins/token_guard/policy.py` | `subscribed_phases` 加 `POST_COMPACT`；`on_event` 加分支 → 新 `_evaluate_post_compact` | `_evaluate_post_compact`：`still_high = should_compact(post_pct, attempt, max_retries)`（compact 後仍達門檻＝失敗）→ `process_compact_result(triggered_compact=still_high, ...)`（`CompactFailureState` SSOT 記/重設）→ `is_critical`（連續 2 次）回 `ResourceRequest(request_halt, reason="Gap-008-E …")`，否則 None |
| ④ 載具誠實 | `tools/ab_compare_backends.py` 註解 | 訂正 :149-156 DEF-78-001 註解 | production compact 維度本輪起真值（≥80% 真送 /compact + TOKEN_COMPACT marker）；無 parse 邏輯變更（既有 substring 計數即生效） |

- **語意保證（零退化）**：`_consult_token_guard` 入口 `peak_pct <= 0` 仍直接 None（無 token 訊號 → 不 emit、不 compact、行為與接線前完全一致）。POST_COMPACT 現況**零 emit 端**，故加 plugin handler 不影響任何既有路徑。
- **誠實邊界**：
  - compact prompt 採 core-local 結構化常數，**未移植棄用路徑的 memory-anchor**（task/失敗摘要/global_goal 注入）——anchor 屬 compact 品質 enrichment、非 DEF-78-001 接線必要（載具計數 + /compact 動作不依賴 anchor）；本輪明標此為**誠實限制**（justified：anchor 需 core→plugin 拉 build_compact_prompt 或重複其邏輯，違分層/DRY；可 route 未來輪）。
  - Gap-008-E **完整移植**（掌舵者裁定）：連續 compact 失敗 2 次 → 強制 TOKEN_HALT + checkpoint，與棄用路徑 `CompactFailureState` 語意一致。
- **W-78-1 對齊**：TOKEN_HALT marker（Gap-008-E 觸發）沿用 W-78-1 `logger.warning` 格式；TOKEN_COMPACT 用 `logger.info`（對齊棄用 `_impl.py:232`）。兩者皆落 log 供載具解析（載具讀檔文字、不分 level）。

### RTM 需求列（階段三/四回填實測欄）

| RTM-ID | 需求 | 驗證 | 階段 |
|--------|------|------|------|
| RTM-79-1 | `perform_compact` 印真誠 TOKEN_COMPACT marker（含 [Sxx] + NN%）、送 /compact、回 compact 後 peak；無 token 訊號回 0 | 單測（fake executor 驗 marker 文字 + execute 被呼 + post_peak 傳遞） | 三 |
| RTM-79-2 | Kernel `request_compact`（且非 halt）→ `_handle_compact` 送 compact + emit POST_COMPACT；compact 後未達上限 → 續評估原 output（ADVANCE） | 單測（85% fake → compact + 印 marker + 不 HALT、續評估成功） | 三 |
| RTM-79-3 | Gap-008-E：compact 後 token 仍 ≥ 門檻連續 2 次 → 真 TokenGuardPlugin 回 request_halt → Kernel HALT + 印 TOKEN_HALT + AutoResumeService 存 checkpoint | 單測（真 TokenGuardPlugin，compact 後仍高 ×2 → HALT，halt_step_idx 正確） | 三 |
| RTM-79-4 | TokenGuardPlugin subscribed_phases 納入 POST_COMPACT；`_evaluate_post_compact` 仍高記失敗、降低重設 | 單測（POST_COMPACT 仍高 → request_halt at critical；降低 → None + 計數重設） | 三 |
| RTM-79-5 | 零退化：peak=0 不 emit/compact；POST_COMPACT 零既有 emit 端故無副作用；全套 pytest ≥ 3421 / 0 failed | 全套 pytest + lint + LOC + snapshot | 三/四 |
| RTM-79-6 | 載具 compact 維度誠實——production 真送 /compact 後 compact_count 轉真值；註解訂正 | 載具註解 + §8 誠實標 | 四 |

---

## §4 實作與雙重驗證（2026-06-26 完成）

### §4.1 實作明細（W-78-2）
- **新 `autoclaude/core/_token_compactor.py`**（`perform_compact`）：印真誠 `=== STATE: TOKEN_COMPACT | [Sxx] context NN% >= compact 門檻 ===`（`logger.info`，載具 substring 計 compact_count + 抓 NN% 餵 peak + 抓 [Sxx] per-step）；送 core-local 結構化 `/compact` 常數 `_COMPACT_PROMPT` 經 `executor.execute(..., on_event=fresh TokenObserver)`；回 compact 後 `peak_pct`。純委派、零 plugin/infra import（core-purity 維持）。
- **`autoclaude/core/kernel.py`**：import `perform_compact`；`_consult_token_guard` 於 halt 檢查後加 `if tu.request_compact:` → 委派新 `_handle_compact`（:301-330）——`perform_compact` 取 post_peak → emit `POST_COMPACT{token_pct:post_peak, step_id, max_retries}` → `pc.request_halt`（Gap-008-E）則印 `=== STATE: TOKEN_HALT | [Sxx] … （Gap-008-E 連續 compact 失敗）===`（`logger.warning`）+ 回 `StepOutcome(HALT, peak=max(peak,post_peak))`；否則 None 續評估。Kernel 僅委派 + honor request（純 DAG），送 /compact 業務邏輯在 core helper、連續失敗決策走 EventBus。
- **`autoclaude/plugins/token_guard/policy.py`**：`subscribed_phases` 加 `POST_COMPACT`；`on_event` 加 POST_COMPACT 分支 → 新 `_evaluate_post_compact`——`still_high = should_compact(post_pct,…)`（compact 後仍達門檻＝失敗）→ `process_compact_result(triggered_compact=still_high)`（`CompactFailureState` SSOT 記/重設）→ `is_critical`（連續 2 次）回 `ResourceRequest(request_halt, reason="Gap-008-E …")`。
- **Gap-008-E HALT checkpoint 持久化**：**複用 W-78-1 既有路徑**——`_handle_compact` 回 HALT → `run()` 傳 `halt_step_idx` → AutoResumeService `_persist_halt_checkpoint`（gate `halt_step_idx is not None`）自動存，**零新持久化碼**。
- **`tools/ab_compare_backends.py`**：僅更新 DEF-78-001 誠實註解（:149-159 compact 維度本輪起 production 真值、雙子路徑全閉合），無 parse 邏輯變更（既有 substring 計數即生效）。
- **新測 13**：compactor 4（`test_token_compactor.py`）+ kernel compact 4（`test_kernel_token_compact.py`，用真 TokenGuardPlugin）+ plugin POST_COMPACT 5（`test_token_guard_plugin.py::TestPostCompactGap008E`）。
- **更新 2 既有測試**（§4.2 詳述）：`tests/core/test_kernel_token_halt.py`（85% 行為遷移）+ `tests/plugins/token_guard/test_policy_mutation.py`（subscribed_phases len 2→3）。

### §4.2 既有測試更新（行為變更誠實紀錄，非退化）
W-78-2 接線後，兩個既有測試的硬編碼斷言反映「W-78-2 未接」的舊行為，依 Rule 9 更新為新行為（**非 failure 退化，是刻意行為變更的測試對齊**，全程無隱藏 skip/xfail）：
- `tests/core/test_kernel_token_halt.py::test_compact_threshold_does_not_halt_this_round` → 改名 `test_compact_threshold_triggers_compact_not_halt`：85% 由「Kernel 不動作」更新為「真送 /compact + 印 TOKEN_COMPACT marker、單次失敗不 halt」。
- `tests/plugins/token_guard/test_policy_mutation.py::test_subscribed_phases_includes_both`：`len(phases)==2` → `==3`（新增 POST_COMPACT），補 `POST_COMPACT in phases` 斷言。
- 首跑全套揭露此 1 處 count 斷言失敗（3433 passed / 1 failed），更新後復綠 3434/0；如實記錄、未繞過。

### §4.3 受控突變實證非空殼（序列、Edit 還原、禁 git checkout）
- **MUT-79-1**〔kernel `if tu.request_compact:` → `and False`〕→ `test_compact_threshold_sends_compact_and_marker` + `test_consecutive_compact_failures_trigger_gap008e_halt` 轉紅（compact 不送、不 halt），Edit 還原復綠。
- **MUT-79-2**〔policy `_evaluate_post_compact` 的 `if not ok:` → `and False`〕→ Gap-008-E 兩測轉紅（`isinstance(None, ResourceRequest)` False / `halted` False），Edit 還原復綠。
- **MUT-79-3**〔compactor `return post_observer.peak_pct` → `* 0`〕→ `test_returns_post_compact_peak_from_fresh_observer` + Gap-008-E 整合測轉紅（post_peak 失真致連續失敗判定失效），Edit 還原復綠。
- `grep -rn MUT-79 autoclaude/` 無殘留；還原後相關 4 檔 68 passed 復綠。

## §5 零退化驗證矩陣（RTM / SCG-5，階段四回填實測）

| 檢查 | 命令 | 通過條件（floor = improving_78 實測 3421） | 實測 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3421 passed / 0 failed（新測只增不減） | **3434 passed / 122 skipped / 0 failed**（= 3421 + 13 新；69.89s） ✓ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken**（core→core helper 合法，零 core→plugin/infra） ✓ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | **violations=0**（total=19624 / cap=20438；kernel.py 實測 307 行 < absolute≤750 紅線〔core/kernel.py 屬 unclassified→absolute tier，非 service〕、新 helper `_token_compactor.py` 53 行過 data tier） ✓ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK — 對齊一致** ✓ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **N/A — 本輪零碰 AISDLC_SDD/**（git diff 鐵證） | **N/A**：`git status --short AISDLC_SDD/` 空輸出（階段四複核） |
| DAL 等價 | equivalence job | 隨全套通過；無新 DAL/checkpoint schema 改動（複用 W-78-1 持久化路徑） | 隨全套通過（`tests/equivalence/`）、零碰 DAL schema，無新 round-trip 契約 |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A — 零碰 `*.tla`/FSM**（git diff 鐵證） | **N/A**：git status 無 `*.tla`/FSM 變更 |

## §6 缺陷帳本本輪處置（詳見 AutoSDD_Defect_Log.md）

- **DEF-78-001（P2）**：本輪 W-78-2 接 compact 子路徑（perform_compact + Kernel `_handle_compact` + plugin POST_COMPACT）+ 完整移植 Gap-008-E（連續失敗 2 次→HALT）→ **fixed@improving_79（halt+compact 雙子路徑全接線、全閉合）**。
- **DEF-76-001（P2）**：compact 維度（compact_count / peak）隨本輪轉 production 真值 → 由 partially-fixed 升 **fixed**（halt + compact 載具維度皆 production 真值）。
- 其餘 open/routed（DEF-01-007/01-009/62-001/17-001/42-001/35-001）：本輪未觸碰標的，複驗維持原狀態。

## §7 多專家 Zero-Trust 審查（階段四回填）

_（待 Architect / SA-SD / QA 三鏡 + 複審證據）_

## §8 誠實標記（階段四回填補完）

- **規格先行**：本檔 §1–§3（含 `<Architecture_Design_Review>`/介面 delta/RTM）於**階段二先落地**（寫 code 前），§4/§5/§7 實測欄階段三/四回填——非事後結案報告。
- **誠實級別**：本輪＝**C 軌指揮官 AutoClaude 缺陷修復輪（接 DEF-78-001 compact 子路徑），非成熟度推進**，`L_合體=min(L5,L5,L5)=L5` 維持。
- **memory-anchor 未移植**：compact prompt 採 core-local 結構化常數，棄用路徑的 memory-anchor enrichment（task/失敗摘要/global_goal 注入）本輪未移植（justified：避免 core→plugin 拉 build_compact_prompt 或重複其邏輯破壞分層/DRY；非 DEF-78-001 接線必要，載具計數 + /compact 動作不依賴 anchor）。遵 [[no-defer-unless-justified]]：真延後須明說理由＝分層/DRY 張力。
- **既有測試更新誠實**：§4.2 如實記兩個既有測試由「W-78-2 未接」舊行為更新為新行為（行為變更測試對齊，非 failure 退化）；首跑 1 處 count 斷言失敗已更新復綠，未隱藏。
- **Gap-008-E 完整移植**：掌舵者裁定，連續 compact 失敗 2 次→強制 TOKEN_HALT+checkpoint，與棄用路徑 CompactFailureState 語意一致；CompactFailureState SSOT 留 plugin、走 EventBus（POST_COMPACT），未外洩 Kernel。
- **N/A 精確**：AISDLC_SDD ci-gate / 五軌 TLC ＝「條件未觸發、本輪確實未跑」附 git diff 鐵證（`git status --short AISDLC_SDD/` 空）；DAL 等價 ＝「既有測試隨全套已跑且通過、本輪無新 DAL/checkpoint 契約」（複用 W-78-1 持久化路徑）。
- **誠實限制（承 W-78-1）**：Gap-008-E HALT 經 W-78-1 既有 `_persist_halt_checkpoint` 存最小 checkpoint，跨 session 計數器（goto/inject/skip/evolution）不隨此最小 checkpoint 持久化（預設空 dict）；核心 resume 資料齊備。
