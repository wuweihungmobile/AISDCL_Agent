# CrossPlatform R211（improving_113）四方複審逐字稿——六面 Sonnet 唯讀審查鏡原文

> 姊妹檔：主審計證據檔＝`docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md`（判決、裁決、處置、理論洞、結案帳住那裡；本檔只保全原文供逐條重驗）。

## 〈T-1 W3 QA 鏡〉（review_w3_qa_113.md）

# W3 引擎無人值守硬化包｜QA 零信任複審（improving_113）

- 審查者：QA 零信任複審鏡（Sonnet）。範圍：`AutoClaude/` 的 10 支修改＋2 支新檔；未讀、未評、未跑 `tools/`（W1）與根層全套。
- 方法：交件 `w3_dev_log_113.md` 的每個數字都自己重跑；repo 全程唯讀（除 `__pycache__`／`.pytest_cache` 這類 git 忽略的快取外），唯一的就地改動是步驟 3 的 sliced_sleep.py 突變（已還原並以 sha256 對帳）；其餘突變一律「記憶體內」（pytest -p 外掛，scratchpad 內），零 repo 寫入。
- 產物目錄：`/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/qaw3_out/`（輸出檔、突變驅動 `mutate_qa.py`、獨立 E2E `qa_e2e_refusal.py`、覆蓋率 `qa_cov.py`）。

## 0. 判決

**VERDICT: CONDITIONAL（QA3-01）**

- 功能面全部成立：全套 4910 passed／156 skipped／rc=0（基線 4864／156，+46＝新檔 44＋boot self check 2）；lint-imports 9 kept 0 broken；ruff 乾淨；LOC 五類 violations 皆空；snapshot_sync rc=0；拒絕長睡的端到端三項（checkpoint 先落盤／halted＋external_resume_required／main() rc=1）全綠；CLI 三條事實逐字重現；零 skip；零輪號違規；零新增 DEF-ID。
- 6 個規格內突變：5 個被擊殺、1 個存活（M2：容忍邊界 `>`→`>=`，QA3-02，P3）。
- 唯一必收條件 **QA3-01（P2）**：`sleep_slice_seconds`／`clock_jump_tolerance_seconds` 的出廠預設（60／5）與 PRD §4.5.2／§9 逐字常數（`SLEEP_SLICE_SECONDS=30`／`CLOCK_JUMP_TOLERANCE_SECONDS=120`）不同，且 config.py 註解寫「常數住 PRD §9」、測試名寫「defaults follow the plan」而計畫書 §3.3 並未給這兩個數字——未登記的對憲法偏離。修法二選一（見 §7）。
- 其餘 QA3-02～QA3-09 為 P3／P4，只列不改判；其中 QA3-02／03／04 建議同 commit 順手收（各一行到數行）。

## 1. 驗收指令（逐字尾段；皆在 `AutoClaude/` 下、根 `.venv`、`unset AUTOSDD_PARALLEL_TESTS`）

### 1.1 全套 pytest（`python -m pytest tests/ -q`）
```
[PG autodetect] localhost:5432 沒有在聽 ⇒ 不注入（PG 相關測試維持 skip）
4910 passed, 156 skipped in 59.06s
pytest_rc=0
```
基線（主控改動前親跑）：`4864 passed, 156 skipped in 36.69s`。差 +46＝`tests/utils/test_sliced_sleep.py` 44（`--collect-only` 實數 44）＋`tests/test_r100_boot_self_check.py` 2（HEAD 37 個 `def test_` → 現 39；diff 為純新增）。skipped 156→156 不變、failed 0。

### 1.2 lint-imports（`lint-imports`）
```
routing) KEPT
autoclaude must not import monorepo harness modules (consume the file contract 
instead) KEPT

Contracts: 9 kept, 0 broken.
lint_imports_rc=0
```

### 1.3 ruff（改到的 10 支 .py，不帶 --config；清單取自 `git status --short AutoClaude/`）
```
All checks passed!
ruff_rc=0
```

### 1.4 LOC（`python tools/check_loc_budget.py --json`，violations 區）
```
{'total': 17395, 'baseline': 17079, 'cap': 20438, 'total_violation': False, 'absolute_violations': [], 'tier_violations': [], 'special_violations': [], 'special_stale': [], 'root_tools_violations': []}
loc_rc=0
```
以預算工具自己的 `count_loc` 對 HEAD 與工作樹逐檔實量：auto_resume.py 254→278（+24）、config.py 199→202（+3）、verified_cli_versions.py 20→38（+18）、main.py 152→153（+1）、sliced_sleep.py（新）31。與 Developer 交件一致；auto_resume +24 超出計畫書「淨 ≤+15」（見 QA3-05）。

### 1.5 snapshot_sync
```
wexpect 未安裝，改用 subprocess 模式（部分互動提示可能無法自動回應）
[snapshot_sync] OK — Snapshot 區段 + sprint 骨架對齊一致
snapshot_rc=0
```

## 2. sliced_sleep.py 規格內突變（`mutate_qa.py`：備份→單點突變→跑 `tests/utils/test_sliced_sleep.py -n 0`→finally 一律 cp 還原→sha256 對帳；不用 checkout／restore／stash）

基準：未突變時 `44 passed in 1.29s`。

| # | 突變（唯一錨點、各一處） | 結果 | 紅的測試（`-rf` 全列） | 還原 |
|---|---|---|---|---|
| M1 | 比較方向反過來：`abs(dw - dm) > tol` → `<` | KILLED（6 failed／38 passed） | `test_a_wait_is_slept_in_slices_until_it_is_full`；`test_a_wall_clock_jump_beyond_tolerance_ends_the_wait_early`；`test_a_jump_within_tolerance_is_not_a_jump`；`test_a_partial_jump_only_shortens_the_remaining_by_the_wall_delta`；`test_a_process_stall_longer_than_the_slice_is_counted_by_the_monotonic_clock`；`TestTheHaltWaitIsSliced::test_a_wall_clock_jump_during_the_wait_resumes_early_and_says_so` | sha256 還原 OK |
| M2 | 容忍邊界：`> tol` → `>= tol` | **SURVIVED**（44 passed） | 無 | sha256 還原 OK |
| M3 | 剩餘重算拿掉：`remaining - step` → `remaining - chunk` | KILLED（4 failed／40 passed） | `test_a_wall_clock_jump_beyond_tolerance_ends_the_wait_early`；`test_a_partial_jump_only_shortens_the_remaining_by_the_wall_delta`；`test_a_process_stall_longer_than_the_slice_is_counted_by_the_monotonic_clock`；`TestTheHaltWaitIsSliced::test_a_wall_clock_jump_during_the_wait_resumes_early_and_says_so` | sha256 還原 OK |
| M4 | stop 檢查搬到 sleep 之後（`while remaining > 0:` ＋ 片尾 `if stop(): break`） | KILLED（1 failed／43 passed） | `test_a_stop_before_the_first_slice_exits_without_sleeping` | sha256 還原 OK |
| M5 | wait≤0 仍 sleep 一次（迴圈前插 `if remaining <= 0: sleep(0.0)`） | KILLED（3 failed／41 passed） | `test_a_wait_that_is_not_positive_never_sleeps[0]`／`[-1]`／`[-3600.0]` | sha256 還原 OK |
| M6 | slice 超過剩餘時不截短：`chunk = min(slice, remaining)` → `chunk = slice` | KILLED（4 failed／40 passed） | `test_a_wait_is_slept_in_slices_until_it_is_full`；`test_the_slices_always_add_up_to_the_wait_when_no_clock_jumps[1]`／`[59.5]`／`[61]` | sha256 還原 OK |

**擊殺 5／6。** 驅動器逐字輸出（節錄尾段）：
```
   FAILED tests/utils/test_sliced_sleep.py::TestSlicedSleepPure::test_the_slices_always_add_up_to_the_wait_when_no_clock_jumps[59.5]
   FAILED tests/utils/test_sliced_sleep.py::TestSlicedSleepPure::test_the_slices_always_add_up_to_the_wait_when_no_clock_jumps[61]
FINAL sha256(target)==orig: True
```

### 還原證明（逐字）
```
git diff --exit-code AutoClaude/autoclaude/utils/sliced_sleep.py   → rc=0
```
注意：該指令對本檔是**空洞證明**：sliced_sleep.py 是 untracked（`git status` 顯示 `?? AutoClaude/autoclaude/utils/sliced_sleep.py`），`git diff` 對 untracked 檔恆為空、rc 恆 0，與有沒有還原無關。故另以不依賴 index 的方式對帳（備份於**第一次突變之前**自 Developer 版本複製，驅動器開跑前再斷言 `sha256(目標)==sha256(備份)`）：
```
git diff --no-index --exit-code <備份 sliced_sleep.orig.py> AutoClaude/autoclaude/utils/sliced_sleep.py   → rc=0
4917fdecf01007225d44f94954be38d942793ccd09ac0af92cb51b2d84a9dd30  AutoClaude/autoclaude/utils/sliced_sleep.py
4917fdecf01007225d44f94954be38d942793ccd09ac0af92cb51b2d84a9dd30  .../qaw3_out/sliced_sleep.orig.py
git status --short AutoClaude/  → 與審查開始時相同的 10 個 M＋2 個 ??（無新增、無消失）
```
驅動器內另有 `atexit` 保險還原；本場未用到 checkout／restore／stash。

### 補：AST 鎖與接線鎖自己有牙嗎（記憶體內突變，零 repo 寫入）
讓「讀原始碼的 AST 測試」改讀 scratchpad 內的突變副本（pytest `-p` 外掛，改 `auto_resume_mod.__file__`／`PKG_DIR`）：

| 突變副本 | 紅的測試 |
|---|---|
| `_wait` 內改回直接 `time.sleep(wait_secs)` | `test_auto_resume_never_calls_a_sleep_function_directly`（行 323）；`test_the_real_clocks_are_what_the_service_injects`（以 `KeyError: 'wall'` 紅，非斷言訊息） |
| 加 `from time import sleep` 與裸 `sleep(0)` | `test_auto_resume_never_calls_a_sleep_function_directly`（行 324） |
| `sleep=time.sleep` 換成 `lambda s: None`（注入點消失） | `test_the_real_clocks_are_what_the_service_injects` |
| main.py 拿掉 `is_interrupted=` 接線 | `test_main_wires_the_hotkey_into_the_service` |

另獨立重驗 Developer 的 M15：外掛把 `AutoResumeService._wait` 換成「記 emit、不睡、不拒絕」後，三支改形既有測試 `3 failed in 1.17s`（`test_run_with_future_resume_waits`／`test_auto_resume_loop_waits_instead_of_burning_every_retry_at_once`／`test_the_halt_loop_really_consults_the_quota_axis`）；同三支不加外掛 `3 passed in 0.42s`。

### 補：覆蓋率（本機無 coverage／pytest-cov；自寫 stdlib settrace，`qa_cov.py`）
```
COVERAGE sliced_sleep.py: 28/28 executable lines = 100.0% ; missed=[] ; pytest_rc=0
```
弧觀測：`if slice_seconds <= 0`（41／42 兩向）、`while`（44／54 兩向）、`if jump`（50／52 兩向）皆走過。（Developer 報 29/29，我量 28/28：可執行行定義不同，皆 100%，無分歧。）

## 3. 拒絕長睡路徑的端到端（我自己寫的 `qa_e2e_refusal.py`，不依賴 Developer 的測試檔）

設計：真 `FileStateRepository`（tmpdir 內真 `*.checkpoint.json`）、**出廠預設** `max_inprocess_wait_seconds=7200` 不改、`resume_delay_minutes=180`（等待≈10800s）、`time.sleep` 全程替身（A 段若被呼叫即拋 AssertionError）、Kernel 為每次都回 halted 的替身、不碰真 claude／真額度端點／真工作樹（main 段另替身 executor／kernel／開機自檢／額度量測／救援，cwd 切到 tmpdir）。

**第一次執行 1 項 FAIL＝我自己腳本的斷言寫錯**（`schedule_resume` 內部會再 `save_checkpoint` 一次，事件序列出現兩次 `save_checkpoint:after`，我的「恰四個事件」比對過嚴）；實際事件順序本來就對。修斷言為「首次出現序」後第二次執行 ALL PASS。兩次輸出皆留檔：`qaw3_out/step4_e2e.txt`（第一次）、`qaw3_out/step4_e2e_run2.txt`（第二次）。第二次關鍵事件序列（逐字）：
```
  events:
    ('save_checkpoint:before', False)
    ('save_checkpoint:after', True)
    ('save_checkpoint:before', True)
    ('save_checkpoint:after', True)
    ('schedule_resume', '2026-10-10T03:32:13')
    ('_wait:enter', 'halt', 10800, True, (1, '2026-10-10T03:32:13'))
    ('_wait:return', 'external_resume_required')
```
第二次逐字結果：
```
== A. halt 路徑（resume_delay_minutes=180 ⇒ 等待≈10800s > 預設 7200s；time.sleep 若被呼叫即炸）
  [PASS] production default max_inprocess_wait_seconds 未被動過 == 7200
  [PASS] (b) 型別是 KernelResult
  [PASS] (b) success is False
  [PASS] (b) halted is True
  [PASS] (b) reason == external_resume_required  ⇐ 'external_resume_required'
  [PASS] time.sleep 一次都沒被呼叫  ⇐ []
  [PASS] Kernel 只跑 1 次（拒絕後不續跑）  ⇐ 1
  [PASS] (a) 事件順序（首次出現）：save_checkpoint → schedule_resume → _wait:enter → _wait:return  ⇐ ['save_checkpoint:before', 'save_checkpoint:after', 'save_checkpoint:before', 'save_checkpoint:after', 'schedule_resume', '_wait:enter', '_wait:return']
  [PASS] (a) 進入 _wait（拒絕判斷）當下 checkpoint 檔已在磁碟且含 scheduled_resume_at  ⇐ ('_wait:enter', 'halt', 10800, True, (1, '2026-10-10T03:32:13'))
  [PASS] (a) 拒絕返回後檔案仍在磁碟  ⇐ /var/folders/ld/fkzj758537q6sf9dgzdw83zr0000gn/T/tmpdsqkdmm6/ck/01_simple_2_step.checkpoint.json
  [PASS] 磁碟 checkpoint step_idx==1 且 scheduled_resume_at≈now+180m  ⇐ (1, '2026-10-10T03:32:13')
  [PASS] log 含「需外部續跑」且標「已落地」
  [PASS] total_wakes == 0（沒開始的等待不記成喚醒）  ⇐ {'total_wakes': 0, 'halt_resumes': 0, 'evolution_restarts': 0, 'checkpoint_resumes': 0, 'esc_f12_resumes': 0, 'manual_resumes': 0, 'failed_emits': 0, 'total_wait_seconds': 0.0, 'last_wake_at': None, 'last_scheduled_resume_at': None, 'wake_kinds': []}
== A2. 邊界（注入剩餘秒數；sleep 為不推進時鐘的替身）
  [PASS] 剩餘 7200.0s：refused == False（reason='halted'，sleep 呼叫 120 次，加總 7200）
  [PASS] 剩餘 7200.001s：refused == True（reason='external_resume_required'，sleep 呼叫 0 次，加總 0）
  [PASS] 剩餘 7199.0s：refused == False（reason='halted'，sleep 呼叫 120 次，加總 7199）
== B. checkpoint 續跑路徑（既有 checkpoint 排程在 3 小時後）
  [PASS] (b) halted/success/reason  ⇐ (True, False, 'external_resume_required')
  [PASS] Kernel 沒被啟動  ⇐ 0
  [PASS] sleep 零次  ⇐ []
  [PASS] (a) checkpoint 位元組完全未變（外部續跑者拿到的就是原檔）
  [PASS] 結果帶 scheduled_resume_at 與 completed_steps=1  ⇐ ('2026-10-10T03:32:13', 1)
  [PASS] log「需外部續跑」且標「已落地」
  [PASS] total_wakes == 0
== C. main() 入口 rc（真 AutoResumeService＋真 FileStateRepository；只替身 executor／kernel／開機自檢／額度／救援）
  [PASS] main() 在「剩餘 > 上限」情境回 rc == 1  ⇐ rc=1
  [PASS] 該情境 Kernel 只跑 1 次、time.sleep 0 次  ⇐ calls=1 slept=[]
  [PASS] 該情境 log 有「需外部續跑」
  [PASS] main 的結束 log 帶 reason=external_resume_required
  [PASS] 對照組：等待 60s（≤上限）→ 照睡後續跑成功，main() rc == 0  ⇐ rc=0 calls=2 slept_sum=59.554877
RESULT: ALL PASS
e2e_rc=0
```
對應規格三項：
- (a) checkpoint 檔先落盤：進入拒絕判斷（`_wait` 入口）當下，磁碟上已有 `01_simple_2_step.checkpoint.json`，內含 `step_idx=1`、`scheduled_resume_at`；拒絕返回後檔案仍在；B 段（續跑路徑）檔案位元組在拒絕前後完全相同。
- (b) `KernelResult`：`halted=True`、`success=False`、`reason='external_resume_required'`；Kernel 只跑 1 次（續跑路徑 0 次）；`time.sleep` 0 次；`total_wakes==0`。
- (c) `python -m autoclaude` 入口：`main.py:254` 為 `return 0 if result.success else 1`；實跑 `main()`（真 AutoResumeService＋真 FileStateRepository）在「剩餘>上限」回 **rc=1**，結束 log 帶 `reason='external_resume_required'`；對照組（等待 60s≤上限）照睡後續跑，**rc=0**（可證 rc=1 來自拒絕，不是組裝假象）。
- 邊界（注入剩餘秒數）：剩餘 `7200.0`→不拒絕（睡 120 片、加總 7200）；`7200.001`→拒絕；`7199.0`→不拒絕。即「`>` 上限才拒絕」的 `>` 方向正確。

拒絕路徑的 log 順序（逐字，`qaw3_out/step4_loglines.txt`）：
```
INFO 檢查點已儲存: /var/folders/ld/fkzj758537q6sf9dgzdw83zr0000gn/T/tmpcpv_sl_x/01_simple_2_step.checkpoint.json | step_idx=1 [T02] token=93.0%
INFO AutoResumeService | 已存 token HALT checkpoint（step_idx=1, peak=93%）
INFO 已載入檢查點: step_idx=1 [T02]，儲存於 2026-10-10T00:43:11
INFO 檢查點已儲存: /var/folders/ld/fkzj758537q6sf9dgzdw83zr0000gn/T/tmpcpv_sl_x/01_simple_2_step.checkpoint.json | step_idx=1 [T02] token=93.0%
INFO AutoResumeService | AUTO_RESUME #1/1 | 等待 10799s 後繼續
INFO 已載入檢查點: step_idx=1 [T02]，儲存於 2026-10-10T00:43:11
ERROR AutoResumeService | 需外部續跑：需等 10799s > max_inprocess_wait_seconds=7200s ⇒ 拒絕行程內長睡（checkpoint 已落地）；請屆時由 OS 排程器／根層哨兵續跑
```

## 4. 三支改形既有測試＋boot self check：舊斷言 vs 新斷言

| 測試 | 舊斷言（HEAD） | 新斷言 | 判定 |
|---|---|---|---|
| `tests/core/test_auto_resume.py::TestRunWithScheduledResume::test_run_with_future_resume_waits` | `result.success is True`；`mock_sleep.call_count == 1`；`mock_sleep.call_args[0][0] > 60` | `result.success is True`；`slices` 非空；`max(slices) <= cfg.token_guard.sleep_slice_seconds`；`sum(slices) > 60` | **等價改形**（門檻 60 不變；「恰好一次」改為「每片 ≤ slice」）。單測層級少了「恰好一次」那道上界：我以記憶體內「等待執行兩次」突變實測，這支 **PASS（存活）**，舊斷言（`call_count==1`）會紅。但同一突變（只動 checkpoint_resume 路徑）被既有 `tests/core/test_auto_resume_metrics.py::TestAutoResumeServiceMetricsProperty::test_run_with_future_checkpoint_records_metrics_within_expected_range` 擊殺（`1 failed, 224 passed`，範圍＝新檔＋8 支 auto_resume 相關既有檔，共 9 檔 225 案）⇒ 套件層級偵測力未降。依 brief「放寬即 P2」字面這是輕微放寬，我判 **P3（QA3-04）**，理由與一行補法見 §7；主控從嚴可升 P2 |
| `tests/core/test_auto_resume_halt_persist.py::test_auto_resume_loop_waits_instead_of_burning_every_retry_at_once` | `len(slept) >= 3`；`all(s > 1000 for s in slept)` | `waits`＝`sliced_sleep` 每次呼叫的 wait 引數；`len(waits) >= 3`；`all(w > 1000)`；`sum(slept) > 1000 * len(waits)` | **等價且略收緊**（多一道實際睡眠量對帳）。雙倍等待突變下新舊皆 PASS（舊斷言也無上界）⇒ 無損 |
| `tests/test_r82_quota_axis_and_shipped_defaults.py::TestAutoResumeServiceHonoursTheQuotaAxis::test_the_halt_loop_really_consults_the_quota_axis` | `slept.call_count == 1`；`5*60 < slept.call_args.args[0] <= 6*60+5` | `total = sum(各次引數)`；`5*60 < total <= 6*60+5` | **等價**（區間逐字不變；`call_count==1` 被總量上界 365 涵蓋——雙倍等待突變下 FAILED） |
| `tests/test_r100_boot_self_check.py`（+2） | — | `cli_version_verdict('2.1.295')` ⇒ `dry_run False` 且不含 `DRY_RUN_TEXT`；`verified` 文字不含 `--max-turns` | **純新增**（diff 無任何既有斷言被改）；第二支斷言前有 `assert lines`（防空清單恆真） |

三支改形測試「等待被跳過」時皆仍轉紅（記憶體內突變獨立重驗 Developer 的 M15）：`3 failed in 1.17s`；控制組 `3 passed in 0.42s`。
另：6 次重複跑（4 檔、159 案、`-n 0`）皆 `159 passed`，無時間型 flake。

## 5. 零 skip、註解掃描、DEF 存在性

```
$ git diff AutoClaude/tests | grep -n -i "skip"                       → 零命中（grep rc=1）
$ grep -n -i -E "skip|xfail|importorskip" AutoClaude/tests/utils/test_sliced_sleep.py   → 零命中（grep rc=1）
$ git diff AutoClaude/ | grep -n -i -E "skip|xfail"                    → 零命中（grep rc=1）
skipped 計數：基線 156 → 全套 156（不增）
$ git diff AutoClaude/ | grep -n -E "R2[1-9][0-9]"                     → 零命中（grep rc=1）
$ grep -n -E "R2[1-9][0-9]" AutoClaude/autoclaude/utils/sliced_sleep.py AutoClaude/tests/utils/test_sliced_sleep.py   → 零命中（grep rc=1）
新增行（tracked diff 的 + 行＋兩支新檔，共 637 行）中的 improving_ 字樣：僅 `improving_113`（19 處）；無「延後／下一輪／TODO／FIXME」
$ git diff AutoClaude/ | grep -oE "DEF-[0-9]+-[0-9]+" | sort -u      → DEF-200-205（僅出現在 main.py hunk 的既有 context 行，非新增）
新增行與兩支新檔：零個 DEF-ID
```
`DEF-200-205` 存在性：`docs/06_quality/AutoSDD_Defect_Log.md` 命中（第 161 行 DEF-200-246 列引用它）；archive 家族 `AutoSDD_Defect_Log_archive_68.md`、`AutoSDD_Defect_Log_archive_INDEX.md` 命中。
`git diff --check AutoClaude/` rc=0；兩支新檔無 CR、無行尾空白、末尾換行存在。
`config.yaml`／`config.yaml.example`：`yaml.safe_load` 與 HEAD 逐值相等（True／True），`load_config` 皆可載入，三旋鈕讀回 `60 5 7200`；把 example 內被註解的三行取消註解後亦可載入。

## 6. verified_cli_versions 三條事實（零 token，各自重現）

```
$ claude --version                       → rc=0   2.1.295 (Claude Code)
$ claude --help > file ; grep -c -- '--max-turns' file                 → 0   （grep rc=1＝零命中，與條目「不在 help」一致）
$ grep -c -- '--permission-mode' file                                  → 1
  help 內 --settings <file-or-json>／--add-dir <directories...>／--allowedTools, --allowed-tools <tools...>／
  -r, --resume [value]／--model <model>／--permission-mode <mode> 各命中 1（條目第 2 條列的六個字面全在）
  150:  --permission-mode <mode>   Permission mode to use for the session
  151-                              (choices: "acceptEdits", "auto",
  152-                              "bypassPermissions", "manual",
  153-                              "dontAsk", "plan")
$ claude --permission-mode default --version                           → rc=0   2.1.295 (Claude Code)
$ claude --permission-mode definitelynotamode --version                → rc=1
  error: option '--permission-mode <mode>' argument 'definitelynotamode' is invalid. Allowed choices are acceptEdits, auto, bypassPermissions, manual, dontAsk, plan.
```
三條與 `verified_cli_versions.py` 的 `2.1.295` 條目逐字相符；「`default` 不在 choices 內＝被接受但 help 未列出」亦屬實；註解中「PRD §4.5.4 喚醒指令範例含 `--max-turns 40` 並標 [需核對]」我對 PRD 第 1102 行（`[需核對]`）與第 1106 行（`--max-turns 40`）核對屬實。（沒有執行任何會燒 token 的 `claude -p`。）

## 7. Findings

等級口徑（沿用 R209／R210 QA 鏡慣例）：P2＝實質缺陷／對憲法偏離，判 CONDITIONAL 以上；P3＝訊息誤導或附屬缺口，只列；P4＝理論洞／已揭露限制，只登記。我的審查範圍刻意「只驗交件宣稱＋規格內突變」，沒有對 `sliced_sleep` 做對抗式變體搜尋。

### QA3-01｜P2｜出廠預設與 PRD §4.5.2／§9 逐字常數不同，且註解與測試名把來源說成 PRD／計畫書（必收條件）

- 證據（PRD 逐字）：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 第 1063 行「`sleep(min(remaining, SLEEP_SLICE_SECONDS))  # 分片，預設 30s`」、第 1064 行「`CLOCK_JUMP_TOLERANCE (120s)`」；§9 第 1851～1853 行 `SLEEP_SLICE_SECONDS=30`／`CLOCK_JUMP_TOLERANCE_SECONDS=120`／`MAX_INPROCESS_WAIT_SECONDS=7200`。
- 證據（實作）：`AutoClaude/autoclaude/utils/config.py:259-261` 預設 `sleep_slice_seconds=60`、`clock_jump_tolerance_seconds=5`、`max_inprocess_wait_seconds=7200`——只有第三個與 PRD 相同；同檔 `:256` 註解寫「（PRD §4.5.2／§4.5.5；常數住 PRD §9）」。測試 `tests/utils/test_sliced_sleep.py:412-416` `test_defaults_follow_the_plan` 釘死 60／5／7200；而計畫書 `docs/04_planning/AutoSDD_improving_113.md` §3.3 全文只出現 `7200s`（PRD），**沒有**給 60 或 5（`grep -n -i -e sleep_slice -e TOLERANCE docs/04_planning/AutoSDD_improving_113.md` 只命中旋鈕名，無預設值）。Developer 交件 §2 也沒有任何一句談及這兩個數字與 PRD 不同。
- 為什麼是 P2 而非 P3：PRD 是最高憲法（「實作沒照 PRD 做」修實作、「PRD 與實測不符」才修憲，須四方全同意）；這是兩個**預設值**對憲法的未登記偏離，外加兩處把來源講成 PRD／計畫書的敘述不實。行為無害（皆可由 config 覆寫、5s 容忍反而更靈敏），所以不是 REJECT 級；但 RTM 若記「R8＝§4.5.2 已達成」就把偏離帶進覆蓋率矩陣。
- 重現：`grep -n -e SLEEP_SLICE_SECONDS -e CLOCK_JUMP_TOLERANCE -e MAX_INPROCESS_WAIT_SECONDS docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`；`cd AutoClaude && python -c "from autoclaude.utils.config import TokenGuardConfig as T; c=T(); print(c.sleep_slice_seconds, c.clock_jump_tolerance_seconds, c.max_inprocess_wait_seconds)"` → `60 5 7200`。
- 修法二選一（主控裁決，皆小）：
  - **A 對齊 PRD**：預設改 30／120。我以記憶體內 what-if（改 `TokenGuardConfig.model_fields` 預設並 rebuild，零 repo 寫入）跑新檔＋8 支 auto_resume 相關既有檔（共 9 檔 225 案）：`3 failed, 222 passed`，紅的恰是新檔三支——`TestTheHaltWaitIsSliced::test_a_wall_clock_jump_during_the_wait_resumes_early_and_says_so`（寫死 `[60, 60]`）、`TestAnInterruptDuringTheWaitExitsGracefully::test_the_interrupt_stops_the_wait_between_slices_and_returns_a_result`（寫死 `[60, 60]`）、`TestTokenGuardSleepKnobs::test_defaults_follow_the_plan`；既有檔零影響。另 `config.yaml.example:61-62` 的示範值 60／5 同步改。
  - **B 保留 60／5 並登記偏離**：improving_113 §8／證據檔寫明理由，把 PRD §9 兩常數列為修憲候選（走四方程序）；`config.py:256` 改成不誤導的說法（例如「預設與 PRD §9 的 30／120 不同，理由見 …」）；`test_defaults_follow_the_plan` 改名為不指向「計畫書」的名稱（計畫書沒有這兩個數）。

### QA3-02｜P3｜容忍邊界 `> tol` 沒有測試釘住（M2 存活）

- 證據：§2 表 M2——`abs(dw - dm) > tol` 改 `>= tol`，`tests/utils/test_sliced_sleep.py` 44 支全綠（`44 passed in 0.44s`）。計畫書 §3.3 寫的是「差 `> tol` ⇒ 重算」。套件內其他檔用真時鐘＋不推進時鐘的 sleep 替身，不可能在恰等於 tol 處命中，所以套件層級也無人擊殺。非等價突變：恰等於 tol 時 `>=` 會多把牆鐘增量計入剩餘（多扣 tol 秒）。
- 一個可直接加的測試（對 `>`→`>=` 紅、對現碼綠）：
  ```python
  def test_a_wall_delta_exactly_at_tolerance_is_not_a_jump(self):
      clock = _FakeClock(wall_extra={1: 5.0})            # |dw − dm| == tol(5.0)：規格是 `> tol` 才算跳躍
      out = _run(clock, 120, tol=5.0)
      assert not out.clock_jump_detected and clock.calls == [60, 60]
  ```
- 已驗證該測試有牙：對現碼綠；對 M2 突變紅（突變下觀測 `clock.calls == [60.0, 55.0]`、`clock_jump_detected=True`）。驗證檔 `qaw3_out/scratch_tests/test_boundary_probe.py`（在 scratchpad，不在 repo；`2 passed in 0.20s`）。
- 不升 P2 的理由：邊界相等在真實時鐘幾乎不會精確發生；5／6 突變被擊殺、Developer 另有 M1～M15。

### QA3-03｜P3｜「等待期間按 ESC+F12 才真的有人看」在 `python -m autoclaude` 入口不成立（宣稱過頭；底層缺口為既存）

- 證據：`main()` 全檔沒有 `register`（`grep -n -i register autoclaude/main.py` → 無命中）；全 `autoclaude/` 下唯一的 `HotkeyHandler.register()` 呼叫在 `autoclaude/execution/playbook_runner.py:375`，而 `PlaybookRunner(` 在生產碼中**無任何建構點**（`grep -rn -E "PlaybookRunner\(" autoclaude` → 無命中）；`_stop_event.set`／`_on_trigger` 除 `hotkey_handler.py` 自身外也無第二個設定者。⇒ 全域熱鍵從未被註冊，`hotkey.triggered` 在 main 入口永遠為 False。W3 的接線（`is_interrupted=lambda: hotkey.triggered`）本身正確且是必要前提，但**不充分**。
- 過頭的敘述：`main.py:245-246`（「ESC+F12 在片與片之間才真的有人看…否則等待期間按熱鍵沒有任何反應」）、`config.yaml.example:61`（「片與片之間才收得到 ESC+F12」）、`sliced_sleep.py` 檔頭 ②、`auto_resume.py` 建構子 docstring（「生產路徑接 hotkey 的 triggered」）、Developer 交件 §2 第 5 點。service 層注入點與 AST 接線鎖都成立，也有牙（§2 補表）；缺的是「事件源被註冊」。
- 這是 pre-existing：唯一的 `register()` 呼叫仍住在舊 `PlaybookRunner`（`playbook_runner.py:375`），而 main.py 自己的註解寫「舊 PlaybookRunner 直連模式已於 W6 拔除」——register 隨舊路徑成為死碼，Kernel 路徑從未接上（`git log -S"hotkey.register()"` 只指到 `0cda8aa6` 一個 commit，沒有「後來被刪」的歷史證據；以上是現況靜態事實，不是回溯歸因）。不在 W3 修，但 W3 不得把它寫成已成立。建議：把上述敘述改成「注入點已接；全域熱鍵是否被註冊屬既存缺口（main() 未呼叫 register；macOS 的 keyboard 套件另需 root）」，並在 §8 誠實劃界登記；是否立 DEF 由主控裁。

### QA3-04｜P3｜`test_run_with_future_resume_waits` 單測層級少了「恰好一次」的上界（輕微放寬；套件層級偵測力未降）

- 證據：見 §4 第一列。舊 `call_count == 1` 對「等待被執行兩次」會紅；新斷言只有下界 `sum(slices) > 60`，記憶體內「等待執行兩次」突變下這支 PASS。同一突變只動 checkpoint_resume 路徑時，被既有 `tests/core/test_auto_resume_metrics.py::TestAutoResumeServiceMetricsProperty::test_run_with_future_checkpoint_records_metrics_within_expected_range` 擊殺 ⇒ 套件整體沒有失去偵測力，故不計 P2。依 brief「放寬即 P2」字面主控可升級；一行補法：把 `assert sum(slices) > 60` 收成 `assert 295 < sum(slices) <= 305`（與新檔 `test_control_the_same_wait_at_or_below_the_cap_is_slept_not_refused` 的 `295 < sum <= 301` 同尺）。
- 重現：`qaw3_out/plug/qa_doublewait_plugin.py`（全路徑雙倍等待）與 `qa_doublewait_ck_plugin.py`（僅 checkpoint_resume 路徑），以 `PYTHONPATH=…/qaw3_out/plug python -m pytest -p <外掛名> -n 0 -q <測試>` 執行。

### QA3-05｜P3｜auto_resume.py 淨 +24，超出計畫書「淨 ≤ +15」（Developer 已自陳）

- 證據：§1.4（預算工具自己的 `count_loc`：254→278）；tier 為 service ≤500，無任何 violations。構成與理由見 Developer 交件 §2 第 9 點（`_wait` 約 14 行＋import 3＋建構子 2＋續跑路徑結果 4）。這是計畫書落點與實況的差，不是閘門違規；請主控在 §4／§8 以實測數字登記，或接受。
- 同類既存舊註解：`auto_resume.py:16` 檔頭「行數 ≤ 250（行數預算 CI 強制）」修前 254、修後 278，與現行 tier（≤500）不符——非 W3 引入（P4），順手訂正或維持皆可。

### QA3-06｜P4｜拒絕長睡時磁碟 checkpoint 的 `scheduled_resume_at` 不是額度 resets_at（Developer §2 第 10 點已自陳；我實測確認）

- 證據：`qaw3_out/qa_quota_refusal_ck.py`——額度軸量到 3 小時後 reset、`resume_delay_minutes` 為出廠 30：拒絕後磁碟 checkpoint 逐字 `scheduled_resume_at = 2026-10-10T01:12:00 → now+30.0 min`，而 refusal 的依據是 ~180 分鐘；唯一帶正確等待時間的是 log（「需等 10800s」）——不可機讀。外部續跑者若依 checkpoint 排程會早 ~150 分鐘重啟，再 halt／再拒絕一次。
- 附帶：halt 路徑的拒絕結果 `scheduled_resume_at=None`（逐字 `{'success': False, 'halted': True, 'reason': 'external_resume_required', 'scheduled_resume_at': None, 'halt_step_idx': 1, 'completed_steps': 1, 'total_steps': 2}`），續跑路徑的拒絕結果卻帶 `sched`——兩條路徑的結果欄位不對稱（沿用 R81 既有「Kernel 路徑 result.scheduled_resume_at 恆 None」，非 W3 引入）。
- 處置：已揭露，建議納入 §8 誠實劃界與 improving_114 候選（拒絕時把 `scheduled_resume_at` 改寫成 now＋等待，或另存 `external_resume_at`）。W3 規格只要求「checkpoint 已落＋非零 rc＋明示需外部續跑」，三項皆成立，故不判缺陷。依根 CLAUDE.md〈額度哨兵〉的描述，哨兵巡邏讀的是 Claude Code 逐字稿、不是引擎 checkpoint；是否另有外部續跑者消費這份 checkpoint 我沒查（brief 禁讀根層 `tools/`），因此本項沒有暴露證據，只登記。

### QA3-07｜P4｜`Field(ge, le)` 只有 slice 有上界

- 證據：計畫書 §3.3 寫「`Field(ge, le)`」；`config.py:260-261` 的 `clock_jump_tolerance_seconds`（`ge=1`）與 `max_inprocess_wait_seconds`（`ge=60`）沒有 `le`。把前者設成極大值＝關掉時鐘跳躍偵測，把後者設成極大值＝關掉拒絕長睡；兩者目前由 config 完全可控、無護欄。屬規格字面差，建議補上界（例如 tolerance ≤ 3600、max_inprocess ≤ 86400，與 `resume_delay_minutes le=1440` 同量級），或在註解說明「刻意不設上界」。

### QA3-08｜P4｜拒絕前的 INFO 行字面矛盾

- 證據：§3 的 log 序列——先 `INFO … AUTO_RESUME #1/1 | 等待 10799s 後繼續`，緊接 `ERROR … 需外部續跑 … 拒絕行程內長睡`。INFO 行在 `_wait` 做拒絕判斷之前就印了。ERROR 行清楚，不影響判讀；純措辭。續跑路徑同形（`checkpoint scheduled_resume_at 等待 %.0fs`）。

### QA3-09｜P4｜驗證方法備註：`git diff --exit-code` 對 untracked 新檔是空洞證明

- brief 要求以 `git diff --exit-code AutoClaude/autoclaude/utils/sliced_sleep.py` 證明還原；該檔為 `??`，此指令恆 rc=0。本場另以 `git diff --no-index --exit-code <備份> <檔>`＋sha256 對帳（§2）。建議日後對「新增未追蹤檔」的突變審查一律用後者（或先 `git add -N`——那是寫 index 的 git 寫入，本場不做）。

## 8. 誠實劃界（我沒做／做不到的）

- 沒有讓機器真的睡眠：單調鐘「睡眠期間是否計時」的平台行為仍只依文件（與 Developer 相同），演算法對兩種行為都成立但未實機驗。
- 沒有跑根層全套、沒有讀根層 `tools/`（brief 明令；我跑的 `tools/check_loc_budget.py`／`tools/snapshot_sync.py` 是 `AutoClaude/tools/` 下 AutoClaude 自己的腳本。前者的非阻塞 WARN 區會列出根層檔案餘裕，與 W3 無關，我未評論、未納入本審查）；表②指紋回填、ONBOARDING §7 基線數字（4864→4910）仍待收尾單人窗口，W3 未動。
- 沒有對 `sliced_sleep` 做超出規格的對抗式變體搜尋；突變僅 6 個，另加 4 個 AST／接線突變與 3 個服務層記憶體內突變（皆零 repo 寫入）。
- Windows／PS 5.1：W3 純 Python、無路徑分隔符或 shell 依賴，但本場只在 macOS 驗。
- 我的 E2E 以 `time.sleep` 替身代替「注入式時鐘」做「不真睡」；邊界另以注入 `resume_clock_seconds_until` 驗，沒有注入 `time.time`／`time.monotonic`（全域替換會污染 logging），純函式層的注入式時鐘覆蓋由 Developer 的 44 支與我的突變實驗負責。
- 我第一次跑 E2E 有一項 FAIL 是我腳本的斷言過嚴（見 §3）；已訂正並留兩次輸出，沒有隱瞞。

## 〈T-2 W3 SD／Architect 鏡〉（review_w3_sd_113.md）

# SD／Architect 唯讀審查鏡報告 — W3 引擎無人值守硬化包（AutoSDD_improving_113 §3.3）

審查者：SD／Architect 鏡（Sonnet）｜基準：HEAD 93929947 ＋ 工作樹（AutoClaude/ 10 支修改＋2 支新檔）｜2026-10-10

範圍與紀律聲明
- 只審 AutoClaude/。未讀、未評論 W1（tools/ 工作樹變更、.env.example）。
- 為回答「下游有沒有消費者」（任務書第 3 題），只對 **HEAD tracked 內容**跑 `git grep`（tools/、.claude/），並跑了 CLAUDE.md 列為「現查」的唯讀零 token 探針 `tools/probe/reset_window_distribution.py`（輸出落 scratchpad）。
- 未改任何 repo 檔、未做任何 git 寫入、未跑根層 run_root_unittests.py。只動到 gitignored 快取（lint-imports／ruff）。最終 `git status --short --untracked-files=all` 與開場相同（無新增 tracked／untracked 檔）。
- 所有「重現」腳本都在 scratchpad：`/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/w3sd/`。

## VERDICT：CONDITIONAL（條件＝SD3-01、SD3-02、SD3-03、SD3-04）

實作本體（分片休眠純函式、兩處等待改走它、拒絕長睡、設定三欄、CLI 清單、44＋2 測試）**與規格字面相符（偏離與缺口逐條列在 §1 表）、測試真有牙、架構紅線全過**；我沒有找到實作層的 P1／P2（錯誤決策＋暴露證據）。嚴重度採任務書口徑：P2 須修／P3 應修／P4 只登記。
四個條件都是「文件／訊息／小修」級，其中 **SD3-01 是計畫書前提的缺口（需主控裁決）**，不是 Developer 偏離：規格寫「交棒由根層哨兵承接」，但 HEAD 上沒有任何元件認得 `external_resume_required`、也沒有任何元件會重啟 `python -m autoclaude`；而實測 3 個真實額度 episode 有 2 個超過 2 小時上限。

---

## 0. 零信任重現（我自己跑的；數字不是轉述 Developer）

| 項 | 指令（皆在 AutoClaude/ 下、根 .venv、unset AUTOSDD_PARALLEL_TESTS） | 逐字結果 |
|---|---|---|
| import-linter | `PYTHONUTF8=1 lint-imports` | rc=0；尾行 `Contracts: 9 kept, 0 broken.` |
| ruff（10 支 .py 整檔） | `ruff check --no-cache <10 files>` | rc=0；`All checks passed!` |
| LOC | `python tools/check_loc_budget.py` | rc=0；`total=17395 baseline=17079 cap=20438 violations=0 (absolute=0 tier=0 special=0 special_stale=0 root_tools=0 total=0)`；本包 5 檔不在 SPECIAL／ROOT-TOOLS 警告清單 |
| LOC Δ（用 repo 自己的 `count_loc`，HEAD vs 工作樹） | scratch 腳本 | auto_resume.py 254→278（**+24**）；config.py +3；verified_cli_versions.py +18；main.py +1；sliced_sleep.py 新檔 31 |
| 新測試＋boot self check | `pytest tests/utils/test_sliced_sleep.py tests/test_r100_boot_self_check.py -q -p no:cacheprovider` | `86 passed in 1.76s`（新檔 44 ＋ boot 2） |
| 8 支相關檔 | Developer 同一份清單 | `181 passed in 11.31s` |
| 全套 | `pytest tests/ -q -p no:cacheprovider`（預設 addopts＝xdist） | `4910 passed, 156 skipped in 39.90s`（與 Developer 數字相同） |
| 抖動 | 新檔連跑 5 次 | 5/5 `44 passed` |
| 行覆蓋 | 自寫 `sys.settrace`（本機無 coverage／pytest-cov） | `COVERAGE sliced_sleep.py: 28/28 = 100.0%`（行覆蓋；無分支覆蓋工具） |
| snapshot | `python tools/snapshot_sync.py --check` | rc=0 `OK — Snapshot 區段 + sprint 骨架對齊一致` |
| 空白／EOL | `git diff --check -- AutoClaude`；新檔 CR 計數 | rc=0；6 檔 CR=0；新檔無行尾空白 |
| config 等價 | yaml.safe_load(HEAD) vs 工作樹 | config.yaml／config.yaml.example 兩檔 `parsed-equal-to-HEAD = True`（只改註解） |
| CLI 版本 | `claude --version` | rc=0；`2.1.295 (Claude Code)` |
| `--max-turns` | `claude --help > f; grep -c -- '--max-turns' f` | `0`（help 共 311 行） |
| help 旗標 | 逐一 `grep -c` 六個字面 | `--settings <file-or-json>`／`--add-dir <directories...>`／`--allowedTools, --allowed-tools <tools...>`／`-r, --resume [value]`／`--model <model>`／`--permission-mode <mode>` 各 1 |
| permission-mode 正面 | `claude --permission-mode default --version` | rc=0；`2.1.295 (Claude Code)` |
| permission-mode 負面對照 | `claude --permission-mode definitelynotamode --version` | rc=1；`error: option '--permission-mode <mode>' argument 'definitelynotamode' is invalid. Allowed choices are acceptEdits, auto, bypassPermissions, manual, dontAsk, plan.`（`default` 確實不在清單內，與 verified 文字一致） |
| 清單判決 | `read_cli_version()`＋`cli_version_verdict()` | `'2.1.295'`／`(False, 'CLI 版本 2.1.295 在已驗證清單內（核實項 3 條）')` |

---

## 1. 設計符合性（規格 §3.3 ＋ RTM 逐條對 diff）

| 規格條目 | 實作位置 | 判定 |
|---|---|---|
| `sliced_sleep(wait, slice_s, tol_s, *, wall, mono, sleep, stop) -> SleepOutcome` | sliced_sleep.py:34-39（參數名較長、位置同形）；`SleepOutcome` NamedTuple 4 欄 | 符合 |
| 每片比較 wall／mono 增量差 > tol ⇒ 重算剩餘；stop ⇒ 提早回 | sliced_sleep.py:43-53 | 符合（向前跳＝重算；向後跳＝忽略，見 §5 第 4 題與 SD3-04） |
| `auto_resume.py` 兩處改走它 | :234（checkpoint_resume）、:296（halt）→ `_wait` :312-327 → :323 | 符合；AST 鎖 test_sliced_sleep.py:372-392 |
| >max_inprocess ⇒ 拒絕長睡、rc 非零、checkpoint 已落 | :314-321；rc 由既有 main.py:254 `return 0 if result.success else 1` | 符合（「rc 非零」只被 `result.success is False` 間接證明，見 SD3-08） |
| `TokenGuardConfig` 三欄 `Field(ge, le)`、帶預設 | config.py:259-261 | **部分**：只有 slice 同時有 ge／le；tol、max_inprocess 無 `le`（SD3-07，P4） |
| `verified_cli_versions.py` 補 2.1.295，只寫零 token 事實，`--max-turns` 不得寫存在 | verified_cli_versions.py:41-58；:34-40 誠實劃界註解在 `verified` 之外 | 符合（三條皆重現，見 §0） |
| LOC：sliced_sleep ≤45／auto_resume 淨 ≤+15／config +3 欄／verified +25 | 31／**+24**／+3／+18（diff +25 行） | auto_resume 超 +9：**可接受**（理由見 §4 #1） |
| `.importlinter` 9 kept 0 broken | 重現 | 符合 |
| checkpoint 零新欄 | `git diff` 無 checkpoint_manager／models 變動 | 符合（沒有新欄；SD3-02 的建議修法也只改既有欄位的值） |
| 測試 (1)～(6) | (1)(2)(5)＝TestSlicedSleepPure；(3)＝TestALongWaitIsRefusedInProcess；(4)＝TestAnInterruptDuringTheWaitExitsGracefully ＋ 純函式 stop 三測；(6)＝TestWiringLocks:372 | 符合 |
| coverage ≥90% | 100%（28/28 行） | 符合（行覆蓋） |
| test_r100_boot_self_check +2 | :263、:271 | 符合 |
| RTM R8（§4.5.2） | sliced_sleep ＋ 上列測試 | 符合 |
| RTM R9（§4.5.5 >2h 不行程內硬等） | 「不行程內硬等」✓；「交棒」✗（HEAD 無消費者） | **部分**（SD3-01、SD3-02） |
| RTM R10（R-6.2-2 清單含 2.1.295） | 清單＋2 測 | 符合 |
| 預設值（規格未寫數字；PRD §6 設定區塊 9 有） | 60／5／7200 vs PRD 30／120／7200 | **偏離**（SD3-03） |

---

## 2. 架構紅線

| 紅線 | 結果 | 證據 |
|---|---|---|
| utils 不得 import core／infra | ✓ | sliced_sleep.py 只 import `logging`／`collections.abc`／`typing`；`test_utils_sliced_sleep_imports_nothing_from_core_or_infra`（:404）；lint-imports 9/0 |
| auto_resume 不得反向 import 根層 tools/ | ✓ | 新 import 僅 `collections.abc.Callable`／`dataclasses.replace`／`...utils.sliced_sleep`（auto_resume.py:26-27、:35）；契約 9「autoclaude must not import monorepo harness modules」KEPT |
| core 不依賴 execution／infra | ✓ | core→utils 是既有方向（已 import `utils.resume_clock`） |
| playbook_runner.py thin facade 未受影響 | ✓ | `git status` 無 execution/ 檔變動；注意其內另有舊直連路徑第三處 `time.sleep(wait_secs)`（:430），production 零建構點，見 SD3-11 |
| plugins 互不 import | ✓ | 無 plugin 檔變動 |
| 無新外呼／無新持久化欄位 | ✓ | — |

---

## 3. Findings

### SD3-01｜P3（**主控裁決點**）｜拒絕長睡的「交棒」在 HEAD 無消費者；預設上限讓實測多數 episode 改為退出；註解過度宣稱
**證據**
1. 沒有任何元件認得新 reason：`git grep -n -I "external_resume_required" HEAD -- .` → rc=1、0 行；`interrupted_during_wait` 同為 rc=1、0 行（工作樹內只有 auto_resume.py 與 test_sliced_sleep.py 命中）。
2. 沒有任何根層元件會重啟引擎：`git grep -n -I -e "-m autoclaude" -e "python -m autoclaude" HEAD -- tools .claude` 只有 2 行，皆為 `tools/tests/test_windowsapps_guard_cross_consistency.py:1335,1354` 的註解；`git grep -n -I -i -e scheduled_resume_at -e PlaybookCheckpoint -e load_checkpoint -e '["autoclaude"' -e "'autoclaude'" HEAD -- tools .claude` 只有 3 行（bootstrap 安裝目標＋2 行 bootstrap 測試），**無任何一行消費引擎的 checkpoint**。哨兵讀的是 Claude Code 逐字稿、續的是 `claude -r`，不是 `python -m autoclaude`。
3. 實測分佈（CLAUDE.md 列的現查探針，非構造語料）：`python tools/probe/reset_window_distribution.py` → 逐字稿母體 743 支、相異撞線 episode 3 個、`episode hit→reset min=54.5 / median=189.6 / max=224.2 分鐘`（全部：[54.5, 189.6, 224.2]）。**3 個裡有 2 個 >120 分鐘（7200s）**。（n=3 很小；且引擎在 95% 就 halt，等待量是 ≥ hit→reset，所以 2/3 是偏低估計。auto_resume.py:366-368 的 R82 註解也自述窗長 min 0.5／max 253 分。）
4. 現行預設 `max_inprocess_wait_seconds=7200`（config.py:261）下，這類 halt 修前＝行程內等到 `resets_at`（機器不睡就自癒）；修後＝`rc=1` 退出，無人自動續跑。我用同一份 `AutoResumeService`、額度軸量到 4 小時後 reset 實跑（`refusal_sim_quota.py`），stdout 逐字：
   `[ERROR] autoclaude.core.services.auto_resume: AutoResumeService | 需外部續跑：需等 14400s > max_inprocess_wait_seconds=7200s ⇒ 拒絕行程內長睡（checkpoint 已落地）；請屆時由 OS 排程器／根層哨兵續跑`，stderr 0 byte。
5. 過度宣稱：config.yaml.example:58-60「等待 > max_inprocess_wait_seconds 時引擎拒絕行程內硬等、以非零 rc 結束，**由 OS 排程器／根層哨兵於該時刻後續跑**」把一個尚不存在的機制寫成已存在的事實（auto_resume.py:318 的 ERROR 訊息是祈使句「請屆時…續跑」，可以接受；問題在 example 註解的陳述句）。這個主張並非本包才有（auto_resume.py:374-377 的 R82 註解就寫「OS 級喚醒由根層哨兵負責」），但本包把它從「行程死了」的假想情境變成「每次 >2h 都會走」的常態路徑，使它第一次承重。
6. PRD §4.5.5（:1112-1126）要求 >MAX_INPROCESS 時 ①凍結 ②向 OS 排程器註冊一次性喚醒 ③Daemon 退出 ④到時重啟→INIT 掃描 state.json→驗證額度→RESUMING；引擎側目前只有 ①③。

**重現**：上列 git grep 三條與探針（輸出落 `w3sd/grep_head_*.txt`、`w3sd/reset_dist.txt`）；`python w3sd/refusal_sim_quota.py`。
**判準**：R9 的「不行程內硬等」已達成；規格 Architecture_Design_Review Q1 的「交棒由根層哨兵承接」在 HEAD 不成立。
**分級說明（透明）**：我把它評為 P3 而非 P2，是因為它是計畫書前提缺口、不是 Developer 偏離，且處置是「裁決＋登記＋文字訂正」而不是改核心邏輯；但它**有暴露證據**（真實 episode 3 取 2 超限），若主控既不選 B 也不登記 §8，就應升為 P2。
**建議處置（主控擇一並落檔 improving_113 §8）**
- A（建議）接受 PRD 預設值，誠實劃界登記「引擎路徑 >2h 的等待＝rc=1＋checkpoint＋ERROR log，需外部續跑者處理；HEAD 無自動消費者」，並把 config.yaml.example:58-60 的陳述改成「須由外部續跑者（OS 排程器／人工）處理；目前尚無自動消費者」。候選：improving_114 登記「根層消費者」。
- B（保留 R82 行為直到消費者落地）出廠 `config.yaml` 暫時明寫 `max_inprocess_wait_seconds: 15240`（≥ R79 實測 max 253.2 分）；程式預設仍是 PRD 的 7200；純設定層、零程式碼；`le` 沒設上限所以合法。
- C（本輪另派消費者）超出 W3 範圍，不建議。
- 無論 A／B，example 註解過度宣稱都要改。

### SD3-02｜P3｜拒絕路徑寫出的 checkpoint 喚醒時刻與 log 說的不一致（額度軸必然不一致）；halt 路徑的結果物不帶喚醒時刻
**證據**
- 額度軸拒絕時 checkpoint 內 `scheduled_resume_at` 是 `resume_delay_minutes` 推算值（`_persist_halt_checkpoint`，auto_resume.py:454-462），不是額度 `resets_at`。`refusal_sim_quota.py` 逐字：`CHECKPOINT.scheduled_resume_at = 2026-10-10T01:10:41 -> 距今 1799 秒（log 說需等 ~14400 秒）`、`RESULT: False True external_resume_required result.scheduled_resume_at= None`。
- 額度軸要觸發拒絕就必須 wait>7200s，而 checkpoint 的排程恆為 resume_delay（預設 1800s）⇒ **額度軸上每一次拒絕，checkpoint 的喚醒時刻都比真實早**（context 軸上兩者相等，無此問題）。
- 同一路徑的 checkpoint_resume 分支結果帶 `scheduled_resume_at=sched`（:237），halt 分支的 `replace(result, reason=why)`（:298）不帶 ⇒ 兩種拒絕結果物形態不一致。
- ADR-XPLAT-005:201 的設計意圖是「95% 的動作＝走既有 halt 路徑（存 checkpoint＋scheduled_resume_at），但**恢復時刻改用 endpoint 的 resets_at**，取代固定的 resume_delay_minutes=30」；R82 實作只把 sleep 秒數改成 resets_at，checkpoint 的排程沒跟上（既存缺口，非本包引入）。本包的拒絕路徑是第一個「行程離開後只剩 checkpoint 可依賴」的出口，使這個既存缺口第一次有消費面。
**對續跑是否有害（任務書第 3 題後半）**：有害但有界。外部續跑者若以 checkpoint 為準，會在 halt 後 +30 分鐘重啟；新行程 `_resolve_start`→`has_ck and sched`→`wait_secs≈0`→直接 `kernel.run`（開機自檢只拿 band 處理整合佇列，不擋額度：boot_self_check.py:20/57、main.py:113），首步撞線→再 halt→新行程再依額度軸算出 >2h→再拒絕。代價＝每次提早重啟多燒一次嘗試；不會壞資料、會自我糾正，但「checkpoint 已落」對外部續跑者不自洽。
**判準**：R9「checkpoint 已落（可供外部續跑）」的可用性；規格沒要求寫回喚醒時刻，故 Developer 合於字面，建議補。
**建議修法（約 4 行，用既有 port，checkpoint 零新欄）**：拒絕分支內以 `self._state_repo.schedule_resume(canonical_playbook_id(path, mode=...), math.ceil(wait_secs / 60))` 把真實喚醒時刻寫回（同 :458 的 API；只改既有欄位值），ERROR 訊息加絕對 ISO 時刻，兩種拒絕結果都帶 `scheduled_resume_at`；補一支額度軸測試（checkpoint 排程距今 ≈ log 的等待秒數）。若不修，登記 §8：「外部續跑者須以 ERROR log 的等待秒數為準；提早重啟會多燒一次嘗試」。
**既存關聯（非本包、僅供主控知悉）**：同一缺口的另一個症狀——`fresh=False`（生產預設）、額度 6 分鐘後 reset、resume_delay=30 時，`double_wait_sim.py` 實測總睡 `2159 s`（360s 額度等待＋第二輪 checkpoint_resume 再補到 +30 分）而非 ADR 意圖的 ≈360s。R82 的接線鎖（test_r82…::test_the_halt_loop_really_consults_the_quota_axis）建構的 service 沒有 state_repository ⇒ 沒有 checkpoint、沒有第二輪等待，所以沒看見它。

### SD3-03｜P3｜三個預設值與 PRD §6 設定區塊 9 不同；註解把常數歸屬寫成「PRD §9」（章節不存在該內容）；測試名說「follow the plan」但計畫書沒寫數字
**證據**
- PRD :1851-1853（`## 6. 設定檔規範` 內的區塊「9. 重置、休眠與喚醒」）：`SLEEP_SLICE_SECONDS=30`、`CLOCK_JUMP_TOLERANCE_SECONDS=120`、`MAX_INPROCESS_WAIT_SECONDS=7200`；§4.5.2 偽碼 :1059-1066 亦寫「分片，預設 30s」「CLOCK_JUMP_TOLERANCE (120s)」。實作 config.py:259-261＝60／5／7200（只有 7200 對上）。
- config.py:256 註解「常數住 PRD §9」：PRD `## 9.` 是「可觀測性」（:2208）；常數住 §6 的設定區塊 9。AutoClaude/（.py／.yaml／.example）內只此一處這樣引用（`grep -rn --include='*.py' --include='*.yaml' --include='*.example' "PRD §9" AutoClaude`）。
- test_sliced_sleep.py:412-416 `test_defaults_follow_the_plan` 斷言 60／5／7200；計畫書 §3.3 只寫「PRD 7200s」，未給 slice／tol 數字。
**判準**：PRD 是最高憲法（實作與 PRD 不符＝修實作，除非 PRD 與實測不符才走修憲）。靜默偏離＋誤引章節＝可追溯性缺陷；功能影響≈無（slice 60 vs 30 只影響熱鍵反應延遲；tol 5 更靈敏且對此演算法更準，見下）。
**tol=5 合理性（任務書第 4 題）**：對**本演算法**合理，甚至比 PRD 的 120 更對——本實作是「增量帳」（只有偵測到跳躍才改用牆鐘增量），tol 同時決定「未被扣除的牆鐘多走量」的累積上界＝tol×片數。scratch 實測（`clock_scenarios.py`）：S6a 每片睡 4.9s（tol=5）→ 累積晚醒 +588 s；S6b 每片睡 119s（tol=120，PRD 值）→ +14280 s（約 4 小時）；S7 單次 100s 機器睡眠在 PRD 參數（slice 30／tol 120）下**不被偵測**、晚醒 +100 s，在實作預設（60／5）下被偵測、晚醒 +0.0 s。5 s 比 PRD 的 120 s 更適合此演算法；但這是偏離 PRD 的技術理由，必須落檔。雜訊面：兩個時鐘量同一段 sleep，排程抖動同向、`|dw−dm|` 雜訊遠小於 1 s（NTP slew ≤ 500ppm ⇒ 60s 片約 30 ms），5 s 的誤報風險可忽略，且誤報的後果也只是改用牆鐘增量（仍正確）。
**建議處置（擇一）**：(a) slice 改 30（對齊 PRD、零成本）；tol 維持 5，並在 improving_113 §8／證據檔登記「偏離 PRD §6 區塊 9 的 CLOCK_JUMP_TOLERANCE：120→5，理由＝增量帳演算法的累積誤差上界（S6b）；PRD 待下次修憲對齊」；(b) 全對齊 PRD（30／120）並把 `step` 改成無條件 `max(chunk, dm, dw)`（tol 只當診斷旗標），使 120 不損精度（需同步改 `test_a_jump_within_tolerance_is_not_a_jump` 的語意）。無論 (a)(b)：config.py:256 改「PRD §6 設定區塊 9（§4.5.2）」；`test_defaults_follow_the_plan` 改名（例如 `test_defaults_are_pinned`）或 docstring 說明數值來源。

### SD3-04｜P3（訊息誤導，一次呼叫內可恢復）｜牆鐘「倒退」的跳躍 warning 說「剩餘改以牆鐘重算」，實際並未重算
**證據**：sliced_sleep.py:48-52：`jump = abs(dw - dm) > tol` 對方向不敏感，warning 一律寫「⇒ 剩餘改以牆鐘重算」（:50-51），但 `step = max(chunk, dm, dw if jump else 0.0)`（:52）在 dw<dm 時等於 `max(chunk, dm)`＝完全忽略牆鐘（設計選擇，模組檔頭 :14-15 與 test_sliced_sleep.py:120 都明說「向後撥不延長等待」）。`clock_scenarios.py` S3 逐字：`偵測到時鐘跳躍（牆鐘 -540.0s／單調鐘 +60.0s，容忍 5.0s）⇒ 剩餘改以牆鐘重算`，同場結果 `wake -600.0s vs target`（早醒 600 秒）。
**判準**：診斷訊息要與實際動作一致（本包自己的紀律：「未確認落地」而不是謊報）。
**建議**：依方向分兩句——前跳：「剩餘改以牆鐘重算」；倒退：「牆鐘倒退，不延長等待（早醒代價＝再 halt 一次）」；補 caplog 斷言（目前 `test_a_wall_clock_jump_during_the_wait_resumes_early_and_says_so` 只斷言含「時鐘跳躍」）。

### P4（只登記；無暴露證據，不立輪）

- **SD3-05**｜P4｜`resume_delay_minutes`（config.py:251，`ge=0, le=1440`）與新上限的交互：121～1440 分鐘這段原本合法的設定自此被拒絕（大聲、rc=1，不是靜默），沒有跨欄位檢查、`resume_delay_minutes` 的註解也沒提。出廠值 30 不受影響。建議在該欄註解補一句。
- **SD3-06**｜P4｜`load_playbook` 提前（auto_resume.py:218）：僅影響 checkpoint_resume 分支——等待（≤上限，預設 2h）期間若 playbook 被改，續跑用的是等待前載入的版本（修前是等待後才載入）。halt 分支的下一輪仍在迴圈頂載入，不受影響。換到的好處（壞檔不必先睡完）更大，可接受。
- **SD3-07**｜P4｜`Field(ge, le)`：規格字面三欄都帶 ge／le，實作只有 slice 兩者齊備；tol（ge=1）、max_inprocess（ge=60）無上界。無上界讓運維可用設定關閉跳躍偵測／放寬拒絕（SD3-01 的 B 案正需要），故可接受；`test_out_of_range_values_are_rejected` 對這兩欄只測下界。
- **SD3-08**｜P4｜可被外部續跑者消費的面太窄：(a) rc=1 與其他失敗同值，沒有專用 rc（例如 EX_TEMPFAIL=75）或機器可讀行；(b) ERROR 在 **stdout**（logger console handler＝`sys.stdout`，logger.py:76）與 `logs/autoclaude.log`，**stderr 0 byte**（任務書原文說 stderr；實測不是）；(c) 拒絕時沒有任何桌面通知：NotificationPlugin 訂閱 ON_ESCALATION 與 ON_AUTO_RESUME_WAKE（notification_plugin.py:49-52），拒絕路徑兩者皆不屬於（刻意不 emit wake），無人值守時「引擎已停、需外部續跑」只留在 log；(d) `main()` 的 `0 if result.success else 1`（main.py:254）沒有任何測試直接釘住（`grep` tests 只有 test_main_build_executor.py 引用 main）。對「改派 improving_114 消費者」有用，非本輪必要。
- **SD3-09**｜P4（給收尾單人窗口）｜Developer 紀錄 §8 引用「ONBOARDING §7 基線 4864 passed／156 skipped」不見於 ONBOARDING.md（`grep -n "4864" ONBOARDING.md` rc=1）；§7 實值是 ONBOARDING.md:381「macOS **4764 passed / 222 skipped**、Windows 4736 / 172」（乾淨 venv）。表② 回填須在乾淨 venv 實量，不得照該行抄「4910／156」（那是 dev venv 數字）。另：AutoClaude/tests 位元組已變 ⇒ 表② 指紋回填為 commit 前最後一步；`AutoClaude/docs/AutoClaude_Guide.md:126-128` 的 token_guard 範例未含三新欄（任務書已劃給主控收尾）。
- **SD3-10**｜P4｜`PlaybookTask.token_guard` per-step override 的白名單來自 `TokenGuardConfig.model_fields`（playbook.py:55-70）⇒ 三個新鍵自動被接受，但引擎只讀全域 `cfg.token_guard`，寫在步驟層會靜默無效。與既有 `auto_resume`／`max_auto_resumes`／`resume_delay_minutes` 同型（既存慣例），`test_a_per_step_override_may_not_smuggle_a_typo_of_the_new_knobs`（:433）只證明白名單接受，不證明生效。
- **SD3-11**｜P4｜`execution/playbook_runner.py:430` 仍有第三處單次 `time.sleep(wait_secs)`（舊直連模式的自家 auto-resume 迴圈）。core/kernel.py:431-433 註解與 `_simple_mutations.py:52` 自述 production 零建構點（24 個建構點全在 tests/），規格只涵蓋 auto_resume 兩處、符合；但 AST 鎖只釘 auto_resume.py，若該 shim 日後被接線，單次長睡會悄悄回來。
- **SD3-12**｜P4｜R10 的兩個旁註：(a) `--max-turns` 在 PRD §4.5.4（:1106 範例，標 [需核對]）與附錄 B-10（:2610 ✅）被當成存在，2.1.295 `--help` 零命中；本包**正確地沒寫進 verified**。引擎本身不使用該旗標（`grep -rn max-turns autoclaude config.yaml*` 只命中 verified 的註解）。零 token 無法證其存在與否（`--version` 會短路未知旗標，見 verified_cli_versions.py:22-23 的既有紀錄）→ 建議證據檔登記待查，勿當 PRD 修憲題。(b) 清單加入 2.1.295 使 `dry_run` 由 True→False：其唯一生產消費者是 main.py:149 的 `cleanup_merged_worktrees(..., dry_run=dry_run)`，因此「開機空間不足」時 `git worktree remove` 會**真的執行**（只清已 --ff-only 併入者；boot_self_check.py:306-307、:247-252）。這是 R-6.2-2／G5 的設計語意，不是回歸，登記以免日後被誤報。
- **SD3-13**｜P4｜PRD §4.5.2 偽碼的 `received_signal()`（優雅退出）在規格被縮成「中斷＝hotkey」：SIGINT／SIGTERM 在等待中仍走預設處理（KeyboardInterrupt traceback／直接終止）。因 checkpoint 先於等待落盤，狀態安全；另 macOS 非 root 的 `keyboard` 套件 `euid==0` 限制使 ESC+F12 在 mac 上本來就不可用（hotkey_handler.py:37-42、:83-91 的既有說明），所以 `is_interrupted` 接線在 mac 上實質為 no-op（無害）。
- **SD3-14**｜P4｜`_wait` 的「已落地」是讀回「有某份 checkpoint」（auto_resume.py:315），不證明是**本次** halt 的：`save_checkpoint` 失敗（:440-442 只 warning）且磁碟上留有舊 checkpoint 時，ERROR 會說「已落地」。需兩個失敗同時發生；`M12` 突變已守住「完全沒有 checkpoint」那一半。若採 SD3-02 的修法，可順便把 `saved` 改為比對 `step_idx`。

---

## 4. Developer 自陳偏離逐項裁決

| # | 偏離 | 裁決 | 理由 |
|---|---|---|---|
| 1 | auto_resume 淨 +24（規格 ≤+15） | **可接受** | 我用 repo 的 `count_loc` 重量＝+24；service tier ≤500，現 278，餘裕 222；超出的部分是規格沒估進去的 `is_interrupted` 接線、checkpoint 分支的結果建構、`_wait` 內的讀回確認＋ERROR 訊息（Developer 自陳構成：import 3／建構子 2／續跑結果建構 4／`_wait` 約 14；我只獨立重量了總數 +24）；沒有把 helper 搬去新模組「搬帳」，誠實 |
| 2 | keyword-only `is_interrupted`＋main.py 一行接 `hotkey.triggered` | **可接受（且必要）** | 規格 Q3「中斷（既有 hotkey）優雅退出」與 RTM R8-(4) 要求；沒有接線則 `stop` 在生產是死碼（本 repo 最忌的「機制蓋好沒接電」）。`HotkeyHandler.triggered`（hotkey_handler.py:121）存在，`hotkey` 在 main.py:216 恆被建構、不會是 None；與 `HotkeyPlugin`「任何擁有 `.triggered` 的物件」的既有慣例同形（hotkey_plugin.py:27）。AST 鎖 :394。簽章是 keyword-only 且預設永不中斷，向後相容；唯一建構點是 main.py |
| 3 | `load_playbook` 提前到等待之前 | **可接受** | 壞檔／缺檔不必先睡完；拒絕／中斷結果才帶得出 `total_steps`。副作用見 SD3-06（P4） |
| 4 | 拒絕結果＝`KernelResult` success=False／halted=True／reason=`external_resume_required`，main 回 rc=1 | **可接受** | 不新造例外／流程；`autoclaude/` 內沒有任何以 `reason` 字串分支的消費者（`grep -rn "result.reason\|\.reason ==" autoclaude` rc=1），`.halted` 只在 auto_resume 內被讀；改 reason 不會繞過既有分支。halt 與 checkpoint 兩分支的結果物形態不一致見 SD3-02 |
| 5 | config.yaml 只加註解不加值；example 只加被註解掉的示範 | **可接受** | 與 R82 `context_patterns` 的 SSOT 先例一致；兩檔 `yaml.safe_load` 與 HEAD 逐值相等。example 的陳述句過度宣稱見 SD3-01 |
| 6 | 3 支既有測試改形 | **確認「改形不弱化」**（見 §5） | 我自己用 pytest plugin 在行程內替換 `AutoResumeService._wait`（不改 repo 檔）：`MUT=skip`（等待被跳過）→ 3 failed；`MUT=cap60`（等待被截成一片）→ 3 failed。證據 `w3sd/mut_skip.txt`／`mut_cap60.txt` |

---

## 5. 對任務書第 3～7 題的直接回答

### 第 3 題｜拒絕長睡路徑
- **checkpoint 是否真的在拒絕之前落盤**：正常路徑**是**。halt 分支：`_persist_halt_checkpoint(...)`（auto_resume.py:267-270）→ 內部 `save_checkpoint`（:435）與 `schedule_resume`（:458）→ `_freeze_is_safe()`（:277）→ `_wait("halt", …)`（:296）→ 拒絕判斷（:314）。checkpoint 續跑分支：checkpoint 是剛在 :212-214 讀到的那份（本來就在磁碟上），拒絕在 :234。端到端重現（`refusal_sim.py`）：`已存 token HALT checkpoint（step_idx=1, peak=93%）`先於 `需外部續跑…（checkpoint 已落地）`。兩個邊角：`halt_step_idx is None` 的 halt 由上游自存（既有契約）；save 失敗時退化為讀回任何既有 checkpoint（SD3-14，P4）。
- **下游消費者**：**無**（SD3-01 證據 1、2）。rc=1＋stdout／log 的 ERROR 足以讓**人**接手，不足以讓**程式**接手（無專用 rc、無機器可讀時刻、checkpoint 的時刻在額度軸是錯的，SD3-02、SD3-08）。
- **scheduled_resume_at 用 resume_delay 推算是否有害**：有害但有界，細節見 SD3-02（早醒重啟→多燒一次嘗試→再拒絕；不損資料、自我糾正）。

### 第 4 題｜時鐘跳躍演算法（`clock_scenarios.py` 實跑，fake clock）
| 情境 | 結果（wait 單位秒） |
|---|---|
| S1 機器睡眠 1800s、單調鐘**不計**睡眠（macOS `mach_absolute_time`／Linux `CLOCK_MONOTONIC`；本機 `time.get_clock_info('monotonic')`＝`mach_absolute_time()`） | 偵測到跳躍，剩餘以牆鐘扣；`wake +0.0s vs target`、90 片即結束 |
| S2 同一事件、單調鐘**計入**睡眠（Windows 常見語意） | 無跳躍旗標，`step=dm` 照實扣；`wake +0.0s vs target` |
| S3 牆鐘**倒退** 600s | 忽略（`step=max(chunk, dm)`）；`wake -600.0s vs target`＝牆鐘意義上早醒 600s；旗標亮；代價＝再 halt 一次（受 `max_auto_resumes` 約束）。設計選擇，**可接受**，文字見 SD3-04 |
| S4／S4b 差距恰＝tol／tol+0.1 | 嚴格大於才算跳躍；恰＝tol 時晚醒 +5.0s（容忍內不入帳）；+0.1 時 +0.0s |
| S5／S5b 片界 | wait=61、slice=60 → 兩片 [60, 1]；wait=60.0001 → 兩片，剩餘不會卡在 1e-12 |
| S6a／S6b／S7 容忍內多走量不入帳 | 見 SD3-03（tol=5 上界 +588s；tol=120 上界 +14280s；單次 100s 睡眠 PRD 參數下漏偵測） |
- **終止性**：`step ≥ chunk = min(slice, remaining)` ⇒ 最多 `ceil(wait/slice)` 圈；`slice<=0` 直接 `ValueError`（:40-41）；config `ge=1` 先擋；任何 sleep 替身下恰好 ceil(wait/slice) 圈（`test_a_sleep_stand_in_that_moves_no_clock_still_terminates`，:148）。
- **向前跳 vs 向後跳**：向前＝精確補回；向後＝忽略。這與 PRD §4.5.2 偽碼（每圈 `remaining = target_wall − now_wall()`，倒退會自動延長）不同——PRD 形態對「圈與圈之間」的未量到睡眠免疫，本實作（增量帳）有一條**微秒級**的縫：一片結束到下一片 `w0` 擷取之間若恰逢系統睡眠，該段不入帳。規格明寫「每片比較 wall／mono 增量差」，所以符合規格；縫的寬度與 sleep 本身相比可忽略，**可接受**。
- **機器睡眠時 monotonic 不計時**：S1／S2 證明兩種語意下演算法都對；Developer 自陳「沒有實際讓機器睡眠驗證」屬實（我也沒有）；模組檔頭與紀錄都如實標「依文件」，沒有把推論寫成已驗。
- **tol 預設 5s**：見 SD3-03（對本演算法合理；與 PRD 120 不同須落檔）。

### 第 5 題｜三支改形測試與 test_r82
| 測試 | 舊斷言 | 新斷言 | 判定 |
|---|---|---|---|
| test_auto_resume.py::test_run_with_future_resume_waits | `call_count==1`、`args[0] > 60` | 有 sleep、`max(slices) <= sleep_slice_seconds`、`sum(slices) > 60` | 下界保留（>60）、新增「分片」上界；舊的「恰一次」語意依設計不再成立 |
| test_auto_resume_halt_persist.py::…waits_instead_of_burning_every_retry_at_once | `len(slept)>=3`、`all(s>1000)` | 以 `wraps=sliced_sleep` 取每次**完整等待**：`len(waits)>=3`、`all(w>1000)`、另加 `sum(slept) > 1000*len(waits)` | 保留且加嚴（多一道加總對帳） |
| test_r82…::test_the_halt_loop_really_consults_the_quota_axis | `call_count==1`、`5*60 < args[0] <= 6*60+5` | `5*60 < sum <= 6*60+5` | 上下界逐字保留；「恰一次」依設計移除。總和上界仍擋得住「等成 30 分」（1800>365） |
- 我的突變（不改 repo、plugin 於行程內替換 `_wait`）：`MUT=skip` → `3 failed in 0.57s`；`MUT=cap60` → `3 failed in 0.50s`（三支皆紅）。**不弱化**。

### 第 6 題｜verified_cli_versions 新列
- 三條事實全部可由零 token 指令重現（§0 表）：版本字串／help 六個旗標字面各 1 次／`--permission-mode default` rc=0 且負面對照 rc=1 並印 `Allowed choices are acceptEdits, auto, bypassPermissions, manual, dontAsk, plan.`。
- **沒有把沒驗過的寫成已驗**：`--max-turns` 的零命中與「沒有實跑任何會燒 token 的呼叫、各旗標執行期語意未核實」都明寫在 `verified` 之外的註解（:34-40）與第 2 條括號內；`default` 不在 choices 清單的事實有明寫、並註明「不得當作官方承諾的公開值」。
- 與既有 2.1.223 條目「`--version` 會短路旗標檢查，不得拿它當旗標存在性憑證」不矛盾：新條目靠的是**選項值驗證**先於 `--version`，並附負面對照（非法值 rc=1），我重現了兩面。
- 鎖：`test_improving_113_the_verified_text_never_claims_the_flag_the_cli_help_lacks`（test_r100_boot_self_check.py:271；先斷言清單非空，避免恆真）。副作用與登記見 SD3-12。

### 第 7 題｜文件
- config.yaml／config.yaml.example 註解與欄位一致：範圍（1~600／>=1／>=60）與預設（60／5／7200）與 config.py:259-261 吻合；config.yaml 「刻意不寫值」與 R82 先例一致。**例外**：example:58-60 的過度宣稱（SD3-01）。
- 輪號字樣：新增行（tracked diff 145 行＋2 個新檔）對 `R2[0-9][0-9]|R1[0-9][0-9]` 零命中；只有 `improving_113`（計畫書編號，AutoClaude 的既有命名慣例，非 R211 輪號）。
- DEF-ID：新增行與新檔對 `DEF-[0-9]+-[0-9]+` **零命中**（沒有引用任何帳本不存在的 ID）。
- 章節引用：「PRD §4.5.2／§4.5.5」「PRD §4.5.4」「R-6.2-2」皆存在；**「常數住 PRD §9」錯**（SD3-03）。

---

## 6. 重現清單（scratchpad，皆唯讀）
- `w3sd/clock_scenarios.py`（純函式情境 S1～S7）、`w3sd/clock_scenarios_out.txt`
- `w3sd/refusal_sim.py`、`w3sd/refusal_sim_quota.py`（拒絕路徑端到端；看 stdout／stderr／checkpoint／result）
- `w3sd/double_wait_sim.py`（既存雙重等待取證，非本包）
- `w3sd/mut_plugin.py`（`MUT=skip|cap60`，pytest `-p mut_plugin`，PYTHONPATH 指向 w3sd）
- `w3sd/line_cov_sd.py`（stdlib 行覆蓋）
- `w3sd/grep_head_*.txt`、`w3sd/reset_dist.txt`（SD3-01 證據原檔）
- 指令摘要：`git grep -n -I "external_resume_required" HEAD -- .`（rc=1）；`PYTHONUTF8=1 lint-imports`；`python -m pytest tests/ -q -p no:cacheprovider`；`claude --version`／`claude --help`／`claude --permission-mode default --version`／`claude --permission-mode definitelynotamode --version`。

## 〈T-3 W1 SD／Architect 鏡〉（review_w1_sd_113.md）

# W1 模型角色參數化——SD／Architect 唯讀審查（improving_113）

審查者：SD／Architect 唯讀鏡（Sonnet 5.5）｜時點：2026-10-10 00:3x～01:05（本機）
基準：HEAD 93929947＋未提交工作樹。全程唯讀：未改任何 repo 檔、無 git 寫入、未跑根層全套、未打真 usage 端點、未呼叫 claude。
被審新檔指紋（`shasum` 前 12 碼，01:06 取）：`tools/lib/model_roles.py` ff8d75faa2f5｜`tools/tests/test_model_roles.py` 59a00ce76104。
範圍：W1 的八支修改檔＋`.env.example`＋新檔 `tools/lib/model_roles.py`／`tools/tests/test_model_roles.py`；W3 的改動與 W2（`resume_cost`）檔案未讀、未評（例外與據實說明見 §9）。

## 0. VERDICT

**VERDICT: CONDITIONAL（SD1-01、SD1-02）**

- 設計本體站得住：介面 delta 13 列＝符合 12（S4、S8 帶 Dev 自陳偏離，判可接受）＋量上偏離但可接受 1（S9）；零列「缺」或「須修」。RTM R1～R3 符合，R4 值符合但「實際」半邊缺（SD1-02），R5 部分（SD1-05，判可接受＋登記）。
- 兩個 P2 都是就地小修：SD1-01＝四行 yml；SD1-02＝一句 PRD 文字（或改程式，不建議）。
- 待裁決題建議：(a) 採 `inherit`（只給 SUBAGENT 鍵、語意＝不注入）；(b) 判 P4 只登記（轉錄檔 `message.model` 已是事後可稽核的真相源）。細節 §4。

## 1. 本場親跑的驗證（逐字／實測；W2 進行中，故只跑准跑清單）

| # | 指令 | 輸出／結果 |
|---|---|---|
| V1 | `export AUTOSDD_SENTINEL_OFF=1; unset AUTOSDD_PARALLEL_TESTS; cd tools/tests && python -m unittest test_model_roles` | `Ran 56 tests in 2.694s`／`OK`／rc=0（01:04:30） |
| V2 | 同環境 `python -m unittest test_model_roles test_quota_policy` | `Ran 395 tests in 8.545s`／`OK`／rc=0（01:04:42）；00:5x 首跑同為 `Ran 395 tests in 8.339s`／`OK` |
| V3 | `.venv/bin/ruff check --no-cache <W1 十檔>` | `All checks passed!` |
| V4 | `python tools/lib/quota_policy.py --print-env-example \| diff - .env.example` | 無輸出、diff_rc=0；`.env.example` 78 行（`git diff --stat`：6 insertions） |
| V5 | `python AutoClaude/tools/check_loc_budget.py --json` | `root_tools_violations`／`special_violations`／`tier_violations`／`absolute_violations` 皆 `[]`；斷言行：planner 746（餘裕 4）、quota_gate 495（餘裕 5）、quota_messages 379、session_brief 327、quota_policy_env 186、resume_route 90、model_roles 47、hook 717／raw 1089（零餘裕，未變） |
| V6 | 以 `resume_route.resume_argv／fresh_argv` 實建 argv（HELMSMAN=fable） | `[…,'--settings',<姿態檔>,'--model','fable','--add-dir',…]`（RESUME、FRESH 皆然）；預設環境無 `--model`；HELMSMAN=`bad value;rm` 無 `--model`；`role_env()`＝`{'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet'}`；`probe_argv('claude')`＝`['claude','-p','ok','--model','haiku','--output-format','json']` |
| V7 | CI paths 探針（scratchpad `review_w1_sd_ci_paths_probe.py`；用 `test_ci_paths_cover_root_consumers.py` 同一組 `_JOIN_RE`／`_SLASH_RE` 與 fnmatch；**未跑該鎖本身**） | `consumed by: ['test_context_budget_guard.py', 'test_model_roles.py']`；windows-compat-ci.yml push／pull_request、macos-compat-ci.yml push／pull_request 皆 `covered=False`；對照 `tools/lib/resume_route.py` 皆 `covered=True` |
| V8 | 幽靈符號探針（`test_doc_loc_baseline_freshness_r60` 同一組 `_SYMBOL_CLAIM_RE`／定義面 glob，掃 W1 新增行＋兩新檔） | `claims: 0`／`ghost count: 0` |
| V9 | `git diff tools/ .env.example \| grep -nE "R2[1-9][0-9]"`＋新檔 grep＋DEF-ID grep | W1 各檔 0 命中；diff 內 4 行命中全在 `tools/lib/governance_docs.py`（主控登記 R211 證據檔，非 W1）；DEF-ID 0 命中 |
| V10 | `ast.parse(feature_version=(3,9))` 對 model_roles／resume_route／quota_messages／session_brief／quota_policy_env／planner／quota_gate | 七檔皆通過（只驗語法；`TestHookChainLoadsOnTheMacDefaultInterpreter` 未跑） |
| V11 | 值域探針（`model_roles._acceptable`／`load_model_roles`／`quota_policy.parse_env_text`，兩次共 38 個值） | 見 §5；另證 `.env` 行內註解會被剝、帶引號的值保留引號（⇒ 被當壞值） |

`[他包回報]`（未親跑，僅轉述 Dev）：774 支指定集合 OK、全套 10 紅歸因、11 變異全殺、探針兩次成本。

## 2. 設計符合性逐列對照

### 2.1 介面 delta（improving_113 §3.1；列號 S1～S13 是本檔標籤，Dev 自陳偏離另稱 Dev-D1…）

| # | 規格 | 實作座標 | 判定 |
|---|---|---|---|
| S1 | ENV_SPEC +3 列（`attr=None`、`kind="model"`）；預設 空／sonnet／haiku；排在逃生口之前 | `tools/lib/quota_policy_env.py:138,141,144`（`section="policy"`，緊接 RELAY 兩列、逃生口前）；`test_the_rows_render_in_the_policy_region_not_under_the_escape_header` | 符合 |
| S2 | 不動 `load_policy`／`Policy`／`DEFAULT_POLICY` | `git diff` 無 `quota_policy.py`；`load_policy` 對 `attr is None` 列 `continue`；`test_a_bad_role_value_cannot_reset_the_quota_ladder`（壞角色值＋`HALT_PCT=88` ⇒ `problems==[]`、`halt_pct==88.0`） | 符合 |
| S3 | HELMSMAN：空＝不帶 `--model`；非空＝`["--model", v]`，位置 `--settings <檔>` 之後、`--add-dir` 之前 | `model_roles.py:88-90`；`resume_route.py:131-140`；V6 實建 argv；兩路 RESUME／FRESH 皆經 `_posture_argv()` | 符合 |
| S4 | SUBAGENT：①喚醒窗口子行程環境注入 `CLAUDE_CODE_SUBAGENT_MODEL=v`，不設 `_FORCE`；②`--pace`／SessionStart 簡報印角色行 | `model_roles.py:83-85`；`resume_route.py:121-123`；`session_resume_planner.py:1227`（同一物理行 `**resume_route.role_env()`）；`quota_messages.py:833-842`＋`quota_gate.py:1002`；`session_brief.py:548-556,597` | 符合；Dev 自陳偏離 Dev-D1（planner 改走 `role_env()`）＝**可接受**：planner 零新 import、零新行；`role_env()`＝`child_env(_roles())` 行為等價；`_roles()` 讀 `os.environ`，與 `main()` 首句 `apply_env_defaults(os.environ)`（planner.py:1533）同源 |
| S5 | DOWNGRADE：降級建議第二階（預設輸出逐字 `sonnet/haiku`）；付費探針模型 | `quota_messages.py:818-830`；`resume_route.py:126-128`；`planner.py:478,504`；`test_the_default_output_is_byte_identical_to_the_old_literal`＋`test_quota_policy.py:2305-2307` 三字面鎖皆含在 V2 的 OK 內 | 符合 |
| S6 | `model_roles.py` 五件：`ModelRoles`／`load_model_roles`／`child_env`／`model_argv`／`roles_line`；零 I/O、py39、裸 import | `model_roles.py:44,62,83,88,93`；`ModelRolesModuleShapeTest` AST 鎖（無 os／subprocess／pathlib／tempfile／shutil）；V10 | 符合 |
| S7 | `resume_route`：`_posture_argv()` 尾端＋`model_argv`；新 `probe_argv(claude, model)` | `resume_route.py:131-140`、`:126-128` | 符合（多 `_roles()`／`role_env()` 兩個小函式，屬 S4 偏離的一部分） |
| S8 | planner：`probe_quota(model=None)`→`model or roles.downgrade`；`_run_resume` env 同一物理行併 child_env；斷言行淨 ≤+1 | `planner.py:478`（簽名）、`:504`（`resume_route.probe_argv(claude, model)`）、`:1227`；LOC 746→746（淨 0） | 符合；`model or downgrade` 住 `resume_route.py:128` 而非 planner（Dev 自陳偏離 Dev-D2）＝**可接受**，且比規格更省守衛面 |
| S9 | quota_messages：`model_hint_line(decision, roles=None)`＋`model_roles_line`（≤+8）；quota_gate `pace_report` +1；session_brief ≤+2；hook 0 | 實際 +10／0／+10／0；`.claude/` 無改動；`quota_gate.py:1002` 走既有模組屬性 `quota_messages.`（`:98` 既有 `import quota_messages`，DEF-200-435 同型先例） | **偏離（量）→ 可接受**，見 SD1-06 |
| S10 | `.env.example` 由生成器重生（72→78 行） | V4 | 符合 |
| S11 | 讀者鎖元組加 `model_roles.py` | `test_context_budget_guard.py:9642-9644` | 符合 |
| S12 | 新測試：預設／別名／完整 id／壞值退預設且出聲／空 helmsman 不帶旗標／child_env／argv 位置與姊妹鎖同形／render→parse round-trip；紅側以合成注入 | 56 支、零 skip（V1）；合成紅側：`test_the_shape_checker_has_teeth_on_synthetic_bad_argv`、`test_the_family_vocabulary_has_exactly_one_home`（patch `MODEL_FAMILIES`）；Dev 紅綠日誌 `scratchpad/113/w1/red_0..red_4／green_1` 存在 | 符合；`--pace` 接線鎖偏弱（SD1-04） |
| S13 | LOC：model_roles ≤120；`.importlinter` 無影響；無 checkpoint 欄位；hook 零改動 | 47；W1 未碰 AutoClaude/；hook 717／raw 1089 未變 | 符合 |

### 2.2 RTM R1～R5

| 需求 | 對 diff 的判定 | 證據 |
|---|---|---|
| R1 主控模型可由參數檔設定並於喚醒續跑生效 | 符合 | `.env`→`apply_env_defaults`（planner.py:1533）→`resume_route._roles()`→`_posture_argv()`；`test_a_helmsman_lands_right_after_the_settings_file_on_both_routes`、`test_configured_roles_reach_the_resume_route`、`test_configured_roles_reach_the_fresh_route_too`；真機探針見 §6 |
| R2 子代理模型可由參數檔設定並於喚醒窗口生效 | 符合 | `test_configured_roles_reach_the_resume_route`（env 帶 `CLAUDE_CODE_SUBAGENT_MODEL=opus`、無 `_FORCE`）；`test_the_rest_of_the_environment_survives_and_the_signal_stays` |
| R3 降級建議與付費探針讀參數 | 符合 | `ModelHintLineTest`、`ProbeArgvTest`、`ProbeQuotaModelTest` |
| R4 互動窗主控看得到角色值 | 值：符合；「實際」半邊：**缺**（SD1-02）；`--pace` 鎖：偏弱（SD1-04） | `SessionBriefRolesTest`（4 支）；`test_pace_report_is_wired_to_the_model_lines` 只是 `inspect.getsource` 子字串鎖 |
| R5 壞值不靜默 | 部分：互動面出聲（`--pace`／簡報 ⚠️）；無人喚醒窗口只退預設、零痕跡 | `resume_route.py:118` `load_model_roles(os.environ)[0]` 丟棄 problems；`planner.py:1189`（`route_chosen`）、`:1238`（`resumed`）皆不記模型；判可接受＋登記，見 SD1-05 |

### 2.3 Dev 自陳偏離與待裁決的判定

| 項 | 判定 | 理由 |
|---|---|---|
| Dev-D1 planner env 走 `resume_route.role_env()`（Dev-D2：`probe_argv` 的 model 可省略） | 可接受 | 見 S4／S8 列 |
| quota_gate 淨 0（`model_lines` 組合） | 可接受 | `pace_report` 只改既有一行；`model_lines` 是純函式組合（`quota_messages.py:838-842`），env 由 `policy_env()` 注入 |
| session_brief +10（規格 ≤+2） | 可接受 | SD1-06 |
| 值域多一道「首字須英數」 | 可接受 | 嚴格子集；`-sonnet`、`--model=sonnet` 實測拒收（V11）；僅錯誤訊息漏寫此規則（SD1-07） |
| `skip_tag_policy` 69→70 | 可接受（但須收尾單次重釘） | SD1-12：W2 若再加 tools/tests 測試檔，70 會再失效 |
| 待裁決 (a) 無「不注入」出口 | 建議採 `inherit` | SD1-03、§4(a) |
| 待裁決 (b) 壞值／實際模型無痕跡 | 判 P4 只登記 | SD1-05、§4(b) |

## 3. Findings

### SD1-01｜P2 須修｜新根層消費檔 `tools/lib/model_roles.py` 未列入兩支 compat-CI 的 `paths`

- **證據**：V7。`tools/tests/test_model_roles.py:511`（`_SRC = _REPO_ROOT / "tools" / "lib" / "model_roles.py"`）與 `tools/tests/test_context_budget_guard.py:9644` 以字面路徑消費該檔；`.github/workflows/windows-compat-ci.yml`（push 約 `:615`、pull_request 約 `:1005` 的 `tools/lib/resume_route.py` 旁）與 `macos-compat-ci.yml`（約 `:491`、`:879`）的 `paths` 皆無 `tools/lib/model_roles.py`，且無 `tools/lib/**` 這類通配。
- **後果**：`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py::test_all_root_consumers_covered_by_ci_paths[windows-compat-ci.yml]` 與 `[macos-compat-ci.yml]` 各紅一格。此鎖住在 ci-gate 的共享 infra `scripts/tests` 腿（`AISDLC_SDD/scripts/ci-gate.sh:327` 區塊，收尾跑 ci-gate 必踩）；但 pre-push 只在 push 涉 `AISDLC_SDD/` 或 `aisdlc-sdd-ci.yml` 列的根層消費檔時才補跑它（`tools/git-hooks/pre-push:160-200,624-640`），W1 的檔案不在那份清單（`aisdlc-sdd-ci.yml:53-119` 的非 SDD 條目）⇒ **本機 pre-push 可能不攔、潛伏到下次有人跑 ci-gate 或觸發 aisdlc-sdd-ci 才紅**。此鎖判準讀**磁碟存在**而非 git index，所以現在就是紅的，不必等 `git add`。同型已在 R80／R81／R86／R98／R99／R114 重犯過（macos-compat-ci.yml 註解逐字記載，「第六次重犯」）。Dev 的驗收清單沒有 ci-gate，所以沒看到。
- **重現**：`.venv/bin/python -I /private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/review_w1_sd_ci_paths_probe.py`（唯讀）；定論請收尾窗口跑 `bash AISDLC_SDD/scripts/ci-gate.sh` 或 `cd AISDLC_SDD && python -m pytest scripts/tests/test_ci_paths_cover_root_consumers.py -q`。
- **判準**：兩支 workflow 的 push＋pull_request 四張 `paths` 清單各補 `- "tools/lib/model_roles.py"`（緊鄰 `resume_route.py` 那組；`test_push_and_pr_paths_symmetric` 要求對稱）。yml 註解請寫 `improving_113`，不要帶 R 標籤。收尾窗口一併檢查：任何新 `tools/lib/*.py` 被 tools/tests 消費者（含 W2 新檔——不在本鏡範圍，只提醒此檢查點）。

### SD1-02｜P2 須修｜PRD 草稿宣稱不存在的行為：「§6 只印『參數 vs 實際』」

- **證據**：草稿 A 列末段「互動主視窗自己的模型不在本鍵射程（…，§6 只印「參數 vs 實際」）」；improving_113 §3.1 誠實劃界 (1) 同句。實作只印**設定值**：`model_roles.py:93-101` 的 `roles_line` 印「主控=…｜子代理=…｜降級=…（主控值只管無人喚醒窗口；互動視窗自己的模型 .env 管不到，派工請明寫 model:）」；全 W1 diff 沒有任何取「互動視窗實際模型」的碼（Dev 自陳 B5：「只印設定值」）。簡報額度行偶爾帶 `active_model=<家族>`（`session_brief.py:234-235`，僅 `decision.per_axis` 時），那是額度軸的判讀註記，不是「參數 vs 實際」的對照。
- **判準**：修憲文字不得宣稱實作沒有的行為（本 repo 判例：「PRD 與實測不符」才修憲；這裡是修憲本身與實測不符）。**建議改文字**（零程式、零守衛面）：「互動主視窗自己的模型不在本鍵射程（由使用者層 settings `model`／`--model`／`/model` 決定）；`--pace` 與 SessionStart 簡報只印三鍵的設定值並註明此限，不印互動視窗的實際模型」，並同步 improving_113 §3.1 誠實劃界 (1)／§8。若堅持要「實際」半邊＝動守衛面（session_brief／quota_messages），須先有 R197 暴露證據，本鏡不建議。

### SD1-03｜P3 應修｜待裁決 (a)：子代理「不注入」出口

建議與理由見 §4(a)。結論：**採「值 `inherit` 合法且＝不注入」，僅限 `AUTOSDD_MODEL_SUBAGENT` 鍵**；若不採納，PRD 4c 與 improving_113 §8 須明寫「無不注入出口；出廠即對每個喚醒窗口注入」。

### SD1-04｜P3 應修｜`--pace` 的角色行只有 `inspect.getsource` 子字串鎖

- **證據**：`test_model_roles.py:444-448`：`self.assertIn("model_lines(", inspect.getsource(quota_gate.pace_report))`。換成註解掉的呼叫、或接進被 halt 短路掠過的分支，這支照綠。Dev 理由（`pace_report` 取數面要打真快取）不成立：`test_context_budget_guard.py` 已有 in-process `qg.pace_report(...)` 夾具測試（例 `:11819` 的 `_quota_cache(...)`＋`_pace_contract_to_tmp()`，零網路）。
- **判準**：在該夾具測試補一行 `self.assertIn("模型角色", text)`（淨 +1 行；該檔是棘輪標的，須同批算進 +N），或在 test_model_roles 仿其夾具。附註：`pace_report` 的 halt 短路（`quota_gate.py:947` `return halted_pace_text(…)`）不印角色行，halt 期間本無派工，可接受，但測試名稱不要暗示「恆印」。

### SD1-05｜P4 登記｜R5 的無人喚醒窗口：壞值只退預設、零痕跡，實際生效模型不留痕

見 §4(b)。**判可接受**：互動面（`--pace`／簡報）出聲；壞值只退「該鍵」出廠值（不連坐、不壞 argv）；無人窗口的效果事後可由轉錄檔 `message.model` 稽核；R197「量、不挖」下，守衛面加碼需暴露證據，目前沒有。PRD 草稿須誠實寫「無人喚醒窗口不另出聲」（PRD-02）。

### SD1-06｜P4 記錄｜守衛面接線量超出規格（+20 vs 規格合計 ≤+12），邏輯零

| 檔 | 規格 | 實際（V5，斷言行） | 內容 |
|---|---|---|---|
| planner | ≤+1 | 0（746→746） | 簽名＋argv 呼叫＋同一物理行併入 `**resume_route.role_env()`，兩行 `#` 註解免費 |
| quota_gate | +1 | 0（495→495） | `pace_report` 既有一行改寫 |
| quota_messages | ≤+8 | +10（369→379） | `Mapping` import 1＋`import model_roles` 1＋`model_hint_line` 簽名／賦值／return 各 +1＝3＋`model_roles_line` 2＋`model_lines` 3 |
| session_brief | ≤+2 | +10（317→327） | try-import 4（本檔 fail-open 紀律，與其餘六個選配相依同形）＋`_models_note` 6 |
| hook | 0 | 0 | `.claude/` 無改動 |

- **判定**：可接受。守衛面每一行都是接線／純渲染組合，判準邏輯全在 `model_roles.py`／`resume_route.py`（`load_model_roles`、驗證、argv、env 皆不在守衛檔）。session_brief 的 +10 必要性：4 行 try-import 是該檔紀律（缺依賴不得擋 SessionStart），`_models_note` 的 try/except 是同一紀律的用處端；可縮到約 +8，無實益。quota_messages 的 +10 可再縮 ~2（`model_roles_line` 與 `model_lines` 合一），無實益。三檔皆距上限（400）遠。
- **處置**：improving_113 §3.1 的「LOC 落點」數字在 §4／§5 回填時改為實際值，並寫明偏離理由，否則規格與落地對不上。

### SD1-07｜P4 登記｜值域驗證精度（結論＝足夠；列出邊界）

結論見 §5。登記項：①值不正規化大小寫（`Sonnet`／`OPUS` 通過驗證、原樣進 argv，CLI 是否大小寫不敏感未驗證）；②`inherit`／`default`／`best` 被拒（`inherit` 見 SD1-03）；③第三方雲端 id（含 `:`／`@`，如 `anthropic.claude-sonnet-5-5-v1:0`、`claude-sonnet-5-5@20260101`）被拒；④錯誤訊息（`model_roles.py:76-77`）寫「只含 A-Za-z0-9._[]-」，但 `-sonnet` 全由合法字元組成卻被拒（漏寫「首字須英數」）；⑤`.env` 值若帶引號（`"fable"`）被當壞值（與既有數值鍵同行為，且有出聲）；⑥`probe_argv(claude, model)` 的**顯式** `model` 參數不經驗證（目前無呼叫端傳值）。皆無安全面影響。

### SD1-08｜P4 登記｜探針證據的邊界與 RESUME 覆寫的未量面

見 §6。證據成立；未覆蓋面：單一樣本、argv 形狀與實際喚醒不同、未測 `[1m]`、未測大轉錄切模型時的快取重建成本與上下文窗差異。

### SD1-09｜P4 登記｜CLI 版本相依與原生變數優先序

- 序位「呼叫時 model 參數 ＞ 子代理定義 ＞ `CLAUDE_CODE_SUBAGENT_MODEL` ＞ 主對話模型」僅 Claude Code ≥ 2.1.251 成立；官方文件（survey 4-3）明寫更早版本此變數優先序最高、蓋過呼叫時參數與 frontmatter（等同 `_FORCE`）。本機 2.1.295 符合；PRD／docstring／ENV_SPEC 說明皆未標版本條件（PRD-03）。
- `child_env` 排在 spawn env 字典最後（`planner.py:1227`），行程既有的原生 `CLAUDE_CODE_SUBAGENT_MODEL` 會被出廠 `sonnet` 蓋掉（有測試鎖 `test_the_parameter_file_wins_over_an_inherited_native_variable`）。實務射程小：schtasks／launchd 叫起的 tick 行程環境只有 PATH；但「出廠預設蓋過使用者明設的原生變數」與 `.env` 的「env > 檔案 > 出廠」序方向相反，須在 PRD 披露（PRD-04）。

### SD1-10｜P4 登記｜降級建議行的第一階語意；「多擋不少擋」措辭

- 建議行字面＝`model: {子代理}/{降級}`。使用者把 SUBAGENT 設成比視窗更高階（如 `fable`）時，收緊帶下的「降級建議」第一階不再是降級（`quota_messages.py:826-829`）。規格如此定義，登記即可。
- 規格誠實劃界 (2)「（hook 對缺席 model 的 Agent 以視窗模型判軸）方向保守（多擋不少擋）」只在「視窗家族軸比子代理預設家族軸緊」的典型配置成立；反向（sonnet 週軸比視窗家族軸緊）會少擋。建議措辭改「典型配置下偏保守」（PRD-10）。

### SD1-11｜P4 登記｜保護面清單不含 `resume_route.py`／`model_roles.py`

`.claude/hooks/block_destructive_git.py:1445-1459` 的 `_GOV_EXACT`（AUTOSDD_UNATTENDED 下寫入唯讀）含 `.env`、planner、quota_gate／quota_messages 等，**不含** `tools/lib/resume_route.py`（W1 前就不在）與新檔 `model_roles.py`。`.env` 已在表上，無人窗口不能經 Write／Edit 改自己的模型角色；但 Write／Edit 改 `model_roles.py`／`resume_route.py` 不受阻。依 R197 這是登記理論洞（P4）、不是本輪加碼理由。

### SD1-12｜P4 交棒｜收尾窗口的棘輪／鎖清單（W1 側）

- `git add` 新檔後 `TestDef200133TrackedImportsDoNotPointAtUntrackedFiles` 才綠（Dev 已述）。
- `tools/lib/skip_tag_policy.py:410` 的 69→70 只對「W1 單獨」成立；W2 若再加 `tools/tests` 測試檔，須以最終實測值一次重釘（W1 的 70 在 89 支時只剩 78.7%）。
- 護欄層行數 +539 超過主軌單輪上限 517、MIN_TESTS 餘裕只剩 61（皆 `[他包回報]`，Dev §5，本鏡未重跑）；`test_model_roles.py` 537 行對 47 行模組，收尾以搬史料抵銷（記憶檔「護欄層成長用搬史料抵銷」）。
- AutoClaude 側 ENV 鏡射鎖：`AutoClaude/tests/test_r86_pace_contract.py:303-305` 只以 regex 讀 `AUTOSDD_QUOTA_DEGRADED_CAP` 一列，W1 新增三列不影響；`test_r82_quota_axis_and_shipped_defaults.py` 位於 W3 改動檔內，W1 側未驗，由收尾窗口於 W3 落地後一併跑。
- 表② 指紋：樹範圍＝`AISDLC_SDD_v0.01|v0.30/tools/fsm_runtime/tests/`、`AISDLC_SDD/scripts/tests/`、`AutoClaude/tests/`（ONBOARDING.md:357-360），**不含 `tools/tests`**；W1 只動 `tools/tests`，故 W1 不觸發表② 回填（觸發者是 W3 的 AutoClaude/tests 變動，由收尾窗口於最後一步處理）。

### SD1-13｜P4 環境備註｜審查期間觀察到工作樹並行改動

00:54:58，`tools/lib/model_roles.py` 與 `tools/lib/resume_route.py` 同秒被寫入；我讀到的版本曾短暫是 `child_env` 無條件回 `{CHILD_ENV_KEY: roles.subagent}`（docstring「沒有子代理角色就什麼都不加」與 `test_child_env_is_empty_without_a_subagent_role` 會與之矛盾），00:55:33 已還原為審查原版（條件式），內容與 mtime 一致（00:54:58）。疑為並行 QA 變異實驗直接在共用樹上就地變異（repo 紀律 #18：mutation 須在隔離樹）；若是，請改隔離樹，否則同時讀檔的審查者會讀到暫態。本報告所有引用已於 01:04 重驗（V1／V2 在還原後跑）。

## 4. 兩個待裁決題

### (a) 子代理「不注入」出口

**建議：`inherit` 合法且＝不注入，僅限 SUBAGENT 鍵。**

1. **與 ENV_SPEC 既有慣例的相容性**：慣例是「空＝未設＝用該鍵預設」——`load_policy`（`quota_policy_env.py` 的 `if not raw: continue`）、`load_model_roles`（`model_roles.py:72`，且有鎖 `test_surrounding_whitespace_is_stripped_and_blank_means_unset`）、`apply_env_defaults`（空白視同缺席）三處一致；`.env.example` 也印 `AUTOSDD_MODEL_SUBAGENT=sonnet`。SUBAGENT 的預設是 `sonnet`，所以「空值＝不注入」會讓「清空這格」與「採預設 sonnet」語意互換：使用者以為「空＝關」，實際仍注入 sonnet（靜默假交付，正是本 repo 反覆立案的那一型），且要把出廠預設改空（與規格出廠值 sonnet、掌舵者「子代理一律 Sonnet」的紀律方向相反）或破壞上述鎖。`inherit` 是顯式哨兵，與慣例不衝突：空仍＝預設，`inherit`＝我要不干預。
2. **官方事實的精確度**（修正「官方：設 inherit 等同未設」的說法；出處＝`/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/model_roles_site_survey_113.md` §4-2／§4-3）：官方文件只在**子代理定義的 frontmatter** 文件化 `inherit`（survey 4-3：「`inherit` selects the main conversation's model」）；環境變數那一行寫「Accepts an alias such as `haiku` or a full model name」，沒寫 `inherit`。「env＝inherit 等同未設」來自 2.1.295 二進位 `function gme(){let e=a.CLAUDE_CODE_SUBAGENT_MODEL;return e&&e!=="inherit"?e:"inherit"}`（survey 4-2，`[二進位]`），是實作行為、非文件承諾。⇒ 實作成「**不注入**」（child_env 回 `{}`），不要把字面 `inherit` 寫進子行程環境（版本脆弱）。
3. **最小實作（只動非守衛面；請 Dev 做，本鏡不改）**：`model_roles.py`：`INHERIT="inherit"`；`_acceptable` 對 SUBAGENT 鍵放行 `inherit`（HELMSMAN／DOWNGRADE 仍拒：`--model inherit`、探針 `--model inherit` 都無意義；HELMSMAN 要「沿用」請留空）；`child_env`：`subagent in ("", INHERIT)` ⇒ `{}`；`roles_line` 印「子代理=inherit（不注入，沿用視窗模型）」；**降級建議行不得印 `model: inherit/haiku`**（Agent 工具 `model` enum 只有四別名，survey 4-2）——把第一階的呈現收進 `model_roles`（例 `ModelRoles` 加一個 `hint` property），`quota_messages.model_hint_line` 只改引用該 property，守衛面 +0～+1。ENV_SPEC 說明字面補「`inherit`＝不注入（行程既有的 CLAUDE_CODE_SUBAGENT_MODEL 原樣保留）」，`.env.example` 重生。測試 +4：SUBAGENT 接受 `inherit`／HELMSMAN、DOWNGRADE 拒收並出聲／`child_env`＝`{}` 且 `role_env()` 不覆蓋殘留原生變數／建議行不含 `inherit/`。LOC：model_roles 47→約 53（上限 400）。
4. **不採納的代價**：PRD 4c 與 §8 須明寫「無不注入出口、出廠即注入、注入值蓋過原生變數」（PRD-04），且不得留「`.env` 留空＝不管」的暗示。

### (b) 無人窗口壞值與實際採用模型要不要留痕

**建議：判 P4 只登記（SD1-05）；不加守衛面碼。**

- 理由：①壞值的後果被限制在「退該鍵出廠值」，不壞 argv、不連坐；②**非法但格式合法**的值（如不存在的 `claude-sonnet-9-9`）會讓 `claude` 非零離開，既有 `resumed` 事件已記 `rc=` 與 `err=`（planner.py:1238-1239 第二物理行 `err=(proc.stderr or "")[:300]`），失敗可稽核；③成功的窗口，實際跑哪個模型已在該窗口的轉錄檔 `message.model`（每個 assistant 訊息一筆）——比「env 說要用什麼」更真；④R197：守衛面新增一行的前提是暴露證據（severity.md〈暴露度〉三取一），目前三者皆無；⑤互動面壞值已出聲（人下次開 session 即見 ⚠️）。
- **若掌舵者仍要留痕，最小加法**（既有載體＝planner 的 resume log，不是 `relay_machine.py`——後者的 `snapshot_log_fields` 是工作樹快照語意，掛模型欄不對題）：
  - 載體 1（建議）：`planner.py:1238` 的 `append_log(log, "resumed", …)` 第二物理行（`err=…, out=…)` 那行）追加 `**resume_route.role_trace()`——planner 淨 **0** 行（改既有行、不增行）；`resume_route.role_trace()`＋約 5 斷言行，回 `{"model_roles": {helmsman, subagent, downgrade}, "model_problems": [...]}`（生效值＋problems，需要 `_roles()` 回傳 problems）；1 支測試（`_run_resume` 替身 spawn 後讀 log 一行）。
  - 載體 2（零守衛行）：`resume_route.handback_postcheck(route, spawn_at, state, log, append_log, alert)`（`resume_route.py:95`）本就拿到 `log`、`append_log`，可在其內多落一個 `model_roles` 事件；代價＝該函式語意（交接後檢）被混入，且其既有測試可能釘事件清單，先查。
  - 跨波選項（給主控，不評 W2 實作）：若 W2 的落帳記錄本就讀「喚醒後第一筆 assistant 訊息」，加一個 `model` 欄取自同一筆訊息的 `message.model`，是零成本且最誠實的「實際採用模型」記錄。
- 不論採不採，PRD 4c／§8 須誠實寫「無人喚醒窗口的壞值只退預設、不另出聲」（PRD-02）。

## 5. 值域驗證結論（V11，38 個值，`model_roles` 純函式實測）

結論：**對第一方（OAuth／API key）別名與完整 id 足夠；沒有 argv／env 注入面；唯一須處置的是 SD1-03（`inherit`）。**

| 值 | 驗證 | 備註 |
|---|---|---|
| `fable` `opus` `sonnet` `haiku` | 收 | 四別名 |
| `claude-sonnet-5-5`、`sonnet[1m]`、`claude-fable-5-1[1m]`、`claude-3-5-haiku-latest`、`opusplan` | 收 | `opusplan` 因含 `opus` 通過 |
| `Sonnet 5.5`（含空白） | **拒**＋problems 1 句、退預設 | 符合預期 |
| `Sonnet`、`OPUS` | 收（原樣大小寫進 argv） | SD1-07①，CLI 大小寫行為未驗證 |
| `-sonnet`、`--model=sonnet`、`sonnet;ls`、`$(sonnet)`、`../x`、全形 `ｓｏｎｎｅｔ`、`gpt-4`、`claude-mythos-5`、`claude\nsonnet` | 拒 | 首字須英數＋字元白名單；非四家族 id 要先擴 `MODEL_FAMILIES` |
| `inherit` `default` `best` | 拒 | `inherit` 見 SD1-03 |
| `anthropic.claude-sonnet-5-5-v1:0`、`claude-sonnet-5-5@20260101` | 拒 | 第三方雲端 id（`:`／`@`）；repo 現為第一方訂閱制，P4 |
| `sonnet]]`、`sonnet[`、`opus-sonnet` | 收 | 家族字命中即可；無意義值會讓 CLI 非零離開，被 `resumed` 的 `rc=`／`err=` 記下，無安全面 |

- **argv 注入面**：值進 `--model <v>` 兩個 list 元素，不經 shell；首字須英數 ⇒ 不可能被 CLI 當成另一個旗標（`-x`、`--x=`）；白名單排除 cmd.exe 特殊字元（`& | ^ < > % !`）與空白，Windows `.cmd` 殼也無法被注入；env 值同白名單。`_SHOWN_MAX=40` 限制 problems 引用長度，且以 `repr` 引用（換行被跳脫），不撐爆簡報。
- **「誤拒合法值」**：`claude-sonnet-5-5`、`sonnet[1m]` 皆收（`test_every_alias_and_full_id_is_accepted_on_every_key` 覆蓋七個值×三鍵）；其餘邊界見 SD1-07。

## 6. 探針證據（`probe_resume_model_113.json`）

**結論：證成。** `-p -r <sid> --model sonnet` 的新回合跑在 sonnet-5-5。

- call1（`--model haiku`）：`modelUsage` 鍵只有 `claude-haiku-5-5`；`costUSD` 0.0018268300000000002。
- call2（同 `session_id` a119e01d-…、`-r … --model sonnet`）：`modelUsage` 鍵＝`claude-haiku-5-5`＋`claude-sonnet-5-5`；`claude-sonnet-5-5.outputTokens`＝46 與頂層 `usage.output_tokens`＝46、`cacheCreationInputTokens` 8767 與頂層 `usage.cache_creation_input_tokens` 8767 逐項相同 ⇒ 新回合整個記在 sonnet；`claude-haiku-5-5` 那列與 call1 逐項相同（outputTokens 64、cacheCreation 8406、cost 0.0018268…）＝session 累計的舊回合。
- **成本如 Dev 所述**：call2 的 `total_cost_usd` 0.039627430000000005＝call1 0.0018268300000000002＋sonnet 列 `costUSD` 0.037800600000000004（相加 0.0396274…）；Dev 的「call1 $0.00183／sonnet $0.0378／兩次合計約 $0.0396」正確，且沒有把 call2 的累計總額再加一次 call1。
- **邊界**（SD1-08）：①單一樣本、1 回合小 session；②實際喚醒 argv 形狀（`-p -r <sid> <prompt> --permission-mode … --settings … [--model X] --add-dir …`）與探針（`-p "ok" -r <sid> --model sonnet --output-format json`）不同——`--model` 位置由 `_argv_shape_problems` 與 `--add-dir` 變長旗標的既有判準釘住，不是探針證的；③未測 `[1m]` 後綴、未測 HELMSMAN 與存檔模型**不同**家族時對大轉錄的快取重建成本與上下文窗（如存檔跑 `[1m]`、HELMSMAN 設無 `[1m]` 的別名）——B4 的 RESUME「沿用→覆寫」語意只在 HELMSMAN 非空時發生，出廠預設不受影響；W2 的喚醒成本落帳若上線，會是量這件事的現成載具。

## 7. 註解掃描

- `git diff tools/ .env.example | grep -nE "R2[1-9][0-9]"`：4 行命中，**全在 `tools/lib/governance_docs.py`**（主控登記 `CrossPlatform_R211_*` 兩證據檔，`:658-663`），不是 W1；planner 被改的那一物理行含既有的「R115」與 `round-label-ok`，非本輪新增、也小於 211。
- 新檔 `model_roles.py`／`test_model_roles.py`：`R2[1-9][0-9]` 0 命中；DEF-ID 0 命中（故無「引用帳本不存在的 DEF-ID」之虞）。W1 註解一律寫 `improving_113`。
- 另附：未來輪號鎖（`future_round_labels`）的 current 現為 211（主控已建 `CrossPlatform_R211_*` 檔，`current_round()` 取檔名最大號）；W1 無 R 標籤，與該鎖無涉。

## 8. 〈PRD 草稿訂正清單〉（對 `prd_amendment_v2116_draft.md` 的 A／B／C 三段；D 節＝W3，未評）

總體：與實作的鍵名（`AUTOSDD_MODEL_HELMSMAN／SUBAGENT／DOWNGRADE`）、出廠值（空／sonnet／haiku）、`--model` 條件與位置、`CLAUDE_CODE_SUBAGENT_MODEL` 注入與不設 `_FORCE`、值域（別名／含家族字完整 id、壞值退該鍵出廠值）一致；`[需核對]` 前半（旗標，附錄 B-11）已核實、後半（訂閱制內建降級）仍未核實的陳述與 PRD L491 原文一致；A/B/C 三段皆為純新增（新列／新區塊／新落款），**不違反 R110「不疊層」**；與根層文件鎖相關的形態檢查：反引號路徑僅 `docs/04_planning/AutoSDD_improving_113.md`（存在）；「延後到／留給／交給／承接／下輪／零真機」0 命中；R 標籤僅 R110（既有）；幽靈符號鎖與 `check_handoff_carriers` 的掃描面（`_SYMBOL_REF_GLOBS`／`_CARRIER_GLOBS`）都不含 `docs/01_requirements/` PRD 本文。以下為須訂正處：

| ID | 級 | 位置 | 問題 | 建議訂正 |
|---|---|---|---|---|
| PRD-01 | **P2** | A 列末段 | 「§6 只印『參數 vs 實際』」＝實作沒有（＝SD1-02） | 改為「互動主視窗自己的模型不在本鍵射程（由使用者層 settings `model`／`--model`／`/model` 決定）；`--pace` 與 SessionStart 簡報只印三鍵設定值並註明此限，不印互動視窗的實際模型」；同步 improving_113 §3.1(1)／§8 |
| PRD-02 | P3 | B 區塊註解 | 「壞值 → 退該鍵出廠值 ＋ 出聲一次」：實作每次載入都回 problems、`--pace`／簡報每次顯示皆帶 ⚠️（無去重），無人喚醒窗口丟棄 problems（`resume_route.py:118`）不出聲 | 改為「壞值 → 退該鍵出廠值；`--pace`／SessionStart 簡報顯示時帶 ⚠️ 說明；無人喚醒窗口只退出廠值、不另出聲」 |
| PRD-03 | P3 | A 列、B 區塊「官方序位」句 | 序位僅 Claude Code ≥ 2.1.251 成立；更早版本此變數優先序最高、等同 `_FORCE`；未標條件 | 句尾補「（Claude Code ≥ 2.1.251；本機 2.1.295）」，並註「更舊版本此變數蓋過呼叫時 model」 |
| PRD-04 | P3 | A 列／B 區塊 | 缺三項行為披露：①SUBAGENT 出廠即對**每個**喚醒窗口注入（`.env` 留空＝採 sonnet），〔若採 SD1-03：`inherit`＝不注入；否則：目前無不注入出口〕；②注入值蓋過行程既有的 `CLAUDE_CODE_SUBAGENT_MODEL`；③HELMSMAN 非空時 RESUME 路由「沿用存檔模型」變「`--model` 覆寫」（探針實證，§6） | 各補一句；①的措辭須與 SD1-03 的裁決一致 |
| PRD-05 | P3 | A 列同一格 | 「前半／後半」雙義：先指「設定面／自動改模型」，緊接又指 `[需核對]` 的「具體旗標／訂閱制內建降級」 | 第一組改稱「設定面／自動觸發面」；第二組保留原詞 |
| PRD-06 | P3 | A 列正文 | 「`[需核對]`（L491）」：本修憲同批在修訂表加一列，行號即刻漂移（L491→L492） | 刪「（L491）」，改稱「§4.2.3 致動器表下方的 `[需核對]` 註記」（C 節標題的 L476／L491 是給套用者的施工指示，可留，但不得進 PRD 正文） |
| PRD-07 | P3 | A 列日期＋狀態欄 | 日期 2026-10-09 是立案日，修訂日期欄體例是落款日（v2.1.14／v2.1.15 列皆如此）；狀態欄「…四方複審…後生效」是未來式，且無審查紀錄指針；「皆 `model: sonnet` 唯讀鏡」須與審查實況一致 | 落款時填實際落款日（≥2026-10-10）；狀態欄改為實際結果＋紀錄指針（體例：「…4×APPROVE（Architect／SA／SD／QA，紀錄＝`docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md` §6）；程式面同批落地」）；該檔現存於磁碟（反引號路徑 OK）；Architect 鏡是否同為 Sonnet 以該檔 §6 為準逐字對齊 |
| PRD-08 | P3 | A 列標題／摘要 vs 草稿檔 D 節 | v2.1.16 列只涵蓋 W1，而同草稿檔已有 D 節（W3 的 §4.5.2／§4.5.5 落款）；同一版本號的修訂列須涵蓋該版全部落款，或 W3 另列一版 | 擇一：擴充列標題／摘要，或 W3 另列 v2.1.17（本鏡不評 D 節內容） |
| PRD-09 | P3 | B 區塊 | ①`AUTOSDD_MODEL_DOWNGRADE`（降級**目標**）與 §6 區塊 4 既有 `MODEL_DOWNGRADE_PERCENT`（降級**門檻**，harness 未實作）名稱相近，無交叉參照；②「區塊 4c」與 §4.2.2-b 既有的「(4c) gate 聚合面」（v2.1.14 列）同標籤 | ①區塊註解加「與區塊 4 的 `MODEL_DOWNGRADE_PERCENT`（何時降）互補，本鍵只給『降到誰』」；②加「（與 §4.2.2-b 的 (4c) 無關）」 |
| PRD-10 | P4 | C 節／B 區塊誠實劃界 | 缺：①守衛對未帶 `model` 的 Agent 以視窗模型判額度軸（A4 理論洞、hook 零改動），注入後 general-purpose 實際跑子代理預設模型，方向「典型配置偏保守」（SD1-10），非「必然多擋」；②Windows 側未驗證；③降級建議行兩階＝子代理角色／降級角色，語意由使用者設定自負 | 各補一句；②須界定輪次（例：「improving_113 期間僅 macOS 開發機實測；Windows 側未驗證」），不得寫無界定的「零真機」（SC-9） |
| PRD-11 | P4 | C 節 | 檔案路徑（`tools/lib/model_roles.py`、`tools/lib/resume_route.py`）未加反引號，A 列的路徑有加；風格不一致 | 統一；若加反引號須存在（兩檔現存於磁碟；`model_roles.py` 尚未入 index，與 tracked-import 鎖無涉） |
| PRD-12 | P4 | B 區塊註解 | 帶 `attr=None`／`kind="model"`／`load_policy` 等實作細節；日後改名即產生 PRD↔實作漂移（既有 §6 區塊亦引實作符號，可接受） | 只留語意句「不經整組退回語意，一個拼錯的模型名不得重設整套額度門檻」，刪 `attr=None`／`kind="model"` 字面 |

## 9. 未驗證／不在本鏡範圍

- 未跑：根層全套（W2 進行中）、`test_ci_paths_cover_root_consumers.py` 本身（以同一組正則重現，SD1-01）、既有 9 支 argv 形狀鎖與 774 集合（`[他包回報]`，Dev 稱 OK）、`TestHookChainLoadsOnTheMacDefaultInterpreter`（只驗語法 V10）、`--pace` 實際畫面（打真快取，只做純函式渲染樣本：`model_lines` 在收緊帶印兩行、免費帶只印 🤖 行）、Windows 全面、`test_r82_quota_axis_and_shipped_defaults.py`（W3 改動檔）。
- 未讀：W3 的改動檔與實作、W2 的檔案（只從 `git status` 看到其檔名）、repo 根 `.env` 內容（存在，2026-08-23；機密面，不讀）。據實說明的例外：①為評估 W1 新增三列 ENV_SPEC 對 AutoClaude 鏡射鎖的影響，讀了**未被 W3 改動**的 `AutoClaude/tests/test_r86_pace_contract.py`（L45-75、L285-330）並 grep 了 AutoClaude 內引用 `ENV_SPEC` 的檔名；②整檔讀 improving_113 時過目了 §3.2／§3.3 的規格文字，未據以審查；③讀 AISDLC_SDD／AutoClaude 的 CLAUDE.md 為工具自動載入。
- 真機：未呼叫 claude；探針證據僅讀 Dev 交件 JSON 逐項核算。

## 〈T-4 W1 QA 鏡〉（review_w1_qa_113.md）

# W1 模型角色參數化——QA 零信任複審 findings（improving_113）

VERDICT: CONDITIONAL（QA1-01）

VERDICT 理由：
- 無 P2：任務書第 1、2、3、4、6、7 項全數重現且通過（56／774 測試、ruff、.env.example、LOC、突變 6/6、行為實證、碼路徑追問）。
- 條件 QA1-01（P3）：第 5 項探針預期「call2 只含 sonnet」與證據不符；語意結論（新回合跑在 sonnet）由三條算術旁證成立，但措辭必須訂正，避免假話進 PRD／證據檔。
- QA1-02 是 W1＋W2 合併後的整合交棒（單看 W1 不紅），不是 W1 缺陷。

- 審查者：QA 零信任複審鏡（Sonnet 5.5）｜repo HEAD 93929947｜2026-10-10 凌晨（本機時間）
- 範圍：W1——tools/lib/{quota_policy_env,resume_route,quota_messages,quota_gate,session_brief,skip_tag_policy}.py、tools/session_resume_planner.py、tools/tests/test_context_budget_guard.py、.env.example、新檔 tools/lib/model_roles.py／tools/tests/test_model_roles.py。
- 範圍外（未讀未評）：AutoClaude/**（W3）；tools/lib/resume_cost.py、tools/tests/test_resume_cost.py（W2）。唯一接觸＝QA1-02 為了數 tools/tests 的檔案個數，只列檔名、沒開檔。審查期間工作樹另外新增了非 W1 的變動（`git status` 前後對照）：tools/lib/governance_docs.py（M）、tools/lib/relay_machine.py（M）、docs/04_planning/ADR/ADR-XPLAT-002…（M）、docs/06_quality/CrossPlatform_R211_*（??）、tools/lib/resume_cost.py＋tools/tests/test_resume_cost.py（??）——皆未讀未評；W1 十一個檔（含兩個新檔）在整個審查期間內容不變（兩個被突變的檔另以 sha256 還原證明）。
- 單跑前置（每次呼叫都重設）：`export AUTOSDD_SENTINEL_OFF=1; unset AUTOSDD_PARALLEL_TESTS AUTOSDD_PARALLEL_TESTS_WORKERS`，在 `tools/tests` 下載入。
- 原始輸出檔都在 scratchpad/113/qa_w1/；本檔貼的尾段逐字取自那些檔（腳本 qa_build_report.py 組裝時直接讀檔，不重組、不轉述數字）。
- 零信任基準：Developer 交件（w1_dev_log_113.md）的數字一律自己重跑；符合標「重現」、不符標「不符」。

## 0. 一眼表

| 任務書項 | 結果 | 與 Dev 交件 |
|---|---|---|
| 1 `test_model_roles -v` | Ran 56 tests／OK（rc=0） | 重現（Dev：56／OK） |
| 1 指定集合（13 組模組／類別） | Ran 774 tests／OK（rc=0）；尾段無 skipped／expected failures 標註 | 重現（Dev：774／OK） |
| 2 ruff（8 檔，repo 根、不帶 --config） | All checks passed!（rc=0） | 重現 |
| 2 `--print-env-example \| diff - .env.example` | 零輸出（diff_rc=0；.env.example 78 行） | 重現 |
| 2 LOC | ROOT-TOOLS／special／tier／absolute violations 全空；planner 746/750、quota_gate 495/500、hook raw 1089 不變且 hook 零 diff | 重現（8 支數字逐項相同；HEAD 側 6 支「改前值」亦逐項相同） |
| 3 突變（6 個） | 6/6 擊殺；兩檔 sha256 還原前後相同、`git diff --no-index --exit-code` 兩檔 rc=0 | Dev 自做 11 個行程內突變，本場另做 6 個檔案層突變 |
| 4 行為實證 | `--pace` 三形態、argv 與 HEAD 逐字比對、SessionStart 簡報、8 種 import 起手序皆如預期 | — |
| 5 探針證據 | call1 只含 haiku ✓；call2 鍵＝haiku＋sonnet——任務書預期「只含 sonnet」✗，語意結論仍成立（QA1-01） | Dev 敘述「haiku 列逐項相同」需精確化 |
| 6 文件／註解 | W1 檔零 `R2[1-9][0-9]`、新增行零 DEF-ID、新測試零 skip／xfail、E501 由 tools/ruff.toml 涵蓋（自量最大寬度 99） | 重現 |
| 7 風險追問 | 屬實且順序正確：`role_env()` 讀 `os.environ`；`.env` 值靠 planner `main()` 首個呼叫 `apply_env_defaults(os.environ)` 先填入 | — |
| 自加：延伸回歸（17 個相關模組） | 1997 tests／failures=1／skipped=18；唯一紅＝整合型（QA1-02），非 W1 缺陷 | Dev 的全套紅清單不含此項（當時 W2 檔未進樹） |
| 自加：hermeticity（行程環境先帶 HELMSMAN=fable／SUBAGENT=opus／DOWNGRADE=sonnet／CLAUDE_CODE_SUBAGENT_MODEL=haiku／_FORCE=1） | test_model_roles：Ran 56／OK；寬集合 22 個模組：Ran 2702 tests／OK (skipped=18)／rc=0——W1 與既有測試不依賴「這三個鍵沒設」 | — |

## 1. 驗收指令逐字尾段

### 1.1 `python -m unittest test_model_roles -v`（tools/tests 下）
（尾端 5 個 `ok` 行＝WakeSpawnCarriesTheRolesTest 的錄影替身 stdout「ok」被 `_run_resume` 印出，不是結果。）
```
test_the_rest_of_the_environment_survives_and_the_signal_stays (test_model_roles.WakeSpawnCarriesTheRolesTest.test_the_rest_of_the_environment_survives_and_the_signal_stays) ... ok

----------------------------------------------------------------------
Ran 56 tests in 2.658s

OK
ok
ok
ok
ok
ok
rc=0
```

### 1.2 突變全部還原後再跑一次 `python -m unittest test_model_roles`（證明工作樹回綠）
```
Ran 56 tests in 2.662s

OK
ok
ok
ok
ok
ok
rc=0
```

### 1.3 指定集合（任務書第 1 項第二條指令，模組／類別清單逐字照抄）
指令：`python -m unittest test_quota_policy.TestM6EnvExampleBidirectionalLock test_quota_policy.TestM6TheGeneratedFileSurvivesItsOwnConsumer test_context_budget_guard.QuotaEnvFileIsActuallyLoadedTest test_context_budget_guard.ResumeSpawnCarriesTheUnattendedSignalTest test_context_budget_guard.ResumeRouteDegradesOneWayTest test_context_budget_guard.HandbackAddDirIsResolvedDynamicallyTest test_context_budget_guard.FanoutCasualtyRecordTest test_session_brief test_mac_readiness_r82 test_platform_utils_dedup test_subprocess_encoding_hygiene test_platform_neutral_paths test_quota_policy`
輸出摘錄（`grep -E "^(Ran |OK|FAILED|rc=)"`；完整輸出另有測試自身印出的紅字夾具訊息與兩行收尾雜訊，皆為既有測試的 stdout，不是結果）：
```
Ran 774 tests in 106.535s
OK
rc=0
```

### 1.4 `ruff check <8 檔>`（repo 根、不帶 --config；就近設定檔＝tools/ruff.toml）
```
All checks passed!
ruff_rc=0
```

### 1.5 `python tools/lib/quota_policy.py --print-env-example | diff - .env.example`
（為了讀 rc，改導檔再 diff：`... > t4_env_gen.txt; diff t4_env_gen.txt .env.example > t4_env_diff.txt`）
```
diff_rc=0；wc -c(t4_env_diff.txt)=0；.env.example 行數=78
```

### 1.6 `python AutoClaude/tools/check_loc_budget.py --json`（rc=0）與 7 支檔斷言行數
```
absolute_violations => []
tier_violations => []
special_violations => []
root_tools_violations => []
ROOT-TOOLS warn: tools/lib/quota_escalation.py 400 / 400 headroom 0
ROOT-TOOLS warn: tools/lib/skip_group_policy.py 400 / 400 headroom 0
ROOT-TOOLS warn: tools/session_resume_planner.py 746 / 750 headroom 4
ROOT-TOOLS warn: tools/lib/quota_gate.py 495 / 500 headroom 5
SPECIAL warn（節錄；其餘為 archive_defect_log／hook_wiring／run_root_unittests／CLAUDE.md／dev_start／check_script_parity，皆與 W1 無關）: ../.claude/hooks/context_budget_guard.py 1089 / 1089 headroom 0
special_stale => []

（count_loc 與 --json 同一個計價器；AutoClaude/tools 的 check_loc_budget.count_loc 逐檔直呼）
tools/lib/quota_policy_env.py: assertion=186 raw=308
tools/lib/model_roles.py: assertion=47 raw=101
tools/lib/resume_route.py: assertion=90 raw=285
tools/session_resume_planner.py: assertion=746 raw=1681
tools/lib/quota_messages.py: assertion=379 raw=852
tools/lib/quota_gate.py: assertion=495 raw=1218
tools/lib/session_brief.py: assertion=327 raw=598
.claude/hooks/context_budget_guard.py: assertion=717 raw=1089
wc -l .claude/hooks/context_budget_guard.py -> 1089
git diff --quiet -- .claude/hooks; hook_diff_rc=0   （git status --short -- .claude/ 亦為空）

HEAD 側「改前值」（git show HEAD:<檔> 後同一個 count_loc）：
quota_messages 369→379（Δ+10；規格 ≤+8）｜session_brief 317→327（Δ+10；規格 ≤+2）｜quota_gate 495→495（Δ0；規格 ≤+1）
planner 746→746（Δ0；規格 ≤+1）｜quota_policy_env 178→186（Δ+8）｜resume_route 81→90（Δ+9）
```

## 2. 突變（任務書第 3 項；最多 6 個，全做）

方法：腳本 qa_mutate.py——每個突變①`cp` 備份（開跑前一次）②精確字串替換（斷言命中恰 1 處）③只跑 `python -B -m unittest test_model_roles`（`-B`＋PYTHONDONTWRITEBYTECODE=1，避免突變版 .pyc 殘留）④**立刻** `cp` 還原⑤比 sha256。M5 的「位置」由 resume_route.py 決定（不是 model_roles.py），所以 M5 改的是 resume_route.py（備份／還原／證明同樣處理）。

| ID | 突變 | 檔 | test_model_roles 結果（Ran 56） | 擊殺的測試（去重；括號＝命中次數） |
|---|---|---|---|---|
| M1 | 白名單放行含空白／分號：`_VALUE_RE` 字元類加入 `;` 與空白 | model_roles.py | FAILED (failures=6) | LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once（6，subTest：`opus x`、`sonnet;ls` × 三鍵） |
| M2 | `family_key` 檢查拿掉（只剩字元白名單） | model_roles.py | FAILED (failures=8) | 同上（6）＋ test_a_very_long_bad_value_is_quoted_with_a_bounded_length（1）＋ test_the_family_vocabulary_has_exactly_one_home（1） |
| M3 | helmsman 空仍帶 `--model` | model_roles.py | FAILED (failures=5) | ResumeRouteModelFlagTest.{test_a_bad_helmsman_value_degrades_to_no_flag_not_to_a_broken_argv, test_the_posture_flags_are_untouched_by_the_model_flag, test_without_a_helmsman_neither_route_carries_a_model_flag}、RoleDerivationsTest.test_model_argv_is_empty_for_an_empty_helmsman、WakeSpawnCarriesTheRolesTest.test_the_default_wake_window_gets_the_subagent_default_and_no_model_flag（各 1） |
| M4 | subagent 空仍注入（`child_env` 恆回 `{CHILD_ENV_KEY: …}`） | model_roles.py | FAILED (failures=1) | RoleDerivationsTest.test_child_env_is_empty_without_a_subagent_role（1；見下註） |
| M5 | `--model` 位置改到 prompt 之前（`_posture_argv` 尾端不接、`resume_argv`／`fresh_argv` 在 prompt 前插入） | resume_route.py | FAILED (failures=2) | ResumeRouteModelFlagTest.test_a_helmsman_lands_right_after_the_settings_file_on_both_routes、WakeSpawnCarriesTheRolesTest.test_configured_roles_reach_the_resume_route（各 1） |
| M6 | 壞值不回 problems（`return ModelRoles(*values), []`） | model_roles.py | FAILED (failures=36, errors=1) | 共 8 支、37 筆紅：LoadModelRolesTest 6 支（test_a_bad_value_falls_back…says_so_once 含 30 筆 subTest；另 test_an_empty_default_is_named_as_empty_in_the_problem_text 為 ERROR；test_a_very_long_bad_value…、test_one_bad_key_does_not_drag…、test_the_family_vocabulary…、test_two_bad_keys…各 1）＋ ModelHintLineTest.test_model_lines_says_a_bad_value_out_loud ＋ SessionBriefRolesTest.test_a_bad_value_is_warned_in_the_brief |

擊殺數：**6/6**（零存活）。
註 M4：`load_model_roles` 對 subagent 永遠回非空（`raw or default`，預設 sonnet），所以這個分支在整合層是防禦性死分支，只有直接構造 `ModelRoles("fable", "", "haiku")` 的單元測試能咬到它——只靠 1 支測試擊殺，薄但足夠，且不是疏漏（整合層沒有可觀測差異）。

腳本逐字輸出（含還原證明）：
```
baseline sha256:
  model_roles.py 52964cdcb3c50ba08d0433a6d3c29ad09a2cc8646a441b9da3c48e178cf2e8d2
  resume_route.py 5f8e9630083b1b43cd2bbeb52ece5a0ae6b559b74827a8b76f0547fbf0da9542
M1 [白名單放行含空白／分號的值] rc=1 ran=56 FAILED (failures=6) red_tests=6 restored_sha_equal=True
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
M2 [family_key 檢查拿掉] rc=1 ran=56 FAILED (failures=8) red_tests=8 restored_sha_equal=True
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
M3 [helmsman 空仍帶 --model] rc=1 ran=56 FAILED (failures=5) red_tests=5 restored_sha_equal=True
     - test_a_bad_helmsman_value_degrades_to_no_flag_not_to_a_broken_argv (test_model_roles.ResumeRouteModelFlagTest.test_a_bad_helmsman_value_degrades_to_no_flag_not_to_a_broken_argv)
     - test_the_posture_flags_are_untouched_by_the_model_flag (test_model_roles.ResumeRouteModelFlagTest.test_the_posture_flags_are_untouched_by_the_model_flag)
     - test_without_a_helmsman_neither_route_carries_a_model_flag (test_model_roles.ResumeRouteModelFlagTest.test_without_a_helmsman_neither_route_carries_a_model_flag)
     - test_model_argv_is_empty_for_an_empty_helmsman (test_model_roles.RoleDerivationsTest.test_model_argv_is_empty_for_an_empty_helmsman)
     - test_the_default_wake_window_gets_the_subagent_default_and_no_model_flag (test_model_roles.WakeSpawnCarriesTheRolesTest.test_the_default_wake_window_gets_the_subagent_default_and_no_model_flag)
M4 [subagent 空仍注入] rc=1 ran=56 FAILED (failures=1) red_tests=1 restored_sha_equal=True
     - test_child_env_is_empty_without_a_subagent_role (test_model_roles.RoleDerivationsTest.test_child_env_is_empty_without_a_subagent_role)
M5 [--model 位置改到 prompt 之前（resume_route 兩路 argv）] rc=1 ran=56 FAILED (failures=2) red_tests=2 restored_sha_equal=True
     - test_a_helmsman_lands_right_after_the_settings_file_on_both_routes (test_model_roles.ResumeRouteModelFlagTest.test_a_helmsman_lands_right_after_the_settings_file_on_both_routes)
     - test_configured_roles_reach_the_resume_route (test_model_roles.WakeSpawnCarriesTheRolesTest.test_configured_roles_reach_the_resume_route)
M6 [壞值不回 problems] rc=1 ran=56 FAILED (failures=36, errors=1) red_tests=37 restored_sha_equal=True
     - test_an_empty_default_is_named_as_empty_in_the_problem_text (test_model_roles.LoadModelRolesTest.test_an_empty_default_is_named_as_empty_in_the_problem_text)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
     - test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once (test_model_roles.LoadModelRolesTest.test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once)
after sha256:
  model_roles.py 52964cdcb3c50ba08d0433a6d3c29ad09a2cc8646a441b9da3c48e178cf2e8d2 EQUAL
  resume_route.py 5f8e9630083b1b43cd2bbeb52ece5a0ae6b559b74827a8b76f0547fbf0da9542 EQUAL
harness_rc=0
```

還原證明（突變結束後另跑；因兩檔都不是 `git diff --exit-code` 的有效對象——model_roles.py 是 untracked、resume_route.py 本就有 W1 的改動——改用 `--no-index` 對備份比對）：
```
git diff --no-index --exit-code <備份>/bk_model_roles.py tools/lib/model_roles.py   -> model_roles_diff_rc=0
git diff --no-index --exit-code <備份>/bk_resume_route.py tools/lib/resume_route.py -> resume_route_diff_rc=0
shasum -a 256 (突變前＝突變後＝備份)：
52964cdcb3c50ba08d0433a6d3c29ad09a2cc8646a441b9da3c48e178cf2e8d2  tools/lib/model_roles.py
5f8e9630083b1b43cd2bbeb52ece5a0ae6b559b74827a8b76f0547fbf0da9542  tools/lib/resume_route.py
```
誠實揭露：突變窗口共 6 次、每次約 3 秒，期間兩檔在工作樹上是突變版；開跑前 `ps` 看過沒有其他 python／unittest 行程，但無法排除 W2／W3 的行程恰在窗口內載入。還原後 mtime 已更新（cp 的副作用，內容位元組相同）。

## 3. 行為實證（零 token）

### 3.1 `python tools/session_resume_planner.py --pace`（三種環境；來源=cache，未打端點；rc 皆 0）
預設（本機 .env 無 AUTOSDD_MODEL_*，行程環境亦無）——全文：
```
現在可派 2 個 agent（硬上限 cap=4，本視窗已用 1 次）｜band=notice｜最緊的一條＝five_hour 55% 剩 184 分鐘
  kind=session 55% 剩 184 分鐘 band=notice horizon=far cap=4 note=burn-ahead；kind=weekly_all 60% 剩 1504 分鐘 band=notice horizon=mid cap=8 note=burn-thrifty；kind=weekly_scoped 54% 剩 1504 分鐘 band=notice horizon=mid cap=8 model=Fable note=burn-thrifty；kind=five_hour 55% 剩 184 分鐘 band=notice horizon=far cap=4 note=burn-ahead；kind=seven_day 60% 剩 1504 分鐘 band=notice horizon=mid cap=8 note=burn-thrifty；kind=spend 0% reset 距離不明 band=free horizon=none cap=None note=missing　⇒ cap=4 recommended=2 band=notice binding=five_hour reason=ok,burn-ahead,burn-thrifty,gate_excluded=spend,missing
  攤提：kind=weekly_all 剩 40pp／距 reset 1504 分鐘 ÷ 5.0 個 kind=session 窗 = 每窗 7.98pp ×r=5.0（n=57 ⇒ 取中位數）⇒ 本窗配額 39.9pp；kind=session 已用 55pp 剩 184 分鐘 ⇒ 本窗餘裕 -15.1pp；短窗自軸 pace_index=1.43（>1＝超前；分母是短窗流逝比，與本窗餘裕不同軸、不可互抵）；長窗自軸 60pp 未達 converge 70pp ⇒ 出聲不收緊（本次未壓制短窗水位）
  派工前置：方案指紋=five_hour+session+seven_day+spend+weekly_all+weekly_scoped｜此帳號**沒有** usage credits ⇒ 訂閱窗本身即硬牆
   ⏱ 扇出視窗：剩 212 秒（帳上 1 筆，最舊 88 秒前）⇒ 再等 212 秒，最舊那筆就滾出 300s 視窗、釋出 1 個名額
   ⏳ 這一條的 reset 在 2026-10-09T20:00:00.447546+00:00（6 小時內） ⇒ 這道節流很快就會自己解除。
   🔻 降級建議：kind=weekly_scoped 已進收緊帶 ⇒ 建議派工帶 model: sonnet/haiku 續跑（只建議不自動改模型；cap 不受本行影響）。
   🤖 模型角色（.env AUTOSDD_MODEL_*）：主控=（空＝沿用存檔／設定鏈）｜子代理=sonnet｜降級=haiku（主控值只管無人喚醒窗口；互動視窗自己的模型 .env 管不到，派工請明寫 model:）
  來源=cache 量測於=2026-10-10T00:52:44+08:00
```
`AUTOSDD_MODEL_HELMSMAN=fable`（只列模型兩行）：
```
   🔻 降級建議：kind=weekly_scoped 已進收緊帶 ⇒ 建議派工帶 model: sonnet/haiku 續跑（只建議不自動改模型；cap 不受本行影響）。
   🤖 模型角色（.env AUTOSDD_MODEL_*）：主控=fable｜子代理=sonnet｜降級=haiku（主控值只管無人喚醒窗口；互動視窗自己的模型 .env 管不到，派工請明寫 model:）
```
`AUTOSDD_MODEL_SUBAGENT='bad value;'`（只列模型兩行；壞值在 stdout 的角色行上出聲、退回 sonnet；stderr 只有既有的「session 來源」行）：
```
   🔻 降級建議：kind=weekly_scoped 已進收緊帶 ⇒ 建議派工帶 model: sonnet/haiku 續跑（只建議不自動改模型；cap 不受本行影響）。
   🤖 模型角色（.env AUTOSDD_MODEL_*）：主控=（空＝沿用存檔／設定鏈）｜子代理=sonnet｜降級=haiku（主控值只管無人喚醒窗口；互動視窗自己的模型 .env 管不到，派工請明寫 model:） ⚠️ 有 1 個設定值不合法、已退回預設：AUTOSDD_MODEL_SUBAGENT='bad value;' 不是合法模型值（要 opus／sonnet／haiku／fable 別名或含家族字的完整 id，且只含 A-Za-z0-9._[]-）⇒ 採用預設 'sonnet'
```
判讀：角色行值＝主控空／子代理 sonnet／降級 haiku ✓；HELMSMAN=fable → 主控=fable ✓；壞值 → 子代理仍 sonnet 並出聲 ✓；降級建議行維持舊字面 `model: sonnet/haiku` ✓（預設輸出逐字不變）。

### 3.2 `resume_route.resume_argv／fresh_argv` 對 HEAD 版逐字比對（腳本 qa_argv.py）
HEAD 版＝`git show HEAD:tools/lib/resume_route.py` 以 `exec` 載入，`__file__` 設成真路徑（`_REPO_ROOT` 因此相同）；`AUTOSDD_HANDBACK_DIR` 指進 scratchpad。
```
HEAD  resume:
   ["claude", "-p", "-r", "sid-1", "讀 plan，照它第 3 節做。", "--permission-mode", "acceptEdits", "--settings", "/Users/wuweihong/Antigravity/AISDCL_Agent/.claude/settings.unattended.json", "--add-dir", "/x/plan", "/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/qa_w1/hb"]
NEW   resume (helmsman 空):
   ["claude", "-p", "-r", "sid-1", "讀 plan，照它第 3 節做。", "--permission-mode", "acceptEdits", "--settings", "/Users/wuweihong/Antigravity/AISDCL_Agent/.claude/settings.unattended.json", "--add-dir", "/x/plan", "/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/qa_w1/hb"]
HEAD  fresh:
   ["claude", "-p", "讀 plan，照它第 3 節做。", "--permission-mode", "acceptEdits", "--settings", "/Users/wuweihong/Antigravity/AISDCL_Agent/.claude/settings.unattended.json", "--add-dir", "/x/plan", "/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/qa_w1/hb"]
NEW   fresh (helmsman 空):
   ["claude", "-p", "讀 plan，照它第 3 節做。", "--permission-mode", "acceptEdits", "--settings", "/Users/wuweihong/Antigravity/AISDCL_Agent/.claude/settings.unattended.json", "--add-dir", "/x/plan", "/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/qa_w1/hb"]
空 helmsman：resume 逐字相同 = True ｜fresh 逐字相同 = True
NEW   resume (helmsman=fable):
   ["claude", "-p", "-r", "sid-1", "讀 plan，照它第 3 節做。", "--permission-mode", "acceptEdits", "--settings", "/Users/wuweihong/Antigravity/AISDCL_Agent/.claude/settings.unattended.json", "--model", "fable", "--add-dir", "/x/plan", "/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/qa_w1/hb"]
NEW   fresh  (helmsman=fable):
   ["claude", "-p", "讀 plan，照它第 3 節做。", "--permission-mode", "acceptEdits", "--settings", "/Users/wuweihong/Antigravity/AISDCL_Agent/.claude/settings.unattended.json", "--model", "fable", "--add-dir", "/x/plan", "/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/qa_w1/hb"]
resume: --settings@7 --model@9 --add-dir@11 → settings 值之後=True, 緊貼 settings 值之後=True, 在 --add-dir 之前=True, --model 值='fable', --add-dir 後恰 2 個值=True
fresh: --settings@5 --model@7 --add-dir@9 → settings 值之後=True, 緊貼 settings 值之後=True, 在 --add-dir 之前=True, --model 值='fable', --add-dir 後恰 2 個值=True
去掉 --model fable 後與 HEAD 版相同： True True
壞 helmsman：resume 含 --model = False ｜與 HEAD 逐字相同 = True
role_env 預設 = {'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet'}
role_env SUBAGENT=opus = {'CLAUDE_CODE_SUBAGENT_MODEL': 'opus'}
probe_argv 預設 = ['claude', '-p', 'ok', '--model', 'haiku', '--output-format', 'json']
HEAD 版 planner 寫死的探針 argv 形狀 = ['claude','-p','ok','--model','haiku','--output-format','json']
```
判讀：helmsman 空 ⇒ resume／fresh 兩路 argv 與 HEAD **逐字相同** ✓；helmsman=fable ⇒ `--model fable` 緊貼 `--settings <檔>` 之後、在 `--add-dir` 之前、`--add-dir` 後恰 2 個值，去掉 `--model fable` 後與 HEAD 版相同 ✓；夾帶旗標的壞值（`sonnet --dangerously-skip-permissions`）⇒ 不帶 `--model`、argv 與 HEAD 逐字相同 ✓；`probe_argv` 預設形狀＝舊寫死的 `[claude,-p,ok,--model,haiku,--output-format,json]` ✓。

### 3.3 SessionStart 簡報（真 `session_brief.sessionstart_brief`＋真 `quota_gate.policy_env`；額度快取以合成 OSError 替身）
```
[真 policy_env] 總長 1309 字；角色段： 模型角色（.env AUTOSDD_MODEL_*）：主控=（空＝沿用存檔／設定鏈）｜子代理=sonnet｜降級=haiku（主控值只管無人喚醒窗口；互動視窗自己的模型 .env 管不到，派工請明寫 model:）。查證指令（輸出很短，直接跑；要 rc 先導檔再讀，別在 `| head`／`| tail` 之後讀 rc）：這兩條照字面執行（相對路徑、cwd 已是 repo 根；
[三鍵全壞] 總長 1697 字；含 ⚠️： True ；problems 引用長度已有界（每筆 ≤40 字元＋固定說明）
```
簡報本文 1309 字元（含角色段）；三鍵全壞時 1697 字元，problems 引用長度有界。

### 3.4 import 起手序（各以一個全新直譯器、先 import 該模組、再 import 其餘全部）
```
first=model_roles rc=0
first=quota_policy rc=0
first=quota_policy_env rc=0
first=quota_messages rc=0
first=quota_gate rc=0
first=resume_route rc=0
first=session_brief rc=0
first=session_resume_planner rc=0
```
（加 `session_resume_planner` 起手共 8 種，全部 rc=0；無循環 import。）

## 4. 探針證據（任務書第 5 項；只讀 probe_resume_model_113.json，未重跑）

檔：scratchpad/113/probe_resume_model_113.json（claude 2.1.295）。逐字摘出的量：
- call1（`-p "ok" --model haiku`）：modelUsage 鍵＝`['claude-haiku-5-5']` ✓（任務書預期成立）。session_id＝a119e01d-d4a6-4ec5-bc0b-1ac1ecf29b66。
- call2（`-p "ok" -r <call1.session_id> --model sonnet`）：session_id **相同**（同 session 續跑）；modelUsage 鍵＝`['claude-haiku-5-5', 'claude-sonnet-5-5']`——**不是「只含 sonnet 家族」**（任務書預期不成立）。
- 但「新回合只跑在 sonnet」由三條獨立算術旁證支持（逐項取自該 JSON）：
  1. call2 的 haiku 列 9 個數值欄（inputTokens 2／outputTokens 64／thinkingTokens 38／cacheRead 11343／cacheCreation 8406／webSearch 0／costUSD 0.00182683／contextWindow 1000000／maxOutputTokens 128000）與 call1 的 haiku 列**逐項相等**＝session 累計的舊回合；
  2. call2 頂層 `usage`（本次呼叫自身用量）：input 2／output 46／cache_creation 8767／cache_read 11343，四欄與 sonnet 列（inputTokens 2／outputTokens 46／cacheCreation 8767／cacheRead 11343）**逐項相等**；
  3. `total_cost_usd`(call2)＝0.039627430000000005＝haiku 列 0.0018268300000000002 ＋ sonnet 列 0.0378006（差 0.0）；call2 總額 − call1 總額＝0.0378006＝sonnet 列。
- Dev 敘述「claude-haiku-5-5 那列與 call1 逐項相同」嚴格說只在**數值欄**成立：call1 的 haiku 列有 `canonicalModel`／`costBasis`／`provider` 三個 metadata 鍵，call2 的 haiku 列沒有（整列 dict 相等為 False）；缺 metadata 的樣貌與「由存檔還原的累計列」相符、而非本次 API 呼叫列——與 Dev 結論同向，但「逐項相同」要改成「數值欄逐項相同」。
- 探針涵蓋面（誠實劃界）：最小三旗標形（`-p -r --model`）、haiku→sonnet；沒涵蓋完整喚醒 argv（另有 `--permission-mode`／`--settings`／`--add-dir`）與 fable（QA1-05）。

## 5. 文件／註解（任務書第 6 項）

- 任務書字面指令 `git diff tools/ .env.example | grep -nE "R2[1-9][0-9]"`：**現在的工作樹有 4 行命中，全部來自 `tools/lib/governance_docs.py`**（1 行既有 R210 context＋3 行新增的 R211 證據檔登記）。該檔不是 W1 範圍內的檔（mtime 00:56:31 晚於 Dev 交件，內容是登記 CrossPlatform_R211_* 兩份證據檔）——主控側的後續編修，與 W1 無關。
- 限縮到 W1 檔（planner／quota_gate／quota_messages／quota_policy_env／resume_route／session_brief／skip_tag_policy／test_context_budget_guard／.env.example）：`R2[1-9][0-9]` **零命中**；新增行裡唯一的 R 號 token＝planner `_run_resume` 那條既有長行的 `R115 修復 F3`（−／+ 兩版逐字都有，原文＋既有 `round-label-ok`，不是新增引用）。新檔 model_roles.py／test_model_roles.py：R 號 token 零、DEF- 零（「improving_113」字樣可）。
- DEF-ID：W1 新增行與新檔皆零個 ⇒ 「到缺陷帳本與 archive 查存在」沒有可查的對象。
- skip／xfail：test_model_roles.py 零（grep 只命中兩處字串字面 `--dangerously-skip-permissions`）；test_model_roles 與 774 組合的輸出尾段亦無 skipped／expected failures。
- E501／EAW：repo 根**沒有**任何 ruff 設定（ruff.toml／pyproject.toml 皆不存在），`tools/` 下檔案就近解析到 `tools/ruff.toml`（`line-length = 100`；規則含 E501，`ruff check --show-settings` 實查有列 `line-too-long (E501)`）⇒ 1.4 的 All checks passed 即涵蓋 E501；自量（`unicodedata`，W／F 算 2 欄）test_model_roles.py 537 行最大 99、model_roles.py 101 行最大 99，over100＝[]。
- noqa：新檔只有 import 行的 `E402`（sys.path 前置後的 import，同目錄慣例）；W1 diff 新增行的 `noqa: E501` 只出現在被改寫的那條既有 planner 長行（−／+ 各 1，淨 0），不增 E501 存量債。

## 6. test_model_roles.py（537 行／56 支）重複評估——只建議、未改

檔內 13 個 class、56 支；整體不算冗長。逐組比對後的重疊候選（行數＝AST 取的方法跨度＋其後 1 行空白）：

| 候選 | 與誰重疊 | 可省 | 信心 |
|---|---|---|---|
| EnvSpecDeclaresTheThreeRolesTest.test_the_shipped_example_file_carries_the_three_keys（L99–102） | test_quota_policy.TestM6EnvExampleBidirectionalLock（磁碟檔＝產生器輸出）＋同 class 的列檢查 | 5 | 高 |
| ModelRolesModuleShapeTest.test_every_key_has_its_real_reader_in_the_roles_module（L513–517） | test_context_budget_guard.QuotaEnvFileIsActuallyLoadedTest 讀者元組（本包已加 model_roles.py） | 6 | 高（本測試略強：字面必須住在 model_roles.py，但價值低） |
| ModelHintLineTest.test_a_free_band_still_prints_no_hint_whatever_the_roles_are（L419–421） | 同 class 的 test_model_lines_prints_the_hint_only_when_tight…（free 帶斷言 `assertNotIn("降級建議")`）＋ test_quota_policy L2307 | 4 | 中 |
| ProbeArgvTest 的兩支（L288–290、L292–295） | ProbeQuotaModelTest 的 test_an_explicit_model_argument_still_wins／test_the_default_probe_uses_the_downgrade_role（planner 層，經 probe_argv） | 9 | 中（會失去 probe_argv 單元層／接線層的分層） |
| SessionBriefRolesTest 前兩支（L469–477）可併一支；LoadModelRolesTest 首支（L107–110）兩個 assertEqual 同義 | — | 各約 4 | 低 |

結論：**無明顯重複需要合併**。高信心兩項合計約 11 行（2%）；全部候選上限約 34 行（6.3%）。建議：不為此再動一輪；若收尾窗口恰好需要再擠護欄層淨額（本包 +539 已佔主軌上限 517 以上，見 Dev log §5），先砍前兩項即可，其餘會犧牲分層可讀性。

## 7. 風險追問第 7 點——喚醒窗口子行程 `CLAUDE_CODE_SUBAGENT_MODEL` 的實際碼路徑

結論一句：**屬實且順序正確**——planner `_run_resume` 同一物理行真的併入 `resume_route.role_env()`；`role_env()` 讀的是 `os.environ`（不是 `.env` 合併視圖），`.env` 的值由 planner `main()` 第一個呼叫 `quota_gate.apply_env_defaults(os.environ)` 先填進 `os.environ`，而三個新鍵在 `ENV_SPEC` 內（該函式的白名單）。逐項證據：

1. 同一物理行：`sed -n 1227p tools/session_resume_planner.py` 含 `subprocess.run(route["argv"], …` 且 `env={**os.environ, UNATTENDED_ENV: "1", **resume_route.role_env()}`（grep -c 該行＝1）；planner 全檔 `role_env` 只出現在這一行（零新增行，planner 斷言行 746→746）。
2. 讀取來源：`resume_route._roles()` ＝ `model_roles.load_model_roles(os.environ)[0]`——**只讀 `os.environ`**。
3. 呼叫順序：`session_resume_planner.main()`（L1527）第一個實質呼叫是 L1533 `quota_gate.apply_env_defaults(os.environ)`，之後才 `build_parser()` 與各分支（含 L1356 `_run_resume`）；唯一 spawn 喚醒窗口的站點是 L1227（planner／relay_machine／resume_route／quota_escalation 內 `subprocess.run/Popen/check_output/call` 全查過：planner L318＝PowerShell 排程腳本、L503＝`probe_quota` 付費探針、L1227＝喚醒 spawn，quota_escalation L562＝通知指令；relay_machine／resume_route 無；L1285／L1560 只是 `probe_quota(...)` 的呼叫）。
4. `apply_env_defaults` 的填入規則：只填 `ENV_SPEC` 宣告的鍵、且行程 env 缺席（或空白）才填；`policy_env()` 的合併是 `{**dotenv, **os.environ}`，真環境變數（含空字串）贏過 `.env`——所以 `--pace`／簡報（吃 `policy_env()`）與喚醒路徑（吃 `os.environ`）看到的是同一份值。
5. 該順序已有既存機械鎖：`test_context_budget_guard.PlannerMainAlsoPrefillsFromDotEnvTest.test_planner_main_calls_the_prefill_before_the_parser`（AST：planner `main()` 恰有一次 `apply_env_defaults` 呼叫、且在 `build_parser` 之前；延伸回歸內綠）。
6. 本場自跑的端到端（腳本 qa_e2e_dotenv.py；tmp 根放 `.env`：HELMSMAN=fable／SUBAGENT=opus，行程環境先清空；零 token）：
```
before apply: role_env = {'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet'} | model_argv in resume = False
apply_env_defaults filled: ['AUTOSDD_MODEL_HELMSMAN', 'AUTOSDD_MODEL_SUBAGENT']
after  apply: role_env = {'CLAUDE_CODE_SUBAGENT_MODEL': 'opus'}
after  apply: --model fable | 緊貼 settings 值之後 = True
real env haiku beats .env opus: role_env = {'CLAUDE_CODE_SUBAGENT_MODEL': 'haiku'}
```
   判讀：填入前 role_env＝預設 sonnet 且 argv 不帶 `--model`；`apply_env_defaults` 回填 `['AUTOSDD_MODEL_HELMSMAN', 'AUTOSDD_MODEL_SUBAGENT']` 後 role_env＝opus、argv 帶 `--model fable` 且緊貼 `--settings` 值之後；真環境變數 haiku 贏過 `.env` 的 opus ✓。
7. 測試層的誠實劃界：W1 測試把鏈拆成兩段釘（`DotenvReachesTheRolesTest`：`apply_env_defaults`→`load_model_roles`；`WakeSpawnCarriesTheRolesTest`：直接設 `os.environ` 後打真 `_run_resume`），**沒有一支測試把 `planner.main()`→`_run_resume` 整條串起來**；整體由既存 AST 鎖＋本場的腳本式端到端承擔——結構上可接受（與 `AUTOSDD_RESUME_OFF` 等既有鍵同型），記為資訊、不立缺陷。

8. R2 機制（子代理預設模型）的**證據層級**（本場只讀、零 token）：claude 2.1.295 二進位（/Users/wuweihong/.local/share/claude/versions/2.1.295，用 python mmap 取字串上下文）內 `CLAUDE_CODE_SUBAGENT_MODEL` 出現 8 次（另 `_FORCE` 17 次）；其中 `function gme(){let e=a.CLAUDE_CODE_SUBAGENT_MODEL;return e&&e!=="inherit"?e:"inherit"}` 與 `OU(...)` 內 `w=()=>{let P=gme();if(P==="inherit")return h();let H=A(Dt(P),P);…`——即環境變數被讀取、`inherit` 視為不覆寫、其餘值經別名解析 `Dt`；`QN(e)` 另把 `inherit`／`default` 視為「無子代理模型覆寫」。這與 Dev log B1「`inherit` 是 Claude Code 認的合法值」及 design_facts 的序位一致；**但本場與 Dev 都沒有真的派一個不帶 model 的子代理去看它跑在哪個模型**（那要燒 token），所以「注入 → 子代理真的變 sonnet」這一格是文件＋二進位字串層證據，不是行為層證據（併入 QA1-05）。

## 8. 延伸回歸（自加，非任務書指定；因 W2 進行中不跑 run_root_unittests.py 全套，改跑 W1 觸及面的相關模組）

指令（tools/tests 下；17 個模組，涵蓋 test_context_budget_guard 整檔、sentinel／wake-chain／quota 對帳／mac endurance／run_root_unittests／skip ceiling／hook 載具…）：
`python -m unittest test_context_budget_guard test_sentinel_tick_e2e_r145 test_wake_chain_halt_r278 test_quota_reconcile_gap test_root_guard_known_model_r145 test_mac_endurance_r83 test_guard_line_taxonomy_r99 test_negative_existence_claims_r82 test_claim_provenance_r86 test_schedule_capability_parity test_run_root_unittests test_skip_ceiling_ratchet_direction test_nightly_interpreter_determinism test_git_hooks_install_common test_check_hooks_liveness test_windowsapps_guard_cross_consistency test_block_destructive_git_r83`
（刻意排除：test_resume_cost＝W2 範圍；test_adr_xplat001_c1c2_lock／test_doc_loc_baseline_freshness_r60＝護欄層棘輪與 ONBOARDING／ADR 基線，Dev 已知紅且現在混入 W2／W3 的行數，單看無意義。）
第一次（非 -v）的關鍵行（`grep -E "^(Ran 1997 |FAILED|FAIL:|extended_rc|AssertionError: 70 not)"`；該輸出另有若干既有測試自己印的 `Ran 1 test…／OK` 子行程摘要，已濾掉）：
```
FAIL: test_scan_surface_is_not_silently_empty (test_schedule_capability_parity.TestUnittestDiscoverConformance.test_scan_surface_is_not_silently_empty)
AssertionError: 70 not greater than or equal to 71 : 下限 70 已過期（實測 89，下限只剩實測的 79%、低於 80%）——請把 _SCAN_FLOOR 重釘為 71
Ran 1997 tests in 224.870s
FAILED (failures=1, skipped=18)
extended_rc=1
```
第二次（-v）重跑的摘要與 skipped 逐項（兩次皆 1997 tests／failures=1／skipped=18，耗時 224.870s／199.986s）：
```
3660:Ran 1997 tests in 199.986s
3662:FAILED (failures=1, skipped=18)
3664:extended_v_rc=1
--- 失敗 ---
3651:FAIL: test_scan_surface_is_not_silently_empty (test_schedule_capability_parity.TestUnittestDiscoverConformance.test_scan_surface_is_not_silently_empty)
3657:AssertionError: 70 not greater than or equal to 71 : 下限 70 已過期（實測 89，下限只剩實測的 79%、低於 80%）——請把 _SCAN_FLOOR 重釘為 71
--- skipped 逐項歸類（-v 輸出；18 筆）---
  18 [WINDOWS-NATIVE-ONLY]
（18 筆皆為既有的 [WINDOWS-NATIVE-ONLY] 平台標籤 skip，mac 上本就跳過；W1 新測試檔 0 筆。理由前綴逐筆，依 -v 輸出順序）
  - powershell.exe 5.1 的主控台 codepage 行為只在 Windows 成立
  - Get-ScheduledTask 只在 Windows 成立
  - console 配置是 Windows 專屬概念
  - console 配置是 Windows 專屬概念
  - console 配置是 Windows 專屬概念
  - console 配置是 Windows 專屬概念
  - 僅 Windows 有 schtasks 可現查
  - 同上：本分支只在 Windows 有行為
  - 同上：本分支只在 Windows 有行為
  - schtasks 武裝只在 Windows 成立
  - 同上：本分支只在 Windows 有行為
  - 需要原生 PowerShell 引擎解析 .ps1
  - 阻斷契約只在 Windows 成立；非 Windows 分支另有專屬 case
  - 阻斷契約只在 Windows 成立；非 Windows 分支另有專屬 case
  - 阻斷契約只在 Windows 成立；非 Windows 分支另有專屬 case
  - 阻斷契約只在 Windows 成立；非 Windows 分支另有專屬 case
  - 阻斷契約只在 Windows 成立；非 Windows 分支另有專屬 case
  - 此測試用 .cmd 假直譯器驗證 WindowsApps guard，依賴 Windows PATHEXT 解析語意，僅
```
判讀：唯一紅＝`test_schedule_capability_parity.TestUnittestDiscoverConformance.test_scan_surface_is_not_silently_empty`，訊息逐字：「70 not greater than or equal to 71 : 下限 70 已過期（實測 89，下限只剩實測的 79%、低於 80%）——請把 _SCAN_FLOOR 重釘為 71」。成因＝tools/tests 的 test_*.py 現在是 89 支（HEAD 追蹤 87＋W1 的 test_model_roles＋W2 的 test_resume_cost；單看 W1 是 88 支，`int(88×0.8)=70`，下限 70 剛好合格）。見 QA1-02。

### 8.1 hermeticity：行程環境已帶角色變數時，W1 觸及面的測試仍須綠（自加）
動機：規格寫「本機 `.env` 設 `fable`」＝使用者之後真的會在 `.env`／環境裡設這三個鍵；`policy_env()` 是 `{**dotenv, **os.environ}`，所以「行程環境帶值」與「`.env` 帶值」對測試等價（本場不碰真 `.env`）。
做法：`AUTOSDD_MODEL_HELMSMAN=fable AUTOSDD_MODEL_SUBAGENT=opus AUTOSDD_MODEL_DOWNGRADE=sonnet CLAUDE_CODE_SUBAGENT_MODEL=haiku CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` 前綴，各跑一次：
- `python -m unittest test_model_roles`：
```
Ran 56 tests in 2.620s
OK
rc=0
```
- 寬集合（test_quota_policy／test_session_brief／test_mac_readiness_r82／test_platform_utils_dedup／test_subprocess_encoding_hygiene／test_platform_neutral_paths＋§8 清單去掉 test_schedule_capability_parity，共 22 個模組）：
```
Ran 2702 tests in 328.070s
OK (skipped=18)
ambient_wide_rc=0
（skipped=18 與 §8 同一批既有 [WINDOWS-NATIVE-ONLY] 平台標籤 skip；本次未含 test_schedule_capability_parity，所以不含 QA1-02 那一個紅）
```

## 9. Findings

| ID | 等級 | 標題 | 動作 |
|---|---|---|---|
| QA1-01 | P3 | 探針 call2 的 modelUsage 鍵＝haiku＋sonnet，任務書預期「只含 sonnet」不成立；Dev 敘述「逐項相同」缺 3 個 metadata 鍵 | **條件**：下游落款文字（improving_113 §4～§8／證據檔／PRD v2.1.16）一律用 §4 的精確表述 |
| QA1-02 | P3（整合，非 W1 缺陷） | tools/tests 檔數 89 ⇒ 下限 70 過期、應為 71；兩處同源紅 | 收尾單人窗口重釘一個常數 |
| QA1-03 | P4 | LOC 落點偏離：quota_messages +10（規格 ≤+8）未入 Dev 偏差表；session_brief +10（規格 ≤+2，Dev D4 已列） | 記帳；皆在 tier 預算內 |
| QA1-04 | P4 | 無人喚醒不落「生效角色」痕跡（Dev B3 屬實） | 資訊；Dev 建議放 resume_route 側 |
| QA1-05 | P4 | 完整喚醒 argv、fable、子代理環境變數的行為層真機證據都未驗 | 資訊；探針禁重跑，需另行授權 |
| QA1-06 | P4 | `quota_gate.py:136` 的 `model_hint_line` re-export 現無任何消費者 | 資訊；可留可刪 |
| QA1-07 | P4 | 測試重複可省 ~11（高信心）～34 行 | 資訊（§6） |
| QA1-08 | P4 | 範圍外未驗：AutoClaude ENV 鏡射鎖；Dev §5 的 MIN_TESTS／零相依餘裕／護欄行數棘輪數字未獨立重驗 | 收尾全套驗 |
| QA1-09 | P4（設計面→SD 鏡，QA 不裁決） | SUBAGENT 恆注入無出口（Dev B1）；DOWNGRADE 兼任付費探針模型但值域含 fable／opus | 轉 SD 鏡 |

### QA1-01（P3）探針 call2 modelUsage 鍵不是「只含 sonnet」
- 證據：§4。call2 `modelUsage` 鍵＝`claude-haiku-5-5`＋`claude-sonnet-5-5`；haiku 列是累計舊回合（數值欄與 call1 逐項相等、缺 canonicalModel／costBasis／provider）。
- 為什麼不是 P2：語意結論「`-r <sid> --model X` 的新回合真的跑在 X」有三條獨立算術旁證（§4 的 1～3）；W1 的碼與測試不依賴這句敘述。
- 為什麼仍要條件：任務書預期與證據不符，若有人把「modelUsage 只含 sonnet」寫進 PRD／證據檔就是一句假話。落款請寫：「call2 的 modelUsage 多出 sonnet 列（新回合；頂層 usage 與該列逐項相等），haiku 列為 session 累計的舊回合（數值欄與 call1 逐項相同）」。
- 重現：
  `python - <<'EOF'`／`import json; d=json.load(open('<scratchpad>/113/probe_resume_model_113.json')); j2=d['call2']['json_without_result']; print(list(j2['modelUsage']), j2['usage']['output_tokens'], j2['modelUsage']['claude-sonnet-5-5']['outputTokens'])`／`EOF`
  預期印 `['claude-haiku-5-5', 'claude-sonnet-5-5'] 46 46`。

### QA1-02（P3，整合）tools/tests 檔數 89 ⇒ 下限 70 過期
- 證據：現況 `tools/tests/test_*.py` 共 89（`ls test_*.py | wc -l`＝89；排除 W2 的 test_resume_cost.py＝88；`git ls-files`＝87）。`skip_tag_policy.tree_floor_problems` 現場輸出「tools/tests：下限 70 已過期（實測 89，下限只剩實測的 79%、低於 80%）——請把 _TREE_FILE_FLOORS['tools/tests'] 重釘為 71」；`test_schedule_capability_parity` 的 `_SCAN_FLOOR` 是同一個常數的導出（`_SCAN_FLOOR = _SKIP_TREE_FLOORS["tools/tests"]`），所以同一個 70 在兩個消費者各紅一次：`tree_floor_problems`（run_root_unittests 靜態掃描的判準本體，本場直呼、未跑整個 runner）與 `test_schedule_capability_parity`（延伸回歸唯一的 failures=1）。
- 歸因：W1 單獨成立（88 支：`int(88×0.8)=70`，Dev 的 69→70 正確且必要）；W2 的新測試檔進樹後即過期。Dev 的全套紅清單（10 紅）不含它，因為當時 W2 檔還沒進樹。
- 動作：收尾窗口在 W2／W3 都停工後，以最終檔數重釘 `_TREE_FILE_FLOORS['tools/tests']`（現況 → 71），註解沿用 W1 那段的格式（逐字照掃描器指示、零加減推算）；同輪的 MIN_TESTS／零相依餘裕也要重量（QA1-08）。
- 重現：`cd tools/tests && AUTOSDD_SENTINEL_OFF=1 python -m unittest test_schedule_capability_parity.TestUnittestDiscoverConformance.test_scan_surface_is_not_silently_empty`（現況會紅；W2 檔不在樹內時綠）。

### QA1-03（P4）LOC 落點偏離（規格 §3.1「LOC 落點」）
- 證據：§1.6 HEAD 側改前值——quota_messages 369→379（+10，規格 ≤+8，超 2）；session_brief 317→327（+10，規格 ≤+2，Dev D4 已說明＝fail-open try-import＋`_models_note` 的既有紀律）。quota_messages 的 +10 沒有出現在 Dev §2 偏差表（D3 只說 pace_report 淨 0、把組合收進 `model_lines`）。兩檔仍在預算內（379/400、327/400）。
- 動作：記帳即可。

### QA1-04（P4）無人喚醒不落「生效角色」痕跡
- 證據：`_run_resume` 的痕跡只有 `route_chosen`（strategy／why）、`relay_snapshot_before` 等；`--model` 值與注入的 `CLAUDE_CODE_SUBAGENT_MODEL` 都不在 resume log；壞值在無人窗口只退預設、不出聲（出聲只在 `--pace`／SessionStart 簡報，有人在場才看得到）。Dev log B3 屬實，碼路徑已逐項核對。
- 動作：資訊。若要補，Dev 建議放 resume_route 側（planner 無餘裕）；本場不構造變體。

### QA1-05（P4）完整喚醒 argv、fable、以及「子代理環境變數真的讓子代理換模型」都沒有行為層真機證據
- 證據 1：探針為 `-p "ok" -r <sid> --model sonnet`（haiku→sonnet）；真實喚醒 argv 是 `claude -p [-r sid] <prompt> --permission-mode acceptEdits --settings <檔> --model <X> --add-dir <A> <B>`。`--model` 為單值旗標、位置由既有姊妹鎖與新鎖雙重釘住，commander 類 CLI 解析風險低，但**沒有真機解析證據**。
- 證據 2：`CLAUDE_CODE_SUBAGENT_MODEL` 只有文件＋二進位字串層證據（§7 第 8 點），沒有派一個不帶 model 的子代理去看 modelUsage。
- 任務書禁重跑探針、本場零 token，故列未驗證；若要補，一次便宜呼叫即可（`CLAUDE_CODE_SUBAGENT_MODEL=haiku claude -p … --model sonnet`，要求派一個無 model 參數的子代理，看 modelUsage 有無 haiku 列）——需掌舵者另行授權。

### QA1-06（P4）`quota_gate.py:136` 的 `model_hint_line` 無消費者
- 證據：`pace_report` 改走 `quota_messages.model_lines` 後，`model_hint_line` 在 quota_gate.py 的 AST 使用 0 次；全 repo（排除 AutoClaude／.venv／.git）grep 只剩 `quota_messages` 自己與測試（`QM.model_hint_line` 的 QM 是 quota_messages）。ruff 不報。它仍符合 quota_messages 檔頭的「quota_gate re-export、消費端零改動」慣例，所以不是缺陷；若要換 tier 餘裕（495/500）可刪，刪前以 grep 確認無外部 `quota_gate.model_hint_line`。

### QA1-07（P4）測試重複——見 §6。

### QA1-08（P4）範圍外／未獨立重驗
- AutoClaude 側 ENV 鏡射鎖（`tests/test_r82_…`、`test_r86_…`）：Dev log §7 自陳未驗（xdist 掛住被收掉）；W1 的 ENV_SPEC +3 列是否影響其比對是推論；AutoClaude/** 屬 W3，本場未碰。
- Dev log §5 的 `MIN_TESTS`（5207→5263、零相依餘裕 61／223）、護欄層行數（114811→115350 +539 > 主軌上限 517）數字：本場不跑 run_root_unittests.py 全套、不跑 `--print-guard-lines`（會混入 W2／W3 的行數），**未獨立重驗**；5207+56＝5263 的算術與新測試 56 支一致（本場自測 56）。

### QA1-09（P4，設計面，轉 SD 鏡）
- B1（Dev 自陳，本場碼路徑核實屬實）：`load_model_roles` 對 subagent 恆回非空（`raw or default`），`role_env()` 預設實測＝`{'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet'}`——每個喚醒窗口都被注入、沒有「不注入」出口（`inherit` 被 `family_key` 拒收）。規格 §3.1 表格寫的就是預設 sonnet 且注入，所以非偏離；是否要出口是設計裁決。
- DOWNGRADE 兼任付費探針模型，值域含 fable／opus：錯設成貴家族時探針成本放大；規格明載。

## 10. 未驗證／範圍外／資源收尾

未驗證（只能在該環境／範圍外）：完整喚醒 argv 與 fable 的真機解析（QA1-05）；AutoClaude 側 ENV 鏡射鎖（QA1-08）；Windows／PS 5.1（純 Python 檔，本場 mac）；py39 真直譯器（本機無 3.9，且 /usr/bin 殼不碰；只有既有靜態鎖 `test_mac_readiness_r82` 與 Dev 的 `ast.parse(feature_version=(3,9))`）；run_root_unittests.py 全套（W2 進行中）；`--pace` 以外的 hook 實跑（SessionStart 簡報走真函式、未經 hook 行程）。

資源收尾（開了→收了）：
- 突變 harness 暫改 2 檔→已 `cp` 還原、sha256 相同（§2）；備份留在 scratchpad（bk_*.py）。
- 背景任務 2 個（bylutm8ad＝延伸回歸、bl10owhye＝延伸回歸 -v）→皆自然結束（見 §8）。
- `--pace` 3 次：來源=cache、未打端點；它們有既有的狀態副作用（pace_contract／燃燒帳／穩定性狀態），與平常派工前現查相同。
- `tools/.last_failure_*.log`（gitignored 的 runner 失敗明細）：我跑 `test_run_root_unittests` 會產生合成失敗明細（`test_p8fx8` 合成樹的 ImportError，0 failures／1 errors）；同時段另有他人的全套 run（01:06:59 那份 17KB、11 failures，不是我跑的），無法逐份歸屬 ⇒ **未刪、未碰**（刪錯會妨礙別人診斷自己的 run），請收尾窗口一併清。
- tmp 夾具目錄 `qa-w1-env-*`→腳本內已 rmtree；`AUTOSDD_HANDBACK_DIR` 指向的 scratchpad `hb/` 空目錄留在 scratchpad。
- 無 git 寫入（只用 git diff／git show／git status／git ls-files）、無 worktree、無 Docker、無 claude -p 呼叫；未碰 .claude/、根 CLAUDE.md、缺陷帳本、PRD、ONBOARDING.md、AutoClaude/、W2 檔。
- 本檔與全部暫存產物都在 scratchpad/113/qa_w1/（非 repo）。

## 〈T-5 W2 SD＋QA 合一鏡〉（review_w2_113.md）

# W2 `resume_cost_pp` 喚醒成本落帳｜SD 設計符合性＋QA 零信任審查（improving_113）

- 審查者：W2 唯讀審查鏡（Sonnet；SD＋QA 合一）。範圍：`tools/lib/resume_cost.py`（新）、`tools/tests/test_resume_cost.py`（新）、`tools/lib/relay_machine.py`（raw +5／斷言 +3）。W1／W3 的檔案未讀、未評。
- 方法：Developer 交件 `w2_dev_log_113.md` 的每個數字自己重跑；repo 全程唯讀（三檔 sha256 與開場逐位元組相同、`git status --short` 三檔狀態與開場相同，見 §10）；所有突變／探針／原型只在 scratchpad。
- 環境：`python`＝repo `.venv` 3.11.15；`python3`＝`/usr/bin/python3` 3.9.6（僅用於 py39 真跑）；單跑前 `export AUTOSDD_SENTINEL_OFF=1; unset AUTOSDD_PARALLEL_TESTS`，在 `tools/tests` 目錄下載入；未跑 `run_root_unittests.py` 全套。
- 產物：輸出檔在 `.../scratchpad/113/w2rev/`；突變 harness `run_mut.py`／`run_mut_patched.py` 與各副本在 `.../scratchpad/113/mut/`。

## 0. 判決

**VERDICT: APPROVE**（無 P2；P3 六條建議同 commit 順手收，P4 登記）

- 規格九欄＋`model` 齊備；「量不到寫 None 不寫 0」在每一條分支成立（隨機 4000 案＋獨立 oracle 零不符）；接線只在 `state=="resumed"` 落帳；痕跡走 `endurance_env.trace_dir()`、append 走 `quota_ledger.append_record`；AST 鎖存在、對它自稱的三種形態有牙；py39 本體合規（repo 判準＋真 3.9.6 直跑）。
- 我自己的 6 個突變：**3 擊殺、3 存活**（M2／M5／M6，皆測試缺口，W2-01～03）。Developer 的 23 個突變重跑結果與他交件一致（22 擊殺、M17 存活）。
- 第 4 點結論：**能零成本修，且不必動 state 或守衛面**——planner 在每窗 `subprocess.run` 前一刻已把 `relay_snapshot_before` 事件（含秒精度 `at`）落進 `settle_window` 手上就有的 `log`，以該 `at` 取代 `reset_at` 當下界即可同時修好接力窗（relay_seq≥1）與 reset_at 為空的哨兵 probe 路徑；原型經真 `settle_window` 兩窗端到端驗證（W2-05，+10 斷言行、89→99，仍遠低於 tier 400；超出規格落點 ≤90 需主控決定）。

| ID | 等級 | 一句話 |
|---|---|---|
| W2-01 | P3 | 欄位級「缺欄＝None 不是 0」沒有測試鎖（M2 存活）；0 淨行可補 |
| W2-02 | P3 | AST 防成環鎖只認 3 種寫法，`from lib import quota_escalation`（repo 有史料的真形態）等 4 種放行（M5 存活） |
| W2-03 | P3 | `reset_at` 空／缺席 ⇒ `no-anchor` 這條（哨兵 probe 路徑的真實形態）無測試（M6 存活） |
| W2-04 | P3 | 接線處沒有第二道網：callee 若拋例外，settle_window 走災難 handler、**下一窗不被排程**（實測）；現無可達逃逸路徑 |
| W2-05 | P3 | 接力窗／probe 路徑的錨點可零成本修（第 4 點） |
| W2-06 | P3 | FRESH 路由窗的列與「RESUME 量不到」的列無法區分（record 不帶 strategy） |
| W2-07 | P4 | PRD 落款須誠實寫的五件事（pp 未產出、timeout 窗不落帳、probe 路徑、接力窗、FRESH 窗） |
| W2-08 | P4 | 錨步驟與 `reset_at` 下界等價；窗前無真請求被判 no-anchor 會丟合法樣本 |
| W2-09 | P4 | 雜項（open 在 try 外、append 測試只循序、USAGE_KEYS 第二個家、測試檔 UTC、空 usage 停筆、第五個掃描器） |
| W2-10 | 資訊 | 接線位置偏離規格字面「收尾」——D6 理由成立，M15 類突變已證被釘住，接受 |

## 1. 驗收（本場親跑；逐字尾段）

### 1.1 `python -m unittest test_resume_cost -v`
```
test_unmeasurable_windows_say_so_and_never_write_zero (test_resume_cost.ResumeCostTest.test_unmeasurable_windows_say_so_and_never_write_zero)
無 usage／逐字稿缺席／無 assistant／全零佔位 ⇒ measured 為假，數值欄是 None。 ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.012s

OK
rc=0
```

### 1.2 relay 相關既有測試
`grep -ln relay_machine tools/tests/*.py` 只有兩支：`test_context_budget_guard.py`、`test_resume_cost.py`。
```
test_context_budget_guard（整模組）:   Ran 798 tests in 55.529s / OK (skipped=11) / rc=0
```
skipped=11 是整模組既有 skip（未逐一檢視），不在 relay 類內；下面把 relay／接力相關 19 個類單獨跑（`ResumeTickWritesStateOnlyAfterConfirmingTest`＝規格 (5) 在內），skip 為 0：
```
Ran 84 tests in 6.106s

OK
rc=0
```
（Developer 列 18 類／82 支；我多帶 `RearmAfterStopAndSentinelEscalateSurviveAVanishedPlanFileTest` ⇒ 84。）
另跑會經 `_resume_tick`／哨兵 tick 的兩支：`test_mac_endurance_r83 test_sentinel_tick_e2e_r145` ⇒ `Ran 132 tests in 5.384s / OK / rc=0`。

### 1.3 `python -m unittest test_mac_readiness_r82 test_platform_utils_dedup test_subprocess_encoding_hygiene test_platform_neutral_paths test_wake_chain_halt_r278`
```
Ran 339 tests in 99.294s

OK
rc=0
```
以上所有測試跑完後：`~/.autosdd/traces/autosdd_resume_cost.jsonl`、`$TMPDIR/autosdd_resume_cost.jsonl`、`/tmp/autosdd_resume_cost.jsonl` 皆 `No such file`（測試沒有污染真實痕跡目錄）。

### 1.4 ruff（repo 根，不帶 --config）
```
All checks passed!
rc=0
```

### 1.5 LOC（`python AutoClaude/tools/check_loc_budget.py --json`）
`absolute_violations`／`tier_violations`／`special_violations`／`root_tools_violations` 皆 `[]`（rc=0）。
`tools/lib/resume_cost.py` assertion=**89**（規格 ≤90）；`tools/lib/relay_machine.py` assertion=**254**（規格 251→≤260；以同一計價器 `count_loc` 量 HEAD 版＝251、工作樹＝254，與交件一致）。
EAW 寬度：resume_cost.py 最寬 100（L76）、test_resume_cost.py 最寬 100（L60）、relay_machine 新增 5 行寬 [84, 89, 82, 43, 44]；皆 ≤100。

### 1.6 與 Developer 交件對帳
| 項 | Developer 交件 | 我重跑 |
|---|---|---|
| test_resume_cost | 5／OK | 5／OK |
| relay 相關類 | 82／OK | 84／OK（多 1 類） |
| 指定五模組 | 339／OK | 339／OK |
| ruff／LOC | 通過／89・254 | 通過／89・254 |
| 突變（他的 23 個，以他的 `mutate_w2.py` 重跑到我的 scratch） | 22 擊殺、M17 存活 | 22 擊殺、M17 存活（`v5_dev_mutation_rerun.txt`） |
| 真逐字稿唯讀交叉 | 1 支（260 筆 assistant） | 另取 2 支，見 §6 |
| 全套 5268／11 紅 | 他的自陳 | **未重跑**（任務書明令不跑全套），以他的檔案為準、不採信 |

## 2. 設計符合性（規格 §3.2 逐點）

| 規格要求 | 證據 | 結果 |
|---|---|---|
| record 九欄 `{session_id, relay_seq, first_assistant_ts, input_tokens, cache_creation_input_tokens, cache_read_input_tokens, pct_before, pct_after, measured}`＋`model` | `build_record` 回傳 12 鍵＝九欄＋`model`＋`reason`＋`recorded_at`；4000 案隨機測試每筆鍵集合恰等於此 12 鍵 | ✓ |
| `model`＝同一筆 assistant 的 `message.model`，缺＝None、不得空字串頂替 | `first_assistant_usage_after` 回同一筆的 `msg.get("model")`；`build_record` 只收非空 str；測試 1 以 fable/sonnet 不同 model 證「同一筆」；缺鍵／空字串／整數 7 皆 None | ✓ |
| 取值純函式與 I/O 分離 | `build_record` 純；`_assistants` 吃路徑或 iterable；寫入集中在 `append_cost_record`／`record_window` | ✓ |
| 唯一接線點＝`settle_window`；planner 零改動 | `git diff` relay_machine 僅 1 import＋2 行註解＋`if`＋呼叫各 1 行（raw +5）；`git diff tools/session_resume_planner.py` 對 `resume_cost|record_window` 命中 0 | ✓（位置見 W2-10） |
| 只在 `state=="resumed"` 落帳 | 接線 `if state.get("state") == "resumed"`；測試 4：`resume_failed` 不長檔、位元組不變；M4（放寬成含 `resume_failed`）被擊殺 | ✓ |
| 痕跡落 `endurance_env.trace_dir()`、走 `quota_ledger.append_record()` | `record_window` 預設路徑 `endurance_env.trace_dir() / RECORD_NAME`；`append_cost_record` 末行 `quota_ledger.append_record(path, record)`（單次 `os.write`、`O_APPEND`、0o600）；測試以 `AUTOSDD_TRACE_DIR` 導向 | ✓ |
| 零 token、零網路 | import 閉包（`python -I` 實測）＝endurance_env、platform_utils、quota_ledger、quota_limits、resume_cost（`v3_closure.txt`），皆 stdlib／本地純模組 | ✓ |
| 量不到寫 `measured:false`，不得寫 0 | 見 §3 分支表 | ✓（欄位級鎖見 W2-01） |
| AST 鎖：不得 import `quota_gate`／`quota_escalation` | 測試 5 存在；`banned()` 對它自帶的 3 個壞樣本有牙；真檔為 `[]`；盲區見 W2-02 | ✓（有缺口） |
| `pct_before/after` 只在兩次讀數皆量得到時才填 | `build_record` 兩者皆為 int／float（`type()` 比對、排除 bool）才填；v1 接線不傳 ⇒ 恆 None（D3，自陳） | ✓（v1 不產出，見 W2-07） |
| 測試 (1)～(6) | (1) 測試 1；(2) 測試 2；(3) 併入測試 4（`assertFalse(trace.exists())`＋size 不變）；(4) 測試 3；(5) 既有類 84 支綠；(6) 測試 5。五支新測試涵蓋六條 | ✓ |
| LOC ≤90／251→≤260 | 89／254 | ✓ |
| py39 相容 | repo 自己的 `test_mac_readiness_r82.py::py39_incompat`：resume_cost.py＝`[]`、relay_machine.py＝`[]`；`hook_chain_py39_census()` hard／soft 皆 `{}`；真 `/usr/bin/python3` 3.9.6 `-I` 直跑 import＋`last_assistant_before`／`first_assistant_usage_after`／`build_record`／`record_window` 全部成功、`quota_gate`／`quota_escalation` 未被載入（`v3_py39_runtime.txt`） | ✓ |

### 2.1 fail-soft（任務書第 3 點）
- 被呼叫端：`record_window` 的 `try` 包住 `_locate`／`build_record`，`except Exception` 後仍落一列 `measured:false, reason=error:<名>`；append 另包 `contextlib.suppress(Exception)`。我餵它 4000 案隨機垃圾（半截行、非 dict 記錄、型別錯亂的 usage／model／timestamp、壞／空 reset_at、`relay_seq` 為 `"x"`／None）零例外（`fuzz.py`／`v6_fuzz.txt`）；另以邊界探針確認 `relay_seq="abc"` ⇒ `error:ValueError` 列、year-1 的 reset_at ⇒ `no-anchor`（`v3_edge_probe.txt`）。
- 接線處：**沒有第二道網**。探針 `failsoft_probe.py`（真 `settle_window`、planner 副作用換替身、`record_window` patch 成 `raise RuntimeError`）：
```
[baseline (real record_window)] rc=0 events=['relay_spawned'] register_next_window_called=True relay_seq_after=1
[record_window raises RuntimeError] rc=0 events=['relay_settle_crashed'] register_next_window_called=False relay_seq_after=0
```
  ⇒ fail-soft 成立，但**完全仰賴 callee 契約**；契約一旦被日後修改破壞，旁路帳本的失敗會讓喚醒鏈停在這一窗（見 W2-04）。

## 3. 「量不到寫 None 不寫 0」逐分支

| 分支 | reason | 數值欄／model | 鎖 |
|---|---|---|---|
| `usage=None` | `no-assistant-usage` | 全 None | 測試 2 |
| 全零 usage（合成佔位長相） | `no-usage-count` | 全 None（`measured=any(...)` 為假） | 測試 2；M4 擊殺 |
| bool usage（`True`） | `no-usage-count` | 全 None（`type() is int`） | 測試 2；dev M14 擊殺 |
| 逐字稿缺席／空字串 | `transcript-missing` | 全 None | 測試 2 |
| 窗前無真請求 | `no-anchor` | 全 None | 測試 2 |
| reset_at 空／缺／解不出 | `no-anchor`（實測；`reset_at=""`、缺鍵、year-1 皆是） | 全 None | **無測試（W2-03）** |
| 接力窗 relay_seq≥1 | `relay-chain-anchor` | 全 None | 測試 4；M3 擊殺 |
| 例外 | `error:<名>` | 全 None | 測試 2；dev M7 擊殺 |
| 部分欄位缺席（量到其中一欄） | `None`（reason 為 None） | 缺的欄是 None | **無測試（W2-01，M2 存活）** |

## 4. 第 4 點：接力窗錨點限制（relay_seq≥1 標 measured:false）

### 4.1 為何失效
「`state['reset_at']` 之前最後一筆真 assistant 之後的第一筆」在數學上等於「`reset_at` 之後（≥）的第一筆真 assistant」（錨之後到 `reset_at` 之間依定義沒有真請求）；**下界就是 `reset_at`**。接力窗（`RELAY_NEXT` 重排下一窗）時 `reset_at` 不動——`relay_machine.apply_reset_at` 只在值變更時才歸零計數、`resolve()` 只改 `relay_seq` 與 streak——所以第 N 窗（N≥1）的下界仍是第 0 窗之前的那條線，取到的永遠是**第 0 窗的首請求**。Developer 的 `relay-chain-anchor` 守衛是正確的誠實標記。
同一個機理也使哨兵 probe 路徑（`_arm_sentinel`→`_base_state` 的 `reset_at: ""`，掃到撞線時 reset 已過、沒走 `arm_reset`）恆為 `no-anchor`。

### 4.2 候選 state 欄位逐一排除
- 上一窗的 `first_assistant_ts`：只是上一窗第一筆；其後的第二筆請求仍屬上一窗 ⇒ 會撈到上一窗第二筆（錯值）。✗
- `state['next_run_time']`（Windows 憑證）：是時間值；mac 的 `schedule_credential` 不是（根 CLAUDE.md：「憑證是 rc，不是時間值」）。✗（不跨平台）
- `observed_at`：只在 `_arm_endurance` 路徑有，指撞線事件而非 spawn。✗
- Developer 在 D4 建議的 `last_assistant_ts`（本窗結束時寫進 state、下一窗以它為錨）：可行，但要新增 state／checkpoint 欄位（動 planner 的寫入面）；下面的 spawn 錨不需要任何新欄位。

### 4.3 能：用 planner 自己落的 spawn 時刻痕跡
`_run_resume`（`session_resume_planner.py`）在 `subprocess.run` 前一刻 `append_log(log, "relay_snapshot_before", ...)`；`append_log` 每筆帶 `"at"`（秒精度、截斷＝只會早於真 spawn 時刻，`epoch > at` 不會漏掉本窗首請求）。`_resume_tick` 把同一個 `log` 傳給 `_run_resume` 與 `settle_window(args, state, plan, log, rc)`——**`settle_window` 手上就有**，不必讀 state、不必改 planner／守衛面；該事件「有落 log、且先於 `resumed` 事件」由 `RelaySnapshotBeforeIsLoggedTest` 鎖著（先於 `subprocess.run` 是同一個 `try` 內的程式順序）。最小改法（我在 scratch 驗證，**未改 repo**；以下為示意，實作請用 `with` 開檔）：

```diff
-def _locate(state: dict, relay_seq: int) -> tuple[dict | None, str]:
+def _spawn_at(log: object) -> str | None:
+    """最後一筆 relay_snapshot_before 的 at（planner 在 subprocess.run 前一刻落的）。"""
+    last = None
+    with contextlib.suppress(OSError):
+        for line in Path(str(log)).open(encoding="utf-8", errors="replace"):
+            if '"relay_snapshot_before"' in line:
+                with contextlib.suppress(ValueError, AttributeError):
+                    last = json.loads(line).get("at") or last
+    return last
+
+def _locate(state: dict, relay_seq: int, log: object = None) -> tuple[dict | None, str]:
     source = str(state.get("transcript") or "")
-    if relay_seq >= 1:
-        return None, "relay-chain-anchor"
     if not Path(source).is_file():
         return None, "transcript-missing"
+    if spawn := (_spawn_at(log) if log else None):  # 接力窗與 reset_at 為空的 probe 路徑都靠它
+        return first_assistant_usage_after(source, spawn), ""
+    if relay_seq >= 1:
+        return None, "relay-chain-anchor"          # 沒有 spawn 痕跡時的誠實退路（原行為）
     anchor = last_assistant_before(source, state.get("reset_at"))
 ...
-def record_window(state, path=None):  →  def record_window(state, path=None, log=None):
-        usage, why = _locate(state, seq)             →  _locate(state, seq, log)
```
接線改 `resume_cost.record_window(state, log=log)`（relay_machine 不增行）。完整 diff：`w2rev/proposed_resume_cost_spawnat.diff`。
- 驗證 1：`anchor_proto.py`——兩窗合成逐字稿，現況錨法窗 1 取到窗 0 的 `(3, 70000, 111)`；spawn 錨法窗 0／窗 1 各取到自己的 `(3, 70000, 111, fable)`／`(5, 5000, 90000, sonnet)`。
- 驗證 2：端到端（`v4_e2e_two_windows_with_fix.txt`）——真 `settle_window`（修補副本、planner 副作用換替身）連跑兩窗，落帳兩列皆 `measured:true`，`relay_seq=1` 那列＝`input_tokens 5／cache_creation 5000／cache_read 90000／claude-sonnet-5-5`。
- 驗證 3：修補版 resume_cost 對 repo **現有未改動**的 5 支測試 `ran=5 failures=0 errors=0`（`v4_spawnat_variant_vs_repo_tests.txt`）。
- LOC：resume_cost 89→**99**（`count_loc`）。超出規格落點 ≤90、遠低於 tier 400；若要守 ≤90，須同輪重釘規格落點（主控裁）。
- 附帶好處：對「reset_at 到 wake 之間使用者手動續跑」造成的錯值也免疫（錨改成真正的 spawn 時刻）。
- 若主控不採：W2-07 的五件事須進 PRD 落款（接力窗與 probe 路徑 v1 恆 `measured:false`）。

## 5. 突變（隔離副本；repo 工作樹零改動）

做法：`run_mut.py <ID>` 把 `tools/lib/resume_cost.py`（M4 另含 `relay_machine.py`）複製到 `scratchpad/113/mut/<ID>/`、對副本套**恰一處**文字突變（舊字串必須恰出現 1 次，否則中止）、以 `importlib` 預先塞進 `sys.modules`，再載入 repo 內**原樣**的 `tools/tests/test_resume_cost.py` 跑；每個突變獨立子行程；輸出同時印 `resume_cost.__file__`／`relay_machine.__file__` 證明命中副本；`AUTOSDD_TRACE_DIR` 導向 scratch 防漏寫。控制組 M0（不突變、同樣走副本載入）：`ran=5 red=[]`＝harness 有效。

| # | 突變 | 目標 | 結果 | 紅的測試 |
|---|---|---|---|---|
| M1 | `first_assistant_usage_after` 交換 cache_creation／cache_read（規格測試 (1) 的分流） | resume_cost 副本 | **KILLED** | `test_first_request_after_the_last_pre_reset_assistant_is_measured`、`test_settle_window_logs_one_row_per_real_wake_and_nothing_otherwise` |
| M2 | `build_record` 缺欄補 `0` 而非 `None`（規格「不得寫 0」的欄位級） | resume_cost 副本 | **SURVIVED** | —（W2-01） |
| M3 | 接力窗守衛 `relay_seq >= 1` → `>= 2` | resume_cost 副本 | **KILLED** | `test_settle_window_logs_one_row_per_real_wake_and_nothing_otherwise` |
| M4 | 接線閘放寬成 `in ("resumed", "resume_failed")`（零喚醒也落帳） | relay_machine 副本 | **KILLED** | `test_settle_window_logs_one_row_per_real_wake_and_nothing_otherwise` |
| M5 | 在 resume_cost 注入 `from lib import quota_escalation`（AST 鎖有牙嗎） | resume_cost 副本 | **SURVIVED** | —（W2-02） |
| M6 | 刪掉 `if limit is None: return None`（reset_at 解不出的守衛） | resume_cost 副本 | **SURVIVED** | —（W2-03） |

**擊殺 3／6。** 三個存活者皆為測試缺口、現行實作行為正確。

### 5.1 提議的測試補丁（scratch 驗證；不改 repo）
`proposed_test_patch.diff`：測試 2 的 `half` 斷言併入缺欄 None（0 淨行，W2-01）；測試 2 加一筆 `reset_at=""` 案並把 reason 斷言改為 `[4:8]`（+1 行，W2-03）；測試 5 的 `banned()` 逐段比對＋ImportFrom alias＋補壞樣本 `from lib import quota_escalation`（+2 行，W2-02）。**不新增測試方法**（Developer D8：MIN_TESTS 零相依餘裕不允許再加）。總計 179→183 行（上限 180 需連動棘輪重釘或自行壓縮）。以此補丁重跑同一套突變：
```
SURVIVED M0-control: ran=5 red=[]
KILLED   M1: red=[...first_request..., ...settle_window...]
KILLED   M2-partial-usage-none-to-zero: red=['test_unmeasurable_windows_say_so_and_never_write_zero']
KILLED   M3: red=['test_settle_window_logs_one_row_per_real_wake_and_nothing_otherwise']
KILLED   M4: red=['test_settle_window_logs_one_row_per_real_wake_and_nothing_otherwise']
KILLED   M5-ast-lock-evasion-from-lib: red=['test_resume_cost_never_imports_the_quota_gate_family']
KILLED   M6-no-anchor-guard-removed: red=['test_unmeasurable_windows_say_so_and_never_write_zero']
```
⇒ 6／6。對照組（M0）仍綠。

### 5.2 Developer 的 M17（存活）
`.replace("Z", "+00:00")` 在 3.11 為等價變異（`fromisoformat` 本來就吃 Z）。我在**真 3.9.6** 上對突變副本實測：`_epoch('2026-10-09T17:30:00.000Z')` 回 `None`（3.11.15 回 `1791567000.0`）⇒ 該行在 3.9 是承重牆，只是沒有 3.9 測試腿釘它；唯一消費者 `relay_machine`←`session_resume_planner`（`from datetime import UTC`）本就是 3.11 only，影響為零（`v5_m17_py39.txt`）。

## 6. 真逐字稿抽驗（唯讀）

- 母體普查（94 支 `~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/*.jsonl`，普查時點 9,807 筆 assistant 記錄；現役 session 逐字稿持續成長，稍後複查 timestamp 時為 9,820 筆）：`<synthetic>` 9 筆，**皆全零 usage**（其中 8 筆 `isApiErrorMessage`）；`isSidechain` 為真者 0；usage 非 dict 者 0；缺 `model` 鍵者 0；timestamp 複查 9,820／9,820 筆皆為 `YYYY-MM-DDTHH:MM:SS.mmmZ`（`survey_all.txt`、`survey_ts_forms.txt`）。⇒「合成佔位＝全零＝不算量到」與「主逐字稿不含 sidechain 記錄」皆有真資料支撐。
- 純函式交叉（`real_check.py`；`8d8773f9…jsonl` 5.1MB、382 筆 assistant、4 筆合成）：自己用 `json.loads`＋`strptime` 手算「cutoff 前最後一筆真請求＝錨、檔案順序第一筆晚於錨者＝首請求」，與 `last_assistant_before`／`first_assistant_usage_after`／`build_record` 對 **36 個 cutoff**（含「撞線合成訊息後 1 秒／1 小時」「撞線前 1 秒」「真請求前後 1ms」）逐欄比對：**0 不符**；檔案順序與時間順序 0 分歧。一筆樣本：cutoff `2026-09-10T02:44:06.446+00:00` ⇒ 錨 `…02:43:39.166Z`、首請求 `{'ts': '2026-09-10T02:44:20.695Z', 'model': 'claude-fable-5-1', 'input_tokens': 32, 'cache_creation_input_tokens': 12610, 'cache_read_input_tokens': 376340}`。
- `record_window` 端到端（`real_check2.py`；`9ea68d33…`、`8d8773f9…` 各 45 案，`reset_at` 用 +08:00 offset 的真 state 格式）：`cases=45 mismatches=0`×2；每案另跑 `relay_seq=1` 變體，一律 `measured=False／relay-chain-anchor／數值欄 None`。（我第一版比對腳本用「第 k+1 筆」當期望而誤報 5 不符——是我腳本的假設錯：同一個 API 回應的多個內容區塊會在數 ms 內連寫多筆 assistant 記錄，改用獨立手算後 0 不符。）
- 真資料旁證（W1 的拋棄式探針逐字稿 `a119e01d-…jsonl`）：`claude -p -r <sid>` 續跑的新回合**寫進同一個檔、同一個 sessionId**（`sessionId` 全檔僅 1 個）——故「在 `state['transcript']` 內找本窗首請求」的前提成立；且一個 API 回應會存成**多筆 assistant 記錄、usage 相同**（`16:12:44.895Z` 與 `16:12:44.903Z` 皆 `(2, 8406, 11343)`）⇒ 只取首筆不會重複計。
- 隨機差分（`fuzz.py`，種子 20261010）：4000 案（526 量到、3474 量不到）逐案檢查 12 鍵集合、`measured` ⇒ 至少一欄為正 int、非量到 ⇒ 數值欄全 None＋reason 非空、`model` 僅 None／非空 str、pct 恆 None、接力窗守衛、與獨立 oracle 逐欄一致：**0 問題**；`record_window` 零例外。
- 掃描耗時：8.1MB 真逐字稿兩趟全掃約 66ms（≈8ms/MB；32MiB 上限≈0.3s；300MB≈2s）⇒ 放在 `resolve` 之前不構成延遲風險。

## 7. 註解／衛生掃描

- 新增行輪號：資料行中只有 `improving_113`（允許）；無 `R2xx`、無 DEF-ID、無 `round-label-ok` 字樣。relay_machine 新增 5 行＝`improving_113 W2：…` 註解／import／接線。
- `test_resume_cost.py`：179 行；零 skip／xfail／expectedFailure；EAW 寬度最大 100、零行 >100。
- 既有鎖：結構鎖 `test_the_settle_window_delegate_really_disposes`（在 798 支內）綠；我提議的 `suppress` 包裝對該鎖的支配演算法也相容（對修補副本：returns=4、無缺處置支配者，`v3_dominator_lock_on_patched.txt`）。

## 8. Findings

### W2-01（P3）欄位級「缺欄＝None、不是 0」沒有測試鎖
- 證據：M2（`got = {k: raw[k] if type(raw.get(k)) is int else 0 ...}`）5 支全綠 SURVIVED。D2 與 docstring 白紙黑字「部分欄位缺席時缺的那欄是 None、不補 0」，唯一的部分欄位案例（測試 2 的 `half`＝`{"ts":"t","input_tokens":1}`）只斷言 pct 兩欄。這是 RTM R7「量不到不得寫 0」的欄位級體現。
- 重現：`python .../scratchpad/113/mut/run_mut.py M2-partial-usage-none-to-zero`（環境見開頭）。
- 修法（0 淨行）：測試 2 末行改為 `self.assertEqual([half[k] for k in ("pct_before", "pct_after", *_NUM[1:])], [None] * 4)`；補丁後 M2 KILLED。

### W2-02（P3）AST 防成環鎖只認 3 種寫法
- 證據：`banned()` 只比 `n.split(".")[0]`，且 `ImportFrom` 只看 `module`。對 8 種寫法實測（`ast_lock_probe.py`）：CAUGHT＝`import quota_gate`、`from quota_gate import x`、`__import__('quota_gate')`；**MISSED＝`from lib import quota_escalation`、`from tools.lib import quota_gate`、`import tools.lib.quota_gate`、`from . import quota_gate`**、字串拼接動態載入。M5 注入 `from lib import quota_escalation` 5 支全綠。`from lib import quota_escalation` 不是假想：`tools/lib/quota_gate.py` 檔頭 R84／ARCH-10 記載 quota_escalation 曾是**唯一**以該寫法被載入的同層模組（兩個站點）。
- 現況無違規：resume_cost 實際 import 閉包不含 quota_gate／quota_escalation／relay_machine／planner／quota_policy（`v3_closure.txt`）。鎖只看**直接** import、不看遞移（日後 `endurance_env` 加 import 不會被抓）——誠實劃界，P4。
- 修法：`ImportFrom` 併入 alias 名、逐段比對；實測 8 形態抓 7（只剩字串拼接——靜態判準本就不可能）、真檔仍 `[]`（`v3_ast_lock_fix_probe.txt`）；補壞樣本 `from lib import quota_escalation`；補丁後 M5 KILLED。

### W2-03（P3）`reset_at` 空／缺席 ⇒ `no-anchor` 這條無測試
- 證據：M6（刪守衛）5 支全綠。這是哨兵 probe 路徑的真實形態（`_base_state` 的 `reset_at: ""`，Developer §6 自陳）；測試的 `state` 一律帶 `reset_at`。守衛刪掉後該路徑會變成 `error:TypeError` 列（仍 `measured:false`，但 reason 誤導）。現況實測：`reset_at=""`、缺鍵、`"0001-01-01T00:00:00"` 皆 `no-anchor`（`v3_edge_probe.txt`）。
- 修法（+1 行）：見 `proposed_test_patch.diff`（`record_window({**state, "transcript": str(late), "reset_at": ""}, out)`，reason 斷言改 `[4:8]` 並順手釘住 `transcript-missing` 那筆）；補丁後 M6 KILLED。

### W2-04（P3）接線處沒有第二道網
- 證據：§2.1 探針——`record_window` 若拋，`settle_window` 進 SD-8 災難 handler，**`_register_and_record`（下一窗）沒被呼叫、relay_seq 不動**。目前無可達逃逸路徑（§2.1、4000 案隨機），故不是現行缺陷；但這是「記帳旁路能讓喚醒鏈停在這一窗」的形態，且任務書第 3 點明寫「任何例外不得讓 settle_window 失敗」——現況是以 callee 契約滿足、不是以結構滿足。
- 修法（+2 斷言行：`import contextlib`＋`with contextlib.suppress(Exception):`；254→256 ≤260；`proposed_relay_machine_suppress.diff`）：
```diff
         if state.get("state") == "resumed":
-            resume_cost.record_window(state)
+            with contextlib.suppress(Exception):
+                resume_cost.record_window(state)
```
  驗證：修補副本同一探針 → `events=['relay_spawned'] register_next_window_called=True`；dominator 鎖相容（§7）。釘法需 ~4 行（`_settle` 目前不回報「有沒有排下一窗」）；若認為無暴露證據，登 P4 不修亦可（R197 准入口徑）。
- 附帶：模組層 `import resume_cost` 是 hard import——`resume_cost` 日後若在 import 期炸，整個 `relay_machine`／planner 起不來。repo 慣例（`quota_gate` 檔頭）是「能力提供者退化成『量不到』、判讀原語 hard import」；resume_cost 屬能力提供者。現況閉包很小（4 個本地純模組）、風險低，P4 備註，不建議本輪動。

### W2-05（P3）接力窗／probe 路徑錨點可零成本修
見 §4。建議採用；不採則依 W2-07 落款。

### W2-06（P3）FRESH 路由窗的列與「RESUME 量不到」無法區分
- 證據：`choose_resume_route` 在逐字稿缺檔／為空／超過 `AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES`（32MiB）時降級開全新 session（`STRATEGY_FRESH`，argv 不帶 `-r`），新 session 寫在**別的檔**；此時舊逐字稿窗後沒有 assistant。探針（`v3_fresh_route_probe.txt`）：
```
route_strategy=SESSION_RESUME: measured=False reason='no-assistant-usage'; 'strategy' key in record: False
route_strategy=FRESH_SESSION_WITH_STATE: measured=False reason='no-assistant-usage'; 'strategy' key in record: False
```
  兩者逐字相同。而 FRESH 窗正是「逐字稿最大」的那批——此量測要校準的 `AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES` 恰需要把它們分開。`state['route_strategy']` 在 `settle_window` 時已是 in-memory 現成值（`_run_resume` 寫入）。
- 修法（+1～2 斷言行）：`build_record` 加 `strategy` 直通欄（`state.get("route_strategy")`，不 import planner 常數＝不造第二個家），或在 `_locate` 對非 `SESSION_RESUME` 回 `reason="not-resume-route"`（需字面常數，較不建議）。

### W2-07（P4）PRD 落款須誠實寫的事
1. `autoclaude_resume_cost_pp` 的單位是**百分點**；v1 的 `pct_before/after` 恆 None（D3：沒有「spawn 前讀數」的持久來源）⇒ v1 只落 **token 欄**；PRD §11.3「記錄本次喚醒的實際額度成本」只能寫「token 成本已落帳；pp 成本待 spawn 前讀數來源（建議 improving_114）」。
2. 被 3600s timeout 砍掉的窗（`_run_resume` 回 None ⇒ `resume_failed`）不落帳（D5）⇒ 最長窗樣本缺席（存活者偏誤）；這是「沒觸發＝檔不長大」可偵測性的代價，非缺陷。
3. 哨兵 probe 路徑（`reset_at` 空）v1 恆 `no-anchor`（採 W2-05 則消失）。
4. 接力窗 v1 恆 `measured:false／relay-chain-anchor`（採 W2-05 則消失）。
5. FRESH 路由窗與失敗列同形（採 W2-06 則可分）。

### W2-08（P4）錨步驟與 `reset_at` 下界等價
- 「錨之後第一筆」＝「`reset_at` 之後第一筆」（§4.1）；錨步驟唯一的額外行為是 `no-anchor` 守衛。真資料：94 支逐字稿中 2 支只有合成撞線訊息、沒有任何真請求（`566e677f…`、`5c2b78fc…`）；這類 session 被 `-r` 喚醒時窗前無真錨 ⇒ `no-anchor` 丟掉本可量到的樣本。可選簡化：`reset_at` 可解析即直接當下界，`no-anchor` 只留給 `reset_at` 缺／壞。屬設計取捨，規格字面是 Developer 的做法，不改亦可。

### W2-09（P4）雜項
- `_assistants` 的 `opened = Path(source).open(...)` 在 `try` 外，`except OSError: return` 蓋不到 `open()` 本身——缺檔時純函式拋 `FileNotFoundError`（`v3_edge_probe.txt`）；`_locate` 的 `is_file()` 與 `record_window` 的 `except` 兜住，無害。
- 測試 3 只測循序 append；`quota_ledger` 自陳密集並行仍可能掉行，本測試不證原子性（規格 (4) 字面「不掉行」＝循序成立）。我另做並行壓力（`conc_append.py`：8 行程×400 次 `append_cost_record`、列長約 456 位元組）：`ok_returns=3200 parsed_rows=3200 unparsable_lines=0`（本機 APFS；該自陳風險在此列長下未重現，不構成缺陷證據）。
- `USAGE_KEYS` 與 hook 的 `USAGE_FIELDS` 同三欄第二個家（D9 已自陳；hook 為守衛面、方向 hook→lib，不能反向 import）。
- 測試檔 `from datetime import UTC`（3.11+）：與 tools/tests 現存 11 支一致，且被測的 `session_resume_planner` 本身即 `from datetime import UTC` ⇒ 該測試在 3.9 本來就載不起；資源檔本體 py39 合規。
- `first_assistant_usage_after` 遇「usage 為空 dict」的 assistant 會停在那筆（hook 的 `scan_transcript` 慣例是跳過）；真資料 0／9,807，構造性。
- 這是第五個 transcript assistant 掃描器（`quota_limits` 兩個、`sentinel_lifecycle_arm`、`harness_feed`、hook 各有一個），無共用迭代器；本輪不合併（牽動守衛面）。

### W2-10（資訊）接線位置
規格寫「`settle_window` 收尾」，實作放在 `try` 最前、`resolve` 之前（D6：`resolve` 之後 `relay_seq` 已 +1）。理由成立且被鎖：dev M15（`resolve` 之後才落帳）擊殺、測試 4 末段專驗 `relay_seq==0`。接受。

## 9. 未驗證／誠實劃界

- 沒有真的 `claude -r` 無人喚醒窗可驗：本機系統暫存內 23 份真 UUID 端點紀錄只有 `sentinel_decided: patrol 1553／disarm 21`，**零** `woken／probed／resumed／relay_snapshot_before`（重開機即消失，「查不到≠沒發生」）⇒ 各路徑（arm_reset／probe／rearm）在真實喚醒中的佔比**未量到**；W2-05 的 spawn 錨以程式碼閱讀（`_run_resume`／`_resume_tick` 同一個 `log`）＋合成端到端驗證，未用真 planner 事件檔驗。
- Windows、py3.9／3.10 的**測試**皆未跑（資源檔本體已在真 3.9.6 直跑）。
- 全套 5268／11 紅、MIN_TESTS 零相依餘裕 56 的數字、護欄行數棘輪、表② 指紋、雲端 CI：**未重跑、未採信**（任務書明令不跑全套）。
- 我的突變只有 6 個（任務書上限）＋對照組；Developer 另 23 個以他的 harness 重跑確認。我的 harness 與他的不同（他用 `types.ModuleType`＋`exec`、我用 `importlib` 載副本檔），兩者結論一致。

## 10. 資源收尾與「工作樹未動」證明

- 開了→收了：兩個背景測試批次（皆已結束）；一個因 `multiprocessing` 從 stdin 腳本 spawn 而卡住的並行壓力探針已 `TaskStop`（無殘留行程，`ps` 查無 multiprocessing／spawn_main／resource_tracker），改以腳本檔重跑成功；無 worktree、無 claude 呼叫、無 git 寫入、無暫存 venv。
- 訂正（我自己的疏漏）：`anchor_proto.py`／`failsoft_probe.py`／`real_check2.py`／被卡住那支壓力探針起初沒有清自己的 `tempfile.mkdtemp` 目錄；收尾時已逐一刪除 `$TMPDIR` 下 9 個前綴 `w2rev-` 的目錄（`ls -d $TMPDIR/w2rev-*` 現為 0 個）；`fuzz.py`、端到端兩窗腳本、`conc_append.py` 本來就在 `finally`／結尾 `rmtree`。scratchpad 內產物保留（非 repo）。
- 開場快照：`w2_status_before.txt`、`w2_sha_before.txt`；收尾對帳見下方附記。

## 11. 收尾對帳（最後一個動作之後再量）

```
git status --short tools/lib/resume_cost.py tools/tests/test_resume_cost.py tools/lib/relay_machine.py
 M tools/lib/relay_machine.py
?? tools/lib/resume_cost.py
?? tools/tests/test_resume_cost.py
（與開場 w2_status_before.txt 逐字相同）

shasum -a 256（與開場 w2_sha_before.txt 逐位元組相同）
3e6a67d2642a8f4cda9752acd6fe5817dc5c757e4fba9ba801dd34ac795fa4e4  tools/lib/resume_cost.py
8b41d2b6a970e1e01c8c2abc2167f1f5eea0e69a5ce8cfa68cc80aa334c8049f  tools/tests/test_resume_cost.py
49e5bdb74e024c3da295ceb3e40ff3d491759d53ce8cc9ea817a15b2335492ee  tools/lib/relay_machine.py
```
整個 repo 的 `git status --short`（24 個 M＋9 個 ??）與本場開場快照的清單逐項相同；W1 修復者的檔案（同樹並行）我未讀、未評、未動。

## 〈T-6 最終 QA 鏡〉（review_final_qa_113.md）

# 最終 QA 零信任複審（improving_113：W1／W2／W3 實作＋修復包）

VERDICT: REJECT（FQ-01）

- 審查者：最終 QA 零信任複審鏡（Sonnet 5.5，唯讀）｜時點：2026-10-10 02:06～02:35（本機）｜repo HEAD 93929947＋工作樹。
- 判決範圍刻意收窄：**28 個要求重驗的條件／項目，26 closed、2 open**（open＝FQ-01 的 W2 spawn 錨、PRD-08）。唯一阻擋項 **FQ-01（P2）**＝W2 的 spawn 錨「已採納」的宣稱在生產接線上不成立：`tools/lib/relay_machine.py:469` 仍是 `resume_cost.record_window(state)`（沒帶 `log=log`），`_spawn_at()` 在生產上永遠不會被呼叫、接力窗仍 `measured:false／relay-chain-anchor`，且整個 spawn 錨分支零測試（突變 F7／F8／F11 皆存活）。修法是一個字（`log=log`）＋一支鎖＋三處文字對齊，已在隔離副本驗證（§6）；其餘全部條件已閉環。
- 全套：AutoClaude `4919 passed, 156 skipped in 36.06s`（rc=0，≥期望）；`Contracts: 9 kept, 0 broken.`；根層指定 17 模組 `Ran 931 tests`／`OK`（兩次：02:13 與樹靜止後 02:25）；ruff（brief 指定 11 檔＋AutoClaude 10 檔）`All checks passed!`；LOC 五類 violations 皆空；`.env.example` diff 零輸出；crossref／carriers rc=0。
- 工作樹：**審查期間主控並行動了樹**（git add、收尾棘輪重釘、測試補丁、證據檔編修；見 §0.2）；受審的 17 支程式／測試／yml 檔 sha256 與我開場完全相同，我自己零 repo 寫入。

---

## 0. 方法與環境

### 0.1 方法
- 讀完前審 5 份（review_w3_qa／review_w3_sd／review_w1_sd／review_w1_qa／review_w2）、2 份修復交件（w3_fix_log／w1_fix_log）、計畫書 improving_113 全文、證據檔〈二〉〈三〉、PRD 修憲草稿第 2 版（scratchpad `prd_amendment_v2116_draft.md`）、兩份帳本列草稿（`ledger_row_def507／508_draft.md`）。
- 每個閉環判定都附「指令或讀碼座標」；凡能用行為驗的不靠讀碼（獨立 E2E／突變）。
- 突變一律在隔離副本：W3＝pytest `-p` 外掛，把突變後的 `sliced_sleep.py`／`auto_resume.py` 以同名載入 sys.modules（控制組同路徑載入 `210 passed`）；W2＝以 `importlib` 載 scratchpad 副本再載 repo 內**原樣**測試檔；W1＝同 W2 手法。**未對工作樹任何檔做就地突變、未用 checkout／restore／stash／git add**。
- 所有腳本與原始輸出在 `scratchpad/113/fq/`（絕對路徑 `/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/da844569-c04d-4735-ac78-03f92c5abc92/scratchpad/113/fq/`）。
- 環境：`python`＝repo `.venv` 3.11.15；單跑 root unittest 前 `export AUTOSDD_SENTINEL_OFF=1; unset AUTOSDD_PARALLEL_TESTS`，在 `tools/tests` 下載入；PG 沒起（AutoClaude 摘要印 `PG 相關測試維持 skip`）；`--pace` 預設輸出的主控＝fable，而行程環境沒有 `AUTOSDD_MODEL_*`（`env | grep` 驗過）⇒ 值來自 repo `.env`（我依機密面紀律未讀 `.env` 本文，此為推論）。
- 額度提醒（共用額度，主控也會看到）：本場後段 PostToolUse 提示 `five_hour 95% 剩約 91 分鐘 band=halt`，只擋扇出型工具；我沒有使用任何 Agent／Task，全程 Bash／Read。

### 0.2 「工作樹凍結」並未成立（如實記錄）
開場 `git status --short`（`fq_git_status_start.txt`，33 筆）與收尾比對：
- 檔名集合差：新增 `M ONBOARDING.md`、`M tools/run_root_unittests.py`；9 個 `??` 全部變 `A `（主控 `git add`）。收尾 `?? ` 為零。
- sha256 manifest（開場 33 檔）收尾比對：30 檔相同、3 檔不同——`docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md`（mtime 02:10:33）、`tools/lib/skip_tag_policy.py`（02:13:31，`_TREE_FILE_FLOORS` 69→71／`AutoClaude/tests` 223→224）、`tools/tests/test_resume_cost.py`（02:10:12，+4 行測試補丁，179→183 行）。另 `ONBOARDING.md`（02:16:06）、`tools/run_root_unittests.py`（02:16:03）是開場後才進入狀態表。以上都是主控的收尾動作（內容為棘輪重釘、表② 回填、W2 測試補丁、證據檔編修），**不是我寫的**；最後一次樹變動 02:16:06，之後樹靜止（我 02:25 重跑根層模組即在靜止樹上）。
- 受審程式碼檔（全部 `OK`）：`tools/lib/{resume_cost,relay_machine,model_roles,resume_route,quota_messages,quota_gate,session_brief,quota_policy_env}.py`、`tools/session_resume_planner.py`、`AutoClaude/autoclaude/core/services/auto_resume.py`、`AutoClaude/autoclaude/utils/{sliced_sleep,config}.py`、`AutoClaude/autoclaude/main.py`、兩支 compat-ci yml、`tools/tests/test_model_roles.py`、`AutoClaude/tests/utils/test_sliced_sleep.py`。
- 本場對 repo 的副作用：只有 gitignored 的 `__pycache__`（多數已用 `PYTHONDONTWRITEBYTECODE=1`／`-p no:cacheprovider`／`ruff --no-cache` 避開）；`--pace` 兩次有既有的狀態副作用（pace 契約／燃燒帳，落在家目錄，與平常派工前現查相同）。

---

## 1. 逐條閉環表（28 項＋3 項額外）

判定：closed＝前審要求在我可驗的層級成立；open＝不成立。「plan 殘留」指計畫書 §3 規格文字或 §8（尚為空）仍待主控處理，統一列在 FQ-03，不影響該條 closed。

### 1.1 W3 QA 鏡（review_w3_qa_113.md）

| ID | 前審要求 | 修復宣稱 | 我的重驗 | 判定 |
|---|---|---|---|---|
| QA3-01（P2） | 三旋鈕出廠值與 PRD §6 區塊 9 對齊或登記偏離；註解／測試名不得把來源說成 PRD／計畫書 | slice 30（對齊）、tolerance 5（偏離，附理由）、max_inprocess 18000（偏離，附理由）；章節誤引訂正；defaults 測試拆兩支；補 `le` | (a) `TokenGuardConfig` 實讀：`30 5 18000`；`model_fields` metadata＝`Le(600)`／`Le(3600)`／`Le(86400)`（`ge` 為 1／1／60）；`config.py:268-270` 三行與 `:256-267` 理由註解；PRD 現查：`:1851 SLEEP_SLICE_SECONDS=30`／`:1852 CLOCK_JUMP_TOLERANCE_SECONDS=120`／`:1853 MAX_INPROCESS_WAIT_SECONDS=7200`、`:1721 ## 6. 設定檔規範`、`:1847 # 9. 重置、休眠與喚醒`，PRD 檔 `git diff --quiet` rc=0（尚未改）；`grep "PRD §9\|常數住 PRD\|follow_the_plan"` 於 AutoClaude 零命中；測試 `test_the_slice_default_matches_prd_section6_block9`／`test_the_defaults_that_deliberately_deviate_from_the_prd_are_pinned`（`test_sliced_sleep.py:486,491`）；突變 W3-C1（max 改回 7200）、W3-C2（slice 改回 60）、W3-C3（tol 改回 120）**各 KILLED**（見 §5.1） | closed（偏離已入 config 註解與 PRD 草稿 D；PRD 本文尚未落款，見 FQ-02） |
| QA3-02（P3） | 容忍邊界 `>` 要有測試鎖 | 新 `test_the_tolerance_boundary_is_strictly_greater_than`（2 參數） | 突變 W3-M1（`>`→`>=`）→ `1 failed, 209 passed`，紅＝`…boundary_is_strictly_greater_than[5.0-calls0-False]` | closed |
| QA3-03（P3） | 入口未呼叫 `hotkey.register()`，不得宣稱等待期間按鍵會中斷 | 5 處敘述改寫（不接線） | `main.py:245-248` 註解、`test_sliced_sleep.py:466-470` docstring、`sliced_sleep.py` 檔頭②、`auto_resume.py` 建構子 docstring 皆改成「注入點已接，入口目前未呼叫 register()」；事實面重驗：`grep register()`→僅 `execution/playbook_runner.py:375`，`main.py` 無 | closed |
| QA3-04（P3） | `test_run_with_future_resume_waits` 補回「恰好一次」的上界 | `60 < sum(slices) <= 305` | `test_auto_resume.py:156` 現碼；突變 W3-M6（等待執行兩次）→ `6 failed, 204 passed`，紅含 `tests/core/test_auto_resume.py::…::test_run_with_future_resume_waits` | closed |

### 1.2 W3 SD 鏡（review_w3_sd_113.md）

| ID | 前審要求 | 修復宣稱 | 我的重驗 | 判定 |
|---|---|---|---|---|
| SD3-01（P3，裁決點） | 不得把不存在的「根層哨兵承接」寫成事實；example 註解訂正；註冊誠實劃界 | 全部改「本版無自動承接者…外部（OS 排程器／人工）重啟」；`_wait` 註解不再指 R82 舊註解 | `grep "根層哨兵\|根層的哨兵\|哨兵\|交棒"` 於 `AutoClaude/autoclaude`、`tests`、`config.yaml*`、`docs` 零命中；`config.yaml.example:58-66`（本版無自動承接者）；`auto_resume.py:327-333` ERROR 文字（「請於該時刻後由外部（OS 排程器／人工）重啟」）；〈三〉#3 登記理論洞。**plan 殘留**：`improving_113.md:170` 規格文字仍寫「交棒由根層哨兵承接」＋「PRD 7200s」 | closed（plan 殘留見 FQ-03） |
| SD3-02（P3） | 拒絕長睡時 checkpoint 的 `scheduled_resume_at` 要是真實續跑時刻；兩種拒絕結果都帶時刻 | 新 `_pin_resume_time()`（`math.ceil(wait/60)`；只改寫讀得回的 checkpoint；任何失敗只 warning） | **(b) 獨立 E2E `fq_pin_probe.py`（真 FileStateRepository、出廠預設、`time.sleep` 替身）**：額度軸 6 小時後 reset → `(False, True, 'external_resume_required')`、Kernel 1 次、結果帶 `2026-10-10T08:09:31`、磁碟 `scheduled_resume_at ≈ now+359.99 min`（不是 now+30）、結果與磁碟一致、`step_idx` 仍 1；對照 4 小時 → 進入分片 sleep（`slept 30`）、不拒絕。讀碼：`auto_resume.py:316-339`（`_wait`）與 `:344-354`（`_pin_resume_time`）。突變 W3-M3（不改寫）／M4（ceil→floor）／M5（拿掉 `if saved`＝憑空造 checkpoint）／M7（續跑路徑也改寫）**各 KILLED** | closed |
| SD3-03（P3） | 預設值偏離 PRD 要登記；章節誤引訂正；測試名不得說「follow the plan」 | 同 QA3-01 | 同 QA3-01 | closed |
| SD3-04（P3） | 牆鐘倒退的 warning 要與實際動作一致 | 依方向兩句文字＋雙向 caplog 斷言 | `sliced_sleep.py:55`；突變 W3-M2（兩句對調）→ `2 failed`，紅＝`test_a_wall_clock_jump_beyond_tolerance_ends_the_wait_early`、`test_a_backward_wall_step_never_extends_the_wait` | closed |

### 1.3 W1 SD 鏡（review_w1_sd_113.md）與 W1 QA 鏡

| ID | 前審要求 | 修復宣稱 | 我的重驗 | 判定 |
|---|---|---|---|---|
| SD1-01（P2） | `tools/lib/model_roles.py`（及 W2 新檔）列入兩支 compat-CI 的 push＋pull_request `paths` | 四處各補兩行 | **(c)** `grep` 兩檔：macos `:497-498`、`:891-892`；windows `:621-622`、`:1017-1018`，共 8 行；`(cd AISDLC_SDD && ../.venv/bin/python -m pytest scripts/tests/test_ci_paths_cover_root_consumers.py -q -o addopts="" -p no:cacheprovider)` → `49 passed in 14.08s`、rc=0 | closed |
| SD1-03（P3） | 子代理「不注入」出口 | `inherit` 只限 SUBAGENT 鍵＝不注入；`child_env`＝`{}`；建議行不印 `inherit/`；ENV_SPEC 說明＋`.env.example` 重生；+4 測試 | **(d)** `AUTOSDD_MODEL_SUBAGENT=inherit … --pace`＝建議行 `model: haiku 續跑`、角色行 `子代理=inherit（不注入，沿用視窗模型）`；預設輸出＝`model: sonnet/haiku 續跑`、`子代理=sonnet`（逐字見 §3.7）；突變 W1-M1（任一鍵收 inherit）／M2（child_env 寫字面 inherit）／M3（hint_first 恆印）／M4（首字可為 `-`）／M5（inherit 不分大小寫）／M6（pinned 不歸空）**6/6 KILLED**，控制組 `ran=60 red=[]`；`python tools/lib/quota_policy.py --print-env-example \| diff - .env.example`＝導檔 diff 0 位元組、`.env.example` 78 行 | closed |
| SD1-02＝PRD-01（P2） | PRD 草稿不得宣稱「只印參數 vs 實際」 | 草稿第 2 版改「只印三鍵設定值並註明此限，不印互動視窗實際模型」 | 草稿 A 列逐字確認；實作 `model_roles.roles_line` 只印設定值。**plan 殘留**：`improving_113.md:136` §3.1 誠實劃界 (1) 仍是舊句「只印「參數 vs 實際」」 | closed（plan 殘留見 FQ-03） |
| PRD-02 | 壞值語意：互動面 ⚠️、無人窗口不另出聲 | 草稿 B 區塊註解已改 | 草稿 B 註解逐字確認 | closed |
| PRD-03 | 序位的 Claude Code 版本條件 | A、B 皆加「≥ 2.1.251；更舊版本蓋過呼叫時 model；本機 2.1.295」 | 草稿 A／B 逐字確認 | closed |
| PRD-04 | 三項行為披露（恆注入／蓋原生變數／RESUME 沿用→覆寫） | A、B 皆寫；`inherit`＝不注入 | 草稿 A／B 逐字確認（`inherit` 時原生變數保留與「注入值蓋過」不矛盾，B 已分句） | closed |
| PRD-05 | 「前半／後半」雙義 | 改「設定面／自動觸發面」 | 草稿 A 逐字確認 | closed |
| PRD-06 | 不把行號 L491 寫進 PRD 正文 | 改稱「致動器表下方 `[需核對]` 註記」 | `grep L491` 草稿零命中 | closed |
| PRD-07 | 日期＝落款日；狀態欄寫實際結果＋紀錄指針 | A 列日期 2026-10-10；狀態欄「CONDITIONAL→修復→APPROVE，紀錄＝…〈二〉」 | 指針檔存在。🔴 狀態欄的「→APPROVE」是**未來式**：須待四面最終判決（含本檔）全部非 REJECT 才可落款（見 FQ-02 (d)） | closed（附註） |
| PRD-08 | 同一版本號的修訂列須涵蓋該版全部落款 | 單一 v2.1.16 列涵蓋 W1＋W3 | 草稿 A 列標題與摘要只有 **W1、W3**；同檔 E 段是 **W2（§11.3 落款）**，列內與狀態欄（四方複審名單）都沒有 W2 | **open**（P3，FQ-02 (c)） |
| PRD-09 | 與 `MODEL_DOWNGRADE_PERCENT`／§4.2.2-b 的 (4c) 交叉參照 | A、B 皆加 | 草稿 A／B 逐字確認 | closed |
| PRD-10 | 誠實劃界三句（守衛視窗模型假設／Windows 界定輪次／兩階語意自負） | C 段 ①②③ | 草稿 C 逐字確認（②寫「improving_113 期間僅 macOS 開發機實測」） | closed |
| PRD-11 | 檔案路徑加反引號 | C 段已加 | 兩檔皆存在 | closed |
| PRD-12 | 不在 PRD 帶 `attr=None`／`kind="model"` 實作細節 | B 只留語意句 | 草稿 B 逐字確認 | closed |
| QA1-01（P3） | 下游落款不得寫「call2 只含 sonnet」 | 改「haiku（累計舊回合）＋sonnet（本回合，與頂層 usage 逐項相等）」 | 重讀 `probe_resume_model_113.json`：call1 鍵 `['claude-haiku-5-5']`；call2 鍵 `['claude-haiku-5-5','claude-sonnet-5-5']`、`usage.output_tokens` 46＝sonnet 列 46、`cache_creation` 8767＝8767、haiku 列數值欄與 call1 逐項相等、`total_cost` 0.0396274＝0.0018268＋0.0378006；計畫書 §4 W1 列與證據 二-4c 用正確措辭；全文 `grep "只含 sonnet"` 只剩前審原文引號內的引述 | closed |

### 1.4 W2 審查鏡（review_w2_113.md）

| ID | 前審要求 | 修復宣稱 | 我的重驗 | 判定 |
|---|---|---|---|---|
| W2-01（P3） | 欄位級「缺欄＝None 不是 0」要有鎖 | 測試補丁（0 淨行）：`test_resume_cost.py:104-105` | 突變 F2（缺欄補 0）→ 紅＝`test_unmeasurable_windows_say_so_and_never_write_zero` | closed |
| W2-02（P3） | AST 防成環鎖要認 `from lib import quota_escalation` 等寫法 | `banned()` 併入 alias 名並逐段比對、補壞樣本 | 把 `banned()` 原文逐字抽出對 10 種寫法實跑：CAUGHT 9（`import quota_gate`／`from quota_gate import x`／`from lib import quota_escalation`／`from tools.lib import quota_gate`／`import tools.lib.quota_gate`／`from . import quota_gate`／`__import__`／`importlib.import_module`／函式內延遲 import）、MISSED 1（字串拼接，靜態判準本不可能）；突變 F5（注入 `from lib import quota_escalation`）→ 紅＝`test_resume_cost_never_imports_the_quota_gate_family` | closed |
| W2-03（P3） | `reset_at` 空／缺席 ⇒ `no-anchor` 要有測試 | `test_resume_cost.py:92,96-97` | 突變 F6（刪 `if limit is None` 守衛）→ 紅＝`test_unmeasurable_windows_say_so_and_never_write_zero` | closed |
| W2-04（P3） | `settle_window` 接線要有第二道網（callee 拋例外不得讓下一窗不被排程） | `with contextlib.suppress(Exception):`（`relay_machine.py:468-469`） | 以審查鏡的 `failsoft_probe.py`（改成 TemporaryDirectory 版 `fq_failsoft.py`）在**工作樹原樣**跑：`[baseline] events=['relay_spawned'] register_next_window_called=True relay_seq_after=1`、`[record_window raises RuntimeError] events=['relay_spawned'] register_next_window_called=True relay_seq_after=1`（修前是 `relay_settle_crashed`／`False`／`0`）。測試面：突變 F9（拿掉 suppress）**存活**＝這道網沒有測試鎖（主控依 R197 不增測試方法；FQ-06 P4） | closed（行為成立；無測試鎖＝P4） |
| **W2-05＝spawn 錨**（採納的 P3 建議） | 接力窗（relay_seq≥1）與 `reset_at` 為空路徑改以本窗 spawn 時刻錨定，不再恆 `measured:false` | 證據 二-5b：「spawn 錨改讀 `relay_snapshot_before` 事件 `at`（接力窗與 reset_at 空路徑不再恆 measured:false）」；resume_cost.py 140→153 行 | **(e) 不成立。** 見 FQ-01：生產唯一呼叫點 `relay_machine.py:469` 為 `resume_cost.record_window(state)`，無 `log`；`fq_spawn_anchor_e2e.py` 以**原樣** `settle_window` 收接力窗：`record: {'relay_seq': 1, 'measured': False, 'reason': 'relay-chain-anchor', …None}`；同一組資料直接 `record_window(st, out, log=log)` 則 `measured True／claude-sonnet-5-5／input 5`；`grep record_window(` 全 repo 只有 relay_machine 一處生產呼叫、無 `log=` | **open（P2，FQ-01）** |

### 1.5 額外三項（不在你列的清單，但屬前審條件或我順查到的）

| ID | 狀態 | 重驗 |
|---|---|---|
| QA1-06（P4） | closed | `grep model_hint_line`：`quota_gate.py` 已無該 import（`:136` 那行刪除；斷言行 495→494）；仍有的消費者只有 `quota_messages.py` 自身與兩支測試檔（`QM.model_hint_line`／`quota_messages.model_hint_line`） |
| QA1-02（P3，整合） | closed（主控收尾已重釘） | `tools/tests/test_*.py`＝89 支；`skip_tag_policy._TREE_FILE_FLOORS['tools/tests']` 現 71；`python -m unittest test_schedule_capability_parity.TestUnittestDiscoverConformance.test_scan_surface_is_not_silently_empty` → `Ran 1 test`／`OK` |
| **SD1-04（P3 應修）** | **open（無處置紀錄）** | `test_model_roles.py:480-483` `test_pace_report_is_wired_to_the_model_lines` 仍只是 `inspect.getsource` 子字串鎖；主控 二-4c 裁決、證據〈三〉理論洞表、plan 都沒有 SD1-04（`grep SD1-04` 只剩前審原文）。既未修也未登記＝FQ-05 |

---

## 2. 閘門逐字尾段（本場親跑；原始檔都在 `fq/`）

### 2.1 AutoClaude 全套（`(cd AutoClaude && ../.venv/bin/python -m pytest tests/ -q -p no:cacheprovider)`；02:11）
```
AUTOCLAUDE-PG-DSN-IN-EFFECT=0 AUTOCLAUDE-NESTED-SESSION=1
[PG autodetect] localhost:5432 沒有在聽 ⇒ 不注入（PG 相關測試維持 skip）
4919 passed, 156 skipped in 36.06s
pytest_rc=0
```
（≥ 期望 4919／156／0 failed；skipped 與基線 156 相同。）

### 2.2 lint-imports（`(cd AutoClaude && PYTHONUTF8=1 ../.venv/bin/lint-imports)`）
```
routing) KEPT
autoclaude must not import monorepo harness modules (consume the file contract 
instead) KEPT

Contracts: 9 kept, 0 broken.
lint_imports_rc=0
```

### 2.3 根層指定 17 模組（`fq/gate_root_unittests.txt`、`gate_root_unittests_run2.txt`）
指令＝brief 逐字（`test_model_roles test_resume_cost test_quota_policy test_session_brief test_context_budget_guard.{QuotaEnvFileIsActuallyLoadedTest,ResumeSpawnCarriesTheUnattendedSignalTest,ResumeRouteDegradesOneWayTest,HandbackAddDirIsResolvedDynamicallyTest,FanoutCasualtyRecordTest,ResumeTickWritesStateOnlyAfterConfirmingTest} test_mac_readiness_r82 test_platform_utils_dedup test_subprocess_encoding_hygiene test_platform_neutral_paths test_wake_chain_halt_r278 test_root_infra_parity test_pre_push_dispatcher`）。
```
run1（02:13～02:16，主控同時在改 skip_tag_policy 等）:  Ran 931 tests in 149.387s / OK / rc=0
run2（02:25～02:27，樹自 02:16:06 起靜止）:            Ran 931 tests in 121.379s / OK / rc=0
```
兩次摘要行皆無 `skipped=`／`expected failures`／`FAILED`。單獨：`test_model_roles` `Ran 60 tests`／`OK`；`test_resume_cost` `Ran 5 tests`／`OK`；`tests/utils/test_sliced_sleep.py` `53 passed in 0.47s`（`--collect-only`＝53）。

### 2.4 ruff（不帶 --config，`--no-cache`）
```
tools（brief 指定 11 檔）:   All checks passed!   ruff_tools_rc=0
AutoClaude（10 檔，含 2 新檔）: All checks passed!   ruff_autoclaude_rc=0
```
**加碼（主控收尾編修的 4 檔，不在 brief 清單）**：`ruff check --no-cache tools/lib/governance_docs.py tools/lib/skip_tag_policy.py tools/run_root_unittests.py tools/tests/test_context_budget_guard.py` → rc=1，`Found 4 errors.`（4 個 E501，座標見 FQ-04）。

### 2.5 LOC（`python AutoClaude/tools/check_loc_budget.py --json`，rc=0、stderr 0 byte）
```
{'total': 17413, 'baseline': 17079, 'cap': 20438, 'total_violation': False, 'absolute_violations': [], 'tier_violations': [], 'special_violations': [], 'special_stale': [], 'root_tools_violations': []}
```
我用同一把 `count_loc` 對 HEAD／工作樹逐檔實量（斷言行 HEAD→現）：`model_roles` 新 59、`resume_cost` 新 **99**、`relay_machine` 251→256、`resume_route` 81→90、`quota_messages` 369→379、`quota_gate` 495→494、`quota_policy_env` 178→187、`session_brief` 317→327、`session_resume_planner` 746→746、`auto_resume` 254→295、`sliced_sleep` 新 **32**、`config` 199→202、`verified_cli_versions` 20→38、`main` 152→153。

### 2.6 `.env.example`、帳本、交棒、snapshot
```
python tools/lib/quota_policy.py --print-env-example > gen; diff gen .env.example   → gen_rc=0 diff_rc=0；diff 0 位元組；.env.example 78 行
python tools/check_defect_log_crossref.py → crossref_rc=0；末三行：
  🔴 當前輪 R211 係由 R 系列證據檔／交棒書檔名最大號**現查**推得（不寫死）——本輪的證據檔／交棒書尚未建立時，…（見 lagging_clock_notes()）
  外部阻塞軌（AutoSDD_External_Blocked_Log.md，不計入未結列 warn/fail 分母）：5 筆｜DEF-101-693、DEF-101-856、DEF-200-075、DEF-200-253、DEF-200-313
  結構性長債軌（AutoSDD_Structural_Debt_Log.md，不計入未結列 warn/fail 分母）：6 筆｜DEF-101-018、DEF-101-398、DEF-101-701、DEF-101-702、DEF-101-960、DEF-101-980
  （--unresolved-count：未結列數＝0／全部 207 列｜warn=86 fail=98）
python tools/check_handoff_carriers.py → carriers_rc=0；尾行：✅ 每一筆前瞻延後宣稱都有帳本承接載體
  （[census] 當前輪＝R211；tracked 交接載體＝198 份；前瞻延後行 0 筆；commit 訊息 741 則含前瞻延後宣告 0 筆）
python AutoClaude/tools/snapshot_sync.py --check → rc=0：[snapshot_sync] OK — Snapshot 區段 + sprint 骨架對齊一致
（加碼）python tools/sync_onboarding_baselines.py --check → rc=0（… [rootunit-baseline-live:] {'tests': 5272}）；--check-snapshot → rc=0（… cigate-scripts-snapshot passed 363）
```
**預先測試新文件的承接載體（唯讀）**：把尚未被 tracked 的三份新文件（plan／證據檔／覆蓋矩陣）當載體餵 `check_handoff_carriers.carrier_doc_problems(...)`（`fq_carriers_untracked.py`）→ `problems: 0`、三份文件內前瞻延後行 0 筆。主控 `git add` 後 pre-push 不會因這三份被擋。

### 2.7 `--pace`（(d)；`AUTOSDD_MODEL_SUBAGENT=inherit` 與預設兩種逐字；stderr 只有「session 來源＝…」一行）
預設（本機 `.env`＝HELMSMAN fable）：
```
   🔻 降級建議：kind=five_hour,session,weekly_scoped 已進收緊帶 ⇒ 建議派工帶 model: sonnet/haiku 續跑（只建議不自動改模型；cap 不受本行影響）。
   🤖 模型角色（.env AUTOSDD_MODEL_*）：主控=fable｜子代理=sonnet｜降級=haiku（主控值只管無人喚醒窗口；互動視窗自己的模型 .env 管不到，派工請明寫 model:）
```
`AUTOSDD_MODEL_SUBAGENT=inherit`：
```
   🔻 降級建議：kind=five_hour,session,weekly_scoped 已進收緊帶 ⇒ 建議派工帶 model: haiku 續跑（只建議不自動改模型；cap 不受本行影響）。
   🤖 模型角色（.env AUTOSDD_MODEL_*）：主控=fable｜子代理=inherit（不注入，沿用視窗模型）｜降級=haiku（主控值只管無人喚醒窗口；互動視窗自己的模型 .env 管不到，派工請明寫 model:）
```
預設輸出仍逐字 `sonnet/haiku`（舊字面不變）；inherit 時建議行不含 `inherit/`。

### 2.8 其他零 token 事實
- `claude --version` → `2.1.295 (Claude Code)`；`claude --help` 內 `--max-turns` 零命中、`--permission-mode` 1 命中；`VERIFIED_CLI_VERSIONS` 含 `2.1.295`。
- py39：`ast.parse(feature_version=(3,9))` 對 `resume_cost／relay_machine／model_roles／resume_route` 全 OK；repo 自己的 `test_mac_readiness_r82.py::py39_incompat(source)` 對六支新／改檔皆回 `[]`。
- 空白：`git diff --check`（工作樹）rc=0；新檔 CR=0、行尾空白=0。`git diff --cached --check`（已 staged 的文件版）rc=2：`PRD_Coverage_Matrix_113.md:485: new blank line at EOF`、`ZeroTrust_Audit_113.md:48: trailing whitespace`（貼上的 lint-imports 原文行尾空白）＝FQ-07 P4。

---

## 3. 獨立端到端（我自己寫的，不依賴 Developer／前審的測試檔）

### 3.1 `fq_pin_probe.py`（SD3-02／(b)）：`out_pin_probe.txt`
```
[PASS] 結果 success False／halted True／reason external_resume_required  ⇐ (False, True, 'external_resume_required')
[PASS] Kernel 只跑 1 次（拒絕後不續跑）  ⇐ 1
[PASS] 結果帶 scheduled_resume_at（非 None）  ⇐ 2026-10-10T08:09:31
[PASS] 磁碟 scheduled_resume_at ≈ now+360 分（359.0～361.5），不是 now+30 分（resume_delay）  ⇐ now+359.99 min
[PASS] 結果物的 scheduled_resume_at 與磁碟一致
[PASS] checkpoint step_idx 仍為 1（只改了時刻欄）
[PASS] 4h 等待不被拒絕（進了分片 sleep）  ⇐ slept 30
RESULT: ALL PASS
```
（舊 QA 腳本 `qa_quota_refusal_ck.py` 的 3 小時情境在新出廠上限 18000 下**不再被拒絕**，我跑它看到 `AssertionError: slept`＝出廠預設確已是 18000。）

### 3.2 `fq_main_rc.py`（`main()` 入口 rc；出廠預設）：`out_main_rc.txt`
```
[PASS] main() 在「等待 24000s > 上限 18000s」情境回 rc == 1  ⇐ rc=1
[PASS] Kernel 只跑 1 次、time.sleep 0 次
[PASS] log 有「需外部續跑」與「續跑時刻」與「checkpoint 已落地」
[PASS] 結束 log 帶 reason=external_resume_required
[PASS] 對照組：delay=1 分（60s ≤ 上限）→ 睡完後續跑成功 rc == 0  ⇐ rc=0 calls=2 slept_sum=59.92274 slices=2
[PASS] 對照組每片 ≤ 出廠 slice 30s  ⇐ max=30
[PASS] 邊界：delay=300 分（≈18000s，扣掉執行 latency 後略小於上限）不被拒絕
RESULT: ALL PASS
```

### 3.3 `fq_spawn_anchor_e2e.py`（W2 spawn 錨／(e)）：`out_spawn_anchor_e2e.txt`
合成兩窗逐字稿（reset_at 後窗 0 首請求 `(3,70000,111,fable)`、窗 1 首請求 `(5,5000,90000,sonnet)`）＋兩筆 `relay_snapshot_before`（格式同 planner `append_log`），以工作樹**原樣**的 `relay_machine.settle_window` 收 `relay_seq=1` 那窗（planner 的排程／告警副作用換替身，痕跡落 tmp）：
```
relay_machine.__file__ = /Users/wuweihong/Antigravity/AISDCL_Agent/tools/lib/relay_machine.py
resume_cost.__file__   = /Users/wuweihong/Antigravity/AISDCL_Agent/tools/lib/resume_cost.py
== 1. 工作樹原樣：settle_window 收第 1 窗（relay_seq=1；log 內有兩筆 relay_snapshot_before）
  settle_window rc = 0 | rows = 1
  record: {'relay_seq': 1, 'measured': False, 'reason': 'relay-chain-anchor', 'model': None, 'input_tokens': None, …}
  [FAIL] 接力窗（relay_seq=1）在生產接線下量到自己的首請求（input 5／sonnet）
== 2. 對照：record_window 直接帶 log=（W2 鏡原型的接線形態）
  record: {'relay_seq': 1, 'measured': True, 'reason': None, 'model': 'claude-sonnet-5-5', 'input_tokens': 5}
  [PASS] 函式本身帶 log 時量得到
== 3. 原始碼：relay_machine 對 record_window 的呼叫字面
  relay_machine.py:469: resume_cost.record_window(state)
RESULT: UNWIRED／FAIL（ok1=False ok2=True）
```
（我第一版合成時間軸寫錯〔窗 1 spawn 早於窗 0 的第二筆請求〕造成 2 號對照誤判，已修正時間軸後重跑；結論 1 號與時間軸無關——`relay-chain-anchor` 在任何錨邏輯之前就回了。）

---

## 4. Findings

等級口徑沿用本輪前審（R209／R210 QA 鏡慣例）：P2＝實質缺陷／已採納的修復不生效／對憲法偏離，判 CONDITIONAL 以上；P3＝訊息誤導或附屬缺口，只列；P4＝理論洞／已揭露限制，只登記。我的審查範圍＝驗證閉環＋重跑閘門＋突變，**沒有對新碼做超出規格的對抗式變體搜尋**。

### FQ-01｜P2｜W2 spawn 錨「已採納」的宣稱在生產接線上不成立：`_spawn_at()` 是死碼，且整個分支零測試

**證據**
1. 接線：`tools/lib/relay_machine.py:468-469` 現為
   ```
   with contextlib.suppress(Exception):
       resume_cost.record_window(state)
   ```
   沒有 `log=log`（`settle_window` 的參數就叫 `log`，在作用域內）。全 repo `grep "record_window("`：生產呼叫只有這一處；其餘 5 處在 `test_resume_cost.py`，皆不帶 `log`。`_spawn_at(` 除 `resume_cost.py:133` 外無任何呼叫者。⇒ `_locate(state, seq, log=None)` 恆走 `if relay_seq >= 1: return None, "relay-chain-anchor"`。
2. 行為（§3.3）：工作樹原樣的 `settle_window` 收接力窗 → `measured:False／relay-chain-anchor`；同資料直接呼叫 `record_window(..., log=log)` → `measured:True／sonnet／input 5`。
3. 為什麼會漏：W2 審查鏡的補丁檔 `w2rev/proposed_resume_cost_spawnat.diff` **只改 resume_cost.py**；鏡文 §4.3 寫「接線改 `resume_cost.record_window(state, log=log)`（relay_machine 不增行）」那一刀沒有進任何一份 diff（`proposed_relay_machine_suppress.diff` 只含 suppress；鏡的端到端用的是 `rm_patched/relay_machine_passlog.py`，兩檔唯一差別正是 `log=log`）。主控「三份補丁全部採納」逐份屬實，但三份合起來不含這一行。
4. 測試鎖缺席：5 支測試沒有任何一支走到 spawn 錨。隔離突變（`fq/run_mut_fq.py`，控制組 `ran=5 red=[]`）：
   - F7 `if spawn := None:`（分支不可達）→ **SURVIVED**
   - F8 `_spawn_at` 回遙遠未來時刻 → **SURVIVED**
   - F11 把接線改成帶 `log=log`（假想的修好狀態）→ **SURVIVED**（套件分不出「接了」與「沒接」）
5. 宣稱落在：證據檔 `CrossPlatform_R211_ZeroTrust_Audit_113.md:1543`（二-5b：「接力窗與 reset_at 空路徑不再恆 measured:false」）。反例是 plan §4 W2 列與 PRD 草稿 E 段與 `ledger_row_def508_draft.md`：它們寫的恰是「接力第二窗起 measured:false」——**那三處對「現況」是真的，對 二-5b 是矛盾的**。

**影響**：資料面無害（量不到 fail-safe 成 `measured:false`，與 v1 已揭露限制相同）；但是「採納的修復其實沒生效＋證據檔宣稱已生效＋13 行死碼帶著『接力窗…靠它』的註解」，正是本 repo 最忌的「機制蓋好沒接電」與「宣稱先於查證」。`resume_cost.py:6-8,15-16` 的 docstring 還寫著「planner 不記 spawn 時刻」。

**修法（二擇一，主控裁；A 建議）**
- **A（建議，一字＋一鎖）**：`relay_machine.py:469` → `resume_cost.record_window(state, log=log)`。隔離驗證（`fq/run_wired_regression.py`）：接線改在副本後，會經 `settle_window` 的既有測試 `Ran 196 failures 0 errors 0`（`test_resume_cost`＋`ResumeTickWritesStateOnlyAfterConfirmingTest`＋`test_wake_chain_halt_r278`＋`test_mac_endurance_r83`＋`test_sentinel_tick_e2e_r145`；`relay_machine.__file__` 為副本）。補一支鎖，我已驗證**有牙**（`fq/test_resume_cost_pin.py`＋`run_mut_fq2.py`）：在 `ResumeCostTest` 加
  ```python
  def test_a_relay_window_is_measured_from_its_own_spawn_not_from_reset_at(self) -> None:
      tmp = self._tmp()
      (tmp / "t.jsonl").write_text("\n".join(_LINES) + "\n", encoding="utf-8", newline="\n")
      at = (_RESET + timedelta(minutes=7)).isoformat(timespec="seconds")  # 本窗兩筆請求（+5／+9 分）之間
      event = {"event": "relay_snapshot_before", "at": at}
      (tmp / "log.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8", newline="\n")
      self._settle(tmp, state="resumed", relay_seq=1)
      (row,) = [json.loads(ln) for ln in
                (tmp / "tr" / resume_cost.RECORD_NAME).read_text(encoding="utf-8").splitlines()]
      self.assertEqual([row["measured"], *(row[k] for k in _NUM)], [True, 4, 1, 2])
  ```
  結果：目前樹（未接線）**RED**；接線後 **GREEN**；接線＋F7／F8／「relay 守衛移到 spawn 錨之前」三個突變各 **RED**；其餘 5 支不受影響（`ran=6`）。若不想新增測試方法（MIN_TESTS 零相依餘裕），可把同樣 5～6 行併進 `test_settle_window_logs_one_row_per_real_wake_and_nothing_otherwise` 現有的 `relay_seq=1` 那段之後（我驗證的是獨立方法形態）。
  A 之後須同步改文字：`resume_cost.py` docstring（`:6-8`「planner 不記 spawn 時刻」、`:15-16` ②）、plan §4 W2 列、PRD 草稿 E 段、`ledger_row_def508_draft.md`、plan §4 斷言行／raw 數（FQ-03）。
- **B（撤回）**：移除 `_spawn_at`／`log` 參數與 `:133` 那段（回到 W2 鏡原版 `relay-chain-anchor` 路徑），並把證據檔 二-5b 改成「spawn 錨補丁未採（理由…）」；此時 plan §4／PRD E／帳本草稿現行字面才是對的。

**判準**：closure 審查的對象正是「宣稱已修」；這一格宣稱不成立、套件分不出來。

### FQ-02｜P3｜PRD 修憲草稿第 2 版（尚在 scratchpad，PRD 本文未改）仍有 4 處待訂正，落款前必須先修

(a) **D 段**（`prd_amendment_v2116_draft.md:40`）「剩餘 > 上限時引擎以 rc=1 退出並於 **stderr** 明示需外部重啟」——**不實**：ERROR 只出 stdout（logger 唯一 console handler＝`sys.stdout`）與 `logs/autoclaude.log`，stderr 0 byte（SD3-08 與 W3 修復交件 §3 第 1 點已揭露並把程式面全改成「log 的 ERROR 行」；本草稿寫在修復交件之後）。改「並在 log 的 ERROR 行明示需外部重啟」。
(b) **E 段**「接力第二窗起（relay_seq ≥ 1）…標 measured:false」：與 FQ-01 的處置連動——採 A 則須改成「接力窗以本窗 spawn 時刻（planner 落的 relay_snapshot_before）錨定；沒有 spawn 痕跡時才 relay-chain-anchor」；採 B 則現行字面正確。另 E 段寫「收尾時」落帳，實作接線在 `settle_window` **最前**（`resolve` 之前，D6），不是收尾。
(c) **PRD-08 未閉**：v2.1.16 列的標題／摘要只涵蓋 W1＋W3，**沒有 W2（§11.3 落款，即 E 段）**，狀態欄的四方複審名單也沒有 W2 的 SD＋QA 合一鏡（APPROVE）。同一版本號的列須涵蓋該版全部落款。
(d) 狀態欄「CONDITIONAL→修復→APPROVE」是未來式：須待本檔與其餘鏡的最終判決皆非 REJECT 才可落款；本檔現判 REJECT（FQ-01），落款文字應在 FQ-01 處置並複驗後才定稿。
另：`max_inprocess` 7200→18000、tolerance 120→5 兩個偏離是以「PRD 與實測不符／演算法證明」修憲（依「PRD 是最高憲法」記憶：須四方全同意）——草稿 D 已具名；請在落款處寫明同意名單，避免落款先於同意。

### FQ-03｜P3｜計畫書／證據檔／帳本草稿的數字與敘述殘留（逐點座標；均為主控回填 §4～§8 時一併處理）

| # | 座標 | 現況 | 應為／問題 |
|---|---|---|---|
| 1 | `improving_113.md:136` §3.1 誠實劃界 (1) | 「只印「參數 vs 實際」」 | SD1-02／PRD-01 已判實作沒有；規格文字不改也行，但 §8 須登記訂正（§8 尚空） |
| 2 | `improving_113.md:170` §3.3 Architecture_Design_Review 1 | 「（PRD 7200s）…交棒由根層哨兵承接」 | 出廠 18000、無自動承接者；同上，§8 登記或就地劃線訂正 |
| 3 | `improving_113.md:192` §4 W2 列 | 「斷言行 89／上限 90」「+5 raw」「接力第二窗起 measured:false」 | 現 `count_loc` resume_cost＝**99**（超出規格上限 90，證據 二-5b 已自陳）；relay_machine raw 實為 +7（import contextlib／resume_cost 各 1＋2 行註解＋if／with／呼叫），斷言行 251→256（+5）；「接力第二窗起 measured:false」與 二-5b 矛盾（見 FQ-01） |
| 4 | `improving_113.md:193` §4 W3 列 | 「31 LOC」「44 支＋boot 2＋修復包測試」 | `sliced_sleep.py` 現 32；`test_sliced_sleep.py` 現 **53** 支（`--collect-only`），「44」是 Developer 初值 |
| 5 | 證據檔 `:519`（二-3 主控裁決原文） | 「…引擎 rc=1 退出並於 **stderr** 明示…」 | 歷史裁決原文可留，但同檔 `:526` 已記 stderr 項 skipped；建議在 `:519` 後加一句「stderr 部分未實作，見 二-3b」，免讀者誤取 |
| 6 | 證據檔 二-5b（`:1543`） | 見 FQ-01 | 隨 FQ-01 處置改寫 |
| 7 | `ledger_row_def508_draft.md`（scratchpad，尚未入帳本） | 「接力第二窗起 measured:false」「詳 R211 證據檔〈二〉〈五〉」 | 隨 FQ-01 對齊；〈五〉結案帳目前是空節 |
| 8 | 證據檔／plan 內對 DEF-200-507／508 的引用 | **零處**（grep 兩個新號 rc=1；主控收尾訂正：原文樣式含截斷 ID 字面、觸發引用存在性鎖）；帳本最大 ID＝DEF-200-506 | 主控加列時，plan §7、證據〈五〉同步引用；我對文件內 26 筆「DEF-xxx（fixed／closed-by-decision／open）」宣稱逐筆比對帳本（`fq_def_status.py`）：**0 不符** |
| 9 | plan §5～§8 | 皆為「（回填）」空節 | 非缺陷，列為收尾義務：§6 四方審查閉環（含本檔 REJECT→處置→複驗）、§7 帳本列、§8 誠實劃界（#1／#2 的訂正、Windows 未驗、PG／Dual 後端 pin 路徑未實跑、機器睡眠單調鐘只依文件、inherit 行為層無真機、真子代理未派） |

### FQ-04｜P3｜主控收尾編修的 4 行 E501（pre-push 的 `ruff check tools/` 會擋）

`ruff check --no-cache tools/lib/governance_docs.py tools/lib/skip_tag_policy.py tools/run_root_unittests.py tools/tests/test_context_budget_guard.py` → `Found 4 errors.`：
- `tools/lib/governance_docs.py:658`（107＞100）、`:662`（129＞100）——登記兩份 R211 文件的新註解行；
- `tools/lib/skip_tag_policy.py:408`（104＞100）、`:483`（103＞100）——兩處重釘註解（含反引號路徑的中文行）。
（記憶：tools/ 下 E501 以 EAW 寬度算，CJK 算 2 欄；修法＝換行縮短，不增行數棘輪以外的東西。）這 4 行是主控在我審查期間新寫的，樹靜止後仍在；commit 前請 `ruff check` 這四檔再確認。

### FQ-05｜P3｜SD1-04（`--pace` 角色行只有 `inspect.getsource` 子字串鎖）沒有處置紀錄

前審標 P3 應修；主控 二-4c 與證據〈三〉都未提。`test_model_roles.py:480-483` 仍是 `assertIn("model_lines(", inspect.getsource(quota_gate.pace_report))`。處置二擇一：照前審補 `test_context_budget_guard.py` 既有 in-process `qg.pace_report(...)` 夾具的一行 `assertIn("模型角色", text)`（淨 +1 行，該檔是棘輪標的），或登記〈三〉理論洞（`--pace` 角色行無端到端鎖；halt 短路不印角色行屬已知可接受）。**我的行為驗證補位**：本場親跑 `--pace` 兩形態（§2.7）證實接線實際出行，不替代測試鎖。

### FQ-06｜P4｜只登記

1. `resume_cost.py` 註解／docstring 過時：`:6-8`「planner 不記 spawn 時刻（守衛面零改動），改以…最後一筆早於 reset_at 的真 assistant 為錨」、`:15-16` ②（接力窗一律 relay-chain-anchor）、`:133` 行尾「接力窗與 reset_at 為空的 probe 路徑都靠它」——FQ-01 採 A 後前兩處須改（`_spawn_at` 為首選錨、reset_at 錨為退路），採 B 後第三處須刪。
2. W2-04 的第二道網（`with contextlib.suppress(Exception)`）**無測試鎖**：突變 F9（改成 `if True:`）存活。行為已由 `fq_failsoft.py` 證實；R197 下不加測試可接受，登記即可。
3. W3 拒絕上限的相等邊界：突變 W3-M8（`wait_secs > cap` → `>=`）**存活**（5 檔 210 案全綠）。等待秒數是時鐘導出的 float，恰等於 18000.0 實務上不可能；前審 QA 的 E2E A2（7200.0／7200.001／7199.0）在 QA 腳本內、不在 repo。
4. 前審 P4（QA3-05～09、SD3-05～14、SD1-05～13、QA1-03～09、W2-06～10）：〈三〉理論洞表已登記 12 條；我未逐條重驗（brief 未要求）。

### FQ-07｜P4｜staged 文件的空白

`git diff --cached --check` rc=2：`docs/06_quality/CrossPlatform_R211_PRD_Coverage_Matrix_113.md:485: new blank line at EOF`、`docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md:48: trailing whitespace`（第二處是逐字貼上的 lint-imports 輸出行尾空白，屬「逐字不重組」，可保留；第一處刪檔尾空行即可）。hooks 不跑 `git diff --check`（`grep` pre-commit／pre-push 零命中），純整潔項。

### FQ-08｜P4（流程）｜「凍結」窗口內樹被並行改動

見 §0.2。這次的並行動作（staged、重釘棘輪、補丁套用、證據檔編修）都是合理的收尾，但與 brief「凍結狀態」不符；對審查的影響＝我的閘門結果是不同時點的樹：AutoClaude 全套與 lint-imports（02:11）不受影響（AutoClaude 檔 sha 全程不變）；根層模組我在樹靜止後（02:25）重跑一次補強。建議收尾單人窗口在 FQ-01 處置後，**以最後一個位元組變動之後的樹**重跑一次 brief 指定的閘門再 commit。

---

## 5. 突變表（全部隔離副本；工作樹零改動）

### 5.1 W3（外掛 `fq/plug/fq_w3_mut_plugin.py`；5 檔 210 案，控制組同路徑載副本 `210 passed`）
| 突變 | 結果 | 紅的測試（節錄） |
|---|---|---|
| W3-M1 `>`→`>=`（容忍邊界；QA3-02） | KILLED（1 failed） | `…test_the_tolerance_boundary_is_strictly_greater_than[5.0-calls0-False]` |
| W3-M2 跳躍訊息兩句對調（SD3-04） | KILLED（2 failed） | `…jump_beyond_tolerance_ends_the_wait_early`、`…backward_wall_step_never_extends_the_wait` |
| W3-M3 halt 拒絕不改寫（SD3-02） | KILLED（1） | `…quota_axis_refusal_pins_the_real_resume_time_into_the_checkpoint` |
| W3-M4 `ceil`→`floor` | KILLED（1） | 同上 |
| W3-M5 拿掉 `if saved`（憑空造 checkpoint） | KILLED（1） | `…refusal_never_fabricates_a_checkpoint_it_could_not_read_back` |
| W3-M6 等待執行兩次（QA3-04） | KILLED（6） | 含 `tests/core/test_auto_resume.py::…::test_run_with_future_resume_waits`、`test_r82…::test_the_halt_loop_really_consults_the_quota_axis` |
| W3-M7 續跑路徑也改寫 | KILLED（1） | `…far_scheduled_checkpoint_is_refused_before_the_kernel_runs` |
| W3-M8 `wait>cap`→`>=` | **SURVIVED** | —（FQ-06 #3） |
| W3-M9 拿掉拒絕後的 emit | 5 檔 SURVIVED；加跑 `tests/core/test_auto_resume_metrics.py` → KILLED（3 failed，控制組 18 passed） | metrics 三支（套件層級有鎖） |
| W3-C1／C2／C3 預設改回 7200／60／120 | 各 KILLED（1） | `…defaults_that_deliberately_deviate…`／`…slice_default_matches_prd_section6_block9` |

### 5.2 W1 `model_roles`（`fq/run_mut_w1.py`；控制組 `ran=60 red=[]`）：M1～M6 **6/6 KILLED**（見 §1.3 SD1-03）。

### 5.3 W2 `resume_cost`／`relay_machine`（`fq/run_mut_fq.py`；控制組 `ran=5 red=[]`）
| 突變 | 結果 |
|---|---|
| F2 缺欄補 0（W2-01） | KILLED |
| F3 接力守衛 `>=1`→`>=2` | KILLED |
| F5 注入 `from lib import quota_escalation`（W2-02） | KILLED |
| F6 刪 `no-anchor` 守衛（W2-03） | KILLED |
| F10 落帳閘放寬到 `resume_failed` | KILLED |
| F9 拿掉 suppress 第二道網（W2-04） | **SURVIVED**（FQ-06 #2） |
| F7／F8／F11 spawn 錨分支不可達／回未來時刻／假想接線 | **三個皆 SURVIVED**（FQ-01） |

---

## 6. 重現清單（`fq/`）
- 閘門原始輸出：`gate_autoclaude_pytest.txt`、`gate_lint_imports.txt`、`gate_root_unittests.txt`、`gate_root_unittests_run2.txt`、`gate_ruff_tools.txt`、`gate_ruff_autoclaude.txt`、`gate_ruff_extra.txt`、`gate_loc.json`、`env_example_diff.txt`、`gate_crossref.txt`、`gate_carriers.txt`、`gate_unresolved.txt`、`gate_snapshot.txt`、`gate_sync_check.txt`、`gate_sync_snapshot.txt`、`pace_default_full.txt`、`pace_inherit_full.txt`、`out_ci_paths.txt`。
- E2E／探針：`fq_pin_probe.py`→`out_pin_probe.txt`；`fq_main_rc.py`→`out_main_rc.txt`；`fq_spawn_anchor_e2e.py`→`out_spawn_anchor_e2e.txt`；`fq_failsoft.py`→`out_failsoft.txt`；`fq_carriers_untracked.py`；`fq_def_status.py`。
- 突變：`plug/fq_w3_mut_plugin.py`＋`mut_w3_*.txt`；`run_mut_w1.py`＋`mut_w1_*.txt`；`run_mut_fq.py`＋`mut_w2_*.txt`；`test_resume_cost_pin.py`＋`run_mut_fq2.py`＋`mut_w2pin_*.txt`；`run_wired_regression.py`→`out_wired_regression.txt`。
- 工作樹對帳：`fq_git_status_start.txt`（上一層）、`fq/git_status_end.txt`、`fq/sha_manifest_start.txt`、`fq/sha_check_end.txt`。

## 7. 誠實劃界（沒做／做不到）
- 只在 macOS 驗；Windows／PS 5.1 未驗（本輪新碼為純 Python，無路徑分隔符／shell 依賴；yml 的 `paths` 只以 AISDLC_SDD 鎖在 mac 驗）。
- 未跑 `tools/run_root_unittests.py` 全套（brief 明令；主控收尾跑，預期紅＝棘輪／檔數下限／MIN_TESTS 已由主控在重釘中）。
- 未跑 `claude -p`（零 token）；`inherit`／`CLAUDE_CODE_SUBAGENT_MODEL` 的行為層（真子代理是否跟隨視窗模型）仍只有文件＋二進位字串層證據；真機睡眠下單調鐘行為仍只依文件。
- PG／Dual 後端的 `_pin_resume_time` 路徑未實跑（只驗 File／InMemory）。
- 沒有逐條重驗前審全部 P4（brief 未列）。
- 我的第一版 spawn 錨合成時間軸有誤（窗 1 spawn 設得早於窗 0 第二筆請求），已修正重跑；FQ-01 的結論不受影響。

