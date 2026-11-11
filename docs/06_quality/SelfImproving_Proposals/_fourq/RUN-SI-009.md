# 四問審視 RUN-SI-009
## Q1 此頂尖專家會做那些我沒有想到的事？
- Q1-1｜領域：代理記憶的離線校驗｜做法：定期回頭檢驗已存記憶條目，以原始逐字稿為真相修正錯誤或過期者｜機制：在離線時段重放逐字稿，比對逐字稿真相後改寫與其不符的筆記｜座標：src=anthropic-agent-memory Dreaming can correct memory｜查詢：「回頭檢驗已存記憶」＝零命中｜查詢：「比對逐字稿真相」＝零命中
- Q1-2｜領域：代理記憶的寫入準則｜做法：記憶只存環境讀不到的策略與已驗證規則，不存可即時讀回的狀態｜機制：寫入前先判斷該資訊可否從現場重新取得，能者不寫｜座標：src=anthropic-agent-memory can be read off the screen every turn｜查詢：「環境讀不到」＝零命中｜查詢：「從現場重新取得」＝零命中
- Q1-3｜領域：多代理共用記憶的寫入衝突｜做法：每個記憶頁只交給單一代理寫入，多代理並行時不共寫同一張共享表｜機制：每份來源各開一頁並逐字引用原文，不彙整進共用表以免互相覆寫｜座標：src=anthropic-agent-memory several agents wrote to a shared table of contract terms｜查詢：「單一代理寫入」＝零命中｜查詢：「逐字引用原文」＝零命中
## Q2 在哪裡找到最前沿的資料與研究結果？
- Q2-F1｜來源：anthropic-agent-memory｜座標：src=anthropic-agent-memory Dreaming can correct memory｜發現：本輪已讀全文，內容含離線整理記憶、記憶頁單一寫入者、記憶庫膨脹到比原始資料還大的失敗例，皆為本迴圈未涵蓋的做法
- Q2-G1｜URL：https://www.letta.com/blog｜分級：T2｜為何前沿：提出離線時段重整記憶的原始團隊，文章引為 dreaming 的出處之一｜更新頻率：約每月數篇
- Q2-G2｜URL：https://github.com/anthropics/anthropic-cookbook/commits/main.atom｜分級：T1｜為何前沿：文章末段指向 dreaming 與知識 wiki 的官方操作範例，可看實作細節｜更新頻率：近乎每週有提交
## Q3 使用哪些方法與工具？
- Q3-1｜對象：Q1-1｜方法：離線回放校驗（dreaming）加前後對照回放｜工具：tools/selfimproving.py、tools/lib/selfimproving/fourqparse.py、外部：Anthropic 工程文章 The components of agent memory（src=anthropic-agent-memory）
- Q3-2｜對象：迴圈記憶分層與淘汰規則｜方法：記憶層級設計，頂層注入索引保持精簡、細節下移並留連結，加上晉升降級與淘汰規則，以前後對照回放驗證｜工具：tools/selfimproving.py、docs/06_quality/SelfImproving_Observation_Ledger.md、外部：Anthropic 工程文章 The components of agent memory（src=anthropic-agent-memory）
## Q4 如何證明資料與改善結果是有正面影響與收斂的？
- Q4-1｜擬提案：迴圈記憶分層與淘汰規則｜指標類別：M1｜症狀定義：docs/01_requirements/SelfImproving_PRD.md:70｜反證：可評估的採納窗內同根因事件仍連續復發，即分層沒有降低再現｜收斂：依 PRD 的 M1 判定細則，採納後同根因事件在可評估窗內不再復發；樣本不足一律視為 NOT-EVALUABLE
- Q4-2｜擬提案：迴圈記憶分層與淘汰規則｜指標類別：症狀：記憶索引逼近載入上限而被截斷｜症狀定義：docs/06_quality/SelfImproving_Observation_Ledger.md:26｜反證：歸檔與淘汰後索引仍反覆逼近同一上限，表示淘汰規則沒有阻止累積｜收斂：依 OBS-SI-016 登記的再開症狀判定，採納後不再於該症狀下重開
