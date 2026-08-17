# CrossPlatform R95 — 喚醒降級選路（FRESH_SESSION_WITH_STATE）證據檔

> 本檔＝R95／Pkg-D 的證據與史料檔（PRD §4.5.4／§8-10）。持有面：
> `tools/session_resume_planner.py`、`tools/tests/test_context_budget_guard.py`、本檔。
> 🔴 本檔屬 `CrossPlatform_*.md` 具名治理文件慣例；`check_defect_log_crossref.py` 的
> `_GOVERNANCE_DOCS` 登記**不在本包持有面**（鐵律七：並行包禁動別包／公共鎖檔），
> 與同輪 `CrossPlatform_R95_GovWrite_Evidence.md`／`CrossPlatform_R95_Pace_Actuator_Evidence.md`
> 相同，登記留收尾單人窗口一次補三列。

## 1. 立案與設計

**缺口**：`tools/session_resume_planner.py` 此前只有 SESSION_RESUME 一條喚醒路
（`claude -p -r <sessionId>`）。逐字稿不可用（缺檔／為空／超上限）時，`-r` 指令直接
失敗且**沒有降級**——五段續航流程（巡邏→偵測→重排→探測→續跑）全部觸發成功、
稽核痕跡齊備，最後一步空轉，正是本 repo 反覆判過的「機制蓋好沒接電」同型。

**修法**：選路收成一支純函式 `choose_resume_route(claude, session_id, transcript,
plan_path, max_bytes=None)`，回 `{strategy, reason, argv}`：

| 輸入態 | strategy | 指令形態 |
|---|---|---|
| 逐字稿存在、非空、位元組數 ≤ 上限、session id 非空 | `SESSION_RESUME` | `claude -p -r <sessionId> "<讀任務書照第 3 節做…>" --add-dir <任務書目錄>` |
| 逐字稿缺檔／為空／超上限／session id 缺席 | `FRESH_SESSION_WITH_STATE` | `claude -p "按磁碟任務書繼續：讀 <任務書絕對路徑>…"`（**不帶 `-r`**；state 由磁碟任務書交棒——〈可重啟點四條件〉第 2 條本來就要求它落盤） |
| 任務書（plan）不存在 | `REFUSE`（argv=None） | 呼叫端 fail-loud：rc=1、stderr 出聲、痕跡記 REFUSE，**不得靜默派空 prompt**（R59 事故的形狀） |

- **方向鎖（單向降級）**：逐字稿可用時**必須**回 SESSION_RESUME——反向（可用卻開
  FRESH）＝把可用的 session context 丟掉，是資訊損失；FRESH 的 argv 不得帶 `-r`。
  兩面皆有具名測試釘住（見 §3）。
- **接線點＝`_run_resume` 單站**：`--resume-tick` 的 resume 分支與哨兵探測通過那一支
  都收斂到它（該函式抽出的既有理由就是「只有一個站點的東西才有辦法一次證完」），
  故選路只接這一站即涵蓋兩條喚醒鏈。任務書路徑取 `state["plan_path"]`；逐字稿取
  `state["transcript"]`，鍵缺席（R95 之前武裝的舊狀態塊）時以 `resolve_transcript(session_id)`
  現查，查不到即降級、不崩潰。
- **痕跡**：`route_chosen` 事件記 `strategy` 與 `why`（降級是靜默失效的高風險點，
  「走了哪條路」必須事後可稽核）；`resumed` 事件同步帶 `strategy`。
- **護欄不因降級減損**：重驗＋禁 commit/push 句收在 `_RESUME_RULES` 常數，兩條路共用
  （FRESH 少帶護欄句＝比 RESUME 少一層約束，而漏帶是靜默的）；`AUTOSDD_UNATTENDED=1`
  注入與 cwd／`--add-dir`／NO_WINDOW 全數沿用既有 spawn 段，一字未動。

（R95 修復包批補搬：原 `ResumeRouteDegradesOneWayTest` 類 docstring 立案敘事，一字未刪——）

> 立案缺口：此前喚醒只有 `claude -p -r <sessionId>` 一條路，逐字稿不可用（缺檔／
> 為空／超上限）時指令直接失敗且**沒有降級**。三個判準：
>   ① 逐字稿可用時**必須** SESSION_RESUME——降級只准 RESUME→FRESH 單向，反向就是
>      把可用的 session context 丟掉（資訊損失）；
>   ② 不可用時走 FRESH_SESSION_WITH_STATE，argv **不得帶 `-r`**，state 由磁碟任務書
>      交棒（prompt 必須指向它）；
>   ③ 任務書缺席＝REFUSE（argv=None）——兩條路的 prompt 都指向任務書，它缺席時派出
>      去的是空承諾（R59 事故的形狀），不得靜默派空 prompt。

## 2. 逐字稿大小上限：預設值是量出來的

`AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES`（`os.environ` 直讀；**刻意不進** `quota_policy`
的 ENV_SPEC——那是並行別包持有面，註冊留收尾窗口）。預設 `32 * 1024 * 1024`（32MiB）。

本機 `~/.claude/projects/` 全量實測（2026-08-16，量測腳本＝rglob `*.jsonl` 取
`stat().st_size`），輸出逐字：

```
n=1108
min=375  p50=402,949  p90=827,698  p95=1,148,166  p99=3,151,800  max=6,048,262
mean=506,870
cap   8MB: 0/1108 超限 (0.0%)
cap  16MB: 0/1108 超限 (0.0%)
cap  32MB: 0/1108 超限 (0.0%)
cap  64MB: 0/1108 超限 (0.0%)
cap 128MB: 0/1108 超限 (0.0%)
cap 256MB: 0/1108 超限 (0.0%)
```

選值理由：觀測 max＝6.0MB、p99＝3.1MB ⇒ 32MiB ≈ 觀測 max 的 5 倍，**只攔病態值**。
假降級的代價是把可用的 session context 丟掉（方向鎖要防的那件事），故判準刻意窄
（共通紀律：擋到讓人無法工作的守衛會被整個關掉）。要收緊／放寬走 ENV，不改常數。

## 3. 測試證據（當回合真跑，逐字）

新增／修改的測試類（`ResumeRouteDegradesOneWayTest` 8 條＋`RunResumeConsumesTheRouteTest`
3 條＋既有 `ResumeSpawnCarriesTheUnattendedSignalTest` 7 條前置補齊後重跑）：

```
Ran 18 tests in 0.013s

OK
rc=0
```

整支 `tools/tests/test_context_budget_guard.py` 模組：

```
Ran 408 tests in 19.334s
OK (skipped=8)
rc=0
```

根層全套 `python tools/run_root_unittests.py`：

```
Ran 3435 tests in 460.922s
FAILED (failures=18, skipped=44)
rc=1
```

> 🔴 m6 訂正（R95 修復包，2026-08-17）：上段末行原抄錄為 `rc=0`，是**轉錄失誤**——
> runner 對 FAILED 必回非零（`tools/run_root_unittests.py` 的 rc 由 `wasSuccessful()`
> 收斂，失敗即 `return 1`，讀檔即證），且違反「測試結果逐字貼不重組」紀律。就地訂正
> 為 `rc=1`（依 runner 的確定性收斂路徑；原始終端輸出未保存，故此值是推定的機械必然
> 值而非重新實測——照實寫）。

該 18 筆失敗**皆非本包引入**（並行波既有狀態，逐筆歸因）：

- `test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet` 3 筆：護欄層行數棘輪
  84406→84874（+468），成長最多者＝`test_quota_policy.py +168`（Pkg-C 持有；
  m6 指針：後經收尾實測訂正為 **+154**，見 Guard_Repin §A）、
  `test_context_budget_guard.py +164`（**本包，淨額如實回報**）、
  `test_block_destructive_git_r83.py +136`（別包持有）。棘輪重釘依該鎖自己的裁決文
  「重釘一律由收尾包在所有包停工後做一次」。
- `test_check_defect_log_crossref` 15 筆：①`CrossPlatform_R95_GovWrite_Evidence.md`／
  `CrossPlatform_R95_Pace_Actuator_Evidence.md`（皆別包產物）未登記
  `_GOVERNANCE_DOCS` 觸發早退，其餘檢查未執行的連鎖紅——本檔落地後為同一張收尾
  待辦的第三列（見檔頭）；②`TestR71`：全波各包程式碼標 R95 而帳本當前輪＝R94
  （實測 29 處命中，本包 planner 的 R95 註解亦屬同波），帳本 R95 列由收尾窗口補上
  後即綠。此兩因在本包動工前即存在（block_destructive_git.py 等命中皆別包檔），
  非本包引入、也非本包可修（帳本與 crossref 常數皆持有面外）。

## 4. LOC 對價帳（R89 手法）

`tools/session_resume_planner.py` 在 `root_tools` 的 `guardrail_cli` tier 上限 750，
動工前實測 counted LOC＝750（headroom 0）。本包新增選路常數＋純函式＋接線約 36
counted 行，對價如下（**輸出逐位元不變**的實體行合併＋史料搬遷，門檻一格未調）：

| 手法 | 位置 | counted 淨額 |
|---|---|---|
| 字串續行合併（輸出不變） | `check_report`／`schtasks_command`／`_arm_endurance` 五處 print／`_arm_sentinel` print／`main()` fail-loud print／`tick_plan` 四處 return | −40 |
| 史料搬遷（§L-1／§L-2，一字未刪） | 檔頭 R79 解禁段＋哨兵堆積段 → 本檔 | counted ±0（純註解），raw −22 |
| 新增（常數＋選路函式＋接線） | `choose_resume_route` 一帶 | +36（counted）|

完工實測：counted LOC **749**（≤750）、raw 1419→1421（+2）；
`check_loc_budget --json` 的 `root_tools_violations = []`（逐字見交件 loc_check 欄）。

## L-1. 搬遷史料（原 `session_resume_planner.py` 檔頭，R95 搬入，一字未刪）

```
# 🔴 「只印不執行」這條限制的依據已被實測推翻，故本輪解除（照實寫）
# ------------------------------------------------------------------
# R78 版的本段逐字寫「註冊 S4U 任務需要提權，session 內做不到也驗不了 ⇒ 本檔的處置是
# **只印指令**」。兩個前提在 R79 各被實測一次：
#   · 「session 內 spawn `claude` 會死結」（`DEF-101-089`，`CLAUDECODE=1`）——當回合
#     真跑，兩組對照皆 `rc=0`：繼承 `CLAUDECODE=1` 者 4.0s、剝掉者 3.6s。**沒有死結。**
#     🔴 射程：該實測用的是 `claude -p` 非互動 spawn。樹上另有一批用 wexpect pty 的測試
#     仍以舊前提 skip；那條路徑 R79 收斂輪**已複驗**（上一版此處寫「沒有複驗過」，已過期），
#     結論是**在巢狀 session 內仍掛住**：`PtyWrapper.start()` 三次都沒回返（180/180/45s）、
#     `claude.exe` 從未被啟動、剝除 `CLAUDECODE` 的對照組行為相同。
#     ⇒ 反證**只對 subprocess 這一路成立**，不遞移到 pty 路。
#     逐字量測見 docs/06_quality/CrossPlatform_R79_Debt_Audit.md 的 `## DEF-101-913` 節。
#   · 「註冊排程一定要提權」——`Register-ScheduledTask` 註冊**當前使用者**的工作不需要
#     提權（需要提權的是 S4U／`-User SYSTEM` 那種）。
# 於是「排程重啟」這條路第一次變成**可以在 session 內端到端驗證**的東西，而不是一段
# 只能相信的指令字串。取證規則本身一個字都沒放寬：`--register-schtasks` 會在同一段輸出
# 裡自動跑 `Get-ScheduledTask | Get-ScheduledTaskInfo` 並把 `NextRunTime` 印出來，
# **印不出來就回非零 rc**——「我下了指令」不等於「它真的排進去了」。
```

## L-2. 搬遷史料（原 `sentinel_task_name` 上方註解，R95 搬入，一字未刪）

```
#
# 🔴 R79 已知設計問題（**本輪不修**，交棒下一輪）：per-session ＋ SessionStart **無條件**
# 武裝＝每一次 headless `claude -p` 呼叫都會生出一支自己的哨兵（每個 headless session
# 有自己的 session id）。本輪實測：跑兩次探針之後機器上有 3 支 `AutoSDD_Sentinel_*`。
# 6 小時的 `SENTINEL_IDLE_SECONDS` 會讓它們自己下班，所以不會無限長；但 Auto Pilot
# 開啟後短時間內的堆積是真的——續跑那一跑本身也是一個 headless session，它也會武裝
# 一支。可能的處置（都需要先決定語意，故不在本輪射程）：同一個 repo 只留一支（以
# repo 路徑而非 session id 命名，武裝時 `-Force` 覆蓋）；或 SessionStart 先數一次現有
# 哨兵、超過 N 支就不再武裝；或對 headless session（`claude -p`）整個不武裝——但最後
# 這條會把「續跑那一跑自己撞線」的續航能力一起關掉，是取捨不是純改善。
```

## 5. 收尾單人窗口待辦（本包無權動、如實列出）

1. `tools/check_defect_log_crossref.py` 的 `_GOVERNANCE_DOCS` 補登本檔
   （與另兩份 R95 證據檔同一批）。
2. `tools/tests/test_adr_xplat001_c1c2_lock.py` 護欄層行數棘輪重釘：本包淨額＝
   `test_context_budget_guard.py +164`、`tools/session_resume_planner.py` raw +2。
   ——R95 收尾窗口批 §L-3 搬遷後更新：`test_context_budget_guard.py` 7064→6897
   （−167），對凍結基準 6900 為 **−3**；重釘時以磁碟現值為準
   （`--print-guard-lines` 照貼），上一行的 +164 已被本批搬遷抵銷。
3. `AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES` 進 `quota_policy` ENV_SPEC 註冊
   （本包依任務書刻意 `os.environ` 直讀，不碰 Pkg-C 持有面）。

## L-3. 護欄層史料搬遷（R95 收尾窗口批：自 test_context_budget_guard.py 逐字外移）

> 體例同 §L-1／§L-2（R89 搬遷紀律）：只搬「史料」（事故立案、裁決沿革、實測數字與
> 逐字輸出），判準本身與判準的理由留在原檔；搬出原文一字不動，原檔各留 1~2 行壓縮版
> ＋「原文＝Resume 證據檔 §L-3.n」指標。來源＝`tools/tests/test_context_budget_guard.py`。

### L-3.1 `_run_nested_suite` 立案（R84／SA84-01，pytest vs unittest 執行順序）

>     🔴 立案（R84／SA84-01，複審實測）：`pytest tools/tests/test_context_budget_guard.py`
>     rc=1、唯一失敗者是 `SentinelArmingCriterionTest
>     ::test_this_module_never_reaches_the_real_scheduler`（`AssertionError: None != '1'`），
>     而 `python -m unittest tools.tests.test_context_budget_guard` 對同一份原始碼 rc=0。
>     兩者差別**只有執行順序**：unittest 依類別名字母序（`S` 早於 `T`）、pytest 依定義順序
>     （巢狀 runner 那一支在前）。機制：巢狀 suite 收尾會走 `_handleModuleTearDown` →
>     `unittest.case.doModuleCleanups()`，把 `setUpModule` 註冊的還原動作提前執行掉。
>     最小重現（本輪實跑，逐字）：同模組三個類別、中間那個起巢狀 runner ⇒
>     `PIN-AFTER-NESTED: None`、`PIN-IN-LATER-CLASS: None`。
>     ⇒ 官方閘門（`run_root_unittests.py`＝unittest 載具）當時是綠的，但那是**字母序的運氣**；
>     真正的損失是 C3-P4c 要防的「同行程測試在開發者機器上註冊真 launchd job」在
>     `TraceIsolationTest` 之後全程失效——掌舵者機器上那支 22:40 移除、22:58 又重生的
>     `AutoSDD_Sentinel_s` 正是這個形狀。
>     `addModuleCleanup` 也一併補掛回去：堆疊已被沖乾淨，不補的話真正的 module teardown
>     不會還原，pin 會漏到同一個行程裡的後續測試模組。

### L-3.2 `_hook_invocations` 兩段 R80 立案（launcher 轉呼叫＋第二個家）

>     立案（R80 當回合實測）：並行的另一包把註冊面改成經 `_hook_launcher.py` 轉呼叫，
>     於是實體腳本路徑從 `command` 搬到了 `args` ⇒ 只看 `command` 的判準當場回空清單，
>     兩支既有接線鎖同時紅。**那是判準太脆，不是接線壞了**——被鎖的性質是「這支 hook
>     有沒有被註冊在這個事件上」，而它與「是誰去啟動它」無關。這裡把兩處重複的讀法
>     收成一份，順帶讓它對未來再換一次啟動器免疫。
>
>     🔴 R80 收尾：上一段的判斷完全正確，但那份讀法**同一輪內長出了第二個家**——
>     另一包為同一件事建了唯一真相源 `tools/lib/hook_wiring.py`（該包實測：repo 內原有的
>     「只讀 command 找腳本名」解析器會在 exec form 下**全部**掃出空集合而恆綠。🔴 R80
>     二審 `NEW-ARCH-R80B-07`：此處原本寫死支數，而同一個數字在三個家有兩個值——支數是
>     量測值不是常數，現查指令見 `hook_wiring.py` 檔頭）。
>     兩個家各自正確、卻只有一個會被下一次形態變更改到，那正是本 repo 的頭號病。

### L-3.3 `_isolated_env`／R84 C3-P4c 立案（launchctl 孤兒哨兵）

>     # 立案是實測到的：本機 `launchctl list` 長期掛著一支 `AutoSDD_Sentinel_s`，session id
>     # 就是 `s`——那是 `QuotaGateIsWiredToTheBurnPathTest` 的 fixture 檔名（`s.jsonl`）。
>     # 它每 15 分鐘醒來一次，在 Windows 上就是掌舵者看到的那個黑框；而它的 session
>     # 早就不存在，所以永遠不會有人來收它。

### L-3.4 `_run_hook3` R91 沿革（此前只回 (rc, stderr) ⇒ 結構上不可能轉紅）

>     🔴 R91 為什麼 **stdout 必須進得了斷言**：`.claude/hooks/context_budget_guard.py` 自
>     R91 起把 75% 提示同時送上 stdout 的 `hookSpecificOutput`（exit 0 下唯一進得了模型
>     context 的通道）。此前 `_run_hook()` 只回 `(rc, stderr)` ⇒ 全檔沒有任何一條看得到
>     stdout，於是「低水位誤發一份 JSON」在結構上不可能轉紅——而那正是本輪新增出來的
>     失效面。

### L-3.5 `test_the_resumed_run_lands_in_the_repo_not_system32` R80 P0 實測逐字

>         """🔴 R80 P0。沒有這一格時，續跑那一跑的 cwd 繼承排程行程＝`C:\\Windows\\System32`，
>         而 Claude Code 用 cwd 決定「本 session 允許的工作目錄」⇒ 那一跑**結構上做不了任何
>         事**。實測逐字（今天 01:55 那一跑自己的回報）：`Read` 任務書 → 權限未授予；
>         `Get-Content` 同一份 → 「本 session 允許的工作目錄只有 C:\\WINDOWS\\system32」。
>
>         五段流程（巡邏→偵測→重排→探測→續跑）全部觸發成功、稽核痕跡齊備，最後一步空轉
>         ——所以這一條斷言的是**能不能做事**，不是「有沒有被叫起來」。

### L-3.6 `_CONSOLE_FREE_FLOOR` R82／HELM-02 立案（quota_meter.py 漏掉）

> #: 掃描面檔數下限。R82／HELM-02 上修：射程由「planner ＋ hooks ＋ 一支具名的
> #: `quota_escalation`」擴成「planner ＋ hooks ＋ `tools/lib/` 全部 `quota_*.py`／
> #: `sentinel_*.py`」。🔴 立案不是預防性的，是**實測漏掉了一支**：`tools/lib/quota_meter.py`
> #: 的 `subprocess.run` 一直沒有 `creationflags`，而它對本鎖完全隱形——因為射程是一份
> #: 手寫清單，而清單只列了當時想到的那一支。改成 glob 之後，同族新檔自動進來。

### L-3.7 `test_the_duplicated_no_window_expression_still_equals_the_ssot` R83／PD 沿革

>         🔴 **`sentinel_lifecycle` 已於 R83／PD 由兩份名冊移除**（不是鎖被放寬）：該檔那兩個
>         常數的唯一消費者（`_powershell`）在 A-01 收斂時整支刪掉 ⇒ 常數成了零消費者的死碼，
>         本輪連同它們一起刪除（該檔留有墓碑段記載沿革與判準）。名冊是**複製品清單**，複製品
>         不存在了就必須離開清單——留著會 `AttributeError`，而那是假紅不是牙。仍在守的兩端
>         （`quota_meter`／`console_spawn_watch`）逐一具名，射程縮小時會指名道姓地紅。

### L-3.8 R80-SD-01 反向靜默自毀（`<synthetic>` 誤判機制與後果）

>     # `<synthetic>` 是 harness 對**所有**合成訊息的共同標記，不是額度事件的指紋——
>     # `API Error` 與 `[Request interrupted by user]` 都長這樣。第一版把任何沒有後續成功
>     # 回應的合成記錄都登記成候選 ⇒ 一個以中斷／API 錯誤收尾的 session（常態，不是例外）
>     # 會被判成未處理撞線 → `sentinel_decide` 解不出 reset → `escalate` → **哨兵自我刪除**。
>     # 舊病是「該醒不醒」，新病是「不該死卻自我刪除」，兩者同樣靜默：痕跡只多一行
>     # `sentinel_escalate`，`Get-ScheduledTask` 查不到那支工作，與正常下班外觀相同。
>     # 註解裡那個 0.0% 假陽性是**橫斷面**（單一時點 257 支檔），量不到這個**縱向**情境。

### L-3.9 R80 時區框架（act 在 Linux 容器抓到的紅，實跑逐字）

> # ════════════════════ R80：時區框架（act 在 Linux 容器抓到、Windows 本機看不見的兩個紅）
> # 缺陷本體：`resets 9am` 是一個**牆上時刻**，舊實作拿**機器的**本地時區去解它，而
> # `now` 由呼叫端給 ⇒ 同一份語料有兩個框架。act 實跑逐字：
> #   FAIL: SentinelDecisionTest.test_a_pending_hit_whose_reset_already_passed_spends_one_probe
> #         AssertionError: 'arm_reset' != 'probe'
> # 容器是 UTC、本機是 UTC+8，「reset 過了沒」整個翻面。修法是把框架收成**一個**，
> # 且優先採用**訊息自報**的時區（`… (Asia/Taipei)`）——那是資料自己回答的，與機器無關。

### L-3.10 `_quota_cache` R82 schema 實測教訓（16 條測試同時紅）

>     🔴 schema **跟著 meter 走、不寫死字面**（R82 接線階段的實測教訓）：此處原本是一份
>     寫死的 `"autosdd.quota/1"` 複本，meter 升版到 `/2` 之後每一份合成快取都被判
>     schema-mismatch ⇒ 額度軸整條靜默退化成「量不到」⇒ 16 條測試同時紅，而**紅的原因
>     與被測的性質無關**。同一份契約字面第二個家的代價，這一次是在測試側現形。

### L-3.11 `test_unmeasurable_is_its_own_band_and_is_capped_not_unlimited` R81 版與探針數字

>         R81 版逐字斷言 `fanout_cap(None) is None`＝**不設限**，理由是「斷網時自動降併發
>         會讓『網路壞了』與『額度滿了』外觀相同」。那個理由只成立到 R81 複審探針量出它的
>         淨效果為止：**快取過期 600s ＋ 額度 99% 時，42 次 `Agent` 派發放行 42、擋下 0**。

### L-3.12 `test_the_two_thresholds_are_tunable_because_the_helm_asked_for_that` R81 版沿革

>         本條的 R81 版是另一個名字（**刻意不逐字反引號寫出**：那支 test 已不存在，指名它
>         會被幽靈符號鎖判紅，而 grep 到的人會以為它還在——同 `check_loc_budget.py` 對已死
>         符號名的既有處置），逐字註解「掌舵者訴求 b 的兩個數字是規格，**不是可調參數**」
>         並把 80／95 釘死。
>         訴求 6c 逐字要求「有參數設定 .env.example」⇒ 這是**一道鎖在守一個與需求矛盾的
>         宣稱**（本 repo 判過的形態，比沒有鎖更難看見）。裁決見合議規格 D-6（裁 SA）。

### L-3.13 `test_a_bucket_with_a_real_value_outside_limits_can_win` R82 改判準沿革

>         🔴 R82 改判準（`meter.worst()` 已刪除，見該檔的墓碑）：舊版問「挑出來的那一桶
>         是不是它」，而「挑桶」這個動作本身就是本輪要拆掉的缺陷。現在問的是**取數層有沒有
>         把它交出去**——判讀層對全部軸求值，所以「它在不在 axes 裡」才是取數層的責任邊界。

### L-3.14 R83／F2-① 立案實測（17 列 no-cache、二分定位逐字、兩層嚴重性）

> # 🔴 立案是實測，不是衛生偏好。本輪在 mac 真機的 `%TMPDIR%` 撈到
> # `autosdd_quota_degraded.jsonl` 有 **17 列** `source=no-cache`，逐列時間戳與
> # `mkdtemp(prefix="degraded-")`／`"quota-gate-"` 這些**測試自己**的暫存目錄一一對上；
> # 二分定位（逐類別跑、量該檔行數增減）得到逐字證據：
> #     QuotaUnmeasurableFanoutTest: trace +1  新 stamp=1
> #     其餘四個 quota 類別:          trace +0  新 stamp=0
> # 成因：上面那兩個類別把 `quota_cache_path`／`fanout_ledger_path`／`quota_latch_path`
> # 換成沙箱，卻**沒有換** `quota_trace_path`／`degraded_stamp_path` ⇒ `note_degraded()`
> # 寫的是真的那兩個檔。
> #
> # 為什麼這比「檔案變髒」嚴重得多，兩層：
> #   ① 那個 jsonl **就是** SD-B2 要的那個觀測面——人要靠它回答「額度軸是不是正在靜默地
> #      不節流」。17/17 是假的，於是真事件在裡面讀不出來（訊噪比被測試自己毀掉）。
> #   ② 更硬的一層：`note_degraded()` 出聲帶 per-source TTL 閂鎖，而測試**消耗掉了真的那個
> #      閂鎖**。跑完測試後的 180 秒內，production 真的降級時 `note_degraded()` 回 `""`
> #      ——一聲都不出。「不節流 ≠ 不出聲」這條不變量在那個視窗裡是假的，而它完全靜默。
> #      這正是任務書 F2-① 觀察到的症狀（no-cache ⇒ 量不到 ⇒ 不節流且無聲），只是成因
> #      不是它推測的 `TMPDIR` 分裂（該推測已被三組實測否證，見交付報告）。

### L-3.15 `QuotaUnmeasurableFanoutTest` 複審探針實測缺口

>     複審探針實測的缺口（跑 `quota_gate()` 真碼、沙箱 cache/ledger）：快取過期 600s／
>     額度 99% ⇒ 42 次 `Agent` 派發**放行 42、擋下 0**；完全沒有快取亦然。成因是唯一的
>     刷新呼叫點就在這條「已經量不到」的支線上、且 fire-and-forget 不等它 ⇒ 本次仍判
>     「量不到」⇒ 放行。而「過期」是**常態**不是罕見：哨兵巡邏一次都不刷快取、TTL 只有
>     180 秒 ⇒ 任何 ≥3 分鐘的非扇出工作之後，下一波扇出整批通過。

### L-3.16 `test_a_dead_endpoint_with_no_evidence_falls_back_to_the_degraded_cap` R81 版斷言與探針數字

>         R81 版逐字斷言「真的量不到、又沒有任何撞線證據 ⇒ **仍然放行**」（`_burst() == 0`
>         ＝ 42 次全過），理由是「斷網時自動降併發會讓『網路壞了』與『額度真的滿了』外觀
>         完全相同」。

>         R81 複審探針量到的淨效果就是本條在守的東西反了：過期 600s／額度 99% 時 42 次
>         派發放行 42。

### L-3.17 R81 收斂：Pool.map vs 壁鐘 barrier 的量法差異（實測數字）

> # 這不是講究，是量出來的判準差異：
> #   · `Pool.map` 的 worker 是**依序**被啟動的（本機實測彼此錯開數十毫秒）⇒「同時碰同
> #     一個檔」那件事根本沒發生。SD 對 `claim_refresh_slot` 兩種量法：Pool.map 得到
> #     CLAIM=1（看起來完全正確），壁鐘 barrier 得到 **CLAIM=16**（設計意圖 1）。
> #     同一支程式、兩個相反的結論——量法選錯就是一條恆綠的鎖。
> #   · 本檔原本的 `FanoutLedgerTest` 是單行程序列呼叫 ⇒ 對這兩個缺陷零鑑別力，而它全綠。

### L-3.18 `FanoutLedgerConcurrencyTest` 四組 barrier 實測數字

>     落地前以同一支 barrier 探針實測（8 行程 × 40 筆＝320）：
>       · 舊實作 `path.open("a")`             lines=221 **LOST=99（30.9%）**
>       · `os.open` 帶 `os.O_APPEND` ＋單次 `os.write`   lines=281 **LOST=39（12.2%）**
>         （SD 建議的修法本身治不好——Windows 的 CRT 把那個旗標實作成使用者態的 seek＋write）
>       · `msvcrt.locking(LK_LOCK)`           N=8 時 0，**N=20 時 10 個行程直接死在
>         `OSError: Resource deadlock avoided`**（它只重試 10×1 秒）⇒ 鎖自己變成故障源
>       · 現行（目錄項＋`O_CREAT|O_EXCL`）     8×40／20×40／42×10 三組皆 **LOST=0 torn=0**

### L-3.19 `WorkflowFanoutIsOutOfReachTest` 當回合三點量測

>     本包當回合實測（`~/.claude/projects/d--CursorProject-AISDCL-Agent/`）：
>       · `Workflow` 的 tool_result **47/47** 是「Workflow launched in background」
>         ⇒ 那次呼叫在內部 agent 生出來之前就結束，用 Pre/Post 配對算 in-flight 恆讀 ≈0；
>       · `%TEMP%` 的 19 支 `autosdd_sentinel_boot_*.log` **沒有一支**的 sid 長得像 subagent
>         ⇒ SessionStart 對 workflow 內部 agent 一次都沒觸發過；
>       · 但 subagent 逐字稿裡 `PreToolUse:` 命中 136 次 ⇒ 那些 agent **自己的**工具呼叫會跑本 hook。

### L-3.20 `_cred_kwargs` R83 立案（真的去讀使用者 login Keychain）

>     這不只是衛生問題——R83 修這一組之前，`darwin` 主機上這組測試每跑
>     一次就真的 `security find-generic-password` 讀一次使用者的 login Keychain，於是
>     「401 這條臂綠不綠」取決於這台機器有沒有登入過 Claude Code（本機實測：Keychain
>     rc=0、有真 token ⇒ 401 那條臂僥倖是綠的；換一台沒登入的 mac 就會紅在
>     `no-credentials-darwin`）。判準去讀一個會隨機器變的外部狀態，本身就是缺陷。

### L-3.21 `QuotaDegradationReachesTheModelTest` L4-02 立案

>     立案（讀碼＋本輪實跑）：`note_degraded()` 寫 stderr，而它唯一的 production 呼叫鏈
>     （`quota_gate()` 的 L4 分支）在那之後 `return 0`＝放行 ⇒ 依本 repo 自己記載的行為
>     契約（`context_budget_guard.py` 模組 docstring 逐字：「PostToolUse 的 exit 2 會把
>     stderr 回饋給模型」），那段話一個字都到不了模型面前。而 L4 **必須**不節流（斷網
>     與「額度真的滿了」不可混為一談）⇒ 不能改用 exit 2 去換能見度。

### L-3.22 `test_garbage_from_the_keychain_never_becomes_a_token` R83 第三種形態沿革

>         🔴 R83 補第三種形態（輪號經獨立驗證者訂正：原文署名 R82，而該形態在 R82 收輪
>         commit 內 grep「第三種形態」命中 **0**——被守的 `_run_security` 是 R82 的，
>         這一條斷言不是）：`_run_security` 帶 `errors="replace"`，所以**非 UTF-8
>         位元組會降解成一串 U+FFFD**，而那串東西不含任何空白、長度也遠超過 20
>         ⇒ 舊判準（只看「夠長且不含空白」）照樣放行（實測 `True`）。守衛與它自己上一段
>         註解宣稱要防的東西之間差一個字，而後果正是那句話寫的「永遠 401 的假 token」：
>         額度軸從此恆為 `unmeasurable`，80%／95% 兩道門一次都到不了。

### L-3.23 `_returns_with_dominators` R84／SD-09 射程訂正沿革

>         🔴 R84／SD-09 訂正**射程**：舊版靠 `isinstance(sub, ast.stmt)` 決定要不要往下走，
>         而 `ast.ExceptHandler`／`ast.match_case` **不是** `ast.stmt` ⇒ 寫在 `except:`／
>         `case:` 裡的 `return` 連進分母都沒有進，判準對它完全隱形（掃描器照跑、照綠、
>         照回報命中數，只是那條路徑從來不在分母裡——本 repo 判過的「失明是靜默的」）。
>         `ast.TryStar`／`ast.AsyncFor`／`ast.AsyncWith` 是同一個洞的另一半：型別根本不在
>         舊的 isinstance 名單上 ⇒ 落到最後那一格「直線陳述式」，return 被吞掉、而且體內
>         的呼叫還會被當成後續 return 的支配者（往**放行**的方向錯）。
>         今日 `_sentinel_tick`／`_abort_and_unregister` 實測 0 個 try/except ⇒ 存量命中 0，
>         但那是運氣不是設計：任何人補一段 `try/except` 進去就整條失明。

### L-3.24 `test_this_module_never_reaches_the_real_scheduler` 本機實測證據

>         本機實測留下的證據：`launchctl list` 長期掛著一支 `AutoSDD_Sentinel_s`
>         （session id 就是本模組某個 fixture 的檔名 `s.jsonl`），每 15 分鐘醒一次、
>         session 早就不存在 ⇒ 永遠沒有人來收。Windows 上它就是那個黑框。

### L-3.25 R82／C2 的病（複審鏡實測：.env 裡的逃生口靜默失效）

> # 病（複審鏡實測）：`.env.example` 逐字宣稱「生效路徑① 本檔（repo 根 .env）」，而三個
> # 逃生口（`AUTOSDD_QUOTA_GUARD_OFF`／`AUTOSDD_SENTINEL_OFF`／`AUTOSDD_CONTEXT_GUARD_OFF`）
> # 全部直讀 `os.environ`、一律不經 `policy_env()` ⇒ 在 `.env` 裡設 `AUTOSDD_QUOTA_GUARD_OFF=1`
> # → **rc=2（沒放行）**；設成真環境變數 → rc=0。「安全逃生口靜默失效」比沒有文件更糟：
> # 人以為關掉了、守衛照擋，而兩者外觀完全相同。

### L-3.26 `_tmpdir` R84／SA84-06 量測數字（265→295、delta=0）

>         立案是量出來的：`ls $TMPDIR | grep -c autosdd_dotenv` ＝ **265**（複審當下的
>         量測值，不是常數——落地時同一條指令已經 295，因為它每跑一次就漲）。本類每跑一次
>         就在使用者的暫存區留下數個目錄，而它們永遠沒有人收。與哨兵孤兒 job 同一個病
>         （測試在開發者機器上留下真實副作用），只是這一種安靜得多。
>         落地驗證：接上本 cleanup 後，同一支模組跑完一輪的 delta ＝ **0**。

### L-3.27 `QuotaGateIsWiredToTheBurnPathTest` R83 實測與紅端逐字

>     呼叫點條件此前是 `if blocking and …`，而 `blocking` 只在 PreToolUse 為真 ⇒ 額度只在
>     「我要扇出」那一刻被問一次。R83 實測：配額 5%→90% 的整段，主 session 派完最後一波之後
>     再也沒呼叫任何扇出型工具（後續全是全樹跑、agent 回傳、大量讀檔）⇒ 本閘一次都沒被叫到。

>     紅端（接電前實跑）：PostToolUse×{Read,Bash,Grep,Glob,Task} 一律 rc=0、stderr 0 位元組、
>     零任務書、`decide()` 呼叫 0 次。

### L-3.28 R84 掃描面擴到 AutoClaude hooks 的立案實測

> # 🔴 立案（Windows 彈窗窮舉的實測結論）：全庫 80 個 spawn 站點只有 10 個帶旗標，而本鎖的
> # 宣告集合只有 14 支檔——`AutoClaude/**` **整片在射程外**。而那一層裡有一族與根層 hook
> # 完全同構的東西：`AutoClaude/tools/hooks/*.py` 是子專案 session 的 Claude Code hook，
> # 跑在**同一種無 console 的父行程**下 ⇒ 同一個危害、同一個修法、零判準。

> # 🔴 為什麼是「擴面＋登記存量」而不是「擴面就好」：實測擴面後命中 **1 筆**，逐筆判讀是
> # **真陽性**（`claude_md_freshness.py::check_snapshot_drift` 起一支 console 的
> # `sys.executable`，無 `creationflags`），而那支檔不在本包的所有權內。兩個都不可接受的
> # 選項：讓閘門紅著交件／把射程縮回去。

### L-3.29 `QuotaPrepareBandActuallyPreparesTest` 紅端逐字

>     """🔴 紅端（本輪落地前對 HEAD 實跑，逐字）：合成 86% 快取走真閘 ⇒
>     `event=PostToolUse tool=Read rc=0 stderr_bytes=0 plan_writer_calls=0`；
>     `event=PreToolUse tool=Read rc=0 stderr_bytes=0`。對照 96%：`rc=2 stderr_bytes=607`。
>
>     也就是 85% 這一帶唯一真的會發生的事，是 PreToolUse×`Workflow` 被擋
>     （`UNBOUNDED_FANOUT_TOOLS` 只有這一個成員）；`Read`／`Task` 全部靜默放行，
>     而訴求 6C 要的「提前準備下一次 reset」一份任務書都沒有——外觀與「額度很健康」相同。
>     R83 交棒書把射程記成只有 PostToolUse，實測**兩個事件都靜默**。

### L-3.30 R80 撞線驗屍（`SpendLimitReachesAHumanTest`／`UnhandledLimitDetectionTest`）

`SpendLimitReachesAHumanTest`（缺口 A 的載體敘事）：

>     缺的是「通知」有沒有載體：兩支的理由逐字寫著「只有人去 claude.ai 提額才會回來」
>     「硬停並通知人」，而全部的反應是 `print(..., file=sys.stderr)`——這兩支都由
>     schtasks 以 `pythonw.exe`（GUI 子系統、**沒有 console**）起，那行 stderr 沒有任何
>     終端收得到。⇒ 「不排程」成立、「叫人」結構上不可能成立，而兩者留下的痕跡完全同形
>     （狀態 abandoned、工作被刪、jsonl 多一行）。**最難發現的失效形態**正是這一種。

`UnhandledLimitDetectionTest`（哨兵整晚失明的三條性質原文，含事故細節）：

>     被守的性質有三條，每一條都對應一個**已實際發生過**的失效：
>       ① 「已處理」必須是**證據**（事後真的有成功 API 回應），不是推論。舊判準的推論
>          逐字是「我跑得動武裝指令 ⇒ 額度是通的」，而武裝是零 API 呼叫的本機 subprocess
>          ⇒ 那句話恆真、與額度無關。實證：撞線後 2 分鐘就被標成已解決。
>       ② 偵測面必須含 subagent（扇出模式下撞線主要打在那裡）。
>       ③ 必須看**所有**未處理事件，不是只看最後一筆——本次事故裡最後一筆是 `quota_spend`，
>          把更早、仍未解決的 `quota_session` 整個蓋掉。

## L-4. 哨兵存活四修（R95 實作包）：立案、LOC 對價帳與搬遷史料

**立案**：2026-08-16 深夜事故（ADR-XPLAT-004 §2.9 事故時間線；PRD v2.1.5 §4.5.6）。
halt 動作經 `plan_writer` 走 planner 預設路徑**整檔覆寫**任務書，砸掉哨兵 RELAY 狀態塊
→ 00:55 哨兵讀不出狀態塊而**靜默自我解除**（`_abort_and_unregister`，stderr 無人收）
→ 03:50 reset 時機器上零排程 → 空轉八小時至人工介入。四修落地物：
修1＝planner 預設寫出路徑先 `parse_relay` 舊檔、寫完骨架 `write_relay` 回填（R-4.5.6-3）；
修2＝`_heal_relay` 自癒續巡＋三種失效分形＋解除必經 `escalation.alert(loud=True)`
（R-4.5.6-4）；修3＝`sentinel_lifecycle.liveness_problem/liveness_line` 接進 `--pace`
／`--check`（armed stamp vs 排程器現查）；修4＝`quota_messages.halt_resets_at`（詳見
Pace 證據檔 §7-R95-修4）。

### L-4.a PRD §4.5.6 驗收判準 A1~A5 自評（實作包當回合）

| # | 判準 | 自評 | 憑證 |
| --- | --- | --- | --- |
| A1 | 含狀態塊的任務書經骨架重寫後狀態塊存活 | **達成**（紅綠自證：修前實跑紅） | `SentinelDecisionTest.test_a_skeleton_rewrite_preserves_an_existing_relay_block`：斷言 `parse_relay` 逐格等於原狀態塊 |
| A2 | 狀態塊缺席×逐字稿存在 ⇒ 不得 unregister＋告警注入點被叫 | **達成** | `test_a_smashed_relay_self_heals_instead_of_unregistering`：`_schtasks_remove` 零呼叫、`escalation.alert` 被叫、rc=0 且重排 `--sentinel-tick` |
| A3 | binding 無 reset＋他軸有 reset ⇒ arm；全軸無 ⇒ escalate | **達成** | `test_quota_policy.TestR95HaltArmsOffTheEarliestResettableAxis`（5 支，含 waker 接線與訊息面） |
| A4 | 事故重演劇本產出 `arm_reset` 且武裝憑證非空 | **達成（劃界）**：整合測試以事故逐字撞線記錄注入，斷言 state=waiting、reset 來源 transcript-verbatim、憑證鍵非空且 `relay_problems=[]`；**排程器自報憑證的真機半邊**由既有後端鎖（`schedule_backend.arm()` 回讀閘＋`test_mac_endurance_r83`）承擔——本測試模組依既有紀律不碰真排程器 | `test_the_incident_replay_arms_to_the_observed_reset_with_evidence` |
| A5 | 巡邏／武裝／自癒／解除各步痕跡事件名互異 | **達成** | `test_the_three_read_failures_and_the_heal_leave_distinct_traces`：事件集 {sentinel_woken, sentinel_selfhealed, sentinel_heal_failed, sentinel_aborted, sentinel_rearmed} 互異＋三種讀不出 why 分形（=3） |

已知殘項（如實列出）：ADR §2.9 誠實劃界「修 4 實作時應讓閂鎖多記 session_id 與 tool」
未實作（持有面跨 hook 注入簽名；見 Pace 證據檔 §7-R95-修4）。

### L-4.0 LOC 對價帳（R89 手法；`session_resume_planner.py` 部分）

動工前 counted LOC＝749/750。四修新增（修1 +3、修2 +17、修3 +9，含 import）以
**輸出逐位元不變**的實體行合併抵銷（`_resume_tick`／`_arm_sentinel`／`_sentinel_tick`
／`_arm_endurance`／`sentinel_decide` 共 22 站點續行合併），完工實測 **748/750**、
`check_loc_budget --json` 的 `root_tools_violations=[]`。測試面（本檔 §L-4.1 起）＝
`test_context_budget_guard.py` 新增測試以等量史料搬遷抵銷，完工 raw 行數逐位元回到
凍結值 6897（護欄行數棘輪 84362 不動、重釘表未動）。

### L-4.1 搬遷史料（原 test_context_budget_guard.py「R79 Auto Pilot」節首，一字未刪）

```
# 掌舵者逐字裁決：「現在開，但禁止 commit/push」。**兩件事必須綁在同一組鎖裡**——
# 只鎖前者會讓「開了但護欄沒接上」全程綠，而那正是本 repo 判過三次的
# 「機制蓋好沒接電」（R77 PKG-GUARD）。所以下面兩個 class 是一組：
#   ① 預設真的是開，且兩個關閉出口都真的關得掉；
#   ② 那一跑的 spawn **真的**帶著無人看管訊號（漏注入是靜默的——護欄不會出聲說
#      自己沒被掛上，被守的那一跑也不會知道自己沒被守）。
# hook 那一端讀同一個字面，由 `tools/tests/test_check_hooks_liveness.py` 自證。
```

### L-4.2 搬遷史料（原「R80 無 console 父行程下的 spawn」類級敘事，一字未刪）

```
# 🔴 為何是**類級**而不是「把漏掉的兩站補上就好」：R79 治這件事時只改了排程 Action 的
# 載具（python.exe → pythonw.exe），而同一條路上還有三個 spawn 站點沒帶旗標——本 repo
# 已反覆判過「同一份知識住多個家、只鎖一個」的形態（R73 `Find-GitBash`、R79 的 3 站鎖 1
# 站）。所以這裡鎖的是**一整類檔案的一整類呼叫**：宣告集合內每一個 subprocess spawn 都
# 必須顯式帶 no-window 旗標，漏掉任何一站當場紅，不靠人記得。
#
# 集合語意＝「這支檔可能在**無 console 的父行程**下被執行」：
#   · `.claude/hooks/*.py`      由 Claude Code 起（實測其 hook 子行程會自帶 conhost）
#   · `tools/session_resume_planner.py`  由 schtasks 以 `pythonw.exe` 起（無 console）
# 在那個條件下 spawn 一個 console 子系統應用（`python.exe`／`powershell.exe`／
# `claude.exe`）時，Windows 必定新配置一個 console ＝跳到使用者臉上的視窗。
#
# 🔴 分母是**覆蓋率棘輪**（鐵律三的體例）：`_CONSOLE_FREE_FLOOR` 只准升。新增一支 hook
# 卻沒進掃描面時，掃描面會縮到下限以下而轉紅——「射程靜默縮小」是本 repo 記載過的
# 失效方式（`MIN_TESTS` 腐化 11 輪），不能只靠 glob 看起來會自己長大。
```

### L-4.3 搬遷史料（原「R81 額度軸」節敘事，一字未刪）

```
# 🔴 本段每一條都對著一筆**已被獨立審查者實測坐實**的失效，而不是對著實作細節：
#   SA-B1 quota 分支掛在 `block_verdict()` 內 ⇒ 低 context × 高 quota 那個唯一場景到不了
#   SA-B2 分母不是散文，payload 自己帶 `*_dollars`
#   SA-B3 有真值卻不在 `limits[]` 的桶（實測 `nimbus_quill`）
#   SA-B4 utilization 非單調（視窗翻頁驟降 48pp）⇒ 過期快取不得被判為 normal
#   SA-B6 被擋下的呼叫若留在帳上 ⇒ 永久過度節流
#   SA-B7 mac/Linux 上「不排程」與「排不了」外觀相同
#   SD-B1 `Workflow` 在扇出開始前就返回 ⇒ in-flight 恆讀 ≈0
# 🔴 R82：本檔那份寫死的 quota schema 複本已刪除（見 `_quota_cache` 的 WHY）。要 schema
# 的地方一律 `_meter().SCHEMA`——契約字面只有一個家，而那個家在 meter。
# （刻意**不**以反引號逐字寫出那個已死的常數名：幽靈符號鎖對它必紅，而下一個人 grep
#  到它會以為那是現行說法——同 `check_loc_budget.py` 對已死常數名的既有處置。）
```

### L-4.4 搬遷史料（原「R83／F2-② 接線面」節敘事，一字未刪）

```
# 🔴 立案（獨立複驗補的那一半）：F2-② 把取證指引下沉到 `schedule_backend.<後端>.
# evidence_hint()`，而「三句話彼此不同、mac 那句不含 Windows cmdlet」已由
# `test_mac_endurance_r83.BackendInterfaceIsSymmetricTest` 在**後端層**守住。但那是
# 判定層——「那三句話真的出現在使用者讀到的那則訊息裡」是另一件事，而本 repo 的
# 「機制蓋好沒接電」已三度復發。複驗當回合實測：把 cmdlet 字面貼回 `quota_halt_message`
# （＝本輪修掉的缺陷原形，且 `evidence_hint()` 仍留在原處被別人叫）時，全庫**沒有任何
# 東西會轉紅**——後端那三句仍然正確，只是沒有人在讀它。缺陷 ② 的本體是「訊息說了假話」,
# 所以判準必須讀訊息本身。
```

### L-4.5 搬遷史料（原 C3-P1 `PWNED` 判準註解，一字未刪）

```
        # 🔴 R84／C3-P1：判準由 `Write-Output` 換成 `PWNED`——**不是放寬，是換成唯一標記**。
        # `Write-Output` 是 PowerShell 的普通動詞，腳本自己也會**合法地**用它（本輪 P1 在
        # Principal 回退分支加了 `Write-Output 'PRINCIPAL-FALLBACK=…'` 留痕跡）⇒ 舊判準對
        # 「腳本裡本來就有一個 Write-Output」與「payload 逃出來了」無法區分，那是假紅。
        # `PWNED` 只住在 `_NASTY_TASK` 裡，兩者在 payload 中相鄰 ⇒ 逃出去一定一起逃出去，
        # 鑑別力不減。把 `_ps_single_quote` 改成恆等即紅（本輪實測，見收輪回報）。
```

### L-4.6 搬遷史料（原 no-window 豁免上限註解，一字未刪）

```
#: 🔴 合法例外的**名字**與**上限**。
#: 本 repo 判例：沒有上限的逃生口會變成預設關法——豁免標記一多，這支鎖就等於被關掉。
#: 用法：在 spawn 呼叫的**任一行**行尾寫 `# no-window-ok: <為什麼這支真的需要視窗>`；
#: **理由留空無效**（正規式要求至少一個非空白字元）——「有標記」不等於「有理由」，
#: 那是本檔另一條判準（`creationflags` 有設 ≠ 設對）在豁免這一側的同一個形狀。
#: 今天實測用掉 **0** 個。要調大這個上限請在缺陷帳本具名理由；方向是只准調小。
```

### L-4.7 搬遷史料（原 C3-A `schedule_backend.py` 具名加入註解，一字未刪）

```
        # 🔴 R84／C3-A：`schedule_backend.py` **具名**加入。它不叫 `quota_*`／`sentinel_*`
        # 所以上面兩個 glob 一條都罩不到它，而它正是哨兵路徑上僅存的兩個裸 spawn 的家
        # （`_run()` 每 tick 跑 schtasks 查詢／註冊、`_defer()` 起延後的 `/bin/sh`）——
        # 掃描面是 glob 決定的那一刻起，這支就對本鎖隱形，與 R82 漏掉 `quota_meter.py`
        # 逐字同構。刻意具名而不是再放寬 glob：放寬會把同層純資料模組一起拉進來，
        # 製造要逐一辯護的假紅（本 repo 判過那種鎖活不過一輪）。
```

### L-4.8 搬遷史料（原「R81 續航協定的兩個設計缺口」節敘事，一字未刪）

```
# 兩個都不是 bug——機制照著規格跑，而規格漏了一種情況。鎖也照這條界線寫：守的是
# 「規格現在涵蓋了那一種情況」，不是「某支函式回傳什麼」。
#   缺口 A：額度有兩條線（`session limit` 等得到、`monthly spend limit` 等不到），
#           而下游動作只有一種。R80 第 3 次撞線就是這一類，協定全程零反應。
#   缺口 B：協定救的單位是 session，而四次撞線裡主迴圈**一次都沒死**——死的是扇出。
```

### L-4.9 搬遷史料（原 C3-C 處置名單註解，一字未刪）

```
    #: 允許的處置：拆掉自己（`_schtasks_remove`）、重排下一次（`_register_and_record`），
    #: 或把整件事**交棒**給另一支同樣受本判準約束的 tick（`_resume_tick`）。
    #: 三者以外的 return＝那一跑醒來、做了點事、然後把排程留在原地 ⇒ 下一個間隔它會
    #: 再醒一次、再走同一條路，永遠不會停。Windows 上那就是每 15 分鐘一個黑框。
    #: 🔴 R84／C8：第四個名字是**委派**而非新語意——`_abort_and_unregister` 是那四條
    #: abort 路徑收成一份之後的唯一實作，它在函式體第一行就無條件 `_schtasks_remove`。
    #: 直接把名字加進本表會讓判準退化成「呼叫了一個名字好聽的函式」，所以同輪補
    #: `test_the_abort_delegate_really_disposes`：委派自己不處置時當場紅（兩條合起來
    #: 才等價於原判準的強度，缺任一條都比原判準弱）。
```

### L-4.10 搬遷史料（原 `_isolated_env` real_scheduler 註解後半，一字未刪）

```
    # 🔴 上面那組 `TMPDIR`／`HOME` 隔離**結構上擋不住這件事**：`launchctl bootstrap` 進的是
    # 真正的 `gui/<uid>` 網域，與 plist 落在哪個目錄無關 ⇒「把暫存改掉」這一招在排程器
    # 這一軸沒有對應物。唯一能擋的位置就是「根本不要走到武裝那一步」。
    # 🔴 為什麼沿用 `AUTOSDD_SENTINEL_OFF` 而不是新開一個測試專用旗標：它已經是「不要
    # 武裝」的唯一真相源，新開一個等於同一件事兩個家。上面那個 `pop` 仍然必要且不衝突
    # ——它治的是「開發者機器上設過就靜默轉綠」，這裡治的是「測試不得留下真實副作用」，
    # 兩者方向相反地作用在同一個變數上，所以順序是先 pop 再由本測試決定。
```

### L-4.11 搬遷史料（原 refresh_stamp／burn_ledger 兩格立案註解，一字未刪）

```
    # 🔴 R84：第三格（`refresh_stamp_path`）。它與上面兩格同構——額度軸落在生產暫存的
    # 檔——而它此前在 `claim_refresh_slot()` 裡是寫死路徑、沒有注入點 ⇒ 任何走到刷新
    # 路徑的測試都會吃掉真的那個 180 秒名額，此後真的需要補量時靜默不補。
    # 🔴 R86：第四格（`burn_ledger_path`）。它住**持久**目錄（`~/.autosdd/traces`）⇒ 漏關
    # 的代價比前三格更大：合成讀數會被 `burn_ratio()` 當真觀測拿去推換算比，汙染的是
    # **下一次真的派工決策**（理由全文見具名證據檔 `CrossPlatform_R86_Pace_Calibration.md`
    # ——刻意不寫它的目錄前綴：分桶棘輪把「提到散文樹」的整塊歸進 shrink-only 的 `prose`
    # 桶，而本塊守的是沙箱隔離、不是散文，寫全路徑會讓 61 行被誤記進那一桶）。
```

### L-4.12 搬遷史料（原憑證雙欄登記表註解，一字未刪）

```
#: 憑證來源的**雙欄登記表**（R83）。ONBOARDING §7 那兩欄基線是同一個體例：不把「這台
#: 機器上憑證住哪裡」寫成常數，而是把**每個平台各自的答案**登記下來，兩欄在**任何**主機
#: 上都跑。`platform` 是 `sys.platform` 的字面（`quota_meter.access_token` 的分支讀它）。
#:
#: 🔴 為什麼不是「在 mac 上跳過檔案欄／在 Windows 上跳過 Keychain 欄」：那等於那個平台
#: 的憑證來源永遠沒有覆蓋，而本組要守的性質（「憑證讀不到」與「憑證讀得到但 401」是兩個
#: 分得開的答案）**兩個平台都必須成立**——它正是排程器判斷「要不要繼續等額度回來」的
#: 依據，一邊沒守住就等於那半邊的節流演算法建立在假數字上。
```

### L-4.13 搬遷史料（原 `_run_hook3` docstring 後半，一字未刪）

```
    走子行程而非 import＋呼叫 `main()`：hook 的契約是「被 Claude Code 以獨立行程呼叫、
    讀 stdin、以 exit code 表態」，import 進來會繞過 stdin 與 exit code 這兩個契約面
    （本 repo「驗證載具必須對齊 production 真正執行路徑」的既有紀律）。

    🔴 R91 起 75% 提示同時送上 stdout 的 `hookSpecificOutput`（exit 0 下唯一進得了模型
    context 的通道；沿革原文＝Resume 證據檔 §L-3.4）。
    `_run_hook()` 保留為本函式的 `[:2]` 投影，而**不是**把它就地改成三元組：
    只有真的要斷言 stdout 的那幾個站點改呼叫 `_run_hook3()`（本輪 4 個），其餘沿用投影
    ——為了一個新性質去改一批與它無關的斷言，本身就是引入回歸的方式。
```

### L-4.14 搬遷史料（原 `_returns_with_dominators` docstring 後半，一字未刪）

```
        分支體內的呼叫**不算**其他分支的支配者——那正是「支配」與「函式體內出現過」
        的差別，而後者是沒有鑑別力的（`_sentinel_tick` 隨便哪一支分支呼叫過一次
        `_schtasks_remove`，全部 return 就一起被判成安全）。
        R84／SD-09 射程訂正沿革原文＝Resume 證據檔 §L-3.23。

        分支拆法逐條對齊「真的先跑過」這件事，而不是求方便：迴圈的 `orelse` 只拿到
        **迴圈之前**的支配集合（迴圈可能一次都沒跑）；`except` handler 同理只拿到
        `try` **之前**的（body 可能在任何一行拋出）——兩者都往「判紅」的保守方向站。
```

### L-4.15 搬遷史料（原 `MacCredentialSourceTest` docstring 後半，一字未刪）

```
    本組今天守得住的是「判定邏輯」：平台分支選對了路、取不到時回一個**分得出來的**
    理由字面、`security` 吐出來的垃圾不得變成 token。**仍然守不住**的是「一台**沒有**
    Keychain 條目的 mac」——本機構造不出來（清掉條目等於把使用者登出），那一半只由
    `_runner` 注入覆蓋，屬於模擬而非真機。實測值的**唯一的家**是
    `quota_meter.KEYCHAIN_SERVICE` 的註解，本段刻意不複寫（R73 判例）。
```

### L-4.16 搬遷史料（原 quota 獨立路徑鎖 docstring 後半，一字未刪）

```
        上一條只釘住「額度沒有被掛進 context 阻斷路徑」，於是「額度根本沒有人在守」
        與「額度有自己的路徑」兩種狀態它**都判綠**——分母 0 的鎖恆綠，正是本 repo
        判過四成的那一桶。這一條要求 quota 必須有一條**存在且獨立**的路徑：
        `quota_gate()` 存在、被 `main()` 呼叫、且它自己不碰 context 那三個早退符號。

        🔴 R82／Q2-02 擴射程：那條路徑現在住 `tools/lib/quota_gate.py`，所以「存在」
        這件事的掃描面必須跟著搬——否則本鎖會因為 hook 裡再也找不到 `def quota_gate(`
        而變成**恆紅**（那與恆綠一樣沒有鑑別力，而且會被人順手刪掉）。
```

### L-4.17 搬遷史料（原 `_outside_single_quoted` docstring 後半，一字未刪）

```
    PowerShell 單引號字串的文法很小且完整：`'` 進入字串；字串內 `''` 是一個字面單引號、
    仍在字串內；落單的 `'` 結束字串。這裡刻意自己走一遍而**不外呼 `powershell.exe`**——
    根層 unittest 在 mac／Linux 也要跑，多一支平台 skip 就是多一個沒人在跑的判準
    （而「沒人在跑的判準」正是本輪 S3 在治的東西）。

    🔴 這支掃描器與**真** tokenizer 的一致性由 R79 收輪當回合兩地對照證過：同一份腳本
    餵給 `powershell.exe` 的 `[Parser]::ParseFile`，健康版 `errors=0`、把 `_ps_single_quote`
    改成恆等後 `errors=4` 且 `Write-Output` 以獨立 token 出現——與本函式的判讀一致。
```

### L-4.18 搬遷史料（原 `_quota_cache` docstring 多軸段，一字未刪）

```
    `extra`＝再加幾條 `(kind, pct, resets_in)` 軸——多軸是 R82 之後才**表達得出來**的
    東西：舊形狀只有頂層一組 `{pct, kind, resets_at}`，於是「session 90%@34min ＋
    weekly 20%@6d」與「session 10%@34min ＋ weekly 90%@6d」在快取裡根本寫不出差別。
    `account_key`＝R93 新增的帳號身分欄（`None`＝不寫這一鍵，等同本輪之前的舊快取）。
```

### L-4.19 搬遷史料（原 NO_WINDOW 行為測試 docstring 後半，一字未刪）

```
        控制組（不帶旗標）必須**有** console，否則本載具量不到這個缺陷，上一條斷言
        就沒有鑑別力——一個永遠回 0 的壞載具看起來與修好一模一樣。

        🔴 **子行程刻意用 `python.exe` 而不是 `pythonw.exe`**：後者是 GUI 子系統，在
        六種旗標下**全部**都是 0（見 `guard.NO_WINDOW` 的矩陣第三、四列）⇒ 拿它當被測
        對象，控制組也會是 0，整條測試恆綠。要驗「旗標那一層」就必須挑一個沒有旗標
        時**真的會開視窗**的載具。
```

### L-4.20 搬遷史料（原 `_sources` docstring 後半，一字未刪）

```
        🔴 R82／HELM-02 把 `tools/lib/` 那一半由手寫清單換成 glob。舊寫法只具名了
        `quota_escalation.py`（R81 新增 spawn 站點的那一支），於是同一層的
        `quota_meter.py` 帶著一個**沒有 `creationflags` 的 `subprocess.run`** 一直對本鎖
        隱形——本鎖照跑、照綠。這正是本類 docstring 自己寫著要防的事，只是缺口不在
        「有沒有掃」而在「掃誰是誰決定的」：手寫清單的分母由記憶決定，glob 的不會。
        射程限定 `quota_*`／`sentinel_*` 兩族而不是整個 `tools/lib`：那一層還有純資料與
        純判準模組，把它們全拉進來只會製造要逐一辯護的假紅（本 repo 判過那種鎖活不過一輪）。
```

### L-4.21 搬遷史料（原 `EveryHookEscapeHatchIsDeclaredTest` docstring 後半，一字未刪）

```
    誠實劃界：射程**只有這一支 hook**。`AUTOSDD_GIT_GUARD_OFF`／`AUTOSDD_CLAIM_GUARD_OFF`
    （`block_destructive_git.py`／`check_claim_provenance.py`）今天不在 `ENV_SPEC` 裡，
    也就是它們從 `.env` 到不了——那是**已知且尚未關的缺口**，不是本組漏看；把它們一起
    納入會製造兩筆今天無人負責的紅，而那種鎖活不過一輪。
```

### L-4.22 搬遷史料（原 session-limit 控制組 docstring 後半，一字未刪）

```
        判準的價值全在這裡——一個「把兩類都叫人」的實作會讓上面兩條全綠，卻把每一次
        普通的 session 撞線都變成一次騷擾，於是護欄很快就會被關掉。

        語料刻意**不帶** `(Asia/Taipei)` 後綴：帶了的話 `declared_zone` 在有 tz 資料庫的
        機器（Linux／macOS）上會把時刻換到台北框架、在 Windows 上回 `None` 而沿用機器
        時區 ⇒ 同一份語料在兩種機器上落在不同分支。這是本 repo act 實跑抓過的形態。
```

### L-4.23 搬遷史料（原 same-file 判準 docstring 後半，一字未刪）

```
        `guard.unhandled_limit_event` 用**全域**復原證據，本模組用**同檔**證據——因為
        它們問的是不同的問題。R80 量到同檔證據對「帳號額度通不通」假陽性 81.3%，成因
        是「被打死的 subagent 在自己的檔裡永遠不會再有下一則成功回應」；而對「這一個
        agent 死了沒」，那個性質正是唯一正確的判準。把本模組改成沿用全域判準，這一條
        會紅：整個 session 已經復原（主逐字稿有更晚的成功回應），死掉的 agent 仍必須
        留在重派清單上——它不會因為別人活過來就自己活過來。
```

### L-4.24 搬遷史料（原 apostrophe 跳脫鎖 docstring，一字未刪）

```
        """🔴 R79 複審（ARCH nonblocking）修的缺陷：五個內插點把外部字串直接塞進
        PowerShell 單引號字串而未跳脫。`O'Brien` 這種**合法**使用者名就足以讓整段
        註冊腳本語法錯——而失效發生在 `powershell.exe` 那一端，本行程只看得到一個 rc。

        判準刻意不看「有沒有呼叫某個函式」（那種鎖改個名字就瞎），而是看**產出**：
        路徑的任何一段都不得落到單引號字串之外，且所有字串必須閉合。
        把 `_ps_single_quote` 改成恆等即紅（收輪當回合實測）。
        """
```

### L-4.25 搬遷史料（原 Principal 回退留痕鎖 docstring，一字未刪）

```
        """🔴 R84／C3-P1：S4U → 預設 Principal 的回退分支**必須留痕跡**。

        修前它是靜默的：`catch { Register-ScheduledTask @common }` 什麼都不印，而取證段
        （`_EVIDENCE_TEMPLATE`）只印 TaskName/LastRunTime/LastTaskResult/NextRunTime，
        一個字都不提 Principal ⇒「S4U 生效」與「已回退成 InteractiveToken」在憑證上
        **長得一模一樣**。而回退後有互動桌面，載具那一層若同時也退回 console 版就會彈窗
        ——兩層一起失效、零痕跡，正是掌舵者看到「黑框每 15 分鐘一次」而工具側查不到的原因。
        """
```

### L-4.26 搬遷史料（原稽核痕跡單一家鎖 docstring，一字未刪）

```
        """🔴 本輪端到端實測抓到的真缺陷：稽核痕跡分裂成兩個檔。

        `--resume-tick` 必須在讀任何東西**之前**就寫下「我被叫起來了」——那一刻它手上
        只有 `--plan`（session id 還躺在沒讀的狀態塊裡）。舊寫法用 session id 當鍵，
        於是開場那一行落在 `..._<plan 檔名>.jsonl`、其餘落在 `..._<session id>.jsonl`；
        而「觸發了但早期就失敗」那一行剛好寫進沒有人會去看的那個檔 ⇒ 這道機制唯一要
        守的東西（讓「沒觸發」可偵測）自己漏掉。鍵只能是任務書路徑。
        """
```

### L-4.27 搬遷史料（原 spend-limit 敲人門檻 docstring 後半，一字未刪）

```
        🔴 R82／HELM-01 收緊了「敲人」的門檻，所以這一條的語料也跟著補上第二個合取項：
        **有未處理撞線 且 有扇出待救**。理由是使用者三度收到彈窗的那件事——「敲人」是
        整條協定裡唯一會打斷人的動作，而唯一只有人做得到、又真的等不了的情形，是有一批
        被打死的 agent 等著他去按 `resumeFromRunId`。沒有東西要救時仍然寫紙（零打擾），
        那一半由 `test_a_spend_limit_with_nothing_to_rescue_never_taps_a_human` 守。
```

### L-4.28 搬遷史料（原 `test_both_events_speak_and_leave_a_restart_point` docstring 後半，一字未刪）

```
        🔴 誠實劃界（SA-03 的紅端證據裡混了一格治不了的）：`PreToolUse` 只在**扇出邊緣**
        被叫（`tool not in blocking` 就早退，那是刻意的——收斂型工具不受額度節流），
        所以 `PreToolUse×Read` 在 86% 仍然是零位元組，而且**應該是**。那一格由
        `PostToolUse`（射程是註冊面上的每一個工具）覆蓋 ⇒ 兩者合起來的性質才是本輪要的：
        「進了 prepare 帶之後，**第一次**工具呼叫就會出聲並留下可重啟點」。
```

### L-4.29 搬遷史料（原 M2 `test_a_torn_multibyte_plan_self_heals_as_the_fourth_fault` docstring 後半，一字未刪；R95 收尾窗口批）

```
        ——修前 `read_text` 直接炸：無痕跡、無告警、排程僵在原地（比自我解除更難驗屍）。
```

### L-4.30 搬遷史料（原 m5 `test_a_pathological_env_limit_falls_back_loud_not_crash` docstring 修前段，一字未刪；R95 收尾窗口批）

```
        修前直接炸在喚醒路徑（`int()` ValueError）
```

## §L-5 DEF-200-148 立案原文（掌舵者 2026-08-17 定級「會破產的嚴重 BUG」，原話要求務必紀錄；帳本列因單列 700 bytes 上限瘦身成索引，全文一字不動搬此）

> 主控閒置盲區——subagent 背景耗至 session 38% 期間主控零喚醒、水位無人量測、subagent
> 撞線（08-16 收尾包＋08-17 修復包兩次實證）後主控未被機械喚醒統籌。三結構洞：
> ①主控閒置＝零工具呼叫 ⇒ hook 水位機制全睡；②哨兵只認已撞線不做接近滿水位預防；
> ③撞線通知到達時主控可能同在 limit 內。機械修復方向（PRD v2.1.6，R96 開場即辦）：
> 哨兵巡邏加水位預警職責（usage ≥ prepare 錨點且有活躍背景工作 ⇒ 主動武裝喚醒排程＋
> 寫收斂任務書）。過渡紀律已入 memory：派背景波必掛 10-15 分 timer。
