# RTM - SelfImproving P0（觀察帳本定稿、一次性遷移、`check` 與協定目錄）

**版本**: 1.1（SCG-4 二審更新；1.0＝一審〔FAIL，commit `6c4a753d`〕；表格形沿用 `docs/06_quality/RTM-SddEnv.md`，欄位依本輪任務書）
**日期**: 2026-10-19（二審更新 17:09 +08:00）
**狀態**: SCG-4 二審 **PASS**（P1＝0、P2＝0、P3＝0；P4 殘餘 6 項皆不阻斷：F-08、F-10、F-11 (iv)、F-12、F-14、F-15）。一審 FAIL 的兩個阻斷項（F-01 SOP 啟動條件語意偏離、F-02 帳本第 047 列座標點不到）已修復並複驗；結論與逐項證據見 `docs/06_quality/SCG4-REVIEW-SelfImproving-P0-20261019.md` §8。追溯完整：19 個 AC 全列、42 個 AT 全列且全數實跑通過；AC 層 19/19 結案。
**覆蓋率**: AC 19/19（100%）；AT 42/42（100%）；AC 層結案 19/19
**規格**: `docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md`（Stage-2 凍結 `sha256:6c4e28ed30ab3e05ea1acbbf4b8d1a5a5004f5a2aed3fb535abb59cfb420de56`，二審當回合重算相符）；上游 `docs/01_requirements/SelfImproving_PRD.md`（`sha256:9c5718274eb511cc071deb1193ae7eadaaffc3b636826acf8e7935a50754460e`，重算相符）
**實作**: T `13e87b749721cae25a6782005df73587c73baf21`（`tools/selfimproving.py`、`tools/lib/si_*.py` 7 檔、`tools/tests/test_selfimproving_check.py`、`docs/06_quality/SelfImproving_Protocol/{params.json,metrics.md}`、`docs/05_development/SelfImproving_Operations_SOP.md`，加主控收尾的護欄層重釘）→ M `ab4638c439ad1cc4b8408efcd454c29ef7966d0b`（帳本一次性遷移）→ N `f1d7660f16ac8afb15ccdaa582a8ef4a7f6caf04`（`migration_base_sha`＋確認列）→ X `56ef5393ccd41e868b8bf9fd4d8fbd946527b0a0`（流程摩擦入帳）→ Y1 `6c4a753d`（一審報告與 RTM）→ Y2 `9fd15796`（SOP 條文改寫）→ Y3 `4eb912d0`（帳本更正列 063～081）→ Y4 `968e827b`（SD 修復：`tools/lib/si_refs.py`、測試檔、護欄層重釘）→ Y5 `622c83d22675d41c8e85172e95c8af92a6c399f3`（帳本 082～092，HEAD）

> 「本次結果」一律是當回合真跑的輸出（Windows 11；Python 3.11.9；pytest 9.1.1）。整檔：`42 passed, 97 subtests passed in 41.54s`（`python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts=`，rc 0）。逐 AT 單跑指令即 TCS §2 的判定指令（加 `-p no:xdist -o addopts=`）。測試檔座標（行區間）以 HEAD `622c83d2` 為準；測試檔一變動，行區間即過期，須重抽。macOS／POSIX 與 GitHub Actions 端未驗。

## 1. FR → AC 追溯（19 個 AC）

AC 編號規則見 TCS 檔頭：`AC-0NN-Y` 對映 PRD 的 `AC-SI-NN-Y`；`AC-030-x`、`AC-031-x`、`AC-032-x` 為 TCS 自增（來源逐條標示於 TCS 的〈AC 編號規則〉）。

| FR／來源 | PRD AC | TCS AC | User Story | 對應 AT | AT 本次結果 | PRD 座標 | AC 層結論（含實跑檢核） |
|----------|--------|--------|-----------|---------|------------|----------|------------------------|
| FR-SI-01 | AC-SI-01-1 | AC-001-1 | US-001 | AT-001-1-1、AT-001-1-E-1～E-6（7） | 7/7 通過 | PRD:243 | 通過（V2 二審：`row.required`、`row.coordinates`、`row.enums`、`ledger.time_tz` 皆 PASS，92 列；獨立重判 27 個判定碼 0 命中）；文字形態 `[warn]` 前綴已有斷言（F-05 結案） |
| FR-SI-01 | AC-SI-01-2 | AC-001-2 | US-001 | AT-001-2-1（1） | 1/1 通過 | PRD:244 | 通過（V2：`row.markers` PASS；帳本無守衛面 P1／P2 列，唯一的 P2 是第 081 列且面＝文件）；P2＋暴露＝無已有 AT 子測試，突變 M-N 殺（F-05 結案） |
| FR-SI-01 | AC-SI-01-3 | AC-001-3 | US-002 | AT-001-3-1、AT-001-3-E-1～E-4（5） | 5/5 通過 | PRD:245 | **通過（二審結案）**：V1、V4、V5 通過；V3 (1)～(9) 全數通過（(9)「座標可重查」：047 等六列由第 063～068 列更正列補座標，F-02 結案）；R18 (c) 路徑逃逸已有 AT（AT-001-3-E-4 的六個子測試，F-03 結案） |
| FR-SI-02 | AC-SI-02-1 | AC-002-1 | US-001 | AT-002-1-1（1） | 1/1 通過 | PRD:248 | 通過（V8：SOP:50 現含「≥1 個內部來源」，F-11 (ii) 結案） |
| FR-SI-02 | AC-SI-02-2 | AC-002-2 | US-001 | AT-002-2-1（1） | 1/1 通過 | PRD:249 | 通過（V2：`row.provenance` PASS；`check` 唯讀零副作用見 AC-030-2） |
| FR-SI-03 | AC-SI-03-1 | AC-003-1 | US-004 | AT-003-1-1（1） | 1/1 通過 | PRD:252 | **通過（二審結案）**：靜態掃描、動詞範圍、settings 皆通過；SOP〈啟動條件〉(a)～(e) 已改寫並逐句對照 PRD 語意一致（V8、F-01 結案）；恆真斷言已換成鑑別斷言（F-07 i） |
| FR-SI-03 | AC-SI-03-2 | AC-003-2 | US-004 | AT-003-2-1（1） | 1/1 通過 | PRD:253 | 通過（V8：SOP:21 現含成效宣稱須指向症狀指標，F-11 (iii) 結案；V2：`ledger.vacuity` PASS，92 列對下限 10） |
| FR-SI-03 | AC-SI-03-3 | AC-003-3 | US-004 | AT-003-3-1（1） | 1/1 通過 | PRD:254 | 通過（V8：SOP:23 現寫明 T1 是指令、T2～T4 是症狀條件，F-11 (i) 結案；`check --help` 旗標集合恰為五個，已由黑箱探測再證） |
| FR-SI-04 | AC-SI-04-1 | AC-004-1 | US-003 | AT-004-1-1、AT-004-1-E-1～E-3（4） | 4/4 通過 | PRD:257 | 通過（V2：`ref.def`、`ref.obs`、`ref.orig_notes` PASS；`ref.carrier_families` 為 nonblocking NE，`families=PROP-SI count=24`） |
| FR-SI-04 | AC-SI-04-2 | AC-004-2 | US-003 | AT-004-2-1（1） | 1/1 通過 | PRD:258 | 通過（V8：SOP:41） |
| FR-SI-04 | AC-SI-04-3 | AC-004-3 | US-002 | AT-004-3-1、AT-004-3-E-1～E-3（4） | 4/4 通過 | PRD:259 | 通過（V2：`history.row_mutated` PASS；V9：N 之後三個 commit〔11＋19＋11 列〕皆單一 hunk 純追加、0 行刪改） |
| FR-SI-29 | AC-SI-29-1 | AC-029-1 | US-004 | AT-029-1-1（1） | 1/1 通過 | PRD:390 | 通過（V8：Developer 交卷 5 項、QA 一審 §6 八項〔第 069～075 列共七列，#7 併入第 085 列〕、SD 修復棒七項〔第 086～092 列〕皆入帳；SD 項目與交卷原文的逐項對帳未驗） |
| FR-SI-29 | AC-SI-29-2 | AC-029-2 | US-004 | AT-029-2-1（1） | 1/1 通過 | PRD:391 | 通過（V8：SOP:25；V6：`non_evolvable_globs` 含迴圈自身四檔） |
| 自增：§9.3 `check` 列、NFR-SI-09-1 | － | AC-030-1 | US-005 | AT-030-1-1、AT-030-1-E-1（2） | 2/2 通過 | PRD:635、PRD:450 | 通過（V2；黑箱探測：rc 3、`--help`、文字形態）；AT-030-1-1 已與 TCS 文字同強——逐行解析文字形態並與 `--json` 逐項相等（F-04、F-05 結案） |
| 自增：§9.3 `check` 列、§9.4 | － | AC-030-2 | US-005 | AT-030-2-1（1） | 1/1 通過 | PRD:635、PRD:676 | 通過（靜態 grep 零命中 `os.system` 等；AT-030-2-1 現攔截 `os.system`／`os.popen`，F-07 iv 結案；二審 `check` 牆鐘 1.42s） |
| 自增：§9.4、NFR-SI-09-3（指紋為 TCS 類推） | － | AC-030-3 | US-005 | AT-030-3-1、AT-030-3-2（2） | 2/2 通過 | PRD:676、PRD:452、PRD:646 | 通過（V2：`fingerprint` 與一審相同；黑箱探測：草稿列九欄、ID 加一） |
| 自增：§9.1 C5、§9.3、NFR-SI-02-1 | － | AC-031-1 | US-005 | AT-031-1-1、AT-031-1-E-1～E-5（6） | 6/6 通過 | PRD:566、:635、:413–415、:697 | 通過（V6：23 鍵逐鍵、25 項 glob 獨立現算相等；二審 `params.*` PASS、指紋不變） |
| 自增：§9.1 C5「指標定義」、§1.3 | － | AC-031-2 | US-005 | AT-031-2-1（1） | 1/1 通過 | PRD:566、:61–65、:69–78 | 通過（M1～M5 五列與判定細則逐字存在；判準自證三項） |
| 自增：§9.1 C6、NFR-SI-07-2 | － | AC-032-1 | US-005 | AT-032-1-1（1） | 1/1 通過 | PRD:567、PRD:444 | 通過（SOP 骨架齊備；啟動條件語意歸 AC-003-1，已結案） |

## 2. AC → AT → 測試方法 → 本次結果 → 證據座標（42 個 AT）

測試檔座標均為 `tools/tests/test_selfimproving_check.py`（下表只寫 `類別::函式（行區間）`，行區間以 HEAD `622c83d2` 為準）；「TCS」欄為該 AT 的 gherkin 區塊在 TCS 檔內的行區間；「深度對照」＝本棒把測試本體逐斷言對照 TCS 的 Given／When／Then（其餘 AT 亦已讀完測試本體並對照，只是未寫入逐項表）；「F-xx 已修」＝一審發現已由 Y2～Y4 修復並複驗；「二審重放 M-…」＝二審突變重放中，該 AT 殺掉的突變（見 SCG-4 報告 §8.4）。

| AC | AT | 類型 | 測試方法（類別::函式與行區間） | `-k` 判定指令 | 本次結果（單跑，逐字） | 證據座標 |
|----|----|------|------------------------------|--------------|----------------------|----------|
| AC-001-1 | AT-001-1-1 | Integration | `TestLedgerRowRules::test_AT_001_1_1_baseline_is_green`（`:703–727`） | `AT_001_1_1` | 1 passed in 0.79s | TCS `:355–369` |
| AC-001-1 | AT-001-1-E-1 | Unit | `TestLedgerRowRules::test_AT_001_1_E_1_time_and_tz`（`:729–763`） | `AT_001_1_E_1` | 1 passed, 4 subtests passed in 1.31s | TCS `:373–390` |
| AC-001-1 | AT-001-1-E-2 | Unit | `TestLedgerRowRules::test_AT_001_1_E_2_required_fields_and_coordinates`（`:765–810`） | `AT_001_1_E_2` | 1 passed, 10 subtests passed in 2.25s | TCS `:394–413`；深度對照 |
| AC-001-1 | AT-001-1-E-3 | Unit | `TestLedgerRowRules::test_AT_001_1_E_3_enums`（`:812–844`） | `AT_001_1_E_3` | 1 passed in 1.53s | TCS `:417–438` |
| AC-001-1 | AT-001-1-E-4 | Unit | `TestLedgerRowRules::test_AT_001_1_E_4_structure`（`:846–913`） | `AT_001_1_E_4` | 1 passed, 6 subtests passed in 1.69s | TCS `:442–465` |
| AC-001-1 | AT-001-1-E-5 | Unit | `TestLedgerRowRules::test_AT_001_1_E_5_bytes_ctrl_crlf_volume`（`:915–972`） | `AT_001_1_E_5` | 1 passed in 2.37s | TCS `:469–489`；深度對照；F-05 已修；二審重放 M-G／M-H 皆殺 |
| AC-001-1 | AT-001-1-E-6 | Integration | `TestLedgerRowRules::test_AT_001_1_E_6_fixed_sha`（`:974–1007`） | `AT_001_1_E_6` | 1 passed in 1.21s | TCS `:493–512` |
| AC-001-2 | AT-001-2-1 | Unit | `TestLedgerRowRules::test_AT_001_2_1_guard_face_exposure`（`:1009–1044`） | `AT_001_2_1` | 1 passed, 1 subtests passed in 1.16s | TCS `:516–531`；深度對照；F-05 已修；二審重放 M-N 殺 |
| AC-001-3 | AT-001-3-1 | Integration | `TestMigration::test_AT_001_3_1_chain_is_exempt`（`:1048–1079`） | `AT_001_3_1` | 1 passed in 0.79s | TCS `:535–550` |
| AC-001-3 | AT-001-3-E-1 | Integration | `TestMigration::test_AT_001_3_E_1_no_sha_not_exempt`（`:1081–1106`） | `AT_001_3_E_1` | 1 passed, 2 subtests passed in 1.04s | TCS `:554–569` |
| AC-001-3 | AT-001-3-E-2 | Integration | `TestMigration::test_AT_001_3_E_2_confirm_row_variants`（`:1108–1134`） | `AT_001_3_E_2` | 1 passed, 8 subtests passed in 4.03s | TCS `:573–587`；深度對照；F-07 已修；二審重放 M-Q2 殺 |
| AC-001-3 | AT-001-3-E-3 | Integration | `TestMigration::test_AT_001_3_E_3_invalid_sha`（`:1136–1169`） | `AT_001_3_E_3` | 1 passed, 6 subtests passed in 1.77s | TCS `:591–606`；深度對照 |
| AC-001-3 | AT-001-3-E-4 | Integration | `TestMigration::test_AT_001_3_E_4_orig_rules`（`:1171–1236`） | `AT_001_3_E_4` | 1 passed, 6 subtests passed in 2.82s | TCS `:610–629`；深度對照；F-03 已修；二審重放 M-F／M-F2／M-F0 皆殺 |
| AC-002-1 | AT-002-1-1 | Unit | `TestMarksAndProvenance::test_AT_002_1_1_marks`（`:1242–1272`） | `AT_002_1_1` | 1 passed in 1.14s | TCS `:633–651` |
| AC-002-2 | AT-002-2-1 | Unit | `TestMarksAndProvenance::test_AT_002_2_1_provenance`（`:1274–1309`） | `AT_002_2_1` | 1 passed, 5 subtests passed in 2.37s | TCS `:655–671` |
| AC-003-1 | AT-003-1-1 | Unit | `TestScopeAndSop::test_AT_003_1_1_no_resident_mechanism`（`:1313–1370`） | `AT_003_1_1` | 1 passed in 0.14s | TCS `:675–690`；深度對照；F-07、F-01 已修 |
| AC-003-2 | AT-003-2-1 | Unit | `TestScopeAndSop::test_AT_003_2_1_below_floor_is_ne`（`:1372–1394`） | `AT_003_2_1` | 1 passed in 1.53s | TCS `:694–709` |
| AC-003-3 | AT-003-3-1 | Unit | `TestScopeAndSop::test_AT_003_3_1_output_count_not_a_reason`（`:1396–1405`） | `AT_003_3_1` | 1 passed in 0.14s | TCS `:713–727` |
| AC-004-1 | AT-004-1-1 | Integration | `TestReferences::test_AT_004_1_1_existing_references`（`:1463–1472`） | `AT_004_1_1` | 1 passed in 0.59s | TCS `:731–745` |
| AC-004-1 | AT-004-1-E-1 | Integration | `TestReferences::test_AT_004_1_E_1_dangling_obs`（`:1474–1516`） | `AT_004_1_E_1` | 1 passed, 5 subtests passed in 1.65s | TCS `:749–767`；深度對照 |
| AC-004-1 | AT-004-1-E-2 | Integration | `TestReferences::test_AT_004_1_E_2_dangling_def`（`:1518–1536`） | `AT_004_1_E_2` | 1 passed in 0.94s | TCS `:771–786` |
| AC-004-1 | AT-004-1-E-3 | Integration | `TestReferences::test_AT_004_1_E_3_carriers_not_established`（`:1538–1557`） | `AT_004_1_E_3` | 1 passed in 0.94s | TCS `:790–805` |
| AC-004-2 | AT-004-2-1 | Unit | `TestScopeAndSop::test_AT_004_2_1_real_defect_is_def`（`:1407–1410`） | `AT_004_2_1` | 1 passed in 0.14s | TCS `:809–822` |
| AC-004-3 | AT-004-3-1 | Integration | `TestHistory::test_AT_004_3_1_legal_evolution`（`:1563–1592`） | `AT_004_3_1` | 1 passed in 1.23s | TCS `:826–842` |
| AC-004-3 | AT-004-3-E-1 | Integration | `TestHistory::test_AT_004_3_E_1_in_place_rewrites`（`:1594–1634`） | `AT_004_3_E_1` | 1 passed in 1.32s | TCS `:846–862`；深度對照 |
| AC-004-3 | AT-004-3-E-2 | Integration | `TestHistory::test_AT_004_3_E_2_worktree_rewrites`（`:1636–1659`） | `AT_004_3_E_2` | 1 passed in 1.28s | TCS `:866–884` |
| AC-004-3 | AT-004-3-E-3 | Integration | `TestHistory::test_AT_004_3_E_3_no_history_and_outside`（`:1661–1679`） | `AT_004_3_E_3` | 1 passed in 0.80s | TCS `:888–903` |
| AC-029-1 | AT-029-1-1 | Unit | `TestScopeAndSop::test_AT_029_1_1_friction_entry`（`:1412–1420`） | `AT_029_1_1` | 1 passed in 0.14s | TCS `:907–920` |
| AC-029-2 | AT-029-2-1 | Unit | `TestScopeAndSop::test_AT_029_2_1_loop_self`（`:1422–1433`） | `AT_029_2_1` | 1 passed in 0.14s | TCS `:924–938` |
| AC-030-1 | AT-030-1-1 | Integration | `TestCli::test_AT_030_1_1_output_contract`（`:1750–1824`） | `AT_030_1_1` | 1 passed, 3 subtests passed in 2.00s | TCS `:942–961`；深度對照；F-04 已修；二審重放 M-H／M-H2／M-H3 皆殺 |
| AC-030-1 | AT-030-1-E-1 | Unit | `TestCli::test_AT_030_1_E_1_usage_errors`（`:1826–1860`） | `AT_030_1_E_1` | 1 passed, 11 subtests passed in 0.45s | TCS `:965–982` |
| AC-030-2 | AT-030-2-1 | Integration | `TestCli::test_AT_030_2_1_purity`（`:1862–1971`） | `AT_030_2_1` | 1 passed in 1.67s | TCS `:986–1003`；深度對照；F-07 已修；二審重放 M-W 殺 |
| AC-030-3 | AT-030-3-1 | Unit | `TestCli::test_AT_030_3_1_fingerprint`（`:1973–2010`） | `AT_030_3_1` | 1 passed in 1.63s | TCS `:1007–1023` |
| AC-030-3 | AT-030-3-2 | Unit | `TestCli::test_AT_030_3_2_obs_draft`（`:2012–2060`） | `AT_030_3_2` | 1 passed in 1.24s | TCS `:1027–1046` |
| AC-031-1 | AT-031-1-1 | Unit | `TestParams::test_AT_031_1_1_real_params`（`:2066–2095`） | `AT_031_1_1` | 1 passed in 0.61s | TCS `:1050–1066` |
| AC-031-1 | AT-031-1-E-1 | Unit | `TestParams::test_AT_031_1_E_1_missing_keys`（`:2097–2132`） | `AT_031_1_E_1` | 1 passed, 23 subtests passed in 4.75s | TCS `:1070–1084` |
| AC-031-1 | AT-031-1-E-2 | Unit | `TestParams::test_AT_031_1_E_2_glob_consistency`（`:2134–2183`） | `AT_031_1_E_2` | 1 passed, 7 subtests passed in 2.02s | TCS `:1088–1105`；深度對照 |
| AC-031-1 | AT-031-1-E-3 | Unit | `TestParams::test_AT_031_1_E_3_coupling`（`:2185–2219`） | `AT_031_1_E_3` | 1 passed in 1.83s | TCS `:1109–1127` |
| AC-031-1 | AT-031-1-E-4 | Unit | `TestParams::test_AT_031_1_E_4_types`（`:2221–2239`） | `AT_031_1_E_4` | 1 passed in 0.76s | TCS `:1131–1145` |
| AC-031-1 | AT-031-1-E-5 | Unit | `TestParams::test_AT_031_1_E_5_ranges`（`:2241–2257`） | `AT_031_1_E_5` | 1 passed in 0.76s | TCS `:1149–1163` |
| AC-031-2 | AT-031-2-1 | Unit | `TestParams::test_AT_031_2_1_metrics_verbatim`（`:2259–2285`） | `AT_031_2_1` | 1 passed in 0.14s | TCS `:1167–1181` |
| AC-032-1 | AT-032-1-1 | Unit | `TestScopeAndSop::test_AT_032_1_1_sop_skeleton`（`:1435–1457`） | `AT_032_1_1` | 1 passed in 0.14s | TCS `:1185–1199` |

備註：各 `-k` 皆恰選到 1 個測試（每個單跑輸出為 `1 passed, 41 deselected …`，上表省略 `41 deselected`）；Developer 交卷沒有逐 AT 列出驗收字樣 `[AT_OK_…]`（F-06，依裁決結案：Developer 任務書加此要求），故上表的逐 AT 單跑輸出是本棒補上的機器證據，二審已全部重跑（42/42 皆 `1 passed`）。與一審相比只有四個 AT 的子測試數改變：AT-001-2-1（0→1）、AT-001-3-E-2（7→8）、AT-001-3-E-4（0→6）、AT-030-1-1（0→3）；子測試合計 86→97，與整檔 `97 subtests passed` 吻合。

## 3. PRD §8.1 P0 退出條件 (a)～(d) 對照（TCS §6）

| 退出條件 | 對應 AT 與實跑檢核 | 本次結果 |
|----------|-------------------|----------|
| (a) 免追問必填欄 | AT-001-1-1、AT-001-1-E-1～E-5、AT-001-2-1、AT-002-2-1；V9 | 通過：AT 全綠；V9 檢視 N 之後新增的 41 列（052～092）皆 9 欄有值、無「某欄無法填」的反症狀（`row.required` PASS；獨立重判 27 個判定碼 0 命中） |
| (b) 自遷移基準起 `check` 綠 | AT-001-3-1、AT-004-3-1；V1、V2、V4 | 通過：HEAD 的 `check` rc 0（`overall=PASS`，92 列，唯一 NE 為 nonblocking 的載體項） |
| (c) 處置合枚舉且 `orig` 保全 | AT-001-1-E-3、AT-001-3-E-4；V3 | 通過：V3 (1)～(9) 全數通過（ID／時間／情境／症狀／分類／嚴重度逐格相同、座標只前綴追加 3 列、50 列處置皆有 `orig` 且逐字相同、`fixed@` 8 列 sha 語意核對無誤；(9) 座標可重查經第 063～068 列更正列補齊並複驗） |
| (d) 零無座標列、零「之後再看」 | AT-001-1-E-2、AT-001-1-E-3；V2 | 通過：`row.coordinates` 與 `row.enums` PASS；獨立重判 27 個判定碼 0 命中；「之後再看」只出現在檔頭〈規則〉的禁令敘述（第 6 行），處置欄命中 0 列 |

## 4. 實跑檢核 V1～V9 摘要（逐字輸出見 SCG-4 報告 §2 與 §8）

| 編號 | 檢核 | 結果 | 備註 |
|------|------|------|------|
| V1 | 提交鏈 | 通過 | T→M→N→X→Y1～Y5 線性；T、M、N、X 皆為 HEAD 祖先（rc 0）；Y2～Y5 未動 `.claude`、`.github`、凍結三檔與協定目錄 |
| V2 | 真帳本 `check --json` | 通過 | rc 0、92 列、21 項；`ref.obs` PASS；判準指紋與一審相同；獨立重判一致（27 個判定碼 0 命中，列位元組最大 689） |
| V3 | M 稽核 (1)～(9) | 通過 | (1)～(8) 一審已過；(9) 047 等六列由第 063～068 列更正列補座標並於二審複驗（F-02 結案）；新列 058 的座標易失已併入 F-15（P4） |
| V4 | `migration_base_sha` | 通過 | 輸入不變：值等於 M 的完整 sha；`history.migration` PASS（`claim=valid`） |
| V5 | 確認列引言座標 | 通過 | 輸入不變（第 001～062 列零改寫，`history.row_mutated` PASS）；line 2476、2581 皆 `type=user`＋`origin.kind=human`（一審驗證） |
| V6 | `params.json` 初值 | 通過 | 輸入不變（協定目錄零改動；指紋相同） |
| V7 | 護欄與零退化 | 通過 | 根層全套 rc 0（發現 5426、skip 46 皆已標籤）；ruff、LOC、缺陷編號引用鎖（11 passed）全綠；`--print-guard-lines` 淨額 +0、漂移 0；工作樹與 `.claude` 零改動；凍結三檔不變；`check` 牆鐘 1.42s／1.17s |
| V8 | SOP 與流程型 AC 文件檢核 | 通過 | SOP:11–15、:21、:23、:50 逐句對照 PRD AC-SI-03-1／-03-2／-03-3 與 AC-SI-02-1 語意一致（F-01、F-11 (i)(ii)(iii) 結案）；Developer、QA、SD 三方的流程摩擦皆入帳 |
| V9 | N 之後只追加 | 通過 | 三個 commit（11＋19＋11 列）皆單一 hunk 純追加、0 行刪改 |

## 5. NFR-P0-1～8 追溯

| NFR | 內容 | 驗證方式與本次結果 | 結論 |
|-----|------|-------------------|------|
| NFR-P0-1 | 純度與零副作用 | AT-030-2-1 通過，二審起並攔截 `os.system`、`os.popen`（M-W 殺）；一審以 grep 驗證 `tools/selfimproving.py` 與 `tools/lib/si_*.py` 零命中 `os.system`、`os.popen`、`check_output`、`sys.platform`、`.reconfigure(` | 通過 |
| NFR-P0-2 | 效能 | 二審真 repo `check` 牆鐘 1.42s（json）／1.17s（文字）（門檻 < 30s；一審三次 1.077s／1.044s／1.033s）；整檔 41.54s（本機），根層平行 worker 內 88.8s（一審 81.0s；門檻 < 180s，CI 未驗） | 通過（CI 端未驗） |
| NFR-P0-3 | 跨平台 | Windows 實跑；`tools/selfimproving.py` 與 `si_*.py` 無單平台 API；`si_refs.py` 改以 `PureWindowsPath` 判路徑逃逸，兩平台同判決（F-03 結案），測試以 `os.name` 分支涵蓋 POSIX 差異；macOS 未驗 | 通過（POSIX 實跑未驗） |
| NFR-P0-4 | 根層護欄相容 | 測試檔無 skip、skipTest、skipIf、xfail（一審 grep 僅命中區域變數名 `skip`）；文字檔 I/O 皆帶 encoding；二審根層全套 rc 0 | 通過 |
| NFR-P0-5 | LOC 分級 | 二審 `check_loc_budget.py --json` rc 0，`total_violation=False`，四個 violations 陣列皆空 | 通過 |
| NFR-P0-6 | 靜態檢查 | 二審 `ruff check` 9 個 `.py`（`selfimproving.py`、7 個 `si_*.py`、測試檔）：`All checks passed!`（`ruff format --check` 不在本 NFR 範圍；帳本第 090 列記錄 `si_refs.py` 非 format 乾淨，本棒未驗） | 通過 |
| NFR-P0-7 | 測試 hermetic | AT 只用 tmp 合成 repo（`mock.patch.dict(os.environ, …)` 淨化 `GIT_*`）；不讀真帳本；暫存目錄改 `setUpModule`／`tearDownModule`（F-07 iii 結案）；`ref.obs` PASS 與 `test_defect_id_reference_integrity.py`（11 passed）證明無不存在的字面編號；寫入前 `git diff --name-only` 為空 | 通過 |
| NFR-P0-8 | 範圍守衛 | `.claude/**`、`.github/**` 零改動、凍結檔（PRD、TCS、研究方法 SOP）digest 不變；T 提交含 §5.6 以外 8 檔，皆為主控收尾的重釘、CI paths 與 guard-total 站點連動（F-13，已裁決）；Y4 的重釘再度走一次性例外（F-10：R213 列精確淨額 2216→2318，名冊上限仍 5，請掌舵者過目） | 通過（附註） |

## 6. R 條文 → AT 對映與缺口（含突變試驗）

「突變」欄：一審在 scratchpad 複本對生產碼做單點突變（22 個），被對應 AT 殺掉者標「殺」，仍全綠者標「存活」＝該規則面沒有 AT 鑑別（見 SCG-4 報告 §3）；二審對一審六個存活突變加七個自訂對照共 13 個重放（見 SCG-4 報告 §8.4），全數被殺。

| R | 內容 | 觸及它的 AT | 突變／缺口 |
|---|------|------------|-----------|
| R1 | 介面、rc 表 | AT-030-1-1、AT-030-1-E-1、AT-003-1-1（`status`、`prop-new` rc 3）、AT-001-1-E-6（rc 2） | — |
| R2 | 路徑（相對 `--repo`） | AT-030-1-1（誘餌檔）、AT-004-3-E-3（repo 外絕對路徑） | — |
| R3 | 文字形態 | AT-001-1-1（首行、`overall=` 行）、AT-030-1-1（逐行解析項目行與 finding 行、NE 字樣、與 `--json` 相等）、AT-001-1-E-5（`[warn]` 前綴） | 一審存活的 M-G、M-H、M-H2 於二審全殺（M-H3 亦殺）；F-04、F-05 結案 |
| R4 | JSON 形態 | AT-030-1-1（四層鍵序）、AT-001-1-1 | — |
| R5 | 狀態語意 | AT-001-1-1、AT-001-1-E-6、AT-004-1-E-3、AT-031-1-E-1 | 突變 M-T（載體 NE 改 blocking）殺 |
| R6 | OBS 草稿列 | AT-030-3-2 | 突變 M-R（ID 不加一）殺；名額被 nonblocking NE 占用見 F-12（延後） |
| R7 | 判準指紋 | AT-030-3-1（測試內獨立重算） | 突變 M-L（不做 CRLF 正規化）殺 |
| R8 | 純度與零副作用 | AT-030-2-1 | 突變 M-K（拿掉 timeout）殺；M-W（`check` 經 `os.system` 起行程）二審殺 |
| R9 | 列識別與切分 | AT-001-1-E-4、AT-001-1-E-1 | 突變 M-I（拿掉 `ROW-ID-DUP`）殺 |
| R10 | 時間文法 | AT-001-1-E-1 | — |
| R11 | 位元組與控制字元 | AT-001-1-E-5 | 突變 M-B（邊界 `>` 改 `>=`）殺 |
| R12 | 必填欄 | AT-001-1-E-2 | — |
| R13 | 分類、嚴重度、處置 | AT-001-1-E-3 | 突變 M-Q（retired 缺座標不再判）殺 |
| R14 | 標記欄 | AT-002-1-1 | — |
| R15 | 面、暴露、來源、回報者 | AT-001-2-1、AT-002-2-1 | 守衛面 P2＋暴露＝無：一審存活的 M-N 於二審殺（F-05 結案） |
| R16 | 座標形態 | AT-001-1-E-2、AT-001-1-1 | — |
| R17 | `fixed@` 解析 | AT-001-1-E-6 | 突變 M-S（一律視為已解析）殺 |
| R18 | 引用完整性 | AT-004-1-1、AT-004-1-E-1～E-3、AT-001-3-E-4 | 突變 M-M 殺；(c) 路徑逃逸（`..`、絕對、rooted、磁碟機代號）：一審存活的 M-F、M-F2 於二審殺，另 M-F2a、M-F2b、M-F3、M-F0 亦殺（F-03 結案） |
| R19 | 遷移豁免 | AT-001-3-1、AT-001-3-E-1～E-4 | 突變 M-D、M-E、M-P 殺；「引言不被比對」對照突變 M-Q2（二審自訂）殺 |
| R20 | ROW-MUTATED | AT-004-3-1、AT-004-3-E-1～E-3、AT-001-3-E-1 | 突變 M-C、M-O 殺 |
| R21 | `params.json` 對表 | AT-031-1-1、AT-031-1-E-1、AT-031-1-E-4、AT-031-1-E-5 | 突變 M-J（比例上界）殺 |
| R22 | 耦合與 glob 一致性 | AT-031-1-E-2、AT-031-1-E-3、AT-029-2-1 | — |
| R23 | 反空轉與體積 | AT-003-2-1、AT-001-1-E-5 | 突變 M-A（fail 邊界）殺 |
| R24 | 協定目錄 | AT-031-1-1（params 檔形態）、AT-031-2-1（metrics 逐字） | — |
| R25 | SOP 骨架 | AT-032-1-1、AT-003-1-1、AT-003-2-1、AT-003-3-1、AT-004-2-1、AT-029-1-1、AT-029-2-1、AT-004-3-1 | 只判關鍵片段；語意由 V8 判（現行 SOP 已逐句對照一致，F-01 結案）；AT-003-1-1 的恆真斷言已換成關鍵字刪除鑑別（F-07 i） |
| R26 | 範圍守衛 | AT-003-1-1、AT-030-2-1（靜態） | — |

註：二審自訂的突變 M-Q2（確認列改成要求引言含特定文字）與一審的 M-Q（R13：retired 缺座標不再判）是不同的突變，故加 2 區分；二審的完整對照表見 SCG-4 報告 §8.4。

## 7. 覆蓋率統計

| 指標 | 數值 |
|------|------|
| 總 AC 數 | 19（PRD 13＋TCS 自增 6） |
| 有 AT 的 AC 數 | 19 |
| **AC→AT 映射覆蓋率** | **100%**（TCS §1；本棒機械抽取驗證：FRD-lite 的 AC 集合與 §1 映射的 AC 集合相等；二審以 `rtm_data.py` 重抽仍相等） |
| AT 數 | 42（E 類 22；Integration 17；Unit 25） |
| 有測試函式的 AT | 42/42（每個 AT 恰一個測試函式，名稱含其底線形） |
| 整檔實跑 | `42 passed, 97 subtests passed in 41.54s`（rc 0；一審 `42 passed, 86 subtests passed in 38.41s`） |
| 逐 AT 單跑（TCS 判定指令） | 42/42 為 `1 passed`（含子測試），rc 0，每個 `-k` 恰選到 1 個測試（二審重跑） |
| 根層全套 unittest | rc 0；發現 5426 個測試（下限 5326）；skip 46 支皆已標籤；`test_selfimproving_check` 於平行 worker 內 88.8s |
| 突變鑑別力 | 一審 22 個手選突變：16 個被殺、6 個存活；二審對六個存活突變加七個自訂對照共 13 個重放：13 個被殺、存活 0 |
| AC 層結案 | 19/19（二審：AC-001-3、AC-003-1 結案） |
| AT→CI Pipeline | 經根層 unittest 閘門本機實跑 rc 0；GitHub Actions 端（含 T 增列的兩支 compat-ci `paths`）未驗 |
| 平台 | Windows 實跑；macOS／POSIX 未驗（NFR-SI-06-5） |
| 發現統計 | 一審：P1＝0；P2＝2；P3＝3；P4＝9（SCG-4 報告 §4）。二審：P2、P3 全數結案；P4 殘餘 6 項（F-08、F-10、F-11 (iv)、F-12、F-14、F-15）；新發現 1 項（F-15，P4） |
| Developer 驗收字樣 | 0/42 列出（F-06，依裁決結案：Developer 任務書加此要求）；由本棒逐 AT 單跑補證 |

**未覆蓋與待補（供下一輪）**：(1) POSIX 與 CI 端實跑（含 F-03 的 POSIX 分支、T 增列的兩支 compat-ci `paths`）；(2) P4 殘餘：F-08（掌舵者追認）、F-10（一次性例外名冊的第二次使用）、F-11 (iv)（下一份 TCS 範本改「SCG-4 收尾前入帳」）、F-12（草稿列排除 nonblocking NE，P1 的 TCS 再議）、F-15（座標可重查性：第 082、058 列）；(3) 一審 §7 與二審 §8.11 列出的未查證項（`lint-imports`、AutoClaude pytest、`ci-gate`、`check` 邊界探測、護欄層重釘 sha 的獨立重算等）。
