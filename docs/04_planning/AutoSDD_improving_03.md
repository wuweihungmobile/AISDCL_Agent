# AutoSDD_improving_03 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 3 輪）

> **版本**：03（第三輪迭代）
> **日期**：2026-06-14
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ **已凍結**（2026-06-14 🔴 人工確認：使用者於本日 session AskUserQuestion 明示選定「方案 A：P1 評估 + tlc 修正」+ floor=3060 凍結）。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3060 passed / 122 skipped / 0 failed**（2026-06-14 本機實測 96.58s，**非引用文件數字**）；AISDLC_SDD `ci-gate.sh` 必須全綠。
> **本輪選定範圍**（使用者凍結方案 A）：**W1** = DEF-01-008（P1）main.py brain 注入影響評估 + flag-gated 安全落地 + e2e（A 軌整合）；**W2** = DEF-02-002（P3）`tlc_runner` 計數標籤接反修正 → Copy-on-Evolve **v0.04**（B 軌框架程式）。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-14，非文件宣稱）

本計畫所有設計皆錨定下列**已實測事實**（出處：2026-06-14 親自實測 + 逐檔開檔複驗）：

| # | 事實 | 證據位置 | 對設計的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套 = **3060 passed / 122 skipped / 0 failed**（96.58s） | 本機 `python -m pytest tests/ -q` | 本輪零退化 floor = 3060（禁寫死） |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports` | 架構紅線，以實際 8 條為準 |
| F3 | AISDLC_SDD `ci-gate.sh` = **全數通過**（exit 0；arch_fitness advisory warn 不阻擋） | `bash scripts/ci-gate.sh`（AISDLC_SDD 根） | B 軌基線綠 |
| F4 | `check_loc_budget` violations=0（total 17508 ≤ cap 20438）；`snapshot_sync --check` 新鮮 | 本機實測 | 既有紅線無欠帳 |
| F5 | **`scripts/ci-gate.sh:17` 寫死 `FW_DIR=...AISDLC_SDD_v0.01`** → 官方 ci-gate 永遠只測 v0.01，v0.02/v0.03 不在官方閘門覆蓋內 | `AISDLC_SDD/scripts/ci-gate.sh:16-18` | 呼應 DEF-02-001；v0.04 須以 `cd v0.04 && pytest -m "not chaos"` 獨立驗證 |
| D8 | **DEF-01-008（P1）重現**：`main.py:97` `build_kernel(...)` 未傳 `brain=` → `kernel.py:198` correction 區塊（`if self._brain is not None`）整段跳過 + `sdd_governance_plugin.py:198` `decide_escalation` 諮詢（`self._brain is None` 即 return）皆為死碼 | 開檔 `main.py:97`、`kernel.py:198-219`、`sdd_governance_plugin.py:198-211`、`wiring.py:307/315/177/202` | W1 缺口屬實；**brain 一參雙效**（kernel correction + governance escalation） |
| D2 | **DEF-02-002（P3）重現**：`tlc_runner.py:72-86` `_grp` 用 `re.search` 取**首個**匹配（progress 行而非最終 summary），且**無 `generated ≥ distinct` 斷言** | 開檔 `tlc_runner.py:72-86` | W2 缺口屬實 |
| D9 | **DEF-01-009（P3）重現**：`sdd_governance_plugin.py` raw=**250**（恰貼 plugin_entry ≤250 上限）、nonblank=224 | 本機行數實測 | W1 紅線：**禁止擴充該檔**（無擴充空間）；本輪 W1 不改 plugin 本體 |

**硬閘判定**：F1 基線 0 failed 且 3060 = 上輪 floor → **通過，准進階段二**。本輪零退化 floor 錨定 = **3060**。

**繼承缺陷處置（見 §7）**：DEF-01-008（本輪 W1 修）、DEF-02-002（本輪 W2 修）、DEF-01-007（cc-switch，環境工具，續 open watch）、DEF-01-009（plugin 250 行，本輪 W1 不碰該檔，續 watch）、DEF-02-001（Copy-on-Evolve 測試隔離，本輪不取、續 open）。

---

## 1. `<Architecture_Design_Review>`（寫任何實質程式前強制自我檢核）

> 本輪 W1 主體為 **AutoClaude entry-point（main.py）+ config 一個 additive flag**；W2 為 **AISDLC_SDD 框架工具 `tlc_runner.py`（v0.04）**。微核心 `core/`/`plugins/` 結構**零改動**。四問以「flag 預設 OFF = 零行為變更」為核心。

### 1.1 架構純潔性 — 是否創造 God-object？Thin Facade 是否維持？

**否，且維持。** W1 只在 `main.py`（CLI 進入點，本就負責 wiring 組裝）依 flag 條件構造 `MinimaxBrainAdapter(minimax)` 並傳 `brain=`；`build_kernel` 簽名**早已**接受 `brain=`（`wiring.py:264`），**一行不改**。不新增 plugin/port/adapter/class，不改 `SddGovernancePlugin`（守 D9 紅線：該檔 250 行無擴充空間）、不改 `kernel.py`、不碰 `playbook_runner.py`（Thin Facade）。`MinimaxConfig` 加單一 bool 欄位屬 data tier（≤150）。無 God-object。

### 1.2 持久化相容 — 新狀態是否 additive？DAL 三後端零停機是否維持？

**是，且維持。** `enable_kernel_brain: bool = False` 為 `MinimaxConfig` 純加法欄位（pydantic 預設值），**零 alembic、零 PlaybookCheckpoint schema 改動、零 DAL 改動**。預設 False → main.py 不構造 brain → `kernel._brain is None` 與 `SddGovernancePlugin._brain is None`，**與當前 production 位元相同**（3060 基線不動）。舊 config.yaml 無此欄位時 pydantic 取預設 False → 完全相容。W2 不觸碰任何持久化。

### 1.3 安全防護網 — CONDITIONAL 白名單能否攔截鏈式攻擊向量？

**N/A 且零弱化。** W1 不新增任何「從文件生成指令」路徑。flag-on 時啟動的 `kernel.decide_correction` → `step_mutation` 處理走**既有** `_apply_mutation`（`kernel.py:254+`），CONDITIONAL 三層防禦（白名單 regex + 黑名單字元 + shell=False/shlex）**一行不改**，新路徑沿用等強度消毒。flag-off（預設）零新增攻擊面。W2 為框架測試工具，無指令生成。

### 1.4 對外 I/O 安全 — 本輪是否新增 `ToolInvocationPort` 外呼路徑？

**否。** W1 啟用的 brain 後端 `MinimaxClient` 為 **既有** LLM 外呼（main.py 早已構造 `minimax` 並注入 `goal_synthesis`/`evolution`）；flag-on 只是把**同一個既存 client** 再經 adapter 注入 kernel，**未新增任何新外呼端點 / 新網域**。`ToolInvocationPort`（Web/HTTP 工具呼叫）零觸碰，allowlist 預設 deny 不受影響，SSRF 攻擊面零變化。W2 為純本機 subprocess（java TLC），無外呼。

**結論：四項檢核全數自洽，flag 預設 OFF 保證零退化，無架構衝突，准予進入設計細節。**

---

## 2. W1 設計 — DEF-01-008 main.py brain 注入影響評估 + flag-gated 落地（A 軌）

### 2.1 影響評估（zero-trust 開檔實證的耦合關係）

`build_kernel(brain=...)` 把同一個 `brain` **雙重**下發（`wiring.py`）：

1. **`wiring.py:307 → 177 → 202`** → `SddGovernancePlugin(brain=brain)`：`_on_failure` 於違反次數 ≥ threshold 時呼叫 `IBrain.decide_escalation`（advisory 升級諮詢）。`brain is None` 即 `return`（`sdd_governance_plugin.py:198`）。
2. **`wiring.py:315`** → `PlaybookKernel(brain=brain)`：`kernel.py:198` `if self._brain is not None and attempt < max_retries:` 啟動 `decide_correction`（Minimax 改寫 prompt + step mutation）。

**退化風險（為何不能一行 `brain=` 帶過）**：
- 目前 production（brain=None）失敗時**完全不做** Minimax correction，僅以原 prompt 重試 → 注入 brain 會**改變每步重試/修正行為**。
- `kernel.py:216` `if c is None: return ESCALATE("Minimax API 故障，安全停止")` → 注入後 **Minimax API 故障將觸發 escalation**，這是 brain=None 時不存在的新行為。
- 故「修死碼」與「改 production 修正語意」在現有 wiring 是**綁定的**——必須以 flag 解耦風險。

### 2.2 落地決策：flag-gated 注入（預設 OFF = 零退化）

採使用者方案 A 之「**證明非退化才注入，否則 flag-gated**」分支。結論：**flag-gated**——以 `MinimaxConfig.enable_kernel_brain`（預設 `False`）作為唯一開關：

- **flag = False（預設）**：main.py 不構造 brain，行為與當前 production **位元相同**（kernel correction + governance escalation 皆維持 None）→ **零退化**，3060 基線不動。
- **flag = True（operator 顯式啟用）**：main.py 構造 `MinimaxBrainAdapter(minimax)` 傳 `brain=` → 死碼轉為**可達且被測試覆蓋**的能力（kernel Minimax correction + governance escalation 諮詢同時生效；operator 已知並接受 §2.1 的行為差異）。

此決策把 DEF-01-008 從「production 死碼」轉為「**flag-gated 可選能力**」——誠實解（非掩蓋、非盲改）。

### 2.3 介面 delta（additive）

**(a) `autoclaude/utils/config.py`（`MinimaxConfig`）**
```python
enable_kernel_brain: bool = False
# DEF-01-008：是否把 MinimaxBrainAdapter 注入 PlaybookKernel + SddGovernancePlugin。
# 預設 False＝production 維持 brain=None（無 Minimax 逐步 correction、無 escalation 諮詢，
# 零退化）。設 True 啟用後：kernel.decide_correction 生效（改寫 prompt + step mutation）
# 且 Minimax API 故障將觸發 ESCALATION（見 improving_03 §2.1）—— operator 須知悉行為差異。
```

**(b) `autoclaude/main.py`** — 在構造 `minimax` 之後、`build_kernel` 之前：
```python
brain = MinimaxBrainAdapter(minimax) if cfg.minimax.enable_kernel_brain else None
...
kernel = build_kernel(cfg, executor=executor, evaluator=evaluator,
                      hotkey=hotkey, minimax_client=minimax, brain=brain,
                      state_repository=state_repo)
```
（新增 import `from .infra.adapters.minimax_brain import MinimaxBrainAdapter`。）

### 2.4 測試衝擊（additive，Rule 9 測意圖）

新增 `tests/integration/test_def_01_008_brain_injection.py`（或併入既有 wiring/cli 測試），≥4 case：
- **off（預設）零退化**：`enable_kernel_brain=False` → `build_kernel(...)._brain is None` 且 `plugins["sdd_governance"]._brain is None`（證明預設行為 = 現況）。
- **on 注入 kernel**：`enable_kernel_brain=True` + 注入 fake brain → `kernel._brain is not None`。
- **on 注入 governance**：flag-on 時 `SddGovernancePlugin._brain is not None` → `decide_escalation` 在 ≥threshold 時被諮詢（fake brain spy 驗證 call）。
- **on correction 可達**：flag-on + 一個 dry-run 失敗步驟 + fake brain → `decide_correction` 被呼叫一次（驗證死碼轉活）。
- **API 故障語意**：fake brain `decide_correction → None` → kernel 回 ESCALATE（驗證 §2.1 新語意被測試鎖定）。

> 每 case 檔頭註記 WHY（為何此行為重要），符合 Rule 9「測意圖非僅行為」。

### 2.5 LOC 預算落點

- `config.py`：+1 欄位 + 註解（data tier，無逼近上限）。
- `main.py`：+1 import +1 條件式 +1 kwarg（entry-point，非 tier 受限業務檔）。
- 新測試檔：tests/ 不計 LOC 預算。
- **`sdd_governance_plugin.py` / `kernel.py` / `wiring.py` 零改動**（守 D9 紅線）。

### 2.6 `.importlinter` 影響分析

- main.py import `infra.adapters.minimax_brain` — main.py 是 entry-point（**非** core/plugin），既有 main.py 早已 import `infra.adapters.pty_executor`/`shell_evaluator`（`main.py:30-31`），同層 import 合法，**不觸發任何 contract**。
- 不新增 plugin↔plugin、core→infra、brain↔executor 等違規。8 條 contract 預期維持 kept。

---

## 3. W2 設計 — DEF-02-002 `tlc_runner` 計數標籤接反修正（Copy-on-Evolve v0.04）

### 3.1 問題（D2）

`tlc_runner.py:72-74` `_grp` 用 `re.search` 取輸出中**首個**匹配 → TLC 執行中的 progress 行（非最終 summary）被抓取，致 `distinct=855 > generated=706` 違反 TLC「generated ≥ distinct」恆等不變量（DEF-02-002）。**權威停機判準 `No error has been found` 不受影響**，但 raw 計數不可靠。

### 3.2 修正（v0.04）

```python
def _grp(pat: str) -> int:
    ms = re.findall(pat, out)          # 取全部匹配
    return int(ms[-1]) if ms else 0    # 取最後一個＝最終 summary（非中途 progress）
...
# run_tlc 回傳前，新增完整性斷言（fail-closed）：
distinct = _grp(r"(\d+)\s+distinct\s+states\s+found")
generated = _grp(r"(\d+)\s+states\s+generated")
if generated and distinct and generated < distinct:
    raise RuntimeError(
        f"TLC 計數不變量違反：generated({generated}) < distinct({distinct})；"
        f"疑似 parser 抓到非最終 summary 行（DEF-02-002）。")
```
> 斷言僅在「兩值皆非零且 generated < distinct」時 raise，避免 META/FLEET 等小模型零值或邊界誤報；正常 summary（generated ≥ distinct）零影響。

### 3.3 v0.04 Copy-on-Evolve 落版（B 軌紅線：v0.03 凍結唯讀）

1. `robocopy AISDLC_SDD_v0.03 AISDLC_SDD_v0.04`（v0.01/v0.02/v0.03 凍結，git 改動須 = 0）。
2. 於 **v0.04** 施作 §3.2 修正（`tools/fsm_runtime/tlc_runner.py`）。
3. `EVOLUTION_LOG.md` 新增 `v0.03 → v0.04` 列（delta：tlc_runner 計數修正；TLC 證據：五軌重跑、修正後 generated ≥ distinct；回退指引）。
4. `releases/CHANGELOG.md` 新增 `[v0.04]` 段。
5. **不需新 ACT/rule**（純工具 bugfix，非 FSM 狀態/規則變更）；`ID_REGISTRY.yaml` 維持 next_free act=173 / rule="9.39"。
6. **不觸發五軌 TLC 義務**（`_HAPPY_PATH` 與 `*.tla` 零改動，Rule 9.18.1 不啟動）；惟為驗證**修正本身正確**（last-match 抓對最終 summary），仍跑五軌 TLC 確認 generated ≥ distinct 且 0 violation（§4.1）。

### 3.4 測試（v0.04）

新增/補強 `tools/fsm_runtime/tests/test_tlc_runner_parsing.py`：以**合成 TLC 輸出字串**（含中途 progress 行 + 最終 summary）餵 `_grp`/解析函式，斷言：
- last-match 取到最終 summary（非首個 progress 行）。
- `generated ≥ distinct` 的正常輸出不 raise。
- `generated < distinct`（人造畸形）觸發 `RuntimeError`（攻防：鎖定不變量守護）。
> 此測試不需 Java/TLC 實跑（純字串解析），可在 v0.04 pytest not-chaos 內快速驗證。

---

## 4. 階段四 — CI 平價與形式化驗證

### 4.1 五軌 TLC（W2 驗證載體）

雖 W2 不改 `_HAPPY_PATH`/`.tla`（Rule 9.18.1 不強制），仍於 **v0.04** 跑五軌確認修正後計數正確：
```bash
cd AISDLC_SDD/AISDLC_SDD_v0.04
for m in SDD_FSM META_FSM FLEET_FSM COMPOSITION_FSM OPTIMIZATION_FSM; do
  python -m tools.fsm_runtime.tlc_runner --module $m
done
```
通過條件：五軌 `No error has been found`（0 violation）+ **修正後 `TLC_GENERATED ≥ TLC_DISTINCT`**（DEF-02-002 修復實證）。

### 4.2 零退化驗證矩陣（本輪 DoD；floor 以本輪實測為準）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **≥ 3060 passed / 0 failed**（floor=F1；W1 新增測試只增不減；預期 ≥ 3060 + 新 case） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken（實際 8 條） |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 閘門（測 v0.01） | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2 |
| v0.04 not-chaos | `cd v0.04 && pytest tools/fsm_runtime/tests/ -m "not chaos" -q` | 全綠（含新 test_tlc_runner_parsing） |
| 五軌 TLC（W2 驗證） | §4.1 迴圈 | 五軌 0 violation + generated ≥ distinct |

---

## 5. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 落點 | 驗證 |
|------|------|------|
| DEF-01-008 死碼轉可達能力，且預設零退化 | §2.2-2.3 flag 預設 False | off case = 現況（kernel/governance brain 皆 None）|
| flag-on 時 kernel correction 可達 | §2.3 | `decide_correction` 被呼叫一次（fake brain spy）|
| flag-on 時 governance escalation 諮詢可達 | §2.3 | `decide_escalation` ≥threshold 被諮詢 |
| API 故障 escalation 新語意被測試鎖定 | §2.4 | fake brain → None → kernel ESCALATE |
| 微核心結構零改動（守 D9 250 行紅線） | §2.5 | plugin/kernel/wiring git diff = 0 |
| DEF-02-002 計數取最終 summary | §3.2 | 合成輸出 last-match 測試 |
| DEF-02-002 generated ≥ distinct 不變量守護 | §3.2 | 畸形輸入 raise 測試 + 五軌實跑 |
| Copy-on-Evolve v0.04（v0.01~v0.03 凍結）| §3.3 | git 改動=0 + EVOLUTION_LOG/CHANGELOG |
| 零退化 | 全篇 flag 預設 off；W2 不碰 AutoClaude | 3060 passed 持平 |

---

## 6. 實作順序（每支完成立即驗證，絕不累積）

> B 軌 Brownfield：本計畫即 SCG-0/1 載體；§2.1-2.3 介面/邊界 = SCG-2；§2.3/§3.2 delta 契約 = SCG-3；落版過 SCG-4；§4.2 矩陣 = SCG-5 RTM。行進中框架摩擦即記入 `AutoSDD_Defect_Log.md`（DEF-03-xxx）。

- **W1-a** `config.py` 加 `enable_kernel_brain` 欄位 → `python -c import` 驗證 + 既有 config 測試。
- **W1-b** `main.py` flag-gated brain 構造 + 傳參 → `python -m py_compile` + cli/wiring 相關單測。
- **W1-c** 新增 `test_def_01_008_brain_injection.py`（≥5 case）→ 跑該檔全綠。
- **W1-d** 跑 `python -m pytest tests/ -q`（全套）確認 ≥ 3060 + 新 case、0 failed；`lint-imports` 8 kept。
- **W2-a** `robocopy v0.03 → v0.04`（v0.01~v0.03 凍結驗證：git 無改動）。
- **W2-b** v0.04 `tlc_runner.py` last-match + 斷言 → `py_compile`。
- **W2-c** v0.04 新增 `test_tlc_runner_parsing.py` → `cd v0.04 && pytest -m "not chaos"` 全綠。
- **W2-d** 五軌 TLC（§4.1）確認 generated ≥ distinct + 0 violation。
- **W2-e** EVOLUTION_LOG / CHANGELOG v0.04 段。
- **收斂**：跑 §4.2 矩陣全項，任一紅 → 停機修復。

每個 W 結束跑對應驗證；零退化矩陣為本輪硬閘。

---

## 7. 缺陷帳本本輪處置（對照 §0 繼承）

| 缺陷 | 本輪處置 |
|------|---------|
| DEF-01-008（P1, routed） | **本輪 W1 修**（flag-gated 落地）→ 完成後改 `fixed@improving_03` 附證據 |
| DEF-02-002（P3, routed） | **本輪 W2 修**（v0.04 last-match + 斷言）→ `fixed@v0.04` 附證據 |
| DEF-01-007（P3, open） | cc-switch 環境工具未裝，本輪不涉 A/B 驗收，續 `open`（watch） |
| DEF-01-009（P3, open watch） | 本輪 W1 不碰 `sdd_governance_plugin.py`（守 250 行紅線），續 `watch` |
| DEF-02-001（P3, open） | Copy-on-Evolve 測試 rootdir 隔離，本輪未取，續 `open`（候選下輪） |
| 本輪新發現 | 行進中即記 DEF-03-xxx（發現即記、絕不累積） |

---

## 8. 🔴 人工確認凍結點

本文件為 SCG-0/1 規格載體。**實作（W1-a）啟動前須由人類明示確認本計畫凍結**（B 軌紅線：HUMAN_PENDING 不可自動跳過）。**已於 2026-06-14 取得**：使用者經 AskUserQuestion 明示選定方案 A（W1 DEF-01-008 flag-gated 評估 + W2 DEF-02-002 v0.04）+ floor=3060 凍結。凍結後依 §6 實作順序執行，全程套 §4.2 零退化矩陣，收尾走多專家 Zero-Trust 審查閉環。
