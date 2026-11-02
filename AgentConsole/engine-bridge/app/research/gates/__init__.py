"""研究面的確定性閘（gate evaluator 的純函式層；TCS AC-960-9、11、12）。

模組分工（全部是純函式：輸入字串或物件、輸出違規清單或數值；不讀寫檔案、不碰資料庫與網路）：
  schemas      契約常數與登錄表（框架模板的逐值鏡像）、議題檔驗證、`Violation`
  evidence     `evidence_items.json` 的 16 條驗證規則、強度函式、數字錨定、授權待查、定位符去重
  prd_schema   PRD 草擬預檢 P0-1～P0-9、前置否決 P1（SLV-001／002／003、AMBIGUITY）、AC 機械計數
  review_card  審查者單維度輸出與彙整卡的驗證、缺陷狀態的確定性轉移
  aggregate    整數式 W100 聚合與判定（不經浮點、不四捨五入）

呼叫端有二：
  · `app/research/gate_cli.py`：AutoClaude 步驟的 `evaluator_command`，違規＝非 0 結束讓步驟重試；
  · `app/research/orchestrator.py`：入庫前在行程內再驗一次——evaluator 通過不等於可以信任檔案。
"""
