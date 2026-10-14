# agent_briefs — 派工任務書（歷史存檔＋下一輪重派的底稿）

本目錄是主控（Fable）在 2026-10-14～15 Mac 輪派給 Sonnet 子 agent 的任務書原文，**照搬自該 session 的 scratchpad**，供下一輪（Windows）直接複製、改路徑後重派。

| 檔案 | 用途 | 狀態 |
|------|------|------|
| `COMMON_CONTEXT.md` | 每位 agent 共用背景：已拍板決策、鐵律、交卷格式、跨平台規則、三節補充 | 持續有效（路徑段落是 Mac 現況，Windows 要改） |
| `W1_ARCHITECT.md` | 架構文件＋RTM＋計畫書 | 已完成 |
| `W1_BRIDGE.md` | Engine Bridge（FastAPI） | 已完成（兩個前提被實證推翻，見 COMMON_CONTEXT〈補充〉〈補充二〉） |
| `W2_BACKEND.md` | 後端 Phase 1＋2 | 已完成 |
| `W2_INFRA.md` | Docker Compose＋PG18 備援／備份／監控 | 見 Implementation_Plan 進度帳 |
| `W3_FRONTEND.md` | 前端 Phase 1＋2（含 M1～M4 分階段） | 已完成 |
| `W3_BACKEND_P3-6.md` | 後端 Phase 3～6（匯入／執行／監控／設定） | **未派**＝Windows 輪第一棒 |
| `DOC_CORRECTIONS.md` | Bridge 實作與文件的差異回寫清單 | 主控收尾套用 |

🔴 任務書內的絕對路徑（`/Users/...`、`/private/tmp/...scratchpad...`）是 Mac 那台機器的現況，不是常數；Windows 重派時改成該機 repo 根與 scratchpad 的路徑，其餘內容照用。前端 Phase 3～6 的任務書尚未撰寫（要等後端 Phase 3～6 的 OpenAPI 定案後再寫）。
