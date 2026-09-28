# CrossPlatform R179 — 掌舵者五問 Windows 真機四方覆核／SessionGate 收斂證據檔

> 輪次：2026-09-28，Windows 11 Pro 10.0.26200（Koala-MSI），Claude Code 2.1.283；主控 Fable 5.1，子 agent 皆 Sonnet 5。
> 流程：AISDLC 精簡版——主控先親測落一份事實包 → 四方（Architect／SA／SD／QA）唯讀分析 → 每項發現兩位反駁鏡
> （重現正確性／範圍治理）→ 完整性批評者 → 主控裁決 → 主控親手修法（兩處一行級）→ 收尾單人窗口。
> 前輪：`CrossPlatform_R177_SessionGate_Recovery_Evidence.md`（mac；DEF-200-340／401 結案、342 釐清）。本檔為
> DEF-200-342 結案、341 補 Windows 樣本、407／408 新立即結的詳情面。掌舵者原話：「派出四方專家獨立審查，
> 請確認以上都已經修好」。

## 一、掌舵者五問（逐字）與 Windows 真機結論

1. 「我用終端 claude 都會出現以下問題，才開新視窗，就說他被擋不能寫檔案用工具了，然後也不去查真實的數據」
2. 「模型都不用真實的 /context 或 API 去查真實數據」
3. 「印出的 context 數字與 /context 明顯不符，直接告訴我，那就是新缺陷。==> 好像沒有，請確認！」
4. 「`ctx 18.0% 175.2k/1.0m | Fable 5.1` ==> 為何 Windows 11 都沒有這個資訊」
5. 「是否修復已經收斂，不用再進行？」

| 問 | Windows 真機判定 | 一句話 |
|---|---|---|
| Q1 | **NOT-A-DEFECT（Windows 無證據）** | 本機 55 份頂層逐字稿（49 份含 assistant 訊息，2026-08-28～09-28）前 10／40 則 assistant 訊息零筆「新視窗就說被擋不能寫檔」自述；`[SDD-FSM][BLOCK]`／`permissionDecision:deny` 零筆真實紀錄；沒有任何 session 在前 3 次工具呼叫被自家 hook 擋下（最早 #10）；FSM-STATE `current_state: INIT`（2026-07-15 起未變）；`SDD_ACTIVE_VERSION` 未設 ⇒ 唯一會 deny 的 SDD hook 休眠。**R177 假設的 Windows 因果鏈（FSM 殘留阻斷態 → deny → 恢復指令被 lint 擋 → 自述被擋）每一環都被本機實測牴觸**（四方三方判 NOT_A_DEFECT、QA 判 FIXED＝同一批證據的標籤選字差）。 |
| Q2 | **FIXED（機制面）** | DEF-200-401 的三項文案（statusLine 三態、feed reason 接進 context 行、stale-cache 退化值說明）在本 session SessionStart 簡報逐字出現；`test_session_brief.py` 24 passed。SD 誠實劃界：「模型每次都真的去查」是行為傾向，程式碼審查證明不了；本輪能證明的是新視窗簡報已把真實數字與查證指令塞到模型眼前。 |
| Q3 | **NOT-A-DEFECT** | `--check` 五次採樣（主控 3、SA 2、反駁鏡 2）：`harness used＝逐字稿 used 差=0` 六次；唯一非 0 的一次差 15,580 ＝ feed 剛寫入新一則的 `cache_creation_input_tokens`、逐字稿該則尚未落盤，下一次即 0（usage tail 逐字對照見〈二〉）。修 DEF-200-408：差值非 0 時多印一句時序提示，讓下一個讀者不再把瞬間差值讀成新缺陷。 |
| Q4 | **NOT-A-DEFECT（部署缺口，本輪已裝）** | Windows 從未安裝 statusLine（`--status` installed:false rc=1）；掌舵者授權後 `install_statusline.py` rc=0，settings.json 只多 `statusLine` 五行（備份 `.bak-20260928T005957Z`）；Claude Code **在同一視窗即時載入**，~1 分鐘後 feed 檔出現且 `used_percentage` 隨訊息更新；閃窗觀測見〈七〉：可見 console 視窗 **0** 次。 |
| Q5 | **本輪收斂** | 340／401 在 Windows 覆核成立；342 依 Windows 親驗清單全跑完結案；341 Windows 141 次 0 紅、開發機重現不了、解鎖改 CI runner；新立 407（恢復指令 fail-fast）、408（差值提示）同輪結案。掌舵者側剩一件肉眼確認：新視窗最下方有無 `ctx` 行（本 session 是安裝後才載入，主控看不到自己的狀態列）。 |

## 二、主控親測事實（本場 tool_result 逐字）

- HEAD=`ee0d455`（工作樹 clean）；`python tools/session_resume_planner.py --pace`：`現在可派 4 個 agent（硬上限 cap=不設限）｜band=free｜最緊的一條＝seven_day 11% 剩 7021 分鐘`。
- `--check`（安裝前）：`used 86,955`／`window 1,000,000〔查表值…〕`／`水位 8.7%`／`harness feed 未採用：無 feed（statusLine 未設定或本 session 尚無 assistant 訊息）`。
- `install_statusline.py --status`：`"installed": false, "matches_current_checkout": false, "statusLine": null`、`status rc=1`；`--dry-run rc=0` `"action": "would-install"`；`install rc=0` `"action": "installed"`、`"backup": "C:\\Users\\wuwei\\.claude\\settings.json.bak-20260928T005957Z"`；`git diff --no-index` 備份 vs 現檔只多 `statusLine` 區塊（command＝`D:/CursorProject/AISDCL_Agent/.venv/Scripts/pythonw.exe D:/CursorProject/AISDCL_Agent/tools/statusline_context_feed.py`，正斜線、pythonw）。
- feed 檔 `~/.autosdd/context_feed/f16de026-….json` 於 09:02:19 出現（安裝於 08:59:57）：`"context_window_size": 1000000`、`"used_percentage": 17`→`19`→`20` 隨訊息更新 ⇒ Claude Code 在本視窗即時載入 statusLine 並成功呼叫進料器（寫檔＋print 同一路徑）。
- 進料器合成 payload 探針（`Start-Process -RedirectStandardInput`，不接管線）：`python.exe ExitCode=0 stdout=[ctx 8.7% 87.0k/1.0m | Fable 5.1]`、`pythonw.exe ExitCode=0 stdout=[同上]`。
- `--check` 三次：`harness used=169,565 逐字稿 used=153,985 差=15,580`（第二次）→ `harness used=187,312 逐字稿 used=187,312 差=0`（第三次）→ 後續 `199045` 對 `199045`。usage tail：同一 `message.id` 在逐字稿寫多行（thinking／每個 tool_use 各一行）、usage 欄相同；差 15,580 ＝ feed 那一則的 `cache_creation_input_tokens`（`cache_creation.ephemeral_1h_input_tokens=15580`），逐字稿當下最後一行仍是前一則 ⇒ 時序，不是解析（feed 與逐字稿的 cc 欄同源）。
- 逐字稿掃描（scratchpad `scan_win_transcripts*.py`／`scan_hook_errors_v3.py`，只讀）：55 份頂層逐字稿；`TOTAL by hook: {'PowerShell:lint_powershell_command': 61, 'PowerShell:block_destructive_git': 17, 'Workflow:context_budget_guard': 10, 'Agent:context_budget_guard': 11, 'Bash:block_bash_on_windows': 11}`；`sessions whose FIRST 3 tool calls hit a hook block:`（空）；auto-mode 分類器拒絕 0；Architect 加分類：61 筆 lint 命中 **100% 為 pipe-rc（讀 rc 接管線）、0 筆 naked-cd、0 筆 bare-bash**。
- 子專案目錄 slug（`…-AISDLC-SDD-v0-30` 2 份、`…-AutoClaude` 2 份）全是 `claude -p --model haiku` 探針（1 則 assistant、0 次工具），SessionStart 有 `[SDD-FSM]`／`[SDD-CTX]` 字樣但無 deny ⇒ 掌舵者在 Windows 從未於子專案目錄開互動 session。
- FSM-STATE（`AISDLC_SDD_v0.30/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml`，gitignore）：`project: AISDLC_SDD`、`updated_at: '2026-07-15T17:36:40+00:00'`、`current_state: INIT`、`escalation_history: []`、`auto_compact_state` 全 null/0、無 `pending_owner` 欄；另 7 支 `FSM-STATE-test-<pid>.yaml` 測試殘留（同目錄 gitignore）。
- hook 正面現查 `claude -p --model haiku --debug hooks`（兩次）：`claude -p rc=0`、`Hook SessionStart.*success`＝2、`non_blocking_error`＝0、`ENOENT` 6 筆全是 Claude Code stat `~/.claude/agents`／`commands`／`output-styles` 目錄，零筆指向 `.venv` 載具。09-27 09:01 merge 前的舊 session（bb58d158）SessionStart 有兩筆 `ENOENT uv_spawn '….venv/bin/python'`＝配對式舊 settings 的 POSIX 半條（DEF-200-406 已分類 retired）。
- Claude Code 自身（非本 repo hook）也會擋指令：本場 `Remove-Item $h -Force` 被 harness 以 `Remove-Item on system path '/' is blocked. This path is protected from removal.` 擋下（變數路徑被靜態誤讀）——這類訊息不含 `PreToolUse:… hook error` 前綴，`tools/probe/audit_session.py` 與本場掃描器結構上看不到（Architect ARCH-3，登記為量測邊界）。

## 三、四方分析與反駁鏡（摘要；完整 JSON 住 session workflow journal `wf_c8000a6e-ba0`）

| 方 | 核心發現 | 鏡 A（重現） | 鏡 B（範圍治理） | 主控採納 |
|---|---|---|---|---|
| Architect | ARCH-1 R177 Q1 表格措辭易讓讀者把「CONFIRMED」延伸到 Windows 假設鏈；ARCH-2 naked-cd 規則 49 份逐字稿零真實命中、DEF-200-340 屬防禦性強化；ARCH-3 量測器看不到 Claude Code 原生阻擋 | ARCH-1 部分成立（R177 §九已自揭，屬可讀性）；ARCH-3 成立 | ARCH-1 **REFUTED**（不回頭改已發布輪次證據檔，改在本輪證據檔＋帳本 342 收斂）；ARCH-2 REFUTED（340 立案靠確定性 lint 測試非逐字稿統計）；ARCH-3 REFUTED（已知邊界，非本輪 finding） | 不改 R177；本檔〈一〉Q1 列即為引用訂正；ARCH-2 觀察登記於〈九〉 |
| SA | SA-1 342 帳本落後於現查；SA-2 `check_lines()` 差值非 0 無時序說明 | SA-1 REFUTED（SA 只做了 7.1 的 [3] 一項）；SA-2 成立 | SA-1 REFUTED（同）；SA-2 成立但與 Q3 因果未證 | SA-1 由 QA 完整 7.1/7.2＋主控 6.5／7.4 補齊後才結案 342；SA-2 → DEF-200-408 修 |
| SD | SD-1 `recovery_hint.py` PowerShell 恢復指令 `Push-Location` 對不存在路徑非終止錯誤、`-m` 在錯誤 cwd 續跑；SD-2 閃窗觀測窗未跑完＋09:08:14 spawn 早於監看器 | SD-1 成立（三次 pwsh 實測）；SD-2 成立 | SD-1 成立、修法不違規；SD-2 成立 | SD-1 → DEF-200-407 修；SD-2 → 觀測窗延長至 65 分鐘＋再跑一次 `claude -p` 讓 SessionStart spawn 落在窗內（見〈七〉） |
| QA | R158 §七 7.1 [1]~[6]、7.2 6.1~6.4／6.6、7.4 二十次全跑；R177 四支測試 Windows 全綠；F1 341 未重現；F2 342 的分支未合成觸發 | F1 成立（反駁鏡自跑 20 次同綠）；F2 成立 | F1 成立（非新缺陷）；F2 成立但屬已知邊界（純 Python 分支） | F1 → 341 補 141 次樣本；F2 登記〈九〉 |

完整性批評者：四方對 Q1 的 FIXED／NOT_A_DEFECT 是標籤選字差非證據分歧；唯一有實質價值的分歧是 SD 對 Q2「機制對 ≠ 行為對」的劃界（主控採納，寫進〈一〉Q2）。

## 四、主控裁決（做／不做＋理由）

**做**
1. DEF-200-407：`recovery_hint.py` PowerShell 模板 `Push-Location "{sdd_root}"` → `Push-Location "{sdd_root}" -ErrorAction Stop`；v0.30 `test_recovery_hint.py` 兩處斷言同步（`startswith` 字面＋DEF-200-340 那格加 `assertIn('" -ErrorAction Stop; & ', ps)`）。理由：三鏡皆在 pwsh 實測成立、單一旗標、根層 ps-lint 鎖（startswith／endswith 判準）不受影響。
2. DEF-200-408：`tools/lib/harness_feed.py` 新增 `DIFF_HINT` 常數，`check_lines()` 差值非 0 時附在同一行尾（差=0 不附）；`test_context_budget_guard.py` 既有精確斷言同一行改寫、**不增行**（避免觸發護欄棘輪重釘）。理由：本場主控自己被一次 15,580 的瞬間差值誤導、掌舵者 Q3 的觸發點正是這行輸出。
3. DEF-200-342 結案（closed-by-decision）：解鎖條件「Windows 跑 R158 §七 7.1/7.2 回報」由 QA（7.1 六項、7.2 6.1~6.4／6.6／6.7）＋主控（6.5 兩次、7.4 100 次）合力達成；本列在兩平台皆解釋不了 Q1，fail-closed 分支是 D19 刻意設計（R177 主控裁決不改碼），純 Python 平台無關。掌舵者可重開。
4. DEF-200-341 維持 open、補 Windows 樣本：141 次 0 紅（QA 20＋反駁鏡 20＋1＋主控 100），CI 側約 1/15 下全綠機率 ≈0.006% ⇒ 開發機重現不了，解鎖改為 CI runner 重現。
5. statusLine 安裝（掌舵者本場授權執行）。

**不做**
- 回頭改寫 R177〈一〉Q1 表格：範圍治理鏡裁定「已發布輪次證據檔由下一輪引用訂正、不覆寫」；R177 §九已自揭 Windows 零觸及。訂正落在本檔〈一〉。
- 為 ARCH-3 新增「Claude Code 原生阻擋」偵測維度：既有量測器窄字面是檔頭自陳的刻意取捨，屬新功能非修 bug。
- 為 F2 在 Windows 重做 R177〈六〉三變體合成探針：分支為純 Python 條件式、不在鐵律三觸發清單內，且 R177 QA 探針自陳有 launchd 武裝副作用。
- 為 341 在開發機再加大樣本：141 次已把 p≈1/15 的假設壓到 0.006%，再加也對不齊 CI runner 的磁碟／防毒環境。

## 五、修法與紅→綠證據（主控親手、本場真跑）

- v0.30 `python -m pytest tools/fsm_runtime/tests/test_recovery_hint.py -q`：`37 passed in 1.96s`、rc=0（修前 QA 跑同檔 `37 passed`；本輪改的是斷言字面與新增一格 `assertIn`，紅端＝把 `-ErrorAction Stop` 拿掉即 `startswith` 與 `assertIn` 兩格紅）。
- 根層 `python -m unittest discover -s tools/tests -p "test_recovery_hint_passes_ps_lint.py"`：`Ran 2 tests … OK` rc=0（新形態餵 `lint_command()` 仍 0 命中）。
- 根層 `test_context_budget_guard.py -k cross_check_diff -k absent_feed_reason -k compact_boundary_null -k may_block_accepts`：`Ran 4 tests … OK` rc=0；`test_session_brief.py`：`Ran 24 tests … OK` rc=0。
- ruff：`tools/lib/harness_feed.py`＋`tools/tests/test_context_budget_guard.py`（repo 設定）`All checks passed!` rc=0；`--isolated --select E501 --line-length 100` 對 `test_context_budget_guard.py` 命中 5 筆皆為既有行（改寫的 12544 行不在列）；v0.30 兩檔 `All checks passed!` rc=0。

## 六、R158 §七 Windows 親驗清單執行結果（QA `[他包回報]`，主控覆核關鍵值）

- 7.1：[1] `SDD_ACTIVE_VERSION` 空；[2] 磁碟版本目錄 v0.01～v0.30；[3] `current_state: INIT`、`updated_at 2026-07-15T17:36:40+00:00`；[4] statusLine 已設定；[5] hook 載具存在=True；[6] 最近逐字稿前 40 則命中=0。
- 7.2：6.1 `project: AISDLC_SDD, current_state: INIT`；6.2 空；6.3 `--pace` `可派 4 個｜band=free`；6.4 True；6.5（主控）success=2、non_blocking_error=0 ×2；6.6 statusLine 段存在、feed 目錄 True、`差=0`；6.7／7.4 `test_file_lock.py` QA 20 次全 rc=0 `12 passed`、反駁鏡 20＋1 次同綠、主控 100 次 `red=0`、`Errno13 lines: 0`。
- 反駁鏡補充：`$env:CLAUDE_PROJECT_DIR` 在 PowerShell 工具 session 內為空字串，7.1 腳本原文照抄會得到 `D:\AISDLC_SDD` 這種錯路徑，須以 checkout 絕對路徑代入（R158 §七清單的已知邊界，本檔登記不改該檔）。

## 七、閃窗觀測（零 console 的 Toolhelp32＋EnumWindows 監看器，scratchpad `proc_watch_v2.py`）

- 判準：每 100 ms 記錄新行程（含 parent 鏈）＋列舉**可見**的 `ConsoleWindowClass` 視窗（`IsWindowVisible`）；conhost 出現 ≠ 視窗可見（`CREATE_NO_WINDOW` 也會配 conhost）。
- status line 刷新的行程鏈：`claude.exe → bash.exe（配一支 conhost）→ bash.exe → pythonw.exe（venv launcher）→ pythonw.exe`；hook exec form：`claude.exe → pythonw.exe → pythonw.exe`，零 conhost。
- v2（09:09:53 起 1500 s，已正常 `end`）：status line 刷新 33 次、hook 行程下 `pythonw.exe → powershell.exe` 11 次、`VISIBLE_CONSOLE_WINDOW` **0**；v3（09:15:12 起 3600 s，統計於 10:06:29）：刷新 117 次、powershell.exe 26 次、可見視窗 **0**（觀測期涵蓋四方審查 23 個子 agent、兩次 `claude -p`、SDD ci-gate、§7 回填與根層全套）。第二次 `claude -p`（09:31:02）的 SessionStart hook spawn 落在 v3 窗內，可見視窗仍 0。
- 誠實劃界：本機 `claude.exe` 的父鏈是 `pwsh.exe → antigravity ide.exe`（IDE 整合終端，conhost=21、OpenConsole=0）；EnumWindows 是全域列舉，與終端種類無關，但「掌舵者肉眼看到閃窗」仍是唯一的最終驗收，本檔不宣稱「已解決閃窗」，只宣稱「65 分鐘觀測期零可見 console 視窗」。

## 八、帳本異動

- DEF-200-341 open（狀態欄補 141 次樣本與解鎖條件改寫）；DEF-200-342 → closed-by-decision；新立 DEF-200-407 → fixed、DEF-200-408 → fixed、DEF-200-409 → fixed。五列皆 ≤700 bytes（收尾親驗量測；341 第一版 822 bytes 同時撞單列上限與存量超標總量棘輪，兩道一起紅，縮到 692）。
- 帳本輪替（DEF-99-001）：新列把主檔推到 246,397 bytes ≥ WARN 245,760，`test_real_repo_ledger_does_not_falsely_trigger_today` 紅、commit 期判準會指路 `--apply`。第一次全量 `--apply` 把 232 筆搬走後 `test_archive_defect_log.TestUnlockConditionIsMechanicallyChecked.test_headroom_matches_what_def676_claims` 紅（`DEF-101-676 不在主檔 ⇒ 本鎖失去掃描標的`：工具的可搬判準不排除該列，而鎖要求它留在主檔——工具與鎖之間的既有不一致，本輪以 `--keep` 具名排除處理、登記於〈九〉）。還原三檔後重做：`--apply --archive-num 68 --keep DEF-101-676,DEF-200-342,DEF-200-407,DEF-200-408,DEF-200-409`：228 筆、155,970 bytes 搬進 `AutoSDD_Defect_Log_archive_68.md`，主檔 247,062 → 98,488 bytes，INDEX 74,113 → 79,098（archive 標頭留 `--keep` 痕）；52 筆帶交棒字樣未搬（工具自述）；隨後 `--repin-oversize` 重釘超長列豁免常數（`OVERSIZE_ROW_CEILING` 36→24、`OVERSIZE_ROW_EXCESS_CEILING` 20027→14638、12 筆豁免 ID 隨搬遷移除），`tools/lib/ledger_rotation.py` 兩條 `*_HISTORY` 各追加一格、封印各延長一格、`_SEAL_TOTAL_MIN_LEN` 46→48、`_SEAL_TABLE_SHA256` 以當回合 `seal_table_digest()` 實測值重釘；`--check` 事後稽核見〈十〉。
- 主檔現況：本輪五列（341 open、342 closed-by-decision、407／408／409 fixed）與 DEF-101-676 皆留在主檔；前輪的 DEF-200-401（fixed）隨可搬清單住進 archive_68。

## 八之二、收尾單人窗口新發現：DEF-200-409（Windows 測試對真實使用者設定檔做 install→uninstall）

- 根層全套第一跑 3 failures：帳本 WARN 帶（上段）＋ `test_install_statusline.CliSubprocessTest` 兩支（`'noop' != 'would-install'`／`'noop' != 'installed'`）。
- 根因：`_run_cli()` 的 fresh home 只覆寫 `HOME`；Windows 的 `Path.home()`（`ntpath.expanduser`）讀 `USERPROFILE`，子行程於是一直讀寫**真實** `~/.claude/settings.json`。證據：`~/.claude/` 下自 2026-09-22 起累積約 150 支 `settings.json.bak-*`，609／577 bytes（無 statusLine）與 782／814／818 bytes（有）交替＝每次 Windows 跑全套都真的 install→uninstall 一輪；今天真實檔已裝 statusLine（〈二〉）⇒ install 回 `noop`，測試第一次露餡。macOS／CI runner 沒有這個差（`HOME` 有效、runner 無 statusLine）⇒ 兩年來只有這台機器看得到。
- 修法：`env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}`（同行改、不增行）；驗收＝兩支轉綠＋跑測試前後真實 `.bak-*` 數量相等（〈十〉）。
- 誠實劃界：`install_statusline.py` 的 `Path.home()` 不認 Claude Code 自己的 `CLAUDE_CONFIG_DIR` 覆寫——設了該變數的使用者會被裝到錯的 settings.json；本輪未觸及，只登記。歷史 `.bak-*` 殘留由掌舵者決定是否清（本輪不代刪）。

## 九、誠實劃界

- Q1「Windows 無證據」的掃描窗口＝本機 `~/.claude/projects/` 現存 55 份頂層逐字稿（2026-08-28 起）；更早的逐字稿已不在磁碟，結論範圍限定於此窗口。
- ARCH-2 觀察（naked-cd 零真實命中、pipe-rc 佔 100%）只登記不動作：DEF-200-340 的立案靠 `recovery_hint.py` 自產模板的確定性 lint 測試，不靠逐字稿統計；pipe-rc 產生端（模型習慣寫 `cmd | ...; "rc=$LASTEXITCODE"`）是否值得另立改善，留掌舵者裁決。
- 量測盲區：Claude Code 原生阻擋（`Remove-Item on system path … is blocked`）不帶 `PreToolUse:… hook error` 前綴，`tools/probe/audit_session.py` 與本場掃描器皆看不到；R177 §一 Q1 的 mac 歷史部分（09-09～10）不受本輪判定影響。
- DEF-200-342 的 fail-closed 分支本身未在 Windows 合成觸發（QA F2）；結案依據是「本列解釋不了 Q1」＋「分支為 D19 刻意設計」，不是「分支已在 Windows 驗過」。
- statusLine 的 `ctx` 行是否真的顯示在掌舵者的新視窗最下方、以及肉眼有無閃窗，只有掌舵者本人看得到；主控能證明的是進料器在本視窗被 Claude Code 成功呼叫、feed 檔隨訊息更新、65 分鐘零可見 console 視窗。
- DEF-200-410（open，未指派）：`archive_defect_log.py` 全量 `--apply` 會把 `DEF-101-676` 搬走，而 `test_headroom_matches_what_def676_claims` 要求它留在主檔——工具與鎖互相不知道對方；本輪只以 `--keep` 繞過，未改工具（改法需新測試＋護欄棘輪重釘，收尾窗口不做）。
- 四方與反駁鏡的數字皆 `[他包回報]`（主控覆核了 FSM 實值、`--status`、`--check`、四支測試 rc）；一位反駁鏡（ARCH-2 重現面）因五次輸出不合 schema 而無結果，ARCH-2 只剩範圍治理鏡的 REFUTED 裁定，主控據此只登記不動作。

## 十、收尾親驗（主控本場真跑，rc 逐字）

- SDD ci-gate（`pwsh AISDLC_SDD/scripts/ci-gate.ps1` → 薄委派 `bash scripts/ci-gate.sh`）：`AISDLC_SDD_v0.01: 1478 passed（not chaos）`／`AISDLC_SDD_v0.30: 1960 passed（not chaos）`／`共享 infra scripts/tests/: 363 passed`／`SDD_CI_GATE_RC=0`。
- ONBOARDING §7 回填（`tools/lib/clean_venv_carrier.py`，樹外乾淨 venv，探針 psycopg2／sqlalchemy 皆 ABSENT，finally 已刪）：`autoclaude 4689 passed／172 skipped`、`v001 1478`、`v030 1960`、`scripts 363`；指紋 `v030 → a306011227ca`（其餘三棵不變）；`BACKFILL_RC=0`。
- 針對性測試（Windows）：v0.30 `test_recovery_hint.py` `37 passed` rc=0；根層 `test_recovery_hint_passes_ps_lint.py` `Ran 2 … OK`；`test_session_brief.py` `Ran 24 … OK`；`test_context_budget_guard.py -k cross_check_diff…` `Ran 4 … OK`；`test_install_statusline.py` `Ran 26 … OK`（修 DEF-200-409 後；跑前後真實 `~/.claude/settings.json.bak-*` 數量 146→146）；`test_archive_defect_log.py` `Ran 183 … OK`（第一次輪替後 1 failure＝〈八〉所述 676 鎖，`--keep` 重做後綠）；`test_check_defect_log_crossref.py` `Ran 268 … OK`；`test_check_archive_required.py` `Ran 9 … OK`。
- ruff：本輪改到的檔（repo 設定）皆 `All checks passed!`；根層快層 `ruff check tools/ .claude/hooks/` rc=0；`--isolated --select E501 --line-length 100` 對改到的兩支測試檔：改寫行皆不在命中列（`test_install_statusline.py` 第一版 docstring 兩行 111／101 超寬，縮回後 0 命中）。
- 帳本：`archive_defect_log.py --check` rc=0（70 檔／1519 個 ID／68 支 archive 對 68 條 bullet）；`check_defect_log_crossref.py` `CROSSREF_RC=0`（帳本 111 筆有效狀態紀錄、19 份掃描目標皆無矛盾、具名治理文件 130 份皆已登記、未結存量 37 列）；主檔 99,163 bytes（輪替前 247,062）。
- 根層全套 `python tools/run_root_unittests.py`：第一跑 `REAL_RC=1`、`3 failures`（帳本 WARN 帶＋`test_install_statusline` 兩支，皆已修，見〈八〉〈八之二〉）；第二跑（最後一次改帳本與證據檔之後）：`REAL_RC=0`／`✅ unittest 數量下限釘選通過：發現 4666 個測試（下限 4543）`／`[cpu_budget] root-unittest workers=18`／`S=1737.3s｜slot 利用率=99.8%`／`[M6 id 集合] tools/tests@win32：✅ 集合關係成立（本次 skip 46 支）`。
- push 與雲端五支 run：見下方〈十一〉追記（push 後回填）。
