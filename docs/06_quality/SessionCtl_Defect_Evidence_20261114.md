# sessionctl 第一段缺陷證據（DEF-200-580～584 的詳情；帳本列只留索引）

> 設計全文＝`docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` §2.13；規格＝`docs/03_testing/contracts/TCS-SessionCtl-20261113.md`。落款日 2026-11-14。

## DEF-200-580　無人選路只量檔案位元組

- **現象**：sid `d4ed2654-9181-4df1-a6e6-2d712956e23b` 的事件檔 `autosdd_resume_log_…` 2026-11-13T07:32:03 `route_chosen`＝SESSION_RESUME，理由「逐字稿 20,518,438B ≤ 上限 33,554,432B」；`~/.autosdd/traces/autosdd_resume_cost.jsonl` 同 sid 第一回合 `cache_creation_input_tokens`＝138,811、上下文約 60 萬 token。其後無人窗口以 SendMessage 續棒 40～60 萬 token 的舊子代理 44 分鐘，08:16 `relay_stopped` why=band，五小時窗 95～98%。掌舵者原話：「有背景Subagent執行, 沒有被掌控! 這是嚴重問題」。
- **修法**：選路改量續跑成本（ADR §2.13.2）：R1 上下文 token（feed→逐字稿 usage→位元組估計標 `estimated`）、R2 逐字稿 `compact_boundary` 計數、R3 上次續跑 `cache_creation_input_tokens`，任一成立即 FRESH；門檻入 `ENV_SPEC` 且只准下修；FRESH prompt 加兩條硬規則（不得 SendMessage 續舊代理、第一個動作重驗）；判定核心搬入 `tools/lib/sessionctl/switch.py`，planner 留委派。
- **鎖**：`tools/tests/test_sessionctl_switch.py` 的 RouteTest、ThresholdTest（AT-SC-01～18，含 E1 真實數值重放）。
- **劃界**：R1 位元組估計比值 40 B/token 為出廠值（實測點 E1 約 34、E2 約 53，只在 feed 與逐字稿 usage 皆缺時用）；SendMessage 續棒閘屬第二段（DEF-200-584）。

## DEF-200-581　撞線等待中的過期哨兵會續跑舊 session

- **現象**：哨兵 `AutoSDD_Sentinel_f1522ddb-bdcf-4104-bb81-614c1118fa9d` 自 11/9 起 `waiting`、`allow_resume: true`、NextRunTime 2026/11/15 02:02；逐字稿 29,652,867 B、ctx 556,777；其間更新的 session 已做完後續工作，不處理則 11/15 無人續跑一個四天前的 session。主控已手動拆除該排程。根因：`waiting` 是唯一永不收的狀態（`REAPABLE_WHEN_IDLE` 刻意不含它），`sentinel_decide` 的撞線分支優先於 `superseded_by`（原只接在 halt 標記上）。
- **修法**：SUPERSEDED（ADR §2.13.3）：本 session 閒置 ≥ `AUTOSDD_STALE_SESSION_HOURS` 且同專案另有 session 於其後累積達 `should_arm` 門檻的真實工作 ⇒ 不續跑、自我解除、狀態 `superseded`、痕跡 `sentinel_superseded`、handback；`sentinel_decide`（`LIMIT_SPEND` 之後、撞線分支之前）與 `_resume_tick`（探測前）兩處同一判準；`reap_verdict(superseded=)` 對 `waiting` 一致；讀不到其他逐字稿時不判。
- **鎖**：`test_sessionctl_switch.py` 的 SupersededTest、E2ReplayTest、ReapSupersededTest（AT-SC-19～33，含 E2 真值重放）；`test_context_budget_guard.py` 的 SentinelDecisionTest（AT-SC-25～27）。
- **劃界（主控裁決）**：沒有撞線事件的過期 session 走既有閒置解除路徑，狀態 `disarmed`，不寫 handback。

## DEF-200-582　洩漏圍籬把活著的互動 session 合法武裝的哨兵判成洩漏

- **現象**：`~/.autosdd/traces/autosdd_leak_fence.jsonl` 2026-11-13T20:48:35 一筆 `rc: 0, fence_rc: 1`，洩漏清單只有發起該次全套的互動 session 自己的哨兵；新 session 的 hook 在全套跑到一半時合法武裝，全套被判紅而程式碼無問題。
- **修法**：`leak_fence` 差集內的哨兵 job 若其 sid 的真實逐字稿在圍籬起點後有對話記錄（`transcript_activity.sessions_active_since`，沿用單一家判準）⇒ 只出聲、不判死，痕跡新欄 `live_session_jobs`；假 job（無真實逐字稿活動或活動早於圍籬起點）照舊判死。
- **鎖**：`test_context_budget_guard.py::LeakFenceTest`（AT-SC-89／90 正負向）。

## DEF-200-583　第一波推送守門的跨平台八個成因

| # | 平台 | 測試／標的 | 成因 | 修法 |
|---|---|---|---|---|
| 1 | Linux、macOS | AT-749-9-2 | 測試寫死 POSIX 備註為空，實作回 killpg | 預期改 killpg（TCS-P7 勘誤 E-72） |
| 2 | Linux、macOS | AT-749-12 系列、5-E 系列 | 測試把全域 `sys.platform` 偽成 win32，`resolve_git` 改找 `git.com`／`.exe` 而 POSIX 解析不到 | `TestOsTasks.win()` 先解析真 git 並釘住（E-73） |
| 3 | Linux、macOS | AT-749-5-E-13 | 假 gpg 是 `.cmd`，POSIX 不可執行 | POSIX 用 chmod 755 的 sh 腳本（E-74） |
| 4 | macOS | AT-749-9-E-2／E-3／E-4、9-6 | `pid_started_at` 用 BSD `ps` 沒有的 `etimes=`（實作缺陷） | `runner.py` 改 `etime=`＋`_parse_etime`（E-75） |
| 5 | macOS | AT-749-5-E-2-b | hooksPath 絕對形態以字串比對，`/var`→`/private/var` 不等（實作缺陷） | `pushcontent._same_dir` resolve 後同目錄才收（E-75） |
| 6 | macOS | AT-749-5-10 | 測試允許集合不含實作放行的 POSIX `LC_*` 前綴 | 補同一前綴判準（E-74） |
| 7 | GitHub Windows runner | AT-749-9-2 | 測試量整段 `patrolpush.run`（取鎖、數十次 git、收尾）而非牆鐘那一次 `run_argv`；共用 runner 實測 10.047 秒對門檻 8 | 改量牆鐘那一次 `run_argv` 自身耗時，門檻不變（E-76） |
| 8 | GitHub Windows runner | AT-749-5-E-2-b | 暫存路徑為 8.3 短名且可帶 `\\?\` 前綴，`_same_dir` 字串比對不等 | `_same_dir` 剝 `\\?\X:` 前綴（E-77），新增 AT-749-5-E-2-c |

另：Console 側 compose 展開 JSON 省略 `create_host_path`，使 `test_AT_966_2_E_1` 一條斷言紅；移除該項斷言（Console TCS 勘誤 E-26）。

- **驗證（當回合）**：Windows 全檔 p7 152 條 OK、engine-bridge `tests/test_si_deploy_config.py` 17 passed；Linux 容器（ubuntu、python3.12）修前重現 11 條紅、修後 151／152（餘 1 條為容器偽影：python 在 root 擁有的 `/usr/local`，CI 的 toolcache python 該條本來就綠）；手動破壞 `_timeout_kill` 使 AT-749-9-2 轉紅。
- **尚未驗證**：macOS 與 GitHub Windows runner 以下一次 CI 結果為憑，結果見 commit 訊息。

## DEF-200-584　sessionctl 第二段尚未實作（open）

交接包（機械層＋主控層、公告／ack／過期）、三條切換路與洗環境、SendMessage 續棒成本閘（無人阻斷）、背景代理名冊與 `sessionctl status`／`stop`（pid 身分驗證）、Stop 出聲、無人窗口結局與 `pct_before`／`pct_after`、`--pace` 模型建議、新 hook `sessionctl_guard.py`；對應 FR-SC-05、10～23 與 AT-SC-34～88（設計定案於 ADR §2.13.4～§2.13.8）。`AUTOSDD_RESUME_AGENT_TOKENS`、`AUTOSDD_HANDOFF_TTL_HOURS`、`AUTOSDD_ROSTER_QUIET_MINUTES`、`AUTOSDD_SESSION_SWITCH_MODE` 已入 `ENV_SPEC`，消費端尚無。`.claude/` 下的 hook 由主控親套。承接輪次 R215。
