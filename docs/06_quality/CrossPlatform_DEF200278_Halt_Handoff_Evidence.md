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

## 第二輪（2026-09-11；DEF-200-281 自願停機喚醒鏈斷裂）

### 觸發（掌舵者原話逐字）

「Token 用盡時，為何沒有啟動下一個 Reset 的喚醒機制，不需要人類介入，這樣才符合開發自動化！」

### §1 現場證據（本輪）

| 證據 | 值 |
|---|---|
| 自願停機時刻 | 03:25 |
| halt 標記 `at`/`reset_at` | 皆為 `2026-08-09`（一個月前，非本次停機時刻） |
| 哨兵巡邏次數 | 28 次 patrol，全數 `"action":"patrol"`（未曾轉 `arm_reset`／`probe`） |
| relay 任務書 | `reset_at`／`next_run_time` 皆空 |
| 一次性喚醒 job | 無（`launchctl`／schtasks 皆未見任何一次性排程） |
| 續跑損失 | 5 小時 40 分鐘零續跑（直到使用者親自回來） |

### §2 RC-1～RC-5（座標＋證據）

#### RC-1：halt 標記 `at`/`reset_at` 為何寫入 2026-08-09（一個月前）——**測試夾具洩漏**

**根因**：`tools/tests/test_quota_policy.py`（修前）`NOW = datetime(2026, 8, 9, 5, 15, 3, tzinfo=UTC)` 是
「刻意固定、不隨掛鐘漂移」的判準常數；`TestR95HaltArmsOffTheEarliestResettableAxis::test_the_halt_actions_and_message_follow_the_choice`
用這個 `NOW` 呼叫**生產函式** `quota_gate.quota_halt_actions({"transcript_path": ""}, d, NOW, ...)`。
`payload["transcript_path"]=""` 觸發 `resolve_halt_transcript()` 的 env-derived 分支（讀
`CLAUDE_CODE_SESSION_ID`＋`CLAUDE_PROJECT_DIR`）；該測試**未隔離**這兩個環境變數，也未設
`AUTOSDD_TRACE_DIR`——在任何真實 Claude Code session 裡跑 pytest，這兩個變數就是**真實、活著的**
session id 與專案根，`project_transcript_dir(root)/f"{sid}.jsonl"` 會解析到**真的存在**的逐字稿檔
（`cand.is_file()` 為 True），於是 `write_halt_marker()` 把凍結的 `NOW` 寫進**真實**
`~/.autosdd/traces/halt_<真實 sid>.json`。

**本場證據**：現場三份污染標記逐位元組相同：`~/.autosdd/traces/halt_{96d7f386-…,8d8773f9-…,unknown}.json`，
皆為 `{"at": "2026-08-09T05:15:03+00:00", "reset_at": "2026-08-09T08:23:03+00:00", "resolved_source": "env-derived", ...}`。
本機重現（沙箱化 `CLAUDE_CODE_SESSION_ID`／`CLAUDE_PROJECT_DIR`／`AUTOSDD_TRACE_DIR` 指向假 sid
`repro-rc1-fakesid-0001`，複製該測試逐字呼叫）：輸出 marker 內容與現場三份**逐位元組吻合**（除 sid 外）。

**排除的候選假說**：非預設參數常數（`quota_halt_actions()` 的 `now` 是必要參數，無預設值）；非快取
`measured_at` 過期照用（`at`/`reset_at` 由呼叫端傳入的 `now`／`decision` 計算，不讀 `quota_cache_path()`）——
確認就是「呼叫端傳入了一個凍結常數」。

#### RC-2：`sentinel_decide()` 為何沒吃到標記——**標記本身合法過期規則，但輸入被 RC-1 污染**

`tools/lib/quota_messages.py::halt_verdict()`「最新活動晚於標記 ⇒ None」規則本身正確（設計意圖：
session 已自行續跑時標記過期，避免哨兵永遠卡 `probe`）。用本場真實標記＋真實 `(now, idle_seconds)`
三筆重放（取自 `autosdd_resume_log_autosdd_resume_plan_96d7f386-….jsonl`）：

```
marker = {"at": "2026-08-09T05:15:03+00:00", "reset_at": "2026-08-09T08:23:03+00:00", ...}
now=2026-09-11T02:17:13+08:00 idle=618.7  -> halt_verdict=None
now=2026-09-11T09:02:21+08:00 idle=19318.0 -> halt_verdict=None
now=2026-09-11T09:17:21+08:00 idle=270.8  -> halt_verdict=None
```

三筆皆 `None`（因 `now - idle_seconds` 遠晚於 08-09 的 `marker_at`）⇒ 落回 idle-patrol，逐字對應觀測到的
`"action":"patrol","reason":"...session 還活著，續巡"`。**結論**：`halt_verdict()` 的過期判準本身無誤，
是被 RC-1 污染的輸入（一個月前的 `at`）觸發了它——這正是它「該」判過期的資料，只是這份資料不該存在。

#### RC-3：停機當下為何沒排出一次性喚醒——latch 抑制＋RC-1 污染疊加

`tools/lib/quota_gate.py::quota_gate()` 的 halt 分支：`key = f"halt@{decision.binding.kind}@{str(halt_resets_at(decision))[:16]}"`；
`quota_latch_path()` 回 `Path(tempfile.gettempdir())/QUOTA_LATCH_NAME`——**machine-wide、非
session-scoped**。本場真實 latch 檔含 `"halt@five_hour@2026-09-10T19:59"`，恰為本次真實 reset 視窗的鍵。
03:25 那次 halt 因此落入「已閂鎖」分支：只印「額度仍在停止水位：扇出一律不執行，任務書已在磁碟上。」，
**不再呼叫** `quota_halt_actions()`——不寫新標記、不重新嘗試 arm。「誰先閂上」不可考（latch 不記
session），但無論是本 session 較早一次 tool call 已合法閂上（隨後被 RC-1 的測試污染覆寫），或另一
session 搶先閂上，結局相同：本 session 沒有拿到一份新鮮、未過期的標記。**本輪判定**：latch 的
machine-wide 範圍是與 RC-1 疊加、而非獨立主因的結構性風險（見〈未做到〉）。

#### RC-4：`quota_band: unmeasured` 之後為何不再花一次探測——**症狀非獨立缺口**

`sentinel_decide()` 唯一會觸發真額度探測（`probe`→`_resume_tick`）的路徑：①逐字稿有未處理 429、
②`halt_verdict()` 回 `{"action":"probe",...}`（reset 已過）。`quota_band` 只是
`patrol_housekeeping()` 附帶寫入 log 的**診斷欄位**，不是 `sentinel_decide()` 的決策輸入。RC-1
污染標記使 `halt_verdict()` 恆回 `None`，於是永遠落 idle-patrol，`quota_band` 才會一路 `unmeasured`
到底。本輪 F-1 修復後，`halt_verdict()` 一旦拿到有效標記即可正確轉 `probe`（見下方端到端演練：
真實 09:48:16 tick 顯示 `"action":"probe"` 且 `"quota_open":true`——探測**確實**零 token 命中 L0
端點）。**結論**：RC-4 不是獨立缺口，是 RC-1/RC-2 的下游症狀，已隨 F-1 解除。

#### RC-5：「逐字稿仍有更新 ⇒ session 還活著」是否結構上必然誤判——**本次事故並非如此（訂正先前誤判）**

初次用 grep 掃描 `autosdd_resume_log_...jsonl` 得到看似的鋸齒狀 idle_seconds（742/1642/2543 循環），
一度懷疑「背景寫手週期性製造假活性」；**用 `json.loads` 逐行結構化重讀後訂正**：真實序列
`idle_seconds` 從 03:47:14 的 411s **單調遞增**到 09:02:21 的 19318s（≈5.37h，未達
`SENTINEL_IDLE_SECONDS=6h` 門檻），09:17 才因真實活動（本鑑識代理與使用者回歸）重置——先前的鋸齒是
grep 對長 `credential` 欄位子字串誤配對造成的假象，**非真實現象**（依 Rule 12／專案「機械輸出逐字貼」
紀律訂正，不隱藏此前誤判）。活性判準本身在本案**正確**運作（idle 確實正確地單調增長），並非「結構上
必然判活著」。**真正的結構性缺口**在別處：idle-patrol 分支只有兩個終態——`< 6h` 續巡 或 `≥ 6h` 靜默
`disarm`——**兩者都不是真的喚醒**；唯一能產生真喚醒（`arm_reset`/`probe`）的路徑是 `halt_verdict()`，
故全案的唯一負載都壓在「halt 標記是否可信」這一件事上，這正是 RC-1 打中的靶心。

### §3 F-1～F-5（修法逐檔）

**F-1（halt 標記寫入前自檢）**：`tools/lib/quota_messages.py` 新增
`HALT_MARKER_MAX_CLOCK_SKEW_SECONDS = 600` ＋ `halt_marker_or_rejection(sid, decision, now, transcript, source, real_now=None)`——
`real_now` 預設抓真牆鐘，與被檢查的 `now` 比較：`|real_now - now| > 600s` 或 `reset_at < real_now` ⇒
回 `(None, 拒寫理由)`；否則回 `(標記 dict, None)`。`tools/lib/quota_gate.py::quota_halt_actions()`
呼叫端改用上述函式；`marker is None` 時不寫檔、印拒寫理由；回傳字典新增 `"marker_rejected"` 稽核欄。

**F-2（`relay_problems()` 缺 `"halt-marker"` 白名單，端到端演練揪出）**：
`tools/session_resume_planner.py::relay_problems()` 的 `reset_source` 允許值元組由
`("transcript-verbatim", "probe-verbatim", "operator")` 擴為 `(..., "halt-marker")`。修前：每次靠
halt 標記完成的 `arm_reset` 循環，下一輪 tick 讀回狀態塊時會被本判準誤判「猜出來的 reset」，觸發不
必要的 `_heal_relay()` 自癒；自癒用當下呼叫的 argv 重建 `_base_state()`，而排程作業的 argv 從不帶
`--no-allow-resume`，於是操作者原先設定的 `allow_resume=False` 會被**靜默重置**成預設值
`True`——這是一個真實的安全缺口（操作者明確要求「不要自動續跑」，卻被自癒悄悄推翻）。

**F-3（未武裝時印出真實成因）**：既有三種 `not_armed_reason`（逐字稿不可得／plan_writer 失敗／spawn
失敗）之外，F-1 新增第四種輸出面：`act["marker_rejected"]`（自檢拒寫的理由，獨立於
`not_armed_reason`，因為「標記沒寫成」與「喚醒沒武裝成」是兩件可能同時或分別發生的事）。

**F-4（端到端演練）**：見下方〈端到端演練逐字〉。

**F-5（hook 不崩驗證）**：`echo '{"hook_event_name":"PostToolUse","tool_name":"Read","transcript_path":"/nonexistent.jsonl"}' | python .claude/hooks/context_budget_guard.py` → rc=0（隔離
`AUTOSDD_TRACE_DIR`／`AUTOSDD_SENTINEL_OFF=1`）；另補 `SessionStart`／`PreToolUse×Agent` 兩型
payload，皆 rc=0，均無 traceback。

### §4 紅→綠逐字

`HaltMarkerSelfCheckTest`（4 支，先紅後綠）：

```
$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q -k HaltMarkerSelfCheckTest
FAILED ...test_fresh_now_and_future_reset_is_accepted_and_written - KeyError: 'marker_rejected'
FAILED ...test_frozen_now_a_month_stale_is_rejected_and_not_written - KeyError: 'marker_rejected'
FAILED ...test_reset_at_in_the_past_is_rejected_even_when_now_is_fresh - AttributeError: module 'quota_gate' has no attribute 'halt_marker_or_rejection'
FAILED ...test_skew_boundary_is_exactly_the_documented_threshold - AttributeError: module 'quota_messages' has no attribute 'HALT_MARKER_MAX_CLOCK_SKEW_SECONDS'
4 failed, 18 deselected in 0.14s

$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q
......................                                                 [100%]
22 passed, 2 subtests passed in 0.11s
```

`test_halt_marker_reset_source_passes_the_relay_credential_check`（relay_problems 白名單）：

```
$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q -k test_halt_marker_reset_source_passes_the_relay_credential_check
FAILED ...: AssertionError: Lists differ: ["reset_source='halt-marker' 不是觀測值 ⇒ 不准用來武裝（猜出來的時刻會讓它醒在錯的時間）"] != []
1 failed, 22 deselected in 0.11s

$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q
.......................                                                [100%]
23 passed, 2 subtests passed in 0.11s
```

`test_quota_policy.py`（隔離修復＋整檔回歸）：

```
$ python -m pytest test_quota_policy.py -q -k TestR95HaltArmsOffTheEarliestResettableAxis
.....                                                                    [100%]
5 passed, 256 deselected in 0.13s
$ python -m pytest test_quota_policy.py -q
261 passed, 394 subtests passed in 3.51s   rc=0
```

`test_context_budget_guard.py`（回歸）：

```
$ python -m pytest test_context_budget_guard.py -q
633 passed, 10 skipped, 228 subtests passed in 27.38s（rc=0；含 test_wake_chain_halt_r278.py 合併跑）
```

### §5 端到端演練逐字（真 launchd；假 sid `wakechain-selftest-1789091039`）

**憑證實跑（BEFORE）**：`launchctl list | grep AutoSDD_` → 僅兩支真實哨兵
```
-	0	AutoSDD_Sentinel_8d8773f9-efc9-4513-be65-d48ca316d114
-	0	AutoSDD_Sentinel_96d7f386-8130-4a3b-9b89-4b26aae7d1f9
```

**安全前提（避免真燒額度）**：①`probe_quota()` 的 L0 零成本端點當下真的回 `open=True`（讀快取，
零 API 呼叫）；②使用假 sid（非真 UUID），若 `allow_resume` 環節仍嘗試 `claude -p --resume <fake-sid>`，
CLI 會在發出任何模型呼叫前因參數不合法拒絕。

**準備**：寫入合成 halt 標記（`reset_at = now+90s`，真實時鐘 `2026-09-11T09:44:12+08:00` →
`reset_at=09:45:42+08:00`）；`python tools/session_resume_planner.py --arm-sentinel --transcript <path> --no-allow-resume` → rc=0：
```
✅ 排程憑證：launchd gui/501/AutoSDD_Sentinel_wakechain-selftest-1789091039｜launchctl print rc=0｜run interval = 900 seconds｜argv 回讀 7 項與請求逐項相符｜plist = /Users/wuweihong/Library/LaunchAgents/AutoSDD_Sentinel_wakechain-selftest-1789091039.plist｜state = not running
```

**tick #1**（`launchctl kickstart -k`，09:44:45 CST）：
```
{"event": "sentinel_woken", "at": "2026-09-11T09:44:46+08:00"}
{"action": "arm_reset", "reason": "偵測到自願 halt 標記；觀測 reset=2026-09-11 09:45:42.146471+08:00 尚未到 ⇒ 要求排程器改在那個時刻醒（本次零 token）", "controller_idle_seconds": 2686.02, "quota_band": "notice", "event": "sentinel_decided"}
{"action": "arm_reset", "fire_at": "2026-09-11T09:47:42.146471+08:00", "credential": "launchd gui/501/...state = running", "event": "sentinel_rearmed"}
```
⇒ **F-2 現場證明**：halt 標記正確壓過 idle-patrol（idle=2686s 遠小於 6h 門檻，仍走 arm_reset），且真
launchd 憑證顯示重掛成功（`fire_at = reset_at(09:45:42) + HALT_RESET_SKEW_SECONDS(120s) = 09:47:42`，
精確吻合）。

（真實等待至 09:48:05，Monitor/until-loop 阻塞式等待，非人工介入）

**tick #2**（09:48:16 CST）：
```
{"event": "sentinel_woken"}
{"why": "reset_source='halt-marker' 不是觀測值 ⇒ 不准用來武裝", "event": "sentinel_selfhealed"}   ← 修前的整合缺口現場（見 F-2）
{"action": "probe", "reason": "...觀測 reset=...已過 ⇒ 花一次探測確認額度回來了沒", "event": "sentinel_decided"}
{"event": "woken"}
{"rc": 0, "kind": "none", "quota_open": true, "source": "endpoint", "text": "endpoint@...: 7 軸皆 <100%...", "event": "probed"}   ← 零 token L0 探測，確認安全
{"strategy": "SESSION_RESUME", "event": "route_chosen"}
{"rc": 1, "err": "Error: --resume requires a valid session ID or session title...Provided value \"wakechain-selftest-1789091039\" is not a UUID...", "event": "resumed"}   ← CLI 參數層級拒絕，未觸及任何模型呼叫，零額外 token
{"why": "no_progress", "event": "relay_stopped"}
{"event": "sentinel_armed"}   ← 因 resume 失敗，relay_machine 掛回巡邏
```
⇒ 完整鏈路 `arm_reset → probe（零 token）→ resume 嘗試（安全失敗，未燒額度）` 全部由**真 launchd
排程觸發、真 quota_gate/session_resume_planner 生產程式碼**執行，過程 0 次真實模型 API 呼叫。

**收尾（AFTER）**：
```
$ launchctl bootout gui/501/AutoSDD_Sentinel_wakechain-selftest-1789091039   # rc=0
$ launchctl print gui/501/AutoSDD_Sentinel_wakechain-selftest-1789091039    # rc=113（不存在，預期值）
$ launchctl list | grep AutoSDD_
-	0	AutoSDD_Sentinel_8d8773f9-efc9-4513-be65-d48ca316d114
-	0	AutoSDD_Sentinel_96d7f386-8130-4a3b-9b89-4b26aae7d1f9
```
BEFORE／AFTER 完全一致，未動到兩支真實哨兵。

### §6 第二修復包（Dev-D，2026-09-11）：RC-3 per-sid 閂鎖＋naive-now 拒寫

複審（唯讀）對第一包 APPROVE，點名兩項必修：RC-3（halt 閂鎖鍵未含 sid ⇒ 同一 reset 視窗內第二個撞
halt 的 session 被第一個機器級閂鎖誤擋，永遠拿不到自己的 halt 標記）；naive-now 防呆
（`halt_marker_or_rejection()` 對 naive `now` 會拋 `TypeError` 崩掉整條武裝路徑）。

**naive-now**（`quota_messages.py::halt_marker_or_rejection()`）：函式開頭加
`if now.tzinfo is None: return None, f"now={now!r} 缺 tzinfo（naive）⇒ 無法安全比對牆鐘，拒絕落盤"`
（2 行）。方向選擇：**拒寫而非猜時區補 tzinfo**——猜錯時區會讓 `at`/`reset_at` 全錯，落一份看起來
合法、實則讓 `halt_verdict()` 永遠判過期（或提早失效）的標記，與 RC-1 本輪事故同型；拒寫的代價只是
「漏一次武裝機會」，回落既有 idle-patrol 安全網，方向明顯更安全。

**RC-3**（`quota_gate.py::quota_gate()` halt 分支）：閂鎖鍵從
`f"halt@{decision.binding.kind}@{str(halt_resets_at(decision))[:16]}"` 改為先解析
`transcript, _ = resolve_halt_transcript(payload)`、`sid = transcript.stem if transcript else "unknown"`，
再組 `f"halt@{sid}@{decision.binding.kind}@{str(halt_resets_at(decision))[:16]}"`。sid 取法刻意與
`quota_halt_actions()` 寫入標記檔名用的同一個來源一致。`quota_prepare_actions()`（prepare 帶的閂鎖）
本輪**未動**——複審只點名 halt 分支，prepare 帶只影響訊息去重不涉及持久標記寫入，優先權較低。

LOC 影響：`quota_gate.py` 493→495（`guardrail_hub` tier 上限 500，餘裕 5）；`quota_messages.py`
175→177（`guardrail_lib` 上限 400，餘裕 223）。

紅→綠逐字：

```
$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q -k test_naive_now_is_rejected_not_crashed   # 紅端（修前）
E       TypeError: can't subtract offset-naive and offset-aware datetimes
../lib/quota_messages.py:167: TypeError
1 failed, 23 deselected in 0.11s

# 修後
$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q -k HaltMarkerSelfCheckTest
.....                                                                    [100%]
5 passed, 19 deselected in 0.09s
```

```
$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q -k HaltLatchIsSessionScopedTest   # 紅端（修前）
FF                                                                       [100%]
AssertionError: Tuples differ: (0, 0) != (2, 2)   # waker 只被叫一次
AssertionError: Tuples differ: (0, 0) != (2, 2)   # event 參數漏傳（自身測試 bug，已修正）
2 failed, 24 deselected in 0.11s

# 修正測試自身 bug 後重跑（quota_gate.py 仍未修）：
..F                                                                      [部分]
AssertionError: 1 != 2 : 第二個 session 被第一個的機器級閂鎖誤擋 ⇒ RC-3 復發
1 failed, 1 passed

# 修 quota_gate.py 後：
$ python -m pytest tools/tests/test_wake_chain_halt_r278.py -q -k HaltLatchIsSessionScopedTest
..                                                                       [100%]
2 passed, 24 deselected in 0.10s
```

三支必跑摘要：
```
$ python -m unittest test_wake_chain_halt_r278 test_context_budget_guard test_quota_policy -q
Ran 908 tests in 29.633s
OK (skipped=10)
```

### §7 把握程度

- RC-1（測試污染）：**高**。本機重現逐位元組吻合現場三份標記，非推測。
- RC-2（halt_verdict 過期判準）：**高**。用真實 (now, idle_seconds) 三筆重放，輸出與觀測日誌逐字對應。
- RC-3（latch 非 session-scoped）：**中→已修**。latch 缺 session 維度為程式碼實查所證，「本場究竟是
  哪個呼叫者先閂上」不可考（latch 檔不記歸屬），第二修復包已補 per-sid 閂鎖鍵並先紅後綠驗證。
- RC-4：**高**（結構性推論）。
- RC-5：**高，但含一次自我訂正**——初次分析誤讀 grep 輸出，已用結構化重讀訂正並如實記載，未隱藏。
- F-1/F-2 附帶修復：**高**（先紅後綠＋真實 launchd 端到端演練雙重驗證）。
- naive-now 防呆：**高**。先紅（TypeError 逐字重現）後綠，2 行修法，純函式無副作用。

### §8 未做到／疑慮（如實列出）

1. `quota_prepare_actions()`（prepare 帶的類似閂鎖）閂鎖鍵同樣未含 sid，本輪依複審點名範圍未擴大
   修復；🔴 訂正（Dev-D 複審 APPROVE 後）：其風險不只是訊息去重——會壓掉第二個 session 的
   `write_resume_plan()` 持久任務書骨架，不只是訊息去重；後果比 halt 分支輕（該 session 真撞 halt
   時仍會拿到自己的標記與 spawn）。
2. halt 閂鎖底層 `announced_latches`/`remember_latch`（`.claude/hooks/context_budget_guard.py` 約
   L609-628）是非原子讀改寫（純 `open("w")` 覆寫、無鎖），與 `quota_ledger.claim_once` 的 `O_EXCL`
   原子佔位不同，兩 session 幾乎同時到 halt 分支可能 lost-update ⇒ 重複 spawn；已知風險，另立追蹤，
   本輪未修復。
3. `resolve_halt_transcript` 解析不到逐字稿時閂鎖鍵退化為 `sid="unknown"`，兩個都解析不到的並發
   session 仍共用一把鍵——已知殘留、可接受，本輪未修復。
4. naive-now 拒寫是純防禦性 hardening：現行唯一生產呼叫端 `quota_gate()` 的 `now` 恆為 aware，非
   修復已踩到的路徑（該防禦是為未來呼叫端而寫，非本輪事故的直接成因）。
5. Windows 側未實機：所有修法皆為純函式／跨平台程式碼，理論上 Windows 行為一致，但本輪僅在 macOS
   用真 launchd 驗證（同第一輪既有邊界）。
6. 孤兒 `.part.<pid>` 清理（見 DEF-200-282／Dev-C 包）的 Windows 分支（`psutil.pid_exists`）未在
   Windows 上實測；AISDLC_SDD 未宣告 `psutil` 依賴，該分支實質是 no-op（fail-safe，見複審備註）。
7. `_FROZEN_GUARD_LINES`／`guard_self` 分桶棘輪重釘（R144，見 `test_adr_xplat001_c1c2_lock.py`／
   `guard_bucket_policy.py`）為單一代理在任務書明文授權下執行，非正式四方複審——與掌舵者裁決「重釘
   儀式只准收尾單人窗口做」的關係留待掌舵者事後追認或推翻。
