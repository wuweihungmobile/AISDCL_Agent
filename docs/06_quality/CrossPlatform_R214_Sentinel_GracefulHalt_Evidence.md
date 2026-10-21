# CrossPlatform R214：哨兵「自願停機後不續跑」三根因（DEF-200-560／561／562）

> 體例同 `CrossPlatform_R213_DebtZero_FourParty_W5.md`。設計全文＝ADR-XPLAT-004 §2.10；登記＝`tools/lib/governance_docs.py`。
> 驗屍與設計＝主控（Fable 5.1）；落地與自驗＝Developer（Sonnet，起點 HEAD `5593d0bb4c6c1d0df9fdcb7863ad192604aa314f`）。本檔〈七〉由主控追加親驗，Developer 不寫。

## 〈一〉掌舵者原文（逐字）

> 為何沒有自動續跑, 這點屬於嚴重Bug, 請找到根因, 徹底改善!

（2026-10-21，sid `e9f8e2cb-c1fd-4234-8f8a-f1c546529cf1` 首則訊息；另有非構造性痕跡 `%TEMP%\autosdd_resume_log_autosdd_resume_plan_d6dfce97-92bd-4d34-b7d3-73cf5feaa23d.jsonl` 的 16 次 patrol，符合根 CLAUDE.md〈守衛面准入〉的暴露證據。）

## 〈二〉驗屍時間線（主控驗屍，逐字；sid `d6dfce97-92bd-4d34-b7d3-73cf5feaa23d`，Claude Code 2.1.303，Windows）

| 時刻（+08:00） | 事實 | 證據 |
|---|---|---|
| 03:55:27 | `context_budget_guard` 進 halt 帶（five_hour），寫 halt 標記 `{"band":"halt","binding":"five_hour","reset_at":"2026-10-20T19:59:59.530201+00:00","at":"2026-10-21T03:55:27.695912+08:00"}`，武裝哨兵 | `C:\Users\wuwei\.autosdd\traces\halt_d6dfce97-92bd-4d34-b7d3-73cf5feaa23d.json` |
| 03:55:31 | 哨兵狀態塊 `allow_resume: false`（repo 根 `.env` 有 `AUTOSDD_RESUME_OFF=1`；主控已於 08:13 刪除該行） | `%TEMP%\autosdd_resume_plan_d6dfce97-….md` RELAY 區塊 |
| 03:59:37 | harness 注入**寬限提示**：`type=user`、`isMeta:true`、`usageLimitNote:"wrap_up"`、`turnCompanion:true`，內文 `[Usage limit reached; a short grace allowance remains, then this turn is cut off without warning. …]` | 逐字稿 `C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\d6dfce97-….jsonl` L2154 |
| 04:00:17 | 主控（模型）依提示**自願收尾**（最後一筆 `type=assistant`，有 usage） | 同上 L2173 |
| 04:03:32 | harness 寫 `type=system`、`subtype=away_summary`（recap） | 同上 L2176 |
| 之後 | 視窗開著（到 07:54 才關），harness 每小時追加無 timestamp 的 `cost-state`／`last-prompt`／`file-history-snapshot` ⇒ 檔案 mtime 於 04:55:34／05:55:33／06:55:33／07:54:20 被更新 | 哨兵痕跡的 `逐字稿 Ns 前仍有更新` 數列（417→1318→2218→3117→**897**→1797→2698→3598→**898**…） |
| 04:10:32～07:55:31 | 哨兵 **16 次**巡邏全判 `patrol`：`無未處理撞線；逐字稿 417s 前仍有更新 ⇒ session 還活著，續巡`；同筆痕跡 `controller_idle_seconds` 由 612 漲到 14113 | `%TEMP%\autosdd_resume_log_autosdd_resume_plan_d6dfce97-….jsonl` L49～L96 |

對照組（前一天 sid `ee6af537-7091-4f0e-842c-0d091085f77b`，harness **切斷**而非自願收尾）：L2531 寬限提示（15:56:40Z）→ L2608 `type=system`、`subtype=informational`、`level=notice`、content `Usage limit reached · continuing automatically at 12:10am · esc to cancel`（15:58:11Z＝被切斷那一刻）→ L2610 `queue-operation` enqueue → L2612 system `Usage limit reset · continuing automatically` → L2613 `type=user`、`isMeta:true`、`origin:{"kind":"auto-continuation"}`（16:11:11Z）。⇒ harness 只在「turn 被切斷且視窗仍開」時自動續接；自願收尾不會。

## 〈三〉三根因

- **RC-A（DEF-200-560，P1）**：`halt_verdict` 與 6 小時自我解除的「還活著」讀檔案 mtime（`guard.newest_activity_at`）；harness 的 `away_summary` 與每小時 housekeeping 讓 mtime 永遠新。對話活動早就在 `_main_transcript_idle_seconds` 與痕跡欄 `controller_idle_seconds` 算對了，卻沒餵進判定。
- **RC-B（DEF-200-561，P2）**：repo 根 `.env`（gitignored）第 2 行 `AUTOSDD_RESUME_OFF=1`；R97 起 planner `main()` 先 `apply_env_defaults` ⇒ 本機每支 `--arm-sentinel` 都寫 `allow_resume:false`；DEF-200-480 只密封測試、沒處置設定；簡報與 `--pace` 皆不出聲。
- **RC-C（DEF-200-562，P2）**：`unhandled_limit_event` 只認 `type=assistant`＋`<synthetic>`，`_RESET_RE` 只認 `resets 9am`；harness 2.1.303 的寬限提示／切斷通知／auto-continuation 三種記錄不在偵測面。

## 〈四〉修法與落點（raw 行 before→after；LOC＝`count_loc`／上限）

| 檔 | 改動 | 行數 |
|---|---|---|
| `tools/lib/transcript_activity.py`（新） | `newest_conversation_at`／`usage_limit_signals`／`unhandled_grace_note`／`grace_verdict`（brief 四函式）＋ `conversation_view`（planner 單一入口，LOC 抵銷用）＋常數 `GRACE_ALLOWANCE_SECONDS=900`、`RESET_SOURCE`；`usageLimitNote` 只認兩值（F-1）：`wrap_up`＝寬限提示、`release`＝續接訊號，未知值忽略 | —→243／124／400 |
| `tools/session_resume_planner.py` | `sentinel_decide(grace=)`＋優先序（事件＞halt＞寬限＞idle）；`_sentinel_tick` 改 `conversation_view`、痕跡多帶 `grace_note_at`／`conversation_idle_seconds` | 1689→1693／750→750／750（餘裕 0） |
| `tools/lib/quota_limits.py` | `_RESET_RE` 另認 `continuing automatically at`（同一行）；`newest_activity_at` docstring 訂正「非存活判準」 | 436→436／171→171 |
| `tools/lib/relay_machine.py` | `RESET_SOURCES` 第 7 格 `harness-cutoff-notice` | 629→631／310→311／400 |
| `tools/lib/session_brief.py`、`tools/lib/quota_gate.py` | `escape_hatch_note(env)`（RC-B；簡報尾端＋`pace_report` 兩個回傳面） | 598→630／327→343／400；1217→1220／498→500／500（餘裕 0） |
| `tools/probe/sentinel_decide_replay.py`（新）、`tools/probe/zero_token_patrol_sim.py` | 零 token 重放探針；`append-transcript` 控制組注入的記錄補 timestamp（存活判準改對話記錄後，原控制組不再轉紅 p） | —→81／55；400→403／302→304 |
| `tools/tests/` 四檔 | 新 class 三個＋既有夾具改對話 timestamp（`_fresh_transcript` 加 `age`、e2e `_transcript`）＋白名單 pin 6→7 格 | 見〈五〉 |
| 文件與 CI | 根 `CLAUDE.md`〈額度哨兵〉一條、ADR-XPLAT-004 §2.10、`governance_docs.py` 登記、兩支 compat-ci `paths`、`Root_Layout_and_Module_Placement.md` 額度守衛列補 `transcript_activity.py`；QA 回修（F-2／F-4）：`ADR-XPLAT-014-resume-chain-hardening.md` 三處「白名單 6 格」補註第 7 格、根 `CLAUDE.md`〈守衛面准入〉清單與 `SelfImproving_Protocol/params.json` 的 `non_evolvable_globs` 納入 `transcript_activity` | — |

**偏離任務書（兩處，理由見 Developer 回報）**：① `count_loc` 只算斷言行（ADR-XPLAT-013），註解搬遷抵銷不到 planner 一行；改以「`conversation_view` 收攏＋同函式內 `sentinel_rearmed` 的 `append_log` 折成一行」抵銷 `import` 的 +1；② 任務書「`isMeta:true` 的 user 不算」與「auto-continuation 算」互斥（真機 auto-continuation 記錄自己就是 `isMeta:true`），判準改看 `origin.kind`。

## 〈五〉驗證（Developer 當回合真跑）

- **重放探針**（`--sid d6dfce97-… --now 2026-10-21T04:25:31+08:00`，rc=0；舊 idle 為負＝檔案 mtime 現值晚於 `--now`，見〈六〉11）：

```
mtime 最新（檔案現值）=2026-10-21T07:54:20.539525+08:00；對話最新=2026-10-21T04:00:17.405000+08:00
idle：舊判準（mtime）=-12530s；新判準（對話）=1514s
未處理寬限提示={"timestamp": "2026-10-20T19:59:37.024Z", "continue_at": null, "source": "harness-usage-limit-note"}
舊判準 sentinel_decide ⇒ patrol：無未處理撞線；逐字稿 -12530s 前仍有更新 ⇒ session 還活著，續巡（本次零 token）
新判準 sentinel_decide ⇒ probe：偵測到自願 halt 標記；觀測 reset=2026-10-20 19:59:59.530201+00:00 已過 ⇒ 花一次探測確認額度回來了沒
```

  `--now 2026-10-21T04:10:32+08:00`：新判準仍 `patrol`（對話靜止 615 s ＜ 900 s），與事故當晚第一次巡邏同向。
- **真機語料與時間解析重放（F-1，QA 鏡審 P1 回修）**：本專案逐字稿裡帶 `usageLimitNote` 的記錄共 15 筆＝**8 筆 `wrap_up`（寬限提示）＋7 筆 `release`**（harness 於 auto-continuation 之後 9～18 ms 附上的「[Earlier usage-limit notes no longer apply…]」，isMeta、turnCompanion、無 origin；ee6af537 L2614）。🔴 修前本檔把兩種值都當提示，先前寫的「14 筆已處理、1 筆未處理（0 假陽性）」只看了每支逐字稿的**終態**，不是時間解析。QA 的 `grace_tick_replay_patched.py`（每筆記錄起點後每 150 s 取樣一次、至 12000 s，以真函式判決）：**修前** `notes=15 evaluations=1200 probe_verdict_ticks=198`，9 組 probe 起點中只有 d6dfce97 一組是真陽性、其餘 8 組（8d63899d ×4、ee6af537 ×2、fb85a4a6 ×2）之後仍有對話＝假陽性；`fp_demo.py` 三個真逐字稿截斷點（ee6af537 @2026-10-19T16:35:10Z／@17:30:00Z、8d63899d @2026-10-16T15:30:00Z）修前全判 probe。**修後**（同一支腳本 asis 模式、對修後樹，`HORIZON=12000`）：`notes=15 evaluations=1200 probe_verdict_ticks=74`，只剩 `sid=d6dfce97 note=2026-10-20T19:59:37.024Z probe_samples=74 later_conversation_exists=False`（＝事故本身，真陽性）；`fp_demo.py` 三點皆 `patrol`（`未處理寬限提示=None`，idle 999 s／4289 s／1056 s）。`conversation_view` 掃 6 檔（45.6 MB）約 336 ms（壓縮前量測；對照既有 `unhandled_limit_event` 約 266 ms，量測時全套測試併跑）。
- **測試**（Developer 當回合真跑，rc 逐條；單檔 `unittest discover`，原始輸出在 Developer scratchpad `dev\fv2_*.txt`；以下為 QA 回修〔F-1／F-2／F-4〕之後的完工樹）：
  - `test_wake_chain_halt_r278.py -v`：`Ran 72 tests … OK`，rc=0（新 `ConversationActivityReplayTest` 6 支、`PaceReportSaysTheEscapeHatchesTest` 1 支）；
  - `test_context_budget_guard.py`：`Ran 835 tests … OK (skipped=1)`，rc=0（新 `HarnessUsageLimitSignalsTest` 11 支，其中 3 支為 F-1 的 `release`／未知值測試）；
  - `test_session_brief*.py`：`Ran 102 tests … OK`，rc=0（新 `EscapeHatchNoteTest` 3 支）；`test_sentinel_tick_e2e_r145.py`：`Ran 13 tests … OK`，rc=0；
  - `zero_token_patrol_sim.py --selftest`：rc=0「全數符合（斷言 6 項＋控制組 7 組）」；`selfimproving.py check`：rc=0（`si-check rows=246 items=28`、`PASS params.globs`）；
  - 根層全套 `run_root_unittests.py`（workers=18，QA 回修後的完工樹）：發現 5600 個（下限 5542；HEAD 提交訊息所載 5579，多的 21＝本棒新增 18 支＋F-1 三支）、**2 failures／0 errors，rc=1**——兩支皆為 N1（帳本淨額棘輪，歸主控）：`test_check_defect_log_crossref.TestEarlyExitAnnouncesUnrunChecks.test_the_real_gate_still_reaches_the_late_checks` 與 `TestMain.test_main_against_real_repo_is_clean`，成因＝主控寫入的 DEF-200-560／561／562 三列尚未 commit（`check_defect_log_crossref.py` 同為 rc=1：「淨額棘輪違反：本輪新增未結 3 筆 > 結案 0 筆」），commit 後消失；其餘全綠——先前因帳本無三列而紅的`test_defect_id_reference_integrity…` 與 `test_frozen_prefix_rewrite_ledger_chains_and_validates_def_ids` 兩支已隨帳本三列入帳轉綠（本次全套的失敗清單裡不再有它們）；
  - `ci-gate.ps1`：rc=0（SDD v0.01 1478／v0.30 2250／scripts/tests 425 passed；`test_ci_paths_cover_root_consumers.py` 在 scripts/tests 內，兩支 compat-ci 的 `paths` 已含新檔）。
- **突變自證**（突變→紅→用 `Edit` 改回→綠；被突變的五支檔中四支改回後 SHA256 與突變前快照一致，`session_brief.py` 只多改回之後才做的一行註解訂正）：
  - M1 planner `idle` 改回 `guard.newest_activity_at`（mtime）⇒ `ConversationActivityReplayTest.test_the_real_tick_probes_a_stopped_session_and_leaves_a_working_one_alone` 紅：`(0, 'patrol', 0, […]) != (7, 'probe', 1, [])`。任務書預期紅的 (b)(c) 是純函式斷言、不經 planner 那一行，故由 tick 整合測試咬住（(b)(c) 仍在，鎖語意）；
  - M2 拿掉 `sentinel_decide` 的 grace 分支 ⇒ 3 支紅：同一整合測試（`(0, 'patrol', 0) != (7, 'probe', 1)`）、`test_without_a_halt_marker_the_grace_note_alone_wakes_the_sentinel`（`'patrol' != 'probe'`）、`HarnessUsageLimitSignalsTest.test_sentinel_decide_ranks_event_then_halt_then_grace_then_idle`；
  - M3 `_RESET_RE` 改回只認 `resets` ⇒ `test_the_cutoff_notice_parses_like_a_reset_literal`、`test_an_unhandled_note_has_states_and_an_exact_boundary` 紅（`None != datetime(2026, 10, 20, 0, 10, …)`）；
  - M4 `escape_hatch_note` 恆回 `""` ⇒ `EscapeHatchNoteTest` 3 支（5 個 failure 含 subTest）與 `PaceReportSaysTheEscapeHatchesTest`（4 個 subTest）紅；
  - 加碼：M5（`system`／`attachment` 也算活動）⇒ `test_only_conversation_records_move_the_activity_clock` 紅；M6a／M6b（`pace_report` 兩個回傳面各漏接 `hatch`）⇒ 對應 subTest 紅；M7（planner 不傳 `grace=`）⇒ tick 整合測試紅；
  - **F-1 突變**（QA 回修）：`transcript_activity.usage_limit_signals` 的 `note == _NOTE_WRAP_UP` 改回「任何非空 note」⇒ `test_a_release_after_the_auto_continuation_is_not_a_new_note` 紅：`AssertionError: {'timestamp': '2026-10-19T16:11:11.215Z', 'continue_at': None, 'source': 'harness-usage-limit-note'} is not None`（release 被當成最後一筆提示）；同一突變下 `test_a_release_alone_after_a_note_counts_as_handled`、`test_unknown_usage_limit_note_values_are_ignored` 亦紅（共 3 支，`Ran 11 tests … FAILED (failures=3)`）；改回後 SHA256 與突變前一致、`Ran 835 tests … OK`。
- **LOC／lint**：`check_loc_budget.py --json` rc=0（`special_violations`／`tier_violations`／`absolute_violations`／`root_tools_violations` 皆空）；planner 750／750（餘裕 0）、`quota_gate.py` 500／500（餘裕 0）、`quota_messages.py` 398／400（未動）、`quota_limits.py` LOC 171／raw 436（皆不變）、`session_brief.py` 343、`relay_machine.py` 311、新 `transcript_activity.py` 124／400（raw 243）、新探針 55；`.venv\Scripts\ruff.exe check` 14 檔 rc=0 `All checks passed!`；`test_context_budget_guard.py` 的 E501 存量（`ruff --isolated --select E501 --line-length 100`）仍 5 筆、未升；`git diff --check` rc=0（無輸出）。
- **護欄層棘輪**（`--print-guard-lines` 最終 rc=0）：淨額 128203→128652（+449；F-1 回修使 `test_context_budget_guard.py` 再 +43，原 +406）重釘為 R214 列（主軌 +449 ≤ 515、回歸鎖軌 0）；最終印 `淨額 128652→128652 (+0)`、`逐檔漂移 0 支`；`_REPIN_LOG_FROZEN_PREFIX_LEN` 347→348、`_REPIN_LOG_HISTORY_SHA256` 重釘為 `85c3fe9e…`、`_FROZEN_PREFIX_REWRITE_LEDGER` 追加 R214 列（指名 DEF-200-560）；到期義務兌現 `(214, 515)` 並重新武裝 216／514；`_PHASE2_REVIEW_LOG` 補 R214 列；兩站點 `guard-total:R214`（本檔旁的 `CrossPlatform_R145_Scan_Findings.md`、`AutoSDD_improving_112.md` 尾端）；分桶 prose 4350／guard_self 3149（與 HEAD 相同）；`check_defect_log_crossref.py` rc=1（只剩 N1：帳本淨額棘輪「本輪新增未結 3 筆 > 結案 0 筆」，歸主控；其餘項為 ✅／警告）、`check_handoff_carriers.py` rc=0（`[census] 當前輪＝R214`）。
- **持有面外、被鎖逼出的連動**：`ADR-XPLAT-002-platform-surface-reduction.md` 覆蓋表補 R214 列（SC-10 以本檔檔名推得當輪，缺列即紅）。
- **交主控**：① N1（帳本三列的淨額棘輪，及其連動的兩支全套測試）歸主控——三列 commit 後消失；② 本檔落地使「當前輪」推得值變 R214，`check_defect_log_crossref.py` 對 DEF-200-559／560／561／562（承接輪次 R214 恰等於當前輪）印 fail-open 窗口警告（只警告）——請在本輪結案時處置這幾列；③ 追加〈七〉親驗（含 push 後的 CI 現查與真機端到端）。

## 〈六〉理論洞清單（只登記、不修；暴露證據＝無，依〈守衛面准入〉P4）

1. **harness 自動續接與哨兵探測的競態窗**：切斷通知自報的續接時刻＋120 s 哨兵才醒；harness 若遲於此才寫 `auto-continuation`，哨兵看到對話靜止已滿一個巡邏間隔 ⇒ `probe`（`allow_resume` 時 spawn `claude -p -r`），與 harness 自動續接同窗（雙窗，上界一個巡邏間隔）。
2. **`GRACE_ALLOWANCE_SECONDS`＝900 是挑的、不是量出來的**：真機兩次收尾實測 40 s／91 s，harness 沒有契約值。調小會把「主控仍在依提示收尾」誤判成已處理；調大會延後未處理提示的判決。
3. **`continuing automatically at 12:10am` 無日期、無時區**：以切斷記錄當下的時刻、`now` 的時區解成「下一個尚未發生的」該時刻；機器時區與 harness 算繪時區不一致、或日後格式帶星期／日期時解不出 ⇒ `continue_at=None` ⇒ 退回「靜止滿一個巡邏間隔才探測」。
4. **寬限提示通道不看 `superseded_by`**：halt 標記通道有 DEF-200-532 的「他 session 已接手 ⇒ disarm」，寬限提示通道沒有；無標記（statusLine 快取過期）時人已在同專案另一視窗工作，仍會在本 session 靜止滿 900 s 後探測續跑。另 `superseding_session` 只數 assistant 回合（`session_evidence`），與本輪的「對話記錄」定義不同源。
5. **`usageLimitNote` 值域靠語料歸納、不是契約（F-1 已修，留作教訓）**：先前把「寬限提示會再附在 auto-continuation 那一回合」當成理論洞登記，實為誤讀——那是 `usageLimitNote:"release"`（8 `wrap_up`＋7 `release`），把它當提示會讓 harness 剛自動續接、續跑回合在寬限期內結束並靜止 ≥900 s 的 session 被判 probe（QA 時間解析重放修前 9 組 probe 起點 8 組假陽性，修後只剩事故本身，見〈五〉）。現行處置＝`note_at` 只認 `wrap_up`、`release` 算續接訊號、**其餘值一律忽略（寧可不叫醒）**；日後 harness 若新增第三種值，會被忽略而不是被誤判，代價是該型態退回 idle 判定。
6. **字面來自 harness 2.1.303／2.1.304 實測**：`usageLimitNote` 值域（`wrap_up`／`release`）、`origin.kind` 值域（`human`／`auto-continuation`）、`continuing automatically at`、`Usage limit reset` 任一改字，該通道靜默失效（退回 idle 判定＝改前行為），與 `quota_limits._LIMIT_MARKS` 同型脆弱面。
7. **`AUTOSDD_RESUME_OFF=`（空字串）設在 OS 環境變數時**：planner 以 `is None` 判關（空字串＝關），`escape_hatch_note` 以「值非空白」判有設（與 `apply_env_defaults` 填充判準一致；`policy_env()` 分不出 `.env` 空值與環境變數空值），簡報不出聲。
8. **`quota_limits.newest_activity_at`（mtime 版）仍被 hook 再匯出**：可被日後誤用成存活判準；本輪只訂正 docstring 與測試標題，未加守衛碼。
9. **每次巡邏全檔掃描**：`conversation_view` 逐行掃主檔與 subagent 檔（只解析含 `"assistant"`／`"origin"` 字面的行），零 token 但耗 CPU／IO；〈五〉真機語料一條量測約 336 ms／45.6 MB，未設上限。
10. **兩個 hub 檔滿載**：`session_resume_planner.py`（`guardrail_cli`）與 `quota_gate.py`（`guardrail_hub`）本輪結束餘裕皆為 0；再動它們的修復必須先拆職責，否則只能再以折行換行數。
11. **重放探針的誠實劃界**：舊判準取檔案 mtime **現值**（歷史 mtime 不可重建），`--now` 早於檔案最後寫入時舊 idle 為負；不重建 `superseded_by`。
12. **ADR-XPLAT-014 三處「白名單 6 格」為帶日期的歷史陳述**（現為 7 格）：原句保留，QA 回修（F-2）已於各處補註「R214 起第 7 格 `harness-cutoff-notice`（DEF-200-562；ADR-XPLAT-004 §2.10）」；ADR-XPLAT-004 §2.10 同記第 7 格。
13. **已納入（R214，主控裁決，QA 回修 F-4）**：`transcript_activity.py` 實質屬守衛面（planner 每次巡邏必經），原先不在根 `CLAUDE.md`〈守衛面准入〉清單，歷輪證據檔「守衛面量具」的 `git diff --numstat` 路徑集也不含它。現已把 `transcript_activity` 加進該清單的 brace 展開，並於同一批把 `tools/lib/transcript_activity.py` 加進 `docs/06_quality/SelfImproving_Protocol/params.json` 的 `non_evolvable_globs`（`si check` 的 GLOBS-SET-MISMATCH 判準＝PRD 實體 glob ∪ 根 CLAUDE.md 守衛面展開須恰等於該陣列；`params.globs` PASS）。歷輪證據檔裡帶日期的「守衛面量具」指令是當輪快照、不回改；日後的量具路徑集須含本檔。`.claude/hooks/` 的治理檔唯讀集在 `.claude/**` 射程外，本棒不碰。
14. **寬限提示通道在「有未處理提示」時多掃一輪**：`unhandled_grace_note` 於提示未被續接記錄處理時會再呼叫 `newest_conversation_at(paths)`，而 `conversation_view` 已算過同一批檔一次；只在事故形態（提示未處理）每次巡邏多一輪全檔掃描。函式簽名依任務書 §3.1 固定，未改。

## 〈七〉主控親驗（2026-10-21 10:5x～11:1x +08:00；sid `e9f8e2cb-c1fd-4234-8f8a-f1c546529cf1`；每格都是當場輸出）

- **單元與判準**：`test_context_budget_guard -k HarnessUsageLimitSignalsTest` Ran 11 OK；`test_wake_chain_halt_r278` Ran 72 OK；`test_session_brief*` Ran 102 OK；`test_defect_id_reference_integrity` 11 OK；`python tools/selfimproving.py check` overall=PASS rc=0（`params.globs` 含 `tools/lib/transcript_activity.py`）。
- **時間解析重放**（QA 鏡審腳本 `grace_tick_replay_patched.py`，asis 模式、HORIZON=12000）：`notes=15 evaluations=1200 probe_verdict_ticks=74`，唯一 probe 起點＝d6dfce97（`later_conversation_exists=False`＝真陽性）；修前同腳本為 198 個取樣點／9 組起點（QA 一審 F-1 的假陽性）。
- **重放探針** `tools/probe/sentinel_decide_replay.py`：d6dfce97 `--now 04:25:31` 舊判準 patrol（mtime idle −12530 s）→ 新判準 probe（對話 idle 1514 s）；`--now 04:10:32` 新判準 patrol（615 s < 900 s）；ee6af537（harness 已自動續接）兩判準皆 arm_reset、「未處理寬限提示＝（無）」。
- **真機端到端**（拋棄式 sid `069c4ab4-db53-4f78-9365-89f25b1a079e`，haiku；腳本與痕跡＝主控 scratchpad `si_p2\e2e_sentinel.ps1`／`e2e_sentinel_run2.log`）：`--arm-sentinel` ⇒ `NextRunTime = 2026/10/21 上午 11:09:43`、狀態塊 `allow_resume: true`（`.env` 的 `AUTOSDD_RESUME_OFF=1` 已於 08:13 刪除）→ 合成 halt 標記（reset_at 已過 3 分鐘、at 2.5 分鐘前，避免同專案他 session 被判接手）→ 手動 `--sentinel-tick`：痕跡 `sentinel_decided action=probe`（`conversation_idle_seconds` 8012）→ `probed rc=0 quota_open=true source=endpoint` → `route_chosen SESSION_RESUME`（501,601B ≤ 33,554,432B）→ `resumed rc=0 handback_written=true`（無頭視窗以 haiku 回覆 833 tokens、handback 落 `~/.autosdd/handback/069c4ab4-….md`）→ `relay_stopped why=no_progress`（拋棄式無工作、`files_changed=0`，如實）→ `relay_rearmed next_state=NO_PROGRESS_STOP`；收尾 `--remove-schtasks` REMOVED、合成標記已刪。結論：「自願停機 → 哨兵 → 探測 → headless 喚醒」整鏈在真機成立。
- **同一痕跡暴露的新缺陷 DEF-200-563（P1，open）**：被喚醒的無頭視窗 5 次 PowerShell 呼叫皆 `is_error`：`Command contains malformed syntax that cannot be parsed: pwsh exited with code 1: 命令列太長。`（CP950 位元組 A952／A54F／A643／A4D3／AAF8／A143）。隔離探針（皆 haiku、`echo ok`）：A 純無頭＋`--allowedTools PowerShell`＝ok；B `--settings .claude/settings.unattended.json`＝失敗；C `AUTOSDD_UNATTENDED=1`＝ok；D 只 `additionalDirectories`＝ok；E 只 `defaultMode`＝ok；F 無 `PowerShell(...)` 規則＋allowedTools＝ok；G 只有 `PowerShell(git status*)`／`PowerShell(git commit*)`＝失敗；H 工具層 `"PowerShell"` allow＋刪 `PowerShell(...)` allow 樣式＋deny 全留＝ok；I 工具層 allow＋一條 PowerShell deny＝ok；J 工具層 allow＋`PowerShell(echo*)` deny ⇒ `echo ok` 被拒（deny 仍有效）。`--debug` 逐字：`PowerShell parser: pwsh exited 1 … (attempt 1)`／`(attempt 2)` → `PowerShell tool permission denied`。修法＝姿態檔 allow 改工具層 `PowerShell`、刪 8 條 `PowerShell(...)` allow、deny 全留（成品 `si_p2\settings_probe_H.json`）；主控 Edit 該檔被 auto mode 分類器拒（[Self-Modification]）⇒ 待掌舵者套用；harness 缺陷另以 /feedback 回報。
- **未驗（照實寫）**：push 後雲端 CI；QA 鏡審二審判決（本 commit 於其判決前落地，理由＝五小時額度 94%）；DEF-200-563 的修法尚未套用到 `.claude/settings.unattended.json`（分類器保護），套用後需再跑一次 e2e 證明無頭視窗能跑 PowerShell。
- **清理與殘留**：拋棄式哨兵工作已 REMOVED、合成標記已刪；`%TEMP%` 的任務書與痕跡、`~/.autosdd/handback/069c4ab4-….md` 保留為證據（`--pace` 會印「上次無人續跑停在 no_progress」一行，屬該拋棄式運轉，非本輪缺陷）。
