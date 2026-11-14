# TCS-SessionCtl-20261113：session 掌控與切換（需求＋驗收合一）

> 落檔：`docs/03_testing/contracts/TCS-SessionCtl-20261113.md`。設計全文＝`docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` §2.13（下稱 ADR）。缺陷帳本列＝DEF-200-580～584。
> **狀態（2026-11-14）**：第一段（FR-SC-01～04、06～09、24；AT-SC-01～33、89～90）與第二段（交接包、名冊與停止、SendMessage 閘、Stop 出聲、模型建議、hook；FR-SC-05、10～23；AT-SC-34～88）皆已實作並通過。🔴 §3 的真機驗證 V1～V8 仍**待主控真機驗證**，未驗，不得寫成已驗。
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
