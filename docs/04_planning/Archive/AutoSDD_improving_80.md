# AutoSDD_improving_80 — C 軌：compact prompt memory-anchor 移植 → core 共享 SSOT + Kernel compact 路徑 anchor enrichment

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自我精進）**。下一份＝`AutoSDD_improving_81.md`。
> **定位**：閉合 improving_79 §8 明標的**誠實限制**——production Kernel compact 路徑送出的 `/compact` 提示是 core-local 靜態常數（`_token_compactor._COMPACT_PROMPT`），**缺 `=== MEMORY ANCHOR ===` 區塊**（task/attempt/成功條件/global_goal/last_failure），因為 anchor 邏輯（`build_compact_prompt`）住在 plugin、core 不可 import plugin（importlinter Rule 2）。本輪以**正解相依方向**（plugin→core 合法）把純函式 `build_compact_prompt` 上移為 **core 共享 SSOT**，plugin 端 re-export 保既有 caller 不破，並讓 Kernel compact 路徑帶 anchor 素材 → production compact 壓縮後保留任務記憶（提升 token 失控時的收斂韌性，L5 自治能力的實質強化）。
> **成熟度**：`L_合體 = min(A,B,C)` 維持 **L5**（強化既有能力品質、解既有分層張力、閉合上輪誠實限制，非成熟度推進）。
> **掌舵者拍板（2026-06-26）**：本輪 W 項＝ memory-anchor 移植解張力（AskUserQuestion 四候選擇此；非「真跑長 playbook」〔外部依賴重、非乾淨碼交付〕、非 per-step 聚合〔scope 小〕、非 SD_09 W1〔偏 ops〕）。
> **B 軌（dogfooding）**：本輪純 AutoClaude C 軌（生產碼 + 測試），**零碰 `AISDLC_SDD/`**（免 Copy-on-Evolve、免五軌 TLC）。

---

## §1 本輪輸入（自 improving_79 繼承）

1. **上輪（improving_79）已完成 W 項**：**W-78-2 compact 子路徑完整接線 + Gap-008-E 移植**——新 `core/_token_compactor.perform_compact`（送 /compact + 印真誠 TOKEN_COMPACT marker）；Kernel `_consult_token_guard` 加 `request_compact` 分支 → `_handle_compact` → emit POST_COMPACT；TokenGuardPlugin `_evaluate_post_compact` 完整移植 Gap-008-E（連續失敗 2 次 → request_halt → Kernel HALT，CompactFailureState SSOT 留 plugin、走 EventBus）。DEF-78-001 halt+compact 雙子路徑全閉合；DEF-76-001 升 fixed。全套 3434/122/0、commit 318c965 已 push。
2. **上輪明標續 routed（本輪標的）**：
   - **improving_79 §8「memory-anchor 未移植」誠實限制（justified routed）**：compact prompt 採 core-local 靜態常數，棄用路徑的 memory-anchor enrichment（task/失敗摘要/global_goal 注入）未移植，理由＝避免 core→plugin 拉 `build_compact_prompt` 或重複其邏輯破壞分層/DRY。原文「可 route 未來輪」。**本輪做（以正解相依方向移植，解張力非繞過）。**
3. **缺陷帳本 open / routed（本輪複驗維持原狀，非本輪標的）**：DEF-01-007（cc-switch GUI P3）／DEF-01-009（LOC watch P3）／DEF-62-001（auto_recovery 註解 P3）／DEF-17-001・DEF-42-001・DEF-35-001（P2 routed C 軌 SD_09 W1）。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-26，parent 親跑 + 背景跑、輸出複核）

| 項目 | 命令 | 實測結果 | 達標 |
|------|------|---------|------|
| AutoClaude 全套 pytest（硬閘基線） | `PYTHONUTF8=1 python -m pytest tests/ -q` | **3434 passed / 122 skipped / 0 failed**（69.16s） | ✅ = floor 3434，硬閘未觸發 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（198 files / 499 deps） | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19628 / baseline=17032 / cap=20438） | ✅ |
| Snapshot 新鮮度 | `python tools/snapshot_sync.py --check` | **新鮮**（OK，對齊一致） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **EXIT 0 全綠**（v0.01:1478 + v0.26 LATEST:1665 + scripts/tests:129；arch_fitness advisory 不阻擋） | ✅ |
| 上輪構件存在性 | 直讀生產碼 | W-78-2 構件存在屬實：`core/_token_compactor.py`（perform_compact）、`kernel.py:300-332`（`_handle_compact`）、`token_guard/policy.py:193`（`_evaluate_post_compact`）、`tests/core/test_token_compactor.py` + `test_kernel_token_compact.py` | ✅ |
| 外部工具依賴 (f) | — | 本輪純 production 碼 + 測試重構/接線，**零新增外部 CLI/服務/訊息平台**；compact 走既有 `IExecutor.execute` | N/A（無外部依賴） |

> **校正**：SDD 最新演化版實測為 **v0.26**（非 SDD-ROUTER 提示預設 0.18）。本輪零碰 `AISDLC_SDD/`，不受影響。

### 🔴 本輪張力直讀生產碼（零信任，非採信文件）

| 事實 | 鐵證（file:line） |
|------|------------------|
| core compact 路徑送靜態常數、缺 anchor | `core/_token_compactor.py:33-40`（`_COMPACT_PROMPT` 無 `=== MEMORY ANCHOR ===`）；`:62-65`（`executor.execute(_COMPACT_PROMPT, ...)`） |
| anchor 邏輯（含 task/attempt/成功條件/global_goal/last_failure）住在 plugin | `plugins/token_guard/compactor.py:34-77`（`build_compact_prompt` 純函式，含 `=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===` 組裝） |
| `build_compact_prompt(task=None, failure_summary="")` base 與 core `_COMPACT_PROMPT` **逐字相同** | 對照 `compactor.py:66-72`（base 段）vs `_token_compactor.py:33-40` → 文字完全一致（task=None 時 anchor="" 不附加）→ 移除常數改用 build_compact_prompt 為**零行為變更 fallback** |
| Kernel `_handle_compact` 已持有 anchor 素材（只是未傳） | `kernel.py:305`（`_handle_compact(playbook, task, step_idx, attempt, ...)` 已有 task）；`playbook.global_goal`（`_run_step` 全程可取）；`last_failure_reason`（`_run_step:164`，compact 點為前一 attempt 失敗，attempt 0 時為空——語意正確） |
| compact 諮詢點在 execute 後、evaluate 前 → last_failure 為前次 attempt | `kernel.py:184-195`（execute→`_consult_token_guard`→evaluate） |
| caller 全用 `from ...token_guard.compactor import build_compact_prompt`（4 測試 + policy.py） | `policy.py:27`、`tests/.../test_compactor*.py`、`test_w1_*` → **re-export 即全保不破** |
| plugin→core import 為既有合法模式 | 全 plugins `from autoclaude.core.hookspec import HookSpec`；importlinter Rule 2 只禁 core→execution/infra（反向不禁） |

**結論**：張力＝「anchor 邏輯被困在 plugin、core compact 路徑無法取用」。正解＝把**純函式** `build_compact_prompt` 上移為 core 共享 SSOT（plugin re-export），讓 production Kernel compact 路徑帶 anchor 素材——**解分層張力（非繞過、非重複碼）、閉合上輪誠實限制**。

---

## §3 本輪增量設計（W-80-1 memory-anchor 移植 + Kernel compact anchor enrichment）

### `<Architecture_Design_Review>`

1. **架構純潔性（無 God-object / Thin Facade 不破）**：
   - **相依方向正解**：把純函式 `build_compact_prompt`（無 IO、無狀態）從 `plugins/token_guard/compactor.py` 上移到新 `core/_compact_prompt.py`（core 共享 helper，與 `_token_observer.py`/`_token_compactor.py` 同層）。`compactor.py` 改 **re-export**（`from autoclaude.core._compact_prompt import build_compact_prompt`），保 plugin 端既有 import path 與 `policy.build_compact_prompt` 委派全不破。**這是把共用純邏輯下沉到 core，讓 core 與 plugin 共用單一 SSOT——消除 DRY 隱憂，相依方向 plugin→core 合法**（importlinter Rule 2 只禁 core→execution/infra）。`CompactFailureState`/`process_compact_result`（plugin 專用狀態）**留原處不動**。
   - **Kernel 維持純 DAG**：`_handle_compact` 僅多傳 anchor 素材（task/attempt/global_goal/last_failure）給 core helper `perform_compact`，**送 /compact 業務邏輯仍在 core helper**、決策仍走 EventBus。Kernel 不新增業務邏輯。
   - playbook_runner thin facade 不碰、plugin 互不 import（不新增 plugin）、無 core→plugin/infra 反向 import。
2. **持久化相容**：零新增 checkpoint 欄位、零碰 DAL；Gap-008-E HALT 仍複用 W-78-1 `_persist_halt_checkpoint`。additive、DAL 三後端零停機維持。
3. **安全防護網**：零新增 CONDITIONAL 指令生成路徑。anchor 內容由 task 既有欄位（step_id/name/expected_output_regex，已過 PreRunValidator）+ global_goal（playbook 既有欄位）+ last_failure（內部評估字串）內插，**不從外部文件生成指令**；compact prompt 仍以 `/compact` 開頭為靜態保留策略。
4. **對外 I/O 安全**：零新增 `ToolInvocationPort` 外呼路徑；compact 走既有 `IExecutor.execute`。N/A。

### W-80-1 介面 delta

| 修點 | 檔案 | 介面 delta | 設計 |
|------|------|-----------|------|
| ① 純函式上移（新 SSOT） | 新 `autoclaude/core/_compact_prompt.py` | `build_compact_prompt(*, task=None, attempt=0, failure_summary="", global_goal=None, global_goal_anchor_chars=200) -> str` | 逐字搬自 `compactor.py`（簽名/行為完全保留）；無 plugin/infra import、無狀態（純函式）。docstring 標明本檔為 compact prompt 組裝 SSOT，core 與 plugin 共用 |
| ② plugin re-export | `plugins/token_guard/compactor.py` | 移除 `build_compact_prompt` 定義，改 `from autoclaude.core._compact_prompt import build_compact_prompt`（re-export，`# noqa: F401`） | `CompactFailureState`/`process_compact_result` 留原；既有 `from ...compactor import build_compact_prompt`（policy.py + 4 測試檔）零改動 |
| ③ core compact helper 帶 anchor | `core/_token_compactor.py` | `perform_compact(executor, *, step_id, peak_pct, task=None, attempt=0, global_goal=None, failure_summary="", timeout=60) -> float` | 移除靜態 `_COMPACT_PROMPT`；改 `prompt = build_compact_prompt(task=task, attempt=attempt, failure_summary=failure_summary, global_goal=global_goal)`。task=None → anchor="" → 逐字等價舊常數（零退化 fallback）；task 給定 → 帶 `=== MEMORY ANCHOR ===`。marker 不變 |
| ④ Kernel 傳 anchor 素材 | `core/kernel.py` `_consult_token_guard` + `_handle_compact` + `_run_step` 呼叫點 | `_consult_token_guard`/`_handle_compact` 新增 `last_failure_reason: str` 參數；`_run_step:191` 呼叫傳 `last_failure_reason` | `_handle_compact` 呼叫 `perform_compact(..., task=task, attempt=attempt, global_goal=playbook.global_goal, failure_summary=last_failure_reason)`。production compact 路徑此後送帶 anchor 的 /compact |

- **語意保證（零退化）**：
  - `build_compact_prompt(task=None)` 與舊 `_COMPACT_PROMPT` **逐字相同**（§2 鐵證）→ 既有 `test_token_compactor.py` 4 測試（呼叫不帶 task）行為完全一致、不破。
  - 既有 `test_kernel_token_compact.py` 斷言為 `prompt.startswith("/compact")` + `"優先保留" in prompt`（非逐字比對）→ anchor 附加在 base 之後，仍通過、不破。
  - re-export 保 `compactor.build_compact_prompt` 名稱 → policy.py + 4 既有測試 import 全不破（既有 compact prompt 測試＝行為回歸鎖，移位後須仍全綠）。
  - compact 諮詢點 `last_failure_reason` 在 attempt 0 為 ""（前次 attempt 尚無失敗）→ anchor 無 `[LAST_FAILURE]`，與棄用路徑 `failure_summary=""` 語意一致。
- **誠實邊界**：本輪移植 anchor 之**結構**（task/attempt/成功條件/global_goal/last_failure），與棄用路徑 `build_compact_prompt` 語意完全一致（同一函式上移、非重寫）。Kernel compact 點的 `last_failure_reason` 為前次 attempt 失敗（非當次 output 評估結果——當次尚未 evaluate），此為 compact 時點的最佳可得失敗背景，與棄用路徑時序一致。

### RTM 需求列（階段三/四回填實測欄）

| RTM-ID | 需求 | 驗證 | 階段 |
|--------|------|------|------|
| RTM-80-1 | `build_compact_prompt` 上移 `core/_compact_prompt.py`；`compactor.py` re-export，`core` 與 `plugin` 取得**同一函式物件**、輸出逐字一致 | 單測（`from core...` 與 `from plugin...compactor` import is 同一 callable；同參數輸出相等） | 三 |
| RTM-80-2 | `perform_compact` 帶 task → /compact prompt 含 `=== MEMORY ANCHOR ===` + `[ACTIVE_TASK]` + `[GLOBAL_GOAL]`（global_goal 給定時）；task=None → 逐字等價舊 `_COMPACT_PROMPT`（零退化 fallback） | 單測（fake executor 抓 prompt：task→含 anchor；task=None→無 anchor 且 == 舊常數文字） | 三 |
| RTM-80-3 | Kernel `_handle_compact` 傳 task/global_goal/last_failure → production compact 路徑送帶 anchor 的 /compact（含 [ACTIVE_TASK] 與 playbook.global_goal） | 單測（真 TokenGuardPlugin + SequencedTokenExecutor，85% 觸發 compact，抓 calls[1].prompt 含 anchor + global_goal） | 三 |
| RTM-80-4 | core-purity 維持：`_compact_prompt.py` 無 plugin/infra import；lint-imports 8 kept / 0 broken | lint-imports + 模組 import 健全性 | 三/四 |
| RTM-80-5 | 零退化：既有 compactor/policy/kernel-compact 測試（移位前後）全綠；全套 pytest ≥ 3434 / 0 failed；新測只增不減 | 全套 pytest + lint + LOC + snapshot | 三/四 |
| RTM-80-6 | 上輪誠實限制閉合——improving_79 §8「memory-anchor 未移植」由 routed 轉 done；DEF 帳本（如有相關）更新 | §6 缺陷帳本 + §8 誠實標 | 四 |

---

## §4 實作與雙重驗證（2026-06-26 完成）

### §4.1 實作明細（W-80-1）
- **新 `autoclaude/core/_compact_prompt.py`**（66 行，data tier ≤150）：純函式 `build_compact_prompt` 逐字搬自 `plugins/token_guard/compactor.py`（簽名/行為完全保留），成為 compact prompt 組裝 SSOT；無 plugin/infra import、無狀態（維持 core-purity）。
- **`plugins/token_guard/compactor.py`**（94→52 行）：移除 `build_compact_prompt` 定義，改 `from autoclaude.core._compact_prompt import build_compact_prompt  # noqa: F401`（re-export）；`CompactFailureState`/`process_compact_result`（plugin 專用狀態）留原；移除已不用的 `from typing import Any, Optional`。
- **`autoclaude/core/_token_compactor.py`**（67→70 行，data tier）：移除靜態 `_COMPACT_PROMPT` 常數；`perform_compact` 新增 `task=None / attempt=0 / global_goal=None / failure_summary=""` 參數，改 `prompt = build_compact_prompt(task=task, attempt=attempt, failure_summary=failure_summary, global_goal=global_goal)`。task=None → anchor="" → **逐字等價舊常數**（零退化 fallback，腳本實證 `build_compact_prompt(task=None) == 舊 _COMPACT_PROMPT` 為 True）。
- **`autoclaude/core/kernel.py`**（+~6 行，absolute tier）：`_run_step` 呼叫 `_consult_token_guard` 多傳 `last_failure_reason`；`_consult_token_guard` / `_handle_compact` 簽名加 `last_failure_reason=""`；`_handle_compact` 呼叫 `perform_compact(..., task=task, attempt=attempt, global_goal=playbook.global_goal, failure_summary=last_failure_reason)`。Kernel 維持純 DAG（僅多傳 anchor 素材、無新業務邏輯）。
- **新測 6**（`tests/core/test_compact_anchor_migration.py`）：RTM-80-1 上移+re-export 單一 SSOT 2（`is` 同一物件 + 同參數輸出逐字一致）；RTM-80-2 perform_compact 帶 anchor 3（task→含 MEMORY ANCHOR/ACTIVE_TASK/SUCCESS_CONDITION/GLOBAL_GOAL；failure_summary→LAST_FAILURE；task=None→逐字等價 base fallback）；RTM-80-3 Kernel production compact 路徑帶 anchor + global_goal 1（真 TokenGuardPlugin + SequencedExecutor，85% 觸發 compact 抓 prompt）。

### §4.2 既有測試影響（零修改，全綠回歸鎖）
W-80-1 為純函式上移 + additive anchor enrichment，**未改任何既有測試**（無 Rule 9 行為遷移）：
- `build_compact_prompt` 相關 173 既有測試（`test_compactor*.py` / `test_w1_*` / `test_policy.py` / `test_playbook_yaml_backward_compat.py` / `test_token_halt_roundtrip.py`）因 re-export 保 import path 與 `policy.build_compact_prompt` 委派 → 全綠不破。
- `test_token_compactor.py` 4 測（呼叫不帶 task）→ task=None fallback 逐字等價 → 全綠。
- `test_kernel_token_compact.py` 4 測 + `test_kernel_token_halt.py` → 斷言為 `prompt.startswith("/compact")`/`"優先保留" in prompt`（非逐字），anchor 附加在 base 之後仍通過 → 全綠。
- re-export 同一物件實證：`compactor.build_compact_prompt is core._compact_prompt.build_compact_prompt` → True。

### §4.3 受控突變實證非空殼（序列、Edit 還原、禁 git checkout）
- **MUT-80-1**〔kernel `_handle_compact` 的 `task=task` → `task=None`〕→ `test_kernel_compact_path_sends_anchor_with_global_goal` 轉紅（production compact prompt 缺 MEMORY ANCHOR），Edit 還原復綠。
- **MUT-80-2**〔`_token_compactor.perform_compact` 的 `task=task` → `task=None`〕→ 3 anchor 測（perform_compact 帶 anchor / threads last_failure / Kernel 整合）轉紅，Edit 還原復綠。
- **MUT-80-3**〔compactor.py re-export 改本地 wrapper def 破壞 SSOT 同一性〕→ `test_core_and_plugin_share_single_callable`（`is` 斷言）轉紅，Edit 還原復綠。
- `grep -rn "MUT-80\|_core_bcp" autoclaude/`（排除 .pyc 快取）無原始碼殘留；還原後相關 28 測復綠。

## §5 零退化驗證矩陣（RTM / SCG-5，階段四回填實測）

| 檢查 | 命令 | 通過條件（floor = improving_79 實測 3434） | 實測 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3434 passed / 0 failed（新測只增不減） | **3440 passed / 122 skipped / 0 failed**（= 3434 + 6 新；70.52s） ✓ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken（plugin→core 合法） | **8 kept / 0 broken**（198 files / 499 deps；plugin token_guard→core._compact_prompt 合法，零 core→plugin/infra） ✓ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過（新 `_compact_prompt.py` data tier≤150） | **violations=0**（total=19660 / cap=20438；`_compact_prompt.py` 66 行、`_token_compactor.py` 70 行皆 data tier；compactor.py 94→52 行；kernel.py absolute tier 仍 < 750） ✓ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK — 對齊一致** ✓ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **N/A — 本輪零碰 AISDLC_SDD/**（git diff 鐵證） | **N/A**：`git status --short AISDLC_SDD/` 空輸出（階段四複核） |
| DAL 等價 | equivalence job | 隨全套通過；無新 DAL/checkpoint 改動 | 隨全套通過（`tests/equivalence/`）、零碰 DAL schema，無新 round-trip 契約 |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A — 零碰 `*.tla`/FSM**（git diff 鐵證） | **N/A**：`git status` 無 `*.tla`/FSM 變更 |

## §6 缺陷帳本本輪處置（詳見 AutoSDD_Defect_Log.md）

- **improving_79 §8「memory-anchor 未移植」誠實限制（justified routed）**：本輪 W-80-1 以正解相依方向（純函式上移 core 共享 SSOT + plugin re-export + Kernel 傳 anchor 素材）移植完成 → **閉合**。此為計畫書間誠實限制收尾，非缺陷帳本（DEF-）條目（原即非 bug，是分層張力下的 justified 延後）。
- 缺陷帳本既有 open/routed（DEF-01-007/01-009/62-001/17-001/42-001/35-001）：本輪未觸碰標的，複驗維持原狀態。本輪**無新發現缺陷**（純函式上移 + additive，無框架摩擦/工具錯誤）。

## §7 多專家 Zero-Trust 審查（完成，詳見 AutoSDD_ZeroTrust_Audit_80.md）

三鏡並行（主樹派發——本輪有 untracked 新檔，依 DEF-24-001 禁 worktree；突變已序列完成還原、無並行突變）全數 **OVERALL PASS（P0=0 / P1=0）**：
- **Architect**：core-purity（`_compact_prompt.py`/`_token_compactor.py` 零 plugin/infra import）；plugin→core 合法（.importlinter Rule 2 只禁 core→execution/infra，8 kept）；Thin Facade（`_handle_compact` 僅多傳 anchor 素材無新業務邏輯）；SSOT 真實（compactor/policy/core 三路徑 `is` 收斂同一物件，唯一 `def`）；fallback 逐字等價（舊 `_COMPACT_PROMPT` 已物理移除）。
- **SA-SD**：anchor 為純搬移非重寫（對照 `git show HEAD` 逐字一致）；語意/時序正確（task/global_goal/last_failure 來源 + compact 諮詢點 execute 後 evaluate 前）；零退化 fallback 親跑實證；Rule 9 測試咬意圖（親跑 MUT-80-1/3 反證）；介面向下相容（新參數全預設）。
- **QA**：親跑複核全部數字相符（3440/0、8 kept、LOC violations=0、snapshot OK）；6 新測真實收集執行（非 skip/xfail）；獨立重做 MUT-80-1 轉紅→Edit 還原復綠（未用 git checkout）；git 潔淨（零碰 SDD/、無 tla/FSM、dry-run 無 pyc）；缺陷帳本無虛報。QA 誠實記錄一次 grep 上下文誤判後以 Read 撤回（zero-trust 雙向紀律）。

無 P0/P1 發現，免修復循環。複審＝三鏡各自親跑驗證已構成複核（QA 獨立重跑全套 + 突變）。

## §8 誠實標記

- **規格先行**：本檔 §1–§3（含 `<Architecture_Design_Review>`/介面 delta/RTM）於**階段二先落地**（寫 code 前），§4/§5/§6 實測欄階段三/四回填——非事後結案報告。
- **誠實級別**：本輪＝**C 軌指揮官 AutoClaude 能力品質強化輪（compact 記憶保留 + 解分層張力 + 閉合上輪誠實限制），非成熟度推進**，`L_合體=min(L5,L5,L5)=L5` 維持。
- **零行為變更 fallback 實證**：腳本驗 `build_compact_prompt(task=None) == 舊 _COMPACT_PROMPT`（逐字）為 True；既有不帶 task 的 4 個 perform_compact 測試零修改全綠。
- **既有測試零修改**：本輪為純函式上移 + additive anchor，無 Rule 9 行為遷移、無更新任何既有測試（對比 improving_79 曾更新 2 既有測試）——173 個 build_compact_prompt 相關 + 12 個 kernel/compactor 既有測試全綠。
- **anchor 語意一致**：移植的是同一純函式（非重寫），anchor 結構（task/attempt/成功條件/global_goal/last_failure）與棄用路徑完全一致；Kernel compact 點 `last_failure_reason` 為前次 attempt 失敗（compact 在 execute 後、evaluate 前），為該時點最佳可得失敗背景，與棄用路徑時序一致（attempt 0 時為空 → anchor 無 [LAST_FAILURE]）。
- **N/A 精確**：AISDLC_SDD ci-gate / 五軌 TLC ＝「條件未觸發、本輪確實未跑」附 git diff 鐵證（`git status --short AISDLC_SDD/` 空、無 `*.tla`/FSM）；DAL 等價 ＝「既有測試隨全套已跑且通過、本輪無新 DAL/checkpoint 契約」（零碰 DAL schema）。
- **承上輪誠實限制（Gap-008-E checkpoint）**：W-78-1 既有 `_persist_halt_checkpoint` 存最小 checkpoint，跨 session 計數器不隨此最小 checkpoint 持久化——本輪未碰持久化路徑，此限制延續、非本輪引入。
