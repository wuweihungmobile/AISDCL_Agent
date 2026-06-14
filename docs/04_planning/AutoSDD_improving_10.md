# AutoSDD_improving_10 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 10 輪）

> **版本**：10（第十輪迭代）
> **日期**：2026-06-14
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ 結案。範圍＝**按需單一驅動**——🔴 人工方向確認選定「**補裝 cc-switch 關 DEF-01-007**」。階段一深度重偵察揪出真實阻塞：A/B 關閉路徑**不可執行**（載具缺失 + GUI/CLI 偵測落差），記為 **DEF-10-001** 並即修；DEF-01-007 由此**縮窄**為純環境/API 動作。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3075 passed / 122 skipped / 0 failed**（2026-06-14 本機實測 99.25s，**非引用文件數字**；上輪 floor 3069 + 6 新載具參數化 case）；AISDLC_SDD 雙軌閘門 exit 0。
> **本輪定位**：承 improving_06（A 軌主鏈結案）／07（DEF-06-001 取證友善性）／08、09（兩輪健康確認盤點）。階段一證實「再產第三次空輪＝為遞增而遞增」，故 🔴 人工選定唯一真實小驅動：關閉長期 open 的 DEF-01-007。**邊界＝倉內賦能（免 token）**：移除所有倉內阻塞使關閉路徑可一鍵執行；live A/B 的環境/API 動作保留交付使用者。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-14，非文件宣稱）

本計畫所有判斷皆錨定下列**已實測事實**（主 agent 親跑，非引用文件）：

| # | 事實 | 證據位置 | 對本輪的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套（**改動前**）= **3069 passed / 122 skipped / 0 failed**（98.26s） | 本機 `python -m pytest tests/ -q`（背景作業 b0ssu2zn3 尾行） | 硬閘 floor=3069，0 failed → **通過** |
| F1' | AutoClaude 全套（**改動後**）= **3075 passed / 122 skipped / 0 failed**（99.25s） | 本機 `python -m pytest tests/ -q`（背景作業 by5o0ged9 尾行） | 新 floor=**3075**（+6＝新載具被 `test_yaml_import.py` glob 參數化，只增不減、0 failed） |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports`（改動後重跑持平） | 架構紅線 8 條全保 |
| F3 | AISDLC_SDD `ci-gate.sh` 雙軌 = **exit 0**；v0.01:**1478** / v0.04:**1494** | `bash scripts/ci-gate.sh`（背景作業 bverztel6，`/tmp/cigate_10.log` 收斂行自證逐軌計數） | 雙軌健康；DEF-06-001 修復無回歸（V1） |
| F4 | LOC budget violations=**0**（total=17511 / baseline=17032 / cap=20438） | `python tools/check_loc_budget.py`（改動後持平＝零 python 變更） | 分級政策全過 |
| F5 | snapshot = **OK** | `python tools/snapshot_sync.py --check`（改動後持平） | 文件新鮮 |
| A1 | DEF-01-007（cc-switch）使用者**已實裝**，但 `command -v cc-switch`=**NOT FOUND** | 使用者 2026-06-14 補述「已安裝 cc-switch」+ 本機 `command -v cc-switch`=NOT FOUND | 實證 **DEF-10-001(b)**：主流 cc-switch 為 GUI app 不上 PATH |
| A2 | DEF-01-009（`sdd_governance_plugin.py` raw 250）持平、已自癒 | `awk END NR`=250 + F4 violations=0 | 維持 open watch，本輪零擴充不觸發 |
| A3 | 上輪修復構件全部存在 | `pytest_passed_count.sh` / `cross_version_guard.py` / `conftest.py` / 3 組 `scripts/tests/` / `test_def_01_008_brain_injection.py` / `enable_kernel_brain`(main.py+config.py) 皆 `ls`/`grep` 證實 | (d) 構件存在性 PASS |
| **N1** | **本輪新發現缺陷 DEF-10-001**：A/B 關閉路徑不可執行 | (a) `find . -iname "sdd_bridge_smoke*.yaml"`=零命中；(b) `integration_gate.ps1:66` `Get-Command cc-switch` 假設 CLI 但實況 GUI | 觸發本輪 W 項（§2） |

**硬閘判定**：F1 基線 0 failed 且 3069 = 上輪 floor → **通過**，准進階段二。

---

## 1. `<Architecture_Design_Review>`（強制自我檢核 — 寫任何實質改動前）

> **本輪改動面**：**零 python 變更**。僅 (i) 新增靜態 playbook YAML `AutoClaude/scripts/sdd_bridge_smoke.yaml`；(ii) 修改共享 infra 腳本 `tools/integration_gate.ps1` [5/5] 段（偵測邏輯 + 訊息）。AutoClaude 微核心 `core/`/`plugins/`/`adapters/`/`ports/` 零改動；AISDLC_SDD 凍結本體零改動；**免 v0.05 Copy-on-Evolve**。

| 檢核項 | 結論 |
|--------|------|
| 1.1 架構純潔性（God-object / Thin Facade） | **維持**。零碰 kernel/plugin/port/adapter；`playbook_runner.py` Thin Facade 不變。新載具為標準 Playbook schema 靜態資料，不引入任何業務邏輯。 |
| 1.2 持久化相容（additive / DAL 三後端零停機） | **N/A 且維持**。零 alembic / 零 `PlaybookCheckpoint` 欄位 / 零 DAL 觸碰。 |
| 1.3 安全防護網（CONDITIONAL 鏈式攻擊） | **零弱化**。新載具的 `evaluator_command: pytest smoke_add_test.py -q` 為**靜態字串**，循既有 `ShellEvaluator` 消毒路徑，非「從文件生成指令」的動態鏈；gate `[5/5]` 的 CLI 偵測為**固定 allowlist** `@("cc-switch","cc-switch-cli","ccs")`（無使用者輸入、無 shell 插值注入面）。CONDITIONAL 三層防禦與本輪零交集。 |
| 1.4 對外 I/O 安全（`ToolInvocationPort` 外呼） | **N/A**。零新外呼端點、零新網域。cc-switch 為使用者**自行於 shell 執行**的外部工具，**非**本系統經 `ToolInvocationPort` 發起的網路 I/O，無 SSRF/allowlist 攻擊面變化。 |

**結論：四項檢核全數維持，無架構衝突、無凍結本體改動、無安全弱化。本輪不撰寫任何實質 Python。**

---

## 2. 本輪增量設計 — W 項（按需單一驅動）

### 2.1 為何本輪有 W 項（對比 08/09 拒絕製造工作）

improving_08/09 為健康確認盤點輪（無驅動則不製造工作）。本輪**有真實驅動**：

1. 🔴 人工方向確認（§7）於四選項中選定「**補裝 cc-switch 關 DEF-01-007**」——DEF-01-007 是唯一「open 可變可行動」的真實小驅動。
2. 階段一為執行該方向而深度重偵察 A/B 關閉路徑，**揪出 DEF-10-001**：關閉路徑**根本不可執行**（見 §0 N1）。此為框架自我警告的反例——不是「為遞增而遞增」，而是「使用者指定方向時發現的真實缺陷」。

### 2.2 W-10-1：移除 DEF-01-007 倉內阻塞，使 A/B 關閉路徑可一鍵執行

**根因拆解**（DEF-10-001，兩缺口）：

| 子缺口 | 現象 | 修法 |
|--------|------|------|
| (a) A/B 載具缺失 | §5.2/gate [5/5] 引用 `sdd_bridge_smoke.yaml` 全倉不存在 → `autoclaude … --fresh` 必 file-not-found | 建 `AutoClaude/scripts/sdd_bridge_smoke.yaml`（自包含 2 步 `aisdlc_sdd` TDD 載具） |
| (b) GUI/CLI 偵測落差 | gate `Get-Command cc-switch` 假設 CLI；主流 farion1231/cc-switch 為 GUI app 不上 PATH（使用者實裝實證） | gate [5/5] 改多 CLI 名偵測迴圈 + 驗載具存在 + 訊息釐清 GUI≠CLI、指向 CLI 變體 |

**介面 delta**：
- 新檔 `AutoClaude/scripts/sdd_bridge_smoke.yaml`（資料層；非 python，不入 LOC budget）。schema＝標準 `Playbook`（`version`/`project`/`workflow_type=aisdlc_sdd`/`global_goal`/`global_invariants`/`tasks[S01,S02]`）。
- `tools/integration_gate.ps1` [5/5] 段：`foreach($name in @("cc-switch","cc-switch-cli","ccs")){…}` 偵測 + `Test-Path $smokePb` 驗載具 + SKIP/PASS 訊息重寫。**無新增段、無改 exit 語意**（仍 PASS/SKIP 不阻擋）。

**LOC 預算落點**：零 python 變更 → 不觸 `check_loc_budget`。ps1 不計入 LOC tier。

**對 `.importlinter` 各 contract 的影響**：**零**。無 python import 變動，8 條 contract 不受影響（改動後實測 8 kept / 0 broken）。

**checkpoint additive 欄位需求**：**無**。

### 2.3 DEF-01-007 縮窄後的殘留（交付使用者的環境/API 動作）

倉內阻塞清除後，DEF-01-007 縮窄為**純環境/API 動作**，維持 open（非純程式可修）：

1. 裝 cc-switch **CLI 變體**（[SaladDay/cc-switch-cli](https://github.com/saladday/cc-switch-cli)；主流 GUI 版不上 PATH，無法供 headless 自動 A/B）。
2. 配 2 個 model profile（含各自 API key／端點）。
3. 授權 token 花費，於 `AutoClaude/` 執行（程序見 `scripts/sdd_bridge_smoke.yaml` 檔頭）：
   ```
   cc-switch use <profile-A> && autoclaude scripts/sdd_bridge_smoke.yaml --fresh
   cc-switch use <profile-B> && autoclaude scripts/sdd_bridge_smoke.yaml --fresh
   ```
   對比四指標：**一次通過率 / CORRECTION 次數 / SDD_CONTRACT_VIOLATION 次數 / token 峰值**。

> **B 軌 Dogfooding 邊界釐清（誠實聲明）**：本輪「補裝 cc-switch」係使用者依其環境理解所為；經查證 cc-switch **並非系統依賴**——AutoClaude/AISDLC_SDD 全套 3075 passed、雙軌 ci-gate exit 0 皆**不碰 cc-switch**，它僅是 DEF-01-007 的**選配 A/B 驗收工具**。此澄清已向使用者明示。

---

## 3. 階段四 — CI 平價與驗證（零退化矩陣全項，floor 以本輪實測為準）

| 檢查 | 命令 | 通過條件 | 本輪實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 上輪 3069 / 0 failed（新測試只增不減） | ✅ **3075 passed / 122 skipped / 0 failed**（+6 新載具參數化） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | ✅ **violations=0**（total 17511 持平＝零 python 變更） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2 | ✅ **exit 0**（v0.01:1478 / v0.04:1494） |
| 整合閘門 | `integration_gate.ps1 -SkipFull` | [3]+[4] PASS、[5] SKIP 非偽綠、exit 0 | ✅ **exit 0「2 PASS / 1 SKIP」**（[3] bridge 7 passed、[4] 回退 2 passed、[5] 新訊息自證） |
| 五軌 TLC | （僅 FSM 變更時） | 五軌 0 violation | **N/A**（本輪零 FSM／`*.tla`／`_HAPPY_PATH` 變更） |

DAL 等價：本輪零持久化／DAL 觸碰，三後端等價性不受影響。

---

## 4. 缺陷帳本本輪處置（對照 §0 繼承）

| ID | 嚴重度 | 上輪狀態 | 本輪處置 |
|----|--------|---------|---------|
| DEF-10-001 | P3 | （本輪新發現） | **fixed@improving_10**：建 A/B 載具 + 硬化 gate [5/5]（多 CLI 偵測 + 驗載具 + GUI/CLI 釐清）。證據見 §2.2 + Defect_Log |
| DEF-01-007 | P3 | open | **維持 open 但縮窄**：倉內阻塞全清（DEF-10-001 fixed），縮窄為純環境/API 動作（§2.3）；使用者實裝為 GUI 版（NOT FOUND on PATH）實證 DEF-10-001(b) |
| DEF-01-009 | P3 | open watch | **維持 open watch**：raw 250 持平、已自癒（violations=0）、本輪零擴充不觸發 |
| DEF-06-001 | P3 | fixed@improving_07 | **複驗無回歸**（V1）：本輪 ci-gate 收斂段自證逐軌計數行正常顯示 |
| 其餘 | — | fixed | 無回歸（F1'~F5/A3 全綠佐證） |

**本輪新發現缺陷**：DEF-10-001（已即修 fixed）。**無虛報、無漏記**。

---

## 5. 實作順序（每支完成立即編譯+測試，絕不累積）

1. **建 `AutoClaude/scripts/sdd_bridge_smoke.yaml`** → 立即驗：`_validate_playbook_format` + `Playbook.model_validate` 載入 OK（project=SDD_Bridge_Smoke / aisdlc_sdd / S01·S02）。
2. **硬化 `tools/integration_gate.ps1` [5/5]** → 立即驗：`integration_gate.ps1 -SkipFull` exit 0「2 PASS / 1 SKIP」、[5] 新訊息解析到載具。
3. **新載具被 `test_yaml_import.py` 參數化** → 立即驗：`-k "sdd_bridge_smoke or success_rate or discover"` 9 passed；全套重測 3075 / 0 failed。
4. **回掃文件引用 drift**（DEF-05-002/DEF-07-001 紀律）→ gate PASS 訊息由「§A」brittle 引用改為自指 `scripts/sdd_bridge_smoke.yaml` 檔頭，drift-free。

---

## 6. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 | 狀態 |
|------|------|------|------|------|
| R-10-1 階段一零信任重偵察 + 硬閘 | §0 事實表 F1~F5/A1~A3/N1 | 主 agent 親跑五項實測 + 構件複驗 + A/B 路徑盤點 | F1=3069/0 failed 硬閘 PASS、揪出 N1 | ✅ PASS |
| R-10-2 關閉 DEF-01-007 倉內阻塞（W-10-1） | §2.2 兩子缺口拆解 | 建載具 + 硬化 gate | 載具載入 OK、gate -SkipFull exit 0、6 參數化 case 綠 | ✅ PASS |
| R-10-3 DEF-10-001 即記即修 | §4 處置 | Defect_Log 新增 DEF-10-001 fixed@improving_10 | 帳本列在、證據附 file:line | ✅ PASS |
| R-10-4 DEF-01-007 縮窄並誠實交付殘留 | §2.3 | Defect_Log 更新縮窄註記 | 維持 open（環境/API），倉內零阻塞 | ✅ PASS |
| R-10-5 零退化矩陣全項綠 | §3 矩陣 | 六項命令親跑 | §3 實測欄全 ✅（floor 3075） | ✅ PASS |
| R-10-6 文件引用 drift 防護 | §5-4 | gate 訊息自指檔頭 | 無 brittle doc-section 耦合 | ✅ PASS |

---

## 7. 🔴 人工確認凍結點

- **方向確認（第一問）**：2026-06-14 🔴 人工於四選項（暫停遞增 / 補裝 cc-switch 關 DEF-01-007 / 指定新 A 軌 scope / 第三次輕量盤點）中選定 **「補裝 cc-switch 關 DEF-01-007」**。
- **邊界確認（第二問）**：2026-06-14 🔴 人工於三選項（倉內賦能免 token / 裝好後跑 live A/B / 只記缺陷不動程式）中選定 **「倉內賦能（免 token）」**。
- **誠實澄清**：使用者補述「我不知道為何要安裝這個，我以為系統需要」→ 已明示 cc-switch **非系統依賴**，僅 DEF-01-007 選配 A/B 工具。
- **結案宣告**：improving_10 為按需單一驅動輪，DEF-10-001 即記即修（fixed），DEF-01-007 倉內阻塞全清並縮窄，零退化（floor 3075）、鏈維持閉合。
- **下一份**：improving_11（按需）——DEF-01-007 殘留待使用者環境就緒（裝 CLI 變體 + 配 profile + 授權 token）後一鍵跑 live A/B 正式關閉；或出現新整合驅動時觸發。
