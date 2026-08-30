# CrossPlatform R111 哨兵事故鑑識（mac）— 429 同池同死 → 續跑鏈喚醒成功、授權層卡死

> 定位：2026-08-29 夜間 429 事故的鑑識定論落磁碟（單一窗口落帳；時間一律台北 +08:00）。
> 效力聲明：標「✓現查」者＝本檔寫下當回合對痕跡檔逐字核實；標「主 jsonl」者＝自
> `~/.claude/projects/<slug>/1f557657-….jsonl` 取證（429 時刻與 resetsAt 已抽查核實）。
> 證據座標：resume log＝`$TMPDIR/autosdd_resume_log_autosdd_resume_plan_1f557657-….jsonl`
> （事件鍵＝`event`/`at`）；bootout log＝`~/.autosdd/traces/autosdd_sentinel_bootout_
> AutoSDD_Sentinel_1f557657-….log`；armed stamp＝`$TMPDIR/autosdd_sentinel_armed_1f557657-….json`。
> ⚠ resume log 住系統暫存：重開機即消失，「查不到」≠「沒發生」（既有紀律）。

## §1 時間軸（逐時刻）

| 時刻 | 事件 | 證據 |
|---|---|---|
| 22:13 | R111 修復 agent 啟動（單人窗口） | 主 jsonl |
| 22:31 | 主控最後一次回應 | 主 jsonl |
| 22:32 | 主控著手寫任務書＋武裝哨兵（未及完成帶寫） | 主 jsonl |
| 22:42:04 | R111 agent 撞 429（five_hour；`resetsAt=1788015600`＝23:00+08:00） | ✓現查（主 jsonl `2026-08-29T14:42:04Z` 起 429 事件 45 筆） |
| 22:42:05 | 主控同秒死（同一個 five_hour 池） | 主 jsonl |
| 22:50:47 | 哨兵巡邏 `sentinel_woken`→`sentinel_decided action=arm_reset`（「偵測到未處理的撞線；觀測 reset=2026-08-29 23:00:00+08:00 尚未到」）→ 重排 `fire_at=23:02:00` | ✓現查（resume log :138-141） |
| 23:00 | five_hour reset | 主 jsonl（resetsAt）✓ |
| 23:05:48 | 哨兵醒（`woken`）＋決策 `probe`（節錄：「觀測 reset…已過 ⇒ 花一次探測」） | ✓現查（resume log :142-144） |
| 23:05:52 | `probed rc=0 quota_open=true`；`route_chosen strategy=SESSION_RESUME`（「逐字稿可用（2,240,968B ≤ 上限 33,554,432B）⇒ 帶完整 context 續跑」） | ✓現查（resume log :145-146） |
| 23:05:53 | headless 續跑窗口啟動 | 主 jsonl |
| 23:06:14 | 續跑窗口重武裝**同名**哨兵（`sentinel_armed`）＋寫 armed stamp | ✓現查（resume log :147） |
| 23:06:38~23:09 | 續跑窗口全面唯讀（連 `git status` 都要人工核可）⇒ R111 零推進 | 主 jsonl＋收窗備忘錄 |
| 23:10:31 | 續跑窗口誠實收窗（備忘錄節錄：「受阻收窗——續跑鏈本身運作成功，但本窗口 Bash／磁碟寫入全面需人工核可，無法續作工程」「R111 半套現場（18 支 modified、未 commit）原樣保留」） | ✓現查（resume log :148 `resumed rc=0`＠23:10:32） |
| 23:10:33 | deferred watchdog 判 parent-gone 執行 bootout（逐字：`parent-gone waited=1s at 2026-08-29T15:10:33Z`／`bootout rc=0`）——**拆掉的是 23:06:14 剛武裝的新哨兵**；armed stamp 未清（本檔寫下當回合該 stamp 仍在磁碟上 ✓） | ✓現查（bootout log＋stamp 檔） |
| 23:10:33~23:22:54 | 真空 12.4 分：無哨兵、無主控、無續跑窗口 | resume log 零事件（區間內無列）✓ |
| 23:22:54 | 使用者手動介入 | 主 jsonl |
| 23:24:19 | 主控重武裝哨兵（`sentinel_armed`）＋復活 R111 agent | ✓現查（resume log :149） |

## §2 根因分層

1. **喚醒鏈成功、卡死在授權層＝DEF-200-231②**（續跑帶受控授權，已裁未實作）。本次每一段
   機械鏈（撞線偵測→改排 reset→探測→選路→帶 context 續跑）全數成功，續跑窗口也誠實收窗
   ——死因不在鏈，在窗口無授權。🔴 裁決注記寫「執行=Windows」，而本次事故整段發生在 mac
   ⇒ **231② 的射程必須擴到 mac**（帳本 231 列已補指針）。
2. **「哨兵已死」表徵＝D3＋D4 在 mac 側首次實測重演**（ADR-XPLAT-014 §4.0 已預告的形狀）：
   D3＝喚醒完成即無條件自刪，且 23:06:14 續跑窗口武裝的**同名**新哨兵被 23:10:33 的
   deferred watchdog 一併拆掉（同名 race：watchdog 拆的 label 分不出「舊的我」與「新的接班者」）；
   D4＝bootout 後 armed stamp 未清 ⇒ 事後任何讀 stamp 的判斷都會誤信「哨兵還在」。
3. **工具文案同形不同因**：`sentinel_lifecycle.py:128` 一帶注記的「2026-08-16 事故形狀」是
   「任務書被覆寫致零排程」；本次任務書健在、喚醒有發生——把本次讀成 08-16 復發會修錯層。

## §3 耗用歸因與劃界

- 22:42~23:00：本機**零 API 活動**——無自動重試、無 fallback 池（同池同死 ⇒ 兩個行程都
  燒不動）。
- 23:00~23:22 的耗用＝哨兵探針一次（`probed rc=0`）＋headless 續跑窗口以 2,240,968B 逐字稿
  重放完整 context 一次；該窗口其後全面唯讀、零工程產出。
- 劃界：`quota_burn.jsonl` 在 22:11（77%）~23:23（81%）之間**零取樣** ⇒ +4pp 無法逐分鐘
  歸因（落款「沒觸發＝檔不長大」）；週配額是帳號級，他機（兩支 14h peer session，空窗期
  零逐字稿寫入＝非本次來源）對本機不可見。不做「唯一來源是 X」的宣稱。

## §4 機械修法清單（標注射程）

| # | 修法 | 射程歸屬 |
|---|---|---|
| 1 | D4：bootout 路徑清 armed stamp（拆哨兵與拆憑證同一原子動作） | ADR-XPLAT-014 已裁射程 |
| 2 | D3（mac 版）：deferred watchdog 不得拆**接班者**——同名 label 需帶代次/所有權標記，或 parent-gone 判定改綁「武裝者行程」而非 label；喚醒受阻（授權層卡死）不得進 TERMINAL | ADR-XPLAT-014 已裁射程 |
| 3 | DEF-200-231② 落地（續跑帶受控授權），**射程含 mac**（本檔 §2-1 取證） | ADR-XPLAT-014 已裁射程＋本檔擴 mac |
| 4 | PostToolUse 水位鉤子順帶 stamp-vs-launchctl 自癒（stamp 說 armed 而 launchctl 說不存在 ⇒ 當場重武裝或清 stamp 出聲） | 新（本檔提出） |
| 5 | `sentinel_lifecycle.py:128` 誤導文案修正（08-16 形狀＝任務書覆寫；與本次「喚醒成功卡授權」分開記載） | 新（本檔提出） |
| 6 | 無主模式缺口（主控死而 tasks/ 有活體時無人統籌）＝DEF-200-234 新列；設計併 ADR-XPLAT-014（哨兵巡邏 tick 增列該分支） | 新列立案 |
