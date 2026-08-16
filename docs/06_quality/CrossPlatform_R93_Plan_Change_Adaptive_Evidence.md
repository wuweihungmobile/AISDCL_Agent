# R93：額度攤提的方案／帳號變更適配 — 落地證據

> 承 SD 規格〈額度攤提的方案／帳號變更適配（DEF-200-122 收尾 ＋ DEF-200-114 補完）〉。
> 本檔記錄落地當輪的紅綠自證、規格覆核發現、以及 LOC 護欄層棘輪的處置狀態。

## 1. 逐項落地清單

| 檔案 | 改動 |
|---|---|
| `tools/lib/quota_pace.py` | `row_of` 新增 `fp` 參數；`rows_from_jsonl` 回傳四元組（含 `fp`，缺席鍵回 `None`）；`SEED_OBSERVATIONS` 第 4 欄標記 `None`（永久排除）；新增 `filter_by_signature` |
| `tools/lib/quota_gate.py` | 新增 `core_signature`；`record_burn` 帶入 `fp=core_signature(state)`；`burn_ratio` 改吃 `state` 參數、回三元組 `(ratio, note, plan_note)`，僅取同指紋樣本；`pace_report` 三元解包並附加 `plan_note`；`quota_messages` 匯入清單新增 `core_signature_change_note` |
| `tools/lib/quota_messages.py` | 新增 `core_signature_change_note`（Plan B 的「出聲」半邊，不落狀態檔） |
| `tools/lib/quota_meter.py` | `account_posture()` docstring 訂正（純文字，零邏輯改動）：`plan_fingerprint` 保持顯示用語意，隔離判定改由獨立的 `core_signature()` 負責 |
| `tools/tests/test_quota_policy.py` | 新增 `TestR93PlanChangeAdaptiveAmortization`（8 支測試，純函式面）；既有測試 `test_the_conversion_ratio_is_conservative_while_samples_are_thin` 的一行解包由 3 元改 4 元 |
| `tools/tests/test_context_budget_guard.py` | `QuotaGateIsWiredToTheBurnPathTest` 新增 6 支測試方法（端到端接線面）；既有測試 `test_it_says_why_an_empty_short_window_still_cannot_be_burned` 改為預先落兩筆同指紋歷史列（因 `SEED_OBSERVATIONS` 永久排除，舊版假設不再成立） |
| `docs/04_planning/ADR/ADR-XPLAT-009-quota-plan-change-adaptive-amortization.md` | 新檔，ADR 全文 |
| `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` | 版本表新增 v2.1.2 列；新增 §4.1.4（帳號／方案變更偵測） |

## 2. 規格覆核發現：`burn_ratio()` 的 `last_fp` 取法有缺陷（已訂正）

SD 規格 §1.1／§1.3(c) 逐字描述 `last_fp = rows[-1][3] if rows else None`，而
`pace_report()` 的既有呼叫順序是先 `record_burn(state)` 才呼叫 `burn_ratio(state)`。

**問題**：`record_burn` 成功寫入時，那一列就是「這一次呼叫自己剛寫的那一列」，
於是 `burn_ratio` 讀回的「最後一列」逐字等於本次呼叫寫入的那一列，
`last_fp == signature` 恆成立（因為兩者是同一次計算），`core_signature_change_note`
在真實換方案發生的當下反而永遠不出聲。

**實測（落地當回合，逐字貼上）**：

```
sig1 ('extra_usage', 'five_hour', 'seven_day')
call1 plan_note repr: ''
sig2 ('five_hour', 'seven_day', 'weekly_scoped')
call2 plan_note repr: ''
ledger contents:
{"fp": ["extra_usage", "five_hour", "seven_day"], "live": 0, ...}
{"fp": ["five_hour", "seven_day", "weekly_scoped"], "live": 0, ...}
```

兩次呼叫指紋確實不同（sig1 ≠ sig2），但 `plan_note` 兩次皆為空字串——DEF-200-114
要補完的「出聲」機制，若照 SD 規格逐字實作，會是**可以通過所有既有測試、但功能
本體是死碼**的狀態（因為當時尚未寫 B4 測試去驗證它）。

**修法**：`burn_ratio()` 內 `last_fp` 改由排除本次 `state.measured_at` 之後的
最後一列取得：

```python
prior = [r for r in rows if r[0] != state.measured_at]
last_fp = prior[-1][3] if prior else None
```

**訂正後實測**：

```
sig1 ('extra_usage', 'five_hour', 'seven_day')
call1 plan_note repr: ''
sig2 ('five_hour', 'seven_day', 'weekly_scoped')
call2 plan_note repr: '⚠️ 偵測到帳號軸組合改變（extra_usage+five_hour+seven_day → five_hour+seven_day+weekly_scoped）：攤提正在用新樣本重新累積\n'
sig3 ('five_hour', 'seven_day', 'weekly_scoped')
call3 (same sig as call2) plan_note repr: ''
```

三段式行為正確：首次無基準不出聲／真的換指紋才出聲／同指紋不重複出聲。此修正已
反映在 `tools/lib/quota_gate.py::burn_ratio` 與 ADR-XPLAT-009 §2.4，並由
`test_plan_note_fires_only_on_a_real_signature_change`（B4）鎖住。

## 3. 紅綠自證（逐字）

### 3.1 純函式面（`filter_by_signature`）

**RED**（把 `filter_by_signature` 暫時改成不做任何過濾，模擬 DEF-200-122 修復前）：

```
9 failed, 5 passed, 146 deselected, 2 subtests passed in 0.27s
FAILED ...test_estimate_ratio_on_a_fresh_signature_falls_back_safely
FAILED ...test_filter_by_signature_excludes_none_even_when_signature_is_empty
FAILED ...test_filter_by_signature_is_symmetric_for_shrink_and_grow
SUBFAILED ...test_seed_observations_never_enter_any_pool (×3 signature)
SUBFAILED ...test_cross_signature_isolation_end_to_end (×3 target)
```

**GREEN**（還原正確實作）：

```
8 passed, 146 deselected, 8 subtests passed in 0.10s
```

### 3.2 端到端接線面（`burn_ratio` 的 `plan_note`）

**RED**（改回 SD 規格逐字版 `last_fp = rows[-1][3] if rows else None`）：

```
FAILED test_plan_note_fires_only_on_a_real_signature_change
AssertionError: '⚠️ 偵測到帳號軸組合改變' not found in ''
```

**GREEN**（還原 `prior = [r for r in rows if r[0] != state.measured_at]` 修法）：

```
12 passed, 377 deselected in 0.37s
```

## 4. LOC 護欄層凍結面（`tools/tests/*.py`，84149 行棘輪）處置

落地當輪精確量測（以 Edit 呼叫的 old_string/new_string 逐次核算，不受併行編輯
干擾）：本次對 `test_quota_policy.py` 淨增 **91 行**（新測試類別 90 行＋
`import json` 1 行）；對 `test_context_budget_guard.py` 淨增 **106 行**
（B 系列測試方法 91 行＋既有測試訂正 15 行）。

**本輪未對該棘輪的持有面（`_FROZEN_GUARD_LINES`／`_GUARD_LINES_REPIN_LOG`，
皆位於 `tools/tests/test_adr_xplat001_c1c2_lock.py`）做任何重釘或搬史料**，
理由：落地過程中實測該檔正被另一個並行進程即時改寫（同一 session 內三次
`stat`／`git diff` 採樣顯示 mtime 與 diff 內容持續變動，且該檔已有一則
R92 修復包留下的 repin log，明載「本列不涵蓋 `test_quota_policy.py`……
其增量屬另一並行包正在進行中的工作；依本表既有紀律『重釘一律由收尾包在
所有包停工後做一次』，其帳留待收尾窗口核實後一併重釘」）。同一輪內，該檔
自身也存在與本次改動無關的既存紅燈（R90/R91/R92 連續正淨額 streak 上限
違反），與 R93 無關。

依 CLAUDE.md 鐵律七「常數／史料／消費端不在同一持有面時不得派給並行包」，
本次交付遵循收尾窗口統一重釘的既有慣例，將本輪淨增的 91＋106＝197 行
一併留待收尾窗口與其他並行包的淨額合併核實與重釘，不在本次交付內單獨處理。

## 5. `SEED_OBSERVATIONS` provenance 覆核

`docs/06_quality/CrossPlatform_R86_Pace_Calibration.md` 全文檢索「fp」「指紋」
「fingerprint」「signature」等字樣，**零命中**——確認該校準文件從未記錄過
量測當時的核心方案指紋，回填等於偽造 provenance，故本輪對 `SEED_OBSERVATIONS`
的處置是承認永久退場（`fp=None`），而非嘗試回填。

## 6. 帳本收尾：DEF-200-122／DEF-200-114 原狀態欄逐字保全

主檔 `docs/06_quality/AutoSDD_Defect_Log.md` 兩列受 `ROW_MAX_BYTES=700` 管，
瘦身前原文逐字保全於此（收尾窗口動作，非本包持有面）。

### DEF-200-122（結案前，694B）

- **分流欄**：未修。🔴 併立**修憲提案候選**：PRD §4.1.3（`:250`）只規定向下
  不連續，**未把「軸集合／方案指紋變更」列為燃燒率作廢事件** ⇒ 屬憲法缺口，
  須走修憲程序（四方全同意才改 PRD）。修法動取數層，需第三方複審
- **狀態欄**：open（承接輪次：**R93**）
- **結案理由**：本 ADR §2.1／§2.2 的分區過濾已消解立案時的原始症狀（`seven_day`
  22→86 跨方案假斷點），機械物 `filter_by_signature`／`core_signature` 存在
  且回歸鎖（`TestR93PlanChangeAdaptiveAmortization` 8 支＋
  `QuotaGateIsWiredToTheBurnPathTest` 新增 6 支）當回合親測綠：
  `tools/tests/test_quota_policy.py -q` → `154 passed, 300 subtests passed`
  rc=0；`tools/tests/test_context_budget_guard.py -q` →
  `381 passed, 8 skipped, 146 subtests passed` rc=0。憲法缺口半邊
  （PRD §4.1.3 修憲提案）不在本次落地範圍內，維持原分流欄記載，不隨結案抹去。

### DEF-200-114（原已 fixed@R89，本輪僅補交叉引用）

- **分流欄**：只訂正假 docstring；修法須動取數層需第三方複審。🔴 R89 收尾
  訂正原「劃界」（同方案兩帳號指紋相同⇒抓不到）：**本次不適用**，live 指紋
  已變（`extra_usage` 消失、`weekly_scoped` 出現）⇒ 抓得到，只是沒人看
- **狀態欄（結案前）**：fixed@R89：詳§F-114
- **交叉引用理由**：`account_posture()["plan_fingerprint"]` 宣稱的「方案變更
  ⇒ 燃燒率作廢重學」用途，機制本體已由本 ADR §2.2 的 `core_signature`（另一
  個獨立指紋，服務攤提過濾而非顯示）落地接線，非同一份程式碼但解決同一個
  使用者訴求；ADR §2.2 明文「這與 `account_posture()["plan_fingerprint"]`
  是兩個刻意分開的東西」，故本列本體仍是「docstring 訂正、機制未動」，
  只補一筆指向 DEF-200-122 的交叉引用。
