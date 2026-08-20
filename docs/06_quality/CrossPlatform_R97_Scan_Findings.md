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

<!-- guard-total:R97 --> **本輪護欄層累積淨額＝ 84806 → 85695（+889）** —— 逐檔漂移 3 支
（含「同輪追加」節：commit 9ef67f8 之後收尾窗口續作的 +309 與自身編修 +35，逐項見下方；
另含 PRD §4.5.7／§4.5.8 落地的 +266，見「同輪追加③」段）

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
| 本輪淨額 | +279 | 遠低於上限，款(10) 不觸發 |
| 連續上升輪數 | 2（R96 +407、R97 +279） | 上限 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`，剛好踩線但不逾越，款(11) 不觸發；**R98 起必須出現一次淨額 ≤ 0** |
| 到期義務 | 已到期並兌現 | `_REPIN_NET_CAP_DUE_ROUND = 97`（本輪＝到期輪）；上限表追加 `(97, 950)`，同輪重新武裝下一段：到期輪 99、目標 850 |

<!-- guard-total:R97 --> 護欄層累積總量現值 **84806 → 85695（+889）**；原始逐檔清單即上一節，
「同輪追加」節見下方新增段落，款(12) 到期義務同輪兌現（上限表追加 `(97, 950)`，
重新武裝下一段到期輪 99、目標 850）。

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

三條合法出口逐條實查（同上一節體例）：刪死碼不適用（皆為本輪修復必要的回歸覆蓋或
治理帳本自身的稽核痕跡）、搬史料不適用（P0-1/P2-1/P2-2 判準與回歸鎖同次落地，無等量
舊敘事可搬）、抽共用層不適用（`drift_tolerance=0`，且追加②純為數字與註解，無可抽結構）。

連續上升輪數：R96（+407）／R97（原始 +279、追加① +309、追加② +35，合計 +623）
——依 `repin_round_nets()` 同輪合併語意仍計為兩輪，未產生第三個連續上升輪，
`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` 不觸發；`net_cap_for_round(97) = 950`，
本輪合計 623 遠低於上限，`[超出每輪上限]` 不觸發。

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
