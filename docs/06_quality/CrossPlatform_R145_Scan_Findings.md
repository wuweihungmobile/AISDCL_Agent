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
