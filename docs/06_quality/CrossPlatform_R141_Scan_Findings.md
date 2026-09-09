# CrossPlatform R141 — DEF-200-274 第八輪：四方獨立複審修復收尾

- **輪籤**：R141（2026-09-09，macOS；主控收尾單人窗口，單人 agent 執行）。
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R140（DEF-200-274 第七輪，見 `CrossPlatform_R140_Scan_Findings.md`）。
  commit 9478bda push 後，四方（Architect/SA/SD/QA）各自不共享上下文獨立審查
  第七輪的產出，找到本輪要修的具體缺口。

---

## §1 護欄層淨額承認

<!-- guard-total:R141 --> R141 護欄層累積淨額＝ 96240 → 96451（+211，全額歸回歸鎖軌）——
`test_run_root_unittests.py` 新增 `WorkerCountFormulaTest`（`worker_count()` 公式／
環境變數覆寫／非法值退回四條路徑的直接單元測試，SD／QA 共同點名此前全數靠 mock
換掉函式本體，零覆蓋）與 `ReportDispatchImbalanceTest` 兩支新測試（`GITHUB_ACTIONS=
true` 時 `dispatch_imbalance.report_dispatch_imbalance()` 印出 GitHub Actions 原生
`::warning::` annotation，+129）；`test_smoke_ci_sync.py` 新增
`TestParallelTestsCiWiring`（三支 compat-CI 呼叫 `run_root_unittests.py` 的 step
是否設 `AUTOSDD_PARALLEL_TESTS=1` 的機械回歸鎖，SA 點名此前零覆蓋，+46）；本檔
（`test_adr_xplat001_c1c2_lock.py`）自身逐檔漂移 +36（新增主表本列＋回歸鎖軌新列＋
`_REPIN_NET_CAP_SCHEDULE` 到期義務兌現列＋`_PHASE2_REVIEW_LOG` 新列＋
`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列的行數）。逐項見 `_GUARD_LINES_REPIN_LOG`／
`_REGRESSION_LANE_LOG` 的 R141 列。

## §2 本輪找到什麼（四方獨立複審，各自不共享上下文）

對 commit 9478bda（三支 CI workflow 接上平行測試模式）push 後的真實 CI 結果與
第七輪產出各自獨立審查：

- **CI 真實結果**：windows-compat-ci 與 macos-compat-ci 皆 success（windows 是本
  機制第一次在 Windows 真機驗證成功）；root-infra-ci failure——根因為
  `tools/run_root_unittests.py` 撞上 special-tier LOC 棘輪（775 行預算，因平行
  失敗印出／`worker_count()` 退化路徑兩處修復各加了幾行而超額 13 行）。
- **SD／QA 共同點名**：`ParallelFallbackToSequentialTest` 等既有測試全數用
  `mock.patch.object(parallel_shard, "worker_count", ...)` 整個換掉函式本體，從未
  直接呼叫 `worker_count(cpu_count=N)` 斷言公式輸出（`max(1, min(8, cpu-1))`）、
  環境變數覆寫合法值／非法值兩條路徑，公式本身零覆蓋。
- **SA 點名**：CI 已接上 `AUTOSDD_PARALLEL_TESTS=1`，但零測試覆蓋，未來可能被
  無聲刪除而無人發現；`AutoClaude/tools/run_local_nightly.sh`／`run_local_nightly.
  ps1` 兩支本機 nightly 腳本呼叫 `run_root_unittests.py` 時未設同一開關，與
  使用者原始訴求①「本機收尾驗證也不該被拖慢」最直接對應的場景反而漏接。
- **SA 提出方向、本輪落地**：`dispatch_imbalance.report_dispatch_imbalance()`
  偵測到不均時，CI 上應額外印一行 GitHub Actions 原生 `::warning::` annotation，
  直接顯示在 run 摘要頁面，不需人工捲動冗長 log。

## §3 修復（收尾單人窗口，逐條落地）

1. **special-tier LOC 超額**：`tools/run_root_unittests.py` 兩段新增的 WHY 註解
   壓成單行行內指標式註解（完整 WHY 全文即本節），775→777；`AutoClaude/tools/
   check_loc_budget.py` 的 `SPECIAL_FILES` 棘輪具名調高 775→777（已確認無法在
   不刪除已驗證功能或動無關程式碼的前提下再壓縮）。
2. **`worker_count()` 公式直接單元測試**：新增 `WorkerCountFormulaTest`（4 個測試：
   跨 cpu_count 公式表、合法覆寫勝過公式、非法值退回公式、`cpu_count=None` 落在
   `[1, 8]` 值域）。
3. **CI 接線回歸鎖**：新增 `TestParallelTestsCiWiring`（`test_smoke_ci_sync.py`），
   以 `yaml.safe_load` 解析三支 compat-CI，斷言呼叫 `run_root_unittests.py` 的
   step 帶 `AUTOSDD_PARALLEL_TESTS=1`；連帶把 `test_smoke_ci_sync` 加入
   `min_tests_margin.PREREQ_DEPENDENT_MODULES`（新增 `import yaml` 使該模組在零
   相依沙箱同樣會塌）。
4. **兩支本機 nightly 腳本補開關**：`run_local_nightly.sh` 改用
   `env AUTOSDD_PARALLEL_TESTS=1 "$PY" ...`；`run_local_nightly.ps1` 在呼叫前後
   暫時設值／還原（`try/finally`），不外溢到其餘 stage。
5. **GitHub Actions annotation**：`dispatch_imbalance.report_dispatch_imbalance()`
   偵測到不均時，`GITHUB_ACTIONS=true` 才額外逐筆印 `::warning::` 行；新增
   `test_github_actions_env_adds_warning_annotation`／
   `test_non_ci_env_has_no_warning_annotation` 兩支回歸鎖。

## §4 誠實劃界（本輪仍未解決）

- **不可宣稱本輪修復後 CI 會轉綠**——special-tier LOC 修復尚未經過新的 CI run
  驗證（修復尚未 push）；已本機驗證乾淨，待下次 CI run 驗證。
- `ratio_threshold=1.5` 仍寫死、不可由環境變數覆寫（延續第七輪誠實劃界）。
- `AutoClaude/tests/`／`AISDLC_SDD` 的 pytest 套件仍不受本機制惠及。

逐項見 `docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`
〈第八輪〉節；缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274。
