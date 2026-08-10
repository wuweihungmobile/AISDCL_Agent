# CrossPlatform R83 掃描發現（mac 真機首輪）

> **本檔的角色**：R83 這一輪的護欄層淨額逐檔清單、以及本輪各發現的座標宣稱的唯一居所。
> 帳本列（`docs/06_quality/AutoSDD_Defect_Log.md`）受 `ROW_MAX_BYTES` 硬閘，詳情一律搬到具名證據檔、
> 列上只留指針；本檔即那個居所之一。
>
> 🔴 **體例**：本檔不寫死「當場可現查」的量測 token（`Ran <N> tests`、收集面指紋、檔數）。
> 需要數字時指向載具，讓讀者自己現查——理由見根 `CLAUDE.md`〈鐵律三〉表頭與
> `ADR-XPLAT-002` §8 表頭規則 3。例外**兩類**，各自附理由（第二位獨立驗證者補記：此處原寫
> 「唯一例外」，而 §A-1 那組讀數逐字違反它 ⇒ 一份宣告體例的段落自己就是反例）：
> ① 本檔 §B 的護欄層淨額三元組——那是 `repin_log_problems()` 款(9) **強制要求**寫出來的
> 「承認」，且與 `_GUARD_LINES_REPIN_LOG` 表尾那一列由 `doc_guard_total_problems()` 雙向
> 對帳（寫錯即紅）；② §A-1 那組**釘在具名 commit 上、在拋棄式拷貝樹裡量的**歷史讀數
> （`Ran … tests` ／ `FAILED (failures=…)`）——它們量的不是**這棵**樹，而是「動工前態」這個
> 已經不存在的狀態，所以不落在「當場可現查」那一類；它們同時是「10 支紅」這個宣稱唯一的
> 可重跑證據（配方就在同節），刪掉等於把本檔最吃重的那一節架空。

---

## §A 本輪的性質：第一次有 mac 真機

R82 之前的每一輪都在 Windows 上跑。R83 是**第一次**在 macOS 真機上完整跑完一輪，因此本輪的發現有
一個共同形態，值得單獨記下來：

> **判準把「某一台 Windows 機器上量到的值」寫成了常數，於是同一棵樹在 mac 上必紅。**

動工時根層 `run_root_unittests.py` 有一批紅，歸因後是 5 個根因，逐一都是這個形態的實例
（**逐支座標、原始失敗訊息與修法見下方 §A-1**）。**修法一律不是「把常數改成 mac 的值」**——那只是把紅
從 mac 搬到 Windows。正解有兩種，本輪兩種都用到了：

1. **換量測面，讓它平台中立**。例：EOL 棘輪由「本機工作樹位元組」換成 `git ls-files --eol` 的
   `i/` 欄（blob 是 content-addressed ⇒ 每台機器同一個值）；路徑比較由字面相等換成
   `os.path.samefile`（量的是核心回報的 `(st_ino, st_dev)`）；幽靈路徑判準由「機器檔案系統上
   有沒有這個檔」換成「repo 自己的宣告」（`git check-ignore` 合取判準 ＋ 第三態 `ignored`）。
2. **顯式雙欄，兩欄在任何主機上都跑**。例：額度計的憑證來源判準登記 `("win32", "darwin")` 兩欄，
   各自登記「憑證住哪裡」與怎麼把它鋪成讀得到／讀不到，並斷言兩欄的「讀不到」必須是**不同**字面。
   體例比照 `ONBOARDING.md` §7 的兩欄基線。

**刻意不用的第三種**：加 `skip`。那等於讓該平台永遠沒有覆蓋，而本輪的 skip 治理正好在往反方向走
（見 §C）。

---

## §A-1 動工時那批紅：重現配方、根因分群、與「治本 vs 拔判準」的判準

> 🔴 **本節為何存在**：R83 交件版把這批紅的逐筆座標指向「帳本 `DEF-200-*` 系列」，而四方複審中
> **兩位獨立複審者各自逐列讀完該族後證偽**（QA F-1／falsified【1】；SA-03／falsified 3）——當時該族沒有任何一列
> 是這批紅。⇒ 本輪最吃重的宣稱（「10 支 mac 紅全部治本」）當時在磁碟上**沒有可稽核標的**，
> 複審者因此無法完成「逐支確認是治本而不是拔判準」這件事。
>
> 🔴 **分工（本節不是第二個家）**：收斂輪之後**逐支處置與狀態的家是帳本 `DEF-200-030`~`DEF-200-039`
> 十列**（帳本包同輪落地，列上帶測試全名／原始訊息逐字／根因標籤 P1~P5／修法／「修後由哪一支測試守同一件事」）。
> 本節保留的是帳本列**放不進去**的三樣東西：①**重現配方**（可重跑，見下）②**根因分群的盤點**
> （5 個根因怎麼對上 10 支）③**「治本 vs 拔判準」的判準**（下表第 6 欄）。
> 兩處的逐支資料若哪天分岔，**以帳本列為準**——它受 `check_defect_log_crossref.py` 的格式／狀態／承接輪次閘門，本節不受任何機械物。
>
> 🔴 **本節的數字是收斂輪重現出來的，不是轉載**。重現配方要**兩個載體**（這件事本身就是本節最要緊的一課）：
>
> ```bash
> # 載體一：HEAD 的乾淨拷貝樹 → 重現 9 支
> git worktree add --detach <拋棄式路徑> HEAD          # HEAD = R82 收輪 commit 7975140
> cd <拋棄式路徑> && <主樹>/.venv/bin/python tools/run_root_unittests.py
> # 載體二：HEAD 版判準 × **主工作樹**當 repo_root → 重現第 10 支（下表第 10 列）
> ```
>
> 載體一當回合實測逐字：`Ran 2876 tests in 330.082s` ／ **`FAILED (failures=9, skipped=44)`** ／ `RC=1`。

🔴 **支數：10 支全部歸因（此段是獨立驗證輪的訂正，原判斷逐字保留在下一段當史料）**。
獨立驗證輪把「乾淨拷貝樹上只有 9 支」的成因**測出來**了，不再是兩個未證實的假設：第 10 支
（`test_doc_loc_baseline_freshness_r60.TestR81GhostPathClaims.test_the_baseline_is_not_stale`）的判準吃的是
**gitignored 機器本地生成物存不存在**，乾淨拷貝樹裡那些檔一個都沒有 ⇒ 該支在那裡是**綠的**。
換載體即重現：以 HEAD 版該模組的 `stale_path_baseline_problems()` 對**主工作樹**求值，獨立驗證輪當回合實測
**1 筆**，逐字＝`AISDLC_SDD/.claude/settings.local.json 已在基線豁免表上，但它現在解析得到了`。
⇒ **「10」這個數字成立**，5 個根因對得上 10 支（見下方歸因盤點）。

> 🔴 **收斂輪原判斷（逐字保留，因為它錯的方向是要學的）**：「重現出來是 9 支…差的那 1 支**未歸因**，
> 不湊數…② 下表第 7、8 兩支的判準讀的正是『工作樹行尾』這種**不受 git 追蹤**的狀態 ⇒ 那一軸的動工前態
> **原理上不可回溯**。⇒ 本表寫 9 支 ＋ 1 支未歸因，**『10』這個數字本輪未能重現**。」
> **錯在哪裡**：它列的假設① 就是正確答案（「動工時的量測取自主工作樹」），卻沒有花那幾秒鐘去試——
> 而把「我沒試」寫成了「原理上不可回溯」。本 repo 對這個形態已有明文禁令（做不到 ≠ 結構上不可能）。
> **仍然成立的那一半**：下表第 7、8、9 三支（不是兩支）確實吃工作樹行尾這個不受 git 追蹤的軸
> （`git status` 結構上看不見它，見根 `CLAUDE.md`〈鐵律三〉`.py` 行尾那一格）；它們與第 10 支的方向**相反**——
> 第 7~9 支在乾淨樹上**是紅的**（下界釘在 Windows 工作樹量到的值，乾淨樹量到 0 ⇒ 判準要求重釘），
> 第 10 支在乾淨樹上**是綠的**。「換一棵樹就換一組紅」正是這 5 個根因的共同形態。

| # | 測試全名（HEAD 版） | 原始失敗訊息（重現實測，節錄逐字） | 根因 | 修法座標（本輪 diff） | 修後該判準守什麼 |
|---|---|---|---|---|---|
| 1 | `test_check_hooks_liveness.TestHookLauncherContract.test_stdin_argv_and_cwd_match_the_old_shim` | `AssertionError: PosixPath('/private/var/folders/…') != PosixPath('/var/folders/…') : cwd 必須被切到 CLAUDE_PROJECT_DIR` | **② 路徑比較用字面相等**（macOS 的 `/var` 是 `/private/var` 的 symlink ⇒ 同一個目錄有兩個合法字面） | 新增 `_same_path()`（問檔案系統不問字串，`os.path.samefile`）＋ 其**非空虛性自證**；Windows 側對等物改走 `mklink /J` 目錄 junction（不需權限） | 仍守「launcher 必須把 cwd 切到專案根」這件事本身（P0 不變），只是改成問核心回報的 `(st_ino, st_dev)`。**不是**把斷言拿掉，也不是加 skip |
| 2 | `test_context_budget_guard.MeterFailureShapesTest.test_unreadable_credentials_and_http_401_are_different_answers` | `AssertionError: Tuples differ: (None, 'http-401') != (None, 'no-credentials')` | **④ 額度計憑證來源寫死成 Windows 那一個家** ⇒ mac 上鋪不出「讀得到憑證但被 401」這個狀態，兩種失效塌成同一個 | 憑證來源改為可注入；判準改成 `_CRED_COLUMNS = ("win32", "darwin")` **顯式雙欄矩陣**，各欄自報「憑證住哪裡」＋怎麼鋪成讀得到／讀不到 | 仍守「憑證讀不到 ≠ HTTP 401」這個鑑別力，且**兩欄的『讀不到』字面必須不同**（新增的斷言）⇒ 比修前更嚴，不是放寬 |
| 3 | `test_dev_start.TestMacNightlyPlistCapabilityTable.test_healthy_plist_passes_every_capability_row` | `AssertionError: '項與期望不符' unexpectedly found in '✅ launchd 已載入…'` | **⑤ mac launchd 能力表把兩個自變數綁成一個**：「plist 檔案內容」與「這台機器的 `pmset` 電源排程狀態」——後者需 sudo 才排得出來 | 兩者拆成獨立自變數；新增 **stub `pmset` 三態**（健康／未排／不可用），預設姿態＝健康 | 仍逐列驗每一個能力鍵（`RunAtLoad`／`StartCalendarInterval`／退出碼…），只是不再隱含要求「跑測試這台 Mac 剛好排過 `pmset repeat`」 |
| 4 | `test_dev_start.TestMacNightlyPlistCapabilityTable.test_status_prints_exactly_the_rows_static_extraction_predicts` | `AssertionError: False is not true : 健康 plist 的每一列能力都應為 ✅，實得：[…]` | 同 ⑤（同一組自變數綁定的第二個表徵） | 同上 | 仍守「靜態抽取預測的列 ≡ 實際印出的列」這個等式 |
| 5 | `test_doc_loc_baseline_freshness_r60.TestR81GhostPathClaims.test_no_ghost_path_claims` | `AssertionError: Lists differ: [4 筆] != []`；首筆逐字 `docs/04_planning/R75_HANDOFF.md 指名一個不存在的路徑 \`AutoClaude/.g0_readiness.json\`` | **③ 幽靈路徑判準問「這台機器的檔案系統上有沒有這個檔」**——而 gitignored 的**每晚重生量測檔**在不同機器上答案不同 | 判準改成問 **repo 自己的宣告**：`git check-ignore` 合取判準 ＋ **第三態 `ignored`** | 仍守「文件不得指名不存在的路徑」（讀者照抄會撲空），但「不存在」的定義由機器狀態換成 repo 宣告 ⇒ 兩平台同一個答案。**豁免表仍是 shrink-only** |
| 6 | `test_doc_loc_baseline_freshness_r60.TestR67R3ThisFileMakesNoUnstatedPlatformAssumption.test_every_lock_in_this_file_holds_under_every_simulated_platform` | `AssertionError: {'darwin': [...]} != {}` ＋ 逐字「本檔有鎖的結果隨 `sys.platform` 改變 ⇒ 它對『本機是哪個平台』做了未言明的前提假設」 | 同 ③ 的**後設鎖**：它就是專門用來抓「未言明平台前提」的那道鎖，而被抓到的正是第 5 支 | 同上（第 5 支修好，這支自然回綠）＝該後設鎖**有鑑別力的證據** | 仍守「本檔每一道鎖在任一模擬平台下結果相同」。修法明文拒絕加 skip（訊息逐字：「修法不是加 skip，那等於讓該平台永遠沒有覆蓋」） |
| 7 | `test_platform_neutral_paths.TestActiveSourceEolIsRatchetedSeparatelyFromTheFrozenSurface.test_active_surface_python_eol_does_not_grow` | `活躍面 .py 行尾漂移：實測 0 已低於重釘下界 189（上限 220）⇒ 欠債已清掉一大截，請把上限重釘為 0` | **① EOL 棘輪量的是「本機工作樹位元組」**——那是 checkout／smudge 的產物，每台機器不同，且 `git status` 看不見 | 判準拆成**兩個平面**：①`blob_eol_offenders()`（讀 `git ls-files --eol` 的 **`i/` 欄**＝content-addressed，零容忍、平台中立）②`checkout_local_debt_verdict()`（本機工作樹健康度，只在 `actual==0` 放行、附四點紅綠自證） | 平面①是**新增**的零容忍閘門（含「`i/` 欄解析不出來也算違規」的 fail-open 反向釘）⇒ 淨變嚴。平面②守本機健康度且**下界會咬**（欠債清完就要求重釘為 0，正是本支紅在講的事） |
| 8 | `test_platform_neutral_paths.TestActiveSourceEolIsRatchetedSeparatelyFromTheFrozenSurface.test_the_repo_wide_scale_is_measured_not_quoted` | `AssertionError: 0 not greater than 0 : 全庫零漂移？請確認取數管道（本判準不該恆綠）` | 同 ①（這支是取數管道的**非空虛性**自證） | 同上 | 仍守「這條判準不得恆綠」＝取數管道壞掉時要出聲，不是靜默放行 |
| 9 | `test_platform_neutral_paths.TestShebangImpliesLfLineEndings.test_no_new_shebang_file_carries_a_non_lf_line_ending` | `AssertionError: Lists differ: [] != ['AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/arch_fitness.py']` ＋ 逐字「少掉的是已修好（請自 `_SHEBANG_NON_LF_ACTIVE_DEBT` 刪除——欠債清單不得靠慣性活著）」 | 同 ①（shebang × 非 LF 的交集面，同一個取數軸） | 同上（登記面隨取數面一併訂正） | 仍守「shebang 檔不得帶非 LF 行尾」（`\r` 會黏進直譯器名 ⇒ mac/Linux 上 rc=127），且**欠債清單雙向**：多出來即紅、少掉也要紅 |
| 10 | `test_doc_loc_baseline_freshness_r60.TestR81GhostPathClaims.test_the_baseline_is_not_stale` | `基線豁免表已 stale：AISDLC_SDD/.claude/settings.local.json 已在基線豁免表上，但它現在**解析得到**了——請把這一筆從 _GHOST_PATH_BASELINE 刪掉，否則餘裕會變成日後的破口`（獨立驗證輪以 HEAD 版判準對主工作樹求值，實測 1 筆） | 同 ③（同一個判準家族的第三個表徵：**豁免表的 stale 自檢**也吃機器檔案系統 ⇒ 跑過 G0／開過 Claude Code 的那台機器紅，別台綠） | 同上（第三態 `ignored`）＋ 該筆自豁免表移除（gitignored 生成物不是欠債） | 仍守「豁免表不得靠慣性活著」（登記的每一筆都必須**仍然**解析不到），只是「解析不到」的定義由機器狀態換成 repo 宣告 ⇒ 兩台機器同一個答案 |

**逐支對到帳本列**（1:1，非單調，故不排成表格欄）：第 1 支＝`DEF-200-030`／第 2＝`DEF-200-031`／
第 3＝`DEF-200-032`／第 4＝`DEF-200-033`／第 5＝`DEF-200-034`／第 6＝`DEF-200-036`／第 7＝`DEF-200-037`／
第 8＝`DEF-200-038`／第 9＝`DEF-200-039`／第 10＝`DEF-200-035`。帳本列的 P1~P5 標籤即下方五個根因
（P1＝②｜P2＝④｜P3＝⑤｜P4＝③｜P5＝①）。

**歸因盤點**：10 支**全部歸因完畢**，恰好落在 5 個根因上——
① EOL／shebang 取數面 ×3（第 7、8、9 支）｜② 路徑字面比較 ×1（第 1 支）｜③ 幽靈路徑判準家族 ×3（第 5、6、10 支）｜
④ 額度憑證單欄 ×1（第 2 支）｜⑤ launchd 能力表自變數綁定 ×2（第 3、4 支）。
⇒ **「10 支紅／5 個根因」這個宣稱成立且可逐支對上**（獨立驗證輪訂正：收斂輪一度把它降級成「9 支＋1 支未歸因」，見上方史料段）。

🔴 **「治本 vs 拔判準」的判準（本表第 6 欄的存在理由）**：本輪 10 支的修法**沒有一支**是
「把常數改成 mac 的值」「改成不比較」「加 skip」或「放寬棘輪」——四支的淨效果是**變嚴**
（第 1／2／7 支各新增了一道原本不存在的斷言或閘門面；第 10 支把幽靈路徑豁免表的天花板由
**18 壓到 17**——獨立驗證輪逐字現查 `_GHOST_PATH_BASELINE_CEILING`：HEAD 版 18、現行 17，且該筆已自表內移除
⇒ 豁免面**縮小**，是收緊不是放寬）。這一點可由第 6 欄逐支重驗；
與「全樹今天是綠的」是**兩件不同的事**（後者證明不了前者，同本 repo 的 `test_ps1_bom.py` 判例：
檔案在、綠的、守的是別的東西）。

---

## §B 護欄層淨額（`repin_log_problems()` 款(9) 強制的承認）

<!-- guard-total:R83 --> **本輪護欄層累積淨額＝ 73823 → 79083（+5260）** `[收尾重釘後、所有包停工的單人窗口當回合實測]`

🔴 **[非淨減法輪]**，且這是 `_GUARD_LINES_REPIN_LOG` 歷來最大的一筆淨額。照實記，不粉飾。

🔴 **本節 B-1／B-2 兩張表是收尾重釘後由取數管道重生的，不是手抄**（重生法見下方「重生法」小節）。
上一版（收斂輪定稿版）的三元組是 `73823 → 78278（+4455）`，那個值在寫下時為真、其後被
收尾重釘取代 ⇒ 差額 **+804** 的去向逐筆交代在下方「重生前後的差額去哪了」。

### B-1 逐檔漂移（既有檔，按淨額遞減）

| 檔 | 前 → 後 | 淨額 | 成長來源 |
|---|---|---|---|
| `test_context_budget_guard.py` | 5066 → 5644 | **+578** | 四件事疊加：① 額度計憑證來源改為可注入（`quota_meter.token_detail`），失效形態判準改成 `win32`／`darwin` **顯式雙欄矩陣**（`DEF-200-031`）；② `QuotaHaltMessagePointsAtThisPlatformTest`——halt 訊息必須指向**本機那個載具**的取證指令（後端層已有鎖，但「那三句話真的出現在使用者讀到的訊息裡」是另一件事）；③ `TraceIsolationTest`——跑測試不得寫進**生產的**降級觀測面（該類別立案段自陳的實測，收輪包已逐字覆核在 `test_context_budget_guard.py:3472`／`:3485`：真機暫存目錄的 `autosdd_quota_degraded.jsonl` 撈到 **17 列**假 `source=no-cache`，且測試消耗掉真的 per-source TTL 閂鎖〔TTL **180 秒**〕⇒ 跑完測試後 180 秒內 production 真降級時 `note_degraded()` 回空字串＝**一聲不出**）；④ `QuotaGateIsWiredToTheBurnPathTest`——額度那把尺此前只在 PreToolUse 通電 |
| `test_doc_loc_baseline_freshness_r60.py` | 6472 → 6924 | **+452** | 幽靈路徑判準新增第三態 `ignored`（`git check-ignore` 合取）：量測面由機器檔案系統換成 repo 自己的宣告；豁免表天花板 18 → **17**（縮小＝收緊）。`DEF-200-034`／`035`／`036` 三列的共同修法 |
| `test_dev_start.py` | 6774 → 7066 | **+292** | mac launchd 能力表把「plist 內容」與「機器 `pmset` 狀態」拆成兩個自變數（`set_pmset()` 測試縫 ＋ 三態語料）；另加 `TestMacNightlyPmsetMarkerIsNotProse`（安裝器不得釘一個 `pmset` 從不印出的散文錨）。`DEF-200-032`／`033` |
| `test_platform_neutral_paths.py` | 5683 → 5959 | **+276** | EOL／shebang 判準拆成 blob（`ls-files --eol` 的 `i/` 欄，每機同值 ⇒ 平台中立零容忍閘門）與工作樹（本機健康度）**兩個平面**；反空轉載體換成兩平台皆非零的正控。`DEF-200-037`／`038`／`039` |
| `test_check_hooks_liveness.py` | 2578 → 2829 | **+251** | `os.path.samefile`（比 `(st_ino, st_dev)`）取代字面路徑比較，治 mac `/var`→`/private/var` symlink 兩個字面（`DEF-200-030`）；＋ `TestSamePathIsNotVacuous` 非空虛性自證；＋ `_REGISTRATION_BASELINE` 回填 `block_destructive_git.py`（`{Bash, PowerShell}`） |
| `test_run_root_unittests.py` | 1975 → 2177 | **+202** | `ProblemReportItemizationTest`：「表頭報 N 筆、明細只印其中兩類」的回歸鎖。修前七個 problems 類別中，`掃描面為空` **從頭到尾沒有任何一段程式碼印它**，而既有測試只讀回傳值、把 stderr 丟進垃圾桶 ⇒ 結構上看不到 |
| `test_quota_policy.py` | 1416 → 1557 | **+141** | `TestM8bCacheHomeStaysInSync`——檔案契約的**路徑**那一半（R82 只鎖了 schema；meter 與 adapter 因 importlinter 契約不能互 import，複本是設計上必要的，正因必要才需要鎖）；＋ `TestMeterReasonsAreAllRegistered`——失效字面登記面的分母改為**現查** meter 的 `REASON_*` 宣告集合 |
| `test_schedule_capability_parity.py` | 595 → 631 | **+36** | 基底鏈**不動點**解析（同檔內遞迴到 `TestCase`）——舊判準只比基底字面，把 `test_block_destructive_git_r83.py` 的 `_ForeignTreeCase` 三個子類（實測貢獻 16 支真的在跑的測試）誤判為未接線；＋ `_SCAN_FLOOR` 46 → **48**（下限上修＝收緊） |
| `test_adr_xplat001_c1c2_lock.py` | 4768 → 4787 | **+19** | 本輪重釘的稽核痕跡列（`_GUARD_LINES_REPIN_LOG` 的 R83 那一列）與 `_FROZEN_GUARD_LINES` 三支新檔的鍵 |
| `test_doc_env_prefix_platform_parity_r60.py` | 332 → 341 | **+9** | `useMacWin.md` 納入「已知站點仍被 fence 解析器看到」清單（該檔新增 ONBOARDING §7.1 最短路徑）；並訂正原註解「該檔本就 0 站點」——該檔自本輪起有 1 個站點，下限判準靠的是 `1 < _MIN_PREFIX_SITES` 而非「恰好是 0」 |
| `test_subprocess_encoding_hygiene.py` | 1575 → 1581 | **+6** | `tools` 樹掃描面下限 92 → **110** 的重釘註解（該樹由 112 支長到 116 支，92 只還守得住 79%；110 ＝ 116×0.95 由 `tree_count_verdict()` 逐字給出）。方向是收緊 |

**B-1 合計 ＝ +2262**（十一列，零遺漏——列數等於「兩版 `_FROZEN_GUARD_LINES` 都有該鍵但值不同」的鍵數，
以下方「重生法」的 AST 集合差現查得出）。
🔴 **這裡刻意不寫 `guard_line_drift()`**：那個函式比的是**凍結表 ↔ 工作樹**，收尾重釘後恆為空
（現查「逐檔漂移 0 支」）⇒ 拿它當本表的佐證會是一句聽起來很硬、實際永遠為真的空話。
本表的基準是 **HEAD（R82 基線）**，那是另一個比較對。

### B-2 新增檔

| 檔 | 行數（＝`_FROZEN_GUARD_LINES` 該鍵；新檔整支計入） | 立案理由 |
|---|---|---|
| `test_mac_endurance_r83.py` | **1488** | mac launchd 續航後端（`tools/lib/schedule_backend.py`）的回歸鎖。立案＝續航鏈在 mac 上**整條缺席**，且缺席的表徵是綠的（`--arm-sentinel` 印「只在 Windows 成立」卻回 rc=0）。🔴 **1488 而非收斂輪定稿時的 777**：該檔在收斂期間被續寫（現含 **13 個 module-level 測試類別**——收輪包以 AST 現查 `ast.ClassDef`：module-level **13**、含縮排的內嵌類別共 14，本欄取前者；涵蓋「`select()` 是唯一的平台問句」／載具原語只有一個家／三後端介面對稱／回收臂接線／憑證鍵單一家／mac 憑證／武裝不得無回讀即宣稱／自我解除／曆時刻真的抵達 plist／延後動作等軸），逐檔清單重生時取的是凍結表的現值 |
| `test_block_destructive_git_r83.py` | **818** | 毀滅性 git 指令阻斷器的回歸鎖。立案＝本輪真實事故（見 §D） |
| `test_skip_discoverability_r83.py` | **691** | 「文件與錯誤訊息裡的示範指令只在單一平台成立」的掃描器。立案＝PG DSN 守衛的「修法」只印 `$env:…` |

**B-2 合計 ＝ +2997**（三檔）。

**消失的檔＝0 支**（收尾重釘的凍結表對 HEAD 版逐鍵相減，只在 HEAD 有的鍵是空集合）。
這一格必須明文交代而不是留白：鍵消失＝**刪鎖**，本 repo 視為分子下降、方向與棘輪相反，
所以「今天是 0」本身是要記下來的結論，不是沒事發生。

### 🔴 自我對帳式（讓下一個人一眼看得出有沒有漏交代）

```
B-1 逐檔淨額之和  +2262
B-2 新增檔行數之和 +2997
消失的檔           0
────────────────────────
合計              +5260  ＝ §B 頭那一行（帶本輪標記者）的淨額，79083 − 73823
```

三個加數與那一行的淨額**必須逐字相等**。不相等時，差額就是「沒有交代的行數」——
R83 交件版正是在這裡漏了 195 行（見下方史料），而當時沒有任何東西轉紅。

> 🔴 **上面那一行刻意寫「帶本輪標記者」而不逐字寫出「`guard-total:` ＋輪號」那個完整字面**——
> 那個字面**就是判準的觸發條件**（`_GUARD_TOTAL_MARK_RE`），寫在敘述裡會讓這一行也被當成
> 一筆「引用現行累積總量」的宣稱，而它讀不出三元組 ⇒ 判 `[形態不符]`。
> **這不是理論風險：本包寫這張對帳表時逐字踩過一次**，收輪當回合實測紅燈訊息
> 「`CrossPlatform_R83_Scan_Findings.md:168` 帶著 …標記，卻讀不出三元組」，
> 移除該字面後轉綠。同一條警語在磁碟上早有前例（收輪包現查 `grep -rn '不逐字寫出'`）：
> `AutoSDD_improving_106.md` **2 處**、`CrossPlatform_R82_Scan_Findings.md` **3 處**，
> 最早可追到 `CrossPlatform_R76_Scan_Findings.md`（該處記的正是「已經為自家標記寫過同一條理由，
> 卻在別處照踩」）。🔴 **本段初稿寫的是「`AutoSDD_improving_105`／`106` 兩份各留一句」——那是假的**
> （`improving_105` 現查 **0 處**；命中集是上面那三份）。**在一段專門講「別寫錯」的訂正文裡寫錯來源，
> 正是本輪最大宗的那個形態，所以原話不刪、留為判例。**
> ⇒ **警語至少留了三輪、五處以上，還是有人（本包）照踩，而且踩的是同一格**——
> 這是「散文警語對下一位作者零攔阻力」最直接的一筆實證：能攔住它的只有那道判準本身
> （而判準的掃描面今天不含 ADR 目錄，見 §F 第 2 點）。

**重生法（權威源，零手抄）**：

```bash
.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines   # 工作樹側／重釘草稿
git show HEAD:tools/tests/test_adr_xplat001_c1c2_lock.py                          # R82 基線的 _FROZEN_GUARD_LINES
```
把兩版的 `_FROZEN_GUARD_LINES` 都以 `ast` 解析成 dict 再做集合差：**兩邊都有鍵且值不同**→ B-1；
**只在工作樹有鍵**→ B-2；**只在 HEAD 有鍵**→ 刪鎖，必須明文交代。
🔴 **不要看 `--print-guard-lines` 的 `DIFF` 行來重生本表**：收尾重釘之後凍結表＝工作樹
⇒ 那一行必然是「逐檔漂移 0 支」，看它會得到「本輪什麼都沒長」的假結論。逐檔淨額的基準是
**R82 基線（HEAD）**，不是重釘前的凍結表。

### 🔴 重生前後的差額去哪了（+4455 → +5260，差 +804）

收斂輪定稿版的兩張表逐項合計 **+4455**，收尾重釘後為 **+5260**。差額 **+804** 全部落在兩格，
逐筆對得起來（`git diff HEAD` 與凍結表逐鍵可覆核）：

| 格 | 定稿版 | 收尾實測 | 差 | 原因 |
|---|---|---|---|---|
| `test_context_budget_guard.py` | +485 | **+578** | **+93** | **未交代**——定稿後該檔確實又被續寫（+93 行），但「這 93 行是哪幾個類別」在磁碟上查不到：該檔是 tracked 檔，`git diff HEAD` 只給得出「相對 R82 的總增量」，拿不到「相對定稿那一刻」的切片，而定稿當時沒有留下 commit 或快照。🔴 依本檔體例，寧可寫未交代也不猜一組類別名（猜對猜錯讀者都無從分辨）——**未交代本身就是一筆 finding**：它的成因是「收斂期間的中途值沒有可比較的基準」，與 §E 第 1 列同源 |
| `test_mac_endurance_r83.py` | 777 | **1488** | **+711** | 定稿當回合該檔正被另一個收斂包續寫（定稿版自己已在「收輪窗口必讀」預告過這一格會分岔）。同上：確切是哪幾個類別在定稿後才進來，同樣**未交代**（該檔為 untracked，連 `git diff` 都沒有基準可比） |
| 其餘 12 格 | — | — | 0 | 逐格相等（B-1 十一格 ＋ B-2 三格 ＝ 14 格，扣掉上面兩格） |

93 ＋ 711 ＝ **804**，與兩版總量之差逐字相等 ⇒ **總量層面沒有第三個未交代的來源**
（逐類別層面的兩筆未交代見上表，那是另一個粒度的缺口，不影響本式）。

🔴 **史料保留：本表 R83 交件版有三處與磁碟不符，四方複審四個獨立來源同時抓到（Architect A-03／F-1、F-2；SA-04；QA F-9）**——原值一併記下，因為「錯在哪個方向」本身是要學的東西：

- `test_context_budget_guard.py` 交件寫 `5066 → 5411（+345）`，收斂輪實測為 `5066 → 5551（+485）`＝當時**低報 140 行**（收尾實測已是 `5066 → 5644`，見上表）。這一檔正是額度／續航／排程整族的鎖檔，也就是最該被辯護的那一格。
- **漏列兩檔**：`test_schedule_capability_parity.py +36`、`test_adr_xplat001_c1c2_lock.py +19`（合計 55 行零交代）。
- ⇒ 交件版 B-1（9 列）＋ B-2（3 檔）逐項只交代 **4,260**，缺口 **195**＝140 ＋ 55。**與 ADR-XPLAT-006 §6 交件版那個「現查」值的偏差逐字相等**（同一份錯帳被抄到兩個地方，不是兩個獨立筆誤）。
- **為何沒有任何東西轉紅**：`doc_guard_total_problems()` 只判「帶 `guard-total:<輪號>` 標記那**一行**」的總量與算術（該函式 docstring 自己劃界：「不保證作者把每一個該標的地方都標到了」）⇒ 逐檔攤分在射程外。總量對、攤分錯 ⇒ 結構上恆綠。**這是本輪已知未關的缺口，登記在 §E**。

> 🔴 **收輪窗口必讀——本表與 §B 頭那一行的對齊基準是 `_FROZEN_GUARD_LINES`（凍結表），不是工作樹**。
> 兩者在收斂期間**會**分岔（收斂輪定稿當回合就已分岔，`guard_line_drift()` 非空、漂移集中在
> `test_mac_endurance_r83.py`）；**收尾重釘之後兩者相等**，這正是重釘的定義，
> 而它同時意味著 `--print-guard-lines` 的 `DIFF` 行從此是空的（見上方「重生法」的紅字警語）。
> 現查：`.venv/bin/python -m unittest discover -s tools/tests -t tools/tests -p 'test_adr_xplat001_c1c2_lock.py'`
> （末行 `[Scan-H triplet]` 的 `GLC_LINES`＝工作樹側）對上 `sum(_FROZEN_GUARD_LINES.values())`（＝凍結表側）。
> **這件事照實記在這裡，而不是等它靜默過期**：§B 頭那一行受 `doc_guard_total_problems()` 對帳
> ⇒ 收輪重釘凍結表時它會**強制**被改；但**本節的逐檔表沒有任何機械物**（見 §E 第 1 列）
> ⇒ 它會靜默留在舊值。**因此：重釘 `_FROZEN_GUARD_LINES` 的那一次，必須同輪重生本節 B-1／B-2 兩張表**，
> 逐檔值直接取重生法的輸出，不要手抄。這是本輪已實證會出錯**兩次**的那個動作
> （交件版三格全錯、漏兩列、低報 140 行；收斂輪定稿版又有兩格隨後過期）。

🔴 **B-2 交件版三格全部失準**（`~600`／`~780`／字面 **`~?`**），收斂輪逐檔訂正為 777／818／691，
收尾重釘再訂為 1488／818／691。其中 `~?` 是**未填的佔位符**——它出現在一份交件文件裡，
而這張表的存在理由正是「誠實記護欄層淨額」。
本表改記精確值而非量級：這三個數字**同時也是 `_FROZEN_GUARD_LINES` 的值**（新檔整支計入，棘輪對新檔不認「增量」），
所以它不是第二個家，而是同一個量的可對帳轉載——寫錯即與上方自我對帳式不符。

### B-3 誠實劃界（兩點，都對本輪不利）

1. **依成熟度 SSOT 的 M1 判準，達標條件是本表總量連續三輪不上升**——本輪 **+5260** 是明確的反方向。
   M1 因此比動工前更遠，這件事**不因為「成長有正當理由」而改變**。成熟度評估照此結算。
   🔴 **本格原寫 +4455**（收斂輪定稿值），收尾重釘後為 +5260 ⇒ 結論方向不變、幅度更大。
   這一格刻意不改成「見上方那一行」：M1 判的是**方向與幅度**，而幅度就是那個數字本身；
   同一份文件裡它只有一個家（§B 頭那一行）受機械對帳，本格是它的敘述引用，重釘時一併改。
2. **針對本輪修復的第三方複審在本檔落地時尚未執行**：配額 5 小時桶達 83%，四方複審依節流演算法
   延到 reset 後 ⇒ 依 M3「作者自證不計分」，`_GUARD_LINES_REPIN_LOG` 的 R83 那一列屬**中途值**，
   複審收斂後必須再釘一次。
   🔴 **第二位獨立驗證者訂正上一句（原話逐字保留，它在寫下的那一刻為真）**：複審**其後已執行**
   （四方裁決與筆數見 §G）。收斂輪把同一句假話在 §E 第 4 列與 `AutoSDD_improving_107.md` §5／§2
   都訂正了，**唯獨漏掉本格**——於是本檔在 §G 說「複審已執行」、在 §B-3 說「尚未執行」，同一份
   文件自己互相矛盾，而只讀 §B 的人會結算出「本輪零獨立眼睛」。**結論方向不變且更緊**：複審只為
   *部分*修復提供了第一雙獨立眼睛（複審者自陳仍有數組零獨立覆蓋），而「中途值」那條規則不但仍
   成立、還多了一個理由——收斂輪與各獨立驗證輪本身又改動了護欄層鎖檔 ⇒ **收尾必須再釘一次**，
   且那一次要在所有包停工後做（現查差值的指令見上方「收輪窗口必讀」，本格不寫死它）。

### B-4 同輪其餘重釘（方向皆為收緊）

| 站點 | 前 → 後 | 判準指示 |
|---|---|---|
| `skip_tag_policy._TREE_FILE_FLOORS['tools/tests']` | 46 → **48** | `tree_floor_problems()` 第三向「下限已過期」逐字指示 |
| `skip_tag_policy._TREE_FILE_FLOORS['AutoClaude/tests']` | 205 → **208** | 同上。成長來源＝本輪新建的三支 AC target 整合測試（見 §1 訴求 5 那一列） |
| `test_subprocess_encoding_hygiene` 的 `tools` 掃描面下限 | 92 → **110** | `tree_count_verdict()` 腐化上界逐字給出 110（＝116×0.95） |
| `test_check_hooks_liveness._REGISTRATION_BASELINE` | +1 條 | 回填 `block_destructive_git.py`（`{Bash, PowerShell}`） |
| `test_ac_matrix_scaffolding._AC_TARGET_PENDING_CEILING` | 3 → **0** | `_AC_TARGET_PENDING` 由三個 target 收成 `frozenset()`＝欠債清零，天花板同步壓到 0 |

上列皆為**下限上修／上限下壓**＝對「掃描面或欠債面靜默放大」的鑑別力變強，與「不准為了讓數字好看而
放寬棘輪」那條禁令方向相反（那條禁的是**放寬**）。

🔴 **本節交件版寫「另外**三筆**」＝低報**（SA-12 抓到，收斂輪複驗為真：`git diff tools/lib/skip_tag_policy.py`
逐字可見 `"AutoClaude/tests": 205 → 208`；`git diff AutoClaude/tests/contract/test_ac_matrix_scaffolding.py`
逐字可見 `_AC_TARGET_PENDING_CEILING = 3 → 0`）。低報與過報一樣貴：它讓「本輪動了哪幾個棘輪」這個
治理問題拿到假答案。**本表刻意不再自報筆數**——筆數是會漂移的量測值，判準是「未提交 diff 內方向為
收緊的常數變更」，現查：`git diff -U0 | grep -E '^[-+].*(FLOOR|CEILING|MIN|BASELINE)'`。
另有兩筆重釘**各自有自己的家、刻意不在本表**：護欄層總量（§B 頭那一行）與 `MIN_TESTS`（`ONBOARDING.md` §7 表①）；
`skip_group_policy._MEASURED_RUNNERS_MIN 3 → 4` 屬 §C 的 skip 剖面畢業，記在該節。

---

## §C skip 治理：量到的是「單機零 skip 結構上不可能」，**不是**「聯集已經是零」

掌舵者連續多輪要求「徹底解決 skipped」。本輪在 mac 真機上量到的答案是：

- **單一機器上「零 skip」結構上不可能**。mac 側剩餘 skip 的最大單一類是 `[WINDOWS-NATIVE-ONLY]`，
  它們在 mac 上**沒有標的**（`schtasks`／具名 Mutex／PS 5.1 原生 argv 語意等）；反之亦然。
  **這一條是本輪真正量到的結構事實**，它成立、且不依賴任何互補剖面宣告。
- **`tools/tests@darwin` 的 skip 剖面已由 advisory 升為阻斷式天花板**（本輪收尾單人窗口落地）：
  `_RUNTIME_SKIP_CEILING` ＋ `_RUNTIME_SKIP_CEILING_MAX` 兩張表皆有該鍵（`platform` 群零餘裕、其餘五群 0）、
  已自 `_UNMEASURED_RUNNER_PROFILES` 移除、`_MEASURED_RUNNERS_MIN` 3 → 4。現查：
  `python -c "import sys;sys.path.insert(0,'tools');from lib import skip_group_policy as p;print(p.profile_registered('tools/tests@darwin'), p._MEASURED_RUNNERS_MIN)"`。
  零餘裕的連帶稽核面見帳本 **`DEF-200-026`**（收斂輪逐字現查該列存在且主題相符：「skip 剖面由 advisory
  升為阻斷後的連帶稽核」，含 census 43→0／44→0／**45→2 筆**的鑑別力實測）。
  🔴 **該列分流欄的標籤反轉已由帳本包同輪就地訂正**（SA-10 立案；獨立驗證輪現查該列已帶
  「🔴 R83 收斂訂正（SA-10）」段落，原話保留為史料）：交件版寫「把 mac 側 44 支
  **`[MAC-NATIVE-ONLY]`** 往聯集零 skip 收」——而 `[MAC-NATIVE-ONLY]` 的測試在 mac 上是**會跑**的，
  mac 上被 skip 的 44 支全部是 `[WINDOWS-NATIVE-ONLY]`；照那句字面寫的修法是**空動作**。
  正確方向＝確認那 44 支在 `tools/tests@win32` 真的跑到（即下一項的互補剖面，宣告面已補、量測面見 §E）。
  🔴 收斂輪此處原寫「該列**有**一處標籤錯…帳本側訂正屬帳本包射程」——那句話在帳本包落地訂正後即為假，故改為現在的寫法（狀態一律現查該列）。
  > 🔴 **本項交件版寫的是「這是本輪可關而尚未關的缺口」，而磁碟相反**（QA F-2／SA-01 各自獨立抓到，
  > 收斂輪四向複驗全部證偽該句）。它同時出現在本檔 §E 交棒表第 1 列與 `AutoSDD_improving_107.md` §1 S1，
  > **而 §E 是交棒書射程** ⇒ R84 會照它去重做一件已經做完的事、並可能把已量到的健康值再「重新取得」一次。
  > 交件版同時引用了「該模組註解自陳『本輪沒有 mac 真機 ⇒ 健康值今天無論如何取不到』」——那句註解
  > **在同一輪內已就地訂正**（`git diff tools/lib/skip_group_policy.py` 可見 R82 原話被保留為史料、
  > 並補上「R83 是第一輪有 mac 真機」），⇒ 把一句已被自己修掉的話當現行事實引用。R82-era 原話依體例保留為史料。
- 🔴 **「兩平台聯集零 skip」是目標，今天**沒有**機械證據說它達成了**（SA-02 立案，收斂輪複驗為真）。
  唯一能為它作證的報告者是 `skip_group_policy.skip_target_report()`，而它的判定完全取決於
  `_COMPLEMENTARY_PROFILE` 宣告的那個剖面**真的跑得到**那些被 skip 的測試。**交件時**為 darwin 宣告的互補剖面
  是 `("tools/tests@linux",)`，而 mac 上被 skip 的 44 支全部是 `[WINDOWS-NATIVE-ONLY]`、其 skip 條件是
  `os.name != "nt"` ⇒ **linux 上一樣 skip**。交件版狀態下 `skip_target_report('tools/tests@darwin', census)`
  回**空 list＝判準認定已達標**，而它的依據是一個結構上跑不到那一半的平台。
  ⇒ 這是 R82／MAC-01 修掉的「1:1 互補短路」在反方向復發（該處註解自己寫著「1:1 的形狀本身就是那個假綠的來源」）。
  修法座標＝`_COMPLEMENTARY_PROFILE['tools/tests@darwin']` 須含 `tools/tests@win32`（win32 剖面已 registered
  ⇒ 補宣告不會轉紅）；**宣告面已由 skip 包同輪落地**，且該函式同時補了第二向判準
  （由標籤語意算出「非得有哪些平台承接」再減掉真的宣告到的，差集非空即出聲）。
  🔴 收斂輪此處把兩句寫成現在式（「本輪為 darwin 宣告的互補剖面**是** `("tools/tests@linux",)`」／「**應含**」），
  而 skip 包在它定稿後即落地 ⇒ 兩句在磁碟上轉假；獨立驗證輪改為史料式敘述。**狀態一律現查**（本節不寫死它修好了沒）：
  `python -c "import sys;sys.path.insert(0,'tools');from lib import skip_group_policy as p;print(p._COMPLEMENTARY_PROFILE['tools/tests@darwin'])"`。
  🔴 **並且：宣告修好之後 `skip_target_report()` 仍回空，而那不代表已經有證據**——逐行讀該函式，它的兩道判準是
  ①宣告到的互補剖面必須 `profile_registered()`（＝已登記在天花板表裡）②由**標籤語意**算出的
  「非得有哪些平台承接」必須都被宣告到。兩道都是**宣告面／登記面**的判準；
  `tools/tests@win32` 的天花板值來自**先前輪次在 Windows 上的量測**，不是本輪
  （本輪 Windows 側零覆蓋，見 §E 末列）⇒ 「那 44 支在**今天的** win32 上真的跑到」本輪沒有量。
  ⇒ 宣告面已關、量測面未關，兩者是兩件事，後者登記在 §E。
- **AutoClaude 側「一行 docker 指令」這個解法有射程，交件版沒寫射程**（SA-11 抓到，收斂輪實測為真）：
  它只對**沒有 PG 的機器**（`nopg` 剖面）成立。本輪這台機器 docker/PG **本來就開著**
  （`docker ps` → `autoclaude_ci_pg Up (healthy)`；每次跑都印 `AUTOCLAUDE-PG-DSN-IN-EFFECT=1`
  與 `[PG autodetect] 已注入 …DSN`），而 skip **仍有 73 支**：收斂輪當回合在 `AutoClaude/` 下實跑
  `pytest tests -q -rs` → `4304 passed, 73 skipped`、rc=0，逐群加權為
  `[WINDOWS-NATIVE-ONLY] 53／[ENV-DISABLED] 12／[TOOL-ABSENCE] 3／[DEBT] 3／[STRUCTURAL-PAIR] 1／未標籤 1`。
  ⇒ 本機最大單一類是 Windows 原生 53、第二是 `[ENV-DISABLED] 12`（需**非巢狀** session ＋ `claude` CLI，
  docker 完全治不到）。**那筆未標籤的 skip**逐字是 `mutation_token_guard.log not present in repo root`
  （`tests/tools/test_validate_mutmut_log.py`），`skip_group_census` 判為 `untagged`＝欠債型、目標 0，
  而該剖面今天沒有任何天花板看得到它（見 §E）。跑法與雙平台指令見 `ONBOARDING.md` §7.1 與 `useMacWin.md` D 段。

---

## §D 本輪的真實事故：共用工作樹上的 `git stash`

一個 subagent 在**六包並行共用的工作樹**上執行 `git stash -q -u --keep-index`，瞬間清空 16 個修改檔
與 4 個未追蹤檔（含其他包正在寫的檔）。它自己發現後 `git stash pop` 還原，前後 `git diff --stat`
逐字相同、未偵測到資料遺失——**但那是運氣不是設計**：當時若有 agent 正在寫檔，pop 會衝突或覆蓋。

**根因不是粗心**：任務書當時已寫「不要 git add / commit / push」⇒ **禁令沒涵蓋到的那個動詞，就是被
踩的那個**；而 R71 已實證純文件約束對「當下的模型」零攔阻力。

處置分兩層，**刻意不合併成一件事**：

1. **爆炸半徑**（已上線）：`.claude/hooks/block_destructive_git.py`（PreToolUse，matcher `Bash|PowerShell`）。
   判準是**動詞感知**而非只看樹——`stash` 家族溢出到共用 `.git`（`refs/stash` 是 repo 級的），
   因此**不論在哪棵樹都擋**；`checkout -- <path>`／`restore`／`reset --hard`／`clean` 的危害只限
   當前工作樹，落腳目錄可證明在專案根之外時放行。
   🔴 **它結構上擋不到什麼**（誠實劃界）：不經殼的 `subprocess`／MCP、Write/Edit 直接覆寫、
   腳本檔內的指令（工具面只看得到 `bash foo.sh`）、別名／函式。它提高的是一次成本並留下痕跡，
   **不是不可逾越**——行內豁免正是模型自己寫得出來的出口，該出口在 `AUTOSDD_UNATTENDED=1` 下失效。
2. **結構性替代方案**：見 `docs/04_planning/ADR/ADR-XPLAT-006-parallel-agent-snapshot-fanout.md`
   （Architect／SA／SD 三方獨立設計 → 合成 → 兩名對抗複審，最終降級為 **Stage-1-only**）。
   該 ADR 的兩筆 blocking 與其連根修訂記錄在該檔本體，此處不複述一份。

---

## §E Next Action（尚未關的缺口）

> 🔴 **本表在 R83 收斂輪（四方複審後）整理過一次**。交件版第 1 列宣稱
> 「`tools/tests@darwin` skip 剖面尚未由 advisory 升為阻斷」——**那件事在同一輪後段已經做完**
> （磁碟證據見 §C 第二項），該列因此**已移除**：交棒書裡一條假的「未關缺口」，成本是下一輪重做已完成的工作。
> 交件版第 4 列（「四方複審未執行」）亦已作廢——複審已執行，結果見 §G。

| # | 缺口 | 為何沒在本輪關 |
|---|---|---|
| 1 | §B-1／§B-2 的**逐檔攤分無機械物** | `doc_guard_total_problems()` 只判帶 `guard-total:<輪號>` 標記的**那一行**的總量與算術（該函式 docstring 自劃界），逐檔表在射程外 ⇒ 總量對、攤分錯即恆綠。**本輪同一個缺口被實證命中兩次**：① 交件版漂 195 行；② 收斂輪定稿版又漂 804 行（兩格隨後被續寫而過期，逐筆見 §B「重生前後的差額去哪了」）——兩次都無一物轉紅，而第二次連「上一次剛被四方複審逐筆抓過」都沒能防住。**治本形狀已知且是純算術**（不是關鍵詞啟發式，不會誤殺史料）：把款(9) 指名的那份 `.md` 內逐檔表的合計，判為必須等於 `_FROZEN_GUARD_LINES` 的本輪淨額。本輪未做，因為它要改 `tools/tests/test_adr_xplat001_c1c2_lock.py`＝**改動護欄層鎖檔本身**，會連帶讓凍結表漂移並要求同輪再重釘一次。🔴 **原文此處還附了「而本輪的重釘依 M3 已屬中途值」當理由——那句話今天為假，故不留著當現行說法**：收尾重釘已在所有包停工後完成（`_GUARD_LINES_REPIN_LOG` 的 R83 那一列＝終值、`guard_line_drift()` 空），理由只剩「要改鎖檔本身」這一條。承接輪次：**R84** |
| 2 | 帳本內容的真假**零閘門** | `check_defect_log_crossref` 只驗格式／狀態分類／承接輪次／位元組，不驗「這句話是不是真的」。本輪實證：一列把「現查兩處 `def list_jobs`」寫進狀態欄而磁碟是 0 命中 |
| 3 | 帳本不得用**行號**當錨，無機械物 | 本輪實證 6 處行號錨失準（1 處指到空行、1 處指到無關程式），成因是並行改樹。已全部改為符號錨，但下一輪照樣可以寫回去 |
| 4 | **「聯集才是零」的證據只到宣告面，量測面未關**：互補剖面宣告已於本收斂輪訂正（現查為準，SA-02 的立案本體已關），但 `skip_target_report()` 的兩道判準都是**宣告面／登記面**（見 §C 第三項逐行拆解）⇒ 它回空不等於有證據。`tools/tests@win32` 的天花板值來自**先前輪次**的 Windows 量測，「那 44 支在今天的 win32 上真的跑到」本輪沒有量 | 量測面要等 Windows 真機重驗（見本表末列）才給得出來。**本列刻意不寫死宣告的現值**——那是會被改的量測值，現查指令見 §C 第三項 |
| 5 | `AutoClaude/tests@darwin+pg+nested` 剖面**兩張表都沒登記**，連「已知缺口」都沒入 `_UNMEASURED_RUNNER_PROFILES` | 立案於本輪四方複審（SA-07）。本輪其實**量得到**（收斂輪實測 73 skip、含 1 筆未標籤欠債 `mutation_token_guard.log not present in repo root`）⇒ 這是「有量測值卻沒入表」，不是「量不到」。連帶：`_FULL_SUITE_RUNNERS_MIN` 的分母裡沒有它 |
| ~~6~~ | ~~**mac 上續航鏈只有武裝臂、沒有回收臂**~~ 🔴 **本列已作廢：那件事在同一輪後段做完了，而本列在它做完之後才被寫下來** | 🔴 **獨立驗證輪整列訂正（本列是本檔第二次犯自己正在治的病，照實記）**：收斂輪原文逐字宣稱「`tools/lib/sentinel_lifecycle.py` 對 `schedule_backend` 的 import 數＝0，其 GC 硬走 `powershell.exe`（mac 上 rc=127）⇒ `sentinel_task_names()` 回 `[]`」。獨立驗證輪當回合實測**三向全部相反**：該檔對 `schedule_backend` 有多處引用（含 `import`；**支數不寫死**——該檔本輪仍被另一個包續寫）、`_powershell` 整支已刪（只剩註解內的史料提及）、`sentinel_task_names()` 走 `schedule_backend.select().list_jobs()` 並在 mac 上回傳**真實 label**（不是 `[]`）。🔴 **第二位獨立驗證者訂正緊接在後的那半句——本列因此是本檔第三次犯自己正在治的病**：原文寫「同一刻 `launchctl list` 只剩本 session 那一支（複審者當時看到的 2 支探針孤兒已被收掉）」，**那句為假**。孤兒 `AutoSDD_Sentinel_s` 從頭到尾沒被收掉——帳本 `DEF-200-029` 在**同一輪**就記著「殘留機器動作…需人跑 `--remove-schtasks --task-name AutoSDD_Sentinel_s`」，兩處直接互斥；第二位驗證者當回合 `launchctl list` 與 `sentinel_task_names()` **兩邊都列出本 session ＋ 該孤兒**。⇒ 本列**不寫死支數**（那是機器狀態，會隨人手動清理而變），判準只有一條：兩邊必須一致。**時序證據**：`sentinel_lifecycle.py` 的 mtime 是 21:27，本檔寫下這一列是 21:39 ⇒ 寫的時候磁碟上已經是修好的。**形態與交件版 §E 第 1 列逐字同型**（把已完成的工作寫成未關缺口＝最貴的一種假宣稱），只是這一次發生在**專門用來訂正那個病的那一輪**。現查：`python -c "import sys;sys.path.insert(0,'tools');sys.path.insert(0,'tools/lib');import importlib;print(importlib.import_module('lib.sentinel_lifecycle').sentinel_task_names())"` 對上 `launchctl list \| grep AutoSDD_Sentinel_`——兩者必須一致，回 `[]` 而 `launchctl` 有東西才是本列原本要抓的假陰性 |
| 7 | **輪號自我歸屬的「落後方向」零覆蓋** | 立案於本輪四方複審（QA F-5）。守它的判準是 `int(mm.group(1)) > current`（`tools/tests/test_check_defect_log_crossref.py::TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`）⇒ **只擋超前，落後一行都不看**；本輪未提交 diff 內就有數十行以 `R82 新增／R82 訂正／R82 的立案本體` 自我歸屬的**新**程式碼註解。⇒「這條判準是哪一輪立的、被誰複審過」在 R84 會拿到假答案。修法需區分「自我歸屬型」與「史料引用型」兩種形態，本輪未做 |
| 8 | Windows 側零覆蓋 | 本輪全程在 macOS。所有「Windows 上會怎樣」的宣稱皆為替身模擬或靜態推論，**非量測值**；逐項標註在各機械物的 `cross_platform_risk` 內 |

---

## §F `pgrep -f` 等待迴圈的靜默死鎖（`DEF-200-017` 的證據居所）

> 本節是帳本 `DEF-200-017` 的詳情居所（列上受 `ROW_MAX_BYTES` 硬閘，只留指針）。
> **本節逐字訂正了本輪先前兩句自陳為真的敘述**，訂正依據是下方每一條都當回合真跑過的實測。

### F-1 症狀

本輪有三支殼卡在 `until ! pgrep -f <字串>; do sleep N; done` 這種等待迴圈裡，條件永不成立。
**表徵完全靜默**：沒有錯誤、沒有 log、沒有逾時，只是不再前進——是掌舵者觀察「token 都沒有
增加了」才被發現的。

### F-2 訂正①：機制不是「匹配到自己」

本輪先前的敘述是「等待迴圈的指令列本身含該字串 ⇒ `pgrep -f` 匹配到自己」。**那句話為假**，
而且假在會讓人寫出錯誤修法的方向。`man pgrep` 的 `-a` 條目逐字寫著：

> `-a  Include process ancestors in the match list. By default, the current pgrep or pkill
> process and all of its ancestors are excluded (unless -v is used).`

⇒ 自己與**祖先**預設就被排除。實測：單獨一支等待迴圈（token 就寫在該殼自己的 argv 裡）
`n=0` 立刻退出，不會死鎖。

**真正的機制是兄弟互匹**：pattern 字面寫在**每一支**兄弟行程自己的指令列裡，
而 pgrep 只排除自己與祖先、**不排除兄弟**。實測（`pgrep -lf` 印出命中者的 argv，兩支互看）：

```
T2(pid=1352) 命中清單： 1360 pgrep -lf python.*AUTOSDD_RECO3
T1(pid=1351) 命中清單： 1361 pgrep -lf python.*AUTOSDD_RECO3
```

⇒ **需要 ≥2 支並行等待才會死鎖**，這正好對上「本輪三支殼」。

🔴 **本小節的機制敘述漏掉一半，收斂輪據四方複審（QA F-7／falsified【8】）補上**——
**命中集有兩類，不是一類**：

1. **對方那一支 `pgrep`**（上面貼的輸出只涵蓋這一類）；
2. **對方的那個殼本身**——只要 pattern 字面出現在該殼自己的 argv 裡就成立。

複審者的實測逐字：兩側皆 `n=2`，命中者是 `4314 zsh tA.sh QAR83B` ＋ `4316 pgrep -lf QAR83B`
（對側鏡像 `4313`／`4315`）。**為什麼上面那份證據只看到一類**：那次實驗把 pattern 藏在腳本檔內
（`pgrep -lf <pattern>` 出現在腳本裡、不在殼的 argv 上），而**真實事故的形態是把整個 `until` 迴圈
inline 傳給 `zsh -c`**（Bash 工具就是這個形態）——那種形態下兄弟殼**必然**在命中集內。
⇒ 這是本輪已判兩次的「**fixture 比被測世界簡單＝最貴的一種假綠**」的第三筆，發生在一份
專門用來記錄該教訓的節裡。**影響有界**：F-4 的字元類自我否定法對兩類同時成立，故修法不受影響；
但**照本節原敘述去寫探針的人，會用一個不含兄弟殼的 fixture 去驗，重現不出真實事故**。

### F-3 訂正②：本輪建議的修法**同樣死鎖**

先前給出的正解是「用 `pgrep -f "python.*<名稱>"`（只匹配直譯器行程）」。實測兩支並行時
**照樣卡住**（兩支都在第 2 圈仍命中）：正則 `python.*<名稱>` 對自己的字面
`python.*<名稱>` 成立（`.*` 會匹配到字面上的 `.*`）⇒ 換 pattern 完全沒有改變機制。

### F-4 可用的正解（實測有效）

**字元類自我否定法**（同 `ps aux | grep '[p]attern'` 的老招）：把 pattern 寫成
「不匹配自己字面」的形狀，`run_root_unittests` → `run_root[_]unittests`。

```bash
until ! pgrep -f "run_root[_]unittests" >/dev/null 2>&1; do sleep 5; done
```

實測（一次起三支並行等待）：`S1/S2/S3` 全部 `n=0` 立刻退出；同時對照組——真的有一支
argv 含 `run_root_unittests` 的行程在跑時，同一條指令 `rc=0` 且印出該 pid ⇒ **鑑別力沒有
被犧牲掉**。其餘各自成立的替代路：`pgrep <名稱>`（不加 `-f`，只比對 process name，pattern
不會進 argv 比對面）／前景等待／`wait <pid>`。

### F-5 誠實劃界（本輪對這件事的過度宣稱已訂正）

那三支卡死的殼是**已完成 agent 留下的孤兒**。經逐筆時間戳複驗，它們**沒有阻塞任何人**：
驗證者在 19:35:48~20:05:10 全程都在寫檔，最大靜默間隔 2 分 55 秒。⇒ 先前「發現它救了這一輪」
是**過度宣稱**，此處一併訂正：它救的是「下一輪不會再有人這樣寫」。

🔴 **本小節的出處劃界**：這三個數字（時間區間、最大靜默 2 分 55 秒）與「三支殼」這個支數，
是**收尾單人窗口的量測值轉載**，不是本節作者當回合重跑的結果——本節作者當回合真的跑過的
只有 F-2／F-3／F-4 那三組 pgrep 實測。要重驗這一小節請回讀該窗口的逐字稿時間戳。

### F-6 本節沒有機械物

F-4 那個配方目前只住在這份散文裡，**沒有任何東西會在有人寫回 `pgrep -f <裸字面>` 時轉紅**。
長期居所應是 `ONBOARDING.md`（等待長跑指令那一段）＋ 任務書「禁止事項」模板，本輪未落地
（本次授權面只有帳本與本檔）。

---

## §G 四方複審已執行：結果與 M2 的結算依據

> 🔴 **本節為何存在**：交件版在 §E 第 4 列與 `AutoSDD_improving_107.md` §5 皆宣稱「四方複審未執行」，
> 並據此把成熟度 M2 判為 **N/A**（依 M2 判準①「該輪未執行四方複審一律判 N/A，禁記 0」）。
> **複審其後已執行** ⇒ 那兩處在複審發生的那一刻起轉假（SA falsified 12 直接指出這一點）。
> M2 需要一個在 repo 內、可被下一輪引用的結算依據，本節即該依據；此前它只存在於複審者的逐字稿裡（會被 compact 掉）。

**四方裁決**：Architect／QA／SD／SA **全數 `APPROVE_WITH_CONDITIONS`，無人 REJECT**。

**假宣稱筆數（M2 的分子）**：四方各自 `falsified_claims` 段合計 **32 筆**
（Architect 6／QA 9／SD 5／SA 12），**跨方重複未去重**——本輪最吃重的幾筆被 2~4 方各自獨立命中
（例：`tools/tests@darwin` 剖面已升為阻斷卻寫成「未關」＝QA F-2＋SA-01；10 支紅的假指針＝QA F-1＋SA-03；
§B-1 逐檔攤分＝Architect A-03＋SA-04＋QA F-9；ADR 護欄層數字＝Architect A-04）。
去重後的量級不影響結論：**M2 的門檻是「連續三輪 ≤1 筆且無任何 P1」**（絕對值不是比率）
⇒ 本輪一輪就遠超門檻，**M2 判 ❌，不得再記 N/A、也不得記 0**。

**最大的一類**（四方一致，且是本輪要學的東西）：**文件層的假宣稱**——散文／結算表／交棒書寫的事
與磁碟不符，而且**每一筆都沒有任何機械物看得到它**。三個結構原因，逐條都已實測：

1. **總量有鎖、攤分沒有**：`doc_guard_total_problems()` 只判帶 `guard-total:<輪號>` 標記的那一行
   ⇒ 逐檔表漂而恆綠。本輪命中**兩次**：交件版 195 行、收斂輪定稿版 804 行
   （見 §B「自我對帳式」與「重生前後的差額去哪了」、§E 第 1 列）。
2. **掃描面不含 ADR 目錄**：`_GUARD_TOTAL_DOC_GLOBS` 是兩個不遞迴的 glob，
   `docs/04_planning/ADR/` 一個都不匹配 ⇒ ADR 呈給掌舵者拍板的三個數字全錯而無一物轉紅
   （處置與「為何不補標記」的理由見 `ADR-XPLAT-006` §6 訂正段）。
3. **交棒書沒有任何真假判準**：§E 是純散文表。本輪它的第 1 列把一件**已完成**的工作寫成未關缺口
   ——那是最貴的一種假宣稱（下一輪會照著重做，而重做的人不會懷疑交棒書）。

**收斂輪的處置面**（本檔射程內）：§A-1 新建（10 支紅的真居所＋可重跑配方）、§B-1／§B-2／§B-4 逐格
訂正並補上對帳式、§C 三筆假宣稱訂正並補現查指令、§E 整表重整（刪 2 列假缺口、補 5 列複審新發現）、
§F-2 補上漏掉的那一半機制。**程式碼層與帳本層的處置不在本檔**（各由對應的包執行，見該輪帳本列）。

🔴 **本節不寫死「四方條件是否全部關閉」**——那是收斂輪四包並行的結果，任一包的處置都可能改變它。
判準是複審者自己列的轉 APPROVE 條件，逐條驗收由收輪窗口做一次。
