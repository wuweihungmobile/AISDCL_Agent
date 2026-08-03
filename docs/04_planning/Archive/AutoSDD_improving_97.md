# AutoSDD_improving_97 — C 軌/infra：copy_on_evolve.sh 建版後自動重生 FRAMEWORK_STATUS.md（DEF-96-001 修 + 帳本補正）

> **本輪柱別**：**C 軌（指揮官自我精進 / 共享 infra）** 單柱聚焦——修 AISDLC_SDD 共享 CI infra 腳本 `copy_on_evolve.sh`。下一份：`AutoSDD_improving_98.md`。
> **驅動器**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`（整合迭代軌道①）。
> **日期**：2026-06-30　**掌舵者裁定本輪 W 項**：DEF-96-001 修 + 缺陷帳本補正（AskUserQuestion 裁「DEF-96-001 修 + 帳本補正（C軌/infra，建議）」）。
> **版本演化**：**無**——修改落在 `AISDLC_SDD/scripts/`（versioned 目錄外＝共享 CI infra，**免 Copy-on-Evolve**，同 ci-gate.sh / conftest.py / DEF-03-001/05-001 先例）。本輪不開新框架版本（LATEST 維持 v0.29）。

---

## §1　本輪輸入（自上輪繼承）

### 1.1 improving_96 RTM / 實作順序遺留
- improving_96（commit c6c0550、tag v2026.06.30-47）已結案：DEF-95-002 從 routed → fixed@v0.29（PRD→playbook 橋接 backend-robust 化、bridge e2e pty 5/5）。
- **本輪自上輪繼承之缺陷**：improving_96 行進中自爆並自修了 **DEF-96-001（P2，流程/infra）**：`copy_on_evolve.sh` 自動同步 skill 戳記/鏡像/.gitignore，但**不重生 `FRAMEWORK_STATUS.md`** → 建 v0.29 後首跑 ci-gate 因「框架版本/計數 SSOT 新鮮度 lint」報 stale；當時以手動 `framework_status_snapshot.py --write` 重生後才取真實 exit 0，並把「補 copy_on_evolve.sh 後步驟重生 framework_status」**routed improving_97**。

### 1.2 缺陷帳本 open/routed（階段一複驗結果，見 §2）
| 缺陷 | 嚴重度 | 狀態 | 本輪處置 |
|------|--------|------|---------|
| **DEF-96-001** | P2 | routed improving_97（且僅記於 improving_96 收尾敘述、**未補進缺陷總表正式列**＝帳本誠實性缺口） | **本輪修復（W-97-1）+ 帳本補正（W-97-2）** |
| DEF-19-001 | P3 | routed（improving_40 結構天花板、實質 closed） | 非本輪 scope，狀態不變 |
| DEF-62-001 | P3 | open（routed）（auto_recovery call-site 註解「預設 OFF」doc-lag） | 非本輪 scope（他域文件債），狀態不變 |
| DEF-01-007 | P3 | open（cc-switch CLI 變體環境缺裝） | 非本輪 scope（本輪零涉多後端），狀態不變 |
| DEF-01-009 | P3 | open watch（sdd_governance_plugin LOC watch） | 非本輪 scope（本輪零擴充該 plugin），維持 open watch |
| SD_09 W1 source-sha 觀察期 | — | 已到期、待 C 軌 W1 | 非本輪（掌舵者未選） |

### 1.3 上輪 QA 複審「延後/下輪」條目
- improving_96 結案留 4 候選：DEF-96-001 修、bridge workflow 補 Archy SOP、SD_09 W1 觀察期、DEF-19-001。本輪掌舵者選 **DEF-96-001 修 + 帳本補正**；其餘留候選帳本，未動。

---

## §2　階段一：現況重偵察（Zero-Trust Re-Audit 實測）

> Parent 親跑實測（2026-06-30），**硬閘通過**（全綠且 ≥ 上輪基線）。

| 檢查 | 命令 | 實測 | 結論 |
|------|------|------|------|
| AutoClaude 全套 pytest | `python -m pytest tests/ -q`（AutoClaude/） | **3607 passed / 0 failed / 122 skipped** | ✅ ＝上輪基線 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **0 violations**（19947 / cap 20438） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | OK | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | 真實 **exit 0**；雙軌 v0.01:1478 + v0.29:1665 + scripts/tests:129；FRAMEWORK_STATUS.md **新鮮**（improving_96 手修後保持）；FF-1~17 + 11 lint 全綠；arch_fitness 僅 advisory（FF-16 GAP，不阻擋） | ✅ |

**本輪零退化 floor（禁寫死，取本表實測）**：AutoClaude pytest **≥ 3607 passed / 0 failed**；lint-imports 8 kept；LOC 0；AISDLC_SDD ci-gate exit 0（雙軌、scripts/tests 隨新測試只增不減）。

### 2.1 DEF-96-001 根因定位（階段一深偵察，已開檔複核 `scripts/copy_on_evolve.sh`）
- `copy_on_evolve.sh` 建版後**僅有兩個自動同步 block**：
  - L73-97（DEF-58-002）：`skill_header_sync.py --write` + `sync_exposed_skills.py --write`（戳記 + 父層鏡像）。
  - L99-124（DEF-59-001）：自動補新版 `.gitignore` runtime 產物排除 block。
- **缺第三個**：`framework_status_snapshot.py --write` 重生 `FRAMEWORK_STATUS.md`。
- 根因鏈：`framework_status_snapshot.render()`（`framework_status_snapshot.py:116-156`）以 `latest_version(discover_frozen_versions(...))` 算「最新演化版」版本號與各類資產計數；**新版一建立，LATEST 即改變** → 既有 `FRAMEWORK_STATUS.md` 的「最新演化版」段 stale → ci-gate 的「框架版本/計數 SSOT 新鮮度 lint」（`framework_status_snapshot.py --check`，`:182-188`）報紅。
- **同根因家族**：與 DEF-58-002（戳記）、DEF-59-001（.gitignore）完全同型——皆為「Copy-on-Evolve 後須同步某 SSOT，但靠人工後步驟＝必然遺忘」。improving_96 建 v0.29 即實證踩到（首跑 ci-gate stale）。

### 2.2 帳本誠實性缺口（W-97-2 標的）
- `grep "DEF-96-001" docs/06_quality/AutoSDD_Defect_Log.md` 僅命中 L708（improving_96 收尾敘述段），**缺陷總表（L40 起）無 DEF-96-001 正式列**。違反帳本「發現即記、格式化入表」紀律 → 本輪補正。

---

## §3　階段二：本輪增量設計

### 3.1 設計主張（一句話）
**把 improving_96 的人工後步驟「`framework_status_snapshot.py --write` 重生 SSOT」釘進 `copy_on_evolve.sh` 建版腳本本身**，成為第三個自動同步 block——與既有 DEF-58-002/59-001 兩 block 完全對稱（「人去記得改」從流程消失）。**零新增 evaluator/外呼/狀態機/形式化模型**。

### 3.2 W 項（2 項）

#### W-97-1：`copy_on_evolve.sh` 補建版後自動重生 FRAMEWORK_STATUS.md（AISDLC_SDD 共享 infra，可直接改）
- **介面 delta**：在 DEF-59-001 .gitignore block（L124）之後，新增第三個 block：
  ```bash
  # ── DEF-96-001（P2，DEF-58-002/59-001 同家族）：建版後自動重生 FRAMEWORK_STATUS.md SSOT ──
  if [ -f "${_SCRIPT_DIR}/framework_status_snapshot.py" ]; then
    echo "==> 重生框架版本/計數 SSOT（framework_status_snapshot --write）"
    "${_PY}" "${_SCRIPT_DIR}/framework_status_snapshot.py" --write --repo-root "${_BASE}"
    echo "✅ FRAMEWORK_STATUS.md 已隨建版自動重生（DEF-96-001：免人工後步驟，杜絕 SSOT stale 帶紅入庫）"
  else
    echo "⚠️ 同層無 framework_status_snapshot.py（隔離環境）；略過 SSOT 重生" >&2
  fi
  ```
- **`_PY` 上提（必要修正）**：`_PY="${PYTHON:-python}"` 目前定義在 DEF-58-002 block 內（L89），其餘 block 無法引用。`set -u` 下若該 block guard 不過則 `_PY` 未定義 → 新 block 引用即 error。**上提 `_PY` 至 `_BASE` 定義之後（L86 區）成頂層單一定義**，三個 Python-invoking 行為共用（移除 DEF-58-002 block 內重複定義）。對齊既有 `${PYTHON:-python}` 可覆寫慣例（測試可注入）。
- **idempotent / fail-loud**：`--write` 依磁碟現況重生，重跑安全；`set -e` ⇒ 失敗即非零中止，不容假綠。
- **隔離 harness guard**：與既有兩 block 同款 `[ -f ... ]` 存在性 guard——僅複製本腳本的隔離環境優雅略過並 warn（既有 helper 測試不破）；production `scripts/` 恆具 sibling 故必跑。`framework_status_snapshot.py` import `rfc_lifecycle_lint`（`framework_status_snapshot.py:31`），測試 harness 須一併佈署（已在 `_SYNC_SCRIPTS`）。
- **依賴**：純 shell + 既有 `framework_status_snapshot.py`（無新 Python 模組、無新外部依賴）。
- **回歸鎖測試**：`scripts/tests/test_copy_on_evolve.py` 新增 `test_auto_regens_framework_status_on_evolve_def_96_001`——建 v0.02 後斷言 `BASE/FRAMEWORK_STATUS.md` 存在且含「最新演化版」`v0.02`；並把 `framework_status_snapshot.py` 加入 `_SYNC_SCRIPTS`（harness 佈署）。移除新 block → 測試立即轉紅。

#### W-97-2：缺陷帳本補正（DEF-96-001 補進總表正式列）
- **檔案**：`docs/06_quality/AutoSDD_Defect_Log.md` 缺陷總表新增 DEF-96-001 正式列（發現日期 2026-06-30、情境＝improving_96 建 v0.29 後首跑 ci-gate、現象與證據＝SSOT stale lint 報紅 + copy_on_evolve.sh 缺第三 block、嚴重度 P2、分流＝框架 infra RFC/腳本硬化、狀態＝本輪 fixed@improving_97 W-97-1 + 回歸鎖證據）。
- 純文件補正，無程式影響。

### 3.3 介面 delta / LOC / importlinter 影響
| 項目 | delta | LOC tier | importlinter |
|------|-------|----------|--------------|
| `scripts/copy_on_evolve.sh` | 補一個自動同步 block + 上提 `_PY`（~10 行 shell） | 非 .py（AISDLC_SDD shared infra；非 AutoClaude LOC scan 範圍） | 零影響（AutoClaude `.importlinter` 不涵蓋 AISDLC_SDD scripts） |
| `scripts/tests/test_copy_on_evolve.py` | 新增 1 意圖鎖測試 + `_SYNC_SCRIPTS` 加 1 項 | 測試非 LOC scan 範圍 | — |
| `docs/06_quality/AutoSDD_Defect_Log.md` | 補 DEF-96-001 正式列 | 非 .py | — |
- **零碰**：AutoClaude（ports/、plugins/、core/、infra/、playbook_runner.py、PlaybookCheckpoint、DAL 三後端）全未觸；AISDLC_SDD 任一 `AISDLC_SDD_v0.0X/` 凍結/演化版本目錄全未觸；任何 `*.tla`/FSM/`_HAPPY_PATH` 全未觸。
- **Snapshot**：AutoClaude snapshot 不動（本輪零碰 AutoClaude port/plugin）。
- **Copy-on-Evolve**：不觸發（修 `scripts/` 共享 infra，免 Copy-on-Evolve）。

### 3.4 RTM 需求列（實測欄階段四回填）
| RTM | 需求 | 驗證 |
|-----|------|------|
| RTM-97-1 | copy_on_evolve.sh 建新版後自動跑 `framework_status_snapshot.py --write` 重生 `BASE/FRAMEWORK_STATUS.md`，內容反映新版為 LATEST | `test_copy_on_evolve.py::test_auto_regens_framework_status_on_evolve_def_96_001` |
| RTM-97-2 | 第三 block idempotent + fail-loud（`set -e`）+ 隔離環境優雅略過（不破既有 helper 測試） | 既有 7 helper 測試 + 兩 auto-sync 測試持續綠；新測試 |
| RTM-97-3 | `_PY` 上提後三個 Python-invoking block 共用、行為不變（戳記/鏡像/.gitignore 同步仍正確） | `test_auto_syncs_skill_stamps_*` + `test_auto_appends_gitignore_block_*` 持續綠 |
| RTM-97-4 | DEF-96-001 補進缺陷總表正式列、狀態 fixed@improving_97 附證據 | Defect_Log 審閱 + grep 命中總表列 |
| RTM-97-5 | ci-gate 雙軌仍真實 exit 0，scripts/tests 計數 +新測試、無退化 | 階段四 ci-gate 真跑 |

---

## §4　階段三：實作與雙重驗證（已完成）

- **W-97-1**：`scripts/copy_on_evolve.sh` 補第三個建版後自動同步 block（`framework_status_snapshot.py --write --repo-root "${_BASE}"`，L126-143），與 DEF-58-002/59-001 兩 block 對稱（存在性 guard + `set -e` fail-loud + idempotent）；`_PY="${PYTHON:-python}"` 上提至頂層（`_BASE` 後）供三 block 共用，移除 DEF-58-002 block 內重複定義（避 `set -u` 下未定義）。
- **W-97-2**：`docs/06_quality/AutoSDD_Defect_Log.md` 缺陷總表補 DEF-96-001 正式列（fixed@improving_97 W-97-1，附根因/分流/證據）。
- **回歸鎖**：`scripts/tests/test_copy_on_evolve.py` 新增 `test_auto_regens_framework_status_on_evolve_def_96_001`（建 v0.02 後斷言 `BASE/FRAMEWORK_STATUS.md` 存在且認列 v0.02 為 LATEST）+ `_SYNC_SCRIPTS` 加 `framework_status_snapshot.py`（harness 佈署）→ **`test_copy_on_evolve.py` 11 passed**（原 10 + 新 1）。
- **雙重驗證（突變）**：暫以 `: MUTATION_TEST_DISABLED` 停用第三 block 重生行 → 新測試立即轉紅（`FRAMEWORK_STATUS.md` 未生成、`is_file()=False`）；以 Edit 還原（非 `git checkout`，遵守突變還原紀律）→ 11 passed 復綠；grep 確認零突變殘留。
- **安全**：未新增 `SDD_CONTRACT_VIOLATION` / `ToolInvocationPort` 路徑；新 block 呼叫為腳本內固定參數（`_BASE`＝`dirname "$TO"`），無使用者輸入插值、無 shell 注入面。
- **零碰**：AutoClaude 全部源碼/測試、任一 `AISDLC_SDD_v0.0X/` 版本目錄、任何 `*.tla`/FSM/`_HAPPY_PATH` 全未觸（git diff 僅 `scripts/copy_on_evolve.sh` + `scripts/tests/test_copy_on_evolve.py` + 根 `docs/`）。

---

## §5　階段四：CI 平價收斂 — 零退化驗證矩陣（實測欄階段四回填）

| 檢查 | 命令 | 通過條件（floor 取 §2 實測） | 實測 |
|------|------|------------------------------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3607 passed / 0 failed | ✅ **3607 passed / 0 failed / 122 skipped**（複跑確認，零碰 AutoClaude） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | ✅ **0 violations**（19947 / cap 20438，不變） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 雙軌（v0.01 + v0.29）pytest not-chaos 全綠 + arch_fitness exit<2 + 11 lint 全過 | ✅ **真實 exit 0**；雙軌 v0.01:1478 + v0.29:1665 + **scripts/tests:130**（原 129 +1 新測試）；FRAMEWORK_STATUS.md 新鮮；FF-1~17 + 11 lint 全綠 |
| DAL 等價 | equivalence job | 本輪**無新 DAL/checkpoint 改動**→ N/A 第二型 | ✅ **N/A 第二型**（既有 `tests/equivalence/` 隨 3607 全套通過、零 DAL/checkpoint 改動） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A 第一型（條件未觸發、未跑）** | ✅ **N/A 第一型**（鐵證：git diff 僅 `scripts/copy_on_evolve.sh` + `scripts/tests/test_copy_on_evolve.py` + 根 `docs/`，零碰任何 `*.tla`/`.cfg`/`_HAPPY_PATH`/FSM） |
| copy_on_evolve 回歸 | `pytest scripts/tests/test_copy_on_evolve.py -q` | 既有 10 + 新增 1 全綠；新測試移除 block 即紅（突變驗證） | ✅ **11 passed**；突變（`: MUTATION_TEST_DISABLED`）→ 新測試轉紅、Edit 還原復綠 |

---

## §6　缺陷帳本本輪處置
- **DEF-96-001**：本輪修復（W-97-1）；補進缺陷總表正式列（W-97-2）；回歸鎖測試通過後改 `fixed@improving_97`。
- 本輪行進中新發現缺陷一律即記 `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-97-xxx）。

---

## §7　Copy-on-Evolve / 版本演化
- **本輪無版本演化**：修改落 `AISDLC_SDD/scripts/`（共享 CI infra，免 Copy-on-Evolve）。LATEST 維持 v0.29、凍結基線 v0.01 不動。
- TLC：N/A 第一型（零碰形式化模型，git diff 證）。

---

## §8　誠實性標記
- 本檔於**階段二先落地**（§1/§2/§3 規格先行）；§4/§5 實測欄、§4 雙重驗證結果於階段三/四回填。
- 矩陣 N/A 將於階段四精確區分兩型（DAL＝既有隨全套已過；TLC＝條件未觸發未跑 + git diff 證）。
- 本輪柱別＝**C 軌/infra**（修 AISDLC_SDD 共享 CI 腳本），非 B 軌 Copy-on-Evolve 版本演化（scripts/ 免演化）。
