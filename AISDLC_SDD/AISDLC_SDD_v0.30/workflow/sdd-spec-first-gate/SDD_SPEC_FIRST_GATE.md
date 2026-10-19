# SDD Spec-First Gate Workflow
# 規格優先閘門工作流程

**版本**: v1.3
**建立日期**: 2026-04-12
**最後更新**: 2026-10-18
**工作流程類型**: 品質閘門（Quality Gate）
**分類**: SDD Phase 01 新增；Phase A 強化（FSM 整合）；整合輪 115 補強（S-01 FSM 寫入指令、G-10 增量條款）；整合輪 116 補強（D-116-09 報告與 RTM 落點、棕地基線採納指路）

---

## 🎯 工作流程目的

強制執行 SDD（Spec-First）原則：規格必須先於所有實作行為完成並通過驗證。

---

## 🔗 FSM 整合

本工作流程已整合至 [SDD_FSM_ENGINE.md](../sdd-fsm-engine/SDD_FSM_ENGINE.md)。

| FSM 狀態 | 對應 SCG 動作 | Retry Limit |
|---------|-------------|------------|
| SCG_VALIDATION | SCG-0, SCG-1, SCG-2, SCG-3 驗證 | 最多 **3 次** → ESCALATION |
| PR_REVIEW | SCG-4 實作審查 | 最多 **5 次**；相同模式 3 次 → SPEC_AUDIT |
| RTM_VERIFY | SCG-5 RTM 完整性驗證 | 最多 **2 次** → ESCALATION |
| RELEASE_READY | SCG-6 發布確認（雲端 CI 綠才 RELEASE） | 最多 **2 次** → ESCALATION；CI 紅時有界退回 IMPLEMENTATION，耗盡後不自動恢復（OBS-SI-117） |
| SPEC_FROZEN | SCG 通過後 → 觸發 stage-compaction | — |
| ESCALATION | retry 耗盡後 → 強制人工介入 | 不可自動退出 |

**退場機制**：見 [SDD_ESCALATION_PROTOCOL.md](../sdd-escalation/SDD_ESCALATION_PROTOCOL.md)

---

## 🔷 SCG 閘門類型與觸發條件

> ⚠️ **SCG 編號以 AISDLC_SDD_INIT.md 與 CLAUDE.md 為唯一真理來源（SSoT）。**

| 閘門 | 名稱 | 觸發條件 | 主責 Agent |
|-----|------|---------|-----------|
| 🔷 SCG-0 | Requirement Spec Gate | 需求凍結前（PRD + FRD 完成） | sa-analyst |
| 🔷 SCG-1 | Design Spec Gate | 設計凍結前（SRD + API Spec 完成） | sd-architect |
| 🔷 SCG-2 | Architecture Spec Gate | 架構凍結前（C4 圖 + ADR 完成） | sd-architect |
| 🔷 SCG-3 | API Contract Gate（Contract Freeze） | 開發啟動前（OpenAPI 3.1 凍結） | sd-architect / integration-specialist |
| 🔷 SCG-4 | PR Review Gate | 實作 PR 審查（實作與規格一致性） | dev-senior / tech-lead |
| 🔷 SCG-5 | RTM Completeness Gate | 交付前（RTM 100% 覆蓋） | qa-lead |
| 🔷 SCG-6 | Release Gate | 發布前（所有閘門通過確認） | all |

> **產出落點（整合輪 116／D-116-09）**：SCG 驗證報告、SCG-4 審查報告、RTM 與 RTM 驗證報告一律寫 `docs/06_quality/`；
> `docs/03_testing/` 只放**凍結前**的測試規格（TCS、測試策略、測試計畫）。原因：Rule 9.6 絕對禁令 #3 在 SCG_VALIDATION／
> PR_REVIEW／RTM_VERIFY／IMPLEMENTATION 等態擋寫路徑含 `docs/01_requirements/`｜`docs/02_architecture/`｜`docs/03_testing/`
> 的 Write／Edit，報告與 RTM 寫進 `docs/03_testing/` 會被自己的守門擋下（整合輪 115 dogfood 的 DEF-AC-018，六列 BLOCKED）。
> 判準本身不改；對映的三支 skill（`/sdd-gate`、`/sdd-review`、`/rtm-generate`）與 `AISDLC_SDD/CLAUDE.md` Rule 2 表同步。

---

## 🔄 工作流程步驟（含 FSM 整合）

```
[任何 Stage 文件產出前]
         │
         ▼
0. 【FSM 狀態確認】
   記錄當前 retry_count（本 SCG 閘門的重試次數）
   若 retry_count ≥ max_retry → 直接進入 ESCALATION（不執行後續步驟）
         │
         ▼
1. Agent 識別文件類型 → 選擇對應 SCG 閘門
         │
         ▼
2a.【SLV 前置驗證 — 僅 SCG-0 / SCG-3】
   執行 /spec-logical-validator
   ├── SLV CRITICAL FAIL → retry_count++ → 🔴 STOP（修正邏輯問題）
   └── SLV PASS → 繼續步驟 2a-bis
         │
         ▼
2a-bis.【Ambiguity Gate — 僅 SCG-0，Phase G M3 / Rule 9.16】
   呼叫 tools.fsm_runtime.ambiguity_scorer.score_frd(FRD_path)
   ├── max(score) ≥ 0.4 且無對應 AMBIGUITY-WAIVER → SCG-0 FAIL → retry_count++ → 🔴 STOP
   ├── 報告寫入 build/reports/scg/AMBIGUITY-{date}.yaml
   └── 全部 < 0.4 或已 waive → 繼續步驟 2a-ter
         │
         ▼
2a-ter.【Spec Debate — 僅 SCG-0，Phase K M-K2 / ACT-084 / Rule 9.23.3~4，advisory】
   對落在 near-threshold band（預設 0.25 ≤ score < 0.4）的 AC：
   呼叫 tools.fsm_runtime.spec_debate.debate(ac_text)（兩隔離詮釋提對立讀法，量化分歧）
   ├── verdict=divergence → FSMRuntime.enter_spec_debate(ac_id) → exit_spec_debate("divergence")
   │      → HUMAN_PENDING（附兩詮釋 + 分歧證據，人工一句話定案；advisory 不自動改 AC）
   └── verdict=consensus → （如已進入）exit_spec_debate("consensus") → 繼續步驟 2b
         │
         ▼
2b. 執行 spec_compliance_check（格式/完整性驗證）
   ├── completeness 檢查
   ├── format 檢查
   ├── cross_reference 檢查
   └── sdd_specific 檢查
         │
         ├── 檢查失敗 → retry_count++ → 🔴 STOP：修正後重新執行
         │              若 retry_count ≥ 3 → ESCALATION
         │
         ▼
3. 🔷 Spec Compliance Gate PASSED（retry_count 不重置，待 SPEC_FROZEN 後重置）
         │
         ▼
4. 🔴 Human Checkpoint（人類審查）
         │
         ├── 需修改 ──→ 回到步驟 1（retry_count++）
         │
         ▼
5. 🎯 SPEC_FROZEN milestone
   → 執行 /stage-compaction（強制上下文壓縮）
   → retry_count 重置為 0（進入新 Stage）
   → 進入下一 Stage 的 SPEC_DRAFTING
```

> 🔴 **訂正（整合輪 115／S-01）：上方第 3 步的括號與 runtime 不符。**
> **被訂正的原文逐字保留（訂正協議：禁止靜默覆寫；原文仍在上方第 3 步，未動）**：
> 「retry_count 不重置，待 SPEC_FROZEN 後重置」。
> **實際行為**（`FSMRuntime.record_gate_result` 的 `reset_retry`、`FSMState.record_spec_frozen`；〔實測〕隔離沙盒中
> `gate … PASS` 之後 `retry_history.SCG_VALIDATION.current_count` 即為 0）：`gate … PASS` 當下就把**該 gate**
> 的 `current_count` 歸零；`spec-frozen` 再把 SCG_VALIDATION／PR_REVIEW／RTM_VERIFY／RELEASE_READY 全部歸零
> （RELEASE_READY 自 OBS-SI-117 起也有計數，本句原列三個）；兩者都**不**清除
> `cumulative_history`。全文搜尋同一宣稱：全樹僅此一處（`SDD_FSM_ENGINE.md` 與 `sdd-review` skill 的相關敘述與
> runtime 一致，未動）。

---

## 🧾 FSM 寫入指令（S-01：每個閘門結果都要落成一行 CLI）

> **為什麼需要本節**：上方流程裡的「retry_count++」「SPEC_FROZEN milestone」若只是模型記憶中的動作，
> `FSM-STATE-<專案鍵>.yaml` 就永遠停在 `INIT`——而它是 SDD→AutoClaude 橋接**唯一的接頭**（AutoClaude 的凍結閘、
> Bridge 的 `GET /sdd/fsm`、Console 的 SDD 卡都只看它）。Rule 9 絕對禁令 #1 又禁止手改 yaml，所以合法的寫入路徑只有
> 一條：`python -m tools.fsm_runtime.fsm_runtime <動詞>`。本節把每個閘門結果對應到確切指令；讀狀態用 `show`。

### 呼叫樣板（cwd＝SDD 版本目錄；雙形態）

- `<SDD 版本目錄>`＝`AISDLC_SDD/<LATEST>`（LATEST 現查：`python AISDLC_SDD/scripts/sdd_version.py`）。`tools.fsm_runtime`
  是以版本目錄為根的 package，**cwd 必須是版本目錄**；`python` 須是裝有 PyYAML 的直譯器（monorepo 內＝根層 `.venv`）。
- `<鍵>`＝FSM 專案鍵（原名或淨化後的檔名幹皆可；預設＝`SDD_PROJECT`，再退回版本目錄上一層的目錄名）。**每次都帶
  `--project "<鍵>"`**，並與 hooks 讀到的 `SDD_PROJECT` 保持一致。
- `SDD_STATE_DIR`（選用，必須是**絕對路徑**；相對路徑會被拒）：未設＝狀態檔在 `<SDD 版本目錄>/build/reports/fsm/`；
  有設＝**外部專案模式**（狀態檔放在被治理專案自己的樹，例如 Console 管理的專案；規則命中遙測回寫預設關，不弄髒
  框架樹）。外部專案模式的 `<專案根>`＝被治理專案根；預設模式的 `<專案根>`＝`<SDD 版本目錄>`（專案文件寫在
  `<版本目錄>/docs/`）。
- **讀 rc 不接管線**：要看輸出就先接到變數；不要寫 `… | Select-Object -First 1` 之後再讀 `$LASTEXITCODE`（真 rc 會被吃掉）。
- 每次呼叫 stderr 都會多一行 runpy 的 `RuntimeWarning: 'tools.fsm_runtime.fsm_runtime' found in sys.modules …`，與成敗無關
  （要消音就在 `python` 後加 `-W ignore::RuntimeWarning`）；成敗只看 rc 與 stdout。

PowerShell（Windows；不裸 `cd`——`Push-Location`／`Pop-Location` 在同一次呼叫內成對）：

```powershell
Push-Location "<SDD 版本目錄>" -ErrorAction Stop; python -m tools.fsm_runtime.fsm_runtime <動詞> --project "<鍵>" <旗標>; Pop-Location
```

bash／zsh（mac／Linux）：

```bash
cd "<SDD 版本目錄>" && python -m tools.fsm_runtime.fsm_runtime <動詞> --project "<鍵>" <旗標>
```

外部專案模式（多設 `SDD_STATE_DIR` 與 `SDD_PROJECT`）：

```powershell
Push-Location "<SDD 版本目錄>" -ErrorAction Stop; $env:SDD_STATE_DIR = "<專案根>\build\reports\fsm"; $env:SDD_PROJECT = "<鍵>"; python -m tools.fsm_runtime.fsm_runtime <動詞> --project "<鍵>" <旗標>; Remove-Item Env:SDD_STATE_DIR, Env:SDD_PROJECT; Pop-Location
```

```bash
cd "<SDD 版本目錄>" && SDD_STATE_DIR="<專案根>/build/reports/fsm" SDD_PROJECT="<鍵>" python -m tools.fsm_runtime.fsm_runtime <動詞> --project "<鍵>" <旗標>
```

範例（SCG-0 通過，兩種形態各一行）：

```powershell
Push-Location "<SDD 版本目錄>" -ErrorAction Stop; python -m tools.fsm_runtime.fsm_runtime gate --project "<鍵>" --gate SCG_VALIDATION --result PASS --reason "SCG-0 PASS"; Pop-Location
```

```bash
cd "<SDD 版本目錄>" && python -m tools.fsm_runtime.fsm_runtime gate --project "<鍵>" --gate SCG_VALIDATION --result PASS --reason "SCG-0 PASS"
```

### 閘門結果 → 指令對照表

下表「指令」欄＝填入上面樣板 `<動詞> <旗標>` 的內容（`--project "<鍵>"` 已在樣板內，不再重複）。SCG-0～SCG-3 四道閘共用
FSM 的 `SCG_VALIDATION` 一個重試預算（上限 3）；SCG-4＝`PR_REVIEW`（上限 5）、SCG-5＝`RTM_VERIFY`（上限 2）、
SCG-6＝`RELEASE_READY`（上限 2；OBS-SI-117，語意同 `RTM_VERIFY`：第 1 次失敗退回 IMPLEMENTATION、第 2 次失敗 → ESCALATION）。

| # | 時機（對應上方流程步驟） | FSM 轉態 | 指令 |
|---|---|---|---|
| 0 | 隨時確認進度 | （唯讀） | `show`：印完整狀態 JSON，看 `fsm_state.current_state`、`retry_history.<GATE>.current_count`、`frozen_stages`。狀態檔不存在時 `show`／`transition` 會**建立** INIT 狀態檔；只想確認專案已存在、不想誤建檔就加 `--must-exist`（不存在 → rc 5，不建檔） |
| 1 | 新專案起手（步驟 0 之前） | INIT → SCENARIO_DETECT → AGENT_LOAD → SPEC_DRAFTING | 依序三次：`transition --to SCENARIO_DETECT`、`transition --to AGENT_LOAD`、`transition --to SPEC_DRAFTING --reason "<Stage 名稱>"` |
| 2 | 規格草稿完成、送驗（步驟 1～2b 開始） | SPEC_DRAFTING → SCG_VALIDATION | `transition --to SCG_VALIDATION --reason "SCG-<n> 驗證開始"` |
| 3 | 步驟 2a／2a-bis／2b 任一失敗（retry_count++） | SCG_VALIDATION → SPEC_DRAFTING；第 3 次失敗 → ESCALATION | `gate --gate SCG_VALIDATION --result FAIL --reason "<失敗原因，例：SLV-002／FRD 缺 NFR 量化>"` |
| 4 | 步驟 3 Compliance Gate PASSED | SCG_VALIDATION → HUMAN_PENDING | `gate --gate SCG_VALIDATION --result PASS --reason "SCG-<n> PASS"` |
| 5 | 步驟 4 🔴 人要求修改 | 維持 HUMAN_PENDING（FSM **沒有** HUMAN_PENDING → SPEC_DRAFTING 的邊） | `gate --gate SCG_VALIDATION --result FAIL --reason "人工審查：<修改要求>"`：retry_count++，被擋的轉態記進 `decision_trace`（`gate_fail_blocked`）；改好文件後**重新取得人的確認**；不要嘗試 `transition --to SPEC_DRAFTING`（TransitionError，rc 1） |
| 6 | 步驟 4 🔴 **人明確確認通過之後**（步驟 5） | HUMAN_PENDING → SPEC_FROZEN | `spec-frozen …`（見下一小節；之後依步驟 5 執行 `/stage-compaction`） |
| 7 | SPEC_FROZEN 之後，還有下一個 Stage | SPEC_FROZEN → SPEC_DRAFTING | `transition --to SPEC_DRAFTING --reason "進入 Stage-<n+1>"`（再回第 2 列） |
| 8 | SPEC_FROZEN 之後，進入實作（R-9.20.2 先過測試合約談判閘） | SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION | `negotiate-enter --reason "<原因>" --contract-ref "<TCS 相對路徑>"`；Dev／QA 對 oracle 達成共識並簽署後 `negotiate-exit --outcome agreed --reason "<共識依據>"`（規格不夠明確、定不出 oracle 時改 `--outcome underspecified` → SPEC_DRAFTING）。`SPEC_FROZEN → IMPLEMENTATION` 直達邊為向後相容仍存在，但走它等於靜默略過 R-9.20.2，無明文理由不要用 |
| 9 | 實作交 AutoClaude 執行 | IMPLEMENTATION → AUTOCLAUDE_DELEGATED → IMPLEMENTATION | `delegate-enter`／`delegate-exit`：見 `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`（Console／Bridge 路徑由 Bridge 呼叫） |
| 10 | SCG-4 開始 PR 審查 | IMPLEMENTATION → PR_REVIEW | `transition --to PR_REVIEW --reason "SCG-4 PR 審查開始"` |
| 11 | SCG-4 結果 | PASS：PR_REVIEW → RTM_VERIFY；FAIL：→ IMPLEMENTATION（同模式 3 次 → SPEC_AUDIT；耗盡 → ESCALATION） | `gate --gate PR_REVIEW --result PASS --reason "SCG-4 PASS"`；失敗時 `--result FAIL --reason "<失敗模式>"` |
| 12 | SCG-5 結果 | PASS：RTM_VERIFY → RELEASE_READY；FAIL：→ IMPLEMENTATION（耗盡 → ESCALATION） | `gate --gate RTM_VERIFY --result PASS --reason "SCG-5 PASS"`；失敗時 `--result FAIL --reason "<缺口>"` |
| 13 | SCG-6 通過（雲端 CI 綠） | RELEASE_READY → RELEASE | `transition --to RELEASE --reason "SCG-6 PASS"`（等效：`gate --gate RELEASE_READY --result PASS --reason "SCG-6 PASS"`，另歸零 RELEASE_READY 計數並留下 `gate_pass` 軌跡） |
| 14 | SCG-6 失敗（雲端 CI 紅；OBS-SI-117） | RELEASE_READY → IMPLEMENTATION（累計第 2 次失敗 → ESCALATION，**不自動恢復**，只有人能 `resume-from-escalation`） | `gate --gate RELEASE_READY --result FAIL --reason "<CI 失敗摘要，例：run id／失敗 job>"`：**理由必填**（缺＝rc 2，狀態不動）；修好後照第 10～12 列再走 PR_REVIEW → RTM_VERIFY → RELEASE_READY，計數不被那兩關的 PASS 洗掉（新一輪 `spec-frozen` 才歸零）；不要用裸 `transition --to IMPLEMENTATION`（邊合法但不記次數，只用於恢復） |
| 15 | 規格在 SPEC_AUDIT 或發布後（RELEASE_READY／RELEASE）被合法修訂，凍結摘要已過期（OBS-SI-108／F-17） | 不轉態（只**追加**一筆 `kind: refreeze` 的 `frozen_stages` 條目與一筆 `trigger: spec_refreeze` 的 trace） | `spec-refreeze --doc "<修訂過的文件相對路徑>" [--doc …] --root "<專案根>" --reason "<修訂內容；發生在哪個狀態／commit>" --approver "<核准者>"`（見下方〈`spec-refreeze`〉；**`--project` 必填**；不歸零任何 retry 計數） |

補充：

- **只認合法邊**：`transition`／`gate` 只走 `tools/fsm_runtime/transition_rules.py` 的合法邊；其他＝TransitionError
  （舊動詞：traceback＋rc 1；新動詞、`spec-refreeze` 與帶 `--digest` 或 `--json` 的 `spec-frozen`：rc 3＋單行 JSON）。
- **SPEC_REGRESSION_CHECK**：若 `SDD_FSM_ENGINE.md` 的轉換表要求先過它（本 Stage 有重試歷史，即第 5 列留下的
  `current_count > 0`）：`transition --to SPEC_REGRESSION_CHECK --reason "<原因>"`，通過後仍以 `spec-frozen`
  凍結（SPEC_REGRESSION_CHECK → SPEC_FROZEN 是合法邊）。**不要**用 `gate --gate SPEC_REGRESSION_CHECK --result PASS`
  代替——它只轉態，不寫 `frozen_stages`／`spec_doc_digests`。
- **ESCALATION**：重試耗盡或其他 R-9.x 觸發後，hooks 會擋下一切工具呼叫，**只有人能解**（Rule 9.5／絕對禁令 #6）。
  人在 SDD session 以上面的呼叫樣板執行（外部專案模式要帶同一組環境）：
  `resume-from-escalation --to IMPLEMENTATION --reason "<人工原因>"`（`--to` 只能是 SPEC_DRAFTING／IMPLEMENTATION／
  PR_REVIEW；缺 `--reason` 或 `--to` 不合法＝argparse 用法錯誤，rc 2，狀態不動）。完整的 Console／Bridge 版恢復指令樣板見
  `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` §6.8。
- 現況沒有「單獨重置 retry_count」的 CLI 動詞：該 gate 的計數在下一次 `gate … PASS` 或 `spec-frozen` 時歸零；
  不得為此手改 yaml（`/sdd-gate --retry-reset` 並不對應任何 FSM 寫入）。

### `spec-frozen`：凍結寫入（只在人類確認之後）

🔴 **Human Checkpoint 是人類動作**：agent 不得自行判定「已確認」；`--approver` 必須填**人類確認者**（非空、≤100 字、
不含控制字元；Bridge 路徑另禁 `;`，因為它的 `--reason` 以 `; ` 分隔欄位），不得填 agent／skill 名。確認前不要執行本指令
（Rule 8／R-9.5）。

PowerShell：

```powershell
Push-Location "<SDD 版本目錄>" -ErrorAction Stop; python -m tools.fsm_runtime.fsm_runtime spec-frozen --project "<鍵>" --stage "Stage-<n>" --doc "docs/03_testing/contracts/TCS-<Feature>-<date>.md" --doc "<其他凍結文件相對路徑>" --digest --root "<專案根>" --reason "<人類確認依據>" --approver "<人類確認者>" --json; Pop-Location
```

bash／zsh：

```bash
cd "<SDD 版本目錄>" && python -m tools.fsm_runtime.fsm_runtime spec-frozen --project "<鍵>" --stage "Stage-<n>" --doc "docs/03_testing/contracts/TCS-<Feature>-<date>.md" --doc "<其他凍結文件相對路徑>" --digest --root "<專案根>" --reason "<人類確認依據>" --approver "<人類確認者>" --json
```

| 旗標 | 說明 |
|---|---|
| `--stage` | 階段名；沿用 `Stage-<n>` 慣例（`tools/fsm_runtime/README.md`）。同一專案的階段名不要求唯一（摘要鍵遇重複以後者為準） |
| `--doc`（可重複） | 本階段凍結的文件；相對（POSIX 形）或絕對路徑皆可，但須落在 `--root` 之下。**必含要交給 AutoClaude 的 TCS**（官方命名 `TEST-CONTRACT-SPEC-*.md`／`TCS-*.md`）——TCS 不在任何階段的凍結清單內時，橋接的凍結閘 fail-closed |
| `--digest` | 開啟摘要模式：逐檔驗證存在、在根之下、為合法 UTF-8 且 ≤16 MiB，並把 `sha256:<64 位小寫 hex>`（**換行正規化後 UTF-8 文字**的雜湊，與 AutoClaude adapter 的 `spec.digest` 逐位元相同）寫入 `frozen_stages[-1].spec_doc_digests`（鍵＝POSIX 相對路徑）。至少要一個 `--doc`（否則 rc 4）。只帶 `--digest`、不帶 `--json` 時，成功輸出仍是人讀的一行 `OK spec frozen: <stage>`（失敗照下方 rc 契約）。**不帶 `--digest`＝舊行為**：不查檔、不算摘要，`spec_docs` 照字面記；此形態的凍結無法在事後偵測「凍結後改檔」，新文件一律帶 |
| `--root` | 路徑基準＝專案根，必須是**存在的絕對路徑目錄**（否則 rc 4）；只能與 `--digest` 一起用（單獨給＝argparse 用法錯誤，rc 2）。省略時：狀態目錄以 `build/reports/fsm` 結尾則取其上三層，否則取框架版本目錄；自訂 `SDD_STATE_DIR` 落在慣例之外而未給 `--root` 時，`doc_not_found` 會大聲失敗，不會靜默算錯檔 |
| `--reason` | 寫進 `decision_trace` 的稽核理由（缺省為 `Stage frozen: <stage>`）；寫人類確認的依據 |
| `--approver` | 確認凍結的人；寫入 `frozen_stages[-1].approved_by`（只在有值時才出現這個鍵） |
| `--json` | 輸出恰好一行 JSON（成功含 `spec_doc_digests`；失敗 `{"ok":false,"error":<代碼>,…}`），rc 如下 |

rc 契約（適用四個新動詞、`spec-refreeze` 與帶 `--digest` 或 `--json` 的 `spec-frozen`；舊動詞不帶新旗標時輸出與 rc 逐字不變）：0 成功（含 `"noop":true`）／
1 非預期例外／2 argparse 用法錯誤（stdout 無 JSON）／3 前置狀態不符（`transition_not_allowed`，例如 FSM 不在
HUMAN_PENDING）／4 參數值不合法（`invalid_argument`、`doc_not_found`、`doc_outside_root`、`doc_too_large`、
`doc_not_utf8`；`SDD_STATE_DIR` 寫成相對路徑）／5 狀態檔不存在（`--must-exist`）或不可讀。

### `spec-refreeze`：規格修訂後重記摘要（OBS-SI-108／F-17）

**為什麼**：規格在 `IMPLEMENTATION → SPEC_AUDIT` 被合法修訂後，FSM 只能出邊到 `PR_REVIEW`，而 `spec-frozen` 只在
HUMAN_PENDING 合法，於是 `frozen_stages[*].spec_doc_digests` 停在修訂前的值——AutoClaude 的凍結閘（`check_digest`
拋 `SpecDigestMismatchError`）、Bridge 的 409 比對與人讀狀態檔都會判不符。`spec-refreeze` 在**不經 HUMAN_PENDING** 的
前提下，以**追加**一筆 `kind: refreeze` 條目重新背書修訂後的文件（舊條目不改、留作歷史）。

🔴 **只重記「已被合法修訂、且你確實審過」的文件**：重記＝把「這份檔的現況」記成新的凍結摘要，不是例行動作；`--approver`
規格同 `spec-frozen`（非空、≤100 字、不含控制字元），填負責核准這次修訂的人。沒被 `--doc` 點名的文件仍沿用先前條目的
摘要（它們這次沒被重新檢視——若被改過仍會判不符，這是設計）。**時機**：SPEC_AUDIT 期間改完規格，在離開 SPEC_AUDIT
（`transition --to PR_REVIEW`）**之前**重記最省事；離開之後到 RELEASE_READY 之前的各態都不合法。

PowerShell：

```powershell
Push-Location "<SDD 版本目錄>" -ErrorAction Stop; python -m tools.fsm_runtime.fsm_runtime spec-refreeze --project "<鍵>" --doc "docs/03_testing/contracts/TCS-<Feature>-<date>.md" --doc "<其他修訂過的文件相對路徑>" --root "<專案根>" --reason "<修訂內容；發生在哪個狀態／commit>" --approver "<核准者>"; Pop-Location
```

bash／zsh：

```bash
cd "<SDD 版本目錄>" && python -m tools.fsm_runtime.fsm_runtime spec-refreeze --project "<鍵>" --doc "docs/03_testing/contracts/TCS-<Feature>-<date>.md" --doc "<其他修訂過的文件相對路徑>" --root "<專案根>" --reason "<修訂內容；發生在哪個狀態／commit>" --approver "<核准者>"
```

| 旗標 | 說明 |
|---|---|
| `--project` | **必填**，不退回 `SDD_PROJECT`／目錄名推導（退回的專案鍵一次手滑就改到別的專案，框架自身的專案鍵也是合法專案）；缺＝rc 2 |
| `--doc`（可重複） | 本次重新背書的文件；路徑規則與摘要演算法同 `spec-frozen --digest`；至少一個（否則 rc 4） |
| `--root` | 同 `spec-frozen --digest`（省略時由狀態目錄推導；自訂 `SDD_STATE_DIR` 落在慣例之外時請顯式給） |
| `--reason` | **必填**（strip 後非空，否則 rc 4）；寫明修訂內容與修訂發生在哪個狀態／commit；原文寫進 `decision_trace`（`from`＝`to`＝當前狀態、`trigger: spec_refreeze`） |
| `--approver` | 選填；寫入新條目的 `approved_by`（只在有值時才出現這個鍵） |
| 不收 `--stage` | 重記條目的 `stage` 取最近一筆凍結條目的 stage（所以每階段 auto-compact 上限不被洗掉）；給了＝用法錯誤 rc 2。`--digest`／`--json` 不需要（摘要恆算、輸出恆為單行 JSON） |

- **合法狀態只有 `SPEC_AUDIT`、`RELEASE_READY`、`RELEASE`**（後兩者＝發布後的文字勘誤）；其餘狀態 rc 3
  `transition_not_allowed`（訊息列出合法狀態）。從未凍結過（`frozen_stages` 為空）也是 rc 3：重記是重新背書一次既有的凍結，
  第一次凍結走 `spec-frozen`。hooks-ON 時 Rule 9.6 在 RELEASE_READY／RELEASE 擋 `docs/01～03` 的 Write／Edit，所以那兩態的
  文字勘誤要在 hooks-OFF 的視窗改檔；`spec-refreeze` 本身是 CLI，不受此擋。
- **不轉態、不新增邊**（`SDD_FSM.tla` 不受影響），**不歸零任何 retry 計數**、不增 `total_spec_frozen_count`——它不是新的
  SPEC_FROZEN 里程碑，否則會變成洗掉 R-9.1 重試預算的後門。
- **讀端取全部條目的 `spec_doc_digests` 聯集、同鍵後者勝出**（AutoClaude `check_digest`、Bridge 皆然），不要只讀
  `frozen_stages[-1]`（重記條目只含被點名的文件）。成功輸出：`{"ok":true,"verb":"spec-refreeze",…,"refrozen":true,"stage":…,
  "supersedes":…,"spec_doc_digests":{…}}`。
- 先驗前置（狀態與舊凍結，所以狀態不對時根本不讀檔）、再算摘要、最後才改狀態；任何失敗都不動狀態檔位元組。完整欄位與
  rc 見 `tools/fsm_runtime/README.md`〈規格修訂後重記摘要〉。

---

## 🔷 增量（delta）條款（G-10／D-115-07）

> 增量條款：變更限於已凍結系統的單一 Feature 時，SCG-0～3 各清單項可用「追溯 ID＋已凍結上位文件路徑與凍結摘要」滿足，於 TCS 檔頭〈增量追溯表〉逐項列出，免重寫整份。增量文件集＝FRD-lite（US／AC 併入 TCS 檔頭）＋TCS。僅新架構決策才另立 ADR，僅對外 API／事件契約變更才另附 OpenAPI delta。引用不得指向未凍結文件；未列入追溯表視為未滿足。

怎麼用：

- **適用範圍**：「已凍結系統」＝其上位文件（PRD／FRD／SRD／C4／ADR／OpenAPI）已通過 SCG 並經人類確認、列在
  `frozen_stages[*].spec_docs`。全新系統、跨 Feature 變更、或要改動已凍結上位文件本身者**不適用**，走下方完整清單。
- **棕地基線採納（前置）**：既有專案的上位文件從未走過 SCG、FSM 裡沒有任何凍結紀錄時，先把它們以 Stage-1 記成「已凍結」，
  才有可被增量條款引用的對象。程序（五次 `transition` ＋ `spec-frozen --stage Stage-1 --digest`）、reason 慣例
  「baseline adoption；SCG 未重跑」、追溯表標 `ADOPTED`、approver 慣例、三個子專案各自的上位文件清單，見
  [SDD_AUTOCLAUDE_BRIDGE.md](../sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md) §8.4。採納**不等於**重跑 SCG：它只把「人類確認過這批
  文件的現況」記進 FSM，讓後續的凍結綁內容（摘要）有基準。
- **〈增量追溯表〉**（放在 TCS 檔頭，模板見 `docs_template/sdd/testing/TEST-CONTRACT-SPEC-TEMPLATE.md`）：每個
  SCG-0～3 清單項一列，欄位＝清單項／追溯 ID／已凍結上位文件路徑／凍結摘要（`sha256:…`，取自該文件在
  `frozen_stages[*].spec_doc_digests` 的值，`show` 可查）。
- **免重寫不等於免列**：沒有新決策／沒有對外契約變更時，ADR、OpenAPI 清單項仍要列——追溯到**既有**已凍結的
  ADR／OpenAPI（路徑＋摘要）；沒列進追溯表＝未滿足，省略不是 N/A（防「判斷型 skill 把條款讀成放水」的結構性回應）。
- **引用的凍結狀態可機械查**：被引用文件必須出現在 `frozen_stages[*].spec_docs`（有 `--digest` 時另有摘要）；
  不在其中＝引用未凍結文件，視為未滿足。
- 增量文件集（FRD-lite＋TCS）本身仍照常走 `SCG_VALIDATION` → 人類確認 → `spec-frozen --digest`（TCS 必須在 `--doc`
  內）；SCG-4～6 的清單**不因增量而縮減**。
- 同一條款另見 `/sdd-gate`、`/spec-compliance-check` 兩支 skill（檢查表各引用一次）。

---

## ✅ 閘門通過標準

### SCG-0（Requirement Spec Gate）
- [ ] PRD 已完成（業務目標、範疇、假設）
- [ ] FRD 所有欄位完整（F/US/AC 格式規範）
- [ ] 每個 User Story 有可測試 AC（Given/When/Then）
- [ ] 追溯鏈：EPIC → F → US → AC 完整
- [ ] 使用標準 ID 格式（EPIC/F/US/AC）
- [ ] SLV 前置驗證通過（SLV-001~003）
- [ ] **Ambiguity Gate 通過**：所有 AC ambiguity score < 0.4，或例外項已建立 AMBIGUITY-WAIVER（Phase G M3 / Rule 9.16）

### SCG-1（Design Spec Gate）
- [ ] SRD 完整定義系統設計
- [ ] API Spec 草稿已完成（端點清單）
- [ ] NFR 規格化（效能/安全/可用性目標量化）
- [ ] 技術選型有合理依據

### SCG-2（Architecture Spec Gate）
- [ ] SRD 完整定義系統架構
- [ ] C4 Context + Container 圖已產出
- [ ] 所有重大架構決策有對應 ADR
- [ ] Trust Boundary Map 已定義（安全場景必備）

### SCG-3（API Contract Gate — Contract Freeze）
- [ ] 使用 OpenAPI 3.1 格式
- [ ] 所有端點已定義 Request/Response Schema
- [ ] 安全機制已定義（securitySchemes）
- [ ] 追溯至 US/AC（x-aisdlc.related_us 欄位）
- [ ] SLV 前置驗證通過（SLV-004~006）

### SCG-4（PR Review Gate）
- [ ] 實作符合 SCG-3 凍結的 API Contract
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 無 OWASP Top 10 安全漏洞
- [ ] Code Review 通過（由 dev-senior 或 tech-lead 確認）
- [ ] 無 TODO/FIXME 殘留

### SCG-5（RTM Completeness Gate）

> 🔴 **R85／DEF-200-081② 訂正：本清單原本與同檔閘門表互斥。**
> **被訂正的原文逐字保留（訂正協議：禁止靜默覆寫）**：`- [ ] AT 覆蓋率 ≥ 80%（EPIC → F → US → AC → AT）`。
>
> **為何判定它是那個假的**（兩個數字是否在講同一個量：**是**，兩者都指
> `EPIC → F → US → AC → AT` 這條追溯鏈的覆蓋率）：
> ① **同一份清單的上一行**逐字寫「RTM 中所有 AC 均有對應 AT」＝100%，與 ≥80% 直接矛盾；
> ② 同檔閘門表那一列寫「交付前（**RTM 100% 覆蓋**）」；
> ③ 框架自己的模板 `docs_template/sdd/testing/TEST-STRATEGY-SPEC-TEMPLATE.md` 逐字寫
>    「RTM AC→AT 覆蓋率 **100%**」；`guides/system/sdd/SDD_GUIDE.md` 的閘門表同樣寫 100%；
> ④ 閘門名就是 **Completeness** Gate；全樹另有 10 餘處 skills／規則寫「RTM 100%」，
>    而 **≥80% 全樹只出現在這一行**（實測；對照組「RTM 100%」同掃描命中 14 檔
>    ⇒ 命中 1 是「真的只有一處」不是「查不到」）。
> ⑤ 最可能的來源：**上一節 SCG-4 的「單元測試覆蓋率 ≥ 80%」**——那是**程式碼**覆蓋率，
>    與追溯鏈覆蓋率是兩個量，數字漏到了這一節。
>
> **與 `cicd/SDD_TESTING_CICD.md` 的 90% 不是同一個角色、刻意不動它**：該處是
> 「RTM AT 覆蓋率 < 90% → **警告（不阻擋）**」的 CI 早期預警訊號，不是閘門放行條件；
> 閘門條件恆為本節的 100%。兩者若被讀成競爭關係即為誤讀。

- [ ] RTM 中所有 AC 均有對應 AT
- [ ] AT 覆蓋率 100%（EPIC → F → US → AC → AT）——與上一行是同一個量，兩者必須同時成立
- [ ] 所有 AT 測試結果記錄完整（Pass/Fail）
- [ ] 未通過項目有對應 Bug Report 並已修復

### SCG-6（Release Gate）
- [ ] SCG-0 ~ SCG-5 全部通過確認
- [ ] 生產環境部署計畫已完成
- [ ] Rollback 計畫已定義
- [ ] 監控告警已配置（SLO 告警閾值）

---

## 📂 相關文件

- [SDD 核心原則](../../guides/system/sdd/SDD_Core_Principles.md)
- [ADR 範本](../../docs_template/sdd/adr/ADR-TEMPLATE.md)
- [RTM 範本](../../docs_template/sdd/testing/RTM-TEMPLATE.md)
- [API Contract 範本](../../docs_template/sdd/api/CONTRACT-TEMPLATE.yaml)
- [SDD_FSM_ENGINE.md](../sdd-fsm-engine/SDD_FSM_ENGINE.md) — FSM 狀態機（retry_limit 定義）
- [SDD_ESCALATION_PROTOCOL.md](../sdd-escalation/SDD_ESCALATION_PROTOCOL.md) — 退場機制
- [spec-logical-validator SKILL](../../.claude/skills/spec-logical-validator/SKILL.md) — SLV 邏輯驗證
- [stage-compaction SKILL](../../.claude/skills/stage-compaction/SKILL.md) — SPEC_FROZEN 後壓縮
