# AutoSDD_improving_05 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 5 輪）

> **版本**：05（第五輪迭代）
> **日期**：2026-06-14
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ **已凍結**（2026-06-14 🔴 人工確認：使用者經 AskUserQuestion 明示「凍結，依計畫實作」——範圍 DEF-02-001 + 設計「共享 infra fail-loud guard、免 v0.05、T2 列文件化殘留」）。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3069 passed / 122 skipped / 0 failed**（2026-06-14 本機實測 99.58s，**非引用文件數字**）；AISDLC_SDD 雙軌閘門必須全綠。
> **本輪選定範圍**（使用者凍結）：**W1** = DEF-02-001（P3）Copy-on-Evolve 跨版測試 sys.modules 碰撞根因修復。**單一 W 項**（Rule 2 Simplicity First）。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-14，非文件宣稱）

本計畫所有設計皆錨定下列**已實測事實**（出處：2026-06-14 Explore agent 親跑 + 主 agent 沙箱複驗）：

| # | 事實 | 證據位置 | 對設計的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套 = **3069 passed / 122 skipped / 0 failed**（99.58s） | 本機 `python -m pytest tests/ -q` | 本輪零退化 floor = 3069（禁寫死） |
| F2 | `lint-imports` = **8 kept / 0 broken** | `PYTHONUTF8=1 lint-imports` | 架構紅線，以實際 8 條為準 |
| F3 | `check_loc_budget` violations=0（total 17511 ≤ cap 20438）；`snapshot_sync --check` 新鮮 | 本機實測 | 既有紅線無欠帳 |
| F4 | AISDLC_SDD `ci-gate.sh` 雙軌 = **exit 0**（v0.01: 1478 passed / v0.04: 1494 passed，各 not-chaos 全綠 + arch_fitness exit 1 advisory 不阻擋） | `bash scripts/ci-gate.sh`（AISDLC_SDD 根） | DEF-03-001 修復屬實，雙軌健康 |
| F5 | DEF-03-001 構件齊備：`ci-gate.sh` `FROZEN_BASELINE`(27) + `LATEST=ls\|sort -V\|tail -1`(29) + `test_ci_gate_version_resolution.py`(4 case) | 開檔複驗 | 上輪交付屬實 |
| **R1** | **DEF-02-001 碰撞重現**：`cd AISDLC_SDD && pytest vX/.../tests vY/.../tests`（單一 process 跨版）→ `_pytest.pathlib.ImportPathMismatchError: ('tools.fsm_runtime.tests.conftest', '...v0.03...', '...v0.04...')` | 主 agent 2026-06-14 親跑（情境1b） | 根因錨定點 |
| **R2** | **根因 = `__init__.py` 鏈使各版 dotted name 完全相同**：tests/ 有 `__init__.py`，鏈 `tools/`→`tools/fsm_runtime/`→`tools/fsm_runtime/tests/` 皆有 `__init__.py`，version-root 無 → 各版 conftest 的 fully-qualified name 皆 `tools.fsm_runtime.tests.conftest`，prepend 模式下 sys.modules 同名衝突 | 沙箱情境1/1b | 任何 import-mode 微調不可解（見 R3/R4） |
| **R3** | **`import_mode=importlib` 不解**（dotted name 仍同名碰撞）；`consider_namespace_packages=true` 反打斷生產 import（`ModuleNotFoundError: tools.fsm_runtime`） | 沙箱情境 B/C | 排除 importlib 路線 |
| **R4** | **更深真相（決定性）**：即便讓最新版改 iso（移除 `__init__.py`+importlib），跨版同跑仍壞——**生產套件 `tools.fsm_runtime.*` 各版同名**，單一 process 的 sys.modules 只能裝一版 → A 版測試實際 import 到 B 版模組（沙箱情境3 `assert 'vA'=='vB'` 失敗）。**結論：Copy-on-Evolve 下「單一 process 跨版同跑」結構性不可支援；唯一正確隔離＝每版獨立 process（官方 gate 的 `cd vX` 已正確做到）** | 沙箱情境3 | 修法方向定調：不是「讓跨版能跑」，而是 fail-loud + 鎖定隔離不變量 |
| **R5** | guard 機制沙箱實證：`AISDLC_SDD/conftest.py` 的 `pytest_load_initial_conftests` 可攔截「從 repo 根 bare `pytest`」（最常見 footgun，T4 fire 成功）且**不干擾** `cd vX` 單版 gate（T1/T3 pass）；但「顯式 `pytest vX/... vY/...` 雙路徑」因 version 各自 `pytest.ini` 捕獲 rootdir/confcutdir，根 conftest 在 confcutdir 之上**不被載入**（T2 漏，hook 未被呼叫）→ 列文件化殘留 | 沙箱 sdguard2/4 | §2.5 覆蓋矩陣 |
| A1 | AISDLC_SDD 根層**無** conftest.py/pytest.ini（乾淨可放 guard）；`scripts/tests/` 用 `python -m pytest scripts/tests/...`（args 有路徑無版本 → guard 不誤觸） | `ls` + ci-gate.sh 開檔 | guard 落點安全 |
| A2 | DEF-01-007（cc-switch 未裝）仍重現；DEF-01-009（`sdd_governance_plugin.py` 224 非空行 < 250）已自癒→降 watch；DEF-02-001 仍重現（本輪修） | Explore agent 複驗 | §6 缺陷處置 |

**硬閘判定**：F1 基線 0 failed 且 3069 = 上輪 floor → **通過，准進階段二**。本輪零退化 floor 錨定 = **3069**。

---

## 1. `<Architecture_Design_Review>`（寫任何實質程式前強制自我檢核）

> 本輪 W1 主體為 **AISDLC_SDD 共享 CI infra**：`AISDLC_SDD/conftest.py`（跨版 fail-loud guard）+ `scripts/cross_version_guard.py`（可單測的純偵測 helper）+ `scripts/tests/test_cross_version_guard.py`（回歸測試）。AutoClaude 微核心 `core/`/`plugins/`/`adapters/` **零改動**；AISDLC_SDD 凍結本體（v0.0X 的 agent/governance/workflow/tools/.claude）**零改動**；**不做 v0.05 Copy-on-Evolve**（理由見 §2.3）。

### 1.1 架構純潔性 — 是否創造 God-object？Thin Facade 是否維持？

**否，且維持。** guard 為單一職責純函式（偵測 args/cwd 觸及的版本集合 → >1 即 raise `pytest.UsageError`），無狀態、無業務邏輯、不碰 AutoClaude kernel/plugin/port/adapter。`conftest.py` 僅薄包裝呼叫 helper。不新增 class/God-object。

### 1.2 持久化相容 — 新狀態是否 additive？DAL 三後端零停機是否維持？

**N/A 且維持。** W1 純屬測試 infra，**零持久化觸碰**（無 alembic、無 PlaybookCheckpoint、無 DAL）。guard 為純讀（檢查路徑字串 + `os.listdir` 列舉版本目錄），無副作用、無落檔。

### 1.3 安全防護網 — CONDITIONAL 白名單能否攔截鏈式攻擊向量？

**N/A 且零弱化。** W1 不新增任何「從文件生成指令」路徑。版本偵測來自固定前綴正則 `AISDLC_SDD_v0\.0\d+` 比對磁碟目錄名（非外部輸入、不執行任何衍生指令）。CONDITIONAL 三層防禦（白名單 regex + 黑名單字元 + shell=False/shlex）與本輪無交集，一行不改。

### 1.4 對外 I/O 安全 — 本輪是否新增 `ToolInvocationPort` 外呼路徑？

**否。** W1 為純本機 pytest hook，零外呼端點、零新網域、零 `ToolInvocationPort` 觸碰。SSRF/allowlist 攻擊面零變化。

**結論：四項檢核全數自洽，W1 為共享 CI infra 之測試隔離 fail-loud guard，無架構衝突、無凍結本體改動，准予進入設計細節。**

---

## 2. W1 設計 — DEF-02-001 跨版測試 sys.modules 碰撞根因修復（B 軌共享 infra）

### 2.1 問題（R1/R2）

Copy-on-Evolve 使 `AISDLC_SDD_v0.01`～`v0.04` 各保留一份結構完全相同的測試樹（`tools/fsm_runtime/tests/`，含 `conftest.py` 與 `__init__.py`）。因 `__init__.py` 鏈完整，各版測試/conftest 的 fully-qualified module name **完全相同**（`tools.fsm_runtime.tests.conftest`、`tools.fsm_runtime.tests.test_*`）。在**單一 pytest process 同時 collect 多版**時，sys.modules 同名衝突 → `ImportPathMismatchError`，且 traceback 顯示「另一版」路徑（DEF-02-001 原始「traceback 誤導」症狀）。

### 2.2 根因定論（R3/R4）—「跨版同跑」結構性不可支援

沙箱實證**排除**所有 test-infra 微調路線：

- `import_mode=importlib`：dotted name 仍同名 → 不解（R3）。
- `consider_namespace_packages=true`：打斷生產 import（R3）。
- 讓最新版改 iso（移除 `__init__.py`）：conftest 碰撞雖解，但**生產套件 `tools.fsm_runtime.*` 各版同名**，單一 process sys.modules 只能裝一版 → A 版測試實際載到 B 版生產模組（R4 沙箱情境3 失敗）。

**∴ 唯一正確隔離 = 每版獨立 process。** 官方 gate（DEF-03-001 後）的雙軌 `cd vX && pytest` 本就是獨立 process，**無此問題**。DEF-02-001 的本質是「**誤用**（單一 process 跨版）時錯誤訊息 cryptic、誤導」，而非 gate 缺陷。

### 2.3 落地決策：共享 infra fail-loud guard（免 v0.05 Copy-on-Evolve）

依 R4 的根因定論，正確且 proportionate（P3）的修法是 **Rule 12 Fail-Loud + 鎖定隔離不變量**，而非徒勞地「讓跨版能跑」：

- **(a) Fail-loud guard**：在 `AISDLC_SDD/conftest.py`（repo 根、**versioned 目錄之外＝共享 CI infra，非凍結本體，免 Copy-on-Evolve**，與 DEF-03-001 修 `scripts/ci-gate.sh` 同精神）以 `pytest_configure` 偵測「本次 session 將觸及 >1 個 `AISDLC_SDD_v0.0X`」→ raise `pytest.UsageError`，把 cryptic `ImportPathMismatchError` 轉為可行動訊息：指出觸及版本、根因（共用套件名）、與正確用法（`cd <version> && pytest` 或 `scripts/ci-gate.sh`）。
- **(b) 純偵測 helper**：偵測邏輯抽到 `scripts/cross_version_guard.py` 的純函式 `versions_touched(args, cwd) -> set[str]`，使其可被單元測試直接驗證（Rule 9 測意圖），conftest 僅薄包裝。
- **(c) 不做 v0.05**：本修復**零觸碰任一 v0.0X 凍結本體生產碼/測試**，故**不觸發 Copy-on-Evolve**（與 DEF-03-001 一致）。亦**零** `_HAPPY_PATH`/`*.tla` 改動 → **五軌 TLC 不啟動**（Rule 9.18.1 不觸發）。

> 為何不「再加 `__init__.py` 移除/改 import-mode」：那須改凍結本體（違 B 軌紅線），且 R4 證明仍不能讓跨版同跑安全。fail-loud 是面對「結構性不可支援」時的誠實正解。

### 2.4 介面 delta

**(a) `AISDLC_SDD/scripts/cross_version_guard.py`**（新增，共享 infra，純函式）
- `VERSION_RE = re.compile(r"AISDLC_SDD_v0\.0\d+")`
- `versions_touched(args: list[str], cwd: str) -> set[str]`：對每個非旗標 path arg，若路徑含版本片段→納入該版；若無任何 path arg（bare 呼叫）→ 展開 `cwd` 下所有 `AISDLC_SDD_v0.0X` 目錄。回傳觸及版本集合。
- `build_guard_message(versions: set[str]) -> str`：產出 fail-loud 訊息（含 DEF-02-001 與正確用法）。

**(b) `AISDLC_SDD/conftest.py`**（新增，共享 infra，薄包裝）
- `pytest_configure(config)`：以 `config.invocation_params.args/dir` 呼叫 `versions_touched`；若 `len > 1` → `raise pytest.UsageError(build_guard_message(...))`。
- **hook 選擇**（實作期實證，見 DEF-05-001）：原設計 `pytest_load_initial_conftests` 有 chicken-and-egg（rootdir conftest 在該 hook default 實作*之內*才載入，自身實作不被回呼，真 repo 不 fire）；改用 `pytest_configure`（configure 時 conftest 必已註冊，且版本目錄碰撞發生於其後 collection → configure 先 raise，攔在碰撞前）。

**(c) `AISDLC_SDD/scripts/tests/test_cross_version_guard.py`**（新增，回歸測試）
- 純函式單測（快、確定）+ 一支 subprocess 整合煙霧（驗 bare-from-root 實際 fire、單版不誤觸）。

### 2.5 覆蓋矩陣與殘留（R5；Rule 12 誠實標示）

| 情境 | 呼叫 | guard 行為 | 證據 |
|------|------|-----------|------|
| T1 | `cd vX && pytest`（官方 gate） | **不載入/不干擾** → 正常綠 | 沙箱 T1 pass |
| T3 | `cd AISDLC_SDD && pytest vX/.../tests`（單版顯式） | 不 fire → 正常綠 | 沙箱 T3 pass |
| **T4** | `cd AISDLC_SDD && pytest`（**bare，最常見 footgun**） | **fail-loud（UsageError + DEF-02-001 訊息，exit 4）** | 真 repo `pytest --co` 實測 fire、exit=4 |
| T2（殘留） | `cd AISDLC_SDD && pytest vX/... vY/...`（**顯式雙版本路徑**） | guard **不被載入**（version `pytest.ini` 捕獲 confcutdir）→ 仍 `ImportPathMismatchError`（但訊息已列出兩版路徑可診斷） | 沙箱 sdguard2/4 T2 |

> **T2 殘留之誠實聲明**：顯式同時傳入兩個版本路徑是專家刻意操作，conftest 機制無法在此情境攔截（pytest rootdir/confcutdir 被版本內 `pytest.ini` 下移，根 conftest 不載入）。原生 `ImportPathMismatchError` 已具名兩版路徑，可診斷。本輪不為此邊角破壞 confcutdir（加根 `pytest.ini` 經實測會連帶弄壞 T4，得不償失）。列為文件化已知限制。

### 2.6 LOC 預算 / `.importlinter` 影響

- `cross_version_guard.py` / `conftest.py`：AISDLC_SDD 共享 infra，**非** AutoClaude `check_loc_budget` 受控 Python tier（該工具僅計 AutoClaude）。仍自我約束於 helper ≤ ~60 行、conftest ≤ ~15 行。
- 新測試檔：tests/ 不計 LOC 預算。
- **AutoClaude 零改動** → `.importlinter` 8 條 contract **零影響**，預期維持 8 kept / 0 broken。

---

## 3. 階段四 — CI 平價與驗證

### 3.1 W1 驗證載體

```bash
cd AISDLC_SDD
python -m pytest scripts/tests/test_cross_version_guard.py -v   # guard 回歸測試
python -m pytest scripts/tests/ -v                              # 含 DEF-03-001 既有測試一併綠
bash scripts/ci-gate.sh                                         # 雙軌 v0.01+v0.04 仍 exit 0（guard 不干擾 cd vX）
SDD_GATE_DRY_RUN=1 bash scripts/ci-gate.sh                      # 版本解析不受影響
```
通過條件：guard 測試全綠；雙軌 gate exit 0（證 guard 對官方 `cd vX` 零干擾）。

### 3.2 零退化驗證矩陣（本輪 DoD；floor 以本輪實測為準）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **≥ 3069 passed / 0 failed**（floor=F1；W1 不碰 AutoClaude，結構性持平） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken（實際 8 條） |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 雙軌閘門 | `bash scripts/ci-gate.sh` | v0.01 + v0.04 雙軌 not-chaos 全綠 + arch_fitness exit<2（**證 guard 對 `cd vX` 零干擾**） |
| guard 回歸測試 | `pytest scripts/tests/test_cross_version_guard.py` | 全綠（含 bare-from-root fire + 單版不誤觸） |
| 五軌 TLC | **不觸發**（W1 無 `_HAPPY_PATH`/`.tla` 改動，Rule 9.18.1 不啟動） | N/A |

---

## 4. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 落點 | 驗證 |
|------|------|------|
| DEF-02-001：跨版誤用錯誤可行動化（fail-loud） | §2.3(a) `conftest.py` guard | `test_cross_version_guard` bare-from-root fire UsageError + DEF-02-001 訊息 |
| 根因鎖定：每版獨立 process 為唯一隔離 | §2.2/§2.3 + 不變量文件 | 雙軌 gate `cd vX` exit 0；矩陣 R4 載入文件 |
| guard 不干擾官方雙軌 gate | §2.5 T1 | `bash scripts/ci-gate.sh` exit 0 |
| 偵測邏輯可單測（測意圖） | §2.4(b) 純函式 helper | `versions_touched` 單元測試（多版 fire / 單版不 fire / bare 展開） |
| 共享 infra 修復免 Copy-on-Evolve | §2.3(c) 落點在 versioned 目錄外 | git diff 僅 `AISDLC_SDD/conftest.py` + `scripts/`，v0.0X 凍結本體零改動 |
| 零退化 | W1 不碰 AutoClaude | 3069 passed 持平 |

---

## 5. 實作順序（每支完成立即驗證，絕不累積）

> B 軌 Brownfield：本計畫即 SCG-0/1 載體；§2.2-2.4 根因/介面/邊界 = SCG-2；§2.4 delta = SCG-3；落地過 SCG-4；§3.2 矩陣 = SCG-5 RTM。行進中框架摩擦即記入 `AutoSDD_Defect_Log.md`（DEF-05-xxx）。

- **W1-a** `scripts/cross_version_guard.py`（純函式 helper）→ 立即單測 `versions_touched`/`build_guard_message`。
- **W1-b** `AISDLC_SDD/conftest.py`（薄包裝呼叫 helper）→ `python -c` 語法 import 檢查。
- **W1-c** `scripts/tests/test_cross_version_guard.py`（單測 + subprocess 煙霧）→ 跑該檔全綠。
- **W1-d** 實跑雙軌閘門 `bash scripts/ci-gate.sh` → exit 0（證 guard 對 `cd vX` 零干擾）；bare-from-root subprocess 驗 fail-loud。
- **W1-e** 零退化矩陣全項（AutoClaude 3069 / lint-imports 8 / LOC 0 / snapshot 新鮮）。
- **收斂**：任一紅 → 停機修復。

每個 W 結束跑對應驗證；零退化矩陣為本輪硬閘。

---

## 6. 缺陷帳本本輪處置（對照 §0 繼承）

| 缺陷 | 本輪處置 |
|------|---------|
| DEF-02-001（P3, open routed候選） | **本輪 W1 修**（共享 infra fail-loud guard + 根因不變量文件）→ 完成後改 `fixed@improving_05` 附證據；並補記 R4 更深真相（生產套件同名碰撞，非僅 conftest） |
| DEF-01-007（P3, open） | cc-switch 環境工具未裝，本輪不涉 A/B 驗收，續 `open`（watch） |
| DEF-01-009（P3, open watch） | 已自癒（224 非空行 < 250），本輪不碰，續 `watch` |
| 本輪新發現 | 行進中即記 DEF-05-xxx（發現即記、絕不累積） |

---

## 7. 🔴 人工確認凍結點

本文件為 SCG-0/1 規格載體。**實作（W1-a）啟動前須由人類明示確認本計畫凍結**（B 軌紅線：HUMAN_PENDING 不可自動跳過）。本輪需確認兩點：
1. **範圍**：DEF-02-001（已於 2026-06-14 AskUserQuestion 取得）。
2. **修復設計**（待確認）：採「共享 infra fail-loud guard + 根因不變量文件、**免 v0.05 Copy-on-Evolve**」（§2.3），接受 T2 顯式雙版本路徑為文件化殘留（§2.5）。

凍結後依 §5 實作順序執行，全程套 §3.2 零退化矩陣，收尾走多專家 Zero-Trust 審查閉環。
