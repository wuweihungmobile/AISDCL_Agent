# TCS-QuotaWall-20261120：額度牆前的快取續航與到點喚醒（session 內等待為主載具、外部排程為備援）——需求＋驗收合一

> 角色：SD（R218＋R218-C 合併，AISDLC 第 2 階段）。版次 r8（**r8＝聯合 QA 第五輪逐條修：ping 實測 Δ 改相鄰兩次 ping 叫醒讀數差、保溫帳「真工作」只認非唯讀且非監督 `tool_use`、park 武裝哨兵遵守 `SENTINEL_OFF` 補 AT**，新號 AT-QW-81／82、MU-QW-50／51，就地改 REQ-QW-23／65／66、AT-QW-79／80、E2E-QW-30(c) 並加 (e)，見 DES 附錄 G；**r7＝聯合 QA 第四輪逐條修：讀數年齡與陳舊補量、有目標時保溫預算只算未來 k、ping 實測取大**，新號 REQ-QW-64～66、AT-QW-76～80、E2E-QW-29／30、MU-QW-45～49，見 DES 附錄 F；r1 兩桶 → r2 跨重置保溫 → r3 續航情境矩陣 → r4 QA 第二輪逐條修＋R218-B r2 同步 → r5 QA 第三輪逐條修＋R218-B r3 替身介面對齊 → **r6 與 R218-B r4 聯合改版：交叉介面以 SE DES §10.2.1 為準、spawn 站點 L1 拒絕終局、E9 實數改正**；r1／r2 的編號全部作廢，r3 編號沿用、r4／r5 只追加新號並就地改期望值，見 DES 附錄 C、D、E）。設計全文＝`docs/02_architecture/QuotaWall_CacheContinuity_Design.md`（下稱 **DES**）；上游＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 **PRD**；修訂表 v2.1.24 列、§4.2.3／§4.5.7／§4.5.11／§11.3／§11.4 的 v2.1.24 段、§16.6 2026-11-20 列）。
> 前綴：`REQ-QW-`、`AT-QW-`（單元／整合，縫注入）、`E2E-QW-`（真機）、`MU-QW-`（突變，必須讓指定測試轉紅）。計數：**REQ 61、AT 82、E2E 30、MU 51**。
> 🔴 掌舵者 2026-11-18：每個功能都要有真機 E2E（真行程／真排程／真 `claude -p` 子行程／真 hook／真逐字稿重放才算）；結果入 `docs/06_quality/RealVerify_Result_Ledger.md`，未入帳＝未結。🔴 本輪：**任何 E2E 不得需要人按鍵、不得真開窗**（主控裁示；spawn 正控一律 SE 假 `claude`）；不燒真額度到撞牆。
> 數值慣例（r4）：未校準 `ping_pp(c)＝0.5·max(1, p(c)/p(230,000))`、`p(c)＝0.2c＋4500`（DES S-3）；凡期望值依賴 V／L 者，案例必寫明 c。
> 測試慣例沿用 sessionctl：時間注入 `now`、路徑圍籬 tmp（含 `trace_dir`）、不讀本機真實 `~/.claude`（E2E 除外）、不開測試用環境變數鉤、禁用 skip。

## 0. 模組落點表
照 DES §13（本檔不重抄）。

## 1. 需求（REQ）

### 1.1 判準核心（Q1，DES §3～§4）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-01 | `quotawall.plan()` 回 `stage`，依序：`none`（量不到／reset 不明／模式非 auto 且非 notify／無人窗口）→ `wall` → `close`（R ≤ V(k)）→ `nodispatch`（R ≤ L）→ `free` | §3 | Q1 |
| REQ-QW-02 | `k(D)＝max(0, ceil((D+s−L_idle)/T_kw))`，`L_idle＝50`；`s`、`T_kw` 取既有真相源；上下文 < MIN_CTX ⇒ 0 | §3、S-1 | Q1 |
| REQ-QW-03 | `V(k)＝(k+W_CLOSE)·ping_pp＋DETECT_MIN·burn`（`W_CLOSE＝4`、`DETECT_MIN`＝ceil((TTL＋watch poll)/60)）、`L＝V＋AGENT_EST`；未校準 ping_pp 依 REQ-QW-54、burn 1.0、AGENT_EST 5，逐鍵標 `calibrated` | §3、S-2、S-3 | Q1 |
| REQ-QW-04 | ENV_SPEC 三鍵與 `.env.example` 同步；非 >0 有限數 ⇒ 視為未校準並出聲；**V** ≥ 100−準備門檻 ⇒ `invariant=broken`＋stderr 一行、判準照算 | §3、§4 | Q1 |
| REQ-QW-05 | `wall_state()` 三條件任一（①最後切斷後無續接、無新 usage；②`<synthetic>` 限額記錄；③短窗 ≥100 且 reset 在未來），回 `source∈{cut,synthetic,quota}`、`cold_at` | §3 | Q1 |
| REQ-QW-06 | fail-open：任何例外／schema 不符／舊窗讀數（補量也失敗，r7）⇒ `none`、不擋、不推，痕跡 `quotawall_unmeasured`；過期快取改依 REQ-QW-64（補量或外推，r7） | §4、S-23 | Q1 |
| REQ-QW-07 | 只看短窗軸；不讀 `decide` band、配速床、趕工戳記 | §4 | Q1 |
| REQ-QW-08 | 模式矩陣（DES §11 表）：auto／notify／off／`AUTOSDD_UNATTENDED`／`AUTOSDD_QUOTAWALL_OFF`／讀不到 | §11 | Q1、Q4 |
| REQ-QW-09 | 週軸「用到 100%」不變：週軸單獨到任何讀數都不改階段、不擋、不推 | §11 | Q1 |
| REQ-QW-64 | （r7，S-23）讀數年齡：`Plan` 帶 `reading_at`／`stale`；`age > TTL＋watch POLL`（現查 210 秒）⇒ 同步補量一次（零 token 端點）；補量成功用新值、`stale=no`；失敗 ⇒ `R_eff＝max(0, R − ceil(age/60)·burn)`、以 `R_eff` 判階段、`QUOTAWALL_PLAN` 印 `stale=yes reading_age=<秒>`；讀數所屬視窗 reset ≤ now ⇒ `none reason=stale_window`；keepwarm／watch 每個叫醒時刻先做同一套；`reading_at` 早於閂鎖 `latched.at` 或參照 `ref_at` 的讀數不參與 `same_window`（不算換窗）與 `early_reset`（回假）、不更新 `ref_pct` | §3、§4、§5.5、S-23 | Q1、Q2 |

### 1.2 觸發點（Q4，DES §6）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-10 | PreToolUse（主控 Agent／Task／Workflow）：`nodispatch`／`close` ⇒ rc 2；子代理放行；`續派理由：<≥8 字>` 放行並記 `quotawall_override`（無人窗口無效）；收斂閘同時成立只出收斂閘訊息＋一行摘要 | §6.1 | Q4 |
| REQ-QW-11 | 擋派與 watch 訊息含階段、D、R、V、L、`calibrated`、該階段確切步驟 | §6.1、§6.5 | Q4 |
| REQ-QW-12 | Stop 在飛側：次序 `_finalized_wake`→quotawall→監督；`close` ⇒ 推「TaskStop 全部在飛代理 → 結束回合」，訊息不得要求在 TaskStop 前封存 | §6.2、D-D | Q4 |
| REQ-QW-13 | Stop 閒置側：`close` ∧（無有效 park 憑證 ∨ 無主載具在跑）⇒ 一則合併訊息列出尚缺步驟（build→主控層→finalize→park→keepwarm）；都有 ⇒ 不推。既有 `park.stop_verdict`：free／nodispatch 不推、none 照舊（S-16） | §6.2 | Q4 |
| REQ-QW-14 | 主載具閘：armed park 標記 ∧ 無 running 的 keepwarm／watch shell ∧ 非不掛前四項（`off` 以 hook 行程原始環境判，OIR 注入不算）⇒ 推一次掛 keepwarm＋貼雙憑證；與封存閘、park 閘合併一則 | §6.3、§10 | Q4 |
| REQ-QW-15 | 牆中靜音：`stop_mute=="wall"` ⇒ sessionctl Stop 與 `check_pending_handoff` 三種推回全不出，痕跡 `quotawall_stop_muted` | §6.4 | Q4 |
| REQ-QW-16 | `stop_mute=="quota"`：完成閘改 `systemMessage`、不 `mark_pushed`；OIR 讓路不設 `AUTOSDD_KEEPWARM_OFF` | §6.4 | Q4 |
| REQ-QW-17 | watch `quota` 事件前印 `plan_lines`（含 `QUOTAWALL_PLAN=`）；閂鎖四級 prepare＜nodispatch＜close＜halt；處置表依階段（nodispatch＝不派新代理、在飛照跑、重掛 watch）、不含「快完成」 | §6.5 | Q2 |
| REQ-QW-18 | watch 牆中不判事件、不記保溫帳、只寫心跳；牆解除後恢復 | §6.5 | Q2 |

### 1.3 主載具：keepwarm（Q2，DES §5）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-20 | `skip_reason` 不再有 `park`；次序 `unattended→mode→off→handed_over→no_usage→small_ctx` | §5.1 | Q2 |
| REQ-QW-21 | 有 `wake_target` 時，`no_usage`／`small_ctx`／非 affordable（r7：未來 k > n* 或 R < k·ping_pp_eff；保溫帳歷史不計）一律退 `single`（一跳到目標、零付費），不得不掛 | §5.1、§5.2、D-C | Q2 |
| REQ-QW-22 | `wake_target` 優先序：park 標記 armed 且交接包 live ⇒ `primary_wake_at`；否則 `close`／`wall` 且 reset 已知 ⇒ reset＋s；否則無。另回參照 `ref`：來源 reset ⇒ (reset, 讀數)；來源 park 且 `primary_source=reset` ⇒ (`primary_wake_at`−s, 讀數)；`primary_source=at`／無目標 ⇒ 空（r5） | §3 | Q1、Q2 |
| REQ-QW-23 | `chain`：affordable（r7：R ≥ k·ping_pp_eff ∧ k ≤ n*，只算未來 k）⇒ 每段 ≤ max(T_kw, idle) ≤ 50、reset 前付費次數＝k、最後一跳恰在目標；無目標 ⇒ `periodic` 排程與 `cap` 判準（`pings ≥ n*`）與 R216 相同；保溫帳歸零條件依 REQ-QW-65（r8：與 R216 的差異只在歸零多了 REQ-QW-65 的②③，故不再寫「逐位元相同」；讀 keepwarm／watch 輸出與重掛的回合不歸零，`periodic` 連續 n* 次此類回合必判 `cap`） | §5.2、S-24② | Q1、Q2 |
| REQ-QW-24 | 牆內不結束：結束時刻落在 [牆, reset＋s) ⇒ 延到 reset＋s；牆內不 `record_ping` | §5.4 | Q2 |
| REQ-QW-25 | 牆鐘輪詢：每輪 sleep ≤ 60 秒、以牆鐘 epoch 比對；凍結／睡眠跨過截止後一輪內結束 | §5.3 | Q2 |
| REQ-QW-26 | 到目標先讀短窗：≥100 且伺服器回報新的未來 reset ⇒ 延到新 reset＋s（`KEEPWARM_DEFER`、痕跡 `keepwarm_defer`）；讀不到 ⇒ 照原目標叫醒；不得自行推算 reset。提前重置（S-19，r5）：參照非空（`early=on`）時任一 ping／defer 輪讀到 reset 晚於參照 **且讀數低於參照讀數與 100** ⇒ 立即 `resume`（該時刻不 ping，痕跡 `keepwarm_early_reset`）；reset 變晚而讀數未降 ⇒ 照原計畫；defer 時參照更新為（新 reset, 100）；同窗讀數上升時參照讀數取最大值；`park --at`（`primary_source=at`）不適用 | §5.5、S-19 | Q1、Q2 |
| REQ-QW-27 | 到目標判 `KEEPWARM_VERDICT=resume`（rc 0、不計 pings、處置列存在） | §5.5 | Q2 |
| REQ-QW-28 | 首行 `KEEPWARM_PLAN mode=… wake_at=… k=… target_source=… early=…`（flush）；holder 列寫 `wake_at`、`mode`、`target_source` | §5.2、§5.6 | Q2 |
| REQ-QW-29 | watch 持有保溫錨時用同一 `schedule`、牆內延後、`resume`、交棒重判 | §5.7 | Q2 |
| REQ-QW-65 | （r7，S-24）有目標時 `chain`／`single` 只看未來 k（保溫帳歷史 pings 不計；`cap` 只用於 `periodic`）；保溫帳歸零＝真人提示（既有）∨ 主控真工作記錄（r8：錨點後主鏈 assistant 記錄所屬回合含至少一個**非唯讀且非監督**的 `tool_use`——非唯讀＝`midwork.READONLY_TOOLS` 以外〔import〕；監督＝`TaskOutput`／`BashOutput`，及切段後每段皆為 keepwarm／watch 啟動〔`roster.KEEPWARM_CMD_RE`／`WATCH_CMD_RE`，import〕、`sessionctl.py status`、讀其輸出檔的 shell 呼叫；解析不出算真工作——或由 auto-continuation 開啟；`keepwarm.work_mark`）∨ 視窗翻新（`resume`、`keepwarm_early_reset`）；任一歸零一併清空 `last_ping_*`（REQ-QW-66） | §3、§5.2、S-24 | Q1、Q2 |
| REQ-QW-66 | （r7，S-25；r8 改量測窗口）ping 實測：Δ＝相鄰兩次 `ping` 叫醒時刻（皆先經 S-23 補量）的讀數差；每個 `ping` 叫醒時刻，上一筆 `last_ping_pct`／`last_ping_at` 存在、兩筆皆非 stale、同一視窗、Δ ≥ 0 ⇒ `Δ` 寫入 `ping_costs`（最近 5 筆）與痕跡 `keepwarm_ping_cost`，隨後 `last_ping_*` 更新為本次；保溫帳歸零時一併清空 `last_ping_*`；重掛啟動時不量 Δ；`plan` 用 `ping_pp_eff＝max(縮放值, 近 3 筆平均)`、印 `ping_pp_src=scaled|measured`；只抬不降；`calibrated` 照舊 `no`、不寫任何設定檔；三個欄名住 `qw_schema` | §3、§4、S-25 | Q1、Q2 |

### 1.4 備援：park（Q3，DES §7）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-30 | 登記：另認 `stage=="close"` 為前置；標記加 `primary_wake_at`、`primary_source`（短窗 reset〔含 `--why`〕＝`reset`、`--at`＝`at`；r5）、`backup_fire_at＝primary＋10 分`、`close_stuck_window`、`desktop_notify`（取自登記行程環境），排程在 `backup_fire_at`；嘗試武裝哨兵；末行 `PARK_VERDICT=armed … primary_wake_at= backup_fire_at= next_run= sentinel=` | §7.1、S-17 | Q3 |
| REQ-QW-31 | `credential_ok` 多一條：標記的交接包仍 live（`.resumed`／`.ack` ⇒ 失效） | §6.2、§8 | Q3 |
| REQ-QW-32 | 到點次序：SE L1 → 前置 → 讓路 → 選路 → 失敗鏈。讓路四分支：A 活且未到 ⇒ 重排到 `wake_at＋10 分`（≤3 次；重排前過 `register_verdict`）；B 活且已過 ⇒ 觀察 180 秒（每 10 秒），出現 driver ⇒ skip `primary_woke`、holder 消失 ⇒ 轉 C、期滿 ⇒ 卡死往下走；C 正常釋放（無記錄＋有晚於登記的 `keepwarm_verdict`）⇒ `handed_over` skip，其餘觀察 180 秒等 driver；D 已死或從未掛 ⇒ 往下走 | §7.0、§7.3 | Q3 |
| REQ-QW-33 | 同 sid 活 `cli` 窗 ⇒ 不關；RESUME 用 `claude -r <sid> --fork-session`；無活窗 ⇒ 普通 `-r`；活 `sdk-cli` ⇒ skip；spawn 前先寫 `session_switch_spawning`；殺窗只在卡死 ∧ 標記 `close_stuck_window` ∧ R217 五條件（job 行程環境不讀） | §7.4、S-17 | Q3 |
| REQ-QW-34 | 失敗鏈：F4 路 → 另一條 → 終局；每次嘗試 `park_attempt` 痕跡與標記 `outcome.attempts` 記實際值；不得有字面 rc；終局 `status=failed`＋`park_chain_failed`。r6：任一次嘗試的 spawn 函式回 `RC_SIDEEFFECT_REFUSED`（SE D-24）⇒ 該次 `park_attempt` 照記（`reason=sideeffect_refused`）後終局 `refused`，不走另一路、無 handback／佇列／`notify`／`park_chain_failed`；FRESH 的 `handoff._refusals` 前置拒絕仍算一次失敗 | §7.5、§7.5-1a | Q3 |
| REQ-QW-35 | 終局出聲：handback（指向痕跡）、通知佇列入列、`notify()` 依標記 `desktop_notify` AND argv 關閉值、SessionStart 公告、UserPromptSubmit 對同專案視窗同一失敗只注入一次（`park_failure_notice`） | §7.5、S-11、S-17 | Q3、Q4 |
| REQ-QW-36 | 哨兵接手：`status=failed`（只認 failed，`refused` 不接手）且晚於上次巡邏 ⇒ 讓路判準＋一次選路與失敗鏈（不殺窗）；結局 `fired`／`failed_final`、痕跡 `sentinel_park_takeover`；哨兵未武裝則不動作。r5：非終態標記＋逾期 `spawning` 意圖（無同 attempt 成功列）⇒ 先查意圖後是否出現 stem ≠ 原 sid 的新逐字稿：有 ⇒ 補 `spawned ok=True recovered=true`、標記 `fired`、`park_spawn_recovered`、不再 spawn；無 ⇒ 標記 `failed`（attempts 追加 `reason:intent_expired`）、`park_intent_expired`、出聲、再接手一次 | §7.6、S-13 | Q3 |
| REQ-QW-37 | `park --status [--verify]` 與 `sessionctl status` 印主載具（`primary: live pid wake_at mode`／`absent`）、備援（`next_run`／`absent`／`absent(platform)`）、哨兵三列 | §10 | Q3、Q4 |
| REQ-QW-38 | 平台維度（S-14）：非 win32 的 park job 到點不呼叫 spawn，以 `attempted:false, reason:platform_unsupported` 進失敗鏈終點出聲；park 末行、keepwarm 首行、status 印 `backup=absent(platform)`；darwin keepwarm 每 ≤10 分印心跳；`continuity.MATRIX` 鍵含平台 | §2、§5.8、§7.4 | Q1、Q2、Q3 |
| REQ-QW-39 | SE L1 拒絕永不進失敗鏈：fire 站點拒絕 ⇒ 標記 `refused`、無 `park_attempt`／`park_yield_primary`／觀察、無 handback／佇列／`notify`；spawn 站點拒絕（r6，`RC_SIDEEFFECT_REFUSED`）⇒ 同樣終局 `refused`、只留該次 `park_attempt` 一筆；QW 四個新站點（fork、§7.3 重排、§7.5 第 3 步、§7.6 接手）進 `sandbox_scope.SITES` | §7.0、§12 Q3 | Q3 |
| REQ-QW-44 | spawn 執行檔單一來源：到點 job 的 `--claude`（未給＝`"claude"`）必須原樣傳到**每一次** spawn 嘗試——RESUME（`spawn_resume`）、fork（`spawn_resume(fork=True)`）、FRESH（`handoff.spawn(pkg, claude=…)`，修現行 `park_cli.py:428` 未帶）、§7.5 失敗鏈的另一路（`opts.claude`）、§7.6 哨兵接手（讀 park 標記 `claude` 欄，`park` 登記時寫入；r5 對齊 SE §10.2-8）；任一路改用別的執行檔即違規 | §7.4～§7.6 | Q3 |
| REQ-QW-48 | fork 成功判準（S-20，r5）：`spawn_resume(fork=True)` 只認 spawn 後新出現、stem ≠ 原 sid 的 jsonl ∧ 行程活；原逐字稿變大不算；成功寫 `session_switch_spawned`（`ok=True`、`new_sid`、`route=fork`）、不呼叫 `mark_resumed`；失敗進另一路 | §7.4、S-20 | Q3 |
| REQ-QW-49 | `handoff.spawn`（S-21，r5）：驗證成功後才解除哨兵（失敗不解除）；`_duplicate_refusals` 只把 `ok=True`（600 秒內或行程活）或「行程仍活且未重用」者算已開過，`ok=False` 且行程已死不擋 | §7.4、§7.6、S-21 | Q3 |

### 1.5 原主人自續跑（Q2、Q4，DES §8）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-40 | `mark_resumed` 觸發點增：keepwarm／watch 判 `resume` 且本 sid 包 live＋已封存；UserPromptSubmit 判留原窗（`f4_resume_cheaper`／快取熱／`留：`）且本 sid 為原主人、未交棒。fork 新窗不記續跑 | §8 | Q2、Q4 |
| REQ-QW-41 | 冷叫醒閘一致：`.resumed` 後不推；已封存＋只有 keepwarm 在跑不推；收尾流程不會產生「已封存＋在飛代理」 | §8、D-D | Q4 |
| REQ-QW-42 | 交棒重判（S-13）：keepwarm／watch 每個叫醒時刻先 `seal.handed_over`；已交棒 ⇒ `KEEPWARM_VERDICT=handed_over`（rc 0、不計 pings、不呼叫 `mark_resumed`）；`seal._spawned` 認 `session_switch_spawning`（同 attempt 有失敗列者不算；r5：只在 `at` 起 `SPAWN_INTENT_TTL_SEC`〔90，≥ 兩個 spawn 等待常數＋30〕內有效，逾時且無成功列 ⇒ 不算）；§8 觸發 1／2 加「未交棒」 | §5.5、§7.4、§8、S-13 | Q1、Q2、Q4 |
| REQ-QW-43 | 主載具憑證（S-18）：running keepwarm／watch shell ∧ holder 活、`wake_at` 未來、`mode∈{chain,single}` ⇒ ①半路停工判準不判（帶目標主載具＝事件源；`periodic` 照舊排除）；②「缺 park」推回（§6.2 閒置側、`none` 階段既有 `park.stop_verdict`）同一 (sid, 短窗視窗) 至多一次（r5：視窗身分 `same_window`＝讀數未降 ∧ 未過閂鎖 reset＋60 分；reset 觀測值漂移不算換窗），其後 `systemMessage`「備援缺席」、痕跡 `quotawall_backup_absent`；閂鎖讀寫失敗 ⇒ 視為未推；③競態寬限（r5）：holder 缺席但有 running 的本 sid keepwarm shell ⇒ 同一背景任務 id 只寬限一次 | §6.2、§6.4、S-18 | Q1、Q4 |

### 1.6 映像與測試圍籬（Q3，DES §9）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-45 | `procstop.image_allowed`：`^claude\.exe(\.old\.\d+\.\d+)?$` 或 `node.exe`（不分大小寫）；其他拒；身分仍以 procStart 為主 | §9 | Q3 |
| REQ-QW-46 | `image_not_allowed`／`open_failed` 為可降級：跨 sid 關舊窗記 `oldwin_close_degraded` 後照既有出聲繼續 | §9 | Q3 |
| REQ-QW-47 | oldwin 單元測試 `trace_dir` 一律 tmp 圍籬；測試 sid 一律含模組常數 `OLDWIN_TEST_SID_MARK`；測試期間真 `~/.autosdd/traces/oldwin/events.jsonl` 的新增段不含該標記／tmp 路徑／沙盒字樣（真 session 可能同時追加，不判位元組） | §9 | Q3 |

### 1.7 量測（Q5）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-50 | M-K7 額度牆冷重寫（主控兩筆真 usage 間有牆 ①或② 且後一筆 `cache_creation ≥ 0.5×` 前一筆上下文）；不再計入 M-K1 | §15 | Q5 |
| REQ-QW-51 | M-K8：每 (sid, reset) 的 chain／single 次數、跨重置成功（reset 後首筆 `cache_read ≥ 0.9×` 上下文）、省下（`2c − Σp`）、備援觸發／讓路次數、牆前無觸發件數、靜音 Stop 次數 | §15 | Q5 |
| REQ-QW-52 | `--calibrate-quotawall`：三鍵建議值；區間 <8 印「未校準」；不寫任何設定檔；同輸入兩次輸出逐位元組相同 | S-3、S-4 | Q5 |
| REQ-QW-54 | 未校準 `ping_pp(c)＝0.5·max(1, p(c)/p(230,000))`；c ≤ 23 萬恆 0.5，之上隨 p(c) 線性放大 | S-3 | Q1 |
| REQ-QW-55 | 上線閘：Q7 結案與 PRD §16.6 本列轉 ✅ 前置＝真本機 `--calibrate-quotawall` 三鍵有值且已寫入 `env.shared`；不足 ⇒ OI 留著 | S-15 | Q5、Q7 |
| REQ-QW-53 | M-K9 park 到點結局普查：依 `park_job_start` 配對終態，分 fired／skipped（依原因）／failed（依 attempts 原因）；另計「宣稱已排程但未續上」（armed 後 reset＋30 分內原 sid 與其 fork／FRESH 皆無 assistant 記錄） | §15 | Q5 |

### 1.8 規格與政策（本棒／Q7）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-60 | PRD 只追加：DES 附錄 A 七處；修憲前每行位元組不變 | 附錄 A | 本棒、Q7 |
| REQ-QW-61 | 情境矩陣規範性：`continuity.MATRIX`（住 `quotawall.py`）S1～S6 每格主載具／備援／出聲非空；S1～S6 各至少一個 E2E | §2 | Q1、Q6 |
| REQ-QW-63 | 跨包欄名常數（十一個：r5 加 `primary_source`，r7 加保溫帳 `last_ping_pct`／`last_ping_at`／`ping_costs`）與讀取函式只住葉模組 `qw_schema.py`（只 import 標準庫）；其他模組不得寫出整串等於欄名的字串常數（輸出格式字串不算）；wastecensus import `qw_schema` | S-12、§12 | Q1 |
| REQ-QW-62 | 連動文件：`WorkProgress_Axis_Design.md` §7.1 與 D-14、`SessionSwitch_CostModel_Design.md` X-7 各有指向本稿的追加註記；根 CLAUDE.md park SOP 含主載具與雙憑證 | §12 Q7 | Q7 |

## 2. PRD 追溯
| PRD 座標 | 關係 | REQ |
|---|---|---|
| §4.2.3【v2.1.24 新增】額度牆預留閘 | 新增否決閘 | 01～04、07、09～13、16、54、55、64、66 |
| §4.5.4 F4 | 到點選路不變 | 32～34 |
| §4.5.7【v2.1.24 新增】R-4.5.7-4 | 牆後段 | 05、15、18、24 |
| §4.5.11【v2.1.24 新增】R-4.5.11-1～6 | 情境矩陣、原地喚醒、不殺窗、失敗不得無聲、保溫與到點統一、雙憑證 | 14、20～23、25～39、40～44、45～49、61、63、64、65 |
| §11.3／§11.4【v2.1.24 註記】 | E2E 覆蓋要求、週窗 | 21、61 |
| §1.2 原則 2 v2.1.22 註記 | 量測 | 50～53 |
| §16.5 (i)、§16.6 | 修憲程序 | 60、62 |

## 3. 驗收測試（AT；縫：`NOW`、`FS`（tmp 圍籬含 `trace_dir`）、`ENV`、`TR`（合成或截取逐字稿）、`Q`（假 `pace_state`）、`PL`（hook payload）、`MK`（假 park 標記）、`HD`（假 holder 列）、`SCH`（假排程後端）、`API`（FakeApi 行程面）、`SP`（spawn 執行器）
| AT | REQ | 輸入 | 預期 |
|---|---|---|---|
| AT-QW-01 | 01 | `Q`：c＝20 萬（ping_pp 0.5）、D＝150（k＝3、V＝7.5、L＝12.5）；R＝13／12.5／8／7.5／0（且 wall） | free／nodispatch／nodispatch／close／wall（等號邊界含） |
| AT-QW-02 | 01、06 | 量不到、reset 不明、UNATTENDED、mode=off | 皆 `none` 且 reason 各異 |
| AT-QW-03 | 02 | D＝0、48、49、93、94、224、251、300 | k＝0、0、1、1、2、4、5、6 |
| AT-QW-04 | 02、03 | monkeypatch `HALT_RESET_SKEW_SECONDS`＝300、`t_kw_minutes`＝30、`QUOTA_CACHE_TTL_SECONDS`＝60 | k、V 隨之改變（未複寫常數） |
| AT-QW-05 | 03 | k＝0～6 未校準、c＝20 萬 | V＝6、6.5、7、7.5、8、8.5、9；L＝V＋5 |
| AT-QW-06 | 04 | 三鍵使 V＝15.5；三鍵使 L＝16 而 V＝11 | `invariant=broken`、stderr 一行、stage 照算／無 `invariant=broken`、無 stderr（r4 以 V 判） |
| AT-QW-07 | 03、04、54 | c＝309k，`PP_PER_KUNIT` 空／0.02／-1 | 0.5×66,300/50,500≈0.656 `calibrated=no`／p(c)/1000×0.02≈1.326 `yes`／≈0.656 `no`＋出聲 |
| AT-QW-08 | 03 | c＝20k、D＝150 | k＝0、V＝6 |
| AT-QW-09 | 05 | `TR`：T 截至 L926；截至 L935 | wall、`source=cut`、cold_at＝L889 時戳＋3600／非 wall |
| AT-QW-10 | 05 | 合成 `<synthetic>` 限額記錄；`Q` five_hour 100＋reset 未來、無牆記錄 | `source=synthetic`／`source=quota` |
| AT-QW-11 | 06 | `Q` 拋例外／讀數屬已過 reset 的舊窗且補量也拋（r7；年齡造成的陳舊改由 AT-QW-76） | `none`（後者 `reason=stale_window`）、`quotawall_unmeasured`、`pretool_verdict`＝(0,"") |
| AT-QW-12 | 07、09 | seven_day 99％、five_hour 40％；seven_day_opus 99％ | `free`（不擋不推） |
| AT-QW-13 | 07 | five_hour 40％，配速床墊到 prepare、趕工戳記有效 | `free` |
| AT-QW-14 | 08 | `close` × auto／notify／off／UNATTENDED／QUOTAWALL_OFF | rc 2／0＋stderr／0 無聲／0／0 |
| AT-QW-15 | 10 | c＝20 萬、D＝150：R＝13／12.5／7.5 | 放行／rc 2／rc 2 |
| AT-QW-16 | 10 | `close`：`agent_id` 有值；`續派理由：補最後一個測試檔案`；`續派理由：短`；同前＋UNATTENDED | 放行／放行＋`quotawall_override`／rc 2／放行且無 override 痕跡 |
| AT-QW-17 | 10 | 上下文 ≥ 硬線且 `close` | 只出收斂閘訊息＋一行額度牆摘要 |
| AT-QW-18 | 14 | armed `MK`＋`PL.background_tasks` 無 keepwarm／有 running keepwarm／有 running watch；同前＋封存閘成立 | 推（含 `keepwarm --sid`、`KEEPWARM_PLAN`、背景任務 id 字樣）／不推／不推／合併一則（次序 封存→park→主載具） |
| AT-QW-19 | 15 | `TR` 截至 L1645＋封存閘、park、保溫、半路停工、完成閘同時成立 | sessionctl 回 ""；`check_pending_handoff` 無 block；痕跡 `quotawall_stop_muted` |
| AT-QW-20 | 23 | 窮舉 anchor∈[r−300, r]（每分）、T_kw∈{45,30,15}、idle∈{50,20}、s＝2、affordable | 每例：段 ≤ max(T_kw,idle)、付費次數＝k、末跳＝r＋s；無目標時序列＝R216 `deadline` 逐點相同 |
| AT-QW-21 | 21 | 有目標 × {非 affordable（R < k·ping_pp）、ctx 小、`no_usage`、未來 k > n*（r7；原「pings＝n*」改由 AT-QW-78 期望 chain）} | 皆 `mode=single`、付費 0、末跳＝目標；無目標 × pings＝n* ⇒ `cap`（既有） |
| AT-QW-22 | 12、41 | `close`＋在飛代理 1 支（無封存）；依推回 TaskStop 後再 Stop（已封存、只剩 keepwarm） | 第一則含 TaskStop 且 TaskStop 出現在任何 finalize 字樣之前；第二則 `_finalized_wake`＝"" |
| AT-QW-23 | 20、22 | ①QA P1-2 反例（86％、D＝100、c＝30 萬、閒置、無標記）；②同①＋armed `MK`（交接包 live）；③93％、D＝100、c＝30 萬、無標記 | ①逐步：ping_pp 0.639、k＝2、V＝7.83、L＝12.83、R＝14 ⇒ `free`、無目標 ⇒ `mode=periodic`（保溫照掛）；②`mode=chain`、`target_source=park`（不判 `park` 不掛）；③R＝7 ≤ V ⇒ `close`、affordable（7 ≥ 1.28）⇒ `mode=chain k=2`、`target_source=reset` |
| AT-QW-24 | 24 | wall＋reset＝now＋40；chain 計畫中一跳落在牆內 | 不結束直到 reset＋s；`record_ping` 呼叫 0 次 |
| AT-QW-25 | 26 | 到目標：`Q`＝100＋新 reset（觀測）／`Q` 拋例外／`Q`＝100 但無 reset | defer 到新 reset＋s／照原目標 `resume`／照原目標 `resume`（不推算）；S-19（r5，參照＝計畫當時 reset r、讀數 89）：④`target_source=reset`、第 2 次 ping 時 `Q`＝30％＋reset＝r＋300 ⇒ 立即 `resume`＋`keepwarm_early_reset`、該時刻不 ping、pings 不加；⑤反例：到目標時 `Q`＝100％＋reset＝r＋40 ⇒ defer（不 `resume`）、參照更新為（r＋40, 100），defer 中下一輪 `Q` 仍 100％＋r＋40 ⇒ 繼續等（不 `resume`）；⑥反例：第 2 次 ping 時 `Q`＝91％（≥ 參照 89）＋reset＝r＋70 ⇒ 照常 ping、無 `keepwarm_early_reset`；⑦同④但 `target_source=park` 且 `MK.primary_source=at`（`early=off`）⇒ 照常 ping |
| AT-QW-26 | 25 | `now_fn` 在某次 sleep 期間跳過截止 600 秒 | 下一輪即結束；每次 `sleep_fn` 參數 ≤ 60 |
| AT-QW-27 | 27 | 到目標 | `resume`、pings 不變、處置列存在 |
| AT-QW-28 | 28 | 三種 mode 啟動 | 首行格式正確且 flush；holder 列含三欄 |
| AT-QW-29 | 52 | 合成 burn 12 區間；5 區間 | 印建議值且 `FS` 中 `env.shared`／`.env` 未被寫／印「未校準」 |
| AT-QW-30 | 16 | `close`＋完成閘成立；`close`＋OIR undriven | `systemMessage`、`mark_pushed` 0 次／不設 `AUTOSDD_KEEPWARM_OFF` |
| AT-QW-31 | 11 | `nodispatch`／`close` 訊息 | 含 D、R、V、L、`calibrated=`；`close` 含 TaskStop、`--finalize`、`park`、`keepwarm` |
| AT-QW-32 | 13 | 閒置 `close`：無 park 無 keepwarm／有 park 無 keepwarm／兩者皆有 | 列五步／只列 keepwarm／不推 |
| AT-QW-33 | 17 | watch：首次 prepare；重掛；R 降到 nodispatch；再降到 close | `quota`＋`QUOTAWALL_PLAN=`／不觸發／觸發／觸發；處置文字不含「快完成」 |
| AT-QW-34 | 18 | watch 牆中＋停滯代理 3 輪；牆解除 | 無事件、心跳更新、保溫帳不變／恢復判事件 |
| AT-QW-35 | 29 | watch 持錨與 keepwarm 同輸入 | 叫醒時刻序列相同 |
| AT-QW-36 | 22 | `MK` armed＋包 live；`MK` armed＋包 `.resumed`；無 `MK`、`close`；無 `MK`、`free` | park／reset／reset／none |
| AT-QW-37 | 30 | park 成功（`SCH` 回 NextRunTime）；哨兵武裝被拒 | 末行六欄齊全；`sentinel=absent reason=…` |
| AT-QW-38 | 30 | `close` 但讀數 80（校準後）；`free` 且讀數 80 無 `--why` | 登記成功／rc 4 |
| AT-QW-39 | 31 | `MK` armed＋包 `.resumed`／別 sid `.ack`／live | `credential_ok` 假／假／真 |
| AT-QW-40 | 30 | 短窗 reset＝r：`backup_fire_at`、`SCH` 登記時刻 | `primary_wake_at`＝r＋s、`backup_fire_at`＝r＋s＋10 分、排程在後者 |
| AT-QW-41 | 32 | `HD` 活＋wake_at 未來（第 1、4 次）；活＋已過、觀察期第 60 秒出現 driver；活＋已過、無記錄 180 秒；不存在 | 重排（`park_yield_primary`）／第 4 次往下走／skip `primary_woke`／往下走（卡死）／往下走 |
| AT-QW-42 | 33 | 同 sid 活 `sdk-cli` 行程 | skip、`SP` 0 次 |
| AT-QW-43 | 33 | 卡死＋活 `cli` 窗：標記 `close_stuck_window` 假／真但五條件缺一／真且五條件全成立；另一例 job 行程環境設 `AUTOSDD_PARK_CLOSE_STUCK_WINDOW=1` 而標記假 | 不關（fork）／不關（fork）／關後普通 `-r`／不關（job 環境不讀） |
| AT-QW-44 | 33 | F4＝RESUME：活 `cli` 窗／無活窗 | `SP` argv 含 `--fork-session`／不含 |
| AT-QW-45 | 34 | `SP`：RESUME rc 3、FRESH 前置拒（工作樹髒）；RESUME 成功 | attempts＝[{RESUME,attempted,rc 3},{FRESH,attempted false,reason dirty}]、`status=failed`、`park_chain_failed`；標記與痕跡中無 `spawn_rc` 鍵／`fired` |
| AT-QW-46 | 35 | 失敗終局，標記 `desktop_notify`＝1；同前＋argv 帶通知關閉值 | handback 檔指向 `park_chain_failed`；佇列一列；`notify` 呼叫 1 次／`notify` 0 次（佇列、handback 照寫） |
| AT-QW-47 | 33 | 22:42 重建：活 `cli` 窗、`API.image`＝`claude.exe.old.1795116108051.41752`、F4＝RESUME | 不呼叫 terminate；`SP` 以 fork 呼叫；不判 failed |
| AT-QW-48 | 36 | `MK` failed（晚於上次巡邏）＋哨兵武裝；早於上次巡邏；哨兵未武裝；`MK` refused＋哨兵武裝 | 一次選路、`sentinel_park_takeover`；不動作；不動作；不動作 |
| AT-QW-49 | 45 | `claude.exe`、`CLAUDE.EXE.old.1.2`、`claude.exe.old.x.2`、`claude-x.exe`、`node.exe` | 接受、接受、拒、拒、接受 |
| AT-QW-50 | 46 | 跨 sid 關舊窗遇 `image_not_allowed`／`open_failed`／`toctou_*` | `degradable` 記 `oldwin_close_degraded` 繼續／同左／既有可重試 |
| AT-QW-51 | 40、41 | `PL` UserPromptSubmit 真人提示、本 sid 原主人、包 live＋`.sealed`、`f4_resume_cheaper`；隨後 Stop＋running 一般背景 shell | `.resumed` 寫入、`.sealed` 消失；冷叫醒閘不推 |
| AT-QW-52 | 40 | keepwarm `resume`＋包 live＋`.sealed`；fork 成功後的原包 | `.resumed` 寫入／不寫 `.resumed`、有 spawn 痕跡 |
| AT-QW-53 | 35 | 失敗終局，標記 `desktop_notify` 空；之後兩次 UserPromptSubmit | `notify` 不敲（rc 為既有「未啟用」值）但佇列、handback 照寫；提示只注入第一次 |
| AT-QW-54 | 47 | 跑 oldwin 測試前後 | 每個 oldwin 測試內 `FS` 斷言 `trace_dir` 指向 tmp、寫入全落 tmp；每個測試 sid 含 `OLDWIN_TEST_SID_MARK`（掃描測試模組全部 sid 字面）；真檔不在斷言面（真檔判準在 E2E-QW-18） |
| AT-QW-55 | 37 | holder 活／死；排程有／無；哨兵有／無 | 三列逐一 `live…`／`absent` |
| AT-QW-56 | 50 | `TR`＝T 全檔 | M-K7＝2 件 486,057；M-K1 不含 L935／L1665 |
| AT-QW-57 | 51 | 合成痕跡（chain 2、single 1、yield 1、fire 1、無觸發 1） | 各欄計數與省下正確 |
| AT-QW-58 | 53 | 合成 switch 痕跡（含 22:42 型：armed→job_start→route→無終態列＋PK failed） | failed 1（原因 `image_not_allowed`）；「宣稱已排程但未續上」1 |
| AT-QW-59 | 60 | 合成舊／新 PRD 文字（只增、改一字、刪一行） | PASS／FAIL／FAIL |
| AT-QW-60 | 61、38 | `continuity.MATRIX` | 鍵＝(S1～S6, {win32, darwin})，每格三欄非空；載具名屬 W1～W6 或 `absent(platform)`；`absent(platform)` 格的出聲欄非空且帶 OI 標記 |
| AT-QW-61 | 63 | 掃 `tools/lib/**`、`tools/*.py`、`.claude/hooks/*.py` 原始碼 | 十一個跨包欄名（r7）：AST 中**整串等於欄名**的字串常數只出現在 `qw_schema.py`（輸出格式字串如 `"wake_at="`、f-string 片段不算）；另以一個合成檔（寫 `"primary_wake_at"` 字面）證明判準會紅；`qw_schema.py` 只 import 標準庫；`quotawall`／`park` 互不出現在對方的模組頂層 import 環；`wastecensus/sections_wall.py` 的事件名取自 `qw_schema` |
| AT-QW-62 | 54 | c＝0、20 萬、23 萬、30 萬、43 萬、60 萬 | ping_pp＝0.5、0.5、0.5、≈0.639、≈0.896、≈1.233；對所有 c：ping_pp ≥ 0.5 且 ping_pp/p(c) 在 c ≥ 23 萬時為常數 |
| AT-QW-63 | 42 | keepwarm `HD` 自己持有、`TR` 錨點；到目標前 `seal.handed_over` 改為真（痕跡加 `session_switch_spawned`）；同前改成 `spawning` 意圖；`spawning`＋同 attempt 失敗列；ping 時刻已交棒 | `KEEPWARM_VERDICT=handed_over`、`mark_resumed` 0 次、pings 不變／同左／`resume`＋`mark_resumed` 1 次／`handed_over`（不 ping） |
| AT-QW-64 | 32 | 四分支：A（`HD` 活、wake 未來，`register_verdict` 放行／拒）；B（活、已過、第 60 秒 holder 檔消失且痕跡有 `keepwarm_verdict=resume`、第 120 秒出現 driver）；C（無 holder、痕跡 `handed_over`）；C（無 holder、痕跡 `resume`、180 秒無記錄、無活窗）；D（holder 檔在、pid 死） | 重排／不重排且 `refused`；轉 C 後 skip `primary_woke`；skip `handed_over`；往下走（S3）；往下走（S3） |
| AT-QW-65 | 38 | `platform_name="darwin"`：park 登記、到點未讓路、keepwarm 啟動、status；`SP` 記錄器 | park 末行與 keepwarm 首行含 `backup=absent(platform)`；到點 `SP` 0 次、attempts＝[{attempted false, reason platform_unsupported}]、`status=failed`、出聲四管道照走；keepwarm `now_fn` 跑 25 分 ⇒ 心跳 ≥2 行；`win32` 同輸入無心跳 |
| AT-QW-66 | 42 | `seal.handed_over`（`NOW` 注入）：痕跡只有 `spawning`（`at`＝now−10 秒）；`spawning`＋同 attempt 失敗；`spawning` 後 `spawned ok=True`；別 sid `.ack`；只有 `spawning`、`at`＝now−91 秒（逾 TTL）；同前但同 attempt 有 `spawned ok=True`；`SPAWN_INTENT_TTL_SEC` 值 | 真／假／真／真／**假**／真／≥ `handoff.SPAWN_WAIT_SECONDS`＋30 且 ≥ park_cli 續跑等待＋30 |
| AT-QW-67 | 14 | armed `MK`、無 keepwarm shell、`free`；hook 行程原始環境無 `AUTOSDD_KEEPWARM_OFF`、OIR 讓路注入之；原始環境本身設 1 | 推主載具閘／不推（使用者自己關） |
| AT-QW-68 | 13、17 | 讀數 88 且 stage＝`nodispatch`／`free`（校準後）／`none`（量不到 reset）；watch `nodispatch` 處置列 | 不推 park／不推 park／既有 `park.stop_verdict` 原樣；處置含「不派新代理」「重掛」、不含 finalize |
| AT-QW-69 | 34、39 | ①`_cmd_fire`：沙盒目標無租約（L1 refuse）且 holder 活、wake 未來；②同前租約有效；③（r6）租約有效、holder 死、F4＝RESUME，`SP` 的 RESUME 回 `sandbox_scope.RC_SIDEEFFECT_REFUSED`；另一例同③但在 §7.6 哨兵接手中回此值 | ①標記 `refused`、無 `park_yield_primary`／`park_attempt`／handback／佇列、`notify` 0 次、holder 未被讀（`HD` 讀取計數 0）、哨兵接手 0 次；②照 §7.3 重排；③`park_attempt` 恰 1 筆（`reason=sideeffect_refused`、rc 為該常數值）、`SP` 只被呼叫 1 次（無 FRESH 另一路）、`session_switch_spawning` 同 attempt 有失敗列、標記 `refused`、handback 0、佇列 0、`notify` 0、無 `park_chain_failed`；接手例結局 `refused`（非 `failed_final`）、佇列 0；`sandbox_scope.SITES` 含 QW 四站點 |
| AT-QW-70 | 43 | `PL` Stop：`close`、無 park 標記、`background_tasks` 有 running keepwarm、`HD` 活且 `mode=chain`、`wake_at` 未來，最後一則回覆「reset 後繼續剩下的工作」；讀數 94、reset＝r：第 1 次 Stop；第 2 次 reset＝r＋5 分、讀數 94；第 3 次 reset＝r−5 分、讀數 95；第 4 次 reset＝r＋70 分、讀數 95（皆 `now` < r＋60）；第 5 次 讀數 91（已降）＋reset＝r＋300；第 6 次另起：閂鎖於 (r, 94) 後 `now`＝r＋61 分、讀數 96、reset＝r＋300；`HD` `mode=periodic`；閂鎖檔不可寫；競態：`HD` 缺席＋running keepwarm shell（命令列含 `keepwarm --sid <sid>`，id＝b1）連續 2 次 Stop | `midwork` 不判（皆無半路停工推回）；缺 park：第 1 次 block、第 2～4 次 `systemMessage`「備援缺席」無 block（漂移 ±5、+70 不算換窗）、`quotawall_backup_absent`；第 5 次再 block 一次（讀數已降）；第 6 次 block（已過閂鎖 reset＋60）／`periodic` ⇒ midwork 照舊判／不可寫 ⇒ 每次都 block（不漏推）／競態：第 1 次視同主載具在跑（midwork 不判、id b1 記入閂鎖）、第 2 次不成立（midwork 照舊判） |
| AT-QW-71 | 44 | `SP` 記錄器＋`--claude=/x/fake`：F4＝RESUME 無活窗；RESUME 有活窗（fork）；F4＝FRESH；RESUME 失敗後改 FRESH；哨兵接手（`MK.claude`＝`/x/fake`，哨兵 job argv 不帶 `--claude`）；未給 `--claude` | 每一次 spawn 呼叫的 runner argv[0] 皆為 `/x/fake`（含 FRESH 的 `handoff.spawn`、§7.4 fork、§7.5 另一路、§7.6 接手三處各一斷言）；未給 ⇒ 皆為 `"claude"` |
| AT-QW-72 | 48 | `SP`＋`FS` 專案目錄，`spawn_resume(fork=True)`：①行程活、原逐字稿變大、無新檔；②行程活、出現新檔 stem＝原 sid（同名改寫）；③行程活、出現新檔 stem＝新 uuid；④出現新檔但行程已死 | ①②④ 失敗（rc≠0、同 attempt 失敗列、無 `spawned ok=True`、`handed_over` 為 None、`mark_resumed` 0 次）；③成功（`session_switch_spawned` `ok=True`、`new_sid`＝新 stem、`route=fork`、`mark_resumed` 0 次、`handed_over` 為包路徑）；普通 `-r`（fork=False）＋①情境 ⇒ 成功（既有 `grew()` 不變） |
| AT-QW-73 | 49 | `handoff.spawn` 注入 `runner`／`alive`／`disarm` 記錄器：①新檔出現且行程活；②行程活但限時內無新檔；③行程起來即死；④痕跡有同包 `spawned ok=False`（`at`＝now−60 秒、pid 已死）後再 spawn；⑤同前但 `ok=True`；⑥同前 `ok=False` 但 pid 仍活且未重用；⑦舊格式無 `ok` 欄、`at`＝now−60 秒 | ①`disarm` 呼叫 1 次且在驗證之後；②③`disarm` 0 次（哨兵保持武裝）、rc 1；④不被 dedup 拒（可再試）；⑤拒；⑥拒；⑦拒（舊規則） |
| AT-QW-74 | 36、42 | `_sentinel_tick`（`NOW`、`MK` armed、哨兵武裝、`FS` 專案目錄）：①痕跡有逾 TTL 的 `spawning`、無成功列、意圖後無新 jsonl；②同前但意圖後出現 stem≠原 sid 且含記錄的新 jsonl；③意圖未逾 TTL；④`MK` 已 `refused` | ①標記 `failed`、attempts 末列 `reason:intent_expired`、`park_intent_expired`、handback＋佇列、隨後 `sentinel_park_takeover` 一次；②補 `spawned ok=True recovered=true`、標記 `fired`、`park_spawn_recovered`、`SP` 0 次；③不動作；④不動作 |
| AT-QW-75 | 22、26、30 | park 登記：短窗 reset＝r（無 `--why`）／`--why`／`--at T`；隨後 keepwarm 啟動讀 `MK`；`early_reset` 對 park 來源：`primary_source=reset`、第 1 次 ping 時 `Q`＝20％＋reset＝r＋300 | 標記 `primary_source`＝reset／reset／at；首行 `target_source=park`，`early=on`／`on`／`off`；`ref_reset`＝`primary_wake_at`−s；`primary_source=reset` 例立即 `resume`、`keepwarm_early_reset`、pings 不加，隨後 §8 觸發 1 寫 `.resumed`、`credential_ok` 假 |
| AT-QW-76 | 64、06 | （r7）`Q` 帶 `reading_at`、補量端點以 `API` 縫計數；c＝20 萬、D＝150（k＝3、V＝7.5、L＝12.5）：①快取 86％、`reading_at`＝now−15 分、補量回 95％；②快取 86％、`reading_at`＝now−5 分、補量拋例外；③快取 86％、`reading_at`＝now−3 分；④快取讀數的 reset＝now−10 分、補量拋例外；⑤keepwarm chain 的 ping 時刻：快取 86％、`reading_at` 早於 210 秒、補量回 95％ | ①`stage=close`、`stale=no`、補量 1 次；②`R_eff`＝14−5＝9 ⇒ `nodispatch`、`stale=yes reading_age=300`；③不補量（0 次）、R＝14 ⇒ `free`、`stale=no`；④`none reason=stale_window`、不外推；⑤該叫醒時刻補量 1 次、判讀（`early_reset`、`ref_pct`、痕跡讀數）用 95 |
| AT-QW-77 | 64、43、26 | （r7）`same_window`：閂鎖 (r, 95, `at`＝t1)；讀數 86（reset＝r）`reading_at`＝t1−10 分／t1＋1 分；`early_reset`：參照 (r, 89, `ref_at`＝t0)，觀測 (r＋300, 30) `obs_at`＝t0−5 分／t0＋1 分；參照 `ref_pct`＝89 時一筆 `obs_at`＝t0−5 分的 99％ | 前者 `same_window` 真（不算換窗；Stop 為「備援缺席」不 block）、後者假（讀數已降 ⇒ block 一次）；`early_reset` 前者假、後者真；`ref_pct` 仍 89（不被早於參照的讀數更新） |
| AT-QW-78 | 65、21、23 | （r7）c＝48 萬（ping_pp 0.995、n*＝`keepwarm.n_star(480000)` 實值）、D＝205（k＝4、V≈11.96）、R＝5、有目標：保溫帳 pings＝6（human 標記未變）；pings＝n*；同前但 D＝455（k＝10 > n*）、R＝12；R＝3（< 4×0.995）；無目標、pings＝n* | chain k＝4（r6 式會判 single）；chain（不 `cap`）；single；single；`cap`（`periodic` 照 R216） |
| AT-QW-79 | 65 | （r7）保溫帳 pings＝6、`TR` 錨點之後：①auto-continuation 記錄＋主控 assistant 含 `Edit` tool_use；②只有主控重掛 keepwarm 的 PowerShell tool_use 回合 ×3；③keepwarm 到目標判 `resume`；④ping 時刻判 `keepwarm_early_reset`；⑤真人提示；⑥（r8）每回合＝一個 `Read`（讀 keepwarm 輸出檔）＋一個 PowerShell `Get-Content <該輸出檔> -Tail 5 ; python tools/sessionctl.py keepwarm --sid <sid>`（T L2906 形態）×3；⑦（r8）一個 `TaskOutput` 讀 keepwarm 背景任務＋一個 PowerShell `python tools/sessionctl.py status`；⑧（r8）一個 PowerShell `Get-Content <輸出檔> ; git add -u`；⑨（r8）一個無法解析的 PowerShell 指令（未閉合引號） | ①pings 0（`work_mark` 變）；②pings 6 不變；③④寫帳後 pings 0；⑤pings 0（既有）；⑥⑦pings 6 不變、`work_mark` 不變；⑧pings 0（`git add` 段非監督）；⑨pings 0（解析不出算真工作） |
| AT-QW-80 | 66 | （r8 改寫，正式環境時序）c＝20 萬（縮放 0.5），`Q` 快取＋補量端點以 `API` 縫計數：①ping 叫醒 #1（補量回 90）→ 40 秒後重掛啟動（快取 90、年齡 40 秒 ⇒ 不補量）→ 端點改回 93 → 45 分後 ping 叫醒 #2（年齡 > 210 秒 ⇒ 補量回 93）；② `ping_costs`＝[0,0,0]；③叫醒 #2 補量失敗（`stale=yes`）；④叫醒 #2 讀數的 reset 晚於 #1 超過 `LATCH_RESET_TOL_MIN`（換窗）；⑤#1 與 #2 之間 `TR` 附加一筆含 `Edit` 的主控回合；⑥#1 與 #2 之間判 `keepwarm_early_reset`；⑦叫醒 #2 讀數 89（< 90，同窗）；⑧連續 7 次 ping 叫醒、每次 +1 | ①重掛啟動時 `ping_costs` 無新筆、補量 0 次；叫醒 #2 寫入 Δ＝3、補量 1 次，下一個 `plan` 的 `ping_pp_eff`＝3、`ping_pp_src=measured`、`calibrated=no`；②`ping_pp_eff`＝0.5、`scaled`；③④⑤⑥⑦不記錄（⑤⑥另斷言 `last_ping_*` 已清空、⑦之後 `last_ping_pct`＝89）；⑧`ping_costs` 共 6 筆中只留最近 5 筆；全程 `FS` 中 `env.shared`／`.env` 未被寫 |
| AT-QW-81 | 23、65 | （r8，QW5-P2-2）`periodic`（無目標），`keepwarm.n_star(ctx)`＝n；保溫帳 pings 0、human 標記＝當前；重複 n 次：叫醒判 `ping` ⇒ `TR` 附加一回合〔`Read` 輸出檔＋PowerShell `Get-Content <輸出檔> ; python tools/sessionctl.py keepwarm --sid <sid>`〕⇒ 重掛 | 第 1～n 次叫醒判 `ping`、pings 逐次 1…n；第 n＋1 次啟動／叫醒判 `cap`（`KEEPWARM_VERDICT=cap`、rc 0）；全程 `work_mark` 不變 |
| AT-QW-82 | 30 | （r8，QW5-P3-2，X-19）park 成功（`SCH` 回 NextRunTime），行程 env 注入 `AUTOSDD_SENTINEL_OFF=1` | 末行 `sentinel=absent reason=sentinel_off`；`SCH` 對 `AutoSDD_Sentinel_<sid>` 的建立／查詢呼叫 0 次；park 本身照常 armed（末行六欄齊全、`NextRunTime` 非空） |

## 4. 真機 E2E（每個 REQ 至少一個；RealVerify 家族 `quotawall`，id `RV-QW01`～`RV-QW30` 對應 `E2E-QW-01`～`30`）

**共通**：
- 沙盒＝R218-B（SE）`Sandbox`，副作用一律先登記 L2 帳、每案前後快照差異為空（SE R-VER-5）。**任何案例不真開窗**（主控裁示）：會走到產品 spawn 的案例一律在 `park`／`park --fire`／`handoff --spawn`／planner 帶 `--claude <SE GUI 子系統替身 claude>`（記 argv／cwd；**以 SE r3 §4.4 的 `<家>/fakeclaude.mode` 檔指定行為**：`resume_ok`＝argv 含 `-r <sid>` 且不含 `--fork-session` 時追加原 sid 逐字稿；`fresh_ok`＝不含 `-r` 或含 `--fork-session` 時新建 uuid 逐字稿；兩者皆存活 `fakeclaude.sleep`〔缺席 20 秒〕再 rc 0；成功模式遇不適用 argv 照 `fail`；`fail`＝立即以 `fakeclaude.rc` 結束。RESUME 路正控用 `resume_ok`、fork 與 FRESH 路正控用 `fresh_ok`、失敗鏈用 `fail`。**正控不以 rc 0 判**：正控案例讓 F4 選路可預期〔RESUME：逐字稿含 usage、上下文小、快取冷；FRESH：逐字稿無 usage ⇒ 量不到〕，並斷言 `park_route` 的 route 與所設模式一致；名稱與值以 SE DES §10.2.1 X-1～X-22 為準，DES §0.4-8）。**沙盒工作樹乾淨**（SE D-23，X-17）：沙盒建好居所與替身後先斷言 `git status --porcelain` 為空，否則判 FAIL「沙盒髒」——`park` 登記與 FRESH（`handoff._refusals`）都以它為前置。**L1 兩站點**（X-7／X-8）：fire 站點拒絕 ⇒ 無 `park_attempt`；spawn 站點回 `RC_SIDEEFFECT_REFUSED` ⇒ 恰 1 筆 `park_attempt` 後終局 `refused`（DES §7.5-1a）。**同一個替身必須貫穿每一次 spawn 嘗試**：RESUME、FRESH（`handoff.spawn`）、`--fork-session`、§7.5 失敗鏈的另一路、§7.6 哨兵接手；任一路未帶替身＝案例 fail「漏帶替身」（現行 `park_cli.py:428` FRESH 路 `handoff.spawn(pkg)` 未帶，會真開窗，REQ-QW-44），並以 `grant` 授與足夠租約；長案例在原始碼常數宣告 `lease_minutes`（≤ `LEASE_CAP` 300 分），登記時刻須滿足 `fire_at ≤ allow_until`（SE D-15）。**L1 拒絕永不當作失敗鏈的輸入**（SE D-13）：失敗鏈一律以替身 `mode=fail` 注入；L1 拒絕只出現在負控分支，期望 `refused`。
- handback／通知佇列／通知 sink 一律落沙盒居所（`--job-env` 轉送）；通知開關經 `--job-env` 只准帶關閉值（沙盒目標登記時行程環境為開啟值 ⇒ SE `job_env_argv` 拋、登記 rc 2，SE D-20 r4），因此桌面通知「開」的輪次（E2E-QW-15 的 1 輪）**不得**在登記行程環境設 `AUTOSDD_DESKTOP_NOTIFY=1`，改由案例以 `qw_schema` 的欄名在登記後把標記 `desktop_notify` 改寫為 `1`（案例自有的標記操作，記入證據檔）、sink 經 SE 重導；「登記行程原值寫進標記」的寫入路徑本身由 AT-QW-46／53 與 SE E2E-SE-09(c)（正式目標）覆蓋。
- 額度＝T5 端點替身（`tools/lib/realverify/cases/prd_px_lib.py`），同時是 `pace_state` 過期補量的端點；跨 TTL 案例每 120 秒重暖；hook 行程讀到非替身讀數或 `stale-cache` ⇒ 案例 fail「載具漏接」——**唯一例外（r7）**：E2E-QW-29／30 以案例自有操作刻意製造的陳舊讀數（只把快取中該讀數的量測時戳改早、讀數值不改，操作與前後位元組記入證據檔），其餘案例照舊。不燒真額度。
- 牆＝T 的真實行段複本（只複製到沙盒 projects 目錄；除下條的時間戳等距平移外不改內容；需要「解除」時接著複製 T 的後續真實行，同樣平移）。
- 模型 haiku；凡依賴模型呼叫特定工具的步驟，先斷言逐字稿確有該 tool_use，沒有判 ENV 重跑，不得判 PASS（QA P3-4）。
- 以 `claude -p` 替身驗「背景任務結束叫醒主控」者，先跑 E2E-QW-27（約 2 分；同型實證＝RV-KW6，`tools/lib/realverify/cases/sessionctl_keepwarm.py:239-268`），並在本案斷言背景任務結束後逐字稿出現新 assistant 記錄；不成立判 ENV、登 OI（DES §0.4-3、§17），不改走真開窗。
- 逐字稿複本（T 行段）一律先把每筆 `timestamp` 等距平移，使最後一筆＝案例開始時刻 −1 分（內容其他位元組不變），錨點與 k 才不隨重放日期漂移；案例斷言 `mode` 與 k 時以平移後實值套 DES §3 公式比對，不寫死。
- 排程一律 SE 沙盒前綴、帶 OS 自毀時限；結束斷言前綴 0 殘留。
- 縮時只用既有產品旗標（keepwarm `--min`、`--idle-min`、watch `--poll-sec`）與替身讀數的 reset；`BACKUP_GRACE_MIN`／`OBSERVE_SEC` 是程式常數，案例照實等待。

| E2E | REQ | 載具 | 斷言 |
|---|---|---|---|
| E2E-QW-01 | 01～04、06、07、09 | 沙盒逐字稿上下文 c 介於 MIN_CTX（以環境下修）與 23 萬之間（ping_pp＝0.5）。替身依序 8 組：five_hour 80％／reset＋150；88％／＋150；93％／＋150；**94％**／＋40 且 c＜MIN_CTX（環境調高 MIN_CTX）；seven_day 99％ 單獨；seven_day_opus 99％ 單獨；端點 500；five_hour 88％ 且行程環境三鍵使 V≥15。每組後真跑 `python tools/sessionctl.py quotawall --sid <沙盒 sid>` 與 `status` | 依序 `free`、`nodispatch`（R 12 ≤ L 12.5）、`close k=3`（R 7 ≤ V 7.5）、`close k=0 V=6`（R＝V＝6，等號邊界）、`free`、`free`、`none reason=…`、`invariant=broken`＋stderr 一行；每行含 `calibrated=`；全部 rc 0 |
| E2E-QW-02 | 05、24、50 | T 截至 L926 複本放沙盒；替身 five_hour 100％、reset＝now＋4 分；真 `sessionctl keepwarm --sid <T sid> --projects-dir <沙盒> --min 1`；再對 T 全檔複本真跑 `waste_census --switch-metrics` | keepwarm 在 reset＋2 分前不結束（期間每分鐘記錄行程存活）；結束 `KEEPWARM_VERDICT=resume`、保溫帳位元組不變；痕跡 `source=cut`；M-K7＝2 件 486,057、M-K1 不含 L935／L1665 |
| E2E-QW-03 | 08、10、11 | 沙盒掛真 `sessionctl_guard.py`（`_hook_launcher` 載具）；真 `claude -p --model haiku`「用 Agent 工具派一個子代理回答 1+1」：(a) `close`；(b) `free`；(c) `nodispatch`；(d) (a)＋Agent prompt 開頭 `續派理由：驗證逃生口是否放行`；(e) (a)＋mode=notify；(f) (a)＋UNATTENDED；(g) (a)＋`AUTOSDD_QUOTAWALL_OFF=1` | (a)(c) PreToolUse 阻斷且內文含階段、D、R、V、L；(b)(d)(e)(f)(g) Agent 實際執行；(d) `quotawall_override`；(e) debug log stderr 一行 |
| E2E-QW-04 | 12、13、15、16、43 | 沙盒真 hook；真 `claude -p` 先派背景子代理（PowerShell 睡 90 秒）後結束回合，讀數 `close`；同一 session 依推回 TaskStop 後再結束；(c) 無在飛、`close`、無 park；(d) 真 hook 載具餵真 Stop payload，`transcript_path`＝T 截至 L1645 複本，同時讓封存／park／保溫／半路停工／完成閘成立（兩支 hook 皆跑）；(e) `close`＋OIR 有 undriven 項；(f) 2026-11-21 實證重放（S-18）：沙盒 session `close`、不登記 park、以 `run_in_background` 掛真 keepwarm（`mode=chain`，holder 帶 `wake_at`），兩支真 hook 餵連續 3 次真 Stop payload（`background_tasks` 含該 running shell、回覆「reset 後繼續」；第 2、3 次替身 reset 分別漂移 +5 分、+70 分、讀數不降），再把替身換成新視窗（讀數低於閂鎖值但仍屬 `close`、reset＋5 小時）後第 4 次。**修前紅的前提由載具保證**：每次 Stop payload 的 `transcript_path` 逐字稿含本回合啟動 keepwarm 的那筆 PowerShell `tool_use`（非唯讀工具）⇒ midwork 的狀態佐證恆成立，修前三次必判半路停工 | (a) 推回含 TaskStop 且不含 finalize 先行；(b) 第二次 Stop 不再推 TaskStop；(c) 推回列五步；(d) 兩支 hook 皆無 `decision:block`、`quotawall_stop_muted` 痕跡；(e) 完成閘為 `systemMessage`、OI 帳 `pushed` 未變；(f) 三次皆無半路停工 block；缺 park 只第 1 次 block、第 2～3 次 `systemMessage`「備援缺席」（漂移不算換窗）、第 4 次（新視窗）再 block 一次；**修前紅**：Q4 前的 `midwork`／`park.stop_verdict` 三次皆 block |
| E2E-QW-05 | 14、28、30、37 | 沙盒交接包 finalize＋真 `park`（替身 `close`、真 schtasks）；真 `claude -p` 回合結束時不掛 keepwarm；再依推回以 `run_in_background` 掛 keepwarm；`park --status --verify` 前後各一次 | park 末行六欄齊全、`Get-ScheduledTask` 沙盒前綴工作 `NextRunTime` 等於 `backup_fire_at`；第一次 Stop 推主載具閘訊息；掛上後 keepwarm 輸出首行 `KEEPWARM_PLAN mode=… wake_at=`＝`primary_wake_at`；`--status` 前 `primary: absent`、後 `primary: live`；第二次 Stop 不推 |
| E2E-QW-06 | 22、23、27 | 真 `claude -p --model haiku` 建沙盒 session（讀大檔撐到 ≥ 降低後的 MIN_CTX）；替身 85％、reset＝now＋9 分；真 `keepwarm --min 2 --idle-min 3` 迴圈：每次 `ping` 後以真 `claude -p -r <sid> "ok"` 製造新錨點再重掛，直到 `resume` | 首行 `mode=chain`；叫醒序列每段 ≤ 3 分＋1 秒；`ping` 次數＝依實際各錨點逐段重算之值（案例記錄每次重掛的錨點，以 §3／§5.2 公式、T_kw 2、idle 3 算剩餘付費次數；總數必在 [k−1, k]，k＝首段計畫值；QA3 P3-3）；末次 ≥ reset＋2 分且 `resume`；`resume` 後那次 `-r` 的首筆 `cache_read ≥ 0.9×` 上下文；pings 不含 `resume` |
| E2E-QW-07 | 20、21、22、61(S5) | 同 E2E-QW-06 的 session：(a) 替身 R＝1（非 affordable）；(b) 環境 MIN_CTX 調高使 ctx 小；(c) 保溫帳預寫 pings＝n*、human 標記＝當前（r7：案例先以 `keepwarm.n_star(ctx)` 實值確認 n* ≥ 首段 k，否則判 ENV）；(d) 真 `park --at now+6分 --why "週窗目標驗證單跳"` 後掛 keepwarm | (a)(b)(d) 首行 `mode=single`；(a)(b) `wake_at`＝reset＋s、(d) `wake_at`＝`primary_wake_at`、`target_source=park`；三者結束皆 `resume`、付費 ping 0；(d) park job 於 +10 分到點判 skip（主控已有新記錄或 `primary_woke`）。**(c)（r7，S-24；r6 期望 single 作廢）**：保溫帳 pings＝n*（上一段殘留、無真人提示）⇒ 首行 `mode=chain`、`k` 依 DES §3 以實際錨點重算之值、全程無 `KEEPWARM_VERDICT=cap`、末跳 `resume`；**修前紅**：R216 keepwarm 啟動即 `cap` |
| E2E-QW-08 | 25 | 真 keepwarm（single，目標 now＋4 分）；以 `NtSuspendProcess` 凍結其行程於目標前 1 分、目標後 3 分恢復；opt-in 變體：`AUTOSDD_RV_ALLOW_SUSPEND=1` 時以喚醒計時器＋`SetSuspendState` 讓整機睡過目標 | 恢復後 ≤ 65 秒結束、`resume`；opt-in 未開 ⇒ 該變體判 ENV（交卷列出） |
| E2E-QW-09 | 26、22、30 | 真 keepwarm（single，目標 now＋3 分）；替身在目標時刻回 100％＋reset＝now＋5 分；第二變體在目標時刻回 500；(c) 提前重置（S-19）：chain（`target_source=reset`、`--min 1 --idle-min 2`、讀數 90、目標 now＋6 分），第 1 次 ping 後替身改回報 30％＋新的未來 reset；(d) 有 park（r5，QA3 P2-2）：沙盒交接包 finalize＋真 `park`（替身讀數 90、reset＝now＋6 分、不帶 `--at`；真 schtasks；`--claude` 替身 `mode=resume_ok`、租約足夠）後掛真 keepwarm（`--min 1 --idle-min 2`），第 1 次 ping 後替身改回報 30％＋reset＝now＋5 小時；(e) 反例：同 (c) 但第 1 次 ping 後替身回報 91％＋reset 延後 70 分（讀數未降），之後在原目標時刻回 30％ | defer：`KEEPWARM_DEFER` 一行、`keepwarm_defer` 痕跡、在新 reset＋2 分才 `resume`；500：照原目標 `resume`；(c) 第 2 個叫醒時刻即 `resume`（早於原目標）、`keepwarm_early_reset` 一列、pings＝1；(d) 標記 `primary_source=reset`、首行 `target_source=park early=on`、第 2 個叫醒時刻即 `resume`、`keepwarm_early_reset` 一列、包 `.resumed` 寫入；park job 於 `backup_fire_at` 到點 skip（交接包非 live）、假 claude 呼叫 0 次、排程沙盒前綴 0 殘留；(e) 第 2 個叫醒時刻照常 ping（無 `keepwarm_early_reset`），在原目標 `resume` |
| E2E-QW-10 | 40、41 | 沙盒 session 交接包 finalize（`.sealed`）：(a) 真 keepwarm 到目標 `resume`；(b) 重新 finalize 後，以真 `sessionctl_guard.py` UserPromptSubmit 載具餵真人提示 payload（快取熱）；(c) 隨後真 Stop payload 帶 running 一般背景 shell；(d) 負控：重新 finalize、不經 (b)、直接 (c) | (a)(b) `.resumed` 寫入、`.sealed` 消失；(c) 無冷叫醒閘推回；(d) 冷叫醒閘推回（證明 (c) 的綠來自 `.resumed`） |
| E2E-QW-11 | 17、18、29 | 真 `sessionctl watch --poll-sec 2`：(a) 替身 `nodispatch`；重掛同讀數；降到 `close`；(b) 逐字稿＝T 截至 L926＋停滯子代理，觀察 10 輪後複製 T L927～L935 並把讀數改 40％；(c) watch 持錨、替身 `close`、reset＝now＋6 分、`--min 2` | (a) `QUOTAWALL_PLAN=stage=nodispatch`、`WATCH_VERDICT=quota`；重掛 30 秒內不結束；`close` 再觸發、處置列含 park 與 keepwarm、不含「快完成」；(b) 牆中無判決、心跳持續、保溫帳不變，續接後 1 輪內 `stall`；(c) 叫醒時刻序列與 E2E-QW-06 同公式、末跳 `resume` |
| E2E-QW-12 | 32、42、61(S6) | 沙盒 park（真 schtasks、`--claude` 替身 `mode=resume_ok`〔(c) 無活窗 ⇒ F4 選路以逐字稿含 usage、上下文小、快取冷固定為 RESUME，斷言 `park_route` route＝RESUME〕、租約足夠）＋真 keepwarm（single、目標＝`primary_wake_at`）：(a) 排程到點時 keepwarm 仍在等（把 keepwarm 目標以替身 reset 延後）；(b) keepwarm 正常結束、沙盒主控回合寫出記錄；(c) 以 `NtSuspendProcess` 凍住 keepwarm 使其活著但過期（S6 卡死），沙盒無活 `cli` 窗；(d) 接 (c)：備援以假 claude 開出新 session 後，恢復被凍住的 keepwarm 行程 | (a) `park_yield_primary`、新排程 `NextRunTime`＝新 wake＋10 分；(b) holder 正常釋放分支 skip `primary_woke` 或 `live_driver`、假 claude 呼叫 0 次；(c) 觀察 180 秒後往下走、`session_switch_spawning` 先於假 claude 的呼叫時戳、`park_attempt` 至少一列；(d) 恢復後 ≤65 秒 `KEEPWARM_VERDICT=handed_over`、包無 `.resumed`、`.sealed` 未被 keepwarm 刪；全程無任何行程被終止 |
| E2E-QW-13 | 33、34、39、44、61(S3) | 真 `claude -p` 沙盒 session 掛 keepwarm（`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` 調高）；殺掉該 `claude` 行程樹（模擬關窗）；真 park 排程到點（`grant` 足夠租約、`fire_at ≤ allow_until`）：(a) `--claude` 替身 `mode=fail`（RESUME 與 FRESH 兩次嘗試皆經同一替身）；(b) 正控：替身 `mode=resume_ok`（F4＝RESUME）與另一輪 `mode=fresh_ok`（F4 強制 FRESH）；(c) 負控：不授與租約 ⇒ L1 拒絕 | holder 判死、無活窗 ⇒ 假 claude argv 不含 `--fork-session`；(a) 替身記錄恰 2 筆（RESUME argv、FRESH argv，皆為同一替身路徑）、attempts 兩列記替身的實際回傳值與原因、`status=failed`、`park_chain_failed`；(b) `park_route` 的 route 分別＝RESUME（resume_ok 輪：沙盒逐字稿含 usage、上下文小、快取冷）與 FRESH（fresh_ok 輪：逐字稿無 usage ⇒ 量不到），與模式一致（不一致 ⇒ ENV 重跑，不判 PASS）；替身 argv 含 `-r <sid>`（resume_ok 輪）或交接包路徑（fresh_ok 輪）、替身寫出逐字稿、`park_resumed`／`park_spawned`；不以替身 rc 0 判正控；真 `claude`／真窗 0；(c) 標記 `refused`、`sideeffect_refused`、無 `park_attempt`／`park_yield_primary`、無 handback、佇列 0 列、假 claude 呼叫 0 次；三者皆無真窗 |
| E2E-QW-14 | 33、48 | 沙盒 `claude.exe` 副本以 `-p` 起跑長回合（PowerShell 睡 40 分）並在執行中改名為 `claude.exe.old.<ts>.<pid>`；沙盒 sessions 登記檔把該 pid 標為同 sid、`entrypoint=cli`、閒置、無 keepwarm；真 park 到點（`--claude` 替身 `mode=fresh_ok`——fork argv 只適用 `fresh_ok`，SE r3 §4.4）、F4 依實值（快取熱 ⇒ RESUME；先斷言 `park_route` route＝RESUME，否則判 ENV 重跑）；fire 前記原 sid 逐字稿 SHA-256；另段：真 `claude -p --model haiku -r <小沙盒 sid> --fork-session "ok"`（無頭、不開窗） | 改名行程在 fire 後仍存在（`Get-Process` 同 pid、同建立時刻）；無 `oldwin_close_*` 痕跡；假 claude argv 含 `--fork-session`；（S-20）替身新建的逐字稿 stem ≠ 原 sid、`session_switch_spawned` `ok=True`、`new_sid`＝該 stem、`route=fork`；原 sid 逐字稿 SHA-256 與 fire 前相同（替身未寫入）；包無 `.resumed`；另段：新逐字稿為新 sid、含原 sid 歷史記錄、原逐字稿 SHA-256 不變 |
| E2E-QW-15 | 34、35、36、44、49 | 沙盒 park（租約足夠、`--claude` 替身 `mode=fail`；標記 `claude` 欄由 park 登記時寫入替身路徑）＋沙盒哨兵武裝（SE 居所；`ctl_env(arm_sentinel=True)`＋WHY 註解，SE D-25；哨兵接手讀標記 `claude` 欄，接手那次仍 `mode=fail`）：到點失敗鏈；兩輪：標記 `desktop_notify` 空／1（空輪＝登記行程環境 `AUTOSDD_DESKTOP_NOTIFY` 空、由登記寫入；1 輪＝登記後由案例改寫標記，r6，見共通條——沙盒登記不得帶開啟值；通知經 SE 重導到沙盒 sink）；之後真跑沙盒 SessionStart hook 與兩次 UserPromptSubmit；等哨兵下一次真巡邏 | 標記 `attempts` 兩列實際 rc、全檔無 `spawn_rc` 字面；`park_chain_failed`；handback 存在且指向該痕跡；佇列一列；sink：空輪 0 則、1 輪 1 則；SessionStart 輸出含該 handback；UserPromptSubmit 第一次注入提示、第二次無；（S-21）park 失敗鏈結束後哨兵排程仍在（沙盒前綴 `Get-ScheduledTaskInfo` 的 `NextRunTime` 非空）；哨兵 `sentinel_park_takeover` 一列、接手那次的 FRESH 嘗試確有替身記錄（未被 dedup 以「同一交接包已 spawn 過」拒，即使距 park 的 FRESH 失敗 < 600 秒）、標記 `failed_final`；替身記錄＝park 兩筆＋哨兵接手筆數，全部同一替身路徑、真 `claude` 0 |
| E2E-QW-16 | 31 | 沙盒 `close` 讀數；finalize＋park＋keepwarm；以真 UserPromptSubmit（真人提示、快取熱）使包記 `.resumed`；結束回合 | 真 Stop 推回要求重新封存＋park（`credential_ok` 失效）；依推回重做後 park 標記指向新包 |
| E2E-QW-17 | 45、46 | 沙盒 `claude.exe` 副本以 `-p` 起跑長回合，執行中改名為 `claude.exe.old.<ts>.<pid>`；另一副本名 `claude-x.exe`；以真 `winproc`／`procstop` 對兩行程判映像；跨 sid 關舊窗以沙盒包走一次（`open_failed` 以已結束的 pid 製造）；改名行程的背景 keepwarm（single 3 分）結束 | `QueryFullProcessImageNameW` 回改名後全名；家族判準接受改名者、拒 `claude-x.exe`；`oldwin_close_degraded` 一列；改名行程背景任務結束後逐字稿出現新 assistant 記錄 |
| E2E-QW-18 | 47 | 以 `sessionctl runlong` 真跑 `python -m unittest discover -s tools/tests -p "test_sessionctl_oldwin.py"` | rc 0；真 `~/.autosdd/traces/oldwin/events.jsonl` 測試期間的新增段（以前後位元組長度切出）不含 `OLDWIN_TEST_SID_MARK`（由案例 import 測試模組常數取得，非手抄）／tmp 路徑／沙盒字樣（真 session 同時追加不算失敗）；前置斷言該常數非空且被測試 sid 實際使用（否則案例 fail「標記失效」） |
| E2E-QW-19 | 51、53 | 收集 E2E-QW-05～16 實跑痕跡與沙盒逐字稿真跑 `waste_census --switch-metrics`；另對真本機 `~/.autosdd/traces/autosdd_session_switch.jsonl` 唯讀跑一次 | M-K8 chain／single／yield 次數與 E2E 實跑相符；M-K9 對真資料：4a45bc75 2026-11-20 22:42 計 failed（原因含 `image_not_allowed`）且「宣稱已排程但未續上」≥1 |
| E2E-QW-20 | 52、55 | 真本機資料跑 `waste_census --calibrate-quotawall` 兩次 | rc 0；印區間數與建議或「未校準」；兩次輸出逐位元組相同；`git status` 顯示 `env.shared` 未被工具改動。**上線閘（REQ-QW-55）**：Q7 時本案三鍵皆有建議值、且 Q7 commit 的 `env.shared` 三鍵＝該建議值；印「未校準」⇒ 本案 PASS 但 OI-e 不結、Q7 不結 |
| E2E-QW-21 | 60、62、63 | 真 repo 腳本：以修憲前 blob（R217 收尾 commit 已落地用其 SHA，否則 `133c3a38`）對工作樹 PRD 行級比對；grep 三份連動文件的追加註記；真跑 AT-QW-61 的原始碼掃描於實作 HEAD | 修憲前每行同位元組、同相對次序；新增恰為 DES 附錄 A 七處（R217 `OI-` 與 R218-B v2.1.25 另列）；三處註記存在且指向本稿；欄名字面只在 `qw_schema.py` |
| E2E-QW-22 | 61(S1) 及 14、21、30、32、40、42、48、54 | 22:42 事件縮時重放（`lease_minutes`＝60）：T 截至 L2435 複本（時間戳平移，共通條）為沙盒 sid 逐字稿（c≈43 萬）；替身 90％、reset＝now＋20 分；活 `cli` 窗＝沙盒 `claude.exe` 副本 `-p` 長回合、執行中改名為 `claude.exe.old.<ts>.<pid>`、sessions 登記檔標同 sid `entrypoint=cli`（同 E2E-QW-14 手法）；主控流程以真 CLI 跑 finalize→park（`--claude` 替身；變體 A `mode=resume_ok`〔預期 0 次呼叫〕、變體 B `mode=fresh_ok`〔fork argv 只適用它〕）→keepwarm（`--min 5 --idle-min 6`）；**重掛驅動器＝案例本身**：每次 `KEEPWARM_VERDICT=ping` 後把 T 最後一筆主控 assistant 記錄複本以當下時戳附加到沙盒逐字稿（43 萬上下文超出 haiku 視窗，不以 `claude -p -r` 重掛、不燒額度），再以同旗標重掛；不再有任何人工輸入。**變體 A（主載具正常）**；**變體 B（主載具被殺）**：keepwarm 首行出現後即殺其行程（holder 記錄留著、pid 死），其餘相同 | A：`quotawall` 印 `stage=nodispatch`、ping_pp≈0.896 `calibrated=no`；keepwarm 首行 `mode=chain`、`target_source=park`、`early=on`（標記 `primary_source=reset`）、k＝依平移後錨點以 T_kw 5、idle 6 套 §3 公式之值；ping 次數＝依實際各錨點逐段重算之值（必在 [k−1, k]，QA3 P3-3）；在 reset＋2 分 `resume`、`.resumed` 寫入；park job 到點 skip（`primary_woke`／`live_driver`／交接包非 live）、假 claude 0 次。B：park job 到點走分支 D、`park_route` route＝RESUME（快取熱）、假 claude argv 含 `-r <sid> --fork-session`；替身新建逐字稿 stem ≠ 原 sid、`spawned ok=True new_sid=<該 stem> route=fork`；原 sid 逐字稿 SHA-256 自 keepwarm 被殺後到 fire 結束不變（替身未寫入）；改名行程同 pid 同建立時刻仍在；無 `oldwin_close_*`；包有 `spawning`→`spawned`、無 `.resumed`。兩變體皆無行程被終止（案例自己殺的 keepwarm 除外）、無真窗。**修前紅**：以 Q3 前的 `park_cli`／`keepwarm`／`procstop` 跑同一重放——A 因 park 互斥不掛保溫、B 走先關再開——兩者皆 `park_resume_failed`＋`image_not_allowed` |
| E2E-QW-23 | 61(S2) | 撞線型：T 截至 L926 複本、已掛 keepwarm（single，目標＝reset＋s）＋沙盒 park；替身 reset＝now＋4 分；到 reset＋100 秒時把 T L931（auto-continuation）以當下時戳附加到沙盒逐字稿 | keepwarm 牆內不結束；park job 到點 skip `live_driver`；keepwarm 在 reset＋2 分結束（`resume`，處置為「已有人在續工」）；無任何 spawn |
| E2E-QW-24 | 25、61(S1) | V-W1 長等待：真 `claude -p`（`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`＝5 小時）掛 keepwarm single 目標 now＋4 小時；long 類 `MIN_WALL_SECONDS`＝14400；`lease_minutes`＝270；前置 E2E-QW-27 PASS | 4 小時後 `resume`，背景任務結束後逐字稿出現新 assistant 記錄；帳列牆鐘 ≥ 14400 秒。harness 不接受該上限（提前收掉背景）⇒ ENV。**互動半不跑**（不真開窗）⇒ DES §17 OI-a 未結；本案 ENV 時 V-W1 整體無驗，交卷與帳本都不得寫成已驗 |
| E2E-QW-25 | 08、61(S4) | 行程環境 `AUTOSDD_UNATTENDED=1`：真跑 `keepwarm`、`park`、`quotawall`，以及真 planner `_resume_tick` 一次（SE 居所、`--claude` 假 claude） | keepwarm `skip reason=unattended`；park rc 4 拒；`quotawall` 印 `stage=none reason=unattended`；planner 行為與既有 FRESH 路一致（痕跡事件名不變） |
| E2E-QW-26 | 45、46 | R217 跨 sid 關舊窗**成功路徑**（D-I 修後首次真的關得掉，QA2 P3-5）：沙盒 `claude.exe` 副本 `-p` 長回合、執行中改名為 `claude.exe.old.<ts>.<pid>`、sessions 登記檔標 sid A `entrypoint=cli`；沙盒交接包屬 A；以另一 sid B 真跑 `handoff --ack <包>` | 改名行程被終止（同 pid 消失）、`oldwin_close_*` 成功痕跡一列、無 `image_not_allowed`；被終止的只有該沙盒副本（L2 帳登記、快照差異空）；修前（Q3 前 `procstop`）`image_not_allowed` |
| E2E-QW-27 | 27 | 前置（約 2 分；RV-KW6 同型）：真 `claude -p --model haiku` 以 `run_in_background` 掛 `sessionctl keepwarm --min 1`，提示要求背景結束後回一個字 | 逐字稿有完成通知 `completed (exit code 0)`，其後有新 assistant 記錄；不成立 ⇒ 依賴本性質的案例（06、17、24）判 ENV、登 OI |
| E2E-QW-28 | 38、61(mac 欄) | macOS 宿主：沙盒 park（launchd）＋keepwarm（`--min 1`，`MAC_HEARTBEAT_MIN` 以 `--heartbeat-min 1` 縮時）；到點不讓路（keepwarm 已殺） | park 末行與 keepwarm 首行 `backup=absent(platform)`；keepwarm 輸出心跳 ≥2 行；到點 attempts＝`platform_unsupported`、`status=failed`、handback／佇列寫入、零 spawn；`launchctl list` 沙盒前綴 0 殘留。**非 mac 宿主 ⇒ ENV**，DES §17 OI-d 未結 |

| E2E-QW-29 | 64、06、43、26 | （r7，E10 ①重放）沙盒 session，c 介於 MIN_CTX（環境下修）與 23 萬（ping_pp 0.5）；替身 86％、reset＝now＋150 分（k＝3、V＝7.5、L＝12.5）。(a) 真跑 `sessionctl quotawall --sid <沙盒 sid>` 一次（快取寫入 86）；案例把快取中該讀數的量測時戳改為 now−15 分（共通條例外），替身改回 95％；再真跑 `quotawall`。(b) 同 (a) 但時戳改 now−5 分、替身回 500。(c) 真 keepwarm chain（`--min 1 --idle-min 2`、替身 90％、reset＝now＋6 分）：第 1 次 ping 前把快取時戳改早、替身改回 95％。(d) 兩支真 hook 餵真 Stop payload（E2E-QW-04(f) 同載具：`close`、不登記 park、running keepwarm shell）：第 1 次 Stop 於替身 95％ 閂鎖；之後把快取改為 86％ 且時戳早於閂鎖時刻、替身回 500 ⇒ 第 2 次 Stop；負控：快取 86％、時戳晚於閂鎖時刻 ⇒ 第 3 次 Stop | (a) 第二次輸出 `QUOTAWALL_PLAN=stage=close`、`stale=no`，替身補量請求計數 +1；(b) `stage=nodispatch`、`stale=yes reading_age=` 介於 300±5；(c) 該次 ping 的痕跡讀數＝95、替身補量請求 +1；(d) 第 1 次 block（缺 park）、第 2 次 `systemMessage`「備援缺席」無 block（早於閂鎖的 86 不算換窗）、負控第 3 次 block（讀數已降 ⇒ 換窗）；全程替身端點以外無額度讀取、不燒真額度、無 spawn。**修前紅**：Q1 前 `plan` 對 (a) 判 `nodispatch`（陳舊 86）、對 (d) 第 2 次判換窗再 block |
| E2E-QW-30 | 65、66、21、23 | （r7，E10 ②③縮時重放）沙盒 session（c ≥ 下修後 MIN_CTX；案例以 `keepwarm.n_star(ctx)` 實值確認 n* ≥ 首段 k，否則判 ENV）；保溫帳預寫 pings＝6、human 標記＝當前；替身 92％（縮放 ping_pp 0.5 時 k＝4、V＝8 ⇒ `close`）、reset＝now＋9 分；真 keepwarm `--min 2 --idle-min 3`；**重掛驅動器＝案例本身**（同 E2E-QW-22）：每次 `KEEPWARM_VERDICT=ping` 後，把 T 於 2026-11-21 01:2x～04:16 的一個真實 keepwarm 重掛回合（只含重掛 keepwarm 的 PowerShell `tool_use`）複本以當下時戳附加到沙盒逐字稿，再以同旗標重掛；不再有任何人工輸入。(a) 啟動前另附加 T 04:16 的 auto-continuation 記錄＋其後一筆含非重掛 `tool_use` 的主控 assistant 記錄（時間戳平移）；(b) 不附加 (a) 的記錄、pings 改預寫 n*；(c) 接 (a)（r8 改寫）：每次 `KEEPWARM_VERDICT=ping` 後，驅動器**先**附加重掛回合並重掛（此時不重暖快取、不改替身；重掛啟動讀到的是 ping 叫醒當時那筆快取），**重掛啟動後**才把替身讀數 +1（同一視窗；1 > 縮放值 0.5，且 4 次後仍 < 100）、立即重暖一次並恢復共通的 120 秒重暖，下一次 ping 叫醒時讀到 +1 後的值；(d) 接 (a)：到目標 `resume`；(e)（r8，`periodic`）另一沙盒 session、替身不給 reset（無目標）、`--min 2 --idle-min 3`，保溫帳預寫 pings＝n*−2；重掛驅動器每次附加的回合改為 T L2906 的「`Get-Content <log> ; keepwarm`」回合複本（另加一個 `Read` 讀同一輸出檔的 `tool_use`），路徑改寫為沙盒輸出檔 | (a) 啟動後保溫帳 pings＝0（帳檔前後）、首行 `mode=chain`；(b) 首行 `mode=chain`、全程無 `cap`；(c) 第 2 次 ping 叫醒起保溫帳 `ping_costs` 每筆皆 1（不得出現由重掛讀數算出的 0）、其後重掛首行 `ping_pp_eff`＝1、`QUOTAWALL_PLAN`／`KEEPWARM_PLAN` 印 `ping_pp_src=measured`、`calibrated=no`、痕跡 `keepwarm_ping_cost`、`git status` 顯示 `env.shared` 未改；(d) `resume` 後保溫帳 pings＝0；(e) 第 2 次叫醒後 `KEEPWARM_VERDICT=cap`（rc 0）、保溫帳 pings＝n*、驅動器不再重掛；全程付費 ping 次數＝依實際錨點逐段重算之值（必在 [k−1, k]）、無 spawn、不燒真額度。**修前紅**：R216 keepwarm 對 (b) 啟動即 `cap`、對 (a) pings 保持 6；r7 規格的忠實實作對 (c) 記 Δ＝0（`ping_pp_eff` 停在縮放值）、對 (e) 每次歸零而永不 `cap` |

## 5. 突變（MU；每條必須讓指定測試轉紅）
| MU | 突變 | 必紅 |
|---|---|---|
| MU-QW-01 | `close` 邊界 `R ≤ V` 改 `R < V` | AT-QW-01 |
| MU-QW-02 | `W_CLOSE` 改 2，或拿掉 `DETECT_MIN·burn` 項 | AT-QW-05、E2E-QW-01 |
| MU-QW-03 | 階段改讀 `quota_policy.decide` band | AT-QW-13 |
| MU-QW-04 | `converge.stop_verdict` 在飛側不呼叫 quotawall | AT-QW-22、E2E-QW-04 |
| MU-QW-05 | 牆內照常結束並 `record_ping` | AT-QW-24、E2E-QW-02 |
| MU-QW-06 | `schedule` 拿掉「最後一跳直接到目標」 | AT-QW-20、E2E-QW-06 |
| MU-QW-07 | `resume` 計入 pings | AT-QW-27、E2E-QW-06 |
| MU-QW-08 | park 前置對任何階段都放行 | AT-QW-38 |
| MU-QW-09 | `backup_fire_at` 去掉寬限（＝`primary_wake_at`） | AT-QW-40、E2E-QW-05 |
| MU-QW-10 | watch 牆中照常判事件 | AT-QW-34、E2E-QW-11 |
| MU-QW-11 | M-K7 件數同時計入 M-K1 | AT-QW-56、E2E-QW-02 |
| MU-QW-12 | 短窗篩選改全軸（週軸入） | AT-QW-12、E2E-QW-01 |
| MU-QW-13 | 牆中不靜音（sessionctl 或 `check_pending_handoff` 任一） | AT-QW-19、E2E-QW-04 |
| MU-QW-14 | `續派理由：` 在 UNATTENDED 下也記 override／不檢查 8 字 | AT-QW-16 |
| MU-QW-15 | 非 affordable 改回「不掛」（skip `quota_doomed`） | AT-QW-21、AT-QW-23、E2E-QW-07 |
| MU-QW-16 | `skip_reason` 加回 `park` | AT-QW-23、E2E-QW-05 |
| MU-QW-17 | 輪詢改為單次 `sleep(due−now)` | AT-QW-26、E2E-QW-08 |
| MU-QW-18 | 讀不到 reset 時以 now＋5 小時推算 | AT-QW-25、E2E-QW-09 |
| MU-QW-19 | `close` 推回改成先 finalize 後 TaskStop | AT-QW-22、E2E-QW-04 |
| MU-QW-20 | 留原窗不呼叫 `mark_resumed` | AT-QW-51、E2E-QW-10 |
| MU-QW-21 | `_cmd_fire` 失敗分支寫字面 `spawn_rc=1` | AT-QW-45、E2E-QW-15 |
| MU-QW-22 | park 路徑恢復「先關同 sid 活窗再 `-r`」 | AT-QW-47、E2E-QW-14、E2E-QW-22(B) |
| MU-QW-23 | 失敗鏈只試 F4 那一條 | AT-QW-45、E2E-QW-13 |
| MU-QW-24 | 哨兵忽略 `status=failed` | AT-QW-48、E2E-QW-15 |
| MU-QW-25 | `image_allowed` 改回精確名集合 | AT-QW-49、E2E-QW-17、E2E-QW-22(B)、E2E-QW-26 |
| MU-QW-26 | `credential_ok` 不看交接包 live | AT-QW-39、E2E-QW-16 |
| MU-QW-27 | 主載具閘不看 `background_tasks`（恆推） | AT-QW-18、E2E-QW-05 |
| MU-QW-28 | park 讓路不讀 holder | AT-QW-41、E2E-QW-12 |
| MU-QW-29 | keepwarm 到目標不重判交棒（直接 `resume`＋`mark_resumed`） | AT-QW-63、E2E-QW-12(d) |
| MU-QW-30 | 未校準 `ping_pp` 拿掉 p(c) 縮放（恆 0.5） | AT-QW-62、AT-QW-07、E2E-QW-22 |
| MU-QW-31 | 非 win32 到點仍呼叫 spawn，或不印 `backup=absent(platform)` | AT-QW-65、E2E-QW-28（mac 宿主） |
| MU-QW-32 | L1 拒絕改寫 `status=failed` 並走失敗鏈 | AT-QW-69、AT-QW-48、E2E-QW-13(c) |
| MU-QW-33 | 主載具閘改讀 OIR 注入後的環境 | AT-QW-67 |
| MU-QW-34 | `park.py` 直接寫字面 `"primary_wake_at"`（不 import `qw_schema`） | AT-QW-61、E2E-QW-21 |
| MU-QW-35 | `midwork.background_idle` 拿掉帶目標主載具例外，或拿掉「缺 park」閂鎖（每次都 block） | AT-QW-70、E2E-QW-04(f) |
| MU-QW-36 | FRESH 路改回 `handoff.spawn(pkg)` 不帶 `--claude`（或失敗鏈另一路不帶 `opts.claude`／哨兵接手不讀標記 `claude` 欄） | AT-QW-71、E2E-QW-13(a)(b)、E2E-QW-15 |
| MU-QW-37 | oldwin 測試拿掉 `trace_dir` tmp 圍籬 | AT-QW-54、E2E-QW-18 |
| MU-QW-38 | `early_reset` 拿掉「讀數已降」條件（只看 reset 變晚），或 defer 時不更新參照 | AT-QW-25（⑤⑥）、E2E-QW-09(e) |
| MU-QW-39 | S-19 對 `target_source=park` 一律不適用（忽略 `primary_source=reset`） | AT-QW-75、E2E-QW-09(d) |
| MU-QW-40 | 閂鎖以 reset 精確值當鍵（`same_window` 改為 `reset_now == latched.reset`） | AT-QW-70、E2E-QW-04(f) |
| MU-QW-41 | fork 成功判準改回 `grew()`（原逐字稿變大即成功） | AT-QW-72 |
| MU-QW-42 | `handoff.spawn` 解除哨兵移回驗證之前，或 dedup 不看 `ok` | AT-QW-73、E2E-QW-15 |
| MU-QW-43 | `spawning` 意圖不檢查期限（永久算交棒），或哨兵不處理過期意圖 | AT-QW-66、AT-QW-74 |
| MU-QW-44 | （r6）§7.5／§7.6 把 spawn 站點的 `RC_SIDEEFFECT_REFUSED` 當一般失敗（改走另一路、寫 handback、標 `failed`） | AT-QW-69③、SE E2E-SE-05（`park --fire` 變體）、SE E2E-SE-01(e3) 於 SE MU-SE-25 下 |
| MU-QW-45 | （r7）`plan` 不看讀數年齡（陳舊讀數直接當新值用），或補量失敗時不外推 | AT-QW-76①②、E2E-QW-29(a)(b) |
| MU-QW-46 | （r7）`same_window`／`early_reset` 接受早於閂鎖 `at`／參照 `ref_at` 的讀數 | AT-QW-77、E2E-QW-29(d) |
| MU-QW-47 | （r7）有目標時 `affordable` 改回 `pings + k ≤ n*`（或 chain 重掛時照 `pings ≥ n*` 判 `cap`） | AT-QW-78、E2E-QW-07(c)、E2E-QW-30(b) |
| MU-QW-48 | （r7）保溫帳只在真人提示歸零（拿掉 `work_mark` 或視窗翻新歸零） | AT-QW-79、E2E-QW-30(a)(d) |
| MU-QW-49 | （r7）`ping_pp_eff` 不取實測（恆縮放值）或取 min | AT-QW-80、E2E-QW-30(c) |
| MU-QW-50 | （r8）Δ 改回以「重掛啟動讀數 − 上一次 ping 叫醒讀數」計算（r7 窗口） | AT-QW-80①、E2E-QW-30(c) |
| MU-QW-51 | （r8）`work_mark` 改回「重掛以外任何 `tool_use` 都算」（或拿掉監督排除、或拿掉 `READONLY_TOOLS` 判準） | AT-QW-79⑥⑦、AT-QW-81、E2E-QW-30(e) |

## 6. 逐功能 E2E 覆蓋表（每個 REQ ≥1 個真機 E2E）
| REQ | E2E | REQ | E2E | REQ | E2E |
|---|---|---|---|---|---|
| 01 | 01 | 17 | 11 | 34 | 13、15 |
| 02 | 01 | 18 | 11 | 35 | 15 |
| 03 | 01 | 20 | 07 | 36 | 15 |
| 04 | 01 | 21 | 07、22 | 37 | 05 |
| 05 | 02 | 22 | 06、07 | 40 | 10、22 |
| 06 | 01 | 23 | 06、30(e) | 41 | 10 |
| 07 | 01 | 24 | 02 | 45 | 17 |
| 08 | 03、25 | 25 | 08、24 | 46 | 17 |
| 09 | 01 | 26 | 09 | 47 | 18 |
| 10 | 03 | 27 | 06 | 50 | 02 |
| 11 | 03 | 28 | 05 | 51 | 19 |
| 12 | 04 | 29 | 11 | 52 | 20 |
| 13 | 04 | 30 | 05、22 | 53 | 19 |
| 14 | 05、22 | 31 | 16 | 60 | 21 |
| 15 | 04 | 32 | 12、22 | 61 | 22(S1)、23(S2)、13(S3)、25(S4)、07(S5)、12(S6)；mac 欄 28 |
| 16 | 04 | 33 | 13、14 | 62 | 21 |
| 38 | 28 | 39 | 13 | 42 | 12、22 |
| 54 | 22 | 55 | 20 | 63 | 21 |
| 43 | 04(f) | 44 | 13、15 | 48 | 14、22(B) |
| 49 | 15 | 64 | 29 | 65 | 07(c)、30(a)(d)(e) |
| 66 | 30(c) | | | | |

覆蓋率 61／61。MU-QW-41／43 只有 AT 必紅：替身 `fresh_ok` 必寫新檔、`fail` 立即結束，E2E 結構上造不出「行程活、原逐字稿變大、無新檔」與「job 寫下意圖後崩潰」兩個情境，故以 AT-QW-72／74 的縫注入覆蓋（照實揭露，不宣稱 E2E 紅）。**ENV 可能分支與承接**（QA2 P3-1 改寫：並非每案都有恆可跑的常態半）：
- E2E-QW-08 真 OS 睡眠變體（未 opt-in ⇒ ENV）：凍結常態半恆可跑，覆蓋 REQ-QW-25。
- E2E-QW-24（V-W1）：**沒有恆可跑的常態半**——`-p` 半在 harness 不接受 5 小時上限時 ENV，互動半依主控裁示不跑；兩半皆無 PASS ⇒ DES §17 OI-a 未結，不得宣稱 V-W1 已驗。REQ-QW-25 另由 E2E-QW-08 覆蓋，REQ-QW-61(S1) 另由 E2E-QW-22 覆蓋。
- E2E-QW-27 不成立 ⇒ 06、17、24 判 ENV、登 OI。
- E2E-QW-28 非 mac 宿主 ⇒ ENV；REQ-QW-38 的 Windows 側與判準由 AT-QW-65 覆蓋，mac 真機登 OI-d。
- 互動視窗相關（V-W1 互動半、V-W3 長壽窗、V-W8 互動 fork）：本輪不設 E2E，OI-a～c（DES §17）。

## 7. 交卷判準（Q7 收尾窗口）
1. AT 82／82 綠、MU 51／51 各自使指定測試轉紅（突變實跑輸出入證據檔；突變轉紅的 E2E 證據是假 `claude` 被呼叫或痕跡，不開真窗）。
2. E2E 30／30 在 `RealVerify_Result_Ledger.md` 最近一次結果為 PASS（ENV 分支依 §6 末段另列，不算 PASS，也不作為整案 FAIL；其殘項登 OIR，且 V-W1 兩半皆非 PASS 時明寫「V-W1 未驗」）。
3. 根層全套（runlong／waitfor）與 `ruff check tools/ .claude/hooks/` 綠；`.env.example` 生成物新鮮度鎖綠；SE 的 AT-SE-39（`SITES` AST 鎖）於 Q3 commit 綠；SE 的 AT-SE-31／E2E-SE-09 黃金序列於 Q3 同一 commit 重釘並綠（S-21 改了 disarm 位置與 spawn 次序）。
4. QA 獨立審查 PASS，且以 E2E-QW-22 變體 A 與 B「修前紅、修後綠」重現 22:42 事件。
5. 上線閘（REQ-QW-55）：校準三鍵有值且寫入 `env.shared`。PRD §16.6 本列 OI 依 1～5 逐項結案；DES §17 OI-a～f 各自依其承接條件結案；M-K8／M-K9 真實頻率屬觀察期指標，不作結案條件（OI-a～c 例外：其承接條件正是觀察指標）。

## 8. r9 增補：2026-11-23 撞牆 RCA（W11a～e）——REQ／AT／E2E／MU（只追加；r8 以前每行不動）

> 設計＝DES 附錄 H（r9）；立案＝PRD 修訂表 v2.1.27、§16.6 2026-11-23 列。**計數**：r8 基線 REQ 61／AT 82／E2E 30／MU 51；r9 新增 REQ 12（70～81）／AT 14（83～96）／E2E 6（31～36，RealVerify `RV-QW31`～`RV-QW36`）／MU 14（52～65）；**合計 REQ 73／AT 96／E2E 36／MU 65**。本檔表頭（L4）與 §7 的 r8 數字由 Q7 收尾窗口在凍結 W11 時同步改為合計（本節不就地改以保持只增不刪）。
> 暴露證據座標：逐字稿 `C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\8feb3081-ccbc-469d-be8a-ec9e00ae3fad.jsonl`，行號 seq 494、711、739、768、857、869、879、880、915；`~/.autosdd/traces/quota_burn.jsonl` 10:00:02 列；`traces/watch/8feb3081….quota.json`（10:21:15）；`traces/halt_8feb3081….json`（10:21:19）；`autosdd_session_switch.jsonl` 07:42:42 兩列；保溫帳 `traces/keepwarm/8feb3081….json`；scratchpad `se11_run.txt`；12:16:07 watch 末行；12:20 半成品硬擋（tag `8feb3081-q4w6-halfwork-20261123`）。**重放夾具**由實作棒自上述座標截取（截到指定 seq 的逐字稿副本＋當時保溫帳＋快取讀數），落證據檔，不連線真額度。

### 8.1 REQ
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-QW-70 | （W11a）主控 Agent／Task／Workflow 的 PreToolUse 呼叫 `quotawall.pretool_verdict`：`nodispatch`／`close` ⇒ rc 2，訊息含階段、D、R、V、L、`calibrated`、ping_pp 來源與步驟；子代理放行；`續派理由：<≥8 字>` 放行記 `quotawall_override`；與收斂閘同時成立只出收斂閘＋一行摘要（REQ-QW-10 的接線兌現） | H.3 W11a | Q4 |
| REQ-QW-71 | （W11a 順序鎖）`sessionctl_guard` 接上 `pretool_verdict` 的同時，`ping_pp_eff` 的乾淨樣本門檻（REQ-QW-74）必須已生效：污染樣本 `[6.0]`（agents=1）不得使 12:16 情境（讀數 47%）被擋；半成品不得留在運作路徑（被停的包保全後移出工作樹） | H.2 | Q4、W11c |
| REQ-QW-72 | （W11c①）`L＝V＋AGENT_EST＋burn_live×min(D,T_OBS)`，`burn_live＝BURN×N`，N＝在飛背景子代理＋背景真 `claude` 行程；`T_OBS＝30` 只准下修；N＝0 ⇒ 與 r8 逐位相同；不新增設定鍵（沿用 `BURN_PP_PER_MIN`、`AGENT_EST_PP`） | H.3 W11c① | W11c |
| REQ-QW-73 | （W11c②）相鄰兩次 ping 叫醒之間任一時刻有在飛子代理或背景 `claude` 行程 ⇒ Δ 不寫進 `ping_costs`（不乾淨）；讀不到在飛狀態 ⇒ 視為不乾淨 | H.3 W11c② | W11c |
| REQ-QW-74 | （W11c③）量測僅在乾淨樣本 ≥ 3 且量測平均 ≤ 縮放／校準值×3 時合格；`ping_pp_eff＝max(縮放／校準值, 合格量測均值)`（保留 S-25 只抬不降；QA W13 P2-2），無合格量測 ⇒ 縮放／校準值；超上限整批丟棄並落 `ping_cost_outlier`；`kw_ledger` schema `/1`→`/2`（每筆 `{pp,clean}`），舊檔一律不乾淨、讀回 `[]`；`qw_schema.ping_costs` 只回乾淨 pp，跨包欄名仍十一個 | H.3 W11c③ | W11c |
| REQ-QW-75 | （W11d①）額度閂鎖拆兩條序列各自閂鎖：原始讀數 prepare＜halt、計畫 nodispatch＜close；任一序列升級即重新觸發；同序列同級／較低級不出聲；閂鎖檔升 schema，舊檔視為無閂鎖 | H.3 W11d | W11d |
| REQ-QW-76 | （W11d②）閂鎖後在飛代理（含背景 claude 行程）數增加且 stage ≥ nodispatch ⇒ 重新觸發一次；N 不增不連發 | H.3 W11d | W11d |
| REQ-QW-77 | （W11d③）事件文案依來源分開：原始讀數觸發「短窗原始讀數 N% 已達 prepare」；計畫階段觸發「額度牆判 nodispatch／close（R=…、L=…；ping_pp 來源=…）」；原始讀數未達 prepare 時不得出現「原始讀數已達」 | H.3 W11d | W11d |
| REQ-QW-78 | （W11b 前半）`quota_messages.pace_line` 在 gate 軸最高帶 ≠ binding 帶時標題補 `｜短窗=<band> five_hour <pct>% 剩 <N> 分`；相同不補；`_binding_key` 行為（含平手取剩餘分鐘較長）不變 | H.3 W11b | W11b |
| REQ-QW-79 | （W11b 後半，排 W6 後）`--pace` 加一行 `QUOTAWALL_PLAN=…`，由 planner 呼叫 `sessionctl.quotawall.plan_lines`；`quota_gate` 不 import `sessionctl`；量不到不印不報錯 | H.3 W11b | W11b（W6 後） |
| REQ-QW-80 | （W11e①）`Case.spends_quota`：本批含此類案例且 `stage∈{nodispatch,close,wall}` 或短窗原始讀數 ≥ prepare ⇒ 整批判 env `QUOTA-PREFLIGHT`、零 claude 行程；量不到放行 | H.3 W11e | W11e |
| REQ-QW-81 | （W11e②）`driver.run_claude` rc≠0 或逾時，且（輸出含 harness 撞額度字樣〔重用既有辨識、實查後寫入，不得猜〕或 halt 標記晚於案例開跑）⇒ `EnvMissing("quota-wall")` 判 env；`AssertionError` 仍判 fail；無字樣且 halt 標記早於開跑 ⇒ 維持 fail | H.3 W11e | W11e |

### 8.2 AT（縫同 §3；加 `ROS`＝假 roster 快照〔在飛代理／背景 claude 行程數與區間內活動〕、`DRV`＝假 `run_claude` 結果）
| AT | REQ | 輸入 | 預期 |
|---|---|---|---|
| AT-QW-83 | 70 | `PL`：主控 Agent／Task／Workflow payload；`Q`：stage nodispatch／close／free；另含子代理 payload、`續派理由：測試用理由八字以上`、`AUTOSDD_UNATTENDED` 下同文 | nodispatch／close ⇒ rc 2 且訊息含階段／D／R／V／L／ping_pp 來源；free、子代理 ⇒ 放行；理由放行記 `quotawall_override`，無人窗口理由無效；收斂閘同時成立只出收斂閘訊息 |
| AT-QW-84 | 71、74 | 組合：hook 接線開啟（用 `converge` 真路徑呼叫 `pretool_verdict`）＋保溫帳 `[6.0]`（agents=1、`clean=false`）＋12:16 快照（ctx 289,728、讀數 47、reset＝now＋204 分） | `ping_pp` 來源＝`calibrated`／`scaled`（不是 `measured`），stage＝`free`，rc 0；同組合下把乾淨門檻拿掉（突變）⇒ stage 變 nodispatch、rc 2 |
| AT-QW-85 | 72 | `Q`：R＝20（讀數 80）、D＝38、burn 0.663、AGENT_EST 取校準鍵、c＝289,728：①N＝1（在飛 1）；②N＝0；③在飛 1＋背景 claude 行程 2（N＝3）；④D＝10（`min(D,T_OBS)＝10`）；⑤D＝90（取 30） | ①`stage＝nodispatch`（L＝V＋AGENT_EST＋0.663×30 ≥ R）；②L 與 r8 公式逐位相同；③L 隨 N 線性放大；④⑤`min(D,T_OBS)` 邊界各自成立；`close` 判準（R ≤ V）①～⑤不變 |
| AT-QW-86 | 73 | `ROS`＋`TR`：兩次 ping 叫醒（t0、t1）讀數差 6；①區間內 S6 子代理在飛；②區間內只有背景 claude 行程；③區間內全無；④`ROS` 讀取拋例外 | ①②④ ⇒ `ping_costs` 不增、痕跡 `keepwarm_ping_cost` 帶 `clean=false`；③ ⇒ 記一筆 `clean=true` |
| AT-QW-87 | 74、73 | `ping_pp_eff(縮放 0.5)`：①樣本 `[6.0]`（unclean）；②乾淨 `[0.4,0.5,0.45]`；③乾淨 `[2.0,2.2,2.1]`（均值 > 縮放×3）；④乾淨僅 2 筆；⑤`kw_ledger` 讀到 `/1` schema 檔（含 `[6.0]`）；⑥乾淨 `[0.8,0.9,0.85]` | ① 退縮放值；② 量測合格但均值 0.45 < 縮放 0.5 ⇒ 0.5（只抬不降）；⑥ 採量測均值 0.85；③ 整批丟棄、退縮放值、痕跡 `ping_cost_outlier`（含樣本與倍數）；④ 退縮放值；⑤ 讀回 `[]`、視為不乾淨 |
| AT-QW-88 | 74、72 | 12:16 情境：ctx＝289,728、讀數 47（R＝53）、k＝4、保溫帳 `[6.0]`＋Q5 校準 `PP_PER_KUNIT＝0.0061` | `ping_pp≈0.381`（校準）、`V≈5.70`、`L≈6.88`（N＝0）、stage＝`free`；對照：把 `[6.0]` 當量測值採用則 `V＝52`（watch 實印值）、stage＝nodispatch |
| AT-QW-89 | 75 | 閂鎖在 `(計畫, close, r)`；之後原始讀數跨 prepare（同 r）；反向：先 `(原始, prepare, r)` 再計畫 nodispatch；同序列同級；同序列降級 | 前兩者各自觸發一次；同序列同級／降級不出聲；`(原始, halt)` 仍高於 prepare；舊 schema 閂鎖檔 ⇒ 視為無閂鎖、不報錯 |
| AT-QW-90 | 76 | 閂鎖在 nodispatch（N＝1）：①N 1→2 且 stage＝nodispatch；②N 2→2；③N 1→2 但 stage＝free；④連續兩次重掛 N 都 2 | ① 觸發一次並更新 `n_latched`；②④ 不觸發；③ 不觸發 |
| AT-QW-91 | 77 | 事件文案：①stage＝nodispatch、原始讀數 47；②原始讀數 90、stage＝free；③原始讀數 90 且 stage＝close | ① 文案含「額度牆判 nodispatch」「R=」「L=」「ping_pp 來源=」，**不含**「原始讀數已達」；② 含「短窗原始讀數 90% 已達 prepare」、不含「額度牆判」；③ 兩句並陳 |
| AT-QW-92 | 78 | `pace_line`：①five_hour 80% converge 剩 38 分＋seven_day 58% notice（平手取 seven_day 為 binding）；②five_hour 即 binding；③five_hour 低於 binding 帶；④`_binding_key` 回歸：同 ①餵 `_binding_key`、平手結果與 r8 相同 | ① 標題含 `短窗=converge five_hour 80% 剩 38 分`；②③ 不補；④ binding 仍為 seven_day（不改規則） |
| AT-QW-93 | 79 | 沙盒快取＝10:00:02 讀數（80／58，reset 10:40）；planner `--pace`；AST 掃 `tools/lib/quota_gate*`；量不到 | 輸出含 `短窗=converge five_hour` 與 `QUOTAWALL_PLAN=` 一行；`quota_gate` 無 `sessionctl` import；量不到 ⇒ 不印該行、rc 不變 |
| AT-QW-94 | 80 | `Q` 與假 runner：①含 `spends_quota` 案例＋stage close；②同批但 stage free、讀數 60；③無 `spends_quota` 案例＋stage close；④含 `spends_quota`＋原始讀數 ≥ prepare；⑤量不到 | ①④ 整批 env `QUOTA-PREFLIGHT`、`run_claude` 呼叫 0 次；②③⑤ 照跑 |
| AT-QW-95 | 81 | `DRV` 結果：①rc＝-9＋輸出含撞額度字樣；②rc＝1、無字樣、halt 標記時間 > 案例開跑；③rc＝1、無字樣、halt 標記早於開跑；④rc＝0 但案例 `AssertionError`；⑤逾時＋無字樣＋halt 標記晚於開跑 | ①②⑤ `EnvMissing("quota-wall")`、結果 env；③④ 判 fail（真缺陷不被吞） |
| AT-QW-96 | 70、75 | 12:20 事故回歸：半成品式「污染樣本＋hook 接線」組合在**新規則下**重放 12:20 payload（短窗 54%、保溫帳 `[6.0]`、agents＝1） | rc 0 放行（污染樣本不得使 54% 讀數被擋）；同輸入下把乾淨門檻拿掉（突變）⇒ rc 2。「半成品不得留在運作路徑」是流程規則（DES H.2-3），無機械測試，不宣稱有 |

### 8.3 E2E（真機；RealVerify 家族 `quotawall`；共通沿用 §4：不需人按鍵、不真開窗、不燒真額度到撞牆；重放以本事件逐字稿截取檔為主）
| E2E | REQ | 情境與步驟 | 預期 |
|---|---|---|---|
| E2E-QW-31（RV-QW31） | 70、71、74 | **12:16／12:20 重放**：沙盒 session 帶 12:16 快照（ctx 28.9 萬、讀數 47、reset 未來 204 分）與污染保溫帳 `[6.0]`；(a) 真跑 `sessionctl quotawall --sid <沙盒 sid>`；(b) 以真 hook 行程（`sessionctl_guard` PreToolUse）餵主控 `Agent` payload；(c) 重放 07:43（讀數 64、`[6.0]`）。**N 釘死（QA W13 P2-1）**：12:16 在飛 3 支（Q4、W6、RCA）⇒ N＝3；12:20 在飛 0（Q4／W6 已停、RCA 已交卷）⇒ N＝0 | 12:16（N＝3）：(a)(b) `stage≠close`（nodispatch 可接受——當時實燒約 1.8 pp／分，擋第 4 支屬正確）；12:20（N＝0）：(a) `stage=free`、(b) rc 0 不得被擋；(c) 不再是 close；修前（無門檻）皆紅 |
| E2E-QW-32（RV-QW32） | 70、72、78 | **10:02 重放**：seq 869 時刻快照（讀數 80、reset 10:40、D＝38；背景 `RV-SE11` 真 claude 行程以替身 `sleep` 行程偽裝成 claude 身分；Q3 是待派者、由 `AGENT_EST` 承擔，**N 釘死＝1**〔QA W13 P2-1〕；QA 自算 L＝25.25 ≥ R＝20）；(a) planner `--pace` 標題；(b) 真 hook 餵主控 `Agent` payload | (a) 標題含 `短窗=converge five_hour 80% 剩 38 分`（W11b）；(b) W11c① 上線後 rc 2、stage＝nodispatch 或 close、訊息含「續派理由」（W11c① 前此半段記 ENV-NOT-YET，不得宣稱 PASS） |
| E2E-QW-33（RV-QW33） | 73、74 | 真 keepwarm 行程（`--min 1`、縮時）兩次 ping 之間以替身在飛子代理（沙盒 `claude -p` 長回合）跑；接著再無在飛區間補兩筆乾淨、再一筆離群；讀 `kw_ledger` 與 `autosdd_session_switch.jsonl` | 在飛區間 Δ 不入帳（`clean=false`）；乾淨 < 3 筆時 `plan` 的 ping_pp 來源非 `measured`；≥3 筆乾淨且合理時採用；離群時痕跡 `ping_cost_outlier` |
| E2E-QW-34（RV-QW34） | 75、76、77 | 真 watch 行程＋沙盒快取依序 64→80→88（reset 固定）；中途加掛一支在飛子代理 | 64 時不誤報 close；80 時計畫序列／原始序列各自觸發且文案各依來源；88 跨 prepare 觸發；N 增加且 stage ≥ nodispatch 時再觸發一次；末行 `WATCH_VERDICT=` 保持 rc 0（DEF-200-622） |
| E2E-QW-35（RV-QW35） | 80、81 | `realverify run` 於沙盒：(a) 預設 stage＝close 的沙盒快取＋含 `spends_quota` 案例 ⇒ 整批；(b) 假 `claude` 替身輸出實查後的撞額度字樣且 rc≠0 ⇒ 單案；(c) 假 `claude` 無字樣、halt 標記早於開跑、rc≠0 | (a) env `QUOTA-PREFLIGHT`、替身被呼叫 0 次；(b) 判 env；(c) 判 fail；字樣取自證據檔（OI-g 未結則 (b) 的字樣分支標 ENV-PENDING、halt 標記分支照跑） |
| E2E-QW-36（RV-QW36） | 78、79 | 沙盒 `~/.autosdd` 快取＝10:00:02 讀數；真跑 `python tools/session_resume_planner.py --pace`（W6 後含 QW 行） | 標題含 converge＋five_hour；QW 行在 W6 之後出現且量不到時不出；rc 與 r8 相同 |

### 8.4 MU（每條必須讓指定測試轉紅）
| MU | 突變 | 必紅 |
|---|---|---|
| MU-QW-52 | 拿掉 `sessionctl_guard` 對 `quotawall.pretool_verdict` 的呼叫（或對主控放行） | AT-QW-83、E2E-QW-32(b) |
| MU-QW-53 | 拿掉乾淨樣本門檻（n＝1 即採用量測值）而保留 hook 接線 | AT-QW-84、AT-QW-87①、AT-QW-88、AT-QW-96、E2E-QW-31 |
| MU-QW-54 | `L` 拿掉 `burn_live×min(D,T_OBS)` 項，或 N 只算子代理不算背景 claude 行程 | AT-QW-85、E2E-QW-32(b) |
| MU-QW-55 | `ping_cost` 在區間內有在飛代理／背景 claude 仍記入 | AT-QW-86、E2E-QW-33 |
| MU-QW-56 | `MIN_CLEAN_SAMPLES` 改 1，或拿掉 `OUTLIER_X` 上限 | AT-QW-87②③④、E2E-QW-33 |
| MU-QW-57 | 閂鎖回單一序列（prepare＜nodispatch＜close＜halt 一條） | AT-QW-89、E2E-QW-34 |
| MU-QW-58 | 新派工（N 增加）不重新評估閂鎖 | AT-QW-90、E2E-QW-34 |
| MU-QW-59 | watch 文案寫死「原始讀數已達 prepare」 | AT-QW-91、E2E-QW-34 |
| MU-QW-60 | `pace_line` 不補「短窗」欄（或補成 binding 欄） | AT-QW-92①、E2E-QW-32(a)、E2E-QW-36 |
| MU-QW-61 | 誤改 `_binding_key` 平手規則（改取剩餘分鐘較短） | AT-QW-92④ |
| MU-QW-62 | `--pace` 的 QW 行缺席，或 `quota_gate` import `sessionctl` | AT-QW-93、E2E-QW-36 |
| MU-QW-63 | realverify 前置額度閘拿掉（或不看 `spends_quota`） | AT-QW-94①④、E2E-QW-35(a) |
| MU-QW-64 | `run_claude` 撞牆仍判 fail；或反向——rc≠0 一律判 env（吞掉真缺陷） | AT-QW-95①②③④、E2E-QW-35(b)(c) |
| MU-QW-65 | schema `/1` 舊檔樣本不汰除（視為乾淨） | AT-QW-87⑤、E2E-QW-31 |

### 8.5 逐功能 E2E 覆蓋（r9；每個新 REQ ≥1 個真機 E2E）
| REQ | E2E | REQ | E2E | REQ | E2E |
|---|---|---|---|---|---|
| 70 | 31、32 | 75 | 34 | 80 | 35 |
| 71 | 31 | 76 | 34 | 81 | 35 |
| 72 | 32 | 77 | 34 | | |
| 73 | 33 | 78 | 32、36 | | |
| 74 | 31、33 | 79 | 36 | | |

覆蓋率 12／12。**照實揭露的結構性限制**：E2E-QW-32(b) 在 W11c① 上線前、E2E-QW-36 的 QW 行在 W6 前結構上造不出，列為「依賴上線序的 ENV-NOT-YET」，不算 PASS 也不作整案 FAIL，上線序到位後補跑；E2E-QW-35(b) 的字樣分支受 DES OI-g 約束；MU-QW-61 只有 AT 必紅（呈現層規則回歸，E2E 結構上不涉及平手規則）。
