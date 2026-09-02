# CrossPlatform R120 掃描發現（收尾單人窗口）

> 輪籤：R120（技術債總清償循環令第三投）。本檔＝守衛線淨額標記姊妹檔＋收尾全套揪出的
> 待補項紀錄；結案脈絡與逐項取證見 `CrossPlatform_R120_Debt_Closure.md`。

<!-- guard-total:R120 --> **護欄層累積淨額（`--print-guard-lines` 現查）：91646 → 91793（+147）**

## 收尾全套（`run_root_unittests.py`）揪出的待補項

本輪核心工作（P1-7／212 結案／SA-4／P1-8）在各自針對測試皆綠後，收尾全套仍抓到 24 筆紅，
全數為**新增文件觸發既有鎖**（非程式碼缺陷），逐類已修：

1. **新證據檔未登記** `_GOVERNANCE_DOCS`（`tools/lib/governance_docs.py`）——`CrossPlatform_R120_Debt_Closure.md`
   與本檔符合治理文件命名慣例卻未登記，逸出體積守門＋指針稽核；補登兩筆。
2. **sha 鏈未接**——`_FROZEN_PREFIX_REWRITE_LEDGER` 最後一列後指紋停在舊值，未接到本輪
   重釘後的 `_REPIN_LOG_HISTORY_SHA256`；追加 R120 鏈列（`4554dbed`→`31861e`）。
3. **`guard-total:R120` 標記缺兩份 doc**——護欄層淨額三元組須在兩份不同檔寫出（DEF-200-166）；
   本檔與 `R120_HANDOFF.md` 各一站點滿足最低站數。
4. **最新交棒書 stale 宣稱零射程**——`R120_HANDOFF.md`〈還沒做的〉節原措辭不含 `_HANDOFF_STALE_WORDS`
   觸發字，改用「尚未／仍未」＋現查指令 code span 後收得到宣稱（連帶解 `TestR67R3` 平台差異紅）。

## 淨額歸因（本輪三列 repin log 合計 +147）

| 列 | 淨額 | 內容 |
|---|---|---|
| 1 | +130 | P1-7（`test_context_budget_guard.py` +126）＋va3 改寫（+4） |
| 2 | +9 | 本表自身編修（首列稽核＋凍結表值同步＋prefix_len） |
| 3 | +8 | sha 鏈列＋本稽核列＋凍結表值同步＋prefix_len 109→110 |

款(11)：R118 淨額 −6 終止 streak、R119 +399 為第 1 連升、R120 +147 為第 2 連升（合規，
上限 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`）⇒ **`R121` 淨額必須 ≤0**。
