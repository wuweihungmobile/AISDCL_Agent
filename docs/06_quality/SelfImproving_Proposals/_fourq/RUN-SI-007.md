# 四問審視 RUN-SI-007
## Q1 此頂尖專家會做那些我沒有想到的事？
- Q1-1｜領域：自我改進系統的跨運轉記憶｜做法：把運轉結論分成情節與程序記憶兩類，各自設定淘汰規則｜機制：每次運轉結束時把事件經過寫入情節層，把已被驗證的做法提煉進程序層，並依各層規則淘汰過期條目｜座標：src=anthropic-engineering components of agent memory｜查詢：「情節與程序記憶」＝零命中｜查詢：「各自設定淘汰規則」＝零命中
## Q2 在哪裡找到最前沿的資料與研究結果？
- Q2-F1｜來源：anthropic-engineering｜座標：src=anthropic-engineering Harness design for long-running application development｜發現：新增長時間運轉 harness 設計文章，可回頭對照本 repo 無人運轉的接力與收尾設計，但本輪只讀到標題，未讀正文
## Q3 使用哪些方法與工具？
- Q3-1｜對象：Q1-1｜方法：分層記憶設計加前後對照回放｜工具：tools/selfimproving.py、tools/lib/selfimproving/fourqparse.py、外部：Anthropic 工程部落格（src=anthropic-engineering）
## Q4 如何證明資料與改善結果是有正面影響與收斂的？
- Q4-1｜擬提案：迴圈記憶分層與淘汰規則｜指標類別：M1｜症狀定義：docs/01_requirements/SelfImproving_PRD.md:68｜反證：可評估的採納窗內同根因事件仍連續復發，即分層沒有降低再現｜收斂：依 PRD 的 M1 判定細則，採納後同根因事件在可評估窗內不再復發；樣本不足一律視為 NOT-EVALUABLE
