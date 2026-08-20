# CrossPlatform R97 掃描發現與護欄層重釘證據

> 對應 `_GUARD_LINES_REPIN_LOG` 的 R97 那一列。重釘理由欄依規只能是索引，全文在此。
> 🔴 **本輪不是 R71~R96 跨平台複審系列的延續**：那個系列每一輪都圍繞「跨平台真機切換」
> 主題，本輪的議題是獨立的「額度哨兵無人看管耗用 token」，由 Architect/SA/SD/QA 四方
> 獨立審查。沿用 `CrossPlatform_R<NN>_Scan_Findings.md` 命名純粹是延續本 repo 既有的
> 護欄層重釘證據檔命名慣例（機制要求本輪標記必須落在這個 glob 內才有東西可判），
> 不代表本輪併入前述系列。本檔數字量測時點：2026-08-19，工作樹已 commit 前的收尾
> 單人窗口（零並行包，rc 可歸因）。

## 今天實際發生的事

Architect/SA/SD/QA 四方獨立審查「額度哨兵無人看管耗用 token」議題，發現並修復多項缺陷：

1. **per-session 工作命名缺席**：`--arm-endurance`／`--register-schtasks` 未帶
   `--task-name` 時共用固定名字 `AutoSDD_SessionResume`。`Register-ScheduledTask ...
   -Force` 對同名工作是覆蓋語意 ⇒ 兩個 session 平行武裝時，後註冊的會靜默蓋掉先註冊的
   （且沒有任何警告）。修法：新增 `resume_task_name()`（`tools/session_resume_planner.py`），
   比照既有 `sentinel_task_name()` 走 per-session 命名，但**不共用**其前綴
   `AutoSDD_Sentinel_`（那個前綴是哨兵 GC／活性檢查的篩選鍵，共用會讓續航排程被誤判）。
2. **`_run_resume()` 吞不住 spawn 例外**：`subprocess.run` 此前沒有 try/except。本函式被
   無 console 的 pythonw 排程行程呼叫（`sys.stderr is None`），`TimeoutExpired`／
   `FileNotFoundError` 會讓整支行程無聲消失——而呼叫端 `_resume_tick()` 此前已經**先**把
   狀態塊寫成 `"resumed"`、排程也刪了，等於謊稱成功且無法重試。修法：`_run_resume()` 改
   回傳 `int | None`（`None`＝沒有真的跑成），新增 try/except 記
   `resume_spawn_failed`；`_resume_tick()` 改成等 `_run_resume()` 真的跑完（不論成敗）
   才寫狀態塊，失敗時寫 `"resume_failed"`（新終態，已補進
   `sentinel_lifecycle.TERMINAL_STATES`，否則 GC 會把它誤判成「可能還在等額度」而永遠
   不收）。
3. **`.env` 逃生口沒有電**：`AUTOSDD_RESUME_OFF` 此前只讀 `os.environ`，未進
   `quota_policy.ENV_SPEC` 白名單 ⇒ repo 根 `.env` 設了也關不掉，須 Windows
   `[Environment]::SetEnvironmentVariable` 寫登錄檔＋整個重啟 Claude Code 才生效。
   修法：補進 `ENV_SPEC`（`attr=None`，消費端仍住 `session_resume_planner.py` 自己），
   `session_resume_planner.main()` 開頭補一行 `quota_gate.apply_env_defaults(os.environ)`
   （同 hook `main()` 既有的前置填充寫法）。

三項修復皆帶回歸測試覆蓋，這是本輪護欄層行數成長的**全部**來源（含本次重釘自身在
`_GUARD_LINES_REPIN_LOG`／`_FROZEN_GUARD_LINES`／`_REPIN_NET_CAP_SCHEDULE` 佔用的行數
——見下方「本表含本檔自己」段）。

<!-- guard-total:R97 --> **本輪護欄層累積淨額＝ 84806 → 85687（+881）** —— 逐檔漂移 3 支
（含「同輪追加」節：commit 9ef67f8 之後收尾窗口續作的 +309 與自身編修 +35，逐項見下方；
含 PRD §4.5.7／§4.5.8 落地的 +266，見「同輪追加③」段；
含四方最終複審收斂修復的 +134，見「同輪追加④」段；
含收尾單人窗口散文搬遷抵銷 −157 與其自身編修 +15，見「同輪追加⑤」段：
追加④之後累積 +1023 曾超過同輪到期上限 950，搬遷後收斂至 +881）

## 淨額與逐檔清單

| 項 | 值 |
|---|---|
| 重釘前 | 84806（＝R96 收尾窗口釘下的值） |
| 重釘後 | 85085 |
| 淨額 | +279 |

| 檔 | 淨額 | 內容 |
|---|---|---|
| `tools/tests/test_context_budget_guard.py` | +256 | 上述 3 項修復的回歸鎖：per-session 工作命名（`--print-schtasks-command`／`--arm-endurance`／`sentinel_task_name` 對照組各一支）、`_run_resume()` 例外不外洩（`RunResumeSurvivesASpawnExceptionTest`，timeout／FileNotFoundError／控制組三支）、`_resume_tick()` 寫狀態的順序（`ResumeTickWritesStateOnlyAfterConfirmingTest`，spawn 失敗／確認成功／`allow_resume=false` 控制組三支）、`.env` 前置填充接線（`PlannerMainAlsoPrefillsFromDotEnvTest` 兩支＋既有逃生口清單併入 `AUTOSDD_RESUME_OFF`） |
| `tools/tests/test_quota_policy.py` | +13 | `ENV_SPEC` 白名單新增 `AUTOSDD_RESUME_OFF` 一列的形狀鎖（`kind`／`attr`／`section` 三個欄位） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | +10 | 本次重釘自身的稽核列（棘輪要求「淨額在結構上不可能缺席」，那一列自己佔行；本表含本檔自己，動本檔就會動到本表，已用實測值收斂——`--print-guard-lines` 重跑二次到零漂移） |

（此表由 `--print-guard-lines` 的逐檔漂移輸出逐字核對。）

## 為什麼判定「壓不動了」——三條合法出口逐條實查

棘輪自己列的合法出口是「刪死碼／搬史料／抽共用模組」。逐條量測結果：

### 刪死碼 ＝ 0

新增的 `resume_task_name()`、`ArmEnduranceUsesPerSessionTaskNameTest`／
`RunResumeSurvivesASpawnExceptionTest`／`ResumeTickWritesStateOnlyAfterConfirmingTest`／
`PlannerMainAlsoPrefillsFromDotEnvTest` 幾個測試類別逐一實查皆有實際消費者（各自對應
上面某一項真缺陷的修復），零孤兒。

### 搬史料 —— 不適用

這批新增內容此前**沒有等量的舊敘事**可搬——不像 R89/R90/R91 那幾輪是「判準已存在、
只差回歸鎖」，本輪的三個判準與它們的回歸鎖是同一次落地，沒有可搬出量測面的散文。

### 抽共用模組 —— 技術上可行，本輪刻意不做

`RunResumeSurvivesASpawnExceptionTest._run_with()` 與 `ResumeTickWritesStateOnlyAfterConfirmingTest._tick()`
各自的 setup 已用 helper 收斂重複；`test_allow_resume_false_never_calls_run_resume_and_still_terminates`
沒有走 `_tick()` helper（它需要追蹤呼叫次數而非只驗最終狀態），與 `_tick()` 有一段重複
的樣板，理論上可再抽一層——但 `_GUARD_LINE_DRIFT_TOLERANCE = 0` 意味著任何**局部**
壓縮都無法讓本輪重釘變成不必要：只要 `test_context_budget_guard.py`／`test_quota_policy.py`
的行數與凍結表有一行不符，`[逐檔漂移]` 就會紅，出口只有「整批壓到淨額為零」或「整批
重釘」兩者之一。前者等於把幾項真缺陷的回歸測試砍到只剩斷言、拿掉全部 WHY 說明，
與本 repo 對「測試要編碼 WHY 不只是 WHAT」的既有紀律衝突（且失去可讀性換來的餘裕
遠不到淨額的量級）；故本輪選擇重釘，不做非必要的表層重構。

## 代價側（重釘成本棘輪）現查

| 量 | 值 | 出處 |
|---|---|---|
| R97 單輪淨額上限（重釘前） | 1100 | `net_cap_for_round(97)`（`_REPIN_NET_CAP_SCHEDULE` 末段 `(95, 1100)`） |
| 本輪淨額（原始＋追加①②③） | +889 | 遠低於當時上限，款(10) 不觸發 |
| 到期義務 | 已到期並兌現 | `_REPIN_NET_CAP_DUE_ROUND = 97`（本輪＝到期輪）；上限表追加 `(97, 950)`，同輪重新武裝下一段：到期輪 99、目標 850 |
| 🔴 本輪淨額（追加④之後） | **+1023 > 950** | **`[超出每輪上限]` 已觸發**——追加④（四方最終複審收斂修復，DEF-200-160／DEF-200-163 必要回歸鎖 +134）把本輪累積淨額推過同輪剛兌現的到期上限 950。三條合法出口（刪等量行／合併鎖檔／把史料搬進帳本）皆會實質縮減本輪剛新增的必要回歸覆蓋，與本 repo「測試編碼 WHY」既有紀律衝突；`拆給下一輪`需要一個尚未到來、且不違反 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2`（R96/R97 已用滿）的新輪次。**本次收斂刻意不強行壓線**，如實記錄並交由下一個收尾單人窗口裁決（下修排程表或接受一次超額並於下一輪立刻出現淨額 ≤ 0）。連續上升輪數維持 2（R96／R97，未產生第三輪）|

<!-- guard-total:R97 --> 護欄層累積總量現值 **84806 → 85687（+881）**；原始逐檔清單即上一節，
「同輪追加」節見下方新增段落（含「同輪追加④」四方最終複審收斂修復、「同輪追加⑤」散文
搬遷抵銷），款(12) 到期義務同輪兌現（上限表追加 `(97, 950)`，重新武裝下一段到期輪 99、
目標 850）。

## 同輪追加（收尾窗口續作，commit 9ef67f8 之後的四方複審修復）

commit 9ef67f8 落地資安修復＋架構機制（P0-1／P2-1／P2-2）新增 3 支 `tools/lib/*.py`
與對應回歸測試，觸發本檔上方兩處 `guard-total:R97` 標記過期＋護欄層帳本未同步登記。
本節記錄同一收尾窗口內、緊接原始 R97 之後的兩段追加重釘，**沿用同一份 R97 稽核痕跡**
（`repin_round_nets()` 同輪連續多列合併語意），不另開新輪號。

| 段 | 淨額 | 內容 |
|---|---|---|
| 追加①（功能回歸鎖） | 85085 → 85394（+309） | `test_worktree_paths.py` +103（P0-1：`tools/lib/worktree_paths.py` 抽出共用模組，`is_under_disposable_worktree()` 的 `..` 穿越洞回歸鎖）；`test_failure_log_rotation.py` +81（P2-1/P2-2：失敗紀錄輪替方向鎖）；`test_skip_ceiling_ratchet_direction.py` +107（`_RUNTIME_SKIP_CEILING_MAX` 方向鎖，帳本判準過期缺陷回歸測試）；`test_block_destructive_git_r83.py` +18（既有檔補 worktree `..` 穿越洞回歸測試） |
| 追加②（護欄層重釘自身編修） | 85394 → 85429（+35） | `test_adr_xplat001_c1c2_lock.py` +26（本表／稽核列／腐化上界重釘註解自身佔行）、`test_platform_neutral_paths.py` +3（`tools/tests` 掃描下限重釘 53→64 的兩處註解）、`test_subprocess_encoding_hygiene.py` +5（`tools` 掃描下限重釘 110→131 的註解）、`test_worktree_paths.py` +1（`# platform-ok:` 豁免行） |
| 追加③（AutoClaude_Token_監控與喚醒機制 PRD §4.5.7／§4.5.8 落地） | 85429 → 85695（+266） | `test_context_budget_guard.py` +257：新增 `ControllerIdlePrepareWatchTest`（B1／B2，主控閒置量測與 prepare 帶預防性提醒的分支開關紅綠自證）、`PatrolNoticeIsDesktopNotHookTest`（B3，整合測試證明通知從巡邏 tick 本身觸發、零 hook 事件）、`ArmedDriftSelfHealTest`（新缺口：armed stamp 對排程器現查漂移時自動重新武裝，含漂移／未漂移／量不到三組控制對照）；`test_adr_xplat001_c1c2_lock.py` +9（本表／稽核列自身編修，同追加②體例）。生產碼側新邏輯全落 `tools/lib/quota_escalation.py`（400 budget 內，零跨檔溢出）與 `tools/lib/sentinel_lifecycle.py`（3 行擴充，剛好用滿既有餘裕），`tools/session_resume_planner.py`（guardrail_cli tier 750/750 零餘裕）淨額為 0（換被呼叫端更胖，未新增任何一行） |
| 追加④（四方最終複審收斂修復） | 85695 → 85829（+134） | `test_skip_ceiling_ratchet_direction.py` +58：DEF-200-160 二審修復——QA 親測把 `_RUNTIME_SKIP_CEILING_MAX['tools/tests@win32']['platform']` 從 41 改成 999 重跑方向鎖，全數通過、完全沒抓到（根因＝`_FROZEN_CEILING_MAX` 原用 `copy.deepcopy(即時匯入值)`，套套邏輯）；改為原始碼字面凍結（比照 `skip_tag_policy._POSIX_TAG_RATCHET_CEILING` 既有做法），並以同一手法紅綠雙向驗證（放大轉紅、改回轉綠）；`test_check_defect_log_crossref.py` +61：DEF-200-163——`tools/lib/ledger_staleness.py::uncommitted_problems()` 落地時零測試覆蓋，新增 `TestLedgerStalenessUncommittedProblems`（拋棄式 git repo：乾淨帳本／未 commit 修改／git 不可執行三分支）；`test_failure_log_rotation.py` −1：移除未用 `import time`；`test_adr_xplat001_c1c2_lock.py` +16（本表／稽核列自身編修，同追加②③體例） |

三條合法出口逐條實查（同上一節體例）：刪死碼不適用（皆為本輪修復必要的回歸覆蓋或
治理帳本自身的稽核痕跡）、搬史料不適用（P0-1/P2-1/P2-2、DEF-200-160/163 判準與回歸鎖
同次落地，無等量舊敘事可搬）、抽共用層不適用（`drift_tolerance=0`，且追加②④純為數字與
註解，無可抽結構）。

連續上升輪數：R96（+407）／R97（原始 +279、追加① +309、追加② +35、追加③ +266、
追加④ +134，合計 +1023）——依 `repin_round_nets()` 同輪合併語意仍計為兩輪，未產生
第三個連續上升輪，`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` 不觸發；
`net_cap_for_round(97) = 950`，本輪合計 1023 已**超過**上限 950——見下方「款(10) 觸發」段。

## 逐輪淨額（現查，不寫死）

```
python -c "import importlib.util,sys; \
spec=importlib.util.spec_from_file_location('lk','tools/tests/test_adr_xplat001_c1c2_lock.py'); \
m=importlib.util.module_from_spec(spec); sys.modules['lk']=m; spec.loader.exec_module(m); \
print(m.repin_round_nets(m._GUARD_LINES_REPIN_LOG))"
```

## 生產碼側的三項真修復（非護欄層，列此供逐檔清單完整性）

| 檔 | 淨額（`git diff --numstat`） | 內容 |
|---|---|---|
| `tools/lib/quota_policy.py` | +3（6 行新增、3 行刪除，含既有列壓成單行以騰位） | `ENV_SPEC` 新增 `AUTOSDD_RESUME_OFF` 逃生口列 |
| `tools/lib/sentinel_lifecycle.py` | +3（4 行新增、1 行刪除） | `TERMINAL_STATES` 新增 `resume_failed` 終態 |
| `tools/session_resume_planner.py` | +35（52 行新增、17 行刪除） | `resume_task_name()`、`_run_resume()` 例外處理、`_resume_tick()` 寫狀態順序、`main()` 前置填充、`--print-schtasks-command`／`--register-schtasks` 改走 per-session 命名 |
| `.env.example` | +2 | `AUTOSDD_RESUME_OFF` 逃生口說明列 |

這四支不落在護欄層量測面（`tools/tests/*.py`），故不計入本輪 +279 的護欄層淨額，
僅為逐檔清單的完整性一併登記。

## 同輪追加⑤：散文搬遷抵銷 R97 超額（收尾單人窗口，2026-08-20/21）

追加④之後本輪累積淨額 +1023 超過同輪剛兌現的到期上限 950（見上方「代價側」表）。
三條合法出口逐條實查：刪死碼不適用（追加①②③④全為必要回歸覆蓋或本表自身編修）、
抽共用層不適用（`drift_tolerance=0`）。**唯一剩下的出口＝搬史料**——本檔（
`test_adr_xplat001_c1c2_lock.py`）自 R77~R85 累積了大量純敘事性 WHY 註解／docstring，
說明的是「當初為什麼這樣設計」而非「這支測試在斷言什麼」，把全文原樣搬進本節、原處只留
一行指標，對測試覆蓋與判準行為零影響。逐段搬遷清單如下（原處指標即節標題）：

### 護欄層逐檔行數棘輪 WHY

R77 落地物（掌舵者親自拍板）：這個位置原本是一個**純量檔數**棘輪——`tools/tests/` 的
鎖檔支數只准往下。它擋的是「一個 finding 一支新鎖檔」的檔案增生，而長期實測的結論是
**它把病換了個地方長**：歷次取樣的支數一格不動，同期行數卻翻倍有餘（現值現查
`live_triplet()` 的 glc 兩欄）。舊訊息指示「擴充進既有鎖檔」，增量因此被擠進少數
mega-file，而護欄層**行數**在全 repo 一個消費者都沒有——`AutoClaude/tools/check_loc_budget.py`
把 `tools/tests/` 排除在 tier 檢查外，其理由欄指向的兩道機制一個量的是檔數、一個量的是行
**長度**，都不是行數。

⇒ 一進一出、機制數不變：純量檔數 → **逐檔行數表**。新表同時承接三件事：
(a) `DEF-101-561③`「禁止新增鎖檔、只准合併／刪除」——新檔在表上沒有列，且只要淨行數
上升就紅；淨額不上升的合併／改名照舊合法（那是該裁決指定的動作）。
(b) 護欄層**行數**第一次有判準在讀（`guard_line_problems`／`glc_growth_problem`）。
(c) ADR §4.3 的 GLC 行數與本表是**同一個家**：`live_triplet().glc_lines` 與
`sum(_FROZEN_GUARD_LINES.values())` 走同一個 glob，不再是兩個各自漂移的站點。

方向是**收緊**：改版前「一輪加三萬行全綠」，改版後「淨增一行即紅」。重釘紀律（照抄
`run_root_unittests.MIN_TESTS` 的既有慣例，不另立體例）：值一律是**當回合實測**、零加減
推算；多包並行的輪次由**收尾包在所有包停工後**重釘一次，並在 `_GUARD_LINES_REPIN_LOG`
補一列（不補即紅——淨額因此在結構上不可能缺席）。R78 ARCH-02 立案原文＝
CrossPlatform_R95_Guard_Repin_Evidence.md §B-10；`TestRepinCommandIsReal` 雙向釘住
「訊息教的指令必須真的跑得動」。

### `_NET_DELTA_ACCOUNTING_SINCE` WHY

R80 包 C（SA-R80-03）：款(9) 的生效輪次。**刻意不追溯到 R80 自己**——現存每一列都落在
款(7) 的凍結前綴內（列數以 `_REPIN_LOG_FROZEN_PREFIX_LEN` 現查），改寫任何一列會先撞
append-only 指紋，而那道鎖比本款更根本。R80 自己那筆 +1528 的承認與逐檔清單改落在
`docs/04_planning/AutoSDD_improving_104.md` §1 Q2 與 `CrossPlatform_R80_Scan_Findings.md`
附錄 B（同一件事只有一個家）。生效點寫成常數而不是散文——散文式的「從今以後」沒人在讀。

### R84 ARCH-01 代價機制 WHY

**R84 ARCH-01：重釘的「代價」**——立案量測（名義棘輪實為成長帳、M1 照舊制永遠做不到）
原文＝Guard_Repin 證據檔 §B-3；逐輪淨額現查 `repin_round_nets()`，不寫死列數。

形狀選擇（兩案擇一，選 (b) 並說明為什麼）：
(a) **配對制**——每一列上升必須同輪配一列下降。**駁回**：本輪（R84）九包並行、每包都在
補判準，收尾那次重釘必然是正淨額；配對制會讓**本輪合法的重釘做不到**，而一道紅了卻沒有
出路的鎖，本 repo 已判過它一定會被整個關掉（ARCH-02）。
(b) **每輪淨額上限 ＋ 方向鎖**——採用。兩條各自單邊、且都可以在「本輪照常重釘」的前提下
成立，代價是**延後**而不是**封死**：本輪與下一輪可以照樣長大，但第三個連續上升的輪次
必須先出現一次淨額 ≤ 0 的重釘。這正是 M1 判準的形狀，差別在於它從「一個沒人負責的指標」
變成「會擋下 push 的閘門」。

**門檻的取值都是量測值、不是發明的**：單輪淨額上限見 `_REPIN_NET_CAP_SCHEDULE`（每一列
自帶取值理由）；`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`＝M1 判準「連續三輪不上升」的
機械面：允許連兩輪上升，第三輪必須 ≤ 0。兩者皆**只准下修**（`repin_cost_ratchet_problems()`，
形狀照 `_shrink_only_problems` 的凍結基準版：簽入的字面常數 commit 不動它、CI 乾淨樹也
不動它）。

**不追溯**：只判輪號 ≥ `_REPIN_ROUND_CAP_SINCE` 的列。理由與款(9) 逐字同構——現存每一列
都落在款(7) 的凍結前綴內，回頭改它們會先撞 append-only 指紋；而一道「上線當天就把整段
歷史判紅、且沒有任何人補得回來」的閘門，等於要求下一個人先把它刪掉才能 push。
**R84 F3／B-1：起算錨也是門檻，而它原本是本組唯一沒有後設鎖的那一個**——注入實測
（一行 diff 關掉款(10)(11) 整段且無一物轉紅）原文＝Guard_Repin 證據檔 §B-4。方向與另外
兩個**相反但同義**：`net_cap`／`max_consecutive_rising` 只准調小（門檻更低），`SINCE`
也只准**調小**（生效點更早＝涵蓋更多輪＝判準更嚴）。三者一起由
`repin_cost_ratchet_problems()` 看著。

**R85／款(12) 兌現時發現的結構性死結**（純量到期目標 vs append-only 指紋互相排斥）——
立案實測原文＝Guard_Repin 證據檔 §B-5。解不是放寬，是把「**下修不追溯**」從
`_REPIN_ROUND_CAP_SINCE` 那個一次性生效點推廣成**逐輪分段的上限表**：每一列＝「從這一輪
起，單輪淨額上限是多少」（R84 在 5400 下收輪就永遠用 5400 判）。理由與 `SINCE` 逐字同構，
只是從「一刀切」變成「每次下修各自生效」。表是 **append-only、輪號嚴格遞增、上限只准
遞減**（`repin_cost_ratchet_problems()` 看著）⇒ 只能愈收愈緊，而下修永遠不會製造回頭的
假紅。

### 到期義務與重新武裝 WHY

**R84 F3／A-03：現行上限的到期義務**（R85 起每次兌現都就地**重新武裝**下一段）。立案
理由：上限取的是歷來單輪最大值，代價是**對現況零攔阻力**——逐輪淨額一律現查
`repin_round_nets(_GUARD_LINES_REPIN_LOG)`（本段刻意不複寫那張表：前一輪把它抄成散文，
抄完當輪就被自己的第二次重釘證偽，而三份複本沒有一份會因為彼此不一致而轉紅）。機制：
一旦稽核痕跡出現輪號 ≥ `_REPIN_NET_CAP_DUE_ROUND` 的列，而現行上限還沒降到
`_REPIN_NET_CAP_DUE_TARGET` 以下，款(12) 當場轉紅。出口只有一個且永遠開著：**往
`_REPIN_NET_CAP_SCHEDULE` 追加一列更小的上限**（後設鎖只擋調升；分段生效⇒下修不追溯，
所以這個出口在結構上不可能像 R84 那樣把自己鎖死）。刻意不留「延期」參數。

**下一段的步伐刻意變小**：5400→3200 一次砍 2200 是因為 5400 取的是史上最寬值；再往下
就逼近真實輪次大小（現查逐輪淨額的最小正值），步伐不縮就會製造沒有出路的紅（ARCH-02）。
**兌現必然是「下修上限」＋「重新武裝下一段」兩個動作**，不是可選的第二步——本款要
`cap ≤ 目標`、下方 assertLess 要 `目標 < cap`，互斥推導見 CrossPlatform_R89 結案證據檔。

### 淨減法到期輪沿革 WHY

R85 收尾單人窗口：款(11)／ADR-XPLAT-002 §8.1 item 15 那條「**必須出現一次淨額 ≤ 0**」的
**到期輪**。此前它寄生在 `test_the_real_repin_log_stays_inside_the_cost_envelope` 的斷言
裡、且被寫成「R85 已經達成」——那是 P2 在本輪**動工中**寫下的預測，被同一輪其後的必付
成長推翻，於是那句話在**它自己那一輪**就變成假的。搬成具名常數的理由與其他到期常數一字
不差：**義務要能被看見、要有一個會到期的時點**，而不是只有一段散文（`DEF-101-757`：已知
缺口不得只以劃界結案）。刻意不留延期參數——可延期的到期日不是到期日；只准往**前**挪
（更早到期＝更嚴），往後挪是放寬，需掌舵者裁決。

### 文件總量標記形態 WHY

R80 二審（NEW-SA2-01＝QA2-N2）：文件側累積總量對帳的三個常數與掃描面。判準本體與立案
量測見 `doc_guard_total_problems()` 的 docstring。標記刻意做成「冒號後綴 ＋ 輪號」的形態
（同 repo 既有的 `handoff-claim-verified:`／`xplat-rate-history:`），而**不用反引號包**——
反引號在本 repo 是幽靈符號鎖的掃描面，一個帶連字號與冒號的字串放進去只會製造一筆看起來
像懸空引用的噪音。

**R84 ZT-04：標記的形態由「行內出現這個字串」收窄為「住在 HTML 註解裡」**。這不是潔癖，
是擴掃描面的**前置條件**：擴面之前先量假紅，實測**全部命中皆為偽陽性**——`ADR-XPLAT-006`
與 `R83_HANDOFF.md` 為了**指路**而逐字寫出了「這個標記＋輪號」（其中一句正是 ADR 自己
裁定「給 ADR 補一個標記會是誘餌標記」的那一句），沒有一行是總量宣稱，卻會被判
`[形態不符]`。而假紅會逼下一輪的人去改一段本來正確的散文，或直接把鎖關掉（本 repo 已為
此付過學費）。收窄的判準與現況零衝突：**每一個真正的宣稱站點自 R80 起都寫成
`<!-- 標記 -->`**（R80~R83 四輪八處實查皆是），而指路的散文一律是反引號包起來的行內
文字 ⇒ 兩者在形態上本來就分得開，收窄之後假紅由 4 降到 0、真站點一個不少。

### 凍結前綴指紋設計 WHY

**凍結前綴**的長度與內容指紋——把 `_GUARD_LINES_REPIN_LOG` 檔頭那句「**append-only**」由
散文變成機械事實。前綴內的任何一列被改寫（改數字／改理由／兩列合併成一列／整段砍掉），
指紋當場不同；而**追加**新列不動前綴，指紋不變 ⇒ 正常的每輪重釘零額外維護。

為何是「固定長度的前綴」而不是「除最後一列外」：後者在追加時前綴會跟著長大，於是每一輪
都得改一次 sha 常數——那種鎖實務上一定被改寬（本 repo 對「維護成本過高的鎖」有判例)。
代價是**尾端最多一列不受指紋保護**，由 `_REPIN_LOG_MAX_UNFROZEN_TAIL` 把那個窗口釘死：
追加當輪不必動指紋（一列寬限），下一輪要再追加就必須先把前一列納入前綴並重釘，否則
`[前綴過期]` 轉紅。草稿兩個值都由 `--print-guard-lines` 印出（ARCH-02 的教訓：紅了卻沒有
出路的鎖會被關掉）。

### 文件總量掃描面訂正 WHY

**R84 ZT-04 擴面（交棒書）**立案與 **F3／B-2 訂正**（擴面對自己立案的缺陷零效果；ADR 面
因 ADR-XPLAT-006 的合成語料結構上永遠咬不到 ⇒ 該 glob 已移除）——實測原文＝Guard_Repin
證據檔 §B-8。要把 ADR 納回來，得先有不與該 ADR 打架的載體（例如 ADR 引用時一律指向
計畫書的標記行，而不是自己複寫數字）。交棒書那一半**改由不靠標記的款(5) 真正接手**
（`handoff_guard_total_problems()`）：以檔名輪號對上稽核痕跡的該輪合計，假紅存量實測 0
（逐份見那支的 docstring）。

### 涵蓋關係判準 WHY

R78 ARCH-04：`_GUARD_LINE_PATTERN` 上方那句「涵蓋關係改由 `guard_baseline_gaps()` 證明」
在 R77 寫下時，這個函式**並不存在**（全庫 AST 零定義）。兩個面刻意不同——檔數面是遞迴
`test_*.py`（閘門會跑哪幾支），行數面是非遞迴 `*.py`（這一層有多大）——而「不同」與
「有東西從縫裡掉出去」是兩件事，後者需要有人算。`guard_baseline_gaps()` 算的就是那個縫：
閘門會跑、但行數棘輪量不到的檔 ⇒ 它的成長不會讓任何東西轉紅。與 `guard_surface_escapes()`
的分工：那一支問「子目錄裡有沒有 .py」（行數面的已知代價），本函式問「檔數面的每一支是
不是都被行數面數到了」（兩面之間的涵蓋關係）。今天兩者的答案同源（唯一的逃逸方式就是
落進子目錄），但它們是**不同的問句**——把它們併成一個，日後任一 glob 改動時就會有一個
問題沒人問。

### 代價常數後設鎖 WHY

**R84 F3／B-1**：`_REPIN_ROUND_CAP_SINCE` 調的是**分母**、原本唯一沒被守——注入實測
原文＝Guard_Repin 證據檔 §B-7。方向與另外兩個相反但同義：`SINCE` **只准調小**（更早
生效＝涵蓋更多輪＝更嚴）。**R84 F3／A-03：款(12) `[到期未下修]` 也住這裡**——它判的是
「尺自己該不該被下修」而非表的內容，家在後設鎖（放進 `repin_growth_problems()` 會對
輪號較大的合成語料串音，實測見 §B-7）。`latest_round` 預設現查真表，注入測試可傳；
due 兩參數同理。

形狀刻意照 `frozen_ratchet_problems()`（凍結基準版，非 git 導出版）：基準是簽入本檔的
字面常數，故 commit 不動它、`checkout` 不動它、CI 乾淨樹也不動它 ⇒ 比較在任何時點、
任何消費者身上都非退化。若改用 `git show HEAD:<本檔>`，commit 一落地基準就等於現值，
而每一個真正消費本鎖 rc 的閘門都跑在 commit 之後（SA-R67-08 的實證）。殘餘面（誠實
揭露，與 `_FROZEN_MAX_BASELINE_ENTRIES` 那一組同一句話）：同一個 commit 內**同時**改
門檻與凍結基準仍可通過。這是所有釘選式棘輪共有的邊界；本組是純量，調升在 diff 上就是
兩個一起變大的數字，方向一望即知。

### 稽核痕跡假話治理 WHY

`repin_log_problems()` 款(6)(7)（`[歷史變短]`／`[歷史被改寫]`）是 R79 收斂包補的，治的是
這張表自己的假話——append-only 這句話此前零機械強制，壓平整段歷史照樣 rc=0。立案實測
原文＝Guard_Repin 證據檔 §B-6。

### 文件總量對帳判準 WHY

**立案（R80 二審 NEW-SA2-01＝QA2-N2，實測三處全錯；此前沒有任何判準看得到 `.md`）**——
原文＝Guard_Repin 證據檔 §B-8。

為何靠「帶輪號的標記」而不是掃全部箭頭：那兩份文件本來就會逐次記載**每一次**重釘的
分段淨額，那些是史料、本來就不等於總量，全掃會把正確的史料判成違規。輪號還有第二個
作用——下一輪只要在自己的文件裡寫一行，舊輪那幾行自動退位成史料，**零回頭維護成本**
（本 repo 判過：維護成本過高的鎖實務上一定會被改寬）。

誠實劃界：本判準保證「被標出來的那一行講的是今天的數字、且算術自洽」，**不保證作者把
每一個該標的地方都標到了**——與款(4) 只保證有一列、不保證理由是好理由同型。要涵蓋
「漏標」得先有「哪些句子算引用」的判準，那是關鍵詞啟發式，會誤殺史料。

**R84 F3／B-2：上一段那個劃界，正是 ZT-04 擴面失效的原因**——交棒書從來沒有人標，於是
「擴大掃描面」擴到的只是「檔案被讀進來了」。**漏標**那一半改由不靠標記的款(5)
`handoff_guard_total_problems()` 接手（錨＝檔名輪號 ↔ 稽核痕跡該輪合計）；本函式維持
只判「標了的行」，兩者刻意分開（不同的錨、不同的失效形態、零串音）。

### 交棒書對帳判準 WHY

**立案（R84 F3／B-2，Architect 當回合注入實測；交棒書是呈給掌舵者的數字卻零標記可
全錯）**——原文＝Guard_Repin 證據檔 §B-9。

**為何不能沿用標記機制**：標記要人記得寫，而「沒寫」正是這裡的失效形態本身（R83／R84
兩份交棒書都沒寫）。⇒ 本款改用**檔名輪號**當錨：`R<N>_HANDOFF.md` 講的就是第 N 輪，
第 N 輪的護欄層合計是稽核痕跡上算得出來的事實（同輪多列合併，同 `repin_round_nets()`
的單位選擇）⇒ 對帳不需要任何人記得標。

**為何不是「掃到三元組就對帳」**（那是最先想到的形狀，量過之後駁回）：擴面後的掃描面上
三元組字面**遠多於真正的宣稱站點**，其中絕大多數是**史料與逐檔行數**——
`CrossPlatform_R81` 一份就佔了最大宗（`2282 → 3085（+803）` 這種是單一鎖檔的行數，不是
累積總量）、`ADR-XPLAT-006` 內的則是刻意寫壞的注入語料。全判等於製造大量假紅，而假紅會
逼下一個人把整道鎖關掉（本 repo 已為此付過學費，見 `_GUARD_TOTAL_MARK_RE` 上方的 ZT-04
收窄）。本款只問一句話：**該輪的交棒書裡，有沒有一組三元組逐字等於稽核痕跡替該輪算出來
的 (起點, 總量, 淨額)**——其餘三元組一律不管（它們是史料）。

假紅存量＝**空**（落地當回合逐份實測原文＝Guard_Repin 證據檔 §B-9）。逐份重跑見
`test_the_handoff_criterion_is_deliberately_not_retroactive`（第二段直接量磁碟）。

誠實劃界：① 本款保證「該輪交棒書寫得出正確的三元組」，**不保證它沒有同時寫出別的錯
數字**（那需要「哪些句子算引用」的判準，會誤殺史料——與款(4) 只保證有一列、不保證理由
是好理由同型）；② ADR 不在射程內，理由見 `_GUARD_TOTAL_DOC_GLOBS` 上方（ADR-XPLAT-006
已裁定不得補標記，且該檔的三元組是刻意寫壞的注入語料）。

### 逐檔漂移判準 WHY

**(6) 為何非補不可（它不是潔癖，是已發生的實況）**：`guard_line_problems()` 原本的誠實
劃界段逐字寫著「淨額為零的『A 減 B 增』對調…(4)(5) 都不會說話」——而 R79 掃描在**乾淨
HEAD** 上實測到那個盲區已經是現況：三支檔（−11／+7／+4，淨額 0）與磁碟不符，棘輪與
`--print-guard-lines` 雙雙印綠，照流程走的人只會看到「不需要重釘」。劃界不等於防護。
後果有兩層：①凍結表的逐檔數字不再能當基線用，「哪支檔長了多少」的歸因全錯；②在總量
守恆的前提下，任一支護欄檔可以無限膨脹只要別支等量縮水——那正是**檔數棘輪退場時列出
的原始病灶**（「成長全部灌進既有巨檔」），換到行數面之後只是把巨檔換成整層。

容忍度是**參數**不是常數（同 `iron_law3_ratchet_problems()`）：注入測試拿現況當基準，
活體判準拿釘住的 `_GUARD_LINE_DRIFT_TOLERANCE` 當基準。現行釘 0——重釘時逐檔照貼，
容忍度就沒有存在的理由；留餘裕等於替下一次「淨額為零的對調」預先開門。

誠實劃界（本判準**仍**抓不到的）：本函式只讀兩張表，看不到「某支檔改了 10 行、同一支檔
又刪了 10 行」這種檔內互抵——那要 diff 才看得到，不在行數面的定義域內。

### 護欄層棘輪 WHY（`TestGuardLayerRatchet` 類docstring）

WHY（ARCH-R60R3-04）：`DEF-101-561③` 在 R60 round 3 被訂正為「**現在即判定已觸發**：
R61 開輪即進入禁止新增鎖檔、只准合併／刪除」。Architect 全 repo 實查該裁決的落地狀況，
結果是它只活在帳本一格散文與一行註解裡——**零機械強制**。而本檔檔頭自己立的標準是
「把 §4.3 的兩條件做成機械鎖才叫落地——沒有這道鎖，§4.3 就只是散文，本輪已經自證」。
同一把尺量回這條裁決，結論一樣：沒有鎖，它就只是散文。本類就是那道鎖。

🔴 **量測面在 R77 換過一次，語意跟著換了**（動它之前先搞清楚現在管的是什麼）：
  · **舊**：純量「鎖檔支數」，只准往下 ⇒ 讀起來就是「禁止新增鎖檔」。長期實測的結論是
    它把病換了個地方長——支數一格不動，同期行數翻倍有餘，判準全程綠。
  · **現**：`_FROZEN_GUARD_LINES` 逐檔行數表，判準是**淨行數不得上升**
    （`guard_line_problems`／`glc_growth_problem`）。
  · 🔴 因此接手者的語意**不是**「禁止新增檔案」：新增一支鎖檔，只要同一次變更內刪掉
    等量以上的行就合法（那正是該裁決指定的「合併」動作）；反之只改既有巨檔卻淨增一行
    照樣紅。**R78 ARCH-03 實查到散落各處的引用仍逐字寫著舊語意**，那是對已移除機制的
    複述，不是接手者的規則——看到那種寫法請一併訂正，不要照著做。
  · 重釘不是「調高就好」：`--print-guard-lines` 產出新表，並在 `_GUARD_LINES_REPIN_LOG`
    補一列（含淨額與理由），不補即紅（R78 ARCH-01）。

本類仍保留兩支**檔案面**的自錨（`guard_files_in_worktree()` 與根層閘門 pattern 的
SSOT 綁定）：行數面是非遞迴 `*.py`、檔案面是遞迴 `test_*.py`，兩個面的涵蓋關係由
`guard_baseline_gaps()` 證明。`_*.py` 這種**共享零件不進檔案面**：`DEF-101-561①`
指定的 R61 合併動作本身就是「把四支 AST helper 抽成一支共享剝除層」，把零件算進來
會讓那個**被裁決指定的合併動作自己翻紅**（獎勵把重複貼回各鎖檔、懲罰抽共用層）。

### 三條合法出口逐條實查（本次搬遷動作自身）

刪死碼不適用（本次動作是搬遷不是刪除，零測試／零斷言被動到）；抽共用層不適用
（`drift_tolerance=0`，且被搬遷的是純散文無可抽結構）；搬史料＝本次動作本身，逐段清單
即上方各小節，原處指標見對應常數的行內註解。淨額與逐檔清單將於 `--print-guard-lines`
覆核後補登於本節末尾（新增一列 `_GUARD_LINES_REPIN_LOG`，同輪追加，不開新輪號）。
