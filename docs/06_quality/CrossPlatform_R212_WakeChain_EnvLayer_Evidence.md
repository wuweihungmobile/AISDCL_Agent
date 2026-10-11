# CrossPlatform R212 額度喚醒鏈五缺陷（DEF-200-516 家族）與額度參數檔分層（DEF-200-520）證據檔

- **輪籤**：R212（2026-10-11，macOS 真機；主控 Fable 5.1 兼 Architect；SA 設計備忘錄 4 份、Developer 與修復包 7 包、審查鏡 5 面、收尾單人窗口，子代理皆 Sonnet）；**第三列（DEF-200-525／526）落款於 2026-10-12**（同輪第三列，日期跨過日界；段落見〈二-12〉〈二-13〉〈七-2〉）
- **輪型**：R 系列（守衛面／跨平台護欄層）。依範本〈🏁〉T2「走軌道① 還是 R 系列由根因所在面決定」：DEF-200-516 家族與 DEF-200-520 在守衛面 ⇒ 走本檔；DEF-200-518 在產品面 ⇒ 走軌道① T1 最小響應（直接修＋測試＋帳本，不產四件套），其修法與證據同寫在本檔〈二〉，便於同一個 commit 對帳。
- **起點**：HEAD＝9032bebf；`python tools/check_defect_log_crossref.py --unresolved-count` 開場實跑〔收尾親跑〕＝「未結列數＝2」（DEF-200-516、DEF-200-518）；外部阻塞軌 5、結構性長債軌 6。
- **體例**：不使用前瞻輪號的「延後／交給」句型；數字標〔收尾親跑〕＝本場收尾單人窗口自己跑的輸出，〔他包回報：包名〕＝只讀報告、沒重驗；不抄寫 pytest 通過數字的字面（以「通過 N 支」代稱）。第三列起另用〔Docs 包親跑〕（文件修復包〔Sonnet〕自己跑的輸出）與〔主控親跑〕（主控在真機自己跑的輸出）。痕跡座標中的 J 編號＝痕跡 jsonl 的行號（`$TMPDIR/autosdd_resume_log_autosdd_resume_plan_<sid>.jsonl`）。

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
- **修法**：追蹤檔 `env.shared`（16 行〔Docs 包親跑：`git show HEAD:env.shared` 轉 `wc -l` 印 16、rc=0；第一列落地時是 15 行〔`git show 035746ba:env.shared` 同法印 15〕，同輪第二列〈二-11〉在檔頭多加一行〕；`AUTOSDD_QUOTA_HALT_PCT=98`、`AUTOSDD_MODEL_HELMSMAN=fable`、`AUTOSDD_MODEL_SUBAGENT=sonnet`、`AUTOSDD_MODEL_DOWNGRADE=haiku`，每鍵上方一行 WHY）；載入鏈（高→低）：行程 env ＞ `AutoClaude/.env`（引擎 3 鍵）＞ 根 `.env` ＞ `env.shared` ＞ 出廠 `ENV_SPEC`；`tools/lib/quota_env_layers.py`（`merged_file_env`＝鏈的 SSOT；`diagnose`／`_fix_one`／`doctor_cli`）；`tools/lib/quota_gate.py::policy_env` 改讀 `merged_file_env`；引擎 `AutoClaude/autoclaude/utils/config.py::_ENV_FILES` 三元組＋`_quota_env` 命中判定（空白值不遮蔽下層，兩側同語意）；`tools/lib/quota_policy.py` `__main__` 加 `--env-doctor` 分支；`.env.example`（`--print-env-example` 生成物）檔頭；`ONBOARDING.md` §2.2 與 §5 一列；兩支 compat-ci workflow 的 `paths` 加 `env.shared`、`tools/lib/quota_env_layers.py`。審查後 Fix-R 補：harness `_read` 與引擎同為 `errors="replace"`（cp950 存檔不再整層丟棄）、doctor 加 `[bom]` 旗標（rc=1）、`env.shared` 重複鍵／BOM／未宣告鍵鎖、三份使用者指南在 `cp .env.example .env` 之後補一句（在 `AutoClaude/` 下執行 `python ../tools/lib/quota_policy.py --env-doctor --fix`）、使用者可見字串「.env 有設錯」改「env.shared（跨機）或本機 .env」。
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
- **同輪第二列（env.shared pull 後自動同步 `tools/git-hooks/post-merge`；掌舵者 T1「幫我設計自動同步機制」；DEF-200-520 同族；含 QA 複審補鎖）**：淨額 116372→116348（−24）；回歸鎖軌不申報，主軌隨之 430→406 ≤ 516（款(11) 連升仍為第 2 輪、R213 起主軌必須 ≤ 0 不變）。構成：`test_quota_env_layers.py` 328→449（+121：`TestPostMergeHook` 七支＝四支行為鎖＋三支靜態鎖，見〈二〉-11）、`test_windowsapps_guard_bash_parity.py` 1015→1016（+1，`_CALLER_FILES` 登記 post-merge）、本檔 `test_adr_xplat001_c1c2_lock.py` 8744→8598（−146：接鏈列 R104～R165 的旁註 156 行搬至本證據檔〈九〉L7／L8、留 1 行指標；新列 8 行＋接鏈列 1 行）；`_REPIN_LOG_FROZEN_PREFIX_LEN` 336→337、`_REPIN_LOG_HISTORY_SHA256` e62c2eaa57e5…→73b11f302893…、`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列（e62c2eaa57e5 → 73b11f302893，DEF-200-520）；`<!-- guard-total:R212 -->` 兩站同步改為 115633→116348（+715，主軌 406）〔Developer 包回報、收尾親跑 `--print-guard-lines`：`# 淨額 116348→116348 (+0)`／`# 逐檔漂移 0 支`、印出 sha 與檔內相同〕。
- **同輪第三列（DEF-200-525：`tools/lib/cpu_budget.py` 的中文 `--help` 在 cp1252 主控台崩潰＝windows-compat-ci run 38153121596；含第二棒複審後修復＝敲擊 helper 接線自證；第三棒＝DEF-200-526：`LaunchdBackend.arm()` 對正在跑的 job 不再同步 bootout）**：淨額 116348→116429（+81）；全額歸主軌（本列是 `[非淨減法輪]`，回歸鎖軌 309 已達軌上限、不再加報），主軌 R212 合併 +796−309＝487 ≤ 516（款(11) 連升仍為第 2 輪、R213 起主軌必須 ≤ 0 不變）。構成：`test_doc_loc_baseline_freshness_r60.py` 7085→7099（+14：模組層 `_LEGACY_STDIO_ENV`＋`TestR85…` 的 `_knock` 敲擊 helper 與有牙自證改寫；已扣搬走史料 −7＝`iron_law3_ratchet_problems` 踩坑經過 −2、`_check_ignore` 家族三處落地實測數字 −5，見〈九〉L11／L13）、本檔 `test_adr_xplat001_c1c2_lock.py` 8598→8579（−19：史料搬走 25 行至〈九〉L9／L10／L12＝接鏈列 R166～R173 旁註 16 行、到期義務兌現沿革 R184～R212 的 7 行換 1 行指標、檔頭 SA 劃界記錄 4 行換 1 行指標；新列 5 行＋接鏈列 1 行）、`test_mac_endurance_r83.py` 2305→2387（+82：新類 `ArmNeverBootsOutAJobThatIsRunningTest` 五支＋`_print_output` 的 `pid` 參數）、`test_quota_env_layers.py` 449→453（+4：`TestPostMergeHook` 兩支既有測試補斷言——skip 分支出聲＋rc＝0〔同時釘住 `TAG` 在 `set -u` 之後定義〕、修復總結行「刪除 2 行」〔替身 `--fix` 多印兩行 `-X=`／`-Y=`〕；最終零信任複審鏡 P3-7，隔離副本四個突變皆咬住）、`test_cpu_budget.py` 428→428（只拿掉一處 stale 的 `child-encoding-ok:` 行尾標記；`AISDLC_SDD/scripts/tests/test_conftest_xdist_cpu_budget.py` 同拿一處——該檔在 scripts 指紋樹內，指紋 ec35ee2838d0→04108ae4b139，表② 待回填）；`_REPIN_LOG_FROZEN_PREFIX_LEN` 337→338、`_REPIN_LOG_HISTORY_SHA256` 73b11f302893…→cff55af4647d…、`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列（73b11f302893 → cff55af4647d，DEF-200-525）；最終零信任複審鏡 P3-6／P3-7 後第三列原地重釘（不新增列）：理由字串起點「主軌 401→483」訂正為 406（HEAD 兩列後＝739−24−309），並隨 +4 改為 406→487；`<!-- guard-total:R212 -->` 兩站同步改為 115633→116429（+796，主軌 487）〔Developer 包回報；收尾包重釘後 `--print-guard-lines`：`# 淨額 116429→116429 (+0)`／`# 逐檔漂移 0 支`、印出 sha 與檔內相同〕。
- 其他數字釘：skip 樹檔數下限 `tools/tests` 71→72、`AutoClaude/tests` 226→230（照 `run_root_unittests.py` 前置掃描逐字指示）；`MIN_TESTS` 5273→5326（discovery 實測）；ONBOARDING §7 表① `loc-baseline-live` 17797→17857（`sync_onboarding_baselines.py --write`）。表② macOS 欄以乾淨 venv 載具（`python tools/lib/clean_venv_carrier.py`：建→裝→探針→跑→必刪）回填：乾淨 venv 通過 5059 支、skip 222 支（出廠環境值；開發 venv 值不可與它相減）；ci-gate 三軌 1475／1979／362；指紋 v001=8ffe3c3dabbd、v030=6d46814f9084、scripts=ec35ee2838d0、autoclaude=35e0a0326ae2；載具 rc=0、乾淨 venv 必刪完成。

### 二-11 同輪第二列：env.shared 自動同步（git `post-merge` hook；掌舵者原文「幫我設計自動同步機制！==> 下次在 Windows 執行時，幫我自動同步！」；DEF-200-520 同族，不另立缺陷列）

- **設計（SD／Developer 包，Sonnet）**：掛點＝git `post-merge`（mac 現查：`core.hooksPath` 指向本 clone 的 `tools/git-hooks/`（絕對路徑）；Windows 機未量，絕對路徑可能漂移（ONBOARDING §6：搬移後不報錯、直接失效），見〈八-1b〉；hook 檔隨 pull 帶進來即在該次生效；`git pull --ff-only`／dev_start [2/7] 的 ff-only pull／真合併皆觸發，**同一次 pull 才帶進來的 hook 也會在該次執行**〔Developer 包以 git 2.54 在暫存 repo 實測〕——前提是 `core.hooksPath` 已設好：全新 clone 第一次 dev_start 的 [2/7] pull 早於 [5/7] 設 hooksPath，那一次沒有 hook（〈五〉#49）；真的需要 rebase 的 `pull --rebase`／`git rebase`／「Already up to date」不觸發 ⇒ 手動跑 doctor）。行為＝委派 `python tools/lib/quota_policy.py --env-doctor`：rc=0 印一行；問題行**全是**可自動修的旗標（以 `diagnose().fixable` 為準＝`redundant`／`shadows-shared`／`engine≠harness`／`dead`）才跑 `--fix`（先備份 `.env.bak.<UTC>`）再體檢一次、三段輸出全印；含需人判斷的旗標（`unknown`／`bad-value`／`duplicate`／`unreadable`／`missing-shared`／`bom`）則一個檔不動只出聲；rc≠0 卻零旗標行（doctor 自己壞）不 `--fix`；`AUTOSDD_UNATTENDED` 鍵存在（無人值守）只體檢不修（與 `block_destructive_git.py` 紅線 10「`.env` 唯讀」同語意）；永遠 `exit 0`（merge 不受影響）；找不到 repo 根 `.venv` 直譯器略過並出聲；`AUTOCLAUDE_SKIP_HOOKS=1` 跳過；兩處 grep 前綴 `LC_ALL=C`（非 UTF-8 多位元組 locale 下 `≠` 的位元組會讓 `[^]]*` 走不過）；刻意不納入 `HOOK_FILENAMES`（名冊只管「安裝時必須存在」）。bash 3.2＋BSD 相容由 `test_bash32_compat.py` 掃；該測試當場抓到一個真缺陷：`$rc2、` 緊接全形字會被 bash 3.2 併進變數名、`set -u` 下 unbound 中止整支 hook（改 `${rc2}`；〈十一〉-2 的假 claude 也踩到同型）。
- **鎖**：`tools/tests/test_quota_env_layers.py::TestPostMergeHook` 七支——四支行為鎖（temp 目錄 `git init`＋假 `windowsapps_guard.sh`＋替身 python 記 argv：可修⇒三次呼叫、人類旗標⇒一次且不動檔、`AUTOCLAUDE_SKIP_HOOKS=1`⇒零呼叫、直譯器缺⇒rc=0 出聲；locale 一格 darwin 用 `zh_TW.Big5`；無人值守一格 `AUTOSDD_UNATTENDED=""` 驗「鍵存在」語意）＋三支靜態鎖（hook 兩份旗標清單對 `ERROR_FLAGS` 的分割、逐旗標分類對 `diagnose().fixable`、hook 索引 100755／shebang／無 CR／非註解 exit 皆 0；索引模式查詢走 `tools/lib/git_paths.py::ls_files`——第一版裸 `git ls-files` 被 `TestGitPathEnumerationIsQuotepathSafe` 抓到）；`test_windowsapps_guard_bash_parity.py` `_CALLER_FILES` 登記 post-merge。**絕不**對真 repo 根跑 `--fix`（沙盒子行程環境剝掉 `GIT_*`／`AUTOCLAUDE_SKIP_HOOKS`／`AUTOSDD_UNATTENDED`）。
- **QA 零信任鏡（Sonnet，唯讀，隔離複本突變）**：`VERDICT: CONDITIONAL`——零 P1；P2 兩條皆「鎖缺非碼錯」（旗標分類無行為鎖：M8／M9 互換類別測試仍綠；hook 存活無鎖：沙盒把它提交成 100644 再 pull ⇒ git 印 `hook was ignored because it's not set as executable`、`.env` 靜默未動）；P3＝`HOOK_FILENAMES` 未納（另案）、三個測試鬆口（M5 備份名 regex／M6 錨點／M15 乾淨路徑）、文件三處；P4＝非 UTF-8 locale（Big5／eucJP）grep 盲區、`AUTOSDD_UNATTENDED` 下仍會改 `.env`、前綴比對、doctor 檔缺席訊息、輸出噪音、`_fix_one` 非原子寫。QA 自然語料重放：`.env.example` 13 個歷史版本＋本機真實舊備份當舊複本 14/14 自動修復、機密行逐位元組保留、CRLF 複本修後仍全 CRLF、cp950 複本 `--fix` 解碼失敗不動檔。**處置**：P2 兩條＋P3 測試鬆口＋P4 locale／unattended 同輪修（Developer 包第二棒）；突變 18/18 殺（含 QA 指定 M8／M9／M11）；P3 `HOOK_FILENAMES` 與 P4 前綴比對／輸出噪音／非原子寫維持登記、不修（既有行為或另案）；構造性命中依〈守衛面准入〉計 0、不入帳。
- **Windows 覆蓋現況**：控制流已在 windows-latest（Git for Windows 的 bash、替身 python／替身 guard）由 `TestPostMergeHook` 七支實跑通過——**推論，未見逐測試通過列**：windows-compat-ci run 38150026658（#334，8807f3bb，conclusion=success）的 `tools/tests/` 步驟（步驟 7，15:09:13Z→15:20:00Z）success，該步 log 印「✅ unittest 數量下限釘選通過：發現 5333 個測試（下限 5326）」＝下限 5326＋`TestPostMergeHook` 七支，log 內無本模組名稱；run 38153121596（#335，a7b20b7e）同步驟的失敗清單 4 筆皆非本模組、log 內亦無本模組名稱，skip 普查 43 筆無一屬於本模組〔Docs 包親跑：兩個 run 的 `gh run view <id> --json jobs` 與 `--log`，唯讀；skip 普查 43 筆＝他包回報：SD 鏡〕。該兩個 run 內的 hook 是第二棒修改之前的版本。Windows Python 輸出帶 `\r` 的旗標行計數＝SD 鏡於 mac 以 `.venv/Scripts/python.exe` 形態的 CRLF 包裝器、路徑含空白與括號實跑（23 個可修旗標數對、`--fix` 後 `.env` 仍全 CRLF、機密行保留）〔他包回報：SD 鏡〕；`pick_repo_python` 解析 `.venv\Scripts\python.exe`＝pre-commit／pre-push 同一函式，每次 commit／push 都在跑（讀碼）；`AUTOSDD_UNATTENDED=""` 經 subprocess 傳給 Git Bash 保留與否＝同上七支涵蓋（同為推論）。**仍未驗（只能在掌舵者那台 Windows）**：`core.hooksPath` 是否指對、該機 `.venv\Scripts\python.exe` 實解、cp950 主控台顯示、PowerShell 5.1 寫出的 BOM／UTF-16 `.env`。驗收＝〈八-1〉步驟 2 的驗收一行（`doctor rc=0`），不看 pull 畫面。
- **同輪第三列的第二棒對 hook 本身的改動**（隨第三列一併進 commit；Windows 尚未驗）：`AUTOCLAUDE_SKIP_HOOKS=1` 分支現在會出聲（原為零輸出，與「hook 沒被叫到」同畫面；`TAG=` 因此前移到 `set -u` 之後）；修復總結行多帶「刪除 N 行（內容見上方 diff；還原＝把備份檔複製回原檔）」（還原法在 mac 以暫存 repo 實證：`cp .env.bak.* .env` 後與 `.env.example` `cmp` rc=0）；檔頭「新機器第一次 pull 即生效」訂正為「已設好 `core.hooksPath` 的機器第一次 pull 即生效（全新 clone 要等 dev_start 第⑤步設好 hooksPath，之後的 pull 才有）」。Windows 上這幾處的新字樣（`LC_ALL=C grep -c '^-[^-]'`、`${ndel:-0}`）未驗，只驗了 mac `/bin/bash` 3.2.57＋BSD grep 與 shellcheck〔他包回報：Developer 第二棒〕。

### 二-12 同輪第三列：DEF-200-525（windows-compat-ci #335／run 38153121596 紅燈；掌舵者回報；落款 2026-10-12）

- **缺陷**：`tools/lib/cpu_budget.py --help` 的中文 help 在 cp1252 stdout 下 `UnicodeEncodeError`（CI 逐字：`tools/lib/cpu_budget.py: UnicodeEncodeError: 'charmap' codec can't encode characters in position 41-43: character maps to <undefined>`）。e6f0be65 把 `cpu_budget.py --legs 1` 寫進根 CLAUDE.md 現查表，使它進入 `TestR85DocNamedLiveCheckEntriesActuallyRun` 的射程；該測試與三支下游平台中立鎖（`TestR67R3NoUnstatedPlatformAssumption{Linux,Darwin,Win32}.test_holds_under_simulated_platform`，是同一支 R85 測試的平台模擬包裝）同根因紅 4 項〔他包回報：QA／SA／Architect 鏡各自讀 `--log-failed`〕；mac 預設 UTF-8，看不見。run 38153121596＝push 觸發（#335、headSha a7b20b7e）；失敗步驟＝步驟 7，步驟 9～28 共 20 步被 skipped〔Docs 包親跑：`gh run view 38153121596 --json …`，唯讀〕。
- **cp950 事實（為何掌舵者的 zh-TW 真機看不到）**：HEAD 版 `cpu_budget.py --help` 在 `PYTHONIOENCODING=cp950` 下 rc=0（中文 help 在 Big5 內可編碼）；cp1252／ascii／latin-1 才 rc=1，utf-8 rc=0；修後版在這五種編碼下 `--help` 全部 rc=0。只有非 CJK 碼頁（GitHub runner＝cp1252）會爆。`PYTHONIOENCODING` 連 UTF-8 mode 也蓋過（`PYTHONUTF8=1 PYTHONIOENCODING=cp1252 python -c "print(chr(0x4E2D))"` rc=1 `UnicodeEncodeError`），所以在 mac 以它模擬非 UTF-8 主控台有效〔他包回報：Architect 鏡附錄 #4；QA 鏡 A 與 SD 鏡矩陣同向〕。
- **為何現查表加一行就只在 Windows 現形**：R85 的 `--help` 敲擊原本只在**主機預設編碼**下跑——Mac／Linux 預設 UTF-8，永遠看不到非 UTF-8 主控台；同一條敲擊 R85 早就存在，是 e6f0be65 把 cpu_budget 加進現查表才第一次踩到。現查表 11 組真參數在 `PYTHONIOENCODING=cp1252` 下親跑全部 `traceback=False`，沒有「`--help` 綠、真參數路徑爆」的入口；唯一 rc≠0 的是 `reset_window_distribution.py`（rc=1），與預設編碼環境逐位元組相同（內容＝「一個 episode 都沒有 ⇒ 這台機器沒有撞線史」的正常判決）。CI 觸發面不動：windows-compat-ci（182 條）與 macos-compat-ci（183 條）的 push `paths:` 都含 `CLAUDE.md`，正是為了讓這類 docs 變更被 Windows 驗到，收窄只會藏起缺陷；對 a7b20b7e 的完整 sha 現查回 3 個 run（windows failure／root-infra success／macos success），Windows job 在 11 分 47 秒內給出紅燈〔他包回報：Architect 鏡 F-1／F-2〕。
- **原有的鎖為何沒擋住（Architect 鏡 C 訂正）**：Developer 第一棒回報曾寫「此缺陷本來有專門的鎖（判準四），被兩處不實的豁免標記壓掉」——該敘事不成立：①檔內自編號：child 保護是**判準二**（`test_subprocess_encoding_hygiene.py` 的 child 目標 UTF-8 保護判準），判準四是已註冊 hook 腳本；②兩處 `child-encoding-ok:` 標記對其**實際呼叫形態為真**——HEAD 版 cpu_budget 在 cp1252 下 `--legs 1`／`--legs 2`／`--bogus`／無參數的 stdout＋stderr 全 ASCII 且無 Traceback，只有 `--help` 是中文、會爆（逐字：`--help rc=1 stdout+stderr ASCII-only=True traceback=True`），所以不是標記壓住了鎖；③真正的缺口：R85 的 `--help` 敲擊以迴圈變數組路徑（`[sys.executable, str(_REPO_ROOT / rel), "--help"]`），判準二的靜態路徑解析解不出來（HEAD 版判準二在 doc_loc 的納管站點只有一處，R85 的兩處敲擊行不在射程內）；判準三（`nonascii_console_lines`）只看 `print`／`sys.std*.write`，argparse 的 `description=`／`help=` 在其偵測面外（HEAD 版 cpu_budget：`is_entry_point=True`、`has_utf8_stdio_protection=False`、`nonascii_console_lines==[]`、`scan_entry_points` offenders==[]）；④兩處標記是**修好之後才 stale**（目標已具保護 ⇒ 標記壓不到違規 ⇒ 依 stale 規則必須移除），不是它們擋住了鎖。可寫的最強說法是「兩處行尾豁免因目標已具保護而 stale，依 stale 規則移除」。同型剩餘面：repo 現存 `child-encoding-ok:` 標記 7 個，宣稱「只印 ASCII」的僅 1 個（`tools/tests/test_check_hooks_liveness.py` 的合成目標，成立）〔他包回報：Architect 鏡 C、QA 鏡〕。
- **修法**：`tools/lib/cpu_budget.py` 的 `if __name__ == "__main__":` 內、`sys.exit(_main(...))` 前加 `from platform_utils import init_utf8_streams` 與 `init_utf8_streams()`（`tools/lib` 的多數派形態，取不到 SSOT 時靜默不動＝fail-open）。位置只在 `__main__`：行程內 import `cpu_budget` 的只有 `tools/lib/parallel_shard.py` 與 `tools/tests/test_cpu_budget.py`，其餘消費端（AutoClaude／AISDLC_SDD conftest、ci-gate、pre-push、nightly 腳本）全走 CLI subprocess；放模組層會在 import 期換掉 pytest／unittest 行程的 stdout（`_stdio_utf8.py` 檔頭明訂只應在 `__main__` 進入點生效）〔他包回報：Architect 鏡 A、QA 鏡〕。Developer 第一棒是 `sys.path.insert(0, tools/)`＋`import _stdio_utf8`（與 `quota_reconcile.py` 同形）；Architect 鏡 P3-2／SD 鏡 P4-1 指出 `tools/lib` 的 CLI 8 支走 `init_utf8_streams()`、只有 1 支走前者，且前者取不到 SSOT 即 `ModuleNotFoundError`（隔離複製：新版單檔 `new_isolated_rc=1`、HEAD 版 `old_isolated_rc=0` 印 `9`），第二棒改成現形態（註：兩種形態把 cpu_budget.py 單檔複製到沙箱都會 ModuleNotFoundError，複審鏡實測現形態 rc=1；現存消費端零複製，不構成缺陷）。被否決的替代案：把 argparse 字串改成 ASCII 英文（鎖不區分兩案，但下一個中文訊息即復發，且違反使用者可見字串用中文的慣例）、在 workflow 層設 `PYTHONUTF8=1`／`PYTHONIOENCODING=utf-8`（會把整個非 UTF-8 主控台類別從 CI 視野抹掉）〔他包回報：Architect 鏡 A〕。
- **順拿掉兩處 stale 標記**：`tools/tests/test_cpu_budget.py` 與 `AISDLC_SDD/scripts/tests/test_conftest_xdist_cpu_budget.py` 的 `# child-encoding-ok:` 行尾標記各一處。判準二在修法落地後報「標記 stale」逼出（QA 鏡於隔離切片把兩個標記還原成 HEAD 版、修法在：`TestChildEncodingHygiene` rc=1，兩處皆報 stale）；後者在 scripts 指紋樹內 ⇒ ONBOARDING §7 表② scripts 指紋 `ec35ee2838d0→04108ae4b139`，`sync_onboarding_baselines.py --check-snapshot` 目前 rc=1，待乾淨 venv 載具回填（commit 前最後一步）〔他包回報：Developer／Architect／QA 鏡各自獨立證實〕。
- **鎖**：`TestR85DocNamedLiveCheckEntriesActuallyRun` 對根 CLAUDE.md 指名的每支現查入口，`_knock(script, base=None)` 敲兩輪——現行環境一輪、`PYTHONIOENCODING=cp1252`（模組層 `_LEGACY_STDIO_ENV`）一輪，只判 Traceback、rc 不判；有牙格（`test_the_traceback_criterion_has_teeth`）＝合成一支只印 `中` 的腳本，以 `PYTHONIOENCODING=utf-8` 當基線（免得 Windows 預設 cp1252 讓兩輪都爆）交給**同一個** `_knock`，斷言恰在 ` [cp1252]` 那一輪被抓——`_knock` 的 env 接線因此有自證。第一棒版本只自證常數、沒有自證接線（Architect 鏡 P3-1 的突變：把迴圈裡的 `_LEGACY_STDIO_ENV` 換成 `{}`、仍用 HEAD 版未保護的 cpu_budget ⇒ `mutated_knock_vs_HEAD_cpu_budget_rc=0`、有牙測試同樣綠），第二棒補上。另一道靜態鎖：修後 cpu_budget 具保護，判準二對它生效；第二棒以判準本體（`scan_child_encoding`／`has_utf8_stdio_protection`）在迷你樹隔離再證：

  ```text
  [現行（有保護：platform_utils.init_utf8_streams）] has_utf8_stdio_protection=True offenders=0 stale=0 in_scope=1
  [突變（拿掉保護兩行）] has_utf8_stdio_protection=False offenders=1 stale=0 in_scope=1
     offender: tools/tests/test_cpu_budget.py:380: 起 Python child `tools/lib/cpu_budget.py`，但該檔無 UTF-8 stdio 保護…
  ```

  Architect 鏡對第一棒形態的同型突變（拿掉 `import _stdio_utf8`）亦得 `offenders=1`，`AISDLC_SDD/scripts/tests/test_conftest_xdist_cpu_budget.py` 站點同理〔他包回報：Architect 鏡〕。
- **突變實驗（隔離副本，真檔未動；逐字，省略每行的 `Ran … in …s` 段）**：第二棒形態（`_knock` 接線；M0 為未突變對照）〔他包回報：Developer 第二棒〕：

  ```text
  M0 對照（未突變）            rc=0 OK
  M1 Architect 突變（迴圈 env 換成 {}） rc=1 FAILED (failures=1) 只紅 test_the_traceback_criterion_has_teeth：`AssertionError: 0 != 1 : 只該在 cp1252 那一輪爆：[]`
  M2 subprocess.run 不傳 env    rc=1 FAILED (failures=1) 只紅 test_the_traceback_criterion_has_teeth
  M3 `_LEGACY_STDIO_ENV = {}`   rc=1 FAILED (failures=1) 只紅 test_the_traceback_criterion_has_teeth
  M4 第二輪標籤改名 ` [legacy]` rc=1 FAILED (failures=1) 只紅 test_the_traceback_criterion_has_teeth
  ```

  （第一棒版本在 M1 下有牙測試仍綠，是 Architect 抓到的洞。）QA 鏡的突變針對**第一棒形態**（隔離切片＝`git archive HEAD` 解開後套 Developer 的 diff，九檔與真樹逐位元相同）〔他包回報：QA 鏡〕：

  ```text
  基準（未突變）R85 類別：rc=0，OK
  M1（移除 sys.path.insert(...) 與 import _stdio_utf8 兩行）：rc=1；只一支入口被抓，標籤 ` [cp1252]`
     失敗標頭：AssertionError: Lists differ: ["tools/lib/cpu_budget.py [cp1252]: Unicod[99 chars]ed>"] != []
     FAILED (failures=1)（預設環境那一輪不報＝舊鎖在 mac 是盲的）
  M2（_LEGACY_STDIO_ENV 改 {"PYTHONIOENCODING": "utf-8"}）：rc=1，test_the_traceback_criterion_has_teeth 紅
     AssertionError: 'Traceback (most recent call last)' not found in '' : 模擬主控台沒讓非 ASCII 輸出爆 ⇒ cp1252 那一輪沒有鑑別力
     FAILED (failures=1)
  [構造] M3a：根 CLAUDE.md 切片加一行 python tools/lib/zz_fake_cjk.py --help、假入口中文 help 且無 _stdio_utf8
     ⇒ rc=1，tools/lib/zz_fake_cjk.py [cp1252]: UnicodeEncodeError…position 28-33（只被 cp1252 輪抓到）
  [構造] M3b：同一支加上 _stdio_utf8 ⇒ rc=0 OK（新鎖能泛化到未來新入口、且無假紅）
  ```
- **紅→綠（mac 以 cp1252 模擬）**：HEAD 版（`git show HEAD:tools/lib/cpu_budget.py` 複本）`PYTHONIOENCODING=cp1252 python <複本> --help` rc=1，末行 `UnicodeEncodeError: 'charmap' codec can't encode characters in position 39-41: character maps to <undefined>`；工作樹版 rc=0（印出中文 usage／description／options）、`--legs 1` rc=0 印 `9`。CI 位置 41-43 與本機 39-41 的差 2 是推論：Windows 文字模式寫入先把 `\n` 翻成 `\r\n`（argparse 描述前兩個換行）〔QA 鏡，未在 Windows 實測〕。Architect 鏡隔離實驗：`git archive HEAD` 切片＋工作樹版鎖＋HEAD 版 cpu_budget，在**預設環境**跑 R85 類 ⇒ `FAILED (failures=1)`，且**只有** `tools/lib/cpu_budget.py [cp1252]` 一筆（另 8 支入口兩輪皆綠）；換成工作樹版 cpu_budget ⇒ OK。QA 鏡 CI 同形重現：舊 cpu_budget.py＋新鎖，跑 R85＋三個 `TestR67R3NoUnstatedPlatformAssumption{Linux,Darwin,Win32}` ⇒ rc=1、恰四個 FAIL（R85 `test_no_named_entry_dies_before_it_can_do_anything`＋三個 `test_holds_under_simulated_platform`）、`FAILED (failures=4)`＝與 windows-compat-ci 那組四紅同形：舊鎖在 mac 看不見、新鎖在 mac 就看得見〔他包回報：Architect／QA 鏡〕。
- **四方審查判決（修復後的完整對照見〈七-2〉）**：

  | 鏡 | 判決（首行逐字） | 與本列相關的處置 |
  |---|---|---|
  | QA | `VERDICT: APPROVE` | 無 P1／P2；P3 三條（落款缺→本節；〈九〉導言過期→已改；帳本狀態欄缺 Windows CI 註記→已加「CI 實跑待對帳」） |
  | Architect | `VERDICT: APPROVE` | 零 P1／P2；P3 兩條（接線自證、多數派形態）第二棒已修；P4 五條登〈五〉 |
  | SA | `VERDICT: CONDITIONAL` | 5 條 P2 皆為轉述句或文件（無碼錯）；P2-4（本列落款缺）＝本節；P2-5（不可宣稱「已修好」）＝帳本加「CI 實跑待對帳」＋〈四-3〉 |
  | SD | `VERDICT: CONDITIONAL` | 1 條 P2（S14）⇒ DEF-200-526，見〈二-13〉 |
- **Windows CI 實跑**：【已對帳】push `2403f9fd` 後 windows-compat-ci #336（run 38178905961）`Windows smoke` job 非 skipped 步驟全 success（30/31，1 步 skipped），六支 workflow 全綠，逐 job 見〈四-3〉。以下為回填前原文——修法與鎖在工作樹、未 commit／push；#335 在步驟 7 失敗後，步驟 9～28 共 20 步被略過（含 ci-gate.ps1 雙軌、dispatcher hooks 真 commit、dev_start、install_git_hooks 往返），綠燈＝push 後 windows-compat-ci 整個 job 步驟 1～28 都 success。push 後以 `gh run list --commit <完整 sha>`（短 sha 會靜默回空）現查，回填於〈四-3〉；預期 R85 兩輪皆綠。
- **護欄層**：行數、棘輪與兩站點數字只引〈二-10〉第三列 bullet，本節不另抄。
- **准入與輪號**：DEF-200-525 在非守衛面（`tools/lib/cpu_budget.py` 與 `tools/tests` 鎖）：`git diff --name-only` 對根 CLAUDE.md〈守衛面准入〉清單的比對在終態樹（15 個修改檔，含第四、五棒與收尾補鎖）唯一命中 `tools/session_resume_planner.py`——第五棒只加 3 行註解（`git diff --numstat`＝`3	0`、零程式行、planner assertion 750 不變），不是新增守衛碼或鎖；其餘 14 檔無命中〔最終零信任複審鏡（14 檔時）與收尾包（終態 15 檔）各親跑：`grep` rc=0〕。記成同輪第三列而不是新的一輪：成因是 R212 視窗內的 commit（e6f0be65）造成的回歸，同輪修同輪結；缺陷在同一工作樹內立案並 fixed、未結維持 0；沒有未結列也沒有承接輪號，R 系列沒有開輪事件（數字見〈六-1〉末條）〔他包回報：Architect 鏡 E〕。

### 二-13 同輪第三列（續）：DEF-200-526（續跑視窗內 `--arm-sentinel` 同步 bootout 自己的哨兵 job）

- **來源**：SD 鏡 P2-1（讀碼＋合成逐字稿＋假 `_run` 模擬；構造性、無真機）。主張：每個有歷史的真實續跑窗，第一次 PostToolUse 就會從 job 內由 hook 派生 `--arm-sentinel`（續跑窗 SessionStart 清閂鎖後，以整份逐字稿評估 `should_arm`：`sentinel_lifecycle_arm.py:93,147,241`；hook 端 `context_budget_guard.py:794-808,829-840`）；經哨兵 `probe` 分支觸發的 mac 續跑窗跑在哨兵 job 內；`LaunchdBackend.arm()` 在 live descriptor 與請求不符時（例：`arm_reset` 留下、已過期的 calendar）走 bootout，把承載自己的 job 連根拔掉。〈十一-5〉S14 列的「未發生」只因第二列用 1 請求小 session、回合數沒達 `MIN_TURNS=24`。SD 鏡逐字證據〔他包回報：SD 鏡〕——可達性（真函式＋合成逐字稿 40 回合／7020 秒＋注入 spawn；真實 session 最小量測值 38 回合／853 秒）：

  ```text
  transcript evidence: (40, 7020.0) (turns, span_seconds)
  original session first PostToolUse -> armed
  resumed window SessionStart clear_arm_latch -> True
  resumed window FIRST PostToolUse           -> armed
  spawns total (detached --arm-sentinel launched from inside the resumed window): 2
  ```

  與真 `LaunchdBackend.arm()`＋假 `_run`／`Popen`（`XPC_SERVICE_NAME`＝哨兵 label）的模擬：

  ```text
  == A. live descriptor still carries the (now past) arm_reset calendar
  arm rc = 0 | launchctl calls: ['print']
  deferred script spawned = YES | starts with: p=16499; n=0; while kill -0 $p 2>/dev/nu | contains bootout: True
  -> wait target pid p = p=16499 (this process pid = 16499 )
  == B. control: live descriptor has no calendar
  deferred script spawned = no (idempotent no-op: scheduler untouched)
  ```

  SD 鏡的建議：先跑 B+（0 token、真 launchd）當暴露證據，再決定修法（`.claude/hooks/` 屬守衛面，依根 CLAUDE.md〈守衛面准入〉須先附真機輸出）。SD 鏡的模擬假設子孫繼承 `XPC_SERVICE_NAME`（走延後 bootout 分支）；下面 (a) 量到子孫拿到的是 `0`，真實落點是同步 bootout 分支——危害方向相同、機制不同。
- **真機量測 (a)：`XPC_SERVICE_NAME` 的繼承**（主控親跑，0 token；一次性 launchd job `AutoSDD_XpcProbe_175600`，約 2026-10-12 01:56 +0800，跑完即 bootout）：job 內以 `/bin/bash` 依序印自己與各層子孫看到的 `XPC_SERVICE_NAME`。輸出逐字（原始檔在 scratchpad，不入庫；前三行是觀測腳本的註冊訊息，`bash:` 起的七行是量測，其後一行 `ls` 查 venv python 的符號連結身分，最後兩行是清理）：

  ```text
  written /Users/wuweihong/Library/LaunchAgents/AutoSDD_XpcProbe_175600.plist
  bootstrap rc=0
  waited=1
  bash: XPC_SERVICE_NAME=AutoSDD_XpcProbe_175600 pid=21335 ppid=1
  env: XPC_FLAGS=0x0
  env: XPC_SERVICE_NAME=0
  sh child: XPC_SERVICE_NAME=0
  sys python3 child: 0
  venv python child: 0 /Users/wuweihong/Antigravity/AISDCL_Agent/.venv/bin/python
  venv python grandchild: 0
  lrwxr-xr-x@ 1 wuweihong  staff  10 Jul  9 21:45 /Users/wuweihong/Antigravity/AISDCL_Agent/.venv/bin/python -> python3.11
  === cleanup ===
  bootout rc=0
  ```

  讀法：只有 launchd 直接起的那個行程（`bash`，`ppid=1`）看得到自己的 label；連 `/usr/bin/env` 這種最淺的子行程都拿到 `0`，`sh`、系統 python3、venv python 與孫行程也是。⇒ `XPC_SERVICE_NAME == label` 只能認出 job **本體**，認不出任何子孫（推論含 hook 派生的 `--arm-sentinel`；本輪未量 Python 本體→claude→hook→planner 這條真鏈，見誠實劃界(1)）。venv 的 `python` 只是指向 `python3.11` 的符號連結（`ls` 那行），而連 `/usr/bin/env` 都是 `0`，所以這不是 python 啟動器造成的。
- **真機量測 (b)：B+ 修前紅**（主控親跑，0 token，真 launchd＋真 `LaunchdBackend.arm()`；拋棄式 label `AutoSDD_BplusProbe_20261011T175115Z`，2026-10-12 01:51:15 +0800；修法尚未套用）：殼 `job.sh`（job 本體）先寫一行「job start」，再起 `.venv/bin/python child_arm.py <label> <plan>` 當子行程呼叫 `LaunchdBackend().arm(plan, label, "", "--check", None)`；arm 回來後 `job.sh` 才寫「arm_done」、每 2 秒寫一次心跳（共 45 次）、最後寫「job end normally」；`AUTOSDD_TRACE_DIR` 指向 scratchpad（job 的 `environment` 帶它，`launchctl print` 逐字；真 `~/.autosdd/traces` 不受污染）。等 130 秒後觀測，逐字（`run1_observed.txt`；`<scratchpad>` 代表 scratchpad 絕對路徑前綴）：

  ```text
  waited=130s
  === job.log ===
  job start pid=20218 ppid=1 xpc=AutoSDD_BplusProbe_20261011T175115Z at 17:51:15
  child pid=20221 ppid=20218 XPC_SERVICE_NAME=0
  === bootout trace ===
  cat: <scratchpad>/bplus/traces/autosdd_sentinel_bootout_AutoSDD_BplusProbe_20261011T175115Z.log: No such file or directory
  === launchctl print (summary) ===
  print rc=113
  === ps for job.sh ===
  (no job.sh process)
  === launchd_stderr tail ===
  ```

  `print_after.txt` 逐字：`Bad request.`／`Could not find service "AutoSDD_BplusProbe_20261011T175115Z" in domain for user gui: 501`。unload 帳的那一列（`run1_unloads.jsonl`；`argv`／`home`／`tmpdir` 的路徑值以 `…` 略）：

  ```json
  {"ts": "2026-10-12T01:51:15+0800", "op": "bootout", "reason": "", "label": "AutoSDD_BplusProbe_20261011T175115Z", "caller": "child_arm.py:<module>:6", "argv": ["…/bplus/child_arm.py", "AutoSDD_BplusProbe_20261011T175115Z", "…/bplus/plan.md"], "pid": 20221, "ppid": 20218, "home": "…", "tmpdir": "…", "session_id": "", "xpc": "0"}
  ```

  讀法：子行程拿到 `XPC_SERVICE_NAME=0` ⇒ `arm()` 判它不是 job 本體 ⇒ 走**同步** `launchctl bootout`（unload 帳 `op=bootout`、`caller=child_arm.py:<module>:6`、`pid=20221`、`ppid=20218`）⇒ 承載自己的 job 被殺，連 `arm()` 的呼叫者（子行程）與 `job.sh` 一起消失：`job.log` 停在「child pid=…」那行、沒有 `arm rc`／`arm_done`／任何心跳，`launchctl print` rc=113（不存在），`ps` 查無 `job.sh`；沒有 `autosdd_sentinel_bootout_<label>.log`＝延後 bootout 路徑**沒有**被走。依 `arm()` 的順序（回讀之後每次先重寫 plist，再同步 bootout，最後才 bootstrap），plist 已被改寫、卻沒有被載回 launchd〔讀碼推得；修前那一輪未留 plist 位元組〕。⇒ 真機暴露證據成立：這不是理論洞。

  探針腳本（逐字；路徑以當時 scratchpad 為準）：`job.sh`（job 本體；`BPLUS_DIR`／`BPLUS_LABEL` 由 plist 的 `EnvironmentVariables` 帶入）與 `child_arm.py`（子行程）。

  ```bash
  #!/bin/bash
  LOG="$BPLUS_DIR/job.log"
  echo "job start pid=$$ ppid=$PPID xpc=${XPC_SERVICE_NAME:-} at $(date -u +%H:%M:%S)" >> "$LOG"
  /Users/wuweihong/Antigravity/AISDCL_Agent/.venv/bin/python "$BPLUS_DIR/child_arm.py" "$BPLUS_LABEL" "$BPLUS_DIR/plan.md" >> "$LOG" 2>&1
  echo "arm_done rc=$? at $(date -u +%H:%M:%S)" >> "$LOG"
  for i in $(seq 1 45); do echo "hb $i $(date -u +%H:%M:%S)" >> "$LOG"; sleep 2; done
  echo "job end normally at $(date -u +%H:%M:%S)" >> "$LOG"
  ```

  ```python
  import os, sys
  sys.path.insert(0, "/Users/wuweihong/Antigravity/AISDCL_Agent/tools/lib")
  import schedule_backend
  label, plan = sys.argv[1], sys.argv[2]
  print(f"child pid={os.getpid()} ppid={os.getppid()} XPC_SERVICE_NAME={os.environ.get('XPC_SERVICE_NAME')}", flush=True)
  rc, cred = schedule_backend.LaunchdBackend().arm(plan, label, "", "--check", None)
  print(f"arm rc={rc}", flush=True)
  print(cred, flush=True)
  ```
- **修法**（`tools/lib/schedule_backend.py`，`LaunchdBackend`，+26 行〔第三棒 +16，第四棒 +5，第五棒 +5；numstat 累計 28 增 2 減〕）：①`_readback` 在 depth-1 補一支 `elif text.startswith("pid = "): found["pid"] = _first_int(text)`——`launchctl print` 只在 job 在跑時才有該行；子區塊內的 `pid =` 不取，`pid-local endpoints = {` 這種誘餌行不會被 `startswith("pid = ")` 吃到；②`arm()` 緊接 `live = self._readback(task_name)` 之後加早退：`live is not None` 且 `live["pid"]` 不是 `None`、也不等於 `os.getpid()`，且 `XPC_SERVICE_NAME != task_name`（＝launchd 說該 job 在跑、而我不是 job 本體）⇒ 寫痕跡事件 `arm_skipped_inside_job`（欄位 `label`／`job_pid`／`pid`／`ppid`／`xpc`／`at`；落 `autosdd_sentinel_bootout_<label>.log`）、**不碰排程器、不改 plist**、回 `(0, <憑證> + "｜🔴 該 job 正在跑（pid=…）：本行程若是其子孫，同步 bootout會殺掉在跑的 tick 與續跑視窗（launchd 不給子孫 XPC_SERVICE_NAME）⇒ 不碰排程器、不改 plist，重掛由 job 本體尾段執行（settle→哨兵重掛）")`。憑證用語刻意說「若是其子孫」——判準不管譜系，呼叫者可能不是子孫，但同樣不被允許同步殺掉在跑的 job；痕跡多記 `ppid` 與 `xpc` 供事後判拓撲（`ppid=1`＝孤兒化、`ppid＝job_pid`＝直屬子行程）。第四棒（Docs 包讀 B+ 修後輸出發現，登〈五〉#40）：早退路徑的憑證改為自組短憑證——`launchd <domain>/<label>｜launchctl print rc=0｜state｜plist 路徑〔launchd 自報；本路徑未與請求比對〕｜🔴 該 job 正在跑…`，不再套 `_credential` 模板（其「與請求相符」「planner 本體在列」「最壞 N 秒」三句在本路徑都沒比對過；上方 (c) 逐字輸出是修正前的樣子）；鎖＝非本體那支加斷言「憑證不含『與請求相符』」，M1（還原成模板）／M2（塞回該字樣）皆紅，測試檔行數不變。第五棒（主控採納 Developer 第四棒第五節三個觀察）：①`credential_line()` 頁尾——憑證含「本路徑未與請求比對」時，把「上面三件證明的是『此刻存在、參數就是我要的那組、且已持久化』」換成「上面陳述的是『此刻存在』（launchd 自報）；是否已持久化、參數是否就是我要的那組，本路徑皆未比對」，其他路徑的頁尾逐字不動；②早退憑證末句由「重掛由 job 本體尾段執行（settle→哨兵重掛）」改為「不碰排程器、不改 plist；是否重掛交 job 本體尾段（本路徑不證明）」（本 bullet 上文引的是改前末句），對未來動作不做宣稱；③planner 註解（`tools/session_resume_planner.py:398-410` 那段）補三行，指明這條早退路徑是「回讀相符才發憑證」之外的又一個例外（另兩條是 `_deferred_credential` 出口）（只改註解，planner 斷言行數 750 不變）；鎖＝非本體那支補頁尾斷言（對該憑證呼叫 `credential_line` 後不含「參數就是我要的那組」），一般頁尾那支補一個必含片語，把「其他路徑的頁尾不動」釘成機械物；突變：頁尾條件拿掉 ⇒ 非本體那支紅，頁尾條件對所有路徑生效 ⇒ 一般頁尾那支紅，測試檔行數不變。
- **Developer 對主控「祖先鏈」設計的駁回**（第三棒偏離，Developer 回報要求主控確認）：主控派工原擬 `_pid_is_ancestor`（沿 ppid 鏈找 job pid）。Developer 以取樣駁回：Claude Code 生出的 hook 行程自成行程群組——取樣檔例 `43718 84650 43718 …Python … .claude/hook…`（欄位依序 pid、ppid、pgid；ppid＝`claude` 行程 84650、pgid＝自己），共 74 列取樣（另 1 列結束標記），其中 41 列 `pid==pgid`（hook 行程本身）、33 列 `pid≠pgid`（hook 的子行程，例：`43726 43718 43718`＝ppid 與 pgid 都是 hook 的 43718）；hook 裡的 `spawn_sentinel` 用 `Popen` 起 planner 後不等待，hook 一退出 planner 就被孤兒化到 launchd（`ppid=1`），所以真實鏈上 planner 的祖先鏈常常已斷、行程群組也是自己的 ⇒ 祖先鏈法在最需要它的真鏈上會「認不出我是子孫」而照殺（與當初 `XPC_SERVICE_NAME` 法同型失敗）。改用「launchd 說該 job 在跑、且該 pid 不是我、且我沒有拿到自己的 label」＝不管譜系的判準，鏈完整或斷掉時都成立；Developer 的立場：祖先鏈若仍要，只能當**額外**規則而非替代（不會改變真鏈結果）〔他包回報：Developer 第三棒第四節〕。工作樹現行形態＝不管譜系判準，並由下面的 B+ 修後真機驗證。
- **鎖**：`tools/tests/test_mac_endurance_r83.py::ArmNeverBootsOutAJobThatIsRunningTest` 五支——`test_the_readback_takes_pid_only_from_the_jobs_own_line`（只取 depth-1 自己那行；fixture 的 `pid-local endpoints = {` 誘餌行不被吃）、`test_a_caller_that_is_not_the_job_body_never_touches_the_scheduler`（非本體呼叫者、孤兒化 `ppid=1`、`XPC_SERVICE_NAME=0` ⇒ 完全不碰排程器、plist 位元組不變、憑證含「子孫」且不含「與請求相符」、有痕跡）、`test_the_job_body_itself_still_takes_the_deferred_reload_path`（對照組：live pid＝本行程 ⇒ 照舊延後重載）、`test_either_signal_alone_is_enough_to_recognise_the_job_body`（pid 是我但環境沒給、或環境給了 label 但 pid 對不上 ⇒ 都不得被當別人而略過）、`test_a_job_that_is_not_running_is_still_reloaded_by_an_outside_caller`（對照組：沒有 pid＝沒在跑 ⇒ 照舊 bootout＋bootstrap，本修法只擋「殺在跑的 job」）。突變（隔離副本，真檔未動；M1＝把早退守衛換成 `if False:`；M2＝`not in (None, os.getpid())` 改 `not in (None,)`；M3＝拿掉 `XPC_SERVICE_NAME != task_name` 條件；M4＝`_readback` 不取 pid；M5＝連沒在跑〔無 pid〕的 job 也跳過；逐字，省略每行的 `Ran … in …s` 段）〔他包回報：Developer 第三棒附錄 D〕：

  ```text
  M0_control rc=0 | OK |
  M1_guard_never_skips rc=1 | FAILED (failures=1) | FAIL: test_a_caller_that_is_not_the_job_body_never_touches_the_scheduler
  M2_pid_exclusion_dropped rc=1 | FAILED (failures=2) | FAIL: test_either_signal_alone_is_enough_to_recognise_the_job_body
  M3_xpc_exclusion_dropped rc=1 | FAILED (failures=1) | FAIL: test_either_signal_alone_is_enough_to_recognise_the_job_body
  M4_readback_drops_pid rc=1 | FAILED (failures=2) | FAIL: test_a_caller_that_is_not_the_job_body_never_touches_the_scheduler, FAIL: test_the_readback_takes_pid_only_from_the_jobs_own_line
  M5_idle_job_also_skipped rc=1 | FAILED (failures=2, errors=1) | ERROR: test_a_job_that_is_not_running_is_still_reloaded_by_an_outside_caller, FAIL: test_either_signal_alone_is_enough_to_recognise_the_job_body
  ```

  Developer 第三棒另報：最終批第一輪抓到 1 個紅（`test_platform_neutral_paths` 的 `TestNoPosixAbsPathLiteralInAsserts`：自己新增的測試把 `/p` 路徑佔位值放進 `assertIn(...)` 引數），已改成不含路徑字面值的斷言並整批重跑〔他包回報：Developer 第三棒第二節〕。
- **真機量測 (c)：B+ 修後綠（第三棒形態；下方憑證字樣是第四、五棒修正前的樣子）**（主控親跑，0 token，真 launchd；拋棄式 label `AutoSDD_BplusProbe_20261011T190135Z`，2026-10-12 03:01:35 +0800；工作樹含修法）：同一組殼與子行程。窗內觀測（`run2_during_observed.txt`；首行是觀測腳本的 zsh glob 無命中訊息，略；輸出中的縮排 tab 在本檔一律以四個空白代）：

  ```text
  plist written: /Users/wuweihong/Library/LaunchAgents/AutoSDD_BplusProbe_20261011T190135Z.plist
  bootstrap rc=0
  label=AutoSDD_BplusProbe_20261011T190135Z
  arm seen after 1s
  === launchctl print DURING (summary) ===
  print rc=0
      state = running
      pid = 55502
  ```

  `run2_job.log`（19:01 起的一段；其前兩行是修前殘留，略；`hb 2`～`hb 44` 略，`hb lines=45` 見下方 `run2_observed.txt`）：

  ```text
  job start pid=55502 ppid=1 xpc=AutoSDD_BplusProbe_20261011T190135Z at 19:01:35
  child pid=55507 ppid=55502 XPC_SERVICE_NAME=0
  arm rc=0
  launchd gui/501/AutoSDD_BplusProbe_20261011T190135Z｜launchctl print rc=0（不存在時是 113）｜run interval = None seconds〔launchd 回讀，與請求相符〕｜argv 回讀 2 項、planner 本體在列〔未逐項比對：verify 這一側拿不到當初的任務書路徑〕｜plist = /Users/wuweihong/Library/LaunchAgents/AutoSDD_BplusProbe_20261011T190135Z.plist〔launchd 自報，證明已持久化〕｜**無** calendar ⇒ 只有巡邏觸發，最壞 None 秒後才有人動作｜電源姿態＝各電源段 `sleep` 皆為 0（pmset 現查；**這台機器的現況**，不是本專案的保證）｜state = running｜🔴 該 job 正在跑（pid=55502）：本行程若是其子孫，同步 bootout會殺掉在跑的 tick 與續跑視窗（launchd 不給子孫 XPC_SERVICE_NAME）⇒ 不碰排程器、不改 plist，重掛由 job 本體尾段執行（settle→哨兵重掛）
  arm_done rc=0 at 19:01:36
  hb 1 19:01:36
  hb 45 19:03:09
  job end normally at 19:03:12
  ```

  痕跡 `autosdd_sentinel_bootout_<label>.log`（`run2_bootout_trace.log`，唯一一列，逐字）：

  ```json
  {"event": "arm_skipped_inside_job", "label": "AutoSDD_BplusProbe_20261011T190135Z", "job_pid": 55502, "pid": 55507, "ppid": 55502, "xpc": "0", "at": "2026-10-12T03:01:36+0800"}
  ```

  `run2_observed.txt` 摘錄（略去重複的 job.log 與 bootout trace 段，其餘逐字；`<scratchpad>` 同上）：

  ```text
  waited=79s
  hb lines=45
  === unloads.jsonl new lines (label) ===
  0
  0
  === plist still mine? ===
      0 => "/bin/bash"
      1 => "<scratchpad>/bplus/job.sh"
    "RunAtLoad" => true
  === launchctl print AFTER ===
  print rc=0
      state = not running
      last exit code = 0
  === cleanup ===
  bootout rc=0
  0
  ```

  判讀（逐項對上方逐字輸出）：①`arm rc=0`；②憑證帶「不碰排程器、不改 plist」；③痕跡 `arm_skipped_inside_job`：`job_pid=55502`＝窗內 `launchctl print` 的 `pid = 55502`、`pid=55507`／`ppid=55502`＝直屬子行程、`xpc="0"`；④job 活滿全程：45 次心跳加「job end normally」（修前 job 在子行程呼叫 arm 時即被殺，0 次心跳）；⑤unload 帳對本 label 零新列（`autosdd_sentinel_unloads.jsonl` 仍只有修前那一列；〔Docs 包親跑：檔仍 1 行、本 label 出現 0 次、mtime 01:51:15〕）；⑥plist 未被改寫（`ProgramArguments` 仍是 `/bin/bash`＋`job.sh`、`RunAtLoad => true`，沒有被換成 planner argv）；⑦job 自然結束後 `state = not running`、`last exit code = 0`；⑧清理 `bootout rc=0`（`unloads.jsonl new lines` 下的兩個 `0` 與 `cleanup` 末行的 `0` 是觀測腳本未加標籤的計數／rc 輸出，本包不對其語意作推斷，判讀以⑤的獨立現查為準）；收尾時 `~/Library/LaunchAgents/` 無本 label、`AutoSDD_XpcProbe_175600`、修前那顆 label 的 plist，`launchctl list` 無三者〔Docs 包親跑，唯讀〕。
- **真機量測 (d)：B+ 最終碼一輪**（主控親跑，0 token，真 launchd；拋棄式 label `AutoSDD_BplusProbe_20261011T202849Z`，2026-10-12 04:28:49 +0800；工作樹＝第五棒最終碼；`job.log` 內的時刻是 `date -u` 的 UTC）：同一組殼與子行程。`run3_job.log` 自 `job start pid=78091` 起的四行（含完整憑證行，逐字；其後的 `arm_done`、`hb 1`～`hb 44` 略）：

  ```text
  job start pid=78091 ppid=1 xpc=AutoSDD_BplusProbe_20261011T202849Z at 20:28:49
  child pid=78095 ppid=78091 XPC_SERVICE_NAME=0
  arm rc=0
  launchd gui/501/AutoSDD_BplusProbe_20261011T202849Z｜launchctl print rc=0｜state = running｜plist = /Users/wuweihong/Library/LaunchAgents/AutoSDD_BplusProbe_20261011T202849Z.plist〔launchd 自報；本路徑未與請求比對〕｜🔴 該 job 正在跑（pid=78091）：本行程若是其子孫，同步 bootout 會殺掉在跑的 tick 與續跑視窗（launchd 不給子孫 XPC_SERVICE_NAME）⇒ 不碰排程器、不改 plist；是否重掛交 job 本體尾段（本路徑不證明）
  ```

  痕跡 `autosdd_sentinel_bootout_<label>.log`（`run3_bootout_trace.log`，唯一一列，逐字）：

  ```json
  {"event": "arm_skipped_inside_job", "label": "AutoSDD_BplusProbe_20261011T202849Z", "job_pid": 78091, "pid": 78095, "ppid": 78091, "xpc": "0", "at": "2026-10-12T04:28:49+0800"}
  ```

  `run3_observed.txt` 末段（自 `hb 45` 起；略去上方已逐字貼出的 bootout trace 段，其餘逐字；輸出中的縮排 tab 在本檔一律以四個空白代）：

  ```text
  hb 45 20:30:23
  job end normally at 20:30:25
  hb lines=45
  === unloads for label ===
  0
  === launchctl print AFTER ===
  print rc=0
      state = not running
      last exit code = 0
  === cleanup ===
  bootout rc=0
  leftover=0
  ```

  判讀（只逐項對上方逐字輸出）：`arm rc=0`；憑證是第四、五棒之後的現行字樣（不含「與請求相符」「最壞 N 秒」，末句＝「是否重掛交 job 本體尾段（本路徑不證明）」，與 (c) 的第三棒形態不同）；痕跡 `job_pid=78091`＝`job start pid=78091`、`pid=78095`／`ppid=78091`＝直屬子行程、`xpc="0"`；job 活滿 45 次心跳並自然結束（`job end normally`）；窗後 `state = not running`、`last exit code = 0`；清理 `bootout rc=0`、`leftover=0`（`=== unloads for label ===` 下的 `0` 同 (c)，收尾包不對其語意作推斷）。

  時序：run1＝修前 2026-10-12 01:51、run2＝第三棒後 03:01、run3＝第五棒後 04:28（+0800）；三次皆主控親跑、0 token、拋棄式 label 已清。〔最終零信任複審鏡核對檔案 mtime：`schedule_backend.py` 04:18:01、`session_resume_planner.py` 04:19:10、測試 04:18:48、本證據檔 04:19:48，皆早於本次開跑 04:28:49；其後收尾包只動 `credential_line()` 早退版頁尾字串與 planner 註解一個詞，run3 的輸出（`child_arm.py` 直接印 `arm()` 回傳的憑證）不經過 `credential_line()`〕
- **行為代價**：job 在跑期間，任何不是本體的呼叫者要求的重新註冊都會被略過（憑證如實說「沒做」、不改 plist、也不執行 F5「保留未到期 calendar」的重寫）；若呼叫者其實不是子孫，這次重掛要等下一次觸發（PostToolUse 自動武裝／job 尾段重掛）。該情境的實際頻率未量測。
- **誠實劃界**：(1) B+ 是構造情境：探針 job 是 `/bin/bash job.sh`（不是真哨兵），子行程是 `child_arm.py`（直屬子行程、`ppid`＝job pid）；真實鏈（真 `claude -p` 視窗內 hook 派生 `--arm-sentinel`，planner 被孤兒化到 `ppid=1`）**未實跑**——孤兒化那一格靠 Developer 的行程樹取樣與 launchd 行為推得，判準本身不管譜系，故預期成立，但本輪沒有真機樣本；(2) Windows schtasks 對應面未量測；(3) `disarm()` 同型未處理，登〈五〉#39；(4) 略過路徑的憑證前半沿用 `_credential` 模板：上方修後輸出裡 `run interval = None seconds〔launchd 回讀，與請求相符〕` 這句在本路徑沒有被比對過（探針 job 本無 interval），登〈五〉#40（第四棒已修，見上方修法要點末句）；(5) job 本體的 `os.getpid()` 等於 launchd 報的 pid，僅靠讀碼與 `autosdd_sentinel_unloads.jsonl` 第 53 列（`--sentinel-tick` 行程 `ppid=1`、`xpc`＝該 job 自己的 label）推得；即使此等號不成立，XPC 訊號仍單獨保本體（M2／M3 與 `test_either_signal_alone_is_enough_to_recognise_the_job_body` 釘住）〔他包回報：Developer 第三棒第五節〕（最終零信任複審鏡補：上述「僅靠讀碼」已不全，另有三條直接證據：①B+ 的 bash 本體 `job start pid=55502`＝窗內 `launchctl print` 的 `pid = 55502`（run3 為 78091，痕跡的 `job_pid`＝`job start pid=78091`）；②`exec` 經 `.venv/Scripts/pythonw.exe` 符號連結鏈保留 pid（複審鏡實測 `shell pid=83330`／`os.getpid()= 83330`）；③真哨兵 `launchctl print` 的 `program = …/.venv/Scripts/pythonw.exe`＝直接 exec、無包裝層）；(6) hook 在無人續跑窗仍派生 `--arm-sentinel` 的組合不在 INV1～5 內，登〈五〉#38；(7) 第五棒的頁尾替換由憑證內的字面標記「本路徑未與請求比對」觸發，該標記在 `arm()` 與 `credential_line()` 各寫一份字面（未抽常數：`schedule_backend.py` 斷言行 397／400，抽常數要多一行），漂移由非本體那支的頁尾斷言咬住；第五棒比預期的「+2 斷言行以內」多 1 行（+3，394→397），最小可讀寫法需要這三行；(8) 〈十一〉三段真機 E2E 在第三～五棒之前跑，`arm()` 早退改動後未重跑整條到點後尾段，故「真機驗過」對最終碼只覆蓋 B+ 構造路徑（run2／run3）；影響推論：早退只影響「launchd 說該 job 在跑、且呼叫者不是本體」的呼叫，〈十一〉的同名原地重掛（本體呼叫，pid 或 XPC 放行）與 C-A（SessionResume 本體對另一個 Sentinel label bootstrap，當時沒有該 label 在跑的證據）都不屬此型（推論，未重跑）；再開症狀同〈五〉#38。
- **准入說明**：`schedule_backend.py` 不在根 CLAUDE.md〈守衛面准入〉列舉的守衛面；暴露證據仍照辦——B+ 修前真機紅（`arm()` 殺掉在跑的 job）是本缺陷的暴露證據（真後端、構造情境），不是理論洞。SD 鏡建議的另一種修法（hook 端在 `XPC_SERVICE_NAME` 以 `AutoSDD_` 開頭時略過；`.claude/hooks/context_budget_guard.py` 屬守衛面）**沒有採用**；守衛面清單內只有 `tools/session_resume_planner.py` 被動到——第五棒 3 行註解、零程式行（見上方修法要點③與〈二-12〉）。帳本列 DEF-200-526（P2，fixed）的狀態欄寫「構造 B+ 修後真機綠」；其「發現情境」欄依本 repo 慣例零輪號。

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

1. 「早醒不 spawn」：本次註冊帶 `--no-allow-resume`，即使沒有閘也不可能 spawn；證據只剩「沒有 `probed`」。修前反事實（10:12:27 若無閘會 `probed`→`quota_back_no_resume` 自拆、10:22 不會響）推得通，但痕跡裡沒有對照組。〔R212 第二列補證（〈十一〉①P1.3）：`allow_resume=true` 的手動 job 以手改 `reset_at`（構造性）早醒 kickstart ⇒ `woken→resume_tick_early remaining_seconds=281`、無 `probed`、假 claude 日誌不存在；缺的這半已有真 launchd 證據〕
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

### 四-1 本機閘門（收尾單人窗口親跑；rc 與尾行逐字）（第一列收尾時值；第三列後現值見〈四-3〉與〈六-1〉）

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
| 護欄棘輪 | `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`；`python -m unittest test_adr_xplat001_c1c2_lock`（於 tools/tests） | 首行「# 淨額 116372→116372 (+0)」（第一列當時值；第二、三列後現值見〈二-10〉）且「逐檔漂移 0 支」；鎖模組 `Ran 187 tests`／`OK` |
| hook 活性／NTFS／nightly 錨 | `python tools/check_hooks_liveness.py`；`python tools/check_ntfs_paths.py`；`python tools/refresh_nightly_anchor.py --check-head` | 皆 rc=0；「✅ NTFS 檔名檢查通過（27991 個 tracked 路徑，0 違規…」；「✅ nightly 錨判準通過（HEAD）…」 |
| `.env.example` 生成物 | `python tools/lib/quota_policy.py --print-env-example` 與 `.env.example` 逐字 `diff` | 兩步 rc=0、無差異 |
| whitespace | `git diff --check` | rc=0 |
| ONBOARDING 表① | `python tools/sync_onboarding_baselines.py --check` | rc=0；「✅ [loc-baseline-live:] {'total': 17857, 'cap': 20438, 'violations': 0}」「✅ [rootunit-baseline-live:] {'tests': 5326}」 |
| ONBOARDING 表② | `python tools/lib/clean_venv_carrier.py`；`python tools/sync_onboarding_baselines.py --check-snapshot` | 載具 rc=0（乾淨 venv 必刪完成）；`--check-snapshot` rc=0：「✅ §7 表② 指紋相符 macOS 欄（v001=8ffe3c3dabbd, v030=6d46814f9084, scripts=ec35ee2838d0, autoclaude=35e0a0326ae2）」 |

### 四-2 雲端對帳（commit push 後現查 `gh run list --commit <完整 sha>`；run id 與 conclusion 填入下表）

| workflow | run id | conclusion | gating job（`gh run view <id> --json jobs`） | nightly 類 job |
|---|---|---|---|---|
| root-infra-ci | 38150026499 | success | root infra guard：success | — |
| AutoClaude CI | 38150026544 | success | CLAUDE.md Budget + Snapshot Freshness／Tests + LOC Budget／Equivalence Snapshot／PG Contract Tests：皆 success | Mutation ×3／PG E2E／Perf Baseline：skipped（排程或 dispatch 專屬，push 不觸發） |
| macos-compat-ci | 38150026559 | success | macOS smoke：success | nightly full suite／失敗提醒：skipped（排程專屬） |
| windows-compat-ci | 38150026658 | success | Windows smoke：success | nightly full suite／失敗提醒：skipped（排程專屬） |

- 【2026-10-11 23:08 CST 回填】本列與第二列、useMacWin 精簡、D-1 守衛檔四個 commit（035746ba／8d1646f0／be3fcfc2／8807f3bb）由掌舵者在對話中明文授權後一次 push（`9032bebf..8807f3bb  main -> main`，pre-push 全套 `All checks passed!`）；上表以 `gh run list --commit 8807f3bbea01155c22101bdce70ad3d339f2ca4a` 與 `gh run view <id> --json jobs` 現查填入：五支觸發皆 success（另 shellcheck-ci 38150026565 success），job 層 gating 全 success、nightly 類 job 皆 skipped（排程專屬，push 不觸發＝未驗證、不是通過）；aisdlc-sdd-ci 依 paths 未觸發，缺席＝未驗證；不以本機全綠代替雲端。

### 四-3 第三列雲端對帳（push 後回填）

| workflow | run id | conclusion | gating job（`gh run view <id> --json jobs`） | nightly 類 job |
|---|---|---|---|---|
| root-infra-ci | 38178905958（#392） | success | `root infra guard (bash -n + pwsh parse/BOM + EOL(.sh) + EOL(.ps1) + NTFS + parity + py_compile + ...`＝success（步驟 25/26 success） | — |
| AutoClaude CI | 38178905954（#286） | success | `CLAUDE.md Budget + Snapshot Freshness`＝success（步驟 10/10 success）；`Tests + LOC Budget`＝success（步驟 10/10 success）；`PG Contract Tests`＝success（步驟 11/11 success）；`Equivalence Snapshot`＝success（步驟 8/8 success） | `PG E2E (pgvector recall + p95) - nightly`＝skipped；`Mutation Test - GoalSynthesisPlugin (dormant W1, workflow_dispatch only)`＝skipped；`Mutation Test - TokenGuardPlugin (active pilot) - 03:07 UTC`＝skipped；`Perf Baseline (CPU-bound scenarios) - nightly`＝skipped；`Mutation Test - OrchestrationCoordinator (dormant W2, workflow_dispatch only)`＝skipped |
| macos-compat-ci | 38178905970（#321） | success | `macOS smoke（實際執行關鍵腳本，非僅語法解析）`＝success（步驟 29/30 success） | `macOS nightly full suite（深度回歸，非阻斷）`＝skipped；`macOS nightly 失敗提醒（best-effort，不影響 nightly-full 本身的 continue-on-error）`＝skipped |
| windows-compat-ci | 38178905961（#336） | success | `Windows smoke（實際執行關鍵腳本，非僅語法解析）`＝success（步驟 30/31 success） | `Windows nightly 失敗提醒（best-effort，不影響 nightly-full 本身的 continue-on-error）`＝skipped；`Windows nightly full suite（深度回歸，非阻斷）`＝skipped |
| aisdlc-sdd-ci | 38178905965（#141） | success | `offline gate (pytest + arch-fitness)`＝success（步驟 9/9 success） | — |
| shellcheck-ci | 38178905929（#37） | success | `shellcheck (active shell scripts, two-way baseline ratchet)`＝success（步驟 6/6 success） | — |

- **回填（2026-10-12，收尾單人窗口親跑）**：commit `2403f9fd` push 後 `gh run list --commit 2403f9fdf8051618179090ee86d8e62f9f48a3f0` 回 6 個 run（上表），workflow 層全 success；`gh run view <id> --json jobs` 逐 job：gating job 全 success（windows-compat-ci 的 `Windows smoke` job 非 skipped 步驟全 success（30/31，1 步 skipped），修前 #335 失敗的步驟 7 與被略過的步驟 9～28 本次皆跑過），nightly 類 job skipped（排程／dispatch 專屬）。aisdlc-sdd-ci 與 shellcheck-ci 皆被觸發且 success（第二棒動了 `tools/git-hooks/post-merge`）。

- 取數指令：`gh run list --commit <完整 sha>`（**完整 40 碼**；短 sha 會靜默回 `[]`）與 `gh run view <id> --json jobs`；回填時另對 aisdlc-sdd-ci 與 shellcheck-ci（`paths:` 含 `tools/git-hooks/**`，第二棒動了 `tools/git-hooks/post-merge`）依是否觸發逐一標明（缺席＝未驗證，不是通過）。
- 回填前的狀態：第三列（DEF-200-525／526）的修法與鎖在工作樹、未 commit／push；Windows CI 實跑結果、各 workflow 是否觸發皆未知，不以本機全綠代替雲端。
- ONBOARDING §7 表② 的 scripts 指紋：〈二-10〉第一列的 `ec35ee2838d0` 是當時值；第三列拿掉 `AISDLC_SDD/scripts/tests/test_conftest_xdist_cpu_budget.py` 的標記後 live 值為 `04108ae4b139`（`sync_onboarding_baselines.py --check-snapshot` 回報 rc=1，待乾淨 venv 載具回填），回填後以載具輸出為準〔他包回報：Architect／QA 鏡、Developer 三棒各自量得〕。

---

## 〈五〉理論洞清單（P4；只登記、不修、不立輪；再開條件＝症狀驅動，見五問 README S1～S6）

> 合併來源：SA／SD／QA／Architect 四面鏡＋QA 鏡 B（518）＋三份設計備忘錄的誠實劃界，已去重。每條一句**可觀測**的再開症狀（一次真實事件即依 `FiveQuestion_Audit_Protocol/severity.md`〈暴露度〉升 P2 並入帳）；暴露度欄＝量法與結果。

### 五-A 喚醒鏈（planner／relay／schedule backend／halt 標記）

| # | 洞 | 暴露度（量法與結果） | 再開症狀 |
|---|---|---|---|
| 1 | 睡著／闔蓋的 Mac 不會被喚醒（`pmset repeat` 需 sudo，本專案刻意不碰；已知邊界，非待修 bug） | 邊界，未量 | 一次 reset 時刻 Mac 處於睡眠，醒來後 `woken` 事件的 `at` 比 `due_at` 晚逾一個巡邏間隔（附 sid＋痕跡列＋`pmset -g log` 對應段） |
| 2 | reset 時刻解不出 ⇒ 拒絕武裝／`escalate`（PRD C10：不猜、不退回「假設 5 小時」） | 設計 | 一次真撞線的 limit 訊息被判 `escalate`（理由含「拒絕用猜的」），而事後可由同一訊息解出 reset 時刻（附 sid＋逐字稿 seq） |
| 3 | L0 端點憑證在 launchd 無互動環境能否自取未驗；拿不到＝`kind=unknown` ⇒ PATROL_HANDBACK（延後非遺失） | 真機 1 筆：10:22:03 `probed` 的 `endpoint@10:20:04` 早 tick 119 秒，分不出自取或沿用快取（〈三〉）；sid 5535e815 J012 的 `measured_at` 與 tick 同秒（可能自取，未確證）。〔R212 第二列真機 E2E（〈十一〉）：①到點 tick 與③真 claude 的 `probed.text` 皆為 `endpoint@<tick 同秒>`（21:33:13／22:01:38）且額度快取 `measured_at` 同步更新 ⇒ launchd 無互動行程**可以**自取 L0 讀數（2 筆）；②到點 tick 沿用 77 秒前的快取（TTL 內，1 筆）〕 | 一次 launchd 觸發的 tick 其 `probed` 事件 `kind=unknown`，或 `text` 內 `endpoint@<時刻>` 早於 tick 逾快取 TTL 且 `source` 非 endpoint，致 `patrol_handback` 而同窗額度其實已恢復（附 sid＋痕跡列） |
| 4 | 到點後尾段（spawn→settle→哨兵重掛）在真 launchd 未實跑；含「job 行程內對另一 label `bootstrap`」是否被允許（C-A 唯一無法隔離證明的格子）；二層結論見〈二〉-0 | 隔離重現＋`LaunchdBackend`＋假 launchctl 整合測試；真機零筆（修後）。〔R212 第二列真機 E2E（〈十一〉）：三段皆走通——①②假 claude（0 token）、③真 `claude -p -r`（fable）；unload 帳逐字 `op=bootstrap label=AutoSDD_Sentinel_<sid> xpc=AutoSDD_SessionResume_<sid>`＝job 行程內 bootstrap 另一 label 被 launchd 允許（C-A 格已驗，①③各 1 筆）；`relay_done→sentinel_armed→relay_rearmed rc=0`、無 `sentinel_single_owner_deferred`〕⇒ 本條降為已驗，再開症狀照舊 | 一次續航 job 走完尾段後痕跡出現 `arm_failed`／`relay_rearm_failed`（或 `sentinel_armed` 缺席），且 `launchctl list` 無 `AutoSDD_Sentinel_<sid>`（附 sid＋痕跡＋launchctl 輸出） |
| 5 | `--no-allow-resume` 一次性 job 觸發後（`quota_back_no_resume`）只拆自己、不掛回哨兵：`tools/session_resume_planner.py` 該分支只 `_schtasks_remove`；R113 施工圖 §3(d) 判準 1 只列 relay 次態；推論〔讀碼，未驗〕：relatch 的 `claim_once`（`RELATCH_INTERVAL_SECONDS`＝900）在 claim 當下即消耗節流窗，自動復原最早要等上次 claim＋900 秒 | 真機 1 筆（sid 46b55125，10:22:03→10:23:04，由主控手動 `--arm-sentinel`，間隔 61 秒；驗收探針屬構造性）；planner 750／750，修它要先搬行 | 一次 `quota_back_no_resume` 之後、主 session 下一次工具呼叫之前，逐字稿出現 limit 事件而無人叫醒（附 sid＋seq；痕跡無 `sentinel_armed`） |
| 6 | INV5 讓位期間（一次性排程整段等待）哨兵不巡邏；`reset_at` 若比真實可用時刻晚則靜默多等；閘與觸發器用同一把本機鐘，本機鐘與伺服器鐘的偏差只靠 `RESET_SKEW_SECONDS`＝120 秒吸收，超過即回到「到點但伺服器尚未翻頁 ⇒ 探測說未恢復 ⇒ 重掛」的既有路徑 | 設計取捨，無痕跡 | 一次續航 job 等待期間逐字稿出現 limit 事件，而 job 到點前痕跡零動作（附 sid＋seq） |
| 7 | 顯式 `--at`（`reset_at==""`）在 mac 結構化 `at=None` ⇒ plist 只有 interval、無 calendar；A-1 閘對它不適用（SA-1 §7-D） | 無真機痕跡。〔R212 第二列真機 E2E：①③以顯式 `--at` 註冊，`launchctl print` 確為只有 `run interval = 900`、無 calendarinterval、狀態塊 `reset_at` 空（`reset_source=operator-asserted`）；kickstart 當第一個 tick 即探測＋spawn（設計行為）〕 | 一次 mac 上 `--register-schtasks --at <時刻>` 後 15 分鐘內出現 `probed`／`resumed`（附 sid＋`woken` 列） |
| 8 | 多軸殘餘：reset 後另一軸仍在 halt 帶卻 <100% ⇒ L0 判 open ⇒ 多燒一個續跑窗（續跑窗自己先 `--pace`、`settle_window` 判準②擋第二道） | 無真機痕跡 | 一次續跑窗起跑當下 `--pace` 仍顯示某軸 ≥ halt 帶（<100%）卻已 spawn（附 sid＋`probed`／`route_chosen` 列） |
| 9 | 手動 job（`kind=manual`）到點沒有「主 session 是否仍在動」檢查＝雙窗風險（`_resume_tick` 內第二個「該不該問」述詞的候選） | 真實時間線（反事實）：sid 5535e815 兌現時刻前最後一筆逐字稿距兌現 494.6 秒、兌現後首筆在 +104.1 秒〔SA 鏡自算〕。〔R212 第二列真機 E2E ③：手動 job 到點時小 session 逐字稿已 2062 秒無活動仍 spawn；真雙窗未發生（小 session 無人在用）〕 | 一次手動續航 job 到點 spawn 時，主 session 逐字稿在前一個巡邏間隔內仍有活動（附 sid＋seq） |
| 10 | Windows：E-A 讓標記存在期間 `arm_reset`（`-Once`）取代 15 分鐘巡邏 ⇒ 該段無閒置提醒／漂移自癒／新撞線偵測（mac 因 `StartInterval` 底盤不受影響） | Windows 未實機驗證 | 一次 Windows 自願 halt 標記存在期間，主控水位進 prepare 帶或另一軸撞線，而至兌現時刻前哨兵痕跡零列（附 sid＋痕跡） |
| 11 | Windows：`Unregister-ScheduledTask` 失敗（`STILL-PRESENT`、rc=1）時 INV5 仍把殘留 `-Once` 當擁有者讓位、對外 rc=0（R130 M-14）；7-C 的 Windows 對等（`disarm` 同步並驗證 REMOVED）只有註解與報告文字、沒有機械鎖 | 該機專屬，未驗 | 一次 Windows `disarm` 印 `STILL-PRESENT` 之後哨兵未掛上，或續航 job 收尾後哨兵讓位且零排程（附 sid＋痕跡） |
| 12 | E-A 的「兌現後有活動 ⇒ 標記視為過期」回 `None`，`sentinel_decided` 只剩 idle patrol 字樣，標記存在過這件事在痕跡上不可見；延後與 idle patrol 共用 `action=patrol`，只靠 `reason` 字面可辨；靜止守門的代價＝兌現時刻前後 900 秒內主控動過 ⇒ 叫醒最多延後一個巡邏間隔（為防雙窗付的價） | 構造性；靜止守門另有真時間線（兌現時刻時已閒置 8 分 15 秒、1 分 44 秒後又有新訊息）〔SA-4〕。〔R212 第二列真機 E2E ②：`arm_reset` 分支真機兩次（21:35:30 kickstart、21:50:31 interval tick；後者保留 calendar 不重載＝F5 格，bootout log 行數不增）、到點 `probe` 分支一次（22:00:05）；「靜止守門（不叫醒防雙窗）」分支未觀察〕 | 一次需事後解釋「halt 標記存在、時刻已過、為何沒叫醒」，而 `sentinel_decided` 只有 idle patrol 字樣、以 `action` 欄 grep 重建不出（附 sid＋seq＋標記檔）；或兌現時刻已過、主控早已閒置，續跑卻延後逾一個巡邏間隔（附 sid＋連續 `sentinel_decided` 的「不叫醒（防雙窗）」reason） |
| 13 | 合法 INV5 讓位時 `relay_rearmed rc=0` 不帶排程器憑證（R-4.5.6-6 張力；讓位≠失敗是既有語意） | 設計 | 一次 `relay_rearmed rc=0` 同窗有 `sentinel_single_owner_deferred`，而其後 `launchctl list` 無該 sid 任何 job（附 sid＋痕跡） |
| 14 | 7-B 修法殘餘：非 loud `alert` 仍會 GC `plan_dir()` 內 mtime ≥7 天的任務書，本窗任務書若本身 ≥7 天未被重寫也會被收（要等 ≥7 天且期間無人重寫，實際不可達）；且「非 loud 收尾的 `escalation.alert` 收超齡殘骸」這一行可被拿掉而無測試紅（QA 突變 MB1 存活） | 設計取捨，無痕跡 | 一次 relay 窗收尾後任務書消失且該窗 `relay_done`／`relay_stopped` 的 `gc_plans` 計入該檔；或 `~/.autosdd/plans/` 內 ≥7 天殘骸不減（附 sid＋痕跡） |
| 15 | 殭屍／鬼 job（plist 不在、launchd 仍載入、不在本行程集合；非哨兵前綴無 GC；延後 bootout 沒執行時＝痕跡 `defer_failed` 或父行程不退場，C-A 修後會與哨兵短暫並存）；`rearm` 可把哨兵同名 job 掛成未設閘的 `--resume-tick`（需付費探測，INV1 於無人模式禁止 ⇒ 生產不可達） | 無。〔R212 第二列真機 E2E ②：同名原地重掛 `relay_rearmed rc=0 unregister_rc=null rearmed_inplace=true`、延後 relaunch 四行 ×2（`bootstrap rc=0 tries=1`／`print rc=0`）；殭屍 job 未出現，`launchctl list` 收尾與基線相同〕 | `launchctl list` 出現 `AutoSDD_SessionResume_*` label 而其 plist 檔已不在且無活痕跡；或哨兵同名 job 的 argv 含未設閘的 `--resume-tick`（附 `launchctl print` 輸出） |
| 16 | 三個「900」鏡像（`RELATCH_INTERVAL_SECONDS` 無 parity）；`ERROR_FLAGS` 完備性無鎖；`--print-env-example` 與 `--env-doctor` 不互斥；`_NEXT_STEP_HEADING` 與 `HANDBACK_MARKERS[3]` 現同字串但無綁定；取節邏輯兩份（`_section_text`／`_section`） | 無漂移、無症狀 | 真實痕跡中 relatch 間隔與巡邏間隔數值不同；或新增 doctor 旗標漏進 `ERROR_FLAGS` 卻 rc=0；或兩個標題常數字面分家（附輸出） |
| 17 | planner 750／750 零餘裕（`# noqa: E702` 3→5、`# noqa: E501` 100→102；早醒閘用同行多語句擠進去）。預先設計好的下沉路徑＝SA-1 §3.2 A-2（`relay_machine.wait_for_reset`）；本輪不做：只買 2 行、需新增鎖並重寫 T6、無獨立暴露證據（違反〈守衛面准入〉「量、不挖」） | 結構債；`check_loc_budget.py --json` planner `loc=750`、`headroom=0`〔收尾親跑〕 | 任一缺陷修復需要在 planner 加 ≥1 條斷言行（`check_loc_budget` 回 `over_by>0`），或需在 `_resume_tick` 內加第二個述詞，或 `_TICK_DISPOSALS` 需新增名字，或再出現一行 `;` 並列擠行——先做 A-2 再做該缺陷 |
| 35 | 無人喚醒窗口內，模型照 `_RESUME_RULES`「附實測 rc」把 `git log --oneline -1; echo "rc=$?"` 寫成複合 Bash，`.claude/settings.unattended.json` 的 allow 只認 `Bash(git log*)` 單一指令形態 ⇒ harness 權限層要求核准、無人可核准，模型自行改成單一指令再跑（多耗 1 回合；handback 逐字自述此事） | 真機 1 筆：R212 第二列 ③（sid 70371a13，handback「附帶 `; echo "rc=$?"` 的複合形態被 harness 權限層要求核准，無人值守下改以單一指令執行」；〈十一〉） | 一次無人窗口因允許清單不認複合指令而整窗零產出（`resumed.out` 無 handback、`handback_missing`），或同一窗被擋 ≥3 次（附 sid＋逐字稿座標） |
| 36 | `settle` 的停止次態 `no_progress`／`quota_stop`／`relay_exhausted` 與 `RELAY_NEXT` 在真 launchd 未實跑，但它們是預設路徑上的分支（＝DONE 的補集：續跑窗 handback「## 下一步指令」非空即走到；`relay_machine.py:209-215` `plan_has_remaining_work`、`:307-321` `next_state`）。尾段與已在真 launchd 驗過的 DONE 尾段是同一段碼（`relay_machine.py:525-544`）；獨有差異＝`escalation.alert(loud=True)`（`quota_escalation.py:770-805`；`dead_agents=0` 時 `notify` 不呼叫，只寫紙＋`queue_notify`）與 `endurance_env.record_unattended_outcome`（`relay_machine.py:533-536`）＝純檔案 I/O；`RELAY_NEXT`（`relay_machine.py:500-521`）需要的真機原語＝「job 主行程在 job 內同名原地重掛」，正是〈十一-3〉② 驗過的 `rearmed_inplace=true` | 單元層：`test_mac_endurance_r83.py:1113-1137` 在假 job 內跑 DONE／NO_PROGRESS／QUOTA_STOP 三條尾段、`test_context_budget_guard.py:3703-3724` 十六格真值表；真機零筆（B+ 沒有順便走 `RELAY_NEXT`）〔SD 鏡 P3-4 讀碼，座標讀於 2026-10-12 工作樹〕 | 一次真實續跑窗走到上述任一停止次態或 `RELAY_NEXT`，而痕跡缺 `relay_stopped`／`relay_rearmed`，或收尾後 `launchctl list` 無 `AutoSDD_Sentinel_<sid>`（附 sid＋痕跡列＋launchctl 輸出） |
| 37 | 進度量法對「窗前已髒的檔」與「把工作 commit 掉」量成 0（`relay_machine.py:159-168` `files_changed`、`:218-222` `made_progress`、`:112-126` `no_progress_limit` 無人回合夾到 1）：量法 `len(after - before)` 只數「新出現的 porcelain 行」；續跑窗繼續改窗前就已髒的檔、或把工作 commit 掉，都量成 0 ⇒ 第一個窗就 `NO_PROGRESS_STOP`（loud）。方向是 fail-safe（停下並叫人），代價是接力在最常見的開發情境（撞額度時工作樹本來就髒）退化成單窗，且訊息「接力已連續無新進度」不實 | 構造性重現〔SD 鏡 P3-5；真 `relay_machine` 函式、暫存 git repo、`AUTOSDD_UNATTENDED=1`、handback 有下一步、band=free、seq=0；原輸出的 ASCII 直線以全形 `｜` 代〕逐字：`before: [' M a.py']`／`(a) edit already-dirty file   -> files_changed = 0 ｜ made_progress = False`／`(b) commit the work           -> files_changed = 0 ｜ made_progress = False ｜ after: []`／`(c) create a new file         -> files_changed = 1`／`(a) resolve -> NO_PROGRESS_STOP (no_progress_limit = 1 )`／`(b) resolve -> NO_PROGRESS_STOP`／`(c) resolve -> RELAY_NEXT`；無真實暴露 | 一次 relay 窗的 handback 自述有實質進度，而痕跡 `files_changed=0` 且判 `NO_PROGRESS_STOP`（附 sid＋痕跡）；便宜修法備忘＝另計 `git rev-parse HEAD` 是否變動與 `git diff` 內容雜湊是否變動（約 8 行；`relay_machine.py` 屬護欄層，需先搬等量史料） |
| 38 | 續跑窗（無人）內 hook 仍會派生 `--arm-sentinel`，而 INV1～5 鐵律未涵蓋這個組合：續跑窗 SessionStart 清閂鎖後，第一次 PostToolUse 即以整份逐字稿評估 `should_arm`（`sentinel_lifecycle_arm.py:93,147,241`），有歷史的續跑窗必走到 `spawn_sentinel`（`context_budget_guard.py:774-791`，`Popen` 不帶 `start_new_session`）。DEF-200-526 修後＝呼叫者非 job 本體即被 `arm()` 略過（無害）；但每個續跑窗仍多派生一個短命 planner，且真實鏈上它被孤兒化（`ppid=1`）的拓撲只靠 Developer 的行程樹取樣與 launchd 行為推得 | 構造＋真後端：SD 鏡以真函式＋合成逐字稿（40 回合／7020 秒）確認可達（`spawns total … 2`）；主控 B+（〈二-13〉）以真 launchd 重現殺 job（修前）並驗證修後略過；真實 hook 鏈（真 claude 視窗內派生）**未實跑** | 哨兵承載的續跑窗內出現 `arm_skipped_inside_job` 痕跡（`autosdd_sentinel_bootout_<label>.log`），其 `ppid` 既非 1 也非 `job_pid`（拓撲不在預期內），且當窗無 `resumed` 事件；或同窗該 log 出現 `parent-gone waited≤3s` 而當窗無 `resumed`／`relay_done`（附 sid＋痕跡） |
| 39 | `LaunchdBackend.disarm()` 的非自我路徑（`XPC_SERVICE_NAME` 不等於該 label）先 `plist.unlink()` 再同步 `launchctl bootout`——與 DEF-200-526 同型：子孫在 job 內呼叫它，會殺掉承載自己的 job；本輪只修 `arm()`。Windows schtasks 的對應面（子孫在 job 內註冊／移除）未量測：Windows 走 INV5 讓位路徑（SD 鏡讀碼：`_arm_sentinel` 見另一支 `SessionResume` job 即 deferred，屬良性），不在 526 修法射程 | 讀碼＋對稱推論（`disarm` 的非自我路徑是同步 bootout）；無真機痕跡；Windows 零量測 | 一次續跑窗內由子孫呼叫的 `disarm`／`--remove-schtasks` 之後，承載它的 job 消失且該窗無 `resumed`／`relay_done`（附 `autosdd_sentinel_unloads.jsonl` 該列的 `caller`／`ppid`／`xpc` 與 sid）；或 Windows 上續跑窗內的子孫呼叫使該窗的 `-Once` 工作被取消（附 `Get-ScheduledTask` 輸出） |
| 40 | 526 略過路徑回的憑證沿用 `_credential` 全套模板，前半在該路徑上**沒有被比對過**：`run interval = N seconds〔launchd 回讀，與請求相符〕` 與 `StartCalendarInterval = …〔…證明那個時刻真的排進去了〕` 是模板固定文字，而略過路徑的早退在 `_descriptor_problems` 比對**之前**；憑證末尾附加的「🔴 該 job 正在跑…不碰排程器、不改 plist」才是這條路徑的真話。⇒ 憑證前半句可能與請求不符卻寫「相符」（例：live 帶已過去的 `arm_reset` calendar，請求要改成別的時刻）；`schedule_backend.py` 的註解載明憑證字串會被 `append_log(..., credential=…)` 原封記下 | 真機 1 筆〔Docs 包由主控 B+ 修後輸出讀出；構造情境，未經四鏡審〕：探針 job 本無 interval，憑證卻印「`run interval = None seconds〔launchd 回讀，與請求相符〕`」與「最壞 None 秒後才有人動作」（〈二-13〉(c) 逐字） | 已於同列修正（第四棒）：早退路徑憑證改為自組短憑證——只陳述 launchd 自報的 `state`／plist 路徑並明寫「本路徑未與請求比對」，不再含「與請求相符」「planner 本體在列」「最壞 N 秒」；鎖＝`ArmNeverBootsOutAJobThatIsRunningTest` 的非本體那支（憑證不含「與請求相符」；突變 M1 還原成模板、M2 塞回該字樣，皆紅）；第五棒補頁尾與末句 |
| 50 | `ArmNeverBootsOutAJobThatIsRunningTest` 兩個存活突變（最終複審鏡 M10／M11）：早退憑證末句措辭無斷言；`_readback` 的 `pid =` 任意深度亦收（真機 print 只有 depth-1 有該行：Finder／Dock.agent／cloudphotod 唯讀樣本） | 構造，計 0 | 真機 print 出現巢狀 `pid =` 行或憑證末句回到未來宣稱 |

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
| 41 | UTF-16LE 存檔的 `.env`（Windows PowerShell 5.1 的 `>`／`>>`／`Out-File` 預設）被讀成 NUL 間隔的亂碼鍵：doctor 與 post-merge hook 都回報「0 個問題」，使用者寫的覆寫實際讀不到；`quota_env_layers.py` 的 `bom` 偵測只認 `﻿`（座標 `quota_env_layers.py:136`），UTF-16LE 以 `errors="replace"` 讀成 U+FFFD＋NUL 間隔，不觸發 `bom`／`unreadable`。與 #34 同一個洞，此列補 hook 版證據；ONBOARDING §2.2 已加警語（改用編輯器〔UTF-8 無 BOM〕或 pwsh 7） | 構造實測〔SD 鏡 P3-2／P4-5；mac 暫存 Windows 式 repo，`.env` 內 `AUTOSDD_QUOTA_HALT_PCT=90` 與 `AUTOSDD_MODEL_HELMSMAN=sonnet` 兩行完全沒生效〕逐字：`doctor rc=0`／`.env             存在，2 鍵`／`[foreign] 另有 2 行非 AUTOSDD_ 鍵（機密／他用）：不檢查、不印值`／`結論：0 個問題 ⇒ rc=0`；hook 同樣印 `env.shared 同步：0 個問題`；無真實語料 | 同 #34：一次本機 `.env` 以 UTF-16 存檔致其中的鍵未生效，而 doctor 或 hook 印 0 個問題（附檔頭位元組 `ff fe` 與 doctor／pull 輸出） |
| 42 | post-merge 成功路徑（`rc=0` 分支）只印一行，doctor 表內的 `〔process-env〕`（Windows 使用者層環境變數常見）被收尾行吞掉；`useMacWin.md` 卻要求看到它 ⇒ 同步「成功」時若有 `AUTOSDD_*` 行程環境變數蓋住檔案層，仍印 0 個問題 | 構造性〔SD 鏡 P4-2：讀碼＋S1 輸出，表內 `AUTOSDD_SENTINEL_OFF = 1〔process-env〕` 被 hook 的收尾行吞掉〕；無真實暴露 | 一次 pull 後 hook 印「0 個問題」，而 `--env-doctor` 的表內有 `〔process-env〕` 蓋住 `env.shared` 的鍵、致 `--pace`／`--check` 顯示的門檻與 `env.shared` 不同（附 pull 畫面＋doctor 輸出）；便宜修法備忘＝rc=0 分支對 `〔process-env〕` 計數、非零時多印一行（約 2 行） |
| 43 | linked worktree（`.claude/worktrees/*`）內 merge 時 post-merge 印「請跑 dev_start」，與單一 .venv 原則（ONBOARDING §2.1：全樹只有根層 `.venv`，第二顆會被擋下）矛盾；`pick_repo_python` 的 stderr 補救指令被 hook 內的 `2>/dev/null` 吞掉；無害但誤導 | 讀碼〔SD 鏡 P4-4〕；無真實暴露 | 一次在 linked worktree 內 merge，hook 印「請跑 dev_start」而使用者照做、反被單一 `.venv` 掃描擋下（附畫面）；便宜修法備忘＝訊息改為「找不到 repo 根 .venv（若在 linked worktree 內可忽略）」 |

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
| 44 | 判準三對 argparse 說明文字全盲（`tools/tests/test_subprocess_encoding_hygiene.py` 的 `nonascii_console_lines` 只看 `print`／`sys.std*.write`）；同族存量：非豁免 8 支（`AutoClaude/autoclaude/artifact_check.py`、`AutoClaude/tools/` 下 `ac4_nightly_collector.py`／`c6_staging_validator.py`／`drift_log_snapshot.py`／`mutmut_cache_counts.py`／`mutmut_exit_code.py`／`tree_state.py`、`tools/lib/dev_platform_provenance.py`）＋豁免 3 支（`_ENTRY_WAIVERS` 內：`_backfill_emit_real`／`mutation_baseline_lock`／`perf_baseline_lock`）在 `PYTHONIOENCODING=cp1252` 下 `--help` 全部 `rc=1` 加 `UnicodeEncodeError: 'charmap' codec can't encode characters …`；主產品 CLI `python -m autoclaude --help` 同樣 cp1252 rc=1（cp950 與 utf-8 皆 rc=0） | 構造·普查〔Architect 鏡 P4-1，依「量、不挖」計 0〕：AST 普查（掃描根同判準三，1045 檔）`entry points w/o protection whose argparse text has non-ASCII: 17`；其中可當腳本跑的非豁免 8 支與豁免 3 支共 11 支親跑如上；`anonymizer.py`／`slv_generator.py` 兩支被靜態述詞列為無保護但動態 rc=0；`pii_scanner.py`／`main.py`／`chaos_runner.py`／`render_topology_dashboard.py` 以腳本形態跑會 ImportError，非本類，未判；`dev_platform_provenance.py` 雖被 `prepare-commit-msg` 每次 commit 叫起，但其 `nonascii_console_lines==[]`、非 `--help` 路徑無非 ASCII 輸出，無暴露；無 CI 或使用者回報 | 一次 CI 或使用者回報上述任一入口（含 `python -m autoclaude --help`）在非 UTF-8 主控台 `UnicodeEncodeError`（附 run id 或畫面）；若要一併收：`nonascii_console_lines` 擴到 argparse 文字（約 +8 行）＋逐支加保護或縮 `_ENTRY_WAIVERS`，需獨立一包。注意登進缺陷帳本會讓未結列由 0 變正而構成 R 系列開輪事件，故走本表登記 |
| 45 | R85 取數只吃 `python <repo 相對路徑>.py`（`_LIVE_ENTRY_RE`）：`python -m …` 與無 `python` 前綴的入口不在射程；另鐵律三表「console 編碼」列的機械物欄尚未登記 R85 敲擊 | 構造〔Architect 鏡 P4-2〕：親跑取數＝9 支（`AISDLC_SDD/scripts/sdd_version.py`、`AutoClaude/tools/check_loc_budget.py`、`tools/check_handoff_carriers.py`、`tools/lib/cpu_budget.py`、`tools/lib/quota_policy.py`、`tools/probe/misstep_attribution.py`／`reset_window_distribution.py`／`shell_command_corpus.py`、`tools/session_resume_planner.py`）；根 CLAUDE.md 另出現 31 個存在於磁碟、不在 R85 集合的 `.py` 路徑，其中人用入口 `tools/probe/audit_session.py`、`tools/check_hooks_liveness.py`、`tools/check_ntfs_paths.py`、`tools/probe/xplat_hazard_census.py`、`AutoClaude/tools/local_ci_gate.py` 皆有保護（`hook_wiring.py`／`endurance_env.py` 無 `__main__`）⇒ 無暴露；不建議為補鐵律三表而改根 CLAUDE.md（被 9 族鎖直讀、且正是本事件的觸發面） | 根 CLAUDE.md 新增一個非 `python <路徑>.py` 形態的現查入口而其 `--help` 在非 UTF-8 主控台爆（附 CI run 或畫面）；補強選項＝R85 對 `live_check_entries()` 的每支入口再斷言 `has_utf8_stdio_protection(源碼)`（路徑無關，約 +8 行；Architect 鏡親跑該述詞對 9 支入口現況逐支皆 `True`，HEAD 版 cpu_budget 為 `False`） |
| 46 | `_ENTRY_WAIVERS`（`_ENTRY_WAIVER_CEILING=9`）的 `ruff-debt` 理由 4 筆中 2 筆已過期 | 構造〔Architect 鏡 P4-3；在 `AutoClaude/` 下親跑 `ruff check`〕：`tools/_backfill_emit_real.py ruff_rc=1`（`Found 2 errors.`）、`tools/mutation_baseline_lock.py ruff_rc=1`、`tools/perf_baseline_lock.py ruff_rc=0`（`All checks passed!`）、`tools/setup_pg_runtime_role.py ruff_rc=0`（`All checks passed!`）；另 `carrier-protected` 兩筆：`tools/run_root_unittests.py` 的 `import _stdio_utf8` 為真，`AutoClaude/tests/fixtures/dummy_cli.py` 的載具宣稱未能驗證 | 一次要縮 `_ENTRY_WAIVERS` 或查其理由時發現 `ruff-debt` 理由與 `ruff check` 現況不符（附 `ruff` 輸出）；建議另案就地為 `perf_baseline_lock.py` 與 `setup_pg_runtime_role.py` 加保護、移出表並把 `_ENTRY_WAIVER_CEILING` 9→7（方向＝只准縮；檔案在 AutoClaude 樹） |
| 47 | `tools/tests/test_check_hooks_liveness.py` 殘存 `child-encoding-ok` 標記的 WHY 與類 docstring 寫「六支」註冊 hook 腳本，數字已漂移（現 8 支）；舊債、非第三列造成 | 構造〔Architect 鏡 P4-4〕：`hook_command_scripts(.claude/settings.json)` 去重 `registered hook scripts (distinct): 8`（`block_bash_on_windows`／`block_destructive_git`／`check_claim_provenance`／`context_budget_guard`／`lint_powershell_command`／`sdd_hook_router`／`AutoClaude/tools/hooks/check_ps1_encoding`／`check_sh_eol`） | 一次有人依該 docstring 的「六支」判斷哪幾支 hook 被判準釘住而判錯（附畫面）；順手修法備忘＝改成不寫數字（淨 0 行） |
| 48 | `aisdlc-sdd-ci`／`aisdlc-sdd-fsm-chaos-nightly` 的 `paths:` 看不見新依賴邊 `tools/lib/cpu_budget.py → tools/lib/platform_utils.py`（惰性載入 `tools/_stdio_utf8.py`）：兩者只列 `tools/lib/cpu_budget.py`；兩支的消費端皆 fail-open 的 CLI subprocess，root-infra／windows／macos 已覆蓋該改動 | 構造〔QA 鏡 P4-2／Architect 鏡 P4-5 以第一棒形態量；Docs 包以第二棒形態 `git grep -c` 重量〕：`tools/lib/cpu_budget.py` 在 windows-compat-ci 4 條、macos-compat-ci 4、aisdlc-sdd-ci 2、aisdlc-sdd-fsm-chaos-nightly 2、root-infra-ci 1（無 paths 篩選，恆跑）；`tools/lib/platform_utils.py` 與 `tools/_stdio_utf8.py` 在 windows／macos 各 2 條、aisdlc-sdd-ci 與 fsm-chaos-nightly 皆 0 條；`test_ci_paths_cover_root_consumers.py` 不模型化遞移依賴（Architect 鏡親跑 rc=0）；無暴露 | 只改 `platform_utils.py`／`_stdio_utf8.py` 的 push 沒有觸發 aisdlc-sdd-ci 或 fsm-chaos-nightly，而該 CI 消費 cpu_budget 的 worker 數因而退化成預設（附 run 列表與 `[cpu_budget]` 廣播行） |
| 49 | dev_start 的 [2/7] GitHub 同步（`git pull --ff-only`）早於 [4/7] venv 與 [5/7] git hooks 檢核（會重設 `core.hooksPath`）：hook 在 dev_start 內觸發時 `.venv`／`core.hooksPath` 可能尚未就緒；hook 的略過訊息「請跑 dev_start」在 dev_start 內是循環的，且 dev_start 不在尾段補跑 doctor；全新 clone 第一次 dev_start 的 [2/7] pull 沒有 hook。人工補救＝〈八-1〉驗收一行（pull 後一律再跑 doctor） | 構造〔SA 鏡 P4-1；步驟順序 Docs 包親跑 `grep` `tools/dev_start.py` 的步驟標題：[2/7] GitHub 同步→[3/7] 平台切換→[4/7] venv／依賴整備→[5/7] git hooks 檢核〕：三個 dev_start 入口檔（`.py`／`.ps1`／`.sh`）對 `env-doctor`／`env.shared`／`quota_env` 零命中〔SA 鏡〕；無暴露 | 一次全新 clone 的第一次 dev_start 之後，`.env` 仍遮住 `env.shared` 而無任何一處出聲（附 `--env-doctor` 輸出與 dev_start 全文）；便宜修法備忘＝dev_start 尾段補跑一次唯讀 doctor（屬 `tools/`，非守衛面清單） |

---

## 〈六〉五問協定 S4／S5 處置與 PRD §16.2 T4 對照

### 六-1 五問協定（`docs/06_quality/FiveQuestion_Audit_Protocol/README.md`〈窗口規則與收斂判定〉）

- **S4 成立**：本輪出現 P≤2——DEF-200-516／521／522／523／524（守衛面，皆有真機痕跡）與 DEF-200-518（產品面）皆 P2。S4 的另一半「宣稱被擋而前面沒有真阻斷」：本輪無。
- **S5 成立**：守衛面有變動（planner、`quota_messages`、`sentinel_lifecycle`、`quota_gate`、`quota_policy`，及 D-1 的 hook `_GOV_EXACT`），且每一處附暴露證據或掌舵者原文（〈二〉-8）。
- **本輪做了什麼**：①P2 全數同輪 fixed（未結 2→0，〈四〉）；②每處守衛面新增逐項附暴露證據或掌舵者原文，沒有「無證據新增」（〈二〉-8）；③審查口徑「量、不挖」：五面鏡的構造性命中（SD 的 heading 形態探針、BOM／cp950／UTF-16 構造實測、QA 突變實驗）一律只登 P3／P4 或〈五〉、不計 P≤2、不另立缺陷列——本輪新立的 521～524 皆有真機痕跡或真實語料，不是構造所得（〈七〉）；④五問協定目錄零改動（不觸發 `PROTOCOL-CHANGED`、不重置窗口）。
- **本輪不做什麼**：不開五問再評輪——不跑評估機（Windows）的 `audit_session.py` 三項症狀閘指令、不寫輪帳本 `symptom_streak`、不重產 Q4′ 的 `session_gate_acceptance_*.json`。理由：S4／S5 只是「有資格再評」的條件（README 原文「才開一輪再評」），再評量的是評估機主控視窗的誤擋、裸宣稱與 Q2′ 逾期，與本輪缺陷（喚醒鏈與參數檔）沒有量值對應；本輪守衛面變動沒有碰任何五問判準函式。掌舵者若要正式再評，指令與基線取法逐字在 README。
- **第三列（DEF-200-525／526）不改變 S4／S5 處置、不開五問再評**：DEF-200-525（P2）在非守衛面（`tools/lib/cpu_budget.py` 與 `tools/tests` 鎖，〈二-12〉）；DEF-200-526（P2）在喚醒鏈後端 `schedule_backend.py`（不在根 CLAUDE.md〈守衛面准入〉列舉的守衛面；以真後端的構造情境量測，〈二-13〉）；兩者皆同輪發現、同輪 fixed，未結維持 0。S4 字面成立（又出現 P≤2），處置與本節「本輪不做什麼」一條相同——與五問量值（收斂型工具誤擋／漏攔、裸宣稱、Q2′ 逾期）沒有對應，只是「有資格再評」、不開；S5 字面成立但只是註解：終態樹 15 個修改檔與守衛面清單比對唯一命中 `tools/session_resume_planner.py`（第五棒 3 行註解、零程式行）〔最終零信任複審鏡（14 檔時）與收尾包（終態 15 檔）各親跑：`grep` rc=0〕；處置同本節第一列：不新增守衛碼或鎖、不開五問再評。事件驅動面：`check_defect_log_crossref.py --unresolved-count`＝「未結列數＝0／全部 227 列」、`check_handoff_carriers.py` 首行「[census] 當前輪＝R212（…未結承接輪號＝空）」〔Docs 包親跑〕——沒有未結列、沒有承接輪號，R 系列沒有開輪事件。

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

PRD §4.5.2／§4.5.5／§4.5.6／§4.5.8／§4.5.10 在 mac 路徑上被真機暴露的 5 個缺陷已修（各有紅綠測試），入口時間閘已在真 launchd 驗過；PRD §16.3 的 ⏸31／📎8 本輪未動、仍由症狀驅動再開；「完成實作」依 §16.1 的定義＝101 列恰落四格，v2.1.17 已成立，本輪沒有新增 ✅。不對外宣稱 PRD 全面完成（31 列功能延後等症狀、8 列只欠驗收紀錄）、24h／至少 4 次 reset 連續閉環，或自願 halt 之後無條件自動續跑（邊界逐條在〈五〉）；§16.1 對 ✅ 的定義是「機制在、有測試或鎖」而不是「真機走通」，§4.5.5／§4.5.6／§4.5.8 三條 ✅ 在 2026-10-10 的真機上實際斷在五個點，本輪修了這五點。

【R212 第二列（2026-10-11 晚）追記】到點之後的尾段（探測→續跑→handback→收尾→哨兵掛回）的每個接縫，已在本機真 launchd 上各走過（〈十一〉；含 7-C／7-E 修後行為與 C-A 格）；共三次：①②用假 claude（0 token；②由**手寫**的 halt 標記經哨兵 arm_reset→calendar 到點叫醒）、③用真 `claude -p -r`（fable）一次但由手動排程起頭（無標記、無 calendar）。**沒有任何一次同時是「標記起頭」＋「真 claude」**。仍**不**宣稱：真撞線寫出標記（7-E 生產端）、24h／至少 4 次 reset 連續、Windows、睡眠喚醒。

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

### 七-2 第三列四方審查（修復後對照；DEF-200-525／526；2026-10-12）

> 時序與範圍（依各鏡判決檔的時間戳與其所引內容推得）：四鏡審的是 Developer **第一棒**落地後的工作樹——各鏡判決檔都載「9 個修改檔」（與第一棒回報的 9 檔相同），引的 repin 值為 116348→116347、sha `f44d4f15bce6…`，cpu_budget 為 `sys.path.insert`＋`import _stdio_utf8` 形態。第二棒（吸收四鏡 P3／文件訂正的程式面）、第三棒（DEF-200-526，由 SD 鏡 P2-1 逼出）、第四棒（早退路徑憑證自組）、第五棒（頁尾／末句／planner 註解）、文件修復包編修與第三次真 launchd B+（最終碼）都發生在判決**之後**；四鏡**沒有**審過它們。它們由 2026-10-12 的最終零信任複審鏡（Sonnet，唯讀，另出判決）獨立重跑覆核。角色全程唯讀、零信任；突變實驗一律在 scratchpad 隔離副本。

| 鏡 | 判決（首行逐字） | 概況（各鏡自述） |
|---|---|---|
| QA 鏡 | `VERDICT: APPROVE` | 無 P1／P2；P3 ×3、P4 ×3；Developer 與主控宣稱的每個數字皆親跑重量、無一對不上（只有耗時秒數略有不同） |
| Architect 鏡 | `VERDICT: APPROVE` | 零 P1、零 P2；P3 兩條（便宜就修，不阻擋 commit）、P4 五條（只登記） |
| SA 鏡 | `VERDICT: CONDITIONAL` | 0 個 P1；5 個 P2（3 個是「對掌舵者的轉述句」、2 個是 commit 前要補的文件）；P3 ×6、P4 ×3；沒有發現程式碼或鎖層面的錯，要修的幾乎都在「說法」 |
| SD 鏡 | `VERDICT: CONDITIONAL` | 零 P1；1 條 P2（S14 在預設路徑上未驗）；其餘 P3／P4；cpu_budget 修法的設計可 commit，post-merge 在 Windows 上沒有找到「靜默什麼都不做」或「做壞事」的會擋 commit 的路徑 |

**P2 清單與處置**

| 發現 | 性質 | 處置 |
|---|---|---|
| SA P2-1 | 對掌舵者的轉述句：「喚醒鏈……整段走通三次」過度宣稱——三次是同一條「到點後尾段」的三個切片，沒有任何一次同時是「標記起頭」＋「真 claude」 | 〈六-3〉追記改句（下方〈轉述句型〉第 1 句）；〈十一〉本身的限定一直誠實，被壓縮掉的是「到點後尾段／兩次假 claude／手寫標記」這幾個限定詞 |
| SA P2-2 | 對掌舵者的轉述句：「PRD 落款完成」＋「還沒做的仍只等症狀（例如 24 小時連續多次 reset、Windows 真機）」——功能沒做的有 31 列，且舉的兩個例子都不是延後格 | 〈六-3〉第一段改句；〈轉述句型〉第 3 句 |
| SA P2-3 | 〈八〉驗收條件寫成「看 pull 畫面」，但「畫面完全沒有 hook 字樣」是真實、靜默的分支（失效的表徵與成功相同） | 〈八〉header 與〈八-1〉改為「pull 後一律再跑唯讀驗收一行」；新增〈八-1b〉診斷 hook 為何沒出聲 |
| SA P2-4 | 本列在證據檔沒有落款；兩個 guard-total 站與鎖檔 repin 列都寫「逐檔清單見…〈二〉」而〈二〉沒有第三列段落；〈二-10〉舊數字、〈九〉「共六處」過期 | 〈二-12〉與〈二-13〉＋〈二-10〉第三列 bullet（Developer 第三棒已寫）＋〈九〉導言改寫 |
| SA P2-5 | 對掌舵者的轉述句：不可宣稱「windows-compat-ci 已修好」（修法在工作樹、未 push；#335 步驟 9～28 共 20 步被略過）；帳本 525 狀態格缺「Windows CI 實跑待驗」註記 | 帳本 525 狀態欄已加「CI 實跑待對帳」（690 bytes）；〈四-3〉預留雲端對帳；〈轉述句型〉第 4 句 |
| SD P2-1 | S14：每個有歷史的真實續跑窗，hook 都會派生 `--arm-sentinel`；哨兵承載的續跑窗內 `arm()` 同步 bootout 會殺掉在跑的 job | **DEF-200-526**：主控以 B+ 真機量測確認（修前紅、修後綠），修法與鎖見〈二-13〉；〈十一-5〉S14 列同步改寫 |

**P3／P4 去向**（已修＝本輪文件或第二棒程式面已處理；登〈五〉＝只登記、不修）

| 發現 | 一句 | 去向 |
|---|---|---|
| SA P3-1 | 〈六-3〉同節內部矛盾（先寫「不對外宣稱…閉環」，追記又寫「可以宣稱…閉環已真機實跑」） | 已修：〈六-3〉兩段改寫 |
| SA P3-2 | 帳本 516／523 狀態欄仍寫「到點 spawn 後尾段未真機實跑」「C-A 修後未真機實跑」（方向保守、與〈十一〉相反） | 已修：Developer 第二棒改為「到點後尾段已真機驗（〈十一〉）」「C-A 已真機驗（〈十一〉）」（695／696 bytes，≤700） |
| SA P3-3 | 〈二-11〉「`core.hooksPath` 兩台皆指根層」對 Windows 是未量測的斷言；「Windows 實機未驗」低報了已有的間接證據 | 已修：〈二-11〉兩處改寫 |
| SA P3-4 | 〈十一-5〉少列一項：三次 `route_chosen` 全是 SESSION_RESUME，另兩條路由真機零筆 | 已修：〈十一-5〉末列 |
| SA P3-5 | 轉述句「看到 0 個問題或已自動修復就代表兩台一致」過寬；〈八-1〉步驟 3 把「98〔env.shared〕」寫死 | 已修：〈八-1〉步驟 3；〈轉述句型〉第 5 句 |
| SA P3-6 | `.venv\Scripts\python.exe` 不存在時 `"doctor rc=$LASTEXITCODE"` 會沿用上一個指令的 0，印出假的 `doctor rc=0` | 已修：〈八-1〉各指令加 `$LASTEXITCODE = $null;` |
| SA P4-1 | dev_start 的 [2/7] pull 早於 [4/7] .venv 與 [5/7] hooksPath | 登〈五〉#49 |
| SA P4-2 | Mac nightly 最近一次彙總「PASS=3 FAIL=2」（SA 寫於 2026-10-12 01:40；失敗簽名與兩列已修缺陷吻合） | 不立項。其後 2026-10-12 02:00 的排程樣本：`AutoClaude/logs/nightly_mac_latest.log` 尾段「===== nightly 彙總：PASS=5 FAIL=0 =====」、heartbeat 2026-10-11T18:04:10Z〔Docs 包親跑，讀檔〕；該次排程跑的是當時的工作樹（並行編修期間），不保證等同乾淨 HEAD |
| SA P4-3 | Windows 待驗沒有外部阻塞軌載體 | 不登帳（〈八-4〉自稱非再開事件；符合「不製造日期義務」）；〈八〉header 已明講要在 Windows 親跑驗收一行並回報 |
| SD P3-1 | `AUTOCLAUDE_SKIP_HOOKS=1` 時 post-merge 零輸出，與「hook 沒被叫到」同畫面 | 已修：Developer 第二棒補一行出聲 |
| SD P3-2 | 使用者面缺五件（hook 沒跑的畫面、無標記行會被刪、UTF-16LE、改了 env.shared 沒 push、dev_start 建議的 `git pull --rebase` 不觸發 hook） | 已修：ONBOARDING §2.2 與〈八〉header／〈八-4〉；UTF-16LE 的程式面偵測登〈五〉#41 |
| SD P3-3 | 自動修復總結行沒說刪了什麼、怎麼還原（`AutoClaude/.env` 內刻意更嚴的引擎停機線會被靜默放寬） | 已修：Developer 第二棒總結行帶「刪除 N 行（內容見上方 diff；還原＝把備份檔複製回原檔）」；ONBOARDING 補「無標記行會被刪」 |
| SD P3-4／P3-5 | settle 停止次態未真機；進度量法對窗前已髒的檔量成 0 | 登〈五〉#36／#37 |
| SD P4-1 | cpu_budget 慣用法（`init_utf8_streams()` 為多數派） | 已修：Developer 第二棒（〈二-12〉） |
| SD P4-2／P4-4／P4-5 | 成功路徑不印 `〔process-env〕`；linked worktree 訊息誤導；`bom` 偵測不認 UTF-16 | 登〈五〉#42／#43／#41 |
| SD P4-3 | post-merge 檔頭「新機器第一次 pull 即生效」自相矛盾 | 已修：Developer 第二棒訂正檔頭 |
| SD P4-6 | 真 repo 根殘留 `.env.bak.20261011T055059Z` | 〈十〉：待掌舵者驗收後手動刪 |
| Architect P3-1 | R85 鎖的敲擊接線沒有自證 | 已修：Developer 第二棒 `_knock`＋有牙格（〈二-12〉） |
| Architect P3-2 | cpu_budget 用了少數派形態且失去 fail-open | 已修：Developer 第二棒改 `platform_utils`（〈二-12〉） |
| Architect P4-1～P4-5 | 判準三對 argparse 文字全盲；R85 取數射程；`_ENTRY_WAIVERS` 過期理由；「六支」數字漂移；workflow paths 遞移依賴 | 登〈五〉#44～#48 |
| Architect 文件訂正 5a～5e、6 | 〈二-12〉缺／〈四-1〉首行過期／〈九〉導言過期／輪籤跨日／〈六-1〉補句；`test_check_hooks_liveness.py` 的「六支」 | 已修：〈二-12〉、〈四-1〉、〈九〉導言、輪籤、〈六-1〉末條；「六支」登〈五〉#47 |
| QA P3 ×3 | 〈二-10〉指標懸空；〈九〉導言過期；帳本 525 狀態欄缺 Windows CI 註記 | 已修：〈二-12〉與〈二-10〉第三列 bullet；〈九〉導言；帳本「CI 實跑待對帳」 |
| QA P4 ×3 | cp950 不是更好的模擬（資訊性）；aisdlc-sdd-ci 的 paths；更深一層根因只在 Developer 回報 | cp950 事實入〈二-12〉；paths 登〈五〉#48；根因敘事入〈二-12〉〈原有的鎖為何沒擋住〉 |

**轉述句型**（SA 鏡〈四〉「不能說的句子」；對掌舵者轉述時以右欄為準；數字出自 SA 鏡親跑與 PRD §16.3，未經 Docs 包重驗，帳本列數除外）

| # | 不能說 | 改說 |
|---|---|---|
| 1 | 「喚醒鏈在 Mac 上整段走通三次。」 | 「到點之後的尾段，在 Mac 的真排程器上走過三次：兩次用假 claude、一次用真 claude；停機標記是手寫的；沒有一次是『標記起頭＋真 claude』。」 |
| 2 | 「根因徹底解決」「不會再有下一個缺陷」「收斂完成」 | 「兩層根因已找到；五個已知缺陷已修、接縫已在 Mac 真後端走過；下一次真的撞額度，才是修完之後第一次真實全鏈驗證；之後仍由症狀驅動。」 |
| 3 | 「PRD 所有功能都已完成」「PRD 落款完成」 | 「PRD 101 列各有歸宿：29 已落地、33 依設計不做、31 功能延後等症狀（沒做）、8 只欠驗收紀錄；歸格是我代決，你可推翻。」 |
| 4 | 「windows-compat-ci 已修好」「下次會綠」 | 「Mac 上以 cp1252 模擬，紅→綠已驗；修復尚未 push；要等 push 後該 workflow 整個 job 步驟 1～28 都 success 才算。」 |
| 5 | 「Windows 那台一 pull 就自動同步好了」「看到 0 個問題就代表兩台一致」 | 「pull 通常會觸發 hook，但以 pull 後再跑一行 doctor 的 `doctor rc=0` 為準；它代表這台的檔案層沒有遮蔽 env.shared，行程環境變數、帳號有沒有 fable 權限不在比對內。」 |
| 6 | 「.env 同步已在 Windows 驗證 OK」 | 「流程控制在 GitHub Windows runner 通過（間接，替身 python）；你那台真機未驗。」 |
| 7 | 「撞線→停機標記→自動續跑已真機驗過」 | 「消費端（標記→哨兵→到點→探測→續跑）在 Mac 真排程器驗過；標記由真撞線寫出的那一頭沒驗。」 |
| 8 | 「帳本清零／沒有未結」 | 「P≤2 未結 0（全部 227 列〔Docs 包親跑 `--unresolved-count`〕）；另有外部阻塞 5、結構性長債 6 不計入；〈五〉理論洞（#1～#50）只登記。」 |

最終零信任複審鏡（2026-10-12）判決 `VERDICT: CONDITIONAL`（P2×1＝守衛面零改動句不實、P3×8、P4×8），全部於同列處置（P4-4／P4-5 兩條判為不改），見本檔各節；複核判決另記於下方。

複核判決：最終零信任複審鏡對收尾包套用結果的唯讀複核（2026-10-12）＝`VERDICT: APPROVE`：P2-1 與 P3-1～P3-8、P4-1／2／3／6／7／8 皆如實處置（改句命中 1／原句命中 0；程式與數字對終態 15 檔樹相符；21 個測試模組 rc=0；P3-7 四突變與 schedule_backend 八突變皆咬住）；殘餘＝R1 懸空指標與 R3 先行詞（收尾單人窗口已就地改）、R4／R5 措辭與鎖缺口 P4（登記），不阻擋 commit〔他包回報：最終零信任複審鏡；收尾單人窗口照單套用〕。

---

## 〈八〉Windows 機待辦（事實驅動，無輪號義務；本輪 mac 開發，Windows 側零量測）

> 【R212 第二列追記（2026-10-11 晚；2026-10-12 第三列訂正）】`tools/git-hooks/post-merge` 已落地：步驟 1 的 `git pull --ff-only` 成功後會**自動**跑步驟 2 的體檢；問題全是可自動修的旗標時會自動做步驟 3（先備份 `.env.bak.<UTC>`）並再體檢一次，三段輸出都印在 pull 的畫面上。所以 Windows 機做完步驟 1 之後，**一律再跑一次步驟 2 的「驗收」一行**（唯讀）；驗收看它印出的 `doctor rc=0`——這行由 PowerShell 自己印、是 ASCII，不受主控台編碼影響——不要靠 pull 畫面判斷。pull 畫面只當加分：出現 `env.shared 同步：0 個問題`／`已自動修復，備份＝…` 是好消息；**畫面完全沒有 `env.shared 同步` 字樣，不代表成功**：hook 在「Already up to date.」、`core.hooksPath` 漂移或未設（ONBOARDING §6：搬移後不報錯、直接失效）、走了 rebase、或在 IDE 的 Git 面板按 Pull（輸出不一定出現在終端機，未驗）時都不會留下任何字；cp950 主控台上 hook 的中文行也可能亂碼（未驗）。`AUTOCLAUDE_SKIP_HOOKS=1` 殘留時，修後的 hook 會印一行「跳過」（修前零輸出）。看到 `需要人處理` 字樣才做步驟 3；看到 `找不到 .venv python，略過 env.shared 同步` 先跑 `. tools\dev_start.ps1` 再做驗收。hook 的控制流已在 windows-latest（Git for Windows 的 bash、替身 python）由 `TestPostMergeHook` 七支實跑通過（推論，細節見〈二-11〉）；這台 Windows 機器上仍未驗的只有 `core.hooksPath` 是否指對（見〈八-1b〉）、cp950 主控台顯示、`.venv\Scripts\python.exe` 實解（後者與 pre-commit／pre-push 同函式 `pick_repo_python`，每次 commit／push 都在跑），列入〈八-4〉第 6 項。**pull 畫面沒有任何 `[post-merge dispatcher]`／`🔴 env.shared 同步` 行＝這支 hook 沒跑** ⇒ 直接做驗收。

### 八-1 國小版三步（在 repo 資料夾內開 PowerShell；指令皆已過 `lint_powershell_command`，路徑由 `git rev-parse --show-toplevel` 現查、不寫死）

1. **同步**：

   ```powershell
   Push-Location (git rev-parse --show-toplevel); git pull --ff-only; "pull rc=$LASTEXITCODE"; Pop-Location
   ```

   要看到 `pull rc=0`。不是 0：先看〈八-2〉；不要 stash、不要 reset。
2. **驗收**（唯讀；**每次 pull 後都做**，不論 pull 畫面印了什麼）：

   ```powershell
   Push-Location (git rev-parse --show-toplevel); $LASTEXITCODE = $null; $o = & .\.venv\Scripts\python.exe tools/lib/quota_policy.py --env-doctor; "doctor rc=$LASTEXITCODE"; $o | Select-String "AUTOSDD_QUOTA_HALT_PCT|AUTOSDD_MODEL_HELMSMAN"; Pop-Location
   ```

   通過＝印出 `doctor rc=0`，且兩行的來源欄都是〔env.shared〕（值＝repo 根 `env.shared` 檔內同名那行的值；不要拿本檔的數字當標準）。`doctor rc=` 後面空白＝直譯器沒跑起來（`.venv\Scripts\python.exe` 不存在：先跑 `. tools\dev_start.ps1`）；`rc=1`＝要看全文，改跑下面的展開版。（`$LASTEXITCODE = $null` 是刻意的：不重設的話，直譯器找不到時會沿用上一個指令的 0，印出假的 `doctor rc=0`；pwsh 7 於 mac 實測，5.1 同理為推論〔他包回報：SA 鏡〕。）`doctor rc=0` 只代表**這台的檔案層**沒有遮蔽 `env.shared`：行程環境變數另以〔process-env〕標出，被注入 hook 行程的 `.claude/settings*.json` 的 `env` 區塊 doctor 看不到（〈五〉#20），帳號有沒有 fable 權限也不在比對內（〈五〉#23）。

   含 pull 的一行版（最累的情況用；`pull rc` 不是 0 先看〈八-2〉）：

   ```powershell
   Push-Location (git rev-parse --show-toplevel); git pull --ff-only; "pull rc=$LASTEXITCODE"; $LASTEXITCODE = $null; $o = & .\.venv\Scripts\python.exe tools/lib/quota_policy.py --env-doctor; "doctor rc=$LASTEXITCODE"; $o | Select-String "AUTOSDD_QUOTA_HALT_PCT|AUTOSDD_MODEL_HELMSMAN"; Pop-Location
   ```

   `pull rc=0` 只代表 pull 成功，不代表同步成功；同步成功只看 `doctor rc=0` 加兩行來源欄。mac 上以 pwsh 7 對同形狀（把直譯器路徑換成 `.\.venv\bin\python`）實跑的輸出〔他包回報：SA 鏡；`Select-String` 輸出前多一個空行，已省略〕：

   ```text
   doctor rc=0
     AUTOSDD_QUOTA_HALT_PCT                       = 98〔env.shared〕
     AUTOSDD_MODEL_HELMSMAN                       = fable〔env.shared〕
   ```

   展開版（`rc=1` 時看全文；唯讀）：

   ```powershell
   Push-Location (git rev-parse --show-toplevel); $LASTEXITCODE = $null; & .\.venv\Scripts\python.exe tools/lib/quota_policy.py --env-doctor; "doctor rc=$LASTEXITCODE"; Pop-Location
   ```

   `rc=1`＝它會逐行說哪裡多餘、遮住共享設定、壞值或重複。出現 `[unknown]`／`[bad-value]`／`[duplicate]`／`[bom]`／`[unreadable]`／`[missing-shared]` 時停手回報（`--fix` 不處理它們）。表中出現 `〔process-env〕`＝這個 shell 或 Windows 使用者層環境變數有 `AUTOSDD_*`，它贏過所有檔案層，先弄清楚是誰設的。
3. **有問題才修**（只在步驟 2 的旗標都屬 `redundant`／`shadows-shared`／`engine≠harness`／`dead` 時）：

   ```powershell
   Push-Location (git rev-parse --show-toplevel); $LASTEXITCODE = $null; & .\.venv\Scripts\python.exe tools/lib/quota_policy.py --env-doctor --fix; "fix rc=$LASTEXITCODE"; Pop-Location
   ```

   然後再跑一次步驟 2 的驗收，**必須**看到 `doctor rc=0`（＝doctor 末行「結論：0 個問題 ⇒ rc=0」），且表中 `AUTOSDD_QUOTA_HALT_PCT` 與 `AUTOSDD_MODEL_HELMSMAN` 兩行的來源欄是〔env.shared〕、值等於 `env.shared` 檔內該行（乾淨根目錄的實跑形狀：`AUTOSDD_QUOTA_HALT_PCT                       = 98〔env.shared〕`〔收尾親跑，Mac〕；數字會隨 `env.shared` 改值而變，以該檔為準）；備份檔 `.env.bak.*` 驗收後手動刪。

### 八-1b 想知道 hook 為什麼沒出聲（只在 pull 畫面沒有 `env.shared 同步` 字樣時看）

```powershell
Push-Location (git rev-parse --show-toplevel); git config --get core.hooksPath; "hooksPath rc=$LASTEXITCODE"; Test-Path tools/git-hooks/post-merge; Pop-Location
```

正常：第一行是**這個 clone** 的 `…/tools/git-hooks`、`hooksPath rc=0`、最後一行 `True`（mac 同形狀實跑逐字：`/Users/wuweihong/Antigravity/AISDCL_Agent/tools/git-hooks`、`hooksPath rc=0`、`True`〔他包回報：SA 鏡〕）。第一行空白（rc=1）或指到別的資料夾＝hook 不會跑 ⇒ 跑 `. tools\dev_start.ps1`（其 [5/7] git hooks 檢核會重設 `core.hooksPath`）。畫面只有 `Already up to date.`＝沒有新 commit 可合併，hook 本來就不會跑。兩種情形都靠步驟 2 的驗收一行把關。

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
6. `tools/git-hooks/post-merge`（env.shared 自動同步）在 Windows 的首次 `git pull` 實跑：hook 由 Git for Windows 的 bash 執行（控制流已有 windows-latest 的間接證據，見〈二-11〉；推論，未見逐測試通過列）、`pick_repo_python` 解析到 `.venv\Scripts\python.exe`（與 pre-commit／pre-push 同函式，每次 commit／push 都在跑）、`core.hooksPath` 是否指對（〈八-1b〉）、cp950 主控台下中文與 `≠` 的顯示、Windows Python 輸出帶 `\r` 時旗標行計數（SD 鏡於 mac 以 CRLF 包裝器實測無害：`_count` 錨在行首、不吃行尾）、舊 `.env` 若為 PowerShell 5.1 的 BOM／UTF-16LE 或 cp950 存檔時的實際 UX（BOM 與 cp950：hook 刻意不修、只出聲；UTF-16LE：doctor 讀成亂碼鍵、回報 0 個問題，hook 同樣印 0 個問題，登〈五〉#41）；第二棒新增的 hook 字樣（skip 分支、刪除行數與還原法）在 Windows 的 `grep -c`／`${ndel:-0}` 行為未驗；mac 已以 `.env.example` 13 個歷史版本＋本機真實舊備份當舊複本重放 14/14 自動修復〔QA 鏡回報〕。驗收＝〈八-1〉步驟 2 的驗收一行（`doctor rc=0` 與兩行〔env.shared〕來源欄）；pull 畫面只當加分。

---

## 〈九〉〈史料〉——搬出 `tools/tests` 的沿革原文（逐字；來源座標＝`file:line`＠HEAD 見各小節標題）

> 這 13 段（L1～L13）原本是 `tools/tests` 內的 docstring／註解（沿革與事故史料，不是「本檔守什麼」的規格敘述）。本輪為抵銷護欄層行數成長，把它們逐字搬到這裡；原處各留一句仍在約束今日行為的 WHY 與指標「史料搬至 `CrossPlatform_R212_WakeChain_EnvLayer_Evidence.md`〈史料〉」（或指名 L 編號）。來源座標與 HEAD 見各小節標題（L1～L6＠9032bebf、L7／L8＠035746ba、L9～L13＠a7b20b7e）。逐段核對：L1～L8 全文在標題所述 HEAD 對應檔案的該行起原樣存在〔收尾親跑 `git show HEAD:<檔>` 子字串比對〕；L9～L11 另經 Architect 鏡與 QA 鏡各自獨立比對為逐字相同，L12／L13 為 Developer 第二棒自行逐行比對（`verbatim=True`）〔他包回報〕。

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

### L7 重釘接鏈列旁註（R104～R142；`_FROZEN_PREFIX_REWRITE_LEDGER`）｜來源 `tools/tests/test_adr_xplat001_c1c2_lock.py:3368`＠HEAD 035746ba（166 行，其中旁註 107 行；資料列原樣仍在原處）

```text
    ("R101", "423d63fddc0a", "44008855c9e8", "DEF-200-208"),
    ("R102", "44008855c9e8", "c44b6a066da8", "DEF-200-204"),
    ("R102", "c44b6a066da8", "605806a0d4aa", "DEF-200-218"),
    ("R102", "605806a0d4aa", "23b5b6fcc0a2", "DEF-200-207"),
    ("R102", "23b5b6fcc0a2", "cb643af00b7a", "DEF-200-219"),
    ("R102", "cb643af00b7a", "bc7080dcd3f2", "DEF-200-220"),
    ("R103", "bc7080dcd3f2", "b698a52087af", "DEF-200-221"),
    # DEF-200-223：R104 PRD §4.2.5／§4.2.1 BURSTING/EWMA 落地，同體例「追加後立即  round-label-ok
    # 自我凍結」——本輪淨額 -18：測試 +62 與搬遷散文 -91 相抵後，本檔自身兩列
    # （稽核列＋本凍結前綴延伸列）+11，prefix_len 61→62 涵蓋兩列本身。
    ("R104", "b698a52087af", "967b8b322da4", "DEF-200-223"),
    # DEF-200-224：R105 淨額 34-43+9=0，prefix_len 62→63 涵蓋本列本身，逐項見 _GUARD_LINES_REPIN_LOG 同輪列。round-label-ok
    ("R105", "967b8b322da4", "cae90354814a", "DEF-200-224"),
    # DEF-200-202：四方複審 REJECT 修復（quota_gate.py 補 active_model 接線＋  round-label-ok
    # 回歸測試），同體例「追加後立即自我凍結」——本輪追加兩列（功能淨額 +49 ＋
    # 本檔自身編修 +12），prefix_len 63→65 一次涵蓋兩列本身。
    ("R105", "cae90354814a", "763624f17dde", "DEF-200-202"),
    # DEF-200-202：四方複審修復續（`_platform_helpers.py` 折長行＋  round-label-ok
    # `test_defect_id_reference_integrity.py` DEF-200-015 姊妹帳本擴面），同體例
    # 「追加後立即自我凍結」——本輪追加一列，prefix_len 65→66 涵蓋本列本身。
    ("R105", "763624f17dde", "a520bdcef8b7", "DEF-200-202"),
    # DEF-200-202：帳本狀態欄回填 fixed@R105 觸發 dirent-primitive 債表 round-label-ok
    # 微幅上升，同體例「追加後立即自我凍結」——本輪追加一列，prefix_len 66→67
    # 涵蓋本列本身。
    ("R105", "a520bdcef8b7", "a64463e662c1", "DEF-200-202"),
    ("R106", "a64463e662c1", "76bb05948f27", "DEF-101-561"),
    # DEF-101-752：R82 收斂殘餘承接站點，同體例「追加後立即自我凍結」——本輪追加一列
    # （多支 tools/tests/ 掃描面站點改為 tracked ∪ untracked-not-ignored，含本檔自身
    # 逐檔漂移，逐筆重釘過程已收斂合併為單列），prefix_len 71→72 涵蓋該列本身。
    ("R106", "76bb05948f27", "026523f64c92", "DEF-101-752"),
    # DEF-101-752 問題 3 收斂（帳本結案輪修復包重釘漏補）：8 站點永久回歸測試類別 round-label-ok
    # 落地時未重釘本表（ARCH-01 同型復發），本輪補一列（含本檔自身逐檔漂移的兩列
    # 追加），prefix_len 73→75 涵蓋全部新列本身。
    ("R106", "026523f64c92", "6d3be18839b6", "DEF-101-752"),
    # 帳本結案包 #3（DEF-200-166 窗口）：追加本輪稽核列並把它納入前綴（prefix_len 75→76）。
    ("R107", "6d3be18839b6", "b42d19e1db20", "DEF-200-166"),
    ("R107", "b42d19e1db20", "abd0dc217e2b", "DEF-200-141"),  # B2/B3 措辭與指針訂正（2026-08-28）
    # DEF-200-230 回歸鎖窗口：追加本輪稽核列並把它納入前綴（prefix_len 76→77），同體例
    # 「追加後立即自我凍結」——延伸本身即讓指紋改變，故仍須在此留痕。
    ("R108", "abd0dc217e2b", "21c85dff06f9", "DEF-200-230"),
    # DEF-200-233 修復窗口（macos-compat-ci）：追加本輪稽核列並把它納入前綴 round-label-ok
    # （prefix_len 77→78），同體例「追加後立即自我凍結」——延伸本身即讓指紋改變，故留痕。
    ("R108", "21c85dff06f9", "4e0397833463", "DEF-200-233"),
    # DEF-101-747 換載體（Gap C：表② 指紋 stale 的發現時點提前到 dev_start [6/7]）：
    # 追加本輪稽核列並把它納入前綴（prefix_len 78→79），同體例「追加後立即自我凍結」。
    ("R109", "4e0397833463", "dc62ee5d1822", "DEF-101-747"),
    # F2 修復窗口（quota 測試活體態滲入；載體＝DEF-200-232）：R109 追加本輪稽核列 round-label-ok
    # 並把它納入前綴（prefix_len 79→80），同體例「追加後立即自我凍結」。
    ("R109", "dc62ee5d1822", "42b28e14a0b8", "DEF-200-232"),
    # DEF-200-121 修復窗口（護欄層判準修補輪）：追加本輪稽核列並把它納入前綴
    # （prefix_len 80→81），同體例「追加後立即自我凍結」——延伸本身即讓指紋改變，故留痕。
    ("R111", "42b28e14a0b8", "db3448c59433", "DEF-200-121"),
    # 結構性長債分軌輪（2026-08-30）：追加本輪稽核列並依「追加後立即自我凍結」判例
    # 延伸前綴涵蓋該列本身（81→82）；Phase2 到期義務同窗記入 [提案]，載體＝該 DEF。
    ("R113", "db3448c59433", "369320d0f7f9", "DEF-200-211"),
    # v2.1.13 G1 實作批 (a)（喚醒鏈最後一哩）：追加本輪稽核列並依「追加後立即自我凍結」
    # 判例延伸前綴涵蓋該列本身（82→83）；載體＝DEF-200-231②（headless 窗口許可層）。
    ("R113", "369320d0f7f9", "7301deef344e", "DEF-200-231"),
    # v2.1.13 G2 實作批 (b)（handback 交接可見性）：追加本輪稽核列並依「追加後立即
    # 自我凍結」判例延伸前綴涵蓋該列本身（83→84）；載體＝DEF-200-236（交接可見面）。
    ("R113", "7301deef344e", "4b6d79935d12", "DEF-200-236"),
    # v2.1.13 G3+G4 實作批 (c)+(d)（接力狀態機＋哨兵自癒）：追加本輪稽核列並依「追加
    # 後立即自我凍結」判例延伸前綴涵蓋該列本身（84→85）；標號改用 R114（理由見 round-label-ok
    # `_GUARD_LINES_REPIN_LOG` 該列）；載體＝DEF-200-234（受統籌自循環，PRD §3(c)）。
    ("R114", "4b6d79935d12", "ea038ea6ff4e", "DEF-200-234"),
    # R115 收斂棒 round-label-ok（三個修復棒＋治理批累積漂移一次性合法收束）：追加本輪稽核列並依
    # 「追加後立即自我凍結」判例延伸前綴涵蓋該列本身（85→86）；載體＝DEF-200-239
    # （排程孤兒回歸鎖，本輪 test_context_budget_guard.py 內容主要新增項之一）。
    ("R115", "ea038ea6ff4e", "4e5f11565d23", "DEF-200-239"),
    ("R115", "4e5f11565d23", "0c0aa4967799", "DEF-200-239"),
    ("R115", "0c0aa4967799", "9316ce4e91ed", "DEF-200-239"),
    # ADR-XPLAT-013 Phase2 (b)(c) 分軌計價落地：追加本輪稽核列並依「追加後立即自我
    # 凍結」判例延伸前綴涵蓋該列本身（88→89）；載體＝DEF-200-211。
    ("R116", "9316ce4e91ed", "1bd8f0d4e396", "DEF-200-211"),
    # Architect 鏡一審承接補釘，同體例「追加後立即自我凍結」（prefix_len 89→90 涵蓋 round-label-ok
    # 該列本身；A-1/A-2/N-1 詳 CrossPlatform_R116_Scan_Findings.md）。
    ("R116", "1bd8f0d4e396", "a08e0c7043be", "DEF-200-211"),
    # P1-2/P1-3 批追加 R117 稽核紀錄＋分軌首次申報，同體例「追加後立即自我凍結」。round-label-ok
    ("R117", "a08e0c7043be", "d16dc6498956", "DEF-200-234"),
    # P1-4 檢查表規則鎖批追加稽核紀錄，同體例「追加後立即自我凍結」（91→92）。round-label-ok
    ("R117", "d16dc6498956", "f37361174a7f", "DEF-101-886"),
    # DEF-200-212 P1-5 收尾批：追加五列（落地＋自身編修＋三批史料搬遷）並依「追加後 round-label-ok
    # 立即自我凍結」判例延伸前綴涵蓋全部新列本身（92→97）。
    ("R118", "f37361174a7f", "862ff00ae26d", "DEF-200-212"),
    # P1-6 批：skip 天花板①②③與 M6 落款④共同變更鎖落地，追加本輪稽核紀錄（落地＋
    # 本表自身編修二列）並依「追加後立即自我凍結」判例延伸前綴涵蓋全部新列本身
    # （99→101）；載體＝DEF-200-240。
    ("R119", "862ff00ae26d", "7f11c682ae08", "DEF-200-240"),
    # P1-6 批續（round-label-ok）：全套背景跑揪出兩項真違規（R119_HANDOFF.md 零 stale
    # 宣稱、subprocess text=True 缺 encoding）修復後追加稽核列，依「追加後立即自我
    # 凍結」判例延伸前綴涵蓋本列本身（101→102）；載體＝DEF-200-240（同批延續）。
    ("R119", "7f11c682ae08", "21bdbf9b9595", "DEF-200-240"),
    # P1-6 批修復包（DEF-200-240 同批延續）：F1 共同變更鎖判準粒度由檔案級改為剖面
    # 鍵值級，F2 governance_docs.py E501 拆行，同體例「追加後立即自我凍結」——
    # 本輪追加三列（落地列＋本表自身編修二列）並延伸前綴涵蓋全部新列本身（103→107）。
    ("R119", "21bdbf9b9595", "4554dbed8bf5", "DEF-200-240"),
    # R120 收尾：212 結案批＋P1-7 SD-4/SD-8＋SA-4 的守衛線重釘使 round-label-ok
    # `_REPIN_LOG_HISTORY_SHA256` 前進，同體例「追加後立即自我凍結」——本輪追加
    # 本列＋一個 repin 稽核列，prefix_len 109→110 涵蓋新 repin 列本身。
    ("R120", "4554dbed8bf5", "dc94d1a10d4f", "DEF-200-241"),
    # 精準修復輪收尾：三筆缺陷落地＋散文搬遷抵銷的守衛線重釘使 round-label-ok
    # `_REPIN_LOG_HISTORY_SHA256` 前進，同體例「追加後立即自我凍結」——本輪追加三個
    # repin 稽核列＋本列，prefix_len 110→113 涵蓋全部新列本身。
    ("R122", "dc94d1a10d4f", "7d9eb06de5a7", "DEF-200-222"),
    # 精準修復輪第二棒收尾：三筆落地的守衛線重釘使指紋前進，同體例 round-label-ok
    # 「追加後立即自我凍結」——本棒追加一個 repin 稽核列＋本列，prefix_len 114→115。
    ("R123", "7d9eb06de5a7", "4ec1e958f341", "DEF-200-205"),
    # 落地輪收尾：結案批回歸鎖＋到期義務兌現的守衛線重釘使指紋前進，同體例 round-label-ok
    # 「追加後立即自我凍結」——本輪追加一個 repin 稽核列＋本列，prefix_len 115→116。
    ("R126", "4ec1e958f341", "faddc843e042", "DEF-200-241"),
    ("R127", "faddc843e042", "a4b92fe15365", "DEF-200-133"),
    # R129 喚醒鏈零浪費收尾：4 包 +1300 行回歸鎖的守衛線重釘使指紋前進， round-label-ok
    # 同體例「追加後立即自我凍結」——本輪追加一個 repin 稽核列＋本列，
    # prefix_len 117→118 涵蓋新 repin 列本身。
    ("R129", "a4b92fe15365", "1bff7d5bf52e", "DEF-200-266"),
    # R130 M-01/M-05 喚醒鏈死碼修復：cbg +112 回歸鎖的守衛線重釘 round-label-ok
    # 重釘使指紋前進，同體例「追加後立即自我凍結」——本輪追加一個 repin 稽核列＋本列，
    # prefix_len 118→119 涵蓋新 repin 列本身；載體＝DEF-200-266（喚醒鏈同家族）。
    ("R130", "1bff7d5bf52e", "79ab4a9a386e", "DEF-200-266"),  # round-label-ok
    # R131 喚醒鏈四方審計對抗查證與確認破洞修復：cbg／run_root_unittests round-label-ok
    # 回歸鎖的守衛線重釘。重釘使指紋前進，同體例「追加後立即自我凍結」——本輪追加一個
    # repin 稽核列＋本列＋本檔自身編修，prefix_len 119→120 涵蓋新 repin 列本身；
    # 載體＝DEF-200-272（四方審計撿回同家族）。
    ("R131", "79ab4a9a386e", "3a6d5d17cd32", "DEF-200-272"),  # round-label-ok
    # R131 收尾：喚醒鏈規則6崩潰根因修復（write_relay 任務書消失未捕捉例外）回歸鎖 round-label-ok
    # ＋本檔自身編修（cost-envelope 測試補 regression_lane 參數）使指紋再前進；
    # 同輪追加一個 repin 稽核列＋一個回歸鎖軌列＋本列，prefix_len 120→121 涵蓋新列本身；
    # 載體＝DEF-200-272（同家族）。
    ("R131", "3a6d5d17cd32", "1d5bb6d4bec1", "DEF-200-272"),  # round-label-ok
    # R131 二度收尾：對抗式複審發現的收尾修復回歸鎖＋本檔自身編修，prefix_len round-label-ok
    # 121→122 涵蓋新列本身；載體＝DEF-200-272（同家族）。
    ("R131", "1d5bb6d4bec1", "2b2619269538", "DEF-200-272"),  # round-label-ok
    # R132 三度收尾：規則2/3拆除／規則7 leak_fence／規則8無值宣稱／規則5 macOS round-label-ok
    # 串接測試四項回歸鎖＋本檔自身兩筆稽核列，prefix_len 122→124 涵蓋新列本身；
    # 載體＝DEF-200-272（同家族）。
    ("R132", "2b2619269538", "60a3d5bf721b", "DEF-200-272"),  # round-label-ok
    # R133：DEF-200-274 落地——凍結前綴延伸 124→126 涵蓋新兩列本身，同既有體例。round-label-ok
    ("R133", "60a3d5bf721b", "b7448766903c", "DEF-200-274"),
    ("R134", "b7448766903c", "e069a86b7750", "DEF-200-274"),
    # R134 續：DEF-200-274 第三輪對抗式複審收斂批——新增真實 subprocess round-label-ok
    # 回歸測試使護欄層行數重釘，凍結前綴延伸涵蓋新增列本身。
    ("R134", "e069a86b7750", "5f040dde89da", "DEF-200-274"),
    # R135：DEF-200-274 第四輪四方複審收尾——work-stealing 動態派工重構回歸測試＋ round-label-ok
    # TOCTOU 緩解＋回歸鎖軌／到期義務三處新增，凍結前綴延伸涵蓋新增列本身。
    ("R135", "5f040dde89da", "1e3073cee390", "DEF-200-274"),
    # R136：DEF-200-274 第四輪第二次對抗式複審收斂——BaseException 型別缺口回歸 round-label-ok
    # 測試＋回歸鎖軌新列＋本檔自身逐檔漂移，凍結前綴延伸涵蓋新增列本身。
    ("R136", "1e3073cee390", "08ffdc430461", "DEF-200-274"),
    # R137：DEF-200-274 第五輪四方獨立複審收尾——全庫 TOCTOU 病灶排查修復＋回歸 round-label-ok
    # 淨額上限到期義務兌現列＋本檔自身逐檔漂移，凍結前綴延伸涵蓋新增列本身。
    ("R137", "08ffdc430461", "6843feaf786c", "DEF-200-274"),
    # R138：DEF-200-274 第六輪——test_platform_utils_dedup.py 補 _zzz_ 排除（前五輪 round-label-ok
    # 排查未涵蓋此檔）＋本檔自身逐檔漂移，凍結前綴延伸涵蓋新增列本身。
    ("R138", "6843feaf786c", "7b88d4c61478", "DEF-200-274"),
    # R139：DEF-200-274 第六輪四方獨立複審收斂——補齊 dispatch_granularity.py round-label-ok
    # 零測試覆蓋缺口，凍結前綴延伸涵蓋新增列本身。
    ("R139", "7b88d4c61478", "7f78df45354f", "DEF-200-274"),
    # R140：DEF-200-274 第七輪——新增負載不均自動偵測（dispatch_imbalance.py）＋ round-label-ok
    # 四方獨立複審共同點名的 fair_share 分母真缺陷回歸鎖，凍結前綴延伸涵蓋新增列本身。
    ("R140", "7f78df45354f", "d27ba8c13f10", "DEF-200-274"),
    # R141：DEF-200-274 第八輪——四方獨立複審修復收尾（worker_count 公式測試／CI round-label-ok
    # wiring 回歸鎖／GitHub Actions annotation 測試），凍結前綴延伸涵蓋新增列本身。
    ("R141", "d27ba8c13f10", "6f595278360c", "DEF-200-274"),
    # R142：DEF-200-275／DEF-200-277 收尾——兩個獨立缺陷收斂附帶的 guard-line round-label-ok
    # 記帳延伸，凍結前綴延伸涵蓋新增列本身。
    ("R142", "6f595278360c", "b97e86a790f0", "DEF-200-277"),
```

### L8 重釘接鏈列旁註（R143～R165；`_FROZEN_PREFIX_REWRITE_LEDGER`）｜來源 `tools/tests/test_adr_xplat001_c1c2_lock.py:3534`＠HEAD 035746ba（76 行，其中旁註 49 行；資料列原樣仍在原處）

```text
    # R143：DEF-200-275 第四輪——分子改讀逐字稿 API usage＋parity 鎖新增，凍結 round-label-ok
    # 前綴延伸涵蓋新增列本身（prefix_len 由 --print-guard-lines 印出）。
    ("R143", "b97e86a790f0", "7bd3af08e2e2", "DEF-200-275"),
    # R143 同輪追加：第 1 輪審查修復（SA-R4-03 候選鏈測試）再延伸凍結前綴一列。 round-label-ok
    ("R143", "7bd3af08e2e2", "3d5c464c7535", "DEF-200-275"),
    # R144：DEF-200-278 喚醒鏈缺口收尾——新增 test_wake_chain_halt_r278.py，凍結 round-label-ok
    # 前綴延伸涵蓋新增主表列與本軌新列本身（prefix_len 152→153）。
    ("R143", "3d5c464c7535", "39ac03acd0f7", "DEF-200-278"),  # 同輪三度追加
    # R144：DEF-200-275 第五輪 D15——check_claim_provenance.py 新增第五個判準 round-label-ok
    # unbacked_block_claim_hits()，凍結前綴延伸涵蓋新增主表列與本軌新列本身。
    ("R144", "39ac03acd0f7", "19e2a68ac40e", "DEF-200-275"),
    # R144：DEF-200-281 喚醒鏈鑑識收尾——halt 標記寫入自檢＋test_quota_policy.py round-label-ok
    # 測試污染止血，凍結前綴延伸涵蓋新增主表列與本軌新列本身。
    ("R144", "19e2a68ac40e", "55ce75c14334", "DEF-200-281"),
    # R144 第二輪：DEF-200-281 RC-3（halt 閂鎖鍵補 sid）＋naive-now 防呆兩項修復， round-label-ok
    # 凍結前綴延伸涵蓋新增主表列與本軌新列本身。
    ("R144", "55ce75c14334", "846054db5d7e", "DEF-200-281"),
    # DEF-200-275 第六輪：四方複審 REJECT→D17～D25 修復→修後複審全 APPROVE；凍結前綴延伸
    # 涵蓋新增主表列（自含式，含本軌新列本身），起點接 R144 終點 846054db5d7e。 round-label-ok
    ("R145", "846054db5d7e", "67af3c96e763", "DEF-200-275"),
    # R146：DEF-200-275 第七輪收尾單人窗口——package A／B 合法新增＋Dev-Trim7 散文搬遷 round-label-ok
    # 抵銷造成的逐檔漂移收斂（自含式：本檔自身編修亦計入），凍結前綴延伸涵蓋新增
    # 主表列與本軌新列本身，起點接 R145 終點 67af3c96e763。 round-label-ok
    ("R146", "67af3c96e763", "a4aa9940f730", "DEF-200-275"),
    # R146 續：DEF-200-275 第七輪收尾單人窗口（Dev-D8）—DEF-200-287（Windows 稽核帳本 round-label-ok
    # 檔案鎖競態三棒修復）／DEF-200-288（status line harness 進料兩棒）收尾：功能軌新增
    # test_statusline_context_feed.py 等鎖檔、回歸鎖軌 TestConversationLedgerChildTimeoutParity、
    # Dev-Trim8 十五支散文搬遷抵銷造成的逐檔漂移收斂（自含式：本檔自身編修亦計入），
    # 起點接上一列終點 a4aa9940f730。
    ("R146", "a4aa9940f730", "054135e143d6", "DEF-200-287"),
    # R147：DEF-200-274 第九輪收尾單人窗口——P1/P0 zshrc 假紅根治＋LPT 快取／自動 round-label-ok
    # 細分／不均偵測 v2 新判準能力鎖檔＋既有缺陷修復回歸鎖，凍結前綴延伸涵蓋新增
    # 主表列與本軌新列本身，起點接 R146 終點 054135e143d6。 round-label-ok
    ("R147", "054135e143d6", "f436d6837308", "DEF-200-274"),
    # R148：DEF-200-274 第十輪收尾單人窗口——四方獨立審查第九輪產出後 5 包並行修復 round-label-ok
    # （xdist 開關調整／ci-gate 允許清單／halt_verdict 活動容忍窗／139.9s 測試拆三平台
    # 具名子類別／staleness advisory 對稱化）造成的新增主表列與本軌新列自身漂移，
    # 凍結前綴延伸涵蓋新增列本身，起點接 R147 終點 f436d6837308。 round-label-ok
    ("R148", "f436d6837308", "ca5dd474ef16", "DEF-200-274"),
    # R149：DEF-200-293/294/295 root-infra 三筆缺陷收尾——新增主表列與本軌新列自身 round-label-ok
    # 漂移，凍結前綴延伸涵蓋新增列本身，起點接 R148 終點 ca5dd474ef16。 round-label-ok
    ("R149", "ca5dd474ef16", "d7d2f8f98dc8", "DEF-200-293"),
    # R150：DEF-200-297／299 單一 .venv 收斂＋DEF-200-296 鑑別力補強——新增主表列與 round-label-ok
    # 本軌新列自身漂移，凍結前綴延伸涵蓋新增列本身，起點接 R149 終點 d7d2f8f98dc8。 round-label-ok
    ("R150", "d7d2f8f98dc8", "7c1770cb38ca", "DEF-200-297"),
    # R151：DEF-200-301～306 單一 .venv 收斂收尾——新增主表列與本軌新列自身漂移， round-label-ok
    # 凍結前綴延伸涵蓋新增列本身，起點接 R150 終點 7c1770cb38ca。 round-label-ok
    ("R151", "7c1770cb38ca", "0618d2c4affc", "DEF-200-301"),
    # R152：DEF-200-307～310 單一 .venv 四方審查殘餘收尾——新增主表列與本軌新列自身 round-label-ok
    # 漂移，凍結前綴延伸涵蓋新增列本身，起點接 R151 終點 0618d2c4affc。 round-label-ok
    ("R152", "0618d2c4affc", "8b034cee4c63", "DEF-200-307"),
    # R152 沿用：DEF-200-314 mac launchd nightly 三症狀修復——新增主表列與本軌新列 round-label-ok
    # 自身漂移，凍結前綴延伸涵蓋新增列本身，起點接 R152 終點 8b034cee4c63。 round-label-ok
    ("R152", "8b034cee4c63", "038461e50767", "DEF-200-314"),
    # R152 沿用：DEF-200-314 四方複審四項非阻斷修正——新增主表列與本軌新列 round-label-ok
    # 自身漂移，凍結前綴延伸涵蓋新增列本身，起點接 R152 終點 038461e50767。 round-label-ok
    ("R152", "038461e50767", "70959d5b8295", "DEF-200-314"),
    ("R153", "70959d5b8295", "ea0a3bfec58f", "DEF-200-289"),
    ("R154", "ea0a3bfec58f", "f62eab34f224", "DEF-200-320"),
    # R155：新增主表兩列（內容＋收斂）與本軌新列自身漂移，凍結前綴延伸涵蓋新增列本身。round-label-ok
    ("R155", "f62eab34f224", "96325f09b5d5", "DEF-200-315"),
    # R156：DEF-200-324 pre-push 整合閘門修復——新增主表兩列與本軌新列自身 round-label-ok
    # 漂移，凍結前綴延伸涵蓋新增列本身，起點接上一列終點 96325f09b5d5。round-label-ok
    ("R156", "96325f09b5d5", "d1780bab5946", "DEF-200-324"),
    # R157：多 CPU 第十四輪＋DEF-200-325 對話框根治——新增主表兩列與本軌新列自身 round-label-ok
    # 漂移，凍結前綴延伸涵蓋新增列本身，起點接上一列終點 d1780bab5946。round-label-ok
    ("R157", "d1780bab5946", "b55177a84c3b", "DEF-200-325"),
    ("R158", "b55177a84c3b", "e402247cc758", "DEF-200-333"),  # round-label-ok
    ("R159", "e402247cc758", "3765b9dedf5d", "DEF-200-345"),  # round-label-ok
    ("R163", "3765b9dedf5d", "0bf86e99a2d2", "DEF-200-354"),  # round-label-ok
    # DEF-200-358：dev_start [1/7] git 平台 provenance 修復窗口——追加本輪稽核列並依
    # 「追加後立即自我凍結」判例延伸前綴涵蓋該列本身（240→241）。
    ("R164", "0bf86e99a2d2", "8595fde4cf0b", "DEF-200-358"),  # round-label-ok
    # DEF-200-359：WindowsSmoke 逃生口缺失根治窗口——追加本輪稽核列並依「追加後立即
    # 自我凍結」判例延伸前綴涵蓋該列本身（241→242）。
    ("R165", "8595fde4cf0b", "c4350df6e968", "DEF-200-359"),  # round-label-ok
```

### L9 重釘接鏈列旁註（R166～R173；`_FROZEN_PREFIX_REWRITE_LEDGER`）｜來源 `tools/tests/test_adr_xplat001_c1c2_lock.py:3463`＠HEAD a7b20b7e（39 行，其中旁註 16 行；資料列原樣仍在原處）

```text
    # DEF-200-360：dev_start [1/7] fetch-aware 前沿判定窗口——追加本輪稽核列並依「追加後立即
    # 自我凍結」判例延伸前綴涵蓋該列本身（242→243）。
    ("R166", "c4350df6e968", "cf1dc5dab8c1", "DEF-200-360"),  # round-label-ok
    # DEF-200-362：跨機切換摘要句漏套 _note_unfetched 修復窗口——追加本輪稽核列並依
    # 「追加後立即自我凍結」判例延伸前綴涵蓋該列本身（243→244）。
    ("R167", "cf1dc5dab8c1", "c570fe4d14e3", "DEF-200-362"),  # round-label-ok
    # DEF-200-363：多 CPU 第二十輪計時快取隔輪震盪修復窗口——追加本輪稽核列並依
    # 「追加後立即自我凍結」判例延伸前綴涵蓋該列本身（244→245）。
    ("R168", "c570fe4d14e3", "62ff202f16a2", "DEF-200-363"),  # round-label-ok
    # DEF-200-368：多 CPU 第二十一輪計時快取父鍵回填修復窗口——追加本輪稽核列並依
    # 「追加後立即自我凍結」判例延伸前綴涵蓋該列本身（245→246）。
    ("R169", "62ff202f16a2", "5b81821b1c27", "DEF-200-368"),  # round-label-ok
    # 多 CPU 第二十二輪（W 公式改 logical−ceil(logical/physical)／CAP 18／pytest 站點
    # 普查鎖／TMPDIR flake 修法／pre-push 三 leg 並行鎖）：接鏈錨點＝本輪帳本首列
    # DEF-200-373（W 公式在 SMT 機器低估），由收尾單人窗口於記帳員補登後回填
    # （落地時曾暫以 DEF-200-372 佔位，帳本補登同輪即回填，非跨輪殘留）。
    ("R170", "5b81821b1c27", "c2bb8b8b1774", "DEF-200-373"),  # round-label-ok
    ("R170", "c2bb8b8b1774", "8ce188aa65a5", "DEF-200-373"),  # round-label-ok：同輪自身收斂再延伸
    ("R170", "8ce188aa65a5", "4db111b08259", "DEF-200-373"),  # round-label-ok：同輪收斂第三次延伸
    ("R170", "4db111b08259", "c20fa98dbe84", "DEF-200-373"),  # round-label-ok：同輪收斂第四次延伸
    ("R170", "c20fa98dbe84", "3e871dac4bef", "DEF-200-373"),  # round-label-ok：QA-2 修復批同輪延伸
    ("R170", "3e871dac4bef", "803652092c91", "DEF-200-373"),  # round-label-ok：QA-2 修復批收斂延伸
    ("R170", "803652092c91", "2615e5bdae9a", "DEF-200-373"),  # round-label-ok：QA-2 收斂延伸二
    ("R170", "2615e5bdae9a", "49c85ffd5794", "DEF-200-373"),  # round-label-ok：QA-2 收斂延伸三
    ("R170", "49c85ffd5794", "ee5d6d876535", "DEF-200-373"),  # round-label-ok：QA-2 收斂延伸四
    ("R171", "ee5d6d876535", "f3c556f6b43f", "DEF-200-382"),  # round-label-ok：本輪收尾
    ("R171", "f3c556f6b43f", "ecf46fb27335", "DEF-200-382"),  # round-label-ok：前綴延伸涵蓋全部列
    # R172：console_qa 事故輪收尾單人窗口重釘——修復棒 F 行為鎖新增（三道鎖）使護欄層 round-label-ok
    # 行數重釘，追加後依「追加後立即自我凍結」判例延伸前綴涵蓋全部新列本身（275→279）。
    ("R172", "ecf46fb27335", "efc968920451", "DEF-200-389"),  # round-label-ok
    ("R172", "efc968920451", "0b2e73a520bb", "DEF-200-390"),  # round-label-ok：接鏈列自身漂移延伸
    ("R172", "0b2e73a520bb", "2bf9d536b2bd", "DEF-200-391"),  # round-label-ok：回歸鎖軌新列延伸
    ("R172", "2bf9d536b2bd", "3e14b8e6687d", "DEF-200-393"),  # round-label-ok：修復棒 H 收尾重釘
    ("R172", "3e14b8e6687d", "8fe3e9b2b142", "DEF-200-393"),  # round-label-ok：接鏈列造成二次重釘
    ("R173", "8fe3e9b2b142", "da9eafaf2c1c", "DEF-200-386"),  # round-label-ok
    ("R173", "da9eafaf2c1c", "40175f7507e8", "DEF-200-394"),  # round-label-ok：修復棒覆審
    # 收尾單人窗口重釘（F1 缺陷編號訂正 DEF-200-394／395／396 ＋ F2 WMI 監看 deadline 與量測
    # 解耦 ＋ F3 BFS 補解相對 import／UnicodeDecodeError 兜底），就地更新不開新輪。
    ("R173", "40175f7507e8", "2948983719d7", "DEF-200-394"),  # round-label-ok：自身漂移列接鏈
```

### L10 到期義務兌現沿革旁註（R184～R212；`_REPIN_NET_CAP_DUE_ROUND` 上方）｜來源 `tools/tests/test_adr_xplat001_c1c2_lock.py:3273`＠HEAD a7b20b7e（7 行）

```text
#: R184 兌現 (184, 525)；R186 兌現 524；R188 兌現：cap 降至目標 523，重新武裝 522 round-label-ok
#: R190 兌現：cap 降至目標 522，重新武裝 521 round-label-ok
#: R192 兌現 521；R194 兌現：cap 降至目標 520，重新武裝 519 round-label-ok
#: R196 兌現：cap 降至目標 519，重新武裝 518 round-label-ok
#: R208 兌現：cap 降至目標 518，重新武裝 517 round-label-ok
#: R210 兌現：cap 降至目標 517，重新武裝 516 round-label-ok
#: R212 兌現：cap 降至目標 516，重新武裝 515 round-label-ok
```

### L11 覆蓋率棘輪地板參數化的踩坑經過（`iron_law3_ratchet_problems` docstring）｜來源 `tools/tests/test_doc_loc_baseline_freshness_r60.py:3251`＠HEAD a7b20b7e（3 行）

```text
    第一版正是那樣寫的：把第 5 類危害誠實登記進表之後，`test_taking_a_scanner_away_is_red`
    與 `test_deleting_a_known_hazard_row_is_red` 兩支**注入測試**當場轉紅，也就是說
    「解開棘輪」這個動作被我自己新寫的兩道鎖擋住了——與本判準要治的病同型、同一回合復發。
```

### L12 鎖檔檔頭〈射程〉SA 劃界誠實記錄｜來源 `tools/tests/test_adr_xplat001_c1c2_lock.py:43`＠HEAD a7b20b7e（4 行）

```text
  · SA 劃界誠實記錄：這個繞道面**在被發現時尚未被利用**——本包獨立以家族全檔重驗，落地後
    新列中落入 §4.3.1 者只有 `DEF-101-534` 且 C1／C2 皆已滿足；archive 側落入 §4.3.1 而條件
    未滿足者只有 `DEF-43-011`（archive_01）與 `DEF-101-357`（archive_22），兩者都遠早於 ADR
    落地、屬設計上不追溯範圍 ⇒ 擴面後零假紅。
```

### L13 `_check_ignore` 家族「落地當回合實測」數字（三處 docstring；原處改寫成不帶數字的判準句，另留指標）｜來源 `tools/tests/test_doc_loc_baseline_freshness_r60.py` `:4107`／`:4175`／`:4221`＠HEAD a7b20b7e（共 26 行）

（a）`_run_check_ignore` docstring（`--no-index` 的實測：全庫 tracked 路徑餵入的命中數）｜`tools/tests/test_doc_loc_baseline_freshness_r60.py:4107`（6 行；改寫前整段 docstring／段落原文）

```text
    🔴 **刻意不加 `--no-index`**（這不是省略，是判準的一部分）：預設行為會把 **tracked**
    的路徑一律回報為「未忽略」，而那正是本判準要的語意——tracked ＝ repo 的事實，結構上
    不可能是機器本地生成物。落地當回合實測：把全庫 27,600 條 tracked 路徑餵進去，預設命中
    **0** 條、加上 `--no-index` 命中 **341** 條（多為 `AISDLC_SDD/**/build/reports/**` 這類
    被凍結面 ignore 規則涵蓋、卻確實 tracked 的檔）。也就是說加了那個旗標會讓 341 個**真的
    在 repo 裡**的檔被誤判成第三態 ⇒ 指向它們的錯字從此永遠不會紅，而且是靜默的。
```

（b）`prime_machine_local_cache` docstring（批次 vs 逐條計時；基準誤套的命中數）｜`tools/tests/test_doc_loc_baseline_freshness_r60.py:4175`（15 行；改寫前整段 docstring／段落原文）

```text
    """批次預熱：一次 subprocess 問完整批宣稱，而不是每條各問一次。

    落地當回合實測（macOS）：269 條相異宣稱**逐條**問 = 4.62s，**批次**一次 = 0.50s。
    快取是模組級、平台中立性鎖的 3 次重跑只付一次；但逐條問連第一次都太貴。

    🔴 判準是**合取**，兩款缺一不可（第二款是本函式的自證測試當場逼出來的，不是預想）：
      ① 至少一個解析基準下的候選被 ignore 規則命中，且
      ② **沒有**任何一個候選是 repo 已知路徑（tracked 檔或其祖先目錄）。
    只有 ① 會過寬到危險：宣稱要逐一套上每個解析基準，而錯誤的基準會把一條真實路徑
    前綴成一條**不存在**的路徑，那條路徑很容易命中某個廣義規則。落地當回合實測，
    `AISDLC_SDD/AISDLC_SDD_v0.02/build/reports/…` 在基準 `.` 下 tracked、未被 ignore，
    套上基準 `AutoClaude/` 之後卻命中 `AutoClaude/.gitignore:9: build/` ⇒ 只有 ① 時
    這一族（實測 200+ 條）全被誤判成第三態，指向它們的錯字從此永遠不會紅。
    ② 把它們擋掉的理由是語意的：**tracked ＝ repo 的事實，結構上不可能是機器本地生成物**。
    """
```

（c）`tracked_paths_matching_an_ignore_rule` docstring（`--no-index` 會誤判的那一族數量）｜`tools/tests/test_doc_loc_baseline_freshness_r60.py:4221`（5 行；改寫前整段 docstring／段落原文）

```text
    """**tracked 卻同時命中 ignore 規則**的路徑（＝`--no-index` 會誤判的那一族）。

    這批路徑是本判準最重要的對照組：它們真的在 repo 裡，所以指向它們的錯字必須照樣紅。
    落地當回合實測 341 條（多在 `AISDLC_SDD/**/build/reports/**` 凍結面）。
    """
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
| 第三列的 B+／XPC 探針 launchd job（`AutoSDD_XpcProbe_175600`、`AutoSDD_BplusProbe_20261011T175115Z`、`AutoSDD_BplusProbe_20261011T190135Z`、`AutoSDD_BplusProbe_20261011T202849Z`（run3，第五棒最終碼）；皆拋棄式，主控親跑，〈二-13〉） | 已收：XPC 探針與 B+ 修後一輪各自 `bootout rc=0`（逐字在 `xpcprobe/observed.txt` 與 `run2_observed.txt`）；第四顆 B+ 最終碼一輪（run3）清理 `bootout rc=0`、`leftover=0`（逐字在 `run3_observed.txt`）；B+ 修前一輪的 job 已被 `arm()` 自己殺掉（`launchctl print` rc=113，`run1_observed.txt`），其殘留 plist 已刪（該輪的清理 rc 未留在 `run1_observed.txt`）；痕跡只落 scratchpad（job 的 `environment` 帶 `AUTOSDD_TRACE_DIR`，`launchctl print` 逐字；unload 帳與 bootout 痕跡都在 scratchpad 的 `bplus/traces/`）；原始檔留 scratchpad、不入庫 | 收尾現查：`ls ~/Library/LaunchAgents/` 無四者的 plist、`launchctl list` 無四者 label〔前三者由 Docs 包親跑，第四者由最終零信任複審鏡現查（`~/Library/LaunchAgents/` 無 Bplus／XpcProbe plist、`launchctl list` 無該 label），皆唯讀〕 |
| 真 repo 根殘留 `.env.bak.20261011T055059Z`（54 行；前一列 `--fix` 的備份；gitignored） | **未收**：待掌舵者驗收後手動刪（SD 鏡 P4-6 回報；不是第三列產生） | `ls` 與 `git check-ignore -v`＝`.gitignore:36 .env.*` 命中〔Docs 包親跑〕 |
| 哨兵 `AutoSDD_Sentinel_46b55125-…`（〈三〉暫卸後掛回的本 session 哨兵） | **已不在**：2026-10-12 02:23:53 自我解除（閒置 6 小時的設計行為，非本輪造成；上方各列的「現查在位」是當時快照）。審計檔第 53 列逐字：`ts=2026-10-12T02:23:53+0800 op=deferred-bootout label=AutoSDD_Sentinel_46b55125-… caller=_schtasks_remove<-_sentinel_tick<-main argv=[…session_resume_planner.py, --sentinel-tick, --plan] pid=45069 ppid=1 xpc=AutoSDD_Sentinel_46b55125-…`（哨兵自己的 tick 卸載自己）；該 session 逐字稿最後修改 10/11 20:11:48，到 02:23:53 靜止 6 小時 12 分，對得上 `SENTINEL_IDLE_SECONDS = 6 * 3600` 的閒置自我解除設計〔他包回報：Developer 第三棒第六節〕 | `launchctl list`（唯讀）現為 `com.autoclaude.nightly`、`AutoSDD_Sentinel_c785cd2b-…`、`AutoSDD_Sentinel_0aeb6d2a-…`〔Docs 包親跑〕 |
| 文件修復包（Docs 包，Sonnet）的唯讀查詢 | `gh run view`（二個 run 的 json 與 log，不改任何遠端狀態）、`launchctl list`、`ls ~/Library/LaunchAgents/`、`git show`／`git diff`／`git check-ignore`；落檔只在 scratchpad；未起背景行程、未註冊排程、未 commit | — |

---

## 〈十一〉R212 第二列：mac 真機端到端驗收——到點後尾段三段全通（2026-10-11 21:26～22:03；主控親跑；專用小 session sid `70371a13-b1b5-4fdb-b30c-196638812517`）

**為什麼要跑**：〈二〉-0 的二層結論＝「這條鏈的接縫從未在真後端端到端跑過」；〈三〉只走到「到點探測」。掌舵者 T1「想盡所有辦法完成收斂」⇒ 本列把到點後尾段（spawn→handback 後檢→settle→拆一次性排程／同名不拆→哨兵重掛）在真 launchd 上走通，含 7-C／7-E 修後行為與 C-A 格。設計書＝SA 鏡（Sonnet）的 runbook（scratchpad `e2e_runbook.md`，1506 行，不入庫；主控裁決三處修訂：不寫本機 `.env` 覆寫、③用生產模型 fable、不做 B+）。執行者原擬派 Sonnet，被 auto 分類器以 `[Create Unsafe Agents]` 擋下 ⇒ 主控親跑（分類器對 `launchctl kickstart`／`claude -p`／PATH 前置假 claude 皆未擋）。

**證據措辭（runbook §6.3）**：①②＝「真 launchd × 真 planner／relay_machine／schedule_backend × 假 claude（PATH 前置殼層腳本，0 token）」，①的早醒閘用手改 `reset_at`（構造性）；②的 halt 標記為**手寫**（schema 同生產端、真寫入器 `quota_gate.write_halt_marker`），證明消費端、不證明生產端；**只有③**是真 `claude -p -r`（生產模型 fable，一次）。

### 十一-1 開場基線（Stage 0，全部唯讀）

`launchctl list` 基線＝`AutoSDD_Sentinel_46b55125-…`、`AutoSDD_Sentinel_0aeb6d2a-…`（全程不動，收尾相同）；GC 乾跑兩支皆 `✅ 留`；未讀 handback「（無）」；`--env-doctor` rc=0、`AUTOSDD_MODEL_HELMSMAN = fable〔env.shared〕`；`pmset` 各電源段 `sleep 0`；L0：`quota_meter --refresh rc=0`、六軸 <100%（session 29%／weekly_all 37%）。小 session：`claude -p --model haiku --session-id <SID> --output-format json`，`create rc=0`、`is_error=False`、`total_cost_usd=0.01047896`、usage `input=2 cache_create=51811 cache_read=11456 output=4`。

### 十一-2 跑法①（0 token；手動續航 job＋假 claude＋kickstart）——全 PASS

- 註冊：`--transcript <小 session> --register-schtasks --allow-resume --at '<現在>'`（PATH 前置 `fakebin`）⇒ `register rc=0`；`launchctl print`：`run interval = 900 seconds`、`--resume-tick`、無 calendarinterval、`PATH => …/e2e_run/fakebin:…`（〈五〉#7 的實況）。手改狀態塊 `reset_at=現在+3 分`（`reset_source=endpoint-authoritative`、`relay_problems=[]`）。
- 早醒 kickstart（P1.3，距到點 282 s）痕跡逐字：`21:28:09 woken` → `21:28:09 resume_tick_early due_at=2026-10-11T21:32:50.934937+08:00 rc=0 credential=…[**無** calendar … / state = running] reset_at=2026-10-11T21:30:50.934937+08:00 remaining_seconds=281`；forbid `probed`／`route_chosen`／`relay_snapshot_before`／`resumed` 全 PASS；假 claude 日誌 `No such file`（＝沒 spawn）。
- 到點 kickstart（P1.4，先 `quota_meter --refresh`）痕跡逐字：`21:33:13 woken` → `21:33:13 probed rc=0 kind=none quota_open=true text=endpoint@2026-10-11T21:33:13+08:00: 6 軸皆 <100%（最高 weekly_all=37.0% …） source=endpoint` → `21:33:13 route_chosen strategy=SESSION_RESUME why=逐字稿可用（307,612B ≤ 上限 33,554,432B）` → `21:33:14 relay_snapshot_before lines=10 digest=bdfc3ddd…` → `21:33:35 resumed rc=0 strategy=SESSION_RESUME handback_written=true out=E2E-STUB-OK mode=ok` → `21:33:35 relay_done why= band=free gc_plans=0` → `21:33:35 sentinel_armed task=AutoSDD_Sentinel_<SID> credential=launchd gui/501/…[**無** calendar … / state = not running]` → `21:33:35 relay_rearmed rc=0 unregister_rc=0 next_state=DONE rearmed_inplace=false`。判決器 `P1 verdict rc=0`（10 expect＋13 forbid＋9 assert 全 PASS）。
- 尾段現況：`RES job 消失用了 0s`、`print(RES) rc=113`、plist 已不在、`print(SEN) rc=0`（`run interval = 900`、`--sentinel-tick`）；bootout log `parent-gone waited=1s at 2026-10-11T13:33:36Z`／`bootout rc=0`；**unload 帳逐字**：`ours 21:33:35 op=deferred-bootout label=AutoSDD_SessionResume_<SID> xpc=AutoSDD_SessionResume_<SID>`、`ours 21:33:35 op=bootstrap label=AutoSDD_Sentinel_<SID> xpc=AutoSDD_SessionResume_<SID> … caller=_register_at_expr:767<-register_endurance:780<-_register_and_record:1036`（＝**C-A 格：job 行程內對另一 label `bootstrap` 被 launchd 允許**）。假 claude argv 逐字：`-p -r <SID> "<任務書 prompt>" --permission-mode acceptEdits --settings …/.claude/settings.unattended.json --model fable --add-dir ~/.autosdd/plans ~/.autosdd/handback`，env `AUTOSDD_UNATTENDED=1 CLAUDE_CODE_SUBAGENT_MODEL=sonnet XPC_SERVICE_NAME=AutoSDD_SessionResume_<SID>`，`cwd=` repo 根（`--model fable`＝tick 行程現讀 `env.shared` 層的證據）。成本帳列 `measured=false reason=no-assistant-usage`（假 claude 不寫逐字稿）。額度快取 `measured_at=2026-10-11T21:33:13+08:00`＝tick 同秒 ⇒ 〈五〉#3 launchd 行程自取成立。
- 工具缺陷（非產品）：假 claude 第一版以 `"$MODE；rc=0"` 組字串，launchd 的 bash 3.2 把全形「；」的首位元組併進變數名 ⇒ handback 出現非 UTF-8 位元組（`xxd`：`3d bc9b 7263`）；planner 以 `errors="replace"` 讀仍判 `written`、`relay_done`（產品容錯正確）。②前改 `${MODE}`（與 Dev 包在 `post-merge` 抓到的 `${rc2}` 同型）。

### 十一-3 跑法②（0 token；手寫 halt 標記 → 哨兵 `arm_reset` → calendar 到點 → `probe` → 尾段同名原地重掛）——全 PASS

- `halt_marker.py write <SID> 22`：`reset_at=2026-10-11T21:57:30.339463+08:00`、`fire_at=21:59:30`、預期 descriptor `Month=10-Day=11-Hour=22-Minute=0`；kickstart 哨兵。痕跡逐字：`21:35:30 sentinel_woken` → `21:35:30 sentinel_decided action=arm_reset reason=偵測到自願 halt 標記；觀測 reset=2026-10-11 21:57:30.339463+08:00 尚未到 ⇒ 要求排程器改在那個時刻醒（本次零 token） controller_idle_seconds=493.7` → `21:35:30 sentinel_rearmed action=arm_reset fire_at=2026-10-11T21:59:30.339463+08:00 credential=…[plist 已落地並帶 StartCalendarInterval = Month=10-Day=11-Hour=22-…`。延後重載 bootout log：`parent-gone waited=1s at 2026-10-11T13:35:31Z`／`bootout rc=0`／`bootstrap rc=0 tries=1`／`print rc=0`；`LaunchdBackend._readback` 自報 `calendar = {'Minute': 0, 'Hour': 22, 'Day': 11, 'Month': 10} ｜state = not running ｜interval = 900` → `✅ 相符`。
- F5 格（interval tick 不得重載）：`21:50:31 sentinel_woken` → `sentinel_decided action=arm_reset …` → `sentinel_rearmed … credential=…[StartCalendarInterval = Month=10-Day=11-Hour=22-Minute=0〔launchd 回讀〕…`；bootout log 行數維持 4（未 relaunch）。
- 到點：`22:00:05 sentinel_woken` → `22:00:05 sentinel_decided action=probe reason=偵測到自願 halt 標記；觀測 reset=… 已過 ⇒ 花一次探測確認額度回來了沒 controller_idle_seconds=1968.5` → `22:00:05 woken` → `22:00:05 probed rc=0 kind=none quota_open=true text=endpoint@2026-10-11T21:58:48+08:00: … source=endpoint`（沿用 77 秒前快取，TTL 內）→ `route_chosen SESSION_RESUME` → `relay_snapshot_before` → `22:00:26 resumed rc=0 … handback_written=true out=E2E-STUB-OK mode=ok` → `22:00:26 relay_done` → `22:00:26 sentinel_armed … credential=…[plist 已落地並帶 StartCalendarInterval = (無)（plutil -lint 通過）]` → `22:00:26 relay_rearmed rc=0 unregister_rc=null next_state=DONE rearmed_inplace=true`。判決器 `P2 verdict rc=0`（13 expect＋12 forbid＋6 assert 全 PASS）。尾段後：`print(SEN) rc=0`、`run interval = 900`、無 calendarinterval；bootout log 再四行（`parent-gone waited=1s at 2026-10-11T14:00:27Z` … `print rc=0`）；unload 帳只有兩筆同 label 的 `deferred-bootout`（無別 label、無殭屍）；標記於終態後立即刪除。

### 十一-4 跑法③（真 `claude -p -r`，生產模型 fable，一次）——全 PASS

- P3.1 清掉①②殘留後 `launchctl list` 與基線相同；P3.2 乾淨 PATH 註冊（`fakebin` 次數 0）、`plan_sec3.py`：`✅ 第 3 節已換成 E2E 內容；狀態塊完好：state=armed kind=manual allow_resume=True reset_source=operator-asserted`；P3.4 GC 乾跑兩支 `✅ 留`、`quota_meter --refresh rc=0`、小 session 逐字稿已 2062 秒未寫、`kickstart rc=0`（22:01:38）。
- 痕跡逐字：`22:01:38 woken` → `22:01:38 probed rc=0 kind=none quota_open=true text=endpoint@2026-10-11T22:01:38+08:00: 6 軸皆 <100%（最高 session=38.0% …） source=endpoint`（tick 同秒自取，#3 第 2 筆）→ `22:01:38 route_chosen strategy=SESSION_RESUME` → `22:01:38 relay_snapshot_before lines=10 digest=bdfc3ddd…` → `22:02:00 resumed rc=0 strategy=SESSION_RESUME handback_path=~/.autosdd/handback/<SID>.md handback_written=true err= out=E2E-OK` → `22:02:00 relay_done why= band=free gc_plans=0` → `22:02:00 sentinel_armed task=AutoSDD_Sentinel_<SID> … handled_through=2026-10-11T14:01:59.459Z` → `22:02:00 relay_rearmed rc=0 unregister_rc=0 next_state=DONE rearmed_inplace=false`。判決器 `P3 verdict rc=0`（22 項全 PASS）；假 claude 日誌維持 2 次（③沒叫到假的）。
- handback 由真模型寫成（四節齊、「## 下一步指令」節為 `''`、`handback_verdict = written`）；內容逐字自述：唯讀跑了 `git log --oneline -1`（印出 HEAD 035746ba 的訊息）、「附帶 `; echo "rc=$?"` 的複合形態被 harness 權限層要求核准，無人值守下改以單一指令執行」（登〈五〉#35）。
- 成本：`autosdd_resume_cost.jsonl` 該 SID 列逐字 `{"measured": true, "first_assistant_ts": "2026-10-11T14:01:41.236Z", "model": "claude-fable-5-1", "input_tokens": 2, "cache_creation_input_tokens": 54138, "cache_read_input_tokens": 11456, "pct_before": null, "pct_after": null, …}`（`pct_*` 恆 null＝DEF-200-508 v1 既知限制）；`sum_usage.py` 窗內 `model=claude-fable-5-1 requests=10 input=230 cache_create=174618 cache_read=519230 output=2811 ⇒ 輸入面合計 694,078`（10 個請求、絕大多數是 cache 讀取；對照 R212 首列的 fable 窗首請求 309,407）。
- 尾段現況：`RES job 消失用了 0s`；bootout log `parent-gone waited=1s at 2026-10-11T14:02:01Z`／`bootout rc=0`；unload 帳 `ours 22:02:00 op=deferred-bootout label=<RES> xpc=<RES>`、`ours 22:02:00 op=bootstrap label=<SEN> xpc=<RES>`（C-A 格第 2 筆）；額度快取 `measured_at=2026-10-11T22:01:38+08:00`。

### 十一-5 接縫覆蓋表（S1～S16 依 runbook §2；「真」＝真 launchd 行程內實跑）

| 接縫 | 覆蓋 | 證據 |
|---|---|---|
| S1 `woken` 留痕／S2 早醒閘（`allow_resume=true`）／S3 `probed`（L0 自取與沿用快取兩型）／S4 `route_chosen`／S5 spawn argv 與 env／S6 handback 後檢（7-A）／S7 settle→DONE（7-B：`gc_plans=0`，任務書未被 GC）／S8 一次性 job 自拆（deferred-bootout）與同名不拆（`rearmed_inplace=true`）／S9 哨兵重掛含 C-A（job 內 bootstrap 另一 label）／S10 `launchctl list` 基線差集／S11 halt 標記→`arm_reset`（7-E 消費端）／S12 calendar 寫入＋延後重載＋F5 保留／S13 到點 `probe` 重入 `_resume_tick`／S15 檔案層模型→`--model`（env.shared 層）／S16 成本帳（③ `measured=true`） | 真（①②③） | 十一-2～十一-4 逐字 |
| S14 無人窗口的 hook×INV5（`sentinel_single_owner_deferred`）與 hook 派生的 `--arm-sentinel` 在哨兵承載的續跑窗內重掛 | 未發生，**但在預設路徑上**：續跑窗 SessionStart 清閂鎖後第一次 PostToolUse 即以整份逐字稿評估 `should_arm`（`sentinel_lifecycle_arm.py:93,147,241`），任何有歷史的真實 session 的續跑窗都會走到 `spawn_sentinel`；本列只因用 1 請求小 session 才沒走到。`schedule_backend._defer` 的等待對象是呼叫 arm 的行程自己的 pid，hook 派生者不是 job 主行程；B+（真 launchd、構造情境）後由主控補跑：修前紅（`arm()` 同步 bootout 殺掉在跑的 job）、修後綠 ⇒ **真機量測與修法見〈二-13〉**；真實鏈（真 claude 視窗內 hook 派生）仍未實跑，登〈五〉#38 | 〈二-13〉 |
| settle 的 `no_progress`／`quota_stop`／`relay_exhausted`／`RELAY_NEXT` 真機（登〈五〉#36）、7-E 生產端（真撞線寫標記）、〈五〉#1 睡眠、#2、#5、#6、#8、#10／#11 Windows、#12「靜止守門」分支；S4 `route_chosen` 僅 SESSION_RESUME 一型（FRESH_SESSION_WITH_STATE／PATROL_HANDBACK 兩條路由真機零筆；三次 `route_chosen` 皆為 SESSION_RESUME，逐字稿 307,612B〔他包回報：SA 鏡 P3-4〕） | 未驗（本列不宣稱） | — |

### 十一-6 開了→收了（本列）

| 開了 | 收了／現況 | 憑證 |
|---|---|---|
| haiku 小 session `70371a13-…`（1 請求）＋③的 fable 喚醒窗（10 請求） | 逐字稿**保留**（不刪；394,447 B）；任務書／handback 已刪 | `ls`、Z.1 `rm -f` |
| `AutoSDD_SessionResume_<SID>`（①③各一次） | 各自 deferred-bootout 自拆；Z.1 `--remove-schtasks` rc=0 保險 | `launchctl list` 終驗 |
| `AutoSDD_Sentinel_<SID>`（①尾段掛、②原地重掛、③尾段掛） | Z.1 `--remove-schtasks` rc=0；`~/Library/LaunchAgents/` 無本 SID plist | 同上 |
| `halt_<SID>.json` | ②終態後立即刪；Z.1 再刪一次（存在＝False） | `halt_marker.py remove` |
| 本機 `.env` | **從未改**（主控裁決不覆寫）；開場／收尾 sha256 皆 `6868f80b39824749…`；`--env-doctor` 與基線 diff rc=0 | Z.2 |
| scratchpad `e2e_run/`（含 `evidence/` 21 檔、`fakebin/claude`） | 留在 scratchpad，不入庫、不入全域 PATH | — |
| `~/.autosdd/traces/` 的 launchd／bootout／unload／cost 痕跡、`$TMPDIR` 的 resume log | 刻意保留（證據；cost 帳只增：本 SID 3 列） | `ls` |
| 基線兩支哨兵 | 全程未動；終驗「基線有、現在沒有：[]｜現在多出：[]」 | Z.2 |
