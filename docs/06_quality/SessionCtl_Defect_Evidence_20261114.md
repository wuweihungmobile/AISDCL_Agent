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

- **驗證（當回合）**：p7 全檔條數——跨平台修復第一包後 152 條（Windows 全過；Linux 容器 151／152，餘 1 條為容器偽影：python 在 root 擁有的 `/usr/local`，CI 的 toolcache python 該條本來就綠）；第二包（成因 8，AT-749-5-E-2-c）加一條後 153 條；本輪 CI 修復包再加 `_parse_etime` 純函式測試一條（AT-749-9-E-5）後 154 條，AT-749-5-E-2-c 改為各平台都真跑的同一方法（不再是 Windows 限定 skip）。engine-bridge `tests/test_si_deploy_config.py` 17 passed；手動破壞 `_timeout_kill` 使 AT-749-9-2 轉紅。
- **已驗（2026-11-14，`ed9bc12d`）**：macOS 與 GitHub Windows runner 以 CI 為憑——windows-compat-ci 通過；Linux、macOS 的測試失敗已清零，剩餘紅燈只來自本批 Windows 限定 skip 觸發的 skip 治理閘（root-infra-ci、macos-compat-ci），由 TCS-P7 勘誤 E-78 把該測試改為各平台都跑而消除。

## DEF-200-584　sessionctl 第二段（已結案，2026-11-14）

交接包（機械層＋主控層、公告／ack／過期）、三條切換路與洗環境、SendMessage 續棒成本閘（無人阻斷）、背景代理名冊與 `sessionctl status`／`stop`（pid 身分驗證）、Stop 出聲、無人窗口結局與 `pct_before`／`pct_after`、`--pace` 模型建議、新 hook `sessionctl_guard.py` 皆已落地；對應 FR-SC-05、10～23 與 AT-SC-34～88。實作事實與契約偏離見 ADR-XPLAT-004 §2.13.13。

- **鎖**：`tools/tests/test_sessionctl_{handoff,roster,hooks,modelmix}.py`；hook 註冊面由 `test_check_hooks_liveness.py::_REGISTRATION_BASELINE` 與 `test_sessionctl_hooks.py::GuardRegistrationTest` 釘住。
- **SPECIAL 棘輪重釘**：`.claude/hooks/context_budget_guard.py` 1089→1104（+15：`switch_advice` 14 行函式＋1 行呼叫）。為何不可再壓縮：交接包判準與產生全在 `tools/lib/sessionctl/handoff.py`，hook 內只剩 lazy import＋try/except；該 hook 由 `runpy` 起、不能反向 import lib，接線必須住在本檔（ADR §2.13.8）。`tools/lib/` 側 `sentinel_lifecycle.py` 399／400 行、未破。
- **兩個整合缺陷（第二段兩半對接時已修，未另立列）**：`roster._handoffs` 查 `<檔名>.md.ack` 而 `handoff.ack` 寫 `<stem>.ack`（已 ack 的包永遠被當未接手）；spawn 痕跡 `at` 取等完逐字稿之後的時刻使 stop 的時刻比對失準。
- **仍待真機**：TCS §3 的 V1～V8（含互動畫面是否顯示 Stop 的 `systemMessage`）。

### 第二段獨立 QA 與修復（2026-11-14）

獨立 QA 鏡審查 `da15a928`：P1 一件、P2 五件、P3 八件；76 條突變 14 條存活（結論 CONDITIONAL）。處置：

- **P1**：`PlannerWiringTest` 受載入順序影響（別的測試檔先載入真 `handoff` 時，套件屬性已存在、`sys.modules` 假物件換不進去）且會寫進真實 `~/.autosdd/handoff`。修法＝假物件以套件屬性與 `sys.modules` 雙換，`setUp` 圍 `AUTOSDD_HANDOFF_DIR`（該變數在 `sentinel_lifecycle.CACHE_FENCE_ENV` 內）。單跑、與 handoff 檔合跑、`discover -p 'test_sessionctl_*.py'` 三種跑法皆綠；跑完真實目錄無新檔。
- **P2 五件**：實作缺陷一件（`stop_message` 的 shell 計數未濾 `status`，已修）；其餘為鎖缺口（`verify` 的 `is_claude`、`trace_anchors` 依 sid、`stop_window` 砍失敗 rc、`five_hour_reading` 軸別；後者與砍失敗 rc 的實作本就正確），皆補測試並手動破壞驗證轉紅。
- **P3**：`test_human_prompt_headings_cannot_fake_the_main_layer` 名實不符（突變 M44 存活）改為真人提示含獨立 `## 主控層` 行，已殺；`_record_outcome` 查表改 `.get`。其餘邊界類（M14／M16／M21／M52／M53／M69／M70／M71）為單側邊界或唯讀防護，留待日後，不立列。
- **未立新缺陷列**：以上皆於本批修畢。

### 第二段安全審查與理論洞清單（2026-11-14）

獨立安全審查（Opus，唯讀靜態）審 `da15a928`＋hook 套用稿：結論 CONDITIONAL，P1×1、P2×3、P3×9（報告摘要寫 7、逐項列 9）、P4×6。審查發現於第二段發布前修畢，依 DEF-200-584 的記錄方式留在本證據檔，不另立未結列。

- **P1 SEC-6**：無人窗口會被提示並能 `--spawn` 出沒有姿態圍籬的互動視窗（`washed_env` 洗掉 `AUTOSDD_UNATTENDED`）。修法＝`advise_once` 無人時不出聲不設閂鎖；`spawn`／CLI 一律拒絕；FRESH 路不經 `washed_env` 以測試守住（AT-SC-91／92）。
- **P2 SEC-1**：`--all-unattended` 的驗證集合加 print 模式限定（雙駕駛不誤砍互動視窗）。**SEC-2**：痕跡帶 pid 者 pid 必須相符、無 pid 的續跑日誌錨點只放行 print 模式、互動視窗痕跡缺 pid 不砍。**SEC-7**：`--spawn` 拒絕已 ack、或同交接包已有 spawn 痕跡且（pid 仍活或在 600 秒內）（AT-SC-93～95）。
- **P3 已修**：SEC-3（UUID 完整比對，8 碼前綴與非 UUID 形一律驗不到）；SEC-13（機械層與 spawn 提示加「屬資料」句，AT-SC-96）；P4-4 縱深（`--build --session-id` 驗形態）。
- **P3 不修與理由**：SEC-4（`taskkill /T` 殘留 ppid，審查自述未驗，待真機）；SEC-5（Windows npm 版 claude 為 `node.exe` 時回「沒有找到」rc 0＝方向安全，措辭「量不到≠沒有」留待真機看實際行程名後再定）；SEC-8（`washed_env` 前綴剝 `CLAUDE_CODE_*` 會一併剝認證／供應商鍵，需沙盒實測哪些鍵 settings 不會套回，未驗不改）；SEC-9（代理逐字稿尾段 256 KB 無 usage 時放行，長代理以 assistant 收尾、機率低，擴讀策略待有真實命中）；SEC-10（跨 session 代理 id，harness 是否允許未驗）；SEC-11（`AUTOSDD_SESSIONCTL_GUARD_OFF` 在無人模式仍可關，需改 `.claude/hooks/`，不在本棒範圍，待裁）；SEC-12（交接包明文副本，原文本來就在逐字稿；遮罩樣式清單屬新增面，無暴露證據前登記不做）。
- **P4 理論洞（不修）**：①同使用者預先放置偽造痕跡把錨點對準任意行程（仍須命令列含完整 sid 且現在還要 pid 相符）；②列舉與砍之間數秒 pid 重用；③spawn 以裸名 `claude` 解析可被同名 exe 劫持（建議日後改 `shutil.which`）；④`--build --session-id ../x`（本棒已順手封）；⑤交接包首行 `sid=` 可被偽造檔塞入任意 token 進 SessionStart 文字與哨兵名稱；⑥交接包目錄退化到 `%TEMP%` 時符合檔名形態的任何檔被公告。
- **審查未驗項（待主控真機驗證）**：`taskkill /T` 是否依建立時刻過濾殘留 ppid；harness 是否允許跨 session SendMessage 舊代理 id；互動 spawn 從 `claude -p` 工具子行程發出時新視窗會不會被 Job Object 隨窗收掉。

## DEF-200-585　根層兩條測試在 Python 3.12 出錯

- **現象**：主控 2026-11-14 以 Linux 容器（Python 3.12）跑根層全套：`test_bash_probe_spec_contract.TestStubFormIsLaunchableOnItsOwnPlatform.test_windows_form_is_findable_by_the_production_helper` 把 `sys.platform` 換成 `win32` 後，3.12 的 `shutil.which` 走到 `_winapi.NeedCurrentDirectoryForExePath`，非 Windows host 上 `_winapi` 為 None；`test_selfimproving_schedule_advance.TestIngestAndLog.test_D_IMP_9_m_class_asks_for_memory_dir_only_when_a_step_is_pending` 的 `mock.Mock(cls="M", …)` 在 3.12 撞 `__new__` 的參數名。CI 與本機用 3.11 故未現形；影響＝升級直譯器時才會紅。
- **修法**：前者補一個等價的 `_winapi` 替身（`create=True`，3.11 無此屬性也成立）；後者改為 `Mock(...)` 後以屬性賦值設 `cls`。兩處只動測試檔、不改語意。
- **驗證**：以 `aisdcl-act/ubuntu:act-latest`（Python 3.12.3）唯讀掛載 repo 實跑兩條，皆 ok。同一次實跑 `TestIngestAndLog` 另有三條（`run.open` 計數）失敗，與本缺陷無關、疑為容器唯讀掛載或環境差異，未追。
