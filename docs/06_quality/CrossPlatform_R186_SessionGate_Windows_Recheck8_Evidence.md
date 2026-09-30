# CrossPlatform R186 — 掌舵者五問第八次四方獨立覆核（Windows 11 再執行一輪）／DEF-200-435～443 證據檔

> 輪次：2026-09-30（本地 08:06 起；掌舵者離席約 10 小時，18:11 續），Windows 11 Pro 10.0.26200，Claude Code **2.1.285**（R185 為 2.1.284）；主控 **Opus 5.5**（session `f4c765a7-2a26-4453-8d20-34b3c511b6ef`，R179～R185 主控皆 Fable 5.1）；子 agent 皆 Sonnet 5.5：四方 4（Architect／SA／SD／QA）＋Developer 4（Dev-A～D，鎖持有面互不相交）＋唯讀複審（見〈四〉）。額度守衛全程 `cap=1`（每 300 秒 1 個 Agent）⇒ 逐個派、**沒有 wf_id**；各包 JSON 住 session scratchpad（`r186_{architect,sa,sd,qa,dev_a,dev_b,dev_c,dev_d}.json`）。
> 掌舵者要求「省去非必要文件，只留一定需要文件」⇒ 本輪只產：本檔、帳本列、機械鎖必須的登記（`governance_docs.py`、guard-total 兩站點、ONBOARDING §7 回填）與根 CLAUDE.md 三列修正；四方報告不入庫。
> 前輪：`CrossPlatform_R185_SessionGate_Windows_Recheck7_Evidence.md`。

## 一、五問第八次判定（含與 R185 的差異）

| 問 | R186 判定 | 一句話（主控親測或他包實跑） | 與 R185 的差異 |
|---|---|---|---|
| Q1 新視窗就說被擋、不查真實數據 | **真實機制 5 條，本輪全修（DEF-200-435／436／437／438／440）** | Fable weekly_scoped 97%（halt）下 PostToolUse 對 Read／PowerShell／Grep／Glob **每次** rc=2 紅字（R185 逐字稿 `hook_blocking_error` 22 筆）＋扇出阻斷訊息在工具未執行時印「已正常執行完成」；帳號級遲滯檔不分模型，Fable 的 cap=0 污染 Opus 視窗；`--pace` 會把含攤提的較嚴 cap 寫進守衛共用的遲滯檔（先查就被擋）；治理檔提醒 rc=1 被標成 error（23 筆）；Fable 撞 halt 時連 `model: sonnet` 子 agent 也派不出 `[他包回報]`。 | R185 以母體普查判原指控 NOT-A-DEFECT；本輪在「Fable 撞 halt＋多模型視窗」新條件下重現出可機械驗證的成因 |
| Q2 不用真實 /context 或 API | **主控路徑 PASS；機制面修 438（`--pace` 自己扭曲真實數據）與 435（halt 後 `--pace` 謊稱量不到）** | 主控本場第 2 個 tool_use 即跑 `--pace`＋`--check`；但 `--pace` 在 Opus session 印 `five_hour 1% … band=prepare cap=1 note=amortized`（主控 18:35 親測）＝Fable 的 97% 混進攤提。 | R185 PARTIAL；本輪找到「查詢本身改變執法值」這條 R185 沒有的機制 |
| Q3 印出的數字與 /context 不符 | **NOT-A-DEFECT（本輪證據最強）** | 掌舵者肉眼讀到的四個底列數字 156.9k／177.8k／205.0k／212.1k，在本 session 逐字稿 **4/4 精確命中** assistant usage 三欄和（156,941／177,827／204,995／212,108）`[他包回報]`；statusLine 分子＝`--check` harness used＝逐字稿 used，75/75 筆全等 `[他包回報]`；主控 08:06 `--check` 差=0。`/context` 於 2.1.285 仍 USER-ONLY（自驗三步見〈五〉）。 | R185 以時序差解釋非 0 差值；本輪直接用掌舵者親眼讀數對帳 |
| Q4 Windows 沒有 ctx 行 | **NOT-A-DEFECT（Claude Code UI 行為），掌舵者親眼 A/B 兩次確認** | 互動提問框開著時底列 statusLine 看不到（兩次：第一次框開 9h57m `[他包回報]`），送出後立即出現 `ctx 16% 156.9k/1.0m \| Opus 5.5` 等四次讀數；新視窗首回覆前只顯示 `ctx n/a` ⇒ 改成自解釋文案（DEF-200-442）。 | R185「Windows FIXED、TUI 只有肉眼」；本輪由掌舵者肉眼補上最後一環，並找到「一直看不到」的真因＝提問／選單框蓋住底列 |
| Q5 收斂了嗎 | **未收斂**（見〈三〉SA 評估）；本輪修完＝「修復完成、進驗證輪」 | 每輪新立 P≤3：R179～R185 依序 2／2／1／5／2／2／5，R186 單輪 11 `[他包回報]`；43% 是前輪已修缺陷的姊妹站點——病根是鎖綁站點不綁家族。 | R185 宣告「本輪收斂成立」；本輪以操作型定義重判 |

## 二、主控親測事實（本場 tool_result 逐字）

- 動工前 HEAD＝origin/main＝`38f4cbd`、工作樹 clean；`claude --version`＝`2.1.285 (Claude Code)`。
- SessionStart 簡報：「context：本 session 尚無量測（新視窗…）；額度：額度量不到（reason=stale-cache（資料在，但已 24064s > TTL 180s …））⇒ cap=2 recommended=2 band=unmeasured …」。
- `--pace`（08:06:30）：`⇒ cap=1 recommended=1 band=converge binding=seven_day`，`kind=weekly_scoped 97% … band=halt … cap=0 model=Fable note=burn-ahead+model-scoped-excluded`；（18:35:09）`kind=five_hour 1% … band=prepare … cap=1 note=amortized ⇒ cap=1 recommended=1 band=prepare binding=five_hour`；（18:47:19）five_hour 4% 同為 prepare。
- `--check`（08:06）：`used 80,039 … window 1,000,000〔harness 回報（status line context_window.context_window_size；model=claude-opus-5-5）〕 水位 8.0% … 差=0`。
- statusLine：使用者層 `~/.claude/settings.json` 的 command＝`…/.venv/Scripts/pythonw.exe …/tools/statusline_context_feed.py`；本視窗 feed 08:08:58 `version 2.1.285`、`model claude-opus-5-5`。今早 08:04／08:05 另兩支逐字稿各 14 行＝只有 SessionStart 與 `/model` 切換、無 assistant 回覆；其 feed `used_percentage: null`、`context_window_size: 1000000`（＝首回覆前 `ctx n/a` 的真實樣本）。
- 掌舵者本場肉眼回報（逐字）：「完全沒有這一行」（提問框開著時）→「ctx 16% 156.9k/1.0m | Opus 5.5 ==> 現在又可以看到」→「ctx 18% 177.8k/1.0m | Opus 5.5 , 我實在不能確認」→ A/B 題答「框開著時看不到」→「剛剛互動視窗沒法看到 ==> ctx 20% 205.0k/1.0m | Opus 5.5／answer summit後, 就可以看到 ==> ctx 21% 212.1k/1.0m | Opus 5.5」。
- 掌舵者裁決：派工改依「目標模型」判額度軸（DEF-200-436）；halt 帶 PostToolUse「只提醒一次、不再紅字」（DEF-200-435）。
- Agent tool_use 的 input 鍵（本場逐字稿四次皆同）：`description,subagent_type,model,prompt,run_in_background`，`model=sonnet`（DEF-200-436 取 `tool_input.model` 的依據）。
- **DEF-200-434 歸因**：`\CursorProject_DailyBackup` LastRunTime 2026/9/29 23:00:01（與 flash_watch 可見視窗同一秒）、Action＝`D:\CursorProject\01.MyTools\01.BackupCursor\run_backup.bat`、Principal wuwei／Interactive、RegistrationInfo Author `KOALA-MSI\wuwei` Date 2026-04-11T11:21:02；ppid 2636＝svchost（`Schedule`）、1956＝svchost（`DcomLaunch` 等）。掌舵者起初答「不認得這個排程」；主控查得其 README 自述「模組已廢棄，改用 ConsoleUI」，`backup_history.log` 1188 行、`[BAT-END]` 0 次（`.bat` 內 `python` 解析到 pyenv shim `python.bat`、未用 `CALL` ⇒ 不返回），但 robocopy 目標內 `useMacWin.md` 為 09/29 01:21:19、`ONBOARDING.md` 為 09/28 15:30:48 ⇒ 備份本身有在跑。屬掌舵者 repo 外舊工具，非 repo 缺陷。

## 三、四方摘要 `[他包回報]`

- **Architect**（14 項）：A-1 帳號級遲滯檔不分模型（P2）、A-2 `--pace` 攤提與守衛不同尺、A-3 halt 扇出阻斷假句、A-4 halt 帶 PostToolUse 每次 rc=2、A-5 窗表缺 opus／sonnet 5.5、A-6 halt 依視窗模型不依目標模型、A-8 分軌軸綁定脆弱、A-11 根 CLAUDE.md 過時、A-12 治理檔提醒 rc=1；A-7（nimbus_quill unknown-kind＝設計）、A-9（「來源=cache」為常數標籤、時戳如實）、A-10（2.1.285 漂移無 repo 消費者）、A-13（並行起跑競態，P4）、A-14（流程揭露）不立 DEF。
- **QA**：A-1／A-2／A-3／A-4／A-6／A-12 全數 CONFIRMED；A-2 升 P2——`--pace` 並非唯讀，先查再派第二個 Agent 就被 cap=1 擋（S4 對照 S3）；另 11 筆 Q1／Q2 殘餘（halt 後 `--pace` 只回一行「量不到」、重複訊息首行像 free 帶、遲滯壓低時稱「好幾天」等）。重演腳本 `replay_new_window.py` 修前基準 sha256 前 16 碼 05649C73BFEE6D31。
- **SA**：Q3 四讀數 4/4 精確命中、三量同公式 75/75；Q2 主控路徑 PASS；新發現 SA-N1（子 agent 的 `--check` 量到父 session）、SA-N2（遲滯維持的 cap 被說成「好幾天」）；收斂定義與 R187 建議見〈一〉Q5；最少文件集＝帳本列、guard-total 兩站點、ONBOARDING §7、（建立即須登記的）一份證據檔。
- **SD**：D1～D9 設計與四包分工（鎖持有面互不相交，唯一串行邊＝Dev-B 的 D3 API → Dev-A 接線）。

## 四、修法與複審

| DEF | 包 | 修法（`[他包回報]`，主控收尾親驗見〈六〉） |
|---|---|---|
| 435 | Dev-A＋主控＋Dev-F | halt 帶 PostToolUse 只提醒一次（exit 0＋additionalContext，閂鎖鍵 sid×模型×軸×reset）；PreToolUse 扇出仍 rc=2、改稱「這次呼叫已被擋下、沒有執行」；halt 後 `--pace` 快取新鮮印逐軸真實讀數；重複訊息首行點明 halt；遲滯壓低的 cap 改說「由遲滯維持」；節流共用句去掉「不是等一下就好」的矛盾（主控初版把「等窗口清空」寫進共用句，Review-1 指出四個語境為假，由 Dev-F 改成語境中性） |
| 436 | Dev-A＋Dev-F | Agent／Task 帶 `model` 時依目標家族判額度軸；目標模型造成的 halt 只擋這一次、不落 session 級 halt 標記（Review-1 R1-F4） |
| 437 | Dev-B＋Dev-A | 遲滯狀態鍵（模型家族, 尺），`--pace` 走 pace 尺另存；`pace_contract.write(model=)` 另寫家族兄弟檔，canonical 不動 |
| 438 | Dev-B＋Dev-F | 攤提只遮「active_model 已知且不命中」的 scoped 軸；`family_key` 與 hook `model_family()` 同語意並以 parity 格釘住（Review-1 Rule 7） |
| 439 | Dev-C | 窗表補 `claude-opus-5-5`／`claude-sonnet-5-5`＝1000000 |
| 440 | Dev-D | 治理檔提醒與 stash 哨兵提醒改 rc=0＋additionalContext；家族結構鎖 `TestHookExitCodesAreZeroOrTwoExceptDegradedPayload`（hook 內每個 `return 1` 須標 `# degraded-payload:`） |
| 427 | Dev-C＋Dev-A | `claude_json_path()` 新 SSOT；quota_meter／endurance_env／hook 三處／SDD 孿生改走 SSOT；測試不再在真家目錄建目錄 |
| 441 | Dev-B | 分軌軸家族包含比對、`seven_day_opus`／`seven_day_sonnet` 導出 scope |
| 442 | Dev-D | 首回覆前印 `ctx n/a of 1.0m (until next reply) \| <model>` |
| 443 | 主控 | 根 CLAUDE.md 三列改寫（`test_doc_loc_baseline_freshness_r60.py` rc=0） |
| 444 | Dev-E | 根層 runner 把 TEMP／TMP／TMPDIR 導到隔離目錄，跑後比對真實 `autosdd_pace*.json` 並出聲 |

- **修後驗收重演**（主控本場實跑 `replay_new_window.py --out replay_after.txt`，REPLAY_RC=0、elapsed 20s）：修前 13 個「存在」的症狀中 11 個翻成不存在（A-1、A-1b、A-2、A-3、A-4、A-6、A-6b、A-12、A-12b、Q2 halt 一行、Q-3 簡報與執法不符）；仍存在的 2 個是刻意設計的守衛（Windows 擋 Bash、擋行首裸 cd，訊息皆附改用方式）。S2B 情境修後遲滯檔已分家：`fable` cap=0、`opus` cap=2、`opus_pace` cap=2、`sonnet` cap=2；其中兩次 rc=2 為「每 300s 最多 2 次扇出、本視窗已用 2 次」的正常派工上限。
- **Review-1**（唯讀）：APPROVE_WITH_FIXES，must_fix 2（R1-F1、R1-F4）＋should_fix 6，皆交 Dev-F；突變 9 個殺 8 個，存活的 M1（Task＋model）由 Dev-F 補格。

## 五、誠實劃界與未驗

- `/context` 於 2.1.285 仍 USER-ONLY。掌舵者自驗三步（SA 設計）：① 送一句「只回 OK」；② 等回覆後輸入 `/context`，抄下標題列的已用 tokens，同時抄底列 `ctx … N/1.0m`；③ 兩者相差 ≤0.1k 且百分比相同即相符，否則把兩個數字貼給模型當新缺陷。
- 「提問框期間隱藏 statusLine」是否為 Claude Code 刻意設計：只有觀測（掌舵者 A/B 兩次），無官方文件佐證。
- 互動式 SessionStart payload 是否帶 `model`：仍 UNVERIFIED。
- **SA-N1（子 agent 的 `--check` 量到父 session）不修、登記劃界**：主控本場親查工具環境 `CLAUDE_CODE_SESSION_ID=f4c765a7-…`、`CLAUDE_PID=6112`、`CLAUDE_CODE_CHILD_SESSION=1`，Dev-C 在子 agent 內的探針得到**完全相同**的三個值 `[他包回報]` ⇒ 環境裡沒有任何可區分「我是子 agent」的訊號（`CLAUDE_CODE_CHILD_SESSION=1` 主控也有，不是子 agent 標記），猜測式修法只會製造新假話。子 agent 是葉節點、不需自量水位（SA：四個樣本 0 個需要 `--pace`）；其自身 context 由 Claude Code 管。
- A-13（並行子 agent 起跑時「額度量不到」＝refresh 在途競態，P4）：本輪未修，觀察所得僅 Architect 一筆痕跡，不立 DEF。
- 主控初版的 R1-F1 句子本身是一次「共用句用錯語境」的失誤：Review-1 以 probe_a.py 在 halt／Workflow／`--pace`／prepare 四個語境重現為假話，已由 Dev-F 收回。
- Mac 面全部未驗（沿用 R183～R185〈八〉交棒）。

## 六、收尾親驗

- **修後驗收重演**（主控親跑）：見〈四〉末段，11 個缺陷症狀全數翻成不存在。
- **Trim 棒**（掌舵者裁決「先瘦身再說」；`r186_trim.json`）`[他包回報]`：護欄層淨額 +1594→+791；出口 A＝81 段純史料原文 1,078 行逐字搬入新開的 `CrossPlatform_Guard_Line_History_2.md`（129,015 bytes；第一冊只剩約 12KB 故另開，第一冊 TOC 末加指針＝250,018 bytes；已登記 `governance_docs.py`）；出口 B＝35 段本輪新增 docstring 171→110 行；42 支檔去 docstring 的 AST 指紋修前後全同、85 檔逐檔 `Ran` 4876→4876；分桶 prose 4327→4235（≤4311）、guard_self 3163→3007；E501 137→136。
- **主控核帳**：Trim JSON 的 42 支檔逐檔加總 68,767→67,964＝**淨 −803**（與棘輪讀數一致）；`tools/tests` 內指向第二冊的指針行 82 行。⇒ 1,078 是「移出的史料原文行數」，原位另補回指針與保留的現行 WHY 句，故淨減少小於 1,078＋61；重釘列理由的「刪 1078 行」「刪 61 行」指移出動作，淨額以該列 before→after 為準（該列受 sha 鏈保護，不為措辭重算）。
- **重釘棒**（`r186_repin.json`）`[他包回報]`：`--print-guard-lines` 109396→110201（+805，鎖檔自身 8913→8927），最終 print `+0`、逐檔漂移 0 支；回歸鎖軌申報 309、主軌 496 ≤ 524；款(11)：R185 主軌連升第 1 輪、R186 第 2 輪 ⇒ **R187 主軌必須 ≤0**；款(12) 到期兌現 `(186, 524)`、重新武裝 188／523；前綴 316→317、sha12 `61ea6814f294`→`fab77716902f`；`test_adr_xplat001_c1c2_lock.py` `Ran 192` OK；MIN_TESTS 4697→4876（runner 777／777 不增行），ONBOARDING §7 表① 同步一個 token、`sync_onboarding_baselines.py --check`／`--check-snapshot` rc=0；guard-total 兩站點（`CrossPlatform_R145_Scan_Findings.md`〈附記（R186）〉、`AutoSDD_improving_112.md` 尾列）；`special_stale` 為空，SPECIAL_FILES 不動。
- **帳本**（主控用腳本寫入，先驗 ≤700 bytes／7 欄／無半形 `|` 才落盤；434 兩次超線 802→723→698 後才寫）：新增 DEF-200-435～444 十列、427→fixed（685 bytes）、434→no_action_needed（698 bytes）；`check_defect_log_crossref.py` rc=0（有效狀態紀錄 135→145）、`archive_defect_log.py --check` rc=0；未結清單 39→37。
- **根層全套**（主控親跑，最後一次文件寫入之前的程式碼定稿後）：`SUITE_FINAL_RC=0`、`✅ unittest 數量下限釘選通過：發現 4876 個測試（下限 4876）`、slot 利用率 99.8%、`✅ 真實 TEMP 圍籬：全套期間真實 TEMP 下 autosdd_pace*.json 零變動（前 4／後 4 份）；隔離根已建立並清除`、`✅ 孤兒 console 普查：零增長（前 0／後 0）`。對照修前第一跑：20 failures（全在預期三類）＋全套前後真實 `autosdd_pace.json`／`_fable`／`_sonnet` 雜湊皆變。
- 本機 nightly（22:30:01 起跑，`LastTaskResult=1`）撞上未 commit 的修法並重寫 `AutoClaude/.perf_baseline.toml` 4 行——同 R185 慣例一併帶入本輪 commit。

## 七、根層全套、push 與雲端驗收

- 根層全套見〈六〉（`SUITE_FINAL_RC=0`、4876 個測試、真實 TEMP 圍籬零變動）。
- commit `80dbd90`（74 files changed, 4633 insertions(+), 1418 deletions(-)；pre-commit `✅ 全部通過`，ROOT-TOOLS-WARN 三支 tools/lib 餘裕 ≤1 行為既有非阻塞提示）。
- push：`38f4cbd..80dbd90  main -> main`、`[pre-push dispatcher] ✅ 本次 push 觸發的所有 leg 皆通過（rc=0）`（`[cpu_budget] parallel legs: root=18 autoclaude=2 sdd=2 wall=170s`；`✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）`、FRAMEWORK_STATUS.md 新鮮）、`PUSH_RC=0`；`git rev-parse HEAD`＝`origin/main`＝`80dbd90a66bfccdd6df93f795d36d70504a8c086`。
- 雲端（主控 PowerShell 迴圈每 60 秒 `gh run list --commit 80dbd90a66bfccdd6df93f795d36d70504a8c086` 輪詢至全部 completed，2026-10-01 00:41:09 收斂）：`aisdlc-sdd-ci` 36743817768 **success**、`AutoClaude CI` 36743817894 **success**、`macos-compat-ci` 36743817906 **success**、`root-infra-ci` 36743817675 **success**、`windows-compat-ci` 36743817580 **success**（`CLOUD_DONE non_success=0`）。`macos-compat-ci` 成功＝本輪新測試已在雲端 macOS runner 跑過（〈八〉第 6 條的一部分）；真機項目仍待 Mac。
- **Q5 本輪結論**：修復面全部落地（全套、pre-push 三 leg、雲端五支 success），但依 SA 操作型定義**尚未收斂**（〈一〉Q5）；下一輪 R187 在 Mac 執行驗證輪。本節為 push 後回填，隨後以 docs commit 再 push 一次。

## 八、Mac 交棒（掌舵者：「下輪到 MAC 執行!」；承 R183～R185〈八〉，指令形態沿用）

> R187 定位＝**驗證輪**（SA 收斂定義）：目標零程式碼差異、不產生重釘列（本輪主軌已連升第 2 輪，R187 主軌必須 ≤0）。若 Mac 驗證又冒出已知家族的 P≤3，不再開新輪，改做家族級結構鎖。Mac 工具殼是 zsh，讀 rc 的機制與修法見 `useMacWin.md` §C。

1. **開場（第一回合）**：`python tools/session_resume_planner.py --check` 與 `--pace`；首行應為 `session 來源＝環境變數 CLAUDE_CODE_SESSION_ID（sid=…）`。另跑 `env | grep '^CLAUDE'` 記下是否有 `CLAUDE_CODE_SESSION_ID`／`CLAUDE_CODE_CHILD_SESSION`（Windows 主控與子 agent 三值完全相同，見〈五〉SA-N1）。
2. **Q4 肉眼 A/B（掌舵者）**：①新視窗首回覆前底列應為 `ctx n/a of 1.0m (until next reply) | <模型>`（DEF-200-442）；②模型開提問框時底列消失、送出後出現（Windows 已確認為 Claude Code UI 行為）；③回覆後 `ctx NN% …k/1.0m | <模型>` 的數字與 `--check` 的 harness used 同源。
3. **Q3 `/context` 自驗三步**（〈五〉第一條，Windows 仍 USER-ONLY）。
4. **額度模型軸（DEF-200-436／437／438／441）**：`ls ~/.autosdd/traces/autosdd_quota_stability*` 應出現依家族（與 `_pace`）分開的檔；`--pace` 在非 Fable 模型下不得出現因 Fable 專屬軸造成的 prepare／halt。Fable 週額度 reset＝2026-10-02T22:00Z（台北 10/03 06:00）：Mac 若在 reset 前以 Fable 當主控，halt 帶應只在第一次工具呼叫後提醒一次、非錯誤樣式（DEF-200-435），扇出被擋時訊息寫「這次呼叫已被擋下、沒有執行」並附 Read／Write／Edit 照常可用；派 `model: sonnet` 子 agent 應放行。
5. **根層全套經 runner**（DEF-200-444）：`python tools/run_root_unittests.py`，輸出要有 `✅ 真實 TEMP 圍籬` 一行，且 `$TMPDIR/autosdd_pace*.json` 前後雜湊不變；Windows 本輪為 4876 個測試（〈六〉），Mac 預期同數（macOS 專屬 skip 另計）。
6. **本輪新測試在 macOS 首跑**（皆只在 Windows 驗過）：`test_run_root_unittests.py`（`TempFenceTest`，TMPDIR 語意）、`test_block_destructive_git_r83.py`（家族結構鎖、提醒 rc=0）、`test_platform_utils_dedup.py`（`claude_home()`／`claude_json_path()`、joinpath 站點鎖）、`test_context_window_parity.py`、`test_statusline_context_feed.py`、`test_quota_policy.py`、`test_context_budget_guard.py`。
7. **DEF-200-427 的 Mac 側**：Mac 憑證在 Keychain（設 `CLAUDE_CONFIG_DIR` 時 service 名帶 `-sha256(dir)[:8]` 後綴，SD-8），`quota_meter` 的 `claude_home()` 路徑只影響檔案型憑證——請確認 Mac 上 `--pace` 仍量得到額度（`來源=` 行）。
8. **治理檔提醒（DEF-200-440）**：Mac 視窗若有機會編輯治理檔，確認顯示為 `PreToolUse:Edit hook additional context`，不是 hook error（Windows 主控本場兩次親見此形態）。

## 九、掌舵者側待辦（只有本人能做）

1. `/context` 自驗三步（〈五〉第一條）。
2. `\CursorProject_DailyBackup`：README 自述已廢棄但仍每晚 23:00 在跑且備份有效；要保留、停用（`Disable-ScheduledTask -TaskName CursorProject_DailyBackup`）或改走 ConsoleUI 由你決定——repo 不動它。
3. Mac 第一個視窗：R183～R185〈八〉＋本檔〈八〉。
4. （選做）真實 `%TEMP%` 仍有修前測試殘骸（`autosdd_dotenv_*` 約 215 個目錄、`quoteprobe*`、`sentinel_gc*`、測試用 sid 的 `autosdd_ctxguard_*.latches.d`）`[他包回報]`；DEF-200-444 之後經 runner 不再新增，是否清理由你決定。
