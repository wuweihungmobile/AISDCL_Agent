# DEF-200-275 證據檔：SDD-FSM context/budget 計量表誤差與 ESCALATION 誤觸

> 本檔為 `docs/06_quality/AutoSDD_Defect_Log.md` 該列的體積守門接收端（`ROW_MAX_BYTES` 洩壓）；
> 列上只留一句話與本檔指針，逐字原文住這裡。

## 現象（2026-09-08 掌舵者直接發現）

SDD-FSM 的 context/budget 計量表長期量錯，與真實用量差 4 倍以上，且會誤觸 ESCALATION
硬鎖死全部工具呼叫：DEF-200-274 第四輪 Workflow（13 agent、125.6 萬 token）跑到一半，
FSM 自報 `INIT->AUTO_COMPACT_PENDING [auto_compact_trigger] ratio=91.11%`，隨後狀態被
推進 `ESCALATION`（R-9.5「不可自動退出」），連 `Read`/`Bash`/`Task` 等工具全數被
PreToolUse 擋下，之後又自報「context ratio 118%（cumulative=236279），下次 PreToolUse
將拒絕」；但使用者同時以內建 `/context` 指令實測**真實用量僅 29%（285.5k/1M
tokens）**，兩者差約 4 倍。

同型「hook 猜測值 vs `/context` 實測值」落差本專案已有 2 次前例（見 memory
`reference_context_window_check_via_slash_command.md` 記載 R105 967k vs 猜測 200k、
R106 猜測/實測差 4.8 倍），本次為第 3 次復發，屬結構性未修的計量錯誤，非單次偶發；且
這次額外造成**假警報升級成 ESCALATION 把整個 session／並行子 agent 全部鎖死**，代價遠
高於前兩次單純誤報。

## 建議或已採取的處置

找出 FSM 用來算 `cumulative`／`context ratio` 的計量邏輯（推測在
`AISDLC_SDD/<LATEST>/tools/fsm_runtime/` 或 `.claude/hooks/sdd_hook_router.py` 一帶），
釐清它跟真實 model context window（`/context` 可查的權威值）在分子／分母定義上的系統性
落差；修到量出來的百分比與 `/context` 同量級，而非只是拉高閾值治標；同時檢討「量錯就
自動 ESCALATION 鎖死全部工具且不可自動退出」這個懲罰是否與量測可信度不成比例。

## 狀態

open（未指派）：本 session（DEF-200-274 第四輪工作流收尾）親眼撞見＋使用者親自用
`/context` 對照實測，尚未查驗計量器原始碼（本輪 ESCALATION 期間工具被擋，尚待後續
session 查）。

本項與 DEF-200-274（根層測試 runner 平行化）是兩個獨立的缺陷——DEF-200-275 只是在
DEF-200-274 第四輪的 Workflow 執行期間被撞見，兩者的修復範疇不重疊，本檔不負責處理
DEF-200-275 本體（那需要進入 AISDLC_SDD 子專案查 FSM runtime 原始碼，超出本輪工作
範疇）。
