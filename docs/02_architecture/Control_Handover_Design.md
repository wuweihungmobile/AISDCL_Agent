# 背景代理的主控掌控、自動換 session 演算法與新 session 接續（Control & Handover）設計稿

> 🔒 **凍結（spec-frozen，2026-11-22）**：r3 定稿。approver＝掌舵者（常態規則 2026-10-20，sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13；主控執行，主控 sid 814608d1-c56d-4b1f-9303-6b2dbff9b0d0）。reason＝QA 規格審查 r1 FAIL（P1 0／P2 8／P3 7，`w2_specqa_report.md`）→ r2 全數處置；QA 窄範圍複審 r2（`w3_specqa2_report.md`）確認 15 條到位、新發現 P2×2（N-1 park_cli 行數牆、N-2 parkprobe↔park_cli 匯入矛盾）＋P3×3，並建議 r3 後只核這兩點；r3 處置後主控親驗：§21 第 631 行 `park_cli.py` 列（393／400，early 本體移 `parkearly.py`）、§16 第 540～541 行與 TCS AT-CTL-58 匯入方向單向（`parkprobe` 不 import `park_cli`／`parkearly`）；PRD 對修憲前 blob `5af6ce952d70…` 行級子序列檢核 missing=0、`git diff --numstat` 6 增 0 刪。P1／P2 未結＝0。主控另裁決 W5（`pending_switch`／`switch_due`）保留（§7.7，TH-8 可降）。改動須走新版次並重審。

> 角色：SD 系統設計（AISDLC 第 2 階段；W2-SD）。日期 2026-11-22，量測基準 HEAD＝`d68b2b01`（工作樹另有 R218-B S2 半成品，tag `r218b-s2-20261121-wip-preserved`）。**版次 r3（r2 依 QA 規格審查 FAIL〔P1 0、P2 8、P3 7〕改版；r3 依 QA 窄範圍複審 FAIL〔新增 P2 2、P3 3〕小修；待再審）**。
> **r2 變更摘要**：①`sealed_effective` 改四值（`none｜unreadable｜effective｜invalidated`）並逐消費端寫行為（§3.2、§4.1、§4.2）；②`pending_switch` 只認硬線、R2 不寫 pending、作廢規則不自相矛盾、寫入不依賴 `.advised` 閂鎖，且**封存閘觸發條件不改**（§7.3、§7.4、D-CT-6／7／11）；③更正「現行靜默」措辭、暴露證據改引真逐字稿並誠實標註「情境成立、損害在現行機制下未證」（§0.1、§7.6、§7.7、§13）；④`account_changed` 基準值＝park 標記新欄 `parked_account`（`account_key`），欄名常數住 `parkprobe.py`、不進 `qw_schema`（D-CT-9、§8.2）；⑤新增〈SA 需求去處表〉十二列（§20），含 B4「ack 後撤 park」查證與修法（§20.2、WP W4b、REQ-CTL-47）；⑥工作包循序 **W1 先、QW Q2 後**（§15、§17 N-1）；⑦行數牆逐包拆檔方案（§21）；⑧PRD 鎖改釘修憲前 blob（§19）；⑨P3 七條處置（§22）。r2 對 QA 發現的處置表＝§22。
> **r3 變更摘要（只修 QA 複審 5 條，其餘設計不動；處置表＝§22 末段）**：①N-1：§21 補 `park_cli.py` 列（現查 393／400）並更正 `roster.py` 現值 375；park 提前到點的觸發本體與 `--status` 增列文字移出 `park_cli`；②N-2：新增葉模組 `parkearly.py`（early 入口 `tick`／`fire_early`），`parkprobe` 退為純判準葉、定義 import 方向，消除循環；③P3-n1：封存閘條件「非 `effective`」改為「`none` 或 `invalidated`」（§7.2 H 列、§7.4）；④P3-n2：TH-1～TH-7 改含 TH-8（§18 第 3 問；TCS §7 第 5 項）；⑤P3-n3：`ensure_pending` 呼叫點刪「封存閘 Stop」（§7.4、D-CT-11）。
> 輸入：W1 全貌 `w1_context.md`、Architect 報告 `w1_arch_report.md`（下稱 **ARC**）、SA 報告 `w1_sa_report.md`（下稱 **SA**）、主控裁決 14 條（下稱 **裁1～裁14**）、兩份已凍結未完工設計 `QuotaWall_CacheContinuity_Design.md`（下稱 **QW**）與 `RealVerify_SideEffect_Isolation_Design.md`（下稱 **SE**）、現行換 session 設計 `SessionSwitch_CostModel_Design.md`（下稱 **SS**）與 ADR-XPLAT-004 §2.13／§2.14／§2.17／§2.18／§2.19。以上 W1 報告與主控任務書在主控 sid `814608d1-c56d-4b1f-9303-6b2dbff9b0d0` 的 scratchpad，收尾窗口把關鍵段落抄進證據檔。
> 上游：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 **PRD**），修憲走 §16.5 (i)（本稿已追加 v2.1.26，見 §19）。驗收：`docs/03_testing/contracts/TCS-Control-20261122.md`（下稱 **TCS**；前綴 `REQ-CTL-`／`AT-CTL-`／`E2E-CTL-`／`MU-CTL-`；真機家族 `control`，id `RV-CTL01`～）。
> 本稿落地的新程式路徑在實作 commit 前不存在；落點依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2（§16）。本稿**不改** QW／SE 兩份凍結稿；需他稿追加的註記集中在 §17，由收尾包套用。

---

## 0. 結論與代決

### 0.1 結論（七句）
1. **問題 3 有一個已被真實逐字稿證明的 P1 缺陷（A4）**：冷叫醒閘把「已封存、未交棒、主控仍在工作」當成已交棒，推回要求 TaskStop 在飛子代理與其 watch；封存閘卻用 `worked_since` 判「封存後有工作＝封存失效」。同一個事實兩個閘各答一次、答案相反。14 天 12 次推回；sid `65389f03` 逐字稿第 2332～2335、2516～2519 行兩次實發。成因是**封存的有效期只有一個閘認得**，修法是把它做成**單一謂詞** `control.sealed_effective`，不是在冷叫醒閘再補一條例外（那是壓制）。
2. **問題 3 的另一半是「看得見」**：掌舵者看到的畫面（`status` 列出沙盒殘局代理 `a28de7322775c13d3｜rv waiter`、Stop 時才有的一行 systemMessage）無法回答「現在誰在管這些代理」。本稿加：控制態單一判準 `control_state`、`status` 一行、SessionStart 殘局／被切代理公告、statusLine 區段（載具是 repo 內 `tools/statusline_context_feed.py`，不改 `.claude/`）。
3. **問題 4 的答案是「半自動」，本稿把『何時換』寫成一條可重放的演算法**（§7）：輸入十一項、輸出五種動作（留／立即換／排空後換／park 至 t／park 輪詢），第一個命中即回；每一路指名既有載具與憑證。**不新增任何換窗門檻**——硬線 85 萬、F4 成本選路、R2 品質訊號、QW 額度階段全部沿用；新增的只有「排空後換」「防抖 30 分」「帳號變更＝快取必冷」三個原先沒有定義的輸入／輸出。
4. **近 14 天真逐字稿重放**（§7.6）：45 個主控 session，硬線 4 次（其中 3 次當下有在飛代理＝新演算法判「排空後換」；現行機制在這種情形的實況是 PreToolUse 於硬線擋新派工〔`converge.py:53-70`〕、代理交卷後首個 Stop 由封存閘推回〔`seal.stop_verdict`〕，缺的只是「醒來時的提示」，見 §7.4／§7.7）、R2 8 個 session、冷回 39 次其中 F4 判換新 9 次（8 次未封存＝無載具，歸理論洞 TH-5）；park 提前到點重放 8 個標記中 1 個命中（`65389f03`：換帳號後 14:53 即可提前接手，比預定 11/24 19:03 早 52.2 小時、比實際人手開窗早約 23 分鐘）。
5. **park 等待期間額度提前恢復（含換帳號）⇒ 提前到點接手**（§8，裁12）：哨兵（零 token 的 OS 巡邏）每 15 分讀一次額度（巡邏相隔 900 秒，現查；TTL 與相隔皆為現行值）（`quota_meter` 唯讀 GET、TTL≥180 秒，PRD §15.5 紅線 1 豁免四條件），讀數較 park 當時**下降**且低於準備門檻即走既有 fire 路徑；換帳號後快取必冷，F4 強制 `cold=True`，大上下文自然走 FRESH 帶交接包。不另造第二套判準：讀數單調性（同窗不減）沿用 QW S-19 的推理。
6. **交接包機械層補三處**（§9）：第 12 欄「在飛／被切代理」（誰、做到哪、輸出落點、重派短任務書指標）、第 13 欄「鏈上前幾棒」（`.prompts.md` 路徑鏈、各棒最近真人提示摘錄、前幾棒 scratchpad 的可重啟點／任務書／交卷指標）、機械層欄 1 加主控模型；SA 的十項清單逐項標註（機械層補／主控層手寫／不做＋WHY）。finalize **仍只驗結構**（裁9）。
7. **刻意不做**（§12）：軟線／便宜線／階段邊界大就換（掌舵者 2026-11-18「專注在不要讓 Cache 過期」、R1 退役、SS §11）；hook 代替主控機械 finalize／spawn（裁3，登記理論洞 TH-1 與升級條件）；被切代理自動重派（裁10，只列清單、由主控重派）。

### 0.2 主控裁決落地對照（裁1～裁14，照辦、不重議）
| 裁決 | 落地 | 座標 |
|---|---|---|
| 裁1 封存後派工＝封存失效，不禁止派工；真交棒維持要求 TaskStop；單一謂詞住 `control.py` | `control.sealed_effective`（四值，r2）；冷叫醒閘與封存閘共用；`wake_package` 吃它 | §3、§4；REQ-CTL-01～04 |
| 裁2 換手遇在飛代理＝排空後換；牆內例外沿用 QW「先 TaskStop 再封存」，重派資訊入第 12 欄 | `pending_switch` 標記（只認硬線）＋watch `switch_due`；W 列走 QW D-D；**主控裁決 2 的代決，暴露證據標註見 §7.7（情境成立、損害未證）；最小實作＝watch 提示＋標記，封存閘觸發條件不改** | §7；REQ-CTL-22～25 |
| 裁3 hook 不代主控 finalize／spawn；登記理論洞＋升級條件寫死 | TH-1 | §13 |
| 裁4 名冊預設限本 repo 專案 slug、排除沙盒 slug；`--all-projects` 保留舊行為；slug 判準取 `sandbox_scope`；新 `rosterscope.py` | `rosterscope.py`；常數 `SLUG_FRAGMENT` import 自 `sandbox_scope` | §6；REQ-CTL-11～13 |
| 裁5 可見：statusLine 區段（載具 `tools/statusline_context_feed.py`）＋SessionStart 殘局／被切代理公告＋`sessionctl status` 一行；憑證值取自排程器／心跳，不取自述 | `control.status_line`、`controlfacts.segment` | §6.3～§6.5；REQ-CTL-14～16 |
| 裁6 排序：QW Q1 先；W1 在 Q1 之上；不得新增 QW 十一欄名字面；`converge.py` W1 先、QW Q4 後；watch／keepwarm 與 Q2 二擇一 | §15 全局排序；**W2 排在 Q2 之後（獨立包）**，理由見 §15.2 | §15 |
| 裁7 M-W1 改讀真憑證；新增 M-C1；`advise_once` 痕跡 `switch_advise` | §10；REQ-CTL-29、39～43 | §10 |
| 裁8 硬線 85 萬維持；軟線／便宜線一律不做 | §7.2 決策表無任何新上下文門檻 | §7、§12 |
| 裁9 finalize 只驗結構 | REQ-CTL-21（負向需求） | §9.4 |
| 裁10 被切／被殺代理不自動重派；名冊判「被切」與「殘局」，在主控下一回合（Stop systemMessage／watch 判決／SessionStart 公告）與第 12 欄列出 | §6.4、§9.1；REQ-CTL-19～20 | §6.4、§9.1 |
| 裁11 防抖：同 session 鏈 30 分內不連換 | 決策表 D 列 | §7.2；REQ-CTL-26 |
| 裁12 park 等待期間額度提前恢復（含換帳號）⇒ 提前到點接手 | `parkprobe.py`、哨兵分支、`park.recovered` | §8；REQ-CTL-31～38 |
| 裁13 第 12 欄＋鏈上原話＋前幾棒 scratchpad 指標；SA 十項逐項標 | §9 | §9；REQ-CTL-17～18 |
| 裁14 換手「適時」判準寫成明確演算法，附決策表、遲滯、載具憑證、一致性證明、重放分佈 | §7 | §7 |

### 0.3 SD 代決（可隨時以 T1 推翻）
| 代號 | 決定 | WHY |
|---|---|---|
| D-CT-1（r2 改） | `sealed_effective` 回**四值**：`none`（從未封存：戳檔不存在）｜`unreadable`（戳存在但逐字稿讀不到或戳解析失敗）｜`effective`（戳存在、逐字稿可讀、戳後無非唯讀非監督 `tool_use`）｜`invalidated`（戳後有）；每個消費端對四值各寫行為（§3.2 表） | r1 的三態把「從未封存」與「未知」併成 `None`，逐字照做會使「尚未封存、ctx≥硬線」不再被封存閘推回（QA P2-1）；封存閘的主功能就是推「未封存」，`none` 必須與 `unreadable` 分流。現行 `worked_since` 對讀不到檔回 `False`（偏放行），故 `unreadable` 由 `control` 先驗檔案可讀、不改 `worked_since` 語意 |
| D-CT-2 | 「監督／封存流程呼叫」不算封存後工作：`sessionctl.py (handoff｜park｜status｜keepwarm｜watch｜runlong｜waitfor｜quotawall｜switch-plan)` 與 `TaskStop`／`TaskOutput`／`BashOutput`／`AskUserQuestion` 一律排除；`Agent`／`Task`／`SendMessage`／任何寫入／其他 shell 都算工作。文法單一家＝`control.is_supervision_call`，QW S-24② 的 `keepwarm.work_mark` 改 import 它 | 現行 `worked_since` 把 `park`／`keepwarm` 也算工作，封存→park→keepwarm 這條**正規流程**會使封存立即失效（硬線以上時封存閘每次 Stop 都再推重封存）；排除監督呼叫才是「封存後主控又做了會改變交接內容的事」的原意 |
| D-CT-3 | 冷叫醒閘只在兩種情形推 TaskStop：①真交棒（`handed_over`）⇒ 全部在飛任務（含代理）；②封存**有效**（`sealed_effective == "effective"`）⇒ **只**針對「既非監督 shell、也非代理」的背景 shell（例：`ci_wait`、長跑測試）。封存有效而有在飛**代理**時，冷叫醒閘一律不推，交給監督閘（無憑證則推「掛 watch」） | 把 CI-1(c)(d) 落到閘：在飛代理必有監督（CI-1），所以同一個 Stop 輸出不得同時要求殺掉代理與監督代理；只有真交棒才有「舊 session 不該再被叫醒、代理又無法轉移」的理由，此時 TaskStop 才是對的（A4 現場的矛盾正是把這兩種情形混為一談） |
| D-CT-4 | `watch` 單例：**先到者贏**，後到者印 `WATCH_VERDICT=duplicate` rc 0 立即結束；鎖＝`holder` 同型（pid＋行程建立時間），檔 `watch/<sid>.lock`；心跳檔鍵改 `<sid>.<pid>.json`，憑證取任一新鮮 | 先結束者 `finally` 刪共用心跳檔會讓後結束者誤報「無」（ARC A3）；後到者取代先到者會使先到者的 harness 完成通知晚於預期叫醒主控一次，先到者贏最省 |
| D-CT-5（r2 改） | `pending_switch` 標記只存 `{reason＝"hard", since, ctx}`，**條件每次重算**；作廢＝現算 `sealed_effective == "effective"` ∨ `handed_over` ∨（`ctx` 量得到且 `ctx < hard`＝容量問題已被 harness 壓縮解掉）；`ctx` 量不到不作廢。**無 `hard/2` 條件**（r1 的 `hard/2` 對任何壓縮後 session 恆成立，與「R2 pending」互相打架，已刪） | 標記若存「條件成立」會過期失真；只存 `since` 供排空期限用，其餘一律現算（同 QW §3 `wall_state` 的現算哲學）。ctx 在無壓縮下單調不降，`ctx < hard` 即「發生過壓縮」，不需要第二個門檻 |
| D-CT-6（r2 改） | 排空期限 `DRAIN_MAX_MIN＝30`：待換逾時仍有在飛代理且 ctx 仍 ≥ 硬線 ⇒ `decide` 輸出 `SWITCH_NOW(drain_overdue, taskstop_first)`；**載具只有文字提示**——`watch` 下一次任一判決的處置字尾加「待換已逾 30 分：可 TaskStop 全部在飛代理（重派資訊已入第 12 欄）後 `handoff --finalize`」，以及 `switch-plan` 輸出；**不新增推回、不新增 WATCH_VERDICT 事件**。pending **只有 `reason=hard`**，R2 不寫 pending | 硬線離 autocompact 最小點只差約 3 萬 token（`costmodel.OBSERVED_AUTOCOMPACT_MIN`＝881,938，現查 `AUTOSDD_SWITCH_HARD_CTX_TOKENS`）；排空不能無限等；30 分＜閒置自動壓縮約 55 分（SS §1.4）。r1 的「R2 pending 無期限」刪除（QA P2-2：與 D-CT-7 自相矛盾） |
| D-CT-7（r2 補） | R2（壓縮≥R2）在互動 session **不產生推回、不寫 pending**，只設 `prefer_fresh`：任何本來會「續跑」的轉換點（park 到點、無人續跑、冷窗轉送）改走 FRESH | 與 R216 一致：R2 原本就只出聲＋影響無人續跑選路（ADR §2.19 D1）；讓它在互動 session 推回封存＝「為大而換」的後門（掌舵者 2026-11-18 否決）。重放 R2 命中 8 個 session，其中 `d4ed2654` K＝8、為期 57.8 小時的長 session，推回只會吵 |
| D-CT-8 | 帳號變更（park 標記 `parked_account` 與當下 `quota_meter.account_key_of()` 不同；基準值的家見 D-CT-9）**只改一個輸入：快取視為已冷**，不新增任何推回；live 窗口在換帳號後的重寫帳列 TH-4 | 換帳號後新帳號從未見過這段前綴，下一個請求必然整份建立；F4 的 `cold` 輸入本來就吃這個事實。live 窗口在換帳號後的重寫損失**本棒未檢查**（`quota_burn` 近 14 天 4 次帳號變動，只有 11/22 一次落在 armed park 區間內；其餘 3 次的 live 窗口重寫帳未驗證），無暴露證據，依〈守衛面准入〉只登記 |
| D-CT-9 | park 提前到點的「恢復」判準＝**讀數較 park 當時下降（≥ `EARLY_DROP_PP＝5` pp）且全部主軸低於準備門檻**；park 登記時把當時最大主軸讀數寫進標記 `parked_pct`、並把帳號指紋寫進標記 `parked_account`＝`quota_meter.account_key_of()` 的 `account_key`（`sha256(org-id:workspace-id)[:12]`；量不到寫 `null`）；**兩欄名常數住 `parkprobe.py`（`MK_PARKED_PCT`、`MK_PARKED_ACCOUNT`），不進 `qw_schema`**（r2：寫端 `park_cli._cmd_park` import `parkprobe` 常數，讀端 `parkprobe`／`controlfacts` 同源；`parkprobe` 是純判準葉模組，**不 import `park_cli`、不 import `parkearly`**；r3 import 方向（單向無環）＝`session_resume_planner → parkearly → {parkprobe, park_cli}`、`park_cli → parkprobe`（只取常數與 `baseline`／`status_row`），early 觸發入口 `parkearly.tick`／`parkearly.fire_early` 見 §21；`park.marker_problem` 不拒未知欄、`_settle` 以 `dict(marker, …)` 保留未知欄，W6 AT 鎖「往返保留」）。WHY 選 `account_key` 而非 `--pace` 的方案指紋（`plan_fingerprint`／`core_signature`）：後者量的是桶名集合（額度狀態），R90 已實測 29%（10/35）跨方案逐字相同；`account_key` 是取自回應標頭的身分訊號（`quota_gate` 的 `account_key` 欄與 `quota_burn` 的 `account=` 指紋同源）。WHY 不進 `qw_schema`：該檔的跨包欄名清單由 AT-QW-61 掃「十一個字面只准住 `qw_schema`」，加第 12 個＝要改凍結稿的 AT 與計數（r1 的 N-3）；本欄只在 W6 單包兩端使用、Q3 之後，無跨包持有面，不需要進跨包 SSOT，也就不產生他稿註記 | 讀數不能單看絕對值：`park --why` 在**未達門檻**時也能登記（下一棒放不下），絕對值判準會一輪巡邏就誤觸發；同窗讀數單調不減（QW S-19 的推理），所以「下降」是換窗或換帳號的充分條件，且下降本身不需門檻校準 |
| D-CT-10 | 提前到點的載具＝**哨兵巡邏分支**（既有 OS 排程、零 token、15 分一次），不新增排程、不在 park job 內輪詢 | park job 是一次性、到 `backup_fire_at` 才跑；主載具 keepwarm 對 `--at` 型目標是單跳睡到目標（QW §2.2 S5），讀不到額度；哨兵是唯一定期醒來且不依賴 session 存活的零 token 行程 |
| D-CT-11（r2 新） | pending 寫入**不經 `advise_once`、不依賴 `.advised` 閂鎖**：`switchplan.ensure_pending(sid, ctx, hard, now)` 在兩個消費端（watch 每次輪詢、`control_state`／`switch-plan`）**惰性冪等建立**（r3：不含封存閘 Stop——該閘只在「無在飛代理」時觸發，建立條件「在飛代理 > 0」在該點恆不成立，且 §3.1 要求 `seal.py` 只 import `control`）——條件＝`ctx ≥ hard` ∧ 在飛代理 > 0 ∧ 無檔；`since`＝首次觀察時刻，已有檔不覆寫。`advise_once` 只多一個呼叫（寫痕跡 `switch_advise`） | R2 先出聲會吃掉 `.advised`（handoff.py:191-203），之後真到硬線不會再進 `advise_once`（QA P2-2③）；惰性建立與閂鎖解耦，無需改 `advise_once` 的閂鎖結構（該檔 LOC 貼天花板，§21）。代價：`since` 是「首次被觀察」而非「首次越線」，最多晚一個輪詢間隔／一個 Stop，對 30 分期限無實質影響 |
| D-CT-12（r2 新） | **ack 後撤原 session 的 park 標記**：`handoff --ack` 成功後，由新模組 `ackhook.on_ack(pkg, acker_sid, env)` 對包擁有者 sid 的 armed park 標記呼叫 `park_cli.cancel_marker(sid, event="acked")`（把 `_cmd_cancel` 核心抽成公開函式、標記 `cancelled` 並拆備援排程；不加新排程站點，沿 `_cmd_cancel` 既有拆法）；擁有者＝acker 自己（自續跑）不撤 | 查證（§20.2）：`_cmd_fire` 對 `.ack` 已 `skip("acked")`（park_cli.py:397），**雙駕駛風險已被到點判準擋住**；但 ack 到到點之間標記仍 `armed`——`park.yields` 讓哨兵讓路、`control:` 行與 `park --status` 顯示「等待中」、備援排程殘留，是今天 11/22 主控得手動 `park --cancel --session-id` 的原因。成因（ack 不通知 park）消除，而非每次靠人撤 |
| D-CT-13（r2 新） | 行數牆：邏輯一律放新模組，既有檔只加 ≤2 行呼叫（§21 逐包方案） | `session_brief.py` 397／400、`session_resume_planner.py` 745／750、`handoff.py` 394／400 餘 3／5／6 行（`check_loc_budget` 口徑），「超線再說」＝實作時才紅，不可 |

---

## 1. 問題陳述與證據

### 1.1 掌舵者原話（逐字）
- **問題 3**（2026-11-22）：「有背景Subagent執行, 沒有主Agent去掌控Subagent! 這是嚴重問題」
- **問題 4**（2026-11-22）：「自動化機制會適時的自動切換新Sesseion嗎?若不會,請設計自動切換新Sesseion演算法, 並且做好新Session的接續機制, 不要遺漏必要資訊! ==> 請Architect / SA / SD / QA 四方專家進行規劃，分析，設計，實作」
- 同日第 2 題（本稿的 E2E 要求來源）：「請繼續完成以上所有任務, 並且進行所有功能的E To E測試, 尤其是請確認AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md 所有功能都有E To E 完整驗證程式, 並完成的E To E所有測試!」

### 1.2 證據座標（本棒零 token 唯讀實查）
| # | 現象 | 證據 | 代碼座標 |
|---|---|---|---|
| E1 | 冷叫醒閘與封存閘對「封存後工作」答案相反 | 痕跡 `finalized_wake_block` 14 天 12 件（sid 31ea79d4×7、e4f80b15、7ba13bb7、4a45bc75、65389f03×2）；`65389f03-4a29-43f2-8228-61cb3c884a4e.jsonl`：finalize@2221／2235 → 封存後 Agent 派工@2253／2262／2311 → 冷叫醒推回@2332（hook feedback）／2335（blocking error）→ 重封存@2468／2492 → 再派 Agent@2502 → 推回@2516／2519 → 唯一一次 TaskStop 在 2686～2702（最後回合一口氣停多個；**已逐筆驗證者僅 2698／2700 兩筆（兩支同時在跑的 watch）**，其餘筆數未逐筆核對，以實查逐字稿為準）；封存戳 `2026-11-21T19:43:01+08:00`（`~/.autosdd/handoff/65389f03-…_20261121T095211Z.sealed`；**注意**：此為後一次 finalize 覆寫後的現值，原兩次封存戳須由逐字稿取，見 TCS E2E-CTL-01）。第 2235／2492 行是 `api-request-blob`、無時戳 | `seal.py:259-268`（`wake_package` 不看封存後工作）、`seal.py:315-319`（封存閘看）、`converge.py:73-104`、`converge.py:96`（只豁免 keepwarm） |
| E2 | 兩支 watch 並存、心跳共用檔被先結束者刪 | 同逐字稿 2698／2700 兩支同時在跑的 watch 被一次 TaskStop | `watch.py:178-180,204-208,326-328`、`supervise.py:167-182` |
| E3 | 沙盒真 `claude` 的子代理記錄混進全域名冊 | `python tools/sessionctl.py status` 列「[殘局] a28de7322775c13d3｜rv waiter｜haiku」，實體在 `~/.claude/projects/C--Users-wuwei-AppData-Local-Temp-AutoSDD-RV-sbx-vi8s6abz/`；同目錄下另有 sbx-4w8e6a8w、sbx-tkovrr1j | `roster.py:43-57`（無 sid 時掃全部專案 slug） |
| E4 | 無看管區間 | M-W1 575 筆／150.5 小時（**上界**：憑證判準未接，恆無憑證）；SA 自寫逐字稿實算 241 段／5,301.7 分（88.4 小時）、>30 分 46 段，集中於 `d4ed2654`（2,091 分）；watch 上線（11/17）後 `31ea79d4` 494 分、`65389f03` 272 分、`4a45bc75` 164.7 分 | SA §二-1、`sa\probe2_out.txt` |
| E5 | 子代理被額度切斷 8／303 支，其後主控沒有清單 | 8 支末筆記錄 `apiError=usage_limit_reached`：4a45bc75 的 a612f2af／aef5829a／aff9c301、65389f03 的 a018beed／ab867bb2、680d8411 的 a5218308／a93a1add、d4ed2654 的 abe51342 | SA §二-1 |
| E6 | 自動換 session 實務上不由演算法觸發 | `session_switch_spawned` 20 次無一次由大小閘門觸發；硬線只被碰到 4 次且全在 11/7～11/10（R216 改制前）；finalize→ack 中位 4.05 分、P90 374.5 分、最大 1,173.6 分（`65389f03`，換帳號後人手開窗） | SA §二-2、ARC B.2 |
| E7 | 約四分之一接續不走機制 | M-S2：37 個互動 session 中 9 個（24%）人手貼上一輪摘要；今天這一棒即是（`65389f03` 封存 11/21 19:43、ack 11/22 15:16，封存到接手 19.5 小時，包內「已驗證」全過時，靠 RESTART_POINT 補，要翻兩個 scratchpad） | SA M-S2、ARC C.2 |
| E8 | park 等 73 小時而額度早已恢復 | `~/.autosdd/traces/park/65389f03-….json`：parked_at 11/21 17:53、fire_at **11/24 19:03**、status 最終 `cancelled`（人手撤，mtime 11/22 15:16:59）；`quota_burn.jsonl` 11/22 14:45 讀數 `account=34cd…`（先前 `eaf5…`）、`seven_day` 0.0；沒有任何機制發現 | §8.5 重放 |
| E9 | 帳號切換不是罕事 | `quota_burn.jsonl` 近 14 天 `account=` 指紋變動 4 次（11/13 20:27、11/14 08:05、11/16 20:13、11/22 14:45） | `sd_acct.py` 重放 |

### 1.3 根因（一句話）
**「已封存」與「已交棒」是兩個狀態，卻被同一個閘合併處理，且封存的有效期只有一個閘認得；而「誰在管在飛代理」只存在於各閘各自的內部判斷、沒有單一真相源，也沒有人眼可見的地方。**

---

## 2. 不變式與破壞狀態收斂

### 2.1 不變式（規範性，進 PRD v2.1.26）
> **CI-1（控制權）**：任何時刻 t，若 `inflight(sid,t) ≠ ∅`（主控 sid 名下有 running 的背景子代理，或主控派出的 `claude -p` 無頭行程），則同時成立：
> (a) 主控行程存活，或有「主控已死」的可偵測且已出聲的狀態；
> (b) 至少一個**喚醒源**存在：harness 完成通知（必然）∧〔`sessionctl watch` 憑證 valid ∨ keepwarm 在掛〕——前者管「交卷」、後者管「停滯／超時／額度／快取」；
> (c) 該 sid 不得同時處於「已交棒」——真交棒前必須先排空，或明確 TaskStop 並把重派資訊寫進交接包；
> (d) 任何閘對 sid 下的指令（TaskStop／封存／spawn／掛 watch）不得與另一個閘的指令互相矛盾。
>
> **CI-2（可見）**：以上狀態對人眼可見至少一處，不依賴人去敲指令。

CI-1(d) 的結構保證＝§3 的單一謂詞；可測形式＝TCS AT-CTL-12（狀態乘積表：任一狀態組合下，同一個 Stop 輸出不同時包含「TaskStop 在飛代理」與「掛 watch 監督在飛代理」）。

### 2.2 破壞狀態 A1～A14 處置表（承 ARC §A.1；嚴重度與暴露證據依〈守衛面准入〉）
| # | 狀態 | 處置 | 落點 |
|---|---|---|---|
| A1 | 回合結束有在飛代理、沒掛 watch，推回只一次 | **不改守衛**（無暴露證據顯示推回後仍不掛；M-W1 恆無憑證＝量測盲，先修量測） | §10 M-W1 改讀真憑證；TH-2 |
| A2 | watch 結束後主控沒重掛 | 同 A1 | — |
| A3 | 兩支 watch 並存、心跳被先結束者刪 | **修**：單例＋心跳 pid 化（D-CT-4） | §5；W2 |
| **A4** | **已封存、未交棒、主控仍派工**（P1） | **修**：單一謂詞（D-CT-1～3） | §3、§4；W1 |
| A5 | 真交棒（ack／forward）時仍有在飛代理 | 守住（spawn 前置拒絕）；ack 先於排空的路徑理論洞 | TH-3 |
| A6 | 已交棒舊視窗在硬線以下仍派 Agent | 理論洞（無實例；M-F3 的 4 件是真人提示不是派工） | TH-3 |
| A7 | 撞額度牆而代理在飛 | 已有完整設計（QW），**本稿不重做**；本稿只提供第 12 欄保存重派資訊 | QW；§9.1 |
| A8 | 主控 `/exit`／視窗關／被殺，代理成殘局 | **補出聲**：SessionStart 公告「上次有 N 支代理未收尾」（偵測既有，出聲新增）；`claude -r` 後在飛代理能否接回＝**未驗證**（harness 行為） | §6.4；W3 |
| A9 | harness 自動壓縮 | 守住（判準讀檔／payload，不受壓縮影響） | — |
| A10 | park／keepwarm 期間 | 守住（`live_driver` 讓路 9 件、0 件雙駕駛） | — |
| A11 | 無人窗口 print 模式 | 守住（設計邊界；本稿 E2E 不得在無人窗口依賴 watch） | ADR §2.12 |
| A12 | 沙盒子代理混進全域名冊 | **修觀察面**：名冊預設範圍（裁4） | §6；W3 |
| A13 | quiet 代理被當成不在飛 | 理論洞 | TH-3 |
| A14 | 使用者看不到「主控監督中」 | **修**：`status` 一行＋SessionStart＋statusLine（裁5） | §6；W3 |

---

## 3. 控制態判準（單一真相源）

### 3.1 模組分工（避免循環匯入）
| 模組 | 內容 | 匯入 |
|---|---|---|
| `tools/lib/sessionctl/control.py`（**葉**） | 純謂詞與純函式：`sealed_effective(stamp, transcript)`、`is_supervision_call(block)`、`ControlState` 資料類、`classify(facts)`（事實→控制態，純合成）、`status_line(state)`／`segment_text(state)`（人眼文字，純 ASCII 區段與中文一行）、常數 | 只依標準庫與 `transcript_activity` |
| `tools/lib/sessionctl/controlfacts.py` | 事實讀取器：向 `seal`、`roster`、`supervise`、`watchlock`、`park`、`holder`、`switch` 取值組成 `Facts` 再交 `control.classify`；對外 `control_state(payload, sid, env)`、`segment(sid, transcript_path)`（statusLine 用，帶 10 秒檔案快取與 150 ms 時限） | 全部 sessionctl 模組 |

`seal.py` 只 import `control`（葉）；`controlfacts` 單向依賴其餘模組；無任何函式內 lazy import（QW S-12 同款結構解）。

### 3.2 `sealed_effective(stamp, transcript) -> "none" | "unreadable" | "effective" | "invalidated"`（r2 四值）
- `stamp`＝`.sealed` 檔內的 ISO 時刻（`seal._stamp`，讀檔仍在 `seal.py`；本函式不讀檔）。
- 判定順序（第一個命中即回）：
  1. `stamp is None`（戳檔不存在）⇒ **`none`**（從未封存，與逐字稿可不可讀無關）；
  2. 戳存在但 ISO 解析失敗，或 `transcript` 缺／不是可讀檔（`control._readable` 先驗：`is_file()` 且可開啟讀首位元組，不改 `worked_since`）⇒ **`unreadable`**；
  3. 戳之後**主控**逐字稿沒有任何「非唯讀、非監督」`tool_use` ⇒ **`effective`**；
  4. 有這種 `tool_use`（封存已失效；再 finalize 即重封存，`seal()` 本就支援）⇒ **`invalidated`**。
- 各消費端對四值的行為（**逐格寫死；CI-1(d) 的單一謂詞要求每個消費端都有答案**）：
| 消費端 | `none` | `unreadable` | `effective` | `invalidated` |
|---|---|---|---|---|
| 封存閘 `seal.stop_verdict` | **照現行**：`ctx ≥ hard` ∧ 未交棒 ∧ 無在飛代理 ⇒ 推「未封存」（保證從未封存的 session 照舊被推回） | 不推（偏放行；現行亦然：戳存在、`worked_since` 回 False ⇒ 視為有效） | 不推 | 推（`why="封存後有工作"`） |
| 冷叫醒閘 `seal.wake_package`→`converge._finalized_wake` | 不推（未封存，E-CW-1） | 不推 | 推（僅「非監督、非代理」背景 shell；D-CT-3） | 不推（A4 病灶：封存已失效） |
| `pending_switch` 作廢 | 不作廢 | 不作廢 | 作廢 | 不作廢（封存失效，仍待換） |
| 換手決策表 F 列（`sealed=effective` 才轉送） | F′（無載具，TH-5） | F′ | F（轉送） | F′ |
| `ControlState.sealed`／`status`／statusLine | `none`（statusLine 無區段） | `unknown`（印 `?`） | `effective`（`ctl: sealed`） | `ineffective`（無區段；`status` 印 `sealed=ineffective`） |
| `forward.py`（冷窗轉送） | 不改（本稿不動 forward 判準，它自有 `.sealed` 讀法；只在 AT-CTL-04 掃描列管） | 同左 | 同左 | 同左 |
- 實作：`transcript_activity.worked_since(path, since_iso, ignore=None)` 增一個關鍵字參數 `ignore`（`Callable[[dict], bool]`，對每個 `tool_use` 區塊回真＝忽略），預設 `None` 時行為**逐字不變**；`control` 傳 `is_supervision_call`。`READ_ONLY_TOOLS` 仍由 `transcript_activity` 持有（單一家）。
- 守衛面：`transcript_activity.py` 在〈守衛面准入〉清單內，暴露證據＝E1（逐字稿座標＋12 件痕跡），夠。

### 3.3 `is_supervision_call(block) -> bool`（D-CT-2；文法單一家）
`tool_use` 區塊 `block` 屬監督／封存流程呼叫，若：
1. 工具名 ∈ `{TaskStop, TaskOutput, BashOutput, AskUserQuestion}`；或
2. 工具名 ∈ `{PowerShell, Bash}`，且其 `input.command` 以 `;`、`&&`、`||`、換行切段後**每一段**都屬下列之一：
   (i) 匹配 `sessionctl\.py["']?\s+(handoff|park|status|keepwarm|watch|runlong|waitfor|quotawall|switch-plan)\b`（import `roster.WATCH_CMD_RE`／`KEEPWARM_CMD_RE` 並補其餘動詞，不另寫第二份 watch／keepwarm 樣式）；
   (ii) 對本 session 監督輸出檔的唯讀讀取（`Get-Content`／`gc`／`cat`／`type`／`tail`／`Select-String`，可接 `Select-Object` 管線），輸出檔＝上列指令的重導目標。
   任一段不屬、或指令解析不出 ⇒ 不是監督（**判不出偏「算工作」**：封存失效是保守側——寧可失效後再封存一次，不讓真工作被視為沒發生）。
- QW S-24②（保溫帳「真工作」）與本判準是同一類問題；本稿定為單一家，QW Q2 的 `keepwarm.work_mark` 一律 import 本函式（§17 註記 N-1）。

### 3.4 `ControlState`（`control.classify` 的輸出）
| 欄 | 型別／值域 | 來源（事實讀取器；憑證不取自述） |
|---|---|---|
| `sid` | str | payload |
| `agents_running` / `agents_quiet` | int | `roster.snapshot(sid)` 的 running／quiet（payload `background_tasks` 優先，同 `seal.agents_running`） |
| `agents_cut` | list[{id, kind∈{usage_limit, stopped, residue}}] | §6.4 判準 |
| `supervision` | `valid｜stuck｜none` ＋ `source∈{payload, heartbeat, lock}` | `supervise.credential`（主證＝payload 內 running 的 watch shell；副證＝心跳新鮮；W2 後心跳取任一新鮮、鎖＝`watchlock` 持有者活著） |
| `next_wake` | ISO｜None＋`carrier∈{keepwarm, watch, park}` | holder 列（QW Q1 欄）、watch 心跳；量不到＝`None`（印 `?`） |
| `sealed` | `none｜unknown｜effective｜ineffective`（＝`sealed_effective` 四值 `none｜unreadable｜effective｜invalidated` 的顯示名；值域一一對應） | `seal._stamp` ＋ `control.sealed_effective` |
| `handed_over` | pkg 路徑｜None | `seal.handed_over`（單一家，不改） |
| `pending_switch` | `{reason, since}`｜None | §7.4 標記讀取 |
| `wall` | bool | QW `wall_state`（Q1 後；之前恆 False） |
| `park` | `{status, primary, backup_next_run, early_probe}`｜None | `park.read_marker`＋排程器自報（`--verify` 才問排程器） |
| `unacked_pkg` | 路徑｜None | `handoff.list_handoffs` |

`status_line(state)` 範例（一行）：
`control: sid=814608d1 agents=2(running) watch=valid(pid 18340, hb 40s) next_wake=15:30(keepwarm) sealed=none handed_over=no pending_switch=no park=none`
憑證值（pid、心跳年齡、`next_run`）由 `controlfacts` 向行程表／心跳檔／排程器取值，不抄標記或主控回覆。

---

## 4. A4 修法（冷叫醒閘新語意）

### 4.1 `wake_package` 與 `_finalized_wake`
- `seal.wake_package(sid, env=None, transcript=None)`：
  - 回「已交棒」的包（不變）；
  - 否則回「最新包 live ∧ `control.sealed_effective(stamp, transcript) == "effective"`」的包；`transcript` 缺 ⇒ 該分支回 `None`（`unreadable`⇒不推）。
  - **既有測試遷移（P3-1）**：預設 `transcript=None` 使封存分支回 `None`，會令既有斷言失敗——W1 動工時現查 `Grep "wake_package" tools/tests`（QA 已列座標：`test_sessionctl_converge.py:486-491`、`test_sessionctl_seal.py:325／348／388` 等），逐檔補傳逐字稿夾具（有 `.sealed` 且戳後無工作的最小逐字稿），**不放寬斷言、不改預設為舊行為**（舊行為＝A4 病灶）；遷移清單寫進 W1 交卷。
- `converge._finalized_wake(payload, env)`：傳 `payload["transcript_path"]`；其餘次序不變。
- `seal.stop_verdict`（封存閘）：把行 316-319 的內聯 `worked_since` 改呼叫 `control.sealed_effective`，依 §3.2 表：`none` ⇒ **照現行推「未封存」**；`unreadable`／`effective` ⇒ 不推；`invalidated` ⇒ 推（`why="封存後有工作"`）。**行為差異**：`park`／`keepwarm`／`status` 等監督呼叫不再使封存失效（D-CT-2）——硬線以上、封存→park→keepwarm 的正規流程不再被每次 Stop 要求重封存。

### 4.2 冷叫醒閘新語意（取代 `converge.py:73-104` 現行）
| 狀態 | 現行 | 新 | WHY |
|---|---|---|---|
| 已交棒（別人 ack／spawn） | 推「TaskStop 全部」 | **不變** | 舊 session 不該再被叫醒（E-HD-1） |
| 已封存、`effective`、有「非監督、非代理」的背景 shell（`ci_wait` 等）；（`effective`＝§3.2 四值之一，下列各列同） | 推 | 推（只列這些 shell） | D-CT-3 ② |
| 已封存、`effective`，在飛代理（不論有無監督憑證） | 推（A4 的病灶之一） | **不推**（無憑證時由監督閘推「掛 watch」，兩閘互斥） | CI-1(d)：不得同時要求殺代理與監督代理 |
| 已封存、`effective`，只剩 keepwarm／watch shell | 只豁免 keepwarm | **兩者都豁免**（`control.is_supervision_shell` 單一家，包 `roster.is_supervision_shell`） | 對稱 |
| 已封存、`invalidated`（A4 現場） | 推（錯） | **不推** | 裁1 |
| 已封存、`unreadable` | 推 | **不推** | D-CT-1 |
| 未封存（`none`） | 不推 | 不變 | E-CW-1 |

### 4.3 為什麼不在冷叫醒閘補「若有派工就放行」
那是壓制：兩個閘仍各自記得「封存」的含義，下一個消費端（forward、keepwarm、statusLine）又要補一次。單一謂詞讓所有消費端對同一事實給同一答案；AT-CTL-04 以原始碼掃描鎖「`sessionctl/` 內除 `control.py` 外不得直接呼叫 `worked_since(`」。

---

## 5. 監督單例（A3）

- `tools/lib/sessionctl/watchlock.py`（新）：`acquire(sid, pid)` 以 `holder` 同型機制（pid＋`holder.start_token`；`holder.is_live`／`pid_alive` 單一家，不複製）寫 `trace_dir()/watch/<sid>.lock`；活著的別人持有 ⇒ 回 `False`。寫不進檔案 ⇒ 回 `True`（互斥是優化、不是監督的前提，同 `holder.acquire` 的處理）。
- `watch.run` 入口（約 6 行）：`acquire` 失敗 ⇒ 印 `WATCH_VERDICT=duplicate`、rc 0、立即結束；處置表 `DISPOSAL["duplicate"]`＝「已有同 sid 的 watch 在掛：不需重掛，繼續本回合或結束回合」。`ORDER` 不含 `duplicate`（它不是 decide 的事件，是入口判決）。
- 心跳檔鍵 `<sid>.<pid>.json`；`write_heartbeat`／`_drop_heartbeat` 只動自己的檔；`supervise.read_heartbeat(sid)` 取 `<sid>.*.json` 與舊 `<sid>.json` 中**最新且新鮮**者。舊格式讀取保留一輪（相容），測試釘「寫出只有新格式」。
- 與 QW Q2 的關係見 §15.2：**W2 排在 Q2 之後**，因 Q2 重做 `watch.run`／`keepwarm.py` 本體，鎖入口必須包在 Q2 定型的 `run` 之上。

---

## 6. 名冊範圍與可見性

### 6.1 範圍（裁4）
- `tools/lib/sessionctl/rosterscope.py`（新）：
  - `repo_slug(repo=None)`：本 repo 在 `~/.claude/projects` 的 slug（沿 `handoff._project_dir(_REPO)` 的算法，不另寫 pattern）；
  - `is_sandbox_slug(slug)`：`sandbox_scope.SLUG_FRAGMENT in slug`（**import 常數，不寫字面**；R218-B 單一家）；
  - `scope_dirs(projects, session_id, all_projects=False)`：給 sid ⇒ 該 sid（行為不變）；無 sid 且非 `all_projects` ⇒ 只回本 repo slug 下的 `*/subagents`；`all_projects` ⇒ 舊行為（全部專案），**但仍標記沙盒 slug 項**（`sandbox=true`），不靜默隱藏。
- `roster._agent_dirs` 改呼叫 `rosterscope.scope_dirs`（`roster.py` 現查 375／400，仍不在其中放新邏輯；roster 只加 1～2 行）。
- `tools/sessionctl.py status` 新旗標 `--all-projects`；預設輸出末尾印一行 `（另有 N 支代理在其他專案／沙盒，--all-projects 查看）`，避免「被藏起來」的反效果。
- 不影響任何閘：所有 hook 呼叫皆帶 sid（ARC A12）。

### 6.2 沙盒殘局不再污染（REQ-CTL-13）
`a28de7322775c13d3｜rv waiter` 屬 `…AutoSDD-RV-sbx-vi8s6abz`；預設範圍下 `status` 不列、`--all-projects` 列且標 `[沙盒]`。負控：本 repo 真專案殘局仍列出。

### 6.3 `status` 一行與 SessionStart 公告
- `python tools/sessionctl.py status` 在名冊之前加 `control:` 一行（§3.4 範例）；`--json` 帶 `control` 物件。
- SessionStart 簡報（`tools/lib/session_brief.py`，守衛面）加一行：上一個 session 有 N 支代理未收尾（殘局，本 repo 範圍）／有 M 支被額度切斷（附「看清單：`sessionctl status`」與第 12 欄所在包）。**沙盒 slug 不公告**。對 A8（`claude -r` 後在飛代理能否接回，未驗證）只出聲、不假設。

### 6.4 被切／被殺／殘局代理的判準與出聲（裁10）
`rosterscope.cut_kind(agent_path, main_transcript)`：
- `usage_limit`：代理逐字稿末筆記錄 `apiError` 含 `usage_limit_reached`，或末筆 assistant 為 `<synthetic>` 且文字含 `hit your`／`usage limit`；
- `stopped`：`rosterscan.killed_ids`（主逐字稿的 `<status>killed</status>` 通知；既有）；
- `residue`：既有名冊 `residue` 狀態。
出聲三處，內容同一份 `agentbrief.render_cut(agents)`：①Stop `systemMessage`（`roster.stop_message` 末加，只在有被切且該 sid 本回合尚未提示過時）；②`watch` 判決處置字尾；③SessionStart 公告。每筆列「誰（id／描述／模型）、做到哪（最後 3 則 assistant 文字摘要）、輸出落點（代理 Write／Edit 的 `file_path` 去重至多 8 個＋任務書內寫明的 scratchpad／handback 路徑）、重派短任務書指標（代理逐字稿首筆 user 記錄＝原任務書的前 600 字＋『重派：新代理＋短任務書，不 SendMessage 續舊代理』）」。**不自動重派**（裁10）。

### 6.5 statusLine 區段（CI-2）
- 載具＝`tools/statusline_context_feed.py::ui_line(payload)`（`~/.claude/settings.json` 的 statusLine 已指向它，`tools/install_statusline.py` 安裝；**不改 `.claude/**`**）。有內容時在既有行尾加 ` | ` ＋ `controlfacts.segment(session_id, transcript_path)`；無內容回空字串＝既有輸出逐字不變（既有測試與 `test_context_window_parity.py` 不動）。
- 區段文字（純 ASCII，沿該檔既有 `_ascii` 紀律）：`ctl: 2 agents watch ok` ／ `ctl: 2 agents NO WATCH` ／ `ctl: 1 agent CUT` ／ `ctl: sealed` ／ `ctl: HANDED-OVER` ／ `ctl: switch pending`；`agents=0` 且無封存／待換／交棒 ⇒ 空。
- 成本與失效：statusLine 每則 assistant 訊息、`/compact` 後、`refreshInterval` 到期都會呼叫；`segment` 帶 `trace_dir()/control/<sid>.seg` 10 秒快取、150 ms 時限、任何例外回空字串（同該檔 fail-open 紀律）、純讀檔不開行程。
- 欄位假設：官方 statusLine 輸入 JSON 含 `session_id`、`transcript_path`（E2E RV-CTL09 以 `~/.autosdd/context_feed/<sid>.json` 的**真實 payload** 驗證；缺 `transcript_path` ⇒ 區段只用 sid 路徑的檔，退化而不報錯）。
- 互動畫面是否顯示該區段、Stop `systemMessage` 是否顯示＝〔OI-20261120-010〕的同款真機目視項，本稿登 V-CTL1（TCS §4）。

---

## 7. 自動換 session 演算法

### 7.1 輸入（`switchplan.Inputs`，十一項；全部有現成真相源，無新量測）
| 輸入 | 值域 | 真相源 |
|---|---|---|
| `ctx` N | int｜None | `roster._scan(transcript)["ctx_tokens"]` |
| `hard` | int | `switch.threshold(HARD_CTX_KEY)`（現查 `AUTOSDD_SWITCH_HARD_CTX_TOKENS`） |
| `compactions` K／`r2` | int／int | `transcript_activity` 壓縮計數／`switch.threshold(R2_KEY)` |
| `cache` | `hot｜cold｜unknown` | `cachestate.cache_state(transcript, now)`；`account_changed` 為真 ⇒ 強制 `cold`（D-CT-8） |
| `quota` | `{stage, short_pct, short_reset, weekly_pct, weekly_reset, stale}` | QW `quotawall.plan`（Q1 前以 `park._pace_state` 的短窗讀數＋`wall_state` 退化版：只有 `none／free／close` 三值，標 `calibrated=no`） |
| `inflight` | `{agents, supervision}` | `controlfacts`（§3.4） |
| `tree` | `clean｜wip_tagged｜dirty` | `handoff._refusals` 同判準（既有） |
| `mode`／`unattended` | auto｜notify｜off／bool | `switch.switch_mode`、`AUTOSDD_UNATTENDED` |
| `account_changed` | bool | park 標記 `parked_account`（登記當下的 `account_key`，D-CT-9）≠ 當下快取 `account_key`（`quota_meter.measure_detail` 寫入）；**任一側 `None`（量不到、舊標記無此欄）⇒ `False`**。無 park 標記的 session 恆 `False`（基準值只存在於 park 標記；本稿不為「session 起始」另造基準檔——無暴露證據，TH-4） |
| `since_takeover_min` | float｜None | 本 sid 為某包的接手者時，`.ack` 時刻距今；非接手者 None |
| `sealed`／`handed_over`／`pending` | `controlfacts` | §3.4 |

### 7.2 決策表（自上而下，第一個命中即回）
輸出 `Decision(action, reason, flags, carrier, credential)`；`action∈{STAY, SWITCH_NOW, SWITCH_AFTER_DRAIN, PARK_UNTIL, PARK_POLL}`；`flags`＝`keepwarm`、`prefer_fresh`。

| # | 條件（全部成立） | 動作 | 載具（既有，不新增） | 憑證（可稽核證據） |
|---|---|---|---|---|
| G0 | `unattended` ∨ `mode=off` | STAY（`gate`） | — | — |
| G1 | `handed_over` | STAY（`handed_over`；本窗不得再動工作樹） | UserPromptSubmit 轉送／「已交棒」告知（`forward.py`） | 痕跡 `forward_handed_over`；包 `.ack`／spawn 列 |
| W | `quota.stage ∈ {close, wall}`，或短窗讀數 ≥ 準備門檻且無有效續航憑證（`park.stop_verdict` 條件） | 目標為週軸／`park --at`／D > 6 小時 ⇒ **PARK_POLL(t)**；否則 **PARK_UNTIL(t)**。有在飛代理 ⇒ 先「TaskStop 全部在飛代理，重派資訊入第 12 欄」（QW D-D）；`mode=notify` ⇒ 只出聲 | QW §5 主載具（keepwarm 單跳／跨重置鏈）＋§7 備援（park 排程）；**本稿 §8**：兩者之外再加哨兵提前恢復探針 | QW 雙憑證（背景任務 id＋`KEEPWARM_PLAN wake_at=`；`PARK_VERDICT=armed … next_run=`）；PARK_POLL 另帶 `early_probe: next_probe=<哨兵 NextRunTime>` |
| D | `since_takeover_min < DEBOUNCE_MIN(30)`（且非 W） | STAY（`debounce`） | — | 痕跡 `switch_plan` |
| H | `ctx ≥ hard` | `inflight.agents = 0` ⇒ **SWITCH_NOW**；`> 0` ⇒ **SWITCH_AFTER_DRAIN**（`ensure_pending` 惰性建立標記，D-CT-11；逾 `DRAIN_MAX_MIN(30)` 仍 `ctx ≥ hard` ⇒ `SWITCH_NOW(drain_overdue)`，僅文字提示，D-CT-6） | 封存閘（Stop，**觸發條件不改**：`ctx ≥ hard` ∧ 無在飛代理 ∧ 未交棒 ∧ `sealed_effective` 為 `none` 或 `invalidated`；`unreadable`／`effective` 不推，同 §3.2）→ finalize → `handoff --spawn`；待換靠 `watch` 的 `switch_due` 提示 | `.sealed`；spawn 痕跡／`.ack`；`pending` 標記檔 |
| F | `cache=cold` ∧ `costmodel.fresh_is_cheaper(ctx, cold=True)` ∧ `sealed=effective`（四值，§3.2） | SWITCH_NOW（冷窗轉送） | `forward.py`（UserPromptSubmit：原文落檔、`handoff.spawn`） | 痕跡 `forward_spawned` |
| F′ | `cache=cold` ∧ F4 判換新 ∧ `sealed≠effective`（`none`／`unreadable`／`invalidated`） | STAY（`cold_unsealed`；**無載具**，TH-5） | — | M-C5 觀測 |
| K | 主控閒置 ∧ 無任何 running 背景任務 ∧ `ctx ≥ KEEPWARM_MIN_CTX` ∧ 非「不掛的情形」 | STAY＋`flags.keepwarm` | Stop 保溫閘 → `sessionctl keepwarm`（R216） | holder／`KEEPWARM_PLAN` |
| Z | 其餘 | STAY | — | — |
| （旗標） | `compactions ≥ r2` | 不改動作；`flags.prefer_fresh`＝真 | 任何續跑選路點（`park.fire_route`、`switch.fresh_reasons`、`forward`）一律走 FRESH | 痕跡 `park_route`／`forward_*` 的 why |

邊界：`ctx` 為 None（量不到）⇒ H、F 不成立（FRESH 的代價是丟上下文，量不到偏續跑，同 SS D2）。W 列在 QW 未實作前（Q1 之前）退化為既有 `park.stop_verdict` 的條件，動作＝PARK_UNTIL。

### 7.3 遲滯與抖動
1. **防抖**：D 列。接手後 30 分內不連換。次序＝W 在 D 之前（牆不等人，不受防抖限制）、H 在 D 之後（剛接手的上下文不可能達硬線，實際 0 命中；保留只為防「finalize→spawn→新 session 立刻又判換」的迴圈）。重放 0 命中（`31ea79d4` 連三包間隔 4.7／7.8 小時）。
2. **單向閂鎖**：同一 (sid, 原因) 的出聲（`advise_once`）各只一次；`pending_switch` 檔存在即不重建（冪等，D-CT-11），與 `.advised` 閂鎖互不依賴；不因 ctx 在門檻附近來回而重複出聲（ctx 在無壓縮下單調不降，實際不會來回；R2 的 K 單調不降）。
3. **待換標記的有效期**：`pending_switch` 只存 `{reason＝"hard", since, ctx}`（D-CT-5）；作廢條件＝`sealed_effective == "effective"` ∨ `handed_over` ∨（`ctx` 量得到 ∧ `ctx < hard`）。ctx 無壓縮單調不降 ⇒ `ctx < hard` 即「發生過壓縮」，容量問題已被 harness 以有損方式解掉，重新評估即可；`ctx` 量不到＝不作廢。與 R2 無任何交互（R2 不寫 pending）。作廢後若 `ctx` 又回到 ≥ hard，`ensure_pending` 會再建新標記（新 `since`）。
4. **提前恢復**（§8）：同一 park 標記至多觸發一次；觸發即寫 `park_early_recovered` 並走 fire 路徑，後續巡邏見標記非 armed 即略過。
5. **QW 側既有閂鎖**（S-18 同窗至多推一次、watch 額度閂鎖）不變。

### 7.4 `pending_switch`（排空後換）
- 檔：`trace_dir()/switch/<sid>.pending`，JSON `{"reason": "hard", "since": "<ISO+offset>", "ctx": <int>}`（`reason` 只有 `hard`）；**寫入端＝`switchplan.ensure_pending`（D-CT-11：惰性冪等，不經 `advise_once`、不依賴 `.advised`）**，呼叫點＝watch 輪詢、`control_state`／`switch-plan`（r3：刪「封存閘 Stop」——該閘只在無在飛代理時觸發，建立條件恆不成立；`seal.py` 亦不得為此 import `switchplan`）。
- 消費端兩處加提示、**一處不動**（單一讀取函式 `switchplan.read_pending(sid)`）：
  1. `watch`：代理全數交卷（`decide` 的 `all_done` 事件）時若有效標記 ⇒ `WATCH_VERDICT=switch_due`（rc 0，處置表：「到換手點：寫完交接包主控層 → `handoff --finalize <包>` → `--spawn`；不再派新代理」）；pending 逾 `DRAIN_MAX_MIN` 仍有在飛代理時，任一判決的處置字尾加「待換已逾 30 分」提示（D-CT-6）；
  2. `control_state`／statusLine（`ctl: switch pending`）；
  3. **封存閘 `seal.stop_verdict` 觸發條件不改**（QA P2-3 最小實作）：「`ctx ≥ hard` ∧ 無在飛代理 ∧ 未交棒 ∧ `sealed_effective` 為 `none` 或 `invalidated`」（r3：與 §3.2 四值表一致，`unreadable` 不推）本來就會在代理交卷後的首個 Stop 推回；pending 不是新的推回條件，R2 session 因此**零新增推回**（QA P2-2①）。
- 為什麼要 `switch_due`：harness 在背景代理完成時本來就會叫醒主控（Bash 工具說明逐字：`re-invokes you when it exits`），但主控被叫醒時不一定記得「待換」；標記＋判決把「待換」變成醒來第一句話看得到的事件。
- 牆內例外：W 列已有收尾流程（QW D-D），不經 pending。

### 7.5 一致性證明（與 R216／QW／SE）
| 規則 | 對應既有判準（函式） | 證明方式 |
|---|---|---|
| H＝R216 D1 | `seal.stop_verdict` 的 `ctx ≥ hard`、`converge._gate`、`context_budget_guard` 出聲 | 同一 `switch.threshold(HARD_CTX_KEY)`；AT-CTL-47：`decide` 在 `ctx≥hard ∧ agents=0` 與現行 `seal.stop_verdict` 逐輸入向量同判 |
| F＝R216 D2 | `costmodel.fresh_is_cheaper`、`forward._forward_verdict` 條件 10 | 同函式呼叫；AT-CTL-47 |
| K＝R216 D3 | `keepwarm.stop_verdict` 的不掛情形集合 | 同函式；AT-CTL-47 |
| W＝QW 階段 | `quotawall.plan.stage`、QW S-16 | 同函式；QW §2.2 S1／S5 的主載具／備援原樣 |
| R2＝R216 D1 末句 | `switch.fresh_reasons` 的 R2 | `prefer_fresh` 只改選路輸入，不改推回 |
| **新增行為僅四處** | AFTER_DRAIN／pending／`switch_due`（**僅提示，不增推回**）、防抖 30 分、帳號變更⇒cache cold、PARK_POLL 的提前恢復探針 | 每處在現行為「未定義」或「只有 PreToolUse 擋派工」：AT-CTL-47 表驅動比對「`decide` 在任何輸入向量上都不在現行不推處新增推回；四處中只有『防抖』與『提前恢復到點接手』會改變實際動作（前者＝不連換，後者＝提前 fire），其餘僅改提示文字或輸入」 |

與 SE：本稿不新增任何 spawn／register／notify 站點（提前到點重用既有 `_cmd_fire` 與 `handoff.spawn`，兩者已在 `SITES`）；新增的唯一站點是哨兵分支裡對額度讀取的呼叫，它不是 `SITES` 的類別（非 spawn／register／fire／tick／notify／headless），但**屬 tick 類**——哨兵 tick 分支入口本來就先過 L1（實作座標＝`sched_isolation.tick_gate`，工作樹 S2 半成品；SE §3.4「tick」列），本稿分支排在其後（§8.3）。

### 7.6 近 14 天真逐字稿重放（零 token、唯讀；腳本 `…\scratchpad\sd_replay.py` 一次性估計，**不入 repo**，輸出 `sd_replay_out.txt`；正式版＝W5 `waste_census --replay-plan`，數字以它為準）
**母體**：`~/.claude/projects/D--CursorProject-AISDCL-Agent/*.jsonl` 近 14 天有動過者 45 個；`quota_burn.jsonl` 896 筆（2026-08-19～11-22）；park 標記 8 個。
| 判定點 | 命中 | 備註 |
|---|---|---|
| H：`ctx ≥ 85 萬` | 4 個 session（3d200496、58ce5ccd、76d1471c、f1522ddb，皆 11/8～11/10） | 其中 **3 個當下有在飛代理**（3d200496×1、76d1471c×2、f1522ddb×3）⇒ 新演算法判 SWITCH_AFTER_DRAIN；現行：PreToolUse 在硬線擋新派工（`converge.py:53-70`）、代理交卷後首個 Stop 由封存閘推回（`seal.stop_verdict`），缺的只是主控被 harness 完成通知叫醒時「待換」不在眼前。座標見 §7.7 |
| R2：壓縮 ≥ 2 | 8 個 session（04b38d83、3d200496、58ce5ccd、742135ef、76d1471c、85bcbec8、d4ed2654 K＝8、f1522ddb） | 只設 `prefer_fresh`，無推回（D-CT-7） |
| 冷回（距上一筆 assistant ≥ 60 分）後有新 assistant | 39 次 | 其中 `2×ctx > F(1+q)`（F4 判換新）**9 次**，**8 次當時該 sid 無封存包**＝F′（無載具，TH-5；不是新演算法造成，是現狀的量化） |
| 閒置 ≥ 45 分的回合間隔 | 82 次 | 保溫（K）的母體；成效以 M-K1／M-K2 為準，不在本稿 |
| D：防抖 | 0 命中 | 現有包鏈最短間隔 4.7 小時 |
| park 提前恢復（D-CT-9，格點＝`parked_at＋n×15 分`，讀數取格點前最近一筆、≤1 小時內） | 8 個標記中 **1 個**命中：`65389f03` 於 **11/22 14:53**（讀數時刻 14:45、帳號變動＝是）；提前 **≥ 52.2 小時（下界）**（預定 11/24 19:03）；人手實際開窗 15:16（標記 `cancelled` 於 15:16:59）＝約早 23 分。**下界理由**：`quota_burn.jsonl` 在 11/21 19:16 與 11/22 14:45 之間無任何讀數，14:45 是第一筆新帳號讀數、不是額度實際恢復的時刻，真實可提前量只多不少 | 其餘 7 個（等待 0.4～9.9 小時）區間內未見讀數下降＝照原排程；負控成立（沒有誤觸發） |
### 7.7 `pending_switch`／`switch_due` 的暴露證據與代決聲明（r2；QA P2-3）
- **這是主控裁決 2 的代決**（「換手遇在飛代理＝排空後換」），SD 不否決也不擴張；依〈守衛面准入〉逐項標註：
  1. **情境成立（真實逐字稿、非構造）**：近 14 天重放硬線（85 萬，重放用 850,000）命中 4 個 session，**3 個當下有在飛代理**。首次越線列（`~/.claude/projects/D--CursorProject-AISDCL-Agent/<sid>.jsonl`，本棒當回合實跑）：`3d200496-a6dd-47e0-9921-b3904cf412ac` 第 3130 行（2026-11-08T16:57:09Z、ctx 853,361、在飛 1）；`76d1471c-0331-49e0-9d57-83b84d05d397` 第 4204 行（11-08T00:38:36Z、850,959、在飛 2）；`f1522ddb-bdcf-4104-bb81-614c1118fa9d` 第 2775 行（11-09T05:09:52Z、853,332、在飛 3）；另 `58ce5ccd-13fb-47fc-8a46-b04fa73257d7` 第 3548 行（11-10T09:57:29Z、851,844、在飛 0）。四個 session 越線後仍各續跑 1,445／1,815／9,158／3,132 行、均**無 `.sealed` 包**。
  2. **損害在現行機制下未證**：四件全在 11/8～11/10，**早於 R216 改制（11/18）**；當時硬線與封存閘尚未是現行形態，不能推論現行機制下「排空後主控沒換」。A4 的 12 件 `finalized_wake_block` 是另一件事（封存後被錯推），不是「該換沒換」的證據。
  3. **故本包定位＝預防性**：最小實作＝`watch` 的 `switch_due` 提示＋惰性 pending 標記＋`control_state` 欄＋statusLine 文字；**封存閘觸發條件不改、不新增任何推回**（§7.4）。若主控或再審認為此證據不足，W5 內此一小塊（`ensure_pending`、`switch_due`、`DISPOSAL` 一列、statusLine 一個字串）整體降為理論洞 TH-8，不影響 W5 其餘（決策表、`switch-plan`、量測）。升級觸發條件同 TH-1。
- **A4 與本節不同級**：A4（`finalized_wake_block`）有逐字稿座標加 12 件痕跡，是 P1；本節是預防性，不得借 A4 的證據。

**§7.6 重放的誠實限制（承上表）**：①重放以逐字稿＋`quota_burn` 近似判定點，未帶 `inflight` 的精確時序（以代理檔首末時間戳聯集近似）；②巡邏相位為理想化格點，真實哨兵相位另計（≤15 分誤差）；③帳號變動取自 `quota_burn` 指紋，同組織換使用者可能漏看；④未驗證的是「新演算法實際上線後的行為分佈」——重放只證明判準對歷史輸入給出可解釋的判定，不證明上線後換手品質。

---

## 8. park 等待期間額度提前恢復（裁12）

### 8.1 問題
`65389f03` 週額度 100% ⇒ `park --at` 到 11/24 19:03（73.2 小時）。掌舵者 11/22 換帳號後讀數已回 0%，但：主載具 keepwarm 對 `--at` 目標是單跳睡到目標（QW §2.2 S5）、不讀額度；QW S-19 的 `early_reset` 對 `primary_source=at` 明定不適用；park job 到 `backup_fire_at` 才跑一次。**沒有任何元件在等待期間重讀額度**。封存到接手 19.5 小時、靠人手貼上一輪輸出。

### 8.2 判準 `park.recovered(marker, state, policy, now)`
```
axes   = 非 FALLBACK、非 MODEL_SCOPED 的短窗軸 ∪ 週軸，pct 為有限數；讀數年齡 ≤ TTL＋POLL（QW S-23：陳舊先零 token 補量，補不到＝不判）
cur    = max(axes.pct)
recovered ⇔ marker.parked_pct 存在 ∧ cur ≤ parked_pct − EARLY_DROP_PP(5) ∧ cur < policy.prepare_pct
```
- **不另造第二套判準**：「低於準備門檻」就是 `park.stop_verdict` 要求 park 的同一把尺；「下降」沿 QW S-19／S-23 的單調性推理（同窗讀數不減 ⇒ 降＝換窗／換帳號）。QW 的 `early_reset(ref, …)` 管「短窗 reset 型目標」，本判準管「`--at`／週軸型與換帳號」，兩者資料來源與謂詞形狀不同、**不會對同一事件各給一個答案**——哨兵分支在判準前先查 `quotawall.early_reset` 適用則不重判（§8.3 步驟 4）。
- 基準欄（r2，D-CT-9）：`parked_pct`＝`_cmd_park` 登記當下 `max(axes.pct)`；`parked_account`＝登記當下 `quota_meter.account_key_of()` 的 `account_key`（量不到寫 `null`）。W6 單包同改 `park_cli._cmd_park`（寫）與 `parkprobe`／`controlfacts`（讀）；**欄名常數 `MK_PARKED_PCT`／`MK_PARKED_ACCOUNT` 住 `parkprobe.py`、不進 `qw_schema`**（理由見 D-CT-9；因此**無 N-3 計數同步、AT-QW-61 十一欄掃描不受影響**）。舊標記無 `parked_pct` ⇒ 不判（照原排程，出聲 `early_probe=absent(no_baseline)`）；舊標記無 `parked_account` ⇒ `account_changed=False`（不判換帳號，仍可因讀數下降提前）。
- `account_changed(marker, now_key)`＝`marker.parked_account` 與 `now_key` 皆非 `None` ∧ 不相等；`now_key` 取 `park._pace_state` 同一次讀數的快取 `account_key`（不另打端點）。

### 8.3 載具與流程（哨兵巡邏分支）
**座標（r2，P3-3；以工作樹現查為準）**：`park.yields` 住純函式 `session_resume_planner.sentinel_decide`（約 614 行）內，不在 `_sentinel_tick`；`_sentinel_tick`（約 1418 行）第一件事是 `sched_isolation.tick_gate(_REPO_ROOT, "_sentinel_tick", …)`（SE S2 半成品，非 `sandbox_scope.target_verdict`）。**探針插入點＝`_sentinel_tick` 內、`tick_gate` 通過之後、呼叫 `sentinel_decide` 之前**；`sentinel_decide` 與 `park.yields` 不動。次序：`tick_gate` → 探針 → `sentinel_decide`（內含 `park.yields` 讓路）→ QW §7.6 接手。W6 在 planner 內只加**一行**呼叫 `parkearly.tick(...)`（r3：入口住葉模組 `parkearly.py`，內部先呼叫 `parkprobe.evaluate` 取判決、成立時才 `fire_early`），判準全在 `parkprobe.py`、觸發本體全在 `parkearly.py`（§21）。`session_resume_planner.py` 在守衛面清單，暴露證據＝E8。
1. 前置：標記 `armed` ∧ 在 `valid_until` 內 ∧ 剩餘等待 ≥ `EARLY_MIN_WAIT_MIN(60)` ∧ 該包 live、未 `.ack`、未 `handed_over`（含 `spawning` 意圖）；`AUTOSDD_UNATTENDED`／模式非 auto ⇒ 不探；
2. SE L1 tick 判準先過（`sched_isolation.tick_gate`，已在 `_sentinel_tick` 入口通過；`refused` ⇒ `_sentinel_tick` 早已返回，探針不會被執行）；
3. 讀額度：`park._pace_state(now)`（既有；經 `quota_meter` 唯讀 GET、快取 TTL≥180 秒；巡邏相隔 15 分，遠大於 TTL）；落痕跡 `park_early_probe`（`reading`、`stale`、`parked_pct`、`recovered`）；量不到 ⇒ `reason=unmeasured`、不觸發、不報錯；
4. `recovered` ∧ `quotawall.early_reset` 不適用（或適用但主載具未醒）⇒ 走既有 `_cmd_fire` 路徑，`opts.early=True`：
   - §7.2 前置、`live_driver` 讓路、`handed_over`／`spawning` 去重**全部照 QW §7.2～§7.5**；
   - §7.3 分支 A（「主載具活著且未到 ⇒ 重排」）在 `early` 下**停用**（我們就是要早於它），B／C／D 照舊；
   - 選路：`park.fire_route(held, cold)`，`cold` 在 `account_changed` 時強制為真（D-CT-8）；大上下文自然判 FRESH 帶交接包；`prefer_fresh`（R2）照舊；
   - 活窗存在 ⇒ 依 QW §7.4 開 `--fork-session` 或 FRESH，**不關窗**；
   - 失敗鏈、`refused` 終局、哨兵接手（QW §7.5～§7.6）原樣；
5. 觸發成功寫 `park_early_recovered`（`saved_min`＝距原 `fire_at` 分鐘數、`account_changed`）；標記因 fire 而非 armed，其後巡邏略過；排程 job 照 QW 自拆。
- 為什麼不是新排程：QW §0.3 S-6／X-19 已規定 park 登記附帶武裝哨兵；哨兵是唯一定期醒來、不依賴 session 存活、零 token 的載具。
- 哨兵缺席（`AUTOSDD_SENTINEL_OFF`、拒絕武裝、macOS 以外平台不支援）⇒ park 末行與 `park --status` 照實印 `early_probe=absent(reason)`（雙憑證原則：只有一份就寫另一份缺席，QW §10）。

### 8.4 憑證
- 探針憑證＝哨兵排程的 NextRunTime（Windows `Get-ScheduledTask … NextRunTime`；macOS＝`launchctl list` rc）；探針實跡＝痕跡 `park_early_probe` 最後一列時間；`park --status` 加一列 `early_probe: next_probe=<NextRunTime> last=<ISO> reading=<pct> baseline=<parked_pct>`（SE X-22：兩稿各自加列、互不改對方列）。

### 8.5 重放與 PRD 紅線 1 豁免四條件
重放見 §7.6（`65389f03` 14:53、提前 52.2 小時、7 個負控無誤觸發）。四條件逐條：①唯讀 GET（`quota_meter` 既有）；②端點知識單一站點（`quota_meter.py`，本稿不新增第二個讀取點）；③TTL≥180 秒節流（巡邏 900 秒＋快取）；④失效降級出聲（`unmeasured` 痕跡與 `park --status` 列；SessionStart 簡報對「armed park 且探針連續 unmeasured」加一行）。

---

## 9. 交接包第 12／13 欄與接續資訊

### 9.1 第 12 欄「在飛／被切代理」（機械層，零 token）
`MECH_HEADINGS` **末尾追加**（不插入，既有欄號 1～11 不變，避免文件引用「第 7 欄」位移）。每列：
`id｜描述｜模型｜狀態（running／quiet／residue／cut／stopped）｜ctx｜任務書指標｜代理逐字稿路徑｜輸出落點｜最後 3 則 assistant 摘要｜建議處置`。
- 資料來源：`roster.snapshot(sid)`（狀態）＋ `agentbrief`（新：讀代理逐字稿；首筆 user 記錄＝原任務書；Write／Edit 的 `file_path`；末 3 則 assistant 文字；`cut_kind`）。
- 建議處置字面：`running`＝「排空後換（pending_switch）」；`cut`／`stopped`／`residue`＝「重派：新代理＋短任務書（原任務書見指標），不 SendMessage 續舊代理」。
- 與 `handoff._refusals`（有在飛代理拒絕 spawn）並存：排空或 TaskStop 之後 spawn；TaskStop 掉的代理其半成品現在有指標（ARC C.1 的缺口）。

### 9.2 第 13 欄「鏈上前幾棒」
- 鏈的走法：本 sid 為某包 P₁ 的接手者（`.ack` 記 `sid=<本 sid>`）⇒ P₁ 的擁有者 sid＝前一棒 Y₁；再找 Y₁ 為接手者的包 P₂……至多 `CHAIN_DEPTH＝5` 棒。**同一 sid 有多個包時（P3-5；例：`4a45bc75` 兩包）**：每一步取「`.ack` 內 `sid=` 等於當前 sid 者中，`.ack` 時刻**最早**的包」（＝該 sid 當初被誰接手的那個包；一個 sid 只會被接手一次，多包中其餘為該 sid 自己當擁有者時產生的包）；若同一 sid 有多個 `.ack` 指向它，取最早者並於欄內註「另有 N 個包同接手者」；找不到 ⇒ 鏈止於此（寫「鏈止於 <sid>：無包記錄其接手」）。真鏈已查證可走（QA：31ea79d4→4a45bc75→65389f03→814608d1，`.ack` 內含 `sid=`）。
- 每棒列：棒 sid、封存時刻、`<包 stem>.prompts.md` 路徑（**全文真人原話住該檔**，本欄只指路徑）、該棒最近 3 則真人提示前 200 字摘錄、該棒 scratchpad 的★檔（`RESTART_POINT`／`BRIEF`／`HB_`／`*_report.md`，沿 `handoff_build._scratchpad_text` 的辨識，對 Y₁～Y₅ 各跑一次，每棒至多 12 檔）。
- **大小上限（P3-4；常數住 `agentbrief.py`／`promptchain.py`，現查）**：真人提示摘錄每則 ≤ `PROMPT_EXCERPT_CHARS＝200` 字、至多 `LAST_PROMPTS＝3` 則／棒；assistant 摘要每則 ≤ `BRIEF_CHARS＝300` 字、至多 `LAST_TEXTS＝3` 則／代理；第 12 欄全欄 ≤ `COL12_MAX_CHARS＝12000` 字、第 13 欄全欄 ≤ `COL13_MAX_CHARS＝8000` 字，超出者從最舊列截斷並於欄末寫「已截斷 N 列」；**一律不含 `tool_result` 內容**（只取 `type=text` 的 assistant／user 文字區塊）。隱私面與既有 `.prompts.md`（本 session 全部真人提示全文，同一目錄、同一權限）同等級，不新增暴露面。
- 「是否已答」**不判**（做不到可靠）；主控層「待掌舵者決定」仍手寫。
- 這解決的實例：今天接手要翻 `4a45bc75…\RESTART_POINT.md` 與 `65389f03` scratchpad 兩跳，現在欄 13 直接列出。

### 9.3 SA 交接資訊十項逐項標記（裁13）
| # | SA 項 | 處置 | WHY／座標 |
|---|---|---|---|
| ① | git HEAD、髒檔表、`*-wip-preserved` 標籤 | **機械層已有**（欄 2～4） | `handoff_build.py:73-93` |
| ② | 在飛代理名冊（id／描述／模型／狀態／輸出落點／是否被切） | **機械層補**（欄 12，本稿） | §9.1 |
| ③ | 排程憑證清單（park／sentinel／watch／keepwarm 與 NextRunTime） | **機械層已有**（欄 8，前綴 AutoSDD_／AutoClaude*）；watch／keepwarm 是背景任務不是排程，其憑證在欄 12 的狀態與 `control:` 行 | `handoff_build.py:96-109` |
| ④ | 額度現況（短窗／週、reset、趕工戳記） | **機械層已有**（欄 9；快取可能陳舊 DEF-200-637，欄內標讀數年齡） | — |
| ⑤ | 本 session 全部真人提示全文 | **已有**（`.prompts.md`，欄 5 摘錄）；鏈上前幾棒＝欄 13 | `seal.render_prompts` |
| ⑥ | 進行中 SDD 鍵與 FSM 狀態；未結 OI id | **未結 OI id：機械層補**（欄 12 之後附一行，重用 `session_brief_oi` 的摘要函式，量不到寫量不到）；**SDD 鍵與 FSM 狀態：主控層手寫**（WHY：狀態住 `SDD_STATE_DIR`，多數 session 無此環境；有則「已驗證」第 1 行必列） | 重用而非重寫 |
| ⑦ | 活的 worktree／subst／容器／暫存待清理物 | **worktree 機械層補**（欄 3 加 `git worktree list` 一行）；**subst／容器：不做**（WHY：外部指令依賴 docker／subst、慢、與接續無關；清理慣例由任務書收尾條款承接，記憶 `cleanup-after-tests-convention`） | — |
| ⑧ | 模型與權限姿態、scratchpad 路徑 | **主控模型：機械層補**（欄 1 加「主控模型」＝逐字稿最後一筆 assistant 的 model）；**權限姿態：不做**（WHY：harness 層設定，逐字稿不載；新 session 自己看 statusLine）；scratchpad 路徑＝欄 10＋欄 13 | — |
| ⑨ | 本輪凍結授權與引用座標（approver 字串） | **主控層手寫**（WHY：語意判斷，非可蒐事實；錯抄＝偽造授權，機械蒐集比手寫風險更高） | — |
| ⑩ | 上輪任務書／TCS／E2E 覆蓋表路徑 | **前鏈★檔機械列出**（欄 13）；覆蓋表本身的路徑 **主控層手寫** | — |

### 9.4 `finalize` 仍只驗結構（裁9）
`handoff.REQUIRED`（前四節非空、無 `TODO:`）不變；不加「已驗證至少含一個 rc／Ran N 模式」之類內容檢查（無暴露證據、有誤判風險；機械驗證只會造出假通過）。內容品質靠主控層與 QA。REQ-CTL-21 為負向需求，E2E 以「已驗證寫（無）」仍通過 finalize 鎖定現行為不被誤改。

### 9.5 連動面（同 commit 收齊）
TCS-SessionCtl AT-SC-34「11 欄」→ 13 欄（逐欄斷言）、`handoff_build.MECH_HEADINGS`、`HANDOFF_CLOSING`／`handoff` 說明文字中的「機械層 11 欄」、CLAUDE.md〈換 session 的 SOP〉、ADR-XPLAT-004 §2.13.4 就地註記。

---

## 10. 量測（零 token、只讀、不接閘門；`tools/lib/wastecensus/sections_ctl.py` 新＋ `--replay-plan`）
| 指標 | 定義 | 目標 | 備註 |
|---|---|---|---|
| **M-W1（修正）** | 無看管區間：子代理在飛 ∧ 主控沒在動 ∧ 該區間內無**有效監督憑證**（payload `background_tasks` 或心跳或 `watchlock`；W2 後可得）；舊口徑（恆無憑證）的 575 筆／150.5 小時**只當上界**並行出數一期 | >30 分筆數＝0（SA REQ-A1） | 裁7 |
| **M-C1** | 封存後派工被冷叫醒推回（A4 回歸率）＝痕跡 `finalized_wake_block` 中，推回當下 `.sealed` 戳之後主控有非監督 `tool_use` 者 | **0** | 修前 14 天基線 12 件 |
| M-C2 | 接續完整度：M-S2 手貼接續比率（基線 9／37＝24%）；新 session 第一小時回頭讀舊資料次數（基線中位 2.5、非零 18／26） | ≤5%；中位 ≤1 | SA REQ-B3 |
| M-C3 | park 提前恢復：`park_early_recovered` 件數、`saved_min` 合計；`park_early_probe` 的 `unmeasured` 比率 | 觀察 | 裁12 |
| M-C4 | 換手判定分佈：痕跡 `switch_plan`（只記非 STAY 與每 session 首次 STAY 理由）按動作／原因計 | 觀察 | §7 |
| M-C5 | F′：冷回且 F4 判換新但未封存件數（基線 8／14 天） | 觀察（TH-5 升級條件） | §13 |
| M-C6（r2，SA A6 迴歸） | 無人窗口 session 中子代理被收尾／print 模式上限終止件數（讀既有逐字稿 `<status>killed</status>` 與 `AUTOSDD_UNATTENDED` 窗口記錄；判準在 `sections_ctl.py`） | **0**（觀察口徑，不接閘門） | REQ-CTL-48；既有 DEF-200-575 迴歸鎖 |
| 新痕跡事件 | `switch_advise`（`advise_once` 每次出聲）、`switch_plan`、`pending_switch_set`／`_due`／`_cleared`、`watch_duplicate`、`park_early_probe`、`park_early_recovered`、`control_cold_wake_exempt`（冷叫醒閘因 `ineffective／supervised` 放行時記一筆，使 M-C1 有分母） | — | 與 QW §13 事件名無衝突 |

---

## 11. 與 R216／QuotaWall／R218-B 的介面對照表（逐列；不得與 QW §12 與 SE §10.2.1 衝突）
| # | 介面字面 | 值／語意 | 本稿座標 | 對方座標 | 衝突檢查 |
|---|---|---|---|---|---|
| I-1 | `seal.wake_package` 簽章 | 增 `transcript=None`；無此參數的呼叫＝`handed_over` 分支同舊、封存分支回 `None`（**既有斷言須補傳逐字稿夾具，§4.1 遷移條款**） | §4.1 | QW Q1 改 `seal._spawned`（認 `spawning` 意圖，不同函式） | 檔同、函式不同；W1 在 Q1 之後 commit |
| I-2 | 跨包欄名（AT-QW-61 的十一個） | W1～W5 **不新增**其中任何一個字面；W6 新增的 `parked_pct`／`parked_account` 常數住 `parkprobe.py`、**不進 `qw_schema`、不屬跨包欄名**（單包兩端、Q3 之後） | §0.3 D-CT-9、§8.2 | QW §12 本節判準；S-12 | 無；r2 已刪 N-3（不需 QW 附錄同步計數） |
| I-3 | `converge.py` 改動範圍 | W1 只動 `_finalized_wake` 與其呼叫的 `wake_package` 傳參；QW Q4 之後在其上改 `_park_stop` 分派與 S-18 閂鎖 | §4.1 | QW §12 Q4 | W1 先、Q4 後（裁6） |
| I-4 | `watch.py`／`keepwarm.py` | W2 只在 `watch.run` 入口加鎖呼叫並改心跳鍵；Q2 重做 `run` | §5 | QW §12 Q2 | **W2 排 Q2 之後** |
| I-5 | `holder.py` | 本稿不碰（單例鎖另檔 `watchlock.py`，重用 `holder.is_live`／`start_token` 為只讀呼叫） | §5 | QW Q1 增欄 | 無 |
| I-6 | 保溫帳「真工作」文法 | `control.is_supervision_call`（單一家）；QW `keepwarm.work_mark` import | §3.3、§17 N-1 | QW S-24② | 語意一致（QW 文法是本文法的子集——QW 未含 `handoff／park／quotawall／switch-plan／runlong／waitfor` 動詞；N-1 要求 QW 以本函式為準） |
| I-7 | 冷叫醒閘 keepwarm 豁免 | 擴為 keepwarm＋watch 兩者（`control.is_supervision_shell`） | §4.2 | QW D-J／§8、QW S-13 `handed_over` 重判 | QW 的 `mark_resumed` 觸發點不受影響；`handed_over` 判準不改 |
| I-8 | 哨兵 `_sentinel_tick` 分支 | 在 `sentinel_decide`（內含 `park.yields` 讓路）呼叫**前**插提前恢復探針（一行呼叫 `parkearly.tick`，r3；判決由 `parkprobe.evaluate` 產生）；`sched_isolation.tick_gate` 更前；QW §7.6 的 `failed` 接手分支位置不變 | §8.3 | SE §3.4 tick 列、QW §7.6 | 次序：`tick_gate` → 本稿探針 → `sentinel_decide`／讓路 → QW 接手；W6 在 Q3／SE S3 之後 |
| I-9 | park 標記 | 增 `parked_pct`、`parked_account`（常數住 `parkprobe.py`）；`primary_source=at` 仍使 QW S-19 不適用 | §8.2 | QW S-19、§7.1 | 本判準不複用 `early_reset`，二者不對同事件各答一次（§8.3 步驟 4） |
| I-10 | `_cmd_fire(early)` | `opts.early=True` 僅停用 §7.3 分支 A 的重排；其餘黃金序列不變 | §8.3 | SE X-7／X-8／X-18、QW §7.0～§7.5 | `early=False`（所有現行路徑）逐字不變；黃金序列 AT 在 W6 增 `early` 版本，不改舊版 |
| I-11 | `handoff_build.MECH_HEADINGS` | 末尾追加第 12、13 欄；欄 1／3 各加一行內容 | §9 | SE S7 對該檔 import `PKG_REPO_LABEL` 一行 | 序列：W4 先、S7 後或同收尾 commit |
| I-12 | `sandbox_scope.SLUG_FRAGMENT` | `rosterscope` 與 `controlfacts` 只 import 常數 | §6.1 | SE §3.2 | 無；`sandbox_scope.SITES` 不增列（本稿無新 spawn／register 站點） |
| I-13 | `tools/sessionctl.py` | `status` 加 `--all-projects`、`control:` 行；`switch-plan` 新動詞 | §6.3、§7 | SE S2（`apply_job_env` 最先）、QW Q4（`quotawall` 動詞、status 兩列） | 同檔不同段；W3 在 SE S2 之後、不與 Q4 並行 |
| I-14 | 痕跡檔 | 沿 `autosdd_session_switch.jsonl`；新事件名見 §10 | §10 | QW §13 | 無重名 |
| I-15 | 硬線／R2／F4／keepwarm 常數 | **全部引用**（`switch.threshold`、`costmodel`、`keepwarm`），本稿新增常數只有 `DEBOUNCE_MIN`、`DRAIN_MAX_MIN`（`switchplan`）、`EARLY_MIN_WAIT_MIN`、`EARLY_DROP_PP`、`MK_PARKED_PCT`、`MK_PARKED_ACCOUNT`（`parkprobe`）、`CHAIN_DEPTH`、`PROMPT_EXCERPT_CHARS`、`LAST_PROMPTS`、`COL13_MAX_CHARS`（`promptchain`）、`BRIEF_CHARS`、`LAST_TEXTS`、`COL12_MAX_CHARS`（`agentbrief`）；皆非換窗門檻 | §7～§9 | SS／ADR §2.19 | 無新換窗門檻 |
| I-16（r2） | `park_cli.cancel_marker`（自 `_cmd_cancel` 抽出） | 公開函式，行為同現行 `park --cancel`（標記 `cancelled`、拆備援排程）；新增唯一呼叫者 `ackhook.on_ack` | §0.3 D-CT-12、§20.2 | SE S2（`park_cli.py` 正在改）、QW Q3；SE SITES（`register`／`disarm` 類站點由既有 `_disarm_verified` 承擔，不新增站點） | `_cmd_cancel` 既有 AT 逐字不變；W4b 在 S2、Q3 之後 |

**衝突檢查結論**：與 QW §12、SE §10.2.1 X-1～X-22 逐列比對，無字面或語意衝突；唯一需他稿同步的是計數與 import 方向（§17）。

---

## 12. 被否決的方案
| 方案 | 否決理由 | 反向鎖 |
|---|---|---|
| 在冷叫醒閘補「若封存後有派工就放行」 | 壓制：各消費端仍各自記「封存」的含義，下一個消費端再補一次 | MU-CTL-01、AT-CTL-04 |
| 禁止封存後派工 | 與「先封存、再做自主工作、最後 spawn」的既有流程（`seal.py:335-336` 封存閘文字）矛盾；封存是對「當時」的交代，同 `mark_resumed` 的理由 | MU-CTL-02 |
| 軟線／便宜線／「階段邊界上下文大就換」（SA OQ-5、REQ 附帶建議） | 掌舵者 2026-11-18「專注在不要讓 Cache 過期」、R1 退役、SS §11 否決軟線與 hold——**不得復活**；換窗是為了快取成本，不是為了大 | MU-CTL-14（演算法不含任何新 ctx 門檻） |
| hook（SessionStart／Stop／排程）代主控機械 finalize＋spawn（方案 C） | hook 沒有 LLM、寫不了主控層；包內容未驗證即交棒；與 park／keepwarm／forward 三載具再多一條；**無暴露證據**（14 天沒有一次「到硬線卻沒封存」） | TH-1 升級條件；MU-CTL-15 |
| 被切代理自動重派（SA OQ-2 的「由 runner 重派」） | 避免重複燒額度；重派需要判斷（原任務書是否還對、半成品是否可用）；裁10 | AT-CTL-55、E2E-CTL-12 |
| watch 後到者取代先到者 | 先到者的完成通知會多叫醒主控一次；先到者贏最省 | AT-CTL-20、21、MU-CTL-10 |
| 用絕對讀數判 park 提前恢復 | `park --why` 可在未達門檻時登記，絕對值判準一輪巡邏就誤觸發 | MU-CTL-30 |
| 在 park job 內輪詢額度 | job 一次性、到 `backup_fire_at` 才跑；改為常駐會變成第三種載具 | — |
| 新增獨立排程做提前恢復探針 | 哨兵已是定期、零 token、不依賴 session 的載具（X-19 登記即武裝） | — |
| 交接包插入新欄於第 8 欄之後 | 欄號位移使既有文件引用（「機械層第 7 欄」）失真；末尾追加 | MU-CTL-22 |
| finalize 加內容檢查 | 無暴露證據、誤判風險；機械驗證只會造假通過（裁9） | REQ-CTL-21、E2E-CTL-21 |
| 用 `claude -r` 後在飛代理自動接回的假設 | harness 行為**未驗證**；本稿不依賴 | TH-6 |

---

## 13. 理論洞清單（依〈守衛面准入〉只登記、不擴守衛；每項附升級觸發條件）
| 代號 | 洞 | 為何不補 | 升級觸發（出現即立案，附 sid＋痕跡座標） |
|---|---|---|---|
| **TH-1** | hook 代主控 finalize／spawn（ARC 方案 C）：到硬線仍未封存且主控閒置 | 14 天零次「到硬線卻沒封存」 | 14 天內出現「`ctx ≥ 硬線` 或 `pending_switch` 逾 60 分仍未封存，且之後主控閒置 ≥ 30 分」的真痕跡 ≥ 1 次 |
| TH-2 | A1／A2：Stop 監督閘只推一次、推回後仍不掛 watch | M-W1 恆無憑證＝量不出；先修量測（M-W1 改讀真憑證） | M-W1 修正版 14 天內 >30 分無看管區間 ≥ 1 筆（附 sid） |
| TH-3 | A5／A6／A13：經 `.ack`／forward 路的真交棒不經 `_refusals`；已交棒舊視窗在硬線以下派 Agent；quiet 代理被當不在飛 | 無實例 | 任一 session 在 `.ack`／spawn 痕跡之後出現 Agent／Task 派工記錄（附逐字稿行號）；或 spawn 前置通過卻有 quiet 代理後續被判殘局 |
| TH-4 | 帳號變更後 live 窗口續跑付 2N 重寫（D-CT-8 只改 `cold` 輸入、不新增推回） | 近 14 天 4 次帳號變動，其中 3 次的 live 窗口重寫帳**未驗證**（本棒未查），故無暴露證據 | `account_key` 變動後 5 分鐘內的主控回合出現 `cache_creation ≥ F4 門檻` 的重寫，且 sid 未封存，≥ 1 件 |
| TH-5 | F′：冷回大上下文（`2N > F(1+q)`）且未封存 ⇒ 無載具（8／14 天） | 修法只有「大就換」（已否決）或預防冷（保溫，M-K1／M-K2 持有）；轉送需封存包，hook 寫不了主控層 | M-K1＋M-K2 超標與 M-C5 同窗成立；或同一 sid 冷回重寫 ≥ 2 次 |
| TH-6 | `claude -r` 續跑後在飛代理能否被主控接回（harness 行為）；猝死路（無主控層，由機械層＋逐字稿尾端重建）端到端可用性 | 未驗證、無可用探針（需真 harness 跨行程）；本稿不依賴 | 掌舵者或任一窗口回報「續跑後代理消失／被重複派」附 sid |
| TH-8（有條件；§7.7） | 預防性的 `pending_switch`／`switch_due` 小塊（硬線∧在飛代理：情境真實命中 3、損害在現行機制下未證，且四件皆早於 R216） | 主控裁決 2 代決保留；若再審或主控認定證據不足則整塊降為本列、W5 其餘不受影響 | 同 TH-1：14 天內出現「硬線越線後有在飛代理、代理交卷後首個 Stop 仍未封存、且主控閒置 ≥ 30 分」的真痕跡 ≥ 1 次（附 sid＋行號） |
| TH-7 | 提前恢復在 `refused` 沙盒目標、macOS 睡眠、哨兵缺席下的行為 | 前兩者已由 SE L1 與 QW S-14 覆蓋；後者照實印 `absent(reason)` | `early_probe=absent` 的 armed park 實際撞上額度恢復而無人接手（M-K9 同款） |

---

## 14. DEF 草稿（編號由收尾包現查缺陷帳本最大號＋1 配發；現查最大＝DEF-200-637；QW Q7、SE S7 亦預留 DEF，序位依收尾順序）
| 草稿 | 嚴重度 | 摘要 | 根因 | 修法／落點 |
|---|---|---|---|---|
| D-CTL-1 | **P1** | 冷叫醒閘對「已封存、未交棒、封存後仍派工」要求 TaskStop 在飛代理與其 watch（A4；E1） | 封存有效期只有封存閘認得；兩閘各答一次 | W1：`control.sealed_effective` 單一謂詞；`wake_package` 吃 transcript；D-CT-1～3 |
| D-CTL-2 | P3 | 兩支 watch 並存、共用心跳檔被先結束者刪（A3；E2） | 心跳以 sid 為鍵、無單例 | W2：`watchlock`＋心跳 pid 化 |
| D-CTL-3 | P2（觀察面） | 沙盒真 `claude` 子代理記錄混進全域名冊（A12；E3）；使用者看不到誰在掌控（A14） | `roster._agent_dirs` 掃全部專案 slug；無單一可見處 | W3：`rosterscope`、`status` 一行、SessionStart、statusLine |
| D-CTL-4 | P2 | 交接包不含在飛／被切代理與鏈上前幾棒原話，約 24% 接續靠人手貼（E5、E7） | 機械層 11 欄無此資訊 | W4：欄 12／13、`agentbrief`、`promptchain` |
| D-CTL-5 | P2 | park 等待期間額度提前恢復（含換帳號）無人發現，73 小時預定、實際人手開窗（E8、E9） | 無元件在等待期間重讀額度；QW S-19 對 `--at` 明定不適用 | W6：`parkprobe`、哨兵分支、`park.recovered` |
| D-CTL-7 | P3 | handoff `--ack` 後原 session 的 armed park 標記與備援排程仍在（11/22 靠人手 `park --cancel --session-id`）；`_cmd_fire` 已對 `.ack` skip，雙駕駛風險已擋、殘留的是「等待中」假象與讓路（SA REQ-B4） | ack 不通知 park | W4b：`ackhook.on_ack`、`park_cli.cancel_marker` |
| D-CTL-6 | P3（量測） | M-W1 恆無憑證；`advise_once` 無痕跡 | 憑證判準未接；出聲不落事件 | W5：M-W1 修正、`switch_advise`、M-C1～M-C5 |

---

## 15. 工作包切分（鐵律七：鎖的持有面）與全局排序

### 15.1 工作包表（W0 為本稿與 TCS；W8 為收尾）
「鎖」＝每包列出其動到的鎖（常數／史料／消費端）各住哪些檔；三者不在同一持有面者不得並行派給不同包。

| WP | 內容 | 動到的檔（常數／史料／消費端） | 前置 | 並行 |
|---|---|---|---|---|
| W0 | DES＋TCS＋PRD v2.1.26（本棒）；QA 規格審查；主控依常態規則凍結 | `docs/02_architecture/Control_Handover_Design.md`、`docs/03_testing/contracts/TCS-Control-20261122.md`、PRD | ARC＋SA | 單人 |
| **W1** | A4：`control.py`（葉）；`seal.effective`／`wake_package(transcript)`；`transcript_activity.worked_since(ignore=)`；`converge._finalized_wake` 傳參；封存閘改吃謂詞 | **常數**：`control.py`（`SUPERVISION_TOOLS`、動詞正則）、`transcript_activity.READ_ONLY_TOOLS`（不動）；**史料**：`seal.py`（`.sealed` 格式不變）、`test_sessionctl_seal.py`、`test_sessionctl_converge.py`；**消費端**：`converge.py`、`seal.stop_verdict`、新 `test_sessionctl_control.py` | **QW Q1 commit**（`seal._spawned`）；與 SE S2／S3／S5 檔不相交；**W1 的 `control.py` 常數是 QW Q2 `keepwarm.work_mark` 的上游**（r2：W1 commit 先於 Q2 派工；N-1 在 Q2 派工前套用） | 與 SE S2／S3／S5、QW Q5 並行；**QW Q2 排在 W1 之後（循序）**；LOC 風險：`transcript_activity.py`（453 行實測、分級現查）只加 `ignore` 參數 |
| **W2** | `watchlock.py`；`watch.run` 入口鎖；心跳 pid 化；`supervise.read_heartbeat` 任一新鮮 | **常數**：`watchlock.py`、`watch.py` 的 `heartbeat_path`；**史料**：舊 `<sid>.json` 心跳（相容讀一輪）；**消費端**：`supervise.py`、`controlfacts`（W3 才有）、`test_sessionctl_{watch,hooks}.py` | **QW Q2 commit**（Q2 重做 `watch.run`／`keepwarm.py`） | 與 Q3、Q5、W3 並行 |
| **W3** | `rosterscope.py`；`roster` 2 行；`status --all-projects`＋`control:` 行；`controlfacts.py`；`control.status_line`；SessionStart 殘局／被切公告；statusLine 區段 | **常數**：`rosterscope.py`（import `sandbox_scope.SLUG_FRAGMENT`）；**史料**：`status` 輸出格式（`test_sessionctl_roster.py`、`test_sessionctl_hooks.py`）、`statusline_context_feed` 既有輸出（`test_context_window_parity.py` 不動）；**消費端**：`tools/sessionctl.py`（旗標段）、`tools/lib/session_brief.py`（守衛面）、`tools/statusline_context_feed.py` | W1（`control`）；QW Q1（`qw_schema` 讀取函式）；**SE S2 commit**（同改 `tools/sessionctl.py`） | 與 W2、Q2、Q5 並行；**不與 Q4 並行**（同檔 `tools/sessionctl.py`）；LOC 風險：`tools/lib/session_brief.py` 397／400——殘局公告邏輯一律放新模組 `sessionctl/briefline.py`，`session_brief.py` 只加 ≤2 行呼叫（§21） |
| **W4** | `agentbrief.py`；`promptchain.py`；`handoff_build` 第 12／13 欄與欄 1／3 加行；`rosterscope.cut_kind`；`roster.stop_message` 被切出聲；TCS-SessionCtl AT-SC-34 改 13 欄 | **常數**：`handoff_build.MECH_HEADINGS`（欄序單一家）；**史料**：`TCS-SessionCtl-20261113.md` AT-SC-34、既有包 `.md` 格式（不遷移，舊包無第 12／13 欄＝讀取端容忍）；**消費端**：`handoff.ensure_mechanical`（不改）、`roster.py`（`stop_message` 末加）、`test_sessionctl_handoff.py` | W1（seal.py 同檔序列）、W3（`rosterscope`） | 單人（序列於 SE S7 對 `handoff_build` 一行之前或同收尾） |
| **W5** | `switchplan.py`（`decide`、`ensure_pending`／`read_pending`、`on_advise`）；`controlfacts` 擴；`advise_once` 只加 1 行痕跡呼叫；`watch` `switch_due`＋逾時處置字尾；**封存閘觸發條件不改**（僅讀 `sealed_effective` 四值）；量測 `sections_ctl.py`＋`--replay-plan`＋M-W1 修正；`sessionctl switch-plan` 動詞 | **常數**：`switchplan.py`（`DEBOUNCE_MIN`、`DRAIN_MAX_MIN`）；**史料**：`pending` 檔、`autosdd_session_switch.jsonl` 事件名；**消費端**：`handoff.py`（`advise_once`）、`watch.py`、`seal.py`、`wastecensus/*`、`tools/sessionctl.py`、`tools/probe/waste_census.py` | W1、W2、W4、**W4b**（`tools/sessionctl.py` 同檔）；**SE S2、QW Q2、Q3 commit**（`handoff.py`／`watch.py`／`sessionctl.py` 同檔） | 單人；LOC 風險：`handoff.py` 394／400——`advise_once` 只加 1 行呼叫 `switchplan.on_advise`（寫 `switch_advise` 痕跡），`ensure_pending` 不經該檔（D-CT-11）；`watch.py`、`seal.py` 各只加 ≤2 行（§21） |
| **W4b**（r2 新） | ack 後撤原 session 的 park 標記（D-CT-12）：`ackhook.py`；`park_cli.cancel_marker`（自 `_cmd_cancel` 抽出的公開函式）；`tools/sessionctl.py` 的 `handoff --ack` 分支加 1 行呼叫 | **常數**：`ackhook.py`；**史料**：park 標記 `status` 值域（`park.STATUSES` 不動）、`_cmd_cancel` 既有行為與 AT（`test_sessionctl_park*.py`）；**消費端**：`park_cli.py`、`tools/sessionctl.py`、`handoff.py`（只讀 `.ack`，不改） | **SE S2 commit**（`park_cli.py`／`sessionctl.py` 同檔，S2 正在實作）、**QW Q3 commit**（`park*.py`）、W4（同為 handoff 接續流程，序列即可） | 單人；與 W6 同持有面（`park_cli.py`）⇒ **W4b 先、W6 後，不並行** |
| **W6** | park 提前到點：`parkprobe.py`（判準、`baseline`、`status_row`）；`parkearly.py`（r3 新：`tick`、`fire_early`）；`park.recovered`；`park_cli`（只留呼叫，合計 ≤4 行：`_cmd_park` 寫 `parked_pct`／`parked_account` 1 行、`--status` 加列 1 行、`_cmd_fire(early)` ≤2 行）；`session_resume_planner._sentinel_tick` 一行呼叫 `parkearly.tick`；SessionStart 一行（經 `briefline.py`） | **常數**：`parkprobe.py`（`EARLY_*`、`MK_PARKED_PCT`、`MK_PARKED_ACCOUNT`；**不進 `qw_schema`**，D-CT-9）；**史料**：park 標記格式（舊標記無此二欄＝不判／不判換帳號；`marker_problem` 不拒未知欄、`_settle` 保留未知欄）、黃金序列 AT（SE X-18）；**消費端**：`park.py`、`park_cli.py`、`session_resume_planner.py`、`test_sessionctl_{park,park_route}.py`、`test_context_budget_guard.py`（SentinelDecision） | **QW Q3 commit**、SE S2／S3 commit、**W4b commit**（同持有面 `park_cli.py`） | 單人（`park_cli`／planner 持有面）；LOC 風險：planner 745／750——只加 1 行呼叫 `parkearly.tick`；`park_cli.py` 393／400（餘 7）——新邏輯進 `parkprobe.py`／`parkearly.py`，`park_cli` 合計 ≤4 行；W4b 與 W6 都改 `park_cli`，W4b 先 W6 後（r3；與 SE S2／QW Q3 同檔，動工前現查餘額，§21） |
| **W7** | E2E 家族 `control`（TCS §4 全部）＋`cases.json` 加列 | **常數**：`cases.json`（共用單一持有面）；**消費端**：`tools/lib/realverify/cases/control.py` | W1～W6（含 W4b）；**SE S6、QW Q6 commit** | 單人 |
| **W8** | 收尾：棘輪重釘（新測試檔）、`Root_Layout` §3、ADR-XPLAT-004 新節、根 CLAUDE.md 守衛總表／換 session SOP、DEF 立案與結案、PRD §16.6 〔OI〕回填、QW／SE 追加註記（§17）、E2E 全跑入帳 | 收尾面 | W1～W7 | 單人（與 SE S7、QW Q7 同一收尾窗口，序 S7→Q7→W8 或合併一次重釘） |

### 15.2 W2 與 QW Q2 的二擇一（裁6 明訂）
**決定：W2 排在 Q2 之後（獨立包），不併入 Q2。** 理由：①Q2 已含 keepwarm 全部、watch §5.7／§6.5、`work_mark`、`handed_over` 重判，是 QW 最大的一包，再併 W2 會使單人包過大且測試面混雜；②鎖入口必須包在 Q2 定型的 `watch.run` 之上，併入沒有收益、只有 rebase 風險；③代價＝A3 在 Q2 完成前仍在（P3：新 harness 的憑證走 payload、不受影響；只影響舊路徑與人眼 `status`），可接受。W2 對 `watch.run` 只加 4～6 行呼叫與心跳鍵，Q2 之後的 commit 上直接加。

### 15.3 全局排序（含 QW Q1～Q7、SE S1～S7）
```
已完成：SE S1（447c49cd）、SE S5 部分（927bc1d8）
進行中：SE S2 半成品（工作樹，tag r218b-s2-20261121-wip-preserved）

階段 0：W0（本稿＋QA 審查＋凍結）
階段 1（可並行，檔不相交）：SE S2 ∥ SE S3 ∥ SE S5 ∥ QW Q1 ∥ QW Q5
階段 2：W1（Q1 之後；不碰 handoff.py／park*.py／planner，故可與 SE S2 同時）。**W1 先、QW Q2 後（循序，r2）**：Q2 的 `keepwarm.work_mark` import W1 的 `control.is_supervision_call`，常數（W1）與消費端（Q2）不得並行派給兩包
階段 3（並行）：QW Q2（W1 之後）∥ W3（W3 前置 SE S2＋W1＋Q1）；SE S6（S2／S3／S5 後）
階段 4：W2（Q2 後）∥ QW Q3（SE S2／S3 後）
階段 5：W4（W1、W3 後）；QW Q4（Q2、Q3 後；不與 W3 並行）
階段 5b：W4b（W4、SE S2、Q3 後；與 W6、W5 同持有面 ⇒ 序列 W4b → W5／W6）
階段 6：W5（W1、W2、W4、W4b、S2、Q2、Q3 後）；W6（Q3、W4b 後）
階段 7：QW Q6（Q2～Q5、S6 後；cases.json 單人）→ W7（S6、Q6 後；cases.json 單人）
階段 8：SE S7 → QW Q7 → W8（收尾單人；或合併一次棘輪重釘）
```
不可並行對（同持有面）：W1×Q1（seal.py）；**W1×Q2（`control.py` 常數 ↔ `keepwarm.work_mark` 消費端，r2 補）**；W2×Q2（watch.py）；W4b×{W6,S2,Q3}（park_cli.py）；W4b×{W3,W5}（tools/sessionctl.py）；W3×Q4（tools/sessionctl.py）；W3×SE S2（同）；W5×{S2,Q3}（handoff.py）；W6×{S2,S3,Q3}（park_cli／planner）；W7×{S6,Q6}（cases.json）；W4×SE S7（handoff_build 一行）。QW §12 與 SE §10.1 的原排序不變，本稿只在 Q1／Q4 前後插入。

---

## 16. 模組落點表（照 `Root_Layout_and_Module_Placement.md` §2）
| 元件 | 路徑 | §2 格 |
|---|---|---|
| 控制態葉模組（謂詞＋純合成） | `tools/lib/sessionctl/control.py` | 函式庫（sessionctl 既有套件新葉模組） |
| 控制態事實讀取器 | `tools/lib/sessionctl/controlfacts.py` | 同上 |
| watch 單例鎖 | `tools/lib/sessionctl/watchlock.py` | 同上 |
| 名冊範圍與被切判準 | `tools/lib/sessionctl/rosterscope.py` | 同上（roster LOC 貼天花板） |
| 代理摘要（第 12 欄來源） | `tools/lib/sessionctl/agentbrief.py` | 同上 |
| 鏈上前幾棒（第 13 欄來源） | `tools/lib/sessionctl/promptchain.py` | 同上 |
| 換手演算法（純函式＋pending 讀寫） | `tools/lib/sessionctl/switchplan.py` | 同上 |
| park 提前到點判準（`evaluate`、基準欄常數、`baseline`、`status_row`；r3 純判準葉，不 import `park_cli`／`parkearly`） | `tools/lib/sessionctl/parkprobe.py` | 同上 |
| park 提前到點 early 入口與觸發本體（r3 新：`tick`、`fire_early`；import `parkprobe` 與 `park_cli`，單向） | `tools/lib/sessionctl/parkearly.py` | 同上 |
| SessionStart 殘局／被切／unmeasured 公告行（r2：拆出，不進 `session_brief.py`） | `tools/lib/sessionctl/briefline.py` | 同上 |
| ack 後撤 park 標記（r2 新） | `tools/lib/sessionctl/ackhook.py` | 同上 |
| 量測 | `tools/lib/wastecensus/sections_ctl.py`；旗標 `tools/probe/waste_census.py --replay-plan`（M-C1～M-C5 併入 `--supervision-metrics`／`--switch-metrics`） | 函式庫（wastecensus）／量測探針 |
| 指令入口 | `tools/sessionctl.py`：`status --all-projects`、新動詞 `switch-plan`（薄殼，無判準） | 指令入口薄殼 |
| statusLine 區段 | `tools/statusline_context_feed.py`（既有檔，加一行呼叫） | 既有工具 |
| 測試 | 新 `tools/tests/test_sessionctl_control.py`、`test_sessionctl_switchplan.py`、`test_sessionctl_parkprobe.py`、`test_sessionctl_agentbrief.py`、`test_waste_census_ctl.py`、`test_sessionctl_ackhook.py`（r2 新，共 6 個新測試檔）；其餘擴充既有檔 | 測試 |
| E2E | `tools/lib/realverify/cases/control.py`；結果帳 `docs/06_quality/RealVerify_Result_Ledger.md`；登記 `docs/06_quality/RealVerify_Protocol/cases.json` | realverify 既有套件 |
| 規格 | 本稿；`docs/03_testing/contracts/TCS-Control-20261122.md` | 需求／設計、測試契約 |
| 痕跡／狀態 | `trace_dir()/switch/<sid>.pending`、`trace_dir()/watch/<sid>.lock`、`trace_dir()/watch/<sid>.<pid>.json`、`trace_dir()/control/<sid>.seg`；`autosdd_session_switch.jsonl` 新事件 | repo 外執行期痕跡 |
| CI | sessionctl／wastecensus／hooks／planner 既有 compat-ci `paths` 已涵蓋，**不新增**；`tools/statusline_context_feed.py` 現查是否已在 `paths`，未在則 W8 同 commit 加 | CI 接線 |
| 守衛面登記 | `tools/lib/sessionctl/**`（已在清單）、`tools/lib/transcript_activity.py`、`tools/session_resume_planner.py`、`tools/lib/session_brief.py` 皆已在〈守衛面准入〉清單；**不新增守衛面成員**；`.claude/**` 本稿零改動 | — |

---

## 17. 需他稿追加註記（本稿不改兩份凍結稿；收尾包套用）
| # | 目標 | 追加內容 |
|---|---|---|
| N-1 | QW S-24②／`keepwarm.work_mark` | 「監督」判準改為 import `control.is_supervision_call`（單一家，Control DES §3.3），不另寫指令文法；QW 文法是其子集。**套用時機（r2）：QW Q2 派工前必套（不是收尾包才套）**；W1 commit 先於 Q2（§15.3 階段 2→3，循序） |
| N-2 | QW §12 本節判準、AT-QW-61 | 註記「W1 先於或同 Q1 後 commit，W1 不新增十一欄任何字面；`seal.py` 的 W1 改動（`wake_package`、`stop_verdict`）與 Q1 的 `_spawned` 在不同函式」 |
| N-3（r2 刪除） | — | r1 要求 AT-QW-61 計數改十二；r2 把 `parked_pct`／`parked_account` 常數改住 `parkprobe.py`、不進 `qw_schema`（D-CT-9），不屬跨包欄名，**無需任何 QW 註記**。編號保留以免 N-4～N-10 位移 |
| N-4 | QW §7.3 分支 A | 註記「哨兵提前恢復（Control §8）以 `opts.early=True` 停用分支 A 的重排；其餘分支不變」 |
| N-5 | QW §13 痕跡表 | 加 `park_early_probe`、`park_early_recovered` |
| N-6 | SE §10.2.1 | 加 X-23：`_cmd_fire(early)` 與哨兵探針分支；L1 tick 判準先於探針（本稿 I-8）；`sandbox_scope.SITES` 不增列 |
| N-7 | TCS-SessionCtl AT-SC-34 | 11 欄 → 13 欄（W4 同 commit） |
| N-8 | ADR-XPLAT-004 | 新節（編號收尾包現查）；§2.13.4（交接包 11 欄）、§2.18（監督閘）、§2.19（封存閘 `worked_since`）就地註記指向本稿 |
| N-9 | 根 CLAUDE.md | 〈機械守衛總表〉sessionctl_guard 列：冷叫醒閘敘述改為「已交棒，或封存有效（`control.sealed_effective`）且有非監督／未受監督的背景任務」；〈換 session 的 SOP〉加「待換（pending_switch）／switch_due」與「提前恢復探針」兩句；速查表加 `sessionctl switch-plan`、`status --all-projects` |
| N-10 | `Root_Layout` §3 sessionctl 列 | 加 10 個新模組（`control`、`controlfacts`、`watchlock`、`rosterscope`、`agentbrief`、`promptchain`、`switchplan`、`parkprobe`、`parkearly`、`briefline`、`ackhook`）與 6 個新測試檔（r2：由 8／5 增為 10／6；r3：新模組 `parkearly` 使模組數增為 11，測試檔仍 6，`parkearly` 由 `test_sessionctl_parkprobe.py` 同檔涵蓋） |

---

## 18. 修復不留後遺症三問
1. **另一台機器／另一個人身上會不會回來？** A4 的成因（封存有效期各閘各記）被單一謂詞消除；AT-CTL-04 原始碼掃描鎖「`sessionctl/` 內除 `control.py` 外不得直接呼叫 `worked_since(`」，E2E-CTL-01 以**同一份真逐字稿**（65389f03 第 2221～2335、2468～2519 行）重放，別台機器重現不了舊行為。判準不含任何機器常數（硬線、F4、TTL 皆現查）。
2. **有沒有文件、座標、凍結 digest、設定因此不一致？** 連動面（§9.5、§15、§16、§17）同 commit 收齊：TCS-SessionCtl AT-SC-34、`MECH_HEADINGS`、ADR 新節、PRD v2.1.26＋§16.6、CLAUDE.md 兩列、Root_Layout、`_TREE_FILE_FLOORS`／棘輪重釘（W8）、CI paths 現查。QW／SE 兩份凍結稿零改動，註記集中 §17。
3. **有沒有留下「之後再看」？** 理論洞逐條登記 §13（TH-1～TH-8）並各附**可機械偵測的升級觸發條件**；未驗證項（`claude -r` 後代理接回、猝死路、statusLine 互動畫面顯示、真互動窗目視）明列於 TCS §4 末與 §13 TH-6，不寫成「已通過」。

---

## 19. PRD v2.1 追溯與修憲（§16.5 (i)；已追加進 PRD，既有每一行位元組不變）
| 新需求 | PRD 座標 | 修憲動作 |
|---|---|---|
| CI-1 控制權、CI-2 可見 | §1.2 原則 1（控制面／執行面）後加【v2.1.26 註記】；§4.4.3、§4.5.7 延伸 | 修訂表 v2.1.26＋註記 |
| A4 封存有效期單一謂詞 | §4.3 交棒路線（line 1030 附近）、§16.6 2026-11-18 列的後續；§15.5 紅線建議新增「閘與閘不得互相矛盾」（本稿**不追加紅線**，只在 §16.6 列「依據」寫入，紅線增修留掌舵者 T1） | §16.6 新列 |
| 自動換手演算法、pending_switch | §4.5.4 同版註記延伸 | §16.6 新列 |
| 在飛／被切代理與鏈上原話入交接包 | §4.5.4、§11.3 | §16.6 新列 |
| park 提前到點（含換帳號） | §4.5.11 末加【v2.1.26 註記】 | 同上 |
| E2E 家族 `control` | §11.1～§11.9 | 結案格自帶 |

**「只增不改」的機械鎖（r2；QA P2-8）**：釘**修憲前 blob**，不釘 `git diff`（提交後 `git diff -U0` 對 HEAD 為空，鎖會失效）。
- 常數：`PRD_PRE_AMENDMENT_BLOB＝5af6ce952d701284642f199d19dd3daea58beca7`（即 `git rev-parse HEAD:docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 於 v2.1.26 追加**之前**的值；本棒當回合實查＝`5af6ce952d701284642f199d19dd3daea58beca7`）。住 `test_sessionctl_control.py`（W0／W8 的 AT-CTL-75 同檔）。blob 物件在歷史中永遠可取（`git cat-file -p <blob>`），提交前後皆有效。
- 判準（**行級子序列，寫死**）：`git cat-file -p <PRD_PRE_AMENDMENT_BLOB>` 的每一行（以 `\n` 切、UTF-8 解碼、逐字相等、不 strip）依序出現在工作樹 PRD 檔的行序列中（雙指標：舊檔行 i 只能與新檔中不早於前一個匹配位置的行相等）；新檔多出的行只能是整行新增。**不選字元級**：「既有行位元組不變」的要求本來就以行為單位，行內插字（字元級才放行）正是要禁止的修改；也**不選純 `git diff`**（提交後失效）。
- 後續修憲（v2.1.27 以後）同樣不破壞本鎖：只在尾端或表格中整行新增；若日後要改既有行須走 §16.5 並同 commit 更新本常數（該 commit 本身即修憲紀錄）。
- 失效偵測：blob 取不到（淺 clone 缺歷史）⇒ 測試以 `unittest` 的 **FAIL**（不 skip）報「缺 blob，請 `git fetch --unshallow`」，因為「判不了」不得當作通過。CI checkout 深度由 W8 現查（`fetch-depth: 0` 或含該 blob）。

---

## 20. SA 需求去處表（r2 新；QA P2-5）
逐項對 SA 報告 REQ-A1～A6／B1～B6。「去處」只有四種：**實作 WP**／**迴歸**（既有條文已涵蓋、本稿只加鎖）／**理論洞**（TH，附觸發）／**不做＋WHY**。

### 20.1 對照表
| SA REQ | SA 原判準（摘要） | 去處 | 本稿對應與目標值（誠實改寫） |
|---|---|---|---|
| A1 在飛代理必有看管者（P1；M-W1 >30 分筆數＝0） | 無看管區間 >30 分＝0 | **實作 WP（量測先行）＋理論洞** | 量測：W5 修 M-W1 讀真憑證（REQ-CTL-39）；守衛：**不改**（A1／A2 無暴露證據顯示推回後仍不掛，M-W1 恆無憑證＝量測盲，TH-2）。**目標值改寫**：「>30 分筆數＝0」由 SA 的 P1 目標降為 **M-W1 修正版出數後再定**——現行 watch 單例（W2）與可見（W3）已降低發生面，但 575 筆／150.5 小時是上界、真值未知，不先釘數字；TH-2 觸發＝修正版 14 天內 >30 分 ≥1 筆（附 sid）即立案修 A1。**不做**的部分＝「現在就把 0 當驗收」（WHY：量測口徑恆無憑證，釘 0 會逼出無證據的守衛擴張，違反〈守衛面准入〉） |
| A2 被切代理清單（P1；漏列＝0） | 8 支被切樣本漏列 0 | **實作 WP W4** | `rosterscope.cut_kind`＋第 12 欄＋三處出聲（REQ-CTL-19／20；E2E-CTL-12 以 8 支真形狀驗漏列 0） |
| A3 封存／冷叫醒同判準（P1） | 兩閘結論一致 | **實作 WP W1** | `control.sealed_effective` 單一謂詞（REQ-CTL-01～04、07；E2E-CTL-01 真逐字稿重放） |
| A4 沙盒代理不入名冊（P2） | 預設 `status` 殘局＝0 | **實作 WP W3** | `rosterscope`（REQ-CTL-11～13；E2E-CTL-06） |
| A5 一眼看到誰在掌控（P2） | `status`／簡報 5 欄 | **實作 WP W3** | `control:` 行、SessionStart、statusLine（REQ-CTL-14～16；畫面顯示＝〔OI〕V-CTL1） |
| A6 無人窗口不被整批殺（P1；迴歸） | 無人窗口子代理被收尾殺掉＝0 | **迴歸（已涵蓋，本稿加量測鎖）** | 既有 DEF-200-575／ADR §2.12（`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` 與牆鐘同源）。**本稿不新增守衛**；REQ-CTL-48（新）要求：①W7 的 E2E 一律不在無人窗口依賴 watch（A11）；②`waste_census` 新增一欄 M-C6「無人窗口 session 中子代理被 `status=killed`／收尾終止件數」讀既有逐字稿（目標 0；觀察口徑，不接閘門）。既有 realverify 家族已有 DEF-200-575 案（SD 現查 `cases.json` 對帳，W7 不重造） |
| B1 該換的自動換（P1；機械觸發 ≥80%） | 機械觸發比例 ≥80% | **實作 WP W5（演算法）＋不做（目標值）** | 演算法寫成可重放決策表（§7；REQ-CTL-22、42）。**目標值改寫**：「機械觸發 ≥80%」**不做**——WHY：①本稿主控裁決 3 明定 hook 不代主控 finalize／spawn（TH-1），換手最後一步（寫主控層、finalize、spawn）仍由主控完成，「機械觸發」在此架構下的真實含義只能是「機械**提醒**＋機械載具（封存閘、watch、轉送、park）就位」；②實務上換手由「主控照提示做」完成，比例取決於主控而非演算法，釘 80% 會誘使擴張到 hook 代理。**改寫為**：M-K6 觸發源欄（W5 補，REQ-CTL-41 M-C4）觀察「提示後 N 分內完成 finalize 的比例」，TH-1 觸發條件已寫死 |
| B2 換手延遲 ≤2 分（P1） | finalize→ack 中位 ≤2 分、P90 ≤10 分 | **不做＋WHY（目標值）；其餘實作** | WHY：finalize→ack 的主要延遲是「人是否在窗前」（基線 P90 374.5 分、最大 1,173.6 分＝換帳號後人手開窗），而 `--spawn` 一旦被呼叫是秒級；與 TH-1（hook 不代 spawn）直接衝突，故中位 ≤2 分**不作驗收**。本稿能縮短的兩段已做：①park 等待期提前到點（W6，省 52.2 小時下界）；②接手後 `.ack` 前舊 park 自動撤（W4b）。**改寫目標**：M-C2 觀察 finalize→ack 分佈（不設門檻） |
| B3 只憑交接包就能接手（P1；手貼 ≤5%） | M-S2 ≤5%（基線 9／37） | **實作 WP W4** | 第 12／13 欄、`prompts.md` 鏈、未結 OI（REQ-CTL-17、18）；M-C2 量測（基線 24%）；目標 ≤5% 保留為 PRD 再開症狀（§16.6 列） |
| B4 手動換窗新窗被告知＋舊 park 自動撤（P2） | 簡報含未接手包；park 被撤 | **實作 WP W4b（撤 park）＋既有（公告）** | 公告＝既有 SessionStart `handoff.announce`；**撤 park＝W4b `ackhook`（REQ-CTL-47）**，查證與修法見 §20.2 |
| B5 不遺漏在飛代理（P1） | 包含名冊欄、缺列＝0 | **實作 WP W4** | 第 12 欄（REQ-CTL-17；E2E-CTL-10／12／22） |
| B6 防抖與不該換清單（P2） | 30 分內連換＝0 | **實作 WP W5** | `DEBOUNCE_MIN`、決策表 G／D 列（REQ-CTL-26；重放 0 命中） |

### 20.2 B4 查證：「ack 後自動撤原 session 的 park」
- **查證（本棒當回合讀 `tools/lib/sessionctl/park_cli.py::_cmd_fire`，行 372～）**：到點 job 的第一批判斷依序為 ①標記非 `armed` 或 job 非本標記所屬 ⇒ `skip("cancelled"／"not_armed")`；②`UNATTENDED` ⇒ refused；③**`pkg.with_suffix(".ack").exists()` ⇒ `skip("acked")`（行 397～398）**；④包非 live ⇒ `skip("expired")`；⑤`live_driver` ⇒ skip；⑥`_duplicate_refusals` ⇒ `skip("spawned")`；之後才選路（RESUME／FRESH）。結論：**RESUME 路已對 acked 包 skip**，11/24 到點時 `claude -r` 舊 sid 造成雙駕駛的風險**已被擋住**（r1 任務書的擔憂不成立，不需為此新增守衛）。
- **仍存在的殘留（今天實例）**：ack（11/22 15:16）到預定到點（11/24 19:03）之間，標記仍 `armed`、備援排程仍在：①`park.yields` 使該 sid 的哨兵讓路；②`control:`／`park --status` 顯示「等待中」假象；③備援排程殘留到點才自拆（SE 的 EndBoundary 雙保險兜底，但仍是 50 多小時的殘留）；④主控得手動 `park --cancel --session-id`（11/22 實例）。
- **修法（D-CT-12、W4b、REQ-CTL-47）**：`handoff --ack` 成功後呼叫 `ackhook.on_ack(pkg, acker_sid, env)`：解析包擁有者 sid（沿 `handoff` 既有包檔名／`.md` 擁有者欄，不另寫解析）；擁有者 ≠ acker 且有 `armed` park 標記 ⇒ `park_cli.cancel_marker(owner_sid, event="acked")`（標記 `cancelled`、拆備援排程；`_cmd_cancel` 核心抽出的公開函式，不新增排程站點）；擁有者＝acker（自續跑，`.resumed` 路）⇒ 不撤。冪等（無標記／已非 armed ⇒ 無動作、rc 0）。
- **E2E（E2E-CTL-24，新）**：沙盒 park（備援排程以 SE 租約前綴）→ 別 sid `handoff --ack` → 斷言 ①標記 `cancelled`（`event=acked`）②備援排程 0 殘留（`Get-ScheduledTask` 查無）③到點 job 若被強制觸發見 `skip("cancelled")`④對照組（自續跑 ack）標記不撤。MU-CTL-43：`on_ack` 對擁有者＝acker 也撤 ⇒ AT-CTL-85 紅。

---

## 21. 行數牆處置：逐包拆檔方案（r2 新；QA P2-7）
**基準（本棒當回合 `python AutoClaude/tools/check_loc_budget.py --json` 與 QA 實測；口徑＝該工具，非 `wc -l`）**：`tools/lib/session_brief.py` 397／400（餘 3）、`tools/session_resume_planner.py` 745／750（餘 5）、`tools/lib/sessionctl/handoff.py` 394／400（餘 6）；`sentinel_lifecycle.py` 399／400（餘 1）；**r3 更正與補列**：`roster.py` 現查 **375**／400（餘 25，r2 誤寫 399 為照抄任務書口徑）、`park_cli.py` 現查 **393**／400（餘 **7**，r2 漏列）。**原則（D-CT-13）：邏輯一律放新模組，既有檔只加 ≤2 行呼叫；動工前 `check_loc_budget.py --json` 現查餘額，不得「超線再說」。**
| 檔（餘額） | 會碰到它的包 | 拆出方案（新模組名、落點、職責） | 既有檔增量 |
|---|---|---|---|
| `tools/lib/session_brief.py`（397／400） | W3（殘局／被切公告）、W6（armed park 探針連續 unmeasured 一行） | 新 `tools/lib/sessionctl/briefline.py`：`orphan_line(repo_slug, env)`（殘局／被切，沿 `rosterscope`）、`park_probe_line(env)`（unmeasured 連續 3 次）、`join(lines)`；只回字串或空字串 | `session_brief.py` 只加 **1 行** `from … import briefline`（頂層）與 **1 行**在簡報組裝處附加 `briefline.lines(env)` 結果；W3 與 W6 都只改 `briefline.py`，**不再碰 `session_brief.py`**（W6 的一行也走 `briefline`） |
| `tools/session_resume_planner.py`（745／750） | W6（`_sentinel_tick` 探針）；R218-B S2 已在該檔動（半成品，餘額以現查為準） | **兩個新葉模組（r3，N-2）**：`parkprobe.evaluate(args, now, S) -> dict \| None`（純判準：讀標記、前置判斷、`_pace_state`、`recovered`、落痕跡；不 import `park_cli`／`parkearly`）；`parkearly.tick(args, now, S) -> dict \| None`（early 入口：呼叫 `parkprobe.evaluate`，判決成立才呼叫 `parkearly.fire_early(sid, now, env)`；後者以 `park_cli._cmd_fire` 既有核心對已判定的標記走「提前」路徑）；回 `None`＝無事、續走 `sentinel_decide` | planner 只加 **1 行** `if (r := parkearly.tick(...)) is not None: return r`（含 `# noqa` 註記同 S2 風格）＋頂層 import 若尚未有（W6 動工前現查，若餘額＜2 則先由 W6 派工前包把 planner 內某一已存在的純函式搬到 `sessionctl/` 騰出空間，**不放寬 `SPECIAL_FILES` 天花板**） |
| `tools/lib/sessionctl/handoff.py`（394／400） | W5（`advise_once` 痕跡）；W4b（只讀 `.ack`，不改） | 新 `switchplan.on_advise(sid, reason, ctx, k, mode)`（寫 `switch_advise` 痕跡）；`ensure_pending` 不經該檔（D-CT-11） | `advise_once` 只加 **1 行**呼叫 `switchplan.on_advise`；`handoff.py` 頂層 import 1 行；合計 ≤2 行 |
| `tools/lib/sessionctl/park_cli.py`（**393／400，餘 7**；r3 補列，N-1） | W4b（抽 `cancel_marker`）、W6（`_cmd_park` 寫兩欄、`_cmd_fire` early、`--status` 增列）；SE S2、QW Q3 已／將在同檔動（半成品，餘額以現查為準） | **early 觸發本體進 `parkearly.py`**（`tick`／`fire_early`），**`--status` 增列文字與兩欄基準值組裝進 `parkprobe.py`**（`parkprobe.baseline(axes, account_key) -> dict`、`parkprobe.status_row(marker, env) -> str`）；`park_cli` 只留呼叫：`_cmd_park` 1 行（`marker.update(parkprobe.baseline(…))`）、`--status` 1 行（`parkprobe.status_row`）、`_cmd_fire` early 路徑的 `opts.early` 判斷合計 ≤2 行；W4b 的 `cancel_marker` 抽出為**搬移淨 0 行**、`ackhook` 只呼叫它 | W6 合計 **≤4 行**（頂層 `from . import parkprobe` 1 行含在內）、W4b **淨 0**；W4b 先、W6 後，兩包合計 ≤4 ＜ 餘 7；**SE S2／QW Q3 若先消耗餘額，W6 動工前現查，餘額＜增量時先把 `park_cli` 內一個既有純函式搬進 `parkearly`／`parkprobe` 騰出空間（淨減），不放寬 `LOC_TIERS`** |
| `tools/lib/sessionctl/roster.py`（**375／400**，r3 更正） | W3（`_agent_dirs` 改呼叫範圍）、W4（`stop_message` 末加被切清單） | `rosterscope.scope_dirs` 取代 `_agent_dirs` 內的掃描（**淨減行**：舊掃描樣式 6～8 行搬走）；被切清單 `agentbrief.render_cut` 由 `stop_message` 一行呼叫 | W3 淨 −5 左右、W4 +1；W3 先於 W4（已在序）；若 W3 後餘額仍＜2，W4 在 `stop_message` 之外另掛 hook 側呼叫（`sessionctl_guard` 組訊息處，`.claude/` 不動，經 `converge` 合成而非 `roster`） |
| `tools/lib/sentinel_lifecycle.py`（399／400） | **本稿不碰** | — | 0 |
| `tools/lib/sessionctl/watch.py`、`seal.py`、`converge.py`、`supervise.py`、`park.py`（`park_cli.py` 見上列，r3 單獨成列） | W1（seal、converge）、W2（watch、supervise）、W5（watch、seal）、W6（park） | 判準全在新葉模組（`control`、`watchlock`、`switchplan`、`parkprobe`、`parkearly`、`ackhook`）；既有檔只加呼叫與參數傳遞，每檔每包 ≤6 行；W4b 把 `_cmd_cancel` 核心抽成 `cancel_marker` 是**搬移（淨 0 行）**不是新增 | 各包交卷附 `check_loc_budget.py --json` 輸出（rc 0、無 tier／special 違規）；AT-CTL-81 事後驗 |
| `tools/lib/transcript_activity.py`（守衛面） | W1 | 只加 `ignore` 參數（≤4 行）；`READ_ONLY_TOOLS` 不動 | ≤4 |
**驗收**：各包交卷必附當回合 `check_loc_budget.py --json` 輸出（`tier_violations`／`special_violations`／`root_tools_violations` 皆空）；AT-CTL-81 保留為事後鎖。**不得**以調高 `SPECIAL_FILES`／`LOC_TIERS` 解壓（TCS 共通紀律：不放寬任何門檻或棘輪）。

---

## 22. r2 對 QA 規格審查發現的處置表（P2×8、P3×7）
| # | QA 發現 | 處置 | 座標 |
|---|---|---|---|
| P2-1 | `sealed_effective` 的 `None` 混淆「從未封存」與「未知」 | **採納（主控裁決 1）**：改四值，逐消費端四值行為寫表；AT-CTL-05 拆為 05a／05b（新增 AT-CTL-83）；MU-CTL-04／05 改寫＋新增 MU-CTL-43（`none` 視為 `unreadable` 必紅，使從未封存的 ctx≥硬線 session 不再被推回）；現行 `worked_since` 對讀不到回 False 由 `control._readable` 先驗 | §3.2、§4.1、D-CT-1；REQ-CTL-01；AT-CTL-05／83／84 |
| P2-2 | R2 與 pending 自相矛盾、`.advised` 閂鎖吃掉硬線 pending | **採納（主控裁決 2）**：pending 只認硬線；刪「R2 pending」；作廢改 `ctx<hard`（無 `hard/2`）；寫入改 `ensure_pending` 惰性冪等、不經 `advise_once`；封存閘觸發條件不改（R2 零新增推回）；AT 補「先 R2 出聲、後到硬線仍寫 pending」 | D-CT-5／6／7／11、§7.3、§7.4；REQ-CTL-23；AT-CTL-43／50／86 |
| P2-3 | `pending_switch` 缺暴露證據、「現行靜默」措辭不符程式 | **採納（主控裁決 3）**：更正措辭為「PreToolUse 在硬線擋新派工＋代理交卷後首個 Stop 由封存閘推回」（`converge.py:53-70`、`seal.stop_verdict`）；暴露證據改引真逐字稿四件（sid＋行號，§7.7）與 A4 的 12 件（另一級）；載明「主控裁決 2 代決」；經重查：**情境成立、損害未證、四件早於 R216**，故定位預防性、最小實作、並登 TH-8（可整塊降級） | §0.1、§0.2、§7.6、§7.7、§13 TH-8 |
| P2-4 | `account_changed` 基準值無存放處 | **採納（主控裁決 4）**：park 標記新欄 `parked_account`（`account_key`）與 `parked_pct` 同寫；欄名常數住 `parkprobe.py`、不進 `qw_schema`（WHY 見 D-CT-9）；選 `account_key` 而非 `plan_fingerprint`（桶名集合，R90 實測 29% 碰撞）；任一側 `None` ⇒ `False`；REQ-CTL-27／34 改寫到可實作；刪 N-3 | D-CT-8／9、§7.1、§8.2；REQ-CTL-27／34；AT-CTL-62／87 |
| P2-5 | 缺 SA REQ-A／B 逐項去處表 | **採納（主控裁決 5）**：§20 十二列；B4 以 `_cmd_fire` 實查：RESUME 路對 acked 已 skip（行 397），雙駕駛風險已擋、殘留為「等待中」假象，修為 W4b `ackhook`＋E2E-CTL-24；A1／B1／B2 目標值誠實改寫為「量測先行」「不做＋WHY」；A6 列迴歸＋REQ-CTL-48 | §20；REQ-CTL-47／48；E2E-CTL-24 |
| P2-6 | W1 並行欄含 Q2、與 N-1 自相矛盾 | **採納（主控裁決 6）**：W1 先、Q2 後（循序）；W1 並行欄刪 Q2；前置欄寫「W1 commit 先於 Q2」；N-1 改為 Q2 派工前必套；§15.3 圖與表一致；不可並行對補 W1×Q2 | §15.1、§15.3、§17 N-1 |
| P2-7 | 行數牆未在工作包處理 | **採納（主控裁決 7）**：§21 逐檔逐包拆檔方案（新增 `briefline.py`、`ackhook.py`；`parkprobe.tick`、`switchplan.on_advise`）；各包 LOC 風險欄；驗收＝交卷附 `check_loc_budget` 輸出 | §21、§15.1 LOC 風險欄、D-CT-13；AT-CTL-81 |
| P2-8 | PRD 只增不改的鎖在提交後失效 | **採納（主控裁決 8）**：釘修憲前 blob `5af6ce95…`；判準＝行級子序列（寫死，WHY 見 §19）；AT-CTL-75、E2E-CTL-21、MU-CTL-39 三處同改；blob 取不到＝FAIL 不 skip | §19 末；REQ-CTL-44；AT-CTL-75；E2E-CTL-21；MU-CTL-39 |
| P3-1 | `wake_package` 預設語意破壞既有測試 | **採納**：列遷移條款（補傳逐字稿夾具、不放寬斷言、不改預設為舊行為）；W1 交卷附遷移清單 | §4.1；AT-CTL-15 |
| P3-2 | E2E-CTL-01 戳時刻來源（2235／2492 無時戳；`.sealed` 已被覆寫） | **採納**：改取第 2221 行（2026-11-21T09:52:54Z）與第 2468 行（11:19:31Z）所在記錄的時戳＋1 秒；於 E2E-CTL-01 與 §1.2 E1 註明 | §1.2 E1；TCS E2E-CTL-01 |
| P3-3 | 哨兵分支座標寫法 | **採納**：`park.yields` 住 `sentinel_decide`（約 614 行）；探針插在 `_sentinel_tick`（約 1418 行）內、`sched_isolation.tick_gate`（約 1422 行）之後、`sentinel_decide` 之前；I-8、§7.5、§8.3、AT-CTL-59 同改 | §8.3、§11 I-8、§7.5 |
| P3-4 | 第 12／13 欄大小上限 | **採納**：每則字數、列數、全欄上限常數；不含 `tool_result`；隱私面與 `.prompts.md` 同級 | §9.2 |
| P3-5 | 同 sid 多包鏈走法 | **採納**：每步取 `.ack` 內 `sid=` 為當前 sid 者中最早 `.ack` 時刻的包；多指向註記；找不到即止 | §9.2；AT-CTL-34 |
| P3-6 | 「提前 52.2 小時」是下界 | **採納**：標「≥52.2 小時（下界）」並寫明 `quota_burn` 11/21 19:16～11/22 14:45 無讀數 | §0.1 第 4 點、§7.6 |
| P3-7 | TaskStop 筆數未驗 | **採納**：改「已逐筆驗證者僅 2698／2700 兩筆，其餘以實查為準」 | §1.2 E1 |
**不修的項目**：無（8＋7 全採納）。**採納但有保留者**：P2-3 保留主控裁決 2 的代決（不否決），只改措辭、補證據與降級路徑；P2-5 的 B1／B2 目標值不採 SA 原數字（WHY 在 §20.1）。

### 22.1 r3 對 QA 窄範圍複審新發現的處置表（P2×2、P3×3；報告 `w3_specqa2_report.md`）
| # | QA 發現 | 處置 | 座標 |
|---|---|---|---|
| N-1（P2） | `park_cli.py` 行數牆漏列（現查 393／400）、`roster.py` 現值誤寫（實 375） | **採納**：§21 補 `park_cli.py` 獨立列（餘 7）；early 觸發本體進新葉模組 `parkearly.py`，`--status` 增列文字與兩欄基準值組裝進 `parkprobe.py`（`status_row`、`baseline`），`park_cli` 只留呼叫（W6 合計 ≤4 行、W4b 淨 0）；`roster.py` 更正為 375；W4b 先、W6 後與 SE S2／QW Q3 同檔的關係在 §15 W4b／W6 列與 §21 一致；餘額＜增量時先搬純函式騰空間，不放寬 `LOC_TIERS` | §21、§15.1 W6 列、§15.3、N-10；AT-CTL-90 |
| N-2（P2） | `parkprobe` 不 import `park_cli` 卻要呼叫未定義的 `park_cli.fire_early`（循環／矛盾） | **採納**：early 入口放獨立葉模組 `parkearly.py`，公開函式 `parkearly.tick(args, now, S)`、`parkearly.fire_early(sid, now, env)`；`parkprobe.evaluate` 為純判準；import 方向＝`planner → parkearly → {parkprobe, park_cli}`、`park_cli → parkprobe`，`parkprobe` 不 import 另二者；D-CT-9、§8.3、I-8、§21、TCS AT-CTL-58／59 字面一致；模組數 10→11 | D-CT-9、§8.3、§11 I-8、§21、N-10；AT-CTL-58／59／90 |
| P3-n1 | §7.2 H 列與 §7.4「非 `effective`」含 `unreadable`，與 §3.2 矛盾 | **採納**：兩處改「`none` 或 `invalidated`」；TCS REQ-CTL-25 同改 | §7.2 H、§7.4；REQ-CTL-25 |
| P3-n2 | TCS §7 第 5 項「TH-1～TH-7」漏 TH-8；REQ-CTL-48 無真機 E2E 未登明 | **採納**：改 TH-1～TH-8（TCS §7 第 5 項、DES §18 第 3 問）；REQ-CTL-48 無真機 E2E 的劃界保留（改以 `waste_census` 真跑量測，TCS §6 表第 48 列已標示，覆蓋表一致），並在 TCS §7 明載 | TCS §6、§7；DES §18 |
| P3-n3 | `ensure_pending` 呼叫點含「封存閘 Stop」恆不成立且違反 §3.1 | **採納**：刪此呼叫點，餘 watch 輪詢、`control_state`／`switch-plan`；AT-CTL-86 同改 | D-CT-11、§7.4；AT-CTL-86 |


## 23. 實作對照註記（2026-11-23 收尾；只增註記，既有條文不改）

> 依 W4／W4b 實作落地後的實況補註；上列條文（§16、§0.3、§21、附錄）逐字保留，以本節為對照。

1. **`cut_kind` 的實作位置**：§16 與 TCS AT-CTL-32 寫的 `rosterscope.cut_kind`，實作落在 `tools/lib/sessionctl/agentbrief.py::cut_kind`（`rosterscope` 只負責名冊限本專案的掃描範圍）。以下列為準：`agentbrief.cut_kind(agent_path, *, killed, agent_id, ...)`。
2. **新常數 `agentbrief.STOPPED_RECENT_SECONDS`＝24 小時**（`24 * 3600`）：主逐字稿記著被 TaskStop、近 24 小時內有動、且名冊不再列的代理才算「近期被停」（`stopped`）；超過者不出聲。本常數與 `cut_kind` 同檔，屬 W4 新增，原設計未載。
3. **`cutvoice.py` 的掛點**：三處出聲各只呼叫一個 `cutvoice` 函式——Stop `roster.stop_message` 呼叫 `cutvoice.stop_text`、`watch` 判決處置字尾呼叫 `cutvoice.watch_text`、SessionStart `briefline` 呼叫 `cutvoice.brief_text`；`agentbrief.render_cut` 只被 `cutvoice` 使用（REQ-CTL-20；判準全在葉模組）。
4. **`ackhook` 的掛點在入口層**：`tools/sessionctl.py` 的 `handoff` 分支呼叫 `ackhook.after_handoff(rest, handoff.cli(rest))`，`--ack` 成功才進 `ackhook.on_ack`（REQ-CTL-47）；`handoff.py` 本身不 import `ackhook`，維持行數牆（§21）。
5. **提前到點改以子行程觸發（W6，2026-11-24；取代 §8.3 步驟 4、§11 I-10、TCS AT-CTL-61 的「行程內 `_cmd_fire(early=True)`」寫法）**：`session_resume_planner.py` 對 `--sentinel-tick` 無條件設 `AUTOSDD_UNATTENDED=1`，而 `park_fire`、`handoff.spawn`、`spawn_resume` 在該旗標下一律拒絕開窗；照原寫法行程內呼叫，真行程 smoke 實證 spawn 0 次。實作改為 `parkearly.fire_early` 以**與 park 排程相同的 argv** 起乾淨環境的 `park --fire` 子行程（仍走 Q3 同一條 fire 路，不新增 spawn 站點）；early 與「強制視為快取已冷」改由環境變數 `AUTOSDD_PARK_EARLY`／`AUTOSDD_PARK_FORCE_COLD` 傳遞（常數住 `park.py`），不用 opts。`_precheck` 不再以 `UNATTENDED` 擋（哨兵 tick 內恆為真）。**不採**「放寬 planner 對哨兵 tick 強制 `UNATTENDED`」的替代案：那是守衛面，且無暴露證據（R197 守衛面准入）。AT-CTL-61 的判準語意（early 僅停用 §7.3 分支 A 的重排、`early=False` 黃金序列逐字不變）不變，只是觸發載具由函式參數改為子行程環境變數；機械物＝`tools/tests/test_sessionctl_parkprobe.py`＋真行程 smoke（反例 3＋正例 1，`SMOKE_VERDICT=pass n=25`）。
6. **哨兵任務書檔名要去 `PLAN_PREFIX` 才是 park 標記的 sid 鍵**：任務書檔名＝`autosdd_resume_plan_<sid>.md`、park 標記以裸 sid 為鍵。W6 探針與既有 QW §7.6 的 `on_patrol(plan.stem, …)` 都改為去前綴後的裸 sid——後者原本在真行程永遠讀不到標記（Q3 單元測試以裸 sid 當檔名，未能抓到）；缺陷登記 DEF-200-646。
7. **W5 實作對照（2026-11-25；主控裁示：以下偏離全數採納，原條文不改）**：①新增葉模組 `switchfacts.py`（事實讀取）——不拆會成 `handoff→switchplan→seal→handoff`、`watch→controlfacts→supervise→watch` 兩個 import 環；Root_Layout §3 模組數 +1 於 W8 收尾同步。②`handoff.advise_once` 呼叫 `switchplan.advise_hook`（由命中文字解析 reason／ctx／K）再轉 `on_advise`，`on_advise` 簽名同 §15。③`switch_due` 不經 `watch.decide`／ORDER，走 `watch_wake.due_merge`＋`switchplan.merge`（守 `watch.py` 行數牆）；它只勝過「無事」與保溫族，其餘判決不變。④`park.fire_route` 增 `prefer_fresh` 參數（AT-CTL-44：見 R2 的 `prefer_fresh` 即走 FRESH），`park_cli` 淨 +1 行。⑤`control_cold_wake_exempt` 只在「封存失效而放行」落痕跡，「監督 shell 放行」不落（避免每次 Stop 洗版）。⑥量測口徑：M-C1 歷史封存時刻取逐字稿內 `handoff --finalize` 呼叫時刻（`.sealed` 會被覆寫）；M-W1 歷史憑證只取「看管中」出聲與現存心跳檔；重放的近似項印在 `--replay-plan` 輸出末行。⑦真 `claude -p`（E2E-CTL-14）、換帳號替身與 `cases.json` 登記屬 W7；W5 以 `switch-plan` 對真逐字稿截斷複本的真行程為備援證據。主控親驗（主樹 998b8804）：ruff 0、LOC rc 0、sessionctl* 1020、waste* 123、context_budget_guard 871、c1c2 187、platform_neutral 177、doc_loc_r60 286、defect_crossref 276 皆 OK。
---

## 24. WP-SW 增修：換帳號接手全自動化與子代理掌控訊息（r4；2026-11-28；只增不改，§0～§23 逐字不變）

> 🔒 本節是凍結稿**之後**的增修，上游＝PRD 修訂表 v2.1.30、§16.6 2026-11-28 列；驗收＝`TCS-Control-20261122.md` §8（REQ-CTL-49～59）。角色＝SD（WP-SW）。輸入＝Architect＋SA 報告 ARCH-Q34（sid 4290bf58 scratchpad `q34_arch_report.md`）與主控裁示八條。本節**不改** §0～§23 任一行；§13 理論洞清單 TH-1～TH-8 不變，新增 TH-A～D 的處置見 §24.11。
> 與其他工作包**不重疊**（鎖持有面，鐵律七）：WP-FENCE＝柵欄與 `unacked_pkg` 類（`sid-1_20261125T223155Z.md` 那件）、WP-HOOK＝G9 假推回（`.claude/hooks/**`）、CLOSE＝缺陷帳本結案；本節**零改動 `.claude/**`、零改動缺陷帳本、零動排程**，持有面全在 `tools/`：`_stdio_utf8.py`、`session_resume_planner.py`（只增呼叫行）、`tools/lib/sessionctl/**`、`tools/lib/wastecensus/supervision.py`、`tools/probe/sentinel_decide_replay.py`。與 WP-HOOK 不同檔、可並行（REQ-CTL-55 只改 `agentbrief.py`／`cutvoice.py` 的文字）。

### 24.0 決策總表

| 決策 | 問題（證據） | 決定 | 判準／實作住哪 | REQ |
|---|---|---|---|---|
| D-SW-1 | G-1：pythonw `sys.stderr is None`，`acctswitch.py:229` 的 `.write` 拋 `AttributeError`，哨兵 tick 無聲死亡（`LastTaskResult=1`、`NextRunTime` 空白） | 消除成因：stdio SSOT 對 `None` 串流改綁 `os.devnull`；**不改** `acctswitch.py` 一行（那是壓制） | `tools/_stdio_utf8.py::reconfigure_stdio_utf8`（SSOT，被 hook 與全部入口匯入） | 49 |
| D-SW-2 | G-1 另一面：本次死因只能靠實驗反推，因為崩潰沒有任何痕跡與告警（與 R-4.5.6-4（b）相反） | 排程入口一律過 `crashguard.run`：未捕捉例外 ⇒ `sentinel_crashed`／`park_job_crashed` 痕跡＋`alert(loud=True)`＋仍重排；連續 3 次停止重排 | 新葉 `tools/lib/sessionctl/crashguard.py`；planner 只增分派呼叫 | 50 |
| D-SW-3 | TH-B：提前探針 2/2 `unmeasured`、`reading=null` 無原因 | 先寫「行為」：量得到，量不到必須具名 `why`（封閉值域）；根因 Developer 先驗證是否與 D-SW-1 同源 | `parkearly.py`／`parkprobe.py` 的痕跡欄位；根因結果回填 §24.3 | 51 |
| D-SW-4 | TH-A（升格）：到點／提前到點不看「同專案另一 session 在動」 | 新葉 `othersession.active` 判準重用 `transcript_activity.driver_after`（只收 `kind=="assistant"`，人類／`/login` 視窗不算；r4a 修正）；提前＝不提前、到點＝延後（用盡終局 skip，且必須經 `park_announce` 出聲、status／簡報可見） | `tools/lib/sessionctl/othersession.py`；呼叫點 `park_fire.run`、`parkearly._precheck` | 52 |
| D-SW-5 | G-5：接手時沒有「封存之後發生了什麼」 | `handoff --ack` 成功後印摘要（唯讀、零 token） | 新葉 `tools/lib/sessionctl/ackevents.py`；掛點 `ackhook.after_handoff` | 53 |
| D-SW-6 | G-5 另半：機械層第 4 欄不列 `*-halfwork` | 第 4 欄加列本 owner 的保全標籤（標題不改）；第 3 欄 worktree 現查已落地，只鎖住 | `handoff_build.py::_git_sections`／`wip_tags` | 54 |
| D-SW-7 | G-2：名冊訊息把三類狀態併成一句「由主控決定」 | 三段式文字；`stopped` 看主控層是否提到該代理 | `agentbrief.render_cut`＋`cutvoice` 三處傳入包 | 55 |
| D-SW-8 | G-4：M-W1 把背景 shell 算成無看管 | `stop_events` 加 `kind`，`m_w1` 加 `agent`／`shell` 子集 | `tools/lib/wastecensus/supervision.py` | 56 |
| D-SW-9 | G-3：哨兵重放不帶 `park=`／`stale=`／帳號比對，主控被誤導 | 加第四列「真 tick 同輸入」，唯讀、不呼叫 `reconcile` | `tools/probe/sentinel_decide_replay.py` | 57 |
| D-SW-10 | 舊哨兵殘骸（無觸發時刻）無人 GC | ack 時掛 `sentgc.sweep`：只拆 `NextRunTime` 空、非本 sid、**非執行中（`State!=Running` 且 `LastRunTime` 夠舊）**的殘骸；列舉經沙盒範圍化的 `job_table`；`status` 維持唯讀（r4a 修正） | 新葉 `tools/lib/sessionctl/sentgc.py`；掛點 `ackhook.after_handoff` | 58 |

### 24.1 D-SW-1：為什麼是 devnull、為什麼是 SSOT 而不是 `acctswitch.py:229`

- **成因鏈**（程式座標，現查）：`_sentinel_tick`（`session_resume_planner.py:1428`）→ `ruling_io.sentinel_halt`（`:1488`）→ `compose` → `acctswitch.reconcile`（`:223` 寫完 `account_switch` 痕跡後 `:229` 直接 `sys.stderr.write`）。排程器以 pythonw 起行程且不繼承 std handle ⇒ `sys.stderr is None`；`_stdio_utf8.py:72～73` 對 `None` 只 `continue`。⇒ `AttributeError` 未捕捉。
- **為什麼不是改 `:229`**：同一族站點不只一處（`quota_gate.py` 的 `sys.stderr.write`：693、853、855、882、1081、1105、1125、1146 行；`pace_contract.py`、`quota_availability.py`、`apply_lock.py` 另有同形站點，是否落在排程入口的 import 閉包內由 AT-CTL-96 的 AST 掃描判定，SD 未逐一驗證）。改一行＝壓制；SSOT 一處正解＝消除成因（根 CLAUDE.md〈修復不留後遺症〉順序：消除成因＞型別／結構層正解＞有文件依據的決策＞壓制）。
- **為什麼 devnull、不另開日誌檔**（主控定）：①`print(file=None)` 本來就是 no-op，語意只改變「直接 `.write` 會炸」；②日誌檔需要路徑、輪替、清理、編碼與權限決策，新增一整塊狀態面；③診斷由 D-SW-2 的結構化痕跡承擔（比散文 stderr 好稽核）。**取捨**：stderr 內容在 pythonw 下仍看不到——這是現況（`se_gate.py:44` 的註解早已寫明「pythonw：stderr None 靜默」），本決策不倒退、也不假裝解決。
- **射程**：只有「沒有繼承 std handle」的行程（pythonw 排程入口、`DETACHED_PROCESS` 子行程）。hook 與前景指令都有管線，行為不變；`io.StringIO` 等測試替身（無 `.reconfigure`／`.buffer`）仍 no-op。
- **語意等價的兩個分支站點**（r4a）：`tools/lib/openitems/verbs.py:193`、`tools/selfimproving.py:454` 以 `sys.stdout is not None` 分支；改綁 devnull 後由「略過輸出」變「輸出寫進 devnull」，同樣不可見、rc 不變——故「只改變直接 `.write` 會炸這一點」是對 `.write`／`.flush` 站點而言，這兩處為語意等價（AT-CTL-96 的普查納入）。
- **入口前提**：排程入口在進入點呼叫 `reconfigure_stdio_utf8`（planner、`tools/sessionctl.py` 現查已匯入；Developer 以 REQ-CTL-50 入口清單逐一確認）。
- **持有面**：`tools/_stdio_utf8.py`（被 `.claude/hooks/**` 匯入，但本節不改 hook；`tools/tests/test_stdio_utf8.py` 既有斷言全綠＝不改行為的證據）。

### 24.2 D-SW-2：排程入口崩潰護欄（`crashguard`）

- **設計**：`crashguard.run(entry, body, *, on_crash, state_ref)`＝`try: return body() except Exception as exc: …`。**純轉接＋三件事**（落痕跡、`quota_escalation.alert(loud=True)`、呼叫注入的 `on_crash` 重排），判準與常數全在本葉；planner 分派處只寫 `return crashguard.run("sentinel-tick", lambda: _sentinel_tick(args), on_crash=…)`（單行，每入口 ≤2 行，總增量 ≤6 行）。
- **痕跡欄位**（稽核分形，承 R-4.5.6-4（c））：`sentinel_crashed`／`park_job_crashed`／`sentinel_crash_loop` 三個互異事件名；`exc_type`、`file`（相對 repo）、`line`、`tb`（≤`CRASH_TB_MAX_CHARS`）、`sid`、`task`、`entry`、`streak`。
- **告警管道**：沿用既有 `quota_escalation.alert(reason, state, loud=True, plan=…)`；不新增通知原語、不新增 Windows toast 路徑。注意該函式既有文字標題是「需要你動手」（`quota_escalation.py` 的 `alert` 內 note 內容）；崩潰告警的 `reason` 字串自帶「哨兵崩潰（<例外型別> @ <檔>:<行>）、已自動重排」，由 Developer 確認此標題不致誤導（若會誤導，只加 `reason` 前綴，不改 `alert` 簽名；那是 §13 界外的文字面，不為此擴大守衛）。
- **告警的真實行為與停止時的可見性（r4a；主控裁示 2 附條件）**：`quota_escalation.alert(loud=True)` 對 `dead_agents==0` **只寫紙（`note_path()`）＋入通知佇列、不敲桌面**（`quota_escalation.py:756～804`，HELM-01）；本設計不傳 `dead_agents`、不繞過，所以崩潰告警的實際落點＝note 檔＋佇列，**E2E 與 AT 不得斷言 toast**。連續 3 次停止重排那一刻另留 handback（`resume_route.handback_report(f"{sid}_sentinel_crash_loop")`，與 `park_announce._handback` 同形，二選一已定）。可見性：`crashguard.status_lines(env)` 唯讀取痕跡 `autosdd_session_switch.jsonl` 各 sid 最新一筆 `{sentinel_crash_loop, sentinel_crash_cleared, sentinel_gc}`，最新為 `crash_loop` ⇒ 一行「哨兵因連續崩潰停止：<task>／<sid8>／<exc_type>@<file>:<line>」，由 `roster.render_snapshot`（`sessionctl status`）與 `briefline`（SessionStart）各以 ≤3 LOC 掛上；正常 tick 使 streak 歸零（原 streak>0）時落 `sentinel_crash_cleared`、殘骸被 `sentgc` 拆除時落 `sentinel_gc`，兩者皆使該行消失。WHY 讀痕跡不讀狀態塊：狀態塊在停止後會被 GC／拆哨兵時一併清掉，痕跡在持久目錄 `~/.autosdd/traces`。
- **為什麼連續 3 次停止重排**：沒有上限的「崩潰→重排」＝每 15 分鐘一次無聲空轉直到天荒地老（與根 CLAUDE.md 鐵律六同族：等待機制自己壞掉）；3 次是「瞬時環境問題 vs 結構性崩潰」的最小分辨量，常數 `CRASH_STREAK_MAX` 住 `crashguard.py`、只准不變或下修。streak 寫進狀態塊（既有 `_write_relay_best_effort` 路，不新增檔案）。
- **`park --fire` 崩潰**：標記走既有失敗鏈（`park_chain` 結算 `failed`＋`park_announce.announce`），不新增第二條失敗出口（QW §7.5 單一失敗鏈）。`refused`（L1）永不進本路。
- **rc 語意**：重排成功後仍回 1，讓排程器 `LastTaskResult` 如實為非 0，**同時 `NextRunTime` 非空**——兩者合讀＝「崩潰過但仍活著」，與 G-1 的「`LastTaskResult=1` 且 `NextRunTime` 空白＝死了」可區分；這是 ARCH-Q34 G-1 證據 1 的反面。
- **入口清單 `crashguard.ENTRIES`**：`session_resume_planner.py` 的 `--sentinel-tick`、`--resume-tick`（`_resume_tick` 內部已有 R97 的 try/except，保留；`crashguard` 是外層兜底）、`tools/sessionctl.py park --fire`、`oldwin_sched.job_argv` 的到點 job。Developer 以 `park_cli.job_argv`／`oldwin_sched.job_argv`／planner 註冊腳本三站點普查；新增排程入口而未入表＝AT-CTL-101 紅。
- **持有面**：`tools/lib/sessionctl/crashguard.py`（新）、`tools/session_resume_planner.py`（守衛面，只增行）、`tools/sessionctl.py`（薄殼，`park --fire` 分派處增 1 行）。

### 24.3 D-SW-3：TH-B 行為規格與「待實作驗證」欄

- **規格只寫行為**（TCS REQ-CTL-51）：armed park 期間，排程器（pythonw）起的探針必須取得新鮮讀數；量不到必須落具名原因；換帳號且判決 `CONTINUE` ⇒ 兩個巡邏間隔內提前接手。**根因由 Developer 查，不預設**。
- **證據**（ARCH-Q34 §6 TH-B）：`autosdd_session_switch.jsonl` 第 1379 行（09:51:52）、第 1381 行（10:06:52）`park_early_probe reason=unmeasured stale=true reading=null`；`quota_burn.jsonl` 在 11-26 晚至 11-28 10:12 之間無讀數；M-C3「探針 2 次、unmeasured 2（1.0）」。
- **待實作驗證（疑點，皆唯讀可驗；SD 只唯讀看了呼叫鏈，未實跑）**：
  1. **與 G-1 同源？**量測路徑 `parkearly.tick`（`:90`）→ `park_reset.ruling_for`（`park_reset.py:33`）→ `gather` → `quota_gate.pace_state`（`quota_gate.py:896`）→ `quota_meter.measure_detail`（`quota_meter.py:751`）。若鏈內任一處在 pythonw 下 `sys.stderr.write`（`quota_gate.py` 有多處），例外會被 `parkearly.tick` 的 `except Exception`（`:117`）吞成 `park_early_error`（落 `EV_ERROR`）或被 `settled_quota` 判量不到。**驗法**：以 `sw_pythonw` 載具真跑 `pace_state`，修 D-SW-1 前後各一次，取例外型別（TCS AT-CTL-108）。痕跡第 1379／1381 行是 `park_early_probe`（不是 `park_early_error`），所以它更像「走完了但量不到」而非「例外被吞」——此推理支持疑點 2～4 優先，但**不排除** `measure_detail` 內部以 `(None, reason)` 吞例外。
  2. **補量名額**：`claim_refresh_slot()`（`quota_gate.py:591`）每個 TTL 只放行一個補量者；哨兵 tick 若永遠搶輸（keepwarm、hook 先搶）而 `await_winner`（`quota_gate.py:617～619`）在 `QUOTA_SYNC_TIMEOUT_SECONDS` 內等不到 ⇒ 結構性 `unmeasured`。**驗法**：讀 `refresh_stamp_path()` 戳記時刻與哨兵 tick 時刻的相對位置（痕跡 09:51:52 與 10:06:52 對照）。
  3. **pythonw 環境缺憑證面**：排程器起的行程環境缺 `USERPROFILE`／`HOME`／`CLAUDE_CONFIG_DIR` ⇒ `measure_detail` 找不到憑證檔 ⇒ `no_credential`。**驗法**：`sw_pythonw` 載具內印 `os.environ` 子集。
  4. **舊帳號憑證已失效且新帳號憑證尚未落入快取**：逐字稿 10:08～10:11 另一實例 `/login`（5387233b）；`quota_burn.jsonl` 首筆 `account=34cd3507237f` 約 10:12——即 10:06:52 的探針發生時帳號尚未換，讀數量不到可能是舊憑證 401。
- **疑點 4 的取證指令**（唯讀，一行）：`python -X utf8 -c "import json,pathlib; p=pathlib.Path.home()/'.autosdd'/'traces'/'quota_burn.jsonl'; r=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; print([(x['ts'],[f for f in x['fp'] if f.startswith('account=')]) for x in r if x['ts']>='2026-11-28T10:00'][:3])"`（`quota_burn.jsonl` 路徑＝`quota_gate.burn_ledger_path()`；列欄位 `ts`、`fp`〔含 `account=<指紋>`〕、`pct`；SD 本棒只確認欄位形狀，未以此斷言「10:12 首筆」，該時間仍是 ARCH-Q34 敘述，由本指令驗）。
- **回填格**：Developer 完成驗證後在此回填「成立的疑點編號、證據（輸出）、修法 commit」。不論哪個成立，皆須有一條紅綠自證的修法與 AT（TCS AT-CTL-104～108）。
- **不放寬**：`parkprobe.evaluate` 的 fail-closed（量不到不判恢復）、判決非 `CONTINUE` 不提前，逐字不變。

### 24.4 D-SW-4：TH-A 升格（雙駕駛防護）

- **升格理由**（寫進規格 WHY；§13 TH-A 的升級觸發條件已成立）：①問題 4 是掌舵者明令設計的演算法，前置情境在真實逐字稿已發生 **2 次**（4290bf58 開於 10:11:26、ack 10:13:43，2.3 分；814608d1 開於 11-22 15:14:14、ack 15:16:41，2.5 分；ARCH-Q34 TH-A）；②G-1／TH-B 修好後提前探針才會真的 fire，**發生率隨之上升**（修了 TH-B 反而放大 TH-A）；③掌舵者真機回報（暴露證據 (a)）：交接包 `C:\Users\wuwei\.autosdd\handoff\65389f03-4a29-43f2-8228-61cb3c884a4e_20261121T095211Z.prompts.md` **第 13 行**：「為何還有另一個視窗, 問同樣的問題? 是否沒有執行自動關閉機制? 這也會導致混淆或多頭馬車!」。三者同時成立，依〈守衛面准入〉暴露三取一，**不是理論洞**。
- **判準**：`othersession.active(project_dir, own_sid, now)`：`project_dir` 直下 `*.jsonl`（`<sid>/subagents/` 不是另一個 session）、`stem != own_sid`、`transcript_activity.driver_after` **以迴圈呼叫**直到回 `kind=="assistant"`（命中）或 `None`（沒人在動）。**迴圈的理由（r4b，QA 複審 P2-N1）**：`driver_after`（`transcript_activity.py:358～376`）回傳的是 `since_epoch < stamp <= now` 窗口內**最早一筆**非合成對話記錄（`stamp < best[0]` 取最小，`kind` 可為 `assistant`／`human`／`auto-continuation`），不是「窗口內有沒有 assistant」；真實活躍 session 的窗口內通常「人類提示 → assistant 回覆」交錯，最早一筆常是 human，單次呼叫只看 `kind` 會把正在動的 session 判成沒人在動＝雙駕駛。作法：`since = now − N`；`r = driver_after(path, since, now)`；`None` ⇒ 此 sid 沒人在動；`assistant` ⇒ 命中；其餘 ⇒ `since` 推進到 `r.timestamp` 的 epoch 再呼叫。終止：每步 `since` 嚴格增大、上界 `now`；另設硬上限 `OTHER_SESSION_SCAN_MAX_STEPS`＝200 次，逾限視為沒人在動並落痕跡 `action=scan_cap`（fail 方向不變）。**不改 `transcript_activity.py`**（守衛面；只被呼叫），迴圈只住 `othersession.py`；改回單次呼叫由 MU-CTL-76 咬住。`N＝SENTINEL_INTERVAL_SECONDS`（現值 900 秒；現查 `tools/session_resume_planner.py:251`）。**重用**：「有沒有別的駕駛」的單一判準住 `tools/lib/transcript_activity.py::driver_after`（`:358`；DEF-200-564 哨兵、`_run_resume` spawn 前閘、重放探針共用；掃主檔＋近 24 小時 subagent 檔、排除 `<synthetic>` 限額記錄）——不開第二家、不看 mtime（DEF-200-560：harness `away_summary`／每小時 `cost-state` 會讓 mtime 一直在動）。**為什麼只收 `assistant`、不用 `newest_conversation_at`（r4a，主控裁示 1(a)）**：`newest_conversation_at` 的「對話記錄」含 `type=user ∧ origin.kind=human`（`transcript_activity.py:104～117`），換帳號時開的 `/login` 視窗只有人類／本機指令記錄、沒有 AI 回合，用它會把這個視窗誤判成「另一個 session 在動」，park 到點被白白延後 3 次（≈45 分）再終局 skip——正是本節要消除的情境（4290bf58 開於 10:11:18、為換帳號視窗）。`driver_after` 回傳 `kind`（`assistant`／`human`／`auto-continuation`）讓呼叫端自選，本判準只認 `assistant`，**不新寫任何詞表**。掃描骨架與 `sentinel_lifecycle_arm.superseding_since` 的目錄走法一致，但**門檻不同**：後者要「24 回合且 600 秒」才算接手（拆哨兵、不可逆），本判準要的是「此刻有人在動」（只決定延後／不提前，可逆），故不套用 `MIN_TURNS`／`MIN_SPAN`。
- **處置分兩處**：
  1. `parkearly._precheck` 回 `other_session` ⇒ 不提前（探針下一巡邏照常；無狀態改動）。
  2. `park_fire.run`（排程到點的 job 本體）：在 `live_driver`（同 sid）之後、`handoff._duplicate_refusals` 之前加：有其他 session 在動 ⇒ **延後**（重排原語＝`oldwin_park._rearm`＋`park_yield.rearm_fields`，同 `park_yield` 的 rearm 路徑；計數欄 `other_session_defers` 住標記，不與 `park_yield.RESCHEDULES_KEY` 共用，避免兩種延後互相吃額度），至多 `OTHER_SESSION_MAX_DEFERS`（3）次，**用盡終局 `skip("other_session")`**。
- **為什麼延後而非終局 skip**（偏離主控裁示字面「skip（理由 `other_session`）並落痕跡」；已列報告「偏離」）：終局 skip 走 `finish(0, "skipped", reason)`，標記結算成 `skipped`，交接包再無人接手。但同專案常有與本交棒無關的 session（SelfImproving 每日無人窗口、其他視窗）在到點瞬間有對話記錄——直接終局 skip 會把全自動接手整批吞掉，與本節目標（全自動）相反。延後 3 次（≈45 分鐘）仍有人在動時，才判定「真的有人在接手」而終局 skip；`other_session` 這個理由字串與痕跡 `park_other_session` 仍照裁示落下。**用盡的終局 skip 必須出聲（r4a，主控裁示 1(b)）**：`park_fire.skip` 現況不呼叫 `park_announce.announce`（只有 failed 分支 `park_fire.py:78` 出聲），照原設計實作會讓「交接包無人接」對掌舵者與下一個 session 無聲。故終局分支在結算標記後呼叫 `announce` 恰一次（`announce` 泛化為由呼叫端傳 `title`／`body`／handback 檔名尾碼，失敗鏈預設值逐字不變），走既有管道（handback＋通知佇列＋依標記 `desktop_notify` 偏好的桌面通知）；`sessionctl status` 的 park 列與 SessionStart 簡報（`parkprobe.brief_line` 同形）顯示「park 因他 session 在動而終局 skip：<包路徑>」，判準只讀標記 `status=="skipped" ∧ outcome.event=="other_session" ∧ 包尚無 .ack`（`othersession.status_lines`，不新增狀態面）。若主控認為應直接終局，改 `OTHER_SESSION_MAX_DEFERS＝0` 即可（一個常數，AT-CTL-112 以參數化涵蓋）。
- **fail 方向**：目錄讀不動／逐字稿讀不到 ⇒ 回「沒人在動」（維持現行行為；不替系統增加無證據的攔阻）。
- **與既有防線的關係**：`.ack` 已存在 ⇒ `skip("acked")`（雙駕駛防線）不變；`live_driver`（同 sid）不變；本判準補的是「**別的 sid**」。
- **不新增 spawn 站點、不動 `.claude/**`、不新增讀額度端點**（PRD §15.5 紅線 1 不受影響）。
- **持有面**：`tools/lib/sessionctl/othersession.py`（新）、`park_fire.py`、`parkearly.py`（W-SW2 與 W-SW3 同持有面 `parkearly.py`，串行）。

### 24.5 D-SW-5／D-SW-6／D-SW-10：ack 摘要、機械層第 3／4 欄、舊哨兵 GC

- **ack 摘要**（`ackevents.summary`）：資料源＝`autosdd_session_switch.jsonl`（`switch.trace` 寫的那份，路徑取自既有 `trace_dir`）、`<包 stem>.sealed` 時刻、排程器自報（Windows：`Get-ScheduledTask … | Get-ScheduledTaskInfo` 的 `LastTaskResult`／`NextRunTime`；macOS：`launchctl` 的 rc，照實劃界：憑證是 rc 不是時間值）、`holder`／行程表（驗身分）。唯讀、零 token、預算 2 秒。掛點＝`ackhook.after_handoff`（它本來就在 `tools/sessionctl.py` 入口層，`handoff.py` 不 import，守行數牆 §21）。ARCH-Q34 G-5 證據：406454ea 包封存於 11-26 23:47:36 後發生 keepwarm 主載具被殺（逐字稿第 10419 行）、帳號切換、舊哨兵崩潰（G-1），新主控得手翻痕跡。
- **機械層第 3 欄**：**現查已落地**——`handoff_build.py:96～98` 已含 `git worktree list`（DES §9.3 ⑦ 的實作；TCS AT-CTL-30 已斷言「欄 3 含 worktree 行」）。ARCH-Q34 §5 寫「未查」是當時未讀該檔；本節只重申並以 AT-CTL-120 鎖住，不重做。
- **機械層第 4 欄**：現行 `wip_tags`（`handoff_build.py:63～67`）只列 `git tag --points-at HEAD` 且以 `-wip-preserved` 結尾者；`406454ea-20261126-flk5-halfwork` 指向 `git stash create` 的 commit（`dc65a475`，不在 HEAD）所以列不到，只活在手寫層（包第 284 行）。新規則：另列 `git tag --list "<sid 前 8 碼>-*"` 中以 `-halfwork` 或 `-wip-preserved` 結尾者，附目標 SHA 前 12 碼與「不在 HEAD」。**標題 `wip-preserved 標籤` 不改**（`MECH_HEADINGS` 順序與字面是 AT-SC-34／AT-CTL-30 的鎖，改標題＝放寬／破壞既有鎖）。
- **舊哨兵殘骸 GC（誰、何時）**：由 `handoff --ack` 成功後的 `ackhook.after_handoff` 呼叫 `sentgc.sweep`；**不在 `status` 顯示時 GC**（`status` 維持唯讀，TCS AT-CTL-139）。判準四合取（`NextRunTime` 空、sid≠acker、`LastTaskResult∉{0,267009,267011}` 或任務書 `state∈{abandoned,disarmed,superseded}`、**排程器自報 `State!="Running"` 且 `LastRunTime` 距今 ≥ `SENTINEL_INTERVAL_SECONDS＋parkearly.CHILD_TIMEOUT_SECONDS`〔現值 900＋600＝1500 秒〕；任一讀不到 ⇒ 不拆**）；`NextRunTime` 非空一律不動；至多拆 5 個。**第四條的成因（QA P2-4）**：哨兵 `-Once` 觸發後 tick 進行中（至多一個 `CHILD_TIMEOUT_SECONDS`），工作物件 `NextRunTime` 為空、`LastTaskResult` 為 267009（執行中，值取自 `check_scheduled_task_drift.py` 已知良性值表），前三條會把**活著、正在跑的別人哨兵**拆掉；`LastRunTime` 門檻再擋「剛跑完、重排登記尚在途」。**移除與列舉走既有站點、不新增排程原語**：移除＝`schedule_backend.select().disarm`（`sentinel_lifecycle._remove_task` 同一條；既有 `sentinel_lifecycle.gc` 走它，本 GC 不開第二個移除家）；列舉＝既有 `list_jobs(prefix)` 只回名稱、不夠判 `State`／`LastRunTime`，故在 `schedule_backend` 三後端各加**唯讀** `job_states(prefix)`（Windows＝`Get-ScheduledTask`＋`Get-ScheduledTaskInfo`；launchd 的 `last_run`／`next_run` 回 `None` ⇒ macOS 上本 GC 因「讀不到不拆」而不動作，只出聲，誠實劃界）。**範圍化（QA P2-5①）**：`sentgc.job_table(env, *, repo_root)` 在列舉階段依 `sandbox_scope.sandbox_home(repo_root)` 濾名稱——正式 checkout ⇒ 全部 `AutoSDD_Sentinel_*`；沙盒 repo ⇒ 只留 `AutoSDD_Sentinel_<該沙盒身分檔 sid>*`；`ackevents` 與 `sweep` 共用同一次列舉。這使 E2E 對沙盒跑真 `handoff --ack` 時，真實 `AutoSDD_Sentinel_406454ea-…` 殘骸**結構上進不了候選**，不靠清理時小心。WHY：ack 是「新 session 已接手、舊 session 的舊物該退場」的唯一機器可驗事件；`NextRunTime` 空白＝排程器自報「不會再跑」，拆它不可能影響任何喚醒。**限制（誠實劃界）**：殘骸要等「下一次任何 ack」才被清；沒有 ack 就沒有 GC（`status` 仍會顯示「過期哨兵」讓人看見）。406454ea 的現存殘骸（`AutoSDD_Sentinel_406454ea-91fc-4481-9c11-b28ed7d9e95f`）會在下次 ack 時被清；排程動作不在本棒範圍（SD 不動排程）。
- **持有面**：`ackhook.py`（掛點＋呼叫）、新葉 `ackevents.py`／`sentgc.py`、`handoff_build.py`。

### 24.6 D-SW-7：名冊訊息三段式（G-2）

- 現狀（ARCH-Q34 G-2 證據）：`agentbrief.py:294～300` 的 `render_cut` 把 `cut`（額度切斷）／`stopped`（主控 TaskStop）／`residue`（擁有者已不在）併成一句「被切斷／停止／未收尾（不自動重派，由主控決定）」；`_ACTIONS["stopped"]`（`:42～43`）一律「重派」；`cutvoice.stop_text`（`cutvoice.py:48～75`）不讀交接包。406454ea 逐字稿第 10412 行（2026-11-26T23:48:27）即此文字，而同稿第 10306 行（23:46:36）TaskStop、第 10308 行 `git stash create`、包第 284／288／308 行已記處置——掌舵者據此重提問題 3。
- 設計（TCS REQ-CTL-55）：三段標題；`stopped` 列看「本 sid **最新已封存**包的**主控層**（六節）」是否提到該代理 id 前 8 碼或描述首詞元：提到 ⇒「主控已停止並已記入交接包 <路徑>」，否則「主控已停止、交接包未記處置 ⇒ 下一棒依第 12 欄重派」。**只看主控層**：機械層第 12 欄本來就列所有代理，把它算進去＝恆為「已記入」，判準失去鑑別力（TCS MU-CTL-62）。406454ea 的包主控層只寫「FLK5」（第 284／288 行）、id 只在第 12 欄（第 203／207 行）——所以首詞元規則是必要的，否則這個真實案例仍會落「未記處置」。
- **不加推回**（AT-CTL-127）：`stop_message` 的 `decision` 不變、閂鎖不變；只改 `systemMessage` 文字。第 12 欄 `render_rows`／`_block` 逐字不變（那是交接包本身，「建議處置：重派」在該處是正確的）。E2E-CTL-12 的「四處清單同文」比對範圍收斂為「列的 id／輸出落點／重派指標」，標題行與 `stopped` 處置行不在比對內（TCS §8 檔頭已載）。
- **持有面**：`agentbrief.py`（`render_cut` 簽名加 `pkg_text`／`pkg_path`，預設 `None` ⇒ 退化為「未記處置」句）、`cutvoice.py`（三處呼叫點找包並傳入）。**不動** `roster.py`（貼天花板）、`sessionctl_guard.py`（`.claude/hooks/**`）。

### 24.7 D-SW-8／D-SW-9：量測與重放（非守衛面）

- **M-W1 子代理口徑**（ARCH-Q34 G-4 證據）：`w1_detail.txt` 第 14～43 行，29 筆 >30 分中 **17 筆**是「本回合結束時仍有 背景任務在跑：（1 個背景 shell）」；`STOP_VOICE="本回合結束時仍有"`（`supervision.py:35`）同時命中代理與 shell。分類規則見 TCS REQ-CTL-56。**既有鍵逐字不變**（向下相容，既有 `test_waste_census_ctl.py` 不改斷言）；§13 TH-2 的升級觸發改以 `agent.gt_30min` 判讀。
- **哨兵重放第四列**（ARCH-Q34 G-3 證據）：工具現只傳原始 halt 標記、`grace`、`driver`（`sentinel_decide_replay.py:121～126`），不傳 `park=`、`stale=`、`superseded_by=`，不做帳號比對；真 tick（`session_resume_planner.py:1489`）傳 `halt=ruling_io.sentinel_halt(…)`＋`park=`＋`stale=`。結果：主控以重放得 `arm_reset`，真實是 09:51／10:06 `patrol`（park 讓路）與 10:21:52 崩潰。第四列的 `park=` 以痕跡 `park_armed`／`park_cancelled`／`park_acked_cancel` 摺到 `--now`（重放是 as-of，磁碟標記只有現值）；**待實作驗證**：痕跡是否足以還原 `valid_until`／`route`（`park.yields` 的判準輸入）——不足則該列對該欄標「量不到」並說明，不猜。標題固定標明「不重現排程器 stdio 環境」（崩潰類缺陷此列看不見；那一類由 E2E-CTL-25／26 的真 pythonw 行程承擔）。
- **持有面**：`tools/lib/wastecensus/supervision.py`、`sections_ctl.py`；`tools/probe/sentinel_decide_replay.py`。皆**不接任何閘**。

### 24.8 暴露證據與守衛面准入（R197）

| 改動 | 屬守衛面？ | 暴露證據（severity.md〈暴露度〉三取一） |
|---|---|---|
| `_stdio_utf8.py`（D-SW-1） | 被守衛面匯入（`.claude/hooks/**`）；檔本身不在清單 | (b) 排程器自報 `LastTaskResult=1`／`NextRunTime` 空白（2026-11-28T10:25:01+08:00）；續航日誌 10:21:52 有 `sentinel_woken` 無 `sentinel_decided` |
| `session_resume_planner.py`、`crashguard.py`（D-SW-2） | 是 | 同上（G-1 無痕跡無告警） |
| `parkearly`／`parkprobe` 欄位（D-SW-3） | 是（`sessionctl/**`） | (b) 痕跡第 1379、1381 行 `unmeasured`、`reading=null`；M-C3 提前恢復 0 件 |
| `park_fire`／`parkearly`／`othersession`（D-SW-4） | 是 | (a) 65389f03 包 prompts 第 13 行掌舵者真機回報＋(b) 前置情境 2 次（4290bf58、814608d1） |
| `ackhook`／`ackevents`／`sentgc`（D-SW-5／10） | 是 | (b) 本 session 實況：封存後事件靠手翻（ARCH-Q34 G-5）、殘骸 `AutoSDD_Sentinel_406454ea-…` 仍在（`sessionctl status`「過期哨兵」） |
| `agentbrief`／`cutvoice`（D-SW-7） | 是 | (a) 掌舵者據 406454ea 逐字稿第 10412 行的舊訊息提問題 3：提問原文在 sid `4290bf58-a5e9-4e64-b118-e9db87ca2af4` 逐字稿（`~/.claude/projects/D--CursorProject-AISDCL-Agent/4290bf58-a5e9-4e64-b118-e9db87ca2af4.jsonl`）**第 14 行**（內含「沒有主Agent去掌控Subagent」；現查：該行 `grep` 命中，同稿第 34、196、201 行為後續重貼） |
| `handoff_build`（D-SW-6） | 是 | (b) 包第 284 行手寫、機械層第 4 欄不列 `halfwork` |
| `supervision.py`、`sentinel_decide_replay.py` | 否（量測／探針） | (b) `w1_detail.txt` 第 14～43 行；重放與真 tick 輸入不同（主控被誤導一次） |

「量、不挖」：本節只處理有暴露證據者；TH-C（17 筆 shell 是否含 keepwarm／watch 未被辨識）、TH-D（keepwarm 主載具 11-27 00:40:52 被殺原因）只登記（§24.11），不擴大搜尋。

### 24.9 新葉模組與落點（照 `Root_Layout_and_Module_Placement.md` §2；追加 §16 表，不改既有列）

| 元件 | 路徑 | §2 格 |
|---|---|---|
| 排程入口崩潰護欄 | `tools/lib/sessionctl/crashguard.py` | 函式庫（sessionctl 既有套件新葉） |
| 另一 session 在動判準 | `tools/lib/sessionctl/othersession.py` | 同上 |
| ack 後封存後事件摘要 | `tools/lib/sessionctl/ackevents.py` | 同上 |
| 舊哨兵殘骸 GC | `tools/lib/sessionctl/sentgc.py` | 同上 |
| 測試（新） | `tools/tests/test_sessionctl_crashguard.py`、`test_sessionctl_othersession.py`、`test_sessionctl_ackevents.py`、`test_sessionctl_sentgc.py`；其餘擴充既有 `test_stdio_utf8.py`、`test_sessionctl_ackhook.py`、`test_sessionctl_agentbrief.py`、`test_sessionctl_parkprobe.py`、`test_waste_census_ctl.py` | 測試 |
| E2E | `tools/lib/realverify/cases/control.py`（RV-CTL25～35）、登記 `docs/06_quality/RealVerify_Protocol/cases.json`；結果帳 `docs/06_quality/RealVerify_Result_Ledger.md` | realverify 既有套件 |
| 規格 | 本節；`docs/03_testing/contracts/TCS-Control-20261122.md` §8；PRD 修訂表 v2.1.30、§16.6 2026-11-28 列 | 需求／設計、測試契約 |

### 24.10 LOC 影響（量測日 2026-11-28；數字一律現查 `python AutoClaude/tools/check_loc_budget.py --json`，下表是本棒當回合以 `count_loc` 與行數實量）

| 檔 | 現值（LOC／raw 行） | tier 上限 | 本節增量上界 | 說明 |
|---|---|---|---|---|
| `tools/session_resume_planner.py` | 742／1666 | `guardrail_cli` 750（餘裕 8） | ≤6 LOC（每入口 ≤2 行；`--sentinel-tick`、`--resume-tick`；`import crashguard` 若頂層寫就計入這 6 行，一律惰性 import 寫在分派那一行內） | 判準全進 `crashguard.py`；**餘裕近 0，Developer 動工前後各量一次**；超出＝設計不可行，退回 SD 重拆而非改天花板 |
| `tools/_stdio_utf8.py` | 24／92 | `guardrail_cli` 750 | ≈+6 LOC | `None` 分支改綁 devnull |
| `tools/lib/sessionctl/park_cli.py` | 325／403 | `guardrail_lib` 400 | **0** | raw 行數 403 已逾 DES §21 當時的牆值 400（該牆的口徑現查 `tools/tests` 對應鎖），故**不增一行**；`park --fire` 的 `crashguard` 包裝落 `tools/sessionctl.py` 入口層 |
| `tools/lib/sessionctl/agentbrief.py` | 254／346 | 400 | ≈+40 LOC | 三段式與已記入判準；若逼近 400 把「已記入」判準抽到新葉（不動 tier） |
| `tools/lib/sessionctl/cutvoice.py` | 72／110 | 400 | ≈+15 | 三處呼叫點找包 |
| `tools/lib/sessionctl/park_fire.py` | 61／80 | 400 | ≈+20 | 前置＋延後＋終局 skip 出聲（r4a） |
| `tools/lib/sessionctl/park_announce.py` | 現查 | 400 | ≈+12 | `announce` 泛化 `title`／`body`／handback 尾碼（r4a；失敗鏈預設值逐字不變） |
| `tools/lib/schedule_backend.py` | 現查 | 依 tier 現查 | ≈+40 | 三後端唯讀 `job_states`（r4a）；若逼近 tier 上限，抽到同目錄新檔而非改天花板（動工前量） |
| `roster.py`／`briefline.py`／`parkprobe.py` | 523 raw／69／現查 | 400 tier 以現查為準 | 各 ≤3 LOC | status／簡報顯示 `crashguard.status_lines`、`othersession.status_lines`（r4a）；判斷全在新葉，動工前後各量，餘裕不足退回 SD |
| `tools/lib/sessionctl/parkearly.py` | 111／168 | 400 | ≈+10 | `_precheck`＋`why` 欄 |
| `tools/lib/sessionctl/ackhook.py` | 31／53 | 400 | ≈+10 | 掛點 |
| `tools/lib/sessionctl/handoff_build.py` | 153／207 | 400 | ≈+14 | 第 4 欄 |
| `tools/lib/wastecensus/supervision.py` | 184／252 | 400 | ≈+30 | `kind`＋子集 |
| `tools/probe/sentinel_decide_replay.py` | 92／131 | `guardrail_cli` 750 | ≈+40 | 第四列 |
| 新葉四檔 | 0 | 各 400 | 各 ≤150 | `crashguard`／`othersession`／`ackevents`／`sentgc` |

`tools/lib/transcript_activity.py`（316／569）**只被呼叫，不改**（`newest_conversation_at` 已存在）。Root_Layout §3 模組數 +4、`tools/tests` 新測試檔 +4 的棘輪重釘走 12 道鎖儀式（同一個 commit 收齊，見 TCS REQ-CTL-59）。

### 24.11 理論洞清單增列（只登記、不擴守衛；附升級觸發）

| 代號 | 洞 | 處置 |
|---|---|---|
| TH-A | 雙駕駛 | **本節升格並處理**（D-SW-4）；§13 原列保留為史料，其升級觸發條件已成立 |
| TH-B | 提前探針量不到 | **本節處理行為與具名原因**（D-SW-3），根因由 Developer 回填 §24.3 |
| TH-C | 17 筆背景 shell 事件是否含 keepwarm／watch 未被 `roster.is_supervision_shell` 認出（DEF-200-623 回歸？） | 只登記；觸發＝逐筆辨識出任一筆是 keepwarm／watch shell 仍被 Stop 出聲 |
| TH-D | keepwarm 主載具 11-27 00:40:52 被殺（逐字稿第 10419 行）原因未明 | 只登記；觸發＝主載具被殺且備援也失效、最後靠人 |
| TH-E（新） | 殘骸 GC 只掛 ack：沒有 ack 就沒有 GC（沒人接手的包，舊哨兵殘骸要等下一次任何 ack） | 只登記；觸發＝殘骸存在逾 7 天且期間無任何 ack（附工作名） |
| TH-F（新；r4a 改寫） | `OTHER_SESSION_MAX_DEFERS＝3` 用盡終局 skip 後交接包無人接的「無聲」面已由 §24.4 補上（終局 skip 經 `park_announce` 出聲＋status／簡報可見），**不再是理論洞**；殘餘風險只剩「另一 session 其實是無關的長跑視窗（有 assistant 回合）而誤擋」（人需依告警自行 `handoff --spawn`） | 只登記殘餘；觸發＝`park_other_session action=skip` 之後 24 小時內無人 ack 該包（附兩個 sid） |

### 24.12 被否決的方案

| 方案 | 否決理由 |
|---|---|
| 只改 `acctswitch.py:229` 一行（`if sys.stderr: …`） | 壓制；同族站點（`quota_gate.py` 多處）下次必重演；違反〈修復不留後遺症〉順序 |
| stdio `None` 時綁暫存日誌檔 | 主控已定 devnull；日誌檔引入路徑／輪替／清理／編碼決策面，且診斷已由結構化痕跡承擔 |
| `sentinel_crashed` 落痕跡但不重排 | 崩潰一次就喚醒鏈斷線，且 `NextRunTime` 空白＝與 G-1 不可區分；故重排＋streak 上限 |
| 無上限重排 | 結構性崩潰會每 15 分鐘無聲空轉（鐵律六同族） |
| TH-A 在 `park_fire` 直接終局 skip | 標記結算 `skipped` 後交接包無人接；同專案常有無關窗口在到點瞬間有記錄；見 §24.4（常數 `OTHER_SESSION_MAX_DEFERS＝0` 即可切回） |
| TH-A 判準用 `newest_conversation_at`（含人類記錄） | 換帳號 `/login` 視窗只有人類／本機指令記錄，會被誤判成「另一個 session 在動」而白白延後；`driver_after` 回 `kind`，只收 `assistant` 即可（QA P2-1） |
| 殘骸 GC 只看 `NextRunTime` 空＋`LastTaskResult≠0` | 把哨兵 tick 進行中（267009、`State=Running`）的活哨兵拆掉；需加 `State!=Running` 與 `LastRunTime` 門檻（QA P2-4） |
| E2E 的舊哨兵以 `AutoSDD_RV_` 租約工作冒充、清理時掃整台機器的 `AutoSDD_Sentinel_*` | 名稱前綴與 `ackevents`／`sentgc` 的列舉對不上，且 `sweep` 會溢出沙盒拆真殘骸；改用沙盒 sid 命名的真哨兵＋列舉階段範圍化（QA P2-5） |
| TH-A 判準看檔案 mtime | harness 的 `away_summary`／`cost-state` 讓 mtime 永遠新（DEF-200-560），判準失去鑑別力 |
| TH-A 判準套 `superseding_since` 的 24 回合／600 秒門檻 | 那把尺是「人已接手、可拆哨兵（不可逆）」；本判準只決定延後（可逆），用同門檻會讓剛開窗的 2.3 分鐘雙駕駛窗口恰好漏掉 |
| GC 掛在 `status` 顯示時 | `status` 是唯讀診斷，讓它有寫入＝診斷動詞變成副作用站點；且 `status` 常由人在危機時查看 |
| 把「已記入交接包」判準放寬到整包（含機械層） | 機械層第 12 欄恆列全部代理 ⇒ 恆「已記入」，判準無鑑別力 |
| 改 `MECH_HEADINGS` 第 4 項標題為「保全標籤」 | 破壞 AT-SC-34／AT-CTL-30 既有鎖；放寬鎖不可行 |

### 24.13 修復不留後遺症三問（本節）

1. **另一台機器／另一個人身上會不會回來？**不會：D-SW-1 在 SSOT 消除成因（任何新增的 `sys.stderr.write` 站點都被覆蓋，AT-CTL-96 的 AST 掃描自動納入新站點）；D-SW-2 的入口清單鎖（AT-CTL-101）讓新增排程入口未護欄即紅。
2. **有沒有文件、座標、凍結 digest、設定因此不一致？**§0～§23 與 TCS §1～§7 逐字不變；PRD 修訂表／§16.6 只增列；`MECH_HEADINGS` 不動；`engine-bridge` CLI 閉包不動（`othersession` 不被頂層 import，AT-CTL-143）；連動面（落點表、棘輪、compat-ci `paths`、`cases.json`、CLAUDE.md 若需增列）由 REQ-CTL-59 同一個 commit 收齊。
3. **有沒有留下「之後再看」？**有兩類已明文登記而非遺漏：TH-C／D／E／F（§24.11，各附升級觸發）、TH-B 根因（§24.3 回填格，Developer 先驗證）；除此之外無。凍結後實作前，規格不再補洞。

### 24.14 ADR 判斷
本節**無新架構決策需要 ADR**：①D-SW-1 是 SSOT 內的缺陷修復，②D-SW-2 沿用既有告警管道與重排原語，③D-SW-4 沿用 `park_yield` 重排原語與 `transcript_activity` 尺，④其餘為文字與量測。若主控認為「排程入口一律過 `crashguard`」屬跨專案架構約束，可在 ADR-XPLAT-004 §2.19 後追加一節；本稿不替主控代決。
