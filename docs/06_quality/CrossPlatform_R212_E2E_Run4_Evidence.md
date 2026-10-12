# CrossPlatform R212 第四列證據檔：跑法④ 真機驗收、PRD §12 權限旗標落款、.env 同步答覆

- **輪籤**：R212 第四列（2026-10-12，macOS 真機；真機段主控親跑，其餘為子代理）；不冠新輪號。主檔＝`docs/06_quality/CrossPlatform_R212_WakeChain_EnvLayer_Evidence.md`，本檔延續其〈十一〉。新立 `DEF-200-527` 一列作 PRD §16.5 (iii) 的入口（同輪 fixed；〈四〉），帳本其餘不動（`python tools/check_defect_log_crossref.py --unresolved-count` 末段「未結列數＝0／全部 228 列」〔修復包親跑〕）。
- **體例**：〔主控親跑〕＝主控在真機自己跑的輸出；〔他包回報：包名〕＝只讀報告、Docs 包沒重驗；〔Docs 包親跑〕＝撰寫包唯讀現查；〔修復包親跑〕＝四方複審後的修復包當回合真跑（含突變實驗）。逐字區塊複製自 scratchpad（`e2e4/run/`、`dev_s12/`，不入庫）。pytest 數字以「通過／略過」斜線對代稱。

---

## 〈一〉掌舵者原文與本列範圍

**T1 原文（2026-10-12，與 10-11 同一份的第六次貼文，不是新需求原文；逐字）**：

> 「1.請徹底完成以上任務，找到沒法完成收斂的根因，徹底解決？請想盡所有辦法完成收斂任務！ 2.完成實作AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md裡面所有功能！ 3.如何將兩邊的 .env同步，哪邊才是正確完整的？這個參數檔該如何維護？幫我設計自動同步機制！==> 下次在Windows執行時，幫我自動同步！請進行驗證功能是否ＯＫ？ 4.需要馬上切到Windows執行及開發嗎？」

**W1** 跑法④（〈二〉〈三〉）；**W2／W3** PRD §12 權限旗標 T4 命中（依 §16.5 (iii) 轉 ✅）與 F-SBR-001 r5 真跑（〈四〉）；**W4** 四問答覆：問 1（收斂根因）＝主檔〈二-0〉兩層結論仍是答案，本列補上真機（〈三〉）；問 3、4＝〈五〉；**問 2（完成實作 PRD 所有功能）**：依 §16.1，v2.1 已做完（101 列恰落四格、無未分類〔他包回報：Architect 鏡〕）。字面「所有功能」不等於該命題，兩讀並陳：「照 §16.1（掌舵者 2026-10-10 立案的『做完』定義），v2.1 已做完；沒做的 31 項（動工前快照；本列後 ⏸ 為 30）依 §16.5 設為『等症狀出現才做』、33 項依設計不做、8 項只欠驗收紀錄（皆為凍結日快照數；各列歸格為主控代決）。要連這些也做，說『重開第 N 項／全部重開』，我就開，並把你的原話記進 PRD §16.6。」掌舵者可隨時以 §16.5 (i) 推翻；本列依 §16.5 (iii) 另轉一格、並在 §6.1 列追記一句同事件的事實（格不變；〈四〉），§16.3 快照不重算。

---

## 〈二〉跑法④逐字證據（W1；主控親跑；2026-10-12 13:16～13:57）

入庫驗收工具：`tools/probe/wakechain_e2e.py`（`--selftest`／`--judge`／`--run`；覆蓋面與限制見本節首段末）。

**問題**：S14／主檔〈五〉#38——真 `claude -p -r` 續跑窗跑在哨兵 job 內時，窗內 PostToolUse hook 會派生 `--arm-sentinel`；`LaunchdBackend.arm()` 的早退（DEF-200-526 的修法）是否擋下它、job 是否活到 handback。**設計**（SA 鏡 `e2e4/RUNBOOK.md`，不入庫〔他包回報：SA〕；判決器 `judge4.py`＝S14-core 9 項＋tail 13 項）：全新 haiku 小 session、boost 灌 turns 過門檻（`turns>=24`；`span>=600s` 靠牆鐘）；第 3 節＝三條單獨唯讀 git＋零檔案改動＋「## 下一步指令」非空，預期出口 `NO_PROGRESS_STOP`（真 handback 2/2 的下一步非空，非 DONE 才是預設出口〔Architect 鏡〕；④ 與真撞線共用出口分支與尾段、觸發不同：本列是「被指示零改檔」，真撞線是「有做事但量成 0」，見主檔〈五〉#37；「最可能出口」為讀碼＋2/2 真 handback 推得，無觀測頻率）；本機 `.env` 暫寫 `AUTOSDD_MODEL_HELMSMAN=haiku # override-ok`（主控裁決，窗後還原）。**措辭**：真 launchd × 真 planner／`relay_machine`／`schedule_backend` × 真 `claude -p -r`（haiku，一次）；halt 標記**手寫**（真寫入器 `quota_gate.write_halt_marker`），證明消費端、不證明生產端。**入庫工具**：`tools/probe/wakechain_e2e.py`（`--selftest`／`--judge`／`--run`）是 `judge4.py` 的 17 項子集（S14-core 9＋tail 8；C5／C6／M2／M2b／M3 未移植）；`--selftest` rc=0、`--judge` 對本輪真痕跡重判 `S14-core: PASS（8/8）｜tail: PASS（7/7）｜WARN 2`（WARN＝S6b／C8，暫存任務書與紙條已清）〔修復包親跑〕；其 `--run` 只被 mock 驗過、未在真機整段跑過（本節真跑＝手動 RUNBOOK＋`judge4.py`），覆蓋面僅 `NO_PROGRESS_STOP`＋S14 早退，DONE 尾段與 calendar 延後重載的重驗件仍在 scratchpad、未入庫。

### 二-1 Stage 0～3

- **Stage 0～1**：基線 job 只有 `AutoSDD_Sentinel_c785cd2b-f043-485a-8674-417f85abf251`（別視窗）與 `AutoSDD_Sentinel_2b759c13-b2f8-4119-90f0-ee0e73a92ea4`（主控視窗），全程不動；八項 GO 皆成立（含 XPC 實驗 `own: LABEL_X`／`child(default inherit): 0`〔主控親跑，未落檔；Docs 包重跑逐字相同〕）。SID `14fb33dc-4ffc-40c9-b62b-9dcf801d02f4`，`claude -p … --model haiku --session-id <SID>` 與 `-r` 續接各一次，皆 `"is_error":false`；窗前 `span=33s`，窗內評估時隨牆鐘已是 2319.1 秒。
- **Stage 2～3**：手動 `--arm-sentinel`（`run interval = 900 seconds`、**無** calendar）、`.env` 暫覆寫（`--env-doctor` 印 `AUTOSDD_MODEL_HELMSMAN = haiku〔.env〕`）；T0＝13:37:54 寫標記 `reset_at=2026-10-12T13:52:54.288671+08:00`（＋15 分）、`fire_at=…T13:54:54.288671+08:00`、預期 calendar `Month=10-Day=12-Hour=13-Minute=55`；kickstart 後 `PASS assert sentinel_decided.action == "arm_reset"`（`p3_verdict1.txt`）；F5（interval tick 不得重載）：13:52:55 第二組事件仍帶 `StartCalendarInterval = Month=10-Day=12-Hour=13-Minute=55〔la…`，bootout log 終態只有兩組四行（下節）。

### 二-2 Stage 4 等 calendar、真窗、判決

13:55:01 抓到窗：`launchctl print`（節錄；`immediate reason = xpc event`，`calendarinterval` descriptor＝13:55，與 `sentinel_woken` 13:55:00 吻合）；`ps`：`claude -p -r 14fb33dc-… --permission-mode acceptEdits --settings …/settings.unattended.json --model haiku …`（pid 63542）的 ppid 是 63538＝job 本體 `session_resume_planner.py --sentinel-tick`：

```text
gui/501/AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4 = {
	…
	state = running
	…
	runs = 2
	pid = 63538
	immediate reason = xpc event
	…
	last exit code = 0
	…
			stream = com.apple.launchd.calendarinterval
	…
			descriptor = {
				"Minute" => 55
				"Hour" => 13
				"Day" => 12
				"Month" => 10
			}
```

**事件 17 筆**（逐字；`f0:N`＝痕跡 jsonl 行號，第 1 行是 Stage 2 手動武裝的 `sentinel_armed`，在 T0 之前）：

```text
f0:2     13:37:54 sentinel_woken                   plan=/Users/wuweihong/.autosdd/plans/autosdd_resume_plan_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.md
f0:3     13:37:54 sentinel_decided                 action=arm_reset reason=偵測到自願 halt 標記；觀測 reset=2026-10-12 13:52:54.288671+08:00 尚未到 ⇒ 要求排程器改在那個時刻醒（本次零 token） controller_idle_seconds=1257.2208490371704 quota_band=unmeasured
f0:4     13:37:54 sentinel_rearmed                 action=arm_reset fire_at=2026-10-12T13:54:54.288671+08:00 credential=launchd gui/501/AutoSDD_Sentinel_14fb33dc-4ffc-4…[plist 已落地並帶 StartCalendarInterval = Month=10-Day=12-Hour=13-…
f0:5     13:52:55 sentinel_woken                   plan=/Users/wuweihong/.autosdd/plans/autosdd_resume_plan_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.md
f0:6     13:52:55 sentinel_decided                 action=arm_reset reason=偵測到自願 halt 標記；觀測 reset=2026-10-12 13:52:54.288671+08:00 尚未到 ⇒ 要求排程器改在那個時刻醒（本次零 token） controller_idle_seconds=2158.5794298648834 quota_band=unmeasured
f0:7     13:52:55 sentinel_rearmed                 action=arm_reset fire_at=2026-10-12T13:54:54.288671+08:00 credential=launchd gui/501/AutoSDD_Sentinel_14fb33dc-4ffc-4…[StartCalendarInterval = Month=10-Day=12-Hour=13-Minute=55〔la…
f0:8     13:55:00 sentinel_woken                   plan=/Users/wuweihong/.autosdd/plans/autosdd_resume_plan_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.md
f0:9     13:55:00 sentinel_decided                 action=probe reason=偵測到自願 halt 標記；觀測 reset=2026-10-12 13:52:54.288671+08:00 已過 ⇒ 花一次探測確認額度回來了沒 controller_idle_seconds=2282.9790098667145 quota_band=notice
f0:10    13:55:00 woken                            plan=/Users/wuweihong/.autosdd/plans/autosdd_resume_plan_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.md
f0:11    13:55:00 probed                           rc=0 kind=none quota_open=true text=endpoint@2026-10-12T13:53:42+08:00: 6 軸皆 <100%（最高 weekly_all=62.0% resets_at=2026-10-17T17:59:59.532735+00:00） source=endpoint
f0:12    13:55:00 route_chosen                     strategy=SESSION_RESUME why=逐字稿可用（520,419B ≤ 上限 33,554,432B）⇒ 帶完整 context 續跑
f0:13    13:55:00 relay_snapshot_before            lines=10 digest=176f124e69450533bd53d91638683f999cc2ad7b3a0ad7ac73de447f8bfb5e3d
f0:14    13:55:03 sentinel_armed                   task=AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4 credential=launchd gui/501/AutoSDD_Sentinel_14fb33dc-4ffc-4…[state = running] handled_through=2026-10-12T05:55:03.110Z
f0:15    13:55:17 resumed                          rc=0 strategy=SESSION_RESUME handback_path=/Users/wuweihong/.autosdd/handback/14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.md handback_written=true err= out=E2E4-OK\n
f0:16    13:55:17 relay_stopped                    why=no_progress band=notice note=/var/folders/ld/fkzj758537q6sf9dgzdw83zr0000gn/T/AUTOSDD_ATTENTION.md note_written=true notify_rc=-2 notify_queued=false
f0:17    13:55:17 sentinel_armed                   task=AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4 credential=launchd gui/501/AutoSDD_Sentinel_14fb33dc-4ffc-4…[plist 已落地並帶 StartCalendarInterval = (無)（`plutil -lint` 通過）] handled_through=2026-10-12T05:55:15.778Z
f0:18    13:55:17 relay_rearmed                    rc=0 unregister_rc=null next_state=NO_PROGRESS_STOP rearmed_inplace=true
```

**bootout log**（逐字 9 行）：

```text
parent-gone waited=1s at 2026-10-12T05:37:55Z
bootout rc=0
bootstrap rc=0 tries=1
print rc=0
{"event": "arm_skipped_inside_job", "label": "AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4", "job_pid": 63538, "pid": 63598, "ppid": 1, "xpc": "0", "at": "2026-10-12T13:55:03+0800"}
parent-gone waited=1s at 2026-10-12T05:55:18Z
bootout rc=0
bootstrap rc=0 tries=1
print rc=0
```

第 1～4 行＝T0 的 `arm_reset` 延後重載；第 5 行＝窗內 hook 派生的 `--arm-sentinel` 走到 `arm()` 的早退：`job_pid=63538` 等於窗內 `launchctl print` 的 `pid`，`pid=63598`／`ppid=1`＝孤兒化的 hook 孫行程，`xpc="0"`＝預設繼承把 `XPC_SERVICE_NAME` 洗成 0 ≠ label；第 6～9 行＝窗後尾段重掛。窗內沒有 `parent-gone`；unload 帳 `ours=3 other=0`（13:37:15 `bootstrap`、13:37:54 `deferred-bootout`、13:55:17 `deferred-bootout`＝與 `resumed` 同秒的尾段重掛；判決當時的帳，Z.1 的 13:57:22 `bootout`〔`--remove-schtasks`〕不計，帳上同 label 共 4 列），`resumed` 之前零列。job 本體 pid 連續：13:55:17 那列的 `pid=63538`（`xpc`＝label、argv＝`--sentinel-tick`）＝早退行 `job_pid=63538`＝窗開時 `launchctl print` 的 `pid`，即同一個 job 本體行程在 hook 派生的 arm 之後 14 秒仍活著並自行做尾段重掛〔QA 鏡讀痕跡〕；判決器 S5c 只查 `resumed` 存在、不比對 pid（pid 連續性判準未入庫）。

**判決器**（逐字，22 項全 PASS，含各項 `↳` 明細；另 5 項 INFO 不計入、未貼：S6a／S6c／S6d＝hook 派生 planner 跑過 `main()`、SessionStart 跑過 `arm_sentinel`、窗內 PostToolUse `hook_success` 5 筆；C9＝launchd log 有 alert 行；C10＝窗內零新增髒檔）：

```text
PASS  [S14-core] S1  窗開（relay_snapshot_before）且窗收（resumed）
        ↳ 窗 2026-10-12 13:55:00+08:00 ～ 2026-10-12 13:55:17+08:00（17s）
PASS  [S14-core] S2  窗內 hook 派生的 --arm-sentinel 走到 arm() 且憑證自述「該 job 正在跑」
        ↳ launchd gui/501/AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4｜launchctl print rc=0｜state = running｜plist = /Users/wuweihong/Library/LaunchAgents/AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf80
PASS  [S14-core] S3  autosdd_sentinel_bootout_AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.log 有窗內的 arm_skipped_inside_job（label 對、at 在窗內）
        ↳ job_pid=63538 pid=63598 ppid=1 xpc='0'（xpc≠label 才會走到早退）
PASS  [S14-core] S4  should_arm 在窗內通過（events 檔 sentinel_armed：turns>=24 且 span>=600）
        ↳ turns=38 span_seconds=2319.1
PASS  [S14-core] S5a 窗內沒有 parent-gone（＝沒有人在窗內排延後 bootout 重載）
PASS  [S14-core] S5b unload 帳窗內對本 label 沒有 bootout／deferred-bootout
PASS  [S14-core] S5c tick 活到 resumed（claude 收窗後 tick 還在寫痕跡）
PASS  [S14-core] S5d autosdd_sentinel_launchd_AutoSDD_Sentinel_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.log 無 Traceback
PASS  [S14-core] S6b 活任務書（autosdd_resume_plan_14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.md）第 3 節未被 hook 派生的骨架重寫蓋掉（含 E2E4-S14）
PASS  [tail] C1  事件依序出現（窗內 hook 派生的 sentinel_armed → resumed → relay_stopped → 窗後哨兵重掛 sentinel_armed → relay_rearmed）
PASS  [tail] C2  欄位斷言（arm_reset→probe；probed.quota_open；SESSION_RESUME；resumed.rc=0＋handback_written；relay_stopped.why=no_progress；relay_rearmed rc=0／同名原地／NO_PROGRESS_STOP）
PASS  [tail] C2b alert(loud) 副作用：紙條已寫、無桌面通知（notify_rc=-2）、未入補投佇列
        ↳ band='notice'（收窗時額度帶；不影響出口判定）
PASS  [tail] C3  禁止事件皆未出現
PASS  [tail] C4  第一次 arm_reset 的憑證帶 StartCalendarInterval（= Month=10-Day=12-Hour=13-Minute=55）
PASS  [tail] C5  launchctl list 終態：基線齊、本 SID 只剩哨兵、無殭屍
PASS  [tail] C6  unload 帳自 T_START 起對基線 label 沒有 bootout／deferred-bootout
PASS  [tail] C7  autosdd_unattended_outcome.jsonl 自 T_P4 起本 SID 恰 +1 列（event=unattended_stop reason=no_progress handback=…/<SID>.md）
        ↳ {"event": "unattended_stop", "session": "14fb33dc-4ffc-40c9-b62b-9dcf801d02f4", "reason": "no_progress", "reset_returned": true, "handback": "/Users/wuweihong/.autosdd/handback/14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.md", "at": "2026-10-12T13:55:17+0800"}
PASS  [tail] C8  alert 紙條 $TMPDIR/AUTOSDD_ATTENTION.md 存在、mtime 在窗內、載本 SID 與停止原因
        ↳ /var/folders/ld/fkzj758537q6sf9dgzdw83zr0000gn/T/AUTOSDD_ATTENTION.md
PASS  [tail] M1  成本帳該 SID 新列：measured=true、model 含 haiku
        ↳ {"measured": true, "model": "claude-haiku-5-5", "reason": null, "input_tokens": 2, "cache_creation_input_tokens": 2479, "cache_read_input_tokens": 78087}
PASS  [tail] M2  窗內逐字稿：模型、Read 任務書、三條單獨 git 指令、Write 只寫 handback（零檔案改動）
PASS  [tail] M2b 窗開前逐字稿 assistant 記錄數 >= 24（should_arm 的 turns 門檻）
        ↳ 窗前 turns=37
PASS  [tail] M3  handback：四節齊、「## 下一步指令」節**非空**（出口＝no_progress 的前提；空＝會走 DONE）、mtime 在窗內
        ↳ 再跑一次 `git status --short` 並回報結果。
S14-core: PASS（9/9）｜tail: PASS（13/13）｜WARN 0
VERDICT4 rc=0
```

### 二-3 成本、handback、Stage Z 終驗

**成本**（`usage_dedup.txt`，逐字；成本帳 4→5 列，該列見判決 M1）：

```text
窗內  model=claude-haiku-5-5   真請求=4  (記錄 8) input=8      cache寫=10899   cache讀=331651   output=2318  ⇒ 輸入面 342,558  估 $0.0067
窗前  model=claude-haiku-5-5   真請求=4  (記錄 37) input=8      cache寫=66631   cache讀=220326   output=3636  ⇒ 輸入面 286,965  估 $0.0173
[CC cost-state（實際記帳）] 累計 totalCostUSD=0.024004  各模型 costUSD=claude-haiku-5-5:0.024004  窗內差額=$0.006656
```

**handback**（haiku 寫成、四節齊；「卡在哪」逐字，第 4 節見判決 M3）：

```text
## 卡在哪
工作樹不乾淨，與計畫書第 3 節「本窗必須維持零檔案改動」的前提相反。本窗**沒有**修改、建立、刪除任何檔案，這些改動來源不明（本 session 未做）。未碰、未 commit、未 push。需要人回來確認這些改動是誰的（可能是另一包或另一視窗），再決定保留或保全（git stash create ＋ tag）。
```

haiku 如實回報 10 項改動「來源不明（本 session 未做）」，未碰、未 commit；那是並行 Developer 包的編修（〈六〉#51）。結局檔與紙條見判決 C7／C8（紙條 Z.1 已還原）。**Stage Z 終驗**：`launchctl list` 過濾 AutoSDD 只剩兩個基線哨兵；痕跡行數 59／5／4（unloads／cost／outcome）；`.env` sha256 `6868f80b39824749…` 前後相同〔主控親跑，未落檔〕；`--env-doctor` 現查 rc=0 且與 Stage 0 基線 `diff` rc=0〔Docs 包親跑〕；終態 repo 髒檔 10 行（基線空）是並行包 13:16 後的編修，窗內前後快照相同；`--pace` 已消費結局警語（逐字）：

```text
🔴 ⚠️ 上次無人續跑：於 2026-10-12T13:55:17+0800 停在 no_progress，額度已回，handback=/Users/wuweihong/.autosdd/handback/14fb33dc-4ffc-40c9-b62b-9dcf801d02f4.md，請重驗（zero-trust：不採信『已通過』宣稱）
```

---

## 〈三〉接縫覆蓋更新（主檔〈十一-5〉的續表；「真」＝真 launchd 行程內實跑）

| 接縫 | 主檔原記 | 第四列後 |
|---|---|---|
| S14／#38 哨兵承載的真窗內，hook 派生的 `--arm-sentinel` 走到 `arm()` | 未發生／真實鏈未實跑 | **真，1 筆**：早退成立（事件名見〈二-2〉bootout log 第 5 行；`xpc="0"`、`ppid=1` 由推得變實測）；窗內零 `parent-gone`／`deferred-bootout`；job 活到 `resumed` 與尾段（job 本體 pid 連續，見〈二-2〉） |
| #36 settle 非 DONE 出口 | 真機零筆 | `no_progress` **真，1 筆**：`relay_stopped`→`sentinel_armed`→`relay_rearmed next_state=NO_PROGRESS_STOP rearmed_inplace=true`；結局檔 +1 列、紙條已寫、無桌面通知（`notify_rc=-2`）；觸發是「被指示零改檔」，與真撞線（續改窗前已髒的檔、量成 0）共用出口分支與尾段、觸發不同（主檔〈五〉#37） |
| 「標記起頭＋真 claude」 | 主檔〈六-3〉：沒有任何一次同時具備 | 本列為首筆：手寫標記→`arm_reset`→calendar 到點→`probe`→真 `claude -p -r` |

另：L0 讀數沿用 78 秒前快取（`endpoint@2026-10-12T13:53:42+08:00`，TTL 內），不新增主檔〈五〉#3 的自取樣本；現存 `$TMPDIR` resume log 的 `route_chosen` 共 5 筆、全為 SESSION_RESUME（3 個 sid，含 10-10 的真撞線窗；本列窗是其中一筆）〔他包回報：SA 鏡、Architect 鏡〕，FRESH／PATROL 在 R212 第一至四列範圍內（mac 真機）零筆。重掛後的哨兵（`relay_rearmed rearmed_inplace=true` 之後）＝同名 job 以 interval 900 秒、無 calendar 重載（Z.1 前的 `launchctl print`〔主控存檔〕：`runs = 0`、`run interval = 900 seconds`、無 event triggers）；+900 秒的 tick 走 `_sentinel_tick`：無真撞線事件，halt 標記若仍在則因「窗內逐字稿活動 > reset＋120 秒」判過期（`halt_verdict`）⇒ 落閒置巡邏（`patrol`，零 token），不會再 spawn 一窗〔讀碼，未實測：Z.1 於 13:57:22 已移除該哨兵，窗後只存活約 2 分鐘〕。**本清單為本列已知項，不是完整宣告；R212 第一至四列範圍內（mac 真機）無樣本、不宣稱**：`RELAY_NEXT`／`quota_stop`／`relay_exhausted` 出口；探測回「未恢復」的 `rearm`／`patrol_handback`／`stop` 三出口（殘存真痕跡 `probed` 6 筆全為 `quota_open=true`）；真 429 逐字稿事件或真 halt 標記起頭的 `arm_reset`（`sentinel_decided` 的 `arm_reset` 4 筆全為手寫標記 E2E、`escalate` 0 筆；含 7-E 生產端）；窗內真改檔（`RELAY_NEXT` 的前提；主檔〈五〉#37 預測第一窗即 `NO_PROGRESS_STOP`）；失敗態（resume_failed／REFUSE／`rc=None` 重掛）；FRESH／PATROL 路由；24h 或至少 4 次 reset 的連續閉環；睡眠喚醒；主檔〈五〉#39；窗長超過 1 小時；R212 第四列沒有 Windows 真機樣本（含 Windows 喚醒鏈：主檔〈五〉#10／#11／#39）。測試替身只建模 Windows 語意（主檔〈二-0〉第 2 層第 1 項）本列未動，登〈六〉#58。收斂是症狀驅動（主檔〈二-0〉第 3 點、範本〈🏁〉），本表不是「接縫都走過了」的宣告。

---

## 〈四〉PRD §12 權限旗標：T4 命中、處置與落款（W2、W3）

**T4 對照**（範本〈🏁〉T4；〔他包回報：Architect 鏡〕唯讀掃描 2026-10-11 後寫入的 38 個逐字稿檔等，對 PRD §16.2 的 31 個 ⏸ 格；座標 Docs 包複核）：**命中 1**＝[22]「§12 權限旗標」，再開症狀「引擎於非容器環境以 `bypassPermissions` 跑了一次（附 config 與 sid）」。F-SBR-001 乾淨真跑 C1～C4 以 `--permission-mode bypassPermissions` 跑巢狀 claude：`AutoClaude/docs/03_testing/SddBridge_RealRun_Evidence_20261011.md` 第 13 行 `claude.extra_args = ['--permission-mode', 'bypassPermissions', '--model', 'haiku']`、第 80～84 行 argv 表（自 02:46:49）、第 391 行自陳「巢狀 claude 以 `--permission-mode bypassPermissions` 執行，實際上可讀寫任何路徑」〔Docs 包逐行核對〕。巢狀逐字稿 sid（`~/.claude/projects/-private-tmp-claude-501-sbr-iso-5535e815-r{1,2,3,4}-…/` 檔名 8 碼前綴，`ls`〔Docs 包親跑〕）：r1 `576cddc1`／`d9567d2c`；r2 `597a72ee`／`80793cb5`；r3 `0c561a4b`／`fffd2e9a`；r4 `edc1f6b9`／`f59303d9`。

**處置（兩讀並陳）**：Architect 鏡初審認為症狀字面成立、但性質是主控自造的驗證跑（隔離目錄、haiku、顯式 opt-in、無實損）＝構造性（`severity.md`〈暴露度〉），建議母體不動、向掌舵者揭露、由他決定；複審撤回異議、同意轉格（理由：HEAD 的 `AutoClaude/config.yaml` 註解、`AutoClaude_Guide.md`、`config.py` 註解與六份 ab_configs 都教人在主機用 bypass，暴露是持續的文件面事實；機制已全落且有測試；非守衛面）〔他包回報：Architect 鏡〕。QA 鏡判：字面成立、性質最弱（主控自造、無實損）、程序面原先不穩（未走 (iii) 的唯一入口、PRD 動了不只一格）〔他包回報：QA 鏡〕；本列據此補兩件——立 `DEF-200-527`（§16.5 (iii) 的入口，「分流去向」標 §16.2 座標，同輪 fixed）、PRD 只動 §12 一格（⏸→✅）＋§6.1 列同一事件的一句事實追記（格不變）；§11.1 部分落款已自 PRD 撤回，改記〈六〉#53。**主控裁決**：掌舵者 T1 第 2 句要求完成實作，依 §16.5 (iii) 把 [22] 由 ⏸ 轉 ✅（§16.3 快照不重算；修訂表 v2.1.18），掌舵者可隨時以 §16.5 (i) 推翻。**轉格判準（為何 [22] 轉、[17]／[21] 不轉）**：症狀實際發生，且該列規範的機制於同輪全部落地並有測試；[17]／[21] 雖同為 F-SBR-001 C4 真跑命中，但 DEF-200-518 只修了 ESCALATION 善後（dump／通知／演化提案），`NEEDS_HUMAN`／告警機制未落地，故不轉格，座標記於 DEF-200-518「分流去向」〔Architect 鏡 P3-7〕。未動守衛面（`.claude/hooks/**`、`.claude/settings*.json`、根 CLAUDE.md〈守衛面准入〉所列檔零改動）。

**實作座標**（〔他包回報：Developer〕；座標 Docs 包 `grep`／`git diff` 現查）：`AutoClaude/autoclaude/execution/boot_self_check.py` 的 `detect_isolation_env`（非 Linux 視為主機）、`permission_bypass_requests`（`executor.permission_mode` 與 `claude.extra_args` 兩條路都判）、`permission_bypass_allowed_from_env`（只讀行程環境；打錯字算關）、`permission_bypass_verdict`；`AutoClaude/autoclaude/main.py` 的 `run_boot_self_check` 餵入兩個設定面；`AutoClaude/.env.example` 新增註解鍵 `# ALLOW_PERMISSION_BYPASS=false`；範本 `AutoClaude/scripts/bridge_e2e/wordcount/config.template.yaml` 改 `--permission-mode acceptEdits` ＋ `--allowedTools "Read,Edit,Write,Bash(pytest:*)"`；測試 `AutoClaude/tests/execution/test_prd12_permission_bypass_invariant8.py`（新增 86 項：全套 5159／156 → 5245／156〔他包回報：Developer 終態；13:34 的第一版曾為 79 項、5238／156〕）。**判決表**（PRD §6.1 不變式 8 的前件是旗標，字面讀法，主控裁決採用；要求 bypass／旗標為真／容器）：否／否／任＝放行；否／是／有＝放行；**否／是／無＝拒絕**；是／否／任＝拒絕；是／是／無（macOS 一律視為主機）＝拒絕；是／是／有＝放行並 log。

**閘門逐字**（Developer 終態，`dev_s12/final3_*.log`〔他包回報：Developer〕）：AutoClaude pytest 全套 5245／156（通過／略過）、41.35 秒、rc=0（`final3_pytest.log`；修前 5159／156）；`PYTHONUTF8=1 lint-imports` → `Contracts: 9 kept, 0 broken.` rc=0；ruff 尾行＝全部檢查通過；`check_loc_budget` → `total=17962 baseline=17079 cap=20438 violations=0`。開機自檢煙霧：舊 bypass 範本 `boot rc=1`（`ERROR 開機自檢未過 | … ALLOW_PERMISSION_BYPASS 不是 true（目前＝未設）⇒ 拒絕啟動`），新範本 `boot rc=0`。

**F-SBR-001 r5**（`acceptEdits`＋白名單範本，haiku；〔主控親跑〕，`dev_s12/sbr_r5_*.txt`）：`run_clean_rc=0`；aggregate `{'total_steps': 3, 'success_steps': 3, 'pass_rate': 1.0, 'evaluator_steps': 3, 'escalated': None, 'kernel_success': None, 'peak_token_pct': None}`（後兩欄 None；同 log 內 `KernelResult(success=True, completed_steps=3, total_steps=3` 逐字存在）；log `開機自檢 |` 3 行、`開機自檢未過` 0 行；`結果：成功（SUCCESS）`；`tool_use 共 14 次；越界 0 次 ⇒ 乾淨`、`audit_rc=0`。n=1、haiku 機率性，不宣稱失敗率。**ab_configs**（六份舊 bypass config，`AutoClaude/scripts/ab_configs/*.yaml`；〔他包回報：Developer〕）：全改 PRD §12 正道、不再用 `bypassPermissions`——`ab_pty` 為 `--permission-mode acceptEdits --allowedTools Read,Edit,Write,Bash(pytest:*)`（pty 路）；`ab_sdk` 為 `executor.permission_mode: acceptEdits` ＋ `sdk_tool_allowlist [Read, Edit, Write, Bash]`（SDK 白名單只到工具名粒度、`Bash` 名放行任意指令，登〈六〉#57）；`correction_mock`／`correction_real` 與 `lowthr_compact`／`lowthr_halt` 為 `Read,Edit,Write`（消費者只需寫檔，或由 evaluator 親跑 pytest）。靜態驗證：六份 `run_boot_self_check` 皆 `boot_rc=0`；回歸鎖 7 項（`test_prd12_…py`）；隔離副本 7 個突變（AB1～AB7）全殺。**六份未真跑**（各檔註解載「尚待真跑驗證」）。

**複審後的修復（修復包；〔修復包親跑〕）**：(a) 立 `DEF-200-527`（695 bytes，≤700）；PRD 撤回 §11.1 追記、§12 落款補劃界。(b) `AutoClaude/tests/conftest.py` 新增 autouse `_hermetic_permission_bypass_flag`：殼層 export 的 `ALLOW_PERMISSION_BYPASS` 不再影響測試——修前該旗標為 true 時 `test_r100_boot_self_check.py::test_g10_*` 2 項紅〔SD 鏡 P4-5〕，修後同指令（`-k "g10 or prd12 or boot_self_check"`）148／0；鎖＝`tests/test_conftest_quota_env_isolation.py::TestPermissionBypassFlagIsNotLeakedIntoTests`（探針只斷言旗標不在 `os.environ`；子行程帶旗標跑它：有 conftest 必綠、`--noconftest` 對照組必紅，不碰容器偵測故各主機結果確定；隔離副本突變 2 個——fixture 不再 pop 旗標→鎖紅、探針改成 `assert True`→對照組紅——皆被殺）。(c) 仍教 bypass 的兩處（`AutoClaude/config.yaml.example`、`AutoClaude/docs/04_planning/AutoClaude_Guide.md`）改為 acceptEdits＋白名單／加註記，`AutoClaude/.env.example` 補「只判引擎設定面」劃界句〔SD 鏡 P3-5〕。(d) `tools/probe/wakechain_e2e.py`：`z()` 每步獨立 try／except 且 `.env` 還原排第一，收尾消費結局警語（落 `<out>/banner.txt`）並清 `$TMPDIR` 閂鎖目錄；judge 加回 `resumed.rc==0`，C4 的 calendar 預期改由 `arm_reset` 事件的 `fire_at` 推導（`+59s` 只往後取整，與 `schedule_backend_calendar` 同；原 `w.cal in cal` 在 `--judge`／`--run` 恆真），S6b 只在任務書不在時降 WARN（被覆蓋即紅）；罐頭裡 arm 早退事件名那一行不再含 4 位數字（`check_pytest_baseline_sites` 未納管站點維持 114，不增為 115〔Architect 鏡 P2-1〕）；檔頭明標 `--run` 只被 mock 驗過。驗證：`--selftest` rc=0；`--judge` 對本輪真痕跡仍 `S14-core: PASS（8/8）｜tail: PASS（7/7）｜WARN 2`；scratchpad 罐頭世界突變 5 個（`resumed.rc=1`→C2 紅、`fire_at` 加 5 分→C4 紅、缺 `fire_at`→C4 紅、事後模式任務書被覆蓋→S6b 紅、任務書已清→S6b 仍 WARN）皆如預期；sandbox 替身跑 `run_e2e`（S3 例外＋handback `.ack` unlink 失敗）：`.env` 還原符、失敗步驟逐步印出、其餘清理照做（修前原檔在同一沙箱同情境 `.env` 留著 haiku 行〔SD 鏡 P3-1；修復包重現〕）；另 6 情境（S3 例外／S3 `KeyboardInterrupt`／S4 例外／S4 內 SIGTERM／NO-GO／Z 內 unlink 失敗）×3 種 `.env` 原貌（缺檔／有結尾換行／無結尾換行）共 18 格皆 `.env` 還原符，結局警語步驟本身失敗時其餘步驟照做且 rc=1；全檔 450 行（修前 447），`check_loc_budget` 的 `root_tools_violations`／`tier_violations` 皆 `[]`。**未做**：QA 鏡 T1／T2（pid 連續性判準、`tickdead` 負對照）、SD 鏡 P3-4／P3-6 與 S0 的 `.env` 殘留行 NO-GO——不在本輪裁決範圍，且 450 行上限已無餘裕。

---

## 〈五〉.env 同步與是否切 Windows（掌舵者問 3、4；Architect D／E 題白話版）

**哪邊才正確、怎麼維護**：兩邊的 `.env` 都不是標準。標準在 repo：`env.shared`（追蹤檔，放決策值，如停機線 98）＋出廠值（`ENV_SPEC`）；根目錄 `.env.example` 才是程式生成的完整鍵清單（`python tools/lib/quota_policy.py --print-env-example`），不要複製成 `.env`；`AutoClaude/.env.example` 是引擎側手寫的覆寫層範本（引擎專屬覆寫＋機密，額度鍵只認 3 個，harness 不讀）；每台機器的 `.env` 只放「這台的例外」（行尾 `# override-ok: <理由>`）。載入鏈：行程 env ＞ `AutoClaude/.env`（引擎 3 鍵）＞ `.env` ＞ `env.shared` ＞ 出廠。決策值改 `env.shared`、commit 並 `git push`（沒 push 的那台會靜默吃不同值），另一台 pull 後由 `post-merge` hook 自動對齊（ONBOARDING §2.2）；體檢 `python tools/lib/quota_policy.py --env-doctor`（唯讀，rc=0 才算沒遮蔽），可自動修的才 `--fix`（先備份）；UTF-16 存檔的 `.env` 會被讀成亂碼鍵（主檔〈五〉#41）。

**自動同步與驗證**：git `post-merge` hook（主檔〈二-11〉），mac 控制流有 `TestPostMergeHook` 七支鎖；R212 第四列沒有 Windows 真機樣本。間接證據〔推論；他包回報：Architect 鏡〕：該機自 2026-09-22 起 83 個 commit 皆已 push（最新 `0da65578`＠2026-10-06），pre-push 以 `pick_repo_python` 解析直譯器、失敗即擋 push，故當時 `core.hooksPath` 與 `.venv\Scripts\python.exe` 是通的；無鎖缺口＝`TestPostMergeHook` 把 `pick_repo_python` 整個替身，真直譯器解析沒有端到端測試；只能在 Windows 驗：cp950 顯示、Git for Windows 實際觸發、nightly 是否弄髒 `ONBOARDING.md`。

**驗收一行（RESULT 自判版，已取代主檔〈八-1〉含 pull 版；逐字抄 Architect 鏡 D 題）**：

```powershell
Push-Location (git rev-parse --show-toplevel); git pull --ff-only; $p = $LASTEXITCODE; $LASTEXITCODE = $null; $o = & .\.venv\Scripts\python.exe tools/lib/quota_policy.py --env-doctor; $d = $LASTEXITCODE; if (($p -eq 0) -and ($d -eq 0)) { "RESULT: PASS" } else { "RESULT: FAIL pull_rc=$p doctor_rc=$d" }; Pop-Location
```

〔Docs 包親跑〕`lint_command()` 回 `[]`；pwsh 7.6.3 於 mac 暫存 repo（直譯器換成 `./.venv/bin/python`、零網路）五情境皆如預期：新 commit＋doctor rc=0 → `RESULT: PASS`；doctor rc=2 → `RESULT: FAIL pull_rc=0 doctor_rc=2`；pull 被髒檔擋下 → `pull_rc=1 doctor_rc=0`；直譯器不存在 → `pull_rc=0 doctor_rc=`；不在 git repo → `pull_rc=128 doctor_rc=`。5.1 同形為〔推論〕。此一行版看不見〔process-env〕覆蓋（與主檔〈五〉#42 同；舊的含 pull 版有印兩行來源欄，現版沒有，要看來源欄跑主檔〈八-1〉的展開版）。

**最可能的失敗畫面與處置**：pull 被 nightly 弄髒的 `ONBOARDING.md` 擋下：`error: Your local changes to the following files would be overwritten by merge: ONBOARDING.md … Aborting`、pull_rc=1〔推論，該機未見過；訊息形狀已在暫存 repo 見到〕；其後 doctor 在舊樹跑，不認 `--env-doctor`、rc=2 ⇒ `RESULT: FAIL pull_rc=1 doctor_rc=2`，不會是假綠。處置：`git status --short` 確認髒的只有 ` M ONBOARDING.md`，再 `git diff --stat ONBOARDING.md` 確認只有錨那幾行（若含表② 回填，改走主檔〈八-2〉步驟 2：先 `git add`＋commit 再 `git pull --no-rebase`）；確認後在一般 PowerShell 視窗（非 Claude 視窗；Claude 視窗內 `block_destructive_git.py` 會擋 `git restore`，見主檔〈八-2〉）執行 `git restore ONBOARDING.md`，再貼一次。**先 pull、再做表② 回填**：回填（`clean_venv_carrier.py`）會寫 ONBOARDING.md，restore 會抹掉它。髒內容通常是 nightly 寫回的錨〔推論，該機未見過〕。一行版只是備援，實務入口是 `useMacWin.md` 啟動提示詞。

**要不要馬上切 Windows**：不需要。開發留 mac；Windows 面的待驗清單在主檔〈八-4〉（該機專屬、非再開事件），在該機做該機的事時含三件（估 1～2 小時〔估計〕）：①啟動提示詞（同步＋post-merge 首次實跑＋dev_start）；②表② Windows 欄回填 `.venv\Scripts\python.exe tools/lib/clean_venv_carrier.py`（需 Docker daemon；先 pull 再回填）；③上面的驗收一行。理由：mac 專屬工作（launchd 真機，本列 W1 已跑）在 Windows 驗不了；雲端 windows-compat-ci #336 success（主檔〈四-3〉）；晚切的代價只是首次 pull 帶更多 commit（`--ff-only` 失敗時 loud 且不改樹）。**這個理由沒覆蓋的面**：Windows 喚醒鏈（schtasks 後端，主檔〈五〉#10／#11／#39）R212 第四列零量測，不因「不需要切」而變成已驗。

---

## 〈六〉理論洞新增（P4；只登記、不修；全域連號接主檔〈五〉最大號 #50）

| # | 洞 | 暴露度 | 再開症狀 |
|---|---|---|---|
| 51 | 續跑窗接手的工作樹含別人未提交的改動：handback 如實回報 10 項「來源不明」並未碰（正確），但靠模型自制；`files_changed` 只數窗後新增的 porcelain 行，窗內他人新增髒檔會量成有進度、排出下一窗 | 前半真機 1 筆（〈二-3〉）；後半構造 | handback 把他人改動報成自己的產出或 commit／保全了它們，或因他人新增髒檔而排出 `relay_spawned`（附 sid＋前後 `git status`） |
| 52 | 收窗額度帶取自快取檔：`relay_machine.current_band` 只讀快取（零網路），`reset_returned`＝帶為 free／notice〔Docs 包親讀〕。本列 `weekly_all` 62.0% ⇒ `band=notice`、`reset_returned=true`。快取 TTL 180 秒〔SA 鏡讀碼〕短於多數真窗：窗長超過快取剩餘壽命時帶為 `unmeasured` ⇒ `reset_returned=false`、`--pace` 寫「額度未回」而額度已回〔推論；本列窗 17 秒，未走到〕 | `notice` 分支真機 1 筆；`unmeasured` 只有讀碼 | 結局列 `reset_returned=false` 而同刻 `quota_meter --refresh` 各軸 <100%（附 sid＋結局列＋輸出） |
| 53 | PRD §11.1「零 token 遙測 6 小時」列仍為驗收資料殘留格（📎，PRD 不動）：現存 4 段 ≥6 小時全機靜止窗（哨兵閒置自我解除門檻 21600 秒使每筆解除＝一段 ≥6 小時靜止＋24 次零 token 巡邏）**只證「哨兵巡邏零 token」，不證「遙測零 token、U5h 增量 0」**（遙測當時根本沒被輪詢；巡邏只讀快取）。四段（sid：起→終 +08:00，靜止秒）：435d2cb4-4d1a-44e8-9622-e5d073b2fa35（2026-09-22 11:00:05→17:03:26，21801；24 次巡邏＋1 次解除）、ba149f52-54bf-4364-b89d-4d70675ca65a（09-27 16:58:53→23:04:07，21914）、c00d202a-360b-435f-8ffb-35345ba9a507（10-03 13:43:38→19:45:43，21725）、35be7e5b-abb2-4e08-8711-4835b91a4482（10-05 23:08:28→10-06 05:09:37，21669）；座標＝`~/.autosdd/traces/autosdd_sentinel_launchd_AutoSDD_Sentinel_<sid>.log` 末 25 行與同名 `autosdd_sentinel_bootout_AutoSDD_Sentinel_<sid>.log` 解除時刻；四段期間 `~/.claude/projects/` 全 11 個專案目錄無 jsonl 寫入、`quota_burn.jsonl` 窗內 0 列〔他包回報：Architect 鏡；QA 鏡獨立重掃 725 個 jsonl、四窗命中 0 筆〕 | 他包回報＋QA 鏡重掃；Docs 包核對四份 bootout log 末兩行時刻相符 | PRD §11.1 列的結案格被改為 ✅（`git diff` 可見）而依據只引用這四段；或遙測在 ≥6 小時窗內被輪詢（`quota_burn.jsonl` 窗內 ≥1 列）而同窗 `~/.claude/projects/**/*.jsonl` 有新增 token 記錄、或 U5h 相對權威讀數增量 ≠ 0（附窗界與兩份讀數） |
| 54 | 早退成立繫於 hook 以預設繼承 `Popen` 派生：條件之一是 `XPC_SERVICE_NAME` ≠ label（本列 `xpc="0"`、`ppid=1`）；`spawn_sentinel` 的 `Popen` 無 `env=`（`.claude/hooks/context_budget_guard.py`〔Docs 包現查〕）；日後改顯式 `env=` 帶回 label，早退即失效、殺掉承載它的 job〔推論；SA 鏡讀碼〕 | 真機 1 筆＋本機實驗；翻盤未實測 | 同主檔 #38：窗內 bootout log 出現 `parent-gone waited≤3s` 且當窗無 `resumed`，unload 帳 `xpc`＝label |
| 55 | 跨 session 並行寫者：哨兵的靜止守門只看本 session 逐字稿（`halt_verdict` 的 idle 取自 `session_transcripts(transcript)`），續跑窗啟動時他窗（掌舵者另一視窗、Developer 包）若仍在改同一 repo，兩個寫者互蓋；與 #9（同 session 雙窗）、#51（量法偏誤）不同〔SA 鏡讀碼〕 | 前提本列已真實出現：13:16 起並行 Developer 包製造 10 行髒檔，窗內 haiku 報「來源不明」（〈二-3〉）；碰撞本身未觀測 | 續跑窗存續期間（`relay_snapshot_before`→`resumed`），另一 sid 的逐字稿對同一路徑也有 Edit／Write，或同檔 diff 交錯（附兩 sid＋路徑＋時刻） |
| 56 | `NO_PROGRESS_STOP` 只停「接力」不停「巡邏」：窗「起不來」型（REFUSE／A-PRE 拒／spawn 失敗）不寫逐字稿 ⇒ halt 標記或真撞線事件不過期 ⇒ 下個 900 秒 tick 再 probe→resume，每次 loud 紙條＋結局列，至 6 小時閒置解除（零 token 但吵）〔SA 鏡讀碼：`halt_verdict`／`_resume_tick`／`settle_window`；未實測〕 | 讀碼推得；無真機痕跡 | 同一 sid 的 `autosdd_unattended_outcome.jsonl` 在 6 小時內 ≥2 列 `no_progress`（附 sid＋列） |
| 57 | ab_sdk 白名單只到工具名粒度：`sdk_tool_allowlist [Read, Edit, Write, Bash]` 的 `Bash` 名放行＝任意指令（pty 路的 `Bash(pytest:*)` 是指令粒度）；config／測試 docstring／sprint_history 稱「引擎限制」，而 `build_tool_allowlist_predicate` 的 predicate 簽章 `(tool_name, _tool_input)` 拿得到 `tool_input`，窄化可在 predicate 內做——是設計取捨、不是引擎限制〔SD 鏡讀碼〕 | 構造；六份 ab_configs 皆未真跑；ab_sdk 只是開發者手動 A/B 載具 | ab_sdk 真跑的逐字稿出現 pytest 以外的 Bash 指令（附 sid＋`tool_use` 座標），或有人要求窄化 |
| 58 | 測試替身只建模 Windows 語意（主檔〈二-0〉第 2 層第 1 項：`_StatefulFakeSchedulerBackend.disarm` 同步移除）：本列補的是偵測手段（真後端 E2E），替身不對稱未修也未登記〔Architect 鏡〕 | 真機 2 筆同型：DEF-200-523、DEF-200-526 皆經真 launchd 才現形（帳本發現情境） | 下一個只在 mac 真後端（launchd）現形、而離線測試（替身）全綠的缺陷（附 DEF 列＋該缺陷在替身上的行為差異） |

---

## 〈七〉本機閘門

- **Docs 包親跑**（落筆後；當回合尾行與 rc）：`check_defect_log_crossref.py`／`check_handoff_carriers.py`／`check_pytest_baseline_sites.py`／`ruff`（governance_docs）皆 rc=0；三支 unittest `Ran 488 tests`／`FAILED (failures=6)`：6 項同源＝ONBOARDING §7 表① `loc-baseline-live` 17857 ≠ 實測 17962（Developer 的 AutoClaude 編修所致，早於本包動工；收尾回填 `python tools/sync_onboarding_baselines.py --write`）
- **四方複審鏡各自真跑**（〔他包回報：X 鏡〕；尾行逐字摘要，pytest 數字以「通過／略過」斜線對代稱）：
  - QA 鏡（CONDITIONAL；P2×4＝D1～D4，修復包已全修）：新測試檔 86／0（rc=0）；觸及改動模組的 9 支測試檔 425／1；`lint-imports` `Contracts: 9 kept`；`check_loc_budget` `total=17962 baseline=17079 cap=20438 violations=0`；單檔 unittest：`test_adr_xplat001_c1c2_lock` Ran 187 tests／OK、`test_platform_neutral_paths` Ran 177 tests／OK、`test_subprocess_encoding_hygiene` Ran 39 tests／OK、`test_platform_utils_dedup` Ran 43 tests／OK、`test_doc_loc_baseline_freshness_r60` Ran 281 tests／FAILED (failures=6)（同源＝ONBOARDING §7 表① `loc-baseline-live` 與指紋）；9 個突變（M1～M8／M8'）全被殺。
  - SD 鏡（APPROVE；P3×6）：新測試檔 86／0（`-n 3 --dist worksteal` 86／0；注入 `ALLOW_PERMISSION_BYPASS=true container=podman KUBERNETES_SERVICE_HOST=10.0.0.1` 亦 86／0）；相關七檔 453／0、橋接三檔 111／0；`lint-imports` `Contracts: 9 kept, 0 broken.`；ruff `All checks passed!`；`check_loc_budget` violations=0；根層單檔 unittest：`test_platform_neutral_paths`＋`test_subprocess_encoding_hygiene` Ran 216 tests／OK、`test_adr_xplat001_c1c2_lock` Ran 187 tests／OK、`test_platform_utils_dedup` Ran 43 tests／OK、`test_doc_loc_baseline_freshness_r60` Ran 281 tests／failures=6（同源）；A 面程式突變 14 個全殺、回歸鎖資料突變 8 個全紅（存活 2 個為 regex 寬度，P4）。
  - Architect 鏡（CONDITIONAL；P2×1＝驅動器罐頭的 arm 早退事件名那一行同時含 4 位數字，致 `git add` 後棘輪 114→115，修復包已修）：`test_platform_neutral_paths` Ran 177 tests／OK；`test_subprocess_encoding_hygiene` Ran 39 tests／OK；doc_loc 具名 7 類 Ran 66 tests／OK；`TestOnboardingLiveBaselineFreshness` failures=1（已知）；`check_loc_budget` rc=0；`check_defect_log_crossref`／`check_handoff_carriers` rc=0；`sync_onboarding_baselines.py --check-snapshot` rc=1（已知：macOS 欄 autoclaude 指紋 35e0a0326ae2→0e9f53abe3aa）；ruff 全過；`lint-imports` 9 kept；新測試檔＋`test_r100_boot_self_check` 144／0；`.env.example` 相關 AutoClaude 4 檔 234／0；`test_quota_env_layers`＋`test_quota_policy` Ran 377 tests／OK；round-label 鎖＋`test_check_pytest_baseline_sites` Ran 30 tests／OK；`secret_scan --paths`（14 個改動／新檔）rc=0。
  - SA 鏡（APPROVE；P3×10，修復包已處置）：`wakechain_e2e.py --selftest` rc=0；`--judge` rc=0（8／8＋7／7＋WARN 2）；`check_defect_log_crossref.py --unresolved-count` rc=0（當時 0／227）；`lint_powershell_command.lint_command()` 對 RESULT 一行回 `[]`；pwsh 7.6.3 五情境；`relay_machine` 純函式；未跑 AutoClaude 全套。
- **修復包親跑**（〔修復包親跑〕；當回合尾行）：`check_defect_log_crossref.py` rc=0（帳本 228 筆）；`check_handoff_carriers.py` rc=0；`check_pytest_baseline_sites.py` rc=0（未納管站點 114）；`wakechain_e2e.py --selftest` rc=0、`--judge`（本輪真痕跡）rc=0；`ruff check tools/probe/wakechain_e2e.py tools/lib/governance_docs.py` rc=0；`check_loc_budget` `total=17962`、`root_tools_violations`／`tier_violations` 皆 `[]`；AutoClaude：旗標 export 下 `-k "g10 or prd12 or boot_self_check"` 148／0（rc=0）、全套 5248／156（通過／略過，rc=0；較 Developer 終態 5245 多本包新增的 3 項＝探針＋2 鎖）、`lint-imports` `Contracts: 9 kept, 0 broken.`、ruff 全過；根層 `test_check_defect_log_crossref`／`test_defect_id_reference_integrity`／`test_check_pytest_baseline_sites`／`test_platform_neutral_paths`／`test_subprocess_encoding_hygiene` 合跑 Ran 523 tests／OK（rc=0，`AUTOSDD_SENTINEL_OFF=1`）；`test_adr_xplat001_c1c2_lock`＋`test_platform_utils_dedup` Ran 230 tests／OK（含 SC-9）；`test_doc_loc_baseline_freshness_r60` Ran 281 tests／FAILED (failures=6)（與複審鏡同一組已知 6 項：ONBOARDING §7 表① `loc-baseline-live` 17857 ≠ 實測 17962 與其衍生，回填前的預期狀態）；`sync_onboarding_baselines.py --check-snapshot` rc=1（macOS 欄 autoclaude 指紋 35e0a0326ae2→7dfd3589edad：本包動了 `AutoClaude/tests`，指紋須在收尾回填前定稿）；`secret_scan --paths`（本包動到的 12 檔）rc=0。
- **主控收尾親跑**〔主控親跑，2026-10-12 收尾單人窗口；rc 逐字〕：四方審查（SA／SD APPROVE；Architect／QA CONDITIONAL→修復包全修→QA 二審 APPROVE）後，根層全套 `python tools/run_root_unittests.py` 前兩次 rc=1——第一次早退於靜態標籤掃描（`_TREE_FILE_FLOORS['AutoClaude/tests']` 230 低於實測 289 的 80%，照指示重釘 231，`tools/lib/skip_tag_policy.py`）、第二次 1 failure＝`test_mac_endurance_r83.BackendInterfaceIsSymmetricTest.test_the_launchd_only_exemptions_really_have_no_outside_consumer`（本檔〈二〉的探針呼叫了後端 launchd 專屬豁免方法；改為探針內部以 `hasattr(os, "getuid")` 罩住自組 `gui/<uid>`，並把註解裡的同名子字串拿掉——該鎖是全 repo `.py` 的子字串掃描）；第三次 `root suite rc=0`（`[cpu_budget] root-unittest workers=9`；skip census tools/tests@darwin 47 支全為 platform 標籤、欠債型 0；真實 TEMP 圍籬零變動）。AutoClaude 全套 `python -m pytest tests/ -q`：5248／156（通過／略過）rc=0；`PYTHONUTF8=1 lint-imports`：`Contracts: 9 kept, 0 broken.`；`ruff check tools/probe/wakechain_e2e.py` 全綠；`--selftest` `SELFTEST rc=0`；對稱鎖單跑 `OK`。表① 已 `sync_onboarding_baselines.py --write`（LOC 17962）；表② 回填（`clean_venv_carrier.py`）與 `--check`／`--check-snapshot`、commit／push／CI 對帳見本節下一行（回填 commit 補）。
- **雲端對帳**〔主控親跑；回填 commit〕：commit `1818de87`（29 檔）push 觸發六支 workflow 皆 `completed success`（`gh run list --commit 1818de87fbbb5a96673008d50eeb1e619ce22223`，等候 1107 秒）：root-infra-ci 38230301052／AutoClaude CI 38230301082／macos-compat-ci 38230301062／windows-compat-ci 38230301093／arch-fitness 38231604962／drift-daily 38230947003。push 前 pre-push 全套 rc=0（`7552166f..1818de87  main -> main`）；表② 由 `clean_venv_carrier.py` 回填 rc=0、`--check`／`--check-snapshot` 皆 rc=0。本回填 commit 不再回填。

---

## 〈八〉開了→收了（本列）

| 開了 | 收了／現況（憑證＝〔Docs 包親跑〕唯讀現查，除非另標） |
|---|---|
| haiku 小 session `14fb33dc-…`；`AutoSDD_Sentinel_14fb33dc-…` | 逐字稿**保留**（609,568 B）；哨兵 Z.1 `--remove-schtasks` 已移，`launchctl list` 過濾 AutoSDD 與 `~/Library/LaunchAgents/` 都只剩兩個基線哨兵 |
| halt 標記；本機 `.env` 一行；`$TMPDIR/AUTOSDD_ATTENTION.md` | 標記已刪（`~/.autosdd/traces/` 只剩 5 份歷史真標記）；`.env` 已還原（`--env-doctor` 現查與基線逐字相同；sha256〔主控親跑〕）；紙條已還原成基線那張真事件紙條（與 `base_ATTENTION.md` `cmp` rc=0） |
| 本 SID 的 `~/.autosdd/plans/`、`handback/` 檔與 `$TMPDIR` 骨架／armed／閂鎖／boot log | 已刪；**未收**：`$TMPDIR/autosdd_ctxguard_14fb33dc-….latches.d/`（內含 117 B 的 `known_model_windows_path.cache`，boost 視窗 hook 產物，Z.1 的 `rm -f` 不含目錄） |
| traces、`$TMPDIR` resume log；scratchpad；Docs 包的唯讀查詢與 pwsh 暫存 repo | traces 與 resume log **刻意保留**（證據）；scratchpad 不入庫；Docs 包未起背景行程、未註冊排程、未 commit／push |
| 修復包的突變副本（`AutoClaude` 複本）與 sandbox 替身 harness | 複本已刪；harness 用 `tempfile.mkdtemp` 沙箱並自刪；未執行 `launchctl`／`claude`／`--run`，未起背景行程、未註冊排程、未 `git add`／commit／push |
