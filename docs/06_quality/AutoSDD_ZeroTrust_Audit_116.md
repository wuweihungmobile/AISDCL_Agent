# AutoSDD 整合輪 116 零信任稽核

**對應計畫**：[AutoSDD_improving_116.md](../04_planning/AutoSDD_improving_116.md) §2〈問題 3 的判準 C1～C7〉、§3 缺口 G-116-NN、§6 裁決 D-116-14／D-116-15。
**本檔分工**：W3 QA（Sonnet；未參與三份規格的撰寫、未參與任何實作；規格作者＝W2 SA、實作者＝真 haiku 經 Bridge 委派〔DF-A〕與 hooks-ON 的 headless Sonnet〔DF-B、DF-C〕）一人寫入。三份 SCG-4 報告與 RTM 在各子專案自己的 `docs/06_quality/`，本檔是總表。
**證據原則**：每一格「成立」都附當回合真跑的指令、rc 與逐字輸出；沒跑的寫進 §8〈未涵蓋〉。證據原檔住 QA 暫存目錄 `…\scratchpad\qa_w3\`（閘門日誌、突變結果 JSON、FSM 引文）與 `…\scratchpad\qa_drill\`（C7 演練），重點輸出已逐字引在本檔。本檔不含任何機密值（Bridge 寫入權杖為拋棄式測試值，只以「命中檔數」形式出現）。**突變檢驗全部在記憶體內改寫，repo 檔案零改動**（`git status --short` 在本檔寫入前只有本輪交付文件）。
**本檔不含的決定**：缺陷編號 DEF-200 由主控入帳；AgentConsole 面缺陷編號續用 `DEF-AC-0NN`——115 收尾補記已佔用 035～037，本輪新編號自 **DEF-AC-038** 起。
> 主控補註（2026-10-18 收尾後）：本檔「G-116-17 未修／修後行為未驗」各處（§1.0、§1 表 C1／C7、§7、§9.7）為一審／二審當時實況，逐字保留。根 router 兩格 matcher 已修齊（PostToolUse `d75a38a0`、PreToolUse `a8504ba1`；帳本 DEF-200-551），修後行為由 Sonnet 操作員以 haiku headless 三件組視窗（從根啟動、狀態目錄在 scratch）驗過：ESCALATION 下 PowerShell 回 JSON deny、INIT 下 CONTEXT-LEDGER 出現 pre／post 兩條 PowerShell、SessionStart 注入專案鍵；逐字座標＝`AutoSDD_improving_116.md` §7 末列。

## §1 三路 dogfood 證據與 C1～C7 判定

### §1.0 結論先行

三個真實小功能都已實作並 commit：**DF-A** AutoClaude 的 Webhook 發送（委派路徑：Bridge＋真 haiku，執行根為真實 `AutoClaude/` 樹）、**DF-B** AgentConsole 決策軌跡 `from` 還原（純 SDD session，hooks-ON headless Sonnet）、**DF-C** 根層 `sdd_env.py` 三件組產生器（同上）。SCG-4 一審結果：**DF-B 通過**（19 個突變全被殺），FSM 已走完 PR_REVIEW→RTM_VERIFY 到 **RELEASE_READY**；**DF-A 與 DF-C 各有一個 P2**（F-01、F-02：測試強度，記憶體內突變檢驗有 12 個由 TCS 的 R 條文導出的突變存活），兩鍵各一次 `PR_REVIEW` FAIL、退回 IMPLEMENTATION，待修復棒後二審。無 P1。hooks-ON 的 C1 取得 **G-116-17 的真實暴露證據**（兩個真實視窗各 2 次 PowerShell 呼叫完全不入 CONTEXT-LEDGER，且 C7 演練證實 ESCALATION 下 PowerShell 不被擋）。

| 判準 | 判定 | 一句話證據（座標） |
|------|------|-------------------|
| C1 入口可達 | **部分**（G-116-17 暴露證據成立，未修） | 兩個 hooks-ON 視窗只靠三件組即得 SessionStart 成功注入 `project:`／`current_state:`（§1.3）；ledger 的 Read／Write／Edit 入帳與 router 觸發數逐項相等；但 PowerShell 呼叫（兩視窗各 2 次）零入帳（§1.3），阻塞態下也不被擋（§6 步驟 18～19） |
| C2 文件落點 | 成立 | 三個狀態目錄的狀態檔與 ledger 檔 `git check-ignore -v` 皆命中；Bridge 與 session 同址；三份 TCS 在各子專案自己的 `docs/03_testing/contracts/`；報告與 RTM 落 `docs/06_quality/`（§1.4） |
| C3 閘門一致 | 成立 | BRIDGE §8.9 對映表；`AutoClaude/CLAUDE.md` 與 `AgentConsole/CLAUDE.md` 各有指路一行；AutoClaude 的 skills 鏡像不再是 v0.09 舊版（§1.4） |
| C4 棕地可用 | 成立（附但書） | 三份 TCS 皆走增量條款；演練鍵逐步重跑 BRIDGE §8.4 的採納鏈與談判閘成功（§6 步驟 1～12）；機械半段空轉由 QA 人讀補位；Java／TS 只劃界、本輪未實證 |
| C5 技能／代理可達 | 成立（附但書） | `AISDLC_SDD:sdd-review`、`AISDLC_SDD:rtm-generate` 以前綴叫起並用於本審查；`sync_exposed_skills.py --check` rc 0（父層與 AutoClaude 各 59 檔）；Skill 工具回傳 session 啟動時的快取文字，路徑與磁碟已更新的版本不同（F-08，P4） |
| C6 實證 dogfood | 成立（附但書） | 三個功能皆實作並 commit，含一條委派路徑（DF-A：九步評估各 rc 0、RTM 9／9）與兩條純 session 路徑（DF-B、DF-C）；但 SCG-4 一審 DF-A、DF-C 各有 P2，閉環要等二審 |
| C7 可重複且不鎖死 | 成立（附但書） | 阻塞態演練：deny 訊息自帶外部專案模式的恢復指令，原樣貼進另一個 PowerShell 行程即解鎖，解鎖後同一次讀檔成功（§6）；附但書＝阻塞態對 PowerShell 無效（G-116-17 的另一面向） |

**對「問題 3 能不能答『完美利用』」的建議**：計畫書自訂「七條同時成立，缺任一降為部分」。C1 因 G-116-17 未修維持「部分」，所以本輪仍不宜答「完美」；W4 加 PowerShell matcher 並經 QA 驗證兩視窗的 ledger 出現 PowerShell 入帳後，C1 可升成立，屆時只剩 SCG-4 二審的閉環。

### §1.1 環境與前置

| 項目 | 值 |
|------|----|
| 日期、角色 | 2026-10-18；W3 QA（Sonnet 5.5） |
| 作業系統與殼 | Windows 11 專業版 10.0.26300；PowerShell 工具為 pwsh 7.6.7（Core）；鐵律一：不用 Bash 工具 |
| 直譯器與工具 | Python 3.11.9（根 `.venv`）；Claude Code 2.1.302；coverage 7.6.1（僅裝在 scratch 目錄 `qa_w3\covlib`，用 `uv pip install --target`，根 `.venv` 無 `coverage` 套件，已複驗） |
| 程式版本 | HEAD `07cfa9ae`；SDD LATEST `AISDLC_SDD_v0.30`；三份 TCS 凍結摘要當回合重算皆相符（見各報告頭） |
| 服務 | 本機 PG 容器 `autoclaude_pg`（pg18）在場，AutoClaude 全套以 `--dist loadgroup` 注入 PG 位址；engine-bridge 套件不需 DSN |
| FSM 狀態目錄 | `AutoClaude\build\reports\fsm`（鍵 `autoclaude-webhook`）、`AgentConsole\build\reports\fsm`（`agentconsole-fsm-trail`）、`build\reports\fsm`（`monorepo-sdd-env`）；演練鍵 `sdd-drill` 的狀態目錄在 scratchpad（不在 repo 內）。框架真實狀態檔 `AISDLC_SDD_v0.30\build\reports\fsm\FSM-STATE-AISDLC_SDD.yaml` 全程未碰（`fsm_call.py` 只接受四把鍵，並在程式內斷言狀態目錄不是框架預設目錄；該檔 mtime 仍為 2026-07-16 01:36:40，早於本輪） |

### §1.2 DF-A 委派路徑證據複驗（操作員報告 vs 原始檔 vs 本場重算）

來源：操作員報告 `…\scratchpad\df_a\report.md`；原始檔 `df_a\logs\a2_*`、`df_a\workspace\4e6bd6c9-…\`（`engine-1.log`、`run.json`、`events.jsonl`、`engine\checkpoints\rtm\`）、`df_a\artifacts\`。

| 項目 | 複驗結果（當回合） |
|------|------------------|
| compile 回應（`a2_step3_compile_raw.json`） | `frozen_digest="verified"`、`unmapped_at_ids=[]`、`warnings=[]`、`scenario="brownfield"`、`fsm_project="autoclaude-webhook"`；`digest` 與 Stage-2 凍結摘要 `sha256:2d473454d33d46fa341566a6f4cea25d135ce3a7a22dd0acce1d41f1bfcec8cf` 逐字相等；9 個任務，step_id 為 `sdd-brownfield-at-001-1-1`、`-2-1`、`-3-1`、`-3-2`、`-3-e-1`、`-4-e-1`、`-5-1`、`-6-1`、`-6-2`；每個任務 `evaluator_command` 為 `pytest tests -k "AT_001_x_y" -q`、驗收 regex 為 `\[AT_OK_001_x_y\]`、`max_retries=5` |
| 建批次請求（`a2_step3_run_request.json`） | `execution_path` 為真實樹 `D:\CursorProject\AISDCL_Agent\AutoClaude`；請求層 `env={"AUTOCLAUDE_NO_PG_AUTODETECT":"1"}`；`extra_args=["--permission-mode","acceptEdits","--allowedTools","Read,Edit,Write,Bash,PowerShell","--model","haiku"]`、`token_guard.auto_resume=false`；`sdd` 帶 `spec_dir`、`spec_file`、`fsm_project="autoclaude-webhook"`、`approver="掌舵者代理（主控）"` |
| run 終態（`run.json`、`a2_final_run_state.json`） | `status=COMPLETED`、`exit_code=0`、`completed_steps=9`／`total_steps=9`、`reason="引擎正常結束"`、`started_at=2026-10-18T05:04:43Z`、`completed_at=2026-10-18T05:13:21Z`（518 秒）、`peak_token_pct=14.6582`、`sdd.sync={"exit":"done","ok":true}`；`sdd.root=D:\CursorProject\AISDCL_Agent\AutoClaude`、`sdd.state_dir=…\AutoClaude\build\reports\fsm`（與 BRIDGE §8.1 的標準值同址，Bridge 與 hooks-ON session 看到同一份狀態檔）；`env_keys` 只列變數名 `AUTOCLAUDE_NO_PG_AUTODETECT`（不存值） |
| 引擎日誌（`engine-1.log`） | 九步各一行「執行評估指令: pytest tests -k "AT_001_x_y" -q (timeout=120s)」緊接「評估通過 [exit=0]」（13:05:11～13:13:21）；`STEP_TOKEN_PEAK` 依序 10.0410、12.2132、11.0204、11.6009、12.0775、10.8740、13.4284、14.0979、14.6582；`KernelResult(success=True, completed_steps=9, total_steps=9, reason='success')` |
| FSM 軌跡 | 見 §1.5：`SPEC_FROZEN→TEST_CONTRACT_NEGOTIATED`（`test_contract_enter`）→`IMPLEMENTATION`（`test_contract_exit`，agreed）→`AUTOCLAUDE_DELEGATED`（第一輪 run `f5446f48…` START）→第一輪 FAILED 被第二輪回收（`RECLAIMED old_status=FAILED by=4e6bd6c9…`）→START→`IMPLEMENTATION`（`COMPLETED`）；`escalation_history` 0 筆；`autoclaude_delegated_tracking.playbook_ref=run:4e6bd6c9-…`。談判閘 `negotiate-enter→negotiate-exit agreed→delegate-enter→delegate-exit done` 的語意在 Bridge 路徑下以上列觸發名稱對應 |
| RTM | Bridge `GET /autoclaude/runs/{id}/rtm` 回應（`a2_step5_rtm_response.json`）：AT 9／9（100.0）、AC 6／6（100.0）、`unmapped_at_ids=[]`、`fully_covered:true`、`advisory:true`；引擎 `engine\checkpoints\rtm\RTM-COVERAGE-autoclaude-webhook.yaml`（637 位元組）同值，且與 `artifacts\a2_RTM-COVERAGE-autoclaude-webhook.yaml` 的 sha256 相同（`841E28DF…EC6F0`）；`RTM-GAP-autoclaude-webhook.md`：「全部 AC/AT 已覆蓋，無 gap」 |
| 權杖不落地 | 以 Python 位元組搜尋（含 UTF-16LE 形式；只印命中數）：`df_a` 全目錄排除 `secret\`：128 檔、命中 0；repo 工作樹含 gitignored（排除 `.git`、`.venv`、`node_modules` 與各種快取目錄）：39810 檔、命中 0 |
| 範圍越界 | 見下 |
| RC-1 根因（DEF-200-550） | 見下 |
| Bridge StepTracker 遮罩漏配（操作員新觀察 b） | 見下 |

**範圍越界（haiku 工作樹，逐檔）**：`git show --stat 306dbb2a` 恰三檔（`notifier.py` 24 行異動、`webhook_sender.py` 135 行新增、`tests/utils/test_webhook_sender.py` 503 行新增）。對 haiku 執行窗（本地 13:04～13:14）掃描整個 repo（含 gitignored，排除 `__pycache__` 與各種快取目錄）：被改過的檔案恰五個——`AutoClaude/build/reports/fsm/FSM-STATE-autoclaude-webhook.yaml.bak`（13:04:42，Bridge 經 CLI 寫）、`AutoClaude/autoclaude/utils/webhook_sender.py`（13:10:40）、`AutoClaude/autoclaude/utils/notifier.py`（13:12:19）、`AutoClaude/tests/utils/test_webhook_sender.py`（13:12:58）、`AutoClaude/build/reports/fsm/FSM-STATE-autoclaude-webhook.yaml`（13:13:21，Bridge 經 CLI 寫）。**越界檔數 0**。另核對 commit 內容與操作員執行後留的副本（`artifacts\a2_webhook_sender.py`、`a2_notifier.py`、`a2_test_webhook_sender.py`）逐位元組相同（sha256 前綴 `bff12203081a7d44`／`fe28c5b982eb25e0`／`3dc702f6bb952b06`，位元組數 5588／8141／20120），即送審的就是引擎評估通過的那份。

**RC-1 根因與修法複驗**：第一輪偽 TOKEN_HALT 的根因是 `context_pct_from_claude_json` 取 `claude -p --output-format json` 頂層 `usage` 的跨回合累計（每一回合都把整個 prompt cache 再讀一次）：夾具 `claude_json_step1_halt_fixture.json`（16 回合）累計 24＋1,354,671＋110,846＝1,465,541 token，除以 100 萬視窗＝146.6%、夾成 100% 觸發 TOKEN_HALT；同一次呼叫的 `usage.iterations[-1]`（最後一次 API 呼叫＝目前 context）為 2＋129,496＋625＝130,123＝13.0123%。第二輪九步的逐步對照表（`a2_step_usage_table.txt`）：舊估法在步 5-1 為 1,792,905（100.0%）、步 6-1 為 1,177,597（100.0%）、步 4-e-1 為 82.8%，新法九步皆在 10.0%～14.7%——**根因與修法成立**。修法在 `AutoClaude/autoclaude/utils/token_tracker.py`（`_latest_iteration_usage`／`_context_used_tokens`；缺 `iterations`、非空 list、末筆不是映射或沒有 context 鍵時退回累計）與 `tests/test_token_regex.py:292-351` 的 `TestContextPctUsesLatestIteration`（6 個測試函式，含真實夾具）；AutoClaude 全套當回合為綠（§3）。殘餘風險見 F-06（P4）。

**StepTracker 遮罩漏配（DEF-AC-038，P3）對 RTM／FSM 的影響＝無**：`a2_final_events.json` 的 81 筆事件中，步驟 7（5-1）沒有 STARTED／COMPLETED；步驟 6（4-e-1）出現 `RETRYING`（attempt 2，seq 56）；seq 80 為 `STEP_TRACKING_GAP`（列出 `sdd-brownfield-at-001-5-1`），`run.json` 的 `completed_step_ids` 把 5-1 排在最後（由 `_reconcile_step_gap` 補入）。成因：引擎日誌的遮罩把步 5-1 啟動行 prompt 中的 `u5er:p4ss@`（TCS 的合成假密碼）改成 `u5er:***@`（`engine-1.log` 第 36 行，該行含 https 與 http 兩個假位址各一處；`playbook.yaml` 內仍是原文 `u5er:p4ss@`），Bridge `StepTracker._match`（`app/logparse.py:171-181`）用「playbook prompt 是啟動行 `-p` 的子字串」配對，遮罩後不成立。影響評估：RTM 取自引擎 YAML（不經 StepTracker）；FSM 的 `delegate-exit` 決策由純函式 `terminal_decision`（`app/sdd_sync.py:127-145`）依 run 終態決定，不讀 StepTracker——兩者在本 run 皆正確（§1.5、上表）。真正受影響的是 Console 步驟時間軸與計數：該步無事件、前一步被標成第 2 次嘗試，且若被遮罩的步驟失敗，`fail_current()` 會把失敗記到前一步（`app/runner.py:605-608`）。**建議修法**：以引擎日誌 `STEP_TOKEN_PEAK | step=` 行為步驟邊界的權威來源，或比對前先對 playbook prompt 套同一份遮罩；回歸測試需用含 `user:pass@` 形態的 prompt。

### §1.3 DF-B、DF-C 的 hooks-ON 證據（C1）

來源：`df_b\hooks.log`、`df_c\hooks.log`（headless `claude -p --model sonnet --debug hooks`，環境三件組由啟動器注入）；兩個 `CONTEXT-LEDGER-2026-10-18.yaml`（各在該鍵的狀態目錄）。

**SessionStart 成功與注入（逐字節錄；log 時戳 UTC）**：

| 視窗 | 行 | 內容 |
|------|----|------|
| DF-B | `hooks.log:522-523` | `Hook SessionStart:startup (SessionStart) success:`（`context_budget_guard.py`，`[SDD-CTX-GUARD]` 水位簡報；`:523` 記 2125 字元） |
| DF-B | `hooks.log:529-530` | `Hook SessionStart:startup (SessionStart) success:`（`sdd_hook_router.py session_start`）其 `additionalContext` 以 `[SDD-FSM] Session bootstrap` 起首，逐行為 `- project: agentconsole-fsm-trail`、`- current_state: IMPLEMENTATION`、`- applied_ci_events: 0`、`- total_scg_retries_all_time: 0`，後接 `[SDD-FSM][DECISION-TRACE] 最近 5 筆狀態轉換：`（`:530` 記 1800 字元） |
| DF-C | `hooks.log:524-525`、`:531-532` | 同形；`- project: monorepo-sdd-env`、`- current_state: IMPLEMENTATION`（`:525` 記 2122 字元、`:532` 記 1766 字元） |

逐字節錄（行首 UTC 時戳與 `Hook SessionStart:startup (SessionStart) success:` 字樣；注入內容為 JSON 字串，`\n` 為字面跳脫；每行只取前 200～330 字元，行長標在末尾）：

```text
df_b\hooks.log:522  2026-10-18T03:49:32.810Z [DEBUG] "Hook SessionStart:startup (SessionStart) success:\n{\"hookSpecificOutput\": {\"hookEventName\": \"SessionStart\", \"additionalContext\": \"[SDD-CTX-GUARD]\\uff08Windo …（行長 5969 字元，後略）
df_b\hooks.log:529  2026-10-18T03:49:32.902Z [DEBUG] "Hook SessionStart:startup (SessionStart) success:\n{\"hookSpecificOutput\": {\"hookEventName\": \"SessionStart\", \"additionalContext\": \"[SDD-FSM] Session bootstrap\\n- project: agentconsole-fsm-trail\\n- current_state: IMPLEMENTATION\\n- applied_ci_events: 0\\n- total_scg_retries_all_time: 0\ …（行長 2030 字元，後略）
df_c\hooks.log:524  2026-10-18T03:53:55.699Z [DEBUG] "Hook SessionStart:startup (SessionStart) success:\n{\"hookSpecificOutput\": {\"hookEventName\": \"SessionStart\", \"additionalContext\": \"[SDD-CTX-GUARD]\\uff08Windo …（行長 5966 字元，後略）
df_c\hooks.log:531  2026-10-18T03:53:55.799Z [DEBUG] "Hook SessionStart:startup (SessionStart) success:\n{\"hookSpecificOutput\": {\"hookEventName\": \"SessionStart\", \"additionalContext\": \"[SDD-FSM] Session bootstrap\\n- project: monorepo-sdd-env\\n- current_state: IMPLEMENTATION\\n- applied_ci_events: 0\\n- total_scg_retries_all_time: 0\\n- [S …（行長 1996 字元，後略）
```

**CONTEXT-LEDGER 入帳與 hooks.log 對照（當回合以 Python 解析）**：

| 視窗 | session id | ledger 檔 | 入帳統計 | hooks.log 的 router（`sdd_hook_router.py`）觸發 | PowerShell 在 hooks.log | PowerShell 在 ledger |
|------|-----------|-----------|----------|-----------------------------------------------|-------------------------|---------------------|
| DF-B | `c92b50ce-1c37-4565-b186-2a557a651199` | `AgentConsole\build\reports\fsm\CONTEXT-LEDGER-2026-10-18.yaml`（27 筆） | Read 8 pre＋8 post、Write 3＋3、Edit 2＋2、`ConversationLedger` 1（`conv-overhead`） | PreToolUse 與 PostToolUse 各 Read 8、Write 3、Edit 2 | 2 次工具呼叫＝`PreToolUse:PowerShell` 4 次（`lint_powershell_command.py`×2、`block_destructive_git.py`×2）、`PostToolUse:PowerShell` 2 次（`context_budget_guard.py`×2）；**`sdd_hook_router.py` 觸發 0 次** | **0 筆** |
| DF-C | `b8887dbe-6250-4f07-8616-6ab35433982b` | `build\reports\fsm\CONTEXT-LEDGER-2026-10-18.yaml`（14 筆） | Read 3＋3、Write 3＋3、Edit 1＋1 | 各 Read 3、Write 3、Edit 1 | 同上：`PreToolUse:PowerShell` 4 次、`PostToolUse:PowerShell` 2 次；router 0 次 | **0 筆** |

**判讀**：ledger 的入帳數與 router 在 Read／Write／Edit 上的觸發數逐項相等（26＝13 pre＋13 post；14＝7＋7，另加 DF-B 的 1 筆 `ConversationLedger`），所以 SDD 的 context-ledger 守門在被 matcher 命中的工具上確實生效（C1 的正面）；PowerShell（Windows 上唯一的 shell 載具）每次呼叫只觸發兩支非 SDD 的 hook，**ledger 零入帳**。這是 `SDD_AUTOCLAUDE_BRIDGE.md` §8.12 與 D-116-14 預先寫定的再開症狀「Windows 設 `SDD_ACTIVE_VERSION` 的真實 session 其 CONTEXT-LEDGER 缺 PowerShell 呼叫」的**真實暴露證據**（非探針種子、非構造：兩個真實開發視窗，sid 與檔案路徑如上）。另：兩份 hooks.log 的 `permissionDecision` 值皆為空集合、`deny` 字樣只出現在 5 行設定載入訊息（零次 deny）——兩視窗都停在 IMPLEMENTATION，沒有寫規格檔。Grep 工具（DF-B 2 次、DF-C 1 次）同樣不經 router，屬唯讀工具，不構成暴露。

### §1.4 C2／C5 附帶

**狀態目錄不入庫（`git check-ignore -v` 的「規則」欄與「路徑」欄整理成一行；五次 rc 皆 0）**：

```text
AutoClaude/build/reports/fsm/FSM-STATE-autoclaude-webhook.yaml        => AutoClaude/.gitignore:9:build/
AgentConsole/build/reports/fsm/FSM-STATE-agentconsole-fsm-trail.yaml  => AgentConsole/.gitignore:16:build/
build/reports/fsm/FSM-STATE-monorepo-sdd-env.yaml                     => .gitignore:70:/build/reports/fsm/
build/reports/fsm/CONTEXT-LEDGER-2026-10-18.yaml                      => .gitignore:70:/build/reports/fsm/
AgentConsole/build/reports/fsm/CONTEXT-LEDGER-2026-10-18.yaml         => AgentConsole/.gitignore:16:build/
```

五次 rc 皆 0；本檔寫入前 `git status --short` 只有本輪交付文件（狀態與 ledger 檔不在其中）。

**skills 鏡像**：`python AISDLC_SDD/scripts/sync_exposed_skills.py --check` rc 0：`[skills-ssot] OK … .claude/skills == LATEST(AISDLC_SDD_v0.30)（59 檔一致）`、`OK … AutoClaude/.claude/skills == LATEST(AISDLC_SDD_v0.30)（59 檔一致）`；`ci-gate.ps1` 內同一道 lint 同結果。

**skill 可達與實際使用（C5）**：以 Skill 工具叫起 `AISDLC_SDD:sdd-review` 與 `AISDLC_SDD:rtm-generate`，內容實際用在本審查：三份 SCG-4 報告沿用 `sdd-review` 的 A（FRD 一致性表）、B（Contract）、C（Invariants）、D（RTM 覆蓋）、審查結論表與必修項目表結構；三份 RTM 沿用 `rtm-generate` 的檔頭（版本／日期／狀態／覆蓋率）、追溯矩陣（EPIC｜Feature｜User Story｜AC｜Test Case｜API｜NFR｜狀態）與覆蓋率統計。**觀察（F-08，P4）**：Skill 工具回傳的是 session 啟動時的快取文字，其「強制產出」仍寫 `docs/03_testing/SCG4-REVIEW-…` 與 `docs/03_testing/RTM-…`；磁碟上的 `AISDLC_SDD/.claude/skills/sdd-review/SKILL.md` 與 v0.30 副本已依 D-116-09 改為 `docs/06_quality/`。本審查一律以磁碟與 D-116-09 為準；新開的 session 會讀到新版。

### §1.5 FSM 狀態檔引文（三鍵最終狀態；`show --must-exist` 逐字取值，decision_trace 末 8 筆；每筆為 `ts｜from -> to｜trigger｜reason`）

**`agentconsole-fsm-trail`（DF-B）— 通過，已到 RELEASE_READY**

```text
show --must-exist rc=0
current_state: RELEASE_READY
project: agentconsole-fsm-trail    updated_at: 2026-10-18T06:05:28+00:00
frozen_stages: 2 筆
  [0] stage=Stage-1 approved_by=掌舵者代理（主控） frozen_at=2026-10-18T02:35:20+00:00
      docs/01_requirements/Agent_ConsoleUI_PRD.md = sha256:1629cc2a67ba3e2b8df569c3349da89b8c8804b796744bf3b0df8fd3990d246c
      AgentConsole/docs/02_architecture/Architecture.md = sha256:ffc13220a4d8a11008f6178087b237c5a1b3b2ddf95da63deb40e26b526c3cd3
      AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md = sha256:ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38
      AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md = sha256:d67e450b48f9ace170ec5873c81bca74d915ac1bd15ab496cbbfdea8efffbf36
      AgentConsole/docs/02_architecture/API_Contract_P3-6.md = sha256:42db0d8ecad61b2fe50d59caaff3a12bebe3d551eb09d6c7868cd7d567bf82d2
      AgentConsole/docs/02_architecture/openapi-p3-6.yaml = sha256:e51d8c298fbe46d668ee2f6b6e38f6ef832e20ce4b0e71505ed8e5e4253ca141
  [1] stage=Stage-2 approved_by=掌舵者代理（主控） frozen_at=2026-10-18T03:48:38+00:00
      AgentConsole/docs/03_testing/contracts/TCS-FsmTrail-20261018.md = sha256:409b2c5e32f24a7ea93adc0b88da31c9d1dd3757866bd22d9f8750140f58e8e1
decision_trace: 共 17 筆；最後 8 筆（逐字）：
  [9] 2026-10-18T03:18:51+00:00 | HUMAN_PENDING -> SPEC_REGRESSION_CHECK | trigger=cli_manual | reason=QA 凍結前預審 agreed 附 M-B1（契約「原樣」敘述的語意偏離要誠實登記為已知邊界 3）＋採納 trigger 第三條件；退回 SPEC_REGRESSION_CHECK 由 SA 修訂後重核
  [10] 2026-10-18T03:45:39+00:00 | SPEC_REGRESSION_CHECK -> HUMAN_PENDING | trigger=cli_manual | reason=SPEC_REGRESSION_CHECK 完成：QA 預審 M-B1 修訂，check_tcs 重核 OK
  [11] 2026-10-18T03:48:38+00:00 | HUMAN_PENDING -> SPEC_FROZEN | trigger=spec_frozen | reason=掌舵者代理核准凍結 Stage-2：FRD-lite＋TCS（AgentConsole/docs/03_testing/contracts/TCS-FsmTrail-20261018.md）已由 SA 走完 SCG-0～3（增量條款；追溯表 22 列摘要與 Stage-1 逐字一致）、QA 凍結前預審 agreed；授權依據：掌舵者 2026-10-18 T1 原文「我授權幫我決策」；D-116-15
  [12] 2026-10-18T03:48:38+00:00 | SPEC_FROZEN -> TEST_CONTRACT_NEGOTIATED | trigger=test_contract_enter | reason=R-9.20.2 談判閘：TCS 為 oracle；QA 凍結前預審 agreed
  [13] 2026-10-18T03:48:38+00:00 | TEST_CONTRACT_NEGOTIATED -> IMPLEMENTATION | trigger=test_contract_exit | reason=Dev／QA 對 oracle 達成共識：QA 預審 agreed，實作者（headless Sonnet）只拿 TCS 本身
  [14] 2026-10-18T05:51:55+00:00 | IMPLEMENTATION -> PR_REVIEW | trigger=cli_manual | reason=SCG-4 PR 審查開始
  [15] 2026-10-18T06:05:17+00:00 | PR_REVIEW -> RTM_VERIFY | trigger=gate_pass | reason=PR_REVIEW PASS
  [16] 2026-10-18T06:05:28+00:00 | RTM_VERIFY -> RELEASE_READY | trigger=gate_pass | reason=RTM_VERIFY PASS
escalation_history: 0 筆
```

**`autoclaude-webhook`（DF-A）— 一審 FAIL，退回 IMPLEMENTATION（`PR_REVIEW` retry_count＝1）**

```text
show --must-exist rc=0
current_state: IMPLEMENTATION
project: autoclaude-webhook    updated_at: 2026-10-18T06:05:28+00:00
frozen_stages: 2 筆
  [0] stage=Stage-1 approved_by=掌舵者代理（主控） frozen_at=2026-10-18T02:35:20+00:00
      CLAUDE.md = sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41
      docs/02_architecture/SRD_AGT_Phase1_Memory.md = sha256:7b13674e2c29d22f1442e4e3650284765badeb419820513cf7cb010ca670cc2a
      docs/02_architecture/SRD_AGT_Phase2_Closedloop.md = sha256:d69ecf6eaec3fd348e78ab1102e4f573cb47caacc81e7e5f7041bf0c70b8be4e
      docs/02_architecture/SRD_AGT_Phase3_Autonomy.md = sha256:1916b5a972717fe1b40cb82189b8c10720b93b734f885ad93892ae48dab84571
  [1] stage=Stage-2 approved_by=掌舵者代理（主控） frozen_at=2026-10-18T03:48:38+00:00
      docs/03_testing/contracts/TCS-WebhookSender-20261018.md = sha256:2d473454d33d46fa341566a6f4cea25d135ce3a7a22dd0acce1d41f1bfcec8cf
decision_trace: 共 20 筆；最後 8 筆（逐字）：
  [12] 2026-10-18T04:03:41+00:00 | SPEC_FROZEN -> TEST_CONTRACT_NEGOTIATED | trigger=test_contract_enter | reason=console-signoff approver=掌舵者代理（主控）; run=f5446f48-1eb5-4400-ad98-a2b9e314b2d6
  [13] 2026-10-18T04:03:42+00:00 | TEST_CONTRACT_NEGOTIATED -> IMPLEMENTATION | trigger=test_contract_exit | reason=console-signoff approver=掌舵者代理（主控）; oracle=docs/03_testing/contracts/TCS-WebhookSender-20261018.md@sha256:2d473454d33d46fa341566a6f4cea25d135ce3a7a22dd0acce1d41f1bfcec8cf; basis=import-draft-signoff; r9.20.3=not-satisfied
  [14] 2026-10-18T04:03:42+00:00 | IMPLEMENTATION -> AUTOCLAUDE_DELEGATED | trigger=autoclaude_delegated_enter | reason=console-run run=f5446f48-1eb5-4400-ad98-a2b9e314b2d6 START
  [15] 2026-10-18T05:04:42+00:00 | AUTOCLAUDE_DELEGATED -> IMPLEMENTATION | trigger=autoclaude_delegated_exit | reason=console-run run=f5446f48-1eb5-4400-ad98-a2b9e314b2d6 RECLAIMED old_status=FAILED by=4e6bd6c9-5655-4aec-9294-a6674ead055a
  [16] 2026-10-18T05:04:42+00:00 | IMPLEMENTATION -> AUTOCLAUDE_DELEGATED | trigger=autoclaude_delegated_enter | reason=console-run run=4e6bd6c9-5655-4aec-9294-a6674ead055a START
  [17] 2026-10-18T05:13:21+00:00 | AUTOCLAUDE_DELEGATED -> IMPLEMENTATION | trigger=autoclaude_delegated_exit | reason=console-run run=4e6bd6c9-5655-4aec-9294-a6674ead055a COMPLETED
  [18] 2026-10-18T05:51:55+00:00 | IMPLEMENTATION -> PR_REVIEW | trigger=cli_manual | reason=SCG-4 PR 審查開始
  [19] 2026-10-18T06:05:28+00:00 | PR_REVIEW -> IMPLEMENTATION | trigger=gate_fail | reason=PR_REVIEW FAIL (retry 1) — SCG-4 FAIL：測試強度 F-01（P2）——50 個突變中 R 條文導出的 10 個存活（P01 四階段逾時、P02a／P02b 驗證順序、P03 終局 WARNING 缺 attempts、P04 時間戳 UTC、P05 先寫 alert log 再呼叫、P06 int 型 timeout_s、P07 欄位順序、P08 invalid_payload 日誌帶 payload、P09 invalid_argument 日誌帶 URL）；修法限 tests/utils/test_webhook_sender.py 追加斷言；F-05（P3）模組 docstring 改字；詳 AutoClaude/docs/06_quality/SCG4-REVIEW-WebhookSender-20261018.md
autoclaude_delegated_tracking: {"entered_at": "2026-10-18T05:04:42+00:00", "resume_state": "IMPLEMENTATION", "playbook_ref": "run:4e6bd6c9-5655-4aec-9294-a6674ead055a"}
escalation_history: 0 筆
```

**`monorepo-sdd-env`（DF-C）— 一審 FAIL，退回 IMPLEMENTATION（`PR_REVIEW` retry_count＝1）**

```text
show --must-exist rc=0
current_state: IMPLEMENTATION
project: monorepo-sdd-env    updated_at: 2026-10-18T06:05:28+00:00
frozen_stages: 2 筆
  [0] stage=Stage-1 approved_by=掌舵者代理（主控） frozen_at=2026-10-18T02:35:21+00:00
      CLAUDE.md = sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1
      docs/04_planning/AutoSDD_Iteration_Prompt_Template.md = sha256:02f6e22631be375d045da7ac4700abcb3d6c23fd33169522be90f4eb7944ae95
  [1] stage=Stage-2 approved_by=掌舵者代理（主控） frozen_at=2026-10-18T03:48:38+00:00
      docs/03_testing/contracts/TCS-SddEnv-20261018.md = sha256:cc0988beef137f6fa3222513f176afb8890bd53d9af6b1b7fec689258c820d5a
decision_trace: 共 16 筆；最後 8 筆（逐字）：
  [8] 2026-10-18T02:44:31+00:00 | SCG_VALIDATION -> HUMAN_PENDING | trigger=gate_pass | reason=SCG_VALIDATION PASS
  [9] 2026-10-18T03:18:51+00:00 | HUMAN_PENDING -> SPEC_REGRESSION_CHECK | trigger=cli_manual | reason=QA 凍結前預審 underspecified（M-C1：相對 --root 的 abspath 鑑別）；退回 SPEC_REGRESSION_CHECK 由 SA 修訂後重核
  [10] 2026-10-18T03:45:40+00:00 | SPEC_REGRESSION_CHECK -> HUMAN_PENDING | trigger=cli_manual | reason=SPEC_REGRESSION_CHECK 完成：QA 預審 M-C1 修訂，check_tcs 重核 OK
  [11] 2026-10-18T03:48:38+00:00 | HUMAN_PENDING -> SPEC_FROZEN | trigger=spec_frozen | reason=掌舵者代理核准凍結 Stage-2：FRD-lite＋TCS（docs/03_testing/contracts/TCS-SddEnv-20261018.md）已由 SA 走完 SCG-0～3（增量條款；追溯表 22 列摘要與 Stage-1 逐字一致）、QA 凍結前預審 agreed；授權依據：掌舵者 2026-10-18 T1 原文「我授權幫我決策」；D-116-15
  [12] 2026-10-18T03:48:38+00:00 | SPEC_FROZEN -> TEST_CONTRACT_NEGOTIATED | trigger=test_contract_enter | reason=R-9.20.2 談判閘：TCS 為 oracle；QA 凍結前預審 agreed
  [13] 2026-10-18T03:48:38+00:00 | TEST_CONTRACT_NEGOTIATED -> IMPLEMENTATION | trigger=test_contract_exit | reason=Dev／QA 對 oracle 達成共識：QA 預審 agreed，實作者（headless Sonnet）只拿 TCS 本身
  [14] 2026-10-18T05:51:55+00:00 | IMPLEMENTATION -> PR_REVIEW | trigger=cli_manual | reason=SCG-4 PR 審查開始
  [15] 2026-10-18T06:05:28+00:00 | PR_REVIEW -> IMPLEMENTATION | trigger=gate_fail | reason=PR_REVIEW FAIL (retry 1) — SCG-4 FAIL：測試強度 F-02（P2）——29 個突變中 CP1（拿掉 force_utf8_stdio）與 CP2（長度檢查先於格式檢查）存活；F-03（P3）Windows 上 --shell bash 輸出為 CRLF；詳 docs/06_quality/SCG4-REVIEW-SddEnv-20261018.md
escalation_history: 0 筆
```

各鍵 `gate` 的指令輸出（當回合）：DF-B `PR_REVIEW PASS` → `{"gate": "PR_REVIEW", "result": "PASS", "next_state": "RTM_VERIFY"}`；`RTM_VERIFY PASS` → `{"gate": "RTM_VERIFY", "result": "PASS", "next_state": "RELEASE_READY"}`；DF-A、DF-C `PR_REVIEW FAIL` → `{"gate": "PR_REVIEW", "result": "FAIL", "retry_count": 1, "next_state": "IMPLEMENTATION"}`。`PR_REVIEW` 預算上限 5 次、同模式 3 次進 SPEC_AUDIT：兩鍵都只用了 1 次。

## §2 SCG-4 審查表（三路；Code vs TCS vs AC）

> 三份報告（各 ≤120 行，結構依 `AISDLC_SDD:sdd-review`）：[DF-A](../../AutoClaude/docs/06_quality/SCG4-REVIEW-WebhookSender-20261018.md)、[DF-B](../../AgentConsole/docs/06_quality/SCG4-REVIEW-FsmTrail-20261018.md)、[DF-C](SCG4-REVIEW-SddEnv-20261018.md)。本節是逐 AT 與逐突變的明細。
> **存活突變的分級口徑**：任務書規定「每個突變必須讓至少一個 AT 轉紅，否則記 P2『oracle 無鑑別力』」。核心突變（任務書建議與 TCS 的 Then 直接要求）一律全數被殺；存活的 12 個全是我另外由 TCS 的 **R 條文／Given** 導出的探針——該條文明文要求、行為可由公開 API 或日誌觀察、且不需真睡眠或真網路，但對應 AT 的 Then 沒有逐項斷言。測試忠於 TCS 的 Then，缺口在「R 條文強於 Then」（TCS 層）與「測試只做到 Then」（測試層）兩處。照任務書字面一律記 P2（F-01、F-02）；修法只是在既有測試函式追加斷言，不需改 TCS（TCS 已凍結）。

### §2.1 DF-A WebhookSender（AutoClaude）

**逐 AT 對照 Gherkin 的 Then**（測試檔 `AutoClaude/tests/utils/test_webhook_sender.py`）：

| AT | 測試座標 | Then 逐項 | 測試是否逐項斷言 | 結論 |
|----|---------|-----------|------------------|------|
| AT-001-1-1 | `:23-62` | 200／201／204 各回 `WebhookResult(True, 碼, 1, None)`；handler 恰一次；POST、URL、JSON 本文、content-type；`timeout_s=2.5` 的 `read` 為 2.5；結果 frozen | 全部逐項（`:38-44`、`:58`、`:61-62`） | 忠於；R4 四階段只斷言 `read`（P01）、無 int 型 `timeout_s` 正例（P06）、欄位順序無斷言（P07） |
| AT-001-2-1 | `:65-93` | 12 個壞位址各回 `(False, None, 0, "invalid_url")`；handler 零呼叫；無例外 | 全部（`:74-93`；含 `https://[::1`） | 忠於 |
| AT-001-3-1 | `:96-129` | 503、503、200 → 3 次與 `[0.5, 1.0]`；ConnectError 後 200 → 2 次與 `[0.5]` | 全部 | 忠於 |
| AT-001-3-2 | `:132-194` | 五情境（永遠 503、永遠 ReadTimeout、永遠 500 且 `max_attempts=7`、503→ConnectError→502、502→503→ReadTimeout）的結果、次數與 `sleeps` | 全部，含 `[0.5, 1.0, 2.0, 4.0, 8.0, 8.0]` 與「終局不殘留前次值」 | 忠於 |
| AT-001-3-E-1 | `:197-240` | 帶 Location 的 302、400、401、404、429 各 1 次；302 只有原主機收到；503＋`max_attempts=1` 1 次；`sleeps` 恆空 | 全部（`:226-240`） | 忠於 |
| AT-001-4-E-1 | `:243-316` | RuntimeError 不重試；六種壞 payload→`invalid_payload`；十種壞參數→`invalid_argument`；`_Stop(BaseException)` 原樣傳播 | 全部 | 忠於；Given 宣稱的驗證順序 R1→R2→R3 沒有任何組合案例（P02a／P02b） |
| AT-001-5-1 | `:319-416` | 四次呼叫的 DEBUG／WARNING 筆數與內容、七個標記字串不得出現在日誌與 `error` | 全部（`:350-354`、`:368-371`、`:390-394`、`:407-411`、`:414-416`） | 忠於；終局 WARNING 無 `attempts` 斷言（P03）、第四次 payload 不含標記（P08）、R3 失敗路徑零日誌斷言（P09） |
| AT-001-6-1 | `:419-472` | 每輪 `send_webhook` 恰一次、位置參數 `(url, payload)`、kwargs 空；payload 恰四鍵與值；`timestamp` 可解析且帶時區；含 `Webhook` 的日誌恰一筆與等級、片段；無「尚未實作」與 URL；alert log 仍寫入 | 全部 | 忠於；`timestamp` 只斷言帶時區、不斷言 UTC（P04）；不斷言「先寫 alert log 再呼叫」（P05） |
| AT-001-6-2 | `:475-503` | `None` 與 `""` 各一次，`send_webhook` 零呼叫、無 `Webhook` 日誌；alert log 恰兩行、行尾與 naive 時間戳 | 全部 | 忠於 |

**R 條文 × 殺死它的突變**（`mut_dfa`）：R1＝A12、A21、A27、A29；R2＝A13；R3＝A10、A10b、A25（順序 P02a／P02b、int 型 P06 存活）；R4＝A01、A06、A32（四階段 P01 存活）；R5＝A02、A11、A20、A26、A31；R6＝A07、A08、A09、A22、A24；R7＝A07、A09；R8＝A11、A12；R9＝A03、A04、A05、A14、A28、A30（P03、P08、P09 存活）；R10＝N01、N02、N06、N12、N13（P04、P05 存活）；R11＝N03、N07、N08、N10、N11；R12＝N04、N05。

| ID | 突變（記憶體內改寫） | 結果 | 轉紅的 AT |
|----|----|----|----|
| A01（核心） | follow_redirects=False -> True（跟隨重導） | 被殺 | AT-001-3-E-1 |
| A02（核心） | 4xx 也重試（retryable = status >= 400） | 被殺 | AT-001-3-E-1 |
| A03（核心） | 終局 WARNING 記原始 URL | 被殺 | AT-001-5-1 |
| A04（核心） | DEBUG 日誌記原始 URL | 被殺 | AT-001-5-1 |
| A05（核心） | invalid_url 驗證失敗的 WARNING 帶原始 URL | 被殺 | AT-001-5-1 |
| A06（核心） | 忽略 timeout_s（固定 5.0） | 被殺 | AT-001-1-1 |
| A07（核心） | 網路錯誤分支不重設 status（殘留較早嘗試的 status） | 被殺 | AT-001-3-2 |
| A08（核心） | 退避不封頂 8 秒 | 被殺 | AT-001-3-2 |
| A09（核心） | 嘗試次數差一（attempts > max_attempts） | 被殺 | AT-001-3-2、AT-001-3-E-1、AT-001-5-1 |
| A10（核心） | max_attempts 接受 bool | 被殺 | AT-001-4-E-1 |
| A10b（核心） | timeout_s 接受 bool | 被殺 | AT-001-4-E-1 |
| A11（核心） | 攔截 BaseException | 被殺 | AT-001-4-E-1 |
| A12（核心） | 位址解析不包 ValueError | 被殺 | AT-001-2-1 |
| A13（核心） | payload 序列化允許 NaN（拿掉 allow_nan=False） | 被殺 | AT-001-4-E-1 |
| A14（核心） | DEBUG 日誌記 payload 內容 | 被殺 | AT-001-5-1 |
| A20（核心） | 只認 200 為成功 | 被殺 | AT-001-1-1 |
| A21（核心） | http 也放行 | 被殺 | AT-001-2-1、AT-001-5-1 |
| A22（核心） | 最後一次嘗試之後仍睡眠 | 被殺 | AT-001-3-2、AT-001-3-E-1 |
| A23（核心） | HTTP 失敗的 error 不叫 http_<碼> | 被殺 | AT-001-3-2、AT-001-3-E-1、AT-001-5-1 |
| A24（核心） | max_attempts 預設 3 -> 4 | 被殺 | AT-001-3-2、AT-001-5-1 |
| A25（核心） | timeout_s 邊界 > 0 改 >= 0 | 被殺 | AT-001-4-E-1 |
| A26（核心） | 只有 ConnectError 可重試（ReadTimeout 不重試） | 被殺 | AT-001-3-2 |
| A27（核心） | 位址不驗 hostname | 被殺 | AT-001-2-1 |
| A28（核心） | 遮罩後 URL 保留 netloc（含 userinfo 與 port） | 被殺 | AT-001-5-1 |
| A29（核心） | invalid_url 的 attempts 回 1 | 被殺 | AT-001-2-1、AT-001-5-1 |
| A30（核心） | 成功路徑多記一筆 INFO | 被殺 | AT-001-5-1 |
| A31（核心） | transport 錯誤的 error 改用例外訊息（非類別名稱） | 被殺 | AT-001-3-2 |
| A32（核心） | 不傳 json 本文（只 POST） | 被殺 | AT-001-1-1 |
| N01（核心） | 以關鍵字參數呼叫 send_webhook | 被殺 | AT-001-6-1 |
| N02（核心） | payload timestamp 改 naive 本地時間 | 被殺 | AT-001-6-1 |
| N03（核心） | notifier 的 INFO 日誌帶 webhook URL | 被殺 | AT-001-6-1 |
| N04（核心） | 空字串位址也發送（is not None） | 被殺 | AT-001-6-2 |
| N05（核心） | alert log 時間戳改帶時區 | 被殺 | AT-001-6-2 |
| N06（核心） | payload 缺 dump_path 鍵 | 被殺 | AT-001-6-1 |
| N07（核心） | 成功改記 WARNING | 被殺 | AT-001-6-1 |
| N08（核心） | 失敗 WARNING 缺 attempts | 被殺 | AT-001-6-1 |
| N10（核心） | 殘留舊的「尚未實作」警告（含 URL） | 被殺 | AT-001-6-1 |
| N11（核心） | notifier 的失敗 WARNING 帶 webhook URL | 被殺 | AT-001-6-1 |
| N12（核心） | payload 多一個鍵 | 被殺 | AT-001-6-1 |
| N13（核心） | payload 的 title 與 message 對調 | 被殺 | AT-001-6-1 |
| P01（探針） | R4：逾時只套 read，其餘三階段固定 5.0 | **存活** | （無） |
| P02a（探針） | R1→R2→R3 驗證順序：payload 先於位址 | **存活** | （無） |
| P02b（探針） | R1→R2→R3 驗證順序：參數先於 payload | **存活** | （無） |
| P03（探針） | R9：終局 WARNING 不含 attempts | **存活** | （無） |
| P04（探針） | R10：payload timestamp 用帶本地偏移（非 UTC） | **存活** | （無） |
| P05（探針） | R10：webhook 呼叫移到寫 escalation_alert.log 之前 | **存活** | （無） |
| P06（探針） | R3：timeout_s 只收 float（int 被拒） | **存活** | （無） |
| P07（探針） | WebhookResult 欄位順序（Given：ok、status、attempts、error） | **存活** | （無） |
| P08（探針） | R9：invalid_payload 的 WARNING 帶 payload 內容 | **存活** | （無） |
| P09（探針） | R9：invalid_argument 的 WARNING 帶原始 URL | **存活** | （無） |

小計：50 個突變，被殺 40、存活 10。

**NFR 逐項（當回合）**：NFR-001-1 只 import 標準庫與 httpx（`webhook_sender.py:11-17`），lint-imports 9 kept、0 broken；-2 模組 135 行、`check_loc_budget` rc 0；-3 整檔單跑 1.80 秒（< 5 秒）；-4 測試無 `httpx.get`／`post`／socket／`time.sleep`（grep 零命中）；-5 ruff 三檔無違規；-6 測試無 skip／xfail／`sys.platform`，`read_text` 帶 `encoding="utf-8"`，無磁碟機代號路徑，含 userinfo 的假 URL 皆 example.com 子網域並帶 `secret-scan-ok`；-7 AutoClaude 全套 rc 0；-8 隔離環境量覆蓋率：`webhook_sender.py` 74 述句漏 0、22 分支部分 0（行 100%、分支 100%），R1～R12 逐條皆被 AT 觸及；-9 引擎評估環境於請求層 `env` 帶 `AUTOCLAUDE_NO_PG_AUTODETECT=1`，九步評估各 rc 0；-10 恰三檔，樹下限 241→242 由主控於 `d9dc1ff0` 重釘（`int(303×0.8)＝242`）。

### §2.2 DF-B FsmTrail（AgentConsole）

**逐 AT 對照 Gherkin 的 Then**（測試檔 `AgentConsole/engine-bridge/tests/test_fsm_trail.py`）：

| AT | 測試座標 | Then 逐項 | 測試是否逐項斷言 | 結論 |
|----|---------|-----------|------------------|------|
| AT-001-1-1 | `:25-47` | 回傳 list 且 `is not trace`、長度 2；`result[0] is trace[0]` 且無 `from_inferred`；`result[1]` 新 dict、`from` 還原、`from_inferred is True`、`to` 不變、其餘五鍵逐值相等；呼叫後輸入與快照相等 | 全部（`is True` 以 `is` 斷言） | 忠於 |
| AT-001-2-1 | `:50-82` | 十筆混合只有 `[3]` 被改、其餘為同一物件且無 `from_inferred`；`trace2` 三筆雙命中 | 全部 | 忠於 |
| AT-001-3-1 | `:85-97` | 八種不合格 provenance，筆本身三條件合格，一筆不改、新 list、同一元素物件 | 全部 | 忠於 |
| AT-001-4-1 | `:100-107` | None／42／abc／dict／tuple／set 回同一物件；dict 與 tuple 內容不變 | 全部 | 忠於 |
| AT-001-4-2 | `:110-129` | 十個不良元素與一個好元素：長度 11、前十筆同一物件、第十一筆被改寫 | 全部 | 忠於 |
| AT-001-5-1 | `:141-176` | HTTP 200、`decision_trace` 恰 5 筆（t3～t7）、前 4 筆逐值相等且無 `from_inferred`、最後一筆還原；`current_state`、`escalation_provenance`、`fsm_project`、`phase.name==BLOCKED`；檔案位元組不變；直接呼叫 `_state_view` 逐值相等 | 全部 | 忠於 |
| AT-001-5-2 | `:179-204` | 四個檔（other_source、無 provenance、殘留 provenance＋`retry_exhausted` 自迴圈、IMPLEMENTATION 態）皆 200、`decision_trace` 等於檔內尾 5 筆、無 `from_inferred`、`alpha`／`beta`／`delta` 最後一筆 `from` 仍是 ESCALATION | 全部 | 忠於 |

**R 條文**：R1＝B12；R2＝B03、B04、BP2；R3＝B01、B02、B09、B10、B11；R4＝B05、B07、B15；R5＝B16、B19；R6＝B08、BP1；R7（純度、不 import `app.*`）為靜態項，`fsm_trail.py` 只有 `from __future__`、`from typing import Any`，無 I/O（人工讀碼）；R8＝B06、B13、B20；R9（`:freeze` 共用 `_state_view`）由 AT-001-5-1 的直接呼叫涵蓋，且 `GET` 路徑被 B06 等打紅。

| ID | 突變（記憶體內改寫） | 結果 | 轉紅的 AT |
|----|----|----|----|
| B01（核心） | R3②：拿掉 trigger 條件 | 被殺 | AT-001-2-1、AT-001-5-2 |
| B02（核心） | R3③：拿掉 provenance 閘 | 被殺 | AT-001-3-1、AT-001-5-2 |
| B03（核心） | R2：沒有改寫時回傳同一個 list | 被殺 | AT-001-3-1 |
| B04（核心） | R2：就地改動輸入元素 | 被殺 | AT-001-1-1、AT-001-2-1、AT-001-4-2 |
| B05（核心） | R4：改寫時多動 to 欄 | 被殺 | AT-001-1-1、AT-001-4-2、AT-001-5-1 |
| B06（核心） | R8：接線不經 restore_trail（原樣尾 5 筆） | 被殺 | AT-001-5-1 |
| B07（核心） | R4：from_inferred 用 1 而非 True | 被殺 | AT-001-1-1、AT-001-2-1、AT-001-4-2、AT-001-5-1 |
| B08（核心） | R6：元素不先驗 dict（非 dict 元素會拋例外） | 被殺 | AT-001-4-2 |
| B09（核心） | R3③：source 只要有值就放行 | 被殺 | AT-001-3-1、AT-001-5-2 |
| B10（核心） | R3：from／to 比對不分大小寫 | 被殺 | AT-001-2-1 |
| B11（核心） | R3①：只看 from、不看 to | 被殺 | AT-001-2-1、AT-001-4-2 |
| B12（核心） | R1：tuple／set 被轉成 list | 被殺 | AT-001-4-1 |
| B13（核心） | R8：接線把 provenance 傳成 None | 被殺 | AT-001-5-1 |
| B15（核心） | R4：還原值字串錯一個字 | 被殺 | AT-001-1-1、AT-001-2-1、AT-001-4-2、AT-001-5-1 |
| B16（核心） | R5：不符元素被複製成新 dict（不是同一個物件） | 被殺 | AT-001-1-1、AT-001-2-1、AT-001-3-1、AT-001-4-2 |
| B19（核心） | R5：不符元素被加上 from_inferred: False | 被殺 | AT-001-1-1、AT-001-2-1、AT-001-3-1、AT-001-4-2、AT-001-5-1、AT-001-5-2 |
| B20（核心） | R8：視窗由尾 5 筆改尾 4 筆 | 被殺 | AT-001-5-1、AT-001-5-2 |
| BP1（探針） | R6：provenance 為 list 時改拋例外（任何輸入都不拋） | 被殺 | AT-001-3-1 |
| BP2（探針） | R2：結果是新 list 但元素順序反轉 | 被殺 | AT-001-2-1、AT-001-4-2、AT-001-5-1、AT-001-5-2 |

小計：19 個突變，被殺 19、存活 0。

**NFR 逐項（當回合）**：-1 零 import 與無 I/O；-2 1000 次呼叫中位 0.70 微秒、P99 0.80 微秒、最大 2.10 微秒（限 1000 微秒）；-3 `tests/test_sdd_fsm.py` 鍵集合斷言在全套中續綠，OpenAPI 形狀不變；-4 engine-bridge 全套 rc 0，24 個略過逐筆為環境因素（7 個 symlink 權限、17 個未設 `BRIDGE_TEST_DSN`），零筆來自 `test_fsm_trail.py`；-5 ruff 兩視角皆無違規；-6 無 `FSM-STATE` 字串，`tests/test_sdd_integration_parity.py` 的 F-4 AST 鎖續綠；-7 無檔案 I/O、無時間戳；-8 `git show --stat 4c327ea0` 恰三檔。R8 接線 diff：`sdd.py:28` 一行 import（在 `fsm_phase` 與 `models` 之間）、`:187-188` 一個運算式，其餘一字未動。

### §2.3 DF-C SddEnv（根層）

**逐 AT 對照 Gherkin 的 Then**（測試檔 `AISDLC_SDD/scripts/tests/test_sdd_env.py`）：

| AT | 測試座標 | Then 逐項 | 測試是否逐項斷言 | 結論 |
|----|---------|-----------|------------------|------|
| AT-001-1-1 | `:38-56` | 預設根與預設 json：兩次 rc 0、stdout 相同；單一 JSON、鍵序、值皆字串；`SDD_PROJECT`、旗標；`SDD_STATE_DIR` 逐段與絕對；`SDD_ACTIVE_VERSION` 等於 `latest_version_name` 去前綴且符合 `\d+\.\d+` | 全部 | 忠於 |
| AT-001-1-2 | `:59-81`、`:84-110` | 四個 sub 的狀態目錄查表、`0.10` 勝 `0.9`、目錄樹前後相同；相對根與尾端分隔符、非 ASCII 根原樣輸出 | 全部（參數化 4 個＋另一函式） | 忠於 |
| AT-001-2-1 | `:117-135` | powershell 五行、行首、值以單引號包住、第 3 行單引號雙寫還原後等於預期路徑 | 全部 | 忠於 |
| AT-001-2-2 | `:138-156` | bash 五行、`'\''` 跳脫還原 | 全部 | 忠於 |
| AT-001-3-1 | `:159-176` | 九個壞值 rc 2、stdout 空、stderr 含「格式」；31 字 rc 2、stderr 含 30 | 全部（9 個參數＋獨立函式） | 忠於；「格式先於長度」的檢查順序沒有組合案例（CP2） |
| AT-001-3-2 | `:178-191` | 保留字三種大小寫 rc 2 且含「保留字」；30 字、單字元、`a-b-c-1` rc 0 | 全部 | 忠於 |
| AT-001-4-1 | `:194-211` | rc 0、單行 `OK <絕對路徑>`、無環境區塊、目錄樹與檔案內容不變 | 全部 | 忠於 |
| AT-001-4-2 | `:214-235` | 兩種缺法 rc 5、stdout 空、stderr 含 `state_not_found` 與預期路徑、目錄樹不變（不得建出 `AgentConsole`／`build`） | 全部 | 忠於 |
| AT-001-5-1 | `:238-276` | 版本不可解 rc 1；root 非目錄 rc 2（兩種）；用法錯誤 rc 2（三種）；成功呼叫不改 `os.environ`、目錄樹不變；`--help` rc 0 | 全部 | 忠於；Given 要求的 R1（stdio 重設為 UTF-8）無斷言（CP1） |

**R 條文**：R1＝C21（rc）、CP1 存活（stdio 重設）；R2＝C12、C15；R3＝C24、C25；R4＝C01、C14、C18；R5＝C08、C19；R6＝C06、C07、C13、C26；R7＝C02、C04、C05、C16、C17（CP2 存活）；R8＝C03、C10、C11、C22、CP3；R9＝C09；R10＝C27、C28。

| ID | 突變（記憶體內改寫） | 結果 | 轉紅的 AT |
|----|----|----|----|
| C01（核心） | R4：--root 不轉絕對路徑 | 被殺 | AT-001-1-2 |
| C02（核心） | R7：slug 長度上限放寬到 31 | 被殺 | AT-001-3-1 |
| C03（核心） | R8：--check 缺檔時建立狀態目錄 | 被殺 | AT-001-4-2 |
| C04（核心） | R7：保留字比對區分大小寫 | 被殺 | AT-001-3-2 |
| C05（核心） | R7：格式檢查先於保留字 | 被殺 | AT-001-3-2 |
| C06（核心） | R6：powershell 不雙寫單引號 | 被殺 | AT-001-2-1 |
| C07（核心） | R6：bash 不跳脫單引號 | 被殺 | AT-001-2-2 |
| C08（核心） | R5：版本以字串排序（0.9 > 0.10） | 被殺 | AT-001-1-2 |
| C09（核心） | R9：成功時寫入 os.environ | 被殺 | AT-001-5-1 |
| C10（核心） | R1：--check 缺檔回 rc 1（非 5） | 被殺 | AT-001-4-2 |
| C11（核心） | R8：--check 不看檔案是否存在（永遠 OK） | 被殺 | AT-001-4-2 |
| C12（核心） | R2：遙測旗標值 1 | 被殺 | AT-001-1-1、AT-001-2-1、AT-001-2-2 |
| C13（核心） | R6：json 形態逸出非 ASCII（ensure_ascii 預設） | 被殺 | AT-001-1-2 |
| C14（核心） | R4：預設根取 parents[1] | 被殺 | AT-001-1-1 |
| C15（核心） | R2：輸出變數順序對調（PROJECT／STATE_DIR） | 被殺 | AT-001-1-1、AT-001-2-1、AT-001-2-2 |
| C16（核心） | R7：slug 格式放行底線 | 被殺 | AT-001-3-1 |
| C17（核心） | R7：恰 30 字也被拒（>= 30） | 被殺 | AT-001-3-2 |
| C18（核心） | R4：不驗 root 是目錄 | 被殺 | AT-001-5-1 |
| C19（核心） | R5：版本不可解時不早退 | 被殺 | AT-001-5-1 |
| C21（核心） | R1：用法錯誤 rc 回 1（非 2） | 被殺 | AT-001-5-1 |
| C22（核心） | R8：--check 狀態檔名用 slug（非 <sub>-<slug>） | 被殺 | AT-001-4-1、AT-001-4-2 |
| C24（核心） | R3：sdd 的狀態目錄名 sdd-dogfood -> sdd_dogfood | 被殺 | AT-001-1-2 |
| C25（核心） | R3：AutoClaude 目錄名大小寫 | 被殺 | AT-001-1-2、AT-001-2-1、AT-001-4-1 |
| C26（核心） | R6：--shell 預設改 powershell（非 json） | 被殺 | AT-001-1-1 |
| C27（核心） | R10：成功時 stdout 多印一行說明 | 被殺 | AT-001-1-1、AT-001-1-2、AT-001-2-1、AT-001-2-2、AT-001-3-2 |
| C28（核心） | R10：slug 驗證診斷改印 stdout（非 stderr） | 被殺 | AT-001-3-1、AT-001-3-2 |
| CP1（探針） | R1：不重設 stdout／stderr 為 UTF-8（拿掉 force_utf8_stdio） | **存活** | （無） |
| CP2（探針） | R7：長度檢查先於格式檢查 | **存活** | （無） |
| CP3（探針） | R8：--check 的 OK 行不含絕對路徑 | 被殺 | AT-001-4-1 |

小計：29 個突變，被殺 27、存活 2。

**NFR 逐項（當回合）**：-1 無 `subprocess`、無檔案 I/O、無時間戳（grep 零命中，`environ` 只在 docstring）；-2 `main()` 10 次含真實 git 解析，最大 0.049 秒（限 2 秒）；-3 無 `sys.platform` 分支（Windows 實跑 `--shell bash` 為 CRLF，見 F-03）；-4 測試無 skip／xfail／平台分支；-5 ruff 兩檔無違規；-6 hermetic（`tmp_path`、不讀 `SDD_` 變數、不碰真實狀態檔）；-7 `scripts/tests` 全綠、兩個新檔、樹下限 26→27 由主控於 `e73749bf` 重釘。**真跑**：`--check` 對三個 dogfood 鍵皆 rc 0 並印 `OK <絕對路徑>`，對不存在的鍵 rc 5；`--shell json`／`powershell`／`bash` 的 stdout 位元組：行尾皆 CRLF（bash 形 242 位元組含 5 個 `\r\n`、單獨 `\n` 0 個）。

## §3 閘門親跑表（當回合；起點為乾淨 HEAD `07cfa9ae`，交付文件寫入之前）

| # | 閘門 | 指令（cwd） | rc | 關鍵輸出 |
|---|------|-------------|----|----------|
| G1 | DF-A 整檔單跑 | `python -m pytest tests/utils/test_webhook_sender.py -q -p no:xdist -o addopts=`（`AutoClaude`；`AUTOCLAUDE_NO_PG_AUTODETECT=1`） | 0 | 9 支通過、1 警告、1.80 秒；`--durations=5` 重跑 1.88 秒 |
| G2 | AutoClaude 全套（**第一次，誤設逃生變數**） | `python -m pytest tests/ -q -n 8 --dist loadgroup`（`AutoClaude`；`AUTOCLAUDE_NO_PG_AUTODETECT=1`） | 1 | 1 失敗、5791 通過、104 略過；失敗者＝`tests/tools/test_local_ci_gate.py::test_conftest_is_where_the_autodetect_is_wired`（斷言 note 含 `pytest`，實得「跳過：AUTOCLAUDE_NO_PG_AUTODETECT 已設」）。環境造成，非碼缺陷（F-07） |
| G3 | AutoClaude 全套（**正確形態**：不設逃生變數，PG 位址由 conftest 注入） | 同上，不設該變數 | 0 | 5889 通過、7 略過、14 警告、46.99 秒 |
| G4 | lint-imports | `lint-imports.exe`（`AutoClaude`；`PYTHONUTF8=1`） | 0 | `Contracts: 9 kept, 0 broken.` |
| G5 | ruff 三檔 | `ruff check autoclaude/utils/webhook_sender.py autoclaude/utils/notifier.py tests/utils/test_webhook_sender.py`（`AutoClaude`） | 0 | `All checks passed!` |
| G6 | LOC 預算 | `python AutoClaude/tools/check_loc_budget.py --json`（根） | 0 | 總 18625、基線 17079、分級違規 0、絕對違規 0；新檔不在違規清單 |
| G7 | DF-B engine-bridge 全套 | `python -m pytest -q -n 4`（`AgentConsole\engine-bridge`） | 0 | 1003 通過、24 略過、5 警告、137 秒；以 `-rs` 重跑列出 24 筆理由（7 symlink、17 DSN），零筆來自 `test_fsm_trail.py` |
| G8 | DF-B ruff 兩視角 | `ruff check .`（`AgentConsole\engine-bridge`）與 `ruff check AgentConsole/engine-bridge`（根） | 0／0 | 兩次皆 `All checks passed!` |
| G9 | DF-C `scripts/tests` | `python -m pytest scripts/tests -q`（`AISDLC_SDD`） | 0 | 421 通過、1 略過（Unix chmod 分支在 Windows 不可達，既有）、31 子測試通過、76.97 秒 |
| G10 | DF-C ruff 兩檔 | `ruff check AISDLC_SDD/scripts/sdd_env.py AISDLC_SDD/scripts/tests/test_sdd_env.py`（根） | 0 | `All checks passed!` |
| G11 | `ci-gate.ps1` | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File AISDLC_SDD\scripts\ci-gate.ps1`（根） | 0 | 70.4 秒；「本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）」；逐軌計數 `AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.30:2149 scripts/tests:421`；skills SSOT 兩目標各 59 檔一致；Router hook 覆蓋 lint 綠 |
| G12 | 根層棘輪三模組 | `python -m unittest discover -s tools/tests -p <檔>`（根）：`test_platform_utils_dedup.py`、`test_platform_neutral_paths.py`、`test_subprocess_encoding_hygiene.py` | 0／0／0 | 43 項 OK／OK／39 項 OK（含 `_TREE_FILE_FLOORS` 重釘後的樹下限鎖） |
| G13 | DF-A 覆蓋率 | `python -m coverage run --branch --include=…webhook_sender.py -m pytest …`（`AutoClaude`；`PYTHONPATH` 指向 scratch 的 coverage 7.6.1） | 0 | 74 述句漏 0、22 分支部分 0、**100%**（純行覆蓋亦 100%）；根 `.venv` 無 `coverage` 套件（複驗 `Test-Path` 為 False） |
| G14 | 突變檢驗 | 記憶體內 import hook 改寫（`mutate_runner.py`／`mutate_all.py`；各突變一個全新子行程） | — | 98 個突變：被殺 86、存活 12（DF-A 50＝殺 40／活 10；DF-B 19＝殺 19／活 0；DF-C 29＝殺 27／活 2）；三個基線皆乾淨（9／7／22 全過） |
| G15 | NFR 計時 | 見 §2.2、§2.3 | 0 | DF-B P99 0.80 微秒；DF-C 最大 0.049 秒 |
| G16 | 交付文件機械自檢 | `verify_docs.py`（三份報告 ≤120 行、無任務書列的兩個禁用詞、RTM 機械列數、基線數字判準、LF、無 BOM） | 0 | 問題數 0；`AgentConsole/docs/06_quality/RTM.md` 機械列數 392、US 列 58 不變 |

**未列入的閘門**：根層 `tools/run_root_unittests.py` 全套、AutoClaude 的 `tests/contract/test_claude_md_*.py` 單獨重跑、Docker 全棧——本輪未跑（見 §8）；上表 G12 只是與本輪重釘直接相關的三個模組。

## §4 發現

審查結論：**無 P1；P2 兩筆（F-01、F-02）；P3 五筆（F-03、F-04、F-05、DEF-AC-038、F-09）；P4 四筆（G-116-17、F-06、F-07、F-08）**。F-01、F-02 必須本輪修，主控派修復棒後由我二審。

| 編號 | 嚴重度 | 歸屬／編號 | 摘要 | 處置 |
|------|:------:|-----------|------|------|
| F-01 | **P2** | AutoClaude 面（測試；請主控入 DEF-200） | DF-A 的 oracle 無鑑別力：50 個突變中 10 個存活（P01 R4 四階段逾時只斷言 `read`、P02a／P02b R1→R2→R3 驗證順序無組合案例、P03 終局 WARNING 無 `attempts` 斷言、P04 `timestamp` 不斷言 UTC、P05 不斷言先寫 alert log 再呼叫、P06 無 int 型 `timeout_s` 正例、P07 `WebhookResult` 欄位順序無斷言、P08 `invalid_payload` 路徑的日誌是否帶 payload，實際沒被檢查（第四次呼叫的 payload 不含任何標記字串）、P09 `invalid_argument` 路徑零日誌斷言）。**P09 最重**：日後有人在該路徑把 URL 寫進日誌，現有測試不會紅。P04 僅在機器時區非 UTC 時可被咬住（本機為 UTC+8；UTC 的 CI 上錯誤實作與正解同值） | 只動 `AutoClaude/tests/utils/test_webhook_sender.py` 追加斷言；逐項座標與寫法見 DF-A 報告的必修表；修復棒完成後我重跑 10 個探針須全數轉紅、整檔與全套須綠 |
| F-02 | **P2** | 根層／AISDLC_SDD 面（測試；請主控入 DEF-200） | DF-C 的 oracle 無鑑別力：29 個突變中 2 個存活（CP1 拿掉 `force_utf8_stdio()` 呼叫、CP2 長度檢查排到格式檢查之前） | 只動 `AISDLC_SDD/scripts/tests/test_sdd_env.py`：spy 斷言一次 `main()` 恰呼叫一次 stdio 重設；AT-001-3-1 參數表加 `"A" * 31`；寫法見 DF-C 報告 |
| F-03 | P3 | 根層／AISDLC_SDD 面（碼＋測試） | Windows 上 `sdd_env.py --shell bash` 輸出為 CRLF（真跑 242 位元組含 5 個 `\r\n`、單獨 `\n` 0 個）：`eval "$(… --shell bash)"` 於 Git Bash 會把 `\r` 黏進值；違反 NFR-001-3「輸出形態由 --shell 決定而不是由平台決定」與根層鐵律三的行尾項；capsys 看不到此差異 | `sdd_env.py:128` 改寫位元組（`sys.stdout.buffer.write(...encode("utf-8"))`）或 `reconfigure(newline="\n")`，並補一支子行程取原始位元組的測試；SOP 的 bash 形只供 mac／Linux，所以不是 P2 |
| F-04 | P3 | 根層（TCS 文字） | TCS 的 R1 寫行內 `reconfigure`、R9 與 NFR-001-1 寫「只用標準庫與同目錄 `sdd_version`」；實作改走 `rfc_lifecycle_lint.force_utf8_stdio()`（`e73749bf`，為過根層 `test_platform_utils_dedup` 的 shrink-only 棘輪）。行為等價 | TCS 已凍結不改；已記於 `RTM-SddEnv.md` 備註與 DF-C 報告「已知偏離」 |
| F-05 | P3 | AutoClaude 面（碼，文字） | `webhook_sender.py:1-8` 模組 docstring 寫「目前實作 AT-001-1-1 的成功路徑…」的開發進度敘述，完工後不實 | 改為用途說明；程式不動 |
| DEF-AC-038 | P3 | AgentConsole 面 | Bridge `StepTracker` 被引擎日誌遮罩漏配（§1.2）：缺 5-1 事件、4-e-1 標 attempt 2、`STEP_TRACKING_GAP`；不影響 RTM 與 FSM | 不在本輪修。修法見 §1.2；再開症狀＝Console 步驟時間軸缺步驟或把失敗記到前一步 |
| G-116-17 | P4（**暴露證據成立；建議升 P2**） | 根層守衛面（只列出；依 D-116-14 由主控 W4 處理） | 根 router 的 PreToolUse／PostToolUse matcher 不含 PowerShell：兩個真實 hooks-ON Windows 視窗（sid 與 ledger 路徑見 §1.3）各 2 次 PowerShell 呼叫 ledger 零入帳；C7 演練另證 ESCALATION 下 PowerShell 不被擋（§6 步驟 18～19，構造性探針，不計新暴露證據） | 符合根 `CLAUDE.md`〈守衛面准入〉的暴露證據條件；matcher 為受保護路徑，由主控 W4 單人窗口加，分類器拒絕則 staged 交掌舵者；修後我驗兩視窗等價場景的 ledger 出現 PowerShell 入帳 |
| F-06 | P4 | AutoClaude 面 | `context_pct_from_claude_json` 缺 `usage.iterations` 時退回累計值：若 claude 版本不輸出該欄，多回合的真實樹委派批次仍會偽 TOKEN_HALT | 再開症狀：真實樹委派批次在不帶 `usage.iterations` 的 claude 版本偽停機 |
| F-07 | P4 | AutoClaude 面（測試與 TCS 運維建議） | TCS NFR-001-9 建議的 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 只適用 `-k` 選取評估；整套測試設了它會讓 `tests/tools/test_local_ci_gate.py::test_conftest_is_where_the_autodetect_is_wired` 因環境而紅（本場 G2 實證，rc 1；G3 以正確形態重跑 rc 0）。該測試未像處理 `CI` 那樣 `delenv` 逃生變數 | 再開症狀：有人照 NFR-001-9 對整套測試設該變數而得 rc 1；修法＝該測試 `monkeypatch.delenv("AUTOCLAUDE_NO_PG_AUTODETECT", raising=False)` |
| F-08 | P4 | harness 觀察 | Skill 工具回傳 session 啟動時的快取文字（§1.4）；同 session 內改 SKILL.md 不反映 | 不修；SOP 已規定新功能開新 session |
| F-09 | P3（流程） | QA 自身 | W2.5 預審的結論「不會讓既有根層測試轉紅」不完整：實際上根層棘輪需主控重釘 `_TREE_FILE_FLOORS`（AutoClaude/tests 241→242、AISDLC_SDD/scripts/tests 26→27），DF-C 首跑全套另紅於 `test_platform_utils_dedup`（10→11）。前者後來由 SA 寫進 TCS 的 NFR-001-10 與 NFR-001-7，後者要到實作後才現形 | 已由主控修畢（`d9dc1ff0`、`e73749bf`）；預審清單日後須加「新增檔對根層 shrink-only 棘輪的影響」一項 |

**TCS 層面的註記（非實作缺陷）**：DF-A 的 TCS AT-001-4-E-1 在 Given 宣稱要求「驗證順序 R1→R2→R3」，其 When／Then 卻沒有任何組合案例，這是 P02 存活的根因；DF-C 的 AT-001-5-1 Given 宣稱「要求 R1」而 Then 沒有 R1 的斷言，這是 CP1 存活的根因。凍結後的 TCS 不改，由測試追加斷言補強。

## §5 RTM

| 檔案 | 動作 | 內容 |
|------|------|------|
| `AgentConsole/docs/06_quality/RTM.md` | 單線合併新列（新增 §2.1，14 列；其餘一字未動） | `F-001`、`US-001`、`AC-001-1`～`AC-001-5`、`AT-001-1-1`～`AT-001-5-2`；四格（實作檔／自動測試／E2E 驗證／狀態）皆回填；狀態 `✅ 實作+測試`（E2E 欄如實寫「非 E2E」，故不標 `✅ 已驗證`）；備註登記契約「原樣」描述的語意偏離 |
| `AutoClaude/docs/06_quality/RTM-WebhookSender.md` | 新建 | 9 列矩陣、覆蓋率 6／6、R↔AT 對映、NFR 追溯；狀態 In Review |
| `docs/06_quality/RTM-SddEnv.md` | 新建 | 9 列矩陣、覆蓋率 5／5、R↔AT 對映、NFR 追溯；狀態 In Review |

**偏離任務書字面之處（如實登記）**：任務書寫「`RTM.md` 單線合併新列（F-001／US-001／AC-001-1～5／AT 七列）」。RTM 檔頭與 §1.2 規定主表行首只准六種前綴（`US-`／`API-`／`BR-`／`NFR-`／`INF-`／`UI-`），§3.4 的現查指令以行首 `| <前綴>-` 計數；直接把 TCS 本地的 `US-001` 放進主表會讓總列數 392 與 US 58 對帳失準。因此以新增 §2.1 子表承載，ID 欄加反引號（RTM 檔頭「說明用表格的 ID 欄一律加反引號，避免被誤計」的既有慣例），掛靠既有列 BR-13／BR-14 但不改它們的四格。**現查（合併後）**：`^| (US|API|BR|NFR|INF|UI)-` 機械列數 392（US 58）、與合併前相同；§2.1 表頭 9 欄、資料列 14 列、每列 9 格、摘要皆 ≤ 20 字、ID 皆加反引號；檔案 LF、無 BOM。主控若要改成主表 BR 列（BR-34 起，並同步檔頭、§1.2、§3.2 三處數字），請另行指示。

**SCG-5 的 FSM 結果**：DF-B `RTM_VERIFY PASS`（AC 5／5、AT 7／7＝100%）→ RELEASE_READY。DF-A、DF-C 的 RTM 覆蓋同為 100%，但因 `PR_REVIEW` 一審 FAIL，`RTM_VERIFY` 未執行（二審通過後再跑，兩鍵各剩 `PR_REVIEW` 預算 4 次、`RTM_VERIFY` 預算 2 次）。

## §6 C7 演練逐字（拋棄式鍵 `sdd-drill`）

> 授權依據：W3 任務書 §3-2 與計畫 D-116-14；演練鍵的狀態目錄在 scratchpad（`…\scratchpad\qa_drill\fsm`，不在 repo 內），`approver` 如實標明「非真實人工核准」。**這是演練，不是真實的人工恢復**：agent 不得代跑真實專案的 `resume-from-escalation`（Rule 9.5），本場只對拋棄式鍵做。步驟 15 的「第二終端」＝PowerShell 工具的獨立行程（環境沒有三件組，與 headless 視窗的環境隔離）。

**步驟 1～12：建檔、走到 IMPLEMENTATION、轉入 ESCALATION（逐字；`show` 的整份 JSON 只留 `current_state` 一行，完整輸出在 `qa_drill/transcript_setup.txt`）**

```text
### 01 建檔（新功能鍵第一次 show，不帶 --must-exist）  [13:52:28]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project sdd-drill
rc=0
（JSON 略）"current_state": "INIT",

### 02 show --must-exist（三件組同址驗證）  [13:52:28]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project sdd-drill --must-exist
rc=0
（JSON 略）"current_state": "INIT",

### 03 transition → SCENARIO_DETECT  [13:52:28]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime transition --project sdd-drill --must-exist --to SCENARIO_DETECT --reason 'baseline adoption；SCG 未重跑'
rc=0
OK transitioned to SCENARIO_DETECT

### 04 transition → AGENT_LOAD  [13:52:28]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime transition --project sdd-drill --must-exist --to AGENT_LOAD --reason 'baseline adoption；SCG 未重跑'
rc=0
OK transitioned to AGENT_LOAD

### 05 transition → SPEC_DRAFTING  [13:52:28]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime transition --project sdd-drill --must-exist --to SPEC_DRAFTING --reason 'baseline adoption；SCG 未重跑'
rc=0
OK transitioned to SPEC_DRAFTING

### 06 transition → SCG_VALIDATION  [13:52:28]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime transition --project sdd-drill --must-exist --to SCG_VALIDATION --reason 'baseline adoption；SCG 未重跑'
rc=0
OK transitioned to SCG_VALIDATION

### 07 transition → HUMAN_PENDING  [13:52:28]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime transition --project sdd-drill --must-exist --to HUMAN_PENDING --reason 'baseline adoption；SCG 未重跑'
rc=0
OK transitioned to HUMAN_PENDING

### 08 spec-frozen Stage-1（演練；approver 如實標明非真實人工）  [13:52:29]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime spec-frozen --project sdd-drill --must-exist --stage Stage-1 --doc CLAUDE.md --digest --root D:\CursorProject\AISDCL_Agent --reason 'QA 演練（拋棄式鍵 sdd-drill）；baseline adoption；SCG 未重跑；授權依據：W3 任務書 §3-2、計畫 D-116-14' --approver 'QA 演練（拋棄式鍵 sdd-drill；非真實人工核准）' --json
rc=0
{"ok":true,"verb":"spec-frozen","project":"sdd-drill","from_state":"HUMAN_PENDING","current_state":"SPEC_FROZEN","stage":"Stage-1","spec_doc_digests":{"CLAUDE.md":"sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1"}}

### 09 negotiate-enter  [13:52:29]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime negotiate-enter --project sdd-drill --must-exist --reason 演練：進談判閘 --contract-ref CLAUDE.md
rc=0
{"ok":true,"verb":"negotiate-enter","project":"sdd-drill","from_state":"SPEC_FROZEN","current_state":"TEST_CONTRACT_NEGOTIATED","entered":true,"from":"SPEC_FROZEN","to":"TEST_CONTRACT_NEGOTIATED"}

### 10 negotiate-exit agreed  [13:52:29]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime negotiate-exit --project sdd-drill --must-exist --outcome agreed --reason 演練：共識達成
rc=0
{"ok":true,"verb":"negotiate-exit","project":"sdd-drill","from_state":"TEST_CONTRACT_NEGOTIATED","current_state":"IMPLEMENTATION","exited":true,"outcome":"agreed","to":"IMPLEMENTATION"}

### 11 transition → ESCALATION（演練）  [13:52:29]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime transition --project sdd-drill --must-exist --to ESCALATION --reason drill
rc=0
OK transitioned to ESCALATION

### 12 show --must-exist（確認 current_state）  [13:52:29]
$ (cwd=AISDLC_SDD_v0.30; env: SDD_STATE_DIR=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm SDD_PROJECT=sdd-drill) python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project sdd-drill --must-exist
rc=0
（JSON 略）"current_state": "ESCALATION",

```

**步驟 13：hooks-ON headless haiku 讀 README.md 第一行（drill 鍵在 ESCALATION）——被擋**（`qa_drill/step8_blocked_read_session.txt`，逐字）

```text
LABEL: step8_blocked_read
STATE_DIR: C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm
SDD_PROJECT: sdd-drill
CWD: D:\CursorProject\AISDCL_Agent
CMD: claude -p --model haiku --allowedTools Read --debug hooks --debug-file C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\step8_blocked_read_hooks.log "請用 Read 工具讀 D:\CursorProject\AISDCL_Agent\README.md 的第一行並回覆"
RC: 0
TIMED_OUT: False
ELAPSED_S: 8
--- STDOUT ---
我無法讀取 `README.md`。Read 工具被 SDD-FSM 的 PreToolUse hook 擋下，原因是目前 `sdd-drill` 專案的狀態是 ESCALATION（結構性升級）。hook 規定這個狀態下所有工具呼叫都會被阻擋，必須由人工在終端執行恢復指令。

我沒有嘗試其他工具或繞過方式（例如 PowerShell 讀檔、`SDD_HOOKS_DISABLE=1`），因為這會繞過治理守衛。

需要你處理的是：

- **恢復指令**：PowerShell 版本已列在 hook 的輸出裡，請在終端整行執行（它會把 `sdd-drill` 從 ESCALATION 轉回 SPEC_DRAFTING）。
- **注意**：這個 ESCALATION 來源是「未記錄」，hook 也說明這是 QA 演練用的拋棄式專案（鍵 `sdd-drill`）。你若確認演練已結束，可以直接依 R-9.5 恢復。
- 恢復後，我可以重新讀取 `README.md` 第一行並回覆。

--- STDERR ---
```

**步驟 14：debug log 第 712 行的 hook 輸出（`permissionDecision` 與恢復指令文字；`permissionDecisionReason` 全文逐字）**

```text
permissionDecision: deny
[SDD-FSM] state ESCALATION blocks all tool calls until human intervenes
[SDD-FSM][RECOVERY] 此 ESCALATION 來源 session=未記錄（第四輪前）；類別=structural（結構性升級）；原因=未記錄（第四輪前）；時間=未記錄（第四輪前）
  溯源：此 ESCALATION 由 session=unknown 於 未記錄（第四輪前）（時間未知）因 未記錄（第四輪前） 寫入（rule_id=unknown）；本 session=ebc3e953-5d09-4183-9fef-01ff481a226c（無法確認是否為觸發者（來源 session 或本 session 身分未記錄））
  目標=SPEC_DRAFTING（resume_state 不在合法出口，fallback 為 SPEC_DRAFTING）
  目前本 session 尚無可用 usage（新 session 首擊或 compact 後）
  外部專案模式（SDD_STATE_DIR 有設）：狀態目錄=C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm；專案鍵=sdd-drill。下列兩行已帶環境與 --project，請整行複製；省略任一項會打到框架預設目錄（回 noop、rc=0 的假成功，專案仍鎖死）
  人工恢復（R-9.5：需人類在終端執行；依你的殼複製對應那一整行）：
  bash/zsh   : cd "D:\CursorProject\AISDCL_Agent\AISDLC_SDD\AISDLC_SDD_v0.30" ; SDD_STATE_DIR='C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm' SDD_PROJECT='sdd-drill' "D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe" -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project 'sdd-drill' --to SPEC_DRAFTING --must-exist --reason "human resume after structural escalation"
  PowerShell : Push-Location "D:\CursorProject\AISDCL_Agent\AISDLC_SDD\AISDLC_SDD_v0.30" -ErrorAction Stop; $env:SDD_STATE_DIR = 'C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm'; $env:SDD_PROJECT = 'sdd-drill'; & "D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe" -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project 'sdd-drill' --to SPEC_DRAFTING --must-exist --reason "human resume after structural escalation"; Remove-Item Env:SDD_STATE_DIR, Env:SDD_PROJECT; Pop-Location
  修好後請自 ~/.zshrc（PowerShell 為 $PROFILE）移除 SDD_HOOKS_DRY_RUN=1（暫時繞過已無必要）。 緊急繞過：set SDD_HOOKS_DISABLE=1（全關）或 SDD_HOOKS_DRY_RUN=1（改發警告不阻擋）。
```

**步驟 15：把步驟 14 印出的 PowerShell 恢復指令原樣貼進另一個 PowerShell 行程執行**（PowerShell 工具的獨立行程，環境沒有三件組；指令字串逐字取自 `reason`，已存 `qa_w3/blocks/c7_recovery_command_ps.txt`）

```text
Reminder: remove SDD_HOOKS_DRY_RUN=1 from ~/.zshrc (PowerShell: $PROFILE); the temporary bypass is no longer needed.
{"from": "ESCALATION", "via": "RESUME_VERIFICATION", "to": "SPEC_DRAFTING", "resolved_at": "2026-10-18T05:54:04+00:00"}
```

**步驟 16：`show --must-exist`（`fsm_summarize.py` 取值，decision_trace 末 4 筆逐字）**

```text
show --must-exist rc=0
current_state: SPEC_DRAFTING
project: sdd-drill    updated_at: 2026-10-18T05:54:04+00:00
frozen_stages: 1 筆
  [0] stage=Stage-1 approved_by=QA 演練（拋棄式鍵 sdd-drill；非真實人工核准） frozen_at=2026-10-18T05:52:29+00:00
      CLAUDE.md = sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1
decision_trace: 共 11 筆；最後 4 筆（逐字）：
  [7] 2026-10-18T05:52:29+00:00 | TEST_CONTRACT_NEGOTIATED -> IMPLEMENTATION | trigger=test_contract_exit | reason=演練：共識達成
  [8] 2026-10-18T05:52:29+00:00 | IMPLEMENTATION -> ESCALATION | trigger=cli_manual | reason=drill
  [9] 2026-10-18T05:54:04+00:00 | ESCALATION -> RESUME_VERIFICATION | trigger=human_resume | reason=human resume after structural escalation
  [10] 2026-10-18T05:54:04+00:00 | RESUME_VERIFICATION -> SPEC_DRAFTING | trigger=human_resume | reason=human resume after structural escalation
escalation_history: 0 筆
```

**步驟 17：解鎖後再跑一次相同的 headless 讀檔——成功**（`qa_drill/step11_after_unlock_read_session.txt`，逐字）

```text
LABEL: step11_after_unlock_read
STATE_DIR: C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm
SDD_PROJECT: sdd-drill
CWD: D:\CursorProject\AISDCL_Agent
CMD: claude -p --model haiku --allowedTools Read --debug hooks --debug-file C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\step11_after_unlock_read_hooks.log "請用 Read 工具讀 D:\CursorProject\AISDCL_Agent\README.md 的第一行並回覆"
RC: 0
TIMED_OUT: False
ELAPSED_S: 6
--- STDOUT ---
第一行是：

```
# AISDCL_Agent
```

--- STDERR ---
```

**步驟 18：附帶探針（構造性，不計新暴露證據）——drill 鍵再轉入 ESCALATION 後，headless haiku 改用 PowerShell 工具讀同一檔**（`qa_drill/step12_blocked_powershell_session.txt`，逐字；該次 `show` 確認 `current_state: ESCALATION`）

```text
LABEL: step12_blocked_powershell
STATE_DIR: C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\fsm
SDD_PROJECT: sdd-drill
CWD: D:\CursorProject\AISDCL_Agent
CMD: claude -p --model haiku --allowedTools PowerShell --debug hooks --debug-file C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\fb85a4a6-fab4-4426-b0a0-1592a486cfd9\scratchpad\qa_drill\step12_blocked_powershell_hooks.log "請用 PowerShell 工具執行 Get-Content -LiteralPath D:\CursorProject\AISDCL_Agent\README.md -TotalCount 1 ，並把輸出的那一行原樣回覆"
RC: 0
TIMED_OUT: False
ELAPSED_S: 6
--- STDOUT ---
The first line of `D:\CursorProject\AISDCL_Agent\README.md` is:

```
# AISDCL_Agent
```

--- STDERR ---
```

**步驟 19：同一份 debug log 裡 PowerShell 觸發的 hook（逐字；沒有 `sdd_hook_router.py`、沒有任何 `permissionDecision`）**

```text
2026-10-18T05:55:02.180Z [DEBUG] Hooks: PreToolUse:PowerShell [${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe ${CLAUDE_PROJECT_DIR}/.claude/hooks/_hook_launcher.py .claude/hooks/lint_powershell_command.py] finished with status 0 (53ms)
2026-10-18T05:55:02.182Z [DEBUG] Hooks: PreToolUse:PowerShell [${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe ${CLAUDE_PROJECT_DIR}/.claude/hooks/_hook_launcher.py .claude/hooks/block_destructive_git.py] finished with status 0 (55ms)
2026-10-18T05:55:02.794Z [DEBUG] Hooks: PostToolUse:PowerShell [${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe ${CLAUDE_PROJECT_DIR}/.claude/hooks/_hook_launcher.py .claude/hooks/context_budget_guard.py] finished with status 0 (139ms)
```

**C7 小結**：(1) SOP 完整性——三件組、開場 `show --must-exist`、採納鏈與談判閘全數照 `SDD_AUTOCLAUDE_BRIDGE.md` §8 可逐步重跑（步驟 1～12，rc 皆 0）；(2) 阻塞態對被 matcher 命中的工具（Read）確實 deny，且 deny 訊息自帶外部專案模式的恢復指令（含 `SDD_STATE_DIR`、`SDD_PROJECT`、`--project`、`--must-exist`、`-W ignore::RuntimeWarning`，G-116-01／DEF-200-544 的修法在真機成立）；(3) 原樣貼進另一個 PowerShell 行程即解鎖（`decision_trace` 末兩筆 `human_resume`，reason 與 deny 訊息中的字串相同，證明字串一致），解鎖後同一次讀檔成功；(4) **但**阻塞態對 PowerShell 無效（步驟 18～19）：ESCALATION 下 headless 用 PowerShell 讀檔照常成功，router 完全沒被觸發——G-116-17 不只影響 ledger，也讓 ESCALATION 的「所有工具呼叫被擋」承諾在 Windows 上對唯一 shell 載具失效；(5) 恢復指令的 `--to` 為 `SPEC_DRAFTING`（演練以 `transition` 直接轉入 ESCALATION、`resume_state` 不在合法出口時的 fallback）；真實委派失敗走 `delegate-exit failed`，由 SOP §6.8 指定 `--to IMPLEMENTATION`，本場未走那條路（見 §8）。

## §7 VERDICT

**FAIL**（有 P2：F-01、F-02）。無 P1。DF-B 通過並已到 RELEASE_READY。

- **P≤2 清單（主控派修復棒；我二審）**：
  1. **F-01（P2）** `AutoClaude/tests/utils/test_webhook_sender.py`：在既有測試函式追加斷言——`:58` 後四階段逾時全等於 2.5、`timeout_s=3`（int）正例；AT-001-1-1 追加 `dataclasses.fields` 順序斷言；`:301` 後追加組合壞輸入（`http` 位址加 `None` payload 回 `invalid_url`、合法位址加 `None` payload 加 `max_attempts=0` 回 `invalid_payload`）；`:371` 後 `assert "attempts=3" in warnings[0].getMessage()`；第四次呼叫 payload 改 `{"x": object(), "leak-me-42": 1}`；AT-001-5-1 追加第五次呼叫（`secret_url`、`max_attempts=0`）斷言恰 1 筆含 `invalid_argument` 的 WARNING 且全文不含七個標記；AT-001-6-1 `:454` 後 `utcoffset() == timedelta(0)`，並把 `send_webhook` 替身改為函式、被呼叫當下斷言 `escalation_alert.log` 已存在。
  2. **F-02（P2）** `AISDLC_SDD/scripts/tests/test_sdd_env.py`：AT-001-5-1（`:238` 起）以 `monkeypatch.setattr(sdd_env, "force_utf8_stdio", spy)` 斷言一次 `main()` 恰呼叫一次；AT-001-3-1 的參數表（`:160`）加 `"A" * 31`（既有 `"格式" in cap.err` 即咬住檢查順序）。
- **P3（當輪改字）**：F-03 `sdd_env.py:128` 行尾；F-05 `webhook_sender.py:1-8` docstring；F-04 已記於 RTM 備註；F-09 為 QA 自身流程註記。DEF-AC-038 不在本輪修。
- **二審範圍**：修復後我會重跑——12 個存活突變（須全數轉紅）、DF-A 與 DF-C 整檔與全套（G1、G3、G9、G11）、`ruff`、覆蓋率與 LOC；FSM 對 DF-A、DF-C 各 `transition --to PR_REVIEW`→`gate PR_REVIEW PASS`→`gate RTM_VERIFY PASS`→預期 RELEASE_READY；並更新兩份 RTM 的狀態欄。
- **本輪 PASS／FAIL 的依據**：閘門全數親跑（§3；G2 的 rc 1 為我誤設環境變數所致，G3 以正確形態重跑為綠）、突變 98 個（§2）、委派路徑證據複驗全數相符（§1.2）、範圍越界 0、權杖零洩漏。**三鍵最終狀態**：`autoclaude-webhook`＝IMPLEMENTATION；`agentconsole-fsm-trail`＝**RELEASE_READY**；`monorepo-sdd-env`＝IMPLEMENTATION。
- **對 C1／C7 的附帶建議**：G-116-17 的暴露證據已齊（§1.3、§6），建議主控依 D-116-14 於 W4 加 PowerShell matcher；加完後我以同形態的兩個視窗各驗一次（SessionStart 注入、ledger 出現 PowerShell 入帳、ESCALATION 下 PowerShell 被擋）。

## §8 未涵蓋

1. **真實網路下的 `send_webhook`**：所有證據都經 `httpx.MockTransport`；真 HTTPS 端點的 TLS 驗證、代理環境變數、`~/.netrc`、真逾時與真重導均未驗。再開症狀：webhook 在真實環境收不到告警、或日誌出現未遮罩的 URL。
2. **Backend（Java）與 Frontend（TS）對 `from_inferred` 的承接**：DF-B 只動 Bridge；Console 監控頁「最近決策」是否顯示「AUTOCLAUDE_DELEGATED → ESCALATION」、Backend DTO 是否容許新增鍵，本場未驗（RTM §2.1 的 E2E 欄已如實寫「非 E2E」）。再開症狀：監控頁仍顯示 ESCALATION → ESCALATION，或 Backend 對未知鍵報錯。
3. **平台**：全部在 Windows 11 單機（pwsh 7.6.7、Claude Code 2.1.302）；`sdd_env.py` 的 bash 形在真實 bash／zsh 的 `eval`、DF-A 全套在 macOS／Linux、POSIX 形恢復指令的真殼執行，皆未驗。
4. **委派批次本身未重跑**：§1.2 是對操作員產物與原始日誌的複驗（compile 回應、run.json、事件、引擎日誌、RTM YAML、FSM 軌跡、權杖掃描、越界掃描、副本逐位元組比對），不是我另起一次真 haiku 批次。
5. **hooks-ON 只驗了 headless**：兩個開發視窗與 C7 演練都是 `claude -p`；互動 TUI 視窗的 SessionStart 注入、PowerShell 工具的 permission 提示與 auto mode 分類器行為未驗。
6. **真實委派失敗的恢復路徑**：C7 演練用 `transition --to ESCALATION` 進入阻塞態（`escalation_history` 0 筆、恢復目標 `SPEC_DRAFTING`），未走 `delegate-exit failed`＋`--to IMPLEMENTATION`（SOP §6.8）與 Console 顯示的 `recovery` 欄位。再開症狀：真實委派失敗後照 deny 訊息或 Console 的指令恢復而失敗。
7. **根層全套與其他子專案閘門**：`tools/run_root_unittests.py` 全套、AutoClaude `tests/contract/test_claude_md_*.py` 單獨重跑、AgentConsole backend／frontend 閘門、Docker 全棧均未跑；本場只跑與三個功能及本輪重釘直接相關者（§3 G12）。
8. **二審未發生**：F-01、F-02 修復前，DF-A 與 DF-C 的 SCG-4／SCG-5 未閉環；兩份 RTM 狀態為 In Review。
9. **G-116-17 的修復**：本輪不含 matcher 變更，因此「修後 PowerShell 入帳與阻塞態被擋」沒有證據；本場的暴露證據只證明缺口存在。
10. **突變檢驗的邊界**：突變為手工挑選的 98 個（核心 83、由 R 條文導出的探針 15；探針中 12 個存活、3 個被殺），不是窮舉；對 R6「`sleep=None` 時用 `time.sleep`」與 R4「每次嘗試用完即關閉 client」這兩條，在 NFR-001-4（不真睡眠、不碰網路）的前提下結構上無法由測試觀察，不計入存活。

## §9 二審（SCG-4 複審：F-01～F-03、F-05）

**日期**：2026-10-18　**二審者**：同一位 QA（未參與實作）　**對象**：HEAD `90d911e4`（主控指定的二審範圍；寫本節時 HEAD 已前進到 `d75a38a0`，該 commit 只動 `.claude/settings.json`、`CLAUDE.md`、`ONBOARDING.md`、`AutoSDD_improving_116.md` 四檔，`AISDLC_SDD/scripts`、`AutoClaude/autoclaude`、`AutoClaude/tests` 三處與 `90d911e4` 的 diff 為空，本節結論對其同樣成立）

**本節與一審的關係**：§7 的 VERDICT「FAIL」、§8 第 8 項「二審未發生」、§5 末段「`RTM_VERIFY` 未執行」皆以本節為準；一審原文一字未改（訂正協議：不靜默覆寫）。

### 9.1 提交對照與取證方式

| commit | 內容 | 增刪（`git show --numstat`） |
|--------|------|-----------------------------|
| `322e1351` | F-01／F-02 測試補強，只動兩支測試檔 | DF-A 測試 +68／−4；DF-C 測試 +4／−1 |
| `1c802e92` | F-03：`sdd_env.py` 改寫位元組並新增測試一支；F-05：`webhook_sender.py` 只改模組 docstring | `sdd_env.py` +11／−1；`test_sdd_env.py` +17／−0；`webhook_sender.py` +5／−5 |
| `90d911e4` | 只有四份 `.md`（API_Contract_P3-6、Phase6_P1_Backlog、ADR-XPLAT-016、improving_116） | `AISDLC_SDD/scripts`、`AutoClaude/autoclaude`、`AutoClaude/tests` 三處與 `1c802e92` 的 diff 為空 |

**取證方式（如實登記）**：突變與閘門量的是 commit 內容，不是工作樹。我第一次在工作樹上跑突變時，主控正在改 `sdd_env.py` 與測試（工作樹 14:27 的 F-03／F-05 修改）：DF-C 從 C14 起多出 3 支測試（基線 23 變 26），該次結果作廢、不採用（原檔留在 scratch，檔名帶 `contaminated`）。改以唯讀 `git archive` 把 `322e1351` 與 `90d911e4` 的相關子樹匯出到 scratch，突變載具用環境變數指向匯出樹；每個突變結果都記錄被改模組的載入來源路徑，全部落在匯出樹內。

### 9.2 弱化複核（`git show 322e1351`）

**結論**：既有斷言刪除 0 條、弱化 0 條；測試函式名稱（AT 底線形）一個都沒改，新增的函式只有巢狀輔助 `fake_send`（`1c802e92` 另有新測試，見 9.4）。被移除的 5 行逐行如下。

| # | 檔 | 被移除的行 | 改成 | 判定 |
|---|----|-----------|------|------|
| 1 | DF-A | `from datetime import datetime` | `from datetime import datetime, timedelta` | 匯入放寬，非斷言 |
| 2 | DF-A（AT-001-5-1 第四次呼叫） | `{"x": object()},` | `{"x": object(), "leak-me-42": 1},` | payload 仍不可序列化；`invalid_payload`、零呼叫、恰一筆 WARNING 三組斷言原樣；只讓既有標記字串進得了 payload（P08） |
| 3 | DF-A | 註解「四次呼叫的日誌全文…」 | 「五次呼叫…」 | 註解 |
| 4 | DF-A（AT-001-6-1） | `with patch(…, side_effect=outcomes) as mock_send:` | `side_effect=fake_send`（函式依序回同樣兩個 `WebhookResult`） | `outcomes` 只有兩個結果物件、沒有例外項，回傳等價；`call_count`、`call_args_list`、位置參數、四鍵 payload、日誌層級等後續斷言一字未動。`notifier.py:75` 對 `send_webhook` 沒有 try／except，替身內的斷言失敗會直接外拋、不會被吞 |
| 5 | DF-C（AT-001-3-1 參數表） | `… "中文"]` | `… "中文", "A" * 31]` | 只加一個值 |

### 9.3 突變複跑

**DF-A 殺 50/50、DF-C 殺 29/29**（兩個 commit 皆然；存活 0；apply／not-loaded／collect 異常 0）

| commit | 對象 | 基線 | 突變 | 被殺 | 存活 |
|--------|------|------|------|------|------|
| `322e1351` | DF-A | 9 支通過 | 50（核心 40、探針 10） | 50 | 0 |
| `322e1351` | DF-C | 23 支通過 | 29（核心 26、探針 3） | 29 | 0 |
| `90d911e4` | DF-A | 9 支通過 | 50（核心 40、探針 10） | 50 | 0 |
| `90d911e4` | DF-C | 26 支通過 | 29（核心 26、探針 3） | 29 | 0 |

**一審 12 個存活者逐個轉紅**（兩個 commit 的轉紅測試相同；座標＝`AutoClaude/tests/utils/test_webhook_sender.py` 或 `AISDLC_SDD/scripts/tests/test_sdd_env.py` 於 `90d911e4`）：

| 突變 | 內容 | 轉紅的測試 | 咬住它的斷言座標 |
|------|------|-----------|------------------|
| P01 | R4 逾時只套 `read` | AT-001-1-1 | DF-A `:59` 四鍵全等 |
| P06 | R3 `timeout_s` 只收 float | AT-001-1-1 | `:61-64` int 正例 |
| P07 | `WebhookResult` 欄位順序 | AT-001-1-1 | `:66-72` `dataclasses.fields` |
| P02a | R2 先於 R1（payload 先於位址） | AT-001-4-E-1 | `:317-324` 壞位址加 `None` payload 須回 `invalid_url` |
| P02b | R3 先於 R2（參數先於 payload） | AT-001-4-E-1 | `:325-333` 壞 payload 加 `max_attempts=0` 須回 `invalid_payload` |
| P03 | 終局 WARNING 缺 `attempts` | AT-001-5-1 | `:404` |
| P08 | `invalid_payload` 的日誌帶 payload | AT-001-5-1 | `:433` payload 加標記鍵，配 `:465-467` 標記迴圈 |
| P09 | `invalid_argument` 的日誌帶原始 URL | AT-001-5-1 | `:446-462` 第五次呼叫，配 `:465-467` |
| P04 | `timestamp` 用本地偏移 | AT-001-6-1 | `:517-518` `utcoffset() == timedelta(0)` |
| P05 | 先呼叫 webhook 再寫 alert log | AT-001-6-1 | `:489-500` 替身在被呼叫當下斷言 log 已存在且行數相符 |
| CP1 | 拿掉 `force_utf8_stdio()` | AT-001-5-1 | DF-C `:284` spy、`:290` `calls == [1]` |
| CP2 | R7 長度檢查先於格式檢查 | AT-001-3-1［`"A"*31`］ | `:177` 新參數值，配既有 `"格式" in cap.err` |

**方法註記**：（1）C09、C27 原先錨定在被 F-03 刪掉的 `sys.stdout.write(render(env, args.shell))` 一行；`1c802e92` 版改錨在 `text = render(env, args.shell)`，變異語意不變（成功時寫入 `os.environ`；stdout 多一行說明），兩者皆被殺（C09 由 AT-001-5-1、C27 由 9 支測試）。（2）P04 只在機器時區非 UTC 時咬得住：本機 UTC+8 所以被殺；UTC 的 CI 上該突變與正解同值（一審已載，不是測試缺陷）。

### 9.4 F-03／F-05 複核（`git show 1c802e92`）

**F-03（`sdd_env.py` 行尾）：成立，修得對。**

- 碼：成功路徑改為 `text = render(...)`、`sys.stdout.flush()`、取 `sys.stdout.buffer`、`buffer.write(text.encode("utf-8"))`、`buffer.flush()`；串流沒有 `.buffer`（極少數替身）才退回文字寫入。`--check` 的 OK 行與 stderr 診斷仍走文字層，Windows 上為 CRLF（本機實測：OK 行 stdout 84 位元組含 1 個 CR；兩種診斷 stderr 各 1 個 CR）；它們不是 `eval` 的對象，TCS R6／NFR-001-3 針對的是 `--shell` 三形態，所以只記為觀察、不列缺陷。
- 新測試 `test_AT_001_2_2_raw_stdout_bytes_carry_no_cr`（bash、powershell、json 三參數）：用 `sys.executable` 起子行程、取原始位元組，斷言 rc 0、無 `\r`、以 `\n` 結尾。本機實測三種 `--shell` 的 stdout 皆 CR 0 個。
- **拿掉修復就該紅**（突變做在 `90d911e4` 匯出樹的磁碟複本上，因為子行程跑的是磁碟檔；基線 26 支通過）：R0 修前原碼 `sys.stdout.write(text)`＝3 失敗（恰為新測試三參數）；R1 位元組寫入但 LF 換成 CRLF＝5 失敗（新測試 3、既有 2）；R2 去掉結尾換行＝3 失敗（新測試）；R3 位元組寫到 `stderr.buffer`＝12 失敗（含新測試 3）。誠實劃界：CR 只出現在 Windows 的文字層，mac／Linux 上新測試有沒有修復都是綠（該回歸本來就只存在於 Windows）。
- 不用 `reconfigure(newline=)` 的理由（行內 stdio 複本棘輪只准縮不准長）成立：本場 `test_platform_utils_dedup` 43 項 OK。

**F-05（`webhook_sender.py` 模組 docstring）：成立。** 兩版去掉模組 docstring 後的 AST 完全相同；行數 136／136；差異只在第 2 行與第 4～7 行；第 8 行之後逐行相同。新 docstring 已由開發進度敘述改為用途與邊界，與讀碼一致（R1～R6、R8、R9 逐項核過）；兩處文字面落差見 F-10、F-11（P4）。

### 9.5 閘門（二審範圍；全套由主控收尾統跑，我沒跑）

| 閘 | 指令（cwd） | 結果 |
|----|------------|------|
| G1 | DF-A 整檔 `python -m pytest tests/utils/test_webhook_sender.py -p no:xdist -o addopts= -q`（`AutoClaude`；設 `AUTOCLAUDE_NO_PG_AUTODETECT=1`） | rc 0；`9 passed, 1 warning in 0.45s` |
| G2 | DF-C 整檔 `python -m pytest scripts/tests/test_sdd_env.py -p no:xdist -o addopts= -q`（`AISDLC_SDD`） | rc 0；`26 passed in 0.59s` |
| G3 | 根層棘輪三模組 `python -m unittest discover -s tools/tests -p <模組>.py` | rc 皆 0：`test_platform_utils_dedup` Ran 43 OK；`test_subprocess_encoding_hygiene` Ran 39 OK；`test_platform_neutral_paths` Ran 177 OK |
| G4 | ruff 五檔（`webhook_sender.py`、`notifier.py`、`test_webhook_sender.py`、`sdd_env.py`、`test_sdd_env.py`；commit 內容經 stdin，以 `--stdin-filename` 套各檔原有設定） | rc 0；各檔 `All checks passed!` |

G1、G2 在真實工作樹跑（`git status` 顯示 `.py` 無未提交修改，工作樹內容＝HEAD）。

### 9.6 FSM 結果（三鍵最終狀態；`show --must-exist` 逐字）

兩鍵的指令：`transition --to PR_REVIEW`、`gate --gate PR_REVIEW --result PASS`、`gate --gate RTM_VERIFY --result PASS`，rc 皆 0；環境同一審（`SDD_ACTIVE_VERSION=0.30`、同一狀態目錄、`SDD_PROJECT=<鍵>`、cwd `AISDLC_SDD_v0.30`）。框架真實狀態檔 `FSM-STATE-AISDLC_SDD.yaml` 的修改時間仍是 2026-07-16 01:36:40、2417 位元組，未動。

```text
autoclaude-webhook     current_state: RELEASE_READY    decision_trace 共 23 筆；最後 3 筆：
  [20] 2026-10-18T06:39:26+00:00 | IMPLEMENTATION -> PR_REVIEW | trigger=cli_manual | reason=SCG-4 二審開始：F-01 測試補強 322e1351、F-05 docstring 1c802e92，HEAD 90d911e4
  [21] 2026-10-18T06:39:26+00:00 | PR_REVIEW -> RTM_VERIFY | trigger=gate_pass | reason=PR_REVIEW PASS
  [22] 2026-10-18T06:39:26+00:00 | RTM_VERIFY -> RELEASE_READY | trigger=gate_pass | reason=RTM_VERIFY PASS
monorepo-sdd-env       current_state: RELEASE_READY    decision_trace 共 19 筆；最後 3 筆：
  [16] 2026-10-18T06:39:34+00:00 | IMPLEMENTATION -> PR_REVIEW | trigger=cli_manual | reason=SCG-4 二審開始：F-02 測試補強 322e1351、F-03／F-05 修復 1c802e92，HEAD 90d911e4
  [17] 2026-10-18T06:39:34+00:00 | PR_REVIEW -> RTM_VERIFY | trigger=gate_pass | reason=PR_REVIEW PASS
  [18] 2026-10-18T06:39:34+00:00 | RTM_VERIFY -> RELEASE_READY | trigger=gate_pass | reason=RTM_VERIFY PASS
agentconsole-fsm-trail current_state: RELEASE_READY    decision_trace 共 17 筆；最後 3 筆（一審已到，本場未動）：
  [14] 2026-10-18T05:51:55+00:00 | IMPLEMENTATION -> PR_REVIEW | trigger=cli_manual | reason=SCG-4 PR 審查開始
  [15] 2026-10-18T06:05:17+00:00 | PR_REVIEW -> RTM_VERIFY | trigger=gate_pass | reason=PR_REVIEW PASS
  [16] 2026-10-18T06:05:28+00:00 | RTM_VERIFY -> RELEASE_READY | trigger=gate_pass | reason=RTM_VERIFY PASS
```

### 9.7 發現與結案狀態

| 編號 | 嚴重度 | 狀態 |
|------|:------:|------|
| F-01 | P2 | **已結案**：`322e1351`；DF-A 殺 50/50 |
| F-02 | P2 | **已結案**：`322e1351`；DF-C 殺 29/29 |
| F-03 | P3 | **已結案**：`1c802e92`；拿掉修復即紅（9.4） |
| F-05 | P3 | **已結案**：`1c802e92`；docstring 差異經 AST 驗證程式未變 |
| F-04、F-09 | P3 | 維持：F-04 是 TCS 文字偏離（主控 `e73749bf` 已接受）；F-09 是 QA 自身流程註記 |
| DEF-AC-038 | P3 | 維持開啟、本輪不修；入帳位置見 9.8 |
| G-116-17 | P4（建議升 P2） | 不屬本次二審範圍。依 `d75a38a0` 的 commit 訊息：根 router 的 PostToolUse matcher 已納入 PowerShell，PreToolUse 那一格被 auto mode 分類器拒絕、待掌舵者套上；我沒有驗證修後行為（驗法見 §7 末項） |
| F-06、F-07、F-08 | P4 | 不變 |
| F-10 | P4（新） | `webhook_sender.py` 新 docstring 第 6 行「任何例外都收進 `WebhookResult`、永不拋出」偏廣：程式（第 122 行註解、AT-001-4-E-1 情境四）只攔 `Exception`，`BaseException` 照常上拋；建議改「任何 `Exception`」 |
| F-11 | P4（新） | 同一 docstring 第 7 行遮罩清單「使用者資訊、埠、查詢字串、片段」漏列「路徑」；程式（第 35 行）與測試標記 `s3cret` 都涵蓋路徑，而 webhook 的 token 常在路徑裡 |
| F-12 | P4（新） | `sdd_env.py` 新寫法 `text.encode("utf-8")` 是嚴格編碼：POSIX 上含非 UTF-8 位元組的路徑（解出 lone surrogate）會拋 `UnicodeEncodeError`，舊文字層有 `errors="replace"`。理論洞、無暴露證據，不要求處理；再開症狀＝真實環境出現此例外 |

### 9.8 帳務與文件現況

- **DEF-AC-038 的入帳位置**：DEF-AC 序列沒有獨立帳本，慣例是記在各輪證據檔 §4（115 的 DEF-AC-030～037 就在 `docs/06_quality/AutoSDD_ZeroTrust_Audit_115.md` 第 473～514 行）。現查（含 `d75a38a0`；整個 repo 對 `DEF-AC-038` 的命中只有四份文件）：①本檔 §4 第 401 行（另見第 6、58、392、615 行）；②`AutoClaude/docs/06_quality/SCG4-REVIEW-WebhookSender-20261018.md` 第 40 行；③`AutoClaude/docs/06_quality/RTM-WebhookSender.md` 第 67 行；④主控的 `docs/04_planning/AutoSDD_improving_116.md` 第 133 行（W2 DF-A 第二輪列的末欄，是提及、不是入帳）。根層帳本 `docs/06_quality/AutoSDD_Defect_Log.md`（HEAD 版）與 `AgentConsole/docs` 都沒有。我沒有寫任何帳本。
- **兩份 RTM 依主控指示未動**：`RTM-WebhookSender.md`、`RTM-SddEnv.md` 的「狀態」欄仍寫 In Review、備註寫「待二審通過」，與本節結論不符；`RTM-SddEnv.md` 另有三處過期：「整檔 22 項」（現 26）、AT-001-2-2 未列新測試、AT-001-3-1 的「9 個參數」（現 10）。是否同步由主控裁量（約 6 行）。
- 一審兩份 SCG-4 報告的測試座標是 `306dbb2a`／`343d583a` 版；修復後行號位移，以本節 9.3 為準。

### 9.9 二審 VERDICT

**PASS**。無 P1、無 P2；一審的 P2 兩筆（F-01、F-02）與 P3 兩筆（F-03、F-05）皆已結案；新增 P4 三筆（F-10～F-12），不擋閘。三鍵最終狀態：`autoclaude-webhook`＝**RELEASE_READY**；`monorepo-sdd-env`＝**RELEASE_READY**；`agentconsole-fsm-trail`＝**RELEASE_READY**。

### 9.10 二審未涵蓋

1. 全套與其他閘門（`tools/run_root_unittests.py`、AutoClaude 全套、`ci-gate`、Docker 全棧）：主控收尾統跑，本場只跑 9.5 的整檔與相關模組。
2. 新測試在 mac／Linux 的行為：設計上恆綠（CR 只存在於 Windows 文字層），本場未跑。
3. 一審 §8 的其餘項目（真實網路、Backend／Frontend 承接、委派批次重跑、互動 TUI、真實委派失敗的恢復路徑）不變；G-116-17 的修復現況見 9.7，修後行為未驗。
