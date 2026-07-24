# AutoSDD Defect Log — Archive 13

> **歸檔來源**：`AutoSDD_Defect_Log.md` R38「四方複審裁決總結」敘事段落，於 R40 跨平台輪（2026-07-24）動工前逐字搬遷（R39 收尾已建議 R40 優先規劃再次歸檔；R40 動工前主檔 257,388 bytes、距 256KB 僅剩 1.8% 餘量）。搬移對象與 archive_05/06/07/08/10/11/12 同類：歷史敘事段落，缺陷現況已被主檔缺陷總表 live 狀態取代，原文逐字保全、零刪除。

## R38 四方複審裁決總結（2026-07-24）

本輪使用者要求同 R16 起既有固定格式：全面掃描四維度＋Architect 架構最佳化評估，發現問題即修復，再經 Architect/SA/SD/QA 四方獨立審查至全數 APPROVE。

- **前置基線**：AISDLC_SDD `ci-gate.sh` 全通過（v0.01:1475、v0.30:1703、scripts/tests:188）、根層 `tools/tests/` 416 passed/4 skipped、AutoClaude pytest 3751 passed/146 skipped（**R39 校正**：此讀數所用根層共用 `.venv` 經 R39 QA 一審獨立查證確實已受 `psycopg2`/`sqlalchemy` 污染，非官方乾淨基線——官方基線見 `ONBOARDING.md` §7「R37 校正」之 3,653 passed/210 skipped，本行數字僅供 R38 動工當下「與前一輪一致、無回歸」之相對比對用，不應被引用為 AutoClaude 側絕對基線），本輪動工前重跑確認與 R37 收尾狀態一致、無回歸。帳本主檔 246,971 bytes，已達 256KB 上限 94.2%，Scan-D 掃描後判斷需本輪歸檔（見下）。
- **全面掃描（Scan-A/B/C/D 四維度 + Architect 架構深度評估，皆背景 agent 獨立平行執行）**：B（Shell/程序/訊號）、C（CI 腳本雙軌對等性）皆零新發現，延續 R35~R37 結果；D（文件/帳本一致性）抽樣核對 R33~R37 `fixed@R...` 宣稱皆對照程式碼確認屬實，另發現帳本主檔逼近輪替上限、以及 R37 commit 缺對應敘事章節（DEF-101-318）；A（檔名/路徑相容性）找到兩項真實新缺陷：`production_monitor.py` 的 `nfr_id` 欄位未納入 HMAC 簽章覆蓋且未淨化即組入檔名，可致路徑穿越或 Windows 崩潰（DEF-101-314，P0）；`state_loader.py::_sanitize_component()` 只擋 `/`、`\`，是同缺陷類別第 5 個獨立實作但覆蓋度明顯弱於已鎖 parity 的 AutoClaude 側版本（DEF-101-315，P1），`spec_patch_proposer.py` 有同款次要缺口一併記入（DEF-101-316）；Architect 深度評估找到 `AISDLC_SDD_v0.30/tools/install_hooks/install_post_commit.ps1` 裸 `Get-Command python` 檢查缺 WindowsApps 空殼排除，是 R27~R37 反覆修復的同一缺陷類別第 5 個獨立未覆蓋位置、首次出現在 AISDLC_SDD 子專案而非 AutoClaude/根層（DEF-101-317，P2）。
- **歸檔**：Scan-D 發現帳本逼近上限後，動工前先將 R34、R35 敘事段落搬遷至新檔 `archive_10.md`（232,372 bytes），釋出空間供本輪新增內容。
- **修復落地（第一輪）**：三個互不重疊檔案的修復包平行執行——① `production_monitor.py` 把 `nfr_id` 併入簽章欄位 + 新增獨立淨化函式；② `state_loader.py` 擴充 `_sanitize_component()` 淨化覆蓋度，`spec_patch_proposer.py` 改用同一函式，新增跨模組 parity 測試；③ `install_post_commit.ps1` 在本檔內獨立實作 WindowsApps 空殼排除（理由：AISDLC_SDD 獨立 `releases/` 打包發布機制，不可硬相依 monorepo 根路徑）。過程中主控親自跑三軌回歸時發現 1 個新測試檔（`test_install_post_commit_windowsapps_guard.py`）誤觸根層 `test_platform_neutral_paths.py` 機械掃描（Windows 磁碟機假路徑字面值），已用既有 `# platform-ok:` 豁免標記就地訂正。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆於主工作樹直接操作、不使用 `isolation: worktree`）

- **SA**：**APPROVE**（無條件）——親自讀簽章覆蓋欄位邏輯確認 `nfr_id` 缺席時 canonical payload 仍用固定空字串佔位、簽章穩定；核對 `_sanitize_component`/`_sanitize_nfr_id` 對非字串型別輸入不拋例外；核對 `install_post_commit.ps1` 的 `-like '*\WindowsApps\*'` 屬路徑分段精確比對、不會誤中 `MyWindowsAppsBackup` 這類巧合子字串（另記一個非本輪新增、繼承自根層共用實作的精度缺口供追蹤，不阻擋）。
- **QA**：**APPROVE**（無條件）——對五個新增/修改測試檔逐一親自 bug-injection（改回舊版邏輯重跑測試確認轉紅、備份+diff核對還原，全程未用 `git checkout --`），確認皆具真實鑑別力、非裝飾性斷言，跨模組 parity 測試確實用兩獨立函式實際輸出比對。
- **Architect**：**REJECT**——查證「`install_post_commit.ps1` 不可 dot-source 根層 `WindowsAppsGuard.ps1`」的理由：實際 `tar -tzf` 檢視 `releases/v0.01/*.tar.gz` 發現根本沒有 `tools/install_hooks/`，且本檔自身已用 `$MainCheckoutRoot` 強相依 monorepo 根路徑，獨立實作等於重製 R37 剛收斂掉的同款副本；另發現 `production_monitor.py::_sanitize_nfr_id()` 與 `state_loader.py::_sanitize_component()` 在同一套件內幾乎逐字重複、無循環 import 障礙卻未收斂。
- **SD**：**REJECT**——對三處修復逐一 bug-injection（雙重編碼路徑穿越、NUL 字元、大小寫混合保留裝置名等），確認 `production_monitor.py`/`install_post_commit.ps1` 本身無漏洞，但找到 `state_loader.py::_sanitize_component()` 的 padding-bypass 順序缺陷：`"CON" + 77個空格 + "X"` 會使保留裝置名檢查失效、guard 被繞過。

**針對一審發現的修復**：派兩個互不重疊修復包——① 修正 `_sanitize_component()` 操作順序為單輪「淨化→截斷→rstrip→保留名檢查」，新增 padding-bypass 回歸測試，並把 `production_monitor.py::_sanitize_nfr_id()` 改為重用 `state_loader._sanitize_component()`（薄包裝＋`nfr_id` 專屬預設值，移除重複常數）；② `install_post_commit.ps1` 改為 dot-source 根層 `tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython`，連帶修復兩份假 monorepo fixture 與 CI paths 缺口（`test_ci_paths_cover_root_consumers.py` 機械鎖抓到）。

### 四方複審（SendMessage 保留一審上下文複審）

- **Architect**：**APPROVE**——親自重讀 diff 確認兩項 REJECT 理由皆已收斂：`install_post_commit.ps1` 不再殘留內嵌判斷、`production_monitor.py` 已改為 import 共用函式；意外發現「收斂成共用函式」的價值展示——若未收斂，SD 發現的 padding-bypass 修復就不會自動惠及 nfr_id 路徑。
- **SD**：**APPROVE**——用原本的攻擊手法（含 `PRN`/`AUX`/`NUL`/`COM1`/`LPT9`/大小寫混合）重跑確認 padding-bypass 已修復，`_sanitize_nfr_id` 委派後仍正確免疫；`install_post_commit.ps1` 的 WindowsApps 判斷式邏輯只是搬移位置未改變語意，一審驗證過的邊界案例重測結果一致。
- **SA**：**APPROVE**——獨立重跑 720 組保留名×padding 長度×結尾字元 fuzzer 確認 0 bypass；獨立用 `tar -tzf` 查證 Architect 對 release 打包內容的推翻理由屬實；簽章覆蓋範圍邏輯、非字串輸入防禦、WindowsApps 比對精度三項一審驗證過的核心安全性質皆未因重構而改變。
- **QA**：**APPROVE**——對三處追加修復逐一 bug-injection（含二階段還原測試：先改回繞過共用函式的 direct passthrough 確認 7 個測試轉紅、再驗證 dot-source 改造後 fixture 未讓測試退化成「檔案存在就通過」的空殼判斷），確認鑑別力未因重構而流失。

**四方複審最終結論：全數 APPROVE**（Architect/SD/SA/QA 皆 APPROVE，二審收斂了一審 Architect/SD 的兩項 REJECT）。本輪 R38 全部異動（`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/production_monitor.py`、`state_loader.py`、`spec_patch_proposer.py`、對應測試檔、新檔 `test_state_component_sanitizer_parity.py`、`AISDLC_SDD/AISDLC_SDD_v0.30/tools/install_hooks/install_post_commit.ps1`、新檔 `AISDLC_SDD/scripts/tests/test_install_post_commit_windowsapps_guard.py`、`AISDLC_SDD/scripts/tests/test_install_post_commit_exec_bit.py`、`tools/lib/WindowsAppsGuard.ps1`、`.github/workflows/aisdlc-sdd-ci.yml`、`docs/06_quality/AutoSDD_Defect_Log.md`、新檔 `docs/06_quality/AutoSDD_Defect_Log_archive_10.md`）可放行。**已知限制（如實記載）**：SA 一審發現的 `WindowsApps` 路徑分段比對未要求上層必須是 `Microsoft`（`C:\dev\WindowsApps\python.exe` 這種非系統路徑仍會被排除）是繼承自根層共用實作 `tools/lib/WindowsAppsGuard.ps1` 的既有系統性限制，非本輪新增，建議另案追蹤；Architect 一審提及的其餘同缺陷類別姊妹呼叫點（`path_cost.py`/`production_to_fpl.py`/`counterfactual_replay.py`/`sandbox_runner.py`/`hub_sync.py` 等）本輪未觸及，留待下一輪掃描。**收尾驗證**：全套回歸最終重跑——AISDLC_SDD `ci-gate.sh` 全通過（v0.01:1475、v0.30:1704、scripts/tests:188）、根層 `tools/tests/` 416 passed/4 skipped、AutoClaude pytest 3751 passed/146 skipped（**R39 校正**：同上，此為受污染共用 venv 讀數，非官方基線，官方基線見 `ONBOARDING.md` §7 之 3,653/210）、`python3 tools/check_script_parity.py` 全綠、`python3 -m tools.arch_fitness.arch_fitness --strict` fail=0、YAML 語法驗證通過。帳本主檔本輪新增大量內容後為 250,727 bytes（95.6%，`check_defect_log_crossref.py` 印出「已逼近輪替上限」警告但非 FAIL），建議下一輪（R39）動工前優先規劃再次歸檔（候選：搬遷 R36 敘事段落至 `archive_11.md`）。
