# 單一權威額度判決與換帳號作廢設計（QuotaVerdict／AccountSwitch Design）

- 版本：v1.2（SD-2，2026-11-25；依 QA 複審 FAIL〔新 P2×6、P3×4〕修訂；規格階段，實作未開始）。v1.0（SD-0）→ v1.1 的逐條處置見 §14；v1.1 → v1.2 見 §15。
- 上游：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 修訂表 v2.1.28 與 v2.1.29（勘誤）、§4.1.6（R-4.1.6-1～8 及其【v2.1.29 勘誤】）、§4.1.7（R-4.1.7-1～6）、§4.1.5 R-4.1.5-1（量不到 ⇒ `cap ≤ cap_prepare`，本設計遵守、不取代）、§15.5 紅線 14、§4.1.4／§4.2.3【v2.1.24】／§4.5.10／§4.5.11 的【v2.1.28 註記】、§16.6 2026-11-25 第一列。
- 驗收：`docs/03_testing/contracts/TCS-Autopilot-20261125.md`（REQ-AP-QV-01～11、REQ-AP-AC-01～04）。
- 兄弟設計：`docs/02_architecture/Autopilot_Pipeline_Design.md`（合入、推送、棘輪、CI、舊視窗、詢問類別閘、測試圍籬；〈外部限制〉全文住那裡，本檔 §2 只摘與額度有關者）。
- 先例與被消費的設計：`docs/02_architecture/QuotaWall_CacheContinuity_Design.md`（額度牆計畫 `qw_plan`、閂鎖、保溫）、`docs/02_architecture/Control_Handover_Design.md`（park 等待期間額度提前恢復、`parkprobe.account_changed`）。

**為什麼另立一份、不併入 `Control_Handover_Design.md`**：Control_Handover 管的是「誰在控制背景代理、何時換手」（控制面），本檔管的是「額度現在准許做什麼」（判決面）。兩者的消費關係是單向的（控制面讀判決），併在一起會讓 128 KB 的控制面文件再承擔一條獨立的判準鏈，審查時無法單獨凍結。QuotaWall 設計是本檔的**輸入**（`qw_plan` 是判決函式的一個參數），也不併入。

**命名**（v1.1 起；F-10、F-26）：判決純函式住扁平檔 `tools/lib/quota_ruling.py`，取數與 CLI 住 `tools/lib/sessionctl/ruling_io.py`。刻意不用 `qv_` 前綴：與既有 `sessionctl/qw_verdict.py` 只差一個字母。對外字面仍是 PRD 已定的 `QUOTA_VERDICT=` 判決行與 `python tools/sessionctl.py quota` 動詞（指令字面＝對外契約，不改）。下文「判決」皆指 `quota_ruling.ruling()` 的輸出。

---

## 0. 一頁結論

1. 停工、park、續跑、等重置、可派數五類決定，全部由 `quota_ruling.ruling()` 一次算出，輸出唯一動作（`CONTINUE｜NODISPATCH｜WAIT_RESET｜PARK｜HALT_WEEKLY`）與一行 `QUOTA_VERDICT=`。所有既有額度判讀站點逐一普查（§3.5：改接 C1～C21、劃界 B1～B7；v1.2 補 park 提前恢復與換手計畫的 park 分支），每處標「改接」或「劃界（附 WHY）」；以機械鎖 `QV::SingleHouseTest` 釘住白名單，新增私有判讀站點即紅（R-4.1.6-2、REQ-AP-QV-10）。
2. `cap` 只有一個來源：派工閘同一條管線（`decide`＋清倉＋可得性遲滯＋平穩機制，含目標模型），由 `quota_gate.dispatch_decision()` 抽出後供判決與派工閘共用（§3.2 末、§9）。
3. 判決帶 `expires_at＝min(measured_at＋180 s, 短窗 reset)`（量不到時另見 §3.3），過期一律重算（R-4.1.6-3）；87%＋距重置 14 分 ⇒ `WAIT_RESET`，不是 `PARK`（R-4.1.6-4）；`WAIT_RESET` 有自己的叫醒載具，不受保溫的 `small_ctx`／`no_usage`／n* 限制，無人窗口改交哨兵（§3.6）。
4. 量不到讀數 ⇒ `CONTINUE` 加 `deg=unmeasured`，`cap` 走 R-4.1.5-1 的降級上限（`1 ≤ cap ≤ cap_prepare`），不是 `cap=0`——不違反「靜默鎖死已禁止」（R-4.1.6-8 的【v2.1.29 勘誤】）。量不到 reset 時刻 ⇒ `NODISPATCH`，不出 `PARK`（避免 park 自己拒絕造成的死循環）。
5. park 的 `--why` 退役，改 `--next-est <pp>` 進判決，缺省值由程式推導、模型只能往上調（R-4.1.6-5、§5）；halt 標記不再壓住補量（R-4.1.6-6）。
6. halt／rush／閂鎖／保溫帳全部綁 `account_key`；三個零 API 觸發器發現「帳號可能已變」⇒ 補量 ⇒ 指紋不符即作廢舊標記（改名保留）並出聲（§4.1.7、§7）。
7. 落點：純函式＝扁平共用單檔（只依賴 `quota_policy`）；I/O 與 CLI＝sessionctl；扁平檔不 import 任何套件，需要判決的扁平消費端由呼叫端（hook／planner）注入（§8）。SelfImproving 經 CLI `--json` 取判決（不 import sessionctl）。

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
| usage 端點非公開、會 429 | （PRD §15.5 紅線 1 既有劃界） | R-4.1.6-6 補量仍受紅線 1 四條件；429 ⇒ 降級出聲、判決走 §3.2 第 6 列（`CONTINUE`＋`deg=unmeasured`＋降級 cap，R-4.1.5-1） |
| macOS 憑證在 Keychain | （PRD §4.1.4 既有劃界） | 觸發器①在 macOS 缺席，只靠②③（R-4.1.7-2） |

---

## 3. 判決函式（`quota_ruling.ruling`）

### 3.1 輸入（全部來自同一次取數，`sessionctl.ruling_io.gather()` 產生的不可變快照）

| 欄 | 來源（既有站點，不新增端點知識） | 說明 |
|---|---|---|
| `state` | `quota_gate.read_quota()`／`refresh_quota_blocking()`／`settled_quota()`；L3 地板 `quota_floor_reading()` | axes、`account_key`、`measured_at`、`source`、`reason` |
| `decision` | `quota_gate.dispatch_decision(state, now, env, model, event)`（v1.1 新增；自 `quota_gate()` L1053～L1112 原樣抽出：`load_policy`→`quota_burndown.active`→`quota_policy.decide(…, active_model, burndown)`→`quota_availability.evaluate`→`quota_stability.evaluate`→cap 改寫） | band、cap、binding、`recommended_fanout`；**派工閘與判決共用這一份**（F-01 ②）。配速床（§2.15）與趕工戳記都只經由它影響 `cap` |
| `model` | 呼叫端：主控家族（`--pace`、Stop、watch）；派工判斷用 Agent／Task 呼叫的目標模型 | 決定哪些模型分軌週軸（`quota_policy.MODEL_SCOPED_KINDS`）進第 2 列，與 DEF-200-436「只擋指名模型」同義（F-06） |
| `markers` | `quota_halt_marker.read_halt_marker()`、`quota_rush`、`sessionctl/park.py` | **只收 `account` 等於 `state.account_key` 者**；不符者交 §7 作廢流程；舊格式（無 `account`）依 R-4.1.7-5 |
| `plan` | `sessionctl/qw_plan`（吃同一份 `state`） | `stage`、`r`（R）、`v`（V）、`limit`（L）、`d_min`（D）、`reset`（欄名照 `qw_plan.Plan` L25～L46 現查）。**`Plan` 沒有 cap 欄**（`k` 是保溫次數，不是派工上限）；`plan` 只經 §3.2 第 3～5 列影響**動作**，從不影響 `cap`（v1.2，QA 複審 N-06） |
| `n_live` | `sessionctl/roster`（在飛代理數） | 給計畫序列與 `next_est` 缺省值 |
| `next_est` | park `--next-est <pp>`（選填；缺省值見 §5） | 取代 `--why` |
| `policy` | `quota_policy.load_policy()` | prepare／halt 百分比、`QV_WAIT_RESET_MIN` |
| `now` | 呼叫端注入（測試可控） | 唯一時間來源 |

### 3.2 決策表（由上而下，第一個命中即短路；整張表是一個函式，不可能輸出兩個動作）

| 序 | 條件 | 動作 | 理由／條文 |
|---|---|---|---|
| 1 | spend／`extra_usage` 軸（`quota_policy.FALLBACK_KINDS`）讀數達其上限 | `HALT_WEEKLY`，`wk=none`，理由句「月度支出上限：沒有 reset 可等」 | F-08 ①；與哨兵既有 `LIMIT_SPEND` escalate 同義；提高上限是人要做的 `[COST]` 型動作（APD §7、§8 例外清單） |
| 2 | 與 `model` 相關的週軸（全模型週軸＋該模型的分軌週軸）讀數 ≥ halt，或同帳號 halt 標記 `binding` 屬週軸且未過期 | `HALT_WEEKLY` | 週軸照舊用到 100% 才停（`env.shared` `AUTOSDD_QUOTA_HALT_PCT`）；別家模型的分軌週軸不進來（F-06） |
| 3 | 短窗**原始**讀數 ≥ prepare，或同帳號短窗 halt 標記未過期，或 `plan.stage ∈ {close, wall}` | 短窗 reset 已知：`D ≤ QV_WAIT_RESET_MIN` ⇒ `WAIT_RESET`，否則 `PARK`；**短窗 reset 量不到 ⇒ `NODISPATCH`** | R-4.1.6-4；E2 情境（87%、D=14）落 `WAIT_RESET`；量不到 reset 不出 PARK（F-07：park 對量不到 reset 一律 rc 4，判 PARK 會讓 Stop 推回與 park 拒絕互相打轉） |
| 4 | `plan.stage == nodispatch` | `NODISPATCH` | 在飛照跑、不派新 |
| 5 | `next_est ≥ plan.R − plan.V`（放不下） | 同第 3 列的三分支 | R-4.1.6-5；取代 `--why` 的自由文字 |
| 6 | `state` 量不到（無任何可用軸；含 429、逾時、無憑證、快取過期且補量失敗），且上面各列皆未命中 | `CONTINUE`，`deg=unmeasured`，`cap＝decision.cap`（量不到時 `decide()` 回降級上限，`1 ≤ cap ≤ cap_prepare`，R-4.1.5-1） | R-4.1.6-8【v2.1.29 勘誤】；不是 `cap=0`（PRD §4.1.5「0＝靜默鎖死，本實作已明文禁止」）。量不到時第 1～3 列只能由標記與 L3 地板（逐字稿撞線）命中 |
| 7 | 其他 | `CONTINUE` | — |

- `D`＝到短窗 reset 的分鐘數（`plan.D`）。
- `QV_WAIT_RESET_MIN` 出廠＝`AUTOSDD_KEEPWARM_MINUTES`（同一個數，不另設；WHY：保溫間隔是主載具的叫醒粒度，等的上限等於一次保溫間隔時，最壞只多叫醒一次）。新鍵只在 `quota_policy` 的 `ENV_SPEC` 以「別名＝保溫分鐘」登記，數字現查 `--print-env-example`。
- `cap`（v1.2 改寫，N-06）：`CONTINUE` 時＝`decision.cap`，**唯一來源**（PRD R-4.1.6-2【v2.1.29 勘誤】「cap 的唯一來源＝派工閘同一條管線」逐字成立；v1.1 的 `min(decision.cap, plan.cap)` 刪除——`qw_plan.Plan` 無此欄，取兩者最小等於替實作棒開第二個 cap 來源，即 G11 的形狀）。`decision.cap is None`（free 帶不設限）⇒ 判決 `cap＝policy.max_fanout`，與 `pace_contract.payload()` 把 `None` 換成 `max_fanout` 的既有規則同一個數、同一來源（`quota_policy.py` `max_fanout`，`AUTOSDD_QUOTA_MAX_FANOUT`），不另設。其他動作恆 0。QuotaWall 計畫要收緊派工的唯一途徑是讓 `plan.stage` 命中第 3／4 列（改動作），不是改 cap。動作只看原始讀數與標記；配速床、趕工戳記、清倉授權、平穩機制只改 `cap`，**不改動作**（F-08 ②③）。
- 帳號量不到但有讀數（`account_key is None` 而軸可用）：照讀數判，判決行 `acct=none`；標記依 R-4.1.7-5 舊格式規則處理。v1.0 第 1 列「帳號量不到且有任何軸 ≥ prepare ⇒ NODISPATCH」刪除（與 PRD 用語不一致、且與 R-4.1.5-1 衝突，F-02）。
- 純函式：不讀檔、不讀環境、不讀牆鐘；全部經參數。

### 3.3 判決行（`quota_ruling.line`）

```
QUOTA_VERDICT=<ACTION> acct=<12 碼|none> win=<短窗 reset ISO|none> wk=<週 reset ISO|none> cap=<n> measured_at=<ISO|none> expires_at=<ISO> vid=<8 碼> mdl=<模型家族> [deg=unmeasured]
```

- 前八欄＝PRD R-4.1.6-2 的字面；`mdl=`、`deg=` 是 v2.1.29 勘誤允許的附加欄（附加欄只可在尾端增加，消費端以鍵取值，不以位置取值）。
- 第二行起是一句白話理由（例：「短窗 87%、14 分後重置：保溫等重置，不 park」）。
- `vid＝sha256(ACTION|acct|win|wk|cap|measured_at|mdl|deg)[:8]`：同一份輸入恆得同一 vid，watch 閂鎖與 Stop 宣稱守衛都以它比對。
- `expires_at`：讀數可用時＝`min(measured_at＋QUOTA_CACHE_TTL_SECONDS, 短窗 reset)`；讀數不可用時＝`now＋max(QUOTA_CACHE_TTL_SECONDS, retry_after)`（`retry_after` 取 429 回應標頭，缺＝0；F-19：否則判決產出當下就過期，消費端緊迴圈重算）。`QUOTA_CACHE_TTL_SECONDS` 是 `quota_gate.py` 既有常數（180），不另設。
- 換帳號後第一行判決的理由句附「已作廢 n 個舊帳號標記」（R-4.1.7-6）。
- 時刻一律帶 offset 的 ISO（鐵律三 naive 時間戳列）。
- `--json` 另帶：`band`（`decision.band`，供 SelfImproving 降載判斷，§3.5 SI 列）、`reason`（理由句）、`billing`（供 Autopilot 設計 §7 的 `[COST]` 類別判定；判決本身不吃它）。`billing` 推導：`credits_present=false` ⇒ `subscription_only`；`fallback_available=true` ⇒ `credits_fallback`；`source` 為 API key 模式 ⇒ `api_key`；欄位缺或形狀不對 ⇒ `unknown`。推導函式 `quota_ruling.billing_from_posture()` 由 `quota_messages.posture_line()` 抽出、`posture_line()` 改呼叫它（同一來源、同一判讀，不另寫第二份；也替 400／400 的 `quota_messages.py` 騰出行數）；換帳號後隨新快取重判。

### 3.4 取數（`ruling_io.gather`）

1. 讀快取；年齡 > TTL，或 §7.1 任一觸發器成立 ⇒ 經**既有單一站點** `quota_gate.refresh_quota_blocking()` 補量一次（紅線 1 (b) 端點知識站點不增加；`claim_refresh_slot` 名額與 `settled_quota()` 既有語意不變）。
2. **halt 標記不得壓住補量**（R-4.1.6-6）：刪除 `quota_messages.halted_pace_text()` 的「標記有效即不補量」分支；TTL 節流照舊（同一 TTL 內至多一次）。
3. 429／逾時 ⇒ `note_degraded` 既有降級出聲；判決走 §3.2 第 6 列（量不到但非鎖死）。
4. 以同一份 `state` 呼叫 `quota_gate.dispatch_decision()` 與 `qw_plan.plan()`，再呼叫 `quota_ruling.ruling()`；回傳不可變快照；呼叫端不得再讀第二次快取拼湊。

### 3.5 消費端普查與處置（F-01；同一個 commit 改齊；舊判讀刪除，不留第二個家）

**普查方法**（SD-1 當回合以 Grep 掃 `tools/**`、`.claude/hooks/*.py`，樣式：`read_quota(`、`quota_policy.decide(`、`decide(state`、`prepare_hits(`、`qw_plan.plan(`、`halt_verdict(`、`read_halt_marker(`、`weekly_forces_fresh(`、`.band`；v1.2 依 QA 複審 N-02 加包裝入口 `pace_state(`、`_pace_state(`、`settled_quota(`、`default_read(`／`default_refresh(` 與 `prepare_pct`／`halt_pct` 的比較運算；實作棒第一動作以同一組樣式重掃，表外新出現的站點一律預設「改接」，且 §3.5.3 的鎖會讓漏掉的站點轉紅，不靠記得）。

#### 3.5.1 改接（據以行動的判讀；一律改讀判決）

| # | 消費端 | 現況（檔：函式／行） | 改為 |
|---|---|---|---|
| C1 | **派工閘（PreToolUse，真正的致動器）** | `tools/lib/quota_gate.py` `quota_gate()` L1031～L1180（經 `context_budget_guard.py`）：自行 `decide()`、halt 帶 rc 2、prepare 帶動作、fanout cap 帳 | 新增注入依賴 `rule`（hook 端傳 `sessionctl.ruling_io.rule_from_decision`；扁平 hub 不 import 套件，比照既有「六個注入依賴全部來自 hook 端」）。`dispatch_decision()` 抽出後，`quota_gate()` 只依判決：`ACTION ≠ CONTINUE` ⇒ 擋展開型派工（rc 2，訊息附判決行）；`CONTINUE` ⇒ 以判決 `cap` 記 fanout 帳；halt／prepare 的副作用（halt 標記、任務書、喚醒武裝）改由判決的 `ACTION` 與 `decision.binding` 驅動，閂鎖鍵加 `acct` |
| C2 | QuotaWall 擋派與提示 | `sessionctl/qw_guard.py` L106／L124（`qw_plan.plan`、`prepare_hits`）；`sessionctl/qw_verdict.py` `pretool_verdict()`／`stop_verdict()`／`absent_notice()`／`mute()`（L63～L157；經 `sessionctl_guard.py`、`check_pending_handoff.py`） | qw_guard 的擋派分支退役（判決第 3、4 列已涵蓋 stage close／wall／nodispatch，致動器只留 C1 一處，免得兩支 hook 各擋各的、訊息各說各的）；`qw_verdict` 的提示與 mute 改以判決行為準（`mute` 的鍵＝vid） |
| C3 | `--pace` | `tools/session_resume_planner.py` `main()` 的 `args.pace` 區塊；首行由 `quota_gate.pace_report` 產；L1617 halted 行；`tools/lib/quota_messages.py` `halted_pace_text()` L169（自行 `quota_policy.decide` 判 `BAND_HALT` 決定要不要印「換模型」提示；v1.2 補列，N-02） | 首行＝`QUOTA_VERDICT=` 行；halted 行只在 `HALT_WEEKLY` 且同帳號標記時出現；整個區塊抽到 `ruling_io.pace_block()`（§9）；`halted_pace_text()` 的 `decide` 呼叫刪除，「換模型有沒有用」提示改依判決（`HALT_WEEKLY` 且 `mdl=` 的週軸是模型分軌軸 ⇒ 印），改為吃注入的判決物件（扁平檔不 import 套件） |
| C4 | watch 額度事件 | `sessionctl/watch_wake.py` `quota_keys()` L60（`park.prepare_hits`）；`watch.py` L296（`plan_fn`） | 單一序列：鍵＝`(acct, ACTION, win)`，只有 `WAIT_RESET｜PARK｜HALT_WEEKLY｜NODISPATCH` 觸發；末行 `WATCH_VERDICT=quota action=<A> vid=<v> expires_at=<t>`；處置表一個動作一列，`WAIT_RESET` 列不含「park」字樣 |
| C5 | watch 閂鎖 | `sessionctl/keepwarm.py` `quota_latch`、`SERIES`（raw／plan 兩序列） | 一序列，鍵加 `acct`；`SERIES` 表退役 |
| C6 | park 前置 | `sessionctl/park_reset.py` `resolve()` L46～L61（`why_ok` 分支、`_close_stage`、`prepare_hits`） | 當下重算判決；非 `PARK｜HALT_WEEKLY` ⇒ rc 4 並印判決行；`--why` 參數自 `park_cli` 移除（傳入即 argparse 錯誤並指路 `--next-est`）；`--at` 保留，但判決須為 `HALT_WEEKLY` 或 `--next-est` 判放不下；拒絕文案不再出現 `--why`（`--done --why` 除外，F-07） |
| C7 | Stop 停工推回 | `sessionctl/park.py` `stop_verdict()` L319～L341（`prepare_hits`） | 判決為 `PARK｜HALT_WEEKLY` 且無續航憑證才推回；`WAIT_RESET` ⇒ 依 §3.6 掛叫醒載具，不推 park |
| C8 | Stop 收斂閘的額度牆摘要 | `sessionctl/converge.py` `stop_verdict()`（合成封存／park／保溫三閘） | 額度相關句一律引判決行；不得另行判帶 |
| C9 | 保溫叫醒目標 | `sessionctl/qw_plan.py` `wake_target()` L207～L232；`kw_wake.py` L76；`kw_run.py` | 新增來源 `ruling_wait_reset`（§3.6） |
| C10 | SessionStart 簡報 | `tools/lib/session_brief.py` `quota_line()` L219～L250（L240 `decide`）、L505～L506（第二處 `decide`） | 兩處皆改：由呼叫端（SessionStart hook）注入判決，簡報以 `quota_ruling.brief_line(r)` 呈現（扁平檔不 import 套件，§8） |
| C11 | 哨兵巡邏 | planner `_sentinel_tick()` L664 讀 `quota_messages.halt_verdict`；L1482 `read_halt_marker` | 讀判決：`HALT_WEEKLY｜PARK` 維持撞線等待；無人窗口的 `WAIT_RESET` 依 §3.6 交哨兵武裝；帳號不符的 halt 標記交 §7 |
| C12 | 無人續燒判帶 | `tools/lib/relay_machine.py` L149～L161（`decide(...).band ∈ {free, notice}`） | 改為判決 `ACTION == CONTINUE`（`deg=unmeasured` 時沿用 relay 既有 fail-closed：不續燒） |
| C13 | 換手決策的額度輸入**與換手計畫的 park 分支**（v1.2 擴寫，N-01 ②） | `sessionctl/switchfacts.py` `quota_facts()` L113～L131（自行取 `park._pace_state`、`qw_plan.plan`、`prepare_pct` 組 `switchplan.Quota`）；`sessionctl/switchplan.py` `_short_hit()`／`_wall()` L99～L120（`stage∈{close,wall}` 或 `short_pct ≥ prepare_pct` 或 `weekly_pct ≥ prepare_pct` ⇒ `PARK_UNTIL`／`PARK_POLL`；經 `controlfacts.decide`、`watch_wake.py` L120～L131 消費）——E2 情境（87%、D=14）判決為 `WAIT_RESET`，它卻出 PARK，且週軸以 prepare（不是 halt）判，與決策表第 2 列也不同 | ①`switchplan.Quota` 的判讀欄 `stage`／`short_pct`／`weekly_pct`／`prepare_pct` 退役，改帶判決欄 `action`（`ACTION`）、`win`、`wk`、`vid`；`credential`、`stale`、`wait_min`（＝`plan.d_min`，只供 `long_wait` 輪詢形態）、`target_axis` 保留。②`_wall()` 依判決 ACTION 對映、不再自比門檻：`PARK` ⇒ `PARK_UNTIL`（`long_wait` 或 `target_axis≠short` 時 `PARK_POLL`），目標＝`win`；`HALT_WEEKLY` ⇒ `PARK_POLL`，目標＝`wk`（`wk=none` 的 spend 列 ⇒ 不出 PARK，回 `STAY` 理由 `spend_limit`）；**`WAIT_RESET` ⇒ `STAY`、理由 `wait_reset`、`Flags.keepwarm=True`、carrier＝`keepwarm（ruling_wait_reset）`，絕不出 `PARK_*`**；`NODISPATCH`／`CONTINUE` ⇒ 回 `None`（交下一列）。`credential` 為真時照舊不出 PARK。③`_short_hit()` 刪除（無呼叫端）。④`switchfacts.quota_facts()` 改由 `ruling_io.gather()` 取判決後組 `Quota`（不再自讀 `park._pace_state`／`policy`；`qw_plan.plan` 只取 `d_min`、`stale`，屬 C 站點診斷用，見 §3.5.3 白名單）；取數失敗 ⇒ `action=None` ⇒ `_wall` 回 `None`（與 `decide` 的「量不到偏續跑」同向）。⑤量測重放 `wastecensus/sections_ctl.py` L184（B4）依新 `Inputs` 形狀同 commit 改，不另寫判準 |
| C21 | **park 提前恢復**（v1.2 新增，N-01 ①） | `sessionctl/parkearly.py` `tick()` L89～L117（`park._pace_state`→`parkprobe.evaluate`→`recovered` ⇒ `fire_early` 起 `park --fire`＝提前「續跑」）；`sessionctl/parkprobe.py` `evaluate()` L60～L75（`recovered ⇔ cur ≤ parked_pct − EARLY_DROP_PP ∧ cur < policy.prepare_pct`）——cur < prepare 但 `plan.stage=close` 時判決為 `PARK`，它卻提前續跑 | `parkearly.tick` 改為：取 `ruling_io.gather()` 的判決 ⇒ **`fire_early` 的必要條件＝`ACTION == CONTINUE` 且無 `deg=unmeasured`**；`parkprobe.evaluate` 改簽名為 `evaluate(marker, state, ruling, now)`：`recovered ⇔ ruling.action == CONTINUE ∧ ¬ruling.degraded ∧ cur ≤ parked_pct − EARLY_DROP_PP`。`cur < policy.prepare_pct` 這一半**退役**（准許與否只由判決決定）；`cur ≤ parked_pct − 5pp` 這一半**保留為判決之後的遲滯閘**（WHY：它只能讓提前恢復更少、不能讓它在判決不准時發生——一個只收緊、不放寬的 AND 項不構成第二個判讀家；用途是避免讀數在 prepare 附近抖動時 park／提前恢復來回翻轉，Control_Handover DES §8.3 的既有設計理由）。`account_changed` 分支不變（換帳號＝另一個判決輸入，判決本身以新帳號 `state` 重算）。痕跡 `park_early_probe` 加欄 `vid`、`action` |
| C14 | 交接包額度欄 | `sessionctl/handoff_build.py` L125 | 寫判決行（§4 第 3 點：`--ack` 時重算） |
| C15 | escalation | `tools/lib/quota_escalation.py` L335（`decide(read_quota(now)…)`） | 改讀判決（第 1 列 spend ⇒ escalate 既有路徑）；同行數替換，淨增 0（該檔 400／400，§9） |
| C16 | 原始讀數工具 | `tools/lib/quota_meter.py --json` | 首行印「診斷用，判斷請看 `python tools/sessionctl.py quota`」（R-4.1.6-7） |
| C17 | QuotaWall CLI | `sessionctl/qw_cli.py` L44／L59 | 首行印判決行；計畫細節降為診斷段 |
| C18 | **SelfImproving 巡邏與研究免掃**（主控代決 ①；REQ-AP-QV-09） | `tools/lib/selfimproving/sched.py` `quota_check()`／`quota_verdict()` L232～L265、`patrol.py` `_quota()` L96～L105（L233 呼叫）、`fourq.py` `_free_band()` L35 | 經子行程 `python tools/sessionctl.py quota --json` 取判決（SI 套件不得 import sessionctl，SSOT §2；也不 import 扁平 `quota_ruling`，因為它需要 sessionctl 的取數）：跳過＝`ACTION ≠ CONTINUE` **或** `deg=unmeasured`（保留 SI 一向的 fail-closed）；降載＝`--json` 的 `band ∈ {notice, converge}`（與現行降載集合同義）；子行程失敗或輸出不可解析＝跳過（fail-closed）。`writeverbs.py` L254 與 `evspec.py` 的 `--band` 值改記判決的 `ACTION`（`quota-band` 附註值＝判決行） |
| C19 | 新 CLI 動詞 | — | `python tools/sessionctl.py quota [--json] [--next-est <pp>] [--model <family>]`（入口薄殼只分派，判準在 `quota_ruling`，取數在 `ruling_io`） |
| C20 | Stop 宣稱守衛 | `.claude/hooks/check_claim_provenance.py` | 新增一族（只出聲）：最後一則回覆含額度判斷詞（「已重置」「可以派」「不需要 park」「halt」「額度夠」）而本回合 tool_result 無未過期 `QUOTA_VERDICT=` ⇒ 出聲（R-4.1.6-7）；假紅以真實語料量（TCS E2E-AP-QV-06） |

#### 3.5.2 劃界（不改；附 WHY）

| # | 站點 | WHY |
|---|---|---|
| B1 | 判決管線內部（取數與組帶）：`quota_gate.read_quota`／`refresh_quota_blocking`／`settled_quota`／`pace_state`／`dispatch_decision`／`quota_floor_reading`、`quota_policy.decide`（含 `quota_policy*.py` 內部的門檻比較與 `quota_policy_env.py` L378 跨欄位不變式驗證）、`quota_burndown.py` L145／L159／L299～L351（halt 門檻內的清倉判定）、`quota_availability.py`、`quota_stability.py`、`quota_reconcile.py`、`quota_pace_floor.py`、`quota_gate.py` L618／L657（`pace_floor=False` 對照）；**包裝入口**（v1.2 補列，N-02）：`sessionctl/park.py` `_pace_state()` L369～L372、`sessionctl/qw_wall.py` `default_read()`／`default_refresh()` L36～L53——只有 `ruling_io.gather()` 與 C 站點中明文標「診斷用」者可呼叫它們（§3.5.3） | 它們是判決的**輸入**，不據以行動；判決只此一家呼叫它們組合成動作。包裝入口只轉手讀數，本身不比門檻 |
| B2 | 續跑選路成本：`tools/lib/resume_route.py` `weekly_forces_fresh()` L161～L185、`tools/lib/resume_cost.py` L165 | 輸出是「怎麼續」（resume 或 fresh），不是五類決定；前提是呼叫端已由判決（C11／C12）准許續跑。選路門檻 `converge_pct` 屬成本模型（ADR-XPLAT-004 §2.13），不是准許與否 |
| B3 | 模型平衡建議：`sessionctl/modelmix.py` L79、`tools/sessionctl.py` L49 | 資訊性建議（「改派哪個家族較省」），輸出標「建議（非判決）」，不據以擋派或停工 |
| B4 | 量測與重放：`tools/probe/**`、`tools/lib/wastecensus/**`（含 `pace_replay.py`）、`tools/lib/realverify/**` | 不接閘門 rc、不據以行動（各檔頭自述） |
| B5 | 測試：`tools/tests/**` | 測試本身 |
| B6 | **壓縮可否**（非五類決定；v1.2 自 B1 拆出，N-07）：`quota_gate.py` `draining()` L503～L525（`decide(read_quota(at), …, pace_floor=False)`＋`compact_margin_breached`：`pct + compact_cost_budget_pp > prepare_pct`），經 `context_budget_guard.py` L1067 決定 84% 提示要不要叫主控壓縮 | 回答的是「現在壓縮會不會把五小時水位推過線」（PRD §4.3 壓縮條件），不是停工／park／續跑／等重置／可派數；它不是判決的輸入，判決也不吃它。v1.1 把它寫成「`decide` 的姿態探針」列進 B1，WHY 不成立，故獨立成列。若日後要讓它據以擋派或停工，必須先改接判決 |
| B7 | **`park --done` 的時限上限**（v1.2，N-10）：`sessionctl/park_cli.py` L196～L199（`quota_gate.pace_state(now).axes` 取短窗 `resets_at`，`limit = min(5 小時, 短窗 reset)`） | 只取「reset 時刻」作為收工標記的有效期上限，不比任何門檻、不判准許與否；`--done` 本身是人／主控宣告「沒有剩餘工作」（§5），不是額度決定 |

#### 3.5.3 機械鎖（REQ-AP-QV-10；F-01 ③）

- `QV::SingleHouseTest`：AST 掃 `tools/**/*.py`（除 B4、B5 目錄）與 `.claude/hooks/*.py`，收集兩類站點（檔＋外層函式名），與白名單常數 `RULING_INPUT_SITES` **相等比對**：多一處（新增私有判讀）紅；少一處而白名單未改也紅（同 `hook_wiring.SHELL_FORM_CENSUS` 的相等判準）。
  - **(i) 呼叫站點**：呼叫 `read_quota`、`refresh_quota_blocking`、`settled_quota`、`pace_state`、`_pace_state`、`default_read`、`default_refresh`、`quota_policy.decide`（含 `decide(` 之以 `quota_policy` 別名或屬性取得者）、`prepare_hits`、`qw_plan.plan`、`halt_verdict`、`read_halt_marker`、`weekly_forces_fresh`（v1.2 加包裝入口，N-02：v1.1 只收直接原語，經 `park._pace_state` 取數再自比門檻的站點——parkearly、parkprobe、switchfacts、qw_guard、qw_wall、watch_wake、park_cli——鎖看不見）。
  - **(ii) 門檻比較站點**：`ast.Compare` 節點的任一運算元子樹含屬性名 `prepare_pct` 或 `halt_pct`（`ast.Attribute.attr`），且所在檔不屬 `quota_policy*.py`／`quota_ruling.py`（N-02）。v1.2 普查（SD-2 當回合 `git grep -n -E "(prepare_pct|halt_pct)"` 過濾比較運算）的現存站點：`quota_burndown.py` L145／L159（B1）、`quota_gate.py` L499 `compact_margin_breached`（B6）、`sessionctl/park.py` L132 `prepare_hits`（C4／C6／C7 改接後無呼叫端即刪；仍有者必入表）、`park_reset.py` L69（C6）、`parkprobe.py` L72（C21）、`switchplan.py` L104／L110（C13）、`watch_wake.py` L64（C4）。改接完成後 (ii) 的白名單只剩 B1、B6 兩列的站點。誠實劃界：以區域變數轉存門檻（`p = policy.prepare_pct; if x >= p`）的比較，(ii) 看不見；(i) 仍會抓到該站點取數那一呼叫，故不構成整片失明。
- **白名單 `RULING_INPUT_SITES` 的定義**（v1.2，N-09）：＝B1～B3、B6、B7 的站點 ＋ `quota_ruling`／`ruling_io` 本身 ＋ **C 站點中明文標「診斷／排程用、不據以決定五類」者**，逐項附 WHY；後者現有：C4 `watch.py` L296 的 `plan_fn`（只取 `d_min` 決定 watch 的下一次 tick 時刻；判決另取）、C9 `kw_wake.py` L76（`qw_plan.plan` 決定保溫 ping 的時刻與 `wake_target`；叫醒時刻不是五類決定，五類決定由叫醒後的判決重算）、C13 `switchfacts.quota_facts()` 的 `qw_plan.plan`（只取 `d_min`／`stale` 供輪詢形態）、C17 `qw_cli.py` L44／L59（計畫細節診斷段，首行為判決行）。C 站點改接後若仍有一般呼叫（非上列），即屬漏改，鎖紅。
- 白名單常數住測試檔，每項附一句 WHY；改白名單＝改本節表（同一 commit）。
- 誠實劃界：AST 只看見直接呼叫；以 `getattr` 字串、`importlib` 動態呼叫的站點看不見；別名 import（`from lib.quota_gate import read_quota as rq`）由 AST 解析 import 別名後仍可認。

### 3.6 叫醒載具（F-03；REQ-AP-QV-11；判決之外的「誰在 reset 後叫醒主控」）

| 判決 | 窗口 | 載具 | 叫醒目標 |
|---|---|---|---|
| `WAIT_RESET` | 互動、模式 auto、未設 `AUTOSDD_KEEPWARM_OFF`、未交棒 | `sessionctl keepwarm`：`qw_plan.wake_target()` 新增來源 `ruling_wait_reset`（優先序：park 標記 → **判決 WAIT_RESET** → stage close／wall）。目標＝`win＋qw_calc.skew_min()`。此來源**不受** `skip_reason()` 的 `no_usage`／`small_ctx` 與保溫帳 n*（`cap`）限制：比照 R218「有 `wake_target` 時只有前四項會讓指令不掛」，且 n* 只計付費 ping、不計這一次單跳 | `win`＋時鐘容差 |
| `WAIT_RESET` | 無人窗口（`AUTOSDD_UNATTENDED`） | 無頭窗口不能等（print 模式背景上限會殺掉它，ADR-XPLAT-004 §2.12）⇒ 寫 handback 後結束，哨兵依判決武裝撞線等待（C11 擴及 `WAIT_RESET`），到 `win＋skew` 由既有無人續跑路徑接手 | 同上 |
| `WAIT_RESET` | 互動但模式非 auto 或設 `AUTOSDD_KEEPWARM_OFF` | 無程式載具：判決行理由句明寫「人已關閉自動換手／保溫：本視窗不會在重置後自動叫醒」（這是人的設定選擇，不是半路停工；Stop 半路停工判準把這個理由句視為合法換手標記） | — |
| `WAIT_RESET` | 已交棒 | 不適用（新 session 自己判） | — |
| `PARK` | 互動 auto | 既有 park 一次性排程（`AutoSDD_HandoffSpawn_*`） | `win＋skew` |
| `PARK` | 無人窗口／模式非 auto | park 拒絕（既有 rc 4）；無人窗口改哨兵（同 `WAIT_RESET` 無人列） | 同上 |
| `HALT_WEEKLY` | 全部 | 既有：哨兵撞線等待；互動另可 `park --at <週 reset>` | `wk`（spend 列無 reset ⇒ 走 `LIMIT_SPEND` escalate） |
| `NODISPATCH` | 全部 | 不需叫醒：在飛照跑；下一次 watch tick、保溫 ping 或工具呼叫時以 `expires_at` 重算 | — |

`wake_target` 回傳來源字串集合改為 `{park, ruling_wait_reset, reset, none}`；`kw_run` 對 `ruling_wait_reset` 只單跳不 ping（不付費）。

---

## 4. 有效期與陳舊判決（N5）

- 任何消費端拿到判決行（自己的 tool_result、watch 輸出檔、交接包）時，以 `expires_at` 對 `now`：過期 ⇒ 呼叫 `ruling_io.gather()` 重算，舊 vid 只寫進痕跡 `stale_verdict_recomputed {old_vid, new_vid, age_s}`，不據以行動。
- watch 的輸出檔在 harness 叫醒主控時可能已過期（AskUserQuestion 阻塞即此例，E5）；處置表第一列固定為「先 `sessionctl quota` 重算，再依新 ACTION 處置」。提問期間到達的事件同此（PRD R-4.5.12-4）。
- 交接包第 12／13 欄若含判決行，`--ack` 時一律重算（新 session 的 measured_at 必晚於舊包）。

---

## 5. park 參數變更（N6）

| 舊 | 新 | 遷移 |
|---|---|---|
| `park --why "<≥8 字>"`（未達門檻也登記） | `park --next-est <pp>`（數值，下一棒估計額度百分點） | `--why` 自 argparse 移除；CLAUDE.md〈換 session 的 SOP〉與記憶檔 `quota-stop-must-park.md` 的「未達門檻用 `park --why`」由 CLOSE 窗口同 commit 改寫 |
| `park --done --why` | 保留（`--done` 宣告「沒有剩餘工作」，不是推翻額度判決） | 無 |
| `park --at <ISO> --why` | `park --at <ISO>`＋判決須為 `HALT_WEEKLY` 或 `--next-est` 判放不下 | `--at` 的自由文字理由改寫入痕跡欄 `note`（只記錄、不參與判定） |

- **`next_est` 缺省值**（F-25）：未給 `--next-est` 時＝`qw_calc.cal_agent × max(1, n_plan)`（`cal_agent`＝QuotaWall 既有的每代理校準燒量；`n_plan`＝主控在交接包或派工意圖登記的下一棒代理數，缺＝在飛數 `n_live`）。模型給的值低於缺省值時取缺省值（只能往上調，方向保守：多 park、不少 park）。

---

## 6. 被取代條文與測試對照表（F-09；同一 commit 改，不留兩套語意）

| 被取代者 | 座標 | 新條文 | 處置（同 commit） |
|---|---|---|---|
| INV-H3 收斂版（halt 期間 `--pace` 不打 API） | PRD §4.5.10（已有【v2.1.28 註記】）；測試 `tools/tests/test_wake_chain_halt_r278.py::PaceReportShortCircuitsDuringHaltTest`（D23） | R-4.1.6-6 | WP-QV 改斷言為「halt 有效＋快取逾 TTL ⇒ 補量一次」，不註解、不刪類別；`quota_messages.halted_pace_text` 刪不補量分支 |
| 兩序列閂鎖 REQ-QW-75／REQ-QW-77（兩條同時成立兩句並陳；r9 W11d） | `docs/02_architecture/QuotaWall_CacheContinuity_Design.md`；`docs/03_testing/contracts/TCS-QuotaWall-20261120.md` 對應 AT／MU；PRD §16.6 2026-11-23 列；測試 `tools/tests/test_sessionctl_watch.py::QuotaSeriesLatchTests` | §3.5 C4／C5 單一序列 | 測試改斷言單一序列；QuotaWall DES 與 TCS-QuotaWall 由 CLOSE 追加【v2.1.28／v2.1.29 註記】列（只增不改）；被取代的 AT／MU 編號逐一列在註記內（實作棒以 `git grep -n "REQ-QW-7[5-7]" docs/03_testing` 現查） |
| W11b 後半：`--pace` 標題露短窗最高帶、`QUOTAWALL_PLAN=` 行（REQ-QW-79、AT-QW-93、MU-QW-62、E2E-QW-36） | `tools/tests/test_pace_quotawall_line_w11b2.py`；TCS-QuotaWall §8 | §3.5 C3（首行＝判決行；`QUOTAWALL_PLAN=` 降為診斷段第二行起） | 測試改斷言「首行為 `QUOTA_VERDICT=`、`QUOTAWALL_PLAN=` 仍在但不在首行」；TCS-QuotaWall 加註記 |
| ADR-XPLAT-004 §2.17 D3b（`park --why`）與驗收 AT-PK-46b | `docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` L1006；`docs/03_testing/contracts/TCS-SessionPark-20261116.md` L117 | R-4.1.6-5、§5 | ADR-004 §2.17 由 CLOSE 追加「D3b 由 v2.1.28 R-4.1.6-5 取代」註記（不改原文）；AT-PK-46b 改斷言 `--why` 為 argparse 錯誤並指路 `--next-est`，TCS-SessionPark 加註記 |
| ADR-XPLAT-004 §2.17 D9（park 拒絕訊息指路 `--at … --why`） | 同 ADR §2.17 | §3.5 C6 文案 | 同上註記；訊息鎖測試同 commit 改 |
| ADR-XPLAT-004 §2.15 配速床與趕工戳記的「餵給門檻判定的水位墊高」 | ADR-004 L780～L946 | §3.2 末：只影響 `cap`、不影響動作 | ADR-004 §2.15 追加註記：判決動作只看原始讀數；`pace_floor` 經 `dispatch_decision` 只改 cap |
| 根 CLAUDE.md〈換 session 的 SOP〉「`park --why`」「`park --at <ISO> --why`」 | 根 `CLAUDE.md` | §5 | CLOSE 同 commit 改寫 |
| 記憶檔 `quota-stop-must-park.md`（「未達門檻用 `park --why`」） | 使用者記憶目錄 | §5 | CLOSE 同 commit 改寫（記憶檔不在 repo，主控親改並於交卷列出） |

---

## 7. 換帳號偵測與標記作廢（AccountSwitch，§4.1.7）

### 7.1 零 API 觸發器（只負責「該重量了」）

| # | 觸發器 | 檢查站點 | 平台 |
|---|---|---|---|
| T① | `~/.claude/.credentials.json` 的 (mtime, size) 與上次記錄不同 | `context_budget_guard.py` PostToolUse（一行呼叫 `acctswitch.tick()`）、`watch` 每輪、哨兵 tick | Windows／Linux（macOS 缺席，照實劃界） |
| T② | 逐字稿自上次檢查位移後出現 `<command-name>/login</command-name>` | 同上（增量讀，記住 byte offset） | 全平台 |
| T③ | 任一次正常補量的 `account_key` 與快取上次不同 | `ruling_io.gather()` | 全平台 |

- T① 的上次記錄存 `~/.autosdd/traces/acct_probe.json`（經 `endurance_env.trace_dir()`，測試圍籬可攔，見 Autopilot 設計 N3）。
- token 自動刷新也會改 T①（多量一次，安全方向）。
- **觸發器成立即作廢的前提**：觸發器只觸發補量；作廢一律等補量取得新指紋後才判（R-4.1.7-3）。補量失敗（量不到）時不作廢、不保留判斷——標記照舊當輸入，下一次成功補量再判。

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

**落點決定（v1.1，F-10）**：判決純函式與判決行呈現＝**扁平共用單檔** `tools/lib/quota_ruling.py`（SSOT §2「單檔共用工具」格；只 import `quota_policy`；`quota` 前綴在 `PREFIX_ROSTER` 存量名冊內，不觸散落鎖）。取數、CLI、`--pace` 區塊＝sessionctl 套件內新檔 `ruling_io.py`；換帳號＝sessionctl 新檔 `acctswitch.py`。

WHY：SSOT §2 第一列「跨模組只准 import `tools/lib/` 的共用單檔，不得互相 import 對方套件」。v1.0 把純函式也放進 sessionctl，會讓三類消費端無路可走：扁平 hub `quota_gate`（C1 要改讀判決）、扁平 `session_brief`（C10）、SelfImproving 套件（C18）。v1.1 的依賴方向：

```
quota_policy ← quota_ruling（純函式；扁平）
                  ↑            ↑
quota_gate ───────┘            │（quota_gate 只 import quota_ruling 的型別與 line()；判決由 hook 注入）
sessionctl/ruling_io ──→ quota_gate.dispatch_decision、qw_plan、roster、quota_ruling
hooks／planner ──→ sessionctl/ruling_io（取判決）──→ 注入 quota_gate()、session_brief
selfimproving ──→ 子行程 `python tools/sessionctl.py quota --json`（走資料，不 import）
```

扁平檔（`quota_gate`、`session_brief`、`quota_escalation`、`relay_machine`）**不得 import `lib.sessionctl`**；需要判決時由呼叫端注入（`rule` 依賴或判決物件參數）。此約束由 `QV::SingleHouseTest` 同檔一條 AST 斷言釘住（扁平檔 import `sessionctl` 即紅）。

| 內容 | 落點（新檔標「新」） | 規則對應（SSOT §2） |
|---|---|---|
| 判決純函式、判決行、`billing_from_posture`、`brief_line` | 新 `tools/lib/quota_ruling.py` | 函式庫：單檔共用工具 |
| 取數快照、`rule_from_decision`、`pace_block`、`quota` 動詞實作 | 新 `tools/lib/sessionctl/ruling_io.py` | 函式庫（既有套件） |
| 換帳號觸發與作廢 | 新 `tools/lib/sessionctl/acctswitch.py` | 同上 |
| 派工閘管線抽出 | 既有 `tools/lib/quota_gate.py` 新函式 `dispatch_decision()`（自 `quota_gate()` 原樣搬出，同檔） | 存量 hub |
| CLI 動詞 | 既有入口 `tools/sessionctl.py` 加 `quota` 動詞（薄殼） | 指令入口列 |
| 測試 | 新 `tools/tests/test_sessionctl_qv.py`（判決＋換帳號＋單一家鎖同一檔，壓低新檔數） | 測試列；CLOSE 重釘 |
| 真機 E2E 案例 | `tools/lib/realverify/cases/` 新家族檔 `quotaverdict.py` | realverify 既有落點 |
| 痕跡 | `~/.autosdd/traces/`（`account_switch`、`stale_verdict_recomputed`、`acct_probe.json`） | repo 外，經 `endurance_env.trace_dir()` |
| CI 接線 | sessionctl 已在 compat-ci `paths`（`tools/lib/sessionctl/**`）；`tools/lib/quota_ruling.py` 為新扁平檔，CLOSE 加入兩支 compat-ci `paths`（`test_ci_paths_cover_root_consumers.py` 鎖） | CI 接線列 |
| 不可進化面 | `params.json` `non_evolvable_globs` 加 `tools/lib/quota_ruling.py`（守衛類） | 不可進化面列；CLOSE |
| 登記 | SSOT §3：新檔於實作 commit 後由 CLOSE 加反引號登記（規格階段只在 SSOT §3「autopilot＋QuotaVerdict」說明列以純文字預告） | §3 登記表 |

engine-bridge 閉包（SSOT §4 第 6 點）：`quota_ruling` 只被 `quota_gate`（頂層 import 型別）與 sessionctl import；`quota_gate` 不被 `quota_policy`／`transcript_activity` 頂層 import，故閉包不變。WP-QV 交卷時以 `tools/tests/test_ci_paths_cover_root_consumers.py` 與 engine-bridge 引用 `si_repo_support` 的測試實跑證明（記憶 `tools-lib-new-module-engine-bridge-closure`）。

---

## 9. LOC 牆處置（數字＝SD-0 當回合 `check_loc_budget.root_tools_reports()` 實量；實作前現查）

| 檔 | 現值／上限 | 本輪新增估計 | 抽出清單（先抽、再加；抽出與改接同 commit） | 抽出後餘裕估計 |
|---|---|---|---|---|
| `tools/session_resume_planner.py`（cli 750） | 750／750 | +4（哨兵讀判決） | ①`main()` 的 `args.pace` 區塊（L1568～L1582）→ `ruling_io.pace_block(args, deps)`，planner 留 2 行；②`_halt_marker_probe_path()`（L1515～L1524）→ `quota_halt_marker.py` | 約 +18 |
| `tools/lib/quota_messages.py`（lib 400） | 400／400 | +6（帳號比對、刪不補量分支約 −4） | `halt_verdict()`（L194～L239）與 `halt_marker_or_rejection()`（L254～L283）→ `tools/lib/quota_halt_marker.py`；`posture_line()` 的計費姿態推導 → `quota_ruling.billing_from_posture()`；`quota_messages` 留 re-export 一行 | 約 +70 |
| `tools/lib/quota_gate.py`（hub 500） | 496／500 | +10（`dispatch_decision` 簽章與回傳、`rule` 注入、閂鎖鍵 acct；`quota_gate()` 本體以判決取代 L1053～L1112 後淨減） | `pace_report()`（L912～L987）→ `ruling_io.pace_report()`；呼叫端（planner、`qw_cli`、測試）以 `git grep -n pace_report` 全數改接，`quota_gate` 不留 delegate（hub 成員清單只縮不長） | 約 +60 |
| `tools/lib/session_brief.py`（lib 400） | 398／400 | +2 | `quota_line()`（L219～L250）→ `quota_ruling.brief_line()`；L505～L506 第二處改讀注入判決 | 約 +28 |
| `tools/lib/quota_escalation.py`（lib 400） | 400／400 | 0（L335 同行數替換） | 若替換超出一行：把 L335 所在的判帶函式整段（實作棒現查邊界）搬到 `quota_halt_marker.py`（escalation 判定的自然家同為 halt 族） | 0 |
| `.claude/hooks/context_budget_guard.py`（special 1104） | 1104／1104 | +5（PostToolUse 呼叫 `acctswitch.tick()`、PreToolUse 傳 `rule` 依賴） | `_known_table_cache_path()`／`known_model_windows_path()`／`load_known_model_windows()`（L380～L447）→ 新扁平檔 `tools/lib/model_window_table.py`（前綴 `model` 現 1 支，加入後 2 支 <3）；CLOSE 把 `SPECIAL_FILES` 該檔門檻下修為新實值（棘輪雙邊咬人） | 約 +53，門檻下修後歸 0 |
| `tools/lib/relay_machine.py`、`sessionctl/switchfacts.py`、`handoff_build.py`、`converge.py`、`qw_guard.py`（擋派分支退役，淨減）、`qw_verdict.py`、`qw_cli.py`、`qw_plan.py`、`kw_wake.py`、`kw_run.py`、SI `sched.py`／`patrol.py`／`fourq.py` | 現查 | 各 ≤ +15 | 實作棒逐檔現查；任一檔超過分級 90% 時先列抽出清單交主控 | — |
| 其他觸及檔 | `watch.py` 283、`watch_wake.py` 142、`keepwarm.py` 220、`park_cli.py` 320、`park_reset.py` 61、`quota_rush.py` 186、`quota_halt_marker.py` 20、`quota_meter.py` 327、`check_claim_provenance.py` 510／750 | 各 ≤ +30 | 不需抽出 | — |

抽出原則：只搬、不改行為（搬移 commit 與行為變更 commit 分開，搬移那一個 commit 全套必須綠，證明搬移零行為差異）。

---

## 10. 持有面表（鐵律七）

| 鎖／機制 | 常數 | 史料 | 消費端 | 唯一持有者 |
|---|---|---|---|---|
| 判決決策表 | `quota_ruling.py`（`QV_WAIT_RESET_MIN` 讀 `quota_policy`） | PRD §4.1.6、本檔 §3.2 | §3.5.1 C1～C21 | WP-QV |
| 單一家白名單 `RULING_INPUT_SITES` | `tools/tests/test_sessionctl_qv.py` | 本檔 §3.5.2 | 全 repo 判讀站點 | WP-QV（改白名單＝改 §3.5 同 commit） |
| 派工閘管線 `dispatch_decision` | `quota_gate.py` | 本檔 §3.1 | 判決、C1 | WP-QV |
| halt 標記 schema | `quota_halt_marker.py` | 痕跡目錄 | `quota_messages`、planner、`acctswitch` | WP-AC（在 WP-QV 收工並親驗後） |
| rush 戳記 schema | `quota_rush.py` | — | `quota_pace_floor`、`statuscmd` | WP-AC |
| watch 閂鎖鍵 | `keepwarm.py` | — | `watch_wake.py` | WP-QV |
| 叫醒來源 `ruling_wait_reset` | `qw_plan.py`、`kw_run.py` | 本檔 §3.6 | keepwarm、哨兵 | WP-QV |
| `ENV_SPEC` 新鍵 `QV_WAIT_RESET_MIN` | `quota_policy_env.py` | `env.shared` 不改（別名） | `quota_ruling` | WP-QV |
| SelfImproving 判決消費 | `selfimproving/sched.py`、`patrol.py`、`fourq.py` | SelfImproving_PRD AC-SI-30-1／NFR-SI-07-5／FC-l 註記 | SI 巡邏 | WP-QV（SI 套件只改消費端；`sched.py` 的既有 SI 測試改斷言同 commit） |
| `SPECIAL_FILES` 門檻、c1c2、`_TREE_FILE_FLOORS` | `AutoClaude/tools/check_loc_budget.py`、`tools/tests/test_adr_xplat001_c1c2_lock.py`、`tools/lib/skip_tag_policy.py` | 兩站點 guard-total | 全套 | **CLOSE 單一窗口**（並行包只回報建議值） |
| `.claude/hooks/*` 改動 | — | — | — | WP-HOOK（staged diff 交主控親套；本檔涉及 `context_budget_guard.py` 兩處、`check_claim_provenance.py` 新族） |
| 帳本 | — | — | — | CLOSE |

WP-QV 與 WP-AC 動同一組 quota 檔 ⇒ **串行**。SI 套件測試（`tools/tests/test_selfimproving_*`）與 WP-QV 同持有面 ⇒ 不得另派並行包改。

---

## 11. 守衛面准入：暴露證據座標（每個觸及守衛面的條目）

| 條目 | 守衛面檔 | 暴露證據（三取一：真實逐字稿實際發生） |
|---|---|---|
| 判決函式與改接 | `tools/lib/sessionctl/**`、`tools/lib/quota_messages.py`、`tools/lib/quota_gate.py`、`tools/session_resume_planner.py`、`tools/lib/session_brief.py`、新 `tools/lib/quota_ruling.py` | E1（L2447）、E2（`watch9.log` 03:46）、E5（L2445） |
| 派工閘改讀判決（C1） | `tools/lib/quota_gate.py`、`.claude/hooks/context_budget_guard.py` | E1：同一回合 `--pace` 與派工閘各自判讀而矛盾（L2447）；QA-S F-01 普查 |
| park `--why` 退役 | `tools/lib/sessionctl/park_reset.py`、`park_cli.py` | E4（L2504→L2508） |
| halt 不壓補量 | `tools/lib/quota_messages.py` | E1、E3（L210） |
| 標記綁帳號與作廢 | `tools/lib/quota_halt_marker.py`、`quota_rush.py`、`sessionctl/keepwarm.py`、`.claude/hooks/context_budget_guard.py` | E3（halt 標記原檔無帳號欄、L173、L210）、E7（`quota_burn` 空洞） |
| WAIT_RESET 叫醒載具 | `sessionctl/qw_plan.py`、`kw_run.py` | E2（03:46 stage=free、87%、D=14：判決若為 WAIT_RESET 而無載具＝第六類停） |
| Stop 宣稱守衛 QV 族 | `.claude/hooks/check_claim_provenance.py` | E6（L2553、L2564） |
| `context_budget_guard` 抽出 `model_window_table` | `.claude/hooks/context_budget_guard.py`、新 `tools/lib/model_window_table.py` | 純搬移（LOC 牆前置），附屬於上一列 AC 觸發器的證據；新檔納入守衛面清單（CLOSE 改根 CLAUDE.md〈守衛面准入〉） |

`tools/lib/sessionctl/**` 已在守衛面清單內，`ruling_io.py`／`acctswitch.py` 自動屬之；`tools/lib/quota_ruling.py` 與 `tools/lib/model_window_table.py` 需加（CLOSE 改根 CLAUDE.md〈守衛面准入〉的清單；`quota_ruling` 與既有 `quota_gate`、`quota_policy` 同列）。

---

## 12. 修復不留後遺症三問

1. **另一台機器會不會回來？** 判準只吃 state 與標記；`account_key` 取自伺服器標頭、跨平台相同；macOS 缺 T① 已照實劃界，T②T③ 仍成立；`WAIT_RESET` 的無人窗口路徑不依賴 keepwarm（mac 的無頭窗同樣交哨兵；mac 睡眠邊界沿根 CLAUDE.md 既有劃界）。
2. **有沒有文件／座標不一致？** §6 對照表逐項列出被取代的條文與測試，PRD v2.1.28／v2.1.29、本檔、TCS、CLAUDE.md、兩份 SelfImproving PRD 註記、記憶檔、QuotaWall DES／TCS-QuotaWall／TCS-SessionPark／ADR-004 註記，由 WP-QV＋CLOSE 同 commit 收齊；舊兩序列與 `--why` 同 commit 刪除。
3. **有沒有「之後再看」？** N8（Stop 額度推回噪音）依 AP-A 報告登記〈理論洞清單〉，CLOSE 清單已列（APD §12）；`QUOTA_BURNDOWN_OFF` 等由 agent 子行程可覆寫的判決輸入（APD §5 普查結果）登記理論洞。除此之外無。

---

## 13. 與 AP-A 報告的差異（SD-0 決定，v1.1 部分改寫）

| 項 | AP-A | SD-0 | SD-1 | WHY |
|---|---|---|---|---|
| 落點 | `tools/lib/quotaverdict/` 套件 | `tools/lib/sessionctl/qv_*.py` | 純函式扁平 `quota_ruling.py`＋sessionctl `ruling_io`／`acctswitch` | SSOT §2 禁止套件互相 import；扁平消費端與 SI 需要一個不屬任何套件的判決家（§8） |
| `quota_gate` 餘裕 | 0 | 4（實量 496／500） | 同 | 當回合實量；結論不變（仍需抽出） |
| `/login` 觸發器 | 待查 hook | 官方文件證實無專屬事件；`auth_success` 不採用 | 同 | §2 |
| `QV_WAIT_RESET_MIN` | 預設＝保溫分鐘數 | 別名同一數、不另設新值 | 同 | 不讓兩個數各自漂移 |
| `pace_report` | 未定 | 搬入 `qv_render`，hub 不留 delegate | 搬入 `ruling_io` | hub 成員只縮不長 |
| 量不到 | — | `NODISPATCH` | `CONTINUE`＋`deg=unmeasured`＋降級 cap | R-4.1.5-1 禁止 cap=0（F-02） |
| QV 與 AC 測試 | 未定 | 同一新測試檔 | 同（加單一家鎖） | 壓低重釘稅 |

---

## 14. v1.0 → v1.1 處置索引（QA-S 報告 `qa_spec_report.md` 發現編號）

| 發現 | 本檔落點 |
|---|---|
| F-01 單一判決有縫 | §3.1 `decision`、§3.2 cap、§3.5 普查表 C1～C20／B1～B5、§3.5.3 機械鎖 |
| F-02 量不到與 R-4.1.5-1 衝突 | §3.2 第 6 列、§3.3 `deg=`、§0 第 4 點 |
| F-03 WAIT_RESET 無叫醒載具 | §3.6 |
| F-06 模型分軌 | §3.1 `model`、§3.2 第 2 列 |
| F-07 PARK 對量不到 reset 死循環 | §3.2 第 3、5 列、§3.5 C6 |
| F-08 spend 軸、配速床、rush | §3.2 第 1 列與末段；rush 定性見 PRD R-4.1.6-5【v2.1.29 勘誤】 |
| F-09 被取代者清單（QV 面） | §6 |
| F-10 落點與命名 | 命名段、§8 |
| F-19 不可用狀態的 `expires_at` | §3.3 |
| F-25 `next_est` 缺省值 | §5 |
| 主控代決 ①（SI 改讀判決） | §3.5 C18、§8、§10 |

---

## 15. v1.1 → v1.2 處置索引（QA 複審 `qa_spec2_report.md` 發現編號）

| 發現 | 本檔落點 |
|---|---|
| N-01 普查漏 park 提前恢復（parkearly／parkprobe）與換手計畫 park 分支（switchplan） | §3.5.1 C13 擴寫、新 C21；PRD R-4.1.6-2【v2.1.29 勘誤（續）】 |
| N-02 鎖看不見包裝入口與門檻比較 | §3.5 普查方法、§3.5.2 B1 補包裝入口、§3.5.3 (i)(ii) 兩類站點；C3 補 `halted_pace_text` |
| N-07 `draining()` 誤列 B1 | §3.5.2 新 B6 |
| N-09 白名單定義使鎖無法綠 | §3.5.3 白名單定義（含診斷／排程用 C 站點逐項 WHY） |
| N-10 `park --done` 上限未列 | §3.5.2 新 B7 |
| N-06 `plan.cap` 不存在、與 PRD「cap 唯一來源」衝突 | §3.1 `plan` 列、§3.2 `cap` 段（只取 `decision.cap`；`None` ⇒ `max_fanout`） |
