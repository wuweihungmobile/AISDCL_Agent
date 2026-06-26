# AutoSDD ZeroTrust Audit 80 — W-80-1 compact prompt memory-anchor 移植

> **輪次**：improving_80（C 軌：指揮官 AutoClaude 能力品質強化）
> **標的**：把純函式 `build_compact_prompt` 從 plugin 上移為 core 共享 SSOT + plugin re-export + Kernel compact 路徑帶 MEMORY ANCHOR，閉合 improving_79 §8「memory-anchor 未移植」誠實限制。
> **審查日期**：2026-06-26
> **結論**：**OVERALL PASS（P0=0 / P1=0）**，准予結案。

---

## 一、階段一 Zero-Trust Re-Audit（parent 親跑 + 背景跑，輸出複核）

| 項目 | 命令 | 實測 | 達標 |
|------|------|------|------|
| AutoClaude 全套 pytest（硬閘基線） | `PYTHONUTF8=1 python -m pytest tests/ -q` | 3434 passed / 122 skipped / 0 failed（69.16s） | ✅ = floor 3434，硬閘未觸發 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken（198 files / 499 deps） | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0（total=19628 / cap=20438） | ✅ |
| Snapshot 新鮮度 | `python tools/snapshot_sync.py --check` | OK 對齊一致 | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | EXIT 0 全綠（v0.01:1478 + v0.26:1665 + scripts/tests:129） | ✅ |
| 上輪構件存在性 | 直讀生產碼 | W-78-2 構件（`_token_compactor.py`/kernel `_handle_compact`/policy `_evaluate_post_compact`/2 新測檔）皆真實存在 | ✅ |

硬閘通過，准進階段二。

## 二、階段四零退化驗證矩陣（parent 親跑）

| 檢查 | 通過條件（floor 3434） | 實測 |
|------|------|------|
| AutoClaude 全套 | ≥ 3434 / 0 failed | **3440 passed / 122 skipped / 0 failed**（= 3434 + 6 新；70.52s） ✓ |
| 架構契約 | kept / 0 broken | **8 kept / 0 broken**（plugin token_guard→core._compact_prompt 合法） ✓ |
| LOC 分級 | 全過 | **violations=0**（total=19660；`_compact_prompt.py` 66 行、`_token_compactor.py` 70 行 data tier；compactor.py 94→52 行） ✓ |
| Snapshot | 新鮮 | **OK** ✓ |
| AISDLC_SDD 閘門 | N/A 零碰 | **N/A**：`git status --short AISDLC_SDD/` 空輸出 |
| DAL 等價 | 隨全套通過 | 隨全套通過、零碰 DAL schema、無新 round-trip 契約 |
| 五軌 TLC | N/A 零碰 *.tla/FSM | **N/A**：git status 無 `*.tla`/FSM 變更 |

## 三、受控突變實證（序列、Edit 還原、禁 git checkout）

| 突變 | 動作 | 結果 |
|------|------|------|
| MUT-80-1 | kernel `_handle_compact` 傳 perform_compact 的 `task=task` → `task=None` | `test_kernel_compact_path_sends_anchor_with_global_goal` 轉紅（production compact prompt 缺 MEMORY ANCHOR）→ Edit 還原復綠 |
| MUT-80-2 | `_token_compactor.perform_compact` 的 `task=task` → `task=None` | 3 anchor 測（perform_compact 帶 anchor / threads last_failure / Kernel 整合）轉紅 → Edit 還原復綠 |
| MUT-80-3 | compactor.py re-export 改本地 wrapper def 破壞 SSOT 同一性 | `test_core_and_plugin_share_single_callable`（`is` 斷言）轉紅 → Edit 還原復綠 |

`grep -rn "MUT-80\|_core_bcp" autoclaude/`（排除 .pyc 快取）無原始碼殘留；還原後 28 相關測復綠。

## 四、多專家三鏡審查（並行、主樹派發）

> 主樹派發理由：本輪有 untracked 新檔（`core/_compact_prompt.py`、`tests/core/test_compact_anchor_migration.py`），依 DEF-24-001「審查 untracked 新檔禁 worktree」紀律；突變已序列完成還原、無並行就地突變，無需隔離。

### 4.1 Architect 鏡 — OVERALL PASS（P0=0 / P1=0）
- **core-purity PASS**：`grep` 證 `_compact_prompt.py`（僅 `__future__` + `typing`）、`_token_compactor.py`（logging/typing/core 內部相對 import）零 plugins/infra import。
- **相依方向合法 PASS**：`lint-imports` 8 kept / 0 broken；.importlinter core-purity（Rule 2）只禁 core→execution/infra，plugin→core 為正常向下依賴，不在任何 contract 禁止範圍。
- **Thin Facade PASS**：`_handle_compact` 只多傳 4 個 anchor 素材、無新增分支/業務邏輯；送 /compact 業務邏輯仍在 core helper；playbook_runner 未碰。
- **SSOT 真實 PASS**：compactor / policy / core 三路徑 `is` 收斂同一物件；`def build_compact_prompt` 全 codebase 僅 `_compact_prompt.py:23` 一處（policy.py:140 為委派 wrapper 非重複實作）。
- **零退化 fallback PASS**：舊 `_COMPACT_PROMPT` 已物理移除（grep 無殘留）；task=None 逐字等價舊七行常數。

### 4.2 SA-SD 鏡 — OVERALL PASS（P0=0 / P1=0）
- **anchor 移植正確 PASS**：對照 `git show HEAD:.../compactor.py` 舊函式 vs `core/_compact_prompt.py`，簽名/anchor 組裝/failure_summary 處理逐字一致——純搬移非重寫；`CompactFailureState`/`process_compact_result` 正確留 compactor.py。
- **語意一致 PASS**：task（kernel.py:323）/ global_goal（:324 playbook.global_goal）/ last_failure（_run_step:207→:191→:304→:325）來源正確；compact 諮詢點 execute(:184) 後 evaluate(:196) 前，attempt 0 時 last_failure="" → anchor 無 [LAST_FAILURE]，語意正確。
- **零退化邊界 PASS**：親跑 `build_compact_prompt(task=None) == 舊 _COMPACT_PROMPT` → True。
- **Rule 9 PASS**：6 測咬行為意圖；親跑 MUT-80-1/3 反證可轉紅。
- **介面契約 PASS**：perform_compact 新參數全預設、向下相容既有 caller/測試。

### 4.3 QA 鏡 — OVERALL PASS（P0=0 / P1=0）
- 親跑複核全部數字相符：pytest `3440 passed, 122 skipped`；lint `8 kept, 0 broken`；LOC `violations=0`；snapshot `OK`。
- 6 新測真實存在、`-v` 跑出 6 passed（非 skip/xfail），名稱對齊 RTM-80-1/2/3。
- 獨立重做 MUT-80-1（kernel `task=task`→`task=None`）→ 轉紅（AssertionError 缺 MEMORY ANCHOR）→ Edit 還原（未用 git checkout）→ 復綠、git diff 無殘留。
- git 潔淨：3 改 + 3 新；`git status --short AISDLC_SDD/` 空；無 tla/FSM；`git add -A -n AutoClaude/` dry-run 僅 5 源碼/測試檔、無 pyc。
- 缺陷帳本誠實：最大編號 DEF-78-001（improving_79），本輪未新增 DEF；計畫書 §6「本輪無新缺陷 + improving_79 §8 閉合非 DEF 條目」誠實。
- **QA 自我更正（誠實留證）**：審查途中曾因 Grep `-C` 上下文片段拼接誤判 kernel.py:324 為 `task=None`，隨後以 Read 兩次確認生產碼為 `task=task` 即撤回誤判，並由突變實證反向印證原碼正確（zero-trust 雙向紀律）。

## 五、複審

三鏡各自親跑驗證（QA 獨立重跑全套 pytest + lint + LOC + snapshot + 突變；Architect/SA-SD 親跑 lint + `is` 同一性 + 逐字等價）已構成複核。無 P0/P1 發現 → 無修復循環需求。

## 六、結案判定

**OVERALL PASS**。W-80-1 以正解相依方向（plugin→core 合法）把純函式上移為 core 共享 SSOT，production Kernel compact 路徑帶 MEMORY ANCHOR，逐字等價 fallback 保零退化，improving_79 §8「memory-anchor 未移植」誠實限制實質閉合。零退化矩陣全綠、三鏡全 PASS、缺陷帳本誠實，准予結案。
