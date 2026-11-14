# 四問審視 RUN-SI-011
## Q1 此頂尖專家會做那些我沒有想到的事？
- Q1-1｜領域：人機協作審查獨立性｜做法：對審查代理的任務書隨機植入已知傾向的立場且不告知，事後比對審查結論是否跟著傾向走｜機制：每份任務書以擲硬幣決定植入傾向，結論與傾向一致的頻率明顯高於機率即判定審查獨立性不足｜座標：src=anthropic-research went with their agent’s lean｜查詢：「植入已知傾向」＝零命中｜查詢：「擲硬幣決定」＝零命中
- Q1-2｜領域：QA 審查流程｜做法：審查者先獨立寫下預期判決並封存，之後才讀作者交件，只在兩者分歧處深入審查｜機制：任務書分兩階段交付，第一階段只給規格不給成品，封存檔的雜湊先於第二階段開放｜座標：src=anthropic-research a human reviewer is only an independent check if their judgment is their own｜查詢：「預期判決並封存」＝零命中｜查詢：「兩階段交付」＝零命中
## Q2 在哪裡找到最前沿的資料與研究結果？
- Q2-F1｜來源：anthropic-research｜座標：src=anthropic-research went with their agent’s lean｜發現：Anthropic 的隨機對照研究顯示專家會順從 AI 代理的傾向，人類審查只有在判斷出於自己時才算獨立檢查，與本迴圈的審視者、歸因者獨立性直接相關。
- Q2-F2｜來源：cc-docs-hooks-md｜座標：src=cc-docs-hooks-md to mark the condition as one that can never be satisfied｜發現：Stop 類 hook 現有「不可能滿足」的放行語意與 StopFailure 的錯誤類型分類，可供 DEF-200-584 第二段的收尾出聲設計比對，但屬守衛面、只轉交掌舵者。
## Q3 使用哪些方法與工具？
- Q3-1｜對象：Q1-1｜方法：隨機化對照試驗（反事實傾向注入，審查者不知情）｜工具：tools/selfimproving.py、tools/lib/selfimproving/fourqparse.py、外部：Anthropic 專家判斷研究（src=anthropic-research）
- Q3-2｜對象：Q1-2｜方法：預先登記式盲審（先封存判決、後開放交件）｜工具：tools/lib/selfimproving/fourqparse.py、docs/05_development/SelfImproving_Operations_SOP.md、外部：Claude Code hooks 參考文件（src=cc-docs-hooks-md）
## Q4 如何證明資料與改善結果是有正面影響與收斂的？
- Q4-1｜擬提案：審查任務書植入傾向對照試驗（先出草案，觸及 SOP 與守衛面的部分轉交掌舵者）｜指標類別：症狀：審查結論跟隨植入傾向｜症狀定義：docs/05_development/SelfImproving_Operations_SOP.md:151｜反證：植入傾向與結論一致的程度和無植入對照組無可辨差異時，視為此症狀不存在、擬提案撤回｜收斂：以 PRD 定義的採納窗為單位，連續可評估採納窗內此症狀不再出現即視為收斂，不可評估記 NOT-EVALUABLE
- Q4-2｜擬提案：審查者先封存預期判決再讀交件（草案）｜指標類別：症狀：審查未獨立發現而事後才被別人揪出的缺陷｜症狀定義：docs/06_quality/AutoSDD_Defect_Log.md:357｜反證：採用先封存判決後，漏網缺陷出現的情形與採用前無可辨差異，則此做法無效、應撤回｜收斂：以 PRD 定義的採納窗為單位，窗內同根因缺陷不再復發（M1 判定細則的 recurred 不成立）才算收斂
