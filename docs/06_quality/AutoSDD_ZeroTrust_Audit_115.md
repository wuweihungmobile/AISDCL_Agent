# AutoSDD 整合輪 115 零信任稽核

**對應計畫**：[AutoSDD_improving_115.md](../04_planning/AutoSDD_improving_115.md) §2〈問題 1 判定〉（判準 C1～C6）與 §4.5（W4 SDD dogfood）。
**本檔分工**：§1 由 W4 SDD dogfood 操作員寫入（Sonnet；本場兼任 SA、QA，並以「掌舵者代理」身分按下核准凍結）；§2 起由 W5 QA 獨立稽核追加，W4 不寫。
**證據原則**：每一格「成立」都附當回合真跑的指令、rc 與逐字輸出；沒跑的一律寫進 §1.10〈未驗證〉。證據原檔在暫存目錄（絕對路徑見 §1.11），重點輸出已逐字引在本檔。本檔不含任何機密值（寫入權杖為兩端同值的拋棄式測試值，不入檔）。

## §1 Dogfood 證據

### §1.0 結論先行

一個真實小功能 T-G（Bridge 純函式：FSM `current_state` 對映 `phase{name,order,blocking,observation}`）完整走過一次 Console × Bridge × AutoClaude × SDD 迴圈：SDD session 以真 CLI 走閘門到 HUMAN_PENDING → Console 畫面核准凍結 → 路徑 A 匯入並簽核 → 以 `aisdlc_sdd` 啟動批次（真 claude，haiku）→ 引擎評估指令與驗收 regex 全過 → FSM 回 IMPLEMENTATION → RTM 在 Console 可見；失敗路徑以決定性替身走了兩遍（CI 夾具一遍、Console 實機一遍）。本場沒有發現 P2 以上缺陷（P≤2 為零）；登記 P3 五筆（SDD 三筆、Console 兩筆）加 P4 八筆，見 §1.9。

| 判準 | 判定 | 一句話證據（座標） |
|------|------|-------------------|
| C1 綁定與唯一性 | 成立（附但書） | 綁定寫回與部分唯一索引衝突 409、同目錄兩個 FSM 專案時未指認即 fail-closed 422（§1.8 C1） |
| C2 人工閘 | 成立（附但書） | UI 核准凍結 → FSM `decision_trace`／`frozen_stages`、Console 稽核、Bridge 稽核同 trace_id，三向逐值對上（§1.2 D-2、§1.5） |
| C3 治理執行 | 成立 | `aisdlc_sdd` 啟動、三點摘要相符、step_id 為 `sdd-greenfield-at-…`；凍結後改檔 → 409 且零副作用（§1.2 D-3、§1.8 C3） |
| C4 狀態同步 | 成立（附但書） | 成功路徑 AUTOCLAUDE_DELEGATED → IMPLEMENTATION；失敗路徑 ESCALATION、恢復、再啟動，Console 逐值對上（§1.3、§1.7） |
| C5 追溯 | 成立 | 引擎 YAML、Bridge、Console 三處逐值相等，畫面標「諮詢視圖」（§1.2 D-4） |
| C6 自食 | 成立（附但書） | FSM 狀態檔、RTM、Console 畫面、決定性替身失敗路徑、SCG-4 審查俱全；審查者與規格作者為同一操作員，W5 為第二眼（§1.6、§1.8 C6） |

**對「問題 1 能不能答『是』」的建議**：本場證據支持答「是」，範圍＝Windows、haiku、單機、一個純函式大小的功能、AT 皆為 Unit 類。計畫書自訂的降級規則是「缺 C2 或 C6 即降為部分」：C2、C6 本場皆有當回合證據，故不降；但 C6 的獨立性只靠 W5 補第二眼，W5 若推翻其中任何一格，以 W5 為準。範圍之外的事（POSIX、Docker、Integration／E2E 類 AT 用真 AI 跑、暫停續跑）見 §1.10，沒有被這一場證明。

### §1.1 環境與前置

| 項目 | 值 |
|------|----|
| 日期、角色 | 2026-10-17；W4 操作員（Sonnet；SA、QA、掌舵者代理三帽） |
| 作業系統 | Windows 11 Pro（10.0.26300）；互動載具 pwsh 7.6.7；顯示的恢復指令另以 Windows PowerShell 5.1（`powershell.exe`）執行 |
| 直譯器與工具 | Python 3.11.9（根 `.venv`）、Node v22.23.3、OpenJDK 21.0.10、claude 2.1.302（Claude Code，模型 haiku） |
| 資料庫 | 容器 `qa-pg`（`pgvector/pgvector:pg18`，伺服器 18.4），埠 25433；埠 5432 的 `autoclaude_pg` 未碰 |
| 程式版本 | HEAD `5593e178`；SDD LATEST `AISDLC_SDD_v0.30` |
| 服務 | backend 18080（e2e profile）、Bridge 18081（真引擎；`/health` 回 `{"status":"ok",…}`，其中 `engines.sdd.latest="AISDLC_SDD_v0.30"`、`db.ok=true`）、frontend 3000（standalone） |
| Console 設定 | `autoclaude.claudeExtraArgs=--permission-mode acceptEdits --allowedTools Read,Edit,Write,Bash --model haiku`、`execution.autoResume=false`，其餘為預設；失敗路徑實機期間暫將 `autoclaude.claudeCommand` 指向替身 `aisdlc-mock-claude.exe`，結束後已還原為 `claude`（讀回確認） |
| 引擎行為 | wexpect 已安裝，但引擎偵測到 re-exec 啟動器而改走 subprocess 模式（`engine-1.log` 第 12 行：「偵測到 re-exec 啟動器…改走 subprocess 模式」）；Brain 停用（`engine-1.log` 第 3 行：「未設定 MINIMAX_API_KEY：Brain 相關能力…本次停用」）。任務書原寫「wexpect 不在」，與實況不符 |
| 專案根 | `C:\Users\wuwei\AppData\Local\Temp\e2e\projects\tg-phase`（Console 專案 id `8bcd85c6-20b8-44c0-b6ea-2986a082ffdb`；FSM 專案鍵 `tg-phase`）；失敗路徑另用 `...\projects\tg-phase-fail` |

### §1.2 步驟證據（D-0～D-6）

**D-0 建專案**。`POST /api/v1/projects`（operator）→ HTTP 201；`id=8bcd85c6-20b8-44c0-b6ea-2986a082ffdb`、`name=tg-phase`、`sddProject=null`（尚未綁定）、`goalsCount=0`。原檔 `logs\d0_create_project.log`。

**D-1 Stage-1 基線與 Stage-2 規格（SDD session 側，全走 FSMRuntime CLI，未手改任何 FSM-STATE 檔）**

1. Stage-1 基線（模擬既有凍結系統）：五份上位文件為 HEAD 文件的逐字複本。FSM 以五次 `transition`（各 rc=0）走 INIT → SCENARIO_DETECT → AGENT_LOAD → SPEC_DRAFTING → SCG_VALIDATION → HUMAN_PENDING，理由欄寫明「匯入已凍結上位文件，不重跑 SCG（用 transition 而非 gate PASS，避免記一次沒發生過的閘門通過）」；再 `spec-frozen --stage Stage-1 --doc …（五份）--digest --root … --approver operator --json`，rc=0，輸出 `{"ok":true,"verb":"spec-frozen","project":"tg-phase","from_state":"HUMAN_PENDING","current_state":"SPEC_FROZEN","stage":"Stage-1","spec_doc_digests":{…五份…}}`。CLI 摘要與獨立重算（PowerShell，換行正規化後的 UTF-8 做 sha256）五份逐一相等；本場收尾時五份的摘要也與目前工作樹同名檔逐一相等：

   | 文件（專案根相對路徑） | 摘要前 12 碼 |
   |------------------------|--------------|
   | `docs/01_requirements/AutoSDD_improving_115.md` | `f63346dbd6b9` |
   | `docs/02_architecture/API_Contract_P3-6.md` | `67e8053c1579` |
   | `docs/02_architecture/Architecture.md` | `ffc13220a4d8` |
   | `docs/02_architecture/adr/ADR-001-TechStack-Lock.md` | `ff0bcd0038b7` |
   | `docs/02_architecture/api/openapi-p3-6.yaml` | `47fd89355b6e` |

2. Stage-2（T-G 增量條款）：TCS 同檔含 FRD-lite（F-001、US-001、AC-001-1～5、NFR-001-1～3）、〈增量追溯表〉二十二列、§1 映射七個 AT、七段 Gherkin；二萬一千六百八十四個位元組，摘要 `sha256:8f440a68e683837ddb2e8e3e37a9c9593116bca18a702d834a3616bd427b1e84`。`transition` → SPEC_DRAFTING → SCG_VALIDATION（各 rc=0）。
3. 機械檢查（皆 rc=0；預編譯與追溯表兩項在收尾時重跑一次留檔，所以追溯表檢查印出的 FSM 狀態是當時的 IMPLEMENTATION，凍結前那一次的輸出內容相同）：
   - 預編譯（adapter 的解析半段，凍結前先驗）：`spec_format_version=1.0`、`scenario=greenfield`、七個 AT、`unmapped_at_ids={}`、弱 regex 零個（`logs\d1_precompile_check.log`）。
   - 追溯表：`rows=22 expected=22 fsm_state=IMPLEMENTATION frozen_stages=['Stage-1', 'Stage-2']`，二十一列 OK、一列 SELF（「SCG-0／RTM 初版已建立」），末行 `RESULT PASS problems=0`；每列的上位文件路徑存在、列內摘要等於獨立重算、也等於 `frozen_stages[*].spec_doc_digests`、且列在 `spec_docs`（`logs\d1_trace_table_check.log`）。
   - phase 表：十五項檢查全 OK，主路徑二十一＋觀測十五＋阻塞四＋過渡三＝四十三，等於 `_HAPPY_PATH` 鍵數，四組兩兩不相交，末行 `RESULT PASS problems=0`（`logs\d1_phase_table_check.log`）。
   - SLV 機械半段與模糊度閘：見 `logs\d1_slv_scan.log` 與 DEF-AC-015、DEF-AC-016（兩者在增量專案上空轉）。
4. `gate --gate SCG_VALIDATION --result PASS --reason …` rc=0，輸出 `{"gate": "SCG_VALIDATION", "result": "PASS", "next_state": "HUMAN_PENDING"}`（`logs\d1_gate_pass.log`）。本場沒有發生過任何閘門失敗，也沒有捏造失敗。
5. 與任務書的差異：任務書寫「AC-001-1～4」，TCS 多了 AC-001-5（三個過渡狀態 → TRANSIENT）。理由：契約 §3.1.5 的四十三個鍵由主路徑二十一、觀測十五、阻塞四、過渡三組成，沒有第五條 AC 就有三個鍵沒有歸屬。
6. 沒有執行 `/stage-compaction`（SPEC_FROZEN 後 R-9.4 要求；見 §1.10）。三個 SDD 技能（`sdd-gate`、`spec-logical-validator`、`spec-compliance-check`）是讀其 SKILL.md 後以腳本執行機械半段、判斷半段由操作員人讀，不是以斜線指令叫起。

**D-2 人工閘（Console 畫面）**。Playwright（chromium，寬 1440、高 2000 的 viewport）以 operator 登入 Console，專案詳情「SDD 治理」→「核准凍結」→ 對話框 → 送出（原檔 `logs\d2_freeze_ui.log`）：

- 對話框 approver 一行：「核准人：operator（唯讀；取自登入身分，不由畫面指定）」。
- 送出前：`state=HUMAN_PENDING`、`pending=等待人工確認`；送出後：`state=SPEC_FROZEN`、`frozen=已凍結：Stage-2（2026-10-17 20:47:39）`、`pending=無`。
- `POST http://localhost:18080/api/v1/projects/8bcd85c6-20b8-44c0-b6ea-2986a082ffdb/sdd/freeze` → HTTP 200；回應 `currentState=SPEC_FROZEN`、`frozenStages` 兩筆，Stage-2 的 `approved_by=operator`、`spec_doc_digests` 為 TCS 的 `sha256:8f440a68…1e84`。
- FSM `decision_trace` 該筆：`from=HUMAN_PENDING`、`to=SPEC_FROZEN`、`trigger=spec_frozen`、`reason=console-freeze approver=operator; reason=掌舵者代理核准凍結：T-G 增量 FRD-lite 加 TCS（AC-001-1～5、AT 共 7 條）已由 SDD session 走完 SCG-0～3（增量條款；追溯表 22 列機械檢查 0 問題），Stage-2 凍結`。
- Console 稽核（PG `console.audit_log`）：`subject=operator`、`role=OPERATOR`、`method=POST`、`path=/api/v1/projects/8bcd85c6-…/sdd/freeze`、`entity_type=project`、`occurred_at=2026-10-17 12:47:39 UTC`、`trace_id=ad3d69c0-812b-4c79-9921-931a8b24c4ce`。
- Bridge 稽核（`_audit.jsonl`）同一個 trace_id 兩筆：`event=sdd_cli verb=spec-frozen result=ok rc=0 approver=operator`（12:47:39.824）、`event=sdd_write verb=freeze result=ok approver=operator`（12:47:39.837）；沒有任何含 token 的欄位。
- PG `projects.sdd_project='tg-phase'`（第 5 項寫回標準鍵）。
- 截圖（`shots\`）：`d2_01_sdd_governance_before_freeze.png`、`d2_02_freeze_dialog_filled.png`、`d2_03_sdd_governance_after_freeze.png`。

**D-3 路徑 A 匯入、簽核、批次**

- `POST /api/v1/import/text` → 201；`POST /api/v1/import/{id}/parse`（body：`executionPath`、`autonomyLevel=4`、`specDir`、`specFile=TCS-TgPhase-20261017.md`、`targetProjectId`）→ HTTP 200：`path=SDD`，一個目標 greenfield、七個任務；`passCriteriaSpec.stepId` 為 `sdd-greenfield-at-001-1-1`、`…-1-2`、`…-2-1`、`…-3-1`、`…-4-1`、`…-4-2`、`…-5-1`；`maxRetries=5`；`maintainContext` 依序 false、true、false、false、false、true、false；七個 `specDigest` 全為 `sha256:8f440a68…1e84`；`specFormatVersion=1.0`；`warnings=[]`（`logs\d3_parse_response.log`）。
- Bridge 直打 `POST /sdd/compile` 對照（`logs\d3_bridge_compile.log`）：HTTP 200、`frozen_digest:"verified"`、`unmapped_at_ids:[]`、`warnings:[]`、`fsm_project:"tg-phase"`、`digest` 等於凍結摘要，七個 `step_id` 與 parse 結果相同。
- `signoff` → 200；`confirm` → 201，回傳的就是既有專案（同一個 id，`goalsCount=1`、`tasksCount=7`、`sddProject=tg-phase`、`sddSpecFile` 為 TCS 絕對路徑；`logs\d3_confirm_response.log`）。
- `POST /api/v1/projects/{id}/execute` → 201，沒有 `warnings`；`runId=830d4b92-5a91-430b-94dd-ab84e94473bb`、`traceId=66727d51-3cc9-44e4-b584-b4dd63a0e9f4`（`logs\d3_execute_response.log`）。
- 執行（真 claude 2.1.302，haiku）：run 狀態 `COMPLETED`，七步全過，耗時一百四十二秒；輪詢紀錄 `logs\watch_main.log`——六十八次取樣 run 皆 RUNNING、FSM 皆 AUTOCLAUDE_DELEGATED，最後一次取樣（142.2 秒）run 與 FSM 同時是 COMPLETED／IMPLEMENTATION，FSM 離開委派態不需額外等待（上限三十秒）。
- 引擎結束行（`engine-1.log` 第 57 行）：`Playbook 結束 | KernelResult(success=True, completed_steps=7, total_steps=7, reason='success', step_log=['[sdd-greenfield-at-001-1-1] AT-001-1-1 ✓ (attempt 2)', '[sdd-greenfield-at-001-1-2] AT-001-1-2 ✓ (attempt 1)', …`。第一步第二次嘗試才過：第一次嘗試模型的最終回覆缺 INTAKE、SPECIFICATION、HUMAN_GATE 三個字（程式與測試其實已寫好、評估指令會過），第二次補上（`playbook_sdd-greenfield-at-001-1-1.log` 第 2、4 行的 `result` 欄逐一核對）。
- 治理確實生效的證據：工作區 `playbook.yaml` 有 `workflow_type: aisdlc_sdd` 與 `workflow_path: C:\Users\wuwei\AppData\Local\Temp\e2e\projects\tg-phase\docs\03_testing\contracts\TCS-TgPhase-20261017.md`；七個 `step_id` 皆為 `sdd-greenfield-at-…`；Console DAG 的 TASK 節點 `stepId` 同（不是 `G1-T1`）；引擎寫出 `engine\checkpoints\rtm\RTM-COVERAGE-tg-phase.yaml`（檔名帶 `SDD_PROJECT` 的值，內含凍結摘要）；`run.json` 的 `env_keys` 只有 `MOCK_CLAUDE_DELAY,MOCK_CLAUDE_FAIL_REGEX`（e2e profile 預設，無權杖名），`sdd.sync={"exit":"done","ok":true,…}`。
- 權杖不落地：掃描工作區、Bridge 日誌、證據日誌共一百零一個檔，含權杖值的檔案零個（只數檔數、不印值）。

**D-4 追溯覆蓋（C5）與畫面**

- 引擎 `RTM-COVERAGE-tg-phase.yaml`：`kind: rtm-coverage`、`scenario: greenfield`、`spec_digest: sha256:8f440a68…1e84`；摘要段 AT 總數七、通過七（`at_coverage_pct: 100.0`）、AC 總數五、覆蓋五（`ac_coverage_pct: 100.0`）、`fully_covered: true`、`unmapped_at: 0`；`failed_at_ids`、`weak_regex_at_ids`、`unmapped_at_ids` 皆為空清單。
- Bridge `GET /autoclaude/runs/{id}/rtm`（`logs\d4_bridge_rtm.log`）：`at` 為七／七、`pct` 100.0、`unmapped` 零；`ac={"covered":5,"total":5,"pct":100.0}`、`fully_covered:true`、`advisory:true`、`spec_digest` 同。
- Console `GET /api/v1/executions/{id}/rtm`（`logs\d4_console_rtm.log`）：同值（駝峰欄名），`advisory:true`。三處逐值相等。
- 畫面（`logs\d4_views.log`）：執行頁「追溯覆蓋」面板標「諮詢視圖」，並寫「AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘」；AT 通過七／七（100.0%）、AC 覆蓋五／五（100.0%）、規格摘要 `sha256:8f440a68e683…`、場景 greenfield、未通過／偏弱／無法歸屬皆「無」。「SDD 治理」區：`state=IMPLEMENTATION`、`phase=階段—`、`frozen=已凍結：Stage-2（2026-10-17 20:47:39）`。監控頁 SDD 卡：FSM 專案 `tg-phase`、目前狀態 IMPLEMENTATION、最近決策五筆（新到舊）。截圖：`d4_10_execute_rtm_panel.png`、`d4_11_sdd_governance.png`、`d4_12_monitor_sdd_card.png`。
- 失敗的 run 沒有 RTM：`GET /executions/{失敗 runId}/rtm` → HTTP 404、`reason=rtm_not_found`（§1.7）。
- 畫面的 `階段` 欄在本場所有狀態下都是「—」：T-G 的 `tg_phase.py` 是本場的產物，尚未搬入 Bridge，`GET /sdd/fsm*` 的 `phase` 恆為 null（Bridge 測試 F-5 仍為預留的略過）；這是記錄現況，不算缺陷。
- AI 的產物：`tg_phase.py`（八十七行）、`conftest.py`（兩行註解）、七個測試檔共八個測試函式；專案根保留，副本在 `artifacts\`。SCG-4 審查見 §1.6。

**D-5 CI 夾具（`AgentConsole/engine-bridge/tests/test_sdd_dogfood_fixture.py`，新檔）**

兩個測試，只把 AI 換成確定性替身 `aisdlc-mock-claude`，其餘全是真的（真 SDD CLI 子行程扮演人在 SDD session、真 Bridge、真 adapter、真引擎、真 pytest 評估指令；不需要 claude、不需要 PG）：

1. 成功夾具：SDD session 走閘門到 HUMAN_PENDING → Bridge `:freeze` → `POST /sdd/compile`（四個 AT，含邊界尾綴 `AT-001-2-E-1`；斷言 step_id、max_retries、maintain_context、regex、evaluator_command）→ `POST /autoclaude/runs` 帶 `sdd` 區塊 → COMPLETED → FSM 四跳逐字（含 reason）、`playbook_ref=run:<id>`、`workflow_path` 為規格檔、引擎子行程環境只有 `SDD_PROJECT`、RTM 全覆蓋、`GET /sdd/fsm` 無 `recovery`。
2. 失敗夾具：E2E 類 AT（重試上限二）的驗收 regex 替身永遠不會輸出 → run FAILED 且 `reason` 以「引擎升級（ESCALATION）」開頭 → FSM ESCALATION、`escalation_provenance.source=autoclaude_delegated_failed`、歷史末筆未解、`decision_trace` 末筆 reason 內含失敗的 regex → Bridge 視圖有 `recovery`（兩種殼各一條）→ 恢復前下一批次 409 `fsm_state_conflict` 且零副作用（沒有建 run 目錄）→ **把卡片顯示的那條指令原樣執行**（Windows 以 `powershell.exe -File` 跑 PowerShell 形，其餘平台跑 POSIX 形）→ FSM IMPLEMENTATION、歷史回填 `resolved_at` 與 `resolution`、provenance 不清除 → 下一批次 201 → 同夾具再次升級，歷史為「已解、未解」。

驗證輸出（本場當回合）：
- `ruff check`：engine-bridge 目錄視角（單檔、整個目錄）與 monorepo 根視角（engine-bridge 整棵）皆 rc=0（ruff 回報全數通過）。
- 夾具兩個測試通過；連跑三次各一次全數通過（每次約十一點五秒），另以 `-n 2` 平行跑一次也全數通過（約七秒）。
- 整個 engine-bridge 測試套件（`-n 4`）rc=0：九百個測試通過、二十五個略過；略過全為環境因素——七個 Windows 無法建 symlink、十七個未設 `BRIDGE_TEST_DSN`、一個 W4 預留位（`test_sdd_integration_parity.py` 第 553 行：T-G phase 表尚未落地）；本檔兩個夾具測試未被略過。
- 根層守衛：`tools/tests/test_platform_neutral_paths.py`（一百七十七個測試）與 `tools/tests/test_subprocess_encoding_hygiene.py`（三十九個測試）皆 OK（rc=0）。注意：新檔尚未 `git add`，依 `git ls-files` 列舉的掃描器要等收尾 commit 後才看得到它。
- 夾具測試過程新發現：SDD v0.24 起規則遙測預設開啟，沒有 `SDD_ENABLE_RULE_FIRE_TELEMETRY=0`、`SDD_ENABLE_RULE_CATCH_TELEMETRY=0` 的 CLI 驅動會把計數寫回 tracked 的 `governance/rules/*.yaml`；夾具「人」那一側的子行程已帶這兩個旗標，收尾 `git status` 沒有任何 `AISDLC_SDD/` 變動。

**D-6 四源對拍**：見 §1.5。

### §1.3 FSM 狀態檔引文（主專案 `tg-phase`，只經 CLI 寫入）

終態摘要（`logs\d3_fsm_after_run.log`，由獨立 PyYAML 讀檔，不經任何被測 API）：`current_state: IMPLEMENTATION`、`current_sprint: 1`、`updated_at: 2026-10-17T12:52:20+00:00`、`trace_len: 14`、`frozen_stage_names: [Stage-1, Stage-2]`。

`frozen_stages[1]`（Stage-2）：`frozen_at: 2026-10-17T12:47:39+00:00`、`spec_docs: [docs/03_testing/contracts/TCS-TgPhase-20261017.md]`、`spec_doc_digests` 該檔 `sha256:8f440a68e683837ddb2e8e3e37a9c9593116bca18a702d834a3616bd427b1e84`、`approved_by: operator`。

`autoclaude_delegated_tracking`：`entered_at: 2026-10-17T12:49:57+00:00`、`resume_state: IMPLEMENTATION`、`playbook_ref: run:830d4b92-5a91-430b-94dd-ab84e94473bb`（退出後不清除，是歷史殘留欄）。

`decision_trace` 末五筆（逐字；時間為 UTC）：

| ts | from → to | trigger | reason |
|----|-----------|---------|--------|
| 12:47:39 | HUMAN_PENDING → SPEC_FROZEN | `spec_frozen` | `console-freeze approver=operator; reason=掌舵者代理核准凍結：…Stage-2 凍結` |
| 12:49:57 | SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED | `test_contract_enter` | `console-signoff approver=operator; run=830d4b92-5a91-430b-94dd-ab84e94473bb` |
| 12:49:57 | TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION | `test_contract_exit` | `console-signoff approver=operator; oracle=docs/03_testing/contracts/TCS-TgPhase-20261017.md@sha256:8f440a68e683837ddb2e8e3e37a9c9593116bca18a702d834a3616bd427b1e84; basis=import-draft-signoff; r9.20.3=not-satisfied` |
| 12:49:57 | IMPLEMENTATION → AUTOCLAUDE_DELEGATED | `autoclaude_delegated_enter` | `console-run run=830d4b92-5a91-430b-94dd-ab84e94473bb START` |
| 12:52:20 | AUTOCLAUDE_DELEGATED → IMPLEMENTATION | `autoclaude_delegated_exit` | `console-run run=830d4b92-5a91-430b-94dd-ab84e94473bb COMPLETED` |

跑完後 FSM 刻意停在 IMPLEMENTATION（沒有推進 PR_REVIEW 以後各態），保留給 W5 重驗；`git status` 與 SDD 樹零變動。

### §1.4 Console API 回應與稽核層引文

- `POST …/sdd/freeze` → 200（D-2）；`POST …/execute` → 201（D-3）；`GET /api/v1/engines/sdd?projectId=…`（凍結前，`logs\d2_pre_console_engines_sdd.log`）：`available:true`、`version.latest="AISDLC_SDD_v0.30"`、`fsm.currentState="HUMAN_PENDING"`、`fsm.fsmProject="tg-phase"`、`fsm.phase=null`、`fsm.recovery=null`、`humanPending.count=1`。
- `GET /api/v1/executions/{runId}`（主 run）：`status=COMPLETED`、`completedSteps=7`、`totalSteps=7`、`totalTokensUsed=1086389`、`tokenBudget=1000000`、`elapsedSec=142`（見 DEF-AC-020）。
- `console.audit_log` 欄位（psql 實查）：`id, occurred_at, subject, role, method, path, entity_type, entity_id, http_status, trace_id`，沒有 `action` 欄（DEF-AC-025）。
- Bridge `_audit.jsonl`（專案 `tg-phase` 共七列）：freeze 兩列（trace `ad3d69c0-…`，見 D-2）；批次五列同 trace `66727d51-3cc9-44e4-b584-b4dd63a0e9f4`（與 execute 回應的 `traceId` 相同）——`sdd_cli` 的 `negotiate-enter`、`negotiate-exit`、`delegate-enter`，`sdd_write verb=run`，以及收尾的 `sdd_cli delegate-exit`（12:52:20.256）；每列 `result=ok`、無 token 欄（DEF-AC-026 為契約文字與此不符）。
- 請求識別碼貫穿：Console 的 `traceId` 同時出現在回應、`audit_log.trace_id` 與 Bridge 稽核，三處可互相對上。

### §1.5 四源對拍表（NFR-OBS-01；契約 E2E-17 第 17 列；主 run 終態後現跑）

① FSM 狀態檔（獨立 PyYAML 讀檔）② Bridge `GET /sdd/fsm/{p}?root=` ③ Console `GET /engines/sdd?projectId=` 與 `GET /executions/{id}` ④ PG（獨立 psql）。腳本 `d6_fourway.ps1`，原檔 `logs\d6_fourway_main.json`，十列、不等〇列：

| 比對項 | ① FSM 檔 | ② Bridge | ③ Console | ④ PG | 相等 |
|--------|----------|----------|-----------|------|:----:|
| 目前狀態（跨狀態機語意） | IMPLEMENTATION | IMPLEMENTATION | IMPLEMENTATION | `execution_runs.status`＝COMPLETED ⇒ IMPLEMENTATION | 是 |
| 凍結階段 | Stage-2 | Stage-2 | Stage-2 | （無） | 是 |
| 凍結文件 `spec_docs` | `docs/03_testing/contracts/TCS-TgPhase-20261017.md` | 同 | 同 | `sdd_spec_file` 換算相對路徑＝該項 | 是 |
| 凍結摘要 | `sha256:8f440a68…1e84`（等於獨立重算） | 同 | 同 | `tasks.pass_criteria_spec->>'specDigest'` 全部相同值＝該摘要 | 是 |
| 凍結理由 | `console-freeze approver=operator; reason=…` | 同 | 同 | `audit_log` 無 reason 欄（只比 subject） | 是 |
| approver | `operator` | `operator` | `operator` | `audit_log.subject=operator` | 是 |
| 凍結時間 | FSM `ts` 12:47:39 | （同檔） | （無） | `occurred_at` 12:47:39（差距零秒；門檻五秒內） | 是 |
| 綁定 | （無） | （無） | `tg-phase｜規格目錄｜規格檔` | `projects.sdd_project／sdd_spec_dir／sdd_spec_file` 三值相同 | 是 |
| 委派追蹤 | `playbook_ref=run:830d4b92-…` | （視圖不含此欄） | `GET /executions/{id}` 的 `id` 相同 | `execution_runs.id` 相同 | 是 |
| phase（資訊列） | （無） | null | null | （無） | 是 |

說明：委派追蹤列的 Bridge 欄為「視圖不含此欄」，與契約四源表該格的「—」一致；phase 列只是記錄現況（T-G 尚未搬入）。時間戳以 UTC 比。

### §1.6 SCG-4 審查表（AI 寫的程式與測試 vs Gherkin；QA 角色）

審查對象：`tg_phase.py`（八十七行）、`conftest.py`（兩行）、`tests/test_AT_001_*.py`（七個檔、八個測試函式）；基準規格 TCS（摘要 `8f440a68…1e84`）與上位契約 §3.1.5。完整報告：專案根 `build/reports/verification/SCG4-REVIEW-TgPhase-20261017.md`（`/sdd-review` 規定寫 `docs/03_testing/`，但 IMPLEMENTATION 狀態下該前綴被 Rule 9.6 絕對禁令三禁寫，見 DEF-AC-018，故改放此處）。

| AT | 測試檔與行 | Gherkin 要求 | 結論 |
|----|-----------|--------------|------|
| AT-001-1-1 | `test_AT_001_1_1.py:9-42` | 十個狀態、四鍵集合、INTAKE／1、SPECIFICATION／2、HUMAN_GATE／3、兩旗標 false、order 單調 | 忠於 |
| AT-001-1-2 | `test_AT_001_1_2.py:9-52` | 十一個狀態、各階段名稱與 order、旗標、單調且相鄰差 1 | 忠於 |
| AT-001-1-2（第二個函式） | `test_AT_001_1_2.py:55-62` | 「與上一個 AT 的十個狀態合起來」單調且相鄰差 1 | **弱化（輕度）**：只取四個前段、五個後段狀態，不是完整的十加十一；取樣仍橫跨 order 1～8，斷言有效，字面保真度不足 |
| AT-001-2-1 | `test_AT_001_2_1.py:9-57` | 十五個觀測狀態、兩旗標、五個回歸階段 | 忠於 |
| AT-001-3-1 | `test_AT_001_3_1.py:9-23` | 四個阻塞狀態、BLOCKED／0／blocking true | 忠於 |
| AT-001-4-1 | `test_AT_001_4_1.py:9-29` | 六個輸入（BOGUS_STATE、init、42、1.5、True、None）一律 UNKNOWN、不拋例外 | 忠於 |
| AT-001-4-2 | `test_AT_001_4_2.py:9-29` | 六個輸入（空字串、空白、` INIT `、列表、字典、集合）同上 | 忠於 |
| AT-001-5-1 | `test_AT_001_5_1.py:9-18` | 三個過渡狀態、TRANSIENT／0 | 忠於 |

七個 AT 中六個忠於、一個含輕度弱化的函式、零偏離。獨立於 AI 測試的量測（原檔 `logs\d4_*.log`）：

| 量測 | 結果 |
|------|------|
| 全套 | 八個測試全數通過（專案根，`logs\d4_full_suite.log`） |
| 突變探針（只動暫存副本，`mutation_probe.py`） | 十四個單行突變全數被殺死、存活零個（`logs\d4_mutation_probe.log`）：改 order、少一個主路徑狀態、拿掉阻塞／過渡成員、改觀測回歸階段、拿掉 `isinstance` 守衛、加 strip／upper 正規化、多一個回傳鍵、改 RELEASE 的 order⋯⋯ |
| 行覆蓋 | 98.2%（標準庫 trace，五十七行可執行、命中五十六；`pytest-cov` 未裝於根 venv；`logs\d4_line_coverage.log`） |
| 完整性（獨立於 AI 測試） | `_HAPPY_PATH` 四十三個鍵全數映到非 UNKNOWN 階段，旗標與 `_BLOCKING_STATES`／`OBSERVATION_STATES` 逐一相符；主路徑 order 為 1～8 連續（`logs\d4_scg4_measure.log`） |
| NFR-001-2 單次呼叫低於 1 毫秒（P99） | 五萬五千次呼叫：P50 0.20 微秒、P99 0.30 微秒、最大 19.10 微秒 |
| NFR-001-1 純函式、僅標準庫 | import 零個、I／O 呼叫零個、TODO／FIXME 零行 |
| NFR-001-3 裸 pytest 可匯入模組 | 成立（AI 自己放了兩行註解的 `conftest.py`） |

TCS 層面的偏離（不是 AI 弱化）：TCS 自己的 SCG-4 通過標準第三列「每個 AC 至少一個負向 AT」，AC-001-1、AC-001-2、AC-001-3、AC-001-5 沒有專屬負向 AT（負向由 AC-001-4 的非法輸入與分類互斥承擔；互斥另由 phase 表檢查與 `scg4_measure.py` 機械證明）。QA 判斷：純函式分類問題的結構性做法，登記為已知偏離，不要求補測試。**SCG-4 建議：通過**；附一條非必修建議（AT-001-1-2 第二個函式改用完整的十個前段狀態）。

### §1.7 失敗路徑（決定性替身）

**甲、CI 夾具**：見 §1.2 D-5 第 2 點。重點觀察：引擎對「同一個驗收 regex 連敗」只嘗試兩次就升級（`STARTED(1) → RETRYING(2) → FAILED(2)`，替身被呼叫兩次），沒有用盡 `max_retries=2`＋1 的上限；這是引擎的語意預算行為，夾具只釘不變式（升級前至少重試一次、嘗試數不超過上限、替身呼叫次數等於嘗試次數）。

**乙、Console 實機**（專案 `tg-phase-fail`，Console 專案 id `e8d6acd9-b6e0-477a-9efe-395ffdcb6dc5`；單一 E2E 類 AT，Then 的字面值 `NEVER_PRINTED_1` 替身必不輸出；FSM 專案鍵 `tg-phase-fail`；腳本 `f_a_setup.ps1`、`f_b_run.ps1`、`f_d_recover.ps1`、`f_f_extra.ps1`，原檔 `logs\f_*.log`）：

1. 準備：SDD session 以 CLI 走 INIT → … → SCG_VALIDATION，`gate --result PASS` → HUMAN_PENDING；Console 建專案；`POST …/sdd/freeze` → 200（`approved_by=operator`，摘要等於獨立重算）；路徑 A 匯入（parse 200、一個任務、`maxRetries=2`、`expectedOutputRegex=NEVER_PRINTED_1`）、signoff 200、confirm 201。
2. 執行：`POST …/execute` → 201（`runId=c3e88f2c-ed2f-435c-a85f-731198d50dbf`）；三秒後 run `FAILED`、`bridgeStatus=FAILED`，`reason=引擎升級（ESCALATION）：[sdd-greenfield-at-001-1-1] 輸出未符合期望 regex: 'NEVER_PRINTED_1'`；同一次輪詢 FSM 已是 ESCALATION（離開委派態額外等待零秒）。PG `execution_runs.status=FAILED`。
3. FSM（UTC，`logs\f_fsm_after_fail.log`）：`current_state=ESCALATION`；`decision_trace` 末筆 `trigger=autoclaude_delegated_exit`、reason `console-run run=c3e88f2c-… ENGINE-ESCALATION step=sdd-greenfield-at-001-1-1: [sdd-greenfield-at-001-1-1] 輸出未符合期望 regex: 'NEVER_PRINTED_1'`；`escalation_provenance.source=autoclaude_delegated_failed`；`escalation_history` 一筆、`triggered_at=2026-10-17T13:25:44+00:00`、`resolved_at=null`；`autoclaude_delegated_tracking.playbook_ref=run:c3e88f2c-ed2f-435c-a85f-731198d50dbf`。
4. Console／Bridge：`GET /engines/sdd?projectId=…` 與 Bridge `GET /sdd/fsm/…`：`currentState=ESCALATION`、`phase=null`、`escalationProvenance.source=autoclaude_delegated_failed`、歷史一筆未解、`recovery.target=IMPLEMENTATION`，`recovery.powershell` 為 `Push-Location '…\AISDLC_SDD_v0.30' -ErrorAction Stop; $env:SDD_STATE_DIR = '…\tg-phase-fail\build\reports\fsm'; & '…\python.exe' -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project 'tg-phase-fail' --to IMPLEMENTATION --reason "<人工原因>"; Remove-Item Env:SDD_STATE_DIR; Pop-Location`，`recovery.posix` 為對應的 `cd … && SDD_STATE_DIR=… … resume-from-escalation …`。
5. 畫面（`logs\f_views.log`；截圖 `f_20_sdd_governance_escalation.png`、`f_21_monitor_sdd_card_escalation.png`）：「SDD 治理」區 `state=ESCALATION`；紅色升級區塊 `data-unresolved=true`，摘要「ESCALATION・2026-10-17 21:25:44・console-run run=c3e88f2c-… ENGINE-ESCALATION step=…」，來源「autoclaude_delegated_failed・AutoClaude 委派失敗（引擎升級）」，恢復說明「恢復（在 SDD session 執行；Console 不提供恢復動作）建議恢復到 IMPLEMENTATION。指令內的 <人工原因> 請自行替換為實際原因；Console 不替換、也不執行它。」，`PowerShell`、`POSIX（bash／zsh）` 兩段各有「複製」鈕；「核准凍結」鈕為停用並寫「FSM 目前不在 HUMAN_PENDING（目前：ESCALATION）」；監控頁 SDD 卡同樣顯示升級區塊。
6. 恢復前下一批次被擋：`POST …/execute` → HTTP 409、`reason=sdd_fsm_state_conflict`、`details={"currentState":"ESCALATION","expectedState":["IMPLEMENTATION","SPEC_FROZEN"]}`；`execution_runs` 列數前後相同（二→二）、FSM 檔不變（`logs\f_c4_execute_blocked.log`）。失敗 run 的 RTM：HTTP 404、`reason=rtm_not_found`。
7. 人工恢復：取 Console 回應裡的 `recovery.powershell`，把 `"<人工原因>"` 換成中文理由，寫成 UTF-8 含 BOM 的 `.ps1`，以 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File` 執行 → rc=0（`logs\f_recovery_exec.log`）：stdout `{"from": "ESCALATION", "via": "RESUME_VERIFICATION", "to": "IMPLEMENTATION", "resolved_at": "2026-10-17T13:26:51+00:00"}`；stderr 帶兩段無關訊息（DEF-AC-024）。FSM：`ESCALATION → RESUME_VERIFICATION → IMPLEMENTATION` 兩跳 `trigger=human_resume`、reason 為中文理由原樣；`escalation_history[-1].resolved_at=2026-10-17T13:26:51+00:00`、`resolution=human_resume → IMPLEMENTATION: W4 失敗路徑實機：人工確認這個夾具的失敗是預期的，恢復到 IMPLEMENTATION`（中文未亂碼）；`escalation_provenance.source` 仍是 `autoclaude_delegated_failed`（恢復後不清除，與契約一致）。Console：`currentState=IMPLEMENTATION`、`recovery=null`、歷史末筆有 `resolved_at`。
8. 下一個批次可直接啟動：第二次 `POST …/execute` → 201（`runNumber=2`）→ 同一規格仍必敗 → run FAILED、FSM 再次 ESCALATION，歷史兩筆（已解、未解）。
9. 第二次恢復後再看畫面（`logs\g_views_after_recovery.log`；截圖 `g_20_sdd_governance_escalation.png`）：升級區塊數量為零、`state=IMPLEMENTATION`；Console 專案狀態仍顯示「失敗」（兩個狀態機各自獨立，與四源表的對映一致）。
10. 監控頁「最近決策」（`logs\h_decisions.log`；截圖 `h_22_monitor_sdd_decisions.png`）把引擎升級那筆顯示成「ESCALATION → ESCALATION」（DEF-AC-023）。

### §1.8 C1～C6 逐條判定

**C1 綁定與唯一性：成立（附但書）**
- 一對一綁定：Console 專案 `tg-phase` 經核准凍結寫回 `sddProject=tg-phase`（PG `projects.sdd_project` 同值，§1.5 綁定列）；`confirm` 併入既有專案不新建專案（回傳 id 相同）。
- 唯一性（在失敗路徑專案根上現跑，腳本 `f_e_c1.ps1`，原檔 `logs\f_c1_*.log`）：在 `tg-phase-fail` 的狀態目錄再用 CLI 建第二個 FSM 專案 `tg-other`（目錄內兩檔 `FSM-STATE-tg-other.yaml`、`FSM-STATE-tg-phase-fail.yaml`）。Console 另建專案 `tg-dup` 同一個 `executionPath`：`PUT …/sdd-binding {"sddProject":"tg-phase-fail"}` → HTTP 409、`reason=sdd_binding_conflict`、`details={"sddProject":"tg-phase-fail","holderProjectId":"e8d6acd9-b6e0-477a-9efe-395ffdcb6dc5","cause":"already_bound_elsewhere"}`，持有者 id 等於失敗路徑專案 id；viewer 改綁 → 403。
- fail-closed 指認（Bridge `POST /sdd/compile`，同一規格目錄）：不帶 `fsm_project` → HTTP 422、`reason=spec_not_frozen`、`detail=…\build\reports\fsm: 狀態檔不唯一（tg-other, tg-phase-fail），請設定 SDD_PROJECT 指定專案——fail-closed，不依字母序猜（他專案已凍結不得放行本專案）`；帶 `fsm_project=tg-phase-fail` → 200、`frozen_digest="verified"`；帶 `fsm_project=tg-other` → 422、`detail` 說該檔 `frozen_stages 為空且 current_state='SCENARIO_DETECT' 未達 SPEC_FROZEN 之後狀態`。
- Console 視圖：`GET /engines/sdd?projectId=…` 回 `fsm.project=tg-phase-fail`，`projects[]` 列出兩個專案（`tg-other:SCENARIO_DETECT`、`tg-phase-fail:ESCALATION`）。
- 但書：(a) 多 FSM 共處的指認與唯一性是在拋棄式的失敗路徑專案根上驗的，不是主專案；(b) 兩檔共處時沒有實跑一個批次（失敗路徑專案當時在 ESCALATION，批次被擋）；(c) `sdd-binding` 不檢查狀態檔是否存在（契約 §1.10.7 明文，本場未另行驗證該點）；`tg-dup` 改綁到同目錄的另一個 FSM 專案 `tg-other` 回 200（沒有人持有它）；(d) 主專案的狀態目錄只有一個 FSM 檔，主路徑本身沒有多專案情境。

**C2 人工閘：成立（附但書）**
- 正向：FSM 在 HUMAN_PENDING（由真 CLI 的 `gate --result PASS` 進入）；Console 畫面以已認證 approver `operator` 核准（approver 欄唯讀、取自登入身分）；FSM `decision_trace` 一筆、Console `audit_log` 一列、Bridge 稽核兩列（同 trace_id），時間差零秒，理由與 approver 逐值對上（§1.2 D-2、§1.5）；`frozen_stages[1]` 帶 `spec_doc_digests`（等於獨立重算）與 `approved_by`。
- 負向（在失敗路徑專案、FSM 為 IMPLEMENTATION 時現跑，`logs\f_freeze_negatives.log`）：operator 再凍結 → HTTP 409、`sdd_fsm_state_conflict`、`details={"currentState":"IMPLEMENTATION","expectedState":"HUMAN_PENDING"}`；viewer → 403 `ACCESS_DENIED`；未認證 → 401；畫面的「核准凍結」鈕在非 HUMAN_PENDING 時停用。
- 但書：(a) 核准人是任務書授權的「掌舵者代理」，以 `operator` 帳號操作，不是真人掌舵者；(b) v1.5 畫面不顯示也不送 `expectedDigests`（契約 §1.10.2 明文，§6.8.6 靜默處二），核准的是「按下那一刻磁碟上的檔」而不是「核准人看過的版本」，Bridge 的比對防線只對 API 消費者有效；(c) Stage-1 基線是模擬的（§1.10）。

**C3 治理執行：成立**
- 路徑 A 匯入並簽核後，批次以 `aisdlc_sdd` 啟動；工作區 `playbook.yaml` 帶 `workflow_type: aisdlc_sdd` 與規格檔路徑；引擎寫出帶凍結摘要的 RTM（證明治理外掛載入並使用了規格）；step_id 皆 `sdd-greenfield-at-…`（§1.2 D-3）。
- 三點摘要：凍結時（FSM `spec_doc_digests`）、匯入時（每個任務的 `passCriteriaSpec.specDigest`，PG `tasks.pass_criteria_spec`）、執行前（execute 的預檢，201 即相符）與引擎 RTM 的 `spec_digest` 四處皆為 `sha256:8f440a68…1e84`，並等於獨立重算。
- 負向（失敗路徑專案、FSM 為 IMPLEMENTATION，`logs\f_c3_execute_digest_changed.log`）：在凍結後的 TCS 末尾加一行，`POST …/execute` → HTTP 409、`reason=sdd_spec_digest_changed`、`details={"frozenDigest":"sha256:7dab39d1…bfc6","currentDigest":"sha256:8b0cca2e…bb0e","doc":"docs/03_testing/contracts/TCS-TgFail-20261017.md","pair":"frozen_vs_file"}`；`execution_runs` 列數前後相同、FSM 狀態與 `updated_at` 不變；還原檔案後摘要等於凍結摘要、Bridge 編譯回 200。

**C4 狀態同步：成立（附但書）**
- 成功路徑：批次期間 FSM 為 AUTOCLAUDE_DELEGATED（六十八次取樣皆是），完成回 IMPLEMENTATION，`decision_trace` 四跳與 reason 逐字合契約（§1.3）；Console 卡片與狀態檔逐值相等（§1.5）。
- 失敗路徑：引擎升級型失敗 → FSM ESCALATION（同一次輪詢）；Console 顯示阻塞、provenance、恢復指令；照顯示的指令恢復（PowerShell 5.1 實跑，rc=0，中文理由無亂碼）→ IMPLEMENTATION；下一批次 201；恢復前下一批次 409 零副作用；失敗 run 無 RTM（404）（§1.7）。CI 夾具把同一條路徑釘成每次可重跑的測試（§1.2 D-5）。
- 但書：(a) 失敗路徑用決定性替身，不是真 AI 失敗；(b) 取消交還、孤兒回收、外來委派（E2E-17 第 20、21 列）、暫停續跑與權杖重驗（第 25 列）本場沒有在 Console 實跑，Bridge 測試套件（`test_sdd_run_lifecycle.py`）覆蓋其行為；(c) `phase` 在所有畫面皆為 null，等 T-G 搬入；(d) 委派失敗的稽核軌跡 `from` 欄不是真實來源狀態（DEF-AC-023）。

**C5 追溯：成立**。引擎 YAML、Bridge、Console 三處逐值相等，畫面標「諮詢視圖」並寫明「AT 通過不等於規格被滿足」；失敗 run 為 404。但書：進行中批次取 RTM 應為 404（E2E-17 第 16 列後半）本場沒有實跑。

**C6 自食：成立（附但書）**。一個真實功能（T-G）依此迴圈做完：FRD-lite 加 TCS → SCG-0～3 機械檢查與報告 → Console 畫面核准凍結 → 路徑 A 匯入簽核 → 真 AI（haiku）在引擎治理下寫出程式與測試 → 引擎評估與 RTM → SCG-4 審查（含突變探針、覆蓋率、效能、完整性量測）；證據含 FSM 狀態檔（§1.3）、RTM（§1.2 D-4）、Console API 與畫面、一次失敗路徑（決定性替身，CI 夾具加 Console 實機）、QA 審查（§1.6）。但書：(a) SCG-4 審查者與 TCS 作者、迴圈操作員是同一人（被審的程式與測試則是另一個行程——claude haiku——所寫），W5 的獨立稽核才是第二眼；(b) SCG-4 審查結論沒有寫進 FSM（FSM 停在 IMPLEMENTATION，沒有走 PR_REVIEW、RTM_VERIFY、SCG-5、SCG-6）；(c) 這個功能要搬進 Bridge 並讓 `phase` 欄活起來仍是尚未做的接線步驟。

### §1.9 DEF 新列（自 DEF-AC-015 起；本場無 P≤2）

| ID | 嚴重度 | 歸屬 | 現象與證據 | 影響 |
|----|:------:|------|-----------|------|
| DEF-AC-015 | P3 | AISDLC_SDD | 模糊度閘 `score_frd` 對 FRD-lite 的表格形 AC 抽出零條：`logs\d1_slv_scan.log` 第 17 行 `score_frd(…) extracted ACs=0  (heading-form AC blocks only)`；改用 `score_ac` 逐列才算得出五條，`{"scorer_version": "v1.0", "acs_scored": 5, "max_score": 0.0, "blocking": []}` | 增量條款的 SCG-0 步驟 2a-bis 在表格形 AC 上空轉，輸出看起來是綠的 |
| DEF-AC-016 | P3 | AISDLC_SDD | SLV 規則的掃描目標（`FRD-*`、`CONTRACT-*.yaml`、`SRD-*` 等檔名樣式）在增量專案（FRD-lite 與 TCS 同檔）命中零檔：SLV-001、003、004、006 皆 `targets=[]`（`logs\d1_slv_scan.log` 第 2、4、5、7 行） | 邏輯驗證的機械半段在增量專案沒有可掃的東西，且不出聲；只剩人讀判斷 |
| DEF-AC-017 | P4 | AISDLC_SDD（規則文件） | 〈增量追溯表〉要求每個 SCG-0～3 檢查項一列、各引上位凍結文件與摘要，但「SCG-0／RTM 初版已建立」的對象就是增量自己的 TCS，規則沒說該引什麼；本場自引並標 SELF（`logs\d1_trace_table_check.log` 第 7 行） | 文件缺口；各專案會各自發明寫法 |
| DEF-AC-018 | P3 | AISDLC_SDD（技能與 hook 互相衝突） | `/sdd-gate`、`/sdd-review`、`/rtm-generate` 強制輸出到 `docs/03_testing/`，但 Rule 9.6 絕對禁令三在 SCG_VALIDATION、PR_REVIEW、RTM_VERIFY、IMPLEMENTATION 禁寫該前綴（允許寫入的只有七個狀態：AGENT_LOAD、INIT、RESUME_VERIFICATION、SCENARIO_DETECT、SPEC_AUDIT、SPEC_DRAFTING、SPEC_REGRESSION_CHECK）。實測探針六列 BLOCKED（`logs\d4_spec_write_guard_probe.log`） | 掛上 SDD hooks 的真 session 裡，技能在被規定產出報告的狀態下產不出報告；本場專案無 hooks 才寫得出 SCG-0～3 報告，SCG-4 審查報告改放 `build/reports/verification/` |
| DEF-AC-019 | P3 | AgentConsole（Settings 驗證） | `autoclaude.claudeExtraArgs` 的驗證規則 `^[A-Za-z0-9_.=:,/@\- ]{0,500}$` 擋掉括號、星號與引號，規則式授權 `--allowedTools "Bash(pytest:*)"` 無法設定：三種寫法皆 HTTP 400（`logs\f_claudeextraargs_probe.log`）；可表達的最窄授權是整個 `Bash` | Console 派的治理批次要讓 AI 跑 pytest，只能放開不受限的 shell；本場的真跑就是以此姿態執行 |
| DEF-AC-020 | P3 | AgentConsole（預設值） | 預設 `execution.globalTokenBudget` 為一百萬，七個 AT 的 haiku 批次用掉 1,086,389（108.6%）：畫面在第五步後出現「Token 使用量已達預算的 90%（899061 / 1000000）」，結尾「已超出預算（1086389 / 1000000），已要求暫停執行」，事件流 `events.jsonl` 第 77 行 `status":"PAUSING"`；暫停發生在最後一步收尾，run 仍 COMPLETED（截圖 `d4_10_execute_rtm_panel.png`） | 預設預算對治理批次偏低：同規模再大一點的批次會在預設值下被中途要求暫停 |
| DEF-AC-021 | P4 | AutoClaude | 引擎 subprocess 模式每次呼叫真 `claude -p` 先等三秒：各步驟 `playbook_sdd-*.log` 共八處 `Warning: no stdin data received in 3s`，合計二十四秒，約占一百四十二秒批次的 17%；疑因（待驗）：`pty_wrapper._start_subprocess` 以 `stdin=subprocess.PIPE` 起行程且不寫不關（`pty_wrapper.py` 第 266 行） | 每個真 AI 步驟多等三秒 |
| DEF-AC-022 | P4 | AutoClaude（可觀測性） | 重試嘗試的失敗原因不留痕：步驟一第一次嘗試因最終回覆缺 INTAKE、SPECIFICATION、HUMAN_GATE 而失敗，事件流只有 `STARTED(1)`、`RETRYING(2)`、`COMPLETED(2)`（`events.jsonl` 第 16、24、31 行，欄位無原因），`engine-1.log` 沒有原因行；要知道只能翻每步驟的原始輸出檔 | 維運者看不出為什麼重試 |
| DEF-AC-023 | P4 | AISDLC_SDD 與 AgentConsole（顯示） | 委派失敗進 ESCALATION 時，`decision_trace` 該筆 `from` 是 `ESCALATION`（`record_escalation` 先把 current 寫成 ESCALATION；`state_loader.py` 自己的註解稱為既有行為），真實來源 `AUTOCLAUDE_DELEGATED → ESCALATION` 這一跳不在稽核軌跡裡；Console 監控頁「最近決策」因此顯示「ESCALATION → ESCALATION」（`logs\f_fsm_after_fail.log` 第 93～96 行、`logs\h_decisions.log`） | 稽核軌跡缺一跳、畫面讀起來像自迴圈 |
| DEF-AC-024 | P4 | AISDLC_SDD 與 AgentConsole（恢復指令體驗） | Console 顯示的恢復指令每次執行都在 stderr 印兩段與使用者無關的訊息：`RuntimeWarning: 'tools.fsm_runtime.fsm_runtime' found in sys.modules…`（顯示的指令缺 `-W ignore::RuntimeWarning`，Bridge 自己呼叫 CLI 有帶）與「Reminder: remove SDD_HOOKS_DRY_RUN=1 from ~/.zshrc…」（SDD 恢復成功後無條件印出）；功能無礙（`logs\f_recovery_exec.log`：rc=0、FSM 已回 IMPLEMENTATION） | 初次使用者會以為恢復出錯 |
| DEF-AC-025 | P4 | 契約與實作 | 契約 E2E-17 第 5 列與四源對拍表寫「`audit_log` 的 `action=project.sdd.freeze`」；實際 `console.audit_log` 欄位為 `id, occurred_at, subject, role, method, path, entity_type, entity_id, http_status, trace_id`，沒有 `action` 欄（§1.4） | 照契約寫的獨立 SQL 查不到；實務上靠 `method` 與 `path like '%/sdd/freeze'` 認列 |
| DEF-AC-026 | P4 | 契約與實作 | 契約 E2E-17 第 5 列寫 Bridge 稽核單一事件 `event=sdd_write`、`verb=spec-frozen`；實際是同一個 trace_id 的兩列：`event=sdd_cli verb=spec-frozen`（rc=0）與 `event=sdd_write verb=freeze`（§1.2 D-2、§1.4） | 契約文字與稽核檔不符，W5 照契約斷言會誤報 |
| DEF-AC-027 | P4 | 文件（主控帳務） | `docs/04_planning/AutoSDD_improving_115.md` 標頭「狀態」仍寫「Architect 草稿（§1～§5…）」，而它在本場被當成 Stage-1 的 PRD 角色基線（追溯表有三列引用它）；該檔第 3 行 | 狀態標頭落後；列此備查 |

### §1.10 〈未驗證〉與 Windows 專屬邊界

未驗證（本場沒有證明，請勿當成已通過）：

1. 平台：只在 Windows 11、pwsh 7.6.7、claude 2.1.302、haiku 上真跑；macOS、Linux、Docker 全棧（E2E-17 第 26 列）沒有跑；POSIX 形的恢復指令本場沒有在真的 POSIX 殼裡執行過（本機只有字串斷言，夾具的 POSIX 分支要等 CI 或 macOS 才會跑到）。
2. 真 AI 的批次全是 Unit 類 AT（重試上限五）；Integration 類與 E2E 類 AT 只經決定性替身（CI 夾具與失敗實機）。
3. Stage-1 基線是模擬的：五份上位文件由 HEAD 複本充當、FSM 以 `transition` 走到 HUMAN_PENDING、`spec-frozen` 由「掌舵者代理」按下，沒有真的跑過那五份文件的 SCG-0～3 內容檢查。
4. `/stage-compaction`（SPEC_FROZEN 後 R-9.4 強制）沒有執行；三個 SDD 技能的判斷半段由操作員人讀，不是由技能代理執行；SLV 判斷式規則未逐條出報告。
5. SCG-4 審查者、TCS 作者、迴圈操作員是同一人；審查結論沒有寫進 FSM；PR_REVIEW、RTM_VERIFY、SCG-5、SCG-6 沒走；FSM 刻意停在 IMPLEMENTATION。
6. T-G 的 `tg_phase.py` 尚未搬入 Bridge：所有畫面與 API 的 `phase` 恆為 null；Bridge 測試 F-5 預留位仍略過；契約 E2E-17 第 14、19 列「W4 接線後」的 phase 斷言未驗。
7. 取消交還、孤兒回收與外來委派、暫停續跑與權杖重驗、進行中批次的 RTM 404、Docker 全棧與唯讀掛載（E2E-17 第 16 列後半、20、21、25、26 列）沒有在 Console 實跑；第 23 列只做了 freeze 與 sdd-binding 的 viewer 403、freeze 的未認證 401，其餘端點的權限矩陣未逐一驗。
8. wexpect／pty 路徑沒有走到（引擎偵測 re-exec 啟動器後改走 subprocess 模式）；Brain（Minimax）停用，step correction、goal synthesis、自演化提案沒有被行使。
9. 預算暫停只出現在最後一步收尾，「中途暫停再續跑」沒有被行使（DEF-AC-020）。
10. 畫面證據只有 Playwright chromium、固定 viewport（寬 1440、高 2000）；沒有跨瀏覽器。
11. C1 的多 FSM 共處在拋棄式的失敗路徑專案根上驗，主專案沒有；兩檔共處時沒有實跑批次。

Windows 專屬邊界：

- `claude` 解析為 `C:\Users\wuwei\.local\bin\claude.EXE`（原生 exe，不是 `.cmd` shim）；引擎因 re-exec 啟動器偵測改走 subprocess 模式（`engine-1.log` 第 12、13 行）。
- 顯示的 PowerShell 恢復指令以 Windows PowerShell 5.1 實跑成功：腳本檔需 UTF-8 含 BOM，否則 5.1 以 ANSI 讀取會弄壞含中文的字串；CI 夾具的 Windows 分支同樣寫 BOM 加 CRLF 的暫存檔。
- Console 同時顯示 PowerShell 與 POSIX 兩種形態，不分主機作業系統；在 Windows 主機上 POSIX 形帶 Windows 路徑，僅供複製到別台機器用，不能在本機執行。
- Bridge 測試套件有七個測試因 Windows 無法建立 symlink 而略過（開發者模式或系統管理員才可），與本場無關。
- 寫入權杖與 `SDD_STATE_DIR` 的處理：引擎子行程環境只有 `SDD_PROJECT`，沒有狀態目錄指標與任何 `BRIDGE_*`（CI 夾具以替身的 trace 斷言；實機以磁碟掃描零命中佐證）。

### §1.11 檔案、重跑與收尾

**本場新增並供 commit 的檔案**（兩個，皆在 repo 內）：
- `docs/06_quality/AutoSDD_ZeroTrust_Audit_115.md`（本檔）
- `AgentConsole/engine-bridge/tests/test_sdd_dogfood_fixture.py`

**重跑 CI 夾具**（根 `.venv`，工作目錄 engine-bridge）：`python -m pytest tests/test_sdd_dogfood_fixture.py -q`；Windows 以 `Push-Location …\AgentConsole\engine-bridge; …; Pop-Location` 同一次呼叫包住。

**暫存目錄證據檔**（絕對路徑根：`C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\0f21f73d-2c1d-4c72-a705-54ac42f61c74\scratchpad\w4_dogfood\`）：`logs\*.log`（本檔引用的原檔）、`shots\*.png`（十四張截圖）、`artifacts\`（AI 的 `tg_phase.py` 與七個測試、TCS、SCG-0～3 報告、SLV 報告、SCG-4 審查報告）、`*.ps1`、`*.py`、`pw\*.cjs`（操作員工具，非產品碼）。

**環境殘留**（給接手者）：`%TEMP%\e2e\projects\tg-phase`（FSM 停在 IMPLEMENTATION，供 W5 重驗）、`%TEMP%\e2e\projects\tg-phase-fail`（FSM 停在 IMPLEMENTATION，兩筆升級歷史皆已解；另有第二個 FSM 專案 `tg-other` 停在 SCENARIO_DETECT）。收尾已停服務並停掉 `qa-pg` 容器：該容器以 `docker run --rm` 啟動，`docker stop` 後容器與其中的 Console 資料（專案、run、稽核列、為 C1 驗證建又刪的 `tg-dup`）一併消失，所以 PG 側的引文（稽核列、`execution_runs`、綁定欄）只留在本檔與 `logs\`；W5 要重驗須先重建環境（`reset_local.ps1` 類腳本），再以路徑 A 對仍在磁碟上的專案根與 FSM 狀態檔重新匯入。埠狀態見交卷訊息。
