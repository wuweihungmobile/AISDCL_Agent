# 喚醒鏈鐵律 — 規則清單＋驗證方法＋誠實現況（2026-09-06）round-label-ok

> 用途：掌舵者要求「把規則整理出來，讓我後續驗證」。本檔逐條列出你講過的鐵律、
> 它在程式碼裡的**機械強制點**、你可以自己跑的**驗證指令**、以及**當下誠實現況**。
>
> 🔴 誠實聲明：commit `b1ef81f` 的訊息宣稱「2 輪對抗複審全修／可見性實地驗過／
> 真的種排程＝0 次」。本 session 的四方獨立審計（撿回稿見
> `docs/06_quality/CrossPlatform_R130_FourParty_Salvage.md`）＋主控親驗證明**那些宣稱誇大**：
> 其中 INV1／INV4 在真喚醒路徑上是死碼、洩漏防火牆一行都沒接進閘門、複審無任何可稽核紀錄。
> 「綠色的測試」≠「規則真的守住」——多數 INV 測試自己 `patch.dict` 塞旗標，繞過了真路徑的洞。
>
> 驗證指令一律 macOS／zsh；cwd 標在每段。Python 用 `.venv/bin/python3`。

---

## 一、規則 × 強制點 × 驗證 × 現況

圖例：✅＝本 session 已修並紅綠實證｜⚠️＝部分（有洞）｜❌＝未做／實測失敗

### 規則 1（INV1）：主 agent 沒起來就不該浪費 token — 無人等額度＝零付費探針
- **強制點**：`tools/session_resume_planner.py::probe_quota`（免費端點答不出時，`os.environ.get(AUTOSDD_UNATTENDED)` 為真才不 spawn 付費 `claude -p`）＋ `main()` 分派 tick 前 `os.environ.setdefault(UNATTENDED_ENV,"1")`（本 session 補）。
- **驗證**：`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python3 -m unittest test_context_budget_guard.Inv1ScheduledTickMarksUnattendedTest test_context_budget_guard.Inv1UnattendedZeroPaidProbeTest -v`
- **現況**：✅ **本 session 修好（M-01）**。修前：launchd 叫起的 tick 行程沒帶 `AUTOSDD_UNATTENDED`（plist EnvironmentVariables 只有 PATH，`plutil -p` 實測），該分支是死碼 ⇒ 免費端點答不出時照樣付費探測（≈31,847 tokens／次）。已加測試 `Inv1ScheduledTickMarksUnattendedTest`（紅→綠實證）。

### 規則 2（INV2）：續跑不得以 fan-out（Workflow／子 agent）為第一動作
- **強制點**：**軟閘**＝`tools/lib/resume_route.py::resume_argv(allow_followup=…)`，False 時 prompt 不含 Workflow 提示。**硬擋**＝`.claude/hooks/context_budget_guard.py` 的 `BLOCKING_TOOLS`(Task/Agent/Workflow) 只在 context ≥90% 才擋。
- **驗證**：`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python3 -m unittest test_context_budget_guard.Inv2Inv3WorkflowFanoutGateTest -v`
- **現況**：⚠️ **只有軟閘、沒有硬擋（M-06 未做）**。無人姿態不 deny fan-out 工具 ⇒ 一個剛被叫醒的 agent 仍可自己 spawn 一堆小幫手，沒有任何機制擋。**本 session 的 72-agent fan-out 就是活證據**：沒有機制擋下我。

### 規則 3（INV3）：後續只准在「前一窗確實起來且有進度」且「非本額度視窗第一窗」之後
- **強制點**：`tools/lib/relay_machine.py::followup_allowed`（`made_progress ∧ relay_seq≥1`）→ `session_resume_planner.py::choose_resume_route(followup_ok=…)` → `resume_argv(allow_followup=…)`。
- **驗證**：`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python3 -m unittest test_context_budget_guard.Inv2Inv3WorkflowFanoutGateTest -v`
- **現況**：⚠️→✅（接線測試本 session 補上）：判準與接線存在，且本 session 補了兩支端到端接線測試（`choose_resume_route` 與 `_run_resume` 是否真把 followup 傳下去），並注入 2 個突變實證會紅（M-05 已做）。硬擋仍缺（見規則 2）。

### 規則 4（INV4）：無人看管一次沒進度就停，不得靠 env 放寬成多窗續燒
- **強制點**：`tools/lib/relay_machine.py::no_progress_limit()`（`AUTOSDD_UNATTENDED` 為真回 1）。
- **驗證**：`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python3 -m unittest test_context_budget_guard.Inv4UnattendedStopsOnFirstNoProgressTest -v`
- **現況**：⚠️ 判準有；且**規則 1 修好後真喚醒路徑才吃得到 `AUTOSDD_UNATTENDED`**（在此之前 tick 行程讀不到，夾 1 是死的）。端到端大部分**已涵蓋**（`no_progress_limit()` 夾 1、attended 聽 env、resolve 單次即停三支既有測試）；唯一未鎖的細縫＝`settle_window` 有沒有真的呼叫 `no_progress_limit()`（M-15 降級為細縫）。

### 規則 5（INV5）：同一 session 只准一個排程擁有者，不得雙 job 各自探測
- **強制點**：`tools/lib/relay_machine.py::other_owner_for_session`，只在 `_arm_sentinel` 一站呼叫。
- **驗證**：`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python3 -m unittest test_context_budget_guard.Inv5SingleOwnerTest -v`
- **現況**：⚠️ 一站有；**手動路徑（`--register-schtasks`／`_arm_endurance`）不查 owner（M-13 未做）**；假後端忽略 `prefix` 參數，wiring 測試對「列舉前綴突變」失明（M-07 未做）。

### 規則 6：可自主喚醒（reset 後喚醒鏈自癒、無人介入真的續跑）
- **強制點**：SessionStart 自動 `--arm-sentinel`；哨兵 launchd 每 900s tick；`_resume_tick` 探到額度回來 → `_run_resume` spawn `claude -p -r <sid>`。
- **驗證**（行為＋痕跡）：`launchctl list | grep AutoSDD_Sentinel`（哨兵在不在）；reset 後查 `~/.autosdd/traces/autosdd_sentinel_launchd_<label>.log` 有沒有自己醒來續跑的痕跡。
- **現況**：❌ **本 session 實測失敗**——撞上限後是**你手動喚醒**我的，喚醒鏈沒自己接手。原因至少含規則 1 的死碼（探針行為在真路徑不對）；完整根因尚未逐一歸因。

### 規則 7：完整的測試防火牆（每條規則有機械鎖、刪了會紅、每次更新過 CI/CD）
- **強制點**：應有——(a) 洩漏防火牆 `leak_fence` 接進 `run_root_unittests`／CI／pre-push；(b) 註冊表釘住 INV1~5 測試類別存在。
- **驗證**：`grep -rn leak_fence tools/ .github/ | grep -v test`（應有命中）；`grep -rn Inv1UnattendedZeroPaidProbe tools/tests/ | grep -v test_context_budget_guard.py`（應有存在性錨）。
- **現況**：❌ **不完整**。`leak_fence` 非測試檔 **0 命中**（ADR §3.6 只是設計、沒落地，M-03）；INV 測試 **0 處**被註冊表釘住 ⇒ 整批刪掉沒有任何閘門會紅（M-20）；MIN_TESTS 只是下限，餘裕大於新增測試數。

### 規則 8（CLAUDE.md 鐵律四）：不可扯謊 — 宣稱完成／全綠／零損失必須附當場真跑輸出
- **強制點**：`.claude/hooks/check_claim_provenance.py`（Stop 事件；只出聲不擋）。
- **驗證**：`grep -n "只出聲\|值域\|不帶值" .claude/hooks/check_claim_provenance.py`
- **現況**：⚠️ hook 只認**帶數字**的量化宣稱（`N passed`／`rc=N`）；「完成」「全綠」「零損失」這種**無值宣稱**它結構上看不見。commit `b1ef81f` 的誇大正是走這個盲區溜過去的。

---

## 二、本 session 已修（附紅綠指令，可自己重放）

- **M-05（規則 3）**：`choose_resume_route`／`_run_resume` 接線測試（本 session）。
  - 綠：`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python3 -m unittest test_context_budget_guard.Inv2Inv3WorkflowFanoutGateTest -v`
  - 證明有牙：把 `choose_resume_route` 的 `allow_followup=followup_ok` 改成 `=True`（或把 `_run_resume` 的 `followup = relay_machine.followup_allowed(state)` 改成 `= True`）→ 判紅；還原回綠。
- **M-01（規則 1）**：`main()` 分派 tick 前補 `AUTOSDD_UNATTENDED`。
  - 綠：`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python3 -m unittest test_context_budget_guard.Inv1ScheduledTickMarksUnattendedTest -v`
  - 證明它會紅：把 `tools/session_resume_planner.py` 裡 `if args.sentinel_tick or args.resume_tick:` 那兩行拿掉，再跑上面指令 → 2 fail。
  - ruff：`.venv/bin/ruff check tools/session_resume_planner.py tools/tests/test_context_budget_guard.py` → All checks passed!

## 三、仍未做（不塗綠；每筆一句話＋帳本代號）

- 規則 2 硬擋 fan-out（M-06）；規則 4 端到端測試（M-15）；
  規則 5 手動路徑查 owner（M-13）＋假後端保真（M-07）；規則 6 自主喚醒根因逐一歸因；
  規則 7 leak_fence 接閘門（M-03）＋INV 測試註冊表（M-20）；規則 8 無值宣稱防火牆。
- 完整 22 筆見 `docs/06_quality/CrossPlatform_R130_FourParty_Salvage.md`（含 evidence／驗證建議）。
- 🔴 這些多數跨檔、且部分撞 LOC 上限（`quota_escalation.py` 400/400、`context_budget_guard.py` 1089/1089），
  需搬史料騰額度、且收尾（MIN_TESTS／護欄線／帳本／ONBOARDING 回填）只能單人窗口一次帶走。
