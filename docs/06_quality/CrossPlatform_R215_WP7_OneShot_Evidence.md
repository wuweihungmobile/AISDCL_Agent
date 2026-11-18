# R215 WP-7 一次性真機驗證證據（非 sessionctl 待驗項）

**執行**：2026-11-18 20:4x～21:0x，WP-7 驗證棒（Sonnet），主控 sid 89c354d9 親驗殘留與 smoke。
**設計**：`CrossPlatform_R215_PendingVerification_Closure.md` §2 #38～#57、§6b-6。原始輸出原在主控 scratchpad `wp7\`（臨時，以本檔為準）。

| # | 判定 | 關鍵證據 |
|---|---|---|
| 38 | PASS | 官方 statusline 文件欄位表含 `rate_limits.five_hour／seven_day.used_percentage`、`resets_at` |
| 40 | PASS | 回讀 ff1000ed 逐字稿：605 筆 `cwd` 全為 `D:\CursorProject\AISDCL_Agent` |
| 48 | PASS | `gh run view 44231147621`（e8949650）：三測試分片 15.8／22.4／23.0 分、彙總 0.9 分，全 success；分片前基線 59 分 |
| 49 | PASS | 461：`misstep_attribution.py` rc 0；判準④「管線尾節是 rc 遮蔽型濾器」於 10-03 之後 78 場 session 命中 0（無修前對照：10-03 前無逐字稿）。462：假 HOME 跑 SessionStart hook rc 0，`systemMessage` 帶「statusLine 未安裝…貼上即安裝」 |
| 50 | PASS | `git log -S`：修法 b1ef81f5（`classify_probe_output`、`_remove_unless_self`）與 bfb07cf1（`Inv1…`）皆在 HEAD；帳本 :166／:167「工作樹待收尾 commit」為過時文字 |
| 51 | PASS（部分） | 真 `AutoResumeService`＋真 hook＋真 schtasks：回 `external_resume_required`、註冊 `AutoSDD_EngineResume_…`（NextRunTime 21:03）、`--remove` 後 0；另一次性 job 20:53 到點觸發、跑 engine（rc 1，playbook 刻意壞 yaml 免耗 token）後自拆。**未驗 engine 真跑出結果** ⇒ 第二波 RV 案例補 |
| 52 | PASS | `node:22-alpine` 唯讀 bind：主機 `os.replace` 三次，容器讀到 v2／v3／v4；容器寫入回 Read-only file system |
| 53 | PASS（Windows） | 內容同 #51；launchd 側在 mac，本機不可達（C：另機） |
| 54 | PASS | `windows_smoke_local.ps1`（`powershell.exe` 5.1）rc 0、`PASS=13 FAIL=0`（主控親驗）；「LATEST .sh 可啟動」step PASS |
| 55 | PASS | 事件帳本 seq 98／99：`by=patrol`、`kind=research.registry`、`carrier=console`、2026-11-11 10:30:02；RTM-SelfImproving-P6 檔頭「AT-645-4-1 仍待真機觸發」為過時文字 |
| 56 SEC-4 | PASS | `taskkill /T /F` 殺 cmd→cmd→ping 三層樹 rc 0、子孫無殘留 |
| 56 SEC-5 | PASS（本機） | 原生 `claude.exe` 名稱符合 `claude*` 過濾；npm 版 `node.exe` 本機不可重現（C：另機） |
| 56 SEC-8 | PASS | `washed_env` 洗掉 `CLAUDE_CODE_*`、`CLAUDECODE`、`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`，洗後 `claude -p --model haiku` rc 0、認證正常 |
| 56 SEC-10 | 改判 C | 需兩個互動 session 互打 agent id；harness 行為、無暴露證據 ⇒ 理論洞清單（主控裁決 §6b-6） |
| 57 | PASS | `test_context_budget_guard.Inv5SingleOwnerTest` rc 0（12 OK、skipped=1 為 MAC 對照）；真 `Get-ScheduledTask` 那條實跑 |

**殘留清理**：`docker ps -a --filter name=wp7` 空；`AutoSDD_EngineResume*`／`AutoSDD_RV_*` 排程 0（主控 21:0x 親驗）；無殘留 PING.EXE；未碰 `autoclaude_pg`、Sentinel、SI_Patrol。
