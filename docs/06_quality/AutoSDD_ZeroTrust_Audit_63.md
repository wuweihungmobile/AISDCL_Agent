# AutoSDD ZeroTrust Audit 63 — B 軌 scaffold_gc 翻環活體化（v0.24→v0.25）

> **輪次**：improving_63｜**日期**：2026-06-25｜**柱位**：B 軌（流程自治 L5 加固）
> **掌舵者 signoff**：AskUserQuestion「B 軌 scaffold_gc 翻 ON」
> **紀律**：所有數字錨定本輪真實 tool 輸出（zero-trust，禁文件宣稱當事實）。

---

## §1 階段一：現況重偵察（HARD GATE）

由兩個背景 Explore/general agent 以 Bash 工具實測（避免 perf 載具膨脹），主 agent 親讀碼複核構件。

| 項目 | 實測命令 | 結果 | 判定 |
|------|---------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3315 passed / 122 skipped / 0 failed**（124.87s）| ✅ ＝floor 3315 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（195 檔/489 依賴）| ✅ |
| (c) LOC budget | `python tools/check_loc_budget.py` | **violations=0**（total=18999/cap=20438）| ✅ |
| (d) Snapshot/git | `snapshot_sync --check` / `git status --short` | **新鮮 / 工作樹乾淨**| ✅ |
| (e) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.24:1656 / scripts:129；arch_fitness fail=0/warn=3| ✅ |
| (f) 構件存在性 | 親讀 `fsm_runtime.py` | 唯一殘留預設 OFF 的 B 軸 opt-in arm = `_scaffold_gc_auto_propose_enabled()`（:87-91 truthy-only）；fire/catch/SLV/AUTO_RECOVERY 皆已預設 ON | ✅ |

**HARD GATE 結論**：基線零退化、零 failed、不低於上輪（3315 ≥ floor 3315；v0.24:1656 ≥ floor 1656）→ **准予進入階段二**。

**arch_fitness advisory 佐證**：v0.24/v0.25 兩版皆 FF-16 GAP-X2「鷹架代謝 GC 從未產退役 ROI 提案（代謝肌肉從未收縮）」——正是本輪翻環標的，方向與系統現況訊號吻合。

## §2 階段二/三：增量設計 + 實作（W-63-1/2/3）

**Copy-on-Evolve v0.24→v0.25**：官方 `scripts/copy_on_evolve.sh`（git-archive 純 tracked 860 檔 + 自動 bump 版本戳 45 檔/skills 鏡像 59 檔/.gitignore block）。

| W 項 | 改動 | 檔 |
|------|------|-----|
| W-63-1 | `_scaffold_gc_auto_propose_enabled()` truthy-only → unset→True/顯式 falsy→opt-out（鏡像 `_auto_recovery_enabled`）+ 註解 | `tools/fsm_runtime/fsm_runtime.py:80-100` |
| W-63-2 | 新增 session autouse fixture `_isolate_scaffold_gc_default`（測試套預設 flag="0"）| `tools/fsm_runtime/tests/conftest.py:62-87` |
| W-63-3 | wiring Case 1 改 `test_default_on_enter_auto_runs_gc`（default-ON 活體）、Case 2 改 `test_explicit_opt_out_pure_tracking_no_auto_gc`（opt-out 零退化）| `tools/fsm_runtime/tests/test_scaffold_gc_auto_propose_wiring.py:45-91` |

**改動範圍實測（diff v0.24 vs v0.25）**：
- `fsm_runtime.py`：**僅** flag 註解區塊 + `_scaffold_gc_auto_propose_enabled()` 函式體（外科手術級，`_HAPPY_PATH` 未碰）。
- `conftest.py`：**純 additive**（新增 26 行 fixture，既有零改）。
- `transition_rules.py` + 5 `formal/*.tla`：**逐位元零差異**（diff exit 0）→ 免五軌 TLC（Rule 9.18.1 無重跑義務）。

## §3 階段三雙重驗證（單測 + 契約 + 零退化護欄）

| 驗證 | 命令 | 結果 |
|------|------|------|
| scaffold wiring + phase_h | `pytest test_scaffold_gc_auto_propose_wiring.py test_phase_h.py -q` | **45 passed**（8.85s）|
| v0.25 全套 not-chaos | `pytest tools/fsm_runtime/tests/ -m "not chaos" -q` | **1656 passed / 4 skipped**（30.20s，＝v0.24 同數，零退化）|
| conftest 隔離生效 | `ls v0.25/build/reports/gc/` | **無報告洩漏**（裸 enter_scaffold_gc 測試 byte-identical）|
| FSM/tla 零差異 | `diff` transition_rules.py + 5 *.tla | **全 exit 0**（免 TLC 依據成立）|

## §4 階段四：CI 平價收斂（零退化矩陣全項）

| 檢查 | 命令 | 通過條件 | 結案實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥3315/0 failed | **3315/0**（零接觸 AutoClaude，`git status --porcelain AutoClaude/`=空）|
| 架構契約 | `lint-imports` | kept/0 broken | **8 kept/0 broken**（基線，零接觸）|
| LOC | `check_loc_budget` | 全過 | **violations=0**（基線，零接觸）|
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | **exit 0**；v0.01:1478 / **v0.25:1656** / scripts:129 |
| Snapshot/SSOT | ci-gate 內含 | 新鮮 | **全綠**（FRAMEWORK_STATUS 重生、skill 戳 v0.25、父層 skills 鏡像 v0.25 59 檔、router hook v0.25、gitignore block v0.25）|
| 五軌 TLC | 僅 FSM 變更時 | n/a | **n/a**（FSM/*.tla 對 v0.24 逐位元零差異，diff exit 0）|

**ci-gate 尾部真實輸出**：
```
✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.25）
   逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.25:1656 scripts/tests:129
EXIT=0
```

> **誠實註記**：FRAMEWORK_STATUS.md 首跑 ci-gate 因新建 v0.25 而 stale（預期，Copy-on-Evolve 後步驟），`python scripts/framework_status_snapshot.py --write` 重生後重跑 ci-gate EXIT=0。FF-16 GAP-X2 advisory 仍存（不阻擋）——翻環使機制預設活體，advisory 查磁碟 build/reports/gc/ 實際報告，於 production 代謝週期跑過後自然清除，本輪不為清 advisory 強塞 runtime 報告入庫。

## §5 多專家 Zero-Trust 審查（Architect / SA-SD / QA）

> **派發紀律（DEF-24-001）**：v0.25 為本輪未追蹤新增檔，三鏡一律**主樹派發、禁 worktree**（worktree 由 HEAD 建樹看不到 untracked 新檔→假陰性）。QA 突變待 Architect/SA-SD 完成後序派（避免並讀同檔假紅）。

### 5.1 Architect 鏡 — ✅ OVERALL PASS
5/5 宣稱屬實，無不一致：
1. 改動外科手術級——`fsm_runtime.py` 僅 2 hunk（flag 註解 + 函式體 truthy-only→unset→True），`_HAPPY_PATH`/`enter_scaffold_gc` 主邏輯/其餘函式皆未碰；81 def/class 兩版相同、總行數僅 +9。
2. `transition_rules.py` + 5 `*.tla` diff **全 exit 0**（免五軌 TLC 依據成立）。
3. 架構純潔（無新 God-object/類別；`scaffold_gc.py` 本身 diff exit 0；conftest 純 additive `61a62,87`）。
4. AutoClaude 零接觸（`git status --porcelain AutoClaude/` 空）。
5. 翻環模式與 `_auto_recovery_enabled`/`_slv_auto_propose_enabled`/`_rule_fire_telemetry_enabled` **逐字同構**。
附帶查證：wiring 非空殼、紅線 spy 真實、fail-closed 有測試。

### 5.2 SA-SD 鏡 — ✅ OVERALL PASS
6/6 核心宣稱屬實，三道護欄程式+測試雙層成立：
1. run_gc 路徑**零 set_maturity 呼叫**（`scaffold_gc.py` 全 177 行查證，:11/:149 為 docstring/報告字串非呼叫）。
2. 報告寫 `build/reports/gc/SCAFFOLD-ROI-{date}.md`（運行工作區，非凍結 governance）。
3. fail-closed（run_gc 包 try/except，失敗進態仍成功、不偽造 report_path）。
4. opt-out 保留（顯式 0/false/no/off → False，還原 v0.07）。
5. 敘事連貫（fire/catch v0.24 預設 ON → fire_count 真實累積 → GC 有資料）。
6. 計畫書 W-63-1/2/3 + RTM 測試名與實檔逐一吻合。
**P4 標示瑕疵（已 review，不阻擋）**：計畫書 §2/§5 部分行號（如 scaffold flag `:87-91`）為 v0.24 重偵察當時位置，v0.25 翻環後因註解擴充位移至 `:95-100`——屬「描述 v0.24 前態 vs v0.25 後態」的版本脈絡差，非錯誤；本審計 §2 W 表已以 v0.25 後態行號為準。

### 5.3 QA 鏡 — ✅ OVERALL PASS（突變實證非空殼）
- **任務1 獨立複現**：`pytest wiring + phase_h` → **45 passed**（執行層零信任複現，補 Architect/SA-SD 僅靜態查證之缺口）。
- **任務2 突變實證（生產碼）**：
  - 突變 A（`return True`→`return False` 模擬翻環失效）→ `test_default_on_enter_auto_runs_gc` **1 failed**（`KeyError: 'auto_gc'`）→ Edit 還原 → **1 passed**。
  - 突變 B（插入 `set_maturity` 模擬破 R-9.20 #11 紅線）→ `test_red_line_gc_never_auto_retires` **1 failed**（spy 抓到呼叫）→ Edit 還原 → **1 passed**。
  - ⇒ 兩護欄測試**會抓真實回退，非空殼**。
- **任務3 缺陷帳本誠實**：無 DEF-63 條目與「本輪無新增」一致；§1 八項 open/routed 與總表逐一吻合。
- **收尾**：`git diff --stat fsm_runtime.py` 空、`pytest wiring` 9 passed → **工作樹零殘留污染**（突變還原一律 Edit，禁 git checkout，守 DEF-61-001）。

## §6 結案裁決

**三鏡（Architect / SA-SD / QA）+ QA 突變實證全 PASS → 本輪 OVERALL PASS，准予結案。**

- **零退化**：AutoClaude 3315/0（零接觸）、lint 8 kept、LOC 0、ci-gate EXIT=0（v0.01:1478 / v0.25:1656 / scripts:129）。
- **紅線零弱化**：run_gc 永不 set_maturity（QA 突變 spy 機械證實）、fail-closed、入口紀律不弱化、FSM/`*.tla` 對 v0.24 逐位元零差異（免 TLC）。
- **maturity 誠實**：B 軸 L5 **機制加固**（scaffold 代謝由 opt-in→預設活體），`L_合體` 維持 L5，**非升級**。B 軸 opt-in→default-ON 翻環家族（AUTO_RECOVERY/SLV/fire/catch/scaffold_gc 五支）至此收齊。
- **缺陷**：本輪無新框架缺陷。DEF-62-001（auto_recovery call-site 註解滯後）於 v0.25 行號移至 L420（因本輪 scaffold 註解前插位移），維持 open/routed——守 Rule 3 surgical 不擴 scope 修他域 feature 註解。
- **誠實 nuance**：FF-16 GAP-X2 advisory 仍存（不阻擋），翻環使機制預設活體，advisory 於 production 實際代謝週期跑過後自然清除。
