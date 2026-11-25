# TCS-Autopilot-20261125：自動駕駛開發——單一額度判決、換帳號作廢、合入推送管線、詢問類別閘（需求＋驗收合一）

> 上游：PRD `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 修訂表 v2.1.28、v2.1.29（勘誤）、§4.1.5 R-4.1.5-1、§4.1.6、§4.1.7、§4.5.12、§15.5 紅線 14、§16.6 2026-11-25 兩列；設計 `docs/02_architecture/QuotaVerdict_AccountSwitch_Design.md` v1.1（下稱 QVD）、`docs/02_architecture/Autopilot_Pipeline_Design.md` v1.1（下稱 APD）、`docs/04_planning/ADR/ADR-XPLAT-018-autopilot-merge-carrier.md`（下稱 ADR-018）；SelfImproving_PRD AC-SI-30-1／NFR-SI-07-5／FC-l 與 SelfImproving_Ledger_DB_PRD AC-LD-12-3 的 2026-11-25 註記。
> **狀態（2026-11-25，SD-1 v1.1）**：規格階段，實作未開始。所有 AT／MU／E2E 狀態欄＝「待實作」；未跑不得寫成已驗。v1.0 → v1.1 依 QA-S 審查修訂（§6）。
> 測試座標約定：`QV`＝`tools/tests/test_sessionctl_qv.py`（新）、`MG`＝`tools/tests/test_autopilot_merge.py`（新）、`PS`＝`tools/tests/test_autopilot_push.py`（新）、`HK`＝`tools/tests/test_sessionctl_hooks.py`（既有，增量）、`OW`＝`tools/tests/test_sessionctl_oldwin.py`（既有，增量）、`CW`＝`tools/tests/test_ci_wait.py`（既有，增量）、`CR`＝`tools/tests/test_check_defect_log_crossref.py`（既有，增量）、`PH`＝`tools/tests/test_check_pending_handoff.py`（既有，增量）、`CP`＝`tools/tests/test_claim_provenance_r86.py`（既有，增量）、`SI`＝`tools/tests/test_selfimproving_schedule_patrol.py`（既有，改斷言＋增量；實作棒以 `git grep -ln "quota_check\|quota_verdict" tools/tests` 現查其他受影響 SI 測試檔）、`KW`＝`tools/tests/test_sessionctl_keepwarm*.py`（既有，實作棒現查檔名）。單元測試一律注入 `now`、路徑圍籬到 tmp、不讀真 `~/.claude`、不起真排程、不打真端點；禁用 skip。
> **E2E 定義**（掌舵者 2026-11-18：「請將所有功能都寫好完整的E To E測試案例,不要遺漏任何一個!」）：真行程、真排程、真 `claude -p` 子行程、真 git、真逐字稿重放（sid `406454ea-91fc-4481-9c11-b28ed7d9e95f`）或真讀數錄製重放才算；單元測試不算。執行＝`python tools/realverify.py run --family <家族>`，結果入帳 `docs/06_quality/RealVerify_Result_Ledger.md`；未入帳＝未結。
> **E2E 載具（v1.1 指名；F-14）**：
> - **載具 H（真 hook 二進位＋合成／錄製 payload）**：realverify 既有「工具副本沙盒」（`tools/lib/realverify/cases/sessionctl_park.py` 等：被測碼逐位元組複製到沙盒、hook 經 `_hook_launcher` 真跑），以 stdin 餵 hook payload；**不經 `claude -p`**。
> - **載具 E（端點替身）**：既有 `tools/lib/realverify/cases/prd_px_lib.py` 的 T5 替身（本機 TLS CONNECT 代理＋自簽 CA＋沙盒 HOME 假 token）。**只注入被測 CLI／hook 子行程的環境**，回應以錄製的 payload 與兩個帳號標頭（取自真實 `quota_burn.jsonl` 的 `34cd3507237f`／`eaf5241f6fe2` 樣本）組成。不用於 `claude -p`：usage 端點與 messages API 同 host，CONNECT 層分不開，替身會攔下 claude 自己的流量，且假 token 讓 claude 無法認證。
> - **載具 C（真 `claude -p`）**：真憑證、`--model haiku`，只用於必須由 harness 本身產生行為的列（WT-01 隔離起點、G1-03／G1-04 的 `CLAUDECODE` 注入、ASK-01 模型真呼叫）；不掛端點替身；額度讀數只走 `AUTOSDD_QUOTA_CACHE_DIR` 指到的錄製快取，且快取年齡在 TTL 內（不觸發補量）。
> - **時間**：不新增 `now` 注入縫（QuotaWall 設計慣例：不開測試用環境變數；守衛面准入）。改用**時間平移重放**：錄製夾具的 `measured_at`／`resets_at` 依真牆鐘平移（例：reset＝真 now＋14 分），真 CLI 於真時刻執行；需要跨過有效期者以 `sessionctl runlong`／`waitfor` 真等。
> - 不可達者：每列「不可達部分與備援」欄寫明。

## 0. 模組落點表（照 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）

| 元件 | 路徑 | §2 格 |
|---|---|---|
| 判決純函式、判決行、計費姿態推導 | 新扁平 `tools/lib/quota_ruling.py` | 函式庫：單檔共用工具（只 import `quota_policy`；QVD §8） |
| 取數、`quota` 動詞實作、`--pace` 區塊 | 新 `tools/lib/sessionctl/ruling_io.py` | 函式庫（既有 sessionctl 套件） |
| 換帳號 | 新 `tools/lib/sessionctl/acctswitch.py` | 同上 |
| 派工閘管線抽出 | 既有 `tools/lib/quota_gate.py` 新函式 `dispatch_decision()` | 存量 hub |
| 詢問類別閘 | 新 `tools/lib/sessionctl/askgate.py`；接線 `.claude/hooks/sessionctl_guard.py`、`.claude/settings.json` | 既有套件＋守衛面 |
| 合入／推送 | 新套件 `tools/lib/autopilot/`（`merge`、`carrier`、`pushgate`、`ledgersplit`、`locks`、`outcome`）；入口 `tools/autopilot.py` | 函式庫（新套件）＋指令入口 |
| 治理閘逃生口述詞 | 新扁平 `tools/lib/human_escape.py` | 函式庫：單檔共用工具 |
| 痕跡圍籬 | 新扁平 `tools/lib/suite_fence.py`；`min_tests_margin.py` 承接自 runner 抽出的兩函式 | 函式庫：單檔共用工具 |
| LOC 抽出 | 新扁平 `tools/lib/model_window_table.py`；`quota_halt_marker.py` 承接 halt 判讀 | 函式庫（扁平共用） |
| 既有改動 | `ledger_closing_guards.py`、`tools/git-hooks/pre-push`、`ciwait/core.py`、`oldwin.py`、`oldwin_sched.py`、`check_pending_handoff.py`、`check_claim_provenance.py`、`context_budget_guard.py`、`run_root_unittests.py`、`session_resume_planner.py`、`quota_*`、`session_brief.py`、`relay_machine.py`、sessionctl watch／park／parkearly／parkprobe／qw／kw／switchfacts／switchplan／controlfacts／handoff_build／converge 族、`selfimproving/{sched,patrol,fourq,writeverbs,evspec}.py` | 既有家 |
| 測試 | 新三檔（QV、MG、PS）＋既有檔增量 | 測試 |
| 真機 E2E 家族 | `tools/lib/realverify/cases/quotaverdict.py`、`tools/lib/realverify/cases/autopilot.py`（新家族檔） | realverify |

## 1. 需求（REQ）

| REQ | 需求 | PRD／設計 | 狀態 |
|---|---|---|---|
| REQ-AP-QV-01 | 單一判決函式：同一份輸入只產一個 ACTION；原始讀數帶、模型分軌週軸、spend 軸、QW stage 在函式內合成（QVD §3.2 決策表七列）；`cap` 唯一來源＝派工閘管線 `dispatch_decision()`；配速床／趕工戳記只影響 cap、不影響動作；換手計畫（`switchplan._wall`）與 park 提前恢復（`parkearly.tick`）只依判決 ACTION、不自比門檻（v1.2，QVD §3.5 C13、C21） | R-4.1.6-1、R-4.1.6-2、R-4.1.6-4、R-4.1.6-5【v2.1.29 勘誤】 | 待實作 |
| REQ-AP-QV-02 | 判決行格式（含附加欄 `mdl=`、`deg=`）與有效期；過期必重算；讀數不可用時 `expires_at＝now＋max(TTL, retry_after)` | R-4.1.6-2、R-4.1.6-3【v2.1.29 勘誤】；QVD §3.3、§4 | 待實作 |
| REQ-AP-QV-03 | halt 標記不壓補量；補量受紅線 1 四條件 | R-4.1.6-6；QVD §3.4 | 待實作 |
| REQ-AP-QV-04 | park 只在判決 `PARK｜HALT_WEEKLY` 時登記；`--why` 退役、`--next-est` 取代（缺省值由程式推導、只能往上調）；量不到 reset 不判 PARK；park 的所有訊息與判決動作一致 | R-4.1.6-5；QVD §3.2 第 3 列、§5 | 待實作 |
| REQ-AP-QV-05 | watch 額度事件只由判決觸發、單一序列閂鎖 `(acct, ACTION, win)`；`WAIT_RESET` 處置不含 park | R-4.1.6-2／4；QVD §3.5 C4／C5 | 待實作 |
| REQ-AP-QV-06 | 主控與子代理的額度宣稱須有本回合未過期判決行（Stop 只出聲）；提問期間到達的事件回覆後以有效期重算 | R-4.1.6-7、R-4.5.12-4 | 待實作 |
| REQ-AP-QV-07 | 量不到讀數 ⇒ `CONTINUE`＋`deg=unmeasured`＋`1 ≤ cap ≤ cap_prepare` 並出聲（不是 cap 0）；`--json` 帶 `billing`（與 `posture_line` 同一推導函式）與 `band` | R-4.1.5-1、R-4.1.6-8【v2.1.29 勘誤】；QVD §3.2 第 6 列、§3.3 | 待實作 |
| REQ-AP-QV-08 | LOC 抽出為純搬移：搬移 commit 全套綠、行為零差異；抽出後各檔在分級內、`SPECIAL_FILES` 門檻下修 | QVD §9 | 待實作 |
| REQ-AP-QV-09 | SelfImproving 巡邏、研究免掃、四問降載改讀判決（經 CLI `--json`，不 import sessionctl）：跳過＝`ACTION ≠ CONTINUE` 或 `deg=unmeasured`；降載＝`band ∈ {notice, converge}`；子行程失敗＝跳過 | 主控代決 ①；SelfImproving_PRD AC-SI-30-1、NFR-SI-07-5、FC-l 註記；QVD §3.5 C18 | 待實作 |
| REQ-AP-QV-10 | 單一判讀家機械鎖：判決輸入原語的呼叫站點與白名單相等；扁平檔不得 import `lib.sessionctl` | R-4.1.6-8；QVD §3.5.3 | 待實作 |
| REQ-AP-QV-11 | `WAIT_RESET` 叫醒載具：互動窗口由 keepwarm 以 `ruling_wait_reset` 來源單跳到 `win＋skew`（不受 `small_ctx`／`no_usage`／n* 限制）；無人窗口交哨兵；模式非 auto／保溫關閉時理由句明寫無載具 ；Stop 時判決為 `WAIT_RESET` 且無 running keepwarm ⇒ 保溫閘推回一次要求掛載，`small_ctx`／`no_usage`／n* 不豁免（v1.2） | R-4.1.6-4【v2.1.29 勘誤】【v2.1.29 勘誤（續）】；QVD §3.6 | 待實作 |
| REQ-AP-AC-01 | halt 標記、rush 戳記、閂鎖、保溫帳新寫入帶 `account`；量不到寫 `null` 並出聲 | R-4.1.7-1 | 待實作 |
| REQ-AP-AC-02 | 帳號不符 ⇒ 標記改名 `.void-<ts>` 作廢、落 `account_switch`、出聲一次；舊格式標記依同軸讀數判 | R-4.1.7-3～5 | 待實作 |
| REQ-AP-AC-03 | 三個零 API 觸發器（憑證檔 mtime／size、逐字稿 `/login`、指紋變化）皆觸發補量；觸發器本身不作廢任何標記 | R-4.1.7-2、R-4.1.7-3 | 待實作 |
| REQ-AP-AC-04 | 被動觀測：真實 `/login` 後一個 TTL 內必有 `account_switch`；判決行與 `sessionctl status` 顯示帳號指紋；判決行附「已作廢 n 個」 | R-4.1.7-6 | 待實作 |
| REQ-AP-MG-01 | `autopilot merge`：repo 外獨立 clone rebase、略過已吸收、帳本尾端提交、補連動鎖、全套、綠才 ff、清理；冪等、不留半套 | APD §3.2 | 待實作 |
| REQ-AP-MG-02 | 合入期全套＝pre-push 同款（合成 stdin 呼叫，leg 集合相同） | APD §3.3 | 待實作 |
| REQ-AP-MG-03 | 驗證載具測的是合入樹：`.venv` 連結＋`PYTHONPATH`＋每次執行期自證（`carrier_leak`）＋三子樹紅綠自證；連結清理只刪連結；空間不足 `no_space`；機器本地狀態白名單帶入並逐筆驗雜湊、同 clone 基線對照（候選紅 ⊆ 基線紅 ⇒ `carrier_divergence`，不算代理的紅；v1.2） | APD §3.2 步 0／4.5／4.7／5／6；ADR-018 D1～D3、D5 | 待實作 |
| REQ-AP-WT-01 | 代理 worktree 起點＝本地 HEAD（`worktree.baseRef: "head"`）；merge 記錄 `base_drift`；合入後殘留代理分支／worktree 普查 | APD §3.1；ADR-018 D4 | 待實作 |
| REQ-AP-G1-01 | 帳本淨額棘輪：推送期逐 ref 比 pre-push stdin 的 `<local_sha>` 對 `<remote_sha>`（不讀工作樹）並阻斷；提交期只出聲 | APD §4.1 | 待實作 |
| REQ-AP-G1-02 | 推送閘：淨額 > 0 ⇒ 產同輪修復任務書、前綴推送可達；判決非 `CONTINUE` 不推 | APD §4.2、§4.3 | 待實作 |
| REQ-AP-G1-03 | `AUTOSDD_NET_RATCHET_OFF` 在 `CLAUDECODE` 或 `AUTOSDD_UNATTENDED` 下無效並出聲 | APD §5 | 待實作 |
| REQ-AP-G1-04 | 提交／推送期治理閘逃生口族（`AUTOSDD_NET_RATCHET_OFF`、`AUTOSDD_SNAPSHOT_GATE_OFF`）一律經單一述詞 `human_escape.honored()`；族名直接環境讀取只准出現在該檔；族常數只增不減 | 主控代決 ②；APD §5；SelfImproving_Ledger_DB_PRD AC-LD-12-3 註記 | 待實作（快照閘本身未實作，見 §5 OI 需求） |
| REQ-AP-ASK-01 | AskUserQuestion 類別閘：只放行 `[IRREVERSIBLE]`（必填系統與原因）、`[COST]`（必填服務與預估 > 50 美元；服務為 Claude／Anthropic 且 `billing=subscription_only` 擋）、`[K1]`（須寫「須掌舵者親打」、選項不含「核准」）；「要不要＋可代決動作」句型阻斷（不論標籤；v1.2：動作詞須為被問的對象＝疑問詞之後 12 字元內的複合動作詞，單詞「繼續」不收；阻斷訊息不得把不可復原或花錢的動作交給模型決定）；名詞不阻斷；無人窗口全擋；放行落 `ask_allowed` | R-4.5.12-3～5【v2.1.29 勘誤】；APD §7 | 待實作 |
| REQ-AP-ASK-02 | `check_pending_handoff` 推回文案改「先代決、三類才問」；描述分類規則／複述掌舵者定義的句子不判交棒；`check_claim_provenance` 不把敘述過去事件的「被擋／擋下」當本場宣稱 | R-4.5.12-1；APD §7、§13 | 待實作 |
| REQ-AP-CI-01 | `ci_wait` 認得排隊逾時（`queue_timeout`）並自動重跑（同 sha ≤ 2 次） | APD §6 | 待實作 |
| REQ-AP-OW-01 | 舊視窗關閉事件驅動＋指數退避（上限 12 小時）；本 PRD 機制全部訊息家不含「請手動」「請您」「手動跑」「請人」（例外逐筆列名） | R-4.5.12-1／2；APD §8 | 待實作 |
| REQ-AP-FN-01 | 全套期間痕跡圍籬：真痕跡目錄出現夾具形新列 ⇒ 全套 rc≠0；runner 先抽出再加（SPECIAL 不破） | APD §9、§11 | 待實作 |

## 2. 驗收（AC → AT）

### 2.1 QV（`QV::VerdictTest` 等；純函式，注入 state／decision／markers／plan／model／now）

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-QV-01a | 短窗 87%、D=14、`stage=free`、`QV_WAIT_RESET_MIN=45` ⇒ `WAIT_RESET`；輸出不含 `PARK` | `QV::VerdictTest::test_87pct_14min_waits_reset_not_park` |
| AC-QV-01b | 決策表七列逐列正反例：第 1 列 spend 撞限 ⇒ `HALT_WEEKLY wk=none`；第 2 列週軸 ⇒ `HALT_WEEKLY` 且**優先於**同時成立的短窗第 3 列；第 3 列 D>45 ⇒ `PARK`、短窗 reset 量不到 ⇒ `NODISPATCH`；第 4 列 `stage=nodispatch` ⇒ `NODISPATCH`；第 5 列 `next_est ≥ R−V` 的三分支、`next_est < R−V` ⇒ 不命中；第 6 列見 AC-QV-07a；第 7 列 | `QV::VerdictTest::test_table_rows_*`（每列一方法，正反例各一） |
| AC-QV-01c | 性質：對笛卡兒積（band × stage × D（含量不到）× next_est × 標記 × 模型 × 讀數可用與否）輸出恰一個 ACTION、`cap>0` 僅在 `CONTINUE` | `QV::VerdictTest::test_exactly_one_action_property` |
| AC-QV-01d | 具名時刻斷言（F-17；取自真實 `quota_burn.jsonl` 2026-11-24～25 的固定夾具，測試時複製到 tmp）：2026-11-25 03:46:19 列（five_hour 87%、reset 04:00、`stage=free`）⇒ `WAIT_RESET win=…04:00`；04:00:32 列（0%）⇒ `CONTINUE`；2026-11-24 20:50 列（`account=34cd3507237f`）與 03:43 列（`account=eaf5241f6fe2`）的 `acct` 欄各自等於該列帳號 | `QV::VerdictTest::test_named_moments_from_burn_ledger` |
| AC-QV-01e | 模型分軌（F-06）：Fable 專屬週軸 100%、全模型週軸 60% ⇒ `model=sonnet` 判 `CONTINUE`、`model=fable` 判 `HALT_WEEKLY` | `QV::VerdictTest::test_model_scoped_weekly_axis` |
| AC-QV-01f | 配速床與趕工戳記只改 cap（F-08）：同一份原始讀數，`decision` 分別以有／無配速床、有／無 rush 產生 ⇒ 四種組合的 ACTION 相同、cap 可不同 | `QV::VerdictTest::test_pace_floor_and_rush_affect_cap_only` |
| AC-QV-01g | cap 來源（F-01 ②；v1.2 依 QA 複審 N-06 改寫）：`CONTINUE` 時 `cap == dispatch_decision(...).cap`（`None` ⇒ `== policy.max_fanout`）；注入一個 `stage=free` 但其他欄位任意的 `plan` 替身（含帶多餘 `cap` 屬性的替身）⇒ 判決 cap 不變；`quota_gate()` PreToolUse 記 fanout 帳所用的 cap 與同一時刻判決行 `cap=` 相等 | `QV::VerdictTest::test_cap_is_dispatch_pipeline`、`QV::ConsumerTest::test_gate_and_line_share_cap` |
| AC-QV-02a | 判決行欄位齊全、`expires_at＝min(measured_at+180s, 短窗 reset)`、時刻帶 offset、`vid` 對同輸入穩定、附加欄只在尾端 | `QV::RenderTest::test_line_fields_and_expiry` |
| AC-QV-02b | `--pace`、watch、park、SessionStart 簡報、`qw_cli`、交接包六處第一個額度行皆為 `QUOTA_VERDICT=` | `QV::ConsumerTest::test_consumers_print_verdict_first` |
| AC-QV-02c | 消費端拿到過期判決 ⇒ 重算並落 `stale_verdict_recomputed`；不以舊 vid 行動（例：watch 輸出檔的舊 vid 為 `PARK`、重算為 `CONTINUE` ⇒ 不 park） | `QV::ConsumerTest::test_stale_verdict_recomputed` |
| AC-QV-02d | 讀數不可用時 `expires_at＝now＋max(180, retry_after)`，且 `> now`（F-19） | `QV::RenderTest::test_unusable_state_expiry_in_future` |
| AC-QV-03a | halt 標記有效＋快取超過 TTL ⇒ 補量恰一次（同 TTL 內第二次不補） | `QV::GatherTest::test_halt_does_not_suppress_refresh` |
| AC-QV-03b | 429（帶 retry-after）⇒ 降級出聲、判決 `CONTINUE deg=unmeasured`、`1 ≤ cap ≤ cap_prepare`、不重試 | `QV::GatherTest::test_429_degrades_to_capped_continue` |
| AC-QV-04a | 判決 `CONTINUE` ⇒ `park` rc 4 並印判決行；傳 `--why` ⇒ argparse 錯誤並指路 `--next-est` | `QV::ParkTest::test_continue_refuses_and_why_retired` |
| AC-QV-04b | `--next-est` ≥ R−V 且 D>45 ⇒ `PARK` ⇒ 登記（縫 `ARM`）並印排程憑證；D≤45 ⇒ `WAIT_RESET`、不登記 | `QV::ParkTest::test_next_est_drives_park_or_wait` |
| AC-QV-04c | park 的任何輸出（拒絕、登記、狀態）所印動作與當下判決 ACTION 一致；拒絕文案不含 `--why`（`--done --why` 除外）；短窗 reset 量不到時判決為 `NODISPATCH` 而非 `PARK`，park 拒絕訊息與 Stop 推回不互相指向（F-07） | `QV::ParkTest::test_park_messages_match_verdict` |
| AC-QV-04d | `--next-est` 缺省＝`cal_agent × max(1, n_plan)`；給的值低於缺省 ⇒ 取缺省（F-25） | `QV::ParkTest::test_next_est_default_and_floor` |
| AC-QV-05a | watch 單一序列：`WATCH_VERDICT=quota action=<A> vid=<v> expires_at=<t>`；同 `(acct,ACTION,win)` 只觸發一次 | `QV::WatchTest::test_single_series_latch` |
| AC-QV-05b | `WAIT_RESET` 處置列不含「park」；`keepwarm.SERIES` 不存在 | `QV::WatchTest::test_wait_reset_disposition_has_no_park` |
| AC-QV-06a | Stop 宣稱守衛：重放 L2564 回合（夾具化逐字稿片段）⇒ 出聲一次 | `CP::QuotaVerdictClaimTest::test_l2564_claim_without_verdict_voices` |
| AC-QV-06b | 同回合有未過期 `QUOTA_VERDICT=` ⇒ 靜默；只有過期者 ⇒ 出聲 | `CP::QuotaVerdictClaimTest::test_fresh_verdict_silences` |
| AC-QV-06c | 子代理陳述（F-18）：判準函式吃子代理逐字稿片段（含額度判斷詞、無判決行）⇒ 回出聲文字；接線面（SubagentStop 未註冊）照實劃界，見 E2E 表 | `CP::QuotaVerdictClaimTest::test_subagent_transcript_judged_same` |
| AC-QV-06d | 提問期間的事件（R-4.5.12-4）：AskUserQuestion tool_result 之前取得的判決行，在其後的額度陳述中視同過期（判準＝判決行時刻早於最近一次 AskUserQuestion 結果）⇒ 出聲 | `CP::QuotaVerdictClaimTest::test_verdict_before_question_is_stale` |
| AC-QV-07a | 讀不到 state（無可用軸）、無標記、無 L3 地板 ⇒ `CONTINUE deg=unmeasured`、`1 ≤ cap ≤ cap_prepare`＋出聲；同時有同帳號 halt 標記 ⇒ 依標記走第 2／3 列 | `QV::VerdictTest::test_unreadable_is_capped_continue` |
| AC-QV-07b | `billing` 四值推導由 `quota_ruling.billing_from_posture()` 產生，`posture_line()` 呼叫同一函式；欄位缺 ⇒ `unknown` | `QV::RenderTest::test_billing_from_posture` |
| AC-QV-08a | 抽出後 `check_loc_budget --json` 無違規；`context_budget_guard.py`、`run_root_unittests.py` 的 `SPECIAL_FILES` 門檻等於新實值 | `tools/tests/test_adr_xplat001_c1c2_lock.py`（既有，CLOSE 重釘後綠） |
| AC-QV-08b | `pace_report` 不再存在於 `quota_gate`（hub 成員只縮不長） | `QV::LocTest::test_pace_report_moved_out_of_hub` |
| AC-QV-09a | SI `quota_check` 以替身 CLI 輸出（`--json`）判定：`CONTINUE` ⇒ 不跳過；`WAIT_RESET`／`PARK`／`NODISPATCH`／`HALT_WEEKLY` ⇒ 跳過 `quota-band`；`CONTINUE deg=unmeasured` ⇒ 跳過；子行程 rc≠0 或 JSON 不可解析 ⇒ 跳過 | `SI::QuotaVerdictConsumptionTest::test_skip_by_action_and_deg` |
| AC-QV-09b | 降載＝`band ∈ {notice, converge}`（`fourq` 用 `fourq_degrade_items_max`）；`research.skip` 的 `band` 附註值＝判決行 | `SI::QuotaVerdictConsumptionTest::test_degrade_and_skip_note` |
| AC-QV-09c | `tools/lib/selfimproving/` 不 import `sessionctl` 也不 import `quota_gate`（AST） | `SI::QuotaVerdictConsumptionTest::test_no_cross_package_import` |
| AC-QV-10a | 單一家鎖：判決輸入原語的呼叫站點集合 == `RULING_INPUT_SITES` | `QV::SingleHouseTest::test_sites_equal_allowlist` |
| AC-QV-10b | 鎖有鑑別力：合成樹多一個私有判讀站點 ⇒ 紅；白名單多一個不存在站點 ⇒ 紅；別名 import 仍可認 | `QV::SingleHouseTest::test_lock_discriminates` |
| AC-QV-10c | 扁平檔（`tools/lib/*.py`）不 import `lib.sessionctl`（AST） | `QV::SingleHouseTest::test_flat_files_do_not_import_sessionctl` |
| AC-QV-10d | 包裝入口可見（N-02）：合成樹新增一個函式，以 `park._pace_state(now)` 取數（不直接呼叫任何原語）⇒ 鎖紅並列出該檔＋函式；以 `quota_gate.pace_state`、`settled_quota`、`qw_wall.default_read` 各取一次同樣紅 | `QV::SingleHouseTest::test_wrapper_entry_sites_are_seen` |
| AC-QV-10e | 門檻比較可見（N-02）：合成樹新增 `if axis.pct >= policy.prepare_pct:`（取數由參數傳入、無任何呼叫原語）⇒ 鎖紅；同一比較寫在 `quota_policy*.py`／`quota_ruling.py` 內 ⇒ 不計 | `QV::SingleHouseTest::test_threshold_compare_sites_are_seen` |
| AC-QV-10f | 白名單形狀（N-09）：`RULING_INPUT_SITES` 每項帶非空 WHY 與分類（`B1`…`B7`／`ruling`／`diag`）；`diag` 項恰為 QVD §3.5.3 列舉的四處（watch `plan_fn`、`kw_wake`、`switchfacts` 的 `qw_plan.plan`、`qw_cli`）；改接後真樹上鎖綠 | `QV::SingleHouseTest::test_allowlist_entries_have_category_and_why` |
| AC-QV-11a | 互動 auto：判決 `WAIT_RESET`、`stage=free`、ctx 小於 `AUTOSDD_KEEPWARM_MIN_CTX_TOKENS` ⇒ `wake_target` 回 `(win＋skew, "ruling_wait_reset", …)`，`skip_reason` 不使指令不掛 | `KW::RulingWaitResetTest::test_small_ctx_still_wakes_at_win` |
| AC-QV-11b | 保溫帳 pings 已達 n* ⇒ `ruling_wait_reset` 仍單跳、不付費 ping | `KW::RulingWaitResetTest::test_cap_does_not_block_single_hop` |
| AC-QV-11c | 無人窗口 ⇒ 不掛 keepwarm；哨兵判定（C11）對 `WAIT_RESET` 維持撞線等待並以 `win＋skew` 武裝 | `KW::RulingWaitResetTest::test_unattended_hands_to_sentinel` |
| AC-QV-11d | 模式非 auto 或 `AUTOSDD_KEEPWARM_OFF` ⇒ 判決理由句含「不會在重置後自動叫醒」；`check_pending_handoff` 半路停工判準把該句視為合法換手標記 | `KW::RulingWaitResetTest::test_no_carrier_is_said`、`PH::AutopilotWordingTest::test_no_carrier_sentence_is_legit_stop` |
| AC-QV-11e | 掛載推動者（N-05）：判決 `WAIT_RESET`＋ctx 小於 `AUTOSDD_KEEPWARM_MIN_CTX_TOKENS`＋`background_tasks` 無 running 項 ⇒ `keepwarm.stop_verdict` 回非空推回文字（含 `keepwarm --sid` 與判決行）；同條件改 `no_usage`（ctx 量不到）、或保溫帳 `pings ≥ n*` ⇒ 仍推回；`background_tasks` 只有 running 的 watch（無 keepwarm）⇒ 仍推回；有 running keepwarm ⇒ 不推；`stop_hook_active` ⇒ 不推；`park.stop_verdict` 對同一 payload 回空 | `KW::RulingWaitResetTest::test_stop_pushes_keepwarm_on_wait_reset_despite_small_ctx` |
| AC-QV-11f | 前四項仍豁免：同 AC-QV-11e 條件但 `AUTOSDD_UNATTENDED`／模式非 auto／`AUTOSDD_KEEPWARM_OFF`／已交棒 ⇒ 不推；判決非 `WAIT_RESET` ⇒ 回到原判準（小上下文不推） | `KW::RulingWaitResetTest::test_stop_first_four_still_exempt` |
| AC-QV-12a | 換手計畫不出 PARK（N-01 ②）：E2 讀數（短窗 87%、D=14、`stage=free`）組出的判決 `WAIT_RESET` 餵 `switchplan.decide` ⇒ `action == STAY`、`reason` 含 `wait_reset`、`flags.keepwarm`，且**不是** `PARK_UNTIL`／`PARK_POLL` | `QV::ConsumerTest::test_switchplan_wait_reset_never_parks` |
| AC-QV-12b | 換手計畫依判決對映：`PARK` ⇒ `PARK_UNTIL` 目標＝`win`（D>6 小時 ⇒ `PARK_POLL`）；`HALT_WEEKLY` ⇒ `PARK_POLL` 目標＝`wk`；`HALT_WEEKLY wk=none`（spend）⇒ `STAY spend_limit`；`CONTINUE`／`NODISPATCH` ⇒ 不由額度列命中；週軸 80%（≥ prepare、< halt）而判決 `CONTINUE` ⇒ 不出 PARK（舊判準以 prepare 判週軸）；取數失敗（`action=None`）⇒ 不出 PARK；`switchplan.Quota` 無 `short_pct`／`weekly_pct`／`prepare_pct` 欄（結構斷言） | `QV::ConsumerTest::test_switchplan_maps_ruling_actions` |
| AC-QV-13a | park 提前恢復受判決約束（N-01 ①）：park 標記 `parked_pct=92`、當下讀數 80（< prepare、比基準低 12pp）、但 `plan.stage=close` ⇒ 判決 `PARK` ⇒ `parkearly.tick` 不呼叫 `fire_early`（以縫計數 0）、痕跡 `park_early_probe` 帶 `action=PARK` | `QV::ConsumerTest::test_parkearly_respects_park_ruling` |
| AC-QV-13b | 判決 `CONTINUE` 且讀數比基準低 ≥ 5pp ⇒ fire 一次；判決 `CONTINUE` 但只低 3pp ⇒ 不 fire（遲滯閘保留）；判決 `CONTINUE deg=unmeasured` ⇒ 不 fire；`parkprobe.evaluate` 原始碼不再引用 `prepare_pct`（AST） | `QV::ConsumerTest::test_parkearly_fires_only_on_continue_with_drop` |

### 2.2 AC 換帳號（`QV::AcctSwitchTest`）

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-AC-01a | 三種持久狀態新寫入 schema 必有 `account`；量不到 ⇒ `null`＋出聲 | `QV::AcctSwitchTest::test_writes_carry_account` |
| AC-AC-02a | 標記 `34cd3507237f`、快取 `eaf5241f6fe2` ⇒ 改名 `.void-<ts>`、`account_switch` 一列、出聲一次、`--pace` 不印 halted | `QV::AcctSwitchTest::test_mismatch_voids_marker` |
| AC-AC-02b | 舊格式標記＋同軸讀數低於門檻 ⇒ 作廢；高於 ⇒ 保留並補寫 `account` | `QV::AcctSwitchTest::test_legacy_marker_by_reading` |
| AC-AC-02c | park 標記不在本流程作廢（走 `parkprobe.account_changed`）；rush 戳記不符即作廢 | `QV::AcctSwitchTest::test_park_delegated_rush_voided` |
| AC-AC-03a | 憑證檔 (mtime,size) 變 ⇒ 觸發；不變 ⇒ 不觸發；macOS（注入平台）⇒ T① 缺席並照實出聲 | `QV::AcctSwitchTest::test_trigger_credentials_file` |
| AC-AC-03b | 逐字稿增量出現 `<command-name>/login</command-name>` ⇒ 觸發；byte offset 前已讀者不重觸發 | `QV::AcctSwitchTest::test_trigger_login_record` |
| AC-AC-03c | 指紋變化 ⇒ 觸發 reconcile | `QV::AcctSwitchTest::test_trigger_fingerprint_change` |
| AC-AC-03d | 觸發器成立但補量失敗（量不到指紋）⇒ 不作廢任何標記（R-4.1.7-3）；補量成功且指紋相同 ⇒ 不作廢 | `QV::AcctSwitchTest::test_trigger_alone_never_voids` |
| AC-AC-04a | 換帳號後第一行判決附「已作廢 n 個舊帳號標記」；同一對 old→new 只出聲一次 | `QV::AcctSwitchTest::test_first_verdict_reports_voided` |
| AC-AC-04b | 任何輸出不含「建議換帳號」類字樣（詞表） | `QV::AcctSwitchTest::test_no_switch_advice_wording` |
| AC-AC-04c | `sessionctl status` 輸出含帳號指紋（12 碼）或 `acct=none`（F-18） | `QV::AcctSwitchTest::test_status_shows_fingerprint` |

### 2.3 合入、推送、棘輪（`MG`／`PS`／`CR`；真 git 於 tmp 拋棄式 repo）

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-MG-01a | W11b2 形狀（代理起點落後、main 已含 W6）⇒ rebase 成功；有衝突 ⇒ `conflict`＋衝突包、主樹與 clone 都不留 rebase 狀態 | `MG::MergeTest::test_rebase_or_conflict_bundle` |
| AC-MG-01b | 同指令重跑 ⇒ `MERGE_VERDICT=noop`（patch-id 略過） | `MG::MergeTest::test_idempotent_rerun` |
| AC-MG-01c | 全套紅（縫：假 pre-push 回 1）⇒ `red`、主樹 HEAD 不動 | `MG::MergeTest::test_red_suite_keeps_main` |
| AC-MG-01d | 帳本變更散在三個提交 ⇒ 結果中帳本只出現在尾端單一提交、其餘提交不含帳本檔 | `MG::MergeTest::test_ledger_changes_moved_to_tail` |
| AC-MG-01e | 清理用 `git worktree remove`（不帶 `--force`）與 `git branch -d`；`git worktree list` 與 `git branch --list "worktree-agent-*"` 回到起始集合 | `MG::MergeTest::test_cleanup_no_force` |
| AC-MG-01f | 鎖：第二個 merge 在鎖存在時回 `busy`；主樹髒 ⇒ `dirty` | `MG::MergeTest::test_lock_and_dirty` |
| AC-MG-01g | `repin_growth_problems()` 非空 ⇒ `repin_blocked`、不改上限常數 | `MG::MergeTest::test_repin_blocked` |
| AC-MG-01h | 驗證載具是獨立 clone：clone 的 `git rev-parse --git-common-dir` 指向 clone 自己（不是主樹 `.git`） | `MG::CarrierTest::test_clone_has_own_git_dir` |
| AC-MG-02a | 合成 stdin 呼叫的 pre-push 與真 `git push` 觸發的 pre-push 收到相同四欄、跑相同 leg 集合（以 leg 名稱集合比對） | `MG::PrePushParityTest::test_synthetic_stdin_same_legs` |
| AC-MG-03a | 執行期自證：以注入縫讓 `import autoclaude` 解析到 clone 外 ⇒ `MERGE_VERDICT=carrier_leak`、不跑全套、印兩個實際路徑 | `MG::CarrierTest::test_leak_is_fail_closed` |
| AC-MG-03b | 紅綠自證：只在 clone 的 `tools/`、`AutoClaude/`、`AISDLC_SDD/<LATEST>/` 各植一個讓對應 leg 轉紅的突變（主樹不植）⇒ 全套紅且三條 leg 各自紅；不植 ⇒ 綠 | `MG::CarrierTest::test_clone_only_mutations_turn_suite_red`（真全套，`runlong`／`waitfor`；E2E-AP-MG-03 同載具） |
| AC-MG-03c | 清理：`.venv` 連結被刪、目標（主樹 `.venv`）完好；以注入縫讓連結身分驗不到 ⇒ 中止清理並記痕跡、不遞迴刪 | `MG::CarrierTest::test_link_removed_target_intact` |
| AC-MG-03d | 可用空間 < 2×已追蹤檔總大小（縫：空間查詢）⇒ `no_space`、不建 clone | `MG::CarrierTest::test_no_space` |
| AC-MG-03e | 白名單帶入（N-03）：拋棄式主樹放 `.env`、`.dev_env_state.json` ⇒ clone 內兩者存在、雜湊相等、`.env` 為硬連結（`os.stat` 的 `st_nlink ≥ 2` 且 inode／file id 相同）；從 clone 移除白名單任一項（縫：帶入步驟跳過該項）⇒ `MERGE_VERDICT=carrier_divergence` 附該項、全套未啟動（假 pre-push 呼叫計數 0）；主樹本身沒有該檔 ⇒ 跳過並記痕跡、不判 divergence；`arch-fitness.json`、`.hypothesis/` 不被帶入 | `MG::CarrierTest::test_local_state_allowlist_carried_and_verified` |
| AC-MG-03f | 基線對照（N-03）：假 pre-push 以 sha 決定結果——主樹 HEAD 上 leg A 紅、候選上 leg A 紅 ⇒ `carrier_divergence legs=A`、主樹 HEAD 不動、產修復任務書；主樹 HEAD 綠、候選 leg A 紅 ⇒ `red`；主樹 HEAD leg A 紅、候選 leg A＋B 紅 ⇒ `red` 且只列 B；同鍵第二次合入 ⇒ 基線不重跑（假 pre-push 對主樹 HEAD sha 的呼叫計數 1）；`clone` 刪除後主樹 `.env` 內容與連結數還原 | `MG::CarrierTest::test_baseline_separates_carrier_from_agent` |
| AC-WT-01a | `.claude/settings.json` 含 `worktree.baseRef == "head"` | `HK::SettingsTest::test_worktree_baseref_head` |
| AC-WT-01b | `--base-at-dispatch` 與 merge-base 不等 ⇒ 落 `base_drift` 痕跡、仍完成 rebase | `MG::MergeTest::test_base_drift_recorded` |
| AC-WT-01c | 殘留普查：合入痕跡已 ok／noop 的代理分支或 worktree 仍存在 ⇒ 普查回非空、`sessionctl status` 顯示殘留數 | `MG::MergeTest::test_residual_agent_branches_census` |
| AC-G1-01a | `PHASE=push`、`LOCAL=<local_sha>`、`BASE=<remote_sha>`：`local_sha` 比 base 多 1 筆未結 ⇒ 阻斷 | `CR::PushRangeRatchetTest::test_push_phase_uses_local_sha` |
| AC-G1-01b | 未設 `PHASE`（提交期）淨額 > 0 ⇒ 出聲、問題清單為空 | `CR::PushRangeRatchetTest::test_commit_phase_voices_only` |
| AC-G1-01c | pre-push 逐 ref 匯出三變數（新分支 remote 全零用 merge-base 回退值；local 全零＝刪 ref ⇒ 跳過） | `CR::PushRangeRatchetTest::test_prepush_exports_per_ref` |
| AC-G1-01d | **前綴推送放行**（F-05）：工作樹與 HEAD 含尾端新未結列，stdin 的 `local_sha`＝尾端父提交 ⇒ 淨額 0、放行 | `CR::PushRangeRatchetTest::test_prefix_push_allowed_despite_worktree_tail` |
| AC-G1-01e | stdin 兩行（一行淨額 0、一行淨額 >0）⇒ 阻斷，訊息列出淨額 >0 那一 ref | `CR::PushRangeRatchetTest::test_multi_ref_stdin` |
| AC-G1-02a | 尾端提交含新未結列 ⇒ `PUSH_VERDICT=net_positive prefix=<尾端父提交>`、產修復任務書 | `PS::PushGateTest::test_prefix_push_on_net_positive` |
| AC-G1-02b | 修復提交把列轉 fixed ⇒ 整段可推 | `PS::PushGateTest::test_full_push_after_fix` |
| AC-G1-02c | 判決非 `CONTINUE`（縫：假 `sessionctl quota --json`）⇒ 不推 | `PS::PushGateTest::test_no_push_unless_continue` |
| AC-G1-02d | prefix 計算：尾端提交不是帳本提交（帳本未剝離）⇒ `prefix=none` 並產任務書，不推任何一點 | `PS::PushGateTest::test_prefix_none_when_tail_not_ledger` |
| AC-G1-03a | `CLAUDECODE=1`＋OFF ⇒ 照常判並出聲；`AUTOSDD_UNATTENDED`＋OFF 同；兩者皆無＋OFF ⇒ 依舊放行 | `CR::PushRangeRatchetTest::test_off_ignored_under_claudecode` |
| AC-G1-04a | `human_escape.honored()` 對族內每一成員三態（人＋OFF ⇒ True；`CLAUDECODE`＋OFF ⇒ False 且回出聲句；未設 ⇒ False 無句）；`AUTOSDD_SNAPSHOT_GATE_OFF` 在族內 | `CR::HumanEscapeTest::test_honored_three_states` |
| AC-G1-04b | AST：族成員名稱的直接環境讀取（`os.environ`／`env.get`／`getenv` 帶該字串）只出現在 `human_escape.py` | `CR::HumanEscapeTest::test_family_reads_only_via_predicate` |
| AC-G1-04c | `HUMAN_ONLY_ESCAPES` ⊇ {`AUTOSDD_NET_RATCHET_OFF`, `AUTOSDD_SNAPSHOT_GATE_OFF`}（只增不減） | `CR::HumanEscapeTest::test_family_only_grows` |

### 2.4 詢問類別閘與推回（`HK`／`PH`／`CP`）

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-ASK-01a | 重放 L2431 的問題（推送逃生口）⇒ rc 2，訊息含三類清單 | `HK::AskGateTest::test_l2431_blocked` |
| AC-ASK-01b | `[IRREVERSIBLE]`＋`系統：GitHub`＋`不可復原原因：push --force 覆寫遠端歷史` ⇒ 放行（含「推送」類名詞不擋，F-11 ①）；系統名非本機／專案／GitHub（例：雲端資料庫）同樣放行；放行落 `ask_allowed` | `HK::AskGateTest::test_irreversible_any_system_allowed` |
| AC-ASK-01c | `[IRREVERSIBLE]` 缺系統或原因 ⇒ 擋 | `HK::AskGateTest::test_irreversible_requires_fields` |
| AC-ASK-01d | `[COST]`＋`服務：Claude`：`billing=subscription_only` ⇒ 擋；`credits_fallback`／`api_key`／`unknown` 且 `預估：80 美元`、問題含「啟用超額使用額度」⇒ 放行；`預估：50 美元` ⇒ 擋（門檻嚴格大於） | `HK::AskGateTest::test_cost_claude_by_billing_and_threshold` |
| AC-ASK-01e | `[COST]`＋`服務：GitHub Actions`＋`預估：60 美元`、`billing=subscription_only` ⇒ 放行（非 Claude 服務不讀 billing，F-11 ②）；缺 `服務：` ⇒ 擋 | `HK::AskGateTest::test_cost_non_claude_ignores_billing` |
| AC-ASK-01f | `[K1]` 且含「須掌舵者親打」⇒ 放行；選項含「核准」⇒ 擋；缺字樣 ⇒ 擋 | `HK::AskGateTest::test_k1_hint_only` |
| AC-ASK-01g | 任一類標籤＋可代決句型（例：`[IRREVERSIBLE] 系統：本機；不可復原原因：…；要不要 park？`）⇒ 擋，且訊息為判準 4 文案（含「請改寫問句、去掉可代決的子問題」與命中的問句、**不含**「由你代決」「依最適方案決定」）；同標籤只含名詞「park」而無「要不要／是否…」句型 ⇒ 不因句型擋 | `HK::AskGateTest::test_self_decide_pattern_overrides_tag` |
| AC-ASK-01k | 正例（N-04）：`[IRREVERSIBLE] 系統：GitHub；不可復原原因：push --force 覆寫遠端歷史。是否繼續？` ⇒ 放行並落 `ask_allowed`；`[COST] 服務：GitHub Actions；預估：60 美元。是否繼續？` ⇒ 放行；`[IRREVERSIBLE] 系統：GitHub；不可復原原因：…。是否執行 force push 覆寫遠端歷史（完成後主控會 park）？`（動作詞在疑問詞 12 字元之外）⇒ 放行；控制組 `[IRREVERSIBLE] …。是否繼續跑？` ⇒ 擋 | `HK::AskGateTest::test_labeled_continue_question_allowed` |
| AC-ASK-01l | 阻斷訊息三分（N-04）：判準 2／3／4 三種訊息皆含「在得到回答之前，不得執行」；判準 2（無標籤）訊息含「若它屬於下列三類，請補上標籤」，且「代決」只出現在「不屬於就」之後的子句；判準 3 訊息指出缺哪一欄；判準 3／4 訊息不含「由你代決」「依最適方案決定」（整題授權語） | `HK::AskGateTest::test_block_messages_never_delegate_irreversible` |
| AC-ASK-01h | 舊類別標籤 `[BIZ]`／`[SECRET]`／`[VISUAL]`／`[HARNESS]`、無標籤 ⇒ 擋 | `HK::AskGateTest::test_retired_tags_blocked` |
| AC-ASK-01i | `AUTOSDD_UNATTENDED` ⇒ 任何問題擋（含三類必填齊全者） | `HK::AskGateTest::test_unattended_blocks_all` |
| AC-ASK-01j | 動作詞表只增不減（後設鎖：`SELF_DECIDE_VERBS` ⊇ APD §7 v1.2 列舉的 13 個複合動作詞）；單詞「繼續」不在表內（反向鎖，N-04）；名詞詞表不存在（v1.0 的「推送」「合入」「rebase」「cherry-pick」「額度」「裁決」不在任何阻斷常數中） | `HK::AskGateTest::test_verbs_only_grow_and_no_noun_lexicon` |
| AC-ASK-02a | 推回文案先叫代決、列三類；不含「請您」「請手動」 | `PH::AutopilotWordingTest::test_pushback_prefers_self_decide` |
| AC-ASK-02b | 「真正需要您決定的類別」「以後要請您決定的只有這兩類」（逐字取自 sid 406454ea 2026-11-25）⇒ 不判交棒 | `PH::AutopilotWordingTest::test_rule_description_not_handoff` |
| AC-ASK-02c | 控制組：「需要您決定要不要推送」仍判交棒（判準未被放寬到失去鑑別力） | `PH::AutopilotWordingTest::test_real_handoff_still_caught` |
| AC-ASK-02d | 「先前 L2424 被分類器擋下」不當本場宣稱；「本回合 pre-push 擋下 3 項」仍判 | `CP::PastEventTest::test_past_event_not_claim` |

### 2.5 CI、舊視窗、圍籬

| AC | 判準 | AT 座標 |
|---|---|---|
| AC-CI-01a | 三支真 run（45427135743、45439253352、45456241389）attempt 1 jobs JSON 錄製夾具 ⇒ `queue_timeout`；有步驟的 cancelled、14 分取消、16.5 分取消、同 ref 有較新 run ⇒ 不命中 | `CW::QueueTimeoutTest::test_classify_recorded_attempts` |
| AC-CI-01b | 命中 ⇒ 呼叫 `gh run rerun <id> --failed`（縫 `run`）、末行 `pass rerun=queue_timeout×1`；第 3 次 ⇒ `fail reason=queue_timeout_exhausted` rc 1 | `CW::QueueTimeoutTest::test_rerun_and_exhaustion` |
| AC-OW-01a | APD §8 字樣鎖射程內全部使用者可見字串不含「請手動」「請您」「手動跑」「請人」；例外清單逐筆「檔:函式＋WHY」，清單外命中即紅；例外清單本身每項都必須仍有命中（過期例外即紅） | `OW::AutopilotTest::test_no_manual_wording_across_message_homes` |
| AC-OW-01b | not_idle ⇒ 退避間隔 60·2^k、總時長到 12 小時才 `oldwin_retry_exhausted`；`MAX_RETRIES` 常數不存在 | `OW::AutopilotTest::test_exponential_backoff_12h` |
| AC-OW-01c | 舊視窗 Stop（已交棒且已 ack）⇒ `oldwin_idle_hint`＋60 秒後排程一次；未 ack ⇒ 不排 | `OW::AutopilotTest::test_old_stop_triggers_check` |
| AC-OW-01d | `status=shell` 長時間不變 ⇒ 不終止 | `OW::AutopilotTest::test_shell_never_killed` |
| AC-FN-01a | 圍籬期間真痕跡目錄（tmp 模擬）新增一列帶 `%TEMP%`／`sc-*`／夾具 sid ⇒ 判洩漏；真系統同時段寫入的非夾具形列 ⇒ 不判 | runner 既有測試檔（WP-FENCE 現查）`::TraceFenceTest` |
| AC-FN-01b | runner 抽出為純搬移：`min_tests_note_stale_tokens` 自 `min_tests_margin`（或備援家）import 的結果與搬移前逐字相同；runner raw 行數 ≤ 新 SPECIAL 門檻 | `::TraceFenceTest::test_extraction_is_pure_move`＋AC-QV-08a 同鎖 |

## 3. 突變清單（MU；QA 逐條實打，每條至少一條 AT 轉紅，未轉紅＝補斷言）

| MU | 突變 | 應轉紅 |
|---|---|---|
| MU-QV-1 | 決策表第 3 列拿掉 `D ≤ QV_WAIT_RESET_MIN` 分支（一律 PARK） | AC-QV-01a |
| MU-QV-2 | 恢復兩序列鍵（raw 與 plan 各自觸發） | AC-QV-05a、AC-QV-01c |
| MU-QV-3 | `expires_at` 只取 `measured_at+TTL`（不取短窗 reset 的 min） | AC-QV-02a |
| MU-QV-4 | 恢復 halt 有效即不補量 | AC-QV-03a |
| MU-QV-5 | park 恢復接受 `--why` | AC-QV-04a |
| MU-QV-6 | 量不到改回 `NODISPATCH`（cap 0）或改回不設限 `CONTINUE`（cap None） | AC-QV-07a、AC-QV-03b |
| MU-QV-7 | Stop 宣稱守衛不看 `expires_at` | AC-QV-06b |
| MU-QV-8 | 第 2 列與第 3 列對調（短窗優先於週軸） | AC-QV-01b |
| MU-QV-9 | 拿掉第 4 列（`stage=nodispatch` 落 CONTINUE） | AC-QV-01b |
| MU-QV-10 | 第 5 列比較改 `>`、或拿掉第 5 列 | AC-QV-01b、AC-QV-04b |
| MU-QV-11 | 短窗 reset 量不到時回 `PARK` | AC-QV-01b、AC-QV-04c |
| MU-QV-12 | 拿掉 spend 列（第 1 列） | AC-QV-01b |
| MU-QV-13 | 第 2 列看全部模型分軌軸（不看 `model`） | AC-QV-01e |
| MU-QV-14 | 動作改讀 `decision.band`（墊高帶影響動作） | AC-QV-01f |
| MU-QV-15 | `cap` 改用 `quota_policy.decide().cap`（不經 `dispatch_decision`） | AC-QV-01g |
| MU-QV-16 | 消費端拿舊 vid 行動（跳過過期檢查） | AC-QV-02c |
| MU-QV-17 | 不可用狀態 `expires_at＝measured_at＋TTL` | AC-QV-02d |
| MU-QV-18 | `next_est` 不取缺省下界 | AC-QV-04d |
| MU-QV-19 | SI 跳過判準忽略 `deg=unmeasured` | AC-QV-09a |
| MU-QV-20 | SI 子行程失敗改為不跳過 | AC-QV-09a |
| MU-QV-21 | 白名單 `RULING_INPUT_SITES` 多加一個實際新增的私有站點（鎖被放寬成包含式比對） | AC-QV-10b |
| MU-QV-22 | `wake_target` 對 `ruling_wait_reset` 套 `small_ctx` 限制 | AC-QV-11a |
| MU-QV-23 | `ruling_wait_reset` 計入保溫帳 n* | AC-QV-11b |
| MU-QV-24 | 哨兵只對 `HALT_WEEKLY｜PARK` 維持等待（不含無人窗口的 `WAIT_RESET`） | AC-QV-11c |
| MU-QV-25 | 宣稱守衛不考慮 AskUserQuestion 結果之前的判決 | AC-QV-06d |
| MU-QV-26 | 判決 cap 改回 `min(decision.cap, getattr(plan, "cap", …))`，或 `decision.cap is None` 時改取 0／保溫次數 `plan.k`（N-06） | AC-QV-01g |
| MU-QV-27 | `switchplan._wall` 恢復 `short_pct ≥ prepare_pct` 或 `stage∈{close,wall}` 判準（不看判決） | AC-QV-12a、AC-QV-12b |
| MU-QV-28 | `switchplan` 把 `WAIT_RESET` 對映成 `PARK_UNTIL` | AC-QV-12a |
| MU-QV-29 | `parkprobe.evaluate` 恢復 `cur < prepare_pct` 為唯一准許條件（不看判決） | AC-QV-13a |
| MU-QV-30 | 拿掉 `cur ≤ parked_pct − EARLY_DROP_PP` 遲滯閘，或 `deg=unmeasured` 也准 fire | AC-QV-13b |
| MU-QV-31 | 鎖的呼叫樣式拿掉 `pace_state`／`_pace_state`／`settled_quota`／`default_read`（回到 v1.1 只收直接原語） | AC-QV-10d |
| MU-QV-32 | 拿掉 (ii) 門檻比較站點的收集 | AC-QV-10e |
| MU-QV-33 | 白名單 `diag` 類放寬成「任何 C 站點」 | AC-QV-10f |
| MU-QV-34 | 保溫閘判決分支恢復 `small_ctx`／`no_usage` 豁免 | AC-QV-11e |
| MU-QV-35 | 判決分支套 `pings ≥ n*` 不推 | AC-QV-11e |
| MU-QV-36 | 判決分支把任何 running 背景任務視為載具（只要有 running 就不推） | AC-QV-11e |
| MU-QV-37 | 判決分支拿掉前四項豁免 | AC-QV-11f |
| MU-AC-1 | reconcile 不比對 `account`（只看存在） | AC-AC-02a |
| MU-AC-2 | 舊格式標記一律保留 | AC-AC-02b |
| MU-AC-3 | 逐字稿觸發器不記 byte offset（每次全讀） | AC-AC-03b |
| MU-AC-4 | 觸發器成立即作廢（不等補量指紋；R-4.1.7-3 核心安全判準） | AC-AC-03d |
| MU-AC-5 | 補量失敗時作廢 | AC-AC-03d |
| MU-MG-1 | 略過已吸收改成不比 patch-id | AC-MG-01b |
| MU-MG-2 | 紅時仍 ff | AC-MG-01c |
| MU-MG-3 | 清理加 `--force` | AC-MG-01e |
| MU-MG-4 | 帳本不剝離到尾端 | AC-MG-01d |
| MU-MG-5 | 載具改回 `git worktree add` | AC-MG-01h |
| MU-MG-6 | 拿掉 `PYTHONPATH` 注入 | AC-MG-03b（全套變綠＝測到主樹） |
| MU-MG-7 | 拿掉執行期自證 | AC-MG-03a |
| MU-MG-8 | 清理以遞迴刪除處理 `.venv` 連結 | AC-MG-03c |
| MU-MG-9 | 帶入後不驗白名單項存在與雜湊 | AC-MG-03e |
| MU-MG-10 | 拿掉基線對照（候選紅一律 `red`） | AC-MG-03f |
| MU-MG-11 | 基線紅時一律 `carrier_divergence`（不比 leg 集合，代理新增的紅被吸收） | AC-MG-03f |
| MU-MG-12 | `.env` 改為複製內容（不是硬連結） | AC-MG-03e |
| MU-WT-1 | 不比對 `--base-at-dispatch`（不記 `base_drift`） | AC-WT-01b |
| MU-WT-2 | 殘留普查只看 worktree、不看分支 | AC-WT-01c |
| MU-G1-1 | 推送期比較對象改回工作樹或 `HEAD` | AC-G1-01a、AC-G1-01d |
| MU-G1-2 | 提交期恢復阻斷 | AC-G1-01b |
| MU-G1-3 | 拿掉 `CLAUDECODE` 判斷 | AC-G1-03a、AC-G1-04a |
| MU-G1-4 | pre-push 只對 stdin 第一行呼叫棘輪 | AC-G1-01e |
| MU-G1-5 | prefix 一律取 HEAD 的父提交（不驗尾端是帳本提交） | AC-G1-02d |
| MU-G1-6 | `ledger_closing_guards` 改回直接讀 `os.environ` 的 OFF | AC-G1-04b |
| MU-ASK-1 | 可代決句型檢查移到標籤檢查之後且標籤命中即放行 | AC-ASK-01g |
| MU-ASK-2 | `[COST]` 對 Claude 服務不讀 `billing` | AC-ASK-01d |
| MU-ASK-3 | 恢復舊五類標籤 | AC-ASK-01h |
| MU-ASK-4 | 推回判準拿掉「類別定義語」豁免 | AC-ASK-02b |
| MU-ASK-5 | 豁免放寬到「所有含『您』的句子」 | AC-ASK-02c |
| MU-ASK-6 | 恢復 v1.0 名詞詞表優先阻斷 | AC-ASK-01b、AC-ASK-01d、AC-ASK-01j |
| MU-ASK-7 | 無人窗口分支拿掉 | AC-ASK-01i |
| MU-ASK-8 | `[IRREVERSIBLE]` 必填欄位檢查拿掉 | AC-ASK-01c |
| MU-ASK-9 | `[COST]` 門檻 `>` 改 `≥`，或拿掉門檻 | AC-ASK-01d |
| MU-ASK-10 | `[K1]` 不檢查「核准」選項 | AC-ASK-01f |
| MU-ASK-11 | `[COST]` 非 Claude 服務也套 `billing` | AC-ASK-01e |
| MU-ASK-12 | `SELF_DECIDE_VERBS` 加回單詞「繼續」 | AC-ASK-01k、AC-ASK-01j |
| MU-ASK-13 | 判準 4 的阻斷訊息改回「這類決定由你代決」 | AC-ASK-01g、AC-ASK-01l |
| MU-ASK-14 | 拿掉「疑問詞之後 12 字元內」距離限制（整句任一處有動作詞即命中） | AC-ASK-01k |
| MU-CI-1 | 不檢查 `runner_name==""` | AC-CI-01a |
| MU-CI-2 | 重跑上限拿掉 | AC-CI-01b |
| MU-CI-3 | 時間窗改為 `≥ 14 分`（拿掉上界）或 `≥ 15 分`（收緊下界） | AC-CI-01a（14 分、16.5 分兩例） |
| MU-OW-1 | 退避改回固定 3 次 | AC-OW-01b |
| MU-OW-2 | 舊視窗 Stop 不檢查 ack 即排程 | AC-OW-01c |
| MU-OW-3 | 字樣鎖射程縮回三支檔 | AC-OW-01a |
| MU-FN-1 | 圍籬比對只看檔案大小不看列內容 | AC-FN-01a |

## 4. E2E 覆蓋表（一功能一列，不得遺漏；全部入帳 `docs/06_quality/RealVerify_Result_Ledger.md` 才算結）

| 功能 | E2E | 載具（真的是什麼） | realverify 案例 | 不可達部分與備援 |
|---|---|---|---|---|
| 單一判決（QV-01） | E2E-AP-QV-01 | 載具 E＋時間平移重放：以 sid 406454ea 03:46 的真實讀數（87%）與 halt 標記原檔（舊帳號 `34cd3507237f`）組沙盒；替身回 `eaf5241f6fe2` 標頭；真 `python tools/sessionctl.py quota` 於「reset＝now＋14 分」與「reset 已過、0%」兩個平移時刻真跑 | `RV-AP-QV01` | 無；斷言前者 `WAIT_RESET`、後者 `CONTINUE acct=eaf5241f6fe2`、兩者皆無 halted 行 |
| 判決行與有效期（QV-02） | E2E-AP-QV-02 | 載具 E：真 `sessionctl watch` 背景行程得判決 → 替身換讀數 → 真等超過 `expires_at`（`runlong`／`waitfor`）→ 真 `park` | `RV-AP-QV02` | 無；斷言 park 依新判決、痕跡 `stale_verdict_recomputed` |
| halt 不壓補量（QV-03） | E2E-AP-QV-03 | 載具 E：沙盒放有效 halt 標記，真 `python tools/session_resume_planner.py --pace` 兩次（相隔 > TTL，真等），替身計數 GET 次數 | `RV-AP-QV03` | 無；斷言 GET＝2、首行為判決行 |
| park 前置（QV-04） | E2E-AP-QV-04 | 真排程（沙盒命名空間、R-VER 隔離）：A＝`CONTINUE` 不產排程；B＝`--next-est` 放不下 ⇒ `AutoSDD_HandoffSpawn_*` 且 NextRunTime 非空；C＝短窗 reset 量不到 ⇒ 判 `NODISPATCH`、park rc 4 且訊息不含 `--why`；D（v1.2，N-01 ①）＝沙盒 park 標記（`parked_pct=92`）＋錄製讀數 80%、`stage=close`，真跑 `python tools/session_resume_planner.py --sentinel-tick`（沙盒任務書）⇒ 痕跡 `park_early_probe action=PARK`、無 `park --fire` 子行程（`fire_early` 的子行程 argv 以 R-VER 替身攔截計數）；換成 0% 讀數 ⇒ 恰一次；收尾撤銷 | `RV-AP-QV04` | macOS 走 launchd，憑證是 rc（既有 park 劃界） |
| watch 單序列（QV-05） | E2E-AP-QV-05 | 真 `sessionctl watch` 背景行程＋載具 E（87%→0% 跨平移後的重置點） | `RV-AP-QV05` | 無；斷言只觸發一次 `WAIT_RESET`、重置後不再觸發；同一回合 `switch_plan` 痕跡（`switchplan.trace_plan`）無 `PARK_UNTIL`／`PARK_POLL`（v1.2，N-01 ②） |
| Stop 宣稱守衛（QV-06） | E2E-AP-QV-06 | 載具 H：真 Stop hook（`check_claim_provenance.py`）以逐字稿 406454ea 重放；另以近 14 天真實逐字稿全量重放（同 `tools/probe/handoff_census.py` 母體）記 QV 詞族新增命中數，人工抽核 | `RV-AP-QV06` | 斷言 L2564 回合出聲一次；全量重放的新增命中經人工抽核判為假紅者 ≤ 2（超過即改詞表重跑，F-16）；子代理面：SubagentStop 未註冊（無暴露證據不擴守衛面），以判準函式吃真實子代理逐字稿重放代替並登記〈理論洞清單〉 |
| 失效方向與 billing（QV-07） | E2E-AP-QV-07 | 真 `sessionctl quota --json` 於三種錄製快取（缺 posture、無 credits、credits 可用）＋載具 E 回 429（帶 retry-after） | `RV-AP-QV07` | 無；斷言 429 時 `CONTINUE deg=unmeasured`、`1 ≤ cap ≤ cap_prepare`、`expires_at > now` |
| LOC 純搬移（QV-08） | E2E-AP-QV-08 | 真 pre-push（合成 stdin）於搬移 commit 與前一 commit 各跑一次，leg 結果相同 | `RV-AP-QV08` | 無 |
| SI 改讀判決（QV-09） | E2E-AP-QV-09 | 沙盒 repo 副本＋載具 E：真跑 SelfImproving 排程巡邏入口（`tools/selfimproving.py` 的巡邏動詞；實作棒現查乾跑旗標，無則於沙盒副本真跑），三種錄製讀數（free、87% 近重置、量不到）各一次 | `RV-AP-QV09` | 無；斷言三次的 `research.skip`／不跳過與判決動作一致、量不到必跳過 |
| 單一家鎖（QV-10） | E2E-AP-QV-10 | 沙盒 git repo 副本植入一個私有判讀站點，真跑 `python -m unittest discover -s tools/tests -p test_sessionctl_qv.py`（子行程） | `RV-AP-QV10` | 無；斷言 rc≠0 且訊息列出該站點；移除後 rc 0 |
| WAIT_RESET 叫醒（QV-11） | E2E-AP-QV-11 | 互動面：載具 E 讀數 87%、reset＝now＋3 分（平移），合成小上下文逐字稿，真 `sessionctl keepwarm` 背景行程 ⇒ 在 `win＋skew` ± 30 秒內結束並印叫醒末行；無人面：同讀數於 `AUTOSDD_UNATTENDED` 下真跑哨兵武裝（沙盒排程命名空間）⇒ NextRunTime≈`win＋skew`；Stop 段（v1.2，N-05）：載具 H，以同一沙盒（小上下文逐字稿、判決 `WAIT_RESET`、`background_tasks` 空）真跑 Stop hook（`sessionctl_guard.py` 經載具）⇒ `decision:block` 且理由含 `keepwarm --sid`；第二次（`stop_hook_active`）⇒ 放行 | `RV-AP-QV11` | macOS 排程憑證是 rc（既有劃界） |
| 標記帶帳號（AC-01） | E2E-AP-AC-01 | 載具 H＋E：真 PostToolUse hook（`context_budget_guard.py`）以錄製讀數 ≥ halt 觸發 halt 寫入，讀真寫出的沙盒標記檔驗 `account` | `RV-AP-AC01` | 無 |
| 換帳號作廢（AC-02） | E2E-AP-AC-02 | 載具 H＋E：沙盒 HOME 內換一份憑證檔（真 mtime 變化），替身改回第二帳號標頭；真 PostToolUse hook 下一次呼叫後落 `account_switch`、halt 作廢、真 `--pace` 首行為判決行 | `RV-AP-AC02` | 不切換真帳號（不可、也不該）；以真憑證檔變化＋錄製標頭取代 |
| `/login` 觸發（AC-03） | E2E-AP-AC-03 | 載具 H：逐字稿 406454ea L173～L210 重放，真 hook 讀增量 | `RV-AP-AC03` | 無；斷言 L210 時刻判決為新帳號。**本列是 AC 家族結案主證** |
| 被動觀測（AC-04） | E2E-AP-AC-04 | 觀測型：每次 SessionStart 掃痕跡與逐字稿 `/login` 記錄配對 | `RV-AP-AC04-OBS` | **不擋結案**（F-20）：觀測期 30 天；樣本 0 照實記「未觀測」；有樣本且不配對＝再開症狀 |
| 合入管線（MG-01） | E2E-AP-MG-01 | 真 git：repo 外拋棄式 clone 重建 W6／W11b2 兩分支（含已吸收提交與三提交帳本），真跑 `autopilot merge` | `RV-AP-MG01` | 全套以真 pre-push 的縮小 leg（拋棄式 repo 內只含 MG 測試）代表；完整 leg 對等由 E2E-AP-MG-02、完整載具由 E2E-AP-MG-03 證 |
| pre-push 對等（MG-02） | E2E-AP-MG-02 | 真 pre-push：合成 stdin 一次、對拋棄式 bare remote 真 `git push` 一次，比 leg 集合 | `RV-AP-MG02` | 無 |
| 合入載具（MG-03） | E2E-AP-MG-03 | 真 `autopilot merge` 對本 repo 的真 local clone：clone 內三子樹各植一突變 ⇒ 真全套紅（三 leg 各紅）；再跑一次不植 ⇒ 綠；收尾驗主樹 `.venv` 完好、連結已刪；基線段（v1.2，N-03）：同一 clone 先以主樹 HEAD 跑基線並入 `baseline.jsonl`，第二次合入同鍵 ⇒ 基線不重跑；真 clone 內白名單項存在、雜湊等於主樹、`.env` 為硬連結；收尾後主樹 `.env` 連結數還原。缺項分支（帶入失敗 ⇒ `carrier_divergence`）不在 E2E 注入：要讓真帶入失敗只能改真主樹或跨卷，前者違反 ADR-018 D3「測試一律不改真主樹」，後者不保證每台機器可得；由 AC-MG-03e 的縫承接並照實劃界 | `RV-AP-MG03` | Windows 全額佔碟：開跑前查空間；不足 ⇒ 案例記 `no_space` 並以 macOS（clonefile）機器補跑，未補跑前不算結 |
| worktree 起點（WT-01） | E2E-AP-WT-01 | 載具 C：真 `claude -p` 於拋棄式 repo（含一個未推送提交、`worktree.baseRef: "head"`）派 `isolation: "worktree"` 子代理執行 `git rev-parse HEAD`，斷言含該未推送提交；收尾以 `autopilot merge --dry-run` 的殘留普查驗回收 | `RV-AP-WT01` | 無 |
| 推送範圍棘輪（G1-01） | E2E-AP-G1-01 | 拋棄式 bare remote＋真 `git push` 觸發真 pre-push：整段推（擋）與前綴推（放行）各一次，工作樹含尾端新列 | `RV-AP-G101` | 無 |
| 推送閘與前綴推送（G1-02） | E2E-AP-G1-02 | 重建 HYG1 形狀（修 2＋登記 1）三提交，真 `autopilot push` 對 bare remote | `RV-AP-G102` | 無 |
| 逃生口對稱（G1-03） | E2E-AP-G1-03 | 載具 C：真 `claude -p` 讓模型在拋棄式 repo 以 Bash／PowerShell 設 OFF 提交 ⇒ 棘輪照判並出聲；同指令在無 `CLAUDECODE` 的乾淨行程 ⇒ 放行 | `RV-AP-G103` | 無 |
| 逃生口族（G1-04） | E2E-AP-G1-04 | 同 G1-03 的 `claude -p` 回合內，模型另以真子行程呼叫 `human_escape.honored("AUTOSDD_SNAPSHOT_GATE_OFF", os.environ)`（環境由 harness 注入，非測試設定）⇒ 印 False 與出聲句 | `RV-AP-G104` | 快照閘本身尚未實作：其 E2E 由 SelfImproving 帳本 DB 案實作階段補（§5 OI 需求）；本列只證述詞在真 harness 環境下的判定 |
| 詢問類別閘（ASK-01） | E2E-AP-ASK-01 | 主載具 H：真 PreToolUse hook（真 `sessionctl_guard.py` 經載具）以近 14 天 15 次真實提問的 payload 重放＋三類各一筆合成正例（含 force-push「是否繼續？」題〔v1.2，N-04〕、Claude 超額題）；輔載具 C：第一動作以 `claude-code-guide` 查 print 模式能否呼叫 AskUserQuestion，可 ⇒ 一筆真 `claude -p` 回合讓模型真呼叫（可代決題）⇒ 被擋 | `RV-AP-ASK01` | print 模式不可呼叫 ⇒ 輔載具該筆改「錄製的真互動 PreToolUse payload 重放」並照實記錄（F-23）；互動畫面顯示 block 理由不可程式目視（同既有〔OI-20261120-010〕劃界） |
| 推回與宣稱守衛假紅（ASK-02） | E2E-AP-ASK-02 | 載具 H：真 Stop hook 以 sid 406454ea 2026-11-25 兩次假推回回合重放 ⇒ 不推回；以近 14 天真實逐字稿全量重放（`tools/probe/handoff_census.py --midwork` 同母體）比較修前修後命中數，新增假紅 0 | `RV-AP-ASK02` | 無 |
| CI 排隊逾時（CI-01） | E2E-AP-CI-01 | `gh api` 錄製三支 run attempt 1／2 回應重放＋真 `ci_wait` 行程；另於下一次真推送被動觀測 | `RV-AP-CI01`、`RV-AP-CI01-OBS` | 外部現象可能消失：被動觀測 0 命中照實記錄（不算 FAIL、不算 PASS），錄製重放為主證 |
| 舊視窗（OW-01） | E2E-AP-OW-01 | 真行程替身（R-VER 替身）＋真排程重試鏈：替身維持 `status=shell` 2 次後轉閒置 ⇒ 第 3 次退避後關閉；全程痕跡無禁字 | `RV-AP-OW01` | 兩個真互動視窗不可自動化（harness UI）⇒ 以替身＋真排程驗到關閉動作前一刻；互動層列 APD §2 外部劃界 |
| 痕跡圍籬（FN-01） | E2E-AP-FN-01 | 真跑 `run_root_unittests.py`，搭一支故意洩漏的探針測試（紅綠自證：有探針 rc≠0、拿掉 rc 0） | `RV-AP-FN01` | 無 |

覆蓋檢查：§1 每個 REQ 在本表恰有至少一列（QV-01～11、AC-01～04、MG-01～03、WT-01、G1-01～04、ASK-01～02、CI-01、OW-01、FN-01，共 28 列）；不可達者皆有備援與劃界。

## 5. 跨檔鎖、收尾（CLOSE）與需主控登記的 OI

- 新測試檔三支（QV、MG、PS）⇒ c1c2 重釘、`_TREE_FILE_FLOORS`、skip 普查、`MIN_TESTS`＋ONBOARDING 同步，由 CLOSE 一次做（並行包只回報建議值）。
- CI paths：compat-ci 兩支加 `tools/lib/autopilot/**`、`tools/autopilot.py`、`tools/lib/model_window_table.py`、`tools/lib/quota_ruling.py`、`tools/lib/human_escape.py`、`tools/lib/suite_fence.py`；`non_evolvable_globs` 加 `tools/lib/autopilot/**`、`tools/autopilot.py`、`tools/lib/quota_ruling.py`、`tools/lib/human_escape.py`。
- SSOT §3：「autopilot＋QuotaVerdict」預告列改反引號登記（檔案存在後）。
- 根 CLAUDE.md、記憶檔、被取代條文與測試：依 APD §12 CLOSE 列、§16 與 QVD §6 對照表逐項，同 commit 收齊。
- 本 TCS 的 realverify 案例 id 登記於 `docs/06_quality/RealVerify_Protocol/cases.json`。
- **需主控以 `python tools/openitems.py open` 登記的 OI**（本棒不自行開 OI；凍結時一併登記，id 回填 PRD §16.6 兩列與本節）：
  1. 快照閘（SelfImproving 帳本 DB 案 AC-LD-12-3）實作時必須經 `human_escape.honored()`，並在 `docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-*` 補一條 AT（`CLAUDECODE`＋`AUTOSDD_SNAPSHOT_GATE_OFF` ⇒ 照常擋並出聲）與一條 E2E。
  2. 既有「畫面目視」類 OI 依 APD §16 轉載具或改劃界（逐筆處置）。
  3. PRD §16.6 2026-11-25 兩列原寫「〔OI〕」佔位的實作與 E2E 項（第一列實作 2＋E2E 15、第二列實作 1＋E2E 3；見 PRD 【v2.1.29 勘誤】）。

## 6. v1.0 → v1.1 處置索引（QA-S 發現）

| 發現 | 本檔落點 |
|---|---|
| F-01 | REQ-AP-QV-01、QV-10；AC-QV-01g、AC-QV-02b、AC-QV-10a～c；MU-QV-15、21；E2E-AP-QV-10 |
| F-02 | REQ-AP-QV-07；AC-QV-03b、AC-QV-07a；MU-QV-6；E2E-AP-QV-07 |
| F-03 | REQ-AP-QV-11；AC-QV-11a～d；MU-QV-22～24；E2E-AP-QV-11 |
| F-04 | REQ-AP-MG-03；AC-MG-01h、AC-MG-03a～d；MU-MG-5～8；E2E-AP-MG-03 |
| F-05 | REQ-AP-G1-01；AC-G1-01a、01c～01e；MU-G1-1、4；E2E-AP-G1-01 |
| F-06 | AC-QV-01e；MU-QV-13 |
| F-07 | AC-QV-01b、AC-QV-04c；MU-QV-11；E2E-AP-QV-04 C 段 |
| F-08 | AC-QV-01b（spend）、AC-QV-01f；MU-QV-12、14 |
| F-11 | AC-ASK-01b、01d、01e、01g、01j；MU-ASK-6、11 |
| F-13 | §3 新增 MU-QV-8～25、MU-AC-4～5、MU-MG-5～8、MU-WT-1～2、MU-G1-4～6、MU-ASK-6～11、MU-CI-3、MU-OW-2～3 |
| F-14 | 檔頭〈E2E 載具〉、§4 每列載具欄 |
| F-15 | REQ-AP-OW-01、AC-OW-01a；MU-OW-3 |
| F-16 | E2E-AP-QV-06 |
| F-17 | AC-QV-01d |
| F-18 | AC-QV-06c、AC-QV-06d、AC-AC-04c |
| F-19 | AC-QV-02d；MU-QV-17 |
| F-20 | E2E-AP-AC-04 |
| F-23 | E2E-AP-ASK-01 |
| F-25 | AC-QV-04d；MU-QV-18 |
| 代決 ① | REQ-AP-QV-09；AC-QV-09a～c；MU-QV-19～20；E2E-AP-QV-09 |
| 代決 ② | REQ-AP-G1-04；AC-G1-04a～c；MU-G1-6；E2E-AP-G1-04；§5 OI 需求 1 |

## 7. v1.1 → v1.2 處置索引（QA 複審 `qa_spec2_report.md` 發現 N-01～N-10；SD-2）

| 發現 | 本檔落點 |
|---|---|
| N-01 普查漏 parkearly／parkprobe 與 switchplan | REQ-AP-QV-01；AC-QV-12a～b、AC-QV-13a～b；MU-QV-27～30；E2E-AP-QV-04 D 段、E2E-AP-QV-05 斷言補 |
| N-02 鎖看不見包裝入口與門檻比較 | AC-QV-10d、AC-QV-10e；MU-QV-31、32 |
| N-07 `draining()` 誤列 B1 | QVD §3.5.2 B6（劃界文字；無 AT：不改接） |
| N-09 白名單定義 | AC-QV-10f；MU-QV-33 |
| N-10 `park --done` 上限 | QVD §3.5.2 B7（劃界文字；由 AC-QV-10f 的白名單形狀覆蓋） |
| N-05 WAIT_RESET 掛載推動者 | REQ-AP-QV-11；AC-QV-11e～f；MU-QV-34～37；E2E-AP-QV-11 Stop 段 |
| N-03 clone 缺主樹機器本地狀態 | REQ-AP-MG-03；AC-MG-03e～f；MU-MG-9～12；E2E-AP-MG-03 基線段 |
| N-04 詢問閘擋掉必填齊全的「是否繼續」且叫模型代決 | REQ-AP-ASK-01；AC-ASK-01g 改寫、AC-ASK-01j 改寫、AC-ASK-01k～l；MU-ASK-12～14；E2E-AP-ASK-01 合成正例補 `是否繼續` 題 |
| N-06 `plan.cap` 不存在 | AC-QV-01g 改寫；MU-QV-26 |
