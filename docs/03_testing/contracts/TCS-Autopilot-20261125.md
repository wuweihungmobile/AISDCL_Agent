# TCS-Autopilot-20261125：自動駕駛開發——單一額度判決、換帳號作廢、合入推送管線、詢問類別閘（需求＋驗收合一）

> 上游：PRD `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 修訂表 v2.1.28、§4.1.6、§4.1.7、§4.5.12、§15.5 紅線 14、§16.6 2026-11-25 兩列；設計 `docs/02_architecture/QuotaVerdict_AccountSwitch_Design.md`（下稱 QVD）、`docs/02_architecture/Autopilot_Pipeline_Design.md`（下稱 APD）。
> **狀態（2026-11-25，SD-0）**：規格階段，實作未開始。所有 AT／MU／E2E 狀態欄＝「待實作」；未跑不得寫成已驗。
> 測試座標約定：`QV`＝`tools/tests/test_sessionctl_qv.py`（新）、`MG`＝`tools/tests/test_autopilot_merge.py`（新）、`PS`＝`tools/tests/test_autopilot_push.py`（新）、`HK`＝`tools/tests/test_sessionctl_hooks.py`（既有，增量）、`OW`＝`tools/tests/test_sessionctl_oldwin.py`（既有，增量）、`CW`＝`tools/tests/test_ci_wait.py`（既有，增量）、`CR`＝`tools/tests/test_check_defect_log_crossref.py`（既有，增量）、`PH`＝`tools/tests/test_check_pending_handoff.py`（既有，增量）、`CP`＝`tools/tests/test_claim_provenance_r86.py`（既有，增量）。單元測試一律注入 `now`、路徑圍籬到 tmp、不讀真 `~/.claude`、不起真排程、不打真端點；禁用 skip。
> **E2E 定義**（掌舵者 2026-11-18：「請將所有功能都寫好完整的E To E測試案例,不要遺漏任何一個!」）：真行程、真排程、真 `claude -p` 子行程、真 git、真逐字稿重放（sid `406454ea-91fc-4481-9c11-b28ed7d9e95f`）或真讀數錄製重放才算；單元測試不算。載具＝`python tools/realverify.py run --family <家族>`，結果入帳 `docs/06_quality/RealVerify_Result_Ledger.md`；未入帳＝未結。「錄製重放」＝把真實端點回應（payload＋兩個帳號標頭，取自真實 `quota_burn.jsonl` 的 `34cd3507237f`／`eaf5241f6fe2` 樣本）錄成夾具，經 `quota_meter` 既有注入縫回放（不新增端點知識站點，守紅線 1 (b)）。

## 0. 模組落點表（照 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）

| 元件 | 路徑 | §2 格 |
|---|---|---|
| QV 判決／取數／呈現 | 新 `tools/lib/sessionctl/qv_verdict.py`、`qv_io.py`、`qv_render.py` | 函式庫（既有 sessionctl 套件；WHY 見 QVD §8） |
| 換帳號 | 新 `tools/lib/sessionctl/acctswitch.py` | 同上 |
| 詢問類別閘 | 新 `tools/lib/sessionctl/askgate.py`；接線 `.claude/hooks/sessionctl_guard.py`、`.claude/settings.json` | 同上＋守衛面 |
| 合入／推送 | 新套件 `tools/lib/autopilot/`；入口 `tools/autopilot.py` | 函式庫（新套件）＋指令入口 |
| LOC 抽出 | 新扁平 `tools/lib/model_window_table.py`；`quota_halt_marker.py` 承接 halt 判讀 | 函式庫（扁平共用） |
| 既有改動 | `ledger_closing_guards.py`、`tools/git-hooks/pre-push`、`ciwait/core.py`、`oldwin.py`、`oldwin_sched.py`、`check_pending_handoff.py`、`check_claim_provenance.py`、`context_budget_guard.py`、`run_root_unittests.py`、`session_resume_planner.py`、`quota_*`、`session_brief.py`、sessionctl watch／park 族 | 既有家 |
| 測試 | 新三檔（QV、MG、PS）＋既有檔增量 | 測試 |
| 真機 E2E 家族 | `tools/lib/realverify/cases/quotaverdict.py`、`tools/lib/realverify/cases/autopilot.py`（新家族檔） | realverify |

## 1. 需求（REQ）

| REQ | 需求 | PRD／設計 | 狀態 |
|---|---|---|---|
| REQ-AP-QV-01 | 單一判決函式：同一份輸入只產一個 ACTION；原始讀數帶與 QW stage 在函式內合成（QVD §3.2 決策表六列） | R-4.1.6-1、R-4.1.6-4 | 待實作 |
| REQ-AP-QV-02 | 判決行格式與有效期；過期必重算 | R-4.1.6-2、R-4.1.6-3；QVD §3.3、§4 | 待實作 |
| REQ-AP-QV-03 | halt 標記不壓補量；補量受紅線 1 四條件 | R-4.1.6-6；QVD §3.4 | 待實作 |
| REQ-AP-QV-04 | park 只在判決 `PARK｜HALT_WEEKLY` 時登記；`--why` 退役、`--next-est` 取代 | R-4.1.6-5；QVD §5 | 待實作 |
| REQ-AP-QV-05 | watch 額度事件只由判決觸發、單一序列閂鎖 `(acct, ACTION, win)`；`WAIT_RESET` 處置不含 park | R-4.1.6-2／4；QVD §3.5 | 待實作 |
| REQ-AP-QV-06 | 主控額度宣稱須有本回合未過期判決行（Stop 只出聲） | R-4.1.6-7 | 待實作 |
| REQ-AP-QV-07 | 讀不到判決 ⇒ `NODISPATCH` 並出聲；`--json` 帶 `billing` 欄（與 `posture_line` 同源） | R-4.1.6-8；QVD §3.3 | 待實作 |
| REQ-AP-QV-08 | LOC 抽出為純搬移：搬移 commit 全套綠、行為零差異；抽出後各檔在分級內、`SPECIAL_FILES` 門檻下修 | QVD §9 | 待實作 |
| REQ-AP-AC-01 | halt 標記、rush 戳記、閂鎖、保溫帳新寫入帶 `account`；量不到寫 `null` 並出聲 | R-4.1.7-1 | 待實作 |
| REQ-AP-AC-02 | 帳號不符 ⇒ 標記改名 `.void-<ts>` 作廢、落 `account_switch`、出聲一次；舊格式標記依同軸讀數判 | R-4.1.7-3～5 | 待實作 |
| REQ-AP-AC-03 | 三個零 API 觸發器（憑證檔 mtime／size、逐字稿 `/login`、指紋變化）皆觸發補量 | R-4.1.7-2 | 待實作 |
| REQ-AP-AC-04 | 被動觀測：真實 `/login` 後一個 TTL 內必有 `account_switch`；判決行附「已作廢 n 個」 | R-4.1.7-6 | 待實作 |
| REQ-AP-MG-01 | `autopilot merge`：repo 外 rebase、略過已吸收、帳本尾端提交、補連動鎖、全套、綠才 ff、清理；冪等、不留半套 | APD §3.2 | 待實作 |
| REQ-AP-MG-02 | 合入期全套＝pre-push 同款（合成 stdin 呼叫，leg 集合相同） | APD §3.3 | 待實作 |
| REQ-AP-WT-01 | 代理 worktree 起點＝本地 HEAD（`worktree.baseRef: "head"`）；merge 記錄 `base_drift` | APD §3.1 | 待實作 |
| REQ-AP-G1-01 | 帳本淨額棘輪：推送期基準＝remote sha 並阻斷；提交期只出聲 | APD §4.1 | 待實作 |
| REQ-AP-G1-02 | 推送閘：淨額 > 0 ⇒ 產同輪修復任務書、前綴推送；判決非 `CONTINUE` 不推 | APD §4.2、§4.3 | 待實作 |
| REQ-AP-G1-03 | `AUTOSDD_NET_RATCHET_OFF` 在 `CLAUDECODE` 或 `AUTOSDD_UNATTENDED` 下無效並出聲 | APD §5 | 待實作 |
| REQ-AP-ASK-01 | AskUserQuestion 類別閘：只放行 `[IRREVERSIBLE]`（任何系統整體毀壞不可復原，必填系統與原因）、`[COST]`（非訂閱制且預估 > 50 美元；`billing=subscription_only` 一律擋）、`[K1]`（須寫「須掌舵者親打」）；可代決詞表優先阻斷；無人窗口全擋；放行落 `ask_allowed` | R-4.5.12-3～5；APD §7 | 待實作 |
| REQ-AP-ASK-02 | `check_pending_handoff` 推回文案改「先代決、三類才問」；描述分類規則／複述掌舵者定義的句子不判交棒；`check_claim_provenance` 不把敘述過去事件的「被擋／擋下」當本場宣稱 | R-4.5.12-1；APD §7、§13 | 待實作 |
| REQ-AP-CI-01 | `ci_wait` 認得排隊逾時（`queue_timeout`）並自動重跑（同 sha ≤ 2 次） | APD §6 | 待實作 |
| REQ-AP-OW-01 | 舊視窗關閉事件驅動＋指數退避（上限 12 小時）；任何文案不含「請手動」「請您」 | R-4.5.12-1／2；APD §8 | 待實作 |
| REQ-AP-FN-01 | 全套期間痕跡圍籬：真痕跡目錄出現夾具形新列 ⇒ 全套 rc≠0 | APD §9 | 待實作 |

## 2. 驗收（AC → AT）

### 2.1 QV（`QV::VerdictTest` 等；純函式，注入 state／markers／plan／now）

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-QV-01a | 短窗 87%、D=14、`stage=free`、`QV_WAIT_RESET_MIN=45` ⇒ `WAIT_RESET`；輸出不含 `PARK` | `QV::VerdictTest::test_87pct_14min_waits_reset_not_park` |
| AC-QV-01b | 決策表六列逐列正反例（含第 3 列 D>45 ⇒ `PARK`、量不到 reset ⇒ `PARK`、第 2 列週軸 ⇒ `HALT_WEEKLY` 優先於短窗） | `QV::VerdictTest::test_table_rows_*` |
| AC-QV-01c | 性質：對笛卡兒積（band × stage × D × next_est × 標記）輸出恰一個 ACTION、`cap>0` 僅在 `CONTINUE` | `QV::VerdictTest::test_exactly_one_action_property` |
| AC-QV-01d | 重放真實 `quota_burn.jsonl`（測試時複製到 tmp 的固定夾具，取自 2026-11-11～25）每列，「同一輸出兩個 ACTION」＝0 | `QV::VerdictTest::test_burn_ledger_replay_single_action` |
| AC-QV-02a | 判決行欄位齊全、`expires_at＝min(measured_at+180s, 短窗 reset)`、時刻帶 offset、`vid` 對同輸入穩定 | `QV::RenderTest::test_line_fields_and_expiry` |
| AC-QV-02b | `--pace`、watch、park、SessionStart 簡報四處第一個額度行皆為 `QUOTA_VERDICT=` | `QV::ConsumerTest::test_four_consumers_print_verdict_first` |
| AC-QV-02c | 消費端拿到過期判決 ⇒ 重算並落 `stale_verdict_recomputed`；不以舊 vid 行動 | `QV::ConsumerTest::test_stale_verdict_recomputed` |
| AC-QV-03a | halt 標記有效＋快取超過 TTL ⇒ 補量恰一次（同 TTL 內第二次不補） | `QV::GatherTest::test_halt_does_not_suppress_refresh` |
| AC-QV-03b | 429 ⇒ 降級出聲、判決 `NODISPATCH`、不重試 | `QV::GatherTest::test_429_degrades_to_nodispatch` |
| AC-QV-04a | 判決 `CONTINUE` ⇒ `park` rc 4 並印判決行；傳 `--why` ⇒ argparse 錯誤並指路 `--next-est` | `QV::ParkTest::test_continue_refuses_and_why_retired` |
| AC-QV-04b | `--next-est` ≥ R−V 且 D>45 ⇒ `PARK` ⇒ 登記（縫 `ARM`）並印排程憑證；D≤45 ⇒ `WAIT_RESET`、不登記 | `QV::ParkTest::test_next_est_drives_park_or_wait` |
| AC-QV-05a | watch 單一序列：`WATCH_VERDICT=quota action=<A> vid=<v> expires_at=<t>`；同 `(acct,ACTION,win)` 只觸發一次 | `QV::WatchTest::test_single_series_latch` |
| AC-QV-05b | `WAIT_RESET` 處置列不含「park」；`keepwarm.SERIES` 不存在 | `QV::WatchTest::test_wait_reset_disposition_has_no_park` |
| AC-QV-06a | Stop 宣稱守衛：重放 L2564 回合（夾具化逐字稿片段）⇒ 出聲一次 | `CP::QuotaVerdictClaimTest::test_l2564_claim_without_verdict_voices` |
| AC-QV-06b | 同回合有未過期 `QUOTA_VERDICT=` ⇒ 靜默；只有過期者 ⇒ 出聲 | `CP::QuotaVerdictClaimTest::test_fresh_verdict_silences` |
| AC-QV-07a | 讀不到 state 或帳號量不到且有軸 ≥ prepare ⇒ `NODISPATCH`＋出聲 | `QV::VerdictTest::test_unreadable_is_nodispatch` |
| AC-QV-07b | `billing` 四值推導與 `posture_line()` 同源（共用函式）；欄位缺 ⇒ `unknown` | `QV::RenderTest::test_billing_from_posture` |
| AC-QV-08a | 抽出後 `check_loc_budget --json` 無違規；`context_budget_guard.py` 的 `SPECIAL_FILES` 門檻等於新實值 | `tools/tests/test_adr_xplat001_c1c2_lock.py`（既有，CLOSE 重釘後綠） |
| AC-QV-08b | `pace_report` 不再存在於 `quota_gate`（hub 成員只縮不長） | `QV::LocTest::test_pace_report_moved_out_of_hub` |

### 2.2 AC 換帳號（`QV::AcctSwitchTest`）

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-AC-01a | 三種持久狀態新寫入 schema 必有 `account`；量不到 ⇒ `null`＋出聲 | `QV::AcctSwitchTest::test_writes_carry_account` |
| AC-AC-02a | 標記 `34cd3507237f`、快取 `eaf5241f6fe2` ⇒ 改名 `.void-<ts>`、`account_switch` 一列、出聲一次、`--pace` 不印 halted | `QV::AcctSwitchTest::test_mismatch_voids_marker` |
| AC-AC-02b | 舊格式標記＋同軸讀數低於門檻 ⇒ 作廢；高於 ⇒ 保留並補寫 `account` | `QV::AcctSwitchTest::test_legacy_marker_by_reading` |
| AC-AC-02c | park 標記不在本流程作廢（走 `parkprobe.account_changed`）；rush 戳記不符即作廢 | `QV::AcctSwitchTest::test_park_delegated_rush_voided` |
| AC-AC-03a | 憑證檔 (mtime,size) 變 ⇒ 觸發；不變 ⇒ 不觸發；macOS（注入平台）⇒ T① 缺席並照實出聲 | `QV::AcctSwitchTest::test_trigger_credentials_file` |
| AC-AC-03b | 逐字稿增量出現 `<command-name>/login</command-name>` ⇒ 觸發；byte offset 前已讀者不重觸發 | `QV::AcctSwitchTest::test_trigger_login_record` |
| AC-AC-03c | 指紋變化 ⇒ 觸發 reconcile | `QV::AcctSwitchTest::test_trigger_fingerprint_change` |
| AC-AC-04a | 換帳號後第一行判決附「已作廢 n 個舊帳號標記」；同一對 old→new 只出聲一次 | `QV::AcctSwitchTest::test_first_verdict_reports_voided` |
| AC-AC-04b | 任何輸出不含「建議換帳號」類字樣（詞表） | `QV::AcctSwitchTest::test_no_switch_advice_wording` |

### 2.3 合入、推送、棘輪（`MG`／`PS`／`CR`；真 git 於 tmp 拋棄式 repo）

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-MG-01a | W11b2 形狀（代理起點落後、main 已含 W6）⇒ rebase 成功；有衝突 ⇒ `conflict`＋衝突包、主樹與拋棄式 worktree 都不留 rebase 狀態 | `MG::MergeTest::test_rebase_or_conflict_bundle` |
| AC-MG-01b | 同指令重跑 ⇒ `MERGE_VERDICT=noop`（patch-id 略過） | `MG::MergeTest::test_idempotent_rerun` |
| AC-MG-01c | 全套紅（縫：假 pre-push 回 1）⇒ `red`、主樹 HEAD 不動 | `MG::MergeTest::test_red_suite_keeps_main` |
| AC-MG-01d | 帳本變更散在三個提交 ⇒ 結果中帳本只出現在尾端單一提交、其餘提交不含帳本檔 | `MG::MergeTest::test_ledger_changes_moved_to_tail` |
| AC-MG-01e | 清理用 `git worktree remove`（不帶 `--force`）與 `git branch -d`；`git worktree list` 回到起始集合 | `MG::MergeTest::test_cleanup_no_force` |
| AC-MG-01f | 鎖：第二個 merge 在鎖存在時回 `busy`；主樹髒 ⇒ `dirty` | `MG::MergeTest::test_lock_and_dirty` |
| AC-MG-01g | `repin_growth_problems()` 非空 ⇒ `repin_blocked`、不改上限常數 | `MG::MergeTest::test_repin_blocked` |
| AC-MG-02a | 合成 stdin 呼叫的 pre-push 與真 `git push` 觸發的 pre-push 收到相同四欄、跑相同 leg 集合（以 leg 名稱集合比對） | `MG::PrePushParityTest::test_synthetic_stdin_same_legs` |
| AC-WT-01a | `.claude/settings.json` 含 `worktree.baseRef == "head"` | `HK::SettingsTest::test_worktree_baseref_head` |
| AC-WT-01b | `--base-at-dispatch` 與 merge-base 不等 ⇒ 落 `base_drift` 痕跡、仍完成 rebase | `MG::MergeTest::test_base_drift_recorded` |
| AC-G1-01a | `PHASE=push`＋`BASE=<舊 sha>`、工作樹＝HEAD 但 HEAD 比 base 多 1 筆未結 ⇒ 阻斷 | `CR::PushRangeRatchetTest::test_push_phase_uses_remote_base` |
| AC-G1-01b | 未設 `PHASE`（提交期）淨額 > 0 ⇒ 出聲、問題清單為空 | `CR::PushRangeRatchetTest::test_commit_phase_voices_only` |
| AC-G1-01c | pre-push 匯出兩變數（新分支用 merge-base 回退值） | `CR::PushRangeRatchetTest::test_prepush_exports_base` |
| AC-G1-02a | 尾端提交含新未結列 ⇒ `PUSH_VERDICT=net_positive prefix=<尾端父提交>`、產修復任務書 | `PS::PushGateTest::test_prefix_push_on_net_positive` |
| AC-G1-02b | 修復提交把列轉 fixed ⇒ 整段可推 | `PS::PushGateTest::test_full_push_after_fix` |
| AC-G1-02c | 判決非 `CONTINUE`（縫：假 `sessionctl quota --json`）⇒ 不推 | `PS::PushGateTest::test_no_push_unless_continue` |
| AC-G1-03a | `CLAUDECODE=1`＋OFF ⇒ 照常判並出聲；`AUTOSDD_UNATTENDED`＋OFF 同；兩者皆無＋OFF ⇒ 依舊放行 | `CR::PushRangeRatchetTest::test_off_ignored_under_claudecode` |

### 2.4 詢問類別閘與推回（`HK`／`PH`／`CP`）

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-ASK-01a | 重放 L2431 的問題（推送逃生口）⇒ rc 2，訊息含三類清單 | `HK::AskGateTest::test_l2431_blocked` |
| AC-ASK-01b | `[IRREVERSIBLE]`＋`系統：<x>`＋`不可復原原因：<y>`、無詞表命中 ⇒ 放行並落 `ask_allowed`；系統名非本機／專案／GitHub（例：雲端資料庫）同樣放行 | `HK::AskGateTest::test_irreversible_any_system_allowed` |
| AC-ASK-01c | `[IRREVERSIBLE]` 缺系統或原因 ⇒ 擋 | `HK::AskGateTest::test_irreversible_requires_fields` |
| AC-ASK-01d | `[COST]` 且 `billing=subscription_only` ⇒ 擋；`credits_fallback`／`api_key`／`unknown` 且 `預估：60 美元` ⇒ 放行；`預估：40 美元` ⇒ 擋 | `HK::AskGateTest::test_cost_by_billing_and_threshold` |
| AC-ASK-01e | `[K1]` 且含「須掌舵者親打」⇒ 放行；選項含「核准」⇒ 擋 | `HK::AskGateTest::test_k1_hint_only` |
| AC-ASK-01f | 任一類標籤＋詞表命中（例：`[IRREVERSIBLE] … 要不要 park`）⇒ 擋 | `HK::AskGateTest::test_lexicon_overrides_tag` |
| AC-ASK-01g | 舊類別標籤 `[BIZ]`／`[SECRET]`／`[VISUAL]`／`[HARNESS]`、無標籤 ⇒ 擋 | `HK::AskGateTest::test_retired_tags_blocked` |
| AC-ASK-01h | `AUTOSDD_UNATTENDED` ⇒ 任何問題擋 | `HK::AskGateTest::test_unattended_blocks_all` |
| AC-ASK-01i | 詞表只增不減（後設鎖：常數集合 ⊇ 本 TCS 列舉的 16 詞） | `HK::AskGateTest::test_lexicon_only_grows` |
| AC-ASK-02a | 推回文案先叫代決、列三類；不含「請您」「請手動」 | `PH::AutopilotWordingTest::test_pushback_prefers_self_decide` |
| AC-ASK-02b | 「真正需要您決定的類別」「以後要請您決定的只有這兩類」（逐字取自 sid 406454ea 2026-11-25）⇒ 不判交棒 | `PH::AutopilotWordingTest::test_rule_description_not_handoff` |
| AC-ASK-02c | 控制組：「需要您決定要不要推送」仍判交棒（判準未被放寬到失去鑑別力） | `PH::AutopilotWordingTest::test_real_handoff_still_caught` |
| AC-ASK-02d | 「先前 L2424 被分類器擋下」不當本場宣稱；「本回合 pre-push 擋下 3 項」仍判 | `CP::PastEventTest::test_past_event_not_claim` |

### 2.5 CI、舊視窗、圍籬

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-CI-01a | 三支真 run（45427135743、45439253352、45456241389）attempt 1 jobs JSON 錄製夾具 ⇒ `queue_timeout`；有步驟的 cancelled、14 分取消、同 ref 有較新 run ⇒ 不命中 | `CW::QueueTimeoutTest::test_classify_recorded_attempts` |
| AC-CI-01b | 命中 ⇒ 呼叫 `gh run rerun <id> --failed`（縫 `run`）、末行 `pass rerun=queue_timeout×1`；第 3 次 ⇒ `fail reason=queue_timeout_exhausted` rc 1 | `CW::QueueTimeoutTest::test_rerun_and_exhaustion` |
| AC-OW-01a | `oldwin.py`、`sessionctl_guard.py`、`qw_prompt.py` 全部使用者可見字串不含「請手動」「請您」（例外清單逐筆列名才准） | `OW::AutopilotTest::test_no_manual_wording` |
| AC-OW-01b | not_idle ⇒ 退避間隔 60·2^k、總時長到 12 小時才 `oldwin_retry_exhausted`；`MAX_RETRIES` 常數不存在 | `OW::AutopilotTest::test_exponential_backoff_12h` |
| AC-OW-01c | 舊視窗 Stop（已交棒且已 ack）⇒ `oldwin_idle_hint`＋60 秒後排程一次 | `OW::AutopilotTest::test_old_stop_triggers_check` |
| AC-OW-01d | `status=shell` 長時間不變 ⇒ 不終止 | `OW::AutopilotTest::test_shell_never_killed` |
| AC-FN-01a | 圍籬期間真痕跡目錄（tmp 模擬）新增一列帶 `%TEMP%`／`sc-*`／夾具 sid ⇒ 判洩漏；真系統同時段寫入的非夾具形列 ⇒ 不判 | runner 既有測試檔（WP-FENCE 現查）`::TraceFenceTest` |

## 3. 突變清單（MU；QA 逐條實打，每條至少一條 AT 轉紅，未轉紅＝補斷言）

| MU | 突變 | 應轉紅 |
|---|---|---|
| MU-QV-1 | 決策表第 3 列拿掉 `D ≤ QV_WAIT_RESET_MIN` 分支（一律 PARK） | AC-QV-01a |
| MU-QV-2 | 恢復兩序列鍵（raw 與 plan 各自觸發） | AC-QV-05a、AC-QV-01c |
| MU-QV-3 | `expires_at` 只取 `measured_at+TTL`（不取短窗 reset 的 min） | AC-QV-02a |
| MU-QV-4 | 恢復 halt 有效即不補量 | AC-QV-03a |
| MU-QV-5 | park 恢復接受 `--why` | AC-QV-04a |
| MU-QV-6 | 讀不到判決改回 `CONTINUE` | AC-QV-07a |
| MU-QV-7 | Stop 宣稱守衛不看 `expires_at` | AC-QV-06b |
| MU-AC-1 | reconcile 不比對 `account`（只看存在） | AC-AC-02a |
| MU-AC-2 | 舊格式標記一律保留 | AC-AC-02b |
| MU-AC-3 | 逐字稿觸發器不記 byte offset（每次全讀） | AC-AC-03b |
| MU-MG-1 | 略過已吸收改成不比 patch-id | AC-MG-01b |
| MU-MG-2 | 紅時仍 ff | AC-MG-01c |
| MU-MG-3 | 清理加 `--force` | AC-MG-01e |
| MU-MG-4 | 帳本不剝離到尾端 | AC-MG-01d |
| MU-G1-1 | 推送期基準改回 `HEAD` | AC-G1-01a |
| MU-G1-2 | 提交期恢復阻斷 | AC-G1-01b |
| MU-G1-3 | 拿掉 `CLAUDECODE` 判斷 | AC-G1-03a |
| MU-ASK-1 | 詞表檢查移到標籤檢查之後且標籤命中即放行 | AC-ASK-01f |
| MU-ASK-2 | `[COST]` 不讀 `billing` | AC-ASK-01d |
| MU-ASK-3 | 恢復舊五類標籤 | AC-ASK-01g |
| MU-ASK-4 | 推回判準拿掉「類別定義語」豁免 | AC-ASK-02b |
| MU-ASK-5 | 豁免放寬到「所有含『您』的句子」 | AC-ASK-02c |
| MU-CI-1 | 不檢查 `runner_name==""` | AC-CI-01a |
| MU-CI-2 | 重跑上限拿掉 | AC-CI-01b |
| MU-OW-1 | 退避改回固定 3 次 | AC-OW-01b |
| MU-FN-1 | 圍籬比對只看檔案大小不看列內容 | AC-FN-01a |

## 4. E2E 覆蓋表（一功能一列，不得遺漏；全部入帳 `docs/06_quality/RealVerify_Result_Ledger.md` 才算結）

| 功能 | E2E | 載具（真的是什麼） | realverify 案例 | 不可達部分與備援 |
|---|---|---|---|---|
| 單一判決（QV-01） | E2E-AP-QV-01 | 真逐字稿重放：sid 406454ea L2445～L2569＋`quota_burn` 20:50／03:43／03:46／04:00 四列＋halt 標記原檔，真跑 `sessionctl quota` 於兩個時刻（`now` 注入：03:46、09:21） | `RV-AP-QV01` | 無；斷言 03:46＝`WAIT_RESET win=04:00`、09:21＝`CONTINUE acct=eaf5241f6fe2`、無 halted 行 |
| 判決行與有效期（QV-02） | E2E-AP-QV-02 | 真 `claude -p`（沙盒 `AUTOSDD_QUOTA_CACHE_DIR`、`AUTOSDD_TRACE_DIR`）：先跑 `watch` 得判決、錄製重放推進讀數與時鐘超過 `expires_at`、再跑 `park` | `RV-AP-QV02` | 無；斷言 park 依新判決、痕跡 `stale_verdict_recomputed` |
| halt 不壓補量（QV-03） | E2E-AP-QV-03 | 真 `claude -p` 回合中跑 `--pace` 兩次（相隔 > TTL），錄製重放計數取數次數 | `RV-AP-QV03` | 無 |
| park 前置（QV-04） | E2E-AP-QV-04 | 真排程（沙盒命名空間、R-VER 隔離）：A＝`CONTINUE` 不產排程；B＝`--next-est` 放不下 ⇒ `AutoSDD_HandoffSpawn_*` 且 NextRunTime 非空，收尾撤銷 | `RV-AP-QV04` | macOS 走 launchd，憑證是 rc（既有 park 劃界） |
| watch 單序列（QV-05） | E2E-AP-QV-05 | 真 `sessionctl watch` 背景行程＋錄製重放（87%→0% 跨重置） | `RV-AP-QV05` | 無；斷言只觸發一次 `WAIT_RESET`、重置後不再觸發 |
| Stop 宣稱守衛（QV-06） | E2E-AP-QV-06 | 真 Stop hook 以逐字稿 406454ea 重放 | `RV-AP-QV06` | 無；斷言 L2564 回合出聲一次 |
| 失效方向與 billing（QV-07） | E2E-AP-QV-07 | 真 `sessionctl quota --json` 於三種錄製快取（缺 posture、無 credits、credits 可用） | `RV-AP-QV07` | 無 |
| LOC 純搬移（QV-08） | E2E-AP-QV-08 | 真 pre-push（合成 stdin）於搬移 commit 與前一 commit 各跑一次，leg 結果相同 | `RV-AP-QV08` | 無 |
| 標記帶帳號（AC-01） | E2E-AP-AC-01 | 真 `claude -p` 回合觸發 halt 寫入（錄製讀數 ≥ halt），讀真寫出的沙盒標記檔驗 `account` | `RV-AP-AC01` | 無 |
| 換帳號作廢（AC-02） | E2E-AP-AC-02 | 真 `claude -p`，沙盒 `CLAUDE_CONFIG_DIR` 內換一份憑證檔（觸發 mtime），錄製重放回兩帳號標頭；真 PostToolUse hook 下一次工具呼叫後落 `account_switch`、halt 作廢、`--pace` 首行為 QV | `RV-AP-AC02` | 不切換真帳號（不可、也不該）；以真憑證檔變化＋錄製標頭取代 |
| `/login` 觸發（AC-03） | E2E-AP-AC-03 | 逐字稿 406454ea L173～L210 重放，真 hook 讀增量 | `RV-AP-AC03` | 無；斷言 L210 時刻判決為新帳號 |
| 被動觀測（AC-04） | E2E-AP-AC-04 | 觀測型：每次 SessionStart 掃痕跡與逐字稿 `/login` 記錄配對 | `RV-AP-AC04-OBS` | 依掌舵者自然換帳號產生樣本；樣本 0 時照實記「未觀測」，不算 PASS，也不要求人額外操作 |
| 合入管線（MG-01） | E2E-AP-MG-01 | 真 git：repo 外拋棄式 clone 重建 W6／W11b2 兩分支（含已吸收提交與三提交帳本），真跑 `autopilot merge` | `RV-AP-MG01` | 全套以真 pre-push 的縮小 leg（拋棄式 repo 內只含 MG 測試）代表；完整 leg 對等由 E2E-AP-MG-02 證 |
| pre-push 對等（MG-02） | E2E-AP-MG-02 | 真 pre-push：合成 stdin 一次、對拋棄式 bare remote 真 `git push` 一次，比 leg 集合 | `RV-AP-MG02` | 無 |
| worktree 起點（WT-01） | E2E-AP-WT-01 | 真 `claude -p` 於拋棄式 repo（含一個未推送提交、`worktree.baseRef: "head"`）派 `isolation: "worktree"` 子代理執行 `git rev-parse HEAD~0`，斷言含該未推送提交 | `RV-AP-WT01` | 無 |
| 推送範圍棘輪（G1-01） | E2E-AP-G1-01 | 拋棄式 bare remote＋真 `git push` 觸發真 pre-push | `RV-AP-G101` | 無 |
| 推送閘與前綴推送（G1-02） | E2E-AP-G1-02 | 重建 HYG1 形狀（修 2＋登記 1）三提交，真 `autopilot push` 對 bare remote | `RV-AP-G102` | 無 |
| 逃生口對稱（G1-03） | E2E-AP-G1-03 | 真 `claude -p` 子行程內設 OFF 提交（拋棄式 repo）⇒ 棘輪照判；同指令在無 `CLAUDECODE` 的乾淨行程 ⇒ 放行 | `RV-AP-G103` | 無 |
| 詢問類別閘（ASK-01） | E2E-AP-ASK-01 | 真 PreToolUse hook（真 `sessionctl_guard.py` 經載具）以近 14 天 15 次真實提問重放＋三類各一筆合成正例；另一筆真 `claude -p` 回合讓模型真的呼叫 AskUserQuestion（可代決題）⇒ 被擋 | `RV-AP-ASK01` | 互動畫面顯示 block 理由不可程式目視：以 `claude -p` 的 stream 輸出與 hook 痕跡代替（同既有〔OI-20261120-010〕劃界） |
| 推回與宣稱守衛假紅（ASK-02） | E2E-AP-ASK-02 | 真 Stop hook 以 sid 406454ea 2026-11-25 兩次假推回回合重放 ⇒ 不推回；以近 14 天真實逐字稿全量重放（`tools/probe/handoff_census.py --midwork` 同母體）比較修前修後命中數，新增假紅 0 | `RV-AP-ASK02` | 無 |
| CI 排隊逾時（CI-01） | E2E-AP-CI-01 | `gh api` 錄製三支 run attempt 1／2 回應重放＋真 `ci_wait` 行程；另於下一次真推送被動觀測 | `RV-AP-CI01`、`RV-AP-CI01-OBS` | 外部現象可能消失：被動觀測 0 命中照實記錄（不算 FAIL、不算 PASS），錄製重放為主證 |
| 舊視窗（OW-01） | E2E-AP-OW-01 | 真行程替身（R-VER 替身）＋真排程重試鏈：替身維持 `status=shell` 2 次後轉閒置 ⇒ 第 3 次退避後關閉；全程痕跡無「請手動」 | `RV-AP-OW01` | 兩個真互動視窗不可自動化（harness UI）⇒ 以替身＋真排程驗到關閉動作前一刻；互動層列 APD §2 外部劃界 |
| 痕跡圍籬（FN-01） | E2E-AP-FN-01 | 真跑 `run_root_unittests.py`，搭一支故意洩漏的探針測試（紅綠自證：有探針 rc≠0、拿掉 rc 0） | `RV-AP-FN01` | 無 |

覆蓋檢查：§1 每個 REQ 在本表恰有至少一列（QV-01～08、AC-01～04、MG-01～02、WT-01、G1-01～03、ASK-01～02、CI-01、OW-01、FN-01，共 23 列）；不可達者皆有備援與劃界，不留任何未完成的真機項。

## 5. 跨檔鎖與收尾（CLOSE）

- 新測試檔三支（QV、MG、PS）⇒ c1c2 重釘、`_TREE_FILE_FLOORS`、skip 普查、`MIN_TESTS`＋ONBOARDING 同步，由 CLOSE 一次做（並行包只回報建議值）。
- CI paths：compat-ci 兩支加 `tools/lib/autopilot/**`、`tools/autopilot.py`、`tools/lib/model_window_table.py`；`non_evolvable_globs` 同。
- SSOT §3：「autopilot＋QuotaVerdict」預告列改反引號登記（檔案存在後）。
- 根 CLAUDE.md：守衛面清單加 `tools/lib/model_window_table.py`；現查表加 `sessionctl quota`、`autopilot merge／push`；〈換 session 的 SOP〉`park --why` → `--next-est`；機械守衛總表 `sessionctl_guard.py` 列補 PreToolUse／AskUserQuestion。
- 本 TCS 的 realverify 案例 id 登記於 `docs/06_quality/RealVerify_Protocol/cases.json`。
