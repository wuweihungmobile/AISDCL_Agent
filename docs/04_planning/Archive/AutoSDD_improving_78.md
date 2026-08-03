# AutoSDD_improving_78 — C 軌：production Kernel 路徑 token-guard halt 完整接線（揪出 DEF-78-001）+ 真實 token 峰值可觀測

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自我精進）**。下一份＝`AutoSDD_improving_79.md`。
> **定位**：修復跨輪潛伏缺陷 **DEF-78-001**——production 唯一正式路徑（Kernel）**從未接上 token-guard 的 ≥90% halt 編排**，致 halt/checkpoint 在 production 結構性死碼、載具 token 維度恆 0。本輪把 **halt 路徑**完整接線（觀測真實 token% → 決策 → HALT + 真誠 marker → path-aware checkpoint 持久化），使「≥90% halt+checkpoint」在 production 真正生效、且載具讀得到真實峰值。
> **成熟度**：`L_合體 = min(A,B,C)` 維持 **L5**（修復 production 編排缺口、恢復文件宣稱行為，非成熟度推進）。
> **掌舵者拍板（2026-06-26，三問）**：① 本輪標的＝DEF-76-001 production marker；② 揪出 DEF-78-001 後重新切分＝**B 完整接線 token-guard**；③ 落地形態＝**路徑層 + 純 Kernel、halt 先行**（避開 Kernel ≤service-tier LOC + 純狀態機紅線）。
> **B 軌（dogfooding）**：本輪純 AutoClaude C 軌（生產碼 + 測試），**零碰 `AISDLC_SDD/`**（免 Copy-on-Evolve、免五軌 TLC）。

---

## §1 本輪輸入（自 improving_77 繼承）

1. **上輪（improving_77）已完成 W 項**：W-77-1 real-run 路徑 resolve + fail-loud（修 DEF-77-001）、W-77-2 輕量真跑取真實非-token 指標。載具 43 passed、全套 3407/122/0、commit 3931bcf（本輪 DEF-77-002 遺留）已 push。
2. **上輪遞延 / routed**：
   - **DEF-76-001（P2）**：production Kernel 不發 token marker → 載具 token 維度恆 0。原 routed「production marker（仿 W-71-2）」本輪。
   - improving_77 §8 候選：(a) 真跑更長 playbook／per-step 多輪聚合／(b) SD_09 W1 source-sha（~06-29）／(c) W-67-2 producer（需 v0.27）。
3. **缺陷帳本 open / routed**：DEF-01-007（cc-switch GUI P3）／DEF-01-009（LOC watch P3）／DEF-62-001（auto_recovery 註解 P3）／DEF-17-001・DEF-42-001・DEF-35-001（P2 routed C 軌 SD_09 W1）／DEF-76-001（P2 partially-fixed + routed）／**DEF-77-002（P3 fixed@本輪 commit 3931bcf）**。

> **🔴 本輪 scope 對齊掌舵者三段裁示的誠實切分**：掌舵者核准「DEF-76-001 production marker」後，階段二零信任直讀生產碼**揪出 DEF-78-001**——marker 之所以缺，根因是 **production Kernel 路徑根本沒接 token-guard 編排**（≥80% compact / ≥90% halt 全住棄用 PlaybookRunner 路徑）。硬掛靜態 marker＝為死碼偽造訊號（違 fail-loud）。經兩問重新切分，掌舵者裁「B 完整接線 / 路徑層+純 Kernel / halt 先行」。本輪因此**不**做 DEF-76-001 的紙面 marker，而是**修 DEF-78-001 的 halt 子路徑**：真正接線使 ≥90% halt 在 production 生效，marker 隨真實 halt 自然且真誠地印出。**compact 子路徑（≥80% /compact 動作）＝W-78-2 拆執行層 helper，視本輪餘裕誠實評估，未做即明標續 routed。**

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-26，parent 親跑）

| 項目 | 命令 | 實測結果 | 證據 |
|------|------|---------|------|
| AutoClaude 全套 pytest（硬閘基線） | `python -m pytest tests/ -q` | **3407 passed / 122 skipped / 0 failed**（70.18s, exit 0） | bg task bqki2gkuy；= improving_77 結案值，零退化 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | bg task bj3x6ctjy（196 files / 492 deps） |
| 上輪構件存在性 | 開檔核對 | improving_77 兩 helper（`_resolve_invocation_path`/`_load_log_or_raise`）+ 測試存在、DEF-77-001 fixed 屬實 | `tools/ab_compare_backends.py`、`tests/tools/test_ab_compare_backends.py` |
| DEF-77-002 遺留 | `git status` | config.yaml/.env.example/Defect_Log 未 commit → 本輪 housekeeping commit 3931bcf push | — |

### 🔴 DEF-78-001 揪出（階段二零信任直讀生產碼，非採信 agent）

| 事實 | 鐵證（file:line） |
|------|------------------|
| Kernel 呼叫執行器不傳 on_event | `core/kernel.py:177-180`（`execute(full_prompt, maintain_context=, timeout=, label=)`） |
| POST_ATTEMPT payload 無 token_pct | `kernel.py:238-242` → `token_guard/policy.py:158` 取 `token_pct=0.0` → should_halt/should_compact 恆 False |
| Kernel 零消費 request_compact | kernel.py 全檔 grep：僅 :248 消費 request_halt |
| 全 codebase 零 ON_TOKEN_USAGE emit 端 | grep 僅 4 subscriber（含 `checkpoint/_phase_handlers.py:77 save_token_halt`）→ 皆死碼 |
| compact/halt 真實邏輯在棄用路徑 | `prompt_dispatcher.py`（取 `runner: PlaybookRunner`）／`_impl.py:233`（TOKEN_COMPACT）／`_token_halt.py:46`（TOKEN_HALT，僅棄用路徑呼叫） |
| production 主路徑 | `main.py:137-138` `AutoResumeService(kernel,...).run(args.playbook)` → `kernel.run(playbook)`（無 path）；**AutoResumeService 才握 playbook_path** |
| AutoResumeService 已備 halt 處理但從未觸發 | `auto_resume.py:207-225` 處理 `result.halted`，但 production `result.halted` 恆 False（Kernel 從不 HALT on token） |

**結論**：production token 壓力實際全交給 executor 內 act-first 檢查（`sdk_executor_adapter.py:233`）+ Claude Code CLI 自身 autocompact；AutoClaude 編排層 compact/halt 在 Kernel 路徑是 dead code。本缺陷與 DEF-71-001（pty 接線崩潰）/DEF-72-001（prompt 殘缺）同根因家族——**Kernel 遷移長期無 token-guard 覆蓋**。

> **lint-imports / LOC / snapshot / ci-gate / 五軌 TLC**：本輪動 `autoclaude/` 生產碼（core/kernel.py、core/services、core/kernel_state、token observer helper、checkpoint 持久化、測試 fake）但**零碰 `AISDLC_SDD/`**；故 AISDLC_SDD ci-gate 與五軌 TLC ＝ **N/A（git diff 鐵證零碰觸發路徑，階段四附）**；lint-imports/LOC/snapshot 於階段四回填（須維持 8 kept / 0 / FRESH）。

---

## §3 本輪增量設計（W-78-1 halt 完整接線；W-78-2 compact 拆 helper、視餘裕）

### `<Architecture_Design_Review>`

1. **架構純潔性**：
   - Kernel 維持「純 DAG 狀態機、honor resource request」角色——本輪只**新增**：(a) 傳 on_event 觀測 token%、(b) 步驟後 emit ON_TOKEN_USAGE（既有 phase）、(c) 沿用既有 `request_halt → 回傳 HALT` 機制（:248 先例）+ 印真誠 TOKEN_HALT marker。**不**在 Kernel 送 /compact（業務邏輯）——compact 動作拆 W-78-2 執行層 helper。
   - token 觀測抽為**純 helper**（消費 ExecutionEvent → 追蹤 peak），離網可單測。
   - checkpoint 持久化放 **AutoResumeService（Layer 2 coordinator，握 path）**，非純 Kernel——符合「路徑層+純 Kernel」裁示與既有「AutoResumeService 處理 halted/resume」職責。
   - 無 God-object、不破 Thin Facade（playbook_runner 不碰）、plugin 互不 import（不新增 plugin）。
2. **持久化相容**：halt checkpoint 由 AutoResumeService 直接經**注入之 `IStateRepository.save_checkpoint`** 寫入（**非經 CheckpointPlugin**——該 plugin 的 `save_token_halt`（ON_TOKEN_USAGE handler）依賴 payload 帶 `request_halt`+`playbook_path`，本輪 Kernel emit 的 ON_TOKEN_USAGE payload 僅 `{token_pct, step_id, max_retries}`、不帶這些 key，故 EventBus 不會觸發舊 handler 寫檔 → **無雙寫**；舊 `save_token_halt` 在 Kernel 路徑本就死碼，本輪由 AutoResumeService 路徑取代其職責）。additive、DAL 三後端零停機維持；`KernelResult` 補 additive 欄（`halt_step_idx`/`peak_token_pct`，預設值 → 既有呼叫零變更）。
3. **安全防護網**：零新增 CONDITIONAL 指令生成路徑；on_event callback 只讀事件、不生成指令。
4. **對外 I/O 安全**：零新增 `ToolInvocationPort` 外呼路徑；token 觀測讀的是既有 executor 事件流。N/A。

### W-78-1：halt 路徑完整接線（介面 delta）

| 修點 | 檔案 | 介面 delta | 設計 |
|------|------|-----------|------|
| ① token 觀測 helper | 新 `autoclaude/core/_token_observer.py`（或併入 kernel helper） | `class TokenObserver`：`__call__(event)` 消費 ExecutionEvent；`peak_pct` property | SDK：讀 `TOKEN_PCT` 事件 `{pct}`；PTY：`PARTIAL_OUTPUT {text}` → `extract_context_pct(text, patterns)`。無事件 → peak 0（零退化） |
| ② Kernel 觀測 + emit + halt | `core/kernel.py` `_run_step` | `__init__` 新增 optional `token_patterns: list \| None=None`（additive，預設 None→PTY 觀測 no-op、SDK 仍有效） | execute 傳 `on_event=observer`；execute 後 emit `ON_TOKEN_USAGE` payload `{token_pct: peak, step_id, max_retries}`；若回 `request_halt` → `logger.warning("=== STATE: TOKEN_HALT \| [%s] context %.0f%% >= halt 門檻 %.0f%% ===")` + 回 `StepOutcome(HALT, peak=...)` |
| ③ KernelResult 補欄 | `core/kernel_state.py` | `halted_(... , halt_step_idx=None, peak_token_pct=0.0)` additive；`StepOutcome` 補 `peak_token_pct`/halt step | resume 點與峰值由 result 傳至 AutoResumeService |
| ④ halt checkpoint 持久化 | `core/services/auto_resume.py` | `result.halted` 分支：save_checkpoint(path-aware) | 以 `_current_path` + `result.halt_step_idx`/`peak_token_pct` + completed_step_ids 經 state_repo 存最小 halt checkpoint，使既有 resume 迴圈讀得到 |
| ⑤ executor fake 協定一致性 | `tests/helpers/fake_ports.py` + ~7 inline fake | `execute(..., on_event=None)` | 補 keyword（IExecutor 協定本就有）→ Kernel 傳 on_event 不破測 |
| ⑥ 載具誠實 | `tools/ab_compare_backends.py` 註解 | 訂正 DEF-76-001 註解：production 端 TOKEN_HALT marker 本輪起真實存在（halt 路徑） | 載具已解析 TOKEN_HALT，無需改 parse；只更新誠實註解 |

- **語意保證（零退化）**：on_event 為 additive；無 token 事件時 peak=0 → 不觸發 halt → 與今日行為完全一致。既有測試 fake 補 on_event 後簽章相容。
- **誠實邊界**：本輪 marker 只在**真實 token% ≥ halt 門檻**時印（真誠，非靜態偽造）；smoke playbook 過短不觸發 → 載具仍誠實顯示無 halt（非偽 0）。compact_count 維持 0（production 本輪不送 /compact，誠實）。
- **W-78-2（compact 動作）**：≥80% → 步驟後另起 `/compact` execute + TOKEN_COMPACT marker，屬執行/服務層業務邏輯；**視 W-78-1 完成後餘裕與零退化餘量決定是否本輪交付，未做即 §8 明標續 routed**（不無謂延後亦不硬塞致破基線）。

### RTM 需求列（階段三/四回填實測欄）

| RTM-ID | 需求 | 驗證 | 階段 |
|--------|------|------|------|
| RTM-78-1 | TokenObserver 從 SDK TOKEN_PCT / PTY PARTIAL_OUTPUT 正確追蹤 peak、無事件回 0 | 單測 observer（SDK 事件、PTY 文字、空） | 三 |
| RTM-78-2 | Kernel 步驟後 emit ON_TOKEN_USAGE 帶真實 token%，token_guard ≥halt 回 request_halt → Kernel HALT + 印真誠 TOKEN_HALT marker | 單測（高 token% fake executor → HALT + marker；低 token% → ADVANCE 無 marker） | 三 |
| RTM-78-3 | halt 時 AutoResumeService 存 path-aware checkpoint，resume 迴圈讀得到正確 step_idx | 單測（halt result → checkpoint 存於 state_repo，_resolve_start 讀回） | 三 |
| RTM-78-4 | 既有 executor fake 補 on_event 後全套零退化、Kernel 傳 on_event 不破測 | 全套 pytest ≥ 3407 / 0 failed | 三/四 |
| RTM-78-5 | 載具 token 維度誠實——production halt 路徑 marker 真實存在；compact 維度誠實標續 routed（若 W-78-2 未做） | 載具註解 + §8 誠實標 | 四 |

---

## §4 實作與雙重驗證（2026-06-26 完成）

### §4.1 實作明細（W-78-1）
- **新 `autoclaude/core/_token_observer.py`**（`TokenObserver`）：消費 ExecutionEvent；SDK 讀 `TOKEN_PCT {pct}`、PTY 以 `extract_context_pct`（late import utils）解析 `PARTIAL_OUTPUT {text}`；`peak_pct` property。純觀測零副作用。
- **`autoclaude/core/kernel.py`**：import `TokenObserver`；`_run_step`（:177-188）建 observer 傳 `on_event`；execute 後呼新 helper `_consult_token_guard`（:274-299）——`peak_pct<=0` 直接 None（零退化）、否則 emit `ON_TOKEN_USAGE{token_pct,step_id,max_retries}`、`tu.request_halt` 則印 `=== STATE: TOKEN_HALT | [Sxx] context NN% >= halt 門檻 ===` + 回 `StepOutcome(HALT, peak_token_pct=)`；run() HALT 分支傳 `halt_step_idx=step_idx, peak_token_pct=`。
- **`autoclaude/core/kernel_state.py`**：`StepOutcome.peak_token_pct=0.0`；`KernelResult.halt_step_idx=None`/`peak_token_pct=0.0`；`halted_(...)` 補兩 additive 參數（預設值，既有呼叫零變更）。
- **`autoclaude/core/services/auto_resume.py`**：新 helper `_persist_halt_checkpoint`（path-aware 存最小 halt checkpoint，resume 點=halt_step_idx）；run() 加 `if result.halted and result.halt_step_idx is not None:` 觸發（gate 防覆蓋既有/其他 halt 路徑 checkpoint）。直走注入之 `IStateRepository.save_checkpoint`，非經 CheckpointPlugin（無雙寫，見 §3.2）。
- **測試 fake 協定一致性**：`tests/helpers/fake_ports.py` + 6 inline fake + `_template.py` 補 `on_event=None`。
- **`tools/ab_compare_backends.py`**：僅更新 DEF-76-001/78-001 註解（halt 維度 production 轉真值、compact 續待 W-78-2），無 parse 邏輯變更。
- **新測 14**：observer 6（`test_token_observer.py`）+ kernel halt 4（`test_kernel_token_halt.py`，用真 TokenGuardPlugin）+ 持久化 4（`test_auto_resume_halt_persist.py`，含防退化測）。

### §4.2 退化修復（過程誠實）
首次全套跑出 **2 failed**（`test_kernel_resume_multi_halt.py`）——`_persist_halt_checkpoint` 原對**所有** halted 觸發，遇 `halt_step_idx is None`（既有/mock 路徑已自存 checkpoint）退回 step_idx=0 覆蓋了正確 checkpoint → resume 倒回。**修復**＝gate `result.halt_step_idx is not None`（只對本輪新接線的 token-observer halt 生效）+ 補回歸測 `test_halt_without_halt_step_idx_does_not_clobber_existing_checkpoint`。修後全套復綠。

### §4.3 受控突變實證非空殼（序列、Edit 還原、禁 git checkout）
- **MUT-78-1**〔kernel `if tu.request_halt:` → `and False`〕→ `test_high_token_pct_triggers_halt_and_marker` 轉紅（`assert False is True`），Edit 還原復綠。
- **MUT-78-2**〔observer `_observe` 的 `if pct > peak` → `and False`〕→ observer peak 兩測轉紅，Edit 還原復綠。
- **MUT-78-3**〔auto_resume `step_idx = halt_step_idx if … else 0` → `= 0`〕→ 持久化兩測轉紅（`0==1`），Edit 還原復綠。
- `grep MUT-78 autoclaude/` 無殘留；QA 鏡獨立重做 (a)(b) 亦轉紅還原。

---

## §5 零退化驗證矩陣（RTM / SCG-5，階段四回填實測）

| 檢查 | 命令 | 通過條件（floor = improving_77 實測 3407） | 實測 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3407 passed / 0 failed（新測只增不減） | **3421 passed / 122 skipped / 0 failed**（= 3407 + 14 新；parent + QA 鏡各親跑） ✓ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken**（core→utils 合法，未破契約） ✓ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | **violations=0**（kernel.py +40→service≤500 / auto_resume / 新 helper 皆過） ✓ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK — 對齊一致** ✓ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **N/A — 本輪零碰 AISDLC_SDD/**（git diff 鐵證） | **N/A**：`git status --short AISDLC_SDD/` 空輸出（三鏡複核） |
| DAL 等價 | equivalence job | 隨全套通過；halt checkpoint 經既有 save_checkpoint，無新 round-trip 契約 | 隨全套通過、零碰 DAL schema，無新 round-trip 契約（`tests/equivalence/`） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A — 零碰 `*.tla`/FSM**（git diff 鐵證） | **N/A**：git status 無 `*.tla`/FSM 變更 |

---

## §6 缺陷帳本本輪處置（詳見 AutoSDD_Defect_Log.md）

- **DEF-78-001（P2）**：本輪 W-78-1 修 halt 子路徑 → 預期 **partially-fixed@improving_78（halt 接線）+ routed（compact 動作 W-78-2/下輪）**（依本輪是否含 W-78-2 定稿）。
- **DEF-76-001（P2）**：本輪以 DEF-78-001 修復**連帶澄清其 framing**（marker 缺＝編排未接線，非單純漏印）；halt 路徑接線後 production 真實 TOKEN_HALT marker 存在，載具 halt 維度轉真值。compact 維度仍待 W-78-2。
- **DEF-77-002（P3）**：fixed@本輪 commit 3931bcf（housekeeping）。
- 其餘 open/routed（DEF-01-007/01-009/62-001/17-001/42-001/35-001）：本輪未觸碰標的，複驗維持原狀態。

---

## §7 多專家 Zero-Trust 審查（2026-06-26 完成）

三鏡皆**主樹派發**（本輪有 untracked 新檔 _token_observer.py + 3 新測 + 計畫/帳本 → 依 DEF-24-001 禁 worktree；受控突變序列化於實作後單線完成並 Edit 還原）：

- **Architect** — OVERALL PASS（P0=0/P1=0）：Kernel 維持純 DAG（新增屬既有 emit-phase + honor-request_halt 角色，無 /compact 業務邏輯誤入）、分層紅線 8 kept（core→utils 合法 late import）、LOC violations=0、持久化層歸屬正確且**無雙寫**（Kernel emit payload 不帶 request_halt → 舊 save_token_halt 不觸發）、playbook_runner thin facade 未碰。2 P2 觀察（最小 checkpoint 計數器限制已標 / SDK pct float 防禦，無實害）。
- **SA-SD** — OVERALL PASS（P0=0/P1=0；親跑 3421/0）：根因屬實（grep 證改前零 ON_TOKEN_USAGE emit、TOKEN_COMPACT 僅棄用路徑）、halt 接線正確（92%→HALT+marker、50%→前進、85%→compact 區間誠實不動作無 overclaim）、零退化機制成立（peak=0 不 emit）、防退化 gate 無漏洞、測試驗意圖（真 TokenGuardPlugin）、誠實無虛報。2 P2（計畫 §3 措辭「CheckpointPlugin API」訂正＝**已修**；save_token_halt 死碼註記＝**已於 §3.2 補註**）。
- **QA** — OVERALL PASS（P0=0/P1=0）：獨立全套 **3421/122/0**、lint 8 kept、LOC 0、snapshot OK、獨立突變 (a)(b) 轉紅 Edit 還原無殘留、零碰 AISDLC_SDD、無 skip/xfail 規避、退化點 test_kernel_resume_multi_halt 綠、誠實標註三項屬實。

全閉環 PASS，准結案。

---

## §8 誠實標記

- **規格先行**：本檔 §1–§3（含 `<Architecture_Design_Review>`/介面 delta/RTM）於**階段二先落地**（寫 code 前），§4/§5/§7 實測欄階段三/四回填——非事後結案報告。
- **誠實級別**：本輪＝**C 軌指揮官 AutoClaude 缺陷修復輪（修跨輪潛伏 DEF-78-001 之 halt 子路徑），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。
- **halt vs compact 切分誠實**：本輪只接 halt 路徑；compact 動作（≥80% /compact）誠實標 routed W-78-2（架構張力＝屬執行層業務邏輯 + 零退化餘量考量，justified 延後，非無謂延後）。test_compact_threshold_does_not_halt_this_round 正面鎖此邊界，杜絕「compact 已接」overclaim。
- **最小 checkpoint 限制誠實**：halt checkpoint 不持久化跨 session 計數器（goto/inject/skip/evolution，預設空 dict）；核心 resume 資料齊備。已於帳本 + `_persist_halt_checkpoint` docstring 揭露。
- **退化過程誠實**：§4.2 如實記首跑 2 failed 之退化與修復，未隱藏。
- **DEF-78-001 來源誠實**：此缺陷是掌舵者核准 DEF-76-001 marker 後、parent 零信任直讀生產碼坐實 marker 補點時揪出；經三段 AskUserQuestion 重新切分為 B/路徑層+純Kernel/halt先行。
- **scope 誠實**：本輪 halt 先行；compact 動作（W-78-2）視餘裕，未做即明標續 routed（遵 [[no-defer-unless-justified]]：能做當場做、真延後須明說理由＝架構張力 + 零退化餘量）。
- **N/A 精確**：AISDLC_SDD ci-gate / 五軌 TLC ＝「條件未觸發、本輪確實未跑」附 git diff 鐵證。
