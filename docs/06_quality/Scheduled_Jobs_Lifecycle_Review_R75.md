# Windows 排程 Job 生命週期複查（R75 / SA）

| 欄位 | 內容 |
|------|------|
| 角色 | SA（系統分析），**唯讀分析**（除本檔外零改動） |
| 日期 | 2026-08-04 |
| 觸發 | 掌舵者提問：兩支 Job「還有需要嗎／測完了嗎／能不能加速結束」 |
| 載具 | PowerShell 工具（PS 5.1 引擎經 `powershell.exe`）＋ Read/Grep；排程一律 `Get-ScheduledTask`（不用 `schtasks /query`，本機對這批工作回空＝假陰性） |
| 引用政策 | 本檔所有數字皆為**當回合真跑**輸出，逐項附指令。行號為 2026-08-04 實查值 |

---

## 0　一頁結論

> 🔴 **本檔撰寫期間（2026-08-04 22:30~22:34）今晚的 nightly 就跑完了**，四軌數字與 `.g0_readiness.json` 憑證均已更新。本節與 §2.1.4／§6 為**跑完後**的值。

> ## 🔴 R76 全域訂正（2026-08-05）— 讀本檔任何日期／筆數之前先讀這一塊
>
> R76 對這份檔案動了兩件事，使**全文所有 GA 終點日期與「差 N 筆」都已作廢**。原文
> 一律逐字保留為 R75 時代快照（樹裡不重述被推翻的話，但也不改寫史料），現況以本塊為準：
>
> 1. **兩支 GA 判準被收緊**（PKG-D／R76-13：新增 staleness ＋ 窗內連續性 span ≤ 40 天）。
>    方向正確、**不得放寬**。代價：obs 由 `ready` 翻成 `sparse`（rc 1）、drift 亦 `sparse`。
>    **G0 四軌現況＝mutation ✅／AC4 ✅／obs ❌(sparse)／drift ❌(sparse)。**
>    新終點＝**再連續進帳 obs 17 晚（最早 2026-08-21）／drift 18 晚（最早 2026-08-22）**。
>    全文出現的「差 2 筆」「最快 2026-08-06 夜」「2 晚後」「另三軌已全綠」一律以此取代。
>    綁住兩軌的是 **span 不是筆數**——補筆數沒有用，要的是**不中斷**。
> 2. **E3 已達標**：掌舵者提權完成，`check_scheduled_task_drift.py` 實測 `status=ok`／rc=0，
>    且該判準已改為逐任務量測（不再結構性不可滿足）。`AutoClaude_WindowsSmoke` 的
>    **三條退出判準現在全數成立**，剩下的只有 PM 拍板（見 §2.2.6 三段表的第 ② 段）。
>
> 現查配方（不要相信本檔任何一個數字，跑一次）：
> `python AutoClaude/tools/observability_ga_check.py --json`、
> `python AutoClaude/tools/drift_log_ga_check.py --json`、
> `python tools/check_scheduled_task_drift.py --json`。

> ## 🔴 R76 收尾二次訂正（2026-08-06）— 上一塊的第 2 點已被同一天的一個事件推翻
>
> 上面那塊寫於 2026-08-05 白天，當時 E1（雲端主通道活著）確實成立。**當天晚上它就不成立了。**
> 原文一律逐字保留，不改寫；本塊為現況。
>
> **事件（2026-08-05T16:05:50Z）**：對 `windows-compat-ci.yml` 的一次 `workflow_dispatch`
> （run `31023606162`）三個 job 全部 `conclusion=failure`、`steps` 長度 0、2~4 秒結束，
> annotation 逐字 `The job was not started because recent account payments have failed or
> your spending limit needs to be increased`。同一個 sha 的 push run 在 21 分鐘前還全數
> success ⇒ **Actions 額度是在這中間耗盡的**。立帳 `DEF-101-866`（`DEF-101-081` 同型復發）。
>
> **對本檔三處結論的影響**（只列影響，不改寫上面的原文）：
>
> | 本檔原結論 | 現況 |
> |---|---|
> | §0 第 2 點「三條退出判準現在全數成立，剩下只有 PM 拍板」 | **E1 不成立** ⇒ 不是 3/3。**沒有可拍板的退場**；`AutoClaude_WindowsSmoke` **維持每日** |
> | §2.2.3 E1 欄「達標」／§2.2.4「主通道已經復活」 | 主通道**又倒了一次**。E1 逐字要求「近 30 天零筆 billing／startup_failure 類」，現在有一筆 |
> | §2.2.6 段 ②「PM 拍板退場或降頻」 | **不到拍板時點**，前置條件回到未滿足 |
>
> **E1 要重新成立的兩個必要條件（缺一不可）**：① 掌舵者在 GitHub `Billing & plans`
> 恢復額度；② 此後 30 天的窗口內不再出現同類事件。**判準本身一個字都不用改**——
> 它問對了問題，而且今天問出了答案。
>
> 🔴 **量測配方要補一步**（判準對，但 §2.2.3 那條 `gh run list` 量不到它）：billing 事件在
> run 層的 `conclusion` 就是普通的 `failure`，與「測試真的紅了」逐字同形 ⇒ 只看 run list
> 分不出兩者。必須下沉到 job 層與 annotation，**兩個特徵同時成立**才判定為 billing 類：
>
> ```powershell
> gh api repos/:owner/:repo/actions/runs/<runId>/jobs --jq '.jobs[].steps|length'
> #   ⇒ 0 代表工作根本沒開始，不是跑到一半失敗
> gh api repos/:owner/:repo/check-runs/<jobId>/annotations
> #   ⇒ 訊息含 payments have failed 或 spending limit
> ```
>
> 🔴 **順帶：這件事替 §2.2.3 末那段雙向反證投下第一張實票。** 該段的結論是「判準要綁在
> **主通道活性**（E1）而不是綁在**發現數**上」。今天，補償控制立案的原始情境（雲端帳務
> 停擺 ⇒ Windows 側零執行級訊號）**正在重演**——若當初綁的是「連續 N 天零發現就撤」，
> 這支排程早已被撤掉，而被撤掉的正是主通道倒下時唯一還活著的那條通道。**綁對象選對了。**

| Job | 性質 | 測完了嗎 | 距終點 | 建議 |
|---|---|---|---|---|
| `AutoClaude_Nightly` | **混合**：觀察期採集＝階段性（有終點）＋ local_ci_gate／perf／chaos＝常態回歸（無終點） | **非常接近**。四軌中 3 軌已達標，只剩 drift GA `28/30`〔R76：見上方訂正塊，現為 2 軌未達標〕 | **2 筆紀錄**（＝2 個 UTC 日）⇒ 最快 **2026-08-06 夜**〔R76：見上方訂正塊，現為 17／18 晚〕 | **保留、先不動**。四軌全綠後 PM 拍板 → **降頻（例如每週）而非移除** |
| `AutoClaude_WindowsSmoke` | **補償控制**（雲端 CI 帳務停擺期間的替代通道），**有正式退出判準** | 退出判準 3 條中 **2 條已達標**，唯一卡點是排程設定漂移〔R76：3 條全數達標，見上方訂正塊〕〔🔴 R76 收尾：**E1 已於 2026-08-05 因帳務事件失效 ⇒ 現為 2/3**，見上方第二個訂正塊〕 | 一條提權指令〔R76：已執行完畢〕〔R76 收尾：距終點回到「額度恢復 ＋ 其後 30 天無同類事件」〕 | 先修設定；之後**可退場**，但退場是一輪 code 工作（見 §5 D-4），不是刪個工作了事。折衷建議先降頻〔🔴 R76 收尾：**維持每日、不得退場**〕 |

🔴 **最省力的加速手段不是改判準，是修排程設定**（§3）：`ExecutionTimeLimit=PT72H` ＋ `MultipleInstancesPolicy=IgnoreNew` 這組合在 2026-08-02 已經吃掉一整天的三軌進帳一次；drift **只剩 2 筆**，再被吃一次終點就往後推好幾天。

✅ **§2.1.4 的預測已於同一 session 內被今晚的 nightly 證實**：08-03 那輪印的 `ac4=False`、`obs_ga=TOOL-ERROR` 兩筆假訊號，在 08-04 這輪已變成 `ac4=True`、`obs_ga=True`。**不要拿 08-03 那份 log 當現況。**

🔴 **今晚 nightly exit=1，但與觀察期無關**：唯一失敗的 stage 是 `local_ci_gate`，根因是**本輪其他 agent 未 commit 的編修踩到根層護欄檔的行數棘輪**（`tools/archive_defect_log.py` 1511>1507、`tools/check_defect_log_crossref.py` 1479>1474），並連帶讓 4 支 LOC 預警帶測試轉紅。四個觀察期軌道的 stage **全部 exit=0**。詳見 §6。**這一筆恰好就是「這支 Job 還有沒有用」的當場答案：它在 3 分 13 秒內抓到了當下正在發生的紅。**

---

## 1　現況取證

### 1.1 存在哪幾支

```powershell
Get-ScheduledTask | Where-Object TaskName -like 'AutoClaude*' | Select-Object TaskName,State,TaskPath
```
```
TaskName                State TaskPath
--------                ----- --------
AutoClaude_Nightly      Ready \
AutoClaude_WindowsSmoke Ready \
```

⇒ **恰好兩支，與掌舵者所列一致**。第三支 `AutoClaude_SD09_G0_GateCheck` 已於 R71 從本機移除（腳本保留），本次實查確認不在列。`tools/scheduled_task_expectations.json` 的對照組也恰好列這兩支 ⇒ **任務清單層面對照組與現場一致**。

### 1.2 心跳（LastRun / LastResult / NextRun）

```powershell
Get-ScheduledTask -TaskName 'AutoClaude_Nightly','AutoClaude_WindowsSmoke' | Get-ScheduledTaskInfo |
  Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime,NumberOfMissedRuns
```

**取證時點① — 2026-08-04 約 21:5x（今晚 nightly 觸發前）**

| Job | State | LastRunTime | LastTaskResult | NextRunTime | MissedRuns |
|---|---|---|---|---|---|
| `AutoClaude_WindowsSmoke` | Ready | 2026/8/3 23:54:40 | **0** | 2026/8/4 23:30:00 | 0 |
| `AutoClaude_Nightly` | Ready | 2026/8/3 22:30:01 | **0** | 2026/8/4 22:30:00 | 0 |

**取證時點② — 2026-08-04 22:34（今晚 nightly 跑完後，同一 session 內）**

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File '<repo>\tools\install_windows_nightly.ps1' -Status
```
| Job | State | LastRunTime | LastTaskResult | NextRunTime |
|---|---|---|---|---|
| `AutoClaude_Nightly` | Ready | **2026/8/4 22:30:01** | **1** ← 見 §7 | 2026/8/5 22:30:00 |
| `AutoClaude_WindowsSmoke` | Ready | 2026/8/3 23:54:40 | 0 | 2026/8/4 23:30:00 |

⇒ **兩支都活著、都有下次執行時間**，不是「排了但沒排進去」。`AutoClaude_Nightly` 今晚 `LastTaskResult=1`＝真的抓到紅（根因與觀察期無關，§7）。

> **附帶取證**：`install_windows_nightly.ps1 -Status` 自身 `rc=0`（＝整組任務都存在），且它會逐項印出期望值對照——與 §3 的比對器結論一致（nightly 2 項、smoke 3 項不符）。兩個獨立載具互證，非單一來源。

### 1.3 Trigger / Action / Settings 實機值

| 項目 | AutoClaude_Nightly | AutoClaude_WindowsSmoke |
|---|---|---|
| Trigger | Daily 22:30（StartBoundary `2026-05-20T22:30:00`） | Daily 23:30（StartBoundary `2026-07-31T23:30:00+08:00`） |
| Execute | `powershell.exe` | `powershell.exe` |
| Arguments | `-NoProfile -ExecutionPolicy Bypass -File d:\CursorProject\AISDCL_Agent\AutoClaude\tools\run_local_nightly.ps1` | `-NoProfile -ExecutionPolicy Bypass -File "D:\CursorProject\AISDCL_Agent\tools\windows_smoke_local.ps1"` |
| WorkingDirectory | `d:\CursorProject\AISDCL_Agent\AutoClaude` | （空） |
| WakeToRun | **True** ✅ | **True** ✅ |
| StartWhenAvailable | **True** ✅ | **True** ✅ |
| DisallowStartIfOnBatteries | **False** ✅ | **False** ✅ |
| StopIfGoingOnBatteries | **False** ✅ | **False** ✅ |
| ExecutionTimeLimit | **PT72H** ❌（期望 PT4H） | **PT72H** ❌（期望 PT4H） |
| MultipleInstances | **IgnoreNew** ⚠️（期望 StopExisting） | **IgnoreNew** ⚠️（期望 StopExisting） |
| Enabled | True | True |

> 記憶檔的**四項關鍵設定**（`WakeToRun`／`StartWhenAvailable`／`DisallowStartIfOnBatteries=false`／`StopIfGoingOnBatteries=false`）**兩支都已正確**。本次漂移落在 R69 補的另外三項（見 §3）。
> ⚠️ 附帶觀察：`WakeToRun=True` 在本機**實測失效**（R71：近 10 天 6 筆 Power-Troubleshooter 事件 1 的 `WakeSourceType` 全為 `0\Unknown`），需 `powercfg` 開啟電源計畫的喚醒計時器。掌舵者把時刻改到 22:30／23:30「確保開機中」正是對這件事的有效繞道，**不必回頭處理**。

---

## 2　逐支 Job：目的／性質／終止條件／能否加速

### 2.1　`AutoClaude_Nightly`

#### 2.1.1 目的（白話一句）

**每晚跑一次 7 stage 的深度回歸，同時它是 SD_09 三個觀察期 ＋ observability GA 的唯一採集器**——那四軌的證據就只有這支在寫。

權威出處：`AutoClaude/tools/run_local_nightly.ps1:1-14`（`.SYNOPSIS` / `.DESCRIPTION`）

```
  - local_ci_gate 全套（Stage L）          — R9：push 空窗期每日全套訊號
  - mutation-test (Docker / Linux mutmut) — 觀察期 #1
  - pg-e2e-nightly + AC4 collector        — 觀察期 #2
  - perf-baseline-nightly                  — 補強信號
  - drift_log 被動掃描                     — 觀察期 #3
  - observability-snapshot                 — D-16 30 天取證
  - sdd-fsm-chaos                          — Rule 9.9.4 本地補償（CI 停擺期間）
```

#### 2.1.2 性質：**混合**——不能一句話回答「有沒有終點」

| stage | 性質 | 有終點嗎 |
|---|---|---|
| mutation（觀察期 #1） | 階段性 | ✅ 已達標（baseline 已鎖） |
| pg-e2e + AC4 collector（觀察期 #2） | 階段性，但**有新鮮度要求** | ✅ 已達標，🔴 但停止採集 30 天後會自動翻回未達標（見 2.1.6） |
| drift_log（觀察期 #3） | 階段性 | ⏳ `27/30` |
| observability-snapshot（D-16） | 階段性 | ✅ 已達標 `43/30` |
| local_ci_gate（Stage L） | **常態回歸監控** | ❌ 無終點 |
| perf-baseline | **常態回歸監控** | ❌ 無終點 |
| sdd-fsm-chaos | **常態回歸監控**（CI 停擺期補償） | ❌ 無終點 |

#### 2.1.3 終止條件的權威定義在哪裡

🔴 **誠實揭露：這支 Job 沒有像 smoke 那樣的正式「退出判準」段落。** 全檔 grep `退出判準｜退場｜終止條件` 只命中兩處，都不是 Job 層的退場判準：

| 位置 | 內容 | 是不是 Job 退場判準 |
|---|---|---|
| `run_local_nightly.ps1:563` | 「對**退出判準**的增益精確為 0」 | ❌ 指的是 mutation 鎖定的判準，不是 Job |
| `run_local_nightly.ps1:1780-1784` | 四軌全綠時 `recommended_action = 'PM 拍板執行 G0 動作清單，並評估把觀察期 stage 降頻／退場（ADR-SD09-012 §7 / SD_Improving_09 W0）'`；否則 `'維持每晚採集；gaps 清空前不得降頻（降頻會讓觀察期永遠到不了）'` | ⚠️ **這是目前最接近的東西** |

⇒ **實質終止條件＝「G0 四軌全綠 → PM 拍板」**，且 R74 已把它機械化成一份憑證：

- `run_local_nightly.ps1:1742-1759` — 每輪都寫 `.g0_readiness.json`（落點 `AutoClaude/.g0_readiness.json`），帶 `generated_at` / `ready` / 四軌 detail / `gaps` / `recommended_action`。
- 該檔頭註解自己寫明了立案理由：**「使用者問的『這測試測完了嗎、能不能結束』之所以問了三輪還沒答案，機械成因就是達標事件沒有留下任何可查詢的狀態，只留在一份 14 天後就會被輪替刪掉的 log 裡。」**
- ✅ **實查：第一份憑證已於本檔撰寫期間產生**（今晚 22:33 的 nightly 寫入）。**掌舵者從此只要讀這一個檔就能回答「測完了沒」：**

```powershell
Get-Content 'D:\CursorProject\AISDCL_Agent\AutoClaude\.g0_readiness.json' -Encoding utf8
```
```json
{
    "schema_version": 1,
    "generated_at": "2026-08-04T14:33:13Z",
    "run_id": "223001",
    "ready": false,
    "tracks": {
        "mutation": { "ok": true, "pass": true,
                      "detail": "should_lock=True; baseline=0.7071; tail unique-sha 5/7; records=7" },
        "ac4":      { "ok": true, "pass": true, "status": "ready",
                      "green_streak": 44, "green_streak_required": 14,
                      "staleness_days": 0, "staleness_max_days": 30 },
        "obs":      { "ok": true, "pass": true,
                      "detail": "[PASS] (status=ready; rc=0; green_streak=44/30)" },
        "drift":    { "ok": true, "pass": false,
                      "detail": "not passed (status=observing; rc=1; green_streak=28/30; W1 入場歸屬待 PM 裁示——本載體 fail-closed 視為阻塞)",
                      "w1_entry_ownership": "pending-PM-ruling; carrier fail-closed treats it as blocking" }
    },
    "gaps": ["drift_log GA green_streak 28 < window 30（採集失敗＝table_missing 也會打斷 streak，未必是真漂移事件）"],
    "recommended_action": "維持每晚採集；gaps 清空前不得降頻（降頻會讓觀察期永遠到不了）"
}
```

⇒ **`ready=false`，`gaps` 只有一項，就是 drift 差 2 筆。** 憑證自己也記下了 §2.1.6 末提到的判準衝突（`w1_entry_ownership: pending-PM-ruling`）——載體選 fail-closed 把 drift 當阻塞，**但那是待 PM 裁示的事，不是既定事實**。

#### 2.1.4 距離終點多遠（四軌逐軌實測）

指令（`AutoClaude/` 下，`.venv` python）：

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
& '<repo>\.venv\Scripts\python.exe' tools\ac4_progress_check.py --json
& '<repo>\.venv\Scripts\python.exe' tools\observability_ga_check.py --json
& '<repo>\.venv\Scripts\python.exe' tools\drift_log_ga_check.py --json
```

| 軌 | 權威工具 | 22:30 前實測 | **22:34 實測（今晚 nightly 後）** | rc | 狀態 |
|---|---|---|---|---|---|
| #1 mutation | `mutation_baseline_lock.should_lock` | `locked=True  baseline=0.7071428571428572  records=7` | 同（源碼未動，stage 依 R74 邏輯 `SKIP`） | 0 | ✅ **達標（baseline 已鎖）** |
| #2 AC4 | `tools/ac4_progress_check.py` | `status=ready  green_streak=43/14  staleness=0/30` | `status=ready  green_streak=**44**/14  staleness_days=0/30  ready_for_labeled_pr=true` | **0** | ✅ **達標** |
| obs GA | `tools/observability_ga_check.py` | `status=ready  43/30  total=43` | `status=ready  green_streak=**44**  window=30  total_records=44` | **0** | ✅ **達標** |
| #3 drift GA | `tools/drift_log_ga_check.py` | `status=observing  27/30  total=36` | `status=observing  green_streak=**28**  window=30  total_records=37` | **1** | ⏳ **唯一未達標，差 2 筆** |

mutation 軌實測逐字（向權威模組現場提問，不自行重算）：
```
{"locked": true, "baseline": 0.7071428571428572, "records": 7,
 "tail7_shas": [null, null, "5208cff397beecc5", "20940e1b903dc19d",
                "4af78567437894af", "55013d0a916f814e", "5a44cbba2d95ce2f"]}
rc=0
```

**⇒ 只差 drift 一軌、只差 2 筆紀錄。**

> 🔴 **R76 就地訂正（上表 R75 欄位逐字保留為時代快照；本塊才是現況）**：本輪 PKG-D 依
> R76-13 **收緊了兩支 GA 判準**（新增 staleness ＋ 窗內連續性：last-30 筆的日曆跨度必須
> ≤ 40 天）。方向正確、**不得放寬**，但代價是上表兩列同時失效：
>
> | 軌 | R75 欄（上表） | **R76 現查實測** | rc |
> |---|---|---|---|
> | obs GA | `status=ready 44/30` ✅ 達標 | `status=sparse green_streak=44/30 span=58/40 max_gap=12d` ❌ **由達標翻回未達標** | **1** |
> | #3 drift GA | `status=observing 28/30`（⏳ 差 2 筆） | `status=sparse green_streak=28/30 span=65/40 max_gap=12d` ❌ | **1** |
>
> 🔴 **「差 2 筆」這個心智模型整個作廢**：綁住兩軌的不再是 `green_streak`，而是 **span**。
> drift 就算把那 2 筆補滿，span 仍約 63 天、照樣 sparse。新的終點是**再連續進帳**：
> **obs 17 晚（最早 2026-08-21）／drift 18 晚（最早 2026-08-22）**，前提是每晚 22:30
> 排程不漏跑。此值以兩支工具的判準公式對現有帳本日期獨立試算所得（`window_span_days`
> 由 58／65 降到 39／40 的那一步），非估算；重算配方＝以 last-30 的日曆跨度逐日模擬。
> ⚠️ `AutoClaude/.g0_readiness.json` 是每晚重生的量測檔，可能**早於**本次判準變更
> （讀之前先看它的 `generated_at`）；今晚 nightly 跑完它會自己把 obs 翻成 `pass=false`。

🔴 **兩筆「已修好但線上還沒反映」的假訊號**——這是為什麼看 log 會以為離終點還很遠：

`logs/nightly_2026-08-03_223001.log` 的 `[G0-NOT-READY]` 行印的是：
```
mutation=True (should_lock=True; baseline=0.7071; tail unique-sha 5/7; records=7)
ac4=False (ready=False; 9/14 rolling-window-days)
obs_ga=False (TOOL-ERROR:無效的 JSON 基本型別: ython.bat : [observability_ga_check] WARN: ...)
```

| 假訊號 | 真相 | 修復 commit | 修復時間 vs 那輪 nightly |
|---|---|---|---|
| `ac4=False (9/14)` | ADR-SD09-012 的 gap-tolerant 判準（`green_streak 43/14`）已拍板並落地 → 實測 `status=ready` rc=0 | `a371068` | 2026-08-04 **09:57**，晚於 08-03 22:30 |
| `obs_ga=TOOL-ERROR` | **假未達標**。工具真實答案是 `status=ready 43/30` rc=0。成因：`observability_ga_check.py` 每次把 legacy-record WARN 印到 **stderr**（本檔實測：`2>$null` 後 WARN 消失 ⇒ 確為 stderr），`2>&1` 合流後 PS 5.1 把它包成 `python.bat : ...` 的 ErrorRecord，舊濾法「見到第一個 `{` 之後全收」把它接到 JSON 尾巴 → `ConvertFrom-Json` 當場炸（DEF-101-775） | `68028fa` | 2026-08-04 **00:51**，晚於 08-03 22:30 |

修法已在 `Get-ObsGaPass`（`run_local_nightly.ps1:766-773`）與 `Get-DriftGaPass`（`:835-842`）落地＝「收到第一個能成功 parse 的 JSON 就停」。

⇒ 預測：**今晚 22:30 那輪，是第一輪會同時印出 mutation／ac4／obs 三軌全綠的 nightly。**

✅ **預測已於同一 session 內被證實**（`logs/nightly_2026-08-04_223001.log:482` 逐字）：

```
[G0-NOT-READY] mutation=True (should_lock=True; baseline=0.7071; tail unique-sha 5/7; records=7)
               ac4=True (ready=True (status=ready; staleness_days=0/30); gate 44/14 green_streak; 10/14 rolling-window-days)
               obs_ga=True ([PASS] (status=ready; rc=0; green_streak=44/30))
               drift_ga=False (not passed (status=observing; rc=1; green_streak=28/30; W1 入場歸屬待 PM 裁示——本載體 fail-closed 視為阻塞))
             — gaps: drift_log GA green_streak 28 < window 30
```

**兩筆假訊號都不見了**（`ac4=False`→`True`、`obs_ga=TOOL-ERROR`→`True`），且 `ac4` 那行同時印出新舊兩個口徑（`gate 44/14 green_streak` 與 `10/14 rolling-window-days`），ADR-SD09-012 L-4 選 (a) 語意凍結的效果在此可見——**不再有 §2.8 那種「41/14 看起來超標三倍」的誤導**。

#### 2.1.5 drift 為什麼是 28 而不是 37 —— 卡住的是「採集失敗」，不是漂移事件

實測（`.drift_log_history.jsonl`，**今晚 nightly 前的 36 筆**逐列；跑完後為 37 筆／`green_streak=28`，結構不變）：

```
total 36
failing: [(8, '2026-06-02T18:00:51+00:00')]
last5: ['2026-07-29T18:04:30+00:00', '2026-07-30T18:07:01+00:00',
        '2026-08-01T02:23:20+00:00', '2026-08-02T18:04:30+00:00',
        '2026-08-03T14:34:56+00:00']
dup utc dates: []          <- 36 筆分佈在 36 個不同 UTC 日期，零重複
green tail count: 27
```

- **全部紀錄的 `severity_non_info_count` 皆為 0** ⇒ 真實漂移事件數＝**零**。
- 唯一那筆 `passed=false` 是**第 9 筆（`2026-06-02T18:00:51+00:00`）**，原因是 `drift_log_table_exists=false`（alembic head 落後）＝**採集失敗**，不是漂移事件。判準定義 `passed = table_exists AND non_info_count == 0`（`tools/drift_log_snapshot.py:55`）把兩件事混在一起，所以它把 streak 歸零。
- 該根因**已不存在**（ADR-SD09-012 §1.1 訂正框：`alembic_version = 0018_version_kind_discriminator` = 鏈頭），其後 **28 筆全綠**（今晚再 +1）。
- **也就是說：`green_streak` 這個分子被一筆兩個月前的採集故障壓著，而那故障的成因早已修掉。**

#### 2.1.6 能不能加速？（掌舵者要的是「讓階段性驗證早點結束」）

**先確認終止條件有沒有綁在日曆天數上——這是本 repo 已經被咬過兩次的病（ADR-SD09-011 mutation 軌、ADR-SD09-012 AC4 軌）。**

答案：**drift 軌沒有綁日曆連續（它是 gap-tolerant streak，缺口不會歸零），但綁了「一天最多一筆」**：

- `tools/drift_log_snapshot.py:10`（設計原則）＋ `:70` / `:90`（`_utc_date` 比對）：**同 UTC date 去重**。
- 實測佐證：36 筆零重複 UTC 日期（上方 `dup utc dates: []`）。

⇒ **2 筆 = 2 個不同 UTC 日，這是硬下限，跑幾次都一樣。**

| 加速手段 | 效果 | 評估 |
|---|---|---|
| ~~A. 今天先補一筆~~ | ~~今天（08-04 UTC）還沒有紀錄，手動 `Start-ScheduledTask` 即入帳~~ | ✅ **已自動完成**——今晚 22:30 的排程觸發已把 08-04 那筆入帳（`27→28`）。**本項已無需人工動作** |
| **B. 修排程設定**（§3，需提權） | 08-02 那個空桶就是 `PT72H + IgnoreNew` 造成的（`logs/nightly_2026-08-01_101807.log` 跑了 **35.6 小時**：08-01 10:18 → 08-02 21:54，在 PT72H 額度內存活，`IgnoreNew` 把 08-02 的觸發整個丟掉 ⇒ UTC 08-02 三軌零進帳） | ✅ **最高優先，且是現在唯一還有意義的加速動作**。剩 2 筆時再被吃一次，終點就從 08-06 推到 08-08+ |
| C. 提高觸發頻率（每小時等） | **負收益，已被實測否決**（ADR-SD09-012 §2.3／§2.4）：720 次/月產出 ≤ 30 筆（效率 4.2%）、多燒 89 h/月 CPU，且 last-write-wins 讓「當天最後一次抖動毀掉整天」的機率上升 24 倍 | ❌ 不做 |
| D. 加 logon/startup trigger | 反事實模擬 7 → 10/14，到不了門檻；且那 +3 是靠鑽 UTC 桶邊界（本地 08:00）換來的，ADR 明指是漏洞不是特性（§2.6） | ❌ 不做 |
| **E. ADR 級：把「採集失敗」與「漂移事件」分開判定** | drift 立刻變 `37/30` → **當場達標**。這與 ADR-SD09-011／012 是**同一個病的第三次復發**（判準量到的不是它想證明的東西） | ⚠️ **技術上成立，但不建議**——自然路徑只剩 **2 天**，為 2 天開一份 ADR 級判準變更（含反作弊論證＋雙向鑑別力取證＋PM signoff）不划算。**若這 2 晚 drift 又被任何原因打斷，此路應立刻啟用** |

**⇒ 加速結論：只做 B，不動判準。最快達標日＝2026-08-06 夜（08-05／08-06 兩個 UTC 日各補一筆），前提是那兩晚 22:30 機器開著。**

> 🔴 **R76 訂正上面這一行與下面那一段（兩句都已被本輪自己推翻）**：
> ① **最快達標日不是 08-06**。PKG-D 收緊判準後綁住兩軌的是 span 不是筆數，新終點＝
>    **obs 最早 2026-08-21／drift 最早 2026-08-22**（見 §2.1.4 的 R76 訂正塊）。
>    加速手段 B（修排程設定）仍是唯一有效的，且**現在更重要**——連續性本身成了判準，
>    中間漏一晚就會把 span 推回去。
> ② **「另三軌已全綠 ⇒ W1 現在就可以啟動」已不成立**：obs 也翻成 sparse 了。現況＝
>    mutation ✅／AC4 ✅／obs ❌(sparse)／drift ❌(sparse)。若 PM 裁定 drift 非 W1 入場
>    條件，**還是要等 obs**（最早 08-21）。這一句原本是一張綠燈，本輪把它弄假了，
>    故在此就地標紅而不是留著讓人照做。
> ③ 加速手段 **E（把採集失敗與漂移事件分開判定）** 的成本效益也翻轉了：原文以「自然
>    路徑只剩 2 天」否決它，而現在是 17～18 天。**若 PM 要縮短，E 值得重新評估**——
>    但它治的是 `green_streak`，對 span 這一半無效，所以單靠 E 仍到不了終點。
>
> ⚠️ 一項判準衝突，順便呈報 PM：`run_local_nightly.ps1` 的 G0 閘門是
> `mutation AND ac4 AND obs AND drift` **四軌全要**；而 ADR-SD09-012 §1.1 寫 drift
> 「**非 W1 入場阻塞項**（歸屬待 PM 裁定），但 W5 雙條件角色不受影響」。這一項仍然
> 只需要拍板、不需要改判準——但拍板的輸入請用上面 ② 的現況，不是本段原文。

#### 2.1.7 處置建議：**保留，先不動；2 晚後降頻，不要移除**

| 建議 | 理由 |
|---|---|
| 現在：**保留每日** | drift 只剩 2 筆；今晚憑證的 `recommended_action` 逐字：「維持每晚採集；gaps 清空前不得降頻（降頻會讓觀察期永遠到不了）」 |
| 2 晚後四軌全綠：**PM 拍板 → 降頻（例如每週）** | 見下四點 |
| **不要移除** | 見「移除會失去什麼」 |

**為什麼是降頻而不是移除（四點）：**

1. 🔴 **AC4 有新鮮度判準。** `STALENESS_MAX_DAYS = 30`（ADR-SD09-012 L-7／§7.6 S4 決策）。實測目前 `staleness_days=0/30`。**停止採集 30 天後，AC4 會自動翻成 `status=stale` / `ready=False`**——不是「達標了就永久達標」。R74 落地時的雙向取證逐字：`STALE(-400d) rc=1 status=stale green_streak=43/14 staleness_days=400 ready=False`。⇒ 要維持 W1 入場憑證有效，**至少每 30 天要有一筆 AC4 紀錄**。
2. **drift／obs 都是 gap-tolerant streak**（容缺口），每週跑照樣累積，不會因為降頻而歸零。
3. **mutation stage 的成本已自動歸零。** R74 已在 `run_local_nightly.ps1:558-621`（`Get-MutationRetestNeeded`）加上「已鎖定 **且** 當前源碼 sha 已量過 → 跳過」。該 stage 原佔整輪 53%（4m05/7m45），源碼不動時現在自動省掉。反作弊不鬆動：兩條件任一不成立就照跑。
4. **local_ci_gate／perf／chaos 三支沒有終點**，它們是常態回歸訊號；降頻是取捨、移除是砍掉訊號。

**移除會失去什麼（具體清單）：**

1. AC4 觀察期 30 天後轉 `stale` → W1 入場憑證失效（見上 1）。
2. drift GA 永遠停在 `27/30`，永不達標。
3. observability GA 的 D-16 「30 天取證」斷鏈。
4. 每日一次的本機全套訊號（pytest ＋ `check_loc_budget` ＋ `lint-imports`，Stage L）。
5. perf baseline 漂移偵測（sub-ms 量級，只有這裡在乾淨環境量）。
6. `sdd-fsm-chaos` 的本機補償（Rule 9.9.4）。
7. `.g0_readiness.json` 不再更新 ⇒ 「該停了 / 該重啟了」再度變成「要有人記得去讀 log」——正是 R74 立這份憑證要消滅的狀態。

---

### 2.2　`AutoClaude_WindowsSmoke`

#### 2.2.1 目的（白話一句）

**Windows 側的便宜 tripwire**：88 秒內把雲端 `windows-compat-ci` 的 12 個 PASS 點在本機跑一遍（.ps1 語法解析四棵樹、三支 hook 安裝器的安裝／解除往返、linked worktree 拒絕、中文路徑編碼防護、`-Command` 非典型呼叫鏈、兩支平台無關 checker、nightly 安裝器 `-WhatIf` 預覽）。

權威出處：`tools/windows_smoke_local.ps1:1-57`（檔頭與 9 個步驟清單）。

#### 2.2.2 性質：**這支有正式退出判準，而且它把兩件事分開**

🔴 權威出處：`tools/windows_smoke_local.ps1:89-127`（R74 新增；檔頭原文自陳「此前全庫查不到任何一條，這是它至今無法結束的直接原因」）。

| 對象 | 性質 | 退出判準 |
|---|---|---|
| **(甲) 腳本本身** `tools\windows_smoke_local.ps1` | 常態工具 | **永久保留、無退出判準**。理由（原文）：「它的價值是『push 前／離線時能在 88 秒內知道有沒有壞』，這個價值與雲端 CI 活不活著無關」 |
| **(乙) 每日排程任務** `AutoClaude_WindowsSmoke` | **補償控制**（R60 為雲端 CI 帳務停擺 DEF-101-081 期間「Windows 側零執行級訊號」而建） | ✅ **有**。「補償控制的存在理由是主通道死了，所以它有退出判準：**主通道復活即退場**」——三條 E1/E2/E3 全部成立才可移除 |

⇒ **掌舵者問的「這個測試的目的為何、能不能結束」，對 (甲) 的答案是「不會結束，這是設計」；對 (乙) 的答案是「可以結束，判準寫在 `tools/windows_smoke_local.ps1` 的退出判準段」（R76 起刻意不寫死行號——R76 PKG-D 改寫該段後行號已位移，寫死的引用會指向別的文字）。這兩件事此前被混為一談，正是它一直問不出答案的原因。**

#### 2.2.3 三條退出判準逐條實測

| 條 | 判準原文（`tools/windows_smoke_local.ps1` 退出判準段；R76 起不寫死行號） | 本輪實測 | 結論 |
|---|---|---|---|
| **E1** | 雲端主通道活著：`windows-compat-ci` 近 30 天 ≥ 20 個 run，且零筆 conclusion 屬 billing／startup_failure 類 | `gh run list --workflow windows-compat-ci.yml --limit 40 --json createdAt,conclusion,status`：<br>`total_runs=40`，跨度 `2026-07-25 16:21Z ~ 2026-08-04 02:04Z`（**10 天內 40 run**）<br>`success=8  failure=32`<br>`non_completed_status=0`<br>`billing_or_startup=0`（無 `startup_failure`／`action_required`／`null`） | ✅ **達標** |
| **E2** | 本腳本每一項都有雲端對應 step（`tools/tests/test_smoke_ci_sync.py` 步驟語意鎖為綠＝零 smoke-only 項目） | `pytest tools/tests/test_smoke_ci_sync.py -q` → `23 passed, 1 skipped, 2 subtests passed`，**rc=0** | ✅ **達標** |
| **E3** | 移除後 Windows 側仍有每日執行級心跳：`AutoClaude_Nightly` 存在且 `tools/check_scheduled_task_drift.py` 回 rc=0 | `AutoClaude_Nightly` 存在 ✅（§1.1）；但 `check_scheduled_task_drift.py` → **rc=1 / status=drift**（§3） | ❌ **未達標** |

> 🔴 **R76 就地訂正 E3（本列 R75 欄位逐字保留為時代快照，不改寫）**：兩件事都變了。
> ① **量測值**：掌舵者提權重跑安裝器後，`tools/check_scheduled_task_drift.py` 當回合實測
>    `status=ok`／**rc=0**（`AutoClaude_Nightly` 與 `AutoClaude_WindowsSmoke` 各 7 項全符）。
> ② **判準本身有結構性缺陷、已改寫**（R76-06／本輪 PKG-D）：E3 原文以**整支工具的 rc** 取證，
>    而該工具的期望值 SSOT 同時列著兩支任務——執行 E3 自己授權的動作（移除 smoke）必然讓它
>    回 `task_missing`／rc=1 ⇒ **這條判準結構上不可能被滿足**。已改為逐任務量測（只看
>    `.tasks.AutoClaude_Nightly`），並在 `tools/windows_smoke_local.ps1` 就地寫下一般化規則
>    「判準的量測對象不得隨被它所判的動作而改變」（R75 頭號教訓第三次復發）。
> ⇒ 現況：**E1／E2／E3 三條可能都已成立**，但「是否真的移除 `AutoClaude_WindowsSmoke`」是
>    掌舵者的決定，本輪零 `Register-`／`Unregister-ScheduledTask` 呼叫。
>
> 🔴 **R76 收尾三次訂正（2026-08-06）**：上面那一行在寫下的同一天晚上就失效了——
> **E1 已不成立**（2026-08-05T16:05:50Z 的帳務事件，`DEF-101-866`）。取證、影響面與
> 「量測配方要補一步」的理由見 §0 的**第二個**訂正塊；本行不重述，只把結論接上：
> **三條現為 2/3，`AutoClaude_WindowsSmoke` 維持每日、不得退場。**

**訂正腳本內的現況欄（R76 二次訂正 — 這兩行本身在 R76 已成假話，見上方訂正塊）**：
`tools/windows_smoke_local.ps1` 的「現況快照」段已於 R76 **整段移除**，改為只留不會過期的
處置規則（在該檔的判準段之後；本行刻意**不寫死行號**——R76 第一版就是因為寫死行號而在
同一次提交裡指向一段已被自己刪掉的文字）。三條的**現況以上方 R76 訂正塊為準**：
E1 達標、E2 達標、E3 **在改為逐任務判準後亦達標**（實測 `status=ok`／rc=0）。
本行不逐字重述被推翻的舊結論——樹裡不留假句子（R75 交棒書禁止事項 #5／R73 頭號教訓）。

> **關於那 32 筆 failure**：它們是真正的測試紅（R 系列跨平台修復期的 push churn），**不是**帳務或基礎設施停擺——E1 要區分的正是這件事，而它區分對了。`status` 全為 `completed`、零 `startup_failure` ⇒ workflow 真的跑起來了，主通道是活的。最新一筆 `2026-08-04T02:04:23Z`（＝R74 `a371068` 的 push）為 `success`。

#### 2.2.4 能不能加速？

**這一題的前提要修正：這支不是在累積證據，它沒有「進度」可以加速。** 它是補償控制，退場條件是「主通道復活」，而主通道**已經復活**。所以：

- **不需要加速驗證**——需要的是**修一項設定，然後拍板退場**。
- 唯一卡點 E3 是一條提權指令的事（§3、§5 D-1）。修完設定後 E1/E2/E3 **三條全數成立**。
- 🔴 **R76 回執**：該提權指令**已由掌舵者執行完畢**，`check_scheduled_task_drift.py` 當回合
  實測 `status=ok`／rc=0 ⇒ 上一行的「修完設定後」這個前提已經發生，三條現況全部成立。
  剩下的**只有** ② 拍板（見 §2.2.6 的三段表）——不再有任何工程前置。

#### 2.2.5 排程載具下實測正常（不是「它反正也沒在跑」）

避免拿「它沒在跑」當撤除理由，逐項取證：

- `logs/windows_smoke_2026-08-03_233119.log`：`===== 彙總：PASS=12 FAIL=0 =====`（該 log 收尾於 23:31:19，＝ 23:30 觸發 + 88 秒），**23:30 排程觸發確實會跑且全綠**。
- `windows_smoke_latest.log`（2026-08-04 00:53）：`PASS=12 FAIL=0`，`[smoke-env] codepage=65001 psver=5.1.26100.8875`、`msys=`（載具正確：原生 PS 5.1、非 MSYS）。
- 2026-08-03 有 4 筆 `PASS=11 FAIL=2`（01:08~01:52 之間），全部落在 R73 修復進行中的時段，其後全綠。

#### 2.2.6 處置建議

**分三段，別把它們混在一起：**

| 段 | 動作 | 誰做 |
|---|---|---|
| **① 現在** | 修排程設定漂移（同一條指令一起修好 nightly）→ E3 成立 → 退出判準 3/3 | 🔴 掌舵者（需提權），§5 D-1 |
| **② 拍板** | 決定「退場」還是「降頻」。**SA 建議降頻而非移除**：它現在的實質成本只有 **88 秒 CPU ＋ 一筆 log**，而它守的是三支 hook 安裝器的 linked-worktree 拒絕、非 ASCII 路徑編碼、`-Command` 呼叫鏈這幾道每日活體驗證。88 秒/天換這個，划算〔🔴 **R76 收尾：本段暫不適用**——E1 已於 2026-08-05 因帳務事件失效（`DEF-101-866`），前置條件回到未滿足，**維持每日**，不到拍板時點。見 §0 第二個訂正塊〕 | PM |
| **③ 若真要退場** | 🔴 **不是刪個工作就好**，見下 | 需一輪 code 工作（§5 D-4） |

**🔴 「只刪工作」會留下兩個誤導訊號（本輪實查程式碼確認）：**

1. `install_windows_nightly.ps1 -Status` 的判準是「整組任務**全部**存在＝0；任一缺席＝1」（檔頭 `:52`，實作 `:212-213` `$loaded = (Test-TaskPresent nightly) -and (Test-TaskPresent smoke)`）⇒ **只刪 smoke 會讓 `-Status` 永遠 exit 1**，變成一個恆紅、因此會被習慣性忽略的心跳查詢。
2. `tools/scheduled_task_expectations.json` 仍列 `AutoClaude_WindowsSmoke` ⇒ drift checker 會判該任務缺席。🔴 **R76 訂正（本列原文已為假）**：原文寫「**rc 不會轉紅**（缺席只記 `absent` 不記 `drifts`，rc 只由 `drifts` 驅動）」——那是 R75 之前的實作。R75 已補上 `elif present < len(expectations): report["status"] = STATUS_TASK_MISSING`（該行註解逐字「＝漏跑的最強形態，**不得判綠**」），而 `check_scheduled_task_drift.py` 的收尾是 `return 1 if report["status"] in (STATUS_DRIFT, STATUS_ERROR, STATUS_TASK_MISSING) else 0` ⇒ **只刪 smoke 會讓它 rc=1**，且該工具在 nightly 是 fail-closed。所以這一項的實害方向與原文相反：不是「靜默脫節」，是「當場整條 nightly 轉紅」。兩種都不可接受，處置一樣（見下方 ⇒ 那一段），但**別照原文以為刪了不會有事**。
3. 安裝器**沒有「只移除 smoke」的模式**：`-Uninstall` 對整組生效（`:221` `foreach ($name in @($TaskName, $SmokeTaskName))`）。

⇒ 真正的退場＝改 `install_windows_nightly.ps1`（把 smoke 移出受管組）＋ `tools/scheduled_task_expectations.json` ＋ `tools/tests/test_install_windows_nightly.py`（含 `TestScheduledTaskExpectationsSsot` 與 `test_smoke_task_shares_catchup_settings_and_runs_before_nightly` 兩道鎖）＋ `tools/windows_smoke_local.ps1:99-127` 的判準段改述為「已退場」。**這是一輪有 DoD 的工作，不是一條指令。**

**移除會失去什麼（具體清單）：**

1. push 之前／離線時的 Windows 執行級訊號**自動化**。腳本還在，但變回「要有人記得跑」——**那正是 R60 立案時要解決的原始問題**（DEF-101-529 訂正前的狀態：「補償控制自己沒有心跳」）。
2. 雲端 `windows-compat-ci` 帳務再度停擺時的復發保險（DEF-101-081 已經發生過一次）。
3. 三支 hook 安裝器（`AutoClaude/tools/install_git_hooks.ps1`、`AISDLC_SDD/scripts/install-hooks.ps1`、LATEST `install_post_commit.ps1`）的 linked-worktree 拒絕 ＋ 中文路徑 `core.hooksPath` 編碼防護 ＋ `-Command` 非典型呼叫鏈防呆的**每日活體驗證**。
4. `install_windows_nightly.ps1 -WhatIf` 預覽的每日健檢（[9/9]）。

**🔴 反過來也要說（腳本 `:115-121` 自己記載的雙向反證，不可只引一半）：**
- R74 同輪雲端抓到一筆**本機十道閘門全綠**的 P0（hook 中文指引在非 CJK codepage 被 escape）⇒ **「smoke 零發現」不代表「沒有東西可發現」**，用「零發現」當撤除依據會在通道還有價值時撤掉它。
- 但那筆缺陷是**雲端 runner** 抓的、不是本機 smoke ⇒ **也不支持「smoke 排程是唯一發現通道」**這個 R60 立案前提。
- **兩個方向都不成立**，所以判準才綁在「主通道活性（E1）」而不是綁在「發現數」上。本節結論照此判準走，不摻入發現數論證。

---

## 3　排程設定漂移：逐項明細與後果

```powershell
$env:PYTHONUTF8='1'; & '<repo>\.venv\Scripts\python.exe' '<repo>\tools\check_scheduled_task_drift.py'
```
```
[schedule-drift] status=drift
  - AutoClaude_Nightly: 2 項漂移
      Settings/ExecutionTimeLimit: 實機=<missing> 期望=PT4H
      Settings/MultipleInstancesPolicy: 實機=IgnoreNew 期望=StopExisting
  - AutoClaude_WindowsSmoke: 3 項漂移
      Settings/ExecutionTimeLimit: 實機=<missing> 期望=PT4H
      Settings/MultipleInstancesPolicy: 實機=IgnoreNew 期望=StopExisting
      Principals/Principal/LogonType: 實機=InteractiveToken 期望=S4U
  修法（需「以系統管理員身分執行」）：...
rc=1
```

> 註：XML 導出裡 `ExecutionTimeLimit` 顯示 `<missing>`；`Get-ScheduledTask` 的 Settings 物件對同一項回報 `PT72H`（§1.3）。兩者指的是同一件事＝**沒有套上 PT4H**。

### 逐項後果

| # | 任務 | 設定 | 實機 | 期望 | 沒套上會造成什麼（附實證） |
|---|---|---|---|---|---|
| 1 | Nightly | `ExecutionTimeLimit` | PT72H | **PT4H** | 被睡眠凍住的實例在 72 小時額度內**存活**，隔日觸發被吃掉 → 該日**三軌零進帳**。實證：`logs/nightly_2026-08-01_101807.log` 從 08-01 10:18 跑到 08-02 21:54＝**35.6 小時**，UTC 08-02 桶零紀錄。正常整輪 5~8 分鐘（實測 7m45／5m38），PT4H 已極寬鬆 |
| 2 | Nightly | `MultipleInstancesPolicy` | IgnoreNew | **StopExisting** | `IgnoreNew` 讓凍住的實例吃掉**後續所有**觸發；`StopExisting` 是 `ExecutionTimeLimit` 之外的第二道防線。兩項是同一個失效模式的雙保險，只修一項仍有洞 |
| 3 | Smoke | `ExecutionTimeLimit` | PT72H | **PT4H** | 同 #1（smoke 正常 88 秒） |
| 4 | Smoke | `MultipleInstancesPolicy` | IgnoreNew | **StopExisting** | 同 #2 |
| 5 | Smoke | `LogonType` | **InteractiveToken** | **S4U** | 「符合啟動條件時使用者未登入」→ **整輪不跑**。實證：2026-08-02 事件 332，`NumberOfMissedRuns=1`。S4U＝以該使用者身分執行但**不需登入、不需存密碼** |

### 記憶檔「四項關鍵」現況：**兩支都已正確，本次不在漂移清單內**

| 四項 | Nightly | Smoke | 沒設會怎樣 |
|---|---|---|---|
| `WakeToRun` | ✅ True | ✅ True | 睡眠/休眠時不喚醒機器 → 到點不跑（另需 `powercfg` 喚醒計時器，本機該層實測失效，掌舵者已用「改到開機時段」繞過） |
| `StartWhenAvailable` | ✅ True | ✅ True | 關機錯過觸發後**不補跑** → 觀察期 idle 漏跑 |
| `DisallowStartIfOnBatteries` | ✅ False | ✅ False | 吃電池時**擋啟動** |
| `StopIfGoingOnBatteries` | ✅ False | ✅ False | 執行中切到電池被**中途砍掉** |

### 🔴 為什麼這次一定要修（不是潔癖）

drift 軌**只剩 2 筆**。#1+#2 這個組合已經在 08-02 實際吃掉一整天的三軌進帳一次。再被吃一次，達標日就從 2026-08-06 推到 08-08 以後。**修排程設定是現在成本最低、效果最直接的加速手段。**

### 🔴 這筆漂移已被 nightly 自己納管（本輪他人已落地，DEF-101-794）

今晚的 log `:496` 逐字：
```
[SCHED-DRIFT] 上列漂移＝已知存量（DEF-101-794；修法需系統管理員提權）——顯著可見但不計入本輪失敗。
              偵測器回報 status=ok 之後，本項應移回 finalFailures（見本段註解）
```
⇒ 已有人把 `check_scheduled_task_drift.py` 接進 nightly，並刻意先設成**可見但不阻斷**（否則 nightly 會因為一件只有人類能修的事而每晚必紅）。**設計意圖是「等你修完，它就會變成硬閘」**——所以 D-1 不只是清一個警告，它會解鎖一道閘門的升級。本檔的 D-1 建議與該落地方向一致，非重複造輪。

---

## 4　孤兒盤點（兩個方向都查）

### 4.1 孤兒 Job（有工作、指向的腳本不存在）：**無**

| Job | Action 指向 | 磁碟實查 |
|---|---|---|
| AutoClaude_Nightly | `d:\CursorProject\AISDCL_Agent\AutoClaude\tools\run_local_nightly.ps1` | ✅ 存在 |
| AutoClaude_WindowsSmoke | `D:\CursorProject\AISDCL_Agent\tools\windows_smoke_local.ps1` | ✅ 存在 |

> 附帶觀察（無功能影響、僅記錄）：兩支的磁碟機字母大小寫不一致（`d:\` vs `D:\`），且 nightly 有 `WorkingDirectory`、smoke 沒有。NTFS 路徑不區分大小寫，兩支腳本都自行以 `$PSScriptRoot` 定位 repo 根，故無影響。這是兩支在不同輪次註冊留下的痕跡。

### 4.2 孤兒腳本（有腳本、沒有對應 Job）：**3 支，性質各不相同**

| 腳本 | 狀態 | 判定 |
|---|---|---|
| `AutoClaude/tools/g0_gate_check.ps1` | 原由 `AutoClaude_SD09_G0_GateCheck` 排程呼叫；**該工作已於 R71 從本機移除**（腳本刻意保留）。現無排程消費者，仍可手動跑 | ⚠️ **真孤兒（可接受）**——它的功能已被 nightly 內建的四軌 G0 判定 ＋ `.g0_readiness.json` 憑證取代。建議保留供手動查詢，但應在檔頭註明「已無排程消費者」 |
| `AutoClaude/tools/reschedule_g0_gatecheck.ps1` | 唯一用途是重排上面那支**已不存在**的工作 | 🔴 **真孤兒（無用途）**。建議列入清理候選（本輪唯讀，不動） |
| `AutoClaude/tools/fix_nightly_catchup.ps1` | 補跑保護校正器。`install_windows_nightly.ps1:320-322` 建立時已內建同款設定 | ✅ **非孤兒缺陷**。該檔檔頭 `:13` 明文「已安裝的舊機器仍可用該腳本校正」＝刻意保留的歷史修復路徑 |

### 4.3 對照組 vs 現場（任務清單層面）

`tools/scheduled_task_expectations.json` 列 **2** 支＝線上 **2** 支 ⇒ 一致。工作缺席不會讓 checker 轉紅（`evaluate()` `:130-133`／`:149-151`），這是刻意的 CI 安全設計，但也意味著**日後若有人刪掉工作，checker 不會吵**——已在 §2.2.6 標為退場時必須一併處理的事。

---

## 5　給掌舵者的決策清單

### D-1　🔴 需系統管理員｜修排程設定漂移（**最高優先，建議今天做**）

**要做什麼**（在「以系統管理員身分執行」的 PowerShell 視窗）：

選項 A —— **維持你現在設定的時刻**（nightly 22:30、smoke 23:30）：
```powershell
powershell -ExecutionPolicy Bypass -File D:\CursorProject\AISDCL_Agent\tools\install_windows_nightly.ps1 -NightlyAt 22:30 -SmokeAt 23:30 -AllowSmokeAfterNightly
```

選項 B —— **順便回復「smoke 早於 nightly」的設計不變量**（nightly 22:30 不變，smoke 移到 21:30）：
```powershell
powershell -ExecutionPolicy Bypass -File D:\CursorProject\AISDCL_Agent\tools\install_windows_nightly.ps1
```

🔴 **不要不帶參數就跑，除非你要選 B。** 安裝器是 `Unregister→Register`，`-SmokeAt` 的 param 預設值是 **21:30**（不是你現在的 23:30）——不帶參數會把 smoke 從 23:30 搬到 21:30。這是安裝器**刻意**的設計（`install_windows_nightly.ps1:83-96`）：`smoke < nightly` 有一條 active 機械鎖（`tools/tests/test_install_windows_nightly.py::test_smoke_task_shares_catchup_settings_and_runs_before_nightly`），理由是「smoke 是 88 秒的便宜 tripwire、nightly 是 5~8 分鐘的深度回歸；機器當晚只醒一小段時間時先跑完便宜那支才有意義」。你現行的 23:30 與該鎖相反。
**SA 建議選 B**：21:30 同樣落在「確保開機中」的時段，且能讓鎖與現場重新對齊（選 A 則要顯式帶 `-AllowSmokeAfterNightly` 宣告違反，鎖與現場繼續脫節）。

**驗證（同一則回覆內必須貼出下列輸出，否則不算已修——反「事後諸葛」取證規則）**：
```powershell
# ① 安裝器自報（整組全在＝exit 0）
powershell -ExecutionPolicy Bypass -File D:\CursorProject\AISDCL_Agent\tools\install_windows_nightly.ps1 -Status

# ② 漂移比對器（應 status=ok、rc=0）— 不需提權
$env:PYTHONUTF8='1'
& 'D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe' 'D:\CursorProject\AISDCL_Agent\tools\check_scheduled_task_drift.py'

# ③ 排程器自報下次執行時間（NextRunTime 就是憑證）
Get-ScheduledTask | Where-Object TaskName -like 'AutoClaude*' | Get-ScheduledTaskInfo |
  Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime
```

**為什麼**：① 這是 drift 軌剩下 3 筆能不能順利入帳的關鍵（08-02 已被吃掉一天）；② 這也是 smoke 退出判準 E3 的唯一卡點，修完 E1/E2/E3 三條全成立。

**不做的後果**：睡眠凍住的 nightly 實例會繼續吃掉隔日觸發（已發生過一次，代價是一整天三軌零進帳）；smoke 在使用者未登入時整輪不跑（已發生過一次，`NumberOfMissedRuns=1`）；smoke 的退場判準永遠卡在 2/3，這個問題會第四輪再問一次。

---

### D-2　✅ 已自動完成（無需動作）｜今天那筆 drift 紀錄

原建議是手動 `Start-ScheduledTask` 補今天（08-04 UTC）那筆。**今晚 22:30 的排程觸發已自動完成**（`27→28`，`.drift_log_history.jsonl` 37 筆）。

⚠️ **不要為了「趕進度」在同一個 UTC 日重複跑**：UTC-date 去重會讓第二次只是覆寫同一筆，而 last-write-wins 意味著**如果第二次剛好抖一下，會把已經入帳的綠改成紅、streak 歸零**（ADR-SD09-012 §2.3 EXP-B 實測）。**重跑是負收益。**

**接下來要做的事只有一件：確保 08-05 與 08-06 兩晚 22:30 機器開著。**
> 🔴 **R76 訂正**：不是兩晚，是**連續 17／18 晚**（obs 最早 08-21、drift 最早 08-22）——
> 判準改為看 span 之後，「不中斷」本身成了判準，中間漏一晚就會把終點往後推。見 §0 訂正塊。

---

### D-3　PM 拍板｜2 晚後對 G0 四軌拍板（預估 2026-08-06 夜 ~ 08-07 晨）
> 🔴 **R76 訂正：時點改為 2026-08-22 之後**（見 §0 訂正塊）。本標題的日期為 R75 快照。

**要做什麼**：等 `AutoClaude/.g0_readiness.json` 的 `ready` 變成 `true`（該檔已存在，今晚起每輪都會覆寫；🔴 R76：讀它之前先看 `generated_at`，那是每晚重生的量測檔，可能早於最近一次判準變更），然後拍三件事：
1. 觀察期 stage **降頻**（SA 建議每週；🔴 上限是 30 天，因為 AC4 `STALENESS_MAX_DAYS=30`），或維持每日。🔴 **R76：在 obs／drift 兩軌轉綠之前不得降頻**——新判準要求 last-30 筆落在 ≤40 個日曆天內，每週採集結構上永遠達不到。
2. drift 是不是 W1 入場條件？（判準衝突見 §2.1.6 末：nightly 的 G0 要四軌，ADR-SD09-012 §1.1 說 drift「非入場阻塞項、歸屬待 PM 裁定」。〔🔴 R76 訂正：原文此處寫「若裁定不是，W1 現在就能啟動」——**已不成立**，obs 也翻成 sparse 了，裁定 drift 出局仍要等 obs（最早 08-21）。〕）
3. ADR-SD09-012 §7.5 仍掛著的 S3（UTC 桶錯位是否另開一輪）。

**查詢指令（不需提權）**：
```powershell
Get-Content 'D:\CursorProject\AISDCL_Agent\AutoClaude\.g0_readiness.json' -Encoding utf8
```

**不做的後果**：nightly 繼續每晚跑（每晚成本 5~8 分鐘，且 mutation stage 在源碼不動時已自動跳過）。**沒有立即損害，但「該停了」這件事會再度沒人拍板**——這正是 R74 立那份憑證要防的。

---

### D-4　需一輪 code 工作｜smoke 排程若要退場（**不要只刪工作**）

**要做什麼**（四處同步，有 DoD）：
1. `tools/install_windows_nightly.ps1` — 把 smoke 移出受管組（含 `-Status` 的 `$loaded` 判準、`-Uninstall` 的 `foreach`）。
2. `tools/scheduled_task_expectations.json` — 移除 `AutoClaude_WindowsSmoke` 條目。
3. `tools/tests/test_install_windows_nightly.py` — 更新 `TestScheduledTaskExpectationsSsot` 與 `test_smoke_task_shares_catchup_settings_and_runs_before_nightly` 兩道鎖。
4. `tools/windows_smoke_local.ps1:99-127` — 判準段改述為「(乙) 已於 R__ 退場，附 E1/E2/E3 取證」；**(甲) 腳本永久保留的段落不動**。
5. 提權跑 `-Uninstall` 後重新 install（或直接 `Unregister-ScheduledTask -TaskName 'AutoClaude_WindowsSmoke' -Confirm:$false`）。

**為什麼不能只刪工作**：`-Status` 會永遠 exit 1（`:212-213` 整組全在才回 0）；drift checker 會靜默把它記成 `absent` 而 rc 不變紅（`:130-133`／`:149-151`）⇒ 對照組與現場靜默脫節，正是這支 checker 立案要消滅的狀態。

**不做的後果**：smoke 每天多花 88 秒 CPU ＋ 一筆 log。**SA 建議：不划算就別做，改降頻或直接維持每日**——它守的是三支 hook 安裝器的 linked-worktree 拒絕、中文路徑編碼、`-Command` 呼叫鏈這幾道每日活體驗證，88 秒/天換這個是好交易。

---

### D-5　清理候選｜孤兒腳本（低優先，本輪唯讀未動）

| 腳本 | 建議 | 不做的後果 |
|---|---|---|
| `AutoClaude/tools/reschedule_g0_gatecheck.ps1` | **刪除或標記廢棄**——它唯一的用途是重排一支 R71 已移除的工作 | 樹裡留一支「看起來還在用」的腳本，下一個人會以為那支排程還存在 |
| `AutoClaude/tools/g0_gate_check.ps1` | **保留，檔頭加註「已無排程消費者，功能由 nightly 四軌 G0 ＋ `.g0_readiness.json` 承載」** | 同上，但這支手動仍有用，風險較低 |
| `AutoClaude/tools/fix_nightly_catchup.ps1` | **保留不動** | 無（檔頭已明說是舊機器校正路徑） |

---

## 6　🔴 今晚（2026-08-04 22:30）nightly `exit=1` 的根因——與觀察期無關

本檔撰寫期間今晚的 nightly 跑完了，`LastTaskResult=1`。逐 stage 取證（`logs/nightly_2026-08-04_223001.log`）：

```
:478  END nightly summary: mutation=SKIP pg-e2e=0 perf=0 drift=0 obs=0 local_ci_gate=1 sdd_chaos=0
:497  END exit decision: exit=1 (failed stages: local_ci_gate=1)
```

| stage | exit | 說明 |
|---|---|---|
| local-ci-gate full | **1** | 🔴 唯一失敗 |
| mutation-test | `SKIP` | ✅ R74 邏輯生效：已鎖定且源碼 sha 已量過 → 跳過（整輪因此只花 **3m13s**，對比 7m45s） |
| Docker-PG-bring-up | 0 | ✅ |
| pg-e2e + AC4 collector（觀察期 #2） | 0 | ✅ |
| perf-baseline | 0 | ✅ `regression_check_rc=0, baseline_lock_rc=0` |
| drift_log-scan（觀察期 #3） | 0 | ✅ 已入帳 |
| observability-snapshot | 0 | ✅ |
| sdd-fsm-chaos | 0 | ✅ 53.5s |

**⇒ 四個觀察期／GA 軌道的採集 stage 全部成功，這筆紅完全不影響 §2.1.4 的進度。**

### 6.1 根因：本輪其他 agent 未 commit 的編修踩到根層護欄檔的行數棘輪

`local_ci_gate` 內兩項紅，但**是同一個根因**：

```
:10  [check_loc_budget v2-tiered] total=20296 baseline=17032 cap=20438
                                  violations=2 (absolute=0 tier=0 special=2 total=0)
:19  [SPECIAL] ADR-SD08-001 SPECIAL_FILES line-count violations:
:20    [special<=1507] ../tools/archive_defect_log.py: 1511 > 1507 (+4)
:21    [special<=1474] ../tools/check_defect_log_crossref.py: 1479 > 1474 (+5)
:22  [LOC budget] FAIL (rc=1)
...
:244 4 failed, 3995 passed, 145 skipped in 113.09s
:245 [pytest] FAIL (rc=1)
```

4 支 pytest 失敗的斷言訊息**自己就指向同一個根因**：
```
:115 AssertionError: cap = total+11 時 rc 應為 0（預警帶必須非阻塞）；實得 1。
     若非破線態卻得 rc=1，請先確認 repo 是否另有 tier/absolute/special 違規
```
⇒ LOC 預警帶測試是在驗「沒破線時 rc 必須是 0」，而 repo 現在有 **2 筆 special 違規**，所以那 4 支必然紅。**一個根因、兩個症狀，不是兩件事。**

### 6.2 這是本輪 in-flight 編修，不是存量缺陷

本 session 早先 `git status --porcelain` 實測：
```
 M AutoClaude/tools/hooks/check_sh_eol.py
 M CLAUDE.md
 M tools/archive_defect_log.py            ← 就是它
 M tools/check_defect_log_crossref.py     ← 就是它
 M tools/scheduled_task_expectations.json
```
兩支破棘輪的檔**正是本輪其他 agent 正在編修、尚未 commit 的檔**（缺陷帳本歸檔／交叉引用那條工作線）。

**⇒ 這筆紅屬本輪 in-flight 狀態，處置歸屬那條工作線的持有者，不在本 SA 唯讀分析的射程內**（本檔對這兩支檔零改動）。持有者需在 commit 前把 `archive_defect_log.py` 壓回 ≤1507、`check_defect_log_crossref.py` 壓回 ≤1474，或依棘輪規則「先刪死碼／抽共用模組，確認不可壓縮後才在缺陷帳本具名調高」。

### 6.3 這一筆恰好回答了掌舵者的第一個問題

「`AutoClaude_Nightly` 這個機制測完完畢了嗎？還有需要嗎？」

**今晚它在 3 分 13 秒內抓到一筆當下正在發生的紅**——而且是本機 push 前閘門會擋、但 in-flight 狀態下還沒人跑到的那一類。這就是它作為「常態回歸監控」那一半的價值展示：**觀察期那一半會結束（剩 2 筆），回歸監控那一半不會**。這也正是 §2.1.7 建議「降頻而非移除」的實證支撐。

---

## 7　本檔取證邊界（誠實揭露）

| 項目 | 狀態 |
|---|---|
| §1 排程現況（兩個時點）、§3 漂移、§2.1.4 四軌（前後兩組）、§2.2.3 E1/E2、§2.1.5 drift 逐列、§2.2.5 smoke log、§6 今晚紅 | ✅ **當回合真跑**，指令與輸出均已附 |
| §2.1.3 `.g0_readiness.json` | ✅ **當回合真讀**。⚠️ 但它在本檔撰寫期間由「不存在」變成「存在」——寫它的 code 是 R74（`a371068`，08-04 09:57）落地，第一次寫入是今晚 22:33 那輪。**本檔引用的是 `run_id=223001` 那一份，會被下一輪覆寫**（每輪都寫，帶 `generated_at`）。要現況一律重讀該檔，不要引用本檔的快照 |
| §5 D-1 的提權指令 | ❌ **未執行**（SA 無提權，且刻意不嘗試）。這是交付指令，不是已驗證結果。修完務必貼出 `-Status`／比對器／`NextRunTime` 三份輸出 |
| nightly 本體、全套 pytest | ❌ **本 SA 刻意未跑**（前者數小時、後者有他人在跑）。§6 的 stage 逐項數字**來自今晚排程自己跑出來的 log**，不是我跑的 |
| §2.1.6 的「最快 2026-08-06 夜達標」 | ⚠️ **這是推算，不是量測**。前提＝08-05／08-06 兩晚 22:30 機器開著且 drift stage 不再出錯。**任何一晚漏跑就往後推一天** |
| §2.2.3 E1 的 40 筆雲端 run | ✅ 真跑 `gh run list`。⚠️ 判準原文寫「近 **30 天** ≥ 20 個 run」，實測 40 筆全落在**近 10 天**內 ⇒ 條件以更嚴的方式滿足，但**本檔沒有回查第 11~30 天**（`--limit 40` 已被近 10 天填滿）。若日後要重驗，需加大 `--limit` 或改用 `--created` 篩選 |
| `AutoClaude/tools/run_local_nightly.ps1`、`AutoClaude/tools/hooks/`、`docs/04_planning/`、`docs/06_quality/AutoSDD_Defect_Log.md`、`tools/archive_defect_log.py`、`tools/check_defect_log_crossref.py`、`tools/scheduled_task_expectations.json` | ⚠️ 本輪由他人持有／正在變動（`git status` 實測）。本檔對它們**只讀不寫**；行號為 2026-08-04 實查值，若他人同輪改動請重新 grep 錨點，勿沿用本檔行號 |
| §6 那筆紅的處置 | ❌ **不在本 SA 射程**（屬缺陷帳本工作線的持有者）。本檔只做歸因取證，未動那兩支檔 |
| 本檔改動範圍 | ✅ **僅新建本檔一支，零既有檔改動** |
