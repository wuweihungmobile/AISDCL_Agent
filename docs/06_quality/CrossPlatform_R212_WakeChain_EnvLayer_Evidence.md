# CrossPlatform R212 額度喚醒鏈五缺陷（DEF-200-516 家族）與額度參數檔分層（DEF-200-520）證據檔

- **輪籤**：R212（2026-10-11，macOS 真機；主控 Fable 5.1 兼 Architect；SA 設計備忘錄 4 份、Developer 與修復包 7 包、審查鏡 5 面、收尾單人窗口，子代理皆 Sonnet）
- **輪型**：R 系列（守衛面／跨平台護欄層）。依範本〈🏁〉T2「走軌道① 還是 R 系列由根因所在面決定」：DEF-200-516 家族與 DEF-200-520 在守衛面 ⇒ 走本檔；DEF-200-518 在產品面 ⇒ 走軌道① T1 最小響應（直接修＋測試＋帳本，不產四件套），其修法與證據同寫在本檔〈二〉，便於同一個 commit 對帳。
- **起點**：HEAD＝9032bebf；`python tools/check_defect_log_crossref.py --unresolved-count` 開場實跑〔收尾親跑〕＝「未結列數＝2」（DEF-200-516、DEF-200-518）；外部阻塞軌 5、結構性長債軌 6。
- **體例**：不使用前瞻輪號的「延後／交給」句型；數字標〔收尾親跑〕＝本場收尾單人窗口自己跑的輸出，〔他包回報：包名〕＝只讀報告、沒重驗；不抄寫 pytest 通過數字的字面（以「通過 N 支」代稱）。痕跡座標中的 J 編號＝痕跡 jsonl 的行號（`$TMPDIR/autosdd_resume_log_autosdd_resume_plan_<sid>.jsonl`）。

---

## 〈一〉掌舵者原文（T1）與立案

**T1 原文（2026-10-11，逐字；授權主控代決，子代理一律 Sonnet、主控 Fable）**：

- 「請徹底完成以上任務，找到沒法完成收斂的根因，徹底解決」
- 「完成實作 AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md」
- 「如何將兩邊的 .env 同步，哪邊才是正確完整的？這個參數檔該如何維護？」

| DEF | 面 | 嚴重度 | 來源 | 分流 | 本檔寫成時 |
|---|---|---|---|---|---|
| DEF-200-516 | 守衛面（planner） | P2 | 開場帳本列（上一個 commit 登記；本機 sid 5535e815 續航實錄；範本 T2 再開事件，承接輪次「未指派」） | R 系列（本檔） | fixed |
| DEF-200-518 | 產品面（Kernel） | P2 | 開場帳本列（F-SBR-001 QA 鏡核證據檔 C4 修前對照；範本 T2 再開事件） | 軌道① T1 最小響應 | fixed |
| DEF-200-520 | 守衛面（取數層）＋引擎 `config.py` | P3 | 掌舵者 T1 第 3 句（直接立案，**不是**缺陷暴露，故不套暴露度三取一） | R 系列（本檔） | fixed（D-1 兩半同一個 commit 為前提，見〈二〉-6） |
| DEF-200-521（7-A）／522（7-B）／523（7-C）／524（7-E） | 守衛面（`resume_route`／`relay_machine`／`schedule_backend`／`quota_messages`） | P2 | 設計階段（SA-1／SA-4）以 sid 5535e815 痕跡逐段對時間線所發現的同源接縫缺陷，各有真機痕跡或真實語料 | R 系列（本檔） | fixed |

- 516／518 兩列是範本〈🏁〉T2（缺陷帳本新立 P≤2 未結列）的載體；掌舵者 T1 一句使其解鎖並授權徹底處理。521～524 與 516 同輪新立、同輪 fixed，不產生新的未結列。
- 掌舵者問題 2「完成實作 PRD v2.1」的處置見〈六〉；問題 3（.env 同步）＝DEF-200-520，答案與維護程序見〈二〉-6 與〈八〉。

---

## 〈二〉根因與修法

### 二-0 「沒法完成收斂」的根因：兩層結論（掌舵者 T1 第 1 句）

1. **直接根因（一層）＝A-1 入口時間閘缺席**：`_resume_tick` 把「被叫醒＝時刻已到」當成不變式（Windows `-Once` 單觸發器下為真），但 mac 後端為了自我修復底盤，把 `StartInterval=900` 與 `StartCalendarInterval` 同時掛進同一支 launchd job（既有鎖 `test_mac_endurance_r83.py` 要求保留）；interval 在 calendar 之前 2 小時 16 分叫醒 tick，而 tick 入口沒有任何 reset 時間閘，直接以 L0（端點新鮮且各軸 <100%）判額度已恢復並 spawn 續跑窗。A-1 把閘加在不變式被破壞的那一層。
2. **結構根因（二層）＝這條鏈的接縫從未在真後端被端到端跑過**：為什麼「修一個、真機又出下一個」？
   - 測試替身只建模 Windows 語意：`_StatefulFakeSchedulerBackend.disarm`（`tools/tests/test_context_budget_guard.py`）是同步移除，所以 mac 的「延後 bootout」讓 7-C 在全綠測試下隱形；
   - 7-A、7-B、7-C、7-E 全在「到點之後」那一段（spawn→收尾→哨兵重掛／halt 標記讀取），而本輪真機驗收為零 token、刻意帶 `--no-allow-resume`，只走到探測；到點後那一段仍只有替身與隔離重現；
   - sid 5535e815 的痕跡本身就是證據：J011→J022 一次走完五個接縫缺陷（見各項暴露證據）。
3. **收斂的誠實定義**：可以宣稱「五個真機暴露的缺陷已修，各有紅綠測試，入口時間閘已在真 launchd 驗過」；**不能**宣稱「不會再有下一個接縫缺陷」。本 repo 的收斂是症狀驅動（範本〈🏁〉），不是「沒有缺陷」；到點後尾段的自然發生判讀欄位見〈三〉末與〈五〉#4。

### 二-1 DEF-200-516（A-1：入口時間閘）

- **缺陷**：手動一次性續航在 reset 前被 900 秒 interval tick 叫醒並 spawn（reset 前 2 小時 16 分：23:45:55 `woken`，calendar 為 02:02）；收尾拆排程 ⇒ reset 時刻零續跑。
- **根因**：見〈二〉-0 第 1 點；`quota_open` 以「各軸 <100%」判（PRD v2.1.17 註記 C2 已把「端點新鮮且每軸 <100%」定為現行「已恢復」判準），與 `band=halt` 矛盾的是**時間**而不是判準，所以不改 `quota_open` 定義。
- **修法**：`tools/lib/relay_machine.py::reset_not_reached`（純函式；整秒比較；對缺鍵／空字串／垃圾／過去值／`kind=="sentinel"` 一律不適用）＋ `tools/session_resume_planner.py::_resume_tick` 入口閘（位於 `woken` 留痕之後、`probe_quota` 之前；早醒＝不探測、不 spawn、不動無進展計數，依 reset 重掛一次性排程，事件 `resume_tick_early`，欄位 `due_at`／`reset_at`／`remaining_seconds`）。planner 淨增 4 條斷言行（746→750，**餘裕 0**，見〈五〉#17）。
- **紅→綠**：Dev-A 報告原為 14 支新測試（12 紅、2 綠）；Dev-D 把 7-A 兩支併成一支後終版 13 支、12 紅、1 綠（T9 前提釘）〔他包回報：Dev-A／Dev-D；QA 鏡核對〕；其中 516 屬 8 紅（T1／T2／T3a／T3b／T4／T5／T6／T8）＋1 前提釘（`New-ScheduledTaskTrigger -Once -At` 在、`Repetition` 不在）。修前事件序列逐字：`['woken', 'probed', 'relay_stopped', 'relay_rearmed'] != ['woken', 'resume_tick_early']`。審查後 Fix-R2 補 1 支「早醒重掛失敗路徑」（`RearmAndSentinelRearmedBranchesAlsoAlertLoudOnFailureTest`）：突變 MA3（`return rc`→`return 0`）與 MA4（拿掉 `_alert_on_rearm_failure`）在補測前全部相關模組存活、補後各被殺〔他包回報：Fix-R2〕。
- **暴露證據**：sid 5535e815 痕跡 J011（2026-10-10T23:45:55+08:00 `woken`）→ J012（`probed` `quota_open=true`、`source="endpoint"`、6 軸皆 <100%、最高 `weekly_all=96.0%`）→ J013（`route_chosen SESSION_RESUME`）→ J016（23:50:45 `resumed rc=0`）→ J017（`relay_done` `band=halt` `gc_plans=1`）〔收尾親讀〕；launchd 自報憑證 `run interval = 900 seconds`＋`StartCalendarInterval = Month=10-Day=11-Hour=2-Minute=2`〔SA-1 備忘錄 §6〕。修後真機驗收見〈三〉。

### 二-2 DEF-200-521（7-A：handback 標題帶後綴即判 DONE）

- **缺陷**：handback 的「## 下一步指令」標題帶後綴（例：「## 下一步指令（互動視窗，…）」）即被判無未完項 ⇒ 誤判 DONE、拆排程。
- **根因**：`relay_machine._section_text` 以整行相等比對標題字串，而 `resume_route.handback_verdict` 用子字串；續跑 prompt（`_RESUME_RULES`）自己就把標題寫成帶後綴形態，模型照樣輸出。
- **修法**：`tools/lib/resume_route.py::heading_hit` 為唯一規則，三處共用：`handback_verdict`、`relay_machine._section_text`、`sentinel_lifecycle._section`（順帶，同型缺陷）。規則最初取子字串，審查後 Fix-R2 收緊為行首規則（`line.lstrip().startswith(marker)`）：「前文某行只是提到標題字樣」的反例不再把取節起點提前。
- **紅→綠**：`HandbackHeadingIsOneRuleTest` 2 支修前紅（「帶後綴且有未完項不是 DONE」`'DONE' != 'RELAY_NEXT'`；「判決與取節共用一條規則」修前 `heading_hit` 不存在）；`sentinel_lifecycle._section` 另 1 支（`HandbackSessionStartAnnounceTest::test_vb3_a_suffixed_next_step_heading_still_speaks_its_section`，修前出聲文字為 `## 下一步指令` 加「（節空白）」）〔他包回報：Dev-A／Dev-D〕。Fix-R2 把 QA 反例併入 7-A 測試，突變 `HH_substring_rule`（退回子字串）被殺。
- **暴露證據**：本機真 handback 2／2（`~/.autosdd/handback/5535e815-423c-478b-bb4c-9cf8a020528c.md`、`~/.autosdd/handback/b80b257b-a1f5-40dc-8c14-63ebd3bebcbd.md`）標題皆帶後綴；修前 `_section(下一步指令)` 長度 0、修後 597／4179（Fix-R2 改行首規則後重算相同）；`resolve()` 對真檔實跑修前回 `DONE`（反事實：精確標題回 `NO_PROGRESS_STOP`）〔Dev-D 報告 §11、SA-1 備忘錄附錄；Architect 鏡獨立重算長度與備忘錄逐字相同〕；痕跡 J017 `relay_done`（DONE）。
- **誠實劃界**：行首規則仍是「標題字樣之後不查邊界」，形態 D／E 與檔首 BOM 的殘餘見〈五〉#18；不宣稱此規則零誤判。

### 二-3 DEF-200-522（7-B：非 loud 停止次態先 GC 任務書再寫它）

- **缺陷**：`settle_window` 的 DONE／QUOTA_STOP 兩條路先收掉本窗任務書、再寫它 ⇒ `FileNotFoundError` 假崩潰；重掛哨兵也因任務書不存在而 `arm_failed`。
- **根因**：非 loud 的 `escalation.alert(plan=plan)` 會 GC 本窗任務書，隨後 `write_relay(plan, state)` 與 `_arm_sentinel` 都需要它；只有「之後不再有人站在這份任務書上」時 GC 它才對，而 `settle_window` 的四個停止次態一律重掛哨兵。
- **修法**：`tools/lib/relay_machine.py::settle_window`：非 loud `alert` 不再點名本窗任務書（`plan=plan` 只在 loud 分支才有作用）；≥7 天的超齡殘骸照收。
- **紅→綠**：e2e `ManualRegisterThenWakeE2ETest` 兩支（DONE／QUOTA_STOP）修前紅，事件序列逐字 `['woken', 'probed', 'relay_done', 'arm_failed', 'relay_settle_crashed']`／`['woken', 'probed', 'relay_stopped', 'arm_failed', 'relay_settle_crashed']`〔他包回報：Dev-A〕。
- **暴露證據**：sid 5535e815 J019（2026-10-10T23:50:45+08:00 `relay_settle_crashed`，`error="FileNotFoundError(2, 'No such file or directory')"`）〔收尾親讀〕。

### 二-4 DEF-200-523（7-C：mac 續航 job 自拆後 INV5 把自己當另一擁有者）

- **缺陷**：mac 續航 job 收尾時對自己 `disarm`（延後 bootout），緊接的 `_arm_sentinel` 走 INV5 單一擁有者判斷，`list_jobs` 仍列出尚未拆除的自己 ⇒ 哨兵讓位、尾段之後零排程（`relay_rearmed rc=0` 與零 job 並存）。Windows 的 `Unregister-ScheduledTask` 立即生效（依讀碼），沒有這個窗口。
- **根因**：`LaunchdBackend.disarm` 的自拆是延後 bootout（`_SELF_DISARMED`），而測試替身是同步移除（〈二〉-0 第 2 點）。
- **修法**：`tools/lib/schedule_backend.py::LaunchdBackend.list_jobs` 回「邏輯現況」：扣掉本行程已自拆且 plist 已不在者（隱藏條件未放寬；別支活 job 照舊讓位）。
- **紅→綠**：Dev-D 5 紅（`SelfDisarmTest` 的 `list_jobs` 1 支＋`ResumeJobSelfDisarmThenSentinelArmTest` 4 格 DONE／NO_PROGRESS／QUOTA_STOP／PATROL），對照 subTest（別支活 job 照舊讓位）修前後皆綠；修前紅訊息逐字 `['relay_done', 'sentinel_single_owner_deferred', 'relay_rearmed']`〔他包回報：Dev-D〕。
- **暴露證據（只引 sid 5535e815）**：J017（`relay_done`）→ J018（同秒 `sentinel_single_owner_deferred`，`owner=AutoSDD_SessionResume_5535e815-…`）→ J019 → J020（2026-10-11T00:43:35+08:00 `sentinel_armed`，hook relatch 補回）：其間 52 分 50 秒零排程；`~/.autosdd/traces/autosdd_sentinel_bootout_AutoSDD_SessionResume_5535e815-423c-478b-bb4c-9cf8a020528c.log` 逐字「parent-gone waited=1s at 2026-10-10T15:50:46Z」「bootout rc=0」〔收尾親讀〕。**不引 sid 46b55125 的 10:22:03**：那一次走 `quota_back_no_resume` 分支，只拆自己、設計上本來就不掛哨兵（見〈三〉〈五〉#5）。
- **狀態**：C-A 修後**未在真 launchd 實跑**；唯一無法隔離證明的格子＝job 行程內對另一個 label `bootstrap` 是否被 launchd 允許（失敗非靜默：`arm()` rc≠0 ⇒ loud）。

### 二-5 DEF-200-524（7-E：自願 halt 標記幾乎立即過期）

- **缺陷**：自願 halt 標記被判過期得太快，哨兵落回 idle patrol、不在 reset 時刻叫醒。
- **根因**：`halt_verdict` 以「最新逐字稿活動晚於標記 `at` ＋ `HALT_MARKER_ACTIVITY_SKEW_SECONDS`（10 秒）」判標記過期（立案前提：自願停機不會讓逐字稿繼續更新）；但 halt 通知本身說收斂型工具照常可用 ⇒ 標記後不到幾秒就有活動 ⇒ 標記立即失效。
- **修法**：`tools/lib/quota_messages.py::halt_verdict`：有 reset 的標記，失效＝兌現時刻（`reset_at＋HALT_RESET_SKEW_SECONDS`）之後逐字稿仍有活動；兌現時刻已到須靜止 ≥ `HALT_QUIESCE_SECONDS`（900，與 planner 巡邏間隔 parity 鎖）才 probe，否則回 `patrol` 並於 reason 明說「halt 標記…不叫醒（防雙窗）」（不 fail-quiet）；無 reset 的標記保留舊規則。3 支既有測試的期望值改動屬語意修正（被證偽的前提；`test_activity_beyond_the_skew_tolerance_is_still_stale` 改名反轉，其餘兩支夾具調整、期望值不變），真正的「已續跑不叫醒」鎖一支沒少。
- **紅→綠**：`HaltVerdictTest` 修前 failures=4、errors=1（`AttributeError: module 'quota_messages' has no attribute 'HALT_QUIESCE_SECONDS'`；`None != 'arm_reset'`）、e2e `SentinelTickConsumesHaltMarkerE2ETest` failures=1（`900.001247 != 720 within 2 delta`）；Fix-R2 補 `idle=None` 格（突變 ME5 被殺）〔他包回報：Dev-D／Fix-R2〕。
- **暴露證據**：`~/.autosdd/traces/halt_*.json` 真標記 5 份（9ea68d33、c00d202a、da844569、e1a2d13c、5535e815；〔收尾親列檔案〕）：首筆逐字稿活動距標記 14.5／34.6／17.5／430.0／23.8 秒即超過 10 秒容忍窗、36／36 個後續 tick 同；c00d202a 兌現後零活動＝該被叫醒卻永不會被叫醒的那一份〔SA-4 備忘錄；SA 鏡獨立重算 5 份標記普查一致，36／36 與收尾均未重算〕；sid 5535e815 標記 `at=2026-10-10T23:33:22.756171+08:00`、`reset_at=2026-10-10T17:59:59.799057+00:00`（收尾親讀），哨兵第一次讀標記是 J021–J022（00:58:35 `sentinel_decided patrol`，`controller_idle_seconds=326.79`）。

### 二-6 DEF-200-520（額度／模型參數檔跨機分層：`env.shared` ＋ 四層載入鏈 ＋ `--env-doctor`）

- **缺陷**：額度參數檔無跨機同步面。`.env` 不入庫，舊機器的複本每一行都遮住共享決策；引擎與 harness hook 各讀一條鏈；本機 `.env` 複本落後生成物 11 鍵（`--env-doctor` 真機輸出：16 筆 `[redundant]`＋資訊 `[stale-copy]`，結論行逐字「結論：16 個問題 ⇒ rc=1　修復：python tools/lib/quota_policy.py --env-doctor --fix」〔收尾親跑〕）。
- **三個問題的答案**：①「兩邊哪個 `.env` 才正確完整？」都不是——完整鍵清單是 `.env.example`（程式印出的生成物，不是要複製的範本），該用的值是 `env.shared`（決策）＋出廠值；②怎麼同步：改 `env.shared`、`git push`，另一台 `git pull`（喚醒排程每次 tick 都重新啟動 planner 現讀檔，不必重新武裝）；③怎麼維護：`python tools/lib/quota_policy.py --env-doctor`（rc=0 乾淨；rc=1 逐行點名多餘／遮蔽共享／壞值／重複鍵／BOM），確認後加 `--fix`（先備份成 `.env.bak.<UTC 時間戳>`、只刪該刪的行）。本機專屬例外只寫在 `.env`，行尾加 `# override-ok: <WHY>`。
- **修法**：追蹤檔 `env.shared`（15 行；`AUTOSDD_QUOTA_HALT_PCT=98`、`AUTOSDD_MODEL_HELMSMAN=fable`、`AUTOSDD_MODEL_SUBAGENT=sonnet`、`AUTOSDD_MODEL_DOWNGRADE=haiku`，每鍵上方一行 WHY）；載入鏈（高→低）：行程 env ＞ `AutoClaude/.env`（引擎 3 鍵）＞ 根 `.env` ＞ `env.shared` ＞ 出廠 `ENV_SPEC`；`tools/lib/quota_env_layers.py`（`merged_file_env`＝鏈的 SSOT；`diagnose`／`_fix_one`／`doctor_cli`）；`tools/lib/quota_gate.py::policy_env` 改讀 `merged_file_env`；引擎 `AutoClaude/autoclaude/utils/config.py::_ENV_FILES` 三元組＋`_quota_env` 命中判定（空白值不遮蔽下層，兩側同語意）；`tools/lib/quota_policy.py` `__main__` 加 `--env-doctor` 分支；`.env.example`（`--print-env-example` 生成物）檔頭；`ONBOARDING.md` §2.2 與 §5 一列；兩支 compat-ci workflow 的 `paths` 加 `env.shared`、`tools/lib/quota_env_layers.py`。審查後 Fix-R 補：harness `_read` 與引擎同為 `errors="replace"`（cp950 存檔不再整層丟棄）、doctor 加 `[bom]` 旗標（rc=1）、`env.shared` 重複鍵／BOM／未宣告鍵鎖、三份使用者指南在 `cp .env.example .env` 之後補一句（在 `AutoClaude/` 下執行 `python ../tools/lib/quota_policy.py --env-doctor --fix`）、使用者可見字串「.env 有設錯」改「env.shared（跨機）或本機 .env」。
- **D-1（治理面保護，兩半缺一不可）**：`.claude/hooks/block_destructive_git.py` 的 `_GOV_EXACT` 追加 `env.shared`、`tools/lib/quota_env_layers.py` 兩項（hook 740→741／750；hook 半由掌舵者親手套用補丁——auto 分類器對 `.claude/**` 的 Self-Modification 拒絕，依權限姿態不繞）；測試半 `tools/tests/test_block_destructive_git_r83.py` 的 `PROTECTED` +2 已在位。驗證指令：`cd tools/tests && python -m unittest test_block_destructive_git_r83 -q` 須印 238 OK；只有測試半時 2 紅（`test_every_protected_file_is_blocked_when_unattended` 的 `rel='env.shared'`／`rel='tools/lib/quota_env_layers.py'`：`AssertionError: 0 != 2`），只有 hook 半則 238 OK 但新項沒有牙〔Architect 鏡副本實測〕。**本列結案以兩半同一個 commit 為前提**：若 hook 半未落地，本列「保護面」一句不成立，須改寫為「已知缺口：無人窗口可改 `env.shared`」並登〈五〉。
- **紅→綠**：`test_quota_env_layers` 31 支（新鎖檔；新模組沒有「修前紅」，改以突變證明鑑別力：Dev-C N1～N4 全被殺；Fix-R 的 cp950 案修前 `Tuples differ: (91.0, 98.0) != (91.0, 91.0)`、BOM subTest 修前 `(0, False) != (1, True)`〔他包回報：Dev-C／Fix-R〕）。
- **暴露證據**：掌舵者 T1 第 3 句（原文見〈一〉）。D-1 的暴露證據＝本變更自造的回歸：把停機線的有效來源從受保護的 `.env` 搬進不受保護的 `env.shared`、並把「讀哪些檔」的邏輯從受保護的 `quota_gate.py` 搬進不受保護的新檔——無人值守 `Write` payload 餵 hook：`env.shared` rc=0、`tools/lib/quota_env_layers.py` rc=0、`.env` rc=2（Dev-C 與 Architect 鏡各量一次）；PRD §12／§15.5 紅線 10 字面把 `.env` 列為禁寫，R87（改取數層繞過 halt ⇒ 13 agent 全滅）是同類真事件。
- **未涵蓋**：`quota_policy_env.py`（出廠值）、`relay_machine.py`、`resume_route.py`、`model_roles.py`、`AutoClaude/.env` 同一收錄判準下仍不在 `_GOV_EXACT`（既有狀態、非本輪造成；〈五〉#24）。

### 二-7 DEF-200-518（產品面：Kernel 路徑 ESCALATION 不產 dump／通知／演化提案）

- **缺陷**：`AutoClaude/CLAUDE.md` 宣稱 ESCALATION 會通知＋EscalationDump＋自動演化，但 Kernel 正式路徑 `autoclaude/` 無 `ON_ESCALATION` 的 emit 點；F-SBR-001 C4 真跑 `escalated=True` 後 `checkpoints/` 空、log 零「EscalationDump」（`AutoClaude/docs/03_testing/SddBridge_RealRun_Evidence_20261011.md` C4）。
- **根因**：接線缺口（SA-2 判定方案 A）：「收斂判 escalate」與「重試耗盡」兩個失敗型出口從不 emit。
- **修法**：`AutoClaude/autoclaude/core/kernel.py::_announce_escalation`（兩段式、fail-soft：先 `ON_ESCALATION_DUMP_REQUEST`、後 `ON_ESCALATION`，兩段各自 try/except）；`core/hookspec.py` `EscalationDumpedResult.dump`；`core/resolution_policy.py` `MergedResult.escalation_dump`；`plugins/checkpoint/_phase_handlers.py`（無 tracker 但有 `failure_history` 時於 plugin 層重建 `FailureTracker`）；`utils/checkpoint_manager.py` 公開唯讀 `checkpoint_dir`；`plugins/sdd_governance_plugin.py`（`max_retries_exhausted` 略過，防與 ON_FAILURE 重複諮詢）；`run()` 的 ESCALATE 分支印 `=== STATE: ESCALATION | step=… |`。veto／使用者中斷／Brain 故障型升級刻意不補（D-1 決策，與舊路徑同語意）；`AutoClaude/CLAUDE.md` 僅動一行（仍 400 行）並揭露「Kernel 路徑 dump 已知四處不精確」。
- **紅→綠**：5 個新測試檔（`AutoClaude/tests/core/test_escalation_dump_result_def_200_518.py`、`AutoClaude/tests/core/test_kernel_escalation_emit_def_200_518.py`、`AutoClaude/tests/integration/test_kernel_escalation_artifacts_def_200_518.py`、`AutoClaude/tests/plugins/test_checkpoint_dump_request_from_history_def_200_518.py`、`AutoClaude/tests/plugins/test_sdd_governance_escalation_dedupe_def_200_518.py`）修前「20 紅／7 綠 → 27 綠」〔他包回報：Dev-B〕；QA 鏡 B 審後 Fix-B 追加 4 項（`is_stuck` 參數化 2 案、善後拆兩個 try 1 支、多步驟案例 1 支）⇒ 收尾親跑收集 31 項〔收尾親跑〕；QA 突變 Q10／Q11a 修前存活（`rc=0`）、修後被殺（`rc=1`）〔他包回報：Fix-B〕。
- **暴露證據**：F-SBR-001 C4 修前對照（上述證據檔）；範本〈🏁〉T2 再開事件（帳本列開場為 open）。
- **未涵蓋**：QA 鏡 B 理論洞，見〈五〉#27～#31。

### 二-8 守衛面准入對照（根 CLAUDE.md〈守衛面准入〉：新增守衛碼或鎖的前提＝暴露證據；Architect 鏡 §1 核對、座標逐字收入）

| 新增 | 規模（斷言行；HEAD→現值） | 暴露證據（座標見〈二〉各項） | 判定 |
|---|---|---|---|
| planner `_resume_tick` 時間閘（A-1） | planner 746→750 | sid 5535e815 J011～J019；launchd 自報 interval＋calendar 雙觸發；修後真機見〈三〉 | 有 |
| relay_machine `reset_not_reached` | +12（256→268） | 同上 | 有 |
| `heading_hit`／`_section_text`／`sentinel_lifecycle._section`（7-A） | resume_route +3（90→93）、sentinel_lifecycle +1（360→361） | 真 handback 2／2 帶後綴標題被判空白；`resolve()` 真檔實跑回 DONE | 有（真實語料，非探針種子） |
| `settle_window` 非 loud alert 不遞 plan（7-B） | ±0 | J019 `relay_settle_crashed`（真痕跡） | 有 |
| `LaunchdBackend.list_jobs` 回邏輯現況（7-C） | schedule_backend +3（377→380） | J018 後 52 分 50 秒零排程（J020）＋bootout log；只靠 sid 5535e815 | 有 |
| `halt_verdict` 兌現時刻判準＋`HALT_QUIESCE_SECONDS`（7-E） | quota_messages +7（379→386） | 真標記 5／5 於 14.5～430 秒內過期；靜止守門另有真時間線（兌現時刻時已閒置 8 分 15 秒、1 分 44 秒後又有新訊息）〔SA-4〕 | 有 |
| `quota_gate.policy_env` 改讀 `merged_file_env` | quota_gate 494→492（淨減） | 掌舵者 T1 第 3 句 | 掌舵者原文 |
| `--env-doctor` 分支／`quota_policy_env` 檔頭 | +4／+4 | 同上；不進任何閘門判準 | 掌舵者原文 |
| 新檔 `quota_env_layers.py` | 221（400 上限） | 同上；進 hook 判準的只有 `_read`＋`merged_file_env`，其餘為 doctor | 掌舵者原文 |
| D-1 `_GOV_EXACT` +2 項 | hook 740→741（750） | 本變更自造的回歸＋R87 同類真事件（見〈二〉-6） | 有（自造回歸＋同類真事件；非對抗搜尋所得） |

- 沒有「無證據的守衛面新增」。誠實注記：env 層是掌舵者直接立案的功能，照實標「掌舵者原文」而不硬套暴露度；「前提釘」類鎖（T9 schtasks 單一 `-Once` 觸發器、`hasattr(relay_machine, "reset_not_reached")`、`HALT_QUIESCE_SECONDS == SENTINEL_INTERVAL_SECONDS` parity）自身沒有獨立暴露證據，但它們釘的是各自修法的前提，不另列。

### 二-9 本輪明確不改

`quota_open` 定義（PRD v2.1.17 註記 C2）；PRD 任何條文（只在 §16.6 追加一列，母體 101 列不動）；出廠值（`ENV_SPEC`；`env.shared` 的停機線 98 是刻意放寬，出廠值與 PRD §6 字面不動）；五問協定目錄（零改動，不觸發 `PROTOCOL-CHANGED`）；根 `CLAUDE.md`；`.claude/**`（D-1 hook 半由掌舵者親手）；planner 的 A-2 下沉重構（理由見〈五〉#17）。

### 二-10 護欄層行數棘輪重釘（逐檔清單；`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` 收斂值〔收尾親跑〕）

- 淨額 115633→116372（+739）；全額分兩軌：回歸鎖軌申報 309（＝軌上限；DEF-200-516 家族與 DEF-200-520 的回歸鎖），主軌 430 ≤ 516（款(11) 連升第 2 輪；R211 為第 1 輪；R213 起的任一輪主軌必須 ≤ 0）。
- 構成（逐檔）：`test_quota_env_layers.py` 新鎖檔 328、`test_context_budget_guard.py` 14736→14923（+187）、`test_mac_endurance_r83.py` 2210→2305（+95）、`test_sentinel_tick_e2e_r145.py` 308→408（+100）、`test_wake_chain_halt_r278.py` 1067→1079（+12）、`test_block_destructive_git_r83.py` 3422→3424（+2，D-1 測試半）、本檔 `test_adr_xplat001_c1c2_lock.py` 8729→8744（+15：重釘列、回歸鎖軌同輪列、到期兌現註解列、接鏈列、`_FROZEN_GUARD_LINES` 新列）；合計 328＋187＋95＋100＋12＋2＋15＝739。
- 到期義務：`_REPIN_NET_CAP_DUE_ROUND` 212 到期——兌現 `(212, 516)` 並重新武裝 214／515。
- 凍結前綴：`_REPIN_LOG_FROZEN_PREFIX_LEN` 335→336、`_REPIN_LOG_HISTORY_SHA256` 重釘、`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列（f5cb9e3fe7d6 → e62c2eaa57e5，DEF-200-516）；`<!-- guard-total:R212 -->` 兩站：`docs/04_planning/AutoSDD_improving_112.md`、`docs/06_quality/CrossPlatform_R145_Scan_Findings.md`。
- 其他數字釘：skip 樹檔數下限 `tools/tests` 71→72、`AutoClaude/tests` 226→230（照 `run_root_unittests.py` 前置掃描逐字指示）；`MIN_TESTS` 5273→5326（discovery 實測）；ONBOARDING §7 表① `loc-baseline-live` 17797→17857（`sync_onboarding_baselines.py --write`）。表② macOS 欄以乾淨 venv 載具（`python tools/lib/clean_venv_carrier.py`：建→裝→探針→跑→必刪）回填：乾淨 venv 通過 5059 支、skip 222 支（出廠環境值；開發 venv 值不可與它相減）；ci-gate 三軌 1475／1979／362；指紋 v001=8ffe3c3dabbd、v030=6d46814f9084、scripts=ec35ee2838d0、autoclaude=35e0a0326ae2；載具 rc=0、乾淨 venv 必刪完成。

---

## 〈三〉真機驗收（主控親跑，launchd，零 token；只驗入口時間閘，其餘未真機實跑）

**做法（sid 46b55125-6a63-4b4f-9a56-6cbf8d33029c，本機 macOS）**：先卸掉本 session 的哨兵（INV5 單一擁有者：09:56:57 的第一次續航註冊被當時還在的哨兵擋下，見 J017），再以 `--register-schtasks --no-allow-resume` 註冊一次性續航 job `AutoSDD_SessionResume_46b55125-6a63-4b4f-9a56-6cbf8d33029c`（`run interval = 900 seconds`、`StartCalendarInterval = Month=10-Day=11-Hour=10-Minute=22`；reset＝10:20:00.494920、到點＝reset＋120 秒）。`--no-allow-resume`＝醒來那一跑只探測＋留痕、不 spawn、不花 token。

**段一：interval tick（2026-10-11 10:12:27；註冊後約 15 分鐘）——痕跡 jsonl 第 20、21 行逐字〔收尾親讀〕**

```json
{"plan": "/Users/wuweihong/.autosdd/plans/autosdd_resume_plan_46b55125-6a63-4b4f-9a56-6cbf8d33029c.md", "event": "woken", "at": "2026-10-11T10:12:27+08:00"}
{"due_at": "2026-10-11T10:22:00.494920+08:00", "rc": 0, "credential": "launchd gui/501/AutoSDD_SessionResume_46b55125-6a63-4b4f-9a56-6cbf8d33029c｜launchctl print rc=0（不存在時是 113）｜run interval = 900 seconds〔launchd 回讀，與請求相符〕｜argv 回讀 7 項與請求逐項相符｜plist = /Users/wuweihong/Library/LaunchAgents/AutoSDD_SessionResume_46b55125-6a63-4b4f-9a56-6cbf8d33029c.plist〔launchd 自報，證明已持久化〕｜StartCalendarInterval = Month=10-Day=11-Hour=10-Minute=22〔launchd 自報的 descriptor，證明那個時刻真的排進去了〕｜電源姿態＝各電源段 `sleep` 皆為 0（pmset 現查；**這台機器的現況**，不是本專案的保證）｜state = running", "reset_at": "2026-10-11T10:20:00.494920+08:00", "remaining_seconds": 572, "event": "resume_tick_early", "at": "2026-10-11T10:12:27+08:00"}
```

**段二：calendar tick（10:22:03，遲 3 秒）——第 23、24、25 行逐字〔收尾親讀〕**

```json
{"plan": "/Users/wuweihong/.autosdd/plans/autosdd_resume_plan_46b55125-6a63-4b4f-9a56-6cbf8d33029c.md", "event": "woken", "at": "2026-10-11T10:22:03+08:00"}
{"rc": 0, "kind": "none", "quota_open": true, "text": "endpoint@2026-10-11T10:20:04+08:00: 6 軸皆 <100%（最高 weekly_all=20.0% resets_at=2026-10-17T17:59:59.892226+00:00）", "source": "endpoint", "event": "probed", "at": "2026-10-11T10:22:03+08:00"}
{"event": "quota_back_no_resume", "at": "2026-10-11T10:22:03+08:00"}
```

**驗收後**：10:23:04 主控 `--arm-sentinel` 掛回本 session 哨兵（第 26 行 `sentinel_armed`；`launchctl list` 現查只剩兩支 `AutoSDD_Sentinel_*`，零 `AutoSDD_SessionResume_*`〔收尾親跑，見〈十〉〕）：

```json
{"task": "AutoSDD_Sentinel_46b55125-6a63-4b4f-9a56-6cbf8d33029c", "credential": "launchd gui/501/AutoSDD_Sentinel_46b55125-6a63-4b4f-9a56-6cbf8d33029c｜launchctl print rc=0（不存在時是 113）｜run interval = 900 seconds〔launchd 回讀，與請求相符〕｜argv 回讀 7 項與請求逐項相符｜plist = /Users/wuweihong/Library/LaunchAgents/AutoSDD_Sentinel_46b55125-6a63-4b4f-9a56-6cbf8d33029c.plist〔launchd 自報，證明已持久化〕｜**無** calendar ⇒ 只有巡邏觸發，最壞 900 秒後才有人動作｜電源姿態＝各電源段 `sleep` 皆為 0（pmset 現查；**這台機器的現況**，不是本專案的保證）｜state = not running", "handled_through": "2026-10-11T02:23:01.769Z", "event": "sentinel_armed", "at": "2026-10-11T10:23:04+08:00"}
```

**這兩段能證明什麼**

1. A-1 閘在真 launchd 行程內走通：interval tick 停在 `woken`→`resume_tick_early`（`remaining_seconds=572`、`due_at`＝reset＋120 秒），**沒有 `probed`**；credential 回讀 `StartCalendarInterval` 仍為 10:22 且 `state = running`（重掛冪等，未 bootout）；
2. 到點 tick（遲 3 秒）通過閘，走 `woken`→`probed`→`quota_back_no_resume`。

**這兩段不能證明什麼（誠實劃界）**

1. 「早醒不 spawn」：本次註冊帶 `--no-allow-resume`，即使沒有閘也不可能 spawn；證據只剩「沒有 `probed`」。修前反事實（10:12:27 若無閘會 `probed`→`quota_back_no_resume` 自拆、10:22 不會響）推得通，但痕跡裡沒有對照組。
2. **到點後的「spawn→收尾→哨兵重掛」整段未真機實跑**；7-C（C-A 修法）與 7-E（E-A 修法）修後行為同樣**未真機實跑**：兩次 tick（10:12／10:22）用的是 Dev-A 版生產碼（含 A-1／7-A／7-B，不含 7-C／7-E，後兩者 10:26:27 才套用）。
3. **L0 讀數來源未確證**：`probed` 的 `text` 為 `endpoint@2026-10-11T10:20:04+08:00`，比 tick（10:22:03）早 119 秒——很可能是主控 10:20 的 `--pace` 補量留下的快取，而不是 launchd 行程自己取得憑證、發 HTTP 刷新；launchd 無互動環境能否自取憑證，本痕跡沒有任何一筆證據。
4. 邊界：到點恰好（整秒相等）的 tick 沒有真機樣本；Windows 在本輪全無量測。

**10:22:03 之後本 session 零排程的歸因（避免誤引）**：那一次走 `quota_back_no_resume` 分支（狀態塊 `allow_resume=false`）——`tools/session_resume_planner.py` 該分支只 `_schtasks_remove`、不 `_arm_sentinel`（設計：人回來跑 `claude -r`）。launchd log（`autosdd_sentinel_launchd_AutoSDD_SessionResume_46b55125-….log`）逐字：

```text
探針 rc=0 kind=none open=True
判定 resume：探針通過＝額度已恢復
✅ 額度已恢復。狀態塊記著 allow_resume=false（帶了 --no-allow-resume／AUTOSDD_RESUME_OFF，或它是 R79 之前武裝的）⇒ 人回來跑：claude -r 46b55125-6a63-4b4f-9a56-6cbf8d33029c
```

bootout log（`autosdd_sentinel_bootout_AutoSDD_SessionResume_46b55125-….log`）逐字：

```text
parent-gone waited=1s at 2026-10-11T02:22:04Z
bootout rc=0
```

痕跡中間沒有 `sentinel_single_owner_deferred`，所以這次零排程**不是** 7-C 的重演；7-C 的暴露證據只用 sid 5535e815（〈二〉-4）。這個「一次性 job 恢復後不掛回哨兵」的尾段另登〈五〉#5。

**自然發生時的判讀欄位（不是義務）**：到點 spawn 後尾段成功＝痕跡出現 `sentinel_armed` 且 `launchctl list` 含 `AutoSDD_Sentinel_<sid>`、無 `sentinel_single_owner_deferred`；失敗＝`arm_failed`／`relay_rearm_failed`；halt 後第一個 `sentinel_decided` 應為 `arm_reset`（E-A）。

---

## 〈四〉本機閘門與雲端對帳

### 四-1 本機閘門（收尾單人窗口親跑；rc 與尾行逐字）

| 閘門 | 指令（repo 根） | rc／關鍵輸出（逐字或逐項摘錄） |
|---|---|---|
| 根層全套 | `python tools/run_root_unittests.py` | **rc=1**（預期：唯一殘紅＝D-1 hook 半尚未套用）；「✅ unittest 數量下限釘選通過：發現 5326 個測試（下限 5326）」；失敗明細「2 failures / 0 errors / 0 unexpected successes」，兩筆皆為 `test_block_destructive_git_r83.TestGovernanceFilesAreReadOnlyWhenUnattended.test_every_protected_file_is_blocked_when_unattended` 的 subTest（`rel='env.shared'`、`rel='tools/lib/quota_env_layers.py'`：`AssertionError: 0 != 2`）；hook 半套用後預期該模組全綠；「[skip census] tools/tests@darwin 共 47 支：…欠債型 0 支（目標 0）」；✅ 真實 TEMP 圍籬：全套期間真實契約目錄（與 autosdd_quota.json 同目錄）下 autosdd_pace*.json 零變動（前 3／後 3 份；目錄 /Users/wuweihong）；隔離根已建立並清除。 |
| AutoClaude 全套 | `cd AutoClaude && python -m pytest tests/ -q` | rc=0；開發 venv 通過 5159 支、skip 156 支（39.40 秒；**不是入庫基線**，基線唯一出處＝ONBOARDING §7） |
| AutoClaude 本機 CI 閘門 | `bash AutoClaude/tools/local_ci_gate.sh` | rc=0；總結七關（editable sentinel／LOC budget／CLAUDE.md <=400／CLAUDE.md line<=800／snapshot --check／import-linter／pytest）皆 PASS；「✅ 全部通過 — 可安全 push。」 |
| import-linter | `cd AutoClaude && PYTHONUTF8=1 lint-imports` | rc=0；「Contracts: 9 kept, 0 broken.」 |
| ruff | `ruff check tools/ .claude/hooks/` | rc=0；「All checks passed!」 |
| LOC 閘門 | `python AutoClaude/tools/check_loc_budget.py --json` | rc=0；四類 violations 皆空、`total_violation` 為 false；total=17857 cap=20438；planner assertion 750／750（headroom 0） |
| 缺陷帳本 | `python tools/check_defect_log_crossref.py`；`--unresolved-count` | rc=0；「帳本 225 筆有效狀態紀錄」「具名治理文件 166 份皆已登記」「當前輪 R212」；「未結列數＝0／全部 225 列｜warn=86 fail=98」 |
| 帳本保全 | `python tools/archive_defect_log.py --check` | rc=0；「✅ 帳本保全稽核通過（70 檔／1634 個 ID…」 |
| 交接載體 | `python tools/check_handoff_carriers.py` | rc=0；「[census] 當前輪＝R212…」「前瞻延後行 0 筆」「✅ 每一筆前瞻延後宣稱都有帳本承接載體」 |
| 護欄棘輪 | `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`；`python -m unittest test_adr_xplat001_c1c2_lock`（於 tools/tests） | 首行「# 淨額 116372→116372 (+0)」且「逐檔漂移 0 支」；鎖模組 `Ran 187 tests`／`OK` |
| hook 活性／NTFS／nightly 錨 | `python tools/check_hooks_liveness.py`；`python tools/check_ntfs_paths.py`；`python tools/refresh_nightly_anchor.py --check-head` | 皆 rc=0；「✅ NTFS 檔名檢查通過（27991 個 tracked 路徑，0 違規…」；「✅ nightly 錨判準通過（HEAD）…」 |
| `.env.example` 生成物 | `python tools/lib/quota_policy.py --print-env-example` 與 `.env.example` 逐字 `diff` | 兩步 rc=0、無差異 |
| whitespace | `git diff --check` | rc=0 |
| ONBOARDING 表① | `python tools/sync_onboarding_baselines.py --check` | rc=0；「✅ [loc-baseline-live:] {'total': 17857, 'cap': 20438, 'violations': 0}」「✅ [rootunit-baseline-live:] {'tests': 5326}」 |
| ONBOARDING 表② | `python tools/lib/clean_venv_carrier.py`；`python tools/sync_onboarding_baselines.py --check-snapshot` | 載具 rc=0（乾淨 venv 必刪完成）；`--check-snapshot` rc=0：「✅ §7 表② 指紋相符 macOS 欄（v001=8ffe3c3dabbd, v030=6d46814f9084, scripts=ec35ee2838d0, autoclaude=35e0a0326ae2）」 |

### 四-2 雲端對帳（commit push 後現查 `gh run list --commit <完整 sha>`；run id 與 conclusion 填入下表）

| workflow | run id | conclusion | gating job（`gh run view <id> --json jobs`） | nightly 類 job |
|---|---|---|---|---|
| root-infra-ci | | | | |
| AutoClaude CI | | | | |
| macos-compat-ci | | | | |
| windows-compat-ci | | | | |

- 本檔寫成時 commit 尚未 push，上表欄位為空；push 後由主控以上述指令現查填入（commit sha、每支 run 的 conclusion；job 層另查，workflow 綠不等於 job 綠）。shellcheck-ci／aisdlc-sdd-ci 依 paths 未觸發者，缺席＝未驗證；不以本機全綠代替雲端。

---

## 〈五〉理論洞清單（P4；只登記、不修、不立輪；再開條件＝症狀驅動，見五問 README S1～S6）

> 合併來源：SA／SD／QA／Architect 四面鏡＋QA 鏡 B（518）＋三份設計備忘錄的誠實劃界，已去重。每條一句**可觀測**的再開症狀（一次真實事件即依 `FiveQuestion_Audit_Protocol/severity.md`〈暴露度〉升 P2 並入帳）；暴露度欄＝量法與結果。

### 五-A 喚醒鏈（planner／relay／schedule backend／halt 標記）

| # | 洞 | 暴露度（量法與結果） | 再開症狀 |
|---|---|---|---|
| 1 | 睡著／闔蓋的 Mac 不會被喚醒（`pmset repeat` 需 sudo，本專案刻意不碰；已知邊界，非待修 bug） | 邊界，未量 | 一次 reset 時刻 Mac 處於睡眠，醒來後 `woken` 事件的 `at` 比 `due_at` 晚逾一個巡邏間隔（附 sid＋痕跡列＋`pmset -g log` 對應段） |
| 2 | reset 時刻解不出 ⇒ 拒絕武裝／`escalate`（PRD C10：不猜、不退回「假設 5 小時」） | 設計 | 一次真撞線的 limit 訊息被判 `escalate`（理由含「拒絕用猜的」），而事後可由同一訊息解出 reset 時刻（附 sid＋逐字稿 seq） |
| 3 | L0 端點憑證在 launchd 無互動環境能否自取未驗；拿不到＝`kind=unknown` ⇒ PATROL_HANDBACK（延後非遺失） | 真機 1 筆：10:22:03 `probed` 的 `endpoint@10:20:04` 早 tick 119 秒，分不出自取或沿用快取（〈三〉）；sid 5535e815 J012 的 `measured_at` 與 tick 同秒（可能自取，未確證） | 一次 launchd 觸發的 tick 其 `probed` 事件 `kind=unknown`，或 `text` 內 `endpoint@<時刻>` 早於 tick 逾快取 TTL 且 `source` 非 endpoint，致 `patrol_handback` 而同窗額度其實已恢復（附 sid＋痕跡列） |
| 4 | 到點後尾段（spawn→settle→哨兵重掛）在真 launchd 未實跑；含「job 行程內對另一 label `bootstrap`」是否被允許（C-A 唯一無法隔離證明的格子）；二層結論見〈二〉-0 | 隔離重現＋`LaunchdBackend`＋假 launchctl 整合測試；真機零筆（修後） | 一次續航 job 走完尾段後痕跡出現 `arm_failed`／`relay_rearm_failed`（或 `sentinel_armed` 缺席），且 `launchctl list` 無 `AutoSDD_Sentinel_<sid>`（附 sid＋痕跡＋launchctl 輸出） |
| 5 | `--no-allow-resume` 一次性 job 觸發後（`quota_back_no_resume`）只拆自己、不掛回哨兵：`tools/session_resume_planner.py` 該分支只 `_schtasks_remove`；R113 施工圖 §3(d) 判準 1 只列 relay 次態；推論〔讀碼，未驗〕：relatch 的 `claim_once`（`RELATCH_INTERVAL_SECONDS`＝900）在 claim 當下即消耗節流窗，自動復原最早要等上次 claim＋900 秒 | 真機 1 筆（sid 46b55125，10:22:03→10:23:04，由主控手動 `--arm-sentinel`，間隔 61 秒；驗收探針屬構造性）；planner 750／750，修它要先搬行 | 一次 `quota_back_no_resume` 之後、主 session 下一次工具呼叫之前，逐字稿出現 limit 事件而無人叫醒（附 sid＋seq；痕跡無 `sentinel_armed`） |
| 6 | INV5 讓位期間（一次性排程整段等待）哨兵不巡邏；`reset_at` 若比真實可用時刻晚則靜默多等；閘與觸發器用同一把本機鐘，本機鐘與伺服器鐘的偏差只靠 `RESET_SKEW_SECONDS`＝120 秒吸收，超過即回到「到點但伺服器尚未翻頁 ⇒ 探測說未恢復 ⇒ 重掛」的既有路徑 | 設計取捨，無痕跡 | 一次續航 job 等待期間逐字稿出現 limit 事件，而 job 到點前痕跡零動作（附 sid＋seq） |
| 7 | 顯式 `--at`（`reset_at==""`）在 mac 結構化 `at=None` ⇒ plist 只有 interval、無 calendar；A-1 閘對它不適用（SA-1 §7-D） | 無真機痕跡 | 一次 mac 上 `--register-schtasks --at <時刻>` 後 15 分鐘內出現 `probed`／`resumed`（附 sid＋`woken` 列） |
| 8 | 多軸殘餘：reset 後另一軸仍在 halt 帶卻 <100% ⇒ L0 判 open ⇒ 多燒一個續跑窗（續跑窗自己先 `--pace`、`settle_window` 判準②擋第二道） | 無真機痕跡 | 一次續跑窗起跑當下 `--pace` 仍顯示某軸 ≥ halt 帶（<100%）卻已 spawn（附 sid＋`probed`／`route_chosen` 列） |
| 9 | 手動 job（`kind=manual`）到點沒有「主 session 是否仍在動」檢查＝雙窗風險（`_resume_tick` 內第二個「該不該問」述詞的候選） | 真實時間線（反事實）：sid 5535e815 兌現時刻前最後一筆逐字稿距兌現 494.6 秒、兌現後首筆在 +104.1 秒〔SA 鏡自算〕 | 一次手動續航 job 到點 spawn 時，主 session 逐字稿在前一個巡邏間隔內仍有活動（附 sid＋seq） |
| 10 | Windows：E-A 讓標記存在期間 `arm_reset`（`-Once`）取代 15 分鐘巡邏 ⇒ 該段無閒置提醒／漂移自癒／新撞線偵測（mac 因 `StartInterval` 底盤不受影響） | Windows 未實機驗證 | 一次 Windows 自願 halt 標記存在期間，主控水位進 prepare 帶或另一軸撞線，而至兌現時刻前哨兵痕跡零列（附 sid＋痕跡） |
| 11 | Windows：`Unregister-ScheduledTask` 失敗（`STILL-PRESENT`、rc=1）時 INV5 仍把殘留 `-Once` 當擁有者讓位、對外 rc=0（R130 M-14）；7-C 的 Windows 對等（`disarm` 同步並驗證 REMOVED）只有註解與報告文字、沒有機械鎖 | 該機專屬，未驗 | 一次 Windows `disarm` 印 `STILL-PRESENT` 之後哨兵未掛上，或續航 job 收尾後哨兵讓位且零排程（附 sid＋痕跡） |
| 12 | E-A 的「兌現後有活動 ⇒ 標記視為過期」回 `None`，`sentinel_decided` 只剩 idle patrol 字樣，標記存在過這件事在痕跡上不可見；延後與 idle patrol 共用 `action=patrol`，只靠 `reason` 字面可辨；靜止守門的代價＝兌現時刻前後 900 秒內主控動過 ⇒ 叫醒最多延後一個巡邏間隔（為防雙窗付的價） | 構造性；靜止守門另有真時間線（兌現時刻時已閒置 8 分 15 秒、1 分 44 秒後又有新訊息）〔SA-4〕 | 一次需事後解釋「halt 標記存在、時刻已過、為何沒叫醒」，而 `sentinel_decided` 只有 idle patrol 字樣、以 `action` 欄 grep 重建不出（附 sid＋seq＋標記檔）；或兌現時刻已過、主控早已閒置，續跑卻延後逾一個巡邏間隔（附 sid＋連續 `sentinel_decided` 的「不叫醒（防雙窗）」reason） |
| 13 | 合法 INV5 讓位時 `relay_rearmed rc=0` 不帶排程器憑證（R-4.5.6-6 張力；讓位≠失敗是既有語意） | 設計 | 一次 `relay_rearmed rc=0` 同窗有 `sentinel_single_owner_deferred`，而其後 `launchctl list` 無該 sid 任何 job（附 sid＋痕跡） |
| 14 | 7-B 修法殘餘：非 loud `alert` 仍會 GC `plan_dir()` 內 mtime ≥7 天的任務書，本窗任務書若本身 ≥7 天未被重寫也會被收（要等 ≥7 天且期間無人重寫，實際不可達）；且「非 loud 收尾的 `escalation.alert` 收超齡殘骸」這一行可被拿掉而無測試紅（QA 突變 MB1 存活） | 設計取捨，無痕跡 | 一次 relay 窗收尾後任務書消失且該窗 `relay_done`／`relay_stopped` 的 `gc_plans` 計入該檔；或 `~/.autosdd/plans/` 內 ≥7 天殘骸不減（附 sid＋痕跡） |
| 15 | 殭屍／鬼 job（plist 不在、launchd 仍載入、不在本行程集合；非哨兵前綴無 GC；延後 bootout 沒執行時＝痕跡 `defer_failed` 或父行程不退場，C-A 修後會與哨兵短暫並存）；`rearm` 可把哨兵同名 job 掛成未設閘的 `--resume-tick`（需付費探測，INV1 於無人模式禁止 ⇒ 生產不可達） | 無 | `launchctl list` 出現 `AutoSDD_SessionResume_*` label 而其 plist 檔已不在且無活痕跡；或哨兵同名 job 的 argv 含未設閘的 `--resume-tick`（附 `launchctl print` 輸出） |
| 16 | 三個「900」鏡像（`RELATCH_INTERVAL_SECONDS` 無 parity）；`ERROR_FLAGS` 完備性無鎖；`--print-env-example` 與 `--env-doctor` 不互斥；`_NEXT_STEP_HEADING` 與 `HANDBACK_MARKERS[3]` 現同字串但無綁定；取節邏輯兩份（`_section_text`／`_section`） | 無漂移、無症狀 | 真實痕跡中 relatch 間隔與巡邏間隔數值不同；或新增 doctor 旗標漏進 `ERROR_FLAGS` 卻 rc=0；或兩個標題常數字面分家（附輸出） |
| 17 | planner 750／750 零餘裕（`# noqa: E702` 3→5、`# noqa: E501` 100→102；早醒閘用同行多語句擠進去）。預先設計好的下沉路徑＝SA-1 §3.2 A-2（`relay_machine.wait_for_reset`）；本輪不做：只買 2 行、需新增鎖並重寫 T6、無獨立暴露證據（違反〈守衛面准入〉「量、不挖」） | 結構債；`check_loc_budget.py --json` planner `loc=750`、`headroom=0`〔收尾親跑〕 | 任一缺陷修復需要在 planner 加 ≥1 條斷言行（`check_loc_budget` 回 `over_by>0`），或需在 `_resume_tick` 內加第二個述詞，或 `_TICK_DISPOSALS` 需新增名字，或再出現一行 `;` 並列擠行——先做 A-2 再做該缺陷 |

### 五-B handback 標題規則

| # | 洞 | 暴露度（量法與結果） | 再開症狀 |
|---|---|---|---|
| 18 | `heading_hit` 行首規則的殘餘：形態 D（共用前綴的另一個標題，例「## 下一步指令集（舊）」在前、其節為空而真節有未完項）與形態 E（舊標題在前且有內容、真節已清空）仍誤判（D：有未完項卻 DONE；E：反向多判）；檔首若帶 UTF-8 BOM，第一行「## 做了什麼」不再命中（`lstrip()` 不剝 U+FEFF）⇒ `handback_verdict` 判 `stale`（舊子字串規則不受影響） | 本機真 handback 2／2 標題乾淨、零提及行、零近似標題；handback 由 `claude -p` 的 Write 工具寫、不帶 BOM | `relay_done`（DONE）事件對應的 handback 尾節仍有未完項；或一次 handback 因 BOM 被判 `stale`（附 sid＋`relay_next` 痕跡） |

### 五-C 額度參數檔分層（env.shared）

| # | 洞 | 暴露度（量法與結果） | 再開症狀 |
|---|---|---|---|
| 19 | doctor 約 208 行與 hook 載入鏈（`quota_gate` 頂層 import）同檔載入，hook 只需 `_read`＋`merged_file_env` 約 25 行 | py3.9 census（動態可達性）涵蓋；`python -X importtime` 該檔累計 281～293 微秒〔他包回報：Dev-C〕；`difflib`／`shutil` 已延後到 `_fix_one` 內 import | doctor 日後再長大時 hook 鏈載入可量測地退步（`python -X importtime` 該檔累計 ≥1 毫秒）或 py3.9 census 轉紅；屆時拆成獨立 doctor 模組 |
| 20 | doctor 盲區：`export` 前綴與引號寫法記成 `[foreign]` 不報；`91#x` 這類顯示值；行程 env 為「存在但空白」時 doctor 落到檔案層（表列 `98〔.env〕`），而 `policy_env()` 實為 `{**檔案, **os.environ}`（空字串蓋掉檔案值 ⇒ harness 吃出廠 95）、引擎則落到檔案層——HEAD 即有同型不對稱，本輪 doctor 的〔來源〕欄把它說成一致；另 doctor 只看自己這個 shell 的行程 env，看不到被注入 hook 行程的 `.claude/settings.json`／`settings.local.json` 的 `env` 區塊（`settings.json` 現況無 `AUTOSDD_*`〔SA-3 實測〕，`settings.local.json` 未讀） | 真實語料 0（repo settings 與當前 shell 皆無空白 `AUTOSDD_` 匯出）；QA 鏡實跑 `AUTOSDD_QUOTA_HALT_PCT=`：harness 95.0／doctor 98／引擎 98.0 | `env \| grep '^AUTOSDD_QUOTA_.*=$'` 非空，且 `--pace` 的門檻≠doctor 表（附畫面） |
| 21 | `env.shared` 信任模型：追蹤檔任何 push 擴散到所有機器與 CI；合法但寫錯意圖的值（例：停機線寫成 99）能過值域檢查 | 無 | 一次 `env.shared` 的合法值被誤改、經 pull 擴散，致某機在非預期水位 halt 或不 halt（附 commit＋sid） |
| 22 | 引擎執行期不對「根 `.env` 遮住 `env.shared`」出聲（唯一偵測＝人跑 doctor）；重複鍵語意分歧（harness 取最後一行、引擎取第一行）在本機 `.env` 只偵測不修（追蹤檔 `env.shared` 另有鎖） | 無 | 一次 `.env` 遮住共享值，`--pace`／`--check` 顯示的門檻與 `env.shared` 不同而 doctor 未被執行（附畫面）；或同檔重複鍵致兩側吃不同停機線（附 doctor 的 `[duplicate]` 輸出） |
| 23 | `AUTOSDD_MODEL_HELMSMAN=fable` 進共享檔，前提「兩台機器同一帳號」是主控代決、未驗；失敗為 loud（`resumed` rc≠0），出口是該機 `.env` 寫 `AUTOSDD_MODEL_HELMSMAN=<有權限的別名>  # override-ok: <WHY>`；另：空白值不遮蔽下層（A3 的代價），本機無法把共享鍵「清空」，只能改寫成別的明確值 | 掌舵者代決，未驗 | 任一機器的無人喚醒窗口 `claude -p --model fable` 啟動失敗（`resumed` rc≠0 且輸出含模型存取錯誤；附 sid＋launchd／schtasks log）；或某機要回到「不帶 --model」卻只能寫別的明確值 |
| 24 | 同一收錄判準（「改它可直接改變 cap／band」）下，`quota_policy_env.py`（出廠值與解析器；本輪起 `merged_file_env` 也依賴它）、`relay_machine.py`、`resume_route.py`、`model_roles.py`、`AutoClaude/.env`（引擎 3 鍵覆寫層）仍不在 `_GOV_EXACT`；既有狀態、非本輪造成；D-1 只收 `env.shared` 與 `quota_env_layers.py`；〈守衛面准入〉之下不擴 | 無暴露（無人窗口改這些檔的實錄 0 筆）；Architect／QA 鏡各自實測無人值守 Write `quota_policy_env.py` rc=0 | 無人值守 session 的 Write／Edit 動到上述任一檔而 hook 零阻擋（附 sid＋seq） |
| 25 | `.env.example` 在 Windows 以 PowerShell 5.1 的 `>` 重生會寫成 UTF-16，`env_example_problems` 逐字比對紅（loud）；ONBOARDING §2.2 的編碼句只談 `.env`／`env.shared`，沒有針對重生 `.env.example` 的警語 | 構造性 | Windows 重生 `.env.example` 後生成物比對紅而讀者不知道原因（附畫面） |
| 26 | PRD R-4.5.7-1 指路「現查 `quota_policy.py --print-env-example` 找閒置門檻」已過期（輸出 82 行、`idle` 與「閒置」命中 0 筆）；現行單一來源＝planner `SENTINEL_INTERVAL_SECONDS`，`HALT_QUIESCE_SECONDS` 與之 parity；PRD 範圍凍結不改字 | SA 鏡實測〔他包回報：SA 鏡〕 | 一次有人依 R-4.5.7-1 的指路現查閒置門檻而查無（附畫面） |

### 五-D Kernel ESCALATION 善後（DEF-200-518；QA 鏡 B 理論洞）

| # | 洞 | 暴露度（量法與結果） | 再開症狀 |
|---|---|---|---|
| 27 | Kernel 路徑 dump 內容不精確（`Playbook` 欄空白、重啟指令 `autoclaude ""` 不可照抄、最後 log 檔名與實際不符、「從 checkpoint 繼續」措辭不準）；已於 `AutoClaude/CLAUDE.md` 揭露；根治路徑＝SA-2 方案 B 或讓 PRE_RUN 帶 `playbook_path` | QA 鏡 B 探針實物：`**Playbook**: ` 空白、`## 繼續執行指令` 為 `autoclaude ""`、`## 最後執行 Log` 為 `playbook_T01_attempt0.log`（實際寫 `playbook_{label}.log`） | 有人照抄 dump 的 `autoclaude ""` 而失敗；或下游工具解析 `**Playbook**:` 欄讀到空值 |
| 28 | veto／使用者中斷／Brain 故障型升級仍無 dump、無通知（D-1 決策刻意；與舊路徑同語意）；KB `record_escalation` 在 Kernel 路徑仍不寫（D-4） | 設計 | 無人值守長跑因 SDD 越閘 veto 或「Minimax API 故障，安全停止」而停，只有 log marker 與 `--last-run-summary` 的 reason、沒有通知或 dump；或 `FailureKnowledgeBase` 在 Kernel 路徑跑多輪後仍無任何 escalation 記錄 |
| 29 | 演化提案只出聲、不落檔；有 `MINIMAX_API_KEY` 時多一次同步 Minimax 呼叫（`_call_with_retry` 逾時 30 秒×最多 3 次＋退避，最壞約 96 秒） | 讀碼，未打真端點 | 升級後 CLI 多停逾一個 `minimax.timeout_seconds`；或要求「提案可被人審核」卻只能翻 log |
| 30 | `dump_path` 在出廠相對 `checkpoint_dir` 下是相對路徑（`escalation_alert.log` 內 `dump=checkpoints/…`）；`--last-run-summary`／`last_run_summary.json` 不帶 dump 路徑 | 讀碼＋探針 | 從別的目錄讀 alert.log 的人找不到該 dump；或升級後使用者要先翻 checkpoints 目錄才找得到 dump |
| 31 | dump 失敗路徑（`dump_path==""`）無測試：通知退成一般 notify、不寫 `escalation_alert.log`；同一秒、同 step 的兩次升級會互蓋 dump 檔（檔名只到秒；既存設計，非本輪引入） | 讀碼 | `escalation_alert.log` 缺某次升級的行；或同一 step 同秒兩次升級後 `checkpoints/` 只剩一份 dump |

### 五-E 測試、環境與編碼

| # | 洞 | 暴露度（量法與結果） | 再開症狀 |
|---|---|---|---|
| 32 | 兩支 SA-04 容忍窗鎖（`test_wake_chain_halt_r278.py`）已併成一支表格鎖，但對**現行**判準下有 reset 的標記本就盲（無 reset 邊界由反轉鎖的對照守著）；`AutoClaude/tests/test_r86_pace_contract.py`、`test_r82_quota_axis_and_shipped_defaults.py` 仍寫「兩份 `.env`／根層當基底、AutoClaude 那份覆寫它」（概念上仍對，只是現在是四層鏈的上兩層；動它們會讓 `autoclaude` 指紋樹再變） | 無 | 兩鎖之一被改壞卻無測試紅；或讀者照註解以為 `env.shared` 不會被引擎讀（附 diff） |
| 33 | AutoClaude 全套 pytest 每跑一次就在 `$TMPDIR` 頂層留 `escalation_fallback_*.md`／`playbook_fallback_*.log`（既存行為，非本輪引入：收尾開場時現查累積 137 個 `escalation_fallback_*.md`、最早 2026-09-19） | 收尾現查：`$TMPDIR` 內該前綴檔數與 mtime 分佈〔收尾親跑〕 | `$TMPDIR` 內這兩個前綴的檔數持續成長，且根層全套的「真實 TEMP 圍籬」因它轉紅（附圍籬訊息） |
| 34 | 已修的兩種編碼形態（UTF-8 BOM ⇒ `[bom]`、rc=1；cp950 存檔 ⇒ 兩側同 `errors="replace"`、ASCII 鍵值存活）不含 **UTF-16**（PowerShell 5.1 的 `>`／`Out-File` 預設）存檔的 `.env`：被當 UTF-8 以替換字元讀、鍵名全毀 ⇒ 該檔所有鍵被靜默忽略，doctor 仍印「0 個問題 ⇒ rc=0」（只多一則 `[foreign] 另有 N 行非 AUTOSDD_ 鍵`）；HEAD 的單檔讀法同樣忽略它，非退步 | 構造實測 1 筆（收尾以 UTF-16 LE＋BOM 的 `.env` 在 scratch 根實跑：表中 `AUTOSDD_QUOTA_HALT_PCT` 仍為 98〔env.shared〕、結論 0 個問題；同批 cp950 案生效為 90〔.env〕、UTF-8 BOM 案 rc=1）〔收尾親跑〕；無真語料 | 一次本機 `.env` 以 UTF-16 存檔致其中的鍵未生效，而 doctor 印 0 個問題（附檔頭位元組與 doctor 輸出） |

---

## 〈六〉五問協定 S4／S5 處置與 PRD §16.2 T4 對照

### 六-1 五問協定（`docs/06_quality/FiveQuestion_Audit_Protocol/README.md`〈窗口規則與收斂判定〉）

- **S4 成立**：本輪出現 P≤2——DEF-200-516／521／522／523／524（守衛面，皆有真機痕跡）與 DEF-200-518（產品面）皆 P2。S4 的另一半「宣稱被擋而前面沒有真阻斷」：本輪無。
- **S5 成立**：守衛面有變動（planner、`quota_messages`、`sentinel_lifecycle`、`quota_gate`、`quota_policy`，及 D-1 的 hook `_GOV_EXACT`），且每一處附暴露證據或掌舵者原文（〈二〉-8）。
- **本輪做了什麼**：①P2 全數同輪 fixed（未結 2→0，〈四〉）；②每處守衛面新增逐項附暴露證據或掌舵者原文，沒有「無證據新增」（〈二〉-8）；③審查口徑「量、不挖」：五面鏡的構造性命中（SD 的 heading 形態探針、BOM／cp950／UTF-16 構造實測、QA 突變實驗）一律只登 P3／P4 或〈五〉、不計 P≤2、不另立缺陷列——本輪新立的 521～524 皆有真機痕跡或真實語料，不是構造所得（〈七〉）；④五問協定目錄零改動（不觸發 `PROTOCOL-CHANGED`、不重置窗口）。
- **本輪不做什麼**：不開五問再評輪——不跑評估機（Windows）的 `audit_session.py` 三項症狀閘指令、不寫輪帳本 `symptom_streak`、不重產 Q4′ 的 `session_gate_acceptance_*.json`。理由：S4／S5 只是「有資格再評」的條件（README 原文「才開一輪再評」），再評量的是評估機主控視窗的誤擋、裸宣稱與 Q2′ 逾期，與本輪缺陷（喚醒鏈與參數檔）沒有量值對應；本輪守衛面變動沒有碰任何五問判準函式。掌舵者若要正式再評，指令與基線取法逐字在 README。

### 六-2 PRD §16.2 T4 對照（範本〈🏁〉T4：觀察者義務＝新立 DEF／寫證據檔時對照 §16.2「再開症狀」欄，命中者在該 DEF 列「分流去向」標座標）

方法：把 §16.2 ⏸ 列的「再開症狀」整句抽出（`[n]`＝表內第 n 個 ⏸ 列），逐列對照 sid 5535e815／46b55125 兩份 planner 痕跡、`autosdd_resume_cost.jsonl`、`quota_burn.jsonl`、5 份 halt 標記，以及 518 的 C4 實跑。

| ⏸ 列 | 再開症狀（摘） | 本輪痕跡 | 判定 |
|---|---|---|---|
| [11] §4.5.4 AUTO | 週軸讀數已達 converge 帶仍選 SESSION_RESUME、喚醒成本推高週額度（附 sid＋`quota_burn.jsonl` 前後列） | 前半成立：sid 5535e815 J012 `weekly_all=96.0%`、J013 `route_chosen SESSION_RESUME`〔收尾親讀〕；後半無證據：`autosdd_resume_cost.jsonl` 該列 `pct_before`／`pct_after` 皆 null（DEF-200-508 v1 限制）、`quota_burn.jsonl` 在 23:02:08（weekly 93）與 02:04:00（weekly 0）之間無任何列〔SA 鏡〕 | 前半命中、後半無法證實 ⇒ 不構成 T4；DEF-200-516 列「分流去向」標座標 |
| [30] A5c 喚醒成本 | cost 列三個 usage 欄合計的實數＋同 sid `route_chosen=SESSION_RESUME`＋掌舵者認定不可接受的原話 | 前兩項成立：cost 列 2＋3215＋306190＝309,407 tokens（首個 assistant 回合，`measured=true`）、同 sid J013 為 SESSION_RESUME〔SA 鏡〕；第三項（掌舵者原話）無 | 2／3 ⇒ 不構成 T4；該窗是 516 的早醒 spawn，A-1 已使其不再發生 |
| [17] §8 列 9 卡死／NEEDS_HUMAN | 一次需人介入的卡死而桌面通知與 ESCALATION 皆未觸發 | 518 的 C4 實跑：`escalated=True` 後 `checkpoints/` 空、零 `ON_ESCALATION` emit（`AutoClaude/docs/03_testing/SddBridge_RealRun_Evidence_20261011.md` C4） | 前半成立 ⇒ 本輪由 DEF-200-518 修復；母體列不改（見下） |
| [21] §9 告警 | 一次需人介入事件無人被告警而擱置 | 同上（C4） | 同上 |
| [10]／[12]／[15]／[9]／[31] | 長睡被拒、單次醒來 >90 秒、reset 晚到連探、喚醒窗不能 commit 隔日才收尾 | 兩份痕跡無相符實例（5535e815 的 23:45:55 窗約 4 分 50 秒，子 session 自述「沒派工」） | 未發生 |
| [23] §12 治理檔禁寫 | 無人窗口改動 `resume_route.py`／`model_roles.py` 等 | 本輪對 `resume_route.py` 的改動來自互動主控派出的 Developer 子代理（非無人窗口，`AUTOSDD_UNATTENDED` 未設）〔他包回報〕 | 未發生；與 D-1 同一議題 |
| 其餘 21 列 | — | 無關 | 未發生 |

- PRD §16.5 末段要求再開時在命中列的結案格就地落款；依本輪收尾任務書，**母體 101 列不動、不改任何條文**（只在 §16.6 追加 env.shared 一列），[17]／[21] 的落款改記於本節與 DEF-200-518 列「分流去向」的座標。

### 六-3 對「完成實作 PRD v2.1」的誠實限定句（證據檔、commit 訊息、回覆皆以此為準）

PRD §4.5.2／§4.5.5／§4.5.6／§4.5.8／§4.5.10 在 mac 路徑上被真機暴露的 5 個缺陷已修（各有紅綠測試），入口時間閘已在真 launchd 驗過；PRD §16.3 的 ⏸31／📎8 本輪未動、仍由症狀驅動再開；「完成實作」依 §16.1 的定義＝101 列恰落四格，v2.1.17 已成立，本輪沒有新增 ✅。不對外宣稱 PRD 全面完成、喚醒鏈閉環，或自願 halt 之後無條件自動續跑（邊界逐條在〈五〉）；§16.1 對 ✅ 的定義是「機制在、有測試或鎖」而不是「真機走通」，§4.5.5／§4.5.6／§4.5.8 三條 ✅ 在 2026-10-10 的真機上實際斷在五個點，本輪修了這五點。

---

## 〈七〉四方審查結論（修復前的五面鏡；不抄全文，逐條 P3 的處置如下）

> 角色全程唯讀、零信任；突變實驗一律在 scratchpad 隔離副本（R211 SD1-13 教訓）。處置者縮寫：Fix-R／Fix-R2＝根層修復包、Fix-B＝AutoClaude 修復包（皆 Sonnet）、收尾＝本檔建立者。本節只記修復**前**的審查判決與處置；修復後的複審不在本檔寫成時點。

| 鏡 | 判決（首行逐字） | P3／P4 概況 |
|---|---|---|
| SA 鏡（需求／PRD 對齊） | `VERDICT: CONDITIONAL`（只有 P3／P4；三項 P3 附「升 P2 條件」） | 14 項（P3×12、P4×2；其中 22 條理論洞已併入〈五〉） |
| SD 鏡（系統設計） | `VERDICT: CONDITIONAL`（無 P≤2；有 P3／P4） | F1～F7 |
| QA 鏡（零信任，根層） | `VERDICT: CONDITIONAL`（無 P≤2；P3 六筆〔P3-3 審查期間已結〕、P4 若干） | 31 個突變中 26 殺死、4 存活（MA3／MA4／MB1／ME5，皆「錯誤分支無測試」）、1 個是修法試驗 |
| Architect 鏡（棘輪可行性與准入） | `VERDICT: CONDITIONAL`（只有 P3／P4，無 P≤2） | P3×9、P4×5；棘輪在副本實跑可行，不需要 DEF-200-208 型例外 |
| QA 鏡 B（DEF-200-518） | `VERDICT: CONDITIONAL`（無 P≤2；P3 四條、P4 若干） | 19 個突變；理論洞 10 條 |

| 鏡 | P3 一句 | 處置（處置者） |
|---|---|---|
| SA | 停機線搬進 `env.shared` 而保護面沒跟著搬（升 P2 條件：520 標 fixed 而 D-1 未落地） | 測試半 `PROTECTED` +2 已在位（Fix-R）；hook 半由掌舵者親手套用；本檔〈二〉-6 與帳本 520 列以兩半同 commit 為前提 |
| SA | 「7-C 在 sid 46b55125 現場重演」誤歸因（升 P2 條件：寫進帳本或證據檔） | 帳本 523 與本檔只引 sid 5535e815；46b55125 只當 A-1 的真機實證（〈二〉-4、〈三〉）；`quota_back_no_resume` 尾段不掛哨兵另登〈五〉#5（收尾） |
| SA | 516 列現象欄「零進度一次即解除」已被痕跡證偽（事件是 `relay_done`＝7-A 誤判 DONE） | 帳本 516 列改寫（收尾） |
| SA | §16.2 座標缺（4 列 ⏸ 的再開症狀前半成立） | 帳本 516／518 列「分流去向」標座標；〈六〉-2（收尾） |
| SA | PRD §16.6 應追加 env.shared 一列（(i) 新需求自帶結案格） | 已追加（收尾） |
| SA | `sentinel_decide` docstring 仍寫被證偽前提；兩份 docs 同前提 | planner 兩行 docstring 換兩行（LOC 不變）、`CrossPlatform_DEF200278_Halt_Handoff_Evidence.md` 兩處追加、`WakeChain_IronLaws_Verification.md` 規則 5〈現況〉追加 INV5 一句（Fix-R；註：該節本無 halt 前提，補的是 SA-4 清單指定的 INV5 句） |
| SA | 使用者可見字串仍說「.env 有設錯」「一律改 .env」 | 三處改為「env.shared（跨機）或本機 .env」（Fix-R；`quota_gate.py` 一處拆三實體行，assertion 491→492） |
| SA | `AutoClaude/.env.example` 複寫「env.shared 目前 98」；三份使用者指南的 `cp` 流程自帶遮蔽 | 改「現值見 repo 根 env.shared」；三份指南補 `--env-doctor --fix` 一句，指令依 cwd 寫成 `../tools/lib/quota_policy.py`（Fix-R） |
| SA | Windows 程序沒有追蹤載體、缺 pull 失敗分支、`<WIN_REPO_ROOT>` 佔位 | 〈八〉（收尾） |
| SA | S4／S5 同時成立而計畫未寫處置 | 〈六〉-1（收尾） |
| SA | 「完成實作 PRD」過度宣稱風險（升 P2 條件：對外寫完成） | 〈六〉-3 限定句（收尾） |
| SA | 516／523 狀態欄與證據檔要逐字寫「到點後尾段未真機實跑」 | 〈三〉、〈二〉-4、帳本狀態欄（收尾） |
| SA（P4） | `.env` 以 UTF-8 BOM 存檔時首行鍵被靜默忽略、doctor 仍印 0 個問題 | doctor 加 `[bom]` 旗標（rc=1）（Fix-R） |
| SD | F1 `heading_hit` 子字串規則會讓有未完項卻判 DONE（形態 D／G／I）；Dev-A「方向保守、不會誤判」一句不成立 | 該句不入庫；Fix-R2 收緊為行首規則（G／I 轉正）；D／E／BOM 殘餘登〈五〉#18 |
| SD | F2 `env.shared` 是跨機追蹤檔，有效性鎖用 dict 解析、重複鍵隱形（harness 取最後一行、引擎取第一行） | 新鎖：逐行抽鍵 `len==len(set)`、鍵 ⊆ `ENV_SPEC`、檔首無 BOM；doctor 對重複鍵本來就 rc=1，補鎖不補碼（Fix-R） |
| SD | F3 `HALT_RESET_SKEW_SECONDS` 註解宣稱有 parity 測試，全 repo 找不到 | 新增 parity 測試並讓註解指名該測試（Fix-R） |
| SD | F4／F5／F6 | 同上列（docstring／誤歸因／D-1 兩半） |
| SD（P4） | F7 harness 嚴格 UTF-8（壞編碼整層丟棄）與引擎 `errors="replace"` 不對稱（cp950 存檔：引擎吃 91、harness 吃 98） | harness `_read` 對齊 `errors="replace"`（引擎 HEAD 起即如此，`config.py` 零改動）；ONBOARDING §2.2 補「一律存 UTF-8（無 BOM）」；順帶防住 `--fix` 對非 UTF-8 檔的未接例外（Fix-R） |
| QA | P3-1 早醒分支重掛失敗路徑零測試（突變 MA3／MA4 存活） | 補 1 支（Fix-R2；兩突變各被殺）；兩支已失鑑別力的 SA-04 鎖併成表格鎖抵銷行數（斷言逐條保留） |
| QA | P3-2 `halt_verdict(兌現後, idle=None)` 零測試（突變 ME5 存活；逐字稿檔缺席時 `idle=None` 可達，失效形態＝哨兵 tick 拋 `TypeError`） | 表格補 1 格（Fix-R2；ME5 被殺） |
| QA | P3-3 planner docstring | 審查期間已結 |
| QA | P3-4／P3-5／P3-6 | 同 SA（誤歸因）／本檔〈九〉史料／D-1 |
| QA（P4） | `heading_hit` 反例；`_with_dotenv` 只替身 `.env`（真 `env.shared` 仍被讀）；過時註解；其餘 c／d／e／g／h／i／k | 反例進 7-A 測試、`_with_dotenv` 導 env.shared 空檔（差分實測舊 fixture 對「別的鍵非法」會紅）、兩處「兩份 .env」註解改現行說法（Fix-R2）；其餘登〈五〉 |
| Architect | P3-1 skip 樹檔數下限任務書沒列（runner 開跑前 `return 1`） | 照 runner 逐字指示重釘（收尾，〈二〉-10） |
| Architect | P3-2 棘輪餘裕薄；款(11) 連升第 2 輪、R213 起主軌必須 ≤ 0 | 重釘放在所有 tools/tests 編修之後做一次；理由欄寫明（收尾，〈二〉-10） |
| Architect | P3-3 證據檔缺〈史料〉節、准入表、理論洞 | 本檔〈九〉、〈二〉-8、〈五〉（收尾） |
| Architect | P3-6 帳本 516／518 兩列僅剩 18／21 位元組餘裕 | 發現情境與描述欄縮到 ≤700 位元組、細節搬本檔（收尾） |
| Architect | P3-7 MIN_TESTS 與 ONBOARDING 表① 落後 | 重釘＋`sync_onboarding_baselines.py --write`（收尾） |
| Architect | P3-8 planner 750／750 結構債 | 登〈五〉#17；本輪不做 A-2 |
| QA B | P3 `AutoClaude/.env.example:116` 與新行為矛盾；`CLAUDE.md:199` 缺「dump 已知不精確」與 Minimax 時間界；`is_stuck` 沒有鎖 | 皆改（Fix-B）；`CLAUDE.md` 仍 400 行；Minimax 時間界依讀碼寫「逾時 30 秒×最多 3 次＋退避，最壞約 96 秒」（任務書字面「上界 30 秒」會是假話，偏離已揭露） |
| QA B（P4） | `config.yaml:96` 措辭；善後單一 try 連坐；多步驟案例 | 各改／補（Fix-B）；其餘理論洞登〈五〉#27～#31 |

- 設計與實作的偏離（Rule 7，已逐條記在各包報告）：事件欄位用 `due_at` 而非備忘錄草稿的 `fire_at`（既有鎖釘 `fire_at` 恰 2 個站點）；7-B 採「非 loud alert 不遞 plan」而非「先寫再 GC」或「GC 後不再寫」（兩者都讓重掛的哨兵沒有任務書）；7-E 的三支既有測試期望值改動屬語意修正（〈二〉-5）。

---

## 〈八〉Windows 機待辦（事實驅動，無輪號義務；本輪 mac 開發，Windows 側零量測）

### 八-1 國小版三步（在 repo 資料夾內開 PowerShell；指令皆已過 `lint_powershell_command`，路徑由 `git rev-parse --show-toplevel` 現查、不寫死）

1. **同步**：

   ```powershell
   Push-Location (git rev-parse --show-toplevel); git pull --ff-only; "pull rc=$LASTEXITCODE"; Pop-Location
   ```

   要看到 `pull rc=0`。不是 0：先看〈八-2〉；不要 stash、不要 reset。
2. **檢查**（唯讀）：

   ```powershell
   Push-Location (git rev-parse --show-toplevel); & .\.venv\Scripts\python.exe tools/lib/quota_policy.py --env-doctor; "doctor rc=$LASTEXITCODE"; Pop-Location
   ```

   `doctor rc=0`＝什麼都不用做；`rc=1`＝它會逐行說哪裡多餘、遮住共享設定、壞值或重複。出現 `[unknown]`／`[bad-value]`／`[duplicate]`／`[bom]`／`[unreadable]`／`[missing-shared]` 時停手回報（`--fix` 不處理它們）。表中出現 `〔process-env〕`＝這個 shell 或 Windows 使用者層環境變數有 `AUTOSDD_*`，它贏過所有檔案層，先弄清楚是誰設的。
3. **有問題才修**（只在步驟 2 的旗標都屬 `redundant`／`shadows-shared`／`engine≠harness`／`dead` 時）：

   ```powershell
   Push-Location (git rev-parse --show-toplevel); & .\.venv\Scripts\python.exe tools/lib/quota_policy.py --env-doctor --fix; "fix rc=$LASTEXITCODE"; Pop-Location
   ```

   然後再跑一次步驟 2，**必須**看到末行「結論：0 個問題 ⇒ rc=0」，且表中 `AUTOSDD_QUOTA_HALT_PCT` 後面是「98〔env.shared〕」（乾淨根目錄的實跑形狀：`AUTOSDD_QUOTA_HALT_PCT                       = 98〔env.shared〕`〔收尾親跑，Mac〕）；備份檔 `.env.bak.*` 驗收後手動刪。

### 八-2 `git pull --ff-only` 被髒檔擋下的分支（〔以下 Windows 未驗證〕）

訊息點名 `ONBOARDING.md` 時：本機 nightly 每晚把新錨寫回工作樹的 `ONBOARDING.md` 但不 commit，而本輪 commit 也改了該檔，ff-only 因此拒絕。

1. `git status --short`：確認髒的只有 ` M ONBOARDING.md`。
2. `python tools/refresh_nightly_anchor.py --check-head`：它只驗 HEAD；輸出末行是處置指令，照該行辦（通常＝把工作樹的錨併入一個本機 commit：`git add ONBOARDING.md`、`git commit`，再 `git pull --no-rebase`；錨欄位若衝突，取任一側皆可——錨是 GitHub 狀態的純函式，下次 nightly 會重寫）。
3. **不要**用 `git checkout -- ONBOARDING.md`、`git restore`、`git stash`：`block_destructive_git.py` 會擋（鐵律五）；`git stash create` 只做保全、不會清掉髒檔。
4. 仍卡住就停手回報，附 `git status --short` 全文。

### 八-3 其他步驟（細節版）

- 前置：`Test-Path (Join-Path (git rev-parse --show-toplevel) '.venv\Scripts\python.exe')` 必須 `True`；否則先跑 `tools\dev_start.ps1`（其 [2/7] 同步步驟會 ff-only pull；工作樹髒、分叉或 nightly 執行中不會自動 pull）。
- 僅當該帳號**沒有 fable 存取**才需要（掌舵者代決兩台同一帳號，預期用不到）：在本機 `.env` 加一行覆寫（`utf8NoBOM` 只有 PowerShell 7 有；5.1 的 `-Encoding UTF8` 會寫入 BOM，doctor 會標 `[bom]`；`Add-Content` 附加到檔尾，若 `.env` 末行沒有換行會黏在上一行，附加前先確認）：

  ```powershell
  Add-Content -LiteralPath (Join-Path (git rev-parse --show-toplevel) '.env') -Encoding utf8NoBOM -Value 'AUTOSDD_MODEL_HELMSMAN=sonnet  # override-ok: 本機無 fable 存取'
  ```

- 驗收後清理（備份含舊內容；`AutoClaude\.env.bak.*` 可能含機密；已被 `.gitignore` 與 pre-commit 機密閘涵蓋，仍請手動刪）：

  ```powershell
  Get-ChildItem -LiteralPath (git rev-parse --show-toplevel) -Filter '.env.bak.*'
  ```

### 八-4 Windows 真機未驗項（該機專屬待驗清單＝非再開事件：不開輪，只在該機做該機的事）

1. 〈八-1〉三步的指令與 `--env-doctor`／`--fix` 的輸出形狀只在 mac 以合成的 Windows 式舊複本實跑（26 個問題、`--fix` 後 `0 個問題 ⇒ rc=0`）〔他包回報：Dev-C〕；cp950 終端機顯示中文與 `≠` 可能亂碼（不影響 rc 與旗標英文名）；`utf8NoBOM` 僅 pwsh 7。
2. schtasks `-Once` 路徑：A-1 閘在 Windows 常態不觸發（單觸發器）；只有前提釘（`New-ScheduledTaskTrigger -Once -At` 在、`Repetition` 不在）靜態守著，真機 `Register-ScheduledTask` 路徑零量測。
3. E-A 在 Windows 的取捨（〈五〉#10）與 M-14（〈五〉#11）：零量測。
4. D-1：hook 的 `_fold_gov_path` 比對前 `normcase`，Windows 大小寫變體（`ENV.SHARED`）理應同樣命中新項（讀碼，未驗）。
5. ONBOARDING §7 表② Windows 欄與 Windows nightly 首筆樣本：沿用 `CrossPlatform_R210_Debt_Closure_Final_Evidence.md`〈八〉；本輪 `AutoClaude/tests` 指紋已變，Windows 欄回填指令 `python tools\lib\clean_venv_carrier.py`，驗收 `python tools\sync_onboarding_baselines.py --check-snapshot`。

---

## 〈九〉〈史料〉——搬出 `tools/tests` 的沿革原文（逐字；來源座標＝`file:line`＠HEAD 9032bebf）

> 這六段原本是 `tools/tests` 內的 docstring／註解（沿革與事故史料，不是「本檔守什麼」的規格敘述）。本輪為抵銷護欄層行數成長，把它們逐字搬到這裡；原處各留一句仍在約束今日行為的 WHY 與指標「史料搬至 `CrossPlatform_R212_WakeChain_EnvLayer_Evidence.md`〈史料〉」（共六處：`test_context_budget_guard.py` 四處、`test_mac_endurance_r83.py` 兩處）。逐段已核對：每段全文在 HEAD 對應檔案的該行起原樣存在〔收尾親跑 `git show HEAD:<檔>` 子字串比對〕。

### L1 R11X 空字串無人旗標（INV1）｜來源 `tools/tests/test_context_budget_guard.py:3844`＠HEAD 9032bebf（9 行）

```text
        """R11X（本輪對抗式稽核破洞）邊界值：`AUTOSDD_UNATTENDED=""`（鍵存在但值為空
        ——上游 wrapper script 誤寫／殘留 shell profile 都可能造成這個狀態）。修復前
        `probe_quota` 用 Python 真值測試 `if os.environ.get(...):`，空字串判定為假 ⇒
        誤判成『非無人模式』⇒ INV1 這道付費探測煞車失效（`main()` 分派 tick 前的
        `setdefault` 也救不了它：鍵已存在，`setdefault` 不覆寫）。讀取端改成鍵存在性
        判準（`UNATTENDED_ENV in os.environ`）後，這個邊界值必須仍然被視為無人模式——
        這是縱深防禦：即使某個呼叫路徑忘了先強制覆寫成 `"1"`，讀取端自己也不會被這個
        空字串誤判成攻擊者／殘留值想要的『非無人模式』。
        """
```

### L2 R11X 空字串無人旗標（INV4）｜來源 `tools/tests/test_context_budget_guard.py:4041`＠HEAD 9032bebf（4 行）

```text
        """同一破洞（R11X）打穿 INV4：修復前 `AUTOSDD_UNATTENDED=""` 這個邊界值會讓
        `no_progress_limit()` 的真值測試誤判成『非無人模式』，於是
        `AUTOSDD_RELAY_NO_PROGRESS_LIMIT=5` 真的放行連燒 5 窗而非夾在 1。讀取端改成
        鍵存在性判準後，這個邊界值必須仍然夾到 1。"""
```

### L3 console_qa 事故呼叫鏈（PlannerCheckIsConsoleFreeTest）｜來源 `tools/tests/test_context_budget_guard.py:6345`＠HEAD 9032bebf（6 行）

```text
    """行為鎖（console_qa 事故輪）：`pythonw.exe` 起 `tools/session_resume_planner.py
    --check`（唯讀；QA 實測會在 1 秒內觸發 OpenConsole.exe＋WindowsTerminal.exe 建立的
    那條路——`measure()` → `harness_feed.measure()` → `guard.window_evidence(session_id=
    None)` → `known_model_windows_path()` → `sdd_latest.resolve_latest_root_fast()` →
    importlib 動態載入 `sdd_version.py` → `tracked_version_dirs()` 內那個裸
    `subprocess.run(["git", ...])`）不得讓 Windows 新開一個可見 terminal。
```

### L4 console_qa 事故（內層腳本註解）｜來源 `tools/tests/test_context_budget_guard.py:6175`＠HEAD 9032bebf（9 行）

```text
# 🔴 本輪修（console_qa 事故）：`STARTUPINFO(STARTF_USESHOWWINDOW, wShowWindow=SW_HIDE)`
# 對本探針要量的東西（`GetConsoleWindow()` 有沒有 handle）零影響——那是 API 層的存在性，
# 不是視窗可見性；但它能讓「none」這個負對照（flags=0，本來就是刻意不帶 NO_WINDOW 才會
# 真的開視窗的那一格）不再把 Windows 升級交給 Windows Terminal 的
# OpenConsole.exe／WindowsTerminal.exe 承載。實測（建立事件監看器，隔離重跑）：不帶本
# STARTUPINFO 時 flags=0 每次都觸發 OpenConsole.exe+WindowsTerminal.exe 建立事件；帶了
# 之後三次隔離重跑 0/3 次觸發（其中一次仍會生出一個會自行收尾的 conhost.exe，非本輪
# 判準射程——task 5 只守 OpenConsole.exe／WindowsTerminal.exe）。全案例統一套用：「shipped」
# 這類已帶 CREATE_NO_WINDOW 的案例本來就沒有視窗，套用零風險。
```

### L5 DEF-200-267 F2-② 實跡（SelfDisarmTest）｜來源 `tools/tests/test_mac_endurance_r83.py:1004`＠HEAD 9032bebf（7 行）

```text
        """DEF-200-267 F2-②（2026-09-05 18:12:09→18:12:10 實跡）：`_resume_tick` 的
        PATROL_HANDBACK 對哨兵自己 `disarm()`（延後純 bootout）再 `_arm_sentinel()`
        （回讀相符 ⇒ 冪等 no-op）⇒ 父退場 1s 後 bootout 拆掉剛認證 `state = running` 的
        job；bootout log 只有一行、無 bootstrap。載具層修法：**plist 存在即為「應該活著」
        的 SSOT**——自我 disarm 的延後腳本改成 `bootout; [ -f plist ] && bootstrap×3 + print`
        （`disarm` 已同步 unlink；之後有人 `arm()` 會重寫 plist ⇒ 父退場那一刻「plist 在」
        ＝有接班者）。同一支腳本改做 relaunch ⇒ **不會有兩支腳本競態**。"""
```

### L6 DEF-200-268 F5 實跡（CalendarMoment）｜來源 `tools/tests/test_mac_endurance_r83.py:1156`＠HEAD 9032bebf（6 行）

```text
        """DEF-200-268 F5（2026-09-05 17:57:03 實跡）：`arm_reset` 連續七個 tick 把 18:02
        排進 calendar（launchd 六次自報 descriptor），截止前最後一格 `_calendar_of` 因
        `(at-now) ≤ interval` 回 None ⇒ 「要求無、回讀有」判不符 ⇒ bootout+bootstrap 把
        18:02 拆掉、`StartInterval` 重計 ⇒ 18:12:04 才醒（死等 12 分 4 秒，檔頭「≤60 秒」
        在此格為假）。修法：live calendar 仍在未來且距今 ≤ interval ⇒ 視為相符、保留、
        不 relaunch；plist 重寫時也要把它帶著（重開機後仍是同一份）。"""
```

---

## 〈十〉開了→收了

| 開了 | 收了／現況 | 憑證 |
|---|---|---|
| launchd job `AutoSDD_SessionResume_46b55125-…`（真機驗收的一次性續航 job；註冊前先卸本 session 哨兵） | 10:22:04 自拆（bootout log「parent-gone waited=1s at 2026-10-11T02:22:04Z」「bootout rc=0」）；收尾 `launchctl list`（唯讀）現查零 `AutoSDD_SessionResume_*` | `launchctl list`（唯讀）＝`AutoSDD_Sentinel_46b55125-…`、`AutoSDD_Sentinel_5535e815-…`、`com.autoclaude.nightly`，`SessionResume` 命中 0〔收尾親跑〕 |
| 本 session 哨兵 `AutoSDD_Sentinel_46b55125-…`（驗收前暫卸） | 10:23:04 `--arm-sentinel` 掛回（痕跡第 26 行 `sentinel_armed`）；現查在位。別 session 的 `AutoSDD_Sentinel_5535e815-…` 全程未動 | 同上 |
| 任務書 `~/.autosdd/plans/autosdd_resume_plan_46b55125-….md` | 保留：現役哨兵每個 tick 都讀寫它，不是殘骸 | `ls` |
| `$TMPDIR` 頂層實驗與測試暫存：Dev-A 實驗寫的 `autosdd_resume_log_plan_plan-存在.jsonl`、`autosdd_resume_log_plan_plan-已被-GC.jsonl`、`autosdd_resume_log_plan.jsonl`（來源不明，先於 Dev-A 動工）、`exp_arm_nxzkv3ov`、`suite_tmp_zy0twodi`；AutoClaude 全套 pytest 留下的 `playbook_fallback_*.log` 與 `escalation_fallback_*.md` | **已收**（收尾以明列檔名清單刪除，不用 glob）：`autosdd_resume_log_plan_plan-存在.jsonl`、`autosdd_resume_log_plan_plan-已被-GC.jsonl`、`exp_arm_nxzkv3ov/`，以及收尾自己的 AutoClaude 全套／本機 CI 閘門／乾淨 venv 載具實跑產生的 `escalation_fallback_*.md` 3 個與 `playbook_fallback_*.log` 4 個。**未收（不是本輪開的、或每跑必再現的既存行為）**：`suite_tmp_zy0twodi/`（內含 `d23_sentinel_e2e_*` 的空目錄樹；收尾刪過一次，根層全套重跑後同名再現，是全套每跑必留的測試殘影，不是被中斷的殘骸）、`autosdd_resume_log_plan.jsonl`（約 1.3 MB，自 2026-09-19 起被測試持續累積的固定名 log，來源不明、先於本輪動工）、其餘 `escalation_fallback_*.md`（收尾開場時 137 個、自 2026-09-19 起累積，見〈五〉#33）；皆不影響任何鎖 | `find "$TMPDIR" -maxdepth 1` 現查 |
| 收尾單人窗口的乾淨 venv `autoclaude_cleanvenv_20261011T052645Z`（表② 回填載具） | 載具 `finally` 自刪；`find "$TMPDIR" -maxdepth 1 -name 'autoclaude_cleanvenv_*'` 現查 0 筆〔收尾親跑〕 | `find` |
| 收尾單人窗口的背景任務（全套與載具，每次皆背景執行） | 皆已結束；`ps` 現查無殘留 pytest／sync／runner 行程〔收尾親跑〕 | `ps` |
| `git add` 的新檔（`env.shared`、`tools/lib/quota_env_layers.py`、`tools/tests/test_quota_env_layers.py`、AutoClaude 5 支 518 測試、本證據檔） | 已 stage、未 commit | `git status --short` |
| `runner` 自寫的失敗明細 `tools/.last_failure_*.log`（gitignored，既有行為） | 收尾期間每次全套實跑各留 4 份（3 份來自 runner 自測的合成失敗、1 份是真失敗）；先前各輪留下的同類檔仍在；未刪 | `git check-ignore -v` |
| scratchpad 工作檔（`closer_*`） | 不入庫 | — |
