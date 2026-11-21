# R216 收尾證據：換 session 依快取成本（不讓快取過期）與真機自驗載具收尾

> 輪次＝R216（`python tools/check_handoff_carriers.py` 首行以本檔檔名現查）。收尾單人窗口（SD＋文件治理）於 2026-11-19 做連動面收齊；本檔只記**可重驗的座標**，不複寫數字（量測值一律現查）。
> 上游：掌舵者 2026-11-18「請檢討context 25萬就切換Session的合理性, 是否應該專注在不要讓Cache過期!」（再指令三連）；裁決＝不設軟線、只留硬線、hold 不實作。設計＝`docs/02_architecture/SessionSwitch_CostModel_Design.md`（§11 裁決段優先）；驗收＝`docs/03_testing/contracts/TCS-SessionSwitch-CostModel-20261118.md`；ADR＝ADR-XPLAT-004 §2.19；PRD＝v2.1 修訂表 v2.1.22。

## 一、本輪收齊的連動面（同一個 commit）

| 面 | 座標 |
|---|---|
| ADR | `docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` §2.19（新）；§2.13／§2.14／§2.17／§2.18 的 R1／R3／「已出聲」敘述就地加註「v2.1.22 起見 §2.19」 |
| PRD 修憲 | `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`：修訂表 v2.1.22 列、§16.6 列、§1.2 原則 2／§4.3／§4.5.4／§11.3 四處就地註記（不改既有條文一字） |
| 根 CLAUDE.md | 〈換 session 的 SOP〉〈收斂閘與硬線〉〈派背景代理＝同一回合掛監督〉、新增〈不讓快取過期〉一段、機械守衛總表 `sessionctl_guard.py`／`context_budget_guard.py` 兩列、現查速查表三列（keepwarm／runlong+waitfor／realverify） |
| TCS | `TCS-SessionSwitch-CostModel-20261118.md`（軟線／hold 標「依裁決不實作」、`waitfor` 上限 255）；`TCS-SessionCtl-20261113.md`／`TCS-TokenWaste-20261114.md`（R1／R3 列標史料；FR-W2、V-W3 改保溫點新定義） |
| 缺陷帳本 | `AutoSDD_Defect_Log.md` DEF-200-611～615（詳情 `CrossPlatform_R215_PendingVerification_Closure.md`〈R216 收尾〉） |
| 落點表 | `docs/02_architecture/Root_Layout_and_Module_Placement.md` sessionctl 列補新檔、realverify 列 DEF 號訂正 |
| realverify | `RealVerify_Protocol/cases.json` 補登 14 案例；`sched.register_once` 改走 `quiet_python()`；`os.name` 守衛；整檔 `# ruff: noqa: E501` 改逐行 |
| 棘輪 | `test_adr_xplat001_c1c2_lock.py`（逐檔表、重釘列、接鏈列、名冊精確淨額）、`run_root_unittests.py::MIN_TESTS`、`skip_tag_policy._TREE_FILE_FLOORS`、`test_subprocess_encoding_hygiene.py` 掃描面下限、`governance_docs.py`、compat-ci `paths`（`tools/lib/realverify/**`）、ONBOARDING 基線 |
| 死碼 | `supervise.WATCH_CMD_MARK` 刪除（改 `_WATCH_CMD_RE`，無外部引用，ADR／TCS 敘述同步） |

## 二、誠實未結（不得宣稱已完成）

- 〔已於 2026-11-19 WP-F／WP-G 補做，見〈四〉〕TCS WP-G 量測端與 park 選路（REQ-SS-19）原列未實作，現已落地。
- E2E-SS-04（`-p` 模式快取層）、E2E-SS-05（上線 14 天後 M-K2＝0）、V-SS1～V-SS4 互動真機項：以 `docs/06_quality/RealVerify_Result_Ledger.md` 已入帳者為準，未入帳＝未結。
- PRD §16.6 v2.1.22 列因此維持 ⏸。

## 三、當回合驗證輸出

見收尾回報（指令、Ran／OK／rc）；本檔刻意不抄數字。

## 四、WP-F／WP-G／偶發測試補做（2026-11-19，SD 單人窗口）

| 項 | 落點與驗證座標 |
|---|---|
| WP-F park 到點選路（REQ-SS-19） | 判準 `tools/lib/sessionctl/park.py::fire_route`；執行 `park_cli.py::_fire_route／spawn_resume`；單元＋整合 `tools/tests/test_sessionctl_park_route.py`（含反向變體：熱快取大上下文仍續跑、失敗不退回 spawn）；真排程＋真行程 RealVerify `RV-PR1`（冷＋17 萬⇒RESUME）／`RV-PR2`（冷＋60 萬⇒FRESH），家族 `sessionctl_parkroute` |
| WP-G 量測（REQ-SS-20／21） | 判準 `tools/lib/wastecensus/sections_keep.py`、I/O `keep_load.py`、入口旗標 `report.py`；`reader.py` 增 `kw_calls`（保溫類指令配對叫醒通知）；`tools/tests/test_waste_census_keep.py`（AT-SS-50～52、決定性快照重放、事件名與 sessionctl 常數相等）；真逐字稿 RealVerify `RV-SC1`／`RV-SC2`，家族 `sessionctl_switchcensus` |
| 偶發測試 DEF-200-616 | 成因＝測試逐次重種「now+3600s」的 reset 而閂鎖鍵取到分鐘，跨整分鐘換鍵（被測物無缺陷）；重現載具＝在整分鐘前 5ms 起跑（修前 2/2 紅、修後 2/2 綠）；修法＝整視窗只種一次快取＋時鐘無關的決定性回歸；帳本 `AutoSDD_Defect_Log.md` |
| DES §7 對帳 | M-K1／M-K2／M-K3／M-K4、P1、S2 與 DES 逐位相符；P3／P4b／S1 差異＝母體多一支交接包開場 session（F 中位 480,734→467,949）與 `annotate.units` 對「分層未標」寫入記 1.25（DES 腳本記 2.0，F_a 差 6 單位）；逐項核過、非缺陷 |
| 仍未結 | E2E-SS-05（上線 14 天後 M-K2＝0）；park RESUME 路「到點真開 `claude -r` 視窗並續寫原逐字稿」（V-SS5，〔OI-20261120-009〕待掌舵者目視；folder trust＋禁開窗）；E2E-SS-04、V-SS1～V-SS4 沿用上節 |

## 五、QA 退件修復：同 session 自續跑不算交棒（2026-11-19，SD 單人窗口；DEF-200-617／618）

| 項 | 落點與驗證座標 |
|---|---|
| P2-1 成因 | `.ack` 沒記接手者、`seal.handed_over` 只看 `.ack` 存在；暴露證據＝主控 sid 31ea79d4 逐字稿第 675 行（SessionStart 公告叫它 ack 自己的包）、第 808／852 行（Stop 冷叫醒閘推回兩次），`.ack` 落款 09:02:43 |
| 修法（消除成因，不在各消費者各打補丁） | `handoff.ack` 記 `sid=`；原主人 ack／`park_cli.spawn_resume` 成功 ⇒ `seal.mark_resumed`（寫 `.resumed`、刪 `.sealed`、清自己 sid 的 `.ack`；舊格式 `.ack` 保留，見〈六〉P3-a）；`handed_over` 只認別的 sid 的 ack 或 spawn 痕跡；`announce` 對自己的包改提示續做；`seal()` 重新封存時清 `.resumed`；`handoff._state` 新增 `resumed` 狀態。ADR-XPLAT-004 §2.19 D7、TCS §3.5b／E2E-SS-15 |
| 消費者處置 | `wake_package`（冷叫醒閘）、keepwarm `skip_reason`、`converge._exits`／PreToolUse 訊息、`forward._handed_over_verdict`、封存閘 `seal.stop_verdict` 全經 `handed_over`／`wake_package`／`is_sealed`，零改動即修好；SessionStart `announce` 與 `ack`／`spawn_resume` 為資料寫入端，已改 |
| 驗證 | 單元：`test_sessionctl_seal.py::SelfResumeTest`、`_converge.py::…test_p2_1…`、`_keepwarm.py::…self_resumed…`、`_handoff.py::AnnounceTest`、`_park_route.py::SpawnResumeTest`（皆含反向變體：別的 sid／spawn 痕跡仍是交棒）；真機 RealVerify `RV-C4`（甲＝同 sid 自續跑、乙＝別的 sid 對照） |
| P3-1 | `test_sessionctl_keepwarm.py::test_p3_1_the_same_reset_window_boundary_is_pinned`；M12／M13 突變在 worktree 皆被殺 |
| P3-2 | PRD v2.1 §11.3 line 2387 就地註記指向 §16.6 2026-11-18 列①（不改既有條文本體） |
| 本機殘留（主控 sid 31ea79d4 的 `.ack`） | 本修復不動它；主控在 31ea79d4 視窗內跑 `python tools/sessionctl.py handoff --ack <交接包路徑>`（該視窗的 `CLAUDE_CODE_SESSION_ID` 即原主人）⇒ 轉成 `.resumed`、清掉舊格式 `.ack`（**已於複審前完成**；〈六〉P3-a 之後同樣的舊格式 `.ack` 不再被 `--ack` 自動清掉） |
| 守衛面 hook 一行（已套用，見〈六〉P3-b） | `.claude/hooks/context_budget_guard.py` SessionStart 呼叫 `announce_handbacks(..., sid=payload.get("session_id"))`；不套用時 `announce` 退用環境變數 `CLAUDE_CODE_SESSION_ID`，功能不缺只少一條來源 |

## 六、複審 P3 三條收尾（2026-11-19，SD 單人窗口；DEF-200-619～621）

| 項 | 成因／修法／驗證 |
|---|---|
| P3-a 舊格式 `.ack` 兩處判準不一致（DEF-200-619） | 成因＝`seal.mark_resumed` 刪舊格式 ack、`handed_over` 卻保守視為別人接手。修法＝`mark_resumed` 只清**自己 sid** 的 `.ack`，別的 sid 與舊格式一律保留（兩處同一判準）；`handoff --ack`（原主人）遇舊格式印出舊 `.ack` 路徑與處置；`seal.legacy_ack` 為判準。取捨＝ADR-XPLAT-004 §2.19 D7〈舊格式取捨〉：本機 19 份舊格式 `.ack` 全為早已完成的真交棒（2026-11-19 現查 `~/.autosdd/handoff`），舊格式為封閉集合、無可靠機器判別依據，故不自動遷移。驗證＝`test_sessionctl_seal.py::SelfResumeTest::test_mark_resumed_clears_only_the_owners_own_ack`（含 `handed_over` 一致性）、`::test_legacy_ack_predicate_only_matches_an_ack_without_sid`、`test_sessionctl_handoff.py::test_owner_ack_over_a_legacy_ack_keeps_it_and_says_so`、`test_sessionctl_keepwarm.py::…self_resumed…`；真機 RV-C4 新增丙段（舊格式 ack ⇒ 保留並印提示，純 CLI） |
| P3-b hook 接線突變存活（DEF-200-620） | 補 `test_context_budget_guard.py::HandbackSessionStartAnnounceTest::test_the_hook_hands_the_payload_session_id_down_to_the_announcement`（`guard.main()` 實跑；原主人 sid 得「本 session 自己封存」、別人得「未接手的交接包」）。**不動 hook**（LOC 棘輪滿檔）。突變驗證（拋棄式 worktree，已移除）：未突變 `Ran 7 OK`；hook 該行改成 `sid=None` ⇒ 該測試 FAIL（`'本 session 自己封存' not found`）＝殺死 |
| P3-c RealVerify 失敗不留證據（DEF-200-621） | 成因＝案例判失敗後沙盒（含 `~/.claude/projects/<slug>` 逐字稿）隨清理一起刪光，2026-11-19T02:07:49Z RV-C4 fail 291 秒的根因無從查起。修法＝`runner.run_case` 在失敗／例外且**清理前**呼叫 `CaseContext.keep_failure_evidence`：把每個沙盒的逐字稿、`hook_events.jsonl`、`debug_*.log`、`traces/` 複製到持久目錄 `~/.autosdd/realverify_kept/<案例>_<時刻>/sandbox<i>_<sid8>/`，路徑印在失敗訊息、notes 與帳本證據欄；通過與 env 缺件不留（不累積殘留）。驗證＝`test_realverify_lib.py::FailureEvidenceIsKeptTest`（通過不留／失敗留且沙盒仍清掉／env 不留） |
| P3-c 根因（已重現並查明） | 本棒真機 RV-C4 前 6 次連跑全 pass，第 7 次（改動 handoff 輸出後重驗）於 2026-11-19 15:47 重現逾時 280 秒，**保留證據機制當場救下逐字稿**（`~/.autosdd/realverify_kept/RV-C4_20261119T154738/`，已於查明後清除）。時間線（hook_events＋逐字稿＋debug 日誌）：15:42:59 甲組提示 ⇒ 15:43:03 Stop（背景 shell 啟動）⇒ 15:43:22 背景 shell 結束的 task-notification ⇒ 15:43:24 Stop 被**保溫閘**推回「請掛 `sessionctl keepwarm`」⇒ 15:43:31 模型（haiku）照做、把 `keepwarm`（預設 45 分鐘）掛成背景行程 ⇒ 15:43:33 Stop 放行 ⇒ debug 日誌 15:43:38「Waiting for background work to finish」⇒ `claude -p` 一直等到牆鐘 280 秒逾時被砍。成因＝甲組（自續跑）正是保溫閘「該掛」的情形，模型是否照推回指示做是隨機的（故低頻；2026-11-19T02:07:49Z 那次 291 秒同型）。修法（消除成因）＝RV-C4 的兩個 `claude -p` 回合設 `AUTOSDD_KEEPWARM_OFF=1`（只關保溫閘；被測的冷叫醒閘不受影響，保溫判決本來就由後面真跑 `keepwarm` CLI 驗）。連帶發現：逾時只砍 claude 本體 ⇒ 背景行程握著沙盒目錄，清理報 RESIDUE；`driver._kill_tree` 改連子行程樹一併砍（`test_realverify_lib.py::TimeoutKillsTheWholeTreeTest`） |
| RV-C3 在 worktree 內 rc=1 | 成因＝事故重放的真逐字稿母體住主 checkout 的 `~/.claude/projects/<主 checkout slug>`，worktree 路徑 slug 對不上。修法＝`sandbox.main_checkout_root`（`git rev-parse --git-common-dir`）算主 checkout，worktree 內改以 `--base` 指向它；母體目錄不存在 ⇒ `EnvMissing`（rc 2，大聲報、不默默 skip）；非 worktree 行為逐位元組不變。驗證＝`test_realverify_lib.py::MainCheckoutRootTest`（真 git worktree）；真機＝在拋棄式 worktree（junction `.venv`）跑 `realverify run --case RV-C3` ⇒ `REALVERIFY_VERDICT=pass n=1`（已移除 worktree） |
| 真機自驗末行（本棒，最終程式碼） | converge 家族 `pass n=4` 連 2 次、RV-C4 單跑 3 次 `pass n=1`（關保溫閘後）、`sessionctl_handoff pass n=5`、`sessionctl_keepwarm pass n=5`、RV-C3 於 worktree `pass n=1`（該次於逾時修法前跑，RV-C3 不受其影響）；殘留 0（`AutoSDD_RV_*` 排程、`AutoSDD_RV_sbx_*` 沙盒、worktree 皆查過） |

## 七、UX：監督／保溫的正常結果不得呈現成錯誤（2026-11-19，SD 單人窗口；DEF-200-622／623）

暴露證據＝掌舵者真機畫面回報（sid `31ea79d4`）：`Background command "Arm main-session keepwarm" failed with exit code 6`（一天十多次），與 Stop 出聲「本回合結束時仍有 背景任務在跑：（1 個背景 shell）…TaskStop」（當時唯一在跑的是依設計掛的 keepwarm）。設計全文＝ADR-XPLAT-004 §2.19.1 D8。

**新舊 rc 對照**（harness 對背景指令任何非 0 結束都標 `failed`，正常叫醒不得非 0）：

| 指令／判決 | 舊 rc | 新 rc | 末行 |
|---|---|---|---|
| `keepwarm` ping／cap／skip | 6／7／0 | 0／0／0 | `KEEPWARM_VERDICT=<判決> …`（不再帶 `rc=`） |
| `watch` all_done／overrun／stall／budget／quota／keepwarm | 0／2／3／4／5／6 | 全 0 | `WATCH_VERDICT=<事件> n=<N>`（不再帶 `rc=`） |
| `waitfor` done／pending | 0／3 | 0／0 | `WAITFOR_VERDICT=done rc=<被等指令 rc>`／`pending seg=i/12` |
| 缺 `--sid`、`waitfor` 參數錯 | 2 | 2（真錯誤，不變） | stderr |
| `runlong` | 被跑指令的 rc | 不變（被等指令真失敗時標 failed 是正確訊息） | — |

**rc 消費者盤點**（先 grep 全 repo 的 `KEEPWARM_VERDICT`／`WATCH_VERDICT`／`RC[`／`returncode`／`rc ?[=＝] ?[2-7]`；無任何消費者真需要靠 rc 分辨事件，故未停下回報）：

| 消費者 | 處置 |
|---|---|
| `tools/lib/sessionctl/{watch,keepwarm,longwait}.py`（`RC`／`RC_PENDING` 表、處置表、閘訊息、`UNKNOWN_DISPOSAL`） | 表刪除、一律 `return 0`、訊息改「看末行」 |
| `tools/sessionctl.py` | 薄分派、原樣回傳模組 rc，不需改 |
| `sessionctl_guard.py`／`supervise.py`／`converge.py`／`wastecensus/{supervision,sections_keep,reader}.py` | 不讀 rc（痕跡 `rc` 欄無讀者；`EV_*` 名稱不變）；`supervise._WATCH_CMD_RE` 改指 `roster.WATCH_CMD_RE`（單一家） |
| `.claude/**` | 零處需改（`sessionctl_guard.py` 文字不含 rc 語意；本棒未動 `.claude/`） |
| 單元測試 `test_sessionctl_{watch,keepwarm,longwait,hooks}.py` | 改斷言末行與 rc 0，附反向變體（`hasattr(RC)`、末行無 `rc=`、痕跡無 `rc`、CLI 子行程 quota 事件 rc 0、字面相近的 `echo keepwarm watch` 仍報） |
| RealVerify `sessionctl_{keepwarm,watch,longwait,converge}`（RV-KW1～4、RV-W1～6、RV-LW1、RV-C4） | `_check_verdict` 簽名去 `want_rc`；環境缺件判定由「rc≠5」改為「末行非 quota」；其餘斷言 rc 0＋末行 |
| CLAUDE.md、ADR §2.18.1／§2.19.1（D3／D5／新 D8）、TCS-SessionCtl、TCS-SessionSwitch-CostModel（REQ／AT／E2E／V 列＋新 §3.5c）、DES §4 | 同 commit 改寫；歷史帳（`RealVerify_Result_Ledger.md` 舊行、缺陷帳舊列）保留作史料 |

**Stop 出聲（DEF-200-623）**：`roster.is_supervision_shell`（`WATCH_CMD_RE`／`KEEPWARM_CMD_RE`，容忍腳本路徑後引號）判出的 shell 不計入「仍在跑的背景任務」；只剩它們時**不出聲**。二擇一取「不出聲」的 WHY＝存在與否已由監督閘（有在飛代理時）、保溫閘（無背景工作時）各自推回把關，正常運作不需每回合再說；「保溫中（下次叫醒約 HH:MM）」需讀逐字稿算錨點，增加 Stop 路徑 I/O 與失效面。有別的背景 shell 時照舊出聲且只數別的；有子代理時 `watching_text` 看管中字樣照舊。

**真機自驗（當回合真跑）**：新增 `RV-KW6`（真 `claude -p`＋repo 真 Stop 守衛，背景掛真 `keepwarm --min 1`）、`RV-KW7`（同載具掛真 `watch --grace-sec 20`）：Stop payload 恰一個 running 的該 shell（前提）、真 Stop hook 無「背景任務在跑／TaskStop／擁有者」警告語、harness 完成通知 `completed (exit code 0)` 且無 failed、痕跡判決 ping／all_done。首次 RV-KW7 因斷言面錯誤（逐字稿只收完成通知、不收背景指令輸出）自己報紅並留證據，改取痕跡判決後 `RV-KW6 pass`、`RV-KW7 pass`（`realverify.py run --case`，逐字稿座標見 `RealVerify_Result_Ledger.md` 本輪入帳列）。誠實劃界：畫面上「failed」字樣的**渲染**由 harness 決定，本載具只能機驗「完成通知為 completed／exit code 0」這個成因面；掌舵者目視仍可補一次（非阻塞）。

**帳本順手修正**：`AutoSDD_Defect_Log.md` DEF-200-604／605 補 `7c38492c`（`git log -S` 查實）、DEF-200-609 補 `9f757344`；609「待重測」查實＝V-F1 已於 R215 盤點改列備援路徑、由 RV-F1 機驗（見 `CrossPlatform_R215_PendingVerification_Closure.md` 盤點列 46），冷窗轉送的真機畫面目視＝掌舵者目視（非阻塞），已據實改寫。
