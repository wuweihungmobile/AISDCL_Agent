# CrossPlatform R158 — SessionGate 誤讀四問／Status Line 收尾證據檔

> 收尾單人窗口（2026-09-20）撰。輸入＝`DECISION.md`（主控裁決）、`PKG_REPORTS.md`（六包回報）、
> 五份分析（`analysis_architect/sa/sd/qa/docs.md`）、兩份反駁（`refute_q1q2.md`／`refute_q3q4ci.md`）、
> `moved_lore_r158_p2.md`（已過時，未採用）／`moved_lore_r158_p6.md`。帳本新列：DEF-200-333～342。

## 一、使用者四問與結論（逐字抄 `DECISION.md` 首節）

- **Q1「開新視窗第一擊被擋、不能寫檔」**：全 repo 能在 Write/Edit 前 deny 的只有 SDD
  `context_ledger_pre`（需 `SDD_ACTIVE_VERSION`）。精確對應「Read/Bash 能用、只有一般檔
  Write/Edit 被擋」的是 FSM `AUTO_COMPACT_PENDING` 且 `pending_owner` 缺席（舊版狀態檔）的
  fail-closed 分支（`fsm_runtime.py:637-687`）；全擋的是 `_BLOCKING_STATES` 四態
  （`fsm_runtime.py:622-627`：`ESCALATION`／`ESCALATION_FINAL`／`TERMINATED`／
  `TOKEN_BUDGET_CRITICAL`）。兩者都要該機器的 FSM-STATE 殘留舊 session 狀態，且
  v0.23~v0.29 hook 仍會寫專案級 `TOKEN_BUDGET_CRITICAL`。**Windows 端實值主控看不到 ⇒
  必須由使用者跑診斷腳本親驗**（見〈六、Windows 親驗清單〉）。另一條讓模型「自述被擋」的是
  額度 halt 帶的重複紅字（每次 Read/Bash 都 rc=2，且少了「收斂不受影響」澄清句）——它不擋
  任何工具，但會讓模型誤讀。
- **Q2「不查真實數據」**：真實數據出口存在（`--check`／`--pace`／status line feed），但
  SessionStart 沒有任何機制把真實數字餵進模型；SessionStart 的 DECISION-TRACE 還原樣列
  10 天前的 `TOKEN_BUDGET_CRITICAL ratio=0.99` 而無「已解除」標記；router 的版本漂移告警
  走 stderr exit 0 ⇒ 模型永遠看不到。
- **Q3「數字不符」**：mac 三次親跑 harness used＝逐字稿 used（差=0）。官方文件明文：status
  line 百分比與 `/context` 因計算時機不同可能不一致，非缺陷。Windows 因未裝 statusLine 無法
  比對。**不是新缺陷**。殘餘小缺口：compact 後空窗時 `harness_feed.check_lines()` 完全靜默。
- **Q4「Windows 沒有 ctx 行」**：從未在 Windows 安裝；repo 層刻意不加（閃窗疑慮、未親驗）；
  既有 `_comment_windows` 建議 Git Bash 違反鐵律一。官方：Windows 上 statusLine 由 Git Bash
  執行（有裝才用，否則 PowerShell），恆 shell form；反斜線會被 bash 吃掉 ⇒ 正斜線＋雙引號。
- **CI #250**：`file_lock.py:50` `_write_sentinel` 的 `os.open(O_CREAT|O_EXCL)` 在 Windows
  delete-pending 態丟 `PermissionError`，取鎖迴圈只接 `FileExistsError`。15 次 CI 首見，間歇性。

## 二、五方分析與三份反駁的要點（各 3~5 條，附 file:line）

### Architect（`analysis_architect.md`）
- A1 路徑 1：FSM 專案級 `_BLOCKING_STATES` 卡住全新 session（`fsm_runtime.py:622-627`）。
- A1 路徑 2/3：`AUTO_COMPACT_PENDING`＋規格檔寫入、owner 未知時 fail-closed（`fsm_runtime.py:637-687`）——**Q1 最精確候選**。
- A1 路徑 5：SessionStart 呈現層「陳舊紅字」造成模型自行誤判（非機械 deny，直接解釋 Q1/Q2）。
- A2 選定方案 1b：SessionStart 呈現層溯源強化（不做真自動恢復，只做澄清句），避免違反 Rule 9 禁令。
- A3：repo 層 `settings.json` 刻意不加 Windows status line（閃窗疑慮、未親驗），需 Windows 使用者層手動安裝。

### SA（`analysis_sa.md`）
- S2：PowerShell 5.1 診斷腳本（Q1 專用），全程唯讀，通過 `lint_powershell_command.py` 三條規則核對。
- S3：真實數據出口盤點——`context_budget_guard.py` 模組 docstring 第 43 行自陳「SessionStart 只做 `arm_sentinel` 與 handback 宣告，不量測、不出聲」；84% 以下完全沉默（`tier_of()` 回 `None`）。
- S4：halt 重複訊息（`quota_gate.py:1140-1147`）缺「收斂不受影響」澄清，首則（`quota_messages.py:278-283`）有；重複訊息卻是撞牆期間人唯一持續看得到的版本——**有真實誤讀風險**。
- T6.7（QA 借用同一份分析）：Windows 原生重跑 `test_file_lock.py` 20 次以重現 CI #250 競態。

### SD（`analysis_sd.md`）
- D1：CI #250 file_lock.py 修法——平台分流 `_ACQUIRE_TRANSIENT_ERRORS`。
- D2：Q4 Windows status line 安裝器——`pythonw.exe`＋兩 token、不經 shell 包裝（後被反駁者部分推翻，見下）。
- D3：Q1 修法三案，選 1b（SessionStart 溯源強化）。
- D4：Q2 機制設計——SessionStart 無條件真實數字簡報。
- D5：LOC/棘輪親跑 `check_loc_budget.py --json`：`total=17318/baseline=17079/cap=20438`（動工前）。

### QA（`analysis_qa.md`）
- T6：Windows 端使用者親驗清單（PowerShell 5.1，六項＋誠實劃界），見〈六、Windows 親驗清單〉逐字收錄。
- S3/S4 對照組：真實數據出口表格逐項列 CLI／hook 兩套系統互不相通。
- 誠實劃界：QA 未能在 mac 上重現 Windows 環境的 `SDD_ACTIVE_VERSION` 缺漏或版本落差情境，列為「本分析最大未驗證假設」。

### 反駁者（`refute_q1q2.md`／`refute_q3q4ci.md`）
- refute_q1q2 §1.1：反駁 Architect「額度守衛 halt PostToolUse exit 2 是最貼近 Q1 一致重現候選」——結構上不可能解釋「不能寫檔」，Write/Edit 從未進過這支 hook 的任一事件（PreToolUse／PostToolUse matcher 皆不含 Write/Edit）。
- refute_q1q2 §0：合成 payload 驅動 `context_budget_guard.py` 的 halt 帶行為（親測，隔離環境防污染真實 `~/.autosdd`）。
- refute_q3q4ci §1a/1d：mac 上差=0 的嚴謹度覆核，已讀 `context_budget_guard.py:501-536` `read_context_feed()`、`tools/statusline_context_feed.py:105-118` `_current_usage_sum()`，逐項核實非巧合。
- refute_q3q4ci §2/(c)：file_lock 根因唯一性——`gh run view 35452796159 --log-failed` 完整 Traceback，確認 `_write_sentinel` 的 `O_CREAT|O_EXCL` 是唯一觸發點。
- refute_q3q4ci §b：改動 B（`_is_stale()` 吞 `PermissionError` 回 `False`）裁定**成立，而且比 QA 已知風險更嚴重**（會結構性關閉陳舊鎖回收）——主控裁決故不做改動 B（見 DEF-200-341）。

## 三、修復包 P1～P6 與紅→綠證據（逐字貼 `PKG_REPORTS.md` 摘要行）

### P1 file_lock（SDD v0.30）
檔：`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/file_lock.py`、`tests/test_file_lock.py`。
改動 A：模組常數 `_ACQUIRE_TRANSIENT_ERRORS = (FileExistsError, PermissionError) if os.name == "nt" else (FileExistsError,)`；acquire 迴圈 `except _ACQUIRE_TRANSIENT_ERRORS`。主控追加窄護欄：`_STAT_TRANSIENT_ERRORS`，acquire 的 except 內 `_is_stale()` 呼叫包 try/except。**未改 `_is_stale` 本體**（反駁者否決改動 B，見 DEF-200-341）。
測試：新增 `AcquireTransientPermissionErrorTests`（3 支）＋`StatTransientPermissionErrorTests`（2 支）。
紅：`2 failed, 1 passed, 7 deselected`／`1 failed, 1 passed, 10 deselected`；
綠：`python -m pytest tools/fsm_runtime/tests/test_file_lock.py tools/fsm_runtime/tests/test_conversation_ledger.py -q` → `61 passed, 1 skipped in 3.94s`。ruff `All checks passed!`。

### P2 額度 halt 訊息＋harness_feed（根層）
檔：`tools/lib/quota_messages.py`（新常數 `HALT_CONVERGENT_CLARIFICATION`）、`tools/lib/quota_gate.py`、`tools/lib/harness_feed.py`、`tools/tests/test_context_budget_guard.py`。
紅：`AssertionError: [] != ['harness feed 存在...']`；`AssertionError: '你剛才那次工具呼叫已正常執行完成' not found in '...'`。
綠：`cd tools/tests && python -m unittest test_context_budget_guard -q` → `Ran 652 tests in 31.137s` / `OK (skipped=10)` rc=0。ruff 全綠。

### P3+P4 陳舊阻斷態可見性（SDD v0.30 session_start ＋ 根層 router）
P3 檔：`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/session_start.py`（`_decision_trace_staleness_note(...)`）；`tools/fsm_runtime/tests/test_session_start_rules.py`（+3）。綠：`8 passed in 0.39s`。
P4 檔：`.claude/hooks/sdd_hook_router.py`（`_target_writes_legacy_token_budget_critical()`／`_drift_advisory_text()`／`_merge_advisory_into_stdout()`）；新 `tools/tests/test_sdd_hook_router_r158.py`（13 支）。綠：`Ran 13 tests in 0.059s / OK`；`test_check_hooks_liveness` `Ran 173 tests / OK (skipped=5)`。ruff 全綠；router 未破線。

### P5 status line 安裝器（根層）
檔：新 `tools/install_statusline.py`、`tools/statusline_context_feed.py`（新 `build_command()`／`resolve_windows_interpreter()`／`_quote_token()`）、新 `tools/tests/test_install_statusline.py`（30 case）。
偏離（主控接受）：token 含空白才加雙引號。
綠：`python -m unittest test_install_statusline test_statusline_context_feed -q` → `Ran 44 tests in 0.393s / OK`；`test_check_wrapper_thinness.TestRootGateToolsRejectUnknownFlags` 8 tests OK；`--dry-run`／`--print-command` rc=0、零 `.bak` 產生。ruff 全綠。
回報棘輪：`test_platform_neutral_paths.py` 樹檔數腐化上界（`tools/tests`／`tools` 兩桶）＋`test_subprocess_encoding_hygiene.py` 內 7 支同一則——本輪已重釘（見〈五、棘輪重釘清單〉）。

### P6 SessionStart 真實數字簡報（根層）
檔：新 `tools/lib/session_brief.py`、`.claude/hooks/context_budget_guard.py`（史料壓縮，原文逐字保全於 `moved_lore_r158_p6.md`）、`tools/tests/test_context_budget_guard.py`、新 `tools/tests/test_session_brief.py`（14 支）。
綠：`python -m unittest test_session_brief -q` → `Ran 14 tests in 0.003s / OK`；`HandbackSessionStartAnnounceTest`+`SentinelWiringTest` → `Ran 18 tests / OK (skipped=4)`；整檔 → `Ran 654 tests in 30.420s / OK (skipped=10)`。ruff 全綠。
🔴 P6 自述新測試「寫出即通過、未先出現失敗態」；本收尾窗口未逐支對 HEAD 版重驗（超出收尾窗口的唯讀複審範圍，留待下一輪四方複審時對抗式覆核）。

## 四、全套閘門實跑（收尾單人窗口，2026-09-20）

- 根層：`python tools/run_root_unittests.py`（首次實跑 rc=1，靜態標籤掃描階段早退：`tools/tests` 樹檔數下限 62 已過期＋`windows-compat-ci.yml`／`macos-compat-ci.yml` 缺 `tools/install_statusline.py`／`tools/lib/session_brief.py` 兩份消費檔路徑）。逐項修復後重跑：`ruff check tools/ .claude/hooks/ --no-cache` → `All checks passed!`；`TestGuardLayerRatchet`／`TestRegressionLaneSplit` 65 tests OK；完整 `run_root_unittests.py` 見下方最終收工節。
- SDD：`cd AISDLC_SDD && bash scripts/ci-gate.sh` 首次實跑 rc=1（`scripts/tests/test_ci_paths_cover_root_consumers.py` 兩支：macos-compat-ci.yml／windows-compat-ci.yml 皆缺同兩份消費檔）；修復後 `scripts/tests/test_ci_paths_cover_root_consumers.py -q` → `49 passed in 11.75s`；完整 ci-gate 見下方最終收工節。

### 最終收工（逐字貼閘門輸出）

- 根層 `python tools/run_root_unittests.py` → rc=1，`2 failures / 0 errors / 0 unexpected successes`：
  `test_check_defect_log_crossref.TestEarlyExitAnnouncesUnrunChecks.test_the_real_gate_still_reaches_the_late_checks`
  與 `TestMain.test_main_against_real_repo_is_clean`；`✅ unittest 數量下限釘選通過：發現 4429 個測試（下限 4371）`。
  `AUTOSDD_NET_RATCHET_OFF=1 python -m unittest` 對這兩支重跑 → 皆 `ok`。
- SDD `bash scripts/ci-gate.sh` → rc=0，`逐軌計數：AISDLC_SDD_v0.01:1475 AISDLC_SDD_v0.30:1949 scripts/tests:353`。
- `ruff check tools/ .claude/hooks/ --no-cache` → `All checks passed!` rc=0。
- `git status --short` → 22 個 `M` + 6 個 `??`（收尾窗口回報寫 21；SA 二次複審與主控 `git status --short | grep -c '^ M'` 實測皆 22，差在計數，22 檔逐一核對皆在六包＋收尾自述範圍內，無隱藏變更）。

🔴 淨額棘輪紅＝發現輪預期：本輪對帳本淨增 3 筆 open（DEF-200-340／341／342），未結淨額棘輪機制
正確攔下上述兩支失敗，可用逃生口證明非誤鎖。**commit 那一次帶 `AUTOSDD_NET_RATCHET_OFF=1`、
push 時不得帶**（628f6e99 教訓：pre-push 與 commit 共用同一個 shell env 時，這個逃生口會洩入
根層其他 env 敏感測試，致其翻紅）。

## 五、棘輪重釘清單（表名／舊值→新值／原因）

| 表 | 舊值→新值 | 原因（本輪造成） |
|---|---|---|
| `.github/workflows/windows-compat-ci.yml` paths（2 處 push/pull_request 區塊） | 缺 → 補 `tools/install_statusline.py`／`tools/lib/session_brief.py` | 新增根層消費檔未列入 paths，`scripts/tests/test_ci_paths_cover_root_consumers.py` 逐字指名 |
| `.github/workflows/macos-compat-ci.yml` paths（2 處） | 同上 | 同上 |
| `tools/lib/skip_tag_policy.py::_TREE_FILE_FLOORS['tools/tests']` | 62 → 64 | 本輪新增 3 支回歸鎖檔，`tools/tests` 由 78→81 支，62 只剩實測 77%，判準逐字指示重釘為 64 |
| `tools/tests/test_platform_neutral_paths.py::_scan_roots()` `tools/tests` 桶 | 64 → 79 | 同上機制，`tools/tests` 由 80→83 支，過腐化上界 80，判準逐字指示重釘為 79 |
| `tools/tests/test_platform_neutral_paths.py::_scan_roots()` `tools` 頂層桶 | 27 → 36 | 新增 `tools/install_statusline.py` 頂層檔，該桶由 37→38 支，過腐化上界 37，判準逐字指示重釘為 36 |
| `tools/tests/test_adr_xplat001_c1c2_lock.py::_FROZEN_GUARD_LINES` | 101669 → 102515（+846） | 逐檔漂移：三支新回歸鎖（297／189／220）＋`test_context_budget_guard.py` +117／`test_platform_neutral_paths.py` +4／`test_mac_endurance_r83.py` +3（P6 行為變更同步訂正）／本表自身 +16 |
| `_GUARD_LINES_REPIN_LOG` | 新增 R158 一列 | ARCH-01 對帳義務，`--print-guard-lines` 覆核收斂 |
| `_REGRESSION_LANE_LOG` | 新增 R158 一列（309） | router 全額 189＋context_budget_guard 全額 117＋mac_endurance_r83 全額 3＝309，主軌 846−309＝537 貼齊該輪上限 |
| `_REPIN_LOG_FROZEN_PREFIX_LEN`／`_REPIN_LOG_HISTORY_SHA256` | 237→238／`b55177a8...`→`e402247c...` | 追加新列後自我凍結，同既有體例（覆核收斂多次後的最終指紋） |
| `_FROZEN_PREFIX_REWRITE_LEDGER` | 新增 R158 一列 | 指紋鏈接 `b55177a84c3b`→`e402247cc758`，DEF-ID＝DEF-200-333 |
| `tools/tests/test_mac_endurance_r83.py::EscapeHatchAndNoProliferationTest::test_session_start_stays_silent_and_exit_zero_on_this_machine` | 斷言改寫 | P6 讓 SessionStart 無條件送出真實數字簡報，舊斷言「stdout 必為空字串」不再成立；改判合法 JSON 且含 `[SDD-CTX-GUARD]` 標記 |
| `tools/lib/governance_docs.py::_GOVERNANCE_DOCS` | 新增本證據檔路徑 | 新建治理文件即刻登記 |
| `docs/06_quality/CrossPlatform_R145_Scan_Findings.md`／`docs/04_planning/AutoSDD_improving_112.md` | 新增 `<!-- guard-total:R158 -->` 兩站點 | doc-total 對帳（≥2 站點），同 R129～R157 寄居體例 |

## 六、搬遷史料（`moved_lore_r158_p6.md` 全文內嵌，非僅引用檔名）

P6 為守 `context_budget_guard.py` special-tier raw-line 棘輪（動工前 1087/1089，headroom 僅 2 行），
把四段原始 docstring/comment 壓縮成較短敘述。以下為 `moved_lore_r158_p6.md`（scratchpad，未受 git
追蹤）的逐字全文，避免該檔被清理後這兩段判準性文字從 repo 永久消失：

### 段落 1：`quota_limits` re-export 說明（原第 105-108 行）

原文：
```
# 額度**撞線判讀**唯一的家＝`tools/lib/quota_limits.py`。刻意 hard import（判讀原語
# 給 fallback stub 等於讓同一份字面有第二個家）。下面 11 個在本檔內不會被呼叫，是給
# `tools/session_resume_planner.py`（`guard.<name>` 取用）的純再匯出，刪任一個都會
# 在無人看管的排程路徑上 AttributeError。
```
壓縮後：
```
# 額度撞線判讀唯一的家＝`tools/lib/quota_limits.py`（刻意 hard import）；下面 11 個是
# 給 `session_resume_planner.py` 用的純再匯出，全文搬 scratchpad/r158/moved_lore_r158_p6.md。
```

### 段落 2：`blocking_reach_problems` docstring（原第 172-177 行）

原文：
```
def blocking_reach_problems(blocking: tuple[str, ...], observed: set[str]) -> list[str]:
    """阻斷臂的**有效性**判準（純函式）：圈到的名字必須真的會出現。回空 list ＝合格。

    `observed`＝實測逐字稿裡出現過的 `tool_use` 名稱集合。空集合時**不判**——那代表
    「這台機器上量不到」，不代表「命中面是 0」，而「量不到 ≠ 量到零」是本檔通篇的紀律。
    """
```
壓縮後：
```
def blocking_reach_problems(blocking: tuple[str, ...], observed: set[str]) -> list[str]:
    """阻斷臂的有效性判準（純函式）：圈到的名字必須真的會出現，回空 list＝合格。
    `observed` 空集合時不判（量不到≠量到零，全文搬 scratchpad/r158/moved_lore_r158_p6.md）。"""
```

### 段落 3：`settings_chain` docstring（原第 696-700 行）

原文：
```
def settings_chain(root: Path | None = None) -> list[Path]:
    """Claude Code settings 檔，**由高優先到低優先**。刻意不含 enterprise policy
    層（讀它也沒意義：只會讓分母更小＝更早喊，方向安全）。誠實劃界：`--settings`
    旗標與 `/model` 的 session 內覆寫本檔看不到，這正是 `window_from_model` 要用
    逐字稿實跑 model 做交叉否決的原因。"""
```
壓縮後：
```
def settings_chain(root: Path | None = None) -> list[Path]:
    """Claude Code settings 檔，由高優先到低優先（不含 enterprise policy 層：讀它
    只會讓分母更小，方向安全）。誠實劃界全文搬 scratchpad/r158/moved_lore_r158_p6.md。"""
```

### 段落 4：`arm_quota_wakeup` docstring（原第 850-854 行）

原文：
```
def arm_quota_wakeup(transcript: Path | None, plan: str) -> dict:
    """額度 95%／`arm` 分支的喚醒武裝；回 `{armed, sentinel_off, posix}` 給訊息用。
    `armed`＝**真的 spawn 出去了**；`posix`＝這台機器沒有排程載具（mac 上為 False）。
    全文（含 R83／W2-A 沿革）逐字保全於 CrossPlatform_DEF200275_Context_Metering_
    Evidence.md〈第七輪 史料搬遷〉節。"""
```
壓縮後：
```
def arm_quota_wakeup(transcript: Path | None, plan: str) -> dict:
    """額度 95%／`arm` 分支的喚醒武裝；回 `{armed, sentinel_off, posix}`（`armed`＝真的
    spawn 出去了；`posix`＝無排程載具）。全文搬 CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第七輪〉節。"""
```
（此段內容原本就已逐字保全於 `CrossPlatform_DEF200275_Context_Metering_Evidence.md`〈第七輪
史料搬遷〉節，此處純壓縮指標措辭，非首次搬遷。）

### 淨額核算（實測，非估算）

- 動工前：`python AutoClaude/tools/check_loc_budget.py` 實測 `context_budget_guard.py: 1087`
  （budget 1089，headroom 2）。
- 新增：session_brief import 區塊 4 行 + main() SessionStart 呼叫 4 行 = +8 行。
- 段落 1~4 壓縮共省若干行；段落 4（`arm_quota_wakeup`）第一版壓成 2 行撞 E501（117>100），
  改回 3 行以符合行寬——實際淨省行數因此比初估少 1 行。
- 收工後實測：`git diff --stat` 顯示 17 insertions / 17 deletions（總行數不變），
  `check_loc_budget.py` 回報 `context_budget_guard.py: 1088`（budget 1089，headroom 1，rc=0）。
  以**這一行實測數字**為準，上面的逐段估算僅供追溯思路，不得引用為事實。

`moved_lore_r158_p2.md` 為 P2 早期草稿已過時，未採用（P2 最終改用 `quota_messages.py`
單一 SSOT，無需搬遷史料）。

## 七、Windows 親驗清單

以下三部分逐字收錄，供 Windows 使用者實機驗證（本輪 mac 單機無法親驗）。

### 7.1 Q1 診斷腳本（`analysis_sa.md` §S2，PowerShell 5.1，全程唯讀）

```powershell
# ============================================================
# R158 Q1 診斷腳本（PowerShell 5.1）——全程唯讀，不改動任何檔案
# ============================================================

# [1] SDD_ACTIVE_VERSION 環境變數
Write-Output "[1] SDD_ACTIVE_VERSION = $env:SDD_ACTIVE_VERSION"
# 若為空／未設：sdd_hook_router.py 休眠 no-op，SDD 的 context_ledger_pre（唯一會 deny 的 hook）不會活。
# 若設了但 != 下面 [2] 查到的磁碟最高版：SessionStart 只印軟告警（_drift_advisory），不擋，但代表這台機器可能還在跑舊版語意的 hook（見 [1a]）。

# [2] 磁碟上實際存在的 AISDLC_SDD 版本目錄（由小到大列出，最後一行是最高版）
Write-Output "[2] 磁碟版本目錄："
Get-ChildItem -Path "$env:CLAUDE_PROJECT_DIR\AISDLC_SDD" -Directory -Filter "AISDLC_SDD_v*" |
    Sort-Object Name |
    Select-Object -ExpandProperty Name
# 若 [1] 的版號落後這裡最後一行：這台機器上真正生效的 context_ledger_pre.py 可能是舊語意
# （v0.23~v0.29：ratio>=95% 寫「專案級」TOKEN_BUDGET_CRITICAL，會讓下一個全新視窗開場就被擋；
#  v0.30 起：改成「session 級」deny，不會有這個殘留問題）。

# [3] FSM 狀態檔：current_state 與 updated_at（本機各自一份，不進 git）
$fsmPath = "$env:CLAUDE_PROJECT_DIR\AISDLC_SDD\AISDLC_SDD_v0.30\build\reports\fsm\FSM-STATE-AISDLC_SDD.yaml"
Write-Output "[3] FSM 狀態檔：$fsmPath"
if (Test-Path $fsmPath) {
    Get-Content -Encoding utf8 $fsmPath | Select-String "current_state|updated_at"
} else {
    Write-Output "    （不存在——這台機器從未寫過 FSM 狀態，不會有殘留阻斷態）"
}
# 若 current_state 屬於 ESCALATION / ESCALATION_FINAL / TERMINATED / TOKEN_BUDGET_CRITICAL 之一：
#   這就是 Q1 的直接根因——assert_tool_allowed() 會擋所有工具，需要人手動跑 resume-from-escalation。
# 若 updated_at 是很舊的日期：代表這是上次 session 遺留、模型自己看不到的陳舊狀態。

# [4] 使用者層 settings 有沒有 statusLine（Q4 對照用）
$settingsPath = "$env:USERPROFILE\.claude\settings.json"
Write-Output "[4] 使用者層 settings：$settingsPath"
if (Test-Path $settingsPath) {
    Get-Content -Encoding utf8 $settingsPath | Select-String "statusLine"
} else {
    Write-Output "    （檔案不存在 => 從未設定過 statusLine）"
}
# 有輸出：Windows 其實裝了 statusLine，Q4「Windows 沒有」需要重新定義成「裝了但不動作」。
# 無輸出：確認 Q4 根因＝從未安裝（非機制壞掉）。

# [5] hook 載具是否存在（fail-open 風險自檢）
$carrier = "$env:CLAUDE_PROJECT_DIR\.venv\Scripts\pythonw.exe"
Write-Output "[5] hook 載具存在=$(Test-Path $carrier)　（路徑：$carrier）"
# False：所有 exec-form hook（含 SDD 的 deny hook、context_budget_guard.py、本腳本要查的
#   lint_powershell_command.py 自己）在這台機器上一律 fail-open——換句話說，若 [5]=False，
#   Q1「被擋」反而更不可能是這些 hook 造成的，因為它們結構上跑不起來（根 CLAUDE.md〈hook 載具〉節）。

# [6] 最近一份逐字稿前 40 則 assistant 訊息是否含「擋」相關字樣
Write-Output "[6] 最近逐字稿掃描："
$latest = Get-ChildItem -Path "$env:USERPROFILE\.claude\projects" -Recurse -Filter "*.jsonl" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($latest) {
    Write-Output "    逐字稿：$($latest.FullName)"
    $lines = Get-Content -Encoding utf8 $latest.FullName -TotalCount 4000
    $checked = 0
    $hit = 0
    foreach ($line in $lines) {
        if ($line -match '"type"\s*:\s*"assistant"') {
            $checked = $checked + 1
            if ($checked -le 40 -and $line -match '擋|blocked|deny|無法寫|無法用工具') {
                $hit = $hit + 1
            }
        }
    }
    Write-Output "    前 40 則 assistant 訊息命中「擋／blocked／deny」次數 = $hit"
} else {
    Write-Output "    （找不到逐字稿檔，需人工確認 ~/.claude/projects 下實際路徑）"
}
# hit > 0：Windows 這台機器上真的重現了「被擋」字樣，且已知是哪一份逐字稿，可回頭比對 [1]~[5]。
# hit = 0：與 mac 現況一致（mac 8 份逐字稿前 40 則皆零命中）。
```

**lint 合規說明**（讀過 `.claude/hooks/lint_powershell_command.py` 後逐條核對）：
- 規則①（管線接 `Select-Object`/`Sort-Object`/`Select-String` 等之後讀 `$LASTEXITCODE`）：本腳本**完全不讀** `$LASTEXITCODE`，不觸發。
- 規則②（裸 `cd`/`Set-Location`/`sl`/`chdir`）：本腳本**全程用絕對路徑，零 `cd`**。
- 規則③（裸 `bash <script>.sh`）：本腳本不呼叫 `bash`，不觸發。

### 7.2 QA 六項親驗清單（`analysis_qa.md` §T6，PowerShell 5.1）

```powershell
# 6.1 Q1 根因排查——FSM 專案級狀態是否卡在阻塞集合
Get-Content -Encoding utf8 (Join-Path $env:CLAUDE_PROJECT_DIR 'AISDLC_SDD\AISDLC_SDD_v0.30\build\reports\fsm\FSM-STATE-AISDLC_SDD.yaml') |
  Select-String 'current_state|project:'
# 預期：current_state 若印出 ESCALATION／ESCALATION_FINAL／TERMINATED／TOKEN_BUDGET_CRITICAL
# 四者之一 ⇒ 這就是 Q1 的直接根因。若印出 SPEC_DRAFTING 等非阻塞態，則需查 6.2/6.3。

# 6.2 SDD_ACTIVE_VERSION 與 hook 是否用舊語意版本
$env:SDD_ACTIVE_VERSION
# 預期：應為 0.30（若空白或指到 v0.23~v0.29，該版 context_ledger_pre.py 仍是「寫入專案級
# TOKEN_BUDGET_CRITICAL」的舊語意——這是本輪最值得懷疑的 Windows 端差異）。

# 6.3 額度閘（quota_gate）是否卡在 halt 帶
python (Join-Path $env:CLAUDE_PROJECT_DIR 'tools\session_resume_planner.py') --pace
# 預期：印出「可派 N 個／cap=.../band=.../最緊的一條＝.../分鐘」。若 band 為 stop／halt 類型
# 且伴隨「額度仍在停止水位：扇出一律不執行」，這是 Q1 的另一個可能根因。

# 6.4 hook 載具是否存在（fail-open 反向風險，順手排查）
Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR '.venv\Scripts\pythonw.exe')
# 預期：True。若 False，代表 hook 體系整體 fail-open。

# 6.5 hook 是否真的在跑（正面現查）
claude -p --model haiku --debug hooks --debug-file h.log "ok"
Select-String -Path h.log -Pattern 'Hook SessionStart.*success'
# 預期：至少一行 success。

# 6.6 Q3／Q4：status line 與 context feed 是否已安裝
Get-Content -Encoding utf8 (Join-Path $env:USERPROFILE '.claude\settings.json') | Select-String 'statusLine'
Test-Path (Join-Path $env:USERPROFILE '.autosdd\context_feed')
# 預期：目前應皆「查無 statusLine／目錄不存在」——這是部署缺口，不是 bug。

python (Join-Path $env:CLAUDE_PROJECT_DIR 'tools\session_resume_planner.py') --check
# 預期：由於無 context feed，harness 那一行應印出「無法讀 feed」而非
# 「harness used=... 逐字稿 used=... 差=0」——這行輸出本身就是 Q3/Q4 根因的機械證據。

# 6.7 F1：Windows 原生重現 test_file_lock.py 間歇性競態
Push-Location (Join-Path $env:CLAUDE_PROJECT_DIR 'AISDLC_SDD\AISDLC_SDD_v0.30')
$env:PYTHONUTF8 = '1'
for ($i = 1; $i -le 20; $i++) {
  python -m pytest tools/fsm_runtime/tests/test_file_lock.py -q
}
Pop-Location
# 預期：多數次 1 passed，少數次可能重現 CI #250 的
# PermissionError: [Errno 13] Permission denied: '...counter.lock'（機率性，CI 近 15 次只中 1 次）。
```

誠實劃界（QA 自述）：6.1/6.2/6.3 三者互斥或並存皆有可能；本 QA 未能在 mac 上重現 Windows
環境的 `SDD_ACTIVE_VERSION` 缺漏或版本落差情境，這是本分析最大的未驗證假設，Windows 親驗前
一律標「待驗證」。

### 7.3 Status line 安裝三步（P5 交付物）

```bash
# 1) 預覽（不寫入任何檔案）
python tools/install_statusline.py --dry-run
# 2) 安裝（只動 ~/.claude/settings.json 的 statusLine 鍵，先備份 settings.json.bak-<UTC時間戳>）
python tools/install_statusline.py
# 3) 開新 claude 視窗，觀察是否出現 ctx 行、有無閃 console 視窗
#    Windows 上若 pythonw.exe 與 sys.executable 同目錄存在則安裝器改用它（GUI 子系統減少閃窗機率，
#    效果待 Windows 親驗，不可宣稱「已解決閃窗」）；閃窗就立即：
python tools/install_statusline.py --uninstall
```

### 7.4 CI #250 Windows 原生重跑指令

```powershell
Push-Location (Join-Path $env:CLAUDE_PROJECT_DIR 'AISDLC_SDD\AISDLC_SDD_v0.30')
$env:PYTHONUTF8 = '1'
for ($i = 1; $i -le 20; $i++) { python -m pytest tools/fsm_runtime/tests/test_file_lock.py -q }
Pop-Location
```
（同 7.2 節 6.7；獨立列出供只想驗 CI #250 這一件事的讀者直接複製。）

### 7.5 FSM-STATE 卡在阻斷態時的一行恢復指令（`recovery_hint.py::recovery_command()`）

兩殼模板（`sdd_root`／`python`／`target`／`reason` 依實際狀態代入；`-m` 是唯一可跑形態，
直跑檔案會因相對 import 而 `ImportError`）：

```bash
# POSIX（bash／zsh）
cd "<sdd_root>" ; "<python>" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --to <target> --reason "<reason>"
```

```powershell
# PowerShell（& 必須緊貼直譯器路徑前，不是整行最前）
Set-Location "<sdd_root>"; & "<python>" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --to <target> --reason "<reason>"
```

🔴 注意：`recovery_command()` 產生的 PowerShell 形態使用 `Set-Location` 帶絕對路徑並加引號——
根 CLAUDE.md 鐵律二字面若被讀成「`lint_powershell_command.py` 只擋帶相對路徑的 `Set-Location`」，
與該 hook 實測「對任何 `Set-Location`（含絕對路徑加引號）皆命中」不符，此缺口已立
DEF-200-340（open，未指派）。

## 八、誠實劃界

- mac 上未重現 Q1「被擋」字樣（8 份逐字稿前 40 則皆零命中）；Windows 端實值需使用者親跑
  〈七、Windows 親驗清單〉後回報。
- Q3「數字不符」：官方文件明文 status line 百分比與 `/context` 因計算時機不同可能不一致，
  非本輪缺陷；mac 三次親跑差=0，Windows 因未裝 statusLine 無法比對。
- Status line 安裝後是否閃 console 視窗**未在 Windows 親驗**；`pythonw.exe` 替換邏輯是否真的
  消除閃窗，效果待證。
- DEF-200-340／341／342 三筆 open：分別待「文件措辭 vs 判準過寬」裁定、Windows 真機重現
  CI #250 後再評估 `_is_stale` 本體是否要改、以及 Windows 端 FSM-STATE 實值佐證「不能寫檔」
  的最精確候選路徑。
- P6 自述新測試「寫出即通過、未先出現失敗態」，本收尾窗口的唯讀性質使其未逐支對 HEAD 版
  重驗，留待下一輪四方複審對抗式覆核（若覆核發現該測試對 HEAD 版本身不轉紅，需追加真正的
  紅端注入）。

## 九、複審登記（四方複審發現，登記不修）

- Architect P2｜`tools/tests/test_sdd_hook_router_r158.py:9`｜`_merge_advisory_into_stdout`
  對真實 v0.30 `session_start.py` 輸出形狀無整合回歸鎖，僅合成 stub 一支端到端測試；未來若
  v0.30 任一成功路徑改為不含字串 `additionalContext`，merge 會靜默退回 stderr 且無測試會紅。
- Architect P3｜`.claude/hooks/context_budget_guard.py:1088`｜special-tier headroom 僅剩 1 行
  （1088/1089），下次任何單行新增即破線。
- Architect P3｜`.claude/hooks/sdd_hook_router.py:196-210`｜BOM／多 JSON 物件併接等 fail-safe
  分支無專屬單元測試，僅靠 `except (json.JSONDecodeError, TypeError)` 兜底。
- SD P3｜`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/session_start.py:379-380`｜`_build_context()`
  用 `if trace:` 包住整段，使 `_decision_trace_staleness_note` 內對空 `trace` 的防禦
  （`(trace or [])[-5:]`）成死碼，無直接單元測試餵 `trace=[]`。
- SD P3｜同檔 `_decision_trace_staleness_note`｜`any(s in reason for s in blocking_states)`
  為自由文字子字串比對，目前 4 個阻斷態名稱獨特風險低，但未來新阻斷態名稱若為常見詞子字串
  會誤判，且無反例測試把關。
- QA P2｜`tools/tests/test_context_budget_guard.py`（`HarnessFeedStageTest` 新增 3 支中 2 支：
  `test_a_cross_check_diff_is_printed_when_both_sides_measure`／
  `test_an_absent_feed_reason_is_not_swallowed`）｜對 HEAD 版 `harness_feed.py` 直接呼叫
  `check_lines()` 也 PASS，屬既有行為回歸鎖而非本輪先紅再綠產物。
- QA P2｜`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_session_start_rules.py::
  test_decision_trace_omits_staleness_note_while_still_blocked`｜同上模式，HEAD sandbox 上
  重跑也 PASS。
- QA P2｜`tools/tests/test_sdd_hook_router_r158.py::test_no_advisory_text_when_active_is_already_latest`
  ｜同上模式，無漂移情境對 HEAD 版 `router.main()` 重跑也 PASS。
- QA P3｜PKG_REPORTS「先紅再綠」敘事｜建議未來 PKG 報告區分「新行為斷言」與「規格完整性斷言」
  兩類測試計數。

## 十、補正 4：本機 smoke 被 .venv 守衛擋下（DEF-200-343）

**事實**：`19f3e75b`（2026-09-19，DEF-200-315「單一 .venv 最後一哩」）把互動式安裝器
（`AutoClaude/tools/install_git_hooks.sh`／`AISDLC_SDD/scripts/install-hooks.sh`／
LATEST `install_post_commit.sh`）改為只認 repo 根層 `.venv` 直譯器，PATH 上的
`python`／`python3` 一律拒收，除非 `CI=true`／`GITHUB_ACTIONS=true` 或人為逃生口
`AUTOSDD_ALLOW_PATH_PYTHON=1`。`tools/macos_smoke_local.sh`／
`tools/windows_smoke_local.ps1` 各自在 OS temp 建的假 repo（`git clone` 而來）天生
沒有 `.venv`，於是這三個安裝器呼叫點在假 repo 內全數被守衛擋下——mac nightly 自
09-20 02:00 起 `[1/4] macos_smoke` 轉紅：`bash tools/macos_smoke_local.sh` 修復前
親跑 `===== 彙總：PASS=10 FAIL=4 SKIP=0 =====` rc=1（紅：[3/7] `install_git_hooks.sh
安裝後 core.hooksPath 未設定`、`install-hooks.sh 安裝後 core.hooksPath 未設定或安裝
失敗（rc=1）`、[4/7] `install_post_commit.sh 於 worktree 執行失敗（rc=1）`、[7/7]
`PASS 總數 10 低於下限 13`）。CI 因 workflow 內建 `GITHUB_ACTIONS=true` 走逃生口，
未受影響；本輪（R158 六包）未動任何安裝器與 smoke 腳本，純屬 19f3e75b 的連帶。

**修法**：假 repo 本來就沒有 `.venv`，`AUTOSDD_ALLOW_PATH_PYTHON=1` 是
`tools/lib/windowsapps_guard.sh`／`tools/lib/WindowsAppsGuard.ps1` 文件明寫的人為
逃生口，不是繞過守衛——smoke 驗的是安裝器 hooksPath 往返邏輯，不是 `.venv`
存在性。`tools/macos_smoke_local.sh` 於 3a（`install_git_hooks.sh` 往返）、3c
（`install-hooks.sh` 往返）、[4/7]（LATEST `install_post_commit.sh` worktree 實跑）
三處子 shell 內加 `export AUTOSDD_ALLOW_PATH_PYTHON=1`（僅該子 shell 範圍內生效，
不外洩到 [5/7] 等唯讀段）；`tools/windows_smoke_local.ps1` 同型，於共用函式
`Test-InstallRoundtrip`（[2/9]/[4/9]a/[6/9] 三處呼叫共用同一函式體）與 [5/9]
（`install_post_commit.ps1` worktree 實跑）內以 `$env:AUTOSDD_ALLOW_PATH_PYTHON =
'1'` 包住安裝器呼叫、`finally` 區塊還原舊值（`Remove-Item Env:` 或設回）。3b/3d/
[3/9]/[4/9]b（linked worktree 拒絕測試）未動——這些子 shell 本輪未觀察到失敗
（守衛 rc=1 恰與「worktree 應拒絕」期望值巧合一致），裁決範圍僅涵蓋 FACTS 記錄
為紅的三個「往返」呼叫點。

**mac 實測前後彙總行**：
- 修復前：`===== 彙總：PASS=10 FAIL=4 SKIP=0 =====` rc=1
- 修復後：`===== 彙總：PASS=13 FAIL=0 SKIP=0 =====` rc=0（`bash tools/macos_smoke_local.sh` 全程親跑，[1/7]~[7/7] 全數 PASS）

**Windows 待親驗**：`tools/windows_smoke_local.ps1` 本輪僅完成靜態合規（`ruff` 不管
`.ps1`；`cd tools/tests && python -m unittest test_ps51_compat
test_platform_neutral_paths -q` 已於本機 mac 對 `.ps1` 檔掃描過 OK），主控在 mac
上無法實跑 PowerShell 腳本本體，Windows 側 `PASS=13/13` 待 Windows 親驗補上。
