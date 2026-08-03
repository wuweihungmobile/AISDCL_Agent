# AutoSDD_improving_83 — C 軌：DEF-81-001 SDK 支真跑驗證閉合 + 揪修載具 observer-peak 盲報（DEF-83-001）

> **本輪定位**：軌道① 整合迭代第 83 輪。**柱別＝C 軌（指揮官 AutoClaude 自身能力 / 觀測載具）**。
> **下一份檔名**：`AutoSDD_improving_84.md`。
> **本輪主軸（真跑重新定錨）**：上輪 routed「SDK 真值接線（需真跑取 schema）」。本輪階段一真跑**推翻原假設**——SDK schema 本就有 `percentage`、既有碼本就正確、W-82-4 已讓 SDK 真值端到端流動（真跑 `KernelResult.peak_token_pct=2.0`）。故 **DEF-81-001 SDK 支以真跑鐵證驗證閉合（零生產碼改動）**；真正待修的是**載具 `ab_compare_backends.py` 把真實峰值盲報為 0%**（DEF-83-001，[[ab-carrier-production-blind-marker]] 家族再現）。
> **框架版**：維持 v0.26（本輪零碰 AISDLC_SDD 框架本體）。**成熟度**：維持 L_合體 L5。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_82 遺留
- **已完成**：W-82-1（context% 純函式）、W-82-2（PTY `--output-format json` 接線）、W-82-3（SDK `_emit_token_pct` fail-loud 化）、W-82-4（Kernel 成功路徑帶 `peak_token_pct`，PTY 端到端真跑 6.2128%）。
- **明確 routed 本輪**：DEF-81-001 **SDK 支真值接線**——improving_82 §6/§8.2 稱「需真跑取得 SDK `get_context_usage()` 真實 schema 後無推測接通」。

### 1.2 Defect_Log open / routed 處置計畫
| 缺陷 | 狀態 | 本輪處置 |
|------|------|---------|
| **DEF-81-001**（P2，訊號源根因，SDK 支） | PTY 支 fixed@82 + SDK 支 routed | **本輪閉合（真跑驗證，非改碼）**：階段一真跑揭露 SDK schema 本就有 percentage、既有碼正確、W-82-4 已端到端接通（真跑 peak=2.0）。升 fixed@improving_83（SDK 支，real-run-verified）。 |
| **DEF-83-001**（P3，本輪真跑揭露，新增） | open → 本輪即修 | 載具 `ab_compare_backends.py` 在訊號已觀測時把「token 峰值」印成 marker peak（恆 0，未撞門檻）而非 observer 真值（6.2/2.0）→ 修。 |
| **DEF-83-002**（P3，誠實性，上輪文件） | open → 本輪訂正 | improving_82 §8.2 稱「SDK 端到端真跑仍 peak=0」係未真跑之推測；本輪訂正 + 入帳。 |
| DEF-62-001 / DEF-19-001 / DEF-23-005 家族 / DEF-30-001 家族 / DEF-32-002（P3） | routed | 非本輪 scope，維持 routed。 |

### 1.3 上輪 QA 複審延後條目
- 無新「延後」條目進本輪（improving_82 三鏡 OVERALL PASS，P0=0/P1=0）。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-27 本輪親跑）

### 2.1 零退化基線（硬閘：floor = improving_82 實測 3468 passed / 0 failed）
| 檢查 | 命令 | 實測 | 上輪基線 | 達標 |
|------|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3468 passed / 0 failed / 122 skipped** | 3468 / 0 | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | 8 / 0 | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19767 / cap=20438） | 0 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | **OK（fresh）** | fresh | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **PASS**（v0.01 1478 + v0.26 1665 + scripts 129，arch_fitness fail=0） | PASS | ✅ |

**硬閘通過**，准進階段二。improving_82 六構件（context_pct 純函式 / PTY json 接線 / SDK fail-loud / ClaudeConfig.output_format / Kernel 成功路徑 peak / 對應測試）經 audit agent 逐項驗證真實存在且被測。

### 2.2 SDK `get_context_usage()` 真實 schema（parent 親跑取證，非採信偵察推測）
`claude_agent_sdk` 版本 **0.2.110**。SDK 套件 `types.py:759-789` `ContextUsageResponse` TypedDict **明載 `percentage: float`（0-100）** + `totalTokens/maxTokens/rawMaxTokens/model`。**親跑 probe**（`scratchpad/probe83_sdk_ctx.py`，trivial prompt，client 連線期內呼叫 `get_context_usage()`）實測回傳：
```
KEYS: ['agents','apiUsage','autoCompactThreshold',...,'maxTokens','model','percentage','rawMaxTokens','totalTokens']
percentage: 5   totalTokens: 50622   maxTokens: 1000000   model: claude-opus-4-8[1m]
```
→ **SDK schema 確有 percentage 且真跑回真實值**。與 improving_82 §8.1 的 PTY `claude -p --output-format json`「無 percentage 欄」是**兩條不同管道**（SDK 走 control request；PTY 走 print JSON）。既有 `sdk_executor_adapter._emit_token_pct`（:281 `usage.get("percentage")`）**本就正確**——真跑會 emit `TOKEN_PCT {"pct": 5.0}`，不走 W-82-3 的 warning 分支。

### 2.3 端到端真跑（DEF-81-001 SDK 支閉合 + DEF-83-001 揭露的決定性鐵證）
載具 `ab_compare_backends.py --run scripts/sdd_bridge_smoke.yaml --pty-config ... --sdk-config ... --n 1` 親跑（claude 2.1.144 / sdk 0.2.110），引擎 utf-8 log 鐵證：

| 後端 | `KernelResult.peak_token_pct`（log 原值） | 載具「token 峰值」顯示 |
|------|------|------|
| PTY | **6.2006**（真實非 0，與 improving_82 6.2128 一致） | **0%** ❌（盲報） |
| SDK | **2.0**（真實非 0！SDK 真值端到端流動） | **0%** ❌（盲報） |

→ **(a) DEF-81-001 SDK 支端到端閉合**：SDK 真值（`get_context_usage().percentage`）→ `_emit_token_pct` emit TOKEN_PCT → `TokenObserver` peak → W-82-4 Kernel 成功路徑 → `KernelResult.peak_token_pct=2.0`。既有碼 + W-82-4 已完成，**零生產碼改動**。
→ **(b) DEF-83-001 揭露**：載具兩後端都印「0%」卻標「已觀測」（自相矛盾），把真實 A/B token 差異（PTY 6.2 vs SDK 2.0）藏成 0。

### 2.4 DEF-83-001 根因（file:line 鐵證）
`tools/ab_compare_backends.py:227-234` `_fmt_token_peak`：
```python
if not m.token_signal_observed:          # observer_peak>0 → False，不進此分支
    return "0%（⚠ 訊號源未產出，非真值）"
return f"{m.peak_token_pct:.0f}%"         # ← 印 marker peak（恆 0，smoke 未撞 80/90% 門檻無 marker）
```
- `m.observer_peak_token_pct`＝**6.2006/2.0**（從 KernelResult 解析的訊號層真值，`parse_run_metrics:166-168`）。
- `m.peak_token_pct`＝**0**（掃 TOKEN_COMPACT/TOKEN_HALT marker 行得到的決策層 peak，`:189-209`；smoke 太短未撞門檻 → 無 marker）。
- `_fmt_token_peak` 在「已觀測」分支印的是**決策層 marker peak（0）**而非**訊號層 observer 真值**。同病在 `_fmt_agg_token_peak:368-373`（用 `peak_token_pct_mean/max`，亦 marker 來源）。
- **驗證腳本**（`scratchpad/verify83_carrier.py`）實證：`[pty] observer_peak=6.2006 marker_peak=0.0 signal_observed=True ->顯示='0%'`、`[sdk] observer_peak=2.0 marker_peak=0.0 -> '0%'`。

> **W-81-1 設計盲點**：fail-loud 只區分了「訊號未產出（observed=False）」vs「真值」兩態，**漏掉第三態**——「訊號已產出（observed=True）但未撞門檻（marker peak=0）」。此態應報 observer 真值，卻誤報 marker 0。

### 2.5 DEF-83-002（誠實性，上輪文件）
improving_82 §8.2 第 2 點稱「本輪 SDK 端到端真跑仍 peak=0」。經查 improving_82/81 的 ZeroTrust_Audit **從未做過真正的 SDK 端到端真跑**（audit_82 僅驗 PTY 真跑；SDK「peak=0」係靜態讀碼推測「mock dict 無 percentage → 真跑也無」）。本輪真跑實證 SDK 端到端 peak=2.0，原宣稱不成立——屬「用未跑的真跑結果當事實」（違 [[no-fabricated-tool-output]] / zero-trust）。

---

## §3 本輪增量設計（規格先行）

### 3.1 W 項總覽（1 項生產載具改動 + 2 項驗證/文件閉合）
| 項目 | 標的檔 | tier / budget | 性質 |
|------|--------|--------------|------|
| **W-83-1** | `tools/ab_compare_backends.py`（現 526 行） | 絕對紅線 ≤750 | 修 DEF-83-001：「token 峰值」改報 observer 真實峰值（取 observer / marker 最大）+ aggregate 同步 |
| DEF-81-001 SDK 支閉合 | （無碼改） | — | 真跑驗證閉合（§2.2/2.3 鐵證 + 既有單測 `test_emit_token_pct_emitted_when_percentage_present` 鎖契約） |
| DEF-83-002 訂正 | 帳本 + 本計畫書 | — | 入帳 + 訂正上輪未驗證宣稱 |

### 3.2 `<Architecture_Design_Review>`（寫任何 Python 前）
1. **架構純潔性**：改的是 `tools/` 觀測載具（非 `autoclaude/` 生產微核心）；新增一個 `RunMetrics` property + 2 個 aggregate 欄位 + 改 2 個純函式 display；無 God-object、不涉 Thin Facade、不涉 Kernel/EventBus。✅
2. **持久化相容**：零 checkpoint / DAL / PlaybookCheckpoint 改動。✅
3. **安全防護網**：零 CONDITIONAL / shell 生成路徑改動。✅
4. **對外 I/O 安全**：零新增 `ToolInvocationPort` 外呼路徑。✅

### 3.3 介面 delta（W-83-1）
**新增 `RunMetrics.effective_peak_token_pct` property（DRY SSOT）**：
```python
@property
def effective_peak_token_pct(self) -> float:
    """本次 run 的真實 token% 峰值＝訊號層 observer 真值（KernelResult.peak_token_pct）
    與決策層 marker peak（TOKEN_COMPACT/HALT 行）取最大。
    Kernel production 路徑 observer 看見全程 → observer ≥ marker；合成/legacy log 可能
    只有 marker（observer=0）→ 取 max 兩態皆正確。DEF-83-001：原顯示誤用 marker（未撞
    門檻恆 0）藏掉 observer 真值。"""
    return max(self.observer_peak_token_pct, self.peak_token_pct)
```
**`_fmt_token_peak` 改用 effective**（signal observed 分支）：`return f"{m.effective_peak_token_pct:.0f}%"`。訊號未產出分支（⚠）不變。
**`AggregateMetrics` 新增** `effective_peak_token_pct_mean: float` + `effective_peak_token_pct_max: float`（additive）；`aggregate_runs` 以 `r.effective_peak_token_pct` 計；`_fmt_agg_token_peak` 改用 effective mean/max。既有 `peak_token_pct_mean/max`（marker 來源）保留不動（向後相容、per-step churn 維度仍需）。

> **零退化保證**：`parse_run_metrics` 對 `peak_token_pct`（marker）/ `observer_peak_token_pct` 的解析**完全不動**；既有測試（marker 85% → 顯示 85%：observer 0 / marker 85 → max 85 ✓）全數保持綠。

### 3.4 LOC 預算落點
- `ab_compare_backends.py`：521 → **546**（實測 raw 行；+25 含 1 property + 2 aggregate 欄 + aggregate_runs 3 行 + display 改寫 + 註解），遠落絕對紅線 750 ✅。

### 3.5 `.importlinter` 各 contract 影響分析
- 改的是 `tools/`（不在 `autoclaude/` 套件樹、非 importlinter 掃描標的）；**8 kept / 0 broken 不變**。✅

### 3.6 checkpoint additive 欄位需求
- **無**。零持久化改動。

### 3.7 RTM 需求列（SCG-5 載體；測試名階段三落地對齊）
| RTM-ID | 需求 | 驗證測試 |
|--------|------|---------|
| RTM-83-1 | observer>0 且無 marker（DEF-83-001 真跑情形）→「token 峰值」報 observer 真值非 0% | `test_def_83_001_observer_peak_shown_when_no_marker` |
| RTM-83-2 | observer=0 且 marker>0（既有語意）→ 報 marker 值（零退化） | `test_def_83_001_marker_peak_shown_when_no_observer` |
| RTM-83-3 | observer>0 且 marker>0 → 報兩者最大 | `test_def_83_001_effective_peak_takes_max` |
| RTM-83-4 | `effective_peak_token_pct` property = max(observer, marker) | `test_effective_peak_is_max_of_observer_and_marker` |
| RTM-83-5 | 真跑情形（KernelResult peak=2.0 無 marker）format_comparison 顯示 2% 非 0% | `test_def_83_001_realrun_kernelresult_peak_rendered` |
| RTM-83-6 | aggregate effective mean/max 反映 observer 真值；多輪 format 不藏真值 | `test_def_83_001_aggregate_effective_peak` |
| DEF-81-001 SDK 支 | percentage 有值 → emit TOKEN_PCT（契約鎖；real-run-verified 見 §2.2/2.3） | 既有 `test_emit_token_pct_emitted_when_percentage_present` |

### 3.8 受控突變（階段三）
| 突變 | 預期 |
|------|------|
| MUT-83-1 | `effective_peak_token_pct` 改回只用 `self.peak_token_pct`（marker）→ RTM-83-1/5 轉紅 |
| MUT-83-2 | `max(...)` 改 `min(...)` → RTM-83-3 轉紅 |
| MUT-83-3 | `_fmt_token_peak` 改回印 `m.peak_token_pct` → RTM-83-1/5 轉紅 |

---

## §4 實作與雙重驗證（階段三/四實測回填）

### 4.1 實作落地
| 項目 | 落地 | 單測 | 受控突變 |
|------|------|------|---------|
| **W-83-1** | `ab_compare_backends.py`：`RunMetrics.effective_peak_token_pct` property（max(observer,marker)）+ `_fmt_token_peak` 改用 effective + `AggregateMetrics.effective_peak_token_pct_mean/max` + `aggregate_runs` 計 + `_fmt_agg_token_peak` 改用 effective | `test_ab_compare_backends.py` +6 case（RTM-83-1~6） | **MUT-83-1**（只回 marker）→ 4 紅；**MUT-83-2**（max→min）→ 7 紅；**MUT-83-3**（_fmt 印 marker）→ 2 紅；全 Edit 還原無殘留 |
| **DEF-81-001 SDK 支** | 零碼改（真跑驗證閉合） | 既有 `test_emit_token_pct_emitted_when_percentage_present` 鎖 percentage→emit 契約 | — |

### 4.2 真跑證據（決定性鐵證，§2.2/2.3 取得）
- **SDK probe**（`scratchpad/probe83_sdk_ctx.py`）：`get_context_usage()` 回 `percentage=5`、totalTokens=50622、maxTokens=1000000、model=claude-opus-4-8[1m]。
- **端到端 A/B 真跑**（`ab_compare_backends.py --run --n 1`）：`KernelResult.peak_token_pct` PTY **6.2006** / SDK **2.0**（log 鐵證）→ SDK 真值端到端流動。
- **DEF-83-001 修前/修後**（對同一組 ab83 真跑 log 解析，零額外 token）：

| | 修前載具顯示 | 修後載具顯示 | KernelResult 真值 |
|---|---|---|---|
| token 峰值（pty） | **0%** ❌ | **6%** ✅ | 6.2006 |
| token 峰值（sdk） | **0%** ❌ | **2%** ✅ | 2.0 |

## §5 零退化驗證矩陣（階段四實測）

| 檢查 | 命令 | 通過條件（floor=上輪實測） | 本輪實測 | 結果 |
|------|------|------------------------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3468 passed / 0 failed | **3474 passed / 0 failed / 122 skipped**（+6 新測） | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（total=19767；本輪改 `tools/` 不在 autoclaude/ 計數域，ab_compare 實測 546 行 < 絕對紅線 750） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **PASS**（v0.01 1478 + v0.26 1665 + scripts 129；git diff 鐵證零碰框架本體） | ✅ |
| DAL 等價 | equivalence job | 三後端等價 | **既有 `tests/equivalence/` 隨全套 pytest 通過；本輪零 DAL/repositories/checkpoint 改動故無新 round-trip 契約**（git diff 證實只動 `tools/`） | ✅（N/A 類型②：既有隨全套通過） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation | **N/A 類型①：本輪零碰 `*.tla`/FSM/`_HAPPY_PATH`**（git diff 證實零 AISDLC_SDD 改動；TLC 不在 pytest 全套、需 Java，未跑） | N/A① |

## §6 缺陷處置

- **DEF-81-001**（P2，訊號源根因，SDK 支）：**SDK 支由 routed → fixed@improving_83（real-run-verified，零生產碼改動）**。真跑鐵證：SDK `get_context_usage()` schema 本就有 `percentage`（probe 回 5）、既有 `_emit_token_pct` 碼正確、W-82-4 已端到端接通（端到端真跑 `KernelResult.peak_token_pct=2.0`）。契約鎖於既有單測 `test_emit_token_pct_emitted_when_percentage_present`。**至此 DEF-81-001 PTY+SDK 雙支全閉合**。
- **DEF-83-001**（P3，新增，本輪 dogfooding 真跑揭露）：載具 `ab_compare_backends.py` `_fmt_token_peak`/`_fmt_agg_token_peak` 在訊號已觀測時印決策層 marker peak（未撞門檻恆 0）而非訊號層 observer 真值（6.2/2.0）→ 與「已觀測」自相矛盾、藏掉真實 A/B token 差異（[[ab-carrier-production-blind-marker]] 家族）。**fixed@improving_83**（W-83-1：`effective_peak_token_pct=max(observer,marker)` SSOT property + 單/多輪 display 改用 + 6 新測 + MUT-83-1/2/3）。
- **DEF-83-002**（P3，新增，誠實性，上輪文件）：improving_82 §8.2 稱「SDK 端到端真跑仍 peak=0」係未真跑之靜態推測（audit_82 僅驗 PTY；SDK「peak=0」由 mock dict 無 percentage 推得）。本輪真跑實證 SDK 端到端 peak=2.0，原宣稱不成立。**fixed@improving_83（訂正）**：本計畫書 §2.5 + 帳本載明，並以 §2.2/2.3 真跑鐵證取代推測。

## §7 結案契約

```yaml
closure-evidence:
  round: improving_83
  track: C  # 指揮官 AutoClaude 自身能力 / 觀測載具（DEF-81-001 SDK 支真跑閉合 + DEF-83-001 載具修）
  pytest: "3474 passed / 0 failed / 122 skipped"
  lint_imports: "8 kept / 0 broken"
  loc_violations: 0
  snapshot: fresh
  aisdlc_sdd_cigate: PASS  # 零碰框架本體
  real_run_sdk_get_context_usage_percentage: 5      # probe 真跑（schema 本就有 percentage）
  real_run_end2end_peak_token_pct: {pty: 6.2006, sdk: 2.0}  # 端到端 KernelResult 真值
  carrier_display_before_after: {before: "0%/0%", after: "6%/2%"}  # DEF-83-001 修前/後
  mutations: "MUT-83-1/2/3 全轉紅 + Edit 還原無殘留"
  new_tests: 6
  production_files_touched: 0   # 零碰 autoclaude/ 生產碼（SDK 支真跑驗證閉合，非改碼）
  tooling_files_touched: 1      # tools/ab_compare_backends.py（觀測載具）
  aisdlc_sdd_touched: 0
  framework_version: v0.26  # 不變
  maturity: L5  # L_合體不變
  defects:
    - DEF-81-001: "SDK 支 fixed（real-run-verified，零碼改）；PTY+SDK 雙支全閉合"
    - DEF-83-001: "fixed（載具 observer-peak 盲報）"
    - DEF-83-002: "fixed（訂正 improving_82 §8.2 未驗證宣稱）"
```

## §8 誠實限制

1. **DEF-81-001 SDK 支以真跑驗證閉合、非改碼**：本輪沒有改任何 `autoclaude/` 生產碼——真跑揭露既有碼本就正確（improving_81/82 的「SDK 盲區」是從沒真跑過的推測）。閉合證據＝真跑鐵證（§2.2/2.3）+ 既有單測契約鎖。誠實標記：這是「驗證一個被誤判為壞的東西其實是好的」，價值在於用真跑終結 5 輪的推測。
2. **W-83-1 改的是觀測載具非生產微核心**：`tools/ab_compare_backends.py` 是 A/B 量測工具，非 `autoclaude/` 產品碼。修的是「報告層把真值藏成 0」的觀測缺陷，不影響 production token-guard 行為（token-guard 用的是 Kernel observer 真值，本就正確）。
3. **`effective_peak = max(observer, marker)` 的語意邊界**：Kernel production 路徑 observer 看見全程 → observer ≥ marker，取 max 即 observer；合成/legacy log 可能只有 marker（observer=0），取 max 即 marker。兩態皆正確。marker peak（`peak_token_pct`）欄位與 per-step churn 維度保留不動（向後相容）。
4. **probe 的 percentage=5 vs 端到端 2.0 差異屬正常**：probe 在本 session（已載大量 context）內跑，端到端在乾淨 smoke session 跑，context% 自然不同；兩者都 >0、都證明 SDK 訊號源活著，這才是重點。
5. **規格先行遵循**：本輪 §1-§3（含 W-83-1 設計 + RTM）於階段二先落地、才動碼；§4/§5 為階段三/四回填。無「事後結案報告」式偏離。
