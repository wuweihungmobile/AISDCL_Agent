# AutoSDD_improving_68 — A/C 軌:Claude Agent SDK 執行器整合(SdkExecutorAdapter,雙 adapter 並存可回退)

> **軌道**:① 整合迭代｜**本輪柱位**:**C 軌(指揮官 AutoClaude 執行器能力)× A 軌(同源升級驅動 Claude Code 的橋接)**｜**下一份**:`AutoSDD_improving_69.md`
> **日期**:2026-06-25｜**驅動器**:`AutoSDD_Iteration_Prompt_Template.md`｜**依據**:`docs/02_architecture/Agent_Architecture_Integration_Assessment.md`(四鏡×2輪 + Phase0 spike GO,掌舵者批准開工)
> **本輪性質**:把評估首選「Claude Agent SDK 替換 PtyExecutor」落為可回退的執行器後端切換。**新舊 adapter 並存、預設仍 PtyExecutor → 零行為變更**;SDK 路徑 opt-in。
> **狀態(2026-06-25 完整收斂)**:W-68-1/2/3 三項全交付,階段四全綠(3345/122/0、8 kept、LOC 0、snapshot FRESH、ci-gate exit 0),多鏡審查 PASS。唯 R-68-7 活體 A/B 待網路環境(PENDING,不假裝)。
> **🔴 環境限制(誠實前置)**:本輪「活體 A/B」(真的用 SDK 驅動 Claude Code、實測 Token Guard 先發)需可連 Anthropic API 之環境;本 session 沙箱無外網(spike 實證 WebFetch ECONNREFUSED)。故本輪交付 = **設計 + 實作 + mock 單元測試全綠 + 零退化**;**活體 A/B 驗收明確列為收尾閘,待具網路環境跑,絕不假裝跑過**([[no-fabricated-tool-output]])。

---

## §1 上輪繼承

- **improving_67**(A 軌雙向橋接)已 commit+push(`badcd4a`)。架構評估文件已 commit(`8f5ceef`→`76a710e`),Phase0 spike 裁決 GO。
- **缺陷帳本**:本輪預期無新框架缺陷(純 AutoClaude 側新增 adapter + 純函式)。既有 open/routed 項非本輪 scope。

## §2 階段一零信任重偵察(實測,全錨定本輪 tool 輸出)

| 項目 | 命令 | 結果 | 硬閘 |
|------|------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3327 passed / 122 skipped / 0 failed**(69.82s) | ✅ ＝floor 3327 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | ✅ |
| (c) LOC / snapshot | `check_loc_budget` / `snapshot_sync --check` | **violations=0(total=19054)/ FRESH** | ✅ |
| (d) AISLDC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**(v0.01:1478 / v0.26:1665 / scripts:129) | ✅ |
| (e) claude-agent-sdk | `pip show` / `pip check` | **v0.2.110;依賴 anyio/mcp/sniffio;pip check 乾淨;零測試 import** | ✅ 無干擾 |

**硬閘結論**:基線零退化、不低於上輪 → 准予進入後續階段。

## §3 三軸成熟度現況 + 本輪定位

| 軸 | 現級 | 本輪影響 |
|----|------|---------|
| A 協作 | L5 | 同源升級驅動 Claude Code 的橋接(PTY 文字流→JSON-over-stdio),加固不升級 |
| B 流程 | L5 | 不動 |
| C 引擎 | L5 | 執行器後端可切換、結構化可觀測,加固不升級 |

`L_合體 = L5`(維持——執行器同源升級屬韌性/可觀測性加固,不新增自治能力)。

---

## §4 <Architecture_Design_Review>(寫實質 Python 前必出)

### 4.1 架構純潔性
- **不創 God-object**:新增 `SdkExecutorAdapter`(infra/adapters,實作既有 `IExecutor`,職責單一＝把 SDK 串流橋接成同步 `ExecutionOutput` + emit 五事件);act-first 為 thresholds.py 內**新增一個純函式**,無新類別、無狀態。
- **Thin Facade 維持**:`playbook_runner.py` 零變更;wiring 注入點以 config 選 backend,選擇邏輯薄。
- **複用既有合約**:adapter 實作既有 `IExecutor` protocol(execute/send_interrupt/ExecutionEvent 五種);安全閘**重用既有 `ToolInvocationAdapter`** 接成 SDK `can_use_tool`;不新增 port。

### 4.2 持久化相容
- **零新持久化**。SDK session 限縮在單次 execute 內;跨 step/session SSOT 仍是 PlaybookCheckpoint(無雙寫)。DAL 三後端不受影響(executor 層,非 repository 層)。

### 4.3 安全防護網
- **can_use_tool 接既有 allowlist**:SDK 工具呼叫前必過既有 `ToolInvocationAdapter`(預設 deny + host allowlist + 審計),不發明第二套閘。`permission_mode` 顯式設最小權限(預設 `None`,spike 已證非 acceptEdits),配合 CrossStepValidator git 污染偵測。
- **無新 shell 注入路徑**:adapter 不從文件生成指令;prompt 經既有流程。

### 4.4 對外 I/O 安全
- SDK 底層 spawn Claude Code CLI(JSON-over-stdio,bundled binary),非新增 `ToolInvocationPort` 外呼路徑;對 Anthropic API 的網路 I/O 等同既有 PtyExecutor 驅動 Claude Code(同源,無新威脅類別)。

### 4.5 Token Guard 權威保全(act-first,本輪核心安全設計)
- SDK 內建 autocompact(`isAutoCompactEnabled`/`autoCompactThreshold`);**為保住 AutoClaude 形式化門檻(80% compact / 90% halt)權威**,採 act-first:讀 SDK 可查詢的 `autoCompactThreshold`,驗證 AutoClaude halt 門檻(換算 token 數)**低於**它 → AutoClaude 先 checkpoint/halt,CLI 來不及 autocompact。純函式 `verify_act_first_ordering` fail-closed,完全可單元測試,**不依賴關閉旗標**(第二保險:settings/env 關閉 autocompact,鍵名待活體查)。
  - **本輪實作精度(SA-SD 鏡誠實修正)**:adapter 執行期守門為 **warn-only**(不安全→`logger.warning`,執行照常起;取不到用量則 best-effort 略過不阻斷)。純函式本身 fail-closed(無法判定回 False),但 adapter **尚未把「不安全」升級為硬擋**(拒絕以該設定啟用 sdk 後端)。硬擋屬 improving_69 候選 W 項(需活體確認門檻可靠讀取後再升級,避免誤擋)。

---

## §5 增量設計(W 項 / 介面 delta / LOC 落點)

### W-68-1 — act-first Token Guard 排序純函式(make-or-break,零風險,本輪先做)
- **檔**:`autoclaude/plugins/token_guard/thresholds.py`(現 50 行,data/strategy tier)。
- **新增純函式** `verify_act_first_ordering(*, autocompact_threshold_tokens, max_tokens, halt_pct) -> bool`:回傳「AutoClaude halt 門檻是否先於 SDK autocompact 觸發」(halt_pct/100 * max_tokens < autocompact_threshold_tokens)。供 SdkExecutorAdapter 啟動時驗證、不安全則 fail-closed warn。
- **LOC**:+~12 行(純函式 + docstring)。完全可單元測試(給定門檻值斷言安全/不安全)。

### W-68-2 — SdkExecutorAdapter(實作 IExecutor,mock 測;活體 A/B 待跑)
- **檔**:`autoclaude/infra/adapters/sdk_executor_adapter.py`(新,adapter tier ≤400)。
- **介面**:實作 `execute(prompt, *, maintain_context, timeout, label, on_event) -> ExecutionOutput` + `send_interrupt(reason) -> bool`。
  - 內部以 `ClaudeSDKClient`/`query` 驅動;`anyio` 橋接 async→sync。
  - 串流訊息映射 `on_event`:AssistantMessage text→`partial_output`、ToolUseBlock→`tool_use`、ResultMessage→`token_pct`(取 get_context_usage/usage)+`completion`。
  - `can_use_tool` 接注入的 allowlist 回呼(constructor 注入,不 import infra)。
  - `send_interrupt` 走 SDK interrupt。
- **mock 測試**:mock SDK client 吐 canned 訊息,斷言事件映射 + ExecutionOutput + can_use_tool 被呼叫 + interrupt。
- **🔴 活體 A/B 待跑**:真實驅動 Claude Code 的端到端 + token 門檻先發,列收尾閘(需網路環境)。
- **LOC**:adapter ≤400(估 ~180)。

### W-68-3 — 執行器後端 config 切換 + 選配依賴 + wiring(預設 pty,零行為變更)
- **檔**:`pyproject.toml`(加 `claude-agent-sdk` 為 optional extra,如 `[sdk]`)+ config(加 `executor.backend: "pty"|"sdk"`,**預設 "pty"**)+ `wiring.py`(依 config 選 adapter)。
- **零退化保證**:預設 "pty" → 既有 3327 行為與測試完全不變;SDK 為 opt-in。
- **LOC**:config + wiring 各 +~10 行。

### 不需動的部分(scope 收斂)
- 零碰 FSM / `*.tla` / checkpoint / DAL / ports 數量 / thin facade / AISLDC_SDD 本體 → 免五軌 TLC、免 Copy-on-Evolve。
- 預設 backend 不變 → AutoClaude 3327 結構性零退化。

---

## §6 RTM

| RTM | 需求 | 設計落點 | 驗證(DoD) | 狀態 |
|-----|------|---------|-----------|------|
| R-68-1 | act-first:AutoClaude halt 先於 SDK autocompact(保形式化門檻權威) | W-68-1 `verify_act_first_ordering` | `TestVerifyActFirstOrdering`(5 測:安全/不安全/邊界相等/門檻非正×2,Rule 9 含「不安全必判 False」) | ✅(全套 3332 passed/0 failed 零退化) |
| R-68-2 | SdkExecutorAdapter 結構實作 IExecutor(事件映射) | W-68-2 [sdk_executor_adapter.py](../../AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py) | `test_event_mapping_full_stream` + `test_result_message_is_error_maps_exit_code_1`(mock SDK→斷言 partial_output×2/tool_use/token_pct/completion + ExecutionOutput) | ✅(2 測) |
| R-68-3 | can_use_tool 接注入 allowlist predicate(安全閘不繞過、fail-closed) | W-68-2 `_wrap_can_use_tool` | `test_can_use_tool_predicate_wired_and_consulted` + `_exception_fail_closed` + `_no_predicate_means_no_hook`(predicate 被諮詢、例外→Deny、未注入→None 交 SDK 守門) | ✅(3 測) |
| R-68-4 | send_interrupt 可達 | W-68-2 | `test_send_interrupt_when_not_running_returns_false` + `test_interrupt_at_message_boundary_sets_completed_false`(訊息邊界中斷→interrupt 被呼叫、completed=False、後續訊息不累積) | ✅(2 測) |
| R-68-5 | 後端切換預設 pty 零行為變更 | W-68-3 [main.py:95](../../AutoClaude/autoclaude/main.py) | `test_executor_config_defaults_to_pty` + `test_both_executors_structurally_satisfy_iexecutor` + 全套零退化(預設 pty 不變) | ✅ |
| R-68-6 | 依賴零衝突 | W-68-3 | `pip check` 乾淨(§2e 已證) | ✅ |
| R-68-7 | 活體 A/B:SDK 驅動 Claude Code 端到端 + token 門檻先發 | W-68-2 | **收尾閘:待網路環境活體實測**(本輪據實標 PENDING,不假裝) | ⏸️ PENDING(環境) |

## §7 零退化驗證矩陣(floor = §2 實測)

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3332** / 0 failed(新測試只增不減,預設 pty 不變) | ✅ **3345 passed / 122 skipped / 0 failed**(69.65s;floor 3332 + 12 sdk adapter 測 + 1 隔離契約 parametrize 新例) |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | ✅ **8 kept / 0 broken**(含 sdk_executor 納入 executor-brain isolation) |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過(adapter≤400) | ✅ **violations=0**(total=19344,sdk_executor_adapter ~280 行 < adapter 400) |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | ✅ **OK**(未動 port/plugin 清單;adapter 不入 __init__) |
| AISLDC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0(本輪零 SDD 變更,持平) | ✅ **exit 0**(v0.01:1478 / v0.26:1665 / scripts:129,與階段一基線逐字一致) |
| 活體 A/B | (SDK 驅動 Claude Code) | token 門檻先發、輸出對等 PtyExecutor | ⏸️ PENDING(需網路環境,本輪不假裝) |

---

## §7.1 本輪進度(完整四階段收斂)

> **更新(2026-06-25 續做 session)**:前一 session 為部分結案 checkpoint(僅 W-68-1);本 session 接續完成 **W-68-2 + W-68-3**,補齊階段三實作 + 階段四收斂 + 多鏡審查。三 W 項全交付,改用 mock 收斂(活體 A/B R-68-7 仍 PENDING)。

- **W-68-1 act-first**(前 session):`verify_act_first_ordering` + 5 測試,fail-closed。
- **W-68-2 SdkExecutorAdapter**(本 session):[sdk_executor_adapter.py](../../AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py)(~280 行,adapter tier)實作 IExecutor:串流訊息映射(partial_output/tool_use/token_pct/completion)+ 注入式 can_use_tool(fail-closed)+ 執行期 act-first 守門(從 `get_context_usage()` 取 maxTokens/autoCompactThreshold)+ send_interrupt(訊息邊界)。選配依賴 lazy import + 注入 client_factory → 模組在未裝 [sdk] 下可被測試 import。**12 mock 測全綠**。
- **W-68-3 後端切換**(本 session):`ExecutorConfig(backend=pty|sdk,預設 pty)` + [main.py](../../AutoClaude/autoclaude/main.py) lazy-import sdk 分支 + pyproject `[sdk]` extra。**預設 pty → 零行為變更**(全套 3345 中無一測試引用 sdk 後端)。
- **加固**:sdk_executor_adapter 納入 `.importlinter` executor-brain isolation 雙向契約 + AST 靜態驗證(8 kept / 0 broken)。
- **階段四全項 PASS**:全套 3345/122/0(floor 3332)、lint 8 kept、LOC 0、snapshot FRESH、ci-gate exit 0。**零退化達成**。
- **唯一 PENDING**:R-68-7 活體 A/B(需穩定 Anthropic API 環境;沙箱無外網,據實標 PENDING 不假裝)。

## §8 缺陷 / 延後

- **活體 A/B 收尾閘(R-68-7)**:本 session 沙箱無外網,無法真實驅動 SDK 跑 Claude Code。本輪做到「設計 + adapter + mock 測全綠 + 零退化」;活體驗收待具網路環境跑,**據實標 PENDING,不偽稱完成**(Rule 12 fail loud)。
- **autocompact 關閉鍵名**:act-first(不需此鍵)為主路徑;settings/env 關閉為第二保險,鍵名待活體查官方文件,列 backlog。執行期 act-first 已可運作——`ClaudeSDKClient.get_context_usage()` 回傳的 `ContextUsageResponse` 直接含 `maxTokens`/`autoCompactThreshold`/`percentage`(本輪實測 SDK v0.2.110 型別),adapter 即以此餵 `verify_act_first_ordering`。
- **🔴 設計摩擦(誠實修正 plan §4.3 假設)**:原 §4.3 寫「重用既有 `ToolInvocationAdapter` 接成 SDK `can_use_tool`」——實測型別不對位:`ToolInvocationAdapter.invoke(ToolRequest)` 是 AutoClaude **自身**的 3-kind 對外 I/O 模型(web_search/http_request/send_message,domain allowlist),而 SDK `can_use_tool` 是 gate **Claude Code 工具呼叫**(Bash/Read/Edit/WebFetch… + 任意 input dict)的 async callback。兩者語意不同類。**本輪修正**:adapter 改為注入泛型 `CanUseToolPredicate=(tool_name,input)->bool`,並包成 SDK async `PermissionResultAllow/Deny`(fail-closed);adapter「諮詢注入 predicate」之能力已由 mock 測證實(R-68-3)。main.py sdk 分支本輪以 `can_use_tool=None`(交 SDK `permission_mode="default"` 守門,spike 證安全),**richer domain-allowlist predicate 之 production 接線屬活體 A/B 後續**——因其對真實 tool_name 語意的正確性無法在無外網沙箱驗證,本輪不假裝接好。→ 列 improving_69 A 軌候選 W 項。
- **本輪無新框架缺陷**(純新增 adapter + config + 純函式;AISLDC_SDD 本體零變更)。`can_use_tool` 型別不對位屬本輪計畫文件自身的設計假設修正,非框架缺陷,故不入 Defect_Log,於此誠實留證。
