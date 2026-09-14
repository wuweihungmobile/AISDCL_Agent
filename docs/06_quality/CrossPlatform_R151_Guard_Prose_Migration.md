# CrossPlatform R151 — 護欄層散文搬遷證據檔（Dev-Trim Trim-B）

本檔是 R151 守衛線搬遷抵銷包（Dev-Trim Trim-B）的**逐字保全**落點：`tools/tests/` 五支持有檔
（`test_doc_loc_baseline_freshness_r60.py`／`test_block_destructive_git_r83.py`／
`test_check_defect_log_crossref.py`／`test_context_budget_guard.py`／
`test_ntfs_trailing_space_device_name.py`）內的歷史沿革敘事（「當年為什麼這樣改／
哪一輪誰抓到什麼／前值序列／事故重演敘事」）自程式碼搬出，原處只留一行指標。判準、
斷言、常數值、字串字面、豁免 token 一律**未動**；每段被裁減的 docstring／註解一律保留
其第一句（測什麼／為何）。

體例沿用 R122／R127 的先例：以 `## <檔名>` / `### <原本掛在哪個符號上>` 分節，節內以
fenced block 逐字保全原文（含縮排）。搬遷不改變任何判準的射程；被搬走的文字若日後需要
回頭閱讀，循原處指標行找回本節。

🔴 各節「原處：… L<a>-<b>」記的是**搬遷前**（本包動工前）的行號；本包同一檔內有多處
搬遷，後一處的搬遷會讓前面已搬遷處之後的行號整體上移，故本檔一律記**搬遷前**的座標，
要找回原處請以該節標題點名的符號（函式／類別名）定位，不要用行號。

指標行刻意寫**裸檔名**「CrossPlatform_R151_Guard_Prose_Migration.md」，不帶
`docs/06_quality/` 前綴——帶前綴的字面會被 `tools/lib/guard_bucket_policy.py` 的分桶
判準算進 `prose` 桶 token，讓原本不掛散文樹的塊被誤歸類，抵銷本包想同時壓低的兩把棘輪。

## test_ntfs_trailing_space_device_name.py

### 模組 docstring：R57／R67 缺陷沿革與各軸立案敘事

原處：`tools/tests/test_ntfs_trailing_space_device_name.py` L1-59（模組 docstring 主體）

```text
R57 回歸鎖：Windows 保留裝置名「保留名 + 尾隨空白 + 副檔名」形態不得逃逸。

缺陷（R57 掃描 B1）：`tools/check_ntfs_paths.py` 與 `tools/git-hooks/pre-commit`
的 `_ntfs_seg_bad()` 都以「切到第一個點」取 base 後直接比對保留名清單——
`CON .txt` 的 base 是 `"CON "`（帶尾隨空白），`^(CON|...)$` / case pattern `CON`
皆不匹配；而「整段以空白或句點結尾」那一條只看整段（`CON .txt` 結尾是 `t`）也
不成立 → 兩道判準之間漏出一個縫，`CON .txt`／`NUL .log`／`LPT1 .yaml` 全數放行。
Windows 實情：Win32 解析裝置名時會忽略基底名後的尾隨空白，此形態在 Windows
checkout 仍會撞到裝置名。

本檔只鎖 monorepo 根層兩處實作（Python CI 版 + bash hook 版）的**行為對等**。
同一缺陷形態另存在於兩處，**R57 主控收尾時已一併修復並各自設鎖**：
`AutoClaude/autoclaude/utils/logger.py._sanitize_log_filename`（第三方，鎖在
`test_windows_forbidden_filename_parity.py::TestTrailingSpaceReservedNameCrossConsistency`）
與 `AISDLC_SDD/scripts/component_sanitizer.py.sanitize_component`（第四處，屬子專案
邊界不可跨界 import，鎖在 `AISDLC_SDD/scripts/tests/
test_component_sanitizer_reserved_trailing_space.py`）。四處成因相同：都是
`rstrip(" .")` 作用於整串、之後才 `split(".", 1)[0]`，故 `CON .txt` 的 stem 皆為 `"CON "`。

────────────────────────────────────────────────────────────────────────────
## R67 併入：目錄段大小寫碰撞（A2）／文件引用大小寫（A15）／Unicode NFC 正規化（B16）

**為何併進本檔而不另開一支**：`tools/tests/` 有一道護欄層棘輪
（`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet`，機械承載
DEF-101-561③／DEF-101-565 的架構級裁決）——R67 當時它量的是**檔數**，語意是
「R61 開輪即禁止新增鎖檔、只准合併／刪除」（🔴 R78 ARCH-03 訂正：R77 起改量逐檔行數的
**淨額**，新增檔案只要同一次變更刪掉等量以上的行就合法；下段是 R67 當時的實錄），
理由是護欄層已比它所護的生產碼還大。R67 初版確實另開了一支獨立鎖檔
（`test_path_segment_case_and_nfc_collision.py`），**當場被該棘輪擋下**；依其明示的合法作法
（「把新判準擴充進既有鎖檔」）改為併入本檔。本檔是最貼近的宿主：它既有的職責就是
「monorepo 根層兩處 NTFS 實作（Python CI 版 + bash hook 版）的行為對等」，
R67 三軸全部落在同兩處實作上。**檔名比內容窄是刻意承受的代價**（改名屬另一種變更、
且會打斷既有引用），讀者請以本段為準。

### R67-A2 — 目錄段層級碰撞
`check_ntfs_paths.py` 的碰撞檢查用**整條路徑**做分群鍵、`pre-commit` 的 A3 閘用
`grep -iFx` 做**整行**比對，兩者對「目錄段拼法不同、basename 完全不重複」結構上失明。
本 repo 就是這樣長出 `docs/04_planning/{Archive,archive}/` 與
`docs/06_quality/{Archive,archive}/` 兩對 index 目錄並靜默共存 6 週
（`f81ad94` 用大寫收 improving_01–31、`22782fe` 改小寫收 32–50）。
mac(APFS)／Win(NTFS) 上兩拼法**塌縮成同一個磁碟目錄**、`git status` 全綠＝本機零訊號；
同一 commit 在 Linux CI／github.com 上卻是**兩個獨立目錄**（R67 以 `hdiutil` 建
case-sensitive APFS 卷實測坐實）。危害不是立即覆蓋（basename 不重疊時不會），而是
**同一份程式碼在兩平台掃到不同的檔案集合**，以及交叉引用在 Linux 變死連結。

### R67-A15 — 文件交叉引用大小寫
上述漂移的第一個已實體化症狀：3 處文件把 improving_39 的出處寫成
`docs/04_planning/Archive/AutoSDD_improving_39.md`，而該檔當時實住小寫 `archive/`。
R67 的修法是**收斂目錄拼法為大寫 `Archive/`**（全 repo 外部引用清一色用大寫、兩支
`README.md` 也住大寫側），使這 3 處原地變正確——**一個字都不用改**，因而不必改寫
逐字保全的歷史歸檔帳本 `docs/06_quality/AutoSDD_Defect_Log_archive_02.md`。

### R67-B16 — Unicode NFC 正規化
整組檔名衛生鎖的設計標的清一色是「Windows/NTFS 簽出會不會炸」，沒有一項守
「macOS 簽出會不會炸」。macOS(APFS/HFS+) 對檔名做 NFD、Windows(NTFS) 用 NFC，
git 以 `core.precomposeunicode` 在 macOS readdir 端轉回 NFC；一旦 index 內存的是 NFD
位元組，macOS clone 後該檔即永久呈現「index 一份 NFD、工作樹一份 NFC 未追蹤」的雙重
身影：`git status` 恆不乾淨，且 `git clean -fd` 清掉 phantom 會直接變成 tracked 檔遺失
（兩種不乾淨狀態互斥，無常規手段回到乾淨——R67 實測）。
```

### TestNfcAxisScopeIsCiOnlyByDesign：範圍決策沿革與實測依據

原處：`tools/tests/test_ntfs_trailing_space_device_name.py` L306-319（class docstring）

```text
這條的鑑別力方向是**反向**的（斷言「hook 不該有」而非「必須有」），理由與
`test_ntfs_trailing_space_device_name.py` 的前導空白鎖同型：本 repo 的守門慣例是
「hook 與 CI 版行為對等」，故下一輪掃描者看到「CI 有六項、hook 只有五項」時，
幾乎必然會把它當成缺口而「補齊對稱性」。實測結論是補了等於加死碼——

  · macOS 端 `git add` 走 argv 有 `precompose_argv`、走目錄走訪有 readdir
    precompose（R67 實測：磁碟 NFD 檔名 `63616665cc812e6d64` 經 `git add .`
    後 index 記為 NFC `636166c3a92e6d64`）；
  · Windows/NTFS 本身即 NFC。

⇒ NFD index 項只能由 Linux 貢獻者／GitHub web／plumbing 進來，**那三條路都不經過
pre-commit**；而它們全都會被 CI 版的全量 tracked 掃描網住。
```

## test_doc_loc_baseline_freshness_r60.py

### hook_claim_problems：為何非補②不可（R75）＋ 同一通行證換皮復活（R76）

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L2798-2817（docstring 內兩段）

```text
    🔴 為何非補 ② 不可（本函式自己放行過一次假事實）：原判準是 OR——「已註冊 **或**
    該行標明子專案射程」，於是 `if name in settings_text: continue` 讓「已註冊」單獨
    成為免檢通行證，**完全不看那些行實際寫了什麼**。實況：`a371068` 這個 commit 的
    一個包把 `check_sh_eol.py` 橋進根 `.claude/settings.json`，同一個 commit 的訂正文
    卻仍把它算在「不會跑」那一組並連帶少報了橋接支數 ⇒ 假事實在寫下的當回合就成立，
    而這道鎖結構上恆綠（實跑當時 4 tests 全 ok、rc=0）。

    ②「一行都不得」而非「主要那行不得」是刻意的：這個字樣的語意是絕對的（「這支在根
    session 不會跑」），一支會跑的 hook 沒有任何語境能讓那句話變成真的。副作用是文件
    必須把「已橋接清單」與「未橋接清單」**分行寫**——那不是本判準的成本，而是它要的
    結構：兩組事實混在同一行時，逐行 substring 判準對任何一組都判不準。

    🔴 **R76 訂正（同一個通行證換皮復活）**：「已註冊」的判定原本是
    `if name in settings_text:`——拿**整份 settings.json 的文字**做 substring。於是
    該檔任何角落提到過的名字（`_comment`／`_why` 敘述、被註解掉的舊 wiring、`matcher`
    說明裡順口舉的例）都算「已註冊」而讓那支 hook **整支免檢**；把真 wiring 拔掉、
    只留一句註解，根 CLAUDE.md 那句「已橋接 N 支」就成了假話而零訊號。R75 才剛拆掉
    OR 型通行證（見上方 ②），這裡是同一個病的第二個住所：**判定「有沒有」時，掃描面
    必須是解析出來的結構，不是整檔文字。**
```

### `_SKIPPED_CELL_RE` 上方：R75 訂正的缺陷本體與三理由

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4759-4769（區段旗標下的註解）

```text
🔴 缺陷本體：該格的受鎖 token 只有「N tests OK」（見 `SYNC._SPECS`），`skipped=N` 與
**其後的逐項清單**明文不在鎖內。後果實測：受鎖 token 每輪被產生器更新，而 `skipped=N`
與那份手寫清單自寫下之後從未被核對過；本輪淨增約 33 筆 skip，零機械記帳。

🔴 為何**不**把那個數字本身做成 live 鎖（誠實的設計裁決，不是偷懶）：
  ① 結構性不可能在同一次執行內取值——跑在套件**裡面**的測試不可能知道自己這一次跑完
     的最終 skip 數（`MIN_TESTS` 能鎖是因為它是靜態常數，不是 runtime 結果）。
  ② 就算改由 runner 事後比對，skip 數**依機器而變**（docker 在不在、pwsh 7 裝沒裝、
     zsh 有沒有）⇒ 硬相等會在任何一台環境略異的機器上假紅，而假紅的鎖最後一定被關掉。
  ③ 靜態站點數不是它的替代量：本輪實測 tools/tests 有 11 個「Windows 上會 skip」的
     站點，卻對應到 32 支已標籤 skip（class 級 decorator 一對多），差 3 倍。
```

### `_CLOUD_ANCHOR` 上方：R74 缺陷本體與 QA-R74-01 blocking 發現

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4853-4865（區段旗標下的註解）

```text
🔴 缺陷本體：§7 表①②量的全是**本機**（六道根層閘門／四棵測試樹／LOC），整節
**零欄位**承載雲端結論；而 `tools/lib/ci_liveness.py` 的哨兵只查排程軌（`--event
schedule` / `workflow_dispatch`），push 軌完全不在視野內。於是 R73 收輪時本機全綠、
`82eee92` 推上去，而**同一個 commit 的 `windows-compat-ci` 在雲端是 failure**
——這件事結構上不可能被任何本機機械物報出來。缺的不是新鮮度，是**平面**。

🔴 **QA-R74-01（BLOCKING）：本鎖的第一版把 `head-sha` 當成「有寫就算」**。實測取證：
把該欄換成全零的 40 位 sha，`cloud_status_problems` 仍回 `[]`；全庫搜尋
`head-sha` 除本檔外**沒有任何生產碼消費它** ⇒ 這個欄位是裝飾品。而新鮮度判準是
`checked-at < max(measured-at)` 的**日期字串**比較，本 repo 一輪常在同一天內完成
（R74 的兩個 commit 相隔 8 小時、同一天）⇒「動了本機基線就得重查雲端」這條因果判準
在一輪之內結構上不可能觸發。兩層加起來的後果正是 R74 頭號發現的成因本體：
錨上記載的雲端結論屬於**上一個** commit，而鎖全綠。
```

### `cloud_pending_problems`：R75 落地首版拿 `origin/main` 當比較對象的教訓

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L5240-5246（docstring 內一段）

```text
    R75 落地時我第一版就是拿 `git rev-parse origin/main` 當比較對象，實測後果：main 上
    三支 workflow 全紅（root-infra／windows-compat／macos-compat），而且**每一次 push 都
    必紅**。推導很短：CI 是在 push **之後**跑的，那時 `origin/main` 已經等於被測的那個
    commit；要讓 commit X 通過，X 的檔案內容就必須寫進 X 自己的 sha——而 sha 是 X 內容的
    雜湊，**自我指涉、不可能滿足**。當回合實測重現（HEAD == `origin/main` == `21354c9`
    時跑同一支測試即紅），錯誤訊息還指著兩個其實相等的值。
```

### `_GHOST_PATH_BASELINE_CEILING`：18→19→18→17→18→19 逐格沿革

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4069-4077（常數上方 `#:` 註解）

```text
#: 🔴 R81 QA B-3 重釘：18 → 19（擴掃描面才看見的既有存量，本常數紅燈訊息明文指定的
#: 那條合法路徑）。🔴 R81 SA-B3 再下修：19 → **18**——那一筆豁免的標的（四方複審轉錄檔）
#: 已於本輪建立、解析得到，自清機制當場要求刪除該筆登記。**下修方向本來就是這道鎖要的**：
#: 天花板是欠債上限，不是額度。
#: 🔴 R82／P4 再下修：18 → **17**——`AISDLC_SDD/.claude/settings.local.json` 改由第三態
#: 承接（見上方表頭與 `is_machine_local_artifact()`）。這一筆不是「清掉了」而是「搬家了」，
#: 但天花板要的就是**本表**只准變小，搬走同樣算變小。
#: R99 round-label-ok：17→18 新增一筆，WHY 同上方 CrossPlatform_R99_Scan_Findings.md
#: R126 round-label-ok：18→19 新增一筆（已刪除的孤兒載具，第二類），WHY 見表內該筆旁註。
```

### `_GHOST_PATH_BASELINE` 上方：R82／P4 對「已 gitignore 出庫」一類的訂正

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4031-4036（常數上方 `#:` 註解）

```text
#: 🔴 R82／P4 訂正上面第二類的措辭與內容：「已 gitignore 出庫」這一族**已經不該住在本表**
#: ——它有專屬的第三態（`is_machine_local_artifact()`，理由見該函式）。逐筆豁免對它是錯的
#: 修法：豁免表是「這台機器上解析不到」的登記，而 gitignored 生成物在**不同機器上解析
#: 結果本來就不同**，於是同一筆登記在 A 機器是必要的、在 B 機器是 stale——兩邊都會紅，
#: 只是紅的那一支不同。本輪據此移出 `AISDLC_SDD/.claude/settings.local.json`（唯一一筆
#: 命中第三態的登記，實測；其餘 17 筆一筆都不是 gitignored）。
```

### R78 ARCH-03／SD-07（具名機械物鎖第四面）：缺陷本體實測三筆

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L3602-3610（區段旗標下的註解）

```text
🔴 缺陷本體（複審逐字指出的逃逸縫）：上面三面判準的擷取器 `_MECHANISM_PATH_RE` 只認
**帶副檔名的路徑**。於是「以一個**裸識別字**指認機械物」這種寫法完全不在任何鎖的視野內：
  · R77 的護欄層**檔數**棘輪常數被它自己那一輪刪掉，全庫剩零個賦值定義、十餘個引用
    （分布十支檔）——**專門偵測懸空引用的那道鎖照樣綠**。
    （🔴 本段刻意不逐字寫出那個已死的名字：本節新加的判準會把它判成幽靈，而那正是它
     該有的行為；訂正註記引述假話等於製造新假話——同 R73 已立的紀律。）
  · 最嚴重的一處：`AutoClaude/tools/check_loc_budget.py` 拿它當「根層 `tools/tests/`
    不納入 LOC 分級管轄」的正當性依據 ⇒ 一整層數萬行護欄碼的豁免，掛在一個不存在的符號上。
  · 同源還有一個已移除的測試方法名與一個從未存在的函式名，散在十餘處註解／docstring。
```

### R76：把 R75 頭號教訓擴到退場／解除條件類判準——為何非擴不可

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L5901-5907（區段旗標下的註解）

```text
🔴 為何非擴不可（同形態第三次復發，而上面那道旗艦鎖結構上抓不到它）：R75 的鎖讀的是
**本模組內 `cloud_*` 家族的 Python 執行碼**。第三次復發卻住在
`tools/windows_smoke_local.ps1` 的**註解散文**裡——E3 原文要求「移除該排程任務後，
`check_scheduled_task_drift.py` 回 rc=0」，而該 checker 的期望值 SSOT
（`tools/scheduled_task_expectations.json`）**同時列著要被移除的那支任務** ⇒ 執行 E3
自己授權的動作必然讓 E3 轉紅。語言不同（PowerShell 註解）、載體不同（散文而非執行碼）、
命名不同（沒有 `cloud_` 前綴），三個縫任一個都足以讓上面那道鎖看不見它。
```

### `_run_check_ignore`：R82／P4 複驗補洞——「追蹤中的」為何不是修辭

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4135-4148（docstring 內一段）

```text
    🔴 **「追蹤中的」不是修辭，是本函式最重要的一道過濾**（R82／P4 複驗補洞）。
    `git check-ignore` 讀的 ignore 來源有三種，其中**兩種不隨 repo 走**：
      · repo 內的 `.gitignore`（tracked ⇒ 每台機器逐字相同）✅
      · `$GIT_DIR/info/exclude`（由 `git clone` 就地新建、**untracked**）❌
      · `core.excludesFile`（使用者家目錄的全域 ignore，例 `~/.config/git/ignore`）❌
    只問「被不被 ignore」而不問「**是誰宣告的**」，等於把第三態的答案接回機器本地狀態
    ——也就是本節正在治的那個缺陷，只是從「檔案系統上有沒有這個檔」換成了「這台機器的
    git 設定裡有沒有這條規則」。複驗當回合在本機實測到它**已經活著**：
    `.git/info/exclude` 有 10 條 repo 完全沒宣告的 `**/.claude/*` 規則，於是
    `resolve_doc_path('AutoClaude/.claude/agent-registry.json')` 在本機回 `'ignored'`、
    在沒有那個區塊的 checkout 上會回 `'missing'` ⇒ 紅照樣會在兩台機器間漂移。
```

### R81 幽靈路徑宣稱 立案：量測值理由、補的縫、R81 掃描面實測

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L3923-3945（區段旗標下的註解，
分兩段搬遷）

```text
立案理由（量測值，不是印象）：`tools/probe/misstep_attribution.py` 現跑的桶分佈裡
「宣稱先於查證」是**最大的具名桶**，而它今天一個機械物都沒有；相對地最小的那個桶
（選錯載具）正是唯一上了機械阻斷的。⇒ 這一桶缺的是門，不是更多自律。

本面補的是**證據錨可解析性**這條線上缺席的那一半：符號那半已有
`TestR78GhostSymbolClaims`、具名機械物那半已有 `mechanism_claim_problems`，缺的是
「治理文件裡**任何**以反引號寫出的 repo 路徑」。這個縫有判例——R75 訂正逐字記載
「此格原先寫的 `AutoClaude/` 前綴在磁碟上不存在，而當時的具名機械物鎖只認 `.py`
副檔名故照樣放行」：讀者照著走必定撲空，而全 repo 沒有任何東西會轉紅。

🔴 掃描面刻意只有**治理活文件**（.md），程式碼面整片排除——這是實測不是偷懶：
`tools/**/*.py` ＋ `.claude/hooks/*.py` ＋ `AutoClaude/tools/*.py` 面上 757 筆宣稱有
49 筆解析不到，而它們幾乎全是合成範例與注入 fixture（`a/b/c.md`、`A/x.sh`、以及既有
機械物鎖自己用來驗紅的假路徑）；判準分不開它們與真宣稱 ⇒ 納入等於製造 49 筆要逐一
辯護的假紅，那種鎖活不過一輪。同理排除輪次凍結史料（`CrossPlatform_R*_*.md`、缺陷
帳本）：它們寫下當時為真，納入等於逼人竄改歷史記錄（同 `_SYMBOL_REF_GLOBS` 的理由）。
```

### `_NIGHTLY_RUN_FIELD` 上方：R76 複審 ARCH-03 補的兩欄 provenance 立案

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4942-4947（常數上方 `#:` 註解）

```text
#: 🔴 **R76 複審 ARCH-03 補的兩欄 provenance**。落地首版的判準⑧ 只有三種判定：欄位缺席、
#: 值是 `none`、值裡有現查不到的 job 名——**沒有任何一條在看「那個宣告現在還成不成立」**。
#: 實測四個互相矛盾的值（宣告 windows 紅／宣告 macos 紅／宣告兩支都紅／宣告全綠）全部判綠。
#: 於是兩個方向都失明：①本輪 PKG-B 修好 `windows-nightly-full` 之後，錨仍會逐字宣告它是
#: 紅的而判準照樣綠＝**一句被鎖守著的假話**；②下週換 `macos-nightly-full` 轉紅，一行都不會響。
#: 它買到的是「有人查過一次」，而它替代的正是那個「橫跨四輪沒人讀」的 issue 通道。
```

### `test_a_tracked_path_is_never_the_third_state`：R82／P4 複驗訂正自陳守備對象

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4526-4533（docstring 內一段）

```text
        🔴 R82／P4 複驗訂正本測試自陳的守備對象（原文寫「`--no-index` 陷阱的紅綠自證」，
        而它對那件事**沒有鑑別力**——把 `--no-index` 加回正式判準，本測試照樣全綠）。實測
        兩組對照：把該旗標加進判準後，341 條陷阱路徑的**最終判決一筆都沒變**（0/341），
        因為 `--no-index` 多出來的命中一律落在 tracked 檔上，而那正好被合取的第二款
        （`prime_machine_local_cache` 的 tracked 否決）整片吃掉 ⇒ **否決款嚴格支配該旗標
        的差異**。真正有鑑別力的是否決款本身：把它拿掉，200 條取樣**全部 200 條**被誤判
        成第三態。「測試名／訊息描述了一件它沒在守的事」正是本檔通篇在治的病，故就地改正
        而不是留著當註腳。
```

### `_handoff_claim_blocks` 巢狀小標題：R79 複審發現的錯誤實作與繞過式處置

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L6410-6415（docstring 內一段）

```text
    🔴 R79 複審（HANDOFF 包注入時當場量到）：**巢狀小標題繼承父節的射程**。
    上一版對「任何 `##` 以上的標題」一律重設 `in_section`，包括 `###`——於是一個
    住在「待辦」大節底下、但小標題本身不含觸發字的 `###` 區塊，整區條目會**靜默退出
    射程**（實測：加了四個小標題之後，拿掉某一項的現查指令，這道鎖照樣印綠）。
    當時的處置是「把觸發字寫進每一個小標題」＝繞過，不是修好；下一個人在 §4 底下
    新增一個不含該字的小標題就會再踩一次，而且沒有任何東西會轉紅。
```

### `_IRON_LAW3_COVERED_FLOOR` R79／R80：逐格沿革（R127 之前尚未搬遷的一段）

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L2729-2735（常數上方 `#:` 註解）

```text
#: R79：4 → 7（`.ps1` 行尾補上 hook＋事後兜底；另新增 exec bit 與目錄項原語兩列，
#: 兩列都是「新增時就已經有掃描器」，分子分母同時 +1）。
#: R80（包 B）：7 → 12。分子 +5＝`$env:*` 讀取、`Get-Command` 解析、大小寫敏感度
#: （前兩項本輪新建站點級判準；第三項是訂正低報）、`.py` 行尾（本輪新建活躍面止血）、
#: 以及兩個新登記且**當輪就有掃描器**的危害類中的 shebang×行尾；naive 本地時間戳那一列
#: 同樣是新增即有掃描器 ⇒ 實際分子為 13，此處只釘到 12 是**刻意留一格**：並行工作包
#: 若在本輪同時動到這張表，釘到剛好等於現值會讓兩邊互相判紅。地板是下界不是等號。
```

## test_check_defect_log_crossref.py

### R71（DEF-101-765 解鎖條件 (c)）：根因與否決的兩個替代方案

原處：`tools/tests/test_check_defect_log_crossref.py` L2050-2063（區段旗標下的註解）

```text
根因逐字（帳本 `DEF-101-765`）：「`current_round()` **只讀帳本**，程式碼註解裡的輪號對它
完全不可見，兩邊可以無限漂移」。`DEF-101-757` 入規「已知的鎖射程缺口不得只以劃界結案」，
故本組鎖把那個盲區封起來——但**刻意射程窄而準**，判準是「超前」不是「不等於」：

  ✅ 採用：輪號 **> 帳本當前輪** 即紅。
     · 對正當歷史引用**天然免疫**：「R70 那輪做了 X」講的是已發生的輪次，恆 ≤ 當前輪。
       這一點不是宣稱，由 `test_a_legitimate_historical_reference_is_not_flagged` 坐實。
     · 抓得到 `DEF-101-765` 的**實際形態**：本批程式碼自稱 R72、帳本當前輪 R71。
  ❌ 否決 ①「輪號 ≠ 當前輪即紅」：本 repo 的註解**大量**逐字引用往輪（`R42`／`R60`／
     `R69`…），實測全樹逾千處 ⇒ 幾乎每支檔都紅，屬「寬而吵」，鎖會被 opt-out 掉。
  ❌ 否決 ②「只掃未提交／本批新增的行」：可攔本次事故，但一 commit 就失明——鎖的價值
     在下一輪，而下一輪它什麼都看不到；且 `git diff` 面對 rebase／squash 不穩定。
  ❌ 否決 ③「凡輪號一律要求同行帶輪次來源註記」：等於強制全樹改寫上千處註解，成本遠高
     於收益，且新格式一樣會漂移（本 repo 已有多筆「格式訂了沒人跟」的前例）。
```

### 早退遮蔽（P0-A）：立案事故

原處：`tools/tests/test_check_defect_log_crossref.py` L2469-2473（區段旗標下的註解）

```text
兩道鎖同源於一次實測事故：帳本目錄新增一份未登記的治理文件時，本工具**只印 2 行**
（`❌ 具名治理文件涵蓋面與磁碟脫節` ＋ 那一筆），原本會印的 8 筆孤兒 warning、18 筆
已結列殘留待辦全部消失——而讀者看到的是「輸出變乾淨了」。同一則訊息教人「請在該常數
補上一筆」，但那支檔當時卡在 raw-line 棘輪 1474/1474、**餘裕 0 行**，照做即破另一道
硬閘 ⇒ 訊息在磁碟現況下不可執行，兩道鎖互為對方的違規。
```

### `_ADD_CONTENT_DIRECTIVES`：R76 複審 ARCH-02／SD-02 訂正（兩欄→三欄）

原處：`tools/tests/test_check_defect_log_crossref.py` L2588-2593（常數上方 `#:` 註解）

```text
#: 🔴 R76 複審 ARCH-02／SD-02 訂正：本表落地首版**只有兩欄**（第三欄「被要求編輯的檔」
#: 在註解裡宣告、在實作裡不存在），而餘裕斷言硬編 `Path(m.__file__)`、根本不讀本表 ⇒
#: 上方 `:2333` 那句「要納入就在本表加一筆」是假的：照三欄格式加一筆會 `ValueError:
#: too many values to unpack`，退成兩欄則 `_message()` 靜默跑到別支函式、產生一則講
#: 別的常數的誤導訊息。現已補成真三欄、餘裕斷言逐筆迭代、`_message()` 具名 dispatch
#: 且未知名字 fail-loud。同時把第二支工具真的納管進來（那正是它「做成表格」的意義）。
```

### R84：`改派`／`回執` 出口過期判準——立案與住所裁決

原處：`tools/tests/test_check_defect_log_crossref.py` L2050-2063 附近的姊妹段，
實際座標見 `tools/tests/test_check_defect_log_crossref.py` L3217-3227（區段旗標下的註解）

```text
🔴 立案（帳本 `DEF-200-041`，R84 落地為 `DEF-200-047`）：`m._reassign_hit()` 是硬規則②
的**無條件**出口——它只問狀態欄有沒有「改派」／「回執」字樣，**不問改派到第幾輪**。於是
一列寫過一次改派附記之後，它的承接輪號此後永遠不再被比較：實測 `DEF-101-886`／`887`
的出口寫的是 R81，而 HEAD 已是 R83 收輪，三輪零交付卻一次都沒轉紅。

🔴 **為何判準住在測試檔而不是 `check_defect_log_crossref.py`**（誠實劃界，不是偏好）：
該工具受 `check_loc_budget.SPECIAL_FILES` 的 raw-line 棘輪管（門檻 1474），當回合實測
raw 餘裕 22 行，而 `TestActionableMessagesHaveLocHeadroom` 另要求它保留
`_MIN_DIRECTIVE_HEADROOM`(=5) 行 ⇒ 可用只有 17 行，塞不下「判準＋WHY＋逐列訊息」。
代價已誠實記在帳本 `DEF-200-047`：閘門 `check_defect_log_crossref.py` 的 rc 不含本判準，
咬人的是根層 unittest 閘門（CI 亦跑）。
```

## test_context_budget_guard.py

### `InvariantLocksArePresentTest`：2026-09-07 掌舵者裁決（INV2＋INV3 拆除）

原處：`tools/tests/test_context_budget_guard.py` L11916-11927（class 內 `#:` 註解）

```text
    #: 現查快照（2026-09-07，`grep -n 'class Inv[0-9]\|class Fix[0-9]'
    #: tools/tests/test_context_budget_guard.py`）：本檔目前存在的 6 個 INV/FIX 類別，
    #: 逐一登記其**當下**測試方法數下限。數字是量測值不是常數——之後合法新增測試會讓
    #: 現值大於此表（不紅）；本表只在有人整批刪除／砍到低於下限時才出聲。
    #:
    #: 🔴 2026-09-07 掌舵者裁決（INV2＋INV3 拆除，SA＋SD 兩位獨立審查通過）：
    #: `Inv2Inv3WorkflowFanoutGateTest`（6 支）與 `Fix4FirstWindowCannotFanOutEndToEndTest`
    #: （2 支）兩列**整列移除**——被守的行為（第一無人視窗禁 fan-out／需前一窗證明有進度
    #: 才解鎖）已不存在，留著列就會讓判準對「不存在的類別」拋例外而恆紅（`loadTestsFromName`
    #: 對缺類別是拋例外，不是回 0，所以不能只把數字改成 0）。Fix4 唯一與該禁令無關的
    #: 那一支（`test_arm_sentinel_arms_fail_open_when_job_list_is_unmeasured`）已遷入
    #: `Inv5SingleOwnerTest`，其下限因而 6→7（遷入的那一支在新家一樣被守著，不是淨損）。
```

原處：`tools/tests/test_context_budget_guard.py` L11919-11922（dict 字面內的行內註解）

```text
        # 🔴 收尾單人窗口重釘 7→11（實測 2026-09-07：12 支，見上方 loader 現查指令）——
        # 規則 5 的 macOS 真機測試（`test_real_launchd_listing_feeds_other_owner_for_
        # session`）＋既有 M-19 Windows 對照＋失敗開放族測試併入本類別後累積 12 支，
        # 留 1 支裕度（同其餘各列既有慣例：下限＝現測值−1，非湊整）。
```

### `test_the_resume_prompt_never_names_a_workflow_resume_call`：三段沿革（DEF-200-270③→gated→拆 gate）

原處：`tools/tests/test_context_budget_guard.py` L6688-6693（docstring 內一段）

```text
        史料兩層：DEF-200-270 ③ 原本**無條件**注入 ⇒ headless 窗口
        一起手就重跑 34-agent Workflow、撞權限牆前先燒掉一輪 token；2026-09-05 改成
        gated（INV2＋INV3）；2026-09-07 連 gate 一起拆——醒來的主 agent 與互動 session
        同等信任，要不要 fan-out 由它自己讀任務書／handback 判斷，系統不再用提示句驅使
        特定工具呼叫。fanout 清單（`resume_call` 欄）仍然照寫，那是給人／給模型自己讀的
        磁碟事實，不是 prompt 注入。
```

### `test_the_record_states_when_resume_from_run_id_is_invalid`：DEF-200-270 措辭 stale 的沿革

原處：`tools/tests/test_context_budget_guard.py` L6613-6616（docstring 內一段）

```text
        DEF-200-270：「同 session only／沒有任何排程器按得到」在 `claude -p -r <sid>` 無頭
        續跑成立後（R111／R113 四段全通；round-label-ok）已 stale：
        `-p -r` 就是同一個 session，run 目錄住
        `<sid>/` 底下。
```

### `test_va1_both_routes_carry_permission_mode_and_settings`：2026-09-07 姿態檔合一裁決

原處：`tools/tests/test_context_budget_guard.py` L3150-3158（docstring 內一段）

```text
        🔴 2026-09-07 掌舵者裁決（INV2＋INV3 拆除）：姿態檔**只有一份**——
        `UNATTENDED_SETTINGS`。此前 M-06 另立 `.claude/settings.unattended_first_window.json`
        給「第一窗」用（deny 帶 Task／Agent／Workflow），現已刪除：訂閱制風險模型下，
        一旦主 agent 確認喚醒即與互動 session 同等信任，不分窗次。額度風險由
        `RELAY_MAX_SPAWNS`（每視窗 spawn 上限）＋1 小時牆鐘 timeout＋INV4（無人看管一次
        沒進度就停）界住，不需要分階段 fan-out 解鎖。故本條一併釘住「兩路指向同一份檔」
        與「那一份檔的 deny 不含 fan-out 三工具」——本類原有的兩支 fan-out 姿態測試
        （第一窗 deny 三工具 ＋ followup 窗 allow 三工具的控制組）證明的是「兩份檔有
        分流」，該前提已不成立，故連同姿態檔一起刪除；它們的核心斷言併進本條。
```

### `WindowUsageIsToldTheSameWayByBothOutletsTest`：①②③ 三支測試的紅端沿革

原處：`tools/tests/test_context_budget_guard.py`
`test_both_fanout_branches_print_the_window_count_they_were_given` L11082-11084、
`test_the_blocked_workflow_message_counts_the_real_ledger` L11099-11102、
`test_a_full_window_reads_as_zero_on_both_sides` L11118-11122（三段 docstring 內文）

```text
`live=3` 是挑過的：它既不是 `0`（舊 Workflow 分支硬寫的那個字面），也不是 cap
（否則「印的是 live」與「印的是 cap」在畫面上分不出來）——底下那一行斷言就是在
釘住這個前提，免得哪天階梯一改讓 cap 恰好等於 3 而本條靜默失去鑑別力。
```

```text
紅端逐字（R96 落地前）：Workflow 那一支傳的是**字面 `0`**，而真正的 `live` 要更
後面才算得出來、該分支早就 `return 2` 了 ⇒ 被擋的人恆看到「本視窗已用 0 次」，
於是會推論「配額還有、擋我的是別的原因」。①（純渲染）結構上抓不到它——①問的是
「給了 live 有沒有印」，而這個缺陷是「呼叫端根本沒把 live 給進去」。
```

```text
紅端（主控本輪實測）：`--pace` 印「現在可派 2 個 agent（硬上限 cap=2）」的同一
刻，`Agent` 被守衛擋下、理由逐字是「每 300s 最多 2 次扇出，本視窗已用 2 次 ⇒
不執行」。根 CLAUDE.md〈現查指令速查表〉明文要求「**派工前**問『現在能派幾個
agent』→ `--pace`」⇒ 官方指定的派工前置出口會給出一個當場被守衛推翻的數字。
①②都抓不到它：那兩條完全不碰 `--pace` 這個出口。
```

## test_platform_neutral_paths.py（Dev-Trim Trim-C）

### 模組 docstring：R11/R12 磁碟機假路徑判準沿革

原處：`tools/tests/test_platform_neutral_paths.py` 模組 docstring（搬遷前，L2-29）

```text
WHY：R11 真 Mac 首跑實證——測試裡把 D:/repo 這種磁碟機假路徑字串塞給 Path()，
它只在 Windows 是絕對路徑；POSIX 上 `repo_root / 絕對路徑` 的 pathlib join 會退化
成串接（D:/repo/D:/repo/…）、resolve 後恆不相等 → Windows 全綠、Mac/Linux 假紅
（test_check_hooks_liveness.py TestIsHooksEffective 兩案例實際紅過）。修法是改用
_platform_helpers.ABS_FAKE_REPO 平台中立常數；本測試機械掃描測試樹原始碼，
防未來有人複製舊 pattern 再踩一次。

R11 四方複審補強（SD-2/ARCH-2）：原 regex 只抓「Path( 後緊接引號＋大寫磁碟機
＋正斜線」單一形態——漏抓 r/f 等字串前綴變體、反斜線形態 X:\\、小寫磁碟機，
以及**裸字串**磁碟機路徑常數（原病灶正是不經 Path( 直呼的裸字串）。改為抓
「任意字串字面值以磁碟機路徑開頭」（引號後緊接單一字母＋冒號＋斜線或反斜線；
匹配起點是引號本身，故 r/f/b 前綴一律涵蓋）。並：
  (a) 每行先剝 `#` 註解尾再掃（註解舉例不誤報；heuristic 不解析字串內的 #，
      字串內含 # 且其後才出現磁碟機路徑的極端形態會漏掃，屬可接受取捨）；
  (b) 豁免顯式平台語意 PureWindowsPath(/PurePosixPath(（該行本來就是在寫
      特定平台路徑）與逐檔豁免清單 _ALLOWED（附 WHY）；
  (c) 支援行尾 `# platform-ok: <理由>` 豁免標記（合法命中須逐行附理由明示處置）。

R12 掃描面（ARCH-R12-4；DEF-101-149 病灶類別在其他測試樹此前零守門）：
  1. tools/tests/（本目錄，非遞迴——維持 R11 現狀）
  2. AISDLC_SDD/scripts/tests/（非遞迴）
  3. AutoClaude/tests/（**遞迴**，含 plugins/core/contract/… 子樹）
  4. LATEST 版 tools/fsm_runtime/tests/（遞迴；LATEST 以 scripts/sdd_version.py
     SSOT subprocess 解析——手法對齊 check_script_parity；解析失敗 fail-loud，
     不得靜默縮小掃描邊界。凍結版 v0.01~v0.2X 依鐵律不掃、也不可修）
```

### `_scan_roots`：tools/tests 逐輪重釘（R97）

原處：`_scan_roots()` 內 `_TESTS_DIR` 元組上方註解

```text
🔴 護欄層重釘 R97 追加當輪由 85085→85394 新增 3 支鎖檔，`tools/tests`
實測 67 支越過腐化上界 66（`TestScanRootFloorBand` 開的藥：只還守得住
79% 掃描面），依失敗訊息重釘 53 → 64。
```

### `_scan_roots`：tools/lib 逐輪重釘（R81／R85-P12／R98／Gap C／第七輪）

原處：`_scan_roots()` 內 `tools/lib` 元組上方註解

```text
R81 10→21（`quota_ledger.py`／`quota_limits.py` 落地）；R85／P12 21→30
（`unattended_authz.py` 落地）；R98 30→41（`quota_policy_env.py`／
`schedule_backend_calendar.py`／`sentinel_lifecycle_arm.py` 三支新子模組落地，
本樹 43 支越過腐化上界 40，重釘理由與淨額詳見 `CrossPlatform_R98_Scan_Findings.md`）；
Gap C 接線輪 41→49（`onboarding_snapshot_note.py` 落地，本樹 52 支越過腐化
上界 51，重釘值＝下限帶訊息逐字要求，詳見 `CrossPlatform_R106_Scan_Findings.md`
的 R109 標記行）。第七輪收尾重釘 49→59（新增 harness_feed.py）。
```

### `_DIRENT_UNGUARDED_DEBT`：42→40→39 逐輪重釘沿革

原處：`_DIRENT_UNGUARDED_DEBT` 常數上方註解

```text
DEF-200-275 第四輪 42 → 40（方向＝下修）：SDD LATEST `conversation_ledger.py` 原有三個各自
`tmp=…; os.replace(tmp, path)` 的站點（append／merge／calibration）收斂為 `_atomic_write_yaml`
一處（pid 專屬 tmp），判準逐字指示「有人修掉了，請把數字改小：實測 40」⇒ 照填。
DEF-200-275 第七輪 D31（windows-compat-ci #220／#221）40 → 39（方向＝下修）：
`conversation_ledger._atomic_write_yaml` 的 `os.replace(tmp, path)` 移進新函式
`_replace_with_retry`，改用 `try: os.replace(...) except PermissionError:` 短退避重試
（見該函式），本判準因此把它由「未處置」改判為「已處置」——一個站點消失。同輪新增的
`_merge_sidecar_if_present` 站點 `os.replace(sidecar, claimed)` 一開始就寫在
`try: … except (PermissionError, FileNotFoundError):` 內，本判準判定為已處置，不計入
census（新增站點但不增債）。判準逐字指示「有人修掉了，請把數字改小：實測 39」⇒ 照填。
🔴 D31b／D31c 訂正（W-5，四方複審發現本段描述已過期，訂正協議：保留原文，追記訂正）：
上一段描述的「認領改名」（`_merge_sidecar_if_present` 內 `os.replace(sidecar, claimed)`）
已在 D31b 整段移除——四方複審發現該手法仍有兩個資料遺失缺陷（C3／W-1，見
`conversation_ledger.py` 模組 docstring D31b 段），總架構師裁決改成 sidecar「每筆一檔、
寫成即不可變」，不再需要任何認領改名；`_merge_sidecar_if_present` 起只剩「掃描目錄→
逐檔讀→折進記憶體 doc」，沒有 `os.replace` 呼叫（純讀取，不在 `_DIRENT_PRIMITIVES` 掃描
範圍內）。D31c（解複審 W-4）在 `_write_sidecar` 既有的 `_replace_with_retry` 呼叫端加了
一個新分支（`LedgerReplaceDenied` 時保留 tmp，不再無條件 `finally: tmp.unlink()`），但
呼叫的仍是同一個 `_replace_with_retry`——該函式內部唯一的 `try: os.replace(...)
except PermissionError:` 站點本身沒變。D31b／D31c 兩輪都沒有新增或移除任何
`os.replace`／`os.rename`／`shutil.move` 站點，數字仍是 39
（`test_unguarded_site_census_matches_the_ledger` 當回合實測，見 D31c 任務書）。
```

### `test_the_index_exec_set_matches_the_onboarding_policy_sentence`：五十輪 open 沿革

```text
該列自 R14 起 open 逾五十輪，逐字寫著解鎖條件＝「以 `git ls-files -s` 取出 mode
`100755` 的檔案集合，與 `ONBOARDING.md` §6 執行權限政策句具名的 755 清單逐項互比
（散文即 SSOT），不符即 rc=1」。**取數管道早就有了**（本類別 R79 落地時就在讀
`git ls-files -s`），缺的一直是這一項比對——所以政策句與索引之間的漂移到今天為止
一個訊號都沒有。
```

### `test_the_dst_gap_is_reproducible_without_touching_the_system_clock`：第一版 zoneinfo 教訓

```text
🔴 **不用 `zoneinfo.ZoneInfo("America/New_York")`**（第一版就是那樣寫的，當回合
實測 `ZoneInfoNotFoundError`）：Windows 沒有系統 tz 資料庫，`zoneinfo` 要靠
`tzdata` 這個**選配**套件，而本 repo 沒有裝它 ⇒ 那種寫法會讓這條在 Windows 上
變成 ERROR、在 mac/Linux 上通過。本判準在守的就是「單平台判準不可無條件外推」，
它自己第一版卻正是那個形態。改用固定 offset 直接構造 fall-back 的兩個瞬間：
EDT(-04:00) 的 01:30 與 EST(-05:00) 的 01:30 相差正好一小時，而**丟掉 offset
之後兩者完全相同**——這就是 DST 落回那一小時的全部語意，且零外部相依。
```

### `test_every_registered_debt_entry_still_has_a_platform_neutral_reason`：R82 複驗補正

```text
🔴 第三個條件刻意向 **blob** 問而不是向工作樹問（R82 複驗補正）：本條的失敗訊息
叫人「把該筆自欠債表刪掉」，而工作樹版對「index 有、工作樹沒有」（稀疏 checkout）
回 `False` ⇒ 那會是一個**假紅，且它建議的動作會就地縮小掃描面**——被刪掉的那一筆
正是 Windows 那台仍然成立的欠債。縮面的表徵是「看起來更乾淨」，沒有人會發現。
```

### `test_no_two_files_share_the_same_marker_string`：SC-4／SC-9 共用判例

```text
`test_adr_xplat001_c1c2_lock.py` 的 SC-4／SC-9 **刻意**共用同一個
`stale-premise-ok:`（該檔 `sc9_…` 的 docstring 逐字寫「豁免沿用 SC-4 的…」，
且死信偵測的 `consumed` 集合把它算成同一個），那是**同一位擁有者**在同一份檔裡
自己看得到的設計；把它判紅只會是自製誤報。真正會出事的是**跨檔**：兩支互不知情
的掃描器各有一套 stale 偵測，其中一方的合法豁免就是另一方的紅——ARCH-01 那筆
逃出去的縫正是這一格。
```

## test_check_hooks_liveness.py（Dev-Trim Trim-C）

### `test_the_sdd_latest_hook_tree_is_covered_too`：R88／DEF-200-104 立案

```text
立案（R85／P4 提出、R88 修）：前兩個掃描面是 `.claude/hooks/` 與
`AutoClaude/tools/hooks/`，而 SDD LATEST 那一棵樹**一個判準都看不到**——當回合
AST 實查有 3 個裸 `subprocess.check_output(["git", ...])`（`closure_evidence_
verify.py` 1 個、`post_commit_drift.py` 2 個）。它們是真的會跑的：SDD 框架的
hook 掛在版本目錄下，以 LATEST 為 cwd 開 session 是常態（同 R84 對
`FROZEN_SETTINGS_PREFIX` 下過的判決——把活躍面排除在普查外＝假的安心）。
```

### `registered_tool_scope`：R80 解析面改問 SSOT

```text
🔴 R80：解析面由「`command` 字串」改問唯一真相源 `tools/lib/hook_wiring.py`。
exec form（治 Windows 閃窗的形態）把腳本路徑搬進 `args`，只讀 `command` 的舊寫法
轉換後會回**空 dict** ⇒ `registration_shrink_problems()` 會把**每一支** hook 都
報成「註冊條目整個不見了」。射程判準必須跟著形態走，否則它守的是字串不是事實。
```

### `TestSamePathIsNotVacuous`：symlink／junction 兩平台覆蓋沿革

```text
這幾格**兩個平台都跑得到、也都在量同一件事**（沒有任何 `skipUnless`）：連結是
POSIX 與 Windows 都有的機制，只是**原語不同**——POSIX 是 symlink、Windows 是
目錄 junction（原語選擇與 WHY 見 `_make_directory_link`）。此前這裡兩邊都寫
`os.symlink`，於是 Windows 側恆為 skip；改成各走各的原語之後，Windows 不再需要
開發者模式就有真覆蓋。殘留的那一個 skip 只剩「這台機器的檔案系統根本建不起
連結」（FAT／某些網路磁碟）這一種機器能力問題，不是平台語意
（`DEF-101-766`：單平台判準不可無條件外推，反之亦然）。
```

### `TestLintPowerShellHookBehaviour`：刻意不掛 skipUnless 的兩個理由

```text
🔴 **刻意不掛 `skipUnless(os.name == "nt")`**，兩個理由：
  ① 這些判準的成因是「payload 帶的是一段 PowerShell 指令」，不是「這台機器是
     Windows」——把它綁在當下平台上，mac/Linux 一側就永遠沒人跑過（本檔的
     `TestBlockBashHookGuidanceSurvivesNonUtf8Locale` 早有同樣的取捨與理由）。
  ② 新增一個平台 skip 站點會動到 `skip_tag_policy._SITE_CLASS_CENSUS` 的相等
     判準，而那張表由另一個工作面在維護。用注入 `os.name` 取得**更大**的覆蓋、
     同時零跨檔耦合，比「多開一個站點再去別人的表上加一」好。
```

### `TestNightlyTaskActionsAreWindowless`：LogonType=S4U 漂移沿革

```text
第一層防護是 `LogonType=S4U`（無互動桌面 ⇒ 本來就看不到），但那一層**已經被實測
證明會漂**：`tools/scheduled_task_expectations.json` 的 `_why` 逐字記載 smoke 任務的
LogonType 曾漂成 `InteractiveToken` **連三輪**，而漂掉的那三輪正是使用者會看到彈窗
的那三輪。`-WindowStyle Hidden` 是與它獨立的第二層。
```

### `TestConversationLedgerChildTimeoutParity`：零跨層 parity 測試立案

```text
是**手寫鏡射** `.claude/hooks/sdd_hook_router.py` 的 `_CHILD_TIMEOUT["PostToolUse"]`
（見該模組 docstring D31b-3 段的 WHY——`worst_case_ledger_budget_sec()` 的組合上界必須
留給 router 的 child timeout 足夠餘裕）。全庫此前**沒有任何跨層 parity 測試**斷言兩者
真的相等：`test_conversation_ledger.py::LedgerLockBudgetTests` 只是拿
`worst_case_ledger_budget_sec()` 跟 `conversation_ledger` 自己的
`HOOK_CHILD_TIMEOUT_SEC` 比——兩個常數同出一檔，自己跟自己比恆真，router 那邊的值
漂移了（例如有人改了 `_CHILD_TIMEOUT["PostToolUse"]` 卻忘記同步鏡射常數）不會被任何
測試發現。
```

### `test_the_shim_has_exactly_one_home`：取樣面選 argv 而非整檔文字

```text
🔴 取樣面刻意是**解析後的 argv**，不是整份檔案的文字。第一版寫成
`assertNotIn("runpy.run_path", _SETTINGS.read_text(...))`，當場被
`test_archive_defect_log.TestNoAssertionSamplesALiveDocumentWholesale` 抓到：
該檔有 6 個 `_comment` 在**合法地**敘述舊 shim 的設計理由，只要有人在註解裡
寫出那個字樣就假紅——而假紅的下場是有人回頭去改註解裡的歷史敘述（那正是
Pkg-P12 實際發生過的事）。判準要看的是「**會被執行的東西**裡有沒有 shim」。
```

### `test_the_p0_hook_is_covered_by_the_production_form_lock`：R75 WHY

```text
WHY（R75／DEF-101-802）：改寫 `_run_hook` 的 argv（例如換成 `-c` 形態）
曾經會讓 `.claude/hooks/block_bash_on_windows.py` 靜默離開 child 編碼判準的
射程——一支**測試**的寫法決定另一道鎖的射程。判準四改以 production 的註冊表
（`.claude/settings.json` 的 `-c` ＋ runpy 形態）為掃描面，本案只確認那道鎖
真的存在且真的罩住這支 hook，避免本檔日後被重構時無人知情。
```

### `test_the_cwd_criterion_still_catches_a_launcher_that_never_chdirs`：為何非有不可

```text
🔴 **為什麼這一格非有不可**：上一格剛從「字面相等」換成「同一個實體」，而
放寬判準最常見的失敗模式就是**寬過頭變成恆真**。合成注入一支「忘記 chdir」
的啟動器（那正是它要防的 P0：hook 在錯的 cwd 下跑，所有相對路徑判準全歪），
證明新判準仍然說得出話。
```

### `test_non_windows_keeps_the_platform_contract`：R85／P12 訂正

```text
本 docstring 的前一版寫「mac/Linux 開 Auto Pilot 時這道鎖必須另外補」，那句話
自 R85 起已為假：mac 側補在 `.claude/hooks/block_destructive_git.py`
（matcher `Bash|PowerShell`、平台中立），判準與訊息兩支共用
`tools/lib/unattended_authz.py` 這一個家，回歸鎖是該檔的姊妹鎖
`test_block_destructive_git_r83.TestUnattendedAuthzHasTeethOnEveryPlatform`。
```

### `test_the_windows_branch_uses_a_junction_not_a_symlink`：唯一證據

```text
沒有它，把 `_make_directory_link()` 的 junction 分支刪掉會完全無聲：mac 上
每一格照樣綠（那條分支在 mac 上本來就不會執行），而 Windows 側悄悄退回
「恆 skip」——測試檔在、判準在、rc 是 0，與修好完全相同。
以注入 `os.name` 驗證而不是掛 `skipUnless`，是本檔既有慣例（見 `:481`／`:825`
兩處的同一理由：注入取得的覆蓋比「只在對的機器上才跑」更大）。
```

### `test_the_gui_whitelist_is_per_site_not_a_whole_file_pass`：R84／SD-05 缺口實測

```text
修前的判準是 `_GUI_CARRIER_SYMBOL in text`（整檔），實測注入：只在**註解**裡提到
它、另外寫一個內插出 `powershell.exe` 的 Action ⇒ **0 筆命中**。而 console 載具
混在內插裡正是這一族最難看見的形態（第一分支的字面比對看不到它）。
```

### `test_every_active_settings_file_passes_the_form_criteria`：擴面前假紅

```text
為何這一格此前不存在（而不是「不需要」）：`hook_form_problems()` 對
`AutoClaude/.claude/settings.json` 實測回 **12 筆假紅**（B／E 兩條做字面比對，
而那份檔的載具帶 `../`）⇒ 想擴面的人會先撞到一堵假牆，於是擴面一直沒發生，
而 SDD LATEST 那份 shell form 就一直沒有任何形態判準看著。假紅先修（見
`win_carrier_kind()`），再擴面——順序反了就會有人把判準關掉。
```

### `test_collapse_is_judged_per_session_not_by_the_historical_total`：R78／SD-03

```text
上一版的崩塌判準建在跨 session 合計的 `shell_calls == 0` 上，而預設用法會
把整個逐字稿目錄加總（本機 51 支）——那是只會單調增長的歷史量，於是「今天
格式改了」這個唯一要防的失效結構上打不出來。本測試餵的正是那個情境：一支
舊的、量得到東西的逐字稿 ＋ 一支新的、有記錄卻抽不到任何 shell 呼叫的。
合計 `shell_calls` 是 2（>0）⇒ 舊判準會回 rc=0＝「本輪零違規」。
```

### `TestRunEncodingRegression`：R10 QA-8 WHY

```text
WHY：R9 修復「text=True 無 encoding 在 zh-TW Windows 走 cp950 → 非 ASCII repo
路徑 UnicodeDecodeError → liveness 靜默失效（無法判定＝不警告）」，但 13 個既有
case 全 mock _run，重構移除 encoding 參數時測試依然全綠。本 case 直接鎖住
subprocess.run 的呼叫參數（同輪同款修復在 test_git_hooks_install_common 有鎖，
此處補齊對稱）。
```

### `TestHooksDoNotSignpostMissingLocks`：DEF-101-790 WHY

```text
WHY：`block_bash_on_windows.py` 的指引訊息指名一支從未存在的鎖檔，真正的鎖
卻在本檔裡。**執行規則的機械物給錯的指路比沒有指路更糟**——讀者會認為它比
文件權威，於是「我查過了」是假的（`tools/ruff.toml` 檔頭有過同型訂正：原本
指向一支沒有該類別的測試檔）。射程刻意只到 `.claude/hooks/`：那是本 repo 唯一
「會主動阻斷使用者操作」的一層，指路錯誤的代價最高。
```

### `TestFrozenShellFormIsAShrinkOnlyExemption`：R84 訴求 7 立案

```text
🔴 立案（R84 訴求 7）：這一族此前是**結構性豁免**——`FROZEN_SETTINGS_PREFIX` 一句話
就把 30 份全部踢出掃描面，於是「凍結面有沒有被人動過」與「LATEST 轉了沒有」兩件事
同時失明。凍結面依 Copy-on-Evolve 政策不改寫，所以正解不是把它們也轉掉（那才是打破
政策），而是把「還有幾份是 shell form」登記成**可查的量測值**、判準取相等、方向只准
變小。新開一版**不會**讓它上升：新版由已是 exec form 的 LATEST 複製而來。
```

### `TestAutoClaudeHookSpawnsAreConsoleFree`：R84 訴求 7／C1 立案

```text
立案事實：`AutoClaude/tools/hooks/check_sh_eol.py::_run_git` 對 `git.exe` 的
`subprocess.run` 沒有 `CREATE_NO_WINDOW`。父行程是 `pythonw.exe`（GUI 子系統、
**沒有 console**），Windows 在這種情況下會替 console 子系統的 child **配一個新
console 視窗** ⇒ 每次 Write／Edit 到 `.sh` 就閃一次。`.claude/hooks/` 那一棵樹早有
判準看著（`ConsoleFreeSpawnTest`），`AutoClaude/tools/hooks/` 這一棵**一個都沒有**。
```

## test_archive_defect_log.py（Dev-Trim Trim-C）

### 模組 docstring：R60 round 1 四方複審五個鑑別力缺口

原處：`tools/tests/test_archive_defect_log.py` 模組 docstring（搬遷前）

```text
R60 round 1 四方複審拆穿本檔初版五個鑑別力缺口，逐一對應現行結構：
`TestCheckModeBugInjection`（注入七種真實缺陷比對 problem 集合差異，而非只看 rc）／
呼叫 `ADL.POINTER_RE` 本體對真實帳本雙分支斷言（原自寫窄正則零測試消費者）／
`TestConservationGuardsAreExplicitNotAssert`（AST 斷零 `assert` 陳述＋`python -O`
子行程重驗，原裸 `assert` 在 `-O` 下整組消失）／`TestCheckIsWiredIntoGates`（斷言
pre-push／CI 真的執行 `--check`，原無人看 rc）／`_generated_header_of()` 結構邊界
（原 `[:4000]` 切片溢入表格區撞到合法引用字樣）。五項缺口細節與 Pkg-P12 假紅史料
見證據檔〈第七輪 史料搬遷（Dev-Trim8）〉。
```

### `test_a_new_archive_header_is_generated_and_carries_no_retracted_claim`：取樣範圍沿革

```text
🔴 取樣範圍走 `_generated_header_of()`（結構邊界）而**不是**寫死切片：Pkg-P12
前這裡是 `[:4000]`，會切進逐字搬入的表格區、撞到某列缺陷描述而假紅。該假紅由
下方 `test_the_header_boundary_excludes_a_row_that_legitimately_quotes_it` 永久
釘住，鎖的牙由 `test_the_retracted_claim_lock_has_teeth_on_a_header_borne_claim`
釘住（兩面都在，才不是「為了消紅燈把鎖弄鈍」）。
```

### `test_the_two_quotation_exceptions_are_exempt_but_always_printed`：round 2 補洞立案

```text
🔴 這兩條是本輪自己補的洞（帳本 round 2 實際寫入時當場踩到）：
  (甲) code span 引述 —— 帳本的缺陷條目本來就要逐字引述判準語法（敘述
       ARCH-R60-01 時寫 `` `立帳見主檔 DEF-101-493` ``）；
  (乙) 術語提及 —— 本 repo 慣用「立帳見」字樣 這種中文引號寫法（本工具自己的
       錯誤訊息就是），一律誤報會逼人改寫**正確的**散文。
硬要求若把這兩種也當宣稱，帳本永遠無法談論自己的判準；但豁免必須看得見——
否則「用反引號夾帶一個真指針」就是新的靜默規避路徑。
```

### `TestPlanRejectsRowsWithExternalResidencePointers`：DEF-101-612 立案史料

```text
DEF-101-612 立案史料（R60 收尾包搬遷後家族與治理文件共 11 處居所指針同時失實）
搬遷，原文＝Guard_Repin 證據檔 §E-12。本類別逐項注入真實會撞到的三種形態
（立帳見主檔／見主檔／已在某 archive），並反向坐實「正確的排除範圍」不會誤傷。
```

### `TestCriteriaListIsASingleSsot`：round 2 殘留清單漂移

```text
原始缺陷：round 2 主控推翻方案(乙)、刪掉 `check()` 的第(7)項「具名治理文件無家族專用
語法的指針宣稱」反向鎖，卻**漏改 `apply()` 標頭裡手寫的「共七項」清單**。而 archive 是
**零刪除的史料檔** ⇒ 每跑一次 `--apply` 就把那份失實宣稱複製成一份新的永久紀錄。
這與本工具立帳要消滅的病（「宣稱一道機械檢查存在而它不存在」）完全同型，且是在同一輪、
同一支工具身上復發。另一處殘留：`_fenced_line_numbers()` docstring 還寫著「判準⑦ 用」。
```

### `TestR82RotationSideEffectsAreAnnounced`：DEF-101-977／676 兩筆事故形態

```text
意圖（Rule 9）：這兩筆是同一種病的兩面——歸檔器改變了下游判準的輸入，卻讓下游的人
去發現後果。977 的實際發生形態：`--archive-num 64` 搬走 3 列，`OVERSIZE_ROW_GRANDFATHERED`
的那 3 筆當場過期、`check_defect_log_crossref.py` 判準②轉紅，而歸檔器對此**零輸出**
⇒ 每輪歸檔都復發、每輪都手動修。676 的形態：每次 `--apply` 都把一條索引 bullet 寫回
主檔家族，於是釋出與新增同時發生，而**只有釋出那一半被印出來**，讀者因此以為餘裕買到了。
```

### `TestMoveSubsetSelectionIsNamedAndTraceable`：DEF-101-811 原始缺陷

```text
原始缺陷：`--apply` 全有全無，唯一的「不要搬這一筆」入口是判準④ 的 `--ack-handoff`
——而那是**加入**用的，方向相反。於是每輪都得先讓工具把本輪列一起搬走、再手工把它們
還原回主檔；手工還原一份剛被就地覆寫的帳本，正是本工具立帳要消滅的動作。
```

### `TestDingExceptionRequiresCornerQuotes`：三方複審分歧與主控裁決

```text
🔴 **三方判斷不一致，主控裁決採納收窄**（勿改寫成「四方一致認為」）：
  · Architect：撤回「(丁) 重開了 ARCH-R60-01③」的疑慮。
  · SD：以四發注入判定 **(丁) 沒有重開** ARCH-R60-01③——它只豁免「無 ID 因而無物可
    稽核」的提及（家族內同句仍 RED、治理文件內帶真實 ID 的失實指針仍 RED）。
  · SA：判定**重開**，理由是例外開得比需要寬、形態級模糊仍在。
**事實三方一致**（治理文件內未加引號的無 ID 散句 → rc=0），分歧純在價值判斷。
主控裁決理由：代價僅一行判準，而現存唯一 (丁) 用例本就落在「」內 ⇒ 零誤紅。
```

### `TestArchiveIndexCoverage`：R60 收輪前索引未登記事故

```text
原始缺陷：R60 收輪前人工建了 `archive_31` 卻沒登記進主檔索引段，而當時的四項判準
完全不看索引 ⇒ `--check` 照印 rc=0，主檔標題還寫死「三十檔」。**同一支閘門在同一個
session 印的是「32 檔」**（家族檔數）——兩個數字在同一份輸出裡自相矛盾而沒人被擋。
```

### `TestGovernanceDocsAreInThePointerAuditSurface`：方案(乙)裁決過程

```text
裁決過程刻意記在測試裡：主控初裁方案(乙)「立帳見＝家族專用語法、家族外禁用」，
隨後**自己推翻**——(乙) 會讓治理文件裡的指針完全失去居所稽核，而 ARCH 的證據正指出
其中一處指向的列是待 R61 承接的**活列**，一旦被搬走該句就靜默失實（與 archive_26/27
→ `DEF-101-493` 同一劇本，而 493 正是 ARCH-R60-01 的原始案例）。**把語法禁掉＝把
偵測面一起丟掉**，故改採擴面。
```

### `TestBareResidenceTokenHasAHardRequirement`：SA 完整方言普查

```text
🔴 結構論證（SA 完整方言普查）：`立帳見` 有 `POINTER_VERB` 硬要求（動詞在、後面沒跟
可解析 ID 即紅），但**真正承載居所語意的 token 是「現居」，而它先前沒有對等硬要求**。
不帶 `見` 動詞的裸 `現居 archive_NN` 於是兩道正則皆不命中 ⇒ 注入失實宣稱時 rc=0、零訊號。
磁碟現況此形態零命中（latent，非已發生），但結構上一直開著——這正是「還沒出事」與
「不會出事」的差別，本 repo 對前者的處置一律是補鎖而不是記一筆觀察。
```

### `TestCheckIsWiredIntoGates`：立此鎖的理由

```text
🔴 立此鎖的理由：`tools/` 下 7 支 `check_*.py` 全部有執行點（pre-push 守門迴圈 ＋
root-infra-ci.yml 具名 step），唯一破例就是本輪新增的這支——它兩處出現都只在
compat-ci 的 `paths:` 過濾器（觸發條件，不是執行 step）。`tools/tests/
test_root_infra_parity.py` 已守「CI 與 pre-push 兩份清單互為鏡射」，但它守不到
「兩邊同時被拿掉」，故本鎖補上「兩邊都必須有」這一面。
```

### `TestOpenBacklogArchiveIsRejected`：方向②駁回理由

```text
駁回理由不是工作量大，是它會讓孤兒偵測（`orphan_backlog_problems()` 吃主檔全文）
對未結列——唯一需要孤兒偵測的那一群——變成零檢查，且讓「帳本是 SSOT」在讀者面
失效（未結項才是每輪必讀的那一半）。R68 量化對照顯示改採①＋判準②收窄已足夠釋放
容量餘裕，不必以破壞硬規則換取更大數字，史料見證據檔〈第七輪 史料搬遷
（Dev-Trim8）〉。
```

## test_check_script_parity.py（Dev-Trim Trim-C）

### `test_uep_is_five_after_r65_migration`：UEP 逐輪遷移沿革

```text
歷史：R60 基線 8 → R61 Phase 1-B 遷移兩對至 `_THINNESS_ENROLLED` 後為 6
（公式當時是 `_EXEMPT_PAIRS` + `_TLC_TRACK_ENROLLED`）→ R65 Phase 2-A 把
run_tlc 那唯一一筆 `_TLC_TRACK_ENROLLED` 條目也升級為 hash 釘選
（不計入 UEP）後，`_TLC_TRACK_ENROLLED` 本身
退場、公式不再有該項，UEP 應為 5。
```

### `TestRunTlcInvocationParityLock`：R65 沿革與現行判準設計

```text
R65（ADR-XPLAT-002 §5 Phase 2-A）：取代退場的 run_tlc FSM 軌錨點集合鎖
（原 `_check_run_tlc_tracks`）。run_tlc.{sh,ps1} 薄殼化後兩側已不再內嵌
`.tla`/`.cfg` 檔名字面（舊鎖的抽取對象消失），但「兩側委派引數仍可能分歧」
（DEF-101-100 攔的正是這型漂移：.ps1 曾缺整條 FLEET_FSM 軌而 .sh 有）這個
風險本身沒有消失——依 ADR §4.2 rule 3 dominance test，此斷言沒有現成接手者，
改抽兩側委派 `tools.fsm_runtime.tlc_runner` 時傳的 `--module`/`--cfg` 引數
token 做同型 multiset 比對，延續同一個保護意圖，只是換一個新形態下仍存在
的錨點（fixture 注入變異，同 R12 原測試手法）。
```

### `TestR67LatestPinnedShebangCoverage`：WHY 當初另立一支與本輪合表

```text
WHY 當初要另立一支：R67 時 LATEST 釘選住在本檔的第二張表，而
`test_check_wrapper_thinness.py` 那支全面性測試只走 `_PINNED_SHA256` 的迴圈——
LATEST 那兩支不在它的射程裡，不補這條就會「主表修好、LATEST 仍在覆蓋面外」。
🔴 本輪（E-06／R77-54①）兩表合一後，那支全面性測試的迴圈**自動涵蓋** LATEST 鍵；
本類別因此改為守住「合併確實把 LATEST 帶進了那個迴圈」——刻意不刪，因為刪掉
就沒有任何東西會在「有人把 LATEST 鍵再拆出去」時說話。
```

### `TestR64TierShrinkOnlyRatchet`：本類刻意加進本檔而非新開檔案

```text
本類刻意加進本檔而非新開檔案：新開 `test_*.py` 當時會讓護欄層檔數棘輪翻紅
（DEF-101-561③，R78 起量測面已換成淨行數，但「同族判準住同一個家」的理由
仍然成立）。史料見證據檔〈第七輪 史料搬遷（Dev-Trim8）〉。
```

### `TestR13LibAndInstallerEnrollment`：WHY

```text
WHY：tools/lib/ 三支（install 共用層「異名對等品」×2＋PowerShell 專屬 helper）
過去完全在 _PAIR_SCAN_DIRS 邊界外——增刪/改名零機械訊號；install_mac_nightly.sh
（R13 ARCH-R13-3 launchd 安裝器）為新增單邊 .sh，皆須附決策依據納管。
計數註記（R13 擴充依據）：「13 對＋11 支單邊」是 R12 時期工具的動態實跑輸出、
並無任何測試釘選值鎖定該計數（enrollment 守護靠 unknown/stale 名單而非總數），
R13 擴面後實跑輸出為 13 對＋15 支單邊，無需同步任何釘選。
```

### `TestLatestThinnessRationaleIsFactual`：R79 實測病灶

```text
病灶（R79 實測）：原文聲稱 compat-CI 只跑本檔，實則兩支 workflow 各有一個
`run_root_unittests.py` step 對真樹跑全部 16 鍵——那句話是「這段不可刪」的
唯一論據，失實前提會讓下一輪架構決定建立在假話上。本鎖釘的不是散文字面而是
它依賴的四個世界事實，任一事實翻轉即紅並指名要改哪一段。史料見證據檔
〈第七輪 史料搬遷（Dev-Trim8）〉。
```

### `TestLatestThinnessPin`：R65 立、本輪改為委派沿革

```text
R65 起本鎖接手 `run_tlc.{sh,ps1}` 兩側內容未偏離的斷言，比舊鎖更嚴格
（鎖住整份正規化內容而非只比對軌 token 集合）。E-06／R77-54①：受測對象改為
`check_wrapper_thinness`（唯一實作）＋本檔薄呼叫點，斷言逐條保留作為併表的
dominance test 本體，注入面改 patch 該表與 LATEST 解析器。史料見證據檔
〈第七輪 史料搬遷（Dev-Trim8）〉。
```

### `TestLatestKeysAreCoveredByTheSingleCrossLock`：R66 DEF-101-622 承接沿革

```text
原本這裡是 `_check_latest_thinness_cross_lock()` 的專屬類別——它與
`TestThinnessCrossLock` 逐字同形，只差兩張表的名字，而這兩支存在的**唯一理由**
正是「兩份獨立字面清單會各自腐化」。判準自己複製兩份，等於把它負責攔的病帶進
守門層本身。兩表合一後只剩一份 cross-lock，本類別因此改成：證明 LATEST 鍵**確實
落在那一份的射程內**（不是「少了一支測試」，是「同一批斷言換人承接」）。
```

## test_pre_push_dispatcher.py（Dev-Trim Trim-C）

### 模組 docstring：R9 P1／R10 ARCH-1 立案沿革

```text
本 dispatcher 是 R9 P1 修復（root-infra leg：純根層變更 push 原本一個閘門都不跑，
CI 帳單停擺期間零防護）＋ R10 ARCH-1 擴充（根層消費檔 leg：aisdlc-sdd-ci.yml paths
承認的非 AISDLC_SDD/ 條目，其回歸鎖住在 AISDLC_SDD/scripts/tests，純根層 push 原本
永遠不執行它們）的核心防線，先前卻零自動化測試（tools/tests 只有 pre-commit 的
SIGPIPE 回歸鎖）。分流邏輯一旦被重構改壞——case 前綴比對寫錯、fail-safe 被
「優化」成靜默放行、消費檔 yml 解析退化成空集合、子 hook 缺失改成軟跳過——
症狀全都是「push 照樣全綠放行」，沒有任何紅燈，正是最危險的無聲復發。
```

### `test_subproject_only_change_still_runs_root_guard_fast_tier`：R69 WHY

```text
WHY：那八支守門工具（check_script_parity／check_ntfs_paths／
check_wrapper_thinness／check_defect_log_crossref …）守的全是**跨子專案**
不變式——它們的掃描面本來就涵蓋 AutoClaude/tools 與 AISDLC_SDD/scripts。
R69 前的觸發條件是「存在不在兩子專案底下的變更路徑」，於是「只改
AutoClaude/tools/xxx.ps1」這種最常見的 push，一支根層守門都不跑，CI 帳務
停擺期間等同零防護（本 repo 已有 windows-compat-ci 連 15+ 次紅的前例）。
快慢分層即取捨：快層 8 支同機實測合計約 1.0s（逐支 0.03~0.27s），一律跑；
慢層（py_compile + run_root_unittests，同機實測 111.89s）維持路徑觸發。

本鎖若被改回「只有根層變更才跑守門」，症狀是子專案 push 全綠放行、
跨專案守門靜默不執行——與 R9 P1 當年修的是同一個病，只是換一邊。
```

### `test_integration_gate_change_runs_the_gate`：R67-C18 WHY

```text
WHY（R67-C18）：tools/integration_gate.{sh,ps1,_core.py} 是 monorepo 整合層
閘門，但它在整個自動化層零呼叫端——唯二執行者是兩支已隨 CI 帳務停擺
（DEF-101-081）而多輪未跑的 compat-CI。「雲端是唯一執行者的東西＝實質已死」：
改壞閘門本體後，本機沒有任何流程會發現。本 leg 是它在本機的第一個活體執行者。
刻意用 `_core.py`（而非 `.sh`）當觸發檔，鎖住 dispatcher 的 glob 前綴比對
`tools/integration_gate*` 真的涵蓋三支，而不只認到薄殼那一支。
```

### `test_empty_stdin_failsafe_runs_all_legs`：leg 計數漂移與 fail-safe WHY

```text
R67-C18 起「全部」＝四 leg（兩子專案 + root-infra + 整合閘門）；測試名刻意不寫
死數字，避免下一次增減 leg 時名稱與內容漂移（本 repo 已多次踩到計數敘述漂移）。

WHY：pre-commit 框架等外層工具可能吃掉 hook 的 stdin；無法判定 push
範圍時唯一安全語意是全跑。fail-safe 若被「優化」成靜默放行（rc=0、
零 leg），就是整個 dispatcher 最危險的回歸模式。
```

## test_wake_chain_halt_r278.py（Dev-Trim Trim-C）

### 模組 docstring：DEF-200-278 事故沿革

```text
事故：額度守衛判 `band=halt` 後，`quota_halt_actions()` 只認 `payload["transcript_path"]`
——缺席（或雖有路徑但暫時讀不到檔）就整段放棄，任務書寫不出來、喚醒訊息卻只印一句
籠統的「拿不到逐字稿路徑」，不管真正的成因是什麼（見 §RC1）。而哨兵（`sentinel_decide`）
只認逐字稿裡的未復原撞線（429），自願停機沒有那一筆 ⇒ 永遠 `patrol` 到 6 小時後靜默
解除。兩層合起來＝reset 到了也不會有人喚醒續跑（本輪 2026-09-10 19:1x～23:11 損失
≈3h50m 的直接成因）。
```

### `HaltMarkerSelfCheckTest`：DEF-200-281／F-1 立案鑑識

```text
立案：本輪鑑識實測 `~/.autosdd/traces/halt_{96d7f386-…,8d8773f9-…,unknown}.json`
三份現場標記逐位元組相同（`at`="2026-08-09T05:15:03+00:00"／
`reset_at`="2026-08-09T08:23:03+00:00"／`resolved_source`="env-derived"），
追根究柢是 `tools/tests/test_quota_policy.py::TestR95HaltArmsOffTheEarliestResettableAxis
::test_the_halt_actions_and_message_follow_the_choice` 用模組常數
`NOW = datetime(2026, 8, 9, 5, 15, 3, tzinfo=UTC)` 呼叫 `quota_halt_actions()`，
且未隔離 `CLAUDE_CODE_SESSION_ID`／`CLAUDE_PROJECT_DIR`／`AUTOSDD_TRACE_DIR`——
在任何真實 session 裡跑 pytest 都會把這個凍結值寫進真實 sid 的 halt 標記。
```

## test_smoke_ci_sync.py（Dev-Trim Trim-C）

### `TestNightlyCarrierReferencesResolve`：具體失敗案例

```text
這道鎖要擋的**具體失敗**（本輪實測，不是假想）：登記表把兩個 CI step 指給
`AutoClaude/tools/run_local_nightly.ps1`，而該檔當時**根本沒有**那兩件事——
舊守門 `test_named_local_carriers_actually_exist` 只驗「被指名的檔案存在」，
nightly 腳本當然存在，於是這張表可以說謊而零訊號。ONBOARDING §6.1 又刻意
不再重抄、直接指向本表當唯一真相源 ⇒ 任何人拿它回答「什麼只能等雲端」都會
得到錯的答案，而雲端此刻因帳務停擺根本不會跑。
```

### `TestMacSmokeCliContract`：R69 兩道入口守門 WHY

```text
WHY 這兩件事住同一支測試：它們是同一個病灶的兩面——**這支腳本先前對「怎麼被呼叫」
完全沒有意見**。① 任何打錯的旗標（例如把 `--help` 敲成 `--hlep`）都被靜默丟棄、整套
smoke 照跑完再印綠；② 以 macOS 預設的 zsh 執行時 `${BASH_SOURCE[0]}` 未定義，腳本
目錄解到呼叫端 cwd，guard source 失敗後 `is_real_python_candidate` 變成 command not
found，於是印出**與事實相反**的「找不到 python」——使用者被指去裝一個早就裝好的東西。
```

### `TestCiStepLocalCarrierCoverage`：R67-C19 具體失敗案例

```text
這道鎖要擋的**具體失敗**：有人在 compat-CI 加一個新驗證步（例如新平台守門），本地
smoke／nightly 完全沒跟上，而 compat-CI 因帳務停擺不會執行 ⇒ 那一步實際上**從未在
任何地方跑過**，卻讓 §6.1 的「本地補償」措辭看起來仍成立。Scan-C 已實測注入證明此
情境下 56 支護欄測試（含本檔）全綠、零訊號。
```

## test_dev_start.py（Dev-Trim Trim-C）

### `_narrative_node_ids`：R71 為何把 docstring 擴出去

```text
🔴 R71 為何要把 docstring 這一層擴出去（不是為了消紅，是兩道鎖真的互斥）：
`DEF-101-762` 的鎖必須**逐字引述**生產碼的拼法才斷言得了它，而本鎖規定測試樹內
唯一合法拼法是 SSOT 那一串。該組鎖併進本檔時，它「解釋 CP950 下會發生什麼事」的
斷言訊息與 skip reason 全被判成分歧拼法（實測 8 筆命中、其他檔 0 筆）。把講解算成
複本，作者唯一的消紅路徑是刪掉講解——鎖因此反過來消滅自己存在的理由，與本檔
`TestPsUtf8PreludeIsSingleSpelling` docstring 記載的自噬是同一形狀，只是換了位置。
```

### `test_healthy_plist_passes_every_capability_row`：「健康」兩個自變數

```text
🔴「健康」在本測試裡是**兩個自變數**：能力表大多數列讀 plist 檔案內容
（`install_healthy_plist()` 全權控制），WakeToRun／NextRunTime 兩列讀
`pmset -g sched` ＝**這台機器的電源排程狀態**。夾具的 pmset stub 把第二個
自變數也收進測試手裡，兩列因此**留在**斷言內（沒被拿掉、沒被放寬成允許 ⚠️）。
只設前者時本測試在真 mac 上為何結構性必紅、又為何在 Windows 上沒人看見，
史料＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
```

### `test_fake_39_shim_is_live_so_the_version_check_is_what_rejects_it`：雙引號探測片段沿革

```text
🔴 本測試的探測片段刻意**不含任何雙引號**（第一版寫 `print("MM=%d.%d" % …)`
當場被 PS 5.1 吃掉一個引號、實測拿到 `SyntaxError: invalid syntax`）——
載具本身踩進 DEF-101-760 就會量到假紅，看起來像 shim 壞了。
改印 `sys.version_info[:2]` 這個 tuple 的預設 repr，零引號需求。
```

### `test_dispatch_only_freshness_is_reported_even_though_verdict_is_fresh`：實證來源與設計取捨

```text
實證來源（2026-08-03 唯讀 gh 實查）：`aisdlc-sdd-arch-fitness.yml` 的
schedule 軌最後成功 2026-07-14、最近一次 schedule run 2026-07-27 failure，
而 08-02 14:24 有一次 workflow_dispatch 成功 ⇒ 主判準看起來新鮮。

🔴 為何不是把 `workflow_dispatch` 移出 `_LIVENESS_EVENTS`：那樣做會讓
DEF-101-703 的死鎖復發（哨兵印的處置指令產生的正是 dispatch run，不算數
就永遠解不開）。dispatch 繼續計入主判準，遮蔽事實另立一句話。
```

### `test_deadline_stops_the_scan`：R71 訂正唯一被改動的斷言

```text
🔴 R71 訂正（本鎖唯一被改動的既有斷言，理由寫在這裡）：原本第二條是
`assertEqual(stale_schedule_tracks(...), [])`——也就是**把「沒查」與「查過、
很健康」編碼成同一個回傳值**。那正是 E-2 的病：`_scan_order` 前身是固定
字典序 ⇒ 預算截斷永遠砍掉排最後的 `windows-compat-ci.yml`（實測本 repo 7 軌
排序後它就是最後一名），而呼叫端收到 `[]`、印「排程軌正常」。
本鎖的**意圖**（不得對 probe 發動查詢、不得拖住開工）以 `assert_not_called()`
逐字保留並仍是主判準；改掉的只是「截斷必須靜默」這個附帶結果——靜默本身是
缺陷，不是要保護的行為。
```

### `test_win32_returns_none_without_spawning`：三重 mock 立案

```text
DEF-101-243③／R19／DEF-101-247③ 立案：win32 專屬案例與三重 mock 視野缺口
（原文＝Guard_Repin 證據檔 §D-3）。
```

### `test_candidate_chain_word_splits_under_zsh`：zsh 迴歸鎖立案

```text
🔴 zsh 迴歸鎖（R69 P2 自身修復過程中真的踩到）：候選鏈初版寫成空白
分隔字串 + `for c in $LIST`，在 bash 下正確、在 **zsh** 下整條清單被當成
單一候選 ⇒ 一支都命中不了。zsh 對未加引號的參數展開預設不做字詞切分
（SH_WORD_SPLIT off），而 `source tools/dev_start.sh` 的主場正是 macOS
預設 shell zsh——bash 全綠、真實入門路徑仍斷，與本輪要修的缺陷同型。
```

### `test_weekly_track_tolerates_one_skip`：R71 保留 STALE_PERIOD_FACTOR 的理由

```text
🔴 R71 保留本鎖的理由（D-5 的處置說明）：診斷把 `STALE_PERIOD_FACTOR=2.0`
列為缺陷（週頻門檻 14 天 ⇒ 結構上不可能「當場發現」）。本輪**刻意不動這個
常數**——它擋的是「單次 runner 排隊／額度抖動」造成的假紅，拿掉就回到天天
狼來了、然後被忽略（那正是 DEF-101-703 的死法）。改以**新增判準**取得當場
訊號：`_schedule_axis_note` 讓「cron 觸發後 run 轉紅」立刻出聲，不進容忍窗
（見 `test_failed_scheduled_attempt_inside_tolerance_window_still_speaks`）。
```

### `test_same_job_set_across_crons_is_not_a_blind_spot`：fixture 形狀沿革

```text
🔴 本 fixture 的形狀是被鑑別力驗證逼出來的：第一版把 `7 3` 那個 job 的 `if:`
改成 `7 2`，結果 `cron_job_map` 只剩**一個**鍵 ⇒ 走的是 `len(mapping) < 2`
的早退，**根本沒碰到**要守的「同一組 job」判準。實測：把 `all(s == sets[0])`
整條刪掉，那一版仍然全綠＝死鎖。現在兩個 job 的 `if:` 都同時列出兩條 cron，
因此 map 有兩個鍵、兩鍵的 job 集合相同——這才真的走到那條判準上。
```

### `PMSET_ONESHOT_WAKEORPOWERON`：反組譯實證

```text
#: 一次性的 **wakeorpoweron**——這才是「全文子字串比對」那個舊形態真正會吃下去的
#: 假綠，而 `PMSET_ONESHOT_ONLY`（eventtype＝`wake`）**吃不到**：`wake` 不是詞彙表
#: `wakepoweron|wakeorpoweron|poweron` 的子字串，所以那一支即使拿全文比對去跑也照樣綠
#: （本輪實測：忠實還原全文比對 → 24 tests OK，rc=0）。⇒ 沒有這一支，
#: 「一次性事件不得算數」這件事在**歷史上真的出過錯的那個形態**上是零覆蓋的。
#:
#: 🔴 這不是虛構的 OS 行為，是反組譯實證：一次性段的顯示路徑（` [%ld]  %s at %s`）
#: 在印出前先把 eventtype 原值與 `wakepoweron` 逐位元組比對
#: （`x9=0x65776f70656b6177`＝"wakepowe" ＋ `w10=0x006e6f72`＝"ron"），**相等就把顯示
#: 字串換成字面值 `wakeorpoweron`**（`csel x24, x9, x8, ne`，x8 指向 0x15d53）。
#: 重複段則不做這個代換、直印原值 ⇒ 同一個 eventtype 在兩段的渲染**不同**。
#: 使用者把 `pmset repeat` 打成 `pmset schedule` 就會落在這一格：事件跑一次就沒了，
#: 撐不起「每天 02:00 前叫醒」，但全文比對會回報「已排定」。
```

## Trim-C 本棒刻意未搬的登記

- `test_claim_provenance_r86.py` 各測試方法的 docstring：該檔模組 docstring 已明文登記
  「per-assertion 的 WHY 未搬動，仍在各 class／method 的 docstring 內」（R86 既有裁決），
  本棒沿用不重複處理。
- `test_smoke_ci_sync.py` 的「這張表的取證邊界」整段（`_NO_CARRIER`／`_PARTIAL`／`_INFRA`
  三段說明＋(a)~(d) 四款）：`test_registry_discloses_its_evidentiary_boundary` 機械要求
  該段落必須逐字留在本檔（錨點字串＋長度門檻＋四個具名 marker），搬走會讓該鎖失去比對對象，
  本棒未動。
- `test_pre_push_dispatcher.py`／`test_check_hooks_liveness.py`／`test_archive_defect_log.py`
  等檔內大量「判準①②③…」「(a)(b)(c)」列舉：那是各測試方法/類別實際覆蓋的情境清單，
  與判準當下語意同源，只搬了掛在列舉之外的歷史敘事段落，列舉本身未動。
- `test_dev_start.py` 絕大多數 MUST FIX／QA 複審類的 2-4 行短 docstring：抽樣判定它們
  已是「第一句測什麼／為何」的精簡形態，本身即無多少可搬的純史料，故未逐一處理
  （僅處理其中篇幅明顯偏長、屬事故重演或反組譯考證的十餘處）。

## 本輪刻意未搬的登記

- `test_doc_loc_baseline_freshness_r60.py::unsatisfiable_exit_criterion_problems` 的
  ①～⑤ 判準列表與「已實測涵蓋／不涵蓋」清單——那是本函式當下實際檢查範圍的規格文件，
  不是史料。
- `test_doc_loc_baseline_freshness_r60.py::hook_claim_problems` 的 ①② 兩條判準本身
  （只搬了掛在它們上面的兩段事故敘事，判準敘述留在原處）。
- `test_check_defect_log_crossref.py::TestDef200241GrandfatheringReadsLedgerClosureNotTheClock`
  的 ①～⑤ 條列——同上，是本類實際鎖住的性質列表。
- `test_block_destructive_git_r83.py` 各測試方法的 docstring：抽樣檢視後判定它們絕大多數
  直接等於「這支測試在防哪個具體回歸」，與判準當下語意同源，搬走會讓讀者失去對照，
  本輪未動（見任務回報 notes_for_helm）。
- `test_context_budget_guard.py` 模組 docstring 的「被守的四類性質」段與
  `test_no_caller_passes_the_reserved_keys_any_more` 的 Pkg-P12 事故敘事——R127 已登記
  刻意未搬（同源引述三處，收斂屬另案），本輪沿用該裁決不重複處理。
