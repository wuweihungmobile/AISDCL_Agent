# TCS-SessionCtl-20261113：session 掌控與切換（需求＋驗收合一）

> 落檔：`docs/03_testing/contracts/TCS-SessionCtl-20261113.md`。設計全文＝`docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` §2.13（下稱 ADR）。缺陷帳本列＝DEF-200-580～584。
> **狀態（2026-11-14）**：第一段（FR-SC-01～04、06～09、24；AT-SC-01～33、89～90）與第二段（交接包、名冊與停止、SendMessage 閘、Stop 出聲、模型建議、hook；FR-SC-05、10～23；AT-SC-34～88）皆已實作並通過。🔴 §3 的真機驗證 V1～V8 仍**待主控真機驗證**，未驗，不得寫成已驗。
> **R3 增量（2026-11-17；背景代理監督、封存閘、冷窗轉送、半路停工；設計＝ADR-XPLAT-004 §2.18；缺陷帳本列 DEF-200-597～605）**：§1b 與 §2.9～§2.12 為本增量的 FR／AT；全部已實作、單檔實跑綠、**未提交**；§3b 的 V-W／V-F 真機驗證**待掌舵者目視**，未驗不得寫成已驗。
> 測試一律 `tools/tests/test_sessionctl_*.py`（規劃四支，見 §3；現有 `test_sessionctl_switch.py`）＋既有檔增量；所有時間注入 `now`（aware datetime），所有路徑注入 `tmp`／`HOME` 圍籬（`sentinel_lifecycle.temp_fence`），**不讀本機真實 `~/.claude`、不起真排程、不起真 claude**。

## 0. 模組落點表（照 Root_Layout §2）

| 元件 | 路徑 | §2 格 |
|---|---|---|
| 函式庫套件 | `tools/lib/sessionctl/{__init__,switch,handoff,handoff_build,roster,procstop,modelmix}.py` | 模組套件 |
| 入口薄殼 | `tools/sessionctl.py` | 指令入口 |
| hook | `.claude/hooks/sessionctl_guard.py` | 守衛面（主控親套） |
| 測試 | `tools/tests/test_sessionctl_{switch,handoff,roster,hooks}.py` | 測試 |
| 夾具（E1／E2 數值，不含內容） | `tools/tests/fixtures/sessionctl/`（現查既有 fixtures 目錄慣例；無則併入測試檔常數） | 測試資料 |
| 規格／帳本 | 本檔；ADR-XPLAT-004 §2.13；`docs/06_quality/AutoSDD_Defect_Log.md`；`docs/06_quality/SessionCtl_Review_RTM_20261113.md` | 03／04／06 |

R3 增量落點（照 Root_Layout §2；`tools/lib/sessionctl/` 套件內新檔，入口仍為 `tools/sessionctl.py`；量測側 `tools/lib/wastecensus/` 套件）：

| 元件 | 路徑 | §2 格 |
|---|---|---|
| 監督 | `tools/lib/sessionctl/watch.py`（監督程序）、`supervise.py`（憑證、Stop 監督閘、派工附註、status 一行、crons 記錄） | 模組套件 |
| 封存／轉送 | `tools/lib/sessionctl/seal.py`（封存、已交棒判準、封存閘）、`forward.py`（UserPromptSubmit 轉送） | 模組套件 |
| 半路停工 | `tools/lib/sessionctl/midwork.py`（判準）；`.claude/hooks/check_pending_handoff.py`（薄接點） | 模組套件／守衛面 |
| 量測 | `tools/lib/wastecensus/supervision.py`、`supervision_load.py`（M-W／M-F／M-S）；`tools/probe/waste_census.py --supervision-metrics`、`tools/probe/handoff_census.py --midwork` | 模組套件／探針 |
| 測試 | `tools/tests/test_sessionctl_{watch,supervise,seal,forward}.py`、`test_waste_census_supervision.py`；增量於 `test_sessionctl_{converge,handoff,hooks,roster}.py`、`test_check_pending_handoff.py`、`test_waste_census_metrics.py`、`test_check_hooks_liveness.py` | 測試 |

現況（第二段落地後）：上表各檔皆已建（`handoff_build.py` 與 `procstop.py` 是實作時為守 LOC 與隔離安全敏感邏輯而拆出的檔）。登記在 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §3。

**涵蓋判定（2026-11-14 現查）**：
- CI `paths`：`.github/workflows/windows-compat-ci.yml` 與 `macos-compat-ci.yml`（push、pull_request 兩段各一行）原先**未**涵蓋 `tools/lib/sessionctl/**`，已補，與 `tools/lib/selfimproving/**` 同形。
- SelfImproving `non_evolvable_globs`：原先**未**涵蓋；`switch.py` 承接自 `session_resume_planner.py`（守衛面）的續跑選路與哨兵過期判準，屬守衛面，已補 `tools/lib/sessionctl/**` 於 `docs/06_quality/SelfImproving_Protocol/params.json` 與 PRD 〈實體 glob〉（`required_globs` 兩處集合相等）；`python tools/selfimproving.py check` 的 `params.globs` 對表通過。

## 1. 需求（FR）

| FR | 內容 | 對應 | 狀態 |
|---|---|---|---|
| FR-SC-01 | 無人選路以 R1～R4 判 FRESH，理由逐條列命中者；皆不成立 RESUME | D2、E1 | 已實作並通過 |
| FR-SC-02 | R1 取數優先序 feed → 逐字稿 usage → 位元組估計（標 estimated）；三者皆缺 R1 不成立 | D2 | 已實作並通過 |
| FR-SC-03 | 三門檻＋`STALE_SESSION_HOURS`＋`RESUME_AGENT_TOKENS` 住 `ENV_SPEC`，`--print-env-example` 可見；R1～R3 與 `RESUME_AGENT_TOKENS` 只准下修 | D2、D6 | 已實作並通過 |
| FR-SC-04 | FRESH prompt 指向交接包，且含「不得 SendMessage 續舊代理」「第一個動作重驗」兩條字面 | D2、D5 | 已實作並通過 |
| FR-SC-05 | 互動視窗 R1～R3 任一成立 ⇒ 一個 session 只出聲一次並產生交接包機械層；`off` 不出聲、`notify`／`auto` 出聲 | D2、D5 | 已實作並通過（2026-11-14） |
| FR-SC-06 | SUPERSEDED：閒置 ≥ STALE 且他 session 於其後有真實活動 ⇒ 不 RESUME 不 FRESH、自我解除、狀態 `superseded`、落痕跡與 handback；優先於撞線分支（LIMIT_SPEND 除外） | D3、E2 | 已實作並通過 |
| FR-SC-07 | 無他 session 活動（整週無人）⇒ 續航行為與修前逐位元組相同 | D3 | 已實作並通過 |
| FR-SC-08 | `_resume_tick` 在探測前套用同一判準 | D3 | 已實作並通過 |
| FR-SC-09 | `reap_verdict` 對 `waiting`＋superseded ⇒ 收；`waiting` 未 superseded ⇒ 不收；判準只有 `switch.superseded_by` 一個家 | D3 | 已實作並通過 |
| FR-SC-10 | 交接包機械層欄位齊全（缺值寫「量不到：…」），時間帶 offset | D4 | 已實作並通過（2026-11-14） |
| FR-SC-11 | 真人提示判準排除 tool_result／meta／auto-continuation／子代理／注入；取最後 K 則 | D4 | 已實作並通過（2026-11-14） |
| FR-SC-12 | `--finalize` 驗主控層前四節非空且無 `TODO:`，缺項 rc≠0 並列出 | D4 | 已實作並通過（2026-11-14） |
| FR-SC-13 | 公告：未 ack 未過期者於 SessionStart 出聲；`--ack` 寫 sidecar 後不再出聲；過期不出聲但 status 可見 | D4 | 已實作並通過（2026-11-14） |
| FR-SC-14 | 猝死（無主控層）時接班提示含「主控層缺席」字樣 | D4 | 已實作並通過（2026-11-14） |
| FR-SC-15 | `--spawn` 前置三條（finalize、工作樹保全、無執行中代理）缺一拒絕；通過後洗環境、起可見視窗、解除舊哨兵、落痕跡 | D5 | 已實作並通過（2026-11-14） |
| FR-SC-16 | 非 Windows `--spawn` 一律 notify 行為（印手動指令、rc≠0、不外呼） | D5 | 已實作並通過（2026-11-14） |
| FR-SC-17 | SendMessage 閘：互動出聲 rc 0；`AUTOSDD_UNATTENDED` 阻斷 rc 2；解析不到放行 | D6、E1 | 已實作並通過（2026-11-14） |
| FR-SC-18 | 名冊三態（執行中／安靜／殘局）＋上下文與累計 token | D7 | 已實作並通過（2026-11-14） |
| FR-SC-19 | `stop` 先驗 pid 身分（命令列含 sid ∧ 建立時刻吻合），不符不砍 | D7 | 已實作並通過（2026-11-14） |
| FR-SC-20 | Stop 事件有執行中代理 ⇒ `systemMessage` 出聲、rc 0、永不阻斷 | D7 | 已實作並通過（2026-11-14） |
| FR-SC-21 | 無人窗口每窗收窗記錄結局（起訖、路線、pct 前後、handback），banner 游標制只出聲一次；SessionStart 簡報接 banner | D7 | 已實作並通過（2026-11-14） |
| FR-SC-22 | `resume_cost.jsonl` 寫入 `pct_before`／`pct_after` | D7、E1 | 已實作並通過（2026-11-14） |
| FR-SC-23 | `--pace` 印一行模型建議（四種情境） | D8、E3 | 已實作並通過（2026-11-14） |
| FR-SC-24 | 洩漏圍籬不把活著的互動 session 合法武裝的哨兵判成洩漏：差集內 job 的 sid 有真實逐字稿且圍籬起點後有對話記錄 ⇒ 只出聲、不判死、痕跡 `live_session_jobs`；假 job 照舊判死 | ADR §2.13.11 | 已實作並通過 |

### 1b. R3 增量需求（監督、封存、轉送、半路停工；設計＝ADR-XPLAT-004 §2.18）

| FR | 內容 | 對應 | 狀態 |
|---|---|---|---|
| FR-W1 | `sessionctl watch [--sid] [--stall-min] [--wall-min] [--ctx-max]`：阻塞輪詢，第一個事件成立即印處置表對應列與末行 `WATCH_VERDICT=<事件>` 後以表定 rc 結束；每輪覆寫心跳檔 | D1 | 已實作並通過（未提交） |
| FR-W2 | keepwarm 為常數、不開 env；無人窗口取 `min(常數, harness 背景等待上限−餘裕)` | D1 | 已實作並通過（未提交） |
| FR-W3 | stall 不判「最後一筆為 assistant end_turn」的代理 | D1 | 已實作並通過（未提交） |
| FR-W4 | quota 事件重用 `park.prepare_hits`（讀快取、不外呼） | D1 | 已實作並通過（未提交） |
| FR-W5 | `supervise.credential`：payload 主證＋心跳副證；無欄位退 pid＋心跳；例外視為有效 | D1 | 已實作並通過（未提交） |
| FR-W6 | 監督閘 Stop 推回（有在飛子代理 ∧ 憑證非有效；至多一次；痕跡 `supervise_stop_block`） | D1 | 已實作並通過（未提交） |
| FR-W7 | Stop 出聲改「看管中」字樣（憑證有效時） | D1 | 已實作並通過（未提交） |
| FR-W8 | PreToolUse（Agent／Task）放行時無新鮮心跳 ⇒ 附一行派工後掛監督提醒 | D1 | 已實作並通過（未提交） |
| FR-W9 | `sessionctl status` 多一行監督狀態（只能用心跳副證） | D1 | 已實作並通過（未提交） |
| FR-A1 | `advise_once(agent_id=)` 有值即回空、不寫任何檔（E-ARCH-1） | D6 | 已實作並通過（未提交） |
| FR-S1 | 封存閘（Stop；無在飛代理 ∧ 上下文 ≥ R1 ∧ 未交棒 ∧ 封存無效 ⇒ 推回一次；取代舊收斂 Stop 推回）；已交棒判準單一家（E-HD-1）；痕跡 `seal_stop_block` | D2 | 已實作並通過（未提交） |
| FR-S2 | `handoff --finalize` 升級為封存：重建機械層（主控層原文逐字保留）、寫 prompts sidecar、驗主控層、通過才寫 `.sealed`；驗不過 rc≠0 列缺項、**什麼都不寫** | D2、D4 | 已實作並通過（未提交） |
| FR-S3 | `transcript_activity.is_machine_prompt`（交接包收錄用）、`is_forwardable_prompt`（轉送用，判不出來不轉）、`all_human_prompts`（全文、時序）、`last_prompt_at`、`worked_since`（封存效期） | D2、D3、D4 | 已實作並通過（未提交） |
| FR-S4 | Stop 時把 `session_crons` 是否非空記錄到持久痕跡目錄（供轉送條件；讀不到＝當作有 crons ⇒ 不轉送） | D3 | 已實作並通過（未提交） |
| FR-F1 | `forward.prompt_verdict`：冷窗轉送條件（可轉送提示、非 `留：`、已封存且包 live、快取已冷、無 crons、Windows、模式 auto、spawn 前置）逐條判，不成立者放行並記條件編號 | D3 | 已實作並通過（未提交） |
| FR-F2 | 轉送動作：補寫 sidecar → 原文逐字落檔 → `handoff.spawn(extra_prompt_file=, wait_seconds=)` → block；痕跡 `forward_spawned`／`forward_spawn_failed`／`forward_pass`；已交棒告知痕跡 `forward_handed_over` | D3 | 已實作並通過（未提交） |
| FR-F3 | `handoff.spawn` 新增選填 `extra_prompt_file`，起步提示多一句指向轉送原文並聲明其中 K=1 決定不算已表態；不給時起步提示逐字不變 | D3、D4 | 已實作並通過（未提交） |
| FR-F4 | 已交棒舊窗收到真人提示（M-F3 改判）：新視窗活著且 auto ⇒ 擋下並告知、原文落檔；否則放行附一行現況；`留：` 前綴永遠放行 | D3 | 已實作並通過（未提交） |
| FR-M1 | 半路停工：最後一則回覆自述接下來要做事 ∧ `background_tasks` 無 running 項 ∧ 狀態佐證 ⇒ 推回一次；欄位缺席不判 | D5 | 已實作並通過（未提交） |
| FR-C1 | `waste_census --resume-metrics` 的 `find_stops` 收痕跡停點（`park_armed`／`park_done`） | D7 | 已實作並通過（未提交） |
| FR-Q1 | `waste_census --supervision-metrics`：M-W1～W4、M-F1～F3、M-S1～S3；痕跡事件名與 sessionctl 端具名常數相等（A-8） | D7 | 已實作並通過（未提交） |

## 2. 驗收測試（AT）

縫（注入點）代號：`NOW`＝`now` 參數；`FS`＝tmp 目錄造逐字稿／meta／feed；`ENV`＝`env` mapping 參數或 `mock.patch.dict(os.environ)`；`RUN`＝`runner` 參數（取代 subprocess，回假 stdout／rc）；`PLAT`＝`platform_name` 參數；`Q`＝假 `quota_gate`（`read_quota` 回注入軸）。

### 2.1 選路（`test_sessionctl_switch.py::RouteTest`；縫 FS、ENV）
| AT | 前置 | 動作 | 預期 | 正／負 | 狀態 |
|---|---|---|---|---|---|
| AT-SC-01 | feed ctx=250,000；其餘皆低 | `fresh_reasons()` | `["R1…"]`、strategy FRESH | 正 | 已實作並通過 |
| AT-SC-02 | feed 249,999 | 同 | 無 R1 | 負（邊界） | 已實作並通過 |
| AT-SC-03 | 逐字稿含 2 個 compact_boundary | 同 | 只命中 R2 | 正 | 已實作並通過 |
| AT-SC-04 | resume_cost 同 sid 最近一筆 cache_creation=100,000（較舊一筆 0） | 同 | 只命中 R3（取最近一筆） | 正 | 已實作並通過 |
| AT-SC-05 | 逐字稿 size > 上限 | `choose_resume_route` | FRESH，理由含既有字串 | 正（R4 回歸） | 已實作並通過 |
| AT-SC-06 | `weekly` 非空 | 同 | FRESH | 正（R4 回歸） | 已實作並通過 |
| AT-SC-07 | 全部低 | 同 | RESUME、argv 含 `-r <sid>` | 負 | 已實作並通過 |
| AT-SC-08 | feed 缺席、逐字稿最後 usage 合計 300,000 | `fresh_reasons()` | R1 命中、理由標 `transcript` 來源 | 正 | 已實作並通過 |
| AT-SC-09 | feed 缺、逐字稿無 usage、size 20,518,438 | 同 | R1 命中且理由含 `estimated` | 正 | 已實作並通過 |
| AT-SC-10 | feed 缺、usage 缺、size 不可得 | 同 | R1 不成立、理由含「R1 量不到」、其他規則照判 | 負 | 已實作並通過 |
| AT-SC-11 | **E1 重放**：size 20,518,438、上限 33,554,432、feed 缺、逐字稿最後 usage≈600,000（夾具數值）、compactions≥2、R3 138,811 | `choose_resume_route` | FRESH，理由同時含 R1/R2/R3 | 回歸鎖 | 已實作並通過 |
| AT-SC-12 | FRESH 路 | 同 | prompt 含交接包路徑與兩條硬規則字面；argv 不含 `-r` | 正 | 已實作並通過 |
| AT-SC-13 | 任務書缺席 | 同 | REFUSE、argv None（既有行為不變） | 負 | 已實作並通過 |

### 2.2 門檻與方向鎖（`test_sessionctl_switch.py::ThresholdTest`；縫 ENV）
| AT | 動作 | 預期 | 狀態 |
|---|---|---|---|
| AT-SC-14 | 讀出廠 `ENV_SPEC` | R1≤250,000、R2≤2、R3≤100,000、RESUME_AGENT_TOKENS≤150,000（方向鎖：只准下修；改大即紅） | 已實作並通過 |
| AT-SC-15 | env 覆寫 R1=200,000 | 生效 | 已實作並通過 |
| AT-SC-16 | env 覆寫 R1=400,000（大於出廠） | 退出廠值＋stderr 一行（只收緊不放寬） | 已實作並通過 |
| AT-SC-17 | env 覆寫 `abc`／`-1` | 退出廠值＋出聲 | 已實作並通過 |
| AT-SC-18 | `--print-env-example` | 五個新鍵與 `AUTOSDD_SESSION_SWITCH_MODE` 皆列出（既有 env example 新鮮度鎖同步） | 已實作並通過 |

### 2.3 SUPERSEDED（`test_sessionctl_switch.py::SupersededTest`＋`test_context_budget_guard.py::SentinelDecisionTest` 增量；縫 FS、NOW）
| AT | 前置 | 動作 | 預期 | 正／負 | 狀態 |
|---|---|---|---|---|---|
| AT-SC-19 | 本 sid 最後對話 25h 前；他 sid 其後 30 回合／900s | `superseded_by()` | 回 `{sid, turns, span_seconds, last_at}` | 正 | 已實作並通過 |
| AT-SC-20 | 同上但本 sid 閒置 23h | 同 | None | 負 | 已實作並通過 |
| AT-SC-21 | 閒置 25h、他 sid 只有 1 回合（`claude -p ok`） | 同 | None | 負 | 已實作並通過 |
| AT-SC-22 | 閒置 25h、他 sid 的活動全在本 sid 最後活動之前 | 同 | None | 負 | 已實作並通過 |
| AT-SC-23 | 他 sid 活動只在 `<sid>/subagents/` 下 | 同 | None（子代理不是另一 session） | 負 | 已實作並通過 |
| AT-SC-24 | 目錄讀不動（OSError） | 同 | None | 負（fail→續航） | 已實作並通過 |
| AT-SC-25 | 未處理撞線事件（非 SPEND）＋superseded | `sentinel_decide` | `disarm`、`superseded_by` 欄、`clear_halt` | 正（優先序） | 已實作並通過 |
| AT-SC-26 | `LIMIT_SPEND` 事件＋superseded | 同 | `escalate`（錢的事仍叫人） | 負 | 已實作並通過 |
| AT-SC-27 | **整週無人**：撞線事件、reset 未到、無他 session | 同 | `arm_reset`，與修前逐位元組相同 | 對照 | 已實作並通過 |
| AT-SC-28 | **E2 重放**：狀態 `waiting`、`allow_resume` true、閒置 4 天、逐字稿 29,652,867B、ctx 556,777、他 sid 其後有活動、now＝2026-11-15T02:02+08:00 | `_sentinel_tick`（`schedule_backend` 與 `probe_quota` 打樁） | 未呼叫 probe／spawn；排程解除；狀態 `superseded`；痕跡 `sentinel_superseded`；handback 檔存在且含 `claude -r` | 回歸鎖 | 已實作並通過 |
| AT-SC-29 | 同 E2，但走 `_resume_tick`（`-Once` 路） | `_resume_tick` | 同上（探測前攔下） | 回歸鎖 | 已實作並通過 |
| AT-SC-30 | 既有 `superseding_session(halt_marker)` 全部既有測試 | 跑既有 | 全綠（抽參數後語意不變） | 回歸 | 已實作並通過 |
| AT-SC-31 | `reap_verdict(state="waiting", superseded=True, idle≥門檻)` | 呼叫 | (True, 理由含 superseded) | 正 | 已實作並通過 |
| AT-SC-32 | `reap_verdict(state="waiting", superseded=False)` | 呼叫 | (False, …) 既有字串 | 負 | 已實作並通過 |
| AT-SC-33 | `superseded` 在 `TERMINAL_STATES` | 斷言 | 是（GC 收得到） | 正 | 已實作並通過 |

### 2.3b 洩漏圍籬（`test_context_budget_guard.py::LeakFenceTest`；縫 FS、NOW）
| AT | 前置 | 動作 | 預期 | 正／負 | 狀態 |
|---|---|---|---|---|---|
| AT-SC-89 | 差集內的哨兵 job，其 sid 的真實逐字稿在圍籬起點之後有對話記錄 | `leak_fence` | 只出聲、不判死（rc 不變紅），痕跡含 `live_session_jobs` | 正 | 已實作並通過（`test_a_live_session_arming_mid_run_is_said_but_not_judged_dead`） |
| AT-SC-90 | 差集內的假 job（無真實逐字稿，或活動在圍籬起點之前） | 同 | 照舊判洩漏（`fence_rc` 非 0） | 負 | 已實作並通過（`test_a_seeded_fake_job_or_a_stale_transcript_is_still_judged_a_leak`） |

附：AT-SC-28／29 的實測對照＝`test_sessionctl_switch.py::E2ReplayTest`（E2 真值 29,652,867 B／ctx 556,777／`waiting`／`allow_resume`／閒置 4 天）；整週無人對照＝`test_a_week_with_nobody_else_still_goes_the_old_way`；E1 重放＝AT-SC-11（20,518,438 B、33,554,432、138,811）。AT-SC-09 的位元組估計比值 40 B/token 為出廠值（裁決見 ADR §2.13.2），只在 feed 與逐字稿 usage 皆缺時使用並標 `estimated`。AT-SC-33 的「無撞線事件的過期 session 狀態＝`disarmed`」裁決見 ADR §2.13.3。

### 2.4 交接包（`test_sessionctl_handoff.py`；縫 FS、RUN、NOW、Q）
| AT | 前置 | 動作 | 預期 | 狀態 |
|---|---|---|---|---|
| AT-SC-34 | 完整夾具 | `build_mechanical()` | 11 欄標題全在；時間字串 `fromisoformat(...).tzinfo is not None` | 已實作並通過（`test_sessionctl_handoff.py::MechanicalLayerTest`） |
| AT-SC-35 | git RUN 回 rc≠0 | 同 | git 各欄寫「量不到：」、其餘欄照填、不拋例外 | 已實作並通過（`test_sessionctl_handoff.py::MechanicalLayerTest`） |
| AT-SC-36 | `git status --short` 100 行 | 同 | 只列 40 行＋「共 100 行」 | 已實作並通過（`test_sessionctl_handoff.py::MechanicalLayerTest`） |
| AT-SC-37 | 逐字稿：human×5、tool_result×3、isMeta×2、auto-continuation×1、`<system-reminder>` 注入×1、子代理檔的 user×2 | `human_prompts(k=3)` | 恰為最後 3 則 human 原文；負向樣本一則都不在 | 已實作並通過（`test_sessionctl_handoff.py::HumanPromptsTest`） |
| AT-SC-38 | human 文字 5,000 字 | 同 | 截 2,000 字並標截斷 | 已實作並通過（`test_sessionctl_handoff.py::HumanPromptsTest`） |
| AT-SC-39 | 排程 RUN 回空 NextRunTime | 同 | 該列標「NextRunTime 量不到」，不寫成已排程（取證規則） | 已實作並通過（`test_sessionctl_handoff.py::MechanicalLayerTest`） |
| AT-SC-40 | 主控層四節齊、無 TODO | `finalize()` | rc 0 | 已實作並通過（`test_sessionctl_handoff.py::FinalizeTest`） |
| AT-SC-41 | 缺 `## 禁止事項` | 同 | rc≠0、訊息列出缺項名 | 已實作並通過（`test_sessionctl_handoff.py::FinalizeTest`） |
| AT-SC-42 | 含 `TODO:` | 同 | rc≠0 | 已實作並通過（`test_sessionctl_handoff.py::FinalizeTest`） |
| AT-SC-43 | 標題帶後綴「## 下一步確切指令（R3）」 | 同 | 認得（`heading_hit`） | 已實作並通過（`test_sessionctl_handoff.py::FinalizeTest`） |
| AT-SC-44 | 無主控層（猝死） | `announce()` | 出聲含「主控層缺席，先以機械層＋逐字稿尾段重建」 | 已實作並通過（`test_sessionctl_handoff.py::AnnounceTest`） |
| AT-SC-45 | 兩份未 ack、一份已 ack、一份過期 | `announce(emit)` | 恰出聲兩份；每份 ≤3 行＋路徑 | 已實作並通過（`test_sessionctl_handoff.py::AnnounceTest`） |
| AT-SC-46 | `emit` 回 False | 同 | 不寫任何 sidecar（交接包本來就不在出聲時 ack） | 已實作並通過（`test_sessionctl_handoff.py::AnnounceTest`） |
| AT-SC-47 | `ack(path)` 後 | `announce` | 該份不再出聲 | 已實作並通過（`test_sessionctl_handoff.py::AnnounceTest`） |
| AT-SC-48 | `status` | 列表 | 過期份仍列出並標 expired | 已實作並通過（`test_sessionctl_handoff.py::AnnounceTest`） |
| AT-SC-49 | `AUTOSDD_HANDOFF_DIR` 指向唯讀 | `handoff_dir_status()` | 退系統暫存且回 False（同 handback） | 已實作並通過（`test_sessionctl_handoff.py::AnnounceTest`） |

### 2.5 spawn（`test_sessionctl_handoff.py::SpawnTest`；縫 RUN、PLAT、ENV、FS）
| AT | 前置 | 預期 | 狀態 |
|---|---|---|---|
| AT-SC-50 | 未 finalize | 拒絕 rc≠0、RUN 未被呼叫 | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest`） |
| AT-SC-51 | 工作樹髒且無 `*-wip-preserved` | 拒絕 | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest`） |
| AT-SC-52 | 工作樹髒但 HEAD 有 `r1-wip-preserved` | 通過該條 | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest`） |
| AT-SC-53 | 名冊有執行中代理 | 拒絕並列出代理描述 | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest`） |
| AT-SC-54 | 三條皆過、PLAT=win32 | RUN 收到的 env 無 `CLAUDECODE`／`CLAUDE_CODE_SESSION_ID`／任何 `CLAUDE_CODE_*`／`AUTOSDD_UNATTENDED`；cwd＝repo 根；argv 含交接包路徑；creationflags 含 CREATE_NEW_CONSOLE；舊哨兵 disarm 被呼叫；痕跡 `session_switch_spawned` 含 pid | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest`） |
| AT-SC-55 | `washed_env({"claudecode":"1","Claude_Code_Session_Id":"x","PATH":"p"})` | 大小寫不敏感移除、PATH 保留（鐵律三：Windows env 大小寫） | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest`） |
| AT-SC-56 | PLAT=darwin | rc≠0、印手動指令、RUN 未被呼叫 | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest`） |
| AT-SC-57 | MODE=notify | 同 56 | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest`） |
| AT-SC-58 | MODE=off | PostToolUse 判定不出聲不產檔；`--spawn` 拒絕 | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest／AdviseOnceTest`） |
| AT-SC-59 | MODE=auto，R1 成立，同 session 第二次 PostToolUse | 只出聲一次（閂鎖） | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest／AdviseOnceTest`） |
| AT-SC-60 | MODE=auto，全部不成立 | 不出聲、不產檔 | 已實作並通過（`test_sessionctl_handoff.py::SpawnTest／AdviseOnceTest`） |

### 2.6 SendMessage 閘、名冊、stop、Stop 出聲（`test_sessionctl_roster.py`、`test_sessionctl_hooks.py`；縫 FS、ENV、RUN、PLAT）
| AT | 前置 | 動作 | 預期 | 正／負 | 狀態 |
|---|---|---|---|---|---|
| AT-SC-61 | 目標代理上下文 150,000、互動 | hook PreToolUse | rc 0、輸出含「改派新代理」 | 正 | 已實作並通過（`test_sessionctl_hooks.py::ResumeGateFunctionTest／HookSubprocessTest`） |
| AT-SC-62 | 同上、`AUTOSDD_UNATTENDED=1` | 同 | rc 2、stderr 含「改派新代理＋短任務書」 | 正 | 已實作並通過（`test_sessionctl_hooks.py::ResumeGateFunctionTest／HookSubprocessTest`） |
| AT-SC-63 | 上下文 149,999、無人 | 同 | rc 0、無輸出 | 負 | 已實作並通過（`test_sessionctl_hooks.py::ResumeGateFunctionTest／HookSubprocessTest`） |
| AT-SC-64 | 目標名解析不到／meta 壞 JSON／payload 無 `tool_input` | 同 | rc 0 放行 | 負（fail-open） | 已實作並通過（`test_sessionctl_hooks.py::ResumeGateFunctionTest／HookSubprocessTest`） |
| AT-SC-65 | **E1 重放**：無人、目標代理最後 usage 合計 450,000 | 同 | rc 2 | 回歸鎖 | 已實作並通過（`test_sessionctl_hooks.py::ResumeGateFunctionTest／HookSubprocessTest`） |
| AT-SC-66 | meta `finished:false`、最後記錄 2 分鐘前 | `roster.snapshot` | 執行中 | 已實作並通過（`test_sessionctl_roster.py::RosterStateTest`） |
| AT-SC-67 | 同、40 分鐘前 | 同 | 安靜 | 已實作並通過（`test_sessionctl_roster.py::RosterStateTest`） |
| AT-SC-66b | meta 無 `finished`、擁有者主逐字稿 harness 記錄（`queue-operation`／`attachment`）帶該代理 `<status>killed</status>`；人貼的同字樣（`user`）不算（DEF-200-606） | 同 | 不列入名冊 | 已實作並通過（`test_sessionctl_roster.py::RosterStateTest::test_def_200_606_taskstopped_agent_leaves_the_roster`） |
| AT-SC-68 | 同、擁有者逐字稿閒置 > 巡邏間隔、RUN 無含 sid 的行程 | 同 | 殘局，且說明「非燒額度中」 | 已實作並通過（`test_sessionctl_roster.py::RosterStateTest`） |
| AT-SC-69 | `finished:true` | 同 | 不列執行中 | 已實作並通過（`test_sessionctl_roster.py::RosterStateTest`） |
| AT-SC-70 | 候選行程命令列含 sid、建立時刻吻合痕跡 | `stop --window` | taskkill `/T /F /PID` 被呼叫（絕對路徑）、哨兵解除、痕跡 `window_stopped` | 已實作並通過（`test_sessionctl_roster.py::StopWindowTest`） |
| AT-SC-71 | 命令列含 sid、建立時刻不符（pid 重用） | 同 | 不砍、rc≠0、列候選 | 已實作並通過（`test_sessionctl_roster.py::StopWindowTest`；第二段 QA 補 `test_kill_failure_is_rc_one_and_said_not_stopped`、`test_a_non_claude_process_with_the_sid_in_its_cmdline_is_never_killed`、`test_trace_anchors_ignore_other_sessions_spawn_records`） |
| AT-SC-72 | 建立時刻符、命令列不含 sid | 同 | 不砍 | 已實作並通過（`test_sessionctl_roster.py::StopWindowTest`） |
| AT-SC-73 | 列舉 RUN rc≠0 | 同 | 不砍、明說「量不到」 | 已實作並通過（`test_sessionctl_roster.py::StopWindowTest`） |
| AT-SC-74 | Stop payload、名冊 2 支執行中 | hook Stop | rc 0、stdout JSON `systemMessage` 含「2 支」與描述 | 已實作並通過（`test_sessionctl_hooks.py::StopMessageFunctionTest／HookSubprocessTest`；第二段 QA 補 `test_finished_background_tasks_are_never_reported_as_running`：status 非 running 的子代理與 shell 不計入） |
| AT-SC-75 | Stop、無執行中／名冊讀不動 | 同 | rc 0、無輸出 | 已實作並通過（`test_sessionctl_hooks.py::StopMessageFunctionTest／HookSubprocessTest`） |
| AT-SC-76 | Stop、`stop_hook_active` 為真 | 同 | 仍 rc 0（永不 block） | 已實作並通過（`test_sessionctl_hooks.py::StopMessageFunctionTest／HookSubprocessTest`） |

### 2.6b 第二段安全審查後的收緊（`test_sessionctl_handoff.py`、`test_sessionctl_roster.py`；縫 RUN、ENV、FS、NOW）
| AT | 前置 | 預期 | 狀態 |
|---|---|---|---|
| AT-SC-91 | `AUTOSDD_UNATTENDED` 有設（任何非空值）；互動 `spawn`／CLI `--spawn` | rc 1、說明「無人窗口不開互動視窗」、RUN 未被呼叫、哨兵未解除（SEC-6） | 已實作並通過（`SpawnTest::test_sec6_unattended_window_never_spawns_an_interactive_window`／`test_sec6_cli_spawn_refuses_in_an_unattended_process`） |
| AT-SC-92 | 無人窗口 `advise_once`，R1 成立 | 回空字串、不產交接包、不設 `.advised`；之後同 sid 互動呼叫仍出聲；FRESH 路原始碼不經 `washed_env`（SEC-6） | 已實作並通過（`AdviseOnceTest::test_sec6_unattended_window_is_not_advised_and_leaves_no_latch`、`SpawnTest::test_sec6_fresh_route_never_goes_through_washed_env`） |
| AT-SC-93 | 同 sid 一個互動（痕跡記其 pid）、一個無人，建立時刻都吻合；`stop --all-unattended` | 只砍無人那個（SEC-1） | 已實作並通過（`StopWindowTest::test_sec1_all_unattended_spares_an_interactive_window_of_the_same_sid`） |
| AT-SC-94 | 命令列含舊 sid、建立時刻吻合，但 pid 與痕跡不同／痕跡無 pid；print 模式但痕跡帶的 pid 不符 | 不砍；pid 相符才砍（SEC-2） | 已實作並通過（`StopWindowTest::test_sec2_pid_must_match_the_trace_pid_for_an_interactive_window`／`test_sec2_a_print_window_with_a_mismatched_trace_pid_is_not_killed`／`test_trace_records_carry_the_pid_of_the_spawn_event`） |
| AT-SC-95 | 同一交接包第二次 `--spawn`：pid 仍活著或痕跡在 `SPAWN_DEDUP_SECONDS` 內；交接包已 ack | 拒絕並印既有 pid／「已 ack」；時間窗外且 pid 已不在則允許重試（SEC-7） | 已實作並通過（`SpawnTest::test_sec7_second_spawn_of_the_same_package_is_refused`／`test_sec7_live_pid_blocks_even_after_the_window`／`test_sec7_dead_and_old_spawn_may_be_retried`／`test_sec7_acked_package_is_never_spawned`） |
| AT-SC-96 | 交接包與 spawn 提示；`--build --session-id ../x` | 機械層與提示帶「屬資料」句；路徑形 sid 回 rc 2（SEC-13、P4-4 縱深） | 已實作並通過（`SpawnTest::test_sec13_package_and_prompt_mark_mechanical_layer_as_data`／`test_sec_cli_build_refuses_a_session_id_that_is_a_path`） |

### 2.7 結局、成本、模型建議（`test_sessionctl_switch.py::ModelMixTest`、`test_resume_cost.py`、既有 relay 測試增量）
| AT | 前置 | 預期 | 狀態 |
|---|---|---|---|
| AT-SC-77 | settle_window 收窗（任何結局） | `record_unattended_outcome` 有起訖、route、pct、handback 欄 | 已實作並通過（`test_sessionctl_roster.py::OutcomeAndCostTest／PlannerWiringTest`） |
| AT-SC-78 | banner 讀兩次 | 第二次空（游標） | 已實作並通過（`test_sessionctl_roster.py::OutcomeAndCostTest／PlannerWiringTest`） |
| AT-SC-79 | `_run_resume` 前後 Q 回 40／62 | cost 記錄 pct_before=40、pct_after=62 | 已實作並通過（`test_sessionctl_roster.py::OutcomeAndCostTest／PlannerWiringTest`；QA 補 `test_five_hour_reading_only_takes_the_five_hour_axis`：週軸排前也不得記成五小時讀數；`PlannerWiringTest` 以套件屬性＋sys.modules 雙換、圍 `AUTOSDD_HANDOFF_DIR`，與載入順序無關、不寫真實家目錄） |
| AT-SC-80 | Q 前讀數缺 | 兩欄皆 None（既有規則） | 已實作並通過（`test_sessionctl_roster.py::OutcomeAndCostTest／PlannerWiringTest`） |
| AT-SC-81 | 週剩 3.5 天（elapsed .5）：all 40%、Fable 70% | 「Fable 超前：多外派」 | 已實作並通過（`test_sessionctl_modelmix.py::AdviceTest`） |
| AT-SC-82 | all 70%、Fable 30% | 「全模型超前：子代理降級」 | 已實作並通過（`test_sessionctl_modelmix.py::AdviceTest`） |
| AT-SC-83 | all 20%、Fable 20%、elapsed .5 | 「兩軸皆寬：深度審查可用 Opus」 | 已實作並通過（`test_sessionctl_modelmix.py::AdviceTest`） |
| AT-SC-84 | `resets_at` 缺 | 該軸不判，印「量不到」，不拋 | 已實作並通過（`test_sessionctl_modelmix.py::AdviceTest`） |

### 2.8 跨檔鎖（既有檔）
| AT | 內容 | 落點 | 狀態 |
|---|---|---|---|
| AT-SC-85 | 新 hook 已註冊且在根 CLAUDE.md 機械守衛總表點名 | `test_doc_loc_baseline_freshness_r60.py::TestR74…`／`TestR79…` | 已實作並通過（`test_sessionctl_hooks.py::GuardRegistrationTest`） |
| AT-SC-86 | 新 hook exec form、啟動器契約、載具存在 | `test_check_hooks_liveness.py` | 已實作並通過（`test_check_hooks_liveness.py::TestHookRegistrationScopeIsShrinkOnly`） |
| AT-SC-87 | 外部執行檔 argv 皆在平台守衛內 | `test_platform_neutral_paths.py::TestForeignExecutableArgvIsGuarded` | 已實作並通過（`test_platform_neutral_paths.py::TestForeignExecutableArgvIsGuarded`） |
| AT-SC-88 | 文字 I/O 皆帶 encoding；git 列舉帶 quotepath | 同檔 `TestTextIoDeclaresEncoding`／`TestGitPathEnumerationIsQuotepathSafe` | 已實作並通過（`test_platform_neutral_paths.py::TestTextIoDeclaresEncoding／TestGitPathEnumerationIsQuotepathSafe`） |

### 2.9 監督（R3；`test_sessionctl_watch.py`、`test_sessionctl_supervise.py`；縫＝注入時鐘／名冊／額度／心跳讀取，不開環境變數鉤）
| AT | 一句話 | 縫 | 狀態（測試檔::名稱） |
|---|---|---|---|
| AT-W1～6 | 六種事件（all_done、overrun、stall、budget、quota、keepwarm）各自成立時 rc 與末行正確、先到先出 | 假名冊／假時鐘 | 已實作並通過（`test_sessionctl_watch.py::EventTests`：`test_w1_all_done_after_grace_when_never_seen`、`test_w1b_all_done_immediately_once_seen`、`test_w2_overrun`、`test_w3_stall`、`test_w4_budget`、`test_w5_quota`、`test_w6_keepwarm`、`test_w6_keepwarm_boundary_in_decide`、`test_event_order_is_pinned`、`test_disposal_row_and_rc_table`） |
| AT-W7 | 最後一筆為 end_turn 的代理 20 分無記錄不判 stall | 假名冊 | 已實作並通過（`test_sessionctl_watch.py::EventTests::test_w7_end_turn_agent_is_not_stalled`） |
| AT-W8 | stall 門檻低於下限 ⇒ 退回出廠值並出聲 | ENV、CLI 參數 | 已實作並通過（`test_sessionctl_watch.py::ConfigTests::test_w8_stall_floor_is_11`） |
| AT-W9 | 單支上下文門檻只准下修（env 與 `--ctx-max` 皆然） | ENV | 已實作並通過（`test_sessionctl_watch.py::ConfigTests::test_w9_ctx_only_downward`） |
| AT-W10 | 心跳每輪覆寫、帶 offset | FS | 已實作並通過（`test_sessionctl_watch.py::HeartbeatTests::test_w10_heartbeat_rewritten_each_round_with_offset`） |
| AT-W11 | 憑證四態：payload 有 watch shell＋心跳新鮮／缺席＝有效；心跳過期＝卡死；無 payload 項（含別終端手跑、已結束的 watch）＝無效；無欄位退 pid＋心跳；例外＝有效 | 假 payload、假心跳 | 已實作並通過（`test_sessionctl_supervise.py::CredentialTests`：`test_main_proof_with_fresh_or_missing_heartbeat_is_valid`、`test_main_proof_with_stale_heartbeat_is_stuck`、`test_no_main_proof_is_none_even_with_fresh_heartbeat`、`test_finished_or_other_shell_is_not_proof`、`test_old_harness_without_field_needs_fresh_heartbeat_and_live_pid`、`test_any_exception_fails_open_to_valid`） |
| AT-W12 | 監督閘：有在飛子代理無憑證 ⇒ block；有憑證 ⇒ 不推回且字樣為看管中；`stop_hook_active`／無人／模式非 auto ⇒ 放行；只有子代理觸發 | 假 payload | 已實作並通過（`test_sessionctl_supervise.py::StopGateTests`：`test_no_credential_blocks_with_exact_command_and_traces`、`test_stuck_reason_says_taskstop_first`、`test_valid_credential_does_not_block_and_message_says_watched`、`test_loop_brake_unattended_and_modes`、`test_only_subagents_trigger`、`test_event_name_matches_the_measurement_side`） |
| AT-W13 | 冷叫醒閘與監督閘同時成立 ⇒ 只出冷叫醒 reason；未封存者落到監督閘（E-CW-1） | 假 payload＋假交接包 | 已實作並通過（`test_sessionctl_supervise.py::ColdWakeVsSuperviseTests::test_finalized_package_wins_over_supervise`、`::test_unfinalized_falls_to_supervise_gate`） |
| AT-W14 | PreToolUse（Agent／Task）：無新鮮心跳附一行、有心跳不附、子代理自己的呼叫不附 | 假 payload | 已實作並通過（`test_sessionctl_supervise.py::DispatchNoteTests`：`test_note_when_no_fresh_heartbeat`、`test_silent_with_fresh_heartbeat_subagent_call_unattended_or_other_tool`、`test_converge_verdict_carries_the_note_when_the_gate_passes`） |
| AT-W15 | `status` 一行監督（有效／卡死／無）、`session_crons` 三態記錄 | FS | 已實作並通過（`test_sessionctl_supervise.py::StatusAndCronsTests`） |
| AT-A1 | 子代理 payload 呼叫 `advise_once` ⇒ 回空、無 `.advised`、無包 | FS | 已實作並通過（`test_sessionctl_handoff.py::` 內 `test_earch1_subagent_call_neither_advises_nor_eats_the_latch`） |

### 2.10 封存閘與封存（R3；`test_sessionctl_converge.py::StopVerdictTest`、`test_sessionctl_seal.py`；縫 FS、NOW、ENV）
| AT | 一句話 | 縫 | 狀態（測試檔::名稱） |
|---|---|---|---|
| AT-S1 | 封存閘四格（N<R1／有在飛代理／已封存且之後無工作／已交棒 各使其放行）＋一格推回 | FS | 已實作並通過（`test_sessionctl_converge.py::StopVerdictTest::test_at_s1_each_of_the_four_conditions_releases_and_the_fifth_blocks`） |
| AT-S2 | 封存閘與 park 同時成立 ⇒ 一則合併 reason（先封存再 park） | FS、Q | 已實作並通過（`test_sessionctl_converge.py::StopVerdictTest::test_at_s2_seal_gate_and_park_merge_into_one_reason`） |
| AT-S3 | finalize 通過：機械層重建、主控層逐字保留、寫 sidecar 與封存戳 | FS、NOW | 已實作並通過（`test_sessionctl_seal.py::SealTest::test_seal_rebuilds_mechanical_keeps_main_verbatim_and_writes_sidecar_and_stamp`、`::test_cli_finalize_goes_through_seal`、`::test_finalize_stays_a_pure_check_with_no_side_effects`） |
| AT-S4 | prompts sidecar 收全部真人提示、排除機器注入；超過字數上限時保留第一則與最後十則全文、中段列索引 | FS | 已實作並通過（`test_sessionctl_seal.py::SealTest::test_sidecar_over_limit_keeps_first_and_last_ten_full_and_indexes_the_middle`、`::test_refresh_prompts_rewrites_only_the_sidecar`；`::TranscriptCriteriaTest::test_is_machine_prompt_table`、`::test_all_human_prompts_full_text_in_order_with_lines`） |
| AT-S5 | 主控層有 `TODO:` ⇒ rc≠0 且**無** `.sealed`、無 sidecar | FS | 已實作並通過（`test_sessionctl_seal.py::SealTest::test_seal_with_todo_returns_rc1_and_writes_nothing`） |
| AT-S6 | ff1000ed 形態（上下文 ≥ R1、包停在機械層、無 `.advised`）⇒ Stop 推回 | FS（以實測數值造假逐字稿） | 已實作並通過（`test_sessionctl_converge.py::StopVerdictTest::test_at_s6_the_ff1000ed_shape_pushes_back_without_any_advised_latch`） |
| AT-S7 | 封存效期：封存後只讀檔不使其失效，非唯讀工作使其失效（裁決 A-1）；`worked_since` 讀不到 ⇒ 不推回 | FS | 已實作並通過（`test_sessionctl_converge.py::StopVerdictTest::test_a1_reading_after_the_seal_does_not_invalidate_but_work_does`；`test_sessionctl_seal.py::TranscriptCriteriaTest::test_worked_since_ignores_read_only_tools_and_old_and_sidechain`、`::test_worked_since_unreadable_or_bad_since_is_false_the_release_direction`） |
| AT-S8 | 已交棒判準（E-HD-1）：寫完且〔已 ack ∨ 有 spawn 痕跡〕才算；已交棒 session 不被封存閘推回、但掛背景任務仍被冷叫醒閘推回；只寫完未封存不啟動冷叫醒閘（E-CW-1） | FS | 已實作並通過（`test_sessionctl_converge.py::StopVerdictTest::test_e_hd_1_handed_over_session_is_not_pushed_back_but_a_wake_task_is`、`::test_handed_over_needs_a_written_package_and_a_hand_off_signal`、`::test_e_cw_1_a_written_but_unsealed_package_does_not_arm_the_wake_gate`、`::test_def_200_588_finalized_package_with_a_running_task_is_pushed_back`、`::test_def_200_588_the_wake_gate_stays_silent_when_nothing_can_wake_it`） |

### 2.11 轉送與已交棒告知（R3；`test_sessionctl_forward.py`；縫＝注入 spawn／alive／cache／crons／preflight／refresh／platform，不開環境變數鉤）
| AT | 一句話 | 縫 | 狀態（測試檔::名稱） |
|---|---|---|---|
| AT-F0 | 條件全成立 ⇒ block、原文已落檔、已 spawn、痕跡 `forward_spawned` | 假 spawn 等 | 已實作並通過（`test_sessionctl_forward.py::PathOneForwardTest::test_all_nine_conditions_hold_then_block_with_original_saved_and_spawned`） |
| AT-F1 | 各條件逐一使其不成立 ⇒ 放行且 `forward_pass` 帶第一個不成立條件編號 | 同上 | 已實作並通過（`::PathOneForwardTest::test_each_failing_condition_passes_and_records_its_number`） |
| AT-F2 | `<task-notification>` 開頭永不擋（F1-8 回歸鎖）；`<pasted_content` 可轉、未知角括號包裝不轉 | 同上 | 已實作並通過（`::PathOneForwardTest::test_task_notification_is_never_forwarded`、`::test_pasted_content_is_forwardable_unknown_angle_wrapper_is_not`） |
| AT-F3 | 原文落檔逐字一致、SHA-256 相符 | FS | 已實作並通過（`::PathOneForwardTest::test_original_prompt_is_saved_verbatim_with_matching_sha256`） |
| AT-F4 | spawn 失敗 ⇒ 放行、原文檔保留、痕跡 failed；行程活著但逐字稿未見仍算已轉送；落檔失敗不擋 | 假 spawn | 已實作並通過（`::PathOneForwardTest::test_spawn_failure_passes_and_keeps_the_saved_original`、`::test_alive_process_without_transcript_still_counts_as_forwarded`、`::test_write_failure_of_the_original_never_blocks`） |
| AT-F5 | 非 Windows／模式 notify ⇒ 放行＋additionalContext（附手動 spawn 指令） | 注入 platform | 已實作並通過（`::PathOneForwardTest::test_notify_and_non_windows_pass_with_a_spawn_hint`） |
| AT-F6 | 快取熱 ⇒ 放行（留原地較便宜） | 假 cache | 已實作並通過（`::PathOneForwardTest::test_hot_cache_stays_in_place`） |
| AT-F7 | `session_crons` 記錄非空或讀不到 ⇒ 放行 | 假 crons | 已實作並通過（`::PathOneForwardTest::test_cron_record_nonempty_or_unreadable_never_forwards`） |
| AT-F8 | 任何例外 ⇒ rc 0 放行（函式層與子行程跑 hook、注入壞 payload） | 子行程 | 已實作並通過（`::PathOneForwardTest::test_any_exception_fails_open`、`::HookLayerTest::test_malformed_input_exits_zero_and_silent`、`::test_task_notification_through_the_real_hook_is_silent`） |
| AT-F9 | 已交棒舊窗：新視窗活著 ⇒ block 並告知（不 spawn、不論快取冷熱）；新視窗不在 ⇒ 放行附現況；`留：`／機器注入／notify ⇒ 放行 | 假 alive | 已實作並通過（`::PathTwoHandedOverTest`：`test_new_window_alive_blocks_with_notice_and_never_spawns`、`test_hot_cache_blocks_too`、`test_new_window_gone_passes_with_a_status_line`、`test_escape_prefix_task_notification_and_notify_mode_pass`；hook 層 `::HookLayerTest::test_handed_over_window_gets_block_json_without_spawning`） |
| AT-F10 | 痕跡事件名與量測端 `EV_FORWARD_*` 常數相等；`UserPromptSubmit` 以 exec form、timeout 大於 spawn 等待秒數註冊 | — | 已實作並通過（`::PathOneForwardTest::test_trace_event_names_match_the_census_constants`、`::RegistrationTest::test_user_prompt_submit_registered_exec_form_with_timeout_50`） |

### 2.12 半路停工與量測（R3；`test_check_pending_handoff.py`、`test_waste_census_metrics.py`、`test_waste_census_supervision.py`）
| AT | 一句話 | 狀態（測試檔::名稱） |
|---|---|---|
| AT-M1 | 事故原句與進行式詞表命中；摘要、標題、引號、否定、他人負責、合法換手標記整則不命中 | 已實作並通過（`test_check_pending_handoff.py::TestMidworkWording`） |
| AT-M2 | Stop 接線：無背景工作＋髒工作樹 ⇒ 推回；有 running 背景任務、欄位缺席、其他守衛條件（第二次 Stop、無人、開關）、乾淨工作樹且只讀工具 ⇒ 放行；兩種判準同時命中合併一則；讀不到逐字稿 fail-open | 已實作並通過（`test_check_pending_handoff.py::TestMidworkStopWiring`） |
| AT-C1 | f2260ce7 重現：低於 prepare 的樣本＋`park_armed` 痕跡 ⇒ 計為停點；無痕跡的閒置不計 | 已實作並通過（`test_waste_census_metrics.py::test_at_c1_park_trace_stop_below_prepare_threshold_is_counted`） |
| AT-Q1 | M-W1～W4、M-F1～F3、M-S1～S3 各自的判準與缺資料時寫明「無資料」而非乾淨的零；CLI 全印且不寫進 repo | 已實作並通過（`test_waste_census_supervision.py`，含 `test_missing_trace_events_say_no_data_instead_of_a_clean_zero`、`test_cli_prints_every_metric_and_writes_nothing_into_the_repo`） |
| AT-HV2-9 | 接續測驗四題（沙盒 haiku 自動驗交接包 v2 是否足以接續） | **未實作**（H 縫；待真機／後續包，未驗不得寫成已驗） |

### 2.13 既有 AT 的語意改動（舊收斂 Stop 推回 → 封存閘；`test_sessionctl_converge.py` 內改名）
舊 AT-TW-70～77 與 AT-TW-79／AT-TW-80 的原文住 `docs/03_testing/contracts/TCS-TokenWaste-20261114.md` §2（該檔不在本增量改動範圍，其對應列以本表為準）：

| 舊 AT | 新語意與測試 |
|---|---|
| AT-TW-70 | 改為 AT-S6／AT-S1：不再要求「已出聲」與硬門檻，上下文 ≥ R1 即推回；痕跡 `converge_stop_block` 改 `seal_stop_block`；測試 `test_at_tw_70_…` 改名 `test_at_s6_the_ff1000ed_shape_pushes_back_without_any_advised_latch`（hook 層 `test_sessionctl_hooks.py::HookConvergeTest::test_at_tw_70_hook_stop_pushes_back_once_with_a_block_decision` 保留） |
| AT-TW-71、72／72b、77 | 保留（`test_at_tw_71_a_second_stop_is_never_pushed_back`、`test_at_tw_72_…`、`test_at_tw_72b_…`、`test_at_tw_77_pushback_lifts_after_the_context_comes_down`；77 去掉「已出聲」前提） |
| AT-TW-73 | 刪除：「寫完≠封存」，改由 AT-S1（已封存且之後無工作放行）與 AT-S8（已交棒）涵蓋 |
| AT-TW-74、76 | 合併為 `test_at_tw_74_unattended_notify_off_and_broken_payloads_are_noops` |
| AT-TW-75 | 刪除：「已出聲在先」的邊界不再存在，改為 AT-S1 的「N<R1」邊界 |
| AT-TW-79、80 | 保留，前提改為先封存（`.sealed`）或已交棒（E-CW-1）；AT-TW-80 的上下文改 R1 減 50,000 以避開封存閘 |

## 3. 真機驗證（主控親跑；V 步驟）

| V | 步驟 | 通過憑證 |
|---|---|---|
| V1 | `python tools/sessionctl.py status` 於本機 | 列出本 session 子代理（含本場 Sonnet 代理）與 `AutoSDD_*` 排程 NextRunTime 值；rc 0 |
| V2 | E2 重放：以 f1522ddb 任務書數值造一份臨時任務書（不取內容）→ `--sentinel-tick` 於隔離 `AUTOSDD_TRACE_DIR`／`AUTOSDD_PLAN_DIR` | 痕跡 `sentinel_superseded`、無 `probed`、排程不存在（`Get-ScheduledTask` 現查無該名） |
| V3 | 互動：開一個測試視窗→`handoff`（機械層）→ 補主控層 → `--finalize` → `--spawn` | 新視窗可見；新視窗 `$env:CLAUDECODE` 為空；新視窗 SessionStart 簡報出聲交接包；`--ack` 後再開一窗不出聲；舊 sid 哨兵 `Get-ScheduledTask` 查無 |
| V4 | 無人：`claude -p` 下派一支代理再 SendMessage 續它（上下文門檻臨時以 env 下修到 1,000） | rc 2 被擋、stderr 字樣；互動視窗同操作只出聲 |
| V5 | Stop：派一支 background 代理後立即結束回合 | 畫面看到 `systemMessage`（掌舵者可見） |
| V6 | `stop --window <假 sid>`：起一支命令列含該 sid 的 `pwsh -NoExit` 佔位行程 | 被砍；對另一支命令列不含 sid 的行程不動 |
| V7 | `--pace` | 多一行模型建議，與當下兩週軸數字一致 |
| V8 | `claude -p --debug hooks` 正面現查新 hook | `Hook Stop.*success`、`PreToolUse` 於 SendMessage 觸發記錄 |

### 3b. R3 增量的真機驗證（**待真機，未驗不得寫成已驗**；已驗的一項見末列）

| V | 步驟 | 通過憑證 |
|---|---|---|
| V-W2 | 互動視窗：派背景子代理後不掛 watch 就結束回合；再掛 watch 結束回合 | 前者見監督閘推回理由、後者見「看管中」字樣（互動畫面是否顯示 block 理由與 `systemMessage` 本身即待驗項） |
| V-W3 | 掛 watch 後主控閒置至保溫點 | watch 結束叫醒主控、首回合以讀快取為主（M-W2 不新增冷重寫）；若 `idleCompaction` 提前壓縮主控，保溫點需下調 |
| V-W4 | 背景子代理交 interim 卷時看 `meta.finished` 與 `background_tasks` | 記錄實值；all_done 不提早成立 |
| V-F1 | 封存後等快取冷，在舊視窗打一句真人提示 | 舊視窗畫面顯示轉送說明、新視窗自動開出並讀到轉送原文檔；失敗路徑原文檔仍在；`留：` 開頭的提示留在原視窗 |
| V-F2 | 已交棒（已 spawn／已 ack）的舊視窗打一句提示 | 畫面顯示「本視窗已交棒」說明與原文檔路徑 |
| V-HOOK | `claude -p --model haiku --debug hooks`（正面現查） | `Hooks: UserPromptSubmit [...sessionctl_guard.py] finished with status 0`（**已驗**：2026-11-17 主控親跑，註冊後真 harness 觸發記錄） |
