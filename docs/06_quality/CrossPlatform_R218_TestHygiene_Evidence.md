# CrossPlatform R218 測試衛生證據（HYG1：DEF-200-647／648；C 項調查＝DEF-200-649）

> 範圍：根層 `tools/tests` 的兩類「環境汙染造成的假紅」與一個守衛面誤判的調查。三項皆出自 2026-11-24～25 真實事件，非構造性。

## DEF-200-647：全 repo 掃描器把 `.claude/worktrees/` 的代理副本當本體掃

- **症狀**：2026-11-24 主樹 `test_platform_neutral_paths` 站點普查 `{'live': 1205} != {'live': 37}`；同日 22:30 AutoClaude_Nightly `local_ci_gate=1`，`AutoClaude/logs/nightly_2026-11-24_223001.log` 約 814～907 行列出 6 處斷言（`test_check_hooks_liveness` 兩支、`test_mac_endurance_r83` 三支、`test_platform_neutral_paths` 一支），路徑全是 `.claude/worktrees/agent-*/…`。
- **成因**：Agent 工具 `isolation: worktree` 把整份 repo 副本建在 `<repo>/.claude/worktrees/<name>/`（gitignored）。以檔案系統走訪（`rglob`）從 repo 根或 `.claude/` 起掃的測試，把副本當本體掃；代理在飛或 worktree 未移除期間，主樹全套與 nightly 必假紅。副本移除後自癒，所以只在「有代理在跑」的時段出現、難重現。
- **修法（消除成因）**：`tools/lib/worktree_paths.py` 新增唯一排除入口 `rglob_live(repo_root, pattern, base=None)` 與純字面判斷 `is_disposable_worktree_rel`（錨定 repo 根、NTFS 大小寫不敏感）。五個站點改走它：`test_platform_neutral_paths`（`_pathext_scan_files`、站點普查）、`test_mac_endurance_r83`（`_carrier_scan_surface`、`_outside_consumers`）、`test_check_hooks_liveness`（`_action_scan_sources`）、`test_python_c_percent_shim`（`_iter_ps1_files`）。掃描根是 `tools/`、`tools/lib/`、`.claude/hooks` 等子樹者副本不在其下，不需處理。
- **不選的做法**：各處自帶一份 `if "worktrees" in parts`（會是第 N+1 份複本、新掃描器照抄舊寫法即復發）；改 `.gitignore`（掃描器走檔案系統、不看 gitignore）。
- **回歸鎖**：`tools/tests/test_worktree_paths.py::TestRglobLiveSkipsAgentWorktreeCopies`——①對照組證明夾具確實讓裸 `rglob` 掃進副本；②`rglob_live` 與無副本 repo 的掃描集合相等；③五支真實掃描器（把各模組 `_REPO_ROOT` 指到夾具 repo）有／無副本結果相同；④結構鎖：`tools/tests`、`tools/lib` 不得再出現 repo 根名稱直接 `.rglob(`。
- **紅綠自證（當回合）**：修前在主樹 `.claude/worktrees/probe/` 造真副本（`tools`、`.claude/hooks`、`AutoClaude/tools`、`AISDLC_SDD/scripts`、`.github` 共 1095 檔）跑根層全套，恰為與 nightly 同一組 6 紅；修後同副本在位，這六支與 `TestPathextReadsAreePlatformGuarded`、`test_python_c_percent_shim` 全綠（55 案例）。把 `_pathext_scan_files` 暫時改回裸 `rglob`，新鎖轉紅（`pathext：副本改變了掃描結果`＋結構鎖），還原後綠。

## DEF-200-648：沙盒 git 背景自動維護與 teardown rmtree 競速

- **實例**：macOS CI run 45427135743 attempt 2，`test_openitems_gate` teardown 的 `rmtree` 撞 `.git/objects/maintenance.lock` FileNotFoundError（`git commit` 之後 git 起 detached `maintenance run --auto`／`gc --auto`）。單點修法已在 `test_openitems_gate._git`（`-c maintenance.auto=false -c gc.auto=0`）。
- **類別面**：`tools/tests` 另有約 55 處 `["git", "-C", …]` 子行程、46 處 `init`；逐處抄 `-c` 是把同一件事抄 55 次，下一個新站點照樣漏。
- **否決的集中做法**：runner 設 `GIT_CONFIG_COUNT`／`KEY_n`／`VALUE_n`——`tools/lib/selfimproving/pushcontent.py` 與 `git.py::ENV_RULES` 把行程環境內任何 `GIT_CONFIG_*` 視為設定注入而拒絕，SelfImproving 推送守門那一族測試會整批改判。
- **修法**：新 `tools/lib/git_sandbox_fence.py::fence`，`tools/run_root_unittests.py` 的 `main()` 在 `temp_fence` 內層、`run_with_floor` 外層包它（同一行內加一層，零行數成本）。它組一份 git 模板目錄（底＝呼叫端自設的 `GIT_TEMPLATE_DIR` 否則 git 預設模板，再疊 `config`：`maintenance.auto=false`、`gc.auto=0`）並設 `GIT_TEMPLATE_DIR`；`git init`／`git clone` 建的 repo，`.git/config` 一出生就帶這兩鍵，之後無論哪個 helper、帶不帶 `-c` 都吃得到。runner 是 pre-push／nightly／三支 CI 共同入口；平行 worker 與測試子行程皆繼承環境。
- **誠實劃界**：單檔直跑 `python -m unittest <檔>` 不經 runner、不受圍籬（與修前相同）；只管新建 repo（複製既有 `.git` 的不涵蓋）；`test_openitems_gate._git` 的 `-c` 保留當第二層（不是遺留物：單檔直跑時它是唯一防線）。
- **回歸鎖**：`tools/tests/test_run_root_unittests.py::GitSandboxFenceTest`——真 `git init` 對照（圍籬內 local 設定有兩鍵、圍籬外沒有）、環境還原（含原本沒設／原本有設／例外）、呼叫端模板疊加不被吞、runner 接線 AST 鎖（`fence` 在 `temp_fence` 內、`run_with_floor` 外）。
- **連動**：`windows-compat-ci.yml`／`macos-compat-ci.yml` 兩段 `paths` 各加 `tools/lib/git_sandbox_fence.py`（tools/tests 經 runner 消費）。

## C 項（只調查）：leak_fence 把「真系統同時段自行重排的排程」判成測試洩漏 → DEF-200-649

- **事實**：2026-11-24 23:21 推送期間，真排程 `AutoSDD_OpenItem_OI-20261120-003` 到點由真 driver 自我重登記為 `AutoSDD_OpenItem_OI-20261120-003_202611250522`（`docs/06_quality/OpenItems_Event_Ledger.jsonl` 第 221 列：`ev=drive`、`by=driver:OI-20261120-003`、`ts=2026-11-24T23:21:03+08:00`、`task` 即該新 label）。pre-push 的 `sentinel_lifecycle.leak_fence` 以 `AutoSDD_*` 前後差集判死，把它當測試洩漏，rc 非零。
- **判準現況**（`tools/lib/sentinel_lifecycle.py::leak_fence`）：判死＝`run()` 前後 `list_jobs("AutoSDD_")` 的差集，唯一豁免是 `_live_armed`——label 內含 session id 且該 session 在圍籬起點後有真實對話記錄。OpenItem label 沒有 session id（`session_of()` 回 None），結構上進不了豁免。
- **能否在不放寬下區分**：能。測試種下的假 job 不會在**真** `OpenItems_Event_Ledger.jsonl` 留 `ev=drive` 事件（測試的帳本都在暫存根），而真 driver 重排必留。把「圍籬期間（`ts` ≥ 圍籬起點）、帳本記載由真 driver 登記的 `task` label」併進 `_live_armed` 的豁免（同樣只出聲不判死）即可：測試假 job 仍判死；沒有帳本證據的新增 job 仍判死；讀不到帳本一律不脫罪。
- **處置**：判準住守衛面（`tools/lib/sentinel_lifecycle.py` 在〈守衛面准入〉清單內），本包不改。暴露證據已齊（真機 pre-push 實際發生＋帳本第 221 列），立案 DEF-200-649 為 open，承接＝另派守衛面專棒（需附本節判準與暴露證據，並照准入規則附 WHY）。

## D 項：DEF-200-649 修復（D649）

- **准入**：暴露證據＝OI 事件帳本第 221 列（`ev=drive`、2026-11-24 23:21:03）＋pre-push 實際被 leak_fence 判紅，符合〈守衛面准入〉「真實發生」。
- **修法（消除成因）**：`sentinel_lifecycle.py` 新增 `_driver_rearmed(labels, since, ledger)`，併入 `leak_fence` 既有 `live` 豁免（同樣只出聲、不判死、痕跡記 `live_session_jobs`）。命中條件須同時成立：`ev=drive`、`by` 以 `driver:` 開頭、`task` 等於新增 label、`ts` ≥ 圍籬起點。人工 `by=human`、他 label、事件早於圍籬、空帳、檔不存在、壞行一律不脫罪。判準放在既有判準模組，不開第二套；`OI_LEDGER_REL` 與 `openitems/params.py::LEDGER_REL` 以文字鎖相等（該套件是 `from lib import` 脈絡，平面匯入不跨）。
- **WHY 不是放寬**：測試的 OpenItem 帳本都在暫存根，從不寫真帳本的 drive 事件；真 driver 重排必寫。唯一能讓假 job 脫罪的方式是它自己寫進真 repo 帳本，那已不是測試洩漏。
- **回歸鎖**：`tools/tests/test_context_budget_guard.py::LeakFenceTest` 新增三案。紅綠自證：暫時把併入行改成 `live += [] and …`，真 driver 重排案轉紅（`1 != 0`），還原後 13 案全綠。

## E 項：DEF-200-650 statusline smoke 間歇紅（FLK1）

- **症狀**：2026-11-25 兩次真實發生（D649 代理首跑根層全套；主控 push 的 pre-push）：`RealProcessSmokeTest.test_statusline_prints_no_watch_then_watch_ok_from_a_real_heartbeat` 得 `ctx 11% 5/1.0m | Opus`，`ctl:` 整段缺席；單檔跑恆綠。
- **重現**：測試側載具在真子行程包住 `controlfacts.control_state`／`segment` 印耗時與例外（不改產品碼），照該測試夾具建居所、每次清快取，與並行根層全套同時跑 120 次：1 次命中，`SEG_MS=161.8 SEG=''`、沒有 `STATE_MS` 行（取數在時限內沒做完），無任何例外。閒置時取數 4～10 ms、冷啟動首次 18 ms；48 支燒機行程下冷啟動 121 ms。
- **成因**：`controlfacts.segment` 的 150 ms 牆鐘時限（DES §6.5，產品預算，逾時回空且不寫快取，`SegmentCacheTest` 已以注入縫確定性驗過）。smoke 卻在真子行程裡依賴這個預算一定夠用，並行全套的排程飢餓讓它偶爾不夠。不是產品缺陷：status line 在慢機器上不顯示區段正是設計。
- **修法**：smoke 改經 `run_statusline`（`python -c` 開機碼以 runpy 跑真腳本 `__main__`，只把區段時限換成 60 秒，其餘 stdin→main→ctl_segment→真檔全照跑）。產品碼、預算、斷言都沒動。
- **回歸鎖**：`test_flk1_smoke_carrier_survives_a_machine_slower_than_the_product_budget`：取數注入 450 ms 延遲，保留產品時限的同一載具必得 `ctx 11% 5/1.0m | Opus`（載具觸發得到病），換 smoke 時限則印 `ctl: 1 agent NO WATCH`。紅綠自證：把 `run_statusline` 預設時限改回產品值，該案以與真實紅逐字相同的訊息轉紅，還原後全綠。


## F 項：CLOSE3（DEF-200-651、DEF-200-652）與帳本輪替後的列數斷言

- **症狀**：2026-11-25 推送 `7b66ccd6`（缺陷帳本歸檔輪替 archive_69）時 pre-push 根層全套 3 紅：AT-749-9-2「測試載具沒看到 hook 的孫行程（sleep），鑑別力不成立」、`SwitchPlanCliTest.test_real_process_smoke` 得 `PARK_UNTIL`、`test_AT_IC_01_4_2` 主檔列數 82 不大於 100。
- **列數斷言**：該斷言的目的是擋「讀到 0 列的假綠」；主檔會因歸檔輪替變小，門檻改為 `> 0`，目的不變。
- **DEF-200-652 成因**：smoke 子行程的額度快取目錄是空的 ⇒ `quota_gate.pace_state` 取得補量名額，以真 `~/.claude/.credentials.json` 打 `/api/oauth/usage`，讀到當下真短窗%；推送當時短窗達準備門檻 ⇒ `PARK_UNTIL`。只圍快取目錄與 TEMP 擋不住這條線上補量（探針實測：圍完仍讀到 `short_pct=7.0`、`weekly_pct=42.0`）。**修法**：子行程 `CLAUDE_CONFIG_DIR` 指到測試暫存（`platform_utils.claude_home` 的 SSOT）⇒ 憑證讀不到、不連線、額度軸量不到。新增斷言 `short_pct`／`weekly_pct` 皆為 `None`：任何真額度滲入都會紅，不必等到真額度剛好高。紅綠自證：拿掉該行即紅（`(9.0, 42.0) != (None, None)`），還原即綠。
- **DEF-200-651 成因**：舊載具用背景執行緒每 0.5 秒以 `Get-CimInstance` 查一次行程表；孫行程只活在「hook 起來」到「牆鐘 3 秒砍樹」之間。時間線探針（包住 `sleeper_pids` 記每次查詢起訖與命中）：閒置時活著的窗口約 2.3 秒、可命中 3～4 次；60 支燒機行程＋6 條 CIM 查詢迴圈下，單次查詢最長 2.53 秒、命中降到 1 次（4 次中 3 次只剩 1 次命中）。並行全套下守門 git 呼叫把 hook 推遲、查詢又更慢，查詢窗整個落在砍樹之後 ⇒ `seen` 為空。產品（`runner.run_argv` 逾時砍樹）沒有缺陷，缺陷在觀測與砍樹賽跑。
- **修法（結構正解）**：測試把 `runner._timeout_kill` 包一層：逾時那一刻先查到孫行程（上界 `SEEN_GATE_SECONDS=20`，小於孫行程的 27.31 秒）才呼叫真的砍樹。觀測不再跟砍樹賽跑；hook 起得晚也能等到。量 `run_argv` 耗時時扣掉這段等待，(ii)「逾時＋寬限內返回」的鑑別力不變。產品碼、牆鐘、寬限、斷言門檻都沒動。
- **回歸鎖**：`test_DEF_200_651_kill_is_judged_even_when_the_hook_is_late_past_the_wall`：hook 先睡 4.07 秒（超過牆鐘）才生出帶標記的孫行程，把「負載下 hook 起得晚」做成確定性輸入。紅綠自證：把 `SEEN_GATE_SECONDS` 改成 0（砍樹不等觀測，等同舊載具），該案以與真實紅逐字相同的訊息轉紅；還原後 `TestLockAndWall` 6 案全綠。

## G 項：DEF-200-654 整檔直跑兩支 `_run_resume` 類紅（FLK2）

- **症狀**：2026-11-26 主控在 WP-QV 合入後（HEAD `5fe81290`）整檔直跑 `test_context_budget_guard.py` 兩紅：`RunResumeOtherDriverTest`〔近期有人打字〕`(1, 1, True) != (1, 0, True)`、`RunResumeWritesHandbackPathIntoStateTest` 的 `[] != [(1, '--resume-tick')]`；`-k` 單跑恆綠。本棒照原指令重跑三次皆重現。
- **重現探針**（scratchpad，不改產品碼）：在兩類 `setUp` 後包住 `subprocess.run`，非 git 呼叫印 argv 與堆疊 ⇒ 被數成 spawn 的那一次是 `powershell.exe … Get-ScheduledTask`，來自 `choose_resume_route` → `handoff.ensure_mechanical` → `handoff_build._schedule_rows`；選路紀錄為 FRESH，理由「週軸 weekly_all=81%、seven_day=81% 已達 converge 帶」。逐支比對 `quota_meter.cache_path()` 內容雜湊 ⇒ 唯一改寫模組共用圍籬快取的是 `ArmedPlanStepThreeTest.test_the_resume_prompt_points_a_todo_section_three_at_the_handback_and_memory`，寫入 `source=endpoint`、與開發機真快取同值的讀數；環境變數逐支比對零洩漏。
- **成因**：WP-QV 把交接包額度欄的預設取數從只讀快取改為 `ruling_io.current` → `gather` → `pace_state`（設計 C14，產品行為不改）。該測試走 FRESH 支線時圍籬快取是空的、補量名額可搶 ⇒ 以真憑證打額度端點，再把真讀數寫進本模組共用的圍籬快取；180 秒內後面兩類讀到真週軸 ≥ converge ⇒ 改走 FRESH ⇒ 多一次真排程查詢被數成 spawn、`_fake_run` 在 spawn 前快照之前就寫了 scratch（判準④ files_changed 歸零）。綠紅取決於真週軸當下高低與快取新鮮度，所以 WP-QV 乾淨 worktree 那次沒紅。
- **修法（測試側結構正解）**：①模組圍籬 `_pin_handoff_hermetic`（掛在 `_pin_sentinel_off`，巢狀補釘同路）把 `ensure_mechanical` 的兩縫換成零副作用版本——排程列舉只准 git、其餘 rc 127，額度欄只讀快取——交接包其餘欄位照真函式產生，本模組所有 FRESH 選路一次罩住；②兩支 `_run_resume` 類宣告專屬空額度快取（與既有 `AUTOSDD_QUOTA_CACHE_DIR` 隔離類同形），選路輸入不再取自共用快取。產品碼、斷言、門檻都沒動，沒加 retry／skip。
- **回歸鎖**：`Flk2HermeticResumeRouteTest` 三案：圍籬在時 FRESH 支線零端點、零非 git 行程；注入組拔掉圍籬，同一呼叫必打端點（Windows 另起排程查詢）；共用快取種週軸 95% 並拔掉圍籬時兩類照樣綠。紅綠自證：拿掉兩類的專屬快取 ⇒ 第三案以與真實紅同形的兩筆失敗轉紅；拿掉模組圍籬 ⇒ 第一案 `([(4,)], [['powershell.exe']]) != ([], [])`；還原後三案與兩類全綠。

## H 項：DEF-200-656 windows-compat-ci 分片 3/3 的 E2E-AP-QV-10 `stderr` 為 None（FLK3）

- **症狀**：GitHub windows-compat-ci run 45761837270（commit `33ea299d`）分片 3/3 唯一紅：`SingleHouseLockE2ETest.test_e2e_ap_qv_10_planted_site_turns_the_real_lock_red` 第 893 行 `red.stderr[-800:]` → `TypeError: 'NoneType' object is not subscriptable`。本機全套未重現。
- **排除**：根層 runner 每個派工單位各起一個子行程（`tools/lib/parallel_shard.py` 的 Popen），別的模組換掉 `subprocess.run` 不可能外洩進來；本檔自身也沒有替換 `subprocess.run`。斷言訊息參數是先求值的，所以 None 並不代表 rc 為 0——「植入站點沒讓鎖紅」這個推測不成立。
- **成因**：E2E 的子行程 `python -m unittest …` 以繼承的環境啟動；CI runner 沒有 `PYTHONUTF8`／`PYTHONIOENCODING`，子行程 stderr 用 locale 碼頁寫斷言訊息裡的中文，父端以 `encoding="utf-8"` 解碼。Windows 的 `subprocess._communicate` 用讀取執行緒解碼，解碼失敗時執行緒死掉、緩衝是空的，回傳值就是 `stderr=None`（不拋例外）。本機殼層設了 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8:surrogateescape`，所以看不到。
- **重現**：同一台開發機移除這兩個變數後單跑該類 ⇒ 讀取執行緒印 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa1`，測試以與 CI 逐字相同的 `TypeError` 失敗。
- **修法（消除成因）**：子行程環境改由 `_utf8_child_env` 產生：清空 `PYTHONPATH`（原本的沙盒密閉）並強制 `PYTHONUTF8=1`＋`PYTHONIOENCODING=utf-8`。兩個都要：`PYTHONIOENCODING` 優先序高於 UTF-8 模式，只設 `PYTHONUTF8` 擋不住繼承來的值（探針：父環境 `PYTHONIOENCODING=cp950`、只補 `PYTHONUTF8=1` ⇒ 仍得 `None`；用 helper ⇒ 得原字串）。父端補 `errors="replace"`（倉庫慣例），解碼不一致時不再整段丟失。
- **回歸鎖**：`test_child_env_forces_utf8_even_under_a_locale_encoded_parent`：父環境刻意拔掉 `PYTHONUTF8`、設 `PYTHONIOENCODING=cp950`，子行程寫中文到 stderr，父端以 utf-8 解碼（不帶 `errors`）必須逐字取回。紅綠自證見上一條探針；修後在無 UTF-8 模式的環境單跑該類兩案皆綠，E2E 的 `rc≠0` 斷言照常成立。

## J 項：DEF-200-658 `ci_wait` 把 GitHub 排隊逾時當真紅（WP-CI，REQ-AP-CI-01）

- **症狀**：macos-compat-ci 的 macOS smoke job 首跑排隊恰 15 分、runner 名稱空白即 `cancelled`、零步驟，三次真實發生（run 45427135743、45439253352、45456241389，皆 2026-11-24）；`ci_wait` 判 fail，主控手動 `gh run rerun --failed` 後立即全綠。
- **成因**：外部現象（GitHub 排隊逾時取消）與真失敗在 run 層同為 `cancelled`，只有 attempt 的 jobs 資料能分辨（唯讀 `gh api …/attempts/<n>/jobs`：`steps==[]`、`runner_name==""`、`created_at→completed_at` 約 15.0 分）。
- **修法**：`classify_attempt`／`queue_timeout_minutes` 判形態，`wait()` 在「全部完成且失敗者全是排隊逾時」才 `gh run rerun <id> --failed` 續等，同 SHA ≤ 2 輪，超過 `fail reason=queue_timeout_exhausted`；同 ref 在 job 存活期間有不同 SHA 的 run＝concurrency 自取消，不重跑；查不到一律保守判 fail。痕跡 `autosdd_ci_queue.jsonl`（`ci_queue_timeout {run, attempt, minutes}`）。
- **驗證**：唯讀 GET 對三支真 run 重放，`queue_timeout_minutes` 回 15.02／15.0／15.0；單元＋真 `ci_wait.py` 行程（gh 以 sitecustomize 重放錄製形狀）全綠；八個突變全數殺死。規格＝`docs/02_architecture/Autopilot_Pipeline_Design.md` §6、`docs/03_testing/contracts/TCS-Autopilot-20261125.md` REQ-AP-CI-01。

## I 項：DEF-200-657 macos-compat-ci 兩支 macOS 專屬紅（FLK4）

- **症狀**：GitHub macos-compat-ci run 45789188660（commit `96ff7665`）兩紅：`AcctSwitchTest.test_trigger_credentials_file` 的 `[] != ['T1']`；`QuotaCliE2ETest.test_e2e_ap_qv_07_billing_and_unmeasured`（billing＝unknown 子案）`json.loads` 得 `JSONDecodeError … char 0`。Windows／ubuntu 皆綠。
- **成因（皆為測試假設宿主平台；產品照 QVD §7.1 正確）**：`acctswitch.tick` 的 `platform` 預設取 `sys.platform`，macOS 依 QVD 表列「T① 在 macOS 缺席（憑證在 Keychain）」走缺席分支，並在 stderr 印一次資訊行（閂鎖 `t1_absent_said`）。①T① 測試未帶 `platform`，mac 上走缺席分支 ⇒ 不觸發；②E2E 的 `_cli` 回傳 stdout＋stderr 合併字串、取末行解析 JSON，mac 上 `quota` 經 `gather`→`tick` 把資訊行印在 stderr 尾端 ⇒ 末行非 JSON；閂鎖只響第一次，所以三子案只紅第一個（billing＝unknown），與 CI 逐字相符。
- **重現**：舊版測試在 Windows 以 `mock.patch.object(sys, "platform", "darwin")` 單跑 T① 測試 ⇒ `+ ['T1']` 同形紅；E2E 以 sitecustomize 的 atexit 在子行程 stderr 尾端注入一行、照舊合併解析 ⇒ `JSONDecodeError: Expecting value: line 1 column 1 (char 0)` 同形紅。
- **修法（測試密閉，不 skip、不改產品）**：T① 案在宿主平台以 mock 釘成 darwin 的前提下顯式帶 `platform="linux"／"win32"`，另加一條「宿主 darwin、不帶參數 ⇒ 缺席」斷言；E2E `_cli` 記下 `self.stdout`，判決 JSON 一律經 `_json()` 只從 stdout 取，失敗訊息仍用合併輸出。
- **回歸鎖**：`test_json_verdict_survives_trailing_stderr`（atexit 注入 stderr 尾行，三平台都能重現 mac 形態；先斷言注入確實出現，載具失效即紅）。紅綠自證：把 `_cli` 改回以合併輸出當判決來源 ⇒ 該案紅、還原綠；舊 T① 案在 mock darwin 下紅、新案在 mock darwin 與原生平台皆綠。

## K 項：DEF-200-659 逾時砍樹測試的心跳觀測跟 2 s 牆鐘賽跑（FLK5）

- **症狀**：pre-push 並行全套唯一紅 `test_selfimproving_verify.TestVerify.test_AT_217_1_E_2_probe_timeout_kills_the_tree [c]`，`assertGreater(s0, 0)` 得 `0 not greater than 0`；單跑兩次皆綠。
- **s0 量的是什麼**：探針（`_HANG` 系列）起一個孫行程，每 0.1 s 往心跳檔追加 1 byte；s0＝`verify` 回來當下心跳檔大小，用來證明「被砍之前孫行程確實活著」，之後 1.5 s 不再長大才算整棵樹被砍。
- **重現與量測**：載具包住 `runner.run_probe`／`_kill_tree`（真砍樹照呼叫），記錄逾時那一刻 pidfile 在不在、心跳幾 byte；HEAD 版測試原封不動。閒置：逾時當下心跳 18～43 byte。60 支燒機＋6 條 CIM 迴圈 8 次：降到 9～41 byte，全綠。與並行根層全套同跑 25 次：99 次砍樹中 13 次逾時當下心跳檔還不存在（其中 8 次連 pidfile 都還沒寫，即孫行程尚未生出），3 次自然轉紅（[c] 兩次、[a] 一次），訊息與 pre-push 逐字相同；其餘幾次靠 `taskkill` 自身延遲讓孫行程搶寫一筆而僥倖綠。
- **成因**：觀測跟逾時牆鐘賽跑。`probe_timeout_seconds=2` 必須涵蓋探針與孫行程兩層 Python 直譯器的啟動；負載下啟動可超過 2 s，逾時砍樹發生在第一筆心跳之前。產品端 `run_probe` 的逾時與 `taskkill /T` 砍樹沒有缺陷。
- **修法（結構正解，只改測試）**：新 helper `_run_hang` 以 `mock.patch.object` 包住 `runner._kill_tree`：逾時那一刻先等心跳檔非空（上界 `HB_GATE_SECONDS=20`，遠短於探針的 600 s）才呼叫真砍樹；耗時斷言扣掉閘門等待，「15 s 內回來」的鑑別力不變。產品碼、逾時值、斷言都沒動，沒加 retry／skip。
- **回歸鎖**：`test_DEF_200_659_tree_kill_is_judged_even_when_the_grandchild_starts_after_the_wall`：探針先睡 3 s（大於 2 s 逾時）才生孫行程，把「負載下起得晚」變成確定輸入。紅綠自證：`HB_GATE_SECONDS=0`（等同舊載具）⇒ `AssertionError: 0 not greater than 0 : 載具沒等到孫行程心跳，砍樹鑑別力不成立`；還原 ⇒ 新案與 AT-217-1-E-2 皆綠。
- **同一 AT 在壓力下另見的兩種紅（不屬本列，未修，交主控裁決）**：①沙盒樹 manifest 與 `app.sandbox` 不符（`+ sha256:dee23c85…`），全套加載具壓力下 25 次見 2 次、三支載具並行加燒機見 1 次。可疑點：測試把 `probe_timeout_seconds` 設 2，而 `_three_steps` 的 `apply_patch`／`reverse_apply` 也用同一個值；壓力下單次 `git apply` 量到 1.3～2.75 s，`reverse_apply` 的失敗回傳值又被忽略。12 次插樁沒有抓到 `reverse_apply` 回 False，所以成因尚未確認。②三支載具並行加 60 支燒機時，NFR-P2-2 的「整體小於 15 秒」得 15.9～17.4 s。這個壓力遠大於 pre-push，門檻是規格值，不動。