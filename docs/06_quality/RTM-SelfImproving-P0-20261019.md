# RTM - SelfImproving P0（觀察帳本定稿、一次性遷移、`check` 與協定目錄）

**版本**: 1.0（SCG-4 獨立 QA 棒建立；表格形沿用 `docs/06_quality/RTM-SddEnv.md`，欄位依本輪任務書）
**日期**: 2026-10-19
**狀態**: SCG-4 一審 **FAIL**（P1＝0、P2＝2：F-01 SOP 啟動條件語意偏離、F-02 帳本第 047 列座標點不到；結論與逐項證據見 `docs/06_quality/SCG4-REVIEW-SelfImproving-P0-20261019.md`）。追溯本身完整：19 個 AC 全列、42 個 AT 全列且全數實跑通過；AC 層有 2 個 AC 因實跑檢核未過而未結案（AC-001-3、AC-003-1）。
**覆蓋率**: AC 19/19（100%）；AT 42/42（100%）；AC 層結案 17/19
**規格**: `docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md`（Stage-2 凍結 `sha256:6c4e28ed30ab3e05ea1acbbf4b8d1a5a5004f5a2aed3fb535abb59cfb420de56`，當回合重算相符）；上游 `docs/01_requirements/SelfImproving_PRD.md`（`sha256:9c5718274eb511cc071deb1193ae7eadaaffc3b636826acf8e7935a50754460e`）
**實作**: T `13e87b749721cae25a6782005df73587c73baf21`（`tools/selfimproving.py`、`tools/lib/si_*.py` 7 檔、`tools/tests/test_selfimproving_check.py`、`docs/06_quality/SelfImproving_Protocol/{params.json,metrics.md}`、`docs/05_development/SelfImproving_Operations_SOP.md`，加主控收尾的護欄層重釘）→ M `ab4638c439ad1cc4b8408efcd454c29ef7966d0b`（帳本一次性遷移）→ N `f1d7660f16ac8afb15ccdaa582a8ef4a7f6caf04`（`migration_base_sha`＋確認列）→ X `56ef5393ccd41e868b8bf9fd4d8fbd946527b0a0`（流程摩擦入帳，HEAD）

> 「本次結果」一律是當回合真跑的輸出（Windows 11；Python 3.11.9；pytest 9.1.1）。整檔：`42 passed, 86 subtests passed in 38.41s`（`python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts=`，rc 0）。逐 AT 單跑指令即 TCS §2 的判定指令（加 `-p no:xdist -o addopts=`）。macOS／POSIX 與 GitHub Actions 端未驗。

## 1. FR → AC 追溯（19 個 AC）

AC 編號規則見 TCS 檔頭：`AC-0NN-Y` 對映 PRD 的 `AC-SI-NN-Y`；`AC-030-x`、`AC-031-x`、`AC-032-x` 為 TCS 自增（來源逐條標示於 TCS 的〈AC 編號規則〉）。

| FR／來源 | PRD AC | TCS AC | User Story | 對應 AT | AT 本次結果 | PRD 座標 | AC 層結論（含實跑檢核） |
|----------|--------|--------|-----------|---------|------------|----------|------------------------|
| FR-SI-01 | AC-SI-01-1 | AC-001-1 | US-001 | AT-001-1-1、AT-001-1-E-1～E-6（7） | 7/7 通過 | PRD:243 | 通過（V2：`row.required`、`row.coordinates`、`row.enums`、`ledger.time_tz` 皆 PASS，62 列） |
| FR-SI-01 | AC-SI-01-2 | AC-001-2 | US-001 | AT-001-2-1（1） | 1/1 通過 | PRD:244 | 通過（V2：`row.markers` PASS；全帳本無 P1／P2 列）；P2＋暴露＝無無 AT 鑑別（F-05） |
| FR-SI-01 | AC-SI-01-3 | AC-001-3 | US-002 | AT-001-3-1、AT-001-3-E-1～E-4（5） | 5/5 通過 | PRD:245 | **未結案**：V1、V4、V5 通過，V3 (1)～(8) 通過但 (9)「座標可重查」未通過（F-02）；R18 (c) 路徑逃逸無 AT（F-03） |
| FR-SI-02 | AC-SI-02-1 | AC-002-1 | US-001 | AT-002-1-1（1） | 1/1 通過 | PRD:248 | 通過（V8：SOP:50 語意一致；缺「≥1 內部來源」見 F-11） |
| FR-SI-02 | AC-SI-02-2 | AC-002-2 | US-001 | AT-002-2-1（1） | 1/1 通過 | PRD:249 | 通過（V2：`row.provenance` PASS；`check` 唯讀零副作用見 AC-030-2） |
| FR-SI-03 | AC-SI-03-1 | AC-003-1 | US-004 | AT-003-1-1（1） | 1/1 通過 | PRD:252 | **未結案**：靜態掃描、動詞範圍、settings 皆通過，但 SOP〈啟動條件〉(b)(c)(d)(e) 語意與 PRD 不符（V8、F-01） |
| FR-SI-03 | AC-SI-03-2 | AC-003-2 | US-004 | AT-003-2-1（1） | 1/1 通過 | PRD:253 | 通過（V8：SOP:21；V2：`ledger.vacuity` PASS，62 列對下限 10） |
| FR-SI-03 | AC-SI-03-3 | AC-003-3 | US-004 | AT-003-3-1（1） | 1/1 通過 | PRD:254 | 通過（V8：SOP:23；`check --help` 旗標集合恰為五個，已由黑箱探測再證） |
| FR-SI-04 | AC-SI-04-1 | AC-004-1 | US-003 | AT-004-1-1、AT-004-1-E-1～E-3（4） | 4/4 通過 | PRD:257 | 通過（V2：`ref.def`、`ref.obs`、`ref.orig_notes` PASS；`ref.carrier_families` 為 nonblocking NE，`families=PROP-SI count=24`） |
| FR-SI-04 | AC-SI-04-2 | AC-004-2 | US-003 | AT-004-2-1（1） | 1/1 通過 | PRD:258 | 通過（V8：SOP:41） |
| FR-SI-04 | AC-SI-04-3 | AC-004-3 | US-002 | AT-004-3-1、AT-004-3-E-1～E-3（4） | 4/4 通過 | PRD:259 | 通過（V2：`history.row_mutated` PASS；V9：N 之後單一 hunk 純追加 11 列、0 行刪改） |
| FR-SI-29 | AC-SI-29-1 | AC-029-1 | US-004 | AT-029-1-1（1） | 1/1 通過 | PRD:390 | 通過（V8：Developer 交卷 5 項全數入帳；SD 項目對帳未驗） |
| FR-SI-29 | AC-SI-29-2 | AC-029-2 | US-004 | AT-029-2-1（1） | 1/1 通過 | PRD:391 | 通過（V8：SOP:25；V6：`non_evolvable_globs` 含迴圈自身四檔） |
| 自增：§9.3 `check` 列、NFR-SI-09-1 | － | AC-030-1 | US-005 | AT-030-1-1、AT-030-1-E-1（2） | 2/2 通過 | PRD:635、PRD:450 | 通過（V2；黑箱探測：rc 3、`--help`、文字形態）；AT-030-1-1 弱於 TCS 文字（F-04、F-05） |
| 自增：§9.3 `check` 列、§9.4 | － | AC-030-2 | US-005 | AT-030-2-1（1） | 1/1 通過 | PRD:635、PRD:676 | 通過（靜態 grep 零命中 `os.system` 等；V7：真 repo 牆鐘最大 1.077s） |
| 自增：§9.4、NFR-SI-09-3（指紋為 TCS 類推） | － | AC-030-3 | US-005 | AT-030-3-1、AT-030-3-2（2） | 2/2 通過 | PRD:676、PRD:452、PRD:646 | 通過（V2：`fingerprint` 與獨立重算一致；黑箱探測：草稿列九欄、ID 加一） |
| 自增：§9.1 C5、§9.3、NFR-SI-02-1 | － | AC-031-1 | US-005 | AT-031-1-1、AT-031-1-E-1～E-5（6） | 6/6 通過 | PRD:566、:635、:413–415、:697 | 通過（V6：23 鍵逐鍵、25 項 glob 獨立現算相等） |
| 自增：§9.1 C5「指標定義」、§1.3 | － | AC-031-2 | US-005 | AT-031-2-1（1） | 1/1 通過 | PRD:566、:61–65、:69–78 | 通過（M1～M5 五列與判定細則逐字存在；判準自證三項） |
| 自增：§9.1 C6、NFR-SI-07-2 | － | AC-032-1 | US-005 | AT-032-1-1（1） | 1/1 通過 | PRD:567、PRD:444 | 通過（SOP 骨架齊備；啟動條件語意歸 AC-003-1） |

## 2. AC → AT → 測試方法 → 本次結果 → 證據座標（42 個 AT）

測試檔座標均為 `tools/tests/test_selfimproving_check.py`（下表只寫 `類別::函式（行區間）`）；「TCS」欄為該 AT 的 gherkin 區塊在 TCS 檔內的行區間；「深度對照」＝本棒把測試本體逐斷言對照 TCS 的 Given／When／Then（其餘 AT 亦已讀完測試本體並對照，只是未寫入逐項表）；`F-xx` 指向 SCG-4 報告 §4 的發現。

| AC | AT | 類型 | 測試方法（類別::函式與行區間） | `-k` 判定指令 | 本次結果（單跑，逐字） | 證據座標 |
|----|----|------|------------------------------|--------------|----------------------|----------|
| AC-001-1 | AT-001-1-1 | Integration | `TestLedgerRowRules::test_AT_001_1_1_baseline_is_green`（`:693–717`） | `AT_001_1_1` | 1 passed in 0.73s | TCS `:355–369` |
| AC-001-1 | AT-001-1-E-1 | Unit | `TestLedgerRowRules::test_AT_001_1_E_1_time_and_tz`（`:719–753`） | `AT_001_1_E_1` | 1 passed, 4 subtests passed in 1.34s | TCS `:373–390` |
| AC-001-1 | AT-001-1-E-2 | Unit | `TestLedgerRowRules::test_AT_001_1_E_2_required_fields_and_coordinates`（`:755–800`） | `AT_001_1_E_2` | 1 passed, 10 subtests passed in 2.26s | TCS `:394–413`；深度對照 |
| AC-001-1 | AT-001-1-E-3 | Unit | `TestLedgerRowRules::test_AT_001_1_E_3_enums`（`:802–834`） | `AT_001_1_E_3` | 1 passed in 1.52s | TCS `:417–438` |
| AC-001-1 | AT-001-1-E-4 | Unit | `TestLedgerRowRules::test_AT_001_1_E_4_structure`（`:836–903`） | `AT_001_1_E_4` | 1 passed, 6 subtests passed in 1.66s | TCS `:442–465` |
| AC-001-1 | AT-001-1-E-5 | Unit | `TestLedgerRowRules::test_AT_001_1_E_5_bytes_ctrl_crlf_volume`（`:905–959`） | `AT_001_1_E_5` | 1 passed in 2.20s | TCS `:469–489`；深度對照、見 F-05 |
| AC-001-1 | AT-001-1-E-6 | Integration | `TestLedgerRowRules::test_AT_001_1_E_6_fixed_sha`（`:961–994`） | `AT_001_1_E_6` | 1 passed in 1.20s | TCS `:493–512` |
| AC-001-2 | AT-001-2-1 | Unit | `TestLedgerRowRules::test_AT_001_2_1_guard_face_exposure`（`:996–1025`） | `AT_001_2_1` | 1 passed in 0.97s | TCS `:516–531`；深度對照、見 F-05 |
| AC-001-3 | AT-001-3-1 | Integration | `TestMigration::test_AT_001_3_1_chain_is_exempt`（`:1029–1060`） | `AT_001_3_1` | 1 passed in 0.77s | TCS `:535–550` |
| AC-001-3 | AT-001-3-E-1 | Integration | `TestMigration::test_AT_001_3_E_1_no_sha_not_exempt`（`:1062–1087`） | `AT_001_3_E_1` | 1 passed, 2 subtests passed in 1.06s | TCS `:554–569` |
| AC-001-3 | AT-001-3-E-2 | Integration | `TestMigration::test_AT_001_3_E_2_confirm_row_variants`（`:1089–1114`） | `AT_001_3_E_2` | 1 passed, 7 subtests passed in 3.58s | TCS `:573–587`；深度對照、見 F-07 |
| AC-001-3 | AT-001-3-E-3 | Integration | `TestMigration::test_AT_001_3_E_3_invalid_sha`（`:1116–1149`） | `AT_001_3_E_3` | 1 passed, 6 subtests passed in 1.76s | TCS `:591–606`；深度對照 |
| AC-001-3 | AT-001-3-E-4 | Integration | `TestMigration::test_AT_001_3_E_4_orig_rules`（`:1151–1187`） | `AT_001_3_E_4` | 1 passed in 1.84s | TCS `:610–629`；深度對照、見 F-03 |
| AC-002-1 | AT-002-1-1 | Unit | `TestMarksAndProvenance::test_AT_002_1_1_marks`（`:1193–1223`） | `AT_002_1_1` | 1 passed in 1.14s | TCS `:633–651` |
| AC-002-2 | AT-002-2-1 | Unit | `TestMarksAndProvenance::test_AT_002_2_1_provenance`（`:1225–1260`） | `AT_002_2_1` | 1 passed, 5 subtests passed in 2.36s | TCS `:655–671` |
| AC-003-1 | AT-003-1-1 | Unit | `TestScopeAndSop::test_AT_003_1_1_no_resident_mechanism`（`:1264–1320`） | `AT_003_1_1` | 1 passed in 0.14s | TCS `:675–690`；深度對照、見 F-07；語意見 F-01 |
| AC-003-2 | AT-003-2-1 | Unit | `TestScopeAndSop::test_AT_003_2_1_below_floor_is_ne`（`:1322–1344`） | `AT_003_2_1` | 1 passed in 1.52s | TCS `:694–709` |
| AC-003-3 | AT-003-3-1 | Unit | `TestScopeAndSop::test_AT_003_3_1_output_count_not_a_reason`（`:1346–1355`） | `AT_003_3_1` | 1 passed in 0.14s | TCS `:713–727` |
| AC-004-1 | AT-004-1-1 | Integration | `TestReferences::test_AT_004_1_1_existing_references`（`:1413–1422`） | `AT_004_1_1` | 1 passed in 0.60s | TCS `:731–745` |
| AC-004-1 | AT-004-1-E-1 | Integration | `TestReferences::test_AT_004_1_E_1_dangling_obs`（`:1424–1466`） | `AT_004_1_E_1` | 1 passed, 5 subtests passed in 1.66s | TCS `:749–767`；深度對照 |
| AC-004-1 | AT-004-1-E-2 | Integration | `TestReferences::test_AT_004_1_E_2_dangling_def`（`:1468–1486`） | `AT_004_1_E_2` | 1 passed in 0.96s | TCS `:771–786` |
| AC-004-1 | AT-004-1-E-3 | Integration | `TestReferences::test_AT_004_1_E_3_carriers_not_established`（`:1488–1507`） | `AT_004_1_E_3` | 1 passed in 0.93s | TCS `:790–805` |
| AC-004-2 | AT-004-2-1 | Unit | `TestScopeAndSop::test_AT_004_2_1_real_defect_is_def`（`:1357–1360`） | `AT_004_2_1` | 1 passed in 0.13s | TCS `:809–822` |
| AC-004-3 | AT-004-3-1 | Integration | `TestHistory::test_AT_004_3_1_legal_evolution`（`:1513–1542`） | `AT_004_3_1` | 1 passed in 1.15s | TCS `:826–842` |
| AC-004-3 | AT-004-3-E-1 | Integration | `TestHistory::test_AT_004_3_E_1_in_place_rewrites`（`:1544–1584`） | `AT_004_3_E_1` | 1 passed in 1.32s | TCS `:846–862`；深度對照 |
| AC-004-3 | AT-004-3-E-2 | Integration | `TestHistory::test_AT_004_3_E_2_worktree_rewrites`（`:1586–1609`） | `AT_004_3_E_2` | 1 passed in 1.27s | TCS `:866–884` |
| AC-004-3 | AT-004-3-E-3 | Integration | `TestHistory::test_AT_004_3_E_3_no_history_and_outside`（`:1611–1629`） | `AT_004_3_E_3` | 1 passed in 0.79s | TCS `:888–903` |
| AC-029-1 | AT-029-1-1 | Unit | `TestScopeAndSop::test_AT_029_1_1_friction_entry`（`:1362–1370`） | `AT_029_1_1` | 1 passed in 0.14s | TCS `:907–920` |
| AC-029-2 | AT-029-2-1 | Unit | `TestScopeAndSop::test_AT_029_2_1_loop_self`（`:1372–1383`） | `AT_029_2_1` | 1 passed in 0.14s | TCS `:924–938` |
| AC-030-1 | AT-030-1-1 | Integration | `TestCli::test_AT_030_1_1_output_contract`（`:1661–1742`） | `AT_030_1_1` | 1 passed in 1.45s | TCS `:942–961`；深度對照、見 F-04、F-05 |
| AC-030-1 | AT-030-1-E-1 | Unit | `TestCli::test_AT_030_1_E_1_usage_errors`（`:1744–1778`） | `AT_030_1_E_1` | 1 passed, 11 subtests passed in 0.44s | TCS `:965–982` |
| AC-030-2 | AT-030-2-1 | Integration | `TestCli::test_AT_030_2_1_purity`（`:1780–1878`） | `AT_030_2_1` | 1 passed in 1.72s | TCS `:986–1003`；深度對照、見 F-07 |
| AC-030-3 | AT-030-3-1 | Unit | `TestCli::test_AT_030_3_1_fingerprint`（`:1880–1917`） | `AT_030_3_1` | 1 passed in 1.61s | TCS `:1007–1023` |
| AC-030-3 | AT-030-3-2 | Unit | `TestCli::test_AT_030_3_2_obs_draft`（`:1919–1967`） | `AT_030_3_2` | 1 passed in 1.24s | TCS `:1027–1046` |
| AC-031-1 | AT-031-1-1 | Unit | `TestParams::test_AT_031_1_1_real_params`（`:1973–2002`） | `AT_031_1_1` | 1 passed in 0.61s | TCS `:1050–1066` |
| AC-031-1 | AT-031-1-E-1 | Unit | `TestParams::test_AT_031_1_E_1_missing_keys`（`:2004–2039`） | `AT_031_1_E_1` | 1 passed, 23 subtests passed in 4.67s | TCS `:1070–1084` |
| AC-031-1 | AT-031-1-E-2 | Unit | `TestParams::test_AT_031_1_E_2_glob_consistency`（`:2041–2090`） | `AT_031_1_E_2` | 1 passed, 7 subtests passed in 1.98s | TCS `:1088–1105`；深度對照 |
| AC-031-1 | AT-031-1-E-3 | Unit | `TestParams::test_AT_031_1_E_3_coupling`（`:2092–2126`） | `AT_031_1_E_3` | 1 passed in 1.81s | TCS `:1109–1127` |
| AC-031-1 | AT-031-1-E-4 | Unit | `TestParams::test_AT_031_1_E_4_types`（`:2128–2146`） | `AT_031_1_E_4` | 1 passed in 0.75s | TCS `:1131–1145` |
| AC-031-1 | AT-031-1-E-5 | Unit | `TestParams::test_AT_031_1_E_5_ranges`（`:2148–2164`） | `AT_031_1_E_5` | 1 passed in 0.76s | TCS `:1149–1163` |
| AC-031-2 | AT-031-2-1 | Unit | `TestParams::test_AT_031_2_1_metrics_verbatim`（`:2166–2192`） | `AT_031_2_1` | 1 passed in 0.14s | TCS `:1167–1181` |
| AC-032-1 | AT-032-1-1 | Unit | `TestScopeAndSop::test_AT_032_1_1_sop_skeleton`（`:1385–1407`） | `AT_032_1_1` | 1 passed in 0.14s | TCS `:1185–1199` |

備註：各 `-k` 皆恰選到 1 個測試（每個單跑輸出為 `1 passed, 41 deselected …`，上表省略 `41 deselected`）；Developer 交卷沒有逐 AT 列出驗收字樣 `[AT_OK_…]`（F-06），故上表的逐 AT 單跑輸出是本棒補上的機器證據。

## 3. PRD §8.1 P0 退出條件 (a)～(d) 對照（TCS §6）

| 退出條件 | 對應 AT 與實跑檢核 | 本次結果 |
|----------|-------------------|----------|
| (a) 免追問必填欄 | AT-001-1-1、AT-001-1-E-1～E-5、AT-001-2-1、AT-002-2-1；V9 | 通過：AT 全綠；V9 檢視 N 之後新增的 12 列（051～062）皆 9 欄有值、無「某欄無法填」的反症狀 |
| (b) 自遷移基準起 `check` 綠 | AT-001-3-1、AT-004-3-1；V1、V2、V4 | 通過：HEAD 的 `check` rc 0（`overall=PASS`，62 列，唯一 NE 為 nonblocking 的載體項） |
| (c) 處置合枚舉且 `orig` 保全 | AT-001-1-E-3、AT-001-3-E-4；V3 | 部分：V3 (1)～(8) 通過（ID／時間／情境／症狀／分類／嚴重度逐格相同、座標只前綴追加 3 列、50 列處置皆有 `orig` 且逐字相同、`fixed@` 8 列 sha 語意核對無誤）；V3 (9) 座標可重查未通過（F-02） |
| (d) 零無座標列、零「之後再看」 | AT-001-1-E-2、AT-001-1-E-3；V2 | 通過：`row.coordinates` 與 `row.enums` PASS；獨立重判 27 個判定碼 0 命中；「之後再看」只出現在檔頭〈規則〉的禁令敘述，處置欄命中 0 列 |

## 4. 實跑檢核 V1～V9 摘要（逐字輸出見 SCG-4 報告 §2）

| 編號 | 檢核 | 結果 | 備註 |
|------|------|------|------|
| V1 | 提交鏈 | 通過 | T→M→N→X；M 恰動帳本與附註檔；N 恰動 `params.json` 一鍵與帳本一列 |
| V2 | 真帳本 `check --json` | 通過 | rc 0、62 列、21 項；獨立重判一致 |
| V3 | M 稽核 (1)～(9) | **未通過（僅 (9)）** | 第 047 列的檔案路徑不存在（F-02）；020、030、043 為軟性問題 |
| V4 | `migration_base_sha` | 通過 | 值等於 M 的完整 sha；祖先 rc 0 |
| V5 | 確認列引言座標 | 通過 | line 2476、2581 皆 `type=user`＋`origin.kind=human`，文字逐字相符 |
| V6 | `params.json` 初值 | 通過 | 23 鍵逐鍵相符；25 項 glob 獨立現算相等 |
| V7 | 護欄與零退化 | 通過 | 根層全套 rc 0（發現 5426、skip 46 皆已標籤）；ruff、LOC、缺陷編號引用鎖（11 passed）全綠；工作樹與 `.claude` 零改動；凍結三檔不變；`check` 牆鐘最大 1.077s |
| V8 | SOP 與流程型 AC 文件檢核 | **未通過** | SOP〈啟動條件〉(b)(c)(d)(e) 與 PRD AC-SI-03-1 語意不符（F-01）；Developer 5 項流程摩擦全數入帳 |
| V9 | N 之後只追加 | 通過 | 單一 commit、單一 hunk、純追加 11 列、0 行刪改 |

## 5. NFR-P0-1～8 追溯

| NFR | 內容 | 驗證方式與本次結果 | 結論 |
|-----|------|-------------------|------|
| NFR-P0-1 | 純度與零副作用 | AT-030-2-1 通過；本棒以 grep 驗證 `tools/selfimproving.py` 與 `tools/lib/si_*.py` 零命中 `os.system`、`os.popen`、`check_output`、`sys.platform`、`.reconfigure(` | 通過 |
| NFR-P0-2 | 效能 | 真 repo 三次牆鐘 1.077s／1.044s／1.033s（門檻 < 30s）；合成 repo 的單次 `check` 為亞秒級；整檔 38.41s（本機），根層平行 worker 內 81.0s（門檻 < 180s，CI 未驗） | 通過（CI 端未驗） |
| NFR-P0-3 | 跨平台 | Windows 實跑；`tools/selfimproving.py` 與 `si_*.py` 無單平台 API；rooted 路徑在 Windows 與 POSIX 行為不同（F-03）；macOS 未驗 | 部分（F-03、macOS 未驗） |
| NFR-P0-4 | 根層護欄相容 | 測試檔無 skip、skipTest、skipIf、xfail（grep 僅命中區域變數名 `skip`）；文字檔 I/O 皆帶 encoding；根層全套 rc 0 | 通過 |
| NFR-P0-5 | LOC 分級 | `check_loc_budget.py --json` rc 0，`total_violation=False`，四個 violations 陣列皆空 | 通過 |
| NFR-P0-6 | 靜態檢查 | `ruff check` 9 個新 `.py`：`All checks passed!` | 通過 |
| NFR-P0-7 | 測試 hermetic | AT 只用 tmp 合成 repo（`mock.patch.dict(os.environ, …)` 淨化 `GIT_*`）；不讀真帳本；`ref.obs` PASS 與 `test_defect_id_reference_integrity.py`（11 passed）證明無不存在的字面編號；`git diff --name-only` 為空 | 通過 |
| NFR-P0-8 | 範圍守衛 | `.claude/**` 零改動、凍結檔（PRD、TCS、研究方法 SOP）digest 不變；T 提交含 §5.6 以外 8 檔，皆為主控收尾的重釘、CI paths 與 guard-total 站點連動（F-13；重釘走一次性例外見 F-10） | 通過（附註） |

## 6. R 條文 → AT 對映與缺口（含突變試驗）

「突變」欄：本棒在 scratchpad 複本對生產碼做單點突變（22 個），被對應 AT 殺掉者標「殺」，仍全綠者標「存活」＝該規則面沒有 AT 鑑別（見 SCG-4 報告 §3）。

| R | 內容 | 觸及它的 AT | 突變／缺口 |
|---|------|------------|-----------|
| R1 | 介面、rc 表 | AT-030-1-1、AT-030-1-E-1、AT-003-1-1（`status`、`prop-new` rc 3）、AT-001-1-E-6（rc 2） | — |
| R2 | 路徑（相對 `--repo`） | AT-030-1-1（誘餌檔）、AT-004-3-E-3（repo 外絕對路徑） | — |
| R3 | 文字形態 | AT-001-1-1（首行、`overall=` 行）、AT-030-1-1（項目行） | finding 行文法與 `[warn]` 前綴、NE 的 `blocking`／`nonblocking`：存活（F-04、F-05）；黑箱探測已補驗符合 |
| R4 | JSON 形態 | AT-030-1-1（四層鍵序）、AT-001-1-1 | — |
| R5 | 狀態語意 | AT-001-1-1、AT-001-1-E-6、AT-004-1-E-3、AT-031-1-E-1 | 突變 M-T（載體 NE 改 blocking）殺 |
| R6 | OBS 草稿列 | AT-030-3-2 | 突變 M-R（ID 不加一）殺；名額被 nonblocking NE 占用見 F-12 |
| R7 | 判準指紋 | AT-030-3-1（測試內獨立重算） | 突變 M-L（不做 CRLF 正規化）殺 |
| R8 | 純度與零副作用 | AT-030-2-1 | 突變 M-K（拿掉 timeout）殺 |
| R9 | 列識別與切分 | AT-001-1-E-4、AT-001-1-E-1 | 突變 M-I（拿掉 `ROW-ID-DUP`）殺 |
| R10 | 時間文法 | AT-001-1-E-1 | — |
| R11 | 位元組與控制字元 | AT-001-1-E-5 | 突變 M-B（邊界 `>` 改 `>=`）殺 |
| R12 | 必填欄 | AT-001-1-E-2 | — |
| R13 | 分類、嚴重度、處置 | AT-001-1-E-3 | 突變 M-Q（retired 缺座標不再判）殺 |
| R14 | 標記欄 | AT-002-1-1 | — |
| R15 | 面、暴露、來源、回報者 | AT-001-2-1、AT-002-2-1 | 守衛面 P2＋暴露＝無：突變 M-N 存活（F-05） |
| R16 | 座標形態 | AT-001-1-E-2、AT-001-1-1 | — |
| R17 | `fixed@` 解析 | AT-001-1-E-6 | 突變 M-S（一律視為已解析）殺 |
| R18 | 引用完整性 | AT-004-1-1、AT-004-1-E-1～E-3、AT-001-3-E-4 | 突變 M-M 殺；(c) 路徑逃逸（`..`、絕對、rooted）：M-F、M-F2 存活（F-03） |
| R19 | 遷移豁免 | AT-001-3-1、AT-001-3-E-1～E-4 | 突變 M-D、M-E、M-P 殺 |
| R20 | ROW-MUTATED | AT-004-3-1、AT-004-3-E-1～E-3、AT-001-3-E-1 | 突變 M-C、M-O 殺 |
| R21 | `params.json` 對表 | AT-031-1-1、AT-031-1-E-1、AT-031-1-E-4、AT-031-1-E-5 | 突變 M-J（比例上界）殺 |
| R22 | 耦合與 glob 一致性 | AT-031-1-E-2、AT-031-1-E-3、AT-029-2-1 | — |
| R23 | 反空轉與體積 | AT-003-2-1、AT-001-1-E-5 | 突變 M-A（fail 邊界）殺 |
| R24 | 協定目錄 | AT-031-1-1（params 檔形態）、AT-031-2-1（metrics 逐字） | — |
| R25 | SOP 骨架 | AT-032-1-1、AT-003-1-1、AT-003-2-1、AT-003-3-1、AT-004-2-1、AT-029-1-1、AT-029-2-1、AT-004-3-1 | 只判關鍵片段；語意由 V8 判，現有偏離見 F-01 |
| R26 | 範圍守衛 | AT-003-1-1、AT-030-2-1（靜態） | — |

## 7. 覆蓋率統計

| 指標 | 數值 |
|------|------|
| 總 AC 數 | 19（PRD 13＋TCS 自增 6） |
| 有 AT 的 AC 數 | 19 |
| **AC→AT 映射覆蓋率** | **100%**（TCS §1；本棒機械抽取驗證：FRD-lite 的 AC 集合與 §1 映射的 AC 集合相等） |
| AT 數 | 42（E 類 22；Integration 17；Unit 25） |
| 有測試函式的 AT | 42/42（每個 AT 恰一個測試函式，名稱含其底線形） |
| 整檔實跑 | `42 passed, 86 subtests passed in 38.41s`（rc 0） |
| 逐 AT 單跑（TCS 判定指令） | 42/42 為 `1 passed`（含子測試），rc 0，每個 `-k` 恰選到 1 個測試 |
| 根層全套 unittest | rc 0；發現 5426 個測試（下限 5326）；skip 46 支皆已標籤；`test_selfimproving_check` 於平行 worker 內 81.0s |
| 突變鑑別力 | 22 個手選突變：16 個被殺、6 個存活（R18 (c) 路徑逃逸 2、R3 `[warn]`、R3 finding 行、R3 NE 字樣、R15 P2＋暴露＝無各 1） |
| AC 層結案 | 17/19：未結案者 AC-001-3（V3 (9)，F-02）、AC-003-1（V8，F-01） |
| AT→CI Pipeline | 經根層 unittest 閘門本機實跑 rc 0；GitHub Actions 端（含 T 增列的兩支 compat-ci `paths`）未驗 |
| 平台 | Windows 實跑；macOS／POSIX 未驗（NFR-SI-06-5） |
| 發現統計 | P1＝0；P2＝2；P3＝3；P4＝9（SCG-4 報告 §4） |
| Developer 驗收字樣 | 0/42 列出（F-06）；由本棒逐 AT 單跑補證 |

**未覆蓋與待補（供下一輪）**：(1) F-03 的路徑逃逸、F-04／F-05 的文字形態斷言、P2＋暴露＝無等規則面缺口，建議補 AT；(2) F-01、F-02 修復後須複驗 V8 與 V3 (9)；(3) POSIX 與 CI 端實跑。
