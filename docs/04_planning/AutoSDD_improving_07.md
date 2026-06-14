# AutoSDD_improving_07 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 7 輪）

> **版本**：07（第七輪迭代）
> **日期**：2026-06-14
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ 設計凍結待 🔴 人工確認（見 §7）；範圍＝**DEF-06-001（P3）取證友善性**單一收尾項。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3069 passed / 122 skipped / 0 failed**（2026-06-14 本機實測 95.15s，**非引用文件數字**）；AISDLC_SDD 雙軌閘門必須全綠。
> **本輪定位**：A 軌主鏈已於 improving_06 結案，本輪為「**按需增量**」——唯一具體驅動＝上輪 routed 之 **DEF-06-001**（單一 P3 共享 CI infra 取證友善性摩擦）。**單一 W 項**（Rule 2 Simplicity First），不為遞增而遞增。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-14，非文件宣稱）

本計畫所有設計皆錨定下列**已實測事實**（主 agent 親跑）：

| # | 事實 | 證據位置 | 對設計的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套 = **3069 passed / 122 skipped / 0 failed**（95.15s） | 本機 `python -m pytest tests/ -q` | 本輪零退化 floor = 3069（禁寫死） |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports` | 架構紅線，以實際 8 條為準 |
| F3 | AISDLC_SDD `ci-gate.sh` 雙軌 = **exit 0**（v0.01: **1478 passed** / v0.04: **1494 passed**，各 not-chaos 全綠 + arch_fitness exit 1 advisory 不阻擋） | `bash scripts/ci-gate.sh`（修復前基線 `/tmp/cigate_before_07.log`） | 雙軌健康；逐軌數字為 DEF-06-001 驗收基準 |
| F4 | `scripts/tests/` = **12 passed**（4 version-resolution + 8 cross_version_guard） | `pytest scripts/tests/ -q` | 共享 infra 既有測試健康，新測試增量於此 |
| **R1** | **DEF-06-001 重現**：修復前 ci-gate 收斂行僅 `✅ 本機 CI 閘門全數通過（版本：v0.01 v0.04）`，**無逐軌 `N passed`**（須另跑 `grep` 才見 1478/1494） | `/tmp/cigate_before_07.log:50`（收斂行）vs `:24`/`:98`（逐軌數字散在各軌 pytest 尾） | 修復錨定點 |
| A1 | DEF-01-007（cc-switch 未裝）仍重現（環境工具，非純程式可修）；DEF-01-009（`sdd_governance_plugin.py` 受控非空行 < 250）已自癒 watch；本輪零擴充不觸發 | improving_06 結案盤點複驗 | §6 缺陷處置 |

**硬閘判定**：F1 基線 0 failed 且 3069 = 上輪 floor → **通過，准進階段二**。本輪零退化 floor 錨定 = **3069**。

---

## 1. `<Architecture_Design_Review>`（寫任何實質程式前強制自我檢核）

> 本輪變更主體為 **AISDLC_SDD 共享 CI infra**：`AISDLC_SDD/scripts/ci-gate.sh`（雙軌收斂補印逐軌 `N passed`）+ `scripts/pytest_passed_count.sh`（可單測的純函式擷取 helper）+ `scripts/tests/test_pytest_passed_count.py`（回歸測試）。AutoClaude 微核心 `core/`/`plugins/`/`adapters/` **零改動**；AISDLC_SDD 凍結本體（v0.0X 的 agent/governance/workflow/tools/.claude）**零改動**；**不做 v0.05 Copy-on-Evolve**（理由見 §2.3）。

### 1.1 架構純潔性 — 是否創造 God-object？Thin Facade 是否維持？

**否，且維持。** `ci-gate.sh` 維持 thin orchestrator；解析邏輯抽出為單一職責純函式 helper（沿用本 repo `cross_version_guard.py`「抽純函式 + 單獨測」既有慣例，Rule 11 Conformance），ci-gate 僅多一個 `GATE_SUMMARY` 陣列 accumulator + 一行收斂輸出。**零業務邏輯新增**，不碰 AutoClaude kernel/plugin/port/adapter。

### 1.2 持久化相容 — 新狀態是否 additive？DAL 三後端零停機是否維持？

**N/A 且維持。** 純屬 CI infra 腳本，**零持久化觸碰**（無 alembic、無 PlaybookCheckpoint、無 DAL）。helper 為純讀（grep 受信 pytest stdout），無副作用、無落檔（用後即 `rm` 暫存）。

### 1.3 安全防護網 — CONDITIONAL 白名單能否攔截鏈式攻擊向量？

**N/A 且零弱化。** 不新增任何「從文件生成指令」路徑。helper 僅以 `grep -oE` 讀取**本地受信 pytest stdout**，無 `eval`、無從輸入構造指令、無 shell 注入面。`set -o pipefail` 保留 → pytest 任一軌 fail（非零）時 `python … | tee` 即非零，`set -e` 在收斂前中止（**硬閘語意一行不改**）。CONDITIONAL 三層防禦與本輪無交集。

### 1.4 對外 I/O 安全 — 本輪是否新增 `ToolInvocationPort` 外呼路徑？

**否。** 純本機腳本，零外呼端點、零新網域、零 `ToolInvocationPort` 觸碰。SSRF/allowlist 攻擊面零變化。

**結論：四項檢核全數自洽，本輪為共享 CI infra 之取證友善性加固，無架構衝突、無凍結本體改動，准予進入設計細節。**

---

## 2. W1 設計 — DEF-06-001 雙軌 ci-gate 逐軌計數取證友善性（B 軌共享 infra）

### 2.1 問題（R1）

improving_06 結案三鏡複核時（QA 鏡，獨立審查 agent 親跑 ci-gate 取證）發現：雙軌閘門尾段僅印總結「✅ 全數通過（版本：v0.01 v0.04）+ exit 0」，**未在收斂彙總印出各軌 `N passed`**。逐軌數字（v0.01:1478 / v0.04:1494）雖存在於各軌 pytest 輸出尾行，但因輸出截斷散落於遠處 → 審查 agent 在 tail 視窗無法獨立複核，須主 agent 另跑 `tee+grep` 補證。硬閘判據（exit 0 + 雙版本名 + arch_fitness exit<2）**不受影響，非阻擋、非偽綠**，純屬零信任取證時需多一道撈取的摩擦。

### 2.2 落地決策：收斂彙總補印逐軌計數（免 v0.05 Copy-on-Evolve）

proportionate（P3 取證友善性）的修法＝**單行自證**：

- **(a) 逐軌擷取 + 收斂彙總**：`run_gate_for_version()` 內以 `tee` 保留 console 串流的同時擷取該軌最終 `N passed`，append 到全域 `GATE_SUMMARY`；雙軌迴圈結束後於收斂行下方印 `逐軌計數：v0.01:1478 v0.04:1494`（對齊 DEF-06-001 原建議格式，無 `passed` 後綴；`passed` 語意由標籤「逐軌計數」+ 上方逐軌 echo 表意），使**單次輸出即自證逐軌結果**，免審計捲動截斷輸出。
- **(b) 純函式 helper**：擷取邏輯抽到 `scripts/pytest_passed_count.sh`（讀 stdin → 印單一整數），使解析意圖能被 `scripts/tests/` 快速單測鎖定（Rule 9 測意圖），ci-gate 僅薄呼叫。
- **(c) 不做 v0.05**：本修復**零觸碰任一 v0.0X 凍結本體**（落點全在 `AISDLC_SDD/scripts/`＝versioned 目錄外＝共享 CI infra），故**不觸發 Copy-on-Evolve**（與 DEF-03-001 / DEF-02-001 一致）。亦**零** `_HAPPY_PATH`/`*.tla` 改動 → **五軌 TLC 不啟動**（Rule 9.18.1 不觸發）。

### 2.3 介面 delta

**(a) `AISDLC_SDD/scripts/pytest_passed_count.sh`**（新增，共享 infra，純函式）
- 讀 stdin（pytest 輸出），印出最終 summary 的 passed 整數：`grep -oE '[0-9]+ passed' | tail -1 | grep -oE '^[0-9]+'`，無匹配印 `0`（fail-soft：取證輔助絕不反害硬閘退出碼）。
- 設計重點：取**最後一個** `N passed`（避免抓中途進度行）；`subtests` 邊界（尾行 `… 14 subtests passed` 第二 token）因 `[0-9]+ passed` 需數字緊鄰 " passed" 而不誤匹配 → 仍回主計數。

**(b) `AISDLC_SDD/scripts/ci-gate.sh`**（additive 修改）
- 函式上方新增 `GATE_SUMMARY=()`。
- `run_gate_for_version()`：pytest 改 `… | tee "$PYTEST_LOG"`（保留串流、`pipefail` 保留硬閘），擷取 `PASSED` 後 `echo "==> [1/3] ${VER}: ${PASSED} passed（not chaos）"` + `GATE_SUMMARY+=("${VER}:${PASSED}")`。
- 收斂行下方新增 `echo "   逐軌計數：${GATE_SUMMARY[*]}"`。

**(c) `AISDLC_SDD/scripts/tests/test_pytest_passed_count.py`**（新增，回歸測試，7 case）
- 純函式單測：plain / **subtests 邊界**（1478 非 14）/ 多行取最終 summary / **多 `N passed` 匹配取最後**（釘 `tail -1` 防退化：改 head -1 即紅）/ 無匹配回 0（fail-soft）/ 含 failed 仍取 passed。subprocess 呼叫（`cwd=REPO_ROOT` + 相對 posix 路徑，繞 Windows→bash 反斜線屏障，與 `test_ci_gate_version_resolution.py` 同手法）。

### 2.4 LOC 預算 / `.importlinter` 影響

- helper / ci-gate：AISDLC_SDD 共享 infra bash，**非** AutoClaude `check_loc_budget` 受控 Python tier（該工具僅計 AutoClaude）。helper 自我約束 ≤ ~15 行；ci-gate 增量 ≤ ~12 行。
- 新測試檔：tests/ 不計 LOC 預算。
- **AutoClaude 零改動** → `.importlinter` 8 條 contract **零影響**，維持 8 kept / 0 broken。

---

## 3. 階段四 — CI 平價與驗證

### 3.1 W1 驗證載體

```bash
cd AISDLC_SDD
printf '1478 passed, 4 skipped, 34 deselected, 14 subtests passed in 24s\n' | bash scripts/pytest_passed_count.sh  # → 1478（subtests 邊界）
python -m pytest scripts/tests/ -q                              # 19 passed（12 既有 + 7 新）
bash scripts/ci-gate.sh                                         # 雙軌 exit 0 + 收斂行印「逐軌計數：v0.01:1478 v0.04:1494」
SDD_GATE_DRY_RUN=1 bash scripts/ci-gate.sh                      # 版本解析不受影響（既有 4 測試守）
```

### 3.2 零退化驗證矩陣（本輪 DoD；floor 以本輪實測為準）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **≥ 3069 passed / 0 failed**（floor=F1；本輪不碰 AutoClaude，結構性持平） | ✅ 3069/0（95.15s） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken（實際 8 條） | ✅ 8 kept / 0 broken |
| AISDLC_SDD 雙軌閘門 | `bash scripts/ci-gate.sh` | v0.01 + v0.04 雙軌 not-chaos 全綠 + arch_fitness exit<2 + **收斂行自證逐軌計數** | ✅（見 §3.3） |
| 共享 infra 測試 | `pytest scripts/tests/` | 全綠（既有 12 + 新 7） | ✅ 19 passed |
| 五軌 TLC | **不觸發**（本輪無 `_HAPPY_PATH`/`.tla` 改動，Rule 9.18.1 不啟動） | N/A | — |

### 3.3 DEF-06-001 驗收（修復前 vs 後，單一輸出自證）

- **修復前**（`/tmp/cigate_before_07.log:50`）：`✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.04）`（收斂行**無**逐軌計數）。
- **修復後**（實測 `/tmp/cigate_final_07.log:152`）：收斂行下方新增 `逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.04:1494` + 各軌 `==> [1/3] <VER>: N passed`（line 25/100）。

---

## 4. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 落點 | 驗證 |
|------|------|------|
| DEF-06-001：雙軌收斂單行自證逐軌計數 | §2.2(a) `ci-gate.sh` `GATE_SUMMARY` + 收斂行 | 修復後 ci-gate 收斂行含 `逐軌計數：v0.01:1478 v0.04:1494` |
| 擷取邏輯可單測（測意圖） | §2.3(b) 純函式 helper | `test_pytest_passed_count.py` 7 case（含 subtests 邊界 / 多匹配取最後 / fail-soft） |
| 硬閘語意不變（任一軌紅不印彙總） | §2.2(a) `tee` + `pipefail` | pytest 失敗時 `set -e` 在彙總前中止；雙軌 gate exit 0 證綠路徑正常 |
| guard 不干擾既有版本解析 | §2.3(b) 不碰 dry-run 分支 | `SDD_GATE_DRY_RUN=1` + 既有 4 version-resolution 測試全綠 |
| 共享 infra 修復免 Copy-on-Evolve | §2.2(c) 落點在 versioned 目錄外 | git diff 僅 `AISDLC_SDD/scripts/`，v0.0X 凍結本體零改動 |
| 零退化 | 不碰 AutoClaude | 3069 passed 持平、lint 8/0 |

---

## 5. 實作順序（每支完成立即驗證，絕不累積）

> B 軌 Brownfield：本計畫即 SCG-0/1 載體；§2.1-2.3 問題/落地/介面 = SCG-2/3；落地過 SCG-4；§3.2 矩陣 = SCG-5 RTM。行進中框架摩擦即記入 `AutoSDD_Defect_Log.md`。

- **W1-a** `scripts/pytest_passed_count.sh`（純函式 helper）→ 立即 subprocess 單測。
- **W1-b** `scripts/ci-gate.sh`（additive accumulator + 收斂行）→ bash 語法檢查。
- **W1-c** `scripts/tests/test_pytest_passed_count.py`（7 case）→ 跑 `scripts/tests/` 全綠（含既有 12）。
- **W1-d** 實跑雙軌 `bash scripts/ci-gate.sh` → exit 0 + 收斂行自證逐軌計數。
- **W1-e** 零退化矩陣全項（AutoClaude 3069 / lint-imports 8 / scripts/tests 18）。
- **收斂**：任一紅 → 停機修復。

---

## 6. 缺陷帳本本輪處置（對照 §0 繼承）

| 缺陷 | 本輪處置 |
|------|---------|
| DEF-06-001（P3, open routed→improving_07） | **本輪 W1 修**（收斂補印逐軌計數 + 純函式 helper + 7 case 測試）→ 完成後改 `fixed@improving_07` 附證據 |
| DEF-01-007（P3, open） | cc-switch 環境工具未裝，本輪不涉 A/B 驗收，續 `open`（watch） |
| DEF-01-009（P3, open watch） | 已自癒（受控非空行 < 250），本輪零擴充不碰，續 `watch` |
| 本輪新發現 | 行進中即記（發現即記、絕不累積） |

---

## 7. 🔴 人工確認凍結點

本文件為 SCG-0/1 規格載體。本輪需確認：
1. **範圍**：DEF-06-001（P3，上輪已 routed 至 improving_07）作為唯一收尾 W 項，**不為遞增而遞增**開其他項。
2. **修復設計**：採「雙軌收斂補印逐軌 `N passed` + 純函式 helper、**免 v0.05 Copy-on-Evolve**」（§2.2）。

凍結後依 §5 實作順序執行（**已完成並通過 §3.2 矩陣**），收尾走多專家 Zero-Trust 審查閉環。
