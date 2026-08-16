# ADR-XPLAT-009：額度攤提的方案／帳號變更適配

## 狀態
Accepted（R94：四方複審 Architect／SA／SD／QA 全數 APPROVE，含兩輪 REJECT→修復→
複驗；`account_key` 訊號已採納並落地，見 §7 R94／SA-2／D1 訂正段）

## 1. 背景

`tools/lib/quota_pace.py` 的跨窗攤提換算比 `r`（R86 落地，見
`docs/06_quality/CrossPlatform_R86_Pace_Calibration.md`）從
`~/.autosdd/traces/quota_burn.jsonl` 的歷時落款差分推估，該檔**永不輪替、
永久持久**（ADR-XPLAT-004 §2.6 endurance 決策的下游）。

兩筆既有缺陷指出同一個根因的兩面：

- **DEF-200-114**（R89 立案，docstring 訂正已 fixed@R89，機制本體未修）：
  `quota_meter.account_posture()` 的 `plan_fingerprint` 宣稱可用於「方案變更 ⇒
  燃燒率作廢重學」，該用途零實作。
- **DEF-200-122**（R89 立案，本 ADR 落地後 fixed@R93，狀態以帳本為準）：
  `quota_pace.segments()` 的翻頁啟發式只認**下降**為斷點，對換方案／換帳號
  造成的**上升**跳變結構上失明（實測：`seven_day` 22→86 於 10 分鐘內、
  `live=0`，物理上不可能是真燃燒，照樣被併入同一段落估計 `r`——此為立案時
  的原始症狀，已由 §2.1 分區設計消解）。

掌舵者訴求：**「大→小」與「小→大」兩個方向的帳號容量變更都必須被攤提正確
適配**，不得讓跨方案的樣本污染同一個估計池。

## 2. 決策

### 2.1 分區優於偵測

不做「偵測換方案事件並主動重置狀態」（Architect Plan B 的狀態檔輪替半邊），
改為**分區**：每一列落款帶一個核心方案指紋 `fp`，`estimate_ratio()` 前先
以「當前指紋」過濾出同池樣本。方向對稱性由分區的性質保證——跨指紋的樣本
結構上不會落在同一段，不需要教會 `segments()` 認識「上升也算翻頁」。

### 2.2 指紋語意：只算 `KNOWN_KINDS` 內的桶名集合

`core_signature(state)`（新，`tools/lib/quota_gate.py`）：

```
tuple(sorted({a.kind for a in state.axes if a.kind in quota_policy.KNOWN_KINDS}))
```

理由：`quota_policy.KNOWN_KINDS` 是既有的「哪些桶是我們認得的分類」判準
（R89／SA 複審 B-3 立案），未知桶名的增減依既有紀律定性為 **schema 演進**
（例：`nimbus_quill` 由無值代號變成真值），已由既有 `drift_against()`／
`NOTE_UNKNOWN` 通報，不該觸發攤提重置；已知桶名的增減才是換方案/換帳號的
訊號（DEF-200-114 觀測案例：`extra_usage` 消失＋`weekly_scoped` 出現）。

**這與 `quota_meter.account_posture()["plan_fingerprint"]` 是兩個刻意分開
的東西**（同 `CREDIT_POOL_KEYS`／`FALLBACK_KINDS` 的既有判例：關係不是相等）：
後者是給人看的顯示用指紋（含全部桶名，服務 `posture_line()` 的診斷可讀性），
前者是判定用、只服務攤提過濾。`account_posture()` 本身**不改動**其內容，
只訂正 docstring 裡已失效的「用途」宣稱。

### 2.3 舊格式落款與 `SEED_OBSERVATIONS` 的處置：`None` ＝永久排除

`rows_from_jsonl()` 對缺席 `fp` 鍵的舊列（本次落地之前寫下的所有既有落款）
回 `None`；`filter_by_signature()` 對 `fp is None` 的列**一律排除**，即使
目標 signature 恰好也是 `()`。`SEED_OBSERVATIONS`（R86 唯一一筆外部校準基準）
比照辦理，一併標記 `fp=None`——因為 `CrossPlatform_R86_Pace_Calibration.md`
全文查無指紋 provenance（R86 版本報告「已有 provenance 可回填」的說法經
本輪覆核為失實陳述），無法誠實回填，只能承認退場。

**這是刻意的信心度倒退**：落地當下樣本池可能因此低於
`_ROBUST_SEGMENTS=3`，退回既有的 min-based 保守估計，直到新指紋下累積出
真實樣本。方向仍是安全的（保守而非放寬），且自癒（隨查詢次數增加而恢復）。

### 2.4 出聲不輪替（Plan B 的一半）

`quota_messages.core_signature_change_note(last_fp, current_fp)`：純渲染，
讀落款最後一列的 fp 與這次的 fp 比對，指紋不同即在 `--pace` 輸出附加一行
提示。**不新增任何持久狀態檔**——判準與資料都是 Plan A 過濾邏輯的副產品，
零額外 I/O。這是 SA 裁決保留的部分：Architect Plan B 的「事件 + 輪替檔 +
歸檔」多做的東西沒有換到額外偵測涵蓋率（判準來源相同），故只留「出聲」，
不做狀態檔輪替。

🔴 **落地時發現並訂正的一處規格缺陷**（實作面，非決策面；記錄於此供複審）：
`pace_report()` 的既有呼叫順序是先 `record_burn(state)` 才呼叫
`burn_ratio(state)`，若 `last_fp` 逐字取「落款最後一列」，則在 `record_burn`
成功寫入的多數情況下，那一列**正是本次呼叫自己剛寫下的**，導致
`last_fp == signature` 恆成立、`core_signature_change_note` 在真實換方案
當下反而**結構上永遠不出聲**（雙時刻真實驗證：兩次不同指紋呼叫，
`plan_note` 兩次皆為空字串）。修法：`burn_ratio()` 內 `last_fp` 改由
**排除本次 `state.measured_at`** 之後的最後一列取得，使其真正反映「上一次
量到的指紋」而非「這一次剛寫的指紋」。此修正已在 `tools/lib/quota_gate.py`
落地並以 `QuotaGateIsWiredToTheBurnPathTest::
test_plan_note_fires_only_on_a_real_signature_change` ＋
`test_plan_note_is_silent_on_the_very_first_reading`（見 §5〈驗收判準清單〉C-10）
鎖住三段式行為（首次無基準不出聲／真的換指紋才出聲／同指紋不重複出聲）。

## 3. 被否決的方案

| 方案 | 為何否決 |
|---|---|
| Plan B 全案（顯式偵測事件 ＋ 主動輪替落款檔 ＋ 出聲） | 多一個持久狀態檔＝多一個新的失效面；判準與 Plan A 完全相同（皆比對 `plan_fingerprint`），多做的部分沒有換到額外偵測涵蓋率。違反 Simplicity First |
| 裸 tuple 相等（不分 `KNOWN_KINDS`） | SA 複審實測 `nimbus_quill` 在兩次觀測之間由無值代號變成有真值——單純的 schema 演進就足以改變裸指紋，會讓功能在正常運作時頻繁誤觸發，比不修還吵 |
| 只認「移除既有桶」為換方案訊號 | 結構上漏掉「小→大」情境裡只新增已知桶、不移除任何桶的那一類真實案例，違反掌舵者「兩個方向都要涵蓋」的訴求，也未通過雙向對稱驗收 |
| SEED_OBSERVATIONS 回填猜測指紋 | 校準文件查無指紋 provenance；偽造一個猜的指紋等於偽造 provenance（同 `_keychain_token` 拒絕送出降解字串當 token 的既有判例） |
| 修改 `segments()` 使其認上升為翻頁 | 分區設計下這支函式的既有邏輯已足夠（跨指紋樣本結構上不會同段），改它是多餘的複雜度，且會製造新的假陽性風險（單指紋內的真實抖動不該被判成翻頁） |

🔴 **R93 二次訂正：新增一列——`account_key` 併入指紋（非被否決，本輪已採納）**。
落地當下獨立 Architect 複審 REJECT 指出上表與 §6 未引用已存在的 R90 實測證據，
下表補記本輪的技術判斷與現查依據（不放進「被否決」欄，因為它是本輪真的落地的方案）：

| 方案 | 判斷 |
|---|---|
| `account_key = sha256(org-id:workspace-id)[:12]`，併入 `core_signature()`（前綴標籤＋既有桶名集合，互補） | **已採納**。可行性現查（本輪複測，非採信轉述）：對本機真實帳號跑 `fetch_usage()`，回應標頭確實含 `anthropic-organization-id`／`anthropic-workspace-id`，與 R90 §2.5 記錄的值逐字相同；零額外網路呼叫（同一次既有請求）、零額外 token、不涉憑證處理（標頭非憑證，雜湊後更不是）。解決 R90／Architect 指出的兩個盲區（同方案換帳號、不同方案桶名集合相同），且與既有桶名分區**互補**而非取代——見 §6 |
| 只用 `account_key` 取代桶名分區（不再看 `KNOWN_KINDS`） | 否決。R90 §2.3 的方向 B（同帳號內指紋自然翻動 8 次）證明桶名分區仍捕捉到真實的方案容量差異訊號；account_key 不變不代表額度狀態沒變，拿掉桶名分區會讓真正的換方案訊號漏接 |
| 把 `account_key` 做成偵測換帳號的**顯式事件**（另開狀態檔記錄「上次帳號是誰」） | 否決，理由與 Plan B 全案同構：判準來源相同（併入指紋即可讓 `filter_by_signature()` 結構性拆開），多一個狀態檔只多一個失效面，沒有換到額外偵測涵蓋率 |

## 4. 機械物

- `tools/lib/quota_pace.py::filter_by_signature`（新）
- `tools/lib/quota_gate.py::core_signature`（新；R93 二次訂正併入 `account_key`）
- `tools/lib/quota_messages.py::core_signature_change_note`（新）
- 回歸鎖：`tools/tests/test_quota_policy.py::TestR93PlanChangeAdaptiveAmortization`
  類別（純函式面，8 支測試）；`tools/tests/test_context_budget_guard.py` 內
  `QuotaGateIsWiredToTheBurnPathTest` 新增 6 支測試方法（端到端接線面）——
  逐條判準見 §5〈驗收判準清單〉。
- 🔴 R93 二次訂正（Architect REJECT 承接，`DEF-200-114`）新增：
  - `tools/lib/quota_meter.py::account_key_of`（新，純函式）——
    `sha256(anthropic-organization-id:anthropic-workspace-id)[:12]`。
  - `tools/lib/quota_meter.py::fetch_usage`（回傳形狀變更：`(status, payload)` →
    `(status, payload, headers)`，第三格供 `account_key_of()` 消費）。
  - `tools/lib/quota_meter.py::measure_detail`（讀數 dict 新增 `account_key` 鍵；
    `SCHEMA` 不升版——純追加鍵，同 `is_active`／`severity` 既有先例）。
  - `tools/lib/quota_policy.py::QuotaState.account_key`（新欄，帶預設值
    `None`，既有建構點零改動）。
  - `tools/lib/quota_gate.py::read_quota`（從快取讀 `account_key` 填入
    `QuotaState`）。
  - 回歸鎖：`tools/tests/test_quota_policy.py::
    TestR93AccountKeyIsDerivedFromExistingResponseHeaders`（純函式面，4 支）；
    `tools/tests/test_context_budget_guard.py` 內
    `QuotaGateIsWiredToTheBurnPathTest` 新增 5 支測試方法（`core_signature` 併入
    account_key 的兩個盲區各一支、向後相容一支、`measure_detail` 端到端兩支）。
- 🔴 R94／D1（SD 獨立複審阻塞項承接，本輪**唯一**改動行為的地方）新增：
  - `tools/lib/quota_gate.py::core_signature`（`state.usable() and
    state.account_key is None` 時呼叫既有 `note_degraded("no-account-key", …)`；
    回傳值本身逐字不變，新增的只是一次副作用）。
  - 回歸鎖：`tools/tests/test_context_budget_guard.py` 內
    `QuotaGateIsWiredToTheBurnPathTest` 新增 3 支測試方法——
    `test_core_signature_reports_degraded_when_usable_but_account_key_is_missing`
    （正例，紅綠自證已跑：改回舊版會讓它失敗）、
    `test_core_signature_stays_silent_when_account_key_is_present`（控制組①：
    帳號指紋齊全不准吵）、
    `test_core_signature_does_not_double_report_an_unusable_state`（控制組②：
    `usable()==False` 時不得再蓋一次「量不到」的聲）。

## 5. 驗收判準

🔴 **R94／SA-1 訂正（獨立 SA 複審 REJECT 承接）**：本節此前指向一份「SD 規格文件
〈驗收判準清單〉」，而全庫 `grep -rln "驗收判準清單" docs/` 查無此檔——那份規格
只存在於工作流內部 agent 的暫時對話中，從未落磁碟，複審者無法獨立核驗。本節
現在**是**驗收判準的唯一的家（不再指向任何外部檔案），逐條由既有回歸測試反推
整理，每一條都附至少一支現有測試的完整定位（`類別::方法`）。

### A. 分區判準（`quota_pace.filter_by_signature`／`estimate_ratio`）

回歸鎖類別：`tools/tests/test_quota_policy.py::TestR93PlanChangeAdaptiveAmortization`

| # | 判準 | 測試 |
|---|---|---|
| A-1 | 落款 `fp` 逐字往返（寫什麼讀回什麼） | `test_row_of_round_trips_the_signature` |
| A-2 | 本輪落地前的舊落款（無 `fp` 鍵）必須解析成 `None`，不得猜成 `()` | `test_legacy_rows_without_fp_key_parse_to_none` |
| A-3 | `fp is None` 的列一律排除，即使目標 signature 恰好也是 `()` | `test_filter_by_signature_excludes_none_even_when_signature_is_empty` |
| A-4 | **雙向對稱**：「大→小」（桶消失）與「小→大」（桶新增）都必須被拆開、不得混池 | `test_filter_by_signature_is_symmetric_for_shrink_and_grow` |
| A-5 | `SEED_OBSERVATIONS` 永不進入任何指紋池 | `test_seed_observations_never_enter_any_pool` |
| A-6 | 陌生指紋（無同池樣本）⇒ 安全退回「無可用區段」，不得瞎猜 | `test_estimate_ratio_on_a_fresh_signature_falls_back_safely` |
| A-7 | **floor 不變式**（本 ADR §6 D5 論證的直接回歸鎖）：`shown_pct >= raw_pct` 不因換算比 `r` 的來源改變而破 | `test_the_amortization_floor_survives_arbitrary_ratio_sourced_from_a_filtered_pool` |
| A-8 | 三個以上相異指紋交叉隔離，互不污染 | `test_cross_signature_isolation_end_to_end` |

### B. `account_key` 純函式面（`quota_meter.account_key_of`）

回歸鎖類別：`tools/tests/test_quota_policy.py::
TestR93AccountKeyIsDerivedFromExistingResponseHeaders`

| # | 判準 | 測試 |
|---|---|---|
| B-1 | 兩個標頭皆在 ⇒ 確定性短雜湊，且與 R90 §2.5 一手實測值逐字相符 | `test_both_headers_present_yields_a_deterministic_short_hash` |
| B-2 | R90 §2.5 記錄的兩個真實帳號，key 必須不同 | `test_two_real_accounts_from_r90_give_different_keys` |
| B-3 | 任一標頭缺席／空白／非字串 ⇒ 一律回 `None`，不得猜 | `test_either_header_missing_or_blank_is_unmeasurable` |
| B-4 | 標頭不是憑證：雜湊後的輸出不得逐字含任一原始標頭值 | `test_the_headers_are_not_credentials_and_never_appear_in_the_key` |

### C. 端到端接線面（`tools/lib/quota_gate.py` 掛進 hook 的那條路）

回歸鎖類別：`tools/tests/test_context_budget_guard.py::
QuotaGateIsWiredToTheBurnPathTest`

| # | 判準 | 測試 |
|---|---|---|
| C-1 | `PostToolUse` matcher 必須涵蓋燒額度那條路（`Read`／`Bash` 至少在內） | `test_the_post_tool_use_matcher_covers_the_burn_path` |
| C-2 | 額度判定入口不得被 `blocking`（扇出名單）罩住，且必須把 `event` 傳下去 | `test_the_quota_call_is_no_longer_gated_on_the_fanout_edge` |
| C-3 | `PostToolUse` 在 halt 帶必須寫任務書並在 stderr 出聲 | `test_post_tool_use_at_halt_writes_a_plan_and_says_so` |
| C-4 | halt 副作用（寫任務書＋spawn 武裝）每個 reset 視窗只跑一次，不得 spawn 風暴 | `test_the_halt_side_effects_run_exactly_once_per_reset_window` |
| C-5 | halt 帶不得搶占 context 哨兵的武裝時機 | `test_quota_halt_does_not_preempt_the_context_sentinel` |
| C-6 | `PostToolUse` 絕不記派發帳（同一次 `Task` 不得被 Pre／Post 各記一次） | `test_post_tool_use_never_charges_the_dispatch_ledger` |
| C-7 | `core_signature()` 只算 `KNOWN_KINDS` 內的桶名，未知桶不參與分類 | `test_core_signature_reflects_only_known_kinds` |
| C-8 | `record_burn()` 落款帶的 `fp` 必須等於當下 `core_signature()` | `test_record_burn_writes_the_current_signature` |
| C-9 | `burn_ratio()` 排除舊指紋樣本，不得混進當前估計池 | `test_burn_ratio_excludes_a_prior_different_signature` |
| C-10 | `plan_note` 三段式：史上第一筆不出聲／真的換指紋才出聲／同指紋不重複出聲（§2.4 規格缺陷修正的直接回歸鎖） | `test_plan_note_fires_only_on_a_real_signature_change`、`test_plan_note_is_silent_on_the_very_first_reading` |
| C-11 | `--pace` 零 token：快取新鮮時新增的過濾/比對邏輯不得多打端點 | `test_pace_report_still_reads_only_cache_no_network` |
| C-12 | `account_key` 缺席（舊快取／標頭缺席）⇒ 逐字退回今天的桶名指紋，行為不變 | `test_core_signature_falls_back_to_bare_kinds_without_an_account_key` |
| C-13 | **R94／D1**：`state.usable()` 為真但 `account_key is None` 時必須觸發 `note_degraded()`；`account_key` 齊全、或 `usable()==False` 時皆不得誤觸發 | `test_core_signature_reports_degraded_when_usable_but_account_key_is_missing`、`test_core_signature_stays_silent_when_account_key_is_present`、`test_core_signature_does_not_double_report_an_unusable_state` |
| C-14 | 同方案換帳號（kind 集合逐字相同）時指紋仍必須拆開（R90／Architect 盲區①） | `test_core_signature_separates_two_accounts_with_the_identical_known_kinds` |
| C-15 | 不同方案但桶名集合恰好相同時指紋仍拆得開（R90／Architect 盲區②） | `test_core_signature_separates_different_plans_with_coincidentally_equal_kinds` |
| C-16 | `measure_detail()` 端到端把回應標頭的 `account_key` 接進讀數；標頭缺席時讀數的 `account_key` 為 `None` | `test_measure_detail_wires_the_account_key_into_the_reading`、`test_measure_detail_reports_none_account_key_without_identity_headers` |

驗收方式：`pytest tools/tests/test_quota_policy.py tools/tests/test_context_budget_guard.py -q` 全綠即代表以上 28 條逐一通過（本節不再另立「通過標準」文字，測試的斷言本身就是判準）。

## 6. 已知限制（照實寫，不粉飾）

🔴 **R93 二次訂正（獨立 Architect 複審 REJECT 承接，`DEF-200-114`）**：本節第 1 點
「需帳號識別（涉及憑證處理），另案」在落地當下**未引用 repo 裡已存在、已 commit
（`982adf4`）的實測證據** `docs/06_quality/Quota_R90_CrossAccount_Experiment.md`
§2.3-2.4——該文件用真實 Pro→Team 換帳號資料，對 §2.2「只算 `KNOWN_KINDS` 桶名集合」
的指紋語意做了**雙向證偽**：

- **偽陽性（R90 §2.4）**：同一份落款裡，真實換帳號那一筆的差異軸
  `['extra_usage', 'weekly_scoped']`，與**同帳號**內另外兩次自然翻動（相隔 1341
  分鐘與 618 分鐘）**逐字相同**——3 次指紋翻動命中裡 2 次是假陽性。根因：
  `extra_usage`／`weekly_scoped` 這兩個已知桶的有無，取決於額度狀態（餘額用盡／
  無 scoped 額度），不是帳號身分。
- **偽陰性（R90 §2.2）**：37 列落款中，切帳號**前**的 35 列裡有 **10 列（29%）**
  的指紋與新帳號的指紋**逐字相同**，且這是 **Pro→Team 跨方案**（不限同方案）。

⇒ **kind 集合本身不具備身分鑑別力**，只能捕捉「桶集合真的變了」這件事（換方案的
容量差異訊號），不能捕捉「帳號變了但桶集合恰好沒變」。§2.2 分區設計因此**保留**
（跨指紋樣本結構上不會混池，仍是安全方向），但不再單獨承擔「偵測換帳號」這個角色。

**正解已採納**：`account_key = sha256(anthropic-organization-id:
anthropic-workspace-id)[:12]`（R90 §2.5 提出、本輪 `tools/lib/quota_meter.py::
account_key_of()` 落地）。兩個標頭**就在 `fetch_usage()` 已經在發的那次回應標頭
裡**（一手實測，R90 §2.5 與本輪複測皆同），**不涉憑證處理**（標頭不是憑證，
雜湊後更不是）、**零額外網路／token**。`quota_gate.core_signature()` 在量得到
`account_key` 時把它併入指紋（前綴標籤＋既有桶名集合，互補而非取代）：

1. **同方案換帳號（kind 集合逐字相同）**——本輪解決：account_key 不同 ⇒ 指紋不同。
2. **不同方案但桶名集合恰好相同**（本節此前漏列的邊界，本次補齊；獨立 Architect
   複審第二個較小缺漏）——當它對應到不同帳號（org／workspace 不同）時本輪一併
   解決；若是**同一個** org／workspace 下方案原地變更、kind 集合又恰好沒變，
   account_key 不會變化，此殘餘邊界與既有 `account_posture()` 劃界同型，仍是
   結構性盲區（下方第 1 點）。

修訂後的殘餘限制：

1. **同一 org／workspace 下方案原地變更、且 kind 集合恰好不變時仍抓不到**——
   account_key 與桶名集合皆不變，需要伺服器揭露方案本身的識別欄位（payload 現況
   無此欄，見 `quota_meter.account_posture()` 對 `plan_fingerprint` 的既有劃界）。
   範圍已由「同方案換帳號」全類縮小到這個更窄的殘餘情境。
   🔴 **R94／D5 補記（下游安全網，不是這一點的解法）**：即使分區在這個殘餘情境
   下失靈——把不同方案的樣本混進同一個 `burn_ratio()` 估計池，算出一個受污染
   的換算比 `r`——下游 `tools/lib/quota_pace.py::band_inputs()` 的 floor 不變式
   仍然無條件成立：`shown = max(raw_pct, min(ceiling, 100*raw_pct/allowance_pp))`
   （見該函式上方的方向鎖註解），故**`shown_pct >= raw_pct` 恆成立**——
   `allowance_pp <= 100` 使 `100*raw/allowance >= raw`，`r` 被污染、被誤設，
   甚至被 `AUTOSDD_*` 環境變數改成任意大的值，都不能讓餵給 `pct_band()` 的水位
   跌破伺服器給的原始讀數。也就是說，這個殘餘偵測盲區最壞只會讓攤提「調得
   不夠準」（多算或少算保守幅度），**結構上不可能**把一個真實的高水位顯示成
   更低、進而放寬節流——後者才是必須阻斷的方向。
2. **`account_key_of()` 量不到時（標頭缺席）逐字退回今天的桶名指紋**——不是新的
   失效面，是安全預設：`core_signature()` 對 `account_key is None` 一律不改變
   既有行為，不得因為量不到身分訊號就更保守或更寬鬆。
   🔴 **R94／D1 訂正（獨立 SD 複審阻塞項承接）**：「不是新的失效面」這句話沒錯，
   但它此前**零觀測性**——退回邏輯本身沒變，只是這條路徑在此之前完全靜默：
   `state.usable()` 為真（量測本身成功）卻 `account_key is None` 時，退回裸桶名
   指紋這件事無聲發生，而它正是 R90 §2.4 已實測「29%（10/35）跨方案指紋逐字
   相同」那個碰撞面會真實命中的路徑。已比照本節其餘每一種退化路徑（stale-cache／
   schema-mismatch／no-credentials／ledger-unreadable／meter-crashed／
   policy-invalid）接上 `note_degraded()`（`tools/lib/quota_gate.py::
   core_signature()`，source＝`no-account-key`，TTL 閂鎖每 source 180 秒僅出聲
   一次）；`state.usable()==False` 時**不**出聲——那個狀態的「量不到」已由別的
   路徑說過，這裡再出聲只是稀釋訊號。**這是本輪唯一真的改動行為的地方**（新增
   一次副作用呼叫，`core_signature()` 的回傳值本身逐字不變）。回歸鎖：
   `QuotaGateIsWiredToTheBurnPathTest::
   test_core_signature_reports_degraded_when_usable_but_account_key_is_missing`
   （紅綠自證：改回舊版純 `return kinds` 會讓它失敗）＋ 兩支控制組
   （`account_key` 齊全時、`usable()==False` 時皆不准出聲）。
3. **`KNOWN_KINDS` 本身是會成長的分類表**：某輪把一個今天的未知桶正式收進
   `KNOWN_KINDS` 時，那次程式碼升版會讓歷史指紋與當下不再相符，觸發一次性、
   方向安全的冷啟動。有界、自癒，不是每輪都會發生。
4. **快取 TTL 身份盲區**：`read_quota()` 的 180 秒新鮮度判斷只比對時間差，
   不比對帳號/方案身份——換帳號後 ≤180 秒內可能仍採信舊帳號的讀數。有界
   （下次量測自癒），本輪不修，文件化為已知殘餘風險。
5. **換方案當下在跑的 agent 不受影響**：cap 只作用於未來派工決策，不會回頭
   殺掉已派出、尚在執行的 agent；若新方案更小，它們會繼續消耗新方案的真實
   配額直到自然結束。這是物理事實，不是程式缺陷。
6. **`SEED_OBSERVATIONS` 永久退場是信心度倒退**：落地當下樣本池可能低於
   `_ROBUST_SEGMENTS=3`，需要真實樣本重新累積。
7. **`account_key` 上線那一刻對既有樣本池是一次性的信心度倒退**：本輪之前寫下的
   落款 `fp` 皆無帳號標籤，指紋形狀（有無 account_key 前綴）改變的當下，歷史樣本
   結構上不再與新指紋相符——與第 3 點 `KNOWN_KINDS` 成長同型，一次性、方向安全、
   自癒。
8. **`account_key` 跨機器／同帳號多 workspace 的穩定性未驗**（R90 §2.7 誠實劃界，
   本輪沿用未擴大驗證面）：若同一個真實帳號在不同機器上量到不同的
   `anthropic-workspace-id`，或一個帳號本身跨多個 workspace 使用，`account_key`
   會把它們判成不同身分——方向仍安全（過度分區只讓樣本池變小、退回保守估計，
   不會讓攤提放寬），但尚未有多機器/多 workspace 的一手觀測可以確認之。
9. **`account_key_of()` 對「同一帳號多次成功呼叫」的標頭穩定性從未驗證**
   （R94／D2，獨立 SD 複審提出）：本 ADR 與 R90 §2.5 皆只驗證過「標頭存在、
   雜湊值對映到正確的帳號」這一刻的橫切面，未驗證同一帳號在不同時間點反覆
   呼叫 `fetch_usage()` 時 `anthropic-organization-id`／`anthropic-workspace-id`
   是否逐次一致（例如負載平衡或多區域路由是否可能讓同一帳號的連續請求拿到
   不同的 workspace 標頭）。若標頭本身不穩定，`core_signature()` 會把同一個
   真實帳號誤判成多個不同分區——與第 8 點「跨機器／多 workspace」同型但更窄
   （同機器、同帳號、連續呼叫）。誠實記載為**未驗證前提**，本輪不新增驗證
   機制（成本與本次任務書射程不成比例，留待下一輪有需要時再開）。
10. **經常性跨帳號使用會讓分區碎片化、永久退回保守估計**（R94／D4）：
    `burn_ratio()` 的估計池只取同指紋樣本；若同一部機器頻繁在多個帳號間切換
    （例如多租戶維運、CI 共用同一份 `~/.autosdd/traces`），每個帳號各自累積的
    同指紋樣本會被稀釋，長期低於 `_ROBUST_SEGMENTS=3`，攤提因此長期停留在
    min-based 保守估計、換算比 `r` 永遠學不起來。方向仍是安全的（保守而非
    放寬），代價是「頻繁跨帳號使用者」拿到的攤提精準度系統性低於「單一帳號
    穩定使用者」。本輪沒有請求要修，列為已知限制。

## 7. 承接

- `docs/06_quality/AutoSDD_Defect_Log.md`：`DEF-200-122` → `fixed@R93`；
  `DEF-200-114` 補一則交叉引用（機制本體已由本 ADR 落地，欄位語意本身
  維持原判——見 quota_meter.py docstring 訂正）。**本次交付未動帳本**（依
  任務書分工，帳本由另一 agent 負責），上述更新留待負責帳本的 agent 執行。
  🔴 **R93 二次訂正補記**：`DEF-200-114` 欄位語意「維持原判」這句話本身
  已被 R90 證據推翻並在本輪修正（見 §6、`quota_meter.account_posture()`
  docstring）——負責帳本的 agent 執行上述更新時，請一併把該列的判讀換成
  §6 開頭那段訂正文，不要沿用本節這句已作廢的舊措辭。**本包依任務書規定
  仍未動帳本**，本段只是把最新判讀交棒清楚。
  🔴 **R94／SA-2 訂正（獨立 SA 複審 REJECT 承接）**：上面兩段交棒到目前
  仍**未被執行**——帳本 `docs/06_quality/AutoSDD_Defect_Log.md:261` 的
  `DEF-200-114` 列今天仍只反映**第一次**訂正（`core_signature` 落地那次），
  完全沒提 `account_key`／R90 證據／「同方案換帳號已解決」。本包依約束仍
  **不得**改帳本，故把該列「狀態」欄應改成的**逐字草稿**留在這裡，供帳本
  負責窗口直接採用（ID／發現日期／發現情境／現象與證據／嚴重度／分流去向
  五欄不變，只替換「狀態」欄）：

  ```
  fixed@R89：詳§F-114 ｜R93 二次訂正（Architect REJECT 承接，取代上一版本
  欄位判讀）：R89 版「機制本體已由 ADR-XPLAT-009 §2.2 core_signature 落地
  （獨立指紋，非同一欄）」已被 `docs/06_quality/
  Quota_R90_CrossAccount_Experiment.md` §2.2-2.4 的真實 Pro→Team 換帳號
  資料證偽——單靠 `KNOWN_KINDS` 桶名集合對「同方案換帳號」偽陰性 29%
  （10/35，不限同方案）、對「同帳號自然翻動」偽陽性 2/3。正解已改採
  `account_key = sha256(anthropic-organization-id:anthropic-workspace-id)
  [:12]`（`quota_meter.account_key_of()`，取自 `fetch_usage()` 既有回應
  標頭，零額外網路／token、不涉憑證處理），已解決「同方案換帳號」與
  「不同方案桶名集合恰好相同」兩個盲區，桶名分區保留為互補訊號（非取代）。
  殘餘限制：同一 org/workspace 下方案原地變更且桶名集合恰好不變時仍抓
  不到（ADR-XPLAT-009 §6 第 1 點；下游 `band_inputs()` floor 不變式保證
  此殘餘盲區最壞只讓攤提偏保守，不會放寬）。R94：`account_key` 量不到
  （`state.usable()` 為真但 `account_key is None`）此前零觀測性的退化
  路徑已補 `note_degraded()`（ADR §6 第 2 點／§4）。詳見 ADR-XPLAT-009
  §2.2／§6／§4；交叉引用 DEF-200-122／§6
  ```

  **是否建議主控再派一次帳本收尾窗口：建議派**，理由三條（本包現查、非
  轉述）：
  1. `python tools/check_defect_log_crossref.py` 現查 `current_round()=93`，
     而本 ADR 本輪（D1 修復＋SA-1/SA-2 訂正）已在用 **R94** 標籤——帳本時鐘
     落後實際工作一輪；R94 的第一列一旦落地，crossref 目前對「承接輪次
     恰等於當前輪」那個 fail-open 窗口會關閉，屆時 `DEF-200-128` 等一批
     現時「承接輪次：R93」的列是否仍算有效承接，需要帳本窗口重新逐筆判定
     （現查：`python tools/check_defect_log_crossref.py 2>&1 | grep -c
     "fail-open 窗口"` → **27** 筆）。
  2. `DEF-200-128`（open，承接輪次 R93，內容是「§5a 待驗清單無可重跑載體」）
     本身尚未關閉——帳本窗口收尾時應一併判斷它要改派 R94 或已有可重跑載體
     可以結案，不應放著讓它在時鐘推進後變孤兒候選。
  3. 現查 `--unresolved-count` 未結存量 **77** 列（warn 門檻 86／fail 門檻
     98，尚未破線，非阻塞），但疊加上面兩點，累積到下一次自然收尾窗口的
     成本只會更高（同既有判例「發現可平行化、結案不能」：未結帳本單調
     成長是結構性的）。
- 落地前須完成四方複審（本 ADR 與 SA 複審皆援引 `DEF-200-114`／R87 教訓：
  修取數/攤提層不得由單一 agent 直接推進）。
- **護欄層 LOC 凍結面（`tools/tests/*.py` 棘輪）的收尾重釘**：本次交付對
  `test_quota_policy.py`／`test_context_budget_guard.py` 淨增約 91／106 行
  （測試碼，非生產碼）。落地當下該棘輪的持有面（`_FROZEN_GUARD_LINES`／
  `_GUARD_LINES_REPIN_LOG`，皆位於 `tools/tests/test_adr_xplat001_c1c2_lock.py`）
  正被另一個並行進程即時改寫（R92 修復包），依鐵律七「常數/史料/消費端
  不在同一持有面時不得派給並行包」，本次**不**對該棘輪做重釘或搬史料。
  🔴 **R93 二次訂正補記**：本包（Architect REJECT 承接）在該棘輪之外又對
  這兩支測試檔各自新增數支測試（`account_key` 純函式面 4 支＋端到端接線面
  5 支），同樣**未重釘**該棘輪常數。現查（本包當回合實測，非採信轉述）：
  `--print-guard-lines` 顯示淨額 **84386→84386（+0）**——`_FROZEN_GUARD_LINES`
  已由另一個並行收尾進程在本包工作期間同步更新到與磁碟一致，本包全程未曾
  改動 `test_adr_xplat001_c1c2_lock.py` 一行。留待收尾窗口在該進程完成後
  再核實一次總額是否仍與磁碟相符。
