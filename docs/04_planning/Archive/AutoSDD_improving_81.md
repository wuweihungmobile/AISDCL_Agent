# AutoSDD_improving_81 — C 軌：真跑揭露 token% 訊號源盲區（DEF-81-001）+ 載具 fail-loud 護欄

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自我精進）**。下一份＝`AutoSDD_improving_82.md`。
> **定位**：掌舵者拍板的「真跑較長 playbook 取真實 token 差異」**前提被真跑實證推翻**——本輪以 zero-trust 真跑揭露：PTY/SDK 雙 backend 真跑 `peak_token_pct` 皆恆 0、compact/halt 在真實負載**從未觸發**。據此重定向（掌舵者 AskUserQuestion 二次拍板）＝**記缺陷 DEF-81-001 + 載具 fail-loud 護欄**：真跑 `peak=0` 時明確區分「訊號源未產出」vs「真值 0」，杜絕下輪再誤宣稱「production 真跑取到 token 真值」。**不修根因**（訊號源修復＝SDK `get_context_usage` / PTY `--output-format json` 涉跨輪 scope，明標 routed）。
> **成熟度**：`L_合體 = min(A,B,C)` 維持 **L5**（揭露誠實盲區 + 加固量測載具誠實性，非成熟度推進）。
> **掌舵者拍板（2026-06-26）**：① W 項＝真跑取 token 差異（AskUserQuestion 四候選擇此）；② 真跑推翻前提後二次拍板＝記缺陷 + fail-loud 護欄（非「深診 SDK 再修」/「修 PTY」/「遞延改別的 W」）。
> **B 軌（dogfooding）**：本輪純 AutoClaude C 軌（載具碼 + 測試 + 缺陷帳本），**零碰 `AISDLC_SDD/`**（免 Copy-on-Evolve、免五軌 TLC）。

---

## §1 本輪輸入（自 improving_80 繼承）

1. **上輪（improving_80）已完成 W 項**：W-80-1 compact prompt memory-anchor 移植 → `core/_compact_prompt.py` 共享 SSOT + Kernel compact 路徑 anchor enrichment；閉合 improving_79 §8 誠實限制。全套 3440/122/0、commit ad334c2 已 push。
2. **上輪點名候選**：「真跑較長 playbook 取真實 token 差異——halt+compact 雙維度加 compact prompt 內容，現在在 production 真跑都是真值了」。**本輪做（並以真跑驗證該宣稱——結果推翻之，見 §2）。**
3. **缺陷帳本 open/routed（本輪複驗維持，非標的）**：DEF-01-007（cc-switch GUI P3）/DEF-01-009（LOC watch P3）/DEF-19-001（catch 覆蓋 P3 routed）/DEF-23-005（RFC 生命週期 P3 routed）/DEF-17-001・DEF-35-001・DEF-42-001（P2 routed C 軌 SD_09 W1）。

---

## §2 階段一實測（Zero-Trust Re-Audit + 真跑探測，2026-06-26，parent 親跑/派 agent 親跑）

### §2.1 基線硬閘（agent 親跑複核，PASS）

| 項目 | 命令 | 實測 | 達標 |
|------|------|------|------|
| AutoClaude 全套 pytest（硬閘基線） | `python -m pytest tests/ -q` | **3440 passed / 122 skipped / 0 failed**（68.77s） | ✅ = floor 3440，硬閘未觸發 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（199 files / 501 deps） | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total 19660 / cap 20438） | ✅ |
| Snapshot 新鮮度 | `python tools/snapshot_sync.py --check` | **新鮮 OK** | ✅ |
| 上輪構件 | 直讀 | `core/_compact_prompt.py`(66)、`tests/core/test_compact_anchor_migration.py`(153，6 測全 collect) 真實存在 | ✅ |
| 外部工具依賴 (f) | 真跑探測 | claude CLI `v2.1.144` 在 `/c/Users/wuwei/.local/bin/claude` **可用**；身處 `CLAUDE_CODE_CHILD_SESSION` 嵌套環境，subprocess spawn claude **實測可跑通** | 已確認 invocation 形態 |

### §2.2 🔴 真跑探測揭露的重大事實（推翻原 W 項前提）

> 階段一 (f) 紀律（DEF-10-002a：勿假設可 headless 自動化）→ 做最小真跑探測。在 scratchpad 臨時工作目錄真跑既有 `scripts/sdd_bridge_smoke.yaml`（2 步），pty + sdk 雙 backend 各一次。

| 事實 | 鐵證（命令輸出 / file:line） |
|------|----------------------------|
| 真跑在 child session **可行**（雙 backend） | 二者皆 `KernelResult(success=True, completed_steps=2, total_steps=2, reason='success')`、真建 `smoke_add.py`+`smoke_add_test.py`、evaluator 真跑 `pytest ... [exit=0]` |
| **PTY 真跑 token% 恆 0** | `KernelResult(... peak_token_pct=0.0)`；claude `-p` 純文字輸出（playbook_S01.log：`Created ... [TEST_READY]`）不含 context%；`extract_context_pct` 6 regex 無從抓（`utils/token_tracker.py:20-34`） |
| **SDK 真跑 token% 也恆 0** | `KernelResult(... peak_token_pct=0.0)`；SDK 真走 SDK 路徑（log:2「執行器後端：Claude Agent SDK」）但**全程無 `TOKEN_PCT` log**；`_emit_token_pct` 在 `get_context_usage().percentage` 取不到時**靜默跳過**（`infra/adapters/sdk_executor_adapter.py:276`，else 不 emit） |
| **結論：上輪「production 真跑都是真值了」宣稱從未被真實負載驗證** | improving_76~80 接的全是**下游**（marker emit 鏈 `kernel.py:297/335`、`_token_compactor.py:58` + decision 邏輯 + anchor）；**最上游 token% 訊號在兩 backend 真跑皆未產出**，compact(≥80%)/halt(≥90%) 在任何真跑下從未真實觸發。此為 DEF-76-001 家族的**最終根因**：歷輪修下游接線，訊號源頭在真跑中始終是乾的 |

### §2.3 載具 parse 邏輯實況（護欄設計依據）

- `tools/ab_compare_backends.py:160-180` `parse_run_metrics`：`peak_token_pct` **只掃含 `TOKEN_COMPACT`/`TOKEN_HALT` 的行**（line 165 `continue`）→ peak 來自「達門檻才印的 marker 行」，無 marker 即 0。
- `_RE_FIELD_INT`/`_RE_FIELD_BOOL`（line 47-55）：自 KernelResult blob 取 completed/total/success/escalated/halted——**但未解析 `peak_token_pct`**（observer 層真值，production `kernel.py` 真印於 KernelResult 行）。
- **判據（零歧義）**：context% = used/max，只要 observer 真在運作 peak 必 > 0（即使 1%）；`KernelResult.peak_token_pct == 0.0` 嚴格意味 observer **從未收到任何可解析 token% 事件 = 訊號源未產出**（非「context 真的 0%」）。

> **校正**：SDD 最新演化版 v0.26（非 SDD-ROUTER 提示預設 0.18）。本輪零碰 `AISDLC_SDD/`，不受影響。

---

## §3 本輪增量設計（W-81-1：DEF-81-001 入帳 + 載具 fail-loud 訊號源護欄）

### `<Architecture_Design_Review>`

1. **架構純潔性（無 God-object / Thin Facade 不破）**：護欄**100% 落在載具** `tools/ab_compare_backends.py`（純 log 解析工具，非 production 執行路徑）。新增解析 KernelResult 既有 `peak_token_pct` 欄位 + `token_signal_observed` 判定 + 報告渲染標記。**零碰** `autoclaude/`（core/infra/plugins/execution）任何 production 碼、零碰 executor/observer、零新增 plugin/port。Kernel 純 DAG 不動。
2. **持久化相容**：零碰 checkpoint / DAL。RunMetrics/AggregateMetrics 為**載具內部 dataclass**（非持久化模型），新增欄位 additive（預設值），不影響任何序列化。
3. **安全防護網**：零新增 CONDITIONAL 指令生成路徑、零從文件生成指令。純讀取既有 log 文字、regex 解析。
4. **對外 I/O 安全**：零新增 `ToolInvocationPort` 外呼路徑。N/A。

### W-81-1 介面 delta

| 修點 | 檔案 | 介面 delta | 設計 |
|------|------|-----------|------|
| ① RunMetrics 加 observer 真值欄 + 訊號判定 | `tools/ab_compare_backends.py` | `RunMetrics` 加 `observer_peak_token_pct: float = 0.0`（additive）；加 `token_signal_observed` property = `observer_peak_token_pct > 0.0 or peak_token_pct > 0.0` | observer 層真值（KernelResult）或載具掃到 marker 行 % → 任一 > 0 即「有訊號」。預設 0.0 → 真跑無訊號時 property=False（fail-loud） |
| ② parse 解析 KernelResult.peak_token_pct | `parse_run_metrics`（`tools/ab_compare_backends.py`） | 新增 `_RE_FIELD_FLOAT = {"peak_token_pct": re.compile(r"peak_token_pct=(\d+(?:\.\d+)?)")}`；自 kr_blob 解析 → `m.observer_peak_token_pct` | 錨 production KernelResult 真實輸出（`kernel.py` 印）；無 KernelResult 行（半途 log）→ 維持 0.0 = 無訊號（誠實）|
| ③ AggregateMetrics 加訊號計數 | `tools/ab_compare_backends.py` | `AggregateMetrics` 加 `token_signal_observed_count: int = 0`（additive） | 多輪報告也能標：N 輪中幾輪有 token 訊號 |
| ④ aggregate_runs 聚合訊號計數 | `aggregate_runs` | `agg.token_signal_observed_count = sum(1 for r in runs if r.token_signal_observed)` | additive 一行，不動既有聚合 |
| ⑤ 單輪報告 fail-loud 渲染 | `format_comparison` | token 峰值列：`not token_signal_observed` → 渲染 `0%（⚠ 訊號源未產出，非真值）`；另加「token 訊號源」狀態列（已觀測/未產出） | 杜絕裸 `0%` 被誤讀為「context 真的 0%」 |
| ⑥ 多輪報告 fail-loud 渲染 | `format_aggregate_comparison` | token 峰值列：`token_signal_observed_count == 0` → 加 `（⚠ N 輪皆無訊號）`標記 | 多輪真跑同樣不被誤宣稱取到真值 |

- **語意保證（零退化）**：
  - `observer_peak_token_pct` 預設 0.0、property 純讀——既有 43 個載具測試斷言的欄位（peak_token_pct/compact_count/...）全不變，不破。
  - `format_comparison`/`format_aggregate_comparison` 對「有訊號」（peak>0 或 observer>0）路徑渲染**完全不變**（僅 `not signal` 分支新增標記）→ 既有 format 測試（若斷言有訊號樣本）不破；新增「無訊號」標記為新行為，由新測涵蓋。
  - 零碰 `autoclaude/` → 全套 pytest production 測試零影響。
- **誠實邊界**：本輪護欄解決的是「**載具/報告層**誤把訊號源缺失呈現為 token 真值 0」。**不修訊號源根因**（PTY claude -p 不吐 context% / SDK get_context_usage 無 percentage）→ 明標 DEF-81-001 routed 下輪。護欄使「訊號源未產出」在報告層 fail-loud 可見，即達掌舵者「杜絕下輪再誤宣稱取到真值」之意圖。

### RTM 需求列（階段三/四回填實測欄）

| RTM-ID | 需求 | 驗證 | 階段 |
|--------|------|------|------|
| RTM-81-1 | `parse_run_metrics` 解析 KernelResult `peak_token_pct` → `observer_peak_token_pct`；blob 無此欄/半途 log → 0.0 | 單測（含 peak_token_pct=0.0 / =12.5 / 無 KernelResult 三情形） | 三 |
| RTM-81-2 | `token_signal_observed`：observer>0 或 marker peak>0 → True；皆 0 → False | 單測（四象限：observer 有/無 × marker 有/無） | 三 |
| RTM-81-3 | `format_comparison`：無訊號 → token 峰值列標「⚠ 訊號源未產出」+ 訊號源狀態列；有訊號 → 渲染不變（零退化） | 單測（無訊號標記出現 / 有訊號樣本渲染與舊版一致） | 三 |
| RTM-81-4 | `aggregate_runs` + `format_aggregate_comparison`：`token_signal_observed_count` 聚合正確；全無訊號多輪標「N 輪皆無訊號」 | 單測 | 三 |
| RTM-81-5 | DEF-81-001 入帳（P 級 + 雙 backend 真跑鐵證 + routed 根因修復）；improving_80 候選「真跑取真值」前提推翻記錄誠實標 | §6 缺陷帳本 + §8 | 四 |
| RTM-81-6 | 零退化：既有 43 載具測試全綠；全套 pytest ≥ 3440 / 0 failed；新測只增不減；lint 8 kept / LOC 0 / snapshot 新鮮 | 全套 pytest + lint + LOC + snapshot | 三/四 |

---

## §4 實作與雙重驗證（2026-06-26 完成）

### §4.1 實作明細（W-81-1，全落 `tools/ab_compare_backends.py` 載具，零碰 `autoclaude/`）
- **新 `_RE_FIELD_FLOAT`**（regex `peak_token_pct=(\d+(?:\.\d+)?)`）：解析 production KernelResult 印的 observer 層真值。
- **`RunMetrics`**：加 `observer_peak_token_pct: float = 0.0`（additive）+ `token_signal_observed` property（`observer_peak_token_pct > 0.0 or peak_token_pct > 0.0`）。
- **`parse_run_metrics`**：自 kr_blob 解析 `peak_token_pct` → `m.observer_peak_token_pct`（**不覆寫**載具自掃 marker 行的 `m.peak_token_pct`，兩者不同來源；無 KernelResult/半途 log → 維持 0.0 = 無訊號）。
- **`_fmt_token_peak` helper**：訊號源未產出（`not token_signal_observed`）→ 渲染 `0%（⚠ 訊號源未產出，非真值）`，否則照常 `{peak}%`。
- **`format_comparison`**：token 峰值列改用 `_fmt_token_peak`；新增「token 訊號源（W-81-1）」狀態列（已觀測/未產出）。
- **`AggregateMetrics`**：加 `token_signal_observed_count: int = 0`（additive）。
- **`aggregate_runs`**：`agg.token_signal_observed_count = sum(1 for r in runs if r.token_signal_observed)`。
- **`format_aggregate_comparison`**：新增巢狀 `_fmt_agg_token_peak`（N 輪皆無訊號 → 標「⚠ N 輪皆無訊號」）+「token 訊號源 (有訊號輪數 / N)」狀態列。
- **新測 9**（`tests/tools/test_ab_compare_backends.py`，43→52）：RTM-81-1 parse observer 真值 2（解析正確 + 不覆寫 marker peak + 半途 log 0.0）；RTM-81-2 訊號判定 3（雙 0→False / observer>0→True / marker→True）；RTM-81-3 單輪 format 2（無訊號標警示 + 有訊號零退化渲染不變）；RTM-81-4 aggregate 2（訊號計數 + 多輪皆無訊號標記）。
- **LOC**：載具 463→約 490 行，落 absolute tier ≤750（tools/ 未匹配特定 tier，預設 750）；`check_loc_budget` violations=0。

### §4.2 既有測試影響（零修改，全綠回歸鎖）
- 既有 43 載具測試**零修改全綠**：新增欄位皆 additive（預設 0.0/0）、property 純讀、format 「有訊號」路徑渲染不變（僅 `not signal` 新分支）。
- 既有 `_PERFECT`/`_ESCALATED` blob 不含 `peak_token_pct=` → `observer_peak_token_pct` 取預設 0.0、無 marker → `token_signal_observed=False`；既有 format 測試未斷言裸 "0%" 字串故不破（43 passed 實證）。
- 零碰 `autoclaude/` production 碼 → 全套其餘 production 測試零影響。

### §4.3 受控突變實證非空殼（序列、Edit 還原、禁 git checkout）
- **MUT-81-1**〔`token_signal_observed` 的 `> 0.0` → `>= 0.0`（恆 True）〕→ `test_rtm_81_2_signal_absent` 等 **4 測轉紅**，Edit 還原復綠。
- **MUT-81-2**〔parse 的 `m.observer_peak_token_pct = float(...)` → `= 0.0`（不寫真值）〕→ RTM-81-1/81-2/81-4 **3 測轉紅**，Edit 還原復綠。
- **MUT-81-3**〔`_fmt_token_peak` 的 `if not m.token_signal_observed:` → `if False:`（fail-loud 失效）〕→ `test_rtm_81_3_format_flags_absent` **轉紅**，Edit 還原復綠。
- `grep -nE "MUT-81|if False|>= 0\.0 or"` 無原始碼殘留；還原後 52 測全綠。

## §5 零退化驗證矩陣（RTM / SCG-5，階段四回填實測）

| 檢查 | 命令 | 通過條件（floor = improving_80 實測 3440） | 實測 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3440 passed / 0 failed（新測只增不減） | **3449 passed / 122 skipped / 0 failed**（= 3440 + 9 新；69.37s） ✓ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken** ✓ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過（載具 absolute tier ≤750） | **violations=0**（total 19660 / cap 20438） ✓ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK — 對齊一致** ✓ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **N/A — 零碰 AISDLC_SDD/**（git diff 鐵證） | **N/A**：`git status --short AISDLC_SDD/` 空輸出 |
| DAL 等價 | equivalence job | 隨全套通過；無新 DAL/checkpoint 改動 | 隨全套通過（`tests/equivalence/`）、零碰 DAL，無新 round-trip 契約 |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A — 零碰 `*.tla`/FSM**（git diff 鐵證） | **N/A**：`git status` 無 `*.tla`/FSM 變更 |

## §6 缺陷帳本本輪處置（詳見 AutoSDD_Defect_Log.md）

- **新增 DEF-81-001（P2，open routed）**：真跑 token% 訊號源盲區——PTY（claude `-p` 純文字不吐 context%）/SDK（`get_context_usage().percentage` 取不到時 `_emit_token_pct` 靜默跳過）雙 backend 真跑 `KernelResult.peak_token_pct` 皆恆 0、compact(≥80%)/halt(≥90%) 在真實負載**從未觸發**。為 DEF-76-001 家族的最終根因（improving_76~80 接的是下游 marker/decision，上游訊號源真跑為乾）。**本輪處置**：載具加 fail-loud 護欄（報告層區分「訊號源未產出」vs「真值 0」）→ 杜絕誤宣稱；**根因修復（訊號源接線）routed 下輪**（PTY `--output-format json` 取 usage / SDK `get_context_usage` schema 診斷）。嚴重度 P2 理由：核心編排機制真跑空轉，但 (a) 每 step claude -p 為獨立短上下文、單次爆 context 機率低；(b) SDK 模式有原生 autocompact 兜底（`_verify_act_first` act-first 守門確保排序）——有事實兜底、非全無防護；屬長期潛伏非本輪引入退化。
- **缺陷帳本既有 open/routed**（DEF-01-007/01-009/19-001/23-005/17-001/35-001/42-001）：本輪未觸碰標的，複驗維持原狀態。

## §7 多專家 Zero-Trust 審查（完成，詳見 AutoSDD_ZeroTrust_Audit_81.md）

三鏡並行（主樹派發——本輪有 untracked 新檔 docs + 改 tracked 載具/測試，依 DEF-24-001 禁 worktree；突變已序列完成還原、無並行突變）全數 **OVERALL PASS（P0=0 / P1=0）**（回填於 §7 審計報告）。

## §8 誠實標記

- **規格先行**：本檔 §1–§3（含 `<Architecture_Design_Review>`/介面 delta/RTM）於**階段二先落地**（寫 code 前），§4/§5/§6 實測欄階段三/四回填——非事後結案報告。
- **誠實級別**：本輪＝**C 軌指揮官 AutoClaude 量測載具誠實性加固 + 揭露長期潛伏盲區（DEF-81-001）**，非成熟度推進，`L_合體=min(L5,L5,L5)=L5` 維持。
- **🔴 最重要誠實標記——推翻上輪宣稱**：improving_80 結案語「halt+compact 兩維度在 production 真跑都是真值了」**經本輪真跑實證為不成立**：雙 backend 真跑 token% 訊號源皆未產出、compact/halt 從未真實觸發。歷輪（71~80）的「production 真跑為真值」宣稱僅涵蓋下游 marker emit 與 decision 邏輯，**最上游訊號源從未在真跑流動**。此為 zero-trust 真跑（非採信文件宣稱）的直接成果。
- **不修根因之明示**：本輪**僅做報告層 fail-loud 護欄**，不修訊號源根因（掌舵者拍板）；DEF-81-001 根因修復明標 routed 下輪。護欄使「訊號源未產出」在報告層可見即達「杜絕下輪再誤宣稱取到真值」之意圖。
- **零退化 + 零碰 production**：全落載具（純 log 解析工具）；既有 43 載具測試零修改全綠、全套 3449/0、零碰 `autoclaude/` 與 `AISDLC_SDD/`（git diff 鐵證）。
- **N/A 精確**：AISDLC_SDD ci-gate / 五軌 TLC ＝「條件未觸發、本輪確實未跑」附 git diff 鐵證（`git status --short AISDLC_SDD/` 空、無 `*.tla`/FSM）；DAL 等價 ＝「既有測試隨全套已跑且通過、本輪無新 DAL/checkpoint 契約」（零碰 DAL）。
- **真跑探測誠實邊界**：本輪真跑限於 smoke（2 步）雙 backend 各一次（child session 環境實證可跑通）；未跑「較長 playbook ≥10 步」——因真跑已在 smoke 階段即揭露訊號源恆 0 的根本盲區，較長 playbook 不會改變此結論（訊號源缺失與 playbook 長度無關），故無須耗 token 跑長 playbook，scope 收斂至護欄。
