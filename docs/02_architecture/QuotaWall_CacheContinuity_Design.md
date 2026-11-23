# 額度牆前的快取續航與到點喚醒（QuotaWall Cache Continuity）設計稿——session 內等待為主載具、外部排程為備援

> 🔒 **spec-frozen（r8，2026-11-21）**：approver＝掌舵者（常態規則 2026-10-20，sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13；主控執行）；reason＝聯合 QA 第五輪 `r218_joint_specqa5_report.md`、第六輪 `r218_joint_specqa6_report.md` 判 r8 PASS（P1／P2＝0）；主控親驗 `git diff -U0 133c3a38` PRD 11 段、刪除行只在 R217 三處；與 R218-B r5 同 commit 凍結。**實作棒必辦（QA6 P3）**：QW6-P3-1 AT-QW-79⑥／AT-QW-81／E2E-QW-30(e) 夾具逐字照 T L2906 真實形態（讀上一支 keepwarm 輸出＋`*>` 新檔），S-24② 判準含任一次啟動的重導目標，並加痕跡 `keepwarm_work_reset reason=…`；QW6-P3-2 為 AT-QW-79⑧⑨ 補 MU（計數變動時同步 TCS 表頭、§7、PRD §16.6）。

> 角色：SD 系統設計（R218＋R218-C 合併，AISDLC 第 2 階段）。日期 2026-11-20，量測基準 HEAD＝`133c3a38`（工作樹另有 R217 期 A、R218 F5 未提交實作，見 §12 前置）。
> **版次**：**r8＝r7 ＋ 聯合 QA 第五輪（QW r7 FAIL：P2×2、P3×2；與 R218-B r5 表頭小修同 commit 凍結）逐條修**（附錄 G）：ping 實測 Δ 改為「相鄰兩次 ping 叫醒時刻（皆已補量）的讀數差」、區間內有真工作／真人提示／換窗的段不記（S-25）；保溫帳歸零的「真工作」只認含非唯讀且非監督 `tool_use` 的回合（重用 `midwork.READONLY_TOOLS` 與 `roster` 監督指令判準），使 `periodic` 的 R216 cap 不被讀 keepwarm 輸出的回合架空（S-24②）；§15 殘餘風險照實改寫並評估「貪婪續付」（不採，S-26）；X-19 的 `SENTINEL_OFF` 補 AT。r7＝r6 ＋ 聯合 QA 第四輪（FAIL：P2×2、P3×3；與 R218-B r5 聯合改版）逐條修**（附錄 F）：讀數帶年齡、陳舊先零 token 補量、補不到保守外推並標 `stale=yes`、早於閂鎖／參照的讀數不判換窗（S-23，§1 E10）；有目標時保溫預算只算未來 k、保溫帳於主控真工作或視窗翻新時歸零（S-24）；ping 實測讀數差取大（S-25）；§15 補第二次跨 reset 帳。r6＝r5 ＋ 與 R218-B r4 聯合改版（同一 SD 同時改兩稿；附錄 E）：兩稿交叉介面字面改以 SE **§10.2.1 跨規格介面對照表**為單一真相源（本稿只引用）；§7.5 加「spawn 站點 L1 拒絕（`RC_SIDEEFFECT_REFUSED`）＝終局 `refused`，不算失敗、不走另一路」；S-17 對齊 SE D-20 r4（正式目標遇不允許值不轉送、不阻擋登記）；§1 E9／S-3／S-18／§15 依主控以 Stop 守衛讀數核對的實數改正（跨 reset 付費 ping 5 次、89→94＝5pp、平均約 1 pp／次）；QA 第四輪判準自我核對（附錄 E 末）。r5＝r4 ＋ QA 第三輪（FAIL：P2×6、P3×7）逐條修（附錄 D）＋ R218-B r3 替身介面逐字對齊：S-19 加「讀數已降」且 defer 更新參照、park 標記 `primary_source` 使 close 流程不再停用 S-19、S-18 閂鎖改以「同一短窗視窗」判、fork 成功只認新 sid 逐字稿（S-20）、`handoff.spawn` 成功後才解除哨兵且 dedup 只認成功或活行程（S-21）、spawning 意圖有期限（S-13）。r4 的內容如下：r1「依 D 分兩桶」→ r2「跨重置保溫為主、封存換手為備援」（QA 規格審查 FAIL 後，主控代決 D-A～D-E）→ r3＝r2 ＋ R218-C 續航方法論重檢（掌舵者 2026-11-20 22:5x 立案：park 到點沒續跑、保溫沒作用；主控代決 D-F～D-K）→ **r4＝r3 ＋ QA 第二輪（FAIL：P2×5、P3×7）逐條修**（附錄 C）：期望值對齊公式、22:42 重放加「主載具被殺」變體、`handed_over` 判決杜絕兩個駕駛、平台維度（macOS）、欄名常數收進 Q1、未校準 `ping_pp` 隨上下文縮放且校準列為上線前必要、任何 E2E 不真開窗（正控一律假 `claude`）；另納 2026-11-21 真機實證（keepwarm 跨 reset 成功；暴露兩閘不認保溫 ⇒ S-18、提前重置 ⇒ S-19）。r2 的 `park --wall`、`fallback` 階段、黏性 S-5、刷新 S-6、S-10「主策略不掛 park 後備」在 r3 撤除（§0.6、§14）。
> 輸入（皆在 sid 4a45bc75 的 scratchpad，收尾窗口把關鍵段落抄進證據檔）：R218 Architect／SA 報告 `r218_architect_report.md`／`r218_sa_report.md`（下稱 **ARC**／**SA**）；QA FAIL 報告 `r218_specqa_report.md`（下稱 **QA**）、第二輪 `r218_specqa2_report.md`（下稱 **QA2**）、第三輪 `r218_specqa3_report.md`（下稱 **QA3**）；R218-C Architect／SA 報告 `r218c_architect_report.md`／`r218c_sa_report.md`（下稱 **CARC**／**CSA**）。逐字稿＝`C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\4a45bc75-afdb-4e86-82de-be508230e99b.jsonl`（下稱 **T**，行號＝jsonl 行號）。
> 上游：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 **PRD**），修憲走 §16.5 (i)（附錄 A）。驗收：`docs/03_testing/contracts/TCS-QuotaWall-20261120.md`（下稱 **TCS**；前綴 `REQ-QW-`／`AT-QW-`／`E2E-QW-`／`MU-QW-`）。
> 相容：R218-B `docs/02_architecture/RealVerify_SideEffect_Isolation_Design.md`（下稱 **SE**）的 L1 產品面拒絕、L2 副作用帳、居所轉送先於本稿落地（§12）。本稿新增的程式路徑在實作 commit 前不存在；落點依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2。
> **r9（2026-11-23，W12）**：只追加——附錄 H（撞五小時上限 RCA 的 W11a～e 逐項規格：擋派接線順序鎖、`L` 加在飛燒量、ping 樣本乾淨門檻與 schema 升版、閂鎖拆兩序列、`--pace` 標題補短窗最高帶、realverify 額度閘）、§12 表尾 W11b～e 四列（W11a 併 Q4）、§17.3；既有條文、編號、常數一字不動；TCS §8、PRD 修訂表 v2.1.27／§16.6 同步追加。

---

## 0. 結論與代決

### 0.1 結論
1. **兩種失敗，同一個根**：今天兩次撞牆冷重寫合計 486,057 token（T935、T1665，r2 §1）；22:42 park 到點沒續上、22:52 冷重寫 402,080 token（CSA §1）。根因是續航按「機制」切（哨兵／park／keepwarm／harness），不是按「情境」切——「視窗開著＋主動停工＋跨 reset」這一格的負責者是 park，而 park 用的是最不適合這一格的載具（外部行程殺窗重開），失敗又沒有下一層（CARC §一）。
2. **續航改按情境矩陣分派（§2，規範性）**：每格必有「主載具／備援／出聲」三欄，空格＝缺陷。
3. **主載具＝session 內背景等待**（D-F）：視窗開著時，到點喚醒與保溫統一由 `run_in_background` 的 `sessionctl keepwarm` 負責；牆鐘輪詢（≤60 秒一次）容忍睡眠。額度付得起 ⇒ 跨重置保溫（每段 ≤ 50 分、最後一跳在 reset＋s）；付不起 ⇒ 退成「到點只醒一次」，**不得不掛**。保溫與 park 不再互斥。
4. **外部排程降為備援**（D-G）：park 照掛，到點時刻＝主載具預定醒來＋10 分；醒來先看主載具與 `live_driver`，有人在動就讓路。備援觸發時同 sid 視窗還活著 ⇒ **不關窗**，依 F4 開 `claude -r <sid> --fork-session`（新 sid）或 FRESH 交接包；**撤回 R217 §7.1「park 到點先關再開」**。
5. **失敗不得無聲**（D-H）：備援失敗依序 F4 選的路 → 另一條路 → 出聲（handback＋SessionStart 公告＋UserPromptSubmit 提示＋通知佇列；桌面通知依使用者既有開關）；結局只記實際值；哨兵看到 `status=failed` 接手一次。
6. **額度牆預留**（r2 主體保留）：剩餘 R ≤ L 停新派工；R ≤ V 進收尾（TaskStop → 封存 → park → 掛 keepwarm），keepwarm 依預算決定跨重置或單跳。牆中不推回、不出監督事件，keepwarm 不在牆內醒（延到 reset＋s）。
7. **今天三件事套用後（推論，§15）**：兩牆保溫跨 reset 省約 57 萬加權單位；22:42 那一件由主載具在 22:42 原地叫醒（零開窗、零殺窗），若主載具也失敗，備援開 fork 新窗、不會再「沒人知道」。

### 0.2 主控代決（掌舵者 2026-10-31 常態授權「依照最佳化, 最理想, 最適當的解決方案…我授權幫我決策」；掌舵者可隨時以 T1 推翻）
| 代號 | 決定 | WHY |
|---|---|---|
| D-A | 主策略＝跨重置保溫（ARC 方案 a＋d） | QA P2-1：harness 在 reset＋約 100 秒自動續接舊 session（T931、T1656），r1 桶 1 今天兩牆省 0；ARC 實算 k 最壞 6 ＜ n*≈9 |
| D-B | 擋派線貼近牆；額度照樣用到接近滿 | 掌舵者裁決原文；QA P2-3 |
| D-C | 「注定失敗」以預算判；r3 起付不起不是「不掛」而是「單跳」 | QA P1-2；CARC §2.3「保溫跨不過 reset 不得等於沒人叫醒」 |
| D-D | 收尾先 TaskStop 全部在飛代理，再封存 | QA P1-1：與冷叫醒閘矛盾從流程上消失 |
| D-E | 掌舵者原裁決兩個前提不成立，照實改版（§0.5） | 主控已回報 |
| D-F | 主載具＝session 內背景等待（擴充 keepwarm，不另開指令）；牆鐘輪詢；付不起退單跳、不得不掛；保溫與 park 不互斥 | CARC §2.1 W1：官方文件「本機互動 session 背景指令 no time limit」；19:14 保溫準時叫醒（CSA §1）＝這個載具在本視窗活得好好的。擴充 keepwarm 而不新增 `waituntil`：冷叫醒閘豁免、holder 互斥、保溫帳都已在 keepwarm，新指令要再造一份（V-W6） |
| D-G | 外部排程降為備援：fire＝主載具醒來＋寬限；讓路；活窗不關、改 fork／FRESH；殺窗只留給卡死且明示開關 | CARC §1.2：「先關再開」用最脆弱的手段解一個不需要跨行程的問題；CSA §2：舊窗自動關閉上線至今 24 次事件 0 次成功。**取代 R217 D-14**（該條是掌舵者 2026-11-19 互動選項「有條件自動關 (Recommended)」；本代決依 22:5x「請重新檢視整個方法論」授權改語意，跨 sid `--ack` 後關舊窗的原用途不變） |
| D-H | 失敗鏈 F4 路 → 另一條 → 出聲；結局記實際值；哨兵接手 `status=failed` | CARC C8～C11：失敗＝靜默終局 |
| D-I | `procstop` 映像改家族比對；oldwin 單元測試圍籬 | CARC §1.3、CSA §2 實測 `claude.exe.old.1795116108051.41752` |
| D-J | 原主人自續跑自動記 `.resumed` | CSA §1 22:54：park 失敗後冷叫醒閘仍視本包「已封存」而誤推 |
| D-K | 「會自動繼續」須同時貼主載具（背景任務 id＋預定醒來時刻）與備援（NextRunTime）兩份憑證 | CARC R-9：18:29 只貼了外部憑證，而它恰是這情境最弱的一層 |

### 0.3 SD 代決（r3；主控／掌舵者可隨時以 T1 推翻）
| 代號 | 決定 | WHY |
|---|---|---|
| S-1 | `k(D)＝max(0, ceil((D + s − L_idle) / T_kw))`，`L_idle＝50` | QA P3-1；最後一段 ≤ 50 ＜ 55（harness 閒置壓縮）＜ 60（快取） |
| S-2 | `V(k)＝(k + W_CLOSE)·ping_pp ＋ DETECT_MIN·burn`；**`W_CLOSE＝4`**（r2 為 2） | r3 收尾多了封存與 park 兩步：TaskStop、`handoff --build`／寫主控層／`--finalize`、`park`、掛 keepwarm 約 4～6 個請求，每個讀一次 c；一次保溫 p(c) 已含兩次讀取 ⇒ 以 4 次保溫計約 8 次讀取＝上界 |
| S-3 | 未校準預設（r4）：`ping_pp(c)＝PING_PP_REF·max(1, p(c)/p(C_REF))`（`PING_PP_REF＝0.5`、`C_REF＝230,000`、`p(c)＝2·W_CR·c＋P_FIX`＝`keepwarm.py:86-89` 同式）、`burn 1.0 pp／分`、`AGENT_EST 5 pp`；輸出逐鍵標 `calibrated=no` | QA2 P3-2：r2 的 0.5 上界量自 c≈23～31 萬，固定值到 43 萬並不保守；以 p(c) 比例放大＝每次保溫實際讀的 token 量成正比，`C_REF` 取量測區間下緣 ⇒ 區間內恆 ≥ 實測、區間外隨 c 線性上升（偏保守的方向）。AGENT_EST 納入校準（QA P3-2）。區間外單點（2026-11-21 真機，§15 E9；r6 依主控核對實數改正）：c≈44 萬實付 5 次 ping、89→94＝5pp（首段含收尾回合）⇒ 平均上界約 **1.0 pp／次**，**高於**縮放值 0.916 約 9%（讀數為整數、每段量化誤差 ±1pp，不足以否證也不足以佐證）——S-3 在此點**未證明偏保守**；正確性不靠它：V 另含 W_CLOSE＝4 與偵測項（本例實付 5 ≤ V 12.24），上線前由 S-15 校準閘把值換成實測，§0.4-9 待主控決定是否先調高 `PING_PP_REF` |
| S-4 | 校準只印建議值，不寫回 | 量測不接閘門 |
| S-5 | 階段只剩 `none／free／nodispatch／close／wall`；`park --wall` 與 `mode=wall` 撤除 | r3 起收尾一律「封存＋park＋keepwarm」，付得起與否由 keepwarm 啟動時自行判（單跳或跨重置），不需要第二個 park 模式與黏性 |
| S-6 | 寬限 `BACKUP_GRACE_MIN＝10`、讓路觀察 `OBSERVE_SEC＝180`（程式常數） | 寬限蓋過「主載具醒來→主控那一回合寫出記錄」；觀察期蓋過「機器睡醒時排程器 StartWhenAvailable 與 keepwarm 同時到點」的競態（§7.3） |
| S-7 | 牆中靜音＝sessionctl 全部 Stop 推回＋`check_pending_handoff` 三種推回；keepwarm 在牆中不結束（延到 reset＋s） | QA P2-4①；T923／T926：保溫在牆內醒 ⇒ 429 |
| S-8 | `nodispatch`／`close` 期間完成閘不推 `drive`、OIR 讓路不關 keepwarm | QA P2-4② |
| S-9 | 唯讀動詞 `sessionctl quotawall`；`status`／`park --status` 加主載具列 | 主控與 E2E 的現查口 |
| S-10 | 備援的 RESUME 在同 sid 活窗存在時用 `claude -r <sid> --fork-session` | `claude --help` 現查：`--fork-session  When resuming, create a new session ID`；新 sid 承接同一段歷史，不違反「同 sid 不得兩行程寫同一份逐字稿」（R217 §7.1 的不變量）而免殺窗 |
| S-12 | 跨包欄名與讀取函式只住葉模組 `tools/lib/sessionctl/qw_schema.py`（只 import 標準庫）：holder 增欄 `wake_at`／`mode`／`target_source`、park 標記 `primary_wake_at`／`primary_source`（r5）／`backup_fire_at`／`close_stuck_window`／`desktop_notify`、痕跡事件名 `session_switch_spawning`、意圖期限常數 `SPAWN_INTENT_TTL_SEC`（r5，S-13）、保溫帳 `last_ping_pct`／`last_ping_at`／`ping_costs` 與 `ping_costs(row)`（r7，S-25）；`holder.py` 增欄與 `seal._spawned` 認意圖記錄也在 Q1 | QA2 P2-5（鐵律七：欄位的生產端 Q2／Q3 與消費端 Q1／Q2／Q3 分屬並行包）；葉模組同時解掉「quotawall 匯入 park、park 又要讀 quotawall 常數」的循環匯入（結構正解，不靠函式內 lazy import） |
| S-13 | keepwarm／watch 在**每一個**叫醒時刻（ping、到目標、defer 後）先以 `seal.handed_over(sid)` 重判；已交棒 ⇒ `KEEPWARM_VERDICT=handed_over`（rc 0、不計 pings、不呼叫 `mark_resumed`），處置「本窗已交棒：不得動工作樹，結束回合」。park job 在呼叫任何 spawn **之前**先寫 `session_switch_spawning` 意圖記錄；`seal._spawned` 認 `spawning`（其後同 attempt 有失敗列者不算）與既有 `spawned`（`ok` 為真）。**r5：意圖有期限**——`spawning` 只在其 `at` 起 `SPAWN_INTENT_TTL_SEC`（＝`max(handoff.SPAWN_WAIT_SECONDS, park_cli 續跑等待秒數)＋60`，現值 90；常數住 `qw_schema`，測試釘「≥ 兩個等待常數＋30」）內算交棒；逾時且同 attempt 沒有 `spawned ok=True` ⇒ 不算交棒。哨兵把「標記非終態（armed／job 執行中）＋過期意圖」視同 `failed` 接手並出聲（§7.6） | QA2 P2-3：讓路上限後或 S6 判卡死後，舊窗 keepwarm 晚醒會判 `resume`、§8 觸發 1 又在已 spawn 的包上寫 `.resumed` ⇒ 兩個視窗動同一棵工作樹。意圖先寫，才沒有「spawn 已開窗、痕跡還沒落」的競態窗。QA3 P2-6：job 在寫下意圖後、終態列前崩潰／被殺／重開機 ⇒ 永久 `_spawned`：舊窗判已交棒、標記又非 `failed`、哨兵不接手＝無聲零駕駛（違反 R-4.5.11-4）；期限＝spawn 自身等待上限＋寫痕跡餘裕，逾時仍無成功列即可確定 job 已死 |
| S-14 | 平台維度：macOS 無自動開窗備援（`park_cli.py:332` 非 win32 一律拒 spawn）。mac 的 park job 到點仍跑讓路判準，未讓路則直接記 `attempts=[{route, attempted:false, reason:"platform_unsupported"}]` 進失敗鏈終點出聲；park／keepwarm／status 照實印 `backup=absent(platform)`；keepwarm 在 darwin 每 ≤10 分印一行心跳（零 token）；自動重開登 OI（§17） | QA2 P2-4：CARC L63「mac 記憶體壓力且閒置 ≥30 分背景指令會被收」打中 single／chain；R-4.5.11-1「每格非空」、R-4.5.11-4「失敗不得無聲」。否決 mac 以 launchd `claude -p -r` 無頭續跑：同 sid 可能仍有活窗＝兩個駕駛；加 `--fork-session` 則等於把互動工作交給無人窗口（S4 語意），兩者都比「出聲＋OI」差（§14） |
| S-15 | 校準為上線前必要：PRD §16.6 本列轉 ✅ 與 Q7 結案前置＝真本機 `waste_census --calibrate-quotawall` 三鍵皆有建議值，且主控把值寫進 `env.shared`（Q7 commit，附 WHY 與區間數）；區間不足 ⇒ Q7 不結、OI 留著，上線期間以 S-3 縮放預設運作 | QA2 評估④；S-4「量測不自動寫回」不變——寫回是人審過的 commit，不是量測副作用 |
| S-16 | 既有 `park.stop_verdict`（短窗 ≥ 準備門檻推 park）：quotawall 判得出階段（free／nodispatch）時**不推**；`close` 走 §6.2；`none`（量不到）維持既有 | QA2 P3-4；D-B「額度照樣用到接近滿」——free／nodispatch 推 park 等於回到 r1「一進準備帶就收」 |
| S-17 | 到點 job 只吃標記資料與 argv：殺窗開關 `close_stuck_window`、桌面通知偏好 `desktop_notify` 在 `park` 登記當下由登記行程環境寫進標記；job 行程環境不讀這兩鍵（R218-B 排程 job 環境允許表 `job_env_argv(env, sandbox=)`：DIR 鍵＋`SESSION_SWITCH_MODE`＋通知只准空＋`SENTINEL_OFF` 只准 `1`，經 argv 帶過排程邊界；**r6 對齊 SE D-20 r4：不允許值只在沙盒目標拒絕登記；正式目標不轉送該值、登記照常**——掌舵者自行開 `AUTOSDD_DESKTOP_NOTIFY=1` 時，正式 `park` 照常登記、原值寫進標記 `desktop_notify`，argv 不帶通知鍵；SE §10.2.1 X-14／X-15）；argv 帶來的通知「關閉」值與標記取 AND。SE 產品面 L1 拒絕（fire 站點與 spawn 站點兩種）**永不進失敗鏈**（§7.0、§7.5-1a） | 與 R218-B 相容（主控裁示）；排程器不繼承環境，舊稿「讀自 job 行程環境」在新允許表下恆為空。r6：SE 第三輪 QA P2-3 指出 r3 的 D-20 對正式目標也拋例外，與本條「正式登記寫通知原值」衝突，兩稿同改 |
| S-18 | **主載具憑證**＝payload `background_tasks` 有 running 的 keepwarm／watch shell ∧ 本 sid holder 列 `is_live` ∧ `wake_at` 在未來 ∧ `mode∈{chain,single}`（帶目標；`periodic` 不算）。成立時：①半路停工判準（`midwork.background_idle`）把該 shell 視為「會叫醒主控做事」的事件源、不判半路停工；②「缺 park」推回（§6.2 閒置側、`none` 階段的既有 `park.stop_verdict`）對**同一短窗視窗**（r5，見下）**至多推一次**，其後改 `systemMessage` 一行「備援缺席：…」（R-4.5.11-6「只有一份就照實寫另一份缺席」），閂鎖＝`trace_dir()/quotawall/<sid>.json` 記 `{reset, pct, at, grace_task_ids}`（讀寫函式 `quotawall.latch_seen／latch_mark`，Q1）。**r5 視窗身分（QA3 P2-3）**：`quotawall.same_window(latched, reset_now, pct_now, now)`＝非「已翻新」；已翻新 ⇔ 讀數已降（`pct_now < latched.pct`；同一視窗內伺服器讀數單調不減，降＝換窗）∨ `now ≥ latched.reset＋LATCH_RESET_TOL_MIN`（60 分；閂鎖時觀測的 reset 已過一小時以上，必屬新窗）；讀數量不到時只用後一條。reset 觀測值本身漂移（±5 分、+70 分）不改視窗身分——鍵不再是 reset 精確值。**r5 競態寬限（QA3 P3-7）**：holder 缺席但 payload 有 running 的本 sid keepwarm shell（命令列含 `keepwarm`＋`--sid <sid>`）⇒ 同一背景任務 id 只寬限一次 Stop（id 記入閂鎖檔 `grace_task_ids`），視同主載具在跑；第二次仍無 holder ⇒ 不成立（防 holder 永久寫不進而長期壓住推回） | **暴露證據（真機，2026-11-21 01:2x～04:16，sid 4a45bc75；scratchpad `keepwarm2～6.log`、`RESTART_POINT.md` L76～L77）**：主控以現行 keepwarm 鏈跨 reset：保溫帳 k=1～5 為付費 ping（各次後短窗讀數 91、92、93、93、94），k=6（04:16）醒來時已 reset；共 6 次叫醒（r6 依主控以 Stop 守衛讀數核對改正），每次叫醒後 Stop 都被額度停工守衛推回要求 park（不認 keepwarm）、半路停工閘也因 `roster.is_supervision_shell` 把 keepwarm 排除而推回——每次 ping 多付一個推回回合。帶目標的 keepwarm 到點會判 `resume` 叫醒主控續工，本質是事件源；`periodic` 只保溫不續工，維持排除 |
| S-19 | 提前重置（r5 改寫）：計畫帶**參照**（`ref_reset`、`ref_pct`）＝計畫當時觀測的短窗 reset 與讀數；chain／single 的任一叫醒時刻（ping 或 defer 中每輪）先讀短窗，`quotawall.early_reset(ref, obs)`＝`ref_reset` 非空 ∧ 觀測 reset 晚於 `ref_reset` ∧ **觀測讀數 < `ref_pct` 且 < 100**（讀數已降）⇒ 直接判 `resume`（該叫醒時刻不 ping、不計 pings）。只有 reset 變晚而讀數未降（V-W4：估早了、視窗沒翻）⇒ 照原計畫（到目標時照 §5.5 defer 規則）。**defer 時參照更新**為（新 reset, 該次讀數）——否則 defer 後下一輪必判 resume。同一視窗內觀測讀數上升時 `ref_pct` 跟著取最大值（ping 自己會推高讀數）。**適用範圍**：`target_source=reset`，或 `target_source=park` 且標記 `primary_source=reset`（park 以短窗 reset 登記，含 `--why`）；`primary_source=at`（`park --at` 的承諾時刻）⇒ `ref_reset` 為空、不適用；讀不到照原計畫 | 同一實證：01:2x 讀到 reset 約 05:30，04:16 那次叫醒時讀數已翻新——觀測值與估計可差 70 分以上（只用觀測值，§3）。QA3 P2-1：「reset 晚於計畫」單獨成立也涵蓋「本來估早了」——不加讀數條件會在牆內叫醒（429，E4）或牆前續工撞牆；讀數已降是換窗的充分條件（伺服器讀數同窗單調不減）。QA3 P2-2：r4 的 close 流程一律登記 park ⇒ `target_source=park` ⇒ S-19 永遠停用，正是今晚情境；短窗 reset 登記的 `primary_wake_at` 只是觀測值的轉抄、不是承諾，只有 `--at` 是 |
| S-20 | fork 成功判準（r5，QA3 P2-4）：`spawn_resume(fork=True)` 的成功憑證**只認**「spawn 之後專案目錄出現的新 jsonl，且檔名 stem ≠ 原 sid」∧ 行程仍活；原逐字稿變大**不算**（fork 前提就是同 sid 舊窗還活著、會自己寫原逐字稿）。成功 ⇒ 寫 `session_switch_spawned`（`ok=True`、`handoff`＝包、`sid`＝原 sid、`new_sid`＝新檔 stem、`route=fork`），**不**呼叫 `mark_resumed`；失敗 ⇒ 同 attempt 寫失敗列、進 §7.5 另一路。普通 `-r`（無活窗）維持既有 `grew()` | `park_cli.py:351-353` `grew()`＝「原逐字稿變大 ∨ 有新檔」、`:367` 無條件 `mark_resumed`：舊窗或 harness 寫原逐字稿即假成功 ⇒ `handed_over` ⇒ 舊窗被告知已交棒而新窗沒起來＝零駕駛 |
| S-21 | `handoff.spawn` 兩個既有副作用（r5，QA3 P2-5）：①解除哨兵改在**驗證成功之後**（現行 `handoff.py:448` 在開窗後、驗證前呼叫 `_disarm_sentinel`），失敗不解除——所有呼叫端同一語意（互動 `--spawn` 失敗時保留哨兵也無害：哨兵只認撞線與 park `failed`）；②`_duplicate_refusals`（`:371-397`）只把 `ok is True`（600 秒內或行程仍活）或「行程仍活且未被重用」的 `session_switch_spawned` 算成已開過；`ok is False` 且行程已死 ⇒ 不擋；無 `ok` 欄的舊格式列照舊規則（保守） | ①FRESH 失敗時哨兵已被拆 ⇒ §7.6 沒有接手者（E2E-QW-15 期望的 `sentinel_park_takeover` 結構上不成立）；②失敗列也擋 600 秒 ⇒ 哨兵 10 分內接手時 FRESH 必被拒。只改 park 路徑會讓同一函式兩種語意（兩個家），故全面改 |
| S-22 | （r6）spawn 站點 L1 拒絕（`RC_SIDEEFFECT_REFUSED`）＝終局 `refused`：該次 `park_attempt` 照記、意圖寫失敗列、不走另一路、不出聲、哨兵不接手（§7.5-1a、§7.6）；交叉介面字面一律引用 SE §10.2.1 | SE 第三輪 QA P2-2：r5 §7.5-1「FRESH 前置拒絕也算一次失敗」會把 spawn 站點的 L1 拒絕也當失敗而改走另一路，另一路的替身先記一行 ⇒ SE MU-SE-25「替身 0 行」必錯，且等於替不合法目標再試一次；以專屬 rc 區分「此路走不通」與「不該叫醒」。AT-QW-69③、MU-QW-44 |
| S-23 | （r7，QA4 Q-P2-1）**讀數年齡**：`plan` 與每個叫醒時刻取短窗讀數時一併取 `reading_at`（＝該讀數由伺服器回應的時刻，`pace_state` 的量測時戳；不是讀快取的時刻），`age＝now − reading_at`。①`age > QUOTA_CACHE_TTL_SECONDS＋watch.POLL_SECONDS`（現查 210 秒，與 `DETECT_MIN` 同一組常數）⇒ 同步補量一次（零 token 的 `/api/oauth/usage`，既有 `quota_gate.py:892` 路；E2E 的端點＝T5 替身）；②補量成功 ⇒ 用新讀數、`stale=no`；③補量失敗 ⇒ `R_eff＝max(0, R − ceil(age/60)·burn)` 保守外推，階段判定與輸出一律用 `R_eff`，`QUOTAWALL_PLAN` 印 `stale=yes reading_age=<秒>`；④讀數所屬視窗的 reset ≤ now（舊窗讀數）⇒ 量不到（`stage=none reason=stale_window`），不外推；⑤keepwarm 與 watch 的每個叫醒時刻（ping、到目標、defer 每輪）先做①～④再判；⑥**早於閂鎖時刻（`latched.at`）或計畫參照時刻（`ref_at`）的讀數不參與 `same_window` 與 `early_reset`**，視同沒有新讀數：`same_window` 回真（不算換窗）、`early_reset` 回假、`ref_pct` 不更新。外推只往收緊方向（R 變小），不會讓擋派或收尾晚觸發 | **暴露證據（真機 §1 E10，2026-11-21 05:2x，sid 4a45bc75）**：短窗讀數停在 86%，實際已 95%，一次跳 9pp。V 的偵測項 `DETECT_MIN·burn` 只在「讀數年齡 ≤ TTL＋POLL」時成立；年齡沒有上界時，c≈48 萬、D≈205 下讀數 86（R 14 ≤ L 16.96）判 `nodispatch`，實際 R 5 早該 `close`，等看到真讀數時 R 已 < V，只剩 single，reset 時冷重寫。同一個陳舊低讀數還會讓 S-18 的 `same_window` 以「讀數已降」誤判換窗而多推一次、讓 S-19 誤判提前重置。補量把年齡壓回 DETECT_MIN 的假設之內（消除成因）；補不到時外推是保守正解（寧可早收、不晚收）；舊窗讀數不外推（跨窗的燒速沒有意義）。AT-QW-76／77、E2E-QW-29、MU-QW-45／46 |
| S-24 | （r7，QA4 Q-P2-2）**有目標時保溫預算只算未來**：`affordable＝R ≥ k·ping_pp ∧ k ≤ n*(c)`（`n*`＝`keepwarm.n_star`＝`floor(W_CC1·c/p(c))`，即「k 次保溫總價不超過一次冷重寫」；k＝從本次錨點到目標還要付的次數）；保溫帳的歷史 `pings` 不進式子；`cap`（`pings ≥ n*`）只在 `periodic`（無目標）適用。保溫帳歸零條件由「真人提示」增為三條：①真人提示（既有，`human_mark`）；②**主控真工作記錄**（r8 收窄，QA5 QW5-P2-2）：錨點之後主鏈出現一筆 assistant 記錄，其所屬回合含至少一個「**非唯讀且非監督**」的 `tool_use`，或該回合由 harness auto-continuation 開啟。「非唯讀」重用 `midwork.READONLY_TOOLS`（import、不複製；`Read`／`Grep`／`Glob` 以外皆非唯讀，與半路停工的狀態佐證同一判準）；「監督」排除兩類：(i) harness 讀背景輸出的工具（`TaskOutput`／`BashOutput`）；(ii) shell `tool_use`（PowerShell／Bash），其指令以 `;`／`&&`／`||`／換行切段後**每一段**都屬下列之一：keepwarm／watch 啟動（`roster.KEEPWARM_CMD_RE`／`WATCH_CMD_RE`，import）、`sessionctl.py status`、對本 session keepwarm／watch 輸出檔（其啟動指令的重導目標或背景任務輸出路徑）的唯讀讀取（`Get-Content`／`gc`／`cat`／`type`／`tail`／`Select-String`，可接 `Select-Object` 管線）。任一段不屬、或指令解析不出 ⇒ 該 `tool_use` 算真工作（判不出偏「歸零」：寧可 `periodic` 多付一段，不讓真工作後的閒置提早 cap 而冷）。判準住 `keepwarm.work_mark(transcript)`，與 `human_mark` 同型：標記變了即歸零；③**視窗翻新**：keepwarm／watch 判 `resume`（到目標）或 `keepwarm_early_reset` 時，先把 pings 歸零再寫帳 | 目標已知時，過去的 ping 是沉沒成本；ski-rental 上限 n* 是「終點未知」時的競爭比界，拿來判「終點已知、還要付幾次」的鏈，會把上一段閒置的花費重複計入。**暴露證據（真機 §1 E10）**：04:16 原窗自動續工（沒有真人提示）⇒ 第一段 6 次叫醒仍留在帳上；05:2x 進 close 時依 r6 式 pings 6＋k 4＝10 > 9 ⇒ single，距 reset 約 3.5 小時必冷；實際 07:20 keepwarm 判 `cap k=9`、距 reset 仍 89 分。`periodic` 維持 R216 cap（終點未知，ski-rental 才是對的界）。**r8（QA5 QW5-P2-2）**：r7 的②把「keepwarm／watch 重掛以外的任何 `tool_use`」都算真工作；keepwarm 輸出導檔，主控每次 ping 叫醒都要讀末行 `KEEPWARM_VERDICT`（T L2906 即「`Get-Content log ; keepwarm`」同一呼叫），這種回合會讓每次 ping 都歸零、`periodic` 的 cap 永不觸發、人離開期間無限付費——收窄為「非唯讀且非監督」即消除成因，而 cap 判準本身與 R216 相同（REQ-QW-23）。AT-QW-78／79／81、E2E-QW-07(c)、E2E-QW-30、MU-QW-47／48／51 |
| S-25 | （r7，QA4 Q-P3-1；**r8 改量測窗口**，QA5 QW5-P2-1）**ping 實測取大**：Δ＝**相鄰兩次 `ping` 叫醒時刻的讀數差**。keepwarm 在每個 `ping` 叫醒時刻先依 S-23⑤取讀數 x（陳舊即補量），若保溫帳已有上一筆 `last_ping_pct`／`last_ping_at`，且同時成立：兩筆皆 `stale=no`、同一短窗視窗（reset 差 ≤ `LATCH_RESET_TOL_MIN`）、`x ≥ last_ping_pct` ⇒ `Δ＝x − last_ping_pct` 寫進保溫帳 `ping_costs`（保留最近 5 筆）與痕跡 `keepwarm_ping_cost`；不論記或不記，隨後把 `last_ping_*` 更新為本次（x、now）。保溫帳因 S-24 三條件任一歸零（真人提示、真工作、視窗翻新）時**一併清空 `last_ping_*`**，故區間內有真工作、真人提示或換窗的段結構上不會被記（不另存標記，欄名仍是三個）。**重掛啟動時不取讀數算 Δ**；之後同 sid 的 `plan` 用 `ping_pp_eff＝max(ping_pp(c), mean(ping_costs 最近 3 筆))`（一筆都沒有＝縮放值），輸出印 `ping_pp_src=scaled|measured`；只抬不降；`calibrated` 欄照舊是 `no`、不寫回設定（S-4）。**不推翻** `PING_PP_REF＝0.5`（主控裁示：上線前由 S-15 校準閘換成實測值） | 兩個獨立點（E9 約 1.0 pp／次 @ c≈44 萬、E10 約 1.33 pp／次 @ c≈48 萬〔95→98→98→99〕）都高於 S-3 縮放值（0.916、0.995）；整數讀數每次量化誤差 ±1pp，單次 Δ 可為 0～3，故取最近 3 筆平均、只抬不降。Δ 也可能含同帳號其他 session 的用量，取大是偏保守的方向。**r8 WHY**：r7 以「重掛啟動讀數 − ping 叫醒讀數」為 Δ，兩者只差幾十秒；ping 時刻依 S-23 剛補量，重掛時讀數年齡 < 210 秒不補量、讀到同一筆快取（伺服器用量本身亦有延遲）⇒ 正式環境結構上 Δ≈0，又因只抬不降而恆停在縮放值，REQ-QW-66 失效。相鄰兩次 ping 叫醒相隔 T_kw，兩筆都經 S-23 補量，差值恰為其間那一個 ping 回合（叫醒→重掛）的成本；區間內有真工作或真人提示時差值混入工作用量，故不記（同 E9 91→92→93 的讀法）。代價：第一筆實測要到第二次 ping 叫醒才有。AT-QW-80、E2E-QW-30(c)、MU-QW-49／50 |
| S-26 | （r8，QA5 QW5-P3-1）**不採「貪婪續付」**（已在 chain 中只要 `R ≥ ping_pp_eff` 就續付、付不起才一跳到目標）；維持每次重掛依 S-24 重算 `chain`／`single` | 續付的 ping 只在「付完後剩餘一跳 ≤ `L_idle` 50 分」時換得熱快取，而「付完能否到目標」正是 S-24 的 affordable 式；已判付不起時續付，剩餘一跳仍 > 50 分（照樣冷），已付的 ping 全數沉沒（每次 p(c)，c≈48 萬約 10 萬加權單位，另耗短窗 pp 使收尾更早撞牆）⇒ 期望值為負。中途退 single 的殘餘（單筆量化偏高觸發誤退）照實登記於 §15，以「近 3 筆平均」逐步收斂與 S-15 校準閘承接，不加守衛（無第二件暴露證據） |
| S-11 | 失敗出聲不改使用者通知偏好：桌面通知照 `AUTOSDD_DESKTOP_NOTIFY`（預設關）；必達管道＝handback＋SessionStart 公告＋UserPromptSubmit 提示＋`quota_escalation.notify_queue_path()` 佇列 | `quota_escalation.py:547-548`「預設就不敲，是使用者的直接指令」；「不得無聲」以下一個人眼必經的兩個入口（開新窗、在任一視窗打字）保證 |

### 0.4 待主控決定（開放問題）
1. **R217 附錄 A-11 第⑥列「park（§2.17）✅」**：本次 22:42 事件使該列不成立；R217 收尾窗口落款 A-11 時，⑥列應改寫 OI id 指向本稿（或維持未結），否則 §16.6 會同時出現「park ✅」與本稿「park 失敗鏈未結」。屬 R217 持有面，本稿不改。
2. ~~SE（R218-B）PRD 修訂表列「兩桶」字樣與 §16.6 ⏸~~（r4 現查已解：R218-B r2 列改寫為「v2.1.24 由 R218 QuotaWall r3（含 R218-C）佔用」、§16.6 改〔OI〕）。版號定稿：**v2.1.24＝R218 QuotaWall（r3 含 R218-C；r4 為同列就地改版、不另佔號）；v2.1.25＝R218-B**；v2.1.23 由 R217 預留。
3. ~~`claude -p` 是否在背景任務結束時重新呼叫模型~~（r4 已有實證，QA2 P3-1）：RV-KW6（`tools/lib/realverify/cases/sessionctl_keepwarm.py:239-268`）在 `-p` 逐字稿驗到背景 keepwarm 的完成通知 `completed (exit code 0)` 與其後模型回覆。TCS 另設約 2 分鐘的前置案例 E2E-QW-27，凡依賴此性質的案例先跑它；不成立判 ENV、登 OI，不得改走真開窗（本輪任何 E2E 不真開窗）。
4. ~~未校準預設~~（r4 主控裁示：校準為上線前必要，S-15）。
5. **真 OS 睡眠的 E2E**（V-W2 真機半）會讓掌舵者電腦睡著，預設不跑（opt-in `AUTOSDD_RV_ALLOW_SUSPEND=1`，未開判 ENV）；常態以「凍結 keepwarm 行程跨過截止」的真行程案例代驗（§16）。
6. **（r4 新增）真互動視窗半一律不跑**（主控裁示：任何 E2E 不得真開窗）：V-W1 數小時單跳的互動半、V-W3 長壽互動窗、V-W8 互動 fork 開窗改由上線後觀察指標（M-K8「跨重置成功」、M-K9）承接，登 OI 未結（§17），不以 `-p` 常態半宣稱已驗。
7. **（r4 新增）macOS 自動重開**（S-14）：mac 上 S1／S3／S5／S6 備援只剩出聲；是否補 mac 的開窗載具（例如 `open -a Terminal` 帶 `claude -r --fork-session`）待主控決定，登 OI。
8. **（r5 新增；r6 改寫）R218-B 介面**：r6 起兩稿交叉介面（替身載體與三模式、`--claude`／標記 `claude` 欄、fire／spawn 兩種 L1 拒絕與 rc、`park.STATUSES`、`park_attempt` 計數、`backup_fire_at`、租約、job 環境轉送與通知開關、QW 新站點進 `SITES`、沙盒工作樹乾淨、黃金序列重釘）一律以 **SE §10.2.1 X-1～X-22**（r7：SE r5 補 X-19 park 附帶武裝哨兵、X-20 痕跡名與 reason 詞彙、X-21 `ctl_env(arm_sentinel=True)`、X-22 `park --status` 加列）為準，本稿不另抄值；**凍結前置＝兩稿同一 commit 凍結，主控以該表逐列核對兩稿座標**。以下為 r5 時的對齊紀錄（值與 X 表一致）：載體＝`<家>/fakeclaude.mode` 檔（SE §4.4），值 `resume_ok`（RESUME 路：argv 含 `-r <sid>` 且不含 `--fork-session`，追加原 sid 逐字稿）／`fresh_ok`（fork 或 FRESH 路：新建 uuid 逐字稿）／`fail`（立即以 `fakeclaude.rc` 結束）；成功模式存活 `fakeclaude.sleep`（缺席 20 秒）；「成功模式遇不適用 argv ⇒ 照 fail」；哨兵接手的執行檔讀 park 標記 `claude` 欄（SE §10.2-8，SE S2 讓 `park` 登記時寫入）；L1 新判準 `sandbox_real_exe`（沙盒目標∧執行檔不在沙盒家目錄∧`window≠true` ⇒ 終局 `refused`，不進失敗鏈；r6：在 spawn 站點命中時回 `RC_SIDEEFFECT_REFUSED`，§7.5-1a）。
9. **（r6 新增）未校準 `PING_PP_REF` 是否先調高**：E9 單點平均上界約 1.0 pp／次 @ c≈44 萬，高於 S-3 縮放值 0.916 約 9%（在量化誤差內）。選項：(a) 維持 0.5（S-15 校準閘上線前必換成實測值；V 的 W_CLOSE 已吸收本例差額）——SD 建議；(b) 先調為 0.55（縮放後 44 萬 ≈1.01）使區間外單點不再高於預設。兩者皆不改公式與判準結構，只改一個常數與 AT-QW-05／07／62、E2E-QW-01／22 的期望值。**（r7 補）第二點**：E10 c≈48 萬實付約 1.33 pp／次（95→98→98→99），高於縮放值 0.995 約 34%——兩個獨立點皆高於 S-3。主控裁示仍維持 (a)；r7 另加 S-25（keepwarm 記錄每次 ping 的實測讀數差，計畫取 max(縮放值, 實測)），使上線到校準之間的偏差在同一 sid 內自行收斂，不必先改常數。

### 0.5 掌舵者原裁決與改版理由（D-E，沿用 r2）
- 原裁決：「1. 到 85% 就封存換手…**不必重寫大上下文**；額度照樣可用到接近滿。保溫在注定失敗時自動不排。 2. 另外預留保溫額度…**只有在重置距今 1 小時內才有用**」（主控提供的選項文案）。
- 證據：F4 在今天的上下文量級選 RESUME 照樣冷重寫；harness 在 reset＋100 秒先續接；保溫可在牆前預付 k 次一路接到 reset（ARC §三、QA P2-1）。
- 改版保留三個意圖：額度用到接近滿（§6.1 擋派線）、注定失敗不付費（r3：單跳＝零付費）、接近上限停派留額度（主策略本體）。

### 0.6 R218-C 撤回／改語意清單處置（CARC §三 R-1～R-9）
| # | 既有設計 | 處置 | 本稿座標 |
|---|---|---|---|
| R-1 | r2 跨重置保溫為主 | 保留並擴充：付不起退單跳；park 與 keepwarm 分層 | §5、D-C、D-F |
| R-2 | r2 S-10「主策略不同時掛 park」 | **撤回**：同時掛，fire＝醒來＋寬限，讓路 | §7.1、§7.3、S-6 |
| R-3 | R217 §7.1「park 到點先關再開」（`oldwin_park.resume_gate`） | **改語意**：活窗不關，fork／FRESH；殺窗只在卡死＋登記時 `AUTOSDD_PARK_CLOSE_STUCK_WINDOW=1` 寫進標記（S-17）＋R217 五條件；跨 sid `--ack` 後關舊窗不受影響 | §7.4 |
| R-4 | `procstop.CLOSE_IMAGES` 精確名 | 家族比對；`image_not_allowed`／`open_failed` 改可降級 | §9 |
| R-5 | `_cmd_fire` gate=fail 寫死 `spawn_rc=1` | 刪除；結局記 `attempts`；失敗鏈 | §7.5 |
| R-6 | `finish` 失敗即自拆、無排程 | job 照舊一次性自拆，但失敗交哨兵接手（§7.6）並出聲；「失敗＝無人知」消失 | §7.5、§7.6 |
| R-7 | 哨兵只認撞線 | 增認 park 標記 `status=failed` | §7.6 |
| R-8 | R218-B 隔離 | （r6：交叉介面以 SE §10.2.1 為準）本稿全部 E2E 在 SE 沙盒、經 SE L2 帳登記；**r4：任何 E2E 不真開窗**，spawn 的正控一律 SE 假 `claude`（沙盒 bin 目錄經 argv 帶過排程邊界；記 argv；`<家>/fakeclaude.mode`＝`resume_ok`（RESUME 路）｜`fresh_ok`（fork 或 FRESH 路）｜`fail`，成功模式寫逐字稿並存活 20 秒以滿足 spawn 成功判準；**正控不以 rc 0 判**，正控案例讓 F4 選路可預期並斷言 `park_route` 的 route 與所設模式一致，失敗鏈用 `fail`；§0.4-8）；改名映像以沙盒 `claude.exe` 副本執行中改名重現 | §16、TCS §4 共通 |
| R-9 | park 憑證只有外部 | 雙憑證 | §10 |

**本節判準**：§0.2～§0.3 每個代決在 TCS 有對應 REQ 或 AT；§0.4 未刪除的各題在交卷時列給主控。

---

## 1. 問題與證據

| # | 現象 | 證據 | 代碼座標（本棒抽驗） |
|---|---|---|---|
| E1 | 準備帶 watch 有叫醒，處置交主控自由裁量 | T722／T747、T1588／T1607 | `watch.py:54` `DISPOSAL["quota"]` |
| E2 | 有在飛子代理時 park 閘不評估 | ARC R4 | `converge.py:120-123` |
| E3 | 冷叫醒閘對「已封存未交棒」只豁免 keepwarm shell | QA P1-1 | `converge.py:73-104`、`seal.py:259-268` |
| E4 | 保溫在牆內醒 ⇒ 429 | T923／T926 | `keepwarm.py:236-282` 到截止即 `record_ping` |
| E5 | 牆後推回送不出 | T1636、T1639 → T1645 | `park.py:286-327`、`check_pending_handoff.py:315-358` |
| E6 | 準備帶仍可派工 | T808、T826 | `--pace` prepare 帶 cap 2 |
| E7 | harness 自動續接是實際救援者（撞線型） | T931、T1656 | `transcript_activity.py:424-459` |
| E8 | 完成閘 `drive` 與 OIR 讓路吃掉／關掉預留 | QA P2-4② | `check_pending_handoff.py:340`、`sessionctl_guard.py:76-83` |
| C4 | park 標記有效 ⇒ 保溫不掛（互斥） | CSA §1 19:14:30；CARC C4 | `keepwarm.py:186-187` |
| C6/C7 | RESUME 前先關同 sid 活窗；映像被自動更新改名 ⇒ `image_not_allowed` | OW 末行 22:42:01；映像全路徑 `C:\Users\wuwei\.local\bin\claude.exe.old.1795116108051.41752` | `park_cli.py:416`、`oldwin_park.py:63-87`、`procstop.py:227`、`procstop.py:259` |
| C8/C9 | 映像拒絕被當 terminal、無重試 | CARC | `oldwin.py:339-372` |
| C10 | gate=fail 寫死 `spawn_rc=1`，`spawn_resume` 根本沒被呼叫 | PK outcome；UL caller `_cmd_fire:424` | `park_cli.py:422-424` |
| C11 | 失敗只寫一份沒人讀的 handback、自拆排程、switch 痕跡沒有失敗列 | CSA §3 | `park_cli.py:276-290`、`382-386`、`433` |
| C12 | 主動停工無人接手：harness 不續接、哨兵只認撞線 | CSA §1 22:42～22:52 | — |
| D-J | park 失敗後原主人被叫醒，冷叫醒閘因包仍 `.sealed`＋live 誤推 | CSA §1 22:54（T2522～2540） | `seal.wake_package`；`forward.py:148` 留原窗時不記續跑 |
| E9 | （r4 新增，正面實證；r6 依主控核對實數改正）session 內背景等待跨 reset 可行：01:2x 收尾後短窗 89%、距 reset 約 245 分、c≈44 萬；現行 keepwarm 鏈保溫帳 k=1～5 為付費 ping，各次後讀數 91、92、93、93、94；k=6（04:16，n*＝9）醒來時已 reset、快取未冷、原窗續工 ⇒ 跨 reset 實付 **5 次 ping、89→94＝5pp（含首次收尾回合）、平均約 1 pp／次**；同時暴露 S-18 兩閘每次叫醒都推回、S-19 提前重置 | sid 4a45bc75 2026-11-21 01:2x～04:16；scratchpad `keepwarm*.log`、`RESTART_POINT.md` L76～L80（L80＝主控以 Stop 守衛讀數核對的實數） | `park.py:286-327`（不認 keepwarm）、`midwork.py:79-82`（排除 supervision shell） |
| E10 | （r7 新增，QA4）第二次跨 reset：①**陳舊讀數**——05:2x 短窗讀數顯示 86%、實際 95%（一次跳 9pp）；②**保溫帳跨段累計**——04:16 原窗自動續工、沒有真人提示，第一段 6 次叫醒仍留帳，07:20 keepwarm 判 `cap k=9`（ski-rental 上限）時距 reset 仍 89 分，主控改用 session 內背景等待到 reset＋3 分（牆鐘每 60 秒輪詢），08:53 原窗準時叫醒、額度已 reset（D-F「付不起就到點只醒一次」的正面實證）；③**ping 成本隨上下文放大**——c≈48 萬時每次 ping 0～3pp（95→98→98→99，平均約 1.33） | sid 4a45bc75 2026-11-21 05:2x～08:53；scratchpad `r218_joint_qa_brief.md`〈新真機實證〉、`r218_joint_specqa_report.md` Q-P2-1／Q-P2-2／Q-P3-1 | `park._pace_state`／`quota_gate.py:892`（讀數沒有年齡上界）、`keepwarm.py:154`（只真人提示歸零）、`keepwarm.py:255`（`pings ≥ n*` ⇒ `cap`） |
| T5 | 真機案例全 PASS 卻沒抓到：RV-WP52～54 未實作、FakeApi 映像恆為 `claude.exe`、RV-PR3 沙盒無活窗、RV-PR1 PASS 證據含 failed | CSA §5 | — |

---

## 2. 續航情境矩陣（規範性；PRD §4.5.11 承接）

### 2.1 載具
| 代號 | 載具 | 叫醒誰 | 前提 | 限制 |
|---|---|---|---|---|
| W1 | **keepwarm 單跳**（一路等到目標時刻才結束） | 本視窗主控，原地續 | 視窗行程活著；互動模式 | 官方：本機互動背景指令無時間上限；`-p` 有上限（`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`）；CC 退出即清除；**macOS 記憶體壓力下閒置 ≥30 分的背景指令會被收（CARC L63；Windows 無此條）**——darwin 每 ≤10 分印心跳行（「閒置」是否以輸出判未證，OI，S-14） |
| W2 | **keepwarm 跨重置鏈**（W1＋k 次付費 ping） | 同 W1，且快取不冷 | 同 W1＋預算付得起 k 次 | 牆內付不出（§5.4 延到 reset＋s） |
| W3 | harness auto-continuation | 被切斷的同 session | 撞線型 | 主動停工無效；睡眠逾約 30 分需 Enter（OBS-SI-283） |
| W4 | 外部排程 `claude -r <sid>`（無活窗）／`claude -r <sid> --fork-session`（有活窗） | 新互動視窗 | **Windows 限定**、mode=auto、交接包 live | macOS：job 照跑但只到出聲（S-14） |
| W5 | 外部排程 `handoff --spawn`（FRESH） | 新 session 帶交接包 | **Windows 限定**；交接包 finalize、工作樹保全 | macOS 同上 |
| W6 | 哨兵巡邏 | 撞線續航；r3 起另接 park `failed` | 哨兵已武裝 | 只讀逐字稿、零 token |

### 2.2 情境 → 主載具／備援／出聲
| 情境 | 主載具 | 備援（主載具寬限內沒動靜才動）——Windows | 備援——macOS（S-14） | 出聲 | 不得用 |
|---|---|---|---|---|---|
| S1 互動、視窗開著、**主動停工**（`close` 階段或 `park --why`）、短窗 | W2（付得起）／W1（付不起）——目標＝reset＋s；darwin 加心跳 | W4（F4＝RESUME；活窗 ⇒ fork）或 W5，fire＝目標＋10 分；失敗鏈 → W6 | `absent(platform)`：launchd job 到點跑讓路判準，未讓路即 `platform_unsupported` 進失敗鏈終點；W6 接手同樣只到出聲；OI | 失敗鏈終點（§7.5），兩平台相同 | 殺窗＋`claude -r` 作主路徑；mac 無頭 `-p -r` |
| S2 互動、視窗開著、**撞線** | W3（reset＋約 100 秒）；W1 已掛者在 reset＋s 醒（見到新記錄即判 `resume` 無事可做） | W6（既有）；若有 park 標記同 S1 | W6（既有 launchd 巡邏）；park 標記同 S1 mac 欄 | 同上 | 牆內叫醒 |
| S3 互動、視窗已關或電腦重開 | （主載具不存在：holder 行程已死） | W4（無活窗 ⇒ 普通 `-r`）或 W5，依 F4 | `absent(platform)`：同 S1 mac 欄；OI | 同上 | — |
| S4 無人（`AUTOSDD_UNATTENDED`） | 既有 planner／哨兵 FRESH 路 | — | — | 既有 | W1、W2 |
| S5 週窗（`park --at`，天級） | W1（同一目標，並掛）；darwin 加心跳 | W4／W5（WakeToRun），fire＝目標＋10 分 | `absent(platform)`：launchd 到點只出聲（Mac 睡著不會被喚醒，根 CLAUDE.md〈mac 已知邊界〉）；OI | 同上 | 只靠 W1 |
| S6 視窗開著但卡死（holder 活著、醒來時刻已過、觀察期內沒有任何記錄） | — | W4 fork 或 W5（不殺窗）；殺窗只在標記 `close_stuck_window=true`（S-17）且 R217 §7.1 五條件全成立 | `absent(platform)`：只出聲；OI | 同上 | 預設殺窗 |

**本節判準**：表內每格非空（AT-QW-60 以表驅動測試讀本節做成的常數表 `continuity.MATRIX`，鍵＝(情境, 平台)，空格即紅；`absent(platform)` 是合法值但必須連到出聲欄與 OI id）；S1～S6 每格至少一個 Windows E2E（TCS §6），macOS 欄由 E2E-QW-28 覆蓋（非 mac 宿主判 ENV、登 OI）。

---

## 3. 名詞與機械定義

| 名詞 | 定義（唯一真相源） |
|---|---|
| 短窗讀數 | `park.measured_short(state, now)`（伺服器原值；不吃攤提、配速床、趕工戳記） |
| reset | `park.reset_of(hits)`；解不出＝量不到；**只用觀測值**（不假設 5 小時） |
| R | `100 − max(短窗 pct)`；讀數帶 `reading_at`，年齡規則見 S-23（陳舊 ⇒ 補量；補不到 ⇒ 以 `R_eff` 外推、`stale=yes`；舊窗讀數 ⇒ 量不到）（r7） |
| D | `(reset − t)` 分；hook／watch＝現在；keepwarm 排程＝錨點 `keepwarm.anchor()` |
| s | `quota_messages.HALT_RESET_SKEW_SECONDS / 60`（現查 2） |
| T_kw | `keepwarm.t_kw_minutes()`（45、只准下修、下限 15） |
| L_idle | `quotawall.IDLE_LIMIT_MIN＝50`（keepwarm `--idle-min` 只准再下修，供 E2E 縮時） |
| k(D) | S-1；上下文 < `AUTOSDD_KEEPWARM_MIN_CTX_TOKENS` ⇒ 0 |
| p(c)、ping_pp、burn、AGENT_EST | p(c)＝`2·W_CR·c＋P_FIX`（`keepwarm.py:86-89`）；三鍵 env，空＝未校準：`ping_pp(c)＝0.5·max(1, p(c)/p(230,000))`（S-3）、burn 1.0、AGENT_EST 5。例：c≤23 萬 0.5；30 萬 0.639；30.9 萬 0.656；43 萬 0.896；48 萬 0.995。r7：計畫實際用 `ping_pp_eff＝max(ping_pp(c), 本 sid 實測近 3 筆平均)`（S-25） |
| V(k) | `(k + W_CLOSE)·ping_pp + DETECT_MIN·burn`；`W_CLOSE＝4`、`DETECT_MIN＝ceil((QUOTA_CACHE_TTL_SECONDS＋watch.POLL_SECONDS)/60)`（現查 180＋30 ⇒ 4） |
| L | `V(k) + AGENT_EST` |
| stage | 依序：`none`（量不到／reset 不明／模式非 auto 且非 notify／無人窗口）→ `wall` → `close`（R ≤ V(k)）→ `nodispatch`（R ≤ L）→ `free` |
| `wall_state` | 同 r2：①最後一筆切斷記錄之後無續接、無新真 usage；②主鏈最後一筆 assistant 為 `<synthetic>` 且含 `hit your`／`usage limit`；③短窗讀數 ≥ 100 且 reset 在未來；回 `{wall, reset, cold_at, source}` |
| 目標 `wake_target` | 依序：本 sid park 標記 armed 且其交接包 live ⇒ 標記 `primary_wake_at`；否則 stage ∈ {close, wall} 且 reset 已知 ⇒ reset＋s；否則無。r5 另回**參照** `ref`＝(`ref_reset`, `ref_pct`, `ref_at`)：來源 reset ⇒ (該 reset, 當下讀數, 該讀數 `reading_at`)；來源 park 且標記 `primary_source=reset` ⇒ (`primary_wake_at − s`, 當下讀數, 該讀數 `reading_at`)；`primary_source=at` 或無目標 ⇒ (None, None, None)（S-19 不適用）。`ref_at` 為 r7 新增（S-23⑥） |
| 預算判 `affordable` | （r7，S-24）有目標：`R ≥ k(D_anchor)·ping_pp_eff ∧ k ≤ n*(c)`——只算從本次錨點起還要付的 k 次，保溫帳歷史 pings 不計（沉沒成本）；收尾回合已付，不含 W_CLOSE。無目標（`periodic`）不用本式，照 R216 `pings < n*` |
| `handed_over` | `seal.handed_over(sid)`（單一家；r4 起 `_spawned` 另認 `session_switch_spawning` 意圖記錄，r5 起意圖只在 `SPAWN_INTENT_TTL_SEC` 內有效，S-13） |

**數值（未校準、c ≤ 23 萬，s＝2、T_kw＝45、L_idle＝50、W_CLOSE＝4）**：D≤48 ⇒ k＝0、V＝6；49～93 ⇒ 1、6.5；94～138 ⇒ 2、7；139～183 ⇒ 3、7.5；184～228 ⇒ 4、8；229～273 ⇒ 5、8.5；274～300 ⇒ 6、9。c 更大時 ping_pp 依 S-3 放大（例 c＝43 萬、k＝5：V＝9×0.896＋4＝12.06、L＝17.06）。**不變量（r4 改以 V 判）**：V ＜ 15（＝100 − 準備門檻 85）⇒ `close` 時讀數恆在準備帶內；V ≥ 15 時 `plan_lines` 印 `invariant=broken` 並 stderr 一行，判準照算（不偷偷改值）——正確性不靠它，`park` 前置另認 `stage=="close"`（§7.1）。r3 以 L 判，c 放大後 L ≥ 15 屬常態（43 萬即 17.06），會讓 stderr 變噪音，故改 V。

**本節判準**：`quotawall.py` 只從上表各真相源取值（AT-QW-04 以替換常數證明）。

---

## 4. 判準核心 `tools/lib/sessionctl/quotawall.py`（純函式、零 token）

| 函式 | 回傳 | 說明 |
|---|---|---|
| `plan(sid, transcript, env, now, *, read_quota=None)` | `Plan(stage, D, k, V, L, R, reset, ctx, calibrated, invariant, reason, reading_at, stale, ping_pp_src)` | 讀 `park._pace_state`；r7 依 S-23 判讀數年齡：陳舊 ⇒ 同步補量一次（`quota_gate.py:892`；E2E 的補量端點同為 T5 替身），補不到 ⇒ `R_eff` 外推、`stale=True`；舊窗讀數 ⇒ `none reason=stale_window`；`ping_pp` 依 S-25 取大 |
| `wall_state(transcript, now, *, read_quota=None)` | §3 | — |
| `wake_target(sid, transcript, env, now, *, marker=None, plan=None)` | `(epoch｜None, source∈{park,reset,none}, ref)` | §3；keepwarm、watch、park 共用；`ref` 見 §3（r5） |
| `early_reset(ref, obs_reset, obs_pct, obs_at)` | `bool` | S-19：`ref_reset` 非空 ∧ `obs_reset > ref_reset` ∧ `obs_pct < min(ref_pct, 100)`；任一輸入缺 ⇒ False（r5）。r7（S-23⑥）：`obs_at < ref_at` ⇒ False |
| `same_window(latched, reset_now, pct_now, now, reading_at)` | `bool` | S-18 閂鎖視窗身分（r5）；常數 `LATCH_RESET_TOL_MIN＝60`。r7（S-23⑥）：`reading_at < latched.at` ⇒ 讀數不參與「讀數已降」一條（只剩「已過閂鎖 reset＋60 分」一條可判換窗） |
| `schedule(anchor, target, k, affordable, t_kw, s, idle)` | `list[epoch]`（叫醒時刻序列，最後一個＝目標或空） | §5.2；keepwarm 與 watch 共用 |
| `pretool_verdict(payload, env, now)` | `(rc, msg)` | §6.1 |
| `stop_verdict(payload, env, now, *, inflight)` | `reason｜""` | §6.2 |
| `stop_mute(payload, env, now)` | `"wall"｜"quota"｜""` | §6.4 |
| `plan_lines(plan)` | `list[str]`（含 `QUOTAWALL_PLAN=` 一行） | watch／status／`quotawall` 動詞共用 |
| `primary_live(payload, sid, now)` | `bool` | S-18 主載具憑證（running keepwarm／watch shell ∧ holder 帶目標且活、`wake_at` 未來）；midwork 與 §6.2 共用 |
| `latch_seen(sid, reset, pct, now)`／`latch_mark(sid, reset, pct, now)` | `bool`／None | S-18「缺 park」每 (sid, 短窗視窗) 一次的閂鎖（r5：以 `same_window` 判，不以 reset 精確值當鍵）；檔案 `trace_dir()/quotawall/<sid>.json`；讀寫失敗 ⇒ 視為未推（寧可多推一次，不漏推） |

任何例外 ⇒ `stage="none"`、`pretool_verdict` (0,"")、`stop_verdict`／`stop_mute` ""（fail-open）。ENV_SPEC 新增三鍵（`AUTOSDD_QUOTAWALL_PP_PER_KUNIT`、`…_BURN_PP_PER_MIN`、`…_AGENT_EST_PP`；空＝未校準；非 >0 有限數 ⇒ 視為未校準並出聲）；程式常數 `IDLE_LIMIT_MIN`、`W_CLOSE`、`BACKUP_GRACE_MIN`、`OBSERVE_SEC`、`PING_PP_REF`、`C_REF`、`MAC_HEARTBEAT_MIN＝10`、`LATCH_RESET_TOL_MIN＝60`（r5）、三個未校準預設。跨包欄名常數與讀取函式不在本檔，在葉模組 `qw_schema.py`（S-12；本檔與 park／keepwarm／holder 皆 import 它）。逃生口 `AUTOSDD_QUOTAWALL_OFF`：只關擋派與推回，牆中偵測、牆內延後、靜音照舊（那是正確性）。只看短窗軸，不讀 `quota_policy.decide` band、配速床、趕工戳記。

---

## 5. 主載具：session 內背景等待（`keepwarm` 擴充；D-F）

### 5.1 不掛的情形（`keepwarm.skip_reason`，r3）
次序 `unattended → mode → off → handed_over → no_usage → small_ctx`；**`park` 一項刪除**（`keepwarm.py:186-187`）。有 `wake_target` 時只有前四項會讓它不掛；`no_usage`／`small_ctx`／未來 k > n*（r7 起不看保溫帳歷史，S-24）只會讓它「不付費 ping」，仍以單跳等到目標（D-C：付不起＝單跳，不是不掛）。

### 5.2 排程（`quotawall.schedule`）
- 啟動時讀一次 `wake_target` 與 `plan`，印首行 `KEEPWARM_PLAN mode=<chain|single|periodic> wake_at=<ISO> k=<n> target_source=<park|reset|none> early=<on|off>`（flush；D-K 憑證之一；`early=on`＝`ref_reset` 非空、S-19 生效，r5）。
- `target` 為空 ⇒ `periodic`：R216 行為逐位元相同（錨點＋T_kw、到 n* 即 `cap`）。
- `target` 非空 ∧ `affordable` ⇒ `chain`：自錨點每 T_kw 一次 ping，直到 `target − 錨點 ≤ idle` 時下一跳直接到 target。性質（AT-QW-20 窮舉）：每段閒置 ≤ max(T_kw, idle) ≤ 50；reset 前付費次數＝k；最後一次恰在 target。
- `target` 非空 ∧ 非 affordable ⇒ `single`：一跳到 target，零付費。
- 每輪重讀錨點：真人或主控有新記錄 ⇒ 錨點後移、重算（R216 既有語意）；保溫帳歸零（r7，S-24）＝真人提示（既有）∨ 主控真工作記錄（`work_mark` 變了；r8 只認含非唯讀且非監督 `tool_use` 的回合，讀 keepwarm／watch 輸出與重掛不算，S-24②）∨ 視窗翻新（`resume`／`keepwarm_early_reset`）。`chain`／`single` 的判定只看未來 k（S-24），保溫帳歷史只供 `periodic` 的 cap 與量測。
- 讀數一律先過 S-23 年齡規則（啟動時與每個叫醒時刻）；每個 `ping` 叫醒時刻以本次與上一次 ping 叫醒的讀數算實測 Δ、再把 `last_ping_*` 更新為本次（r8，S-25；重掛啟動時不算 Δ）。

### 5.3 牆鐘輪詢（V-W2）
迴圈每輪 `sleep(min(POLL_SECONDS, due − now))`（`POLL_SECONDS＝60`，`keepwarm.py:44`），`now` 一律取牆鐘 epoch（`time.time`），不以單調鐘或單次長 sleep 計時。機器睡眠或行程被凍結跨過截止 ⇒ 恢復後至多一輪（≤60 秒＋排程抖動）即結束。PRD §4.5.2「修正 v1 的單次長 sleep」同型教訓。

### 5.4 牆內不結束（S-7）
任何計畫中的結束時刻落在 `[wall 偵測時刻, reset＋s)` ⇒ 延到 reset＋s；牆內不呼叫 `record_ping`（結束本身就是叫醒＝一次 429）。`wall_state` 每輪重判。

### 5.5 到目標：先驗額度再叫醒（V-W4）
（r7）本節每一次「讀短窗」都先過 S-23：陳舊即補量、補不到外推並標 `stale=yes`；早於參照時刻 `ref_at` 的讀數不參與 `early_reset`、不更新 `ref_pct`。到 target 時讀一次短窗（同 `plan` 的讀法）：讀數 ≥ 100 且伺服器回報**新的**未來 reset ⇒ target 改為新 reset＋s、繼續等（`KEEPWARM_DEFER` 一行、痕跡 `keepwarm_defer`），**同時把參照更新為（新 reset, 100）**（r5）；讀不到／reset 不明 ⇒ 照原 target 叫醒（不猜時刻，PRD §4.5.10）。**提前重置（S-19，r5）**：`early=on` 時，每個 ping 時刻與 defer 中的每輪也讀一次短窗（同一讀法、同一快取，不另付 token），先判 `quotawall.early_reset(ref, obs)`（reset 晚於參照**且讀數已降**）⇒ 立即判 `resume`（該時刻不 ping、痕跡 `keepwarm_early_reset`）；reset 變晚而讀數未降 ⇒ 照常 ping／照常等；同窗讀數上升 ⇒ `ref_pct` 取最大值。`early=off`（`park --at`）不適用。提前續工後 §8 觸發 1 寫 `.resumed` ⇒ park 備援到點依 §7.2「交接包非 live」skip。結束判 `KEEPWARM_VERDICT=resume`（rc 0、不計 pings）。處置：「已到預定時刻：照停工前計畫繼續；交接包已自動記為續跑（§8）；park 備援會自行讓路」。

**交棒重判（S-13，QA2 P2-3）**：每一個叫醒時刻（ping、到目標、defer 結束）在印判決**之前**先跑 `seal.handed_over(sid)`；非 None ⇒ `KEEPWARM_VERDICT=handed_over`（rc 0、不計 pings、不呼叫 `mark_resumed`、痕跡 `keepwarm_verdict verdict=handed_over`），處置：「本視窗已交棒（備援已在別的 session 接手）：不得動工作樹、不得重掛，直接結束回合」。啟動時的 `skip_reason=handed_over` 不變。WHY：讓路上限（第 4 次）或 S6 觀察期滿後備援已 fork／FRESH，而舊窗 keepwarm 其實還活著（凍結解除、DEFER 結束）——不重判就會 `resume` 並寫 `.resumed`，兩個視窗同時動工。

### 5.6 holder 與憑證
`holder` 列增欄 `wake_at`、`mode`、`target_source`（欄名常數與 `holder.acquire(..., extra=)`／`qw_schema.holder_wake(row)` 讀取函式在 Q1 落地，S-12；Q2 只呼叫）；`park --status`、`sessionctl status` 讀它印主載具列（§10）。

### 5.7 watch 共用
watch 持有保溫錨（R217 A4）時用同一 `schedule`、同一牆內延後、`resume` 與交棒重判（REQ-WP-31 互斥沿用）。

### 5.8 macOS（S-14）
darwin 上 keepwarm 每 `MAC_HEARTBEAT_MIN`（10）分在 stdout 印一行 `KEEPWARM_HEARTBEAT <ISO>`（flush、不叫醒、零 token）；首行 `KEEPWARM_PLAN` 加欄 `backup=absent(platform)`。心跳能否擋住「記憶體壓力下閒置 ≥30 分被收」未證，登 OI；被收時由 park 的 launchd job 在 fire 時刻出聲（§7.5）。

---

## 6. 觸發點

### 6.1 PreToolUse 擋新派工（`converge.converge_verdict` 內呼叫）
- 主控的 Agent／Task／Workflow；`payload.agent_id` 有值放行。`nodispatch`／`close` ⇒ rc 2；`free`／`none`／`wall` 放行。
- 訊息含階段、D、R、V、L、`calibrated`、該階段確切步驟。逃生口 `續派理由：<≥8 字>`（記 `quotawall_override`；無人窗口無效）。收斂閘（硬線）先判；兩者都成立只出收斂閘訊息＋一行額度牆摘要。

### 6.2 Stop 推回
- **在飛側**：`_finalized_wake` → `quotawall.stop_verdict(inflight=True)` → `supervise.stop_verdict`，取第一個非空。`close` ⇒「TaskStop 全部在飛代理（成品留工作樹）→ 結束回合；下一次 Stop 會帶你走收尾」。
- **閒置側**（`_park_stop` 由 quotawall 分派）：`close` 且〔無有效 park 憑證 ∨ 無主載具在跑〕⇒ 一則合併訊息列出尚缺的步驟：`handoff --build`→寫主控層→`--finalize`→`park`→`keepwarm`（`run_in_background`）。已有有效 park 且主載具在跑 ⇒ 不推。
- `credential_ok` 的「有效」r3 起多一條：標記的交接包仍 live（被 `.resumed`／`.ack` 就失效，§8）。
- **主載具在跑、只缺 park（S-18）**：同一 (sid, 短窗視窗) 只推一次（閂鎖 `latch_seen／latch_mark`，視窗身分以 `same_window` 判：reset 觀測值漂移不算換窗，讀數已降或已過閂鎖 reset＋60 分才算；r5）；其後 Stop 回 `systemMessage`「備援缺席：主載具 wake_at=… 在跑；未登記 park（原因自述）」，不 block。`none` 階段的既有 `park.stop_verdict` 由 `_park_stop` 套同一閂鎖（`park.py` 判準本體不改）。
- 既有 `park.stop_verdict`（短窗 ≥ 準備門檻推 park）的位置（S-16，QA2 P3-4）：`_park_stop` 先問 `quotawall.plan`；`free`／`nodispatch` ⇒ 不推 park（額度照樣用到接近滿）；`close` ⇒ 上一條；`none` ⇒ 既有 `park.stop_verdict` 原樣（量不到時它本身也不判，行為逐位元不變）；`wall` ⇒ 靜音（§6.4）。

### 6.3 主載具閘（D-K 的機械物；Stop 閒置側）
本 sid 有 armed park 標記 ∧ payload `background_tasks` 沒有 running 的 keepwarm／watch shell ∧ 非「不掛的情形」前四項 ⇒ 推回一次：「park 只是備援；請掛 `sessionctl keepwarm --sid <sid>`（run_in_background），並把背景任務 id 與輸出首行 `KEEPWARM_PLAN … wake_at=` 貼進回覆」。取代 r2 keepwarm 保溫閘在 park 有效時的沉默（C4）。與保溫閘、封存閘同時成立時合併成一則（次序 封存→park→主載具）。
「不掛的情形」的 `off` 項以 **hook 行程的原始環境**判（`sessionctl_guard.py:76-83` OIR 讓路注入的 `AUTOSDD_KEEPWARM_OFF` 不算；QA2 P3-3）：主載具閘屬 park 憑證，不屬保溫閘，否則 `park --why`／S5 `park --at` 在 free 階段會因 OIR 注入而失聲。

### 6.4 牆中與準備帶靜音（`stop_mute`）
| `stop_mute` | sessionctl Stop | `check_pending_handoff`（散文交棒／半路停工／完成閘） | OIR 讓路（`sessionctl_guard.py:76-83`） |
|---|---|---|---|
| `"wall"` | 整體回 ""，痕跡 `quotawall_stop_muted` | 三種推回全部不出 | 不適用 |
| `"quota"`（nodispatch／close） | 照 §6.2／§6.3 | 散文交棒照舊；半路停工照舊但主載具憑證成立時不判（S-18，任何 `stop_mute` 值皆同）；完成閘改 `systemMessage` 一行，不呼叫 `gate.mark_pushed` | 不設 `AUTOSDD_KEEPWARM_OFF` |
| `""` | 照舊 | 照舊 | 照舊 |

接點：`check_pending_handoff.py` `main()` 呼叫一次 `stop_mute`（lazy import、例外 ""）；`openitems/gate.py` 判準不改；`midwork.background_idle` 只加 S-18 一條（帶目標主載具 shell 不排除；讀 holder 走 `qw_schema.holder_wake`，讀不到＝維持排除，即舊行為）。

### 6.5 watch
`quota` 事件前印 `plan_lines`；閂鎖帶級 `prepare(1)＜nodispatch(2)＜close(3)＜halt(4)`；處置表依階段：`prepare`＝既有；`nodispatch`＝「已進擋派區：不再派新代理（PreToolUse 會擋）；在飛代理照跑、主控自己的工作照做；重掛同一條 watch」（QA2 P3-4）；`close`＝「TaskStop → 封存 → park → 掛 keepwarm」；不再出現「代理快完成 ⇒ 重掛」；牆中不判事件、不記保溫帳、只寫心跳。

---

## 7. 備援：park（外部排程；D-G、D-H）

### 7.0 到點判定次序（r4，與 R218-B 相容）
SE 產品面 L1 拒絕（喚醒對象合法性，PRD §11.9 R-VER-4）→ §7.2 前置 → §7.3 讓路（含 `OBSERVE_SEC` 觀察期）→ §7.4 選路 → §7.5 失敗鏈。L1 判準釘在 `park_job_start` 痕跡之後、讀標記之前（SE §3.4）；本稿的 holder 讀取、`park_yield_primary`、`OBSERVE_SEC` 觀察、`park_attempt` 一律排在 L1 之後。**L1 拒絕永不進失敗鏈**（SE D-13）：標記狀態寫 `refused`（不是 `failed`），不寫 `park_attempt`、不重排、不嘗試另一路、不寫 handback、不入通知佇列、不呼叫 `notify`；§7.6 哨兵接手只認 `failed`，`refused` 結構上不會被接手；只走 SE 的痕跡 `sideeffect_refused` 與 `_disarm_verified` 自拆。WHY：L1 拒絕＝目標不合法（沙盒過期、根不一致），把它當「續航失敗」會讓哨兵替一個不合法目標再試一次。**r6：L1 有兩個站點**——上述 fire 站點（`_cmd_fire` 首判，不寫 `park_attempt`）與 spawn 站點（`spawn_resume`／`handoff.spawn` 開頭，例：漏傳 `--claude` 而命中 `sandbox_real_exe`、或租約在選路後到期）；後者回 `RC_SIDEEFFECT_REFUSED`，處置見 §7.5-1a。兩者皆終局 `refused`（SE D-13／D-24；SE §10.2.1 X-7／X-8）。

### 7.1 登記
- 前置照舊（finalize、工作樹保全、無在飛代理、短窗到準備門檻或 `--why`／`--at`），**另認** `plan.stage == "close"` 為前置成立。
- 標記新增 `primary_wake_at`（＝既有到點時刻：短窗 reset＋s，或 `--at` 值）、`primary_source`（r5：前者 `reset`〔含 `--why`〕、後者 `at`；S-19 據此判是否適用）與 `backup_fire_at＝primary_wake_at＋BACKUP_GRACE_MIN`；排程登記在 `backup_fire_at`。另寫 `close_stuck_window`（登記行程環境 `AUTOSDD_PARK_CLOSE_STUCK_WINDOW=="1"`）與 `desktop_notify`（登記行程環境 `AUTOSDD_DESKTOP_NOTIFY` 原值）；欄名常數全在 `qw_schema`（S-12、S-17）。job argv 的環境轉送照 SE `job_env_argv(env, sandbox=…)`（`sandbox` 取自同站點 `register_verdict`；正式目標遇不允許值不轉送、不阻擋登記，SE D-20 r4）。
- 非 win32：照常登記 launchd job（出聲用），末行 `route=` 後加 `backup=absent(platform)`（S-14）。
- 嘗試武裝本 sid 的哨兵（既有 `--arm-sentinel` 路；拒絕時照實印 `sentinel=absent reason=…`）。遵守 `AUTOSDD_SENTINEL_OFF`（X-19）：有設 ⇒ 不呼叫任何排程器、末行 `sentinel=absent reason=sentinel_off`（r8，AT-QW-82）。
- 末行 `PARK_VERDICT=armed route=… primary_wake_at=<ISO> backup_fire_at=<ISO> next_run=<排程器自報值> sentinel=<armed|absent>`；其上一行提示 §6.3 的主載具與貼憑證。

### 7.2 到點前置（照舊）
未 armed／已 ack／已 `.resumed`（交接包非 live）／過期 ⇒ skip；`live_driver`（含 harness auto-continuation）⇒ skip。

### 7.3 主載具讓路（新）
讀 `holder.read(sid)`，四個分支互斥（r4 把「正常釋放」與「已死」拆開，QA2 P2-3）：
- **A 活著且未到**：`holder.is_live` ∧ `wake_at > now` ⇒ 重排到 `wake_at＋BACKUP_GRACE_MIN`（每標記至多 3 次，計 `reschedules`；job 內登記新排程前先過 SE `register_verdict`，拒絕 ⇒ 不重排、照 L1 終局 `refused`；沙盒目標帶 `job_expiry`）、痕跡 `park_yield_primary`。第 4 次往下走（舊窗晚醒時由 §5.5 交棒重判兜住）。
- **B 活著且已過**：`is_live` ∧ `wake_at ≤ now` ⇒ 觀察 `OBSERVE_SEC`（每 10 秒重看 `live_driver` 與 holder）：出現 driver ⇒ skip `primary_woke`；觀察期內 holder 記錄消失 ⇒ 轉分支 C 重判；期滿仍無 ⇒ 判 S6 卡死，往下走。
- **C 正常釋放**：holder 記錄不存在 ∧ 痕跡有本 sid 晚於 park 登記的 `keepwarm_verdict`（`resume`／`ping`／`handed_over`）⇒ 主載具已叫醒主控：`handed_over` ⇒ skip `handed_over`；其他 ⇒ 觀察 `OBSERVE_SEC` 等 driver，出現 ⇒ skip `primary_woke`，期滿無記錄 ⇒ 主控被叫醒卻沒寫記錄（視窗卡死或已關），依活窗有無往下走（S6／S3）。
- **D 已死或從未掛**：holder 記錄存在但 `is_live` 假，或記錄不存在且無上述判決痕跡 ⇒ S3，往下走。

### 7.4 選路與活窗（R-3 改語意；S-10）
- F4 選路（`park.fire_route`，不變）。
- **spawn 執行檔單一來源**：job argv 的 `--claude`（SE §4.2；未給＝`"claude"`）原樣傳到每一次嘗試——`spawn_resume`（含 `fork=True`）、`handoff.spawn(pkg, claude=…)`（修現行 `park_cli.py:428` FRESH 路未帶）、§7.5 另一路（一律 `opts.claude`）、§7.6 哨兵接手（r5 對齊 SE §10.2-8：讀 park 標記的 `claude` 欄，`park` 登記時由 SE S2 寫入；不另讀哨兵 job argv）；REQ-QW-44、AT-QW-71、MU-QW-36。
- 任何 spawn 呼叫**之前**先寫 `session_switch_spawning`（`handoff`＝包路徑、`attempt`＝序號、`route`、`at`）；失敗時同 attempt 寫失敗列（`seal._spawned` 據此不算），成功時寫既有 `session_switch_spawned`（`ok=True`；S-13）。意圖逾 `SPAWN_INTENT_TTL_SEC` 仍無成功列 ⇒ 不算交棒（S-13 r5）。
- **fork 成功判準（S-20，r5）**：只認 spawn 後新出現、stem ≠ 原 sid 的 jsonl ∧ 行程活；原逐字稿變大不算；成功列帶 `new_sid`、`route=fork`；fork 路不呼叫 `mark_resumed`。
- **`handoff.spawn`（S-21，r5）**：成功後才解除哨兵（失敗不解除，§7.6 才有接手者）；dedup 只認成功列或行程仍活者——同一包 600 秒內 FRESH 失敗後，哨兵接手的 FRESH 不被拒。
- 同 sid 有活著的 `entrypoint=cli` 視窗（`oldwin_park.live_windows_of`）：**不關**。RESUME ⇒ `spawn_resume(..., fork=True)` 以 `claude -r <sid> --fork-session` 開新窗；FRESH ⇒ `handoff.spawn`。成功後對原交接包寫 spawn 痕跡（新 sid），舊窗依既有「已交棒」語意：人在舊窗打字 ⇒ UserPromptSubmit 告知「本視窗已交棒」；舊窗 keepwarm 晚醒 ⇒ `handed_over`（§5.5）。
- fork 新 session 與交接包（QA2 P3-5）：fork 承接的是同一段歷史，**算交棒**——spawn 痕跡寫好即 `handed_over`；續跑提示末句要求新 session 先 `handoff --ack <包>`（新 sid 記入 `.ack`），ack 前後 `handed_over` 皆為真，不依賴 ack 成立。
- 非 win32 ⇒ 不呼叫任何 spawn，直接以 `attempted:false, reason:"platform_unsupported"` 一列進 §7.5 終點（S-14）。
- 同 sid 有活著的 `entrypoint=sdk-cli` ⇒ 視同 live_driver skip（`oldwin_park.py:69` 既有）。
- 無活窗 ⇒ 普通 `claude -r <sid>` 或 FRESH。
- 殺窗：只在 §7.3 判卡死 ∧ 標記 `close_stuck_window==true`（登記時寫入，S-17；job 行程環境不讀此鍵——R218-B 允許表下它恆為空）∧ R217 §7.1 五條件全成立；關掉後才用普通 `-r`。`oldwin_park.resume_gate` 於 park 路徑只剩這一個呼叫點。

### 7.5 失敗鏈與結局（R-5、D-H）
1. 依序嘗試：F4 選的路 → 另一條路（RESUME↔FRESH；FRESH 的 spawn 前置〔`handoff._refusals`：未 finalize、工作樹髒且無 wip tag、有在飛代理〕若拒絕也算一次失敗並記原因）。
1a. **（r6）spawn 站點 L1 拒絕＝終局，不算失敗、不走另一路**：任一次嘗試（含 fork、另一路、§7.6 接手）的 spawn 函式回 `RC_SIDEEFFECT_REFUSED`（SE D-24；以常數比對，不寫字面）⇒ 該次 `park_attempt` 照記實際 rc 與 `reason=sideeffect_refused`、`session_switch_spawning` 同 attempt 寫失敗列（`seal._spawned` 不算交棒）；隨即標記 `status=refused`（reason 帶 spawn 站點理由）、`_disarm_verified` 自拆、job rc 0；**不**嘗試另一路、**不**寫 handback、**不**入通知佇列、**不**呼叫 `notify`、**不**寫 `park_chain_failed`；§7.6 只接手 `failed`，結構上不接手。與第 1 條的分界：前置拒絕＝「此路暫時走不通」（失敗、試另一路）；L1 拒絕＝「這個目標不該被叫醒」（終局）。
2. 每次嘗試落 `switch.trace("park_attempt", route, attempted, rc｜None, reason)`；標記 `outcome.attempts` 逐筆記實際值。**禁止任何字面 rc**（MU-QW-21 守）。
3. 全部失敗 ⇒ 標記 `status=failed`、`switch.trace("park_chain_failed", attempts)`、寫 handback（指向上述痕跡）、`quota_escalation.notify_queue_path()` 入列、`quota_escalation.notify()`（開關＝標記 `desktop_notify` AND argv 帶來的關閉值，S-17）。SessionStart 公告未讀 handback（既有）；UserPromptSubmit 對同專案任一視窗、同一失敗只注入一次「park 到點失敗」提示（`sessionctl_guard` 轉送分支前；痕跡 `park_failure_notice`）。
4. job 照舊一次性自拆（`_disarm_verified`）；後續由 §7.6 接手。

### 7.6 哨兵接手（R-6、R-7）
`_sentinel_tick` 每次巡邏多讀本 sid park 標記（接手分支先過 SE L1 tick 判準；`refused` 不接手）：`status=failed` 且 `outcome.at` 晚於上次巡邏 ⇒ 依 §7.3 讓路判準檢查一次，未讓路則跑一次 §7.4～§7.5（不殺窗；執行檔取標記 `claude` 欄）；結局 `fired` 或 `failed_final`（r6：接手中的 spawn 回 `RC_SIDEEFFECT_REFUSED` ⇒ 結局 `refused`，同 §7.5-1a，不入佇列），痕跡 `sentinel_park_takeover`，failed_final 時再入通知佇列一次。哨兵未武裝 ⇒ 沒有第二道網，park 登記時已照實印 `sentinel=absent`（§7.1）。r5 起哨兵不會因 FRESH 失敗被拆（S-21）。
**過期意圖（r5，S-13、QA3 P2-6）**：標記非終態（armed／job 執行中）∧ 痕跡有本包 `session_switch_spawning` 已逾 `SPAWN_INTENT_TTL_SEC` ∧ 同 attempt 無 `spawned ok=True` ⇒ 先查「前次其實成功」：意圖 `at` 之後專案目錄出現 stem ≠ 原 sid 且含記錄的新 jsonl ⇒ 補寫 `session_switch_spawned`（`ok=True`、`recovered=true`）、標記 `fired`、痕跡 `park_spawn_recovered`、**不再 spawn**（防兩個駕駛）；否則標記改 `status=failed`（`outcome.attempts` 追加 `{route, attempted:true, rc:null, reason:"intent_expired"}`）、痕跡 `park_intent_expired`、照 §7.5 第 3 步出聲，再依上段接手一次（普通 `-r` 路的「前次其實成功」不會產生新 sid 檔，由接手前的 §7.2 `live_driver` 與 §7.4 活窗偵測兜住：有人在動即 skip、有活 cli 窗即走 fork）。

---

## 8. 原主人自續跑自動記 `.resumed`（D-J）
`seal.mark_resumed`（既有，`seal.py:204`）的觸發點增為：
1. keepwarm／watch 判 `resume`（§5.5）且本 sid 最新交接包 live ∧ `.sealed` 存在 ∧ **包未 spawn、未被別 sid ack**（`seal.handed_over(sid) is None`，含 `spawning` 意圖；QA2 P2-3）⇒ 呼叫；已交棒時不會走到這裡（§5.5 先判 `handed_over`），此條件是第二道；
2. UserPromptSubmit 轉送判「留在本窗」（`forward.py:148` `f4_resume_cheaper`、快取熱、`留：` 前綴）∧ 本 sid 為包的原主人 ∧ 未交棒（同上判準）⇒ 呼叫；
3. 既有：`handoff --ack` 原主人、park RESUME 成功（`park_cli.py:367`）。
效果：`.sealed` 刪除 ⇒ `wake_package` 回 None ⇒ 冷叫醒閘不再推（22:54 誤推消失）；`credential_ok` 失效 ⇒ 若仍在 `close`，Stop 依 §6.2 重新要求封存＋park（不留過期備援）。fork 新窗（§7.4）**不**記續跑（那是交棒）。FRESH 新窗的 `--ack` 與舊窗 `.resumed` 互搶：spawn 前已寫 `spawning` ⇒ 舊窗兩個觸發點都判已交棒、不寫 `.resumed`，互搶在結構上消失。

---

## 9. 映像家族比對與測試圍籬（D-I）
- `procstop.CLOSE_IMAGES` 改為家族判準 `procstop.image_allowed(name)`：`^claude\.exe(\.old\.\d+\.\d+)?$` 或 `node.exe`（不分大小寫）；身分仍以 handle 上建立時刻＝登記 procStart 為主，映像只是縱深防禦。
- `oldwin._terminate`：`image_not_allowed`／`open_failed` 改為可降級（`terminal=False, degradable=True`）：跨 sid 關舊窗路徑記 `oldwin_close_degraded` 後照既有「新 session 出聲」繼續；不再走 `retry_at=None` 的死路。
- `tools/tests/test_sessionctl_oldwin.py` 一律以 tmp 圍籬 `trace_dir`（CSA §2：23 筆 `identity_unverified` 是單元測試寫進正式痕跡目錄）；新增一條鎖：測試期間真 `~/.autosdd/traces/oldwin/events.jsonl` 的新增段不含測試 sid／tmp 路徑／沙盒字樣（真 session 可能同時追加，不判位元組數）。r5（QA3 P3-2）：測試 sid 一律含測試模組常數 `OLDWIN_TEST_SID_MARK`（可 grep 的獨特字串，例如 `qwoldwintest`），E2E-QW-18 以 import 該常數 grep，圍籬拿掉時必命中轉紅（MU-QW-37）。

---

## 10. 憑證（D-K）
宣稱「會自動繼續」的回覆必須同時貼：①主載具＝`run_in_background` 回的背景任務 id＋keepwarm 首行 `KEEPWARM_PLAN … wake_at=`；②備援＝`PARK_VERDICT=armed … next_run=`（Windows NextRunTime 值；macOS rc）。只有一份就照實寫「主載具缺席」或「備援缺席」。機械物：§6.3 主載具閘（沒掛就推一次）、`park --status [--verify]` 印兩列（`primary: live pid=… wake_at=… mode=…`／`absent`；`backup: next_run=…`／`absent`；`sentinel: armed|absent`）。根 CLAUDE.md〈反事後諸葛〉與〈因額度停工走 park〉段由 Q7 追加本規則。

---

## 11. 模式、無人窗口、讀不到、與其他機制
| 情形 | 擋派 | Stop 推回／主載具閘 | keepwarm | park 備援 | 牆中靜音 |
|---|---|---|---|---|---|
| mode=auto | 擋 | 推 | chain／single／periodic | 照 §7 | 有 |
| notify | stderr 一行 | 不推 | skip `mode`（既有） | 既有 notify 行為 | 有 |
| off | 無 | 無 | skip `mode` | 無 | 有 |
| `AUTOSDD_UNATTENDED` | 無 | 無 | skip（既有） | 拒（既有） | 有 |
| `AUTOSDD_QUOTAWALL_OFF` | 無 | 無（主載具閘照舊，它屬 park 不屬額度牆） | 牆內延後照舊；`affordable` 不判（有 target 一律 single） | 照 §7 | 有 |
| 讀不到／reset 不明 | 放行 | park 既有 | 無 target（除 park 標記）；`wall_state` 只用逐字稿兩條件 | 照 §7 | 只用逐字稿兩條件 |
| OIR 讓路注入 `AUTOSDD_KEEPWARM_OFF`（hook 行程內） | 照判 | 保溫閘讓路；**主載具閘以原始環境判、照推**（§6.3） | 不受影響（另一行程） | 照 §7 | 有 |
| macOS | 照判 | 照推（主載具閘照舊） | 照 §5，加心跳與 `backup=absent(platform)` | 到點只出聲（S-14） | 有 |

與既有：週軸「用到 100%」不變（只看短窗軸）；配速床／趕工戳記不讀；R1 退役、軟線、hold 不復活；X-7（`SessionSwitch_CostModel_Design.md:297`）有條件再開（Q7 追加註記）；冷叫醒閘一致性由 D-D＋§8 保證；R217 完成閘／半路停工／OIR 讓路見 §6.4；R217 §7.1 跨 sid 關舊窗用途不變、park 同 sid 用途改 §7.4。

---

## 12. 工作包切分（鐵律七：鎖的持有面）

**前置順序**：R217 期 A 收尾 commit（A9）＋ R218 F5（`interactive.py`）commit → SE S1 → {SE S2 ∥ SE S3 ∥ SE S5} → SE S6 → 本稿 Q 系列（Q1、Q2、Q5 可提前與 SE S2／S3／S5 並行，見下表）。WHY：SE S2 改 `park_cli.py`／`park.py`／`handoff.py`／`oldwin_sched.py`／`tools/sessionctl.py`，SE S3 改 `tools/session_resume_planner.py`，SE S5／S6 持有 `realverify/**` 與 `cases.json`——與本稿 Q3／Q4／Q6 同一持有面。共通：並行包不重釘棘輪、不寫帳本、不改 CI paths。

| WP | 內容 | 動到的檔（常數／史料／消費端） | 前置 | 並行 |
|---|---|---|---|---|
| Q1 | `quotawall.py`（§3～§4：plan、wall_state、wake_target、schedule、三個 verdict、plan_lines、`continuity.MATRIX`〔鍵＝(情境, 平台)〕常數表、`ping_pp` 縮放）＋ENV_SPEC 三鍵＋`.env.example`；**r4 起另含跨包 schema（S-12）**：葉模組 `qw_schema.py`（holder 增欄、park 標記五欄〔r5 加 `primary_source`〕、`session_switch_spawning` 事件名、`SPAWN_INTENT_TTL_SEC` 與讀取函式）、`holder.acquire(extra=)`／讀取、`seal._spawned` 認 `spawning` 意圖（含期限）；S-18 的 `primary_live`／`latch_*`／`same_window`、S-19 的 `early_reset`；**r7**：S-23 讀數年齡（補量、`R_eff` 外推、`stale_window`、`same_window`／`early_reset` 的讀數時刻條件、`ref_at`）、S-24 有目標時的 `affordable`（只算未來 k）、S-25 `ping_pp_eff`（保溫帳三個跨包欄名 `last_ping_pct`／`last_ping_at`／`ping_costs` 與讀取函式 `qw_schema.ping_costs(row)` 住 `qw_schema`：生產端 Q2、消費端 Q1） | 新：`tools/lib/sessionctl/{quotawall,qw_schema}.py`、`tools/tests/test_sessionctl_quotawall.py`；改：`tools/lib/sessionctl/{holder,seal}.py`、`test_sessionctl_holder*.py`、`test_sessionctl_seal*.py`、`tools/lib/quota_policy_env.py`（守衛面，暴露證據＝T858／T1645、22:42 事件）、`.env.example` | A9 | 與 SE S2／S3／S5 並行（檔不相交；SE S2 不碰 holder／seal）；本稿內單人 |
| Q2 | 主載具：keepwarm（§5 全部、刪 `park` 不掛、`resume`、S-19 提前重置、`handed_over` 重判、darwin 心跳、`--idle-min`、首行 PLAN、`mark_resumed` 觸發 1）、watch（§5.7、§6.5）；holder 只呼叫 Q1 的 `acquire(extra=)`；**r7**：每個叫醒時刻先補量（S-23⑤）、保溫帳歸零三條件與 `work_mark`、`chain`／`single` 只看未來 k、`cap` 只用於 `periodic`（S-24）、`ping` 叫醒時以相鄰兩次 ping 讀數差寫 `ping_costs`（r8；欄名 import `qw_schema`，S-25）；r8 `work_mark` 只認非唯讀且非監督 `tool_use`（import `midwork.READONLY_TOOLS`、`roster.KEEPWARM_CMD_RE`／`WATCH_CMD_RE`，S-24②） | `tools/lib/sessionctl/{keepwarm,watch}.py`、`tools/tests/test_sessionctl_{keepwarm,watch}.py` | Q1 | 與 Q3、Q5、SE S2／S3／S5 並行 |
| Q3 | 備援：park 登記欄位與憑證（欄名取 `qw_schema`）、`credential_ok` 交接包 live、`_cmd_fire` 讓路四分支／活窗 fork／`spawning` 意圖／失敗鏈／結局／`platform_unsupported`、`spawn_resume(fork=)`（S-20 成功判準）、`oldwin_park` 改語意、`procstop` 家族、`oldwin` 可降級、oldwin 測試圍籬、哨兵接手 `_sentinel_tick`（含過期意圖，r5）；**r5：`handoff.spawn` 成功後才解除哨兵、`_duplicate_refusals` 只認成功或活行程（S-21）**。**R218-B 同步（SE §10.2 第 2、7、8 項；同一個 commit）**：新站點 `spawn_resume(fork=True)`、§7.3 job 內重排（呼叫 `register_verdict`）、§7.5 第 3 步通知與入列、§7.6 `_sentinel_tick` 接手分支四處進 `sandbox_scope.SITES` 並呼叫判準；AT-SE-39 隨本包落地（AST 鎖使漏登記即紅）；§7.4 fork 與 §7.5 另一路傳 `opts.claude`、§7.6 讀標記 `claude` 欄，同 commit 補三處 runner argv[0]＝替身的 AT（AT-QW-71）；**SE 的 AT-SE-31／E2E-SE-09 黃金序列與 E2E-SE-01(e1)(e3)、09(b) 的 `park_attempt` 斷言由本包同一 commit 重釘**（spawn 次序與 disarm 位置改變會動到它們；SE §10.2.1 X-18）；**r6**：§7.5-1a 消費 SE S2 已提供的 `sandbox_scope.RC_SIDEEFFECT_REFUSED` 與 `park.STATUSES` 的 `refused`（SE D-21／D-24；本包不另定義），AT-QW-69③ 隨本包落地 | `tools/lib/sessionctl/{park,park_cli,oldwin_park,oldwin,procstop,handoff}.py`、`tools/session_resume_planner.py`、`tools/lib/sandbox_scope.py`（只在 `SITES` 加列）、`tools/tests/test_sessionctl_{park,park_route,oldwin,handoff}.py`、`tools/tests/test_context_budget_guard.py`（SentinelDecision 增案）、SE 的 AT-SE-39／AT-SE-31 所在測試檔、E2E-SE-09 黃金序列檔 | Q1、SE S2、SE S3 commit。**`handoff.py` 同時是 SE S2 的持有面**：先 SE S2 commit（L1 spawn 站點判準在 `spawn` 開頭）、後本包（disarm 次序與 dedup 在同函式後段），本包在 SE S2 之上改，兩者不並行；本包對 `handoff.py` 的改動與 `SITES`、AT-SE-31 重釘同一個 commit | 與 Q2、Q5 並行（檔不相交） |
| Q4 | 守衛接線：`converge.py`（PreToolUse、Stop 兩側、主載具閘、`_park_stop` 分派與 S-18 閂鎖）、`midwork.py`（S-18：`background_idle` 認帶目標主載具）、`forward.py`（`mark_resumed` 觸發 2、park 失敗提示）、`tools/sessionctl.py`（`quotawall` 動詞、status 兩列）、`.claude/hooks/check_pending_handoff.py`（`stop_mute`）、`.claude/hooks/sessionctl_guard.py`（OIR 讓路排除 close、UserPromptSubmit 失敗提示接點）；既有 park／keepwarm Stop 測試逐案覆核 | `tools/lib/sessionctl/{converge,forward,midwork}.py`、`tools/sessionctl.py`、兩支 hook、`tools/tests/test_sessionctl_{converge,forward,hooks,keepwarm}.py`（keepwarm 測試檔內既有 `background_idle` 案只改那幾案）、`test_openitems_gate.py`（同）、`test_check_pending_handoff*.py` | Q2、Q3 | 單人（守衛面：子代理產 diff 到 scratchpad，主控親套） |
| Q5 | 量測：M-K7、M-K8、M-K9（park 到點結局普查）、`--calibrate-quotawall` | 新：`tools/lib/wastecensus/sections_wall.py`、`tools/tests/test_waste_census_wall.py`；改：`wastecensus/{sections_keep,keep_load,report}.py`、`tools/probe/waste_census.py`（旗標分派） | Q1（事件名常數；r5：wastecensus 直接 import `lib.sessionctl.qw_schema`——葉模組只依標準庫、套件 `__init__` 只補 `sys.path`，無循環；QA3 P3-1） | 與 Q2、Q3 並行 |
| Q6 | RealVerify 家族 `quotawall`（TCS §4 全部）＋`cases.json`；**另含 SE 的 E2E-SE-17 案例程式**（落在 `cases/sideeffect.py`，SE §10.2 第 4 項，主控確認；SE S7 的 OI 於本包收尾結案） | 新：`tools/lib/realverify/cases/quotawall.py`；改：`tools/lib/realverify/cases/sideeffect.py`（只加 E2E-SE-17）、`docs/06_quality/RealVerify_Protocol/cases.json` | Q2～Q5 commit、SE S6 commit | 單人（cases 單一持有） |
| Q7 | 收尾：棘輪重釘（新 2 測試檔）、`Root_Layout` §3、ADR-XPLAT-004 新節（編號現查；R217 C3 預留 §2.20、SE S7 另佔一節）、`WorkProgress_Axis_Design.md` §7.1 與 D-14 追加註記（指向本稿 §7.4）、X-7 追加註記、根 CLAUDE.md（守衛總表兩列、換 session SOP〈因額度停工走 park〉加主載具與雙憑證、〈反事後諸葛〉加雙憑證、速查表加 `sessionctl quotawall`）、缺陷帳本 DEF（22:42 事件 P1、映像白名單、字面 rc、失敗靜默，現查最大號＋1）、PRD §16.6 本列 OI 回填、E2E 全跑入帳、**上線閘（S-15）：真本機 `waste_census --calibrate-quotawall` 三鍵有值並寫進 `env.shared`**、§17 理論洞與 OI 清單抄進證據檔 | 收尾面（含 `env.shared`） | Q1～Q6 | 單人 |
| W11b | （r9，附錄 H.3）`pace_line` 標題補「短窗最高帶」欄（不改 `_binding_key`）；**後半**：planner `--pace` 加 `QUOTAWALL_PLAN` 一行（排 W6 之後） | 前半：`tools/lib/quota_messages.py`、`tools/tests/` 對應檔；後半：`tools/session_resume_planner.py`、`tools/tests/` 對應檔 | 前半無（Q4／W6 皆不碰）；後半＝W6 commit | 前半與 W11d／W11e 並行；後半單人（守衛面）。註記：實作另含 `tools/lib/quota_short_window.py`（LOC） |
| W11c | （r9）①`L` 加 `burn_live×min(D,T_OBS)`（`T_OBS＝30` 住 `qw_calc`）；②在飛區間 ping Δ 不入帳；③乾淨樣本 ≥3 且 ≤校準×3 才採用量測值、`kw_ledger` schema `/1`→`/2`、`ping_cost_outlier` 痕跡 | `tools/lib/sessionctl/{qw_calc,qw_plan,kw_wake,kw_ledger,qw_schema,roster}.py`、`tools/tests/test_sessionctl_{quotawall,keepwarm}.py` | Q1、Q2 commit；**②③須不晚於 W11a（同 commit 或更早）**；① 待 DES 凍結後實作，且先於 Q7 校準；**上線序（QA W13 P2-3 主控裁決）：{②③＋W11a（Q4）} → ① → W11b／W11d／W11e；① 不等 W11b／d／e**（① 才是擋下 10:02 事故的那一項） | ②③與 Q4 同 commit 或先；① 單人；W11d／W11e 並行（檔不相交，`kw_ledger` 同被 Q2 持有故在 Q2 後） |
| W11d | （r9）watch／keepwarm 額度閂鎖拆兩條序列（原始讀數 prepare＜halt；計畫 nodispatch＜close）；新派工（N 增）且 stage≥nodispatch 重新觸發；事件文案依來源分開 | `tools/lib/sessionctl/{watch_wake,keepwarm,watch}.py`、`tools/tests/test_sessionctl_{watch,keepwarm}.py` | Q2 commit | 與 W11b 前半、W11e 並行（檔不相交；與 Q4 不同檔） |
| W11e | （r9）realverify `spends_quota` 旗標、開跑前額度閘（整批 env `QUOTA-PREFLIGHT`）、`run_claude` 撞牆型失敗判 env（字樣實查後寫入、重用既有辨識） | `tools/lib/realverify/{runner,driver}.py`、`tools/lib/realverify/cases/*.py`（只加旗標）、`tools/tests/` 對應檔 | **Q6 commit 後串行**（cases 單一持有） | 與 W11b 前半、W11d 並行（檔不相交，但 `cases/` 在 Q6 後） |
| （W11a） | 併入 **Q4**，不另開包：`sessionctl_guard.py`／`converge.py` 的 PreToolUse 呼叫 `quotawall.pretool_verdict`（AT-QW-83／84／96、E2E-QW-31／32(b)） | 同 Q4 | Q4 前置＋**W11c-②③ 不晚於本項** | 同 Q4（單人、主控親套） |

**本節判準**：任兩包「並行」欄對稱；`quotawall.py`、`qw_schema.py`、`holder.py`、`seal.py` 的本稿改動只出現在 Q1 commit，**跨包欄名字面（`primary_wake_at`、`primary_source`、`backup_fire_at`、`close_stuck_window`、`desktop_notify`、`wake_at`、`target_source`、`session_switch_spawning`，r7 加保溫帳 `last_ping_pct`、`last_ping_at`、`ping_costs`，共十一個）只在 Q1 commit 新增、其他包只 import 常數**（AT-QW-61 以原始碼掃描鎖；判準限「字串常數整串等於欄名」，輸出格式字串如 `wake_at=`、`primary_wake_at=` 不算，QA3 P3-1）；兩支 hook 只在 Q4；`cases/**`／`cases.json` 只在 Q6；`sandbox_scope.SITES` 的 QW 四列只在 Q3；棘輪只在 Q7；`park_cli.py`、`handoff.py`、`session_resume_planner.py` 不早於 SE S2／S3 commit。

---

## 13. 模組落點表（照 `Root_Layout_and_Module_Placement.md` §2）
| 元件 | 路徑 | §2 格 |
|---|---|---|
| 判準（既有套件新模組） | `tools/lib/sessionctl/quotawall.py` | 函式庫（sessionctl） |
| 跨包欄名 schema（既有套件新葉模組，S-12） | `tools/lib/sessionctl/qw_schema.py` | 函式庫（sessionctl） |
| 量測（既有套件新模組） | `tools/lib/wastecensus/sections_wall.py` | 函式庫（wastecensus） |
| 指令入口 | `tools/sessionctl.py`：新動詞 `quotawall`；`keepwarm` 新旗標 `--idle-min`、`--heartbeat-min`（只准下修，供 E2E 縮時）；`park --status` 增列；`tools/probe/waste_census.py` 新旗標 `--calibrate-quotawall`（M-K7／M-K8／M-K9 併入 `--switch-metrics`） | 指令入口薄殼／量測探針 |
| 設定 | `tools/lib/quota_policy_env.py` `ENV_SPEC` 三鍵；`.env.example` | 既有額度設定 SSOT |
| hook 接點 | `.claude/hooks/check_pending_handoff.py`、`.claude/hooks/sessionctl_guard.py` | 守衛面（主控親套） |
| 測試 | 新 `tools/tests/test_sessionctl_quotawall.py`、`tools/tests/test_waste_census_wall.py`；其餘擴充既有檔 | 測試 |
| E2E | `tools/lib/realverify/cases/quotawall.py`；結果帳 `docs/06_quality/RealVerify_Result_Ledger.md` | realverify 既有套件 |
| 痕跡 | `trace_dir()` 下 `autosdd_session_switch.jsonl`（新事件 `quotawall_plan`、`quotawall_block`、`quotawall_override`、`quotawall_stop_muted`、`keepwarm_defer`、`primary_wake`、`park_yield_primary`、`park_attempt`、`park_chain_failed`、`park_failure_notice`、`sentinel_park_takeover`、`oldwin_close_degraded`、`session_switch_spawning`、`keepwarm_early_reset`、`quotawall_backup_absent`、`park_intent_expired`（r5）、`park_spawn_recovered`（r5）；`keepwarm_verdict` 新值 `handed_over`；`session_switch_spawned` 新欄 `new_sid`／`route`／`recovered`（r5））；S-18 閂鎖檔 `trace_dir()/quotawall/<sid>.json` | repo 外執行期痕跡 |
| 規格 | 本稿；TCS | 需求／設計、測試契約 |
| CI | sessionctl／wastecensus／hooks／planner 既有 paths 已涵蓋，不新增 | CI 接線 |

---

## 14. 被否決的方案
| 方案 | 否決理由 | 反向鎖 |
|---|---|---|
| r1「依 D 分兩桶」 | 今天兩牆省 0（QA P2-1） | MU-QW-15 |
| park 到點先關同 sid 活窗再 `-r`（R217 §7.1 用於 park） | 用殺使用者 TUI 解一個本視窗自己就能被叫醒的問題；映像改名即失效（24 次 0 成功） | MU-QW-22、E2E-QW-14 |
| 活窗存在時 park 直接 skip | 主載具失敗時就沒有任何人接手（R217 r3 D-14 已指出的空窗） | AT-QW-47 |
| 新增獨立 `waituntil` 指令 | 冷叫醒閘豁免、holder 互斥、保溫帳要再造一份 | — |
| 付不起就不掛保溫（r2 `quota_doomed` skip） | 22:42 事件：保溫跨不過 reset 就等於沒人叫醒 | MU-QW-15、AT-QW-23 |
| 主策略不掛 park 後備（r2 S-10） | 關窗／長睡／主載具失敗時無人接手 | AT-QW-40 |
| `park --wall` 獨立模式＋黏性＋刷新 | r3 收尾單一流程後無用，多一套判準多一個家 | — |
| 失敗後 park 自己再排一次重試 | 與哨兵接手重複（兩個家做同一件事）；哨兵已是零 token 巡邏 | — |
| 失敗出聲強制開桌面通知 | 違反使用者「預設不敲」直接指令（`quota_escalation.py:547-548`）；改以人眼必經入口保證 | AT-QW-53 |
| 一進準備帶就擋全部派工 | 抵觸「額度用到接近滿」 | AT-QW-15 |
| 準備帶以 `quota_policy.decide` band 判 | 配速床會把低讀數墊成 prepare | MU-QW-03 |
| 牆中照常推回／叫醒 | 全部 429（T926、T1636、T1645） | MU-QW-10、MU-QW-13 |
| 單次長 sleep 等到目標 | 睡眠跨過截止時行為未定；PRD §4.5.2 同型教訓 | MU-QW-17 |
| 校準值自動寫回 | 量測改判準、繞過人審 | AT-QW-29 |
| （r4）macOS 以哨兵 launchd `claude -p -r <sid>` 無頭續跑作備援 | 同 sid 活窗可能仍在＝兩個駕駛；加 `--fork-session` 則把互動工作交給無人窗口（S4 語意）且不受 R218-B 開窗站點規範 | AT-QW-65 |
| （r4）mac chain 段長改 <30 分 | 付費次數約 ×1.8、更常退成 single，而 single（數小時）本身就擋不住「閒置被收」——段長治不了根；改心跳（零成本）＋出聲＋OI | — |
| （r4）Q3 改在 Q2 之後串行以避開跨包欄位 | 拉長關鍵路徑且仍是兩個家；葉模組一次解掉鐵律七與循環匯入 | AT-QW-61 |
| （r4）以 L1 未授權拒絕驅動失敗鏈 E2E | L1 拒絕是終局 `refused`、不進失敗鏈（SE D-13）；改假 `claude` rc≠0 注入 | MU-QW-32 |
| （r4）keepwarm `resume` 時不重判交棒 | 讓路上限後／S6 後舊窗晚醒＝兩個駕駛（QA2 P2-3） | MU-QW-29 |
| （r5）S-19 只看「reset 晚於計畫」 | reset 估早而視窗未翻也成立 ⇒ 牆內叫醒（429）或牆前撞牆（QA3 P2-1） | MU-QW-38 |
| （r5）S-18 閂鎖以 reset 精確值當鍵 | 觀測 reset 同窗可漂移 70 分以上 ⇒ 每回合推回再現（QA3 P2-3） | MU-QW-40 |
| （r5）fork 沿用 `grew()`（原逐字稿變大即成功） | 舊窗自己寫原逐字稿即假成功＝零駕駛（QA3 P2-4） | MU-QW-41 |
| （r5）只在 park 路徑延後解除哨兵（傳 `disarm=` 注入） | 同一函式兩種語意＝兩個家；互動路徑失敗時保留哨兵無害（QA3 P2-5） | MU-QW-42 |
| （r5）spawning 意圖永久有效 | job 崩潰即無聲零駕駛（QA3 P2-6） | MU-QW-43 |
| （r6）spawn 站點 L1 拒絕當一般失敗、改走另一路 | 替不合法目標再試一次；沙盒內的 handback／通知即 S14 外洩（SE D-13） | MU-QW-44 |
| （r6）兩稿各自維護交叉介面字面 | 前三輪新缺陷多半是一邊改、另一邊沒跟上；改為 SE §10.2.1 單一真相源 | — |
| （r7）ping 實測 Δ＝重掛啟動讀數 − ping 叫醒讀數 | 兩者相隔數十秒、讀數年齡 < 210 秒不補量，讀同一筆快取 ⇒ 正式環境 Δ 恆≈0（QA5 QW5-P2-1）；改相鄰兩次 ping 叫醒讀數差（S-25） | MU-QW-50 |
| （r7）`work_mark` 認重掛以外任何 `tool_use` | 讀 keepwarm 輸出的回合每次 ping 都歸零 ⇒ `periodic` cap 永不觸發、無限付費（QA5 QW5-P2-2）；改非唯讀且非監督（S-24②） | MU-QW-51 |
| （r8 評估）chain 中貪婪續付到付不起 | 剩餘一跳仍 > 50 分時同樣冷，續付全數沉沒（S-26） | — |

---

## 15. Token 帳（推論標明；單位＝`costmodel.py` 加權單位）
- r4 起未校準 `ping_pp` 隨 c 放大（S-3），下列 V／L 為 r4 值。
- **牆 A**（D≈224、c≈232k、ping_pp 0.504）：k＝4、V＝8.03、L＝13.03。保溫 4×p(232k)≈20.4 萬 vs 實付冷重寫 2×205,022≈41.0 萬 ⇒ 省約 20.6 萬。
- **牆 B**（D≈145、c≈309k、ping_pp 0.656）：k＝3、V＝8.59、L＝13.59。保溫 3×66.3k≈19.9 萬 vs 56.2 萬 ⇒ 省約 36.3 萬。
- **22:42 事件**（18:29 停工、短窗 90% ⇒ R＝10、D＝251、c≈43 萬、ping_pp 0.896、n*＝9、19:14 已 ping 1 次）：k＝ceil((251+2−50)/45)＝5，V＝12.06、L＝17.06 ⇒ 階段 nodispatch（與 QA2〈二〉推演一致；主控主動 `park`，90% 已過準備門檻）；affordable（10 ≥ 5×0.896＝4.48；r7 起只算未來 k：5 ≤ n* 9，19:14 那次 ping 是沉沒成本、不計）⇒ chain，保溫 5×p(430k)＝5×90,500≈45 萬vs 實付冷重寫 402,080×2≈80.4 萬 ⇒ 省約 35 萬，且 22:42 在原窗原地續工、無開窗。若付不起 ⇒ single：22:42 原地醒來冷重寫一次（與實付相同），但不會「沒人叫醒」。
- **2026-11-21 真機實證（E9；現行 R216 keepwarm 的 periodic 鏈，非本稿實作；r6 依主控以 Stop 守衛讀數核對的實數改正）**：01:2x 短窗 89%（R＝11）、D≈245、c≈44 萬 ⇒ 依本稿：p(c)＝92,500、ping_pp＝0.5×92,500/50,500≈0.916、k＝ceil((245+2−50)/45)＝5、V＝9×0.916＋4≈12.24、L≈17.24 ⇒ R 11 ≤ V ⇒ `close`；affordable（11 ≥ 5×0.916＝4.58；r7 起只算未來 k：5 ≤ n* 9）⇒ `chain k=5`。實際：保溫帳 k=1～5 為付費 ping，各次後讀數 91、92、93、93、94；k=6（04:16）醒來時已 reset。跨 reset 實付 **5 次 ping、89→94＝5pp（含首次收尾回合）**——≤ V 12.24，牆未撞。平均上界約 **1.0 pp／次 @ c≈44 萬**（收尾回合的份額無法從整數讀數拆出；量化誤差每段 ±1pp），**高於**未校準縮放值 0.916 約 9% ⇒ S-3 在此點**未證明偏保守**（r5「0.75 pp／次、偏保守」係把首段整段扣除所致，不成立，撤回）；V 仍守住，因 V 另含 W_CLOSE 與偵測項。**單點、未經 `--calibrate-quotawall`，不作校準值**（S-15 上線閘照舊；是否先調高 `PING_PP_REF` 見 §0.4-9）。帳：保溫 5×p(44 萬)≈46.3 萬 vs 冷重寫 2×44 萬＝88 萬 ⇒ 省約 41.7 萬加權單位，且 04:16 原窗熱快取續工。**照本稿 r5 流程重推（QA3〈二〉）**：R 11 ≤ V ⇒ `close` ⇒ 收尾登記 park（短窗讀數 89 已過準備門檻 ⇒ `primary_source=reset`）⇒ keepwarm `target_source=park`、`early=on`、chain k＝5，叫醒點約 02:00、02:45、03:30、04:15、05:00、目標 05:32。r4 下 S-19 對 park 不適用，會照付 05:00 那次 ping、05:32 才續工；r5 下 S-19 照樣生效：視窗翻新（實測不晚於 04:16）之後的第一個叫醒點即判 `resume`（最早 04:15、最遲 05:00），省 1～2 次 ping、提早 32～77 分續工，`.resumed` 使 park 備援到點 skip。r4 原句「照本稿 S-19 最後一次 ping 可省」在 r4 自己規定的流程下不成立（QA3 P2-2），以本段取代。
- **2026-11-21 第二次跨 reset（E10；r7 新增；現行 R216 keepwarm，非本稿實作；以下皆推論、單位同上）**：c≈48 萬 ⇒ p(c)＝100,500、ping_pp＝0.5×100,500/50,500≈0.995、n*＝9；05:2x 時 D≈205 ⇒ k＝ceil((205+2−50)/45)＝4、V＝8×0.995＋4≈11.96、L≈16.96。**實際**：陳舊讀數 86（R 14）只到 `nodispatch`；真值 95（R 5）早已 < V；第一段 6 次叫醒留帳，05:2x 之後付 3 次 ping（95→98→98→99），07:20 判 `cap k=9`，改背景等待 89 分到 08:53 叫醒——距上一筆主控 usage 約 89 分 > 60 分，推論為冷：3×p≈30.2 萬＋冷重寫 2×48 萬＝96 萬 ⇒ 約 126 萬。**照 r6 重推**：讀數 86 判 `nodispatch`；即使讀到 95，pings 6＋k 4＝10 > 9 ⇒ single，05:2x 起閒置約 3.5 小時必冷 ⇒ 約 96 萬。**照 r7 重推**：S-23 補量使讀數年齡 ≤ 210 秒，`close` 會在讀數到 89%（R 11 ≤ 11.96）時觸發，而非 95 才發現；S-24 只算未來 k＝4 ≤ 9 ⇒ chain；以 E10 實測每次約 1.33pp，k＝4 實付約 5.3pp＋收尾回合 ≤ V 11.96，牆不撞，reset 後熱快取續工：4×p≈40.2 萬 vs 96 萬 ⇒ 省約 56 萬。S-25（r8）自**第二次** ping 叫醒起才有第一筆實測（Δ＝相鄰兩次 ping 叫醒的讀數差；重掛啟動時不量），之後每次重掛的計畫改用 max(縮放值, 近 3 筆平均)，後續段落的預留隨實測上修；若讀數都補量成功、間隔內無真工作，本例 Δ 序列約 3、0、1（95→98→98→99），平均 1.33。補量失敗的情況下，外推 burn 1.0 比真實燒速更早收尾（QA5 推演），偏保守。**殘餘風險（r8 照實改寫，QA5 QW5-P3-1）**：補量也失敗、外推又低估跳升（本例 9pp 一次跳）時，可能要到 R＝5 才進 close（k＝4，4×0.995≈4.0 ≤ 5 ⇒ chain）。每次重掛都依 S-24 重算：第一筆實測到手時若單筆量化偏高（例 Δ＝3；真值約 1.33，整數讀數量化 ±1 再加上同帳號其他用量），重算得 k·Δ > R（例 剩 k＝3 需 9 > R 2）⇒ **中途退 single**，剩餘數段（最壞約 160 分）閒置而冷，reset 後原窗冷重寫一次；已付的 1～2 次 ping（每次約 10 萬加權單位）沉沒。這不是「撞牆後最後一段 > 50 分」（r7 原句的機制寫錯）：§5.4 只在牆內延後叫醒，退 single 發生在撞牆之前。評估過「已在 chain 中就續付到付不起」（貪婪續付）：剩餘一跳仍 > 50 分時同樣冷，續付的 ping 全數沉沒，期望值為負，**不採**（S-26）。由「近 3 筆平均」逐步收斂與 S-15 校準閘承接，登記殘餘風險、不另加守衛（無第二件暴露證據）。
- 收尾回合（W_CLOSE）是把本來會做的工作回合換成收尾，計入 V（少用的 pp），不另計 token。
- single 模式（付不起）閒置數小時可能遇上 harness 約 55 分的閒置自動壓縮（QA2 P3-7）：壓縮若落在牆內＝429、不耗額度；落在牆外＝一次摘要呼叫，其後叫醒時上下文已小。兩者都不改 V（single 本來就不預付保溫），只改醒來時的重寫量，由 M-K2 量；§5.4 牆內延後保證主載具自己不在牆內叫醒。
- 真實數字由 M-K7／M-K8／M-K9 量出；本節不作結案依據。

---

## 16. 真機驗證點 → E2E（不得需人按鍵；SE 沙盒；**任何 E2E 不真開窗**，spawn 正控一律 SE 替身 `claude`〔`--claude <path>`；`<家>/fakeclaude.mode`：RESUME 路正控 `resume_ok`、fork 與 FRESH 路正控 `fresh_ok`、失敗鏈 `fail`；正控不以 rc 0 判，案例讓 F4 選路可預期並斷言 `park_route` 的 route 與模式一致；同一替身貫穿 RESUME／FRESH／fork／失敗鏈另一路／哨兵接手（哨兵讀標記 `claude` 欄）〕；長案例宣告 `lease_minutes` 且 `fire_at ≤ allow_until`〔`LEASE_CAP` 300 分〕；以上介面字面以 SE §10.2.1 為準）
| # | 待證點 | E2E（恆可跑或 ENV） | 不跑的一半 → 承接 |
|---|---|---|---|
| V-W1 | 長等待（≥4 小時）後 harness 仍叫醒 | E2E-QW-24：`claude -p` 以 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`＝5 小時掛 keepwarm single 4 小時（long 類，`MIN_WALL_SECONDS`＝14400；`lease_minutes`＝270），斷言結束後逐字稿出現新 assistant 記錄。harness 不接受該上限 ⇒ ENV | 互動視窗數小時單跳：不真開窗 ⇒ **OI 未結**（§17），上線後以 M-K8「跨重置成功」觀察承接。兩半皆無 PASS 時不得宣稱 V-W1 已驗（主控裁示） |
| V-W2 | 睡眠／凍結跨過截止 | E2E-QW-08：真 keepwarm 行程以 `NtSuspendProcess` 凍結跨過截止 3 分後恢復，≤65 秒內結束且判 `resume` | 真 OS 睡眠變體（opt-in `AUTOSDD_RV_ALLOW_SUSPEND=1`＋喚醒計時器，不需按鍵；未 opt-in 判 ENV） |
| V-W3 | CC 自動更新改名後背景叫醒仍有效、家族比對 | E2E-QW-17：沙盒 `claude.exe` 副本以 `-p` 起跑後把執行中映像改名為 `claude.exe.old.<ts>.<pid>`（與更新器同手法），背景 keepwarm 結束仍叫醒；`QueryFullProcessImageNameW` 回新名；家族判準接受、`claude-x.exe` 拒絕 | 長壽互動窗：OI（§17） |
| V-W4 | 醒在牆內（reset 估錯） | E2E-QW-09：T5 替身在目標時刻回 100％＋新 reset ⇒ defer；端點 500 ⇒ 照原目標醒；(c)(d) 提前重置（reset 來源與 park `primary_source=reset`）；(e) reset 變晚但讀數未降 ⇒ 不提前（r5） | — |
| V-W5 | 閒置 55 分自動壓縮 | 量測（M-K2 既有）＋E2E-QW-06 鏈的每段 ≤ idle；single 模式的壓縮成本不入 V、由 M-K2 量（§15 末條） | — |
| V-W6 | Stop 閘相容 | E2E-QW-10：真 hook，封存＋keepwarm 在跑 ⇒ 不推；`.resumed` 後在飛代理 ⇒ 不推 | — |
| V-W7 | 視窗被關後備援接手 | E2E-QW-13：殺掉掛 keepwarm 的 `-p` 行程樹 ⇒ 真排程到點、holder 已死；足夠租約＋`--claude` 替身 `mode=fail` 注入失敗 ⇒ 失敗鏈；替身 `resume_ok`（F4＝RESUME 可預期）／`fresh_ok`（F4＝FRESH 可預期）⇒ 正控，斷言 `park_route` 的 route 與模式一致（不以 rc 0 判）；未授權 ⇒ 負控（L1 `refused`、不進失敗鏈） | 真開窗：不跑（主控裁示） |
| V-W8 | `--fork-session` 得新 sid 承接歷史、舊行程不受影響 | E2E-QW-14：沙盒活窗行程（改名映像）不受 fire 影響；替身（`fresh_ok`）argv 含 `--fork-session`、新檔 sid ≠ 原 sid、原逐字稿未被替身寫入（S-20）；另以真 `claude -p -r <sid> --fork-session "ok"`（無頭、非開窗）驗新 sid 逐字稿含原歷史、原逐字稿位元組不變 | 互動 fork 開窗：OI（§17） |
| V-W9 | 22:42 事件重放（修前紅修後綠） | E2E-QW-22 變體 A（主載具正常）與 B（主載具被殺 ⇒ 備援 fork；改名映像活窗、替身 `claude`） | — |
| V-W10 | `-p` 背景完成後模型被叫醒（V-W1／V-W3／E2E-QW-24 的前提） | E2E-QW-27（約 2 分，RV-KW6 同型） | — |
| V-W11 | macOS 載具（心跳、`backup=absent(platform)`、到點只出聲） | E2E-QW-28：mac 宿主真跑；非 mac 宿主判 ENV | mac 自動重開：OI（§17） |
| V-W12 | （r7）陳舊讀數（E10 ①）：補量、外推、舊窗、閂鎖／參照不吃舊讀數 | E2E-QW-29：T5 替身先回陳舊 86（案例把快取讀數時戳改早），再跳 95 | — |
| V-W13 | （r7）第二次跨 reset 重放（E10 ②③）：殘留保溫帳不擋 chain、真工作歸零、ping 實測取大 | E2E-QW-30 | — |

---

## 17. 理論洞清單與 OI 清單（r4；Q7 抄進證據檔，主控凍結時 `openitems.py open` 登記）

### 17.1 理論洞（根 CLAUDE.md〈守衛面准入〉：無暴露證據 ⇒ 只登記、不擴守衛）
| # | 洞 | 為何不修 | 再開症狀 |
|---|---|---|---|
| TH-1 | 主控自己長時間 inline 工作，一個回合內從 `close` 燒到撞牆：沒有回合內觸發點（PreToolUse 只擋派工），收尾要等回合結束的 Stop（QA2 P3-6） | 兩次真實撞牆（T935、T1665）皆代理在燒、watch 接得住；無真實語料命中 | 任一撞牆逐字稿顯示「牆前最後一個回合是主控 inline、跨過 `close` 而無 Stop」（附 sid＋行號） |

### 17.2 OI（未結、不得以替身宣稱已驗）
| # | 項 | 承接 |
|---|---|---|
| OI-a | V-W1 互動視窗數小時單跳（E2E-QW-24 只驗 `-p` 半；若 `-p` 半也 ENV，則 V-W1 整體無驗） | 上線後 M-K8「跨重置成功」≥1 件且屬 single 模式（附 sid）才結 |
| OI-b | V-W3 長壽互動窗跨自動更新後背景叫醒 | 同上，M-K8 與 `QueryFullProcessImageNameW` 痕跡 |
| OI-c | V-W8 互動 fork 開窗 | 上線後 M-K9 出現 `fork` 路成功一件（附新舊 sid） |
| OI-d | macOS：心跳能否擋住閒置收回；mac 無自動開窗備援（S-14、§0.4-7） | 主控決定是否補 mac 開窗載具；E2E-QW-28 在 mac 宿主 PASS |
| OI-e | 校準上線閘（S-15）區間不足時 | `--calibrate-quotawall` 三鍵有值並寫入 `env.shared` |
| OI-f | E2E-SE-17（SE 站點的 L1 真機驗證，案例程式隨 Q6） | Q6 收尾結案 |

### 17.3 r9 增補（2026-11-23 撞牆 RCA；規格住附錄 H）
- **否決方案**（RCA §7 五項，WHY 見附錄 H.5）：調低 prepare／halt 門檻；改 `_binding_key` 平手規則；讓配速床與攤提也吃燒速；只靠提示詞約束子代理時序；把撞牆 FAIL 改成 skip。
- **理論洞** TH-2、**OI** OI-g／OI-h：見附錄 H.6。

---

## 附錄 A：PRD 修憲（§16.5 (i)；本棒已追加進 PRD，修憲前原文一字不動）
| 編號 | 落點 | 內容摘要 |
|---|---|---|
| A-1 | 修訂表 v2.1.22 列之後（v2.1.25 列之前） | **v2.1.24** 列（r3 重寫；合併 R218 與 R218-C 兩次立案原文）。v2.1.23 由 R217 預留，落款時插在本列之前 |
| A-2 | §4.2.3 v2.1.16 落款引言之後、§4.2.4 之前 | `【v2.1.24 新增】` 額度牆預留閘（r3 重寫：階段、收尾流程、單跳） |
| A-3 | §4.5.7 末、`#### 4.5.8` 之前 | `【v2.1.24 新增】R-4.5.7-4（牆後段）`（r3 重寫：keepwarm 牆內不結束、延到 reset＋s）。R217 附錄 A-9 錨點是「偏離 2 之後」：A-9 緊接偏離 2、本段恆為 §4.5.7 最後一段 |
| A-4 | §4.5.10 末（v2.1.16 W3 落款引言之後）、`### 4.6` 之前 | **新增 `#### 4.5.11` 續航情境矩陣與載具分層【v2.1.24 新增】**：R-4.5.11-1～6（矩陣規範性、視窗存活優先原地喚醒、禁止以終止互動視窗為續跑前置、失敗不得無聲、保溫與到點喚醒統一、雙憑證）＝CARC ④ A-1～A-5 與 R-9 |
| A-5 | §11.3 末（v2.1.22 註記之後） | `【v2.1.24 註記】` 互動視窗仍開著時的到點喚醒 E2E 要求（CARC ④ A-6） |
| A-6 | §11.4 末（v2.1.25 註記之後） | `【v2.1.24 註記】` 週窗以外部排程為主、W1 並掛（CARC ④ A-7） |
| A-7 | §16.6 2026-11-18 列之後、R218-B 列之前 | 2026-11-20 列（r3 重寫）。依 R217 附錄 A-5／A-11，結案格不用 ⏸；待實作與待驗收由 OIR 承接（OI-20261121-003），主控凍結本規格時以 `python tools/openitems.py open` 登記（實作 1＋E2E 全數）後回填 |

**本附錄判準**：E2E-QW-21 以修憲前 blob（R217 收尾 commit 已落地則用其 SHA，否則 `133c3a38`）比對——修憲前每一行位元組不變，本稿新增恰為上表七處；R217（`OI-` 標記）與 R218-B（v2.1.25）並行追加另列。

---

## 附錄 B：QA FAIL（r1）逐條處置（r3 現況）
| QA | 處置 | 座標 |
|---|---|---|
| P1-1 冷叫醒閘矛盾 | 收尾先 TaskStop 再封存（D-D）；keepwarm 豁免既有；`.resumed` 後不推（§8） | §6.2、§8；AT-QW-22、AT-QW-51、MU-QW-19 |
| P1-2 `quota_doomed` 以 D 判 | 預算判；付不起＝單跳（不是不掛）；park 不再使保溫跳過 | §5.1、§5.2；AT-QW-21、AT-QW-23、MU-QW-15 |
| P2-1 今天兩牆省 0 | 主策略跨重置保溫；§15 誠實帳 | D-A、§15 |
| P2-2 V 未算偵測延遲與收尾 | `V(k)＝(k+W_CLOSE)·ping_pp＋DETECT_MIN·burn`，W_CLOSE＝4 | S-2、§3；AT-QW-07、MU-QW-02 |
| P2-3 一進準備帶就擋派 | 擋派線 L＝V＋AGENT_EST | §6.1；AT-QW-15 |
| P2-4 R217 衝突 | ①牆中 `check_pending_handoff` 三推回靜音；②準備帶完成閘只出聲、OIR 不關 keepwarm；③§16.6 寫 OI；④A-3 在 A-9 之後；Q4 納兩支 hook | §6.4、附錄 A |
| P3-1 k 多排；watch 路徑不一致 | S-1；`schedule` 共用 | §5.2、§5.7；AT-QW-20 |
| P3-2 AGENT_EST 無數據 | 納入校準、逐鍵標未校準 | S-3；AT-QW-29 |
| P3-3 E2E-QW-07 ENV 卡死 | 選路／失敗鏈痕跡（恆可跑）與開窗拆開；r4 起開窗半撤除，正控改假 `claude`（附錄 C） | §16；TCS E2E-QW-13～15 |
| P3-4 haiku 不一定呼叫 Agent | 先斷言 tool_use 出現，沒出現判 ENV 重跑 | TCS §4 共通 |
| P3-5 wall 條件① | 「最後切斷之後無續接、無新 usage」；斷言 `source` | §3；AT-QW-09 |
| P3-6 MU 缺口 | 補齊（TCS §5） | TCS §5 |
| P3-7 E2E 基準 | 附錄 A 判準 | E2E-QW-21 |
| P3-8 補量端點 | T5 替身同時作補量端點；hook 行程讀到非替身讀數即 fail「載具漏接」 | TCS §4 共通 |

---

## 附錄 C：QA 第二輪（r3 FAIL：P2×5、P3×7）逐條處置（r4）
| QA2 | 處置 | 座標 |
|---|---|---|
| P2-1 期望值與公式矛盾 | E2E-QW-01 第 4 組改 94%（R＝6＝V，等號邊界）；AT-QW-23 第 1 例改期望 `periodic`（逐步重算：c＝30 萬 ⇒ ping_pp 0.639、k＝2、V＝7.83、L＝12.83、R＝14 ⇒ free）；補第 3 例「93%、`close`＋無標記 ⇒ chain、`target_source=reset`」；因 S-3 縮放，凡依賴 V 的 AT／E2E 一律寫明 c | TCS E2E-QW-01、AT-QW-01／05／07／15／23 |
| P2-2 E2E-QW-22 不會變紅 | 變體 B「主載具被殺 ⇒ 備援面對活 cli 窗＋改名映像」，斷言替身 argv 含 `--fork-session`、改名行程同 pid 同建立時刻仍在；MU-QW-22／25 必紅加 E2E-QW-22(B)；常態半一律沙盒 `claude.exe` 副本執行中改名（E2E-QW-14 同）；T 複本時間戳平移到 now；斷言 `mode`；重掛驅動器＝案例本身附加 T 真實記錄複本（43 萬上下文超出 haiku 視窗，不以 `-p -r` 重掛） | TCS E2E-QW-14／22、MU-QW-22／25 |
| P2-3 兩個駕駛 | `KEEPWARM_VERDICT=handed_over`（每個叫醒時刻重判）；§8 觸發 1／2 加「包未 spawn」；spawn 前寫 `spawning` 意圖；§7.3 拆四分支（正常釋放獨立） | S-13、§5.5、§7.3、§7.4、§8；AT-QW-63／64／66、E2E-QW-12(d)、MU-QW-29 |
| P2-4 macOS 無備援 | §2.2 加平台欄；mac 備援＝出聲（`platform_unsupported` 進失敗鏈終點）、心跳、`backup=absent(platform)`；自動重開登 OI | S-14、§2、§5.8、§7.1、§7.4、§17；REQ-QW-38、AT-QW-65、E2E-QW-28、MU-QW-31 |
| P2-5 Q2∥Q3 欄位分家 | 葉模組 `qw_schema.py`＋holder／seal 改動收進 Q1；§12 判準加「欄名字面只在 Q1」 | S-12、§12；REQ-QW-63、AT-QW-61、MU-QW-34 |
| P3-1 `-p` 叫醒已有實證 | 引 RV-KW6；前置案例 E2E-QW-27；改寫 TCS §6 末段：V-W1 無恆可跑常態半，ENV 時登 OI | §0.4-3、§16、§17；TCS §6 |
| P3-2 校準必要 | 未校準 `ping_pp` 依 p(c)/p(23 萬) 放大；上線閘＝校準有值 | S-3、S-15；REQ-QW-54／55、AT-QW-62、E2E-QW-20、MU-QW-30 |
| P3-3 OIR 注入讓主載具閘失聲 | 主載具閘以原始環境判 `off` | §6.3、§11；AT-QW-67、MU-QW-33 |
| P3-4 `park.stop_verdict` 與 watch nodispatch | free／nodispatch 不推 park；watch nodispatch 處置文字 | S-16、§6.2、§6.5；AT-QW-68 |
| P3-5 fork 與交接包；R217 關舊窗成功路徑 | fork 算交棒、新 sid 先 ack；R217 跨 sid 關舊窗（改名映像）成功路徑 E2E | §7.4；E2E-QW-26 |
| P3-6 主控 inline 燒到牆 | 理論洞，登記不擴守衛 | §17.1 TH-1 |
| P3-7 single 閒置壓縮成本 | 註明不入 V、由 M-K2 量 | §15、§16 V-W5 |
| R218-B r2 同步（主控追加） | E2E-QW-13 改足夠租約＋`--claude` 替身 `mode=fail`（r2 第二輪 QA 後：正控 `resume_ok`／`fresh_ok`、不以 rc 0 當正控；同一替身貫穿 RESUME／FRESH／fork／另一路／哨兵接手，REQ-QW-44；真 traces 只判新增段無沙盒字樣）；Q3 四個新站點同 commit 進 `SITES`（§7.3 重排用 `register_verdict`）、AT-SE-39 隨 Q3；觀察期／`park_yield_primary`／`park_attempt` 在 L1 之後、L1 拒絕＝`refused`、哨兵只認 `failed`；E2E-SE-17 隨 Q6 落 `cases/sideeffect.py`；spawn 類 E2E 全帶 `--claude`、長案例宣告 `lease_minutes`、`fire_at ≤ allow_until` | §7.0、§7.3、§7.6、§12 Q3／Q6、§16；TCS §4 共通、E2E-QW-13、AT-QW-69 |
| 2026-11-21 真機實證（主控追加） | 納入校準佐證與 §15 帳（E9）；兩閘每次 ping 都推回 ⇒ S-18（主載具憑證：midwork 認帶目標 keepwarm、缺 park 每 (sid, reset) 只推一次）；reset 早於估計 ⇒ S-19 提前重置 | §1 E9、S-3、S-18、S-19、§5.5、§6.2、§6.4、§15；REQ-QW-26／43、AT-QW-25／70、E2E-QW-04(f)／09(c)、MU-QW-35 |

---

## 附錄 D：QA 第三輪（r4 FAIL：P2×6、P3×7）逐條處置（r5）
| QA3 | 處置（WHY 見 §0.3 對應代決） | 座標 |
|---|---|---|
| P2-1 S-19 歧義 | 加合取「讀數已降」（`early_reset`：obs reset > ref ∧ obs pct < min(ref_pct, 100)）；defer 時參照更新為（新 reset, 100）；同窗讀數上升 `ref_pct` 取最大值；PRD R-4.5.11-2 括號加「且讀數已降」 | S-19、§3、§4、§5.5；PRD R-4.5.11-2；REQ-QW-26；AT-QW-25（補兩反例＋defer 後一輪）、E2E-QW-09(e)、MU-QW-38 |
| P2-2 close 流程停用 S-19 | park 標記加 `primary_source∈{reset,at}`（欄名住 `qw_schema`）；來源 reset 時 S-19 照樣生效（`early=on`），提前續工以 `.resumed` 使備援 skip；§15 E9 結論改正 | S-12、S-19、§3、§5.2、§5.5、§7.1、§15；REQ-QW-22／26／30；AT-QW-75、E2E-QW-09(d)、MU-QW-39 |
| P2-3 閂鎖鍵不穩 | 視窗身分 `same_window`：讀數已降或已過閂鎖 reset＋60 分才算換窗；reset 漂移不算 | S-18、§4、§6.2；REQ-QW-43；AT-QW-70（補 ±5、+70、換窗兩法）、E2E-QW-04(f)、MU-QW-40 |
| P2-4 fork 假成功 | S-20：只認新出現、stem ≠ 原 sid 的 jsonl ∧ 行程活；fork 路不 `mark_resumed`；替身 fork argv 用 `fresh_ok`（SE r3：只寫新 uuid 檔；`resume_ok` 遇 fork argv 照 fail） | S-20、§7.4、§16；REQ-QW-48；AT-QW-72、E2E-QW-14／22(B)、MU-QW-41 |
| P2-5 `handoff.spawn` 副作用 | S-21：成功後才解除哨兵（全呼叫端同語意）；dedup 只認 `ok=True` 或行程仍活；Q3 檔案清單補 `handoff.py`＋測試，寫明「先 SE S2、後 Q3、同檔不並行、與 SITES／AT-SE-31 重釘同 commit」 | S-21、§7.4、§7.6、§12；REQ-QW-49；AT-QW-73、E2E-QW-15、MU-QW-42 |
| P2-6 意圖無期限 | `SPAWN_INTENT_TTL_SEC`＝max(兩個 spawn 等待)＋60＝90；逾時無成功列不算交棒；哨兵把非終態標記＋過期意圖視同 failed 接手並出聲，先查「前次其實成功」防雙駕駛 | S-13、§3、§7.4、§7.6、§13；REQ-QW-36／42；AT-QW-66（補過期例）、AT-QW-74、MU-QW-43 |
| P3-1 AT-QW-61 掃描衝突 | 判準限「字串常數整串等於欄名」；wastecensus 改 import `qw_schema` | §12；AT-QW-61 |
| P3-2 REQ-QW-47 無 MU；標記不可 grep | MU-QW-37；測試 sid 含模組常數 `OLDWIN_TEST_SID_MARK`，E2E-QW-18 import 後 grep | §9；AT-QW-54、E2E-QW-18、MU-QW-37 |
| P3-3 ping 次數＝k 邊界 | 改為依實際各錨點逐段重算之值（必在 [k−1, k]） | TCS E2E-QW-06／22(A) |
| P3-4 E9 計數 | 改為「跨越 reset 期間 5 次 ping（01:15～04:16，計數 2→6），保溫帳起點 1」；affordable 改 pings 1＋5；帳改 5×p（**r6 再改正**：計數與 0.75 pp 結論依主控核對實數更正，見附錄 E） | §1 E9、S-18、§15 |
| P3-5 04(f) 修前紅前提 | 載具保證 Stop payload 的逐字稿含本回合啟動 keepwarm 的 PowerShell 呼叫（非唯讀工具）⇒ midwork 狀態佐證恆成立 | TCS E2E-QW-04(f) |
| P3-6 SE 替身介面 | 已依 SE r3 交卷稿逐字對齊（`<家>/fakeclaude.mode`、三值、fork→`fresh_ok`、哨兵讀標記 `claude` 欄、`sandbox_real_exe`）；**SE r3 凍結後由主控 diff 核對，列為本稿凍結前置** | §0.4-8、§0.6 R-8、§7.4、§7.6、§16；REQ-QW-44 |
| P3-7 S-18 競態 | holder 缺席時同一 keepwarm 背景任務 id 只寬限一次 Stop | S-18；AT-QW-70 |
| 主控追加⑦⑧⑨（R218-B r3） | ⑦正控不以 rc 0、斷言 `park_route` route 與模式一致；⑧fork／另一路傳 `opts.claude`、哨兵讀標記 `claude` 欄、Q3 同 commit 補三處 argv[0] AT；⑨AT-SE-31／E2E-SE-09 黃金序列由 Q3 同 commit 重釘 | §0.6 R-8、§7.4、§7.6、§12 Q3、§16；AT-QW-71、TCS §4 共通 |

---

## 附錄 E：r6 聯合改版（與 R218-B r4）逐條處置＋QA 第四輪判準自我核對
| 來源 | 處置 | 座標 |
|---|---|---|
| 主控裁示：交叉介面逐字一致 | 介面字面改以 SE §10.2.1 X-1～X-18 為單一真相源；§0.4-8 改寫為「兩稿同 commit 凍結、逐列核對」；§0.6 R-8、§16 表頭、TCS §4 共通改引用 | §0.4-8、§0.6、§16；TCS §4 共通 |
| SE 第三輪 QA P2-2（主控裁示：§7.5 L1 refused 終局） | §7.0 分 fire／spawn 兩站點；§7.5-1a；§7.6 接手中被拒結局 `refused`；S-22 | §7.0、§7.5-1a、§7.6、S-22；REQ-QW-34／39、AT-QW-69③、MU-QW-44 |
| SE 第三輪 QA P2-3（與 S-17 衝突） | S-17 對齊 SE D-20 r4：沙盒拒不允許值、正式不轉送照常登記；§7.1 加 `job_env_argv(env, sandbox=)`；TCS 共通：沙盒「通知開」輪改為登記後改寫標記（r5 寫「登記行程設 1」在 SE 下會 rc 2，**本稿 r5 自身缺陷**，一併修） | S-17、§7.1；TCS §4 共通、E2E-QW-15；SE E2E-SE-09(c) |
| SE 第三輪 QA P2-1（沙盒工作樹髒） | TCS 共通加「建好居所與替身後 porcelain 空」前置（SE D-23） | TCS §4 共通 |
| SE 第三輪 QA P2-4／P3-1／P3-5 | `park_attempt` 恰 1 筆與 Q3 重釘範圍（§12 Q3）；`park.STATUSES` 由 SE S2 提供、Q3 消費；E2E-QW-15 哨兵武裝改 `ctl_env(arm_sentinel=True)` | §12 Q3；TCS E2E-QW-15 |
| E9 實數改正（主控以 Stop 守衛讀數核對） | k=1～5 付費 ping（91、92、93、93、94）、k=6（04:16）已 reset ⇒ 5 次、5pp、平均約 1 pp／次；撤回 r5「0.75 pp、S-3 偏保守」與「保溫帳起點 1／2→6」；affordable 改 pings 0＋5；S-3 改寫為「此點未證明偏保守、V 仍守住」；§0.4-9 開放題 | §1 E9、S-3、S-18、§15、§0.4-9 |

**QA 第四輪判準自我核對（`r218_qa4_brief.md`）**：
1. 第三輪 P2-1～P2-6、P3-1～P3-7、主控⑦⑧⑨：附錄 D 各列座標逐一現查存在；P3-4 的 E9 計數本身有誤，r6 再改正（上表末列）。
2. S-19 三條件、`primary_source`、`same_window`（60 分）、S-20、S-21、TTL 90：邊界由 AT-QW-25④～⑦、AT-QW-70 六例、AT-QW-72 四例、AT-QW-73 七例、AT-QW-66／74 鎖；突變 MU-QW-38～43 各自有必紅 AT。未發現互相矛盾。
3. 今晚實證與 22:42 重放套進 r6：E9 走 `close`→park（`primary_source=reset`）→chain k=5、S-19 於翻窗後首個叫醒點 `resume`；22:42 變體 A 原地續、B 備援 fork（替身 `fresh_ok`）；任一路被 L1 拒 ⇒ `refused` 終局（不開窗、不需人）。無斷鏈／需人／真開窗點。
4. 與 SE r4 介面：X-1～X-18 逐列兩邊座標已填；工作包序 SE S2 先於 Q3、`handoff.py`／`park.py`／`park_cli.py` 同檔不並行（§12）。**r5 自查出的唯一跨稿缺陷**＝E2E-QW-15「登記行程設通知 1」與 SE 允許表衝突（已修）。
5. 計數：REQ 58、AT 75（AT-QW-69 擴為三例，不增號）、E2E 28、MU 44（+MU-QW-44）；覆蓋 58／58；PRD 只追加（v2.1.24 段為本輪未凍結草案，就地改 R-4.5.11-4 一句）。

---

## 附錄 F：聯合 QA 第四輪（r6 FAIL：P2×2、P3×3）逐條處置（r7，與 R218-B r5 聯合改版）
| QA4 | 處置（WHY 見 §0.3 對應代決） | 座標 |
|---|---|---|
| Q-P2-1 陳舊額度讀數使預留線晚觸發 | S-23：`Plan` 帶 `reading_at`；年齡 > TTL＋POLL（210 秒）先零 token 補量；補不到以 `R_eff＝R − ceil(age/60)·burn` 保守外推並印 `stale=yes reading_age=`；舊窗讀數 ⇒ `none reason=stale_window`；keepwarm／watch 每個叫醒時刻先補量；早於閂鎖 `latched.at`／參照 `ref_at` 的讀數不參與 `same_window`／`early_reset`、不更新 `ref_pct`；§1 加 E10；§16 加 V-W12；TCS 共通把「刻意製造的 stale」排除在「載具漏接」之外 | S-23、§1 E10、§3（R、`ref`）、§4（`plan`、`early_reset`、`same_window`）、§5.2、§5.5、§12 Q1／Q2、§15、§16；REQ-QW-64、AT-QW-11（改）／76／77、E2E-QW-29、MU-QW-45／46 |
| Q-P2-2 保溫帳 n* 跨段累計 | S-24：有目標時 `affordable＝R ≥ k·ping_pp_eff ∧ k ≤ n*`（只算未來 k；歷史 pings 是沉沒成本）；`cap` 只留給 `periodic`；保溫帳歸零加「主控真工作記錄（`work_mark`）」與「視窗翻新（`resume`／`early_reset`）」；E2E-QW-07(c) 改為期望 chain；補殘留 pings 6 ⇒ chain 的 AT；§15 補第二次跨 reset 帳（cap k=9 於距 reset 89 分耗盡、改 single、08:53 原窗叫醒） | S-24、§3 `affordable`、§5.1、§5.2、§12 Q2、§15；REQ-QW-21／23（改）、REQ-QW-65、AT-QW-21（改）／78／79、E2E-QW-07(c)（改）／30、MU-QW-47／48 |
| Q-P3-1 ping 成本隨上下文放大 | S-25：keepwarm 記每次 ping 的實測讀數差（`ping_costs` 最近 5 筆），計畫取 `max(縮放值, 近 3 筆平均)`、印 `ping_pp_src`；不推翻 `PING_PP_REF＝0.5`（S-15 校準閘照舊）；§0.4-9 註明第二點 | S-25、§0.4-9、§3 `ping_pp`、§12 Q1／Q2；REQ-QW-66、AT-QW-80、E2E-QW-30(c)、MU-QW-49 |
| Q-P3-2 X-4 座標、X-11 `--why` | SE §10.2.1 X-4 的 QW 座標改為 TCS §4 共通與 §0.4-8；X-11 改「Q3 前＝原登記時刻（`--at` 值；短窗／`--why` 登記＝reset＋s）」 | SE §10.2.1 |
| Q-P3-3 表外交叉介面 | SE §10.2.1 補 X-19（park 登記附帶武裝本 sid 哨兵，§7.1）、X-20（痕跡名與 reason 詞彙）、X-21（`ctl_env(arm_sentinel=True)`）、X-22（`park --status` 兩稿加列） | SE §10.2.1；本稿 §7.1、§10 |
| B-P2-1（SE，涉本稿 §7.1） | 本稿 §7.1「park 登記時嘗試武裝本 sid 哨兵」不改；SE E2E-SE-09 (a)(b) 登記行程設 `SENTINEL_OFF=1`，(c) 先把 `AutoSDD_Sentinel_<sid>` 記入 L2、斷言武裝後撤除，L2 發現式掃描加認 `AutoSDD_RVprod_`（SE 持有面） | SE §5.3、§10.2.1 X-19；SE TCS E2E-SE-09 |
| 計數 | REQ 58→61、AT 75→80、E2E 28→30、MU 44→49；覆蓋 61／61；跨包欄名 8→11（REQ-QW-63、AT-QW-61、§12 判準） | TCS 表頭、§6、§7；PRD §16.6 本列 |

**本輪自查**：①新號 REQ-QW-64～66、AT-QW-76～80、E2E-QW-29／30、MU-QW-45～49 皆在 TCS 定義且被引用、無重號；②每個新 REQ 有 E2E（64→29、65→07(c)／30、66→30）；③新 E2E 皆不需人按鍵（陳舊讀數以案例改寫快取時戳製造、ping 回合以 T 真實重掛回合複本附加）、不燒真額度（讀數皆 T5 替身）、不真開窗（不走 spawn）；④PRD 只動本草案自有的 v2.1.24 段（§4.2.3、R-4.5.11-5、修訂表列、§16.6 列），對 HEAD `133c3a38` 的刪除行仍只在 R217 三個 hunk。

## 附錄 G：聯合 QA 第五輪（QW r7 FAIL：P2×2、P3×2；R218-B r5 PASS、P3×1）逐條處置（r8）
| QA5 | 處置（WHY 見 §0.3 對應代決） | 座標 |
|---|---|---|
| QW5-P2-1 S-25 量測窗口在正式環境恆≈0 | Δ 改「相鄰兩次 ping 叫醒時刻（皆經 S-23 補量）讀數差」；兩筆皆 `stale=no`、同一視窗、Δ ≥ 0 才記；保溫帳因 S-24 三條件歸零時一併清空 `last_ping_*`（區間內有真工作／真人提示／換窗的段不記）；重掛啟動時不量。AT-QW-80 改為正式環境時序（重掛不刷新快取、下一次 ping 叫醒補量）；E2E-QW-30(c) 改為「重掛啟動後才 +1 並重暖」；補 MU-QW-50（以重掛讀數算 Δ ⇒ 必紅） | S-25、§5.2、§12 Q2、§14、§15；REQ-QW-66、AT-QW-80（改）、E2E-QW-30(c)（改）、MU-QW-50 |
| QW5-P2-2 `work_mark` 架空 `periodic` cap | 「真工作」只認含非唯讀且非監督 `tool_use` 的回合：非唯讀＝`midwork.READONLY_TOOLS` 以外；監督＝`TaskOutput`／`BashOutput`，及每段都是 keepwarm／watch 啟動、`sessionctl.py status`、讀其輸出檔的 shell 呼叫；解析不出算真工作。REQ-QW-23 改為「cap 判準與 R216 相同、歸零條件依 REQ-QW-65」；AT-QW-79 加⑥～⑧；補 AT-QW-81（periodic 跑 n* 次「讀輸出＋重掛」必判 `cap`）、E2E-QW-30(e)、MU-QW-51 | S-24②、§5.2、§12 Q2、§14；REQ-QW-23／65（改）、AT-QW-79（改）／81、E2E-QW-30(e)、MU-QW-51 |
| QW5-P3-1 §15 殘餘風險機制寫錯 | 照實改寫為「每次重掛重算、單筆實測偏高時中途退 single、閒置約 160 分而冷、已付 ping 沉沒」；評估「貪婪續付」不採（S-26：剩餘一跳仍 > 50 分時同樣冷、續付全數沉沒、期望值為負）；仍登記殘餘、不加守衛 | §15 E10、S-26、§14 |
| QW5-P3-2 X-19 `SENTINEL_OFF` 無 QW AT | §7.1 寫明 `SENTINEL_OFF` ⇒ 零次排程器呼叫、`sentinel=absent reason=sentinel_off`；補 AT-QW-82；SE §10.2.1 X-19 補字面與 AT-QW-82 座標（X 表唯一改動） | §7.1；REQ-QW-30；AT-QW-82；SE §10.2.1 X-19 |
| B5-P3-1 SE TCS 表頭缺 r5 列、相容版次 | SE TCS 表頭補 r5 列、「相容＝QW r7／r8」；SE DES 表頭「相容」同步、版次註記第五輪只補字面 | SE TCS L3；SE DES L3、L7、§10.2.1 標題 |
| 計數 | REQ 61（不變；23／65／66 就地改）、AT 80→82、E2E 30（不變；30(c) 改、加 (e)）、MU 49→51；覆蓋 61／61；跨包欄名仍 11 | TCS 表頭、§5、§6、§7；PRD 修訂表 v2.1.24 列、§16.6 本列 |

**本輪自查**：①新號 AT-QW-81／82、MU-QW-50／51 皆在 TCS 定義且被引用、無重號；②無新 REQ，改寫的 REQ-QW-23／65／66 各有 E2E（23→06、30(e)；65→07(c)、30；66→30）；③E2E-QW-30(c)(e) 不需人按鍵（重掛回合以 T 真實回合複本附加）、不燒真額度（T5 替身）、不真開窗（不走 spawn）；④PRD 只就地改本草案自有的 v2.1.24 修訂表列與 §16.6 列，對 HEAD `133c3a38` 的刪除行仍只在 R217 三個 hunk。

---

## 附錄 H：r9 增補——2026-11-23 撞五小時上限 RCA（W11a～e）逐項規格（r9；只追加，r8 以前每行不動）

> 立案：掌舵者 2026-11-23 12:2x 貼撞牆畫面「以上的情況, 是否需要進行改善, 請進行分析改進!」（PRD §16.5 (i)，修訂表 v2.1.27 列、§16.6 2026-11-23 列）。輸入＝Opus RCA 報告 `w11_rca_report.md`（scratchpad；§0～§7）；主控親驗兩項關鍵證據：`tools/lib/quota_policy.py:647-652` `_binding_key` 平手取剩餘分鐘較長者；`~/.autosdd/traces/autosdd_session_switch.jsonl` 唯一一筆 `keepwarm_ping_cost delta=6.0 at 07:42:42`（同一毫秒 `watch_verdict agents=1`，即 S6 子代理在跑）。
> 角色：SD。本節是 r8 凍結規格之後的**增補**：既有 S-／REQ-／AT- 編號、常數、判準全部不動，新判準只用新編號（REQ-QW-70～81、AT-QW-83～96、E2E-QW-31～36、MU-QW-52～65；TCS §8）。r8 S-3／S-25／REQ-QW-10／17／18 的相關句子由本節**加限定**（先於該句的新規則），不是改寫（H.3 逐項標示）。

### H.1 暴露證據（根 CLAUDE.md〈守衛面准入〉：以下皆為本機真實事件，非構造）
逐字稿 T＝`C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\8feb3081-ccbc-469d-be8a-ec9e00ae3fad.jsonl`（行號＝seq）。

| 證據 | 座標 | 證明什麼 |
|---|---|---|
| 07:43:05 watch `QUOTAWALL_PLAN=stage=close D=177 k=3 V=46 R=36 invariant=broken`，讀數僅 64% | T seq 494 | 誤報 close；成因＝`ping_costs=[6.0]`（W11c②③）；閂鎖被它鎖死（W11d） |
| 08:43／09:28／09:52 三次保溫叫醒皆印 `invariant=broken V=40/34/28` 卻無額度事件 | T seq 711、739、768 | 單一序列閂鎖吃掉後續訊號（W11d） |
| 10:00:02 讀數 five_hour 80%、seven_day 58%、reset 10:40 | `~/.autosdd/traces/quota_burn.jsonl` 10:00:02 列 | 重放輸入（E2E-QW-32） |
| 10:02:43 背景 `realverify run --case RV-SE11`；10:02:47 `--pace` 印 band=notice、最緊＝seven_day；10:02:51～58 主控寫「短窗已降到注意帶」並派 Q3 | T seq 857、869、879、880 | 標題藏帶（W11b）；擋派判準未接 hook（W11a）；在飛燒量未入 L（W11c①） |
| 10:21:15 watch `stage=wall R=0`；10:21:19 halt 標記；10:23 RV-SE11 的 RV-S1 rc=-9、W5 逾時 300 秒、KW1～4 失敗全判 FAIL | T seq 915；`traces/watch/8feb3081….quota.json`；`traces/halt_8feb3081….json`；scratchpad `se11_run.txt` | 撞牆型失敗被判 FAIL（W11e） |
| 12:16:07 `WATCH_VERDICT=quota n=3 stage=nodispatch R=53 V=52 L=57`，原始讀數約 47%；文案卻寫「原始讀數已達 prepare」 | 主控提供之 watch 末行；`traces/keepwarm/8feb3081….json` `ping_costs=[6.0]` | 過度保守擋派區（讀數 47% 即生效）；文案假話（W11c③、W11d③） |
| **12:20 主控派工被 rc 2 硬擋**：被停的 Q4／W6 **未驗證半成品**（`qw_guard.py`／`qw_prompt.py` 等）已被運作中的 `sessionctl_guard` 載入，以污染的 `ping_pp=6.0` 在短窗約 54% 時擋派（rc 2） | 主控 12:20 派工當回合（保全：tag `8feb3081-q4w6-halfwork-20261123`；副本 scratchpad `q4w6_halfwork\`） | **W11c②③ 必須先於或同於 W11a 上線**——否則 W11a 一接上就是這個事故的常態版；且**半成品被停時必須移出運作路徑**（H.2 規則 3） |

### H.2 上線順序約束與運作路徑規則（規範性）
1. **順序**：{W11c-②③ ＋ W11a（併入 Q4）**同時或更早**上線，同一 commit 或 ②③ 先} → {W11b ∥ W11d ∥ W11e} → W11c-① → Q7 校準 → W6 之後補 `--pace` 的 QW 行（W11b 後半）。
2. **機械鎖**（REQ-QW-71）：只要 `sessionctl_guard` 的 PreToolUse 呼叫 `quotawall.pretool_verdict`，`ping_pp_eff` 的乾淨樣本門檻（H.3 W11c③）就必須存在；測試以行為斷言（AT-QW-84），不以字串掃描。WHY：擋派是 rc 2 硬擋，輸入污染的代價是工作被擋，不是出聲。
3. **半成品不得留在運作路徑**：`tools/lib/sessionctl/**` 與 `.claude/hooks/**` 是**即載即生效**的（hook 每次工具呼叫重新 import 工作樹檔，不看「是否已 commit」）。任何被停、未經驗證的包，主控必須在停工當下以 `git stash create`＋tag 保全後**把半成品檔移出工作樹**（本事件的 tag 與副本即此做法）；只「不 commit」不算隔離。此規則寫進任務書範本（`w2_dev_common.md` 的收尾條款由主控在下次改版加註；本稿不改它）。

### H.3 逐項規格
#### W11a　擋派接線（併入 Q4；持有面＝Q4）
- **判準**：`sessionctl_guard.py` PreToolUse 對主控（payload 無 `agent_id`）的 Agent／Task／Workflow 呼叫 `quotawall.pretool_verdict`（已存在，§6.1）；`nodispatch`／`close` ⇒ rc 2，訊息含階段、D、R、V、L、`calibrated`、ping_pp 來源（`measured`／`scaled`／`calibrated`）與確切步驟；`續派理由：<≥8 字>` 放行並記 `quotawall_override`；與收斂閘同時成立只出收斂閘訊息＋一行摘要（REQ-QW-10 原文）。fail-open 不變。
- **常數**：無新增。**檔**：`.claude/hooks/sessionctl_guard.py`、`tools/lib/sessionctl/converge.py`（Q4 既有清單）；**序**：與 Q4 同包同 commit，且其上線前提＝W11c-②③（H.2-1／2）。**與進行中 WP 的持有面**：Q4（converge／forward／midwork／`tools/sessionctl.py`／兩支 hook／新 `qw_guard`／`qw_prompt`）本就持有；W6（parkprobe／parkearly／park／park_cli／briefline／planner）不碰。**重做**：被停的 Q4／W6 半成品不得直接 `git restore` 回來用，須從 tag 取出後逐檔重驗（形狀可參考 `qw_guard.py` 的 mute／inflight／idle／primary_gate／stop_notice 五函式，規格以本 DES §6 為準）。

#### W11c　可行性算式與樣本污染（消除成因；持有面＝`qw_calc`／`qw_plan`／`kw_wake`／`kw_ledger`／`qw_schema`，不在 Q4／W6）
- **① L 加在飛燒量**（對 r8 S-2「`L＝V＋AGENT_EST`」加限定）：`L ＝ V ＋ AGENT_EST ＋ burn_live × min(D, T_OBS)`；`burn_live ＝ BURN × N`，`N ＝` 在飛背景子代理數（`roster`）＋背景真 `claude` 行程數（`roster`／`procstop` 身分判準）；**`BURN` 在本式的語意＝每一個在飛單位的 pp／分（QA W13 P2-1 主控裁決：與 V 內 `detect×burn` 的「主控燒速」同一校準鍵、同一數值，但 N 不含主控本身——主控已由 V 承擔，不重複計；待派的那一支由 `AGENT_EST` 承擔，不計入 N）**。`BURN`、`AGENT_EST` 沿用 Q5 校準鍵 `AUTOSDD_QUOTAWALL_BURN_PP_PER_MIN`、`AUTOSDD_QUOTAWALL_AGENT_EST_PP`（**不新增鍵**）。`T_OBS＝30` 分鐘，新常數住 `qw_calc.py`，只准下修（WHY：不假設在飛者燒滿整個 D；30 分鐘≈一次 watch 偵測加一次收尾所需的觀察窗，過大會使晨間大 D 恆判 nodispatch）；`N＝0` ⇒ 與 r8 公式逐位相同（回歸）。`V` 不變、`close` 判準（R ≤ V）不變。與 Q7 校準有序依賴：**先改算式（DES 凍結、實作），再校準**。
- **② 在飛區間的 ping 讀數差不入帳**（對 S-25 加限定）：`kw_wake.ping_cost` 在「相鄰兩次 ping 叫醒之間任一時刻有在飛子代理或背景 `claude` 行程」時不寫 `ping_costs`（與 S-25 既有的「有真工作／真人提示／換窗不記」並列，同一個 `clean` 判準）；判準取自逐字稿（兩叫醒時刻之間的 Agent／Task／Workflow `tool_use` 與其完成通知）＋兩端點 `roster` 快照，讀不到 ⇒ 視為不乾淨。
- **③ 樣本採用門檻**（對 S-3／`qw_calc.ping_pp_eff` 加限定，修 n=1 覆蓋校準值）：`ping_pp_eff` 僅在**乾淨樣本 ≥ `MIN_CLEAN_SAMPLES`（3）** 且量測平均 **≤ 縮放／校準值 × `OUTLIER_X`（3）** 時該量測值才「合格」，`ping_pp_eff ＝ max(縮放／校準值, 合格量測均值)`，無合格量測 ⇒ 縮放／校準值（**QA W13 P2-2 主控裁決：保留 r8 S-25「只抬不降」，本項只收緊「何者算合格量測」，不取代 max 規則**——低於縮放值的量測不會降低估值，WHY：保溫預留偏高的代價是少派一支，偏低的代價是撞牆冷重寫）；超過上限者整批丟棄並落痕跡 `ping_cost_outlier`（含樣本、縮放值、倍數）。兩常數住 `qw_calc.py`，只准下修 `OUTLIER_X`、只准上修 `MIN_CLEAN_SAMPLES`。**schema 升版**：`kw_ledger.SCHEMA` `autosdd.keepwarm/1` → `/2`，`ping_costs` 每筆為 `{"pp":<數>,"clean":<bool>}`；讀到 `/1` 檔一律視為不乾淨（讀回 `[]`），既有污染樣本 `[6.0]` 即此汰除。`qw_schema.ping_costs(row)` 只回乾淨樣本的 pp（**跨包欄名仍十一個，不新增**）。
- **檔**：`qw_calc.py`、`qw_plan.py`、`kw_wake.py`、`kw_ledger.py`、`qw_schema.py`、`roster.py`（只讀取介面）及對應 `tools/tests/test_sessionctl_{quotawall,keepwarm}.py`。**序**：②③先（H.2-1）；①待 DES 凍結後實作。**同批 hot-wire 風險**：`kw_ledger.py` 同被 Q2 持有，W11c 在 Q2 commit 之後做。

#### W11d　watch／keepwarm 閂鎖拆兩條序列（結構正解；持有面＝`watch_wake`／`keepwarm.quota_latch`／`watch.py` 文案）
- **判準**（對 REQ-QW-17「閂鎖四級」加限定）：閂鎖鍵改 `(序列, 級別, reset 分鐘)`，兩條序列各自閂鎖——**原始讀數序列** prepare＜halt、**計畫序列** nodispatch＜close；任一序列升級即重新觸發；同序列同級或較低級不出聲（原規則在序列內不變）。
- **新派工重新評估**：閂鎖之後在飛代理數（含背景 claude 行程）增加，且當下 stage ≥ nodispatch ⇒ 重新觸發一次（閂鎖記 `n_latched`，只在 N 增加時再觸發；N 不增不連發）。
- **事件文案依來源分開**（修 `watch.py` 寫死句）：原始讀數觸發 ⇒「短窗原始讀數 N% 已達 prepare」；計畫階段觸發 ⇒「額度牆判 nodispatch／close（R=…、L=…；ping_pp 來源=…）」；兩者同時 ⇒ 兩句並陳。**原始讀數未達 prepare 時，禁止出現「原始讀數已達」字樣**。`quota_disposal` 本已依階段分，不變。
- **常數**：無新增。**閂鎖檔升 schema**（舊檔讀回視為無閂鎖，fail-open）。**序**：W11b ∥ W11d ∥ W11e 三者檔不相交可並行；W11d 不與 Q4（`converge`／hook）同檔，但 `watch.py` 同被 Q2 持有，Q2 commit 後做。

#### W11b　`--pace` 標題補「短窗最高帶」（結構正解，呈現；持有面＝`tools/lib/quota_messages.py`）
- **判準**：`quota_messages.pace_line` 在「gate 軸中最高帶 ≠ binding 帶」時，標題行補一欄 `｜短窗=<band> five_hour <pct>% 剩 <N> 分`（五小時窗；週軸不補）；兩者相同則不補。**不改 `_binding_key`**（`tools/lib/quota_policy.py:647-652`；R59 的 arm／escalate 語意靠平手規則，WHY 見 H.5）。無新常數。
- **後半（排 W6 之後）**：`--pace` 另印一行 QuotaWall（`QUOTAWALL_PLAN=…`），由 `tools/session_resume_planner.py` 呼叫 `sessionctl.quotawall.plan_lines`；**`quota_gate` 不得 import `sessionctl`**（避免依賴成環，AT-QW-93 以 AST 鎖）；量不到 ⇒ 不印、不報錯（fail-open）。planner 是 W6 持有面 ⇒ 後半必須在 W6 commit 之後單人做。
- **檔**：前半 `quota_messages.py`＋`tools/tests/` 對應檔（Q4／W6 皆不碰，可與 W11d／e 並行）；後半 `tools/session_resume_planner.py`（守衛面，暴露證據＝H.1 seq 869）。

#### W11e　realverify 額度閘（消除成因；持有面＝`tools/lib/realverify/runner.py`、`driver.py`、`cases/*.py` 旗標；排 Q6 之後）
- **① 開跑前額度閘**：`Case` 加旗標 `spends_quota`（會呼叫 `run_claude` 或互動開窗者）；本批含此類案例，且 `qw_plan.stage ∈ {nodispatch, close, wall}` 或短窗原始讀數 ≥ prepare 門檻 ⇒ **整批判 env**，訊息 `QUOTA-PREFLIGHT`（含階段、R、reset），**一個 claude 行程都不起**。量不到 ⇒ 放行（fail-open，與 plan 一致）。
- **② 撞牆型失敗判 env**：`driver.run_claude` 在 rc≠0 或逾時，且（輸出含 harness 撞額度字樣，**或**本機 halt 標記時間晚於該案例開跑時刻）⇒ 拋 `EnvMissing("quota-wall")`，判 env、不判 fail。`AssertionError` 仍判 fail（真缺陷不得被吞）；無字樣且 halt 標記早於開跑 ⇒ 維持 fail。
- **字樣來源（不得猜）**：harness 撞額度原文字樣常數住 `driver.py`，內容必須由實作棒**實查後寫入**：①既有判準 `quota_limits.unhandled_limit_event`／`quotawall.wall_state`（`<synthetic>` 限額記錄、最後切斷通知）已辨識的字串為單一真相源，**重用而不複製**；②再從 2026-11-23 10:21 撞牆的主控逐字稿與 scratchpad `se11_run.txt`（RV-S1 rc=-9、W5 逾時、KW1～4 種子回合失敗）實取 stdout／stderr 原文落進證據檔；實查不到的字樣一律不寫、只靠 halt 標記時間判（寧可判 fail 也不憑空造字樣）。
- **常數**：字樣表（實查後）；無新數值。**序**：Q6（只碰 `cases/`）commit 後串行做；案例旗標改 `cases/*.py` 與 Q6 同一持有面，必須在其後。

### H.4 §12 工作包表加列（見 §12 表尾新增四列；W11a 併入 Q4，不另開包）
W11b／W11c／W11d／W11e 與進行中 WP 的持有面關係見上；Q4 持有 `converge`／`forward`／`midwork`／`tools/sessionctl.py`／兩支 hook／`qw_guard`／`qw_prompt`，W6 持有 `parkprobe`／`parkearly`／`park`／`park_cli`／`briefline`／`planner`——W11c／d／e 與兩者檔不相交，W11b 後半碰 planner 故排 W6 後。共通：並行包不重釘棘輪、不寫帳本、不改 CI paths；棘輪與 `Root_Layout` 落點仍只在 Q7（W11 的新常數與模組無新增檔：落點表不變）。

### H.5 否決方案（RCA §7 逐項；§17.3 同列，WHY 住此）
| 方案 | 否決 WHY |
|---|---|
| 調低 prepare 或 halt 門檻 | 違反「週額度用到 100%」與 D-B「額度照樣用到接近滿」；只是把撞牆提前，成因（看不到燒速、樣本污染）仍在 |
| 改 `_binding_key` 平手規則 | 連動 `reset_branch` 的 arm／escalate（R59 同型事故）；本病只在呈現層，補一欄即足 |
| 讓配速床、攤提也吃燒速 | 同一件事變成第二個家；燒速可行性只放在 QW 的 L 一處（W11c①） |
| 只靠提示詞約束子代理時序 | 本事件 Q3 已證無效（10:30 前只讀的約束被無視）；有先後依賴就用派工順序保證 |
| 把撞牆 FAIL 改成 skip | Rule 12：ENV 必須出聲，不得變綠；故判 env（出聲、不算 PASS）而非 skip |

### H.6 理論洞與 OI（根 CLAUDE.md〈守衛面准入〉）
- TH-2（理論洞，只登記）：`MIN_CLEAN_SAMPLES＝3` 在低頻保溫（一天 < 3 次乾淨 ping）下量測值長期不被採用、恆用縮放／校準值。為何不修：縮放值已是保守側且 Q7 校準列上線閘；再開症狀＝連續 3 天乾淨樣本 < 3 且校準值偏離實測 > 3 倍（附 `ping_cost_outlier` 痕跡）。
- OI-g：W11e②「harness 撞額度原文字樣」的實查結果入證據檔前不得宣稱 E2E-QW-35(b) 已驗字樣分支；承接＝W11e 實作棒附證據檔座標。
- OI-h：W11a 真機 hook 畫面是否顯示 rc 2 訊息（沿用〔OI-20261120-010〕待掌舵者目視）。
