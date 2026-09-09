# CrossPlatform R136 — DEF-200-274 第四輪第二次對抗式複審收斂 round-label-ok

- **輪籤**：R136（2026-09-09，macOS；Developer 角色收尾）
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R135（DEF-200-274 第四輪四方複審收尾，見
  `CrossPlatform_R135_Scan_Findings.md`）。第四輪修復落地並經 Architect／SD／QA
  三方 APPROVE_WITH_CONDITIONS／APPROVE_WITH_CONDITIONS／REJECT 收斂後，同一批
  檔案又跑了第二次四方對抗式複審（Architect／SA／SD／QA），裁決 Architect＝
  REJECT、SA＝APPROVE_WITH_CONDITIONS、SD＝APPROVE、QA＝未回報。本輪為該次複審
  的逐條修復收尾。

---

## §1 護欄層淨額承認

<!-- guard-total:R136 --> 本輪護欄層行數 95762 → 95843（+81，全額歸回歸鎖軌，見
`_REGRESSION_LANE_LOG` 同輪一列 81，貼齊本輪主表淨額，扣除後款(11) 連續上升
streak 於本輪歸零）。另起 R136 而非續記 R135，係因 R135 的 lane 額度（309）已由
既有四列（119+51+55+17=242）用掉大半，本輪 81 若續記 R135 會使該輪 lane 合計達
323、超過 `_REGRESSION_LANE_ROUND_CAP=309`。

逐檔分解：
- `test_run_root_unittests.py` +61：新增回歸測試類別
  `ParallelShardWorkerThreadBaseExceptionDoesNotEscapeTest`（Architect finding
  1(a)：worker thread 內部拋出非 `Exception` 子類的 `BaseException`——如
  `SystemExit`——時，`run_parallel()` 不得讓它穿透，改由新抽出的 `_crash_fallback()`
  直接收尾，不依賴外層 `except Exception` 篩選型別）；`LoadBalancingRegressionTest`
  docstring 重寫（Architect finding：計時斷言複合延遲風險，`worker_count` 由 2 改為
  3）；`ParallelShardStderrBackpressureRegressionTest` docstring 局部訂正（SA
  minor finding：「shard 0/1」字面訂正為「LOUD／SLOW 那個模組」）。
- `test_adr_xplat001_c1c2_lock.py` +20：本檔自身逐檔漂移（新增本輪稽核列＋回歸
  鎖軌新列＋`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列本身的行數，同 R131/R134/R135
  既有體例）。

## §2 分桶棘輪（guard_self）

本輪未修改 `tools/lib/guard_bucket_policy.py` 的 `guard_self` 桶成員內容
（`test_platform_neutral_paths.py`／`test_adr_xplat001_c1c2_lock.py` 等）以外的
判準邏輯，`guard_self` 桶行數不變。

## §3 到期義務兌現與展延

本輪未觸發任何到期義務（`_REPIN_NET_CAP_SCHEDULE` 現行 cap＝548，本輪淨額扣除
lane 後為 0，遠低於 cap；`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND=137`／
`_PHASE2_REVIEW_LOG` 最新列 R135 皆未到期）。

## §4 四方複審逐條處理

完整的第二次四方複審逐字結果、逐條處理方式與端到端重驗輸出見
`docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第四輪第二次
對抗式複審〉節（本檔不重複記載，避免同一件事有兩個會漂移的家）；缺陷帳本索引見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274／DEF-200-276。
