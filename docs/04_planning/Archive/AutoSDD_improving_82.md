# AutoSDD_improving_82 — C 軌：DEF-81-001 訊號源根因修復（PTY token% 真接線 + SDK 盲區可觀測化）

> **本輪定位**：軌道① 整合迭代第 82 輪。**柱別＝C 軌（指揮官 AutoClaude 自身能力）**。
> **下一份檔名**：`AutoSDD_improving_83.md`。
> **掌舵者拍板**：本輪主軸＝**修 DEF-81-001 根因**（動 `autoclaude/infra/` 生產碼，前 5 輪「零碰 production」後第一次真動生產碼）。
> **框架版**：維持 v0.26（本輪零碰 AISDLC_SDD 框架本體）。**成熟度**：維持 L_合體 L5。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_81 遺留
- **已完成**：W-81-1 載具 fail-loud 護欄（`observer_peak_token_pct` + `token_signal_observed` property + `_fmt_token_peak` 區分「訊號源未產出」vs「真值 0」）。
- **明確 routed 本輪**：DEF-81-001 的**訊號源接線根因**（PTY `claude -p --output-format json` 取 usage 算 context% / SDK `get_context_usage` schema 診斷）——需動 `autoclaude/` infra 生產碼，improving_81 justified 延後至本輪。

### 1.2 Defect_Log open / routed 處置計畫
| 缺陷 | 狀態 | 本輪處置 |
|------|------|---------|
| **DEF-81-001**（P2，訊號源根因） | partially-fixed（載具護欄）+ routed（根因） | **本輪推進**：PTY 路徑真接線（升為 fixed 之 PTY 子路徑）；SDK 路徑 fail-loud 可觀測化（盲區可見）。SDK 真值接線（需真跑取 SDK usage schema）誠實續 routed。 |
| DEF-62-001（P3，註解滯後） | open(routed) | 非本輪 C 軌 scope，維持 routed。 |
| DEF-19-001 / DEF-23-005 / DEF-30-001 家族 / DEF-32-002（P3） | routed | 非本輪 scope，維持 routed。 |

### 1.3 上輪 QA 複審延後條目
- 無新「延後」條目進本輪（improving_81 三鏡 OVERALL PASS，P0=0/P1=0）。SA-SD 措辭訂正已當輪閉合。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-26 本輪親跑）

### 2.1 零退化基線（硬閘：floor = improving_81 實測 3449 passed / 0 failed）
| 檢查 | 命令 | 實測 | 上輪基線 | 達標 |
|------|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3449 passed / 0 failed / 122 skipped** | 3449 / 0 | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | 8 / 0 | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19660 / cap=20438） | 0 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | **OK（fresh）** | fresh | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **PASS**（v0.01 1478 + v0.26 1665 + scripts 129，0 failed，arch_fitness fail=0） | PASS | ✅ |

**硬閘通過**，准進階段二。

### 2.2 根因碼路徑偵察（file:line 鐵證）
- **PTY（DEF-81-001 支(1)）**：[pty_executor.py:66-69](../../AutoClaude/autoclaude/infra/adapters/pty_executor.py#L66-L69) 固定組 `claude -p prompt`，**無 `--output-format`**；逐行 readline → emit `PARTIAL_OUTPUT`；`text` = 全行串接（下游 `expected_output_regex` 比對對象）。`TokenObserver` 靠 [token_tracker.py:20-35](../../AutoClaude/autoclaude/utils/token_tracker.py#L20-L35) 6 條 regex 掃純文字 → 無 context% → 恆 None → peak 恆 0。
- **SDK（DEF-81-001 支(2)）**：[sdk_executor_adapter.py:264-282](../../AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py#L264-L282) `_emit_token_pct` 在 `usage.get("percentage") is None` 時**靜默 return**（不 emit、不 log）→ 真跑全程無 `TOKEN_PCT`。
- **載具**：[ab_compare_backends.py:110-118](../../AutoClaude/tools/ab_compare_backends.py#L110-L118) `token_signal_observed` + [:227-234](../../AutoClaude/tools/ab_compare_backends.py#L227-L234) fail-loud 渲染就緒；真跑入口 `run_backend`（subprocess `python -m autoclaude playbook --fresh --config`）。

### 2.3 claude CLI JSON 真實結構（parent 親跑取證，非採信偵察推測）
`claude --version` = **2.1.144**。`claude -p "..." --output-format json` 實測結構（**無 `percentage` 欄，偵察推測被推翻**）：
```json
{"type":"result","subtype":"success","result":"ok",
 "usage":{"input_tokens":6,"cache_creation_input_tokens":37121,"cache_read_input_tokens":21676,"output_tokens":6,...},
 "modelUsage":{"claude-haiku-4-5-...":{"...":...,"contextWindow":200000},
               "claude-opus-4-7[1m]":{"input...":6,"cacheRead...":21676,"cacheCreation...":37121,"contextWindow":1000000,...}}}
```
**可算 context%**：`(input_tokens + cache_read_input_tokens + cache_creation_input_tokens) / max(modelUsage[*].contextWindow) × 100`。實測樣本 ≈ (6+21676+37121)/1000000 ≈ **5.88%**（真實非 0）。`result` 欄 = 答案文字（下游 regex 比對對象，可無損還原）。

---

## §3 本輪增量設計（規格先行）

### 3.1 W 項總覽（≤3）
| W 項 | 標的檔 | tier / budget | 性質 |
|------|--------|--------------|------|
| **W-82-1** | `autoclaude/utils/token_tracker.py`（現 136 行，落絕對紅線 750） | utils → ≤750 | 新增 context% 計算 SSOT 純函式 |
| **W-82-2** | `autoclaude/infra/adapters/pty_executor.py`（現 142 行）+ `autoclaude/utils/config.py`（ClaudeConfig 加欄） | adapter ≤400 / data | PTY 接 `--output-format json` 取真 context%（fail-loud fallback 保零退化） |
| **W-82-3** | `autoclaude/infra/adapters/sdk_executor_adapter.py`（現 ~319 行） | adapter ≤400 | SDK `_emit_token_pct` fail-loud 化（盲區可觀測） |

### 3.2 介面 delta

**W-82-1**（`token_tracker.py` 新增純函式，無副作用）：
```python
def context_pct_from_claude_json(parsed: dict) -> Optional[float]:
    """從 `claude -p --output-format json` 結果推算 context 使用率（0-100，近似）。

    used  = usage.input_tokens + cache_read_input_tokens + cache_creation_input_tokens
    window = max(modelUsage[*].contextWindow)
    pct   = clamp(used / window * 100, 0, 100)
    缺 usage/modelUsage、used<=0 或 window<=0 → None（訊號源未產出，由上游 fail-loud 處理）。
    🔴 誠實邊界：此為近似 context%（claude JSON 無直接 percentage 欄），非 claude 自報值。
    """
```

**W-82-2**（`ClaudeConfig` 加 additive 欄 + `PtyExecutor.execute` 接線）：
- `ClaudeConfig` 新增 `output_format: str = "json"`（預設 "json"＝啟用真接線；設 `""` 退回純文字舊行為，向後相容開關）。
- `execute()`：`output_format` 非空時 args 插 `["--output-format", fmt]`；收集行結束後，`fmt=="json"` 且 raw 非空 → 容錯 `json.loads`：
  - 成功 → `text = parsed.get("result", raw)`（還原答案文字，零退化）；`context_pct_from_claude_json(parsed)` 得 pct 且 `on_event` 存在 → emit `TOKEN_PCT {"pct": pct}`（在 COMPLETION 之前）。
  - 失敗 → `logger.warning(...)` fail-loud；`text = raw`（退回原始輸出＝舊行為）。

**W-82-3**（`sdk_executor_adapter._emit_token_pct` fail-loud）：
```python
        usage = ... # get_context_usage()
        pct = usage.get("percentage") if isinstance(usage, dict) else None
        if pct is not None:
            self._emit(on_event, TOKEN_PCT, {"pct": float(pct)}, seq)
        else:
            logger.warning("SDK get_context_usage 無 percentage 欄，token% 訊號源未產出（DEF-81-001 SDK 支）；usage keys=%s",
                           sorted(usage.keys()) if isinstance(usage, dict) else type(usage).__name__)
```
（取 usage 例外的 `except` 分支亦補 warning；不硬算 fallback——未真跑取得 SDK usage schema，硬算＝推測。）

### 3.3 LOC 預算落點
- `token_tracker.py`：136 → ~175（+~39），落絕對紅線 750 ✅。
- `pty_executor.py`：142 → ~178（+~36），adapter ≤400 ✅。
- `sdk_executor_adapter.py`：~319 → ~327（+~8 log），adapter ≤400 ✅。
- `config.py`：+1 欄位，data tier（models/ports）不涉；config.py 本身不在 tier pattern → ≤750 ✅。

### 3.4 `.importlinter` 各 contract 影響分析
- Rule 1（plugins 互不 import）：不涉。
- Rule 2（core 不依賴 execution/infra）：不涉（改的是 infra/adapters + utils）。
- Rule 4/5（Brain/Executor 互不 import）：W-82-2/3 改的是 executor adapter，**不** import brain；W-82-1 純函式無相依。✅
- 其餘 Rule 3/6/7/8：不涉。
- **預期 8 kept / 0 broken 不變**（adapter import utils.token_tracker 為既有合法路徑，`_token_observer` 已有先例）。

### 3.5 checkpoint additive 欄位需求
- **無**。`peak_token_pct` 既有欄位語意不變，本輪只讓真跑時有非 0 值流入。

### 3.6 RTM 需求列（SCG-5 載體；測試名待階段三落地對齊）
| RTM-ID | 需求 | 驗證測試（暫定名） |
|--------|------|------------------|
| RTM-82-1 | context% 純函式對真實 JSON 樣本算出正確近似值 | `test_context_pct_from_real_claude_json` |
| RTM-82-2 | 多模型取最大 contextWindow | `test_context_pct_uses_max_context_window` |
| RTM-82-3 | 缺 usage/modelUsage / window<=0 / used<=0 → None | `test_context_pct_none_on_missing_fields` |
| RTM-82-4 | pct clamp 至 [0,100] | `test_context_pct_clamped` |
| RTM-82-5 | PTY json 模式：parse 成功 emit TOKEN_PCT 且 text=result | `test_pty_json_emits_token_pct_and_unwraps_result` |
| RTM-82-6 | PTY json parse 失敗 → fail-loud fallback 退回原文、不 emit | `test_pty_json_parse_failure_failloud_fallback` |
| RTM-82-7 | `--output-format json` 進 args；`output_format=""` 時退回純文字（不加參數/不 parse） | `test_pty_output_format_in_args_by_default` + `test_pty_output_format_disable_switch` |
| RTM-82-8 | 既有 PTY 行為零退化（mock 非 JSON 走 fallback 全綠） | 既有 `test_pty_executor.py` 全數 + `test_pty_json_no_token_pct_when_usage_missing` |
| RTM-82-9 | SDK `_emit_token_pct` percentage None → 不 emit 但 log warning（盲區可見） | `test_emit_token_pct_warns_when_percentage_missing` |
| RTM-82-10 | SDK percentage 有值 → 照常 emit（零退化） | `test_emit_token_pct_emitted_when_percentage_present` + 既有 SDK adapter 測試 |
| RTM-82-11 | 真跑驗證：PTY json 模式 token% > 0（訊號源已流動） | §4.2 端到端真跑（KernelResult.peak_token_pct=6.2128%） |
| W-82-4（真跑揭露增量） | 成功 run（未觸門檻）KernelResult.peak_token_pct 端到端帶真值 + 無訊號零退化 | `test_success_run_carries_peak_token_pct_end_to_end` + `test_success_run_no_token_signal_peak_stays_zero` |
| DEF-82-001（載具修） | 報表 fail-loud ⚠ 在 cp950 console 不炸 | `test_main_parse_mode_renders_failloud_on_cp950_stdout` |

> **SA-SD P3-1 校正（結案回填）**：上表測試名於階段三實作落地後已對齊實際名（原 §3.6 暫定名 `test_sdk_emit_token_pct_warns_on_missing_percentage` 等已更新），杜絕 DEF-23-005 家族「改名後未回掃 RTM」復發。

---

## §4 實作與雙重驗證（階段三/四實測回填）

### 4.1 實作落地（四項；W-82-4 為真跑揭露的當輪增量）
| W 項 | 落地 | 單測 | 受控突變 |
|------|------|------|---------|
| **W-82-1** | `token_tracker.py` `context_pct_from_claude_json()`（近似 context% 純函式） | `test_token_regex.py::TestContextPctFromClaudeJson` 9 case | **MUT-82-1**（漏 ×100）→ 2 紅 → Edit 還原 |
| **W-82-2** | `pty_executor.py` 接 `--output-format json`（parse→result 還原+emit TOKEN_PCT；fail-loud fallback）+ `ClaudeConfig.output_format="json"` | `test_pty_executor.py::TestPtyExecutorJsonTokenPct` 5 case + 既有 7 全綠（fallback 零退化） | **MUT-82-2**（`if False` 不 emit）→ 1 紅 → 還原 |
| **W-82-3** | `sdk_executor_adapter._emit_token_pct` fail-loud 化（percentage 缺失/例外 → warn，不再靜默） | `test_sdk_executor_adapter.py` +2 case | （warn 行為，覆蓋於單測 caplog 斷言） |
| **W-82-4** 🔴 真跑揭露增量 | `kernel.py` run() 累積 `run_peak_token_pct` + 成功 StepOutcome 帶 `observer.peak_pct` + `KernelResult.success_` 加 `peak_token_pct` 參數（端到端閉合：成功未觸門檻亦見真值） | `test_kernel_token_halt.py` +2 case（端到端帶真值 + 零退化） | **MUT-82-3**（成功路徑丟 peak）→ 1 紅 → 還原 |
| **DEF-82-001** 載具修 | `ab_compare_backends.py` main() 強制 stdout utf-8（cp950 console ⚠ print 防炸） | `test_ab_compare_backends.py` +1 case（cp950 stdout 不炸） | — |

> **🔴 規格先行良性偏離（誠實標記）**：W-82-4 與 DEF-82-001 **不在 §3 原設計**——皆由階段三**真跑當場揭露**（W-82-4：直接探測 PtyExecutor 已 emit 5.9% 但端到端 KernelResult 仍 0，查出成功路徑丟棄 observer.peak；DEF-82-001：載具真跑兩 backend 跑完卻在 print ⚠ 階段 cp950 炸）。依工程紀律「不無謂延後」+ 真跑揭露即修，當輪納入並補單測/突變/RTM；非事後補做，而是真跑驅動的增量發現。

### 4.2 真跑證據（北極星推進的決定性鐵證）
**(a) PtyExecutor 層直接探測**（`probe82_pty_tokenpct.py`，claude 2.1.144）：
- `ExecutionOutput.text == '[DONE]'`（還原為答案，非整坨 JSON → 下游 regex 零退化）
- events = `['partial_output', 'token_pct', 'completion']`，**TOKEN_PCT payload `{'pct': 5.8974}`**（真實非 0）

**(b) 端到端 Kernel 真跑**（`python -m autoclaude scripts/sdd_bridge_smoke.yaml --config ab_pty_config.yaml --fresh`）：

| 真跑 | `KernelResult.peak_token_pct` |
|------|------------------------------|
| 上輪 81（improving_81 階段一） | **0.0**（恆 0） |
| 本輪修前（PtyExecutor 改了、W-82-4 未做） | **0.0**（Kernel 成功路徑丟棄 observer.peak） |
| **本輪修後（+ W-82-4）** | **6.2128%**（success=True, completed_steps=2, halted=False） |

→ DEF-81-001 **PTY 支端到端完整閉合**：訊號源（PtyExecutor emit）→ Kernel 成功路徑落地 → KernelResult 暴露真值 → 載具可讀。token-guard 的「油表」在 PTY 真跑端到端通了。

## §5 零退化驗證矩陣（階段四實測）

| 檢查 | 命令 | 通過條件（floor=上輪實測） | 本輪實測 | 結果 |
|------|------|------------------------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3449 passed / 0 failed | **3468 passed / 0 failed / 122 skipped**（+19 新測） | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（total=19767 / cap=20438） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **PASS**（階段四最終復跑確認；git diff 鐵證零碰框架本體） | ✅ |
| DAL 等價 | equivalence job | 三後端等價 | **既有 `tests/equivalence/` 隨全套 pytest 通過；本輪零 DAL/repositories/checkpoint 改動故無新 round-trip 契約**（git status 證實未動 `infra/repositories/`） | ✅（N/A 類型②：既有隨全套通過） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation | **N/A 類型①：本輪零碰 `*.tla`/FSM/`_HAPPY_PATH`**（git status 證實零 AISDLC_SDD 改動；TLC 不在 pytest 全套、需 Java，未跑） | N/A① |

## §6 缺陷處置

- **DEF-81-001**（P2，訊號源根因）：**PTY 支由 routed → fixed@improving_82**（W-82-1/2/4 訊號源→Kernel 落地→KernelResult 端到端閉合，真跑 6.21% 鐵證 + MUT-82-1/2/3 + 19 新測）。**SDK 支**：W-82-3 fail-loud 可觀測化（盲區從靜默→可見），**真值接線續 routed improving_83**（需真跑取 SDK `get_context_usage` 真實 schema 後才能無推測地接通，本輪不硬算）。
- **DEF-82-001**（P3，新增，本輪 dogfooding 真跑揭露）：載具 `ab_compare_backends.py` main() print 報表時 fail-loud `⚠`（W-81-1 引入）/中文在 Windows cp950 console 撞 `UnicodeEncodeError` 中斷（真跑兩 backend 已跑完卻在 print 階段炸）。**fixed@improving_82**（main 開頭 best-effort `sys.stdout.reconfigure(utf-8)` + 回歸測試以 cp950 fake stdout 鎖）。

## §7 結案契約

```yaml
closure-evidence:
  round: improving_82
  track: C  # 指揮官 AutoClaude 自身能力（DEF-81-001 訊號源根因修復）
  pytest: "3468 passed / 0 failed / 122 skipped"
  lint_imports: "8 kept / 0 broken"
  loc_violations: 0
  snapshot: fresh
  aisdlc_sdd_cigate: PASS  # 零碰框架本體
  real_run_pty_peak_token_pct: 6.2128  # 端到端非 0（上輪恆 0）
  mutations: "MUT-82-1/2/3 全轉紅 + Edit 還原無殘留"
  new_tests: 19
  production_files_touched: 7   # kernel/kernel_state/pty_executor/sdk_executor_adapter/config/token_tracker/ab_compare_backends
  aisdlc_sdd_touched: 0
  framework_version: v0.26  # 不變
  maturity: L5  # L_合體不變
  defects:
    - DEF-81-001: "PTY 支 fixed；SDK 真值接線 routed improving_83"
    - DEF-82-001: "fixed（載具 cp950 print）"
```

## §8 誠實限制

1. **W-82-1 為近似 context%**：claude `-p --output-format json`（2.1.144 親跑）**無**直接 `percentage` 欄，故由 `usage`（input + 兩 cache）÷ `modelUsage` 最大 `contextWindow` 推算。多模型取最大視窗為主模型基準。此近似對 token-guard 門檻判斷（80%/90%）足夠，但非 claude 自報精確值。
2. **SDK 支真值未接通**：W-82-3 只做 fail-loud 可觀測化（percentage 缺失→warn 而非靜默）。真值接通需先真跑取得 SDK `get_context_usage()` 回傳的真實 schema（是否有 maxTokens/used 可算），未真跑即硬算＝基於推測（違 zero-trust），故續 routed improving_83。本輪 SDK 端到端真跑仍 peak=0，但現在會 log warning 使盲區可見。
3. **PTY json 模式串流體驗降級**：`--output-format json` 為 single-result（一次性吐完整 JSON），故「人看的即時逐字串流」喪失（PARTIAL_OUTPUT 變 JSON 片段），但功能面（下游 `expected_output_regex` 評估、token-guard）無損——text 已還原為 `result` 欄。可用 `output_format=""` 退回純文字舊行為。
4. **規格先行良性偏離**：W-82-4 + DEF-82-001 為真跑當輪揭露增量（見 §4.1 標記），非 §3 事前設計；已補齊單測/突變/RTM/帳本，誠實標記。
5. **DEF-82-001 為 Windows cp950 console-only**：CI（utf-8 環境）無法複現原 crash；回歸測試以 cp950 fake stdout 主動複現並鎖修復。
