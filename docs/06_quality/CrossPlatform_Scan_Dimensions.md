# 跨平台複審 Scan-A~H 掃描維度慣例（正式規格）

> **緣起**：Mac/Windows-11 相容性複審輪（R1 起持續累積；最新輪次見 `docs/06_quality/AutoSDD_Defect_Log.md`
> 最末列——本檔刻意不寫死輪號，R56 發現原寫「累積至今 R47」時實況已是 R55，且與同檔下方
> 內容自相矛盾）自 ~10+ 輪前開始，習慣把每輪掃描
> 拆成「Scan-A/B/C/D」四個維度分工，但此慣例此前只活在各輪缺陷帳本列的引用文字裡
> （如 `docs/06_quality/AutoSDD_Defect_Log.md` 的 DEF-101-265／269／289／352／353），從未有
> 一份獨立文件把字母對應的維度定義寫下來——新加入的審查員/agent 只能逐一翻歷史帳本引用逆向
> 推敲字母含義。本檔（DEF-101-387 落地）補上這道缺口，**只做正式定義，不重複教學**。

## 維度定義（A~E 為 R56 定案的五維；F／G 為 R59 新增、H 為 R60 新增，理由見表後）

| 維度 | 範圍 | 典型產出/信號 | 歷史帳本佐證 |
|------|------|--------------|-------------|
| **Scan-A** | 廣泛／背景 agent 通用掃描，**無固定子範圍**——不預設鎖定某類檔案或機制，讓 agent 自由發現跨平台問題 | 任意類型缺陷（路徑穿越、編碼、guard 覆蓋…皆可能命中） | DEF-101-352（R43 Scan-A：`pty_executor.py`／`prompt_dispatcher.py` 路徑穿越，背景 agent 全面掃描發現） |
| **Scan-B** | 檔名淨化／防增生鎖覆蓋率——`component_sanitizer` 家族（`_sanitize_component`／`_sanitize_log_filename`）與 WindowsApps guard 家族（`windowsapps_guard.sh`／`WindowsAppsGuard.ps1`／`is_real_python_candidate`）的覆蓋面是否有語言/檔案類型/呼叫點遺漏 | 未淨化呼叫點、guard 覆蓋不對稱（如某語言/某檔案缺席） | DEF-101-353（R43 Scan-B：WindowsApps guard 只收斂 `.ps1`／`.py`，9 支 bash 呼叫端從未排除） |
| **Scan-C** | CI/CD 與排程基礎設施維度——workflow（`.github/workflows/*-compat-ci.yml`）的 `runs-on`／步驟覆蓋是否對稱、nightly 佈線（`run_local_nightly.*`）是否對等、runner 環境（如 `windows-latest`＝Server SKU 而非用戶端 Windows 11）是否誠實揭露 | workflow 步驟缺席、平台落差未揭露、排程機制不對稱 | DEF-101-265（R24 Scan-C：Windows runner 實為 Server 2022，未如 macOS 側揭露）；DEF-101-269（R26 Scan-C：`windows-compat-ci.yml` 從未實跑 `install_windows_nightly.ps1 -WhatIf`） |
| **Scan-D** | 缺陷帳本／文件維度——基線數字新鮮度（如 pytest passed/skipped 是否隨新測試增長而回填）、帳本歸檔輪替（是否逼近 256KB 上限）、跨文件引用一致性（帳本 vs `ONBOARDING.md` 等 crossref 目標是否各說各話） | 基線數字落後、帳本超限未歸檔、跨文件狀態矛盾 | DEF-101-289（R32 Scan-D：`ONBOARDING.md` §7 pytest 基線落後實測 +11） |
| **Scan-E**（＝ Architect-Design） | Architect 架構最佳化評估——針對跨平台相容性既有架構慣例（dispatcher 模式／薄殼收斂／SSOT 收斂／Copy-on-Evolve 凍結政策／CI paths 白名單／帳本基線唯一站點等）逐項複核設計合理性，非缺陷掃描 | 架構判準記錄、SSOT/收斂建議、既有慣例是否仍成立的複核結論 | DEF-101-412（R52 Architect 記錄 evaluator_command 同進程/跨進程判準，見下節）；DEF-101-413（R53 Scan-B＋Architect-Design 交叉發現） |
| **Scan-F**（**R59 新增**，＝ Runtime／載具） | **在目標平台上「真的把東西跑起來」**，比對可觀測行為與宣稱是否一致——入口腳本（`bootstrap`／`dev_start`／平台 smoke／nightly／三個本機閘門）實跑、跨兩種載具（原生 PowerShell vs Git Bash、真 `.exe` vs `.bat` shim、pyenv vs venv 直譯器）的行為差分、以及**驗證載具自身有無鑑別力** | 只在執行時現形的缺陷（假紅／假綠／恆紅／靜默零輸出）、載具事故、skip 明細所揭露的環境降級 | DEF-101-502（entry-point 依賴 hash 缺口）／503（`%` 被 batch shim 吃掉致 stage 恆紅）／504（開工流程與 nightly 撞車製造整批假紅）／506（同平台不同啟動方式用到不同直譯器）／509（Windows 專屬腳本的語法閘門在 Windows 上 skip）／510（skip 可見度單向）／511（smoke 經 Git Bash 產生假紅） |
| **Scan-G**（**R59 新增**，＝ backlog 接續稽核） | 上一輪（或更早）登記為 `deferred`／`backlog`／`open watch` 的項目**是否有存在的承接者**——指向的輪次是否真的存在、解鎖條件是否具體到可執行、本輪是否讓某個 backlog 家族的複本數靜默增長 | 孤兒 backlog（指向已作廢/不存在的輪次）、空話式解鎖條件、只論證一種修法就宣告延後、複本數靜默 +1 | DEF-101-521（R58 整輪作廢後四處「列 R58 backlog」成為無主孤兒，且 R59 在同一家族新增第 5 份複本）；DEF-101-517 的解鎖條件經 ARCH-R59-06／SA-R59-06 交叉指出只覆蓋最貴的一條修法 |
| **Scan-H**（**R60 新增**，＝ 護欄層自檢／「掃鎖自己」） | **標的是護欄層本身**，不是生產碼——每一支新增／修改的機械鎖、豁免表、稽核工具是否符合本 repo 對「鎖已落地」的認定門檻；以及護欄層的**規模趨勢**是否仍與它擋下的缺陷量相稱 | 無牙的鎖（注入缺陷不轉紅）、恆真斷言、無 stale 自檢的豁免表、鎖的散文寫死可機械算出的數字、稽核工具「可重跑但沒有任何閘門看它的 rc」、護欄行數成長率 > 它擋下的缺陷 | DEF-101-562（產生器只保證受抽取 token 新鮮、同一行散文照樣 stale）／DEF-101-563（表② 四格零機制）／ARCH-R60-02（稽核工具四道閘門零接線、唯一間接接線是恆真斷言）／ARCH-R60-07（保全用裸 `assert`，`python -O` 即蒸發）／ARCH-R60R2-04（新鎖在自己明文禁止的事情上犯規：docstring 寫死筆數且寫錯）／ARCH-R60-06（豁免表靠 docstring 命中撐著永不退場） |

自 R50 起連續多輪「五維掃描」已是實務穩定用詞（見缺陷帳本 DEF-101-394/396/403/412/413/414 等），R56 將正式定義從四維補齊至五維，消除「新審查員需翻歷史帳本逆推 Scan-E／Architect-Design 字母含義」的落差。

### 為何 R59 必須加 Scan-F／Scan-G（實證，非推論）

R59 的 SA 複審在本輪資料上做了一次逐筆歸因，結論是**既有五維存在結構性盲區**：

> R59 共 **23** 筆條目（`DEF-101-502`~`524`，四方一審後又補了 521~524；本段初稿寫「19 筆」是一審前的計數，由二審 SA 訂正），其中 `DEF-101-502`~`506`／`509`／`510`／`511` 共 **8 筆的「發現情境」欄明寫是
> 「R57 落地後首次真 Windows 開機開工」或「R59 主控實測」，一筆都沒掛在 Scan-A~E 任何一維**。
> 而該 8 筆內含 **5 筆 P1**（502 entry-point 依賴 hash 缺口、503 `%` 被 shim 吃掉、504 nightly 撞車假紅、506 直譯器不決定性、**509** Windows 專屬腳本的語法閘門在 Windows 上 skip）。五維掃到的是 507/508/512/513/514/517/518/519——重要，但**沒有一筆是 P1**。
> **二審 SA 訂正兩處計數**：本段初稿寫「4 筆 P1」漏列 509；另初稿寫「全部落在這 8 筆裡」，而一審後新增的 **DEF-101-522 也是 P1 且不在該 8 筆內**。**但立論方向不受影響、反而更強**——509 是「實跑後逐支讀 skip 明細」發現、522 是「原生 PowerShell 探針」發現，兩者都正是 Scan-F 的語意（在目標平台真的把東西跑起來、並確認載具自身有鑑別力）。

**根因**：A~E 五維的定義與判例全部是**讀 repo 檔案**的靜態面。Scan-A 雖自稱「無固定子範圍」，但其定義與歷史判例（路徑穿越、編碼、guard 覆蓋）都是讀檔，agent 從未被要求把東西跑起來。於是下列三類問題**結構上不可達**：

1. **只在執行時現形**——本輪 4 筆 P1 在磁碟上看起來完全正常（`%`-formatting 是合法 Python、`$script:PyExe = 'python'` 是合法 PowerShell），只在跑起來、且跑在特定載具上才炸。此前這一維完全依賴「人肉偶然開機」。
2. **工具鏈／環境版本漂移**——pyenv-win `python.bat` vs 真 `.exe`、zsh vs bash 3.2、cp950 codepage、symlink 權限（本輪 `[WinError 1314]` 是從 skip 明細**讀出來**的，不是任何一維掃到）、260 字元路徑上限、防毒檔案鎖。這些在 repo 裡沒有對應檔案 → 掃檔案的維度不可能命中。
3. **零 artifact 缺口**——Scan-B/C 是「已知家族的對稱性」檢查，前提是家族已存在；某類平台風險在 repo 裡一份實作都沒有時，沒有東西可比對。

**另一個獨立盲區**：Scan-D 管「基線新鮮度／歸檔／crossref 一致」，但**不管「上一輪的 deferred 是否有承接者」**——這正是 R58 整輪作廢後四處「列 R58 backlog」能安然存活的結構原因（DEF-101-521）。故另立 Scan-G。

**Scan-D 的相關限制也一併記下**（同輪 SA 指出）：crossref 閘門做的是「文件 vs 文件」一致性，**沒有任何機械物拿文件裡的數字去跟機器重量一次**。這是 ONBOARDING §7 能長期單邊（DEF-101-515）、且 R59 新表初版又寫入中途快照（SA-R59-01）的結構原因。

> 🔴 **R60 訂正該限制的現況**（原句尾寫「目前對策是紀律…尚無機械鎖」，落地後已成假話——本檔自己就是 Scan-H 第一條判準的客戶）：ONBOARDING §7 現分兩表且各有機制。**表①**（根層 unittest 數、LOC 三數字）＝ live 鎖，取值來源是機器、閘門每次執行都當場重算（`tools/sync_onboarding_baselines.py --check`），並自 R60 round 3 起連**同一行的散文**也受管（DEF-101-562）。**表②**（AutoClaude pytest、三軌 ci-gate）機器算不出現場值，改以**因果式 presumed-stale 觸發器**：比對四套測試樹的內容指紋（`--check-snapshot`，接 pre-push 第 8 支守門與 root-infra-ci 第 14 道），指紋一變即判該表過期並指出一鍵回填指令（DEF-101-563）。**仍為紀律而非機械的部分**：指紋抓不到「生產碼變動改變 `parametrize` 來源」「docker daemon 可用性」「平台差異」三類（充分觸發器、非必要條件），且 macOS 欄至今零真機量測。

### 為何 R60 必須加 Scan-H（實證，非推論）

R60 的四方複審 **round 2** 提出 27 筆新發現，Architect 對其中自己那 6 筆做了逐筆歸屬，結論是：

> 本輪我提的 6 筆新發現中，**零筆**落在生產碼上——三筆在治理文件、一筆在新鎖自己的 docstring、一筆在新稽核的方言邊界、一筆是趨勢本身。

同輪量測：`tools/tests/*.py` 由 round 1 的 52 支／20,188 行增至 56 支／22,524 行（**一輪 +11.6%**，而 round 2 的唯一任務是「修 round 1 的 21 筆」），護欄層行數**已超過它所護的 AutoClaude 生產碼**（`check_loc_budget` total 見 ONBOARDING §7 表①）。

**根因**：Scan-A~G 全部把標的設在「生產碼／文件／執行期行為」，**沒有一維以護欄層自己為標的**。於是「新鎖以高於它擋下缺陷的速率生產新的未受檢面」這件事結構上不可達——它只能靠複審者順手發現，而複審者的任務書寫的是掃生產碼。R60 一輪內出現三個假綠**全部發生在護欄層自己身上**（帳本稽核工具零接線、保全用裸 `assert` 被 `-O` 蒸發、產生器只保證 token 不保證散文），是這個盲區的直接證據。

**Scan-H 的必跑項（下一輪起，缺一即該輪 Scan-H 未完成）**：

1. **每一支新增或修改的鎖，必附一次 bug-injection 紅綠實測**——注入它聲稱要擋的缺陷，貼出轉紅的逐字訊息 ＋ 控制組 0 failures。沒有注入證明的鎖一律視為 `NOT-PROVEN`，不得計入本輪成果。
2. **每一張豁免表／已知債名冊，必附 stale 自檢 ＋ 具名承接輪次**（對齊下方硬規則②）。刻意無 stale 自檢＝事實上的永久豁免。
3. **鎖的 docstring／註解不得寫死可由程式現查的數字**（筆數、列數、支數）。要提供量級提示就寫「以現查為準」。
4. **護欄層規模趨勢須逐輪量測並記入帳本**：`tools/tests/*.py` 支數與行數、`MIN_TESTS`、以及「同一語意的雙平台實作對數」（`tools/check_script_parity.py` 現查值）。判準是**後者必須下降**——把「多平台相容性」的標的從『再加一道驗證』轉為『減少需要驗證的平面』；護欄行數上升不算成果。
5. **稽核工具必須有閘門看它的 rc**。「可重跑但沒有任何閘門消費其 rc」與「不可重跑」是同一個病的兩種形狀。

## 架構判準：evaluator_command 分診問題（DEF-101-412）

R52 Architect 複核 `evaluator_command` 相關修復慣例時記錄一項前瞻性判準，供未來輪處理 evaluator_command 相關跨平台缺陷時作為**第一道分診問題**：

> 此 `evaluator_command` 是**同進程生成即消費**（可安全用 `sys.executable` 絕對路徑），還是**編譯期產出、執行期可能跨行程/環境/機器消費**（`sys.executable` 不安全，應假設目標 PATH 含對應 console script，不可用 `sys.executable`）？

- **同進程生成即消費案例**：`evolution/playbook_evolver.py`／`minimax_evolver.py` 的 `_derive_part_a_evaluator()`——同一 Python 行程內生成並立即由同行程消費，故 `sys.executable` 安全（見 DEF-101-394 修法）。
- **編譯期產出、執行期跨行程消費案例**：`infra/adapters/sdd_to_playbook_adapter.py` 的 `_EVALUATOR_TEMPLATE`（R53 DEF-101-413 後已由雙模板 tuple 收斂為單一字串常數，非複數）——本檔在編譯期產出 YAML 字串，執行期可能於完全不同的行程/環境/機器上被讀取執行，編譯時解析的 `sys.executable` 路徑在執行時未必存在；正確修法是去除裸 `python -m` 前綴、假設目標 PATH 含對應 console script（如 `pytest`），而非改用 `sys.executable`（見 DEF-101-403／DEF-101-413 修法與其「刻意未採用 sys.executable」的理由記載）。

動工前先問「這行指令是誰在何時執行」，誤用會把原本明顯的 `rc=127` 換成更難診斷的路徑不存在 `FileNotFoundError`。

## 架構判準：WindowsApps guard 三語言等價實作為何不可收斂（R56 Scan-E）

WindowsApps guard（排除 Windows Store App Execution Alias 空殼 `python.exe`）目前有**三份語言別的等價實作**：`tools/lib/windowsapps_guard.sh`（bash）、`tools/lib/WindowsAppsGuard.ps1`（PowerShell）、`tools/bootstrap_core.py`（Python）。每一輪的 Architect 都會把「三份實作＝SSOT 未收斂」重新列為候選發現、再逐一論證掉（R56 Scan-E 又花掉一次）。本節把該論證定案，供未來輪直接引用，不需重辯。

**(1) bootstrap 悖論——不可能以 Python 為單一 SSOT。** guard 的職責正是「在還沒有可用 Python 之前，判斷 Python 是否可用」。`tools/git-hooks/pre-push` 內的順序即為證據：先 `. "$TOPLEVEL/tools/lib/windowsapps_guard.sh"`（純函式定義、無副作用），再以 `if ! is_real_python_candidate python` 把關，**之後**才出現該檔第一個實際的 `python` 呼叫（`python -m py_compile`）——即 guard 必須在任何 Python 執行之前就能運作。（刻意以符號而非行號錨定：該檔為高頻改動檔，行號必漂移；覆核方式＝`grep -n 'windowsapps_guard\|is_real_python_candidate\|python' tools/git-hooks/pre-push` 確認三者的出現順序。R56 實測為 L46／L191／L204。）若把判斷邏輯收斂進 Python，判斷本身就需要先有可用 Python，邏輯上自我指涉。同理 `.ps1` 呼叫端（`bootstrap.ps1` 等）也必須在取得 Python 前完成判斷。故三份實作是**語言邊界造成的必要重複**，不是可收斂的實作重複。

**(2) 既有折衷——資料抽 SSOT、執行邏輯刻意保留多份。** 同類問題本 repo 已有定案先例：`tools/lib/bash_probe_spec.py` 把「探測規則的**資料**」（`PROBE_CMD`、期望輸出、System32 排除段）抽成單一真相源，但驗活的**執行邏輯**刻意保留三份獨立實作，理由明文寫在該檔 docstring——「以維持三份回歸鎖彼此獨立的鑑別力（不會因為共用函式本身壞掉而三份同時失效）」。WindowsApps guard 沿用同一折衷：三份實作之間的等價性不靠「收斂成一份」，而靠機械 parity 鎖保證——`tools/tests/test_windowsapps_guard_bash_parity.py` 與 `tools/tests/test_windowsapps_guard_cross_consistency.py`（含 repo-wide 前瞻掃描 + 附理由豁免白名單 + stale 自檢）。

**(3) 分診問句（動工前先問）。** 遇到「同一邏輯出現 N 份」的候選發現時，先回答：

> 這個重複是**實作重複**（同一語言、同一執行時機，該收斂成一份），還是 **bootstrap／語言邊界造成的必要重複**（跨語言、或需在該語言 runtime 尚不可用時執行，不可收斂）？

- 若為前者 → 收斂為 SSOT（如 R55 `BASE_DENY_CHARS`、DEF-101-238/429）。
- 若為後者 → **不收斂**，改為「資料抽 SSOT + 機械 parity 鎖」，並確認 parity 鎖確實有前瞻性（能抓到「新增第 N+1 份」而非只驗白名單內既有幾份——R43 曾因此翻修過一次）。

附帶邊界（R56 實測揭露，避免未來高估防護力）：parity 鎖屬正則/靜態掃描類防護，對「同時改名又改寫法」的再發明形狀存在既知盲區，見 `tools/tests/test_windowsapps_guard_cross_consistency.py` 內 `_STUB_NAME_RE`／`_STUB_PREDICATE_RE` 上方的變體對照表與方法論邊界說明（同 DEF-101-333 對本測試家族殘留繞過向量的四方一致裁定：三方各自構造出**不同類型**的繞過手法＝已觸及逐行正則相對於 AST 解析的結構性天花板，此時判準應從「是否可能被繞過」〔永遠是 yes〕切換為「當前投入 vs. 已知具體威脅模式是否相稱」。**R56 訂正**：本處原引 DEF-101-433，但該則前提〔`check_wrapper_thinness.py` 缺前瞻機制〕已於 R56 經 bug-injection 證偽——反向驗證實存於 `tools/check_script_parity.py` 的納管完整性掃描，故其「比例原則裁定」建立在不成立的前提上，不宜續作判例）。

## 架構判準：靜態掃描錨為何從三份複本收斂為 SSOT（R57 Scan-E，**改判 R56 裁定**）

> **為何必須寫在這裡**：上一節（WindowsApps guard）定案的是「**不可**收斂」，本節定案的是同一輪
> repo 內另一組重複「**應該**收斂」。兩者結論相反卻都成立——若不把判準寫清楚，未來輪的
> Architect 讀到上一節會誤以為「本 repo 對重複一律採不收斂」，而 R57 正是踩過這個坑：R56 曾
> 明文裁定「三份 `_CI_TREE_RE` 逐字複本刻意不收斂」，R57 把它推翻了。

**背景**：CI 的「pwsh 語法解析 + UTF-8 BOM 守門」step 掃描 N 棵樹，本機三處鎖
（`tools/tests/test_ps1_bom.py`／`test_smoke_ci_sync.py`／`test_ps51_compat.py`）各自從該 step
抽出樹清單比對，防「CI 與本機掃描面分歧」。R56 發現三份抽取正則是逐字複本，論證後裁定
「三份各有 `len==3` 斷言擋著、收斂屬跨檔重構逾越當輪界線」，列為 backlog 不收斂。

**R57 的改判與其實證**：三份讀的是**同一個檔案的同一個 step**，彼此**不構成獨立觀測**。實證即
DEF-101-481——三份的抽取式全部硬綁 `-Path` 具名參數，而 PowerShell 的 `-Path` 可省略；插入一棵
位置參數寫法的新樹後，三份共 20 支測試**同時**全綠。複製三遍只是把同一個盲點抄了三遍。

**(1) 分診問句（承接上一節，補上「同語言」側的細分）。** 上一節問的是
「實作重複 vs bootstrap/語言邊界造成的必要重複」。當答案落在「同語言、同執行時機」時，再問第二層：

> 這 N 份複本是否**觀測同一個對象**？

- **觀測同一對象**（如三份都解析同一個 workflow step、同一個常數檔）→ 複本數不產生鑑別力，
  N 份只是同一個盲點的 N 個副本，**應收斂為 SSOT**。鑑別力的真正來源是「錨本身有沒有被鎖」。
- **觀測不同對象**（如 `tools/lib/bash_probe_spec.py` 的三份驗活邏輯各自跑在 bash/PowerShell/Python
  三個 runtime 上）→ 複本彼此是獨立訊號，**保留多份**，靠 parity 鎖維持等價。
  （R57 round 3 Architect 註記：此例其實在**第一層**問句〔跨語言〕即已完成路由，本處僅借其
  「獨立訊號」語意作說明——本 repo 目前**沒有**「同語言、同執行時機、但觀測不同對象」的實例。
  故第二層問句是第一層的細分而非覆蓋；未來若出現真正的同語言實例，應回填取代本例。）

**(2) 收斂的必要配套：SSOT 必配呼叫端鎖。** R57 收斂後，round 1 Architect 實測「把任一呼叫端改回
自寫舊正則 → 全套測試仍 rc=0 全綠」——SSOT 沒有強制力就只是慣例。本 repo 既有先例
（`test_platform_utils_dedup.py`、`test_sanitize_component_callsite_frozen_versions.py`）都配了呼叫端鎖。
**收斂與呼叫端鎖必須同一次落地**，否則是把 N 個弱鎖換成 1 個沒有強制力的弱鎖，嚴格更差。
呼叫端鎖建議走 `ast` 而非文字比對：`ast.parse` 建樹時即丟棄註解、字串字面值也不會變成
`ImportFrom`/`Call` 節點，故「把接線留在註解或字串裡」的繞過在結構上無法成立（R57 實測驗證）。

**(3) 靜態錨「何時算夠好」——比例原則的適用時機。** R57 的錨改了三輪仍被找到逃逸形態：
初版硬綁 `-Path`（位置參數逃逸）→ 加 `.ps1` 尾巴錨（引號 filter／`-Include`／`Join-Path` 逃逸）
→ 加 cmdlet 出現次數錨（`get-childitem` 全小寫／`GCI`／`Dir` 逃逸）→ 加 `re.IGNORECASE`。
這是逐行正則相對於真 PowerShell AST 解析的**結構性天花板**，與 DEF-101-333 對 WindowsApps
parity 鎖家族的裁定同型。判準應在下述時點切換：

> 當連續多輪的新發現都是「**同一結構性成因**的不同表面形態」（此處＝正則不解析 PowerShell 語法），
> 而非新的成因類別時，判準即應從「是否可能被繞過」（永遠是 yes）切換為
> 「**當前投入 vs 已知具體威脅模式是否相稱**」。

R57 的收斂點：三條錨（樹抽取式／`.ps1` 尾巴計數／cmdlet 出現次數）＋ `re.IGNORECASE` ＋
一張**已實測的「不涵蓋」常駐表**（`_KNOWN_UNCOVERED`，未來被涵蓋時翻紅強迫改文件）。
真正的護欄不是「錨抓得到每一種寫法」，而是**誠實揭露抓不到哪些**——故本判例的最後一條是：

**(4) 邊界宣稱必須實測，且不得使用未窮舉的絕對詞。** R57 有兩輪的修復本身就栽在這裡：
round 1 寫「與引號界定全部無關」被 round 2 推翻；round 2 改寫成「唯一殘餘風險是非 cmdlet 途徑」，
又被 `get-childitem`（它就是走 Get-ChildItem）當場推翻。定案寫法為三段式：

> **已實測涵蓋**：（逐項列出，每項都跑過）
> **已實測不涵蓋**：（逐項列出，每項都跑過，並釘成常駐斷言）
> **未窮舉**：明文聲明本清單非窮舉，不做「唯一殘餘風險是 X」這類宣稱。

**本判準的套用範圍（R57 round 3 Architect ARCH-R57R3-04）**：R57 僅將其套用於 `_CI_TREE_RE`
一組。repo 內同族的同語言重複（如 `_FROZEN_SDD_VERSION_RE` + `_exclude_frozen_sdd_versions()`
於 `test_windowsapps_guard_bash_parity.py`／`test_windowsapps_guard_cross_consistency.py` 逐字
相同，另有 `_FROZEN_VERSION_DIR_RE` 兩份變體）**尚未逐一檢視**，列 backlog——**R59 改派**：原寫「列 R58 backlog」，而 R58 整輪經使用者判定失控作廢（`reset --hard 75aab89`），指向一個不存在的輪次＝無承接者。改派為 **R60 起未指派 backlog**；R59 另在此家族新增第 5 份複本（`test_windows_forbidden_filename_parity.py` 的前瞻鎖，見帳本 DEF-101-519／521），收斂時應一併處理五份。寫明此點是為了
避免下一輪讀到本節後誤判「R57 對同語言重複採了兩套標準」。

（本節論證原僅存於 `tools/tests/_ci_scan_anchors.py` docstring，經 R57 round 3 SA 指出
「Scan-E 級論證未回寫判例檔，未來輪 Architect 會讀到 R56 的舊語境而不知已被改判」後搬入正文。
對應帳本 DEF-101-481／494。）

## 使用方式

- 🔴 **三條硬規則（①② R59 新增，源於上表 Scan-F／Scan-G 的成立理由；③ R60 新增，源於 Scan-G G-03 的交棒死信）**：
  1. **每輪必須在當前平台實跑一次入口腳本並記錄結果**（至少：平台 smoke、根層 unittest 全套、
     兩子專案閘門），且**必須確認驗證載具本身有鑑別力**——「綠」或「零輸出」不得直接當成好消息
     （R59 三度踩到載具本身是肇事者，見 DEF-101-520 第二項）。
  2. **任何 `deferred`／`backlog` 必須指向一個存在的輪次或明確標為「未指派」**，且解鎖條件要具體到
     下一輪能直接執行；若延後理由只論證了其中一條修法，須明說還有哪些較便宜的路徑未評估
     （DEF-101-517 即因此被四方一審交叉打回補正）。
     🔴 **本規則目前純靠紀律，尚無機械鎖；若未來要落機械鎖，先避開這個坑**（R59 二審 ARCH-R59-NB4 指出）：缺陷帳本是**逐字保全的歷史檔**，`DEF-101-500` 那列會永遠留著「列 R58 backlog」字樣——本輪刻意（且正確地）沒去改寫它，而是用 `DEF-101-521` 改派。所以規則**不能**寫成「still-deferred 的列不得提及不存在的輪次」，那會讓閘門**永紅**。正確判準是：**狀態仍為 `open`／`deferred` 的列若提及一個 `R\d+` 承接者，該輪號必須 ≥ 當前輪，或該列／有一筆更新的 DEF 條目載明「改派」**——這樣 `DEF-101-500` 因 `521` 存在而合法通過，真正的孤兒才會紅。可行宿主是 `tools/check_defect_log_crossref.py`（已是六道根層閘門之一）。
  3. **跨軌交棒必須有「回執」才算成立**（R60 新增，源於 Scan-G G-03：五筆「交棒他軌」的
     `deferred` 全是死信）。硬規則②只管「指向的輪次存不存在」，不管「交棒到**別的軌**之後
     有沒有人接」——G-03 正是掉進這個縫。判準三條：
     - **容器必須存在且可指名到檔**。R60 實測 `grep -rn "一般 CI 維護" --include=*.md .` 全庫只
       命中缺陷帳本裡那兩列自己 ⇒ `DEF-101-434`／`435` 交棒的「一般 CI 維護缺陷帳本」**根本不存在**。
       禁止寫「記入某某帳本」而該帳本不是一個真實檔案路徑。
     - **容器存在也不等於交棒成立：目標軌帳本必須真的出現對應工作項**。R60 實測
       `AutoClaude/docs/04_planning/` 確有 `AutoClaude_Improving_001~012.md`／`SD_Improving_01~09.md`，
       但 `grep -rn 'DEF-101-422' --include=*.md . | grep -v AutoSDD_Defect_Log` 只命中一行 ADR 的
       佐證引用（不是工作項）⇒ `DEF-101-422`／`470` 指向的是**存在但從未被更新**的容器。
       **交棒的成立條件是目標側有登記，不是來源側有寫「建議交棒」。**
     - **拿不出回執就一律視為「未指派」**（回落到硬規則②），並在帳本列就地寫明改派，
       不得停在「建議由某軌處理」這種無主狀態。R60 對 `DEF-101-422`／`435`／`470` 三列即照此處置。
     🔴 同硬規則②，本條目前**純靠紀律、尚無機械鎖**；要落鎖時同樣要避開「歷史檔逐字保全 ⇒ 舊列
     永遠留著死信字樣 ⇒ 閘門永紅」的坑，正確判準是「該列或一筆更新的 DEF 條目載明改派／回執」。
     立帳見缺陷帳本 DEF-101-555【4】。

- **動工前**：依本輪待辦性質對照上表，決定本輪要跑哪幾維（A~E 通常皆跑，**F／G 為每輪必跑**；Scan-A 兜底發現
  未預期問題，B/C/D 針對性複查已知高風險面，Scan-E 由 Architect 角色複核架構慣例本身是否仍合理）。
- **記帳時**：帳本「發現情境」欄援引維度代號（如「R47 Scan-B」「R53 Scan-B＋Architect-Design」），
  供未來審查員／本文件對照，不需每次重新解釋字母含義。
- **擴充新維度**：若未來出現無法歸入 A/B/C/D/E 任一類的常態性掃描焦點，於本表新增一列並
  同步命名慣例（Scan-F…），不需改動既有五維定義。

## 邊界

本文件只定義「維度是什麼」，不規定「每輪必須怎麼跑」——各輪掃描的深度、工具、觸發時機由
`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 與各輪 prompt 自行決定，本檔不越權。
