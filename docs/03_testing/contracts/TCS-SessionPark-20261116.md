# TCS-SessionPark-20261116：額度自願停工的續航 park（需求＋驗收合一）

> 設計全文＝`docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` §2.17（下稱 ADR）；缺陷帳本列＝DEF-200-594～596（`docs/06_quality/AutoSDD_Defect_Log.md`）。命名照本目錄既有 `TCS-<模組>-<日期>.md`；不併入 SessionCtl／TokenWaste 兩檔，因二者是已凍結的狀態對照帳，本案新 AT 前綴 `AT-PK-`。
> **狀態（2026-11-16）**：**H 路已實作**（`tools/lib/sessionctl/park.py`、`park_cli.py` 與連動檔）。**本輪不做 W 路**（同 session 背景等待者；ADR §2.17 否決案 X38）：W 路 AT 編號保留不重排，狀態欄標「本輪不做」。§3 真機驗證：V-PK2 的 ①②⑤ 已於 2026-11-16 由第一次真實停工驗到（sid f2260ce7 → ff1000ed），其餘（V-PK2 ③④⑥、V-PK3、V-PK4）仍**待真機**，未驗不得寫成已驗。
> 測試一律 `tools/tests/test_sessionctl_park.py`（新）＋既有檔增量；所有時間注入 `now`（aware datetime）、所有路徑圍籬到 tmp，**不讀本機真實 `~/.claude`、不起真排程、不起真 claude、不打真額度端點**。禁用 skip。
> 狀態欄的測試座標一律為 `test 檔::類::方法`；`PK`＝`tools/tests/test_sessionctl_park.py`。

## 0. 模組落點表（照 Root_Layout §2；全部在已登記的 sessionctl 套件與既有檔內，無新落點格）

| 元件 | 路徑 | §2 格 |
|---|---|---|
| 函式庫（新） | `tools/lib/sessionctl/park.py`（純判準＋標記）、`tools/lib/sessionctl/park_cli.py`（CLI／job 本體／排程編排） | 模組套件（既有） |
| 函式庫（改） | `tools/lib/sessionctl/converge.py`（Stop 尾端接線）、`tools/lib/sessionctl/handoff.py`（+公開預演函式 `spawn_preflight`）、`tools/lib/engine_resume_job.py`（+`arm_oneshot`、`interactive`）、`tools/lib/quota_messages.py`（準備帶訊息）、`tools/lib/wastecensus/resume.py`（新）＋`report.py`（旗標） | 既有家 |
| 入口薄殼 | `tools/sessionctl.py`（+`park` 分派）；`tools/probe/waste_census.py` 不改（旗標在套件內） | 指令入口 |
| 守衛面（主控親套） | `tools/session_resume_planner.py`（`sentinel_decide` 讓路）、`.claude/hooks/check_pending_handoff.py`（詞表）、`.claude/hooks/sessionctl_guard.py`（僅 docstring） | 守衛面 |
| 測試 | `tools/tests/test_sessionctl_park.py`（新）；增量 `test_check_pending_handoff.py`、`test_sessionctl_hooks.py`、`test_sessionctl_converge.py`、`test_waste_census_metrics.py` | 測試 |
| 規格／帳本 | 本檔；ADR §2.17；`docs/06_quality/AutoSDD_Defect_Log.md` | 03／04／06 |

涵蓋判定：`tools/lib/sessionctl/**` 已在 CI `paths` 與 SelfImproving `non_evolvable_globs`；新檔落在同一 glob 下，不需新增 paths。

## 1. 需求（FR）

| FR | 內容 | 對應 | 狀態 |
|---|---|---|---|
| FR-PK-01 | `park_route(wait_s, *, unattended, mode, carrier_ok)` 只回 `H`／`REFUSE`；REFUSE＝無人、模式非 auto、無載具、reset 不明 | ADR D1 | 已實作 |
| FR-PK-02 | Stop 判準只讀**短窗軸原始讀數** `Axis.pct`，不吃攤提／配速床墊高後的 band；週軸不算 | ADR D2、X32 | 已實作 |
| FR-PK-03 | 停工無有效憑證 ⇒ 推回一次；憑證兩種（H 排程、DONE 戳記）；`stop_hook_active`、無人、模式非 auto、`AUTOSDD_PARK_GUARD_OFF`、無載具、量不到 ⇒ 不推回 | ADR D2／D4／D9 | 已實作 |
| FR-PK-04 | 憑證是值：排程憑證取不到（含 rc=0 但無值）⇒ `park` rc≠0、不寫標記 | ADR D4 | 已實作 |
| FR-PK-05 | `park` 前置：交接包已 finalize、spawn 前置預演通過；否則 rc 2 並列缺項（登記前就失敗） | ADR D5 | 已實作 |
| FR-PK-06 | （原 W 路順序與回滾）H 路順序：登記 → 寫標記，標記寫失敗即回滾排程 | ADR D5 | 已實作（H 部分）；W 部分本輪不做 |
| FR-PK-07 | （原等待者）等待者自帶截止、逐段睡、心跳 | ADR X38 | 本輪不做（W 路，ADR §2.17 否決案） |
| FR-PK-08 | job 本體（`park --fire`）：取消／ack／過期／有人在動（對話記錄判活）⇒ 跳過；其餘 `handoff.spawn`；結局寫標記、必要時寫 handback、自拆 | ADR D6 | 已實作 |
| FR-PK-09 | 哨兵在 park 窗內讓路為 `patrol`；`LIMIT_SPEND` 仍 `escalate`；無標記逐位元組同舊行為 | ADR D7 | 已實作 |
| FR-PK-10 | 準備帶訊息不含寫死的「85~95%」、含 `sessionctl.py park`、不含「在這個視窗說一聲」類句型 | ADR D8 | 已實作 |
| FR-PK-11 | 交棒詞表補「你」字系列（最終詞表見 AT-PK-74）；否定／引號／K1 抑制照舊 | ADR D8 | 已實作 |
| FR-PK-12 | `--resume-metrics` 產出 M-R1～M-R4（含 `unmeasured` 另計） | ADR §2.17.7 | 已實作 |
| FR-PK-13 | `arm_oneshot(interactive=True)` 的 Windows 腳本用 Interactive Principal 且無 S4U／fallback；`interactive=False` 逐位元組同舊腳本 | ADR X36 | 已實作 |
| FR-PK-14 | park*.py 不含排程器原語；零新環境變數門檻（只有 `AUTOSDD_PARK_GUARD_OFF` 一個逃生口） | ADR D9 | 已實作；無專屬測試，靠既有鎖（見 AT-PK-85、88） |

## 2. 驗收測試（AT）

縫（注入點）代號：`NOW`＝`now` 參數；`FS`＝tmp 圍籬；`ENV`＝`env` mapping；`Q`＝假額度讀取函式；`ARM`＝假 `arm_oneshot`／`disarm`／`list_jobs`；`RUN`＝`runner`；`SPAWN`＝假 `handoff.spawn`；`PLAT`＝`platform_name`。

**夾具 INC（事故數值，不含內容）**：sid `798a7bf1-a991-4a08-8ab8-d0736296f823`；最後 assistant＝2026-11-15T19:17:12.620Z、usage input 2／cache_read 217,962／cache_creation 1,482（ctx 219,446）；額度快照＝`five_hour`／`session` 各 98.0%、`resets_at`＝2026-11-15T20:00:00+00:00（距 43 分）、`seven_day` 78.0%＋`weekly_scoped(Fable)` 78.0%（距 8467 分）；`now`＝2026-11-15T19:17:15Z。
**夾具 AMORT（墊高控制組）**：`five_hour` 23.0%、`resets_at`＝now＋43 分；`seven_day` 78.0%＋`weekly_scoped(Fable)` 78.0%、`resets_at`＝now＋8467 分；`ratio=4.3`、`ratio_note="n=84"`、`active_model="fable"`。前置斷言：`quota_policy.decide(...).per_axis` 的五小時軸 `band=="prepare"` 且 `note` 含 `amortized`、`axis.pct==23.0`。

### 2.1 選路（`PK::RouteTest`；純函式）

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-01 | ctx=100,000、wait 45 分 | （原：`W`） | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-02 | INC：ctx=219,446、wait_s=2,820 | `("H", …)`（H 版改寫：選路不再讀 ctx） | 已實作（`PK::RouteTest::test_at_pk_02_the_incident_goes_to_h_route`） |
| AT-PK-03 | ctx=100,000、wait 70 分 | （原：`H`，W／H 邊界） | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-04 | wait_s=360、ttl_s=300 | （原：`ttl_s−300` 邊界） | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-05 | `unattended=True` | `("REFUSE", reason 含「無人窗口」)` | 已實作（`PK::RouteTest::test_at_pk_05_unattended_is_refused`） |
| AT-PK-06 | wait_s=`None` | `REFUSE`，reason 含「reset」與「不假設」 | 已實作（`PK::RouteTest::test_at_pk_06_unknown_reset_is_refused_without_assuming_five_hours`） |
| AT-PK-07 | ctx=149,999／150,000 | （原：W／H） | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-08 | ctx=`None` | （原：`H`） | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-09 | wait_s 邊界（`ttl_s−300`、`W_MAX_WAIT_SECONDS`） | （原：W／H 邊界）；H 版另釘「負 wait 不是拒絕」 | 本輪不做（W 路，ADR §2.17 否決案）；另有 `PK::RouteTest::test_at_pk_09_negative_wait_is_not_a_refusal` |
| AT-PK-10 | `mode∈{notify,off}`；`carrier_ok=False` | `REFUSE` | 已實作（`PK::RouteTest::test_at_pk_10_mode_and_carrier_refusals`） |
| AT-PK-11 | 讀常數 `W_MAX_WAIT_SECONDS`、`CONFIRM_WINDOW_SECONDS`、`YIELD_GRACE_SECONDS` | （原：W 常數方向鎖） | 本輪不做（W 路，ADR §2.17 否決案）；`YIELD_GRACE_SECONDS` parity 由 `PK::ReadingTest::test_yield_grace_matches_quiesce` 釘 |

### 2.2 原始讀數（`PK::ReadingTest`；縫＝`Q`、`NOW`、Policy）——本案 (g) 的核心

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-12 | AMORT（前置斷言先過） | `park.prepare_hits(state, policy, now)==[]`（raw 23% < 85）；同一 state 的 `decide(...).per_axis` 五小時軸 band 為 prepare | 已實作（`PK::ReadingTest::test_at_pk_12_amortised_band_is_not_a_hit`） |
| AT-PK-13 | 五小時軸 pct=84.9／85.0／85.1；與 `quota_policy.pct_band` 逐格相等 | `[]`／命中／命中 | 已實作（`PK::ReadingTest::test_at_pk_13_threshold_edges_match_pct_band`） |
| AT-PK-14 | 只有 `seven_day` 99% | `[]`（週軸不算） | 已實作（`PK::ReadingTest::test_at_pk_14_17_weekly_axes_never_count`） |
| AT-PK-15 | `session` 90% 與 `five_hour` 90%；兩軸 `resets_at` 相差取**較晚者** | 兩軸命中、`reset_of(hits)` 取 max | 已實作（`PK::ReadingTest::test_at_pk_15_reset_of_takes_the_latest`） |
| AT-PK-16 | pct=NaN／`inf`／`True`；`resets_at` naive／`None`／過去 | 該軸不命中；`reset_of` 回 `None` | 已實作（`PK::ReadingTest::test_at_pk_16_bad_readings_are_not_hits`） |
| AT-PK-17 | `weekly_scoped` 95%、短窗軸 10% | `[]` | 已實作（`PK::ReadingTest::test_at_pk_14_17_weekly_axes_never_count`） |
| AT-PK-18 | `axes==()`／快取過期 | `prepare_hits` 回 `None`；`stop_verdict` 為 `""`、落 `park_verdict_unmeasured` | 已實作（`PK::ReadingTest::test_at_pk_18_unmeasured_is_none_not_empty`；`PK::StopVerdictTest::test_at_pk_18b_unmeasured_is_traced`） |
| AT-PK-19 | parity：`SHORT_WINDOW_KINDS`、`SHORT_WINDOW_MINUTES` | 與 `quota_gate._FIVE_HOUR_KINDS`、`_FIVE_HOUR_MINUTES` 相等 | 已實作（`PK::ReadingTest::test_at_pk_19_parity_with_quota_gate`） |
| AT-PK-20 | kind 為不認得的字面但窗長導出 300 分 | 視為短窗軸；窗長 10080 的軸不是 | 已實作（`PK::ReadingTest::test_at_pk_20_window_length_is_derived_not_named`） |

### 2.3 Stop 判準（`PK::StopVerdictTest`）

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-21 | INC 回放；無標記 | reason 非空，含 `python tools/sessionctl.py park`、`park --done --why`；經 `converge.stop_verdict` 總入口亦同 | 已實作（`PK::StopVerdictTest::test_at_pk_21_incident_without_marker_is_pushed_back`；`…::test_at_pk_21b_total_entry_via_converge`） |
| AT-PK-22 | AT-PK-21 ＋有效 H 標記 | `""` | 已實作（`PK::StopVerdictTest::test_at_pk_22_valid_h_marker_passes`） |
| AT-PK-23 | W 標記＋心跳檔容忍 | （原：心跳 149／151 秒） | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-24 | DONE 標記有效／過期／why 7 字 | 有效→`""`；過期→推回；7 字→推回 | 已實作（`PK::StopVerdictTest::test_at_pk_24_done_marker_validity`） |
| AT-PK-25 | 額度 72% | `""`（負控） | 已實作（`PK::StopVerdictTest::test_at_pk_25_low_quota_is_not_pushed_back`） |
| AT-PK-26 | `stop_hook_active=True` | `""`（第二次 Stop 放行） | 已實作（`PK::StopVerdictTest::test_at_pk_26_stop_hook_active_passes`） |
| AT-PK-27 | `AUTOSDD_UNATTENDED=1` | `""`，且不讀額度、不讀標記 | 已實作（`PK::StopVerdictTest::test_at_pk_27_unattended_does_not_even_read_quota`） |
| AT-PK-28 | `AUTOSDD_PARK_GUARD_OFF=1`；mode notify／off；無載具 | 各 `""` | 已實作（`PK::StopVerdictTest::test_at_pk_28_escape_hatches`） |
| AT-PK-29 | 短窗 98% 但 `resets_at` 缺／naive／已過 | `""`（reset 不明不推回） | 已實作（`PK::StopVerdictTest::test_at_pk_29_unknown_reset_is_not_pushed_back`） |
| AT-PK-30 | 標記 status∈{fired,cancelled,failed,skipped}、sid 不同、schema 錯、壞 JSON、窗已過 | 皆不算憑證⇒推回（fail-closed） | 已實作（`PK::StopVerdictTest::test_at_pk_30_non_credentials_are_pushed_back`） |
| AT-PK-31 | 任何內部例外 | `""`（fail-open，P0） | 已實作（`PK::StopVerdictTest::test_at_pk_31_any_exception_fails_open`） |
| AT-PK-32 | 收斂閘與 park 推回同時成立 | 回收斂閘的 reason（先判者先回） | 無專屬測試：靠結構保證（`converge.stop_verdict` 的 `_converge_stop(...) or _park_stop(...)`）與 `test_sessionctl_converge.py` 既有收斂閘測試 |
| AT-PK-33 | 交接包已 `--spawn`、短窗 98% | `""`（條件⑤） | 已實作（`PK::StopVerdictTest::test_at_pk_33_spawned_package_is_not_pushed_back`；痕跡讀取 `…::test_handed_off_reads_the_spawn_trace`） |
| AT-PK-34 | 不變式 I-1：推回情境下 `park_cli.run(argv=[])` 可滿足；拒絕情境 `stop_verdict==""` 且 `park` rc 4 | rc 0／rc 4 | 已實作（`PK::ParkCliTest::test_at_pk_34_invariant_what_the_guard_demands_park_can_satisfy`；`…::test_at_pk_28b_mode_and_carrier_refusals_match_the_stop_guard`） |
| AT-PK-35 | hook 端到端：子程序餵 Stop payload 給 `sessionctl_guard.py` | 有載具平台 rc 0＋`decision:block`；`stop_hook_active`／GUARD_OFF→無輸出；無載具平台靜默 | 已實作（`tools/tests/test_sessionctl_hooks.py::HookParkTest::test_at_pk_35_stop_pushes_back_a_quota_stop_without_a_credential`） |

### 2.4 標記（`PK::MarkerTest`；縫＝`FS`）

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-36 | 寫後讀（H／DONE）；欄位缺、schema 錯、naive 時間戳、sid 含 `../`；讀取端不建目錄 | 合格者原樣讀回；其餘 `None`；寫入端拒絕不合格者 | 已實作（`PK::MarkerTest::test_roundtrip_h_and_done`；`…::test_invalid_markers_read_as_none_and_are_refused_on_write`；`…::test_reading_creates_nothing`） |

### 2.5 `park` 編排（`PK::ParkCliTest`；縫＝`Q`、`ARM`、`RUN`、`FS`、`ENV`、`NOW`）

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-37 | H 路（INC）；`ARM` 回 `(0, "NextRunTime = …")` | rc 0；呼叫序列＝`arm_oneshot` → 寫標記；標記 `route=H`、`status=armed`、`job.credential` 逐字等於 `ARM` 回值；label 形如 `AutoSDD_HandoffSpawn_798a7bf1_<YYYYMMDDHHMM>`；末行 `PARK_VERDICT=armed route=H …` | 已實作（`PK::ParkCliTest::test_at_pk_37_h_route_arms_then_writes_the_marker`） |
| AT-PK-38 | `ARM` 回 `(0, "")`／`(1, "")` | rc 1；不寫標記；落 `park_arm_failed`；stderr 含「不會說它已排程」 | 已實作（`PK::ParkCliTest::test_at_pk_38_no_credential_means_no_marker`） |
| AT-PK-39 | W 路兜底排程順序 | （原：W 路） | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-40 | W 路兜底失敗 | （原：W 路） | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-41 | H 路、標記寫入失敗 | rc 1；已登記 job 被 `disarm` 且 `list_jobs` 驗證不在；落 `park_arm_failed` | 已實作（`PK::ParkCliTest::test_at_pk_41_marker_write_failure_rolls_the_job_back`） |
| AT-PK-42 | 交接包不存在／未 finalize | rc 2，列缺項；`arm_oneshot` 未被呼叫 | 已實作（`PK::ParkCliTest::test_at_pk_42_package_preconditions`） |
| AT-PK-43 | spawn 前置預演失敗（髒工作樹、有執行中代理） | rc 2，列出與 `handoff._refusals` 同字面的原因；未登記任何排程 | 已實作（`PK::ParkCliTest::test_at_pk_43_preflight_failures_arm_nothing`；預演與 spawn 拒絕同源另釘 `PK::PreflightTest::test_preflight_matches_spawn_refusals`） |
| AT-PK-44 | `AUTOSDD_UNATTENDED=1` | rc 4；`Q`／`ARM` 未被呼叫；落 `park_refused` | 已實作（`PK::ParkCliTest::test_at_pk_44_unattended_is_refused_before_anything_is_read`） |
| AT-PK-45 | reset 量不到 | rc 4、stderr 含「量不到 reset」與「不假設 5 小時」；`ARM` 未被呼叫 | 已實作（`PK::ParkCliTest::test_at_pk_45_unknown_reset_is_refused_loudly`） |
| AT-PK-46 | 無短窗軸達 prepare（只有週軸高）；`--at` 合法性 | rc 4 並指向 `--at <ISO> --why`；`--at` 缺 why／過去／>8 天 ⇒ rc 2；合格 `--at` ⇒ H 路 | 已實作（`PK::ParkCliTest::test_at_pk_46_weekly_only_needs_explicit_at`） |
| AT-PK-46b | 短窗 84%（未達 prepare）：無 why／7 字 why／合格 why；短窗 reset 缺＋合格 why | 無 why、7 字 ⇒ rc 4 並指向 `--why`、不排程；reset 缺 ⇒ rc 4「不假設 5 小時」；合格 why ⇒ rc 0，觸發時刻＝觀測 reset＋120 秒取整，標記 `axis.pct`＝84、`why` 逐字（ADR §2.17 D3b） | 已實作（`PK::ParkCliTest::test_at_pk_46b_below_threshold_parks_only_with_a_stated_why`） |
| AT-PK-47 | `park --done --why`（8 字／7 字／無人） | 8 字→rc 0、DONE 標記；7 字→rc 2；無人→rc 4 | 已實作（`PK::ParkCliTest::test_at_pk_47_done_marker`） |
| AT-PK-48 | `park --cancel`（disarm 成功／失敗／無標記／`list_jobs` 量不到） | 成功→`cancelled`；失敗→維持 armed、rc 1；量不到→rc 1、不宣稱已移除 | 已實作（`PK::ParkCliTest::test_at_pk_48_cancel_verifies_removal`） |
| AT-PK-49 | `park --status`（`--verify` 才經排程器取證） | 印 route／status／觸發時刻／憑證；預設零副作用 | 已實作（`PK::ParkCliTest::test_at_pk_49_status_is_read_only_unless_verify`） |
| AT-PK-50 | 同 sid 第二次 `park` | 舊排程先撤並驗證再登記新的；新舊標籤不同 | 已實作（`PK::ParkCliTest::test_at_pk_50_second_park_replaces_the_first`） |

### 2.6 等待者（W 路）

| AT | 狀態 |
|---|---|
| AT-PK-51 | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-52 | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-53 | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-54 | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-55 | 本輪不做（W 路，ADR §2.17 否決案） |
| AT-PK-56 | 本輪不做（W 路，ADR §2.17 否決案） |

（原內容：`--wait-until` 等待者的逐段睡、`overslept` 判定、心跳檔；再開條件見 ADR X38。）

### 2.7 job 本體（`PK::JobTest`；縫＝`SPAWN`、`ARM`、`FS`、`NOW`、`ENV`）

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-57 | 舊逐字稿最近 900 秒內有 `assistant` 記錄 | `SPAWN` 未被呼叫；`handoff_spawn_skipped reason=live_driver`；標記 `skipped`；job 自拆 | 已實作（`PK::JobTest::test_at_pk_57_58_a_live_driver_blocks_the_spawn`） |
| AT-PK-58 | 同上但為 `human`／`auto-continuation` 記錄 | 同 AT-PK-57 | 已實作（同 `PK::JobTest::test_at_pk_57_58_a_live_driver_blocks_the_spawn`） |
| AT-PK-59 | 負控（DEF-200-560 同型）：只有 `away_summary`、`cost-state`、`tool_result` 型 user、`isMeta` 寬限提示，且檔案 mtime 剛剛 | `SPAWN` 被呼叫（不得因 mtime 新而跳過） | 已實作（`PK::JobTest::test_at_pk_59_synthetic_records_and_fresh_mtime_are_not_a_driver`） |
| AT-PK-60 | 交接包已 ack／已過期／不存在 | 跳過 `reason=acked|expired`；`SPAWN` 未被呼叫；job 自拆 | 已實作（`PK::JobTest::test_at_pk_60_acked_or_expired_package_is_skipped`） |
| AT-PK-61 | 標記 `cancelled`／缺／sid 不符 | 跳過（`cancelled|not_armed`）；job 自拆；rc 0 | 已實作（`PK::JobTest::test_at_pk_61_cancelled_or_missing_marker_is_skipped`） |
| AT-PK-62 | `SPAWN` 回 0 | 標記 `fired`、落 `park_spawned`、job 自拆；rc 0 | 已實作（`PK::JobTest::test_at_pk_62_success_marks_fired_and_removes_the_job`） |
| AT-PK-63 | `SPAWN` 回 1 | 標記 `failed`、落 `park_spawn_failed`、寫含四個標題的 handback、job 自拆；rc 1 | 已實作（`PK::JobTest::test_at_pk_63_failure_writes_a_handback_with_the_four_headings`） |
| AT-PK-64 | `AUTOSDD_UNATTENDED=1` | 拒絕 spawn、rc 4 | 已實作（`PK::JobTest::test_at_pk_64_unattended_job_refuses_to_spawn`） |
| AT-PK-65 | 兜底 job（W 路） | （原：W 兜底 job 跳過） | 本輪不做（W 路，ADR §2.17 否決案） |

### 2.8 哨兵讓路（`PK::SentinelYieldTest`；直接呼叫 `planner.sentinel_decide`）

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-66 | 未處理撞線事件＋ park 標記 H armed、在窗內 | `action=="patrol"`、reason 含讓路字面 | 已實作（`PK::SentinelYieldTest::test_at_pk_66_a_valid_marker_yields_to_the_scheduled_job`） |
| AT-PK-67 | 無標記（`park=None`）：既有五分支代表輸入表 | 與不帶 `park` 參數的輸出逐項相同（以等值比較取代「修前實作凍成黃金值」，因修前實作無法在不碰 git 寫入下現跑） | 已實作（`PK::SentinelYieldTest::test_at_pk_67_69_no_effective_marker_means_the_old_decision_exactly`） |
| AT-PK-68 | `LIMIT_SPEND` 事件＋有效標記 | `escalate` | 已實作（`PK::SentinelYieldTest::test_at_pk_68_monthly_spend_still_escalates_under_a_valid_marker`） |
| AT-PK-69 | 標記窗已過；標記 `status!=armed` | 退回既有判定 | 已實作（同 `PK::SentinelYieldTest::test_at_pk_67_69_no_effective_marker_means_the_old_decision_exactly`；讓路窗邊界另見 `PK::StopVerdictTest::test_yields_only_for_armed_h_inside_window`） |
| AT-PK-70 | `_sentinel_tick` 接線 | 原始碼中 `sentinel_decide(` 呼叫帶 `park=` | 已實作，僅原始碼接線斷言，未做 e2e tick（`PK::SentinelYieldTest::test_at_pk_70_the_tick_passes_the_marker_through`） |
| AT-PK-71 | AST 鎖：`sentinel_decide` 的 action 集合仍恰為五個 | 既有測試全綠（本案沒有新增 action 字面） | 無專屬測試：既有鎖 `tools/tests/test_context_budget_guard.py::PatrolHandbackIsItsOwnOutcomeTest` |

### 2.9 訊息與詞表

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-72 | `quota_prepare_message`（prepare 帶、含短窗軸） | 不含 `85~95%`；含 `sessionctl.py park`；不含「在這個視窗說一聲」「說一聲繼續」；仍含「準備」「現查還能派幾個」 | 已實作（`PK::MessageTest::test_at_pk_72_prepare_message_points_at_park_and_not_at_the_old_window`） |
| AT-PK-73 | M7 判準：新增句不含 `%` | 新增句不含 `%` | 已實作，併入 AT-PK-72 的方法（新增句不含 `%` 斷言）；未另寫完整 M7 判準測試 |
| AT-PK-74 | `pending_handoff_hits`：「…仍由你決定。」「待你處理」「留給你」「交給你」「需要你」「你來決定」皆命中。**最終詞表**：待你、留給你、交給你、交由你、由你決定、你來決定、需要你、需你、你裁決；「請你」「等你」不收（普查造成 3 回合假紅） | 命中；「請你」「等你」的日常敘述不命中 | 已實作（`tools/tests/test_check_pending_handoff.py::TestSecondPersonVocabulary::test_at_pk_74_second_person_handoffs_are_red`；不收詞反例 `…::test_everyday_second_person_narration_stays_green`） |
| AT-PK-75 | 負控：「你不需要做任何事」「沒有任何事卡在等你」「不用等你」；引號內「由你決定」；K1 親打句 | 皆不命中 | 已實作（`tools/tests/test_check_pending_handoff.py::TestSecondPersonVocabulary::test_at_pk_75_negated_quoted_and_k1_second_person_forms_are_green`） |
| AT-PK-76 | `python tools/probe/handoff_census.py` 重跑（唯讀，主控親跑） | 附實測數字；假紅＝0 才算過 | 已實作（主控 2026-11-16 親跑：214 回合命中 14；詞表若收「請你」「等你」會多出 3 回合假紅，最終詞表不收後該 3 回合假紅消失） |

### 2.10 量測（`tools/tests/test_waste_census_metrics.py::ResumeMetricsTest`；縫＝tmp 合成逐字稿＋`quota_burn.jsonl`＋痕跡檔、`NOW`）

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-77 | INC 合成夾具：最後 assistant 19:17:12.620Z；`quota_burn` 樣本 five_hour=98、`resets_at`=20:00:00Z；下一筆 human 00:54:03.896Z（443 字）；下一筆 assistant 00:54:22.783Z（cc 188,230） | M-R1＝294.4±0.1 分鐘；M-R2＝1；M-R3＝188,230 token（≈10.4pp） | 已實作（`tools/tests/test_waste_census_metrics.py::ResumeMetricsTest::test_at_pk_77_incident_fixture`） |
| AT-PK-78 | reset 後第一筆為 `按交接包繼續：…`／`auto-continuation`／`origin.kind=sdk` | M-R2＝0；M-R1 仍量到第一筆 assistant | 已實作（`…::ResumeMetricsTest::test_at_pk_78_machine_wakeups_are_not_a_human`） |
| AT-PK-79 | 間隔 ≥30 分但前 15 分鐘無 `quota_burn` 樣本 | 計入 `unmeasured`，輸出明列 | 已實作（`…::ResumeMetricsTest::test_at_pk_79_unmeasured_gaps_are_counted_not_dropped`） |
| AT-PK-80 | M-R4：停點前後 10 分鐘內有／無 `park_armed`、`park_done`；`park_stop_block` 件數 | 無痕跡者計入「無憑證停點」；block 件數獨立列出 | 已實作（`…::ResumeMetricsTest::test_at_pk_80_stops_without_a_credential_are_listed`） |
| AT-PK-81 | `--resume-metrics` 與既有 `--since-days`、`--out`、`--replay-hard-ctx` | `--replay-hard-ctx` 既有行為不變；不寫 repo 內任何檔 | 已實作（`…::ResumeMetricsTest::test_at_pk_81_resume_metrics_cli_coexists_with_replay_and_writes_nothing`） |

### 2.11 排程載具與跨檔鎖

| AT | 輸入 | 預期 | 狀態 |
|---|---|---|---|
| AT-PK-82 | `_arm_schtasks(…, interactive=True)` 腳本 | 含 `-LogonType Interactive`；不含 `S4U`、不含 `PRINCIPAL-FALLBACK`；含四項排程設定；`NextRunTime` 為空 ⇒ `(1, "")` | 已實作（`PK::EngineOneshotTest::test_at_pk_82_interactive_script_has_no_s4u_and_no_fallback`） |
| AT-PK-83 | `interactive=False`（預設）腳本 | 與修前逐位元組相同 | 已實作（`PK::EngineOneshotTest::test_at_pk_83_default_script_is_byte_identical_to_the_pre_change_script`） |
| AT-PK-84 | `arm_oneshot` 在 NoCarrier／planner 不可達 | `(1, "")`、stderr 說明 | 已實作（`PK::EngineOneshotTest::test_at_pk_84_arm_oneshot_without_carrier_is_refused`） |
| AT-PK-85 | `CarrierPrimitivesHaveOneHomeTest` 掃描面含 park*.py | 零命中 | 無專屬測試：既有鎖 `tools/tests/test_mac_endurance_r83.py::CarrierPrimitivesHaveOneHomeTest` 現行綠 |
| AT-PK-86 | `BackendInterfaceIsSymmetricTest`、`TestForeignExecutableArgvIsGuarded`、`TestTextIoDeclaresEncoding` 等既有鎖 | 照舊綠 | 無專屬測試：既有鎖現行綠（`tools/tests/test_mac_endurance_r83.py::BackendInterfaceIsSymmetricTest`、`tools/tests/test_platform_neutral_paths.py`、`tools/tests/test_subprocess_encoding_hygiene.py`） |
| AT-PK-87 | 文件宣稱↔註冊對帳（根 CLAUDE.md〈機械守衛總表〉含 `park`、`AUTOSDD_PARK_GUARD_OFF`；無新 hook） | 照舊綠 | 無專屬測試：靠既有 `test_doc_loc_baseline_freshness_r60.py` 的 `TestR74…`／`TestR79…`；CLAUDE.md 更新由主控收尾 |
| AT-PK-88 | 零新門檻變數：`quota_policy.py --print-env-example` 鍵集合與修前相同；`park.py` 以 `os.environ` 直讀者只有 `AUTOSDD_PARK_GUARD_OFF` | 相等 | 無專屬測試：靠程式審查與 `PK::StopVerdictTest::test_at_pk_28_escape_hatches` 對逃生口行為的釘住 |

## 2.12 突變清單（QA 逐條實打；每條至少一條 AT 應轉紅，未轉紅＝補斷言）

W 路專屬突變（M-PK-01、05、09、10、16、21）本輪不做（ADR §2.17 否決案 X38）；編號保留。

| M | 突變 | 應紅 |
|---|---|---|
| M-PK-02 | `stop_verdict` 的比較由 `≥ prepare_pct` 改成 `≥ halt_pct`（本案成因） | AT-PK-21、13 |
| M-PK-02b | 判準改吃 `decide()` 的 `per_axis[].band`（墊高後） | AT-PK-12 |
| M-PK-03 | 憑證檢查改成只看 rc／標記存在、不看憑證值（或 `status` 不看） | AT-PK-38、30 |
| M-PK-04 | job 的「有人在動」改用逐字稿檔案 mtime | AT-PK-59 |
| M-PK-06 | 拿掉 `stop_hook_active` 早退 | AT-PK-26、31 |
| M-PK-07 | 判準納入週軸／不限短窗 | AT-PK-14、17、19、20 |
| M-PK-08 | `park` 先寫標記再登記排程（順序對調）；或標記寫失敗不回滾 | AT-PK-37、41 |
| M-PK-11 | 哨兵讓路忽略 `LIMIT_SPEND` | AT-PK-68 |
| M-PK-12 | reset 量不到時假設 5 小時（或 `REFUSE` 改成放行） | AT-PK-06、16、18、29、45 |
| M-PK-13 | 無人窗口不拒絕（park／Stop／job 任一處） | AT-PK-05、27、44、64 |
| M-PK-14b | `interactive` 參數被忽略 | AT-PK-82 |
| M-PK-15 | job 不查 `live_driver` 直接 spawn | AT-PK-57、58 |
| M-PK-17 | `--done` 的 8 字下限拿掉（寫入端或讀取端任一處） | AT-PK-24、47 |
| M-PK-18 | 多軸 reset 取 min 而非 max | AT-PK-15 |
| M-PK-19 | 標記路徑對 sid 不驗形態（路徑穿越） | AT-PK-36 |
| M-PK-20 | 哨兵讓路窗不設上界（永遠讓路）／讓路不看 `status` | AT-PK-69 |

## 3. 真機驗證（主控親跑；不得由開發棒代驗；結果寫進缺陷帳本列；一律「待真機」）

W 路專屬的 V-PK1（W 路真等一次 reset）與 V-PK6（背景等待者 55 分鐘存活）本輪不做（ADR X38）；編號保留，餘者沿用原編號。

| V | 步驟 | 通過憑證 | 狀態 |
|---|---|---|---|
| V-PK2 | **H 路排程與換手**：大上下文視窗 `handoff --build`→補主控層→`--finalize`→`park`；等到點 | ① 貼出 `park` 印的 `NextRunTime` 實測值與同時間的 `Get-ScheduledTask -TaskName 'AutoSDD_HandoffSpawn_*' \| Get-ScheduledTaskInfo` 輸出；② 到點（reset＋2 分內）使用者桌面**可見**的新互動視窗開出、新逐字稿出現（貼新 sid 與 `park_spawned` 痕跡列）；③ 新視窗 `$env:CLAUDECODE` 為空、SessionStart 出聲交接包；④ Principal 回讀為 Interactive；⑤ job 自拆；⑥ macOS 欄（另機）：憑證是 `launchctl print` rc 0＋descriptor 回讀，睡眠姿態以 `pmset -g custom` 現查 | **①②⑤ 已驗（Windows，2026-11-16）**：sid `f2260ce7` 於 10:10:13 +08:00 `park`（痕跡 `park_armed`，憑證 `NextRunTime = 2026/11/16 下午 01:03:00`，job `AutoSDD_HandoffSpawn_f2260ce7_202611161303`）；13:03:00.127 `park_job_start`（late_s 0.127）、13:03:00.367 `session_switch_spawned`（新逐字稿 `ff1000ed-171a-4299-b309-80a632fb8cba.jsonl`，建立 13:03:03）、13:03:03.912 `park_spawned rc 0`；新 session SessionStart 出聲未接手交接包並已 `handoff --ack`；事後 `Get-ScheduledTask` 查 `AutoSDD_HandoffSpawn_*` 為 0 筆、`park --status --verify` 回 `status=fired`「排程器中：不在」。停工 10:10 到接手 13:03 之間無人介入。**③④ 未驗**（job 已自拆，Principal 無從回讀；新視窗啟動前的 `$env:CLAUDECODE` 無法從 session 內回看）；⑥ macOS 待另機 |
| V-PK3 | **到點前在舊視窗說話 ⇒ 排程跳過**：同 V-PK2，到點前 5 分鐘於舊視窗打一句話 | 到點後沒有新視窗；痕跡 `handoff_spawn_skipped reason=live_driver`；job 自拆 | 待真機 |
| V-PK4 | **Stop 推回訊息互動畫面可見**：互動視窗、短窗軸 ≥ prepare、無 park 憑證時結束一個回合 | 掌舵者畫面看到推回訊息（含 `park` 指令一行）；第二次 Stop 放行。**若互動畫面不顯示 block reason ⇒ 本守衛退為只出聲，須回 ADR 改寫** | 待真機 |
| V-PK5 | **基線回放**：`python tools/probe/waste_census.py --resume-metrics --since-days 14` | 上線前基線已由主控 2026-11-16 親跑（ADR §2.17.7：停點 6、unmeasured 55；M-R1 n=3 中位 274.9／P90 294.4 分；M-R2 1；M-R3 589,565 token；M-R4 無憑證停點 6）；park 上線後的對照待觀察期（14 天）後重跑 | 基線已量；上線後對照待真機 |
