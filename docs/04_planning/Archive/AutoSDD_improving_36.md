# AutoSDD_improving_36 — C 軌 SD_09 W1 前置必修：DEF-35-001 goal_synthesis 單檔 source_sha256 支援

> **軌道①整合迭代** 第 36 輪。**本輪主柱＝C 軌（指揮官 AutoClaude）**。🔴 掌舵者定調（AskUserQuestion）：
> 本輪 scope ＝**修 DEF-35-001**（閘門無關之 W1 前置必修）；修法採**方案 A（單檔支援）**。
> 下一份：`AutoSDD_improving_37`（按需，建議＝06-26 G0 開啟後的 W1 正式執行輪）。
>
> **凍結**：2026-06-18。tag 待定。前輪：improving_35（C 軌 W1 mutation pilot 準備／多模組鎖定契約前置，commit 2a21210，tag v2026.06.18-33）。

---

## 0. 本輪定位與防跨軌誤指

| 項目 | 內容 |
|------|------|
| 軌道 | ① 整合迭代（根層 docs/） |
| 主柱 | **C 軌**（AutoClaude 自身能力 / SD_09 W1 前置必修） |
| 工作流帳本 | `AutoClaude/docs/05_development/SD09_Execution_Guide.md`（C 軌沿用其 G0~G6 與 W 紀律） |
| 缺陷回流 | 根層 `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-35-001 → fixed@improving_36） |
| 下一份 | `AutoSDD_improving_37`（按需，建議 06-26 G0 開啟後 W1 正式執行） |

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit，硬閘通過）

主 agent 主樹親跑實測（皆附證據，禁文件宣稱）：

| 項目 | 實測 | 結論 |
|------|------|------|
| (a) AutoClaude 全套 pytest | **3218 passed / 122 skipped / 0 failed**（110.63s） | = 上輪基線，**硬閘通過** |
| (b) lint-imports | 8 kept / 0 broken | PASS |
| (d) improving_35 構件 | commit 2a21210 / tag v2026.06.18-33 全存 | PASS |
| (e) DEF-35-001 重現 | `plugins/goal_synthesis` 與 `tests/plugins/goal_synthesis` 皆**為單檔非目錄**（`test -d`=MISSING）；`goal_synthesis_plugin.py` 187 行存在；token_guard / core/orchestration 對照皆為目錄；ci.yml:374-375 dormant job 路徑亦錯 | open，W1 前必修 |
| (f) 缺陷帳本 open/routed | DEF-35-001(routed W1)、DEF-32-002、DEF-19-001、DEF-01-007、DEF-01-009、DEF-17-001 | 已盤點 |

**本輪 floor = 3218 passed。**

### 1.1 誠實 scoping（Dr. Alan 定調 + 掌舵者拍板）

- **W1「執行」仍被 2026-06-26 G0 閘門 blocked**（今天 06-18）：#2 AC4（~06-20）+ #3 obs/drift（~06-26）兩者皆過才開；#1 unique sha 須 W1 合法改 token_guard 源碼自然解（紀律 #12 禁人工 churn）；主 agent 禁偽造 nightly。故 W1 task list（T1-B1 tag / T1-B6 兩週 nightly / T1-B7 Report）本輪**不能做**。
- **本輪唯一閘門無關且有實質價值的工作 ＝ 修 DEF-35-001**（缺陷帳本已標「W1 啟動前必修」）。其修法在帳本明標 🔴「確認前不動實作」（屬 production 配置/行為變更）。
- **🔴 人工閘門（AskUserQuestion 2026-06-18）**：(Q1) 本輪 scope ＝ C 軌修 DEF-35-001；(Q2) 採方案 A（單檔支援）。

---

## 2. 階段二：增量設計（W-36-1）

### <Architecture_Design_Review>

1. **架構純潔性**：僅改 `tools/mutation_baseline_lock.py`（CI 工具，非微核心/plugin/adapter），加 `is_file()` 分支與 `_MODULE_PATHS` 單檔指向。無 God-object、Thin Facade 不受影響、未動 `core/ports`/`plugins`。
2. **持久化相容**：未觸碰 PlaybookCheckpoint／DAL 三後端，零停機相容維持。
3. **安全防護網**：未新增任何指令生成路徑，CONDITIONAL 三層防禦不受影響。
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑，allowlist 不受影響。

### 2.1 W-36-1 設計（方案 A，介面 delta）

| 項目 | 內容 |
|------|------|
| 改檔 1 | `tools/mutation_baseline_lock.py`：`compute_source_sha256` 加 `is_file()` 分支（單檔直接 hash，截 16 chars，與目錄分支對稱）；`_MODULE_PATHS["goal_synthesis"]` → 指向單檔 `goal_synthesis_plugin.py` |
| 改檔 2 | `.github/workflows/ci.yml`（dormant W1 job:374-375）：`--paths-to-mutate=autoclaude/plugins/goal_synthesis_plugin.py --tests-dir=tests/plugins/test_goal_synthesis_plugin.py`（源單檔 ↔ 單測試，皆實際存在） |
| 改檔 3 | `AutoClaude/docs/05_development/SD09_Execution_Guide.md`（T1-B3:322 + G1 grep:335）：計畫路徑同步單檔精準 |
| 新增測試 | `tests/tools/test_mutation_baseline_lock.py` +3 case（單檔解析非 unknown / 單檔內容差異 / **DEF-35-001 真實路徑回歸鎖**） |
| LOC 落點 | `mutation_baseline_lock.py` 為 `tools/`（CI 工具），check_loc_budget violations=0 維持 |
| `.importlinter` 影響 | 無（工具/測試不在 8 條 contract 約束範圍） |
| checkpoint additive | 無 |

### 2.2 方案選擇依據（為何 A 非 B，Rule 2/3）

- goal_synthesis 僅 **187 行 < plugin_entry 250**，無 LOC 拆 package 理由；方案 B（拆 `goal_synthesis/` 目錄）需動 wiring import、blast radius 大，屬過度設計。
- W1 計畫中 **coordinator 已採「單檔精準」** `coordinator.py`（[SD09:359](../../AutoClaude/docs/05_development/SD09_Execution_Guide.md#L359)）為先例——單檔目標非異類。
- `is_file()` 分支對既有目錄模組（token_guard / coordinator）**零行為變更**（仍走 rglob 目錄分支），僅對單檔新增能力 → 零退化。

### 2.3 誠實 scope 邊界（Rule 12）

- **本輪不啟動 W1、不跑 mutmut、不偽造 nightly**：ci.yml dormant job 的 `--paths-to-mutate`/`--tests-dir` 僅修正為**實際存在**的單檔/單測試（可 `ls` 驗證），實際 mutmut 執行與 kill_rate 驗證屬 W1 執行期（06-26 G0 後）。
- 修復對齊 W-35-1 既有契約測試（`test_mutation_multi_module_lock.py` 以 `source_path` mock 注入，本輪改動不影響其 4 case）。

---

## 3. 階段三：實作與雙重驗證

- 實作：改 3 檔 + 新增 3 測試 case。
- 單元驗證：`pytest tests/tools/test_mutation_baseline_lock.py` → **52 passed**（49 + 3 新）；含 W-35-1 契約測試 `tests/contract/test_mutation_multi_module_lock.py` 合跑 **56 passed**。
- **突變實證（Rule 9，in-memory 還原禁 git checkout，DEF-32-001）**：
  - **M1**：`compute_source_sha256` 的 `is_file()` 分支停用（`if False`）→ 單檔落入目錄 rglob 回空 → 3 個新 case 全 FAILED（`single_file_resolves_not_unknown` / `single_file_distinguishes_content` / `module_paths_goal_synthesis_points_to_existing_file`，stderr `'unknown' = compute_source_sha256(goal_synthesis_plugin.py)`）。
  - **M2**：`_MODULE_PATHS["goal_synthesis"]` 退回不存在目錄 → 回歸鎖 case `module_paths_goal_synthesis_points_to_existing_file` 精準 FAILED（其餘 51 passed）。
  - 還原後 56 passed，`git diff` 複核**無 M1/M2 突變殘留**（`grep -i "MUTATION:"` 零命中）。

---

## 4. 階段四：CI 平價收斂（零退化矩陣）

| 檢查 | 命令 | 通過條件（floor=3218） | 實測 |
|------|------|----------------------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3218 / 0 failed | **3221 / 122 / 0**（+3）✅ |
| 架構契約 | `lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（total=18506≤20438）✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | OK / 對齊 ✅ |
| YAML 合法性 | `yaml.safe_load(ci.yml)` | 可解析 | ci.yml YAML OK ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 | 本輪**零碰**（純 AutoClaude C 軌，無框架變更），引上輪 v0.01:1478 / v0.14:1593 全綠 ✅ |
| DAL 等價 | equivalence | 三後端等價 | 未改 DAL，不受影響 ✅ |
| 五軌 TLC | — | — | 無 FSM/*.tla 變更，不觸發 ✅ |

---

## 5. 缺陷處置（DEF-35-001 → fixed@improving_36）

- **DEF-35-001**（P2，routed W1）→ **fixed@improving_36**：方案 A 落地（單檔 source_sha256 + `_MODULE_PATHS` 單檔指向 + ci.yml/計畫路徑同步）。詳見 Defect_Log 證據欄。
- **本輪無新增框架程式缺陷、零 Copy-on-Evolve（無 v0.15）**。
- **未推進（維持原狀態，誠實標示非本輪 scope）**：DEF-32-002（routed 未來輪，A 軌刻意 scope）、DEF-19-001（routed，catch 4/39，B 軌框架側）、DEF-01-007（open，cc-switch 環境缺裝，本輪不涉多後端）、DEF-01-009（open watch，本輪零碰 sdd_governance_plugin、violations=0）、DEF-17-001（routed，遙測，B 軌框架側）。

---

## 6. RTM（需求可追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 |
|------|------|------|------|
| DEF-35-001 修復：goal_synthesis 單檔 source_sha256 可解析 | §2.1 方案 A | `compute_source_sha256` is_file 分支 + `_MODULE_PATHS` 單檔 | 3 新 case + M1/M2 突變實證 |
| W1 dormant job/計畫路徑指向實際存在目標 | §2.1 改檔 2/3 | ci.yml:374-375 + SD09 T1-B3:322/G1:335 | YAML OK + `ls` 驗證單檔/單測試存在 + grep 命中=1 |
| 既有目錄模組零行為變更 | §2.2 | is_file 僅新增分支 | 既有 49 case 全綠持平 |
| 零退化 | §4 矩陣 | — | 3221/122/0、lint 8/0、LOC 0、snapshot OK |
| 誠實 scope（不啟 W1/不跑 mutmut/不偽造 nightly） | §2.3 | 僅修正存在性路徑 | mutmut 執行驗證明標 W1 執行期 |

---

## 7. 結案

- W-36-1 交付完成：DEF-35-001 修復（方案 A），零退化、56 case 全綠 + M1/M2 突變實證。
- DEF-35-001 → **fixed@improving_36**（W1 啟動前必修已解，GS mutation 可鎖定/可 mutate）。
- **下一份 `AutoSDD_improving_37`（按需）**：建議＝06-26 G0 開啟後的 W1 正式執行輪（GS pilot 兩週 nightly + Report，#1 unique sha 由 W1 合法改源碼自然解）。
- 審計證據見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_36.md`。
</content>
</invoke>
