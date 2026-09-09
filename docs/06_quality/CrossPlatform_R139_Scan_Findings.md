# CrossPlatform R139 — DEF-200-274 第六輪四方獨立複審收斂

- **輪籤**：R139（2026-09-09，macOS；主控收尾單人窗口）
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R138（DEF-200-274 第六輪頭重腳輕修法落地，見
  `CrossPlatform_R138_Scan_Findings.md`）。R138 落地後派 Architect／SA／SD／QA
  四方獨立審查（各自不共享上下文，分別跑）重新核對三題，本輪逐條處理四方
  共同點名的缺口。

---

## §1 護欄層淨額承認

<!-- guard-total:R139 --> 本輪護欄層行數 95942 → 96117（+175，全額歸回歸鎖軌）
——`test_run_root_unittests.py`（3335 → 3486，+151）新增三個回歸測試類別；
`test_adr_xplat001_c1c2_lock.py` 自身逐檔漂移收斂（新增稽核列＋
`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列＋`_REGRESSION_LANE_LOG` 新列本身＋
`_REPIN_NET_CAP_SCHEDULE` 到期義務兌現列，+23）。同輪兌現 `_REPIN_NET_CAP_
SCHEDULE` 到期義務（cap 547→546，`_REPIN_NET_CAP_DUE_ROUND=139`），同輪重新
武裝下一段（`_REPIN_NET_CAP_DUE_ROUND=141`／`_REPIN_NET_CAP_DUE_TARGET=545`）。

## §2 四方獨立複審結果摘要

四方對 R138 落地的變更（`tools/lib/dispatch_granularity.py`／
`tools/run_root_unittests.py`／`tools/tests/test_platform_utils_dedup.py`）
各自獨立跑，三題裁決一致：`VERDICT_LEDGER_RESOLVED=partial`／
`VERDICT_FEATURE_COMPLETE=partial`／`VERDICT_LOAD_BALANCED=partial`。

- **Architect**：設計本身穩健（安全網 fail-closed、與 `parallel_shard.py`
  零耦合整合皆核實無誤），但點名零測試覆蓋 + docstring 假宣稱（blocking）＋
  證據檔缺〈第六輪〉章節、主帳本未回填（major）。額外建議：白名單缺機械
  安全網守「無模組層 fixture」這條前提。
- **SA**：獨立核實白名單兩檔類別/測試數精確相符、護欄層簿記精確相符、
  `sync_onboarding_baselines.py --check` 乾淨；同樣點名證據帳本斷鏈＋零測試
  覆蓋（Finding 1-3）；額外指出白名單缺正式 runbook（僅有 docstring 範例）；
  親測 wall-clock 307.95s，比 R138 文件宣稱的 274s 高約 12%（判定為機器
  負載雜訊，模組級耗時逐項對得上佐證修法有效）。
- **SD**：親寫驗證腳本對真實 4045 支測試呼叫 `suite_dispatch_units()`，139
  個派工鍵逐一用 `loadTestsFromName()` 回灌計數，0 筆不符——機制本身正確性
  獨立佐證。同樣點名零測試覆蓋（blocking）＋ docstring 假宣稱（blocking）。
  核實 `_zzz_` 排除不誤傷任何真實 tracked 檔案（`git ls-files '*_zzz_*.py'`
  空集合）。VERDICT_LEDGER_RESOLVED 給 resolved（僅就護欄層帳務自洽性判斷，
  未涵蓋證據檔斷鏈這件事——與 Architect/SA/QA 的 partial 裁決範圍不同，非
  真正分歧）。
- **QA**：親測序列 794.00s vs 平行 4-worker 300.01s／308.50s，加速比
  ≈2.6x，強力推翻第三輪「幾乎零加速比」（572s/570s≈1.0x）的舊描述；兩次
  平行重跑完全一致（發現數/skip數/rc 皆相同）；1-worker 邊界案例驗證細分後
  的派工鍵能被單一 worker 正確消化，無漏測試無重派；橫跨 5 趟全套跑零次
  複現 `_zzz_` TOCTOU（誠實劃界：非統計顯著證偽，第五輪自陳 1/3 機率複現，
  5 次全不中機率 ≈13.5%，非可忽略）。額外發現：審查機器 `~/.zshrc` 全域
  設定 `AUTOSDD_PARALLEL_TESTS=1`，會讓任何人在此機器上裸執行「序列基準」
  被無聲劫持成平行模式（非本輪程式缺陷，環境隱患記錄供知悉）。

## §3 修復（收尾單人窗口逐條落地）

1. **`dispatch_granularity.py` 零測試覆蓋（Architect/SA/SD 皆列 blocking）
   ——已修復**：`tools/tests/test_run_root_unittests.py` 新增三個測試類別
   （+151 行，全額歸回歸鎖軌）：
   - `DispatchGranularityDispatchKeyTest`：白名單頂層類別正確細分／巢狀
     類別 fail-closed／`getattr` 解不回同一物件時 fail-closed／placeholder
     測試不受白名單影響，共 5 支測試方法。
   - `DispatchGranularityPlaceholderConstantStaysInSyncTest`：機械斷言兩份
     `_PLACEHOLDER_MODULE`／`_module_of()` 複本仍同步（Architect 額外提醒
     的複本漂移風險，直接轉成回歸鎖）。
   - `DispatchGranularityWhitelistHasNoModuleLevelFixturesTest`：機械斷言
     白名單兩個真實檔案皆無 `setUpModule`／`tearDownModule`（Architect
     finding：把「已核實無隱性共享狀態依賴」這條最容易被忽略的前提，從
     純人工核實轉成機械不變量）。
2. **`dispatch_granularity.py` docstring 假宣稱（Architect/SD 皆列
   blocking）——已修復**：改為據實列出上述三個測試類別的名字與各自看守的
   面向，不再是查無實據的籠統宣稱。
3. **證據帳本斷鏈：`CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`
   缺〈第六輪〉章節（Architect/SA/QA 皆點名）——已修復**：補上該章節，
   涵蓋 R138 實作與本輪（R139）四方複審收斂全貌。
4. **主缺陷帳本 `AutoSDD_Defect_Log.md` 的 DEF-200-274 列未同步（SA/QA 皆
   點名）——已修復**：狀態欄改為指向〈第六輪〉，敘明頭重腳輕根因已修復。

## §4 本輪重驗（逐字，2026-09-09）

```
$ cd tools/tests && env -u AUTOSDD_PARALLEL_TESTS -u AUTOSDD_PARALLEL_TESTS_WORKERS \
    ../../.venv/bin/python3 -m unittest test_run_root_unittests -v
Ran 135 tests in 63.015s
OK
```

```
$ .venv/bin/python3 -m unittest test_adr_xplat001_c1c2_lock
Ran 192 tests in 10.5s
OK
```

`ruff check tools/lib/dispatch_granularity.py tools/run_root_unittests.py
tools/tests/test_platform_utils_dedup.py tools/tests/test_run_root_unittests.py`
：`All checks passed!`；`AutoClaude/tools/check_loc_budget.py --json`：
`total_violation=False`。

## §5 誠實劃界（本輪仍未解決／範圍外）

- **Windows 真機驗證**：仍未解，本輪未觸及。
- **SA 建議的正式 runbook**：白名單「何時該加入新檔案」目前仍只有
  `dispatch_granularity.py` docstring 裡兩筆已核准項目的敘述可依樣畫葫蘆，
  未提煉成獨立、給下一個接手者看的操作指引/checklist——本輪未落地，留供
  後續（非阻斷，屬文件品質改善）。
- **wall-clock 精確重現性**：多包並行審查時測到的秒數（300~308s）與單租戶
  基準（274s，見 R138 §3）有 9~18% 落差，已由四方一致判定為機器負載雜訊
  （模組級耗時逐項對得上），但這代表 R138/R139 文件裡的絕對秒數應讀作
  「該次量測環境下的代表值」而非精確可重現的保證值。
- **QA 發現的環境隱患**（`~/.zshrc` 全域 `AUTOSDD_PARALLEL_TESTS=1`）：
  非本輪程式碼缺陷，不在本輪修復範圍，僅記錄供未來在此機器上量測「序列
  基準」時留意需顯式 `env -u AUTOSDD_PARALLEL_TESTS` 覆寫。
- **VERDICT_LEDGER_RESOLVED 現況**：本輪已修復四方點名的全部 blocking／
  major 缺口（零測試覆蓋、docstring 假宣稱、證據帳本斷鏈、主帳本未同步），
  但因 Windows 真機驗證仍未解，DEF-200-274 整體維持 `partial`，不宣稱
  `fixed`/`closed`。
