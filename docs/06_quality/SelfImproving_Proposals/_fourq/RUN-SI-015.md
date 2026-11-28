# 四問審視 RUN-SI-015
## Q1 此頂尖專家會做那些我沒有想到的事？
- Q1-1｜領域：記憶索引容量治理｜做法：索引逼近上限時，由程式依最久未引用的條目自動降級搬入歸檔檔，不靠人工判斷｜機制：以 cap_frac 水位觸發，依各條目最後被引用的時間排序後壓實｜座標：OBS-SI-367｜查詢：「最久未引用」＝零命中｜查詢：「cap_frac」＝命中不涵蓋：既有只在 OBS 帳本記載容量達標的事實，沒有依引用時間自動降級的壓實機制
## Q2 在哪裡找到最前沿的資料與研究結果？
- Q2-F1｜來源：cc-docs-memory-md｜座標：src=cc-docs-memory-md up to the first 200 lines or 25KB of MEMORY.md｜發現：官方文件載明 MEMORY.md 每次只載入前 200 行或 25KB，超出部分在載入時被截掉，索引逼近上限等同於尾端條目靜默失效
## Q3 使用哪些方法與工具？
- Q3-1｜對象：Q1-1｜方法：LRU 式分層淘汰，並以乾跑比對壓實前後索引內容｜工具：tools/lib/selfimproving/capacity.py、tools/lib/selfimproving/memdir.py、外部：Claude Code 記憶文件（src=cc-docs-memory-md）
## Q4 如何證明資料與改善結果是有正面影響與收斂的？
- Q4-1｜擬提案：M 類記憶索引依引用時間自動降級歸檔｜指標類別：症狀：記憶索引逼近容量而需人工歸檔｜症狀定義：`python tools/selfimproving.py status`｜反證：若壓實後被降級的條目在後續運轉又被查閱或重新寫回，代表降級判準錯誤，提案不成立｜收斂：依 PRD 症狀閘定義，容量事件不再因同一成因反覆觸發人工歸檔
