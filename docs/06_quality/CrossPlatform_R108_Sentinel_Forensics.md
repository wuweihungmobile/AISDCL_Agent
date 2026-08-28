# CrossPlatform R108 — 哨兵死亡實機驗屍報告

> **性質**：唯讀取證報告。ADR-XPLAT-014 §4.3〈死因取證方法設計〉自承「排程器日誌那一路
> 完全未實測」（同檔 §5-6：「事件 ID、日誌是否預設啟用、保留期多久，本 ADR 一個字都沒有
> 量過」）——本報告是那一路的**第一次實測**。
>
> **標的事件**：`docs/04_planning/R107_RESUME.md:114-120` 記載的哨兵
> `AutoSDD_Sentinel_b13f4527-525f-4128-9eed-a80207d4d3f6` 在 2026-08-28 11:51~14:57
> 之間死亡（armed stamp 說在、`Get-ScheduledTask` 查無此工作），14:59 重武裝。
>
> **三態紀律**：本報告每一項都區分〔**量得到**〕／〔**量不到**〕／〔**通道不存在**〕。
> 這是 ADR §4.3 步驟 3 與 §6 表 C6' 的規範性要求：「讓查詢 rc≠0 ⇒ 若回『無事件』＝紅」。
> 本報告**不允許**把「查不到」寫成「沒發生」。

---

## 1. 量測環境（實查，非引用）

| 項目 | 實測值 | 取得指令 |
| --- | --- | --- |
| 量測時刻 | `2026-08-28 21:21:01 +08:00` ～ `21:30` 之間 | `Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'` |
| 機器名 | `Koala-MSI` | `hostname` |
| OS | `Microsoft Windows NT 10.0.26200.0` | `[System.Environment]::OSVersion.VersionString` |
| 殼引擎 | PowerShell `7.6.5`（PowerShell 工具面；生產排程 Action 走 `pythonw.exe`） | `$PSVersionTable.PSVersion` |
| 執行身分 | `KOALA-MSI\wuwei` | `[Security.Principal.WindowsIdentity]::GetCurrent().Name` |
| **是否提權** | **`False`**（非 Administrator） | `WindowsPrincipal.IsInRole([WindowsBuiltInRole]::Administrator)` |

🔴 **提權狀態是本報告多處「量不到」的直接原因**，不是通道不存在。兩者在 ADR 的三態裡
是不同的格子，混報會讓下一輪誤以為那些通道無用。

---

## 2. 逐項取證結果

### 2.1 排程器事件日誌通道（ADR 預測「可能預設關閉」）— 〔量得到〕，**預測證偽**

```powershell
Get-WinEvent -ListLog 'Microsoft-Windows-TaskScheduler/Operational'
```

實測輸出（逐字）：

```
LogName            : Microsoft-Windows-TaskScheduler/Operational
IsEnabled          : True
LogMode            : Circular
MaximumSizeInBytes : 10485760
RecordCount        : 17116
LastWriteTime      : 2026/8/28 下午 09:21:02
OldestRecordNumber : 210667
```

**保留期覆蓋現查**（這一步決定「事件窗還在不在」，不得推算）：

```
Oldest TimeCreated : 2026-08-20 05:06:01  RecordId=210667 Id=100
Newest TimeCreated : 2026-08-28 21:21:01  RecordId=227782 Id=102
```

⇒ **2026-08-28 11:51~14:57 的事件窗完整落在保留期內**。ADR 預測的「可能未啟用 ⇒ 對事件窗
零觀測能力」在本機**不成立**：這個通道不但可用，而且是**唯一**能把死亡定位到秒的通道。

> 開啟通道的指令（若在他機為 `IsEnabled=False` 時需要，**本報告未執行**、需提權）：
> `wevtutil set-log Microsoft-Windows-TaskScheduler/Operational /enabled:true`

**窗內事件量（09:00~15:30）**：全機 1483 筆，其中含 `AutoSDD` 者 135 筆。實測到的事件 ID
與語意（皆取自本機逐字訊息，非查表推測）：

| Id | 本機逐字語意 |
| --- | --- |
| 106 | 使用者「…」已**登錄**工作排程器工作 |
| 140 | 使用者「…」已**更新**使用者工作 |
| 141 | 使用者「…」已**刪除**工作排程器工作 |
| 111 | 工作排程器已**終止**工作的執行個體 |
| 107 | 由於滿足**時間觸發程序**條件，已啟動執行個體 |
| 129 | 已啟動工作，執行個體「`…\pythonw.exe`」，**處理程序識別碼**為 N |
| 100 | 已為使用者「…」啟動工作的執行個體 |
| 200 / 201 | 已啟動 / 已順利完成動作，**傳回碼為 N** |
| 102 | 已順利完成工作的執行個體 |

### 2.2 Security 日誌 4698／4699 替代路 — 〔量不到（需提權）〕，且**訊息會偽裝成量到零**

```powershell
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4698,4699; StartTime=…; EndTime=…}
# → EXCEPTION: No events were found that match the specified selection criteria.

Get-WinEvent -ListLog 'Security'
# → ListLog EXCEPTION: To access the 'Security' log start PowerShell with elevated user rights.
#   Error: Attempted to perform an unauthorized operation.

auditpol /get /subcategory:"{0CCE9227-69AE-11D9-BED3-505054503030}"
# → rc=1314 / Error 0x00000522: A required privilege is not held by the client.
```

🔴 **這是本輪最危險的一格**：非提權查 4698/4699 拋出的例外訊息是
**「No events were found that match the specified selection criteria.」**——與「日誌可讀但
真的沒有那些事件」**逐字相同**。把它讀成「沒有刪除事件」就是 ADR C6' 明文要防的假確定性。

⇒ 判準：**必須先 `Get-WinEvent -ListLog 'Security'`**，那一步失敗才是「量不到」的憑證；
稽核政策本身（`auditpol`）同樣需提權，故「4698/4699 有沒有被開啟稽核」在非提權下
**也量不到**。三態結論：**通道存在、非提權下量不到、本報告不對其內容作任何斷言。**

### 2.3 排程器現況快照 — 〔量得到〕

**量測於 `2026-08-28 21:21:26`**（🔴 下列輸出中本 session 的工作名已按全檔體例截到 UUID
前 8 碼＋`…`，同 `b13f4527-…` 的處理；三審 QA 要求兩種寫法不得並存）：

```
TaskName                     State TaskPath
--------                     ----- --------
AutoSDD_Sentinel_020d4b1c-…  Ready \

TaskName           : AutoSDD_Sentinel_020d4b1c-…
LastRunTime        : 2026/8/28 下午 09:12:42
LastTaskResult     : 0
NextRunTime        : 2026/8/28 下午 09:27:42     ← 憑證（值，不是 rc）
NumberOfMissedRuns : 0
```

⇒ 現存 `AutoSDD_*` 工作**只有一支**＝本 session（`020d4b1c`）的哨兵。R107 於 14:59 重武裝的
`AutoSDD_Sentinel_b13f4527` 與 `AutoSDD_SessionResume_b13f4527` **現已皆不存在**（死亡時刻
見 §2.6 旁證）。

### 2.4 痕跡檔兩處 — 〔量得到〕，但**位置與 ADR §4.3 的假設不符**

**(a) `%TEMP%`（`C:\Users\wuwei\AppData\Local\Temp`）**：與本案相關者

| 檔名 | 大小 | mtime |
| --- | --- | --- |
| `autosdd_resume_log_autosdd_resume_plan_b13f4527-….jsonl` | 15445 | `2026-08-28 17:57:11` |
| `autosdd_sentinel_armed_b13f4527-….json` | 253 | `2026-08-28 09:03:02` |
| `autosdd_sentinel_boot_b13f4527-….log` | 138 | `2026-08-28 08:50:47` |
| `autosdd_resume_plan_b13f4527-….md`（任務書＋狀態塊） | — | **不存在** |

armed stamp 內容（逐字）：

```json
{"session_id": "b13f4527-525f-4128-9eed-a80207d4d3f6", "turns": 24, "span_seconds": 728.8,
 "armed_at": "2026-08-28T09:03:02",
 "transcript": "C:\\Users\\wuwei\\.claude\\projects\\d--CursorProject-AISDCL-Agent\\b13f4527-….jsonl"}
```

🔴 **stamp 的 mtime 是 09:03:02，而工作死於 14:02:09** ⇒ 死亡路徑**沒有**清掉 stamp。
ADR **§4.3 末段〈順帶要修的一格〉**預告的歸因盲區（「stamp 在、工作不在」與「被外部刪除」
事後同形）**實測成立**（🔴 **本版把原本的 `:536-539` 改為節級引用（三審 QA）**：那個行號
已被 ADR 自己的後續修訂沖走，現在指到 §3.5 Q6 的三選一選項；跨檔引用一律以節號為錨）。marker 路徑構式現查 `tools/lib/sentinel_lifecycle_arm.py`（ADR 引 :144-145）。

**(b) `~/.autosdd/traces`（`C:\Users\wuwei\.autosdd\traces`，持久面）**：目錄存在，內含

| 檔名 | 大小 | mtime |
| --- | --- | --- |
| `claim_freshness.jsonl` | 5264 | `2026-08-28 17:27:57` |
| `quota_burn.jsonl` | 6559 | `2026-08-28 21:21:06` |
| `autosdd_quota_availability.json` | 127 | `2026-08-28 21:22:43` |
| `autosdd_quota_stability.json` | 94 | `2026-08-28 21:22:43` |

🔴 **零筆 bootout／abort／disarm／哨兵決策痕跡。** 哨兵的四分支決策**全部**寫在 (a) 的
`%TEMP%` jsonl，不在持久痕跡目錄（`trace_dir()` ＝ `~/.autosdd/traces`，
SSOT `tools/lib/endurance_env.py:104-118`〔實讀〕，其消費者是 quota 那一族，不是哨兵）。
⇒ 照 ADR §4.3 步驟 1 走（「先讀 `~/.autosdd/traces` 找 bootout/abort，命中即答案是自己走的」）
會在本案**零命中**，並據此**誤判「不是自己走的」**——而真相恰恰是自己走的。詳見 §4-F2。

**(c) 事件檔關鍵列（決定性證據，逐字節錄）**：`autosdd_resume_log_…_b13f4527-….jsonl`
（77 列；11:33 以前為每 15 分鐘一次的 `patrol`／`sentinel_rearmed` 正常節律，此處只摘死亡段）

```
event=sentinel_armed   at=08/28/2026 11:44:30  credential=2026/8/28 上午 11:59:29
event=sentinel_woken   at=08/28/2026 11:59:29
event=sentinel_decided at=08/28/2026 11:59:30  action=arm_reset
    reason=偵測到未處理的撞線；觀測 reset=2026-08-28 14:00:00+08:00 尚未到
           ⇒ 要求排程器改在那個時刻醒（本次零 token…）
event=sentinel_rearmed at=08/28/2026 11:59:31  action=arm_reset
    fire_at=08/28/2026 14:02:00  credential=2026/8/28 下午 02:02:00
event=sentinel_woken   at=08/28/2026 14:02:00
event=sentinel_decided at=08/28/2026 14:02:01  action=probe
    reason=偵測到未處理的撞線；觀測 reset=2026-08-28 14:00:00+08:00 已過
           ⇒ 花一次探測確認額度回來了沒
event=woken            at=08/28/2026 14:02:01
event=probed           at=08/28/2026 14:02:08  rc=0 kind=none quota_open=True
event=quota_back_no_resume                     at=08/28/2026 14:02:08   ← 死亡決策
event=sentinel_armed   at=08/28/2026 14:59:40  credential=2026/8/28 下午 03:14:39
```

### 2.5 `C:\Windows\System32\Tasks` XML 殘骸 — 〔枚舉：量不到，且 **fail-open 假陰性**〕／〔點查：量得到〕

```powershell
Get-ChildItem 'C:\Windows\System32\Tasks' -Filter 'AutoSDD_*'
# → 回 $null，**沒有拋任何例外**（表徵＝「目錄可讀，查無 AutoSDD_* 檔」）

Get-ChildItem 'C:\Windows\System32\Tasks' -Force
# → EXCEPTION: UnauthorizedAccessException: Access to the path
#   'C:\Windows\System32\Tasks' is denied.

Test-Path 'C:\Windows\System32\Tasks\AutoSDD_Sentinel_020d4b1c-…'   # → True
Get-Content  '…\AutoSDD_Sentinel_020d4b1c-…' -TotalCount 1          # → 可讀
```

🔴 **證偽自證**：非提權枚舉「查無 `AutoSDD_*`」是**假的**——同一時刻
`Get-ScheduledTask` 明明回報 `AutoSDD_Sentinel_020d4b1c-…` 存在，且以**完整工作名點查**
該 XML 檔 `Test-Path`＝`True`、`Get-Content` 讀得到。⇒ 枚舉路徑**靜默失明**，探針若據此寫
「無殘骸」就是憑空造出負面結論。**可用形態只有「以完整工作名做點查詢」。**

### 2.6 旁證：兩個對照死亡（校準判別器用）

延長查詢到 15:30~21:30（同一通道）：

```
18:09:43 Id=141 \AutoSDD_SessionResume_b13f4527-525f-4128-9eed-a80207d4d3f6
18:09:43 Id=141 \AutoSDD_Sentinel_b13f4527-525f-4128-9eed-a80207d4d3f6
19:27:42 Id=106 \AutoSDD_Sentinel_020d4b1c-…
```

⇒ **`--remove-schtasks`（資源釋放）的簽名＝同一秒刪除「同 session 的兩支工作」，且不伴隨
任何 107/129/200 執行事件。** 14:02:09 那次**只刪哨兵一支、且伴隨自己那一跑的
111＋201(rc=0)＋102** ⇒ 形態明確不同。這個判別器是**經驗校準**出來的，不是推測。

另一項噪音來源需登記：窗內 `AutoSDD_Sentinel_UNITTEST_GHOST` 有 **11＋ 組**
`106`→`141`（09:21、10:11、10:23、10:47、10:58、11:11、15:59、16:20、16:36、16:55、17:11、17:28…）
＝單元測試自造的鬼工作。🔴 **「11＋」不是「11」（三審 QA 訂正，與 §4-F6 統一）**：括號內的
時間戳是**節錄非窮舉**（末尾「…」即此意），而節錄出來的就有 **12** 個 ⇒ 兩數不相等，
本報告**不宣稱確切組數**，兩處一律寫「11＋」。**任何以 `AutoSDD_*` 過濾 141 的探針都會被它灌滿**，必須排除。

---

## 3. 死因研判

### 3.1 事件重建（秒級 × 行程級 × 源碼級三重對齊）

| 時刻 | 通道 | 事實 |
| --- | --- | --- |
| 11:59:29 | 事件日誌 107/129/100/200 | 哨兵按 15 分節律觸發，執行個體 `{eeac42ee}`、`pythonw.exe` PID 37076 |
| 11:59:30 | jsonl | `action=arm_reset`：偵測到未處理撞線、觀測 reset=14:00 未到 ⇒ **主動把下一次觸發從 12:14 改到 14:02** |
| 11:59:31 | jsonl ＋ 事件日誌 201(rc=0)/102 | 重武裝成功，`fire_at=14:02:00`、憑證 `14:02:00` |
| 12:00~14:02 | 事件日誌 | 哨兵**零觸發**（此為**設計行為**，見 §3.2 假說 X 的排除） |
| 14:02:00 | 事件日誌 107/129/100/200 | 觸發，執行個體 `{805dfb5f}`、`pythonw.exe` PID 17712 |
| 14:02:01 | jsonl | `action=probe`：reset 已過 ⇒ 花一次探測 |
| 14:02:08 | jsonl | `probed rc=0 kind=none quota_open=True` ⇒ **額度真的回來了** |
| 14:02:08 | jsonl | **`quota_back_no_resume`** |
| **14:02:09** | 事件日誌 **141 ＋ 111 ＋ 201(rc=0) ＋ 102** | **工作被刪除、自己那一跑的執行個體被終止、動作傳回碼 0** |

### 3.2 假說相容度表

| 候選死因（ADR §4.3 表） | 相容度 | 證據 |
| --- | --- | --- |
| **它自己走了 `disarm`／`_abort_and_unregister` 分支** | **✅ 已證實** | jsonl `quota_back_no_resume`@14:02:08 → 事件 141@14:02:09（**同一跑內、間隔 1 秒**）＋ 111 終止自己的執行個體 ＋ 201 動作 rc=0；源碼 `tools/session_resume_planner.py:1306-1315` 該分支結尾就是 `_schtasks_remove(state["task_name"])` |
| 被外部刪除（人／清理工具／另一支 planner `--remove-schtasks`） | ❌ 排除 | §2.6 校準出的 `--remove-schtasks` 簽名是「兩支同秒刪、無執行事件」；14:02:09 只刪一支且伴隨自己那一跑的 rc=0 完成事件。人手刪除需在自己觸發後第 9 秒精準命中，且 jsonl 已逐字記下它自己的決定 |
| 排程器自己丟了它（服務重啟／任務庫損毀） | ❌ 排除 | 141 帶明確使用者上下文；同窗其他排程工作全程正常（§3.3）；無 Service/損毀類事件伴隨 |
| 被安全軟體清除 | ❌ 排除 | 同上；且不會產生與自身 rc=0 完成同秒的 141 |
| （新增假說 X）**機器睡著導致漏跑** | ❌ 排除 | 見 §3.3 |
| （新增假說 Y）觸發器被 `Set-ScheduledTask`／`schtasks /change` 弄壞（R107 註 #4 的形態） | ❌ 排除 | 12:00~14:02 的零觸發有 jsonl 明文動機（`arm_reset` 主動改時刻），且 14:02:00 **準時觸發**＝觸發器完好 |

### 3.3 「2 小時沒跑」不是死亡，是設計行為（一個很自然的錯假說，已實測證偽）

`Get-WinEvent` 全機事件時間分佈（11:30~14:30，485 筆）顯示 12:00~14:02 期間**其他排程工作
每隔數分鐘持續正常執行**（12:00/12:01/12:04/12:05/12:06/12:09/12:11/12:21/12:26/…/13:56/13:58）
⇒ **機器沒睡**。`Microsoft-Windows-Kernel-Power` 在 09:00~15:30 亦查無任何
42/107/109/130/131 事件（回「No events were found…」；此處該訊息可信，因為同一 `System` 日誌
在非提權下可讀——與 §2.2 的 Security 不同）。哨兵是**單獨**停跑的，而 jsonl 給出了動機：
它自己在 11:59:30 把下一跑改到 reset 之後（14:00 + 2 分緩衝）。

### 3.4 根本原因鏈（源碼實讀，`tools/session_resume_planner.py`）

```python
1306:    if state.get("allow_resume"):
1307:        rc = _run_resume(args, state, log); state["state"] = "resumed" if rc is not None else "resume_failed"
1308:    else:
1309:        rc, state["state"] = 0, "resumed"
1310:        append_log(log, "quota_back_no_resume")
1311:        print(f"✅ 額度已恢復。狀態塊記著 allow_resume=false（…）⇒ 人回來跑：claude -r {state['session_id']}")
1312:    state.update(_cleared_credentials())
1313:    write_relay(plan, state)
1314:    _schtasks_remove(state["task_name"])  # -Once 已觸發、不會再響，無論成敗都不再需要它
1315:    return rc if rc is not None else 1
```

`allow_resume` 的來源（實讀）：

- `:956` `dest="allow_resume", default=os.environ.get(RESUME_OFF_ENV) is None`
- `:277` `RESUME_OFF_ENV = "AUTOSDD_RESUME_OFF"`
- `:1015` `_base_state()` 把 `"allow_resume": bool(args.allow_resume)` 寫進狀態塊
- `:1329` `_arm_sentinel()` 就是用 `_base_state(...)` 建狀態塊

**實測環境值**：

```
$env:AUTOSDD_RESUME_OFF                                              → [1]（已設）
[Environment]::GetEnvironmentVariable('AUTOSDD_RESUME_OFF','User')   → [1]  ← 持久、User 層
[Environment]::GetEnvironmentVariable('AUTOSDD_RESUME_OFF','Machine')→ []
repo .claude/settings.json 的 env 區塊                                → 只有 PYTHONUTF8、
                                                                        CLAUDE_AUTOCOMPACT_PCT_OVERRIDE
```

**現存活哨兵狀態塊實測**（`%TEMP%\autosdd_resume_plan_020d4b1c-….md`）：

```
"allow_resume": false,
```

⇒ **`AUTOSDD_RESUME_OFF=1` 設在 Windows User 層持久環境（不在 repo）**，因此**每一次**
`--arm-sentinel` 都把 `allow_resume: false` 寫進狀態塊，而該值直接決定 :1306 走 `else` 分支。

**四個疊加缺陷**（皆源碼可證，非推測）：

| # | 缺陷 | 後果 |
| --- | --- | --- |
| D1 | `:1309` 在**沒有續跑**的路徑上把 `state["state"]` 寫成 `"resumed"` | 狀態字說謊；事後看狀態塊會以為續跑過了 |
| D2 | `:1311` 唯一的告知管道是 `print()`，而排程 Action 的載具是 **`pythonw.exe`（GUI 子系統、無 console）** | 「人回來跑 `claude -r`」這行**結構上被丟棄**。對比 `:1388` 的 `sentinel_heal_failed` 走 `escalation.alert(..., loud=True)`＝桌面級告警；**本分支沒有** |
| D3 | `:1314` `_schtasks_remove()` **無條件**執行，註解理由「-Once 已觸發、不會再響，無論成敗都不再需要它」 | 該理由對**觸發器**為真、對**任務**為假：本案還有工作待續，哨兵卻自刪 ⇒ 14:02~14:59 喚醒鏈全斷（`SessionResume` 仍停在 19:56） |
| D4 | 該分支未清 armed stamp | 事後「stamp 在、工作不在」與外部刪除同形（ADR §4.3 末段〈順帶要修的一格〉實測成立） |

### 3.5 🔴 這不是歷史事故，是**現行狀態**

現存活哨兵 `AutoSDD_Sentinel_020d4b1c-…` 的狀態塊實測同為 `"allow_resume": false`
⇒ **下一次「撞線 → reset 到 → 探測到額度回來」時，它會走完全相同的分支、同樣自刪、
同樣把唯一的告知寫給不存在的讀者。** 死亡條件仍然武裝著。

---

## 4. 對 ADR-XPLAT-014 §4.3 探針設計的回饋

| # | 回饋 | 依據 |
| --- | --- | --- |
| **F1** | **「日誌預設可能未啟用」在本機證偽**：`IsEnabled=True`、Circular 10MB、保留 8 天（08-20~08-28）、17116 筆。它是**唯一**能把死亡定位到秒＋對到行程 PID 的通道 ⇒ 探針應把它從「候選」升為**主通道**。但「現查是否啟用」這一步**仍要保留**（他機可能不同），只是預期值要改。 | §2.1 |
| **F2** | 🔴 **§4.3 步驟 1 的痕跡位置假設是錯的，且錯的方向會造成誤判**：哨兵四分支決策全寫在 `%TEMP%` 的 `autosdd_resume_log_*.jsonl`；`~/.autosdd/traces` 對哨兵決策**零命中**。照現行步驟 1 走會得到「traces 沒有 bootout/abort ⇒ 不是自己走的」——**與真相相反**。修法：把 `%TEMP%` jsonl 列為**第一順位**證據源，並在 §4.3 表格裡改正那一列的「查不到代表什麼」。附帶的壞消息：決定性證據住在 ADR 自己標「重開機即消失」的檔裡 ⇒ 取證面的頭號風險是**重開機**，不是日誌保留期。 | §2.4(b)(c) |
| **F3** | 🔴 **Security 4698/4699 的失敗訊息會偽裝成「量到零」**：非提權查詢拋的是「No events were found that match the specified selection criteria.」＝與真無事件**逐字相同**。探針**必須先 `Get-WinEvent -ListLog 'Security'`**（失敗才是「量不到」的憑證）；`auditpol` 亦需提權（rc=1314）。這正是 C6' 要防的形態，且它比 ADR 預想的更陰險——不是 rc≠0 就能分辨。 | §2.2 |
| **F4** | 🔴 **`System32\Tasks` 枚舉是 fail-open 假陰性**：`-Filter` 不帶 `-Force` 回空且**不拋例外**；`-Force` 才露出 `UnauthorizedAccessException`。⇒ 探針**不得**用枚舉；唯一可用形態是「以完整工作名點查」（`Test-Path`／`Get-Content` 實測可行）。 | §2.5 |
| **F5** | **§4.3 末段〈順帶要修的一格〉實測成立，且價值比 ADR 說的更高**（🔴 節級引用，原 `:536-539` 已失效）：修掉之後「stamp 在但工作不在」就唯一代表外部刪除——而本案**不是**外部刪除，所以這一格會把歸因成本從「三通道交叉比對」降到「一眼可辨」。建議提前，不要等 §4.4 同輪。 | §2.4(a) |
| **F6** | **探針必須排除單元測試噪音**：窗內 `AutoSDD_Sentinel_UNITTEST_GHOST` 產生 11＋ 組 `106`→`141` 配對。以 `AutoSDD_*` 過濾 141 的探針會被灌滿，真事件被埋。 | §2.6 |
| **F7** | **可交付一個經驗校準的判別器**（ADR 目前沒有）：「自刪」＝141 只刪一支 ＋ 同秒伴隨自身 111/201(rc=0)/102；「`--remove-schtasks`」＝同秒刪同 session 兩支 ＋ 無執行事件。這比「看使用者欄位」可靠——141 的使用者欄位對自刪與人刪**都是** `KOALA-MSI\wuwei`，該欄位**零鑑別力**。 | §2.6、§3.2 |

---

## 5. 誠實劃界

1. **本報告全程唯讀**：只執行查詢類指令，未建立／修改／刪除任何排程工作，未改動 repo 內
   任何既有檔案。唯一寫入＝本檔。
2. **未提權** ⇒ Security 日誌內容、稽核政策、`System32\Tasks` 枚舉三者**未量到**，本報告
   對其內容不作任何斷言（含「沒有 4698/4699 事件」這種斷言——那正是禁止的那一句）。
3. **`b13f4527` 的狀態塊檔已不存在**（`autosdd_resume_plan_b13f4527-….md`）⇒ 該 session
   當時狀態塊裡 `allow_resume` 的**逐字值未直接量到**。§3.4 的結論是由三項實測合成：
   (a) `AUTOSDD_RESUME_OFF=1` 在 User 層持久環境；(b) 源碼 :956/:1015/:1329 的傳遞鏈；
   (c) 同機制**現存活**哨兵的狀態塊實測為 `"allow_resume": false`。這是**強推論**，
   不是直接觀測——若要升級為直接觀測，需在下一次事件發生前保全狀態塊。
4. **哨兵的 `sentinel_armed` 痕跡不記 `allow_resume`**（`:1333` 只記 task／credential／
   handled_through；記 `allow_resume` 的 `:1064` 屬 `_arm_endurance` 另一條路）⇒ 從痕跡
   **無法**回答「這支哨兵武裝時允不允許續跑」。這是取證面的具體缺欄，建議補。
5. **`Microsoft-Windows-Kernel-Power` 查無事件**這一句在本報告中被當成可信的「量到零」，
   理由是同一 `System` 日誌在非提權下可讀（與 §2.2 的 Security 不同）；睡眠假說的**主要**
   否證仍是「其他排程工作全程正常執行」這個正面證據，不倚賴該負面結論。
6. **未回答「為什麼 `AUTOSDD_RESUME_OFF=1` 被設在 User 層」**——那是掌舵者機器的環境事實
   （可能正是 R107 註 #2「headless 續跑窗口許可層不足」的手動應對）。本報告只指出它的
   後果，不裁決該設定該不該存在；那是 R108 §4.3 之外的架構議題（安全 vs 自動化）。
7. **`AutoSDD_SessionResume_e7013c46` 於 14:58:35 被刪**（141）——與本案哨兵死亡是不同事件，
   本報告未追查其歸因。
