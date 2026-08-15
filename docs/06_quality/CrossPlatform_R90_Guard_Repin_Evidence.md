# CrossPlatform R90 護欄層重釘證據

> 對應 `_GUARD_LINES_REPIN_LOG` 的 R90 那一列。重釘理由欄依規只能是索引，全文在此。
> 🔴 本檔所有數字皆量於 **R90 收尾單人窗口的靜止樹**（八包全部停工、無其他工作者），
> 故 rc 與行數可歸因。本輪四方複審一致認定：移動標的上量到的數字不具憑證力。

## 淨額與逐檔清單

| 項 | 值 |
|---|---|
| 重釘前 | 83578（＝R89 收尾窗口釘下的值） |
| 重釘後 | 83739 |
| 淨額 | +161 |

| 檔 | 淨額 | 內容 |
|---|---|---|
| `tools/tests/test_quota_policy.py` | +124 | R89 觀測欄（`is_active`／`severity`）「接好卻沒有電」的回歸鎖：新帳號（Team）payload fixture、通電不得改判的漂移判準、兩組合成注入、端到端反向判準、雙向相容 |
| `tools/tests/test_context_budget_guard.py` | +25 | 取數層責任邊界：新欄位不得改變**桶的列舉**與鍵的存在性；敵意型別原樣帶出不得強制轉型 |
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | +12 | 本次重釘自身的稽核列（棘輪要求「淨額在結構上不可能缺席」，那一列自己佔行） |

前兩支＝派給包 A 的成長（+149），第三支＝收尾窗口重釘的自身成本（+12）。

## 為什麼判定「壓不動了」——三條合法出口逐條實查

棘輪自己列的合法出口是「刪死碼／搬史料／抽共用模組」。逐條量測結果：

### ① 刪死碼 ＝ 0

新增的四個 helper（`_R89_TEAM`／`_r89_state`／`r89_decision_drift_problems`／`_r89_decide`）
與新增的 `import dataclasses`，逐一實查皆有實際消費者，零孤兒。

### ② 搬史料 —— **已由包 A 用盡**，殘餘不在出口射程內

包 A 自陳把史料搬進 `tools/lib/quota_meter.py`〈R89 觀測欄〉段後，該包的淨額由 **+253 降到 +149（−41%）**。
收尾窗口對 +149 逐行複量（`git diff -U0` 分類）：

| 類別 | 行數 |
|---|---|
| 程式（fixture／判準／斷言） | 105 |
| docstring | 18 |
| 註解 | 8 |
| 空行 | 18 |

殘餘散文共 26 行，其中 8 行**已經是指標形態**（逐字指向 `tools/lib/quota_meter.py`
的〈R89 觀測欄〉段與 fixture 的真機出處），18 行是**判準的理由**。
而 R89 那一列的重釘紀錄逐字寫著：搬遷體例是「判準與判準的理由**一行都沒搬**」
——理由不在出口射程內。⇒ 這條出口對本批已無可搬之物。

### ③ 抽共用模組 —— 技術上可行，**收尾窗口刻意不做**（列為交棒項）

`tools/tests/test_quota_policy.py` 檔頭自訂的體例是「判準本體住
`tools/lib/quota_criteria.py`，本檔只留『呼叫判準 ＋ 斷言』」。
依此體例，`r89_decision_drift_problems()` 屬於可下沉的判準本體，約 11 行（佔 +149 的 7%）。

不做的理由（誠實劃界，不是「不可壓縮」）：

1. 它要動 `tools/lib/` ——**另一個 LOC 預算面**（`ROOT_TOOLS_TIERS`／`SPECIAL_FILES`
   raw-line 棘輪），而該面的既有判例正是「A 鎖要求的動作是 B 鎖的違規」。
2. 收益僅 7%，重釘在任一情況下仍不可免。
3. 收尾窗口的首要交付是**靜止樹憑證**；在唯一能取得憑證的時點做非必要重構，
   等於拿憑證的可歸因性去換 7%。

⇒ 本輪據實登記為「**未用盡**出口③」，交棒給下一輪，而不是宣稱不可壓縮。

## 代價側（重釘成本棘輪）現查

| 量 | 值 | 出處 |
|---|---|---|
| R90 單輪淨額上限 | 2000 | `net_cap_for_round(90)`（`_REPIN_NET_CAP_SCHEDULE` 末段 `(89, 2000)`） |
| 本輪淨額 | +161 | 遠低於上限，款(10) 不觸發 |
| 連續上升輪數 | 1 | R89 淨額 −92 ⇒ streak 歸零；上限 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`，款(11) 不觸發 |
| 到期義務 | 未到期 | `_REPIN_NET_CAP_DUE_ROUND = 91`（目標 1600）；R90 < 91 |

🔴 **交棒警訊（下一輪必讀）**：R91 同時撞上兩件事——
① 款(12) 到期：稽核痕跡一旦出現 R91 的列，`_REPIN_ROUND_NET_CAP` 必須先追加一段 ≤ **1600**；
② 連升計數：R90 已是第 1 輪上升，R91 可再升（第 2 輪），但 **R92 必須出現一次淨額 ≤ 0**。
若 R91 也是多包並行的成長輪，這兩件事會疊在同一個收尾窗口上。

## 逐輪淨額（現查，不寫死）

```
python -c "import importlib.util,sys; \
spec=importlib.util.spec_from_file_location('lk','tools/tests/test_adr_xplat001_c1c2_lock.py'); \
m=importlib.util.module_from_spec(spec); sys.modules['lk']=m; spec.loader.exec_module(m); \
print(m.repin_round_nets(m._GUARD_LINES_REPIN_LOG))"
```

## 重釘後的閘門憑證（靜止樹）

```
[Scan-H triplet] UEP=5 AC=47 GLC_FILES=64 GLC_LINES=83739
Ran 3346 tests in 430.061s
OK (skipped=44)
ROOT_TRUE_RC=0
```

`GLC_LINES=83739` 與 `sum(_FROZEN_GUARD_LINES.values())`、`_GUARD_LINES_REPIN_LOG` 表尾
三處逐字相等（款(4) `[未對帳]` 與款(2) `[淨額不符]` 皆綠）。

## 分桶棘輪（未動）

`tools/lib/guard_bucket_policy.py` 現查讀數 `{'prose': 4009, 'guard_self': 3545}`，
凍結基準 `{'prose': 4119, 'guard_self': 3545}` ⇒ `bucket_ratchet_problems()` 回空。
本輪的 +161 **一行都沒有落進 prose 桶**（新增全屬判準與 fixture）
⇒ 未動任何桶基準、未調高任何門檻。
