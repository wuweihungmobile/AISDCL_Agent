# R217 SA 報告：PRD v2.1 需求追溯、未結大全、E2E 缺口、名冊殘局

- 角色：SA 系統分析（Opus），全程唯讀。日期 2026-11-19。HEAD＝f1e8d50c；工作樹有並行 SD（DEF-200-622／623）的未提交修改，本報告不碰。
- 標記：〔實查〕＝本棒當回合有工具輸出；〔推論〕＝由程式碼或文件推出、未實跑；〔他帳〕＝引自帳本或證據檔、本棒未重跑。
- 編號：本報告提議的編號可以直接轉成 SD 的 REQ／AT／E2E（R217-REQ-xx、R217-E2E-xx、R217-DEF-xx）。

---

## 0. 一句話結論

1. **PRD v2.1 不是實際的上游。** 2026-10-14 之後落地的續航機制，有 8 個家族沒有在 PRD §16.6 登記，也沒有修訂表列：§2.10～§2.18 的 sessionctl 第一段與第二段、收斂閘、配速床／趕工戳記、park、watch／封存／轉送、半路停工，以及散文交棒 Stop 守衛。PRD 自己的 §16.5／§16.6 規定「凍結後經 (i) 立案的每一項，落地時在此追加一列」，所以這是程序缺口。PRD 全文 grep `midwork`、`check_pending_handoff`、`quota_pace_floor`、`rush`、`roster`、`§2.13`～`§2.18`，命中都是 0〔實查〕。
2. **待驗項目沒有任何驅動器。**
   - `tools/realverify.py` 的檔頭寫「本機／nightly 跑」（第 8 行）。R215 的 WP-6 也承諾「nightly 接上 realverify stage」（`CrossPlatform_R215_PendingVerification_Closure.md:178`、`:240`）。
   - 實查結果是全 repo 非 docs 檔案裡，沒有任何排程、nightly 腳本或 SI 巡邏會呼叫 realverify。命中只有 workflows 的 paths 過濾、測試，以及 realverify 自身〔實查〕。
   - 兩支 `long` 案例 RV-LW3 與 RV-W6 從來沒跑過：帳本命中 0〔實查〕。
   - 兩個 14 天時間閘（E2E-SS-05、V-PK5）也沒有任何排程接手：`tools/lib/selfimproving/` grep `waste_census`，命中 0〔實查〕。
   - 所以主控說「沒有剩下要做的事」時，沒有任何機械物會反駁它。依鐵令，這算 BUG。
3. **名冊殘局是兩個判準缺陷疊加，再加上 RealVerify 留下的垃圾。** 見 §5。目前沒有機械物會收它，PRD 也沒有任何條文管名冊。

---

## 1. 需求清單與逐條追溯矩陣（共 100 條）

### 1.0 計數

| 狀態 | 條數 |
|---|---:|
| 完備 | 78 |
| 缺 E2E | 6 |
| 缺真機 | 6 |
| 未實作（非裁決） | 2 |
| 依裁決不實作（不計未結） | 2 |
| ⏸ 人裁（§13 法務、A7） | 2 |
| 文件宣稱與程式不符 | 3 |
| 本棒未追溯 | 1 |
| **合計** | **100** |

另外：D 區 20 條全部「PRD 未登記」，這是文件層缺口，和上表的狀態並列計。

### 1.A PRD §16.2 活躍結案表 54 列（繼承 PRD 自帳 ✅52／⏸2，本棒只抽查有殘留的列）

| R217 編號 | PRD 座標 | 實作座標 | 單元測試 | E2E | 最近真機證據 | 狀態 |
|---|---|---|---|---|---|---|
| R217-REQ-A01～A46 | §16.2 中 29 個矩陣 ✅ ID，加上沒有殘留的 ✅ 列 | 見 PRD 各列落款 | 見各列 | 部分有 RV（RV-N1～N5 哨兵、RV-A1 引擎） | RealVerify 帳 `family=sentinel pass n=5`（2026-11-18T15:33:38Z）、`family=autoresume pass`（15:39:08Z） | 完備（PRD 自帳；本棒未逐列重驗） |
| R217-REQ-A47 | §3.2 FSM／中斷後重啟續跑 | `AutoClaude/autoclaude/main.py::register_global_hotkey`、`core/services/auto_resume.py` | `test_prd32_global_hotkey_registration.py` | RV-A1（§11.3① halt→重啟→T02 跑完） | RV-A1 帳 15:26:08Z pass | 完備（PRD 列內「〔待補〕」測試已由 RV-A1 覆蓋；文字未更新，屬輕微文件落差） |
| R217-REQ-A48 | §4.5.2 長睡外部續跑 | `external_resume.py`、`tools/lib/engine_resume_job.py` | `test_auto_resume_external_resume_cmd.py` | RV-A1 | 同上 | 完備（PRD 列仍寫「✅（待真機驗證）」，屬文件陳舊） |
| R217-REQ-A49 | §6.1 不變式 | `boot_self_check.py` | 多支 | — | — | 完備（不變式 5 與 10 是已知邊界） |
| R217-REQ-A50 | §8 列 3 陳舊 index.lock | `relay_machine.py::stale_index_lock` | `test_context_budget_guard.py` | 無 | PRD 列自陳「Windows `tasklist` 分支未實跑」 | **缺真機**（本機就是 Windows，可以自驗） |
| R217-REQ-A51 | §11.1 零 token 6h | `zero_token_patrol_sim.py` | selftest | 只有模擬 | PRD 列自陳「真機 6 小時牆鐘驗證未做」 | **缺真機**（屬時間累積類） |
| R217-REQ-A52 | §11.8 24h／≥4 reset | `day_long_relay_sim.py`、`test_day_long_resume_prd11_8.py` | 有 | 只有模擬 | 只有 mac 單次（R212） | **缺真機**（屬時間累積類） |
| R217-REQ-A53 | §13 使用條款法務檢核 | — | — | — | — | ⏸ 人裁 |
| R217-REQ-A54 | 施工圖 A7 無人 commit／push | — | — | — | — | ⏸ 掌舵者安全裁決 |

### 1.B PRD §16.6 凍結後立案 4 列

| 編號 | 列 | 狀態 |
|---|---|---|
| R217-REQ-B01 | 2026-10-10 CLI 版本家族判定 | 完備 |
| R217-REQ-B02 | 2026-10-11 env 跨機同步 | 完備；掌舵者實機 cp950 殘留照舊 |
| R217-REQ-B03 | 2026-10-14 halt 標記辨識他 session 接手 | 完備 |
| B04 | 2026-11-18 快取成本（v2.1.22） | ⏸，展開為 1.C |

### 1.C v2.1.22：TCS-SessionSwitch REQ-SS-01～21（加 2 條拆出的效果需求）

- TCS 座標：`docs/03_testing/contracts/TCS-SessionSwitch-CostModel-20261118.md:25-45`。
- 單元測試檔都在 `tools/tests/`。各檔 `def test_` 數〔實查〕：costmodel 16、keepwarm 26、watch 36、longwait 23、converge 31、handoff 90、switch 36、seal 20、forward 24、park_route 14、waste_census_keep 23、hooks 42。

| R217 編號 | REQ | 實作座標 | 單元測試 | E2E | 最近真機證據（RealVerify_Result_Ledger.md） | 狀態 |
|---|---|---|---|---|---|---|
| C01 | REQ-SS-01 成本公式＋R1 退役 | `sessionctl/costmodel.py` | test_sessionctl_costmodel | RV-CM1 | 2026-11-18T20:07:18Z costmodel pass n=4 | 完備 |
| C02 | REQ-SS-02 | — | — | — | — | 依裁決不實作 |
| C03 | REQ-SS-03 keepwarm 指令 | `sessionctl/keepwarm.py` | test_sessionctl_keepwarm | RV-KW1／KW2（E2E-SS-03） | 2026-11-19T08:12:14Z keepwarm pass n=5 | **文件不符**（REQ 寫 rc 6／7；並行 SD 的 DEF-200-622 正在改成 rc 0，TCS 要同步改） |
| C03b | 保溫真的保住快取（主前提） | — | — | E2E-SS-04：**沒有 RV 案例** | 無 | **缺 E2E**（可自動，屬 a 類） |
| C04 | REQ-SS-04 保溫帳 | keepwarm.py | 同上 | RV-KW1（帳 pings／n_star） | 同上 | 完備 |
| C05 | REQ-SS-05 不掛條件 | keepwarm.py | 同上 | RV-C4 乙組（`skip reason=handed_over`） | 2026-11-19T08:06:00Z | 完備（其他 skip 分支只有單元測試） |
| C06 | REQ-SS-06 Stop 保溫閘 | `.claude/hooks/sessionctl_guard.py`、keepwarm.stop_verdict | test_sessionctl_hooks | RV-KW5 | 08:12:14Z | 完備 |
| C07 | REQ-SS-07 冷叫醒閘豁免 | converge／seal | test_sessionctl_converge | RV-C2、RV-C4 | 08:00:11Z | 完備 |
| C08 | REQ-SS-08 watch 保溫錨點 | `sessionctl/watch.py` | test_sessionctl_watch | RV-W6（V-W3）：**`long`，帳本 0 列** | 無 | **缺 E2E**（a 類） |
| C08b | 子代理分段等待效果 | longwait.py | — | E2E-SS-08＝RV-LW3：**`long`，帳本 0 列** | 無 | **缺 E2E**（a 類） |
| C09 | REQ-SS-09 watch quota 閂鎖 | keepwarm.py:310、watch.py | test_sessionctl_watch | RV-KW3／KW4（E2E-SS-09） | 08:12:14Z | 完備 |
| C10 | REQ-SS-10 runlong | `sessionctl/longwait.py` | test_sessionctl_longwait | RV-LW1 | 2026-11-18T16:31:39Z longwait pass n=3 | 完備 |
| C11 | REQ-SS-11 waitfor | 同上 | 同上 | RV-LW1 | 同上 | 完備 |
| C12 | REQ-SS-12 長前景閘 | longwait.pretool_verdict | 同上 | RV-LW2／LW4（E2E-SS-07） | 同上 | 完備 |
| C13 | REQ-SS-13 封存閘 HARD | seal.py | test_sessionctl_seal | RV-CM1、RV-C1 | 20:07:18Z | 完備 |
| C14 | REQ-SS-14 hold | — | — | — | — | 依裁決不實作 |
| C15 | REQ-SS-15 收斂閘 HARD | converge.py | test_sessionctl_converge | RV-CM2（E2E-SS-11） | 同上 | 完備 |
| C16 | REQ-SS-16 advise_once＝HARD | handoff.py | test_sessionctl_handoff | RV-CM1 | 同上 | 完備 |
| C17 | REQ-SS-17 fresh_reasons／F4 | switch.py | test_sessionctl_switch | RV-CM3（E2E-SS-13） | 同上 | 完備 |
| C18 | REQ-SS-18 轉送 F4 | forward.py | test_sessionctl_forward | RV-CM4（E2E-SS-12）、RV-F1 | 同上；forward 2026-11-18T13:19:46Z | 完備 |
| C19 | REQ-SS-19 park 選路 | park.fire_route、park_cli.spawn_resume | test_sessionctl_park_route | RV-PR1／PR2（E2E-SS-14） | 2026-11-18T23:51:45Z | **缺真機**（V-SS5：真的開出 `claude -r` 視窗） |
| C20 | REQ-SS-20 量測 M-K | wastecensus/sections_keep.py | test_waste_census_keep | RV-SC1／SC2 | 23:51:15Z | 完備（E2E-SS-05 的 14 天目標見 b 類） |
| C21 | REQ-SS-21 事件常數 | keepwarm.py:30-32、longwait.py:31、sections_keep.py:26-29 | test_waste_census_keep | — | — | **文件不符（輕）**：TCS:45 仍列 `hold_set`，程式依裁決無此常數 |

### 1.D 凍結後已落地、PRD 未登記的機制（20 條；權威＝ADR-XPLAT-004 §2.10～§2.18，加上根 CLAUDE.md〈收尾常態規則〉）

| R217 編號 | 機制（ADR 座標） | 實作 | E2E | 最近真機證據 | 狀態 |
|---|---|---|---|---|---|
| D01 | 自願停機喚醒活動判準 §2.10 | transcript_activity.py | RV-N1～N3 | sentinel pass 2026-11-18T15:33:38Z | 完備 |
| D02 | 雙駕駛 §2.11 | 同上 | RV-N3／N5 | 同上 | 完備 |
| D03 | 無人 print 模式背景上限 §2.12（DEF-200-574／575） | unattended_authz.py、resume_route.spawn_env | **沒有 RV 案例** | 無 | **缺 E2E** |
| D04 | 無人選路量成本 §2.13.2 | switch.py | RV-CM3 | 20:07:18Z | 完備 |
| D05 | 過期 session 不續跑 §2.13.3 | sentinel_decide | RV-N4（V2） | sentinel pass | 完備 |
| D06 | 交接包 build／finalize／spawn／ack §2.13.4-5 | handoff.py | RV-H1～H5 | 2026-11-19T08:07:34Z pass n=5 | **缺真機**：RV-H3 備註「rc=1（信任對話框限制：不等新逐字稿）」，新視窗是否真的讀包沒有驗 |
| D07 | SendMessage 續棒成本閘 §2.13.6 D6 | roster.resume_gate | RV-M1 | gates pass 20:19:15Z | 完備 |
| D08 | 名冊／status／stop §2.13.6 D7 | roster.py、procstop.py | RV-T1／T2 | status pass 21:17:12Z | **文件與程式不符：判準有兩個缺陷**（見 §5） |
| D09 | 模型平衡建議 §2.13.7 | modelmix.py | RV-T3 | status pass | 完備 |
| D10 | 收斂閘 §2.14 | converge.py | RV-M2、RV-C3 | gates pass | 完備 |
| D11 | 長等待角色用 1h 快取（long-runner，G3）§2.14 | `.claude/agents` 不存在〔實查 `exists=False`〕 | V-T1～T3 | 無 | **未實作**（條件項，ADR 決定未收尾） |
| D12 | 推送快層先行 §2.14 | tools/git-hooks/pre-push | — | — | 本棒未追溯 |
| D13 | 配速床＋趕工戳記 §2.15 | quota_pace_floor.py、quota_rush.py | RV-R1／R2 | quota_rush pass 15:39:23Z | **部分未實作**：V-P6 的 `--pace-metrics`／`--replay-pace-floor` 不存在（`realverify/cases/quota_rush.py:87-93` 已把「未落地」釘成斷言；wastecensus 中沒有這兩個旗標〔實查〕） |
| D14 | 網頁讀取不進派發帳 §2.16（DEF-200-590） | quota_gate | **沒有 RV** | 無 | **缺 E2E** |
| D15 | park §2.17 | park.py、park_cli.py | RV-K1～K7、RV-N5 | park pass 2026-11-19T02:28:18Z | 完備（V-PK5 的 14 天對照屬 b 類） |
| D16 | watch 監督 §2.18 D1 | watch.py、supervise.py | RV-S1／S2、W1～W5；**W6 從未跑** | watch pass 2026-11-18T21:08:20Z | **缺 E2E**（V-W3） |
| D17 | 封存閘 §2.18 D2 | seal.py | RV-C1 | converge pass | 完備 |
| D18 | 冷窗轉送／已交棒告知 §2.18 D3-4 | forward.py | RV-F1～F3 | forward pass 13:19:46Z | **缺真機**（畫面與新視窗兩件，c 類） |
| D19 | 半路停工判準 | sessionctl/midwork.py、check_pending_handoff.py | RV-P2 | pending_handoff pass 20:19:52Z | 完備 |
| D20 | 散文交棒 Stop 守衛 | check_pending_handoff.py | RV-P1 | 同上 | 完備 |

另有一條要特別點名：**AutoClaude 引擎在續航路徑中沒有上場**〔實查〕。

- 生產碼裡呼叫 `python -m autoclaude` 的只有 `tools/lib/engine_resume_job.py`，那是引擎自身長睡的外部續跑。
- 哨兵、park、keepwarm、handoff 一律直接 spawn `claude`，不經 AutoClaude。
- AutoClaude 唯一的真機證據是 RV-A1（引擎自續跑，n=1 playbook）。
- 所以「無人看管時舵手是 AutoClaude」這句記憶，在本輪的續航上並不成立。結論交 Architect。

---

## 2. 未結大全（去重後 26 項：a 16／b 4／c 6）

grep 範圍：根 CLAUDE.md、ADR-XPLAT-004、TCS-SessionCtl／Park／SessionSwitch／TokenWaste、PRD、缺陷帳本、R215／R216 證據檔〔實查〕。重點座標如下：

- CLAUDE.md:88／149／179
- ADR:524／526／723／799／801／812／1057／1062／1064／1134／1135／1195／1199
- TCS-SessionCtl:5／283／310
- TCS-Park:4／216／223／224／225
- TCS-SS:156／157／160／164-167／218
- TCS-TW:269／282／556／567
- 帳本 DEF-200-594／596／597 狀態欄
- R216 證據:23／38

### (a) 可由 AutoClaude／RealVerify 自動驗，只是沒人做（依鐵令算 BUG）

| # | 項目 | 證據 | 提案（R217-E2E 編號） |
|---|---|---|---|
| a1 | **realverify 沒有任何排程驅動**（R215 WP-6 承諾的 nightly stage 沒有落地） | realverify.py:8、R215:178／240；非 docs 檔 grep 命中 0 | R217-REQ-01：`run_local_nightly.ps1`（或 SI 巡邏）新增 stage，跑 `realverify run --all --long` 並入帳；失敗要轉缺陷帳本列 |
| a2 | E2E-SS-04 保溫真效果，沒有案例 | TCS-SS:156；list 無對應 RV | R217-E2E-01 |
| a3 | RV-LW3（E2E-SS-08／V-SS2）從未跑 | 帳本 0 列 | 併 a1 |
| a4 | RV-W6（V-W3）從未跑 | 帳本 0 列 | 併 a1 |
| a5 | V-SS1 閒置 3 小時回來 `cache_read≥0.9×` | TCS-SS:222 | R217-E2E-02（`-p -r` 近似） |
| a6 | RV-KW6／KW7（DEF-200-622／623）未入帳 | list 有、帳本 0 列 | 並行 SD 收尾時跑 |
| a7 | V-P6 量測旗標未實作 | quota_rush.py:87 | 實作，或依 §16.5 正式退役 |
| a8 | §8 列 3 Windows `tasklist` 分支未實跑 | PRD §16.2 該列 | R217-E2E-03（本機造 index.lock＋mtime 回撥） |
| a9 | RV-H3 新視窗受信任對話框擋住，不等新逐字稿 | 帳本 08:07:34Z | R217-E2E-04（預植 trust） |
| a10 | §2.12 print 模式背景上限，無 E2E | — | R217-E2E-05 |
| a11 | §2.16 網頁讀取不進派發帳，無 E2E | — | R217-E2E-06 |
| a12 | long-runner（G3／V-T1～T3）未實作、未裁決 | ADR §2.14；`.claude/agents` 不存在 | Architect 裁決：做或退役 |
| a13 | 名冊兩個判準缺陷、RV 沙盒逐字稿目錄殘留 5 個 | §5 | R217-DEF-01～03 |
| a14 | 文件陳舊：R215 WP-6 承諾的「待驗→已驗」改寫沒做完 | 見下方條列 | 收尾單人窗口依帳本逐列改寫 |
| a15 | v2.1.22 修訂表「QA 獨立審查紀錄座標待填」 | PRD:27 | 填座標 |
| a16 | PRD §16.6 缺 8 族登記（§0-1） | PRD grep | R217-REQ-02：依 §16.5 (i) 補列＋修訂表 v2.1.23 |

a14 的陳舊位置：

- DEF-200-594／596／597 仍寫「待真機」，但 RV-K1／K7、RV-S1／S2 已經 pass。
- ADR:1064、TCS-Park:4／223／224 仍寫「待真機」，但 RV-K2／K7 已經 pass。
- CLAUDE.md:88／149／179 仍是舊字樣，R215 #1～#3 擬改寫，至今未改。

### (b) 需要時間累積

| # | 項目 | 到期 | 現在誰驗 | 提案驅動器 |
|---|---|---|---|---|
| b1 | E2E-SS-05：M-K2＝0（上線 14 天） | 約 2026-12-02（自 2026-11-18 起算） | 無 | SI 巡邏 `AutoSDD_SI_Patrol` 已每日跑（status 有列這個排程）。加一張「到期觀察項」表：到期當天自動跑 `waste_census --switch-metrics --since-days 14` 並入帳 RealVerify；未達標就立缺陷 |
| b2 | V-PK5：park 上線 14 天 `--resume-metrics` 對照 | 2026-11-30（R215:82） | 無 | 同上 |
| b3 | §11.8 24h／≥4 reset 真牆鐘 | 無日曆（PRD 規定不排日曆） | 無 | 改用「事件觸發」：哨兵痕跡累積到 4 次 reset 續跑時，由 nightly 自動彙整一次 |
| b4 | §11.1 6h 零 token 真牆鐘 | 同上 | 無 | nightly 偵測「前 6 小時無 session」時自動跑 `--pace` 首尾比對（PRD 列已給配方） |

### (c) 只能人眼看的互動畫面（附自驗方案）

| # | 項目 | 自驗方案 |
|---|---|---|
| c1 | V-SS5：park RESUME 真開 `claude -r` 視窗並續寫原逐字稿 | 可自驗。用預先植入 trust 的固定沙盒（在 `~/.claude.json` 的 projects 項寫 `hasTrustDialogAccepted`〔推論，須 SD 現查鍵名〕），跑真 park `--at now+2`。斷言：原 sid 逐字稿到點後新增 user／assistant 記錄＋`park_route` 痕跡。不需要看畫面 |
| c2 | V-SS4／V-PK4／V5／V-W2／V-C2：block 理由與 `systemMessage` 畫面可見 | 逐字稿的 `hook_blocking_error`／`stop_hook_summary` 已能機驗「訊息送達 harness」（R215 #1 已採這個口徑）。純畫面渲染：可以用 PowerShell `PrintWindow` 擷取新視窗，加 `Windows.Media.Ocr` 比對字樣〔推論，可行性待 SD 試做〕；做不到就明寫為非阻塞目視 |
| c3 | V-F1 畫面：轉送說明＋新視窗讀到原文檔 | 新視窗讀檔＝c1 同法（看新 sid 逐字稿有沒有 Read 該 `forward-*.md`）；畫面＝c2 同法 |
| c4 | §13 使用條款法務檢核 | 確定做不到：法律判斷，只能人做 |
| c5 | A7 無人 commit／push | 不是驗證，是掌舵者的安全裁決 |
| c6 | V-K1／K2（互動 `ScheduleWakeup` 保溫、95～99% 時 wake）、V-M1 | V-K1 已被 keepwarm 取代，可以正式退役。V-K3 改由 M-K2（b1）量。V-K2 需要真實額度狀態，屬事件觸發 |

### Top 10（依「讓工作停滯」的影響排序）

1. a1 realverify 沒有驅動器
2. a16 PRD 未登記 8 族
3. b1／b2 14 天時間閘沒有接手者
4. a2 E2E-SS-04
5. a13 名冊判準缺陷
6. a3／a4 兩支 long 案例從未跑
7. c1 V-SS5 可自驗卻掛在人身上
8. a14 文件陳舊，造成「有待驗」的假象，也掩蓋真待驗
9. a9 RV-H3 trust 限制
10. a7 V-P6 未實作

---

## 3. E2E 缺口與案例草案（8 項）

| 提議編號 | 對應 | 載具 | 斷言 |
|---|---|---|---|
| R217-E2E-01 | E2E-SS-04（C03b） | 新 RV-KW8 `long`：真 `claude -p --model haiku` 三次。t0 建 session，上下文 ≥4,096；t0+45 分 `-r` 輕觸；t0+100 分 `-r`。另設對照組：不輕觸、t0+70 分 | 第三次 `cache_read ≥ 0.9×` 前一回合上下文；對照組 `< 0.1×`。以 usage 的 `ephemeral_1h_input_tokens` 判斷是否為 1h 層；不是 1h 層就改量 5m 版（4 分 vs 7 分） |
| R217-E2E-02 | V-SS1（a5） | RV-KW8 延伸：t0 後每 45 分 `-r` 輕觸，共 4 次，總長 3 小時 | 每次 `cache_read ≥ 0.9×`；逐字稿沒有 `compact_boundary` |
| R217-E2E-03 | §8 列 3（A50） | 沙盒 git repo 造 `.git/index.lock`，os.utime 回撥 700s；真跑 `relay_machine.stale_index_lock`（Windows `tasklist` 分支） | 沒有 git 行程時改名為 `index.lock.stale-*`；另起一支 `git` 行程佔住時要 kept |
| R217-E2E-04 | RV-H3／D06（a9） | 沙盒預植 trust 後 `handoff --spawn` | 新 sid 逐字稿出現 Read 交接包路徑；SessionStart 公告字樣 |
| R217-E2E-05 | §2.12（D03） | 真 `claude -p --model haiku` 帶 `resume_route.spawn_env()`，派一支背景 shell `sleep` 超過上限 | 行程在上限內結束；環境含 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`＝SSOT 值 |
| R217-E2E-06 | §2.16（D14） | 真 hook 行程 PreToolUse，連續 WebFetch／WebSearch 若干次，加 Agent 一次 | 派發帳不含 Web 類；Agent 不因 Web 呼叫被扇出節流擋 |
| R217-E2E-07 | 名冊（D08／R217-DEF-01～02） | 沙盒 projects：主逐字稿 killed 通知距檔尾 >256KB；另起一支命令列含舊 sid 交接包路徑的假 claude 行程 | 被停代理不列入；舊 owner 不因新視窗命令列被誤判為活著 |
| R217-E2E-08 | a1 驅動器本身 | nightly 腳本 dry-run | stage 有呼叫 realverify 並寫帳本列；`claude` 缺件時 rc≠0 且入帳（不得 skip） |

`long` 案例 RV-LW3／RV-W6 不需要新草案，只要接上 a1 的驅動器。

---

## 4. 名冊殘局：實查與根因

### 4.1 現況（`python tools/sessionctl.py status`，rc=0〔實查〕）

- `[安靜] ab573c773ef06f035｜R216 SD｜ctx 413116｜擁有者 05d1b770｜最後 2026-11-19T00:55:26`
- `[殘局] a7eeea0a7b8c718b3 rv-t1-worker｜擁有者 810bce3b`、`[殘局] a96d1a715d16ff89d rv sleeper｜擁有者 c02eb607`、`[殘局] ab500ab86bbedfbf1 Opus 設計｜擁有者 c4242b88`
- 視窗行程：pid 15660（來源 05d1b770）

### 4.2 為何「安靜」那支一直不消失（兩個缺陷疊加，都已實查）

1. **R217-DEF-01：killed 偵測的讀取窗太短。**
   - 依據 `roster.py:173-186` 與常數 `_TAIL_BYTES=262144`（:29），`_killed_ids` 只讀主逐字稿的尾端 256KB。
   - 05d1b770 逐字稿第 769 行有 `<status>killed</status>`（task-id ab573c773ef06f035），距檔尾 **284,096 bytes**，已經超出讀取窗。所以 TaskStop 被漏認〔實查：檔長 2,692,634、該行 offset 2,408,538〕。
   - 檔頭自陳「通知若被擠出尾端，照舊等 quiet 門檻降級（不更糟）」，但下一條缺陷讓它連降級成殘局都做不到。
2. **R217-DEF-02：擁有者被誤判為還活著。**
   - `procstop.sid_of`（procstop.py:113-116）取命令列裡的**第一個 UUID**。
   - pid 15660 是交棒新開的視窗，命令列是 `claude "按交接包繼續：讀 C:\Users\wuwei\.autosdd\handoff\05d1b770-…md…"`〔實查〕，所以取到的是舊 sid 05d1b770。
   - 結果是 `owner in alive`，`roster.py:227` 不進殘局判定，這支代理永遠停在「安靜」。
   - 「安靜」不受 `RESIDUE_MAX_AGE_SECONDS`（24h）約束，只有在全域名冊以 mtime 48h 回看（:219-220）時才會消失〔推論〕。

### 4.3 三支殘局

- **R217-DEF-03：RealVerify 沙盒留下逐字稿目錄。**
  - 810bce3b 與 c02eb607 的 slug 是 `C--Users-wuwei-AppData-Local-Temp-AutoSDD-RV-sbx-*`〔實查〕。
  - `~/.claude/projects` 下這類目錄共 **5 個**〔實查〕。
  - RealVerify 只清 Temp 沙盒本身，沒有清 `~/.claude/projects/<沙盒 slug>`。這和 R216 證據:62「殘留 0（`AutoSDD_RV_sbx_*` 沙盒…皆查過）」不一致，因為那次只查了 Temp。這也違反「測試用完慣例移除」。
- c4242b88：上一輪設計代理的擁有者 session 結束時沒有 TaskStop。依設計，殘局是歷史記錄、不燒額度，最後記錄滿 24h 會自動從預設名冊消失（`roster.py:231-234`）。本例最後記錄是 11-18 21:26，約今晚 21:26 消失〔推論〕。

### 4.4 依 PRD 誰該負責收？

- PRD v2.1 對名冊、殘局**零條文**（grep `roster` 命中 0〔實查〕），權威只有 ADR §2.13.6 D7。
- 依 D7，名冊只是**唯讀掌控面**（status、stop window）。「收掉」的責任在發出背景代理的主控（TaskStop）。殘局則依設計只顯示、不處置。

### 4.5 目前的機械物

- 只有兩件，都是「排除或過期」，沒有一件是「收」：
  - DEF-200-606 的 killed 排除，有上述讀取窗缺陷。
  - DEF-200-611 的殘局 24h 過期隱藏。
- 沒有任何機械物會：
  - 讓「安靜」過期；
  - 在交棒時對被停或未收的代理寫 `finished`；
  - 清 RealVerify 留在 projects 下的沙盒 slug 目錄。

### 4.6 建議（交 SD）

1. DEF-01：killed 偵測改成增量全掃，或對被 TaskStop 的代理另寫持久標記（例如 handoff `--finalize` 時把已 TaskStop 的 id 寫進 sidecar）。
2. DEF-02：`sid_of` 只認 `-r <uuid>`／`--resume <uuid>`／`--session-id <uuid>` 這類旗標形態；交接包路徑裡的 UUID 不算擁有者活著。
3. DEF-03：`sandbox` 清理時一併刪除 `~/.claude/projects/<沙盒 slug>`，並在案例結尾斷言它不存在。
4. 「安靜」也套用壽命上限：例如擁有者已交棒（有 `.ack`／spawn 痕跡），就降成殘局。

---

## 5. 實耗

- 本棒：約 45 次工具呼叫，全部唯讀；只寫本報告一檔。
- 名冊自報上下文 208,988、累計 4,844,475（status 當下）。
- 上述數值皆為 18:54 時點；交卷時一定更高，以 harness 實計為準。
