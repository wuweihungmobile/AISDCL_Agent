# ADR-XPLAT-015：資源回收協定（resource reclamation）——OS 排程 job／暫存檔／Docker 容器／背景行程

- **狀態**：**Adopted（舵手依掌舵者 2026-08-29「裁決題以最佳理想化代決」規則於 2026-09-05 裁 §7 Q1＝A／Q2＝A／Q3＝A；設計已經 4 提案 × 3 評審鏡 × 25 條宣稱對抗驗證〔5 條修正〕；本 ADR 是設計文件，未落地任何生產碼，§5 為施工順序）**。原狀態＝Proposed（四方提案合成稿 → 修訂者定稿）。
- **日期**：2026-09-05
- **關係**：**增補** [ADR-XPLAT-004](ADR-XPLAT-004-token-endurance-protocol.md) §2.6（預防性哨兵＝武裝側）——本 ADR 是**同一協定的另一半（回收側）**，不另立「哨兵是什麼」的第二份敘述；
  承接 [ADR-XPLAT-014](ADR-XPLAT-014-resume-chain-hardening.md) 的「不主張新增檔案」原則與 §4.5 憑證紀律；
  沿用 ADR-XPLAT-004 §2.7 的「量不到≠量到零」與根 CLAUDE.md〈反事後諸葛取證規則〉（憑證＝排程器回讀值，不是 rc）。
- **對應缺陷**：**待立列：DEF-200-239 的 mac 孿生＋第二接縫**。既有列 `DEF-200-239`（帳本 `docs/06_quality/AutoSDD_Defect_Log.md:240`，狀態 `fixed`）的修法射程只蓋 `_tick` helper 族（注入 `sb.select`）且回歸鎖 win32-only；本 ADR 立案取證（§1.2-5～1.3）以絆線實證：**arm 有第二個接縫**（`tools/lib/quota_escalation.py:353 _heal_armed_drift` 直呼 `schedule_backend.select().arm`，不經 `planner.register_endurance`），任何直呼 `_sentinel_tick`／`patrol_housekeeping` 且只 patch `register_endurance` 的測試都從這條路真種——**每次全套（含每次 `git push` 的 pre-push root-infra leg）都在 mac 真機種一次 `T-f4b`**；GHOST 測試則以 subprocess 真武裝、只靠 `addCleanup` 拆。改列／新立列**只由收尾單人窗口寫**（鐵律七）。
- **立案取證**：`docs/06_quality/Resource_Leak_Forensics_20260905.md`（事實底稿；本 session 2026-09-05 實測；§1 四個背景項目主人判定、§2 T-r95 鑑識、§6 全套＋絆線重演堆疊）。本 ADR §1 逐字引用其實測值並標〔實測〕。
- **落地物（候選，尚未動工）**：`tools/lib/quota_escalation.py`、`tools/lib/schedule_backend.py`、`tools/lib/schedule_backend_calendar.py`、`tools/lib/sentinel_lifecycle.py`、`tools/run_root_unittests.py`（+1~2 raw line）、`tools/tests/test_context_budget_guard.py`、`tools/tests/test_mac_endurance_r83.py`、`AutoClaude/tools/local_ci_gate.py`、`AutoClaude/tests/tools/test_local_ci_gate.py`。**本 ADR 不主張新增任何 `tools/*.py`**（往 `tools/` 新增 `.py` 同時污染 ruff／LOC 棘輪／`_script_scan_surface` 三個面，理由同 ADR-XPLAT-014 檔頭）；**不改 `.claude/hooks/context_budget_guard.py`**（raw 1089/1089，餘裕 0）；**不新增任何 hook 事件**（`.claude/settings.json` 現有 `SessionStart`／`PreToolUse`／`PostToolUse`／`Stop` 四種〔實讀〕，新增 `SessionEnd` 會觸發根 CLAUDE.md 機械守衛總表雙向鎖，且哨兵本來就必須活過 session 結束）。

> **本檔所有數字的性質**：`〔實讀〕`＝本輪以 Read／Grep／sed 讀出的 `檔案:行號`（修訂輪 2026-09-05 已對 HEAD `7d4086b` 全數重取；工作樹乾淨）；
> `〔實測〕`＝本 session 在本機真跑指令得到的輸出（事實底稿或本輪直接現查）；
> `〔現查〕`＝落地時必須重跑指令取值，本檔不複寫。**本檔不把任何會漂移的量測值（LOC、測試數、launchd 清單）寫成常數**；
> 文內出現的 LOC 現值皆〔實測〕於 2026-09-05，落地當回合一律重跑 `python AutoClaude/tools/check_loc_budget.py --json`。
> 🔴 行號會隨落地漂移：帳本／證據檔寫入前，每一個 `檔案:行號` 都要以 `grep -n` 重取一次（尤其 `SchedulerHygieneTest` 落地後 `test_context_budget_guard.py` 全檔行號後移）。

---

## 1. 立案

### 1.1 使用者原話與四個背景項目的判定〔實測〕

使用者問：「APP 背景活動中有一些程序……目前看到兩個 Docker、兩個 Python 這四個都有用到嗎？」並要求「設計一個資源回收機制，讓啟動的資源可以正常被關閉，沒有正常關閉的資源，可以在程序執行完後被正常關閉回收」。

| 項目 | 實體 | 主人 | 判定 |
|---|---|---|---|
| Docker ×2 | `/Library/LaunchDaemons/com.docker.socket.plist`、`com.docker.vmnetd.plist`（root；vmnetd pid 542 閒置）〔實測〕 | Docker Desktop 安裝的特權 helper，**非本專案建立** | 非洩漏。PG e2e（`AutoClaude/docker-compose.ci.yml:28` `container_name: autoclaude_ci_pg`〔實讀〕）需要 Docker；卸不卸 Docker Desktop 是使用者裝機決策，**不在本 ADR 回收面** |
| Python #1 | `~/Library/LaunchAgents/AutoSDD_Sentinel_1ffc5fd6-….plist`（StartInterval 900）〔實測〕 | 另一個**仍活著**的 Claude session 的額度哨兵（逐字稿 14:59 仍更新）〔實測〕 | 合法，保留 |
| Python #2 | `~/Library/LaunchAgents/T-r95.plist`，ProgramArguments＝`.venv/bin/python tools/session_resume_planner.py --sentinel-tick --plan /var/folders/…/T/trace-forms-gkufbkp6/autosdd_resume_plan_sess-forms.md --task-name T-r95`〔實測〕 | **單元測試留下的真排程工作**（tmpdir 前綴 `trace-forms-`、session `sess-forms`、task `T-r95`） | **洩漏**。本 session 已 `launchctl bootout`（rc=0）、刪 plist、刪 tmpdir；事後 `launchctl print` rc=113〔實測〕 |
| bash | `~/Library/LaunchAgents/com.autoclaude.nightly.plist`（02:00 每日；`tools/install_mac_nightly.sh` 安裝）〔實測〕 | 使用者刻意安裝 | 非洩漏；`launchctl list` 狀態欄 1（上次非零退出）屬健康問題**另案** |

答「四個都有用到嗎」：**兩個 Docker 是 Docker Desktop 的系統 daemon，不是本專案起的；兩個 Python 一個合法、一個是測試洩漏（已收）。** 本 ADR 要治的是「一個」怎麼變成「每次全套都會再生一個」。

### 1.2 T-r95 鑑識摘要〔實測；逐字引自事實底稿 §2／§6〕

1. **種下時刻**：tmpdir 內 `autosdd_resume_log_autosdd_resume_plan_sess-forms.jsonl` 前 12 列全在 `2026-09-05T10:39:42`；第 6／11 列由 `tools/lib/quota_escalation.py::_heal_armed_drift` 寫、憑證＝真 `LaunchdBackend`。真 launchd job 首次醒來 10:54:42，之後每 900s 一次直到 15:09:46；`launchctl print` `runs = 17`。
2. **自我永續機制**：每一 tick `_heal_armed_drift` 以 `sentinel_lifecycle.sentinel_task_names()`（＝`select().list_jobs("AutoSDD_Sentinel_")`，`tools/lib/sentinel_lifecycle.py:148-158`〔實讀〕）判「armed but missing」（`tools/lib/quota_escalation.py:349`〔實讀〕）；`T-r95` 永不匹配前綴 ⇒ **每一 tick 都判漂移並真的重新 arm**（`quota_escalation.py:353` → `schedule_backend.py:426`，重寫 plist＋bootout＋bootstrap），共 20 筆 `sentinel_armed_drift_healed`。刪 plist 下一 tick 就重建；tmpdir 被測試 `addCleanup(rmtree)` 刪掉後亦被 job 的 `write_relay`／`append_log` 重建（目錄 mtime 14:54）。
3. **歷史**：`~/.autosdd/traces/autosdd_sentinel_launchd_T-r95.log` 529 行、8 次「靜止 21605s ⇒ 靜默解除」循環；`autosdd_sentinel_bootout_T-r95.log` 記 8/30、8/31 兩次 bootout ⇒ 自 8/29 起反覆被全套重新種下。同型殘骸 `T-f4b`、`T_R81`（本輪現查 `~/.autosdd/traces` 仍有六支 `autosdd_sentinel_{bootout,launchd}_{T-f4b,T-r95,T_R81}.log`〔實測〕）。
4. **帳本**：`DEF-200-239`（2026-08-31）狀態 `fixed`，回歸鎖 `test_no_ghost_t_r95_task_survives_a_real_windows_scheduler_query`（`tools/tests/test_context_budget_guard.py:5589`〔實讀〕）**只在 win32 跑**（`:5595-5597` `if sys.platform != "win32": self.skipTest(...)`）⇒ mac 側零機械現查。
5. **全套＋絆線重演**（事實底稿 §6；15:17~15:29；絆線＝`LaunchdBackend._write_plist` 目標落在真 `~/Library/LaunchAgents` 即拋、`_run` 的 `launchctl bootstrap/bootout` 即拋、planner 子行程 spawn 只記錄）：`Ran 3932 tests in 697.946s`、`FAILED (errors=2, skipped=45)`，兩個 error 皆為絆線命中：
   - **`REAL_PLIST_WRITE ~/Library/LaunchAgents/T-f4b.plist`**：堆疊 `test_context_budget_guard.py:4071 test_the_sentinel_tick_arm_reset_branch_also_wires_the_reset_boundary`（def `:4042`）→ `session_resume_planner.py:1368 _sentinel_tick` → `quota_escalation.py:487 patrol_housekeeping` → `quota_escalation.py:353 _heal_armed_drift` → `schedule_backend.py:426 LaunchdBackend.arm`。該測試只 patch `planner.sentinel_decide` 與 `planner.register_endurance`（`:4060-4068`〔實讀〕），**沒有注入假排程後端**；而 `_heal_armed_drift` 不經 `register_endurance`、直接 `schedule_backend.select().arm(...)` ⇒ **每次全套（含每次 `git push` 的 pre-push root-infra leg，`tools/git-hooks/pre-push:341`〔實讀〕）都在真機種下 `T-f4b`**。`~/.autosdd/traces/autosdd_sentinel_bootout_T-f4b.log` 今日 5 筆 bootout（03:18Z／03:41Z／05:25Z／06:23Z／06:45Z）＝ 5 次全套。T-f4b 之所以只活 15 分鐘：tmpdir 被 `addCleanup` 刪掉 ⇒ 下一 tick「任務書不存在」（`schedule_backend.py:406-410`）⇒ 自我解除；**若測試行程被 kill／timeout 於 cleanup 前，tmpdir 留下 ⇒ 永久殘留**（＝T-r95 形狀：tmpdir `trace-forms-gkufbkp6` 存活，job 每 tick 自癒重掛）。
   - **`REAL_LAUNCHCTL_WRITE launchctl bootout gui/501/AutoSDD_Sentinel_UNITTEST_GHOST`**：來自 `test_arming_accepts_a_transcript_that_does_not_exist_yet`（def `:2402`〔實讀〕）的 `addCleanup(planner._schtasks_remove, task)`（`:2420`）→ `schedule_backend.py:546 disarm`——該測試以 subprocess **真的武裝**了 `AutoSDD_Sentinel_UNITTEST_GHOST`（`_isolated_env` 只改 HOME／TMPDIR，launchd 網域仍是真 gui/501；且 `_isolated_env` 預設已對子行程寫 `AUTOSDD_SENTINEL_OFF=1`（`:252-253`〔實讀〕），**但 planner 的 `_arm_sentinel`→`register_endurance`→`select().arm` 這條路根本不讀該旗標**）；**清理只在測試正常結束才發生**，靠 `addCleanup` 才拆。
6. **結構性結論（事實底稿 §6 逐字）**：**arm 有兩個接縫**——`planner.register_endurance`（`session_resume_planner.py:755` → `_register_at_expr` `:744` `select().arm`）與 `quota_escalation._heal_armed_drift`（`:353` 直呼 `select().arm`）。DEF-200-239 的修法（`_tick` helper `test_context_budget_guard.py:2031-2060` 於 `:2054-2055` 注入 `sb.select`）只蓋走 helper 的測試族；任何直呼 `_sentinel_tick`／`patrol_housekeeping` 的測試都會經第二接縫真種。單測行程內對五支嫌疑測試裝絆線單獨跑 ⇒ 5 tests OK、絆線未響〔實測〕⇒ **單測不會種、全套才會種**；模組身分 `escalation.schedule_backend is sb` 等四項皆 True〔實測〕（排除「補丁打錯份」）。**T-r95 今日 10:39 的種下入口尚未被絆線逐字命中**（絆線只抓到 T-f4b 這一站）——本 ADR 的止血是結構性的、不依賴逐站歸因，但帳本敘述**不得寫「T-r95 種下點已找到」**。
7. **機器現況（修訂輪唯讀現查 2026-09-05；勿沿用任一提案的舊讀值）**：
   - 排程面：`launchctl list | grep -Ei 'AutoSDD|T[-_]|autoclaude|UNITTEST'` 只列 `AutoSDD_Sentinel_1ffc5fd6-…`（0）、`com.autoclaude.nightly`（1）、`AutoSDD_Sentinel_b80b257b-…`（0）〔實測〕；`launchctl print gui/501/AutoSDD_Sentinel_UNITTEST_GHOST` rc=113（**已不在**）。grep 樣式用 `T[-_]` 而非 `T-`——`T_R81` 用底線，原樣式會漏。
   - plist 面：`~/Library/LaunchAgents/` **本專案標籤**的 plist 只有對應上列三支；另有 3 支 Google 非本專案（`com.google.GoogleUpdater.wake`／`com.google.keystone.agent`／`com.google.keystone.xpcservice`）〔實測〕——這正是 §3.3 `foreign` 類的真實樣本。
   - 持久痕跡面：`ls ~/.autosdd/traces | wc -l` → 64；含第 3 點所列六支 `T-*`／`T_*` 殘骸 log〔實測〕。
   - 暫存檔面：`$TMPDIR`（`/var/folders/…/T/`）根層 **至少七個**測試殘骸〔實測，mtime 皆落在 15:09~15:25 全套視窗〕：`autosdd_resume_log_autosdd_resume_plan_sess-forms.jsonl`（15:09）、`autosdd_resume_log_autosdd_resume_plan_UNITTEST_GHOST.jsonl`（15:25）、`autosdd_resume_log_autosdd_resume_plan_sid-lock.jsonl`（15:21；來源 `test_context_budget_guard.py:1395-1401` `session_id: "sid-lock"`）、`autosdd_resume_log_plan.jsonl`（15:21）、`autosdd_resume_plan_s.md`（15:21）、`autosdd_resume_plan_sid.md`（15:21）、`autosdd_sentinel_boot_r83-no-such-session.log`（15:25；來源 `test_mac_endurance_r83.py:1394` `r83-no-such-session.jsonl`）。**殘骸跨兩個測試檔** ⇒ 暫存檔面洩漏不是單一測試檔的 `_tmpdir` 衛生問題，§3.6 B 面判準必須是「`$TMPDIR` 根層 `autosdd_*` 前綴 ＋ 非活 session id」而非逐檔點名。
   - 〔未定〕項：`autosdd_sentinel_boot_{5cb358d0,88e90227,89b044ee,8da09c11}.log` 四支（10:38~10:50，內容為 session-start 行）；修訂輪對 `~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/` 逐字稿現查只對得上 `8da09c11` 一支（判決方回報對得上兩支——差異未歸因），其餘標〔未定〕而非省略（量不到≠量到零）。

### 1.3 三個結構事實 → 止血層對應（事實底稿 §6 的落點）

| 結構事實〔實測〕 | 為什麼 DEF-200-239 的修法蓋不到 | 本 ADR 對應層 |
|---|---|---|
| 第二個 arm 接縫：`quota_escalation._heal_armed_drift` `:353` 直呼 `select().arm`，不經 `register_endurance` | `_tick` helper 注入 `sb.select` 只保護走 helper 的測試；`:4071` 直呼 `_sentinel_tick` 並只 patch `register_endurance` ⇒ 第二接縫裸奔 | §4-1 精確查名（非前綴 label 不再結構性 missing）＋ §4-2 `_heal_armed_drift` 尊重 `AUTOSDD_SENTINEL_OFF` ＋ §3.2 行程級沙箱（在 `select()` 一次罩住兩個接縫） |
| T-f4b 每次 pre-push 全套都真種（今日 5 筆 bootout＝5 次全套） | 回歸鎖 `:5589` win32-only，mac 全套零現查；job 15 分鐘後自我解除 ⇒ 事後 `launchctl list` 看不到 | §3.6 圍籠 ledger 面（決定性：忘了注入本身判紅）＋ A 面差分 ＋ §4-3(b) `SchedulerHygieneTest` AST 鎖（兩支 tick 對稱射程） |
| GHOST 測試以 subprocess 真武裝、只靠 `addCleanup` 才拆 | in-process patch 罩不到子行程；`_isolated_env` 寫的 `AUTOSDD_SENTINEL_OFF=1` 被 `arm()` 無視 | §3.2 沙箱讓 `AUTOSDD_SENTINEL_OFF` 在後端層生效（子行程繼承）＋ §7 Q2 真機射程改 opt-in |

---

## 2. 資源清冊與生命週期表

| # | 資源類 | 正常關閉點（現況） | 事後回收點（現況） | 現況機械物〔實讀〕 | 缺口 → 本 ADR 處置 |
|---|---|---|---|---|---|
| 1 | **OS 排程 job**：launchd `~/Library/LaunchAgents/<label>.plist`／schtasks——哨兵（per session）、續航續跑、nightly、測試夾具（`T-*`、`*_UNITTEST_*`） | 哨兵自我解除（`_sentinel_tick` disarm 分支，閒置 ≥21600s）；`LaunchdBackend.disarm` `schedule_backend.py:529-554`（刪 plist→bootout→`_readback` 回讀）／`SchtasksBackend.disarm` `:328`；測試 `addCleanup(_schtasks_remove)` | SessionStart `spawn_sentinel_gc` `.claude/hooks/context_budget_guard.py:788-803` detached 起 `sentinel_lifecycle.py --apply --keep <sid>`；`gc()` `sentinel_lifecycle.py:364-406` | `reap_verdict` `:214`；`_remove_task` `:292`；`list_jobs(prefix)` `schedule_backend.py:350／:556／:793` | **前綴盲區**（`gc()` 母體＝`sentinel_task_names()` `:375`）；**所有權靠 label 不靠 argv**；**無「列舉全部屬於我們的 job」原語**；mac 零機械現查 → §3.3 `owned_jobs()`、§3.4 `orphan_verdict`、§3.6 圍籠、§4 止血 |
| 2 | **暫存檔**：`tempfile.gettempdir()` 下 `autosdd_resume_plan_<sid>.md`、`autosdd_resume_log_*.jsonl`、`autosdd_sentinel_boot_*.log`、`autosdd_ctxguard_*.json`、測試 mkdtemp；持久痕跡 `~/.autosdd/traces`（SSOT `tools/lib/endurance_env.py:125 trace_dir()`；逃生口 `AUTOSDD_TRACE_DIR` `:75`；唯讀退回暫存 `:108-118`） | 測試 `_tmpdir` `test_context_budget_guard.py:175-180`（mkdtemp＋addCleanup rmtree）；終態 `alert(loud=False)`→`gc_plans` `quota_escalation.py:690` | `reap_plans` `quota_escalation.py:666`（唯一 unlink 站點，`PlanReapHasOneHomeTest` `test_mac_endurance_r83.py:1699`）；`_sweep_artifacts` `sentinel_lifecycle.py:304-329` | `TmpdirHygieneTest` `:183`（僅本檔 AST 鎖） | 外部寫者（真 job）重建 tmpdir；根層殘骸（§1.2-7，跨兩個測試檔）無人列舉；`autosdd_resume_log_*.jsonl` 是稽核面**刻意不刪**（`sentinel_lifecycle.py:332-342`）→ §3.4「先拆排程再 sweep」、§3.6 B／C 面**只列不刪**、§6 劃界 |
| 3 | **Docker 容器／網路**：`autoclaude_ci_pg`／`autoclaude_ci_net`（`docker-compose.ci.yml:28／:46／:49`） | `gate_pg` `AutoClaude/tools/local_ci_gate.py:623-648`：alembic 失敗分支 `:641` 與正常路徑 `:647` 兩處 `_run_quiet([*_PG_COMPOSE, "down", "-v"])`，**皆不在 try/finally 內**（`:623-648` 區間 grep `try:|finally:` 零命中〔實讀〕）；`up -d --wait` 失敗 `:631-633` 直接 `return 1` **不收** | 無（`useMacWin.md:118` 人工 SOP：`osascript -e 'quit app "Docker"'`） | `_PG_COMPOSE` `:98`；`pg_autodetect` `:213`；`_stream` `:479-481` 裸 `subprocess.run`；`_run_quiet` `:484-492` 吞 OSError 回 1 | KeyboardInterrupt／例外／up 半起皆漏收；無現查 → §3.7 try/finally＋容器回讀憑證；孤兒容器**只印建議不自動 down** |
| 4 | **樹外乾淨 venv**（ONBOARDING 回填 SOP） | `useMacWin.md:118`「回填完立刻刪掉樹外 venv」（人） | 無 | 無 | **劃界**：路徑不在 repo、是人開的；圍籠只印 `ls -d $TMPDIR/*venv*` 式普查行（§6） |
| 5 | **背景行程**：pytest／run_root_unittests／pre-push；`_defer` detached `/bin/sh`（`schedule_backend.py:734-756`，`DEFER_WAIT_CAP_SECONDS=3900` `:190` 自帶上界，痕跡 `autosdd_sentinel_bootout_<label>.log`）；hook `spawn_sentinel`／`spawn_sentinel_gc`（一次性）；測試 `subprocess.run(timeout=180)` | 全部有自然終點（等待上界／單次執行／timeout） | 無需回收器 | `_defer` 痕跡「沒觸發＝檔不長大」 | 缺**可見性** → §3.6 普查行（字元類自我否定 `pgrep`；**只印不殺**：殺錯一支在等額度的 tick＝把續航靜默弄丟）；Claude 子 agent／Workflow 由 harness 持有，**劃界不碰** |
| 6 | **git worktree**（Agent isolation） | 用完自動移除 | `git worktree prune`＝git 寫入 | `block_destructive_git.py` 擋 `worktree remove --force` | **劃界**：只 `git worktree list --porcelain` 唯讀普查；淨減法只准收尾單人窗口（鐵律七）。本輪現查只有主樹〔實測〕 |
| 7 | **桌面通知／佇列檔**（`~/.autosdd/traces/` notify queue） | `redeliver_queued` `quota_escalation.py:488` 每 tick 重投 | 同左（既有機制已是回收器） | 同左 | 無新缺口；圍籠報表附 `notify_queue_pending` 既有欄位 |

---

## 3. 設計

### 3.0 核心命題

> **「是我們的」看 argv 指紋不看 label；「已成孤兒」看主人存活不看檔名；「碰不碰真載具」由行程決定而不是由每支測試記得注入；任何一軸量不到（`None`）一律不收、只出聲。**

三個判準都與命名無關，所以命名逃逸（`T-r95`／`T-f4b`／`plan.md`／自訂 `--task-name`）不再是盲區。回收在**三個時點**各做一次「現查 ∖ 持有」差分：(a) 所有權者正常收（`disarm`／`addCleanup`／`try-finally`）；(b) 執行單元收尾（全套 runner 圍籠）；(c) 下一位開工者（SessionStart 既有 `spawn_sentinel_gc`，hook 零改動）。

### 3.1 登錄：不新增資源登錄簿

每一類資源的**真相源就是它的載具本身**（launchd／schtasks 回讀、`docker ps`、檔案系統）。刻意否決「`autosdd_resources.jsonl` 資源帳本」（SD 提案 C5）：它自承「帳本是線索不是真相、`gc()` 母體仍以排程器回讀為主」，五個寫入站點的 LOC 稅只換來 `origin` 欄的可讀性；且帳本會誤導讀者在「量不到」時以帳本補位。唯一的行程內登錄是 §3.2 沙箱後端的 `ledger`（那是**測試行程專用**、用來把「忘了注入」變成決定性紅燈，不是 production 帳本）。

### 3.2 行程級沙箱：`select()` 第三縫，沿用既有 `AUTOSDD_SENTINEL_OFF`

- **家**：`tools/lib/schedule_backend.py:809-817 select()`〔實讀〕（唯一提問點；既有兩個注入參數 `os_name`／`platform_name`）。新類別 `SandboxBackend(real)` 放 `NoCarrierBackend`（`:768`）之後。
- **規則（寫進本檔檔頭並以測試釘住）**：
  1. **裸 `select()`**（兩參數皆 `None`）且 `os.environ.get("AUTOSDD_SENTINEL_OFF")` 有值 ⇒ 回 `SandboxBackend(真後端)`；
  2. **顯式帶參數**的 `select(os_name=…)`／`select(os.name, sys.platform)` ⇒ **一律回真後端**（保住 `SelectIsTheOnlyPlatformQuestionTest` `test_mac_endurance_r83.py:90-99` 三支鎖；也是回收臂取真載具的出口）；
  3. `AUTOSDD_UNATTENDED`（`tools/lib/unattended_authz.py:37`）有設時**忽略沙箱**（無人值守不准假排程）。
- **為什麼沿用 `AUTOSDD_SENTINEL_OFF` 而不新增 `AUTOSDD_SCHEDULER_SANDBOX`／`AUTOSDD_SCHEDULER_BACKEND`**：它已是 ENV_SPEC 登記的逃生口（`tools/lib/quota_policy_env.py:133`〔實讀〕，語意「1 ⇒ 額度續航哨兵關掉」）、`setUpModule` 已對整個測試行程釘它（`test_context_budget_guard.py:69-84`）、`_isolated_env` 已對子行程預設寫 `=1`（`:252-253`）、`test_this_module_never_reaches_the_real_scheduler`（`:8116`）已在守兩條路。**同一個變數同時罩住 in-process 直呼與 subprocess 路徑，也同時罩住兩個 arm 接縫**（§1.3 第一列），且與 `EscapeHatchAndNoProliferationTest`（`r83:1345`）「不得另寫一套」精神一致。現況的病恰是：這個旗標只有 hook 端（`context_budget_guard.py:765／:812／:842`）尊重，**後端 `arm()` 一律照做**。
- **`SandboxBackend` 行為**（`name`／`credential_key`／`evidence_hint`／`credential_line` 委派真後端，讓 `test_context_budget_guard.py:1861／:2155` 裸讀 `credential_key` 不破）：
  - `arm()`：**只**把 `{task, plan, tick, origin}` 記進類別層 `ledger`（`origin`＝`traceback.extract_stack()` 中最深的 `tools/tests/` 幀，讓「哪支測試忘了注入」可列名）；回 `(0, "SANDBOX（未武裝：AUTOSDD_SENTINEL_OFF 有設）…")`——憑證字串逐字含「未武裝」，會被 `append_log(..., credential=…)` 原封寫進 `autosdd_resume_log_*.jsonl` ⇒ 沙箱外洩到真 shell 時痕跡檔自證；
  - `list_jobs(prefix)`：`real.list_jobs(prefix)`（`None` 原樣向上）∪ ledger 內符合前綴者——**有狀態** ⇒ §4 精確查名後，沙箱內的 arm 在下一 tick 被判「在」，漂移自癒最多發生一次；
  - `disarm(task)`：ledger 移除 **並** 透傳 `real.disarm(task)`（`--remove-schtasks` 在使用者設了 `AUTOSDD_SENTINEL_OFF` 的 shell 下仍真的拆得掉；對假 label 透傳＝`launchctl bootout` 查無、無害）；
  - `verify_cli`：透傳；`owned_jobs()`：`real.owned_jobs()` ∪ ledger（標 `sandbox=True`）。
- **對稱鎖**：加進 `_BACKENDS`（`r83:340`）過 `BackendInterfaceIsSymmetricTest`（`:371`）。
- **失效可偵測**：(a) 沙箱沒生效（有人繞 `select` 直呼類別）⇒ §3.6 圍籠 A 面差分抓到真 job；(b) 沙箱外洩到 production ⇒ 憑證含「未武裝」進痕跡、`liveness_line`（`sentinel_lifecycle.py:184`）印 `backend.name`、`SentinelWiringTest` 加一條「production 路徑憑證不得含『未武裝』」；(c) `ledger` 非空＝有測試忘了注入 ⇒ 圍籠列名並判紅（**決定性**，不受 §3.6 時間窗影響）。

### 3.3 所有權判準：`owned_jobs()`（三後端＋沙箱對稱）

- **家**：`LaunchdBackend`／`SchtasksBackend`／`NoCarrierBackend`／`SandboxBackend` 各加一個公開方法 `owned_jobs(self) -> list[dict] | None`；純解析 `owned_record(label, argv_tokens, definition_path) -> dict | None` 放 `tools/lib/schedule_backend_calendar.py`（count_loc 44/400〔實測〕，檔頭自述「純函式、無模組層可變狀態」`:1-12`〔實讀〕）。排程器原語仍只住 `_CARRIER_HOMES` 宣告的兩家（`r83:205-211`）。
- **回傳列**：`{"label", "argv", "plan", "tick", "planner", "definition", "kind"}`；`kind ∈ {sentinel, resume, fixture, foreign}`。
- **指紋**：argv 任一項**以 `tools/session_resume_planner.py` 結尾**（`Path(...).name == "session_resume_planner.py"` 且父目錄名 `tools`）⇒ `ours`；**不**精確比對本 checkout 的 `resolve()` 路徑（那是 `_verify_problems` `schedule_backend.py:503-516` 的武裝側判準，回收側必須寬：從已刪 worktree／別 checkout 種下的 job 是**最確定的死者**，精確比對會讓它永遠是 foreign 而無人認領）。`planner` 欄＝該路徑；**該檔不存在 ⇒ 直接可判孤兒**（job 醒來只會 fail-loud 空轉）。`tick`＝argv 中 `--sentinel-tick`／`--resume-tick`；`plan`＝`--plan` 後一項。argv 不含 planner ⇒ `foreign`（`com.autoclaude.nightly`／Docker Desktop 的 `com.docker.*`／`com.google.*`／第三方）——**永不動**。
- **mac 取法**：(a) glob `LAUNCH_AGENTS_DIR/*.plist`（`:167`）以 `plistlib` 讀 `ProgramArguments`；(b) `launchctl list` 全集中非 `com.apple.*` 且 (a) 未涵蓋的 label → 既有 `_readback()`（`:634`，已解析 `arguments = {…}` 與 depth-1 `path`）——(b) 是抓「**已載入但 plist 已刪**」殭屍（`schedule_backend.py:421-425` 記載的 macOS 專屬態；`install_mac_nightly.sh:54／:473／:530` R68-M31）的唯一辦法，**不能只做 (a)**。`definition`＝launchd 自報 `path`。任一列舉指令 rc≠0 ⇒ 整體回 `None`。
- **Windows 取法**：單次 `planner.run_powershell`（NO_WINDOW＋UTF-8 前置，同 `list_jobs` `:345-358` 的理由）：`Get-ScheduledTask | ForEach-Object { $_.TaskName + "`t" + $_.TaskPath + "`t" + (($_.Actions | ForEach-Object { $_.Execute + ' ' + $_.Arguments }) -join ' ') }`；依 `runner_action_argument`（`session_resume_planner.py:654-657`：`"<planner>" <tick> --plan "<path>" --task-name "<task>"`）解析引號。**不用** `Export-ScheduledTask` XML（那是 `tools/check_scheduled_task_drift.py:42` 的另一家，不複製）。**🔴 本格本機量不到**（mac），落地時標「未驗證」，見 §5 步 3 與 §6。
- **NoCarrier**：回 `[]`（量到零，與 `:793-794` `list_jobs` 同理）。

### 3.4 孤兒判準真值表 `orphan_verdict()` 與 `gc()` 母體擴充

- **家**：`tools/lib/sentinel_lifecycle.py`（count_loc 213/400〔實測〕，餘裕最大）；與 `reap_verdict` `:214-249` 並列，**重用**它而不重寫。
- **主人錨點來源**：讀任務書 RELAY 狀態塊（`plan_state` `:197-212` 走 `planner.parse_relay` `session_resume_planner.py:373`，塊內有 `session_id`／`transcript`）；**檔名 `autosdd_resume_plan_<sid>.md` 只作加速**，不是判準（planner `--out` 是自由路徑，`session_resume_planner.py:1473`〔實讀〕；手動 `--arm-sentinel --out ~/x/plan.md` 的合法哨兵不得因檔名被誤收）。讀不出 ⇒ `owner=unknown`。
- **真值表**（`present` 來自 `list_jobs(label)` 精確查；`owner` 由 plan 軸＋`reap_verdict` 合成）：

| present × owner | `alive` | `dead` | `unknown` |
|---|---|---|---|
| **EXISTS** | 留（row 標 `kept`） | **收** | 留＋報 `unverifiable` |
| **ABSENT**（`[]`） | 無物可收 | 無物可收 | 無物可收 |
| **UNMEASURABLE**（`None`） | 不收、rc=1、出聲 | 不收、rc=1、出聲 | 不收、rc=1、出聲 |

  - `dead`＝下列**任一**：① `--plan` 檔不存在；② launchd 自報 `definition` plist 不在磁碟（殭屍態；Win 無此態）；③ `planner` 路徑檔不存在；④ `reap_verdict(...)` 回 `True`（逐字稿不存在／閒置 ≥6h 且狀態 ∈ `REAPABLE_WHEN_IDLE` `:64`）。
  - `alive`＝`reap_verdict` 回 `False` 且理由是 protected／仍活躍／`waiting`。
  - `unknown`＝`_transcript_dir()` 回 `None`（`:269`）∨ plan 在但 `parse_relay` 讀不出且無其他線索。
  - `foreign` 一律不進表。`--keep` 與 `_newest_session`（`:280-289`）保護面**原封不動**。
- **`gc()` 改動**：母體＝`sentinel_task_names()` ∪ `owned_jobs()` 的 label（任一為 `None` ⇒ 整體 `None`，沿 `:375-376`）；每列多 `kind`／`plan`／`definition`／`planner` 欄。**非前綴族（`kind=fixture`）第一階段只列不收**：`--apply` 對它們 `reap=True` 但 `applied=False`，需 `--apply-fixtures` 顯式旗標才動（§7 Q1）。**回收順序改為「先 `_remove_task` 拆排程、再 `_sweep_artifacts`」**（堵住 §1.2-2 tmpdir 被 job 重建）。
- **痕跡**：`_record_reap`（`:343-361`）對非前綴孤兒的 plan 父目錄常已不在 ⇒ `append_log` 失敗回 `""`；且 `_remove_task` 走同步 `disarm` 不會產生 `autosdd_sentinel_bootout_<label>.log` ⇒ 收掉一支 `T-*` 在磁碟上一字不剩（與 `:332-342` 立案的病同形）。**修法**：`gc()` 每次執行無論有無回收都 append 一行 JSON 報表到 `endurance_env.trace_dir()/autosdd_gc_report.jsonl`（`seen`／`kept`／`reaped`／`unverifiable` 四數＋逐筆 label／kind／why／`unregister_rc`／`after_listing`）——「沒觸發＝檔不長大」；`liveness_line` 加印「上次 GC 時間＋四數」。`~/.autosdd/traces/autosdd_sentinel_{launchd,bootout}_*.log` **刻意不刪**（本輪還原 8 次循環的唯一鑑識材料），只在報表列大小。

### 3.5 回收器與觸發點

| 時點 | 觸發 | 動作 | 憑證 |
|---|---|---|---|
| (a) 正常路徑 | 哨兵自我解除；測試 `addCleanup`；`gate_pg` finally | 既有 `disarm`／`rmtree`／`down -v` | mac `launchctl print` rc=113（`_readback is None`）；Win `Unregister` 後 `Get-ScheduledTask` 查無（`REMOVED` 字樣 `:340-343`）；`docker ps -a --filter name=autoclaude_ci_pg` 空 |
| (b) 執行單元收尾 | `python tools/run_root_unittests.py`（pre-push leg ②、三支 CI、開發機） | §3.6 圍籠：ledger 判紅＋A 面差分過 §3.4 判準後收＋B／C 面只列 | 同上＋圍籠痕跡檔每跑一次多一行 |
| (c) 下一位開工者 | SessionStart `spawn_sentinel_gc`（hook 零改動，`context_budget_guard.py:788-803`） | `gc()` 母體擴充後的 `--apply --keep <sid>`；fixture 族依 §7 Q1 | `autosdd_gc_report.jsonl` 長大；`autosdd_sentinel_boot_<sid>.log` 既有 `孤兒回收 spawn=True` 行（`:776`） |
| 人工 | `python tools/lib/sentinel_lifecycle.py [--apply] [--apply-fixtures] [--keep SID]` | dry-run 預設（`:368` 設計決定不變） | stdout 清單＋報表檔 |

runner 被 kill／timeout 時 (b) 不跑 ⇒ 由 (c) 兜底；(c) 是 detached、stdout DEVNULL ⇒ 其失效唯一可見面＝報表檔不長大與 `liveness_line`。**兩層互為備援，皆不改 hook 檔**。

### 3.6 全套 runner 圍籠 `leak_fence()`

- **接線（+1~2 raw line）**：`tools/run_root_unittests.py:720`〔實讀〕`return run_with_floor(_TESTS_DIR, MIN_TESTS)` 改為 `return sentinel_lifecycle.leak_fence(lambda: run_with_floor(_TESTS_DIR, MIN_TESTS))`，並在 `:129` lib 路徑注入之後補 `import sentinel_lifecycle`。**刻意不動 `run_with_floor`**（`:496`）：`:711-713` 明寫它被單元測試餵合成樹呼叫。本檔 raw 756/759〔實測〕（`SPECIAL_FILES` 棘輪 `AutoClaude/tools/check_loc_budget.py:176`）⇒ 最多 +3；若不夠先搬史料抵銷（記憶：護欄層成長用搬史料抵銷）。import 鏈 `sentinel_lifecycle → sentinel_lifecycle_arm／schedule_backend → endurance_env／schedule_backend_calendar` 全為 repo 內模組＋stdlib〔實讀〕，過 `ZeroDepEnvironmentDiscriminationTest`（`tools/tests/test_run_root_unittests.py:1959`）。
- **邏輯（住 `sentinel_lifecycle.py`）**：
  1. `os.environ.setdefault("AUTOSDD_SENTINEL_OFF", "1")`（§3.2 沙箱對整個套件行程生效；子行程繼承）；
  2. 真後端＝`schedule_backend.select(os.name, sys.platform)`（**顯式參數繞過沙箱**）；快照 A₀＝`owned_jobs()`（或 `None`）；B₀＝`Path(tempfile.gettempdir()).glob("autosdd_*")` 名稱集合；C₀＝`trace_dir()` 名稱集合（排除圍籠自己的檔）；
  3. 跑 `run` 得 `rc`；
  4. **ledger 面**：`sys.modules["schedule_backend"].SandboxBackend.ledger`（走測試同一個模組物件，避開 `lib.X` vs `X` 雙身分）非空 ⇒ 逐筆印 `label／plan／origin 測試幀` ⇒ **rc=1**（這就是「忘了注入」本身，決定性、無時間窗）；
  5. **A 面**：A₁∖A₀ 每筆過 §3.4 `orphan_verdict`：`dead` ⇒ `_remove_task`＋回讀＋rc=1；`alive`（另一活 session 在 700s 內剛武裝的合法哨兵）⇒ **只印「看見但保留」**，不動、不紅；`unknown` ⇒ 印 `unverifiable`，不動、不紅；A₀ 或 A₁ 為 `None` ⇒ 印「排程面量不到（載具＝X），本輪不判排程洩漏」，rc 不動；
  6. **B／C 面**：新增者**只列不刪**（並行 session 尚未武裝前落在 tmp 根的 `autosdd_resume_plan_<sid>.md`／`autosdd_ctxguard_<sid>.json` 沒有任何指紋可判所有權；刪了 ⇒ 之後 `arm()` 因「任務書不存在，拒絕註冊」（`schedule_backend.py:406-410`：`:406` 判式、`:409` 印訊息、`:410` `return 1, ""`；這是 `arm` 的**第二道**拒絕，首道在 `:401-405` planner 不可達／label 不安全）靜默失去續航）。B 面判準＝「`$TMPDIR` 根層 `autosdd_*` 前綴 ＋ 檔名內 session id 不在活 session 集合」（§1.2-7 已證殘骸跨兩個測試檔，逐檔點名無用）；
  7. **Docker／行程普查行**：`docker ps -a --filter name=autoclaude_ci_pg --format '{{.Names}}'` 三態（空＝量到零；`docker` 缺或 rc≠0＝**量不到**）；`pgrep -fl '[s]ession_resume_planner.py --(sentinel|resume)-tick'`（字元類自我否定；**`pgrep` rc=1 在此語意＝量到零**，輸出明寫此例外）／Win `Get-CimInstance Win32_Process | Where-Object CommandLine -like '*session_resume_planner.py*--*-tick*'`；只印不殺；
  8. append 一行 JSONL 到 `trace_dir()/autosdd_leak_fence.jsonl`；回 `max(rc, fence_rc)`。圍籠自身例外 ⇒ 印 stderr、痕跡寫 `fence_failed`、**不得把套件結果變綠**。
  9. `CI` 環境變數有設 ⇒ A 面只印不判（CI Linux `NoCarrier` 回 `[]` 本就恆空，明寫比隱含好）。
- **誠實劃界**：A 面差分是機率式偵測（慢機／CI 全套 >900s 時，測試種下的 job 在 tmpdir 被 addCleanup 刪後、下一 tick 走「任務書不存在 ⇒ 自我解除」，殘骸在收尾快照前自己消失——這正是 T-f4b 事後 `launchctl list` 看不到、卻在 `bootout_T-f4b.log` 留下 5 筆的原因）；**決定性偵測是第 4 步 ledger**，A 面只是第二層。

### 3.7 Docker：`gate_pg` 無條件收尾

- **家**：`AutoClaude/tools/local_ci_gate.py:623-648`（count_loc 357/750〔實測〕；`:624-630` 為 docstring）。
- **改法**：`up --wait`（`:631`）之後整段包 `try/finally: _run_quiet([*_PG_COMPOSE, "down", "-v"])`；`:641` alembic 失敗分支的顯式 `down` 移入 finally（保住 `test_gate_pg_alembic_failure_tears_down_and_fails` `AutoClaude/tests/tools/test_local_ci_gate.py:298-307`「恰好一次 down」，斷言在 `:305`〔實讀〕）；**`up --wait` 失敗（`:631-633`）也 `down -v`**（半起的 `autoclaude_ci_net` 同樣是殘留）⇒ 同輪改 `test_gate_pg_compose_up_failure_skips_alembic` `:310-317` 的 `:317 quiet_calls == []  # 容器沒起來，無需清理` 為「alembic 未跑、down 有跑」（衝突取捨：資源回收目標 > 既有斷言字面；Rule 7 表面衝突、不平均）。
- **誠實劃界（為什麼要 try/finally 而不是多補幾個 `down`）**：`_stream` 是裸 `subprocess.run(cmd).returncode`（`:479-481`），KeyboardInterrupt／OSError 會從 `:631`／`:639`／`:643` 任一處外拋——那正是現況兩處 `down` 都接不到、只有 finally 接得到的路徑；`_run_quiet` 已吞 OSError（`:484-492`），放進 finally 不會製造第二個例外遮蔽原例外。KeyboardInterrupt 是 `BaseException`，finally 仍跑、例外照外拋。
- **憑證**：finally 後印 `[PG teardown] docker ps -a --filter name=autoclaude_ci_pg → <空|names>`；`docker` rc≠0（daemon 未起，本 session 即此態〔實測〕）⇒ 印「量不到」不判。
- **孤兒容器**：§3.6 普查行與 `gc()` 報表**只印建議指令** `docker compose -f AutoClaude/docker-compose.ci.yml down -v`，**不自動 down**（容器可能是使用者手動起來做 PG e2e）——與排程 job 的處置**刻意不同**。Docker Desktop app 與其 `com.docker.*` LaunchDaemons（root）不在回收面，維持 `useMacWin.md:118` 人工收尾。

### 3.8 平台雙軌對照

| 面 | macOS（launchd） | Windows（schtasks） | Linux／CI |
|---|---|---|---|
| 列舉全部 | `launchctl list`（三欄 `PID\tStatus\tLabel`） | `Get-ScheduledTask`（**不用** `schtasks /query`，實測假陰性） | `NoCarrier` 回 `[]` |
| argv 回讀 | plist `ProgramArguments` ＋ `launchctl print` 的 `arguments = {…}`（`_readback` `:634`） | `(Get-ScheduledTask).Actions.Execute／Arguments` | n/a |
| 定義檔 | launchd 自報 `path =`（殭屍＝該路徑不在磁碟） | `TaskPath`（無殭屍態） | n/a |
| 精確查名 | `list_jobs(prefix=task)` → `_labels_with_prefix`（`schedule_backend_calendar.py:40-42` `startswith`）再過濾 `== task` | `-like '<task>*'` **含萬用字元語意**：label 含 `[`／`?`／`*` 會假陰性 ⇒ 每 tick 重掛回歸。修法：`_unsafe_name`（`schedule_backend_calendar.py:32-34`）擴到拒絕 `[]*?`（兩平台同一判準） | n/a |
| 拆除憑證 | `launchctl print` rc=113（`_readback is None`） | `Unregister-ScheduledTask` 後 `Get-ScheduledTask` 查無（`REMOVED`） | 回 0 但不宣稱拆成功（`:787-788`） |
| 行程普查 | `pgrep -fl '[s]ession_resume_planner…'`（rc=1＝量到零） | `Get-CimInstance Win32_Process` | 同 mac |
| 暫存根 | `$TMPDIR`（`/var/folders/…/T`） | `%TEMP%` | `/tmp` |
| 持久痕跡 | `~/.autosdd/traces` | `%USERPROFILE%\.autosdd\traces` | 同 |
| 沙箱旗標設法 | `AUTOSDD_SENTINEL_OFF=1 python …` | `$env:AUTOSDD_SENTINEL_OFF='1'; python …`（**無** `VAR=1 cmd` 前綴語法） | 同 mac |

### 3.9 失效可偵測性總表

| 機制 | 它壞了會怎麼看見 |
|---|---|
| §4 精確查名回歸 | 同一 label 的 `sentinel_armed_drift_healed` 連續出現（每 900s 一筆）；`gc()` 報表 `drift_heals` 欄 >1 |
| §3.2 沙箱沒生效 | 圍籠 A 面抓到真 job；`~/.autosdd/traces/autosdd_sentinel_bootout_T-*.log` 再長大 |
| §3.2 沙箱外洩到 production | 憑證含「未武裝」進 `autosdd_resume_log_*.jsonl`；`--verify-schtasks` rc=1；`liveness_line` 印 `backend.name` |
| §3.6 圍籠沒跑 | `autosdd_leak_fence.jsonl` 不長大 |
| §3.4 gc 沒跑／誤收 | `autosdd_gc_report.jsonl` 不長大；誤收方向由 dry-run 觀察期（§7 Q1）與 `after_listing` 回讀欄可稽核 |
| §3.7 容器殘留 | 下次 `up --wait` 撞固定 `container_name` fail-loud；普查行印非空 |

---

## 4. 對 T-r95／T-f4b 型洩漏的直接止血

事實底稿 §6 的三個結構事實（§1.3）各對一層，**缺一不可**，每層各有紅綠自證：

1. **精確查名**（`tools/lib/quota_escalation.py:349`〔實讀〕，淨 LOC 0）：`sentinel_lifecycle.armed_but_missing(task, sentinel_lifecycle.sentinel_task_names())` 改為 `armed_but_missing(task, _exact_listing(task))`，其中 `_exact_listing`＝`schedule_backend.select().list_jobs(task)` 過濾 `== task`（結果只可能 `[task]`／`[]`／`None`）。非前綴 label 從「結構上永遠 missing」變成三值；`None` 仍走「量不到不算漂移」（`armed_but_missing` `sentinel_lifecycle.py:192-194` 不變）。這一層治的是**自我永續**（§1.2-2）：即使有人真種下 `T-x`，它不再每 tick 自癒重掛。**同輪必修既有鎖**：`test_context_budget_guard.py:5149-5253` 四支 heal-drift 測試以 `patch.object(sentinel_lifecycle, "sentinel_task_names", ...)` 驅動且內嵌 `_StubBackend`（`:5159／:5194／:5217`）只實作 `arm` 沒有 `list_jobs` ⇒ 改後 AttributeError；須補 `list_jobs` 並把 seed 搬到假後端。
2. **`_heal_armed_drift` 尊重既有釘＝第二接縫的呼叫端護欄**（+2 行）：`os.environ.get(guard.SENTINEL_OFF_ENV)`（`quota_escalation.py:68` 已 import guard，零成環）有設 ⇒ 不 arm、落 `sentinel_armed_drift_skipped_pinned` 痕跡。讓 `setUpModule` 的釘管到第二接縫（`:353`）；與 §3.2 沙箱互為備援（沙箱在 `select()`、此在呼叫端——任一層被繞過另一層仍在）。**刻意否決** SA 的「連續第 2 筆 healed 即停止重掛」棘輪：為已被第 1 層根治的病再加一道會誤傷合法漂移（人手 Unregister 兩次）的判準。
3. **測試面**：
   - (a) 修 `:4071` 所屬測試（def `:4042`）補 `patch.object(sb, "select", return_value=_StatefulFakeSchedulerBackend())`（與 `_tick` helper `:2054-2055` 同藥方）——這是絆線唯一逐字命中的種下站。
   - (b) 新增 `SchedulerHygieneTest`（比照 `TmpdirHygieneTest` `:183`）AST 鎖。**射程＝兩支 tick 對稱**，直接引用既有 `:7944 _TICK_FUNCS = ("_sentinel_tick", "_resume_tick")`，不另寫第二份清單——既有註解逐字寫「只判前者等於把一半的路徑交給運氣」，本鎖不得與之衝突。理由：`_resume_tick`（`session_resume_planner.py:1167`）**不**呼叫 `patrol_housekeeping`（唯一站點 `:1368` 在 `_sentinel_tick` 內），但四條分支都真的到達 `schedule_backend.select()` 的 `arm`／`disarm`：stop 分支 `:1213 _schtasks_remove` → `:913 select().disarm`；PATROL_HANDBACK 分支 `:1226 _schtasks_remove` ＋ `:1244 _arm_sentinel` → `:1276 _register_and_record` → `:960 register_endurance` → `:744 select().arm`；rearm 分支 `:1258 _register_and_record`（同鏈）；resume 分支 `:1266 relay_machine.settle_window` → `relay_machine.py:289 planner._arm_sentinel`。**判準＝二擇一接縫**：直呼 `_sentinel_tick`／`_resume_tick`／`patrol_housekeeping` 的 `Call` 所在函式體內，要嘛有 `patch.object(sb, "select", …)`，要嘛同時 patch 掉該 tick 可達的全部排程接縫——`_schtasks_remove` ＋ {`_register_and_record` | `register_endurance` | `_arm_sentinel`} 之一（接縫名單直接引用 `:7940 _TICK_DISPOSALS`，避免第二份清單）。以此判準現查：9 個 `_resume_tick` 直呼站點（`:1419／:3153／:3197／:3408／:3503／:3545／:3855／:3914／:4033`）皆走第二種接縫（例：`:1412-1417` patch `_schtasks_remove`＋`_register_and_record`；`:4030-4032` patch `register_endurance`）⇒ **全部合規、不假紅**；`:4071` 仍是唯一違規站。**紅綠自證**：測試字串內餵 AST 一個故意只 patch `probe_quota`／`tick_plan`、不 patch 任何排程接縫的 `_resume_tick` 假站點，鎖必須判紅。**誠實劃界**：`select().credential_key`／`.name` 這類唯讀屬性存取（`:950`、`:962`；`:4033` 站點就真的在真後端上讀 `credential_key`）不算副作用，鎖不判；判的是 `arm`／`disarm` 可達性。
   - (c) GHOST 測試（def `:2402`）在沙箱下從真機副作用變成沙箱路徑（其斷言「任務書骨架寫出」「不被『逐字稿還不存在』擋下」照樣成立），`addCleanup(_schtasks_remove)`（`:2420`）透傳到真後端仍是「查無、無害」；mac／Win 皆不再有測試真跑 `--arm-sentinel`——**這是把洩漏源換成誠實的射程缺口**，見 §7 Q2。

**誠實劃界**：本輪絆線只實證 T-f4b 的種下點（`tripwire_hits.log`），T-r95 今日入口未歸因；三層止血對任何入口一體適用、不依賴逐站找到，但缺陷帳本只能寫「T-f4b 站點已實證（`:4071` → 第二接縫 `:353`）、T-r95 入口未歸因、GHOST 子行程真武裝已實證、結構性修法覆蓋三者」。

---

## 5. 落地順序（每步可獨立驗收；驗收數字一律當回合現跑）

> 本節所有「候選類別.方法」形態的測試名皆為**尚未落地的候選命名**（點分寫法刻意不用裸 `test_` 反引號，以免被 `TestR78GhostSymbolClaims` 判為幽靈符號）；落地時以實際 def 名回填。

| 步 | 內容 | 驗收測試名（新增／既有） | 紅綠自證 |
|---|---|---|---|
| 0 | **主控現查**：`launchctl list \| grep -Ei 'AutoSDD\|T[-_]\|UNITTEST'`（`T[-_]` 才抓得到 `T_R81`）；`ls $TMPDIR \| grep autosdd_`；`ls ~/.autosdd/traces \| grep -E 'T-f4b\|T-r95\|T_R81'`；不得沿用任何提案的舊讀值 | n/a | 貼輸出 |
| 1 | §4-1＋§4-2：精確查名＋尊重 SENTINEL_OFF；修四支 heal-drift 測試 stub | `HealArmedDriftTest.test_a_non_prefixed_label_already_present_is_not_re_armed`（假後端 seed `T-x` 後 `arm_calls == []`）；`HealArmedDriftTest.test_a_pinned_process_never_re_arms_and_leaves_a_skipped_trace`；既有 `:5149-5253` 四支續綠；`SchedulerBackendNeverTouchesRealSchtasksTest` `:5547` 的 `arm_calls` 非空續有鑑別力 | 修前第一支必紅（現況每 tick 重掛） |
| 2 | §4-3：修 `:4071`＋`SchedulerHygieneTest` AST 鎖（射程＝`_TICK_FUNCS` 兩支＋`patrol_housekeeping`；二擇一接縫判準） | `SchedulerHygieneTest.test_every_direct_tick_call_isolates_the_scheduler`（現查違規＝`:4071` 一站；`_tick` `:2059`／`:4733` 與 9 個 `_resume_tick` 站點已合規）；`SchedulerHygieneTest.test_a_resume_tick_call_that_patches_no_scheduler_seam_is_red`（AST 餵假站點的紅綠自證）；既有 `:7944` 家族續綠 | 鎖先於修落地 ⇒ 必紅一次；落地後以 `grep -n 'sb, "select"' tools/tests/test_context_budget_guard.py` 重取行號寫帳本 |
| 3 | §3.2 `SandboxBackend`＋`select()` 第三縫＋`_BACKENDS` 更新 | `SandboxBackendTest.test_a_direct_sentinel_tick_without_injection_never_reaches_a_real_carrier`（重演 `:4071` 形態、對 `LaunchdBackend.arm`／`SchtasksBackend.arm` 掛 `_boom`）；`SandboxBackendTest.test_explicit_platform_arguments_always_return_the_real_backend`；`SandboxBackendTest.test_the_sandbox_credential_says_it_is_not_armed`；`SandboxBackendTest.test_unattended_ignores_the_sandbox`；既有 `SelectIsTheOnlyPlatformQuestionTest`／`BackendInterfaceIsSymmetricTest` 續綠 | 第一支修前必紅（就是 T-f4b 那條路） |
| 4 | §3.3 `owned_jobs()` 四後端＋`owned_record` 純函式 | `OwnedJobsTest.test_launchd_reads_argv_from_plist_and_from_readback_for_zombie_labels`（合成 plist 目錄＋假 `_run`，含一個 plist 已刪的 label）；`OwnedJobsTest.test_a_job_whose_argv_lacks_the_planner_is_foreign`（nightly／`com.google.*` 形態負對照）；`OwnedJobsTest.test_a_planner_path_that_no_longer_exists_is_ours_and_dead`；`OwnedJobsTest.test_windows_owned_jobs_parses_actions_arguments`（注入 `run_powershell` 假輸出）；`OwnedJobsTest.test_a_failed_enumeration_is_unmeasurable_not_empty`；`CarrierPrimitivesHaveOneHomeTest` 續命中兩家 | mac 真機 dry-run：兩支活哨兵在列為 `sentinel`、`com.autoclaude.nightly` 與三支 `com.google.*` 為 `foreign`（貼輸出） |
| 5 | §3.4 `orphan_verdict` 真值表＋`gc()` 母體擴充＋先拆再 sweep＋`autosdd_gc_report.jsonl` | 9 格逐格具名測試（含 `OrphanVerdictTest.test_unknown_owner_is_never_reaped`）；`OrphanVerdictTest.test_gc_reaps_the_schedule_before_sweeping_artifacts`；`OrphanVerdictTest.test_gc_appends_one_report_line_even_when_nothing_is_reaped`；`OrphanVerdictTest.test_a_zombie_label_whose_plist_is_gone_can_still_be_disarmed`（假 `_run`：plist 缺、`print` rc=0 ⇒ `_remove_task` 走 bootout 並回讀 113）；**既有 `:8290` `test_gc_never_collapses_unknown_into_missing` 與 `:8314` `_apply_once` 須補 patch `owned_jobs` 回 `[]`** | 人工種一支 `T-test` 指向不存在 plan ⇒ dry-run 判 `fixture／dead`；`--apply-fixtures` 後 `launchctl print` rc=113、報表檔變大 |
| 6 | §3.6 `leak_fence()`＋runner `:720` 接線 | `LeakFenceTest.test_a_non_empty_sandbox_ledger_names_the_test_and_reds_the_run`；`LeakFenceTest.test_a_dead_job_that_appears_during_the_run_is_reaped_and_reds_the_run`；`LeakFenceTest.test_an_alive_job_that_appears_during_the_run_is_kept_and_not_red`；`LeakFenceTest.test_unmeasurable_enumeration_is_said_out_loud_and_never_reaped`；`LeakFenceTest.test_new_temp_and_trace_files_are_listed_never_deleted`；`LeakFenceTest.test_the_fence_appends_exactly_one_trace_line_per_run`；`LeakFenceTest.test_main_is_wrapped_by_the_leak_fence`（AST 讀 runner `main` `:699`） | 故意保留步 2 修前版本跑全套 ⇒ runner rc=1 並列名 `:4071`；修後 rc=0；連跑兩次 `wc -l ~/.autosdd/traces/autosdd_leak_fence.jsonl` 各 +1；`check_loc_budget --json` runner ≤759 |
| 7 | §3.7 `gate_pg` try/finally＋憑證行 | 候選 pytest 函式 test_gate_pg_tears_down_when_pytest_is_interrupted（未落地）；候選 pytest 函式 test_gate_pg_compose_up_failure_still_tears_down（未落地）（改 `:310-317`，斷言 `:317`）；既有 `:298`／`:320` 續綠 | 需 Docker 開著才能真機驗（本 session 未起，標「量不到、待驗證」） |
| 8 | 收尾單人窗口：帳本新立列「DEF-200-239 的 mac 孿生＋第二接縫」（T-f4b 站點實證／第二接縫 `:353`／GHOST 子行程真武裝／殭屍態／mac 零現查）＋ DEF-200-239 補述；ADR-XPLAT-004 §2 補「回收側」一節、ADR-XPLAT-014 §4.1 表補 `owned_jobs`／`orphan_verdict`；根 CLAUDE.md〈現查指令速查表〉加「資源殘留普查」一列（改前先盤 9 族鎖）；`useMacWin.md:118` 指向普查指令；ONBOARDING §7 表① 由 `sync_onboarding_baselines.py --write` 回填（commit 前最後一步）；push 前跑全套根層閘門 | `TestR74IronLawMechanismAccounting` 等根 CLAUDE.md 釘住測試 | 並行包禁寫帳本 |

---

## 6. 風險與劃界（誠實寫出不做什麼）

**風險**
- **LOC 三重稅**：`schedule_backend.py` count_loc 360/400〔實測〕，§3.2＋§3.3 約 +40 assertion 行 ⇒ 破線。**docstring 轉 `#` 註解對 `count_loc` 是零效果**（`check_loc_budget.py:294`：敘事＝docstring／裸字串 ∪ 整行 `#`，兩者同桶）；只能真搬純函式到 `schedule_backend_calendar.py`（44/400）或搬程式碼；`quota_escalation.py` 377/400 只餘 23。`run_root_unittests.py` raw 756/759 只准 +3。落地當回合先跑 `check_loc_budget --json`。
- **沙箱誤留在真 shell**：`AUTOSDD_SENTINEL_OFF` 本就是「哨兵關掉」逃生口，語意一致；但使用者若忘了它，`--arm-sentinel` 會靜默進沙箱——緩解＝憑證逐字「未武裝」、`--verify-schtasks` rc=1、`AUTOSDD_UNATTENDED` 下忽略。
- **`gc()` 射程擴大後誤收代價擴大**：以 `--apply-fixtures` 顯式旗標＋dry-run 觀察期（§7 Q1）與三值 `owner` 軸緩解；`--keep` 寫進 CLI help。
- **A 面差分假紅**：另一活 session 在全套期間新武裝的哨兵，已由「過 `orphan_verdict`、alive 只印不紅」排除；但若其 plan 尚未寫出 RELAY 塊 ⇒ `unknown` ⇒ 印 `unverifiable`、不紅（正確方向）。
- **`SchedulerHygieneTest` 假紅／假綠兩向**：判準若只認 `patch.object(sb, "select")` 會把 9 個合法 `_resume_tick` 站點判紅（C23 判決已證）；若只認接縫名單又會漏掉直接 `import schedule_backend` 後呼叫類別的形態（那一半交給 §3.2 沙箱＋§3.6 ledger）。兩向都以 AST 餵假站點的紅綠自證釘住。
- **T-r95 入口未歸因**：帳本敘述受限（§4 末段）；建議補一次帶 `sys.modules` 身分快照的全套重演。
- **Windows 格全部未實測**：對稱鎖只守介面不守語意；`Actions.Arguments` 引號形態、pythonw 載具下 `run_powershell` 輸出編碼、`-like` 萬用字元，皆需持 Windows 機器者以 `Get-ScheduledTask | Select TaskName,@{n='Args';e={$_.Actions.Arguments}}` 貼輸出後才可宣稱；落地時加 `@skipUnless(win32)` 且帶 `[WINDOWS-NATIVE-ONLY]` 標籤（runner `:713` 靜態掃描擋漏標）。
- **既有鎖會被踩到（同輪修）**：`r83:340` `_BACKENDS`；`test_context_budget_guard.py:5159／:5194／:5217` stub 缺 `list_jobs`；`:8290／:8314` 需 patch `owned_jobs`；`test_local_ci_gate.py:310-317`（`:317` 斷言）；`:70` `setUpModule` docstring「一律不准碰真的排程器」改寫為「不准**寫**、唯讀列舉可」（圍籠在同行程真跑 `launchctl list`）。

**不做什麼（劃界）**
- **不**回收 Docker Desktop 本體與其 `com.docker.*` LaunchDaemons（root、使用者安裝）；**不**自動 `down` 孤兒容器。
- **不**刪 `~/.autosdd/traces/autosdd_sentinel_{launchd,bootout}_*.log`（鑑識面）；**不**刪暫存根／痕跡目錄的任何新出現檔（只列）；`autosdd_resume_log_*.jsonl` **不**納入 `reap_plans` 刪除族（與 `sentinel_lifecycle.py:340-342` 對撞）。
- **不**殺任何背景行程（`pgrep` 只印）；Claude 子 agent／Workflow／Monitor 由 harness 持有。
- **不**處理樹外 venv、git worktree（唯讀普查；淨減法只准收尾單人窗口）、通知佇列（既有機制）。
- **不**新增 hook 事件、**不**改 `context_budget_guard.py`、**不**新增 `tools/*.py`、**不**另立資源帳本。
- **不**治其他測試檔的裸 `mkdtemp`（`TmpdirHygieneTest` 只管本檔；`test_mac_endurance_r83.py:1394` 那支殘骸屬發現輪）。
- **不**處理 `com.autoclaude.nightly` 狀態欄 1（健康問題另案）；**不**碰 `com.google.*` 三支 plist（`foreign`）。

---

## 7. 待掌舵者裁決的問題（最多 3 題）

**Q1 非前綴（fixture）族的 `--apply` 何時開？**
- A. **先觀察一輪**：`gc()` 對 fixture 族只列不收（需 `--apply-fixtures`），看一輪 SessionStart 的 `autosdd_gc_report.jsonl` 後再由 hook 端加旗標（hook 檔餘裕 0，需先搬史料）。
- B. 落地即真收（SessionStart `--apply` 直接動）。
- **推薦 A**：`reap_verdict` docstring `:229-234` 就是同一個病在最貴處犯過一次；dry-run 的價值在清單本身已兌現。

**Q2 GHOST 測試（def `:2402`）在沙箱下失去真機射程，怎麼補？**
- A. **另立 opt-in** `[MANUAL-REAL-SCHEDULER]` 測試（預設 skip；人工顯式 `AUTOSDD_SENTINEL_OFF=` 清空並帶旗標時才真跑，cleanup 在**同一個 env** 下 subprocess `--remove-schtasks`），帳本明寫「mac／Win 預設全套不再有真武裝射程」。
- B. 保留 GHOST 真副作用（`_isolated_env(real_scheduler=True)` 並 pop 沙箱旗標），cleanup 改同 env 下拆。
- **推薦 A**：B 保留了「測試行程被 kill 即永久殘留」那一半（事實底稿 §6 第 2 點實證：清理只靠 `addCleanup`）；A 把真機驗證變成人工、有意識的動作。

**Q3 圍籠 rc=1 在 pre-push 是否擋 push？**
- A. **擋**：洩漏就是缺陷，與其他根層閘門同等；今日 5 筆 `bootout_T-f4b.log` 就是 5 次 pre-push／全套各真種一次的證據。
- B. pre-push 只印、CI 與開發機手跑才判。
- **推薦 A**：ledger 面是決定性的（忘了注入＝測試本身寫錯）；A 面已排除活哨兵假紅；`CI` 下只印不判已另處理。
