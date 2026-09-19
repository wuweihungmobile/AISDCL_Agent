# CrossPlatform R145 — DEF-200-275 第六輪四方複審 REJECT→D17～D25 修復→修後複審 APPROVE；DEF-200-279／280 結案、DEF-200-283 新立：護欄層淨額記帳

- **輪籤**：R145（2026-09-12，macOS；主控 Fable 5.1 只裁決，Architect／SA／SD／QA 四方複審與 Dev-A～D／A2／D2／Trim 修復包皆 Sonnet 5 並行子 agent，
  主控收尾單人窗口 commit）。
- **體例**：不使用前瞻輪號句型；數字皆主控親跑（`--print-guard-lines`）或各包 `[他包回報]` 標記。
- **上承**：R144（DEF-200-275 第五輪＋DEF-200-281／282 收尾，見 `CrossPlatform_R144_Scan_Findings.md`）。
  本輪非開新一輪 CrossPlatform 掃描輪四件套，僅為 DEF-200-275 第六輪四方複審收斂（掌舵者三問：新視窗被擋／不用真實數據／
  數字與 /context 不符）＋ DEF-200-279／280 結案＋ DEF-200-283 新立附帶的護欄層淨額記帳延伸。

---

## §1 護欄層淨額承認

<!-- guard-total:R145 --> R145 護欄層累積淨額＝ 97488 → 98236（+748＝+48 test_adr_xplat001_c1c2_lock＋18 test_check_hooks_liveness＋79 test_claim_provenance_r86＋48 test_context_budget_guard＋215 test_root_guard_known_model_r145＋141 test_sentinel_tick_e2e_r145＋199 test_wake_chain_halt_r278；分軌＝回歸鎖軌 392〔含本檔記帳 48〕＋功能軌 356〔兩支新判準能力鎖檔〕，回歸鎖軌超上限 309 走 `_REGRESSION_LANE_APPROVED_OVERAGE`、功能軌熄滅款(11)[只升不降] 走 `_REPIN_APPROVED_ROUND_OVERAGE` 第三格〔上限 2→3〕，皆四方記帳複審核准，見 §3）——
逐項見下方 §2；證據見 `docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md`〈第六輪〉節；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-275／DEF-200-279／DEF-200-280／DEF-200-283。此附記為 doc-total 對帳（≥2 站點）
另一站點寄居 `AutoSDD_improving_112.md`，同 R129～R144 寄居體例。round-label-ok

## §2 逐檔清單

| 檔 | 前 | 後 | 淨額 | 歸類 |
|---|---|---|---|---|
| `test_adr_xplat001_c1c2_lock.py` | 7855 | 7903 | +48 | 回歸鎖軌（記帳誠實度：主表 R145 列、到期兌現列 (145, 543)、重新武裝註解、軌表列、兩張名冊列、MAX_ENTRIES 上修註解、前綴鏈列） |
| `test_check_hooks_liveness.py` | 3296 | 3314 | +18 | 回歸鎖軌（D20 sdd_hook_router matcher 含 Agent／Workflow 正面斷言） |
| `test_claim_provenance_r86.py` | 936 | 1015 | +79 | 回歸鎖軌（D24 佐證窗口本回合＋前一回合） |
| `test_context_budget_guard.py` | 11861 | 11909 | +48 | 回歸鎖軌（D21 查表收斂佈線＋D22 原子 latch 儲存） |
| `test_root_guard_known_model_r145.py` | 0 | 215 | +215 | **功能軌**（新檔；D21 根層 known_model 查表收斂三階＋fail-open stderr——全新判準能力，同 R135 D15 判例；Architect 記帳複審指名） |
| `test_sentinel_tick_e2e_r145.py` | 0 | 141 | +141 | **功能軌**（新檔；D23 _sentinel_tick 端到端消費 halt 標記——Dev-C 自陳對修前碼亦綠＝覆蓋補強非結案證據；Architect 記帳複審指名） |
| `test_wake_chain_halt_r278.py` | 492 | 691 | +199 | 回歸鎖軌（D22 prepare 閂鎖鍵補 sid／原子 latch＋D23 halt 顯示、relay 空 session_id 體檢） |

SDD 子專案側（`AISDLC_SDD/AISDLC_SDD_v0.30/`）的 hook／runtime／測試改動（D17～D19／SA-04／D25／ARCH-R6-01 修復／chaos 舊債補修、
新檔 `test_settings_matcher_r145.py`／`test_escalation_provenance_r6.py`）計入該子專案自身的 LOC 政策，不落本檔棘輪射程；逐檔見證據檔
〈第六輪〉§修法逐檔與§複審修復波。

## §3 分軌申報與一次性例外（四方記帳複審核准紀錄）

- 本輪 tools/tests 淨額 +748 分軌申報：**回歸鎖軌 392**（`_REGRESSION_LANE_LOG` R145 列＝結案回歸鎖 `test_wake_chain_halt_r278`
  +199／`test_claim_provenance_r86` +79／`test_context_budget_guard` +48／`test_check_hooks_liveness` +18＋本檔自身記帳 +48）、
  **功能軌 356**（`test_root_guard_known_model_r145.py` 215＋`test_sentinel_tick_e2e_r145.py` 141——Architect 記帳複審指名：前者是
  根層全新查表收斂能力（同 R135 D15「新判準＝功能軌」判例），後者 Dev-C 自陳對修前碼亦綠、屬覆蓋補強非結案證據）。主控初版曾
  「全額 733 歸回歸鎖軌」，被 Architect 以「客觀效果是悄悄熄滅為此而設的 [只升不降] 警報」駁回，改為現行誠實分法。
- 回歸鎖軌 392 > 上限 309：Dev-Trim 已搬 87 行史料進證據檔（不砍 assert／夾具／邏輯下的可搬遷上限，[他包回報]）仍超額 ⇒
  `_REGRESSION_LANE_APPROVED_OVERAGE["R145"] = (392, …)`（此前空表，MAX_ENTRIES=1 未動）。
- 功能軌 356 > 0 ⇒ R143／R144／R145 連續三輪正成長觸發款(11) `[只升不降]`；合法出口＝本輪淨減法（刪／合併等量舊鎖檔，需另開淨減法輪）
  或主表名冊 ⇒ `_REPIN_APPROVED_ROUND_OVERAGE["R145"] = (356, …)`，名冊已滿（R101／R129）故 `MAX_ENTRIES` **2→3 可見上修**
  （`test_the_registry_stays_a_one_time_exception` 先紅逼出；理由欄誠實寫明「本筆熄滅的是 [只升不降]」；理論下限 0，下一次淨減法輪落地
  時應下修並移除失效列）。`net_cap_for_round()`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`／`lane_split_problems()`／
  `_REGRESSION_LANE_ROUND_CAP` 判準邏輯與門檻數字本輪一個字未動（SD 逐 hunk 核實）。
- 到期義務兌現：`_REPIN_NET_CAP_SCHEDULE` 加 `(145, 543)`（cap 544→543），同輪重新武裝 `_REPIN_NET_CAP_DUE_ROUND=147`／
  `_REPIN_NET_CAP_DUE_TARGET=542`；凍結前綴鏈 `_FROZEN_PREFIX_REWRITE_LEDGER` 接一列（846054db5d7e→現值，DEF-200-275）。
- `prose` 分桶 4182→4512（+330）：兩支新檔 docstring 的指針字面使整檔依 `BUCKET_PRIORITY` 落 prose 桶（歸桶副作用；另一出口＝拔掉
  指針改落 guard_self，同為 shrink-only，成長只會換桶）。`_TREE_FILE_FLOORS` `tools/tests` 56→58、LATEST fsm tests 62→64。

### §3.1 四方記帳複審判決（皆 Sonnet 5、唯讀；對初版「全額 733 回歸鎖軌」版本審）

| 方 | overall | 要點 |
|---|---|---|
| SD | **APPROVE**（六項全過） | 逐 hunk 核實六個判準函式零改動；方向鎖（cap 只降、floor 只升、MAX_ENTRIES 未預先放寬、since 未追溯）成立；名冊使用落在款 4 自己宣告的第二出口，形狀與 R101／R129 先例同形；算術 215+141+199+18+79+48+33=733 與 `--print-guard-lines` 對帳 |
| SA | **APPROVE** | 逐檔前／後值 vs `git show HEAD` 逐字相符；`_FROZEN_GUARD_LINES` 求和 98221＝`GLC_LINES`；兩站點標記行逐字元相同；prose 4512 為現量測值；Dev-Trim 87 行史料已核實貼入證據檔（302 行逐字相同）；DEF-200-279 狀態欄已誠實揭露「track_id 接線另案」非過度宣稱；三支帳本鎖 rc=0 |
| QA | **APPROVE** | 獨立重算 +733 逐檔相符；反向注入自證：刪名冊 R145 格 ⇒ `[回歸鎖軌超上限] …+733 超過上限 309` 真紅；刪 `(145, 543)` 列 ⇒ `[到期未下修] …仍是 544、高於到期目標 542` 真紅——守衛仍有牙 |
| Architect | **REJECT（部分：(b) 申報寬度）** | (a)(c)(d) APPROVE；(b) 356 行（root_guard_known_model 215＋sentinel_tick_e2e 141）依框架定義與 R135 判例應歸功能軌，「全額回歸鎖軌」的客觀效果是熄滅 [只升不降] 警報；替代方案＝回歸鎖軌 377（＋記帳）、功能軌 356 走主表名冊同型一次性例外並誠實寫明理由 |

**收尾窗口處置**：採 Architect 替代方案（見上 §3 現行分法：392／356、兩張名冊、MAX_ENTRIES 2→3）；修正後請 Architect 快速複核 diff
（判決見下 §3.2）。

### §3.2 Architect 修正後複核

> Architect 複核（修正版）：**APPROVE**。392／356 分法誠實（§3.1 原 REJECT 理由已被此分法解決：移出的正是抽查標記的兩支檔；392＝377＋本檔自身因第二張名冊列與 `MAX_ENTRIES` 註解多長的 15 行，同 R131～R135「本檔自身漂移全額歸本軌」慣例）；主表名冊第三格與 `MAX_ENTRIES` 2→3 對照 R101／R129 先例合規（指名輪號＋精確淨額＋≥20 字理由、理由誠實寫明熄滅款(11)、上修為可見一次性動作且承諾下限 0）；SD 所稱「六個判準函式零改動」核實屬實；實測 `Ran 192 tests OK`／`GLC_LINES=98236`／淨額 +0（重跑一度受同機背景 `run_root_unittests.py` 行程的 `_zzz_*` 暫存鎖檔干擾——同型於「並行 agent 透過測試副作用互蓋」教訓，該行程結束後重跑乾淨）。可 commit。[他包回報]

## §4 本輪摘要

詳見 `CrossPlatform_DEF200275_Context_Metering_Evidence.md`〈第六輪〉：觸發（掌舵者三問原話）、四方判決表（4/4 REJECT）、裁決 D17～D26、
修法逐檔（Dev-A／B／C／D）、修後複審（Architect／SA／QA REJECT、SD APPROVE；阻斷 ARCH-R6-01／SA-F2／QA-R6-01）、複審修復波
（Dev-A2／Dev-D2）、迷你複審（Architect／SA 皆 APPROVE）、實測、把握程度、未做事項（含掌舵者「這個我要如何解決」四項）。

## §5 未做事項（另案）

- D26 Models API 種子值刷新需 `ANTHROPIC_API_KEY`（SOP 見證據檔〈未做事項〉第 1 項）。
- Windows 真機驗證（push 後看 `windows-compat-ci`；exec form 載具／schtasks／O_EXCL 於 NTFS／`psutil` 分支）。
- DEF-200-279 的「刻意並行多 track」情境（`FSMRuntime.bootstrap(track_id=…)` 接線既有 `load_track_state`）需 mini-ADR 定範圍。
- `record_escalation()` 直寫 `current` 使 decision_trace `from` 欄對 6 個站點成為 ESCALATION 自迴圈（Architect 迷你複審 P3，既有行為擴大，
  現有兩個消費者只看 `to`）。
- `state_loader.save_state()` 併發 `.bak` 輪替 FileNotFoundError 被既有 try/except 吞（SD-RR-01，P2 非阻斷）。
- `endurance_env.trace_dir()` 唯讀路徑仍會 mkdir 的同型風險（Dev-C 只在 planner 內繞開）。
- LOC 餘裕：`quota_gate.py` 499/500、`session_resume_planner.py` 750/750、`context_budget_guard.py` 1089/1089。

## 第七輪附記（R146；DEF-200-275 第七輪收尾單人窗口 Dev-C7）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為 DEF-200-275 第七輪（package A／B 修復＋Dev-Trim7 散文搬遷）
  造成的護欄層逐檔漂移收斂記帳，寄居本檔（同 R141～R145「單一缺陷收尾附帶記帳」寄居體例，不另開新檔）。

<!-- guard-total:R146 --> R146 護欄層累積淨額＝ 98236 → 98195（-41＝-25 前段＋（本輪續）-16 DEF-200-287／288 收尾；-25 分解＝-40 主表 15 檔逐檔漂移＋15 本檔自身（test_adr_xplat001_c1c2_lock.py）自含式漂移；[淨減法輪]，不受款(9)`[未附刪除清單]` 約束）——
成因：package A（D27 根層 context_budget_guard.py 補查表收斂⑥階＋`tools/lib/sdd_latest.py` per-session 快取）／
package B（D28 SDD telemetry writeback 守衛，v0.30 三支 hook＋fsm_runtime.py＋新檔
`test_rule_telemetry_requires_hook_r7.py`〔屬 AISDLC_SDD 子專案自身 LOC 政策，不落本檔棘輪射程〕）對
`test_context_window_parity.py`／`test_context_budget_guard.py`／`test_root_guard_known_model_r145.py` 的合法新增，
加上 Dev-Trim7 十二支既有測試檔 docstring／模組頂端敘事搬遷抵銷（原文逐字保全於
`CrossPlatform_DEF200275_Context_Metering_Evidence.md`〈第七輪 史料搬遷（Dev-Trim7）〉節）。
逐項見下表；證據見 `docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md`〈第七輪〉節；
缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-275／DEF-200-284／DEF-200-285／DEF-200-286。
此附記為 doc-total 對帳（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，同 R129～R145 寄居體例。round-label-ok

| 檔 | 前 | 後 | 淨額 |
|---|---|---|---|
| `test_block_destructive_git_r83.py` | 2288 | 2285 | -3 |
| `test_context_budget_guard.py` | 11909 | 11950 | +41 |
| `test_context_window_parity.py` | 145 | 229 | +84 |
| `test_dev_start_ps1_lastexitcode.py` | 548 | 521 | -27 |
| `test_doc_env_prefix_platform_parity_r60.py` | 340 | 331 | -9 |
| `test_doc_loc_baseline_freshness_r60.py` | 7155 | 7145 | -10 |
| `test_gha_action_versions.py` | 703 | 681 | -22 |
| `test_no_invalid_escape_sequences.py` | 339 | 315 | -24 |
| `test_ntfs_trailing_space_device_name.py` | 760 | 759 | -1 |
| `test_platform_utils_dedup.py` | 1112 | 1078 | -34 |
| `test_root_guard_known_model_r145.py` | 215 | 227 | +12 |
| `test_sanitize_component_frozen_sdd_versions_lock.py` | 340 | 317 | -23 |
| `test_skip_discoverability_r83.py` | 744 | 742 | -2 |
| `test_smoke_ci_sync.py` | 1399 | 1397 | -2 |
| `test_windowsapps_guard_bash_parity.py` | 973 | 953 | -20 |
| `test_adr_xplat001_c1c2_lock.py`（本檔自身，自含式） | 7903 | 7918 | +15 |

主表 15 檔合計 -40；加上本檔自身自含式漂移 +15（`_GUARD_LINES_REPIN_LOG` 新增本輪兩列＋`_REPIN_LOG_FROZEN_PREFIX_LEN`
172→174＋`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列，反覆覆核收斂至此），本輪總淨額 -25。淨額為負，`repin_log_problems()`
款(9) `[未附刪除清單]` 僅在淨額為正時判定，本輪不觸發；`repin_growth_problems()` 款(11) `[只升不降]` 的連續正成長計數
因本輪淨額 ≤0 而歸零（R143～R145 三輪連續正成長已結束）。

### 第七輪附記續（R146 續；Dev-D8 收尾單人窗口，2026-09-12）

**體例**：延續上段同一輪（R146）記帳，非開新一輪。承接上表終點 98211，收尾 DEF-200-287（windows-compat-ci
#220／#221 Windows 稽核帳本檔案鎖競態，三棒修復 D31／D31b／D31c；三輪複審 W／C REJECT→C APPROVE／W REJECT
（W-4 P0）→W／C 皆 APPROVE，C-1 P3 登記不修）與 DEF-200-288（status line harness 進料，D32／D32b 兩棒；
兩鏡首輪 REJECT→S8b 全修→final:architect／qa 兩鏡最終複審皆 APPROVE，各登記 P2 不修）造成的逐檔漂移收斂，
詳見證據檔〈第七輪追加 A／B〉節。

| 檔 | 前 | 後 | 淨額 |
|---|---|---|---|
| `test_archive_defect_log.py` | 3839 | 3767 | -72 |
| `test_bash32_compat.py` | 1020 | 985 | -35 |
| `test_bash_probe_spec_contract.py` | 867 | 859 | -8 |
| `test_check_hooks_liveness.py` | 3314 | 3397 | +83 |
| `test_check_script_parity.py` | 2098 | 2051 | -47 |
| `test_check_wrapper_thinness.py` | 1234 | 1185 | -49 |
| `test_context_budget_guard.py` | 11950 | 12160 | +210 |
| `test_context_window_parity.py` | 229 | 281 | +52 |
| `test_find_git_bash_parity.py` | 1326 | 1306 | -20 |
| `test_install_windows_nightly.py` | 1385 | 1347 | -38 |
| `test_negative_existence_claims_r82.py` | 380 | 370 | -10 |
| `test_platform_neutral_paths.py` | 5762 | 5781 | +19 |
| `test_pre_commit_dispatcher_sigpipe.py` | 964 | 936 | -28 |
| `test_ps_engine_ssot.py` | 960 | 905 | -55 |
| `test_run_root_unittests.py` | 3716 | 3648 | -68 |
| `test_subprocess_encoding_hygiene.py` | 1609 | 1582 | -27 |
| `test_windows_forbidden_filename_parity.py` | 1025 | 1003 | -22 |
| `test_windowsapps_guard_cross_consistency.py` | 2183 | 2051 | -132 |
| `test_workflow_permission_concurrency_lock.py` | 1417 | 1406 | -11 |
| `test_statusline_context_feed.py`（新檔，D32／D32b 功能軌鎖檔） | 0 | 204 | +204 |
| `test_adr_xplat001_c1c2_lock.py`（本檔自身，自含式） | 7918 | 7956 | +38 |

上列 19 支既有檔（Dev-Trim8 十五支散文搬遷抵銷＋D31／D32 系列回歸鎖擴充）合計 -258；加上新檔
`test_statusline_context_feed.py` +204（功能軌，D32 status line harness 進料鎖檔）；加上本檔自身自含式
漂移 +38（本節新增 `_GUARD_LINES_REPIN_LOG` 本輪續多列＋`_FROZEN_GUARD_LINES` 兩次更新＋
`_REPIN_LOG_FROZEN_PREFIX_LEN` 174→181＋`_REPIN_LOG_HISTORY_SHA256` 重釘＋`_FROZEN_PREFIX_REWRITE_LEDGER`
接鏈列，反覆覆核收斂至此）。三者合計 -258+204+38 = -16，本輪續總淨額 -16（98211 → 98195）。分軌：
功能軌＝`test_statusline_context_feed.py`＋`test_context_budget_guard.py` 的 `HarnessFeedStageTest`＋
`test_context_window_parity.py` 的 `HarnessStageParityTest`；回歸鎖軌＝`test_check_hooks_liveness.py` 的
`TestConversationLedgerChildTimeoutParity`（DEF-200-287 W-3）；不使用任何例外配額（`_REGRESSION_LANE_APPROVED_OVERAGE`／
`_REPIN_APPROVED_ROUND_OVERAGE` 皆未動）。累計本輪（R146 前段＋續）總淨額 98236 → 98195（-41）。

## 第九輪附記（R147；DEF-200-274 第九輪收尾單人窗口）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為 DEF-200-274 第九輪（預設自動多核心＋LPT＋
  自動細分＋不均偵測 v2＋SIGTERM 清理＋P1 zshrc 假紅根治＋AutoClaude／AISDLC_SDD 接 pytest-xdist）造成的
  護欄層逐檔漂移收斂記帳，寄居本檔（同 R141～R146「單一缺陷收尾附帶記帳」寄居體例，不另開新檔）。

<!-- guard-total:R147 --> R147 護欄層累積淨額＝ 98195 → 98943（+748）——內容成長 +638（`test_run_root_unittests.py`
3648→4258 ＋610：`ShouldRunParallelDecisionTest`／`RunWithFloorNeverParallelizesSyntheticTreeTest`／
`_zero_dep_child_env()`＋`ZeroDepProbeForcesSequentialChildEnvTest`＝P1/P0 zshrc 假紅根治回歸鎖 119 行；
`ParallelTimingCacheLoadHintsTest`（快取壞檔容錯＋bool 誤判計時回歸）／`ParallelShardSigtermCleanupTest`／
`ParallelShardSigtermIgnoredOffMainThreadTest`＝既有缺陷修復回歸鎖 151 行；LPT 排序／保存／過期回報／
大批持久化＋自動細分＋不均偵測 v2＋worker 數印出＋既有 cap 8→9 調整＝功能軌 340 行；同輪追加：主控 CI
複驗修正 4258→4268 ＋10（Windows 上 SIGTERM 測試改為不自殺的平台分支＋CI 多印 `::warning::` 的計數
修正，功能軌）；`test_pre_push_dispatcher.py` 686→704 ＋18：compileall 遷移語法偵測回歸鎖，功能軌）＋
本檔（`test_adr_xplat001_c1c2_lock.py`）自身逐檔漂移收斂 +110（`_GUARD_LINES_REPIN_LOG` 本輪多列＋
`_FROZEN_GUARD_LINES` 反覆更新＋`_REGRESSION_LANE_LOG` 新列＋`_REPIN_NET_CAP_SCHEDULE` 到期兌現
（cap 543→542）與重新武裝＋`_PHASE2_REVIEW_LOG` 新列＋U9 具名展延 147→152＋
`_REPIN_LOG_FROZEN_PREFIX_LEN` 181→204＋`_REPIN_LOG_HISTORY_SHA256`／`_FROZEN_PREFIX_REWRITE_LEDGER`
重釘＋E501 存量債棘輪折行，反覆覆核收斂至此）。分軌：回歸鎖軌 270（119+151，全額歸本軌，未使用任何一次
性例外名冊）＋功能軌餘額 478（＝內容成長 368〔340+18+10〕＋本檔自身記帳漂移 110，本輪刻意不把自身記帳
漂移歸入回歸鎖軌以保留回歸鎖軌 cap 309 的餘裕），皆未超各自上限（回歸鎖軌 cap 309／功能軌 cap 542）。
詳細背景複審發現、設計裁決與逐項驗證數字見
`docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第九輪〉節；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274。

## 第十輪附記（R148；DEF-200-274 第十輪收尾單人窗口）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為 DEF-200-274 第十輪（四方獨立審查第九輪
  產出＋5 包並行修復＋收尾單人窗口收斂）造成的護欄層逐檔漂移收斂記帳，寄居本檔（同 R129～R147
  「單一缺陷收尾附帶記帳」寄居體例，不另開新檔）。

<!-- guard-total:R148 --> R148 護欄層累積淨額＝ 98943 → 99419（+476）——內容成長 +407，逐檔：
`test_run_root_unittests.py` 4268→4443（+175：D2 兩支平行回歸鎖 `RunParallelStalenessAdvisoryCiSymmetryTest`／
`ParallelMergeResultSkipCensusParityTest`，驗 staleness advisory 與既有 dispatch_imbalance 的 CI
`::warning::` 對稱、以及 `merge_results()` 重建的 skip 語意與序列真跑一致）；
`test_doc_loc_baseline_freshness_r60.py` 7145→7206（+61：D1 把 139.9s 單一測試方法拆成 Darwin／Linux／
Win32 三個具名平台子類別＋一支類別集合一致性回歸鎖，讓 `dispatch_granularity` 的類別級白名單能各自
分開派工）；`test_wake_chain_halt_r278.py` 691→727（+36：包 C 三支近界回歸鎖，驗
`HALT_MARKER_ACTIVITY_SKEW_SECONDS=10` 容忍窗的邊界內／邊界外／恰等三案）；新檔
`test_ci_gate_xdist_allowlist.py`（0→121：修 2 鎖住 `ci-gate.sh` 的 `XDIST_ARGS` 判準必須是允許清單
`VER == LATEST`、姊妹段落 `scripts/tests/` 呼叫恆帶 xdist，原生於 `AISDLC_SDD/scripts/tests/`、因該樹是
ONBOARDING 指紋樹而遷入本樹，同 D32 status line 先例）。四者皆回歸鎖軌，全額計入，非淨減法輪，
已補 `_REGRESSION_LANE_LOG` R148 列 393（分軌申報，見 `lane_split_problems()`）；淨額 393 超過
軌上限 309，四方獨立審查核准一次性例外（`_REGRESSION_LANE_APPROVED_OVERAGE` 新增 R148 列，
`_REGRESSION_LANE_APPROVED_OVERAGE_MAX_ENTRIES` 1→2，同 R145 判例：一次性收斂優於放寬上限
本體或虛報分類）。另 +11 全套第三次驗證跑時四方複審再發現：`test_doc_loc_baseline_freshness_r60.py`
的 `python_symbol_index()`／`collect_symbol_claims()` 對 `glob()` 快照後才 `read_text()`，D1 拆分後
平台模擬類別數增加、與 `LoadBalancingRegressionTest` 平行寫刪合成檔的既有競態暴露機率上升，補
`try/except FileNotFoundError` 兩處硬化（全額歸功能軌，非回歸鎖，`test_doc_loc_baseline_freshness_r60.py`
7206→7217）。另 +3 全套第四次驗證跑時四方複審再發現：`TestR81GhostPathClaims._FLIP_PROBE` 是固定
檔名，D1 拆分後多個平行 worker 行程各自跑一次 sibling suite 時互撞對方的建檔／刪檔；改帶
`os.getpid()` 隔離（同 `LoadBalancingRegressionTest` 既有慣例，全額歸功能軌，
`test_doc_loc_baseline_freshness_r60.py` 7217→7220）。
另 +69 本檔（`test_adr_xplat001_c1c2_lock.py`）自身逐檔漂移收斂（主表新增列＋本軌新增列＋
`_FROZEN_PREFIX_REWRITE_LEDGER` 追加列＋`_REGRESSION_LANE_LOG` 追加列＋
`_REGRESSION_LANE_APPROVED_OVERAGE` 追加列＋逐列補 CrossPlatform 逐檔清單指標所造成的行數漂移，
`--print-guard-lines` 反覆覆核收斂到本行本身也計入為止，同既有體例；凍結前綴
`_REPIN_LOG_FROZEN_PREFIX_LEN` 204→213、`_REPIN_LOG_HISTORY_SHA256`／`_FROZEN_PREFIX_REWRITE_LEDGER`
同步重釘）——DEF-200-274 第十輪：
掌舵者要求四方獨立審查（Architect／SA／SD／QA，各自不共享上下文分別跑）覆核第九輪 24 條發現，19 條
成立、5 條駁回、1 條未驗；其中 SA-04（`halt_verdict()` 判「標記過期」用零容忍嚴格比較，hook 落盤 `at`
與逐字稿真實 mtime 之間天生的毫秒級時序雜訊會被誤判成「已續跑」，commit c4a7e00 當輪只把測試治具的
mtime 撥早規避現象、生產碼本身未動）、SD-06（種子過期 advisory 與既有 `dispatch_imbalance` 的
`::warning::` 待遇不對稱）、SD-02／SA-01（139.9s 單一測試方法過長、無法被 `dispatch_granularity` 類別級
白名單再細分）三項判定為需修復的真缺陷；5 包並行修復：包 A（CI workflow perf-baseline／pg-e2e／
nightly-full 的 xdist 開關调整）、包 B（`ci-gate.sh` xdist 判準排除清單改允許清單，因 `_atomic_write_text`
競態修法僅存在於 LATEST、中間歷史版依規則不可原地補）、包 C（`HALT_MARKER_ACTIVITY_SKEW_SECONDS=10`
生產面根治＋三支近界回歸鎖）、D1（139.9s 測試拆三平台具名子類別）、D2（staleness advisory CI
`::warning::` 對稱化＋`merge_results()` skip 語意平行回歸鎖）→ 四方複審 3 APPROVE／1 REJECT（一次性例外
未逐字附刪除清單，退回補正）→ 收尾單人窗口修復收斂、SD／QA 二審 APPROVE。誠實劃界：Windows／macOS
物理機親驗待補；本輪修復的自動細分候選層在真實全套從未被觸發過（本機 9／CI 3／2 worker 皆不達公平
份額門檻）；跨 leg CPU 預算協調層缺口（DEF-200-289）與 root-infra-ci nightly-full 新鮮度守衛只判天數、
不判待驗變更是否已被涵蓋（DEF-200-290）留為未結項。詳細背景複審發現、設計裁決與逐項驗證數字見
`docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第十輪〉節；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274／DEF-200-289／DEF-200-290。

## 第十一輪附記（R149；DEF-200-293/294/295 root-infra 收尾）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為 DEF-200-293／294／295 三筆
  root-infra leg 缺陷收尾造成的護欄層逐檔漂移記帳，寄居本檔（同 R129～R148「單一缺陷收尾
  附帶記帳」寄居體例，不另開新檔）。

<!-- guard-total:R149 --> R149 護欄層累積淨額＝ 99419 → 99726（+307）——內容成長 +277：
`test_pre_push_dispatcher.py` 704→981（DEF-200-293 census 通道改餵檔案路徑非 stdin／
DEF-200-294 AutoClaude 子 hook 直譯器候選鏈根層優先＋健康探針／DEF-200-295 `--dist
loadgroup` 判準改問 SSOT 三筆缺陷的回歸鎖與 fake-repo stub：`_autoclaude_leg_stub`／
`_census_stub` 兩支專屬 stub＋`TestAutoClaudeSubHookInterpreterChain`（4 測試）／
`TestAutoClaudeSubHookPytestDistDecision`（4 測試）兩個純文字判準測試類別＋兩支 fake-repo
整合測試，含 E501 存量債棘輪折行 +29）；另 +30 本檔（`test_adr_xplat001_c1c2_lock.py`）
自身逐檔漂移收斂（主表新增列＋`_FROZEN_PREFIX_REWRITE_LEDGER` 追加列所造成的行數漂移，
`--print-guard-lines` 反覆覆核收斂到本行本身也計入為止，同既有體例；凍結前綴
`_REPIN_LOG_FROZEN_PREFIX_LEN` 維持 217（本輪新增列全部涵蓋在內）、
`_REPIN_LOG_HISTORY_SHA256`／`_FROZEN_PREFIX_REWRITE_LEDGER` 同步重釘）。全額歸回歸鎖軌
（`_REGRESSION_LANE_LOG` R149 列 307，未超軌上限 309，未使用任何一次性例外名冊）；
款(12) 到期義務同輪兌現（`_REPIN_NET_CAP_SCHEDULE` 追加 `(149, 541)`，
重新武裝 `_REPIN_NET_CAP_DUE_ROUND=151`／`_REPIN_NET_CAP_DUE_TARGET=540`）。逐項見
`tools/tests/test_pre_push_dispatcher.py`；缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md`
DEF-200-293／DEF-200-294／DEF-200-295。此附記為 doc-total 對帳（≥2 站點）另一站點寄居
`AutoSDD_improving_112.md`，同 R129～R148 寄居體例。round-label-ok

## 第十二輪附記（R150；DEF-200-297／298／299／300 單一 .venv 收斂＋perf 跨環境 provenance 收尾）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為四筆缺陷收尾造成的護欄層逐檔漂移
  記帳，寄居本檔（同 R129～R149「單一缺陷收尾附帶記帳」寄居體例，不另開新檔）。

<!-- guard-total:R150 --> R150 護欄層累積淨額＝ 99726 → 99845（+119）——內容成長 +99：
`test_pre_push_dispatcher.py` 981→1016（+35，DEF-200-297：兩支子 hook 候選鏈**零**子專案 venv
候選的文字鎖＋根 dispatcher ruff 候選不含 `AutoClaude/.venv` 鎖＋修復前 fallback 片段反向自證）／
`test_dev_start.py` 6529→6576（+47，DEF-200-297：`TestStrayVenvScan` 4 測試——`pyvenv.cfg` 標記偵測、
根 `.venv`／`.venv-cache-*` 排除、平台對應刪除指令、`%TEMP%` cleanvenv 殘留）／
`test_context_budget_guard.py` 12160→12177（+17，DEF-200-299：`claim_once` 以 `os.utime` 構造 age<0
的確定性測試）；另 +20 本檔（`test_adr_xplat001_c1c2_lock.py`）自身逐檔漂移收斂（主表新增列＋
`_REGRESSION_LANE_LOG`／`_FROZEN_PREFIX_REWRITE_LEDGER` 追加列，凍結前綴
`_REPIN_LOG_FROZEN_PREFIX_LEN` 217→219、`_REPIN_LOG_HISTORY_SHA256` 同步重釘）。全額歸回歸鎖軌
（`_REGRESSION_LANE_LOG` R150 列 119，未超軌上限 309，未使用任何一次性例外名冊）。DEF-200-298
（perf 基線跨環境比對降 advisory）／DEF-200-300（toml 寫出 CRLF）的修復全在 AutoClaude 側
（`tools/perf_regression_check.py`／`tools/perf_baseline_lock.py`／`autoclaude/utils/perf_baseline.py`／
`.perf_baseline.toml`／ADR-SD08-003 v1.2），不計護欄層。缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md`
DEF-200-297／DEF-200-298／DEF-200-299／DEF-200-300。此附記為 doc-total 對帳（≥2 站點）另一站點寄居
`AutoSDD_improving_112.md`，同 R129～R149 寄居體例。round-label-ok

## 第十三輪附記（R151；DEF-200-301～306 單一 .venv 徹底收斂＋nightly 12 連紅死結解除收尾）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為六筆缺陷收尾造成的護欄層逐檔漂移
  記帳，寄居本檔（同 R129～R150 寄居體例，不另開新檔）。本輪為**淨減法輪**（款(11) 連兩輪上升後
  的第三輪必須 ≤0，本輪兌現），並同輪兌現 cap 到期義務 541→540、重新武裝下一段 153／539。

<!-- guard-total:R151 --> R151 護欄層累積淨額＝ 99845 → 99812（-33）——內容成長：兩支新鎖檔
`test_single_venv_identity.py`（DEF-200-301 hook 載具單一 .venv 身分鎖）／`test_clean_venv_carrier.py`
（DEF-200-306 乾淨 venv 載具）、`test_nightly_interpreter_determinism.py` 278→309（DEF-200-302：刪 PATH 剝除
A／D 兩類、增釘死根層 .venv 的 E 類與大括號感知 fail-loud 判準）、`test_skip_ceiling_ratchet_direction.py`
706→724（DEF-200-303 re-key 後方向鎖改走 `legacy_profile()`）；抵銷＝Dev-Trim 兩棒對 tools/tests 鎖檔的
史料散文搬遷（`test_doc_loc_baseline_freshness_r60.py` −97／`test_ntfs_trailing_space_device_name.py` −61／
`test_platform_neutral_paths.py` −60／`test_check_hooks_liveness.py` −59／`test_archive_defect_log.py` −43／
`test_dev_start.py` −38／`test_check_defect_log_crossref.py` −27／`test_check_script_parity.py` −26／
`test_pre_push_dispatcher.py` −21／`test_context_budget_guard.py` −20／`test_wake_chain_halt_r278.py` −11／
`test_smoke_ci_sync.py` −9），逐字保全於 `CrossPlatform_R151_Guard_Prose_Migration.md`；本檔
（`test_adr_xplat001_c1c2_lock.py`）自身重釘漂移（主表兩新檔登記＋R151 列＋cap 排程列與接鏈列、
凍結前綴 `_REPIN_LOG_FROZEN_PREFIX_LEN` 219→220）含於同一列，未使用任何一次性例外名冊。分桶棘輪同輪
重釘：`prose` 桶與 `guard_self` 桶皆只降（值以 `guard_layer_bucket_census.py --grain chunk` 現查為準）。
DEF-200-304／305 的修復全在 AutoClaude 側，不計護欄層。缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md`
DEF-200-301～DEF-200-306。此附記為 doc-total 對帳（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，
同 R129～R150 寄居體例。round-label-ok

## 第十四輪附記（R152；DEF-200-307～310 單一 .venv 四方審查殘餘收尾）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為四筆缺陷收尾造成的護欄層逐檔漂移
  記帳，寄居本檔（同 R129～R151 寄居體例，不另開新檔）。本輪**非淨減法輪**（R151 淨減法輪已把
  款(11) 連續上升 streak 歸零，本輪可為正）；cap 到期輪 R153 尚未到，本輪維持 540 不動。

<!-- guard-total:R152 --> R152 護欄層累積淨額＝ 99812 → 100211（+399）——內容成長 +249：
`test_nightly_interpreter_determinism.py` 312→384（+72，DEF-200-307：mac nightly／smoke 釘死
根層 .venv 的 F 項斷言）／`test_dev_start.py` 6540→6649（+109，DEF-200-308：雜散 venv 全樹
遞迴掃描＋`step_venv` 擋下）／`test_clean_venv_carrier.py` 199→262（+63，DEF-200-309：clean_venv_
carrier 建立失敗必清理）三筆缺陷的回歸鎖，全額歸回歸鎖軌；`test_windowsapps_guard_cross_
consistency.py` 2051→2052（+1，DEF-200-310：過期字面訂正折行）性質非回歸鎖，全額歸功能軌、
不計入回歸鎖軌淨額；`test_find_git_bash_parity.py` 1306→1310（+4，DEF-200-312：釘死根層 .venv 後
首晚 nightly 真跑抓到 schtasks 最高權限下 `_real_shim` symlink venv launcher ⇒ rc=106，改 Windows 一律
shebang 包裝）同輪追加、歸回歸鎖軌。另 +37 本檔（`test_adr_xplat001_c1c2_lock.py`）自身逐檔漂移收斂（主表新增
列＋`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列＋`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 到期義務
具名展延 152→157〔鐵律七：真拆屬獨立重構持有面，非本輪並行包能做完，展延理由逐字寫在檔內〕
＋同輪追加列所造成的行數漂移，`--print-guard-lines` 反覆覆核收斂到本行本身也計入為止，同
既有體例；凍結前綴 `_REPIN_LOG_FROZEN_PREFIX_LEN` 220→224、`_REPIN_LOG_HISTORY_SHA256`／
`_FROZEN_PREFIX_REWRITE_LEDGER` 同步重釘），全額歸回歸鎖軌。回歸鎖軌淨額合計 285
（`_REGRESSION_LANE_LOG` R152 列，244＋4＋37 自身漂移，未超軌上限 309，未使用任何一次性例外
名冊；DEF-200-310 的 +1 明文排除於本軌淨額之外）。分桶棘輪同輪重釘：`prose` 桶與 `guard_self`
桶皆與上輪相同、未變動（值以 `guard_layer_bucket_census.py --grain chunk` 現查為準）。缺陷
帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-307～DEF-200-310。此附記為 doc-total
對帳（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，同 R129～R151 寄居體例。

**R152 沿用追加**（+113，累計兩批）：第一批 +71——DEF-200-314（mac launchd nightly
三症狀修復）新增 `test_nightly_interpreter_determinism.py` G 項兩支斷言（+58，先紅
後綠實證：mac 對稱 `--unattended` 呼叫、Homebrew bin 存在性探測）＋本檔（`test_adr_
xplat001_c1c2_lock.py`）自身逐檔漂移收斂（+13）。第二批 +42——四方複審四項非阻斷
修正：Homebrew append-only 位置鎖三支斷言＋run_stage 3 整行 unattended 鎖＋
docstring「四件事」訂正為「五件事」（`test_nightly_interpreter_determinism.py`
+29，先紅後綠實證：對 HEAD 舊版與修前的往前插版各驗一次紅）＋本檔自身逐檔漂移收斂
（+13，凍結前綴 `_REPIN_LOG_FROZEN_PREFIX_LEN` 226→228、`_REPIN_LOG_HISTORY_SHA256`／
`_FROZEN_PREFIX_REWRITE_LEDGER` 同步重釘）。兩批皆全額歸功能軌（`[全額功能軌]` 標記，
非回歸鎖）。
逐項見 `CrossPlatform_R152_DEF200314_MacNightly_Evidence.md`；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-314～DEF-200-316。round-label-ok

## 第十五輪附記（R153；DEF-200-289／290／292／317／318 多 CPU 四方審查收尾）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為五筆缺陷收尾造成的護欄層逐檔漂移
  記帳，寄居本檔（同 R129～R152 寄居體例，不另開新檔）。本輪**非淨減法輪**；R152／R153 已連續
  兩輪上升（`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2` 名額用罄）⇒ **R154 必須是淨減法輪**（淨額
  ≤0），否則款(11) 當場紅。cap 到期義務同輪兌現：`_REPIN_NET_CAP_SCHEDULE` 追加 `(153, 539)`、
  重新武裝 `_REPIN_NET_CAP_DUE_ROUND=155`／`_REPIN_NET_CAP_DUE_TARGET=538`。

<!-- guard-total:R153 --> R153 護欄層累積淨額＝ 100211 → 100695（+484）——內容成長 +445：
`test_cpu_budget.py` 新檔 158（DEF-200-289 跨 leg CPU 預算 SSOT 的公式／cap／floor／per_leg／CLI
契約鎖；DEF-200-317 AutoClaude `pyproject.toml` addopts `-n auto --dist worksteal` 讀 toml 斷言寄居
其中）——新判準能力鎖檔，**全額歸功能軌**（GAP-E 鎖保守不計入回歸鎖軌）；`test_ci_gate_xdist_
allowlist.py` 121→213（+92：`CiGatePs1FallbackXdistTest` 鎖住 DEF-200-318「fallback 只跑凍結基線
故**不加** xdist」判讀＋`CpuBudgetExportWiringTest` 鎖 pre-push／ci-gate.sh／ci-gate.ps1 三處匯出段）
歸回歸鎖軌；`test_run_root_unittests.py` 4443→4458（+15：`WorkerCountFormulaTest` 三支顯式拔掉
`GITHUB_ACTIONS`／`AUTOSDD_CPU_HEADLESS`，避免本機綠 CI 紅）歸回歸鎖軌；`test_workflow_permission_
concurrency_lock.py` 1406→1580（+174＝DEF-200-292 告警 label 自癒＋開單不吞錯的三支鎖與兩支 helper
共 105 歸回歸鎖軌＋DEF-200-290 headSha 涵蓋 advisory 三支新判準鎖 69 歸功能軌）；`test_dev_start.py`
6649→6655（+6：DEF-200-319 pre-push 第二次實跑抓到 SIGINT 兩支同型測試 pidfile TOCTOU，改等 pid 文字）歸回歸鎖軌。另 +39 本檔
（`test_adr_xplat001_c1c2_lock.py`）自身逐檔漂移收斂（主表新增兩列＋`_REGRESSION_LANE_LOG` 同輪列＋
`_REPIN_NET_CAP_SCHEDULE` 兌現列＋`_PHASE2_REVIEW_LOG` 同輪 `[提案]` 列〔體例同 R141 那筆：非對 (c)
方向新判斷，僅因稽核痕跡推進到 R153 觸發 §6 五輪時效且 R147 的「維持觀察」名額已用罄〕＋
`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列；凍結前綴 `_REPIN_LOG_FROZEN_PREFIX_LEN` 228→230、
`_REPIN_LOG_HISTORY_SHA256` 同步重釘），全額歸回歸鎖軌。回歸鎖軌淨額合計 257（`_REGRESSION_LANE_LOG`
R153 那筆＝92＋15＋105＋6＋39 自身漂移，未超軌上限 309、未使用任何一次性例外名冊；功能軌 227＝158＋69）。
缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-289／290／292／317／318／319；四方審查與實作
證據見 `CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第十二輪〉。此附記為 doc-total 對帳
（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，同 R129～R152 寄居體例。round-label-ok

## 第十六輪附記（R154；DEF-200-319 第三支補硬化／DEF-200-320 nightly-full 接 SSOT 四方複審收尾）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為兩筆缺陷收尾造成的護欄層逐檔漂移記帳，
  寄居本檔（同 R129～R153 寄居體例）。本輪為 **淨減法輪**（R152／R153 連續兩輪上升名額用罄，
  `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2` ⇒ 本輪淨額必須 ≤0）。cap 到期義務未到（武裝 155／538 不動）；
  `_PHASE2_REVIEW_LOG` 五輪時效未到，本輪無新登記。

<!-- guard-total:R154 --> R154 護欄層累積淨額＝ 100695 → 100691（-4）——內容 -2：`test_dev_start.py`
6655→6653（DEF-200-319：三處同型 pidfile 輪詢抽成模組層 `_wait_pid_text(path, timeout)`，兩支已修者改呼叫、
第三支 `test_lock_stays_busy_via_killpg_while_any_grandchild_alive_then_clears` 同輪補硬化並移除 `time.sleep(0.3)`
權宜緩衝）；`test_ci_gate_xdist_allowlist.py` 213→213（DEF-200-320：`CpuBudgetExportWiringTest` 三支重複方法合併為
`test_orchestrators_export_cpu_budget`，`subTest` 五目標涵蓋兩支 nightly-full workflow）。本檔
（`test_adr_xplat001_c1c2_lock.py`）-2：新增主表列與 `_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列（+8 級）以
`repin_growth_problems()` docstring 兩段史料（ADR-XPLAT-013 Phase2 (b) 分軌 WHY、DEF-200-208 例外名冊 WHY）搬遷
`CrossPlatform_Guard_Line_History.md`〈repin_growth_problems 分軌與例外名冊 WHY〉節抵銷（程式碼內各留一句摘要＋指針）；
凍結前綴 `_REPIN_LOG_FROZEN_PREFIX_LEN` 230→231、`_REPIN_LOG_HISTORY_SHA256` 同步重釘。母項為負 ⇒ 不申報
`_REGRESSION_LANE_LOG`（同 R146／R151 體例），款(9) 不適用、款(11) 連續計數歸零。缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-319／320；四方複審與實作證據見
`CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第十三輪〉。此附記為 doc-total 對帳（≥2 站點）另一站點寄居
`AutoSDD_improving_112.md`，同 R129～R153 寄居體例。round-label-ok

## 第十七輪附記（R155；DEF-200-315 互動式入口釘死根層 .venv＋DEF-200-321～323 四方審查收尾）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為四筆缺陷收尾造成的護欄層逐檔漂移記帳，
  寄居本檔（同 R129～R154 寄居體例）。本輪為**非淨減法輪**（R154 淨額 -4 已使連續上升計數歸零，
  本輪為連升第 1 輪，≤ 上限 2）。cap 到期義務本輪兌現：`(155, 538)` 落地，重新武裝
  `_REPIN_NET_CAP_DUE_ROUND` 155→157、`_REPIN_NET_CAP_DUE_TARGET` 538→537；`_PHASE2_REVIEW_LOG`
  五輪時效未到（R153 [提案] 起算），本輪無新登記。

<!-- guard-total:R155 --> R155 護欄層累積淨額＝ 100691 → 101532（+841）——DEF-200-315（互動式入口
改經 `pick_repo_python`／`Get-RepoPython` SSOT 化：本機缺席 fail-loud、CI／`AUTOSDD_ALLOW_PATH_PYTHON=1`
容許 PATH）／DEF-200-321（root-infra-ci never-started jq 判準排除 `conclusion=="skipped"`）／
DEF-200-322（雜散 venv 守衛四處補洞：`.venv-cache-*` 根層限定剪枝／pre-commit CLI 閘／symlink
`pyvenv.cfg` 查探）／DEF-200-323（`uv sync`／`uv run` 第二顆 venv：dev_start 兩殼 export
`UV_PROJECT_ENVIRONMENT`）四筆收尾的新增測試涵蓋：`test_nightly_interpreter_determinism.py` +349
（H 項新判準能力鎖：本機缺席 fail-loud／CI 容許 PATH／逃生口三情境）、
`test_windowsapps_guard_cross_consistency.py` +126、`test_dev_start.py` +105、
`test_windowsapps_guard_bash_parity.py` +89、`test_pre_commit_dispatcher_sigpipe.py` +33、
`test_workflow_permission_concurrency_lock.py` +32、`test_find_git_bash_parity.py` +26、
`test_clean_venv_carrier.py` +19、`test_git_hooks_install_common.py` +18、
`test_ci_gate_xdist_allowlist.py` +8、`test_pre_push_dispatcher.py` +7（合計 +812）；本檔
（`test_adr_xplat001_c1c2_lock.py`）自身逐檔漂移 +29（新增主表兩列〔內容＋收斂〕、
`_REGRESSION_LANE_LOG` 同輪新列、`_REPIN_NET_CAP_SCHEDULE` 到期義務兌現列與重新武裝、
`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列；凍結前綴 231→233、`_REPIN_LOG_HISTORY_SHA256` 同步重釘）。
分軌：`_REGRESSION_LANE_LOG` R155 列申報 309（貼齊上限，同 R131 體例，優先納入 DEF-200-322／323 的
`test_dev_start.py`／`test_pre_commit_dispatcher_sigpipe.py`／`test_clean_venv_carrier.py` 段、
DEF-200-321 的 `test_workflow_permission_concurrency_lock.py` 段、DEF-200-315 的 windowsapps_guard
兩支三情境行為測試段；`test_nightly_interpreter_determinism.py` 的 H 項與逾額片段保守歸主軌），
主軌淨額 841−309＝532 ≤ cap 538。缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md`
DEF-200-315／321／322／323；四方審查與實作證據見 `CrossPlatform_R152_DEF200314_MacNightly_Evidence.md`
〈收尾（R155）〉。此附記為 doc-total 對帳（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，
同 R129～R154 寄居體例。round-label-ok

## 第十八輪附記（R156；DEF-200-324 pre-push 整合閘門 `--dist loadgroup` 修復）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為單一缺陷修復造成的護欄層逐檔漂移記帳，
  寄居本檔（同 R129～R155 寄居體例）。**另起本輪**（判例＝R132／R136：R155 主軌額度僅剩
  538−532＝6 行，不足容納本次新增，故不續記 R155 而另起）。本輪為非淨減法輪，且是連續第 2 輪
  淨額為正（R155 主軌 +532、本輪主軌 +22）——`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2` 已到頂，
  **R157 必須淨額 ≤0**。cap 到期義務未到（`_REPIN_NET_CAP_DUE_ROUND=157` 尚未觸及，武裝不動）；
  `_PHASE2_REVIEW_LOG` 五輪時效未到，本輪無新登記。

<!-- guard-total:R156 --> R156 護欄層累積淨額＝ 101532 → 101607（+75）——DEF-200-324
（`tools/integration_gate_core.py` 的 `sec_bridge()`／`sec_rollback()` 兩處 AutoClaude pytest 呼叫
零 `--dist loadgroup` 判準，PG 在場即撞 DEF-200-274 X1 守門 rc=4；只在動到閘門本體時 pre-push
才實跑此 leg，故潛伏已久直到近期改動 `integration_gate.sh` 才曝光，擋下一次真實 push）修復：
新增 `_pg_dist_args()` 純函式（問 `AutoClaude/tools/local_ci_gate.py` 的 `pg_autodetect()`／
`pg_dsn_in_effect()` SSOT，同 DEF-200-295 判例，探針失敗保守加）並接進兩處呼叫點；
`test_pre_push_dispatcher.py` 新增 `TestIntegrationGateCorePgDistArgs` 四支行為測試 +53
（PG 在場／缺席／探針失敗三情境＋兩呼叫點接線突變自證）；本檔（`test_adr_xplat001_c1c2_lock.py`）
自身逐檔漂移 +22（新增主表兩列〔內容＋收斂〕、`_REGRESSION_LANE_LOG` 同輪新列、
`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列；凍結前綴 233→235、`_REPIN_LOG_HISTORY_SHA256` 同步重釘）。
分軌：`_REGRESSION_LANE_LOG` R156 列申報 53（`test_pre_push_dispatcher.py` 新增測試全額為
DEF-200-324 缺陷回歸鎖），本檔自身漂移保守全額歸主軌，主軌淨額 75−53＝22 ≤ cap 538。真機驗證：
`bash tools/integration_gate.sh --skip-full`（PG 在場）rc=0，`[3/5]`／`[4/5]` 皆 PASS（22 passed／
2 passed）。缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-324；證據見
`CrossPlatform_R152_DEF200314_MacNightly_Evidence.md`〈收尾（R155）〉#### R156 追記。此附記為
doc-total 對帳（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，同 R129～R155 寄居體例。
round-label-ok

## 第十九輪附記（R157；多 CPU 第十四輪＋DEF-200-325 對話框根治＋DEF-200-326～331 收尾）

- **體例**：本節非開新一輪 CrossPlatform 掃描輪四件套，僅為單一收尾窗口造成的護欄層逐檔漂移記帳，
  寄居本檔（同 R129～R156 寄居體例）。前兩輪（R155／R156）主軌淨額連續為正、
  `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2` 已到頂 ⇒ 本輪主表扣除回歸鎖軌後必須 ≤0：本輪申報
  回歸鎖軌 62（＝同輪主表淨額，子集不得大於母項；raw 回歸鎖行數 +75，餘 13 由史料搬遷抵銷），
  主軌 62−62＝0。cap 到期義務兌現：`(157, 537)`，同輪重新武裝 `_REPIN_NET_CAP_DUE_ROUND=159`／
  `_REPIN_NET_CAP_DUE_TARGET=536`；`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 具名展延 157→162；
  `_PHASE2_REVIEW_LOG` 五輪時效未到，本輪無新登記。

<!-- guard-total:R157 --> R157 護欄層累積淨額＝ 101607 → 101669（+62）——內容 +32（
`test_windowsapps_guard_cross_consistency.py` 2178→2174：DEF-200-325 文字鎖 +13、docstring 訂正搬遷 −17；
`test_ci_gate_xdist_allowlist.py` 213→207：DEF-200-326 路徑鎖 +34、DEF-200-318 fallback 鎖改寫 −15、
模組 docstring 搬遷 −25；`test_cpu_budget.py` 154→183：DEF-200-327 實體核公式鎖 +29；
`test_run_root_unittests.py` 6653→6660：WorkerCountFormulaTest.setUp +5、自動細分門檻鎖 +9、
類別 docstring 搬遷 −11；本檔 `_zzz_` 暫態排除 +6）＋本檔自身漂移 +30（主表兩列、回歸鎖軌新列、
cap 到期兌現列與重新武裝、接鏈列、舊尺技術債展延；凍結前綴 235→237、`_REPIN_LOG_HISTORY_SHA256`
同步重釘）。史料逐字保全於 `CrossPlatform_Guard_Line_History.md`〈R157 WorkerCountFormulaTest WHY〉
與〈R157 test_ci_gate_xdist_allowlist 模組 WHY〉。缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md`
DEF-200-325～331；證據見 `CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第十四輪〉。此附記為
doc-total 對帳（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，同 R129～R156 寄居體例。
round-label-ok
