# TCS-SessionSwitch-CostModel-20261118：換 session 改依快取成本＋主控／子代理保溫（需求＋驗收合一）

> 角色：SA（R216 Architect＋SA 合一棒）。設計全文＝`docs/02_architecture/SessionSwitch_CostModel_Design.md`（下稱 DES）；上游需求＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 PRD，修憲草案見 DES §8）。
> 命名照本目錄 `TCS-<模組>-<日期>.md`；不併入 TCS-SessionCtl／TCS-SessionPark／TCS-TokenWaste（已凍結的狀態對照帳），本案 AT 前綴 `AT-SS-`、E2E 前綴 `E2E-SS-`。
> **狀態（2026-11-19）**：已實作並收尾（R216 收尾窗口）。🔴 **掌舵者裁決（2026-11-18）優先於本檔全文**：不設軟線 `T_soft`、不做 hold 戳記、只留硬線 HARD——凡涉軟線／hold 的 REQ／AT／MU 一律標「依裁決不實作」、不再是待實作項；`waitfor` 單段上限由原稿的 240 改為 **255**（WHY：長前景閘擋線 270000 ms；等 270 秒需要的前景 timeout 會被擋線自己擋住，故上限取擋線以下的 255，預設仍 240）。park 選路（階段 3，REQ-SS-19）未實作。🔴 **量測端（WP-G：REQ-SS-20／21 的 M-K1～M-K6、`--replay-switch`、`--calibrate-switch`、AT-SS-50～52、E2E-SS-01／02／05）本輪未實作＝未結**，不得宣稱已有指標。真機自驗結果以 `docs/06_quality/RealVerify_Result_Ledger.md` 為準，未入帳者＝未結。
> 測試慣例沿用 sessionctl：時間注入 `now`、路徑圍籬 tmp、不讀本機真實 `~/.claude`（E2E 除外，見 §4）、不起真排程、不開測試用環境變數鉤（A-3）、禁用 skip。
> 🔴 掌舵者 2026-11-18 指令：每個功能都要有 E2E（真行程／真排程／真 `claude -p` 子行程／真逐字稿重放才算，單元測試不算）；待真機尾巴＝未完成。§4 逐功能列齊，做不到真機的以「替代 E2E」寫明並計入未結。

## 0. 模組落點表（照 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2；全部在既有 sessionctl／wastecensus 套件 glob 內）

| 元件 | 路徑 | §2 格 |
|---|---|---|
| 函式庫（新） | `tools/lib/sessionctl/costmodel.py`（純公式 F1／F4、參數解析；F3 軟線依裁決不實作）、`keepwarm.py`（截止錨點、保溫帳、n*、保溫閘、quota 閂鎖）、`longwait.py`（runlong／waitfor 本體、長前景閘判準）；`hold.py` 依裁決不實作 | 模組套件（既有 sessionctl） |
| 函式庫（改） | `sessionctl/switch.py`（鍵登記、`fresh_reasons` 改 F4、R3 退役）、`seal.py`（T_soft／HARD／hold）、`converge.py`（HARD 去出聲前提、Stop 合成加保溫閘、冷叫醒閘豁免）、`watch.py`（錨點、閂鎖、處置表文字）、`forward.py`（F4）、`handoff.py`（`advise_once` 門檻）、`park_cli.py`（階段 3）、`tools/lib/quota_policy_env.py`（`ENV_SPEC` 新鍵與出廠值） | 既有家 |
| 量測（新／改） | `tools/lib/wastecensus/sections_keep.py`（新：M-K1～M-K6、`--replay-switch`、`--calibrate-switch`）、`report.py`（旗標） | wastecensus 套件 |
| 入口薄殼 | `tools/sessionctl.py`（+`keepwarm`、`hold`、`runlong`、`waitfor` 分派）；`tools/probe/waste_census.py` 不改 | 指令入口 |
| 守衛面（主控親套） | `.claude/hooks/sessionctl_guard.py`（PreToolUse PowerShell／Bash 分支呼叫 `longwait.pretool_verdict`）、`.claude/settings.json`（matcher 增 PowerShell／Bash） | 守衛面 |
| 測試 | `tools/tests/test_sessionctl_costmodel.py`、`test_sessionctl_keepwarm.py`、`test_sessionctl_longwait.py`（新；`test_sessionctl_hold.py` 依裁決不實作）；增量 `test_sessionctl_switch.py`、`test_sessionctl_converge.py`、`test_sessionctl_handoff.py`、`test_sessionctl_watch*.py`、`test_sessionctl_hooks.py`、`test_waste_census_metrics.py`；E2E `tools/tests/test_sessionctl_costmodel_e2e.py`（新） | 測試 |
| 規格 | DES；本檔；PRD 修憲（收尾窗口）；ADR-XPLAT-004 §2.19（收尾窗口） | 02／03／01／04 |

## 1. 需求（REQ）

| REQ | 內容 | DES | 階段 |
|---|---|---|---|
| REQ-SS-01 | 成本公式 F1／F4 為純函式；參數全由 `ENV_SPEC` 解析（DES §3.2 出廠值），壞值退出廠值並出聲；（`T_soft` 由 F3 推導的部分 **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**；`AUTOSDD_SWITCH_R1_CTX_TOKENS` 退役、有設只出聲「已退役」） | §3 | 1 |
| REQ-SS-02 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**（原：不變式 `T_soft < HARD`）；實作面只留「HARD 須低於觀測到的流程內 autocompact 最小點」 | §4.4 | 1 |
| REQ-SS-03 | `sessionctl keepwarm`：截止＝主控最後一筆帶 usage 的 assistant 記錄＋`T_kw`（45 分），每 60 秒重讀尾端延後；末行 `KEEPWARM_VERDICT=ping|cap …`、rc 6／7；判決行前印處置表對應列 | §4.1 | 2 |
| REQ-SS-04 | 保溫帳 `trace_dir()/keepwarm/<sid>.json`：`pings` 每次 ping 判決 +1；本 session 出現可轉送真人提示即歸零；`n*`＝F1 | §4.1 | 2 |
| REQ-SS-05 | 不掛條件：無人窗口、模式非 auto、`AUTOSDD_KEEPWARM_OFF`、已交棒、park 標記有效、ctx < `KEEPWARM_MIN_CTX`；指令在這些條件下 rc 0 印 `KEEPWARM_VERDICT=skip reason=…` 立即結束（不得常駐） | §4.1 | 2 |
| REQ-SS-06 | Stop 保溫閘：無 running 背景任務 ∧ 非 REQ-SS-05 各條 ∧ `pings < n*` ⇒ 推回一次；`stop_hook_active` 放行；與封存閘／park 合併一則，次序 封存→park→keepwarm | §4.1、§5 D6 | 2 |
| REQ-SS-07 | 冷叫醒閘：已交棒 ⇒ 全部背景任務照舊要求 TaskStop；只封存未交棒 ⇒ `sessionctl.py keepwarm` shell 不計入 | §4.1 | 2 |
| REQ-SS-08 | watch 保溫條件改用 REQ-SS-03 的同一錨點函式 | §4.2 | 1 |
| REQ-SS-09 | watch quota 閂鎖：鍵 `(sid, reset 分鐘, 帶級)`；同鍵不再觸發；帶升級或 reset 改變再觸發；讀／寫失敗 ⇒ 觸發＋stderr 出聲；處置表 quota 列文字更新 | §4.3 | 1 |
| REQ-SS-10 | `sessionctl runlong --out <f> -- argv…`：子行程結束後原子寫 `<f>.done`（rc、結束時刻）；子行程 stdout／stderr 落 `<f>`（UTF-8） | §4.5 | 2 |
| REQ-SS-11 | `sessionctl waitfor --done <f>.done --max-sec S`（預設 240；S ≤ 255，超過夾到 255 並出聲；WHY 不是 270：見狀態列）：完成 rc 0 印尾端 40 行＋`WAITFOR_VERDICT=done rc=<子行程 rc>`；未完成 rc 3 `WAITFOR_VERDICT=pending`；參數錯 rc 2 | §4.5 | 2 |
| REQ-SS-12 | PreToolUse 長前景閘：payload 有 `agent_id` ∧ 工具 PowerShell／Bash ∧ 非背景 ∧ `timeout > 270000` ⇒ rc 2＋指路；行內 `# keepwarm-ok: <WHY>` 豁免（`AUTOSDD_UNATTENDED` 下無效）；主控（無 `agent_id`）不判；解析失敗放行 | §4.5 | 2 |
| REQ-SS-13 | 封存閘門檻：ctx ≥ HARD；（原稿的 T_soft／hold 分支 **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**）其餘前提同現行（無在飛代理、未交棒、封存無效） | §4.4、§5 D3／D4 | 2 |
| REQ-SS-14 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**：`sessionctl hold`（原稿：H ≤ 12、W ≥ 8 字、自帶到期）——hold 沒有作用對象（硬線本來就不受 hold 影響） | §4.4 | 2 |
| REQ-SS-15 | 收斂閘（PreToolUse 派工擋）：ctx ≥ HARD 即擋，不再要求「已出聲」；HARD 出廠 850,000 | §4.4、§5 D12 | 2 |
| REQ-SS-16 | `advise_once` 出聲門檻＝HARD（`fresh_reasons(advise=True)`；原稿的 T_soft／hold 分支 **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**） | §4.4 | 2 |
| REQ-SS-17 | `fresh_reasons`：快取熱 ⇒ 不判 F4；冷 ⇒ `W_CC1·c > F(1+q)` 命中；R2 保留；R1／R3 不再命中，鍵有設時理由清單附「已退役」說明 | §4.4、§5 D10 | 2 |
| REQ-SS-18 | 轉送條件加 F4：冷 ∧ 已封存 ∧ `W_CC1·c > F(1+q)` 才轉送；否則放行並 `show` 一行原因 | §5 D9 | 2 |
| REQ-SS-19 | park job 選路依 F4：RESUME（`claude -r <sid>`）或 FRESH（現行 handoff.spawn） | §4.6 | 3 |
| REQ-SS-20 | waste_census 新欄 M-K1～M-K6；`--replay-switch` 重現 DES §7 全表；`--calibrate-switch` 印 F、B、N_lo、P_fix 建議值（讀逐字稿＋`autosdd_resume_cost.jsonl`） | §2、§7 | 1 |
| REQ-SS-21 | 痕跡事件具名常數：`keepwarm_verdict`、`keepwarm_stop_block`、`watch_quota_latched`、`longwait_block`、`hold_set`；wastecensus 端同名常數由測試斷言相等（不互 import） | §9 | 1～2 |

## 2. PRD 追溯表

| REQ | PRD 條文座標（2026-11-18 行號） | 關係 |
|---|---|---|
| REQ-SS-01、02 | §1.2 原則 6（line 139）、§2 `K_ctx`（line 162）、§2 關鍵釐清（line 169～171） | 新增第三軸「快取成本軸」，不觸發壓縮；修憲補「換 session」的依據（DES §8.1） |
| REQ-SS-03～07 | §1.2 原則 2（line 130～132）、§4.5.7 R-4.5.7-1（line 1239～1246） | 保溫回合≠遙測（就地註記）；補主控閒置盲區的快取面 |
| REQ-SS-08、09 | §1.2 原則 5（line 137～138）、§4.5.7 R-4.5.7-2（line 1248～1254，prepare 帶提醒語意） | 閂鎖失效往保守（觸發）；prepare 帶只提醒一次而非每次輪詢 |
| REQ-SS-10～12 | §4.5.4 成本盲點（line 1127） | 同一成本盲點在子代理 5m TTL 的版本 |
| REQ-SS-13～16 | §4.3（line 998～1022，尤其 line 1022 交棒路線）、§6 區塊 5（line 1893～1899） | HARD＝autocompact 前交棒；84／94 百分比尺不動 |
| REQ-SS-17、18、19 | §4.5.4 AUTO 判準（line 1137～1144，含 C6）、§15.6（line 2593）、§15.7 第 5 點（line 2611～2612） | AUTO 由「依對話規模」改「依成本」；位元組上限保留兜底；weekly→FRESH 維持未實作 |
| REQ-SS-20 | §9 `autoclaude_resume_cost_pp`（line 2325）、§11.3 v2.1.16 落款（line 2377～2382）、§15.7（line 2597～2614） | `resume_cost.jsonl` 為校準來源 |
| 全案 | §16.5 (i)（line 2765）、§16.6（line 2773～2781）、修訂表（line 3～26） | 修憲走 (i)；修訂表 v2.1.22 列、§16.6 列、四處就地註記全文見 DES §8.2～8.4 |

## 3. 驗收測試（AT；單元／整合，縫注入）

縫代號：`NOW`＝`now`；`FS`＝tmp 圍籬（含 `trace_dir`）；`ENV`＝env mapping；`TR`＝合成或真實截取的逐字稿檔；`Q`＝假額度讀取；`PL`＝Stop／PreToolUse payload dict；`RUN`＝假 runner。

### 3.1 成本模型（`test_sessionctl_costmodel.py`）

| AT | 輸入 | 預期 |
|---|---|---|
| AT-SS-01 | 出廠參數 | `t_soft()==534000` 部分 **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**；`fresh_is_cheaper(c=480000, cold=True)` 為假、`c=480001` 為真（F4 邊界） |
| AT-SS-02 | `n_star(400000)` / `n_star(150000)` / `n_star(30000)` | 9 / 8 / 5（F1：`floor(2c/(0.2c+4500))`）；W_CC1 誤用 1.25 的突變必紅 |
| AT-SS-03 | `n_star_sub(400000)` | 12（F2） |
| AT-SS-04 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**（原：`ENV` 設 R1 只准下修推導的 T_soft）；實作面改驗：R1 有設 ⇒ 只出聲「已退役」、不影響任何判準 | |
| AT-SS-05 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）** | — |
| AT-SS-06 | q=0 / q=1 / q=2 | F4 門檻＝240,000／480,000／720,000（t_soft 342,000／534,000／726,000 部分 **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**） |
| AT-SS-07 | 壞值（負數、非數字、q=NaN） | 退出廠值並出聲；不拋 |

### 3.2 keepwarm（`test_sessionctl_keepwarm.py`）

| AT | 輸入 | 預期 |
|---|---|---|
| AT-SS-10 | TR 最後 usage 記錄 T0；NOW=T0+44:59 | 未到期；T0+45:00 ⇒ `ping`、rc 6 |
| AT-SS-11 | 執行中 TR 追加一筆 T1 的 assistant usage | 截止延到 T1+45；不得以啟動時刻為錨（錨 started_at 的突變必紅） |
| AT-SS-12 | 保溫帳 pings=n*−1，再 ping | 判決 `cap`、rc 7；處置表列含「不重掛」 |
| AT-SS-13 | 保溫帳 pings=3，TR 出現可轉送真人提示 | 歸零；`<task-notification>` 不歸零 |
| AT-SS-14 | REQ-SS-05 六種條件逐一 | rc 0、`KEEPWARM_VERDICT=skip reason=<對應>`、1 秒內結束 |
| AT-SS-15 | Stop PL：無背景任務、ctx 400,000、可保溫 | 保溫閘推回，文字含 `sessionctl.py keepwarm`；`stop_hook_active=True` ⇒ 空 |
| AT-SS-16 | Stop PL：同上但 background_tasks 有 running shell（任意） | 不推回 |
| AT-SS-17 | Stop PL：ctx 600,000、未封存、可保溫 | 合併一則：封存閘在前、保溫閘在後 |
| AT-SS-18 | 冷叫醒：已封存未交棒＋running keepwarm shell | 不推回；已 spawn＋running keepwarm ⇒ 推回（豁免誤套到交棒的突變必紅） |
| AT-SS-19 | 半路停工判準（`midwork`）：最後回覆自述「保溫中」＋keepwarm running | 不推回（回歸） |

### 3.3 watch（增量 `test_sessionctl_watch*.py`）

| AT | 輸入 | 預期 |
|---|---|---|
| AT-SS-20 | quota_fn 恆真（prepare、reset R）；連續兩次 `run` | 第一次 rc 5；第二次不因 quota 結束（以 keepwarm／all_done 結束），痕跡有 `watch_quota_latched` |
| AT-SS-21 | 閂鎖存在（prepare,R）；quota 升 halt | 再觸發 rc 5 |
| AT-SS-22 | 閂鎖存在（prepare,R）；reset 變 R+5h | 再觸發 |
| AT-SS-23 | 閂鎖檔壞 JSON／不可寫 | 觸發 rc 5＋stderr 出聲 |
| AT-SS-24 | keepwarm 錨點：watch 啟動於 T0+10，主控最後記錄 T0 | 於 T0+45 判 keepwarm（不是 T0+60） |

### 3.4 長等待（`test_sessionctl_longwait.py`）

| AT | 輸入 | 預期 |
|---|---|---|
| AT-SS-30 | runlong 跑 `python -c "import sys;print('中');sys.exit(3)"` | `<f>` 含「中」（UTF-8）；`<f>.done` 記 rc 3；`.done` 在 `<f>` 寫完後才出現 |
| AT-SS-31 | waitfor：done 不存在、max-sec=1 | rc 3、`pending`；done 存在 ⇒ rc 0、`done rc=3` |
| AT-SS-32 | waitfor `--max-sec 600` | 夾到 255（上限）＋出聲 |
| AT-SS-33 | PreToolUse PL：agent_id、PowerShell、timeout 300000、非背景 | rc 2，訊息含 `runlong` 與 `waitfor` |
| AT-SS-34 | 同上 timeout 270000 ／ 背景 ／ 無 agent_id ／ Read 工具 | 放行（邊界 270000 放行、270001 擋） |
| AT-SS-35 | 同 AT-SS-33 加行尾 `# keepwarm-ok: 一次性下載大檔無法分段` | 放行；`AUTOSDD_UNATTENDED=1` ⇒ 仍擋 |
| AT-SS-36 | PL 缺 tool_input／timeout 非數字 | 放行 |

### 3.5 換窗（增量 `test_sessionctl_converge.py`、`test_sessionctl_handoff.py`、`test_sessionctl_switch.py`；`test_sessionctl_hold.py` 依裁決不實作）

| AT | 輸入 | 預期 |
|---|---|---|
| AT-SS-40 | Stop：ctx 300,000、無在飛代理、未封存 | 不推回（舊 R1 會推回；保留舊門檻的突變必紅） |
| AT-SS-41 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**（原：ctx 534,000＝軟線推回、有效 hold 不推回）；實作面：ctx 534,000 ⇒ 不推回（只有硬線推回） | |
| AT-SS-42 | Stop：ctx 達硬線 HARD | 推回（hold 不存在；硬線無任何豁免） |
| AT-SS-43 | PreToolUse Agent：ctx 850,000、**未出聲** | rc 2；849,999 ⇒ 放行 |
| AT-SS-44 | `advise_once`：ctx 300,000 ⇒ 不出聲；達硬線 ⇒ 出聲（534,000 出聲與 hold 分支 **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**） | |
| AT-SS-45 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）** | |
| AT-SS-46 | `fresh_reasons`：冷、c=479,999 ⇒ 無 F4 命中；480,001 ⇒ 命中；熱、c=800,000 ⇒ 不命中 | |
| AT-SS-47 | `fresh_reasons`：上次續跑寫入 150,000（舊 R3 命中情境）、c=170,000、冷 | 不命中；設了 R3 鍵 ⇒ notes 含「R3 已退役」 |
| AT-SS-48 | 轉送：已封存、冷、c=400,000 | 放行＋`show` 含原因；c=600,000 ⇒ 轉送 |

### 3.6 量測（增量 `test_waste_census_metrics.py`）

| AT | 輸入 | 預期 |
|---|---|---|
| AT-SS-50 | 合成逐字稿：閒置 56 分後 auto 壓縮一次 | M-K2＝1；閒置 3 分的 auto 壓縮不計 |
| AT-SS-51 | 合成：keepwarm 叫醒鏈 3 次 | M-K5 計入三鏈加權單位 |
| AT-SS-52 | 事件名常數兩邊相等（REQ-SS-21） | |

## 4. 逐功能 E2E 覆蓋表（真行程／真逐字稿重放／真 `claude -p`；單元測試不算）

| 功能 | E2E | 載具 | 斷言 | 不可達時的替代與未結標記 |
|---|---|---|---|---|
| F4／F3 判準與重放 | E2E-SS-01 | 真行程 `python tools/probe/waste_census.py --replay-switch --since-days 14`，讀本機真實逐字稿 | 印出 DES §7 各列；P1 改變決定件數、P3 FRESH 件數與 DES 同母體重跑一致（母體變動時只斷言公式一致：以同一份 `turns` 快照 JSON 重放兩次結果相同） | CI 無真逐字稿 ⇒ CI 跑快照 JSON（從真逐字稿抽出、去內容只留 usage／時間戳），本機跑全量 |
| 校準 | E2E-SS-02 | 真行程 `--calibrate-switch`，讀真逐字稿＋真 `autosdd_resume_cost.jsonl` | F 建議值落在 p25～p75（DES §1.4） | 同上 |
| keepwarm 指令 | E2E-SS-03 | 真行程 `python tools/sessionctl.py keepwarm --sid X --projects-dir <tmp> --min 1`（`--min` 為正式 CLI 參數，下限 1、<15 出聲）；tmp 放**真實逐字稿截取**（usage 與時間戳原樣、內容去除） | 約 60 秒後 rc 6、末行 `KEEPWARM_VERDICT=ping`；期間另一行程追加 assistant 記錄 ⇒ 延後 | — |
| keepwarm 真機效果（主前提） | E2E-SS-04 | 真 `claude -p --model haiku` 子行程三次：t0 建 session（上下文≥4,096 token 以啟用快取）、t0+45 分 `-r` 輕觸、t0+100 分 `-r` | 第三次 `cache_read ≥ 0.9×前一回合上下文`；對照組（不輕觸、t0+70 分）`cache_read < 0.1×` | 若 `-p` 模式的快取層不是 1h（以 usage 的 `ephemeral_1h_input_tokens` 判），改量 5m 版本（4 分輕觸 vs 7 分）並標「1h 層待互動真機 V-SS1」，**計未結** |
| 閒置自動壓縮被擋 | E2E-SS-05 | 真逐字稿重放：`waste_census` M-K2 對上線後 14 天 | M-K2＝0 | 上線前不可達；上線 14 天後由 SI 巡邏或主控收尾跑一次，**計未結**直到跑過 |
| Stop 保溫閘／封存閘／冷叫醒閘豁免 | E2E-SS-06 | 真 hook 行程：以 `.venv` 載具執行 `.claude/hooks/sessionctl_guard.py`，stdin 餵 harness 真實 Stop payload 形態（含 `background_tasks`）＋真實逐字稿截取 | AT-SS-15～18 四情境的 stdout JSON（`decision:block` 與否、reason 字樣） | — |
| PreToolUse 長前景閘 | E2E-SS-07 | 同上載具，餵真實子代理 PreToolUse payload（從真逐字稿取 `agent_id`、`tool_input.timeout` 形態） | rc 2／0 對應 AT-SS-33～35 | — |
| 子代理分段等待 | E2E-SS-08 | 真 `claude -p --model haiku` 主控，提示派一支前景子代理（`model: haiku`）用 `runlong` 跑 `python -c "import time;time.sleep(420)"` 並以 `waitfor --max-sec 240` 等待 | 子代理逐字稿：相鄰回合間隔皆 < 300 秒；`waitfor` 回合 `cache_read ≥ 0.9×前回合上下文`；`.done` rc 0 | print 模式背景上限 10 分鐘：本案用前景子代理＋總長 < 9 分；若 harness 擋，**計未結**並改互動真機 V-SS2 |
| watch quota 閂鎖 | E2E-SS-09 | 真行程兩次 `python tools/sessionctl.py watch --sid X --grace-sec 5 --poll-sec 1`，`AUTOSDD_TRACE_DIR`＝tmp，額度快取放真實格式快照（prepare 帶、reset 未來） | 第一次 rc 5；第二次 rc 0（all_done）且非 5；把快照改 halt 後第三次 rc 5 | — |
| hold | E2E-SS-10 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）** | — | 不適用（無作用對象，不計未結） |
| 收斂閘 HARD | E2E-SS-11 | 真 hook 行程 PreToolUse Agent，真逐字稿截取 ctx 850,000 | rc 2 | — |
| 轉送 F4 | E2E-SS-12 | 真 hook 行程 UserPromptSubmit，真逐字稿截取＋已封存交接包；以 `AUTOSDD_SESSION_SWITCH_MODE=notify` 走條件 7 路（不 spawn）驗 F4 前段；spawn 本體沿用 TCS-SessionCtl 既有 E2E | c=400k 放行且 `systemMessage` 含原因；c=600k 達條件 7 | spawn 全路徑沿用既有 V-F1（未結照舊） |
| 無人續跑選路 F4 | E2E-SS-13 | 真行程 `python tools/session_resume_planner.py` 的選路預演（既有 `--dry-run`／`--check` 類旗標；SD 現查）餵真逐字稿 | 冷＋c=170k ⇒ RESUME（舊 R3 判 FRESH） | 若 planner 無預演旗標，SD 不得新增測試專用旗標；改以真 `claude -p` 無人窗口一次（haiku、小上下文）驗，**計未結**直到跑過 |
| park 選路（階段 3） | E2E-SS-14 | 真排程：`sessionctl park` 以 `--at <now+2 分>` 登記，真 schtasks 觸發 `park --fire` | c 小 ⇒ 以 `-r` 續原 sid（新逐字稿行附加於原檔）；c 大 ⇒ 開新 sid | macOS／Linux 只印手動指令（既有劃界）；Windows 實跑 |

## 5. SD 工作包（鎖持有面；鐵律七：常數／史料／消費端不在同一持有面者不得並行）

| WP | 內容 | 常數住 | 史料（測試／快照）住 | 消費端住 | 依賴／並行 |
|---|---|---|---|---|---|
| WP-0 | 查證（唯讀）：閒置 55 分自動壓縮的官方說法、子代理 TTL 可否設 1h、`claude -p` 快取層；結果寫 `docs/06_quality/CrossPlatform_R216_*_Evidence.md` | — | 證據檔 | — | 可與 WP-A 並行（零檔案重疊） |
| WP-A | `costmodel.py`＋`ENV_SPEC` 新鍵＋`switch.py` 鍵登記（`_DOWNWARD_ONLY` 等） | `tools/lib/quota_policy_env.py`、`sessionctl/switch.py` | `test_sessionctl_costmodel.py`、`test_quota_policy*.py`（`--print-env-example` 快照若有） | 暫無（後續包） | 先行；單人 |
| WP-G | `wastecensus/sections_keep.py`、`report.py` 旗標、E2E-SS-01／02 | 讀 `costmodel` 常數（不 import sessionctl 以外的守衛碼；若 A-8 禁止反向 import，則以數值常數重複並由測試斷言相等） | `test_waste_census_metrics.py`、快照 JSON | `waste_census.py` 入口 | WP-A 後；與 WP-C 並行（檔案零重疊） |
| WP-C | watch 閂鎖＋錨點；`keepwarm.py` 的 `deadline()`、`quota_latch()` 兩函式 | `sessionctl/keepwarm.py`（新）、`watch.py` | `test_sessionctl_watch*.py` | `watch.py` | WP-A 後；**keepwarm.py 首建者**，WP-B 必須在其後 |
| WP-B | keepwarm 指令、保溫帳、保溫閘、冷叫醒閘豁免、`sessionctl.py` 分派 | `keepwarm.py`、`supervise.py`（監督憑證改以 `_WATCH_CMD_RE` 容忍路徑後引號，DEF-200-615；`WATCH_CMD_MARK` 字面常數已刪除） | `test_sessionctl_keepwarm.py`、`test_sessionctl_converge.py` | `converge.py`、`seal.py`（`wake_package`）、`tools/sessionctl.py` | WP-C 後串行（同檔 keepwarm.py／converge.py） |
| WP-D | runlong／waitfor、長前景閘、`sessionctl.py` 分派、hook 接線 | `longwait.py`（閾值 270000、240） | `test_sessionctl_longwait.py`、`test_sessionctl_hooks.py` | `.claude/hooks/sessionctl_guard.py`、`.claude/settings.json`（主控親套）、`tools/sessionctl.py` | WP-B 後串行（同檔 `tools/sessionctl.py`、`sessionctl_guard.py`） |
| WP-E | HARD（T_soft／hold 依裁決不實作）、R1／R3 退役、`fresh_reasons` F4、轉送 F4、`advise_once` | `costmodel.py`（讀） | `test_sessionctl_switch.py`、`test_sessionctl_handoff.py`、`test_sessionctl_converge.py` | `seal.py`、`converge.py`、`switch.py`、`forward.py`、`handoff.py`、`tools/sessionctl.py` | WP-D 後串行（`converge.py`、`switch.py`、`sessionctl.py` 重疊） |
| WP-F | park 選路（階段 3） | `park_cli.py` | `test_sessionctl_park.py` | `park_cli.py`、`engine_resume_job.py`（若需） | WP-E 後 |
| WP-H | 收尾單人窗口：ADR §2.19、CLAUDE.md、PRD 修憲（DES §8）、缺陷帳本 DEF（watch quota）、Root_Layout 登記、`tools/tests` 棘輪重釘、`.env.example` 生成 | — | — | — | 最後；淨減法（R3 出廠移除）在此包 |

並行只允許：{WP-0, WP-A}、{WP-G, WP-C}。其餘串行（`tools/sessionctl.py`、`converge.py`、`sessionctl_guard.py` 三個熱點檔）。守衛面檔（`sessionctl/**`、`.claude/**`）的改動成品由主控親套（根 CLAUDE.md〈權限姿態〉）。

## 6. QA 突變點（Opus 獨立審查必跑；每點須有至少一個 AT／E2E 殺掉）

| # | 突變 | 應殺死者 |
|---|---|---|
| MU-01 | F1 用 `W_CC5` 取代 `W_CC1` | AT-SS-02 |
| MU-02 | F1 保溫成本漏乘 2（只算一回合讀取） | AT-SS-02 |
| MU-03 | F3 漏 `(1+q)` | AT-SS-06（F3／軟線 **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）**；F4 的 `(1+q)` 由 AT-SS-46 殺） |
| MU-04 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）** | — |
| MU-05 | keepwarm 截止錨 `started_at` | AT-SS-11、AT-SS-24 |
| MU-06 | 截止 45→55 分 | AT-SS-10 |
| MU-07 | 真人提示不歸零保溫帳／`<task-notification>` 也歸零 | AT-SS-13 |
| MU-08 | 冷叫醒豁免套到已交棒 | AT-SS-18 |
| MU-09 | 保溫閘不看既有 running 背景任務 | AT-SS-16 |
| MU-10 | 閂鎖鍵漏帶級 | AT-SS-21 |
| MU-11 | 閂鎖鍵漏 reset | AT-SS-22 |
| MU-12 | 閂鎖讀失敗時吞事件 | AT-SS-23 |
| MU-13 | 長前景閘 `>` 改 `>=` 或 270000→300000；waitfor 上限 255→270 | AT-SS-34、AT-SS-32 |
| MU-14 | 長前景閘對主控也判 | AT-SS-34 |
| MU-15 | 無人窗口認行內豁免 | AT-SS-35 |
| MU-16 | runlong 先寫 `.done` 再 flush 輸出 | AT-SS-30 |
| MU-17 | 封存閘仍用 250,000 | AT-SS-40 |
| MU-18 | **依掌舵者裁決不實作（2026-11-18，DES §11 D-1＝③ 不設軟線、D-2＝hold 不實作）** | — |
| MU-19 | 收斂閘保留「須先出聲」 | AT-SS-43 |
| MU-20 | `fresh_reasons` 對熱快取也判 F4 | AT-SS-46 |
| MU-21 | R3 仍生效 | AT-SS-47 |
| MU-22 | 轉送 F4 不等式反向 | AT-SS-48 |
| MU-23 | M-K2 閒置窗 50～60 分改成任何閒置 | AT-SS-50 |

QA 另驗：DES §7 重放數字以 E2E-SS-01 重跑（不得採信 DES 內數字）；保溫成本 M-K5 是否確實入帳（不可只報命中率）。

## 7. 真機驗證（互動視窗；未驗＝未結）

| V | 內容 | 判準 |
|---|---|---|
| V-SS1 | 互動主控閒置 3 小時（掛 keepwarm）後回來 | 回來第一回合 `cache_read ≥ 0.9×上下文`；期間無 auto 壓縮；保溫回合輸出 ≤50 token |
| V-SS2 | 互動主控派背景子代理跑 >5 分測試（照 runlong／waitfor） | 子代理逐字稿無 >300 秒間隔、無重寫 |
| V-SS3 | prepare 帶內掛 watch 兩次 | 第二次不立即 rc 5（真機缺陷回歸） |
| V-SS4 | 畫面目視：保溫閘、長前景閘的訊息顯示 | 文字可見、繁中 |

## 8. 禁止事項（SD／QA 任務書必帶）

不准新增測試專用環境變數鉤；不准 skip；不准放寬既有守衛判準以讓新測試通過；不准 `--no-verify`；E2E 的真 `claude -p` 一律 `--model haiku` 且單案 token 上限寫進測試檔頭（預估：E2E-SS-04 約 3 萬、E2E-SS-08 約 5 萬）；並行包禁寫帳本、禁 git 寫入。
