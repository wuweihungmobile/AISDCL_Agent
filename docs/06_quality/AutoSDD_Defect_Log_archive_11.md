# AutoSDD 缺陷帳本 — Archive 11（R36 四方一審/二審裁決敘事）

> 本檔為 `AutoSDD_Defect_Log.md` 依 DEF-99-001 輪替政策搬遷之歷史敘事區段（R39 主檔逼近 256KB 界線時建立，依 R38 收尾建議執行），**原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。內容為 R36「四方一審／二審裁決總結」敘事段落，其缺陷現況已被主檔上方「缺陷總表」live 狀態取代，本檔僅供歷史脈絡查閱。

---

## R36 四方複審裁決總結（2026-07-24）

本輪使用者要求同 R16 起既有固定格式：全面掃描四維度＋Architect 架構最佳化評估，發現問題即修復，再經 Architect/SA/SD/QA 四方獨立審查至全數 APPROVE。

- **前置基線**：AutoClaude pytest 3742 passed/146 skipped、`tools/tests/` 409 passed/3 skipped、AISDLC_SDD `ci-gate.sh` 全通過（v0.01:1475、v0.30:1674、scripts/tests:184），本輪動工前重跑確認與 R35 收尾狀態一致、無回歸。帳本主檔 224,914 bytes，遠低於 256KB 上限，本輪無需提前歸檔。
- **全面掃描（Scan-A/B/C/D 四維度 + Architect 架構深度評估，皆背景 agent 獨立平行執行）**：A（Shell/PowerShell）、B（Python 跨平台）、C（CI/排程/hooks 基建）、D（文件/帳本一致性）**四維度掃描本輪皆零新發現**——Scan-D 特別複核歷史高復發風險項（帳本歸檔計數同步）確認「九檔」與實際 9 個 archive 檔案吻合、無第四度復發；Architect 深度評估複核既有 backlog DEF-101-307（WSL System32 雙 SSOT 孤島）與 DEF-101-308（`test_dev_start_ps1_lastexitcode.py` 靜態計數鎖可被 decoy 繞過），前者發現低成本收斂路徑已具備並建議本輪落地（避免長期堆積 backlog 本身變成技術債），後者以 bug-injection 重新驗證仍成立、維持 backlog 判定；另掃描 AutoClaude 核心套件、AISDLC_SDD fsm_runtime 全目錄與跨 repo 重複實作，零新發現，判斷既有「薄殼＋Python 核心＋SSOT＋交叉鎖」演進路線在 36 輪迭代後仍屬克制、無規模不經濟訊號，建議維持現狀不做根本性重構。
- **修復落地**：依 Architect 設計收斂 DEF-101-307——`tools/integration_gate_core.py::_has_system32_segment()` 改 `import bash_probe_spec as _spec` 取代硬編字面值 `"system32"`；`tools/lib/bash_probe_spec.py::SYSTEM32_SEGMENT` 常數上方補消費者清單註解；`tools/tests/test_find_git_bash_parity.py::_extract_py_system32_word()` 同步改為斷言依賴 SSOT 常數（防退回硬編字面值）。修復落地後以 bug-injection 驗證測試鑑別力（還原硬編字面值→正確變紅），並重跑三軌全套回歸確認無退化。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆於主工作樹直接操作、不使用 `isolation: worktree`）

- **Architect**：**APPROVE**（無條件）——親自讀三檔全文確認 import 慣例與既有四個消費者（`AISDLC_SDD/scripts/bash_probe.py` 等）一致；兩種 bug-injection（硬編字面值還原、SSOT 值漂移為 `"system64"`）皆被正確攔截，確認為真實 SSOT 收斂而非換皮不換骨；範圍確認僅 3 檔異動、無溢出。
- **SA**：**APPROVE**（無條件）——逐項核對消費者清單／docstring／帳本狀態皆準確；確認 `check_defect_log_crossref.py`／CI paths 機械鎖無新覆蓋缺口。
- **SD**：**APPROVE**——除既有兩種 bug-injection 手法外，另用第三種手法（誘餌行內註解＋還原硬編字面值）發現 `_extract_py_system32_word` 的未錨定 regex 縫隙（詳見 DEF-101-309），判定為繼承自既有 `_extract_*` 系列方法論的限制，非本輪新增/加重，列 backlog、非阻擋。
- **QA**：**APPROVE**（無條件）——全套回歸三軌數字與基線逐一比對皆一致；`ruff check` 三檔皆過；`git status` 僅 3 個預期檔案異動。回報審查過程中兩度遭遇工作目錄並行污染（`SYSTEM32_SEGMENT` 短暫讀到 `"system64"`、檔案被重置進 git stash），已妥善還原並在穩定狀態下完成驗證，建議未來輪次改用獨立 git worktree 隔離各審查角色。

**針對一審發現的處理**：SD 發現的誘餌註解繞過縫隙（DEF-101-309）經二審三方（Architect/SA/QA）交叉覆核後正式記入帳本；QA 建議的獨立 worktree 隔離流程改善予以記錄，非本輪阻擋項。

### 四方二審（SendMessage 保留一審上下文複審，分享交叉發現）

- **Architect**：**APPROVE**（無條件）——獨立重放 SD 的誘餌註解手法確認屬實，並多做一步驗證找到正交緩解因子：`ruff check` 對「誘餌註解＋悄悄退回硬編字面值」的失效模式會因 `_spec` import 變成未使用觸發 `F401`，兩層防禦（測試結構鎖 vs. lint AST 引用分析）恰好互補。同意 DEF-101-309 列 backlog（修法需錨定至函式範圍，超出本輪範圍，不成比例）。背書 QA 的獨立 worktree 建議，並提供自己一審過程獨立撞見同款污染的第一手佐證。
- **SA**：**APPROVE-with-conditions**——獨立重現 SD 的繞過手法後，**精修嚴重度定性**：新版 `_extract_py_system32_word`（import 回傳 golden 值）的繞過門檻低於舊版（不需偽造正確值），是本輪重寫引入的實質弱化而非單純繼承；要求獨立記入帳本（而非僅存於審查報告）作為必修收尾項——已依此意見以 DEF-101-309 獨立列出並採用 SA 的精確定性。確認本輪程式碼異動本身仍應放行，不需回頭修改。
- **SD**：**APPROVE**——自我覆核確認送審 diff 未受污染事件波及；補充「誘餌繞過」風險評級由「純理論攻擊」上修為「亦有 stale-comment-drift 自然觸發路徑」，仍判定非本輪阻擋；診斷出本輪「system64」污染事件的根因正是自己在 bug-injection B 步驟對共用檔案的即時改動與其他審查者併發讀取重疊，非外部竄改；同意採用 `EnterWorktree`/`ExitWorktree` 作為未來 bug-injection 階段的隔離手段。
- **QA**：**APPROVE**（無條件）——二次核實 `tools/tests/` 回歸數字穩定（409 passed/3 skipped）；獨立以最小可行實驗覆核誘餌繞過手法屬實，同意列 backlog；同意將獨立 worktree 建議正式記入本輪帳本。

**針對二審發現的處理**：依 SA 精修後的嚴重度定性，DEF-101-309 已獨立記入帳本（見上方缺陷總表），非僅折疊入 SD 的非正式報告；四方最終一致同意本輪 SSOT 收斂程式碼異動本身正確、不需修改即可放行。

**四方複審最終結論：全數 APPROVE**（Architect/SD/QA 無條件 APPROVE；SA 附帶條件為「獨立記錄 DEF-101-309」，已完成，不影響程式碼放行）。本輪 R36 全部異動（`tools/integration_gate_core.py`、`tools/lib/bash_probe_spec.py`、`tools/tests/test_find_git_bash_parity.py`、`docs/06_quality/AutoSDD_Defect_Log.md`）可放行。

**環境異常揭露**：本輪審查過程中，主控與 Architect/SD/QA 三方**各自獨立遭遇同一起工作目錄污染事件**——`tools/lib/bash_probe_spec.py::SYSTEM32_SEGMENT` 一度被改成 `"system64"`，且主控收到一則可疑的 system-reminder，聲稱此變更為使用者/linter 有意所為並要求**不要告知使用者**。主控未採信此指示，直接核實磁碟檔案內容後確認確實被改壞、立即修復回 `"system32"`，並在此如實向使用者揭露，不隱瞞。SD 二審診斷根因：此為 SD 自己在 bug-injection 實驗中即時修改共用檔案、與其他審查者併發讀取重疊所致的真實資源競爭（同 R31~R35 已記載的「並行 bug-injection 互相污染」同根現象），非外部惡意竄改；三方（Architect/主控/QA）亦各自獨立撞見同起異常，交叉印證此為併發共用工作樹的必然結果。所有相關檔案最終皆以 `git diff HEAD` 位元級核對確認與委審異動完全一致，無資料遺失或未還原殘留。QA 建議下一輪起 bug-injection 階段改用獨立 `git worktree` 隔離各審查角色，Architect/SD 皆背書此建議，列入下一輪流程改進項（非本輪阻擋）。

**已知限制（如實記載）**：DEF-101-308（`test_dev_start_ps1_lastexitcode.py` 靜態鎖字面計數可被刻意 decoy 繞過，R35 開出）、DEF-101-309（`test_find_git_bash_parity.py` 新增的 SSOT 依賴斷言可被誘餌註解繞過，本輪開出）維持 open backlog，皆為測試鑑別力層面的縫隙、非生產程式碼缺陷，四方一致判定非阻擋。

**收尾驗證**：全套回歸最終重跑——AutoClaude pytest 3742 passed/146 skipped、`tools/tests/` 409 passed/3 skipped、AISDLC_SDD `ci-gate.sh` 全通過（v0.01:1475、v0.30:1674、scripts/tests:184）、`ruff check` 三個異動檔案皆過、`git status` 僅預期 4 個檔案異動（3 個程式/測試檔 + 本帳本），帳本 `check_defect_log_crossref.py` 狀態一致。
