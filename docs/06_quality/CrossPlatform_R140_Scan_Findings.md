# CrossPlatform R140 — DEF-200-274 第七輪：負載不均自動偵測 + 四方獨立複審收斂

- **輪籤**：R140（2026-09-09，macOS；主控收尾單人窗口）
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R139（DEF-200-274 第六輪四方獨立複審收斂，見
  `CrossPlatform_R139_Scan_Findings.md`）。掌舵者直接提問三題（①帳本問題是否
  解決、②多CPU測試功能是否完備、③是否有頭重腳輕分配不均），並在補充資訊裡
  明確要求「請設計自動偵測機制」取代第六輪〈誠實劃界〉記載的「靠人眼發現
  新熱點」。本輪派 Architect/SA/SD/QA 四方獨立審查（各自不共享上下文，分別跑）。

---

## §1 護欄層淨額承認

<!-- guard-total:R140 --> R140 護欄層累積淨額＝ 96117 → 96240（+123，全額歸回歸鎖軌）——
新增 `tools/lib/dispatch_imbalance.py`（負載不均自動偵測，非鎖檔，不進逐檔
行數表）＋回歸測試 `DispatchImbalanceDetectionTest`／`ReportDispatchImbalanceTest`：
`test_run_root_unittests.py` 3486→3570（+84）；四方獨立複審共同點名並由 SD
給出修法的 `fair_share` 分母真缺陷，補回歸測試
`test_fewer_units_than_workers_and_balanced_flags_nothing`
（`test_run_root_unittests.py` 3570→3587，+17）；本檔（`test_adr_xplat001_
c1c2_lock.py`）自身逐檔漂移 +22（新增稽核列＋`_REGRESSION_LANE_LOG` 新列＋
`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列＋本列自身的行數）。逐項見 `_GUARD_LINES_REPIN_LOG`／`_REGRESSION_LANE_LOG` 的
R140 列。

## §2 四方獨立複審結果摘要

四方對「新增 `tools/lib/dispatch_imbalance.py`」這項變更各自獨立跑，三題裁決
方向一致但理由略有差異：

- **Architect**：`VERDICT_LEDGER_RESOLVED=partial`（無倒退）／
  `VERDICT_FEATURE_COMPLETE=partial`／`VERDICT_LOAD_BALANCED=partial`。實測
  `wc -l tools/run_root_unittests.py`＝775，與 LOC 棘輪表逐字吻合；`ruff check`
  全乾淨；`test_run_root_unittests.py` 143 個測試全綠。點名 Finding F1（major）：
  三支 `.github/workflows/*.yml` 與 `tools/git-hooks/pre-push` 皆未設定
  `AUTOSDD_PARALLEL_TESTS`，偵測結果只印 stdout、不落檔、不影響 rc——「自動」
  目前僅對手動 opt-in 平行模式的個別開發者生效。Finding F2（major，潛伏未
  觸發）：`fair_share` 分母用未經 cap 的名目 `worker_count`，實測「1 個單位、
  worker=8」與「3 個完全平衡的單位、worker=8」皆被誤判為不均。
- **SA**：`VERDICT_LEDGER_RESOLVED=open`（兩項 blocking：本輪新增的
  `_GUARD_LINES_REPIN_LOG` 列落地時引用了尚不存在的〈第七輪〉章節；
  `AutoSDD_Defect_Log.md` DEF-200-274 列未同步本輪——與第六輪複審點名過的
  同型缺口重演）／`VERDICT_FEATURE_COMPLETE=partial`／`VERDICT_LOAD_BALANCED=open`
  （本輪對派工演算法本身零改動，純觀測工具不是負載平衡改善）。獨立核實
  `AutoClaude/pyproject.toml` 與 30 份 `AISDLC_SDD/AISDLC_SDD_v0.*/pytest.ini`
  逐一比對內容完全相同、皆無平行化設定；`AutoClaude/tools/run_local_nightly.sh`
  呼叫本 runner 時亦未設定該環境變數。
- **SD**：獨立寫合成場景實測證實 F2「不是邊緣情況偶爾誤報，而是這個公式在
  `dispatch units < worker_count` 整個區間裡都不是在測『不均』，而是在測
  `worker_count` 設定值本身」（單一單位倍率恆等於 worker_count，與 elapsed
  數值無關）；確認唯一生產路徑（69 支測試檔＋白名單細分後遠大於 worker 上限 8）
  結構上不會踩到，但公式正確性不該依賴這個僥倖。給出一行修法：分母改用
  `min(worker_count, len(module_timings))`。
- **QA**：`VERDICT_LOAD_BALANCED=fixed`（唯一與其他三方不同的裁決——親測全套
  4062 支測試、139 個派工單位、4 worker，`grep "🚨"` 零命中，無誤報也無舊熱點
  假性復發）。用 10 種合成情境逐一戳邊界（極小浮點數／恰好門檻值／10x 主導／
  1 個單位 worker=8／3 個相同單位 worker=8／5 個相同單位 worker=8／7 個相同
  單位 worker=8）驗證核心邏輯除 F2 外皆正確；精確定位問題邊界＝「單位數 ≤ 7、
  worker=8」時全數誤標，「單位數=7、worker=8」時不誤標。親跑全套時 rc=1，15
  個失敗逐一核對測試名稱皆為 `test_adr_xplat001_c1c2_lock.py` 的護欄層棘輪
  測試（收尾窗口尚未補完 R140 帳本三件套所致），與 `dispatch_imbalance` 本身
  無關。

## §3 修復（收尾單人窗口，依四方共同點名逐條落地）

1. **F2／SD 一行修法**：`tools/lib/dispatch_imbalance.py::detect_imbalance()`
   分母改為 `effective_workers = min(worker_count, len(module_timings))`；新增
   回歸測試 `test_fewer_units_than_workers_and_balanced_flags_nothing`（3 個
   耗時皆 20.0 的單位，worker_count 分別代入 2/3/4/8/50，斷言皆不觸發）。
2. **F1（SA blocking）文件斷鏈**：本檔即為該修復標的——`_GUARD_LINES_REPIN_LOG`
   R140 列的引用落地時生效；`docs/06_quality/CrossPlatform_DEF200274_Parallel_
   Tests_Evidence.md` 已補〈第七輪〉章節；`AutoSDD_Defect_Log.md` DEF-200-274
   列已同輪回填。
3. **F1（Architect/SA major）「未達自動」缺口**：不宣稱已解決，如實記載於
   證據檔〈第七輪〉的〈誠實劃界〉一節——這僅是「自動化了計算，沒有自動化
   觸發」，下一輪若要真正達成「不必再靠人眼」，需要至少一條排程在平行模式下
   真的跑一次並讓結果有機械可稽核的落點。

## §4 誠實劃界（本輪仍未解決）

- Windows 真機驗證仍未解（掌舵者已表示會自行在 Windows 11 驗證）。
- 「自動偵測」目前只自動化了計算步驟，未自動化觸發／曝光路徑（見 §3 第 3 項）。
- `AutoClaude/tests/`／`AISDLC_SDD` 的 pytest 套件不受本機制惠及（範圍本身
  不違反 DEF-200-274 立案文字，但此前六輪皆未在〈誠實劃界〉明講此邊界）。
- `ratio_threshold=1.5` 寫死、不可由環境變數覆寫（Architect 指出，目前無害）。

逐項見 `docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`
〈第七輪〉節；缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274。
