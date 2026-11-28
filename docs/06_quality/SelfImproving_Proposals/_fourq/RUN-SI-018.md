# 四問審視 RUN-SI-018
## Q1 此頂尖專家會做那些我沒有想到的事？
- Q1-1｜領域：Agent 記憶工程｜做法：記憶條目降級前先做反事實重放，取該條目所守教訓的歷史失誤型逐字稿，驗證移除後主控不會再犯｜機制：以逐字稿母體中同型失誤的再現與否判定條目是否仍承重，不承重才允許降級搬出索引，有別於 OBS-SI-446 只依最後引用時間排序｜座標：docs/06_quality/SelfImproving_Observation_Ledger.md:455、src=arxiv-agents persistent-state updates do not necessarily improve subsequent performance｜查詢：「反事實重放」＝零命中｜查詢：「條目是否仍承重」＝零命中
## Q2 在哪裡找到最前沿的資料與研究結果？
- Q2-F1｜來源：arxiv-agents｜座標：src=arxiv-agents persistent-state updates do not necessarily improve subsequent performance｜發現：自演化代理的持久狀態更新不保證後續表現變好，記憶變更需獨立驗證而非預設有益
## Q3 使用哪些方法與工具？
- Q3-1｜對象：Q1-1｜方法：反事實重放（以既有逐字稿母體對照條目存在與否的同型失誤再現）｜工具：tools/probe/waste_census.py、tools/lib/selfimproving/capacity.py、tools/lib/selfimproving/memdir.py、外部：EvoLink-Bench 的持久狀態分層評測思路（src=arxiv-agents）
## Q4 如何證明資料與改善結果是有正面影響與收斂的？
- Q4-1｜擬提案：記憶索引降級前反事實重放驗證｜指標類別：症狀：降級條目所守的同型失誤再現｜症狀定義：`python tools/selfimproving.py status`（memory_index 行的再達容量事件）｜反證：降級後同型失誤在後續逐字稿再現且對應到被降級條目，或索引仍需人工歸檔｜收斂：引 PRD〈M1 判定細則〉，可評估採納窗內同根因不再復發，且容量事件不再重開
