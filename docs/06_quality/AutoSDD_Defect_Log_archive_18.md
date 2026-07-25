# AutoSDD Defect Log — Archive 18

> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 4 筆已結列（resolved / wontfix，非 open/routed/backlog）、且未被 `ONBOARDING.md`／`.github/workflows/{windows,macos}-compat-ci.yml`／`AutoClaude/docs/05_development/SD10_PG_Contract_NextAction.md` 四份 crossref 掃描目標以「DEF-ID(狀態宣稱)」樣式引用的條目，於 R44 跨平台輪（2026-07-25）新增 DEF-101-357~364 八筆缺陷列後主檔達 262,301 bytes（超過 256KB 上限）時逐字搬遷。搬移對象為缺陷總表已結列（resolved/wontfix）條目本身，性質同 archive_03/04/09/16（搬總表已結列，非敘事段落）；搬遷前逐一以 grep 核對每筆 DEF-ID 皆未被四份 crossref 目標檔引用，不觸發跨文件矛盾。**原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。

## 缺陷總表（已結列，逐字保全）

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|----|----------|----------|------------------------|--------|----------|------|
| DEF-13-002 | 2026-06-15 | improving_13 前一輪 zero-trust 稽核定案（split-brain 修復決策：觀察期斷檔處置） | monorepo 觀察期 #2/#3 因 DEF-13-001 split-brain 於 06-13~06-15 斷檔。**明確決策＝不 backfill**：舊副本在 branch `sprint/sd_09_phase9`，程式碼已與 monorepo main 分岔；把舊碼採集的 06-13~06-15 觀察 jsonl 注入 monorepo＝以「舊碼數據」充當「monorepo 現碼穩定證據」，違反 Nightly 取證紀律 #1（rc/數據須反映現碼真實執行）與 #3（PASS 須引現碼 RunId）。故**不複製／不覆寫／不注入任何 jsonl**；舊副本資料保留原處 | P1 | 修復決策（不 backfill）；排程修正後自今晚起從現碼重新連續採集，達標日順延 | **resolved@2026-06-15（PM 拍板）**：① backfill 決策＝**確認不 backfill、從現碼重新採集**（守取證紀律 #1/#3）；② 孤立舊副本 `d:\CursorProject\AutoClaude` 已**歸檔重新命名**為 `d:\CursorProject\AutoClaude_ARCHIVED_pre_monorepo_20260615`（杜絕未來再 split-brain；修前掃描確認無其他 schtasks 引用舊路徑；歸檔後複驗排程仍指 monorepo 不受影響）。觀察期 #2/#3 達標日順延、待現碼重新連續累積（追蹤點，非 open 缺陷） |
| DEF-25-001 | 2026-06-17 | improving_25（B 軌 meta⁸ 視覺化飽和認定） | FSM-STATE 視覺化反射觸 R-9.37.4 邊界（視覺化模組不得篡改 meta⁸ 既有合約、反射狀態為唯讀邊界） | P2 | wontfix（by-design 邊界，非缺陷） | **wontfix**（R-9.37.4 設計邊界；歷史脈絡見 `AutoSDD_Defect_Log_archive_01.md` improving_25 段） |
| DEF-42-003 | 2026-06-21 | improving_42 W-42-1 設計期（負向狀態碼跨路徑搶救被既有哨兵測試攔下而揭露） | 引號與負向狀態碼共存時負向被丟棄＝under-specify（引號路徑早 return、負向不評估）；屬 W-32-1 刻意設計決策 + 哨兵 `test_quoted_wins_over_negative_status` 鎖定 | P3 | wontfix（by-design，surface 供掌舵者未來輪決策） | **wontfix+by-design**（archive_01 improving_42 段；哨兵鎖定、非缺陷） |
| DEF-52-006 | 2026-06-23 | C 軌 improving_52（SA 鏡 FIND-4） | stderr 中文 UnicodeEncodeError（理論）：`_init_utf8_streams()` 僅 `__main__` 呼叫；ascii-strict console 直接 import 呼叫會拋。生產 wiring 經實證皆 subprocess→`__main__` 必走→風險為零 | P3 | wontfix（生產路徑必為 subprocess） | **wontfix+理由**（archive_01 improving_52 段；生產必走 subprocess、風險零） |
