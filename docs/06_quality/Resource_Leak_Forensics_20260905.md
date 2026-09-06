# 資源殘留鑑識底稿（2026-09-05）——ADR-XPLAT-015 的立案取證

> 本檔＝ADR-XPLAT-015（`docs/04_planning/ADR/ADR-XPLAT-015-resource-reclamation-protocol.md`）§1 引用的事實底稿原文，由 session `b80b257b-a1f5-40dc-8c14-63ebd3bebcbd` 於 2026-09-05 在 macOS 本機實測後搬入。**刻意不用 `CrossPlatform_R<N>_` 前綴**：本檔不屬任何 R 輪交棒書體系，命名逸出具名治理文件慣例是看得見的決定（`check_defect_log_crossref.unregistered_governance_docs` 的劃界）。所有數字皆為當日量測值，不得引用為常數；行號以當日 HEAD `7d4086b` 為準。

---

# 事實底稿（2026-09-05 本 session 實測；供設計 agent 共用；引用時標〔實測〕）

## 0. 使用者原話
「APP 背景活動中有一些程序，請檢視是否要不必要用的資源，也記得卸除！請設計一個資源回收機制，讓啟動的資源可以正常被關閉，沒有正常關閉的資源，可以在程序執行完後，被正常關閉回收，請 Architect/SA/SD/Developer 考慮如何設計！目前看到兩個 Docker、兩個 Python 這四個都有用到嗎？」

## 1. 四個背景項目的主人〔實測〕
| 項目 | 實體 | 主人 | 狀態 | 判定 |
|---|---|---|---|---|
| Docker ×2 | `/Library/LaunchDaemons/com.docker.socket.plist`、`com.docker.vmnetd.plist`（root；vmnetd pid 542 閒置） | Docker Desktop 安裝的特權 helper，**非本專案建立** | Docker Desktop app 未啟動、daemon socket 不存在 | 非洩漏；PG e2e（`AutoClaude/docker-compose.ci.yml` 服務 `postgres-ci`／容器 `autoclaude_ci_pg`）需要 Docker，保留或由使用者決定卸載 Docker Desktop |
| Python #1 | `~/Library/LaunchAgents/AutoSDD_Sentinel_1ffc5fd6-….plist`（StartInterval 900） | 本專案額度哨兵，屬另一個**仍活著**的 Claude session（逐字稿 14:59 仍更新） | 合法 | 保留 |
| Python #2 | `~/Library/LaunchAgents/T-r95.plist`（StartInterval 900；ProgramArguments＝`.venv/bin/python tools/session_resume_planner.py --sentinel-tick --plan /var/folders/…/T/trace-forms-gkufbkp6/autosdd_resume_plan_sess-forms.md --task-name T-r95`） | **單元測試留下的真排程工作**（`tools/tests/test_context_budget_guard.py::SentinelDecisionTest.test_the_three_read_failures_and_the_heal_leave_distinct_traces`：tmpdir 前綴 `trace-forms-`、session `sess-forms`、task `T-r95`） | 洩漏；本 session 已 `launchctl bootout`（rc=0）、刪 plist、刪 tmpdir；事後 `launchctl print` rc=113 | 已卸除 |
| （bash）| `~/Library/LaunchAgents/com.autoclaude.nightly.plist`（02:00 每日；RunAtLoad true；由 `tools/install_mac_nightly.sh` 安裝於 7/20） | 使用者刻意安裝 | `launchctl list` 狀態欄 1（上次非零退出） | 非洩漏；健康另議 |
- 本 session 自己的哨兵 `AutoSDD_Sentinel_b80b257b-…` 於工作量累積後自動武裝（合法）。
- `git worktree list` 只有主樹；`/tmp` 無殘留 venv；`docker` daemon 未啟動故容器面不可量（**量不到≠量到零**）。

## 2. T-r95 洩漏鑑識〔實測〕
- 種下時刻：tmpdir 內 `autosdd_resume_log_autosdd_resume_plan_sess-forms.jsonl` 前 12 列全在 `2026-09-05T10:39:42`：woken→heal_failed→aborted（第 1 tick）、woken→selfhealed→**armed_drift_healed（真 launchd 憑證字串）**→decided→rearmed（第 2 tick）、woken→selfhealed→armed_drift_healed→…（第 3 tick）。第 6／11 列由 `tools/lib/quota_escalation.py::_heal_armed_drift` 寫（時間戳格式 `+0800`），憑證＝真 `LaunchdBackend`。
- 真 launchd job 首次醒來 10:54:42（真 TMPDIR 的 `autosdd_resume_log_…sess-forms.jsonl`），之後每 900s 一次直到 15:09:46；`launchctl print` `runs = 17`。
- 自我永續機制：每一 tick `_heal_armed_drift` 以 `sentinel_lifecycle.sentinel_task_names()`＝`select().list_jobs(TASK_PREFIX="AutoSDD_Sentinel_")` 判「armed but missing」；`T-r95` 永不匹配前綴 ⇒ **每一 tick 都判漂移並真的重新 arm（重寫 plist＋bootout＋bootstrap）**，20 筆 `sentinel_armed_drift_healed`。即使刪 plist，記憶體中的 job 下一 tick 就重建；tmpdir 被測試 `addCleanup(rmtree)` 刪掉後亦被 job 的 `write_relay`／`append_log` 重建（目錄 mtime 14:54）。
- 歷史：`~/.autosdd/traces/autosdd_sentinel_launchd_T-r95.log` 529 行、8 次「靜止 21605s ⇒ 靜默解除」循環；`autosdd_sentinel_bootout_T-r95.log` 記 8/30、8/31 兩次 bootout ⇒ 自 8/29 起反覆被全套測試重新種下。同型殘骸：`T-f4b`（14:45 已 bootout）、`T_R81`（10:54 已 bootout）。
- 帳本：`DEF-200-239`（2026-08-31）狀態 `fixed`：「測試族注入假 scheduler 後端＋回歸鎖；全套後現查 T-r95 為空」——**回歸鎖 `test_no_ghost_t_r95_task_survives_a_real_windows_scheduler_query` 只在 win32 跑**（mac 上 skip），mac 側零機械現查。
- 本 session 重演：對五支嫌疑測試裝絆線（`LaunchdBackend.arm/_write_plist/disarm`、`_run` 的 launchctl bootstrap/bootout）單獨跑 ⇒ 5 tests OK、絆線未響、事後無 T-r95 ⇒ **單測行程內不會種**。全套（`tools/run_root_unittests.py`）帶絆線重演正在背景跑（結果見 `tripwire_hits.log`）。模組身分檢查：`escalation.schedule_backend is sb` 等四項皆 True（排除「補丁打錯份」）。
- 已知的「刻意真機副作用」測試：`test_arming_accepts_a_transcript_that_does_not_exist_yet` 以 subprocess 真跑 `--arm-sentinel --task-name AutoSDD_Sentinel_UNITTEST_GHOST` 並 `addCleanup(planner._schtasks_remove, task)`——**清理只在測試正常結束時發生**；測試行程被 kill／timeout 即洩漏。

## 3. 現有機制與缺口〔實讀〕
| 機制 | 位置 | 射程 | 缺口 |
|---|---|---|---|
| 哨兵孤兒回收 `--gc --apply` | `tools/lib/sentinel_lifecycle.py`（`gc()`／`reap_verdict()`／`TASK_PREFIX`）；SessionStart 由 `.claude/hooks/context_budget_guard.py::spawn_sentinel_gc` detached 起 | 只列舉 `AutoSDD_Sentinel_*` 前綴、以 session 逐字稿存在／閒置判「可收」；預設 dry-run | **前綴盲區**：`T-*`、`AutoSDD_Sentinel_UNITTEST_GHOST` 等測試名、以及任何非前綴 label 完全看不到；**判「是我們的」靠 label 不靠 argv 指紋** |
| 哨兵自我解除 | `session_resume_planner.py::_sentinel_tick` disarm 分支（閒置 ≥ `SENTINEL_IDLE_SECONDS`=21600） | 合法哨兵正常下班 | 對測試假逐字稿要等 6 小時；期間每 15 分鐘真跑一次 Python |
| 排程後端 disarm | `tools/lib/schedule_backend.py::LaunchdBackend.disarm`（刪 plist→bootout；自我解除走 `_defer` detached 延後）／`SchtasksBackend.disarm` | 單筆解除；憑證＝`launchctl print` rc 113／`Get-ScheduledTask` 查無 | 無「列舉全部屬於我們的 job」原語（`list_jobs(prefix)` 只接前綴） |
| 測試 tmpdir 回收 | `test_context_budget_guard.py::_tmpdir`（mkdtemp＋addCleanup rmtree；`TmpdirHygieneTest` AST 鎖） | 只此一檔 | 外部寫者（真 launchd job）會重建；其他測試檔各自為政 |
| 假後端注入 | `_tick()` patch `sb.select`；`SchedulerBackendNeverTouchesRealSchtasksTest` | in-process 路徑 | subprocess／detached spawn 不受 patch；mac 無真機現查鎖 |
| 任務書殘骸 gc | `quota_escalation.py::gc_plans`／`--gc-plans`（依齡） | `%TEMP%` 任務書 | 不碰排程器 |
| Docker | `AutoClaude/tools/local_ci_gate.py --pg`（`docker compose -f docker-compose.ci.yml up --wait`） | 只起不收 | 收尾靠人（`useMacWin.md` §B 第 3 步「收尾（不要漏）」：刪樹外 venv、`osascript -e 'quit app "Docker"'`）；記憶體反饋 2026-09-05「開了的資源做完要收」 |
| nightly 安裝／卸載 | `tools/install_mac_nightly.sh --install/--uninstall/--status` | 單一 label | 與哨兵體系兩套存在性判準 |
| Windows 對照 | `SchtasksBackend`、`Get-ScheduledTask`、`Unregister-ScheduledTask`、`tools/install_windows_nightly.ps1` | 同型 | 同樣前綴盲區 |

## 4. 資源清冊（本 repo 會啟動的東西）
1. OS 排程 job：launchd（`~/Library/LaunchAgents/<label>.plist`）／schtasks——哨兵（per session）、續航續跑、nightly、測試夾具（`T-*`、`*_UNITTEST_*`）。
2. 暫存檔：`tempfile.gettempdir()` 下 `autosdd_resume_plan_<sid>.md`、`autosdd_resume_log_*.jsonl`、`autosdd_sentinel_boot_*.log`、`autosdd_probe_*`、`autosdd_schtasks_*`、測試 mkdtemp（多種前綴）。持久痕跡 `~/.autosdd/traces`（SSOT `tools/lib/endurance_env.py::trace_dir()`；逃生口 `AUTOSDD_TRACE_DIR`）。
3. Docker 容器／網路：`autoclaude_ci_pg`／`autoclaude_ci_net`（tmpfs PG，需 alembic migrate）。
4. 樹外乾淨 venv（ONBOARDING 回填 SOP）。
5. 背景行程：pytest／run_root_unittests／pre-push 閘門、`_defer` detached shell、`nohup`（禁）、Monitor／until-loop、Claude 子 agent／Workflow。
6. git worktree（Agent isolation；用完自動移除但可能殘留）。
7. 桌面通知／佇列檔（`~/.autosdd/traces/` notify queue）。

## 5. 設計硬約束（根 CLAUDE.md；違反即紅）
- 繁體中文；Windows 禁 Bash（PowerShell 5.1 語意）、mac/Linux bash；鐵律三「另一平台是什麼值」；鐵律四宣稱附輸出；鐵律五禁毀滅性 git；鐵律六等待必有事件源；鐵律七鎖持有面。
- 往 `tools/` 新增 `*.py` 有稅（ruff／LOC 棘輪 `AutoClaude/tools/check_loc_budget.py` `ROOT_TOOLS_TIERS`／`_script_scan_surface`）；ADR-XPLAT-014 明文「不主張新增檔案」。hook 條目 exec form；hook 不得成為故障源（fail-open 方向、不得阻斷工具）。
- 「量不到 ≠ 量到零」（`None` vs `[]`）；憑證是排程器回讀值不是 rc；痕跡「沒觸發＝檔不長大」可偵測。
- 缺陷帳本結案單線（並行禁寫）；未結列容量 warn 86／fail 98（現查 194 筆有效紀錄、rc=0）。
- 根 CLAUDE.md 被 9 族測試釘住，改動前先盤鎖。
- 既有 hook 事件：見 `.claude/settings.json`（本檔另列）。

## 6. 補記：全套＋絆線重演結果〔實測 2026-09-05 15:17~15:29〕
- 指令：`tools/run_root_unittests.py` 全套在絆線包裝下跑（絆線＝`LaunchdBackend._write_plist` 目標落在真 `~/Library/LaunchAgents` 即拋例外；`_run` 的 `launchctl bootstrap/bootout` 即拋例外；planner 子行程 spawn 只記錄）。結果 `Ran 3932 tests in 697.946s`、`FAILED (errors=2, skipped=45)`，兩個 error 皆為絆線命中：
  1. **`REAL_PLIST_WRITE ~/Library/LaunchAgents/T-f4b.plist`**：堆疊＝`tools/tests/test_context_budget_guard.py:4071 test_the_sentinel_tick_arm_reset_branch_also_wires_the_reset_boundary` → `tools/session_resume_planner.py:1368 _sentinel_tick` → `tools/lib/quota_escalation.py:487 patrol_housekeeping` → `tools/lib/quota_escalation.py:353 _heal_armed_drift` → `tools/lib/schedule_backend.py:426 LaunchdBackend.arm`。該測試只 patch 了 `planner.sentinel_decide` 與 `planner.register_endurance`，**沒有注入假排程後端**；而 `_heal_armed_drift` 不經 `register_endurance` 這個接縫、直接呼叫 `schedule_backend.select().arm(...)` ⇒ **每次全套（含每次 `git push` 的 pre-push）都在真機種下 `T-f4b`**。`~/.autosdd/traces/autosdd_sentinel_bootout_T-f4b.log` 今日 5 筆 bootout（03:18Z／03:41Z／05:25Z／06:23Z／06:45Z）＝ 5 次全套。T-f4b 之所以只活 15 分鐘：tmpdir 被 addCleanup 刪掉 ⇒ 下一 tick「任務書不存在」⇒ 自我解除；**若測試行程被 kill／timeout 於 cleanup 前，tmpdir 留下 ⇒ 永久殘留**（T-r95 形狀：tmpdir `trace-forms-gkufbkp6` 存活，job 每 tick 自癒重掛）。
  2. **`REAL_LAUNCHCTL_WRITE launchctl bootout gui/501/AutoSDD_Sentinel_UNITTEST_GHOST`**：來自 `test_arming_accepts_a_transcript_that_does_not_exist_yet` 的 `addCleanup(planner._schtasks_remove, task)` → `schedule_backend.py:546 disarm`——即該測試以 subprocess **真的武裝**了 `AutoSDD_Sentinel_UNITTEST_GHOST`（`_isolated_env` 只改 HOME/TMPDIR，launchd 網域仍是真 gui/501），靠 addCleanup 拆；清理只在測試正常結束才發生。
- 結構性結論：**arm 有兩個接縫**（`planner.register_endurance` 與 `quota_escalation._heal_armed_drift` 直呼 `select().arm`），DEF-200-239 的修法（`_tick` 注入假後端）只蓋住走 `_tick` helper 的測試族；任何直接呼叫 `_sentinel_tick`／`patrol_housekeeping` 的測試都會經第二接縫真種。mac 側零機械現查（回歸鎖 win32-only）。
- 全套跑完後 `launchctl list` 只剩兩支合法哨兵＋nightly；`git status` 乾淨（`tools/.last_failure_*.log` 為 gitignored）。
