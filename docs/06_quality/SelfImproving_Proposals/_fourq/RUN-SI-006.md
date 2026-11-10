# 四問審視 RUN-SI-006
## Q1 此頂尖專家會做那些我沒有想到的事？
- Q1-1｜領域：自我改進系統評測｜做法：以已結案缺陷的修復前快照做反事實重放，檢驗提案器能否重現當年的實際修法｜機制：在拋棄式沙盒檢出缺陷修復前的 commit，重跑擷取到提案全流程並與實際修復差異比對｜座標：tools/probe/sentinel_decide_replay.py:1、tools/lib/selfimproving/fourqparse.py:1｜查詢：「修復前快照」＝零命中｜查詢：「反事實」＝命中不涵蓋：僅在無關的稽核敘述出現，與迴圈對歷史缺陷的回測無關
## Q2 在哪裡找到最前沿的資料與研究結果？
- Q2-F1｜來源：cc-releases｜座標：src=cc-releases into a directory writes｜發現：新版修正了 deny 規則與受保護檔提示對 cp／mv 寫入目錄不生效，屬守衛面繞過類的上游修補，可回頭核對本 repo 守衛對同形態的覆蓋
## Q3 使用哪些方法與工具？
- Q3-1｜對象：Q1-1｜方法：反事實回測加沙盒重放｜工具：tools/selfimproving.py、tools/lib/selfimproving/fourqparse.py、tools/probe/sentinel_decide_replay.py、外部：Claude Code 發行說明（src=cc-releases）
## Q4 如何證明資料與改善結果是有正面影響與收斂的？
- Q4-1｜擬提案：歷史缺陷反事實重放回測｜指標類別：M1｜症狀定義：docs/01_requirements/SelfImproving_PRD.md:70｜反證：同一根因鍵下可評估的採納窗連續復發，即回測沒有降低再現｜收斂：依 PRD 的 M1 判定細則，採納後同根因事件在可評估窗內不再復發；樣本不足一律視為 NOT-EVALUABLE
