"""ResearchToPRD 研究面（Bridge 側；ADR-003、ADR-XPLAT-017；TCS-ResearchToPRD-P0-20261102 D2）。

模組分工（一個模組一件事；新模組先在 `tests/test_research_capability.py` 的登記表登記類別）：
  settings   `BRIDGE_RESEARCH_*` 的讀取與驗證、能力資訊（`/health/deep`、`/research/capabilities`）
  layout     工作區目錄、路徑消毒、原子寫檔（重用 `app.fsutil.write_text_atomic`）
  export     由資料列確定性渲染的檔案（`issue_scope.json`）與 `state.json` 投影（只寫出、不讀回）
  db         `ResearchDb`：fail-loud 的研究表寫入器（單一寫入者；無 DSN 不降級）
  outbox     檔案 outbox＋持久化協定（寫檔→outbox→DB 交易→標完成）與重放
  fsm_ops    外環／內環 FSM 鍵的驅動（只經 `sdd_cli` 的研究面入口；Bridge 不開寫狀態檔）

不變量（各自有機械鎖，見 `tests/test_research_*.py`）：Bridge 是 `console.research_*` 唯一寫入者；
無資料庫即 503，不降級成純檔案模式；流程游標只由 Bridge 在同一交易推進並附 `research.step`
事件；核准只准真人；新程式碼不新增改動目錄項的原語（`os.replace`／`rename`／`move`）。
"""
