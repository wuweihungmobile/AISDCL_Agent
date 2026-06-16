# AutoSDD Improving_22 — 缺陷清償輪（cleanup）：DEF-12-002 + DEF-15-001 深層重構

> **輪次**：整合迭代軌道① 第 22 輪（improving_21 已結案，tag v2026.06.16-18）
> **柱別**：**B 軌（手腳 AISLDC_SDD dogfooding）為主** —— 本輪為缺陷清償輪，無 A/C 軌新功能。
> **定位**：清償 Copy-on-Evolve 版本治理家族殘留缺陷（DEF-12-002 hook 誤攔 / DEF-15-001 模板寄居 runtime 目錄結構異味）。
> **框架版本演化**：v0.12 → **v0.13**（Copy-on-Evolve；觸發者＝W-22-2 移動 FSM 種子模板 + 改 `state_loader.TEMPLATE_PATH`）。
> **日期**：2026-06-17

---

## 階段一：Zero-Trust 重偵察（實測事實，硬閘 PASS）

| 項目 | 實測 | 判定 |
|------|------|------|
| AutoClaude 全套 pytest | **3112 passed / 122 skipped / 0 failed**（109.06s, exit 0） | ✅ 硬閘 PASS（命中上輪 floor 3112；CLAUDE.md 記的 2972 已過期） |
| lint-imports | Analyzed 184 files, 466 deps；**8 kept / 0 broken** | ✅ |
| LOC 預算 | total=17794 baseline=17032 cap=20438 violations=0 | ✅ |
| Snapshot | OK — Snapshot 區段 + sprint 骨架對齊 | ✅ 新鮮 |
| AISLDC_SDD ci-gate | v0.01:1478 / **v0.12:1577** / scripts/tests:25；arch_fitness structural exit<2（2 個 FF-16 advisory 不阻擋） | ✅ |
| 最新凍結版 | **v0.12**（v0.01~v0.12 連續） | — |
| 上輪 21 構件 | closure_evidence.py / closure_evidence_verify hook / rederive CLI / 22 真 git repo 測試 / install_post_commit.{sh,ps1} 全存在 | ✅ |

**本輪 floor（禁寫死，取自本階段一實測）**：AutoClaude **3112**、ci-gate v0.12 **1577**、scripts/tests **25**、lint-imports **8 kept**。

**缺陷帳本未結 6 項**（皆已重現確認）：DEF-01-007（cc-switch 環境缺裝，NOT FOUND）、DEF-01-009（plugin watch，過閘）、**DEF-12-002**（`::` 誤攔，本輪修）、**DEF-15-001 深層**（模板寄居 runtime 目錄，本輪修）、DEF-19-001（catch 4/39 漸進）、DEF-13-002（resolved 追蹤點）。

---

## 階段二：本輪增量設計

### 柱別與 W 項

| W 項 | 缺陷 | 軌 | Copy-on-Evolve | 範圍 |
|------|------|----|----------------|------|
| **W-22-1** | DEF-12-002（P3） | B | **免**（shared infra） | `cross_version_guard._is_path_arg` 對 pytest nodeid（`path::test`）剝除 `::` 後綴再判路徑存在 + 回歸測試 |
| **W-22-2** | DEF-15-001 深層（P2） | B | **v0.12→v0.13** | FSM 種子模板 `FSM-STATE-TEMPLATE.yaml` 由 runtime `build/reports/fsm/` 移至 tracked 源碼位 `tools/fsm_runtime/templates/`；改 `state_loader.TEMPLATE_PATH`；同步文件連結 + `.gitignore` + 回歸測試 |

### SCG-0/1（需求/設計凍結 — Brownfield，本計畫書為載體）

- **問題陳述（As-Is）**：
  - DEF-12-002：`_is_path_arg`（[cross_version_guard.py:44](../../AISDLC_SDD/scripts/cross_version_guard.py#L44)）以 `os.path.exists(token)` 判路徑。pytest 從 REPO_ROOT 跑單一測試的 nodeid `檔案.py::test_y` 含 `::` → `os.path.exists` False ∧ 無版本片段 → 誤判「無路徑 arg」→ 走 bare 分支 `_versions_under_dir(cwd)` 展開全部版本 → 誤報「跨版 pytest 偵測」UsageError。
  - DEF-15-001 深層：FSM 種子模板（`state_loader._load_template()` 必需的**真輸入**）寄居於 runtime 輸出目錄 `build/reports/fsm/`，導致兩處反覆打補丁的結構異味：(1) `copy_on_evolve.sh` 須特例「排除後補回模板」；(2) `.gitignore` 須逐層 negate re-include（每新版重複一段 4 行 idiom）。根因＝**輸入（模板）與輸出（runtime 狀態檔）混居同一目錄**。
- **To-Be（凍結意圖）**：
  - DEF-12-002：剝除 nodeid `::` 後綴後再判存在；版本化 nodeid 的版本偵測（`_versions_in_path` 的 `findall`）不受 `::test` 後綴影響故不需改。**Surgical**：僅改 `_is_path_arg` 一處。
  - DEF-15-001：模板移至 `tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml`（與 loader 同層、tracked 源碼位、`build/reports/` 之外）。輸入/輸出分離後 → v0.13 `.gitignore` 對 `build/reports/` 可**整樹排除無需 negate**；`copy_on_evolve.sh` 特例對 v0.13+ 自然成 no-op（模板已不在 build/reports）。

### SCG-2/3（介面 delta / 契約）

**介面 delta（W-22-1）** — [AISDLC_SDD/scripts/cross_version_guard.py](../../AISDLC_SDD/scripts/cross_version_guard.py)：
```python
def _is_path_arg(token: str, cwd: str) -> bool:
    if VERSION_RE.search(token):
        return True
    # pytest nodeid 形如 path::test_x —— 剝除 :: 後綴再判路徑存在（DEF-12-002）
    path_part = token.split("::", 1)[0]
    if os.path.exists(path_part):
        return True
    return os.path.exists(os.path.join(cwd, path_part))
```
+ [test_cross_version_guard.py](../../AISDLC_SDD/scripts/tests/test_cross_version_guard.py) 新增 nodeid 回歸 case（退化即紅）。

**介面 delta（W-22-2）** — `AISDLC_SDD_v0.13/tools/fsm_runtime/state_loader.py`：
```python
# 舊：TEMPLATE_PATH = REPO_ROOT / "build" / "reports" / "fsm" / "FSM-STATE-TEMPLATE.yaml"
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "FSM-STATE-TEMPLATE.yaml"
```
- DEFAULT_STATE_DIR（runtime 狀態檔輸出 = `build/reports/fsm/`）**不變**（仍為輸出位）。
- docstring line 3 `Source of truth: ...` 同步改新路徑。
- 檔案物理移動：`build/reports/fsm/FSM-STATE-TEMPLATE.yaml` → `tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml`（v0.13 內，git mv 等價）。
- 文件連結同步（v0.13 內 3 處）：`workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`、`AISDLC_SDD_UPGRADE_SOP.md`、`.claude/skills/test-failure-analyzer/SKILL.md`。
- `.gitignore` 新增 v0.13 區塊：`AISDLC_SDD_v0.13/build/reports/*` **整樹排除（無 negate）** + arch-fitness.json + chaos-report.json；新 `templates/` 在 `tools/` 下為正常 tracked 源碼。
- 回歸鎖（v0.13）：`tools/fsm_runtime/tests/` 新增 assert `TEMPLATE_PATH` 落在 tracked 源碼位（含 `tools/fsm_runtime/templates`、不含 `build/reports`）且 `is_file()`。

### LOC 預算落點

- W-22-1：`cross_version_guard.py` +2 行（一行 split、一行註解）；不近任何分級上限。
- W-22-2：`state_loader.py` 改 1 行常數 + 1 行 docstring（淨 0~+1 行）；模板僅搬移；皆遠低於分級上限。

### `.importlinter` 影響分析

**零影響**：W-22 完全不觸碰 AutoClaude（`core/`/`infra/`/`plugins/`），僅改 AISLDC_SDD（`scripts/` + v0.13 框架本體）。lint-imports（AutoClaude 架構契約）受測對象不變 → 維持 8 kept / 0 broken（以非觸碰保證）。

### 五軌 TLC 分析

**不觸發**：W-22 無 `_HAPPY_PATH` / `*.tla` / FSM transition 邏輯變更（僅檔案位置 + 路徑常數）。將以 `git diff` 證 v0.13 `transition_rules.py` + 5 個 `.tla` 對 v0.12 逐位元零差異（Rule 9.18.1 不啟動）。

---

## 🛡️ <Architecture_Design_Review>（寫實質 Python 前）

1. **架構純潔性（God-object / Thin Facade）**：N/A — 不觸碰 AutoClaude 微核心。AISLDC_SDD 側：`state_loader` 僅改一路徑常數，職責不變、無新增 God-object；`_load_template` 介面不變。
2. **持久化相容（additive / DAL 三後端）**：N/A — 不動 AutoClaude `PlaybookCheckpoint` / DAL。AISLDC_SDD 側：模板**內容零變更**（僅位置），FSM-STATE schema 不動，向後相容（runtime 狀態檔輸出位 `build/reports/fsm/` 不變）。
3. **安全防護網（CONDITIONAL 白名單）**：N/A — 無「從文件生成指令」新路徑。W-22-1 `cross_version_guard` 為純偵測函式（無 shell 執行）；`split("::")` 僅字串處理。
4. **對外 I/O 安全（ToolInvocationPort）**：N/A — 本輪零新增外呼路徑。

> 結論：W-22 為 AISLDC_SDD 共享 infra + 框架本體的結構清償，AutoClaude 架構紅線**以非觸碰保證零退化**；AISLDC_SDD 側改動局部、語意保持。

---

## RTM（需求追溯矩陣）

| 需求/缺陷 | 設計 | 實作 | 驗證 |
|-----------|------|------|------|
| DEF-12-002（nodeid `::` 誤攔） | `_is_path_arg` 剝 `::` | `cross_version_guard.py` 改 1 處 | `test_cross_version_guard.py` 新增 nodeid case + scripts/tests 全綠 |
| DEF-15-001 深層（模板移 tracked 源碼位） | `TEMPLATE_PATH` 指 `tools/fsm_runtime/templates/` | v0.13 移檔 + 改常數 + docstring + 3 文件連結 + .gitignore | v0.13 pytest not-chaos ≥1577（FSM bootstrap 從新位載入）+ 新增 TEMPLATE_PATH 位置回歸鎖 + ci-gate 雙軌 exit 0 |
| 零退化（AutoClaude） | 非觸碰 | — | AutoClaude pytest ≥3112 / 0 failed；lint 8/0 |
| 結構異味消除（DEF-15-001 根因） | 輸入/輸出分離 | v0.13 .gitignore 無 negate；copy_on_evolve 特例 no-op | `git add -A -n AISDLC_SDD/AISDLC_SDD_v0.13/` dry-run 審 would-add 無 runtime/stale；模板 tracked |

---

## 階段四：零退化驗證矩陣（floor 取本輪階段一實測，禁寫死）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3112** passed / 0 failed |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISLDC_SDD 閘門 | `bash scripts/ci-gate.sh` | 雙軌 v0.01 + **v0.13** exit 0；v0.13 pytest not-chaos ≥1577；arch_fitness exit<2 |
| scripts/tests | （ci-gate 內含軌） | ≥ **25** passed（含 W-22-1 新 case） |
| 五軌 TLC | 不適用（無 FSM/tla 變更） | `git diff` 證 transition_rules.py + 5 tla 逐位元零差異 |
| 潔淨度 | `git add -A -n AISDLC_SDD/AISDLC_SDD_v0.13/` | would-add 無 build/reports runtime 產物 / arch-fitness.json / stale（DEF-11-002 紀律） |

---

## 缺陷回流（本輪處置）

- **DEF-12-002**：fixed@improving_22（shared infra）。
- **DEF-15-001 深層**：fixed@improving_22（v0.13）—— 深層重構完成，結構異味根因消除。
- DEF-01-009 / DEF-19-001：本輪不動，帳本更新進度（watch / routed 維持，理由：Rule 2/3 + 本輪 scope）。
- 行進中新發現摩擦：即記入 `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-22-xxx）。

---

## 結案契約（closure-evidence — 結案 commit 後填入真實 hash/tag）

```yaml
closure-evidence:
  round: 22
  framework_version: v0.13
  claimed_commits: []   # 結案 commit 後填
  claimed_tag: ""        # 結案 tag 後填
  floors:
    autoclaude_pytest: 3112
    ci_gate_v_latest: 1577
    scripts_tests: 25
    lint_imports_kept: 8
```
