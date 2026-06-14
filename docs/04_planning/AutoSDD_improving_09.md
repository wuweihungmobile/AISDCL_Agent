# AutoSDD_improving_09 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 9 輪）

> **版本**：09（第九輪迭代）
> **日期**：2026-06-14
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ 結案（誠實輕量盤點輪）；範圍＝**零信任健康確認盤點**，本輪**無實質 W 項**（Rule 2 Simplicity First，不為遞增而遞增）。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3069 passed / 122 skipped / 0 failed**（2026-06-14 本機實測 96.62s，**非引用文件數字**）；AISDLC_SDD 雙軌閘門 exit 0。
> **本輪定位**：承 improving_06（A 軌主鏈結案）／improving_07（DEF-06-001 取證友善性收尾）／improving_08（健康確認盤點）之後，improving_09 為「**按需增量**」鏈上的再次健康確認輪——階段一零信任重偵察證實**無自動可導出的實質驅動**（鏈閉合、無新缺陷、唯二 open P3 皆非本輪可行動）。經 🔴 人工方向確認（2026-06-14，於三選項中選定「誠實輕量結案盤點」），本輪不製造工作、不開新 W 項、免 v0.05 Copy-on-Evolve。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-14，非文件宣稱）

本計畫所有判斷皆錨定下列**已實測事實**（主 agent 親跑，非引用文件）：

| # | 事實 | 證據位置 | 對本輪的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套 = **3069 passed / 122 skipped / 0 failed**（96.62s） | 本機 `python -m pytest tests/ -q`（背景作業 bzr5amwkv，尾行 `3069 passed, 122 skipped in 96.62s`） | 本輪零退化 floor = 3069，**正中上輪 floor**、0 failed |
| F2 | `lint-imports` = **8 kept / 0 broken**（181 files / 460 deps） | `PYTHONUTF8=1 lint-imports` | 架構紅線，8 條 contract 全保 |
| F3 | AISDLC_SDD `ci-gate.sh` 雙軌 = **exit 0**；v0.01:**1478** / v0.04:**1494**（各 not-chaos 全綠 + arch_fitness advisory 不阻擋） | `bash scripts/ci-gate.sh`（`/tmp/cigate_09.log`，背景作業 bkz43zep5，`CI_GATE_EXIT=0`） | 雙軌健康；逐軌數字與 improving_07/08 持平 |
| F4 | LOC budget violations=**0**（total=17511 / baseline=17032 / cap=20438） | `python tools/check_loc_budget.py` | 分級政策全過 |
| F5 | snapshot = **OK**（Architecture Snapshot + sprint 骨架對齊） | `python tools/snapshot_sync.py --check` | 文件新鮮 |
| **V1** | **DEF-06-001 修復無回歸**：本輪 ci-gate 收斂段自證印出「逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.04:1494」，單次輸出即自證逐軌結果 | `/tmp/cigate_09.log`（尾 3 行：總結行 + 逐軌計數行） | 上輪取證友善性修復穩定生效 |
| A1 | DEF-01-007（cc-switch 未裝）仍重現（環境工具，非純程式可修）；DEF-01-009（`sdd_governance_plugin.py` raw 250 貼上限、受控非空行 < 250、violations=0）已自癒 watch，本輪零擴充不觸發 | `command -v cc-switch`=NOT FOUND；`wc -l sdd_governance_plugin.py`=250 + F4 violations=0 | §4 缺陷處置 |
| A2 | 上輪（improving_06/07/08）修復構件全部存在 | `pytest_passed_count.sh`／`test_pytest_passed_count.py`／`conftest.py`／`cross_version_guard.py`／`test_def_01_008_brain_injection.py`／`main.py` enable_kernel_brain×2 皆 `ls`/`grep` 證實 | (d) 構件存在性 PASS |

**硬閘判定**：F1 基線 0 failed 且 3069 = 上輪 floor → **通過**。本輪零退化 floor 錨定 = **3069**。

---

## 1. `<Architecture_Design_Review>`（強制自我檢核）

> **本輪零實質程式改動**：AutoClaude 微核心 `core/`/`plugins/`/`adapters/` 零改動；AISDLC_SDD 凍結本體（v0.0X 的 agent/governance/workflow/tools/.claude）零改動；共享 CI infra（`scripts/`）零改動；**不做 v0.05 Copy-on-Evolve**。本節四項檢核因「無新增路徑」全數 N/A，記錄以維持紀律完整性。

| 檢核項 | 結論 |
|--------|------|
| 1.1 架構純潔性（God-object / Thin Facade） | **N/A 且維持**。零新增程式碼、零碰 kernel/plugin/port/adapter。`playbook_runner.py` Thin Facade 不變。 |
| 1.2 持久化相容（additive / DAL 三後端零停機） | **N/A 且維持**。零持久化觸碰，無 alembic / PlaybookCheckpoint / DAL 變更。 |
| 1.3 安全防護網（CONDITIONAL 鏈式攻擊） | **N/A 且零弱化**。零新增「從文件生成指令」路徑，CONDITIONAL 三層防禦與本輪無交集。 |
| 1.4 對外 I/O 安全（`ToolInvocationPort` 外呼） | **N/A**。零新外呼端點、零新網域、SSRF/allowlist 攻擊面零變化。 |

**結論：四項檢核全數因零實質變更而 N/A，無架構衝突、無凍結本體改動。本輪不撰寫任何實質 Python。**

---

## 2. 本輪增量設計 — 無實質 W 項（按需判定）

### 2.1 為何本輪無 W 項（Rule 2 / 範本「按需增量」）

階段一零信任重偵察盤點結果：

1. **A 軌主鏈已結案**（improving_06）；improving_07 已關閉唯一 routed P3（DEF-06-001 取證友善性）；improving_08 已確認鏈健康。
2. **缺陷帳本除唯二 P3 外全 fixed**，且這兩項**均非本輪可行動**：
   - **DEF-01-007**（cc-switch 未裝）：環境工具缺裝，**非純程式可修**——須使用者於環境補裝 cc-switch，方能跑 §5.2 多模型後端 A/B 驗收。屬環境動作，不在本輪 code scope。
   - **DEF-01-009**（`sdd_governance_plugin.py` raw 250）：watch item，已自癒（受控非空行 < 250、violations=0），明文「對該 plugin 任何擴充前必先拆 package；本輪零擴充不觸發」。
3. **本輪階段一無新發現缺陷**（所有健康指標綠）。

依 improving_07/08 已確立之「**按需增量、不為遞增而遞增**」定位（Rule 2 Simplicity First），**製造工作的兩條路皆判定拒絕**：

| 反例（被拒絕的「製造工作」） | 拒絕理由 |
|---------------------------|---------|
| 預先拆 `sdd_governance_plugin` 為 package | 違反 Rule 2/3——重構沒壞的東西；DEF-01-009 明文「零擴充不觸發」，無觸發條件下拆分屬投機重構 |
| 強開新 A 軌整合 scope | 主鏈已閉、需使用者指定方向；無方向時自創 scope = 為遞增而遞增 |

### 2.2 🔴 人工方向確認

2026-06-14 經 🔴 人工確認，於三選項（誠實輕量結案盤點 / 提供 cc-switch 安裝關 DEF-01-007 / 指定新 A 軌 scope）中選定 **「誠實輕量結案盤點」**。本輪據此產出健康確認四件套，不開實質 W 項。

---

## 3. 階段四 — CI 平價與驗證（盤點性，零退化矩陣全項）

本輪雖無實質程式改動，仍執行零退化驗證矩陣**全項**以確認鏈健康（floor 以本輪實測為準、禁寫死）：

| 檢查 | 命令 | 通過條件 | 本輪實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 上輪 3069 / 0 failed | ✅ **3069 passed / 122 skipped / 0 failed** |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | ✅ **violations=0** |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2 | ✅ **exit 0**（v0.01:1478 / v0.04:1494） |
| 五軌 TLC | （僅 FSM 變更時）| 五軌 0 violation | **N/A**（本輪零 FSM／`*.tla`／`_HAPPY_PATH` 變更） |

DAL 等價：本輪零持久化／DAL 觸碰，三後端等價性不受影響（無新 round-trip 契約需驗）。

---

## 4. 缺陷帳本本輪處置（對照 §0 繼承）

| ID | 嚴重度 | 上輪狀態 | 本輪處置 |
|----|--------|---------|---------|
| DEF-06-001 | P3 | fixed@improving_07 | **複驗無回歸**（V1）：本輪 ci-gate 收斂段自證逐軌計數行正常顯示，修復穩定生效 |
| DEF-01-007 | P3 | open | **維持 open**：cc-switch 仍 NOT FOUND（環境工具非純程式可修）；本輪複驗日期更新；俟環境補裝後依 §5.2 手動 A/B |
| DEF-01-009 | P3 | open watch | **維持 open watch**：raw 250 持平、已自癒（violations=0）、本輪零擴充不觸發；續 watch |
| 其餘 | — | fixed | 無回歸（F1~F5/A2 全綠佐證） |

**本輪新發現缺陷**：無（DEF-09-xxx 未產生）。

---

## 5. 實作順序

**無**（本輪零實質程式改動）。

---

## 6. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 | 狀態 |
|------|------|------|------|------|
| R-09-1 階段一零信任重偵察、硬閘判定 | §0 事實表 F1~F5/V1/A1/A2 | 主 agent 親跑五項實測 + 構件複驗 | F1=3069/0 failed、F2=8 kept、F3=exit 0、F4=0、F5=OK、A2 構件全在 | ✅ PASS |
| R-09-2 按需判定本輪是否有實質驅動 | §2.1 盤點 + 拒絕製造工作 | 缺陷帳本盤點 + 🔴 人工方向確認 | §2.2 選定輕量結案 | ✅ PASS |
| R-09-3 上輪 DEF-06-001 修復無回歸 | §0 V1 | 本輪 ci-gate 親跑 | `/tmp/cigate_09.log` 逐軌計數行自證 | ✅ PASS |
| R-09-4 零退化矩陣全項綠 | §3 矩陣 | 五項命令親跑 | §3 實測欄全 ✅ | ✅ PASS |
| R-09-5 缺陷帳本完整誠實更新 | §4 處置 | Defect_Log 更新複驗日期 | 兩 P3 維持 open、無新缺陷、無虛報 | ✅ PASS |

---

## 7. 🔴 人工確認凍結點

- **方向確認**：2026-06-14 已 🔴 人工確認「誠實輕量結案盤點」（§2.2）。
- **結案宣告**：improving_09 為健康確認盤點輪，零實質程式改動、零退化、鏈維持閉合。
- **下一份**：improving_10（按需）——僅在 A 軌出現新整合驅動、或 open P3 變為可行動（cc-switch 補裝 / sdd_governance_plugin 需擴充）時觸發。
