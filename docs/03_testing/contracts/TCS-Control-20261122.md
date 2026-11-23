# TCS-Control-20261122：背景代理的主控掌控、自動換 session 演算法與新 session 接續——需求＋驗收合一

> 🔒 **凍結（spec-frozen，2026-11-22）**：與 `docs/02_architecture/Control_Handover_Design.md` r3 同批凍結；approver、reason 與親驗座標見該檔檔頭凍結紀錄。計數 REQ 48／AT 92／E2E 24（RV-CTL01～24）／MU 49。

> 角色：SD（W2-SD，AISDLC 第 2 階段）。版次 **r3（r2 依 QA 規格審查 FAIL〔P2×8、P3×7〕改版；r3 依 QA 窄範圍複審〔新增 P2×2、P3×3〕小修，待再審）**。**r3 變更摘要**（計數不變：REQ 48、AT 92、E2E 24、MU 49；處置＝DES §22.1）：新葉模組 `parkearly.py`（early 入口 `tick`／`fire_early`，`parkprobe` 退為純判準、import 方向單向無環；REQ-CTL-46；AT-CTL-58／59／90）、`park_cli.py` 行數牆補列（393／400；REQ-CTL-46；AT-CTL-90）、封存閘條件改「`none` 或 `invalidated`」（REQ-CTL-25）、`ensure_pending` 呼叫點刪封存閘 Stop（AT-CTL-86）、§7 第 5 項改 TH-1～TH-8、REQ-CTL-45 模組數 11。r2 變更摘要：`sealed_effective` 四值（REQ-CTL-01；AT-CTL-05／83／84）、pending 只認硬線且封存閘觸發條件不改（REQ-CTL-23／25；AT-CTL-43／50／52／86）、`account_changed` 基準＝park 標記 `parked_account`（REQ-CTL-27／34；AT-CTL-87）、新增 REQ-CTL-47（ack 後撤 park）／48（A6 迴歸量測）與 E2E-CTL-24、PRD 鎖改釘修憲前 blob（REQ-CTL-44；AT-CTL-75／89；E2E-CTL-21；MU-CTL-39）、E2E-CTL-01 戳時刻改取 2221／2468 行附近時戳、新增 AT-CTL-85～92 與 MU-CTL-43～49。處置總表＝DES §22。設計全文＝`docs/02_architecture/Control_Handover_Design.md`（下稱 **DES**）；上游＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 **PRD**；修訂表 v2.1.26 列、§16.6 2026-11-22 兩列）。
> 前綴：`REQ-CTL-`、`AT-CTL-`（單元／整合，縫注入）、`E2E-CTL-`（真機）、`MU-CTL-`（突變，必須讓指定測試轉紅）。計數：**REQ 48、AT 92、E2E 24、MU 49**（自檢＝AT-CTL-76）。
> 🔴 掌舵者 2026-11-18／2026-11-22：每個功能都要有真機 E2E（真行程／真排程／真 `claude -p` 子行程／真 hook／真逐字稿重放才算，單元測試不算）；結果入 `docs/06_quality/RealVerify_Result_Ledger.md`，未入帳＝未結；AutoClaude 自己驗不完的項目算 BUG。
> 測試慣例沿用 sessionctl：時間注入 `now`、路徑圍籬 tmp（含 `trace_dir`）、不讀本機真實 `~/.claude`（E2E 除外）、不開測試用環境變數鉤、禁用 skip。**載具必須能觸發被測 bug**：凡「修前紅」的案例，測試內自帶舊實作的 oracle 複本，先證明夾具確實觸發舊行為（記憶〈驗證載具要能觸發 bug〉），再證明新行為不觸發。

## 0. 模組落點表
照 DES §16（本檔不重抄）。

## 1. 需求（REQ）

### 1.1 控制語意（W1；DES §3～§4）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-01 | `control.sealed_effective(stamp, transcript)` **四值**：戳檔不存在 ⇒ `none`（從未封存，不論逐字稿）；戳存在但解析失敗或逐字稿讀不到 ⇒ `unreadable`；戳之後主控逐字稿無「非唯讀、非監督」`tool_use` ⇒ `effective`；有 ⇒ `invalidated`。各消費端對四值的行為依 DES §3.2 表逐格寫死（尤其：`none` 且 ctx≥硬線 且未交棒 ⇒ 封存閘照舊推「未封存」）。`transcript_activity.worked_since` 增 `ignore` 參數，預設 `None` 時行為逐字不變；`unreadable` 由 `control._readable` 先驗，不改 `worked_since` 的讀不到回 False | §3.2 | W1 |
| REQ-CTL-02 | A4：冷叫醒閘（`converge._finalized_wake`）對「已封存、未交棒」只在 `sealed_effective == "effective"` 時才可能推；`none`／`unreadable`／`invalidated` ⇒ 不推。封存後派工（`Agent`／`Task`／`SendMessage`／寫入／其他 shell）使封存失效；再 finalize 即重封存 | §4 | W1 |
| REQ-CTL-03 | 冷叫醒閘只在兩種情形推 TaskStop：①真交棒（`handed_over`）⇒ 全部在飛任務；②封存有效 ⇒ **只**列「非監督、非代理」的背景 shell。封存有效而有在飛代理 ⇒ 不推（交給監督閘）；keepwarm 與 watch shell 皆豁免 | §0.3 D-CT-3、§4.2 | W1 |
| REQ-CTL-04 | 單一謂詞（含既有測試遷移：`wake_package` 預設無逐字稿時封存分支回 `None`，既有斷言補傳逐字稿夾具，不放寬斷言）：`sessionctl/` 內除 `control.py` 外不得直接呼叫 `worked_since(`；封存閘（`seal.stop_verdict`）與冷叫醒閘對同一組輸入（封存戳＋之後工作＋在飛代理）給出一致結論；`park`／`keepwarm`／`status` 等監督呼叫不使封存失效 | §4.1、§4.3 | W1 |
| REQ-CTL-05 | `control.is_supervision_call(block)` 文法：工具名 ∈ `{TaskStop, TaskOutput, BashOutput, AskUserQuestion}`；或 PowerShell／Bash 且以 `;`／`&&`／`\|\|`／換行切段後每一段屬 `sessionctl.py (handoff｜park｜status｜keepwarm｜watch｜runlong｜waitfor｜quotawall｜switch-plan)` 或對其輸出檔的唯讀讀取；任一段不屬或解析不出 ⇒ 算工作 | §3.3 | W1 |
| REQ-CTL-06 | `control_state(payload, sid, env)` 回 `ControlState`（DES §3.4 全部欄位）；憑證值（pid、心跳年齡、排程 `next_run`）取自行程表／心跳檔／排程器，**不取自主控自述或標記文字**；量不到的欄位寫 `None`／`?`，不猜 | §3.4 | W1、W3 |
| REQ-CTL-07 | CI-1(d) 互斥：於狀態乘積（在飛代理 0／1 × 監督有／無 × 封存 none／unreadable／effective／invalidated × 已交棒 是／否 × 背景 shell 無／ci_wait／watch／keepwarm ＝ 128 態）下，`converge.stop_verdict` 的單一輸出不同時含「TaskStop 在飛代理」與「掛 watch 監督在飛代理」；已交棒且有在飛代理 ⇒ 只有 TaskStop | §2.1 | W1 |

### 1.2 監督單例（W2；DES §5）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-08 | 同 sid 已有活 watch ⇒ 後到者印 `WATCH_VERDICT=duplicate`、rc 0 立即結束、不寫心跳；先到者贏；持有者判活＝pid＋行程建立時間（pid 被重用 ⇒ 接手）；鎖檔寫不進 ⇒ 視為取得（互斥是優化，不是監督的前提） | §5 | W2 |
| REQ-CTL-09 | 心跳檔鍵 `<sid>.<pid>.json`；先結束者只刪自己的檔；寫出只有新格式 | §5 | W2 |
| REQ-CTL-10 | `supervise.read_heartbeat(sid)` 取 `<sid>.*.json` 與舊 `<sid>.json` 中最新且新鮮者（舊格式相容讀一輪） | §5 | W2 |

### 1.3 可見（W3；DES §6）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-11 | 名冊預設範圍：無 sid 且非 `--all-projects` ⇒ 只掃本 repo 專案 slug；slug 算法沿 `handoff._project_dir`；有 sid ⇒ 行為不變 | §6.1 | W3 |
| REQ-CTL-12 | `status --all-projects` 保留舊行為且標記沙盒項；預設輸出末尾印「另有 N 支代理在其他專案／沙盒」一行，不靜默隱藏 | §6.1 | W3 |
| REQ-CTL-13 | 沙盒子代理（`sandbox_scope.SLUG_FRAGMENT` 所在 slug）預設不列為背景代理／殘局；負控：本 repo 真專案殘局仍列；slug 判準只 import `sandbox_scope` 常數，不另寫 pattern | §6.2 | W3 |
| REQ-CTL-14 | SessionStart 簡報加一行：本 repo 範圍內上一個 session 有 N 支代理未收尾（殘局）／M 支被額度切斷（附 `status` 與第 12 欄指路）；沙盒 slug 不公告；不假設 `claude -r` 後代理可接回 | §6.3 | W3 |
| REQ-CTL-15 | `sessionctl status` 在名冊前印 `control:` 一行（欄位依 DES §3.4）；`--json` 帶 `control` 物件；`park --status` 等排程憑證值取自排程器自報（`--verify`）或心跳，不取自述 | §6.3 | W3 |
| REQ-CTL-16 | statusLine 區段：`tools/statusline_context_feed.py::ui_line` 在有內容時於行尾加分隔字串「空白 \| 空白」＋ 純 ASCII 區段（`ctl: 2 agents watch ok`／`NO WATCH`／`CUT`／`sealed`／`HANDED-OVER`／`switch pending`）；無內容回空字串使既有輸出逐字不變；`segment` 帶 10 秒檔案快取、150 ms 時限、任何例外回空字串；不改 `.claude/**` | §6.5 | W3 |

### 1.4 交接包與接續（W4；DES §9）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-17 | 機械層第 12 欄「在飛／被切代理」（`MECH_HEADINGS` **末尾追加**，欄 1～11 順序與編號不變）：每列 `id｜描述｜模型｜狀態｜ctx｜任務書指標（代理首筆 user 記錄前 600 字）｜代理逐字稿路徑｜輸出落點（Write／Edit 的 `file_path` 去重至多 8 個＋任務書內 scratchpad／handback 路徑）｜最後 3 則 assistant 摘要｜建議處置`；量不到寫「量不到：原因」；**大小上限**：每則 assistant 摘要 ≤`BRIEF_CHARS`、至多 `LAST_TEXTS` 則、全欄 ≤`COL12_MAX_CHARS`，超出從最舊列截斷並寫「已截斷 N 列」；一律不含 `tool_result` 內容（只取 `type=text`） | §9.1、§9.2 | W4 |
| REQ-CTL-18 | 機械層第 13 欄「鏈上前幾棒」：沿 `.ack` 的接手者 sid 往回走至多 5 棒（防環；同一 sid 有多個包時，每步取「`.ack` 內 `sid=` 為當前 sid 者中 `.ack` 時刻最早的包」，多指向註記「另有 N 個包同接手者」，找不到即止並註「鏈止於 <sid>」）；全欄 ≤`COL13_MAX_CHARS`、真人提示摘錄每則 ≤`PROMPT_EXCERPT_CHARS`、至多 `LAST_PROMPTS` 則、不含 `tool_result`；每棒列棒 sid、封存時刻、`<包 stem>.prompts.md` 路徑、最近 3 則真人提示前 200 字、該棒 scratchpad ★檔（`RESTART_POINT`／`BRIEF`／`HB_`／`*_report.md`，至多 12 檔）；無前鏈寫「（無前鏈）」；欄 1 加主控模型、欄 3 加 `git worktree list`、欄 12 後附未結 OI id 一行（重用 `session_brief_oi`，量不到寫量不到） | §9.2、§9.3 | W4 |
| REQ-CTL-19 | 被切／被殺／殘局判準：`usage_limit`（代理末筆記錄 `apiError` 含 `usage_limit_reached`，或末筆 `<synthetic>` 含 `hit your`／`usage limit`）、`stopped`（`rosterscan.killed_ids`）、`residue`（既有）；每筆附重派指標「新代理＋短任務書，不 SendMessage 續舊代理」 | §6.4 | W4 |
| REQ-CTL-20 | 被切代理清單在主控下一回合出聲三處且同一份文字：Stop `systemMessage`（該 sid 每次被切只提示一次）、`watch` 判決處置字尾、SessionStart 公告；**不自動重派** | §6.4 | W4 |
| REQ-CTL-21 | 負向：`handoff.finalize` 仍只驗結構（前四節非空、無 `TODO:`）；「已驗證：（無）」仍通過；不加任何內容檢查 | §9.4 | W4 |

### 1.5 自動換手演算法（W5；DES §7）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-22 | `switchplan.decide(Inputs)` 為純函式，依 DES §7.2 決策表自上而下第一個命中即回；動作集合 `{STAY, SWITCH_NOW, SWITCH_AFTER_DRAIN, PARK_UNTIL, PARK_POLL}`；輸出 `reason`、`flags(keepwarm, prefer_fresh)`、`carrier`、`credential`；`ctx` 為 None ⇒ H、F 不成立 | §7.2 | W5 |
| REQ-CTL-23 | `pending_switch`：檔 `trace_dir()/switch/<sid>.pending`（`reason` **只有 `hard`**、`since`、`ctx`）；**R2 不寫 pending**；`switchplan.ensure_pending` 惰性冪等建立（條件＝`ctx ≥ hard` ∧ 在飛代理 > 0 ∧ 無檔；不經 `advise_once`、不依賴 `.advised` 閂鎖；已有檔不覆寫 `since`），`switchplan.read_pending` 讀；作廢＝`sealed_effective == "effective"` ∨ `handed_over` ∨（`ctx` 量得到 ∧ `ctx < hard`）；`ctx` 量不到不作廢；同 (sid, 原因) 的 `advise_once` 出聲只一次 | §7.4、D-CT-5／11 | W5 |
| REQ-CTL-24 | `watch` 於代理全數交卷且有效 pending ⇒ `WATCH_VERDICT=switch_due`（rc 0；處置＝finalize→spawn、不再派新代理）；無 pending ⇒ 既有 all-done 判決不變 | §7.4 | W5 |
| REQ-CTL-25 | **負向（r2）**：封存閘觸發條件**不改**——仍是 `ctx ≥ hard` ∧ 無在飛代理 ∧ 未交棒 ∧ `sealed_effective` 為 `none` 或 `invalidated`（`none` 照推「未封存」、`invalidated` 推「封存後有工作」、`unreadable` 不推）；pending 不是新推回條件；**R2 session 零新增推回**；在飛代理 ⇒ 不推；`park`／`keepwarm` 呼叫不使封存失效（REQ-CTL-04） | §7.4 | W5 |
| REQ-CTL-26 | 防抖：`since_takeover_min < DEBOUNCE_MIN(30)` ⇒ STAY（W 列不受限、H 列受限）；常數住 `switchplan` | §7.3 | W5 |
| REQ-CTL-27 | `account_changed`＝park 標記 `parked_account`（登記當下 `quota_meter.account_key_of()` 的 `account_key`）與當下快取 `account_key` 皆非 `None` 且不相等；只把 `cache` 視為 `cold`；**不新增任何推回**；任一側 `None`（量不到、舊標記無此欄、無 park 標記）⇒ `account_changed=False`（量不到不當作變更）。基準欄名常數 `MK_PARKED_ACCOUNT` 住 `parkprobe.py`（不進 `qw_schema`）；`_cmd_park` 登記時寫入（量不到寫 `null`）；`park.marker_problem` 不拒未知欄、`_settle` 保留未知欄 | §0.3 D-CT-8／9、§8.2 | W5、W6 |
| REQ-CTL-28 | 負向：`switchplan` 無新增上下文門檻（只呼叫 `switch.threshold`／`costmodel`）、無軟線／便宜線；任何 hook 與 `decide` 路徑不呼叫 `handoff.spawn`（hook 不代主控 finalize／spawn，TH-1）；不自動重派被切代理（只列清單） | §7、§12 | W5 |
| REQ-CTL-29 | `handoff.advise_once` 每次出聲落痕跡 `switch_advise`（sid、reason、ctx、K、mode） | §10 | W5 |
| REQ-CTL-30 | 新動詞 `python tools/sessionctl.py switch-plan [--sid S] [--json]`：唯讀、零 token，印 Inputs、Decision、reason、carrier、credential；rc 0（量不到的輸入標「量不到」） | §7 | W5 |

### 1.6 park 等待期間額度提前恢復（W6；DES §8）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-31 | 哨兵巡邏分支次序：SE L1 tick 判準 → 提前恢復探針 → `park.yields` 讓路 → QW §7.6 接手；前置＝標記 `armed` ∧ `valid_until` 內 ∧ 剩餘等待 ≥ `EARLY_MIN_WAIT_MIN(60)` ∧ 包 live、未 `.ack`、未 `handed_over`（含 `spawning`）∧ 非無人窗口、模式 auto | §8.3 | W6 |
| REQ-CTL-32 | `park.recovered`：讀數取自 `park._pace_state`（TTL≥180 秒；陳舊先補量、補不到不判）；`recovered ⇔ parked_pct 存在 ∧ cur ≤ parked_pct − EARLY_DROP_PP(5) ∧ cur < prepare_pct`，`cur＝max(非 FALLBACK、非 MODEL_SCOPED 的短窗軸∪週軸 pct)`；舊標記無 `parked_pct` ⇒ 不判、出聲 `absent(no_baseline)` | §8.2 | W6 |
| REQ-CTL-33 | 提前觸發走既有 `_cmd_fire`（`opts.early=True`）：§7.2 前置、`live_driver`、`handed_over`／`spawning` 去重、§7.4 選路與活窗 fork／FRESH、§7.5 失敗鏈、§7.6 接手全照 QW；**僅**停用 §7.3 分支 A 的重排；`early=False` 的所有現行路徑與黃金序列逐字不變 | §8.3 | W6 |
| REQ-CTL-34 | `account_changed`（REQ-CTL-27 判準，基準取自標記 `parked_account`）為真 ⇒ `park.fire_route(held, cold=True)`：大上下文判 FRESH 帶交接包、小上下文 RESUME（活窗 fork）；`prefer_fresh`（R2）照舊 | §8.3 | W6 |
| REQ-CTL-35 | 降級出聲：讀不到／陳舊補不到 ⇒ 痕跡 `park_early_probe reason=unmeasured`、不觸發、不報錯；SessionStart 對「armed park 且探針連續 unmeasured」加一行 | §8.5 | W6 |
| REQ-CTL-36 | `park --status` 加一列 `early_probe: next_probe=<哨兵 NextRunTime> last=<ISO> reading=<pct> baseline=<parked_pct>`；`park` 登記末行含 `early_probe=armed｜absent(reason)`；兩稿各自加列、互不改對方列（SE X-22） | §8.4 | W6 |
| REQ-CTL-37 | 不誤觸發：`live_driver`、`handed_over`、`spawning` 意圖、剩餘等待 < 60 分、讀數未降、降幅 < 5pp、降了但仍 ≥ 準備門檻、同一標記已觸發過（至多一次）——全部不觸發；`park --why` 在未達門檻時登記的標記不因絕對值低而觸發 | §8.2、§8.3 | W6 |
| REQ-CTL-38 | 哨兵缺席（`AUTOSDD_SENTINEL_OFF`／拒絕武裝）⇒ 照實印 `early_probe=absent(reason)`，不假設探針存在；PRD §15.5 紅線 1 豁免四條件：唯讀 GET、單一站點（`quota_meter.py`）、TTL≥180 秒、失效降級出聲 | §8.5 | W6 |

### 1.7 量測（W5；DES §10）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-39 | M-W1 修正：憑證判準讀真實憑證（payload／心跳／`watchlock`）；舊口徑（恆無憑證）並行出數並標「上界」 | §10 | W5 |
| REQ-CTL-40 | M-C1：封存後派工被冷叫醒推回的件數（A4 回歸率；目標 0）；以 `control_cold_wake_exempt` 為分母事件 | §10 | W5 |
| REQ-CTL-41 | M-C2（手貼接續比率、新 session 第一小時回頭讀舊資料）、M-C3（提前恢復件數與節省分鐘、unmeasured 比率）、M-C4（`switch_plan` 分佈）、M-C5（冷回 F4 判換新但未封存件數）；判準在 `wastecensus/sections_ctl.py` | §10 | W5 |
| REQ-CTL-42 | `python tools/probe/waste_census.py --replay-plan`：以 `decide`／`park.recovered` 重放近 14 天母體（支援 `--population` 快照），輸出 DES §7.6 同形表；判準函式即實作函式（不另寫第二份） | §7.6 | W5 |
| REQ-CTL-43 | 新痕跡事件名（`switch_advise`、`switch_plan`、`pending_switch_set`／`_due`／`_cleared`、`watch_duplicate`、`park_early_probe`、`park_early_recovered`、`control_cold_wake_exempt`）與 QW §13 事件名集合不相交 | §10 | W5、W6 |

### 1.8 規格與收尾（W0／W8）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-44 | PRD 只追加：修訂表 v2.1.26 列、§16.6 兩列、就地註記；**既有每一行位元組不變，機械鎖釘修憲前 blob `5af6ce952d701284642f199d19dd3daea58beca7`**：`git cat-file -p <blob>` 的每一行（逐字相等、不 strip）依序為工作樹 PRD 行序列的行級子序列；blob 取不到＝FAIL（不 skip）；提交前後皆有效；原文逐字 | §19 | W0 |
| REQ-CTL-45 | 連動面同 commit 收齊：TCS-SessionCtl AT-SC-34（13 欄）、`MECH_HEADINGS`、ADR 新節、根 CLAUDE.md 兩列、`Root_Layout` §3（11 個新模組〔r3 含 `parkearly`〕、6 個新測試檔）、棘輪重釘、CI paths 現查、QW／SE 追加註記（DES §17；r2 已無 N-3） | §17 | W8 |
| REQ-CTL-46 | 模組落點與工程約束：新檔照 DES §16；**LOC 分級無違規，且 `session_brief.py`／`session_resume_planner.py`／`handoff.py` 各包增量 ≤2 行（邏輯進 `briefline`／`parkprobe`／`parkearly`／`switchplan`，DES §21）；`park_cli.py`（現查 393／400）W6 合計 ≤4 行、W4b 淨 0（r3）**，交卷附當回合 `check_loc_budget.py --json`；`.claude/**` 零改動；守衛面清單不增成員；QW AT-QW-61 十一欄字面掃描在 W1～W6 後仍綠（`parked_pct`／`parked_account` 住 `parkprobe.py`，不在該清單）；`cases.json` 含 `RV-CTL01`～`RV-CTL24` | §16、§21 | W7、W8 |

### 1.9 r2 新增
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-CTL-47 | **ack 後撤原 session 的 park**（SA B4）：`handoff --ack` 成功後 `ackhook.on_ack(pkg, acker_sid, env)`：包擁有者 ≠ acker 且有 `armed` park 標記 ⇒ `park_cli.cancel_marker(owner_sid, event="acked")`（標記 `cancelled`、拆備援排程）；擁有者＝acker（自續跑）不撤；無標記／已非 armed ⇒ 冪等無動作；不新增排程站點；`_cmd_fire` 對 `.ack` 已有的 `skip("acked")` 不變（雙駕駛防線）；`_cmd_cancel` 既有行為與 AT 逐字不變 | §20.2、D-CT-12 | W4b |
| REQ-CTL-48 | **A6 迴歸量測**（SA A6）：M-C6＝無人窗口 session 中子代理被收尾／print 模式上限終止件數（讀既有逐字稿，目標 0，觀察不接閘門）；W7 的 E2E 一律不在無人窗口依賴 watch；不新增任何守衛（DEF-200-575／ADR §2.12 既有） | §20.1、§10 | W5 |

## 2. PRD 追溯
| REQ | PRD 座標 |
|---|---|
| 01～07、21、28 | §1.2 原則 1 後【v2.1.26 註記】（CI-1 控制權、CI-2 可見）；§4.3 交棒路線；§16.6 2026-11-22「監督掌控」列 |
| 08～16、39～41 | §4.5.7（閒置盲區延伸）、§9 可觀測性；§16.6 同列 |
| 17～20 | §4.5.4 喚醒成本（包內容完整性）、§11.3；§16.6「自動換手與接續」列 |
| 22～30、42 | §4.3、§4.5.4 同版註記；§16.6 同列 |
| 31～38 | §4.5.11 末【v2.1.26 註記】、§15.5 紅線 1 豁免四條件、QW §7；§16.6 同列 |
| 43～46 | §11.1～§11.9、§16.6 結案格 |
| 47（ack 撤 park） | §4.5.11 末【v2.1.26 註記】（park 等待期間）、§4.5.3；§16.6 2026-11-22「自動換手與接續」列 |
| 48（A6 迴歸量測） | §4.4.3、§4.5.4；§16.6 2026-11-22「監督掌控」列（承 DEF-200-575） |

## 3. 驗收測試（AT；縫：`NOW`、`FS`（tmp 圍籬含 `trace_dir`）、`ENV`、`TR`（合成或截取逐字稿）、`PL`（hook payload）、`PK`（包目錄）、`HB`（心跳）、`Q`（假 `pace_state`／`quota_meter` 讀數）、`SCH`（假排程後端）、`SP`（spawn 執行器）、`FS-CL`（假行程表與 `pid_alive`））

### 3.1 控制語意與 A4（W1）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-01 | 01 | 封存戳之後逐字稿無 `tool_use` ⇒ `sealed_effective == "effective"` |
| AT-CTL-02 | 01、02 | 戳後出現 `Agent`／`Task`／`SendMessage`／`Edit`／`Write`／非監督 PowerShell 各一 ⇒ 各自 `invalidated`（表驅動） |
| AT-CTL-03 | 01、04、05 | 戳後只有監督呼叫（`sessionctl.py park`／`keepwarm`／`watch`／`status`／`handoff`、`TaskStop`、`AskUserQuestion`、對 keepwarm 輸出檔的 `Get-Content`）⇒ `effective`；與 `Read`／`Grep`／`Glob` 混用仍 `effective` |
| AT-CTL-04 | 04 | 原始碼掃描：`tools/lib/sessionctl/*.py` 中除 `control.py` 外無 `worked_since(` 呼叫（`transcript_activity.py` 定義處與測試檔不計） |
| AT-CTL-05 | 01 | 戳存在但 ISO 解析失敗／逐字稿不存在或讀不到 ⇒ `unreadable`；`seal.stop_verdict` 見 `unreadable` 不推、`wake_package` 見 `unreadable` 不回封存分支 |
| AT-CTL-06 | 05 | `is_supervision_call` 表驅動：全段監督 ⇒ 真；`;` 後接 `git commit` ⇒ 假；解析不出（非字串 command）⇒ 假；`gc <keepwarm 輸出檔> \| Select-Object -Last 3` ⇒ 真；`sessionctl.py handoff --spawn` ⇒ 真；`ci_wait.py` ⇒ 假；`TaskOutput` ⇒ 真 |
| AT-CTL-07 | 01 | `worked_since(path, iso)`（無 `ignore`）對既有測試輸入逐字不變（既有案全綠＋新增位元組級對照） |
| AT-CTL-08 | 02 | 冷叫醒閘：已封存（有效戳）→ 戳後 `Agent` 派工 → 在飛代理 2 ∧ 未交棒 ⇒ `_finalized_wake` 回 `""`；夾具內含**舊實作 oracle**（舊 `wake_package`），先斷言舊 oracle 在同夾具回「有包」（證明夾具觸發舊 bug） |
| AT-CTL-09 | 02、03 | 以 65389f03 第 2253～2335 行的真實形狀重建 payload：`background_tasks`＝2 支 running 代理＋1 支 `sessionctl.py watch` shell；`sessionctl_guard` Stop 全鏈（`converge.stop_verdict`）⇒ `""`；第 2468～2519 行同法（重封存後再派）⇒ `""` |
| AT-CTL-10 | 03 | 封存有效、無在飛代理、有 `ci_wait.py` 背景 shell ⇒ 推 TaskStop 且訊息只列該 shell |
| AT-CTL-11 | 03、07 | 封存有效＋在飛代理＋watch 憑證有效 ⇒ `""`；同上但無監督憑證 ⇒ 冷叫醒閘 `""`、合成輸出為監督閘的「掛 watch」（兩閘互斥） |
| AT-CTL-12 | 07 | 128 態狀態乘積表驅動（DES §2.1）：任一態 `converge.stop_verdict` 輸出不同時含 TaskStop 指令與「掛 watch」指令；已交棒∧在飛代理 ⇒ 只 TaskStop |
| AT-CTL-13 | 03 | 已交棒（別 sid `.ack`／spawn 痕跡）＋在飛代理＋watch shell ⇒ 推 TaskStop 全部（真交棒行為不變）；原主人自續跑（`.resumed`）⇒ 不算交棒 |
| AT-CTL-14 | 04 | 封存閘：`ctx ≥ hard` 無在飛代理，封存後只有 `park`／`keepwarm` 呼叫 ⇒ 不推；封存後 `Edit` ⇒ 推（`why=封存後有工作`）；`unreadable` ⇒ 不推；**`none`（從未封存）⇒ 照推「未封存」**（見 AT-CTL-83） |
| AT-CTL-15 | 02 | `seal.wake_package(sid, env)`（無 `transcript`）：已交棒分支同舊；封存分支回 `None`。**既有斷言遷移**（`test_sessionctl_converge.py:486-491`、`test_sessionctl_seal.py:325／348／388` 等，W1 現查 `Grep "wake_package" tools/tests` 補全）：逐檔補傳逐字稿夾具，**不放寬斷言**、不把預設改回舊行為；遷移前後各案的斷言語意對照表入 W1 交卷；掃描鎖：遷移後無案例以「省略 transcript」取得 `effective` 結果 |
| AT-CTL-16 | 03 | 封存有效、只剩 keepwarm shell；只剩 watch shell；兩者皆 ⇒ 皆豁免不推 |
| AT-CTL-17 | 06 | `control.classify(facts)` 純函式表驅動：事實組合 → `ControlState` 各欄（含 `supervision` 的 `source`、`sealed` 四值〔顯示名 `none｜unknown｜effective｜ineffective`，與 `sealed_effective` 四值一一對應〕、`pending_switch`） |
| AT-CTL-18 | 06 | `controlfacts.control_state`：注入假行程表／心跳／標記——`supervision.source`、`next_wake` 取自心跳／holder，標記文字被改寫為「已掛 watch」時狀態不變（憑證不取自述） |
| AT-CTL-19 | 15 | `control.status_line` 輸出逐字比對範例行；量不到欄位印 `?` |

### 3.2 監督單例（W2）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-20 | 08 | `watchlock.acquire`：先到者贏；持有者 pid 存在但建立時間不同（pid 重用）⇒ 後到者接手；持有者已死 ⇒ 接手；鎖檔目錄不可寫 ⇒ 回 `True` |
| AT-CTL-21 | 08 | `watch.run` 對已被持有的 sid：末行 `WATCH_VERDICT=duplicate`、rc 0、無心跳寫入、處置表有 `duplicate` 列 |
| AT-CTL-22 | 09、10 | 兩支 watch 各寫自己的心跳；先結束者刪自己的檔後 `supervise.read_heartbeat` 仍回後者；舊 `<sid>.json` 讀得到；新寫入只有新格式 |

### 3.3 可見（W3）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-23 | 11 | `rosterscope.scope_dirs`：projects 目錄含本 repo slug、沙盒 slug、他專案 slug；無 sid 預設只回本 repo；有 sid 行為不變（既有 `test_sessionctl_roster.py` 全綠） |
| AT-CTL-24 | 12 | `all_projects=True` 回全部且沙盒項標 `sandbox=true`；預設輸出末尾「另有 N 支…」行數與 `all_projects` 的差集一致 |
| AT-CTL-25 | 13 | 原始碼掃描：`rosterscope.py`、`controlfacts.py` 無字面 `AutoSDD-RV-sbx-`（只 import `sandbox_scope.SLUG_FRAGMENT`）；負控：本 repo 真專案殘局仍列 |
| AT-CTL-26 | 12 | `status` 預設與 `--all-projects` 的輸出對照（含 `a28de7322775c13d3` 形狀的沙盒殘局夾具：預設不列、`--all-projects` 列且標 `[沙盒]`） |
| AT-CTL-27 | 14 | SessionStart 簡報：本 repo 範圍有殘局／被切 ⇒ 一行；僅沙盒殘局 ⇒ 無；無 ⇒ 簡報逐字不變（既有 `session_brief` 測試全綠） |
| AT-CTL-28 | 16 | `segment` 表驅動：無代理無封存 ⇒ `""`、`ui_line` 輸出與既有逐字相同；2 代理＋watch ⇒ `ctl: 2 agents watch ok`；無 watch ⇒ `NO WATCH`；被切 ⇒ `CUT`；封存 ⇒ `sealed`；已交棒 ⇒ `HANDED-OVER`；待換 ⇒ `switch pending`；全 ASCII；注入例外／超時（>150 ms）⇒ `""`；10 秒內二次呼叫讀快取 |
| AT-CTL-29 | 16 | payload 缺 `transcript_path` ⇒ 退化只用 sid 路徑的檔、不報錯；`session_id` 缺 ⇒ `""` |

### 3.4 交接包與接續（W4）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-30 | 17、18 | `MECH_HEADINGS` 長度 13、前 11 項與舊版逐項相等（順序不變）、第 12／13 項為新標題；`build_mechanical` 輸出 13 個編號節；欄 1 含「主控模型」、欄 3 含 worktree 行 |
| AT-CTL-31 | 17 | 第 12 欄：running／quiet／residue／cut／stopped 各一代理夾具 ⇒ 各列欄位齊全；任務書指標＝首筆 user 記錄前 600 字；輸出落點去重至多 8；最後 3 則 assistant；建議處置字面分「排空後換」與「重派」兩類 |
| AT-CTL-32 | 19 | `rosterscope.cut_kind`：`apiError=usage_limit_reached` ⇒ `usage_limit`；末筆 `<synthetic>` 含 `hit your` ⇒ `usage_limit`；主逐字稿 `<status>killed</status>` ⇒ `stopped`；擁有者已交棒 quiet ⇒ `residue`；以 SA 列的 8 支被切代理形狀各一 |
| AT-CTL-33 | 17 | 代理逐字稿讀不到／空 ⇒ 該列「量不到：原因」，其餘列不受影響，`build` 不拋 |
| AT-CTL-34 | 18 | 第 13 欄：三棒鏈夾具（`.ack` 記接手 sid）⇒ 列出三棒；深度上限 5；環（A ack B、B ack A）不無窮；每棒 prompts 路徑存在／缺失（寫「缺」）；真人提示摘錄 ≤`PROMPT_EXCERPT_CHARS`、至多 `LAST_PROMPTS` 則；scratchpad ★檔至多 12／棒；**同一 sid 多包夾具（4a45bc75 形狀：兩包，其中一包被下一棒 ack）⇒ 取「`.ack` 內 `sid=` 為當前 sid 者中最早」的包，多指向註記「另有 N 個包同接手者」，找不到即止（「鏈止於 <sid>」）** |
| AT-CTL-35 | 18 | 無前鏈 ⇒ 「（無前鏈）」；本 sid 非任何包的接手者 ⇒ 同 |
| AT-CTL-36 | 18 | 欄 12 後附未結 OI id 一行（重用 `session_brief_oi` 摘要函式）；量不到（帳本缺）⇒ 「量不到：原因」；**不得**以主控自述取值 |
| AT-CTL-37 | 17、18 | 舊包（只有 11 欄）：`finalize`／`ack`／`announce`／`list_handoffs` 不受影響，讀取端容忍缺欄 |
| AT-CTL-38 | 21 | `finalize` 仍驗前四節非空、無 `TODO:`；「已驗證：（無）」「待掌舵者決定：（無）」通過；程式碼掃描無「rc／Ran N」類內容檢查 |
| AT-CTL-39 | 20 | `roster.stop_message`：有被切代理且該 sid 尚未提示 ⇒ 末加清單；已提示過 ⇒ 不重複；無被切 ⇒ 既有輸出逐字不變 |
| AT-CTL-40 | 20 | `watch` 判決處置字尾含被切清單（有被切時）；三處出聲文字由同一函式 `agentbrief.render_cut` 產生（原始碼掃描：三個呼叫點同一函式） |

### 3.5 換手演算法（W5）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-41 | 22 | `decide` 表驅動：DES §7.2 每列（G0、G1、W、D、H、F、F′、K、Z）≥1 個輸入向量 ⇒ 預期 `action／reason／flags／carrier`；`ctx=None` 時 H、F 不成立 |
| AT-CTL-42 | 22 | 次序：同時滿足 G1 與 H ⇒ G1；W 與 D 同時 ⇒ W；D 與 H 同時 ⇒ D；W 與 H 同時 ⇒ W |
| AT-CTL-43 | 22、23 | H：`agents=0` ⇒ SWITCH_NOW；`agents>0` ⇒ SWITCH_AFTER_DRAIN 並經 `ensure_pending` 建立 pending（`reason=hard`）；pending `since` 距今 29 分 ⇒ 仍 AFTER_DRAIN；31 分且 `ctx ≥ hard` ⇒ `SWITCH_NOW(drain_overdue, taskstop_first)`（僅文字提示，無新推回、無新 `WATCH_VERDICT`）；**不存在 R2 pending**（`compactions ≥ r2` 且 `ctx < hard` ⇒ 不寫檔、`decide`＝STAY＋`prefer_fresh`） |
| AT-CTL-44 | 22、28 | R2：`compactions ≥ r2` 只設 `prefer_fresh`；`decide` 動作不變；`park.fire_route`、`switch.fresh_reasons` 見 `prefer_fresh` ⇒ FRESH |
| AT-CTL-45 | 26 | 防抖：`since_takeover_min` 29 ⇒ STAY(`debounce`)；31 ⇒ H 正常；W 不受限；非接手者（None）不受限 |
| AT-CTL-46 | 27 | `account_changed=True` 只使 `cache` 輸入為 `cold`；同輸入向量的 `decide` 動作與 `account_changed=False` 相比，差異僅限於 F／F′ 兩列；任一側 `account_key` 為 `None`（快取缺、標記缺 `parked_account`）⇒ `account_changed=False` |
| AT-CTL-47 | 22、28 | 一致性（DES §7.5）：≥500 個合成輸入向量（ctx×agents×cache×sealed×quota stage×K×mode×unattended×handed_over）逐一比對 `decide` 與現行三閘＋F4 轉送的合成（`seal.stop_verdict`、`park.stop_verdict`、`keepwarm.stop_verdict`、`forward` 條件 10）：現行會推處 ⇒ `decide` 給對應動作；`decide` 的差異僅限四處（AFTER_DRAIN／pending、防抖、帳號變更⇒cold、PARK_POLL 提前恢復） |
| AT-CTL-48 | 28 | 原始碼掃描 `switchplan.py`：無數值化 `ctx` 門檻字面；只呼叫 `switch.threshold`／`costmodel`；模組常數集合恰為 `{DEBOUNCE_MIN, DRAIN_MAX_MIN}`（加其他常數即紅，要求先改 DES） |
| AT-CTL-49 | 29 | `handoff.advise_once`：條件成立 ⇒ 落 `switch_advise`（經 `switchplan.on_advise`，`handoff.py` 只加 1 行）、機械層已產則不重產；同 (sid, 原因) 第二次呼叫不再出聲；不同原因各一次；`advise_once` **不寫 pending** |
| AT-CTL-50 | 23 | pending 作廢：`sealed_effective == "effective"`／`handed_over`／（`ctx` 量得到且 `ctx < hard`＝壓縮後）各自使 `read_pending` 回 `None` 並落 `pending_switch_cleared`；`invalidated`／`none`／`unreadable` **不作廢**；`ctx` 量不到不作廢；條件仍成立則有效；作廢後 `ctx` 回到 ≥ hard 且有在飛代理 ⇒ 建新標記（新 `since`） |
| AT-CTL-51 | 24 | `watch` 代理全數交卷：有效 pending ⇒ 末行 `WATCH_VERDICT=switch_due`、rc 0、處置字面含 finalize／spawn；無 pending ⇒ 既有 all-done 判決逐字不變 |
| AT-CTL-52 | 25 | 封存閘觸發條件**不變**（負向）：有效 pending ∧ 無在飛代理 ∧ `ctx < hard` ⇒ **不推**（pending 不是推回條件）；在飛代理 ⇒ 不推；`ctx ≥ hard` ∧ 無在飛 ∧ `none`／`invalidated` ⇒ 推（同現行）；`unreadable`／`effective` ⇒ 不推；R2 命中（K ≥ r2）而 `ctx < hard` 的 session ⇒ 全程零推回（重放 8 個 R2 session 固定夾具）；`stop_hook_active` ⇒ 放行 |
| AT-CTL-53 | 30 | `sessionctl switch-plan`：rc 0；輸出含 Inputs／Decision／reason／carrier／credential；`--json` 可解析；量不到的輸入標「量不到」 |
| AT-CTL-54 | 28 | 原始碼掃描：`.claude/hooks/*.py`、`switchplan.py`、`controlfacts.py`、`control.py` 無 `handoff.spawn`／`--spawn` 呼叫（只允許出現在說明文字字串） |
| AT-CTL-55 | 28 | `agentbrief.render_cut` 輸出只含文字與指標，不含可執行呼叫；原始碼掃描：`agentbrief.py` 無 `subprocess`／`claude` 啟動 |

### 3.6 park 提前恢復（W6）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-56 | 32、37 | `park.recovered` 表驅動，向量＝(parked_pct, cur, prepare)：(100, 0, 85) 真；(100, 96, 85) 假（降 4pp 且仍 ≥ 門檻）；(90, 86, 85) 假（降 4pp 且仍 ≥ 門檻）；(90, 84, 85) 真（降 6pp ≥ 5 且 < 門檻）；(80, 79, 85) 假（降 1pp）；(80, 80, 85) 假（`park --why` 於未達門檻登記，絕對值低不觸發）；`parked_pct` 缺 ⇒ 假 |
| AT-CTL-57 | 32 | 舊標記無 `parked_pct` ⇒ 不判；`park --status` 印 `early_probe: absent(no_baseline)`；探針痕跡 `reason=no_baseline` |
| AT-CTL-58 | 32 | `_cmd_park` 登記時寫 `parked_pct＝max(axes.pct)`（短窗∪週軸、排除 FALLBACK／MODEL_SCOPED）與 `parked_account＝account_key`（量不到寫 `null`）；欄名常數取 `parkprobe.MK_PARKED_PCT`／`MK_PARKED_ACCOUNT`（**不在 `qw_schema`**；原始碼掃描：`qw_schema.py` 不含這兩個字面）；import 方向單向無環（原始碼掃描＋匯入圖檢查，r3）：`parkprobe.py` **不** import `park_cli`／`parkearly`；`parkearly.py` import `parkprobe` 與 `park_cli`；`park_cli.py` 只 import `parkprobe`（取常數、`baseline`、`status_row`），不 import `parkearly`；`park_cli` 內無 `fire_early` 字面；`_cmd_park` 以 `parkprobe.baseline(…)` 一行寫兩欄；量不到 ⇒ 不寫、登記照常；`park.write_marker`／`read_marker`／`_settle` 對含這兩欄的標記往返保留（含 `cancelled`／`fired` 後仍在） |
| AT-CTL-59 | 31 | 哨兵分支次序（以假縫呼叫 `_sentinel_tick`）：`sched_isolation.tick_gate` `refused` ⇒ 早已返回、探針不被呼叫；放行 ⇒ 探針（`parkearly.tick`，planner 內一行；內部先呼叫 `parkprobe.evaluate`，判決成立才 `parkearly.fire_early`，r3）先於 `sentinel_decide`（內含 `park.yields`）；`unmeasured` ⇒ 回 `None`、續走 `sentinel_decide`（讓路 `patrol`）；QW §7.6 `failed` 接手分支位置不變；原始碼掃描：`park.yields` 仍只出現在 `sentinel_decide`、planner 對 `parkearly` 的新增行數 ≤2 |
| AT-CTL-60 | 31、37 | 前置不成立各一例：剩餘等待 59 分 ⇒ 不探；包已 `.ack`；`handed_over`；`spawning` 意圖有效；`live_driver`；`AUTOSDD_UNATTENDED`；模式非 auto ⇒ 皆不觸發、不落 `park_early_recovered` |
| AT-CTL-61 | 33 | `_cmd_fire(early=True)`：§7.3 分支 A（主載具活著且未到）不重排而繼續；B／C／D 照舊；`early=False` 的黃金序列（SE AT-SE-31／E2E-SE-09）逐字不變，另增 `early` 版本序列 |
| AT-CTL-62 | 34 | `account_changed`（標記 `parked_account` ≠ 當下 `account_key`，兩側皆非 `None`）⇒ `fire_route(held, cold=True)`：`held` 大於 F4 門檻 ⇒ FRESH、小於 ⇒ RESUME（同 sid 有活窗 ⇒ fork，不關窗）；`prefer_fresh` ⇒ FRESH；痕跡 `park_route` 的 why 含 `account_changed` |
| AT-CTL-63 | 37 | 至多一次：觸發後標記非 `armed`，下一次巡邏 skip；`park_early_recovered` 恰 1 筆，欄含 `saved_min`、`account_changed` |
| AT-CTL-64 | 33 | `quotawall.early_reset` 適用且主載具已醒（`live_driver`／holder 判決）⇒ 本分支不重判（不對同事件各答一次）；`early_reset` 不適用（`primary_source=at`）⇒ 本分支判 |
| AT-CTL-65 | 31 | 探針節流：巡邏間隔 900 秒、`park._pace_state` 的 TTL 內第二次呼叫讀快取（不重量）；不新增第二個額度讀取點（原始碼掃描：`parkprobe.py` 只經 `park._pace_state`／`quota_meter`） |
| AT-CTL-66 | 35 | 讀不到（端點 500／憑證缺）／陳舊且補量失敗 ⇒ 痕跡 `park_early_probe reason=unmeasured`、不觸發、不拋；連續 3 次 unmeasured ⇒ SessionStart 簡報加一行 |
| AT-CTL-67 | 36 | `park --status` 的 `early_probe:` 列欄位齊全；`next_probe` 取排程器自報（`--verify`）或標 `?`；`refused` 標記下三列照印（SE X-22） |
| AT-CTL-68 | 36、38 | `park` 登記末行 `early_probe=armed`（哨兵武裝成功）／`absent(sentinel_off)`／`absent(arm_refused)`；與 QW §7.1 末行字面相容（本稿只追加一個 token，不改既有 token） |
| AT-CTL-69 | 38 | 原始碼掃描：提前恢復路徑只經 `quota_meter` 的唯讀 GET；無第二個端點知識；巡邏相隔 ≥ TTL（PRD §15.5 紅線 1 豁免四條件逐條有斷言） |

### 3.7 量測與痕跡（W5）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-70 | 39 | M-W1：夾具中某區間有有效 watch 心跳 ⇒ 不計；無任何憑證 ⇒ 計；舊口徑並行輸出且標「上界」；兩口徑數字不相減 |
| AT-CTL-71 | 40 | M-C1：舊實作痕跡夾具（封存後派工＋`finalized_wake_block`）⇒ 計 N；W1 後同夾具重放 ⇒ 0；`control_cold_wake_exempt` 為分母 |
| AT-CTL-72 | 41、42 | `--replay-plan --population <快照>`：輸出 H／R2／冷回／F4／防抖／park 提前各列，數字對固定快照確定；判準函式為 `decide`／`park.recovered` 本體（原始碼掃描：`sections_ctl.py` 不複製判準） |
| AT-CTL-73 | 43 | 新痕跡事件名集合與 QW §13 事件名集合不相交；事件名常數集中一處 |
| AT-CTL-74 | 41 | M-C2／M-C3／M-C4／M-C5 各以夾具確定計算（含 M-C5 的「冷回且 F4 換新且無封存包」） |

### 3.8 規格與收尾（W0／W8）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-75 | 44 | **釘修憲前 blob**（不用 `git diff`，提交後仍有效）：常數 `PRD_PRE_AMENDMENT_BLOB＝5af6ce952d701284642f199d19dd3daea58beca7`；`git cat-file -p` 取舊檔，每一行（`\n` 切、UTF-8、逐字相等、不 strip）依序為工作樹 PRD 行序列的行級子序列（雙指標）；新檔含 v2.1.26 修訂表列與 §16.6 兩列；兩題原文逐字出現。自證見 AT-CTL-89 |
| AT-CTL-76 | 44、46 | 自檢：本檔表頭 REQ／AT／E2E／MU 計數（48／92／24／49）與實際列數相等 |
| AT-CTL-77 | 45 | TCS-SessionCtl AT-SC-34 為 13 欄；`MECH_HEADINGS` 長度 13 |
| AT-CTL-78 | 45、46 | `Root_Layout` §3 sessionctl 列含 10 個新模組與 6 個新測試檔；列內反引號路徑皆存在於磁碟（`test_root_module_layout.py`） |
| AT-CTL-79 | 46 | W1～W7 的 `git diff --name-only` 不含 `.claude/**`；守衛面清單成員數不變 |
| AT-CTL-80 | 46 | QW AT-QW-61 的十一欄字面掃描在 W1～W6 後仍綠；W6 新增 `parked_pct`／`parked_account` 住 `parkprobe.py`、不在該清單、不進 `qw_schema` |
| AT-CTL-81 | 46 | `python AutoClaude/tools/check_loc_budget.py --json` 對新檔與被動到的既有檔無分級違規（`tier_violations`／`special_violations`／`root_tools_violations` 皆空）；`session_brief.py`、`session_resume_planner.py`、`handoff.py` 自各包動工前基線的淨增 ≤2 行（對 W 動工前 HEAD 的 `git diff --numstat` 比對，由 W 包交卷附輸出） |
| AT-CTL-82 | 46 | `cases.json` 含 `RV-CTL01`～`RV-CTL24` 且 family＝`control`；`realverify list` 對已實作者不顯示 planned |

### 3.9 r2 新增（QA 規格審查處置）
| AT | REQ | 內容 |
|---|---|---|
| AT-CTL-83 | 01、04 | **從未封存**（戳檔不存在）：`sealed_effective == "none"`；封存閘對「`none` ∧ `ctx ≥ hard` ∧ 未交棒 ∧ 無在飛代理」**照推「未封存」**（與現行 `seal.stop_verdict` 逐輸入同判）；`none` 且逐字稿不存在仍是 `none`（不是 `unreadable`）；冷叫醒閘對 `none` 不推 |
| AT-CTL-84 | 01、02、06 | 四值×消費端表驅動（DES §3.2 表逐格 5 消費端 × 4 值＝20 格）：封存閘、冷叫醒閘、pending 作廢、決策表 F／F′、`ControlState.sealed` 顯示名；任一格與表不符即紅 |
| AT-CTL-85 | 47 | `ackhook.on_ack`：擁有者≠acker 且標記 `armed` ⇒ 呼叫 `park_cli.cancel_marker`（標記 `cancelled`、事件 `acked`、備援排程經假排程後端被拆）；擁有者＝acker（自續跑）⇒ 不撤；無標記／已 `cancelled`／`fired` ⇒ 無動作 rc 0（冪等）；對同一包二次 ack ⇒ 拒絕不重撤；`_cmd_fire` 對已 `.ack` 包仍 `skip("acked")`（防線不變）；`_cmd_cancel` 既有 AT 逐字不變；原始碼掃描：`ackhook.py` 無 `schtasks`／`launchctl`／subprocess（排程拆除只經 `park_cli`） |
| AT-CTL-86 | 23、25 | **閂鎖解耦**：先讓 R2 命中而 `advise_once` 出聲（`.advised` 已寫）、之後 ctx 越過硬線 ∧ 有在飛代理 ⇒ `ensure_pending` 仍建立 pending（`reason=hard`）；R2 命中而 `ctx < hard` ⇒ 不寫 pending、封存閘零推回；`ensure_pending` 對已有檔不覆寫 `since`；兩個呼叫點（watch 輪詢、`switch-plan`／`control_state`）任一先到皆建立同一標記；原始碼掃描：`seal.py` 不 import `switchplan`、封存閘 Stop 路徑不呼叫 `ensure_pending`（r3：該閘只在無在飛代理時觸發，建立條件恆不成立） |
| AT-CTL-87 | 27、32、34 | `account_changed` 基準：`parked_account` 與當下 `account_key` 皆非 `None` 且不同 ⇒ 真；相同 ⇒ 假；任一側 `None`（含舊標記無此欄）⇒ 假；`now_key` 取自 `_pace_state` 同一次讀數（不另打端點，原始碼掃描）；標記往返保留（AT-CTL-58） |
| AT-CTL-88 | 48 | M-C6：夾具＝無人窗口逐字稿含 `<status>killed</status>`／print 模式上限終止 ⇒ 計 N；無則 0；互動 session 不計；僅讀既有逐字稿、不接閘門 |
| AT-CTL-89 | 44 | PRD 鎖自證（`test_sessionctl_control.py`）：①舊 blob 的每一行依序在新檔 ⇒ 綠；②新檔多出整行（尾端、表格中間）⇒ 綠；③改既有任一行一字／刪一行／交換兩行順序 ⇒ 紅；④blob 取不到（以假 `git` 縫）⇒ **FAIL（不 skip）** 並印「請 `git fetch --unshallow`」；⑤提交後情境（`HEAD:PRD` 已含 v2.1.26）仍綠（blob 為常數，不隨 HEAD 變） |
| AT-CTL-90 | 46 | 行數牆（DES §21）：`briefline.py`／`parkprobe.py`／`parkearly.py`／`switchplan.py`／`ackhook.py` 為新檔（r3 加 `parkearly`）；`park_cli.py` 不含 `def fire_early`／early 觸發本體，且 W6 對它的增量 ≤4 行、W4b 淨 0（對動工前基線，該檔 assertion 數 ≤400）；且判準不在 `session_brief.py`／`session_resume_planner.py`／`handoff.py`（原始碼掃描：這三檔不含 `orphan_line`／`recovered`／`ensure_pending`／`on_ack` 的 `def`）；三檔各包增量 ≤2 行（對動工前基線）；`SPECIAL_FILES` 天花板值未上調（對 `check_loc_budget` 輸出比對） |
| AT-CTL-91 | 18 | 鏈走法（P3-5）：同 sid 多包夾具，取最早 `.ack` 之包；多指向註記；無接手記錄 ⇒ 「鏈止於」；環不無窮 |
| AT-CTL-92 | 17、18 | 大小上限：超長 assistant 文字／超多列夾具 ⇒ 每則截斷於 `BRIEF_CHARS`／`PROMPT_EXCERPT_CHARS`、全欄不超 `COL12_MAX_CHARS`／`COL13_MAX_CHARS`、欄末「已截斷 N 列」；含 `tool_result` 的逐字稿夾具 ⇒ 輸出不含其內容（以唯一標記字串斷言） |

## 4. 真機 E2E（每個 REQ 至少一個；RealVerify 家族 `control`，id `RV-CTL01`～`RV-CTL24` 對應 `E2E-CTL-01`～`24`；案例程式 `tools/lib/realverify/cases/control.py`）

**共通**：
- 沙盒＝R218-B（SE）`Sandbox`；副作用一律先登記 L2 帳、每案前後快照差異為空（SE R-VER-5）；排程一律 SE 沙盒前綴＋OS 自毀時限；結束斷言前綴 0 殘留。**任何案例不真開窗**（唯一例外 `E2E-CTL-23` 走已一次信任的 `C:/Users/wuwei/.autosdd/rv_host` 真互動窗、需人目視，列〔OI〕）。
- 需要 spawn 的案例一律 `--claude <SE GUI 子系統替身 claude>`，行為由 `<家>/fakeclaude.mode` 指定（`resume_ok`／`fresh_ok`／`fail`；SE §10.2.1 X-1～X-6）；正控不以 rc 0 判，案例讓 F4 選路可預期並斷言 `park_route` 的 route 與模式一致。
- 額度＝T5 端點替身（`tools/lib/realverify/cases/prd_px_lib.py`；含 `account_key` 標頭切換）；hook 行程讀到非替身讀數或 `stale-cache` ⇒ 案例 fail「載具漏接」。不燒真額度。
- 真逐字稿重放＝複製真實行段到沙盒 projects 目錄（只複製、不改內容；時間戳整體等距平移時**保持相對順序**）；凡「修前紅」案例，案例內自帶舊實作 oracle 複本，先證夾具確實觸發舊行為，再證新行為不觸發。
- 使用真 `claude -p --model haiku` 的案例：先斷言逐字稿確有預期 `tool_use`，沒有判 ENV 重跑，不得判 PASS；`AUTOSDD_UNATTENDED` 不得設（Stop 守衛在無人窗口是 no-op）；載具沿 `sessionctl_converge.py`／`sessionctl_watch.py` 既有安裝方式（沙盒內掛真 `sessionctl_guard.py`，`_hook_launcher` 載具）。
- 縮時只用既有產品旗標（watch `--poll-sec`、keepwarm `--min`）與替身讀數；`DRAIN_MAX_MIN`、`EARLY_*` 是程式常數，案例以注入 `now` 的子行程參數或標記時間戳（`since`）製造，不改常數。

| E2E | REQ | 載具 | 斷言 |
|---|---|---|---|
| E2E-CTL-01 | 01、02、03、04 | **65389f03 真逐字稿重放**：複製 `65389f03-4a29-43f2-8228-61cb3c884a4e.jsonl` 第 2221～2335 行與第 2468～2519 行的相對順序（含 finalize、Agent 派工、Stop hook feedback 記錄）到沙盒；沙盒包目錄放兩份 `.sealed`（**戳時刻來源（r2，P3-2）**：第 2235、2492 行是 `api-request-blob`、無 `timestamp`，原 `.sealed` 也已被後續 finalize 覆寫〔現值 2026-11-21T19:43:01+08:00〕，故不取這兩行；改取第 2221 行〔2026-11-21T09:52:54Z〕與第 2468 行〔2026-11-21T11:19:31Z〕所在 finalize 記錄的時戳，各 +1 秒；整體等距平移時保持相對順序）；餵**真** `python .claude/hooks/sessionctl_guard.py`（Stop）以逐字稿重建的 payload（`background_tasks`＝2 代理＋1 watch shell）；對照組＝舊實作 oracle＋`.ack` 由別 sid 寫入 | 舊 oracle 在夾具回推回（夾具有效）；新 hook stdout 不含「冷叫醒閘」、rc 0；痕跡無新 `finalized_wake_block`、有 `control_cold_wake_exempt`；對照組（別 sid ack）⇒ 推回含 TaskStop；MU-CTL-01 轉紅 |
| E2E-CTL-02 | 02、03、07 | 真 `claude -p --model haiku` 腳本化三步：①真跑 `handoff --finalize`（沙盒包）→ ②用 Agent 工具派一個睡 20 秒的子代理 → ③結束回合；沙盒掛真 `sessionctl_guard.py`；對照組＝同流程但先 `.ack`（別 sid） | 逐字稿確有 Agent tool_use；封存後該回合 Stop 無「冷叫醒閘」；對照組有；同一輸出不同時含 TaskStop 與「掛 watch」；ENV 分支＝模型未派 Agent |
| E2E-CTL-03 | 05、06 | 三份真逐字稿複本（4a45bc75、65389f03、31ea79d4）＋沙盒包與心跳夾具，真跑 `python tools/sessionctl.py status --json`／`switch-plan --json`；PowerShell 注入「封存後 park／keepwarm／status 呼叫」的合成尾段 | `control` 物件各欄與逐字稿事實一致（代理數、封存四值、已交棒）；注入監督呼叫後 `sealed` 仍 `effective`、注入 Agent 後 `ineffective`；憑證欄取自心跳檔（改寫標記文字不影響） |
| E2E-CTL-04 | 07 | 128 態中取代表性 ≥24 態（含全部 handed_over×agents 組合、四種封存值×三種 shell），每態真起 `sessionctl_guard.py` Stop 行程餵 payload | 每態 stdout 的推回指令集合符合 DES §4.2 表；任一態同時含 TaskStop 與「掛 watch」＝FAIL；已交棒∧在飛代理 ⇒ 僅 TaskStop |
| E2E-CTL-05 | 08、09、10 | 真起兩支 `python tools/sessionctl.py watch --sid X --poll-sec 1`（`run_in_background`）；之後讓先到者結束、後到者（若先啟動則反之）觀察 | 後到者末行 `WATCH_VERDICT=duplicate`、rc 0、不留心跳；先到者結束後 `supervise.read_heartbeat` 不被刪；舊格式心跳夾具仍被讀；pid 重用夾具（殺先到者再啟後到者）⇒ 接手成功 |
| E2E-CTL-06 | 11、12、13 | 沙盒內真 `claude -p --model haiku` 派一支背景子代理（睡 20 秒）；其後真跑 `status`（預設）與 `status --all-projects`；同時複製本 repo 專案的一個真殘局代理檔作負控 | 預設不列沙盒子代理、列本 repo 殘局；`--all-projects` 列且標 `[沙盒]`；預設輸出末行「另有 N 支…」；ENV 分支＝模型未派代理 |
| E2E-CTL-07 | 14、20 | 真 `python .claude/hooks/sdd_hook_router.py`／`session_brief` 的 SessionStart 路徑（沙盒家目錄，不碰真 `~/.autosdd`），夾具＝本 repo slug 下 2 支殘局＋1 支 `usage_limit` 被切（真 SA 列的代理檔形狀）＋沙盒 slug 殘局 | 簡報含「上一個 session 有 2 支代理未收尾／1 支被額度切斷」一行與 `status` 指路；不含沙盒項；無殘局時簡報逐字不變 |
| E2E-CTL-08 | 06、15 | 真 `sessionctl status` 對沙盒 sid：真掛一個 `AutoSDD_RVsbx_` 前綴排程（SE 租約）與真 watch 心跳；`park --status --verify` | `control:` 行的 `next_run` 與 `Get-ScheduledTask … NextRunTime` 逐字相等；心跳年齡與檔案 mtime 一致；改寫 park 標記的 `credential` 文字不影響 `control:` 的 `next_run`（取自排程器） |
| E2E-CTL-09 | 16 | ①真 payload 重放：取 `~/.autosdd/context_feed/<某 sid>.json`（harness 真實 statusLine 輸入，唯讀複製）餵 `python tools/statusline_context_feed.py`，沙盒心跳／代理夾具使區段非空；②`claude -p --settings` 掛 statusLine 驗 `-p` 是否執行（官方：statusLine 屬互動 UI；不執行判 ENV，改以①為準並登〔OI〕V-CTL1）；③真 payload 是否帶 `transcript_path` 現查寫入證據 | ①輸出行＝既有行＋「空白 \| 空白」＋`ctl: …`，純 ASCII、rc 0、耗時 <150 ms（量測）；無內容時輸出與既有逐字相同；`transcript_path` 缺席時退化不報錯；statusLine 互動畫面顯示不在本案宣稱 |
| E2E-CTL-10 | 17、19 | 真 `claude -p --model haiku` 派一支睡 60 秒的真子代理（主控另派一支後 TaskStop 作 `stopped` 樣本）；其間真跑 `python tools/sessionctl.py handoff --build --sid <沙盒 sid>` | 第 12 欄含 running 代理 id、任務書前 600 字、代理逐字稿路徑、輸出落點、最後 3 則 assistant、建議處置＝「排空後換」；stopped 代理列為「重派」；`MECH_HEADINGS` 13 欄、欄 1～11 順序不變 |
| E2E-CTL-11 | 18 | 把 `~/.autosdd/handoff` 中真實的 4a45bc75→65389f03 兩個包（`.md`／`.ack`／`.prompts.md`）與兩份逐字稿複製到沙盒，對沙盒中的「第三棒 sid」真跑 `handoff --build` | 第 13 欄列出 65389f03、4a45bc75 兩棒各自的 prompts 路徑、最近真人提示摘錄、scratchpad ★檔（含 `RESTART_POINT`）；深度與環防護不拋；無前鏈者「（無前鏈）」 |
| E2E-CTL-12 | 19、20 | 8 支被額度切斷代理的真實檔形狀（SA 列：4a45bc75 的 a612f2af／aef5829a／aff9c301、65389f03 的 a018beed／ab867bb2、680d8411 的 a5218308／a93a1add、d4ed2654 的 abe51342；唯讀複製其逐字稿與 meta 到沙盒）＋對應主逐字稿；真跑 `handoff --build`、`status`、真 Stop hook、真 `watch` 判決 | 8 支全數判 `usage_limit`、漏列 0；第 12 欄、Stop `systemMessage`、watch 處置字尾、SessionStart 簡報四處清單同文；每支有輸出落點與重派指標；無任何自動重派動作（無新代理逐字稿出現） |
| E2E-CTL-13 | 22、26、27、28、30 | 真跑 `python tools/sessionctl.py switch-plan --json` 對真逐字稿複本（硬線 4 個 session 3d200496／58ce5ccd／76d1471c／f1522ddb 的觸發當刻截斷版；R2 命中 d4ed2654；65389f03 封存後；防抖夾具＝剛 ack 的接手者）＋沙盒 park 標記（含 `parked_account`）與 T5 替身切換 `account_key` | 76d1471c／f1522ddb／3d200496 ⇒ `SWITCH_AFTER_DRAIN`、58ce5ccd ⇒ `SWITCH_NOW`；d4ed2654 ⇒ `STAY`＋`prefer_fresh`；剛接手 ⇒ `debounce`；`account_changed` 只改 `cache`；任一輸出無新增 ctx 門檻；與 `waste_census --replay-switch` 同母體的 H／R2 計數一致 |
| E2E-CTL-14 | 23、24、25 | 真 `claude -p --model haiku` 派一支睡 30 秒的真代理；先用 `advise_once` 路（以沙盒 `AUTOSDD_SWITCH_HARD_CTX_TOKENS` 的**下修值**使硬線成立，ENV_SPEC 已登記只准下修）寫 pending；真 `watch --poll-sec 1`；代理交卷；之後 Stop | pending 檔鍵集合恰 `reason／since／ctx`；代理交卷時 watch 末行 `WATCH_VERDICT=switch_due`、rc 0；Stop 封存閘推「finalize→spawn」；`.sealed`／finalize 後 pending 作廢（痕跡 `pending_switch_cleared`）；無 pending 對照組 ⇒ 既有 all-done 判決 |
| E2E-CTL-15 | 29、39、40、43 | 真 `python tools/probe/waste_census.py --supervision-metrics`（沙盒痕跡目錄＋真逐字稿複本）；`advise_once` 真觸發一次 | `switch_advise` 痕跡落檔；M-W1 修正版對有心跳區間不計、舊口徑標「上界」；M-C1 對修前痕跡夾具＝N、對 W1 後重放＝0；事件名集合與 QW 不相交 |
| E2E-CTL-16 | 31、32、33、34、36 | **提前恢復正控全流程**：沙盒 `park --at <+2h> --why …`（登記時 T5 替身讀數 weekly 100%、`account_key=A`，標記寫入 `parked_pct=100`、`parked_account=A`；哨兵 `ctl_env(arm_sentinel=True)` 武裝，X-21）；其後 T5 替身改讀數 weekly 3% 且 `account_key` 變更；真跑哨兵 tick（`python tools/session_resume_planner.py` 以排程器同 argv 起的真行程；替身 claude `fresh_ok`／`resume_ok` 兩輪） | 痕跡依序 `park_early_probe`（`recovered=true`）→ `park_route`（why 含 `account_changed`）→ 替身 argv 記錄 ＋ `park_early_recovered`（`saved_min`≈120−經過分鐘）；`fresh_ok` 輪逐字稿新建、`resume_ok` 輪追加；標記 `fired`；同一標記第二次 tick skip；`park --status` 的 `early_probe:` 列欄位齊全；`next_probe` 與 `Get-ScheduledTask` NextRunTime 一致；沙盒前綴排程 0 殘留 |
| E2E-CTL-17 | 37 | **負控 7 輪**（同 E2E-CTL-16 載具，各輪只改一個條件）：①`live_driver`（沙盒逐字稿近 1 分鐘有 assistant 記錄）②包已 `.ack`（別 sid）③`spawning` 意圖有效④剩餘等待 <60 分⑤讀數降 4pp⑥降了但仍 ≥ 準備門檻⑦`park --why` 於未達門檻登記（baseline 80、讀數 80）；外加舊標記無 `parked_pct` | 七輪＋舊標記皆無 `park_early_recovered`、替身 0 次呼叫；舊標記印 `absent(no_baseline)`；MU-CTL-30／34 轉紅 |
| E2E-CTL-18 | 35、38 | 同載具：T5 替身端點 500／憑證缺；另一輪登記時 `AUTOSDD_SENTINEL_OFF=1` | 端點壞：痕跡 `park_early_probe reason=unmeasured`、無觸發、tick rc 0；連 3 次後 SessionStart 簡報加一行；`SENTINEL_OFF`：`park` 末行 `early_probe=absent(sentinel_off)`、零次排程器呼叫（SE X-19 字面）、`--status` 同 |
| E2E-CTL-19 | 41、42 | 真跑 `waste_census.py --replay-plan --since-days 14`（真母體）與 `--population <快照>`（固定快照）；`--switch-metrics` 併出 M-C2～M-C5 | 快照輸出確定且含 H／R2／冷回／F4／防抖／park 提前各列；真母體輸出的 H 與 `--replay-switch` 同母體一致；`65389f03` 在 park 提前列命中、其餘 park 標記不命中（負控）；零 token（無任何 `claude` 啟動） |
| E2E-CTL-20 | 21、28 | 真 `handoff --finalize`：包主控層「已驗證：（無）」；真掃 `.claude/hooks/*`、`tools/lib/sessionctl/*` 對 `handoff.spawn`／`--spawn` 的呼叫；真跑一整輪 Stop／PostToolUse hook（沙盒）後檢查 spawn 痕跡 | finalize 通過（只驗結構）；程式面無 hook 呼叫 spawn；hook 行程跑完後痕跡無 `session_switch_spawned`／`spawning`、替身 0 次呼叫 |
| E2E-CTL-21 | 44、45、46 | 真跑 `git cat-file -p 5af6ce952d701284642f199d19dd3daea58beca7`（修憲前 blob，唯讀）對工作樹 PRD 做行級子序列比對（雙指標；提交前後皆可跑）、`python tools/check_*` 落點鎖（`test_root_module_layout.py`）、`check_loc_budget.py --json`、AT-QW-61 掃描、`cases.json` 解析 | 舊 blob 每行依序仍在新檔（缺任一行＝FAIL；blob 取不到＝FAIL 不 skip）；落點鎖與 LOC 綠；十一欄掃描綠；`realverify list` 含 `RV-CTL01`～`24` |
| E2E-CTL-22 | 12、13、14、17、18、31～34（整合） | **換帳號全鏈縮時重放**：沙盒 park（weekly 100%，`--at +3h`）→ 真 `claude -p`（haiku）派一支代理 → TaskStop → `handoff --build/--finalize`（第 12 欄含重派指標）→ T5 替身換帳號且 weekly 0% → 真哨兵 tick → 替身 claude 起新 session 讀包 → `handoff --ack`；以替身逐字稿斷言它讀到第 12／13 欄 | 新 session 起步提示含包路徑；包第 12 欄含被 TaskStop 代理的重派指標、第 13 欄含前棒 prompts 路徑；整個鏈上**無任何手貼**（M-S2 判準＝首則提示為機器產）；提前時間 < 輪詢間隔＋TTL；`.ack` 寫入、舊 sid 被判已交棒；M-C3 記一筆 |
| E2E-CTL-24 | 47 | **ack 後撤 park**：沙盒 `park --at <+3h> --why …` 登記（備援排程以 SE 租約前綴；T5 替身讀數）→ 以**別 sid** 真跑 `python tools/sessionctl.py handoff --ack <包>`（沙盒包目錄）；對照組二＝自續跑（擁有者 sid 自己 ack）；對照組三＝強制觸發到點 job 本體（`_cmd_fire`，以排程同 argv 起真行程） | 主組：標記 `cancelled`（`event=acked`）、`Get-ScheduledTask` 查無備援排程（0 殘留）、`park --status` 不再顯示 armed、到點 job 強制觸發 ⇒ `handoff_spawn_skipped reason=cancelled` 且替身 claude 0 次呼叫；對照組二：標記仍 `armed`；對照組三（不經 ack 撤、只 `.ack` 存在）⇒ `skip("acked")`（雙駕駛防線）；沙盒前綴排程結束 0 殘留；MU-CTL-44／49 轉紅 |
| E2E-CTL-23 | 14、16、20（互動半）＝V-CTL1 | **真互動窗（需人目視；`rv_host`）**：在 `C:/Users/wuwei/.autosdd/rv_host` 起真互動 `claude`，statusLine 指向 `tools/statusline_context_feed.py`；依 `RealVerify interactive` 載具讓沙盒夾具使 `ctl:` 區段非空、Stop 觸發被切清單 `systemMessage`、SessionStart 簡報出現殘局行 | 掌舵者目視回報：①statusLine 顯示 `ctl: …` ②Stop `systemMessage` 顯示被切清單 ③SessionStart 簡報顯示殘局行。**屬〔OI-20261120-010〕同款真機目視尾巴**：未目視前 REQ-CTL-14／16／20 的「畫面顯示」半不宣稱已驗，結案格寫〔OI〕 |

## 5. 突變（MU；每條必須讓指定測試轉紅）
| MU | 突變 | 必紅 |
|---|---|---|
| MU-CTL-01 | `_finalized_wake` 退回舊 `wake_package`（不看封存後工作） | AT-CTL-08、09、E2E-CTL-01 |
| MU-CTL-02 | 把 `Agent`／`Task` 加進監督集合（派工不算工作） | AT-CTL-02、08 |
| MU-CTL-03 | 把 `park`／`keepwarm` 動詞移出監督集合（算工作） | AT-CTL-03、14 |
| MU-CTL-04 | `sealed_effective` 對 `unreadable` 回 `effective` | AT-CTL-05、84 |
| MU-CTL-05 | `sealed_effective` 退成二態（`unreadable` 回 `invalidated`，使冷叫醒閘／封存閘對讀不到的逐字稿改變行為） | AT-CTL-05、14、84 |
| MU-CTL-06 | `converge.py` 直接呼叫 `worked_since(` | AT-CTL-04 |
| MU-CTL-07 | 封存有效時對在飛代理也推 TaskStop | AT-CTL-11、12、E2E-CTL-04 |
| MU-CTL-08 | 已交棒分支不再推 TaskStop | AT-CTL-13、E2E-CTL-04 |
| MU-CTL-09 | `is_supervision_call` 對解析不出視為監督 | AT-CTL-06 |
| MU-CTL-10 | 第二支 watch 不印 duplicate 而照跑 | AT-CTL-21、E2E-CTL-05 |
| MU-CTL-11 | 心跳檔鍵改回 sid | AT-CTL-22、E2E-CTL-05 |
| MU-CTL-12 | `rosterscope` 預設回全部 slug | AT-CTL-23、26、E2E-CTL-06 |
| MU-CTL-13 | `rosterscope` 寫死沙盒 pattern 字面 | AT-CTL-25 |
| MU-CTL-14 | `switchplan` 加數值化 ctx 門檻（例 300000） | AT-CTL-48、E2E-CTL-13 |
| MU-CTL-15 | 任一 hook／`decide` 路徑呼叫 `handoff.spawn` | AT-CTL-54、E2E-CTL-20 |
| MU-CTL-16 | H 列忽略在飛代理（恆 SWITCH_NOW） | AT-CTL-43、E2E-CTL-13 |
| MU-CTL-17 | 移除排空期限（硬線待換永不升級） | AT-CTL-43 |
| MU-CTL-18 | R2 產生 SWITCH_NOW 推回 | AT-CTL-44、47、E2E-CTL-13 |
| MU-CTL-19 | 移除防抖 | AT-CTL-45、E2E-CTL-13 |
| MU-CTL-20 | W 列移到 D 列之後 | AT-CTL-42 |
| MU-CTL-21 | `account_changed` 新增推回 | AT-CTL-46、47 |
| MU-CTL-22 | `MECH_HEADINGS` 於第 8 欄後插入新欄（欄號位移） | AT-CTL-30 |
| MU-CTL-23 | 第 12 欄略過 `cut` 代理 | AT-CTL-31、32、E2E-CTL-12 |
| MU-CTL-24 | 第 13 欄不設深度上限／不防環 | AT-CTL-34、E2E-CTL-11 |
| MU-CTL-25 | `finalize` 增內容檢查 | AT-CTL-38、E2E-CTL-20 |
| MU-CTL-26 | watch 永不發 `switch_due` | AT-CTL-51、E2E-CTL-14 |
| MU-CTL-27 | pending 永不作廢 | AT-CTL-50 |
| MU-CTL-28 | 封存閘新增「有效 pending 即推」的觸發條件（r2：封存閘觸發條件不得改；使 R2／pending-only session 新增推回） | AT-CTL-52、86、E2E-CTL-14 |
| MU-CTL-29 | `advise_once` 不落 `switch_advise` | AT-CTL-49、E2E-CTL-15 |
| MU-CTL-30 | `recovered` 改用絕對讀數（`cur<prepare` 且無 baseline） | AT-CTL-56、E2E-CTL-17 |
| MU-CTL-31 | `recovered` 不要求下降幅度 | AT-CTL-56 |
| MU-CTL-32 | 探針排在 SE L1 判準之前 | AT-CTL-59 |
| MU-CTL-33 | `early` 未停用分支 A（重排吞掉提前觸發） | AT-CTL-61、E2E-CTL-16 |
| MU-CTL-34 | 有 `live_driver` 仍提前觸發 | AT-CTL-60、E2E-CTL-17 |
| MU-CTL-35 | `account_changed` 不強制 `cold` | AT-CTL-62、E2E-CTL-16 |
| MU-CTL-36 | 同一標記可重複觸發 | AT-CTL-63、E2E-CTL-16 |
| MU-CTL-37 | `unmeasured` 當作 `recovered` | AT-CTL-66、E2E-CTL-18 |
| MU-CTL-38 | M-W1 忽略真憑證（退回舊口徑） | AT-CTL-70、E2E-CTL-15 |
| MU-CTL-39 | 改動 PRD 既有一行（例如 §16.6 既有列一字；以修憲前 blob 比對，提交前後皆須紅） | AT-CTL-75、89、E2E-CTL-21 |
| MU-CTL-40 | statusLine `segment` 在無內容時回非空 | AT-CTL-28、E2E-CTL-09 |
| MU-CTL-41 | `segment` 拋例外／無時限而使 statusLine 空白 | AT-CTL-28、E2E-CTL-09 |
| MU-CTL-42 | SessionStart 公告沙盒 slug 殘局 | AT-CTL-27、E2E-CTL-07 |
| MU-CTL-43 | `sealed_effective` 把 `none`（從未封存）當 `unreadable`／`effective`（使從未封存且 `ctx ≥ hard` 的 session 不再被封存閘推回） | AT-CTL-83、84、14 |
| MU-CTL-44 | `ackhook.on_ack` 對擁有者＝acker（自續跑）也撤 park | AT-CTL-85、E2E-CTL-24 |
| MU-CTL-45 | R2 命中也寫 pending（`ensure_pending` 不判 `reason=hard`／不判 `ctx ≥ hard`） | AT-CTL-86、43、52 |
| MU-CTL-46 | `ensure_pending` 依賴 `.advised` 閂鎖（閂鎖已寫即不建立） | AT-CTL-86 |
| MU-CTL-47 | `account_changed` 在 `parked_account` 缺（`None`）時判真 | AT-CTL-87、46 |
| MU-CTL-48 | PRD 鎖改回「`git diff` 對 HEAD」或容許改行（行級子序列退化為只比行數／只比新增行） | AT-CTL-89 |
| MU-CTL-49 | `park_cli.cancel_marker` 只改標記不拆備援排程 | AT-CTL-85、E2E-CTL-24 |

## 6. 逐功能 E2E 覆蓋表（每個 REQ ≥1 個真機 E2E）
| REQ | E2E | 備註（不可達者與替代） |
|---|---|---|
| 01 | E2E-CTL-01、03 | — |
| 02 | E2E-CTL-01、02 | E2E-CTL-02 的 ENV 分支（模型未派 Agent）不算 PASS，重跑 |
| 03 | E2E-CTL-01、02、04 | — |
| 04 | E2E-CTL-01、03 | 原始碼掃描屬 AT-CTL-04（非 E2E），E2E 以真 hook 行為證明單一判準 |
| 05 | E2E-CTL-03 | — |
| 06 | E2E-CTL-03、08 | — |
| 07 | E2E-CTL-02、04 | — |
| 08 | E2E-CTL-05 | — |
| 09 | E2E-CTL-05 | — |
| 10 | E2E-CTL-05 | — |
| 11 | E2E-CTL-06 | — |
| 12 | E2E-CTL-06、22 | — |
| 13 | E2E-CTL-06 | 真 `a28de7322775c13d3` 現場以夾具形狀重現，不動真 `~/.claude/projects` |
| 14 | E2E-CTL-07、22；**E2E-CTL-23（互動半）** | 畫面顯示＝〔OI〕V-CTL1 |
| 15 | E2E-CTL-08 | — |
| 16 | E2E-CTL-09；**E2E-CTL-23（互動半）** | `-p` 不執行 statusLine 時改以真 payload 重放，互動顯示＝〔OI〕V-CTL1 |
| 17 | E2E-CTL-10、22 | — |
| 18 | E2E-CTL-11、22 | — |
| 19 | E2E-CTL-10、12 | 「`claude -r` 後代理可否接回」＝TH-6，不宣稱 |
| 20 | E2E-CTL-07、12；**E2E-CTL-23（互動半）** | Stop `systemMessage` 畫面顯示＝〔OI〕V-CTL1 |
| 21 | E2E-CTL-20 | — |
| 22 | E2E-CTL-13 | — |
| 23 | E2E-CTL-14 | — |
| 24 | E2E-CTL-14 | — |
| 25 | E2E-CTL-14 | — |
| 26 | E2E-CTL-13 | — |
| 27 | E2E-CTL-13、16 | — |
| 28 | E2E-CTL-13、20 | — |
| 29 | E2E-CTL-15 | — |
| 30 | E2E-CTL-03、13 | — |
| 31 | E2E-CTL-16、22 | — |
| 32 | E2E-CTL-16、17、22 | — |
| 33 | E2E-CTL-16、22 | — |
| 34 | E2E-CTL-16、22 | — |
| 35 | E2E-CTL-18 | — |
| 36 | E2E-CTL-16、18 | — |
| 37 | E2E-CTL-17 | — |
| 38 | E2E-CTL-18 | — |
| 39 | E2E-CTL-15 | — |
| 40 | E2E-CTL-15 | — |
| 41 | E2E-CTL-19 | — |
| 42 | E2E-CTL-19 | — |
| 43 | E2E-CTL-15 | — |
| 44 | E2E-CTL-21 | 文件類需求的「真」＝真跑 `git diff`／落點鎖／LOC 檢查 |
| 45 | E2E-CTL-21 | 同上 |
| 46 | E2E-CTL-21 | 同上 |
| 47 | E2E-CTL-24 | 真排程＋真 `handoff --ack` 行程；真互動窗不需要 |
| 48 | **無真機 E2E（誠實劃界）**：改以 E2E-CTL-15 同載具的 `waste_census` 真跑對真逐字稿母體出 M-C6 數字（零 token、只讀） | M-C6 是觀察量測、非行為；行為面（無人窗口不被整批殺）已由 DEF-200-575 既有 realverify 案覆蓋，本稿不重造（W7 對帳 `cases.json`）；r3：本列為 §7 明載的備援劃界——REQ-CTL-48 為觀察量測、不入 `RV-CTL01`～`RV-CTL24` |

**ENV 與未驗證項（誠實劃界，不算 PASS，不作為整案 FAIL；殘項登 OIR）**：①E2E-CTL-02／06／10／14 的「模型未呼叫預期工具」＝ENV 重跑；②E2E-CTL-09 的 `-p` 不執行 statusLine ⇒ 以真 payload 重放為準；③E2E-CTL-23 需人目視（OI-20261120-010 同款）；④`claude -r` 後在飛代理接回、猝死路端到端（DES TH-6）——本檔**不宣稱**；⑤真 OS 睡眠下的哨兵探針（macOS）——同 QW §0.4-5，預設不跑。

## 7. 交卷判準（W8 收尾窗口）
1. AT 92／92 綠；MU 49／49 各自使指定測試轉紅（突變實跑輸出入證據檔；突變轉紅的 E2E 證據是舊 oracle 推回、替身 claude 被呼叫或痕跡）。
2. E2E 24／24 在 `RealVerify_Result_Ledger.md` 最近一次結果為 PASS（ENV 與 E2E-CTL-23 依 §6 末段另列，不算 PASS；其殘項登 OIR，且互動半非 PASS 時明寫「畫面顯示未驗」）。
3. 根層全套（`runlong`／`waitfor` 形態）與 `ruff check tools/ .claude/hooks/` 綠；QW 的 AT-QW-61 與 SE 的 AT-SE-39 在 W1～W6 各 commit 後仍綠；SE／QW 黃金序列（AT-SE-31、E2E-SE-09）在 W6 後逐字不變。
4. QA 獨立審查 PASS，且以 E2E-CTL-01「修前紅（舊 oracle＋MU-CTL-01）、修後綠」重現 65389f03 的 A4。
5. DES §17 追加註記 N-1～N-10 全數套用；PRD §16.6 兩列〔OI〕依 1～4 逐項結案；DES §13 理論洞 TH-1～TH-8（r3：含有條件的 TH-8）抄進證據檔並各附升級觸發條件。
6. 守衛面碼的暴露證據齊備：A4（逐字稿座標＋12 件痕跡）、A12／A14（掌舵者原話第 3 題、`status` 畫面）、前鏈原話缺（M-S2 9／37）、park 提前（E8、E9）、ack 撤 park（11/22 主控手動 `park --cancel` 實例，DES §20.2）；**pending／`switch_due` 小塊＝預防性（情境真實命中 3、損害在現行機制下未證，DES §7.7；主控裁決 2 代決）——若再審認定不足則整塊降為 TH-8、不寫守衛碼，W5 其餘不受影響**；理論洞不寫守衛碼。
7. 各包交卷附當回合 `check_loc_budget.py --json` 輸出（DES §21；r3：含 `park_cli.py` 餘額現查，W4b／W6 動工前後各一次）；REQ-CTL-48 無真機 E2E 為誠實劃界（§6 表第 48 列：以 `waste_census` 真跑量測代之，不算入 E2E 24／24，亦不入 `cases.json`）；W1 交卷附 `wake_package` 既有測試遷移對照表（AT-CTL-15）。


## 實作對照註記（2026-11-23 收尾；只增註記，既有條文不改）

1. **AT-CTL-32** 的 `rosterscope.cut_kind` 實作在 `tools/lib/sessionctl/agentbrief.py::cut_kind`（名稱以實作為準；AT 的判準與樣本不變）。
2. `agentbrief.STOPPED_RECENT_SECONDS`＝24 小時（`stopped` 只認近期被 TaskStop 者），見 Control_Handover DES §23。
3. REQ-CTL-20 三處出聲掛 `cutvoice`（`roster.stop_message`、`watch`、`briefline`），REQ-CTL-47 的 `ackhook` 掛在 `tools/sessionctl.py` 入口層（`ackhook.after_handoff`），不在 `handoff.py` 內。