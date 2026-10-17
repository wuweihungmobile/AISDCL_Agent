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

### 子命令（共 14 個）

| 子命令 | 必要旗標 | 作用 |
|--------|----------|------|
| `show` | — | 印出完整狀態（縮排 JSON） |
| `transition` | `--to` | 狀態強制轉換（僅用於恢復）；印 `OK transitioned to <state>` |
| `gate` | `--gate`、`--result PASS｜FAIL` | 記錄閘門結果（重試計數、ESCALATION、自動有界恢復）；印 JSON |
| `reconcile` | — | 消費 `CI-EVENT-*.yaml` |
| `spec-audit` | — | 記錄一次 SPEC_AUDIT |
| `spec-frozen` | `--stage` | 記錄 SPEC_FROZEN（見下節的 `--digest`／`--json` 擴充）；印 `OK spec frozen: <stage>` |
| `check-impl` | — | 檢查 IMPLEMENTATION budget |
| `complete-auto-compact` | — | AUTO_COMPACT_PENDING 收尾：回 resume_state、歸零當日帳本 |
| `reset-ledger` | — | 只歸零當日 `CONTEXT-LEDGER` |
| `resume-from-escalation` | `--to`、`--reason` | **人工**恢復 ESCALATION（`--to` ∈ SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW；Bridge 與 Console 不提供此動詞） |
| `negotiate-enter` | `--project`、`--reason`（選填 `--contract-ref`） | SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED（Rule 9.20.2 談判閘）；已在該態＝`noop` |
| `negotiate-exit` | `--project`、`--outcome agreed｜underspecified`、`--reason` | TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION（agreed）／SPEC_DRAFTING（underspecified） |
| `delegate-enter` | `--project`、`--reason`（選填 `--playbook-ref`，慣例 `run:<run_id>`） | IMPLEMENTATION → AUTOCLAUDE_DELEGATED；已在該態＝`noop`（不寫 trace、不更新 tracking） |
| `delegate-exit` | `--project`、`--decision done｜failed`、`--reason` | AUTOCLAUDE_DELEGATED → IMPLEMENTATION（`done`＝**交還控制權、未升級**，不是「成功」）／ESCALATION（`failed`）；兩者都**不清除** `autoclaude_delegated_tracking` |

通用旗標：`--project`（缺省讀 `SDD_PROJECT`）、`--reason`、`--must-exist`（見下）。

### 橋接契約（四個新動詞與 `spec-frozen --json／--digest`；ADR-XPLAT-016 §4）

AgentConsole 的 Bridge 以子行程呼叫本 CLI 寫 FSM（Rule 9 絕對禁令 #1：一切寫入只經 `FSMRuntime`），所以失敗必須有
「可程式辨識」的形態：

- **stdout 恰好一行 JSON**（`ensure_ascii=True`、緊湊分隔）。成功 `{"ok":true,"verb":…,"project":…,"from_state":…,"current_state":…,<動詞專屬欄>}`；
  失敗 `{"ok":false,"error":<代碼>,"detail":<ASCII ≤200 字>,"current_state"?:…}`，並在 **stderr** 印一行 ASCII
  `[SDD-FSM] <動詞> failed: <代碼>: <detail>`（成功時 stderr 為空）。
- **動詞專屬輸出欄**：`negotiate-enter`／`delegate-enter`＝`entered`、`from`、`to`（`noop` 時 `noop`、`current`）；
  `negotiate-exit`＝`exited`、`outcome`、`to`；`delegate-exit`＝`exited`、`decision`、`to`；
  `spec-frozen`＝`stage`、`spec_doc_digests`（有 `--digest` 時）。
- **四個新動詞恆視為已帶 `--must-exist`**，且 `--reason` 必填（strip 後非空；它是寫進 `decision_trace` 的稽核憑證）。
- 舊動詞不帶新旗標時輸出與 rc **逐字不變**（`transition` 的 `OK transitioned to …`、非法轉態 traceback＋rc 1 等）。

| rc | 意義 | stdout `error` |
|----|------|----------------|
| 0 | 成功（含 `"noop":true`） | — |
| 1 | 非預期例外（traceback；舊動詞的非法轉態也是 1） | — |
| 2 | argparse 用法錯誤（缺 `--project`／`--decision`／`--outcome`、`choices` 不符）；stdout 無 JSON | — |
| 3 | 前置狀態不符／轉態不合法（`TransitionError`） | `transition_not_allowed`（附 `current_state`） |
| 4 | 參數值不合法（`--reason` 空、`--approver` 不合格、`--root` 非絕對／非目錄、`--digest` 沒給 `--doc`、`SDD_STATE_DIR` 寫成相對路徑；文件類見下節） | `invalid_argument`、`doc_not_found`、`doc_outside_root`、`doc_too_large`、`doc_not_utf8` |
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

- `state_loader.py` — 讀寫 `FSM-STATE-{project}.yaml`（含 atomic write + .bak）；`state_dir()` 狀態目錄唯一解析點
- `transition_rules.py` — 轉換規則與 retry 上限（與 `SDD_FSM_ENGINE.md` 同步）
- `event_reconciler.py` — 消費 `CI-EVENT-*.yaml`
- `fsm_runtime.py` — Facade 與 CLI（14 個子命令）
- `spec_digest.py` — `spec-frozen --digest` 的純函式：換行正規化摘要、路徑正規化、超限判斷
- `tests/test_transitions.py` — 覆蓋所有 happy-path + error-path 轉換
- `tests/test_cli_bridge_verbs.py`、`tests/test_sdd_state_dir.py`、`tests/test_spec_digest.py` — 橋接契約與環境契約的守護測試

## 與 SDD_FSM_ENGINE.md 同步驗證

`tests/test_md_python_sync.py` 會 parse 文件中的「狀態轉換表」section，驗證 Python 規則與文件一致。
