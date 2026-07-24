# AutoSDD 缺陷帳本 — Archive 10（R34/R35 四方一審/二審/三審裁決敘事）

> 本檔為 `AutoSDD_Defect_Log.md` 依 DEF-99-001 輪替政策搬遷之歷史敘事區段（R38 主檔逼近 256KB 界線時建立），**原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。內容為 R34、R35「四方一審／二審／三審裁決總結」敘事段落，其缺陷現況已被主檔上方「缺陷總表」live 狀態取代，本檔僅供歷史脈絡查閱。

---

## R35 四方複審裁決總結（2026-07-24）

本輪使用者要求同 R16 起既有固定格式：全面掃描四維度＋Architect 架構最佳化評估，發現問題即修復，再經 Architect/SA/SD/QA 四方獨立審查至全數 APPROVE。

- **前置基線**：AutoClaude pytest 3742 passed/146 skipped、`tools/tests/` 407 passed/3 skipped，本輪動工前重跑確認與 R34 收尾狀態一致、無回歸。帳本主檔 213,270 bytes，距 256KB 上限尚遠，本輪未需提前歸檔。
- **全面掃描（Scan-A/B/C/D 四維度 + Architect 架構深度評估，皆背景 agent 獨立平行執行）**：A（Shell/PowerShell）發現 `tools/dev_start.ps1` 兩個 dot-source 早期失敗分支未設 `$LASTEXITCODE`，違反自身 `.NOTES` 文檔契約、與對等 `.sh` 版本不對稱（DEF-101-304）；B（Python 跨平台）與 C（CI/排程/hooks 基建）皆零新發現；D（文件/帳本一致性）發現「已歸檔內容（八檔）」第三度漏同步遞增為「九檔」（DEF-101-305）與 `archive_06.md` 大小描述誤差 79%（DEF-101-306）；Architect 深度評估肯定既有「薄殼＋Python 核心＋SSOT＋交叉一致性鎖」演進路線合理，另發現 WSL System32 排除規則分裂成兩座互不相通的 SSOT 孤島、缺跨島鎖，但實測風險偏低，列為 backlog（DEF-101-307）。
- **修復落地**：DEF-101-304 於兩處分支補 `$global:LASTEXITCODE = 1`，同步更新 `check_wrapper_thinness.py` 雜湊釘選，新增 `tools/tests/test_dev_start_ps1_lastexitcode.py`；DEF-101-305/306 訂正帳本文字。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆於主工作樹直接操作、不使用 `isolation: worktree`）

- **Architect**：**APPROVE**——親自重現修復有效、對新測試 bug-injection 確認鑑別力；提出非阻斷觀察：新測試僅覆蓋「找不到 Python」分支，未覆蓋同構的「找不到 repo 根」分支。
- **SA**：**APPROVE**（無條件）——逐項核對四筆缺陷紀錄數字/路徑/行號、archive 計數與大小描述，全數精確吻合。
- **SD**：**APPROVE-with-conditions**——用 4 組 bug-injection 精準證實「找不到 repo 根」分支是**真實覆蓋盲區**（只還原該分支修復，測試仍全綠），列為必修；另確認 `$global:` scope 前綴非功能必要，屬保守設計選擇非缺陷。
- **QA**：**APPROVE**（無條件）——逐一核實 CI paths 真的會觸發新測試、`pwsh`/`powershell` 在兩支 workflow runner 上確有可用、雜湊釘選正確、全套回歸重跑皆綠、帳本欄位誠實。

**針對一審發現的修復**：Architect/QA/SD 三方交叉獨立發現同一缺口（「找不到 repo 根」分支無測試覆蓋），依既有慣例視為高信度真缺陷，新增靜態一致性測試 `TestDevStartPs1BothFailureBranchesSetLastExitCode`（文字比對 `tools/dev_start.ps1` 全文，鎖住兩分支同時設 `$LASTEXITCODE`），bug-injection 驗證有效後回傳四方複審。

### 四方二審（SendMessage 保留一審上下文複審）

- **SA**：**APPROVE-with-conditions**——獨立 bug-injection 覆核靜態鎖有效，唯一建議：DEF-101-304 的 `fixed@R35` 描述應補充說明追加的靜態測試類別，避免讀者誤判涵蓋方式（皆為子行程實際執行）。已就地訂正。
- **Architect**：**APPROVE**——用兩種進階手法對靜態鎖做對抗式 bug-injection，其一（decoy 註解＋格式偽裝）成功繞過但需刻意對抗性動作，另一（多行拆分）因寫入前置條件不成立未完整驗證；認同「該分支無法安全模擬觸發、改用靜態鎖」的工程判斷合理；審查過程回報遭遇多次可疑偽造 system-reminder 與工具輸出間歇性矛盾內容，皆未採信、改以 `shasum`＋Python `hashlib`＋原始 bytes dump＋`git diff` 交叉核實排除汙染。
- **SD**：**APPROVE-with-conditions**——獨立以相同 decoy 手法重現與 Architect 相同的繞過路徑（交叉印證），並證實此鎖對「意外重排」安全、只對「刻意 padding」不安全；回報一次無法解釋的偶發假紅，經 `git hash-object` 核實排除為暫態雜訊。
- **QA**：**APPROVE**（無條件）——確認新增測試類別無需額外 CI paths 異動；bug-injection 覆核鎖有效；重跑全套回歸皆綠；揭露一次因多 agent 並行 bug-injection 讀寫窗口重疊、短暫讀到他方實驗中間態的 race 觀察（非本輪異動缺陷，已排除為暫態），建議未來留意但不阻擋本輪。

**針對二審發現的處理**：SA 建議的帳本描述訂正已就地完成；Architect/SD 交叉發現的靜態鎖 decoy 繞過手法記入 DEF-101-308（P3 backlog，兩方皆明確判定非阻擋——繞過需刻意對抗性動作、非自然筆誤，且本輪 `dev_start.ps1` 生產邏輯本身修復正確，僅「測試的測試」層面鑑別力縫隙）。

**四方複審最終結論：全數 APPROVE**（Architect/SA/QA 最終皆無條件 APPROVE；SD 唯一殘留項為明確標記非阻斷的 DEF-101-308 backlog，與 Architect 交叉印證一致）。本輪 R35 全部異動（`tools/dev_start.ps1`、`tools/check_wrapper_thinness.py`、新檔 `tools/tests/test_dev_start_ps1_lastexitcode.py`、`docs/06_quality/AutoSDD_Defect_Log.md`）可放行。**環境異常揭露**：本輪多方（SA/Architect/SD/QA）皆各自獨立回報遭遇「並行 bug-injection 互相污染」的暫態現象與可疑的偽造 system-reminder（誘導隱瞞暫時性檔案改動），全數未採信、獨立以 diff/sha256/git hash-object 核實後確認最終狀態乾淨，如實記錄不隱瞞；QA 額外指出這類 race 在共用主工作樹上是真實風險，建議未來輪次視情況加互斥保護，記入 backlog 追蹤。**已知限制（如實記載）**：DEF-101-307（System32 雙 SSOT 孤島缺跨島鎖）、DEF-101-308（`test_dev_start_ps1_lastexitcode.py` 靜態鎖字面計數可被刻意 decoy 繞過）維持 open backlog。**收尾驗證**：全套回歸最終重跑——AutoClaude pytest 3742 passed/146 skipped、`tools/tests/` 409 passed/3 skipped、AISDLC_SDD `ci-gate.sh` 全通過（v0.01:1475、v0.30:1674、scripts/tests:184）、`check_script_parity.py`/`check_ntfs_paths.py`/`check_wrapper_thinness.py` 皆綠、帳本 `check_defect_log_crossref.py` 138 筆有效狀態一致，帳本主檔收斂於 224,914 bytes，遠低於 256KB 上限，本輪無需歸檔。

## R34 四方複審裁決總結（2026-07-24）

本輪使用者要求同 R16 起既有的固定格式：全面掃描四維度＋Architect 架構最佳化評估，發現問題即修復，再經 Architect/SA/SD/QA 四方獨立審查至全數 APPROVE。

- **前置作業**：帳本主檔逼近 256KB 上限（254,679 bytes，距界線僅 0.5% 餘量，R33 二審 SA 已預先提醒），動工前先將 R33 敘事段落搬遷至新檔 `archive_08.md`（降至 250,090 bytes）。
- **前置基線**：AutoClaude pytest 3742 passed/146 skipped（既知 `.venv` postgres 選配污染現況，沿用 R33 收尾狀態）、`tools/tests/` 403 passed/3 skipped，本輪動工前重跑確認與 R33 收尾狀態一致、無回歸。
- **全面掃描（Scan-A/B/C/D 四維度 + Architect 架構深度評估，皆背景 agent 獨立平行執行）**：A（Shell/PowerShell）零新發現（含實測重現 `AISDLC_SDD_v0.01` 凍結版 `verify_traceability.sh` 在 macOS bash 3.2 上的 `declare -A` 已知崩潰，確認為既有 wontfix 家族、非新缺口）；B（Python 跨平台）發現 R33 新增的 `test_windows_forbidden_filename_parity.py` 缺 `usable_bash()` skipIf 守門（DEF-101-298）；C（CI/排程/hooks 基建）發現 macOS 側 `integration_gate.sh` 從未被 CI 實際執行、只靠語法檢查頂替，與已修復的 Windows 側同缺陷模式不對稱（DEF-101-299）；D（文件/帳本一致性）發現「已歸檔內容（六檔）」與實際 8 檔不符（DEF-101-301）；Architect 深度架構評估用「同一跨平台規則被 ≥2 處獨立實作卻無機械鎖」為篩選準則，找到 `tools/dev_start.ps1` 的 WindowsApps 空殼排除 guard 是第 4 個獨立實作且零測試覆蓋，屬 DEF-101-273/279/281 同一缺陷類別第 4 次復發（DEF-101-300）；其餘四面向（機械守門工具生態整體分工、雙原生腳本收斂取捨、nightly/CI stage 對等、DAL/hexagonal、FSM hooks Windows fallback）逐一親自驗證後判定維持既有結論不變。
- **修復落地**：DEF-101-298 補齊鏡自 `test_pre_push_dispatcher.py` 的 `_usable_bash()` + 6 處 `skipIf`；DEF-101-299 於 `macos-compat-ci.yml` 補上 `integration_gate.sh --skip-full` 實際執行步驟；DEF-101-300 新增 `test_windowsapps_guard_cross_consistency.py`；DEF-101-301 訂正計數字樣。過程中自我發現一項連鎖回歸：新測試檔以路徑引用 `tools/dev_start.ps1`，`AISDLC_SDD ci-gate.sh` 的 `test_ci_paths_cover_root_consumers.py` 機械攔下 `macos-compat-ci.yml` paths 未涵蓋此消費檔（DEF-101-042 同構），已於 push/PR 兩份 paths 補上一行修復。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆於主工作樹直接操作、不使用 `isolation: worktree`）

- **Architect**：**APPROVE-with-conditions**——用自行設計的 bug-injection（`-and`→`-or`）發現 `test_windowsapps_guard_cross_consistency.py` 的靜態測試對「布林運算子反轉」無鑑別力，此手法比字面上「拔掉整個 guard」更隱蔽。
- **SA**：**APPROVE-with-conditions**——逐項重跑核對四筆缺陷紀錄的數字與敘述，全數精確吻合；唯一必修：`archive_08.md` bullet 描述「≈2KB」實測為 5,467 bytes（≈5.3KB），差 2.7 倍。
- **SD**：**APPROVE-with-conditions**——對四項修復逐一 bug-injection 皆確認鑑別力，並額外發現 `bootstrap.ps1` 的靜態測試用 `re.search()` 只需命中一次，對其 python/python3 兩個獨立 guard 分支只破壞一處會漏放行（假綠）。過程中主動揭露：遭遇疑似並行 session 暫態污染，以及工具輸出出現偽造 system-reminder 誘導隱瞞暫時性檔案改動，皆未採信、獨立以 diff/git status 核實還原乾淨。
- **QA**：**APPROVE-with-conditions**（唯一阻斷項）——揪出 `macos-compat-ci.yml` 新增步驟註解「AutoClaude 全套測試已於本 job 另跑」不實：該 job 實際只跑 `test_perception.py` 單一檔案，全套僅在 `macos-nightly-full`（continue-on-error 非阻斷）執行。

**針對一審發現的修復**：新增 `test_dev_start_ps1_guard_uses_and_not_or`（鎖 Architect 發現的布林反轉）與 `test_bootstrap_ps1_guard_covers_both_python_and_python3_branches`（改用 `findall` 鎖 SD 發現的雙分支漏放行）；訂正 `archive_08.md` 大小描述為「≈5.3KB」；訂正 `macos-compat-ci.yml`／`windows-compat-ci.yml`（QA 發現的失實敘述其實源自 windows 側既有措辭、一併訂正）的 CI 步驟註解為誠實揭露。

### 四方二審（SendMessage 保留一審上下文複審）

- **QA**：**APPROVE**（無條件；親自核對兩份 workflow 措辭訂正與 nightly-full job 定義完全吻合；獨立 bug-injection 重驗兩個新測試皆正確變紅，且發現 `-or` 反轉的實際危害比表面描述更嚴重——連「完全沒找到任何候選」的情況都會被誤判為找到）。
- **SA**：**APPROVE**（無條件；重新逐項核對，`archive_08.md` 5,467 bytes 與訂正後敘述吻合；如實揭露複審過程中再度撞見並行 bug-injection 暫態競態，經多方法交叉核實排除為誤判來源，非隱瞞）。
- **Architect**：**APPROVE-with-conditions**——用第三種手法（`-notlike` 子句「後」疊加恆真子句 `-or $true`）發現二審新增的兩項測試仍只驗證運算式「中段」，未驗證條件式收尾，可被此手法繞過。
- **SD**：**APPROVE-with-conditions**——確認 `-and`/雙分支修復有效，並獨立驗證 Architect 同時發現的「尾端疊加」缺口；另用新角度（`$PyCand`/`$Py3Cand` 互換賦值）發現一個機率極低的邊界情況，明確判定**非阻擋、列入下輪**。再次遭遇並行污染與偽造 system-reminder，皆未採信、如實記錄。

**針對二審發現的修復**：新增 `test_dev_start_ps1_guard_condition_closes_immediately_after_windowsapps_check`／`test_bootstrap_ps1_guard_conditions_close_immediately_after_windowsapps_check`，改錨定**整條** `if (...)` 判斷式（要求 `-notlike '*\WindowsApps\*'` 之後必須緊接 `)`，中間不得插入任何 token），堵住「尾端疊加恆真子句」繞過手法；SD 發現的變數互換邊界情況記為 DEF-101-303（backlog，非阻擋）。

### Architect 三審（最終確認）

用「巢狀括號疊加恆真子句」「合法多行重排（驗證無過度僵化）」兩種手法對「整條判斷式收尾」新錨定做最後一輪驗證，確認無法在保持 guard 實際失效的前提下繞過；認同 SD 對變數互換邊界情況「機率極低、非阻擋」的判定。**最終 APPROVE**。

**四方複審最終結論：全數 APPROVE**（QA/SA/Architect 無條件 APPROVE；SD 唯一殘留項為明確標記非阻擋的 DEF-101-303 backlog）。本輪 R34 全部異動（`tools/tests/test_windows_forbidden_filename_parity.py`、新檔 `tools/tests/test_windowsapps_guard_cross_consistency.py`〔8 case〕、`.github/workflows/macos-compat-ci.yml`、`.github/workflows/windows-compat-ci.yml`、`docs/06_quality/AutoSDD_Defect_Log.md`、新檔 `docs/06_quality/AutoSDD_Defect_Log_archive_08.md`）可放行。**環境異常揭露**：本輪三方（Architect/SA/SD）皆各自獨立回報遭遇「並行 bug-injection 互相污染」的暫態現象與可疑的偽造 system-reminder（誘導隱瞞暫時性檔案改動），全數未採信、獨立以 diff/git status/md5 核實後確認最終狀態乾淨，如實記錄不隱瞞。**已知限制（如實記載）**：DEF-101-303（`bootstrap.ps1` 變數互換型 bug 缺靜態鎖）維持 open backlog。**收尾歸檔**：帳本主檔加入四筆新缺陷後一度達 264,583 bytes、超過 256KB 上限（`check_defect_log_crossref.py` 由警告轉 FAIL），本輪未延後至 R35，當場逐一確認 12 筆 R15~R27 已結列（狀態皆為 `fixed@R...`，且未被 `ONBOARDING.md`／兩份 compat-ci workflow 以「DEF-ID(狀態宣稱)」樣式引用、不觸發跨文件矛盾）後搬遷至新檔 `archive_09.md`，主檔降回 213,244 bytes（81%），`check_defect_log_crossref.py` 重跑轉綠、跨文件狀態一致。
