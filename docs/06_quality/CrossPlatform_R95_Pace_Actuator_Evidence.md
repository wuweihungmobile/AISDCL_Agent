# CrossPlatform R95 — 配速致動器三合一：證據檔

> Pkg-C 持有面：`tools/lib/quota_pace.py`／`quota_policy.py`／`quota_gate.py`／
> `quota_messages.py`／`tools/tests/test_quota_policy.py`／本檔。
> 機械物＝`tools/tests/test_quota_policy.py` 的 `TestR95AmortizationSpeaksButDoesNotTightenBelowConverge`
> ／`TestR95ModelHintOnlyInTighteningBands`／`TestR95PaceIndexAndTunableCeiling` 三節。
> 章節依批次追加、序號非單調（本檔 §7 之後又見 §7-R95-*，是各批次落款的時間序，不重排
> ——重排會改寫既有搬遷點指回的座標）。

## §1 立案（掌舵者 2026-08-16 當面質疑，最高優先）

當日實測案例：`five_hour` 窗尾 33 分鐘、自軸僅 25%、`weekly` 46%（free band），
跨窗攤提卻因「本窗配額超支 −15.8pp」把 cap 壓到 1 ⇒ 派工被迫空等 reset。

掌舵者裁決此為**演算法缺陷**，三個理由：

1. `five_hour` 剩餘額度 reset 即作廢（**use-it-or-lose-it**）——窗尾把它省下來不會存進任何地方；
2. `weekly` 是**同一個消耗池**——把工作推遲到下一個 5h 窗做，週池消耗一樣多（推遲≠節省）；
3. 空等純浪費牆鐘——攤提的本意是「別讓短窗把長窗提前燒乾」，不是「長窗還很空時也不准用短窗」。

## §2 子任務 1：攤提窗尾行為修正（出聲不收緊）

### 2.1 設計

- 修法＝`quota_pace.amort_relaxed(amort, converge_pct)`：長窗自軸（`100 − remaining_pp`）
  **未達 converge 錨點**時，`band_inputs()` 回**原始水位**（不再調高餵給 `pct_band` 的值），
  但 `Amort` **照算照回**——`Decision.amort`、`--pace` 第三行（`explain()`）、燃燒落款一格不少，
  且 `explain()` 明文加註「出聲不收緊（本次未壓制短窗水位）」。
- **邊界取 converge 錨點（預設 70）而不是 notice（50）**：任務書原文「free band（未達
  converge 錨點）」的括號是操作性定義；converge＝掌舵者四錨點裡「開始收斂」的那條線，
  而攤提壓制本質上就是一種收斂手段——長窗自己都還沒到「該收斂」的水位，拿它的帳面
  去收斂短窗即為本案缺陷。錨點本身（`== converge`）算**收緊側**（fail-safe 方向，
  `test_at_or_above_the_converge_anchor_nothing_relaxes` 釘住含邊界）。
- 參數是**選配、預設 `None`＝逐字維持 R94 行為**：`band_inputs`／`resolve`／`explain` 的
  所有既有呼叫端（含全部既有測試）零改動、逐位元同值；只有生產路徑
  `quota_policy.axes_of()` 顯式傳 `p.converge_pct`。錨點跟著 `.env` 的
  `AUTOSDD_QUOTA_CONVERGE_PCT` 走，不另立第二個門檻常數。

### 2.2 (b) 跨窗記帳（設計筆記，本輪刻意不實作——簡單優先）

任務書允許 (b) 只落設計筆記若 (a) 已足以解決本案例；(a) 已解（實案 46% < 70 ⇒ 不收緊）。
若未來長窗自軸 ≥ converge 且仍出現「窗尾殘量被浪費」的實案，正確形態是把超支懲罰改為
**跨窗分期**而非本窗全程壓制：

- 落款已有逐列 `(ts, short, long)`（`quota_burn.jsonl`），可據以算出「上一窗實際超支多少 pp」；
- 把該超支攤到**未來 N 個窗**（N＝`windows_left`）的 allowance 上，而不是把本窗 shown 一路
  頂到 `halt−1`——即 `allowance' = per_window × r − carryover/N`；
- 方向鎖不變：`shown >= raw`、上界 `halt−1`、`allowance' <= allowance`（只收緊本窗配額的
  分子，不碰 `max(raw, …)` 那道地板）。
- 前置條件：per-window 超支的觀測樣本（今天 n≈0）。無樣本時實作它就是發明數字，故不做。

### 2.3 憲法檢查（必做項；結論＝**一條既有鎖的斷言都沒有改**）

逐條盤點與本案有交集的方向鎖（皆當回合實跑）：

| 鎖 | 釘什麼 | 本修正的關係 |
|----|--------|------------|
| `test_amortization_only_tightens_and_never_triggers_halt` | `shown >= raw`、上界 `halt−1`、長窗軸水位不被動 | 呼叫端不帶 `converge_pct` ⇒ 走 R94 原路徑，逐位元同值；其 fixture 長軸 75／99 皆 ≥ converge，就算帶錨點也不免除。斷言零改動 |
| `test_the_amortization_floor_survives_arbitrary_ratio_sourced_from_a_filtered_pool`（SA 條件④） | `shown >= raw` 不因 ratio 來源而破 | 免除分支回的是 `raw` 本身，`shown == raw` 仍滿足 `>=`。新增 `test_the_feed_never_drops_below_the_raw_pct_for_any_anchor` 把「任何 converge 值」也掃進同一條不變式 |
| `QC.defect_c_divergence`（R86 缺陷 C） | 攤提真的進得了 cap | fixture 長軸 75 ≥ 70 ⇒ 免除不觸發，逐格同值 |
| `QC.unlicensed_acceleration`（R86 方向鎖本體：無節省證據不得比 R85 絕對門檻版鬆） | 掃 (pct, minutes, kind) 網格 | 單軸母體、`ratio=None` ⇒ 攤提整段不參與；且免除只作用在**攤提調高水位**那一格，不碰 horizon ⇒ 結構上無交集 |
| `m3_problems`（M3 加入更緊的軸永不放寬） | 隨機軸集合的 cap 單調 | 母體桶名（`k0…k3`）文法解不出窗長＋`ratio=None` ⇒ 攤提從未參與該 property（**既有射程事實，非本輪引入**，見 §6 誠實劃界） |
| M3b／M3c／M4 | 覆寫、單調、fail-closed | 一行都沒碰（cap 階梯與 horizon fail-closed 邏輯零改動） |
| `TestR93PlanChangeAdaptiveAmortization` | 指紋分區 | `filter_by_signature`／`estimate_ratio` 零改動 |

**判定**：本修正不需要改任何一條既有鎖的斷言 ⇒ 無「靜默改鎖」問題。整包（含放寬語意
本身＝掌舵者裁決的授權放寬）原標注待四方複審；**已於 R107 四方複審通過（與 PRD v2.1.4
修憲批次併批點名，4×APPROVE_WITH_CONDITIONS，2026-08-28 落款；機械面同日重跑
`tools.tests.test_quota_policy` 全綠；紀錄＝`CrossPlatform_R107_Review.md`）**。

新行為為何仍 fail-safe：免除只在「長窗自軸 free/notice 帶」成立——那正是長窗自己的
`pct_band` 都還不節流的水位；免除後短窗回到自己的真實水位與 horizon 判定（缺陷 A/B 的
機制原封不動），並非回到「無限制」。

## §3 子任務 2：模型降級致動器（PRD §4.2.3，missing → 建議面落地）

- 設計出處：PRD §4.2.3 第 7 步「`U7d_model ≥ MODEL_DOWNGRADE_PERCENT` → 模型降級，併發
  不變」＋致動器表「模型層級降級：觸發＝`THROTTLING` 或 `U7d_model` 超標」＋§6 出廠值
  `MODEL_DOWNGRADE_PERCENT=50`。
- 落地形狀：`Decision.model_hint`（觸發軸 kind 逗號串；`""`＝無）＋
  `quota_messages.model_hint_line()`（`--pace` 渲染，空 hint 不印——free 帶印降級建議
  是一句假話）。**只建議不自動改模型**。
- 觸發（取樣面＝`gate`，保險軸不觸發——R89「保險池不得反客為主」同判）：
  ① 任一參與 cap 聚合的軸進 **converge 帶起**（≈PRD 的 THROTTLING 線，出廠值逐格同 70）；
  ② `MODEL_SCOPED_KINDS`（`weekly_scoped`／`seven_day_opus`／`seven_day_sonnet`）進
  **notice 帶起**（notice 錨點出廠值 50＝PRD `MODEL_DOWNGRADE_PERCENT` 出廠值，逐格對齊）。
- `MODEL_SCOPED_KINDS` 是寫死桶名清單，但**與「禁止寫死桶名清單」不衝突**（同
  `KNOWN_KINDS` 的辯護）：一行不參與分類／cap，過期的後果只是少（或多）一句建議，
  結構上不可能改變任何 cap／band／rec ⇒ fail-safe。
- 方向鎖：hint 在 `decide()` 內於 cap／rec／band **全部算完之後**才產生（建構順序保證，
  不是靠自律）；`test_the_hint_never_moves_a_single_decision_bit` 以 S4-10 釘值驗證。
- 同名辨析：hook 側 `context_budget_guard.model_hint`（context 窗長判定用的 harness 設定值）
  與 `Decision.model_hint`（額度降級建議）**同名不同物**，兩把尺不共用模組（R82／Q2-02），
  已在 `Decision` 欄位註解明文標注。

## §4 子任務 3：PACE_INDEX 比值與可調上限（PRD §4.2.8，partial → 落地）

- `quota_pace.pace_index(pct, minutes, window)`＝`utilization ÷ max(ε, elapsed_frac)`
  （PRD §4.2.8 原式；ε＝`_ELAPSED_FLOOR=0.01`，只防窗首發散，不參與方向判定）。
- **兩形式並存**（任務書允許的簡單整合）：`lead_pp` 差值仍是決策輸入（不對稱煞車＋anchor
  邊際的 pp 語意）；`pace_index` 供人讀與校準（對照 PRD 表列 CLI 內建參考值
  five_hour 1.25、seven_day 1.25/1.43/1.67），落 `explain()` 痕跡（`--pace` 第三行
  `短窗 pace_index=…`）。
- `AUTOSDD_QUOTA_PACE_CEILING`（`ENV_SPEC` 註冊、`--print-env-example` 可見、
  `.env.example` 已重生）：**下界 1.0**（低於 1 會把「還沒超支」判成超前、與節儉判定
  矛盾 ⇒ `load_policy` 出聲退預設）；**預設 1.0＝逐位元維持現行行為**（`burn_step` 的
  `ceiling <= 1.0` 短路保留既有 `lead > 0` 判定，
  `test_the_default_ceiling_keeps_the_shipped_burn_step_verbatim` 釘住）。
- 調高 ceiling 的效果與方向鎖：只把「超前 ⇒ 強制 far」放回**中性**
  （`tightest(relative, legacy)`），而中性永不比 R85 絕對門檻版鬆 ⇒
  `QC.unlicensed_acceleration` 在 `pace_ceiling=1e9` 下實跑 `unlicensed == []`
  （`test_a_raised_ceiling_releases_the_brake_but_never_grants_speed`）；「省」側一個字
  不讀 ceiling ⇒ 它放不出任何加速。

## §5 消費端影響面（實跑驗證）

- `tools.tests.test_quota_policy`：177 支全綠（新 +19）。
- `tools.tests.test_context_budget_guard`（`--pace`／`pace_report` 的消費端）：408 支全綠
  （skipped=8 為既有平台跳過）。
- `tools.tests.test_mac_readiness_r82`＋`test_platform_neutral_paths`（py39／編碼債面）：200 支全綠。
- 根層 `.env.example`＝生成物重生（M6 磁碟同步鎖住在本包持有的測試檔內，不重生即紅；
  該檔不在持有面清單但為 `quota_policy.ENV_SPEC` 的機械生成物，已在交件回報標注）。

## §6 誠實劃界

1. **M3「加入軸永不放寬」property 對攤提整段失明是既有事實**：其隨機母體桶名文法解不出
   窗長、且 `ratio=None` ⇒ 攤提在該 property 裡從未參與。本輪的免除分支因此也不在其射程
   內。理論上（R94 版即已如此）「加入一個更長窗、低水位的軸」可改變 total 軸的歸屬而使
   allowance 變大 ⇒ shown 變小——這在 R94 版就存在，非本輪引入；要補鎖需擴母體到可解析
   桶名＋帶 ratio，屬另案。
2. **模型分軌清單會過期**：`MODEL_SCOPED_KINDS` 漏掉未來新模型軌 kind 時，該軌只剩
   converge 帶那一條觸發（晚 20pp 才建議）；失效方向是「少一句建議」，不影響節流。
3. **hint 文字寫死 `sonnet/haiku`**：取任務書原文例句。未來若要按「當前在跑哪個模型」
   動態建議目標模型，需要 observed_model 進 `Decision` 的輸入面，本輪不做（PRD 該步
   `[需核對]` 也尚未核實訂閱方案的內建降級行為）。
3a. **notice 錨點調離 50 時降級建議線隨動**（R95 修復包 m8 補）：模型降級建議的觸發
   線錨在 notice 帶，錨點若被調離 50（`quota_policy` 門檻現查，不寫死數字），建議線
   跟著移動——這是刻意的耦合（建議面隨節流面走），不是漏釘常數；要釘死絕對百分比
   須先給出「錨動了建議不該動」的立案。
4. **護欄層行數棘輪（`_FROZEN_GUARD_LINES`）本輪會紅**：本包對 `tools/tests/` 的淨額
   ＝`test_quota_policy.py` **+154**（`git diff --numstat` 實測 +176/−22；判準本體 19 支
   測試，史料已按 R89 體例外移，見 §7）。
   該棘輪的重釘紀律明文「由收尾包在所有包停工後重釘一次並補 `_GUARD_LINES_REPIN_LOG`」，
   且鎖檔（`test_adr_xplat001_c1c2_lock.py`）不在本包持有面（鐵律七）⇒ 本包只登記淨額，
   不動鎖。同輪另有他包 +300（`test_context_budget_guard.py` +164、
   `test_block_destructive_git_r83.py` +136），收尾請合併對帳。

## §7 搬遷史料（R89 體例：判準理由留原檔，事故數字／立案敘事原文住這裡）

### 7.1 M1b 立案的複驗鏡實測數字（自 `test_quota_policy.py` M1b 節首搬入，原文）

> 複驗鏡實測：固定 weekly_all 57%@8233min、把 session 的 reset 從 1 分鐘掃到 6 天
> （**差 8640 倍**），`decide()` 的 cap/rec/band **逐格相同**（4/2/notice）；使用者錨點①
> 「0%+30m ⇒ 多派」在多軸下相異 rec 只有一個值，而且比中性基準（8）更小 ⇒ 方向相反。

### 7.2 M8-b 立案敘事與判準取捨（自 `test_quota_policy.py` M8-b 節首搬入，原文）

> 為什麼這一格值得一道鎖，而不是「今天兩邊相符就算了」：R83 本輪的 F2-① 任務書提出的修法
> 正是「把快取搬到不吃 TMPDIR 的固定家」。那個動作只改 meter 的話，adapter 會**靜默**讀不到
> 任何檔 ⇒ `_pick()` 回 `None` ⇒ `resume_wait_seconds` 回落寫死延遲、`TokenGuardPlugin`
> 的額度軸恆「量不到」，而 `None` 這個回傳值被 adapter 自己的測試釘成正確行為（同 SCHEMA
> 那一格的判例：「失效全綠、完全靜默」）。⇒ 搬家是可以做的，但它必須是**同一次** commit
> 動兩支檔，而這道鎖就是那個「同一次」的機械保證。
>
> 判準取「兩邊算路徑用的 token 序列相等」而不是「必須是 gettempdir」：後者會把家釘死在
> 今天這個選擇上，於是將來真的要搬家時，這道鎖自己會變成阻力（本 repo 對「鎖住了實作而
> 不是性質」有判例）。搬到 `~/.cache/autosdd/` 一樣綠——只要兩邊一起搬。

### 7.3 `quota_policy.py` 階梯 dict 壓縮的墓碑

`_base_cap`／`_base_rec` 兩張階梯 dict 由逐鍵一行（各 8 行）併為緊排（各 3 行），是
`guardrail_lib`（≤400 行）騰出 `pace_ceiling`／`model_hint`／`MODEL_HINT_BANDS` 淨增的
位置——**行為不變**（同一張表、同一組鍵值；同 R93 對 `_cap_for` 三行併一行的判例）。
壓縮後全套 177 支測試綠（含逐帶邊界掃描 `TestM3cHigherUsageNeverLoosensTheCap`）。

### 7.4 S4 參數表兩列沿革（R95 收尾窗口自 `TestTheTableIsProducedByTheRuleNotByHand` docstring 搬入，原文）

> 🔴 聚合規則改寫後，規格 S4 參數表有**兩列**與交件時的判定不同，照實記：
>   · 第 3 列：表寫 rec=4。舊的 `min(逐軸 rec)` 算出 2 ⇒ 當時被判成「抄寫失誤」；
>     新規則算出 **4** ⇒ **表原本就是對的**，那筆失誤是舊聚合造成的假象。
>   · 第 1 列：表寫 8、它自己的語意欄寫「被 weekly 的 8×0.5=4 壓下來」、舊式子算
>     出 4——三個數字互不相同。新規則算出 **16**：weekly 20% 落在 free 帶、根本
>     不是約束，而 session 30 分鐘後就 reset ⇒ 這正是使用者原句要的「多派」。

### 7.5 R82／C1 round-trip 立案（R95 收尾窗口自 M6 節首註解搬入，原文）

> 病：`env_example_problems()` 拿 `render_env_example()` **跟自己比**，從不呼叫消費者的
> 解析器 ⇒ 兩個家互相一致、都沒對消費者測。而消費者 `quota_gate.policy_env()` 當時做的是
> `partition("=")` + `strip()`，產生器產出的卻是 `KEY=值<補白>#說明`（同一行）。
> 複審鏡實測：把 `.env.example` 原封不動複製成 `.env`，**12 個帶值的鍵全部解析失敗**、
> 全部靜默退回預設；把 `AUTOSDD_QUOTA_HALT_PCT` 改成 99.5、額度 99% ⇒ **仍 rc=2 被擋**
> （生效的是預設 95）。而使用者的標準流程就是 copy 一份再改幾個值 ⇒ 這不是邊角案例。

## §8 設計依據索引

- PRD（憲法）：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`
  §4.2.3（閘門與致動器優先序；第 7 步模型降級）、§4.2.8（pace_index 與 CLI 內建參考值）、
  §6（`MODEL_DOWNGRADE_PERCENT=50`、`*_PACE_CEILING`）。本輪**未修憲**：三個子任務都是
  「實作沒照 PRD 做 ⇒ 修實作」方向；攤提窗尾免除是 PRD 未規範面（攤提本身是 R86 加的
  repo 內機制），由掌舵者 2026-08-16 直接裁決驅動。
- ADR：`ADR-XPLAT-005`（額度節流與扇出恢復）、`ADR-XPLAT-007`（前沿 token 治理）、
  `ADR-XPLAT-009`（換方案自適應攤提——本輪指紋分區語意零改動）。

## §7-R95-修4 哨兵存活四修之修4：halt 武裝的多軸裁決（quota_messages／quota_gate 部分）

**立案**（ADR-XPLAT-004 §2.9 根因第 4 層；PRD §4.5.6 R-4.5.6-5）：2026-08-16 00:42 額度
閘 halt 閂鎖 `halt@extra_usage@None` 首次落鎖，`reset_branch()` 以 binding 單軸判
escalate-only ⇒ `waker` 未武裝；而 five_hour 軸 03:50 reset 後工作實際可續（今晨實證：
額度快取 session/five_hour 18%）。多軸情境下「binding 無 reset ⇒ 只能等人」是假的。

**落地物**：`quota_messages.halt_resets_at()`（≥halt 各軸中最早可解析 reset；全軸皆無
⇒ 回 binding 原值讓 `reset_branch()` 走 escalate）＋三個消費端改讀它：
`quota_gate.quota_halt_actions()` 的 branch 判定、halt 閂鎖鍵的期程半、
`quota_halt_message()`／`throttle_horizon_line()`（halt 帶）的期程句。
方向鎖＝候選含 binding 自己 ⇒ min 只會更早不會更晚；ARM 的 6 小時視界仍由
`reset_branch()` 把關（R59 同形防護一格未鬆）。回歸鎖＝
`test_quota_policy.TestR95HaltArmsOffTheEarliestResettableAxis`（8→5 支，紅面自證：
修前 `halt_resets_at` 不存在即 AttributeError、對照組 binding 單軸判 escalate）。

**LOC 對價帳**：`quota_messages.py` 144→150（headroom 250）、`quota_gate.py` 498→499
（import 一行；headroom 1）、`root_tools_violations=[]`。
**誠實劃界**：ADR §2.9 誠實劃界節「修 4 實作時應讓閂鎖多記 `session_id` 與 `tool`」
本包**未實作**——`latch_write` 的注入簽名 `(latch, key)` 住 hook 側
（`context_budget_guard.remember_latch`），跨出修4 列示的持有面且 quota_gate headroom
僅餘 1 行；已如實回報，交後續輪次。

## §7-R95-搬遷批（哨兵存活四修實作包；R89 體例，一字未刪）

### §7-R95-L1 原 `TestTheTableIsProducedByTheRuleNotByHand` docstring

```
    """🔴 上表每一列都必須從**寫下來的聚合規則**重算得到，而不是手挑的數字。

    規則（見 `quota_policy` 檔頭「兩個角色分開聚合」）：
      cap = min(逐軸 cap)                                    ← 煞車
      rec = min( clamp(min(逐軸 base_rec) × pace) , cap )     ← 加速，pace 取最短期程
    本測試**不呼叫 `decide()`**，而是照上式獨立重算一次——同一顆星有兩條互不相干的
    算法對得上，才排除得掉「表是照著實作抄的」。

    🔴 聚合規則改寫後，規格 S4 表有兩列與交件時判定不同（照實記；第 1／3 列的三方
    數字對照與歸因原文＝R95 Pace 證據檔 §7.4）；其餘 13 列與規格表逐字相同。
    """
```

### §7-R95-L2 原 R82／C4 硬 gate 節敘事

```
# 🔴 R82／C4：把「三個掃描面」從**列舉**升成**硬 gate**。病＝兩個判準只對
# `quota_policy.py` 自己斷言，於是把 `worst()`／`fanout_cap(pct)`／`quota_tier_of(pct)`
# 放回 gate／meter／hook／AutoClaude adapter **五組注入全綠**；「掃描面列出來了」與
# 「掃描面被判了」是兩件事，前者讀起來很像後者。當時那支「確認掃描器擋得住活標的」的
# 測試寫成 `if 定義還在: assertIn(...)` ⇒ 定義不在就整條沉默＝**結構上不可能失敗**
# （這一型比沒有鎖更難看見）。立案史料原文＝R89 收尾證據檔。
```

### §7-R95-L3 原 M9 失效字面登記表敘事（`keychain-timeout`）

```
#: 🔴 R83／F2-③ 新增 `keychain-timeout`：mac 的 Keychain 跳鎖定提示而沒有人按時，
#: `security` 會阻塞到逾時——那與「這台 mac 沒有條目」要做的事完全相反（解鎖 vs 重新登入），
#: 故取數層給了它自己的字面。本表**不是**這批字面的家（家在 `quota_meter.REASON_*`），
#: 而是「每一個字面都必須被 M9 那兩條不變量掃過」的登記處；兩者的同步由
#: `TestMeterReasonsAreAllRegistered` 機械守（漏登記即紅）。
```

### §7-R95-L4 原 R84／6b 係數參數化節敘事

```
# 病：三檔乘數此前是模組層寫死的 dict（`_MULTIPLIER = {near: 2.0, …}`），而掌舵者訴求 6b
# 逐字要求「係數必須可由 env 參數化」——寫死的字面結構上不可能被參數化。
# 這一節同時守住開放之後**新長出來的**危害：兩個鍵各自合法（值域檢查看得到），但
# 「near < far」這種**關係**錯誤只有跨鍵判準看得到，而它會讓「近 reset 加速」變成減速。
```

### §7-R95-L5 原 R83／F2-③ 登記提醒敘事（M9 分母）

```
# 🔴 立案（R83／F2-③，形狀與 `TestM8SchemaStaysInSync` 同構）：取數層新增一個失效字面
# 時，**沒有任何東西**會提醒你來這張表登記它。漏登記的後果不是崩潰而是失明——那個字面
# 從此不在 M9 的分母裡，於是「它會不會被錯判成不設限／被錯判成 halt」這兩條不變量對它
# 一次都沒有驗過，而 rc 與「正確地全部通過」一模一樣（分母少一項是看不見的）。
# 判準的分母是**現查** meter 的 `REASON_*` 宣告集合（會變的量測值），不是寫死清單。
```

### §7-R95-L6 其餘同批壓縮的原文（M8-b 立案段、R87／R93／R95 類 docstring 等）

```
# 🔴 立案（R83／F2-①）：檔案契約有**路徑**＋schema 兩欄而 R82 只鎖了 schema；adapter
# 不能 import meter（importlinter #9）⇒ 路徑複本是設計上必要的，正因必要才需要鎖。
# 立案敘事全文（只動 meter 時 adapter 靜默讀不到檔的失效鏈）與「判 token 序列而不是判
# gettempdir」的取捨原文已搬 R95 證據檔 §7（R89 搬遷體例；判準本身一字未動）。
# 判準：兩邊算路徑用的「家」token 序列相等——搬家可以，但必須同一次 commit 動兩支檔。
#: 「家」只可能來自這幾個地方。刻意是白名單而不是「抓所有識別字」：後者會把
#: `self._path`／`Path`／`if`／`else` 這種**寫法差異**也算進去，於是兩支檔明明用同一個
#: 算法卻判紅（實測：第一版判準就是這樣假紅的）。假紅的鎖活不過一輪。
```

```
    """R87 事故鎖：**取數層不得把「已撞頂但自報 `enabled:false`」的軸丟掉。**
    架構缺口：判讀層的不變式只保證「**給定的軸**不會被放寬」，不保證「軸不會消失」。"""
    """R93／DEF-200-114：…🔴 這是**純函式**測試（零網路）：`account_key_of()` 只吃一個
    dict，本類不打端點。"""
    """R95 攤提：立案實案：five_hour 窗尾 33 分、自軸 25%、weekly 46%（free band），
    攤提仍因帳面超支把 cap 壓死 ⇒ 派工被迫空等 reset——而 five_hour 剩餘額度 reset 即
    作廢（use-it-or-lose-it）、weekly 是同一消耗池（推遲≠節省），空等純浪費牆鐘。"""
    """m1_problems：🔴 刻意**不**斷言「binding 不同／reset 分支不同／訊息不同」——規格
    實測那三條今天就是綠的（A→kind=session branch=arm、B→kind=weekly_all
    branch=notify），寫進去就是零鑑別力的鎖。"""
    """test_is_active：五次觀測 `is_active` 都等於 argmax，但五次一致不構成契約。"""
    """test_the_helm_anchor：使用者原句「Token 剩 30Min 就 Reset、還有 100% 沒用 ⇒
    加速」。加一條**不緊**的長期程軸之後必須仍然成立，而且不得低於中性基準（8）——
    複驗鏡量到的正是「多軸下 rec=4，方向與中性基準相反」。"""
    """test_an_axis_with_no_horizon：不變式＝「**不參與 cap 的軸不得參與 pace**」，
    兩個方向各自被下面兩支釘住。R84／SA-01 的立案史料＝R89 收尾證據檔。"""
    """test_the_negative_horizon：舊實作在 `_delta_minutes` 就把負值夾成 0、另在
    `axes_of` 用一個 if 強制 mid ⇒ `horizon_band` 的負值分支任何生產路徑都到不了
    （刪掉它零測試會紅），而「偏移不得加速」變成同一份知識的第二個家。"""
    """test_the_disk_file：🔴 誠實劃界：該檔的建立屬**第二步**（本包只准動兩支檔），
    今天磁碟上還沒有它。"""
    """test_red_removing_the_separators：下面這一則裡第二個百分比既沒有自己的
    `kind=`、也沒有自己的分鐘，只是坐在第一個桶的名牌與分鐘旁邊。chunk 級判準把它
    切成**一段**、看到段內有 `kind=` 也有「分鐘」⇒ 放行；百分比級判準逐個問 ⇒ 抓到兩筆。"""
    """test_a_toothless：數字是 live 快取的形狀（3 軸 `resets_at=null` 且 0%）：修前 8、
    修後 16。"""
```
