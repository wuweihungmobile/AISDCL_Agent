# 裁決存證：全自動續跑（含 commit/push）＋今晚未續跑根因

- **Status**：Adopted（掌舵者 2026-09-02 直接指令，經一次 AskUserQuestion 重申）
- **日期**：2026-09-02
- **關係**：承接 [ADR-XPLAT-014](ADR/ADR-XPLAT-014-resume-chain-hardening.md)（resume chain hardening，已 Adopted）與缺陷 DEF-200-231。本檔只記「掌舵者對自動化程度的裁決」＋「今晚未續跑的實測根因」，設計細節一律回讀 ADR-XPLAT-014，不重述。

## 1. 掌舵者裁決（逐字重申）

掌舵者原話：「Token用盡時，為何沒有啟動下一個Reset的喚醒機制，不需要人類介入，這樣才符合開發自動化！請檢討任務沒有繼續的根因，並且徹底改善！」

以 AskUserQuestion 提兩個選項（半自動：醒來做完停在 commit/push 前等確認；全自動：連 commit/push 都自己來），掌舵者選 **全自動：連 commit/push 都自己來**。

⇒ 裁決結論：**授權無人看管的續跑那一跑可以 commit／push**。這**超出** ADR-XPLAT-014 §3.4 建議案 B（acceptEdits，明文保留 commit/push 封鎖），等同採 §3.3 方案 F 的能力面，而 PRD §4.5.4／§13 明文禁止把「完全跳過權限」當預設 ⇒ **須經 PRD 修憲＋四方複審才能落地**（見 §4）。

## 2. 今晚（2026-09-02）未續跑的實測根因

哨兵稽核痕跡（`autosdd_resume_log_...jsonl`）逐字（本場現讀）：
- 20:00:33 `sentinel_woken`
- 20:00:34 `sentinel_decided`：`action=disarm`、`reason="無未處理撞線，且逐字稿已靜止 22472s（≥21600s）⇒ 工作已結束 ⇒ 靜默解除"`、`controller_idle_seconds=22471`、`quota_band=unmeasured`
- 20:00:35 `sentinel_disarm`：`unregister_rc=0`

三層根因：
1. **今晚是預防性停止，不是真撞線**：13:12 撞的是 `context_budget_guard.py` 的 band=halt／cap=0（hook 訊息），不是 API 層 429。`sentinel_decide()`（`tools/session_resume_planner.py:662`）只在逐字稿有「未處理撞線事件」（`guard.unhandled_limit_event()`）時走 `arm_reset`／`probe`／續航；預防性停止結構上不是撞線事件 ⇒ 續航排程（`--arm-endurance`→`_resume_tick`→`claude -p -r`）**從未被掛上**。
2. **哨兵自我解除門檻分不出「暫停等 reset」與「工作完成」**：`SENTINEL_IDLE_SECONDS=6h`（`:324`）；逐字稿安靜 ≥6h 即判 `disarm`（reason「工作已結束」）。今晚我停手等 reset，逐字稿安靜超過 6h ⇒ 被判「下班」。
3. **AUTOSDD_RESUME_OFF 不是今晚死因**（與 R108 事故不同）：本場三層現查 `User=`／`Machine=`／`Process=` 皆空。

## 3. 落地狀態現查（本場，比 ADR 8/28 快照新）

- 缺陷②（方案 B：acceptEdits＋禁 commit/push）：**已落地**。`session_resume_planner.py:1141` argv 帶 `--permission-mode`；`:1069` 訊息「自動續跑預設開；禁 commit／push，由 UNATTENDED_ENV 配 PreTool 擋」；`:1203` spawn 帶 `env={... UNATTENDED_ENV:"1"}`。
- 缺陷①（時刻解析階梯）：**未落地**。`DEFAULT_AT_EXPR = "(Get-Date).AddHours(5)"`（`:289`）仍是 `--at` 預設（`:935`）。
- 缺陷③（哨兵存活監測）：`sentinel_lifecycle.py` 有 `armed_but_missing`；偵測面部分在。
- 落點檔 `session_resume_planner.py` 現查 **750/750、headroom 0**（比 ADR 記的 749/750 更滿）⇒ 寫缺陷① 前 ⓿ 抽模組是硬前置。

## 4. 落地計畫（依 ADR-XPLAT-014 §7 順序＋本裁決新增第 5 項）

本工作＝DEF-200-231 落地，**自成一個開發輪，非 R121 純結案輪射程**（R121 不動 tools/tests、淨額≤0）。順序：

1. **⓿ 抽共用模組**（純減法、收尾單人窗口、跑全套）：`autocompact_posture/report`＋`check_report`＋三常數 從 planner 搬 `endurance_env.py`，釋 ≈46 LOC。ADR §7.0-a/§7.0-b。
2. **缺陷① 時刻解析階梯**（L0~L4＋F1/F2/F3＋刪 DEFAULT_AT_EXPR＋白名單兩格）。ADR §2。
3. **今晚 bug 修復（本裁決新增）**：預防性停止（band=halt cap=0）且磁碟有未完成任務書時，`context_budget_guard.py` 的 halt 路徑除了武裝哨兵，另**掛續航排程**（`--arm-endurance` 讀實測 reset）＋哨兵自我解除門檻改為「有未完成任務書＋reset 已過 ⇒ 續跑而非 disarm」。載體 DEF-200-231。
4. **缺陷② 已落地**，僅需複審確認。
5. **commit/push 授權（本裁決新增，須修憲）**：PRD §4.5.4／§13 修訂 → 無人續跑那一跑取得 commit/push 權，且**帶護欄**（建議：只在該輪已過四方複審＋全套綠時才允許自動 push，否則只 commit 不 push、留給人確認）。草案＝`PRD_Amendment_R121_UnattendedCommitPush.md`。
6. **四方複審**全案（安全關鍵：無人看管 commit/push），收斂後落地。

## 5. 禁止事項

- 不得直接把 `AUTOSDD_UNATTENDED` 的 commit/push 封鎖拆掉了事（那是方案 F 的裸形態，PRD 禁）；必須走修憲＋護欄＋四方。
- commit/push 護欄未過四方前，無人續跑維持方案 B（能改檔、不自動 push）。
- ⓿ 是純減法 ⇒ 收尾單人窗口做、禁與 ①③ 並行、跑完全套才開 ①。
