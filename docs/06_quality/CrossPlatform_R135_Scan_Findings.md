# CrossPlatform R135 — DEF-200-274 第四輪四方複審收尾 round-label-ok

- **輪籤**：R135（2026-09-08，macOS；收尾單人窗口）
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R134（DEF-200-274 第三輪對抗式複審收尾，見
  `CrossPlatform_R131_Scan_Findings.md` §7～§8）。第四輪（work-stealing 動態派工重構＋
  負載平衡回歸測試）落地後遭遇 DEF-200-275（SDD-FSM ESCALATION 誤觸）中途擋下，本輪
  補做四方對抗式複審與全數修復收尾。

---

## §1 護欄層淨額承認

<!-- guard-total:R135 --> 本輪護欄層行數 95520 → 95762（+242，全額歸回歸鎖軌，見
`_REGRESSION_LANE_LOG` 同輪四列 119+51+55+17=242，貼齊本輪主表淨額，扣除後款(11)
連續上升 streak 於本輪歸零）。

逐檔分解：
- `test_run_root_unittests.py` +147：work-stealing 動態派工重構的回歸測試
  （`LoadBalancingRegressionTest` 合成負載平衡注入自證＋`import time`）與
  `ParallelShardPopenFailureKillsAlreadyStartedProcsTest` 改依 argv 模組名判斷（原本依
  Popen 呼叫次序在多執行緒下不再可靠）；+55 為對抗式複審收斂追加：Architect 阻斷
  條件建議的新回歸測試 `ParallelShardMultipleThreadFailuresAreAllReportedTest`（3 個
  worker thread 同時失敗，斷言合併例外訊息三筆全部可見）＋修正既存 `_FakeProc`
  fixture 漏 `returncode` 屬性的潛在缺口。
- `test_platform_neutral_paths.py` +27：QA 阻斷條件要求的 TOCTOU 緩解——新增
  `_read_text_or_none()` 輔助函式，套用到 `run_unit_scan()`、
  `TestTextIoDeclaresEncoding._scan_repo()`、`_scan_file()` 三個實際被
  `LoadBalancingRegressionTest`／`ParallelShardRealSubprocessProtocolIntegrationTest`
  在平行模式下寫入 `tools/tests/` 的合成暫存模組（`_zzz_*.py`）競態命中的呼叫點。
- `test_adr_xplat001_c1c2_lock.py` +68：本檔自身逐檔漂移（多次收斂列＋本列自身＋
  `_REGRESSION_LANE_LOG`／`_REPIN_NET_CAP_SCHEDULE`／`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND`／
  `_FROZEN_PREFIX_REWRITE_LEDGER`／`_PHASE2_REVIEW_LOG` 五處到期義務兌現、展延與接鏈
  本身的行數，含對抗式複審收斂追加的新測試自身逐檔漂移）。

## §2 分桶棘輪（guard_self）

`tools/lib/guard_bucket_policy.py` 的 `_FROZEN_SHRINK_ONLY_BUCKET_LINES["guard_self"]`
由 3246 重釘為 3255（+9）——四方複審（Architect／SD／QA）blocking condition 明確要求對
`test_platform_neutral_paths.py` 加 TOCTOU 緩解，該檔本身即 guard_self 桶成員，緩解
程式碼是判準邏輯本身、無法移出散文。

## §3 到期義務兌現與展延

- `_REPIN_NET_CAP_SCHEDULE` 追加 `(135, 548)`：`_REPIN_NET_CAP_DUE_ROUND=135` 本輪剛好
  到期，cap 降到到期目標本身（同 R99/R101/.../R133 既有判例：兌現值貼齊到期目標）。
- `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 由 135 具名展延為 137：ADR-XPLAT-013 §9.3／U9
  四支 `[ROOT-TOOLS]` 檔舊尺技術債真拆屬獨立重構持有面（鐵律七），本輪主軸是
  DEF-200-274 第四輪四方複審收尾，非 root-tools 重構持有面；真拆待獨立窗口，
  135 → 137（在 `_ROOT_TOOLS_DEBT_DUE_MAX_LOOKAHEAD=5` 內）。
- `_PHASE2_REVIEW_LOG` 追加 `(135, "[維持觀察]", ...)`：本輪未觸碰 ADR-XPLAT-013
  方向 (c) 觀測→阻斷轉換提案（R129 `[提案]` 送四方複審一事，複審本身由主控承接、
  非本收尾窗口執行），亦未提出新 Phase 2 提案；上一列是 `[提案]` ⇒ 連續『維持觀察』
  計數自本列起算為一，未觸上限（`_PHASE2_MAX_CONSECUTIVE_DEFERRALS=1`）。

## §4 四方複審逐條處理

完整的四方複審逐字結果、逐條處理方式與端到端重驗輸出見
`docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第四輪〉節（本檔
不重複記載，避免同一件事有兩個會漂移的家）；缺陷帳本索引見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274／DEF-200-273／DEF-200-275。
