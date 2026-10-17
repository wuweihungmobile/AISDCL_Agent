# ADR-XPLAT-016：SDD 整合迴圈的最小侵入白名單——環境契約、FSM 窄寫面、凍結綁內容與委派同步

- **狀態**：**Proposed**（SD 設計稿；主控收尾時改 Accepted）。本檔是設計文件，不含任何生產碼；§11 的白名單是施工授權範圍。
- **日期**：2026-10-17
- **平台**：平台中立（Windows 11＋PowerShell 為主控機；Docker 全棧以唯讀掛載 SDD 為第二載具，兩者的取捨逐項寫在各節）
- **關聯**：[AutoSDD_improving_115](../AutoSDD_improving_115.md) §3 G-01～G-17、§6 D-115-01～16；SA 契約 v1.5 的〈待 SD 定案〉S1～S8（`AgentConsole/docs/02_architecture/API_Contract_P3-6.md` §6.8.3，本檔附錄 B 逐項給值）；[ADR-XPLAT-010](ADR-XPLAT-010-root-subproject-boundary.md) §2.1（跨子專案不 import）；`AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md` D22；PRD `docs/01_requirements/Agent_ConsoleUI_PRD.md` §0.4／§0.5；AISDLC_SDD Rule 9（R-9.5／R-9.6／R-9.20／R-9.38）；框架體檢 S-01～S-20（住本輪審查證據檔）
- **修訂對象**：ADR-001 D22 第 3 項③「Console 只讀、不回寫 FSM-STATE」→「Console 只經 FSMRuntime CLI 窄寫」；`NFR-COMPAT-01`「零侵入」→「最小侵入白名單」（RTM 列由主控收尾單人窗口改驗證口徑，不刪列、不改號）
- **證據**：本檔 §2.3 與 §2.4 的兩次乾跑（真 FSM CLI＋FSMRuntime API，Windows 11／Python 3.11.9，HEAD `38e46582`）與 `檔案:行號` 讀碼；乾跑腳本不入庫，兩次的殘檔都已清除。**本檔不含任何 `DEF-` 編號的狀態宣稱**（缺陷入帳由主控收尾）。

> **數字性質**：`〔讀碼〕`＝本輪以 Read／Grep 讀出的 `檔案:行號`（落地時行號會漂，動手前各自重取）；`〔乾跑〕`＝本輪真跑指令的輸出；`〔未驗〕`＝沒有證據、落地時須補驗。版內路徑一律以 SDD LATEST 為基準（`python AISDLC_SDD/scripts/sdd_version.py` 現查，本檔刻意不寫版號）。

---

## 1. 脈絡

improving_115 判定「AISDLC_SDD 已融入系統」為**部分**：引擎面（CLI 路徑）通、Console 路徑只接了「匯入」與「唯讀狀態卡」。掌舵者授權調整 AutoClaude 與 AgentConsole，並要求以最佳化代決。主控裁決 D-115-01～16 已定方向（FSM 寫入只經 CLI、`SDD_STATE_DIR`、單一寫動詞「核准凍結」、Bridge 為委派唯一同步者、最小侵入白名單、`sdd` 區塊伺服端注入；D-115-14 Console 專案為錨；D-115-15 `delegate-exit done`＝交還控制權；D-115-16 AT 文法）。本 ADR 把這些方向細到「開發者不必再猜」：

| 本 ADR 回答 | 一句話 |
|---|---|
| 怎麼讓 SDD 的狀態住在外部專案 | `SDD_STATE_DIR` 唯一解析點；7 個目錄站點收斂，草案 9 檔中 5 檔經讀碼判定不動（§3） |
| Bridge 怎麼安全地寫 FSM | 子行程呼叫 CLI、固定環境、動詞白名單、權杖（§3.5、§9、§10） |
| 凍結憑什麼可信 | 凍結時記內容摘要，編譯與執行前比對，改檔即 fail-closed（§6） |
| 談判閘怎麼對 | Console 簽核匯入草稿＝談判 `agreed`，附誠實註記（§5） |
| 委派狀態怎麼同步、失敗怎麼辦 | 以 `runner.py` 實際分支逐一對映（§10）：完成與取消交還控制權（`done`）、引擎升級走 `failed`、新批次遇舊委派先回收；失敗後人工恢復路徑（§5.3） |
| 專案與 FSM 專案怎麼綁（循環依賴） | Console 專案是錨：`execution_path`＋`sdd_project`（預設＝專案名，Bridge 淨化），匯入帶 `targetProjectId` 併入既有專案（§7.2） |
| AT 文法與逆向 RTM 歸屬 | `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段＝所屬 AC；未編成的出聲、逆向無法歸屬的標 unmapped（§8） |
| 哪些引擎檔可以動 | §11 白名單＋`git diff` 機械核對 |
| SA 契約的 S1～S8 | 附錄 B 逐項給值 |

**不在本 ADR**：HTTP 欄位形狀與錯誤封包細節（SA 契約 v1.5）、前端畫面、`phase` 投影演算法（dogfood 標的）。本 ADR 與草案 §4.3 的差異集中列在附錄 A，主控會轉給 SA。

## 2. 決策總覽與乾跑證據

### 2.1 決策表

| 編號 | 決定（摘要） | 落點（子專案） | 本檔節 |
|---|---|---|---|
| SD-1 | `SDD_STATE_DIR`（外部專案模式＝遙測回寫預設關）、`SDD_PROJECT` 新增 adapter 讀者、Bridge 固定環境 | SDD、AutoClaude、Bridge | §3 |
| SD-2 | CLI 新動詞 `negotiate-enter`／`negotiate-exit`／`delegate-enter`／`delegate-exit`；`spec-frozen` 加 `--digest`／`--root`／`--approver`／`--reason`／`--json`；全域 `--must-exist` | SDD | §4 |
| SD-3 | 談判閘對映（附四條件）、`failed` 後恢復路徑 | SDD、Bridge、Console | §5 |
| SD-4 | 凍結綁內容：摘要演算法、鍵、生產／消費、三點預檢與錯誤對映 | SDD、AutoClaude、Bridge | §6 |
| SD-5 | adapter 以專案選檔（fail-closed）、Console 專案為錨的綁定（D-115-14：`execution_path`＋`sdd_project` 預設＝專案名、匯入帶 `targetProjectId`）、專案名淨化規則 | AutoClaude、Bridge、Backend | §7 |
| SD-6 | AT ID 文法（D-115-16）、「出現卻未編成」出聲（`unmapped_at_ids`；CLI rc 6、Bridge 200＋警告）、`spec_file`、版本與場景宣告、逆向 RTM 歸屬 | AutoClaude、SDD 模板、Bridge | §8 |
| SD-7 | `BRIDGE_SDD_WRITE_TOKEN`（backend 屬性 `console.bridge.sdd-write-token`） | Bridge、Backend、部署 | §9 |
| SD-8 | 委派同步的終態對映（D-115-15：`done`＝交還控制權；取消也 `done`）、下單順序、補償、回收點 | Bridge | §10 |
| SD-9 | 最小侵入白名單與核對法 | AutoClaude、SDD | §11 |
| SD-10 | LATEST 的 PowerShell matcher、記帳分支與 AUTO_COMPACT 放行（防死鎖） | SDD | §12 |
| SD-11 | 增量（delta）條款 | SDD 文件 | §13 |

### 2.2 解讀本檔的三條規則

1. 凡寫成「必須」的是介面契約（跨棒共用，改動要回本檔）；寫成「建議」的是命名與內部結構，各棒可調。
2. 新增檔案一律只寫檔名（不寫完整路徑），所在目錄寫在同一格；已存在的檔才寫版內／repo 相對路徑。
3. 所有「出聲」都指 `IObservabilityPort.record_event`（AutoClaude）或 Bridge 的 `alert`／audit log（Bridge），不得只寫 stderr。

### 2.3 乾跑證據（真 FSM，專案名 `sd-dryrun-<隨機>`，framework 預設狀態目錄，兩個遙測旗標顯式 0）

「現行」＝LATEST 現有 CLI 動詞；「原型」＝以 FSMRuntime 公開 API 包一層、輸出本檔 §4 所定的形狀（驗證轉態合法性與例外型別，不是新程式碼）。

| # | 動作 | rc | 關鍵輸出（逐字或逐值） |
|---|---|---|---|
| 1 | 現行 `transition --to` SCENARIO_DETECT→AGENT_LOAD→SPEC_DRAFTING→SCG_VALIDATION→HUMAN_PENDING | 0×5 | `OK transitioned to <state>` |
| 2 | 現行 `spec-frozen --stage Stage-2 --doc docs/03_testing/contracts/TCS-DRYRUN-NOFILE.md`（該檔**不存在**） | 0 | `OK spec frozen: Stage-2`；`frozen_stages[0]` 只有 `stage／frozen_at／compaction_report:null／spec_docs`——不查檔、無摘要 |
| 3 | 原型 `negotiate-enter`→`negotiate-exit --outcome agreed` | 0／0 | SPEC_FROZEN→TEST_CONTRACT_NEGOTIATED→IMPLEMENTATION；trace `trigger=test_contract_enter／test_contract_exit`、`spec_refs=[<contract_ref>]` |
| 4 | 原型 `delegate-enter`、再一次 `delegate-enter`、`delegate-exit --decision done` | 0／0／0 | IMPLEMENTATION→AUTOCLAUDE_DELEGATED→IMPLEMENTATION；第二次 `"noop":true`；`autoclaude_delegated_tracking={entered_at,resume_state:"IMPLEMENTATION",playbook_ref}` |
| 5 | 現行 `spec-frozen` 於 IMPLEMENTATION | **1** | traceback `TransitionError: transition not allowed: IMPLEMENTATION -> SPEC_FROZEN`；狀態檔雜湊前後相同 |
| 6 | 原型 `negotiate-exit`／`delegate-exit` 於 IMPLEMENTATION | **3** | `{"ok":false,"error":"transition_not_allowed","current_state":"IMPLEMENTATION","detail":"…expected AUTOCLAUDE_DELEGATED"}` |
| 7 | 原型 `delegate-exit --decision failed` | 0 | `current_state=ESCALATION`；`escalation_provenance={"rule_id":"unknown","source":"autoclaude_delegated_failed",…}`；`escalation_history[-1].resolved_at=null`；該筆 trace 顯示 `ESCALATION->ESCALATION trigger=autoclaude_delegated_exit`（`record_escalation` 先改 `current` 的既有行為，`state_loader.py:254-308`） |
| 8 | 原型 `assert-tool`／`delegate-enter` 於 ESCALATION | 3 | `state ESCALATION blocks all tool calls until human intervenes`／`enter_autoclaude_delegated blocked: current=ESCALATION, expected one of ['IMPLEMENTATION']` |
| 9 | 現行 `resume-from-escalation --to IMPLEMENTATION --reason …` | 0 | `{"from":"ESCALATION","via":"RESUME_VERIFICATION","to":"IMPLEMENTATION","resolved_at":…}`＋stderr 一行 ASCII 提醒；`escalation_history[-1].resolution="human_resume → IMPLEMENTATION: …"`；其後原型 `delegate-enter`／`delegate-exit done` 皆 rc 0 |
| 10 | 現行 `transition --to PR_REVIEW` 於 HUMAN_PENDING | **1** | traceback `TransitionError`——現行 CLI 的非法轉態 rc 是 **1，不是 2**（`parser.error` 才是 2） |
| 11 | 現行 `transition --to IMPLEMENTATION` 於 SPEC_FROZEN | 0 | 直達邊可走（`transition_rules.py:35`）⇒ R-9.20.2 沒有機械強制 |
| 12 | 現行 `show --project <不存在>` | 0 | **自動建出 INIT 狀態檔**（`state_loader.py:359-399` `create_if_missing` 預設真）；原型帶 `--must-exist` 對不存在專案 rc 5、未建檔 |
| 13 | CLI 單次呼叫計時（`show`，檔已存在，暖機 3 次） | — | 0.07、0.07、0.07 秒；其餘動詞 0.07～0.11 秒（improving_115 §5.1-6 的「開銷未量測」就此補值） |
| 14 | 每次 `-m tools.fsm_runtime.fsm_runtime` 的 stderr | — | runpy `RuntimeWarning: 'tools.fsm_runtime.fsm_runtime' found in sys.modules…`（`tools/fsm_runtime/__init__.py:12` 匯入了 `.fsm_runtime`）；與成敗無關 ⇒ Bridge 以 `-W ignore::RuntimeWarning` 起、成敗只看 rc＋stdout |

**判讀**：(a) 真 FSM 上「SPEC_FROZEN→（談判）→IMPLEMENTATION→AUTOCLAUDE_DELEGATED→IMPLEMENTATION」與「failed→ESCALATION→人工恢復→再委派」兩條都合法，**不需要改 `_HAPPY_PATH` 或任何 `*.tla`**；(b) 現行 CLI 沒有可程式辨識的失敗形態（非法轉態＝traceback＋rc 1），所以新動詞必須自帶 rc／JSON 契約；(c) `show`／`transition` 會替不存在的專案建檔，Bridge 呼叫必須帶 `--must-exist`。

**另做的原型驗證（合成狀態檔，不入庫）**：§6.2／§7.1 的判定表以十二個案例逐一驗過：①兩專案共處只認被指定者（同例含 `frozen_stages` 聯集後者勝與 CRLF 檔摘要吻合）；②未凍結專案；③不指定且多檔；④指定不存在的專案；⑤欄位反查；⑥⑦非法鍵（路徑分隔符、`..`）；⑧不在凍結清單；⑨改檔不吻合；⑩舊狀態檔無摘要放行；⑪委派態放行；⑫單檔無專案鍵。原型第一版在 Windows 上全數誤判，根因是對 POSIX 字串使用 `os.path.normcase`（會把 `/` 換成 `\`），並暴露了「專案鍵含路徑分隔符」的缺口——兩者都已訂正進 §6.1 與 §7.1，這正是鐵律三（路徑分隔符、大小寫）要自問的那類問題。

### 2.4 乾跑二（D-115-15：委派退出語意、回收點、ESCALATION 恢復前置條件）

同一套做法（真 FSM CLI＋原型動詞、framework 預設目錄、遙測旗標 0、專案名 `sd-dryrun-<隨機>`），四個專案各自先走到 IMPLEMENTATION（含談判進出）再做下列動作；`playbook_ref` 用本檔 §4.4 規定的 `run:<run_id>` 形態。

| # | 動作 | rc | 關鍵輸出（逐值） |
|---|---|---|---|
| 15 | `delegate-exit --decision done --reason "console-run run=RUN1 CANCELLED"`（該委派 `playbook_ref=run:RUN1`） | 0 | AUTOCLAUDE_DELEGATED→IMPLEMENTATION；trace `trigger=autoclaude_delegated_exit`、`reason` 原樣；🔴 `autoclaude_delegated_tracking` **不會被清除**（仍帶 `playbook_ref: run:RUN1`）。其後 `delegate-enter run:RUN2` rc 0 並覆寫 tracking |
| 16 | 回收點：FSM 在 DELEGATED（引用 `run:RUN2`）時 `delegate-exit done`（reason `console-run run=RUN2 RECLAIMED old_status=FAILED by=RUN3`）→ `delegate-enter run:RUN3` | 0／0 | 兩次呼叫合計約 0.17 秒；trace 連續三筆（enter RUN2／exit RECLAIMED／enter RUN3），tracking 換成 `run:RUN3` |
| 17 | `delegate-exit --decision failed --reason "console-run run=RUN4 ENGINE-ESCALATION step=…: retries exhausted"` | 0 | `current_state=ESCALATION`；`escalation_provenance.source=autoclaude_delegated_failed`、`.reason`＝傳入的 reason；`autoclaude_delegated_tracking` 保留（含 `playbook_ref: run:RUN4`，Console 可據此指出哪個 run）；`escalation_history[-1].resolved_at=null` |
| 18 | 在 ESCALATION 再下 `delegate-exit --decision done` | 3 | `{"ok":false,"error":"transition_not_allowed","current_state":"ESCALATION","detail":"exit_autoclaude_delegated called in state=ESCALATION, expected AUTOCLAUDE_DELEGATED"}`——回收只對 AUTOCLAUDE_DELEGATED 成立，ESCALATION 只有人能解 |
| 19 | `resume-from-escalation` 三種前置不備：`--to HUMAN_PENDING`（不在 `RESUME_TARGETS`）、`--reason "  "`、缺 `--reason` | 2／2／2 | argparse 用法錯誤（stderr 一行、stdout 無 JSON）；狀態仍是 ESCALATION、檔案未動 |
| 20 | `resume-from-escalation --to IMPLEMENTATION --reason "human fixed env; retry delegation"` | 0 | `{"from":"ESCALATION","via":"RESUME_VERIFICATION","to":"IMPLEMENTATION","resolved_at":…}`；`escalation_history[-1].resolved_at` 填值、`resolution="human_resume → IMPLEMENTATION: …"`；🔴 `escalation_provenance` 與 `autoclaude_delegated_tracking` **都不會被清除**；其後 `delegate-enter run:RUN5` rc 0 |
| 21 | `delegate-enter` 不帶 `--playbook-ref`／帶 `--playbook-ref manual-note` | 0／0 | tracking 沒有 `playbook_ref` 鍵／`playbook_ref: manual-note`⇒外來（人在 SDD session 進入的）委派可由「鍵缺或不以 `run:` 開頭」辨認（§10.3） |

**判讀**：(a) `done`／`failed` 兩個出口、回收（done＋再 enter）與恢復後再委派都在真 FSM 上合法，仍**不需要改 `_HAPPY_PATH` 或 `*.tla`**；(b) FSM 檔裡的 `autoclaude_delegated_tracking` 與 `escalation_provenance` 是**歷史殘留欄**，不是現況旗標——讀它們之前必須先看 `current_state`（§5.3、§10.3）；(c) 回收的兩步（exit done、enter）不是原子的，兩步之間若 `delegate-enter` 失敗，FSM 停在 IMPLEMENTATION（無委派），新批次整體回 409／5xx 並不 spawn，下一次建立請求會從 IMPLEMENTATION 常態進入，不需要人工。

---

## 3. 跨專案環境契約（SD-1）

### 3.1 環境變數表

| 名稱 | 讀者（證據） | 設定者 | 語意與值域 | 未設時 |
|---|---|---|---|---|
| `SDD_STATE_DIR` | 新增 `state_loader.state_dir()`（現為常數 `state_loader.py:31`）；經它收斂的 7 個目錄站點（§3.4 的 A1～A7） | Bridge（**只給 FSM CLI 子行程，不給引擎子行程**）；人在 SDD session 自行匯出 | **絕對路徑**目錄，放 `FSM-STATE-*.yaml` 與同目錄衍生物（`CONTEXT-LEDGER-*`、`MONITOR-VIOLATION-*`、`PBS-DRIFT-*`、`SUBAGENT-BYPASS-*`、`CI-EVENT-*`、`LEDGER-CALIBRATION-*`、`PREDICTOR-MISS-*`）。非空白＝**外部專案模式** | 行為逐字不變：`<SDD 版本目錄>/build/reports/fsm` |
| `SDD_PROJECT` | 既有 `project_from_env()`（`state_loader.py:435-440`）；**新增** adapter（`sdd_to_playbook_adapter.py` 建構時讀，§7.1） | Bridge（FSM CLI 子行程＋引擎子行程）；人 | FSM 專案鍵。原名或淨化後檔名幹皆可（§7.4）；純空白視同未設 | runtime：退回版本目錄上一層的目錄名；adapter：見 §7.1 |
| `SDD_ENABLE_RULE_FIRE_TELEMETRY`／`SDD_ENABLE_RULE_CATCH_TELEMETRY` | 既有 `fsm_runtime.py:122-144,181-206` | Bridge 固定為 `0` | 顯式值永遠優先（既有契約不變） | 外部專案模式預設關；否則沿用既有預設 |
| `PYTHONPATH`／`PYTHONDONTWRITEBYTECODE`／`PYTHONUTF8` | Python | Bridge（CLI 子行程） | `<SDD 版本目錄>`／`1`／`1` | — |
| `BRIDGE_SDD_WRITE_TOKEN` | Bridge、backend | 部署者（§9） | 寫入面權杖 | 寫入動詞停用（503） |

### 3.2 `state_dir()` 解析優先序（唯一解析點，必須）

| 序 | 來源 | 規則 |
|---|---|---|
| 1 | 呼叫端顯式 `path=`（`load_state(project, path=…)`） | 不經解析點，維持現況（測試與 chaos 載具用） |
| 2 | `SDD_STATE_DIR`（`strip()` 後非空） | 必須是絕對路徑，否則 `ValueError`（**不接受相對路徑**：Bridge 的 cwd 是 SDD 版本目錄、hook 的 cwd 是專案根、人的 cwd 任意，相對路徑會讓同一變數在不同呼叫者指向不同目錄＝靜默的檔案分裂）；不 `resolve()` symlink |
| 3 | 模組常數 `DEFAULT_STATE_DIR` | **呼叫時才讀**模組屬性（既有測試以 monkeypatch 改它，`test_path_cost.py`、`test_phase_i_m5.py` 等依賴這個晚綁定） |

目錄不由解析點建立；`save_state` 本來就 `mkdir(parents=True)`。`FSM-STATE-<名>.yaml` 檔名規則不變（`state_loader.py:77-88`，專案名經共用淨化）。

### 3.3 外部專案模式（`SDD_STATE_DIR` 非空白）的效果

| 效果 | 做法 | 為什麼 |
|---|---|---|
| 規則命中遙測預設關 | `_telemetry_writeback_allowed(explicit_env)`（`fsm_runtime.py:181-206`）在「顯式值」之後、D28 的 hook 身分判定之前，加一條：`SDD_STATE_DIR` 非空白⇒回 False（不出聲） | `rule_loader.record_state_fires`／`record_state_catches` 把 `fire_count／catch_count` 寫回**版本目錄內被 git 追蹤的** `governance/rules/*.yaml`（`rule_loader.py:25,158`）。外部專案的每次轉態都會弄髒框架樹；Docker 唯讀掛載下還會寫入失敗。顯式 `0／1` 仍優先 |
| 狀態與帳本跟著走 | §3.4 的 A1～A7 全經 `state_dir()` | 狀態檔、當日帳本、監控報告同住一個目錄，`complete-auto-compact` 歸零的才是 hook 寫的那本帳 |
| `rule_loader` 讀規則 | 不變（讀版本目錄內的規則，唯讀） | 規則屬框架，不屬專案 |
| 其餘自動行為 | **不變**（自動恢復、規則自演化提議、鷹架代謝仍預設開） | 這些只在 `gate` 失敗、`LEARNING_COMMIT`、`SCAFFOLD_GC` 等 Bridge 不呼叫的動詞下觸發；人在 SDD session 觸發它們時，寫入框架 `build/reports/*` 是**已知邊界**（§14） |
| Rule 9 禁令 #1 | 仍成立 | 一切寫入只經 `FSMRuntime`；Bridge 的**直接讀**沿用 D22（唯讀遙測）；本 ADR 不新增任何直接讀寫 |

### 3.4 全樹掃描與逐檔表

**掃描方法**：對 LATEST 全樹（`*.py` 與全部文件，含 `.claude/hooks`、`.claude/skills`、`workflow/`、`guides/`、`cicd/`、`agent/`、`docs_template/`、`data/`）以五種樣式掃描：`build/reports/fsm`、`reports/fsm`、`DEFAULT_STATE_DIR`／`LEDGER_DIR`／`STATE_DIR`、`"build" / "reports"` 相鄰 token、`FSM-STATE`。LATEST 版本目錄**沒有自己的 `scripts/` 子目錄**；共享腳本在上一層 `AISDLC_SDD/scripts/`，其內的提及全是 docstring 與測試，沒有路徑解析站點。`guides/`、`prompts/`、`scenarios/` 零命中。

**與 Architect 草案的差異**：草案列 9 檔（`conversation_ledger`、`file_lock`、`event_reconciler`、`arch_fitness`、`fsm_runtime`、`production_monitor`、`spec_monitor`、`state_loader`、`trajectory_predictor`）。讀碼後：其中 5 檔**不改**（B1～B4）；4 檔要改（`state_loader`、`fsm_runtime`、`production_monitor`、`spec_monitor`），其中 `fsm_runtime` 草案只憑字面指認、實際要改的是 `:276` 與 `:181-206` 兩處；另補草案漏掉的 3 個檔（兩支 hook、`subagent_contract.py`）。結果＝**7 個目錄站點（A1～A7）＋1 個遙測預設（A8）**，涉及 7 個檔。

**A 類：要改（Dev-SDD-RT 逐檔做；版內相對路徑）**

| # | 站點 | 現況〔讀碼〕 | 做法 |
|---|---|---|---|
| A1 | `tools/fsm_runtime/state_loader.py:31,77-88` | 常數 `DEFAULT_STATE_DIR`；`_default_state_path`／`track_state_path` 讀它 | 新增 `state_dir()`（§3.2）；兩函式改呼叫它；`DEFAULT_STATE_DIR` 常數保留作預設值與測試 monkeypatch 面 |
| A2 | `tools/fsm_runtime/fsm_runtime.py:276` | `_reset_today_ledger` 以 `REPO_ROOT/build/reports/fsm` 找當日帳本 | 改呼叫 `state_dir()`（與 A3／A4 同目錄） |
| A3 | `.claude/hooks/context_ledger_pre.py:66` | `LEDGER_DIR = _SDD_ROOT/build/reports/fsm`（載入時求值） | `LEDGER_DIR = state_dir()`；仍是模組級常數（測試以 `mod.LEDGER_DIR = tmp` 覆寫的做法不受影響）。hook 是 fail-open 載具：以 try／except 包住匯入與解析，**失敗退回預設目錄並在 stderr 出一行 ASCII 警告**，不得因 `SDD_STATE_DIR` 寫成相對路徑而讓每次工具呼叫的 hook 崩潰 |
| A4 | `.claude/hooks/context_ledger_post.py:39` | 同 A3 | 同 A3 |
| A5 | `tools/fsm_runtime/spec_monitor.py:122` | 違反報告預設 `REPO_ROOT/build/reports/fsm` | `out_dir` 預設改 `state_dir()`（呼叫時求值） |
| A6 | `tools/fsm_runtime/production_monitor.py:62` | `DEFAULT_DRIFT_LOG_DIR`（PBS-DRIFT 滾動檔） | 改 `state_dir()`（載入時求值；該模組已從 `state_loader` 取淨化函式，無新相依） |
| A7 | `tools/fsm_runtime/subagent_contract.py:39` | `BYPASS_LOG_DIR` | 同 A6（同檔 `DISPATCH_LOG_DIR` 在 `build/reports/test-analysis`，不是 fsm 目錄，不動） |
| A8 | `tools/fsm_runtime/fsm_runtime.py:181-206` | 遙測回寫判定 | §3.3 第一列 |

**B 類：明確不改（理由）**

| # | 站點 | 理由 |
|---|---|---|
| B1 | `tools/arch_fitness/arch_fitness.py:153,405-452`（FF-3） | 檢查的是**框架 repo 的目錄衛生**（孤兒 `.tmp`、巢狀垃圾檔），語意就是「框架那個目錄」；不該隨環境變數移到外部專案，CI 也不設該變數 |
| B2 | `tools/fsm_runtime/event_reconciler.py:70` | `events_dir or state.path.parent`，自動跟隨狀態檔 |
| B3 | `tools/fsm_runtime/trajectory_predictor.py:206-221`、`fsm_runtime.py:1602-1779` | `miss_dir` 由呼叫端傳入、無預設值；路徑字面只在 docstring |
| B4 | `tools/fsm_runtime/file_lock.py`、`conversation_ledger.py` | 只吃呼叫端傳入的目錄；路徑字面只在 docstring |
| B5 | `fsm_runtime.py:715-717` | `_assert_allowed_under_auto_compact` 的 `build/reports/fsm/` 是**工具目標路徑的字串前綴比對**，外部專案的路徑同樣含這個片段，仍成立 |
| B6 | `.claude/hooks/session_start.py` | 一律經 `state_loader`，沒有自有路徑 |
| B7 | `tools/fsm_runtime/chaos_runner.py:1380`、`_chaos_b28_benchmark.py:40` | 用演習工作目錄，不碰預設目錄 |
| B8 | 其餘 `REPO_ROOT/build/reports/*` 站點（`abort`、`compaction`、`gc`、`eval`、`hub`、`drift`、`orchestrator`、`closure`、`trajectory`、`fragility`、`ceiling`、`replay`、`optimization`、`value-dimension` 等） | 不是 FSM 狀態；Bridge 的動詞不會觸發；外部專案模式不搬（搬移擴大侵入且無讀者） |
| B9 | 文件字面 `build/reports/fsm`（`workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`、`cicd/SDD_CICD_BASE_LAYER.md`、`cicd/SDD_PRODUCTION_FEEDBACK.md`、`agent/specialized/sdd-orchestrator-zh.yaml`、`.claude/skills/stage-compaction/SKILL.md`、`data/slo_events/README.md`、`docs_template/sdd/quality/PBS-DRIFT-REPORT-TEMPLATE.md`、`AISDLC_SDD_UPGRADE_SOP.md`、`tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml`） | 描述的是預設路徑，不動；**僅** `SDD_FSM_ENGINE.md` 與 stage-compaction 的 `SKILL.md` 各補一句「`SDD_STATE_DIR` 有設時改指該目錄」（Dev-SDD-DOC）；`CHANGELOG.md`／`EVOLUTION_LOG.md` 是史料，只新增條目 |

**測試沙盒（S-09 的根因，同批做）**：`tools/fsm_runtime/tests/conftest.py` 已有三個 session 級 autouse 隔離（meta 帳本、兩個遙測旗標、鷹架代謝旗標）。再加一個：清掉 `SDD_STATE_DIR`／`SDD_PROJECT`，並把 `state_loader.DEFAULT_STATE_DIR` 與載入時求值的帳本／漂移／旁路目錄導向暫存目錄（暫存目錄取名 `build/reports/fsm` 的形狀，使既有「`.name == "fsm"`」斷言不破）。`test_transitions.py` 的 `RuntimeBootstrapTests` 設了 `SDD_PROJECT` 卻沒還原（`test_transitions.py:78,84-86`），須修。**驗收**：整套跑完，版本目錄 `build/reports/fsm/` 的檔案清單前後相同。

### 3.5 Bridge 呼叫 FSM CLI 的固定環境（必須）

| 項 | 值 | 為什麼 |
|---|---|---|
| argv | `[sys.executable, "-W", "ignore::RuntimeWarning", "-m", "tools.fsm_runtime.fsm_runtime", <動詞>, "--project", <專案鍵>, "--must-exist", …]` | 〔乾跑 #14〕runpy 警告與成敗無關；`--must-exist` 防自動建檔（〔乾跑 #12〕） |
| cwd | SDD 版本目錄（`settings.sdd_root`） | `-m tools.…` 需要 |
| 環境 | 以 `os.environ` 為底，**移除所有 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`**，再設：`PYTHONPATH=<版本目錄>`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1`、`SDD_ENABLE_RULE_FIRE_TELEMETRY=0`、`SDD_ENABLE_RULE_CATCH_TELEMETRY=0`、`SDD_STATE_DIR=<專案根>/build/reports/fsm`、`SDD_PROJECT=<專案鍵>` | 環境確定、不洩漏 DB 密碼與權杖給子行程；Docker 的 `/sdd` 唯讀掛載下 CLI 不寫版本目錄（遙測關、不寫 pyc；〔未驗〕容器級） |
| 行程旗標 | `procutil.popen_platform_kwargs()`（Windows＝新行程組＋無視窗）；stdin＝DEVNULL | 與引擎 spawn 同一個載具（`runner.py:228-230`） |
| 輸出 | stdout 取最後一個非空行解析為 JSON；stderr 只作診斷（截 2 KB 入 audit，不入回應） | §4.1 契約 |
| 逾時 | 單次 20 秒；逾時以行程樹終止（`procutil.begin_terminate`）後回 504 `sdd_cli_timeout` | 〔乾跑 #13〕暖機 0.07～0.11 秒，20 秒涵蓋冷啟動與防毒掃描 |
| 序列化 | 行程內以 `(狀態目錄, 專案鍵)` 為鍵的互斥鎖，**同時罩住**「CLI 呼叫」與「`GET /sdd/fsm/{project}` 的檔案讀取」 | 消除 Bridge 自己「讀的當下被 `os.replace` 換檔」的 Windows 共享違規（體檢報告列為理論洞；本設計把自造的那一半消掉） |
| 與 SDD session 並行 | **已知邊界**：狀態檔 load-modify-save 沒有跨行程鎖（只有 `os.replace` 原子） | improving_115 §5.1-6；Bridge 只在 spawn 與終態各呼叫一次，預期近零，登理論洞 |
| 動詞白名單 | `spec-frozen`（僅經 `:freeze`）、`negotiate-enter`、`negotiate-exit --outcome agreed`、`delegate-enter`、`delegate-exit --decision done｜failed` | 其餘動詞（`transition`、`gate`、`resume-from-escalation`、`spec-audit`、`check-impl`、`complete-auto-compact`、`reset-ledger`、`reconcile`、`negotiate-exit --outcome underspecified`）Bridge 一律不呼叫；以測試釘住（§15） |

---

## 4. SDD CLI 新動詞（SD-2）

### 4.1 共通契約（新動詞與 `spec-frozen --json` 皆適用；必須）

| 項 | 契約 |
|---|---|
| stdout | **恰好一行** JSON（`ensure_ascii=True`、緊湊分隔）。成功：`{"ok":true,"verb":…,"project":…,"from_state":…,"current_state":…,…動詞專屬欄}`；失敗：`{"ok":false,"error":<代碼>,"detail":<ASCII，≤200 字>,"current_state"?:…}` |
| stderr | 失敗時一行 ASCII：`[SDD-FSM] <動詞> failed: <代碼>: <detail>`；成功不印。（`_cli` 本檔無 UTF-8 stdio 保護，`fsm_runtime.py:196-198` 的既有慣例＝全 ASCII，`--reason` 內的中文只進 YAML、不回印） |
| rc | 見下表 |
| 全域旗標 | `--must-exist`：狀態檔不存在⇒rc 5，**不建檔**（四個新動詞恆視為已帶此旗標；舊動詞不帶則行為不變） |
| `--reason` | 四個新動詞**必填且 strip 後非空**（缺⇒rc 4）：它是寫進 `decision_trace` 的稽核憑證 |
| 舊動詞 | 不帶新旗標時輸出與 rc 逐字不變（`transition` 的 `OK transitioned to …`、非法轉態 traceback＋rc 1 等） |

**rc 表**（與草案 §4.3 的差異：非法轉態用 **3** 而非 2，因 argparse 的用法錯誤已佔用 2；〔乾跑 #5、#10〕現行非法轉態是 rc 1）：

| rc | 意義 | stdout `error` | Bridge 對映 |
|---|---|---|---|
| 0 | 成功（含 `"noop":true`） | — | 繼續 |
| 1 | 非預期例外（traceback） | — | 502 `sdd_cli_failed` |
| 2 | argparse 用法錯誤（`choices`、缺必填旗標）；stdout 無 JSON | — | 500 `sdd_cli_usage`（Bridge 自己的 bug，測試必須零次出現） |
| 3 | 前置狀態不符／轉態不合法（`TransitionError`） | `transition_not_allowed` | 409 `fsm_state_conflict` |
| 4 | 參數值不合法（`ValueError`；缺檔、超出根、過大、非 UTF-8、`--reason` 空；`SDD_STATE_DIR` 寫成相對路徑，detail 指名該變數） | `invalid_argument`、`doc_not_found`、`doc_outside_root`、`doc_too_large`、`doc_not_utf8` | 422 `sdd_invalid_argument`（Bridge 先驗過，出現＝Bridge bug 或競態） |
| 5 | 狀態檔不存在（`--must-exist`）或不可讀（壞 YAML 且 `.bak` 也壞） | `state_not_found`、`state_unreadable` | 404 `fsm_not_found`／422 `fsm_state_unreadable` |

### 4.2 動詞表（前置狀態以〔乾跑〕與 `fsm_runtime.py` 讀碼為準）

| 動詞 | 必要旗標 | 前置狀態 | 成功轉態與副作用 | 專屬輸出欄 |
|---|---|---|---|---|
| `negotiate-enter` | `--project`、`--reason`，選填 `--contract-ref` | SPEC_FROZEN；已在 TEST_CONTRACT_NEGOTIATED⇒`noop` | →TEST_CONTRACT_NEGOTIATED；`trigger=test_contract_enter`；`contract_ref` 進 `spec_refs`（`fsm_runtime.py:1939-1955`） | `entered`、`from`、`to` |
| `negotiate-exit` | `--project`、`--outcome agreed｜underspecified`、`--reason` | TEST_CONTRACT_NEGOTIATED | agreed→IMPLEMENTATION；underspecified→SPEC_DRAFTING；`trigger=test_contract_exit`（`:1957-1979`） | `exited`、`outcome`、`to` |
| `delegate-enter` | `--project`、`--reason`，選填 `--playbook-ref`（格式見 §4.4） | IMPLEMENTATION；已在 AUTOCLAUDE_DELEGATED⇒`noop`（不寫 trace、不更新 tracking） | →AUTOCLAUDE_DELEGATED；`autoclaude_delegated_tracking={entered_at,resume_state,playbook_ref?}`；`trigger=autoclaude_delegated_enter`（`:3216-3251`） | `entered`、`from`、`to` |
| `delegate-exit` | `--project`、`--decision done｜failed`、`--reason` | AUTOCLAUDE_DELEGATED | done→IMPLEMENTATION——語意＝**委派交還控制權、未升級**，不是「成功」，成敗由後續閘門判（D-115-15）；failed→先 `record_escalation(source="autoclaude_delegated_failed")` 再→ESCALATION（`:3253-3285`）。兩者都**不清除** `autoclaude_delegated_tracking`（〔乾跑 #15、#17〕） | `exited`、`decision`、`to` |
| `spec-frozen`（擴充） | `--project`、`--stage`，選填 `--doc`（可重複）、`--digest`、`--root`、`--reason`、`--approver`、`--json` | HUMAN_PENDING（或 `is_transition_allowed(current,"SPEC_FROZEN")` 為真的其他態）；**先驗前置、再算摘要、最後才改狀態**（現行 `record_spec_frozen` 先改記憶體再轉態，`fsm_runtime.py:641-648`） | →SPEC_FROZEN；見 §4.3 | `stage`、`spec_doc_digests`（有 `--digest` 時） |

### 4.3 `spec-frozen` 的摘要與稽核欄位（必須）

| 項 | 契約 |
|---|---|
| `--digest` | 開啟摘要模式。**不帶＝完全是現行行為**（不查檔、不算摘要、`spec_docs` 照字面記），保住既有測試與 F-SBR 驅動腳本；Bridge 與新版文件一律帶 |
| 摘要演算法（S4 定案：**正規化文字，不是原始 bytes**） | `sha256` over **換行正規化後的 UTF-8 bytes**：先 `\r\n`→`\n`、再 `\r`→`\n`；BOM 不剝（`read_text(encoding="utf-8")` 也不剝）。這與 adapter 的 `spec.digest`＝`sha256(read_text(encoding="utf-8").encode("utf-8"))` 逐位元相同（`sdd_to_playbook_adapter.py:137,278`；`read_text` 會做通用換行轉換）；〔乾跑〕對 LF／CRLF／CR／BOM＋LF／BOM＋CRLF 五種檔，正規化摘要與 adapter 摘要皆相等，而原始 bytes 在 CRLF 與 CR 兩種不等。Windows 上用編輯器存成 CRLF 是常態，用原始 bytes 會讓每次比對假紅。檔案必須是合法 UTF-8（adapter 讀不了的檔不該被凍結），否則 rc 4 `doc_not_utf8` |
| 值格式 | `"sha256:<64 位小寫 hex>"`（與 `SddSpec.digest` 同形） |
| 路徑基準 `--root` | 專案根（絕對路徑）。省略時：`state_dir()` 以 `build/reports/fsm` 結尾⇒取其上三層，否則取 `state_loader.REPO_ROOT`（框架自身專案根）。兩種情況在預設框架目錄下結果一致；自訂 `SDD_STATE_DIR` 落在慣例之外而未給 `--root` 時，`doc_not_found` 會大聲失敗，不會靜默算錯檔 |
| 路徑正規化 | 每個 `--doc`：絕對或相對皆可，`resolve()` 後必須落在 `--root` 之下（否則 rc 4 `doc_outside_root`），記成 **POSIX 相對於 root** 的字串；缺檔或是目錄⇒rc 4 `doc_not_found`；超過 16 MiB⇒rc 4 `doc_too_large`（Bridge 的 `docs[]` 受白名單根限制但檔案可能很大，不能讓一次凍結卡住）。`spec_docs` 與摘要鍵用**同一組**正規化字串。跨平台三點：反斜線只在 Windows 被 `pathlib` 當分隔符（Bridge 一律傳 POSIX 形）；`resolve()` 會跟隨 symlink，指向根外的 symlink 同樣得 `doc_outside_root`（fail-closed）；鍵的大小寫照 `--doc` 字面，不替大小寫不敏感檔案系統另做折疊，失配由 adapter 端 fail-closed 接住（§6.2）。〔乾跑〕原型逐一驗過：相對（POSIX 形與 Windows 反斜線形）、根內絕對、根內含 `..`、根外絕對、`..` 跳出根、目錄、缺檔，加上 CRLF 檔與同內容 LF 檔摘要相同、慣例目錄與自訂目錄兩種 `--root` 推導 |
| 寫入 | `frozen_stages[-1]` 新增鍵（**只在有值時才出現**，舊讀者不受影響）：`spec_doc_digests: {<相對路徑>: "sha256:…"}`、`approved_by: <--approver>` |
| 決策軌跡 | `transition` 的 `reason` 取 `--reason`（缺省仍是 `Stage frozen: <stage>`）；`spec_refs` 取正規化後的 `spec_docs` |
| `--approver` | 非空、≤100 字（與 SA 契約的 `approver` 一致）、不含控制字元；來源是 Console 的 JWT subject（Backend 傳給 Bridge，Bridge 再傳）。C2 的「FSM 與 Console 稽核互相對得上」靠它與 `--reason` 的固定格式（§4.4） |
| 模板 | `tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml` 的 `frozen_stages` 註解補上兩個新鍵的格式（僅註解） |

摘要的純函式（換行正規化、路徑正規化、超限判斷）建議放新增的 `spec_digest.py`（置於 `tools/fsm_runtime/`），CLI 只做接線；Bridge 與 adapter 各自持有一份**等價的兩行實作**，一致性由對拍測試守（§15），不得跨子專案 import（ADR-XPLAT-010 §2.1）。

### 4.4 CLI 參數值的格式（S3 定案；必須）

| 項 | 格式 |
|---|---|
| `--playbook-ref`（`delegate-enter`） | `run:<run_id>`；`run_id`＝Bridge 的 run id（＝`execution_runs.id`）。SA 暫定的裸 `run_id` 改為帶 `run:` 前綴：與文件路徑型的 `spec_refs` 可區分，也讓回收規則（§10.3）只認 Bridge 簽發的值（〔乾跑 #21〕缺省或他種值＝外來委派） |
| `:freeze` 的預設階段名 | 請求省略 `stage` 時用 `Stage-<n>`，`n`＝`frozen_stages` 筆數＋1（Bridge 持互斥鎖時讀狀態檔計得）；請求帶 `stage` 則照用（`^[A-Za-z0-9._-]{1,64}$`）。沿用 SDD `tools/fsm_runtime/README.md` 的 `Stage-N` 慣例；階段名不要求唯一（摘要鍵遇重複以後者為準，§6.1） |
| `--reason` 的組字 | 一律 `console-` 開頭、`key=value` 以 `; ` 分隔：①`spec-frozen`＝`console-freeze approver=<approver>; reason=<使用者理由>`；②`negotiate-enter`＝`console-signoff approver=<approver>; run=<run_id>`；③`negotiate-exit`＝§5.2 C-2 的固定格式；④`delegate-enter`＝`console-run run=<run_id> START`；⑤`delegate-exit --decision done`＝完成 `console-run run=<id> COMPLETED`／取消 `console-run run=<id> CANCELLED`／回收 `console-run run=<舊 id> RECLAIMED old_status=<舊終態或 missing> by=<新 id>`／spawn 失敗補償 `console-run run=<id> SPAWN-FAILED delegation not started`；⑥`delegate-exit --decision failed`＝`console-run run=<id> ENGINE-ESCALATION step=<step_id>: <detail>` |
| 輸入清理 | `approver`：1～100 字、無控制字元、不含 `;`（否則 422 `sdd_invalid_argument`，讓上列格式可無歧義解析）；使用者理由：去前後空白後 1～500 字、無控制字元（含換行）——**不靜默截斷、不替換**，違反即 422，`reason=` 是最後一段、以首個 `reason=` 之後全部為理由；`detail`（引擎升級訊息）取前 200 字、換行與控制字元換成空格 |

---

## 5. R-9.20.2 談判閘對映與失敗恢復（SD-3）

### 5.1 驗證結果（〔乾跑〕＋〔讀碼〕）

| 事實 | 證據 |
|---|---|
| R-9.20.2 要求 SPEC_FROZEN 後先過 TEST_CONTRACT_NEGOTIATED 才進 IMPLEMENTATION，但 `enforcement_mechanism: manual` | `governance/rules/R-9.20-phase-h-gae.yaml:13,19` |
| runtime 保留 SPEC_FROZEN→IMPLEMENTATION 直達邊（向後相容），〔乾跑 #11〕直達邊真的可走 | `transition_rules.py:31-35` |
| 兩步談判（enter→exit agreed）在真 FSM 上合法，且 `exit_test_contract_negotiated` **不檢查**任何「合約簽署」憑證檔，只轉態 | 〔乾跑 #3〕、`fsm_runtime.py:1957-1979` |
| R-9.20.3（oracle 對 Generator 不可見、Generator 與 Evaluator 獨立 context）在 AutoClaude 路徑**結構上不成立**：adapter 把評估指令與驗收 regex 逐字寫進 prompt，且寫測試的就是同一個 AI | `sdd_to_playbook_adapter.py:181-193`；improving_115 §5.1-2 |

### 5.2 裁決：**接受**「Console 簽核匯入草稿＝談判 `agreed`」，附四條件（必須）

| # | 條件 | 做法 |
|---|---|---|
| C-1 | 權威與時機 | 只在 Bridge 收到**帶有效權杖**且含 `sdd` 區塊的 `POST /autoclaude/runs` 時執行（backend 在 `requireSignedOff` 通過後才呼叫，二次校驗 409 照舊）；簽署人＝`sdd.approver`（SA 契約採用的欄名，D-115-16）：Backend 取匯入記錄的核准人（Console 的 `signedOffBy`），為空時取觸發 execute 的 JWT subject，所以**Backend 永遠送具名人**；Bridge 端該欄選填、省略時記 `console`（服務身分，稽核上一眼可辨不是具名人，不假裝有人簽） |
| C-2 | 內容綁定 | `negotiate-exit` 的 `--reason` 固定格式：`console-signoff approver=<approver>; oracle=<TCS 相對路徑>@<sha256:…>; basis=import-draft-signoff; r9.20.3=not-satisfied`；`negotiate-enter` 的 `--reason`：`console-signoff approver=<approver>; run=<run_id>`（§4.4）；`--contract-ref`＝TCS 相對路徑（進 `spec_refs`）。**誠實條款寫進憑證本身**：稽核者讀到的是「人簽了這份 oracle，且獨立性條款未滿足」，不是假裝完整談判 |
| C-3 | 補償性控制 | 真正的閘仍是 SCG-4 的獨立審查（QA 鏡核 AI 寫的測試是否忠於 Gherkin）；RTM 面板一律標「諮詢視圖」（草案 §5.1-2、架構評估紅線 8）。本 ADR **不宣稱** R-9.20.3 已滿足 |
| C-4 | 兩步連發與自癒 | enter 與 exit 在同一個 Bridge 請求內背靠背；中間失敗留在 TEST_CONTRACT_NEGOTIATED，預檢表（§10.2）對它的處置＝`negotiate-exit agreed`＋`delegate-enter`，不需人工 |

**不採**：(a) 直達邊 SPEC_FROZEN→IMPLEMENTATION（靜默略過 R-9.20.2，且 SPEC_FROZEN 的稽核軌跡少一段）；(b) 另立 oracle 來源（要獨立 context 的 Evaluator，超出本輪）；(c) 由 Bridge 呼叫 `negotiate-exit underspecified`（Console 沒有「退回修改」，延後登記，見草案 §5.2）。

### 5.3 `failed` 之後怎麼辦（人工恢復路徑；必須）

| 步 | 內容 |
|---|---|
| 狀態 | FSM＝ESCALATION（阻塞態，`fsm_runtime.py:660-662`；〔乾跑 #8〕此時一切工具呼叫被擋）；`escalation_provenance.source="autoclaude_delegated_failed"`、`escalation_history[-1]` 未結。辨識「這是委派失敗」要讀 `escalation_provenance.source`（trace 那筆是 `ESCALATION->ESCALATION`，不可靠，〔乾跑 #7〕）——所以 `GET /sdd/fsm/{project}` 須與 `escalation_history` 尾端同批**多回 `escalation_provenance`**（目前該端點不回，`routers/sdd.py:142-156`）。🔴 〔乾跑 #17、#20〕`escalation_provenance` 與 `autoclaude_delegated_tracking` 在恢復後**都不會被清除**，所以「現在有沒有一個未解的委派失敗」的判斷式只能是「`current_state` 屬 ESCALATION／ESCALATION_FINAL，且 `escalation_history[-1].resolved_at` 為空」；只看 provenance 在不在會在 IMPLEMENTATION 上顯示過期的失敗。失敗的是哪個 run，讀 `autoclaude_delegated_tracking.playbook_ref`（`run:<run_id>`，§4.4；〔乾跑 #17〕ESCALATION 時仍保留） |
| 誰能恢復 | **只有人**（R-9.5、絕對禁令 #6），而且恢復**留在 SDD session**（D-115-15）。Bridge 與 Console **不提供恢復動詞**（`resume-from-escalation` 不在 §3.5 白名單；A3＝本輪只開「核准凍結」一個人工閘；Bridge 的回收也不能碰 ESCALATION——〔乾跑 #18〕`delegate-exit` 在 ESCALATION 回 rc 3） |
| 怎麼恢復 | 現行 CLI 即可，〔乾跑 #9〕rc 0：`resume-from-escalation --to IMPLEMENTATION --project <鍵> --reason "<人工原因>"`。前置條件：FSM 在 ESCALATION 或 ESCALATION_FINAL（否則 rc 0 回 `{"noop":true,…}`，〔乾跑〕已驗）；`--to` 必須屬 `RESUME_TARGETS`（SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW）、`--reason` 非空，否則 `parser.error`（rc 2，`fsm_runtime.py:3339-3344`；〔乾跑 #19〕三種前置不備皆 rc 2、狀態與檔案不動）；委派失敗該回 IMPLEMENTATION，與 `autoclaude_delegated_tracking.resume_state` 一致。恢復後 FSM＝IMPLEMENTATION，歷史回填 `resolved_at`，**下一個 Console 批次可直接啟動**（〔乾跑 #9〕之後 `delegate-enter` rc 0） |
| Console 該顯示什麼 | ESCALATION 標示（`phase.blocking=true`）＋最近 `escalation_history` 尾端＋**可複製的恢復指令**（建議由 Bridge 在 `GET /sdd/fsm/{project}` 於 ESCALATION／ESCALATION_FINAL 時多回 `recovery:{target,powershell,posix}`；SA 不採納則由前端以 `{root,project}` 套下列模板） |

恢復指令模板（符合根層鐵律一、二：PowerShell 用 `Push-Location`／`Pop-Location` 同一句內成對、不裸 `cd`；POSIX 的 `VAR=值 指令` 前綴只作用於該指令）：

```
PowerShell: Push-Location "<SDD 版本目錄>" -ErrorAction Stop; $env:SDD_STATE_DIR = "<專案根>\build\reports\fsm"; & "<python>" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project "<鍵>" --to IMPLEMENTATION --reason "<人工原因>"; Remove-Item Env:SDD_STATE_DIR; Pop-Location
bash／zsh : cd "<SDD 版本目錄>" && SDD_STATE_DIR="<專案根>/build/reports/fsm" "<python>" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project "<鍵>" --to IMPLEMENTATION --reason "<人工原因>"
```

外部專案模式（`SDD_STATE_DIR` 有設）下該 CLI 不寫遙測，所以人工恢復不會弄髒框架樹。`ESCALATION_FINAL`（結構性、或自動恢復失敗）同路徑，目標可能不同——以 `GET` 回應的 `phase` 與 `escalation_provenance` 為準，不得由 Console 猜。

---

## 6. 凍結綁內容（SD-4，對應 G-06）

### 6.1 生產、消費、預檢

| 角色 | 做什麼 | 在哪 |
|---|---|---|
| 生產者 | `spec-frozen --digest` 對每份 `--doc` 記 `spec_doc_digests`（§4.3） | SDD CLI |
| 消費者 | adapter `load_spec`：取全部 `frozen_stages[*].spec_doc_digests` 的**聯集**（同一鍵在多個階段出現時，後一階段勝出＝以最近一次凍結為準）；以「規格檔絕對路徑的**尾段**等於某個鍵」找對應摘要——**不依賴專案根的絕對路徑**，所以 Docker 與主機路徑不同也成立。比對寫法（必須）：鍵以 `/` 拆段、`os.path.join` 組成本機路徑，兩邊各過 `os.path.normcase`，判 `me == 鍵` 或 `me.endswith(os.sep + 鍵)`；多個鍵吻合取最長者。**不得**對 `as_posix()` 字串直接用 `normcase`——Windows 的 `normcase` 會把 `/` 換成 `\`，尾段比對恆不成立（原型第一版即因此全數誤判「不在清單」） | AutoClaude adapter（§6.2） |
| 預檢三點 | ①凍結時（`:freeze`）②匯入時（`/sdd/compile`＝adapter 內部比對）③執行前（`POST /autoclaude/runs`、`resume`、`restore`） | Bridge（§6.3） |

### 6.2 adapter 判定表（必須）

| 狀況 | 結果 | 例外／出聲 |
|---|---|---|
| 沒有任何階段帶摘要（舊狀態檔、或凍結時沒帶 `--digest`） | 維持現行放行 | `record_event("sdd.frozen_digest_absent", …)`，`SddSpec.frozen_digest_status="absent"`（每個 adapter 實例只出聲一次） |
| 有摘要，但規格檔不在任何階段的清單內 | fail-closed | `SpecNotFrozenError`（detail：「規格檔不在凍結清單」）⇒ 422 `spec_not_frozen` |
| 有摘要且吻合 | 放行 | `frozen_digest_status="verified"` |
| 有摘要但不吻合 | fail-closed | **新** `SpecDigestMismatchError`（`SpecNotFrozenError` 的子類，定義在 `core/ports/spec_source.py`）⇒ 既有 `except SpecNotFrozenError` 路徑（plugin 的 PRE_RUN veto、`sdd_compile` rc 2）自動 fail-closed，Bridge 先接子類回 409 `spec_digest_changed` |

### 6.3 Bridge 三點預檢與錯誤對映（必須）

| 點 | 時機 | 檢查 | 失敗 |
|---|---|---|---|
| ①凍結時 | `POST /sdd/fsm/{project}:freeze` | `docs[]` 皆存在、在根之下；「含 TCS」＝至少一個檔名符合官方 TCS 命名（`TEST-CONTRACT-SPEC-*` 或 `TCS-*`，與 adapter 的官方命名判準同形），且專案已綁定 `sdd_spec_file` 時它必須在 `docs[]` 內（補註 2026-10-17：這一條由 **Backend** 在轉呼 Bridge 前擋下回 400——Bridge 不知道 Console 的綁定；契約 v1.5 偏離 #4 與實作皆如此，本列原文保留）；若 body 帶 `expected_digests`（核准人當時看到的摘要），逐一與現檔摘要比對 | 409 `spec_digest_changed`（`detail.pair=expected_vs_file`）：核准人看的版本不是現在要凍結的版本 |
| ②匯入時 | `POST /sdd/compile` | adapter 內建（§6.2）；回應帶 `fsm_project`、`frozen_digest:"verified｜absent"` | 422 `spec_not_frozen`（未凍結、狀態檔缺、規格檔不在凍結清單）／409 `spec_digest_changed`（有摘要但現檔不吻合）。S7 定案：兩者**依原因並存**，同一原因在三個預檢點用同一個 reason——「內容與凍結時不同」一律 409，不是 422。AT 未編成不是錯誤：200＋`unmapped_at_ids`（§8.2） |
| ③執行前 | `POST /autoclaude/runs`（含 `sdd`）、`:resume`、`/restore` 的 SDD run | 重跑 adapter `load_spec`（凍結＝現檔）；再比對 playbook 各任務的 `spec_digest`（匯入時存下的值）必須恰為現檔摘要這一個值；任務完全沒有 `spec_digest`⇒Backend bug | 409 `spec_digest_changed`（`detail.pair=frozen_vs_file｜import_vs_file`）；缺摘要 422 `sdd_block_invalid`；`frozen_digest_status="absent"` 放行並在 201 的 `warnings` 帶 `sdd_frozen_digest_absent`（不靜默） |

**Backend 對映**：Backend 對 Bridge 的 409 `spec_digest_changed` 與 422 `spec_not_frozen` 一律當**拒絕**處理。注意 `ImportParser.probeSpec`（`ImportParser.java:150-166`）目前把「非 422」的 4xx 當成「略過路徑 A」——`spec_digest_changed` 若走 409 會被它靜默降級成 LLM 草稿，這是 fail-open；Dev-Backend 必須對該 reason 明確丟拒絕（回歸測試具名）。

---

## 7. 選檔與綁定（SD-5，對應 G-02／G-07／S-05／S-10）

### 7.1 adapter 選檔規則（必須）

`_find_fsm_state` 現況：自 `spec_dir` 向上找第一個含 `FSM-STATE-*.yaml` 的 `build/reports/fsm`，取字母序第一個（`sdd_to_playbook_adapter.py:241-252`；〔體檢 S-05〕他專案已凍結即可放行未凍結專案）。新規則：

| 專案鍵來源（優先序） | 行為 |
|---|---|
| 建構子參數 `fsm_project`（字串；`None`＝讀環境；**空字串＝明確不指定、不讀環境**） | Bridge 行程內呼叫一律顯式傳值（含空字串），**不得讀到 Bridge 自己的環境**——開發機匯出 `SDD_PROJECT` 是常態 |
| 環境變數 `SDD_PROJECT`（strip 後非空） | 引擎子行程與 `sdd_compile` CLI 走這條（wiring 於引擎啟動時建構 adapter，`wiring.py:293`） |
| 都沒有 | 保留現行單檔行為 |

在找到的第一個含狀態檔的 `build/reports/fsm` 目錄內：

| 條件 | 結果 |
|---|---|
| 專案鍵含 `/`、`\`、NUL、控制字元，或是 `.`／`..` | `SpecNotFrozenError`（非法鍵）。防路徑穿越；另外在 Windows 上鍵內的 `:` 會被 NTFS 當成資料流，精確檔名那一步只會當它不存在，所以含 `:` 等字元的原名一律走下面的「欄位反查」那一列 |
| 有專案鍵，且 `FSM-STATE-<鍵>.yaml` 存在 | 用它 |
| 有專案鍵，無該檔，但**恰有一個**檔的 YAML `fsm_state.project` 等於鍵（鍵是未淨化的原名，如含 `:`） | 用它 |
| 有專案鍵，其餘情況 | `SpecNotFrozenError`（detail 列出該目錄現有的專案鍵）；**不再往上層目錄找**（往上找會撞到別的專案） |
| 無專案鍵，目錄內恰一個狀態檔 | 用它（現行行為） |
| 無專案鍵，目錄內兩個以上 | `SpecNotFrozenError`（「狀態檔不唯一，請設定 SDD_PROJECT」）——**fail-closed**；框架自己的狀態目錄（現有 8 個檔）從此不能不指定專案就通過凍結閘，這是刻意的 |

`fsm_state_path` 顯式參數維持最優先、行為不變。`_POST_FROZEN_STATES`（`sdd_to_playbook_adapter.py:50-54`）**必須加入 `AUTOCLAUDE_DELEGATED`**：Bridge 在 spawn 前已 `delegate-enter`，引擎 PRE_RUN 讀到的 `current_state` 就是它；對「`frozen_stages` 為空、靠狀態判斷已凍結」的舊狀態檔，缺這一項會讓委派一啟動就被 veto。

引擎 PRE_RUN 的 `load_spec(workflow_path)`（`sdd_governance_plugin.py:170-176`）沿用 §8.3 的「路徑可為檔」規則，plugin 與 port 簽名不改。

### 7.2 Console 專案為錨的綁定（D-115-14；必須）

| 項 | 契約 |
|---|---|
| 錨 | **Console 專案是錨**：綁定＝`execution_path`（已有，`NOT NULL`，`V1__init.sql:13`；狀態目錄根＝`<execution_path>/build/reports/fsm`，`SDD_STATE_DIR` 只由 Bridge 對 CLI 子行程設定）＋`sdd_project`（FSM 專案鍵）。不採「佔位 P0 專案」（會讓一個 FSM 專案綁兩個 Console 專案）。所以**不存在「未綁定」狀態**：沒有 `sdd_not_bound`，核准凍結的請求也沒有 `binding` 欄（SA 契約 §1.10.2 與其驗證順序表的第 3 列須刪） |
| 欄位 | Flyway `V12__project_sdd_binding.sql`（現有最大 V11；檔名採 SA 契約的寫法）：`projects.sdd_project VARCHAR(100)`、`sdd_spec_dir VARCHAR(500)`、`sdd_spec_file VARCHAR(500)`，皆 nullable。`sdd_project` 為 NULL＝「用預設」。加 `sdd_spec_file` 是為了讓後續批次**精確指到那份 TCS**，不必每次重掃整棵樹（G-15）、且之後多一份 TCS 也不會變歧義 |
| 預設與有效值 | 有效 FSM 專案＝`sdd_project`（有值時）否則**專案名**。Backend 不自行淨化（淨化規則只有 Bridge 有鏡像，§7.4）：一律把「有效值（可以是原名）」交給 Bridge，Bridge 回應帶淨化後的 `fsm_project`。可編輯：專案詳情「SDD 治理」區可改 `sdd_project`（自由輸入，Bridge 淨化後生效；可用 `GET /api/v1/engines/sdd?projectId=` 的清單輔助挑選） |
| 寫回（固定專案鍵） | 在**第一次使用**時——核准凍結：唯讀 GET 確認狀態檔存在之後、呼叫 `:freeze` 之前；匯入 confirm：落庫時——Backend 把 Bridge 回的 `fsm_project` 寫進 `sdd_project`（原為 NULL 時）。此後專案改名不會讓綁定悄悄移到另一個 FSM 專案；寫回發生在「這個鍵真的有狀態檔」被確認之後，所以填錯的名字不會留下綁定 |
| 唯一性（先檢查、後寫入） | `(execution_path, sdd_project)` 在**未軟刪除且 `sdd_project` 非空**的列中唯一（partial unique index）。為避免「FSM 已被寫入才發現衝突」，Backend 在**任何 Bridge 寫入呼叫之前**，先以唯讀 `GET /sdd/fsm/{有效名}?root=<execution_path>` 取回 `fsm_project`（該 GET 的回應新增此欄＝狀態檔名裡的**淨化後的鍵**；現有的 `project` 欄是檔內的原名，兩者可能不同，不能拿來當鍵；找不到狀態檔＝404 `fsm_not_found`：要先在該目錄的 SDD session 建好狀態，本來就是 `--must-exist` 的要求），查唯一性並寫回，之後才呼叫寫入端點；衝突⇒409 `sdd_binding_conflict`、不呼叫 Bridge 寫入 |
| 路徑 A 匯入 | `ParseOptions` 帶 `executionPath`（規格根）、`sddProject`（有效值）、選填 `specFile`；`/sdd/compile` 回應的 `fsm_project`、`spec_path` 是回填值的來源。**回填只在 confirm 成功落庫時做**，parse／預覽不回填——放棄的草稿不該產生綁定。`sdd_spec_file`＝回應的 `spec_path`、`sdd_spec_dir`＝其所在目錄 |
| `targetProjectId` | 路徑 A 匯入的選填參數。**帶**＝confirm 時把草稿的目標／任務**併入該既有專案**並回填 SDD 綁定（`sdd_spec_dir`／`sdd_spec_file`，`sdd_project` 為 NULL 時寫回）；parse 的 `executionPath`、`sddProject`、`specFile` 一律取自目標專案，請求另帶不同值⇒409 `sdd_binding_conflict`；**專案已有不同的綁定⇒409 `sdd_binding_conflict`**（任一成立即是：編譯回應的 `fsm_project` 與目標專案的 `sdd_project`〔或其預設淨化鍵〕不同；規格根不在目標專案的 `execution_path` 之下），相同⇒冪等更新 `sdd_spec_dir／sdd_spec_file`。目標專案須存在且未軟刪除（404）。**不帶**＝維持現行「建立新專案」，以規格根當 `execution_path`、以編譯回應回填綁定；同一 `execution_path` 下已有未刪除專案綁定同一個 `fsm_project`⇒409 `sdd_binding_conflict`（唯一索引兜底）。併入的目標／任務如何排序與編號屬 SA 契約，不在本 ADR |
| 一般與 dogfood 流程 | 建專案（`execution_path`＝專案根）→ 人在該目錄的 SDD session 走閘門到 HUMAN_PENDING（`SDD_STATE_DIR=<execution_path>/build/reports/fsm`、`SDD_PROJECT`＝專案名或其淨化鍵）→ Console 核准凍結（專案層端點）→ 路徑 A 匯入並帶 `targetProjectId`＝同一專案 → 簽核 → 執行 |
| 讀取 | `GET /api/v1/engines/sdd` 依專案帶 `root=<execution_path>` 與 `project=<有效名>`；不帶專案維持現行（框架目錄、全域清單） |
| `sdd` 區塊的資格 | 專案有 `sdd_spec_dir`（路徑 A 匯入後才有）才帶 `sdd` 區塊；沒有＝照舊不帶，並在 201 的 `warnings` 出聲（SA 契約的 `sdd_governance_inactive`），不靜默 |
| 解除／改綁 | 沒有「解除綁定」端點；編輯 `sdd_project` 即改綁（受唯一性限制）。UI 與稽核屬 SA 契約 |
| 綁定時警告 | 專案根若是 git 工作樹而 `build/reports/fsm/` **未被忽略**⇒`/sdd/compile` 回應 `warnings` 帶 `state_dir_not_ignored`（Bridge 以 `git -C <根> check-ignore -q -- build/reports/fsm/FSM-STATE-x.yaml`：rc 0＝已忽略、1＝未忽略、128＝非 git 樹則略過）；只警告不擋 |

### 7.3 `sdd` 區塊（`POST /autoclaude/runs`，與 `playbook` 同層；欄位語意必須，JSON 形狀由 SA 定）

| 欄 | 必填 | 語意 |
|---|---|---|
| `spec_dir` | 是 | 絕對路徑；`security.check_path` 過白名單根（同 `/sdd/compile`） |
| `spec_file` | 否 | 相對 `spec_dir` 或絕對（須在 `spec_dir` 之下）；`spec_dir` 內有多份 TCS 時必填 |
| `fsm_project` | 是 | 原名或淨化後的鍵皆可，Bridge 一律先過 `fsm_component()`（§7.4） |
| `root` | 否 | 專案根，預設 `execution_path`；`spec_dir` 必須在其內（否則 422 `sdd_block_invalid`）；狀態目錄＝`<root>/build/reports/fsm` |
| `approver` | 否 | 簽核人（§5.2 C-1；欄名採 SA 契約，D-115-16）：1～100 字、無控制字元、不含 `;`；省略＝`console`；Backend 永遠送具名人（`signedOffBy`，為空時取 JWT subject） |

Bridge 伺服端注入：引擎 playbook 的 `workflow_type="aisdlc_sdd"`、`workflow_path`＝**已驗證的 realpath**（有 `spec_file` 用檔、否則用目錄；§8.3）；引擎子行程環境 `SDD_PROJECT=<鍵>`（先剝除繼承自 Bridge 的 `SDD_PROJECT`／`SDD_STATE_DIR`，§9「剝除」列）。**不注入 `SDD_STATE_DIR` 給引擎子行程**（與草案差異，附錄 A-3）：adapter 靠向上搜尋 `build/reports/fsm` 就找得到狀態，引擎沒有任何讀者需要它；給了反而讓子行程內的 AI 步驟拿到「直接呼叫 FSM CLI 簽自己」的現成指向。外部契約 `PlaybookIn.workflow_type` 仍只收 `auto`（D-115-06）。

### 7.4 專案名淨化規則（S-10；必須）

| 項 | 契約 |
|---|---|
| 規則來源 | `AISDLC_SDD/scripts/component_sanitizer.py` 的 `sanitize_component`（NFC→strip→把 `<`、`>`、`:`、`"`、`?`、`*`、`\`、`/`、ASCII 豎線與 ord<0x20／0x7F 換成 `_`→截 80→`rstrip(" .")` 或 `untitled`→stem 若是 Windows 保留裝置名則加 `_` 前綴並重截） |
| Bridge 鏡像 | Bridge 持有**一份**逐字鏡像 `fsm_component(name)`（Bridge 與 SDD 同屬 monorepo 但不同子專案，不 import；建議新增 `fsm_names.py`）。進入 Bridge 的專案名（body、路徑參數、`sdd.fsm_project`）**一律先過它**；淨化是冪等的（〔乾跑〕21 個樣本：訂單系統、`Order System`、`proj(v2)`、`a+b`、`名稱含@符號`、`a:b`、`x/y`、`CON`、80 字以上、NFD 輸入、尾端空白與句點等，輸出再淨化皆不變），傳原名與傳鍵等價 |
| 讀取白名單 | 原 `^[A-Za-z0-9._-]{1,128}$`（`routers/sdd.py:18`）改為「`sanitize_component` 輸出域」判準：非空；已是 NFC；長度 ≤80；不是 `.`／`..`；不含 `<`、`>`、`:`、`"`、`?`、`*`、`\`、`/`、ASCII 豎線、控制字元、DEL；無前後空白；不以 `.` 結尾。〔乾跑〕舊白名單只接受 21 個樣本淨化結果中的 14 個，新判準接受 21 個。**`..` 只有整段或帶分隔符才有穿越意義**，名稱內部的連續句點不拒（sanitize 本身也不動它）；`_readable_state_file` 的 symlink 逃逸檢查（`routers/sdd.py:34-40`）保留 |
| 列表 | `GET /sdd/fsm` 的 `errors` 語意不變：不合判準的檔名進 `errors` |
| 預設值的來源 | 人在 SDD session 用 `SDD_PROJECT=<Console 專案名>`（原名或淨化鍵皆可：CLI 端 `state_loader` 會淨化成同一個檔名）；Backend 傳專案名（或已寫回的 `sdd_project`）給 Bridge、由 Bridge 淨化（§7.2）；Backend **不自行**推導 FSM 專案名（只有 Bridge 有鏡像） |

---

## 8. 編譯契約（SD-6，對應 S-03／S-04／S-11／S-12）

### 8.1 AT ID 文法（D-115-16 定案；正向編譯與逆向 RTM 共用）

`AT_ID = AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`（整串全比對、區分大小寫、`AT-` 大寫）。**前兩段數字＝所屬 AC**：`AT-001-12-3-a` 屬 `AC-001-12`；第三段起是任意個英數尾綴（`-1`、`-a`、`-E1`、`-E-1`），**不影響歸屬**。這是主控 D-115-16 的定案，取代 Architect／SA 草案的 `AT-[\w\-]+` 與本檔先前的較寬版（首段 `\d{1,4}`、第二段可為字母）。AC 的文法不動（`AC-[\d\-]+`）。

**單一定義**：AutoClaude 在 `core/ports/spec_source.py` 放一份字串常數 `AT_ID_PATTERN`；正向的 `sdd_to_playbook_adapter.py` 與逆向的 `playbook_to_rtm_adapter.py` 都由它組 regex，不得各寫一份（一份判準一個家，也讓兩邊不可能悄悄漂移）。

| 接受 | 拒絕（出現在宣告位置時＝`unmapped_at_ids`，§8.2） |
|---|---|
| `AT-001-1-1`、`AT-001-1`、`AT-001-12-3-a`、`AT-001-1-E1`、`AT-001-1-E-1`、`AT-029-1-1-1-1` | `AT-14-1-1`（首段非三位）、`AT-123`／`AT-001`（缺第二段數字）、`AT-001-E-1`（第二段非數字）、`AT-0001-1-1`、`AT-001-1-`、`AT-001--1`、`at-001-1-1`、`AT-001-1-1_a`（`_` 不在尾綴字元集）、`AT-001-1-1 x`（尾隨文字）、`AT-{NNN}-1-1`（模板佔位，根本不算 AT 字樣） |

〔乾跑〕以上 17 個樣本逐一以 `re.fullmatch` 驗過；`step_id`（`sdd-<場景>-<at_id 小寫>`）與 evaluator 的 `-k` 代號（連字號換底線）對含字母的尾綴成立（`_SAFE_FRAGMENT` 允許字母）。

**既有資料不受衝擊**（〔乾跑〕全 repo 掃描：`AutoClaude` 的 `tests`／`scripts`／`autoclaude`、Bridge、Backend、前端測試共 1262 個檔）：資料字串裡不符新文法的只有 4 個測試檔——翻譯學習的鍵（`AT-001`、`AT-009` 一類）與 `ab_compare` 的 `AT-01`／`AT-02`，它們都不經過兩支 adapter 的 AT 文法；另有 9 個檔只在 docstring 標籤出現舊編號（`AT-24-…`、`AT-27-…`、`AT-14-…` 是歷輪驗收編號，不是資料）。F-SBR 夾具（`AutoClaude/scripts/bridge_e2e/wordcount/` 下的 TCS）編出與舊文法相同的 3 個 AT。結論：沒有任何既有測試資料要為遷就文法而改，**也不得放寬文法去遷就舊資料**。

**E 類（邊界／錯誤）AT**：模板 §4 的 `AT-{NNN}-E-n` 編號因第二段不是數字而**不可編譯**（模板不改，D-115-09）。§4 表格的列第一欄是場景類型、不是 AC id，不屬宣告位置（§8.2），所以照模板填 §4 不會讓編譯失敗。要讓邊界／錯誤 AT 由 AutoClaude 執行，命名成 `AT-{NNN}-{Y}-E-{n}`（掛在其所屬 AC `AC-{NNN}-{Y}` 之下）並列入 §1。Dev-SDD-DOC 在模板 §4 加一句說明這件事（同檔，§11.2）。

### 8.2 「出現卻未編成」的出聲（定案）

| 項 | 契約 |
|---|---|
| 名稱 | 一律 **`unmapped_at_ids`**（SA 契約已用此名）：adapter 欄 `SddSpec.unmapped_at_ids`、事件、Bridge 回應同名；先前草稿的 `dropped_at_ids`／`spec_at_dropped` 作廢。🔴 與逆向 RTM 的 `unmapped_at_ids`（§8.5）是**兩個不同層的欄位**：這裡是「規格裡出現卻沒編成 step」，那裡是「已編成的 AT 還原後無法歸屬 AC」，不得混用 |
| `appeared`（只掃**宣告位置**） | ①AC 映射列：以豎線字元開頭、第一欄（去空白）形如 `AC-…` 的 Markdown 表格列，取**第三欄**內的第一個寬鬆 AT 字樣 `(?<![\w-])AT-[\w-]+`（寬鬆是為了抓到格式錯的 ID）；②Gherkin：每個標為 `gherkin` 的圍欄程式碼區塊的第一個 `#\s*AT-…` 標頭（同現行「一區塊一個 AT」）。模板佔位 `AT-{NNN}-…` 因 `{` 不在字元集而自然略過。**其餘位置一律不掃**：§3 的清單表（第一欄是 AT）、§4 的邊界表（第一欄是場景類型）、內文散文都不是宣告位置——所以照模板填 §3／§4 不會讓編譯失敗。依首次出現順序去重 |
| `compiled` | 進入 `_AT_ROW`（AT 欄改用 §8.1 的嚴格文法）**且**列的 AC id 等於 AT 前兩段推得的 `AC-<第一段>-<第二段>` 的 AT。AC 不一致的列＝未編成（事件 detail `reason=ac_mismatch`）：逆向 RTM 以 AT 前兩段歸 AC（§8.5），正向若放過不一致的列，兩邊會悄悄歸到不同的 AC |
| `unmapped_at_ids` | `appeared − compiled`（保首見順序）→ `SddSpec.unmapped_at_ids`（新欄，預設空 tuple）。Gherkin 標頭沿用同一嚴格文法與 AC 一致性當對應鍵（`_GHERKIN_AT_ID` 改取寬鬆字樣再驗證，不再靜默截成前綴） |
| adapter | `load_spec` **不拋**（引擎 PRE_RUN 也走它，規格若在編譯後被改動，不能讓引擎在 PRE_RUN 崩潰）；只 `record_event("sdd.at_unmapped", {at_ids, count, spec_path})` |
| `sdd_compile` CLI | 新增模組內例外 `SpecAtUnmappedError(ValueError)`，先於一般 `ValueError` 接住：stderr 列出 ID，**rc 6**（現有 0／2／3／4／5，6 不撞；5 是版本）；**不寫輸出檔**（fail-closed）；無覆寫旗標——修法只有「補進 §1／改成合文法的 ID／刪掉」（D-115-09：CLI 要回非零） |
| Bridge `/sdd/compile` | 回應**永遠帶** `unmapped_at_ids`（陣列，空＝`[]`），**不是錯誤**、仍回 200（D-115-16 採 SA 的 Q5：是否阻擋由消費者決定）；Backend 在匯入解析結果的 `warnings[]` 加 `at_unmapped`（SA 契約 §3.3.2），簽核前由人決定。已編成的 AT 照常產出任務。因此**沒有** `spec_at_dropped` 這個 reason |
| 模板本體 | TCS 模板住在 `docs_template/`，**不是**編譯輸入（模板不可直接改，須複製到 `docs/` 實例化）。〔乾跑〕硬拿未實例化的模板去編譯：§1 的列是佔位（`AT-{NNN}-…`）而略過，§2 示例標頭 `# AT-001-1-1`、`# AT-001-1-2` 卻出現而無對應 §1 列⇒`unmapped_at_ids=["AT-001-1-1","AT-001-1-2"]`⇒CLI rc 6、Bridge 200＋警告。這是預期的大聲失敗，不是缺陷：實例化時示例區塊要刪或改成真實 AC 的 AT。Dev-SDD-DOC 在模板 §2 示例區塊旁加一行註解提醒（同檔，已在 §11.2 的模板列） |

〔乾跑〕判定演算法的原型對 F-SBR 夾具得 `compiled` 3 個、`unmapped_at_ids=[]`；對一份合成規格逐列得預期結果（舊編號 `AT-14-2-1`、AC 不一致 `AC-002-1｜AT-001-1-9`、尾隨文字 `AT-001-3-1 (E2E)`、有標頭無 §1 列的 `AT-001-1-7` 皆在 `unmapped_at_ids`，依首見順序；§3／§4 表格裡的 E 類與清單列、`AT-{NNN}` 佔位列不出聲；合法的 `AT-001-1-E-1` 被編成）。

### 8.3 `spec_file`（定案）

| 層 | 契約 |
|---|---|
| adapter | `load_spec(spec_dir, spec_file=None)`；有 `spec_file`：相對路徑以 `spec_dir` 為基準，`resolve()` 後必須是 `spec_dir` 之下、副檔名 `.md`（不分大小寫）的**檔案**，否則 `FileNotFoundError`／`ValueError`；**不掃描、不套官方命名規則**（呼叫端已具名）。副檔名限制是縱深防禦：檔案內容會進 prompt 與摘要，不能讓路徑指到 `spec_dir` 內任意檔 |
| 路徑可為檔 | `spec_dir` 參數若本身是**檔案**，視為 `spec_file`、`spec_dir` 取其父目錄——引擎 PRE_RUN 的 `load_spec(workflow_path)` 因此不必改 port 簽名 |
| `workflow_path` | 有 `spec_file` 時，`sdd_compile` 與 Bridge 注入**檔案路徑**；無則維持目錄（現行）。〔讀碼〕`detect_workflow_impl` 對顯式 `workflow_type` 不看路徑（`boot_helper.py:92-97`），拓樸儀表板的 `resolve_artifact` 在檔案路徑下找不到產物而回 None，皆無害 |
| `sdd_compile` CLI | 新增 `--spec-file`、`--fsm-project`；`compile_spec(..., spec_file=None, fsm_project=None)` |
| Bridge | `SddCompileIn` 增選填 `spec_file`、`fsm_project`；回應增 `spec_file`（實際採用的規格檔）、`fsm_project`（淨化後的狀態檔鍵）、`frozen_digest`、`unmapped_at_ids`（§8.2）、`spec_format_version`（取自 `SddSpec.spec_format_version`，SA 契約已列） |
| Backend | 路徑 A 的探測／匯入帶 `specFile`（匯入選項或已綁定的 `sdd_spec_file`）；未帶維持現行 |

### 8.4 版本宣告（S-11）與場景宣告（S-12）（定案）

| 項 | 新判準 | 〔乾跑〕 |
|---|---|---|
| 版本宣告 | 宣告＝**行首**（容許 `>`、`*`、`_`、反引號、`-`、空白的裝飾）的 `spec[-_ ]format[-_ ]version`；值＝同行 `[^\d\n]{0,16}(\d+\.\d+)`。行內提及（散文）不算宣告 | 官方行、多一個空白、`** : 2.0`、反引號、全形冒號加空白五種皆解出值（舊樣式對其中三種——多一個空白、`** : 2.0`、全形冒號加空白——解不出而退回預設 1.0，即 S-11 的 fail-open）；散文提及＝未宣告；官方模板行與 F-SBR 夾具皆解出 `1.0` |
| 宣告卻解析不出 | 拒絕：`SpecFormatVersionError`（已有 rc 5／422 `spec_format_version_unsupported` 路徑） | `**spec-format-version**: tbd`⇒宣告但無值⇒拒絕 |
| 場景宣告 | 行首 `scenario` 或 `場景` 加冒號（半／全形）後的英文字；值必須屬 10 個場景（`_SCENARIOS`），否則 `ValueError`（⇒422 `spec_ambiguous`／rc 4）。**優先於**現行的整份文字子字串推斷 | `**場景**: greenfield 全新純函式模組`⇒`greenfield`；表格有 `Integration` 但未宣告場景時舊法會判成 integration、新法在有宣告時不受影響 |
| 無場景宣告 | 沿用現行推斷（不改既有 step_id，避免舊 checkpoint 的 `completed_step_ids` 失效），另 `record_event("sdd.scenario_inferred", …)` 讓推斷可見 | — |
| 模板 | `TEST-CONTRACT-SPEC-TEMPLATE.md` 在 `spec-format-version` 行下新增 `**scenario**: greenfield  <!-- 10 場景之一 -->` | — |

### 8.5 逆向 RTM 的 AC 歸屬（S6；D-115-16）

現況〔讀碼〕：`playbook_to_rtm_adapter.py:31` 的 `^AT-(\d+)-(\d+)-(\d+)$` 只認恰好三段數字；還原不出的 `sdd-` 任務被**略過**（`:70-76`），所以 `total_at` 只含認得的 AT——放寬文法後若不改，帶尾綴的 AT 會從覆蓋率分母悄悄消失（覆蓋率被灌高）。新規則：

| 項 | 契約 |
|---|---|
| 還原 | 對每個 `step_id` 以 `sdd-` 開頭的任務：先取 `task.name` 轉大寫（既有行為），不是 AT 字樣再自 step_id 的 `-at-` 界線之後取該段字串並轉大寫；取得的字串以 `AT_ID_PATTERN` 全比對（§8.1，正向與逆向同一份） |
| 歸屬（mapped） | 符合者：AC＝`AC-<第一段>-<第二段>`（`AT-001-12-3-a`→`AC-001-12`；多段尾綴不影響歸屬），聚合進該 AC 的 passed／total 桶（同現行 `_aggregate_ac` 的語意） |
| 無法歸屬（unmapped） | 取得的字串以 `AT-` 開頭卻不過文法（舊規格的 `AT-14-1-1`、E 類 `AT-001-E-1` 等）：**仍計入** `summary.total_at`，並依完成與否計入 `passed_at`／`failed_at_ids`（AT 級指標不假裝它不存在）；**不進任何 AC 桶**（AC 級指標不被它污染）；列入 `unmapped_at_ids`（排序）與 `summary.unmapped_at`（個數）。完全沒有 `AT-` 字樣的 `sdd-` 任務維持現行（略過＋事件 `rtm_writeback_unresolved_step`） |
| `fully_covered` | `ac_total>0` 且全部 AC 覆蓋，**且 `unmapped_at_ids` 為空**——有無法歸屬的 AT 時不得宣稱全覆蓋（在 `RtmCoverageReport.is_fully_covered` 的判準上加一個條件；這是 SD 對「標 unmapped」的落實，主控可否決） |
| 載體 | `RtmCoverageReport` 增 `unmapped_at_ids: tuple[str, ...] = ()`（additive，與 `weak_regex_at_ids` 同模式）；`render_yaml` 增 `summary.unmapped_at` 與頂層 `unmapped_at_ids`；`render_gap_markdown` 增「無法歸屬 AC 的 AT」一節；`core/ports/rtm_feedback.py` 的 doc 往返（`coverage_report_to_doc`／`coverage_report_from_doc`）同步增欄，舊 doc 缺欄讀回 `()`。Bridge 讀 `RTM-COVERAGE-<project>.yaml` 時缺欄視為 `[]`／0（`GET /autoclaude/runs/{id}/rtm` 的回應欄由 SA 契約定） |
| 大小寫 | 逆向一律轉大寫後比對（既有行為）；尾綴含小寫字母的 ID 可編譯，回報時被大寫化，AC 歸屬不受影響。要避免任何歧義就用大寫尾綴 |

---

## 9. 寫入面權杖（SD-7，對應 G-09）

| 項 | 契約（必須） |
|---|---|
| 名稱（S1 定案） | 環境變數 `BRIDGE_SDD_WRITE_TOKEN`（backend 與 Bridge 共用同一個名稱）；backend 的 Spring 屬性名 `console.bridge.sdd-write-token`（寫在 `application.yml` 的 `console.bridge` 段，值取 `${BRIDGE_SDD_WRITE_TOKEN:}`，`BridgeProperties` 增欄 `sddWriteToken`，沿用該段既有的 `${ENGINE_BRIDGE_URL:…}` 寫法）；HTTP 標頭 `X-Bridge-Token` |
| 產生者 | 部署者一次性產生（≥32 字元隨機；`openssl rand -hex 32`，或 PowerShell 用 `[Convert]::ToHexString(...)` 取 32 位元組）。**repo 內不放任何真值**；`.env.example` 只放 `<YOUR_BRIDGE_SDD_WRITE_TOKEN_MIN_32_CHARS>` 佔位 |
| 持有者 | backend（發送）與 Bridge（驗證）。**前端、引擎子行程、FSM CLI 子行程都不持有** |
| 傳遞 | HTTP 標頭 `X-Bridge-Token`，只在會觸發 FSM 寫入的呼叫帶：`POST /sdd/fsm/{project}:freeze`、含 `sdd` 區塊的 `POST /autoclaude/runs`，以及（主控裁決 D-115-18 ④，2026-10-17 補註）帶 `sdd` 的 run 之 `:resume` 與 `/restore`（它們會 `delegate-enter`）——共四個；console-api 對 resume／restore 一律附標頭，Bridge 只對 SDD run 驗 |
| 兩端未設時（S1 定案） | **Bridge 未設**：對上述兩種請求回 **503 `sdd_write_disabled`**（fail-closed）；不含 `sdd` 的 run 照舊（相容）。**backend 未設**：`POST /api/v1/projects/{id}/sdd/freeze` 回 503 `sdd_write_disabled`（不呼叫 Bridge）；execute 對 SDD 專案**不送 `sdd` 區塊**、照 v1.4 行為跑，並在 201 的 `warnings` 帶 `sdd_governance_inactive`（`cause=token_not_configured`，SA 契約）——相容優先、但不靜默。兩端都未設＝SDD 寫入面整個停用（預設值） |
| 缺／錯 | **403 `sdd_write_forbidden`**（SA 契約的 reason 名；缺與錯同一個 reason，不給探測者區分）；以 `hmac.compare_digest` 比對。backend 收到此 403＝兩端設定不一致，轉 502 並記 ERROR（SA 契約 §1.10.2） |
| 設定檢查 | 有設但短於 32 字元，或仍是 `<…>` 佔位⇒啟動即 fail-loud、不靜默退回停用：Bridge 走 `SettingsError`（與 `settings.py:45-46` 的既有慣例相同），backend 在 `BridgeProperties` 的啟動驗證丟出等價錯誤 |
| 剝除 | 〔讀碼〕`_child_env`（`runner.py:203-210`）以 `dict(os.environ)` 起手、整份繼承 Bridge 自己的環境。必須在合併請求層 `env` 之前**先移除**繼承來的 `BRIDGE_SDD_WRITE_TOKEN`、`SDD_STATE_DIR`、`SDD_PROJECT`（Windows 的 `os.environ` 鍵恆為大寫，比對照此；開發機先在 SDD session 匯出再起 Bridge 是常態，不剝的話引擎子行程會悄悄拿到狀態目錄指標與別的專案鍵），之後**只有**含 `sdd` 區塊的 run 才設 `SDD_PROJECT=<鍵>`；`security.validate_env` 的拒絕清單（`security.py:37-42`）加入 `BRIDGE_SDD_WRITE_TOKEN`、`SDD_PROJECT`、`SDD_STATE_DIR`：請求層 `env` 不得設定它們（422 `forbidden_name`，大聲而不是靜默覆蓋） |
| 稽核 | `AuditLog.record("sdd_write", verb, project, approver, result)`；**絕不記權杖值** |
| compose | `AgentConsole/docker-compose.yml` 對 backend 與 engine-bridge 兩個服務都傳 `BRIDGE_SDD_WRITE_TOKEN: ${BRIDGE_SDD_WRITE_TOKEN:-}`（預設空＝停用；SDD 是選用引擎，不像 `JWT_SECRET` 設成必填） |
| Rule 9 | Bridge 原始碼不得直接寫 `FSM-STATE-*.yaml`；§15 的 AST 鎖 |

**誠實劃界**：權杖只封住 **Bridge 的 HTTP 寫入面**。引擎子行程內的 AI 步驟仍可自己執行框架的 FSM CLI（框架程式碼對它可讀）。縱深在於：(a) 不注入 `SDD_STATE_DIR`；(b) 批次期間 FSM 在 IMPLEMENTATION／AUTOCLAUDE_DELEGATED，`spec-frozen` 轉態不合法（〔乾跑 #5〕rc 1）；(c) 凍結綁內容，竄改規格可偵測（§6）。**不防禦主動對抗的 AI**，與 Bridge 無認證的既有限制（Architecture §12 L-6）同級。

---

## 10. 委派同步（SD-8）

### 10.1 終態對映（證據＝`runner.py` 實際分支；D-115-15 修訂 D-115-10）

🔴 **`delegate-exit --decision done` 的語意是「委派交還控制權、未升級」，不是「成功」**：run 是否成功由後續閘門判（SCG-4 審查、RTM 面板），FSM 不替它背書。所以完成與使用者取消都是 `done`；只有引擎升級型失敗是 `failed`。

| 事件 | 分支〔讀碼〕 | 判定 | FSM 動作 |
|---|---|---|---|
| COMPLETED | `_finish_normally` rc＝0（`runner.py:479-486`；引擎 `main` 以 `0 if result.success else 1` 離開，`main.py:322`） | 最終狀態 COMPLETED | `delegate-exit --decision done`，reason `console-run run=<id> COMPLETED` |
| FAILED·引擎升級 | `_finish_normally` rc≠0 且 `self._escalation` 非空（`_on_state` 於引擎印 `=== STATE: ESCALATION` 時設，`:423-429`；`_failure_reason` 以它為先，`:509-510`） | 最終狀態 FAILED 且 `_escalation` 非空 | `delegate-exit --decision failed`，reason `console-run run=<id> ENGINE-ESCALATION step=<id>: <detail ≤200>`（D-115-10：**只有這一型**） |
| FAILED·額度／token 停機 | `_failure_reason` 的 halted 分支（`:511-512`） | FAILED、無 `_escalation` | **不動**（基礎設施故障不得映成阻塞態） |
| FAILED·引擎異常、被訊號終止 | `:513-517` | 同上 | **不動**（留給 §10.3 的回收點；D-115-15 的「不動」清單沒列它，本檔維持 D-115-10 的原意） |
| FAILED·spawn 失敗 | `_spawn` 的 `OSError`（`:231-235`） | enter 已做、委派從未開始 | **補償**：`delegate-exit --decision done`，reason `console-run run=<id> SPAWN-FAILED delegation not started`（done 回 IMPLEMENTATION＝「沒有進行中的委派」） |
| FAILED·Bridge 關閉 | `terminate_for_shutdown`（`:639-647`）＋`_finalize`（`:443-447`） | `shutting_down` | 不動 |
| FAILED／CANCELLED·孤兒 | `reconcile`／`_reap_orphan`（`:822-867`） | Bridge 重啟 | 不動（不論被標成 FAILED 或 CANCELLED；留給 §10.3 的回收點） |
| CANCELLED（使用者取消） | `_finalize`（`:443-449`）、`stop()` 對 PAUSED 直接收尾（`:553-560`） | 最終狀態 CANCELLED（非孤兒） | **`delegate-exit --decision done`**，reason `console-run run=<id> CANCELLED`（D-115-15 修訂了 D-115-10 的「不動」；〔乾跑 #15〕合法、之後可再委派） |
| PAUSED | `_finish_pause`（`:457-477`） | 委派仍開著，可 `:resume` | 不動 |
| `:resume`／`/restore` 重新 spawn | `resume()`（`:570-587`）、`restore()`（`:589-617`） | | 先重跑 §6.3③ 預檢；FSM 為 AUTOCLAUDE_DELEGATED 且 `playbook_ref` 就是本 run（`run:<本 id>`）⇒直接續（引用別的 run 或外來委派⇒409，由 §10.3 的判定處理）；為 IMPLEMENTATION⇒`delegate-enter` 重進（`playbook_ref` 仍用本 run 的 id）；其他（含 ESCALATION）⇒409 `fsm_state_conflict` 並**不 spawn** |

判定函式建議做成**純函式**（`status`、`escalation`、`stop_requested`…⇒`"done"｜"failed"｜None`）放在 Bridge 的獨立模組，讓對映表可不起子行程單測。

**exit 的容錯**：`delegate-exit` 回 rc 3（FSM 已不在 AUTOCLAUDE_DELEGATED，例如人工已處理）⇒視為「已就位」，記 `SDD_SYNC_STATE_DRIFT` 警告、不失敗；其他非零⇒記 `alert`／audit，並把 `{exit, ok:false, error}` 寫進 run 紀錄，FSM 留在原態（由 §10.3 的回收點或人工處理）。

### 10.2 建立流程順序與預檢表（必須）

```
create(req 含 sdd):
 1  既有驗證 ＋ sdd 唯讀預檢（權杖、adapter.load_spec 的凍結與摘要、§6.3 的匯入摘要、FSM 狀態唯讀讀取）→ 4xx，零副作用
 2  取得 advisory lock（既有）
 3  FSM 寫入（依預檢表）→ rc≠0：釋放鎖、回 409／5xx，尚無任何工作區產物
 4  _materialize（既有）；例外⇒補償 delegate-exit done ＋釋放鎖
 5  start／_spawn（既有）；spawn 失敗⇒補償 delegate-exit done（§10.1）
 6  終態：狀態事件先發布，之後（handle.lock 之外）才呼叫 delegate-exit
```

FSM 寫入在 `_materialize` **之前**，是因為失敗時才不會留下半成品 run 目錄——否則 `reconcile` 下次啟動會把它當作「活躍而無行程」的孤兒標成 FAILED，憑空多一筆帶 `sdd` 資訊的假紀錄。終態才呼叫 exit 且在 `handle.lock` 之外，是因為 CLI 呼叫最壞 20 秒不該卡住 `snapshot()`；代價是「終態事件」到「FSM 回 IMPLEMENTATION」之間有約 0.1 秒（暖機）視窗——**dogfood 的四源對拍必須輪詢到 FSM 離開 AUTOCLAUDE_DELEGATED（上限 30 秒）再比，不得單次讀取**。

| FSM 現況 | 預檢處置 | 備註 |
|---|---|---|
| IMPLEMENTATION | `delegate-enter` | 常態 |
| AUTOCLAUDE_DELEGATED | 回收點（§10.3）：所引用的 run 已終態或不存在⇒`delegate-exit done`（RECLAIMED）→`delegate-enter`；仍活著、或外來委派⇒409 `fsm_state_conflict` | 回收也是 FSM 寫入，在鎖內做 |
| TEST_CONTRACT_NEGOTIATED | `negotiate-exit agreed`→`delegate-enter` | 上次 enter 後 exit 前中斷的自癒（§5.2 C-4） |
| SPEC_FROZEN | `negotiate-enter`→`negotiate-exit agreed`→`delegate-enter` | 首次批次 |
| 其他（含 HUMAN_PENDING、ESCALATION） | 409 `fsm_state_conflict`，`detail.current_state` 帶回 | 草案同；ESCALATION 的出路見 §5.3 |
| 狀態檔不存在 | 404 `fsm_not_found` | Bridge 不 init（A3） |

### 10.3 回收點（D-115-15；必須）

FSM 可能留在 AUTOCLAUDE_DELEGATED 而沒有任何行程（引擎異常結束、額度停機、孤兒、Bridge 關閉都「不動」）。不處理的話，下一個批次會被預檢 409 擋住，直到有人手動 `delegate-exit`。回收點讓**新批次**自己解開陳舊委派，且只在確認「舊 run 已不在跑」時才動手。

🔴 判斷只在 `current_state=AUTOCLAUDE_DELEGATED` 時才讀 `autoclaude_delegated_tracking.playbook_ref`——FSM 檔的 tracking 在 exit 後**不清除**（〔乾跑 #15〕），在 IMPLEMENTATION 上它是歷史殘留欄，不得拿來判斷任何事。判定依序：

| # | 條件 | 處置 |
|---|---|---|
| 1 | `playbook_ref` 缺，或不以 `run:` 開頭（外來委派：人在 SDD session 進入的，〔乾跑 #21〕） | 409 `fsm_state_conflict`，`detail={current_state, reason:"foreign_delegation"}`；Bridge **不碰**——解卡由人在 SDD session `delegate-exit` |
| 2 | 解出 `run_id` 後，Bridge 的 run 登錄（含重啟後由 `run.json` 還原的）**查無此 run** | 視為「不存在」⇒回收 |
| 3 | 該 run 存在，但其 `sdd.state_dir` 或 `sdd.fsm_project` 與本次不同 | 視為外來，同第 1 項 409（引用別的 FSM 專案的 run，不是我們能判斷的） |
| 4 | 該 run 為**活躍**（INITIALIZING／RUNNING／PAUSING／PAUSED／CANCELLING；D-115-15 列的 RUNNING／PAUSED 是其中兩種，過渡態一併視為活躍，因為它們隨時可能繼續寫） | 409 `fsm_state_conflict`，`detail={current_state, run_id, run_status}`。同一個 Console 專案與路徑另由 advisory lock 先回 409（鎖鍵＝專案名加路徑，`locks.py:47-50`）；**不同** Console 專案指向同一個 `(狀態目錄, fsm_project)` 則由這一條回 409（Backend 的部分唯一索引是第一道，這條是 Bridge 側的縱深） |
| 5 | 該 run 為**終態**（`TERMINAL_STATUSES`：COMPLETED／FAILED／CANCELLED） | 回收 |

**回收**＝在鎖內依序：`delegate-exit --decision done`（reason `console-run run=<舊 id> RECLAIMED old_status=<舊終態或 missing> by=<新 id>`）→ `delegate-enter`（`--playbook-ref run:<新 id>`）。FSM 軌跡因此留下完整的「舊委派被回收」一筆（〔乾跑 #16〕兩次呼叫約 0.17 秒）。兩步之間 `delegate-enter` 失敗⇒FSM 停在 IMPLEMENTATION（無委派）、本次建立回 409／5xx 並不 spawn，下次建立從 IMPLEMENTATION 常態進入，不需人工。回收在 Bridge audit 記一筆（含舊 run id 與舊終態）。

被回收的舊 run 若是可 `restore` 的終態（額度停機的 FAILED、取消後的 CANCELLED），之後 `:restore` 走 §10.1 的最後一列：FSM 為 IMPLEMENTATION⇒`delegate-enter` 重進，與新批次不衝突（新批次仍在跑時 `restore` 會因 §10.3 第 4 項得 409）。

`RunRecord` 為此增選填 `sdd`（`spec_dir`、`spec_file`、`fsm_project`、`root`、`state_dir`、`approver`、同步結果；`resume`／`restore` 的重驗與回收判定都從它取值，匯入時的任務摘要則取自工作區已存的 `playbook.yaml`）；`from_dict` 會忽略未知鍵、舊 `run.json` 缺欄走預設，`schema_version` 不變（`runstate.py:50-53`）。**`approver` 與 `fsm_project` 之外不含任何機密**。

---

## 11. 最小侵入白名單（SD-9，D-115-05）

> 取代 `NFR-COMPAT-01`「零侵入」與 `AgentConsole/CLAUDE.md` 鐵律 7、Bridge README 的同款宣稱。**白名單外一律禁止**；名單內每一檔都要有理由與守護測試。

### 11.1 AutoClaude（Dev-AutoClaude；檔案互斥）

| 檔 | 理由 | 守護測試 |
|---|---|---|
| `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py` | 專案選檔（§7.1）、摘要比對呼叫（§6.2）、AT 文法（用 `AT_ID_PATTERN`）與 `unmapped_at_ids`、AC 一致性（§8.1-8.2）、`spec_file`（§8.3）、版本與場景宣告（§8.4）、`_POST_FROZEN_STATES` | `AutoClaude/tests/infra/test_sdd_to_playbook_adapter.py`（擴充） |
| `_sdd_frozen_gate.py`（**新增**，置於 `autoclaude/infra/adapters/`） | FSM 狀態定位＋摘要比對抽出成可獨立測的純函式群。LOC 事實：該 adapter 實體 426 行、非空 392 行、**閘門計價 279**（`count_loc` 只算斷言行，ADR-XPLAT-013；adapter 層級 ≤400，餘裕 121，不是 8）；凍結閘邏輯約 110 行若留在 adapter 會到約 389（〔估〕），所以抽出——理由是職責分離與可單測，同時守住餘裕 | `test_sdd_frozen_gate.py`（新增，置於 `AutoClaude/tests/infra/`） |
| `AutoClaude/autoclaude/core/ports/spec_source.py` | `AT_ID_PATTERN`（§8.1，正向逆向共用）；`SpecDigestMismatchError`；`SddSpec` 增三個有預設值的欄（`fsm_project`、`frozen_digest_status`、`unmapped_at_ids`），舊的位置／關鍵字建構不受影響；docstring | `AutoClaude/tests/core/ports/test_spec_source.py`（擴充）；既有用法不破：`AutoClaude/tests/plugins/test_sdd_governance.py`、`AutoClaude/tests/plugins/test_rtm_writeback_plugin.py` |
| `AutoClaude/autoclaude/tools/sdd_compile.py` | `--spec-file`、`--fsm-project`、rc 6（`SpecAtUnmappedError`）、`workflow_path` 規則 | `AutoClaude/tests/tools/test_sdd_compile_cli.py`（擴充） |
| `AutoClaude/autoclaude/infra/adapters/playbook_to_rtm_adapter.py` | 逆向 RTM 歸屬（§8.5，S6／D-115-16）：還原改用 `AT_ID_PATTERN`、前兩段歸 AC、無法歸屬者計入 `total_at` 並標 unmapped、`render_yaml`／`render_gap_markdown` 增欄 | `AutoClaude/tests/infra/test_playbook_to_rtm_adapter.py`（擴充：多段尾綴歸屬、unmapped 計入分母、`fully_covered` 的新條件、舊三段形不變） |
| `AutoClaude/autoclaude/core/ports/rtm_sink.py`、`AutoClaude/autoclaude/core/ports/rtm_feedback.py` | `RtmCoverageReport.unmapped_at_ids`（additive）；history 的 doc 往返同步增欄（舊 doc 缺欄讀回 `()`） | `AutoClaude/tests/core/ports/test_rtm_feedback.py`（擴充：往返含新欄、舊 doc 相容）；既有 `AutoClaude/tests/infra/test_rtm_file_sink.py`、`AutoClaude/tests/infra/test_rtm_file_feedback_source.py` 維持綠 |
| `AutoClaude/autoclaude/core/wiring.py` | **僅 docstring**：`:304-306` 寫 `build/reports/rtm/`，實際是 `<checkpoint_dir>/rtm`（G-16） | 無行為測試；核對法＝`git diff -U0` 只含註解行 |
| `AutoClaude/tests/**` | 上列測試 | `python -m pytest tests/ -q`、`lint-imports`（`adapters` 互 import 不違反 plugins 互不 import 的契約）、`ruff check <改到的檔>`、`python AutoClaude/tools/check_loc_budget.py --json` |

既有的 `AutoClaude/tests/integration/test_sdd_bridge/test_rollback_compat.py`（用歷史版本自己的 `state_loader` 產真品狀態檔再編譯）**必須維持綠**：它證明「舊狀態檔無摘要」的相容路徑。

### 11.2 AISDLC_SDD（僅 LATEST；`python AISDLC_SDD/scripts/sdd_version.py` 現查）

**RT 棒（Dev-SDD-RT；版內相對路徑）**

| 檔 | 理由 | 守護測試 |
|---|---|---|
| `tools/fsm_runtime/state_loader.py` | `state_dir()`、`record_spec_frozen` 增 `spec_doc_digests`／`approved_by` | `test_sdd_state_dir.py`、`test_cli_bridge_verbs.py`（新增，皆置於 `tools/fsm_runtime/tests/`）；既有 `test_template_location.py` 維持綠 |
| `tools/fsm_runtime/fsm_runtime.py` | 遙測預設（A8）、`_reset_today_ledger` 目錄（A2）、`record_spec_frozen` 簽名與先驗後改、`_assert_allowed_under_auto_compact` 放行 PowerShell（§12）、`_cli` 新動詞與旗標 | `test_cli_bridge_verbs.py`、`test_settings_matcher_powershell.py`；既有 `test_phase_z.py`、`test_phase_h.py` 維持綠 |
| `spec_digest.py`（**新增**，置於 `tools/fsm_runtime/`） | 摘要純函式（§4.3） | `test_spec_digest.py`（新增） |
| `tools/fsm_runtime/spec_monitor.py`、`production_monitor.py`、`subagent_contract.py` | A5～A7 目錄解析 | `test_sdd_state_dir.py`；各自既有測試維持綠 |
| `tools/fsm_runtime/conversation_ledger.py` | PowerShell 估算分支（§12） | `test_settings_matcher_powershell.py`；既有 `test_conversation_ledger.py` |
| `.claude/hooks/context_ledger_pre.py`、`.claude/hooks/context_ledger_post.py` | A3／A4、PowerShell 備援分支 | 既有 `test_context_ledger_pre_hook.py`、`test_context_ledger_post_hook.py` 維持綠＋新測試 |
| `.claude/settings.json` | 兩個 matcher 加 `PowerShell`（§12）；**受保護路徑**，改動走 acceptEdits 儀式，子代理成品 staged 交主控 | `test_settings_matcher_powershell.py` |
| `tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml` | 僅註解：兩個新鍵 | `test_template_location.py` |
| `tools/fsm_runtime/tests/conftest.py`、`test_transitions.py`、`test_conversation_ledger.py` | S-09 沙盒與環境洩漏、S-16 `_dead_pid` 可攜寫法 | 整套跑完 `build/reports/fsm/` 清單前後相同 |
| `AISDLC_SDD/scripts/ci-gate.sh`＋新增新鮮度測試（置於 `AISDLC_SDD/scripts/tests/`） | S-13：下限重釘（實測值−8）與「下限不得低於實測的特定比例」 | 該新增測試 |
| `EVOLUTION_LOG.md`、`releases/CHANGELOG.md`、`AISDLC_SDD/FRAMEWORK_STATUS.md`（重生） | 演化紀錄與狀態快照 | `python AISDLC_SDD/scripts/framework_status_snapshot.py --check` |

**DOC 棒（Dev-SDD-DOC）**

| 檔（版內相對路徑，除標明者） | 理由 |
|---|---|
| `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` | S-01 每個閘門／Human Checkpoint／SPEC_FROZEN 的確切指令（bash＋PowerShell 雙形態、cwd＝版本目錄、禁裸 `cd`、帶 `--digest`）；§13 增量條款 |
| `.claude/skills/sdd-gate/SKILL.md`、`.claude/skills/spec-compliance-check/SKILL.md`、`.claude/skills/stage-compaction/SKILL.md`（＋ `sync_exposed_skills.py --write` 重生上一層 `AISDLC_SDD/.claude/skills/` 鏡像） | S-01／G-10 |
| `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` | S-06／G-16：§5 未落地字樣、evaluator 範本、exit code 補 5／6、失效連結；補「Console／Bridge 路徑」單一 SOP 與「何時走 SDD 迴圈」判準；AT 文法、`unmapped_at_ids` 與逆向 RTM 的歸屬規則（§8） |
| `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`、`tools/fsm_runtime/README.md` | `SDD_STATE_DIR` 一句；CLI 動詞表（S-07） |
| `docs_template/sdd/testing/TEST-CONTRACT-SPEC-TEMPLATE.md` | `**scenario**:` 欄、§4 一句（要由 AutoClaude 執行的邊界／錯誤 AT 命名為 `AT-{NNN}-{Y}-E-{n}` 並列入 §1；`AT-{NNN}-E-n` 僅為文件編號、不會被編譯，§8.1）、§2 示例區塊旁一行「實例化時刪除或改成真實 ID」註解（§8.2）、SCG-4 命名（S-08）；AT 文法一行（`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段＝所屬 AC，§8.1） |
| `docs_template/sdd/testing/TEST-STRATEGY-SPEC-TEMPLATE.md`、`docs_template/sdd/testing/RTM-TEMPLATE.md`、`cicd/SDD_TESTING_CICD.md`、`cicd/SDD_GREENFIELD_CICD.md`、`scenarios/testing/SDD_TESTING_ENHANCEMENT.md`、`scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md` | S-08 另六處 SCG-4 英文名 |
| `README.md`、`FILE_DIRECTORY_RULES.md`、`AISDLC_SDD_UPGRADE_SOP.md`、`AISDLC_SDD_UPGRADE_CHECKLIST.md` | S-07 版本中性化與訂正 |
| `AISDLC_SDD_INIT.md`、`agent/specialized/sdd-prd-to-playbook-zh.yaml`、`agent/specialized/sdd-playbook-compiler-zh.yaml` | S-19 路徑限定；compiler 的 exit code 清單補 5／6 |
| `AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD/.claude/settings.local.json.example` | S-15（Rule 2 報告位置）、S-18（過期範例） |

文件類的守護＝`framework_status_snapshot.py --check`、`sync_exposed_skills.py --check`、`skill_header_sync`、既有各 lint 與 `AISDLC_SDD/scripts/ci-gate.ps1`；**不新增只為文件而設的鎖**（避免重釘稅）。

### 11.3 白名單外仍禁止，與機械核對法

| 禁止 | 核對（QA 於 W5 現跑；`<起點>`＝W2 開工前的 commit，由主控記錄） |
|---|---|
| 改任何非 LATEST 的 SDD 版本目錄（含凍結基線與中間歷史版） | `git diff --name-only <起點> HEAD -- AISDLC_SDD` 的輸出，除 `AISDLC_SDD/scripts/**`、`AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD/FRAMEWORK_STATUS.md`、`AISDLC_SDD/.claude/**` 與 LATEST 目錄外，必須為空 |
| 改 `_HAPPY_PATH` 或任何 `*.tla`（Rule 9.18.1，免跑 TLC 的前提） | `git diff <起點> HEAD -- 'AISDLC_SDD/*/tools/fsm_runtime/transition_rules.py' 'AISDLC_SDD/*/tools/fsm_runtime/formal'` 必須為空 |
| `AutoClaude/**` 白名單外的檔 | `git diff --name-only <起點> HEAD -- AutoClaude` 的每一行必須出現在 §11.1 的檔或 `AutoClaude/tests/**` |
| LATEST 內白名單外的檔 | 同上，對 §11.2 兩張表與 `tools/fsm_runtime/tests/**` |
| 根層 `tools/`、`.claude/`、`.github/` | 對這三個路徑的 `git diff --name-only <起點> HEAD` 必須為空（若 QA 認為需要，走收尾單人窗口，鐵律七） |

---

## 12. S-02 的 LATEST 半（SD-10）

**問題**：版本目錄 `.claude/settings.json` 的兩個 matcher 不含 `PowerShell`（PreToolUse `:30`、PostToolUse `:46`），Windows 唯一的 shell 工具不受 FSM 守門。**單純加 matcher 會引入死鎖**：

| 站點 | 現況 | 加入 `PowerShell` 後 |
|---|---|---|
| `fsm_runtime.py:722`（`_assert_allowed_under_auto_compact`） | AUTO_COMPACT_PENDING 期間只放行 Read、有限的 Write／Edit 路徑、**Bash**（讓 `/stage-compaction` 能跑 `complete-auto-compact`） | PowerShell 會被拒（`TransitionError`）⇒ Windows 上 FSM 卡在 AUTO_COMPACT_PENDING 而唯一的 shell 被封，**無法跑收尾指令**，死鎖 |
| `conversation_ledger.py:914`（`estimate_tool_tokens`） | `Bash` 才估指令 token | PowerShell 估 0，帳本漏記 |
| `.claude/hooks/context_ledger_pre.py:179`（`_estimate_tokens` 備援） | 同上 | 同上 |

**設計（必須）**：

1. `.claude/settings.json`：PreToolUse matcher＝`Write|Edit|Read|Bash|PowerShell|NotebookEdit|Task|Agent|Workflow`；PostToolUse matcher＝`Write|Edit|Read|Bash|PowerShell|NotebookEdit`（`PowerShell` 緊接 `Bash`）。
2. 三個站點的 `Bash` 判斷改為 `{"Bash", "PowerShell"}` 同形處理；PowerShell 的指令文字在 `tool_input.command`（與 Bash 同鍵，本機根層 lint hook 以 `matcher: PowerShell` 攔下裸 `Set-Location` 的真實事件佐證工具名＝`PowerShell`）。
3. 回歸鎖放**新檔** `test_settings_matcher_powershell.py`（置於 `tools/fsm_runtime/tests/`；不併入 `test_settings_matcher_r145.py`，該檔 docstring 綁定那一輪的 Agent／Workflow 議題；夾具依該檔「抄而非共用」的慣例複製）。四組斷言：(a) 兩個 matcher 的 token 集合含 `Bash` 與 `PowerShell`；(b) `estimate_tool_tokens("PowerShell", {"command": …})` 與同輸入的 `Bash` 相等；(c) AUTO_COMPACT_PENDING（owner session）下 `assert_tool_allowed("PowerShell", None)` 不拋、與 Bash 對稱；(d) ESCALATION 下 `context_ledger_pre.main()` 對 `tool_name=PowerShell` 回 `deny`。
4. **根層** `.claude/settings.json` 的 router 條目屬守衛面，本輪無暴露證據⇒登理論洞，附再開症狀「Windows 設 `SDD_ACTIVE_VERSION` 的真實 session，其 CONTEXT-LEDGER 缺 PowerShell 呼叫」（D-115-09）。

〔未驗〕沒有起 `claude --debug hooks` 做「PowerShell 呼叫確實觸發 SDD hook」的活體正向驗證（體檢報告同樣只做了靜態推論）；落地後主控須補一次正負兩面（根層 CLAUDE.md〈hook 載具〉的驗收規則）。

---

## 13. 增量（delta）條款草案（SD-11，給 Dev-SDD-DOC；≤200 字）

> 增量條款：變更限於已凍結系統的單一 Feature 時，SCG-0～3 各清單項可用「追溯 ID＋已凍結上位文件路徑與凍結摘要」滿足，於 TCS 檔頭〈增量追溯表〉逐項列出，免重寫整份。增量文件集＝FRD-lite（US／AC 併入 TCS 檔頭）＋TCS。僅新架構決策才另立 ADR，僅對外 API／事件契約變更才另附 OpenAPI delta。引用不得指向未凍結文件；未列入追溯表視為未滿足。

落點：`SDD_SPEC_FIRST_GATE.md` 的閘門通過標準前一節、`sdd-gate` 與 `spec-compliance-check` 兩支 skill 的檢查表各引用一次。**不動 `_HAPPY_PATH`**。判斷型 skill 可能把條款讀成放水（草案 §5.1-5）：dogfood 前半段由 QA 獨立審視；「未列入即未滿足」那句是對放水的結構性回應（省略不是 N/A）。

---

## 14. 後果、替代方案與誠實劃界

### 14.1 後果與誠實劃界

| 項 | 內容 |
|---|---|
| 好處 | Console 路徑第一次能驅動 SDD 前半段（核准凍結）與後半段（談判／委派同步）；凍結綁內容；選檔不再 fail-open；`SDD_STATE_DIR` 讓 Docker 唯讀掛載可行 |
| 代價 | Bridge 多一個寫入面（由權杖、動詞白名單、AST 鎖圍住）；`sdd_compile` 對「出現卻未編成」的 AT 變嚴（CLI rc 6；Console 路徑是 200＋警告）；AT 文法變窄（首段須三位、第二段須數字）——既有資料不受衝擊（§8.1 的掃描），但舊規格若用兩位首段或字母第二段，其 AT 會列入 `unmapped_at_ids`；框架自己的狀態目錄不指定專案就過不了凍結閘；Bridge 多維護一份 `sanitize_component` 鏡像（由對拍測試守）；`delegate-exit done` 的語意改為「交還控制權」，FSM 軌跡不再區分成敗（成敗由後續閘門與 RTM 判，取消與完成靠 reason 字串區分） |
| 已知邊界（未修，各附再開症狀） | ①狀態檔無跨行程鎖，SDD session 與 Bridge 同時寫＝競態（再開：觀測到 `escalation_history`／`decision_trace` 遺失）；②引擎子行程內的 AI 仍可呼叫 FSM CLI（§9 劃界）；③R-9.20.3 獨立性不滿足（§5.2）；④外部專案模式下由人觸發的 SCAFFOLD_GC／LEARNING_COMMIT 等仍寫框架 `build/reports/*`（再開：外部專案要在 Console 內跑這些）；⑤`FSM-STATE-*.yaml` 的 `os.replace` 無 Windows 共享違規重試（體檢理論洞；Bridge 自造的那一半由 §3.5 互斥消除） |
| 〔未驗〕 | Docker 容器級（唯讀 `/sdd`＋`PYTHONDONTWRITEBYTECODE`＋遙測關）；Windows 上真 claude 的 SDD 批次（草案 §5.1-1）；`claude --debug hooks` 對 PowerShell matcher 的活體驗證（§12）；摘要在 NFC／NFD 檔名跨平台的行為 |
| 延後（只列已知再開症狀，其餘同草案 §5.2） | Console「退回修改」（須改 `_HAPPY_PATH`＋TLA）；「解除綁定」端點（改綁已可由編輯 `sdd_project` 達成）；Console 內的恢復動詞（D-115-15：恢復留在 SDD session；再開症狀＝使用者回報「ESCALATION 後要在終端機操作太難」）；`negotiate-exit underspecified` 的 UI |

### 14.2 替代方案

| 方案 | 判定 | 理由 |
|---|---|---|
| Bridge 直接寫 `FSM-STATE-*.yaml` | 否決 | Rule 9 絕對禁令 #1；繞過 `FSMRuntime` 就丟掉 `decision_trace`、重試計數重置、`.bak` 輪替與前置狀態檢查（〔乾跑 #5〕非法轉態在 runtime 內被擋，直接寫檔則無人擋） |
| Bridge `import tools.fsm_runtime`（行程內呼叫 SDD） | 否決 | 與 ADR-XPLAT-010 §2.1 的精神相反（兩樹以行程與資料產物為界）；`state_loader` 匯入時就載入共用淨化模組並在缺 PyYAML 時 `SystemExit`；遙測旗標與狀態目錄是**行程級**環境，行內呼叫無法乾淨隔離；子行程邊界反而讓固定環境（§3.5）可機械斷言。代價（每次約 0.1 秒，〔乾跑 #13〕）可忽略 |
| 保持 D22 原樣（Console 只讀） | 否決 | C2（Console 核准凍結、FSM 與 Console 稽核互相對得上）無法成立；SDD 前半段沒有 Console 驅動面；委派態沒有生產者；掌舵者 T1 原文明示可調整兩引擎 |
| 把 `SDD_STATE_DIR` 也注入引擎子行程 | 否決 | 引擎沒有任何讀者；只會給子行程內的 AI 步驟一個現成的 FSM CLI 指向（§7.3、§9 劃界） |
| 摘要用原始 bytes | 否決 | 〔乾跑〕CRLF 與 CR 檔與 adapter 摘要不等，Windows 編輯器存成 CRLF 是常態，每次比對假紅（§4.3） |
| 為取消／停機另增 `delegate-exit` 第三個決定值（如 `aborted`→IMPLEMENTATION） | 不採 | D-115-15 讓取消直接走既有的 `done`（語意＝交還控制權），其餘不動的終態靠回收點（§10.3）解陳舊；不必改 `exit_autoclaude_delegated` 的對映與其既有測試面。再開症狀：稽核者需要在 FSM 軌跡裡把「取消」與「完成」分開看（現靠 reason 字串區分） |
| 回收規則只看「Bridge 有沒有活躍的同 `fsm_project` run」（SA 的 Q3 建議） | 不採 | D-115-15 以 FSM 記的 `playbook_ref` 所指的 run 為準：能辨認外來（人進入的）委派而不碰、也不會把別的 Console 專案的活躍 run 當成陳舊（§10.3） |
| 佔位 P0 專案（先建專案凍結、匯入再產生另一個專案；SA 的 Q1 解法） | 不採 | D-115-14：一個 FSM 專案綁兩個 Console 專案，兩個批次可同時認領同一個 AUTOCLAUDE_DELEGATED；改以 Console 專案為錨（§7.2） |
| 略過談判閘（SPEC_FROZEN 直達 IMPLEMENTATION） | 否決 | 靜默略過 R-9.20.2，軌跡少一段（§5.2） |
| `SDD_STATE_DIR` 接受相對路徑 | 否決 | 同一變數在 Bridge、hook、人的 shell 指向不同目錄＝靜默的檔案分裂（§3.2） |
| Bridge `/sdd/compile` 對 `unmapped_at_ids` 回 422（fail-closed） | 不採 | D-115-16 採 SA 的 Q5：Bridge 回 200＋`unmapped_at_ids`、Console 轉成匯入警告、簽核前由人決定；CLI 仍 rc 6 fail-closed（D-115-09）。代價：Console 路徑上人可以帶著警告簽核。再開症狀：有人帶警告簽核後執行，回報「step 數少於規格」（§8.2） |
| 白名單以測試檔機械強制（根層 unittest） | 不採 | 根層 `tools/tests` 有重釘稅；改由 QA 現跑 `git diff` 核對（§11.3），並以 Bridge 側測試釘住動詞白名單 |

## 15. 驗證：條款與守護測試

| 條款 | 守護（新增者標「新」；測試檔名只列名，位置見 §11） | 反向對照（拿掉修法必須變紅） |
|---|---|---|
| §3.2 解析優先序、相對路徑拒絕、預設不變 | `test_sdd_state_dir.py`（新） | 把 `state_dir()` 改回常數⇒紅 |
| §3.3 外部專案模式遙測預設關、顯式值優先 | 同上（先造「有 `SDD_STATE_DIR`、無旗標」呼叫 `transition`，斷言 `governance/rules/*.yaml` 內容雜湊不變） | 移除新分支⇒雜湊變 |
| §3.4 A2～A7 站點跟隨 | 同上（逐站點以暫存目錄起子行程或匯入後斷言路徑） | — |
| §3.4 沙盒 | 整套前後 `build/reports/fsm/` 清單相同 | 還原 `SDD_PROJECT` 洩漏⇒清單多出 `FSM-STATE-test-*` |
| §3.5、§9 CLI 環境／權杖／剝除 | Bridge 的新測試：以「假 SDD 樹」（暫存目錄內放一支只回放 JSON 的 `tools/fsm_runtime/fsm_runtime.py` 假模組）真起子行程，斷言 argv、cwd、環境集合（無 `BRIDGE_*`）、逾時殺樹；權杖矩陣 503／403／通過；`_child_env` 無權杖，且在 Bridge 自己的環境帶 `SDD_STATE_DIR`／`SDD_PROJECT` 時，不含 `sdd` 區塊的 run 的子行程環境兩者皆無、含 `sdd` 區塊的只有 `SDD_PROJECT`；`validate_env` 拒 `SDD_*` | 拿掉剝除步驟⇒子行程環境出現 `SDD_STATE_DIR`⇒紅 |
| §4 四動詞與 `spec-frozen` 擴充 | `test_cli_bridge_verbs.py`（新）：以 `SDD_STATE_DIR=<暫存>` 起**真 CLI** 子行程，逐動詞驗 rc 表、單行 JSON、`--must-exist` 不建檔、摘要鍵與 CRLF 正規化；舊動詞輸出逐字不變 | 把非法轉態 rc 改成 2⇒紅 |
| §4.3／§6 摘要一致性 | Bridge 對拍測試：同一批 LF／CRLF／CR／BOM 檔，CLI 輸出的摘要＝adapter 的 `spec.digest`＝Bridge 鏡像 | 改用原始 bytes⇒CRLF 兩列紅 |
| §5 談判對映與恢復 | 〔乾跑〕已證；Bridge 測試釘住 reason 格式與 `ALLOWED_VERBS`；SDD 側 `test_phase_z.py`／`test_phase_h.py` 既有轉態鎖維持綠 | — |
| §6.2 adapter 判定表 | `test_sdd_to_playbook_adapter.py`＋`test_sdd_frozen_gate.py`：已驗證／缺／不在清單／不吻合／聯集後者勝／尾段比對（Docker 路徑不同） | — |
| §7.1 選檔 | 同上：兩專案共處（一凍結一未凍結）只認被指定者；不指定且多檔⇒fail-closed；以 `project` 欄位反查；`AUTOCLAUDE_DELEGATED` 放行 | 還原字母序第一個⇒紅（體檢 S-05 的探針形態） |
| §7.4 專案名 | Bridge 對拍測試：以路徑載入 `component_sanitizer.py`，對 §7.4 的 21 個樣本＋模糊集逐一比對 `fsm_component()`；`GET /sdd/fsm/訂單系統` 通過 | — |
| §8.1／§8.2 編譯契約 | adapter 與 `test_sdd_compile_cli.py`：文法接受／拒絕表（§8.1 的 17 個樣本）、`unmapped_at_ids`（窄宣告位置：AC 列第三欄與 Gherkin 標頭；§3／§4 表格與佔位列不出聲）、AC 一致性、CLI rc 6 且不寫檔、`spec_file` 三向（檔內／檔外／非 `.md`）、版本與場景表；F-SBR 夾具（`AutoClaude/scripts/bridge_e2e/wordcount/` 下的 TCS）編出與舊文法相同的 3 個 AT 且 `unmapped_at_ids` 為空（〔乾跑〕已驗）；官方模板的版本行與 `**scenario**:` 行解出預期值，未實例化的模板本體得 rc 6（§8.2「模板本體」列）；Bridge 測試：`/sdd/compile` 對含未編成 AT 的規格回 200 且 `unmapped_at_ids` 非空 | 放寬回舊的 `AT-[\d\-]+`⇒帶尾綴的 AT 被靜默丟掉的案例紅；Bridge 改回 422⇒200 案例紅 |
| §8.5 逆向 RTM 歸屬 | `test_playbook_to_rtm_adapter.py`（擴充）：多段尾綴歸 AC（`AT-001-12-3-a`→`AC-001-12`）、不符文法者計入 `total_at`／`failed_at_ids`／`unmapped_at_ids` 而不進 AC 桶、有 unmapped 時 `fully_covered` 為 False、舊三段形輸出逐位元不變；`test_rtm_feedback.py`（擴充）：往返含新欄、舊 doc 缺欄讀回 `()` | 還原回舊的 `^AT-(\d+)-(\d+)-(\d+)$`（略過不認得者）⇒unmapped 案例紅 |
| §7.2 綁定（Backend） | Backend 測試（SA 的 RTM 草案已列 `SchemaMigrationIT`、`ProjectApiIT`、`ImportApiIT`，另加凍結 IT）：有效值＝`sdd_project` 否則專案名、第一次成功使用寫回、唯一性衝突回 409 且**未呼叫 Bridge 寫入**、`targetProjectId` 併入與「專案已有不同綁定」409、不帶 `targetProjectId` 的新專案回填、沒有 `sdd_not_bound` 路徑 | 拿掉先檢查後寫入的順序⇒衝突案例出現 Bridge 寫入而紅 |
| §4.4 參數值格式 | `test_cli_bridge_verbs.py` 與 Bridge 測試釘住：`playbook_ref` 前綴 `run:`、預設階段名 `Stage-<n>`、六種 `--reason` 組字、`approver` 含 `;` 或控制字元⇒422、使用者理由 1～500 字且不靜默截斷 | — |
| §10 委派對映與順序 | Bridge 測試（假 SDD 樹＋既有替身引擎）：預檢表每一列、`ALLOWED_VERBS`、終態對映每一列（取消⇒`done`、引擎升級⇒`failed`、其餘不動）、spawn 失敗補償、§10.3 回收判定五列（外來委派／查無 run／他專案的 run／活躍 run／終態 run）、`resume`／`restore` 的 409；`_materialize` 之前寫 FSM（失敗時工作區無 `run.json`） | 把取消改回「不動」⇒取消案例紅 |
| Rule 9 | Bridge 原始碼的 AST 鎖：出現字串 `FSM-STATE` 的模組不得含寫入形態呼叫（`open` 寫模式、`write_text`／`write_bytes`、`os.replace`／`rename`、`shutil` 複製移動、`unlink`）；唯一提到 `tools.fsm_runtime.fsm_runtime` 的子行程呼叫處受 `ALLOWED_VERBS` 限制 | — |
| §11.3 白名單 | QA 於 W5 現跑的 `git diff` 核對（零根層測試，避免重釘稅） | — |
| §12 PowerShell | `test_settings_matcher_powershell.py`（新）四組斷言 | 還原 `fsm_runtime.py:722`⇒(c) 紅 |
| `_HAPPY_PATH`／TLA 不變 | `git diff` 對 `transition_rules.py` 與 `formal/` 為空（TLC 為 N/A，證據＝空 diff） | — |

---

## 附錄 A：與 improving_115 §4.3（Architect 草案）的差異，逐條

| # | 項 | 草案 | 本 ADR | 理由 |
|---|---|---|---|---|
| A-1 | CLI rc | 0 成功、2 轉態不合法 | 0／1 非預期／**2 argparse**／**3 轉態不合法**／4 參數值／5 狀態檔；失敗也印單行 JSON | argparse 佔用 2；〔乾跑 #5、#10〕現行非法轉態是 1 |
| A-2 | CLI 旗標 | `spec-frozen --reason`、`--doc` 計 sha256、缺檔 rc 非 0 | 加 `--digest`（不帶＝現行行為）、`--root`、`--approver`、`--json`；全域 `--must-exist`；四新動詞 `--reason` 必填；摘要＝**換行正規化後的 UTF-8 文字**的 sha256（非原始 bytes；非 UTF-8 rc 4 `doc_not_utf8`）；缺檔 rc 4 `doc_not_found` | 保舊測試與驅動腳本；CRLF 假紅；〔乾跑 #12〕CLI 會替不存在專案建檔 |
| A-3 | 引擎子行程環境 | 注入 `SDD_PROJECT`、`SDD_STATE_DIR` | 只注入 `SDD_PROJECT`；CLI 子行程才有 `SDD_STATE_DIR`；CLI 環境移除所有 `BRIDGE_*`／`SDD_*`；`-W ignore::RuntimeWarning` | 最小權限；adapter 向上搜尋即可；〔乾跑 #14〕 |
| A-4 | `sdd` 區塊 | `{spec_dir, fsm_project}` | 加 `spec_file?`、`root?`、`approver?`（欄名採 SA 契約，D-115-16；1～100 字、無控制字元、不含 `;`；省略記 `console`，Backend 永遠送具名人） | 談判 reason 要記簽核人（§5.2 C-1）；多 TCS（S-04）；狀態目錄推導 |
| A-5 | `:freeze` | body `{root, stage, docs[], approver, reason}` | 加選填 `expected_digests`；`docs[]` 必含 TCS；成功回應帶 `spec_doc_digests` | 核准人看到的版本＝凍結的版本（TOCTOU） |
| A-6 | `/sdd/compile` | 只有 `spec_dir` | 請求加 `spec_file?`、`fsm_project?`；回應加 `spec_file`、`fsm_project`、`frozen_digest`、`unmapped_at_ids`（永遠出現，非空仍回 200）、`spec_format_version`；摘要不符＝409 `spec_digest_changed`（不是 422）；**沒有** `spec_at_dropped` | 綁定回填、多 TCS、S-03；S7 與 D-115-16 的 Q5 |
| A-7 | 錯誤 reason | `spec_not_frozen`、`spec_digest_changed`、`fsm_state_conflict`、`sdd_write_disabled`、403 | 403 的 reason 名＝`sdd_write_forbidden`（SA 的名）；另有 `sdd_block_invalid`（422）、`sdd_cli_failed`（502）、`sdd_cli_timeout`（504）、`sdd_invalid_argument`（422）、`sdd_binding_conflict`（409，Backend）；`fsm_state_conflict` 的 `detail` 另帶 `reason:"foreign_delegation"`／`run_id`／`run_status`（§10.3）；**沒有** `sdd_not_bound`（D-115-14 後不存在未綁定狀態） | 各自對應 §4.1 rc 表、§7.2 與 §10.3 |
| A-8 | 預檢表 | IMPLEMENTATION 放行、SPEC_FROZEN 走談判、其餘 409 | 另增 TEST_CONTRACT_NEGOTIATED（自癒）、AUTOCLAUDE_DELEGATED（回收點：終態或不存在⇒`delegate-exit done`＋`delegate-enter`；活躍或外來⇒409）兩列 | §5.2 C-4、§10.3（D-115-15） |
| A-9 | 生命週期順序 | spawn 前預檢、終態呼 exit | 預檢（唯讀）→鎖→**FSM 寫入**→`_materialize`→spawn；補償；終態在 `handle.lock` 之外呼叫；`resume`／`restore` 重驗 | 失敗不留半成品；不卡 `snapshot()` |
| A-10 | `GET /sdd/fsm/{project}` | `phase`、`escalation_history` | 另須加 `escalation_provenance`（辨識委派失敗）與 `fsm_project`（淨化後的狀態檔鍵，§7.2 的寫回與唯一性檢查要用）；建議再加 ESCALATION 時的 `recovery`（SA 可不採，前端用模板） | 給 Console 明確的失敗後作法（§5.3）；〔乾跑 #7〕trace 不可靠；現有 `project` 欄是檔內原名、不是鍵 |
| A-11 | 專案名規則 | 與 `sanitize_component` 一致 | Bridge 鏡像 `fsm_component()`＋輸出域判準取代 `routers/sdd.py:18` 的白名單 regex；進入 Bridge 的名字一律先淨化 | 〔乾跑〕舊白名單只接受 14／21 |
| A-12 | Backend 綁定欄 | `sdd_project`、`sdd_spec_dir`；路徑 A 成功時回填 | 加 `sdd_spec_file`（Flyway `V12__project_sdd_binding.sql`）；Console 專案為錨（D-115-14）：綁定＝`execution_path`＋`sdd_project`，`sdd_project` 預設＝專案名（Bridge 淨化、Backend 不淨化）、第一次成功使用時寫回；`(execution_path, sdd_project)` 部分唯一索引，**先以唯讀 GET 取 canonical 鍵、檢查唯一、之後才呼叫寫入端點**；`targetProjectId` 併入既有專案；衝突 409 `sdd_binding_conflict`；核准凍結請求**沒有** `binding` 欄 | 精確指到 TCS；防兩專案認領同一 FSM；解開「先凍結後匯入」的循環依賴 |
| A-13 | 權杖 | 未設 503、錯 403、`_child_env` 剝除 | 加：backend 屬性 `console.bridge.sdd-write-token`；backend 未設時 freeze 503、execute 不送 `sdd` 並以 `sdd_governance_inactive` 警告；短於 32 或佔位⇒兩端啟動 fail-loud；`_child_env` 另剝除繼承來的 `SDD_STATE_DIR`／`SDD_PROJECT`；`validate_env` 拒 `SDD_*`／權杖名；audit 不記值；compose 預設空 | 佔位當真值＝公開密鑰；開發機匯出 `SDD_*` 再起 Bridge 是常態 |
| A-14 | 狀態目錄收斂 | 9 檔 | 7 個目錄站點＋1 個遙測預設（涉及 7 檔，其中 3 檔草案未列）；草案 9 檔中 5 檔不改並逐檔寫理由 | §3.4 |
| A-15 | `_POST_FROZEN_STATES` | 未提 | 加 `AUTOCLAUDE_DELEGATED` | 否則舊狀態檔的委派一啟動就被 veto |
| A-16 | S-02 | matcher 加 PowerShell＋ledger 分支 | 另加 `_assert_allowed_under_auto_compact` 放行 PowerShell | 否則 Windows 上 AUTO_COMPACT_PENDING 死鎖（§12） |
| A-17 | 委派退出（D-115-15） | COMPLETED→done、引擎升級→failed，PAUSED／CANCELLED／額度停機／孤兒不動 | **CANCELLED→`done`**（reason 記 CANCELLED）；`done`＝交還控制權、不是「成功」；其餘不動；新批次遇 DELEGATED 走回收點（§10.3），不再有「領養」 | 取消是最常見的使用者路徑，不能讓它把專案卡在委派態；〔乾跑 #15、#16〕 |
| A-18 | `playbook-ref` 格式（S3） | 未定（SA 暫定裸 `run_id`） | `run:<run_id>` | 與文件路徑型 `spec_refs` 可區分，回收只認 Bridge 簽發的值（〔乾跑 #21〕） |
| A-19 | AT 文法與歸屬（D-115-16） | 未定（SA 契約寫 `AT-[\w\-]+`，含模板 E 類） | `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`、前兩段＝所屬 AC；E 類 `AT-{NNN}-E-n` 因第二段非數字**不可編譯**，要執行改名 `AT-{NNN}-{Y}-E-{n}`；列的 AC id 須等於 AT 前兩段推得者；正向與逆向共用 `AT_ID_PATTERN`；宣告位置只限 AC 映射列第三欄與 Gherkin 標頭 | 一份判準一個家；§3／§4 表格不是宣告位置，照模板填不會編譯失敗 |
| A-20 | 逆向 RTM（S6） | 未提 | 無法歸屬的 AT 仍計入 `total_at`、標 `unmapped_at_ids`、不進 AC 桶；`fully_covered` 在有 unmapped 時為 False；`RtmCoverageReport` 與 history doc 增欄 | 不讓放寬後的文法把 AT 從覆蓋率分母悄悄移走（§8.5） |
| A-21 | 白名單 | `sdd_to_playbook_adapter.py`、`wiring.py`、SDD 9 檔 | AutoClaude 另含 `playbook_to_rtm_adapter.py`、`rtm_sink.py`、`rtm_feedback.py`、`spec_source.py`、`sdd_compile.py` 與新增的 `_sdd_frozen_gate.py`；SDD 見 §11.2 的兩張表 | D-115-16 牽動逆向 RTM；§11 |
| A-22 | 預設階段名、reason 組字、輸入清理 | 未定 | `Stage-<n>`；六種 `console-…` 組字；`approver` 不含 `;`、使用者理由 1～500 字不靜默截斷（§4.4） | 稽核三處（FSM 檔、Console、Bridge audit）可互相對上；格式可無歧義解析 |

---

## 附錄 B：對 SA 契約 v1.5〈待 SD 定案〉S1～S8 的逐項答案

SA 契約 §6.8.3 B 表的八項，加上與它們連動的 Q1／Q3／Q4／Q5（主控已於 D-115-14～16 裁決）。值一律以本 ADR 為唯一真相源；SA 改契約時只引用、不另抄。

| # | SA 的問題 | 答案（值） | 節 |
|---|---|---|---|
| S1 | 寫入權杖：環境變數名、backend 屬性名、兩端未設時的行為 | 環境變數 `BRIDGE_SDD_WRITE_TOKEN`（兩端同名）；HTTP 標頭 `X-Bridge-Token`；backend 屬性 `console.bridge.sdd-write-token`（`BridgeProperties.sddWriteToken`，`application.yml` 值 `${BRIDGE_SDD_WRITE_TOKEN:}`）。Bridge 未設⇒`:freeze` 與含 `sdd` 的 run 回 503 `sdd_write_disabled`；backend 未設⇒freeze 回 503 `sdd_write_disabled`（不呼叫 Bridge）、execute 不送 `sdd` 並於 201 `warnings` 帶 `sdd_governance_inactive`（`cause=token_not_configured`）——**同意 SA 的暫行寫法**；不符⇒Bridge 403 `sdd_write_forbidden`（backend 轉 502＋ERROR）；短於 32 字元或佔位⇒兩端啟動 fail-loud | §9 |
| S2 | 環境契約：狀態目錄與 FSM 專案的變數名、`spec_file` 怎麼進引擎端 adapter、CLI 子行程環境／cwd／逾時 | 狀態目錄 `SDD_STATE_DIR`（絕對路徑；**只給 CLI 子行程**，值 `<root>/build/reports/fsm`）；FSM 專案 `SDD_PROJECT`（CLI 與引擎子行程；引擎子行程**只有**這一個，且先剝除繼承自 Bridge 的 `SDD_*`）。`spec_file`：不用新變數，Bridge 伺服端把 playbook 的 `workflow_path` 寫成 **TCS 檔案的 realpath**，引擎 PRE_RUN 的 `load_spec(workflow_path)` 把檔案路徑視為 `spec_file`（port 簽名不改）。CLI：argv `[sys.executable, -W ignore::RuntimeWarning, -m, tools.fsm_runtime.fsm_runtime, <動詞>, --project, <鍵>, --must-exist, …]`、cwd＝SDD 版本目錄、環境＝繼承去掉 `BRIDGE_*`／`SDD_*`／`PYTHONPATH` 後加 `PYTHONPATH`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1`、兩個遙測旗標 `0`、`SDD_STATE_DIR`、`SDD_PROJECT`；逾時 20 秒（504 `sdd_cli_timeout`） | §3.5、§7.3、§8.3 |
| S3 | CLI 動詞表、`playbook-ref` 格式、`:freeze` 預設階段名、`reason` 組字 | 動詞：`negotiate-enter`、`negotiate-exit --outcome agreed`、`delegate-enter`、`delegate-exit --decision done｜failed`、`spec-frozen`（加 `--digest`／`--root`／`--approver`／`--reason`／`--json`），全域 `--must-exist`；rc 0／1／2／3／4／5（§4.1）。`playbook-ref`＝`run:<run_id>`（不是裸 run_id）。預設階段名 `Stage-<n>`（`n`＝`frozen_stages` 筆數＋1）。`reason`：`console-freeze approver=<approver>; reason=<理由>` 等六種（§4.4） | §4 |
| S4 | `spec_doc_digests` 形狀與演算法（bytes 或正規化文字） | 映射 `{<相對 root 的 POSIX 路徑>: "sha256:<64 位小寫 hex>"}`，寫在 `frozen_stages[-1]`（另有 `approved_by`）。演算法＝**換行正規化後的 UTF-8 文字**（`\r\n`、`\r`→`\n`，BOM 不剝）的 sha256，與 adapter 的 `SddSpec.digest` 逐位元相同；**不是**原始 bytes（CRLF 檔會假紅）；非 UTF-8⇒CLI rc 4 `doc_not_utf8`。CLI、adapter、Bridge 三處同一算法，由對拍測試守 | §4.3、§6 |
| S5 | 談判閘對映與 `failed` 後恢復規則 | 接受「Console 簽核匯入草稿＝談判 `agreed`」，附四條件 C-1～C-4，誠實標註 R-9.20.3 不滿足（reason 記 `r9.20.3=not-satisfied`）。`delegate-exit failed`＝ESCALATION（〔乾跑 #17〕）；恢復**只有人、留在 SDD session**：`resume-from-escalation --to IMPLEMENTATION --project <鍵> --reason "<原因>"`（〔乾跑 #19、#20〕前置與結果已驗）；Console 與 Bridge 不提供恢復動詞，只顯示 ESCALATION、`escalation_provenance`（`GET /sdd/fsm/{project}` 須多回）與可複製指令；恢復後新批次可直接啟動。判斷「有未解的委派失敗」須看 `current_state` 屬 ESCALATION 類且 `escalation_history[-1].resolved_at` 為空——provenance 與 tracking 恢復後不清除 | §5 |
| S6 | 逆向 RTM 對放寬文法的 AC 聚合；還原不出 AC 的 AT 是否仍計入 `at.total` | 文法 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`（正逆向同一份 `AT_ID_PATTERN`）；符合者以前兩段歸 AC（`AT-001-12-3-a`→`AC-001-12`，尾綴不影響歸屬）；不符者**仍計入** `summary.total_at`（並依完成與否計入 `passed_at`／`failed_at_ids`）、列入 `unmapped_at_ids`（YAML 頂層）與 `summary.unmapped_at`、不進 AC 桶；`fully_covered` 在 `unmapped_at_ids` 非空時為 False。正向的 `unmapped_at_ids`（Bridge `/sdd/compile` 回應：規格出現卻未編成）與逆向的同名欄是**兩個不同層的欄位** | §8.1、§8.2、§8.5 |
| S7 | `/sdd/compile` 摘要不符的例外型別 | adapter 新增 `SpecDigestMismatchError`（`SpecNotFrozenError` 的子類）；Bridge 在三個預檢點一律把它對映成 **409 `spec_digest_changed`**；其餘 `SpecNotFrozenError`（未凍結、狀態檔缺、規格檔不在凍結清單）＝422 `spec_not_frozen`。兩者**依原因並存**——與 SA 暫行寫法的差異：「凍結後內容已變更」是 409，不是 422 | §6.2、§6.3 |
| S8 | 最小侵入白名單的列檔與理由 | AutoClaude：`sdd_to_playbook_adapter.py`、`_sdd_frozen_gate.py`（新）、`spec_source.py`、`sdd_compile.py`、`playbook_to_rtm_adapter.py`、`rtm_sink.py`、`rtm_feedback.py`、`wiring.py`（僅 docstring）＋測試；AISDLC_SDD（僅 LATEST）：RT 棒與 DOC 棒的兩張表；白名單外一律禁止，以 `git diff` 機械核對 | §11 |
| Q1 | 核准凍結與路徑 A 匯入的循環依賴 | D-115-14：Console 專案為錨，綁定＝`execution_path`＋`sdd_project`（預設＝專案名，Bridge 淨化）；匯入帶選填 `targetProjectId`；核准凍結請求**沒有** `binding` 欄、沒有 `sdd_not_bound` | §7.2 |
| Q3 | FSM 停在委派態的解卡 | D-115-15：取消⇒`done`；新批次遇 DELEGATED 時依 `playbook_ref` 所指 run 判定回收（終態或不存在）或 409（活躍、外來）；與 SA 建議的差異：以 FSM 記的 run 為準，不是「Bridge 有沒有同 `fsm_project` 的活躍 run」 | §10.1、§10.3 |
| Q4 | `approver`／`fsm_project` 兩個補欄 | 採用：`sdd.approver`（選填，省略記 `console`，1～100 字、不含 `;`）；`/sdd/compile` 請求 `fsm_project`、回應 `spec_file`／`fsm_project` | §5.2、§7.3、§8.3 |
| Q5 | 回應形狀的小選擇 | 採用：`ParsedResult` 四欄伺服器擁有；`unmapped_at_ids` 非空仍回 200、Console 轉警告 `at_unmapped`；清單項不帶 `phase`；`spec_format_version` 只顯示 | §8.2 |
