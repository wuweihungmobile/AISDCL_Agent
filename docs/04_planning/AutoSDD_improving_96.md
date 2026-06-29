# AutoSDD_improving_96 — A 軌：PRD→playbook 橋接 backend-robust 化（DEF-95-002 修復）

> **本輪柱別**：**A 軌（雙向協作橋接）** 單柱聚焦。下一份：`AutoSDD_improving_97.md`。
> **驅動器**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`（整合迭代軌道①）。
> **日期**：2026-06-29　**掌舵者裁定本輪 W 項**：只做候選 (a) DEF-95-002 修（Archy artifact-evaluator）。
> **版本演化**：框架本體 Copy-on-Evolve **v0.28 → v0.29**（僅改 Archy agent evaluator 政策）。

---

## §1　本輪輸入（自上輪繼承）

### 1.1 improving_95 RTM / 實作順序遺留
- improving_95（commit 0f00f8b、tag v2026.06.29-46）已結案：PRD→Archy 真跑→compiler→AutoClaude 真跑端到端首證，**sdk 後端 5/5 全過**。
- **未竟之處（本輪標的）**：**pty 後端 0/5**——非工作失敗，而是「keyword 回顯 + pty `--output-format json` 擷取」雙重脆弱致 E-SPEC-1 判定失敗（Claude 實際已正確寫出 SPEC.md 4151 bytes）。記為 **DEF-95-002（P3, routed improving_96）**。

### 1.2 缺陷帳本 open/routed（階段一複驗結果，見 §2）
| 缺陷 | 嚴重度 | 狀態 | 本輪處置 |
|------|--------|------|---------|
| **DEF-95-002** | P3 | routed improving_96 | **本輪修復**（W-96-1~3） |
| DEF-19-001 | P3 | routed（improving_40 達結構天花板、實質 closed） | 非本輪 scope，狀態不變 |
| SD_09 W1 source-sha 觀察期 | — | 已到期（~6/29）、待 W1 改源碼達 unique sha≥7 | C 軌標的，非本輪（掌舵者未選） |

### 1.3 上輪 QA 複審「延後/下輪」條目
- improving_95 結案留 4 候選 (a)~(d)；本輪掌舵者選 (a)。(b)/(c)/(d) 留候選帳本，未動。

---

## §2　階段一：現況重偵察（Zero-Trust Re-Audit 實測）

> 三組 Explore agent 獨立實測（2026-06-29），**硬閘通過**（全綠且 ≥ 上輪基線）。

| 檢查 | 命令 | 實測 | 結論 |
|------|------|------|------|
| AutoClaude 全套 pytest | `python -m pytest tests/ -q`（AutoClaude/） | **3600 passed / 0 failed / 122 skipped** | ✅ ＝上輪基線 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **0 violations**（19895 / cap 20438） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | OK | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | LATEST=**v0.28**；v0.01 1478 / v0.28 1665 / infra 129 全綠；arch_fitness structural fail 0、exit<2 | ✅ |
| improving_95 構件 | — | harness `tools/run_bridge_e2e.py` + 7 單測 + fixture + 3 文件**全部真實存在** | ✅ |

**本輪零退化 floor（禁寫死，取本表實測）**：AutoClaude pytest **≥ 3600 passed / 0 failed**；lint-imports 8 kept；LOC 0；AISDLC_SDD ci-gate exit 0（雙軌，新 LATEST=v0.29）。

### 2.1 DEF-95-002 根因定位（階段一深偵察）
- `infra/adapters/shell_evaluator.py:30-33`：**`expected_output_regex` 比對在 `evaluator_command` 之前**——regex 不過即 `return failure`，evaluator_command 根本不執行。
- fixture E-SPEC-1（`scripts/bridge_e2e/strutils_prd_plan.yaml:42-43`）：`expected_output_regex: "\\[SPEC_DONE\\]"` + `evaluator_command: null` → 完全靠 keyword 回顯把關。
- Archy 政策（`AISDLC_SDD_v0.28/agent/specialized/sdd-prd-to-playbook-zh.yaml:63`）：「evaluator_command：…無可機械檢查者**留空**」→ 教 Archy 對 doc/spec 步只用 keyword regex。
- pty 後端 `claude --output-format json` 對寫檔步擷取脆弱（DEF-81-001 族）→ keyword `[SPEC_DONE]` 遺失 → regex 不過 → escalated 整輪停，**即使檔案已正確產生**。

---

## §3　階段二：本輪增量設計

### 3.1 設計主張（一句話）
**doc/spec 產檔步的把關，從「keyword 回顯（後端脆弱）」改為「artifact-existence（檢查檔案真的產生、後端無關）」**。三處連動 + 既有機制零改動（artifact-existence 用既有 `evaluator_command` 通道表達，不新增 evaluator 型別）。

### 3.2 W 項（3 項）

#### W-96-1：`autoclaude/artifact_check.py` artifact-existence 檢查工具（AutoClaude，可直接改）
- **介面**：`python -m autoclaude.artifact_check <path> [--min-bytes N]`。檔案存在且 size ≥ N → exit 0；否則 stderr 訊息 + exit 1。預設 `--min-bytes 1`（非空即可）。
- **為何裝進 `autoclaude` 套件而非 repo-root `tools/`**：evaluator（`execution/evaluator.py` `subprocess.run(shell=True)` 無 cwd）繼承 AutoClaude 進程 cwd＝harness 傳的 temp 專案目錄。`python -m tools.X` 在 temp 目錄解析不到 `tools`；`python -m autoclaude.artifact_check` 因 autoclaude 為 pip editable-install，**任何 cwd 皆可解析**，且 `<path>` 相對 temp 目錄正確（與 `pytest test_strutils.py` 同理）。
- **依賴**：stdlib（`pathlib`/`sys`）+ click。**不 import** infra/plugins/core。
- **單測**：`tests/tools/test_artifact_check.py`（≥4 case：存在+夠大→0、不存在→1、存在但太小→1、邊界 size==min→0）。

#### W-96-2：Copy-on-Evolve v0.28 → v0.29 + Archy evaluator 政策改寫（框架本體，凍結→新版）
- **複製**：`bash scripts/copy_on_evolve.sh AISDLC_SDD_v0.28 AISDLC_SDD_v0.29`（git archive 純 tracked 1054 檔；自動跑 skill_header_sync 版本戳記→v0.29 + sync_exposed_skills 父層鏡像 + 補 .gitignore）。
- **唯一手改檔**：`AISDLC_SDD_v0.29/agent/specialized/sdd-prd-to-playbook-zh.yaml`
  - `version: "v0.28"` → `"v0.29"`（agent 自身版本欄，誠實對齊）。
  - `outputs.three_tier_plan.contract`（line 62-63）evaluator 指引改寫：
    - 原：「expected_output_regex：該步完成關鍵字（如 `\[FRD_DONE\]`）；evaluator_command：…無可機械檢查者留空」
    - 新：區分兩類步——
      - **可跑測試的實作步**（如 SCG-4 dev）：`evaluator_command` 用 `pytest`，`expected_output_regex` 可留空。
      - **doc/spec 產檔步**（PRD/FRD/SRD/SPEC/ADR 等寫文件）：**用 artifact-existence evaluator**＝`evaluator_command: python -m autoclaude.artifact_check <相對產出檔> --min-bytes N` 檢查檔案真的產生；**`expected_output_regex` 留空、不靠 keyword 回顯**（理由：後端 JSON 擷取脆弱會吞掉 keyword 致誤判，DEF-95-002）。
  - `core_principles` / `quality_standards` 對應補一條「doc/spec 步用 artifact-existence、不靠回顯」原則。
  - **白名單自律不變**：evaluator_command 仍僅 `pytest`/`python` 開頭、無 shell 元字元（攤平器 fail-closed）。
- **EVOLUTION_LOG.md + releases/CHANGELOG.md**：新增 v0.28→v0.29 條目（TLC N/A——零碰 `*.tla`/`_HAPPY_PATH`；純向後相容 agent 政策調整）。

#### W-96-3：fixture 全步 backend-robust 化 + 連帶測試更新 + bridge e2e 真跑取證
> **🔴 範圍校正（階段三 zero-trust 自審揭露）**：`shell_evaluator` 是**先比對 regex 再跑 evaluator_command**，故**所有帶 keyword regex 的步在 pty 都脆弱**（不只 E-SPEC-1）：E-IMPL-1/3 keyword-only 會卡；E-IMPL-2/4 雖有 pytest evaluator，但 keyword regex 先擋、pty 吞 keyword 時 pytest 根本不會跑。improving_95 pty 在 E-SPEC-1 即 escalated 故未暴露後續風險。只修 E-SPEC-1 ⇒ pty 改在 E-IMPL-1 卡、DEF-95-002 未真關閉。**故 fixture 全 5 步依 v0.29 Archy 政策一致改造**（與政策「兩類步皆 regex 留空」自洽）。fixture 採手動遷移至 v0.29 政策（非再花 token 重跑 Archy 重生；政策本身由 v0.29 yaml + 本輪 e2e 真跑驗證）。
- **fixture** `scripts/bridge_e2e/strutils_prd_plan.yaml` **全 5 步**：`expected_output_regex` 一律 `null`、移除 prompt 內「輸出完成關鍵字」要求；evaluator_command 給客觀閘——
  - E-SPEC-1（寫 SPEC.md）→ `python -m autoclaude.artifact_check SPEC.md --min-bytes 200`
  - E-IMPL-1（TDD 紅步，寫 test_strutils.py）→ `python -m autoclaude.artifact_check test_strutils.py --min-bytes 80`
  - E-IMPL-2（實作 slugify 至綠）→ `pytest test_strutils.py -q`（唯一閘）
  - E-IMPL-3（TDD 紅步，追加 truncate 測試）→ `python -m autoclaude.artifact_check test_strutils.py --min-bytes 160`
  - E-IMPL-4（實作 truncate 至綠）→ `pytest test_strutils.py -q`（唯一閘）
  - **誠實標記**：E-IMPL-1/3 為「寫/改檔」TDD 紅步，artifact-existence 只證檔案存在/成長（不證內容正確）——這是 backend-robust 與 TDD 紅步本質的取捨；正確性由緊接的 pytest 步（E-IMPL-2/4 import 同檔）backstop，鏈自驗。較 keyword 回顯**不更弱且後端無關**。
- **連帶測試更新**（誠實反映新意圖，非放水——測試現在鎖「doc 步有 artifact evaluator」）：`tests/tools/test_run_bridge_e2e.py`
  - `test_compile_strutils_plan_flattens_5_tasks_with_goal_grouping`：evaluator 集合 `{E-IMPL-2, E-IMPL-4}` → `{E-SPEC-1, E-IMPL-2, E-IMPL-4}`；E-IMPL-2/4 仍 `pytest ` 開頭、E-SPEC-1 為 `python -m autoclaude.artifact_check ` 開頭。
  - `test_build_evidence_joins_goal_task_and_aggregates`：`evaluator_steps == 2` → `3`。
- **新增白名單回歸鎖**：`test_run_bridge_e2e.py` 或 compiler 測試加一案，斷言 `sanitize_evaluator("python -m autoclaude.artifact_check SPEC.md --min-bytes 200")` 不 raise 且原樣返回（鎖 artifact-check 形態永遠通過消毒）。
- **bridge e2e 真跑取證**（階段四，花真 token）：pty 後端對 strutils fixture 真跑，證 E-SPEC-1 step **不再因 keyword 脆弱 escalated**（DEF-95-002 closed 證據）；證據 JSON 落 `docs/03_testing/`。

### 3.3 介面 delta / LOC / importlinter 影響
| 項目 | delta | LOC tier | importlinter |
|------|-------|----------|--------------|
| `autoclaude/artifact_check.py`（新） | 新增葉 CLI 模組 | unclassified→≤750（實際 ~60 行） | 零影響（不被 plugins/core import、不 import infra） |
| `tests/tools/test_artifact_check.py`（新） | 新增單測 | 測試非 LOC scan 範圍 | — |
| Archy yaml（v0.29） | 改 evaluator 指引文字 + version 欄 | 非 .py | — |
| fixture / test_run_bridge_e2e.py | 改 evaluator 值 + 斷言 | — | — |
- **零碰**：ports/、plugins/、core/、infra/adapters/、playbook_runner.py、PlaybookCheckpoint、DAL 三後端、任何 `*.tla`/FSM/_HAPPY_PATH。
- **Snapshot**：不動（artifact_check.py 非 port/plugin，snapshot 只列 port/plugin/tier/importlinter/DAL）。

### 3.4 RTM 需求列（實測欄階段四回填）
| RTM | 需求 | 驗證 |
|-----|------|------|
| RTM-96-1 | artifact_check：存在+夠大→exit 0；不存在→exit 1；存在但太小→exit 1；size==min→0 | `test_artifact_check.py` |
| RTM-96-2 | artifact-check evaluator_command 通過 `sanitize_evaluator` 白名單（不 raise） | compiler/harness 回歸鎖測試 |
| RTM-96-3 | Archy v0.29 doc/spec 步政策＝artifact-existence + regex 留空（規格文字 + 範例） | v0.29 yaml 審閱 + ci-gate |
| RTM-96-4 | fixture **全 5 步** regex=null + 客觀 evaluator（3 artifact + 2 pytest）；無任一步靠 keyword | fixture 審閱 + `test_run_bridge_e2e.py`（斷言全步 regex None） |
| RTM-96-5 | compile 鏈把全 5 步 evaluator 正確攤平、evaluator 集合＝5 步、白名單放行 | `test_run_bridge_e2e.py`（更新後）+ compile-only（5 evaluator / 0 regex） |
| RTM-96-6 | bridge e2e pty 後端真跑：不再因 keyword 脆弱 escalated（DEF-95-002 closed 證據） | 階段四真跑證據 JSON |

---

## §4　階段三：實作與雙重驗證（已完成）

- **W-96-1**：`autoclaude/artifact_check.py`（53 行）+ `tests/tools/test_artifact_check.py`（6 測）→ **6 passed**；任意 cwd（temp 目錄）真跑驗證 exit 0/1 正確。
- **W-96-2**：`copy_on_evolve.sh` 建 v0.29（863 tracked 檔，自動同步 45 戳記 + 59 鏡像 + .gitignore）；手改 Archy yaml（version v0.29 + core_principles 補 backend-robust 原則 + outputs 契約改寫）；EVOLUTION_LOG + CHANGELOG 條目。**補修**：copy_on_evolve **不**自動重生 `FRAMEWORK_STATUS.md`，首次 ci-gate 在框架版本 SSOT 新鮮度 lint 報 stale → 手動 `framework_status_snapshot.py --write`（latest v0.28→v0.29，2 行）後 --check 新鮮。
- **W-96-3**：fixture 全 5 步 backend-robust 化（regex 全 null、3 artifact + 2 pytest）；`test_run_bridge_e2e.py` 更新（evaluator 集合＝5 步、`evaluator_steps`=5、新增「全步 regex None」斷言 + sanitize 白名單回歸鎖）→ **14 passed**；compile-only 確認 5 evaluator / 0 regex。
- **雙重驗證（pty 真跑，DEF-95-002 closed 鐵證）**：`run_bridge_e2e.py` 對 strutils fixture 以 **pty 後端**（ab_pty_config）真跑 → **5/5 全過**（escalated=False、kernel_success=True、evaluator_steps=5）；improving_95 同 fixture pty 為 **0/5**（E-SPEC-1 keyword escalated）。真產出 SPEC.md（3086B）/ strutils.py / test_strutils.py（3950B）；**parent 獨立複跑 Claude 產物＝35 passed**（非空殼）。證據 `AutoClaude/docs/03_testing/AutoSDD_improving_96_bridge_e2e_pty_evidence.json`；真產物 + pytest 複跑輸出（35 passed）持久化於 `AutoClaude/docs/03_testing/improving_96_pty_artifacts/`（QA 鏡 P3-1 處置：建立可複跑證據鏈）。
- **安全**：未新增 `SDD_CONTRACT_VIOLATION` / `ToolInvocationPort` 路徑；新 evaluator 形態經 `sanitize_evaluator` 白名單（回歸鎖測試證），消毒零弱化。

---

## §5　階段四：CI 平價收斂 — 零退化驗證矩陣（實測欄階段四回填）

| 檢查 | 命令 | 通過條件（floor 取 §2 實測） | 實測 |
|------|------|------------------------------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3600 passed / 0 failed（新測試只增不減） | ✅ **3607 passed / 0 failed / 122 skipped**（+7 新測） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | ✅ **0 violations**（19947 / cap 20438） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 雙軌（v0.01 + v0.29）pytest not-chaos 全綠 + arch_fitness exit<2 + 11 lint 全過 | ✅ **真實 exit 0**（v0.01 + v0.29 雙軌；v0.29 1665 passed + infra 129；FF-1~17 + 11 lint 全綠）〔註：首跑 FRAMEWORK_STATUS stale，重生後重跑取真實 exit 0〕 |
| DAL 等價 | equivalence job | 本輪**無新 DAL/checkpoint 改動**→既有 `tests/equivalence/` 隨全套通過、無新增 round-trip 契約 | ✅ **N/A 第二型**（既有 equivalence 測試隨 3607 全套通過、零 DAL/checkpoint 改動） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A 第一型（條件未觸發、未跑）** | ✅ **N/A 第一型**（鐵證：`AISDLC_SDD_v0.28` vs `v0.29` 的 `formal/*.tla`/`.cfg` + `transition_rules.py` diff 逐位元零差異） |
| bridge e2e（A 軌真跑） | `python tools/run_bridge_e2e.py --source … --config ab_pty_config --workdir …` | pty 後端不再 escalated（DEF-95-002 closed） | ✅ **pty 5/5 全過**（improving_95 為 0/5）；parent 複跑 Claude 產物 35 passed |

---

## §6　缺陷帳本本輪處置
- **DEF-95-002**：本輪修復；階段四真跑證據通過後改 `fixed@v0.29`。
- 本輪行進中新發現缺陷一律即記 `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-96-xxx）。

---

## §7　Copy-on-Evolve / 版本演化
- v0.01 凍結基線不動；v0.28 凍結（升為中間凍結版）；v0.29＝新 LATEST。
- 用 `scripts/copy_on_evolve.sh`（禁裸 `cp -r`，DEF-11-001/38-001）；自動同步版本戳記/鏡像/.gitignore。
- TLC：N/A（零碰形式化模型，git diff 證）。
- 新檔入庫潔淨度：`git add -A -n AISDLC_SDD_v0.29/` dry-run 審 would-add 無 runtime/stale 產物（DEF-11-002 紀律）。

---

## §8　誠實性標記
- 本檔於**階段二先落地**（§1/§2/§3 規格先行）；§4/§5 實測欄、§3.2 W-96-3 真跑結果於階段三/四回填。
- 矩陣 N/A 已精確區分兩型（DAL＝既有隨全套已過；TLC＝條件未觸發未跑 + git diff 證）。
