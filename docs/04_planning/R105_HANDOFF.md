# R105 交接書 — tools/tests/ 護欄層行數棘輪維護輪

> 本檔案由子 agent 執行「棘輪維護」任務時寫入，記錄本輪對 `test_adr_xplat001_c1c2_lock.py`
> 護欄層行數棘輪所做的重釘動作與驗證輸出。🔴 重啟後第一件事＝重驗，不採信本檔任何
> 「已驗證」宣稱本身的正確性。

## 0. 本輪範圍

上一輪（另一批修復）對 `tools/tests/` 四支檔新增回歸測試（DEF-200-158／012／196／
015／173），合計淨行數 +34，觸發 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的護欄層
行數棘輪。本輪**只處理棘輪重釘本身**：

- 現查棘輪目前是紅是綠（`python3 -m unittest tools.tests.test_adr_xplat001_c1c2_lock -v`）。
- 若紅，比照 R103／R104 既有慣例，把 `tools/tests/` 語料內既有的純散文／史料段落
  搬去證據檔以抵銷淨增，讓總淨額回到 ≤0。
- **不刪減任何測試判準的實質內容**——只搬「純敘事／史料」的部分。
- 不做 `git add`／`commit`／`push`。

## 1. 已驗證什麼（本輪實測，附指令與輸出）

### 1.1 起點：棘輪現查為紅

```
$ python3 -m unittest tools.tests.test_adr_xplat001_c1c2_lock -v 2>&1 | tail -20
...
FAIL: test_ratchet_is_independent_of_git_state
AssertionError: ["[成長] 護欄層行數由 88556 增為 88590（+34）——..."] != []
...
FAILED (failures=3)
```

三支失敗測試皆指向同一件事：`_FROZEN_GUARD_LINES` 凍結表（88556）與磁碟實況
（88590）不符，差額 +34，逐檔漂移為 `test_block_destructive_git_r83.py`(+8)／
`test_context_budget_guard.py`(+16)／`test_defect_id_reference_integrity.py`(+1)／
`test_mac_endurance_r83.py`(+9)。

### 1.2 抵銷手法

搬遷 `tools/tests/_platform_helpers.py::strip_ps_comments()` docstring 內
「已知不涵蓋」清單的逐版沿革（R57 round 3／4 差分實測數據，屬純史料，非判準本體）
至 `docs/06_quality/CrossPlatform_R105_Scan_Findings.md`，446→403（-43）。判準
本體（涵蓋清單本身與 WHY 理由）**未搬動**。

### 1.3 另發現的第二道棘輪：分桶棘輪

第一次嘗試（在搬遷段落內寫出 `docs/06_quality/CrossPlatform_R105_Scan_Findings.md`
完整路徑）意外把 `strip_ps_comments` 這個 chunk 從 `selfcontained` 桶翻成
`exclusive prose` 桶（`guard_bucket_policy.py` 的分桶棘輪對 `prose`／`guard_self`
兩桶是 shrink-only），導致 `TestGuardBucketRatchet.test_shrink_only_buckets_did_not_grow`
轉紅（`prose` 桶 4182→4216）。**修法**：搬遷段落內改用不帶 `docs/` 目錄前綴的裸檔名
`CrossPlatform_R105_Scan_Findings.md` 引用（該樹前綴不在 `BUCKET_TREES["prose"]`
內），使該 chunk 維持 `selfcontained`，`prose` 桶回到 4182。此教訓已記入
`docs/06_quality/CrossPlatform_R105_Scan_Findings.md`。

### 1.4 到期義務兌現：DEF-200-224

重釘過程中發現 `_REPIN_NET_CAP_DUE_ROUND=105` 剛好是本輪，需要往
`_REPIN_NET_CAP_SCHEDULE` 追加 `(105, 660)` 一列並重新武裝下一段
（`_REPIN_NET_CAP_DUE_ROUND=107`／`_REPIN_NET_CAP_DUE_TARGET=630`，步伐 30 <
前一段的 40，續守「步伐刻意變小」）。已立案 `DEF-200-224`（見缺陷帳本）。

### 1.5 最終驗證

```
$ python3 tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines 2>&1 | head -3
# 淨額 88556→88556 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）

$ python3 -m unittest tools.tests.test_adr_xplat001_c1c2_lock -v 2>&1 | tail -5
（見交件回報最終實測輸出）
```

<!-- guard-total:R105 --> **本輪護欄層累積淨額（稽核痕跡合計，同輪多列合併）＝ 88556 → 88656（+100）**
——逐檔清單與搬遷散文全文見 `docs/06_quality/CrossPlatform_R105_Scan_Findings.md`；
§2 之後的追加重釘見本檔〈2. 同輪追加：四方複審 REJECT 修復〉與
`docs/06_quality/CrossPlatform_R105_FourParty_Fix.md`。

## 2. 同輪追加：四方複審 REJECT 修復（DEF-200-202）

四方複審對本輪 8 筆缺陷修復包的 REJECT 意見彙整後，逐筆親自查證：7 筆
（DEF-101-402、DEF-200-012／015／043／158／173／196）修復屬實，唯
`DEF-200-202`（`tools/lib/quota_gate.py` 呼叫 `quota_policy.decide()` 不帶
`active_model` ⇒ 模型分軌軸零煞車力）在工作樹 diff 中零改動，確認為真的假交付。
本輪已補齊接線並新增端到端回歸測試，觸發本檔 §0-§1 已重釘過的同一道護欄層行數
棘輪再度上升（+49，集中在 `test_context_budget_guard.py` 新增
`test_the_model_scoped_axis_only_brakes_when_the_transcript_names_it`）。
已同輪追加重釘（`_FROZEN_GUARD_LINES`／`_GUARD_LINES_REPIN_LOG`／
`_REPIN_LOG_FROZEN_PREFIX_LEN`／`_REPIN_LOG_HISTORY_SHA256`／
`_FROZEN_PREFIX_REWRITE_LEDGER` 五處同步），逐項見
`docs/06_quality/CrossPlatform_R105_FourParty_Fix.md`。

## 3. 還沒做（交棒事項）

- DEF-200-015 的姊妹帳本擴面（`test_defect_id_reference_integrity.py` 新增
  `ledger_primary_ids()` 對 `AutoSDD_External_Blocked_Log.md` 的納管）仍是**具名
  列舉**單一路徑，尚未做到 SD 複審原本建議的「現查帳本家族的族號集合」（自動發現
  任一新增的姊妹帳本）——未來若再拆出第三份姊妹帳本，本鎖不會自動涵蓋，需要人工
  再補一行。現查現況：`python -m pytest tools/tests/test_defect_id_reference_integrity.py -q`。
