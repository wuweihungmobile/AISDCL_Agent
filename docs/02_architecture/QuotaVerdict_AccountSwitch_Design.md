# 單一權威額度判決與換帳號作廢設計（QuotaVerdict／AccountSwitch Design）

- 版本：v1.0（SD-0，2026-11-25；規格階段，實作未開始）
- 上游：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 修訂表 v2.1.28、§4.1.6（R-4.1.6-1～8）、§4.1.7（R-4.1.7-1～6）、§15.5 紅線 14、§4.1.4／§4.2.3【v2.1.24】／§4.5.10／§4.5.11 的【v2.1.28 註記】、§16.6 2026-11-25 第一列。
- 驗收：`docs/03_testing/contracts/TCS-Autopilot-20261125.md`（REQ-AP-QV-01～08、REQ-AP-AC-01～04）。
- 兄弟設計：`docs/02_architecture/Autopilot_Pipeline_Design.md`（合入、推送、棘輪、CI、舊視窗、詢問類別閘、測試圍籬；〈外部限制〉全文住那裡，本檔 §2 只摘與額度有關者）。
- 先例與被消費的設計：`docs/02_architecture/QuotaWall_CacheContinuity_Design.md`（額度牆計畫 `qw_plan`、閂鎖、保溫）、`docs/02_architecture/Control_Handover_Design.md`（park 等待期間額度提前恢復、`parkprobe.account_changed`）。

**為什麼另立一份、不併入 `Control_Handover_Design.md`**：Control_Handover 管的是「誰在控制背景代理、何時換手」（控制面），本檔管的是「額度現在准許做什麼」（判決面）。兩者的消費關係是單向的（控制面讀判決），併在一起會讓 128 KB 的控制面文件再承擔一條獨立的判準鏈，審查時無法單獨凍結。QuotaWall 設計是本檔的**輸入**（`qw_plan` 是判決函式的一個參數），也不併入。

---

## 0. 一頁結論

1. 停工、park、續跑、等重置、可派數五類決定，全部由 `tools/lib/sessionctl/qv_verdict.py` 的純函式 `verdict()` 一次算出，輸出唯一動作（`CONTINUE｜NODISPATCH｜WAIT_RESET｜PARK｜HALT_WEEKLY`）與一行 `QUOTA_VERDICT=`。watch、park、`--pace`、SessionStart 簡報、Stop 停工推回、哨兵、PreToolUse 擋派全部只讀這一行（R-4.1.6-2）。
2. 判決帶 `expires_at＝min(measured_at＋180 s, 短窗 reset)`，過期一律重算（R-4.1.6-3）；87%＋距重置 14 分 ⇒ `WAIT_RESET`，不是 `PARK`（R-4.1.6-4）。
3. park 的 `--why` 退役，改 `--next-est <pp>` 進判決（R-4.1.6-5）；halt 標記不再壓住補量（R-4.1.6-6）。
4. halt／rush／閂鎖／保溫帳全部綁 `account_key`；三個零 API 觸發器發現「帳號可能已變」⇒ 補量 ⇒ 指紋不符即作廢舊標記（改名保留）並出聲（§4.1.7）。
5. 落點：住 `tools/lib/sessionctl/` 套件（不另立 `quotaverdict` 套件，WHY 見 §8）。LOC 牆四處（planner 750/750、`quota_messages` 400/400、`quota_gate` hub 496/500、`session_brief` 398/400、`context_budget_guard` special 1104/1104）各有具體抽出清單（§9）。

---

## 1. 立案證據座標（全部當場重查過，見 AP-A 報告 §1；本檔只列座標）

| # | 現象 | 座標 |
|---|---|---|
| E1 | 同一則 `--pace` 輸出自相矛盾（「🔴 halted…沒有新鮮快取可讀」與 `QUOTAWALL_PLAN … R=94.0`） | 逐字稿 sid `406454ea-91fc-4481-9c11-b28ed7d9e95f` L2447 |
| E2 | 同一則 watch 輸出自相矛盾（`QUOTAWALL_PLAN stage=free D=14` 與 `WATCH_VERDICT=quota`「封存→park」） | `watch9.log` 03:46:20 +08；`quota_burn.jsonl` 03:46:19（five_hour 87%）、04:00:32（0%） |
| E3 | halt 標記不帶帳號，/login 後仍生效 | `~/.autosdd/traces/halt_406454ea-….json`（at 21:32:50 +08，無帳號欄）；逐字稿 L173（/login 21:36:47）、L210（仍印舊帳號讀數） |
| E4 | park 正確拒絕後被 `--why` 推翻 | 逐字稿 L2504（rc 4）→ L2508（`--why` 登記）；`tools/lib/sessionctl/park_reset.py` `resolve()` 的 `why_ok` 分支 |
| E5 | 5.5 小時前的判決被當成現況 | `watch9.log` 03:46 對逐字稿 L2445（09:21） |
| E6 | 主控以原始讀數自拼「已重置」結論 | 逐字稿 L2553、L2564 |
| E7 | 換帳號後 7 小時無新帳號讀數 | `quota_burn.jsonl` 20:50（`account=34cd3507237f`）→ 03:43（`account=eaf5241f6fe2`） |

---

## 2. 外部限制（與本檔有關者；全文見 Autopilot 設計〈外部限制〉）

SD-0 於 2026-11-25 經 `claude-code-guide` 子代理查官方文件（`code.claude.com/docs/en/hooks.md`、`authentication.md`）：

| 事實 | 官方原文（節錄） | 對本設計的影響 |
|---|---|---|
| `/login` 沒有專屬 hook 事件 | SessionStart matcher 只有 `startup／resume／clear／compact／fork`；Notification 有 `auth_success`（「Authentication completes」），文件未載是否涵蓋 `/login` 切帳號；ConfigChange 不含憑證檔 | 不以 hook 事件為觸發器（R-4.1.7-2 括號）；`auth_success` 不採用：文件未保證、且要新增 settings 註冊（守衛面擴張）而現有兩個觸發器已覆蓋（R197「量、不挖」） |
| Notification hook 不能阻斷、輸入無帳號欄 | 「Notification hooks can't block or modify notifications.」 | 即使採用也只能當觸發器，判定仍要靠標頭指紋（R-4.1.7-3） |
| usage 端點非公開、會 429 | （PRD §15.5 紅線 1 既有劃界） | R-4.1.6-6 補量仍受紅線 1 四條件；429 ⇒ 降級出聲、判決 `NODISPATCH`（R-4.1.6-8） |
| macOS 憑證在 Keychain | （PRD §4.1.4 既有劃界） | 觸發器①在 macOS 缺席，只靠②③（R-4.1.7-2） |

---

## 3. 判決函式（`qv_verdict.verdict`）

### 3.1 輸入（全部來自同一次取數，`qv_io.gather()` 產生的不可變快照）

| 欄 | 來源（既有站點，不新增端點知識） | 說明 |
|---|---|---|
| `state` | `quota_gate.read_quota()`／`refresh_quota_blocking()` | axes、`account_key`、`measured_at`、`source` |
| `markers` | `quota_halt_marker.read_halt_marker()`、`quota_rush`、`sessionctl/park.py` | **只收 `account` 等於 `state.account_key` 者**；不符者交 §7 作廢流程；舊格式（無 `account`）依 R-4.1.7-5 |
| `plan` | `sessionctl/qw_plan`（吃同一份 `state`） | stage、R、L、D、reset |
| `n_live` | `sessionctl/roster`（在飛代理數） | 給 cap 與計畫序列 |
| `next_est` | park `--next-est <pp>`（選填） | 取代 `--why` |
| `policy` | `quota_policy.load_policy()` | prepare／halt 百分比、`QV_WAIT_RESET_MIN` |
| `now` | 呼叫端注入（測試可控） | 唯一時間來源 |

### 3.2 決策表（由上而下，第一個命中即短路；整張表是一個函式，不可能輸出兩個動作）

| 序 | 條件 | 動作 | 理由／條文 |
|---|---|---|---|
| 1 | `state` 讀不到，或 `account_key is None` 且有任何軸 ≥ prepare | `NODISPATCH` | R-4.1.6-8；失效往保守（紅線 6） |
| 2 | 週軸讀數 ≥ halt，或同帳號 halt 標記 `binding=seven_day` 未過期 | `HALT_WEEKLY` | 週軸照舊用到 100% 才停（`env.shared` `AUTOSDD_QUOTA_HALT_PCT`） |
| 3 | 短窗原始讀數 ≥ prepare，或同帳號短窗 halt 標記未過期，或 `plan.stage ∈ {close, wall}` | `D ≤ QV_WAIT_RESET_MIN` ⇒ `WAIT_RESET`；否則 `PARK` | R-4.1.6-4；E2 情境（87%、D=14）落 `WAIT_RESET` |
| 4 | `plan.stage == nodispatch` | `NODISPATCH` | 在飛照跑、不派新 |
| 5 | `next_est` 有值且 `next_est ≥ plan.R − plan.V`（放不下） | `D ≤ QV_WAIT_RESET_MIN` ⇒ `WAIT_RESET`；否則 `PARK` | R-4.1.6-5；取代 `--why` 的自由文字 |
| 6 | 其他 | `CONTINUE` | — |

- `D`＝到短窗 reset 的分鐘數（`plan.D`，量不到 reset ⇒ 視為無窮大，因此第 3 列落 `PARK`，再由 park 自己的「量不到 reset 拒絕」規則處理——不假設 5 小時）。
- `QV_WAIT_RESET_MIN` 出廠＝`AUTOSDD_KEEPWARM_MINUTES`（同一個數，不另設；WHY：`WAIT_RESET` 的載具就是保溫，等的上限必須等於一次保溫間隔，否則保溫撐不到重置）。新鍵只在 `quota_policy` 的 `ENV_SPEC` 以「別名＝保溫分鐘」登記，數字現查 `--print-env-example`。
- `cap`：`CONTINUE` 時＝`min(quota_pace 的 cap, plan.cap)`；其他動作恆 0（`NODISPATCH` 也是 0：不派新）。
- 純函式：不讀檔、不讀環境、不讀牆鐘；全部經參數。

### 3.3 判決行（`qv_render.line`）

```
QUOTA_VERDICT=<ACTION> acct=<12 碼|none> win=<短窗 reset ISO|none> wk=<週 reset ISO|none> cap=<n> measured_at=<ISO> expires_at=<ISO> vid=<8 碼>
```

- 第二行起是一句白話理由（例：「短窗 87%、14 分後重置：保溫等重置，不 park」）。
- `vid＝sha256(ACTION|acct|win|wk|cap|measured_at)[:8]`：同一份輸入恆得同一 vid，watch 閂鎖與 Stop 宣稱守衛都以它比對。
- `expires_at＝min(measured_at＋QUOTA_CACHE_TTL_SECONDS, 短窗 reset)`；`QUOTA_CACHE_TTL_SECONDS` 是 `quota_gate.py` 既有常數（180），不另設。
- 換帳號後第一行判決的理由句附「已作廢 n 個舊帳號標記」（R-4.1.7-6）。
- 時刻一律帶 offset 的 ISO（鐵律三 naive 時間戳列）。
- `--json` 另帶 `billing` 欄（供 Autopilot 設計 §7 的 `[COST]` 類別判定；判決本身不吃它）：由快取 `posture` 推導——`credits_present=false` ⇒ `subscription_only`；`fallback_available=true` ⇒ `credits_fallback`；`source` 為 API key 模式 ⇒ `api_key`；欄位缺或形狀不對 ⇒ `unknown`。與 `quota_messages.posture_line()` 同一來源、同一判讀（推導函式由 `posture_line` 抽出共用，不另寫第二份）；換帳號後隨新快取重判。

### 3.4 取數（`qv_io.gather`）

1. 讀快取；年齡 > TTL，或 §7.1 任一觸發器成立 ⇒ 經**既有單一站點** `quota_gate.refresh_quota_blocking()` 補量一次（紅線 1 (b) 端點知識站點不增加）。
2. **halt 標記不得壓住補量**（R-4.1.6-6）：刪除 `quota_messages.halted_pace_text()` 的「標記有效即不補量」分支；TTL 節流照舊（同一 TTL 內至多一次，`claim_refresh_slot` 既有名額）。
3. 429／逾時 ⇒ `note_degraded` 既有降級出聲；判決 `NODISPATCH`。
4. 回傳不可變快照；呼叫端不得再讀第二次快取拼湊。

### 3.5 消費端改接（同一個 commit 改齊；舊判讀刪除，不留第二個家）

| 消費端 | 現況（檔：函式） | 改為 |
|---|---|---|
| `--pace` | `tools/session_resume_planner.py` `main()` 的 `args.pace` 區塊；首行由 `quota_gate.pace_report` 產，halt 有效時印 halted 行 | 首行＝`QUOTA_VERDICT=` 行；halted 行只在 `HALT_WEEKLY` 且同帳號標記時出現；整個區塊抽到 `qv_render.pace_block()`（§9） |
| watch 額度事件 | `sessionctl/watch_wake.py` `quota_keys()`：原始讀數序列（`park.prepare_hits`）與計畫序列各自成鍵 | 單一序列：鍵＝`(acct, ACTION, win)`，只有 `WAIT_RESET｜PARK｜HALT_WEEKLY｜NODISPATCH` 觸發；末行 `WATCH_VERDICT=quota action=<A> vid=<v> expires_at=<t>`；處置表一個動作一列，`WAIT_RESET` 列不含「park」字樣 |
| watch 閂鎖 | `sessionctl/keepwarm.py` `quota_latch`、`SERIES`（raw／plan 兩序列） | 一序列，鍵加 `acct`；`SERIES` 表退役 |
| park 前置 | `sessionctl/park_reset.py` `resolve()`（`why_ok` 分支、`_close_stage`） | 當下重算判決；非 `PARK｜HALT_WEEKLY` ⇒ rc 4 並印判決行；`--why` 參數自 `park_cli` 移除（傳入即 argparse 錯誤並指路 `--next-est`）；`--at` 保留，但判決須為 `HALT_WEEKLY` 或 `--next-est` 判放不下 |
| Stop 停工推回 | `sessionctl/park.py` `stop_verdict()` | 判決為 `PARK｜HALT_WEEKLY` 且無續航憑證才推回；`WAIT_RESET` ⇒ 推回要求掛 keepwarm（既有保溫閘文案） |
| SessionStart 簡報 | `tools/lib/session_brief.py` `quota_line()` | 改呼叫 `qv_render.brief_line()`（§9） |
| 哨兵巡邏 | planner `_sentinel_tick()` 讀 `quota_messages.halt_verdict` | 讀判決：`HALT_WEEKLY｜PARK` 才維持撞線等待；帳號不符的 halt 標記交 §7 |
| PreToolUse 擋派 | `sessionctl/qw_guard.py`（經 `sessionctl_guard.py`） | `NODISPATCH｜WAIT_RESET｜PARK｜HALT_WEEKLY` ⇒ 擋展開型派工；`CONTINUE` 放行；判決行附在 rc 2 訊息 |
| 原始讀數工具 | `tools/lib/quota_meter.py --json` | 首行印「診斷用，判斷請看 `python tools/sessionctl.py quota`」（R-4.1.6-7） |
| 新 CLI 動詞 | — | `python tools/sessionctl.py quota [--json] [--next-est <pp>]`（入口薄殼只分派，判準在 `qv_*`） |
| Stop 宣稱守衛 | `.claude/hooks/check_claim_provenance.py` | 新增一族（只出聲）：最後一則回覆含額度判斷詞（「已重置」「可以派」「不需要 park」「halt」「額度夠」）而本回合 tool_result 無未過期 `QUOTA_VERDICT=` ⇒ 出聲（R-4.1.6-7） |

---

## 4. 有效期與陳舊判決（N5）

- 任何消費端拿到判決行（自己的 tool_result、watch 輸出檔、交接包）時，以 `expires_at` 對 `now`：過期 ⇒ 呼叫 `qv_io.gather()` 重算，舊 vid 只寫進痕跡 `stale_verdict_recomputed {old_vid, new_vid, age_s}`，不據以行動。
- watch 的輸出檔在 harness 叫醒主控時可能已過期（AskUserQuestion 阻塞即此例，E5）；處置表第一列固定為「先 `sessionctl quota` 重算，再依新 ACTION 處置」。
- 交接包第 12／13 欄若含判決行，`--ack` 時一律重算（新 session 的 measured_at 必晚於舊包）。

---

## 5. park 參數變更（N6）

| 舊 | 新 | 遷移 |
|---|---|---|
| `park --why "<≥8 字>"`（未達門檻也登記） | `park --next-est <pp>`（數值，下一棒估計額度百分點） | `--why` 自 argparse 移除；CLAUDE.md〈換 session 的 SOP〉與記憶檔 `quota-stop-must-park.md` 的「未達門檻用 `park --why`」由 CLOSE 窗口同 commit 改寫 |
| `park --done --why` | 保留（`--done` 宣告「沒有剩餘工作」，不是推翻額度判決） | 無 |
| `park --at <ISO> --why` | `park --at <ISO>`＋判決須為 `HALT_WEEKLY` 或 `--next-est` 判放不下 | `--at` 的自由文字理由改寫入痕跡欄 `note`（只記錄、不參與判定） |

---

## 6. 與既有條文的關係

- PRD §4.5.10 INV-H3 收斂版（halt 期間 `--pace` 不打 API）由 R-4.1.6-6 取代（PRD 已就地註記）。實作面：`quota_messages.halted_pace_text` 刪除不補量分支；測試面：鎖 INV-H3 的既有測試要改成新條文的斷言（WP-QV 內同 commit，不註解掉）。
- QuotaWall 設計的兩序列閂鎖（REQ-QW-77「兩條同時成立兩句並陳」）由本檔 §3.5 的單一序列取代。QuotaWall DES 由 CLOSE 窗口追加【v2.1.28 註記】一列（只增不改）。

---

## 7. 換帳號偵測與標記作廢（AccountSwitch，§4.1.7）

### 7.1 零 API 觸發器（只負責「該重量了」）

| # | 觸發器 | 檢查站點 | 平台 |
|---|---|---|---|
| T① | `~/.claude/.credentials.json` 的 (mtime, size) 與上次記錄不同 | `context_budget_guard.py` PostToolUse（一行呼叫 `acctswitch.tick()`）、`watch` 每輪、哨兵 tick | Windows／Linux（macOS 缺席，照實劃界） |
| T② | 逐字稿自上次檢查位移後出現 `<command-name>/login</command-name>` | 同上（增量讀，記住 byte offset） | 全平台 |
| T③ | 任一次正常補量的 `account_key` 與快取上次不同 | `qv_io.gather()` | 全平台 |

- T① 的上次記錄存 `~/.autosdd/traces/acct_probe.json`（經 `endurance_env.trace_dir()`，測試圍籬可攔，見 Autopilot 設計 N3）。
- token 自動刷新也會改 T①（多量一次，安全方向）。

### 7.2 判定與作廢（`acctswitch.reconcile(state, markers)`，純函式＋I/O 薄層）

1. 觸發後經 §3.4 補量；`state.account_key` 為權威（R-4.1.7-3）。
2. 逐個持久狀態比對 `account`：

| 狀態 | 檔（現查） | 不符時 |
|---|---|---|
| halt 標記 | `quota_halt_marker.halt_marker_path(sid)` | 改名 `halt_<sid>.void-<YYYYmmddTHHMMSS±zzzz>.json`（保留、不刪） |
| 趕工戳記 | `quota_rush` 的戳記檔 | 同上改名 `.void-<ts>` |
| watch 額度閂鎖／保溫帳／配速床持久狀態 | `keepwarm`、`quota_pace_floor` 的狀態檔 | 鍵帶 `acct`，不同帳號的鍵自然不命中；舊鍵於下次寫入時丟棄 |
| park 標記 | `sessionctl/park.py` | **不重做**：沿用 `parkprobe.account_changed` 的提前恢復路徑（v2.1.26） |

3. 落痕跡 `account_switch {old, new, at, trigger: T①|T②|T③, voided: [...]}` 一列；出聲一次（同一對 old→new 只出聲一次，閂鎖鍵＝`(old,new)`）。
4. 舊格式（無 `account` 欄）：補量後，標記綁定軸讀數 < 該標記門檻 ⇒ 作廢；否則保留並補寫 `account=<現值>`（R-4.1.7-5）。

### 7.3 寫入 schema 變更（新寫入一律帶 `account`）

```json
{"at": "2026-11-24T21:32:50+08:00", "binding": "seven_day", "reset_at": "...", "account": "34cd3507237f"}
```

量不到帳號 ⇒ `"account": null` 並出聲（R-4.1.7-1）；`null` 帳號的標記在下一次量到帳號時依 R-4.1.7-5 處理。

### 7.4 非目標（同 PRD §4.1.4）

本機制只被動適配使用者已完成的合法換帳號；不偵測「該不該換」、不建議換、不觸發換。任何輸出文案不得出現「建議換帳號」類字樣（TCS AT 以詞表鎖）。

---

## 8. 模組落點（依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）

**落點決定：住 `tools/lib/sessionctl/` 套件，不另立 `tools/lib/quotaverdict/`。** WHY：SSOT §2 第一列規定「跨模組只准 import `tools/lib/` 的共用單檔，不得互相 import 對方套件」。QV 的主要消費端（watch、watch_wake、park、park_reset、park_cli、keepwarm、qw_guard、statuscmd）全在 sessionctl 套件內，planner 與 hooks 本來就 import `lib.sessionctl`；另立套件會讓 sessionctl 反向 import 新套件，正好違反該列。QuotaWall 的 `qw_*` 已立先例住在 sessionctl。這是對 AP-A 報告 §3.1「`tools/lib/quotaverdict/`」的偏離。

| 內容 | 落點（新檔標「新」） | 規則對應（SSOT §2） |
|---|---|---|
| 判決純函式 | 新 `tools/lib/sessionctl/qv_verdict.py` | 函式庫列 |
| 取數快照 | 新 `tools/lib/sessionctl/qv_io.py` | 函式庫列 |
| 判決行與 `--pace`／簡報呈現 | 新 `tools/lib/sessionctl/qv_render.py`（承接 §9 抽出的 `pace_report`、`pace_block`、`brief_line`） | 函式庫列 |
| 換帳號觸發與作廢 | 新 `tools/lib/sessionctl/acctswitch.py` | 函式庫列 |
| CLI 動詞 | 既有入口 `tools/sessionctl.py` 加 `quota` 動詞（薄殼） | 指令入口列 |
| 測試 | 新 `tools/tests/test_sessionctl_qv.py`（QV＋AC 同一檔，壓低新檔數） | 測試列；CLOSE 重釘 |
| 真機 E2E 案例 | `tools/lib/realverify/cases/` 新家族檔 `quotaverdict.py` | realverify 既有落點 |
| 痕跡 | `~/.autosdd/traces/`（`account_switch`、`stale_verdict_recomputed`、`acct_probe.json`） | repo 外，經 `endurance_env.trace_dir()` |
| CI 接線 | sessionctl 已在 compat-ci `paths`（`tools/lib/sessionctl/**`），新檔自動涵蓋；`non_evolvable_globs` 同 | CI 接線列：無新 glob |
| 登記 | SSOT §3 sessionctl 列：新檔於實作 commit 後由 CLOSE 加反引號登記（規格階段只在 SSOT §3 新增的「Autopilot／QV 規格階段」說明列以純文字預告，因落點鎖要求反引號路徑存在於磁碟） | §3 登記表 |

engine-bridge 閉包（SSOT §4 第 6 點）：新增的 `qv_*` 若被 `quota_policy`／`transcript_activity` 頂層 import ⇒ 同步三處；設計上**不**讓它們被頂層 import（qv 只被 sessionctl 與 planner lazy import），WP-QV 交卷時以 `tools/tests/test_ci_paths_cover_root_consumers.py` 實跑證明。

---

## 9. LOC 牆處置（數字＝SD-0 當回合 `check_loc_budget.root_tools_reports()` 實量；實作前現查）

| 檔 | 現值／上限 | 本輪新增估計 | 抽出清單（先抽、再加；抽出與改接同 commit） | 抽出後餘裕估計 |
|---|---|---|---|---|
| `tools/session_resume_planner.py`（cli 750） | 750／750 | +4（哨兵讀判決） | ①`main()` 的 `args.pace` 區塊（L1568～L1582）→ `qv_render.pace_block(args, deps)`，planner 留 2 行；②`_halt_marker_probe_path()`（L1515～L1524）→ `quota_halt_marker.py`（其自然家；AC 也要改它） | 約 +18 |
| `tools/lib/quota_messages.py`（lib 400） | 400／400 | +6（帳號比對、刪不補量分支約 −4） | `halt_verdict()`（L194～L239）與 `halt_marker_or_rejection()`（L254～L283）→ `tools/lib/quota_halt_marker.py`（現 20／400）；`quota_messages` 留 re-export 一行，既有 import 端不動 | 約 +65 |
| `tools/lib/quota_gate.py`（hub 500） | 496／500（AP-A 報告寫「餘裕 0」，實量為 4） | +6（`read_quota` 帶出 account、halt 寫入帶 account） | `pace_report()`（L912～L987）→ `qv_render.pace_report()`；呼叫端（planner、`qw_cli`、測試）由 WP-QV 以 `git grep -n pace_report` 全數改接，`quota_gate` 不留 delegate（hub 成員清單只縮不長，不得以 delegate 方式保留） | 約 +65 |
| `tools/lib/session_brief.py`（lib 400） | 398／400 | +1 | `quota_line()`（L219～L250）→ `qv_render.brief_line()`，brief 留一行呼叫 | 約 +28 |
| `.claude/hooks/context_budget_guard.py`（special 1104） | 1104／1104 | +3（PostToolUse 呼叫 `acctswitch.tick()`） | `_known_table_cache_path()`／`known_model_windows_path()`／`load_known_model_windows()`（L380～L447）→ 新扁平檔 `tools/lib/model_window_table.py`（前綴 `model` 現 1 支，加入後 2 支 <3，不觸散落鎖）；CLOSE 把 `SPECIAL_FILES` 該檔門檻下修為新實值（棘輪雙邊咬人） | 約 +55，門檻下修後歸 0 |
| `tools/lib/sessionctl/oldwin.py`（lib 400） | 354／400 | （屬 Autopilot 設計 WP-HOOK） | 見 Autopilot 設計 §9 | — |
| 其他觸及檔 | `watch.py` 283、`watch_wake.py` 142、`keepwarm.py` 220、`park_cli.py` 320、`park_reset.py` 61、`quota_rush.py` 186、`quota_halt_marker.py` 20、`quota_meter.py` 327、`check_claim_provenance.py` 510／750 | 各 ≤ +30 | 不需抽出 | — |

抽出原則：只搬、不改行為（搬移 commit 與行為變更 commit 分開，搬移那一個 commit 全套必須綠，證明搬移零行為差異）。

---

## 10. 持有面表（鐵律七）

| 鎖／機制 | 常數 | 史料 | 消費端 | 唯一持有者 |
|---|---|---|---|---|
| 判決決策表 | `qv_verdict.py`（`QV_WAIT_RESET_MIN` 讀 `quota_policy`） | PRD §4.1.6、本檔 §3.2 | watch／park／planner／brief／qw_guard／check_claim_provenance | WP-QV |
| halt 標記 schema | `quota_halt_marker.py` | 痕跡目錄 | `quota_messages`、planner、`acctswitch` | WP-AC（在 WP-QV 收工並親驗後） |
| rush 戳記 schema | `quota_rush.py` | — | `quota_pace_floor`、`statuscmd` | WP-AC |
| watch 閂鎖鍵 | `keepwarm.py` | — | `watch_wake.py` | WP-QV |
| `ENV_SPEC` 新鍵 `QV_WAIT_RESET_MIN` | `quota_policy_env.py` | `env.shared` 不改（別名） | `qv_verdict` | WP-QV |
| `SPECIAL_FILES` 門檻、c1c2、`_TREE_FILE_FLOORS` | `AutoClaude/tools/check_loc_budget.py`、`tools/tests/test_adr_xplat001_c1c2_lock.py`、`tools/lib/skip_tag_policy.py` | 兩站點 guard-total | 全套 | **CLOSE 單一窗口**（並行包只回報建議值） |
| `.claude/hooks/*` 改動 | — | — | — | WP-HOOK（staged diff 交主控親套；本檔涉及 `context_budget_guard.py` 一行呼叫、`check_claim_provenance.py` 新族） |
| 帳本 | — | — | — | CLOSE |

WP-QV 與 WP-AC 動同一組 quota 檔 ⇒ **串行**。

---

## 11. 守衛面准入：暴露證據座標（每個觸及守衛面的條目）

| 條目 | 守衛面檔 | 暴露證據（三取一：真實逐字稿實際發生） |
|---|---|---|
| QV 判決函式與改接 | `tools/lib/sessionctl/**`、`tools/lib/quota_messages.py`、`tools/lib/quota_gate.py`、`tools/session_resume_planner.py`、`tools/lib/session_brief.py` | E1（L2447）、E2（`watch9.log` 03:46）、E5（L2445） |
| park `--why` 退役 | `tools/lib/sessionctl/park_reset.py`、`park_cli.py` | E4（L2504→L2508） |
| halt 不壓補量 | `tools/lib/quota_messages.py` | E1、E3（L210） |
| 標記綁帳號與作廢 | `tools/lib/quota_halt_marker.py`、`quota_rush.py`、`sessionctl/keepwarm.py`、`.claude/hooks/context_budget_guard.py` | E3（halt 標記原檔無帳號欄、L173、L210）、E7（`quota_burn` 空洞） |
| Stop 宣稱守衛 QV 族 | `.claude/hooks/check_claim_provenance.py` | E6（L2553、L2564） |
| `context_budget_guard` 抽出 `model_window_table` | `.claude/hooks/context_budget_guard.py`、新 `tools/lib/model_window_table.py` | 純搬移（LOC 牆前置），附屬於上一列 AC 觸發器的證據；新檔納入守衛面清單（CLOSE 改根 CLAUDE.md〈守衛面准入〉） |

`tools/lib/sessionctl/**` 已在守衛面清單內，新 `qv_*`／`acctswitch.py` 自動屬之，根 CLAUDE.md 清單不需另加；`tools/lib/model_window_table.py` 需加（CLOSE）。

---

## 12. 修復不留後遺症三問

1. **另一台機器會不會回來？** 判準只吃 state 與標記；`account_key` 取自伺服器標頭、跨平台相同；macOS 缺 T① 已照實劃界，T②T③ 仍成立。
2. **有沒有文件／座標不一致？** PRD v2.1.28、本檔、TCS、CLAUDE.md（〈換 session 的 SOP〉的 `park --why`、現查表加 `sessionctl quota`）、記憶檔、QuotaWall DES 註記，由 WP-QV＋CLOSE 同 commit 收齊；舊兩序列與 `--why` 同 commit 刪除。
3. **有沒有「之後再看」？** N8（Stop 額度推回噪音）依 AP-A 報告登記理論洞、不在本輪；除此之外無。

---

## 13. 與 AP-A 報告的差異（SD-0 決定）

| 項 | AP-A | SD-0 | WHY |
|---|---|---|---|
| 落點 | `tools/lib/quotaverdict/` 套件 | `tools/lib/sessionctl/qv_*.py` | SSOT §2 禁止套件互相 import（§8） |
| `quota_gate` 餘裕 | 0 | 4（實量 496／500） | 當回合實量；結論不變（仍需抽出） |
| `/login` 觸發器 | 待查 hook | 官方文件證實無專屬事件；`auth_success` 不採用 | §2 |
| `QV_WAIT_RESET_MIN` | 預設＝保溫分鐘數 | 別名同一數、不另設新值 | 不讓兩個數各自漂移 |
| `pace_report` | 未定 | 搬入 `qv_render`，hub 不留 delegate | hub 成員只縮不長 |
| QV 與 AC 測試 | 未定 | 同一新測試檔 | 壓低重釘稅 |
