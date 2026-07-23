# AutoSDD 缺陷帳本 — Archive 06（R27 四方一審/二審裁決敘事）

> 本檔為 `AutoSDD_Defect_Log.md` 依 DEF-99-001 輪替政策搬遷之歷史敘事區段（R32 主檔逼近 256KB 界線時建立），**原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。內容為 R27 「四方一審／二審裁決總結」敘事段落，其缺陷現況已被主檔上方「缺陷總表」live 狀態取代，本檔僅供歷史脈絡查閱。

---

## 四方一審裁決總結（R27，2026-07-23）

真 Windows 11 機器複審——全面掃描（四維度 Scan-A/B/C/D，皆背景 agent 獨立執行）＋ Architect 架構最佳化評估 ＋ 主控本人手動重跑本地驗證腳本時意外揪出真實缺陷 ＋ Architect/SA/SD/QA 四方一審。

- **前置基線**：AutoClaude pytest 3608 passed/207 skipped、根層 unittest 359 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+174、`windows_smoke_local.ps1` PASS=11 FAIL=0，本輪動工前重跑確認與 R26 收尾狀態完全一致、無回歸。
- **全面掃描（Scan-A/B/C/D 四維度）**：B（Python 跨平台）、C（CI/排程基建）零新發現，確認 R26 修復皆確實落地無回歸；A（Shell/PowerShell）發現 `tools/bootstrap.ps1` 缺少 Windows Store App Execution Alias（`python.exe` 空殼）排除 guard、與同任務家族的 `tools/dev_start.ps1` 不對等（DEF-101-273）；D（文件/帳本）確認 R26 版本號修復落地，僅發現一項 P4 觀察（CLAUDE.md「最後更新」欄位本質易漂移，既有免責句已揭露，非新缺陷）。
- **主控本人手動重跑意外發現（本輪最重大發現）**：以非標準呼叫方式（`powershell -Command` 包一層而非標準 `-File`）重跑 `tools/windows_smoke_local.ps1` 時，意外重現一筆帳本已記載為「open watch，純理論性，全庫零命中」的舊 backlog（DEF-101-263④）——`tools/lib/GitHooksInstallCommon.ps1` 的 dot-source 陷阱防護只看呼叫棧最外層 frame，某些非典型呼叫鏈下會誤判互動情境，讓本該擋下的「linked worktree 安裝」防呆（防止 `core.hooksPath` 寫入共享 `.git/config` 後 worktree 刪除導致主 checkout 閘門靜默全滅）被靜默繞過。改看呼叫棧 `[1]`（本檔 dot-source 點的直接呼叫者）修復（DEF-101-272），過程中兩度自我糾錯：一審自我複核時先試了「呼叫棧任一層」版本，被既有互動安全回歸測試當場抓到會誤判（frame[0] 恆真）；新增的 `[7/9]` 回歸測試首版又漏設子行程工作目錄，導致 worktree 偵測完全沒被觸發，皆已誠實記載並修復。
- **Architect 架構專項評估**：確認雙原生腳本收斂、鎖/排程機制原生實作等既定架構決策在 R27 規模下仍然正確；重新驗證 DEF-101-271（`check_loc_budget.py` `SCAN_ROOT` 治理縫隙）現況——`dev_start.py` 仍 1772 行、零成長、未觸發 2000 行必修門檻。
- **修復落地**：`GitHooksInstallCommon.ps1` 呼叫棧判準修復（DEF-101-272）；`bootstrap.ps1` WindowsApps 排除 guard + 新增 `tools/tests/test_bootstrap_ps1.py`（DEF-101-273）；`windows_smoke_local.ps1` 新增 `[7/9]` 回歸鎖、`$MinPass` 11→12、步驟編號全數順移為 `/9`；`ONBOARDING.md`／`windows-compat-ci.yml` 步驟編號引用同步訂正；帳本新增 DEF-101-272/273/274/275 四筆條目。

### 四方一審（Architect/SA/SD/QA 獨立審查；SA 於主樹唯讀驗證，SD/QA 於獨立 git worktree 隔離執行 bug-injection，避免並行突變互踩）

- **Architect**：**APPROVE-with-conditions**（親自驗證 `[1]` 判準推理鏈成立，但指出殘餘理論缺口——若 dot-source 敘述本身被包在匿名 ScriptBlock/`Invoke-Expression` 內〔不經任何真實 `.ps1` 檔案〕，`[1]` 仍可能被騙；已記入 DEF-101-272 補充。同意 DEF-101-271/274 本輪不當場修，但指出擬議 2000 行門檻與既有 `ABSOLUTE_LIMIT=750` 絕對紅線落差 2.7 倍的認知不一致，已記入 DEF-101-274 補充。建議下一輪評估「呼叫棧內省猜情境」的根本重構〔`throw` 或顯式 switch〕）
- **SA**：**APPROVE**（無條件；獨立以既有回歸鎖+inline 探針+呼叫棧語意推導驗證 `[1]` 判準正確；確認 bootstrap.ps1 guard 與 dev_start.ps1 逐字一致、無回歸端影響；全庫 grep 確認步驟編號/PASS 數字引用零遺漏）
- **SD**：**APPROVE**（無條件；逐行核對呼叫棧語意與「計算一次、多處共用」設計無快取風險；以既有測試+探針+確定性推導驗證三種變體〔`[-1]`／「任一層」／`[0]`〕皆會如預期紅燈；因唯讀權限限制無法親手改檔做原地 bug-injection，已誠實聲明並建議由具寫入權者補跑紅燈驗證）
- **QA**：**APPROVE**（無條件；以雙層匿名 scriptblock 巢狀呼叫鏈親自嘗試繞過 `[1]` 判準，確認兩支生產安裝器皆於頂層直接 dot-source、無可達繞過路徑；對 `[7/9]` 做真實 bug-injection〔改回 `[-1]` 並 commit 後 clone 重跑〕確認變紅、且 `[3][4]` 仍綠，證實新測試精準鎖住舊測試漏掉的縫；驗證 `-like`/`-notlike` 大小寫不敏感、WindowsApps 三種大小寫變體皆正確排除；獨立發現一項與 R27 無關的環境相依假紅——`_usable_bash()` 在其 worktree PATH 組合下選中缺 coreutils 的精簡版 bash，導致 `.sh` 側一項既有測試假紅，已記入 DEF-101-275，判定非本輪回歸）

**針對一審發現的修復**：① `tools/bootstrap.ps1` 修法欄「與 dev_start.ps1 一致」措辭訂正為澄清 guard 邏輯一致、候選清單因情境不同而非逐字相同；② 補齊 `tools/tests/test_bootstrap_ps1.py`（DEF-101-273 原宣稱「新增測試」與實際不符，已誠實訂正並實際落地，經 bug-injection 確認鑑別力）；③ DEF-101-272/274 補充 Architect 一審發現的理論性殘餘缺口與門檻不一致；④ 新增 DEF-101-275 記載 QA 發現的環境相依測試基礎建設縫隙。回歸複驗：AutoClaude pytest 3608 passed/207 skipped、根層 unittest **361 tests OK**（skipped=10，較基線 359 增 2＝ `test_bootstrap_ps1.py` 兩案）、AISDLC_SDD ci-gate 雙軌 1478+1673+174、`windows_smoke_local.ps1` 標準 `-File` 呼叫 **PASS=12 FAIL=0**，皆與基線一致無回歸。

### 四方二審（SendMessage 保留一審上下文複審，皆親自重跑驗證修復落地）

Architect／SA／SD 三方 **APPROVE**（無條件）；QA **對 `test_bootstrap_ps1.py` 的 Test 2 做對抗式 bug-injection 找到真實裝飾性斷言缺口**——首版 Test 2（`test_real_python_outside_windowsapps_is_used_even_when_windowsapps_stub_present_first`）唯一斷言 `assertNotIn("找不到 python/py/python3", ...)` 對「選中空殼後執行失敗」與「選中真候選後執行失敗」兩條路徑皆為真（兩者輸出皆不含「找不到」字樣），對 bug-injection（改回舊版裸迴圈、誤選空殼）跑此測試**不會變紅**，未真正背書其 docstring 宣稱的「證明選中真候選」，屬裝飾性斷言。

**修復**：改用 `.cmd` 假直譯器（Windows PATHEXT 解析下 `Get-Command python3`／`& python3` 皆會找到 `python3.cmd`，經最小 repro 確認）取代先前不可執行的 `"MZ"` 佔位位元組，令假直譯器被呼叫時印出唯一標記字串 `FAKE_PYTHON3_INVOKED`，正向斷言該標記真的出現——直接證明 bootstrap.ps1 選中並執行了 python3 這個候選、而非空殼。**過程記事三**：修復過程中發現一個新的獨立陷阱——原本想額外斷言 `$LASTEXITCODE`（假直譯器以 `exit /b 42` 收尾），但實測 `powershell -Command "& 'script.ps1'"` 這種巢狀呼叫下，內層腳本的 `exit N` 不會透傳成外層 powershell.exe 行程自身的 exit code（最小 repro：`exit 42` 單獨測試外層恆回 1），這是 `-Command` 巢狀呼叫本身的獨立行為特性、非 bootstrap.ps1 缺陷，與本輪 `GitHooksInstallCommon.ps1` 呼叫棧語意同屬「`-Command` 巢狀呼叫有自己一套規則」家族；已放棄該斷言，只保留標記字串斷言。修復後以相同 bug-injection（改回舊版裸迴圈）重跑確認 Test 2 正確變紅（錯誤訊息可見卡在 WindowsApps 空殼、從未印出標記），還原後重新確認綠燈，根層 unittest 361 tests OK（skipped=10）無回歸。

四方二審最終結論：**全數 APPROVE**。本輪 R27 全部異動（`tools/lib/GitHooksInstallCommon.ps1`、`tools/windows_smoke_local.ps1`、`tools/bootstrap.ps1`、`tools/check_wrapper_thinness.py`、`tools/tests/test_bootstrap_ps1.py`、`ONBOARDING.md`、`.github/workflows/windows-compat-ci.yml`、`docs/06_quality/AutoSDD_Defect_Log.md`）可放行。本輪最終複驗：AutoClaude pytest 3608 passed/207 skipped、根層 unittest 361 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+174、`windows_smoke_local.ps1` 標準 `-File` 呼叫 PASS=12 FAIL=0、三支既有機械閘門（`check_script_parity`/`check_wrapper_thinness`/`check_ntfs_paths`）皆綠，與前置基線完全一致無回歸，準備提交。

**收尾階段機械閘門另揪出一項四方複審範圍外的真實缺口（DEF-101-276）**：四方複審結束、準備提交前的最終 `AISDLC_SDD ci-gate.sh` 全套重跑，`scripts/tests/test_ci_paths_cover_root_consumers.py::test_all_root_consumers_covered_by_ci_paths[macos-compat-ci.yml]` 由綠轉紅——新增的 `tools/tests/test_bootstrap_ps1.py` 以 `REPO_ROOT / "tools" / "bootstrap.ps1"` 直接引用 `tools/bootstrap.ps1`（Windows 專屬腳本），但該測試檔同活在 `windows-compat-ci.yml`／`macos-compat-ci.yml` 兩份 workflow 皆會執行的 `tools/tests/` 目錄下（macOS runner 預裝 `pwsh`，該測試不會被 `@unittest.skipIf` 跳過），`macos-compat-ci.yml` 的 paths 過濾清單卻缺這一項——若未來只改 `tools/bootstrap.ps1` 本身，macOS 側這個回歸鎖不會被觸發（DEF-101-042 同構假綠盲區，此為該機械鎖第四次於本 repo 抓到同款缺陷、且是本鎖第一次由**新增測試檔本身**觸發而非由改動根層腳本觸發）。**修復**：`macos-compat-ci.yml` 的 push／pull_request 兩份 paths 清單皆補上 `tools/bootstrap.ps1`（比照既有 `tools/install_windows_nightly.ps1` 等三支 .ps1 顯式列舉慣例）；重跑 `test_ci_paths_cover_root_consumers.py` 10 tests 全綠，`AISDLC_SDD ci-gate.sh` 雙軌 1478+1673+174 回到全綠。**教訓（記事存證）**：本輪四方複審的審查範圍鎖定「跨平台相容性本身」（`GitHooksInstallCommon.ps1`／`windows_smoke_local.ps1`／`bootstrap.ps1`），未涵蓋「新增測試檔案本身對 CI paths 覆蓋契約的連帶影響」這個治理層面——下一輪若再新增消費根層檔案的測試，應在本輪收尾前就主動重跑 `test_ci_paths_cover_root_consumers.py`，而非等最終 ci-gate 全套重跑才發現。
