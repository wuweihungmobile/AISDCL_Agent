# AutoSDD 缺陷帳本 — Archive 05（R16~R26 四方一審/二審/三審裁決敘事）

> 本檔為 `AutoSDD_Defect_Log.md` 依 DEF-99-001 輪替政策搬遷之歷史敘事區段（R27 主檔逼近/超過 256KB 界線時建立），**原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。內容為 R16 至 R26 各輪「四方一審／二審／三審裁決總結」敘事段落，其缺陷現況已被主檔上方「缺陷總表」live 狀態取代，本檔僅供歷史脈絡查閱。

---

## 四方一審／二審裁決總結（R26，2026-07-23）

真 Windows 11 機器複審——本輪使用者明確要求「Architect 全面檢視多平台相容性設計架構是否合理、進行最佳化改善設計」，故本輪 Architect 任務加重為兩部分：Part A 架構最佳化評估（重點）＋ Part B 傳統架構層缺陷掃描。

- **前置基線**：AutoClaude pytest 3608 passed/207 skipped、根層 unittest 359 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+174，四支既有機械閘門（`check_script_parity`/`check_wrapper_thinness`/`check_ntfs_paths`/`check_defect_log_crossref`）皆綠，本輪動工前重跑確認與 R25 收尾狀態完全一致、無回歸。
- **全面掃描（Scan-A/B/C/D 四維度，皆背景 agent 獨立執行）**：A（Shell/PowerShell）、B（Python 跨平台）零新發現；C（CI/排程基建）發現 `windows-compat-ci.yml` 從未在真實 CI 執行 `tools/install_windows_nightly.ps1`（即使 `-WhatIf` 安全預覽），與 `macos-compat-ci.yml` 對 `install_mac_nightly.sh --render-only` 的真實 CI 覆蓋不對稱（DEF-101-269）；D（文件/帳本）發現 `Nightly_Forensic_Discipline.md` 版本元資料落後於 R22 實際內容編修、`AutoClaude/CLAUDE.md:260` 引用版本號又更落後一版（DEF-101-270）。
- **Architect 架構專項深度評估（Part A，本輪重點）**：實測盤點全倉雙原生腳本對子、`platform_utils.py` 抽象層，並重跑四支既有機械治理工具全數 exit 0，給出 11 項具體評估（A1~A11），核心結論：雙原生腳本「薄殼＋Python 核心」收斂（R12/R16）已徹底落地且有機械防腐化（`check_wrapper_thinness.py`）；smoke 腳本與 nightly 安裝腳本維持厚雙原生實作是刻意且合理的例外（原生語法驗證本質上無法被 Python 包一層消除）；鎖機制/排程機制維持平台原生實作是正確的 OS 邊界判斷；CI workflow 尚不到值得抽 composite action 的量體。額外挖出一項新治理縫隙：`AutoClaude/tools/check_loc_budget.py` 的 LOC 分級只掃 `AutoClaude/autoclaude/`，根層 `tools/dev_start.py`（現已 1772 行）等薄殼化後的 Python 核心檔完全不受管轄（DEF-101-271，P4，判定需人工決策新分級門檻、本輪不當場修）。
- **修復落地**：`windows-compat-ci.yml` 於 `windows-smoke` job 新增步驟以 `-WhatIf` 呼叫 `install_windows_nightly.ps1` 並斷言輸出含 `Register-ScheduledTask`（DEF-101-269）；`Nightly_Forensic_Discipline.md` 補記 v1.10 版本追溯記載 R22 措辭訂正、`AutoClaude/CLAUDE.md:260` 版本號同步訂正（DEF-101-270）；帳本新增 DEF-101-269/270/271 三筆條目。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆親自重跑驗證非採信摘要）

- **Architect**：APPROVE-with-conditions（親自實機執行 `install_windows_nightly.ps1 -WhatIf` 確認零副作用、不需 elevation；重跑四支機械治理工具與 359+20 tests 全綠；必修條件：DEF-101-271 補具體觸發門檻避免無限期延後——已落地；另發現 CI 新步驟行內註解 `*>&1` 與實際程式碼 `2>&1` 不符，已訂正）
- **SA**：APPROVE-with-conditions（親自實機驗證新 CI 步驟斷言邏輯確實會通過；比對 macOS 側驗證強度，指出 Windows 側只驗證「沒 crash + 固定字串」弱於 macOS `plutil -lint` 的結構驗證，記入 backlog 供下輪參考，非本輪阻斷）
- **SD**：APPROVE-with-conditions（逐行核對 YAML 語法與 `$LASTEXITCODE` 管道語意，親自 bug-injection 三種情境〔錯誤旗標／腳本不存在／執行期 throw〕確認斷言皆正確觸發、非裝飾性；必修條件同 Architect 命中 `*>&1`/`2>&1` 不符——已訂正）
- **QA**：APPROVE（對抗式 bug-injection：刪除 `install_windows_nightly.ps1` 真正的 `Register-ScheduledTask` cmdlet 呼叫、只留 `ShouldProcess` 字串字面量，重跑 `-WhatIf` 後 CI 新步驟斷言依然通過——證實此步驟只驗證 WhatIf 路徑字面量、不驗證真實安裝邏輯本身，屬「從零覆蓋提升至部分覆蓋」而非「完整覆蓋」；建議如實記入帳本揭露此侷限，已落地）

**修復落地（回應一審必修條件）**：① `windows-compat-ci.yml` 新步驟行內註解由「需 `*>&1` 合流才捕捉得到」訂正為「屬子行程原生 stdout，2>&1 合流後即可捕捉得到」，`AutoSDD_Defect_Log.md` DEF-101-269 對應描述同步訂正；② DEF-101-271 補具體觸發門檻「`dev_start.py` 超過 2000 行即升級為該輪必修」；③ DEF-101-269 補記 QA 的 bug-injection 實驗與結論，誠實揭露新 CI 步驟鑑別力侷限。

### 四方二審（SendMessage 保留一審上下文複審，皆親自重跑驗證修復落地）

Architect／SD／QA 三方 **APPROVE**（無條件）；SA **APPROVE-with-conditions**（獨立命中同一括號不對稱瑕疵，已於收到 Architect 二審回報時同步修復）。二審過程中 Architect、SA、SD 三位審查員各自獨立發現同一項極小排版瑕疵——註解訂正時漏補收尾括號（純文字，不影響 YAML 解析與 CI 行為），已即時修復並經 `yaml.safe_load` 複驗語法合法。三方獨立命中同一瑕疵屬本輪多方複審交叉印證價值的具體體現，非遺漏放大。

四方二審最終結論：**全數 APPROVE**，本輪 R26 全部異動（4 檔：`windows-compat-ci.yml`、`Nightly_Forensic_Discipline.md`、`AutoClaude/CLAUDE.md`、`AutoSDD_Defect_Log.md`）可放行。本輪最終複驗：AutoClaude pytest 3608 passed/207 skipped、根層 unittest 359 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+174、四支既有機械閘門（`check_script_parity`/`check_wrapper_thinness`/`check_ntfs_paths`/`check_defect_log_crossref`：帳本 114 筆有效狀態）皆綠，與前置基線完全一致無回歸，準備提交。

## 四方一審／二審／三審裁決總結（R25，2026-07-23）

全面掃描（四維度 Scan-A/B/C/D＋Architect 架構專項檢視，5 個唯讀 agent 背景並行）＋ 修復 ＋ Architect/SA/SD/QA 四方一審 ＋ 修復必修項 ＋ 四方二審 ＋ 追加優化修復 ＋ 四方三審（原班人馬 SendMessage 保留上下文，三輪皆複審）：

- **前置基線**：AutoClaude pytest 3608 passed/207 skipped、根層 unittest 350 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+174 全綠，與 R24 收尾數字完全一致，本輪動工前重跑確認無回歸。
- **全面掃描（A/B/C/D 四維度＋Architect）**：本輪四維度掃描與 Architect 架構專項檢視**皆無新的 P2 級跨平台缺陷**（相對 R14~R24 連續多輪的收斂趨勢，本輪是首次「掃描本身零新發現」的整輪，反映累積 24 輪修復後的穩定度）；但四位掃描者一致坐實 R23 遺留 **DEF-101-263** 六項 backlog 中有四項（①②③⑤）現在可當場修，不應再無謂延後。Architect 架構專項檢視另外針對使用者本輪特別要求的「架構是否合理、有無最佳化空間」給出具體結論：雙原生腳本收斂範圍已無「維護成本超過收斂收益」的轉折點（五個歷史收斂候選皆已於 R12/R16 處理完畢，`check_script_parity.py` 的全掃描機制已自動化「該收斂哪支」的判斷）、抽象邊界無新重複模式待抽象、排程能力對照表模式暫無推廣需求（無問題驅動）、帳本主檔（213KB）成長速度加快但未達歸檔門檻，建議下次撞到門檻時把「裁決敘事」與「缺陷表格」拆檔歸檔。四大既定架構決策維持現狀，理由具體（非照抄前輪）。
- **修復落地**：DEF-101-263 ①（`check_ntfs_paths.py` U+FFFD 可讀性說明）②（heartbeat 正則跨檔字面鎖，鏡子自證測試）③（windows/macos compat CI 6 個 job 層 concurrency 區塊機械回歸鎖，`TestCompatCiConcurrencyLock`）⑤（`_WINDOWS_EXIT_DECISION_RE` 加 `\b` 單字邊界）四項全數修復；④（dot-source `-Command` 包裝理論性盲點）維持 backlog（需人工設計決策，全庫零實例）；⑥（`[Environment]::Exit` 跳過 `finally`）reclassify 為「已查證無害、觀察性記事」（親讀兩支生產呼叫端確認 dot-source 前皆無 `try` 包裹）。修復後根層 unittest 358 tests OK（skipped=10，較基線 +8＝新增測試數）。
- **四方一審**：Architect **APPROVE-with-conditions**（點名 `test_ps1_literal_end_exit_decision_lines_present_and_matched` 讀 `.ps1` 用 `encoding="utf-8"` 與同檔既有 `utf-8-sig` 慣例不一致，Rule 11 風格瑕疵；確認④⑥重分類判斷站得住）；SA **APPROVE-with-conditions**（指出 `\b` 對連字號結尾單字如 `high-end`/`front-end` 仍會誤判，屬同類殘留風險；`docs` 措辭「bug-injection 驗證」易誤讀成「檔內含自動化負向案例」，建議訂正用詞）；SD **APPROVE**（逐項 bug-injection 確認 4 項修復皆有真實鑑別力，`_job_concurrency_re()` 的 `re.escape` 正確、無過度/不足跳脫）；QA **APPROVE-with-conditions**（三支機械閘門全綠、對抗式驗證帳本宣稱皆屬實；**回報本輪最重要的發現**——`run_root_unittests.py` 連續 14 次中 3 次失敗，約 21%，無法在單獨/隔離重跑中穩定重現，記錄為 open watch）。
- **修復一審必修項目**：① `test_ps1_literal_end_exit_decision_lines_present_and_matched` 改用 `encoding="utf-8-sig"`（Architect 條件）；② DEF-101-263 帳本措辭訂正「經手動 bug-injection…測試檔本身未內建自動化負向案例」（SA 條件）；③ **假紅根因調查**——主控反組譯 `.pyc` 確認 `\b` 修復已正確編譯、以 52 次獨立 concurrent repro（cold/warm cache 混合、最高 8-way）皆 0 失敗排除位元碼寫入競態與正則邏輯缺陷，改判根因為「四位一審審查員以單一訊息並行派出，審查過程中彼此對共用主樹（`dev_start.py`／`windows-compat-ci.yml`）做暫時性 bug-injection，與同時段其他審查員的全套回歸執行時間窗重疊」，符合既有已知模式 [[parallel-mutation-audit-collision]]，記入 DEF-101-263。
- **四方二審**：Architect **APPROVE**（親驗 utf-8-sig 訂正、親自重演「對主樹做 bug-injection 時期間主樹確實短暫存在壞版本」，以第一手證據坐實根因判定，並建議把「bug-injection 一律用 Edit 復原、禁用 `git checkout --`」升級為審查 SOP 硬性檢查點）；SA **APPROVE**（撤回一審條件外的觀察，追加提出負向後顧 `(?<![\w-])` 優化建議以一併關閉連字號殘留風險，並誠實揭露自己也對 `windows-compat-ci.yml` 做過同類暫時性突變）；SD **APPROVE**（時間序精確回溯：自己第一次執行到假紅測試時尚未動過任何主樹檔案，症狀與「檔案被另一方暫時改回無 `\b` 版本」完全吻合，同意新根因判定，判定為 [[parallel-mutation-audit-collision]] 第三次重演）；QA **APPROVE**（撤回一審保留條件——把 R23 舊版〔無 `\b`〕正則套用到失敗當時字串，結果與觀測到的錯誤訊息逐字吻合，決定性佐證根因判定；主動揭露自己也做過 `git stash`／`windows-compat-ci.yml` 暫時性突變）。
- **二審後追加修復**：採納 SA 建議，`_WINDOWS_EXIT_DECISION_RE` 由 `\b` 改為負向後顧 `(?<![\w-])`，新增 `test_hyphenated_end_word_prevents_false_positive` 回歸鎖，bug-injection 確認鑑別力。**過程意外（誠實揭露）**：驗證後主控本人誤用 `git checkout -- tools/dev_start.py` 還原，把該檔所有未 commit 的 R25 修改一併抹回 R24 committed 狀態（[[git-checkout-mutation-revert-hazard]] 已記錄陷阱的第三次重演，這次是主控本人而非派出的 agent）；已用 Edit 逐段重建並重跑全套確認一致（根層 unittest 359 tests OK, skipped=10），記入該記憶檔案與 DEF-101-263。
- **四方三審**（針對二審後追加修復的小範圍複核）：Architect **APPROVE**（親自 bug-injection 復驗負向後顧邏輯正確；認同「bug-injection 一律用 Edit 復原」應寫進 SOP）；SA **APPROVE**（獨立寫跳脫 pytest 的純 regex 測試覆蓋 8 案例＋3000 次緊迴圈零誤判，證實修復邏輯 100% 確定；**但意外在完全無其他審查員干擾的單一 pytest 呼叫下仍以約 1/15 機率重現同款假紅**，改查 `.pyc` mtime 與加 `PYTHONDONTWRITEBYTECODE=1` 消除假紅，鎖定更精確的獨立成因——位元碼快取寫入競態，記為 **DEF-101-268**）；SD **APPROVE**（regex 對照表+bug-injection 雙重確認無新 edge case；亦記錄一次類似瞬時讀值觀察，判定為同類現象第四次重演跡象）；QA **APPROVE**（三支機械閘門全綠、測試計數逐一核對吻合：146→10/10、根層 359 tests）。
- **收尾補帳**：DEF-101-263 六項殘留 backlog 中 ①②③⑤ 全數 fixed@R25（⑤含二審後追加的負向後顧強化）、④維持 backlog（需人工設計決策）、⑥ reclassify 為已查證無害；新增 **DEF-101-268** 記錄位元碼快取寫入競態這一獨立於「跨審查員主樹突變互踩」之外的第二條假紅成因，open watch，留待下輪評估是否要 repo-wide 停用位元碼快取。

四方三審最終結論：Architect／SA／SD／QA 四位對本輪全部修復（DEF-101-263①②③⑤ 主修復 + SA 建議的負向後顧追加優化）**一致 APPROVE，無保留條件**。本輪最終複驗：根層 unittest 359 tests OK（skipped=10，較 R24 基線 350 增 9＝本輪新增測試數：8 支主修復＋1 支負向後顧回歸鎖）；三支既有機械閘門（`check_defect_log_crossref.py`／`check_pytest_baseline_sites.py`／`check_script_parity.py`）全綠；AutoClaude pytest／AISDLC_SDD ci-gate 本輪未涉及對應程式碼變更，維持前置基線數字不變（3608/207、1478+1673+174）。準備提交。

## 四方一審／二審裁決總結（R24，2026-07-23）

全面掃描（四維度 Scan-A/B/C/D＋Architect 架構專項檢視，5 個唯讀 agent 背景並行）＋ 修復 ＋ Architect/SA/SD/QA 四方一審 ＋ 修復必修項 ＋ 四方二審（原班人馬 SendMessage 保留一審上下文複審，發現殘留缺口後再修復）：

- **前置基線**：AutoClaude pytest 3608 passed/207 skipped、根層 unittest 350 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+174 全綠，與 R23 收尾數字完全一致，本輪動工前重跑確認無回歸。
- **全面掃描（A/B/C/D 四維度＋Architect）**：Scan-A（路徑/編碼/換行/檔案系統）本輪無新發現（既有機械守門複驗全過，27,403 個追蹤路徑零違規）；Scan-B（腳本雙軌對稱）發現 **DEF-101-264**（`run_self_evolution.sh`/`.ps1` 在 git 指令失敗時的語意分歧，`_EXEMPT_PAIRS` 既知侷限的具體坐實案例）；Scan-C（CI/CD 與排程）發現 **DEF-101-265**（`windows-latest` runner 實際對應 Windows Server 2022、與宣稱標的 Windows 11 用戶端環境揭露不對稱），並確認 GitHub CI 帳單停擺（DEF-101-081）持續至本輪；Scan-D（文件契約帳本）發現 **DEF-101-266**（pytest 基線數字 3,607→實測 3,608 純新鮮度落差）；Architect 架構專項檢視結論**架構穩定、零必修**（四大既定架構決策——雙原生腳本收斂範圍、抽象邊界、排程能力對稱性、帳本治理——重新核實均未發現新理由推翻既有判斷）。
- **修復落地**：3 項新發現全數修復（DEF-101-264 兩腳本 git 失敗語意對齊；DEF-101-265/266 純文件補強），修復後 3 檔異動。
- **四方一審**：Architect **APPROVE-with-conditions**（親自追蹤程式流程，指出 DEF-101-264 帳本用詞對「鏡像 .sh 保證語意」過度宣稱，`git add` 失敗時 `$applied` 仍被誤標記已完成）；SA **APPROVE-with-conditions**（獨立命中 DEF-101-264 行號引用誤植、及「跨 PS 版本行為一致」措辭對 `$PSNativeCommandUseErrorActionPreference` 版本相依風險過度宣稱）；SD **APPROVE-with-conditions**（與 Architect 各自獨立命中同一 `$applied` 誤標記現象，並查證 PowerShell/PowerShell repo issue #18368 佐證版本相依疑慮的另一面向）；QA **APPROVE-with-conditions**（親查本機無 pwsh 7+ 屬實、獨立做四組邏輯骨架模擬驗證判斷式正確性；記錄本腳本對子全域零自動化測試覆蓋的既有缺口，及 DEF-101-265 描述方向筆誤）。**主控 zero-trust 複驗關鍵爭議**：Architect 與 SD 皆引用「`.sh` 側 `set -euo pipefail` 下 `git add` 失敗會讓整支腳本立即中止」作為 `$applied` 誤標記問題成立的理由——主控以三組獨立 bash 實測交叉驗證，**證實此引用理由技術上不成立**（bash `-e` 對 `&&` 串列中非最終陳述式失敗有明文豁免），但兩人獨立指出的**核心現象本身**（`$applied` 誤標記）經讀碼確認真實存在、且為兩腳本共享的既有邏輯缺陷（非跨平台分歧），依使用者「所有問題須修復」指示仍一併處理。
- **修復必修項目**：① `run_self_evolution.ps1` 新增 `$PSNativeCommandUseErrorActionPreference = $false`，讓顯式 `$LASTEXITCODE` 檢查成為唯一、版本無關的判斷路徑；② 兩腳本同步修復「`git add`/`git commit` 失敗時誤標記已完成」（新增 **DEF-101-267**）；③ DEF-101-264/265 帳本行號引用與方向描述訂正、過度宣稱措辭收斂。
- **四方二審**：SA **APPROVE**（親驗 `$PSNativeCommandUseErrorActionPreference = $false` 在所有可執行 PS 版本下安全、帳本訂正屬實）；Architect 與 SD **各自獨立**再度命中同一殘留缺口——DEF-101-267 的 `.ps1` 修復只檢查了 `git add` 的 `$LASTEXITCODE`，**未檢查 `git commit` 自身是否成功**，commit 失敗時仍會誤標 `$applied=$true`（與本項原本要根除的缺陷同類，只是換了個位置重現）；QA 亦以骨架模擬**獨立第三次**命中同一缺口。三位獨立審查員（Architect/SD/QA）於二審階段收斂到同一個精確技術建議（巢狀檢查 `git commit` 自身 `$LASTEXITCODE`），主控據此修復並重跑語法驗證。
- **收尾補帳**：DEF-101-267 追加「二審訂正」段落記載 Architect/SD/QA 二審再度獨立命中同一缺口的過程，方法論註記提醒「修復宣稱『已鏡像對方語意』時須逐一核對鏈中每個指令，而非檢查了一環就宣稱整條鏈已對齊」。

四方二審最終結論：SA 為 **APPROVE**，Architect／SD／QA 為 **APPROVE-with-conditions**（二審發現的 `git commit` 退出碼檢查缺口已同輪修復並重驗，帳本已同步訂正）。本輪最終複驗：AutoClaude 3608 passed/207 skipped、根層 350 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+174，與前置基線完全一致（本輪修復範圍未新增測試案例，皆為腳本邏輯與純文件修復），三支既有機械閘門（`check_defect_log_crossref.py`／`check_pytest_baseline_sites.py`／`check_script_parity.py`）全綠，準備提交。

## 四方一審／二審裁決總結（R23，2026-07-22）

真 Windows 11 機器複審（延續 R20~R22 真機基線）——全面掃描（四維度 Scan-A/B/C/D＋Architect 架構專項檢視，5 個唯讀 agent 背景並行）＋ 修復 ＋ Architect/SA/SD/QA 四方一審 ＋ 修復必修項 ＋ 四方二審（原班人馬 SendMessage 保留一審上下文複審）：

- **前置基線**：AutoClaude pytest 3608 passed/207 skipped、根層 unittest 338 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+173 全綠、`windows_smoke_local.ps1` PASS=11 FAIL=0，與 R22 收尾數字完全一致，本輪動工前重跑確認無回歸。
- **全面掃描（A/B/C/D 四維度＋Architect）**：Scan-A（Shell/PowerShell）發現 DEF-101-261（`GitHooksInstallCommon.ps1`/`.sh` docstring 示範可互動式 dot-source，但內部驗證失敗裸 `exit` 會誤殺使用者 shell）；Scan-B（Python）發現 DEF-101-260（`check_ntfs_paths.py` 缺 `errors="replace"`）；Scan-C（CI/排程基建）無新發現，但確認坐實 DEF-101-200 兩個舊帳 rider（ARCH-R15-1 Windows 心跳 FAIL 偵測缺口、SCAN-C-11 windows-compat-ci concurrency 語意風險）仍真實存在；Scan-D（文件帳本）發現 DEF-101-262（ruff baseline 1,339→實測 1,147 三處過期文字）；Architect 架構專項檢視結論**架構穩定、零必修**（兩項過去候選優化——雙原生腳本再收斂、排程宣告檔——皆給出具體「現在不該做」理由，非含糊延後）。
- **修復落地**：5 項全數修復（DEF-101-260/261/262 三項新發現＋DEF-101-200 兩個 rider 一併處理，符合「坐實的舊帳不再延後」原則）。修復後 11 檔異動，全套回歸零回歸。
- **四方一審**：Architect **APPROVE**（親自實機重跑 5 項驗證、`yaml.safe_load` 逐 job 比對 concurrency 拆分，皆吻合）；SA **APPROVE-with-conditions**（獨立重現 ARCH-R15-1/SCAN-C-11 場景確認修復生效；抓到 `GitHooksInstallCommon.ps1` 模組頂層 python 檢查分支的 `exit` 在 dot-source 情境下不會終止呼叫端腳本，PowerShell 頂層 vs 函式內 exit 作用域差異）；SD **APPROVE-with-conditions**（bug-injection 逐項驗證測試鑑別力；抓到 Windows heartbeat FAIL 正則對格式零容忍，3 種真實變體皆假陰性）；QA **APPROVE-with-conditions**（親跑全套回歸；獨立命中與 SA 相同的 `GitHooksInstallCommon.ps1` exit 語意問題，交叉印證；另記錄 4 項非阻斷 backlog）。主控親自重現 SA/QA 點名的 PowerShell exit 語意問題（3 組對照實驗）與驗證 `[Environment]::Exit` 修法有效，確認發現屬實。
- **修復必修項目**：① `GitHooksInstallCommon.ps1` 模組頂層分支改 `[Environment]::Exit(1)`（不受 dot-source 巢狀腳本作用域限制），新增回歸測試並 bug-injection 正反驗證；② `_WINDOWS_EXIT_DECISION_RE` 改大小寫不敏感+空白容忍，新增 3 支對應 SD 點名案例的測試。DEF-101-261 帳本追加訂正段落如實記載先前驗證範圍過度聲稱與追加修復。
- **四方二審**：Architect **APPROVE**（無新增條件，額外評估 `[Environment]::Exit` 副作用範圍，確認現有呼叫路徑無 `finally` 被跳過風險）；SA **APPROVE-with-conditions**（獨立反向 bug-injection 三次確認 `[Environment]::Exit(1)` 修復真實生效；抓到 SD 的正則修復未落帳、帳本測試數字停留舊值）；SD **APPROVE**（親跑 3 個假陰性案例確認修復；另發現正則放寬後假陽性面擴大〔任何 end 結尾單字皆可能誤觸發〕與 `[Environment]::Exit` 跳過 `finally` 兩項真實但風險可控的非阻斷觀察，皆判斷現況無害不構成阻擋）；QA **APPROVE-with-conditions**（親跑全套回歸零回歸＋反向 bug-injection 確認修復；指出一審記錄的 4 項 backlog 未寫入帳本，要求本輪補齊存證，否則審查產出會隨裁決收斂而遺失）。
- **收尾補帳**：DEF-101-200 的 ARCH-R15-1 rider 段落更新為 7 tests 並說明追加的 3 支邊界測試；新增 **DEF-101-263** 彙整 QA 一審 4 項＋SD 二審 2 項共 6 項非阻斷 backlog（NTFS U+FFFD 可讀性、heartbeat 正則跨檔字面鎖缺口、CI concurrency 缺機械回歸鎖、dot-source `-Command` 包裝理論性盲點、正則放寬假陽性面擴大、`[Environment]::Exit` 跳過 `finally`），逐項記錄檔案路徑與判定理由，供下一輪追蹤。

四方二審最終結論：Architect／SD 為 **APPROVE**，SA／QA 為 **APPROVE-with-conditions**（帳本收尾條件已同輪落地）。本輪最終複驗：AutoClaude 3608 passed/207 skipped、根層 350 tests OK（skipped=10，較基線 338 增 12＝本輪新增測試數）、AISDLC_SDD ci-gate 雙軌 1478+1673+174（scripts/tests 較基線 173 增 1）、`windows_smoke_local.ps1` PASS=11 FAIL=0，準備提交。

## 四方一審裁決總結（R22，2026-07-22）

真 Windows 11 機器複審（延續 R20/R21 真機基線）——全面掃描（四維度 Scan-A/B/C/D，皆背景 agent 獨立執行）＋ Architect 架構專項檢視 ＋ Architect/SA/SD/QA 四方一審：

- **前置基線**：AutoClaude pytest 3607 passed/207 skipped、根層 unittest 338 tests OK（skipped=10）、AISDLC_SDD ci-gate 雙軌 1478+1673+173 全綠、`windows_smoke_local.ps1` PASS=11 FAIL=0，本輪動工前重跑確認無回歸。
- **全面掃描（A/B/C/D 四維度）**：A 維度（Shell/PowerShell）零新發現；B 維度發現 N3（`test_pre_push_dispatcher.py` `_python_dir()` fallback 同款反模式，但觸發窗口極窄）與 DEF-101-258（4 孤兒腳本）；C 維度發現 DEF-101-257（Windows nightly log 零保留期）與若干 CI 效率性發現（pip cache 不一致，P3~P4，同意延後）；D 維度發現 `ONBOARDING.md` §7 pytest 基線數字過期約 8 輪，且 `check_pytest_baseline_sites.py` 只防多站點分歧、不驗證 SSOT 自身是否過期（結構性盲區，記事存證）。
- **Architect 架構專項檢視**：架構整體依然穩定，本輪無新架構級缺口；但發現過去 5 輪「零架構級發現」部分是被帳本文字滯後掩蓋的假象——DEF-101-200／233／242／243／247／068(b) 六筆狀態文字皆已過期（實際修復已在 R16/R19/R20 落地，帳本未回頭同步），其中 DEF-101-200 尤其不可簡化訂正為單純 `fixed`：該列於 R15 捆綁三個 rider（ARCH-R15-5＝本輪 DEF-101-257 本身、ARCH-R15-1、SCAN-C-11），SA/SD 一審獨立交叉複核同一疑慮，若籠統訂正會讓仍開著的 ARCH-R15-1／SCAN-C-11 從追蹤中消失。Architect 並指出「排程能力對照契約」測試從未落地（DEF-101-259）是比單純漏測更危險的治理縫隙型態（守門文字宣稱由他處負責，他處其實未做），建議本輪順手補齊。
- **四方一審裁決**：Architect／SA／SD／QA 對六筆帳本訂正候選皆 **APPROVE**（各自親自核實對應程式碼/測試存在且行為相符，非照單全收掃描結論）；對 DEF-101-257（nightly log 保留期）、DEF-101-258（孤兒腳本）、DEF-101-259（排程能力契約）三項新發現，Architect／SA／SD 一致列為**本輪必修**（皆為小工程量、已有明確修法或既拖延 5+ 輪的舊帳，不應再無謂延後）；QA 對抗式驗證額外確認 N4「4 個孤兒腳本」計數須明確排除 `tmp_lint_check.py`（該檔實有呼叫端，非孤兒），並用 bug-injection 驗證 DEF-101-242/243 訂正所引用的新測試回歸鎖確實有鑑別力（非裝飾性）。N3（`_python_dir()` fallback，測試層級、觸發窗口極窄）與 CI pip cache 不一致（純效率）四方一致同意延後，理由具體（非無謂拖延）。
- **修復落地**：`run_local_nightly.ps1` 補 14 天 log 輪替＋靜態鎖測試＋暫存目錄實機驗證三案例（DEF-101-257）；刪除 4 個確認零呼叫端的孤兒腳本（DEF-101-258）；新增 `test_schedule_capability_parity.py`（語意對照表，非字面比對，含 bug-injection 驗證，DEF-101-259）；訂正 `Nightly_Forensic_Discipline.md` 誤導措辭；`ONBOARDING.md` §7 更新巢狀 session 數字（3,557/206 → 3,607/207）並如實揭露 bootstrap 出廠環境數字待另行以乾淨 venv 重驗（不可用舊公式反推造假數字）；訂正 `check_script_parity.py` 對 `install_windows_nightly.ps1` 失實的豁免註解；帳本 DEF-101-200/233/242/243/247/068(b) 六筆狀態文字精確訂正（拆分子項，非籠統改 `fixed`）。修復後重跑 `check_pytest_baseline_sites.py`／`check_defect_log_crossref.py`／`check_script_parity.py` 三支機械守門確認皆通過。

### 四方二審（R22，2026-07-22）

Architect／SA／SD／QA 四方獨立二審，皆親自 Read/Grep/實跑核實（非照單全收一審修復報告），結論**全數 APPROVE，無條件**：

- **Architect**：逐項核實六筆帳本訂正與五項修復皆真實落地，`python -m pytest tools/tests/ -q` 全套 334 passed/10 skipped 無回歸，`git status` 異動範圍與描述完全對應、無夾帶未揭露改動。
- **SA**：獨立在暫存目錄重做一次 log 輪替實機驗證（含刻意把 `nightly_latest.log` 也調成 30 天前），行為與宣稱吻合；確認 DEF-101-200 拆分粒度做對（未讓 ARCH-R15-1／SCAN-C-11 兩個未核實子項隨手被關閉）；確認 ONBOARDING.md 未用公式反推造假數字。
- **SD**：獨立對 `test_schedule_capability_parity.py` 做 bug-injection（移除 `install_windows_nightly.ps1` 的 `$Uninstall` switch），確認測試真的變紅、非裝飾性；技術指引（PowerShell 寫法、對照表設計、不可字面比對）皆被精確採納。
- **QA**：全庫 grep 複驗 4 孤兒腳本刪除無死連結、`tmp_lint_check.py` 確認未被誤動；獨立 bug-injection 證實 log 輪替邏輯的雙重防護（`-Filter` 與 `-ne` 皆可單獨擋下誤刪 latest）；獨立 bug-injection 證實排程能力對照測試有鑑別力；抽驗 DEF-101-247／DEF-101-259 帳本引用皆屬實。**新發現一項非阻斷 backlog**（記入 DEF-101-257 補充：`test_nightly_log_retention_rotation_present` 為結構測試非行為測試，若 Filter 未來改寬則現有測試偵測不到防線退化，排入下一輪）。

四方二審一致 APPROVE，R22 全面掃描-修復-複審閉環完成。

## 四方複審裁決總結（R21，2026-07-22）

真 Windows 11 機器複審（延續 R20 首輪真機基線）——全面掃描（四維度）＋ Architect 架構專項檢視 ＋ Architect/SA/SD/QA 四方一審二審：

- **前置基線**：AutoClaude pytest 3607 passed/207 skipped、根層 unittest 336 passed、AISDLC_SDD ci-gate（1478+1673+173 tests 全綠）、`windows_smoke_local.ps1` PASS=11 FAIL=0，四項本輪動工前後皆重跑確認無回歸。
- **Architect 架構專項檢視**：架構穩定，本輪無新架構級發現；訂正一項過期前提——`find_git_bash()` 雙實作分歧（DEF-101-236）經獨立核實**已於 R17 修復並補結構等價鎖、R19 追加行為驅動測試**，非待辦；提出一項非必修優化建議（排程「意圖」抽成平台無關宣告檔，列未來候選）。
- **全面掃描（A/B/C/D 四維度）**：僅 B 維度（Python 跨平台）發現 1 項新缺陷 **DEF-101-256**——`copy_functional_interpreter()` 未複製直譯器同層 DLL，未啟用 venv 的裸直譯器（pyenv-win／winget 版型）在 Windows 上複製後啟動失敗（`STATUS_DLL_NOT_FOUND`），純測試基建假紅、不影響 production；A/C/D 三維度掃描後無超出既有帳本的新發現。
- **四方一審**：Architect **REJECT**（程序性——當時僅有掃描發現與建議修法，程式碼尚未實際落地，判定不可對未存在的 diff 放行；同時給出具體技術指引：DLL 來源目錄須用 `Path(sys.executable).parent`、不可沿用 `pyvenv.cfg` 分支層級）；SA **APPROVE-with-conditions**（缺陷範圍描述須訂正為「任何未啟用 venv 的官方支援安裝路徑」而非窄化成 pyenv-win 專屬）；SD **APPROVE-with-conditions**（同 Architect 指出目錄層級風險，並要求具名 glob pattern 而非裸 `*.dll`）；QA **APPROVE-with-conditions**（要求新增環境無關自證測試、避免平台條件分支寫法、警示「條件寫反」風險形態）。四方技術指引高度收斂，隨即派修復 agent 落地。
- **修復落地**：`copy_functional_interpreter()` 補上無條件（非平台分支）具名 DLL glob-and-copy，來源/目的目錄變數與既有 pyvenv.cfg 分支完全獨立命名；新增 `TestCopyFunctionalInterpreterDllCopy`（2 支環境無關自證測試）；新增 DEF-101-256 帳本條目（含真機 pyenv-win `git stash` 前後對照 e2e 證據）；訂正 DEF-101-236 狀態為 `fixed@R17`；`ONBOARDING.md` 補排除提示。修復後主控親自複核 diff 並重跑全套確認無回歸（根層 338 tests、AutoClaude 3607 tests 皆綠）。
- **四方二審**：Architect **APPROVE**（親讀確認必修項全落地，DLL pattern 覆蓋度評估足夠，`fixed@R21` 宣稱有真實證據支撐）；SA **APPROVE-with-conditions**（必修項確認落地；發現 `ONBOARDING.md` §1 用詞與帳本引用有微小落差，同輪補上「即官方 python.org 安裝器版型」字樣訂正；另觀察到新測試一次間歇性假紅，經主控在二審全數結束、無並行擾動後獨立重跑 8＋3 輪全綠，判定為二審期間多方並行對同一檔案做突變測試/還原的暫態跡變，非真缺陷）；SD **APPROVE**（親手用暫存腳本把目錄層級改錯重跑新測試，確認會變紅，證明測試對此類退化有鑑別力）；QA **APPROVE**（親手做繞過測試——故意打錯 glob pattern 字串重跑新測試確認變紅，並肯定帳本 e2e 證據具體可信）。
- **附帶事項（如實記錄）**：二審期間 SD 回報工具輸出中出現一則疑似注入的偽造 system-reminder（聲稱檔案被外部改動並指示「別告知使用者」），SD 未採信並主動揭露；QA 驗證中誤觸 `git checkout --` 清空未提交修復，已即時以 Edit 逐字還原並經 `git diff` 位元組級核對一致。主控在二審全程獨立留存 diff 快照比對，確認上述兩起事件皆未造成實際損害。

四方二審最終結論：Architect／SD／QA 為 **APPROVE**，SA 為 **APPROVE-with-conditions**（條件已同輪落地，實質等同 APPROVE）。DEF-101-256 修復完成並經真機 e2e 與四方獨立驗證，DEF-101-236 帳本狀態訂正完畢。本輪最終複驗：AutoClaude 3607 passed/207 skipped、根層 338 tests OK、AISDLC_SDD ci-gate 全綠、`windows_smoke_local.ps1` PASS=11 FAIL=0，準備提交。

## 四方一審裁決總結（R20，2026-07-22）

真 Windows 11 機器複審——Architect／SA／SD／QA 四方獨立審查（皆真機執行驗證，非僅閱讀程式碼；Architect 額外做架構層深度檢視）：

- **Architect**：APPROVE（Part 1 架構層檢視：SSOT 收斂良好無新漏網、雙原生腳本對子〔smoke／install_nightly〕列為長期優化候選非本輪必修、Mutex vs mkdir lock 各自平台原生手法為正確架構決策、DEF-101-249 類缺陷暴露「Windows-only cmdlet 真機驗證覆蓋盤點」系統性盲區之建議；Part 2 本輪複審：親自重現 DEF-101-249 crash 與 Mutex 移除回歸，真機重跑 PASS=11、根層 336 測試皆綠）
- **SA**：APPROVE-with-conditions（逐字核對 `-Status` 與 mac 版語意真對等；真機重現 Mutex 持鎖/釋放行為；額外窮舉核對三支排程腳本共 8 個 ScheduledTasks cmdlet 全部參數名，未發現本輪已知缺陷外的第二個參數錯誤；條件為 DEF-101-254 兩項建議，已同輪落地）
- **SD**：APPROVE（逐行核對三支修改檔案控制流與語法；`AbandonedMutexException` catch 型別過濾器真機驗證正確；發現並提出 DEF-101-254① 建議，已落地）
- **QA**：APPROVE-with-conditions→（修復後）APPROVE（對抗式 bug-injection 對六項標的逐一驗證：`-Status` exit code／`New-ScheduledTaskSettingsSet` 參數名／Mutex 靜態鎖／`_SH_EXCLUSIVE_PASS_GROUPS` 緩解／`os.spawnv` mock／smoke `[8/8]` 真實鑑別力；找到 2 項必修真實假陽性〔DEF-101-252 Mutex 靜態鎖可被邏輯廢掉繞過、DEF-101-253 參數值極性反轉繞過靜態測試〕，皆本輪修復並經 bug-injection 重新驗證確認變紅）

四方合計本輪新增 5 筆缺陷記錄（DEF-101-248~254，含 3 項必修 P1/P2 於一審視窗內全數修復並經對抗式驗證，2 項非阻斷建議同輪一併落地），另關閉 1 筆舊 open 項（DEF-101-228）。所有「必須修復」項目已於一審視窗內處理完畢，修復後以 SendMessage 派回四方原審查 agent（保留一審上下文）複審：Architect／SA／SD 皆親自重現 bug-injection 場景並給出 APPROVE；QA 複審換新角度（不重複一審手法）再戳修復本身，找到 1 項新繞過——DEF-101-255（`assertNotRegex` 正則大小寫敏感，`:$False` 大寫變體可繞過 DEF-101-253 修復，與其同一根因的新變體），本輪立即修復（補 `re.IGNORECASE`）並經 QA 原始注入重現確認變紅。QA 另記錄兩項觀察性發現（Mutex 片段擷取器之 `re.search` 只認第一個相符區塊的理論風險、`[8/8]` 新步驟對 `ShouldProcess` 閘門本身無隔離驗證），皆判定非本輪風險、記入未來留意即可。全部必修項於複審視窗內處理完畢，四方對最終狀態皆給出 APPROVE，進入最終本機驗證與收尾。

## 四方一審裁決總結（R17，2026-07-21）

Architect／SA／SD／QA 四方獨立審查（皆直接於主工作樹操作，未用 git worktree 隔離）：

- **Architect**：APPROVE-with-conditions（F1 CI paths 盲區必修項已修復；F2/F3/F4 為非阻斷建議記事存證）
- **SA**：APPROVE-with-conditions（F1 帳本行數再漂移、F2 同 Architect F1、F3 註解精確度，三項皆已修復/訂正）
- **SD**：APPROVE-with-conditions（`windows_smoke_local.ps1` git 版本守衛失效、`Copy-ItemWithRetry` 註解不精確，兩項 P3 皆已修復）
- **QA**：APPROVE-with-conditions（親自重跑 314+3701+173+1475+1674 測試全綠＋144 skip 全數分類正常＋4 項回報修復逐一獨立覆核屬實；另揪出 2 項 P2 測試保護力缺口，QA 自判非阻斷、已記入 DEF-101-242 排下輪）

四方合計提出 4（Architect+SA 交叉/獨立）+2（SD）+2（QA）＝8 項發現，其中 6 項（DEF-101-241 ①②③④）於一審視窗內全數修復並經 QA 複審獨立驗證確認（含真實 pwsh 執行、非僅語法檢查）；剩餘 2 項（DEF-101-242）為 QA 自身判定非阻斷的測試覆蓋殘留缺口，記事存證排入下一輪。並行審查期間偵測到與 R16 同款的暫態污染（Architect/SD/QA 各自 bug-injection 時序重疊造成的檔案內容瞬態變化），依既有緩解方式（獨立 `git status`/`diff` 核查）確認皆已妥善還原、非真實缺陷。所有「必須修復」項目已於一審視窗內處理完畢，進入最終本機驗證與收尾。

## 四方一審／複審裁決總結（R18，2026-07-22）

前置全面掃描（Shell/PowerShell、Python、CI/排程基建、文件帳本 4 個獨立 agent ＋ Architect 架構檢視，皆背景並行、唯讀）零 P0，共 6 項需修（1 P1＋2 P3＋1 P2＋2 P4）；修復按檔案所有權切成 2 個不重疊修復包並行執行。Architect／SA／SD／QA 四方獨立一審（皆直接於主工作樹操作，未用 git worktree 隔離）：

- **Architect**：APPROVE-with-conditions（P1 必修：`ONBOARDING.md:203` `PASS=8` 未同步 `windows_smoke_local.ps1` 改成的 `$MinPass=10`，親跑 `tools/run_root_unittests.py` 實測 `test_smoke_ci_sync.py` 真的 FAIL；其餘 6 項修復逐一驗證通過）
- **SA**：APPROVE-with-conditions（獨立揪出 Architect 未提及的 P2：`.github/workflows/windows-compat-ci.yml` 第 674 行 `windows-nightly-full` job 的「安裝 AutoClaude 開發 + lint 依賴」步驟，有與本輪已修部分相同的 R15 SCAN-C-10 pip exit code 吞沒缺陷未修，屬本輪掃描漏網項目）
- **SD**：APPROVE（逐行/語法/全域回歸皆綠，但一審僅跑 `AutoClaude pytest` + `AISDLC_SDD ci-gate.sh`，未跑根層 `tools/run_root_unittests.py`，故未發現上述 Architect 點名的 P1）
- **QA**：APPROVE-with-conditions（bug-injection＋`git stash` 對照確認 P1 為本批異動自身造成、非既有缺陷；另合記 3 項非阻斷測試保護力缺口，已記入本表 DEF-101-243 排下一輪）

一審共 2 項必修（Architect 與 QA 各自獨立命中同一個 `ONBOARDING.md` PASS 數字問題，交叉印證；SA 獨立命中 CI workflow 漏網處），皆由主控直接就地修復（複審揪出的小缺陷、一行修規模，未另開修復包）：① `ONBOARDING.md:203` `PASS=8`→`PASS=10` 並補述 R18 新增 `[7/7]` 檢查說明；② `.github/workflows/windows-compat-ci.yml` 674 行區塊補 `$LASTEXITCODE` 檢查，逐字鏡射同檔既有「Install AutoClaude deps」步驟寫法。修復後以 `SendMessage` 派回四方原審查 agent（保留一審上下文）複審，四方**全數 APPROVE**（Architect/SA/QA 皆親自重跑 `test_smoke_ci_sync.py`／`run_root_unittests.py`／yaml lint 驗證修復生效且未引入新問題；SD 本輪複審把根層測試補進驗證範圍，記錄為流程教訓）。QA 複審時合記的 3 項非阻斷測試保護力缺口已記入 DEF-101-243 排入下一輪。並行一審期間未偵測到暫態污染。所有「必須修復」項目已於一審→複審視窗內處理完畢並全數 APPROVE，進入最終本機驗證與收尾。

## 四方一審裁決總結（R16，2026-07-21）

Architect／SA／SD／QA 四方獨立審查（皆直接於主工作樹操作，未用 git worktree 隔離——本輪實測 worktree 只會 checkout 至最後一次 commit、看不到任何未提交異動）：

- **Architect**：APPROVE-with-conditions（DEF-101-232 描述訂正 + `bootstrap_core.py` buffering 補齊，皆已修復；DEF-101-236 排入 backlog）
- **SA**：APPROVE-with-conditions（DEF-101-239 已修復並重新驗證）
- **SD**：APPROVE（DEF-101-237／DEF-101-238 為非阻斷 P3/P4，排入 backlog）
- **QA**：APPROVE（獨立重跑六項核心驗證數字與宣稱精確吻合；5 項 bug-injection 紅/綠驗證證實本輪新增測試皆非偽綠燈）

四方合計親手執行 bug-injection 實驗 15+ 項，全數證實對應測試/守門機制真實鎖住各自修復，未發現偽綠燈或誇大不實的驗證聲稱（除 DEF-101-239 一項已誠實記錄並即時修復）。所有「必須修復」項目已於一審視窗內處理完畢，待重新完整驗證後進入複審確認。

