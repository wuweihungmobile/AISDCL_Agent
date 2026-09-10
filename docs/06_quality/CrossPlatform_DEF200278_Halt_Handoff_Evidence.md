# DEF-200-278 證據檔：喚醒鏈缺口（halt 交棒斷裂＋哨兵不認自願停機）

> 本檔為 `docs/06_quality/AutoSDD_Defect_Log.md` 該列的體積守門接收端；列上只留一句話與
> 本檔指針，逐字原文住這裡。任務書＝ `WAKE_CHAIN_FIX.md`（掌舵者原話：「Token 用盡時，
> 為何沒有啟動下一個 Reset 的喚醒機制，不需要人類介入」）。

## §1 現場證據（掌舵者 2026-09-10 23:11 直接發現；逐字保留自任務書）

| 證據 | 值 | 座標 |
|---|---|---|
| 哨兵 launchd 工作 | 存在、`runs=20`、`last exit code=0`、`run interval=900`、**無 StartCalendarInterval** | `launchctl print gui/501/AutoSDD_Sentinel_8d8773f9-…` |
| 哨兵每次巡邏判定 | `{"action":"patrol","reason":"無未處理撞線；逐字稿 Ns 前仍有更新 ⇒ session 還活著，續巡"}`（22:17／22:32／22:47／23:02 四筆逐字相同） | `autosdd_resume_log_*.jsonl`（151 行） |
| 任務書 relay | `state=waiting, reset_at=18:00:00（停在上一次 reset）, next_run_time="", attempts=0` | `~/.autosdd/plans/autosdd_resume_plan_*.md` |
| 守衛 halt 當下的訊息 | `任務書：（寫不出來——逐字稿路徑不可得）… 這次沒有武裝：拿不到逐字稿路徑` | 本 session 逐字稿 PostToolUse(Bash) hook 輸出（19:1x） |
| 哨兵額度量測 | `quota_band: unmeasured`（閒置期間快取過期） | `quota_gate.py::read_quota` |

損失 ≈ 3 小時 50 分（22:59 reset 到 23:11 使用者親自回來為止零續跑）。

## §2 三層根因（本輪皆有本場直接重現，非推測）

### RC-1（守衛側）：halt 交棒 best-effort，多種成因收斂成同一句籠統訊息

本場重現腳本（`repro_rc1.py`，輸出逐字附下）證明**兩種完全不同的成因**修前得到
**逐字相同**的訊息：

**情境一：`payload` 沒有 `transcript_path`**
```
--- act (no transcript_path) ---
{'branch': 'arm', 'plan': '', 'armed': False, ..., 'sentinel_off': False, 'posix': False, 'kind': 'session'}

--- rendered message ---
🔴 額度到達**停止**水位（最緊的一條＝session）⇒ **停止派發**：...
   任務書：（寫不出來——逐字稿路徑不可得）
   ⚠️ 這一條的 reset 近在眼前、本來該武裝喚醒，但**這次沒有武裝**：拿不到逐字稿路徑 ⇒ 沒有可以掛的任務書。
```

**情境二：`transcript_path` 存在且檔案可讀，只是 `plan_writer`（`write_resume_plan`）本身失敗**
```
--- act (transcript 有效但 plan_writer 失敗) ---
{'branch': 'arm', 'plan': '', 'armed': False, ..., 'sentinel_off': False, 'posix': False, 'kind': 'session'}

（渲染輸出與情境一逐字相同——包含「拿不到逐字稿路徑」，即使逐字稿其實存在）
```

追根究柢：`quota_halt_actions()` 的 `plan = plan_writer(transcript) if transcript and
transcript.is_file() else ""`——只要 `plan` 是空字串，不論是「沒有 transcript」還是
「plan_writer 執行失敗」，`quota_messages.quota_halt_message()` 都印同一句硬編碼的
「拿不到逐字稿路徑」。而且 halt 那一刻**沒有任何持久標記**留在磁碟——哨兵下一次巡邏
（900s 之後）讀不到任何「這個 session 剛剛 halt 過、reset 在 T」的機器可讀狀態。

### RC-2（哨兵側）：`sentinel_decide()` 只認逐字稿裡的未復原撞線（429），不認自願停機

`tools/session_resume_planner.py::sentinel_decide()`（修前）五分支的第一支只問
`event`（`guard.unhandled_limit_event(transcript)` 的結果，即逐字稿裡有沒有一則
「你已撞到限制」的 API 回應）。主控**自願**停機（quota_gate 判 `band=halt` 後結束
回合）不會在逐字稿留下這種事件 ⇒ `event=None` ⇒ 直接落到
`idle_seconds < SENTINEL_IDLE_SECONDS(6h)` 的 `patrol` 分支，永遠續巡到 6 小時後才
`disarm`（靜默解除，不叫人也不續跑）。

### RC-3（協定側）：宣稱先於憑證

主控收尾訊息寫「重置後會自動續跑：您的終端有 auto-continue，加上 launchd 哨兵」——
(a) harness 的 auto-continue 只在主控自己的 API 呼叫吃到 429 時發生，自願停機沒有；
(b) `launchctl list` 有 1 筆只證明**巡邏**存在，relay 的 `next_run_time` 是空的、
`reset_at` 是舊的。`check_claim_provenance.py` 修前的詞表收不到「自動續跑」「會自動
繼續」這一族說法，故這句宣稱不會被本場既有的 Stop hook 攔下來提醒。

## §3 修法（逐檔；INV-H1／H2／H4，INV-H3 見 §7）

| 不變式 | 檔案 | 內容 |
|---|---|---|
| INV-H1a | `tools/lib/quota_gate.py::resolve_halt_transcript()` | payload 缺 `transcript_path`（或給的路徑讀不到檔）時，以 `CLAUDE_CODE_SESSION_ID`＋`probe.audit_session.project_transcript_dir()`（唯一實作，複用不新抄）還原路徑；仍失敗回 `(None, "unavailable")` |
| INV-H1c | `quota_gate.py::halt_marker_path/write_halt_marker/read_halt_marker` | 落一份持久標記 `~/.autosdd/traces/halt_<sid>.json`（`endurance_env.trace_dir()` SSOT），內容＝`{sid, band, binding, reset_at, at, transcript, resolved_source}` |
| INV-H1e | `quota_gate.py::quota_halt_actions()` | `not_armed_reason` 依實際成因分流（逐字稿不可得／`plan_writer` 失敗／spawn 失敗三選一），不再永遠印同一句話；`quota_messages.py::quota_halt_message()` 改讀這個新欄位（缺席時仍保留舊文案，向下相容既有測試字面斷言） |
| INV-H2 | `tools/lib/quota_messages.py::halt_verdict()` | 純函式：halt 標記 → `arm_reset`／`probe`／`escalate`（與既有 429 分支重用完全相同的 3 個 action 字面，不新增第 6 個）。「最新活動晚於標記」（`now - idle_seconds > marker_at`）⇒ 回 `None`＝標記過期，避免哨兵永遠卡在 `probe` |
| INV-H2 接線 | `tools/session_resume_planner.py::sentinel_decide()` | 新增可選參數 `halt`；429 事件分支優先，其次是 `quota_gate.halt_verdict(halt, idle_seconds, now)`，最後才落回既有 idle patrol/disarm；`_sentinel_tick()` 讀 `state["session_id"]` 對應的標記並傳入 |
| INV-H4 | `.claude/hooks/check_claim_provenance.py::NAKED_VERDICT_RE` | 詞表加入「自動續跑」「會自動繼續」，沿用既有 `NAKED_MIN_TOKENS=2` 疊字機制與零佐證（`tool_output` 全空）判準 |

### LOC 棘輪核算（避免下一個人重跑就撞棘輪）

- `tools/lib/quota_gate.py`：493/500（`guardrail_hub` tier）。`halt_verdict()`／
  `HALT_RESET_SKEW_SECONDS` 移到 `quota_messages.py`（155/400）以騰出空間，
  `quota_gate.py` 端只 re-export。
- `tools/session_resume_planner.py`：750/750（`guardrail_cli` tier，ABSOLUTE_LIMIT=750，
  **零餘裕**）——`sentinel_decide()` 只加 2 行（呼叫＋return）＋签名一個新參數，
  `_sentinel_tick()` 只加 1 行讀標記；真正的判讀邏輯全數放在 `quota_messages.py`。
- `.claude/hooks/check_claim_provenance.py`：344/750，餘裕充足，僅加 2 個字面＋WHY 註解。

## §4 先紅後綠（本場實跑輸出）

新增測試檔：`tools/tests/test_wake_chain_halt_r278.py`（18 個 test）。修碼前（红端）：

```
$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q
FAILED ...ResolveHaltTranscriptTest::test_missing_payload_falls_back_to_env_derived_slug
FAILED ...ResolveHaltTranscriptTest::test_nothing_resolvable_says_so_honestly
FAILED ...ResolveHaltTranscriptTest::test_payload_present_and_readable_wins
FAILED ...HaltMarkerRoundTripTest::test_unknown_sid_reads_back_none
FAILED ...HaltMarkerRoundTripTest::test_written_marker_reads_back_verbatim
FAILED ...QuotaHaltActionsWritesMarkerAndNamesTheRealReasonTest::test_no_transcript_anywhere_writes_marker_and_names_the_cause
FAILED ...QuotaHaltActionsWritesMarkerAndNamesTheRealReasonTest::test_plan_writer_failure_gets_its_own_reason_not_a_generic_one
FAILED ...HaltVerdictTest::test_activity_after_the_marker_means_it_is_stale
FAILED ...HaltVerdictTest::test_future_reset_arms_at_reset_plus_skew
FAILED ...HaltVerdictTest::test_no_marker_defers_to_caller
FAILED ...HaltVerdictTest::test_passed_reset_probes_instead_of_patrolling
FAILED ...HaltVerdictTest::test_unparseable_reset_escalates_rather_than_guessing
FAILED ...SentinelDecideRecognizesHaltMarkerTest::test_halt_marker_beats_the_idle_patrol_branch
FAILED ...SentinelDecideRecognizesHaltMarkerTest::test_real_unhandled_429_event_still_wins_over_halt_marker
FAILED ...SentinelDecideRecognizesHaltMarkerTest::test_stale_halt_marker_falls_back_to_existing_idle_logic
15 failed, 1 passed in 0.15s
```

（`ClaimGuardCatchesAutoContinueWithoutCredentialTest` 兩支獨立確認：詞表加入前
`assertRegex` 對「自動續跑」「會自動繼續」不匹配、`naked_verdict_hits()` 對疊字句回 `[]`。）

修碼後（綠端）：

```
$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q
..................                                                     [100%]
18 passed, 2 subtests passed in 0.11s
```

## §5 憑證實跑（真 launchd，假 sid `wakechain-selftest-1789055180`）

```
arm rc: 0
credential: launchd gui/501/wakechain-selftest-1789055180｜launchctl print rc=0（不存在時是 113）｜
run interval = 900 seconds〔launchd 回讀，與請求相符〕｜argv 回讀 7 項與請求逐項相符｜
plist = /Users/wuweihong/Library/LaunchAgents/wakechain-selftest-1789055180.plist〔launchd 自報，證明已持久化〕｜
StartCalendarInterval = Month=9-Day=11-Hour=0-Minute=17〔launchd 自報的 descriptor，證明那個時刻真的排進去了〕｜
電源姿態＝各電源段 sleep 皆為 0（pmset 現查；這台機器的現況，不是本專案的保證）｜state = not running

--- launchctl print gui/501/wakechain-selftest-1789055180 ---
rc= 0
gui/501/wakechain-selftest-1789055180 = {
	...
	event triggers = {
		wakechain-selftest-1789055180.268435480 => {
			keepalive = 0
			service = wakechain-selftest-1789055180
			stream = com.apple.launchd.calendarinterval
			monitor = com.apple.UserEventAgent-Aqua
			descriptor = {
				"Minute" => 17
				"Hour" => 0
				"Day" => 11
				"Month" => 9
			}
		}
	}
	...
	run interval = 900 seconds
}

--- cleanup ---
plist removed: True
post-bootout launchctl print rc= 113 (113=不存在，預期值)
```

`StartCalendarInterval`（表現為 `event triggers` 底下 `stream =
com.apple.launchd.calendarinterval` ＋ `descriptor = {Minute/Hour/Day/Month}`）確實
被 launchd 收下並回讀，證明「reset+skew 那個時刻真的被排進去」這件事在真實載具上成立，
不只是判讀層的純函式回傳值。收尾 `launchctl bootout` 後 `launchctl print` rc=113
（不存在），確認沒有殘留。

## §6 把握程度

- **INV-H1／H2 已在真實載具與純函式兩層驗證**：純函式層（`halt_verdict`／
  `resolve_halt_transcript`／marker 讀寫）18 個 test 全綠；載具層（真 launchd
  `StartCalendarInterval` 排程）用假 sid 實跑並取得憑證（§5）。
- **端到端的「哨兵真的在下一輪巡邏時讀到標記並轉 `arm_reset`」未跑過完整
  `_sentinel_tick()` 的真實 subprocess 一輪**（那需要真的等待或 mock 排程器回呼），
  本輪只驗證了 `sentinel_decide(event, "", idle, now, halt=marker)` 這個純函式介面；
  `_sentinel_tick()` 讀取標記那一行（`quota_gate.read_halt_marker(state.get("session_id")
  or "")`）本身未被獨立測試覆蓋（風險：`state` 缺 `session_id` 鍵時的降級路徑）。
- **INV-H3（閒置期間主動刷新額度快取）未實作**——經檢視，本輪的 `arm_reset`／`probe`
  判定完全不依賴 `quota_gate.read_quota()`／measurability（`halt_verdict()` 純粹比較
  時間戳），故「不因 unmeasured 而不動」這個核心正確性要求**結構上已經滿足**（判讀根本
  不看額度是否量得到）。「主動補量一次讓 `--pace` 等其他消費端也不顯示 unmeasured」
  是可觀測性層面的加分項，本輪因 LOC 預算與時間限制未做，留待下一輪。
- **Windows 側未實機**：`sentinel_decide()`／`halt_verdict()` 皆為純函式，Windows／mac
  行為理論上一致（無平台分支），但 schtasks 載具的真實排程未在本輪驗證（§5 只測了
  launchd）。
- 睡著的 Mac 不會被喚醒是已知邊界（見根 CLAUDE.md〈mac 已知邊界〉），本輪不處理。

## §7 未做事項（誠實列出，供下一輪接手）

1. INV-H3：閒置期間允許 `quota_gate` 補量一次（零 model token 的 usage 端點），
   讓 `--pace`／`--check` 在 halt 期間不再顯示 `quota_band: unmeasured`。
2. `_sentinel_tick()` 讀取 halt 標記那一行缺獨立單元測試（`state` 無 `session_id` 時的
   降級路徑）。
3. Windows schtasks 載具的真實憑證實跑（本輪只測了 launchd／macOS）。
4. 端到端「_sentinel_tick 真的跑一輪、標記真的被消費」的 subprocess 級測試（本輪只測
   到 `sentinel_decide()` 這個純函式邊界）。
