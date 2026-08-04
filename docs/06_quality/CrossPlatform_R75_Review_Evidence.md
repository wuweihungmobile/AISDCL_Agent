# 跨平台 R75 輪次報告 — 缺陷詳情（帳本主檔的詳情面）

> **這份檔是什麼**：R75 新立缺陷 `DEF-101-804`～`DEF-101-823` 共 20 筆的**完整詳情面**。帳本主檔（`AutoSDD_Defect_Log.md`）那 20 列已瘦身為「現象一句話 ＋ 關鍵座標 ＋ 嚴重度 ＋ 承接輪次或狀態 ＋ 一句話修法 ＋ 指向本檔的指針」，完整技術結論、實測輸出與注入式鑑別力證據**逐字**保全在本檔對應的 `## <DEF-ID>` 節。
>
> **為何要兩層化**：R75 開場實測帳本主檔 261,642 bytes，距 `DEF-99-001` 政策的輪替硬閘 262,144 bytes 只剩 502 bytes，而本輪還有缺陷列要寫——連一列都寫不下。兩層化沿用 R60（`CrossPlatform_R60_Fix_Evidence.md`）與 R68（`CrossPlatform_R68_Scan_Findings.md`）已立的先例：主檔留摘要與指針，詳情外置。
>
> **本檔已登記為具名治理文件**（`tools/check_defect_log_crossref.py` 的 `_GOVERNANCE_DOCS`，與 `tools/archive_defect_log.py` 綁同一個 tuple 物件）⇒ 同時受**體積守門**（與帳本同一條 <256KB 物理界線）與 `--check` 判準④⑥ 的**指針稽核**。未登記＝兩道守門同時零檢查（`SA-R60R3-01` 的原始路徑）。
>
> **搬移紀律**：本檔每一節的四段皆由帳本原列**逐字**切出，不改寫任何技術結論、不新增任何未驗證的宣稱、不改任何狀態欄首詞。唯一的字面差異在帳本那一側：`DEF-101-813` 原列的 regex 交替字面含未轉義的字面豎線，會把表格欄位切壞（實測 11 切片 ≠ 表頭 9 欄，`row_arity_problems` 與 `archive_defect_log --check` 雙雙 rc=1），瘦身後的帳本列改用全角分隔；**本檔保留原文**。

## 目錄

- [`DEF-101-804`](#def-101-804)（P0）— R75 四方複審（Architect BLOCKING-1）
- [`DEF-101-805`](#def-101-805)（P0）— R75 四方複審（Architect BLOCKING-2 ＋ SA NON-BLOCKING-3）
- [`DEF-101-806`](#def-101-806)（P1）— R75 四方複審（SD BLOCKING-4）
- [`DEF-101-807`](#def-101-807)（P0）— R75 四方複審（Architect BLOCKING-3）
- [`DEF-101-808`](#def-101-808)（P1）— R75 開場實查（帳本體積閘門）＋SA BLOCKING-2／SD BLOCKING-3
- [`DEF-101-809`](#def-101-809)（P2）— R75 四方複審（SA NON-BLOCKING-4）
- [`DEF-101-810`](#def-101-810)（P2）— R75 帳本容量包查證 `DEF-101-652` 交棒殘餘時實查磁碟
- [`DEF-101-811`](#def-101-811)（P2）— R75 帳本容量包執行 `--apply` 時當場撞到
- [`DEF-101-812`](#def-101-812)（P1）— R75 四方複審（SA BLOCKING-1）
- [`DEF-101-813`](#def-101-813)（P2）— R75 四方複審（Architect NON-BLOCKING-1 ＋ SA NON-BLOCKING-5）
- [`DEF-101-814`](#def-101-814)（P2）— R75 四方複審（SA NON-BLOCKING-1）
- [`DEF-101-815`](#def-101-815)（P1）— R75 四方複審（QA BLOCKING-1）
- [`DEF-101-816`](#def-101-816)（P1）— R75 四方複審（SD BLOCKING-1）
- [`DEF-101-817`](#def-101-817)（P1）— R75 四方複審（SD BLOCKING-2 ＋ QA BLOCKING-3／NB-7）
- [`DEF-101-818`](#def-101-818)（P1）— R75 修 DEF-101-817 時副產物揭露
- [`DEF-101-819`](#def-101-819)（P2）— R75 四方複審（SD NON-BLOCKING-6）
- [`DEF-101-820`](#def-101-820)（P1）— R75 修 DEF-101-819 時實測揭露（HEAD 既存）
- [`DEF-101-821`](#def-101-821)（P2）— R75 四方複審（QA NON-BLOCKING-4）
- [`DEF-101-822`](#def-101-822)（P2）— R75 四方複審（QA NON-BLOCKING-5）
- [`DEF-101-823`](#def-101-823)（P1）— R75 四方複審（QA NON-BLOCKING-6）

## DEF-101-804

**發現日期**：2026-08-04　**嚴重度**：P0　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（Architect BLOCKING-1）

### 現象與證據（帳本原文逐字）

**`.sh` 行尾守門把「這台機器何時 checkout」變成閘門結果**：`AutoClaude/tools/hooks/check_sh_eol.py` 判準問「磁碟此刻含不含 CR」，而 `.gitattributes *.sh text eol=lf` 只約束存入、不回頭正規化既有工作樹。實測 tracked `.sh`=168、磁碟含 CR=144（全在 `AISDLC_SDD` v0.01~v0.29 凍結版樹）、**blob 含 CR=0**、`core.autocrlf=true`、`git status` 對 `*.sh` 乾淨 ⇒ 同一 commit 在新 clone 上 0 支被擋、本機 144 支被擋，且唯一能讓閘門變綠的動作（就地改凍結版）正好違反 Copy-on-Evolve。放大成因：R74 把 `PROJECT_ROOT` 上移到 monorepo 根、擴大 deny 射程時**零測試變更**（`git show a371068 --stat` 無該 hook 測試檔），故這批存量從未被量過

### 分流去向（帳本原文逐字）

修法落地本輪（hook 判準 + 測試）

### 狀態（帳本原文逐字）

fixed@R75｜判準改問 index blob（`git show :<path>`）；凍結版樹排除在阻斷面外，LATEST 一律問 SSOT `AISDLC_SDD/scripts/sdd_version.py`（本檔零版本字面，有鎖釘住）；deny 類 hook 全面 fail-open（git 缺席／非 git 樹／LATEST 解析失敗／任何例外 → exit 0）。測試 6→15 支，含本缺陷回歸鎖（blob LF + 磁碟 CRLF → 放行）與凍結／LATEST **成對**測試（單測凍結放行無法分辨「正確排除」與「整棵樹不守了」）；fixture repo 顯式設 `core.autocrlf=false`，否則「blob 真含 CR」對照組做不出來而假綠。端到端真 payload：凍結版 CRLF→rc=0、真 CRLF 未追蹤新檔→rc=2、非 `.sh`→rc=0、tracked 檔暫改 CRLF→rc=0。`pytest tests/tools/hooks/` → 60 passed rc=0

## DEF-101-805

**發現日期**：2026-08-04　**嚴重度**：P0　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（Architect BLOCKING-2 ＋ SA NON-BLOCKING-3 各自獨立命中）

### 現象與證據（帳本原文逐字）

**compat-CI `paths:` 涵蓋鎖有兩種結構性失明，兩支 workflow 皆漏列真被消費的檔而鎖全綠**：形態 G＝`from <套件> import <模組>` 只抓到套件名（`from lib import baseline_origin as BO` → `from=['lib']`），去找 `lib.py` 找不到即**靜默丟棄**；形態 H＝模組層 list literal 內的相對路徑字串（`_LIVE_DOCS`）完全不在掃描面。實測修前 34 passed rc=0 而無法解析數 21、`tools/lib/baseline_origin.py` 與 `defect_ledger_index.py` 在兩支 compat-CI 的 paths 命中皆為 0 ⇒ 只改這些檔的 push 不觸發任一支 compat-CI。`root-infra-ci.yml` 無 paths 過濾恆跑，故純 Python 迴歸仍被 ubuntu 攔下，**逃掉的正是 Windows／macOS 專屬迴歸**（本輪主目標那一面）。這是 DEF-101-042 假綠的第 7、8 種形態

### 分流去向（帳本原文逐字）

修法落地本輪（掃描器 + 兩支 workflow paths）

### 狀態（帳本原文逐字）

fixed@R75｜兩條正則整批換成 `ast` 解析（`ast.Import` 逐 alias、`ast.ImportFrom` 以 `module`＋`alias.name` 組候選，含相對 import `level`）；同源另修兩層結構限制——候選基底由「自身＋父目錄」兩層寫死改為**逐層祖先到 monorepo 根**、BFS 改為累積 sys.path 池跑 fixed point（sys.path 是行程全域量，實測 2 輪收斂）；靜默丟棄升為 fail-loud（唯一可辯護的忽略＝`sys.stdlib_module_names` 機械認定的標準庫與最小第三方名單）。新增形態 H 掃描器（模組層 `ast.List` 內字串 ＋ repo 相對路徑形態過濾；刻意不含模組層 dict/tuple，否則本鎖自己的登記表會逼出假需求）。無法解析 21→0、掃描面 84→113 檔（NEW=29、LOST=0），暴露並補齊 **19 支**漏列檔 × 兩支 workflow × push/PR 共 4 個區塊。有牙性自證：舊 from-import 行為暫時降解 → 8 failed rc=1；形態 H 掃描器暫時停用 → 2 failed rc=1；收尾 47 passed rc=0

## DEF-101-806

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（SD BLOCKING-4 ＋ Dev-A 複驗）

### 現象與證據（帳本原文逐字）

**排程漂移偵測器「缺席」那一向 fail-open，且程式行為與它自己印的字相反**：`AutoClaude/tools/run_local_nightly.ps1` 的 `$schedDriftRc = 0` 起始，`Test-Path $schedDriftScript` 為假時走 else 只印 `跳過：python 或偵測器缺席（無法量測，不當成通過）` 而 `$schedDriftRc` 留在 0 ⇒ 不進 `finalFailures`、nightly 照樣 exit 0。偵測器本體刻意 fail-closed（`tools/check_scheduled_task_drift.py:179`「量不出來不得當成沒問題」rc=1），接線層把它反轉回 fail-open；舊鎖只釘 `-ne 0` 那一向。真會發生的觸發條件：偵測器改名／搬走／`$RepoRoot` 上一層不是 monorepo 根

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜判定改為**白名單式、不看 rc**（缺席那一向根本沒有 rc 可讀，這正是它能靜默通過的機械原因）：`if ($schedDriftStatus -notin @('drift','ok','skip'))` 即計入失敗，`absent`／`unmeasured`／未來任何新狀態字一律計失敗，與偵測器本體同向。新增注入式**行為**鎖（抽真程式碼在 `powershell.exe` 真跑）並**成對**：缺席→必須計失敗／對照組 `status=drift`→不得計失敗（缺對照組時「缺席改成計失敗」很容易被實作成「一律計失敗」＝退回無限期紅燈）。bug-injection 復原病灶原形：`LOG[ERROR] 量不出來，計入本輪失敗` 與 `FINALFAILURES=`（空）同時出現，1 failed rc=1；還原後 72 passed rc=0

## DEF-101-807

**發現日期**：2026-08-04　**嚴重度**：P0　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（Architect BLOCKING-3）

### 現象與證據（帳本原文逐字）

**ADR-XPLAT-002 把 Scan-H 通過判準改成「三元組逐輪登記完整」，而該判準在寫下的當回合即不成立、且無任何機械物**：§4.3.1 登記表只有 R67／R69 兩列，R70~R74 五輪零登記；`git grep '4.3.1' -- tools/tests/` 命中的全是 C1/C2 凍結版判準，無一條驗三元組登記。同一輪對**孿生案例**（§6 逐輪覆蓋表缺列）正確上了機械物 `SC-10`（含注入案例），對這一半只留「承接者＝每輪收尾包」的散文 ⇒ 同一個「缺席型漏做不會轉紅」的病治了一邊、留了一邊，而留下的那邊剛好就是新判準本身。加重情節：該儀式與 §9.1 邊界 (d-2) 直接衝突（要求人製造必然過期的手抄常數），且現存兩組登記的段首都自陳「量測面髒 ⇒ 不得作為新基線」

### 分流去向（帳本原文逐字）

修法落地本輪（ADR 決策 + 機械承接物）

### 狀態（帳本原文逐字）

fixed@R75｜**廢除手抄登記**（選項 b，非補鎖逼人抄），替代判準三款皆可機械檢查、不需 signoff：三元組由機械物**一次取齊**（每跑一次閘門一次，非每輪一次）、UEP 不上升且 AC 不在 UEP 未降時上升（§4.2 判定規則 2 的逐字機械化，permitted 支另有對照組防超譯）、GLC 量測面未崩塌。承接者＝`tools/tests/test_adr_xplat001_c1c2_lock.py::TestScanHTripletIsTheLiveCriterion`（併入既有檔，未新增鎖檔）。**未編造任何一輪的歷史數字**；R70~R74 缺列不補（那是被判為錯方向的選項 a）。實測 93 tests OK rc=0、報表行 `UEP=5 AC=48 GLC_FILES=56 GLC_LINES=50124`；注入 UEP 抬一階 → 恰紅 2 支（含現況判準那支），注入移除承接者名 → 規格↔承接者雙向綁定測試紅

## DEF-101-808

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 開場實查（帳本體積閘門）＋SA BLOCKING-2／SD BLOCKING-3 各自獨立命中

### 現象與證據（帳本原文逐字）

**R74 宣稱「解帳本死結」的 committed 結果比動工前更靠近硬閘，且列數軸從無人記載**：`git cat-file -s` 實測 `82eee92`（R74 動工前）248,048 → `a371068`（R74 收輪）**252,067** bytes，淨增 4,019；R74 commit 訊息宣稱的「233,559 bytes／102 列」是「歸檔搬出、還沒寫本輪帳目」的**中間態**，不是 commit 狀態。同時未結列 **97**／fail 98（距 1 筆），而未結列結構上不可歸檔＝主檔體積的不可壓縮地板，且 R74 交棒書明文禁止搬走 R74 已結列 ⇒ 本輪光是登錄新缺陷就會同時撞兩軸。另 `tools/lib/defect_ledger_index.py` 註解裡的「R74 收輪實測未結 87 列／186,858 bytes、距 fail 11 筆」是假數字，差 10 筆且差在會讓下一個人放心的方向，住在註解裡無鎖看守

### 分流去向（帳本原文逐字）

修法落地本輪（收斂 + 註解訂正 + 禁令撤銷）

### 狀態（帳本原文逐字）

fixed@R75｜逐筆查證後誠實結案 **16 筆**（未結 97→81，皆附當回合複驗指令與 rc；另抽查 4 筆確認仍成立故不結）；訂正註解為實測值。**R74 那條禁令經實測範圍過寬已撤銷**：`current_round()` 取「發現情境」欄最大輪號，而該輪**未結**列結構上不可歸檔、必然留主檔 ⇒ 只搬**已結**列時時鐘不動；實搬 `archive_56`（含 7 筆 R74 已結列）後 `current_round()` 仍 74、crossref rc=0。承接輪次連鎖陷阱亦先做探針：時鐘跳 R75 後原有 2 筆轉紅（`DEF-101-769`／`786`），已分別複驗結案與部分回執＋改派，收斂後 orphan／unpinned／stale 皆 0。存量豁免棘輪順勢收緊 48→36

## DEF-101-809

**發現日期**：2026-08-04　**嚴重度**：P2　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（SA NON-BLOCKING-4）

### 現象與證據（帳本原文逐字）

**R74 交棒任務書三處數字與磁碟不符**：`:65` 稱本輪實配缺陷號 787~802（16 列），磁碟為 787~**803**（17 列，803 為 `partial@R74`，commit 訊息自己也提到它）；`:64` 稱 `partial@R74` 為 6 筆，實為 **7** 筆；`:30`/`:101` 稱帳本停在 250,596，`git cat-file -s a371068:…` 為 **252,067**。交棒書是下一輪唯一的起點依據，三處皆同 commit 可查

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜逐項訂正為當回合實查值。根因是收尾時把「中途量測」當「收輪量測」寫入（同 DEF-101-808 的中間態問題同源）；訂正處寫成因而非抄錄錯誤數字

## DEF-101-810

**發現日期**：2026-08-04　**嚴重度**：P2　**狀態首詞（帳本機械分類的輸入）**：`open`

### 發現情境（帳本原文逐字）

R75 帳本容量包逐筆查證 `DEF-101-652` 的交棒殘餘時實查磁碟

### 現象與證據（帳本原文逐字）

**`AutoClaude/tools/run_local_nightly.ps1` 至今無頂層 `param()`／`-Help` 關卡**：`DEF-101-652` 於 R67 修好 `.sh` 側（`print_usage()` ＋ `case` 關卡）並逐字載明「殘餘且未修：`.ps1` 對等缺口仍在」，解鎖條件寫「有 Windows 真機可實跑驗證的一輪」——R71／R73／R74／R75 皆為 Windows 真機輪，該前提早已具備而工作未做。本包當回合實查該檔：`:88` 為檔頭註解結尾 `#>`、`:90` `$ErrorActionPreference`、`:94` `Set-StrictMode`，第一個 `param(` 在 `:250` 且屬函式內；全檔零 `-Help`／零 `print_usage`／零 `Show-Usage` ⇒ `run_local_nightly.ps1 --help` 會直接開跑 7 stage nightly，與 R67 在 `.sh` 側修掉的缺陷完全同型

### 分流去向（帳本原文逐字）

`AutoClaude/tools/run_local_nightly.ps1`（補頂層 `param()`／`-Help`：`-Help` rc=0 且不執行任何 stage、未知或多餘參數 rc=2）＋回歸鎖比照 `.sh` 側既有的 `AutoClaude/tests/tools/test_run_local_nightly_sh_static.py`

### 狀態（帳本原文逐字）

open（承接輪次：**R76**）｜本列＝`DEF-101-652` 交棒殘餘的**獨立載體**。為何非拆不可：該殘餘自 R67 起以「改派為：未指派」掛在一列 `fixed@R67` 的狀態欄內，而孤兒承接稽核（硬規則②／`orphan_backlog_problems()`）**只掃未結列** ⇒ 已結列的殘留待辦結構上永遠進不去（同 `DEF-101-724` 記載的整類問題）。本輪先立本列，才具名承認 `DEF-101-652` 歸檔

## DEF-101-811

**發現日期**：2026-08-04　**嚴重度**：P2　**狀態首詞（帳本機械分類的輸入）**：`open`

### 發現情境（帳本原文逐字）

R75 帳本容量包執行 `--apply` 時當場撞到（非掃描發現）

### 現象與證據（帳本原文逐字）

**`tools/archive_defect_log.py --apply` 對可搬清單是全有全無、無任何排除入口**：`apply()` 逐字 `move_lines = [v["line"] for v in p["movable"]]`（`tools/archive_defect_log.py:1391`），而 `plan()` 的 `movable` 恆含所有判準①②③⑤⑥ 全過的列；`--ack-handoff` 只能把判準④ 的列**加進**清單，沒有對稱的排除旗標，`argparse` 四個參數（`--archive-num`／`--ack-handoff`／`--note` ＋三選一模式，`:1486`~`:1492`）全無 `--keep`／`--only`。後果：主控下令「本輪新列 `DEF-101-804`／`805`／`806` 不准搬」時工具無合法路徑可遵守——唯一能擋的是判準⑥（外部居所指針），但那要求先在稽核面寫下一句居所宣稱，等於為了操縱閘門而製造宣稱，與該判準「指針居所是可驗證的事實陳述」的立意相反。本輪只能事後把三列逐字還原回主檔、並就地訂正 `archive_57` 標頭的筆數與搬遷清單兩個資料欄（該標頭由 `MOVE_CRITERIA`／`CHECK_CRITERIA` 機械生成的判準散文一字未動，訂正理由已寫入該標頭的操作備註欄，不留靜默落差）

### 分流去向（帳本原文逐字）

`tools/archive_defect_log.py`（建議二擇一：加「發現情境欄輪號 == `current_round()` 的列預設不可搬、要搬須具名旗標」判準，或加 `--keep <ID>` 排除入口；兩者都比事後手工還原可稽核）

### 狀態（帳本原文逐字）

open（承接輪次：**R76**）｜🔴 附帶查證：主控禁令所附的**機械**理由（「R75 列全被搬走會讓時鐘退回 74」）本輪實測**不成立**——`current_round()` 取主檔「發現情境」欄最大輪號，R75 的未結列（`DEF-101-790`／`792`／`795`～`798`／`802`／`803` 等）結構上不可歸檔、必然留在主檔；`DEF-101-808` 已對 R74 的同型禁令做過同一實測並據此撤銷之，本輪搬遷後複跑 `check_defect_log_crossref.py` 亦仍印「當前輪 R75」。故該禁令現存的有效理由只剩「只讀主檔的人要看得到本輪成果」這一條政策面，本包照政策遵守，並把工具側缺口立成本列

## DEF-101-812

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（SA BLOCKING-1）

### 現象與證據（帳本原文逐字）

**R74 的訂正註記被 R74 自己的同一個 commit 弄成假話，而專門看守這件事的鎖結構上抓不到**：`CLAUDE.md` 逐字寫「根 `.claude/settings.json` 只橋接其中 **1 支**」「另外 5 支一行都不會跑」「除 `check_ps1_encoding.py` 外皆僅 AutoClaude 子專案 session」，但 `a371068` 本身就把 `check_sh_eol.py` 橋進根層（實查 `.claude/settings.json:59` 與 `:64` ⇒ 實為 **2 支已橋接、4 支不會跑**）。鎖沒紅的機械原因：`hook_claim_problems()` 是 `if name in settings_text: continue` ⇒ 已註冊即整支跳過，判準為 OR（已註冊 **或** 該行標子專案射程），於是「**已註冊 且 該行說它不會跑**」這個組合**恆綠**。連鎖：`DEF-101-798` 的解鎖條件建立在同一個假基線上（寫「未橋接的 5 支」）

### 分流去向（帳本原文逐字）

修法落地本輪（文件 + 反向判準 + 下游解鎖條件）

### 狀態（帳本原文逐字）

fixed@R75｜`CLAUDE.md` 改為 2 支／4 支，並**把已橋接的 hook 名稱與「僅 AutoClaude 子專案 session」字樣拆到不同行**——讓逐行 substring 判準結構上判得準，而不是把判準寫鬆。`hook_claim_problems()` 補反向判準：已註冊於根 settings.json 者若被任一行標成不會跑＝同樣違規；既有「已註冊者不必加註記」語意保留。`DEF-101-798` 解鎖條件同步訂正為「未橋接的 **4** 支（`enforce_docs_path`／`loc_budget_check`／`check_lang`／`claude_md_freshness`）」。注入式鑑別力：合成「已註冊 hook 被標成僅子專案」文字 → 舊判準綠、新判準紅（同一輸入餵修前／修後兩版，非宣稱）

## DEF-101-813

**發現日期**：2026-08-04　**嚴重度**：P2　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（Architect NON-BLOCKING-1 ＋ SA NON-BLOCKING-5）

### 現象與證據（帳本原文逐字）

**五筆幽靈機械物指標：文件與註解宣稱的鎖不存在或守的是別的東西，而看守它的鎖只圈一格**。`tools/scheduled_task_expectations.json` 稱由 `tools/tests/test_scheduled_task_expectations.py` 機械釘住（該檔不存在，真鎖在 `test_install_windows_nightly.py::TestScheduledTaskExpectationsSsot`）；`tools/archive_defect_log.py` 與 `tools/check_defect_log_crossref.py` 皆稱 `test_defect_log_capacity_policy_r68.py`（不存在，真類別住 `test_archive_defect_log.py`）；`CLAUDE.md` 把 `install_windows_nightly.ps1` 寫在 `AutoClaude/tools/` 而實際在根層。最難看的第五筆是**實質**假機械物：鐵律三「行尾」列指 `test_ps1_bom.py`，該檔對 `crlf|\r\n|eol` **零命中**（6 支全在驗 BOM），真正會因 CRLF `.sh` 轉紅的是 `test_pre_commit_dispatcher_sigpipe.py::TestPreCommitBlocksCrOnShellScripts`。逃逸原因：原鎖正則只掃**根 CLAUDE.md**、只認反引號 `.py`、且只斷言**檔案存在**

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜五筆指標全部改指真鎖（含類別名）。鎖擴三面：掃描面加 `tools/*.py` 與 `tools/*.json` 內帶「機械鎖／機械釘」的行；副檔名擴到 py／ps1／sh／json 四種；新增**實質判準**（主題關鍵詞佐證 ＋ `::Symbol` 必須真是該檔的 class/def）。五種形態各有注入式鑑別力（舊綠新紅）：`tools/*.py` 註解面、`.ps1` 副檔名、`.json` 面、`::Symbol` 不存在、守錯主題

## DEF-101-814

**發現日期**：2026-08-04　**嚴重度**：P2　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（SA NON-BLOCKING-1）

### 現象與證據（帳本原文逐字）

**ONBOARDING §7 表① 的 `skipped` 與同 commit 實測打架，且逐項清單零機械記帳**：該格寫「1819 tests OK（`skipped=10`）」並逐項展開「Windows 的 10 支全為 POSIX-only 或 macOS-only 語意：8 支 pgid/killpg/SIGINT…」，而同 commit 訊息與交棒書皆為 `skipped=43`。受鎖 token `1819` 被 sync 工具更新了，`skipped=10` 與其後的清單沒有——ONBOARDING 明載「`skipped=N` 刻意不在鎖內」⇒ 結構上無人看守，本輪淨增約 33 筆 skip 零察覺

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜自跑取權威值（`Ran 1819 tests in 296.104s`／`skipped=43`）並改為 `skipped=43（量測時點 2026-08-04）`；**手寫逐項清單整段移除**，改指唯一權威＝每次閘門執行由 `report_all_skips` 逐支印出的現場輸出，並寫明「靜態站點 ≠ 測試支數」（實測 11 站點 ↔ 32 支已標籤 skip，差 3 倍，不可互代）。設計裁決：**不**做成 live 鎖，三條理由寫進 code（跑在套件裡的測試不可能知道自己這次的最終 skip 數／skip 數依機器而變＝硬相等就是假紅／靜態站點差 3 倍），改鎖**可稽核性**（必須存在、必須帶日期、必須指向 live 來源），零假紅面。收尾時另自行刪掉一段剛寫下的「已標籤 32／未標籤 11」附註——因為標籤體系一改組成就變而無人核對，那是剛移除的手寫清單的縮小版

## DEF-101-815

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（QA BLOCKING-1）

### 現象與證據（帳本原文逐字）

**R74 新建的「雲端 CI 結論」錨從不驗證 `head-sha`，新鮮度只到日粒度 ⇒ 它要防的那件事（雲端結論落後一輪）結構上抓不到**：判準只檢查欄位**存在**，把 `head-sha` 換成全零仍全綠；錨現值指向 `82eee92`（R73 收輪 commit）且記 `red=windows-compat-ci.yml`，而 HEAD 是 `a371068`、那支已修綠 ⇒ 本輪自己的 commit 上，表③ 記載的雲端結論屬於上一個 commit。全庫搜尋 `head-sha` 除該測試檔外**無任何生產碼消費**。第二層：`checked-at` 與 `measured-at` 都只有日期，而本 repo 一輪常在同日完成（`82eee92` 01:48 → `a371068` 09:57）⇒「動了本機基線就得重查雲端」這條因果判準在一輪之內不可能觸發

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜新增 5 條判準＋回填 SOP：sha 形態（40 位小寫 hex、非全同字元，純字串零環境相依）／必須解析得出 commit 物件／必須是 HEAD 或其祖先／`checked-at` 不得早於該 commit 提交時間（同日內有效）＋只寫到日就必須自陳 `granularity=day`／錨的 `red=` 必須逐字等於表格 failure 列集合（比內容不比日期）。shallow clone／無 git 下**明說未驗證而不判紅**（`actions/checkout` 預設 depth=1，硬判會製造環境相關假紅）。5 筆注入式鑑別力舊綠新紅（全零 sha／短 sha／形態合法但 repo 無此 commit／同日內結論早於它所評的 commit／表格 failure 而錨沒跟上）。誠實劃界：「錨落後 HEAD 一個 commit」刻意不判 rc 紅（會在「commit 後、重查前」永久紅 ⇒ 養成忽略紅燈），正確歸宿是 pre-push

## DEF-101-816

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（SD BLOCKING-1）

### 現象與證據（帳本原文逐字）

**排程漂移偵測器對「任務整支不存在」結構性失明——一支缺席、另一支設定完美時回 `status=ok`／rc=0，同時照實印出「不存在」**：`tools/check_scheduled_task_drift.py` 的狀態格只登記兩格（全缺席＝skip、存在但設定不符＝drift），「**部分存在**」這一格沒判準沒測試（既有 `test_absent_tasks_are_skip_not_drift` 只覆蓋全缺席，剛好繞過）。判準與被判準物錯配：偵測器要守的是「排程會不會漏跑」，而「任務不見了」是漏跑的最強形態，卻是它唯一看不到的形態——且該事件類真的發生過（R71 從本機移除過一支 `AutoClaude*` 任務）

### 分流去向（帳本原文逐字）

修法落地本輪（偵測器 + nightly 接線 + 測試）

### 狀態（帳本原文逐字）

fixed@R75｜新增狀態字 `task_missing`（rc=1），**刻意不折進 `drift`**：`drift` 在 nightly 接線層有一條具名豁免（DEF-101-794 五項設定要提權才能改，只 WARN 不計失敗），而「任務不見了」的修法不需等提權，搭那條便車＝把最強的漏跑訊號從 exit code 上拿掉。接線層本輪已改白名單 fail-closed（`-notin @('drift','ok','skip')`）⇒ 新狀態字自動落在計失敗側；另補專屬分支與標籤 `schedule_drift_task_missing`，避免它先撞上「讀不出 status」那句誤導訊息。人類可讀輸出訂正：缺席行原本在 rc=0 與 rc=1 兩種相反結論下都印同一句「不存在（未安裝）」，現在會說出結論。「全缺席＝skip」維持預設（該格在自動偵測上本來就沒有證據能分辨「從沒裝過」與「兩支都被移除」，判紅會讓 CI runner 與 fresh clone 永久紅），改以新旗標 `--require-installed` 讓知道自己該有排程的機器顯式關閉缺口，而非只劃界結案。注入式：關掉部分缺席分支 → 3 支翻紅；非 Windows 仍 rc=0 且不呼叫排程 API（DEF-101-766 不回歸）

## DEF-101-817

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（SD BLOCKING-2 ＋ QA BLOCKING-3 ＋ QA NON-BLOCKING-7 三筆同一閘門）

### 現象與證據（帳本原文逐字）

**AC4 觀察期的解鎖判準有三個獨立缺口，合起來使該閘門幾乎沒有鑑別力**：① staleness 量的是「最後一筆**紀錄**」而非「最後一筆**真量測**」——PG/Docker 不可用時採集器每晚仍寫入帶當日 timestamp 的 `status="skip"`，而 skip 對 `green_streak` 中性、對 staleness 卻算新列 ⇒ streak 凍結＋staleness 恆 1 ⇒ **`ready` 永久凍結**（合成歷史實測：14 綠＋其後 120 晚全 skip → `ready=True`、`reasons=[]`，而最後一筆真量測已 287 天前）。這正是 L-7 立判準時逐字要防的狀態，原判準只堵住「沒有新列」那一半，而「列有來但全是 skip」才是常態失敗模式。② 反漂移判準 `recall σ ≤ 0.02` 的輸入在全史裡是同一個常數（44 筆 `recall_at_10` 全為 0.999），而 `gate_basis=green_streak` 又由吃 recall 的 `_is_green` 決定 ⇒ 唯一閘門的一半輸入是常數；輸出只印 `σ=0.0` 與 `reasons=[]`，讀起來像毫無保留達標，且 `observation_streak` 極低（50ms 觀察軌幾乎全未達標，`ready` 由 60ms tolerant 軌成立）這件事完全不可見。③ `staleness_days = max(0, (now - latest_ts).days)` 對未來時間戳 fail-open ⇒ 時鐘偏移或任何一筆未來 timestamp 就永久新鮮

### 分流去向（帳本原文逐字）

修法落地本輪（判準 + 可見性 + 測試 fixture）

### 狀態（帳本原文逐字）

fixed@R75｜① staleness 改量最後一筆真量測（新述詞 `_is_measurement`＝`status != "skip"`）；`all_true_skip` 豁免以同一述詞重新表述，保留「還沒有任何真量測就不罰」但不讓「曾經有真量測、後來全 skip」搭便車（兩者現在互斥，順序風險消失）；新增 `measured_records`／`record_staleness_days`，兩者落差即診斷依據（採集器死了 → 修排程；採集器活著只寫 skip → 修 PG/Docker）。② **不同意「σ 零鑑別力」的框架並分兩層處置**：σ 讀 0 在確定性指標上是正確讀數（recall 對固定語料＋固定索引是確定性量測，鑑別力是**前瞻的**——recall 掉到 0.96 仍過 `≥0.95` 但 σ 會跳到 ~0.02 而攔下），故判準內容不改，改為把「這次讀 0 是因為沒變、不是因為驗過了」印出來（新增 `recall_distinct_values`／`p95_distinct_values`／`metric_variance_observed`／`recall_sigma_discriminating`，以及與 `reasons` 分離的 `caveats`——有 reasons 就不 ready，有 caveats 是 ready 但別讀成毫無保留）；真正的缺口另立一條**收緊**條件：認證時窗內至少要有一個指標出現過變異，否則不 ready（擋 stuck writer／每晚複製上一筆，與 skip 凍結同族的 liveness 假綠）。③ 負值不再夾成 0，改報 `clock_anomaly` 並 fail-closed，反向鎖確認正常歷史不得誤報。四筆各有位元組層注入即紅（跑完 write_bytes 還原並比對 sha）。🔴 **修正全部判準後以真實歷史複跑仍為 `ready`**（44 筆全為真量測、`measured_records=44/44`、最新一筆為當日）⇒ R74 的達標宣稱站得住，凍結缺陷是**潛伏**的而非正在掩蓋假達標

## DEF-101-818

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 修 DEF-101-817 時副產物揭露（鎖在守假事實）

### 現象與證據（帳本原文逐字）

**11 支既有 AC4 測試在斷言「窗內 14 筆一模一樣的指標值 → ready=True」＝fixture 複製了 production 的盲點，於是那些鎖鎖住了那個盲點**。落地 DEF-101-817 的「零變異即不得認證」收緊條件時，這 11 支當場翻紅——它們紅的原因不是新判準錯，而是它們原本就在把「沒有重新量測」寫成「已驗證通過」

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜11 支 fixture 全部改為帶確定性抖動（`+ d*0.01`，值域不跨任何門檻、各 case 原受測對象不變），並在兩份測試檔頭立下 fixture 慣例（合成歷史不得使用全等指標值，否則會複製 liveness 盲點）。這一筆的價值在形態本身：**注入式鑑別力驗的是「判準會不會紅」，驗不出「fixture 是否在餵一個不可能發生的世界」**——後者只有在收緊判準時才會現身

## DEF-101-819

**發現日期**：2026-08-04　**嚴重度**：P2　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（SD NON-BLOCKING-6）

### 現象與證據（帳本原文逐字）

**「CLI 工具必須拒收未知旗標」這條紀律的鎖以檔名 glob 劃界（`glob("check_*.py")`），使 pre-push root-infra leg ＋三支 CI 唯一真正執行的那一支逃逸**：`tools/run_root_unittests.py` 全檔對 argv／argparse／`_cli_flags` 三者皆零命中，帶未知旗標時不拒收而直接跑完整棵樹（實測 rc=1，反映的是套件結果而非旗標拒收）。同一輪對照組四支非 `check_*` 工具皆正確 rc=2 ⇒ 缺口幾乎補齊，只剩後果最大的這一支，而它逃掉的原因純粹是檔名

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜① 該檔新增 `cli(argv)` 一層：先 `reject_unknown_argv()`、合法才進 `main()`，`main()` 一行未動且完全不讀 `sys.argv`。**這個分層是必要而非風格**——若把拒收寫進 `main(argv=None)→sys.argv[1:]`（其餘四支消費者的寫法），零相依探針在子行程內叩 `main()` 時 `sys.argv` 裝的是探針自己的參數，會回 rc=2 而非它斷言的 rc=1 ⇒ **一道真鎖當場變假紅**。② 射程判準改為行為級：`tools/*.py` 中帶 `if __name__ == "__main__"` 者（3 支無 guard 自動落在射程外）。🔴 刻意**不**加「而且要讀 `sys.argv`」這個條件——不讀 `sys.argv` 正是「靜默吞掉」的實作方式，拿它當射程條件會自動豁免每一支還沒修的工具，就是同一個洞換個地方；射程條件必須與「有沒有病」正交。③ `_offenders` 把逾時也算 offender（原本會拋 `TimeoutExpired` 變 error 而非 fail，修前的那支正好會撞這條）。實測：擴射程後新暴露違規 **0**（新納入 9 支裡 8 支早已拒收）；`--no-such-flag` → rc=2、**71 ms** 秒回（非跑完整套才回）；注入「射程退回檔名 glob」→ 2 支紅、注入「`main()` 含 `sys.argv`」→ 1 支紅

## DEF-101-820

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`routed`

### 發現情境（帳本原文逐字）

R75 修 DEF-101-819 時實測揭露（HEAD 既存，非本輪造成）

### 現象與證據（帳本原文逐字）

**`reject_unknown_argv` 對「以 `python -m unittest <模組>` 載入」誤傷，使四支閘門工具的鎖在該載具下變成假紅**：`main(argv=None) → sys.argv[1:]` 的寫法在被 unittest 以模組名載入時，`sys.argv` 裡是**模組名**，被當成未知旗標拒收。實測 `python -m unittest tools.tests.test_gha_action_versions` → `Ran 14 / FAILED (failures=3)`，清掉 `sys.argv` 後 14/14 OK。受影響：`check_wrapper_thinness`／`check_script_parity`／`check_pytest_baseline_sites`／`check_gha_action_versions`。這條在閘門路徑（`sys.argv[1:]==[]`）不會紅，所以七輪無人發現

### 分流去向（帳本原文逐字）

承接輪次：**R75**（同輪處置，見狀態）

### 狀態（帳本原文逐字）

routed（R75 內處置中）— 解鎖條件＝四支統一改為 `cli`/`main` 分層（`sys.argv` 只在 `__main__` 專屬層讀），且 `python -m unittest <模組>` 形態必須 14/14 OK、四支真實 CLI 拒收行為不得退化（各餵 `--bogus-flag-xyz` 仍須 rc=2 秒回）。🔴 **repo 內兩種修法並存需拍板不得混用**（Rule 7）：①`cli`/`main` 分層（先例 `check_defect_log_crossref.py`、本輪 `run_root_unittests.py`）②測試端顯式傳 `[]`（先例 `test_check_wrapper_thinness.py`）。已判 ① 優於 ②，理由寫進 `tools/_cli_flags.py` 檔頭

## DEF-101-821

**發現日期**：2026-08-04　**嚴重度**：P2　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（QA NON-BLOCKING-4）

### 現象與證據（帳本原文逐字）

**subprocess 編碼衛生鎖的 per-tree 檔數下限已腐化，容許掃描面靜默蒸發近八成仍全綠**：`tools` 樹實測 files=81 而 floor=18（slack=63），而下限存在的唯一理由就是「掃描面靜默縮小必紅」。根因＝下限是 2026-07-19 首掃數打八折的化石，樹會長大、下限不會；根層 `tools` 正是 R74 新增檔案最多的樹。同一算法產生的 `_CHILD_SITE_FLOOR`（pinned=20 vs 實測 26）只是還沒漂夠久

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜11 棵樹下限全部重釘到當回合實測 × 0.95（守住比例 22% → 95%），並新增**雙邊帶**防腐（新純函式 `tree_count_verdict`／`repin_ceiling`／`suggested_floor`）：低於下限＝縮面（原意）；高於 `max(floor+10, floor×1.25)`＝**下限自己過時，當場紅並在訊息裡印出該填的數字**。餘裕取法寫進註解（5% 縮水容差＝容許少量合併／刪除；25%＋絕對 10 檔成長容差＝一輪正常增檔不用重釘、累積數輪必被逼重釘）。同一條帶亦套用於 `_CHILD_SITE_FLOOR`。刻意不外接基線同步器：那條路要動別人的檔，而它治的是「數字要跟著實測走」，本缺陷治的是「數字**可以**不跟著實測走多遠」，只需一個就地可判的上界。注入即紅：直接把腐化狀態當 fixture（`tree_count_verdict("tools", 81, 18)` 必須非 None 且訊息含該重釘的數字）

## DEF-101-822

**發現日期**：2026-08-04　**嚴重度**：P2　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（QA NON-BLOCKING-5）

### 現象與證據（帳本原文逐字）

**`has_utf8_stdio_protection` 是整檔子字串比對，一行註解就能滿足判準**：child 檔內只要出現 `.reconfigure(encoding=`／`import _stdio_utf8`／`init_utf8_streams` 字樣（含註解、docstring、被註解掉的程式碼）即視為有保護。以 tokenize 塗白 COMMENT/STRING 後複算 14 支納管 child，14/14 命中皆落在真實程式碼 ⇒ **無現存假綠、屬潛在缺口**。加重情節：同檔另一道判準（`_marker_lines`）早就只認 COMMENT token，同一份謹慎沒有套過來

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜新增 `code_only()`：以 tokenize 把 COMMENT／STRING（含 3.12+ FSTRING_* 分段）**等寬塗白**（行號欄位皆不位移），判準改在塗白後的原始碼上比對；tokenize 失敗＝視為無保護（方向選紅不選綠）。`is_entry_point()` 刻意**不**塗白並就地寫明理由（它的比對樣本自己含字串字面 `"__main__"`，塗白後會恆假；且過度納管的方向偏紅不假綠）——不是默默略過。注入即紅：四種形態（行註解／docstring／被註解掉的程式碼／字串常數）內的保護字樣皆須判為無保護；塗白對真實 repo 零行為變動（offenders 0→0）

## DEF-101-823

**發現日期**：2026-08-04　**嚴重度**：P1　**狀態首詞（帳本機械分類的輸入）**：`fixed@R75`

### 發現情境（帳本原文逐字）

R75 四方複審（QA NON-BLOCKING-6）

### 現象與證據（帳本原文逐字）

**R74 那筆 P0（hook 中文指引在非 CJK codepage 降解）的回歸鎖覆蓋到該 hook 是「順便的」，production 呼叫形態被判準明文排除在外**：child 編碼判準對 `-m`／`-c` 形態 `break` 不納管，而 production 走 `python -c "…runpy.run_path(p)…"`（`.claude/settings.json`）。該 hook 之所以進入判準射程，**唯一原因**是一支測試碰巧用 `[sys.executable, str(_HOOK)]` 直接執行形態起它。突變實測：把那一行改成 production 的 `-c`+runpy 形態 → 判準二 `in_scope` 27→26、該 hook **進射程次數 1→0**，P0 的判準靜默失去這個站點。另一半：`.claude/settings.json` 的 `env.PYTHONUTF8=1` 被測試註記逐字指名為「本機唯一 UTF-8 來源」，卻**零鎖看守**（刪掉全庫全綠、P0 靜默復發）。同型前例＝DEF-76-001（載具只認棄用路徑的 marker，production 不印，真跑恆 0）

### 分流去向（帳本原文逐字）

修法落地本輪

### 狀態（帳本原文逐字）

fixed@R75｜① 新增判準四：把 `.claude/settings.json` 的 **hook 註冊表自己**當掃描面，撈出 `python -c "…runpy.run_path(p)…" <script>` 形態的腳本路徑並要求 UTF-8 stdio 保護（實測納管 4 支、全部已有保護；「註冊了卻不存在的腳本」另列 fail-loud），並具名斷言 R74 P0 那支 hook 必須經此進入射程——突變後判準二失去該站點時，判準四仍罩住（實測 4 tests OK）。② 為 `env.PYTHONUTF8=1` 補鎖，並修掉那段「指名關鍵依賴卻不給它鎖」的註記。🔴 `.claude/settings.json` **一個字未動**（該檔自載「hook 誤觸 deny 會把所有工具硬鎖死」的 P0）：連「拿掉 `env.PYTHONUTF8` 看會不會紅」都走記憶體注入（讀真實檔內容後 pop 該鍵），證明力相同而風險為零。端到端 P0 非降解實證：以 settings.json 逐字取出的 production command ＋ `PYTHONIOENCODING=cp1252` ＋剝 `PYTHONUTF8` → 中文指引完整、無 uXXXX 逃脫；剝掉保護的合成副本則中文消失、逃脫出現（證載具有鑑別力）

