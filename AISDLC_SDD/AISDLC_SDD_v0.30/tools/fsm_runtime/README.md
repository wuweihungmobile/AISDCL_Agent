# FSM Runtime（Phase D ACT-010）

將 `SDD_FSM_ENGINE.md` 的狀態機定義升級為可執行引擎，供 `.claude/hooks/` 與外部驅動者（SDD session 的人、
AgentConsole 的 Bridge）調用。

## 安裝

```bash
pip install pyyaml
```

## CLI 用法

**執行位置＝版本目錄**（`AISDLC_SDD_v<LATEST>/`，LATEST 現查 `python AISDLC_SDD/scripts/sdd_version.py`），入口
`python -m tools.fsm_runtime.fsm_runtime <子命令> [旗標]`。

```bash
# bash／zsh
cd "<版本目錄>" && python -m tools.fsm_runtime.fsm_runtime show --project my-proj
```

```powershell
# PowerShell（鐵律：不用裸 cd；Push-Location／Pop-Location 在同一次呼叫內成對）
Push-Location "<版本目錄>"; python -m tools.fsm_runtime.fsm_runtime show --project my-proj; Pop-Location
```

### 環境變數：狀態目錄與專案（ADR-XPLAT-016 §3）

| 變數 | 語意 | 未設時 |
|------|------|--------|
| `SDD_STATE_DIR` | 狀態目錄的**唯一解析點** `state_loader.state_dir()`：放 `FSM-STATE-*.yaml` 與同目錄衍生物（`CONTEXT-LEDGER-*`、`MONITOR-VIOLATION-*`、`PBS-DRIFT-*`、`SUBAGENT-BYPASS-*`…）。**必須是絕對路徑**（相對路徑 ⇒ `ValueError`／CLI rc 4，因為同一個變數在 Bridge、hook、人的 shell 會指向不同目錄＝檔案分裂）。非空白＝**外部專案模式**：規則命中遙測（`fire_count`／`catch_count`）預設**關**——否則外部專案的每次轉態都會弄髒本版目錄內被 git 追蹤的 `governance/rules/*.yaml`；顯式 `SDD_ENABLE_RULE_FIRE_TELEMETRY／…CATCH…` 仍優先 | `<版本目錄>/build/reports/fsm` |
| `SDD_PROJECT` | FSM 專案鍵（原名或淨化後的檔名幹皆可）；純空白視同未設 | 版本目錄上一層的目錄名 |

### 子命令（共 15 個）

| 子命令 | 必要旗標 | 作用 |
|--------|----------|------|
| `show` | — | 印出完整狀態（縮排 JSON） |
| `transition` | `--to` | 狀態強制轉換（僅用於恢復）；印 `OK transitioned to <state>` |
| `gate` | `--gate`、`--result PASS｜FAIL` | 記錄閘門結果（重試計數、ESCALATION、自動有界恢復）；印 JSON。`--gate RELEASE_READY --result FAIL` 另須 `--reason`（見〈發布關卡回邊〉） |
| `reconcile` | — | 消費 `CI-EVENT-*.yaml` |
| `spec-audit` | — | 記錄一次 SPEC_AUDIT |
| `spec-frozen` | `--stage` | 記錄 SPEC_FROZEN（見下節的 `--digest`／`--json` 擴充）；印 `OK spec frozen: <stage>` |
| `spec-refreeze` | `--project`、`--doc`（可多個）、`--reason` | 規格在 SPEC_AUDIT／RELEASE_READY／RELEASE 被合法修訂後，**追加**一筆重記條目重記摘要，不轉態（見〈規格修訂後重記摘要〉）；單行 JSON |
| `check-impl` | — | 檢查 IMPLEMENTATION budget |
| `complete-auto-compact` | — | AUTO_COMPACT_PENDING 收尾：回 resume_state、歸零當日帳本 |
| `reset-ledger` | — | 只歸零當日 `CONTEXT-LEDGER` |
| `resume-from-escalation` | `--to`、`--reason` | **人工**恢復 ESCALATION（`--to` ∈ SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW；Bridge 與 Console 不提供此動詞） |
| `negotiate-enter` | `--project`、`--reason`（選填 `--contract-ref`） | SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED（Rule 9.20.2 談判閘）；已在該態＝`noop` |
| `negotiate-exit` | `--project`、`--outcome agreed｜underspecified`、`--reason` | TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION（agreed）／SPEC_DRAFTING（underspecified） |
| `delegate-enter` | `--project`、`--reason`（選填 `--playbook-ref`，慣例 `run:<run_id>`） | IMPLEMENTATION → AUTOCLAUDE_DELEGATED；已在該態＝`noop`（不寫 trace、不更新 tracking） |
| `delegate-exit` | `--project`、`--decision done｜failed`、`--reason` | AUTOCLAUDE_DELEGATED → IMPLEMENTATION（`done`＝**交還控制權、未升級**，不是「成功」）／ESCALATION（`failed`）；兩者都**不清除** `autoclaude_delegated_tracking` |

通用旗標：`--project`（缺省讀 `SDD_PROJECT`）、`--reason`、`--must-exist`（見下）。

### 橋接契約（四個新動詞、`spec-refreeze` 與 `spec-frozen --json／--digest`；ADR-XPLAT-016 §4）

AgentConsole 的 Bridge 以子行程呼叫本 CLI 寫 FSM（Rule 9 絕對禁令 #1：一切寫入只經 `FSMRuntime`），所以失敗必須有
「可程式辨識」的形態：

- **stdout 恰好一行 JSON**（`ensure_ascii=True`、緊湊分隔）。成功 `{"ok":true,"verb":…,"project":…,"from_state":…,"current_state":…,<動詞專屬欄>}`；
  失敗 `{"ok":false,"error":<代碼>,"detail":<ASCII ≤200 字>,"current_state"?:…}`，並在 **stderr** 印一行 ASCII
  `[SDD-FSM] <動詞> failed: <代碼>: <detail>`（成功時 stderr 為空）。
- **動詞專屬輸出欄**：`negotiate-enter`／`delegate-enter`＝`entered`、`from`、`to`（`noop` 時 `noop`、`current`）；
  `negotiate-exit`＝`exited`、`outcome`、`to`；`delegate-exit`＝`exited`、`decision`、`to`；
  `spec-frozen`＝`stage`、`spec_doc_digests`（有 `--digest` 時）；
  `spec-refreeze`＝`refrozen`、`stage`、`supersedes`、`spec_doc_digests`。
- **四個新動詞與 `spec-refreeze` 恆視為已帶 `--must-exist`**，且 `--project` 與 `--reason` 必填（strip 後非空；
  它是寫進 `decision_trace` 的稽核憑證）。`spec-refreeze` 不是 Bridge 呼叫的動詞（主控／人用），但同樣是「事後補寫
  稽核憑證」的寫入動詞，缺 `--project` 會退回 `SDD_PROJECT`／目錄名推導的專案鍵，一次手滑就改到別的專案，所以比照辦理。
- 舊動詞不帶新旗標時輸出與 rc **逐字不變**（`transition` 的 `OK transitioned to …`、非法轉態 traceback＋rc 1 等）。

| rc | 意義 | stdout `error` |
|----|------|----------------|
| 0 | 成功（含 `"noop":true`） | — |
| 1 | 非預期例外（traceback；舊動詞的非法轉態也是 1） | — |
| 2 | argparse 用法錯誤（缺 `--project`／`--decision`／`--outcome`、`choices` 不符、`spec-refreeze` 給了 `--stage`）；stdout 無 JSON | — |
| 3 | 前置狀態不符／轉態不合法（`TransitionError`） | `transition_not_allowed`（附 `current_state`） |
| 4 | 參數值不合法（`--reason` 空、`--approver` 不合格、`--root` 非絕對／非目錄、`--digest`／`spec-refreeze` 沒給 `--doc`、`SDD_STATE_DIR` 寫成相對路徑；文件類見下節） | `invalid_argument`、`doc_not_found`、`doc_outside_root`、`doc_too_large`、`doc_not_utf8` |
| 5 | 狀態檔不存在（`--must-exist`，**不建檔**）或不可讀（壞 YAML 且 `.bak` 也壞） | `state_not_found`、`state_unreadable` |

`--must-exist` 是全域旗標：現行 `show`／`transition` 對不存在的專案會**自動建出 INIT 狀態檔**，帶了它就改成 rc 5。

### 凍結綁內容：`spec-frozen --digest`（ADR-XPLAT-016 §4.3）

```bash
python -m tools.fsm_runtime.fsm_runtime spec-frozen --project my-proj --stage Stage-3 --must-exist \
  --digest --json --root /path/to/project --approver alice --reason "console-freeze approver=alice; reason=ok" \
  --doc docs/03_testing/contracts/TCS-Feature-2026-10-17.md
```

- **不帶 `--digest`＝現行行為**（不查檔、不算摘要、`spec_docs` 照字面記）。
- 帶 `--digest`：每份 `--doc` 的摘要寫進 `frozen_stages[-1].spec_doc_digests`（`{POSIX 相對 root 的路徑: "sha256:<64 位小寫 hex>"}`），
  `--approver` 寫進 `approved_by`；`--reason` 成為 `decision_trace` 的 reason（缺省 `Stage frozen: <stage>`）。兩個新鍵**只在有值時才出現**。
- **摘要演算法**：`sha256` over **換行正規化後的 UTF-8 bytes**（`\r\n`→`\n`、再 `\r`→`\n`；BOM 不剝），與 AutoClaude adapter 的
  `SddSpec.digest` 逐位元相同。Windows 編輯器存成 CRLF 是常態，用原始 bytes 會讓每次比對假紅。檔案必須是合法 UTF-8。
- **路徑**：`--doc` 絕對或相對（相對＝相對 `--root`）；`resolve()`（跟隨連結）後必須落在 `--root` 之下；`--root` 省略時，狀態目錄
  以 `build/reports/fsm` 結尾則取其上三層、否則取框架自身專案根（自訂 `SDD_STATE_DIR` 又未給 `--root` 時 `doc_not_found` 會大聲失敗）。
  單檔上限 16 MiB。
- **先驗前置、再算摘要、最後才改狀態**：前置狀態不合法（rc 3）或任何一份文件有問題（rc 4）時，狀態檔位元組不變。

### 規格修訂後重記摘要：`spec-refreeze`（OBS-SI-108／F-17）

**為什麼**：功能鍵在 `IMPLEMENTATION→SPEC_AUDIT` 修訂規格後只能出邊到 `PR_REVIEW`，而 `spec-frozen` 只在 HUMAN_PENDING
合法，所以 `frozen_stages[*].spec_doc_digests` 永遠停在修訂前的值；之後每個消費凍結摘要的面（AutoClaude adapter 的
`check_digest` 會拋 `SpecDigestMismatchError`、人讀狀態檔）都判不符。本動詞在**不經 HUMAN_PENDING** 的前提下重新背書。

```bash
python -m tools.fsm_runtime.fsm_runtime spec-refreeze --project my-proj --root /path/to/project \
  --approver alice --doc docs/03_testing/contracts/TCS-Feature-2026-10-17.md \
  --reason "SPEC_AUDIT 期間改了 TCS §3 路徑字面（commit abc123）"
```

- **只在 `SPEC_AUDIT`（規格修訂的正規所在）與 `RELEASE_READY`／`RELEASE`（發布後的文字勘誤）合法**；其餘狀態一律 rc 3
  `transition_not_allowed`（訊息列出合法狀態）。SPEC_DRAFTING／HUMAN_PENDING 的修訂之後本來就要走 `spec-frozen` 人工閘；
  IMPLEMENTATION 起 R-9.6 禁止改規格，沒有「合法修訂」可重記。從未凍結過（`frozen_stages` 為空）也是 rc 3：重記是重新背書
  一次既有的凍結，第一次凍結走 `spec-frozen`。**不新增狀態、不新增邊**（`SDD_FSM.tla` 不受影響）。
- **只追加、不改寫**：在 `frozen_stages` 末尾追加一筆，舊條目逐欄不變、留作歷史。新條目欄位：`stage`（取最近一筆的 stage，
  所以每階段 auto-compact 上限不會被洗掉）、`frozen_at`、`spec_docs`、`spec_doc_digests`（摘要演算法與路徑規則同上節）、
  `approved_by`（有 `--approver` 才出現）、`kind: refreeze`、`supersedes`（被取代那一筆的 `frozen_at`）、`reason`。
  **沒有 `kind` 鍵的舊格式條目一律視為凍結**（`state_loader.freeze_entry_kind`），既有狀態檔不必手改。
- **讀端取全部條目的 `spec_doc_digests` 聯集、同鍵後者勝出**（AutoClaude `check_digest`、Bridge 皆然），**不要只讀
  `frozen_stages[-1]`**：重記條目只含這次被 `--doc` 點名重新背書的文件，沒被點名的仍沿用先前條目的摘要（誠實的稽核軌跡：
  它們這次沒被重新檢視）。
- **不碰任何 retry 計數與 `total_spec_frozen_count`**：重記不是新的 SPEC_FROZEN 里程碑，否則它會變成洗掉 R-9.1 重試預算的後門。
- 參數：`--project`（必填、不退回環境變數）、`--doc`（至少一個）、`--reason`（必填；寫明修訂內容與發生在哪個狀態／commit，
  原文進 `decision_trace`：`from`＝`to`＝當前狀態、`trigger: spec_refreeze`）、`--approver`、`--root`（同 `spec-frozen --digest`）。
  摘要恆算、輸出恆為單行 JSON，所以 `--digest`／`--json` 不需要（給了無妨）；不收 `--stage`（給了是用法錯誤）。
- 同 `spec-frozen` 的順序：先驗前置（狀態與舊凍結，所以狀態不對時根本不讀檔）、再算摘要、最後才改狀態；任何失敗都不動狀態檔位元組。

### 發布關卡回邊：`RELEASE_READY → IMPLEMENTATION`（OBS-SI-117）

**為什麼**：雲端 CI 在 RELEASE_READY（SCG-6）才紅時，此前唯一出邊是 `RELEASE`，沒有合法回邊，功能鍵只能以「鍵外的維護
commit」修。現在可以有界地退回 IMPLEMENTATION 修：

```bash
python -m tools.fsm_runtime.fsm_runtime gate --project my-proj --gate RELEASE_READY --result FAIL \
  --reason "root-infra-ci ubuntu 夾具競態（run 123）"
```

- **有界**：`RETRY_LIMITS["RELEASE_READY"]=2`，語意同 `RTM_VERIFY`（`limit` 次失敗即 ESCALATION）——第 1 次失敗退回 IMPLEMENTATION
  並計數 +1，第 2 次失敗 → ESCALATION。`SDD_FSM.tla` 以 `GateRetry`／`GateExhaust` 建模並經 TLC 驗證。回到 IMPLEMENTATION 後
  走既有路徑（`PR_REVIEW`→`RTM_VERIFY`→`RELEASE_READY`），計數不被兩關的 PASS 洗掉；新一輪 `spec-frozen` 才歸零。
- **理由必填**（`gate --gate RELEASE_READY --result FAIL` 缺 `--reason` ＝ rc 2；API 層 `ValueError`），其他 gate 維持既有「理由可省」。
- **不可自動恢復**：RELEASE_READY 刻意不在 `auto_recovery` 的可恢復白名單——發布關卡連續失敗屬結構性問題，耗盡後停在已落盤的
  ESCALATION 等人（`resume-from-escalation`）。`gate --gate RELEASE_READY --result PASS` 轉 RELEASE 並歸零計數
  （效果同既有的 `transition --to RELEASE`，但留下 `gate_pass` 軌跡）。
- 裸 `transition --to IMPLEMENTATION` 也合法（邊在 `_HAPPY_PATH`），但它不記次數，只用於恢復；要有界請走 `gate`。
- 既有狀態檔沒有 `retry_history.RELEASE_READY` 區塊也無妨：讀端預設計數 0，第一次 FAIL 時自動建出。
- 順手修的既有缺陷：`record_gate_result` 的耗盡分支此前不存檔（只有 `enter_auto_recovery` 內的轉態碰巧會存），所以
  `SDD_ENABLE_AUTO_RECOVERY=0` 或 gate 不在可恢復白名單時，CLI 印出 `escalated: true` 但磁碟上的狀態檔原封不動——現在耗盡當下就落盤。

## Python API

```python
from tools.fsm_runtime import FSMRuntime

runtime = FSMRuntime.bootstrap()  # 從 $SDD_PROJECT 讀 project 名、從 $SDD_STATE_DIR（缺省版本目錄）讀狀態
runtime.assert_tool_allowed("Write", "docs/01_requirements/FRD-X.md")
runtime.record_gate_result("SCG_VALIDATION", "FAIL", reason="SLV-002")
runtime.reconcile_ci_events()
```

## 測試

```bash
python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q   # 在版本目錄下；ci-gate 的 LATEST 軌即此指令
```

測試套有 session 級沙盒（`tests/conftest.py`）：清掉 `SDD_STATE_DIR`／`SDD_PROJECT` 並把狀態、帳本、漂移、旁路目錄導向暫存目錄，
整套跑完 `build/reports/` 不得出現任何新檔或內容變動。

## 檔案結構

- `state_loader.py` — 讀寫 `FSM-STATE-{project}.yaml`（含 atomic write + .bak）；`state_dir()` 狀態目錄唯一解析點；
  `frozen_stages` 的寫入（`record_spec_frozen`／`record_spec_refreeze`）與 `freeze_entry_kind`（無 `kind` 鍵＝凍結）
- `transition_rules.py` — 轉換規則與 retry 上限（與 `SDD_FSM_ENGINE.md`、`formal/SDD_FSM.tla` 同步）
- `event_reconciler.py` — 消費 `CI-EVENT-*.yaml`
- `fsm_runtime.py` — Facade 與 CLI（15 個子命令）
- `spec_digest.py` — `spec-frozen --digest`／`spec-refreeze` 的純函式：換行正規化摘要、路徑正規化、超限判斷
- `formal/SDD_FSM.tla` — 狀態機的 TLA+ 規格（五軌之一；`_HAPPY_PATH` 一改必須同步並重跑 TLC，見 `formal/README.md`）
- `tests/test_transitions.py` — 覆蓋所有 happy-path + error-path 轉換
- `tests/test_cli_bridge_verbs.py`、`tests/test_sdd_state_dir.py`、`tests/test_spec_digest.py` — 橋接契約與環境契約的守護測試
- `tests/test_spec_refreeze.py`、`tests/test_release_ready_backedge.py` — `spec-refreeze`（OBS-SI-108）與 RELEASE_READY 回邊（OBS-SI-117）的守護測試

## 與 SDD_FSM_ENGINE.md 同步驗證

`tests/test_md_python_sync.py` 會 parse 文件中的「狀態轉換表」section，驗證 Python 規則與文件一致；
`tests/test_tla_python_sync.py` 對 `formal/SDD_FSM.tla` 做同一件事（配對層）。邊的**形狀**（例如回邊必須是有界的
`GateRetry` 而不是無界的 `Move`）另由 `tests/test_release_ready_backedge.py` 釘住。
