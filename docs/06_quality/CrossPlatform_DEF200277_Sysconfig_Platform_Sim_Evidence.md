# DEF-200-277 證據檔：跨平台假設 meta-test 撞見 sysconfig 快取暖機時機而誤報

> 本檔為 `docs/06_quality/AutoSDD_Defect_Log.md` 該列的體積守門接收端（`ROW_MAX_BYTES` 洩壓）；
> 列上只留一句話與本檔指針，逐字原文住這裡。

## 現象（2026-09-10 人工比對雲端 CI log 發現）

main 分支最近兩次 push（`9478bda`、`f61cb45`，皆為 DEF-200-274 系列第七、八輪）在雲端
`root-infra-ci` workflow 都失敗，即使本地 pre-push 檢查全綠。以 `f61cb45` 這次
（run https://github.com/wuweihungmobile/AISDCL_Agent/actions/runs/34379279445）為例，
失敗於「unittest（tools/tests/：...）」步驟：

```
FAIL: test_doc_loc_baseline_freshness_r60.TestR67R3ThisFileMakesNoUnstatedPlatformAssumption.test_every_lock_in_this_file_holds_under_every_simulated_platform
AssertionError: {'darwin': ["ERROR test_doc_loc_baseline_f[174 chars]u'"]} != {}
- {'darwin': ['ERROR '
-             'test_doc_loc_baseline_freshness_r60.TestHistoricalWaiverHasStaleSelfCheck.test_real_specs_have_no_stale_registrations '
-             ':: ModuleNotFoundError: No module named '
-             "'_sysconfigdata__darwin_x86_64-linux-gnu'"]}
```

`TestR67R3ThisFileMakesNoUnstatedPlatformAssumption`（第 2320~2365 行）把 `sys.platform`
依序改成假值（`_NEUTRALITY_PLATFORMS = ("darwin", "linux", "win32")`），重跑整個檔案的
sibling 測試套件，驗證結果不因 `sys.platform` 改變。這次在模擬 `sys.platform='darwin'`
（tuple 第一個元素，最先被模擬）時，完全無辜的
`TestHistoricalWaiverHasStaleSelfCheck.test_real_specs_have_no_stale_registrations`
（第 966~975 行；業務邏輯是檢查 ONBOARDING.md 的歷史豁免登記沒有 stale）炸出
`ModuleNotFoundError: No module named '_sysconfigdata__darwin_x86_64-linux-gnu'`。

## 根因（已查驗，非猜測）

CPython 的 `sysconfig.get_config_vars()` 在整個 Python 行程內**第一次**被呼叫時，會用
當下的 `sys.platform` 動態組出 `_sysconfigdata_<abi>_<platform>_<multiarch>` 這個模組名
並 `import` 它，結果快取進模組層級的 `_CONFIG_VARS`；之後同一行程內所有呼叫都直接讀
快取，不再重算。若這個「行程內第一次」恰好落在 `sys.platform` 已被本檔的模擬迴圈改成
假值期間，組出來的名字會是「假平台（`darwin`）＋真 multiarch（CI runner 是 ubuntu，
真實值 `x86_64-linux-gnu`）」這種現實中從未編譯存在過的組合，import 必然失敗——這與
`test_real_specs_have_no_stale_registrations` 自身的業務邏輯（也與 DEF-200-274 系列在
修的「LOC 棘輪超額」問題，見 `docs/06_quality/CrossPlatform_R141_Scan_Findings.md`）
完全無關，是兩個獨立問題；R141 那份文件也沒有記錄過這個 ModuleNotFoundError，
確認是本輪才發現的新缺陷。

`_NEUTRALITY_PLATFORMS` 把 `"darwin"` 排在第一個，這解釋了為什麼 CI 的失敗字典只有
`darwin` 這個 key（`linux`／`win32` 兩個後續迭代沒有再次觸發，因為那次失敗的 import
嘗試已經讓 Python 走過一次 `_get_sysconfigdata_name()` 路徑）。

本機 macOS 因為在啟用 venv 之後啟動 Python（`site` 模組初始化流程本身重度依賴
`sysconfig`），這個快取在測試開始前早已被暖機過，所以本機重現不了此症狀——`sys.platform`
改成 `'darwin'`（本機真實平台本來就是 darwin）、`'linux'`、`'win32'` 三種模擬皆不會
觸發任何錯誤（已實測 `python -m unittest
test_doc_loc_baseline_freshness_r60.TestR67R3ThisFileMakesNoUnstatedPlatformAssumption -v`
在本機為 `OK`）。

## 修法（已採取）

`tools/tests/test_doc_loc_baseline_freshness_r60.py:2340`：在
`test_every_lock_in_this_file_holds_under_every_simulated_platform` 改
`sys.platform` 之前，先呼叫一次 `sysconfig.get_config_vars()` 用真實平台值暖機快取，
之後全部模擬迭代都吃快取、不再觸發動態 import。這是修「本測試自身模擬手法的副作用」，
不是修 `TestHistoricalWaiverHasStaleSelfCheck` 的業務邏輯（那支測試本身沒有做任何
平台假設，是無辜被撞見的旁觀者）。

同檔新增 `TestDEF200277SysconfigWarmedBeforePlatformSimulation`（第 2381 行起）：源碼
順序回歸鎖，斷言暖機呼叫的字串位置早於 `for fake in _NEUTRALITY_PLATFORMS:` 迴圈——
不依賴能在本機真的重現「假平台 × 真 multiarch」這個只有 CI 的 Linux runner 上才成立
的組合，改用「暖機呼叫必須在迴圈之前」這個可在任何平台上驗證的結構性不變量頂替行為重現。

## 測試（實測輸出）

```
$ python -m unittest test_doc_loc_baseline_freshness_r60 -v   # (cd tools/tests；已 source venv)
Ran 278 tests in ~155s
OK
```

`tools/run_root_unittests.py` 整套（4054+ 支，`unset AUTOSDD_PARALLEL_TESTS
AUTOSDD_PARALLEL_TESTS_WORKERS` 後序列跑）：本輪修復本身相關的測試（本檔＋
`test_defect_id_reference_integrity`）皆綠；殘留項見下。

## 殘留待收尾處理（未在本輪自行處理，依 repo 並行派工紀律）

1. **護欄層行數棘輪**：`tools/tests/test_doc_loc_baseline_freshness_r60.py` 本輪淨增
   30 行（暖機呼叫＋WHY 註解＋新回歸鎖類別），觸發 `test_adr_xplat001_c1c2_lock.py` 的
   `TestGuardLayerRatchet`／`TestShrinkOnlyRatchet`（現況需零違規）。CLAUDE.md 鐵律七＋
   該鎖斷言訊息本身皆明載「重釘 `_FROZEN_GUARD_LINES`／`_GUARD_LINES_REPIN_LOG` 一律由
   收尾單人窗口在所有並行包停工後做一次」，本 fork 是並行工作單元，未自行重釘。收尾時
   請跑 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`（或該檔
   對等入口）取得新基線，並在 `_GUARD_LINES_REPIN_LOG` 補一列（含淨額 +30 與本 DEF 編號
   當理由）。
2. **`test_root_infra_parity.TestRootToolsRuffHasExecutors` 兩支測試失敗**：與本缺陷無關，
   是同一輪另一項改動（`tools/git-hooks/pre-push` 把裸 `ruff check tools/ .claude/hooks/`
   改成候選鏈變數 `"$RUFF_BIN" check ...`，修的是 venv 未啟用時 pre-push 找不到 ruff 的
   環境問題）造成的副作用——該測試的執行者偵測正則只認裸 `ruff check tools/` 字面，
   認不出變數形態的呼叫。此非本 DEF-200-277 的範圍，留給處理該 pre-push 改動的窗口
   同步更新偵測正則或改用另一種能同時滿足兩邊的寫法。
