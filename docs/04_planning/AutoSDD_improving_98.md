# AutoSDD_improving_98 — B 軌/框架演化：Copy-on-Evolve v0.29→v0.30 校正 auto_recovery 滯後註解（DEF-62-001 真修）

> **本輪柱別**：**B 軌（手腳框架自我迭代 / Copy-on-Evolve 版本演化）** 單柱聚焦——修 AISDLC_SDD FSM runtime 凍結本體一行 doc-lag 註解。下一份：`AutoSDD_improving_99.md`。
> **驅動器**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`（整合迭代軌道①）。
> **日期**：2026-06-30　**掌舵者裁定本輪 W 項**：DEF-62-001 真修＝演化 v0.30 校正註解（AskUserQuestion 兩問：①本輪 W 方向＝小缺陷清理 P3 批次；②DEF-62-001 處置＝真修演化 v0.30）。DEF-01-009 維持 open watch、不投機重構。
> **版本演化**：**有**——`AISDLC_SDD_v0.29`（凍結）→ Copy-on-Evolve `AISDLC_SDD_v0.30`，於新版改 `tools/fsm_runtime/fsm_runtime.py:420` 註解；附 `v0.30/EVOLUTION_LOG.md` + `v0.30/releases/CHANGELOG.md`。LATEST 由 `sort -V|tail -1` 自動轉 v0.30。

---

## §1　本輪輸入（自上輪繼承）

### 1.1 improving_97 RTM / 實作順序遺留
- improving_97（commit bc52e88、tag v2026.06.30-48）已結案：DEF-96-001 fixed@improving_97（`copy_on_evolve.sh` 補第三個建版後自動同步 block＝重生 `FRAMEWORK_STATUS.md`，與 DEF-58-002/59-001 對稱）。
- improving_97 結案後一個 nightly-forensic chore（834e211）；本輪開工時工作區僅餘 `.drift_log_history.jsonl`/`.perf_baseline.toml` 兩個取證帳本 nightly 重跑漂移（`passed:true`、perf 亞毫秒雜訊、無退化），照慣例（834e211）以 nightly-forensic 處置。

### 1.2 缺陷帳本 open/routed（階段一複驗結果，見 §2）
| 缺陷 | 嚴重度 | 狀態 | 本輪處置 |
|------|--------|------|---------|
| **DEF-62-001** | P3 | open（routed，跨 improving_62 起多輪）（auto_recovery call-site 註解「預設 OFF」doc-lag） | **本輪真修（W-98-1）**＝Copy-on-Evolve v0.30 校正註解 |
| **DEF-01-009** | P3 | open watch（sdd_governance_plugin LOC watch） | **複驗 + 維持 open watch（W-98-2）**——已自癒（count_loc<250、violations=0）、本輪零擴充該 plugin、不投機拆 package |
| DEF-19-001 | P3 | routed（improving_40 結構天花板、實質 closed） | 非本輪 scope，狀態不變 |
| DEF-01-007 | P3 | open（cc-switch CLI 變體環境缺裝） | 非本輪 scope（本輪零涉多後端），狀態不變 |
| SD_09 W1 source-sha 觀察期 | — | 已到期、待 C 軌 W1 | 非本輪（掌舵者本輪選 P3 清理） |

### 1.3 上輪 QA 複審「延後/下輪」條目
- improving_96/97 結案留候選：bridge workflow 補 Archy SOP（A軌）、SD_09 W1 觀察期（C軌）、P3 清理批次。本輪掌舵者選 **P3 清理批次**，再裁 DEF-62-001 走真修；其餘留候選帳本未動。

---

## §2　階段一：現況重偵察（Zero-Trust Re-Audit 實測）

> 背景 audit agent 全程 Bash 工具實測（2026-06-30），**硬閘通過**（全綠且 ≥ 上輪基線）；parent 複核背景回報無編造。

| 檢查 | 命令 | 實測 | 結論 |
|------|------|------|------|
| AutoClaude 全套 pytest | `python -m pytest tests/ -q`（AutoClaude/） | **3607 passed / 0 failed / 122 skipped**（71.15s） | ✅ ＝上輪基線 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（200 files / 504 deps） | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **0 violations**（19947 / cap 20438；absolute=0 tier=0 special=0） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | OK（Snapshot 區段 + sprint 骨架對齊） | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | 真實 **exit 0**（REAL_CI_GATE_EXIT=0，最後一行「✅ 本機 CI 閘門全數通過」互證）；雙軌 v0.01:1478 + v0.29:1665 + scripts/tests:130；FF-1~17 + 11 lint 全綠；arch_fitness 3 個 advisory warn（FF-5/FF-16）不阻擋、fail=0 | ✅ |

**本輪零退化 floor（禁寫死，取本表實測）**：AutoClaude pytest **≥ 3607 passed / 0 failed**；lint-imports 8 kept；LOC 0；AISDLC_SDD ci-gate exit 0（雙軌；演化後 LATEST 由 v0.29 轉 v0.30，v0.30 計數應與 v0.29 相等＝1665，scripts/tests 不變＝130）。

### 2.1 DEF-62-001 根因與 scope 精確定位（階段一深偵察，已開檔複核 v0.29 `fsm_runtime.py`）
- **唯一滯後行**：`AISDLC_SDD_v0.29/tools/fsm_runtime/fsm_runtime.py:420`
  `# W-15-1 / B-axis L4：flag-gated 有界自動恢復接入。預設 OFF＝行為同 v0.05`
- **已正確（Rule 8 讀後修正 scope，不擴張）**：同檔 L39 檔頭已寫「v0.22（improving_57）：預設 **ON**」、L51-55 `_auto_recovery_enabled()` docstring + `return True # v0.22 預設 ON` 皆正確；L41「→ 還原 v0.05 停機行為」是 opt-out 分支描述（正確）。`grep "預設 OFF"` 全檔僅命中 L420 一行。
- **根因**：auto_recovery 自 v0.22（improving_57）翻預設 ON，但 L420 call-site 註解未隨翻環同步（improving_57 遺留 doc-lag），歷經每次 Copy-on-Evolve 逐字繼承至 v0.06~v0.29 每版。**純註解時間差，零執行語意問題**（`_auto_recovery_enabled()` 實作 unset→True 正確）。
- **同根因家族**：DEF-58-002（戳記）、DEF-59-001（.gitignore）、DEF-96-001（FRAMEWORK_STATUS）的「翻環/建版後 SSOT 同步」家族之文件變體。

### 2.2 DEF-01-009 複驗（W-98-2 標的）
- `AutoClaude/autoclaude/plugins/sdd_governance_plugin.py`：raw 277 行；`check_loc_budget.py` **violations=0**（count_loc 受控指標 < plugin_entry cap 250、已自癒）。本輪 W 項為 AISDLC_SDD 框架側，**零擴充該 plugin** → watch 不觸發。正確處置＝**維持 open watch**；主動拆 package＝無功能驅動的投機重構（違反工程紀律 Rule 2/3），不做。

---

## §3　階段二：本輪增量設計

### 3.1 設計主張（一句話）
**用既有 `scripts/copy_on_evolve.sh`（improving_97 剛硬化）把 v0.29 演化為 v0.30，於新版就地校正 L420 一行滯後註解；舊版 v0.29 凍結唯讀不動。** 零程式語意變更、零 evaluator/外呼/狀態機/形式化模型變更——本輪同時端到端 dogfood improving_97 的「建版後自動重生 FRAMEWORK_STATUS.md」。

### 3.2 W 項（2 項）

#### W-98-1：Copy-on-Evolve v0.29→v0.30 + 校正 L420 滯後註解（DEF-62-001 真修）
- **建版**：`bash scripts/copy_on_evolve.sh AISDLC_SDD/AISDLC_SDD_v0.29 AISDLC_SDD/AISDLC_SDD_v0.30`
  （git archive 純 tracked 匯出 863 檔；自動同步戳記/鏡像 + .gitignore block + **FRAMEWORK_STATUS.md 重生**——三 block 全跑＝improving_97 成果首次跨版實證）。
- **註解 delta**（僅 v0.30，新版非凍結可改）：`tools/fsm_runtime/fsm_runtime.py:420`
  - 前：`# W-15-1 / B-axis L4：flag-gated 有界自動恢復接入。預設 OFF＝行為同 v0.05`
  - 後：`# W-15-1 / B-axis L4：flag-gated 有界自動恢復接入。v0.22 起預設 ON（顯式 opt-out=0`
    `# 才還原 v0.05 停在 ESCALATION 等人）。ON 時：對「可恢復 gate」自動嘗試既有`
  - 與 L39/L51 極性一致；下方 L421「（停在 ESCALATION 等人）。ON 時：…」併入改寫，語意保全、行數對齊（淨增 0~1 行註解）。
- **EVOLUTION_LOG / CHANGELOG**：`v0.30/EVOLUTION_LOG.md` 補 v0.30 條目（DEF-62-001 doc-lag 校正、零行為變更）；`v0.30/releases/CHANGELOG.md` 同步補一筆。
- **依賴**：純既有腳本 + 一行註解編輯，無新 Python 模組、無新依賴、無 `*.tla`/`_HAPPY_PATH`/`.cfg` 觸碰。

#### W-98-2：DEF-01-009 複驗 + 維持 open watch（無程式變更）
- 階段一已複驗（§2.2）：violations=0、本輪零擴充。帳本更新複驗註記、維持 open watch。純文件。

### 3.3 介面 delta / LOC / importlinter 影響
| 項目 | delta | LOC tier | importlinter |
|------|-------|----------|--------------|
| 新增 `AISDLC_SDD_v0.30/`（git archive v0.29） | +863 tracked 檔（v0.29 逐字 + 1 行註解差 + EVOLUTION_LOG/CHANGELOG 補筆 + 自動重生 FRAMEWORK_STATUS/戳記/鏡像） | 非 AutoClaude LOC scan 範圍（AISDLC_SDD 版本目錄） | 零影響（AutoClaude `.importlinter` 不涵蓋 AISDLC_SDD） |
| `…v0.30/tools/fsm_runtime/fsm_runtime.py` | 1 行註解極性校正（純註解） | 非 AutoClaude scan | — |
| `docs/06_quality/AutoSDD_Defect_Log.md` | DEF-62-001 → fixed@improving_98 + DEF-01-009 複驗註記 | 非 .py | — |
- **零碰**：AutoClaude（ports/、plugins/、core/、infra/、playbook_runner.py、PlaybookCheckpoint、DAL 三後端）全未觸；v0.29 及更早凍結版本目錄全未觸（唯讀）；任何 `*.tla`/FSM `_HAPPY_PATH`/`.cfg` 全未觸（純註解）。
- **Snapshot**：AutoClaude snapshot 不動（零碰 AutoClaude）。
- **Copy-on-Evolve**：**觸發**（本輪本體＝框架版本演化）；遵守舊版凍結、新版修改、附 EVOLUTION_LOG/CHANGELOG。

### 3.4 <Architecture_Design_Review>（寫實質變更前自我驗證）
1. **架構純潔性**：無新 God-object、無 Thin Facade 破壞——本輪不碰 AutoClaude 架構，僅 AISDLC_SDD 版本演化 + 一行註解。
2. **持久化相容**：無新狀態、不碰 PlaybookCheckpoint、DAL 三後端零影響（本輪零碰 AutoClaude DAL）。
3. **安全防護網**：未新增「從文件生成指令」路徑；copy_on_evolve 第三 block 呼叫為固定參數（improving_97 已審無注入面），本輪不改該腳本。
4. **對外 I/O 安全**：本輪**未新增** `ToolInvocationPort` 外呼路徑——無 allowlist/SSRF 考量。
5. **形式化同構**：純註解、零碰 `*.tla`/`_HAPPY_PATH`/`.cfg`/FSM Terminals → 五軌 TLC 不變式不受影響（N/A 第一型，git diff 為證）。

### 3.5 RTM 需求列（實測欄階段四回填）
| RTM | 需求 | 驗證 |
|-----|------|------|
| RTM-98-1 | `copy_on_evolve.sh` 成功建 `AISDLC_SDD_v0.30`（863 tracked 檔結構性匯出、無 runtime bloat） | `git add -A -n` would-add 清單審查 + 檔數核對 |
| RTM-98-2 | v0.30 三個建版後自動同步 block 全跑（戳記/鏡像、.gitignore block、FRAMEWORK_STATUS 重生）＝improving_97 跨版實證 | copy_on_evolve 輸出 3 個 ✅；FRAMEWORK_STATUS 認列 v0.30 為 LATEST |
| RTM-98-3 | v0.30 `fsm_runtime.py:420` 註解校正為「v0.22 預設 ON」極性、與 L39/L51 一致；v0.29 凍結本體不動 | grep v0.30 該行 + git diff 確認 v0.29 零變更 |
| RTM-98-4 | DEF-62-001 → fixed@improving_98（附 v0.30 證據）；DEF-01-009 複驗維持 open watch | Defect_Log 審閱 + grep |
| RTM-98-5 | ci-gate 雙軌仍真實 exit 0；LATEST 轉 v0.30、v0.30 計數＝v0.29（1665）、scripts/tests=130 不變、零退化 | 階段四 ci-gate 真跑 |
| RTM-98-6 | AutoClaude 零退化（≥3607 passed / lint 8 / LOC 0 / snapshot OK） | 階段四真跑 |

---

## §4　階段三：實作與雙重驗證（已完成）

- **W-98-1 建版**：`bash scripts/copy_on_evolve.sh AISDLC_SDD/AISDLC_SDD_v0.29 AISDLC_SDD/AISDLC_SDD_v0.30` → COPY_EXIT=0；git archive 純 tracked 匯出 **863 檔**；**三個建版後自動同步 block 全跑**（戳記 45 檔 + 父層 skills 鏡像 59 檔 + `.gitignore` 補 v0.30 block + **FRAMEWORK_STATUS.md 重生**＝improving_97/DEF-96-001 修復首次跨版實證，RTM-98-2 ✅）。
- **W-98-1 註解校正**：`AISDLC_SDD_v0.30/tools/fsm_runtime/fsm_runtime.py:420-421` 由「預設 OFF＝行為同 v0.05（停在 ESCALATION 等人）」改「v0.22 起預設 ON（顯式 opt-out=0 才還原 v0.05 停在 ESCALATION 等人）」，與 L39/L51 極性一致；行數不變。
- **EVOLUTION_LOG / CHANGELOG**：`v0.30/EVOLUTION_LOG.md` 補 v0.29→v0.30 條目 + 標頭凍結範圍/本目錄版號更新；`v0.30/releases/CHANGELOG.md` 補 [v0.30] 條目 + 最後更新日。
- **W-98-2**：DEF-01-009 階段一已複驗（§2.2，violations=0、本輪零擴充），維持 open watch、零程式變更。
- **雙重驗證**（純註解，行為突變不適用，改以差異/凍結/潔淨度三證）：
  1. **v0.29 凍結零變更**：`git status AISDLC_SDD/AISDLC_SDD_v0.29/` 空 ✅（凍結本體未動，符 Copy-on-Evolve）。
  2. **v0.30 僅差該註解**：`diff v0.29 v0.30 fsm_runtime.py` 僅 L420-421 兩行註解差異、無其他差異 ✅；v0.30 全檔 `grep "預設 OFF"` 零殘留 ✅。
  3. **入庫潔淨度**（DEF-11-002 紀律，全量 `git add -A -n` 而非僅數 .pyc）：would-add 913＝v0.30 863（＝git archive 數）+ 父層 skills 鏡像 45 + `.gitignore`/`FRAMEWORK_STATUS.md`/計畫書/2 nightly 取證；**零 runtime/stale 產物混入**（`build/reports/`、`arch-fitness.json`、`chaos-report.json`、`formal/states/`、`__pycache__`、`*.pyc` 全無命中）✅。
- **安全**：未新增 `SDD_CONTRACT_VIOLATION` / `ToolInvocationPort` 路徑；本輪不改 `copy_on_evolve.sh`（improving_97 已審無注入面），僅執行既有腳本 + 一行註解編輯。
- **零碰**：AutoClaude 全部源碼/測試、v0.29 及更早凍結版本目錄、任何 `*.tla`/FSM `_HAPPY_PATH`/`.cfg` 全未觸（git diff/status 為證）。

---

## §5　階段四：CI 平價收斂 — 零退化驗證矩陣（實測欄階段四回填）

| 檢查 | 命令 | 通過條件（floor 取 §2 實測） | 實測 |
|------|------|------------------------------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3607 passed / 0 failed | ✅ **3607 passed / 0 failed / 122 skipped**（零碰 AutoClaude） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | ✅ **0 violations**（19947 / cap 20438，不變） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 雙軌（v0.01 + **v0.30 LATEST**）pytest not-chaos 全綠 + arch_fitness exit<2 + 11 lint 全過；v0.30 計數＝v0.29(1665)、scripts/tests=130 | ✅ **真實 exit 0**；雙軌 **v0.01:1478 + v0.30:1665（＝v0.29）+ scripts/tests:130**；**FF-17 確認 LATEST=v0.30 自動入閘**；**FRAMEWORK_STATUS 新鮮（非 stale）**＝DEF-96-001 跨版實證；arch_fitness fail=0（3 advisory warn 不阻擋） |
| DAL 等價 | equivalence job | 本輪**無新 DAL/checkpoint 改動** → N/A 第二型 | ✅ **N/A 第二型**（既有 `tests/equivalence/` 隨 3607 全套通過、零 DAL/checkpoint 改動） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A 第一型（條件未觸發、未跑）** | ✅ **N/A 第一型**（鐵證：v0.29↔v0.30 diff 僅 `fsm_runtime.py:420-421` 兩行註解，零碰任何 `*.tla`/`.cfg`/`_HAPPY_PATH`/FSM；TLC 不在 ci-gate not-chaos、需 Java + `--full-tlc`） |

---

## §6　缺陷帳本本輪處置
- **DEF-62-001**：本輪真修（W-98-1，v0.30 校正註解）；回歸驗證後改 `fixed@improving_98`（v0.29 凍結本體留 stale 為歷史快照，符合 Copy-on-Evolve 語意）。
- **DEF-01-009**：複驗（§2.2），維持 open watch。
- 本輪行進中新發現缺陷一律即記 `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-98-xxx）。

---

## §7　Copy-on-Evolve / 版本演化
- **本輪有版本演化**：`AISDLC_SDD_v0.29`（凍結唯讀）→ `AISDLC_SDD_v0.30`（新 LATEST）。改動僅落 v0.30；附 `v0.30/EVOLUTION_LOG.md` + `v0.30/releases/CHANGELOG.md`。
- TLC：N/A 第一型（純註解、零碰形式化模型，git diff 證）。

---

## §8　誠實性標記
- 本檔於**階段二先落地**（§1/§2/§3 規格先行，含 `<Architecture_Design_Review>`/介面 delta/RTM）；§4/§5 實測欄、雙重驗證結果於階段三/四回填。
- 矩陣 N/A 階段四精確區分兩型（DAL＝既有隨全套已過；TLC＝條件未觸發未跑 + git diff 證）。
- 本輪柱別＝**B 軌（框架 Copy-on-Evolve 版本演化）**；DEF-62-001 真修＝掌舵者裁定（非為註解擅開新版）。
- DEF-01-009 維持 open watch、不投機重構＝守 Rule 2/3，誠實標記為「正確的不作為」而非遺漏。
