# AutoSDD_improving_12 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 12 輪）

> **版本**：12（第十二輪迭代）
> **日期**：2026-06-15
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ 結案（含 zero-trust 三鏡複審即修）。範圍＝**按需雙驅動，🔴 人工於四選項選定「兩項全做（DEF-11-002 + DEF-11-001 v0.0Y 子項）」**。兩項 improving_11 routed 遺留全數關閉：(1) **W-12-1**＝迭代範本補 DEF-11-002 檢核項（純 doc）；(2) **W-12-2**＝通用 `copy_on_evolve.sh` helper（**共享 infra、免 Copy-on-Evolve**——見 §1 Rule 7 設計決策，修正上輪「v0.0Y」粗略標記）。實作期 B 軌 dogfooding 另發現 **DEF-12-001**（scripts/tests 未被任何閘門 gating，使 W-12-2 測試非強制）→ **本輪即修**（完成 W-12-2 必要部分）；**DEF-12-002**（cross_version_guard 對 `::nodeid` 誤攔）即記 routed。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3075 passed / 122 skipped / 0 failed**（2026-06-15 本機實測，非引用文件；上輪 floor 3075，本輪 AutoClaude 零改動）；AISDLC_SDD 雙軌 ci-gate exit 0（v0.01:1478 / v0.05:1499）+ 新增共享 infra 軌 scripts/tests:24。
> **本輪定位**：承 improving_11（按需單一驅動關 DEF-10-002）。本輪驅動＝improving_11 收尾 routed 的兩項潔淨度紀律家族遺留（DEF-11-002 範本、DEF-11-001 v0.0Y helper）。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-15，非文件宣稱）

主 agent 派 Explore agent 親跑（非引用文件）：

| # | 事實 | 證據 | 對本輪影響 |
|---|------|------|-----------|
| F1 | AutoClaude 全套（**改動前**）= **3075 passed / 122 skipped / 0 failed**（96.22s） | `python -m pytest tests/ -q` | 硬閘 floor=3075，0 failed → **通過** |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports` | 架構紅線 8 條全保 |
| F3 | LOC violations=**0**（total 17511 / baseline 17032 / cap 20438） | `python tools/check_loc_budget.py` | 分級政策全過 |
| F4 | snapshot = **OK** | `python tools/snapshot_sync.py --check` | 文件新鮮 |
| F5 | AISDLC_SDD `ci-gate.sh`（改動前）= **exit 0**；v0.01:1478 / v0.05:1499 | `bash scripts/ci-gate.sh` | 雙軌健康 |
| A1 | DEF-01-007（cc-switch）`command -v cc-switch`=**NOT FOUND**（rc=1）仍重現 | 本機實測 | 環境工具缺裝、倉內零阻塞，維持 open（非本輪 scope） |
| A2 | DEF-01-009（`sdd_governance_plugin.py` raw 250）持平、已自癒（violations=0） | `awk END NR`=250 + F3 | 維持 open watch，零擴充不觸發 |
| A3 | 上輪構件存在：v0.05 FF-17 `check_ff17_evolution_version_gate_coverage` 存在、v0.05 為磁碟最高版 | grep + `ls -d … sort -V tail -1` | (d) 構件存在性 PASS |
| A4 | DEF-11-001 .gitignore 排除仍生效：v0.05 已入庫、build/reports+arch-fitness.json 命中 0 | `git add -A -n AISDLC_SDD/AISDLC_SDD_v0.05/` | 上輪修復無回歸 |
| **D1** | **本輪驅動＝DEF-11-002 + DEF-11-001 v0.0Y 子項**（🔴 人工選「兩項全做」） | Defect_Log + AskUserQuestion | 觸發 W-12-1 / W-12-2 |

**硬閘判定**：F1 基線 0 failed 且 3075 = 上輪 floor → **通過**，准進階段二。

---

## 1. `<Architecture_Design_Review>`（強制自我檢核）

> **本輪改動面**：純流程/共享 CI infra。**AutoClaude 微核心零改動**（零 python、零 port、零 plugin、零 checkpoint、零 DAL）；**AISDLC_SDD v0.01~v0.05 凍結本體零改動**。三處落點皆在 versioned 目錄外的共享 CI infra（`AISDLC_SDD/scripts/` + monorepo 根 `docs/`）。

| 檢核項 | 結論 |
|--------|------|
| 1.1 架構純潔性（God-object / Thin Facade） | **維持/N/A**。本輪零 AutoClaude python；`playbook_runner.py` Thin Facade 零碰。helper 為單一 bash 腳本（~55 行）+ ci-gate 增 ~10 行串流測試軌，無物件、無業務邏輯。 |
| 1.2 持久化相容（additive / DAL 三後端零停機） | **N/A**。零 alembic / 零 `PlaybookCheckpoint` 欄位 / 零 DAL 觸碰。 |
| 1.3 安全防護網（CONDITIONAL 鏈式攻擊） | **零弱化、零交集**。helper 不從文件生成指令、不執行外部輸入；`tar --exclude` 固定字面樣式，無動態鏈、無新注入面。ci-gate 新增軌僅 `pytest scripts/tests/`，無外部輸入。 |
| 1.4 對外 I/O 安全（`ToolInvocationPort` 外呼） | **N/A**。零新外呼端點、零網域、零 HTTP。 |

### Rule 7 誠實設計決策 — W-12-2 落點修正（helper = 共享 infra，免 Copy-on-Evolve，**非 v0.06**）

DEF-11-001 v0.0Y 子項在帳本 status 欄標記為「routed v0.0Y」，主 agent scope 選項標籤亦沿用「Copy-on-Evolve v0.05→v0.06」字樣——**此標記不精準**。理由：

1. **帳本 routing 原文的構件路徑即 `scripts/copy_on_evolve.sh`** ＝共享 infra 路徑（versioned 目錄外）。
2. **全部 Copy-on-Evolve 版本治理家族修復皆落共享 infra、免 Copy-on-Evolve**：`ci-gate.sh`（DEF-03-001）、`conftest.py`（DEF-02-001）、`pytest_passed_count.sh`（DEF-06-001）、`cross_version_guard.py`。helper 屬同家族，同精神。
3. **若為改 2 行 SOP 而整碗複製出 v0.06，反而會再次觸發 DEF-11-001 的潔淨度問題**（新版本目錄又夾帶 runtime 產物）——自相矛盾。Rule 2（Simplicity）/ Rule 3（Surgical）。
4. DEF-11-001 routing 用「**或**」（提供 helper **或** 補 SOP 步驟）——helper 為自動化解、優於人工 SOP 步驟，單獨即滿足分流。

∴ **W-12-2 落 `AISDLC_SDD/scripts/copy_on_evolve.sh`（免 Copy-on-Evolve），不新增 v0.06。** v0.05 凍結本體 `AISDLC_SDD_UPGRADE_SOP.md` §2.1/§5 的 `cp -r` + `git add .` 根因留待**下一次真實 v0.06 演化時**於可編輯副本同步引用 helper（記入 DEF-11-001 routing 餘項，非本輪）。

**結論：四項全數維持/N/A，無架構衝突、無凍結本體誤改、無安全弱化。**

---

## 2. 本輪增量設計 — W 項

### 2.1 W-12-1：DEF-11-002 — 迭代範本補「入庫前 dry-run 潔淨度」檢核項

**根因**：improving_11 收尾 zero-trust 初審把 Copy-on-Evolve commit 潔淨度查證**窄化到 `git check-ignore *.pyc`**，未跑全量 `git add -A -n` dry-run → 漏審 227 個 build/reports + arch-fitness.json runtime 產物 → 誤判 OVERALL PASS（複審以 dry-run 1013 檔當場揭露）。屬審查方法論缺口。

**介面 delta**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`「🔍 多專家 Zero-Trust 審查閉環」step 1 新增 note「Copy-on-Evolve / 大批新檔入庫潔淨度（DEF-11-002 紀律）」：審查涉及新凍結版本或大批 untracked 入庫時，**必跑 `git add -A -n <path>` 全量 dry-run** 審 would-add 無 runtime/stale 產物，**不可僅憑 .pyc 宣稱潔淨**。仿既有「並行派發隔離（流程問題 #11）」note 格式，與階段一 (f)、DEF-05-002/DEF-07-001 同列潔淨度/誠實性紀律家族。

**LOC/契約影響**：純 doc，零 python、零 `.importlinter`、零 checkpoint。

### 2.2 W-12-2：DEF-11-001 v0.0Y 子項 — 通用 `copy_on_evolve.sh` helper（共享 infra）

**根因**：框架無官方 copy helper／SOP 步驟排除 runtime 產物——SOP §2.1 `cp -r` 整碗複製 + §5 `git add .` 必夾帶 build/reports/arch-fitness.json（DEF-11-001 would-add 1013）。

**介面 delta**（落 `AISDLC_SDD/scripts/`，免 Copy-on-Evolve）：

| 構件 | 內容 |
|------|------|
| `scripts/copy_on_evolve.sh` | `copy_on_evolve.sh <from> <to>`。`tar --exclude` 串流複製（排除在複製前、產物從不落地）；排除 `__pycache__`/`*.pyc`/`*.pyo`（無斜線樣式比對 basename → 任意深度）+ `./build/reports`/`./arch-fitness.json`/`./chaos-report.json`（含斜線樣式比對完整成員名 → 僅頂層，對齊 .gitignore 語意）。防呆：參數≠2→exit 2；來源不存在→exit 1；目標已存在→exit 1（拒覆蓋）。**rsync 在 Windows Git Bash 不可用故採 GNU tar**（Git Bash/Linux/macOS 通用）。 |
| `scripts/tests/test_copy_on_evolve.py` | 5 case：helper 存在 / **排除 runtime ∧ 保留源碼（build/planning、build/logs、FF-17 源碼不被連坐排除）** / 拒絕覆蓋 / 來源不存在 / 參數數錯。路徑策略：fixture 建於與 REPO_ROOT 同碟暫存目錄、全程相對 posix 路徑（避 Git usr/bin bash 的 `/mnt/c` vs `/c` 掛載差異與反斜線被吃）。 |

**驗證**：scripts/tests 24 passed（19 既有 + 5 新）；真實 v0.05 實跑 build/reports+arch-fitness.json 排除、build/planning+FF-17 源碼保留、0 __pycache__；**突變測試**（移除 build/reports 排除）→ test_excludes 1 failed（非假測試）。

**LOC/契約/TLC**：helper 為框架 bash tool（非 AutoClaude LOC tier）；零 `.importlinter` 影響；零 `_HAPPY_PATH`/`*.tla`（TLC N/A）。

### 2.3 DEF-12-001（本輪實作期 B 軌 dogfooding 新發現）— ci-gate 納入 scripts/tests gating（本輪即修）

**現象**：`ci.yml` 僅呼叫 `ci-gate.sh`，`ci-gate.sh` 只跑各版 `tools/fsm_runtime/tests/`——`scripts/tests/`（共享 infra 回歸鎖：版本解析 / pytest 計數 / 跨版 guard / 本輪 copy_on_evolve helper）**未被任何閘門執行** → 其「退化即紅」保護從未被實際強制。**直接影響 W-12-2**：若不修，test_copy_on_evolve.py 被任何 gate 都不跑＝Rule 9「不會被執行的測試＝無效」→ W-12-2 半交付。

**修復**：`ci-gate.sh` 版本迴圈後新增「共享 infra scripts/tests/」軌——版本無關跑一次 `pytest scripts/tests/`（`set -o pipefail`+`set -e` → 任一紅燈即中止，硬閘語意一致），並以 `GATE_SUMMARY` 自證 `scripts/tests:24`。FF-17 四錨點未動（複驗 structural-pass）；test_ci_gate_version_resolution 用 SDD_GATE_DRY_RUN 早退（無遞迴）。**判為完成 W-12-2 之必要部分，非新增 scope。**

### 2.4 DEF-12-002（本輪新發現）— cross_version_guard 對 `::nodeid` 誤攔（即記 routed）

**現象**：`scripts/cross_version_guard.py` `_is_path_arg` 用 `os.path.exists(token)` 判路徑；`pytest scripts/tests/x.py::test_y`（從 REPO_ROOT 跑單一測試）的 `檔案::nodeid` token `os.path.exists`=False → 誤判無路徑 arg → 走 bare 分支展開全版本 → 誤報「跨版偵測 v0.01..v0.05」。屬 hook 誤攔（非阻擋，workaround：用目錄路徑或 `-k`；ci-gate 用目錄路徑不受影響）。**route 下一輪/v0.0Y**（小修：`_is_path_arg` 剝除 `::` 後綴再判存在）。

---

## 3. 階段四 — CI 平價與驗證（零退化矩陣全項，floor 以本輪實測為準）

| 檢查 | 命令 | 通過條件 | 本輪實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 上輪 3075 / 0 failed | ✅ **3075 passed / 122 skipped / 0 failed**（101.72s，改動後複測；AutoClaude 零改動持平） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | ✅ **violations=0**（total 17511 持平） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2 | ✅ **exit 0**「v0.01:1478 v0.05:1499 **scripts/tests:24**」（DEF-12-001 新軌自證） |
| arch_fitness FF-17 | `arch_fitness --only FF-17`（v0.05） | structural pass | ✅ **exit 0 / fail=0**（改後 ci-gate.sh 四錨點仍在） |
| 共享 infra 測試 | `pytest scripts/tests/` | 全綠 | ✅ **24 passed**（19 既有 + 5 新 copy_on_evolve；含突變即紅證據） |
| 五軌 TLC | （僅 FSM 變更時） | 五軌 0 violation | **N/A**（本輪零 FSM／`*.tla`／`_HAPPY_PATH`） |

DAL 等價：本輪零持久化／DAL 觸碰，三後端等價性不受影響。

---

## 4. 缺陷帳本本輪處置

| ID | 嚴重度 | 上輪狀態 | 本輪處置 |
|----|--------|---------|---------|
| DEF-11-002 | P3 | open | **fixed@範本v4**（W-12-1）：審查閉環 step 1 補「`git add -A -n` 全量 dry-run」檢核項。grep 證實落地（範本 :164-170） |
| DEF-11-001（v0.0Y 子項） | P3 | routed v0.0Y | **fixed@improving_12**（W-12-2）：`scripts/copy_on_evolve.sh` helper（共享 infra，免 Copy-on-Evolve）+ 5 測試。SOP §2.1 引用 helper 之餘項留待真實 v0.06 演化（routing 餘項，非本輪） |
| DEF-12-001 | P3 | （本輪新發現） | **fixed@improving_12**：ci-gate.sh 納入 scripts/tests gating（完成 W-12-2 測試強制性）|
| DEF-12-002 | P3 | （本輪新發現） | **open / routed 下輪 v0.0Y**：cross_version_guard `::nodeid` 誤攔，小修剝除 `::` 後綴 |
| DEF-01-007 | P3 | open | **維持 open**：環境/API 動作，非本輪 scope；倉內零阻塞 |
| DEF-01-009 | P3 | open watch | **維持 open watch**：raw 250 持平、violations=0 自癒、零擴充不觸發 |
| 其餘 fixed | — | fixed | 無回歸（F1~F5/A3/A4 全綠佐證） |

**本輪新發現缺陷**：DEF-12-001（fixed@improving_12）、DEF-12-002（open/routed）。**無虛報、無漏記**。

---

## 5. 實作順序（每支完成立即測試，絕不累積）

1. **W-12-1 範本補檢核項** → grep 確認 (164-170) 落地。
2. **W-12-2 copy_on_evolve.sh + 5 測試** → `pytest scripts/tests/test_copy_on_evolve.py` 5 passed → 真實 v0.05 實跑驗排除/保留 → 突變（移除 build/reports 排除）證 test_excludes 轉紅 → 還原。
3. **DEF-12-001 ci-gate 補 scripts/tests 軌** → `bash scripts/ci-gate.sh` exit 0 + 收斂自證 `scripts/tests:24` → FF-17 複驗 structural-pass。
4. **全量潔淨度** → `git add -A -n` would-add 僅 4 源碼檔、0 runtime/stale（本輪親實踐 DEF-11-002 紀律）。
5. **AutoClaude 零退化複測** → 3075 passed / 0 failed 持平。

---

## 6. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 | 狀態 |
|------|------|------|------|------|
| R-12-1 階段一零信任重偵察 + 硬閘 | §0 | Explore agent 親跑五項 + 構件複驗 + open 缺陷重現 | F1=3075/0 failed 硬閘 PASS | ✅ |
| R-12-2 DEF-11-002 範本補檢核項（W-12-1） | §2.1 | 範本審查閉環 step 1 新增 note | grep 證實 (164-170)、含 Audit_11 實例 | ✅ |
| R-12-3 DEF-11-001 v0.0Y helper（W-12-2） | §2.2 | `scripts/copy_on_evolve.sh` + 5 測試 | scripts/tests 24 passed、真實實跑、突變即紅 | ✅ |
| R-12-4 W-12-2 落點 Rule 7 修正（共享 infra 非 v0.06） | §1 設計決策 | helper 落 scripts/、零新版本目錄、v0.01~05 凍結未動 | `ls -d AISDLC_SDD_v0.0*` 仍 5 版、would-add 0 runtime | ✅ |
| R-12-5 DEF-12-001 scripts/tests gating（即修） | §2.3 | ci-gate.sh 補共享 infra 軌 | ci-gate exit 0 + `scripts/tests:24`、FF-17 structural-pass | ✅ |
| R-12-6 DEF-12-002 即記 routed | §2.4 | Defect_Log 記載 + 分流 | 帳本列在、open/routed | ✅ |
| R-12-7 零退化矩陣全項綠 | §3 | 八項命令親跑 | §3 實測欄全 ✅（floor 3075、雙軌 1478/1499+scripts/tests:24） | ✅ |

---

## 7. 🔴 人工確認凍結點

- **方向確認**：2026-06-15 🔴 人工於四選項（做 DEF-11-002 / 做 DEF-11-001 v0.0Y / 兩項全做 / 輕量盤點）選定 **「兩項全做（DEF-11-002 + DEF-11-001 v0.0Y）」**。
- **設計偏離聲明（Rule 7）**：W-12-2 helper 落**共享 infra（`AISDLC_SDD/scripts/`）免 Copy-on-Evolve**，**不新增 v0.06**——修正上輪帳本「routed v0.0Y」與 scope 選項「v0.05→v0.06」之粗略標記，理由見 §1（家族前例一致、避免為改 2 行 SOP 整碗複製反觸 DEF-11-001、routing「或」字單 helper 即足）。SOP §2.1 引用 helper 之餘項留待真實 v0.06 演化。
- **scope 擴充聲明**：實作期 dogfooding 發現 DEF-12-001（scripts/tests 未被 gating）→ 因其決定 W-12-2 測試是否強制（Rule 9），判為**完成 W-12-2 必要部分即修**，非新增 scope；DEF-12-002（guard `::nodeid` 誤攔）即記 **routed 不修**以守 scope 邊界。
- **結案宣告**：improving_12 為按需雙驅動輪。W-12-1/W-12-2 全落地、DEF-11-002 + DEF-11-001 v0.0Y 子項 fixed、DEF-12-001 即修。零退化（AutoClaude floor 3075、AISDLC_SDD 雙軌 v0.01:1478/v0.05:1499 + scripts/tests:24、FF-17 structural-pass、TLC N/A）、鏈維持閉合。
- **下一份**：improving_13（按需）——DEF-01-007 殘留待環境就緒跑 live A/B；DEF-12-002 guard `::nodeid` 小修；DEF-11-001 SOP §2.1 引用 helper（隨真實 v0.06）；或出現新整合驅動時觸發。
