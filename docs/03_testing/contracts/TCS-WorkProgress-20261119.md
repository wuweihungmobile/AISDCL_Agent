# TCS-WorkProgress-20261119：工作推進軸（未結項登記簿、完成閘、驅動器、叫醒預算、名冊收斂、AutoClaude 無人舵手）——需求＋驗收合一

> 角色：SD（R217，AISDLC 第 2 階段）。設計全文＝`docs/02_architecture/WorkProgress_Axis_Design.md`（下稱 **DES**）；上游＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 **PRD**，修憲草案見 DES 附錄 A）。
> 輸入：Architect 報告（**ARC**）、SA 報告（**SA**，100 條追溯矩陣、26 項未結、R217-E2E-01～08、R217-DEF-01～03）。編號由 SA 矩陣轉寫：R217-REQ-xx → REQ-WP-xx、R217-E2E-xx → 本檔 E2E-WP-xx（對照見 §6）。
> 修訂 r2（2026-11-19）：回應規格獨立審查 FAIL（P2×6＋P3×8），對應 DES 檔頭 r2 註記；新增／改寫的列以「（r2）」標示。計數：REQ 64、AT 62、E2E 44、MU 16。
> 修訂 r3（2026-11-19）：回應規格獨立審查第二次退件（P2：N-1 有 attempt 之後的空窗、N-2 window_cap 計入 deferrals、N-3 同 sid 雙視窗；P3×6），併入掌舵者兩則新指令：①結案判準「PRD 全功能 E2E」（scratchpad `r217_acceptance_rule.md`，新增 §1.9、§10）；②舊視窗有條件自動關閉（2026-11-19 互動選項「有條件自動關 (Recommended)」，新增 §1.5b）。新增／改寫的列以「（r3）」標示。計數：REQ 90、AT 81、E2E 62、MU 27。
> 修訂 r4（2026-11-19）：回應規格獨立審查第三次退件（P2×4＋P3×7），對應 DES 檔頭 r4 註記與 D-15～D-18。主要變更：§10.3 附錄逐列寫出 A01～A46、B01～B03 的載具與斷言鍵（49／49）；帳列判讀改認「執行案例」欄並與 OIR 對帳（REQ-WP-82、99）；空殼案例防線（REQ-WP-100）；`留：` 否決（REQ-WP-98）；舊窗關閉的 TOCTOU、條件 ② 與重試統一（REQ-WP-55～57）；`AutoSDD_OldWinClose_*` 現查與回收（REQ-WP-101）；對照表重產（REQ-WP-102）；沙盒圍籬改快照比對（§4.1）。新增／改寫的列以「（r4）」標示。計數：REQ 95、AT 92、E2E 64、MU 34。
> 🔴 （r3）結案判準取代舊 §9 第 2 條：TCS 全部 E2E 與 PRD 全功能 E2E 對照表的全部條目，在 `RealVerify_Result_Ledger.md` 最近一次結果都必須是 PASS；long、soak、時間閘案例由驅動器真的跑完；「已排程」與 OIR `driven`／`escalated` 都不算 PASS。例外只限 4 條（C02 軟線、C14 hold、A53 §13 法務、A54 A7），理由見 §10.2。
> 前綴：`REQ-WP-`、`AT-WP-`（單元／整合，縫注入）、`E2E-WP-`（真機）、`MU-WP-`（突變，必須讓指定測試轉紅）。
> 🔴 掌舵者 2026-11-18 指令：每個功能都要有 E2E（真行程／真排程／真 `claude -p` 子行程／真 hook／真逐字稿重放才算，單元測試不算）；待真機尾巴＝未完成。E2E 結果一律入 `docs/06_quality/RealVerify_Result_Ledger.md`，未入帳＝未結，且本身就是 OIR 的 `auto` 列。
> 測試慣例沿用 sessionctl：時間注入 `now`、路徑圍籬 tmp、不讀本機真實 `~/.claude`（E2E 除外）、不開測試用環境變數鉤、禁用 skip。E2E 一律在 repo 外沙盒（`tools/lib/realverify/sandbox.py`），結束後沙盒與 `~/.claude/projects/<沙盒 slug>` 必須不存在（REQ-WP-44）。
> 本檔是待驗標記詞彙的定義文件之一，列在 `OpenItems_Protocol/params.json` 的 `vocabulary_definers`（DES §3.5）。

## 0. 模組落點表
照 DES §12（本檔不重抄）。§5.6 檔案集合＝DES §12「路徑」欄全部。

## 1. 需求（REQ）

### 1.1 OIR 核心（期 A，DES §2～§3）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-01 | OIR＝`docs/06_quality/OpenItems_Event_Ledger.jsonl` append-only 事件帳本；fold 以 `(ts, seq)` 排序得每個 OI 的現態；壞行跳過並在 `list` 末行計數 | §3.1、§3.3 | A1 |
| REQ-WP-02 | 事件 schema（`open／drive／attempt／close／escalate／convert／retire`）與必填欄：`kind ∈ {auto,observe,human,k1}`；auto／observe 必有 `check`；observe 必有 `due`；human 必有 `why_not_auto`（≥8 字）；不合 ⇒ 指令 rc 2、不寫事件 | §3.2 | A1 |
| REQ-WP-03 | 完成定義：範圍內無 undriven；undriven＝`open` 且無有效憑證且非 `listed／escalated`；`driven` 有效性依 DES §3.3 對帳表（r2）：觸發前看排程工作存在（快取）；`at＋start_grace` 後無 `start` ⇒ undriven；有 `start` 無 `attempt` 且逾 `start.ts＋budget_minutes` ⇒ undriven；觸發後不讀 `NextRunTime`（Windows 觸發後為空、macOS 無此值）；（r3）有 `attempt` 時另依 REQ-WP-27 | §2、§3.3 | A1 |
| REQ-WP-04 | `openitems scan`：依 `params.json` 的 `scan_globs`／`marker_regex` 掃標記，報告每處是否帶 OI id；`vocabulary_definers` 不判；末行 `OPENITEMS_SCAN=mapped=<n> unmapped=<m>`，rc 0 | §3.5 | A1 |
| REQ-WP-05 | 防永動：`attempts ≥ max_attempts`（出廠 2）⇒ `escalate`；`deferrals ≥ max_deferrals`（出廠 6）⇒ `escalate`；escalated 不再自動重排；（r3）`deferrals` 只計 `reason=interactive`，見 REQ-WP-28 | §3.3 | A2 |
| REQ-WP-06 | 收件範圍：`open` 的 `source` 必須指向 TCS／缺陷帳本／ADR／PRD 的座標（路徑前綴白名單在 `params.json`）；否則 rc 2（防覆蓋度缺口混入） | §3.4 | A1 |
| REQ-WP-07 | 配號 `OI-<YYYYMMDD>-<NNN>` 在寫入鎖內取當日最大號＋1；兩行程同時 `open` 不得撞號 | §3.2 | A1 |
| REQ-WP-08 | （r2）`start` 事件：run-driver 第 0 步寫 `drive_seq`、`pid`、`proc_start`、`budget_minutes`；`budget_minutes`＝auto：案例牆鐘上限＋`run_budget_margin_minutes`，observe：`observe_timeout_minutes` | §3.2、§3.3、§5.1-0 | A2 |
| REQ-WP-09 | （r2）驅動器自有寫入面＝`params.json` 的 `driver_own_prefixes`（OIR 帳＋RealVerify 帳）；handoff `--spawn` 前置排除「SI 自有面 ∪ 驅動器自有面」（各來源讀不到 ⇒ 該來源不排除）；SI `dirty_paths` 另排除驅動器自有面；SI `OWN_PREFIXES` 與提交白名單不變；驅動器不寫兩本帳以外的 repo 路徑 | §5.5 | A5 |
| REQ-WP-27 | （r3，審查 N-1）有 `attempt` 時，driven ⇔ 它之後（序號更大）有對應的後續事件：fail 未達上限或 deferred ⇒ `drive`；pass ⇒ `close`；達上限 ⇒ `escalate`；或仍在 `a.ts + followup_grace_minutes`（出廠 15）之內。否則 undriven，包括 run-driver 在 attempt 後崩潰、重排時憑證回讀失敗而不寫 `drive` 兩種情形。run-driver 重排失敗時末行加 `redrive=failed`、rc 0，不在行程內重試 | §3.3、§5.1-6 | A1、A2 |

### 1.2 驅動器（期 A，DES §5）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-10 | `drive <id>`（auto／observe）：建一次性排程 `AutoSDD_OpenItem_<id>_<yyyyMMddHHmm>`（四項設定）；建立後回讀排程器自報 `NextRunTime`（macOS：launchd rc），取不到 ⇒ rc≠0、不寫 `drive` 事件；成功末行貼出憑證原文 | §5、§5.2 | A2 |
| REQ-WP-11 | `run-driver <id>`：已 closed／retired ⇒ 自刪排程 rc 0；否則執行 `check`，寫 `attempt`；pass ⇒ `close`（證據＝帳列時間戳＋案例）；fail ⇒ 未達上限重排並寫新 `drive`，達上限 `escalate`；一律刪自己這次的排程；末行 `OPENITEMS_DRIVER=<result> id=<id> n=<n>`，正常判決 rc 0 | §5.1 | A2 |
| REQ-WP-12 | 讓路：同專案互動 session 一個巡邏間隔內有真實工作（`transcript_activity` 判準）⇒ `attempt(deferred, reason=interactive)`、重排，不耗 attempts | §5.1-2 | A2 |
| REQ-WP-13 | 額度：`--pace` 帶在收斂以上 ⇒ `deferred(reason=quota)`，重排到短窗 reset 後（量不到 ⇒ `retry_backoff_minutes`） | §5.1-3 | A2 |
| REQ-WP-14 | observe：觸發時刻＝`due`；到期執行量測 argv 並依 `pass` 判準關閉或計 attempt | §5 | A2 |
| REQ-WP-15 | 人工清單：SessionStart 簡報印 `listed`＋`escalated` 前 `human_cap`（7）項與「另 k 項」；human 列數 > cap 時完成閘每 session 首次 Stop 附一行出聲（不阻斷） | §5.3 | A5 |
| REQ-WP-16 | k1：只列不推；`close` 只接受掌舵者真人發言座標且 `--by human`；AskUserQuestion 回答不算 | §5 | A1 |
| REQ-WP-17 | stale-pass：家族原始檔（案例模組 `SOURCES`）最後 commit 時間晚於該家族最後一筆 pass 帳列 ⇒ 開 auto 列；同家族已有 open／driven 列不重開；（r2 防永動）同家族有 escalated／listed／retired 列時，原始檔最後 commit 必須晚於最晚一筆 escalate／retire／human 化 convert 的 `ts` 才開；觸發事件＝(a) 收尾窗口最後 commit 後手跑（§9 第 6 條）、(b) `run-driver` 第 0 步；無日曆觸發 | §8-4 | A2 |
| REQ-WP-18 | `sessionctl status` 排程區列出 `AutoSDD_OpenItem_*` 與其 NextRunTime | §5.2 | A2 |
| REQ-WP-19 | （r2）扇出上界：全域互斥鎖 `driver.lock`（持有者判活＝pid＋建立時間相符且未逾預算）；每 reset 窗至多 `max_runs_per_window`（2）次執行（reset 量不到退用 `cap_window_minutes` 滾動區間）；`drive`／重排錯開 ≥`stagger_minutes`；`--pace` 雙軸任一 ≥收斂、可派數 <1 或讀不到 ⇒ deferred(quota)；`busy` 不計 attempts／deferrals；（r3）每窗名額改依 REQ-WP-28 的先進先出；soak 案例走 REQ-WP-97 的獨立通道 | §5.1、§5.4 | A2 |
| REQ-WP-28 | （r3，審查 N-2，DES D-11）`quota`、`window_cap`、`busy` 都不計 deferrals。排隊鍵＝`(open.ts, id)`；拿本窗名額的條件是 `R + O < max_runs_per_window`（`R`＝本窗已執行次數，`O`＝排隊鍵較小、`d.at` 在本窗、且本窗尚無 `start` 的 driven 列數）；`window_cap`／`quota` 重排依排隊鍵順序分配下一窗時槽；`openitems list` 印每列的已排隊窗數（資訊欄） | §3.3、§5.4-2／4 | A2 |

### 1.3 完成閘（期 A，DES §4）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-20 | Stop 完成閘：`stop_hook_active` 假 ∧ 非無人窗口 ∧ undriven ≥1 ∧ 本回合狀態佐證（非唯讀工具或 git 髒）⇒ 推回一次，列前 5 個 undriven 與三條出口；判準不讀助理回覆文字 | §4.1 | A5 |
| REQ-WP-21 | 與半路停工、散文交棒合併為一則推回，次序 半路停工 → 散文交棒 → 完成閘 | §4.2 | A5 |
| REQ-WP-22 | `midwork.background_idle` 排除純保溫 shell（判準＝`roster.py` 的 `WATCH_CMD_RE`／`KEEPWARM_CMD_RE`，不複製正則） | §4.3 | A5 |
| REQ-WP-23 | CI 鎖：git 追蹤文件（`vocabulary_definers` 除外）出現待驗標記而該行無 OI id ⇒ 紅；存量以 A8 種子後歸零，之後零容忍 | §3.5 | A7 |
| REQ-WP-24 | 保溫閘讓路：完成閘推回當回合寫 `trace_dir()/openitems/<sid>.gate`；`sessionctl_guard` 保溫閘讀到即不推「掛保溫」 | §4.4 | A5 |
| REQ-WP-25 | fail-open：OIR 讀不到／解析失敗 ⇒ 不推回、stderr 一行 | §4.2 | A5 |
| REQ-WP-26 | （r2）完成閘不開子行程：driven 判定只讀帳本＋排程快取 `sched_cache.json`（一次批次列舉寫入，TTL `sched_cache_ttl_seconds`）；N＝50 時閘判準 ≤2 秒；`list --verify` 不論 N 只開 1 個列舉子行程 | §4.5 | A2、A5 |

### 1.4 叫醒預算（期 A，DES §6）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-30 | watch 不以 `all_done` 退出；全部交卷後轉保溫模式，只剩 `keepwarm`／`cap`／`idle`／`quota`／`budget` 會退出（r3：與 REQ-WP-36 一致，各事件的時點見 REQ-WP-36） | §6.1、§6.3 | A4 |
| REQ-WP-31 | 保溫錨互斥：`trace_dir()/keepwarm/<sid>.holder`（pid＋建立時間）；持有者活著時第二個保溫行程印 `KEEPWARM_VERDICT=skip reason=holder_running` rc 0 結束 | §6.2 | A4 |
| REQ-WP-32 | watch 的 keepwarm 事件與 keepwarm 指令共用保溫帳 `pings`，上限 n*；達上限時 watch 在保溫點以 `cap` 退出（不再以 keepwarm 退出，見 REQ-WP-36） | §6.3 | A4 |
| REQ-WP-33 | waste_census M-WB1（保溫叫醒後主控回合數；資訊欄、不作閘門與結案條件）、M-WB2（子代理完成通知後 60 秒內的重複叫醒數，目標 0） | §6.4 | A7 |
| REQ-WP-34 | 處置表 `ping` 列：重掛同一指令並結束回合 | §6.4 | A4 |
| REQ-WP-35 | V-P6：`waste_census --pace-metrics`、`--replay-pace-floor` 實作（D-7，A7）；`realverify/cases/quota_rush.py:87-93` 的「未落地」斷言反轉（A6 持有，A7 commit 後做） | §0.3 D-7、§11 | A7、A6 |
| REQ-WP-36 | （r2）watch 保溫模式退出條件：保溫點到時 `pings<n*` 且保溫適用 ⇒ `keepwarm`；`pings≥n*` ⇒ `cap`；保溫不適用（條件同 `keepwarm.stop_verdict`）⇒ `idle`；另 `quota`／`budget`；皆 rc 0；全部交卷後至多再叫醒一次 | §6.3 | A4 |

### 1.5 名冊（期 A，DES §7）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-40 | killed 偵測增量全掃（快取 `size／offset／ids`；檔變小重掃） | §7 DEF-01 | A3 |
| REQ-WP-41 | `procstop.owner_sid_of`：sessions 登記檔（`sessionId`＋`procStart` 相符）→ 旗標形態 → 空字串；`alive` 改用它；`sid_of` 改名 `first_uuid_of` 僅供顯示；（r2）相符＝Windows GetProcessTimes creation FILETIME 全等，取不到才退 CIM `CreationDate` 容差 \|Δ\|<10（100ns）；非 Windows 跳過登記檔；同 sid 多檔任一通過即活；不讀 `kind`／`entrypoint` | §7 DEF-02 | A3 |
| REQ-WP-42 | quiet 降級：擁有者已交棒（`.ack`／spawn 痕跡）或不活 ⇒ 殘局 | §7 | A3 |
| REQ-WP-43 | 殘局滿壽命寫 `trace_dir()/roster/retired.jsonl`，`--all` 只顯示計數；不刪逐字稿 | §7 | A3 |
| REQ-WP-44 | 沙盒 cleanup：行程樹結束 → 等 ≤5 秒 → `rmtree` 不吞錯，殘留即案例 fail；`realverify sweep` 清孤兒 slug 目錄（沙盒根不存在 ∧ 無 session 登記檔 `cwd` 指向） | §7 DEF-03 | A3 |

### 1.5b 同 sid 雙視窗與舊視窗有條件自動關閉（r3；期 A，DES §7.1；審查 N-3＋掌舵者 2026-11-19 裁決）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-54 | park 到點：已 ack ⇒ skip(acked)（既有）；交接包已有 spawn 痕跡（`handoff._duplicate_refusals` 非空）⇒ `skip(spawned)`；`live_driver` ⇒ skip（既有）；`procstop.live_windows_of(sid)` 非空 ⇒ 先走 REQ-WP-55 判斷，五條件全部成立就先關再 `claude -r`；不成立就不開第二個同 sid 視窗，改依 REQ-WP-57 重試。任何情形都不得讓同一個 sid 同時有兩個 claude 行程。（r4）「先關再開」只適用 `park.fire_route`＝RESUME；FIRE_SPAWN（帶交接包開新 sid）不適用，到點只做 skip 判斷後照常 spawn，舊窗由新 session `handoff --ack` 走跨 sid 路徑關閉；同 sid 有活著的 `entrypoint=sdk-cli` 行程 ⇒ 視同 `live_driver` skip；否決成立 ⇒ `skip(kept_by_user)`（REQ-WP-98） | §7.1 | A3 |
| REQ-WP-55 | `oldwin.eligible()`（純函式）五條件全部成立才回 true：（r4）先查否決檔，存在即 false（`kept_by_user`）；①登記檔 `sessionId`＝舊 sid 且 `procStart` 與 GetProcessTimes 全等（不退用 CIM 容差），且 `entrypoint`＝`cli`（缺欄或其他值 ⇒ 不是關閉目標；此欄只用來排除目標、不用來判活）；②（r4 改寫）登記檔 `status` 欄存在且＝`idle`（缺欄或值不在 `{idle, busy}` ⇒ 不成立）、名冊中舊 sid 沒有 running 的背景子代理、且舊 sid 逐字稿中沒有 running 的非保溫背景 shell（`run_in_background` 呼叫扣掉完成／killed 通知後，命令列不符 `WATCH_CMD_RE`／`KEEPWARM_CMD_RE` 者，例：runlong、ci_wait）；③舊 sid 逐字稿最後一筆真人 user 記錄距今 > `AUTOSDD_OLDWIN_QUIET_MINUTES`（出廠 5；真人分類沿用 `forward.py` 的同一函式）；④跨 sid：交接包有 `.ack`，且新 sid 逐字稿至少有一筆 assistant 記錄；同 sid（park）：關閉後 `claude -r` 在限時內寫出新記錄（事後驗證）；⑤`sys.platform == "win32"`。回傳值逐條附證據 | §7.1 | A3 |
| REQ-WP-56 | 關閉程序：先寫 `oldwin_close_intent` 痕跡（pid、`procStart`、舊／新 sid、五條件證據、子孫清單）→ 開 handle 並在 handle 上重驗建立時間 → Toolhelp32 列子孫，只收建立時間 ≥ 父行程者，逐一開 handle 驗證 →（r4）**TOCTOU 重驗**：第一個 `TerminateProcess` 之前重讀登記檔（`status` 仍 `idle`、`procStart` 未變）、逐字稿尾段（無新真人 user 記錄、無新 `run_in_background`）與否決檔，任一變了即中止寫 `oldwin_close_refused(reason=toctou_<項>)` 並計一次重試；重驗後只剩 `TerminateProcess` 呼叫（≤1 秒）→ 由葉往根 `TerminateProcess`，最後砍 claude 本體 → 5 秒內確認不在 → 寫 `oldwin_closed`／`oldwin_close_failed`。防護：映像名屬 `{claude.exe, node.exe}`、目標不是呼叫者或其祖先、跨 sid 時目標 `sessionId` ≠ 呼叫者 sid、登記檔不存在一律不關；任一不成立寫 `oldwin_close_refused` 並中止。主控台宿主不主動砍。（r4）設計取捨寫入關閉出聲：舊窗輸入框中未送出的文字不會保留（條件 ③ 與 TOCTOU 重驗降低風險，`留：` 與關閉開關可完全避免） | §7.1 | A3 |
| REQ-WP-57 | （r4 統一）條件 ②或③ 不成立、或 TOCTOU 重驗中止 ⇒ 重試，**每個交接包至多 3 次**（所有範圍同一數字），每次否決與五條件全部重判。跨 sid（`--spawn`、forward、park FIRE_SPAWN）：登記一次性重試排程 `AutoSDD_OldWinClose_<舊 sid 8 碼>_<HHmm>`（觸發＝③最早成立時刻＋1 分；②或 TOCTOU 不成立時＝現在＋quiet 分鐘），憑證＝排程器自報 NextRunTime，回讀不到即 rc≠0。同 sid（park RESUME）：park 把自己的到點排程重排到同一觸發時刻，一次重排計一次重試。3 次後放棄、留痕：跨 sid 由新 session 出聲「舊窗保留（原因）」，park RESUME 寫 failed handback。條件①不成立或否決成立 ⇒ 不關、不重試、只留痕 | §7.1 | A3 |
| REQ-WP-58 | 出聲與開關：ack 當下關閉時，`handoff --ack` 輸出印「已關閉舊視窗 pid=…（sid …）」；其他時點關閉時，寫 `trace_dir()/oldwin/<新 sid>.notice.jsonl`，新 session 在 SessionStart 簡報、`sessionctl_guard` 的 UserPromptSubmit 與 Stop `systemMessage` 擇先出聲一次並標已讀（不新增 hook 註冊）。`AUTOSDD_OLDWIN_AUTOCLOSE_OFF=1`、`AUTOSDD_SESSION_SWITCH_MODE`≠`auto`、`AUTOSDD_UNATTENDED`、非 Windows ⇒ 只提醒（SessionStart 與 `sessionctl status` 印舊窗 pid），不關。範圍＝`--spawn` 後、park 同 sid 續跑、forward 轉送後的舊窗；forward 判準不變，定位改為「關閉前與不關時的安全網」 | §7.1 | A3、A5 |
| REQ-WP-59 | `handoff._duplicate_refusals` 判 spawn 痕跡 pid 是否活著，改用 D-8 身分比對（pid＋建立時間對痕跡 `at`），pid 被重用時不誤拒 | §7.1 同型洞表 | A3 |
| REQ-WP-98 | （r4，D-17）`留：` 否決：自動關閉可能作用的交接包所屬 sid 的視窗收到以 `留：`（全形或半形冒號）開頭的提示 ⇒ `oldwin.record_keep_veto` 寫 `trace_dir()/oldwin/veto/<交接包 stem>.json` 與 `oldwin_keep_veto` 事件；名下無交接包 ⇒ 不寫。否決永久、只綁該交接包、程式與 `--sweep` 都不刪；`eligible()` 先查否決；重試排程觸發見否決 ⇒ 刪除自己、不再登記、新 session 出聲一次；park RESUME 見否決 ⇒ `skip(kept_by_user)`、不 `claude -r`、不重試、寫 handback | §7.1〈否決〉 | A3 |
| REQ-WP-101 | （r4）`sessionctl status` 排程區列出 `AutoSDD_OldWinClose_*`（NextRunTime、LastRunTime、`pending`／`stale`）；回收：重試行程結束時刪自己（`finally`）、登記新重試前刪同舊 sid 前綴的既有工作、`handoff --ack` 與 `oldwin --retry` 啟動時行程內清除 `stale`、`python tools/sessionctl.py oldwin --sweep` 手跑入口（各期收尾窗口附末行）；沙盒前綴讀 `trace_dir()/oldwin/task_prefix` | §7.1〈現查與回收〉 | A3 |

### 1.6 E2E 缺口補件（期 A，DES §8；SA §3）
| REQ | 內容 | 案例 | WP |
|---|---|---|---|
| REQ-WP-45 | 保溫真的保住快取（E2E-SS-04） | RV-KW8（long） | A6 |
| REQ-WP-46 | 閒置 3 小時每 45 分輕觸，快取持續命中、無壓縮（V-SS1） | RV-KW9（long） | A6 |
| REQ-WP-47 | §8 列 3 陳舊 `index.lock` 的 Windows `tasklist` 分支 | RV-IL1 | A6 |
| REQ-WP-48 | handoff `--spawn` 新視窗真的讀交接包（RV-H3 信任框限制） | RV-H6 | A6 |
| REQ-WP-49 | 無人 print 模式背景上限（ADR §2.12） | RV-PB1 | A6 |
| REQ-WP-50 | 網頁讀取不進派發帳（ADR §2.16） | RV-WB1 | A6 |
| REQ-WP-51 | park RESUME 真開 `claude -r` 並續寫原逐字稿（V-SS5） | RV-PR3 | A6 |
| REQ-WP-52 | Stop／PreToolUse 推回訊息送達 harness（V-SS4／V-PK4／V5／V-W2／V-C2／V-F1 的機驗半） | RV-L3 | A6 |
| REQ-WP-53 | 從未跑過的 long 案例 RV-LW3、RV-W6 由 OIR 驅動，跑完且結果帳有 PASS 列（r3：只有 `drive` 憑證不算） | 既有案例 | A8 |

### 1.7 AutoClaude 無人舵手（期 B，DES §9）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-60 | 前置（r2 統一：舵手不需要 PG）：必要條件＝根層 `.venv` import 引擎、`--help` rc 0、`MINIMAX_API_KEY` 鍵存在（不印值）；任一不成立 ⇒ `openitems helm-check` rc 2 並列缺件。alembic 在 head 與 `autoclaude_pg` healthy 只在 `storage.mode`≠`yaml_only` 時升為必要條件，出廠 `yaml_only` 下只印成資訊列、不影響 rc | §0.4、§9.3-1 | B1 |
| REQ-WP-61 | 舵手 checkpoint 走 yaml、目錄 `~/.autosdd/openitems/checkpoints/`；不需要 PG 也能續跑單一 OI | §9.2、§9.3-2 | B1 |
| REQ-WP-62 | H9：AutoClaude 測試不寫入 `AutoClaude/checkpoints/`；回歸鎖比對跑前跑後檔數 | §9.3-4 | B1 |
| REQ-WP-63 | `openitems/helm.py` 由 OI 生成 playbook（`global_goal`、`evaluator_command`＝`openitems check --id`、steps） | §9.2 | B2 |
| REQ-WP-64 | `OPENITEMS_HELM=autoclaude` 時 `run-driver` 委派引擎；引擎 evaluator rc 0 才記 pass；引擎 escalation ⇒ attempt fail | §9.2 | B2 |
| REQ-WP-65 | 引擎啟動前與每一步前過讓路判準；互動 session 出現 ⇒ 收尾、記 deferred | §9.2 | B2 |
| REQ-WP-66 | 預設翻轉：DRY_RUN 一次 rc 0 後，連續 3 次真跑成功（帳本可數）才把 `env.shared` 的 `OPENITEMS_HELM` 改 `autoclaude`；`openitems helm-status` 印資格 | §0.3 D-10 | B4 |

### 1.8 PRD 與文件（期 C）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-70 | PRD 修憲 A-1～A-10 逐字落款；（r2）PRD 既有列一字不動：v2.1.22 修訂表列 QA 座標（PRD:27）與 §16.2 A47／A48 兩列（PRD:2696、:2720）的陳舊字面只在 v2.1.23 修訂表列內追加註記（A-1，N1 判例 PRD:2764）；§16.6 v2.1.22 列（PRD:2787）只在結案格末尾以 `<br>` 追加一行註記（A-10，PRD:2776） | 附錄 A | C1 |
| REQ-WP-71 | PRD §16.6 補登 8 族（A-11），每列依據欄引 ADR 節號＋RealVerify 帳列 | 附錄 A-11 | C1 |
| REQ-WP-72 | 文件陳舊清理（非 PRD）：DEF-200-594／596／597 狀態、ADR-XPLAT-004:1064、TCS-Park:4／223／224、根 CLAUDE.md:88／149／179、TCS-SS:45 `hold_set`；（r2）PRD 的 A47／A48 列與 PRD:27 不在本項，改由 REQ-WP-70 以追加註記處理 | §11 C2 | C2 |
| REQ-WP-73 | long-runner G3（V-T1～T3）依設計退役註記（D-6） | §0.3 D-6 | C2 |
| REQ-WP-74 | 根 CLAUDE.md：〈收尾常態規則〉加第七類停（宣告式完成）、機械守衛總表 `check_pending_handoff` 列補完成閘、速查表加 `openitems` | §11 C3 | C3 |
| REQ-WP-75 | ADR-XPLAT-004 §2.20 工作推進軸 | §11 C3 | C3 |
| REQ-WP-76 | （r3 改寫，DES D-12）§11.1（6h 零 token）、§11.8（24h／≥4 reset）不再等自然事件，改由驅動器跑 soak 案例 RV-SK1、RV-SK2（REQ-WP-87、88）並以 `auto` 列承接；PASS 帳列秒數須 ≥ 各自 `MIN_WALL_SECONDS` | §8-5 | A8 |
| REQ-WP-77 | V-K1 退役（keepwarm 取代）、V-K3 併入 M-K2；（r3 改寫）V-K2 改由 RV-K2B（REQ-WP-89）以 `auto` 列承接，不再等 7 天自然事件 | §8-5 | A8、C2 |
| REQ-WP-78 | §13 法務檢核＝human 列、A7 無人 commit／push＝k1 列；兩者進人工清單，不阻斷完成閘 | §5 | A8 |
| REQ-WP-79 | RV-KW6／KW7（R216 UX 棒的 DEF-200-622／623）若 UX 棒收尾時未入帳 ⇒ A8 開 auto 列並驅動 | §10 | A8 |

### 1.9 PRD 全功能 E2E 對照表與缺口案例（r3；掌舵者 2026-11-19 結案判準；DES §15、§8-2、§8-5）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-WP-80 | 母體 `docs/06_quality/RealVerify_Protocol/prd_population.json`：SA 矩陣 100 條＋本檔全部 REQ-WP，每條 `id`、`prd`、`class ∈ {normal, decision_retired, human}`、`e2e`（≥1 個案例 id）、`why`；非 `normal` 只准 `coverage_params.json` 白名單（C02、C14、A53、A54），且必附裁決座標與理由（§10.2） | §15.1 | E1 |
| REQ-WP-81 | 產生器 `python tools/realverify.py coverage --write` 產出 `docs/06_quality/PRD_E2E_Coverage_Table.md`：欄位＝條目、PRD 座標、E2E id、最近一次 PASS 帳列（時間＋選取）、最近一次結果、狀態；檔頭標「程式產生、勿手改」；同輸入逐位元組相同；`--check` 比對產物新鮮度 | §15.4 | E1 |
| REQ-WP-82 | （r4 改寫，審查 P2-2）帳列判讀：帳列只對第 8 欄「執行案例」**列出的 id** 有效；結果 pass 且 id 不在失敗案例欄 ⇒ PASS，在 ⇒ fail；舊 7 欄帳列只在「選取」恰為單一案例 id 時對該 id 有效，`family=…`／`all` 舊列一律不算；最近一次結果取最晚有效帳列。不符則 PASS 不算：long／soak 秒數 ≥ `MIN_WALL_SECONDS`；long／soak／observe 須與 OIR 對帳（`attempt(pass)` 的 `evidence` 引此帳列，同 `drive_seq` 的 `start.ts` ≤ 帳列時間−秒數，`attempt.ts − start.ts ≥ MIN_WALL_SECONDS`；observe 另須帳列時間 ≥ `due`）；證據欄含該案例全部 `ASSERTS` 鍵 | §15.4 | E1 |
| REQ-WP-83 | CI 鎖 `tools/tests/test_realverify_prd_coverage.py`（零容忍）：(a) PRD §16.2 表列、PRD:2690 ✅ ID 清單、§16.6 各列、TCS-SessionSwitch REQ-SS、本檔 REQ-WP 解析出的條目 ⊆ 母體鍵，新增 PRD 條目沒有 E2E 就紅；(b) `normal` 條目 `e2e` 非空且 id 皆在 `cases.json`；(c) 非 `normal` 只准白名單；(d) `coverage --check` 綠；(e) 母體改指既有案例時，該案例 `refs` 必含此條目的 PRD 座標；（r4）(f) 案例 `CARRIER`／`ASSERTS` 與 §10.3 附錄逐列相同（REQ-WP-100）；(g)(h) `MIN_WALL_SECONDS` 兩道鎖（REQ-WP-99） | §15.2、§15.4、§15.5 | E1 |
| REQ-WP-84 | PASS 債棘輪：`coverage_params.json` 的 `pass_debt`＝目前沒有 PASS 的 `normal` 條目；測試要求實測集合 ⊆ `pass_debt`（只縮不增），重釘只准收尾單人窗口 | §15.4 | E1 |
| REQ-WP-85 | R217 結案＝`realverify coverage --require-pass` rc 0：全部 `normal` 條目的每個 E2E 最近一次結果為 PASS 且符合 REQ-WP-82 的條件，`pass_debt` 為空；OIR `driven`／`escalated` 不算；不符 ⇒ rc 1 並列出條目 | §15.4 | E1 |
| REQ-WP-86 | 本檔每個 E2E-WP-xx 都是一個 RealVerify 案例：已點名者沿用 id，其餘為 `RV-WPxx`（家族 `workprogress`）；`cases.json` 的 `refs` 必含 `E2E-WP-xx` | §15.3 | A6 |
| REQ-WP-87 | RV-SK1（soak）：§11.1 6 小時零 token，沙盒真哨兵巡邏跑滿 6 小時；巡邏 tick ≥ 6h÷巡邏間隔−1、沙盒 spawn 的 `claude` 行程數＝0、無付費探針痕跡；`MIN_WALL_SECONDS`＝21,600 | §8-5 | A6 |
| REQ-WP-88 | RV-SK2（soak）：§11.8 24 小時／4 次 reset，沙盒 session 每約 5 小時注入一筆真逐字稿格式的撞線記錄，真哨兵＋真 schtasks 在每次 reset 後 `claude -p -r --model haiku` 續跑；4 次都寫出新記錄、每次距 reset ≤ 一個巡邏間隔；`MIN_WALL_SECONDS`＝86,400 | §8-5 | A6 |
| REQ-WP-89 | RV-K2B：V-K2，以 `quota_policy` 既有門檻鍵使真實讀數落在等效 95～99% 帶；真 hook 出聲一次、寫出可重啟點任務書、同一 reset 窗不重複 | §8-5 | A6 |
| REQ-WP-90 | RV-OB4（E2E-SS-05，`due` 2026-12-02）、RV-OB5（V-PK5，`due` 2026-11-30）：observe 案例，到期跑 `waste_census --switch-metrics`／`--resume-metrics --since-days 14`，達標 PASS | §8-5 | A6、A8 |
| REQ-WP-91 | RV-UI1：畫面可見（V-SS4／V-PK4／V5／V-W2／V-C2／V-F1 畫面半）。沙盒預植 trust 開真互動視窗，觸發 Stop 推回與 `systemMessage`；用 `PrintWindow` 擷取視窗，再用 `Windows.Media.Ocr` 比對守衛字樣；OCR 元件不可用 ⇒ rc 2（環境缺件，不算綠） | §8-2 | A6 |
| REQ-WP-92 | RV-F4：forward 轉送開出的新視窗真的 Read 了 `forward-*.md`（新 sid 逐字稿可見），沿用 RV-F1 的轉送觸發手法 | §8-2 | A6 |
| REQ-WP-93 | RV-PP1：ADR §2.14 推送快層先行（SA D12）。repo 外 `git clone --local` 沙盒，故意放一個 ruff 紅檔，真跑 `tools/git-hooks/pre-push`；快層紅 ⇒ 慢層與子專案 leg 未啟動（log 無其起始字樣），rc≠0 | §8-2 | A6 |
| REQ-WP-94 | RV-BC1：PRD §6.1 啟動自檢不變式（SA A49）。真行程跑 `boot_self_check`，斷言各已機械化不變式的判定輸出；已知邊界（不變式 5、10）在輸出標為邊界、不判綠 | §8-2 | A6 |
| REQ-WP-95 | RV-SC3：REQ-SS-21 事件常數（SA C21）。對本機真逐字稿跑 `waste_census --switch-metrics`，輸出的事件名集合＝程式常數集合，且不含 `hold_set`；TCS-SessionSwitch:45 同步（REQ-WP-72） | §8-2 | A6、C2 |
| REQ-WP-96 | （r4 改寫）RV-PX01～49：PRD §16.2 ✅ 的 29 個矩陣 ID、無殘留 ✅ 的 17 列、§16.6 B01～B03 逐列一個 E2E，案例 id、載具、輸入、斷言鍵全部依 §10.3 附錄（49／49 已寫定）；只准附錄寫明的三處改指（A17→PX12、A19→PX13、A37→PX34）；附錄「載具前提」不成立時依附錄預定退路改載具並同 commit 改附錄 | §15.2 | A6 |
| REQ-WP-99 | （r4，D-16）結果帳第 8 欄「執行案例」由 `ledger.py` 寫入實際執行的 id（篩掉或未執行者以「略過：id(原因)」標於同欄末尾）；每個 long／soak 案例必須宣告 `MIN_WALL_SECONDS` 與 `DESIGNED_WAIT_SECONDS`，`MIN_WALL_SECONDS` 等於 `coverage_params.json` 的 `min_wall_seconds`、≥0.9×`DESIGNED_WAIT_SECONDS`、≥ 測試檔 `_MIN_WALL_FLOOR`；`_MIN_WALL_FLOOR` 不低於 git HEAD 版參數檔；案例執行把各段實際等待寫入證據，總和 <`DESIGNED_WAIT_SECONDS` ⇒ fail；執行器執行期比對模組值與參數檔，不等 ⇒ fail | §15.4 | E1 |
| REQ-WP-100 | （r4，D-15）空殼防線：§15.5 列舉的案例模組必須宣告 `CARRIER` 與 `ASSERTS`（≥1）；執行器在案例回 pass 但任一 `ASSERTS` 鍵未以 `ctx.evidence` 寫出非空值時改判 fail（`assert_missing:<鍵>`），證據以 `鍵=值` 入帳；CI 鎖 (f) 比對 §10.3 附錄與模組宣告逐列相同 | §15.5 | E1、A6 |
| REQ-WP-102 | （r4，D-18）對照表重產：`ledger.py` 追加帳列後行程內呼叫 `coverage.write()`（讀不到母體 ⇒ stderr 一行、帳列保留）；`run-driver` 第 7 步寫完 OIR 事件後跑 `realverify coverage --write`（逾時 60 秒，失敗只記 `coverage=failed`）；`driver_own_prefixes` 含產物 | §15.4、§5.1-7、§5.5 | E1、A2 |
| REQ-WP-97 | soak 通道：`KIND="soak"` 案例不取 `driver.lock`、不佔每窗名額，改取 `soak.lock`（同時至多 1 支，判活規則同 `driver.lock`） | §5.4-5 | A2 |

**REQ 計數：95**（1.1＝10、1.2＝11、1.3＝7、1.4＝7、1.5＝5、1.5b＝8、1.6＝9、1.7＝7、1.8＝10、1.9＝21）。r4 新增 REQ-WP-98～102，改寫 54～57、82、83、96。r2 新增 REQ-WP-08／09／19／26／36，改寫 03／17／32／33／35／41／60／70／72／76／77；r3 新增 REQ-WP-27／28／54～59／80～97，改寫 03／05／19／30／53／76／77。

## 2. PRD 追溯表（行號＝2026-11-19 HEAD）
| REQ | PRD 座標 | 關係 |
|---|---|---|
| 01～09、20～26 | §2 名詞表（157-173）、§11.3「完成任務」（2375-2379）、§16.1 邊界（2684）、§16.5（2774）、§16.6 v2.1.22 列（2787） | 補「完成」定義與工作推進軸；修憲 A-1、A-2、A-5、A-6、A-7、A-10 |
| 10～19 | §16.5 禁日曆觸發（2774）、§1.2 原則 3 雙軸／原則 5 失效即保守（135-140）、根 CLAUDE.md〈反「事後諸葛」取證規則〉 | 一次性驅動器＋排程器自報憑證＋扇出上界；observe 豁免條件見 A-6 |
| 30～36 | §1.2 原則 2（131-134）、v2.1.22 修訂表列（27） | 叫醒是預算化致動器；A-4、A-8 |
| 40～44 | §4.4.3（1061，已退役） | 名冊無條文 ⇒ A-7 第 7 款 |
| 45～53 | §16.6 v2.1.22 列 ⏸ 原因（2787） | 待驗收改由 OIR 承接（A-5、A-10） |
| 60～66 | §1.2 原則 1（128-130）、§4.5.7 偏離 2（1294-1304）、§15.2～§15.3（2480-2532） | 無人舵手入憲 A-3；偏離 2 陳舊 A-9 |
| 70～79 | §16.5 (i)（2770）、§16.6（2778-2787） | 修憲程序本身 |
| （r3）27、28 | 同 01～19 列 | 補完成定義的空窗、扇出上界的公平性；A-7 |
| （r3）54～59 | 無條文（名冊與視窗管理 PRD 零條文，SA §4.4）；ADR-XPLAT-004 §2.13.4-5、§2.17、§2.18 D3-4 | A-7 第 8 款 |
| （r3）80～97 | §16.2（2688-2720）、§16.6（2778-2787）、§11.1、§11.8、§6.1；掌舵者 2026-11-19 結案判準 | A-7 第 9 款、A-10 ✅ 條件 |
| （r4）98、101 | 無條文（同 54～59）；ADR-XPLAT-004 §2.18 D3-4（`留：` 契約） | A-7 第 8 款的細化 |
| （r4）99、100、102 | 掌舵者 2026-11-19 結案判準（long 案例由驅動器真的跑完、不得以已排程充當 PASS） | A-7 第 9 款 |

## 3. 驗收測試（AT；單元／整合，縫注入）
縫：`NOW`、`FS`（tmp 圍籬含 `trace_dir`）、`ENV`、`TR`（合成或截取逐字稿）、`SCH`（假排程後端，回傳指定 `NextRunTime`）、`PL`（hook payload）、`RUN`（假 runner）、`Q`（假 `--pace` 帶）。

| AT | REQ | 輸入 | 預期 |
|---|---|---|---|
| AT-WP-01 | 01 | 亂序事件、一行壞 JSON | fold 現態正確；`list` 末行 `bad=1` |
| AT-WP-02 | 02 | human 缺 `why_not_auto`／observe 缺 `due`／kind 不在四型 | 各 rc 2、帳本無新行 |
| AT-WP-03 | 03、20 | 夾具甲：回覆「沒有剩下要做的事」＋1 個 undriven；夾具乙：回覆「接下來要做 X」＋全 driven | 甲推回、乙不推（完成閘部分）；把回覆文字對調後判決不變 |
| AT-WP-04 | 03 | 觸發前（`now < at`）：`SCH` 快取「工作不存在」／存在／快取過期 | undriven／driven／driven |
| AT-WP-05 | 04 | 含標記的 FS 文件（帶 id、不帶 id、在 definers 內） | mapped／unmapped／不計 |
| AT-WP-06 | 05 | fail×2 | 第 2 次後 `escalated`，不再寫 `drive` |
| AT-WP-07 | 05 | deferred(interactive)×6 | `escalated`；`attempts` 仍 0 |
| AT-WP-08 | 06 | `source` 指向 `README.md` | rc 2 |
| AT-WP-09 | 07 | 兩執行緒同時 `open` 各 20 次 | 40 個 id 互不相同且連號 |
| AT-WP-10 | 10 | `SCH` 回空字串 `NextRunTime` | rc≠0、無 `drive` 事件、排程被撤 |
| AT-WP-11 | 11 | 已 closed 的 id | 自刪排程、rc 0、末行 `OPENITEMS_DRIVER=noop` |
| AT-WP-12 | 11 | `RUN` pass | `attempt(pass)`＋`close`，證據含帳列時間戳 |
| AT-WP-13 | 11 | `RUN` fail（n=1） | `attempt(fail)`＋新 `drive`（時刻＝now＋360 分） |
| AT-WP-14 | 12 | `TR` 顯示 3 分鐘前有主控記錄 | `deferred(interactive)`、attempts 不變 |
| AT-WP-15 | 13 | `Q`＝收斂帶、reset＝now＋40 分 | `deferred(quota)`、重排至 reset 後 |
| AT-WP-16 | 14 | observe `due`＝now；量測輸出符合／不符 `pass` | close／attempt fail |
| AT-WP-17 | 15 | 9 個 listed | 簡報印 7 項＋「另 2 項」；首次 Stop 附出聲一行、rc 0 |
| AT-WP-18 | 16 | k1 列 `close --by human` 證據為 AskUserQuestion 回答座標 | rc 2 |
| AT-WP-19 | 17 | 家族檔 commit 晚於最後 pass；已有 open 列 | 開 1 列；再跑不重開 |
| AT-WP-20 | 18 | `SCH` 列出 2 個 `AutoSDD_OpenItem_*` | `status` 排程區 2 列含 NextRunTime |
| AT-WP-21 | 20 | `stop_hook_active=true` | 放行 |
| AT-WP-22 | 20 | `AUTOSDD_UNATTENDED=1` | 放行 |
| AT-WP-23 | 20 | 本回合只用 Read／Grep 且 git 乾淨 | 放行 |
| AT-WP-24 | 21 | 三判準同時成立 | 單一推回訊息，段落次序 半路停工→散文交棒→完成閘 |
| AT-WP-25 | 22 | `background_tasks`＝[keepwarm shell running]＋回覆「接下來要做 X」＋狀態佐證 | 半路停工推回（修前放行） |
| AT-WP-26 | 22 | `background_tasks`＝[agent running, watch shell running] | 不判閒置 |
| AT-WP-27 | 24 | 完成閘推回後同回合保溫閘 | 不推「掛保溫」；`.gate` 存在 |
| AT-WP-28 | 25 | 帳本檔權限拒讀 | 放行＋stderr 一行 |
| AT-WP-29 | 08 | run-driver 起跑（auto 案例牆鐘 180 分；observe） | 先寫 `start`、`budget_minutes`＝195／30，`drive_seq` 指向最後一筆 `drive` |
| AT-WP-30 | 30 | 合成名冊：全部交卷 | watch 不退出；轉保溫模式旗標 |
| AT-WP-31 | 30 | 交卷後到保溫點 | 退出 `WATCH_VERDICT=keepwarm`、rc 0 |
| AT-WP-32 | 31 | holder 檔指向活 pid＋相符建立時間／活 pid 不符建立時間／死 pid | skip／接手／接手 |
| AT-WP-33 | 32 | `pings`＝n*−1，watch keepwarm 事件一次後 keepwarm 指令 | 指令印 `cap` |
| AT-WP-34 | 33 | 截取 31ea79d4 逐字稿片段（E3 時段） | M-WB2＝8（重現 ARC E3）；M-WB1 每次 ≥2 |
| AT-WP-35 | 31、§10 | `holder_running` 分支 | rc 0（與 DEF-200-622 一致） |
| AT-WP-36 | 35 | 合成逐字稿 | `--pace-metrics`、`--replay-pace-floor` 輸出欄位齊、rc 0 |
| AT-WP-37 | 36 | 全部交卷後到保溫點：(a) `pings`＝n*；(b) 保溫不適用（`AUTOSDD_UNATTENDED=1`）；(c) `pings`＜n* 且適用；另 (d) 交卷後尚未到保溫點 | (a) `WATCH_VERDICT=cap`、(b) `idle`、(c) `keepwarm`，皆 rc 0 且行程結束；(d) 不退出 |
| AT-WP-40 | 40 | 主逐字稿 killed 行距檔尾 300KB | 該代理被排除；第二次呼叫只讀新增位元組（讀取量斷言） |
| AT-WP-41 | 40 | 逐字稿被截短 | 從頭重掃，結果正確 |
| AT-WP-42 | 41 | 命令列 `claude "讀 …\05d1b770-….md"`＋登記檔 sessionId＝31ea79d4 | owner＝31ea79d4 |
| AT-WP-43 | 41 | 無登記檔；命令列 `claude -r <uuid>`／路徑含 uuid | uuid／空字串 |
| AT-WP-44 | 41 | 登記檔 `procStart` 與行程建立時間不符（pid 重用） | 不採信 |
| AT-WP-45 | 42 | quiet 代理、擁有者已 `.ack` | 殘局 |
| AT-WP-46 | 43 | 殘局最後記錄 25h 前 | 寫 retired 一行；`--all` 顯示計數 |
| AT-WP-47 | 44 | 假 rmtree 失敗 | cleanup 回報失敗、案例 fail（不得 pass） |
| AT-WP-48 | 44 | sweep：沙盒根存在／不存在／登記檔 cwd 指向 | 留／刪／留 |
| AT-WP-50 | 03 | 觸發後（Windows 一次性排程，`SCH` 回 `NextRunTime` 空字串且工作仍在）：(a) `at＋14 分`無 start；(b) `at＋16 分`無 start；(c) 有 start、`budget`＝30、start 後 20 分無 attempt；(d) 同 (c) 但 start 後 31 分（模擬 run-driver 崩潰，`pid` 已死） | (a) driven、(b) undriven、(c) driven、(d) undriven；判決不因 `NextRunTime` 為空而改變 |
| AT-WP-51 | 03 | macOS 後端（`SCH` 只回 launchctl rc、無 `NextRunTime` 欄）跑 AT-WP-04、AT-WP-50 全部變體 | 判決與 Windows 逐格相同 |
| AT-WP-52 | 17 | 家族 F：(a) 有 escalated 列、原始檔最後 commit 早於 escalate；(b) 同 (a) 但之後有新 commit 動 `SOURCES`；(c) listed 列＋無新 commit；(d) (b) 開列後連跑 `scan --stale-pass` 3 次 | (a) 不開；(b) 開 1 列；(c) 不開；(d) 仍只有 1 列 |
| AT-WP-53 | 19 | `driver.lock` 由活 pid＋相符建立時間持有且未逾預算／持有者 pid 死／持有者逾 `budget_minutes` | deferred(busy) 且 attempts、deferrals 皆不變／接手／接手 |
| AT-WP-54 | 19 | `window_runs.jsonl` 當窗已 2 筆；`Q` 回 reset＝now＋50 分／reset 量不到 | deferred(window_cap)、重排 ≥ reset／重排 `retry_backoff_minutes`；滾動區間＝`cap_window_minutes` |
| AT-WP-55 | 19 | 30 列 auto 同時 deferred(interactive) 到同一期望時刻後重排 | 30 個 `at` 兩兩相距 ≥`stagger_minutes` |
| AT-WP-56 | 19 | `Q`：短窗正常但週軸收斂帶／可派數 0／`--pace` 讀不到（rc≠0） | 三者皆 deferred(quota)，不進第 5 步 |
| AT-WP-57 | 26 | 50 列 driven（觸發前 25、觸發後 25）＋快取；`RUN`／`SCH` 計數子行程 | 完成閘判準期間子行程 0 次、耗時 ≤2 秒；`list --verify` 列舉呼叫恰 1 次 |
| AT-WP-58 | 09 | `git status` 行：(a) 只有 OIR 帳＋RealVerify 帳；(b) 加一個其他檔；(c) `params.json` 讀不到時同 (a)；(d) SI `dirty_paths` 遇 (a) | (a) spawn 不因髒拒絕；(b) 拒絕；(c) 拒絕；(d) 回空；且 `sched.OWN_PREFIXES` 不含兩本帳 |
| AT-WP-59 | 41 | (a) 登記檔 `procStart` 與 GetProcessTimes 全等；(b) GetProcessTimes 不可用、CIM 差 5；(c) CIM 差 10,000,000；(d) 平台非 Windows；(e) 同 sid 兩個登記檔、其一 pid 已死 | (a) 採信；(b) 採信；(c) 不採信；(d) 跳過登記檔走旗標形態；(e) 判活 |
| AT-WP-60 | 60 | (a) 假 env 缺 `MINIMAX_API_KEY`；(b) `storage.mode`＝`yaml_only` 且假 docker 回容器不在、alembic 不在 head；(c) `storage.mode`＝`pg` 同 (b) | (a) `helm-check` rc 2，訊息只列鍵名；(b) rc 0、兩項印成資訊列；(c) rc 2 並列兩項缺件 |
| AT-WP-61 | 61 | storage＝yaml_only | 生成 playbook 的 checkpoint 目錄在 `~/.autosdd/openitems/checkpoints/` |
| AT-WP-62 | 63 | 一個 auto OI | playbook 含 `global_goal`、`evaluator_command`＝`python tools/openitems.py check --id <id>` |
| AT-WP-63 | 64 | `RUN` 引擎 rc 0 但 evaluator rc 1 | attempt fail（LLM 宣告不算） |
| AT-WP-64 | 65 | 引擎第 2 步前 `TR` 出現互動記錄 | 收尾、deferred |
| AT-WP-65 | 66 | 帳本：DRY_RUN pass＋真跑 pass,pass,fail,pass,pass,pass | `helm-status` 資格＝是（最後連續 3 次） |

| AT-WP-66 | 27 | （r3）(a) `attempt(fail, n=1)` 後無 `drive`，`now`＝a.ts＋10 分；(b) 同 (a) 但＋16 分；(c) `SCH` 對重排回空 `NextRunTime`（重排時憑證回讀失敗）後跑完 run-driver，`now`＋16 分；(d) `attempt(pass)` 無 `close`＋16 分；(e) `attempt(fail, n=2)` 無 `escalate`＋16 分；(f) `attempt(deferred)` 後有新 `drive` 且觸發前 | (a) driven；(b)～(e) undriven，且 (c) 的末行含 `redrive=failed`、rc 0、帳本無新 `drive`；(f) driven |
| AT-WP-67 | 28 | （r3）30 列 auto 同時開，`max_runs_per_window`＝2，`RUN` 一律 pass、`Q` 正常、依序模擬 15 個窗 | 每窗恰 2 列執行且為排隊鍵最小者；15 窗後 30 列全 closed；沒有任何一列 escalated；`deferrals` 全為 0 |
| AT-WP-68 | 28 | （r3）本窗已有 1 列排隊（舊）、名額剩 1；一列新開的列先觸發 | 新列 deferred(window_cap)；舊列拿到名額 |
| AT-WP-69 | 05、28 | （r3）同一列依序 deferred：quota×10、window_cap×10、busy×10，再 interactive×6 | 前 30 次後 `deferrals`＝0、未 escalate；interactive 第 6 次後 escalated |
| AT-WP-70 | 54 | （r3）park 到點：交接包已有 spawn 痕跡（未 ack） | `skip(spawned)`；不呼叫 `claude -r` |
| AT-WP-71 | 54、55 | （r3）park 到點：`live_windows_of` 回 1 個 pid，五條件 (a) 全成立；(b) ②不成立（status＝busy） | (a) 先呼叫關閉、後呼叫 resume（呼叫順序斷言）；(b) 不關、不 resume，登記重試排程 |
| AT-WP-72 | 55 | （r3）條件逐條翻轉：①procStart 差 1（100ns）；①只有 CIM 可用；②名冊有 running 子代理；③最後真人記錄 4 分前／最後一筆是 `<task-notification>`（真人記錄 6 分前）；④無 `.ack`／有 `.ack` 但新 sid 無 assistant 記錄；⑤平台 darwin | 每一格 false 並指名不成立的條件；③第二格為 true（機器注入不算真人） |
| AT-WP-73 | 56 | （r3）假行程樹：父＋2 子＋1 個 parent pid 相同但建立時間早於父的行程；另一變體在驗證後、終止前把父 pid 換成另一個行程（模擬 pid 重用） | 只砍父與 2 子、由葉往根；早於父者不動；pid 重用變體因 handle 驗證失敗而中止並寫 `oldwin_close_refused`；`oldwin_close_intent` 一定先於任何終止動作寫入 |
| AT-WP-74 | 56 | （r3）防護：映像名 `python.exe`／目標是呼叫者祖先／目標 `sessionId`＝呼叫者 sid／登記檔不存在 | 全部不關並寫 `oldwin_close_refused` |
| AT-WP-75 | 57 | （r3）③不成立（最後真人記錄 2 分前）；第 3 次重試仍不成立 | 重試排程觸發時刻＝最後真人記錄＋5 分＋1 分、憑證非空；`SCH` 回空 ⇒ rc≠0；第 3 次後不再登記、寫放棄痕跡 |
| AT-WP-76 | 58 | （r3）`AUTOSDD_OLDWIN_AUTOCLOSE_OFF=1`／模式 notify／`AUTOSDD_UNATTENDED=1`／非 Windows | 皆不關、只產生提醒文字；park 同 sid 情形不開第二個視窗 |
| AT-WP-77 | 58 | （r3）notice 檔有 1 筆未讀；先後觸發 SessionStart 與 Stop | 只出聲一次（SessionStart），之後標已讀；出聲含 pid |
| AT-WP-78 | 59 | （r3）spawn 痕跡 pid 對應的現行行程建立時間晚於痕跡 `at`（pid 重用），痕跡已逾 `SPAWN_DEDUP_SECONDS` | 不拒絕 spawn；pid 與建立時間相符時照舊拒絕 |
| AT-WP-79 | 80、83 | （r3）母體缺 PRD §16.6 新增的一列 | 鎖紅並指名該列 |
| AT-WP-80 | 83 | （r3）`normal` 條目 `e2e` 為空／id 不在 `cases.json`／非白名單條目標 `human`／改指的既有案例 `refs` 不含該 PRD 座標 | 各自紅並指名 |
| AT-WP-81 | 82 | （r3）合成帳本：family pass 列；同家族後一列 fail 且失敗案例含 X；long 案例 PASS 秒數 < `MIN_WALL_SECONDS`；observe PASS 帳列時間早於 `due` | 家族其他案例 PASS；X 最近一次＝fail；後兩者不算 PASS |
| AT-WP-82 | 81 | （r3）同一輸入跑兩次 `--write`；手改產物一字後 `--check` | 兩次逐位元組相同；`--check` 紅 |
| AT-WP-83 | 84 | （r3）`pass_debt` 外的條目失去 PASS（最近一次轉 fail） | 鎖紅；`pass_debt` 內條目轉 PASS 時不紅 |
| AT-WP-84 | 85 | （r3）全部 PASS 但一條的最近一次為 fail／全部 PASS 且 `pass_debt` 空 | rc 1 並列該條／rc 0 |
| AT-WP-85 | 98 | （r4）(a) 已 spawn 交接包的 sid 收到 `留：繼續` 提示；(b) 名下無交接包的 sid 收到 `留：…`；(c) (a) 之後五條件全成立時呼叫 `eligible()`；(d) (a) 之後重試排程觸發；(e) park RESUME 到點、該 park 交接包有否決；(f) 否決後該 sid 又有新交接包 | (a) 寫否決檔與 `oldwin_keep_veto`；(b) 不寫任何檔；(c) false、理由 `kept_by_user`；(d) 不關、刪除自己的排程、不再登記、寫一筆 notice；(e) `skip(kept_by_user)`、不呼叫 resume、不重排；(f) 新交接包不受舊否決影響 |
| AT-WP-86 | 56 | （r4）TOCTOU：五條件判斷通過後、第一個 `TerminateProcess` 前注入變化：登記檔 `status` 改 `busy`／逐字稿追加一筆真人 user 記錄／逐字稿追加一筆 `run_in_background`／否決檔出現 | 四格皆中止、`TerminateProcess` 呼叫 0 次、寫 `oldwin_close_refused(reason=toctou_<項>)`、重試計數 +1；無變化的對照組照常關閉 |
| AT-WP-87 | 55 | （r4）條件 ② 與目標排除：(a) 登記檔無 `status` 欄；(b) `status`＝`waiting`（不認得）；(c) `status`＝`idle`＋逐字稿有 running 的 `sessionctl runlong` 背景 shell；(d) 同 (c) 但只有 running 的 keepwarm 與 watch shell；(e) `entrypoint`＝`sdk-cli`；(f) `entrypoint` 缺欄 | (a)(b)(c)(e)(f) false 並指名條件；(d) ② 成立 |
| AT-WP-88 | 54、57 | （r4）(a) park 到點 `fire_route`＝FIRE_SPAWN 且同 sid 舊窗活著；(b) park RESUME、② 連續不成立 4 次；(c) 跨 sid、③ 連續不成立 4 次；(d) 同 sid 有活著的 `sdk-cli` 行程 | (a) 不呼叫關閉、照常 spawn 新 sid；(b) park 重排恰 3 次、第 4 次到點寫 failed handback、不再重排；(c) 重試排程恰登記 3 次、之後只出聲；(d) skip、不關不開 |
| AT-WP-89 | 101 | （r4）`SCH` 列出 3 個 `AutoSDD_OldWinClose_*`：一個待觸發、一個已執行且 NextRunTime 空、一個對應已否決交接包；另為同一舊 sid 再登記一個重試 | `status` 排程區 3 列、狀態 pending／stale／stale；`oldwin --sweep` 刪 2 留 1；登記新重試前同前綴舊工作被刪、最後該前綴恰 1 個；否決檔不被刪 |
| AT-WP-90 | 82、99 | （r4）合成帳本：(a) 新格式 `family=F` pass 列「執行案例」＝A（B 為 long、標「略過：B(long)」）；(b) 舊 7 欄 `family=F` pass 列；(c) 舊 7 欄「選取」＝`RV-B` pass 列；(d) 新格式列執行案例含 B 但失敗案例欄含 B | (a) A＝PASS、B 不受影響；(b) 對 A、B 都不算；(c) 對 RV-B 有效（但 B 為 long 仍須 OIR 對帳，見 AT-WP-92）；(d) B＝fail |
| AT-WP-91 | 99 | （r4）參數與宣告：(a) long 案例模組缺 `MIN_WALL_SECONDS`；(b) 模組值≠`coverage_params.json`；(c) 值 < 0.9×`DESIGNED_WAIT_SECONDS`；(d) 參數檔值 < `_MIN_WALL_FLOOR`；(e) `_MIN_WALL_FLOOR` 某鍵 < git HEAD 版參數檔；(f) 參數檔多一個非 long 案例的鍵；(g) 案例執行證據的等待總和 < `DESIGNED_WAIT_SECONDS` | (a)～(f) 鎖各自紅並指名；(g) 執行器判 fail |
| AT-WP-92 | 82、99 | （r4）long 案例 PASS 帳列，OIR：(a) 無對應 `attempt`；(b) 有 `attempt(pass)` 引此列、`start` 到 `attempt` 跨度 < MIN_WALL；(c) 跨度 ≥ MIN_WALL 但 `start.ts` 晚於帳列時間−秒數；(d) 全符合；(e) observe 案例全符合但帳列時間 < `due` | (a)(b)(c)(e) 不算 PASS；(d) PASS |
| AT-WP-93 | 100 | （r4）`RUN` 案例宣告 `ASSERTS=("k1","k2")`：(a) 回 pass、只寫 k1；(b) 回 pass、k2 值為空字串；(c) 兩鍵皆寫；(d) 模組未宣告 `ASSERTS`（屬 §15.5 範圍） | (a)(b) 帳列 fail、失敗原因 `assert_missing:k2`；(c) pass 且證據欄含 `k1=…`、`k2=…`；(d) 鎖紅 |
| AT-WP-94 | 83、100 | （r4）以 §10.3 附錄的解析結果比對：(a) 模組 `ASSERTS` 少一鍵；(b) 多一鍵；(c) `CARRIER` 不同；(d) 附錄列在 `cases.json` 不存在；(e) 改指列（A17）指向的案例 `refs` 缺 §8-8 | 各自紅並指名列與案例 |
| AT-WP-95 | 102 | （r4）(a) `ledger.py` 追加一列後立即 `coverage --check`；(b) 母體檔不存在時追加；(c) `run-driver` 寫 `attempt(pass)` 後；(d) `coverage --write` 子行程逾時 | (a) 綠、子行程 0 個；(b) 帳列已寫、stderr 一行、rc 不變；(c) 產物反映該 `attempt`；(d) 末行含 `coverage=failed`、判決不變、rc 0 |

**AT 計數：92**（01～29＝29、30～37＝8、40～48＝9、50～59＝10、60～65＝6、66～84＝19、85～95＝11）。r2 新增 AT-WP-29／37／50～59，改寫 04／60；r3 新增 AT-WP-66～84，改寫 07；r4 新增 AT-WP-85～95。

## 4. 真機 E2E（每個功能至少一個；載具與斷言）

共通：沙盒＝`realverify.sandbox.Sandbox`；模型＝haiku（除另註）；斷言失敗即案例 fail 入帳；結束斷言沙盒根與 `~/.claude/projects/<slug>` 不存在。

| E2E | REQ | 載具 | 斷言 |
|---|---|---|---|
| E2E-WP-01 | 04 | 真 repo：`python tools/openitems.py scan` | rc 0；末行格式；與 ARC E6（143 處／61 檔）對帳，差異逐條列出原因；A8 後 unmapped＝0 |
| E2E-WP-02 | 10、18 | 沙盒 OIR＋真 `drive`（Windows 真 schtasks） | `Get-ScheduledTask AutoSDD_OpenItem_*` 存在；`NextRunTime` 非空且等於 `drive` 事件憑證；`sessionctl status` 排程區列出；撤銷後工作不存在 |
| E2E-WP-03 | 11、53、03、08 | 沙盒 OIR 一列 auto（check＝RV-L1）；真排程 now＋2 分觸發 `run-driver` | 執行中取樣一次：`Get-ScheduledTaskInfo` 的 `NextRunTime` 為空、`openitems list` 仍判 driven、帳本已有 `start`；結束後排程 LastTaskResult 0；RealVerify 帳新增 RV-L1 pass 列；OIR `close` 證據引該列；排程已自刪；log 末行 `OPENITEMS_DRIVER=pass` |
| E2E-WP-04 | 05、15 | 沙盒 auto 列 check＝必敗案例 RV-OI1；真排程兩次（重排間隔以 `params.json` 設 3 分） | 第 1 次 fail＋新 drive；第 2 次 `escalated`；之後真 `claude -p` 於沙盒的 SessionStart 簡報含該 id |
| E2E-WP-05 | 14 | observe 列 due＝now＋2 分，argv＝`waste_census --switch-metrics` 對沙盒夾具 | 真排程觸發；`close` 證據含量測輸出路徑 |
| E2E-WP-06 | 20～25 | 沙盒掛真 `check_pending_handoff.py`＋`sessionctl_guard.py`；真 `claude -p` 四變體：(a) 回覆宣告完成＋1 undriven＋背景 keepwarm shell；(b) 同 (a) 但項目已 drive；(c) 只讀回合；(d) 回覆「接下來要做 X」＋只有 keepwarm shell running | 逐字稿 Stop 推回：(a) 一次且含 OI id、第二次 Stop 放行、`.gate` 存在且無「掛保溫」推回；(b) 無；(c) 無；(d) 半路停工推回一次 |
| E2E-WP-07 | 40 | 真逐字稿重放：05d1b770 逐字稿複本放沙盒 projects 目錄，呼叫 roster API | ab573c773ef06f035 不列；第二次呼叫讀取量＜新增位元組＋1 行 |
| E2E-WP-08 | 41、42 | 沙盒起真 `claude -p --model haiku`（cwd＝沙盒；命令列含另一個 UUID 的路徑；提示要求以工具執行一次約 45 秒的等待，使行程存活夠久）在跑時呼叫 `sessionctl status`（沙盒 projects）。載具前提已現查（r2，2026-11-19 沙盒實跑一次 `claude -p --model haiku "ok"`，rc 0、5 秒）：執行期間出現 `~/.claude/sessions/<pid>.json`（`kind=interactive`、`entrypoint=sdk-cli`、`cwd`＝沙盒、`sessionId`＝該次新 sid），結束後該檔被移除 | 該 UUID 的擁有者不在 alive；真行程自己的 sid 由登記檔取得且判活；行程結束後同一 sid 不再判活；擁有者已 ack 的 quiet 代理顯示為殘局 |
| E2E-WP-09 | 44 | 真跑 RV-L1 後；另放 2 個孤兒 slug 目錄與 1 個有登記檔 cwd 指向的目錄跑 `realverify sweep` | RV-L1 結束後其 slug 目錄不存在；sweep 刪 2 留 1；本機現存 5 個孤兒（SA §4.3）於收尾時被 sweep 清除並記錄名單 |
| E2E-WP-10 | 45 | RV-KW8（long）：真 `claude -p --model haiku` 建 session（上下文 ≥4,096）；t0＋45 分 `-r` 輕觸；t0＋100 分 `-r`；對照組不輕觸 t0＋70 分 | 第三次 `cache_read ≥ 0.9×` 前一回合上下文；對照 `< 0.1×`；依 usage 的 `ephemeral_1h_input_tokens` 判層別，非 1h 層改量 5m 版（4 分對 7 分） |
| E2E-WP-11 | 46 | RV-KW9（long）：每 45 分輕觸 4 次，共 3 小時 | 每次 `cache_read ≥ 0.9×`；逐字稿無 `compact_boundary` |
| E2E-WP-12 | 47 | RV-IL1：沙盒 git repo 造 `.git/index.lock`，mtime 回撥 700 秒，真跑 `relay_machine.stale_index_lock`；變體另起真 `git` 行程佔住 | 無 git 行程 ⇒ 改名 `index.lock.stale-*`；有 ⇒ kept |
| E2E-WP-13 | 48 | RV-H6：沙盒專案預植 trust（`~/.claude.json` 的 projects 項 `hasTrustDialogAccepted`，現查鍵存在：本機 15 處；寫入前備份、案例結束還原並斷言還原後與備份逐位元組相同）後 `handoff --spawn` | 新 sid 逐字稿出現 Read 交接包路徑；SessionStart 公告字樣；`~/.claude.json` 還原 |
| E2E-WP-14 | 49 | RV-PB1：真 `claude -p` 帶 `resume_route.spawn_env()`，派背景 shell 睡超過上限 | 行程在上限內結束；環境 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`＝`unattended_authz` SSOT 值 |
| E2E-WP-15 | 50 | RV-WB1：沙盒掛真 `context_budget_guard.py`，真 `claude -p` 連續 WebFetch／WebSearch 3 次再 Agent 一次 | 派發帳無 Web 類；Agent 未被扇出節流擋 |
| E2E-WP-16 | 51 | RV-PR3：預植 trust（同 E2E-WP-13 備份還原）＋真 `park --at now+2` | 原 sid 逐字稿到點後新增 user／assistant 記錄；`park_route` 痕跡＝RESUME |
| E2E-WP-17 | 35 | 真逐字稿（本機 `~/.claude/projects` 近 14 天）跑兩旗標 | rc 0、欄位齊；`quota_rush.py` 案例反轉後 pass |
| E2E-WP-18 | 52 | RV-L3：沙盒真 hook 觸發 Stop 推回、PreToolUse 擋、UserPromptSubmit 轉送 | 逐字稿出現 `hook_blocking_error`／`stop_hook_summary` 且內容含守衛字樣；（r3）純畫面渲染改由 E2E-WP-61（RV-UI1）承接，不再用 human 列 |
| E2E-WP-19 | 30、31 | 沙盒真 `claude -p`：派一支背景子代理（短任務）＋背景 `sessionctl watch`；子代理完成後 | 子代理完成通知後 60 秒內**沒有** watch 的 task-notification；watch 之後以 `WATCH_VERDICT=keepwarm` 結束且 rc 0；此時再起 `keepwarm` ⇒ `skip reason=holder_running` |
| E2E-WP-20 | 32、34、36 | 沙盒真 keepwarm＋watch，`AUTOSDD_KEEPWARM_MINUTES` 設 1、保溫帳預置 n*−1；子代理已全部交卷 | 一次 keepwarm 叫醒後下一次 `cap`；處置表 ping 列文字出現在輸出；（r2）重掛的 watch 在下一個保溫點以 `WATCH_VERDICT=cap` rc 0 自行結束（行程不殘留） |
| E2E-WP-21 | 15、16、78 | 沙盒 OIR 放 human×8、k1×1；真 `claude -p` | SessionStart 簡報含 7 項＋「另 2 項」；k1 列標「須掌舵者親打」 |
| E2E-WP-22 | 23 | 沙盒 git repo：commit 一份含待驗標記無 id 的 md，跑真鎖（`python -m unittest tools.tests.test_openitems_marker_lock` 以沙盒為根） | rc≠0 且指名該行；補 id 後 rc 0 |
| E2E-WP-23 | 17 | 真 repo 歷史：`openitems scan --stale-pass --dry-run`；另在沙盒 git repo（真 commit）重演：家族列 escalate → 重掃 → 動 `SOURCES` 再 commit → 重掃 | 真 repo：列出的家族與 `git log`／帳本手算一致、不寫帳本；沙盒：escalate 後重掃不開列，新 commit 後重掃恰開 1 列 |
| E2E-WP-24 | 12 | 沙盒：真 `claude -p` 正在跑（產生主控記錄）時真排程觸發 `run-driver` | `attempt(deferred, interactive)`；attempts 不變；新排程存在 |
| E2E-WP-25 | 13 | 真排程觸發 `run-driver`，行程環境把額度收斂門檻設為 1（`quota_policy` 既有設定鍵） | `deferred(quota)`；重排時刻 ≥ 觀測 reset |
| E2E-WP-26 | 33 | 真逐字稿 31ea79d4 跑 `waste_census --wake-metrics` | 修前 M-WB2＝8；上線後新逐字稿 M-WB2＝0；M-WB1 印出數值（資訊欄，不作判準） |
| E2E-WP-27 | 42、43 | 真機收尾：`python tools/sessionctl.py status` | 不再出現 ab573c773ef06f035「安靜」；三支殘局滿壽命後只見計數；`retired.jsonl` 有對應列 |
| E2E-WP-43 | 07、01 | 沙盒 OIR：同時起 2 個真 `python tools/openitems.py open` 行程，各連開 20 列；（r3）之後追加一行壞 JSON，真跑 `openitems list` | 40 個 id 互不相同且當日連號；帳本 40 行皆可 fold；`list` 末行 `bad=1` |
| E2E-WP-44 | 16 | 真逐字稿重放：從本機 `~/.claude/projects` 現查一筆 AskUserQuestion 的 tool_result 行與一筆真人打字的 user 行（記 sid＋行號），複本放沙盒 projects；沙盒 OIR 一列 k1，真 CLI `close --by human --evidence "<sid> L<行>"` 兩次 | AskUserQuestion 座標 ⇒ rc 2、帳本無 close；真人打字座標 ⇒ rc 0、`close` 證據引該座標；`--by` 非 human ⇒ rc 2 |
| E2E-WP-45 | 25 | 沙盒掛真 `check_pending_handoff.py`；OIR 路徑改放成一個**目錄**（讀檔必失敗）；真 `claude -p --debug hooks` 做一次寫檔回合 | Stop 未被完成閘推回（逐字稿無完成閘字樣）；debug log 的 hook stderr 含 OIR 讀取失敗一行；hook `success` |
| E2E-WP-46 | 03、08 | 沙盒 OIR 一列 auto（check＝RV-OI1 長版，`budget_minutes` 經沙盒 params 縮到 3）；真排程觸發後約 30 秒以 `taskkill /T` 殺掉 run-driver | 殺後立即 `openitems list`：driven；`start.ts`＋3 分後：undriven 且 `NextRunTime` 仍為空（證明判準不靠它）；真 Stop 完成閘列出該 id |
| E2E-WP-47 | 19 | 沙盒 OIR 4 列 auto（check＝RV-L1），`drive` 期望時刻皆 now＋2 分、`max_runs_per_window`＝2（沙盒 params）；真 schtasks | 4 個排程的 NextRunTime 兩兩相距 ≥`stagger_minutes`；每 5 秒取樣 run-driver 行程數恆 ≤1；窗內真跑 2 次，其餘帳本為 deferred(window_cap)；RealVerify 帳只多 2 列 |
| E2E-WP-48 | 26 | （r3）沙盒 `params.json` 的 `task_prefix` 設為 `AutoSDD_OpenItemSbx_<沙盒 8 碼>_`，建 50 個該前綴的真排程（觸發時刻在遠期；案例結束全數撤銷並斷言該前綴 0 殘留；案例前後各列一次真的 `AutoSDD_OpenItem_*`，兩次結果必須相同，證明沒碰到真排程）＋50 列 driven；真 `list --verify` 一次；再以真 hook 載具（`_hook_launcher` → `check_pending_handoff.py`，真 Stop payload）在「50 列」與「0 列」兩種帳本下各跑 5 次計時 | `list --verify` 期間 powershell 子行程恰 1 個；hook 期間 powershell 子行程 0 個；hook 牆鐘每次 ≤15 秒，且 50 列與 0 列的中位數差 ≤2 秒 |
| E2E-WP-49 | 09 | 沙盒真 git repo（含兩本帳的初始 commit）：追加兩本帳各一行後，以真 `git status --porcelain` 輸出餵 spawn 前置的工作樹判準（`handoff._auto_owned` 逐行）與真 SI `sched.dirty_paths`（指向沙盒 repo）；再另改一個非自有檔重跑 | 只有兩本帳髒時：spawn 前置不因髒拒絕、`dirty_paths` 回空；加非自有檔後：兩者都指名該檔 |
| E2E-WP-30 | 60、61 | 真根層 `.venv`：`openitems helm-check`（出廠 `storage.mode: yaml_only`） | rc 0；輸出含 import origin、鍵名存在；alembic 與容器狀態以資訊列印出（不影響 rc）；不含任何金鑰值（輸出 grep 金鑰值命中 0） |
| E2E-WP-31 | 63 | 真引擎 DRY_RUN（`dry_run_executor`）跑生成的 playbook | rc 0；checkpoint 落 `~/.autosdd/openitems/checkpoints/` |
| E2E-WP-32 | 64 | 沙盒 OIR 一列 auto（RV-L1）、`OPENITEMS_HELM=autoclaude`、真排程觸發 | 引擎 log 有 GOAL_SYNTHESIS 與 evaluator rc 0；OIR closed；RealVerify 帳新列 |
| E2E-WP-33 | 64、05 | 同上但 check＝RV-OI1（必敗） | 引擎 escalation；OIR 兩次後 escalated；`AutoClaude/checkpoints/` 檔數不變 |
| E2E-WP-34 | 65 | 引擎跑到第 2 步時沙盒起真 `claude -p` | 引擎收尾、OIR `deferred(interactive)` |
| E2E-WP-35 | 62 | 真跑 AutoClaude `tests/`（xdist） | 跑前跑後 `AutoClaude/checkpoints/` 檔數相同 |
| E2E-WP-36 | 66 | 真帳本：B3 三次真跑後 `openitems helm-status` | 印資格＝是並列三筆帳列；翻預設 commit 引這三筆 |
| E2E-WP-40 | 70～73、76、77 | 真 repo：期 C 收尾後 `openitems scan` 與 `openitems list --undriven` | unmapped＝0；undriven＝0；PRD 修訂表 v2.1.23 列與 DES 附錄 A-1 逐字相同（腳本比對）；（r2）修憲前後 PRD 既有列 v2.1.22 修訂表列、§16.2 §3.2／§4.5.2 兩列整行位元組不變，§16.6 v2.1.22 列只在行尾多出 `<br>🔴【v2.1.23 註記】…`（腳本以修憲前 blob 比對） |
| E2E-WP-41 | 74、75、20 | 真 `claude -p --model haiku --debug hooks` 於 repo 根 | `check_pending_handoff` Stop hook `success`；根 CLAUDE.md 守衛表宣稱↔註冊雙向鎖（`test_doc_loc_baseline_freshness_r60.py::TestR74…`、`TestR79…`）綠 |
| E2E-WP-42 | 53、76、77、79、90 | （r3 改寫）真 repo：A8 後 `openitems list`，以及 E1② 後的結果帳 | A8 後：RV-LW3、RV-W6、RV-SK1、RV-SK2、RV-K2B、RV-OB4（due 2026-12-02）、RV-OB5（due 2026-11-30）、RV-KW6／KW7 都有 `drive` 憑證，排程器現查 NextRunTime 與事件一致（這只是中間狀態，不算通過）。**通過條件**：上列每個案例在結果帳的最近一次結果為 PASS，且 SK1／SK2 秒數 ≥ `MIN_WALL_SECONDS`、OB4／OB5 帳列時間 ≥ `due` |

### 4.1 r3 新增 E2E（全部是 RealVerify 案例；id 依 REQ-WP-86）
🔴 舊視窗關閉類（E2E-WP-52～54）的沙盒圍籬（r4 改寫，審查 P2-3：不寫死任何 sid）：案例開始與結束各取一次快照——①`~/.claude/sessions/*.json` 中**非本案例建立**的全部登記檔（`pid`、`sessionId`、`procStart`、`entrypoint`）；②全部 `claude.exe`／`node.exe` 行程（pid、建立時間）。「本案例建立」＝案例自己 spawn 的行程，或登記檔 `cwd` 在沙盒根之下。斷言：(a) 案例期間 `oldwin_close_intent`／`oldwin_closed` 記錄的每個終止目標都屬於本案例建立的集合；(b) 開始快照中非本案例的 `entrypoint=cli` 登記檔，結束時以相同 `pid`＋`procStart` 仍在；(c) 非本案例、結束時已消失的 `claude`／`node` 行程逐筆列入證據，且不得出現在 (a) 的目標記錄中。任一違反即案例 fail（(b) 違反時原因標「外部互動視窗在案例期間變動，須重跑」，不算綠）。`AUTOSDD_OLDWIN_QUIET_MINUTES` 只在沙盒行程環境內調小；排程前綴用 `trace_dir()/oldwin/task_prefix` 寫入的沙盒前綴。

| E2E | REQ | 載具 | 斷言 |
|---|---|---|---|
| E2E-WP-50 | 02、06 | 沙盒 OIR，真 CLI：`open` human 缺 `why_not_auto`、observe 缺 `due`、`source` 指向 `README.md` | 三者 rc 2；帳本行數不變 |
| E2E-WP-51 | 80～84、86 | 真 repo：`realverify coverage --check`（含「本檔每個 E2E-WP-xx 都出現在 `cases.json` 某案例的 `refs`」）；再於沙盒複製 PRD 加一列 §16.6 新列、母體不動，以沙盒為根真跑鎖測試；再把母體一條 `e2e` 清空重跑 | 真 repo rc 0；新列 ⇒ 鎖紅並指名；清空 ⇒ 紅並指名；`--write` 兩次輸出逐位元組相同 |
| E2E-WP-52 | 54～56、58 | 沙盒預植 trust（同 E2E-WP-13 備份還原），真開沙盒互動視窗 A（沙盒 sid S），一則提示跑完後閒置；沙盒 quiet 設 1 分；A 底下另起一支背景 shell（sleep）。(a) 跨 sid：沙盒交接包 → 真 `handoff --spawn` 開 B → B 真 `handoff --ack`；(b) 同 sid：另建一組 A′（sid S′）＋真 `park --at now+2`；(c) 負例：A″ 一直在跑約 90 秒的工具（status＝busy）時 park 到點 | (a) `oldwin_close_intent` 早於終止；A 的 claude 與背景 sleep 皆不在；`ack` 輸出含 A 的 pid；(b) 到點後 S′ 先只剩 0 個行程、再出現 1 個新 pid（`claude -r S′`），任何取樣時點 S′ 的活行程數 ≤1；新視窗 SessionStart 出聲含舊 pid；(c) 不關、不開第二個 S″ 行程、重試排程 NextRunTime 非空；三者皆通過沙盒圍籬 |
| E2E-WP-53 | 55、57、98、101 | 沙盒視窗 A（sid S）＋沿用 RV-F1 手法真觸發 forward 轉送開 B，B 真 ack。（r4）變體 (v)：B ack 之後、重試排程觸發之前，在 A 真送一句 `留：先留著`；變體 (w)：重試排程待觸發時真跑 `sessionctl status` 與 `oldwin --sweep` | ack 當下因 ③ 不關，並登記重試排程（NextRunTime＝最後真人記錄＋quiet＋1 分）；排程觸發後 A 被關，B 的下一次 UserPromptSubmit 或 Stop 出聲含 A 的 pid，且出聲含「未送出的文字不會保留」；在 A 再打一句字的變體 ⇒ 重試重判後不關。（r4）(v)：否決檔存在、`oldwin_keep_veto` 一筆；排程觸發後 A 仍活（pid＋建立時間不變）、該排程已自刪、該前綴 0 殘留、B 出聲「掌舵者以『留：』保留舊窗」一次；(w)：status 排程區列出該工作與 NextRunTime；sweep 不刪 pending 工作；案例結束該沙盒前綴 0 殘留 |
| E2E-WP-54 | 56、59 | 真行程：起一支無關的真 `python` sleeper，把它的 pid 寫進沙盒的 spawn 痕跡（`at` 早於其建立時間）與一份沙盒 sessions 目錄的假登記檔（`sessionId`＝沙盒 sid、`procStart` 故意差 1）；分別呼叫真 `handoff.spawn` 前置與真 `oldwin.close_if_eligible`（指向沙盒 sessions 目錄） | spawn 前置不因該痕跡拒絕；close 因 ① 不成立而不砍，sleeper 仍活、寫 `oldwin_close_refused` |
| E2E-WP-55 | 27 | 沙盒 OIR 放一列 `attempt(fail, n=1)` 後無 `drive`（`a.ts`＝20 分前）；沙盒掛真 `check_pending_handoff.py`，真 `claude -p` 做一次寫檔回合 | 真 `openitems list` 判 undriven；Stop 被完成閘推回一次且訊息含該 id |
| E2E-WP-56 | 28 | 沙盒 OIR 6 列 auto（check＝RV-L1），沙盒 params：`max_runs_per_window`＝2、`cap_window_minutes`＝6、`task_prefix` 用沙盒前綴；真 schtasks | 約 3 個窗內 6 列全 closed、0 列 escalated；依 `start` 事件時間排序的 id 順序＝排隊鍵順序；帳本 `deferrals` 全 0 |
| E2E-WP-57 | 87、97 | RV-SK1（soak，6 小時），由 OIR 驅動器觸發；期間另有一般案例被驅動 | 斷言見 REQ-WP-87；soak 執行期間一般案例照常拿到名額（`driver.lock` 未被 soak 佔用）；帳列秒數 ≥ 21,600 |
| E2E-WP-58 | 88、97 | RV-SK2（soak，24 小時），由 OIR 驅動器觸發 | 斷言見 REQ-WP-88；帳列秒數 ≥ 86,400 |
| E2E-WP-59 | 89 | RV-K2B，由 OIR 驅動器觸發 | 斷言見 REQ-WP-89 |
| E2E-WP-60 | 90 | RV-OB4、RV-OB5，到期由 OIR observe 驅動器觸發 | 達標 PASS；帳列時間 ≥ `due` |
| E2E-WP-61 | 91、52 | RV-UI1 | 擷圖 OCR 含守衛字樣（Stop 推回與 `systemMessage` 各一）；截圖存證據目錄 |
| E2E-WP-62 | 92 | RV-F4 | 新 sid 逐字稿有 Read 該 `forward-*.md` 的工具記錄 |
| E2E-WP-63 | 93 | RV-PP1 | 快層紅後 rc≠0、慢層與子專案 leg 未啟動；修好 ruff 檔後快層綠才啟動慢層 |
| E2E-WP-64 | 94 | RV-BC1 | 真行程輸出每條已機械化不變式的判定；不變式 5、10 標為邊界 |
| E2E-WP-65 | 95 | RV-SC3 | 事件名集合＝程式常數；無 `hold_set` |
| E2E-WP-66 | 96、100 | （r4 改寫）RV-PX01～49，載具與輸入逐列見 §10.3 附錄 | 每列的案例在結果帳最近一次有效結果為 PASS，且帳列證據欄含該列附錄寫定的全部斷言鍵（`鍵=值`）；三處改指者其 `refs` 含該 PRD 座標 |
| E2E-WP-67 | 85 | 真 repo，E1③：`python tools/realverify.py coverage --require-pass` | rc 0；`PRD_E2E_Coverage_Table.md` 未覆蓋 0、未 PASS 0、例外恰 4 條（C02、C14、A53、A54） |

| E2E-WP-68 | 99、102、82 | （r4）真 repo 外沙盒副本（含真 `ledger.py`、母體與參數檔副本）：一個家族含一般案例 RV-T-a 與 long 案例 RV-T-b（`MIN_WALL_SECONDS`＝120、`DESIGNED_WAIT_SECONDS`＝130）。①真跑 `realverify run --family <該家族>`（不帶 `--long`）；②真跑 `run --case RV-T-b --long` 但由互動行程直接跑（無 OIR）；③沙盒 OIR 一列 auto 指向 RV-T-b，真排程觸發 `run-driver` 跑完；每步之後真跑 `realverify coverage --check` | ①帳列第 8 欄＝`RV-T-a；略過：RV-T-b(long)`、對照表 RV-T-b 仍非 PASS；②帳列秒數 ≥120 但對照表 RV-T-b 仍非 PASS（無 OIR 對帳）；③對照表 RV-T-b＝PASS，證據引 `attempt` 與帳列時間；三步後 `coverage --check` 皆 rc 0（重產有效）；`git status` 只見三個驅動器自有路徑 |
| E2E-WP-69 | 100 | （r4）沙盒副本放一個宣告 `ASSERTS=("seen","count")` 但只寫 `seen` 的案例 RV-T-shell；真跑 `realverify run --case RV-T-shell`；再補寫 `count` 重跑 | 第一次帳列結果 fail、失敗案例含 RV-T-shell、證據含 `assert_missing:count`、rc 1；第二次 pass 且證據欄含 `seen=…`、`count=…` |

**E2E 計數：64**（期 A 34＋r3 新增 18＋r4 新增 2、期 B 7、期 C 3）。r2 新增 E2E-WP-43～49，改寫 03／08／23／26／30／42；r3 新增 E2E-WP-50～67，改寫 18／42／43／48；r4 新增 E2E-WP-68、69，改寫 52～54 的圍籬、53、66。

## 5. 突變（MU；每條必須讓指定測試轉紅）
| MU | 突變 | 必紅 |
|---|---|---|
| MU-WP-01 | `background_idle` 不排除保溫 shell | AT-WP-25、E2E-WP-06(d) |
| MU-WP-02 | `alive` 改回 `first_uuid_of` | AT-WP-42、E2E-WP-08 |
| MU-WP-03 | `_killed_ids` 改回尾讀 256KB | AT-WP-40、E2E-WP-07 |
| MU-WP-04 | 拿掉 `max_attempts` 檢查 | AT-WP-06、E2E-WP-04 |
| MU-WP-05 | `drive` 接受空 `NextRunTime` | AT-WP-10 |
| MU-WP-06 | watch 的 `ORDER` 加回 `all_done` 退出 | AT-WP-30、E2E-WP-19 |
| MU-WP-07 | 完成閘改讀回覆文字（含「完成」才推） | AT-WP-03 |
| MU-WP-08 | cleanup 恢復 `ignore_errors=True` 且不驗殘留 | AT-WP-47、E2E-WP-09 |
| MU-WP-09 | `run-driver` 以引擎 rc 判 pass（不看 evaluator） | AT-WP-63 |
| MU-WP-10 | deferred 也累加 attempts | AT-WP-14、AT-WP-07 |
| MU-WP-11 | watch 保溫模式達 `pings≥n*` 時不退出（回到舊稿行為） | AT-WP-37 |
| MU-WP-12 | driven 有效性改回「`NextRunTime` 早於現在 15 分」 | AT-WP-50、AT-WP-51、E2E-WP-46 |
| MU-WP-13 | stale-pass 忽略 escalated／listed 列 | AT-WP-52、E2E-WP-23 |
| MU-WP-14 | 拿掉全域互斥鎖（或每窗上限） | AT-WP-53（AT-WP-54）、E2E-WP-47 |
| MU-WP-15 | 完成閘逐列呼叫排程後端 | AT-WP-57、E2E-WP-48 |
| MU-WP-16 | spawn 前置不讀 `driver_own_prefixes` | AT-WP-58、E2E-WP-49 |

| MU-WP-17 | （r3）fold 把「有 `attempt`」一律判 driven（回到 r2「依 a.result 走狀態機」） | AT-WP-66、E2E-WP-55 |
| MU-WP-18 | （r3）`window_cap`／`quota` 重新計入 deferrals | AT-WP-67、AT-WP-69 |
| MU-WP-19 | （r3）名額判定拿掉 `O`（不看排隊中的舊列） | AT-WP-68、E2E-WP-56 |
| MU-WP-20 | （r3）park 到點不查 `live_windows_of`（回到只看 `live_driver`） | AT-WP-71、E2E-WP-52(b) |
| MU-WP-21 | （r3）`eligible()` 拿掉條件 ③（不看真人最後打字） | AT-WP-72、E2E-WP-53 |
| MU-WP-22 | （r3）只砍 claude 本體、不砍子孫 | AT-WP-73、E2E-WP-52(a)（背景 sleep 仍活） |
| MU-WP-23 | （r3）終止前不在 handle 上重驗建立時間（直接用 pid） | AT-WP-73（pid 重用變體）、E2E-WP-54 |
| MU-WP-24 | （r3）忽略 `AUTOSDD_OLDWIN_AUTOCLOSE_OFF` | AT-WP-76 |
| MU-WP-25 | （r3）CI 鎖不解析 PRD §16.6（只看母體自己） | AT-WP-79、E2E-WP-51 |
| MU-WP-26 | （r3）帳列判讀不檢查 `MIN_WALL_SECONDS`／`due` | AT-WP-81 |
| MU-WP-27 | （r3）產生器改成接受手寫產物（`--check` 恆綠） | AT-WP-82、E2E-WP-51 |
| MU-WP-28 | （r4）`eligible()` 不查否決檔（`留：` 被蓋過） | AT-WP-85、E2E-WP-53(v) |
| MU-WP-29 | （r4）拿掉 TOCTOU 重驗（直接終止） | AT-WP-86 |
| MU-WP-30 | （r4）條件 ② 只看背景子代理、不看非保溫背景 shell | AT-WP-87(c) |
| MU-WP-31 | （r4）判讀回到「`family=` 列對家族全部案例有效」（不看執行案例欄） | AT-WP-90、E2E-WP-68① |
| MU-WP-32 | （r4）long 案例 PASS 不做 OIR 對帳 | AT-WP-92、E2E-WP-68② |
| MU-WP-33 | （r4）執行器接受缺 `ASSERTS` 鍵的 pass | AT-WP-93、E2E-WP-69 |
| MU-WP-34 | （r4）登記檔 `status` 缺欄時當成 `idle` | AT-WP-87(a) |

**MU 計數：34**（r2 新增 MU-WP-11～16；r3 新增 MU-WP-17～27；r4 新增 MU-WP-28～34）。

## 6. SA 26 項未結對應（對應率 26／26＝100%）
| SA # | 項目 | 對應 |
|---|---|---|
| a1 | realverify 無排程驅動 | REQ-WP-08～11／17／19／26（DES D-4：接 OIR 驅動器，不接 nightly；r2 補觸發後有效性、stale-pass 防永動、扇出上界、閘延遲）；E2E-WP-03、E2E-WP-23、E2E-WP-46～49 |
| a2 | E2E-SS-04 無案例 | REQ-WP-45；E2E-WP-10 |
| a3 | RV-LW3 從未跑 | REQ-WP-53；E2E-WP-03 機制＋A8 驅動入帳 |
| a4 | RV-W6 從未跑 | REQ-WP-53；同上 |
| a5 | V-SS1 3 小時 | REQ-WP-46；E2E-WP-11 |
| a6 | RV-KW6／KW7 未入帳 | REQ-WP-79；E2E-WP-42（UX 棒收尾若已入帳＝已有證據） |
| a7 | V-P6 旗標未實作 | REQ-WP-35（旗標 A7、案例反轉 A6）；E2E-WP-17 |
| a8 | §8 列 3 `tasklist` 分支 | REQ-WP-47；E2E-WP-12 |
| a9 | RV-H3 信任框 | REQ-WP-48；E2E-WP-13 |
| a10 | §2.12 print 上限 | REQ-WP-49；E2E-WP-14 |
| a11 | §2.16 網頁讀取 | REQ-WP-50；E2E-WP-15 |
| a12 | long-runner G3 | REQ-WP-73（依設計退役，DES D-6）；E2E-WP-40 |
| a13 | 名冊兩缺陷＋沙盒殘留 | REQ-WP-40～44（r2：REQ-WP-41 明定 procStart 比對法）；E2E-WP-07／08／09／27 |
| a14 | 文件陳舊 | REQ-WP-72（非 PRD 文件）＋REQ-WP-70（PRD A47／A48 只追加註記）；E2E-WP-40 |
| a15 | v2.1.22 QA 座標待填 | REQ-WP-70（r2：在 v2.1.23 修訂表列追加註記，PRD:27 原文不動）；E2E-WP-40 |
| a16 | PRD 缺 8 族登記 | REQ-WP-71；E2E-WP-40 |
| b1 | E2E-SS-05 14 天 | REQ-WP-14、90（RV-OB4，due 2026-12-02）；E2E-WP-05、42、60 |
| b2 | V-PK5 14 天 | REQ-WP-14、90（RV-OB5，due 2026-11-30）；E2E-WP-05、42、60 |
| b3 | §11.8 24h／≥4 reset | （r3）REQ-WP-76、88（RV-SK2 soak，由驅動器跑滿 24 小時）；E2E-WP-42、58 |
| b4 | §11.1 6h 零 token | （r3）REQ-WP-76、87（RV-SK1 soak，跑滿 6 小時）；E2E-WP-42、57 |
| c1 | V-SS5 真開窗 | REQ-WP-51；E2E-WP-16 |
| c2 | block 理由／systemMessage 畫面 | REQ-WP-52（送達機驗）＋（r3）REQ-WP-91（RV-UI1 截圖 OCR，取代 human 列）；E2E-WP-18、61 |
| c3 | V-F1 轉送畫面＋新視窗讀檔 | （r3）REQ-WP-92（RV-F4 新視窗讀檔）＋REQ-WP-52、91（送達與畫面）；E2E-WP-18、61、62 |
| c4 | §13 法務 | REQ-WP-78（human 列）；E2E-WP-21 |
| c5 | A7 無人 commit／push | REQ-WP-78（k1 列）；E2E-WP-21 |
| c6 | V-K1／K2／K3、V-M1 | REQ-WP-77（V-K1 退役、V-K3 併 M-K2、（r3）V-K2 改由 RV-K2B 主動跑，REQ-WP-89、E2E-WP-59；V-M1 已有 RV-M1 帳列 2026-11-18T20:19:15Z＝已有證據，只需改文件）；E2E-WP-40、E2E-WP-42 |

## 7. ARC 缺口 H1～H10 與停滯型態對應
| ARC | 對應 |
|---|---|
| H1 無完成定義 | REQ-WP-01～09、20、26、70（A-2、A-5、A-6、A-10；r2：A-10 ✅ 條件全部可機械判定） |
| H2 停工閘在保溫下失明 | REQ-WP-22；MU-WP-01 |
| H3 AutoClaude 不在續航路徑 | REQ-WP-60～66、70（A-3、A-9） |
| H4 殘局無規格 | REQ-WP-40～44、70（A-7 第 7 款） |
| H5 叫醒無預算 | REQ-WP-30～34、36、70（A-4、A-8） |
| H6 觀察期與禁日曆衝突 | REQ-WP-14、17（stale-pass 事件觸發）、76、77（事件型項定義 due）、70（A-6） |
| （r2）驅動器扇出 | REQ-WP-19；MU-WP-14 |
| H7 人眼項無集合點 | REQ-WP-15、16、78 |
| H8 停工型態 4～6 不在 PRD | REQ-WP-71（A-11 第 8 列）、74 |
| H9 測試寫真 checkpoints | REQ-WP-62；E2E-WP-35 |
| H10 退出碼兼事件碼 | 並行 R216 UX 棒（DEF-200-622）；本檔 AT-WP-35 斷言相容 |
| S7 宣告式完成／S8 保溫遮蔽／S9 殘局／S10 叫醒過多／S11 待驗需閒置／S12 人眼項 | REQ-WP-20／22／42～43／30～33／45（沙盒驗、不用主控閒置）／15 |
| （r3）同 sid 雙視窗、舊窗殘留 | REQ-WP-54～59；E2E-WP-52～54 |
| （r3）待驗擱置無結案判準 | REQ-WP-80～97；E2E-WP-67 |

## 8. 逐功能 E2E 覆蓋表（每功能 ≥1 個真機 E2E）
| 功能 | E2E |
|---|---|
| OIR 帳本與掃描 | E2E-WP-01、40 |
| 配號不撞號 | E2E-WP-43 |
| auto 驅動器與憑證 | E2E-WP-02、03 |
| 觸發後有效性（空 NextRunTime、崩潰偵測） | E2E-WP-03、46 |
| 扇出上界（互斥／每窗上限／錯開） | E2E-WP-47 |
| 驅動器自有寫入面 | E2E-WP-49 |
| k1 關閉只認真人發言 | E2E-WP-44 |
| 防永動／escalate | E2E-WP-04 |
| observe 驅動器 | E2E-WP-05、42 |
| 讓路／額度 deferral | E2E-WP-24、25 |
| stale-pass（含 escalate 後不重開） | E2E-WP-23 |
| 事件型 observe（§11.1／§11.8／V-K2 的 due） | E2E-WP-42 |
| 完成閘＋保溫排除＋保溫閘讓路 | E2E-WP-06 |
| 完成閘 fail-open | E2E-WP-45 |
| 完成閘延遲（零子行程、N＝50） | E2E-WP-48 |
| CI 標記鎖 | E2E-WP-22 |
| 人工清單 | E2E-WP-21 |
| watch 保溫模式／互斥／cap・idle 退出 | E2E-WP-19、20 |
| 叫醒共用預算 | E2E-WP-20 |
| 叫醒量測 M-WB | E2E-WP-26 |
| V-P6 量測 | E2E-WP-17 |
| 名冊 killed／owner／降級／retire | E2E-WP-07、08、27 |
| 沙盒清理／sweep | E2E-WP-09 |
| 8 個補件案例 | E2E-WP-10～16、18 |
| AutoClaude 前置／DRY_RUN／真跑／失敗／互斥／H9／翻預設 | E2E-WP-30～36 |
| PRD 修憲與文件 | E2E-WP-40、41 |
| （r3）OIR 壞行計數、schema／收件範圍拒絕 | E2E-WP-43、50 |
| （r3）attempt 後空窗判 undriven | E2E-WP-55 |
| （r3）先進先出、排隊不 escalate | E2E-WP-56 |
| （r3）同 sid 雙視窗、舊窗有條件自動關閉（spawn／park／forward 三範圍）、砍錯行程防護、spawn 痕跡身分比對 | E2E-WP-52、53、54 |
| （r3）PRD 全功能 E2E 對照表、CI 鎖、PASS 債、結案 | E2E-WP-51、67 |
| （r3）SA 缺口案例（soak、K2B、14 天觀察、畫面、轉送讀檔、pre-push、啟動自檢、事件常數、逐列案例） | E2E-WP-57～66 |
| （r4）`留：` 否決、`AutoSDD_OldWinClose_*` 現查與回收 | E2E-WP-53 |
| （r4）帳列執行案例、long 案例 OIR 對帳、對照表重產 | E2E-WP-68 |
| （r4）空殼案例防線 | E2E-WP-69 |

## 9. 交卷判準（各期收尾窗口）
1. 該期全部 AT 綠（根層全套以 `sessionctl runlong`／`waitfor` 跑，附 Ran／OK／rc）。
2. （r3 改寫，掌舵者結案判準）該期全部 E2E 在 `RealVerify_Result_Ledger.md` 的最近一次結果為 PASS（判讀規則＝REQ-WP-82）。期中收尾時，未 PASS 者必須已是 OIR `driven` 列並附憑證，這只代表「該期可以收尾、有驅動器在推」，**不代表通過**；`escalated` 列要先修到 PASS 才能收該期。R217 整體結案只看第 7 條。不得以文字「待驗」或「已排程」結案。
3. MU 全部殺死（附突變前後輸出）。
4. `openitems list --undriven` 輸出 0。
5. 修復不留後遺症三問逐條作答。
6. （r2，stale-pass 觸發事件 (a)）收尾窗口在最後一個 commit 之後跑 `python tools/openitems.py scan --stale-pass`，新開列同窗口 `drive`，交卷附其末行與新列 id。
7. （r3）**R217 結案**＝E2E-WP-67 PASS：`python tools/realverify.py coverage --require-pass` rc 0，`PRD_E2E_Coverage_Table.md` 未覆蓋 0、未 PASS 0，例外恰為 §10.2 的 4 條。long、soak、時間閘案例的 PASS 必須是驅動器真的跑完的帳列（秒數與 `due` 條件見 REQ-WP-82）。

## 10. PRD 全功能 E2E 對照（r3；母體種子，E1① 據此建 `prd_population.json`）
編號＝SA 矩陣（scratchpad `r217_sa_report.md` §1）。每條至少一個 E2E（RealVerify 案例 id）；「新」＝本版新增的案例。對照表產物由程式產生（REQ-WP-81），本節只是母體種子，不是對照表本身。

### 10.1 normal 條目（96 條）
| 條目 | PRD／ADR 座標 | SA 狀態 | E2E |
|---|---|---|---|
| A01～A29 | PRD §16.2 ✅ 矩陣 ID（PRD:2690）依序：§4.1.1-T5、§4.1.3、§4.1.4、§4.1.5、§4.2.3a、§4.2.4、§4.2.8、§4.5.5、§4.5.6、§4.5.7、§4.5.8、§4.5.9、§6.2-3、§8-1b、§8-4、§8-6、§8-8、§8-10、§8-14、§12-憑證、§12-命令執行、§13-禁令、§11.4、A1、A2、A5a、A6、A8、A9 | 完備（PRD 自帳） | 依序 RV-PX01～RV-PX29（新）；（r4）載具與斷言逐列見 §10.3；A08 改開 RV-PX08（RV-A1 驗的是 A48 引擎面，不涵蓋 §4.5.5 規劃器排程面） |
| A30～A46 | PRD §16.2 無殘留 ✅ 列依序：§4.1.1 T3（PRD:2697）、§4.3（2698）、§4.5.4（2699）、§4.5.10（2700）、§6.2 R-6.2-2（2702）、§8 列 1（2703）、§8 列 12（2705）、§8 列 13（2706）、§12 權限旗標（2707）、§12 寫入範圍（2708）、§12 日誌遮蔽（2709）、§11.2（2712）、§11.3（2713）、§11.7（2714）、§15.5（2716）、施工圖 A4（2717）、§4.4.3（2719） | 完備（PRD 自帳） | 依序 RV-PX30～RV-PX46（新）；（r4）載具與斷言逐列見 §10.3 |
| A47 | §3.2 FSM／中斷後重啟續跑（PRD:2696） | 完備 | RV-A1 |
| A48 | §4.5.2 長睡外部續跑（PRD:2720） | 完備 | RV-A1 |
| A49 | §6.1 啟動自檢不變式（PRD:2701） | 完備（E2E 欄空） | RV-BC1（新，E2E-WP-64） |
| A50 | §8 列 3 陳舊 index.lock（PRD:2704） | 缺真機 | RV-IL1（E2E-WP-12） |
| A51 | §11.1 零 token 6h（PRD:2711） | 缺真機 | RV-SK1（新，E2E-WP-57） |
| A52 | §11.8 24h／≥4 reset（PRD:2715） | 缺真機 | RV-SK2（新，E2E-WP-58） |
| B01～B03 | PRD §16.6：2026-10-10 CLI 版本家族、2026-10-11 env 跨機同步、2026-10-14 halt 標記辨識他 session 接手 | 完備 | RV-PX47～RV-PX49（新；載具與斷言見 §10.3） |
| C01 | REQ-SS-01 成本公式 | 完備 | RV-CM1 |
| C03 | REQ-SS-03 keepwarm 指令 | 文件不符（rc） | RV-KW1、RV-KW6（DEF-200-622 後 rc 0；TCS-SS 同步歸 REQ-WP-72） |
| C03b | 保溫真的保住快取 | 缺 E2E | RV-KW8（E2E-WP-10） |
| C04 | REQ-SS-04 保溫帳 | 完備 | RV-KW1 |
| C05 | REQ-SS-05 不掛條件 | 完備 | RV-C4 |
| C06 | REQ-SS-06 Stop 保溫閘 | 完備 | RV-KW5 |
| C07 | REQ-SS-07 冷叫醒閘豁免 | 完備 | RV-C2、RV-C4 |
| C08 | REQ-SS-08 watch 保溫錨點 | 缺 E2E | RV-W6（long，E2E-WP-42 通過條件） |
| C08b | 子代理分段等待效果 | 缺 E2E | RV-LW3（long，同上） |
| C09 | REQ-SS-09 watch quota 閂鎖 | 完備 | RV-KW3、RV-KW4 |
| C10 | REQ-SS-10 runlong | 完備 | RV-LW1 |
| C11 | REQ-SS-11 waitfor | 完備 | RV-LW1 |
| C12 | REQ-SS-12 長前景閘 | 完備 | RV-LW2、RV-LW4 |
| C13 | REQ-SS-13 封存閘 HARD | 完備 | RV-CM1、RV-C1 |
| C15 | REQ-SS-15 收斂閘 HARD | 完備 | RV-CM2 |
| C16 | REQ-SS-16 advise_once | 完備 | RV-CM1 |
| C17 | REQ-SS-17 F4 | 完備 | RV-CM3 |
| C18 | REQ-SS-18 轉送 F4 | 完備 | RV-CM4、RV-F1 |
| C19 | REQ-SS-19 park 選路 | 缺真機（V-SS5） | RV-PR1、RV-PR2、RV-PR3（E2E-WP-16）；同 sid 先關再開另由 E2E-WP-52(b) |
| C20 | REQ-SS-20 量測 M-K | 完備 | RV-SC1、RV-SC2、RV-OB4（E2E-WP-60） |
| C21 | REQ-SS-21 事件常數 | 文件不符（`hold_set`） | RV-SC3（新，E2E-WP-65） |
| D01 | §2.10 自願停機喚醒活動判準 | 完備 | RV-N1、RV-N2、RV-N3 |
| D02 | §2.11 雙駕駛 | 完備 | RV-N3、RV-N5 |
| D03 | §2.12 無人 print 模式背景上限 | 缺 E2E | RV-PB1（E2E-WP-14） |
| D04 | §2.13.2 無人選路量成本 | 完備 | RV-CM3 |
| D05 | §2.13.3 過期 session 不續跑 | 完備 | RV-N4 |
| D06 | §2.13.4-5 交接包 | 缺真機（RV-H3 信任框） | RV-H1～RV-H5、RV-H6（E2E-WP-13） |
| D07 | §2.13.6 D6 續棒成本閘 | 完備 | RV-M1 |
| D08 | §2.13.6 D7 名冊 | 文件與程式不符（判準兩缺陷） | RV-T1、RV-T4、RV-T5（E2E-WP-07、08）、E2E-WP-27 |
| D09 | §2.13.7 模型平衡 | 完備 | RV-T3 |
| D10 | §2.14 收斂閘 | 完備 | RV-M2、RV-C3 |
| D11 | §2.14 G3 long-runner | 未實作（DES D-6 依設計退役） | RV-LW3、RV-LW2：退役理由是「子代理 5 分鐘快取壽命」改由分段等待滿足，所以以替代機制的 E2E 驗需求本身成立。**這不是掌舵者判準允許的例外類別**，故不列入 §10.2 |
| D12 | §2.14 推送快層先行 | 本棒未追溯 | RV-PP1（新，E2E-WP-63） |
| D13 | §2.15 配速床＋趕工戳記 | 部分未實作（V-P6） | RV-R1、RV-R2、RV-WP17（E2E-WP-17） |
| D14 | §2.16 網頁讀取不進派發帳 | 缺 E2E | RV-WB1（E2E-WP-15） |
| D15 | §2.17 park | 完備 | RV-K1～RV-K7、RV-N5、RV-OB5（E2E-WP-60） |
| D16 | §2.18 D1 watch 監督 | 缺 E2E（W6） | RV-S1、RV-S2、RV-W1～RV-W6 |
| D17 | §2.18 D2 封存閘 | 完備 | RV-C1 |
| D18 | §2.18 D3-4 冷窗轉送／已交棒告知 | 缺真機 | RV-F1～RV-F3、RV-F4（E2E-WP-62）、RV-UI1（E2E-WP-61） |
| D19 | 半路停工判準 | 完備 | RV-P2 |
| D20 | 散文交棒 Stop 守衛 | 完備 | RV-P1 |
另：本檔全部 REQ-WP 也進母體，`e2e` 取 §4 該 REQ 所對應的 E2E-WP 案例（REQ-WP-86 的 id 規則）。

### 10.2 例外（4 條；只限掌舵者判準允許的兩類，`class` 非 normal）
| 條目 | 類別 | 理由與裁決座標 |
|---|---|---|
| C02 | decision_retired | REQ-SS-02 軟線：掌舵者 2026-11-18 裁決「不設軟線、只留硬線」（`docs/02_architecture/SessionSwitch_CostModel_Design.md:16`、`:307` D-1）。沒有行為可驗 |
| C14 | decision_retired | REQ-SS-14 hold 戳記：同日裁決「hold 整個不實作」（同檔 `:308` D-2） |
| A53 | human | PRD §13 使用條款法務檢核（PRD:2710）：法律判斷，只能由人做；OIR 以 human 列承接（REQ-WP-78） |
| A54 | human | 施工圖 A7 無人 commit／push（PRD:2718）：是掌舵者的安全裁決，不是待驗功能；OIR 以 k1 列承接（REQ-WP-78） |

**覆蓋率**：100 條中 normal 96 條，每條都至少指定一個 E2E id（96／96＝100%）；例外 4 條，都在掌舵者判準允許的兩類內。新指定、待 A6 實作的案例：RV-PX01～49（r4：扣三處改指 PX17／PX19／PX37 為 46 個；PX08 改為自有案例）、RV-BC1、RV-SK1、RV-SK2、RV-SC3、RV-PP1、RV-F4、RV-UI1、RV-K2B、RV-OB4、RV-OB5，以及 §4 已列的 RV-KW8／KW9／IL1／H6／PB1／WB1／PR3／L3／T4／T5。

### 10.3 附錄：A01～A46、B01～B03 逐列載具與斷言（r4；審查 P2-1；CI 鎖 (f) 的單一真相源）
每列先讀 PRD 對應列（§16.2 列文字；29 個矩陣 ✅ ID 讀 `docs/06_quality/CrossPlatform_R211_PRD_Coverage_Matrix_113.md` 的同名列）再寫。「斷言鍵」欄的每個鍵＝案例 `ASSERTS` 的一個元素，冒號後是可觀測判準；案例必須以 `ctx.evidence(鍵, 值)` 寫出該判準的實測值，否則判 fail（REQ-WP-100）。完成數：**49／49**（A01～A46＋B01～B03 每列都有載具與至少一個斷言鍵；其中三列改指同載具案例，見「案例」欄）。

**載具代號**（`CARRIER` 取值；一列可多個，以 `＋` 連接）：
| 代號 | 意義 |
|---|---|
| P | 真行程（repo 內真程式，以子行程在 RealVerify 沙盒中執行） |
| S | 真排程（Windows schtasks／macOS launchd，沙盒專屬前綴，案例結束撤銷並斷言 0 殘留） |
| C | 真 `claude -p`（haiku，沙盒 cwd） |
| H | 真 hook（`_hook_launcher` 載具＋真 payload，或真 `claude -p` 觸發） |
| R | 真逐字稿／真痕跡重放（取自本機真檔或依真格式注入沙盒 projects） |
| E | 沙盒 T5 端點替身：本機 TLS 代理，經 `HTTPS_PROXY` 與 `SSL_CERT_FILE` 只注入沙盒行程環境；沙盒 HOME 放假憑證，真 token 永不送出；替身逐筆記錄請求方法與時間 |
| F | statusLine feed 替身：`AUTOSDD_CONTEXT_FEED_DIR` 指向沙盒，feed 內容取自本機真 feed 樣本 |
| K | `quota_policy` 既有門檻鍵移帶（D-12 同法，只在沙盒行程環境設定） |
| X | PATH 前置的 `claude` 替身 shim（只用在引擎需要特定 CLI 輸出、真 CLI 無法安全誘發的列） |

**載具前提與預定退路**（A6 第一步以 RV-PX01 實跑確認，結果寫進 A6 交卷）：
- E：`tools/lib/quota_meter.py:626` 以 `urllib.request.urlopen` 預設 opener 發請求（本棒當回合 Read 實查），預設 opener 會讀環境代理；預設 SSL context 會讀 `SSL_CERT_FILE`。若實跑不成立 ⇒ 改用 F＋「沙盒 HOME 無憑證」（T5 真的讀不到 ⇒ `settled_quota` 走 statusline-fallback，PRD:2697 已落地的正式路徑）承接讀數類列；只有 429 類（A14、A24 第三變體、A44 `rl1_get_only`）無 F 退路，屆時這三格改列 §10.2 例外候選，交主控裁決並同 commit 改本表。
- C 對 `/compact`（A31）：若 `claude -p -r <sid> "/compact"` 不觸發 PreCompact ⇒ 改用 RV-UI1 的真互動視窗載具送 `/compact`（`CARRIER` 改 `H＋S`，斷言鍵不變）。
- X：shim 只決定 CLI 的輸出內容，被驗的引擎行程、設定載入、log、checkpoint 都是真的；shim 腳本放沙盒 bin 目錄、PATH 只在沙盒行程環境前置。

**唯一無法真實誘發的分支**：A13／A19（§6.2-3、§8-14）的「空間不足 ⇒ 拒絕啟動」分支。`check_space` 的門檻只有程式參數 `margin_bytes`（`AutoClaude/autoclaude/utils/disk_space.py:21` `DEFAULT_MARGIN_BYTES`，無環境鍵或設定鍵，本棒當回合 Grep 實查），要讓真磁碟「不足」只能掛一個小容量磁碟區，非系統管理員權限做不到。所以該列的 E2E 斷言放在「讀的是真磁碟、通過分支輸出正確」，拒絕分支由既有單元測試承接；這是該列內的一個分支例外，不是整列例外（整列仍有斷言鍵與 E2E）。

**載具 E 的條件式分支例外（主控代決 2026-11-19，依 SCG 第四次複審建議）**：A6 第一步先實跑確認載具 E（`HTTPS_PROXY`＋`SSL_CERT_FILE` 本機 TLS 替身）。若成立，A14、A24 第三變體、A44 `rl1_get_only` 的 429 格照驗。若不成立，只拿掉這三格 429 斷言，改列「列內分支例外」，各列其餘斷言照驗，不整列移入 §10.2。WHY：對真端點觸發 429 違反 PRD §13（高頻探測禁令）；端點 URL 寫死（`quota_meter.py:76`），沒有環境鍵可改指；代理對 CONNECT 回 429 時 Python 丟的是 OSError，走不到 HTTPError(429) 分支，沒有其他正當的真機替代。429 分支改由既有單元測試承接；實作期須把實跑結果（成立或不成立）寫進 R217 證據檔。

| 條目 | PRD 座標與要求 | 案例 | 載具 | 輸入 | 斷言鍵：可觀測判準 |
|---|---|---|---|---|---|
| A01 | §4.1.1-T5（PRD:250）：T5 唯讀主源、token 不落痕跡、TTL≥180 s | RV-PX01 | P＋E | 沙盒跑 `python tools/session_resume_planner.py --pace` 兩次，間隔 < TTL | `t5_get_once`：替身收到恰 1 筆、方法 GET；`ttl_cached`：第二次替身新請求 0；`token_absent`：假 token 字串在沙盒 trace_dir、stdout、stderr 命中 0 |
| A02 | §4.1.3（PRD:288）：視窗重置偵測 | RV-PX02（long） | P＋E | 替身讀數 80%→3%、`resets_at` 前移 5 小時，兩次 `--pace` 間隔 > TTL | `rollover_seen`：痕跡出現新窗段；`row_resets_at`：新窗列的 `resets_at` 等於替身值 |
| A03 | §4.1.4（PRD:301）：帳號／方案變更偵測 | RV-PX03（long） | P＋E | 替身兩次回應的 `anthropic-organization-id` 標頭不同，間隔 > TTL | `account_change_seen`：痕跡記一筆帳號變更；`ledger_split`：沙盒出現兩個帳本鍵、舊鍵最後讀數未被新讀數覆寫 |
| A04 | §4.1.5（PRD:358）：遙測全失效收斂 cap≤cap_prepare | RV-PX04 | P | 沙盒 HOME 無憑證檔（T5 真的讀不到） | `unmeasured`：`--pace` 判為量不到；`cap_le_prepare`：印出 cap ≤ `--print-env-example` 的 prepare cap；`no_halt`：沙盒無 halt 標記檔 |
| A05 | §4.2.3a（PRD:484）：閘門短路優先序 | RV-PX05 | P＋E | 替身回 model-scoped 軸 ≥ halt、主軸 20% | `veto_first`：輸出的 binding 軸＝該否決軸且配速段未參與；`cap_from_gate`：cap 等於該閘的值 |
| A06 | §4.2.4（PRD:522）：平穩性（遲滯、死區、停留） | RV-PX06（long） | P＋E | 替身讀數在 converge 門檻 ±1pp 來回 10 次，每次間隔 > TTL | `hysteresis`：cap 變動次數 ≤ 穿越次數÷2；`no_skip_level`：每次放寬只升 1 級；`dwell_respected`：相鄰兩次放寬間隔 ≥ 最短停留秒數（現查鍵值） |
| A07 | §4.2.8（PRD:971）：pace_index 對齊 CLI 配速門檻 | RV-PX07 | P＋E | 替身給定 pct 與 `resets_at` | `pace_index_value`：`--pace` 印出值與案例以同讀數依 PRD §4.2.8 公式手算相差 <0.01 |
| A08 | §4.5.5（PRD:1167）：長休眠交棒 OS 排程 | RV-PX08 | S＋P＋E | 替身回短窗 ≥ halt、`resets_at`＝now＋6 小時 | `endurance_armed`：沙盒前綴排程存在且 NextRunTime 與 reset＋`RESET_SKEW_SECONDS` 相差 ≤60 s；`no_inprocess_sleep`：planner 行程 30 s 內結束 |
| A09 | §4.5.6（PRD:1186）：撞線喚醒閉環 R-1～6、A1～A5 | RV-PX09（long） | S＋R | 沙盒逐字稿依真格式注入 synthetic 撞線記錄（reset＝now＋3 分），真哨兵巡邏；變體刪除任務書狀態塊 | `arm_reset`：痕跡出現 arm_reset；`cred_nonempty`：排程 NextRunTime 非空；`distinct_events`：巡邏、武裝、自癒、解除事件名互異；`self_heal`：變體中哨兵重建狀態塊並續巡、未 unregister |
| A10 | §4.5.7（PRD:1235）：主控閒置盲區預防提醒 B1～B3 | RV-PX10（long） | S＋R＋K | 沙盒逐字稿最後事件設為 40 分前，門檻鍵使真實水位落 prepare 帶 | `idle_seconds`：痕跡閒置秒數與注入時差 ≤60；`notice_by_patrol`：通知痕跡的行程是巡邏行程；`no_skeleton`：任務書檔未被寫入 |
| A11 | §4.5.8（PRD:1306）：哨兵武裝漂移自癒 C1～C4 | RV-PX11 | S＋H | 真武裝沙盒哨兵，以 `Unregister-ScheduledTask` 外力刪除，再以真 hook 載具觸發一次 PostToolUse | `drift_seen`：痕跡出現 armed_but_missing；`rearmed`：同前綴新排程 NextRunTime 非空 |
| A12 | §4.5.9（PRD:1366）：髒污工作樹存檔救援 D1～D9 | RV-PX12 | P | 沙盒 git repo 留未提交修改，真引擎走 halt 路徑 | `rescue_patch`：救援 patch 存在且 `git apply --check` 通過；`tree_untouched`：`git status --porcelain` 前後相同 |
| A13 | §6.2-3（PRD:2052）：可用空間檢查 | RV-PX13 | P | 真 `python -m autoclaude` 開機自檢（checkpoint 目錄在沙盒） | `free_is_real`：自檢輸出 free 值與同時 `shutil.disk_usage` 相差 ≤1%；`pass_line`：輸出含「可用空間 … ≥ 需求 … bytes」（拒絕分支見上方說明） |
| A14 | §8-1b（PRD:2295）：遙測端 429＝量不到、永不 halt | RV-PX14 | P＋E | 替身回 429＋`Retry-After: 120` | `reason_429`：痕跡 reason 為 http-429-unmeasured；`no_halt`：無 halt 標記；`retry_after_shown`：輸出含恢復時刻；`cache_kept`：快取檔前後位元組相同 |
| A15 | §8-4：斷電／checksum 回退 | RV-PX15 | P | 真引擎子行程寫 checkpoint 時在三個寫入階段各以 `taskkill /F` 結束一次 | `torn_rejected`：新行程拒用撕裂版；`fallback_valid`：載入的是上一份 checksum 正確版本 |
| A16 | §8-6：遙測永久失效 | RV-PX16（long） | P | 沙盒無憑證，每隔 > TTL 跑 `--pace`，共 3 次 | `degraded_sustained`：三次皆量不到且 cap ≤ prepare cap；`never_halt`：無 halt 標記 |
| A17 | §8-8：髒污工作樹 | RV-PX12（改指，`refs` 加 §8-8） | P | 同 A12 | 同 A12：`rescue_patch`、`tree_untouched` |
| A18 | §8-10：喚醒後 context 不可用 ⇒ FRESH | RV-PX18 | S＋P | 沙盒 session 逐字稿在到點前改名（不可續），真排程觸發 planner | `route_fresh`：痕跡選路 FRESH；`handback_written`：handback 檔存在 |
| A19 | §8-14：磁碟空間不足 | RV-PX13（改指，`refs` 加 §8-14） | P | 同 A13 | 同 A13：`free_is_real`、`pass_line` |
| A20 | §12-憑證：唯讀、不落痕跡 | RV-PX20 | P＋E | 沙盒假憑證，`--pace` 一次＋真引擎一步 | `token_absent`：假 token 在 trace_dir、state、checkpoint、log 命中 0；`cred_unmodified`：憑證檔 mtime 與雜湊前後相同 |
| A21 | §12-命令執行：命令來自設定、state 無可執行字串 | RV-PX21 | S＋P | 沙盒任務書 RELAY 塊某欄塞入 `& echo pwned > x`，真排程觸發續跑 | `no_side_effect`：沙盒 `x` 不存在；`argv_from_params`：spawn 行程命令列快照不含該字樣 |
| A22 | §13-禁令：不輪替帳號、不繞限流、不高頻探測 | RV-PX22 | P＋E | 10 秒內連跑 `--pace` 20 次 | `probe_rate`：替身請求數 ≤ ceil(經過秒數÷TTL)；`single_account`：沙盒帳本鍵恰 1 個 |
| A23 | §11.4（PRD:2389）：週上限長休眠 | RV-PX23 | S＋P＋E | 替身週軸 ≥ halt、`resets_at`＝now＋3 天，短窗 reset＝now＋2 小時 | `armed_earliest_reset`：排程時刻依最早可 reset 軸（＋skew）；`cred_nonempty`：NextRunTime 非空 |
| A24 | 施工圖 A1（R108 W0～W2.5） | RV-PX24 | P＋E | 三變體：讀數帶 `resets_at`；配速乘數 >1；429＋`Retry-After` | `row_resets_at`：列帶 `resets_at`；`cap_mult_clamped`：輸出含「等同無節流」且乘數 ≤1.0；`retry_after_sidefile`：旁檔記下該時刻 |
| A25 | 施工圖 A2（R108 W3） | RV-PX25 | P＋E | 替身給定一組讀數 | `rec_of_gate`：`--pace`「現在可派」等於案例以同讀數呼叫 `quota_policy.decide()` 回傳的 rec |
| A26 | 施工圖 A5a（R112 REQ-W1／W3／W4／W5／W7） | RV-PX26（long） | S＋C＋R | 沙盒撞線記錄（reset＝now＋3 分）→真哨兵→到點真 `claude -p -r --model haiku`；通知器第一次投遞以唯讀目錄使其失敗 | `resumed`：原 sid 逐字稿新增 assistant 記錄；`prepare_precheck`：續跑前痕跡有額度預檢；`notify_redelivered`：第二次巡邏重投且寫出 delivered 憑證 |
| A27 | 施工圖 A6（R113 G1～G4） | RV-PX27（long） | S＋C | 同 A26 的喚醒鏈 | `unattended_posture`：spawn 命令列含 `settings.unattended.json`；`handback_visible`：下一個真 `claude -p` 的 SessionStart 公告該 handback；`relay_progress`：RELAY 狀態依序前進；`sentinel_rearmed`：fire 後新排程 NextRunTime 非空 |
| A28 | 施工圖 A8（R126 gate 聚合面） | RV-PX28 | P＋E | 替身回應含 model-scoped 軸 | `gate_excluded_printed`：輸出含 `gate_excluded=` 且列出該軸 |
| A29 | 施工圖 A9（R127 環境鍵前綴） | RV-PX29 | P | 真引擎三次，各設 `AUTOCLAUDE_CONFLICT_POLICY`、`AUTOCLAUDE_STATE_RETAIN_VERSIONS`＝2、`AUTOCLAUDE_DIRTY_SAVE_RETRIES` 為非預設值 | `conflict_policy`：自檢輸出採用設定值；`retain_versions`：checkpoint 版本檔數＝2；`dirty_retries`：救援重試次數＝設定值 |
| A30 | §4.1.1 T3（PRD:2697）：statusLine 回寫額度欄與後備 | RV-PX30 | P＋F＋R | 以本機真 feed 樣本為輸入跑真 producer `tools/statusline_context_feed.py`；沙盒無憑證跑 `--pace`；再把 feed `ts` 改成逾 TTL | `feed_rate_limits`：feed 檔含 `rate_limits` 兩窗；`fallback_statusline`：`--pace` reason＝statusline-fallback；`stale_ignored`：逾 TTL 後不採用 feed |
| A31 | §4.3（PRD:2698）：PreCompact 可重啟點＋最短間隔 | RV-PX31 | C＋H | 沙盒 session 以真 `claude -p -r <sid> "/compact"` 壓縮兩次，間隔 <600 s | `restart_book`：第一次後任務書檔存在；`compact_event`：`autosdd_compact_events.jsonl` 新增一行；`interval_warn_only`：第二次只出聲、壓縮照做、hook rc 0 |
| A32 | §4.5.4（PRD:2699）：週軸 ≥ converge 一律 FRESH | RV-PX32 | S＋P＋K | 兩變體：converge 鍵設在真週軸讀數之下／之上 | `fresh_on_weekly`：前者選路 FRESH 且痕跡含週軸理由；`resume_below`：後者不因週軸改路 |
| A33 | §4.5.10（PRD:2700）：醒來付費探針 `claude -p "ok"` 牆鐘 ≤ `PROBE_WALL_SECONDS`（90 s；`resume_route.py:196,199`） | RV-PX33 | P＋E＋X | 互動路徑 `session_resume_planner.py --probe-quota --probe-command <X shim：睡 150 s>`（planner:937、1270）；E 對 T5 回 429 使 L0 回 None，逼出付費探針。WHY 不用 S：無人路徑 `probe_quota` 直接返回不探測（planner:498-501），90 s 上限那條路不會跑（SCG 第四次複審 P2） | `probe_shim_called_once`：shim 呼叫記錄恰 1 筆；`probe_wall_90_95`：shim 啟動到 planner 放棄的牆鐘落在 90～95 s；`probe_not_open`：結果不是 open（走量不到路徑） |
| A34 | §6.2 R-6.2-2（PRD:2702）：CLI 版本家族＋DRY_RUN | RV-PX34 | P＋X | 真引擎開機自檢兩次：真 `claude --version`；shim 回未知 minor | `known_family`：前者不 DRY_RUN、無通知；`unknown_minor_dryrun`：後者 DRY_RUN 且通知痕跡一筆 |
| A35 | §8 列 1（PRD:2703）：推論端 429 有界退避 | RV-PX35 | P＋X | shim 第一次輸出限流字樣＋`Retry-After: 3`、第二次正常；變體 `Retry-After: 900`（>上限 300） | `retried_same_attempt`：同 attempt 重跑 1 次且成功；`waited`：兩次呼叫間隔 ≥3 s 且 ≤3 s＋jitter 上限；`over_cap_halts`：變體走 halt |
| A36 | §8 列 12（PRD:2705）：無人窗口禁網路、禁安裝 | RV-PX36 | C＋H | 沙盒套 `settings.unattended.json`，真 `claude -p` 依提示各嘗試一次 `curl`、`WebFetch`、`pip install`，再跑一個已放行指令 | `deny_curl`、`deny_webfetch`、`deny_install`：逐字稿對應 tool_result 為拒絕；`allowed_ok`：已放行指令 rc 0 |
| A37 | §8 列 13（PRD:2706）：CLI 升級 | RV-PX34（改指，`refs` 加 §8 列 13） | P＋X | 同 A34 | 同 A34：`known_family`、`unknown_minor_dryrun` |
| A38 | §12 權限旗標（PRD:2707） | RV-PX38 | P | 真引擎 config 設 `permission_mode: bypassPermissions`（非容器）；另一次用出廠 config | `bypass_refused`：開機自檢拒絕並出聲；`default_not_bypass`：出廠 config 的 spawn 命令列不含 bypass |
| A39 | §12 寫入範圍（PRD:2708） | RV-PX39 | C＋H | `AUTOSDD_UNATTENDED=1` 下真 `claude -p` 依提示寫沙盒 repo `.git/HEAD`、沙盒 HOME 的 `~/.ssh/config`、`tools/lib/model_roles.py` 複本；再不設該變數重跑 | `gov_blocked`：三筆皆被 hook 拒絕（逐字稿 hook_blocking_error）；`attended_ok`：有人值守時寫入成功 |
| A40 | §12 日誌遮蔽（PRD:2709） | RV-PX40 | P＋X | shim 輸出含假金鑰樣式字串 | `secret_absent`：引擎 log 目錄命中 0；`redacted_marker`：log 含遮蔽標記 |
| A41 | §11.2（PRD:2712）：離線模擬器＋H1 重建 | RV-PX41 | P＋R | 真跑 `tools/probe/pacing_simulator.py --selftest`，並以本機真痕跡重建 H1 | `selftest_rc0`：rc 0；`h1_open_lt_close`：開遲滯 cap 變動次數 < 關遲滯；`h1_trace_copied`：案例開始先把 H1 痕跡（系統暫存，重開機即失；PRD:2712、`pacing_simulator.py:241-244`）複製進沙盒，讀不到即判 fail，不得以「不可得」通過 |
| A42 | §11.3（PRD:2713）：凍結 ≤5 s、kill -9、喚醒成本落帳 | RV-PX42 | P＋K | 真引擎行程，門檻鍵使讀數入 halt 帶；外部計時；變體寫入中 `taskkill /F` | `freeze_le_5s`：halt 到 checkpoint 落盤 ≤5 s（外部量）；`kill9_fallback`：回上一份有效版；`resume_cost_row`：resumed 窗後 `resume_cost` 落一行 |
| A43 | §11.7（PRD:2714）：多實例同帳號 | RV-PX43 | P | 兩個沙盒專案目錄各起真行程，對同一派發帳連搶 30 回合 | `sum_le_cap`：每回合成功總和 ≤ cap；`rounds`：回合數＝30 |
| A44 | §15.5 紅線 1～12（PRD:2716） | RV-PX44 | P＋E＋S＋C＋H＋X | 一個案例內依序跑各紅線的真觸發（「同 Axx」＝同載具在本案例內再跑一次，不引用他案結果）；紅線 5、7 依矩陣判 ➖，案例輸出寫明不判 | `rl1_get_only`：替身只見 GET、每 TTL ≤1 筆；`rl2_freeze`：halt 讀數 ⇒ cap 0、無超額路徑；`rl3_4_os_schedule`：`sessionctl park --at now＋5h` 的排程 NextRunTime 與 now＋5h 相差 ≤60 s；`rl6_degrade`：同 A04；`rl8_429`：同 A35 主變體；`rl9_bypass`：同 A38；`rl10_gov`：同 A39；`rl11_cli`：同 A34；`rl12_token`：同 A20 |
| A45 | 施工圖 A4（PRD:2717）：BurnDown 清倉授權 | RV-PX45 | P＋E | 沙盒 trace_dir 真跑 `tools/lib/quota_burndown.py --issue weekly_all --directive …`、`--status`、`--revoke`；再設 `AUTOSDD_QUOTA_BURNDOWN_OFF=1` 重跑 | `issue_status_rc0`：`--status` rc 0；`cap_raised`：`--pace` cap 上升；`revoke_restores`：撤銷後回原值；`kill_switch`：OFF 時 cap 不變 |
| A46 | §4.4.3（PRD:2719）：Agent 硬性預算三軸 | RV-PX46 | P＋C | 真引擎設 `claude.max_turns_per_step`＝3、`step_timeout_seconds`＝20；一步為真 `claude -p --model haiku`，另一步 sleep 60 | `max_turns_argv`：claude 子行程命令列含 `--max-turns 3`；`step_timeout`：sleep 步在 20 s＋寬限內終止並記 timeout |
| B01 | §16.6 2026-10-10（PRD:2784）：CLI 家族判定 | RV-PX47 | P＋X | shim 依序回同家族較高 patch、新 minor | `patch_family_ok`：前者不 DRY_RUN、無通知；`new_minor_dryrun`：後者 DRY_RUN 且通知 |
| B02 | §16.6 2026-10-11（PRD:2785）：env 跨機同步四層載入鏈 | RV-PX48 | P＋H | 沙盒四層（行程 env、`AutoClaude/.env`、根 `.env`、`env.shared`）放同一鍵不同值；真跑 `tools/lib/quota_policy.py --env-doctor` 與引擎設定載入；`AUTOSDD_UNATTENDED=1` 下真 hook 載具送一筆寫 `env.shared` 的 PreToolUse | `layer_order`：生效值依四層順序；`doctor_reports`：doctor 列出衝突鍵；`gov_protected`：寫 `env.shared` 被 hook 拒絕（rc 2） |
| B03 | §16.6 2026-10-14（PRD:2786）：halt 標記辨識他 session 接手 | RV-PX49（long） | S＋R | 沙盒 halt 標記，另一沙盒 session 逐字稿於標記後累積 ≥24 回合且 ≥600 s 活動，真哨兵巡邏 | `disarm_superseded`：`sentinel_decided` 理由含「接手」且 `cleared_halt=true`；`marker_removed`：halt 標記檔已移除 |

**本附錄判準**：CI 鎖 (f) 逐列比對本表與案例模組（REQ-WP-100）；E2E-WP-66 要求每列最近一次有效結果為 PASS 且證據含本表的全部斷言鍵。標「long」者另依 REQ-WP-99 宣告 `MIN_WALL_SECONDS`／`DESIGNED_WAIT_SECONDS`，並只認驅動器跑完的帳列。

## 11. 追加註記 r5（W5-FIX1，2026-11-23；只追加，不改既有條文）
**事故**：2026-11-22 14:46 整機重開機殺掉正在跑 RV-LW3 的 OIR 驅動器（OI-20261120-001），帳本只留 `start`；§1.1 REQ-WP-03 的「有 `start` 無 `attempt` 且逾 `start.ts＋budget_minutes` ⇒ undriven」要等 195 分才成立，完成閘約 4 小時後才發現。
- **REQ-WP-03／08 追加（執行者存活）**：driven 有效性在「有 `start` 無 `attempt`」時，另以 `start` 的 `pid`＋`proc_start` 對照現況；任一成立 ⇒ undriven，原因新值 `run_died`，立即生效、不等預算：(i) `start.ts` 早於本次開機時間；(ii) pid 不存在；(iii) pid 存在但建立時間與 `proc_start` 差超過 2 秒（pid 復用）。**量不到（開機時間／建立時間讀不到、`pid` 欄位缺）一律退回預算界**，不得把活驅動器判死。判準只用 ctypes／標準庫（完成閘不開子行程，DES §4.5）；載具＝`tools/lib/openitems/liveness.py`，注入點＝`fold(…, run_alive)`，呼叫端＝完成閘 `gate.load_state` 與 `openitems list`。`run_died` 不寫 `attempt`，故不計入 `attempts`／`deferrals`；重掛（`drive`）即接得上。
- **REQ-WP-27 追加（行內補寫）**：`run-driver` 在 `start` 之後以 `BaseException` 為界保證補寫 `attempt`：`KeyboardInterrupt`／`SystemExit` ⇒ `attempt(deferred, reason=interrupted)`（不耗重試預算）並重掛；其他例外 ⇒ `attempt(fail, reason=error:<類名>)`（計入 attempts，達上限同批 `escalate`）；補寫後原例外照常重拋（rc 1）。`reason` 集合追加 `interrupted`。被外力硬殺（關機、`taskkill /F`）行內補不到，由上一條對帳負責。`console_run` 逾時／中斷改殺整棵子行程樹（沿用 `realverify.sandbox.kill_tree`）。
- **AT-WP-50 追加 (e)(f)**：(e) 有 `start`、`budget`＝195、start 後 1 分、存活探針回「已死」⇒ undriven（`run_died`）；(f) 同 (e) 但探針回「量不到」⇒ driven（退回預算界）。(c)(d) 判決不變。
- **E2E-WP-46 修訂**：「殺後立即 `openitems list`：driven」改為「殺後立即 `openitems list`：undriven(run_died)、帳本末列為 `start`、完成閘 `load_state` 列出該 id」；「`start.ts`＋預算後 undriven」一段仍成立（存活探針量不到的平台的後備界）。正式案例由 S6 持有；開發棒的真行程 smoke＝`tools/tests/test_openitems_run_died.py::RealRunnerDeathE2ETest`（真子行程＋真 `taskkill /T /F`＋真 CLI）。
- 對應測試：`tools/tests/test_openitems_run_died.py`（`RunDiedFoldTest`／`StartAliveTest`／`DriverSealsAnAttemptTest`／`ConsoleRunKillsTheWholeTreeTest`／`RealRunnerDeathE2ETest`）。