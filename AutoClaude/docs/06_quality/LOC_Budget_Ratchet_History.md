# LOC 預算棘輪 — 逐常數判準敘事史料歸檔

- **建立日期**：2026-08-24
- **建立者**：LOC 治理修法（`AutoClaude/tools/check_loc_budget.py` 自治 + 史料搬遷）

## 這份文件是什麼、為什麼要有它

`AutoClaude/tools/check_loc_budget.py` 是整個 monorepo 的 LOC 預算治理工具，但它自己
（連同 `AutoClaude/tools/` 其餘檔案）此前**不落在它自己掃描的任何範圍內**
（`SCAN_ROOT = "autoclaude"` 只掃套件本體；`ROOT_TOOLS_ROOT` 只掃 monorepo 根層
`tools/`）——它可以無限長大而不被自己的規則管。這正是「每輪都要花時間手動瘦身」
這個抱怨的根本原因之一；另一半原因是：檔內每個治理常數（`TIER_WARN_MARGIN`／
`SPECIAL_STALE_SLACK`／`SPECIAL_FILES` 逐列棘輪等）旁邊都附了一整段「為什麼是這個
數字」的事故敘事（DEF-XXX 引用、歷史調整過程）——這是好的工程紀律（Rule 9：測試
要驗 intent 不只是 behavior），但這些散文佔了原檔（1110 行）超過一半的篇幅，讓檔案
本身難以在一眼掃過時看清判準邏輯。

本文件比照 `docs/06_quality/CrossPlatform_Guard_Line_History.md` 的既有體例，把
`check_loc_budget.py` 裡最大宗的「逐常數歷史敘事」段落**原文搬到這裡**（只是換
位置，不是刪減內容——所有缺陷本體、實測數字、誠實劃界都完整保留），原始碼本身只留：
判準邏輯（常數本體、函式）＋一行指向本文件對應章節的指標。本文件是純 Markdown、
不在 `check_loc_budget.py` 自身的 LOC 計價範圍內（`count_loc()` 本來就對敘事免費，
搬走它不會改變任何一支檔案的計價結果），純粹是為了原始碼的可讀性，也不會遺失任何
「為什麼這樣設計」的紀錄。

**索引**（依原始碼在 `check_loc_budget.py` 內出現的順序排列；章節標題即原始碼裡
指向本文件時使用的〈…〉錨點名稱）：

1. [總量 cap 與預警帶沿革](#總量-cap-與預警帶沿革)
2. [POLICY_VERSION 通約規則](#policy_version-通約規則)
3. [TOTAL_WARN_MARGIN 沿革](#total_warn_margin-沿革)
4. [TIER_WARN_MARGIN 沿革](#tier_warn_margin-沿革)
5. [SPECIAL_WARN_MARGIN 沿革](#special_warn_margin-沿革)
6. [SPECIAL_STALE_SLACK 沿革](#special_stale_slack-沿革)
7. [SPECIAL_FILES 逐列棘輪沿革](#special_files-逐列棘輪沿革)
8. [根層 tools/ LOC 分級立案（R75）](#根層-tools-loc-分級立案r75)
9. [ROOT_GUARD_ROOTS 立案（R81／Architect-B3）](#root_guard_roots-立案r81architect-b3)
10. [ROOT_TOOLS_HUB_TIER 立案（R84／ARCH-04）](#root_tools_hub_tier-立案r84arch-04)
11. [count_loc() 計價規則沿革（ADR-XPLAT-013）](#count_loc-計價規則沿革adr-xplat-013)
12. [AutoClaude/tools/ 自治納管（本次修法）](#autoclaudetools-自治納管本次修法)

---

## 總量 cap 與預警帶沿革

（原住模組頂層 docstring；現行版本只留精簡摘要並指回本節）

總量 cap：total LOC ≤ baseline × 1.20（防爆漲）。R56 訂正：此 cap 與 tier/absolute
違規**同級阻塞**（見下方 has_violation），非舊述的「sanity check」——宣稱與行為不一致
曾導致兩輪把它誤當軟性提示。baseline 重新校準須走 ADR-SD07-001 §6.3 正式程序
（先刪死碼／收斂重複實作，最後才調 baseline；Architect + SD 雙簽）。
R56 round 5 增訂：`total ≥ cap − TOTAL_WARN_MARGIN` 但尚未破線時印 **非阻塞** [WARN]
（rc 不變、不進 has_violation），把 §6.3 觸發條件 ② 的偵測從人眼改為機械。

R60 增訂（承接 DEF-101-526 明文交棒的 R60 候選）：**單檔** tier 餘裕 ≤
`TIER_WARN_MARGIN` 時印 **非阻塞** [TIER-WARN]（rc 不變、不進 has_violation），
把「LOC tier 滿載檔 × lint 斷行互斥」這個治理衝突從「只有踩到才會發現」改為事先告知。
刻意用 `[TIER-WARN]` 而非沿用 `[WARN]` 標籤：後者已被
tests/contract/test_loc_budget_tiered.py::test_warn_band_boundary_and_rc_invariant
以 `("[WARN]" in out) is expect_warn` 精確釘選為「總量預警帶專屬訊號」，共用標籤會讓
那道鎖在 repo 現況（預警帶非空）下恆真而失效。R71 訂正：此處原寫「3 支滿載檔」，
該數字已隨「刪死碼／收斂重複」輪失真——**現況不寫死於此**，現查＝
`python tools/check_loc_budget.py --json` 的 `tier_warn_band`。

## POLICY_VERSION 通約規則

（原住 `POLICY_VERSION` 常數正上方；現行版本只留一行摘要並指回本節）

政策版本標記（ADR-XPLAT-013 條文六；R100 §E-3「附帶一」訂正）。**每次 `count_loc()`
的計價規則本身改變**（不是門檻數字改變）就必須跟著換版號——版號不是裝飾，是「這個
`.loc_baseline`／`total` 是用哪一把尺量出來的」的唯一標記。

🔴 通約規則（不可通約的兩個版本，禁止直接相減／相除比大小）：

1. **R101／DEF-200-208 已補**（round-label-ok）：`write_baseline()` 每次重釘同時由
   `write_baseline_policy_version()` 把當時的 `POLICY_VERSION` 寫進
   `BASELINE_POLICY_FILE`（`read_baseline_policy_version()` 讀回）——
   這就是「兩者用的是不是同一把尺」的機械答案，不必再靠人眼比對本欄位。
   🔴 但**磁碟上既有的 `.loc_baseline`（17032）沒有回填**：它最後一次寫入
   早於 `POLICY_VERSION` 這個符號存在（`git log -- .loc_baseline` 可查
   2026-06-13），此時 `read_baseline_policy_version()` 誠實回 `None`——
   `None` 必須被下游（`pricing_exemption_problems()`）當成「不是目前這把尺
   釘的」處理，**不得**猜成目前版本（猜錯比誠實缺記錄更糟，同
   `tools/lib/baseline_origin.py` 的既有處方）。
2. 版號**只在計價規則變更時**遞增（tier 門檔或 `TOTAL_INCREASE_LIMIT` 調整不算——
   那些是「尺不變、門檻變」，不影響可比性）；本檔一份判準一個家，版號本身不做任何
   自動換算，換算永遠是人審的責任（同 ADR-XPLAT-012 條文五 §3 的取值紀律）。
3. `v2-tiered+sd08-special` → `v3-assertion-only+sd08-special`：ADR-XPLAT-013 條文一
   把 `count_loc()` 由「排除空行與純註解」改為「只算斷言行」，兩把尺對同一份原始碼
   給出的行數**逐檔不保證相等**、且**淨方向不保證同號**（見該 ADR §1.2 三支頂格檔
   實測，改動可達 −43% 以上；但 R100 §E-4 全樹實測 total 反而 17032→17079 上升
   +47）——這正是 DEF-200-208 的立案理由：`baseline > total` 這個不等式在改尺
   前後可能倒向任一邊，拿它反推「有沒有重釘」在結構上會恆假或恆真，必須改問①的
   provenance，不能再問大小關係。

## TOTAL_WARN_MARGIN 沿革

（原住 `TOTAL_WARN_MARGIN` 常數正上方；現行版本只留一行摘要並指回本節）

R56 round 5 修正：ADR-SD07-001 §6.3 觸發條件 ② 是「連續 2 輪 total ≥ cap − 10」，
但本工具此前只在 total > cap 才有訊號 —— 落在預警帶時輸出與正常態一字不差，
該 ADR 自己的「緣起」段記載 R53(=cap)／R55(=cap−1) 兩次都是靠審查員逐字讀輸出
才發現。在一個把「9 支 vs 15 支」人工計數都機械化的 repo 裡，新訂程序不該只靠人眼。
本常數即該條的機械化。

R56 round 5 補鎖（四方複核指出本訊號自身零回歸保護、且與 ADR 兩站點硬編互稱同步）：

- 本常數 ↔ ADR §6.3 ② 的「cap − 10」由 tests/contract/test_loc_budget_tiered.py::
  test_total_warn_margin_matches_adr_sd07_001_section_6_3 自 ADR 正文抽數字比對，
  機械鎖定而非人工宣稱；改任一站點未同步即翻紅。
- 下方預警帶四態邊界（>= 下緣／total==cap／破線）與「WARN 非阻塞、rc 不得改變」
  由同檔 test_warn_band_boundary_and_rc_invariant 釘住；JSON 兩欄由
  test_warn_band_json_payload_matches_text_mode 釘住。

## TIER_WARN_MARGIN 沿革

（原住 `TIER_WARN_MARGIN` 常數正上方；現行版本只留一行摘要並指回本節）

R60（DEF-101-526 交棒的 R60 候選）：單檔 tier 餘裕預警帶。餘裕 ≤ 本值即印
**非阻塞** [TIER-WARN]，不改 rc、不進 has_violation——刻意不改成 fail，那會當場
擋住現有的**合法**滿載檔。R71 訂正：原文在此寫死三支檔名與各自行數
（pg_state_repository.py 400/400 等），已隨「刪死碼／收斂重複」輪全數失真；
現況一律現查 `python tools/check_loc_budget.py --json` 的 `tier_warn_band`。

為什麼是 6，而不是交棒文字裡舉例的 3（刻意上調，理由留痕）：

1. DEF-101-526 原文寫「如 `check_loc_budget` 對餘裕 ≤ 3 行的檔印 warning」——
   「如」是舉例而非規格。
2. **同一列自己的實測數字反而否證 3**：該輪在滿載的 adapter 檔上修 4 處 E501，
   斷行後實測 `406 > 400 (+6)`——+5 來自 4 處斷行（呼叫 +2、字典 +2、格式字串 +1）、
   +1 來自 ruff I001 自動修復把 `import os, warnings` 拆兩行。也就是「一次 lint
   修復」的實測代價是 6 行；門檻取 3 會讓餘裕 4~6 的檔照樣被咬、卻拿不到預警。
3. 偽陽性成本實測（本輪 201 支計入檔）：餘裕 ≤3 命中 3 支、≤6 命中 5 支
   （多出 evolution_plugin.py 245/250、core/ports/rtm_feedback.py 144/150）；
   代價＝多印 2 行非阻塞提示，而這 2 支正是「一次 lint 斷行就會破線」的檔。
4. 與既有 TOTAL_WARN_MARGIN=10 同形（近上限帶、只 WARN、rc 不變、JSON 亦曝露），
   不新增第二種機制語意。

本值 ↔ 上述判準由 `AutoClaude/tests/tools/test_check_loc_budget_tier_headroom_warn.py`
釘選（含 bug-injection 驗紅）。R76 增訂：本常數同時是**根層 tools/ 分級**
（`ROOT_TOOLS_TIERS`）的預警門檻——那一層與 AutoClaude tier 是同一種度量
（`count_loc` × tier 預算），沿用同一個數字才不會憑空生出第三種「近上限」語意；
`SPECIAL_FILES` 是 raw-line 棘輪、度量面不同，另立 `SPECIAL_WARN_MARGIN`。

## SPECIAL_WARN_MARGIN 沿革

（原住 `SPECIAL_WARN_MARGIN` 常數正上方；現行版本只留一行摘要並指回本節）

R76（R76-16）：`SPECIAL_FILES` raw-line 棘輪的預警帶門檻。**非阻塞**（不進
has_violation、不改 rc），理由同 TIER_WARN_MARGIN——現況那批檔餘裕 0~2 全是**合法**
狀態（門檻依 R69 P3 慣例＝納管當下的實際行數，本來就是零餘裕設計），改 fail 會當場
擋住 repo。

為什麼另立一個數字、而不是沿用 TIER_WARN_MARGIN：兩者度量面不同。tier 量 `count_loc`
（排除空行與純註解），SPECIAL_FILES 量 raw line（空行、註解、Markdown 全算）。

為什麼是 5：

1. 這批檔的最小合法增量不是「一行程式」，而是「一筆具名登記」或「一段訂正註記」。
   R76-00 實測到的死結正是這個形狀：工具訊息教人往 `_GOVERNANCE_DOCS` 補一筆
   ＝+1 行，而 `check_defect_log_crossref.py` 當時 1474/1474 餘裕 0 ⇒ **A 鎖要求的
   補救動作正好是 B 鎖的違規**。第一個訊號就是紅，中間沒有任何預警。
2. 一段照本 repo 體例寫的訂正註記（WHY ＋ 實測 ＋ 邊界）實測約 4~5 行，取 5 剛好
   覆蓋「照規矩留痕」這個最常見的增量形態。
3. 不取更大：raw line 連空行都算，門檻愈大愈接近「常駐全亮」，而常駐全亮的燈等於
   沒有燈。超過 5 就不是「快滿了」而是「一直都很滿」，那是棘輪本身該被重新談的事。

落地當下即有五支落在帶內（餘裕 0~2）——那正是 R76-16 要曝光的事實本身，不是雜訊；
現值一律現查 `python tools/check_loc_budget.py --json` 的 `special_warn_band`。

## SPECIAL_STALE_SLACK 沿革

（原住 `SPECIAL_STALE_SLACK` 常數正上方；現行版本只留一行摘要並指回本節）

🔴 R84（ARCH-05）：`SPECIAL_FILES` raw-line 棘輪的**下界**咬人判準（阻塞）。
缺陷本體：這批門檻自陳「＝納管當下實際行數，只准往下改」，買到的東西是「再往裡塞就
會紅」——而 R84 逐鍵實測發現有列的門檻**遠高於現值**（`../.claude/hooks/
context_budget_guard.py` cap 1451 / raw 1089 ⇒ 陳舊餘裕 **362 行**），也就是那 362 行
可以無聲地長回去而**沒有任何訊號**。上界（`SPECIAL_WARN_MARGIN`）與破線段都看不到這一側：
它們量的是「快滿了」，這一格量的是「門檻自己過期了」。

體例照 repo 既有的同型判例（`tools/tests/test_adr_xplat001_c1c2_lock.py` 的
`_GUARD_LINE_STALE_SLACK` 雙邊帶，該檔逐字寫：「單邊棘輪只會腐化，縮下來卻不重釘的話，
餘裕就是日後無聲加回去的破口」）——那一族是淨行數、這一族是 raw line，兩個度量面，
故另立常數而不共用數字。

為什麼是 32（三個邊界各自可查，故這個數字不是載重件）：

1. **下界**：必須 > `SPECIAL_WARN_MARGIN`(5)，否則「快滿了」與「太鬆了」兩個帶相鄰／
   重疊 ⇒ 每一列永遠落在其中一帶，常駐全亮的燈等於沒有燈。更硬的一條：
   `tools/tests/test_check_defect_log_crossref.py::TestActionableMessagesHaveLocHeadroom`
   要求「訊息教人加一筆的那些檔」餘裕 **≥ 5**（`_MIN_DIRECTIVE_HEADROOM`）⇒ K ≤ 5 會
   讓那道鎖與本判準**互相矛盾而無法同時滿足**（實測那兩支現值 22／6，皆落在 5..32 內）。
2. **上界**：本輪實測，受本判準管的 7 列裡「例行縮小」那一群的陳舊餘裕是
   1／2／6／18／22／25，真正陳舊的那一列是 **362**——兩群之間差一個量級（362 ≈ 11×32），
   門檻落在空隙上而不是密集區 ⇒ 32 上下浮動不會改變任何一列的判定，不會製造邊界抖動。
3. **方向鎖**：只准調小（收緊），由鎖檔 `assertLessEqual` 釘住；調大＝把「預先發放的
   成長額度」再發回去，那正是本判準的立案理由。

**為什麼是阻塞而不是預警**：這一族已經有一個非阻塞預警帶（上界那個），而 R84 之所以要
建這道鎖，就是因為「有訊號但沒人動作」在這一族已經是實況（那 362 行陳舊餘裕存在多輪、
每次 `--json` 都印得出來卻沒有任何東西會紅）。修法是**重釘為現值**（一行 diff），
不是調高——所以它擋得起。

## SPECIAL_FILES 逐列棘輪沿革

（原住 `SPECIAL_FILES` dict 逐項之上；現行版本只留頂部一段摘要並指回本節。
`_SPECIAL_REASONS` 是這批理由的**運行時**版本——供 `check()` 印給違規者看，
本節是給原始碼讀者看的完整沿革，兩者刻意分開，前者不受本次搬遷影響。）

### `../tools/dev_start.py`（1952）

🔴 R68：DEF-101-271／274 訂了「monorepo 根 tools/dev_start.py > 2000 行即升級為
該輪必修」，但**從來沒有量測者**——實測該檔已自帳本三度記載的 1772 行漂到 1918
行、距門檻僅 82 行且無人察覺（帳本同時還在寫「零成長／餘裕 228 行」）。本列即該
門檻的機械量測者：路徑刻意以 `../` 越出 AutoClaude（唯一的 dev_start.py 在
monorepo 根 tools/，SCAN_ROOT="autoclaude" 掃不到它）。**棘輪：只准往下改**，
要往上調必須在缺陷帳本具名理由（同 `_FROZEN_GUARD_LINES` 的重釘慣例）。

🔴 DEF-101-758 下釘 2000 → 1952：gh-run-list 判讀邏輯本體（原 1798~1836，
已無 +4~5 行餘裕可再修）搬到新葉節點模組 `tools/lib/ci_run_status.py`，本檔僅留
薄呼叫；依本棘輪「合法縮小後必須同步下修」的紀律重釘為現值，不下修的話這段
差額就是日後無聲加回去的破口。

### `../tools/check_script_parity.py`（1618）／`../tools/archive_defect_log.py`（1507）

🔴 R69 P3：上一列（R68 落地）**只守 `dev_start.py` 一支**，而根層 `tools/` 是一整層
逾兩萬行的護欄層。同一輪（R68）就有另外兩支在無人看守下大幅膨脹——
`check_defect_log_crossref.py` 漲到四位數行、`archive_defect_log.py` 亦然——證明
「只釘一支」不是取捨而是缺口：守的是**檔名**，不是**那一層的成長**。

本批把根層 tools/ 所有 700 行以上的 .py 全數納管，門檻一律取**納管當下的實際行數**
（不預留餘裕：預留多少都是憑空猜測，而 shrink-only 棘輪的價值就在「下一行就會響」）。
**棘輪：只准往下改。** 要往上調＝先刪死碼／抽共用模組（先例：R68 把 CI 逐軌活性偵測
抽到 `tools/lib/ci_liveness.py`），確認為不可壓縮的真實功能後才在缺陷帳本具名理由。

### `../tools/check_defect_log_crossref.py`（1479）

🔴 具名調高 1474 → 1479（DEF-200-163 staleness advisory 落地）：調高前已先走完「抽共用
模組」那一步——git-dirty 判斷搬進新檔 `tools/lib/ledger_staleness.py`（guardrail_lib
400 budget、當回合遠低於上限），本檔只留 import＋2 行呼叫的接線；+5 行是接線本身，
且 `TestActionableMessagesHaveLocHeadroom` 要求本檔維持 ≥5 行餘裕（見該測試）。

### `../tools/sync_onboarding_baselines.py`（1430）

🔴 R70 具名調高 1451 → 1499（`DEF-101-756`／`DEF-101-757`，依本棘輪自訂的解鎖程序）：
調高**前**已先走完「抽共用模組」那一步——基線三態語意（`unrecorded` 二義性根治）與
nightly 落地產物探針共約 180 行已抽到 `tools/lib/baseline_origin.py`（先例：
`tools/lib/ci_liveness.py`）。留在本檔的殘餘是**不可壓縮的接線**：三態判準要吃
`_SLOW_SPECS`／`platform_cell_index()` 這些只有本檔有的表格解析器，搬出去等於把
解析器一起搬（那會製造第二份表格語意＝本檔一直在治的病）。本輪：R60/R67 史料搬遷後
重釘（收緊）。

### `../tools/run_root_unittests.py`（759）

🔴 具名調高 754 → 759（DEF-200-162，依本棘輪自訂的解鎖程序）：調高前已先走完「抽共用
模組」那一步——失敗明細檔名／輪替邏輯搬進新檔 `tools/lib/failure_log_rotation.py`
（guardrail_lib 400 budget、當回合遠低於上限），本檔只留呼叫端最小接線（import＋2 行
呼叫），+5 行是接線本身、非可再壓縮的重複邏輯。

### `../.claude/hooks/context_budget_guard.py`（1089）

🔴 R81（Architect-B3）：`.claude/hooks/` 納入治理面（見 `ROOT_GUARD_ROOTS` 的 WHY）。
這一支超過 tier 的 750，走與上面那批同一條路：門檻＝**納管當下的實際行數**、
只准往下改。納管當下＝1,634（見 `ROOT_GUARD_ROOTS` 立案段的立案量測）。

🔴 R81 收尾包**下釘**：額度撞線判讀整個主題已搬進 `tools/lib/quota_limits.py`，
該檔實測降到 1,451 ⇒ 依本表「合法縮小後必須同步下修」的紀律把門檻跟著往下走。
不下修的話那 183 行餘裕就是日後無聲加回去的破口（零餘裕是本棘輪的設計，不是意外）。

🔴 R84（ARCH-05）**再下釘 1451 → 1089**（當回合實測 raw＝1089，直接填入、零加減推算）：
上一行自己寫著「餘裕就是日後無聲加回去的破口」，而 R81~R83 之間該檔又縮了 362 行、
門檻沒有跟著走 ⇒ 那句話在同一份檔案裡被自己違反了三輪，因為**沒有任何東西在量它**。
本輪同時補上量測者（`SPECIAL_STALE_SLACK` ＋ `special_stale_reports()`，阻塞），
所以這次的下釘不是靠下一個人記得。

## 根層 tools/ LOC 分級立案（R75）

（原住 `ROOT_TOOLS_ROOT` 常數正上方大段區塊註解；現行版本只留精簡摘要並指回本節）

🔴 缺陷本體：`SCAN_ROOT = "autoclaude"` ⇒ 分級政策（tier ＋ 絕對紅線）**一行都照不到
根層 `tools/`**，而那是一整層兩萬行以上的護欄程式碼。R68／R69 P3 已察覺一半，處置是
把當時 ≥700 行的 6 支具名檔掛上 `SPECIAL_FILES` 的 raw-line 棘輪——但那是**一次性快照**：

1. 當時 <700 行、後來長大的檔完全無人看守。R75 實測 `tools/lib/windows_skip_tags.py`
   在 R74 一輪內 +385 行、達 508 code／727 raw，**零訊號**（`tools/lib/` 整個目錄
   先前一支都沒納管）。
2. 「守的是檔名，不是那一層的成長」——這正是 R69 P3 自己寫下的教訓，卻只修了一半。

本節把既有載具（`count_loc`／`FileReport`／`_matches_pattern`／同一套報表與 rc 收斂）
延伸到根層 `tools/`，**不另造第二套 LOC 檢查器**（那會重演「同一份知識兩個家」）。

三個判準決定，逐條寫下理由（免得下一輪把它讀成任意數字）：

- **預算沿用既有數字，不發明新的**：`guardrail_cli` ＝ `ABSOLUTE_LIMIT`(750)，即
  ADR-SD07-001 的全域絕對紅線原封不動；`guardrail_lib` ＝ 400，取既有
  `adapter`／`contract` tier 的值——`tools/lib/` 是**共用函式庫層**，與 adapter 同性質，
  且一支超過 400 行的共用模組按定義已不只做一件事（`windows_skip_tags.py` 就是實例）。
- **`tools/tests/` 不納管**：與 AutoClaude 側 `SCAN_ROOT="autoclaude"`（不含
  `AutoClaude/tests/`）**對稱**。這是政策一致，不是為了讓現況通過——根層測試樹
  另有 `tools/tests/` 專屬的 E501 存量債棘輪，以及
  `tools/tests/test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 的
  **逐檔行數棘輪**（`_FROZEN_GUARD_LINES`，淨行數只准往下）在管。
  🔴 **R78 ARCH-03 訂正**：本列原本把這層豁免的正當性掛在 R77 已刪除的那個**檔數**
  棘輪常數上（全庫零定義）——也就是說一整層數萬行護欄碼的 LOC 豁免，有一段時間是
  掛在一個**不存在的符號**上。此處刻意不逐字引述那個已死的常數名：
  訂正註記引述假話等於製造新假話，而下一個人 grep 到它會以為那是現行說法。
- **已在 `SPECIAL_FILES` 的檔排除在 tier 檢查外**：同一支檔不受兩種度量（raw line
  vs count_loc）雙重審判；那 5~6 支 1000 行級的護欄 CLI 沿用 R69 P3 立的 raw-line
  棘輪即可。反過來說，**沒被 `SPECIAL_FILES` 收錄又超過 tier 預算的檔一律紅** ⇒
  這道機制會自己補完收錄面（要嘛瘦身、要嘛具名入表附理由），不再是一次性快照。

## ROOT_GUARD_ROOTS 立案（R81／Architect-B3）

（原住 `ROOT_GUARD_ROOTS` 常數正上方；現行版本只留一行摘要並指回本節）

🔴 R81（Architect-B3）：`.claude/hooks/` 也是 monorepo 根層護欄層，卻**不在任何 LOC
治理面內**——`SCAN_ROOT = "autoclaude"` 掃不到它，`ROOT_TOOLS_ROOT` 只有 `tools/`，
而且**沒有任何一行明文豁免**（⇒ 這不是取捨，是缺口）。代價是量出來的：納管當下
`context_budget_guard.py` ＝ 1,634 raw 行，是絕對紅線 750 的 **2.18 倍**；而 R81 那一輪
+421 行全部灌進這一支，同一套 LOC 政策卻正是該輪**新開兩支檔**的立案理由
⇒ **壓力只作用在已經被量的那一層**，於是新檔被推出去、真正在長的巨檔繼續長。

🔴 **誠實：納管當下不會讓任何東西變小。** 門檻取納管當下的實際行數（見上面
`SPECIAL_FILES` 那一列），買到的是「下一個人再往裡面塞就會紅」。這不是減法，
別包裝成減法；把那 1,634 行拆開是另一件事，本輪未做。

## ROOT_TOOLS_HUB_TIER 立案（R84／ARCH-04）

（原住 `ROOT_TOOLS_HUB_TIER` 常數正上方大段區塊註解；現行版本只留精簡摘要並指回本節）

🔴 R84（ARCH-04）：`guardrail_lib` 把 `tools/lib/` **整層**當成同一種東西，而那一層裡
有兩種形狀：**leaf helper**（只被人叫、自己幾乎不叫別人）與 **hub**（把同族的 leaf 組起來
對外只露一個決策面）。R84 實測 `tools/lib/quota_gate.py` ＝ `count_loc` **400／budget 400
／餘裕 0**，而它 fan-out 到 **5 支**同層 lib（`quota_ledger`／`quota_limits`／`quota_meter`
／`quota_policy`／`schedule_backend`），對外 production 消費者只有 1 支
（`.claude/hooks/context_budget_guard.py`）⇒ 這是**分類錯誤**，不是「該檔太胖」：
一支組合 5 個下游的合成面，天生比 leaf helper 需要更多接線行，而
`guardrail_lib=400` 的立案理由逐字寫的是「一支超過 400 行的**共用模組**按定義已不只
做一件事」——那句話對 leaf 成立，對合成面不成立（它做的**就是**「把 5 件事接起來」）。

三個判準，逐條寫下理由（免得下一輪把它讀成「開了一個誰都能進的後門」）：

- **預算不發明新數字，且刻意取 `service`(500) 而不是 `ABSOLUTE_LIMIT`(750)**：
  hub 的語意就是 ADR-SD07-001 `service` tier（「把下游組起來的協調面」），直接**引用**
  那一格的值而非複寫字面，改 SSOT 會同步跟著動。取 750 的話 `guardrail_hub` 與
  `guardrail_cli` 逐字同值 ⇒ **一個等於絕對紅線的 tier 不是 tier**，等於只剩絕對紅線
  在守；本輪刻意選最小的放寬幅度（+100 行），真的還不夠時的下一步是既有的合法出口
  （拆職責／抽共用模組，不可壓縮才具名進 `SPECIAL_FILES` 的 raw-line 棘輪），不是再調高本格。
- **patterns 只收明文列舉的單檔，不得用寬 glob**：`tools/lib/*_gate.py` 這種寫法會讓
  下一支取同樣名字的檔自動繼承 +100 行，而那正是「後門」的形狀。
- **代價：成員清單只准縮不准長，且每一支成員都要能被機械驗證是 hub**。
  `ROOT_TOOLS_HUB_MEMBER_CAP`（成員數上界，只准調小）＋
  `ROOT_TOOLS_HUB_MIN_FANOUT`（fan-out 下界）＋逐支 `override_reason`
  由 `AutoClaude/tests/tools/test_check_loc_budget_hub_tier_and_special_stale.py` 釘住：
  成員數變多、成員不存在、成員 fan-out 不足、預算不是既有數字、pattern 出現 glob，
  任一項即紅。**「是不是 hub」由 AST 現查 fan-out 決定，不是靠自稱。**

🔴 誠實劃界（R84 現查，免得下一輪誤以為本格解了整層的問題）：同族 `skip_*` 六支裡
**沒有一支**符合本格判準——`skip_group_policy.py` 實測 399／400（餘裕 1）但 fan-out 只有
**1**（`skip_tag_policy`），它是被 3 個消費者叫的政策 leaf，不是合成面；該族真正的 hub 是
`windows_skip_tags.py`（fan-out 4，實測 356／400 餘裕 44，**不需要**本格的放寬，故刻意
不收進成員清單——收一支不需要的進來只會稀釋這個 tier 的語意）。⇒ `skip_group_policy`
貼牆這件事**本格沒有解**，它的正解仍是既有那條路（六支收斂成三支），見缺陷帳本 ARCH-09。

`ROOT_TOOLS_HUB_MEMBER_CAP`＝成員數**上界**（只准調小）。今天 1 支：`quota_gate.py`。
要加第二支＝先改這個數字，那一行 diff 就是「有人在放寬單檔上限」的可見痕跡（同
`SPECIAL_FILES` 的解鎖紀律：先拆職責／抽共用模組，確認不可壓縮後才具名調整並在缺陷帳本
寫理由）。`ROOT_TOOLS_HUB_MIN_FANOUT`＝fan-out 下界：至少 import 這麼多支**同層**
`tools/lib/*.py` 才算 hub。取 3 的理由是判別力：`tools/lib/` 現況逐支 AST 實查，fan-out
≥3 的只有 `quota_gate`(5) 與 `windows_skip_tags`(4)，而 leaf 族全部是 0~1 ⇒ 門檻落在兩個
族群之間的空隙上，不是落在密集區（改成 2 會把 leaf 族的上緣掃進來，改成 5 則只剩今天這
一支＝寫死現況）。

## count_loc() 計價規則沿革（ADR-XPLAT-013）

（原住 `count_loc()` 函式 docstring 內；現行版本只留計價契約本身與回歸鎖指標，
歷史修正過程搬到本節）

🔴 為什麼改（缺陷本體）：舊實作把「整行 `#` 免費、docstring 全額」寫成硬編二分，
於是「把 docstring 逐字改寫成 `#` 前綴」可在 raw 行數與可執行 AST 節點數**都逐字
不變**的前提下大幅降低計價 ⇒ 一道套利門；而且它被本工具自己的違規訊息逐字教過
（那句指引已於同一次變更移除）。改後兩種載體同為敘事、同為免費。回歸鎖＝
`AutoClaude/tests/contract/test_loc_budget_tiered.py::
test_narrative_carrier_swap_is_priced_identically`（合成檔前後相等）。

🔴 門「關掉了」這句話的射程（否決權複審 M1 訂正——原文寫「門在**值域上**關閉」，
該句已被實測推翻）：改用敘事桶的第一版**把門搬家並變寬了**——`Expr(Constant(str))`
的 `(lineno, end_lineno)` 涵蓋整個物理行，於是 `""; x = 1` 這種裸字串前綴能讓任一行
免費（實測 `.claude/hooks/block_destructive_git.py` 558→316，−43.4%，而 raw 行數與
每一個 AST 邏輯節點皆逐字不變）。已由 `guard_line_taxonomy._shared_code_lines()`
在值域上補掉（同一份合成套用後 558→558，+0.0%），回歸鎖＝同一支 contract 檔的
`test_a_bare_string_prefix_cannot_buy_a_free_line`。**仍未關**的殘留是「多語句擠一行」
（`a=1;b=2`）——那不是本案開的門：它在舊計價下同樣省錢、且同時減少 raw 行數，是
行數制計價的共有性質。唯一擋它的 ruff E702 在 `.claude/hooks/` 沒有閘門，見
ADR-XPLAT-013 §6 缺口 ⑥。

誠實劃界：shebang／PEP 263／`ASSERTION_PRAGMA_COMMENTS` 這三類整行 `#` 依分類器的
強制歸斷言規則**改為計價**（改前免費）。母體限定的實測值（M2 訂正——原文寫「全樹零檔
上升」是假數字）：**閘門計價母體** 286 支（`build_reports()` 207 ＋
`root_tools_reports()` 79；`SPECIAL_FILES` 走 `count_raw_lines`、不在本函式母體）
新值 > 舊值的檔數＝**0**；放大到**全樹** 5557 支 tracked `.py` 則有 **2 支上升**：
`AutoClaude/tests/tools/test_scaffold_sprint_section.py` 116→118、
`AutoClaude/tests/tools/test_snapshot_sync_sprint_skeleton.py` 113→116。機制不是上述
三類，而是**指派給變數的字串裡的 Markdown 標題**（舊判準看到行首 `#` 就免費＝把
Markdown 誤判成 Python 註解；新判準因該字串不是裸 `Expr(Constant)` 而歸斷言）。
方向皆收緊、兩支皆未破線。

## AutoClaude/tools/ 自治納管（本次修法）

**掌舵者裁決**：把 `check_loc_budget.py`（連同 `AutoClaude/tools/` 其餘檔案）併入
根層 `ROOT_TOOLS_TIERS` 的既有掃描機制，不另開一套獨立分級——同一份「LOC 分級」
知識只有一個家，這是本檔一路在治的病（見〈根層 tools/ LOC 分級立案（R75）〉）。

**落地前乾跑實測**（`count_loc()` 逐檔套用，assertion-only 計價；日期見本文件頁首）：
`AutoClaude/tools/` 頂層 38 支 `.py` ＋ `AutoClaude/tools/hooks/` 7 支 `.py`，
逐檔計價後**最大值** 546 行（`check_loc_budget.py` 自己，經本次史料搬遷後）／
496 行（`run_act_core.py`）／451 行（`ab_compare_backends.py`），**沒有任何一支
超過 `guardrail_cli` 的 750 行預算**——與任務書預想的「5 支以上立即變紅、需分階段」
不同，乾跑結果是 **0 支變紅**，因此直接完成**全目錄納管**，不採取「只納管自己」的
保守選項。

**落地方式**：`ROOT_GUARD_ROOTS` 新增第三個掃描根 `PROJECT_ROOT / "tools"`
（即 `AutoClaude/tools`）；`ROOT_TOOLS_TIERS["guardrail_cli"]` 的 `patterns` 新增
`"AutoClaude/tools/"` 前綴，沿用既有 750 行絕對紅線預算（不發明新數字、不另立新
tier）——與根層 `tools/`／`.claude/hooks/` 同一個 tier、同一套判準、同一份報表。
`AutoClaude/tools/hooks/`（AutoClaude 子專案自己的 Claude Code hooks）隨 `rglob`
一併納入，與根層 `.claude/hooks/` 同等級看待。

**下一輪待辦（本輪刻意不做）**：本輪只做「打開掃描範圍」這一步，不逐檔評估
`AutoClaude/tools/` 內是否有檔案適合細分出獨立 tier（例如未來若出現共用函式庫
子目錄，可能需要比照 `guardrail_lib` 另立一格）。目前該目錄沒有 `lib/` 子目錄，
故不需要。
