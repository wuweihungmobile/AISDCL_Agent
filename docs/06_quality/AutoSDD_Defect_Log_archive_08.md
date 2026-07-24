# AutoSDD 缺陷帳本 — Archive 08（R33 四方一審/二審裁決敘事）

> 本檔為 `AutoSDD_Defect_Log.md` 依 DEF-99-001 輪替政策搬遷之歷史敘事區段（R34 主檔逼近 256KB 界線時建立），**原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。內容為 R33 「四方一審／二審裁決總結」敘事段落，其缺陷現況已被主檔上方「缺陷總表」live 狀態取代，本檔僅供歷史脈絡查閱。

---

## R33 四方複審裁決總結（2026-07-24）

本輪使用者要求同 R16 起既有的固定格式：全面掃描四維度＋Architect 架構最佳化評估，發現問題即修復，再經 Architect/SA/SD/QA 四方獨立審查至全數 APPROVE。

- **前置基線**：AutoClaude pytest 3742 passed/146 skipped（本機既有 `.venv` 已裝 postgres 選配的既知污染現況，沿用 R32 收尾狀態）、`tools/tests/` 386 passed/3 skipped，本輪動工前重跑確認與 R32 收尾狀態一致、無回歸。
- **全面掃描（Scan-A/B/C/D 四維度 + Architect 架構深度評估，皆背景 agent 獨立平行執行）**：A（Shell/PowerShell）、B（Python 跨平台）、C（CI/排程/hooks 基建）皆零新發現，確認 R1~R32 累積修復穩定；D（文件/帳本一致性）發現缺陷帳本逼近 256KB 輪替上限（248,860 bytes）與 DEF-101-289（pytest 基線落後）仍待乾淨 venv 重驗；Architect 深度架構評估重新質疑 R32 判定的三項「維持不變」結論，確認皆仍成立，唯一發現新缺口：Windows 禁用檔名邏輯三處獨立實作（`pre-commit`／`check_ntfs_paths.py`／`logger.py`）缺交叉一致性鎖（DEF-101-295）。
- **修復落地**：DEF-101-289 於全新臨時目錄建立乾淨 venv 重新量測（3,644 passed/210 skipped），更新 `ONBOARDING.md` §7；缺陷帳本 R32 敘事段落搬遷至新檔 `archive_07`；新增 `tools/tests/test_windows_forbidden_filename_parity.py` 鎖住 DEF-101-295，`logger.py` 補套件邊界 WHY 註解。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆於主工作樹直接操作、不使用 `isolation: worktree`）

- **SA**：**APPROVE**（無條件；逐項重建乾淨 venv 驗證 DEF-101-289 數字精確吻合、archive_07 逐字比對無誤）。
- **SD**：**APPROVE**（無條件；對 DEF-101-295 新測試做 5 組 bug-injection，含關鍵的「抽取機制失效是否 fail loud」驗證，皆通過）。
- **Architect**：**APPROVE-with-conditions**（親自驗證 `logger.py` 套件邊界論證因果性成立；驗證抽取失敗會明確報錯非靜默通過）。
- **QA**：**APPROVE-with-conditions**——揪出真實必修：DEF-101-295 一審初版籠統宣稱「三處目前內容一致」不實，`logger.py` 原本完全沒有控制字元淨化，與另兩處不對稱且為具體、非罕見觸發情境。

**針對一審發現的修復**：`logger.py` 補齊控制字元淨化（`ord(ch) < 0x20 or ord(ch) == 0x7F`）；新增 `TestControlCharCrossConsistency`（3 case）；過程中發現並記載 bash 版對內嵌 `\n` 偵測不到的既有狹窄限制（DEF-101-297，backlog，CI 端仍會擋下）；訂正 DEF-101-295 措辭與行號引用。

### 四方二審（SendMessage 保留一審上下文複審）

- **SD**：**APPROVE**（無條件；獨立重現 `\n` 例外根因，確認鑑別力扎實）。
- **SA**：**APPROVE**（無條件；提醒帳本主檔已逼近 256KB 上限 94.6%，建議下一輪規劃再次歸檔，非本輪阻斷項）。
- **QA**：二審再揪出**第二項真實必修**——`logger.py` 用 `rsplit(".", 1)[0]` 剝副檔名，與另兩處 `split(".", 1)[0]` 不對稱，對多重副檔名保留名（如 `lpt5.tar.gz`）漏判，觸發情境同樣具體（playbook 作者以點號分層命名 step_id）。修復後 QA 三審用 5 組全新案例獨立驗證確認為通用修法（非偷懶解法），**最終 APPROVE**。
- **Architect**：**APPROVE-with-conditions**——用「兩支 pytest 行程並行跑同一測試檔」40 組對照重驗，把一審「1 次孤立假紅、根因未能鎖定」的 DEF-101-296 定位出可重現根因（`__pycache__` bytecode 快取並行寫入競態，`PYTHONDONTWRITEBYTECODE=1` 下 0/40 vs baseline 2/40），要求措辭訂正；並發現 QA 二審修復的多重副檔名缺口其實**早在 R16 就由 SD 記載為 DEF-101-237**（當時因唯一呼叫路徑天然免疫判定不修），本輪修復後應交叉關閉避免帳本矛盾。修復後 Architect 三審**最終 APPROVE**。

四方二審最終結論：**全數 APPROVE**。本輪 R33 全部異動（`AutoClaude/autoclaude/utils/logger.py`、`ONBOARDING.md`、`docs/06_quality/AutoSDD_Defect_Log.md`、新檔 `docs/06_quality/AutoSDD_Defect_Log_archive_07.md`、新檔 `tools/tests/test_windows_forbidden_filename_parity.py`〔13 case〕）可放行。**額外收穫**：本輪修復同時關閉了一筆 R16 舊帳（DEF-101-237），並把一項間歇性測試假紅（DEF-101-296）從「無法定位」升級為「有具體對照數據佐證的根因假說＋可操作的複審規避手法」，皆屬四方多輪複審本身帶來的額外價值，非原始任務範圍預期。**已知限制（如實記載）**：DEF-101-297（bash 版 `\n` 控制字元偵測既有狹窄限制）維持 open backlog；缺陷帳本主檔本輪收尾時為 249,684 bytes（低於 256KB 上限但持續逼近），SA 建議下一輪（R34）優先規劃再一次 archive 搬遷。
