# CrossPlatform R183 — 掌舵者五問第五次四方獨立覆核／DEF-200-420／421／422 新立即結／418 第一步／Mac 交棒證據檔

> 輪次：2026-09-29，Windows 11 Pro 10.0.26200（Koala-MSI），Claude Code 2.1.283；主控 Fable 5.1（session `888b2ff4`），子 agent 皆 Sonnet 5：四方 4＋反駁鏡 6＋完整性批評者 1＋Developer 3＋唯讀對抗複審 2＝16 包。全程逐個 `Agent` 派工（額度守衛 weekly_scoped notice 帶在 PreToolUse 擋下 `Workflow`，理由「數不到」；每 300 秒最多 4 個），故本輪**沒有 wf_id** 可引，各包回報 JSON 已摘錄於本檔〈三〉〈四〉。
> 流程：AISDLC 精簡版（掌舵者指示「省去非必要文件，只留一定需要文件」＝本證據檔＋帳本列＋`governance_docs.py` 登記＋useMacWin.md 一句）——主控親測落事實包 → 四方（Architect／SA／SD／QA）唯讀獨立審查（本輪新增「Mac 面」鏡頭：掌舵者「下輪要在MAC執行!」）→ 每項單方發現兩位反駁鏡（A 重現正確性／B 範圍治理；兩方獨立命中且有實跑者免鏡）→ 完整性批評者 → 主控裁決 → Developer **串行**修法（同一鎖持有面不並行：Developer-A 收工後才派 Developer-B；文件包獨立檔）→ 每包一位唯讀對抗複審 → 收尾單人窗口（主控親修複審 must_fix／should_fix、帳本、棘輪重釘、全套、push）。
> 前輪：`CrossPlatform_R182_SessionGate_Windows_Recheck4_Evidence.md`。掌舵者本輪原話：「派出Architect / SA / SD / QA 四方專家獨立審查,請確認以上都已經修好！」＋「下輪要在MAC執行!」。

## 一、五問第五次判定（含與 R182 的差異與 Mac 面）

| 問 | R183 判定 | 一句話 | Mac 面（下輪要親驗的那一環） |
|---|---|---|---|
| Q1 新視窗就說被擋、不查真實數據 | **原始指控 NOT-A-DEFECT（維持）；衍生文字缺陷 412／413 FIXED（四方皆親驗在 HEAD）** | SA 對 R182 後 6 支頂層逐字稿以結構化欄位重數：Bash `tool_use` 0、`hookName=="PreToolUse:Bash"` 0、「被擋／不能寫」命中 19 筆逐條人工分類全是複述五問或 push 被擋、零真自述；QA 餵 Bash payload 給 hook rc=2 且 stderr 含「寫檔／改檔 → 用 Write／Edit」；`halt_convergent_clarification()`／`rc2_clarify()` 現值含 PowerShell、不含「／Bash／」；批評者本場親觸 Bash 一次取得同句＝第五方重現。主控本視窗零 Bash 嘗試、零「被擋」自述。批評者裁定：兩個詞答的是兩個子問題，不可平均成單詞。 | `block_bash_on_windows.py` 非 Windows 一律 exit 0；兩句澄清句 `windows=False` 回 POSIX 版（含 Bash，Mac 上為真話）——有測試守（`test_session_brief.py` patch `is_windows` 兩格、`HaltConvergentClarificationPlatformTest`），macos-compat-ci 對 be2aab2 success。待 Mac 肉眼：簡報印 POSIX 版、不得出現「PowerShell」。 |
| Q2 不用真實 /context 或 API 查數據 | **PARTIAL（維持，四方一致）＋機制面補一刀 DEF-200-420** | SA：R182 後有工具呼叫的 4 支 cli session 前 5 次呼叫皆含 `--check`／`--pace`（4/4；2 支 sdk-cli 零工具呼叫不入分母）；仍是 advisory 非機械強制。**新抓**：`--pace` 本身給的數字比守衛寬鬆（DEF-200-420）——模型「查了真實數據」卻查到一個不會被拿去擋人的判定；主控本場親遇（〈二〉）。 | `--check`／`--pace` 零平台分支；Mac 第一動作照做，並對照 SessionStart 簡報的額度行是否同數（420 在 Mac 的重現點）。 |
| Q3 印出的數字與 /context 不符 | **NOT-A-DEFECT（維持，四方一致）** | SA 對 5 支 session（f16de026／ab9d77f0／aa8c76b6／40a1a0c4／888b2ff4）feed 三欄和 vs 逐字稿最後一筆 usage 三欄和皆 diff=0；主控本場 `--check` 差=0；QA／SA 餵本視窗 feed 印 `ctx 20% 201.4k/1.0m | Fable 5.1`（整數、無 .0，416 生效）。 | feed 路徑 `~/.autosdd/context_feed` 純 expanduser；SA-3：逐字稿 slug 推導 docstring 自陳「觀察到的、非官方契約」且測試循環驗證 ⇒ Mac 第一視窗要 `ls ~/.claude/projects` 對照（〈八〉）。 |
| Q4 Windows 沒有 ctx 行 | **Windows FIXED（維持，掌舵者兩視窗肉眼）；Mac UNVERIFIED（未安裝、零真跑）** | `--status` installed／matches true、`python_basis repo-venv`、rc=0；`CLAUDE_CONFIG_DIR` 指 scratchpad 後 `--status` path 落該目錄、rc=1、真 settings.json mtime 前後皆 2026-09-28 11:39:09（415 生效）。批評者裁定：任何寫成單一「FIXED」的摘要都會誤導下一位讀者，須拆兩半。 | `~/.claude/settings.json` 每台各一份、不隨 clone 走 ⇒ Mac 大機率從未安裝；`build_command(windows=False)` 印 `/…/.venv/bin/python /…/tools/statusline_context_feed.py`（含空白路徑才加雙引號）；官方 statusLine 恆為 shell form、Mac 走 `sh -c`。QA-1：SOP 零提及 ⇒ DEF-200-422 補 useMacWin.md 一句。渲染那一環只有 Mac 肉眼能證。 |
| Q5 收斂了嗎 | **五問本體收斂；本輪再結三件（420／421／422）、418 走完第一步並維持 open** | 四方頂層 PARTIAL／OPEN 的理由全是本輪新抓的旁支（420／421／422／418 數字錯）；修完後帳本 open 列與五問相關者只剩 418（量測器射程債，帳本自載解鎖路徑，不阻斷五問）。〈七〉push 與雲端全綠前，批評者要求的詞是 OPEN；push 後見〈七〉。 | Mac 交棒任務書見〈八〉。 |

## 二、主控親測事實（本場 tool_result 逐字）

- HEAD=`d8b05db`=origin/main、工作樹 clean（動工前）。`--check`：`used 91,479／水位 9.1%／window 1,000,000／harness used=91,479 逐字稿 used=91,479 差=0`。`--pace`：`現在可派 4 個 agent｜band=free｜最緊的一條＝seven_day 43%`，reason 含 `gate_excluded=spend+weekly_scoped`、weekly_scoped note `burn-ahead+model-scoped-excluded`。
- 同一分鐘呼叫 Workflow，PreToolUse hook 印 `weekly_scoped 64% band=notice cap=4 model=Fable note=burn-ahead ⇒ cap=4 recommended=2 band=notice binding=weekly_scoped` 並擋下 ⇒ DEF-200-420 的主控親遇實例（反駁鏡 A 隨後真跑重現：`--pace` 可派 4／free／binding=seven_day，`--pace --model fable` 可派 0／notice／binding=weekly_scoped，七軸讀數逐字相同）。
- `install_statusline.py --status`：installed true／matches_current_checkout true／python_basis repo-venv／command=`D:/CursorProject/AISDCL_Agent/.venv/Scripts/pythonw.exe D:/CursorProject/AISDCL_Agent/tools/statusline_context_feed.py`、STATUS_RC=0。本視窗 SessionStart 簡報逐字含「statusLine：已安裝」與 `_RC2_CLARIFY_WINDOWS`。帳本 open 23 筆（412～417／419 fixed、418 open）；Claude Code 2.1.283。
- **SA-2 線索的主控追查**：feed 目錄孤兒檔 `5ebc8420-…json`（2026-09-28 21:53:17、`current_usage null`、`used_percentage null`、model Fable 5.1；全部 `~/.claude/projects/*` 遞迴無對應 `.jsonl`）；`-p` 的兩支 session（baac706f／34a91914）無 feed 檔 ⇒ statusLine 只在互動 TUI 啟動時被呼叫 ⇒ 5ebc8420＝一個互動視窗在 21:53:17 啟動、未送任何訊息即關閉，落在掌舵者回報「閃黑框」的 21:50～21:55 時窗——R182〈十〉未把「新視窗啟動」列為候選。
- **對照實驗**（零 agent）：`flash_watch.py --seconds 80` 盯著 `wt -w new -d <repo> claude` 啟動 30 秒後 Stop-Process：該 session `c7d891b2` 於 00:30:45 寫 feed（usage null）、無逐字稿＝同簽名；`flash_watch --report`：總視窗事件 20 筆、可見 console 承載者視窗事件 3 筆＝我開的那個 WT（`CASCADIA_HOSTING_WINDOW_CLASS` pid 37512）與 claude.exe 自己的 `PseudoConsoleWindow`（pid 36624，ppid=該 WT）——**零額外可見視窗**。誠實劃界：實驗父鏈是 WT（可見 console），掌舵者的視窗跑在 Antigravity IDE 整合終端（conhost --headless）；WMI `Win32_Process` 快照看不到已結束的短命子行程；批評者指出這只證「statusLine 隨互動啟動被呼叫且零額外視窗」這一環，不宣稱 21:53:17 那一下已定罪。下次最便宜的補實驗＝在 IDE 內「開新分頁」那個動作前同時武裝 `flash_watch.py`（零 spawn）與 WMI 監看器。
- 收尾親驗數字見〈六〉，全套／push／雲端見〈七〉。

## 三、四方分析、反駁鏡與完整性批評（摘要；各包 JSON 住 session 逐字稿）

| 發現 | 來源 | 鏡 A（重現） | 鏡 B（範圍治理） | 主控裁決 |
|---|---|---|---|---|
| ARCH-1＝SD-2 `--pace` 不推導 active_model（planner:1566 `model=args.model`，hook:1001-1010 會掃逐字稿） | Architect、SD 獨立命中 | 真跑：不帶 `--model` 印「可派 4／free／binding=seven_day」，`--model fable` 印「可派 0／notice／binding=weekly_scoped」，七軸讀數逐字相同 ⇒ 差異 100% 來自 active_model；既有測試零受影響；CONFIRMED P2 | 射程內（Q2 機制面）、帳本零命中、R98 裁決只管純函式層、repo 內已有「兩個出口說不同話」判例 `WindowUsageIsToldTheSameWayByBothOutletsTest`；CONFIRMED P2 | 立 **DEF-200-420**，Developer-A 同輪修（`harness_feed.active_model_of` ＋ planner 一行；`--model` 顯式優先、解不出維持保守排除） |
| ARCH-2（＋SD-4）`CLAUDE_CONFIG_DIR` 只有 install_statusline 認；probe 逐字稿站點硬寫 `~/.claude` | Architect、SD | 實測覆寫指空目錄後 `--check` 仍讀真家目錄（覆寫被忽略）；生產站點 4 處非 3 處（補 shell_command_corpus.py）；platform_utils.py 81/400、audit_session.py 532/750 餘裕充足；官方是否展開 `~` 未文件化；CONFIRMED P3 | 五問字面射程外、本機三層皆未設、修法會啟動護欄棘輪重釘 ⇒ 登記不修 P4 | 主控裁決**當場修**（能修就不延後；與 418 第一步併同一包只付一次重釘）：立 **DEF-200-421**，Developer-B 修（`platform_utils.claude_home()` SSOT、4 站點＋`settings_path()` 改接；批評者補抓第 5 站點 `test_doc_loc_baseline_freshness_r60.py` 防污染檢查亦改接；`endurance_env.py:358` 的 `~/.claude.json` 語意不同、不動） |
| ARCH-3＝SD-1 帳本 418「假紅 1」實為 3 | Architect（靜態）、SD（AST 判準複製品實跑：scanned 13 files, problems 3） | — | — | 兩方獨立同數，不另派鏡；418 第一步本輪做，帳本更正數字、維持 open |
| QA-1 statusLine 安裝不在 useMacWin.md／dev_start 任何步驟 | QA | 觀測面成立；「併入 dev_start」＝重開 R158 A3 刻意關閉的自動寫使用者全域設定檔管道 ⇒ 否決；PARTIAL P4 | 帳本零命中；只加文件一句、插在〈B〉步驟 1 之後；PARTIAL P4 | 立 **DEF-200-422**，Developer-Doc 同輪修（useMacWin.md 第 69 行行尾一句，五支文件鎖全綠） |
| SA-2 孤兒 feed 5ebc8420 | SA | 主控親查（〈二〉） | — | 不立 DEF；R182〈十〉歸因補一個候選＋對照實驗 |
| SA-3 slug 推導未在 Mac 核對 | SA | — | — | 不立 DEF（未證實）；入 Mac 交棒〈八〉 |
| SD-3 fail-open 方向 | SD | — | — | 登記不改（同目錄兄弟檔 import 失敗幾乎不可達；SD 自陳） |
| SA-4 sdk-cli session 不入 Q2 分母 | SA | — | — | 方法論註記 |

批評者（Sonnet，唯讀）：核實五項核心發現全部屬實無誇大；新增兩個修正點——`CLAUDE_CONFIG_DIR` 站點實為 5 個（補 `test_doc_loc_baseline_freshness_r60.py:6786`）、418 第一步不得用 glob 納整個 tools/probe（`_sources()` 檔頭自訂「全拉進來＝要逐一辯護的假紅」，`replay_r113_lastmile_driver.py` 只在文件字串提 subprocess.run）；裁定 Q1／Q4 用複合詞、Q5 在 push 前只能寫 OPEN；指出本輪無 wf_id（Workflow 被擋）打破 R179～R182 的可追溯慣例——本檔以「各包回報 JSON 摘錄」替代；Mac 交棒補 8 條可貼指令（已併〈八〉）；SA-2 對照實驗的推廣邊界（父鏈不同）如〈二〉。批評者「無法判」的項目（SA 計數的 commands_run）主控以 SA 回報的 `commands_run` 十三條核對，計數皆有對應腳本。

## 四、修法（Developer `[他包回報]`；主控收尾窗口親驗見〈六〉）

**DEF-200-420**（`tools/lib/harness_feed.py` +23、`tools/session_resume_planner.py` 1 行＋註解、`tools/tests/test_context_budget_guard.py` PaceAutoDerivesActiveModelTest 三格＋HarnessFeedStageTest 三格；Developer-A）
- `harness_feed.active_model_of(transcript, guard) -> str | None`：`transcript` 為 None／非檔案／掃描例外一律回 None（fail-soft＝維持「不確定 → 保守排除」）；否則 `guard.scan_transcript()` 取最後模型字面再 `guard.model_family()`——與 PreToolUse hook 同一組函式、同一條轉換規則。planner `--pace` 分支只改一行：`model=args.model or harness_feed.active_model_of(aim, guard)`（顯式 `--model` 優先；`aim=None` 時行為逐字同今天）。
- 紅端 `[他包回報]`：planner 改回舊行 → `'model-scoped-excluded' unexpectedly found in '現在可派 8 個 agent…'` FAIL；改回 → 3 格 OK。複審鏡 A（唯讀）：ACCEPT_WITH_SHOULD_FIX、must_fix 空；mutant 檢查 `[他包回報]`：baseline 0 failures／`active_model_of` 恆回 None → 1 failure／恆回 "fable" → 2 failures（三格對「沒接上」與「恆常誤判命中」兩種退化皆有鑑別力）；`dis.dis` 證 `(model_family(x) or None) if x else None` 求值序正確；`resolve_transcript()` 非遞迴 glob 不會掃到 subagent 分身；方向安全（逐字稿 opus＋快取 scope Fable 仍排除＝正確）。should_fix 三項主控收尾親修：① `--model` help 與 R98 註解改成「不給則先從逐字稿自動推導；解不出時模型分軌軸不進 cap、只出聲」；② 主控原本把該格的整段輸出比對改成只比 `⇒ cap=` 那一行，鏡 A 指出 `describe()` 把逐軸片語（含「剩 N 分鐘」）與 tail 接在同一行 ⇒ 改用正則只抽 `cap=／recommended=／band=／binding=` 四欄；③ 多一個空白行移除。
- 主控親改的另一處：鏡 A 抓到前，主控親讀 diff 已發現 `assertEqual(auto, explicit)` 比整段輸出含「剩 N 分鐘」、兩次呼叫相隔約 2.4 秒會跨分鐘邊界假紅——這是「先改成只比一行」的來源，鏡 A 再往前推一步。

**DEF-200-421**（`tools/lib/platform_utils.py` +29、`tools/install_statusline.py` +21/-6、`tools/probe/{audit_session,causal_form_census,reset_window_distribution,shell_command_corpus}.py`、`tools/tests/test_doc_loc_baseline_freshness_r60.py` +6、`tools/tests/test_platform_utils_dedup.py` +64、`tools/tests/test_install_statusline.py` +16；Developer-B）
- `platform_utils.claude_home(home=None)`：顯式 `home` → `home/.claude`（維持 install_statusline 既有測試語意）；否則 `CLAUDE_CONFIG_DIR` 去空白非空 → `Path(override)`；否則 `Path.home()/.claude`。`settings_path()` 延遲 import 該 SSOT（同 `statusline_context_feed._repo_venv_python()` 慣例）、失敗退回原地實作；四個 probe 站點改接 `claude_home()/"projects"`（各沿用該檔既有的 tools/lib import 慣例）；第 5 站點（防污染檢查的 `real`）同步改接，`base` 恆為 tempdir 故判準方向不變。
- 複審鏡 B（唯讀）：ACCEPT_WITH_SHOULD_FIX＋**一項 must_fix**——SSOT 對 override 做了 `.expanduser()`（Developer-B 新加）而 `settings_path()` 退回分支沒有，兩條路徑在值含 `~` 時分岔且退回分支零測試；且 WebSearch 證實官方對 `CLAUDE_CONFIG_DIR` 含 `~` 的處理未文件化。主控裁決：**拿掉 SSOT 的 `expanduser()`**（照字面用＝與 DEF-200-415 已鎖語意逐字相同；殼本來就會先展開未加引號的 `~`），並在 `test_install_statusline.py::ConfigDirOverrideTest` 補一格 `test_fallback_branch_matches_the_ssot_when_the_helper_import_fails`（`sys.modules["platform_utils"]=None` 逼 ImportError 走退回分支，env／顯式 home／純空白三態與 SSOT 逐字同值）。should_fix「其餘三站點缺消費端鎖」→ 主控補 `TestClaudeHome::test_every_transcript_consumer_names_the_ssot_and_no_hardwired_home`（五個消費端來源必含 `claude_home()`、程式碼行不得再出現硬寫 `Path.home() / ".claude"`；docstring 史料句以反引號／註解排除——第一版把 audit_session docstring 的「此前硬寫 `…`」當站點抓到，主控親撞後修正）。
- 紅端 `[他包回報]`：audit_session 改回 `Path.home()/".claude"` → `WindowsPath('C:/Users/wuwei/.claude/projects') != WindowsPath('…/Temp/tmpn4di8m0g/projects')` FAIL；改回 OK。鏡 B 攻擊 `[他包回報]`：`CLAUDE_CONFIG_DIR` 指向不存在目錄時 `TestR85DocNamedLiveCheckEntriesActuallyRun` 4 格仍 OK（`resolve()` 對不存在路徑仍回正規化絕對路徑，鑑別力未流失）；`test_platform_neutral_paths.py` 全檔 177 OK；`--check` rc=0（跨包 `from probe.audit_session import …` 未被破壞）。

**DEF-200-418 第一步**（`tools/tests/test_context_budget_guard.py` ConsoleFreeSpawnTest `_sources()`＋四行 assertIn、`tools/probe/{shell_command_corpus,xplat_hazard_census}.py` 補旗標、`tools/probe/xplat_injection_matrix.py` 具名豁免；Developer-B＋主控收尾）
- `_sources()` **策展式**新增四個 tools/probe 檔（不用 glob；鏡 B 以 Grep 全 tools/probe 對 `subprocess.(run|Popen|call|check_call|check_output)(` 與 `os.system/popen/spawn/exec` 普查：只命中這四支，策展零遺漏）。`shell_command_corpus.py`／`xplat_hazard_census.py` 的 `git ls-files`（capture_output、短命）補 `creationflags=NO_WINDOW`；Developer-B 原本三檔各複製一份 NO_WINDOW 表達式，鏡 B 指出 `tools/lib/win_spawn.py` 早有同一顆 SSOT（hook 自己也是 `from win_spawn import NO_WINDOW`，「probe 不得 import hook」的註解文不對題）⇒ 主控改成 `from win_spawn import NO_WINDOW`／`from lib.win_spawn import NO_WINDOW`。`xplat_injection_matrix._run()` 跑的是互動長跑關卡（全套 unittest／git hook）——鏡 B 指出 `CREATE_NEW_PROCESS_GROUP` 會讓子行程脫離主控台、Ctrl+C 傳不到 ⇒ 主控改為行尾具名豁免 `# no-window-ok: 互動長跑關卡（全套 unittest／git hook）要保留 Ctrl+C，DEF-200-418 逐站判`（豁免用 1／上限 2）——這正是帳本 418 自載的「須逐站點判」的第一個實例。
- 紅端 `[他包回報]`：拿掉 xplat_hazard_census 旗標 → `['tools/probe/xplat_hazard_census.py:84：subprocess spawn 沒有 creationflags=…'] != []` FAIL；改回 19 格 OK。`shell_command_corpus.py --summary --corpus tracked` 補旗標後 rc=0（母體 5579 筆）、`--corpus transcripts` rc=0（母體 3645 筆）。帳本 418 更正「假紅 1」為實測 3、記第一步已做，**維持 open**。

**DEF-200-422**（`useMacWin.md` 1 行；Developer-Doc）
- 〈B. 到達後〉步驟 1 行尾追加：簡報印「未安裝」或「已安裝但與本 checkout 不符」時，`<python> tools/install_statusline.py --dry-run` 預覽→安裝→開全新視窗肉眼看 `ctx NN%`；選配、刻意不併入 dev_start（會動使用者家目錄外的設定檔）。五支文件鎖 `[他包回報]`：`test_check_pytest_baseline_sites` 20 OK、`test_doc_env_prefix_platform_parity_r60` 13 OK、`test_skip_discoverability_r83` 26 OK、`test_doc_loc_baseline_freshness_r60` 281 OK、`test_adr_xplat001_c1c2_lock` 192 OK。鏡 B should_fix：句首 U+3000 全形空格（全檔唯一）⇒ 主控改半形。

## 五、方法論註記與誠實劃界

- **額度守衛 notice 帶**：Workflow 被 PreToolUse 擋下（理由「數不到」），全輪改逐個 `Agent`、每 300 秒 ≤4；四方→反駁鏡→批評者→Developer→複審的順序因此拉長，但每包 Sonnet 各 9～23 萬 tokens、主控只讀 JSON。
- **同一個缺陷被兩方獨立命中且有實跑才免派鏡**（ARCH-3＝SD-1）；單方命中一律兩鏡。
- **鏡 A／鏡 B 分歧時主控不平均**：ARCH-2 鏡 B「射程外只登記」的依據是成本（護欄棘輪重釘），不是真偽；與 418 第一步併包後成本攤平 ⇒ 採鏡 A。
- **鐵律七第 3 條**：複審期間主控不動工作樹（本輪照做：兩鏡皆收工後才進收尾單人窗口）；Developer-A 與 Developer-B 同持有面（`test_context_budget_guard.py`／`shell_command_corpus.py`）串行派工。
- **對照實驗的推廣邊界**：〈二〉的 WT 父鏈 ≠ 掌舵者的 conhost --headless 父鏈；本輪只證「statusLine 隨互動啟動被呼叫且零額外視窗」這一環。
- **主控自己的坑**：① `Select-String -Context` 對 `ConvertTo-Json` 拆行陣列會印成一串 `1`（兩次），LOC 餘裕改由反駁鏡用 python 讀 JSON；② 帳本列 418 更新後 702 bytes 撞 700 上限，削「非 1」三字才過；③ 靜態站點鎖第一版把 docstring 史料句當站點；④ 三個行寬紅（豁免註解行 150、planner 註解 107、測試 lambda 行讓 tools/tests 過長行 139→140）全部折行才過。
- **Q4 最後一環**：Windows 兩視窗肉眼已閉合；Mac 只有〈八〉能證。

## 六、收尾親驗（主控本場真跑，rc 逐字）

- 單檔鎖（收尾修改定稿後）：`test_install_statusline.py` `Ran 36 tests … OK` RC=0；`test_platform_utils_dedup.py` `Ran 39 tests … OK` RC=0；`test_context_budget_guard.py -k ConsoleFreeSpawn -k PaceAutoDerivesActiveModelTest` `Ran 22 tests … OK` RC=0（另 `-k active_model_of` 併跑 25 格 OK）；`test_subprocess_encoding_hygiene.py -k test_e501_debt_only_shrinks` `Ran 1 test … OK` RC=0（折行前一度 `140 not less than or equal to 139` 紅）；ruff 14 檔 `All checks passed!` RC=0（折行前兩個 E501：`xplat_injection_matrix.py:212 150>100`、`session_resume_planner.py:901 107>100`）；`xplat_hazard_census.py --help` RC=0、`xplat_injection_matrix.py --help` RC=0、`shell_command_corpus.py --summary --corpus tracked` RC=0（`[tracked] 母體 5580 筆／去重後 5223 種唯一字面`）；`check_loc_budget.py --json` root_tools_violations=[]／special_violations=[]／total_violation=False。
- 護欄棘輪重釘：`--print-guard-lines` 第一次 `淨額 108070→108264 (+194)`、逐檔漂移 4 支（test_context_budget_guard.py 12828→12936 +108、test_doc_loc_baseline_freshness_r60.py 7171→7177 +6、test_install_statusline.py 430→446 +16、test_platform_utils_dedup.py 1078→1142 +64）；填主列＋收斂列＋回歸鎖軌列＋接鏈列後第二次 `108264→108285 (+21)`（本表自身）；U9 到期輪具名展延 183→188 與 Phase2 `[維持觀察]` 到期列（兩道到期鎖皆因輪號走到 R183 觸發）再漂 +9 ⇒ 收斂列 30、本表 9072，最後一次 `108294→108294 (+0)`、`逐檔漂移 0 支`、sha `bd1f875e0ceb…`（全套第一跑抓到 tools/tests 過長行 139→141＝本表 R183 主列註解與收斂列兩行東亞寬度超 100，原地改短不換行後 sha 重取）；凍結前綴 311→313；doc-total 兩站點（`CrossPlatform_R145_Scan_Findings.md`〈附記（R183）〉、`AutoSDD_improving_112.md` 尾列）記整輪合計 108070→108294（+224）。
- 帳本：420（699 bytes）／421（679）／422（640）三列新增、418 列更新（647；第一版 702 撞 700 上限、第二版因交叉參照硬規則補「承接輪次：**未指派**」），皆 7 欄、「發現情境」欄零輪號字面；`governance_docs.py` 登記本檔。
- 其餘鎖與全套見〈七〉。

## 七、根層全套、push 與雲端驗收

- 收尾鎖組（主控本場真跑）：`check_defect_log_crossref.py` 第一次 rc=1（418 列缺「承接輪次：**未指派**」字面＝散文式延後，補上後 rc=0）；`archive_defect_log.py --check` rc=0（70 檔／1532 個 ID）；`sync_onboarding_baselines.py --check-snapshot` rc=0；`test_adr_xplat001_c1c2_lock.py` 第一次 `FAILED (failures=2)`——兩道到期鎖皆因輪號走到 R183 觸發：`[時效逾期] 稽核痕跡已走到 R183，超過到期輪 R182（末列 R177 ＋ 視窗 5 輪）`（Phase2 §6 ⇒ 追加 `(183, "[維持觀察]")` 列，上一列 R177 是 [提案] 故計數歸零後為一）與 `[技術債逾期] ADR-XPLAT-013 §9.3／U9 … 到期輪已是 R183`（具名展延 183→188，理由逐字寫在常數上方）；修後 `Ran 192 tests … OK` rc=0；`test_doc_loc_baseline_freshness_r60.py` `Ran 281 tests … OK` rc=0。
- 根層全套第一跑（`tools/run_root_unittests.py`，worker=18）：`✅ unittest 數量下限釘選通過：發現 4710 個測試（下限 4697）`、`1 failures`＝`test_e501_debt_only_shrinks` `141 not less than or equal to 139`（本表 R183 主列註解行與收斂列兩行東亞寬度超 100）⇒ 原地改短不換行（棘輪 +0 不動、sha 重取 `bd1f875e0ceb…`）；第二跑 `發現 4710 個測試（下限 4697）`／`slot 利用率=99.8%`／`✅ 孤兒 console 普查：零增長（前 0／後 0）`／`RUNNER2_RC=0`、零 FAIL；skip census 46 支（platform 42／env-disabled 4，與 R182 同）。
- commit `a0107b4`（21 files changed, 504 insertions(+), 29 deletions(-)；pre-commit 過）；push `d8b05db..a0107b4  main -> main`、`[pre-push dispatcher] ✅ 本次 push 觸發的所有 leg 皆通過（rc=0）`、`PUSH_RC=0`；`git rev-parse HEAD`＝`origin/main`＝`a0107b410907cde60d825f512502bb1fb51fcea3`。§7 表② Windows 欄指紋相符（v001=8ffe3c3dabbd／v030=4d902e4a743a／scripts=ec35ee2838d0／autoclaude=35adf49caea0）；macOS 欄上次量測 2026-09-27、此後 2/4 棵樹已變動＝單機交替常態，Mac 輪回填（〈八〉第 5 步）。
- 雲端（`gh run list --commit a0107b410907cde60d825f512502bb1fb51fcea3 --json name,status,conclusion,databaseId,createdAt` 背景輪詢至全部 completed，主控本場 tool_result 逐字）：`root-infra-ci` 36461220011 **success**、`windows-compat-ci` 36461220088 **success**、`macos-compat-ci` 36461220032 **success**、`AutoClaude CI` 36461220014 **success**（四支皆 createdAt 2026-09-28T17:52:31Z；`aisdlc-sdd-ci` 依路徑未觸發）。Q5 至此可寫「五問本體收斂」：本輪四個修法全部經全套 4710 支 rc=0、push 與雲端四支 success；帳本 open 列與五問相關者只剩 418（承接輪次未指派、第一步已做）。本節為 push 後回填，隨後以 docs commit 再 push 一次。

## 八、Mac 交棒——下輪第一個新視窗的任務書（掌舵者：「下輪要在MAC執行!」）

> 四條件：① 工作樹狀態確定（見〈七〉HEAD／origin 一致、clean）；② 本節即任務書；③ 已驗證什麼見〈六〉〈七〉、還沒做什麼＝下列 Mac 面全部、確切指令如下、禁止事項見末；④ 到 Mac 後第一件事是**重驗**，不採信本檔任何「已通過」宣稱。

**0. 離開 Windows 前（本輪收尾已做）**：`git status --porcelain --untracked-files=all` 無輸出；`git rev-list --left-right --count origin/main...main`＝`0	0`；`git stash list` 無輸出；雲端 run 結論見〈七〉（未回來的 run 把 headSha 帶到 Mac 對帳）。

**1. 開場（順序不可調）**：useMacWin.md〈啟動提示詞〉第 1～2 步（git ff-only 同步 → `source tools/dev_start.sh`，timeout 10 分）；讀 dev_start 摘要與 SessionStart 簡報——簡報應印 POSIX 版澄清句（含「Bash」、不得含「PowerShell」）與「statusLine：未安裝（安裝：…）」（Mac 這台大機率從未裝過）。

**2. hook 載具正面現查（沒命中＝POSIX 載具設計在 mac 失效，先修再往下）**
```bash
test -x "$(git rev-parse --show-toplevel)/.venv/bin/python" && echo carrier-ok
readlink "$(git rev-parse --show-toplevel)/.venv/Scripts/pythonw.exe"      # 應印 ../bin/python
claude -p --model haiku --debug hooks --debug-file h.log "ok"; grep 'Hook SessionStart.*success' h.log; rm h.log
```

**3. 五問 Mac 面逐一親驗（每條都是本輪只在 Windows 驗過、Mac 零真跑的那一環）**
- Q2／Q3（新視窗第一動作；用 .venv 直譯器，不用裸 python）：
  ```bash
  "$(git rev-parse --show-toplevel)/.venv/bin/python" tools/session_resume_planner.py --check
  "$(git rev-parse --show-toplevel)/.venv/bin/python" tools/session_resume_planner.py --pace
  ```
  `--check` 的「harness used／逐字稿 used／差」：差≠0 時等工具跑完再量一次應歸 0；`--pace` 的 cap／band 應與同視窗 SessionStart 簡報的額度行一致（DEF-200-420 在 Mac 的重現點：若 CLI 比簡報寬鬆，先懷疑自動推導沒接上）。
- Q3 附加（SA-3：逐字稿 slug 推導只在 Windows 觀察過、測試循環驗證）：
  ```bash
  ls "$HOME/.claude/projects" | grep -i "$(basename "$(git rev-parse --show-toplevel)" | tr -c 'A-Za-z0-9\n' '-')"
  "$(git rev-parse --show-toplevel)/.venv/bin/python" -c "import sys; sys.path.insert(0,'tools/probe'); from audit_session import project_transcript_dir; from pathlib import Path; print(project_transcript_dir(Path.cwd()))"
  ```
  兩者不吻合＝新缺陷（`--check` 會 fail-loud 找不到逐字稿，體感像 Q1／Q2）；吻合才可信任 `--check` 的數字。
- Q4（Mac 的 `~/.claude/settings.json` 是另一份檔、Windows 側裝的不會跟過去；官方 statusLine 恆為 shell form、Mac 走 `sh -c`）：
  ```bash
  "$(git rev-parse --show-toplevel)/.venv/bin/python" tools/install_statusline.py --status      # 預期首次 installed false、rc=1
  "$(git rev-parse --show-toplevel)/.venv/bin/python" tools/install_statusline.py --dry-run     # command 應為 <repo>/.venv/bin/python <repo>/tools/statusline_context_feed.py（含空白路徑才加雙引號）
  "$(git rev-parse --show-toplevel)/.venv/bin/python" tools/install_statusline.py               # 安裝（只動 statusLine 鍵、先備份）
  "$(git rev-parse --show-toplevel)/.venv/bin/python" tools/install_statusline.py --status      # 預期 installed true／matches true／python_basis repo-venv、rc=0
  ```
  然後開一個**全新** claude 視窗：肉眼看最下方 `ctx NN% X.Xk/1.0m | <model>`（整數、無 .0）、SessionStart 簡報改印「statusLine：已安裝」。渲染那一環只有肉眼能證。
- Q1（Mac 上 Bash 是正確載具，`block_bash_on_windows.py` 非 Windows exit 0）：刻意跑一次 Bash 工具（如 `ls`）確認放行；另驗 POSIX 澄清句：
  ```bash
  "$(git rev-parse --show-toplevel)/.venv/bin/python" -c "import sys; sys.path.insert(0,'tools/lib'); import quota_messages as qm, session_brief as sb; print(qm.halt_convergent_clarification()); print(sb.rc2_clarify())"
  # 期望：含「Read／Write／Edit／Bash／git」、不含「PowerShell」、不含「鐵律一 hook 停用」
  ```
- DEF-200-421（`claude_home()` 在 Mac 的語意）：
  ```bash
  "$(git rev-parse --show-toplevel)/.venv/bin/python" -c "import sys; sys.path.insert(0,'tools/lib'); import platform_utils as pu; print(pu.claude_home())"
  CLAUDE_CONFIG_DIR=/tmp/probe-cfg "$(git rev-parse --show-toplevel)/.venv/bin/python" -c "import sys; sys.path.insert(0,'tools/lib'); import platform_utils as pu; print(pu.claude_home())"
  # 期望：第一行 $HOME/.claude、第二行 /tmp/probe-cfg
  ```
- Q5：`grep -c '| open' docs/06_quality/AutoSDD_Defect_Log.md` 現查 open 列數並與〈七〉交接數對帳。

**4. 雲端對帳（不要沿用本檔的舊 headSha 當當下驗收）**
```bash
gh run list --branch main --workflow macos-compat-ci.yml --limit 5 --json databaseId,conclusion,headSha,createdAt
gh run view <run-id> --log | grep -E 'PaceAutoDerivesActiveModelTest|HaltConvergentClarificationPlatformTest|ConfigDirOverrideTest|ConsoleFreeSpawnTest|TestClaudeHome'   # 新 class 真的被 mac runner 跑到、非被 skip census 濾掉
```

**5. 全套閘門確立 Mac 基線（useMacWin §B 第 2 步），紅燈在這步清完；再做 ONBOARDING §7 表② 回填**
```bash
"$(git rev-parse --show-toplevel)/.venv/bin/python" tools/lib/clean_venv_carrier.py   # 前提 docker info 印得出版本；不准 --allow-pg-extras
```

**6. 已知跨機事實**：Windows 這台每晚 22:30 nightly 會重鎖 `AutoClaude/.perf_baseline.toml` 讓工作樹變髒——回到 Windows 時先回收再 merge；Mac 睡著不會被喚醒（`pmset -g custom` 現查，不寫成常數）；`test_context_budget_guard.py` 內 Windows 專屬 class（NoWindowBehaviour／flash_watch 活體）在 Mac 會 skip，注意 skip census 天花板。

**禁止事項**：不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准裸 `git stash`／`git checkout --`／`reset --hard`（hook 會擋，且是設計；`.perf_baseline.toml` 漂移用 Edit 還原）；不准把 Windows 側的 `ctx` 行判定拿來當 Mac 已驗證；不准用裸 `python`／`python3` 跑 repo 工具（pyenv shim／系統版本可能不是 3.11+，`install_statusline.py` 用了 `datetime.UTC`）；帳本「發現情境」欄不准寫輪號字面。

## 九、掌舵者側待辦（只有本人能做）

1. 下輪在 Mac 開第一個視窗時，把〈八〉整節當任務書貼給模型（或指名本檔）；Q4 的 `ctx` 行只有你的肉眼能簽收。
2. 若在 Windows 再看到閃黑框：依 R182〈十〉10.4 三步取證，本輪補一條——先掛 `flash_watch.py` 再在 IDE 內「開新分頁／新視窗」，量的是那個動作本身。
