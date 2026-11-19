# 四問審視 RUN-SI-014
## Q1 此頂尖專家會做那些我沒有想到的事？
- Q1-1｜領域：無人續跑的升版漂移防護｜做法：無人續跑顯式停用被 hook 延後的工具呼叫自動恢復｜機制：在續跑行程環境注入 CLAUDE_CODE_DISABLE_DEFERRED_TOOL_RESUME，使 claude -p 續跑不執行延後的呼叫｜座標：src=cc-releases CLAUDE_CODE_DISABLE_DEFERRED_TOOL_RESUME｜查詢：「延後的工具呼叫」＝零命中｜查詢：「無人續跑」＝命中不涵蓋：OBS-SI-428 只釘中斷回合重跑開關，未涉及被 hook 延後的工具呼叫恢復
## Q2 在哪裡找到最前沿的資料與研究結果？
- Q2-F1｜來源：cc-releases｜座標：src=cc-releases CLAUDE_CODE_DISABLE_DEFERRED_TOOL_RESUME｜發現：新環境開關可讓 claude -p 續跑不再執行被 hook 延後的工具呼叫，本 repo 目前沒有 hook 回傳延後，屬預防性釘住
## Q3 使用哪些方法與工具？
- Q3-1｜對象：Q1-1｜方法：顯式環境釘住加上續跑行為的真行程重放驗證｜工具：tools/lib/model_roles.py、tools/selfimproving.py、外部：Claude Code CLI（src=cc-releases）
## Q4 如何證明資料與改善結果是有正面影響與收斂的？
- Q4-1｜擬提案：無人續跑顯式停用延後工具呼叫恢復｜指標類別：症狀：續跑後執行了未經當前守衛核准的工具呼叫｜症狀定義：`python tools/selfimproving.py check`｜反證：若停用後續跑仍執行延後的呼叫，或守衛新增 defer 後續跑行為與預期不符，改善不成立｜收斂：依 PRD 的收斂判定，同一類升版漂移不再於後續運轉重現
