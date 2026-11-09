# SCG-0～3 一審報告：SelfImproving P4「自動演化排程」規格集（QA 鏡，唯讀）

審查 HEAD＝`bce6a59c1d32399d64054196611cfda82066ebdf`（`git status --short` 空＝工作樹乾淨）。審查日 2026-11-09。

## A 判定

**FAIL**（P1 0／P2 3／P3 7／P4 2）。P2 三條都是「規格字面與既有機械物或自身其他條文互相打架、照字面實作會有 AT 無法通過或功能缺口」，修法明確，修完可進二審。其餘面向（需求覆蓋、欄位／枚舉／rc 一致性、AT 錨定與計數、契約連動）整體紮實，下列「C／D／E」表可供二審直接重用。

## B 發現表

### F-01（P2，SCG-3 契約／SCG-2 可測性）能力登記的「全套件禁字樣」與 `schedarm.py` 的 `launchctl` 字面互斥，AT-440-3-1／3-2 照字面無法同時成立
- 位置：PRD §9.4〈P4 增補〉（line 1076）與 TCS 根層 R160（line 122）、R161 (d)（line 123）、AT-440-3-2（line 1555）；對照 `tools/tests/test_selfimproving_capability.py` 的 `FORBIDDEN`（line 91–106）與 `capability_problems` line 223–225（對套件內**每個** `*.py` 跑 `forbidden_hits`）。
- 字面：PRD／TCS 寫「全套件禁字樣（`time.sleep`、`while True`、`os.fork`、`signal.alarm`）對新檔照樣適用」「`forbidden_hits` 對全部新檔為空」，同時 R161(d)／AT-440-3-2 要求 `schedarm.py` 內有 `launchctl`、`powershell.exe` 的 argv 字面（置於平台守衛內）。
- 問題：現行 `FORBIDDEN` 共 14 條，**除上述四條外還含 `schtasks`、`launchctl`、`crontab`、`Register-ScheduledTask`、`ScheduleWakeup`、`CronCreate`、`apscheduler`、`threading.Timer`、`sched.scheduler`、`daemon=True`**；判準不看平台守衛，只做正規式命中。實測現況：`Grep launchctl|schtasks|crontab|ScheduleWakeup` 對 `tools/lib/selfimproving/` 為 0 命中，所以新增 `schedarm.py`（含 `launchctl` 字面）必使 `capability_problems(PKG, CAPABILITY, ENTRY)` 非空，真樹測試（line 330、412 的 `assertEqual(..., [])`）轉紅。PRD／TCS 只列四條、彷彿 `FORBIDDEN` 只有四條，遺漏了與 ADR-SI-14 直接衝突的那幾條（這些字樣原本就是「套件內不得自己排程」的 P0 設計鎖）。同步表（TCS §2.5）也沒列 `FORBIDDEN` 與其 `FORBIDDEN_SAMPLES`（line 108 起）的修改。
- 建議修法：二選一並寫進 PRD §9.4、ADR-SI-14（含 WHY）與 TCS 同步表：(甲) 從 `FORBIDDEN` 移除 `schtasks`／`launchctl`／`Register-ScheduledTask`（保留 `crontab`、`ScheduleWakeup`、`CronCreate`、`apscheduler`、`threading.Timer`、`sched.scheduler`、`daemon=True`、`time.sleep`、`while True`、`os.fork`、`signal.alarm`），並同步改 `FORBIDDEN_SAMPLES`；或 (乙) 判準改為「這三條僅 `schedarm.py` 豁免、且該檔不得出現 `time.sleep`／`while True` 等」。AT-440-3-1／3-2／E-1 同步改為斷言新的禁字樣清單（逐條列出，不再寫「四條」）並加一個「`schedarm.py` 以外出現 `launchctl` 仍被抓」的負控。

### F-02（P2，SCG-0 需求完整／SCG-5 風險）Console「立即啟動」開出的 (a) 運轉沒有任何人執行、也沒有收尾路徑，並會使後續 (f) 到期永久被 `run-open` 跳過
- 位置：PRD AC-SI-37-2（line 522）、AC-SI-38-1（line 529）、AC-SI-38-6（line 534）、AC-SI-39-3（line 541）、§2.2 SC-SI-6（line 126）；SOP〈每心跳做什麼〉步 1／3／4（line 428–431）；TCS R149～R156、AT-437-2-2。
- 字面：SC-SI-6 的預期結果＝「按『立即啟動一次演化』→…→產出提案卡」；AC-SI-37-2 入帳後只追加 `run.open{trigger:"a",carrier:"console"}`；AC-SI-38-1 的 spawn 前置是「到期且 AC-SI-36-2 全不成立… `run-open --trigger f`」；`run-close` 只出現在 AC-SI-38-6（spawn 返回後）與 AC-SI-39-3（有提案皆離開待人工決定態）。
- 問題：trigger a 的 Console 運轉入帳後，**巡邏器不 spawn、不 `research`／`scan`、也不會 `run-close`**（無 spawn 返回事件、無 `prop`）。一、「立即啟動一次演化」鈕在無人視窗時什麼都不會發生（只留下一個空的未關運轉），與 SC-SI-6、§8.1 P4 出口敘述不符；二、此未關運轉使其後每一格的 (f) 嘗試判 `run-open` ⇒ 只記 `sched.skip(run-open)`，直到人手動 `run-close`——一次 Console 點擊就能把自動演化靜默堵死，而 `overdue` 因 skip 事件存在為 false，**偵測面也看不到**。
- 建議修法：在 FR-SI-38 增一條 AC（並補 AT 正負控）明定 Console `run-request` 產生的 (a) 運轉的執行者：建議＝巡邏器對「本心跳新入帳的 `run.open(a, carrier=console)` 且無 `prop`」走與 (f) 相同的 `research`→`scan`→spawn 序（沿用 AC-SI-36-2 ③④⑦ 的跳過判準，但**不要求啟用旗標、不受格線限制**），或明示「僅人在場時由互動主控接手」並另定**閒置未關運轉自動 `run-close(no_event)` 的逾時**（含參數）與 `check`／`status` 對「未關運轉閒置逾時」的可偵測欄位；同步改 SC-SI-6、SOP 步 3、兩份 TCS。

### F-03（P2，SCG-1 一致性）promote 前髒樹記 `sched.skip(dirty-tree)` 與「`sched.skip` 為到期專用」、停用時無格線、`check` 去重鍵互相牴觸
- 位置：PRD AC-SI-38-5（line 533）、AC-SI-39-3（line 541）、AC-SI-36-5（line 516，「停 (f)；入帳與推進照常」）、AC-SI-37-5（line 525，`due_at` 須落格起點）；TCS R155 (b)(d)（line 114）、R144、AT-438-5-E-1；SOP 步 4。
- 字面：38-5「工作樹不乾淨＝不 promote（記 `sched.skip reason=dirty-tree`…）」；39-3／R155(b)「不記 `sched.skip`，那是到期專用」；`sched.skip` 欄位 `due_at`＝本格起點、`check` 驗 `(due_at − origin) mod period == 0`；停用時 `cell_start`＝null。
- 問題：(1) 同一份規格對「`sched.skip` 能否用於推進路徑」自相矛盾（R155(b) vs (d)）。(2) **排程已停用（常見：只用 Console 核准／晉升、不用定期）時**，DEC(promote) 入帳後遇髒樹：沒有格線，`due_at` 無從取值，事件欄位表要求必備 ⇒ 要嘛寫不出事件、要嘛偽造 `due_at` 使 `check` 紅。(3) 去重鍵 (格, reason) 讓到期嘗試的 `dirty-tree` 與 promote 的 `dirty-tree` 互相吞掉，語意不明；且 skip 存在會使 `overdue` 為 false，promote 髒樹也會掩蓋「巡邏沒做 (f)」。AT-438-5-E-1 只測啟用情境，沒有停用情境。
- 建議修法：推進路徑的髒樹改「只寫日誌、不寫事件」（與 R155(b) 一致；下一心跳再試），刪除 38-5／R155(d)／SOP 步 4 的 `sched.skip` 字樣；或另立專屬原因／事件並讓 `due_at` 可為 null 且 `check` 與去重鍵另行規定。AT-438-5-E-1 增「排程停用」子情境與「skip 不影響 `overdue`」斷言。（主控裁決 D-SCH-6 原文含此句，故屬需主控重裁的裁決內部衝突，不是單純筆誤。）

### F-04（P3）無人值守 rc 1 清單三處不一致
PRD AC-SI-38-3 ③（line 531）列 `run-open`…`measure` 但**未列** `patrol`、`sched arm`、`sched disarm`；PRD §9.3 `patrol` 列（line 996）、SOP 序列條文（SOP line 269）、TCS R153／AT-438-3-2「C 類十三個」含 `patrol`，TCS R153 另含 `sched arm／disarm`，PRD 未列 arm／disarm。建議：以 AC-SI-38-3 ③ 為唯一真值表，補 `patrol`、`sched arm`、`sched disarm`，TCS 的「十三個」同步。

### F-05（P3）(a)～(e) 殘字
PRD AC-SI-10-3 本文（line 309）仍寫「AC-SI-03-1 的 (a)～(e)」（後附 v0.13 註改 (a)～(f)）、FR-SI-30 定位句（line 421）「AC-SI-03-1 的 (a)～(e) 不變」、FR-SI-27 憲法對照（line 396）「事件驅動、無日曆」。AC-SI-03-1 新 (f) 與 §3.2／§8.3／SOP 否定句本身無矛盾（已核），但這三處讀者會讀成仍是五類。建議改為 (a)～(f) 或加指向 v0.13 註。

### F-06（P3，風險：跑飛成本）任何 `sched.set(enabled=true)`（含值不變的重送）都重置格線，可在同一天多開 (f) 運轉
PRD AC-SI-36-1 ②「每次啟用或改週期都重置格線」＋AC-SI-37-1 兩種寫入不走 dedupe。Console 使用者重複按「儲存」、或改週期試值，每次都產生新 origin、新格 0，下一心跳就嘗試開運轉（無「距上次 (f) 運轉最短間隔」）。成本上界是每次點擊一個運轉。建議：值與現值完全相同時入帳為 no-op（或不重置 origin），並加「距最近 `run.open(f)` 不足 `sched_run_budget_minutes` 不開」之類的最小間隔，補 AT。

### F-07（P3，風險：兩平台差異）`WakeToRun=true` 搭每 15 分鐘觸發，即使排程停用也每天喚醒機器約 96 次
D-SCH-10／R161：任務觸發 24h 重複、`WakeToRun=true`、`DisallowStartIfOnBatteries=false`；啟用旗標預設停用，OS 任務與旗標獨立，故安裝後無論是否啟用都會喚醒睡眠中的機器（筆電耗電、夜間被叫醒）。mac 邊界另有明文，Windows 沒有。建議：巡邏任務 `WakeToRun=false`（`StartWhenAvailable=true` 已補跑），或在 SOP〈安裝與憑證〉與 PRD §10.1 明寫此成本並讓期望表／`why_each` 記 WHY（期望表是 SSOT，改值須同步安裝器與 `TestScheduledTaskExpectationsSsot`）。

### F-08（P3）黑窗 WHY 宣稱涵蓋「執行時間」，但判準只釘觸發時刻
PRD params 說明（line 917）WHY＝「涵蓋 Windows smoke 與 nightly 的觸發時刻與其執行時間」；`tools/scheduled_task_expectations.json` nightly `ExecutionTimeLimit=PT4H`、22:30 起，最壞到 02:30，黑窗 `21:00-00:30` 在 00:30 結束，後段 2 小時巡邏可與 nightly 並行（額度與 CPU 競爭）；`other-driver` 只看 claude 逐字稿、不看 nightly。TCS AT-440-2-E-2 只釘「涵蓋每個期望觸發時刻」。建議：改 WHY 為「只涵蓋觸發時刻，後段重疊由額度帶與 `dirty-tree` 兜」，或把黑窗終點拉到觸發時刻＋`ExecutionTimeLimit`（`02:30`）並讓測試以期望表的 `ExecutionTimeLimit` 計算。

### F-09（P3）無人值守下 `decide --carrier console` 為實質死許可；且主控任務書對現碼的描述不精確
AC-SI-38-3 ② 允許無人值守 `decide --carrier console`，但無人主控依 AC-SI-39-1 不持金鑰（`AUTOSDD_SI_AUDIT_KEY` 不傳），該路徑永遠 `AUDIT-KEY-MISSING`；而同為 Console 入帳的 `obs-add`／`obs-close`／`sched set`／`run-open` 卻一律拒。建議二選一寫明 WHY（保留以便未來由巡邏器子行程直接入帳），或對齊為「無人值守 `decide` 一律拒」。另：QA 任務書與 D-SCH-8 原文稱「現碼只有 `decide` 與 `measure` 拒」；現查 `decwrite.py:203,372`、`obswrite.py:52`、`promote.py:66`、`sandbox.py:230,350`、`verify.py:172`、`meawrite.py:115` 皆呼叫 `refuse_unattended`／同型檢查，PRD AC-SI-38-3 的「現況」描述才是正確的（本審已據此核實，不算規格缺陷，僅提醒裁決清單措辭需訂正）。

### F-10（P3，風險：巡邏占用）單一巡邏行程最長 4.5 小時，期間 `IgnoreNew` 使 Console 待入帳稽核檔無人入帳
PRD AC-SI-36-3、NFR-SI-01 排程列、SOP 步 0；硬牆＝`RESUME_HARD_WALL_SECONDS`（4.5h），任務 `ExecutionTimeLimit=PT5H`、`IgnoreNew`。一個運轉執行期間所有心跳被忽略，Console 的核准／晉升決定最多延遲 4.5 小時才入帳（與預算 90 分鐘的意圖不符，硬牆只是上界）。建議在 §10.1 風險列與 SOP 明寫此延遲，或把「入帳」拆成不被運轉占用的短行程（鎖仍以 `patrol.lock` 互斥時需另設）。

### F-11（P3，SCG-2）AC-SI-39-2～39-5 沒有獨立的 `-E-` 負控 AT
TCS §1 表：39-2、39-3、39-4、39-5 各只有 1～2 個正控編號 AT（負控情境寫在同一 AT 的 Scenario 內，例如 AT-439-3-1 含 FAIL 不否決、缺 `heldout.freeze` 跳過；AT-439-4-1 含偽造 DEC）。TCS 聲明「30 個 AC 皆至少一個 AT」成立，但「正控 53／負控 43」的統計以編號含 `-E-` 判，39-x 四條的負控被算進正控。建議將各 AT 內的負控拆出 `AT-439-n-E-m`，使「每 AC 一正一負」可由編號機械核對。

### F-12（P4）用詞：AC-SI-38-2「`obs` 入帳」
PRD AC-SI-38-2（line 530）角色序「研究者→`obs` 入帳〔無人主控＝單一寫入窗口〕」，但 C.2 #22 (3)、AC-SI-38-3 ③、SOP 範本步 2 都明定無人主控**沒有** `obs-add` 動詞、改手寫 OBS 列。建議改「手寫入 OBS 帳本」。

### F-13（P4）C.2 #22 (3)「候選由無人主控手寫 OBS 列」未見對應的 `check` 對帳說明
手寫列沒有 `obs.add` 事件；P2 既有 `obs.console_audit` 檢查只針對 Console 載體。非缺陷（P0 起即是手寫路徑），建議在 SOP 範本步 2 補一句「手寫列不產生 `obs.add`，屬既有行為」避免審查誤判。

## C 裁決對照（D-SCH-1～14 → 落點）

| 裁決 | PRD／SOP／TCS 落點 | 備註 |
|---|---|---|
| D-SCH-1 答案與定位 | §5 FG-M 開場（line 506）、AC-SI-03-1（line 269）、§2.2 SC-SI-6、SOP〈啟動條件〉第六類＋(a) Console 載體 | 一致 |
| D-SCH-2 C-12 修訂語意 | §3.2（line 175）、§8.3（line 685）、FG-M（line 507）、SOP〈啟動條件〉否定句 | 無矛盾；殘字見 F-05 |
| D-SCH-3 到期與跳過 | AC-SI-36-1／36-2、R142～R145；C.2 #22 (1) 已將 anchor 改日曆格並撤回 `sched_retry_minutes` | 改動有記載（已知事項）；判序、七值、同格同因一筆 3 處一致 |
| D-SCH-4 Console 兩種寫入 | AC-SI-37-1／37-2、§9.2〈P4 增補〉稽核 body、Console API-SI-12／13、R141 | 一致；`--by console`＋`decider`（§9.7 #86）對照 D-SCH-4 `--by <Console 帳號>` 有註記 |
| D-SCH-5 待入帳自動入帳 | AC-SI-39-1／39-2、SOP 步 1、R149 | 一致 |
| D-SCH-6 核准後機械步驟 | AC-SI-39-3／39-4、38-5、R155 | **F-03** |
| D-SCH-7 無人運轉執行器 | AC-SI-38-1／38-2／38-6、SOP 範本、R150～R156 | Console (a) 運轉不在內：**F-02** |
| D-SCH-8 run-scoped 授權 | AC-SI-38-3／38-4、ADR-SI-15、§9.3 rc 通則、SOP 序列條文、R153 | 現碼事實核實相符（見 F-09）；清單不一致 F-04 |
| D-SCH-9 參數 | §9.2〈P4 增補〉九鍵（現 32 鍵→41）；AC-SI-36-6、NFR-SI-01；AT-440-2 | 一致；`sched_run_budget_minutes` 90 ≤ 240 方向有測試 |
| D-SCH-10 OS 任務 | AC-SI-36-4、R161、SOP〈安裝與憑證〉；三層鎖逐任務逐值 | F-07、F-08 |
| D-SCH-11 Console 顯示與控制 | AC-SI-37-3／37-4／37-5、`status.schedule` 十二鍵（含 C.2 #22 (2) 增三鍵）、Console §0.11、API 契約 §4／§6 | 兩邊逐鍵一致 |
| D-SCH-12 鍵與持有面 | §9.6 P4 列、TCS 檔頭鍵 `monorepo-si-p4-schedule`／`agentconsole-si-schedule` | 一致 |
| D-SCH-13 風險與停機 | AC-SI-36-3／36-6、NFR-SI-01 排程列、AC-SI-37-5（`check` 兩新項）、§10.1 | F-10 |
| D-SCH-14 角色矩陣 | §2.1.1 巡邏器列、AC-SI-38-7 | 一致 |

## D 可測性抽查表（根層 TCS；AT 以映射表統計，現跑腳本核實）

核實指令與輸出摘要：`.venv\Scripts\python.exe -I`（解析 TCS §2 的 AT 區塊）⇒ 96 個 AT／96 唯一／正控 53／負控 43；檔案分佈 `test_selfimproving_schedule_model.py` 32、`..._patrol.py` 34、`..._gate.py` 30（皆 ≤35）；每個 AT 都有 Given／When／Then 與 `[AT_OK_…]`；每個 `-k` 為 AT 底線形加結尾底線（無前綴碰撞）；PRD AC 共 23（36：6、37：5、38：7、39：5），TCS 另自增 `AC-P4-040-1～8`＝共 31，與 TCS 自述相符；`AC-SI-37-4` 於本檔無 AT（委 Console TCS，記載屬實）。

| AC | AT 正／負 | 評語 |
|---|---|---|
| AC-SI-36-1 | 4／4 | 純函式＋注入 `now`，可夾具化 |
| AC-SI-36-2 | 7／3 | 七種跳過各有替身夾具；去重負控在 2-7 |
| AC-SI-36-3 | 2／2 | 雙行程以鎖夾具判 |
| AC-SI-36-4 | 3／2 | 替身後端／`run_argv`；真機屬 P |
| AC-SI-36-5 | 2／2 | 完整 |
| AC-SI-36-6 | 1／1 | 完整 |
| AC-SI-37-1 | 3／2 | G6～G9 前置＝Console 黃金檔 |
| AC-SI-37-2 | 3／2 | 完整；F-03 相關情境缺 |
| AC-SI-37-3 | 2／1 | 完整 |
| AC-SI-37-4 | Console 半 | AC-964-1～4 |
| AC-SI-37-5 | 2／3 | 完整 |
| AC-SI-38-1 | 2／2 | 替身 `claude` 可判，不真起 |
| AC-SI-38-2 | 1／1 | 骨架片段釘住 |
| AC-SI-38-3 | 2／2 | 真值表 AT |
| AC-SI-38-4 | 1／1 | 完整 |
| AC-SI-38-5 | 1／3 | 缺「排程停用」子情境（F-03） |
| AC-SI-38-6 | 1／1 | 完整 |
| AC-SI-38-7 | 1／1 | 完整 |
| AC-SI-39-1 | 1／1 | 完整 |
| AC-SI-39-2～39-5 | 1／0、2／0、1／0、1／0 | 負控在 AT 內（F-11） |
| AC-P4-040-1～8 | 各 ≥1 正 ≥1 負（040-8 僅 1 正） | 範圍守衛可接受 |
| **（缺）** Console (a) 運轉執行與收尾 | 無 | **F-02** |

Console TCS 核實：`# AT-964-…` 區塊 69 個／唯一；對映 `AC-964-1～10` 各 4～14 個（`1:6、2:6、3:7、4:6、5:4、6:6、7:14、8:8、9:8、10:4`，總和 69，與自述相符）；判定指令分 vitest（`-t`）、pytest（`-k`）、gradle（`--tests …AT_964_x_n*`）、playwright（`-g`）；`AT_964_7` 最大序為 9 加 E-1～E-5，無前綴碰撞；所引根層 R 編號（139、141、146、158）皆在根層 TCS 定義範圍內（R137～R165）。

能力登記（`test_selfimproving_capability.py` 判準）對新檔：`sched`／`schedcheck`／`unattended`／`patrolbrief` 為 ro（閉包全 ro）、`schedwrite` rw、`patrol`／`patrolrun`／`schedarm` exec 的分類合理；`runner` 的唯一 `subprocess` 規則與 `run_argv` 靜態不變量有 AT。**唯一不相容＝F-01（禁字樣）**。

## E 契約連動檢核表

| 連動 | 是否列明 | 位置 |
|---|---|---|
| 事件 `sched.set`／`sched.skip`、`run.open` 新欄位 ⇒ `events.py` `_SPEC`／`KINDS`（現 21→23）、trigger 集合（`:184` `abcde`→`abcdef`） | 是 | PRD §9.2；TCS R-事件詞彙、AT-440-1（現查 `KINDS`＝21、`run.open` trigger `abcde` 與規格現況一致） |
| 稽核 JSON 外層七鍵不變、`kind` 新值 ⇒ `consoleaudit.KINDS` 3→5、`SiWriteKind`、Bridge 路由、DB CHECK | 是 | TCS R141；Console API §1.1／§2／§5；V13 內聯匿名 CHECK＋`kind VARCHAR(12)`（`sched-set` 9、`run-request` 11 字元，皆放得下） |
| Flyway 版本「現查＋1」 | 是（現查最大 V22，故 V23；規格不寫死） | API 契約 §5、D-CS-1；PRD C24／FC-p 已加訂正 |
| `status` 新頂層鍵 ⇒ Bridge／backend 原樣轉出、前端 `SI_STATUS_KNOWN_KEYS`、`SiKeyNames` | 是 | Console TCS（`SI_STATUS_KNOWN_KEYS` 10 次、`SiWriteKind` 13 次）、API 契約 §4.1 |
| `params.json` 新鍵 ⇒ `PARAM_SPECS`、`fingerprint`、`non_evolvable`（現 32 鍵→41、`CHECK_RULES_REV` 4→5） | 是 | TCS AT-440-2、R160；`CHECK_RULES_REV` 現值 4 已核 |
| `install_windows_nightly.ps1`＋`scheduled_task_expectations.json`＋`test_install_windows_nightly.py` 任務集合逐字相等 | 是（逐任務逐值） | R161 (b)；`load_trigger_expectations` 對缺 `expected_trigger_time` 已核容忍（`check_scheduled_task_drift.py`） |
| 能力登記計數斷言（51→59／60）、`FORBIDDEN` 清單 | 計數有、**`FORBIDDEN` 清單無** | **F-01** |
| `tools/selfimproving.py` 入口 750 上限、各檔 400 | 是 | R160（`guardrail_cli` 750 已核；現入口 412 行原始行） |
| Bridge `si_cli.py` argv 白名單與 AST 鎖不變 | 是 | API 契約 §2.2、PRD C24 |

## F 誠實劃界

- 全程唯讀；只跑 `git rev-parse`、`git status --short`、`python tools/selfimproving.py status`（印「events_detected: 0」等）、`check_loc_budget.py --json`、我自寫的臨時解析腳本（放 `%TEMP%`，不在 repo），皆未寫 repo 檔案。
- 未逐字讀完兩份 TCS 的每個 Gherkin 情境（根層 1,886 行、Console 1,116 行，且多為極長行）：已機械核實 AT 計數、錨定、GWT／驗收字樣、AC 覆蓋、R 編號引用，並抽讀 R141／R144／R153／R155／R156／R158／R160／R161 與 AT-438-5-E-1；其餘情境內預期值未逐項比對。
- 未執行任何 pytest／vitest／gradle（規格階段尚無測試檔）。
- macOS 路徑、真機 spawn、真 OS 任務屬 P，未驗，規格也已標「未驗」。
- F-02 的「入帳後無人接手」是對字面的推論：我在 PRD／SOP／TCS 皆以關鍵字（「立即啟動」「run-request」「未關運轉」）檢索，未發現任何執行或逾時收尾條文；若主控有口頭裁決在檔外，請補進規格。


## 二審（HEAD 701694ba）

審查 HEAD＝`701694ba3acbb17c3aec8a4e7bcb377bdf5776b2`（`git rev-parse HEAD` 現查；`git status --short` 空）；差異範圍＝`git diff bce6a59c..701694ba --stat` 五檔（PRD 59、SOP 14、根層 TCS 408、Console TCS 6、Console PRD 2 行）。只驗「一審發現是否已結」「D-QA-14～16 落地」「修改是否新生矛盾」。

### 判定：PASS（P1 0／P2 0／P3 4／P4 5；P3、P4 供主控裁決，不擋 PASS）

### 一、F-01～F-13 逐條

| 一審 | 判定 | 落地座標 | 備註 |
|---|---|---|---|
| F-01 P2 禁字樣 vs `schedarm.py` | 已結 | PRD §9.4〈P4 增補〉能力登記段（`FORBIDDEN_EXEMPT={"schedarm.py":(schtasks,launchctl,Register-ScheduledTask)}`、四條核心禁字樣不豁免、負控、`sys.platform` 守衛）＋ADR-SI-14 代價欄；TCS R160、R161(d)、AT-440-3-2（`forbidden_hits` 經豁免後為空）、AT-440-3-3（平台 argv 在守衛內）、AT-440-3-E-1 注入（戊）`sched.py` 加 `launchctl` 仍被抓、（己）`schedarm.py` 加 `time.sleep` 仍被抓、§5.7 同步表（line 1848：`FORBIDDEN` 不動、新增 `FORBIDDEN_EXEMPT`、`FORBIDDEN_SAMPLES` 同步） | PRD 與 TCS 兩處三條豁免字樣、平台守衛、負控逐字一致 |
| F-02 P2 Console (a) 運轉無人執行 | 已結 | PRD 新 AC-SI-38-8（同心跳、不看啟用旗標、不受格線、被擋只寫日誌、收尾同 38-6）＋SC-SI-6、AC-SI-37-2 末句、AC-SI-38-1、AC-SI-36-2 ⑥「本運轉以外」；SOP〈每心跳〉步 1、步 3（line 429、432）；根層 TCS R166、映射表 AT-438-8-1（停用下入帳→同心跳 spawn→無 prop 則 `run-close`、零 `sched.skip`）、AT-438-8-E-1（四種阻擋→日誌、無 skip、運轉仍開、下一心跳 spawn 一次）；Console TCS W-S4 (d′)；Console PRD §0.11 校正 3 | 五處對得上；SOP 步 2 一處殘字見 N-3 |
| F-03 P2 推進路徑髒樹記 skip | 已結 | PRD AC-38-5（只寫日誌、停用時同樣成立）、AC-36-2 末句「`sched.skip` 只在 (f) 到期嘗試寫」、AC-39-3 原句保留；SOP 步 4；TCS R155、AT-438-5-E-1（排程啟用／停用兩子情境，零 `sched.skip`、停用情境事件帳本逐位元組不變） | 與 `due_at` 須格起點、`sched.events` 去重鍵不再牴觸（`SCHED-SKIP-DUE`／`SCHED-SKIP-DUP` 只判非 Console 的到期 skip） |
| F-04 | 已結 | PRD AC-38-3 ③ 現含 `patrol`、`sched arm`、`sched disarm`（共 13 個），與 TCS 「C 類十三個」相符 | |
| F-05 | 已結 | PRD AC-10-3、FR-27 憲法對照、FR-30 定位句改 (a)～(f)（diff 可見） | |
| F-06 | 已結（含一處殘字） | PRD AC-36-1 ②、§9.2 折疊；TCS R142 (b)（重置事件）、AT-436-1-3（第四次 `now` 仍為 `O＋40h`，值不變重送不重置）、R140 `TRIGGER-F-DUE-AT` 改取「最近一次重置事件」 | PRD AC-37-5 仍寫「最近一筆 `sched.set(enabled=true)`」，見 N-1 |
| F-07 | 已結 | PRD AC-36-4、§9.4 設定集（`WakeToRun=false`，nightly／smoke 維持 true）、SOP〈安裝與憑證〉、TCS R161、line 1411 期望值表 | |
| F-08 | 已結 | PRD §9.2 `sched_blackout_local`＝`["21:00-01:30"]`＋WHY 改為「觸發時刻＋常態歷時十倍餘裕、只約束嘗試時刻」；AC-36-2 判準末句；TCS R159（line 121）、AT-440-2-1（line 1621）、D-QA-8 列 | 一審所指「WHY 宣稱涵蓋執行時間」已改寫 |
| F-09 | 已結 | PRD AC-38-3 ② 加註、§9.7 #89 現況清單、C.2 #23；Console TCS §註 4 | |
| F-10 | 已結 | PRD AC-36-3、AC-38-1（脫離式 spawn、`spawn.json`）、AC-38-6（步 0′ 巡視）、§9.4 設定集 `PT1H`；SOP 步 0′、步 3、停用第 4 項；TCS R167、AT-436-3-1、AT-438-6-1／6-2／6-E-1 | 心跳不再被長跑運轉占用，`patrol.lock` 隨即釋放 |
| F-11 | 已結 | 映射表現有 `AT-439-2-E-1`、`AT-439-3-E-1`、`AT-439-4-E-1`、`AT-439-5-E-1`；腳本核對每個 PRD AC 皆有正、負控（唯一例外 `AC-P4-040-8` 只有 1 正控，一審已接受） | |
| F-12 | 已結 | PRD AC-38-2「手寫入 OBS 帳本」 | |
| F-13 | 已結 | SOP 範本步 2、C.2 #22(3)、AC-38-2 | |

### 二、D-QA-14～16

- **D-QA-14 已落地**：PRD AC-38-1／§9.4（三旗標各以 `getattr` 兜底、POSIX `start_new_session`、breakaway 被拒 fail-closed：(f) 記 `sched.skip(spawn-failed)`、(a) 只日誌、V30 真機驗）；SOP 步 3；TCS R167、AT-438-1-E-3（`PermissionError` 注入：(f) 恰一筆 skip、`detail` 以 `breakaway-denied` 起頭；(a) 零 skip；皆無 `spawn.json`、下一心跳成功）。`spawn.json` 欄位 PRD「pid、啟動時刻、硬牆到期時刻」＝TCS `{pid, started_at, wall_due_at}`（另補 `closed_at`），同義。硬牆＝`RESUME_HARD_WALL_SECONDS`，`ExecutionTimeLimit=PT1H` 與 `WakeToRun=false` 只對巡邏任務，nightly／smoke 不動（TCS line 1411）。
- **D-QA-15 大致落地**：Console PRD §0.11 校正 3 已加黑窗句（預設 21:00～01:30）；根層 AC-38-8 明寫受 ②～⑦ 約束含黑窗，AT-438-8-E-1 含黑窗子情境，兩邊同義。缺口見 N-4。
- **D-QA-16 已落地**：PRD AC-36-2 ⑥、§9.3 `run-open` 列、TCS R143 (f)／R166／D-QA-16 列同字；SOP 一處殘字見 N-3。

### 三、機械核對（本回合自跑）

- 根層 TCS（解析 `^# AT-…` 區塊）：AT 標頭 105、唯一 105、全部可解析；正控 56／負控 49，與 §1 自述「105 個 AT（正控 56、負控 49）」相符；測試檔分佈 `schedule_model` 32、`schedule_patrol` 21、`schedule_gate` 31、`schedule_advance` 21（SM32／SP21／SG31／SA21）；每個 AT 有 Given／When／Then 與 `[AT_OK_…]`；`-k` 為錨定名、無不符。映射表列 105、與標頭集合雙向相等；涵蓋 31 個 AC（PRD 24 個含 `AC-SI-37-4` 在本檔無 AT＋自增 8 個，扣掉 37-4 為 31），自述 32 AC 相符。
- Console TCS：`AT-964-…` 標頭 69、唯一 69（未變）。
- `python tools/selfimproving.py check`：`overall=PASS rc=0`（`obs.console_audit` 的 NE 為既有、nonblocking）。
- `python tools/check_pytest_baseline_sites.py`：rc 0（「pytest 基線站點守門通過」）。
- 互引解析：Console TCS 所引根層 R 編號（139、141、146、158、166）與 AT 編號（`AT-437-1-3`）全解得到；根層 TCS 內 R／AT 引用無懸空（僅 R133、R136 指向 P3 TCS、`AT-440-Y-` 為格式說明、`AC-SI-32-1` 為既有 AC，皆非缺陷）。

### 四、新發現（皆非 P1／P2）

- **N-1（P3，修改新生：D-QA-6 連動漏改）**：PRD AC-SI-37-5（約 525 行）`check` 規則仍寫「`origin` 取該 `run.open` 之前最近一筆 `sched.set(enabled=true)`」；D-QA-6 後 origin 是「最近一次重置事件」，TCS R140／R142 已改。照 PRD 字面實作，值不變的重送後 `TRIGGER-F-DUE-AT` 會誤紅。建議把 PRD 該句改為「最近一次重置事件（AC-SI-36-1 ②）」；凍結前改最省。
- **N-2（P3，修改新生：D-QA-10 連動漏改）**：PRD 約 922 行（鐵律三自問）仍寫 `ExecutionTimeLimit=PT5H` 與「硬牆由 `subprocess.run(timeout=…)` 承擔」；約 1132 行（§9.7 FC 列）仍寫巡邏 `ExecutionTimeLimit=PT5H`。與 AC-38-1／38-6／§9.4（`PT1H`、`spawn.json` 硬牆）矛盾。建議改成 `PT1H` 與「硬牆由 `spawn.json` 與步 0′ 承擔」。
- **N-3（P4，修改新生）**：SOP〈每心跳〉步 2（line 431）仍寫 `run-open`（已有未關運轉），未改「本運轉以外」（D-QA-16）。
- **N-4（P3，D-QA-15 部分落地）**：裁決稱「Console TCS W-S4 註已加」，實查 Console TCS 全檔 `黑窗` 為 0 次；W-S4 只新增 (d′)（入帳後由巡邏執行）。Console PRD 要求「對話框摘要顯示黑窗句」，在 Console TCS 沒有對應的 W-S4 (a) 摘要要求或 AT。建議在 W-S4 (a) 加一句摘要含黑窗說明（可併入 AT-964-4-x 既有斷言，不必新增 AT）。
- **N-5（P4）**：Console TCS line 1102 殘留字面「`n4.」——新增的第 4 條與原第 4 條被黏成同一行（PowerShell 換行轉義殘跡），應拆成兩條。
- **N-6（P4）**：PRD C.2 #22(1)、§9.7 #83 仍寫舊 origin 規則；屬歷史裁決紀錄、#23 已覆蓋，可在 #22(1) 加「（#23 D-QA-6 改）」避免誤讀。TCS AT-436-2-2、AT-436-2-E-1（line 492、818）仍以 `["21:00-00:30"]` 當夾具輸入，是顯式夾具值，不依賴預設，無矛盾。
- **N-7（P4）**：TCS line 128 的 R167 與 R165 黏成同一行（`。- **R165 測試 seam`）。映射表 AT-440-3-E-1 描述仍只列原四項注入（本體已含戊、己）。
- **N-8（P4，一審漏看延續）**：`AC-P4-040-8` 僅 1 個正控 AT，無負控；一審已接受，維持。

### 五、三件事結論

1. F-01～F-13 全數已結；三條 P2 皆在 PRD／SOP／兩份 TCS 對得上（F-01 兩處一致含負控 AT；F-02 五處一致；F-03 與 skip 只在到期寫、`due_at` 格起點、去重鍵不再牴觸）。
2. D-QA-14、D-QA-16 已落地無矛盾；D-QA-15 在 Console PRD 與根層兩邊同義，但 Console TCS 缺黑窗摘要要求（N-4，P3）。
3. 機械核對全過（105 AT／32 AC、SM32／SP21／SG31／SA21、Console 69、`check` rc 0、基線站點 rc 0、互引無懸空）；新發現為 PRD 兩處殘字（N-1、N-2）等 P3／P4，無 P1／P2。

## 主控補記（2026-11-09 13:4x +08:00）

- 採納二審 PASS（P1 0／P2 0）。P3／P4 備註 N-1～N-7 由主控依「修復不留後遺症」當場編修進規格、不另開修復棒（commit `a49f7cf6`：PRD AC-SI-37-5 `origin` 定義對齊 D-QA-6、§9.4 鐵律三自問與 §9.7 FC-i 的 PT5H→PT1H 與硬牆改由 `spawn.json`＋步 0′ 承擔、#83 與 #22(1) 加 #23 註記、§13.3 補記；SOP 步 2 `run-open` 判準改「本運轉以外」；根層 TCS R165 自 R167 行尾獨立並歸位、映射表 AT-440-3-E-1 補（戊）（己）；Console TCS W-S4 (a) 確認摘要須含黑窗說明、§7.2 第 5 項拆行）；N-8 維持一審接受。兩份 TCS 追溯表 digest 依磁碟現值重算。
- 主控親驗（當回合真跑）：五檔零 CR；`python tools/selfimproving.py check` overall=PASS rc 0；`check_pytest_baseline_sites` rc 0；`test_selfimproving_events -k sop`、`p2_meta`＋`p3_meta` 皆綠。
- 流程：PRD 鍵 `monorepo-selfimproving` 依凍結常態規則由主控正式重凍（SPEC_FROZEN→SPEC_DRAFTING→SCG_VALIDATION→gate PASS→HUMAN_PENDING→spec-frozen Stage-1，approver 引 sid d6dfce97 line 13）；凍了 SelfImproving PRD／Console PRD 的 RELEASE 鍵一律 spec-refreeze；新鍵 `monorepo-si-p4-schedule`（根層）與 `agentconsole-si-schedule`（Console）open 至 IMPLEMENTATION。各步 rc 見落檔本報告的 commit 訊息與兩個 FSM 狀態目錄。
