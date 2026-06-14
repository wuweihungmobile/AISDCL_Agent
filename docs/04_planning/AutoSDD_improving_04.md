# AutoSDD_improving_04 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 4 輪）

> **版本**：04（第四輪迭代）
> **日期**：2026-06-14
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ **已凍結**（2026-06-14 🔴 人工確認：使用者於本日 session AskUserQuestion 明示選定「只做 DEF-03-001（P2）」+ 修復設計「雙軌：凍結基線 v0.01 + 最新演化版」）。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3069 passed / 122 skipped / 0 failed**（2026-06-14 本機實測 95.37s，**非引用文件數字**）；AISDLC_SDD 雙軌閘門必須全綠。
> **本輪選定範圍**（使用者凍結）：**W1** = DEF-03-001（P2）`ci-gate.sh` 雙軌版本閘門（B 軌框架共享 CI infra）。**單一 W 項**（Rule 2 Simplicity First）。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-14，非文件宣稱）

本計畫所有設計皆錨定下列**已實測事實**（出處：2026-06-14 親自實測 + 逐檔開檔複驗）：

| # | 事實 | 證據位置 | 對設計的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套 = **3069 passed / 122 skipped / 0 failed**（95.37s） | 本機 `python -m pytest tests/ -q` | 本輪零退化 floor = 3069（禁寫死） |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports` | 架構紅線，以實際 8 條為準 |
| F3 | AISDLC_SDD `ci-gate.sh`（修復前）= **exit 0**（pytest not-chaos 全綠 + arch_fitness advisory warn 不阻擋）；**實測僅跑 v0.01** | `bash scripts/ci-gate.sh`（AISDLC_SDD 根） | DEF-03-001 重現：官方閘門只測凍結基線 |
| F4 | `check_loc_budget` violations=0（total 17511 ≤ cap 20438）；`snapshot_sync --check` 新鮮 | 本機實測 | 既有紅線無欠帳 |
| F5 | **`scripts/ci-gate.sh:17` 寫死 `FW_DIR=...AISDLC_SDD_v0.01`**，且檔案位於 `AISDLC_SDD/scripts/`（**versioned 目錄之外＝共享 CI infra，非凍結本體，修改免 Copy-on-Evolve**） | 開檔 `scripts/ci-gate.sh:16-18` | W1 修復面乾淨，免版本演化 |
| F6 | **v0.04 能過完整閘門**：pytest not-chaos = **1494 passed / 4 skipped / 34 deselected / 14 subtests passed**（23.92s）；arch_fitness --strict = **exit 0**（僅 FF-16 advisory，無 structural fail） | 本機 `cd v0.04 && pytest -m "not chaos"` + arch_fitness | 雙軌設計可行：最新版 v0.04 乾淨入閘 |
| A1 | 上輪 W1（DEF-01-008）構件存在且被測試覆蓋：`config.py`/`main.py:101`/`tests/integration/test_def_01_008_brain_injection.py` 三處 `enable_kernel_brain` flag-gated | Grep | 上輪交付屬實 |
| A2 | 上輪 W2（DEF-02-002）構件存在：v0.04 `tlc_runner.py:52 parse_tlc_summary` + `:69` fail-closed 斷言 + `tests/.../test_tlc_runner_parsing.py` | Grep/find | 上輪交付屬實 |
| A3 | DEF-02-002 修復鐵證：EVOLUTION_LOG v0.04 記 SDD_FSM GENERATED 由 first-match 誤報 **706** → last-match 真值 **4706**，`generated(4706) ≥ distinct(855)` 恆等不變量現成立 | `EVOLUTION_LOG.md:13` | DEF-02-002 確認 fixed |

**硬閘判定**：F1 基線 0 failed 且 3069 = 上輪 floor → **通過，准進階段二**。本輪零退化 floor 錨定 = **3069**。

**繼承缺陷處置（見 §6）**：DEF-03-001（本輪 W1 修）、DEF-02-001（同根 P3，本輪未取、續 open watch）、DEF-01-007（cc-switch 環境工具，續 open）、DEF-01-009（plugin 250 行 watch）。

---

## 1. `<Architecture_Design_Review>`（寫任何實質程式前強制自我檢核）

> 本輪 W1 主體為 **AISDLC_SDD 共享 CI infra 腳本 `scripts/ci-gate.sh`（bash）** + 一支版本解析回歸測試。AutoClaude 微核心 `core/`/`plugins/`/`adapters/` **零改動**；AISDLC_SDD 凍結本體（v0.0X 的 agent/governance/workflow/tools）**零改動**。

### 1.1 架構純潔性 — 是否創造 God-object？Thin Facade 是否維持？

**否，且維持。** W1 只改 `scripts/ci-gate.sh`（本就是 CI 編排腳本，無業務邏輯），將「寫死單版」改為「對凍結基線 + 自動偵測最新演化版雙軌各跑一次同一組檢查」。不新增 plugin/port/adapter/class，不碰 AutoClaude 任何檔，不碰 AISDLC_SDD 任一 v0.0X 凍結本體。腳本仍是 thin 編排（pytest + arch_fitness + 選配 TLC），無 God-object。

### 1.2 持久化相容 — 新狀態是否 additive？DAL 三後端零停機是否維持？

**N/A 且維持。** W1 純屬 CI 閘門腳本，**零持久化觸碰**（無 alembic、無 PlaybookCheckpoint、無 DAL）。版本解析為純讀（`ls` 列舉版本目錄）。新增測試 `scripts/tests/test_ci_gate_version_resolution.py` 為純讀 dry-run，無副作用。

### 1.3 安全防護網 — CONDITIONAL 白名單能否攔截鏈式攻擊向量？

**N/A 且零弱化。** W1 不新增任何「從文件生成指令」路徑。版本清單來自 `ls -d AISDLC_SDD_v0.0*` 的磁碟目錄名（固定前綴 glob，非外部輸入），`SDD_FW_VERSION` 覆寫為 operator 本機 debug 用途。CONDITIONAL 三層防禦（白名單 regex + 黑名單字元 + shell=False/shlex）與本輪無交集，一行不改。

### 1.4 對外 I/O 安全 — 本輪是否新增 `ToolInvocationPort` 外呼路徑？

**否。** W1 為純本機 CI 腳本（pytest/arch_fitness/可選 java TLC 皆本機 subprocess），零外呼端點、零新網域、零 `ToolInvocationPort` 觸碰。SSRF/allowlist 攻擊面零變化。

**結論：四項檢核全數自洽，W1 為共享 CI infra 之版本治理修復，無架構衝突，無凍結本體改動，准予進入設計細節。**

---

## 2. W1 設計 — DEF-03-001 ci-gate.sh 雙軌版本閘門（B 軌共享 infra）

### 2.1 問題（F3/F5）

`scripts/ci-gate.sh:17` `FW_DIR="${REPO_ROOT}/AISDLC_SDD_v0.01"` 寫死 → 該腳本（自述為 `.github/workflows/ci.yml`/docker ci-runner/pre-push/act 的**單一真相源**）**永遠只測 v0.01 凍結基線**。實際承載框架演化的 v0.02/v0.03/v0.04（EVOLUTION_LOG 自述「可修改版本」）**不在官方閘門/CI/pre-push 覆蓋內**，僅靠人工 `cd vX && pytest -m "not chaos"` 守護。最新版＝實際改動版反而無自動化閘門，與「地端 = CI = ubuntu-latest 同一組檢查」初衷相違（DEF-03-001 P2）。

### 2.2 落地決策：雙軌（凍結基線 + 自動偵測最新演化版）

採使用者凍結之 Option B：

- **軌一（凍結基線）**：恆測 `AISDLC_SDD_v0.01` → 回歸防護（凍結基線永不破）。
- **軌二（演化軌）**：`ls -d AISDLC_SDD_v0.0* | sort -V | tail -1` 自動偵測語意版本最高者（現為 v0.04）→ 使**最新演化版恆納入官方閘門**，直接關閉 DEF-03-001 治理缺口。
- **逃生口**：`SDD_FW_VERSION=<ver>` 覆寫為單一版本（debug / 二分定位），跳過雙軌。
- **可測性**：`SDD_GATE_DRY_RUN=1` 僅印出將測版本清單即 exit 0（供測試鎖定解析邏輯，不實跑 pytest）。

「自動偵測最高版」而非「再寫死 v0.04」是關鍵——避免下次演化到 v0.05 時缺口復發（測試 `test_latest_is_highest_semver_not_hardcoded` 守此意圖）。

### 2.3 介面 delta

**(a) `AISDLC_SDD/scripts/ci-gate.sh`**（共享 infra，非凍結本體）
- 版本解析區塊：`FROZEN_BASELINE` + 自動偵測 `LATEST` → `FW_VERSIONS` 陣列。
- `SDD_FW_VERSION` 覆寫 + `SDD_GATE_DRY_RUN` dry-run（皆 additive，預設行為 = 雙軌）。
- 將原 [1/3][2/3][3/3] 三步驟包進 `run_gate_for_version()` 函式，對 `FW_VERSIONS` 迴圈。
- arch_fitness exit 語意不變（≥2 structural fail 阻擋；1 advisory 放行）。

**(b) `AISDLC_SDD/scripts/tests/test_ci_gate_version_resolution.py`**（新增，純解析測試）
- 4 case，以 dry-run 輸出鎖定解析意圖（見 §2.4）。

### 2.4 測試衝擊（additive，Rule 9 測意圖）

`scripts/tests/test_ci_gate_version_resolution.py`（4 case，dry-run 純解析、不依賴 Java/TLC）：
- **test_ci_gate_exists**：腳本存在。
- **test_dual_track_includes_frozen_baseline_and_latest**：雙軌必同時含 v0.01（回歸防護）與磁碟最新版（DEF-03-001 修復點）→ WHY：缺任一 = 治理缺口復發。
- **test_latest_is_highest_semver_not_hardcoded**：演化軌 = 磁碟語意版本最高者，非寫死值 → WHY：直防「又退回寫死某版」原缺陷再現。
- **test_single_version_override_collapses_to_one**：`SDD_FW_VERSION` 覆寫收斂為單版 → WHY：debug 逃生口須生效。

> 跨平台穩健性：測試以 `bash -c '<VARS> bash scripts/ci-gate.sh'` 在外層 shell 自身環境內設變數再呼叫內層腳本，繞過 Windows→WSL bash 不繼承宿主環境變數的屏障（CI 原生 bash 亦適用）。

### 2.5 LOC 預算落點

- `ci-gate.sh`：bash 腳本，非 LOC 分級政策受控之 Python tier（`check_loc_budget` 僅計 AutoClaude Python）。
- 新測試檔：tests/ 不計 LOC 預算。
- **AutoClaude 零改動 / AISDLC_SDD v0.0X 凍結本體零改動**。

### 2.6 `.importlinter` 影響分析

- W1 不觸碰 AutoClaude 任何 Python 模組 → AutoClaude `.importlinter` 8 條 contract **零影響**，預期維持 8 kept / 0 broken。

---

## 3. 階段四 — CI 平價與驗證

### 3.1 雙軌閘門實跑（W1 驗證載體）

```bash
cd AISDLC_SDD
bash scripts/ci-gate.sh         # 雙軌：v0.01 + v0.04 各跑 pytest not-chaos + arch_fitness
SDD_GATE_DRY_RUN=1 bash scripts/ci-gate.sh   # dry-run 驗證版本解析
python -m pytest scripts/tests/test_ci_gate_version_resolution.py -v   # 解析回歸測試
```
通過條件：雙軌 exit 0（v0.01 + v0.04 各自 pytest not-chaos 全綠 + arch_fitness exit<2）；解析測試 4 passed。

### 3.2 零退化驗證矩陣（本輪 DoD；floor 以本輪實測為準）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **≥ 3069 passed / 0 failed**（floor=F1；W1 不碰 AutoClaude，結構性持平） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken（實際 8 條） |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 雙軌閘門 | `bash scripts/ci-gate.sh` | **v0.01 + v0.04 雙軌** pytest not-chaos 全綠 + arch_fitness exit<2 |
| 版本解析測試 | `pytest scripts/tests/test_ci_gate_version_resolution.py` | 4 passed |
| 五軌 TLC | **不觸發**（W1 無 `_HAPPY_PATH`/`.tla` 改動，Rule 9.18.1 不啟動） | N/A |

---

## 4. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 落點 | 驗證 |
|------|------|------|
| DEF-03-001：最新演化版納入官方閘門 | §2.2 演化軌自動偵測 | dry-run 含 v0.01 + v0.04；雙軌閘門實跑 v0.04 通過 |
| 凍結基線回歸防護不丟 | §2.2 軌一恆測 v0.01 | dry-run 含 v0.01；雙軌閘門實跑 v0.01 通過 |
| 防「又退回寫死版本」缺陷再現 | §2.2 sort -V 自動偵測 | `test_latest_is_highest_semver_not_hardcoded` |
| debug 逃生口 | §2.2 `SDD_FW_VERSION` 覆寫 | `test_single_version_override_collapses_to_one` |
| 共享 infra 修復免 Copy-on-Evolve | F5 腳本在 versioned 目錄外 | git diff 僅 `scripts/`，v0.0X 凍結本體源碼零改動 |
| 零退化 | W1 不碰 AutoClaude | 3069 passed 持平 |

---

## 5. 實作順序（每支完成立即驗證，絕不累積）

> B 軌 Brownfield：本計畫即 SCG-0/1 載體；§2.2-2.3 介面/邊界 = SCG-2；§2.3 delta = SCG-3；落版過 SCG-4；§3.2 矩陣 = SCG-5 RTM。行進中框架摩擦即記入 `AutoSDD_Defect_Log.md`（DEF-04-xxx）。

- **W1-a** `ci-gate.sh` 改雙軌 + dry-run + 覆寫 → `bash -n` 語法檢查 + dry-run 驗證版本解析。✅
- **W1-b** 新增 `test_ci_gate_version_resolution.py`（4 case）→ 跑該檔全綠。✅
- **W1-c** 實跑雙軌閘門（v0.01 + v0.04）→ exit 0。
- **W1-d** 零退化矩陣全項（AutoClaude 3069 / lint-imports 8 / LOC 0 / snapshot 新鮮）。
- **收斂**：任一紅 → 停機修復。

每個 W 結束跑對應驗證；零退化矩陣為本輪硬閘。

---

## 6. 缺陷帳本本輪處置（對照 §0 繼承）

| 缺陷 | 本輪處置 |
|------|---------|
| DEF-03-001（P2, open routed候選下輪） | **本輪 W1 修**（雙軌版本閘門）→ 完成後改 `fixed@improving_04` 附證據 |
| DEF-02-001（P3, open） | 同根（Copy-on-Evolve 跨版測試 rootdir 隔離），本輪未取；惟 W1 後官方閘門雙軌仍各自 `cd vX` 單版獨立跑（不跨版同跑），故 DEF-02-001 的 sys.modules 同名碰撞風險**不被本輪放大**；續 `open`（候選下輪） |
| DEF-01-007（P3, open） | cc-switch 環境工具未裝，本輪不涉 A/B 驗收，續 `open`（watch） |
| DEF-01-009（P3, open watch） | 本輪不碰 `sdd_governance_plugin.py`，續 `watch` |
| 本輪新發現 | 行進中即記 DEF-04-xxx（發現即記、絕不累積） |

---

## 7. 🔴 人工確認凍結點

本文件為 SCG-0/1 規格載體。**實作（W1-a）啟動前須由人類明示確認本計畫凍結**（B 軌紅線：HUMAN_PENDING 不可自動跳過）。**已於 2026-06-14 取得**：使用者經 AskUserQuestion 明示選定「只做 DEF-03-001（P2）」+ 修復設計「雙軌：凍結基線 v0.01 + 最新演化版」。凍結後依 §5 實作順序執行，全程套 §3.2 零退化矩陣，收尾走多專家 Zero-Trust 審查閉環。
