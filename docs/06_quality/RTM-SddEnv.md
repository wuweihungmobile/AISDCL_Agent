# RTM - SddEnv（G-116-12：SDD 外部專案模式三件組產生器）

**版本**: 1.0（整合輪 116 W3 QA 建立；依 `AISDLC_SDD:rtm-generate` 表格形，路徑依 D-116-09 落 `docs/06_quality/`）
**日期**: 2026-10-18
**狀態**: In Review（SCG-4 一審有 P2：F-02，見 `SCG4-REVIEW-SddEnv-20261018.md`；RTM 覆蓋已達 100%，`RTM_VERIFY` 閘門待二審通過後執行）
**覆蓋率**: 5/5 AC（100%）；AT 9/9
**規格**: `docs/03_testing/contracts/TCS-SddEnv-20261018.md`（凍結摘要 `sha256:cc0988beef137f6fa3222513f176afb8890bd53d9af6b1b7fec689258c820d5a`）
**實作**: commit `343d583a`（`AISDLC_SDD/scripts/sdd_env.py`、`AISDLC_SDD/scripts/tests/test_sdd_env.py`）＋主控修補 `e73749bf`

## 追溯矩陣

| EPIC | Feature | User Story | AC | Test Case（`AISDLC_SDD/scripts/tests/test_sdd_env.py::`） | API | NFR | 狀態 |
|------|---------|-----------|-----|---------------------------------------------------------|-----|-----|------|
| EPIC-001（整合輪 116：SDD 外部專案模式可重複；來源 G-116-12、D-116-04） | F-001 | US-001 | AC-001-1 | AT-001-1-1 → `test_AT_001_1_1_default_root_and_json_shell` | － | NFR-001-3 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-1 | AT-001-1-2 → `test_AT_001_1_2_state_dir_table_for_each_sub`（4 個參數）、`test_AT_001_1_2_relative_and_non_ascii_root` | － | NFR-001-3 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-2 | AT-001-2-1 → `test_AT_001_2_1_powershell_lines_and_quote_escaping` | － | NFR-001-3 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-2 | AT-001-2-2 → `test_AT_001_2_2_bash_lines_and_quote_escaping` | － | NFR-001-3 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-3 | AT-001-3-1 → `test_AT_001_3_1_bad_slugs_are_rejected_with_rc_2`（9 個參數）、`test_AT_001_3_1_overlong_slug_is_rejected_with_rc_2` | － | NFR-001-1 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-3 | AT-001-3-2 → `test_AT_001_3_2_reserved_words_and_length_boundaries` | － | NFR-001-1 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-4 | AT-001-4-1 → `test_AT_001_4_1_check_reports_an_existing_state_file` | － | NFR-001-6 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-4 | AT-001-4-2 → `test_AT_001_4_2_check_reports_a_missing_state_file_without_creating_anything` | － | NFR-001-6 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-5 | AT-001-5-1 → `test_AT_001_5_1_failure_boundaries_and_zero_side_effects` | － | NFR-001-1、-6 | ✅ |

## 覆蓋率統計

| 指標 | 數值 |
|------|------|
| 總 Feature 數 | 1 |
| 總 AC 數 | 5 |
| 有 TC 的 AC 數 | 5 |
| **覆蓋率** | **100%** |
| SCG-5 目標 | 100% |
| 實跑（2026-10-18，當回合） | 整檔 22 項通過；`scripts/tests` 421 通過、1 略過（既有 Windows 不可達分支）；`ci-gate.ps1` rc 0（逐軌 1478／2149／421） |

## R 條文 → AT 對映

| R | 內容 | 觸及它的 AT |
|---|------|------------|
| R1 | 介面、rc 表、stdio 重設 | AT-001-5-1（rc）；stdio 重設無斷言（F-02） |
| R2 | 五變數與固定順序 | AT-001-1-1、AT-001-2-1、AT-001-2-2 |
| R3 | 狀態目錄查表 | AT-001-1-2 |
| R4 | `--root`（預設、絕對化、須為目錄） | AT-001-1-1、AT-001-1-2、AT-001-5-1 |
| R5 | 版本（同目錄 `sdd_version`、數值排序、不可解 rc 1） | AT-001-1-2、AT-001-5-1 |
| R6 | `--shell` 三形態與跳脫 | AT-001-1-1、AT-001-2-1、AT-001-2-2 |
| R7 | slug 驗證與檢查順序 | AT-001-3-1、AT-001-3-2；格式先於長度的順序無斷言（F-02） |
| R8 | `--check` | AT-001-4-1、AT-001-4-2 |
| R9 | 純度（不改環境、不建檔） | AT-001-5-1、AT-001-1-2、AT-001-4-x |
| R10 | 輸出分流（失敗時 stdout 空） | AT-001-3-x、AT-001-4-2、AT-001-5-1 |

## NFR 追溯

| NFR | 驗證結果（當回合） |
|-----|------------------|
| NFR-001-1 | 無 subprocess、無檔案 I/O、無時間戳（grep 零命中）；匯入＝標準庫＋同目錄 `sdd_version`＋`rfc_lifecycle_lint`（見備註 1） |
| NFR-001-2 | `main()` 10 次含真實 git 解析，最大 0.049 秒（< 2 秒） |
| NFR-001-3 | 無 `sys.platform` 分支；路徑一律 `os.path.join`。Windows 實跑 `--shell bash` 輸出為 CRLF（SCG-4 F-03，P3） |
| NFR-001-4 | 測試檔無 skip／xfail／平台分支；假根皆 `tmp_path`；`write_text`／`read_text` 帶 encoding |
| NFR-001-5 | ruff 兩檔 All checks passed |
| NFR-001-6 | 測試 hermetic（`tmp_path`、不讀 `SDD_` 環境變數、不碰真實狀態檔）；整檔單跑 rc 0 |
| NFR-001-7 | `scripts/tests` 全綠；範圍＝兩個新檔；樹下限 26→27 由主控於 `e73749bf` 重釘（`int(34×0.8)＝27`） |

## 備註

1. **已知偏離（SCG-4 F-04，P3，主控於 `e73749bf` 接受）**：TCS 的 R1 寫行內 `reconfigure`，R9 與 NFR-001-1 寫「只用標準庫與同目錄 `sdd_version`」；實作改由同目錄 `rfc_lifecycle_lint.force_utf8_stdio()` 重設 stdio（根層 `test_platform_utils_dedup` 的 shrink-only 棘輪不允許再多一份行內實作）。行為等價；TCS 已凍結、不改，本備註為文字面的訂正。
2. **測試強度缺口（SCG-4 F-02，P2）**：R1 的 stdio 重設與 R7 的「格式先於長度」在現有測試下被改壞也不會轉紅；補強限於在既有測試追加一個 spy 斷言與一個參數值。
3. **行尾（SCG-4 F-03，P3）**：Windows 上 stdout 文字模式把 `\n` 寫成 `\r\n`；json 與 powershell 形無妨，bash 形供 Git Bash `eval` 時會黏進 `\r`。
4. 狀態欄 ✅＝測試實跑為綠；整體仍待 SCG-4 二審通過後才算閉環。
