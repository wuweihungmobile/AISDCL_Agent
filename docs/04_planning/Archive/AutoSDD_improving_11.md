# AutoSDD_improving_11 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 11 輪）

> **版本**：11（第十一輪迭代）
> **日期**：2026-06-15
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ 結案（含收尾複審即修）。範圍＝**按需單一驅動 DEF-10-002**——🔴 人工於三選項（(a)+(b) 全做 / 只做(a)延後(b) / 輕量盤點）選定「**(a)+(b) 全做，完整關閉 DEF-10-002**」。兩項流程/方法論改善皆落地：(a) 迭代範本階段一補檢核項、(b) Copy-on-Evolve v0.05 新增 arch_fitness **FF-17** 固化「演化版必納官方閘門」。**收尾 zero-trust 複審**揭露 Copy-on-Evolve 潔淨度缺口（v0.05 build/reports + arch-fitness.json runtime 產物將隨 commit 入庫、初審潔淨度查證僅憑 .pyc 不完整），🔴 人工定奪「本輪即清理排除」→ 已以 `AISDLC_SDD/.gitignore` 排除（would-add 1013→839），DEF-11-001 即清理子項 fixed、文件誠實改寫（見 §7 + Audit_11 §6）。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3075 passed / 122 skipped / 0 failed**（2026-06-15 本機實測，非引用文件；上輪 floor 3075，本輪 AutoClaude 零改動）；AISDLC_SDD 雙軌 ci-gate exit 0（v0.01:1478 / **v0.05:1499**）。
> **本輪定位**：承 improving_10（按需單一驅動關 DEF-01-007 倉內阻塞）。DEF-10-002 為 improving_10 收尾獨立審查提出、明確 routed 到 improving_11 的兩項治理通則化建議，是本輪唯一真實驅動。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-15，非文件宣稱）

本計畫所有判斷皆錨定下列**已實測事實**（主 agent 親跑，非引用文件）：

| # | 事實 | 證據位置 | 對本輪的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套（**改動前**）= **3075 passed / 122 skipped / 0 failed**（108.38s） | 本機 `python -m pytest tests/ -q`（背景作業 b2yzil67x 尾行） | 硬閘 floor=3075，0 failed → **通過** |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports` | 架構紅線 8 條全保 |
| F3 | AISDLC_SDD `ci-gate.sh`（改動前）雙軌 = **exit 0**；v0.01:1478 / v0.04:1494 | `bash scripts/ci-gate.sh`（`/tmp/cigate_11.log` 收斂行自證逐軌計數） | 雙軌健康；DEF-06-001 修復無回歸 |
| F4 | LOC budget violations=**0**（total=17511 / baseline=17032 / cap=20438） | `python tools/check_loc_budget.py` | 分級政策全過 |
| F5 | snapshot = **OK** | `python tools/snapshot_sync.py --check` | 文件新鮮 |
| A1 | DEF-01-007（cc-switch）`command -v cc-switch`=**NOT FOUND** 仍重現 | 本機實測 | 環境工具缺裝、倉內已零阻塞，維持 open（非本輪 scope） |
| A2 | DEF-01-009（`sdd_governance_plugin.py` raw 250）持平、已自癒 | `awk END NR`=250 + F4 violations=0 | 維持 open watch，本輪零擴充不觸發 |
| A3 | 上輪修復構件全部存在 | `scripts/sdd_bridge_smoke.yaml` 存在、`tools/integration_gate.ps1` [5/5] 已硬化（多 CLI 偵測 + `Test-Path` 驗載具，`grep` 證實） | (d) 構件存在性 PASS |
| **D1** | **DEF-10-002 為本輪唯一真實驅動** | Defect_Log DEF-10-002 status=open，分流去向明載「下一輪 improving_11（按需）：(a)+(b)」 | 觸發本輪 W 項（§2） |

**硬閘判定**：F1 基線 0 failed 且 3075 = 上輪 floor → **通過**，准進階段二。

---

## 1. `<Architecture_Design_Review>`（強制自我檢核）

> **本輪改動面**：(i) **W-11-1**＝monorepo 根 `docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 階段一補一條檢核項（純 doc）；(ii) **W-11-2**＝B 軌框架本體演化 Copy-on-Evolve `v0.04→v0.05`，於 v0.05 `tools/arch_fitness/arch_fitness.py` 新增 **FF-17**（~50 行純函式）+ 5 單元測試 + EVOLUTION_LOG/CHANGELOG。**AutoClaude 微核心零改動**；AISDLC_SDD v0.01~v0.04 凍結本體零改動（修改全落 v0.05）。

| 檢核項 | 結論 |
|--------|------|
| 1.1 架構純潔性（God-object / Thin Facade） | **維持**。FF-17 是 arch_fitness 既有「引用完整性家族」（FF-6/7/14/15）同源延伸，單一純函式 + 註冊進 `ALL_CHECKS`，不創 God-object。AutoClaude `playbook_runner.py` Thin Facade 零碰。 |
| 1.2 持久化相容（additive / DAL 三後端零停機） | **N/A 且維持**。零 alembic / 零 `PlaybookCheckpoint` 欄位 / 零 DAL 觸碰。FF-17 與所有 FF 同為 read-only 無副作用。 |
| 1.3 安全防護網（CONDITIONAL 鏈式攻擊） | **零弱化、零交集**。FF-17 不引入 subprocess、不執行 shell（純文字 regex 分析，鏡像 FF-14 對 CI YAML 靜態作法），無「從文件生成指令」動態鏈、無新注入面。 |
| 1.4 對外 I/O 安全（`ToolInvocationPort` 外呼） | **N/A**。零新外呼端點、零網域、零 HTTP。FF-17 僅讀本機 repo 內檔案。 |

**設計決策（Rule 7 誠實聲明）**：DEF-10-002(b) 原文提及 `governance/R-*.yaml`，惟查 FF-8 機制：新增 `maturity=active` 的 R-9.x 會連鎖強制 test_ref（FF-8）+ trigger_states 可達性（FF-10）+ severity 一致性（FF-12），且 R-9.x 絕對禁令係**自演化 meta-loop 停機安全**之異類關注點。故採**最小正確實作＝新增 FF-17 fitness function**（arch_fitness 本即治理層的 fitness-function 套件、structural fail 即阻擋官方閘門），**不另開 R-9.x**——符合 Rule 2（Simplicity）/Rule 3（Surgical），避免無謂連鎖且不掏空 meta-loop 規則語意。

**結論：四項全數維持/N/A，無架構衝突、無凍結本體誤改、無安全弱化。**

---

## 2. 本輪增量設計 — W 項（DEF-10-002 雙子項，🔴 人工選「全做」）

### 2.1 為何本輪有 W 項

DEF-10-002 是 improving_10 收尾獨立 zero-trust 審查（OVERALL PASS 後）提出、**明確 routed 到 improving_11** 的兩項治理通則化建議，非「為遞增而遞增」。🔴 人工於 scope 三選項中選定「(a)+(b) 全做」。

### 2.2 W-11-1：DEF-10-002(a) — 迭代範本階段一補「外部工具 invocation 形態」檢核項

**根因**：improving_01 §5.2 規劃 cc-switch A/B 時假設其為 PATH CLI，直到 improving_10 才發現主流版（farion1231）為 Tauri GUI 不上 PATH，致 DEF-01-007 拖延 9 輪。範本階段一無「外部工具 invocation 形態偵察」檢核。

**介面 delta**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 階段一原 (a)~(e) 後新增 **(f)**：「本輪若涉外部工具依賴（A/B 後端切換、外部 CLI／服務、訊息平台），須先確認其 invocation 形態（GUI app／PATH CLI／API），勿假設可 headless 自動化（DEF-10-002a 紀律，含 cc-switch 致 DEF-01-007 跨 9 輪實例）」。為 DEF-05-002/DEF-07-001「實作後回掃」系列**首個落入範本之常設階段一檢核**。

**LOC/契約影響**：純 doc，零 python、零 `.importlinter` 影響、零 checkpoint 欄位。

### 2.3 W-11-2：DEF-10-002(b) — Copy-on-Evolve v0.05 新增 FF-17 固化「演化版必納官方閘門」

**根因**：DEF-03-001 曾發現 ci-gate.sh FW_DIR 寫死 v0.01 → 演化版從不進官方閘門；improving_04 以雙軌（凍結基線 + 自動偵測最新版）**點修**。但「演化版必納官方閘門」未上升為**結構不變量**，僅靠單輪缺陷修復，若有人退回寫死無守門。

**介面 delta**（落 v0.05，Copy-on-Evolve 自 v0.04）：

| 構件 | 內容 |
|------|------|
| `tools/arch_fitness/arch_fitness.py` 常數 | `CI_GATE_PATH = PROJECT_ROOT / "scripts" / "ci-gate.sh"`（PROJECT_ROOT=`parents[3]`=`AISDLC_SDD/`，scripts/ 為 versioned 目錄外共享 CI infra） |
| 純函式 `_latest_version_dir()` | 磁碟 `AISDLC_SDD_v0.0*` 語意版本最高者（無則 None） |
| `check_ff17_evolution_version_gate_coverage()` | 靜態讀 `ci-gate.sh`，斷言四錨點動態最新版偵測慣用語：`ls -d AISDLC_SDD_v0.0*` / `sort -V` / `tail -1` / `FW_VERSIONS+=(…LATEST…)`。任一缺＝退回靜態寫死＝DEF-03-001 回歸＝`structural fail`（fingerprint `ff17-static-pin`）。腳本不存在/無版本目錄＝INFO 略過（鏡像 FF-14 no-refs） |
| `ALL_CHECKS` 註冊 + docstring | 計數 16→17、exit-code structural fail 清單補 FF-17 |
| `test_arch_fitness.py` 5 case | 真 repo 涵蓋最新版（ff17-ok）/ 合成雙軌 PASS / 寫死單版 fail / 漏 append-latest fail（evidence 含 `FW_VERSIONS`）/ 腳本缺 INFO 略過 |
| `EVOLUTION_LOG.md` + `releases/CHANGELOG.md` | v0.04→v0.05 段（delta/TLC N/A/驗證/回退） |

**LOC 預算落點**：v0.05 為**新凍結版本**，arch_fitness.py 屬框架 tool（非 AutoClaude LOC tier 治理範圍）；AutoClaude `check_loc_budget` 零觸（total 17511 持平）。

**對 `.importlinter` 各 contract 的影響**：**零**。AutoClaude 無 python import 變動，8 條 contract 持平（8 kept / 0 broken）。

**checkpoint additive 欄位需求**：**無**。

**TLC**：**N/A**——FF-17 為靜態 CI 腳本守門，`_HAPPY_PATH` 與 `*.tla` 零改動（Rule 9.18.1 不啟動）。

---

## 3. 階段四 — CI 平價與驗證（零退化矩陣全項，floor 以本輪實測為準）

| 檢查 | 命令 | 通過條件 | 本輪實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 上輪 3075 / 0 failed（新測試只增不減） | ✅ **3075 passed / 122 skipped / 0 failed**（AutoClaude 零改動，改動後複測持平） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | ✅ **violations=0**（total 17511 持平） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2 | ✅ **exit 0**（v0.01:1478 / **v0.05:1499**，FF-17 ff17-ok 自證） |
| arch_fitness FF-17 | `python -m tools.arch_fitness.arch_fitness --only FF-17`（v0.05） | structural pass | ✅ **exit 0**「官方閘門動態涵蓋最新演化版（v0.05）」 |
| v0.05 arch_fitness 測試 | `pytest test_arch_fitness.py` | 全綠 | ✅ **87 passed**（82 既有 + 5 FF-17） |
| 五軌 TLC | （僅 FSM 變更時） | 五軌 0 violation | **N/A**（本輪零 FSM／`*.tla`／`_HAPPY_PATH` 變更） |

DAL 等價：本輪零持久化／DAL 觸碰，三後端等價性不受影響。

---

## 4. 缺陷帳本本輪處置（對照 §0 繼承）

| ID | 嚴重度 | 上輪狀態 | 本輪處置 |
|----|--------|---------|---------|
| DEF-10-002 | P3 | open | **fixed@improving_11**：(a) fixed@範本v3（階段一補 (f)）+ (b) fixed@v0.05（FF-17 + 5 測試）。證據見 §2 + Defect_Log + EVOLUTION_LOG v0.04→v0.05 |
| DEF-11-001 | P3 | （本輪新發現，缺口由收尾 zero-trust 複審揭露） | **fixed@improving_11（即清理子項）/ routed v0.0Y（通用 helper+SOP 子項）**：複審發現 v0.05 `build/reports/`（173 runtime 取證檔）+ 根 `arch-fitness.json` 未被任何 .gitignore 涵蓋、將隨 commit 入庫。本輪即清理＝於 `AISDLC_SDD/.gitignore` 新增 v0.05 區塊排除 `build/reports/`+`arch-fitness.json`+`chaos-report.json`，`git add -A -n` would-add **1013→839**（排除 174），真源碼（build/planning 52／FF-17 bridge／73 tests／EVOLUTION_LOG／CHANGELOG）保留；ci-gate exit 0、雙軌 1478/1499 不變複驗。通用 `copy_on_evolve.sh` helper／SOP 系統性子項 routed v0.0Y |
| DEF-01-007 | P3 | open | **維持 open**：環境/API 動作（裝 cc-switch CLI 變體 + 配 profile + 授權 token），非本輪 scope；倉內零阻塞 |
| DEF-01-009 | P3 | open watch | **維持 open watch**：raw 250 持平、violations=0 自癒、本輪零擴充不觸發 |
| 其餘 fixed | — | fixed | 無回歸（F1~F5/A3 全綠佐證；DEF-06-001 ci-gate 收斂段逐軌計數正常顯示） |

**本輪新發現缺陷**：DEF-11-001（fixed@improving_11 即清理子項 / routed v0.0Y 系統性子項，誠實即記即修）。**無虛報、無漏記**。

---

## 5. 實作順序（每支完成立即編譯+測試，絕不累積）

1. **W-11-1 範本補 (f)** → 立即驗：grep 確認檢核項落地、語意完整。
2. **Copy-on-Evolve v0.04→v0.05** → 立即驗：`ls -d AISDLC_SDD_v0.0*` 含 v0.05、清 `__pycache__`、`SDD_GATE_DRY_RUN=1` 自證 ci-gate 偵測到 `v0.01 v0.05`。
3. **v0.05 加 FF-17（常數+函式+註冊+docstring）** → 立即驗：`arch_fitness --only FF-17` exit 0、ff17-ok 偵測最新版 v0.05。
4. **加 5 單元測試** → 立即驗：`pytest -k ff17` 5 passed；`test_arch_fitness.py` 87 passed；全套 not-chaos 1499 passed。
5. **EVOLUTION_LOG + CHANGELOG v0.05 段** → 立即驗：雙軌 ci-gate exit 0「v0.01:1478 v0.05:1499」。
6. **AutoClaude 零退化複測** → 3075 passed / 0 failed 持平。

---

## 6. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 | 狀態 |
|------|------|------|------|------|
| R-11-1 階段一零信任重偵察 + 硬閘 | §0 事實表 F1~F5/A1~A3/D1 | 主 agent 親跑五項實測 + 構件複驗 + open 缺陷重現 | F1=3075/0 failed 硬閘 PASS | ✅ PASS |
| R-11-2 DEF-10-002(a) 範本補檢核項（W-11-1） | §2.2 | 範本階段一新增 (f) | grep 證實 (f) 落地、含 DEF-01-007 實例 | ✅ PASS |
| R-11-3 DEF-10-002(b) FF-17 固化（W-11-2） | §2.3 | v0.05 arch_fitness 新增 FF-17 + 註冊 + docstring | `--only FF-17` exit 0、ff17-ok、雙軌 ci-gate 自證 | ✅ PASS |
| R-11-4 FF-17 攻防/回歸測試 | §2.3 測試列 | 5 case（含寫死單版 fail / 漏 append fail 退化即紅） | `pytest -k ff17` 5 passed、突變即紅 | ✅ PASS |
| R-11-5 Copy-on-Evolve 紀律（凍結 + EVOLUTION_LOG + CHANGELOG） | §2.3 | v0.01~04 凍結、v0.05 演化、雙日誌補段 | v0.04 未改、v0.05 日誌齊備 | ✅ PASS |
| R-11-6 零退化矩陣全項綠 | §3 矩陣 | 八項命令親跑 | §3 實測欄全 ✅（AutoClaude floor 3075、v0.05:1499） | ✅ PASS |
| R-11-7 DEF-11-001 即記即修分流 | §4 處置 | Defect_Log DEF-11-001（fixed@improving_11 即清理 .gitignore 排除 / routed v0.0Y 通用 helper） | 帳本列在、證據附 would-add 1013→839 + ci-gate 複驗 | ✅ PASS |

---

## 7. 🔴 人工確認凍結點

- **方向確認**：2026-06-15 🔴 人工於三選項（(a)+(b) 全做 / 只做(a)延後(b) / 輕量盤點）選定 **「(a)+(b) 全做，完整關閉 DEF-10-002」**。
- **設計偏離聲明**：DEF-10-002(b) 原文提及 governance/R-*.yaml，本輪採 arch_fitness FF-17（治理層 fitness-function 套件）而**不另開 R-9.x**，理由見 §1 設計決策（避免 FF-8/10/12 連鎖、不混入自演化 meta-loop 異類關注點）。
- **結案宣告**：improving_11 為按需單一驅動輪（DEF-10-002）。(a)(b) 雙子項全落地，DEF-10-002 fixed。**收尾 zero-trust 複審揭露 Copy-on-Evolve 潔淨度缺口**（v0.05 `build/reports/` 173 runtime 取證檔 + `arch-fitness.json` 將隨 commit 入庫、且鏡三 QA 初審潔淨度查證僅憑 .pyc 不完整）→ 🔴 人工定奪「本輪即清理排除」→ 已於 `AISDLC_SDD/.gitignore` 新增 v0.05 區塊排除（would-add 1013→839），DEF-11-001 即清理子項 fixed@improving_11、通用 helper 子項 routed v0.0Y；文件（本檔／Defect_Log／Audit_11 §6）已誠實改寫。零退化（AutoClaude floor 3075、AISDLC_SDD 雙軌 v0.01:1478/v0.05:1499 排除後不變）、鏈維持閉合。
- **下一份**：improving_12（按需）——DEF-01-007 殘留待使用者環境就緒後跑 live A/B 正式關閉；DEF-11-001 通用 `copy_on_evolve.sh` helper/SOP 子項擇機；或出現新整合驅動時觸發。
