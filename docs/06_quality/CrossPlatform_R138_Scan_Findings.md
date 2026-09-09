# CrossPlatform R138 — DEF-200-274 第六輪：頭重腳輕修法＋補漏 TOCTOU 排除

- **輪籤**：R138（2026-09-09，macOS；主控收尾單人窗口）
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R137（DEF-200-274 第五輪四方獨立複審收斂，見
  `CrossPlatform_R137_Scan_Findings.md`）。第五輪誠實劃界列出「本檔掃描面排查
  非窮盡」與「weighted_shards() 效率優化留待後續」兩項未解；本輪針對第一次
  聚焦到的「頭重腳輕」根因（單一測試占平行總耗時 65%）親自落地修法，並在收尾
  端到端重驗時親自發現並修復第五輪排查漏掉的第 11 個同型 TOCTOU 站點。

---

## §1 護欄層淨額承認

<!-- guard-total:R138 --> 本輪護欄層行數 95925 → 95942（+17，全額功能軌，非
回歸鎖）：

- `test_platform_utils_dedup.py`（1104 → 1112，+8）：`_repo_py_files()` 補
  `_zzz_` 合成暫存模組排除——本函式與 `test_pre_push_dispatcher.py`／
  `test_ps_engine_ssot.py` 同型（第五輪已修），但未被第五輪排查涵蓋，端到端
  重驗時親自複現（`FileNotFoundError` 命中 `_zzz_loadbalance_repro_*`／
  `_zzz_backpressure_repro_*`／`_zzz_protocol_repro_*` 三組合成模組）。
- `test_adr_xplat001_c1c2_lock.py`（7607 → 7616，+9）：本檔自身逐檔漂移收斂
  （新增一筆稽核列＋`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列＋本列本身的行數，
  同 R131~R137 既有體例）。

## §2 頭重腳輕根因修法（非護欄層行數異動，落在 `tools/`／`tools/lib/`）

**背景**：第五輪 QA 已量出 `test_doc_loc_baseline_freshness_r60.py` 單模組占
平行總耗時約 65%，但未落地修法（列入誠實劃界）。本輪實測進一步定位：真正的
離群值不是「這個檔案」整體，而是其中**一支**測試方法：

```
$ .venv/bin/python3 -m pytest tools/tests/test_doc_loc_baseline_freshness_r60.py --durations=30 -q
118.49s call  ...TestR67R3ThisFileMakesNoUnstatedPlatformAssumption::
              test_every_lock_in_this_file_holds_under_every_simulated_platform
5.67s  call  ...TestR67CliFailsLoud::test_audit_mode_is_the_default_and_check_flag_is_real
（其餘 275 支測試合計 <35s）
277 passed, 42 subtests passed in 157.52s
```

**修法**：新增 `tools/lib/dispatch_granularity.py`（先例：`ci_liveness.py`，
`tools/run_root_unittests.py` 受 special-tier LOC 棘輪管制、落地當回合無餘裕）：
平行派工鍵改採「白名單模組用 (module, class) 細分、其餘模組維持 (module) 整體」
——`unittest.TestLoader.loadTestsFromName()` 原生支援 `module.ClassName` 點號
路徑，`tools/lib/parallel_shard.py` 的 worker 協定完全不必改。白名單安全網：
只有「類別是模組頂層屬性、`getattr(module, qualname) is cls`」才細分，巢狀／
動態類別退回模組粒度（fail-closed）。

白名單納入兩檔（`CLASS_LEVEL_DISPATCH_MODULES`），皆已核實類別間無隱性共享
狀態依賴（僅惰性鍵值快取／`setUpClass` 只設自身類別屬性）：

- `test_doc_loc_baseline_freshness_r60`：36 類別、277 測試。
- `test_archive_defect_log`：36 類別、173 測試——修完第一個熱點後，
  `⏱ 模組耗時排行` 浮現的**新**單一最重模組（224.5s），profile 與前者不同
  （無單一離群測試，36 類別普遍偏重）。

## §3 端到端重驗（逐字，2026-09-09，PATH 含 `.venv/bin` 消除 ruff-PATH 環境噪音）

```
$ AUTOSDD_PARALLEL_TESTS=1 AUTOSDD_PARALLEL_TESTS_WORKERS=4 python tools/run_root_unittests.py
✅ 發現 4045 個測試（下限 4045）
[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次 skip 46 支）
rc=0
⏱ 模組耗時排行（前 5，共 139 模組）：
   - test_doc_loc_baseline_freshness_r60.TestR67R3ThisFileMakesNoUnstatedPlatformAssumption: 118.0s
   - test_platform_neutral_paths: 73.6s
   - test_run_root_unittests: 67.6s
   - test_archive_defect_log.TestMoveSubsetSelectionIsNamedAndTraceable: 55.4s
   - test_dev_start: 39.0s
```

單一最重派工單位由 224.5s（本輪修法前）降到 118.0s；4-worker 全套 wall-clock
由第三輪誠實揭露的「幾乎零加速比」基準（序列 572s／平行 570s）改善到約 274s
（本輪修法後，兩次獨立重跑一致：274.46s／274.61s，rc=0，M6 集合關係皆成立）。

## §4 誠實劃界（本輪仍未解決／未觸及的項目）

- **Windows 真機驗證**：仍未解，本 session 全程 macOS-only，無法在此完成，
  沿用第五輪既有記載。
- **weighted_shards() 效率優化的另一半**：`test_doc_loc_baseline_freshness_
  r60.TestR67R3ThisFileMakesNoUnstatedPlatformAssumption` 本身仍需 118s，
  本輪只解決「不拖累其他測試」，未嘗試縮短該測試自身邏輯的耗時（其職責是逐一
  模擬多平台重跑本檔全部鎖，縮短需求須先確認不犧牲覆蓋率，非本輪範圍）。
- **本輪 TOCTOU 補漏排查僅涵蓋本次端到端重驗實際命中的一個站點**
  （`test_platform_utils_dedup.py`）：未對整棵 `tools/tests/` 樹重做第五輪
  等級的逐檔 `rglob`/`glob` 站點普查，不保證這是最後一個漏網站點；下一輪
  若又有新 TOCTOU 現形，比照本輪與第五輪的修法（`_zzz_` 前綴排除）處置即可。
