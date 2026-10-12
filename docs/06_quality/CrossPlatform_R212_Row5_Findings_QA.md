VERDICT: APPROVE
本樹（`git diff HEAD` 指紋 54581ffdde2c…）上我親跑的根層全套、AutoClaude 全套與 pre-push 快層各道皆 RC=0；64 個有效突變殺掉 53 個，存活的 11 個無一指向 P≤2（6 個可證等價或冗餘、5 個是測試牙口缺口或顯示面）；前六次宣稱的數字逐項對得上，其中 3 處須補環境、觸發方式或讀數時點限定（皆 P3 文字訂正）。

# CrossPlatform R212 第五列 QA 零信任複審（執行與數字對帳）

> 角色：QA 鏡（唯讀；model=sonnet）。範圍：本列清倉模式（DEF-200-528 這一帳本列）新碼＋前六次響應宣稱的數字。紀律：未跑 `--pace`／`--issue`／`--revoke`／`--run`；未改任何 tracked 檔；未動 `~/.autosdd`（`--status` 與反事實重算前後以檔案快照比對，零差異）；網路只用了 `gh`（任務書授權的雲端對帳）。突變一律在 scratchpad 複本進行。未做構造性對抗搜尋（量既有判準的紅面，構造性命中計 0）。

## 〈一〉對四問宣稱的逐項核對表

### 一-A 四問

| # | 宣稱 | 我驗到的 | 判定 |
|---|---|---|---|
| 1 | Q1：第四列真跑全過（手寫 halt 標記→哨兵→calendar 到點→probe→真 claude -p -r（haiku）→窗內 hook 派生 --arm-sentinel 被擋→relay no_progress 出口→哨兵原地重掛） | 磁碟痕跡仍在，我用入庫判決器事後唯讀重判：`wakechain_e2e.py --judge 14fb33dc-4ffc-40c9-b62b-9dcf801d02f4 --since 2026-10-12T13:37:54+08:00` RC=0；S14-core 8 項 PASS＋1 項 WARN（S6b：活任務書已清，工具設計內降級）、tail 7 項 PASS＋1 項 WARN（C8：alert 紙條已清）。bootout 痕跡檔逐字含 526 早退事件（事件名 `arm_skip…_inside_job`，全名見該檔；xpc "0"、ppid 1、job_pid 63538、2026-10-12T13:55:03+0800）；成本帳該 SID 一筆 measured=true、model=claude-haiku-5-5。`--selftest` RC=0，負對照（526 早退被繞過）如設計紅在 S2／S3／S5a／S5b。 | 核實（事後重判 15 項 PASS／2 項 WARN）。「根因」的因果判讀不屬 QA 可驗範圍 |
| 2 | Q1：判決 22 項全 PASS | 22＝S14-core 9＋tail 13（Run4 證據檔〈二〉）；那是手動 judge4.py（住另一 session 的 scratchpad，不入庫）。入庫判決器自述只涵蓋 S14-core 9＋tail 8＝17 項，上列我重判的正是這 17 項 | 22 項＝轉述〔他包回報〕；17 項子集本場重現 |
| 3 | Q1：花費 $0.024 | 證據檔記 CC cost-state totalCostUSD=0.024004；金額來源是 harness 記帳，不可重現。本場只驗到成本帳列（cache_read 78087、model haiku、measured=true） | 轉述〔他包回報〕 |
| 4 | Q1：E2E 入庫 `tools/probe/wakechain_e2e.py`（--selftest／--judge／--run） | 入庫屬實；`--selftest`、`--judge` 本場跑通。工具檔頭自述「--run 只被 mock 驗過、未在真機整段跑過（那次真 launchd 驗收＝主控以手動 RUNBOOK＋judge4.py 親跑）」 | 入庫屬實；對外摘要須帶「--run 未在真機整段跑過」（見〈三〉P3-5） |
| 5 | Q1 誠實劃界：Windows 零真機樣本（R212 範圍內）、真 429 寫標記端無新樣本、24 小時／多次 reset 連續閉環未做 | 本場沒有與之矛盾的樣本；CI 的 Windows 綠只證明 smoke 與腳本面 | 相符（不樂觀） |
| 6 | Q2：§16 結案帳 101 列四格，現況 ✅30／➖33／⏸30／📎8 | 解析 PRD §16.2 表（72 列）：HEAD 的結案格＝➖33／⏸30／📎8／✅1，加矩陣原判 ✅29 ⇒ ✅30／➖33／⏸30／📎8（合計 101）；工作樹＝➖33／⏸29／📎8／✅2 ⇒ ✅31／➖33／⏸29／📎8（合計 101） | 前六次數字屬實；本列之後應報 ✅31／➖33／⏸29／📎8。§16.3 (b) 仍印 ✅29／⏸31（見〈三〉P3-4） |
| 7 | Q2：A4 清倉模式由 ⏸ 轉 ✅，入口 DEF-200-528 這一帳本列 | (a) 主帳本 229 列 DEF，未結（open／routed／無法分類）0 列。(b) 以落款檔 `readings_at_issue` 與 events 檔的 `--pace` 決策時刻重算 `decide()`：無授權＝cap=1 rec=1 band=prepare binding=five_hour；有授權＝cap=4 rec=2 band=converge binding=seven_day；逐軸 session／five_hour 為 cap 1→8 rec 1→4、weekly_all／seven_day 為 cap 2→4 rec 1→2，與證據〈三-3〉清倉段逐字同值。(c) 以 18:16 讀數（週 75%／五小時 8%）重算無授權＝cap=1 rec=1 band=prepare binding=five_hour，與〈二-1〉逐字相符。(d) `--status` 重跑 RC=0、六項皆 ✓；以當下真實快取（週 81%／短窗 43%）算：無授權 cap=2 rec=1、有授權 cap=4 rec=2 | 機制與證據相符。但「現在可派」天花板是 2（rec 取 cap_prepare），PRD 列「cap 由 1 升至 cap_converge」≠ `--pace` 標題 cap=2（遲滯）（見〈三〉P3-3） |
| 8 | Q2（隱含）：PRD 所有功能已完成 | 101 列中 ✅31；其餘 ➖33（退役／不適用）、⏸29（無再開症狀不做）、📎8（殘留＝證據）；§16.3 (c) 的 54.4% 是 v2.1.17 快照值 | 「全部完成」不成立，不得用於回覆掌舵者；可說的是「v2.1 範圍結案帳無未分類列」 |
| 9 | Q3：標準＝repo `env.shared`＋出廠 `ENV_SPEC`；本機 `.env` 只放例外；四層載入鏈；`--env-doctor` | `--env-doctor` RC=0：env.shared 4 鍵、.env 4 鍵（提示 [empty-local]：已無任何有值行，可刪）、載入鏈「行程 env > AutoClaude/.env > .env > env.shared > 出廠」；`--print-env-example` 與入庫 `.env.example` 逐位元相同，第 84 行 `AUTOSDD_QUOTA_BURNDOWN_OFF=`；`sync_onboarding_baselines --check` 與 `--check-snapshot` 皆 RC=0 | 核實 |
| 10 | Q3：git post-merge hook 自動對齊（Windows 真機未驗） | `tools/git-hooks/post-merge` 存在且可執行；`core.hooksPath` 指向 repo 內 `tools/git-hooks`（本機生效）；行為鎖（test_quota_env_layers 等）在根層全套與四模組子集皆全過；Windows 面無法驗 | mac 面核實；Windows 驗不到（宣稱自帶劃界） |
| 11 | Q4：不需要馬上切到 Windows | 本列新碼的 Windows 面：新 CLI 在 `PYTHONIOENCODING=cp1252` 下 `--help`／`--status` RC=0、未知引數 RC=2（DEF-200-525 同型風險未重演）；windows-compat-ci 於 1818de87 success（Windows smoke 30 步成功、1 步略過＝失敗明細上傳的條件步驟）；Windows CI 的根層發現數 5338＝本機 5352 減本列新增 14。無 Windows 真機（R212 範圍內） | 未發現必須立刻切的理由；是否切屬決策，本場驗不到真機 |

### 一-B 數字對帳（前六次宣稱與本列骨架的每個數字）

| 數字 | 本場結果 | 標記 |
|---|---|---|
| commit 1818de87「29 檔」 | `git show --stat --format= 1818de87`：29 files changed, 1543 insertions(+), 47 deletions(-) | 本場驗到 |
| 回填 8395affa | 1 file changed, 1 insertion（`CrossPlatform_R212_E2E_Run4_Evidence.md`） | 本場驗到 |
| 六支 CI 全 success（root-infra-ci 38230301052／AutoClaude CI 38230301082／macos-compat-ci 38230301062／windows-compat-ci 38230301093／arch-fitness 38231604962／drift-daily 38230947003） | `gh run list --commit <完整 sha>`：六個 run id 逐一吻合、conclusion 皆 success；逐 job 檢查：gating job 全 success，條件略過的只有「失敗明細落檔上傳」步驟與 nightly／mutation／perf／PG-E2E／advisory 等排程或條件專屬 job。**事件欄位：4 支 push、2 支 schedule（arch-fitness、drift-daily；headSha 恰為 1818de87）** | 本場驗到；「push 觸發六支」措辭不精確（P3-1） |
| 8395affa 的雲端 | root-infra-ci 38232622448 push success；AutoClaude CI 38237108791、artifact-cleanup 38236357222 為 schedule success；macos／windows 因僅動 docs 不觸發 | 本場驗到 |
| 根層全套 rc=0 | 本樹 RC=0；發現 5352 項（下限 5326）、47 項平台標籤略過（`[WINDOWS-NATIVE-ONLY]`）、worker=9、2 分 10 秒；雲端同 commit 三平台皆「發現 5338 項」（5338＋14＝5352） | 本場驗到 |
| AutoClaude「5248／156」 | 本機 dev venv：RC=0、5248 項通過／156 項略過、42.20 秒（含 sqlalchemy／psycopg2／alembic）。**同一 commit 的 AutoClaude CI 摘要行＝5146 項通過／224 項略過（106.11 秒，無 PG extras）**；ONBOARDING §7 表② macOS＝5148／222（dated snapshot，無機械鎖）。本列未改 AutoClaude（`git diff HEAD --stat` 零路徑） | 本場驗到；缺環境限定（P3-2） |
| 帳本未結 0 | 以 repo 自己的分類器解析：主帳本 229 列，fixed 179／closed-by-decision 49／no_action_needed 1，未結 0；外部阻塞軌 5 筆、結構性長債軌 6 筆另列（工具輸出明寫不計入） | 本場驗到；須寫「主帳本未結 0」（P3-9） |
| 22 項判決 | 見一-A #2 | 轉述〔他包回報〕，17 項子集重現 |
| $0.024 | 見一-A #3 | 轉述〔他包回報〕 |
| 週額度 57%→76% | 燃燒落款檔 weekly_all：57 @12:20:52 → 63 @13:57:23 → 67 @14:53:35 → 74 @17:11:58 → 75 @18:16:51 → 78 @19:32:54；`--status` 反事實腳本讀到的現快取 81 @19:58:09。76 這個點值帳本沒有列 | 端點量級吻合、76% 點值驗不到 |
| Dev 的 400／14／259／187 | 四模組 400 項全過（8.1 秒）；`test_quota_burndown` 14 項全過；AutoClaude 契約側四檔 259 項通過；`test_adr_xplat001_c1c2_lock` 187 項全過（主控已報的 187） | 本場驗到 |
| Dev 的 LOC 數字 | `quota_burndown.py` 斷言行 243、`quota_gate.py` 497／500（餘 3）、`quota_policy.py` 301、`quota_pace.py` 368、`quota_messages.py` 387 | 本場驗到 |

## 〈二〉P≤2 清單

**無。** 我檢查過、判為不升級的三處：

1. 「現在可派」天花板仍是 2：附錄 §4.4 值域表自己預告 converge×far 為 (cap 4, rec 2)，且 QB1 的上限夾層是 cap_notice；證據〈三-3〉逐字誠實列出遲滯與 rec。屬設計天花板，不是未治好的缺陷；措辭問題在 P3-3。
2. 清倉授權可由模型自行 `--issue`：附錄 §3.4 與掌舵者裁決 QB3 已明文「載體不具防偽性質」並被接受，不計。
3. 守衛面准入：暴露證據（掌舵者原文＋sid＋`--pace` 逐字）在證據〈二-1〉，且我以 18:16 讀數重算重現了該畫面（cap=1 binding=five_hour），滿足 R197 准入。

## 〈三〉P3（當輪改文字或補牙）

每條格式：座標／重現／判準／級／處置。

**P3-1 提交訊息「push 觸發六支 workflow」不精確。** 座標：8395affa 提交訊息。重現：`gh run list --commit <1818de87 完整 sha> --json name,event,databaseId`——arch-fitness 38231604962、drift-daily 38230947003 的 event 為 schedule。判準：事件欄位逐字。處置：提交訊息不可改；證據檔〈八〉寫「4 支 push＋2 支 schedule（headSha 皆 1818de87）皆 success」。

**P3-2 「AutoClaude 全套 5248／156」缺環境限定。** 座標：1818de87 提交訊息與前六次摘要。重現：本機 `python -c "import sqlalchemy, psycopg2"` 兩者皆在（2.0.51／2.9.12）；`gh run view --job 114747855579 --log` 的摘要行為 5146 項通過／224 項略過。判準：同一 commit、不同環境，兩個數字都對，但只有 CI 數字是出廠環境基線。處置：對外寫「dev venv（含 PG extras）5248／156；CI 出廠環境 5146／224」。

**P3-3 PRD §16.2 A4 列「`--pace` cap 由 1 升至 `cap_converge`」與證據逐字不符。** 座標：PRD §16.2 A4 列【2026-10-12 落款】末段。重現：證據〈三-3〉的 `--pace` 標題＝`cap=2 recommended=2`（遲滯維持，逐軸 cap 為 cap_converge）；`~/.autosdd/traces/autosdd_burndown_events.jsonl` 我讀取時唯一一列 `cap: 4, rec: 2`。判準：標題數字與列文必須同尺。處置：改為「決策 cap 1→cap_converge；`--pace` 標題 cap 1→2（遲滯，每 ≥300 秒 +1）；recommended 1→2」；回覆掌舵者時明說「現在可派 1→2，不是放到 8」。

**P3-4 PRD §16.3 (b) 仍印 ✅29／➖33／⏸31／📎8。** 座標：PRD §16.3 (b) 列。重現：解析 §16.2 表得 ✅31／⏸29（兩次轉格）。修訂表 v2.1.18／v2.1.19 已宣告「不重算」，但該格自身沒有快照時點標記。處置：該格加「v2.1.17 快照；其後轉格見修訂表 v2.1.18／v2.1.19」。

**P3-5 E2E 對外摘要。** 座標：1818de87 提交訊息「E2E 入庫…」＋〈一-A〉#2／#4。判準：入庫工具覆蓋 17 項、`--run` 未在真機整段跑過（工具檔頭自述）；22 項來自不入庫的手動判決器。處置：摘要寫明，避免讀成「22 項判決已入庫且可重跑」。

**P3-6 測試牙口缺口（突變存活；現行碼正確，但宣稱的性質沒有測試釘住）。**
 (a) 派工 hook 的 kill-switch（突變 G5）。突變：`quota_gate()` 內 `quota_burndown.active(state, now, env, core_signature)` 的 env 換成 `{}`；14 項仍全過。我另寫探針（只存在 scratchpad 複本）：真碼下 `AUTOSDD_QUOTA_BURNDOWN_OFF=1` 時 hook 的 `decide()` 不帶授權（觀測值 `[None]`）；突變下仍帶（`['46514ba380']`）。現有測試只在 `pace_report` 路徑驗 kill-switch。
 (b) 寫入端 QB4（突變 B21）。突變：刪 `issue()` 開頭的 fallback／model-scoped 拒絕；14 項仍全過。原因：`put_cache` 夾具只有 session／weekly_all／five_hour／seven_day，`("nope","weekly_scoped","spend")` 三者都因「快取沒有這一軸」被拒，分不出原因。以含 weekly_scoped／spend 的合成快取實測：真碼三者 RC=1 不落檔；突變下 weekly_scoped、spend 皆 RC=0 且落款（消費端 verdict 仍擋，故是縱深缺口不是洩漏）。
 (c) 裝飾性斷言（Rule 9）。`test_bd3` 的 `assertGreater(max(d.cap, P.cap_prepare), 0, …)` 恆真；`test_naming_the_long_window…` 的 `assertIsNone(Q._cap_for(Q.BAND_FREE, Q.AXIS_FAR, P))` 斷言的是 quota_policy 而非本模組。兩者不會因本列邏輯改變而紅；真正的牙在同測試的其他斷言（Q6／Q7／B5a 等突變被殺）。
 判級：P3。處置：R213 標籤的回歸鎖軌現為 305／309、主軌 0，純新增測試行不免費；可把 (c) 的裝飾行等量換成 (a)(b) 的真斷言，淨行數約 0。若不補，降級登記為 P4（再開症狀見〈四〉）。

**P3-7 幽靈鍵鎖靠註解過關。** 座標：`tools/tests/test_context_budget_guard.py::QuotaEnvFileIsActuallyLoadedTest::test_every_key_in_the_example_is_one_the_code_reads`。重現：該鎖以「鍵名字面出現在固定消費者清單檔內」判讀；`quota_burndown.py` 不在清單，鎖由 `quota_gate.py` 呼叫點旁一則註解裡的鍵名過關（Dev 報告 §6-2 已自陳）。若刪掉真讀取點（`OFF_ENV`）而保留該註解，此鎖不紅（kill-switch 本身由 burndown 測試另守，突變 B13c 被殺）。證據檔未載此取捨。處置：二擇一寫進證據檔——把 `quota_burndown.py` 加進該鎖的 consumers 元組（單行），或明記「以註解過關」。

**P3-8 清倉段在 `--pace` 輸出重複。** 座標：`quota_messages.pace_line()` 與 `quota_policy.describe()` 各追加一次（證據〈三-3〉逐字可見，兩段各約 380 字元）。兩支測試分別釘住（`assertIn(d.burndown.text, Q.describe(d))`／`assertIn(…, QM.pace_line(…))`）。主控已自陳並請四鏡判級：P3（噪音，不影響決策）。處置：只留一處並同步改兩支斷言。

**P3-9 「未結 0」限定。** 重現：見〈一-B〉。處置：回覆寫「主帳本未結 0（外部阻塞軌 5 筆、結構性長債軌 6 筆另列）」。

**P3-10 新檔命名會讓 pre-push 快層變紅（與 diff 內容無關）。** 座標：`tools/check_defect_log_crossref.py` 的 `unregistered_governance_docs()`。重現：Architect／SA／SD 三份 `CrossPlatform_R212_Row5_Findings_*.md` 落地後我重跑 `python tools/check_defect_log_crossref.py` → RC=1，訊息「具名治理文件涵蓋面與磁碟脫節（3 筆）」並早退（12 道檢查未執行）；本檔是第 4 份、同樣命中 `CrossPlatform_*.md` 慣例。判準：命中慣例而未登記進 `tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS` ⇒ 紅。處置：四份 findings 全部登記（並在檔內寫明所屬類別），或併入 BurnDown 證據檔後刪除；這是本場唯一會擋 push 的項目。

**P3-11 證據〈三-3〉判讀 (1)「下令前後同一組軸（週軸 78%、短窗 29%）」。** 座標：證據檔〈三-3〉判讀 (1)。重現：下令前唯一的 `--pace` 是〈二-1〉的 18:16 讀數（週 75%／五小時 8%），下令後是 19:34 讀數（78%／29%），兩組讀數不同。實質判斷成立：我以落款檔 `readings_at_issue` 與 events 檔時刻重算，78%／29% 下的無授權決策同為 cap=1 rec=1 band=prepare binding=five_hour。處置：把「同一組軸」改成「以落款檔 `readings_at_issue` 重算的無授權決策」，並寫出這個可重現的對照，不要用兩次不同讀數的 `--pace` 對照。

## 〈四〉P4 理論洞（只登記；每條附可觀測再開症狀）

| # | 洞 | 暴露度 | 再開症狀 |
|---|---|---|---|
| Q-1 | `active()` 外層 fail-closed try/except 無測試（突變 B43 存活；內層 `verdict` 逐步 try 已擋多數例外） | 突變量測，無真實命中 | 派工 hook 的 stderr 出現源自 `quota_burndown.py` 的 Traceback，或落款在位時扇出型工具呼叫被 hook 崩潰放行 |
| Q-2 | `--issue` 以量測當下當 now 讀過期快取，這個性質無測試（突變 B31 存活；Dev 只手動驗過） | 突變量測 | `--issue` 拒絕訊息含「現有：無（stale-cache…」而同刻 `--pace` 仍能印出各軸 |
| Q-3 | SessionStart 簡報額度行（`session_brief.quota_line` 的 `decide()` 無 burndown）與 `--pace` 不同尺——DEF-200-432 修過的同族漂移；落款在位期間簡報也不提清倉 | 讀碼＋反事實重算，未見真實簡報畫面 | SessionStart 簡報的 `⇒ cap=…` 與同刻 `--pace` 標題不同，且 `--status` RC=0 |
| Q-4 | 效期只比 `now < until`；視窗被提早重置時落款仍在位（附錄 §7.3「新視窗結構性不匹配」只在重置恰於 until 發生時成立；字串全等判準會被伺服器亞秒抖動誤殺——燃燒帳同一視窗 resets_at 兩次量測差 0.63 秒） | 設計比對，無真實命中 | `--status` RC=0 而被點名軸 pct 比 `readings_at_issue` 低 10 個百分點以上 |
| Q-5 | `Burn.left`（「效期剩 N 分鐘」）無獨立釘（突變 B42 存活：夾具剛好 left＝7663） | 突變量測 | 清倉段印的剩餘分鐘與 `until − now` 差超過 1 分鐘 |
| Q-6 | 底線③ 的端到端臂缺席：分軌軸與被點名軸 `resets_at` 字串全等、且 active_model 與分軌軸同家族時，只有 `_eligible` 單元級斷言（突變 B45 僅被單元測試殺） | 突變量測 | `--status` 的「本次放寬」清單出現 weekly_scoped／seven_day_opus／seven_day_sonnet |
| Q-7 | 同窗鄰軸零容差字串全等（Dev 與附錄 §9-5 已記）；真實落款檔 weekly_all 與 weekly_scoped 差 185 微秒、weekly_all 與 seven_day 全等 | 真實資料已見（落款檔），目前不影響結果 | `--status` 放寬清單缺少與被點名軸同 reset 的非分軌軸（例如 seven_day 沒跟著放寬） |
| Q-8 | 6 個等價或冗餘守門（B5b rec 夾層被 cap 夾層蓋住、B11 軸缺席項被 `next()` 的 fail-closed 蓋住、B13a 早退被 verdict 項蓋住、B15 named 項實務上不可達、B17 `_in_cap_gate` 項被更嚴的 `_eligible` 蓋住、B25 後兩欄 list 檢查被 `tuple(None)` 例外蓋住） | 突變量測，可證等價 | 無（不是缺陷；簡化這些守門時才需要有人重做等價證明） |

## 〈五〉我跑過的指令與 rc 逐字

工作樹指紋（我的跑期內不變，跑前跑後各量；之後主控續寫證據檔不在此列）：`git diff HEAD | shasum -a 256` ＝ `54581ffdde2cfcc57b87a560b01b1c028f9c7bf97255fd8bf7dcad80edb11277`；`CrossPlatform_R212_BurnDown_FourParty_Evidence.md` ＝ `cc5cf3faff82…`；`tools/lib/quota_burndown.py` ＝ `35aec32604bf…`；`tools/tests/test_quota_burndown.py` ＝ `da6c35e80566…`。launchd 哨兵數 `launchctl list | grep -c AutoSDD_Sentinel_`：跑前 2、根層全套後 2、全部結束後 2（兩個都是活 session 的哨兵）。

### 五-1 根層全套
```
cd <repo> && unset AUTOSDD_PARALLEL_TESTS; AUTOSDD_SENTINEL_OFF=1 python tools/run_root_unittests.py > <scratchpad>/qa/qa_root.log 2>&1   → RC=0（11:44:46Z～11:46:56Z）
✅ unittest 數量下限釘選通過：發現 5352 個測試（下限 5326）
🧾 收集面盤存：91 支 test_*.py 檔／指紋 b3f25431c013
[cpu_budget] root-unittest workers=9 source=cpu_budget
📊 派工摘要：worker=9｜S=970.1s｜ideal=max(S/W, 最長單位)=107.8s（S/W-bound）｜loss=1.00x｜slot 利用率=99.6%
```
尾 15 行＝12 行為 `[WINDOWS-NATIVE-ONLY]` 清單尾段（6 支測試名各附理由行，因含英文動詞過去分詞字樣不逐字抄入本檔；原檔在 scratchpad `qa/qa_root.log`）＋最後 3 行（逐字）：
```
[skip census] tools/tests@darwin 共 47 支：platform=47／tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=0／欠債型 0 支（目標 0）
[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次 skip 47 支）
✅ 真實 TEMP 圍籬：全套期間真實契約目錄（與 autosdd_quota.json 同目錄）下 autosdd_pace*.json 零變動（前 3／後 3 份；目錄 /Users/wuweihong）；隔離根已建立並清除。
```
全套寫出 3 個 `tools/.last_failure_*.log`（runner 自測的合成 import 失敗，gitignored）；已刪除（開了→收了）。

### 五-2 AutoClaude 與靜態閘
```
cd AutoClaude && python -m pytest tests/ -q -p no:cacheprovider     → RC=0；最後一行＝5248 項通過／156 項略過，42.20 秒（本檔禁用英文動詞字樣，原行在 qa/qa_ac.log）；[cpu_budget] xdist workers=9；PG 未在聽（PG 測試略過）
cd AutoClaude && PYTHONUTF8=1 lint-imports                          → RC=0；Contracts: 9 kept, 0 broken.
python AutoClaude/tools/check_loc_budget.py --json                  → RC=0；total=17962 baseline=17079 cap=20438；root_tools_violations []、tier_violations []、special_violations []、absolute_violations []、total_violation False；root_tools_warn_band：quota_escalation 400/400、skip_group_policy 400/400、session_resume_planner 750/750、quota_gate 497/500（餘 3）、schedule_backend 397/400（餘 3）
AutoClaude 契約側四檔（test_r86_pace_contract／test_r100_boot_self_check／test_r82_quota_axis_and_shipped_defaults／test_check_loc_budget_hub_tier_and_special_stale）-n 0 → RC=0；259 項通過
```

### 五-3 本列新碼品質
```
ruff check tools/lib/quota_burndown.py tools/tests/test_quota_burndown.py → RC=0（ruff 摘要：全部檢查通過）
ruff check（8 個被改的既有檔）                                               → RC=0（ruff 摘要：全部檢查通過）
ruff check tools/                                                           → RC=0（ruff 摘要：全部檢查通過）
ruff check tools/ .claude/hooks/ --no-cache                                 → RC=0（ruff 摘要：全部檢查通過）
python tools/check_pytest_baseline_sites.py                                 → RC=0（12 份掃描檔中僅 SSOT 載有基線數字）
python tools/check_defect_log_crossref.py                                   → RC=0（Architect 檔出現之前）；其後 RC=1，見 P3-10
python tools/check_handoff_carriers.py                                      → RC=0（當前輪＝R212；掃描到的前瞻宣稱 0 筆）
python tools/check_ntfs_paths.py                                            → RC=0（27997 個 tracked 路徑，0 違規）
python tools/check_script_parity.py／check_wrapper_thinness.py／check_gha_action_versions.py → 各 RC=0
python tools/archive_defect_log.py --check                                  → RC=0（70 檔／1638 個 ID）
python tools/sync_onboarding_baselines.py --check／--check-snapshot          → 各 RC=0
python tools/refresh_nightly_anchor.py --check-head                         → RC=0
python tools/_script_scan_surface.py --list --suffix .ps1 --with-latest --check-floors → RC=0
python tools/lib/quota_policy.py --print-env-example | grep BURNDOWN         → 84:AUTOSDD_QUOTA_BURNDOWN_OFF=（產出與 .env.example 逐位元相同）
python tools/lib/quota_policy.py --env-doctor                               → RC=0；結論：0 個問題
cd tools/tests && python -B -m unittest test_quota_burndown test_quota_policy test_quota_env_layers test_quota_reconcile_gap → RC=0；400 項全過
cd tools/tests && python -B -m unittest test_quota_burndown                 → RC=0；14 項全過（連跑 15 次 0 失敗；14 項逐一單跑 0 失敗；反向字母序 RC=0；TZ=UTC／Asia/Taipei／America/Los_Angeles／Pacific/Kiritimati／Pacific/Pago_Pago 皆 RC=0）
cd tools/tests && python -B -m unittest test_adr_xplat001_c1c2_lock        → RC=0；187 項全過
PYTHONIOENCODING=cp1252 python tools/lib/quota_burndown.py --help／--status → 各 RC=0；--bogus 與無引數 → RC=2
python tools/probe/wakechain_e2e.py --selftest                              → RC=0
python tools/probe/wakechain_e2e.py --judge 14fb33dc-4ffc-40c9-b62b-9dcf801d02f4 --since 2026-10-12T13:37:54+08:00 → RC=0（S14-core 8／8＋WARN 1；tail 7／7＋WARN 1）
python tools/lib/quota_burndown.py --status                                  → RC=0（落款 45c49b8e35 仍生效；六項 ✓；效期剩 7562 分鐘）；前後快照 ~/.autosdd/traces 與 $TMPDIR 的 autosdd／quota 檔零差異
```

### 五-4 突變實驗（scratchpad 複本，每個突變從 base 全新複製；`AUTOSDD_TRACE_DIR`／`AUTOSDD_QUOTA_CACHE_DIR` 指向 scratchpad 子目錄；驅動器 `qa/mutdrv/run_mutants.py`、`run_mutants2.py`）
共 65 個突變；B13b 補丁不完整（`active()` 早退仍在）為無效突變，由 B13c 取代；有效 64 個：**殺掉 53、存活 11**。14 支測試每一支都至少殺掉一個突變。

| 測試 | 殺掉的突變 |
|---|---|
| `test_naming_the_long_window_relaxes_boundedly_and_leaves_the_floors_alone` | B5a B18 B19 B37 B38 P1 P2 P3 Q1 Q2 Q3 Q4 Q6 M1 |
| `test_pace_and_the_dispatch_hook_both_carry_the_directive` | B13c B27 B39 B41 G1 G2 G3 G4 G6 P2 P4 Q2 Q4 |
| `test_red_every_floor_conjunct_is_load_bearing` | B1 B2 B3 B4 B44 B45 B46 |
| `test_bd9_authorised_but_inert_says_so_with_reasons` | B6 B7 B28 B29 Q2 Q4 |
| `test_issue_status_revoke_roundtrip_and_argument_errors` | B26 B30 B32 B39 B40 Q2 |
| `test_bd3_halt_still_stops` | B3 B33 B46 Q6 Q7 |
| `test_valid_then_each_conjunct_breaks_it` | B10 B12 B13c B23 B24 |
| `test_naming_the_short_window_gets_only_the_same_window_effect` | B14 B38 P2 Q1 Q4 |
| `test_neighbours_need_string_equality` | B16 P2 Q1 Q4 |
| `test_bd6_bd7_a_turned_over_or_unparseable_window_is_never_armed` | B8 B9 B36 |
| `test_bd2_the_ladder_never_tightens_over_every_cell` | B6 B7 |
| `test_refusals_never_leave_a_file` | B20 B22 |
| `test_bd4_fallback_kinds_are_never_relaxed_even_when_named` | B33 B44 |
| `test_bd8_must_finish_wins_over_the_relaxation` | Q5 |

任務書點名的三例：拿掉 FALLBACK 合取項（B1）→ 被 `test_red_every_floor_conjunct_is_load_bearing` 殺（端到端的 BD-4 測試殺不掉單層拿掉，因為 `_in_cap_gate` 也排除 fallback；兩層一起拿掉的 B44 才被 BD-4 殺）；夾層改全域地板（B38 逐軸地板、Q7 聚合後全域地板）→ 被長窗主測試與 `test_bd3_halt_still_stops` 殺；過期判準改成只看檔案存在（B36）→ 被 `test_bd6_bd7_…` 殺。

存活 11 個：B5b B11 B13a B15 B17 B25（可證等價或冗餘，見〈四〉Q-8）、B21 B31 G5（測試牙口缺口，見 P3-6／Q-2）、B42（Q-5）、B43（Q-1）。Dev 報告 §4 表列各判準的紅面，對真實模組突變全部會紅；缺口不在紅面，而在表外被宣稱的三個性質（寫入端 QB4 拒絕、過期快取仍可 `--issue`、派工 hook 路徑的 kill-switch），三者的突變皆存活。

### 五-5 雲端
```
gh run list --commit 1818de87fbbb5a96673008d50eeb1e619ce22223 --json name,conclusion,status,databaseId,headSha,event,createdAt,updatedAt → RC=0；6 筆全 completed／success
gh run list --commit 8395affa322e27f5aa14ee9c3e1309ccdb0f7c2b （同上）                                                                    → RC=0；3 筆全 completed／success
gh run view <6＋1 個 run id> --json jobs                                                                                               → 各 RC=0；非 success 的步驟只有「失敗明細落檔上傳」（條件步驟，conclusion 為略過）
gh run view --job {114747855579,114747855455,114747855252,114747855412} --log                                                          → 各 RC=0；發現數／摘要行如〈一-B〉
```

### 五-6 唯讀的反事實重算（`qa/mutdrv/counterfactual_*.py`；只呼叫公開純函式，未寫任何檔）
- 落款檔 `readings_at_issue`＋events 檔時刻（19:34:35）：無授權 cap=1 rec=1 band=prepare binding=five_hour；有授權 cap=4 rec=2 band=converge binding=seven_day。
- 18:16:51 讀數（證據〈二-1〉）：無授權 cap=1 rec=1 band=prepare binding=five_hour（與證據逐字相符）。
- 當下真實快取（19:58:09，週 81%／短窗 43%）：無授權 cap=2 rec=1 band=converge binding=seven_day；有授權 cap=4 rec=2。

### 五-7 開了→收了
- `tools/.last_failure_8395affa_*.log`（3 個，我的全套自測寫出）→ 已刪。
- scratchpad 突變複本（`mut_*`、`exp_*`）→ 已刪，僅留 `qa/mut/base`（供重跑）與驅動器。
- 背景工作 2 個（根層全套、AutoClaude 全套）→ 皆已結束；無殘留行程。
- 未啟動 Docker、未建 venv、未動 launchd／哨兵、未動 `~/.autosdd`、未呼叫 `quota_meter` refresh。

## 〈六〉文件訂正清單（對主控骨架與前六次宣稱的措辭）

1. 證據檔〈八〉：「六支 workflow」→「4 支 push（root-infra-ci、AutoClaude CI、macos-compat-ci、windows-compat-ci）＋2 支 schedule（arch-fitness、drift-daily）皆 success」；補 8395affa 的 3 筆；CI 數字寫「根層發現 5338 項（三平台）、AutoClaude 出廠環境 5146 項通過／224 項略過」。（P3-1、P3-2）
2. 證據檔〈三-1〉末句「根層全套第四輪（最終樹）rc=1：5 紅」：已被補兩行 guard-total 標記修復；在〈八〉寫本樹實跑 RC=0（工作樹指紋見〈五〉開頭）。
3. 證據檔〈三-3〉判讀 (1)：「同一組軸」改為「以落款檔 `readings_at_issue` 重算的無授權決策」。（P3-11）
4. PRD §16.2 A4 列「cap 由 1 升至 `cap_converge`」→ 決策 cap 與標題 cap 分開寫（P3-3）；§16.3 (b) 加快照時點（P3-4）。
5. 證據檔（任一節）補一句：幽靈鍵鎖以註解過關或改鎖（P3-7）；清倉段重複的處置（P3-8）。
6. 對掌舵者的回覆：Q2 不得用「全部完成」，數字報 ✅31／➖33／⏸29／📎8；清倉效果報「現在可派 1→2（硬上限經遲滯逐步到 4）」；E2E 報「--run 未在真機整段跑過、22 項來自手動判決器」；全套數字報「dev venv 5248／156；CI 出廠環境 5146／224」；未結報「主帳本未結 0」。
7. 登記四份 `CrossPlatform_R212_Row5_Findings_*.md`（P3-10）。
