# AutoSDD_improving_13 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 13 輪）

> **版本**：13（第十三輪迭代）
> **日期**：2026-06-15
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ 結案（含 zero-trust 多專家複審）。範圍＝**按需「成熟度三軸實測＋升最低軸」，🔴 人工於 W 項 signoff 選「兩項都做」**。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3075 passed / 122 skipped / 0 failed**（2026-06-15 階段一本機實測）；本輪交付後 **3091 passed / 122 skipped / 0 failed**（+16＝W-13-2 9 + W-13-1 7，0 failed）。lint-imports 8 kept/0 broken、LOC violations=0、snapshot OK、ci-gate 雙軌 exit 0（v0.01:1478 / v0.05:1499 / scripts/tests:24，本輪零 AISDLC_SDD 改動故不受影響）。
> **本輪定位**：承 improving_12（按需雙驅動）。本輪驅動＝把 improving_13 前置稽核起草的 `AutoSDD_Maturity_Rubric.md` SSOT **落地實測**——以 zero-trust 證據評三軸現級、算 `L_合體=min`，再挑最低軸做一項有界實質升級（對齊北極星「三軸一起升」）。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-15，非文件宣稱）

主 agent 派 Explore agent 親跑（非引用文件）：

| # | 事實 | 證據 | 對本輪影響 |
|---|------|------|-----------|
| F1 | AutoClaude 全套（**改動前**）= **3075 passed / 122 skipped / 0 failed**（99.18s） | `python -m pytest tests/ -q` | 硬閘 floor=3075，0 failed → **通過** |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports` | 架構紅線 8 條全保 |
| F3 | LOC violations=**0**（total 17511 / cap 20438） | `python tools/check_loc_budget.py` | 分級政策全過 |
| F4 | snapshot = **OK** | `python tools/snapshot_sync.py --check` | 文件新鮮 |
| F5 | AISDLC_SDD `ci-gate.sh`（改動前）= **exit 0**；v0.01:1478 / v0.05:1499 / scripts/tests:24 | `bash scripts/ci-gate.sh` | 雙軌＋共享 infra 健康 |

**硬閘判定**：F1 基線 0 failed 且 3075 = 上輪 floor → **通過**，准進階段二。

### 0.1 三軸成熟度 zero-trust 實測評級（依 `AutoSDD_Maturity_Rubric.md` L0–L10）

| 軸 | 級別 | 最強證據（file:line） | 卡點 |
|----|------|----------------------|------|
| **C 引擎自治** | **L4**（萌 L5） | 有界重試/修正 `core/kernel.py:155-244`；自動演化重載 `execution/playbook_runner.py:351-368`＋`evolution/minimax_evolver.py`/`playbook_evolver.py`；跨 session 元學習 `plugins/preference_memory_plugin.py`/`goal_progress_plugin.py`/`knowledge_base_plugin.py`；goal 拆解＋🔴 signoff 硬閘 `execution/goal_decomposer.py:138-145` | **演化結果自動重載無 signoff 守界**（`playbook_runner.py:368` 直接 continue），與 L5「範圍·預算·終止由硬閘＋人工 signoff 守界」不一致 → 記 **DEF-13-004** |
| **B 流程自治** | **L3**（萌 L4） | FSM 自動轉移 `tools/fsm_runtime/fsm_runtime.py:96-127`；凍結規格→pytest 自動鏈 | 每個 SCG 閘門需 HUMAN_PENDING（🔴 紅線本就不可自動跳）；規則不自演化（需人工 version bump+TLC）；僅 smoke 驗證 |
| **A 協作自治** | **L3**（萌 L4） | 規格→playbook 自動編譯 `infra/adapters/sdd_to_playbook_adapter.py:99-130`；凍結硬閘 `:135-150`；e2e smoke `tests/integration/test_sdd_bridge/test_bridge_smoke.py` | **僅 2-AC/3-AT smoke 載具驗證過全鏈**，無真實多-AC/多-AT 端到端證據 → 無法宣稱 >L3 |

**上捲**：`L_合體 = min(C=L4, B=L3, A=L3) = **L3**`（萌 L4）。一致性不變式 `A ≤ min(B,C)`：L3 ≤ min(L3,L4)=L3 ✓。

**最弱軸＝A、B 並列 L3**，共同卡點＝「只在 trivial smoke 驗證、從未在真實多-AC 規格端到端跑綠」。

---

## 1. `<Architecture_Design_Review>`（強制自我檢核）

> **本輪改動面**：純 AutoClaude 整合層。**AISDLC_SDD v0.01~v0.05 凍結本體零改動**（故無 Copy-on-Evolve、無五軌 TLC 觸發）。生產碼僅 `config.py`(+6)、`playbook_runner.py`(+43)；其餘為新測試。

### W-13-1（多-AC 橋接 e2e 載具，升 A 軸）
| 檢核項 | 結論 |
|--------|------|
| 1.1 架構純潔性 | **維持**。純 additive 測試＋fixture，零生產碼、零 God-object、Thin Facade 不碰。 |
| 1.2 持久化相容 | **N/A**。零 checkpoint/DAL 觸碰。 |
| 1.3 安全防護網 | **加壓不弱化**。多-AC 規格更多 AT_id 經白名單模板/黑名單字元消毒（`sdd_to_playbook_adapter._sanitize`），無新注入面。 |
| 1.4 對外 I/O 安全 | **N/A**。零 `ToolInvocationPort`。 |

### W-13-2（演化 signoff 守界，補 C 軸 L5 一致性，DEF-13-004）
| 檢核項 | 結論 |
|--------|------|
| 1.1 架構純潔性 | **維持**。run() 既有迴圈本就有 `max_evolutions`/`auto_resume` 兩道預算閘，新增 signoff 閘同構、非業務邏輯；決策抽 ~22 行 helper `_evolution_signoff_granted`，facade **437<450** 行預算內。 |
| 1.2 持久化相容 | **維持**。無新 `PlaybookCheckpoint` 欄位、零 DAL 觸碰，additive config flag。 |
| 1.3 安全防護網（fail-closed） | **強化**。flag=True 但 approver 缺失/拒絕/例外 → deny 停機不重載＋審計痕，對齊 `goal_decomposer` signoff + `enable_kernel_brain` flag-gate 雙前例。 |
| 1.4 對外 I/O 安全 | **N/A**。 |
| 零退化 | config `require_evolution_signoff` 預設 **False** ＝現行 Gap-012-D 自動重載完全不變；既有 `test_gap012` 35 重載測試零退化。 |

**結論：八項全數維持/N/A/強化，無架構衝突、無凍結本體誤改、無安全弱化。**

---

## 2. 本輪增量設計 — W 項

### 2.1 W-13-1：多-AC SDD 規格 → playbook → 端到端跑綠載具（升 A 軸 L3→L4）

**目的**：把 A 軸從「只 smoke（無法宣稱 >L3）」帶到「真實多-AC 規格 0 行人工改碼自動驅動到綠燈」的可量測 L4 信號。

**介面 delta**：純新增測試 `AutoClaude/tests/integration/test_sdd_bridge/test_bridge_multi_ac.py`（含 3-AC/6-AT 凍結規格 fixture）。複用既有 `_write_fsm_state`、`sdd_compile` CLI、`SddToPlaybookAdapter`、`SddGovernancePlugin`、`PlaybookKernel`，**零生產碼改動**。

**壓測之未覆蓋路徑**（smoke 僅 2-AC/3-AT 未及）：
1. 跨 3 個 AC 邊界的 `maintain_context` 序列＝`F,T,T,F,T,F`（含**連續同-AC 兩次 True**，smoke 僅單次 True）。
2. 混合測試型別 → SCG 閘門 retry 映射＝`[5,5,5,5,5,2]`（Unit/Integration/Contract→SCG-4=5，E2E→SCG-5=2）。
3. 三種 Gherkin Then 斷言型別同存一規格：引號字面（`餘額不足`/`借貸平衡`）、HTTP 狀態碼（`(?i)(201|created)`/`(?i)(200|ok)`）、量化 NFR→weak fallback（2 筆＝AT-002-1-2/AT-003-1-1，必經 `IObservabilityPort` 留審計痕）。
4. 全鏈 6 步經真 kernel + 真 governance plugin 跑綠、零契約違反；含規格先行硬閘攻防（退回 SPEC_DRAFTING → pre_run veto、零步驟執行）。

**LOC/契約影響**：純測試，零 `.importlinter`、零 checkpoint。

### 2.2 W-13-2：演化版重載 L5 signoff 守界（DEF-13-004，補 C 軸一致性）

**根因**：見 §0.1 C 軸卡點 — Gap-012-D 自動重載具預算/終止硬閘但缺人工 signoff，與量表 L5 定義不一致。

**介面 delta**：
- `autoclaude/utils/config.py`：`PlaybookConfig.require_evolution_signoff: bool = False`（預設 off＝零退化）。
- `autoclaude/execution/playbook_runner.py`：
  - 建構子新增 keyword-only `evolution_approver: Optional[object] = None`（hex 可選注入，同 executor/evaluator/brain）。
  - 新增 helper `_evolution_signoff_granted(count, evolved_path) -> bool`：flag off 永遠放行；flag on 須 approver 回傳 True，approver 缺失/例外 fail-closed deny。
  - run() 重載 gate 前插 signoff 檢查；未獲准 → 停機不重載（`return result`，落入終止回報）＋ `_notify` 審計痕。

**LOC/契約影響**：facade 394→**437** 行（<450 預算）；零 `.importlinter` 影響（同層內新增方法/欄位）；零 checkpoint 欄位。

---

## 3. 階段三：實作與雙重驗證（逐項實測）

| W 項 | 單測/契約測試 | 結果 |
|------|-------------|------|
| W-13-2 | `tests/test_def_13_004_evolution_signoff.py`（9 case）+ `test_gap012.py`（35 重載回歸） | **44 passed**（0.73s）；既有重載零退化 |
| W-13-1 | `tests/integration/test_sdd_bridge/test_bridge_multi_ac.py`（7 case） | **7 passed**（0.52s）；6 步全綠、maintain_context/retry/weak 審計全符 |

**誠實補述**：W-13-1 原預期可能揪出橋接框架缺陷（B 軌回流），實測**未現缺陷**——證實 `SddToPlaybookAdapter` 在 3-AC/6-AT 非 trivial 輸入下解析/編譯/全鏈執行皆正確，此為 A 軸的**正面**成熟度證據（非缺陷掩蓋）。

---

## 4. 階段四：CI 平價收斂（全項零退化矩陣，2026-06-15 親跑）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ floor 3075 / 0 failed | **3091 passed / 122 skipped / 0 failed**（102.29s）✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | **violations=0**（total 17549）✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **exit 0**（v0.01:1478/v0.05:1499/scripts/tests:24）；本輪零 AISDLC_SDD 改動 ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **N/A**（無 .tla/_HAPPY_PATH 變更） |

**floor 更新**：本輪交付後新 floor = **3091**（下一輪階段一以此為硬閘下限）。

---

## 5. RTM（需求→實作→驗證追溯）

| W 項 | 驅動 | 推進軸 | 實作 | 驗證 | 狀態 |
|------|------|--------|------|------|------|
| W-13-1 | A/B 軸最弱（L3，只 smoke） | A 協作 L3→L4 信號 | `test_bridge_multi_ac.py`（fixture+e2e，零生產碼） | 7 passed；6 步全綠/maintain_context F,T,T,F,T,F/retry 5,5,5,5,5,2/weak 2 筆審計 | ✅ |
| W-13-2 | DEF-13-004（C 軸 L5 一致性） | C 引擎 L4→L5 | `config.py` flag + `playbook_runner.py` signoff gate | 9 passed + gap012 35 零退化 | ✅ |

**成熟度結語（誠實）**：本輪 A 軸實證升至 L4 信號、C 軸補上 signoff 守界（L5 一致性閉合其一缺口）；但 `L_合體 = min(A,B,C)` 仍受 B 軸 L3（SCG HUMAN_PENDING 為 🔴 紅線不可自動跳、規則不自演化）卡住，**L_合體 維持 L3（萌 L4）**。北極星推進是多輪程式——本輪在最弱軸放下一塊可量測證據，未虛報 L_合體 躍升。

---

## 6. 本輪非預期觀察（誠實揭露）

工作樹另含一筆**非本輪所做**的改動：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 第 11 行 roleplay 抬頭由「L5 自治系統與微核心架構總監」改為「L10…」（使用者自行編輯）。**未併入本輪 commit**，留待使用者處置。
