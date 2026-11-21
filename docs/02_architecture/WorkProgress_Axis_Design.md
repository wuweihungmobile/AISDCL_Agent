# 工作推進軸（Work Progress Axis）設計稿——未結項登記簿、完成閘、叫醒預算、名冊收斂、AutoClaude 無人舵手

> 角色：SD 系統設計（R217，AISDLC 第 2 階段）。日期 2026-11-19，量測基準 HEAD＝`f1e8d50c`。
> 修訂 r2（2026-11-19，回應規格獨立審查 FAIL：P2×6＋P3×8）：修憲改追加註記（附錄 A-1／A-10）、driven 有效性改以 `drive.at`＋`start` 事件對帳（§3.3）、stale-pass 防永動與觸發事件（§8-4）、驅動器全域互斥／每窗上限／錯開／`--pace`（§5.4）、完成閘零子行程與延遲預算（§4.5）、驅動器自有寫入面（§5.5）、procStart 比對法（§7 DEF-02）、watch 保溫模式退出條件（§6.3）、PG 說法統一（§9.3）、§11.1／§11.8／V-K2 定義 due（§8-5）、A-10 ✅ 條件機械化、A6／A7 持有面重切（§11）。
> 修訂 r3（2026-11-19，回應規格獨立審查第二次退件：P2×3＋P3×6，加上掌舵者兩則新指令）：①有 `attempt` 之後的空窗改判 undriven（§3.3）；②`window_cap`／`quota` 不計入 deferrals，改為先進先出（§3.3、§5.4）；③同 sid 雙視窗（park 既有缺陷）與「新 session 接手後有條件自動關閉舊視窗」（掌舵者 2026-11-19 互動選項「有條件自動關 (Recommended)」）合為 §7.1；④掌舵者結案判準（scratchpad `r217_acceptance_rule.md`）落成 §15「PRD 全功能 E2E 對照表」與 R217 結案判準；⑤§11.1／§11.8／V-K2 改成由驅動器真的跑完的案例（§8-5）；P3：§4.1-4 佐證共用、§6.1 退出事件、§11 A3／A6 並行對稱、§12 動詞表、A-10 追加註記的 WHY、沙盒排程前綴。
> 修訂 r4（2026-11-19，回應規格獨立審查第三次退件：P2×4＋P3×7）：①A01～A46（另含 B01～B03）逐列寫出載具與斷言骨架，落在 TCS §10.3 附錄；空殼案例由執行器與 CI 鎖雙重擋下（§15.5，D-15）；②帳列改記「實際執行的案例 id」，long／soak 強制宣告 `MIN_WALL_SECONDS` 並與 OIR `start`／`attempt` 對帳（§15.4，D-16）；③沙盒圍籬改成快照比對、不寫死任何 sid（§7.1 第 5 點）；④舊窗收到 `留：` 即永久否決該交接包的自動關閉（§7.1〈否決〉，D-17）；P3：TOCTOU 重驗與未送出輸入的取捨、條件 ② 納入非保溫背景 shell、只關 `entrypoint=cli`、park FIRE_SPAWN 路與重試次數統一為 3、`AutoSDD_OldWinClose_*` 進 status 與殘留回收、對照表由誰重產（§15.4，D-18）、登記檔 `status` 缺欄或不認得即不關。
> 🔒 **spec-frozen（2026-11-19；approver＝掌舵者（常態規則 2026-10-20，sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13；主控執行））**：依據＝SCG 獨立審查第四次（Opus，唯讀）判前次 11 條全數處置、附錄抽查 14 列 13 列 OK，唯一 P2＝TCS 附錄 A33 斷言量不到付費探針；主控依審查建議逐字改寫該列（載具改 P＋E＋X、互動路徑、shim 恰 1 次＋牆鐘 90～95 s）、補 A41 痕跡複製斷言（審查 P3-4），並代決載具 E 不成立時三格 429 改列內分支例外（TCS §10.3 後段）；主控親驗 `r217_r3_refcheck.py` 輸出 REQ 95／AT 92／E2E 64／MU 34、重號 0、未定義引用 0、TODO 0、REQ 無 E2E 0。凍結時已知、交實作期處理的 P3：證據值只驗非空、TOCTOU 重驗未重查背景子代理、REQ-WP-101／102 無 MU、A43／A33 恆成立鍵鑑別力弱（實作 SCG-4 審查兜底）。
> 輸入：Architect 報告（下稱 **ARC**，scratchpad `r217_architect_report.md`）、SA 報告（下稱 **SA**，scratchpad `r217_sa_report.md`）、共同全貌（scratchpad `r217_review_common.md`）。三檔皆在 sid 31ea79d4 的 scratchpad，收尾窗口會把關鍵段落抄進證據檔。
> 上游：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 **PRD**；行號以 2026-11-19 HEAD 為準，全文 2,982 行）。修憲只走 §16.5 (i)，草案在附錄 A，PRD 本體由實作期收尾窗口改。
> 驗收規格：`docs/03_testing/contracts/TCS-WorkProgress-20261119.md`（下稱 **TCS**）。
> 本稿新增的程式路徑（`tools/lib/openitems/` 等）在實作 commit 前不存在於磁碟；落點依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2，實作 commit 時同步登記該檔 §3。
> 用字：本稿與 TCS 是「待驗標記詞彙」的定義文件，會大量出現這些字樣；REQ-WP-23 的 CI 鎖以 `OpenItems_Protocol/params.json` 的 `vocabulary_definers` 名單豁免這兩份檔（§3.5）。

---

## 0. 結論與代決

### 0.1 結論（五句）
1. 掌舵者看到的「任務沒結束、工作就停滯」＝**宣告式完成**（ARC S7）：主控在 sid 31ea79d4 逐字稿 L1670／L1687 明列未結項後宣告「沒有剩下要做的事」並掛保溫，而 repo 沒有任何機械物會反駁它。
2. 成因在規格層：PRD 只有「額度」與「上下文／快取成本」兩軸，**沒有「工作推進」軸**；§16.1 邊界把真機驗收排除在結案判準外（PRD:2684），§16.5 明文禁待辦清單（PRD:2774），v2.1.22 列把待驗收裝進 ⏸（PRD:2787）——宣告式完成在規格上是合法的（ARC H1）。
3. 機械層兩個洞讓它更隱形：保溫 shell 讓半路停工閘的「無背景工作」恆假（ARC E2，`tools/lib/sessionctl/midwork.py:72-80`）；watch 的 `all_done` 與 harness 的子代理完成通知重複，14.5 小時 21 次叫醒中 8 次是純重複（ARC E3）。
4. 「AutoClaude 沒有作用」屬實：本輪引擎零次真跑（ARC E5），PRD 從未規定誰負責把任務推到完成。但前置條件比 PRD 自述好得多（§0.4）：根層 `.venv` 已能 import 引擎、PG 容器健康、MiniMax 金鑰已在。
5. 修法＝新增「工作推進軸」：**未結項登記簿 OIR**（單一資料面）＋**完成閘**（看狀態不看措辭）＋**驅動器四型**（每個未結項要嘛有排程器自報的憑證、要嘛進人工清單）＋**叫醒預算**＋**名冊收斂**＋**AutoClaude 當無人舵手**（期 B）。

### 0.2 主控代決（照任務書，WHY 一併寫明）
| 代號 | 決定 | WHY |
|---|---|---|
| D-1 | R217 一次收齊 ARC 的 M0～M5、SA 的 26 項未結與 8 個 E2E 缺口；分期 A（完成判準／名冊／叫醒／驅動器）、B（AutoClaude 上場）、C（PRD 補登與文件陳舊清理），每期都有真機 E2E | 掌舵者鐵令「若AutoClaude沒有辦法執行完任務, 應算BUG」；拆成「之後再看」正是本次要根除的型態 |
| D-2 | 無人窗口的舵手改由 AutoClaude playbook 引擎擔任，補進 PRD | 掌舵者 2026-08-08「無人時舵手是 AutoClaude Playbook」從未入憲（ARC H3）；引擎已有 GOAL_SYNTHESIS＋`evaluator_command`＝互動路徑缺的那一半完成判準（ARC §5） |
| D-3 | 防永動出廠值 `max_attempts=2`，用完轉人工清單；叫醒預算採 ARC §7 草案 | 回應 §16.5 拆永動源的本意（PRD:2659）：每個未結項只能被自動嘗試有限次 |

### 0.3 SD 代決（本稿新增，掌舵者可隨時以 T1 推翻）
| 代號 | 決定 | WHY |
|---|---|---|
| D-4 | realverify 接「OIR 驅動器」，**不接** nightly stage | nightly 新增 stage 會連動 summary 行、summary JSON、exit-decision 的跨檔字面鎖（`AutoClaude/tools/run_local_nightly.ps1:53-57` 自述）；`AutoClaude_Nightly` 現查 LastTaskResult＝1，混進去訊號不乾淨；週期全跑會反覆燒已 pass 案例的額度。OIR 驅動器是「一個未結項一次性排程」，有上限、有憑證 |
| D-5 | 「重驗」也走事件：某 realverify 家族的原始檔在其最後一筆 pass 之後被 commit 改過 ⇒ 掃描器開一個 `auto` 列（stale-pass，REQ-WP-16） | 解 SA a1「誰來重跑」而不引入日曆觸發 |
| D-6 | long-runner（ADR-XPLAT-004 §2.14 G3、V-T1～T3，SA a12）**依設計退役** | R216 的子代理分段等待（`runlong`／`waitfor`＋長前景閘）已覆蓋「子代理 5 分鐘快取壽命」這個需求；`.claude/agents` 現查不存在，新增等於擴守衛面而無暴露證據（根 CLAUDE.md〈守衛面准入〉） |
| D-7 | V-P6 的 `--pace-metrics`／`--replay-pace-floor`（SA a7）**實作**，不退役 | 它是量測（零 token、不接閘門），實作成本低；退役反而要動 ADR §2.15 的驗收定義 |
| D-8 | owner 是否活著改讀 harness 的 `~/.claude/sessions/<pid>.json`（`sessionId`＋`procStart`），命令列只認旗標形態；`procStart` 比對法與降級路徑見 §7 DEF-02 | 當回合現查：`15660.json` 的 `sessionId`＝31ea79d4（現行 session），而 `procstop.sid_of` 從 pid 15660 命令列取到的是交接包路徑裡的舊 sid 05d1b770（SA §4.2）。此檔是 harness 內部格式，必須有降級路徑（PRD:33 的「內部」紀律）：讀不到時退回旗標形態，再退回「不判活」。r2 現查：`procStart`＝134395057212197555 與 .NET `Process.StartTime.ToFileTimeUtc()`（底層 GetProcessTimes）**逐位相等**；CIM `Win32_Process.CreationDate` 換算得 …550（DMTF 字串只到微秒，截掉 100ns 尾數）——故採 GetProcessTimes 全等，CIM 只作備援並帶容差 |
| D-9 | AutoClaude 無人舵手**只推驗證類項目**（`auto` 列：有驗收指令者），不改文件、不 commit | 期 C 的文件改寫需要對話脈絡判斷（ARC §5 ④）；無人 commit／push 仍是 PRD §16.2 A7 的 ⏸ 掌舵者安全裁決，引擎只追加帳本列，由下一個有人窗口一併提交 |
| D-10 | 引擎預設啟用的判準是「DRY_RUN 後連續 3 次真跑成功」，不是 ARC M5 的「一週」 | 「一週」是日曆觸發，違反 §16.5 本意；次數判準是事件驅動 |
| D-11（r3） | 只有 `interactive` 讓路計入 deferrals；`window_cap`、`quota`、`busy` 都不計，改以先進先出（FIFO）保證每窗先跑最舊的列 | 後三者是系統排隊或額度節流，不是該項的問題。舊稿每窗 2 次、`max_deferrals`＝6，A8 種下 30 列時約 30 小時內多數列只因排隊就被 escalate（審查 N-2） |
| D-12（r3） | §11.1（6 小時）、§11.8（24 小時／4 次 reset）、V-K2 不再「等自然事件」，改成由驅動器主動跑完的案例（RV-SK1／RV-SK2 用真牆鐘＋真排程；RV-K2B 用 `quota_policy` 既有門檻鍵把帶別移到當下真實水位） | 掌舵者結案判準要求每條都要有 PASS 帳列，「已排程」不算。自然事件不保證會發生，等它就永遠結不了案 |
| D-13（r3） | 「PRD 全功能 E2E 對照表」產生器放在 realverify 底下（`tools/lib/realverify/coverage.py`，動詞 `realverify coverage`），母體放 `RealVerify_Protocol/prd_population.json` | 對照表的三個輸入（案例表、結果帳、母體）都屬 realverify 的持有面。另開模組，就得跨套件讀它的私有格式 |
| D-14（r3） | 同 sid 雙視窗的處置改照掌舵者裁決：五個條件全部成立才自動關閉閒置舊窗；同 sid 的 park 續跑改成「先關閒置舊窗，再 `claude -r`」，不跳過。條件不成立時不開第二個同 sid 視窗，排一次重試（§7.1） | 掌舵者 2026-11-19 互動選項「有條件自動關 (Recommended)」。這取代 r3 草稿原本的 `skip(live_window)`：直接跳過會讓 park 在舊窗還開著時永遠不觸發，又是一個空窗 |
| D-15（r4） | 每個 PRD 逐列案例（RV-PX01～49）與每個 R217 新案例都要在模組宣告 `CARRIER`（載具代號）與 `ASSERTS`（斷言鍵）；執行器在案例回 pass 時，若 `ASSERTS` 有任一鍵沒有寫出證據值，就把結果改判 fail（`assert_missing`）；CI 鎖再比對模組宣告與 TCS §10.3 附錄逐格相同 | 審查指出 A01～A46 只有 id、沒有斷言，是「之後再看」。只靠文件寫斷言，實作時仍可交一個空殼案例拿到 pass；把斷言鍵變成執行期與 CI 都會檢查的資料，空殼在結構上拿不到 PASS |
| D-16（r4） | 結果帳新增「執行案例」欄，判讀只認列出該 id 的列；long／soak 案例的 PASS 還要與 OIR 的 `start`／`attempt(pass)` 對帳，且時間跨度 ≥ `MIN_WALL_SECONDS`；`MIN_WALL_SECONDS` 釘在 `coverage_params.json`，下修受兩道鎖 | 現況 `run --family` 不帶 `--long` 會略過 long 案例（`tools/tests/test_realverify_lib.py:195-200`），但帳列只寫 `family=<家族>`（`RealVerify_Result_Ledger.md:8-11`），舊判讀會把沒跑的 long 案例也判 PASS（假綠） |
| D-17（r4） | 舊窗收到以 `留：` 開頭的提示 ⇒ 永久否決「該交接包」的自動關閉，並留痕；之後重試排程、park、ack 都不再關這個窗 | `留：` 是掌舵者明示「我要留在這個視窗」的既有契約（ADR-XPLAT-004 §2.18）。自動關閉若蓋過它，就違反掌舵者的明示意思。這是對掌舵者「有條件自動關」裁決的細化，只多保護掌舵者明說要留下的視窗，不放寬五條件中的任何一條 |
| D-18（r4） | 對照表產物由兩個寫入點負責重產：realverify 的結果帳寫入函式（行程內，寫完帳列就重產）與 `run-driver` 第 7 步（寫完 OIR 事件後以子行程跑 `realverify coverage --write`）；產物列入 `driver_own_prefixes` | 驅動器追加帳列但不 commit（D-9），若沒人重產，工作樹裡的 `coverage --check` 會一直紅。讓「寫帳的人順便重產」，產物與帳本永遠同步，下一個有人窗口三檔一起提交 |

### 0.4 AutoClaude 前置現查結果（2026-11-19 19:0x，本棒當回合 PowerShell 實跑；只查鍵名、未印任何值）
| 前置 | 結果 | 期 B 處置 |
|---|---|---|
| 根層 `.venv` 能否 import 引擎 | `importlib.util.find_spec('autoclaude').origin`＝`D:\…\AutoClaude\autoclaude\__init__.py`，rc 0（editable 安裝）；`import autoclaude.utils.notifier` 印 `notifier ok` | PRD §4.5.7 偏離 2（PRD:1297-1299「未安裝於根層 `.venv`」）已陳舊 ⇒ 附錄 A 列 A-9 就地註記 |
| `python -m autoclaude --help` | 印出 usage（`[--config CONFIG] [--fresh] [--last-run-summary] [playbook]`）；另有 `wexpect` 的 `pkg_resources` 棄用警告 | WP-B1 把警告列入相容性檢查（setuptools 升 81 後 import 會壞） |
| PG 後端 | `autoclaude_pg` Up 7 days (healthy)，`pgvector/pgvector:pg18` | 但 `AutoClaude/config.yaml` 的 `storage.mode: yaml_only` ⇒ 目前**沒用 PG**；舵手不需要 PG（§9.3-1）；alembic 版本未查 ⇒ WP-B1 資訊步驟 |
| LLM 金鑰 | `AutoClaude/.env` 有 `MINIMAX_API_KEY`、`MINIMAX_GROUP_ID`（值存在）；根 `.env` 無任何鍵 | 引擎從 `AutoClaude/.env` 讀，四層載入鏈已支援（PRD:2785）；不需新金鑰 |
| 執行器 | `executor.backend: pty`；RV-A1 引擎真跑曾 pass（`RealVerify_Result_Ledger.md:64`，2026-11-18T15:05:32Z） | 沿用 pty；DEF-101-913 的 pty 掛住只在 `CLAUDECODE=1` 下，排程啟動不帶該變數 |
| 排程 | `AutoClaude_Nightly` LastTaskResult 1、`AutoSDD_SI_Patrol` 0、本 session 哨兵 0 | D-4 不接 nightly |

### 0.5 待掌舵者決定
無。期 B 的前置全部可由實作窗口自行補齊（沒有任何一項需要掌舵者付費或提供新憑證）；無人 commit／push（A7）維持 ⏸，本設計刻意不需要它（D-9）。

**本節判準**：§0.4 每一列可用 TCS E2E-WP-30 重跑得到相同結論；§0.3 每個代決都在附錄 A 或 TCS 有對應列。

---

## 1. 問題與證據（座標全部引自 ARC／SA，並由本棒抽驗）

| # | 現象 | 證據座標 | 本棒抽驗 |
|---|---|---|---|
| P1 | 宣告式完成 | ARC E1：逐字稿 31ea79d4 L1670、L1687、L1703 | 未重讀（引用） |
| P2 | 保溫遮蔽半路停工閘 | `midwork.py:72-80` `background_idle` 只看有無 running | 實查：line 72 `def background_idle`，line 79 只比 `status == "running"`，不分型別 |
| P3 | 叫醒重複 | ARC E3（21 次、8 次 rc 0 在 Agent finished 後 7～30 秒） | `watch.py:33` `ORDER` 含 `all_done`；`watch.py:159` 找到 all_done 即成立 |
| P4 | 被 TaskStop 的代理不消失 | SA §4.2：`roster.py:29` `_TAIL_BYTES=262144`；killed 行距檔尾 284,096 bytes | 實查 `roster.py:29`、`:173` 存在 |
| P5 | 擁有者誤判活著 | `procstop.py:113-116` 取第一個 UUID；`roster.py:210` 用它算 `alive` | 實查同；`~/.claude/sessions/15660.json` 的 `sessionId`＝31ea79d4 |
| P6 | RealVerify 沙盒逐字稿目錄殘留 | SA §4.3：5 個 `*AutoSDD-RV-sbx-*` | 實查 5 個；`sandbox.py:230-231` 已有 `rmtree(…, ignore_errors=True)`，故成因不是「沒清」而是「清了被吞掉或之後又被寫」（mtime 晚於案例結束，如 `m03e10h4` 21:38:25 有 3 檔）。WP-A3 先查明成因再修 |
| P7 | realverify 無驅動 | SA §0-2、a1 | 未重跑（引用） |
| P8 | 14 天時間閘無人接 | SA b1／b2 | 引用 |
| P9 | AutoClaude 零真跑；單元測試寫進真 `checkpoints/` | ARC E5、H9 | 引用；前置見 §0.4 |
| P10 | PRD 漏登 8 族機制 | SA §0-1、a16 | 引用 |

**本節判準**：每一列在 TCS §6 對到至少一個 REQ 或 E2E。

---

## 2. 名詞與「完成」的機械定義

| 名詞 | 定義 |
|---|---|
| 未結項（Open Item，OI） | 一個已立案功能的驗收項：有出處（TCS／帳本／ADR 座標）、有判準（指令或人眼），尚未有關閉證據 |
| OIR | 未結項登記簿：OI 的唯一資料面（§3） |
| 驅動器（Driver） | 會在無人提醒下把 OI 往「關閉」推一步的機制；四型見 §5 |
| 憑證（Credential） | 驅動器存在的證明，必須是**排程器自報的值**（Windows `NextRunTime`、macOS launchd rc），或「人工清單已收錄」的清單快照列 |
| undriven | 狀態為 `open`，且沒有有效憑證、也沒有進人工清單的 OI |
| 完成（Done） | 一個範圍（一輪、一個功能鍵、或全域）**名下沒有 undriven 的 OI** |

完成閘只判 undriven 的數量；主控說了什麼不參與判斷。

**本節判準**：TCS AT-WP-03 以「措辭說完成、OIR 有 undriven」與「措辭說還要做、OIR 全 driven」兩組夾具驗證判決只隨狀態變。

---

## 3. OIR 資料模型與生命週期

### 3.1 檔案
| 檔 | 內容 | 誰寫 |
|---|---|---|
| `docs/06_quality/OpenItems_Event_Ledger.jsonl` | 事件帳本（append-only，一行一事件），git 追蹤 | `tools/openitems.py` 各動詞；驅動器 |
| `docs/06_quality/OpenItems_Protocol/params.json` | `max_attempts`（2）、`max_deferrals`（6）、`human_cap`（7）、`marker_regex`、`scan_globs`、`vocabulary_definers`、`retry_backoff_minutes`（360）；r2 新增：`start_grace_minutes`（15）、`run_budget_margin_minutes`（15）、`observe_timeout_minutes`（30）、`max_runs_per_window`（2）、`cap_window_minutes`（300）、`stagger_minutes`（10）、`busy_backoff_minutes`（20）、`sched_cache_ttl_seconds`（600）、`driver_own_prefixes`（§5.5）；r3 新增：`task_prefix`（出廠 `AutoSDD_OpenItem_`；沙盒 E2E 改成專屬前綴，§4.5）、`followup_grace_minutes`（15，§3.3） | 人（規格變更才改） |
| `~/.autosdd/traces/openitems/`（`endurance_env.trace_dir()` 之下） | 驅動器執行 log、每回合閘標記 `<sid>.gate` | 驅動器、完成閘 |

WHY 事件帳本放 repo 而非 trace 目錄：OI 是跨 session、跨機器的共同事實，要能被審查與 diff；trace 目錄重灌就沒了。WHY append-only：無人驅動器與互動 session 可能同時寫，追加比改寫衝突面小；fold 時以 `(ts, seq)` 排序。

### 3.2 事件 schema（每行一個 JSON 物件，UTF-8、LF）
共通欄：`ts`（帶 offset 的 ISO）、`ev`、`id`（`OI-<YYYYMMDD>-<NNN>`，配號在寫入鎖內取最大號＋1）、`by`（`sid:<uuid>`／`driver:<task 名>`／`human`）。

| `ev` | 專屬欄 | 意義 |
|---|---|---|
| `open` | `title`、`source`（座標）、`scope`（功能鍵或輪號）、`kind`（auto／observe／human／k1）、`check`（auto／observe：`{"realverify": "RV-x"}` 或 `{"argv": [...], "pass": "rc0"｜"regex:<式>"}`）、`due`（observe 必填）、`why_not_auto`（human 必填，≥8 字） | 立案 |
| `drive` | `task`、`credential`（排程器原文值）、`at`（預定觸發時刻，帶 offset） | 掛上驅動器 |
| `start` | `drive_seq`（對應的 `drive` 事件序號）、`pid`、`proc_start`、`budget_minutes`（本次執行的時間預算，§3.3） | run-driver 行程已真的起來（r2 新增；觸發後判有效性的唯一依據） |
| `attempt` | `n`、`result`（pass／fail／deferred）、`reason`（deferred 時：interactive／quota／busy／window_cap）、`drive_seq`、`evidence`（帳列座標、log 路徑） | 驅動器跑完一次 |
| `close` | `evidence`（RealVerify 帳列時間戳＋案例、CI run id、逐字稿 sid＋行號，或掌舵者發言 sid＋行號） | 關閉 |
| `escalate` | `reason` | 嘗試用盡或 deferral 用盡，轉 human |
| `convert` | `kind`、`why` | 改型（例：human 轉 auto，因找到機驗法） |
| `retire` | `why`、`basis`（修憲列／代決座標） | 依設計不做 |

### 3.3 狀態機（fold 結果）
```
open ──drive──▶ driven ──attempt(pass)+close──▶ closed
  │                │ attempt(fail) 且 n<max_attempts ──▶ driven（驅動器自行重排，新 drive 事件）
  │                │ attempt(fail) 且 n≥max_attempts ──▶ escalated（＝human 清單）
  │                │ attempt(deferred, interactive) 且 deferrals≥max_deferrals ──▶ escalated（r3：其他 deferred 原因不計）
  ├─(kind=human/k1)──────────────────────────────▶ listed（進人工清單）
  └─retire──▶ retired
```
- `driven` 的有效性在讀取時判定，**以帳本對帳為主、排程器只用在觸發前**（r2；舊版「NextRunTime 早於現在 15 分」有洞：Windows 一次性排程觸發後 `NextRunTime` 變空、run-driver 中途崩潰時工作還在且 `NextRunTime` 也空 ⇒ 永遠算 driven；macOS launchd 根本不報下次時刻）。令 `d`＝最後一筆 `drive`、`s`＝`drive_seq`＝d 的 `start`、`a`＝`drive_seq`＝d 的 `attempt`：

  | 時段 | 有效（driven）⇔ | 否則 |
  |---|---|---|
  | `now < d.at` | 排程工作存在（Windows：批次列舉快取含該 task；macOS：`launchctl list <label>` rc 0）。快取過期或讀不到 ⇒ 依帳本視為有效（觸發後的對帳會抓到） | undriven（被外力刪除） |
  | `d.at ≤ now < d.at + start_grace` | 一律有效（等待觸發） | — |
  | `now ≥ d.at + start_grace` 且無 `s` | — | undriven（排程沒觸發：睡眠錯過、工作被刪、載具壞） |
  | 有 `s`、無 `a` | `now < s.ts + s.budget_minutes` | undriven（run-driver 崩潰或被殺；`s.pid` 是否活著只作輔證、不作判準） |
  | 有 `a` | `a` 之後（序號更大）有對應的後續事件：fail 未達上限或 deferred ⇒ 新的 `drive`（它成為新的 `d`，回到本表第一列重判）；pass ⇒ `close`；fail 達上限或 deferrals 用盡 ⇒ `escalate`。或者還在 `a.ts + followup_grace_minutes` 之內（run-driver 寫完 `a` 到寫出後續事件之間的正常間隔） | undriven（r3）：run-driver 在 `a` 之後崩潰，或重排時憑證回讀失敗、依 REQ-WP-10 不寫 `drive`。舊稿寫「依 a.result 走狀態機」，這段空窗會永遠算 driven，完成閘靜默失效（審查 N-1） |

  `budget_minutes`＝auto：該 RV 案例宣告的牆鐘上限（long 案例取其值）＋`run_budget_margin_minutes`；observe：`observe_timeout_minutes`。判準與平台無關（觸發後完全不讀 `NextRunTime`），macOS 與 Windows 同一張表。排程靜默失效仍可偵測（根 CLAUDE.md〈反「事後諸葛」取證規則〉）。
- （r3，D-11）`deferred` 一律不消耗 `attempts`。只有 `reason=interactive` 累計 `deferrals`。`quota`、`window_cap`、`busy` 都不累計：它們是系統排隊或額度節流，不是該項的問題。這三種的有界性由 §5.4 的先進先出保證：任一列最多等「排在它前面的列數 ÷ `max_runs_per_window`」個窗。`openitems list` 對每列印「已排隊窗數」作資訊欄，不作閘門。
- `escalated` 與 `listed` 都算「有驅動器」（人工清單就是它的驅動器），不算 undriven。

### 3.4 收件範圍（防永動）
OIR 只收「已立案功能的驗收項」：TCS 的 E2E／V 項、帳本 DEF 的待驗尾巴、ADR 決定的驗收條件。**不收**覆蓋度缺口、不收「可以更好」的建議——母體仍凍結，不復活 v2.1.17 拆掉的永動源（PRD:2659）。

### 3.5 掃描器（M0，唯讀）
`python tools/openitems.py scan`：對 `scan_globs`（出廠＝git 追蹤的 `docs/**/*.md`、根 `CLAUDE.md`）跑 `marker_regex`（出廠＝`待真機|待掌舵者目視|待目視|仍待真機|待驗|計未結`，即 ARC E6 的詞表），輸出每處標記與它所在行是否帶 `OI-\d{8}-\d{3}`。`vocabulary_definers` 名單內的檔不判。末行 `OPENITEMS_SCAN=mapped=<n> unmapped=<m>`，rc 0（unmapped 是資訊，不是錯誤；閘門在 REQ-WP-23 的 CI 鎖）。

**本節判準**：TCS AT-WP-01～09（fold、配號、憑證現查、防永動）、AT-WP-29（`start` 事件）、AT-WP-50／51（觸發後空 `NextRunTime`、macOS 無 `NextRunTime`）、AT-WP-66（r3：`attempt` 之後的空窗）、AT-WP-69（r3：deferrals 只計 interactive）、E2E-WP-55（r3：真 hook 對「attempt 後無後續事件」的帳本推回）＋E2E-WP-01（真 repo 掃描，與 ARC E6 的 143 處／61 檔對帳，差異逐條解釋）、E2E-WP-43（真行程並行配號）、E2E-WP-46（run-driver 中途被殺 ⇒ 預算過後 undriven）。

---

## 4. 完成閘（Stop；看狀態、不看措辭）

### 4.1 判準（`tools/lib/openitems/gate.py::stop_verdict`，純函式）
推回一次 ⇔ 全部成立：
1. Stop payload 的 `stop_hook_active` 為假（第二次 Stop 放行，與既有 Stop 守衛同一約定）。
2. 不在無人窗口（`AUTOSDD_UNATTENDED` 未設）——無人窗口由 AutoClaude 舵手負責（§9）。
3. OIR fold 後 undriven 數 ≥1（全域，不分 session；WHY：undriven 按定義沒有主人，任何正在動工的 session 都是最近的舵手；一旦掛上驅動器就永久安靜）。
4. 本回合有狀態佐證：做過非唯讀工具，或 `git status` 髒。（r3 釐清）佐證在 hook 行程內**只算一次**，由兩個判準共用：hook 先用 `midwork.did_work`（`tools/lib/sessionctl/midwork.py:97`）判斷；它先看本回合的工具集合，只有工具集合不足以判定時，才呼叫它既有的 `tree_dirty`（`midwork.py:83`，一次有逾時的 `git status --porcelain`）。算出的布林值以參數 `evidence` 傳給 `gate.stop_verdict(…, evidence=…)` 與半路停工判準。所以完成閘這個函式本身不開任何子行程，也不重算佐證（§4.5）。新增成本只有一種情形：本回合只用唯讀工具、而 OIR 有 undriven 時，原本不必跑的那一次 `git status` 會被跑到；它在既有 hook timeout 內，由 E2E-WP-48 計時。只讀檔答問且工作樹乾淨的回合不推。

推回訊息（≤6 行）：列前 5 個 undriven 的 id＋title＋建議出口，出口只有三條：`python tools/openitems.py drive <id>`（auto／observe）、`python tools/openitems.py convert <id> --kind human --why "<WHY>"`、同回合 AskUserQuestion。閘每次推回時寫 `trace_dir()/openitems/<sid>.gate`（當回合標記，供 §6 保溫閘讓路）。

### 4.2 接線
- 判準住 `tools/lib/openitems/gate.py`；hook 接線在 `.claude/hooks/check_pending_handoff.py`（它本來就是「工作沒做完」的 Stop 守衛、唯一會阻斷的 Stop 守衛）。與既有兩個判準（散文交棒、半路停工）**合併成一則**推回，次序：半路停工 → 散文交棒 → 完成閘。
- 守衛面准入的暴露證據：sid 31ea79d4 逐字稿 L1670／L1687（ARC E1）＋掌舵者真機回報（同 sid 2026-11-19 17:5x 原話）。
- fail-open：OIR 讀不到、解析失敗 ⇒ 不推回，stderr 出聲一行。
- 延遲：見 §4.5（閘本身不開任何子行程）。

### 4.3 半路停工閘的保溫遮蔽（S8）
`midwork.background_idle` 改為：`background_tasks` 中**排除純保溫 shell** 後沒有 running 項。純保溫 shell 的判準＝`tools/lib/sessionctl/roster.py:400-401` 的 `WATCH_CMD_RE`／`KEEPWARM_CMD_RE`（已存在，`roster.py:409` 已有合併判斷）——單一真相源，`midwork` 呼叫 roster 的判斷函式，不複製正則。WHY 排除 watch 也算：watch 在子代理全部交卷後只剩保溫功能（§6.1），而子代理本身另有 `agent` 型的 running 項，不會因此被誤判為閒置。

### 4.4 與保溫閘的關係
完成閘推回的那一回合，`sessionctl_guard` 的保溫閘讀到 `<sid>.gate` 標記即不推「掛保溫」（避免叫主控在 undriven 狀態下閒置保溫）。跨套件只透過資料檔，不互 import（Root_Layout §2 第一列）。

### 4.5 延遲預算與排程批次列舉（r2）
- 背景：`check_pending_handoff` 在 `.claude/settings.json:248` 的 timeout 是 15 秒；Windows 逐列現查排程要每列開一次 PowerShell（冷啟動數百毫秒到秒級），N 列即線性放大，逾時時 Claude Code fail-open ⇒ 閘靜默失效。
- 規則：**完成閘不開任何子行程**。判 driven 有效性只讀①事件帳本、②排程快取 `trace_dir()/openitems/sched_cache.json`（`{"at": <ISO>, "platform": …, "tasks": {<task 名>: <NextRunTime 原文或空>}}`）。快取由**一次**批次列舉寫入：Windows＝單一 PowerShell 行程 `Get-ScheduledTask -TaskName '<task_prefix>*' | Get-ScheduledTaskInfo`；macOS＝單次 `launchctl list` 過濾前綴。（r3）前綴一律讀 `params.json` 的 `task_prefix`（出廠 `AutoSDD_OpenItem_`）。沙盒 E2E 用 `AutoSDD_OpenItemSbx_<沙盒 8 碼>_`，不會與真的 `AutoSDD_OpenItem_*` 混在一起（E2E-WP-48）。寫快取者＝`drive`、`run-driver`（開始與結束）、`openitems list --verify`、`sessionctl status`。快取逾 `sched_cache_ttl_seconds` ⇒ 觸發前時段依 §3.3 表「讀不到」列處理（視為有效），不在閘內重列舉。
- 延遲預算：完成閘判準（讀帳本＋fold＋快取＋判決）在 N＝50 列時 ≤2 秒（含 Python 冷啟動以外的全部；目標典型 ≤0.3 秒）；`list --verify` 不論 N 只開 1 個列舉子行程。
- `git status` 佐證沿用 `midwork` 既有實作（已在同一 hook 內付過的成本，不新增）。

**本節判準**：TCS AT-WP-20～28、AT-WP-57（N＝50、子行程 0、≤2 秒）、E2E-WP-06（真 `claude -p`＋真 Stop hook，四個變體）、E2E-WP-45（OIR 讀不到 ⇒ 放行＋stderr）、E2E-WP-48（50 個真排程下真 hook 計時）、MU-WP-01／07／15。

---

## 5. 驅動器四型與排程憑證

| kind | 驅動器 | 憑證 | 關閉條件 |
|---|---|---|---|
| auto | 一次性排程 `AutoSDD_OpenItem_<id>_<yyyyMMddHHmm>` 執行 `pythonw tools/openitems.py run-driver <id>` | 排程器自報 `NextRunTime`（Windows）／launchd rc（macOS），`drive` 當下回讀，取不到即 rc≠0 且不寫 `drive` 事件 | `check` 通過：realverify 帳出現該案例 pass 列（時間晚於 `open`），或 argv 判準成立 |
| observe | 一次性排程，觸發時刻＝`due` | 同上 | 到期時跑量測指令（例 `python tools/probe/waste_census.py --switch-metrics --since-days 14`），判準成立即關 |
| human | SessionStart 簡報的人工清單＋掌舵者在場時同回合 AskUserQuestion | 清單快照列（`listed` 狀態本身） | `close --by human --evidence "<sid> L<行>"`，證據必須是掌舵者真人發言 |
| k1 | 只列、不推 | 同 human | 只認掌舵者親打的 DEC（AskUserQuestion 不算） |

### 5.1 `run-driver <id>` 流程（auto／observe 共用）
0. 寫 `start`（`drive_seq`、`pid`、`proc_start`、`budget_minutes`）；接著跑一次 `scan --stale-pass`（§8-4 觸發事件 (b)；零 token，只讀 `git log` 與帳本）。
1. 讀 OIR；項目已 closed／retired ⇒ 記一行、刪除自己的排程、rc 0。
2. **讓路**：同專案有互動 session 在一個巡邏間隔內做過真實工作（判準＝`tools/lib/transcript_activity.py`，與哨兵雙駕駛同一家）⇒ `attempt(result=deferred, reason=interactive)`，重排 `retry_backoff_minutes` 後（錯開規則見 §5.4），rc 0。
3. **全域互斥與每窗上限**（§5.4）：拿不到全域鎖 ⇒ `deferred(reason=busy)`；依 §5.4-2 的先進先出規則拿不到本窗名額 ⇒ `deferred(reason=window_cap)`。soak 類案例（§8-5）走 §5.4-5 的獨立通道，不經本步。
4. **額度**（PRD §1.2 原則 3 雙軸、原則 5 失效即保守）：`python tools/session_resume_planner.py --pace` 的短窗或週軸任一帶在「收斂」以上、或可派數 <1、或 `--pace` 讀不到 ⇒ `deferred(reason=quota)`，重排到短窗 reset 後（reset 量不到 ⇒ 重排 `retry_backoff_minutes`），rc 0。
5. 執行：auto＝`python tools/realverify.py run --case <RV>`（帶 `--long` 若案例標 long）；observe＝argv。環境走 `resume_route.spawn_env()`（無人 print 模式上限，ADR-XPLAT-004 §2.12）並設 `AUTOSDD_UNATTENDED=1`。執行前在每窗計數檔記一筆（§5.4）。
6. 寫 `attempt`；pass ⇒ 寫 `close`、刪排程；fail ⇒ `n < max_attempts` 則重排（`retry_backoff_minutes` 後）並寫新 `drive`，否則 `escalate`。（r3）任何重排（含第 2～4 步的 deferred）都走 `drive` 同一條路：憑證回讀不到 ⇒ **不寫** `drive`，log 與末行加 `redrive=failed`，rc 仍為 0。之後 fold 依 §3.3「有 `a`」列，在 `followup_grace_minutes` 後判 undriven，由完成閘或下一個有人窗口接手。不在 run-driver 內重試排程，以免一個壞掉的排程器造成無界迴圈。
7. （r4，D-18）寫完本次全部 OIR 事件後，以子行程跑一次 `python tools/realverify.py coverage --write`（逾時 60 秒；失敗只記 log 與末行 `coverage=failed`，不改判決），讓對照表反映剛寫入的 `attempt`／`close`。接著釋放全域鎖、刷新排程快取（§4.5）、刪除自己這一次的排程工作（一次性），末行 `OPENITEMS_DRIVER=<result> id=<id> n=<n>`，**rc 0**（判決只看末行，與 R216 UX 棒的退出碼原則一致，§10）。

### 5.2 排程原語
沿用 `tools/lib/schedule_backend*.py`（Windows 四項設定 WakeToRun／StartWhenAvailable／DisallowStartIfOnBatteries=False／StopIfGoingOnBatteries=False；macOS launchd），不另寫排程知識。命名前綴 `AutoSDD_OpenItem_` 列入 `sessionctl status` 的排程區（現查用）。

### 5.3 人工清單
- SessionStart 簡報（`tools/lib/session_brief.py`）末段印「掌舵者目視清單」：`listed`＋`escalated` 依 `open` 時間排序前 `human_cap`（7）項，超過印「另 k 項」。零 token、≤0.3 s 預算。
- human 列數 > `human_cap` 時，完成閘每個 session 第一次 Stop 額外附一行「人工清單已滿 k 項，請先嘗試轉機驗」（只出聲一次，不阻斷）——ARC §6-2 的「超過 N 項必須先嘗試轉機驗」以出聲落地，避免把人工項變成新的阻斷永動源。

### 5.4 全域併發與花費上限（r2；PRD §1.2 原則 3、原則 5）
背景：A8 一次種幾十列 auto；主控在場時全部 `deferred(interactive)` 360 分，到點同時觸發 ⇒ 大量 `claude -p` 扇出（long 案例單支可達 3 小時）。四道限制同時生效：
1. **全域互斥鎖**：`trace_dir()/openitems/driver.lock`（內容 `pid`、`proc_start`、`id`、`started_at`、`budget_minutes`）。同時只有 1 支 run-driver 走到第 5 步。持有者判活＝pid 存在且行程建立時間相符（比對法同 §7 DEF-02），**且** `now < started_at + budget_minutes`（逾預算視為卡死、可接手，防一支掛住的 driver 永久佔鎖）。取鎖用 OS 原子建立（`O_CREAT|O_EXCL`）＋讀回驗證。拿不到 ⇒ `deferred(busy)`，重排 `busy_backoff_minutes` 後（錯開）。
2. **每窗次數上限**：`trace_dir()/openitems/window_runs.jsonl` 記每次走到第 5 步的時刻；窗＝`--pace` 觀測到的短窗 reset 所界定的當前窗，量不到 reset 時退用最近 `cap_window_minutes` 的滾動區間（這是限速口徑、不是預測 reset，不違反「reset 只能觀測」）。（r3 先進先出，D-11）每列的排隊鍵＝`(open 事件的 ts, id)`。令 `R`＝本窗已執行次數、`O`＝排隊鍵比自己小、目前 `d.at` 落在本窗、且本窗還沒有 `start` 的 driven 列數。**只有在 `R + O < max_runs_per_window`（出廠 2）時才拿到名額**，否則 `deferred(window_cap)`。所以中途新開的列不會插到已在排隊的舊列前面。重排時刻＝下一窗起點（觀測 reset；量不到 ⇒ 滾動區間終點），再依 3. 的錯開規則，**按排隊鍵順序**分配時槽：每窗先跑最舊的 `max_runs_per_window` 列。`window_cap` 不計 deferrals（§3.3），所以 30 列在每窗 2 次的條件下 15 個窗內全部跑過，沒有任何一列因排隊被 escalate（AT-WP-67、E2E-WP-56）。
3. **排程錯開**：`drive`（含所有重排）在 OIR 寫入鎖內選觸發時刻：從期望時刻起，找第一個與所有其他 `driven` 列的 `at` 相距 ≥`stagger_minutes` 的時槽。同一批重排依排隊鍵順序分配，不會落在同一分鐘。
4. **可派數**：第 4 步 `--pace` 的可派數 <1 即不跑（主控在場時互動 session 已先吃掉可派數，驅動器自然讓出）。`quota` deferred 同樣不計 deferrals，並沿用 2. 的排隊鍵順序重排。
5. **soak 通道**（r3，D-12）：案例模組宣告 `KIND="soak"`（長時間、近乎零 token，例如 RV-SK1／RV-SK2）時，不取 `driver.lock`、不佔每窗名額，改取 `trace_dir()/openitems/soak.lock`（同時至多 1 支，判活規則同 1.）。WHY：24 小時案例若持有全域鎖，會把其他全部列卡住一整天；而 soak 案例內部的 `claude -p` 只有少數幾次 haiku 呼叫（RV-SK2 為 4 次），花費可忽略。
效果上界：任一 reset 窗內驅動器至多 `max_runs_per_window` 次一般案例執行，加上至多 1 支 soak 案例；一般案例任一時刻至多 1 支。最壞花費＝2×單一案例上限＋1 支 soak 案例，與 OI 列數無關。

### 5.5 驅動器自有寫入面（r2）
- 無人驅動器會追加兩本帳：`docs/06_quality/OpenItems_Event_Ledger.jsonl`、`docs/06_quality/RealVerify_Result_Ledger.md`（D-9：不 commit，由下一個有人窗口提交）。追加後工作樹變髒。（r4，D-18）另會重產一份產物 `docs/06_quality/PRD_E2E_Coverage_Table.md`，所以 `driver_own_prefixes` 出廠＝這三個路徑；三檔由下一個有人窗口**同一個 commit** 提交（CI 鎖 (d) 對三者不同步即紅）。
- SSOT＝`docs/06_quality/OpenItems_Protocol/params.json` 的 `driver_own_prefixes`（資料檔，不以 Python 常數互 import——§4.4 跨套件只透過資料檔）。**不併入** SI 的 `tools/lib/selfimproving/sched.py:34` `OWN_PREFIXES`：那份是「SI 自有面」的 SSOT，混入會讓 SI 的提交白名單語意變糊。
- 界面（三個消費端，實作 commit 同批改）：
  | 消費端 | 現況 | r2 後 |
  |---|---|---|
  | handoff `--spawn` 前置（`tools/lib/sessionctl/handoff.py:334-348` `_si_owned`） | 只排除 `sched.OWN_PREFIXES` | 排除「SI 自有面 ∪ `driver_own_prefixes`」；兩來源各自讀不到 ⇒ 該來源不排除（保守，回到拒絕），函式改名 `_auto_owned` |
  | SI 巡邏髒檢（`sched.py:282-301` `dirty_paths`） | 只排除 SI 自有面 | 另排除 `driver_own_prefixes`（驅動器寫入不得擋 SI 巡邏）；SI 的提交白名單**不變**（SI 永不提交驅動器的帳） |
  | 驅動器自己 | — | 不檢查工作樹髒不髒（它不 commit）；只寫 `driver_own_prefixes` 的三個路徑（兩本帳追加、對照表重產），寫任何其他 repo 路徑＝缺陷 |
- 互動 session 手跑 `realverify run` 寫的帳列同屬此面：spawn 不因它拒絕，帳列隨同一棵工作樹交給新 session，不遺失。

**本節判準**：TCS AT-WP-10～17、AT-WP-53～56、AT-WP-58、E2E-WP-02～05、E2E-WP-21、E2E-WP-47（扇出上界）、E2E-WP-49（真 git 工作樹的自有面排除）、MU-WP-04／05／14／16；r3：AT-WP-67～69（先進先出、不計 deferrals）、E2E-WP-56（真排程的先進先出）、MU-WP-18／19。

---

## 6. 叫醒預算與事件源合一

### 6.1 watch 不再因 all_done 退出（REQ-WP-30）
- `watch.ORDER`（`watch.py:33`）移除 `all_done` 作為**退出事件**。全部交卷後 watch 轉入「保溫模式」：只剩 `keepwarm`／`cap`／`idle`／`quota`／`budget` 會讓它退出（§6.3 表；舊稿只列三事件，缺 cap／idle ⇒ 達上限後永不退出）。
- WHY：harness 對每支背景子代理完成都會送 task-notification（ARC E3 八次皆在 7～30 秒後重複）；watch 再退出一次＝同一事件叫醒兩次，每次主控冷讀 40 萬～99 萬 cache_read。
- 處置表 `all_done` 列文字改掛在 harness 的子代理完成通知上（根 CLAUDE.md〈派背景代理〉說明由期 C 同步）。

### 6.2 保溫錨互斥（REQ-WP-31）
同一 sid 同時只允許一個保溫持有者：`trace_dir()/keepwarm/<sid>.holder`（內容 pid＋行程建立時間）。`keepwarm` 啟動時發現持有者活著（pid 存在且建立時間相符）⇒ 印 `KEEPWARM_VERDICT=skip reason=holder_running`、rc 0 立即結束；watch 持有時同理。持有者死掉（pid 不在或建立時間不符）⇒ 接手。

### 6.3 叫醒共用預算（REQ-WP-32）
watch 的 `keepwarm` 事件與 `keepwarm` 指令的 `ping` 共用 REQ-SS-04 的保溫帳 `pings`，上限同為 `n*`（F1）。keepwarm 指令達上限印 `cap`。真人提示出現即歸零（不變）。

**保溫模式的退出條件（r2；舊版「達上限後繼續看其他事件」在全部交卷後沒有任何會成立的事件 ⇒ watch 永不退出）**。全部交卷後 watch 只在下列之一成立時結束，全部 rc 0、末行 `WATCH_VERDICT=`：
| 事件 | 時點 | 處置表列 |
|---|---|---|
| `keepwarm` | 保溫點到、`pings < n*`、保溫適用 | 重掛同一指令並結束回合（§6.4） |
| `cap` | 保溫點到、`pings ≥ n*` | 不重掛、結束回合（與 keepwarm 指令的 `cap` 同語意） |
| `idle` | 保溫點到、保溫不適用（無人窗口／模式非 auto／`AUTOSDD_KEEPWARM_OFF`／已交棒／上下文低於門檻——條件同 `keepwarm.stop_verdict` 的「不掛的情形」，單一真相源） | 不重掛、結束回合 |
| `quota`／`budget` | 原判準 | 原處置 |
所以全部交卷後 watch 至多再叫醒一次，且那一次落在保溫點（不與 harness 的子代理完成通知重疊）。

### 6.4 一叫一回合（REQ-WP-34）與量測（REQ-WP-33）
- 處置表的 `ping` 列文字明定「重掛同一指令並結束回合，不做任何判斷」。
- waste_census 新增 M-WB1（每次保溫叫醒後主控 assistant 回合數；**資訊欄**，觀察目標 ≤1，不作任何閘門或結案條件——它取決於 LLM 行為）、M-WB2（task-notification 在子代理完成通知後 60 秒內的重複叫醒數，目標 0；由 §6.1 機械保證）。判準住 `tools/lib/wastecensus/sections_wake.py`，旗標 `--wake-metrics`。

**本節判準**：TCS AT-WP-30～37、E2E-WP-19／20、MU-WP-06／11；M-WB2 在上線後真逐字稿量到 0。

---

## 7. 名冊修正（R217-DEF-01～03；帳本編號由收尾窗口取 DEF-200-624 起現查最大號＋1）

| 缺陷 | 修法（消除成因） | 位置 |
|---|---|---|
| DEF-01 killed 通知超出 256KB 尾讀 | 改為**增量全掃**：快取 `trace_dir()/roster/<owner>.killed.json`（`size`、`offset`、`ids`）；每次只讀 `offset` 之後的新位元組並只解析含 `<task-notification>` 的行；檔案變小（被改寫）⇒ 從頭重掃。`_TAIL_BYTES` 只留給「最後記錄時間」用途 | `tools/lib/sessionctl/roster.py`（`_killed_ids`） |
| DEF-02 擁有者誤判活著 | 新函式 `procstop.owner_sid_of(pid, cmd)`：①讀 `~/.claude/sessions/<pid>.json` 的 `sessionId`，且 `procStart` 與行程建立時間相符才採信；②讀不到 ⇒ 命令列只認 `-r`／`--resume`／`--session-id` 後面緊接的 UUID；③都沒有 ⇒ 空字串（不判活，不是判死）。`roster.py:210` 的 `alive` 改用它；`sid_of` 保留給 `_windows()` 顯示並改名 `first_uuid_of` 以免再被誤用。**「相符」的定義（r2，當回合現查）**：Windows 主路徑＝GetProcessTimes 的 creation FILETIME（100ns 單位；Python 以 ctypes `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)`＋`GetProcessTimes`）與 `procStart` **全等**（實測 pid 15660：兩者皆 134395057212197555）；GetProcessTimes 取不到（權限）才退用 CIM `CreationDate`，容差 \|Δ\| <10（DMTF 字串只到微秒，實測得 …550，差 5）；兩者皆取不到 ⇒ 跳過 ①。**非 Windows**：`procStart` 的單位與時基未現查，不猜 ⇒ 一律跳過 ①，直接走 ②／③（降級，不判活不判死）。另：同一 `sessionId` 可對應多個 `<pid>.json`（實測 15660 與 22096 皆為 31ea79d4、兩行程都活著），任一檔通過比對即判活；`kind` 欄不能用來區分互動與 print（實測 `claude -p` 也寫 `kind=interactive`，區別在 `entrypoint`＝`sdk-cli`），判活不讀這兩欄 | `tools/lib/sessionctl/procstop.py`、`roster.py` |
| DEF-03 沙盒逐字稿目錄殘留 | 先查明成因（P6：`rmtree` 已呼叫但 `ignore_errors=True` 吞錯，且目錄 mtime 晚於案例結束 ⇒ 疑似殘存子孫行程在 cleanup 後又寫）。修法：cleanup 先以行程樹方式結束 claude 及其子孫（Windows `taskkill /T`、POSIX 行程群組），等待最多 5 秒，再 `rmtree` **不吞錯**；仍在 ⇒ cleanup 回報失敗、案例判 fail（不得假綠）。另加 `realverify sweep`：清除「slug 符合 `AutoSDD-RV-sbx-` 前綴 ∧ 對應沙盒根已不存在 ∧ `~/.claude/sessions/*.json` 沒有任何 `cwd` 指向它」的目錄 | `tools/lib/realverify/sandbox.py`、`driver.py`、入口 `tools/realverify.py` |
| quiet 無壽命上限（SA §4.6-4） | `quiet` 代理的擁有者已交棒（有 `.ack` 或 spawn 痕跡）或擁有者不活（DEF-02 新判準）⇒ 降為殘局 | `roster.py` |
| 殘局只隱藏不收斂（ARC E4c） | 殘局滿 `RESIDUE_MAX_AGE_SECONDS` ⇒ 寫一行 `retired` 到 `trace_dir()/roster/retired.jsonl`，之後 `--all` 也只顯示計數；不刪任何逐字稿 | `roster.py` |

### 7.1 同 sid 雙視窗與舊視窗有條件自動關閉（r3；審查 N-3＋掌舵者 2026-11-19 裁決；D-14）

**現查**（主控任務書，2026-11-19）：主控 pid 22096 是 09:02 park 到點以 `claude -r 31ea79d4` 開出的；舊視窗 pid 15660 是 05d1b770 交棒時開出的，同一個 sid，閒置但還活著。本棒當回合查 `park_cli.py:404-408`，到點時只判 `transcript_activity.live_driver`（逐字稿有沒有人在動），沒有查同 sid 是否還有活著的行程。所以閒置的舊窗會被當成不存在，結果同一個 sid 開了第二個行程，兩個行程寫同一份逐字稿。本棒當回合查 `~/.claude/sessions/`：只剩 `22096.json`，欄位含 `sessionId`、`procStart`、`status`（值 `busy`）、`statusUpdatedAt`，15660 已不在。

**同型洞盤點**（任務書要求）：
| 路徑 | 結論 |
|---|---|
| park 到點（`park_cli.py:404-416`） | **有洞**（本節主修）。另一個同型洞：forward 或 `--spawn` 已經開出新 session、但對方還沒 ack 時，park 只看 `.ack`（`park_cli.py:397`），仍會 `claude -r` 舊 sid ⇒ 兩個視窗動同一棵工作樹。修：到點先套 `handoff._duplicate_refusals`（`handoff.py:382`），有 spawn 痕跡就 `skip(spawned)` |
| handoff `--spawn`（`handoff.py:417-480`） | 開的是新 sid，不會有同 sid 兩個行程。舊窗留著是原本的設計，本節改成「新 session ack 後有條件自動關閉」。另一個缺點：`_duplicate_refusals` 判 spawn 痕跡的 pid 只看「行程存在」（`handoff.py:406`），pid 被重用時會誤拒。這是偏安全的錯，不會造成雙視窗，但會擋住正當的 spawn；順手改成 D-8 的身分比對 |
| forward 轉送（`forward.py` → `handoff.spawn`） | 在舊窗內觸發，開新 sid，重複保護同 `--spawn`；併入本節自動關閉的範圍 |
| 哨兵無人續跑（`claude -p -r`） | 不納入。視窗開著時 harness 自己會續接；睡眠逾約 30 分鐘時 harness 改等 Enter，這時 `-p -r` 正是設計好的補救（ADR-XPLAT-004 §2.10、OBS-SI-283）。無人窗口也不會開互動視窗 |

**五個條件**（掌舵者裁決逐字轉寫；全部成立才關）：
| # | 條件 | 判準與單一真相源 |
|---|---|---|
| ① | 確認該視窗確實是舊 session | `~/.claude/sessions/<pid>.json` 的 `sessionId`＝舊 sid，且 `procStart` 與 GetProcessTimes creation FILETIME **全等**（D-8 比對法；這裡**不退用** CIM 容差，取不到就不關）。（r4）**只關互動視窗**：登記檔 `entrypoint`＝`cli` 才是關閉目標；`sdk-cli`（同 sid 的無人 `claude -p -r`）或欄位缺失、值不認得 ⇒ 不是目標。這裡讀 `entrypoint` 只用來**排除**關閉目標，不用來判活（D-8 判活仍不讀它）；同 sid 若有活著的 `sdk-cli` 行程，park 視同 `live_driver`，直接 skip |
| ② | 舊視窗閒置 | （r4 改寫）三項全成立：(a) 登記檔 `status` 欄存在且值＝`idle`；欄位缺失、或值不是本稿認得的值（`idle`、`busy`）⇒ **不成立**（D-8「內部格式」紀律：看不懂就不關）；(b) 名冊（`roster.py`）裡舊 sid 沒有 running 的背景子代理；(c) 舊 sid 沒有 running 的**非保溫背景 shell**。(c) 的算法與名冊同源：讀舊 sid 逐字稿中 `run_in_background` 的 Bash／PowerShell 呼叫，扣掉已收到完成或 killed 通知者，剩下的命令列若不符 `roster.py` 的 `WATCH_CMD_RE`／`KEEPWARM_CMD_RE`（例如 `sessionctl runlong`、`tools/ci_wait.py`、測試全套）⇒ 不閒置。只有純保溫 shell（keepwarm、watch）不算，它們會隨行程樹一起結束 |
| ③ | 掌舵者最後一次在舊視窗打字，距今超過 `AUTOSDD_OLDWIN_QUIET_MINUTES`（出廠 5 分） | 舊 sid 逐字稿的最後一筆真人 user 記錄。「真人提示」的分類沿用 `forward.py` 判定可轉送真人提示的同一個函式；`<task-notification>`、tool_result、`auto-continuation`、hook 注入都不算 |
| ④ | 新 session 已確認接手，並寫出第一筆記錄 | 跨 sid（`--spawn`、forward）：交接包有 `.ack`，而且新 sid 逐字稿至少有一筆 assistant 記錄。同 sid（park 續跑）：關閉後 `claude -r` 在限時內寫出新記錄。這是事後驗證，結果寫進痕跡（失敗處置見下） |
| ⑤ | 只在 Windows 上執行 | 其他平台只提醒、不關：在 SessionStart 簡報與 `sessionctl status` 印「舊視窗 pid=… 仍開著，請手動關閉」 |

**執行者與時點**：
| 範圍 | 誰關 | 何時 |
|---|---|---|
| `--spawn` 後的舊窗 | 新 session 執行 `handoff --ack` 時，同一個指令內呼叫 `oldwin.close_if_eligible(old_sid, new_sid)` | ack 當下 |
| forward 轉送後的舊窗 | 同上（轉送開出的新 session 一樣以 ack 確認接手） | ack 當下；通常卡在 ③（掌舵者剛剛才在舊窗打字），改由重試排程處理 |
| park 同 sid 續跑（`park.fire_route`＝RESUME，即 `claude -r` 原 sid） | park 到點的排程行程（`park_cli.fire`） | `live_driver` 檢查之後、`claude -r` 之前；**先關、再開**，不跳過 |
| park 開新 session（`park.fire_route`＝FIRE_SPAWN，帶交接包開新 sid） | 新 session 執行 `handoff --ack` 時（同 `--spawn` 列） | ack 當下。（r4）此路開的是新 sid，不會有同 sid 兩個行程，所以**不適用「先關再開」**：park 到點只做既有的 skip 判斷（已 ack、已 spawn、`live_driver`、否決），然後照常 spawn；舊窗的關閉走跨 sid 的 ack 路徑 |

**重試（r4 統一為 3 次，所有範圍同一規則）**：條件 ②／③ 不成立時（舊窗忙、或掌舵者剛打過字），或 TOCTOU 重驗失敗時（見「怎麼關」第 5 點），不關、也**不開**第二個同 sid 視窗，而是重試，**每個交接包至多 3 次**，每次五個條件與否決全部重判：
- 跨 sid（`--spawn`、forward、park FIRE_SPAWN）：登記一次性重試排程 `AutoSDD_OldWinClose_<舊 sid 8 碼>_<HHmm>`。觸發時刻＝③ 會成立的最早時刻＋1 分；② 或 TOCTOU 不成立時＝現在＋`AUTOSDD_OLDWIN_QUIET_MINUTES`。憑證同樣是排程器自報的 NextRunTime。
- 同 sid（park RESUME）：不另建 `AutoSDD_OldWinClose_*`，由 park 把自己的到點排程重排到同一個觸發時刻（憑證＝重排後的 NextRunTime）。這一次重排就算一次重試；舊稿「重排一次」的說法作廢。
- 3 次都不成立 ⇒ 放棄並留痕：跨 sid 在新 session 的 SessionStart 出聲「舊窗保留（原因）」；park RESUME 寫 failed handback（`park_cli.py:421` 既有路徑）。
- ①不成立（身分驗不到）一律不關、不重試，只留痕：驗不到身分時，不得當成「可以關」。否決成立（見下）一律不關、不重試。

**`留：` 否決（r4，D-17）**：
- 寫入點：`sessionctl_guard.py` 的 UserPromptSubmit 已把 `留：`（全形或半形冒號）開頭的提示原文送進本視窗（`tools/lib/sessionctl/forward.py`）。r4 在同一判斷分支多做一件事：若本視窗的 sid 名下有「自動關閉可能作用的交接包」（已封存、已 spawn、或已 ack 者中最新的一份；park 情形為 park 綁定的那一份），就寫否決檔 `trace_dir()/oldwin/veto/<交接包 stem>.json`（`sid`、交接包路徑、提示時間、逐字稿路徑），並在 `trace_dir()/oldwin/events.jsonl` 寫 `oldwin_keep_veto`。名下沒有交接包 ⇒ 不寫（沒有東西可否決）。判準與寫入住 `oldwin.py::record_keep_veto`，`forward.py` 只呼叫它，hook 檔不改。
- 效力：**永久**、只綁該交接包。`eligible()` 在五條件之前先查否決檔，存在即回 false（理由 `kept_by_user`）；重試排程觸發時看到否決 ⇒ 刪除自己、不再登記、在新 session 出聲一次「掌舵者以『留：』保留舊窗」；park RESUME 到點看到否決 ⇒ `skip(kept_by_user)`，不 `claude -r`、不重試（掌舵者正在舊窗裡，舊窗本身就是駕駛），並寫 handback 說明。程式不刪否決檔；`oldwin --sweep` 也不碰它。之後新的交接包不受影響（掌舵者若又在新的舊窗打 `留：`，再寫一份）。
- 與掌舵者裁決的關係：只多一種「不關」的情形，五條件一條都沒放寬，所以不違反「有條件自動關」；它保護的正是掌舵者明說要留下的視窗。

**`AutoSDD_OldWinClose_*` 的現查與回收（r4）**：
- `sessionctl status` 的排程區列出 `AutoSDD_OldWinClose_*`（與 `AutoSDD_OpenItem_*` 同區），每列印 NextRunTime、LastRunTime、狀態（`pending`／`stale`；`stale`＝NextRunTime 為空且已執行過，或對應交接包已否決、已關閉、已放棄）。
- 回收由三處負責，不留給人：①每次重試行程在結束時（不論結果，`finally`）刪除自己這一個工作；②登記新的重試前，先刪掉同一個舊 sid 前綴的既有工作（同一舊窗只會有一個待觸發的重試）；③`handoff --ack`、`oldwin --retry` 啟動時在行程內順手執行 `oldwin --sweep` 的邏輯，刪除所有 `stale` 工作。各期收尾窗口另手跑一次 `python tools/sessionctl.py oldwin --sweep` 並附末行。沙盒 E2E 用前綴 `AutoSDD_OldWinCloseSbx_<沙盒 8 碼>_`：前綴讀資料檔 `trace_dir()/oldwin/task_prefix`（檔不存在＝出廠 `AutoSDD_OldWinClose_`；RealVerify 沙盒的 trace_dir 本來就與真機分開，由沙盒寫入專屬前綴），不開測試用環境變數鉤，也不與真的工作混在一起。

**怎麼關（先砍子行程樹，不是只砍 claude.exe）**：
1. 關之前先寫痕跡 `trace_dir()/oldwin/events.jsonl` 的 `oldwin_close_intent`，內容含 pid、`procStart`、舊／新 sid、五個條件的證據、要砍的子孫清單。
2. 用 `OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION)` 開舊窗 claude 行程的 handle，**在 handle 上**重驗 GetProcessTimes＝`procStart`。之後所有動作都對 handle 做，不再用 pid，所以 pid 被重用也砍不到別人。
3. 子孫：用 Toolhelp32 快照沿 parent pid 往下找，只收「建立時間 ≥ 父行程建立時間」的子孫。這可以擋掉 pid 被重用、只是碰巧掛在同一個 parent pid 底下的無關行程。每個子孫一樣開 handle、驗建立時間。從葉節點往上 `TerminateProcess`，最後才砍 claude 本體。
4. WHY 要砍整棵樹：只砍 claude.exe 會留下孤兒背景 shell（keepwarm、watch、runlong）。它們會繼續寫痕跡、持有保溫錨與鎖，正是名冊殘局的成因之一（§7 DEF-03 同型）。主控台宿主（conhost／OpenConsole）不主動砍；claude 結束後它會自行關閉。5 秒內確認舊 pid 已不在。
5. 砍錯行程的防護（任一不成立就中止，並寫 `oldwin_close_refused`）：①的身分全等；映像名（`QueryFullProcessImageName` 的檔名）屬於 `{claude.exe, node.exe}`；目標不是呼叫者自己或它的祖先；目標登記檔的 `sessionId` 不等於呼叫者自己的 sid（跨 sid 情形）；登記檔不存在一律不關。
   **TOCTOU 重驗（r4）**：五條件的判斷與第一個 `TerminateProcess` 之間隔著列子孫、開 handle 等步驟。所以在**第一個** `TerminateProcess` 之前（任何子孫被砍之前）再做一次重驗：重讀登記檔（`status` 仍為 `idle`、`procStart` 未變）、重讀舊 sid 逐字稿尾段（第一次判斷之後沒有新的真人 user 記錄、沒有新的 `run_in_background` 呼叫）、重查否決檔。任一變了 ⇒ 中止並寫 `oldwin_close_refused(reason=toctou_<項>)`，計一次重試。重驗之後到砍完整棵樹之間只剩 `TerminateProcess` 呼叫，不讀檔、不等待（上界 1 秒）；這個殘餘窗口就是設計上接受的最小值。
   **設計取捨：輸入框中未送出的文字會遺失**。掌舵者在舊窗打了字但還沒按 Enter，這段文字不在逐字稿、不在登記檔，任何外部判準都看不到；關閉後就沒了。降低風險的是條件 ③：最後一次**送出**距今要超過 `AUTOSDD_OLDWIN_QUIET_MINUTES`，而且交棒後舊窗收到的送出會被 forward 轉送或「已交棒」告知（ADR-XPLAT-004 §2.18），掌舵者在舊窗開始打字通常緊接著送出，送出就會讓 ③ 重新計時、讓 TOCTOU 重驗中止。想完全保住舊窗的人有兩條路：送一句 `留：`（D-17 否決），或設 `AUTOSDD_OLDWIN_AUTOCLOSE_OFF=1`。新 session 的關閉出聲文字明寫「舊視窗輸入框中未送出的文字不會保留」。
   **E2E 沙盒圍籬（r4 改寫，TCS §4.1）**：不寫死任何 sid。案例開始與結束各取一次快照：①`~/.claude/sessions/*.json` 中**不是本案例建立**的全部登記檔（`pid`、`sessionId`、`procStart`、`entrypoint`）；②全部 `claude.exe`／`node.exe` 行程（pid、建立時間）。「本案例建立」＝案例自己 spawn 的行程，或登記檔 `cwd` 在沙盒根之下。判準：(a) 案例內所有 `TerminateProcess` 目標（`oldwin_close_intent` 與 `oldwin_closed` 逐筆記錄）都必須屬於本案例建立的集合；(b) 開始快照中非本案例的 `entrypoint=cli` 登記檔，結束時必須以相同 `pid`＋`procStart` 仍在；(c) 開始快照中非本案例、結束時已不在的 `claude`／`node` 行程，逐筆列入證據，且不得出現在 (a) 的目標記錄中。(a)(c) 任一違反 ⇒ 案例 fail；(b) 違反 ⇒ 案例 fail（原因標「外部互動視窗在案例期間變動，須重跑」，不算綠）。
6. 關完寫 `oldwin_closed`（或 `oldwin_close_failed`），並追加到 `trace_dir()/oldwin/<新 sid>.notice.jsonl`。

**新視窗出聲**：ack 當下關的，`handoff --ack` 的輸出直接印「已關閉舊視窗 pid=…（sid …）」。由重試排程或 park 關的，新 session 透過已註冊的 hook 讀未讀的 notice 並出聲一次：SessionStart 簡報（`session_brief.py`）、`sessionctl_guard.py` 的 UserPromptSubmit 與 Stop `systemMessage`。不新增任何 hook 註冊。park 續跑時，新開的 `-r` 視窗與舊窗同 sid，所以 notice 以 sid 為鍵。

**開關**：`AUTOSDD_OLDWIN_AUTOCLOSE_OFF=1` 會整個停用，退回「只提醒」。`AUTOSDD_SESSION_SWITCH_MODE` 不是 `auto`，或設了 `AUTOSDD_UNATTENDED` 時，同樣只提醒。停用時 park 同 sid 續跑遇到活著的舊窗，不開第二個同 sid 視窗：沿用上述重試；3 次後寫 failed handback。

**④ 事後驗證失敗（park）**：舊窗已關、`claude -r` 卻沒寫出新記錄時，寫 `park_resume_failed` 與 failed handback（`park_cli.py:420-422` 既有路徑）。逐字稿完整保留，任何人都能 `claude -r <sid>` 接回。這是「先關再開」唯一的代價；和兩個行程寫同一份逐字稿相比，這個代價可以復原。

**與 forward 轉送設計的關係**：forward（ADR-XPLAT-004 §2.18 D3-4）原本假設舊窗會一直留著，掌舵者可能回去打字，所以設計了轉送與「已交棒」告知。自動關閉之後，forward 保留為三種情形的安全網：①從 spawn 到關閉之間的空檔（③ 至少要 5 分鐘）；②非 Windows、開關停用、模式非 auto；③身分驗不到而沒關的舊窗。forward 的判準本身不改，只在設計文件把它的定位從「常態路徑」改成「關閉前與不關時的安全網」（期 C 同步 ADR）。

**落點**：判準與執行住新模組 `tools/lib/sessionctl/oldwin.py`（`eligible()` 純函式＋`close_if_eligible()` 執行）；`procstop.py` 新增 `live_windows_of(sid)`（D-8 比對法）與以 handle 為基礎的 `terminate_tree_verified()`；呼叫端為 `handoff.py`（ack）、`park_cli.py`（fire）、重試入口 `python tools/sessionctl.py oldwin --retry <舊 sid>`、（r4）回收入口 `oldwin --sweep`、否決寫入 `oldwin.record_keep_veto`（由 `forward.py` 的 `留：` 分支呼叫）。

**本節判準**：TCS REQ-WP-54～59、98、101、AT-WP-70～78、85～89、E2E-WP-52～54、MU-WP-20～24、28～30、34。

與 R216 UX 棒的界面：UX 棒改 `roster.py:398-433`（`stop_message` 一類出聲函式）；本節只改 `_killed_ids`、`alive` 計算、狀態降級，**檔案相同、函式不重疊**，但仍依鐵律七排在 UX 棒 commit 之後（§11）。

**本節判準**：TCS AT-WP-40～48、AT-WP-59（procStart 比對法與非 Windows 降級）、E2E-WP-07／08／09、MU-WP-02／03／08；`sessionctl status` 對 05d1b770 類案例歸零。

---

## 8. realverify 接線

1. OIR 驅動器是 realverify 的唯一自動呼叫者（D-4）。
2. SA 的 8 個 E2E 缺口轉成新案例（家族檔名由實作窗口定，cases.json 由 WP-A6 單一持有）：R217-E2E-01→RV-KW8（long）、-02→RV-KW9（long）、-03→RV-IL1、-04→RV-H6、-05→RV-PB1、-06→RV-WB1、-07→RV-T4／T5、-08→本案以 E2E-WP-03 取代（D-4 不接 nightly，驅動器本身的 E2E 就是它）。SA c1／c2／c3 的自驗方案另成 RV-PR3（park RESUME 真開窗）與 RV-L3（hook 推回送達）。（r3，掌舵者結案判準）SA 矩陣其餘缺口與畫面類也都改成案例，不再以 human 列承接：RV-UI1（真互動視窗截圖＋OCR 比對守衛字樣）、RV-F4（轉送開出的新視窗真的讀到轉送原文檔）、RV-PP1（pre-push 快層紅時不啟動慢層）、RV-BC1（§6.1 啟動自檢真行程）、RV-SC3（REQ-SS-21 事件常數對真逐字稿重放）、RV-SK1／SK2／K2B（§8-5）、RV-OB4／OB5（14 天觀察）、RV-PX01～49（PRD §16.2 ✅ 列與 §16.6 B01～B03 的逐列案例，§15.2）。每個 TCS E2E-WP-xx 也都是一個 RealVerify 案例（§15.3），結果一律入同一本帳。
3. 每個 `long` 案例與每個從未入帳的案例在 WP-A8 開成 OIR `auto` 列並 `drive`。
4. stale-pass（D-5）：`openitems scan --stale-pass` 以 `git log -1 --format=%cI -- <家族原始檔>` 取 `T_src`，家族原始檔清單由案例模組宣告（`SOURCES` 常數）。開 `auto` 列 ⇔ 全部成立：
   - `T_src` 晚於該家族最後一筆 pass 帳列時間；
   - 該家族沒有 open／driven 列；
   - **防永動（r2）**：該家族若有 `escalated`／`listed`／`retired` 列，`T_src` 必須晚於其中最晚一筆 `escalate`（或 `retire`、或 human 化的 `convert`）事件的 `ts`——也就是 escalate 之後**出現新 commit 動到原始檔**才准重開；否則不開（舊稿每次重掃都重開，每輪再燒 `max_attempts` 次 RV）。
   觸發事件（r2 明定；兩者都零 token，皆不在 SessionStart／Stop 的延遲路徑上）：(a) 每個收尾單人窗口在其最後一個 commit 之後手跑一次（TCS §9 第 6 條，產物＝新開列的 id 清單，同窗口接著 `drive`）；(b) `run-driver` 每次啟動的第 0 步（§5.1）。不設日曆觸發。
5. （r3 改寫，D-12）事件型驗收項不再等自然事件，改由驅動器主動跑完，PASS 才入帳：
   | 項 | 案例 | 類別 | 載具與判準 | 最短牆鐘 `MIN_WALL_SECONDS` |
   |---|---|---|---|---|
   | §11.1 6 小時零 token | RV-SK1 | soak | 沙盒掛真哨兵巡邏（真排程），跑滿 6 小時；斷言巡邏 tick 數 ≥ 6h÷巡邏間隔−1、期間沙盒 spawn 的 `claude` 行程數＝0、痕跡沒有付費探針記錄 | 21,600 |
   | §11.8 24 小時／≥4 次 reset | RV-SK2 | soak | 沙盒 session 用真逐字稿格式，每約 5 小時注入一筆撞線記錄（帶觀測 reset 時刻）；真哨兵加真 schtasks 在每次 reset 後 `claude -p -r --model haiku` 續跑；斷言 4 次續跑都寫出新記錄，且每次距 reset 不超過一個巡邏間隔 | 86,400 |
   | V-K2 95～99% 帶 wake | RV-K2B | auto | 真 hook 行程。用 `quota_policy` 既有門檻鍵（`--print-env-example` 列出者），把「準備」帶下緣設在當下真實水位以下、「停止」帶設在其上，使真實讀數落在等效的 95～99% 帶；斷言出聲一次、寫出可重啟點任務書、同一 reset 窗不重複 | — |
   | E2E-SS-05 M-K2＝0（上線 14 天） | RV-OB4 | observe（`due` 2026-12-02） | 到期跑 `waste_census --switch-metrics --since-days 14`，達標即 PASS | 帳列時間 ≥ `due` |
   | V-PK5 park 14 天對照 | RV-OB5 | observe（`due` 2026-11-30） | 到期跑 `waste_census --resume-metrics --since-days 14` | 帳列時間 ≥ `due` |
   WHY 用門檻鍵不算作弊：它走的是正式設定路徑（與 E2E-WP-25 同法），被驗的是「讀數落在帶內時的行為」。真的 95% 水位能不能撞到，是額度用量的事實，不是功能。observe 列仍是一次性、綁單一 OI、到期即結或 escalate，符合附錄 A-6。未達標 ⇒ fail ⇒ 依 §5.1 走 `max_attempts`；escalate 代表 R217 未結（§15.4），不是例外。

**本節判準**：TCS E2E-WP-03、E2E-WP-10～15、E2E-WP-23、E2E-WP-42、E2E-WP-57～60、AT-WP-19、AT-WP-52、MU-WP-13。

---

## 9. AutoClaude 上場架構（期 B）

### 9.1 分工（入憲文字見附錄 A-3）
- 有人在場：互動 Claude Code 是舵手（不變）。
- 無人且 OI 有明確驗收指令：AutoClaude playbook 引擎是舵手——由 `run-driver` 委派，引擎的 `evaluator_command` 判「完成」，不是 LLM 說了算。
- 需要對話脈絡的設計判斷、文件改寫、commit：不交引擎（D-9）。

### 9.2 流程
```
OIR auto 列 ─drive─▶ AutoSDD_OpenItem_<id> 排程 ─▶ run-driver <id>
                                                     │ OPENITEMS_HELM=autoclaude？
                       否（期 A 行為）◀───────────────┤
                                                     是
                                                     ▼
          tools/lib/openitems/helm.py 生成 playbook（~/.autosdd/openitems/pb-<id>-<stamp>.yaml）
             global_goal     ＝「OI <id> 關閉」
             evaluator_command＝python tools/openitems.py check --id <id>（rc 0 ⇔ closed）
             steps           ＝①跑驗收（realverify／argv）②失敗時讀 log 判斷是環境缺件或真失敗 ③真失敗寫缺陷草稿到 handback 目錄
          ─▶ python -m autoclaude <pb>（根層 .venv、cwd＝repo、AUTOSDD_UNATTENDED=1、spawn_env）
          ─▶ 引擎 GOAL_SYNTHESIS：evaluator rc 0 ⇒ 完成；否則 escalation ⇒ run-driver 記 attempt(fail)
```
- `OPENITEMS_HELM` 住 `env.shared`（四層載入鏈），出廠 `off`；WP-B4 依 D-10 翻成 `autoclaude`。
- 引擎的 checkpoint 目錄指向 `~/.autosdd/openitems/checkpoints/`（不汙染 `AutoClaude/checkpoints/`，順帶治 H9 的同型問題）。
- 引擎內的 `claude` 步驟模型＝`tools/lib/model_roles.py` 的子代理角色（出廠 sonnet），驗收類 RV 案例自帶模型（多為 haiku）。
- 互斥：引擎啟動前與每一步之前都過 §5.1 第 2 步的讓路判準；互動 session 一出現就收尾、記 deferred。

### 9.3 前置工作包（WP-B1，期 B 第一包）
1. `storage.mode` 決策（r2 統一說法，TCS REQ-WP-60／61 同此）：OIR 舵手只用 yaml checkpoint 即可續跑（單一 OI、短任務），**不需要 PG**；`helm-check` 的必要條件不含 PG 與 alembic。PG 只在 `--last-run-summary` 與跨 run 記憶需要時才開；那時（`storage.mode`≠`yaml_only`）alembic 在 head 與 `autoclaude_pg` healthy 才升為必要條件。出廠 `yaml_only` 下兩者只當資訊列印出。
2. alembic 現查 `python -m alembic current`（AutoClaude 目錄、CI 對等 PG）列為 WP-B1 的資訊步驟：不在 head 就照 CLAUDE.md〈本機 CI 對等〉upgrade，但不擋期 B 其餘工作。判準寫入 TCS AT-WP-60／61。
3. `pkg_resources` 棄用警告：根層 `.venv` 鎖 setuptools <81 或換掉 wexpect 的 import（二擇一，WP-B1 依現查決定並寫 WHY）。
4. H9：AutoClaude 測試夾具的 checkpoint 目錄改 `tmp_path`；加回歸鎖「跑完 `tests/` 後 `AutoClaude/checkpoints/` 檔數不變」。

**本節判準**：TCS E2E-WP-30～34、AT-WP-60～66。

---

## 10. 與並行 R216 UX 棒的界面（假設它會落地）

| 面 | UX 棒（scratchpad `r216_ux_brief.md`）落地後的行為 | 本設計的依賴 |
|---|---|---|
| 退出碼 | keepwarm／watch／waitfor 正常判決一律 rc 0，判決只看末行 `*_VERDICT=`（DEF-200-622） | `run-driver` 同樣 rc 0＋末行 `OPENITEMS_DRIVER=`；watch 新增的 `skip reason=holder_running` 也是 rc 0 |
| Stop 出聲 | 只有保溫／監督 shell 時不出「仍有背景任務…TaskStop」，改正向字樣（DEF-200-623） | 完成閘的推回訊息獨立於該出聲；`midwork` 排除保溫 shell 用同一組 regex（`roster.py:400-401`） |
| 帳本 | 更正 DEF-200-604／605／609 | 本設計新缺陷從 DEF-200-624 起（收尾時現查最大號） |
| 檔案 | 改 `roster.py:398-433`、`keepwarm.py`、`watch.py`、`supervise.py`、`tools/sessionctl.py` | WP-A3／A4 必須在 UX 棒 commit 之後才動這些檔（鐵律七：同持有面不並行） |

若 UX 棒最後未落地（例如退回），WP-A4 先補做「判決 rc 0」那一半，再做本稿 §6；判準不變。

**本節判準**：WP-A3／A4 任務書寫明 UX 棒的 commit SHA 為前置；TCS AT-WP-35 斷言 `holder_running` 的 rc 為 0。

---

## 11. 工作包切分（鐵律七：鎖的持有面）

共通規則：並行包**不重釘**棘輪（`tools/tests` 行數、guard-total、`_TREE_FILE_FLOORS`）、不寫帳本、不改 CI paths；這些全部由各期收尾單人窗口做。

### 期 A（完成判準、名冊、叫醒、驅動器）
| WP | 內容 | 動到的檔（常數／史料／消費端） | 前置 | 可否並行 |
|---|---|---|---|---|
| A1 | OIR 套件骨架：`params`、`ledger`（寫入鎖、配號）、`fold`、`scan`；入口 `open／close／convert／retire／list／check／scan`；`OpenItems_Protocol/params.json` | 新：`tools/lib/openitems/{__init__,params,ledger,fold,scan}.py`、`tools/openitems.py`、`docs/06_quality/OpenItems_Protocol/params.json`、`tools/tests/test_openitems_ledger.py`、`test_openitems_scan.py` | 無 | 與 A3、A4、A6 並行（檔案不相交） |
| A2 | 驅動器：`drive`、`run-driver`、`start` 事件、憑證回讀與排程批次列舉快取（§4.5）、讓路、額度 deferral、全域互斥／每窗上限／錯開（§5.4）、observe | 新：`tools/lib/openitems/{drive,driver_run,schedcache,throttle}.py`、`tools/tests/test_openitems_drive.py` | A1 | 與 A3、A4、A6 並行 |
| A3 | 名冊 DEF-01～03＋quiet 壽命＋retire＋`realverify sweep`；（r3）§7.1 舊視窗有條件自動關閉：新模組 `oldwin.py`、`procstop.live_windows_of`／`terminate_tree_verified`、park 到點改「先關再開」與 `skip(spawned)`、`_duplicate_refusals` 身分比對、`handoff --ack` 呼叫關閉、`sessionctl oldwin --retry` | `tools/lib/sessionctl/{roster,procstop,oldwin,park_cli}.py`、`handoff.py`（只動 `_duplicate_refusals`、`ack`）、（r4）`forward.py`（只在 `留：` 分支加一行 `record_keep_veto` 呼叫）、`tools/sessionctl.py`、`tools/lib/realverify/{sandbox,driver}.py`、`tools/realverify.py`、`tools/tests/test_sessionctl_roster.py`、`test_sessionctl_oldwin.py`、`test_realverify_lib.py` | UX 棒 commit | 與 A1、A2、A6、A7 並行（A6 中依賴 A3 的 T4／T5 與 RV-WP52～54 案例那一步串在 A3 commit 之後）；**不與 A4 並行**（同為 sessionctl 持有面且 UX 棒剛動過） |
| A4 | 叫醒預算：watch 保溫模式、互斥、共用 pings、處置表 | `tools/lib/sessionctl/{watch,keepwarm,supervise}.py`、`tools/tests/test_sessionctl_watch.py`、`test_sessionctl_keepwarm.py` | UX 棒 commit、A3 收工 | 與 A1、A2 並行 |
| A5 | 完成閘＋`midwork` 保溫排除＋SessionStart 人工清單＋保溫閘讓路＋驅動器自有寫入面的兩個消費端（§5.5：handoff `_auto_owned`、SI `dirty_paths`）；（r3）佐證共用（§4.1-4）、舊窗關閉 notice 在 SessionStart／UserPromptSubmit／Stop 出聲（§7.1） | `tools/lib/openitems/gate.py`、`tools/lib/sessionctl/{midwork,handoff}.py`、`tools/lib/selfimproving/sched.py`（只改 `dirty_paths`，`OWN_PREFIXES` 不動）、`tools/lib/session_brief.py`（守衛面）、`.claude/hooks/check_pending_handoff.py`、`sessionctl_guard.py`（守衛面，子代理只產 diff 到 scratchpad，主控親套） | A1、A2、A3、A4 | 單人 |
| A6 | realverify 新案例 RV-KW8／KW9／IL1／H6／PB1／WB1／PR3／L3／T4／T5／OI1（必敗夾具）及 TCS §4 期 A 其餘 E2E 的案例化、`cases.json` 單一持有；**`cases/quota_rush.py:87-93` 未落地斷言反轉也歸 A6**（r2：cases 目錄只有一個持有者）；（r3）§8-2 新增的缺口案例（UI1／F4／PP1／BC1／SC3／SK1／SK2／K2B／OB4／OB5）與逐列案例 RV-PX01～49、每個 E2E-WP-xx 的案例化（§15.3） | `tools/lib/realverify/cases/*.py`（新家族檔＋`quota_rush.py`）、`docs/06_quality/RealVerify_Protocol/cases.json` | 無硬前置；三步串在別包之後：T4／T5 與 RV-WP52～54 串在 **A3 commit** 之後、`quota_rush.py` 反轉串在 **A7 commit** 之後、E2E-WP 案例化串在對應功能包之後 | 與 A1、A2、A3、A7 並行（檔案不相交；三個串接步驟各自等前置 commit） |
| A7 | 量測：M-WB1／M-WB2、V-P6 `--pace-metrics`／`--replay-pace-floor`；CI 鎖「待驗標記必帶 OI id」 | 新：`tools/lib/wastecensus/sections_wake.py`、`tools/tests/test_openitems_marker_lock.py`；改 `wastecensus/report.py`。**不碰** `tools/lib/realverify/**`（r2 重切：舊稿 A7 改 `cases/quota_rush.py` 與 A6 單一持有 cases 衝突，違反鐵律七） | A1 | 與 A3、A6、E1① 並行 |
| A8 | OIR 種子：26 項未結與 E6 的 143 處標記全部 `open`／`drive`／`convert`／`retire`，文件標記補 OI id | `docs/06_quality/OpenItems_Event_Ledger.jsonl`、被標記的各文件（只加 OI id，不改語意） | A1、A2、A6、A7 | 單人（寫帳本） |
| A9 | 期 A 收尾：棘輪重釘、CI paths（compat-ci 兩支）、`non_evolvable_globs`、Root_Layout §3、帳本 DEF、根層全套（runlong／waitfor）、期 A 真機 E2E 全跑入帳 | 收尾面 | 全部 | 單人 |

### 期 B（AutoClaude 上場）
| WP | 內容 | 檔 | 前置 | 並行 |
|---|---|---|---|---|
| B1 | 前置：alembic、storage 決策、setuptools／wexpect、H9 夾具與回歸鎖 | `AutoClaude/tests/**` 夾具、根 `.venv` 鎖檔 | 期 A 收尾 | 與 B2 並行（子專案 vs 根層） |
| B2 | `openitems/helm.py` playbook 生成、`run-driver` 委派、`env.shared` 新鍵 `OPENITEMS_HELM` | `tools/lib/openitems/helm.py`、`driver_run.py`、`env.shared`、`docs/06_quality/OpenItems_Protocol/playbook_template.yaml`、`tools/tests/test_openitems_helm.py` | 期 A 收尾 | 與 B1 並行 |
| B3 | 真機：DRY_RUN、真跑成功、失敗 escalate、互斥讓路 | RealVerify 新家族 `openitems_helm` | B1、B2 | 單人 |
| B4 | 翻預設（D-10：連續 3 次真跑成功）、期 B 收尾 | `env.shared`、收尾面 | B3 | 單人 |

### 期 C（PRD 補登與文件陳舊）
| WP | 內容 | 檔 | 前置 | 並行 |
|---|---|---|---|---|
| C1 | PRD 修憲（附錄 A 全部列）、§16.6 補登 8 族；v2.1.22 修訂表 QA 座標（SA a15）與 §16.2 A47／A48 兩列（PRD:2696、:2720）的陳舊字面**只以追加註記處理、原文一字不動**（附錄 A-1、A-10；PRD:2776、N1 判例 PRD:2764） | PRD | 期 A、B 收尾（✅ 條件要有證據） | 單人（收尾窗口） |
| C2 | 文件陳舊清理（SA a14、C21 `hold_set`）、G3 退役註記（D-6）；PRD 不在本包 | ADR-XPLAT-004、TCS-SessionCtl／Park／SessionSwitch、帳本 DEF-200-594／596／597 | C1 | 與 C3 並行（檔不相交） |
| C3 | ADR-XPLAT-004 新 §2.20 工作推進軸；根 CLAUDE.md〈收尾常態規則〉加「第七類停＝宣告式完成」、機械守衛總表 `check_pending_handoff` 列補完成閘、現查速查表加 `openitems` | ADR、根 CLAUDE.md | C1 | 與 C2 並行 |

### 新增一包：全量 E2E 執行與對照表（r3，掌舵者結案判準）
| WP | 內容 | 檔 | 前置 | 並行 |
|---|---|---|---|---|
| E1 | ①對照表產生器與鎖（§15）：`realverify coverage`、母體 `prd_population.json`（100 條＋TCS REQ-WP 全部）、產出 `docs/06_quality/PRD_E2E_Coverage_Table.md`、CI 鎖 `test_realverify_prd_coverage.py`、PASS 債棘輪 `pass_debt`；②全量執行：把每個未 PASS 的 E2E 開成 OIR `auto`／`observe` 列並 `drive`，由驅動器跑完；long、soak、observe 案例不得在互動 session 用縮短參數代跑；③結案：`realverify coverage --require-pass` rc 0 並入證據檔 | 新：`tools/lib/realverify/coverage.py`、`docs/06_quality/RealVerify_Protocol/prd_population.json`、`docs/06_quality/PRD_E2E_Coverage_Table.md`（產物）、`tools/tests/test_realverify_prd_coverage.py`；改：`tools/realverify.py`（加動詞）；（r4）`tools/lib/realverify/ledger.py`（「執行案例」欄、寫帳後重產對照表，D-16／D-18）、`runner.py`（`ASSERTS` 未寫出即判 fail，D-15）、`docs/06_quality/RealVerify_Protocol/coverage_params.json`（`min_wall_seconds`） | ①：A3 commit，且 A6 的 `cases.json` 已登記全部案例 id（含 planned）。②：期 A、B、C 全部收尾。③：②全部 PASS | ①與 A7 並行（檔案不相交）。①另以 A3 commit 為前置，因為 `tools/realverify.py` 與 A3 的 `sweep` 同檔；②③單人 |

**本節判準**：每個 WP 的任務書含「前置 SHA、持有面、不准碰、交卷判準（TCS 對應編號）」；任兩包的並行欄彼此對稱（甲列寫可與乙並行 ⇔ 乙列也寫甲，r3）；A3／A4 不並行；`tools/lib/realverify/cases/**` 與 `cases.json` 只出現在 A6 的 commit；所有棘輪重釘只出現在 A9／B4／C 收尾的 commit。

---

## 12. 模組落點表（照 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）

| 元件 | 路徑 | §2 格 |
|---|---|---|
| 函式庫（新套件） | `tools/lib/openitems/`：`params`、`ledger`、`fold`、`scan`、`drive`、`driver_run`、`schedcache`、`throttle`、`gate`、`helm`（期 B） | 函式庫（兩支以上、已排定後續階段 ⇒ 第一天成套件） |
| 指令入口 | `tools/openitems.py`，動詞：`scan`、`open`、`drive`、`run-driver`、`check`、`close`、`convert`、`retire`、`list`；期 B 加 `helm-check`（§9.3-1、REQ-WP-60）與 `helm-status`（D-10、REQ-WP-66）（r3 補列）。另有兩個既有入口加動詞：`tools/realverify.py` 加 `sweep`（§7 DEF-03）與 `coverage`（§15）；`tools/sessionctl.py` 加 `oldwin --retry`（§7.1） | 指令入口薄殼 |
| 既有套件新模組（r3） | `tools/lib/sessionctl/oldwin.py`（§7.1）、`tools/lib/realverify/coverage.py`（§15） | 既有套件內模組（不另開根層套件，D-13） |
| 量測 | `tools/lib/wastecensus/sections_wake.py`（入口仍是 `tools/probe/waste_census.py`） | 既有 wastecensus 套件 |
| 測試 | `tools/tests/test_openitems_ledger.py`、`test_openitems_scan.py`、`test_openitems_drive.py`、`test_openitems_gate.py`、`test_openitems_marker_lock.py`、`test_openitems_helm.py`；r3 加 `test_sessionctl_oldwin.py`（A3 階段）、`test_realverify_prd_coverage.py`（E1 階段）。期 A 新增 6 檔超過「每階段 ≤3 檔」⇒ 期 A 拆三階段收：A1／A2 三檔、A3 一檔、A5／A7 兩檔，各自重釘；E1 自成一階段 | 測試 |
| 協定資料 | `docs/06_quality/OpenItems_Protocol/params.json`、`playbook_template.yaml`；r3 加 `docs/06_quality/RealVerify_Protocol/prd_population.json`（對照表母體）與同目錄 `coverage_params.json`（例外白名單、`pass_debt` 棘輪、（r4）`min_wall_seconds`） | 執行期協定資料 |
| 產出物（r3） | `docs/06_quality/PRD_E2E_Coverage_Table.md`（由 `realverify coverage --write` 產生，檔頭標「程式產生、勿手改」） | 審查／RTM（06） |
| 事件帳本 | `docs/06_quality/OpenItems_Event_Ledger.jsonl` | 事件帳本（機器寫） |
| 規格 | 本稿；`docs/03_testing/contracts/TCS-WorkProgress-20261119.md` | 需求／設計、測試契約 |
| 守衛面接線（主控親套） | `.claude/hooks/check_pending_handoff.py`（完成閘）、`sessionctl_guard.py`（保溫閘讓路）；`tools/lib/session_brief.py`（人工清單） | 守衛面 |
| CI 接線 | compat-ci 兩支 workflow 的 `paths` 加 `tools/lib/openitems/**`、`tools/openitems.py` | CI 接線 |
| 不可進化面 | `tools/lib/openitems/**` 列入 `SelfImproving_Protocol/params.json` 的 `non_evolvable_globs`（守衛類模組） | 不可進化面 |
| 驅動器自有寫入面 | `OpenItems_Protocol/params.json` 的 `driver_own_prefixes`＝OIR 事件帳本＋`RealVerify_Result_Ledger.md`＋（r4）`PRD_E2E_Coverage_Table.md`；**不**併入 SI 的 `tools/lib/selfimproving/sched.py:34` `OWN_PREFIXES`（r2 更正：舊稿誤寫 `_OWN_PREFIXES` 且漏 RealVerify 帳）；消費端界面見 §5.5 | 執行期資料目錄規則 |

**本節判準**：`tools/tests/test_root_module_layout.py` 在 A9 收尾後綠；`test_ci_paths_cover_root_consumers.py` 綠。

---

## 13. 被否決的方案

| 方案 | 否決理由 |
|---|---|
| 擴充 midwork 詞表收「完成／沒有剩下」 | 打地鼠；措辭不是狀態，「沒有需要你決定的事」也可為真（ARC §8.4） |
| 讓保溫叫醒順便推進待驗項 | 在主控大上下文裡做工＝最貴的地方；E2E-SS-04 正需要不保溫（ARC S11） |
| 把待驗項塞回 §16.2 母體 | 復活 v2.1.17 拆掉的覆蓋度永動源（PRD:2659） |
| nightly 加 realverify stage（SA a1 原提案） | D-4：跨檔字面鎖、nightly 現紅、週期重跑燒額度 |
| 完成閘只看「本 session 開的 OI」 | 歸屬判定要在 SessionStart 記 HEAD 或改 hook，成本高；undriven 按定義無主，全域判準更簡單且一旦驅動即安靜 |
| 人工清單滿額就阻斷 | 把人工項變成新的阻斷永動源；改為出聲（§5.3） |
| `sid_of` 改取「最後一個 UUID」 | 仍是猜；harness 已有 pid→sessionId 登記檔可直接讀（D-8） |
| 殘局直接刪逐字稿 | 刪的是史料與證據；只記 retired、不再列 |
| AutoClaude 接管互動續航／文件改寫 | 重造 harness 能力（§15.2「先採用」）；需要對話脈絡；無人 commit 未裁決（D-9） |
| 子代理收卷後主控自動 SendMessage 續推 | 冷代理續棒被成本閘擋，且不解決無驅動器 |
| 引擎試用期「一週」 | 日曆觸發；改連續 3 次真跑成功（D-10） |
| （r3）park 到點遇到同 sid 活窗就 `skip(live_window)` | 舊窗一直開著時，park 永遠不觸發，又是一個空窗；掌舵者裁決改為有條件先關再開（D-14） |
| （r3）只砍 claude.exe、不砍子行程 | 背景 shell 會變成孤兒，繼續持有保溫錨與鎖、寫痕跡（§7.1「怎麼關」第 4 點） |
| （r3）以 pid 直接 `taskkill /T /PID` | pid 可能被重用；改成在 handle 上驗建立時間後才終止（§7.1 第 2、3 點） |
| （r3）`window_cap`／`quota` 照舊計入 deferrals | 排隊會把正常列推進人工清單（審查 N-2，D-11） |
| （r3）§11.1／§11.8／V-K2 等自然事件 | 不保證會發生，永遠拿不到 PASS 帳列（D-12） |
| （r3）對照表手寫維護 | 掌舵者判準明定由程式產生；手寫會與帳本漂移（§15.4） |

**本節判準**：每列在 TCS 有一個反向 AT 或 MU 防止回到被否決形態（MU-WP-01、07、02、AT-WP-24；r3：MU-WP-18、20、22、23、26、27）。

---

## 14. Token 帳（依 ARC §6-6 與 E3 實數；推論標明）

- 主控上下文 C≈30 萬時，一次冷重寫≈C×1.25≈37.5 萬加權；保溫叫醒 3 回合≈9～10 萬（ARC E3）。
- 拿掉 all_done 重複叫醒：8/21＝38% 叫醒消失（推論：以 E3 的 14.5 小時計，省約 8×3×C×0.1≈72 萬加權）。
- 一叫一回合：每次保溫叫醒省 2×C×0.1≈6 萬。
- auto 驅動器在沙盒跑，主控成本≈0；單一 RV 案約 10 萬級（推論，ARC §6-6），遠小於一次主控冷重寫。
- 扇出上界（r2，§5.4）：任一 reset 窗內驅動器至多 `max_runs_per_window`（2）次執行、同時至多 1 支；最壞花費＝2×單一案例上限，與 OIR 列數無關（A8 種下幾十列也一樣）。
- 量測口徑：M-WB1、M-WB2（§6.4）、OIR undriven 數（`openitems list --undriven`）。

**本節判準**：上線後以 `python tools/probe/waste_census.py --since-days 14` 與 M-WB 系列重量，入 R217 證據檔。

---

## 15. PRD 全功能 E2E 對照表與 R217 結案判準（r3；掌舵者 2026-11-19 再指令）

掌舵者原話：「請確認AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md 所有功能都有E To E 完整驗證程式, 並完請成的E To E所有測試!」判準全文在 scratchpad `r217_acceptance_rule.md`，本節把它落成可機械判定的形式。

### 15.1 母體（`docs/06_quality/RealVerify_Protocol/prd_population.json`）
- 內容：SA 矩陣 100 條（R217-REQ-A01～A54、B01～B03、C01～C21 含 C03b／C08b、D01～D20），加上 TCS-WorkProgress 的全部 REQ-WP。每條一筆：`id`、`prd`（PRD 章節座標，或 ADR／TCS 座標）、`class`、`e2e`（RealVerify 案例 id 陣列，至少 1 個）、`why`。
- `class` 只有三種值：`normal`（必須有 E2E 且 PASS）、`decision_retired`（掌舵者裁決不實作）、`human`（只能由人裁決）。後兩種只准出現在 `coverage_params.json` 的白名單裡：C02（軟線，`SessionSwitch_CostModel_Design.md:307` D-1）、C14（hold，同檔 `:308` D-2）、A53（§13 法務）、A54（A7 無人 commit／push）。每筆必須附裁決座標與理由（TCS §10）。白名單外出現非 `normal` ⇒ 鎖紅。
- 母體是資料，不是對照表本身。它由 E1① 依 TCS §10 一次建立，之後只由「新增條目」的同一個 commit 擴充。

### 15.2 PRD §16.2 ✅ 列與 §16.6 B01～B03 的逐列案例（RV-PX01～49）
SA 把 A01～A46 標為「完備（PRD 自帳；本棒未逐列重驗）」，而且 E2E 欄只寫「部分有 RV」。依掌舵者判準，每條都要有自己的 E2E，所以逐列配 `RV-PXnn`。（r4 改寫，審查 P2-1：舊稿「A6 實作時再判斷是否已有既有案例」是之後再看）本版已逐列讀 PRD 對應列（§16.2 列文字與 R211 矩陣列），在 TCS §10.3 附錄寫定每列的**案例 id、載具類型、輸入、斷言鍵與可觀測判準**，共 49 列（A01～A46、B01～B03），完成 49／49。其中三列改指同一份載具的另一案例（A17→RV-PX12、A19→RV-PX13、A37→RV-PX34，斷言鍵相同、`refs` 加該 PRD 座標）；A08 不再改指 RV-A1（RV-A1 驗的是引擎長睡外部續跑＝A48，不是 §4.5.5 的規劃器排程面），改開 RV-PX08。附錄另列「載具前提」與其預定退路，以及唯一一處無法真實誘發的分支（A13／A19 的空間不足拒絕分支）與其理由。實作窗口不得改動附錄的斷言鍵；要改就先改 TCS，CI 鎖（§15.5）以附錄為準。

### 15.3 E2E-WP 與 RealVerify 的關係
TCS 的每個 E2E-WP-xx 都是一個 RealVerify 案例：已點名案例者沿用該 id（例：E2E-WP-10＝RV-KW8），其餘一律以 `RV-WPxx` 為 id、家族 `workprogress`；`cases.json` 的 `refs` 必含 `E2E-WP-xx`。所以 TCS 全部 E2E 的結果都落在同一本 `RealVerify_Result_Ledger.md`。

### 15.4 產生器、鎖與結案判準
| 項 | 規則 |
|---|---|
| 產生器 | `python tools/realverify.py coverage [--write｜--check｜--require-pass]`：讀母體、`cases.json`、結果帳，輸出 `docs/06_quality/PRD_E2E_Coverage_Table.md`，欄位為「條目 → PRD 座標 → E2E id → 最近一次 PASS 帳列（時間＋選取）→ 最近一次結果 → 狀態」。檔頭標「程式產生、勿手改」，可重跑，同樣輸入產出逐位元組相同 |
| 帳列格式（r4，D-16） | 結果帳新增第 8 欄「執行案例」：本次 `run` **實際執行**的案例 id（逗號分隔、依執行順序；被 `--long` 篩掉或因前置缺件未執行者不列，另以「略過：id(原因)」寫在同欄末尾）。寫入者＝`tools/lib/realverify/ledger.py`（唯一寫入點）。既有 7 欄舊列一字不改（帳本檔頭「勿手改既有列」） |
| 帳列判讀（r4 改寫） | 一個帳列只對「執行案例」欄**列出的 id** 有效：結果 pass 且該 id 不在「失敗案例」欄 ⇒ 該案例 PASS；在失敗案例欄 ⇒ fail。舊格式（7 欄）帳列只在「選取」恰為單一案例 id 時對該 id 有效；`family=…`、`all` 的舊列對任何案例都**不算**（無法得知 long 案例有沒有被篩掉——這正是舊判讀的假綠）。「最近一次結果」取最晚的有效帳列。另外三個條件，不符的 PASS 不算：①long、soak 案例：帳列「秒數」≥ 該案例的 `MIN_WALL_SECONDS`；②long、soak、observe 案例：必須與 OIR 對帳——存在一筆 `attempt(result=pass)`，其 `evidence` 引用此帳列的時間戳與案例 id，且同一 `drive_seq` 的 `start.ts` 早於帳列時間減「秒數」、`attempt.ts − start.ts ≥ MIN_WALL_SECONDS`（observe 另要求帳列時間 ≥ `due`）——互動 session 手跑的 long 列沒有 OIR 事件，結構上不算；③帳列證據欄須含該案例 `ASSERTS` 的每個鍵（§15.5）。「已排程」不寫帳列，所以結構上不可能算 PASS |
| `MIN_WALL_SECONDS` 與兩道鎖（r4，D-16） | 每個 `long` 或 `KIND="soak"` 案例模組**必須**宣告 `MIN_WALL_SECONDS`（缺 ⇒ 鎖紅、執行器拒跑）。數值釘在 `coverage_params.json` 的 `min_wall_seconds`（以案例 id 為鍵；鍵集合必須恰等於全部 long／soak 案例），模組值必須與它相等（執行器在執行期也比對，不等即 fail）。下修兩道鎖：①**結構下界**——模組另宣告 `DESIGNED_WAIT_SECONDS`（案例設計中所有等待的總和，例：RV-KW8＝45＋55 分＝6,000），要求 `MIN_WALL_SECONDS ≥ 0.9 × DESIGNED_WAIT_SECONDS`；案例執行時把實際各段等待秒數寫進證據，總和 < `DESIGNED_WAIT_SECONDS` 即 fail，所以改小 `DESIGNED_WAIT_SECONDS` 就等於改案例行為，會在 diff 與真跑中現形；②**棘輪下界**——`tools/tests/test_realverify_prd_coverage.py` 內的 `_MIN_WALL_FLOOR` 表，`coverage_params.json` 的值只准 ≥ 該表；該表只准收尾單人窗口重釘，且只准上調（同檔另一測試把它與 `coverage_params.json` 的 git HEAD 版本比較，任一鍵下降即紅） |
| 對照表重產（r4，D-18） | 兩個寫入點，產物永遠跟帳本同步：①`ledger.py` 追加帳列後，在同一行程內呼叫 `coverage.write()`（不開子行程；母體或參數檔讀不到 ⇒ stderr 一行、帳列仍保留）；②`run-driver` 第 7 步寫完 OIR 事件後跑 `realverify coverage --write`（§5.1）。互動 session 手跑 `realverify run` 走的也是 ①。三檔（兩本帳＋產物）屬驅動器自有寫入面（§5.5），由下一個有人窗口同一個 commit 提交；CI 鎖 (d) 對三者不同步即紅 |
| CI 鎖（零容忍） | `tools/tests/test_realverify_prd_coverage.py`：(a) 從 PRD §16.2 表列、PRD:2690 的 ✅ ID 清單、§16.6 各列、TCS-SessionSwitch 的 REQ-SS、TCS-WorkProgress 的 REQ-WP 解析出條目集合，必須 ⊆ 母體鍵集合 ⇒ **新增 PRD 條目卻沒有母體列（也就沒有 E2E）就紅**；(b) 每個 `normal` 條目的 `e2e` 非空，且每個 id 都在 `cases.json`（planned 也算登記）；(c) 非 `normal` 只准白名單內；(d) `coverage --check`：產物與重新產生的結果相同；(e) 改指既有案例時，該案例 `refs` 必含此條目的 PRD 座標；（r4）(f) 斷言鍵一致（§15.5）；(g) `MIN_WALL_SECONDS` 宣告完整、與 `coverage_params.json` 相等、不低於結構下界與 `_MIN_WALL_FLOOR`；(h) `_MIN_WALL_FLOOR` 不低於 git HEAD 版 `coverage_params.json` |
| PASS 債棘輪 | `coverage_params.json` 的 `pass_debt`＝目前沒有 PASS（或最近一次結果不是 pass）的 `normal` 條目集合。測試要求實測集合 ⊆ `pass_debt`，所以只能縮小、不能新增。重釘只准收尾單人窗口做 |
| R217 結案 | `realverify coverage --require-pass` rc 0：全部 `normal` 條目的每個 E2E，在結果帳裡最近一次結果都是 PASS，且符合 long／soak／observe 的條件；`pass_debt` 為空。escalated 的 OIR 列代表 R217 未結，不是例外。例外只有白名單 4 條 |

### 15.5 空殼案例的防線（r4，D-15）
- 宣告：RV-PX01～49、RV-WPxx 與 §8-2 列出的每個 R217 新案例，模組都要宣告 `CARRIER`（載具代號字串，取值見 TCS §10.3 代號表）與 `ASSERTS`（斷言鍵的 tuple，≥1 個）；被母體改指的既有案例（例：RV-A1 承接 A47／A48）同樣要補宣告，補之前 E1 鎖判它為空殼。
- 執行期（`runner.py`）：案例以 `ctx.evidence(key, value)` 寫證據；案例回 pass 時，若 `ASSERTS` 中有任何鍵沒有寫出非空值 ⇒ 執行器把結果改判 fail，失敗原因 `assert_missing:<鍵>`。證據以 `鍵=值` 寫入帳列證據欄。所以只有 id、沒有斷言的案例拿不到 PASS。
- CI（`test_realverify_prd_coverage.py` (f)）：解析 TCS §10.3 附錄表，逐列比對：模組 `CARRIER`＝附錄「載具」欄代號集合、`set(ASSERTS)`＝附錄「斷言鍵」欄集合；附錄有列而 `cases.json` 無此案例、或案例宣告與附錄不同 ⇒ 紅並指名。附錄是單一真相源，實作不得自行增刪斷言鍵。

**本節判準**：TCS REQ-WP-80～86、99、100、102、AT-WP-79～84、90～95、E2E-WP-51、E2E-WP-67～69、MU-WP-25～27、31～33；結案時 `PRD_E2E_Coverage_Table.md` 的未覆蓋數＝0、未 PASS 數＝0。

---

## 附錄 A：PRD 修憲草案（§16.5 (i)；不改既有條文本體，只加修訂表列、就地註記、新節、§16.6 列；由期 C 收尾窗口落款）

| # | 插入座標（2026-11-19 HEAD 行號） | 列文字 |
|---|---|---|
| A-1 | 修訂表，line 27（v2.1.22 列）之後新增一列 | `| **v2.1.23（§16.5 (i)：工作推進軸入憲——未結項登記簿、完成閘、叫醒預算、名冊收斂；AutoClaude 無人舵手）** | 2026-11-19 | **掌舵者 2026-11-19 直接立案（原文：「所以又是任務沒有結束, 工作就停滯了! AutoClaude又沒有作用了!…看看AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md哪裡出問題, 請全面檢討!」）；R217 四方（Architect／SA／SD／QA）；QA 獨立審查紀錄座標＝R217 期 A 實作的 SCG-4 獨立審查（Opus QA）；落款當下尚未執行、沒有紀錄檔，審查完成後於本列末追加註記補上檔名** | 新增第三量測軸「工作推進」：未結項登記簿（OIR）為單一資料面、完成閘看狀態不看措辭、驅動器四型與排程憑證、叫醒為預算化致動器、名冊殘局收斂、無人時由 AutoClaude playbook 推驗證類未結項；設計＝`docs/02_architecture/WorkProgress_Axis_Design.md`、驗收＝`docs/03_testing/contracts/TCS-WorkProgress-20261119.md`。不改既有條文一字；舊列追加註記（N1 判例：字面保留為史料、本列逐字承認）：①v2.1.22 列「QA 獨立審查紀錄座標待填」之座標＝`docs/06_quality/CrossPlatform_R216_SessionSwitch_CostModel_Closure_Evidence.md`（其〈五〉為 QA 退件與修復紀錄）；②§16.2 §3.2 列（line 2696）與 §4.5.2 列（line 2720）所寫「〔待補〕」測試／「待真機驗證」已由 RV-A1 覆蓋（`RealVerify_Result_Ledger.md:73` 帳列 2026-11-18T15:26:08Z pass，含 §11.3① halt→重啟→T02 跑完），兩列字面不改；該類陳舊敘述已由 OIR 退役列 OI-20261120-015 承接 |` |
| A-2 | §2 名詞表，line 167（`C(t)` 列）之後新增四列 | `OI`（未結項，功能鍵層級，OIR）、`驅動器`、`憑證`、`完成（Done）`——定義照本稿 §2；並於 line 173 之後加一句就地註記「工作推進軸與額度軸、上下文軸獨立，三者門檻不得共用」 |
| A-3 | §1.2 原則 1，line 130 之後就地註記 | `> 🔴 【v2.1.23 註記】Daemon 已退役（§16.7）；執行面舵手分工改為：有人＝互動 Claude Code；無人且未結項有明確驗收指令＝AutoClaude playbook（掌舵者 2026-08-08「無人時舵手是 AutoClaude Playbook」）。引擎由未結項驅動器啟動，完成由 evaluator_command 判，不由 LLM 宣告。` |
| A-4 | §1.2 原則 2，line 134 之後就地註記 | `> 🔴 【v2.1.23 註記】叫醒是預算化的致動器，不是遙測：每次叫醒須對應「避免的成本」或「推進的未結項」；不得重複 harness 已送達的事件；保溫錨每 session 唯一；保溫叫醒與子代理在跑期間共用同一預算（§4.5.12）。` |
| A-5 | §16.1，line 2684（邊界第一點）之後就地註記 | `> 🔴 【v2.1.23 註記】⏸ 不得承載待驗收項；v2.1.22 列 ⏸ 原因中的待驗收自本版起改由 OIR 承接。「Windows 真機親驗不入本表」改讀為「不入 §16.2 母體，但入 OIR 並帶驅動器」。` |
| A-6 | §16.5，line 2774 之後就地註記 | `> 🔴 【v2.1.23 註記】OIR 的 observe 驅動器（驗收觀察期一次性到期檢查）不屬日曆觸發，條件：一次性、綁單一 OI、到期即結或 escalate、不得續期；OIR 只收已立案功能的驗收項，不收覆蓋度缺口，故不構成本節所禁的逐輪遞延待辦清單。` |
| A-7 | 新增 §4.5.11（line 1739 之後、`### 4.6` 之前） | 「完成閘」：R-4.5.11-1 OIR 單一資料面（append-only 事件帳本）；-2 完成＝名下無 undriven；-3 Stop 推回一次、判準看狀態不看措辭、無人窗口 no-op；-4 純保溫 shell 不算背景工作；-5 `max_attempts` 出廠 2、用盡轉人工清單；-6 驅動器憑證必須是排程器自報值；-7 名冊：killed 偵測全檔增量、擁有者活性讀 harness session 登記檔並有降級路徑、殘局滿壽命記 retired；（r3）-8 同一個 sid 不得同時有兩個 claude 行程：park 續跑先有條件關閉閒置舊窗再 `claude -r`；新 session 接手（ack）後，舊窗依五個條件自動關閉（身分全等、閒置、掌舵者 5 分鐘未打字、新 session 已寫出記錄、僅 Windows），先留痕、砍整棵行程樹、在新視窗出聲、可整個停用（掌舵者 2026-11-19 互動選項「有條件自動關 (Recommended)」）；-9 每個 PRD 條目都要有 E2E，且結果帳最近一次為 PASS 才算結案；例外只限掌舵者裁決不實作與只能由人裁決的條目，逐條寫明理由（掌舵者 2026-11-19 原話，見本稿 §15） |
| A-8 | 新增 §4.5.12（緊接 A-7） | 「叫醒預算與事件源合一」：R-4.5.12-1 不重複 harness 已送達事件（watch 不因全部交卷退出）；-2 保溫錨互斥；-3 保溫叫醒一回合；-4 預算＝ski-rental 上限 n*，含子代理在跑期間；-5 正常判決 rc 0、判決看末行（引 DEF-200-622） |
| A-9 | §4.5.7 偏離 2，line 1304 之後就地註記 | `> 🔴 【v2.1.23 註記】2026-11-19 現查：根層 `.venv` 已可 import `autoclaude`（editable 安裝，`find_spec` origin＝`AutoClaude/autoclaude/__init__.py`，`autoclaude.utils.notifier` import 成功）；本偏離的理由已不成立，但預防性提醒維持走 `quota_escalation.notify()`（不改既有實作）。` |
| A-10 | §16.6，line 2787 之後新增一列（本修憲自帶結案格）；另於 line 2787（v2.1.22 列）**結案格就地追加一行註記落款**，該列原文一字不動（PRD:2776「在該列結案格就地追加一行註記落款」；N1 判例 PRD:2764） | 新列：`| 2026-11-19 | 工作推進軸（v2.1.23） | ⏸→✅ 條件 | ✅ 條件（全部可機械判定）＝OIR 上線且 E6 標記全數映射（`openitems scan` 末行 unmapped＝0）、`openitems list --undriven` 輸出 0、完成閘真機推回入 RealVerify 帳（E2E-WP-06 pass 列）、M-WB2＝0（`waste_census --wake-metrics` 對上線後真逐字稿）、名冊對 05d1b770 類案例歸零（E2E-WP-27 pass 列）、AutoClaude 舵手連續 3 次真跑成功（`openitems helm-status` 資格＝是）、（r3）`realverify coverage --require-pass` rc 0（PRD 全功能 E2E 對照表未覆蓋 0、未 PASS 0，例外僅 C02／C14／A53／A54）；M-WB1 只作資訊欄入證據檔、不列條件；再開症狀＝任一 session 宣告完成而 OIR 有 undriven 列（附 sid＋行號）|`。v2.1.22 列結案格追加行（以 `<br>` 接在原文末，原文位元組不變）：`🔴【v2.1.23 註記】本列 ⏸ 中的待驗收項自 v2.1.23 起由 OIR 承接：<OI id 列表>；結案判準見 v2.1.23 列`。（r3）**為什麼要在 ⏸ 列的結案格追加註記，而不是只新增 v2.1.23 列**：①v2.1.22 列的 ⏸ 原因本身就是待驗收清單。如果原列不留一句指路，讀者從該列看到的仍是「⏸、待驗」，會把已由 OIR 承接的項目再追一次，同一件事記在兩處（雙重記帳），這正是 SA a14「文件陳舊造成待驗假象」的型態；②PRD §16.5 規定立案項落地時「在該列結案格就地追加一行註記落款」（PRD:2776），只新增新列不符合程序；③N1 判例（PRD:2764）要求原文一字不動，所以用 `<br>` 接在末尾，原位元組不變，E2E-WP-40 以修憲前 blob 比對驗證 |
| A-11 | §16.6，A-10 之後補登 8 列（SA a16；凍結後已落地但未登記） | 每列一機制，結案格依證據：①sessionctl 第一段（ADR-XPLAT-004 §2.13.1～3）✅；②第二段（§2.13.4～7）✅；③收斂閘（§2.14）✅；④配速床＋趕工戳記（§2.15）✅（V-P6 隨 WP-A7 補）；⑤網頁讀取不進派發帳（§2.16）✅（RV-WB1）；⑥park（§2.17）✅；⑦監督／封存／轉送（§2.18）✅；⑧半路停工與散文交棒 Stop 守衛（根 CLAUDE.md〈收尾常態規則〉）✅。每列「依據」欄引 ADR 節號＋RealVerify 帳列時間戳；仍有待驗者在依據欄寫 OI id，不用 ⏸ |

**本附錄判準**：C1 收尾窗口逐列套用後，`openitems scan` 對 PRD 回報 unmapped＝0；修訂表、§16.6 各列的掌舵者原文與本附錄逐字相同。
