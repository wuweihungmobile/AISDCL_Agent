# AutoSDD improving_43 — B 軌·Copy-on-Evolve `.gitignore` 覆蓋自動偵測（DEF-37-001 結構修）

> 軌道① 整合迭代第 43 輪。**本輪柱別＝B 軌（手腳 AISLDC_SDD dogfooding，走 shared infra）**。
> 掌舵者定向（2026-06-21 AskUserQuestion）：**Q1＝B 軌·DEF-37-001 結構修**、**Q2＝≤3 W 項**。
> 下一份：improving_44（候選見 §6）。

---

## 1. 本輪輸入（自上輪繼承）

- **上輪（improving_42）**：A 軌整合橋接 DEF-42-002 But 續行斷言保真度修復，主 commit bf3f541、tag v2026.06.21-42。已結案無未完成 W 項。
- **缺陷帳本 open/routed 盤點**（`docs/06_quality/AutoSDD_Defect_Log.md`）：
  - **DEF-37-001（P3, routed）**＝本輪標的：Copy-on-Evolve 新版 `.gitignore` block 缺漏**無自動偵測**，每輪須人工手補。
  - DEF-01-007（open）：cc-switch CLI 環境工具缺裝，非倉內程式可修，不阻擋。
  - DEF-01-009（open watch）：sdd_governance_plugin.py LOC watch，本輪零觸碰該檔不觸發。
  - DEF-42-001（routed）：test_file_lock Windows flaky，本輪不碰框架本體（B 軌走 shared infra），維持 routed。
  - DEF-42-003（wontfix by-design）：quoted-wins-over-negative-status，需掌舵者拍板推翻，本輪不動。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）— 🟢 HARD GATE PASS

Explore agent 實測（2026-06-21，背景審計 a01d6a3a）：

| 項目 | 結果 | 實測數字 |
|------|------|---------|
| (a) AutoClaude pytest | **PASS** | **3235 passed / 122 skipped / 0 failed**（floor 3235 吻合，零退化） |
| (b) lint-imports | PASS | 8 kept / 0 broken |
| (c) LOC 預算 | PASS | violations=0（total=18522 ≤ cap=20438） |
| (d) snapshot | PASS | FRESH |
| (e) AISDLC_SDD ci-gate | PASS | exit 0；v0.01:1478 / v0.17:1611 / scripts/tests:44 |
| (e) DEF-42-001 隔離 | PASS | 3/3 綠（環境 flaky 非回歸） |
| (f) 上輪構件 | PASS | `_then_assertions` :319 含 `("And","But")`；`TestButContinuationFidelity` 11 cases |

- **本輪 floor 基線（零退化門檻）**：AutoClaude **3235/122/0**、lint 8/0、LOC 0、ci-gate exit 0（v0.01:1478 / v0.17:1611 / scripts/tests:44）、框架最新 **v0.17**。
- **zero-trust 主 agent 糾偏**：審計兵把 DEF-37-001 誤判「fixed（v0.17 已有 block）」——**誤讀缺陷本質**。DEF-37-001 核心＝「**無自動偵測機制**」，v0.17 block 存在純粹因上輪 improving_39 建版時手動補；目前無任何 lint 在缺漏時警告。實際狀態＝**routed**，正是本輪標的。糾正後維持 routed 並由本輪結構修。

## 3. 階段二：本輪增量設計（B 軌 Brownfield SOP，shared infra）

### 3.1 標的與分界
- DEF-37-001 分流去向＝「框架程式/hook 缺陷 → 於 `scripts/rfc_lifecycle_lint.py` 或 `ci-gate.sh` 增『偵測磁碟最新 v0.0X 是否在 .gitignore 有對應 build/reports 排除 block，缺即 warn』（shared infra，免 Copy-on-Evolve）」。
- **設計抉擇（Rule 2 單一職責）**：採**新獨立模組** `scripts/gitignore_coverage_lint.py`，而非併入 `rfc_lifecycle_lint.py`——gitignore 覆蓋 ≠ RFC 生命週期，獨立模組可獨立測試；靠 import 複用 `discover_frozen_versions`/`latest_version`（DRY，不複製版本偵測邏輯）。位於 `AISDLC_SDD/scripts/`（versioned 目錄外，**免 Copy-on-Evolve**，同 cross_version_guard/rfc_lifecycle_lint/copy_on_evolve 家族）。

### 3.2 W 項清單（≤3）

| W 項 | 內容 | 介面 delta | LOC 落點 |
|------|------|-----------|---------|
| **W-43-1** | 新 shared-infra lint 模組 + wire ci-gate | `gitignore_coverage_lint.py`：`gitignore_rule_lines(repo_root)`、`missing_artifact_tokens(repo_root)->(latest,missing)`、`main()`；`RUNTIME_ARTIFACTS=("build/reports","arch-fitness.json","chaos-report.json")`。ci-gate.sh 在 RFC lint 後新增 advisory 段 | 模組 ~110 行（shared infra 不受 AutoClaude LOC 分級）；ci-gate +8 行 |
| **W-43-2** | 意圖鎖測試 + 自動納閘 | `scripts/tests/test_gitignore_coverage_lint.py` 12 case；放 scripts/tests/ 由 ci-gate `python -m pytest scripts/tests/`（DEF-12-001 已修）自動執行 | 測試檔 |
| **W-43-3** | 缺陷帳本回流 | DEF-37-001 routed→**fixed@improving_43** + 證據 | — |

### 3.3 判定演算法（最低誤報）
- 偵測磁碟**最新演化版** `latest_version(discover_frozen_versions(repo_root))`（對齊 ci-gate `sort -V | tail -1`）。
- 對三類 runtime 產物，token = `<latest>/<artifact>`；`.gitignore` 任一**非註解**規則行含該 token 即視為覆蓋。
- **相容兩 idiom**：整樹 `<ver>/build/reports/`（v0.13+）與 negate `<ver>/build/reports/*`（v0.05~v0.12）皆含子串 `<ver>/build/reports` → 命中。
- **過濾 `#` 註解行**：避免 block 註解（如 v0.13 註解提及 `build/reports/`）偽命中。
- **advisory**：缺即 `::warning::`，`main` 永遠 exit 0，**不改 ci-gate 硬閘 exit 語意**（P3 不阻擋，對齊 routed「缺即 warn」）。

### 3.4 對 `.importlinter` 各 contract 影響
- **零影響**：本輪改動全在 `AISDLC_SDD/scripts/`（AISDLC_SDD 子專案 shared infra）與 ci-gate.sh，**零觸碰 AutoClaude 任何模組**。AutoClaude 8 contract 結構不變。

### 3.5 checkpoint additive 欄位需求
- 無。不涉 PlaybookCheckpoint / DAL（純 CI infra read-only）。

### <Architecture_Design_Review>（寫實質 Python 前）
1. **架構純潔性**：shared-infra 純函式 + 薄 main，零業務邏輯入 core，無 God-object；import 複用版本偵測（DRY）。
2. **持久化相容**：N/A（不涉 PlaybookCheckpoint / DAL 三後端）。
3. **安全防護網**：read-only 讀 `.gitignore` + `os.listdir`，無 CONDITIONAL / 指令生成 / 注入面。
4. **對外 I/O 安全**：N/A（無 `ToolInvocationPort` 外呼路徑）。
- read-only 純觀察者：不寫 FSM-STATE、不影響 churn/meta-loop（對齊 rfc_lifecycle_lint）。不碰 `_HAPPY_PATH`/`*.tla`（TLC 不觸發）。

## 4. 階段三：實作與雙重驗證

- **W-43-1**：[gitignore_coverage_lint.py](../../AISDLC_SDD/scripts/gitignore_coverage_lint.py) 建立；[ci-gate.sh](../../AISDLC_SDD/scripts/ci-gate.sh) RFC lint 後新增 advisory 段。
- **W-43-2**：[test_gitignore_coverage_lint.py](../../AISDLC_SDD/scripts/tests/test_gitignore_coverage_lint.py) 12 case（齊備/negate idiom/新版全缺/部分缺/註解不偽命中/只掃最新/無版本/無 gitignore/CLI advisory×3/真實 repo 回歸鎖）。
- **突變驗證**（證非假測試，Rule 9）：
  - M1（RUNTIME_ARTIFACTS 漏 arch-fitness.json）→ **4 cases 紅**（new_version_no_block / partial_block / scans_only_latest / no_gitignore），還原綠。
  - M2（移除 `#` 註解過濾）→ **test_comment_line_not_false_positive 紅**，還原綠。
  - 還原後 12 passed、grep 突變零殘留。
- **端到端**：真實 repo lint→「最新版 v0.17 ... block 齊備」exit 0；模擬最新版 v0.18 缺 block→`::warning::` 精準觸發 + 修復指引、exit 0（advisory）。
- **自動納閘**：scripts/tests/ 44→**56 passed**（+12），由 ci-gate `python -m pytest scripts/tests/` 自動執行（DEF-12-001 已確保被強制）。

## 5. 階段四：CI 平價收斂（零退化驗證矩陣全項）

| 檢查 | 命令 | 通過條件（floor=improving_42 實測） | 本輪結果 |
|------|------|-----------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3235 passed / 0 failed | **3235/122/0**（122.58s）🟢 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 未觸碰 AutoClaude（結構保證） |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | 未觸碰 AutoClaude（結構保證） |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | 未觸碰（結構保證） |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 + 逐軌≥floor | exit 0；v0.01:1478 / v0.17:1611 / scripts/tests:56 🟢 |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（零 `_HAPPY_PATH`/`*.tla` 變更） |

> **結果回填於 §7 收尾註記**（待背景驗證完成）。

## 6. 下一份 improving_44 候選
- C 軌 SD_09 W1（06-26 G0 開後）；或 B 軌 DEF-42-001（test_file_lock flaky，需 Copy-on-Evolve v0.18）；或續 A 軌 SddToPlaybookAdapter 保真度偵察；或 DEF-42-003（需掌舵者推翻 quoted-wins）。

## 7. RTM（需求追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 |
|------|------|------|------|
| DEF-37-001：新版 .gitignore block 缺漏自動偵測 | §3.1-3.3 新獨立 lint 模組 + advisory | W-43-1 gitignore_coverage_lint.py + ci-gate wire | 12 case + M1/M2 突變 + 端到端模擬 v0.18 |
| 相容兩 idiom（整樹/negate）不誤報 | §3.3 子串命中 | RUNTIME_ARTIFACTS 子串比對 | test_negate_idiom_counts_as_covered |
| 註解不偽命中 | §3.3 過濾 `#` 行 | gitignore_rule_lines | test_comment_line_not_false_positive + M2 |
| 只掃最新版（語意版本） | §3.3 latest_version | 複用 rfc_lifecycle_lint | test_scans_only_latest_semantic |
| advisory 不阻擋硬閘 | §3.3 main 永遠 exit 0 | main return 0 | test_main_*_exits_zero + bash -n |
| 自動納閘執行 | §3.2 W-43-2 | scripts/tests/ + ci-gate | scripts/tests 56 passed |
| 真實 repo 不誤報 + 未來回歸保護 | §3.3 | — | test_real_repo_latest_covered |

## 8. §8 結案證據契約（closure-evidence，反幻覺機械閘門 DEF-20-001）

```yaml
closure-evidence:
  base_sha: ccfaf5e  # 本輪所建之上的 HEAD（improving_42 回填收尾後）
  claimed_commits:
    - <主 commit sha：回填時填入>
  claimed_tag: v2026.06.22-43
  pytest:
    autoclaude: "3235 passed / 122 skipped / 0 failed（floor 3235，零退化；本輪零觸碰 AutoClaude）"
    scripts_tests: "56 passed（44 +12 新 gitignore lint case）"
    gitignore_lint_focused: "12 passed（test_gitignore_coverage_lint.py）"
  lint_imports: "8 kept / 0 broken（未觸碰 AutoClaude，結構保證）"
  loc: "violations=0（未觸碰 AutoClaude）"
  snapshot: "FRESH（未觸碰）"
  ci_gate: "exit 0；v0.01:1478 / v0.17:1611 / scripts/tests:56；新增 .gitignore 覆蓋 lint advisory 段自證 v0.17 齊備"
  tlc: "N/A — 零 _HAPPY_PATH/*.tla 變更"
  copy_on_evolve: "N/A — B 軌 shared infra（scripts/，versioned 目錄外，免 Copy-on-Evolve），無 v0.0X 變更"
  mutation_m1: "RUNTIME_ARTIFACTS 漏 arch-fitness.json → 4 case 轉紅；還原 12 綠"
  mutation_m2: "移除 # 註解過濾 → test_comment_line_not_false_positive 轉紅；還原 12 綠"
  zero_trust: "三鏡（Architect/SA-SD/QA）全 PASS，P0=0/P1=0；主樹派發（untracked 新檔，DEF-24-001）"
  discipline_event: "zero-trust 糾偏：階段一審計兵誤判 DEF-37-001『fixed（v0.17 已有 block）』→ 主 agent 糾正缺陷核心＝無自動偵測機制、維持 routed 並本輪結構修"
```

