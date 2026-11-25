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

