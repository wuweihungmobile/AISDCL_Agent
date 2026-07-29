# 跨平台相容性 R60 — 修復證據全文（2026-07-28）
> ## 🔴 本檔已於 R60 round 3 拆為兩份 —— 先看這張對照表（DEF-101-587）
>
> **為何拆**：本檔一度達 **260,963 bytes**，距 **262,144**（Read 工具**單次讀取上限**）僅
> **1,181 bytes**，而全 repo 當時**沒有任何閘門量它的體積**。本檔是帳本「兩層化」的第二層
> ——帳本列只寫摘要、完整證據（bug-injection 紅綠、逐條指令與真實輸出）全在這裡；一旦
> 超過上限，四方複審者**無法一次讀完**，只能分段猜著讀。與 `DEF-99-001`／`DEF-101-123`
> 完全同型：**政策有上限、卻無機械守門**（R9 就是這樣讓帳本默默長到 272KB）。
>
> **檔名刻意不變**：缺陷帳本有 **13 處**指向 `CrossPlatform_R60_Fix_Evidence.md`。改名或
> 搬走會讓那些指針全部失實——那正是本輪 `ARCH-R60-01` 家族反覆在治的病。故**本檔留在
> 原地當入口**，round 3 的節搬到姊妹檔，由下表指路。
>
> | 輪次 | 檔案 | 涵蓋的 `## DEF-ID` 錨 |
> |---|---|---|
> | round 1~2 | **本檔** `CrossPlatform_R60_Fix_Evidence.md` | `DEF-101-527` ~ `DEF-101-560`（共 34 節）＋「各修復包誠實揭露的未修項與跨包請求」段 |
> | round 3 | `CrossPlatform_R60_Fix_Evidence_r3.md` | `DEF-101-568` ~ `DEF-101-586`（共 19 節）＋「Pkg-P11 交付門檻實測」段 |
>
> **要確認某筆是否有全文，一律以實查為準**（本檔不對「涵蓋到哪一號」下區間式宣稱——
> 區間宣稱會在下一次新增條目時自動 stale，那是 `SA-R60-05` 抓到的形狀）：
> ```bash
> grep -ln '^## DEF-101-<NNN>$' docs/06_quality/CrossPlatform_R60_Fix_Evidence*.md
> ```
>
> **體積自此有機械守門**：`tools/check_defect_log_crossref.py` 的體積守門涵蓋面已由
> 「帳本家族」擴到具名治理文件集合（含本檔與姊妹檔），逾 warn 帶印警告、逾上限 fail。

> **本檔的定位**：缺陷帳本 `AutoSDD_Defect_Log.md` 的 R60 條目（`DEF-101-527` 起）各列只寫「現象一句 + 修法一句 + 關鍵實測數字」，
> 完整的 bug-injection 紅綠對照、逐條指令與真實輸出、以及各修復包誠實揭露的未修項與跨包請求，逐字保全於本檔。
>
> 🔴 **涵蓋範圍（round 2 訂正，round 1 SA-R60-05）**：本檔以 `## DEF-101-NNN` 為錨，**每一節的存在即為該筆有全文的憑證；帳本列的「完整證據見本檔」指針只在對應 `##` 錨存在時才成立**。
> 原標頭寫「`DEF-101-527`~`DEF-101-554` 各列…逐字保全於本檔」，但磁碟實況當時只有 **26 節**（529~554）——`527`／`528` 兩節從未寫入，而帳本那兩列的「完整證據見 `CrossPlatform_R60_Fix_Evidence.md`」因此是**懸空指針**（本輪自己才修掉 5 處同型失實指針，見 `DEF-101-527`；新造的兩處恰是本輪最自我批判的兩列）。
> round 2 已補齊 `## DEF-101-527`／`## DEF-101-528`，並補上 round 2 新增條目 `## DEF-101-555`~`## DEF-101-560`。**本檔不對「涵蓋到哪一號」下區間式宣稱**（區間宣稱會在下一次新增條目時自動 stale——這正是 SA-R60-05 抓到的形狀）：要確認某筆是否有全文，一律以 `grep -n '^## DEF-101-<NNN>$' docs/06_quality/CrossPlatform_R60_Fix_Evidence.md` 實查為準。
> 見 DEF-101-558（現居 archive_33）。
>
> **為何分兩層**：第一版把六個修復包回報的完整證據逐字灌進帳本表格列，28 列共約 99.5KB（每列約 3.5KB，歷輪慣例是 1~2KB），主檔當場由 176,296 衝到 **275,979 bytes**、直接撞破 `check_defect_log_crossref.py` 的 262,144 fail 硬閘。
> 這也順帶證偽了 `archive_30` 標頭當時寫的「本輪即使毛增 45KB 仍不觸及 warn 帶」——**實際毛增是約兩倍**。
> 本 repo 既有慣例本來就是長敘事外移（`archive_05`／`06`／`07` 搬的都是敘事段落而非總表列），故改為兩層。


---

## DEF-101-527

**現象**：帳本歸檔的搬遷判準與保全檢查，歷輪都是在對話裡臨時寫一支腳本、跑完即丟，repo 內零載具。
同輪四方掃描（Scan-D 反駁者自找 #1／Scan-G 反駁者自找 #3／#4）抓到三件事：

1. `archive_29`／`archive_30` 標頭都宣稱「由歸檔腳本以閘門自身邏輯機械檢查、逐筆顯式 assert」，
   但那支腳本只存在於某次 session 的暫存目錄、**不可重跑** ⇒ 宣稱一道機械檢查存在而它不可重跑，
   等同沒有檢查。
2. 標頭散文所載判準與實際執行的判準**不是同一個**：判準②照字面（子字串）執行會把狀態欄含
   `OpenMutexW` 的 `DEF-101-504` 誤擋；實際執行版用 ASCII 邊界 lookaround 不會。
   這個假陽性直接影響 Scan-G G-01 提議修法的可行性。
3. 同一次歸檔在 `archive_30` 標頭與主檔歸檔索引給出互相矛盾的位元組數字
   （174447／釋出 81626 vs 174609／釋出 81464），且兩者皆與當時實測 176459 不符
   （根因見 `DEF-101-528`：CRLF 污染）。

**修法（主控 Pkg-1）**：把判準落成正式工具，判準即程式。

- 新建 `tools/archive_defect_log.py`：直接 `import` `tools/check_defect_log_crossref.py` 的
  `_CLAIM_RE`／`_classify`／`_ID_RE`／`_ROW_RE` 當 SSOT，**不另寫一份正則**（避免「文件判準 vs
  執行判準」再次分裂）。四判準 ＋ `--plan`／`--apply`／`--check` 三個模式。
- 判準④（散文交棒偵測）為本輪新增，命中者不自動搬、須以 `--ack-handoff <ID>` 逐筆具名承認
  ——刻意設計成「需具名承認」而非硬擋（硬擋會讓帳本永遠搬不動，因為歷史已結列的散文常提到
  backlog；完全不管就是 `DEF-101-517`／`526` 被靜默埋葬的成因）。
- 新建 `tools/tests/test_archive_defect_log.py`（10 支，**`unittest.TestCase` 類別風格**）。
  ⚠️ 風格不是偏好問題：同輪 C-01 證實 pytest 函式風格會被四道 unittest discover 閘門
  **整檔零收集**（`tools/run_root_unittests.py` + 3 支 CI/hook 消費者），寫成函式風格等於這 10 支
  在所有閘門上都不存在。
- bug-injection（判準④）：把 `DEF-101-517` 的交棒字樣移除後，`--plan` 立即把它列入「可搬」
  （原本在「需具名承認」清單）⇒ 判準④真的在判、不是裝飾。

**round 1 四方複審對本筆的追加發現（已轉為 round 2 標的，本節不代為宣稱已修）**：
`check()` 的指針稽核只掃主檔且不認 `立帳見主檔 …` 樣式（ARCH-R60-01）、`check()` 零閘門接線且唯一
消費測試用 `assertIn(rc, (0, 1))` 吞掉失敗訊號（ARCH-R60-02）、`apply()` 四項保全用裸 `assert`
（`-O` 下整組消失，QA-R60-08）。這三筆由 `tools/` 擁有包於 round 2 處理。

## DEF-101-528

**現象**：主控動工前那支臨時歸檔腳本用 `Path.write_text()` 寫檔，其 `newline` 預設為 `None`，
在 Windows 上把 `\n` 譯成 `os.linesep`（CRLF）。後果三層：

1. 帳本主檔與 `archive_30` 由 `w/lf` 變 `w/crlf`，與 `.gitattributes:34` 的 `*.md text eol=lf`
   宣告相反，`git diff` 直接印警告。
2. **讓該腳本自己的「位元組總量守恆」斷言在最終產物上按字面重驗為假**——多出的位元組正是每行
   一個 CR（主檔 163 個、`archive_30` 61 個）。
3. 這也是三個互異數字（174,447 LF／174,609 CRLF／176,459 含索引條目）的來源，而三者在文件裡
   各自算術自洽、都沒有時點限定詞，讀者無從分辨（同 R57 SA-R57R3-01 判例）。

**修法（主控 Pkg-1）**：

- 主檔與 `archive_30` 以 **bytes 層**正規化回 LF，落地後 assert 磁碟實體零 CR；
  `git ls-files --eol` 複驗皆回 `w/lf`。
- `archive_05`／`archive_21` 一併正規化。**`git diff` 為空即證明語意零變更**（index 本就是 LF，
  只有工作樹被寫成 CRLF）。
- 新工具 `tools/archive_defect_log.py` 一律 bytes 層寫入並在落地後 assert 零 CR，
  `--check` 稽核**整個帳本家族**的行尾。

**round 2 訂正（round 1 QA-R60-09）**：Pkg-5 曾把 `archive_05`／`archive_21` 的 `git status` M
推測為「D-03 三個 byte 數字對不上的其中一個變因」——**該推測不成立**，見本檔 Pkg-5 段的 ⚠️ 訂正註
與 `## DEF-101-558` ③ 的 blob 實測。真變因就是本筆的 CRLF 污染，本筆的歸因是正確的。

---

## DEF-101-529

**發現情境**：R60 Scan-G 交棒的 DEF-101-517 backlog 解鎖條件（archive_30:53 明文：「下一輪先評估這兩條較便宜的路徑，再決定是否需要走 stage 路線」），由 Pkg-4 Scan-C 執行評估並落地

**嚴重度**：P2（承接 DEF-101-517 原評級：補償控制無自動觸發器；本輪已收斂）

**分流去向**：本輪修復（Pkg-4 Scan-C）：落地交棒清單中的路徑①（獨立 schtasks 任務），路徑②（dev_start 心跳哨兵加提醒）評估後不採，理由見狀態欄

### 現象與證據

**Windows 側執行級補償控制 `tools/windows_smoke_local.ps1`（PASS=12）沒有任何自動觸發器＝補償控制自己沒有心跳**。它正是 DEF-101-139 為「雲端 CI 帳務停擺（DEF-101-081）」而建的 Windows 側唯一活體驗證管道，而 R59 逐項 grep 實測確認 `run_local_nightly.ps1` 對它零呼叫、只能手動觸發（也解釋了它為何腐化到讓 R59 踩到 DEF-101-511）。mac 側對照：`run_local_nightly.sh` 的 `[1/4]` 每日自動跑 `macos_smoke_local.sh`。本輪落地後另**實機證實缺席是可偵測的**：`install_windows_nightly.ps1 -Status` 現在回 `❌ 排程任務不存在：AutoClaude_WindowsSmoke`、REAL_EXITCODE=1

### 狀態與驗證

fixed@R60：**評估兩條交棒路徑後選路徑①**（獨立 schtasks 任務），並在形態上選「任務集合」而非新增旗標——`install`／`-Uninstall`／`-Status`／`-WhatIf` 四模式一律作用於整組（AutoClaude_Nightly 02:00 ＋ **AutoClaude_WindowsSmoke 01:00**），故 `param()` 不需動、排程能力對照契約的 switch 集合仍是 {Uninstall, Status}、零 churn；更重要的是它在**能力層**真正對上 mac（mac 是一支 launchd job 內含 smoke，Windows 是 install 一次註冊兩支任務）。為何不採路徑②：心跳哨兵只是「提醒人去手動跑」，補償控制仍然沒有自己的心跳；路徑① 才讓它真的每天跑，且 `-WhatIf` 當場可取得驗證證據（正是交棒清單指出「抵銷了原本引為主要理由的無法觀測真實排程執行」那一點）。**刻意仍不走 stage 路線**（理由沿用 DEF-101-517 原文並寫進腳本檔頭）：新增 stage 需同動 summary 行／summary JSON／exit-decision 清單／Format-Rc 標籤共四處，而 summary 行被 `tools/dev_start.py` 心跳哨兵以跨檔字面正則解析（DEF-101-263②／R25 已建跨檔字面鎖）；獨立任務與 nightly summary **零耦合**。**四項補跑保護共用同一份 `$settings`**（StartWhenAvailable／WakeToRun／`-AllowStartIfOnBatteries`／`-DontStopIfGoingOnBatteries`，參數名依 DEF-101-249 用建構 cmdlet 的正確名稱）——四項對 smoke 的必要性與 nightly 完全相同（同一個筆電夜間睡眠漏跑成因），刻意不另立一份而製造第二個漂移點。**smoke 排在 nightly 之前一小時**：smoke 是數分鐘的便宜 tripwire、nightly 是含 mutation 的小時量級深度回歸，機器只醒一小段時間時先跑便宜那支才有意義。**載具正確性**：schtasks 直起 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`，不經任何 msys 層，符合 DEF-101-511 對該腳本的「必須原生 PowerShell」要求（該腳本偵測 `$env:MSYSTEM` 即 exit 1 拒跑）。**心跳從哪讀**：不另造心跳檔，`-Status` 讀 `Get-ScheduledTaskInfo` 的 LastRunTime／LastTaskResult（語意對應 mac 版讀心跳檔 mtime，實作不同，如實揭露）。**回歸鎖**：`test_install_windows_nightly.py` +2 支結構鎖（任務名／載體路徑／兩個各自獨立的 ShouldProcess／uninstall 覆蓋整組；共用 $settings ＋ smoke 早於 nightly）、+1 支 Windows-native runtime 鎖驗 `-WhatIf` 涵蓋**每一支從原始碼抽出的**任務名，且**執行前後排程存在性快照必須完全相同**（比「檢查某支任務不存在」更可靠：不論本機裝了哪幾支都能抓到 -WhatIf 真的動了系統）。**bug-injection**：smoke 時刻 01:00→03:00 → `'03:00' not less than '02:00'` 翻紅；刪掉 smoke Register 的 `-Settings $settings` → 正則鎖翻紅並指出「四項補跑保護只有 nightly 拿到」；皆以 Edit 還原、md5 逐位元組核對（3cfa9e77…→3cfa9e77…），**未用 `git checkout --`**。**驗證（全部只用 -WhatIf 與唯讀查詢，未真的註冊/移除任何排程任務）**：PS 5.1 `[Parser]::ParseFile` errs=0；`-WhatIf` 印出兩行 `What if: … Register-ScheduledTask … AutoClaude_Nightly` / `… AutoClaude_WindowsSmoke`、rc=0；`-Uninstall -WhatIf` 同樣兩行 Unregister 預覽；跑完後 `Get-ScheduledTask` 只回 `AutoClaude_Nightly Ready`（零副作用）；該檔測試 13→17 OK；`test_windows_nightly_anchor_parity`（含必須逐字保留的 `StartWhenAvailable         = $($s.StartWhenAvailable)` 錨）、`test_ps1_bom`、`test_ps51_compat`、`check_script_parity.py` 全綠。**⚠️ 遺留的跨包同步（本包無權改，已於交付中提報）**：`AutoClaude/tools/run_local_nightly.ps1:21` 與 `ONBOARDING.md:276` 仍寫「Windows 對等物只能手動觸發」，該框架已因本修復過期（「run_local_nightly.ps1 對 smoke 零呼叫」本身仍為真且是刻意解耦，僅「只能手動觸發」需訂正）


---

## DEF-101-530

**發現情境**：R60 Scan-G backlog 接續（承接 DEF-101-526 明文交棒的 R60 候選；Pkg-7 落地）

**嚴重度**：P3（治理衝突的前瞻性告知缺口；現況無新增違規，但下一個動這些檔的人必然重踩）

**分流去向**：本輪落地（Pkg-7）

### 現象與證據

DEF-101-526 記載的治理衝突「LOC tier 滿載檔 × lint 斷行互斥、且兩者都是硬閘」在 R59 只取行內 noqa 緩解，衝突本身交棒 R60 並指定方向：「把它列為固定掃描檢查點（**如** `check_loc_budget` 對餘裕 ≤ 3 行的檔印 warning），讓下一個踩到的人事先知道」。落地前實測確認缺口存在：`check_loc_budget.py` 只在 `over_by > 0`（已破線）才有 `[TIER]` 訊號，滿載檔（餘裕 0）與餘裕充足的檔輸出**一字不差**；repo 現況有 3 支合法滿載檔（`pg_state_repository.py` 400/400、`models/escalation.py` 150/150、`steps_orchestrator/_impl.py` 500/500）

### 狀態與驗證

fixed@R60：`AutoClaude/tools/check_loc_budget.py` 新增 `TIER_WARN_MARGIN = 6` ＋ 非阻塞 `[TIER-WARN]` 段（逐檔列 tier／預算／LOC／餘裕，附三條可操作指引：修 E501 用行內 noqa 而非斷行、勿加 per-file-ignores、說明寫 `#` 不寫 docstring 因後者被 count_loc 計入），`--json` 同步曝露 `tier_warn_margin` 與帶 `headroom` 的 `tier_warn_band`。**刻意不改成 fail**（不進 `has_violation`／`violations_count`、rc 不變）——改 fail 會當場擋住那 3 支合法滿載檔。**刻意用 `[TIER-WARN]` 而非 `[WARN]`**：後者已被 `tests/contract/test_loc_budget_tiered.py::test_warn_band_boundary_and_rc_invariant` 以 `("[WARN]" in out) is expect_warn` 釘為總量帶專屬訊號。**N=6（刻意上調交棒舉例的 3，理由已寫進常數註解）**：(a) 原文「如…≤3」是舉例非規格；(b) **同一列自己的實測否證 3**——4 處 E501 斷行後實測 `406 > 400 (+6)`（+5 斷行、+1 ruff I001 拆 import），一次 lint 修復的實測代價是 6 行，取 3 會讓餘裕 4~6 的檔照樣被咬卻無預警；(c) 偽陽性成本實測（201 支計入檔的餘裕分佈 `<=0:3 / <=3:3 / <=5:4 / <=6:5 / <=10:6`）：多出 2 行非阻塞提示，而多出的 2 支（`evolution_plugin.py` 245/250、`core/ports/rtm_feedback.py` 144/150）正是「一次斷行就破線」的檔；(d) 與既有 `TOTAL_WARN_MARGIN=10` 同形，不新增第二種機制語意。**真實輸出**：`total=20361 baseline=17032 cap=20438 violations=0` rc=0 ＋ `[TIER-WARN] 5 支檔案 tier 餘裕 ≤ 6 行（非阻塞，rc 不變）`，含 `[adapter<=400] autoclaude/infra/repositories/pg_state_repository.py: 400 （餘裕 0 行）`（＝DEF-101-526 當事檔，交棒驗收條件達成）。新增鎖 `AutoClaude/tests/tools/test_check_loc_budget_tier_headroom_warn.py` 9 支（非阻塞性／邊界 ==margin 進 vs ==margin+1 不進／破線檔只進 `[TIER]` 不進預警帶／標籤隔離／JSON↔文字一致／**真 repo 錨點**）。**bug-injection ①** `TIER_WARN_MARGIN=0` → `2 failed`；**② 標籤改回 `[WARN]`** → 我的新鎖 `6 failed` **且既有 `test_loc_budget_tiered.py` 同時 `3 failed`**（坐實標籤碰撞真的會關掉那道鎖）；兩次還原後 `42 passed`、既有 33 支全綠、`ruff` 全過


---

## DEF-101-531

**發現情境**：R60 Scan-A 廣泛掃描 A-01（掃描者原判 P3、反駁者裁 PARTIAL 並主張升 P2）＋反駁者自找 #1；Pkg-2 修復時第三度獨立重跑並訂正機制歸因

**嚴重度**：P2（維持反駁者訂正值；帳本原判 P3 應升。理由：pre-push＋3 支 CI 共用閘門的安全網破洞，且可自發翻紅並指向錯誤的生產碼結論）

**分流去向**：本輪修復（Pkg-2 Scan-A）；檔案 tools/tests/test_bash_probe_spec_contract.py。生產碼 AISDLC_SDD/scripts/bash_probe.py 刻意不動——「無法 spawn 的 bash 本來就不可用」，回 None 語意正確，缺陷純在測試的鑑別力

### 現象與證據

tools/tests/test_bash_probe_spec_contract.py:84（TestUsableBashEndToEndWithRestrictedPath.test_usable_bash_rejects_candidate_when_path_lacks_dirname）在官方閘門 tools/run_root_unittests.py（pre-push:210 + root-infra-ci.yml:293 + macos-compat-ci.yml:314 + windows-compat-ci.yml:420 共四處呼叫）下**誤綠**：unittest 載具 REAL_RC=0「Ran 5 tests / OK」，同一支檔案 pytest 載具 REAL_RC=1「AssertionError: 'C:\Program Files\Git\usr\bin\bash.EXE' is not None」。誤綠來源＝AISDLC_SDD/scripts/bash_probe.py:79-80 的 `except Exception: continue` 把兩種 None 壓成一種：候選被 PROBE_CMD 正確拒絕 vs 子行程根本沒起來。spy 實測 events=[('raise','OSError','[WinError 87] 參數錯誤。')]，即 CreateProcess 沒起來。

【機制歸因訂正（本輪第三方獨立取證，推翻掃描者與反駁者兩版說法）】反駁者寫「判別因子＝同一 process 內先前是否發生過 os.putenv」只解釋了 WinError 87 那一半。真根因更底層：Windows 上 `os.environ['PATH']=''` 是**刪除**該變數而非設為空字串（ctypes GetEnvironmentVariableW('PATH') 由 present len=1546 變成 MISSING/rc=0；新變數設 '' 亦 MISSING、設 'x' 才 present），而子 MSYS bash 在完全沒有 PATH 時會自行合成 /usr/local/bin:/usr/bin:… → dirname 照樣找得到。故舊載具兩段都壞：clear=False 時實測 usable_bash 回傳 bash 路徑（該紅），再加 clear=True 把整個 Win32 區塊清成 0 筆（GetEnvironmentStringsW entries=0）才「湊出」None＝誤綠。⇒「unittest 這條路天生 fail-closed 所以安全」不成立，閘門綠燈是收集排序運氣：修復前多寫一個無關環境變數即翻紅。

實害：DEF-101-275 的 wiring 層防線（生產端是否真的依賴 PROBE_CMD 的 coreutils 驗證）在 Windows 上等於從未執行過。

### 狀態與驗證

fixed@R60（Pkg-2）：①新增 usable_bash_with_probe_spy() 把 None 的兩種來源分流（completed / spawn_errors）；②wiring 測試載具改為「PATH 指向真實存在但空無一物的 temp dir」——本機實測 rc=127、stderr `dirname: command not found`、Win32 區塊維持 87 筆，於是**首次**在 Windows 上真正驗到生產端 wiring（不需退讓成 skip）；③斷言順序改為先 assertFalse(spawn_errors)（訊息明寫「載具故障（非生產端結論）」）→ assertTrue(completed) → assertNotEqual(rc,0) → assertIsNone；④新增 TestNoneSourceIsDistinguishable 三支鎖，含 meta 鎖 test_wiring_test_goes_red_instead_of_green_when_spawn_breaks（把 spawn 失敗注入回 wiring 測試本體，斷言必須 FAIL 且訊息含「載具故障」）。驗證：兩載具皆 8/8 綠（unittest REAL_RC=0「Ran 8 tests / OK」、pytest REAL_RC=0「8 passed」）；先寫無關 os.environ 再跑亦綠（排序運氣消失）；bug-injection 把原始載具 PATH=""+clear=True 完整還原 → REAL_RC=1「AssertionError: [OSError(22,'參數錯誤。',None,87,None)] is not false : 載具故障…」，即同一組條件下舊測試印 ok、新測試指名 WinError 87 而紅；再以 Edit 逐字還原 → REAL_RC=0。8 個 id 已確認在官方 discover 集合內（TOTAL_DISCOVERED=742）


---

## DEF-101-532

**發現情境**：R60 Scan-A A-02（掃描者原判 P2、反駁者裁 PARTIAL 降 P3）；Pkg-2 修復時另揪出修法本身的陷阱

**嚴重度**：P3（採反駁者訂正：兩支 CONTEXT-LEDGER hook timeout=5.0 且對 TimeoutError 早有 append-only sidecar 降級路徑，非資料遺失；但 PermissionError 不在其例外契約內）

**分流去向**：本輪修復（Pkg-2 Scan-A），僅動 LATEST v0.30。v0.01~v0.29 共 29 版同檔各有 3 處同款窄捕，依 Copy-on-Evolve 不回補（歷輪破例皆需使用者核准）

### 現象與證據

AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/file_lock.py 兩處移除 sentinel 的 unlink（:80-83 陳舊回收、:93-96 finally）只捕 FileNotFoundError。Windows 上只要第三方持著該 sentinel 的 handle（防毒／搜尋索引器／備份代理，或本模組 docstring 自己邀請的 post-mortem 讀取者），unlink 就丟 PermissionError [WinError 32]。自寫探針（importlib 直載生產模組、全程只動系統 temp）逐段複現：STEP0 unlink-with-open-handle RAISED PermissionError [WinError 32]；STEP2 escaped_exception=PermissionError [WinError 32] …ledger.lock、sentinel_leaked=True（例外逸出 context manager，而呼叫端的例外契約裡沒有這個型別）；STEP3 next writer blocked 2.03s then TimeoutError。硬化不對稱先例逐字核實：tools/dev_start.py:1127 `except OSError as e` + _warn、_release_bootstrap_lock 內 `except OSError: pass`。

【Pkg-2 另揪出的修法陷阱（掃描者與反駁者皆未提，若照字面修會更糟）】陳舊回收分支原本是無條件 `continue`，會**跳過 deadline 檢查與 sleep**。若只是把 `except FileNotFoundError` 放寬成 `except OSError: pass`，遇到刪不掉的陳舊 sentinel 就變成 100% CPU 無窮忙迴圈、永不 timeout——原版至少會把例外拋出去而終止。實測坐實：把該分支改成無條件 continue 後，回歸測試 REAL_RC=1「AssertionError: True is not false : 陳舊 sentinel 刪不掉時 file_lock 沒有在 5s 內收場——無窮忙迴圈復發」（5.85s）。

### 狀態與驗證

fixed@R60（Pkg-2）：新增 _try_unlink(path)->bool（FileNotFoundError→True 視為已成功、OSError→False 表示仍被持有），兩處移除點共用；陳舊回收分支改為 `if _is_stale(lock_path) and _try_unlink(lock_path): continue`，刪不掉就落回 deadline/sleep 讓 timeout 維持權威（避開無窮忙迴圈）。新增 3 支回歸鎖於 tests/test_file_lock.py：①平台中立注入 PermissionError 驗 finally 不逸出；②原生 Windows 真 open handle（不注入例外）驗同一件事；③陳舊 sentinel 刪不掉必須 5s 內以 TimeoutError 收場，刻意用 thread+join(timeout=5) 使回歸時是紅而非掛死整個 push 閘門。驗證：修復後同一探針 STEP2 escaped_exception=None；test_file_lock.py REAL_RC=0「6 passed」；bug-injection 拿掉 except OSError → REAL_RC=1「3 failed」且原生 Windows 那支是真實 PermissionError [WinError 32]（pathlib.py:1147）而非注入；injection B 無條件 continue → 1 failed（見上）；兩次皆以 Edit 逐字還原後 REAL_RC=0「6 passed」。下游零退化：context_ledger 前後 hook + phase_k 48 passed、phase_j + governance_coverage 100 passed


---

## DEF-101-533

**發現情境**：R60 Scan-A A-04（掃描者原判 P3、反駁者裁 PARTIAL 並建議「不值得為此動 LATEST 生產碼、只寫註解」）；主控明確指派本包修復，Pkg-2 依「所有問題必須徹底全部修復」驗收標準落地程式修復並補齊反駁者留白的可達性論證

**嚴重度**：P3（維持；反駁者主張實質可對齊 P4/wontfix 慣例，但主控指派修復，且修法成本極低、已附雙層回歸鎖，故不降）

**分流去向**：本輪修復（Pkg-2 Scan-A），僅動 LATEST v0.30。v0.01~v0.29 共 29 版同檔同款裸 rmtree，依 Copy-on-Evolve 不回補

### 現象與證據

AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/hub_sync.py:_mirror_local() 用裸 `shutil.rmtree(dst_sub)` 緊接 `shutil.copytree(src_sub, dst_sub)`，未套用 R15 SCAN-B-2 建立的 _rmtree_windows_safe 硬化先例（grep 實查：修復前該先例只存在於 AISDLC_SDD/scripts/sync_exposed_skills.py:50/148 與其測試檔，v0.30 tools/fsm_runtime 零命中）。自寫探針複現 Windows 三段連鎖：bare rmtree → PermissionError [WinError 5] 存取被拒；half-deleted dir still exists=True remaining=['readonly.yaml']；follow-up copytree → FileExistsError [WinError 183] ⇒ 端點從「失敗一次」變成「永久無法鏡像」。硬化版（onerror 清唯讀後重試）→ rmtree OK、copytree OK。

觸發子（補反駁者說「唯讀來源結構性缺席」的一格）：copytree 以 copy2/copystat **連權限位一起複製**，所以任何 file:// hub 的 rules/ 帶唯讀檔（壓縮檔解出、唯讀鏡像共享、備份代理標記）就會把唯讀位帶進 cache_dir，下一次 pull 的 rmtree 即中；第二條 Windows 通用觸發子是第三方持 handle（WinError 32）。可達性採認反駁者的訂正：出廠 knowledge/hub-registry.yaml 是 allowed_endpoints: []、session_start.py:197 有 `and client.endpoints` 守門 ⇒ 出廠設定下 _mirror_local 不可達，屬 latent；但只要使用者登錄任一 endpoint 即為生產路徑（本輪回歸測試就是走真 pull() 打進去的）。

### 狀態與驗證

fixed@R60（Pkg-2）：**就地硬化而非跨樹複用**——先例位於非版本化的 AISDLC_SDD/scripts/，從 v0.30/tools/fsm_runtime import 會新開跨樹依賴（違反各版自足與 Copy-on-Evolve），且先例把失敗包成 RuntimeError 是為人機互動 CLI，而 hub_sync 的 pull() 把任何例外收進 PullResult.error 當非阻擋警告、換型別會打壞呼叫端 except 形狀。故在 hub_sync.py 新增同名模組級 _rmtree_windows_safe(path: Path)（onerror 先 os.chmod(S_IWRITE) 再重試一次；重試仍失敗連同 Python 3.11 POSIX fd-based rmtree 的 TypeError 一律回拋原始錯誤、不換型別），_mirror_local 改走它，補 import stat。新增 2 支鎖於 tests/test_hub_sync.py：①走真生產路徑 pull()→_fetch_endpoint()→_mirror_local()（cache 內檔案 chmod 唯讀後 force=True 二次 pull 必須 error is None）；②平台中立呼叫點鎖（inspect.getsource(_mirror_local) 必含 _rmtree_windows_safe( 且不得含 shutil.rmtree(），因 ① 在 POSIX 恆綠、零鑑別力——此限制已寫進測試 docstring。驗證：REAL_RC=0「51 passed」；bug-injection 改回裸 rmtree → REAL_RC=1，兩鎖各自翻紅（PullResult.error='PermissionError: [WinError 5] …SLV-100.yaml'／assert '_rmtree_windows_safe(' in src 失敗）；Edit 逐字還原後 REAL_RC=0「51 passed」


---

## DEF-101-534

**發現情境**：R60 Scan-F 反駁者自找 #2（P3）；該反駁者在驗 F-02 時繞過 pytest conftest 的 telemetry 隔離 fixture 而無意寫穿真實規則檔，已誠實揭露

**嚴重度**：P3（維持；.gitattributes 會在 git add 時正規化，髒資料不進 repo，真實傷害是工作樹假髒 + 兩平台 diff 不對稱）

**分流去向**：本輪修復（Pkg-2 Scan-A），僅動 LATEST v0.30。v0.01~v0.29 共 29 版同檔同缺（`grep -L 'newline=""'` 全數命中），依 Copy-on-Evolve 不回補；其中僅 21 個凍結版有 record_state_fires（共 22 版含 LATEST），觸發面本來就較小

### 現象與證據

AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/rule_loader.py:_write_rule() 的 `tmp.write_text(yaml.safe_dump(...), encoding="utf-8")` 未帶 newline=""，text 模式預設 newline=None 在 Windows 上把每個 \n 寫成 \r\n；而 governance/rules/R-*.yaml 是 tracked 檔、.gitattributes:30 明文宣告 `*.yaml text eol=lf`。fire 遙測 production 出貨為 ON、record_state_fires() 在每次 transition 都經此路徑寫回（conftest.py:35-47 自陳），故 Windows 上跑一次 FSM 就實測讓 15 支 R-*.yaml 整檔轉 CRLF（git 對每檔警告 CRLF will be replaced by LF、工作樹憑空多 15 支「已修改」檔、掩蓋真正變更並觸發 smoke 的「未 commit 變更」告警）；macOS/Linux 上同一段程式只產生 fire_count 的數字 diff ⇒ 兩平台 diff 體積不對稱。與 DEF-101-524 同缺陷類別，差別是那輪修的是主控一次性寫檔，這次在 production 框架碼裡、每次 rule fire 都發生。

【前提訂正（本輪 Pkg-2 實測，推翻主控任務書的技術前提）】任務書寫「Python 3.11 的 Path.write_text **不吃** newline 參數，要改用 open(..., newline="") 或寫 bytes」——實測不成立：本機 .venv Python 3.11.9 `inspect.signature(Path.write_text)` = (self, data, encoding=None, errors=None, newline=None)；write_text('a\nb\n', encoding='utf-8', newline='') → b'a\nb\n'（CR=0），未帶時 → b'a\r\nb\r\n'（CR=2）。AutoClaude/.venv Python 3.12.11 簽名相同。repo 內亦已有同形先例 tools/tests/test_script_scan_surface_ssot.py:169。故採一行最小改動而非改寫成 open()/write_bytes。

### 狀態與驗證

fixed@R60（Pkg-2）：_write_rule() 的寫檔加 `newline=""` 並拆行、附完整 WHY 註解。新增 tests/test_rule_loader_eol.py 三支鎖：①record_fire 寫出的檔案 bytes 零 \r；②record_state_fires（production 高頻入口）同樣零 \r；③平台中立原始碼契約鎖（inspect.getsource(_write_rule) 必含 newline=""），因 ①② 在 POSIX 恆綠、此限制已寫進檔頭 docstring。載具自我防偽：fixture 以 write_bytes 建立並先斷言自身非 CRLF，且先斷言 record_fire/record_state_fires 的回傳值（fire_count==1／fired==['R-9.98-eol-batch']）以排除「什麼都沒寫也綠」。全部只寫 tmp_path，零觸碰真實 governance/rules/。驗證：REAL_RC=0「3 passed」；bug-injection 拿掉 newline="" → REAL_RC=1「AssertionError: _write_rule() 把 eol=lf 的 tracked 規則檔寫成 CRLF（CR x 12）」（兩支位元組鎖皆紅）；Edit 逐字還原後 REAL_RC=0「3 passed」。遙測 wiring 零退化（rule_fire/rule_catch/rules_index/governance_coverage 併入 205 passed 全綠）


---

## DEF-101-535

**發現情境**：R60 Pkg-3 Scan-B（反駁者自找 #1）；修復者先於系統 temp 拋棄式 repo 獨立取證後落地

**嚴重度**：P3（前瞻性防護缺口：repo 現況 27441 個 tracked 路徑內零此類檔名，四道閘門對此形態一律放行；對齊同家族判例 DEF-101-478。若未來有 mac 真機驗到 mac 側 git 直接接受入庫，可考慮升 P2）

**分流去向**：四處生產實作 + 兩份樣本電池（根層 tools/tests 與 AISDLC_SDD/scripts/tests）

### 現象與證據

四份 NTFS 淨化/驗證實作全數放行 Windows 主控台裝置名 `CONIN$`／`CONOUT$`：tools/check_ntfs_paths.py:_RESERVED_RE、tools/git-hooks/pre-commit:_ntfs_seg_bad 的 case pattern、AutoClaude/autoclaude/utils/logger.py:_WIN_RESERVED_NAME_RE、AISDLC_SDD/scripts/component_sanitizer.py:_WIN_RESERVED_NAME_RE。權威模型＝git for Windows 的 core.protectNTFS（Windows 預設 true）而非 Win32 建檔語意。本機實測（Win 11 Pro 26200 / Git Bash 5.2.37，拋棄式 repo）：`git -c core.protectNTFS=true update-index --add --cacheinfo` REJECT `CONIN$.log`／`CONOUT$.txt`／`CONIN$`／`conin$.log`／`CONIN$.tar.gz`／`CONIN$ .log`／`CONOUT$   .txt`（大小寫、多重副檔名、尾隨空白皆不影響），protectNTFS=false 則全部 ACCEPT；實害＝以 protectNTFS=false 提交後用預設設定 clone → `error: invalid path 'CONIN$.log'` + `fatal: unable to checkout working tree`、rc=128、`ls -b` 空、`git status --porcelain` 顯示 `D CONIN$.log / D plain.txt` ⇒ 整個工作樹開不出來，連無關檔案一併消失（與 R57 已修的 DEF-101-478「保留名+尾隨空白」破壞同級）。同批對照 `CLOCK$.txt`／`CLOCK$ .txt` 連 protectNTFS=true 都 ACCEPT 且 clone rc=0 正常簽出 ⇒ 三個 `$` 裝置名不可綁成一組處理（兩個有害、一個無害）；`CONIN`／`CONIN.log`（少了 `$`）亦 ACCEPT。另訂正 check_ntfs_paths.py docstring 一句失實：原稱「COM0/LPT0 皆非 Microsoft 官方保留名、純保守納入」，實測 git REJECT `LPT0` 但 ACCEPT `COM0` ⇒ LPT0 屬必須擋。

### 狀態與驗證

fixed@R60（Pkg-3）：四處正則/case 加入 `CONIN$`／`CONOUT$`（正則 `$` 轉義；bash 以單引號界定 `'CONIN$'` 使 `$` 成字面值，POSIX 標準、bash 3.2 相容，不依賴「$ 後接非展開字元視為字面」邊角行為）；刻意不納入 `CLOCK$` 並於 benign 樣本常駐 `CLOCK$ .txt`、NON_RESERVED_NAMES 常駐 `CLOCK$`/`CONIN` 釘住此決策。樣本電池兩側逐字同步（RESERVED_NAMES +2、RESERVED_TRAILING_SPACE(_SEGMENTS) +`CONIN$ .log`、BENIGN +`CLOCK$ .txt`）。鑑別力：四份實作逐一單獨注入（移除新裝置名）皆轉紅且訊息可歸因——I1 `unexpectedly None : 未攔下保留裝置名形態 'CONIN$ .log'`／I2 `1 != 0 : bash 版未攔下…（rc=1）`／I3 `logger.py 未攔下尾隨空白保留名 'CONIN$ .log'`／I4 `未攔下尾隨空白保留裝置名 'CONIN$ .log'`；反向 I10（把 CLOCK$ 加進正則）→ `誤判良性路徑段 'CLOCK$ .txt'`。還原後八檔 hash 逐位元組相同。收工驗證：179 passed/141 subtests、check_ntfs_paths rc=0（0 違規）、LOC 20361/20438、ruff 全綠。


---

## DEF-101-536

**發現情境**：R60 Pkg-3 Scan-B B-02（掃描者原判 CONFIRMED、任務書指示「四處統一處理前導空白」）；修復者以自身實測推翻修法方向

**嚴重度**：P3（文件與鎖的缺口，非程式行為缺陷：四處行為分歧無任何記載也無機械鎖，導致每輪掃描都會重新把它當鏡像缺口回報；對齊 DEF-101-336「帳本/文件記載與現況不符」判例）

**分流去向**：四處生產實作註解 + 兩份樣本電池 + 三支新斷言

### 現象與證據

「保留裝置名 + **前導**空白」形態四份實作 1 擋 3 放，且樣本電池無此鏡像形態（無任何一側設鎖）。實測對照（21 樣本，bash 載具先過 CON.txt=BLOCK/hello.txt=pass 自檢）：' CON.txt' → check_ntfs pass／pre-commit pass／logger ' CON.txt'（原樣）／sanitize_component '_CON.txt'（因首行 `.strip()` 剝掉前導空白而暴露保留名）。**關鍵訂正：這不是「三處漏擋」而是「一處多擋」**——git（core.protectNTFS=true）對 ' CON.txt'／'  COM1.log'／' con.txt'／' CON'／' NUL .log'／' CON .txt'／' CONIN$.log' 全部 ACCEPT（git 只在路徑段起頭比對保留名，前導空白使比對失配），只含前導形態的 repo clone rc=0、工作樹有檔、status 空、payload 讀回正確；Win32 只吞尾隨空白/句點不吞前導，本機實測 ' CON.txt'／' CON'／'CON.txt'／' CON .txt' 四者同時共存於同一目錄、os.listdir 全部列出、各 10 bytes 可讀回。⇒ 在兩個 validator 加擋前導空白＝純新增偽陽性（擋下 git 與 Windows 都接受的檔名），零實害可擋。

### 狀態與驗證

fixed@R60（Pkg-3，**修法方向與掃描者提案相反、依自身實測決定**）：刻意**不**加擋前導空白（採反駁者裁決的 (B) 案），改把「三放一擋」從『疑似漏修』定案為『刻意不對稱』並**雙向**設鎖。① 新增 SSOT 樣本組 `LEADING_SPACE_RESERVED_SEGMENTS`（6 筆，含前導+尾隨疊加 ' NUL .log' 與新裝置名 ' CONIN$.log'），AISDLC_SDD 側鏡一份 `LEADING_SPACE_RESERVED`，TestCrossSubprojectSampleParity 新增第三支斷言逐字鎖住。② 四處各自設鎖：check_ntfs_paths 與 pre-commit 必須放行、logger 輸出**逐字不變**（比「不加 `_` 前綴」更嚴）、component_sanitizer 必須加前綴。③ 四份實作與兩份樣本檔寫入自足實測理由，明載「下輪掃描者若再把它當鏡像缺口回報，請先讀本段實測」。R57 邊界教訓已守：完全未新增任何 strip，故純句點防禦不可能退化，仍逐一實測 '.'／'..'／'....' 四處皆 BLOCK 或退化為 'untitled'、' .txt'／'   .gitignore' 四處皆放行。鑑別力（反向注入）：I5 check_ntfs rstrip→strip → `validator 攔下了 git 與 Win32 都接受的前導空白形態 ' CON.txt'`（6 樣本全紅）；I6 pre-commit 加前導剝除迴圈 → `0 != 1 : bash 版攔下了…`；I7 logger rstrip→strip → `'_ CON.txt' != ' CON.txt'`；I8 sanitizer .strip()→.rstrip() → `應暴露保留裝置名並加前綴 ' CON.txt'：' CON.txt'`（證明多擋那一側也真被鎖）；I9 樣本刪一筆 → `Lists differ`。刻意**不**動 component_sanitizer 的 `.strip()`（Rule 3：會改變所有含前後空白的合法輸入的既有輸出，例 ' myproject' → ' myproject'）。


---

## DEF-101-537

**發現情境**：R60 Pkg-3 Scan-B B-01（掃描者原判 P2、反駁者訂正 P3 並指出三處理由要修）

**嚴重度**：P3（前瞻性防護缺口、repo 現況 live 違規＝0；對齊 DEF-101-483／DEF-101-478 判例。掃描者原評 P2 浮報：同家族 DEF-101-364 給 P2 是因當場掰出 9 筆 live 違規）

**分流去向**：tools/tests/test_windowsapps_guard_cross_consistency.py（.py 側，與既有 .sh／.ps1 兩側同政策：只排凍結版與測試檔、無前綴縮面）

### 現象與證據

WindowsApps 空殼 guard 家族的 repo-wide「零 guard 前瞻掃描」只做 bash 與 .ps1 兩側，.py 側缺一條軸。兩側各有兩條（.sh：test_repo_wide_scan_finds_no_unmigrated_sh_scripts + test_repo_wide_scan_finds_no_zero_guard_python_calls；.ps1：test_ps1_mentions_of_windowsapps_all_go_through_ssot + test_python_calls_in_ps1_all_go_through_ssot），Python 側只有 test_windows_apps_predicate_impls_are_all_registered 一條，而它的雙錨（函式名 `def *windows*apps*` ∪ 引號界定 `"windowsapps"`）都長在**判斷式實作**上，對「整支檔案不提 WindowsApps、只把裸 python 名交給 OS 解析」的形狀結構性失明（`_has_zero_guard_python_call` 在 .sh 側處理的正是這個形狀，R44 曾在該側掰出真實命中）。實測：bare subprocess／which() 無 guard 的自建樣本 `_matches_stub_anchor` 皆 False，而對照組（第二份 predicate 實作）為 True ⇒ 鎖沒壞、是掃描面缺這個形狀。live 違規＝0（我自寫 AST 掃描器獨立確認：394 支候選生產 .py，`shutil.which('python'/'python3')` 與 subprocess 裸 argv[0] 皆空，窄判準僅命中 2 支 `sys.executable or "python3"` 兜底）。三項理由訂正：(1) 本項屬**呼叫端納管 enrollment** 軸而非 CrossPlatform_Scan_Dimensions.md §(2) 的「三份實作等價」軸（等價軸在 Python 側已有機械鎖：test_bootstrap_core_py_has_symmetric_stub_detector + test_bootstrap_core.py 五支行為測試含 bug-injection）；(2) 因 bootstrap 悖論（guard 須在 Python 可用前就能運作），Python 側那份只在真直譯器已存在時才跑，暴露面比 .sh/.ps1 **窄**，非掃描者所稱「最後也最容易被繞過的一環」；(3) 「文件過度樂觀」只對一半——該檔 R56 SD 註解已載明層數不足，但帳本無條目。

### 狀態與驗證

fixed@R60（Pkg-3）：新增 .py 側第二條軸——`_BARE_PY_COMMAND_RE`（字串常數首個空白分隔 token 恰為裸 python/python3）+ `_docstring_constant_ids()`（AST 天然排除註解、另主動排除 docstring）+ `_bare_python_command_literals()`（parse 失敗 fail-loud）+ `_has_zero_guard_bare_python()` + 角色註記註冊表 `_ZERO_GUARD_BARE_PY_SITES`（8 筆：2 筆真兜底 `sys.executable or "python3"`／6 筆非呼叫＝docker image tag、人工修復提示字串、argparse prog、evaluator 首 token 白名單、薄殼比對樣式、venv 路徑片段）+ `_normalize_latest_rel()` + 等值斷言（多/少雙向 + 掃描面塌陷保護）+ 11 支常駐鑑別力測試。刻意採寬鬆字面值判準（比照 .sh 側 `_invokes_python_bare`）：實測窄判準只命中 2 支且**不含 bootstrap_core.py 自己**——本 repo 正典形狀是「候選名放 list literal + shutil.which(變數)」，窄判準對它全盲。相對 .sh/.ps1 的結構性優勢：走 AST，註解/docstring 由語法結構排除，不需 `_strip_bash_comment` 那條 R46 已證為無底洞的路。同時訂正因本修復而失實的既有宣稱（該檔原寫「Python 側只有這一層、破了本鎖即零訊號」→ 改寫為兩層互為補位，並明講合併後仍不涵蓋全類別）。三段式邊界宣稱全部實測後寫入。鑑別力：端到端注入（tracked 生產檔暫加 `"python -m nothing"`）→ `First differing element 6: 'tools/check_ntfs_paths.py'`；反向刪註冊表一筆 → `- 'tools/lib/platform_utils.py']`；判準弱化（`python3?`→`python3`）→ 3 failed；docstring 排除失效 → test_docstring_only_mention_is_not_flagged 紅；正反 12 passed。


---

## DEF-101-538

**發現情境**：R60 Pkg-3 修復者自我複核時發現（本輪自己的修復一度造成，非既有缺陷；含「第一版鎖注入不紅」的二次自我打臉）

**嚴重度**：P3（潛在鎖弱化：功能不受影響、當下無實害，但既有前瞻掃描的鑑別力在無任何訊號的情況下對三份實作歸零）

**分流去向**：四處生產實作（交替清單順序 + 🔴 註解）+ tools/tests/test_windows_forbidden_filename_parity.py（新機械鎖）

### 現象與證據

**聯集錨會讓單錨失明且完全無訊號**（新缺陷類別）。tools/tests/test_windows_forbidden_filename_parity.py::test_registered_sites_match_repo_scan_exactly 取錨①（保留名清單 CON→PRN→AUX→NUL 依序、間隙 ≤5 字元）∪ 錨②（禁用字元集合 `<>:"|?*`）。R60 為納入 CONIN$/CONOUT$ 而把它們插在 `CON|` 與 `|PRN` 之間，間隙由 1 變 17 → 實測 check_ntfs_paths.py／tools/git-hooks/pre-commit／logger.py **三處同時**掉出錨①（component_sanitizer.py 僅因既有 docstring 另有一份斜線分隔同序字樣而倖存），而等值斷言因錨②仍命中而**照樣全綠、零訊號**。後果不是立刻壞掉，而是未來錨②被改寫、或新的第 5 份實作照抄「插中間」寫法時，repo-wide 前瞻掃描對它靜默失明。第二層發現：補鎖第一版直接重用錨①，**注入實測不紅**（`27 passed`、REAL_RC=0）——因為修法留下的說明註解本身含一份管線分隔同序字樣，自我滿足了粗粒度錨（＝該檔「錨不剝註解」取捨的可見代價，第一次由本輪自己兌現）。

### 狀態與驗證

fixed@R60（Pkg-3）：① 四處一律把新裝置名移到交替清單**尾端**（`^(...)$` 與 case 皆完全錨定，交替順序不改變匹配集合，功能零變更已實測：bash 側 21 樣本 BLOCK/pass 逐筆與 reorder 前相同、`bash -n`／`sh -n` 皆 rc=0），四處各加 🔴 註解說明順序有意義、勿「整理」。② 新增機械鎖 test_each_authoritative_impl_keeps_base_device_names_adjacent，從註冊表以「角色＝實作」推導 4 份（不另建第 5 份硬編清單，並斷言恰 4 份以防前提漂移）。③ 鎖的判準從錨①改為更嚴的**構造形** `_BASE_DEVICE_NAMES_ADJACENT_RE = CON\|PRN\|AUX\|NUL`（管線分隔、零間隙），四處註解改用頓號分隔以免再自我滿足；assertRegex 改 assertTrue(search)（前者失敗時會 dump 整支 logger.py 約 170 行、訊號被雜訊淹沒）。**殘留 fail-open 已如實揭露於 docstring**：若有人在註解裡寫出管線分隔同序字樣，本鎖會被同一手法滿足；徹底根治需剝註解／AST 解析四種語言，而 R46 已證那是無底洞——本鎖只主張攔下「無意識地插中間」這個真實發生過的動作，不主張攔下刻意偽裝。鑑別力：reorder 前後逐檔量測 anchor1 由 False,False,False,True → True,True,True,True；第一版鎖對同一注入 REAL_RC=0（不紅）、收緊後 REAL_RC=1 `保留名交替構造已讓四個基本裝置名不再相鄰`，還原後綠。


---

## DEF-101-539

**發現情境**：R60 Scan-C C-01（掃描者提出、反駁者獨立重現並訂正 title 失實）＋本包程式化全掃複核

**嚴重度**：P2（鎖存在但從不執行＝形同不存在；同型判例 DEF-101-509「Windows 專屬腳本語法閘門在 Windows 上 skip」於 R59 評 P1，本筆守的面較窄故維持 P2）

**分流去向**：本輪修復（Pkg-4 Scan-C）：載具形態改寫 ＋ 補治本層 repo-wide 前瞻鎖

### 現象與證據

**「兩平台排程能力對等契約鎖」寫成 pytest 模組層函式風格，而四道執行 tools/tests 的閘門全部走 unittest discover ⇒ 這道鎖從落地起從未跑過一次**。tools/tests/test_schedule_capability_parity.py（R22 為 DEF-101-233/259 落地）以 `def test_*` 寫在模組層；`unittest.TestLoader().discover()` 只收 TestCase 子類。實測：`python -m unittest tools.tests.test_schedule_capability_parity` → `Ran 0 tests in 0.000s / OK`（rc=0）；同一檔 `pytest` → `6 passed`。四道閘門＝tools/git-hooks/pre-push:210、.github/workflows/root-infra-ci.yml:293、macos-compat-ci.yml:314、windows-compat-ci.yml:420（皆 `run_root_unittests.py`，tools/run_root_unittests.py:69 `discover(pattern="test_*.py")`）。**訂正掃描者失實處**：原 title 寫「落地 5 輪從未跑過」低報約 7 倍——`git log --follow` 顯示落地於 0053f2a（2026-07-22，R22），至 HEAD 之間帶「相容性 R」的收輪 commit 有 **34 支**（R23~R59，R58 那輪另已作廢）。**守門缺口是系統性的**：MIN_TESTS 只抓「大規模消失」，抓不到「單檔貢獻 0」——實測 MIN_TESTS=661 與 discover 實況 661 完全相等（缺席已固化進下限），且 RATCHET_STALE_RATIO=1.25（826 才紅）保證永無訊號。自寫探針對 43 支 test_*.py 逐檔 discover ＋ AST 統計：ZERO-COLLECTED 僅此 1 支、模組層 test_ 函式僅此 6 支、「帶 test_ 方法但未繼承 TestCase 的類別」全庫 0 支

### 狀態與驗證

fixed@R60：① `test_schedule_capability_parity.py` 6 支改寫為 `unittest.TestCase` 方法（斷言主體與訊息逐字保留 R22 原文，只換載具——形態才是缺陷），並補上該檔在 43 檔中唯一缺席的「執行：python3 -m unittest discover」docstring 行（坐實是漏接線而非刻意選 pytest）；② 治本：同檔新增 `TestUnittestDiscoverConformance`，三種靜默丟棄形狀全覆蓋——(a) 用 discover 本身（與四道閘門同一顆機制）驗每支 test_*.py 至少貢獻 1 支、(b) AST 驗無模組層 `def test_`（(a) 抓不到：檔案若同時有 TestCase 類別會綠而模組層那幾支仍被丟棄）、(c) AST 驗無「帶 test_ 方法卻未繼承 TestCase」的類別，另加掃描面自檢（<40 份即紅）。**放在既有 parity 測試內而不新建掃描器檔案＝沿用 DEF-101-519（R59）已裁定的折中慣例**，已在 class docstring 明寫該理由與可追溯性。**bug-injection 三向**：建臨時 probe 檔注入 pytest 模組層函式 → (a)(b) 同時翻紅並逐一點名（FAILED failures=2）；注入「非 TestCase 類別 ＋ 另放一個真 TestCase」→ 只有 (c) 翻紅（FAILED failures=1，坐實 (c) 補的是 (a) 看不到的殘留洞）；注入能力缺失（`[switch]$Status`→`$StatusQuery`）→ parity 鎖本身翻紅（FAILED failures=2）。所有注入皆以 Edit 還原並 md5 逐位元組核對（4571ebca…→4571ebca…），**未用 `git checkout --`**。**驗證**：改寫後 `Ran 9 tests / OK`（per-file discover 0→9）；受影響模組 198 tests OK；ruff 全過。**殘留（如實記載）**：本鎖住在 test_schedule_capability_parity.py 內，該檔若被整支刪除則鎖一併消失（緩解＝該檔名已被 check_script_parity.py:436 與 windows-compat-ci.yml:262 引用，且 MIN_TESTS 會掉）


---

## DEF-101-540

**發現情境**：R60 Scan-C C-02（掃描者提出、反駁者以 pyyaml 逐 job 稽核與 git log -S 獨立重現並加強）

**嚴重度**：P3（維持裁決評級。保守的一端：L904 是外顯於 CI run 標題的宣稱、非僅內部註解，覆核者若上調 P2 不反對；壓在 P3 的理由是它緊鄰自己的反例）

**分流去向**：本輪修復（Pkg-4 Scan-C）：三處據實改寫 ＋ 新增全檔掃描鎖

### 現象與證據

**R57 已判定失實並訂正過的「本 workflow 全部／其餘步驟一律 `shell: pwsh`」宣稱，在同一檔案內以 step name ＋兩處註解逐字存活——訂正只改了檔頭**。站點（改動前行號）：windows-compat-ci.yml:904（step **name**，會出現在 GitHub Actions run 的步驟標題上）、:907、:939-940。pyyaml 逐 job 實測：windows-smoke（windows-latest）pwsh 19／bash 1；windows-nightly-full（windows-latest）**powershell 2**／pwsh 3；windows-nightly-alert（ubuntu-latest）implicit 3；全檔無 workflow/job 層 `defaults:` ⇒ 兩種「一律」說法皆假，且 L904 那一步**自己就是 `shell: powershell`**、其下一步也是。現行機械鎖 `test_gha_action_versions.py::TestWindowsCiHeaderSnapshotLock` 只比對檔頭快照表 vs YAML 實況，對散文零訊號（該檔 14 tests 全綠）。DEF-101-486 現象欄逐字點名了這些站點而處置欄沒動它們＝部分修復被記成 fixed（Rule 12）。**另訂正一項歷史記載**：L939-940 是「R48 Architect REJECT 理由」的引述，`git log -S "shell: powershell" -- .github/workflows/windows-compat-ci.yml` 實查顯示該 workflow 早在 **1175555（2026-07-15）** 就已有一步原生 `shell: powershell`，比 R48（0e346da，2026-07-26）**早十一天** ⇒ 那句概括在寫下的當時就已失實，不是「曾為真、後過期」的合法歷史記載

### 狀態與驗證

fixed@R60：① 三處改寫，**沿用 R57 政策不寫死支數**——step name 與註解改為「以 `shell: pwsh` 為主要引擎，實際分佈與三類刻意例外見檔頭逐 job 稽核表（本步驟自己就是該表 ③ 的例外之一）」；R48 引述段據 `git log -S` 證據訂正為「該概括在寫下的當時即失實」，保留真正成立的窄斷言（「在本步驟補上之前，本 workflow 沒有任何一步用原生 PS 5.1 執行過 install_post_commit.ps1」）。② 新增 `tools/tests/test_smoke_ci_sync.py::TestWindowsCiShellClaimConsistency`（3 支）——**刻意攤平換行與註解符再掃、不逐行比對**：三個殘留站點中最後一個正是跨兩行寫的，逐行掃描對它天生零訊號，那正是它能在 R57 訂正後存活的原因之一。workflow 檔頭加一對 `CLAIM-QUOTE-BEGIN/END` sentinel 界定「刻意逐字引述舊宣稱以資訂正」的豁免區；鎖反向斷言 sentinel 兩端各恰 1 次、豁免區 ≤90 行（實測 68 行）、且豁免區內至少一筆引述能被正則命中（**鏡子自證**：正則被改寬鬆到零鑑別力時正控先紅）。③ 本鎖落地當下即**逮到修復包自己**寫在 step 註解裡的三筆引述（`Lists differ: ['全部／其餘步驟一律 shell: pwsh', '其餘所有步驟卻一律`shell: pwsh', '全部步驟一律 shell: pwsh'] != []`），逼它們改成指回豁免區、不各自複述一遍——這段經過已寫進檔頭。**bug-injection 兩向**：把宣稱塞回 step name → 翻紅並印出命中字串（FAILED failures=1）；刪掉 END sentinel → 3 支同時紅（`0 != 1 : CLAIM-QUOTE-END sentinel 出現 0 次`）；兩次皆以 Edit 還原並 md5 逐位元組核對（ea02b5b2…→ea02b5b2…）。**驗證**：shell 分佈改動前後**完全相同**（pwsh 19/bash 1；powershell 2/pwsh 3；implicit 3），YAML safe_load OK，姊妹鎖含檔頭快照鎖共 57 tests OK。**方法論邊界（如實揭露、非窮舉）**：正則四段式 `(全部|其餘|所有)→(步驟|step)→一律→pwsh` 已實測涵蓋單行/跨行/全形頓號分隔/反引號包裹四種寫法；**未涵蓋**同義改寫（「所有 step 清一色 pwsh」「無例外皆為 pwsh」）與英文寫法，故它擋的是**復發（照抄舊句）**而非「所有可能的失實宣稱」


---

## DEF-101-541

**發現情境**：R60 Scan-C C-03（掃描者提出、反駁者收窄範圍並訂正兩處失實：承接者其實部分存在＝DEF-101-490，且 md5 分群是本機 CRLF 假象）

**嚴重度**：P4（採納反駁者降級：暴露面嚴格小於已結案的 DEF-101-434〔那是根層真會跑的 CI job 仍只給 P3〕——這 30 份在 GitHub 永不觸發〔巢狀路徑〕、v0.01~v0.29 依 Copy-on-Evolve 禁改、v0.30 檔頭自述是「給尚未存在的 Hub Registry repo 的 sample」。掃描者自陳本筆與 Mac/Windows 相容性無關、應標排除範圍外，評級跟著它走）

**分流去向**：本輪修復「懸空自陳＋無承接者」這一半（Pkg-4 Scan-C）；**LATEST 升版決策本身 routed → AISDLC_SDD 凍結/LATEST 政策擁有者**（見狀態欄的解鎖條件與期限）

### 現象與證據

**`tools/check_gha_action_versions.py` 檔頭的到期風險揭露自陳「需…記入缺陷帳本」，而帳本零記載 ⇒ 承接者不存在（懸空的孤兒揭露）**。實查：git-tracked 巢狀 workflow 30 份（`AISDLC_SDD/AISDLC_SDD_v0.NN/.github/workflows/hub-push.yml`），`git ls-files -s` 收斂為**單一 blob a24abefa91cbc4532300aebf86ed3c84d0ba428b**（committed 內容逐位元組相同），全為 Node20 世代（checkout@v4／setup-python@v5／upload-artifact@v4）。**WebSearch 重新查證官方時程**：runner v2.328.0 起支援 Node20/24 且預設 Node20；2026-06-16 起 runner 預設改 Node24；**2026-09-16 Node.js 20 自 runner 完全移除**（過渡期 `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true` 於移除後失效）。**收窄範圍（採納反駁者訂正）**：「掃描面盲區」那一面已登記且已結案（DEF-101-490，archive_27:27，同一批 30 份、同一次 SA-R57-05 裁定，fixed@R57）；真正沒有承接者的只有「LATEST 模板是否隨根層升版」這個**升版決策本身**，故本筆為 DEF-101-490 未竟的第②子項（延伸自 DEF-101-490／DEF-101-434）。**另訂正一項會害下輪走死路的假象**：`md5sum` 比對這 30 份會看到兩群不同雜湊（v0.01~v0.13 一群、v0.14~v0.30 一群，差 232 bytes），看起來像「內容已分裂」的鐵證，實為本機 checkout 的 CRLF 殘留（`git ls-files --eol` 顯示部分版本工作樹 `w/crlf`）；正確載具是 `git ls-files -s`

### 狀態與驗證

partially-fixed@R60（自陳不再懸空）／routed（升版決策）：① `check_gha_action_versions.py`〈掃描面邊界〉⚠️ 段改寫為完整分流結論：凍結版依 Copy-on-Evolve 不動；**LATEST 是否升版刻意不由 CI 工具鏈側代決**（該檔自述是 sample、要不要升屬框架散佈品質命題，且升 LATEST 會讓「各版此檔為同一 git blob」這個目前可機械核對的不變量首次分裂，代價需由該側評估）；依 R57 政策把寫死的「30 份」改為執行期實查後印出；另補「複核者陷阱」段記載 md5 假象與正確載具。② **讓自陳不可能再靜默腐化**（這才是 C-03 的實質修復）：新增 `_NESTED_DISCLOSED_GENERATION` 登記快照 ＋ `nested_excluded_workflows()`／`nested_action_generation()`／`nested_generation_drift()`，把「實測全為 Node20 世代」從散文升為**機械斷言並接進 gate 的 rc**（雙向：登記了卻消失／實測有卻沒登記／版本不符）；`git ls-files` 抽成共用 helper `_tracked_workflow_files()`，與既有 `_audit_scan_surface()` 共用同一次查詢與同一組正則，不製造第二份 workflow 檔判準。紅燈訊息明寫「正確處置不是改快照了事，而是先回答 LATEST 該不該升版、同步 ⚠️ 段與帳本，最後才更新快照」。③ **bug-injection**：把快照 checkout v4→v5（模擬「有人升了 LATEST 卻沒同步揭露」）→ gate **REAL_RC=1** 並指名 `actions/checkout：登記快照 v5 ≠ 實測 ['v4']`；Edit 還原後 md5 逐位元組相同（d10cef75…→d10cef75…）、REAL_RC=0。四情境探針另證：模擬升版 3 行、模擬掃描面斷掉 3 行「登記快照列為 vX 但實測已不存在」（fail-open 被擋）、模擬新增未登記 action 1 行。**驗證**：既有 test_gha_action_versions + test_check_gha_action_versions 36 tests OK（含對真 repo `main()==0` 兩支）。**🔴 解鎖條件（給承接者）**：期限 **2026-09-16**（Node20 自 runner 移除；已 WebSearch 查證）。屆時若 LATEST 仍為 Node20 世代，下游複製該模板即壞。決策要點：(a) 只動 LATEST 不動凍結版，符合 Copy-on-Evolve，但會首次打破 30 份單一 blob；(b) 若決定升版，機械鎖會當場紅並指路，必須同步 ⚠️ 段揭露與本列狀態。**不建議的做法**：直接改快照讓 gate 轉綠而不回答升版問題——那正是本次修復要消除的行為


---

## DEF-101-542

**發現情境**：R60 Pkg-4 Scan-C 修復包自找（動 -Status 區塊時發現既有修復在 PowerShell 語意下不成立）

**嚴重度**：P2（既有修復實際未生效且被記為 fixed〔Rule 12〕；本輪新增的 Windows smoke 任務缺席偵測也依賴這條 exit code，若不修則「補償控制沒註冊」永遠看不出來）

**分流去向**：本輪修復（Pkg-4 Scan-C）：拆分純函式／印出函式 ＋ 把字面比對鎖升級為真的執行

### 現象與證據

**`install_windows_nightly.ps1 -Status` 的結束代碼恆為 0，DEF-101-248 的修復被 PowerShell 輸出串語意打敗，而它的回歸鎖只比對原始碼字面、從不執行，故連續多輪零訊號**。根因：`Show-NightlyStatus` 一支函式同時 `Write-Output` 報表又 `return $true/$false`，PowerShell 把函式內**所有**輸出併入回傳值 ⇒ `$loaded = Show-NightlyStatus` 實得 `Object[]`（報表字串＋布林），`if ($loaded)` 對非空陣列恆為真。**兩層實測**：(a) 語意最小化證明（無腳本參與）`function Show-Demo { Write-Output "line1"; Write-Output "line2"; return $false }; $loaded = Show-Demo` → `TYPE=System.Object[] COUNT=3`、`if ($loaded)` → TRUE；(b) 端到端（拋棄式副本，不碰 repo）把 `$TaskName` 換成不存在的名字後 `powershell -File <copy> -Status` → **REAL_EXITCODE=0**（期望 1）。**鎖為何看不到**：`test_install_windows_nightly.py::test_status_exit_code_reflects_task_existence` 只 `assertIn("$loaded = Show-NightlyStatus")`——那個字面正是缺陷本身，注入缺陷時它會全綠。後果與 DEF-101-248 原始缺陷完全相同：任何拿 exit code 做自動化判斷的 CI／監控腳本在 Windows 上恆得假陽性；而 mac 版 `install_mac_nightly.sh --status` 未載入時回非零，語意不對等

### 狀態與驗證

fixed@R60：① 拆成「純查詢零輸出」的 `Test-TaskPresent`（`return [bool]$t`）與「只印報表、刻意不回傳值」的 `Show-TaskDetail`／`Show-NightlyStatus`，決策改為 `$loaded = (Test-TaskPresent -Name $TaskName) -and (Test-TaskPresent -Name $SmokeTaskName)`。此「純函式 vs 印出函式」分離是本 repo 既有慣例（`tools/run_root_unittests.py` 的 `windows_native_skips`／`report_windows_native_skips`，理由同構——當年也是因為印出副作用混進被直接呼叫的函式而被 R43 二審抓出），已在程式註解引用該先例。② 鎖升級：既有靜態斷言改為認新的決策式，並補一條反向結構守門（`Show-TaskDetail` 函式體內不得 `return $true/$false`）；**真正有牙的是新增的 Windows-native runtime 鎖** `TestStatusExitCodeRuntime::test_status_exits_nonzero_when_tasks_absent`——把腳本複製到 temp、把兩個任務名改寫成保證不存在的名字後**真的執行** `-Status`，斷言 rc==1，並要求缺席分支那一行同時含任務名與安裝提示兩個 ASCII 標記（避免 rc=1 來自無關錯誤路徑）；改寫式抽到必須恰 1 次否則 fail-loud，不得靜默降級成「不改寫」（那會變成查真任務、鎖失效）。**斷言刻意只認 ASCII**：`powershell.exe` 以 OEM 碼頁（本機 zh-TW＝cp950）寫 stdout，比對中文會讓鎖的成敗取決於執行者的主控台碼頁（同 `windows_smoke_local.ps1` [6]「直讀位元組、不經主控台解碼」的既有取證紀律）；R60 落地時第一版即因此假紅，如實記載。**bug-injection**：把決策式改回舊寫法 `$loaded = Show-NightlyStatus` → 靜態鎖與 runtime 鎖同時紅，runtime 側逐字重現原缺陷 `AssertionError: 0 != 1`（FAILED failures=2）；Edit 還原後 md5 逐位元組相同（3cfa9e77…→3cfa9e77…）、`Ran 17 tests / OK`。**同一注入下，舊版靜態鎖會全綠**——這就是本筆要修的「鎖無鑑別力」本體。**驗證**：修復後真 repo `-Status` REAL_EXITCODE=1（AutoClaude_WindowsSmoke 未註冊），全程未真的動 Task Scheduler


---

## DEF-101-543

**發現情境**：R60 Scan-D D-01（掃描者提報、反駁者三次嘗試推翻皆失敗判 CONFIRMED；Pkg-5 落地修復並根治）

**嚴重度**：P3（同唯一直接先例 DEF-101-289 實測 severity 欄；刻意不上調至 515 的 P2——本筆只是既有表內一個數字未回填，非整表單邊缺席＋容差宣稱主動誤導）

**分流去向**：root（monorepo 根層文件＋根層 tools/tests 機械鎖；零碰 AutoClaude 生產碼、零碰 AISDLC_SDD）

### 現象與證據

ONBOARDING.md:214（§7 Windows 11 基線表 LOC 列）寫死 `total=20356 cap=20438 violations=0` 且 Windows 欄標「完全相同」，實測為 20359——且該值在 R59 自己的收尾 commit 樹上就已 stale。三棵樹獨立實測分離：R57 樹(75aab89)=20356、R59 樹(f9435c5)=20359、HEAD=20359，baseline 與計數器在兩 commit 間零變動，成因為被計數原始碼淨增 3 邏輯行。Pkg-5 修復當時再實測 `[check_loc_budget v2-tiered] total=20359 baseline=17032 cap=20438 violations=0` rc=0。本輪另證此格具有結構性易腐性：修復進行中另一並行包改 AutoClaude/autoclaude/utils/logger.py（git diff --stat：1 file changed, 10 insertions(+), 1 deletion(-)）後同一指令即回 total=20361，也就是同一輪內該格已變動兩次。屬 DEF-101-289（§7 基線落後實測，P3）／DEF-101-515（§7 表單邊缺席，P2）「寫死數字必過期」家族的第 N 次復發；歷輪處置皆為人工回填一次，零機械鎖（實查：全 repo 無任何檢查器比對過該格與 check_loc_budget 實測）。

### 狀態與驗證

fixed@R60（Pkg-5）：① ONBOARDING.md:214 填入親測最終值 total=20361（非任務書給的 20359——並行包改 logger.py 後實測已變，依 MIN_TESTS「填最終工作樹實測值、不做加減推算」紀律填我自己量到的值）；② 同格加 loc-baseline-live 錨點＋機械鎖說明＋明文寫入「填值時點比照 MIN_TESTS 重釘紀律（並行 agent 全停工後才填）」，把本格的結構性易腐性外顯成成文規則；③ ONBOARDING.md:246 R57 註加註「此為 R57 當時值……現行值見上方基線表該格」，避免同節兩數字誤導（該則為有標日期的歷史快照，依 repo 慣例刻意不回填）；④ 根治＝新建 tools/tests/test_doc_loc_baseline_freshness_r60.py（6 支 unittest.TestCase），每次跑根層閘門即 subprocess 實跑 `AutoClaude/tools/check_loc_budget.py --json`，把 total/cap/violations 三項與文件字面值比對，不符即紅並印出應填值；錨點 0／≥2 行、欄位抽不到皆 fail-loud。驗證證據：bug-injection 注入原始 stale 值 20356 → REAL_RC=1、FAIL 訊息逐字印出「修法：把該格改寫為 total=20359 cap=20438 violations=0」；還原 → REAL_RC=0 / Ran 6 / OK，並以 od -c 逐位元組核對還原。額外鐵證：這道鎖上線幾分鐘內就自行抓到一筆真實漂移（20359→20361，非合成注入），並經 git diff --stat 追出肇因包。官方閘門收錄確認（自寫 discover 攤平載具）：6 個 test id 逐字在 tools/run_root_unittests.py discover 清單內、import-failure placeholders=[]，未犯 C-01（pytest 函式風格被 unittest discover 漏收）同型錯誤。殘留（誠實揭露）：同格另一半 `8 kept / 0 broken`（lint-imports）未納入機械比對，須另跑 import-linter，已寫入該鎖 docstring 邊界段。


---

## DEF-101-544

**發現情境**：R60 Scan-D D-02（掃描者提報、反駁者四次嘗試推翻皆失敗且把證據強化一級判 CONFIRMED；Pkg-5 落地修復並根治）

**嚴重度**：P3（同家族 DEF-101-513 實測 severity 欄；不因站點數多而上調，比照 DEF-101-507 的評級理由）

**分流去向**：root＋autoclaude 文件（AutoClaude/README.md 為 AutoClaude 側文件，但機械鎖落在根層 tools/tests 以覆蓋跨子專案活文件名冊；零碰 AutoClaude 生產碼）

### 現象與證據

AutoClaude/README.md:355 仍只給 bash 形態的 `PYTHONUTF8=1 lint-imports`，是 DEF-101-513 家族第 4 個活文件站點、第三次復發。PowerShell 沒有 `VAR=value <指令>` 前綴語法：本機真 Windows PowerShell 5.1（PSVersion = 5.1.26100.8875）實測 → `PYTHONUTF8=1 : The term 'PYTHONUTF8=1' is not recognized as the name of a cmdlet... CommandNotFoundException`，且錯誤訊息完全不指向真因（看起來像 lint-imports 沒裝）；正控直呼 lint-imports.exe → `Contracts: 8 kept, 0 broken` rc=0。整份 README 的 `$env:` 出現 0 次（不是「對照隔太遠」而是「完全沒有」）。該檔在 tools/check_pytest_baseline_sites.py:62 的 _SCAN_FILES 納管名冊內，與 R59 修掉的 UserGuide 同一份名冊、同一份判準。DEF-101-513 修復欄逐字寫「本輪修復（兩份活文件）」並逐一點名 UserGuide §1.4＋根 CLAUDE.md，README 從未被任何一列提及。該家族在 R60 前零機械鎖（Pkg-5 獨立實查：全 repo 無任何檢查器碰過這個形狀，三輪皆手改）。Pkg-5 另以自寫 fence-aware 掃描器獨立重掃全部 tracked .md，確認家族活站點恰 4 個（CLAUDE.md:137、ONBOARDING.md:181、AutoClaude/README.md:355、docs/AISDLC_Agent_UserGuide.md:127），其中僅 README:355 缺對照；另探測 7 支候選活文件（CrossPlatform_Scan_Dimensions.md／AutoSDD_Iteration_Prompt_Template.md／AutoSDD_Capability_Integration_Map.md／AutoSDD_Maturity_Rubric.md／Nightly_Forensic_Discipline.md／Local_CI_Parity_Guide.md／FRAMEWORK_STATUS.md）皆 0 站點，確認無第 5 個漏網。

### 狀態與驗證

fixed@R60（Pkg-5）：① AutoClaude/README.md §測試補一塊 powershell 圍欄（$env:PYTHONUTF8=1; lint-imports）＋🔴 WHY 段（PS 無此語法、照抄的實際錯誤訊息、R57/R59/R60 三次復發史、指向新機械鎖），純新增 15 行零刪除；② 根治＝新建 tools/tests/test_doc_env_prefix_platform_parity_r60.py（13 支 unittest.TestCase）：fence-aware 掃 10 份活文件名冊（沿用 check_pytest_baseline_sites._SCAN_FILES 語意＋根 README.md＋AISDLC_SDD/CLAUDE.md＋兩份指令密集活指引），判準＝PowerShell 語系圍欄內出現前綴語法即直接違規、POSIX 或未標註語系圍欄則要求同檔存在 `$env:<同一個 VAR>` 對照；附 `envprefix-ok: WHY` 行內豁免（空 WHY 不具豁免力，比照 baseline-ok:／encoding-ok: 紀律）、名冊缺席 fail-loud、抽取數量下限 4、已知站點集合釘選。驗證證據：（a）真實文件 bug-injection——移除 README 那行 $env:PYTHONUTF8 → REAL_RC=1，訊息逐字指名「AutoClaude/README.md:355：bash 圍欄內的 PYTHONUTF8= 前綴語法全檔找不到 PowerShell 對照」；還原 → REAL_RC=0 / Ran 13 / OK，且 git diff --stat 顯示 15 insertions(+) 零 deletions＝還原逐位元組無痕；（b）第二次 bug-injection 把 _PREFIX_RE 改成 ZZ[A-Z0-9_]+ 模擬正則漂移 → FAILED (failures=7)，下限鎖逐字翻紅「全名冊只抽到 0 個 VAR=值 指令 站點 < 下限 4」，證明本鎖壞掉不可能假綠；還原後 OK 並 od -c 核對；（c）本機真 PS 5.1 雙向實測（壞形態 CommandNotFoundException／我補的形態 8 kept 0 broken EXITCODE=0）。官方閘門收錄確認：13 個 test id 逐字在 discover 清單內、import-failure placeholders=[]。刻意接受的邊界（已寫入 docstring）：對照要求為檔案級非節級；只掃 .md 活文件不掃全 repo（實測全庫掃描會撞上 SDD 各版 scenarios／docs_template 數百處 VAR=$(...) CI/CD 範本與 improving 系列時代快照，屬偽陽性且違反本 repo「歷史紀錄檔不納管」慣例）。


---

## DEF-101-545

**發現情境**：R60 Scan-E 架構最佳化（E-A-01）落地包 Pkg-6；反駁者裁決為 PARTIAL、評級由 P2 降 P3（同形狀先例 DEF-101-173／182 兩次皆 P3 且**當時都有活體漏管**，本項活體漏管為 0）

**嚴重度**：P3（前瞻性防護缺口；同形狀判例 DEF-101-173／DEF-101-182 皆 P3 且當時各有活體漏管，本項活體 0，比先例更輕，故不取 P2）

**分流去向**：本輪修復（Pkg-6）

### 現象與證據

`tools/check_script_parity.py:336` 的 enrollment 掃描名冊 `_PAIR_SCAN_DIRS = ("tools","tools/lib","AutoClaude/tools","AISDLC_SDD/scripts")` 為本檔自持、**非遞迴** glob（`:485-493` `d.glob("*.sh")/("*.ps1")`；只有 LATEST 那條 leg 用 rglob），與 `root-infra-ci.yml:193-205` 第 2 道 pwsh parse＋BOM 守門的 `Get-ChildItem -Path <樹> -Recurse`（3 棵固定樹＋LATEST 計算式樹）**形狀不一致**；且該名冊本身零完整性鎖（生產碼／測試／帳本三面 grep，唯一相關斷言是 `tools/tests/test_check_script_parity.py:217 assertIn("tools/lib", _PAIR_SCAN_DIRS)` 的成員存在性）。R60 實測：兩邊今日掃到的檔案集合**完全相同**（各 35 支、`DIFF rec-parity=[]`、`DIFF parity-rec=[]`），故無活體漏管——威脅是前瞻性的：在既有樹下新開一層子目錄放成對腳本（`tools/ops/newpair.sh|.ps1`）時 CI 掃得到、parity 看不到（修復前探針對 `tools/ops/newpair`／`AutoClaude/tools/hooks/hookpair`／`AISDLC_SDD/scripts/nested/deep.sh` 一律 False，兩個頂層正控為 True），「新增成對腳本必為機械攔截」的自述宣稱靜默失效。CI 側早在 R13（CI-4，該 step 內留有註解）就為同一風險把 `AISDLC_SDD/scripts` 補 `-Recurse` 做預防性收斂，parity 側從未跟上。

### 狀態與驗證

fixed@R60：① 新建 SSOT `tools/_script_scan_surface.py`（`SCRIPT_SCAN_ROOTS` 三棵樹＋`iter_tree_scripts()` 為**唯一**遞迴列舉實作，遞迴性只寫在一處）；② `check_script_parity._PAIR_SCAN_DIRS` 改指 SSOT（`tools/lib` 由遞迴涵蓋、不再單獨列名），`_discover_scripts()` 改走 SSOT，成對 key 改「repo 相對路徑去副檔名」（與舊「同目錄內 stem」語意等價，既有納管登記逐字不變）；③ `test_ps51_compat.scan_trees()`／`test_ps1_bom._scan_prefixes()` 的固定樹字面值一併改引 SSOT（原各持一份硬編，同組掃描面的硬編站點由 4 處降為「1 份 SSOT + CI yml + windows_smoke_local.ps1 $ps1Trees」）；④ **形狀一致性鎖**落在 `test_ps51_compat.TestPs51ScanConfigPinning.test_tree_set_matches_root_infra_ci_pwsh_step`（期望值改引 `set(SCRIPT_SCAN_ROOTS)`）——刻意不另立新檔，因新檔會成為 `test_ci_scan_anchors._SSOT_CALLERS` 的第 4 份「只接一條抽取錨」呼叫端（第一版即被該 roster 鎖當場攔下，屬 R56/R57 三複本 fail-open 形態）；⑤ 新建 `tools/tests/test_script_scan_surface_ssot.py`（7 支：單一來源／遞迴性合成假樹／完整性 git ls-files 35 支下限）。驗證：`python tools/check_script_parity.py` REAL_RC=0、輸出 `13 對 + 18 支單邊皆已納管（遞迴掃描 3 棵 SSOT 樹 + LATEST tools）`＝納管結果數字與修復前逐字相同（零行為退化）。bug-injection 兩輪皆有鑑別力：(a) `rglob`→`glob` ⇒ test_script_scan_surface_ssot rc=1 failures=3（`'AISDLC_SDD/scripts/nested/deep.sh' not found in {…}`、`'tools/ops/newpair' not found in ['tools/legitpair']`、完整性鎖列出 tools/lib 5 支）＋test_check_script_parity rc=1 failures=3＋生產守門 rc=1 印 5 筆「單邊豁免 stale：tools/lib/… 仍在磁碟但未被掃描發現」；(b) SSOT 加第 4 棵樹「docs」而 CI 未同步 ⇒ test_ps51_compat rc=1（tree_set 不符＋`KeyError: 'docs'`×2 floors fail-loud）、test_ps1_bom rc=1 failures=2。兩次注入皆以 Edit 逐行還原並複驗轉綠、CR=0。


---

## DEF-101-546

**發現情境**：R60 Scan-E（E-A-02）落地包 Pkg-6；反駁者裁決 PARTIAL、評級由 P2 降 P3，且**明確反對掃描者原始提議**（「無條件執行等於部分復活 R10 刻意退場的黑名單枚舉、對正當維護產生常態噪音」），本輪落地為訂正版而非原始理由

**嚴重度**：P3（既有設計取捨留下的殘餘窗口、今日無活體；對照 DEF-101-519「前瞻性防護缺口非現存缺陷」判 P3。掃描者原報 P2 為浮報）

**分流去向**：本輪修復（Pkg-6）

### 現象與證據

`tools/check_wrapper_thinness.py`（修復前 `:249-254`）的 `for keyword in _FORBIDDEN.get(rel, ())` 整段**縮排在 `if actual != pinned:` 內**——「hash 釘選」與「業務邏輯關鍵字」兩道防線是**串聯而非並聯**：一旦有人以檔案自己 docstring 指示的 `--print-hash` 工作流更新 pin（正常維護動作），關鍵字偵測**整組同時失效**。實測（Pkg-6 自寫探針，含兩正控）：把 `for f in "$@"; do echo "$f"; done` 注入 `tools/dev_start.sh` **並同步更新 pin** → `check_wrapper_thinness()` 回傳 `problems=[]`、82 行未達 `MAX_LINES=100` ⇒ 三道訊號全靜音。既有 10 支 `test_forbidden_*` 全走 `_make_fake_root()`＝必然 hash 紅燈態，對這條路徑天生零鑑別力（串聯實作下它們也全綠）。反駁者另證：`main(["--print-hash"])` 提早 return、完全不呼叫 `check_wrapper_thinness()`，故主動更新 pin 的開發者從頭到尾看不到 advisory（本輪並聯化後此後果自動消解——pin 更新後下一次守門執行照樣攔下）。

### 狀態與驗證

fixed@R60：`for keyword …` 整段自 `if actual != pinned:` **反縮排為並聯**，並把比對對象由原始 `text` 改為 `norm`（正規化內容，與 hash 同一份文字）。此二改動同時回應反駁者的兩點：(a) 檔案 docstring 早已記載「只在 hash 已紅時」⇒ 本輪 docstring 改寫為「**訂正串聯設計缺陷**」而非「補上未記載行為」；(b) 常態噪音顧慮 ⇒ 正規化比對讓說明性註解不再誤觸，且實測現行 10 支殼（含另一包本輪剛更新 pin 的 `AutoClaude/tools/local_ci_gate.ps1`）在 raw 與 normalized 兩種比對面命中數皆為 **0**，權威判定明文仍是 hash。逃生口不新增機制：確屬薄殼職責所需者自 `_FORBIDDEN[rel]` 移除該字並就地註明 WHY（清單本身即決策紀錄、改動會出現在 guard 檔 diff 上）。誠實揭露的殘餘偽陽性面已寫進 docstring：`_normalize()` 不剝行尾行內註解，`$x = 1  # for the win` 仍會命中。新增 `tools/tests/test_check_wrapper_thinness.py::TestKeywordDetectionParallel`（4 支：.sh 側本體／.ps1 側對稱／正控 A「只更新 pin 無外溢＝零問題」／正控 B「整行註解含關鍵字字樣不得命中」），17→21 支。bug-injection：把該段縮排回 `if` 內 ⇒ rc=1 failures=2，`pin 更新後關鍵字偵測失效＝兩道防線又被接成串聯（R60 E-A-02 迴歸）：[]` 與 `.ps1` 側同款，兩正控在紅燈側仍 ok（證明紅不是「一律回報」）；反縮排還原後 `Ran 21 tests OK`、`python tools/check_wrapper_thinness.py` REAL_RC=0。


---

## DEF-101-547

**發現情境**：R60 Scan-E（E-A-03）落地包 Pkg-6；反駁者裁決 PARTIAL、評級由 P2 降 P3，且指出**掃描者自己的 grep 輸出漏掉整個檔案**（4 種語意／9 處／2 個具名 helper 三個數字全部低估）

**嚴重度**：P3（常設前瞻性要求未落到本家族、非現存缺陷；同構判例 DEF-101-519 判 P3。掃描者引「兩次都判 P1」支撐 P2 是混淆層級——那兩次是有活體後果的**實例**，本項是**預防機制缺席**）

**分流去向**：本輪修復（Pkg-6）；1 處（語意⑤所在檔）跨包 routed 給 R60 Pkg-3

### 現象與證據

`tools/tests/` 內「本機有哪個 PowerShell 引擎、拿哪一個去跑」在 R60 實查為 **6 檔／10 處功能碼／5 種語意**，無具名 SSOT、亦無防「第 N+1 份選錯」的鎖（`grep -rn 'which("powershell")|which("pwsh")' tools/tests/*.py tools/*.py` 完整輸出：語意①生產引擎 5.1 優先 6 處＝test_bootstrap_ps1:46／test_dev_start_ps1_lastexitcode:35／test_git_hooks_install_common:447,472,495／test_install_windows_nightly:214；語意②任一引擎 skip 述詞 5 處＝test_bootstrap_ps1:38／test_dev_start_ps1_lastexitcode:30／test_git_hooks_install_common:429,468,491；語意③Windows 且有引擎 2 處＝test_bootstrap_ps1:33／test_windowsapps_guard_cross_consistency:230；語意④只認原生 5.1 2 處＝test_nightly_interpreter_determinism:200,233；**語意⑤pwsh 7 優先 1 處**＝test_windowsapps_guard_cross_consistency:57-58，另有 5 個消費點 :153/:169/:230/:233/:249，其中 :169/:249 真的拿它去 subprocess 跑 PowerShell 驗 WindowsAppsGuard 行為）。語意⑤與 R59 **DEF-101-509** 拍板的「生產引擎（5.1）優先」**方向相反**，而被測檔 `tools/lib/WindowsAppsGuard.ps1` 正落在 `test_ps51_compat.py:203-209` 的 PS 5.1 政策樹內（8 支）。`tools/tests/_platform_helpers.py` 實查零引擎述詞。本機 `which pwsh` rc=1、`which powershell` 命中內建 5.1 ⇒ 語意⑤在本機活體影響為零，實害只在「同時裝有兩者」的環境（GitHub-hosted runner 兩者皆預裝、winget 裝過 pwsh 的開發機亦然）。

### 狀態與驗證

fixed@R60（9/10 處）：新建 SSOT `tools/tests/_ps_engine.py`——`PRODUCTION_ENGINE_PRECEDENCE=("powershell","pwsh")`（順序即判準）＋五個具名述詞 `production_engine()`／`any_engine_available()`／`windows_with_engine()`／`native_ps51()`＋`windows_with_native_ps51()`／`available_engines()`；語意③④刻意不與①②合併（WHY 逐字搬進述詞 docstring：`.cmd` 需 cmd.exe 解譯故「有引擎」不足以排除裝有 pwsh 的 macOS/Linux 開發機；PATH 反斜線正規化語意只在原生 5.1 成立、fallback 即失去鑑別力）。**不塞進 `_platform_helpers.py`**：該檔 docstring 自陳收納契約僅兩類並記載 R57「雜物抽屜早期訊號」教訓，故比照同目錄 `_ci_scan_anchors.py` 先例獨立成檔。9 處呼叫端全數改走 SSOT（5 檔），並順手清掉因而未用的 `import shutil`／`import platform`。**刻意保留 1 處行內 `shutil.which`**：`test_install_windows_nightly.py::test_engine_selection_prefers_windows_powershell` 是這條判準的獨立 ground truth（兩邊都用同一顆述詞算 expected 時，優先序寫反會一起寫反、斷言恆綠），已就地補 WHY 並在反增生鎖登記永久豁免＋stale 自檢。新建 `tools/tests/test_ps_engine_ssot.py`（11 支）：優先序常數釘選／**合成「兩引擎都在」驗方向**（🔴 本機無 pwsh 7，不合成就對整個缺陷類別零鑑別力）／只有 pwsh 時兜底／`native_ps51()` 不得 fallback／repo-wide 反增生掃描（含掃描器自身鑑別力自檢 3 必中＋3 必不中）／永久豁免 stale 自檢／正向鎖「5 個已遷移檔必須真的 import SSOT」。bug-injection 兩輪：(a) 優先序改 `("pwsh","powershell")` ⇒ rc=1 failures=2（`Tuples differ` ＋ `兩引擎皆在時選了 pwsh 7——與 DEF-101-509 判準方向相反`），**同一注入下 R59 既有鎖 test_install_windows_nightly 仍 `Ran 13 tests OK` rc=0** ⇒ 逐字坐實本機既有載具對 pwsh-優先零鑑別力；(b) 在 test_smoke_ci_sync.py 追加第 10 處行內 which ⇒ rc=1 `{'test_smoke_ci_sync.py': [673]} != {}`，還原後 sha256 與備份逐位元組相同（`88bc80be19d71dd2…`）、`grep -c _REINVENTED`=0。落地時本檔自己的 stale 自檢當場抓出我誤把 `_ps_engine.py` 登記為永久豁免（它用迴圈變數呼叫 which、本不命中字面 regex），已改為整檔排除並留成註解。


---

## DEF-101-548

**發現情境**：R60 Scan-E（E-refuter-2 自找）落地包 Pkg-6 查證；該檔由 R60 Pkg-3 獨佔，Pkg-6 依分包鐵律不得改動

**嚴重度**：P3（與 DEF-101-509 同類判準錯誤、方向相反；本機零活體，實害限於同時裝有兩引擎的環境）

**分流去向**：跨包 routed 給 R60 Pkg-3（該檔獨佔者）；Pkg-6 側已把判準本體落成 SSOT 並鎖住方向

### 現象與證據

`tools/tests/test_windowsapps_guard_cross_consistency.py:57-58` `def _pwsh_exe() -> str | None: return shutil.which("pwsh") or shutil.which("powershell")` 以 **pwsh 7 優先**選引擎，與 R59 DEF-101-509 拍板並寫在 `test_install_windows_nightly.py:193-214` 的判準（「生產是以 `powershell -ExecutionPolicy Bypass -File` 執行＝5.1…`tools/` 樹受 `test_ps51_compat.py` 的 PS 5.1 相容政策約束，故以 5.1 優先解析」）**方向相反**。消費點 5 個（:153/:169/:230/:233/:249），其中 :169/:249 真的把它交給 subprocess 執行 PowerShell 跑 `Test-IsRealPython` 行為測試；被測檔 `tools/lib/WindowsAppsGuard.ps1` 確實在 `test_ps51_compat.py:203-209` 的 8 支 PS 5.1 政策樹內（`git ls-files -- "tools/*.ps1"` 逐一核對）。本機活體影響為零（`which pwsh` rc=1 ⇒ 靜默 fallback 到 5.1），但任何同時裝有兩者的環境會用 PS 7 去驗一支受 5.1 政策約束的檔案。DEF-101-509 的修復範圍逐字只寫 `test_install_windows_nightly.py` 一支；`grep -rn "_pwsh_exe" docs/06_quality/*.md` 零命中＝未登記。收工前重查該檔（Pkg-3 已對它有其他改動）確認 :58 仍為 pwsh 優先。

### 狀態與驗證

partial@R60（判準側已修、呼叫點待 Pkg-3）：Pkg-6 已把「生產引擎 5.1 優先」寫成唯一具名述詞 `tools/tests/_ps_engine.production_engine()` 並以**合成雙引擎**情境鎖死方向（bug-injection 實證：優先序對調即 `兩引擎皆在時選了 pwsh 7——與 DEF-101-509 判準方向相反` 翻紅，而本機既有鎖同時仍全綠）。該檔本身依分包鐵律未動，已在 `tools/tests/test_ps_engine_ssot.py::_PENDING_MIGRATION_SITES` 具名登記（附完整 WHY 與「Pkg-3 遷移後請刪除本條目」），並送出 cross-package request：把 `_pwsh_exe()` 改為委派 `production_engine()`、`_windows_pwsh_available()`（:230）改為 `windows_with_engine()`。🔴 誠實揭露：該待遷移條目**刻意不加 stale 自檢**（永久豁免那組有），因為加了會在 Pkg-3 修好的那一刻讓本鎖反向翻紅、變成主控最終全套跑的地雷；代價是本輪對這一處**沒有機械攔阻力**，只有登記與請求。


---

## DEF-101-549

**發現情境**：R60 Scan-E（E-refuter-1 自找）落地包 Pkg-6 查證；帳本由主控獨佔書寫，Pkg-6 只提供查證結果

**嚴重度**：P3（兩筆 open watch item／PM 待決依據的事實記載錯誤；同型判例 DEF-101-336「帳本記載與現況不符」亦 P3）

**分流去向**：主控（帳本獨佔書寫）；依帳本「只增不刪」政策應以**補記訂正列**處理，不得改寫 DEF-101-392／401 原文

### 現象與證據

`docs/06_quality/AutoSDD_Defect_Log.md:86`（DEF-101-392，日期 2026-07-26／R48 Architect 架構複審）逐字寫「**Copy-on-Evolve 凍結基線政策已兩度（R44／R45）被迫打破鐵律回補**」；同檔 `:91`（DEF-101-401，2026-07-26／R50）寫「亦未發現 R49 之後出現第三次被迫打破鐵律回補的新事證…DEF-101-357/358（R44/R45）**兩次**破例根因同構」。但 `docs/06_quality/AutoSDD_Defect_Log_archive_22.md:36`（DEF-101-379，日期 **2026-07-25**／來源「R46 全新掃描」）狀態欄逐字為「**fixed@R46**（經使用者核准**第三次**打破 Copy-on-Evolve…）：對 `AISDLC_SDD_v0.01`~`v0.29` 全部 29 個版本的 `path_cost.py` 機械套用 import `_sanitize_component`」。時間序：R46 破例（07-25，帳本當時已寫「第三次」）→ R48 寫「兩度」（07-26）→ R49 四方複審未訂正 → R50 再覆核仍以 2 為基數，三者不可能同時為真。次數本體以 git 獨立覆核：`git log --format='%h %ad %s' --date=short -- 'AISDLC_SDD/AISDLC_SDD_v0.01/tools/fsm_runtime/**' 'AISDLC_SDD/AISDLC_SDD_v0.15/tools/fsm_runtime/**'` 回 `aa5c075 2026-07-26 R46…`／`6b24eb7 2026-07-25 R45…`／`68c159d 2026-07-25 R44…`／`bbf507b 2026-06-18`（v0.15 建版 commit，非破例）／`0cda8aa 2026-06-12`（初始匯入）⇒ **破例 commit 恰 3 支**；另 `git log --since=2026-07-25 -- 'AISDLC_SDD/AISDLC_SDD_v0.0[1-9]/**' 'v0.1*' 'v0.2[0-9]'` 只回 `aa5c075` ⇒ R46 之後（R47~R59）零第四次。影響：DEF-101-401 的升級理由建立在「復發頻率」上，實際是 R44/R45/R46 三輪連續各一次而非兩輪兩次——**低估了它自己要主張的趨勢**，而這兩筆正是待送 PM／ADR 的決策依據。

### 狀態與驗證

查證完成@R60（Pkg-6）：**正確次數＝3（R44／R45／R46）**，三次的標的／嚴重度／核准形式／實際判準／修法／代價已逐一整理進本輪產出 `docs/04_planning/ADR/ADR-XPLAT-001-copy-on-evolve-frozen-baseline-backport.md` §3.1~3.3，次數矛盾與影響另立於該檔 §3.4。載具鑑別力自檢：若帳本一致寫 3 次，該 grep 只會命中「三度／三次」、不會出現「兩度」與「第三次打破」並存 ⇒ 非「一律命中」。Pkg-6 **未觸碰任何帳本檔案**（`git status` 對 `docs/06_quality/` 零本包改動）。


---

## DEF-101-550

**發現情境**：R60 Scan-E（E-A-04）落地包 Pkg-6 撰寫 ADR 時實查發現（非掃描者、非反駁者原始清單內）

**嚴重度**：P3（流程／文件治理缺口，與 DEF-101-370 同型同級；不影響 R46 修復本身之正確性——該修復已由 `tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py` 等機械鎖守）

**分流去向**：AISDLC_SDD 領域（`AISDLC_SDD_v0.30` 為 LATEST、可修改版本，非 Pkg-6 檔案範圍）；Pkg-6 已在 ADR-XPLAT-001 §7 列為 routed 落差

### 現象與證據

`DEF-101-370`（fixed@R44，P2）拍板：`AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md` 為「未來查詢『Copy-on-Evolve 是否曾被打破、在什麼條件下』」的**權威索引入口**（帳本為逐版驗證細節的權威出處，兩者互補不重複），並據此在 R44 新增「凍結基線例外」結構化章節。實查該檔：`grep -n "凍結基線例外"` 只有 `:7 …（R44，2026-07-25）` 與 `:22 …（R45，2026-07-25）` **兩節**；`grep -c "R46" AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md` → **0**（rc=1）⇒ **R46 那次破例（`aa5c075`、DEF-101-379、`path_cost.py` × 29 版）從未進入該索引**。後果：照 DEF-101-370 指定路徑查「例外發生過幾次」只會查到 2 次——這正是 DEF-101-392／401 把次數寫成「兩度」的一條可能來源，且該索引自述的完整性宣稱因此不成立。另註：`:24` R45 章節逐字寫「這是繼 R44 之後…**第二次**」，該敘述在當時為真、不需訂正。

### 狀態與驗證

open（routed@R60，Pkg-6 查證並記錄，未修）：建議在 `AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md` 補「凍結基線例外：v0.01～v0.29 `path_cost.py` 淨化回補（R46，2026-07-26）」章節，欄位比照既有兩節八欄（範圍／日期+signoff／打破理由／修法／TLC 證據／驗證／殘留落差／回退指引），內容可直接取自 `docs/04_planning/ADR/ADR-XPLAT-001-…md` §3.3（含「核准依據事後經 SA 複驗證偽（實際為 FileNotFoundError／零消費者）但修復未回退、僅訂正帳本敘事」這項必須誠實記載的細節）；同時建議檔頭 `:5` 的索引導言補一句「本節數量即例外總次數」以免同款漏記再發生。


---

## DEF-101-551

**發現情境**：R60 Scan-F 反駁者自找 #1（Pkg-7 落地）

**嚴重度**：P2（兩平台閘門報告面不等價 + 被機械鎖宣稱等價；覆蓋可見度損失，不會讓紅變綠）

**分流去向**：本輪修復（Pkg-7）

### 現象與證據

**`AutoClaude/tools/local_ci_gate.ps1:20` 寫死過期的 `$PytestArgs` 預設值 `'tests/ -q --tb=short'`，把 R59（ARCH-R59-01）加進核心 `local_ci_gate.py:63 DEFAULT_PYTEST_ARGS` 的 `-rs` 在整個 Windows 側靜默吃掉**（含 `run_local_nightly.ps1:452` Stage L、根 CLAUDE.md 列為 Windows 唯一本機 CI 指令的那條路）。機制：`.ps1:39 if ($PytestArgs) { $CliArgs += ($PytestArgs -split '\s+') }` 無條件附加，而核心 `parse_args()` 的語意是「首個非旗標參數起**整批取代**預設」，於是「無參數呼叫」在 Windows 上等於顯式覆寫掉核心預設。PATH stub 攔 argv 實測（原生 PS 5.1.26100.8875）：`-File …local_ci_gate.ps1` → `STUB-ARGV: …local_ci_gate.py tests/ -q --tb=short`（無 -rs）；對照 Git Bash `local_ci_gate.sh` → `STUB-ARGV: …local_ci_gate.py`（零參數，落回核心預設）。核心語意實測：`parse_args([])` → `['tests/','-q','-rs','--tb=short']`；`parse_args(['tests/','-q','--tb=short'])` → `['tests/','-q','--tb=short']`。後果＝208 支 skip 的理由在 Windows 側全被吞回一個數字，且兩支**被 `tools/check_wrapper_thinness.py` hash 釘選宣告為等價**的薄殼實際給出不同的 pytest 報告面。**hash 釘選對此形態天生盲目**（它只認「殼內容有沒有變」，不認「殼內嵌常數與核心常數是否還同義」），R59 動核心時它全綠；`grep -rn PytestArgs` 全 repo 亦確認**從無任何測試碰過那個預設值**。附帶第二件事：`local_ci_gate.py:10-13` 自陳的邊角「`.ps1 -PytestArgs ''` 落回核心預設」，以該檔 `.EXAMPLE` 示範的 `-File` 呼叫傳 `''`，PS 5.1 直接 `Missing an argument for parameter 'PytestArgs'` 中止 ⇒ 該邊角在文件自己示範的載具上不可達（本機無 pwsh 7）

### 狀態與驗證

fixed@R60：① `.ps1:20` 預設值 → `''`（無參數時零附加，核心 `DEFAULT_PYTEST_ARGS` 為唯一真相源），檔頭與參數映射處補 WHY。② **根治鎖（非 hash）**新增 `AutoClaude/tests/tools/test_local_ci_gate_shell_arg_parity.py` 7 支：斷言兩殼「送進核心的 pytest 參數清單逐字相同且等於 `DEFAULT_PYTEST_ARGS`」、`.ps1` 的 `$CliArgs` 只准附加 gate 旗標與 `$PytestArgs` 切割結果、`.ps1` 不得內嵌核心 pytest 參數字面值、`.sh` 只准 `"$@"` 透傳。③ 同步重釘 thinness hash（dc470fdc… → 226d6090…），未用 `--no-verify`。④ `local_ci_gate.py` docstring 訂正該邊角揭露並記入 `-File` 不可達。**bug-injection**：改回舊預設 → `6 failed`，訊息逐字 `兩支薄殼給出不同的 pytest 參數面…：.ps1=['tests/','-q','--tb=short'] / .sh=['tests/','-q','-rs','--tb=short']`；還原後 `7 passed`、檔案位元組級一致（BOM=True CRLF=50 size=2733）。修復後 stub 實測：no-args→零參數、`-Pg`→`--pg`、`-Act`→`--act`、`-PytestArgs '-k test_foo -v'`→原樣透傳（覆寫介面不變）。閘門：thinness rc=0（10 支釘選）、parity rc=0（交叉鎖 5 對/10 支鍵集合一致）


---

## DEF-101-552

**發現情境**：R60 Scan-F F-02（CONFIRMED；Pkg-7 落地）

**嚴重度**：P2（覆蓋損失 + 診斷訊息不精確；不會讓任何測試由紅變綠）

**分流去向**：本輪修復（Pkg-7；只動 v0.30 LATEST，凍結版不回補）

### 現象與證據

**v0.30 `tools/fsm_runtime/tests/test_phase_h.py:215-219 requires_docker_success` 以 `not _DOCKER or sys.platform.startswith("win")` 硬排除全部 Windows，排除面遠大於證據面**。DEF-101-062 的不穩定證據全部來自 GitHub-hosted windows-latest（LCOW 堆疊），但判準寫成 OS 級，把本機 Windows 11 + Docker Desktop WSL2（`docker info` → `linux / 29.5.3`，完全不同的堆疊）一起掃掉。實測：`pytest test_phase_h.py -k docker -rs` → `test_docker_backend_real_pass` SKIPPED、`test_docker_backend_real_runtime_fail` PASSED（只掛 `@requires_docker` ⇒ `docker_available()` 為 True）、`test_docker_backend_e2e_through_fsm` SKIPPED ⇒ 觸發者只能是 `or sys.platform` 那一支；繞過 mark 直呼函式本體連跑 4 次全 PASSED、零 flaky。疊上 CI 帳務停擺（DEF-101-081），「容器實跑成功 → OQS pass」這條路在 Windows 上現況**零活體覆蓋**。第二個問題：reason 是一個 `or` 選言，讀者無法分辨哪一個限語觸發（本機恆為第二個）——DEF-101-515 需人工考古才解釋得出 v0.30 −4，根因即此。帳本既有 DEF-101-062／515 兩筆皆把此排除當「正確的平台差異／零退化」處理，方向相反，故非 ALREADY-LOGGED

### 狀態與驗證

fixed@R60：① 排除條件由「平台硬排除」改為「能力偵測 ＋ 窄環境例外」——新增 `_windows_ci_runner()`（Windows 且 `GITHUB_ACTIONS` 或 `CI` 有值），核心判準仍是 `docker_available()`（該函式本身即以 DockerBackend 的完整安全 profile 實跑一次容器，比平台名稱強得多），DEF-101-062 的 GH windows runner 例外原樣保留。② reason 拆成**互斥兩段**，讀者一眼看出是「docker 不可用」還是「Windows CI runner 環境例外」。③ 新增回歸鎖 `test_docker_success_exclusion_is_ci_scoped_not_platform_blanket`。**數字（clean-equivalent，`SDD_FF9_STALE_MIN_AGGREGATE=100` 中和另一包的 governance 污染）**：v0.30 LATEST 軌 `1725 passed, 8 skipped`（＝R59 記載 1725）→ 本檔 `34 passed+2 skipped` → `37 passed`；**我的孤立貢獻 +3 passed / −2 skipped ⇒ 1725→1728**（+2 skip→pass、+1 新鎖；全軌最終觀測 `1736 passed, 6 skipped` 中另 +8 collected 屬並行包，`test_file_lock.py` 3→6 已實證）。**四環境逐一實測**：本機→3 passed；`GITHUB_ACTIONS=true`→1 passed/2 skipped（CI 例外 reason）；`CI=true`→同；PATH 移除 docker→3 skipped（docker 不可用 reason）。**bug-injection**：`_windows_ci_runner()` 改 `return True` → `1 failed`，訊息 `非 CI 環境不得被排除——排除條件退化成平台硬排除`；還原後 `37 passed`、位元組核對 CRLF=0 bareLF=478


---

## DEF-101-553

**發現情境**：R60 Scan-F F-01（PARTIAL→P3；Pkg-7 落地）

**嚴重度**：P3（取證可信度；不影響 FAIL 判定）

**分流去向**：本輪修復（Pkg-7）

### 現象與證據

**`tools/macos_smoke_local.sh` 在非 Darwin 平台把兩項無法驗證的子測試以「SKIP-計-PASS」計入 PASS，收尾三個訊號（`===== 彙總：PASS=13 FAIL=0 =====`／`全部通過 ✅`／rc=0）與真 macOS 滿版全驗逐字相同、計數相同**（兩平台皆恰 13——`test_smoke_ci_sync.py::_SH_EXCLUSIVE_PASS_GROUPS` 已把那兩組互斥分支逐字登記），事後稽核無從分辨「在 Windows 上跑過」與「在 macOS 上全綠」。R59 由 DEF-101-511/512 立的原則（讓結論自己說出降級事實）該輪未回頭套用到這支腳本。反駁者訂正兩點並收斂為 P3：(a) log 本體其實已自陳降級三次（兩行「（SKIP）…（非 macOS）」＋兩個 PASS 標籤字面就寫著 SKIP），標題把範圍限縮在「收尾訊息＋計數」是精確的、why 欄擴大成整份輸出過頭；(b) 影響面純屬取證可信度、不會讓任何 FAIL 變 PASS，與 DEF-101-512 同類同量。`grep -rn 'SKIP-計-PASS' docs/` 與 `grep -rn 'macos_smoke_local' 帳本主檔` 皆零命中，確認未登記

### 狀態與驗證

fixed@R60：① 新增獨立計數器 `SKIPPED_AS_PASS`，兩處 SKIP-計-PASS 站點各遞增一次；**刻意不併入 `pass()`／不新增 helper**——`test_smoke_ci_sync.py` 的 MIN_PASS 語意鎖以「pass 加雙引號訊息」字面呼叫點計數，包一層會多算一次（PASS 計數與 `MIN_PASS=13` 語意完全不動，只動輸出面）。② 兩處彙總行改印 `SKIP=$SKIPPED_AS_PASS`。③ 收尾拆成互斥兩條：`SKIP>0` → `⚠️ 部分通過（本平台 <uname> 非 Darwin）…【本結果不等於 macOS 全驗完成】` 並自行 `exit 0`（**「全部通過」四字不再出現**）；`SKIP==0` → `✅ 全部通過（SKIP=0…）`。④ 檔頭 `Exit:` 明示 rc=0 有兩種、字樣互斥。⑤ 新增鎖 `tools/tests/test_macos_smoke_skip_honesty.py` 8 支（`unittest.TestCase` 形態——C-01 教訓；官方 discover 實查 `MY FILE DISCOVERED = 8`）：計數器初始化／SKIP 站點**納管**（新增第三處未納管即紅）／遞增數==站點數／遞增緊鄰其站點 ≤3 行／彙總行必印 SKIP／`SKIP>0` 分支自行 exit 且其中不得出現「全部通過」／「全部通過」只能在該守門之後／**真跑載具**（切出收尾段以 bash 實跑 SKIP=0 與 SKIP=2 並斷言可分辨）。**修復後實測**（`uname -a` = MINGW64_NT-10.0-26200）：REAL_RC=0，`===== 彙總：PASS=13 FAIL=0 SKIP=2 =====` ＋ `⚠️ 部分通過…【本結果不等於 macOS 全驗完成】`。**bug-injection**（收尾還原成缺陷原貌）→ `FAILED (failures=3)`，真跑載具給出最硬的證據：`SKIP=0 與 SKIP=2 的收尾輸出逐字相同`（兩份 stdout 在 assert 訊息中逐字並列，皆為 `PASS=13 FAIL=0 / 全部通過 ✅…`）；還原後 sha256 與注入前**位元組級一致**（12991495…，size=27380）、`Ran 8 tests … OK`。⑥ 落地過程中 `test_smoke_ci_sync.py` 的 MIN_PASS 語意鎖**當場翻紅（`14 != 13`）**——我在註解裡寫出了 `pass "…"` 字面樣式被它算成第 14 步，已改寫並就地留痕；**既有機械鎖有效運作，如實記載**。`macos_smoke_local.sh` 經查**不在** `check_wrapper_thinness._PINNED_SHA256`（10 支釘選逐一核對），無 pin 需更新；`check_script_parity.py` rc=0


---

## DEF-101-554

**發現情境**：R60 Pkg-7 量測過程附帶查明（污染歸因，非新缺陷 — 記入以免主控／下輪誤判為真紅）

**嚴重度**：P4（環境／取證污染，非程式缺陷；但會讓最終閘門出現假紅）

**分流去向**：主控處置（我依鐵律未執行任何 git 寫入類指令）

### 現象與證據

**v0.30 `test_arch_fitness.py::test_ff9_repo_no_structural_fail` 在本輪工作樹為紅（`1 failed, 1724 passed`），根因是 R60 Scan-F 反駁者驗 F-02 時繞過 pytest 直呼測試函式本體所造成的 repo 檔案污染，不是程式缺陷**。該探針沒吃到 `tools/fsm_runtime/tests/conftest.py::_isolate_rule_telemetry_default`（session 級 autouse，把 telemetry flag 設 "0"），於是 `rule_loader.record_state_fires()` 寫穿 15 支 tracked `AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/R-*.yaml`，`scaffold_roi.fire_count` 由 0 被寫成 4~8。我實測 aggregate = **84** ≥ FF-9 門檻 20（`FF9_STALE_MIN_AGGREGATE`，`arch_fitness.py:1202`）⇒ gate 開啟、24 條 0-fire 規則觸發 `warn ff9-stale-scaffold` 而非測試斷言要求的 `info ff9-ok`。決定性驗證：`SDD_FF9_STALE_MIN_AGGREGATE=100`（gate 關閉）→ `info ff9-ok 全部 39 條 active 規則 scaffold_roi 基座完整`，同時全軌變 `1725 passed, 8 skipped` 恰等於 R59 記載的 1725。污染非我造成：15 檔 mtime 全程維持 `2026-07-28 21:34:38`（`stat -c '%y'`），早於我 21:53 開工；我的 pytest 走 conftest 隔離、零寫入。附帶：`git diff` 對每一支都印 `CRLF will be replaced by LF the next time Git touches it`（＝Scan-F 反駁者自找 #2 的 `rule_loader._write_rule` 未帶 `newline=""` 缺陷的同一批證據）

### 狀態與驗證

open（待主控還原）：跑最終閘門前需 `git checkout -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/`；未還原時 v0.30 ci-gate 會出現 `test_ff9_repo_no_structural_fail` 假紅，且 pytest 通過數少 1（1724 而非 1725）。歸因已由我以「調高 `SDD_FF9_STALE_MIN_AGGREGATE` 即轉綠」＋「HEAD 版 fire_count 全 0、工作樹 aggregate=84」雙向證成，主控不必重新調查


---

---

## DEF-101-555

**（round 2 新增；round 1 QA-R60-04，blocking）**

**現象**：七維掃描 34 項發現中有 4 項零落地——無修復、無帳本條目、本檔 `not_fixed` 亦零提及。
逐項落地／逐項具名不修理由如下，全部指令都在 Windows 11 Pro 26200 ＋ Git Bash 5.2.37 下實跑。

### 【1】Scan-G G-02（CONFIRMED／P2）— DEF-101-333／336／338 指向 R41 的孤兒 backlog

判準逐字（`CrossPlatform_Scan_Dimensions.md:149`，R59 自己寫的硬規則②）：
「狀態仍為 `open`／`deferred` 的列若提及一個 `R\d+` 承接者，該輪號必須 ≥ 當前輪，
或該列／有一筆更新的 DEF 條目載明「改派」」。R41 < R60 且反駁者把主檔＋全部 archive 的每一處
出現逐一回讀後確認**零改派、零結案** ⇒ 三筆皆為孤兒。

round 2 逐筆實查「標的是否其實已被做掉」（若已做掉就該結案而非改派）：

- **333（PowerShell AST 解析）** — 兩支 guard 測試今日確實已 `import ast`
  （`tools/tests/test_windowsapps_guard_cross_consistency.py:33`、`:1330`），乍看像做了；
  但逐行讀 `:1323-1340` 後確認那是 `_bare_python_command_literals()` 在解析 **Python** 原始碼
  （抓「首 token 為裸 python/python3 的字串常數」），與本列要求的 **PowerShell AST**
  （追蹤變數賦值實際使用、here-string 開闔狀態機）完全無關 ⇒ **標的未動**。
  這一點值得記下來：`import ast` 的存在會讓下一輪誤判 333 已封閉。
- **336（凍結版「禁止 commit」機械鎖）** —
  `grep -rln "禁止 commit|禁止提交|forbid.*commit" --include=*.py --include=*.sh --include=*.ps1
  --include=*.yml .` → **REAL_RC=1（零命中）**（排除凍結樹後）⇒ 該鎖不存在。
- **338（v0.01 假 SHA drift 檔）** —
  `git ls-files 'AISDLC_SDD/AISDLC_SDD_v0.01/build/reports/drift/COMMIT-*'` →
  `COMMIT-769eea4e3f66.yaml`／`COMMIT-sha-3rd.yaml`／`COMMIT-sha-high.yaml`／`COMMIT-sha-low.yaml`／
  `COMMIT-testsha-001.yaml`（後四支是假 SHA 形態）⇒ 根因未查、四支仍被追蹤。

**處置**：三列各就地附「🔴 R60 改派」段，改派為**未指派 backlog**，並各給可直接執行的解鎖條件。
體例比照 R59 `DEF-101-521` 對 `DEF-101-500` 的改派——**不改寫歷史原文**（帳本是逐字保全的歷史檔），
而是以新條目＋就地附記載明改派。

### 【2】Scan-A A-03（CONFIRMED／P3）— DEF-101-377 的「R47 複驗已自癒」證偽

round 2 親跑（`core.autocrlf=true`）：

```
$ git ls-files --eol -- '*.sh' | grep -c 'w/crlf'      → 145
$ git ls-files --eol -- '*.sh' | grep -c 'w/lf'        → 23
$ git ls-files -- '*.sh' | wc -l                       → 168      （145+23=168）
$ git ls-files --eol | grep 'w/crlf' | grep -c 'attr/text eol=lf' → 18392
$ git ls-files --eol -- '*.sh' | grep 'w/crlf' | awk '{print $NF}' \
    | grep -vc "^AISDLC_SDD/AISDLC_SDD_v0\."          → 0
```

145 與 `DEF-101-377` **初登記的「145 支 .sh」一字不差**，即 R47 那句「已不可重現／於此機器自癒」
在今日工作樹上不成立。全庫數字為 **18,392**（掃描時點量到 18,412）：差 20 支落在本輪 41 支被修復包
重寫的 tracked 檔內（現 39 支為 `w/lf`），**我未逐檔回溯 HEAD 側行尾，故不宣稱精確歸因**——
這不影響主張，因為 `.sh` 那一組完全沒被本輪碰過。

**根因訂正（本節的重點）**：掃描者猜「R47 在 worktree／臨時 clone 裡量測 → 假陰性」，
並據此把修法寫成「複驗載具必須在主工作樹執行、禁用 worktree」。更有支撐的解釋是**平台切換**：
同一份帳本 `DEF-101-351` 的狀態欄明寫 R51 是在「本機 macOS/Darwin 環境」重跑，
而 macOS 的 checkout 天生 LF，量到 168/168 `w/lf` 是**零鑑別力的必然結果**。
另有一條結構性反證：對 attr 宣告 `text eol=lf` 的路徑，`git checkout`／`reset --hard`
只會寫出 LF、**不可能製造 CRLF**，所以 R58 那次 `reset --hard 75aab89` 無法解釋今日的 18,392 筆
⇒ CRLF 必然**早於** R47。故應落的紀律是「**複驗紀錄必須戳上平台與機器指紋**」，
只寫「禁用 worktree」擋不住同一個假陰性再發生一次。

**免責前提仍成立，故不調升嚴重度**：blob 全為 LF（任何全新 clone 皆正確）；
本機 Git Bash 5.2.37 吃掉 CR（CRLF 腳本實跑 rc=0、`bash -n` rc=0）。

### 【3】Scan-C 反駁者自找 #1 後半 — 行尾守門的 `w/` 半條在唯一載具上結構恆綠

另立 `DEF-101-557` 記為**已知缺口**（採 QA-R60-04【3】required_action 的二選一之後者），
並提跨包請求。完整實測見 `## DEF-101-557`。

### 【4】Scan-G G-03 殘留 — DEF-101-422／435／470 的交棒是死信

```
$ grep -rn "一般 CI 維護" --include=*.md .
  → 只有主檔 L101／L102（即 DEF-101-434 與 DEF-101-435 自己）  ⇒ 該容器不存在
$ grep -rn 'DEF-101-422' --include=*.md . | grep -v AutoSDD_Defect_Log
  → 只一行：AutoClaude/docs/04_planning/ADR/ADR-SD07-001-loc-policy.md:279
    （引它當 LOC 硬閘佐證，不是工作項）                        ⇒ C 軌零登記
```

- 422／470 指向的 `AutoClaude_Improving_0NN`／`SD_Improving_NN`／「C 軌工作流帳本」
  是**存在但從未被更新**的容器；435 指向的「一般 CI 維護缺陷帳本」是**不存在**的容器。
- 三列的技術前提今日**都仍成立**（`_evaluator_derivation.py` 的 `head = tokens[: pytest_idx + 1]`
  未改；`aisdlc-sdd-artifact-cleanup.yml:17` 仍寫「drift-daily.yml 無 upload」而
  `aisdlc-sdd-drift-daily.yml:88-94` 確有 `upload-artifact@v6`／`name: drift-daily-report`）。
- **處置**：三列各附改派段（改派為未指派 backlog／C 軌）、訂正失實容器名，
  並在 `CrossPlatform_Scan_Dimensions.md` 新增**硬規則③（跨軌交棒回執）**：
  交棒只在目標軌帳本出現對應工作項時才算成立，否則一律視為未指派。
  這條是針對「G-03 這種形狀會反覆發生」的制度性補強，不只是修這三列。

**同時記下 G-03 的一半被反駁者證偽**：`DEF-101-434` 其實早已由 R57 結案
（結案記錄 `DEF-101-490` 隨 `archive_27` 歸檔），本輪 Pkg-1 已把主檔那列回填為 `fixed@R57`。
掃描者的 grep 把整個 `AutoSDD_Defect_Log`（含 archive）`grep -v` 掉，正好濾掉那一行。

## DEF-101-556

**（round 2 新增；round 1 SA-R60-04，blocking）**

**現象**：`DEF-101-554` 狀態停在 `open（待主控還原）`，內文指示後續輪跑
`git checkout -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/`——而該還原早已由主控完成。
帳本把**已完成的事記成未完成**，實害三層：`_classify` 判為 `open` 並計入 crossref 的活躍狀態；
`archive_defect_log.py` 判準②會永遠擋它搬遷；R61 讀到會以為有一件待辦，並照著對一棵**乾淨的**
工作樹跑一條破壞性 `git checkout --`。

**round 2 獨立重跑的還原憑證（不採信任何既有宣稱，含主控自己的收尾清單）**：

```
$ git status --porcelain -- AISDLC_SDD/AISDLC_SDD_v0.30/governance > g.txt; echo REAL_RC=$?
  REAL_RC=0 ；wc -c < g.txt → 0            ⇒ 該路徑工作樹零變更
$ grep -rn "fire_count" AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/ \
    | grep -v "fire_count: 0"              → 零命中（39 支 tracked 規則檔皆 fire_count: 0）
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && PYTHONDONTWRITEBYTECODE=1 \
    python -m pytest tools/fsm_runtime/tests/test_arch_fitness.py -q -p no:cacheprovider
  REAL_RC=0 「93 passed in 1.05s」
$ ... -m pytest "tools/.../test_arch_fitness.py::test_ff9_repo_no_structural_fail" -v
  「1 passed in 0.15s」
$ git status --porcelain -- AISDLC_SDD/AISDLC_SDD_v0.30/governance | wc -l   → 0（跑完仍乾淨）
```

最後一條刻意跑在測試之後：`DEF-101-554` 的成因正是「驗證動作本身寫穿 tracked YAML」，
所以只證明「現在乾淨」不夠，還要證明「用正規 pytest 路徑跑過之後仍然乾淨」。

**過期數字訂正**：該列原記「pytest 通過數少 1（1724 而非 1725）」——現行 v0.30 全套為
**1736 passed／6 skipped**（round 1 SD 獨立實測，與 `ci-gate.sh` 尾行一致），兩個數字都已過期。

**同時複查本輪其餘活躍列（SA-R60-04 required_action 的後半）**：

| 列 | 複查結論 |
|----|----------|
| `DEF-101-550` | **真 open**，標的（`EVOLUTION_LOG.md` 補 R46 例外章節）確實未做 → 只補「承接輪次：未指派」 |
| `DEF-101-541` | 自陳半邊已修 → 收斂為 `fixed@R60`；升版決策半邊拆出 `DEF-101-559`（`routed`） |
| `DEF-101-548` | 呼叫端已由主控遷移完成 → 收斂為單一 `fixed@R60`；反增生鎖缺口另屬 QA-R60-07 |
| `DEF-101-557` | round 2 新立，`open`（已知缺口，具名不修） |

## DEF-101-557

**（round 2 新增；round 1 QA-R60-04【3】＋QA-R60-10；源於 Scan-C 反駁者自找 #1 後半）**

**現象**：根層行尾守門的兩條「工作樹（`w/`）」判準，唯一載具是 ubuntu-only workflow：

```
.github/workflows/root-infra-ci.yml:99   runs-on: ubuntu-latest
.github/workflows/root-infra-ci.yml:254  .sh  判準：$1 ~ /(i|w)\/(crlf|mixed)/
.github/workflows/root-infra-ci.yml:278  .ps1 判準：$1 ~ /w\/(lf|mixed)/
```

ubuntu 上 `actions/checkout` 每次都是全新 checkout，對 `eol=lf` 與 `eol=crlf` 都是**確定性 smudge**
⇒ 兩條 `w/` 半條在該平台**結構上不可能紅**，鑑別力為零；而會紅的 Windows 側零載具：

```
$ grep -rn "ls-files --eol" --include=*.yml --include=*.sh --include=*.ps1 --include=*.py . \
    | grep -v "AISDLC_SDD_v0\."
  → root-infra-ci.yml:20(註解)／:242(註解)／:254／:278
  → tools/check_gha_action_versions.py:91（一句註解）
  ⇒ 全庫唯一 ls-files --eol 載具就是那支 ubuntu-only workflow
$ grep -rn "eol|EOL" tools/git-hooks/pre-commit tools/git-hooks/pre-push  → 零命中
```

本機實況正是它抓不到的兩種：

- 145 支 `.sh`（attr `eol=lf`）工作樹為 CRLF（見 `## DEF-101-555`【2】）。
- 3 支 `.ps1`（attr `eol=crlf`）工作樹為 LF：`AISDLC_SDD/scripts/install-hooks.ps1`、
  `AutoClaude/tools/fix_nightly_catchup.ps1`、`AutoClaude/tools/install_git_hooks.ps1`
  （對照本輪已回正的兩支：`AutoClaude/tools/local_ci_gate.ps1`、`tools/install_windows_nightly.ps1`
  皆 `i/lf w/crlf attr/text eol=crlf`）。

**具名不修的理由（不是靜默跳過）**：新增測試檔屬 `tools/tests` 擁有包，帳本包依 R60 分包鐵律
不得新增測試檔；已提跨包請求。**承接輪次：未指派。**

**給承接者的落地建議（可直接執行）**：在 `tools/tests/` 新增一支 unittest，以 `git ls-files --eol`
對 attr `eol=lf` 的路徑斷言工作樹非 crlf、對 attr `eol=crlf` 的路徑斷言工作樹非 lf。
🔴 **先以現況實測決定是 fail 還是 warn**：現況即有 145+3 支違反，直接硬擋會讓本機 pre-push
**永紅**（同 R59 ARCH-R59-NB4 對「永紅規則」的警告——規則不能寫成讓閘門在既有存量下必紅）。
務實作法是釘選現況白名單 ＋ 只對新增檔硬擋，白名單隨清理逐條移除。

**本機三支 `.ps1` 漂移本輪不處理**：修法是 `git add --renormalize` 或重新 checkout，
屬本機環境衛生、與 `DEF-101-377` 同族（該列已定調不由 agent 執行破壞性還原）；
index 側（`i/lf`）正確，故不影響任何使用者 clone。

## DEF-101-558

**（round 2 新增；round 1 SA-R60-05／SA-R60-06／QA-R60-09／ARCH-R60-01 之帳本側）**

### ① 證據檔標頭涵蓋範圍失實 → 補 527／528 兩節 ＋ 標頭改為「以 `##` 錨實查」

原標頭宣稱逐字保全 `DEF-101-527`~`554` 全部；實查 `grep -o '^## DEF-101-[0-9]*' | wc -l` = **26**
（529~554），無 527／528。修法不只補兩節，還把標頭的**區間式宣稱**改成「以 `## DEF-ID` 錨實查」
——區間宣稱會在下一次新增條目時自動 stale，那正是本筆的形狀。

### ② archive_30 標頭的餘裕預測被同輪自己證偽

`archive_30:5` 原句：「把主檔壓到 `256073 → 174447` bytes（釋出 81626），**使本輪即使毛增 45KB
仍不觸及 240KB warn 帶，單輪內不需要第二次歸檔**」。本檔 `:6`（Pkg 分層說明）已逐字證偽：
第一版 28 列共約 **99.5KB**（毛增約為預測的兩倍），主檔當場由 176,296 衝到 **275,979 bytes**、
直接撞破 262,144 fail 硬閘。而同一標頭末段自己寫著「本標頭**不對餘裕做定性宣稱**（R59
SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被自己推翻）」⇒ `:5` 做的正是它宣稱自己不做的事。

**處置**：`:5` 原句就地標 ⚠️ 並指向訂正處（比照 R59 SA-R59-P2-1 慣例，**不刪原文**），
🔴 揭露段標題由「三項缺陷」改為「四項」並補第 4 項全文。
**結論僥倖仍成立純粹因為緊急改成兩層外移，不是因為 `:5` 的推算正確**——這句必須寫進去，
否則下一輪會把「沒撞閘」讀成「預測是對的」。

### ③ archive_05／archive_21 只是 stat-dirty，不是守恆算式的變因（QA-R60-09）

round 2 獨立複驗：

```
$ git hash-object docs/06_quality/AutoSDD_Defect_Log_archive_05.md
  5d1214f2b37f543be154f5c289e387b4fc0c0a67
$ git rev-parse HEAD:docs/06_quality/AutoSDD_Defect_Log_archive_05.md
  5d1214f2b37f543be154f5c289e387b4fc0c0a67          ⇒ 兩側同 blob
$ git hash-object docs/06_quality/AutoSDD_Defect_Log_archive_21.md
  b28df207d3301c40db9229f53713a3a59219834a
$ git rev-parse HEAD:docs/06_quality/AutoSDD_Defect_Log_archive_21.md
  b28df207d3301c40db9229f53713a3a59219834a          ⇒ 兩側同 blob
$ git diff --name-only | grep -c "archive_05\|archive_21"   → 0
$ git status --short -- .../archive_05.md .../archive_21.md
  " M docs/06_quality/AutoSDD_Defect_Log_archive_05.md"
  " M docs/06_quality/AutoSDD_Defect_Log_archive_21.md"
```

`git status` 顯示 M 但 `git diff` 不含它們、blob 與 HEAD 完全相同 ⇒ **純 stat-dirty、零淨變更**，
不可能是任何位元組守恆算式的變因。已在本檔 Pkg-5 段那條 🔴 上報就地加 ⚠️ 訂正註。
真變因是 CRLF 污染（`DEF-101-528` 的歸因正確）。
**順帶記一條收輪檢查**：`git diff --name-only` 與 `git status --short` 的 M 集合若不一致，
須先查明是 stat-dirty 還是真變更，再據此推導任何位元組結論。

### ④ 立帳指針四處失實／逸出稽核（ARCH-R60-01 ④）

| 位置 | 原文問題 | round 2 訂正後 |
|------|----------|----------------|
| `archive_26:9` | 宣稱 `DEF-101-493` 在主檔，實居 `archive_28` | `立帳見 DEF-101-493（現居 archive_28）` |
| `archive_27:9` | 同上 | 同上（保留「與本輪 R58 交接段」語意） |
| `archive_25:11` | 立帳指針只寫到「主檔 R57 條目」、無 DEF-ID | `立帳見 DEF-101-491（現居 archive_28）` |
| 主檔 `:180` | 無 DEF-ID 的散句 | `立帳見 DEF-101-491（現居 archive_28）` |
| 主檔 `:183` | 無 DEF-ID 的散句 | `立帳見 DEF-101-520（現居 archive_30）` |

`DEF-101-491`（archive_25 的立帳）與 `DEF-101-520` ④（archive_28／29 的體積治理紀實）
的居所皆經實查確認。

🔴 **計數訂正（本包自我糾錯，寫進來以免留下憑記憶推算的數字）**：本節初稿寫「落地後全家族『立帳見』字樣 10 處，10/10 皆可解析」——那個 10 是**只數了主檔**的推算，並非實測。
實際重數（掃 `docs/06_quality/AutoSDD_Defect_Log*.md` 全 31 檔）：

```
修復前：總命中 11 ｜帶可解析 DEF-ID 8 ｜無 ID 3
    AutoSDD_Defect_Log.md            '立帳見本表 R57 條目。'
    AutoSDD_Defect_Log.md            '立帳見本表 R59 條目。'
    AutoSDD_Defect_Log_archive_25.md '立帳見主檔 R57 條目。'
  （另有 2 處帶 DEF-ID 但居所宣稱失實：archive_26:9／archive_27:9）
修復後：總命中 19 ｜帶可解析 DEF-ID 19 ｜無 ID 0
  （11 → 19 的增量＝本輪新增的 8 處指針：7 處改派／訂正段的「立帳見本表 DEF-101-555」
    ＋ archive_30 揭露段第 4 項的「立帳見 DEF-101-558」）
```

**權威輸出**（不採信本節的手數，以工具為準）：
`python tools/archive_defect_log.py --check` → REAL_RC=0，尾行逐字「✅ 帳本保全稽核通過（31 檔／672 個 ID／**19 個「立帳見」指針**＋0 處引述）：行尾全 LF、同檔內 ID 無重複列、跨檔狀態分類無矛盾、全部立帳指針皆帶可解析 DEF-ID 且居所宣稱與實況一致」。

🔴 **寫這些訂正註時踩到、值得留痕的坑**：訂正註若把舊的失實形態**逐字重寫**（例如引用
「立帳見主檔 R57 條目」當例子），指針稽核會把那段引用當成一個新的失實指針而報紅——
我第一版就這樣自己觸發了一次。改法是**敘述式引用**（寫「原文的立帳指針只寫到『主檔 R57 條目』、
不帶 DEF-ID」）。這與「註解裡別寫出被鎖的字面」是同一條紀律。

## DEF-101-559

**（round 2 新增；自 `DEF-101-541` 拆出，round 1 SA-R60-08 要求「一列一狀態」）**

**為何要拆**：`DEF-101-541` 原狀態首詞是 `partially-fixed@R60（自陳不再懸空）／routed（升版決策）`
——`partially-fixed` 非《格式定義》合法值，且它的 `fixed` 前綴是 `-`（非 ASCII 英數邊界），
所以 `_classify` 仍命中 `fixed`，把 `routed` 那半邊的活躍語意**靜默吞掉**。
閘門印「零含糊」是真的，但語意與分類不一致。一列同時承載「已修」與「待決」兩種狀態，
在任何以「狀態欄首詞」為準的機械判定下都必然有一半被吃掉 ⇒ 拆成兩列。

**本列承載的待決事項**：`tools/check_gha_action_versions.py`〈掃描面邊界〉段已載明
「LATEST（`AISDLC_SDD_v0.30`）的 `hub-push.yml` sample 是否要升 action 版本，
**刻意不由 CI 工具鏈側代決**」。這是真實的待決點，因為升 LATEST 會讓
「各版此檔為同一 git blob」這個目前**可機械核對的不變量首次分裂**。

**承接輪次：未指派**（依 `CrossPlatform_Scan_Dimensions.md:149` R59 硬規則②明標，
不假造一個輪號——假造輪號正是 G-02／G-03 那六筆孤兒的成因）。

## DEF-101-560

**（round 2 新增；由本包自己新加的落地前斷言抓出，非四方複審、非掃描發現）**

**怎麼被抓到的**：本包第一版寫帳本時，把 `grep -v "fire_count: 0"` 這種含 pipe 的指令直接寫進
儲存格，落地後 `_classify` 讀到的「最後一欄」變成散文碎片。發現後我改成「佔位符 ＋ 落地前
斷言每列必須切成 7 欄」，**那道斷言立刻反手抓出一筆存量真缺陷**：

```
AssertionError: 欄數異常（應為 7）：[(107, '| DEF-101-524 | 2026-07-28 | R59 四方一審裁決與', 9)]
```

**存量缺陷本體**：兩道閘門的欄位切分都只把「未被反斜線前導的 pipe」當分隔符
（`check_defect_log_crossref.py:115`、`archive_defect_log.py:84 _CELL_SPLIT_RE`）。
`DEF-101-524` 的狀態欄內有兩處 code span 含字面 pipe（`grep -oE 'N passed'` 後接管線到 `tail -1`，
以及 Windows 非法字元類 `[\/:*?"<>` 後接 pipe 再接 `]`），於是該列被切成 9 欄，
`cells[-1]` 取到的是以「`]`」開頭的散文碎片，`_classify` 在碎片裡命中 `open`。

淨效果：該列真實狀態欄是 `no_action_needed（流程紀錄）`（應分類 `closed-by-decision`），
卻被**兩道閘門一致誤判為活躍 `open`**。`archive_defect_log.py --plan` 的實測輸出逐字：
`DEF-101-524  ①狀態分類非已結（cls=open）; ②狀態欄含活躍字樣 'open'`
⇒ 一筆已結案的流程紀實被永久當成活躍待辦，並永遠擋在歸檔判準外。

**修法與紅綠對照（主檔）**：兩處字面 pipe 各加一個反斜線前導。

```
修復前：DEF-101-524  ncells=9  cls='open'                first44='] `」等最可能的第 5 份寫法漏報…'
修復後：DEF-101-524  ncells=7  cls='closed-by-decision'  head='no_action_needed（流程紀錄）。…'
```

**零語意變更證明**：把產物的轉義 pipe 全部還原成裸 pipe 後與原文**逐字元相同**
（markdown 對轉義 pipe 的渲染就是字面 pipe，故顯示結果亦不變）。

**全家族掃描：15 列欄數異常**（主檔 1 ＋ archive 14）

```
AutoSDD_Defect_Log.md:107            DEF-101-524  cells=9  cls(last)='open' cls(真狀態欄)='closed-by-decision'
AutoSDD_Defect_Log_archive_03.md:60  DEF-77-002   cells=8
AutoSDD_Defect_Log_archive_03.md:67  DEF-87-002   cells=8
AutoSDD_Defect_Log_archive_03.md:68  DEF-87-003   cells=8
AutoSDD_Defect_Log_archive_04.md:33  DEF-101-024  cells=8
AutoSDD_Defect_Log_archive_04.md:86  DEF-101-087  cells=8
AutoSDD_Defect_Log_archive_04.md:87  DEF-101-088  cells=8
AutoSDD_Defect_Log_archive_09.md:13  DEF-101-244  cells=8
AutoSDD_Defect_Log_archive_09.md:14  DEF-101-246  cells=8
AutoSDD_Defect_Log_archive_09.md:15  DEF-101-247  cells=8
AutoSDD_Defect_Log_archive_09.md:17  DEF-101-264  cells=8
AutoSDD_Defect_Log_archive_09.md:18  DEF-101-267  cells=8
AutoSDD_Defect_Log_archive_16.md:48  DEF-101-245  cells=8
AutoSDD_Defect_Log_archive_23.md:14  DEF-101-407  cells=8
AutoSDD_Defect_Log_archive_28.md:26  DEF-101-498  cells=8
```

**archive 側 14 列刻意不動，理由具名（不是漏做）**：

1. **今日零活體後果**：那 14 個 ID 只存在於 archive，`check()` 的主檔↔archive 分類比對在
   `if _LEDGER.name not in files or len(files) == 1: continue` 就跳掉了；crossref 的 live SSOT
   也只讀主檔。
2. **啟發式不足**：我實測「pipe 落在 inline code span 內（左側 backtick 數為奇數）即為字面」
   這條規則，只能正確處理 15 列中的 **9 列**；其餘 6 列（`archive_04:86`／`:87`、
   `archive_09:13`／`:14`／`:15`、`archive_16:48`）的多餘 pipe 落在 code span 外，
   **需逐列人工判定**（dry-run 在第 6 列就 fail-loud 停住，沒有硬幹）。
3. **盲目轉義的失敗模式比現況嚴重得多**：若誤把真正的儲存格分隔符轉義，整列七個欄位會**靜默
   左移一格全部錯位**，而那**沒有任何現存閘門會抓到**。用同一種病去治這個病是不划算的。

**給承接者的落地順序（可直接執行）**：
先在 `tools/` 側落一道「每列切分後必須為 7 欄」的硬斷言，並**把現存 14 列釘成白名單**
（否則閘門當場永紅，同 R59 ARCH-R59-NB4 的警告）；再逐列人工轉義，
每一列都以「還原後逐字元相同」＋「欄數 7」雙重證明收斂，收斂一列就從白名單移除一列。
**承接輪次：未指派。**

## 各修復包誠實揭露的未修項與跨包請求（逐字保全）

> 🔴 **round 2 補記（round 1 QA-R60-04，blocking）**：下方各包的 `not_fixed` 是**修復包視角**的
> 未修項，**不涵蓋「七維掃描發現但整輪都沒人接手」的那一類**——round 1 QA 逐項比對 34 項掃描
> 發現 ↔ 28 筆帳本條目 ↔ diff 後，抓到 **4 項零落地**（Scan-G G-02／Scan-A A-03／Scan-C 反駁者
> 自找 #1 後半／Scan-G G-03 殘留），三處全部查無記載＝靜默丟棄。
> 這四項已於 round 2 逐項落地或逐項具名不修，完整證據見本檔 `## DEF-101-555`；
> 帳本立帳於 `DEF-101-555`（含 `DEF-101-557` 記載其中唯一需要新程式載具的那一項）。
> **制度性補強**：`CrossPlatform_Scan_Dimensions.md` 新增硬規則③（跨軌交棒回執），
> 讓「交棒到一個不存在或從不更新的容器」不再算成立。



### Pkg-2 Scan-A 技術缺陷（A-01＋Scan-A 反駁者自找 #1、A-02、A-04、Scan-F 反駁者自找 #2）

**未修項（not_fixed）**：

四項全數修復完成（FIXED），沒有靜默跳過的項目。以下是刻意不做／做不到的部分，逐條給理由與證據：

1. **凍結版 v0.01~v0.29 的同款缺陷未回補**（file_lock 窄捕 29 版 x 3 處、rule_loader 缺 newline="" 29 版、hub_sync 裸 rmtree 29 版；計數為我自己 grep 實查）。理由：Copy-on-Evolve，主控指示明訂「本項只改 v0.30（LATEST）」，歷輪三次破例（R44/R45/R46）皆需使用者核准。已列入 cross_package_requests。

2. **A-04 我採取了與反駁者建議相反的處置，特此揭露以供覆核**。反駁者的裁決文字是「值得照它 proposed_fix 末段那句『至少把刻意未套用的理由寫進函式註解』處理，**不值得為此動 LATEST 生產碼**」，並判定實質應對齊 P4/wontfix 慣例。我改成落地程式修復 + 雙層回歸鎖，依據有三：(a) 主控任務書明確指派「再決定是複用還是就地硬化」並要求「所有問題必須徹底全部修復」；(b) 反駁者說「唯讀來源結構性缺席」這一格我補完了——copytree 以 copy2/copystat 連權限位一起複製，任何 file:// hub 的 rules/ 帶唯讀檔就會把唯讀位帶進 cache_dir，加上 Windows 通用的「第三方持 handle（WinError 32）」，觸發子不是空集合；(c) 修法只有一個模組級 helper，且我用真 pull() 生產路徑做了正反雙向實測。**但我完全採認反駁者的可達性訂正**：出廠 allowed_endpoints: [] + session_start.py:197 守門 ⇒ 出廠設定下 _mirror_local 不可達，此筆本質是 latent 的硬化一致性落差，不是進行中的實害。若覆核方認為不該動 LATEST，回退成本很低（一個 helper + 一行呼叫 + 兩支測試）。

3. **A-01 的「誠實 skip」路線我判定不必走，改成讓測試真的有鑑別力**。主控任務書 ② 寫「若判定是 Windows 上空環境區塊 + CreateProcess 的平台限制，就用誠實的 skip 並印出理由」。我實測後認為它**不是**平台限制：換成「PATH 指向真實存在但空無一物的 temp dir」後，Windows 上子行程正常啟動（Win32 區塊維持 87 筆）、rc=127、stderr `dirname: command not found`，即生產端 wiring 在 Windows 上**首次被真正驗到**。skip 會永久放棄這份覆蓋，故不採。

4. **兩處我訂正了上游給的技術前提，若我錯了會影響修法選型**，明白攤開：(a) 主控說「Python 3.11 的 Path.write_text 不吃 newline 參數」——本機 Python 3.11.9 實測簽名含 newline 且行為正確（CR=0 vs 預設 CR=2），repo 也已有同形先例 tools/tests/test_script_scan_surface_ssot.py:169；(b) 反駁者說 A-01 的判別因子是「先前是否發生過 os.putenv」——我實測真根因是「Windows 上 os.environ[NAME]='' 等於刪除變數」（ctypes GetEnvironmentVariableW 直讀證成），putenv 只解釋 WinError 87 那一半。兩處我都附了可重跑的最小指令，請覆核方獨立複驗，不要採信我的結論。

5. **未跑全套測試**（依主控鐵律 #3，避開 __pycache__ 競態假紅）。我只跑了本包動到的檔案 + 其直接下游消費者（共 tools/tests 8 支、v0.30 側 205 支）。全套 pytest（AutoClaude 3740/208、根層 661→現 742）由主控收尾統一跑。

6. **未在 macOS/Linux 實機驗證**（本機只有 Windows 11 Pro 26200）。A-02 的原生 Windows handle 測試以 skipUnless(win32) 誠實跳過非 Windows；A-04 ①與 Scan-F ①② 這幾支位元組/行為鎖在 POSIX 上恆綠、對回歸零鑑別力，我為每一項都另補了一道任何平台都有鑑別力的原始碼/呼叫點契約鎖，並把這個限制寫進測試 docstring 而不是假裝它們跨平台有效。

7. **tools/run_root_unittests.py 本體未修改**。A-01 的病灶在被它執行的測試、不在 runner；runner 對「某支測試以錯誤理由通過」沒有通用可加的偵測手段（真要做就是每支測試自己表態，已在本包落地）。唯一需要動的是 MIN_TESTS 重釘，依該行明文規定必須由主控在所有並行包停工後填實測值，故我不動——已列入 cross_package_requests 第 1 條。

**跨包請求**：

- 【必辦｜tools/run_root_unittests.py:38 的 MIN_TESTS 需由主控重釘】我新增 3 支測試進 tools/tests（該檔 5→8 支）。收工時實測 `discover_suite('tools/tests').countTestCases()` = **742**，而 MIN_TESTS=661、WARN 門檻 727.1、STALE(紅) 門檻 826.25 ⇒ **已越過 WARN、閘門會印「⚠️ 測試數量下限已過期…請把 MIN_TESTS 重釘為 N」，但不會紅**。該行檔內註解明訂「本值由主控在所有並行修復包與四方複審 agent 全部停工後，於最終工作樹實跑取其印出的『發現 N 個測試』直接填入，不做任何加減推算」，故我刻意不動它（742 也還會被其他並行包改變）。請主控收尾時實跑並填實測值。
- 【必辦｜15 支 governance/rules/*.yaml 待還原，非本包造成】動工前 git status 就已有 AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/ 下 15 支 R-*.yaml 為 M（R-9.1／9.2／9.3／9.6／9.7／9.8／9.9／9.15／9.17／9.18／9.19／9.20／9.21／9.38／R-SELF-STRIDE），是 Scan-F 反駁者跑探針時繞過 conftest 隔離 fixture 寫穿的（fire_count 0→4 + 整檔 CRLF），他已誠實揭露並請主控還原。我用 PowerShell 核對其 LastWriteTime 全為 2026/7/28 21:34:38（＝他記錄的時間戳），我的工作始於 22:00 之後，且跑完全部測試後該 15 筆數量與內容未變（我的測試全部寫 tmp_path）。依鐵律我不執行 git 寫入類指令，請主控處理：`git checkout -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/`。
- 【告知｜Copy-on-Evolve 邊界，需使用者核准才能回補】本包三支生產碼的缺陷在凍結版同樣存在，我一律只動 LATEST v0.30：file_lock.py 窄捕（v0.01~v0.29 共 29 版、每版 3 處）、rule_loader.py 缺 newline=""（29 版全數命中；其中 21 個凍結版另有 record_state_fires 這個高頻觸發子）、hub_sync.py 裸 rmtree(dst_sub)（29 版）。若要回補須走使用者核准例外（比照 R44/R45/R46 三次破例）。
- 【告知｜生產碼 AISDLC_SDD/scripts/bash_probe.py 不在本包檔案清單，且我判定不需改】A-01 的 file_evidence 點名該檔:64-81 的 `except Exception: continue` 把 OSError 與「輸出不符」混為一談。我判定這**不是生產缺陷**：一個 spawn 不起來的 bash 本來就不可用，回 None 語意正確；缺陷純在測試無法分辨兩種 None，已在測試側修掉。若主控或複審方仍要在生產端分流（例如區分「不可用」與「探測失敗」以便告警），那是另一個包的檔案，請另行指派。
- 【告知｜本包 3 支檔案的工作樹 CRLF 是動工前既有狀態】file_lock.py（122 CRLF / 0 bare LF）、rule_loader.py（359/0）、tests/test_file_lock.py（181/0）在我編輯前就已是 100% CRLF（DEF-101-377：core.autocrlf=true，全 repo 18,412 支 tracked 檔 w/crlf），編輯工具沿用該檔既有風格、未產生混行。鑑別證據：我同一輪也編輯了 hub_sync.py 與 test_hub_sync.py，兩者維持純 LF。三支的 index 屬性皆 `i/lf attr/text eol=lf`，git add 會正規化回 LF，故不影響提交內容；若主控要順手正規化工作樹，那是 repo 層衛生動作、不屬本包。

**回歸驗證證據（regression_evidence）**：

全部指令都以 `cmd > file 2>&1; echo REAL_RC=$?` 取真 rc（不接管線），並設 PYTHONDONTWRITEBYTECODE=1 + `-p no:cacheprovider`（避開 DEF-101-268 的 __pycache__ 競態）。未跑任何全套。

【① 根層 tools/tests（我唯一動到的那支檔，兩種載具皆驗）】
$ ./.venv/Scripts/python.exe -m unittest discover -s tools/tests -p test_bash_probe_spec_contract.py → REAL_RC=0「Ran 8 tests in 0.107s / OK」
$ ./.venv/Scripts/python.exe -m pytest tools/tests/test_bash_probe_spec_contract.py -q -p no:cacheprovider → REAL_RC=0「8 passed in 0.20s」
（動工前同兩指令：unittest REAL_RC=0「Ran 5 tests / OK」＝誤綠；pytest REAL_RC=1「1 failed, 4 passed」）

【② v0.30 FSM runtime（我動到的 3 支生產碼 + 其下游消費者）】
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && pytest tools/fsm_runtime/tests/{test_file_lock,test_hub_sync,test_rule_loader_eol,test_context_ledger_pre_hook,test_context_ledger_post_hook,test_phase_j,test_governance_coverage,test_rule_fire_telemetry_wiring,test_rule_catch_telemetry_wiring}.py -q -p no:cacheprovider -m "not chaos"
→ REAL_RC=0「205 passed in 4.68s」
分項（各自獨立跑過）：test_file_lock 6 passed（3 既有 + 3 新）／test_hub_sync 51 passed（49 + 2）／test_rule_loader_eol 3 passed（新檔）／context_ledger 前後 hook + phase_k 48 passed／phase_j + governance_coverage 100 passed

【③ 官方閘門收錄與 ratchet 狀態（未跑全套，只 discover 計數）】
$ python -c "run_root_unittests.discover_suite('tools/tests').countTestCases()" → 742（本包新增 3 支，8 個 test_bash_probe_spec_contract id 逐字在內）
MIN_TESTS=661、WARN 門檻 727.1、STALE(紅) 門檻 826.25 ⇒ 742 已越過 WARN（會印「該重釘了」）但**不紅**。見 cross_package_requests 第 1 條。

【④ 其他閘門不退化】
$ ./.venv/Scripts/python.exe AutoClaude/tools/check_loc_budget.py → REAL_RC=0「total=20361 baseline=17032 cap=20438 violations=0」（本包零觸碰 AutoClaude 生產碼，20361 為其他並行包造成，非我）
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && python -m tools.arch_fitness.arch_fitness --strict → rc=1「加權缺陷分數 4｜🔴 fail=0 🟡 warn=4」；ci-gate.sh:161 只在 AF_CODE ≥ 2 才算失敗，故通過。4 筆 warn 為 FF-5（CLAUDE.md §9 頁數）、FF-9（24 條規則 0-fire）、FF-16 x2（元迴圈接地／GC 提案），全與本包三支檔案無關
$ AISDLC_SDD/scripts/framework_status_snapshot.py 的 count_metrics 只數 agent/scenarios/workflow/templates/skills/governance_rules，**不數測試檔** ⇒ 新增 test_rule_loader_eol.py 不會讓 FRAMEWORK_STATUS.md 快照過期
ruff 掃描面實查：ruff 設定只存在於 AutoClaude/pyproject.toml，`grep -rn ruff tools/git-hooks/*` 零命中 ⇒ 根層 tools/ 與 AISDLC_SDD 不在 ruff 閘門內，本包無 E501 風險（被我改動的 rule_loader 那行原本就已 102 字元）

【⑤ 行尾位元組稽核（本包 7 支檔逐檔）】
全部「uniform」無混行：test_bash_probe_spec_contract.py crlf=0/bare=243；hub_sync.py 0/804；test_hub_sync.py 0/1091；test_rule_loader_eol.py 0/87（新檔純 LF）；file_lock.py 122/0、rule_loader.py 359/0、test_file_lock.py 181/0。
後三支的 CRLF 是**動工前就存在**的本機狀態（DEF-101-377；core.autocrlf=true，全 repo 18,412 支 tracked 檔 w/crlf），非我造成——鑑別證據：我同一輪也編輯了 hub_sync.py 與 test_hub_sync.py，兩者維持純 LF，可見編輯工具是「沿用該檔既有風格」而不是統一轉 CRLF；三支的 index 屬性皆 `i/lf attr/text eol=lf`，`git add` 會正規化回 LF。

【⑥ bug-injection 還原核對】四項共做 6 次注入，每次都以 Edit 改那一行、驗完再以 Edit 改回，並在還原後重跑該檔確認回綠（各項證據見 items）。全程未使用 `git checkout --`／`git stash`／`git reset`／`--no-verify`。


### Pkg-3 Scan-B guard/淨化

**未修項（not_fixed）**：

1) **刻意未加擋「保留名 + 前導空白」（B-02 任務書原指示的修法方向）** — 這是本包最重要的一項不服從，理由是我自己的實測而非推論：(a) git for Windows `core.protectNTFS=true`（決定 Windows checkout 會不會整棵樹開不出來的權威模型）對 ' CON.txt'／'  COM1.log'／' con.txt'／' CON'／' NUL .log'／' CON .txt'／' CONIN$.log' **全部 ACCEPT**，只含前導形態的 repo `git clone` rc=0、工作樹有檔、`git status --porcelain` 空、payload 讀回正確；對照組（'CON .txt'／'CONIN$.log'）clone rc=128、工作樹全空。(b) Win32 只吞尾隨空白/句點、不吞前導：' CON.txt'／' CON'／'CON.txt'／' CON .txt' 四者可同時共存於同一目錄（os.listdir 全部列出、各 10 bytes 可讀回）。⇒ 在兩個 validator 加擋＝純新增偽陽性（擋下 git 與 Windows 都接受的檔名），零實害可擋；反駁者裁決同向（「(A) 只會新增偽陽性面」）。我改採 (B) 案：把「三放一擋」定案為刻意不對稱並**雙向**設鎖 + 樣本電池兩側同步 + 四處寫入自足實測理由。若主控判定仍要走 (A)，那是政策選擇而非缺陷修復，需明確指示。

2) **刻意未改 `AISDLC_SDD/scripts/component_sanitizer.py` 首行的 `.strip()`** — 它是四處中唯一會剝前導空白、因而對前導形態更嚴格的一處。改成 `.rstrip()` 能讓四處「輸出對稱」，但會改變**所有**含前後空白的合法輸入的既有輸出（例 ' myproject' → ' myproject'），且該行早於本判準存在、負責的是「呼叫端誤傳含前後空白的片段」（Rule 3 surgical）。改為在該處寫入兩層理由並由兩側斷言雙向鎖住（本處必須加前綴 / 另三處必須放行）。

3) **未重釘 `MIN_TESTS`** — 見 cross_package_requests #1，該行檔內明文規定必須由主控在所有並行包停工後填實測值，我不可代填（R57 曾兩度用算式推錯）。

4) **新相鄰性鎖有已揭露的殘留 fail-open** — 若有人在註解裡寫出管線分隔的 `CON|PRN|AUX|NUL` 字樣，該鎖會被同一手法滿足（我自己第一版就這樣自我滿足、注入不紅）。徹底根治需剝註解／AST 解析四種語言，而 R46 已證那是無底洞（繞過從整行註釋 → no-op 前綴 → heredoc 逐層復發）。已在 docstring 明寫「只主張攔下無意識地插中間這個真實發生過的動作，不主張攔下刻意偽裝」。

5) **B-01 掃描的邊界（三段式已寫入原始碼，此處摘要未涵蓋項）** — 註解與 docstring 內的提及（AST 結構性排除，刻意）；測試檔；凍結版 v0.01~v0.29；尚未 `git add` 的新檔；字面值被拆開或間接組出（`\"pyth\"+\"on\"`、f-string、`os.environ[\"PY\"]`）＝與 `_matches_stub_anchor` 的 K／O 同源的靜態掃描天花板；首 token 非裸名者（`py -3.11`／`python3.11`／`python:3.11-slim`）。並明寫「本清單非窮舉」。

6) **`tools/lib/platform_utils.py` 這筆偽陽性未消除** — 它的 `\"python\"` 是 `venv_dir / \"bin\" / \"python\"` 的路徑片段而非指令首 token，粗粒度判準看不出差別，已以角色註記登記為「非呼叫」並在該筆明寫「此筆即該取捨的成本」。要消除需在 AST 上判斷常數是否為 `/` 運算元，那本身又是新的繞過面（`Path(\"python\")`），成本大於收益。

7) **未在真 bash 3.2 上驗證（本機無此版）** — 已誠實揭露：本機 `bash --version` = GNU bash 5.2.37 x86_64-pc-msys、`sh` 同一支。已用兩個 shell 載具（bash 5.2 功能實跑 + `sh` POSIX 模式功能實跑與 `sh -n`）驗證，且 case pattern 內以單引號界定 `$` 是 POSIX sh 規範內的字面值寫法（刻意不用裸 `CONIN$|…`，那會依賴「`$` 後接非展開字元視為字面」的邊角行為）。macOS 真機驗證仍屬殘留項。

8) **未跑任何全套測試**（依指示避開 `__pycache__` 寫入競態 DEF-101-268）——AutoClaude 全套 3740/208、根層 661 tests、lint-imports、check_defect_log_crossref 皆由主控最後統一跑。我只跑動到的檔案 + 相鄰鎖，且一律 `-p no:cacheprovider` + `PYTHONDONTWRITEBYTECODE=1`。

9) **未編輯缺陷帳本**（鐵律 #1）——4 筆 ledger_entries 交由主控寫入。

**跨包請求**：

- 【必須由主控收尾執行，我刻意不動】重釘 tools/run_root_unittests.py 的 `MIN_TESTS`（現值 661）。本包對 tools/tests 淨增 17 支 unittest 測試（parity +3、ntfs +2、guard cross-consistency +12），故實況會 >661。該行檔內明文規定「本值由主控在**所有並行修復包與四方複審 agent 全部停工後**，於最終工作樹實跑 `python3 tools/run_root_unittests.py` 取其印出的『發現 N 個測試』**直接填入，不做任何加減推算**」（R57 曾兩度用算式推得 552/558，兩次都當場與實況不符）。現況不會讓閘門紅：MIN_TESTS 是下限，RATCHET_STALE_RATIO=1.25 ⇒ 826 才 FAIL；但 RATCHET_WARN_RATIO=1.10 ⇒ 728 起會印 WARN。
- 【他包造成、非我造成，請對應包處理】`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 目前 2 failed（macos-compat-ci.yml／windows-compat-ci.yml）：`根層消費檔未列入 <workflow> paths（只改該檔時其回歸鎖不會跑，DEF-101-042 同構）：['AutoClaude/tools/check_loc_budget.py', 'tools/_script_scan_surface.py', 'tools/archive_defect_log.py']`。三支皆非我的檔（`git status --porcelain` 顯示 `M AutoClaude/tools/check_loc_budget.py`、`?? tools/_script_scan_surface.py`、`?? tools/archive_defect_log.py`，另有 `?? tools/tests/test_archive_defect_log.py`、`?? tools/tests/test_script_scan_surface_ssot.py`）。建立這些檔的包需把它們加進兩支 workflow 的 `paths:`。該目錄其餘 247 passed／1 skipped／31 subtests。
- 【選配、低優先，非我的檔案】AutoClaude 生產碼兩處裸名兜底（`AutoClaude/autoclaude/evolution/_evaluator_derivation.py:46` 的 `_QUOTED_PY = '\"%s\"' % (sys.executable or "python3")`、`AutoClaude/autoclaude/execution/mutation_applier/_simple_mutations.py:56` 的 `python_bin = sys.executable or "python3"`）。我已在新的 `_ZERO_GUARD_BARE_PY_SITES` 以自足理由登記豁免（sys.executable 僅在嵌入式/凍結直譯器下為空；AutoClaude 入口是 `python -m autoclaude`／console script，該情境 sys.executable 恆為 venv 絕對路徑；且 `_evaluator_derivation` 那行是模組載入期求值，真為空則整個套件早已無法運作；`_simple_mutations` 該函式 docstring 自陳「W6 已拔除、目前無非測試呼叫點，暫不可觸發」）。若 AutoClaude 領域的包認為該兜底該改成 fail-loud（raise 而非落到裸名），改完後請同步刪掉那兩筆註冊表條目——等值斷言會在條目腐化時翻紅提醒。
- 【資訊揭露，非請求】`ruff check autoclaude/` 目前 540 findings（E501／I001／UP045 等），`ruff check .`（AutoClaude cwd）944 findings。已證為**既存技術債非本輪造成**：`git show HEAD:AutoClaude/autoclaude/core/event_bus.py` 拿 HEAD 版本單獨掃，同樣回報 `6:74 E501 Line too long (103 > 100)`／`11:1 I001`／`45:32 UP045`。我動到的四支生產碼單獨掃皆 `All checks passed!`，故 pre-commit 的變更檔 ruff 閘不會被我擋下。

**回歸驗證證據（regression_evidence）**：

【動工基線（我自己先跑，非引用）】`pytest -p no:cacheprovider` 六支指派檔 → REAL_RC=0、`133 passed, 86 subtests`。`check_loc_budget` total=20359 cap=20438 violations=0。

【收工最終（全部一律 `-p no:cacheprovider` + PYTHONDONTWRITEBYTECODE=1，未跑任何全套）】
1. pytest 十支相關檔（含四支我動過的測試 + 四道相鄰鎖 test_windowsapps_guard_bash_parity／test_component_sanitizer_shared_layer_lock／test_sanitize_component_frozen_sdd_versions_lock／test_bootstrap_core／test_bash32_compat／test_component_sanitizer_callsite_scan）→ REAL_RC=0、`179 passed, 2 warnings, 141 subtests passed in 18.38s`（基線 133/86 → 淨增 +17 測試、+55 subtests，無退化）。
2. **官方 unittest 載具**（＝run_root_unittests.py 走的同一條 discover 路，DEF-101-351／A-01 已證 pytest 與 unittest 可分歧，故雙載具都跑）：
   test_windows_forbidden_filename_parity → REAL_RC=0 `Ran 27 tests OK`
   test_ntfs_trailing_space_device_name → REAL_RC=0 `Ran 6 tests OK`（bash 類別**實際執行未被 skip**，3 支 ok）
   test_windowsapps_guard_cross_consistency → REAL_RC=0 `Ran 55 tests OK`
   test_windowsapps_guard_bash_parity → REAL_RC=0 `Ran 29 tests OK`
3. `python tools/check_ntfs_paths.py` → REAL_RC=0 `✅ NTFS 檔名檢查通過（27441 個 tracked 路徑，0 違規；最長 142 字元，warn>180/fail>200）`
4. `AutoClaude/tools/check_loc_budget.py` → REAL_RC=0 `total=20361 baseline=17032 cap=20438 violations=0 (absolute=0 tier=0 special=0 total=0)`（+2 行，餘裕 77；logger.py loc=108 tier=unclassified budget=750）
5. ruff（repo 根 cwd、我動到的六支檔）→ REAL_RC=0 `All checks passed!`；`ruff check autoclaude/utils/logger.py`（AutoClaude cwd）→ REAL_RC=0 `All checks passed!`
6. `bash -n tools/git-hooks/pre-commit` → REAL_RC=0；`sh -n`（POSIX 模式第二載具）→ REAL_RC=0；POSIX sh 功能載具實跑 `CONIN$.log`/`CONOUT$.txt` BLOCK、`CLOCK$.txt`/` CON.txt` pass、`CON.txt` BLOCK
7. AISDLC_SDD 子專案 `pytest scripts/tests` → `2 failed, 247 passed, 1 skipped, 31 subtests`；**兩筆失敗與本包無關**（見 cross_package_requests #2，斷言訊息點名的三支檔全非我的檔）
8. `AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_state_component_sanitizer_parity.py`（logger ↔ sanitize_component 跨子專案等強度鎖）→ REAL_RC=0 `8 passed`
9. 還原完整性：11 次 bug-injection 全部以 Edit 逐一改回，八支檔 `git hash-object` 對照 `diff REAL_RC=0`（逐位元組相同）；`git diff --numstat` 確認純增量、無整檔行尾 churn：check_ntfs_paths 43/3、pre-commit 15/2、logger 14/1、component_sanitizer 24/1、parity 測試 123/2、ntfs 測試 32/0、guard 測試 292/4、SDD 樣本測試 44/0。全程未用 `git checkout --`／`git stash`／`git reset`／`--no-verify`。


### Pkg-4 Scan-C CI/排程基建

**未修項（not_fixed）**：

【1】C-03 的「LATEST（v0.30）hub-push.yml 升版到 Node24 世代」— DEFERRED-WITH-REASON，屬「需人工決策」類，非靜默跳過。
理由與證據：(a) **決策擁有者不是本包**——`check_gha_action_versions.py` 的〈掃描面邊界〉裁定自 R57 起就明文寫「LATEST 是否應隨根層升版，需由框架版本治理側（AISDLC_SDD 凍結/LATEST 政策的擁有者）決定」，那是一條從未被推翻的既有分工宣告；本包是 CI/排程基建包，在一個並行多包的 Mac/Windows 相容性輪裡單方面覆寫另一側的決策權，正是 R58 失控的形狀。(b) **掃描者自己聲明本筆與作業系統平台無關、應標排除本輪範圍**，裁決者也據此把評級由 P3 降為 P4 並寫「評級應跟著它走」。(c) **「不做」有具體優點**：`git ls-files -s` 實測 30 份收斂為單一 blob（a24abefa…），這是目前可機械核對的不變量；只升 v0.30 會首次造成 29-vs-1 分裂，而現行沒有任何鎖理解這種分裂（我全庫 grep 確認無 hub-push 內容鎖）。(d) **它在本 repo 內完全不執行**：巢狀路徑 GitHub 永不觸發，且該檔頭自述是「給尚未存在的 Hub Registry repo 的 sample」。
我改為做到有承接者且不可靜默腐化：⚠️ 段寫入分流結論＋WebSearch 查證的期限（2026-09-16 Node20 自 runner 移除）＋路由；並把「實測全為 Node20 世代」升為接進 gate rc 的機械斷言（`_NESTED_DISCLOSED_GENERATION`），有人升了 LATEST 卻沒同步揭露與帳本時 gate 當場紅並指路（bug-injection 已證 REAL_RC=1）。

【2】未把「-WhatIf 需涵蓋兩支任務」的斷言複製進 `tools/windows_smoke_local.ps1` 的 [9/9]（該檔是本包獨佔，我有權改但刻意不改）。理由：該處現行判準是 `rc=0 -and 輸出 -match 'Register-ScheduledTask'`，兩支任務下仍為真、不會假綠；而加上兩個任務名字面會在 smoke 裡新造一個與 `test_install_windows_nightly.py` 重複的漂移站點（本 repo 反覆吃過「同一份硬編散佈多處」的苦）。同一不變量已由新增的 Windows-native runtime 鎖守住，而該鎖經 `run_root_unittests.py` 由 pre-push root-infra leg ＋ 三支 CI 自動帶到，覆蓋面不比 smoke 窄。

【3】`tools/tests/test_extras_quoting_zsh_safety.py` 的模組 docstring 含非法轉義序列（第 1~2 行 `\\``／`\\S`／`\\s`，ruff W605 類）——非本包檔案，未修。我的 AST 掃描鎖會讓 `ast.parse` 對它發 Deprecation/SyntaxWarning 而污染 runner 終端輸出，故在本包鎖內以 `warnings.catch_warnings()` 局部靜音並寫明 WHY（該類別屬 ruff 領域、且噪音會混淆複審者對「本次是否真有失敗」的判讀）。建議由該檔擁有者改成 raw string。

【4】三支 .ps1 的工作樹行尾違反 `.gitattributes *.ps1 eol=crlf`（本機 local-only 漂移，非本包造成、非本包檔案）：`AISDLC_SDD/scripts/install-hooks.ps1`、`AutoClaude/tools/fix_nightly_catchup.ps1`、`AutoClaude/tools/install_git_hooks.ps1` 皆為 `i/lf w/lf`。`root-infra-ci.yml` 的「.ps1 工作樹須為 CRLF」守門正是抓這個形態（判準 `w/(lf|mixed)`），但它跑在 ubuntu 全新 checkout 上、smudge 確定性套用故結構上看不到本機漂移（該 step 註解自己就誠實揭露了這點）。我只把自己寫壞的 `tools/install_windows_nightly.ps1` 轉回 CRLF（實測已回 `w/crlf`），未動別包的三支。屬 DEF-101-377 同族（本機環境衛生），建議以 `git add --renormalize` 或重新 checkout 處理。

【5】未跑全套測試（依交辦第 3 條）：AutoClaude pytest、根層 `run_root_unittests.py` 全跑、AISDLC_SDD `ci-gate.sh`、`check_loc_budget`、`lint-imports` 皆未由本包執行。本包**零 AutoClaude 生產碼改動**，故 LOC 預算（total=20359／cap=20438）與 import-linter 契約不受影響。

**跨包請求**：

- 【必做／收輪前】重釘 `tools/run_root_unittests.py` 的 `MIN_TESTS`（非本包檔案）。我在收工時實測 `discover_suite(tools/tests).countTestCases()` = **756**，而 MIN_TESTS=661、WARN 門檻 727.1 已被跨越（`ratchet_drift_message` 已會印「該重釘了」）、STALE 門檻 826.25 尚未觸及故不紅。本包淨貢獻 +16（parity 0→9、install_windows_nightly 13→17、smoke_ci_sync 8→11），其餘增量來自並行包新增的 test_archive_defect_log.py／test_doc_loc_baseline_freshness_r60.py／test_ps_engine_ssot.py／test_macos_smoke_skip_honesty.py／test_script_scan_surface_ssot.py／test_doc_env_prefix_platform_parity_r60.py。依該檔第 38 行明訂的判準：**必須由主控在所有並行包停工後於最終工作樹實跑取印出值填入，不做加減推算**（R57 兩度用算式推得的數字當場與實況不符）。
- 【必做／文件同步，兩份都不是本包檔案】DEF-101-517 的修復讓兩處記載過期：① `AutoClaude/tools/run_local_nightly.ps1:21`「反向去向帳目」寫『tools/windows_smoke_local.ps1 存在（PASS=12）卻**只能手動觸發**，本檔不呼叫它』；② `ONBOARDING.md:276` R59 訂正段寫『Windows 對等物 windows_smoke_local.ps1（現行 PASS=12）**只能手動觸發**，nightly 不呼叫它…沒有自動觸發器＝補償控制自己沒有心跳』。訂正要點（請精確、勿過度改寫）：**「run_local_nightly.ps1 對它零呼叫」這半句仍然為真且是刻意解耦**（不動 summary 契約），過期的只有「只能手動觸發／沒有心跳」——它現在由 `tools/install_windows_nightly.ps1` 註冊的獨立 schtasks 任務 `AutoClaude_WindowsSmoke`（每日 01:00）觸發，心跳讀 `Get-ScheduledTaskInfo`，`-Status` 對缺席回 exit 1。⚠️ 改 ONBOARDING 時注意該行刻意不寫 `PASS=N` 以外的字面（`test_smoke_ci_sync` 有 ONBOARDING↔腳本釘選跨檔鎖）。
- 【必做／閘門現正紅燈，非本包造成】`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 目前 2 failed（我在動工中途跑到的基線）：`根層消費檔未列入 windows-compat-ci.yml paths：['AutoClaude/tools/check_loc_budget.py', 'tools/_script_scan_surface.py', 'tools/archive_defect_log.py']`，macos-compat-ci.yml 同三筆。這三支是並行包新增/新消費的根層檔。修法是把三條 paths 加進兩支 workflow 的 push+pull_request 區塊——**那兩支 yml 是我獨佔的檔案，其他包改不了**，但我刻意沒加：這些消費檔還在其他包手上（若最後被回退，paths 會指向不存在的檔）。請在檔案集合定稿後指派我補、或由主控直接補。（我自己新增的消費 `tools/windows_smoke_local.ps1` 已確認在覆蓋範圍內：windows 側由 `**/*.ps1` 兜底、macos-compat-ci.yml:176/272 已顯式列舉，故本包未動 paths。）
- 【建議／可延後】把我新增的 `tools/tests/test_smoke_ci_sync.py::TestWindowsCiShellClaimConsistency` 併進 `tools/tests/test_gha_action_versions.py::TestWindowsCiHeaderSnapshotLock` 所在的檔案——那支才是 windows-compat-ci.yml shell 宣稱的既有主場（「表要對」），我這支管「別在表以外再自己講一遍」，兩者本應同居。本輪未併＝`test_gha_action_versions.py` 不在本包獨佔清單內，我不越界改別包檔案。兩支的互相引用已寫在各自 docstring，併檔時直接搬類別即可。
- 【建議／可延後】把 `tools/check_gha_action_versions.py` 加進 `tools/check_defect_log_crossref.py` 的 `_CROSSREF_TARGETS`（該檔非本包）。理由：我把它的〈掃描面邊界〉⚠️ 段從孤兒揭露改成帶路由的分流結論後，該段會引用缺陷帳本狀態；納入掃描面後「帳本改了狀態、工具檔頭沒同步」就會被機械抓到，正是 DEF-101-066 家族的既有防護模式。
- 【資訊／給帳本書寫者】本包的 5 筆 `ledger_entries` 中有 3 筆在程式碼與註解裡引用了尚未配號的 ID：我暫用 **DEF-101-529**（C-02，出現在 windows-compat-ci.yml 檔頭與 test_smoke_ci_sync.py docstring／assertion message）與 **DEF-101-530**（-Status exit code 缺陷，出現在 install_windows_nightly.ps1 的 `Test-TaskPresent` 註解與 test_install_windows_nightly.py 兩處 docstring／訊息）。若主控配號不同，請一併替換這兩個字串（各檔出現處：windows-compat-ci.yml 2 處、test_smoke_ci_sync.py 3 處、install_windows_nightly.ps1 1 處、test_install_windows_nightly.py 4 處）。C-01 我未在程式碼寫入 DEF 號以外的內容——更正：C-01 我在 `test_schedule_capability_parity.py` 檔頭與 3 處斷言訊息用了 **DEF-101-528**，同樣請一併替換（共 5 處）。

**回歸驗證證據（regression_evidence）**：

全程 `PYTHONDONTWRITEBYTECODE=1` ＋ 未跑全套（遵守 DEF-101-268 紀律），只跑受影響模組；rc 一律以 `cmd > file 2>&1; echo REAL_RC=$?` 取真值，不接 tail。

【針對性 unittest（受影響模組全集）】
$ python -m unittest tools.tests.test_install_windows_nightly tools.tests.test_schedule_capability_parity tools.tests.test_smoke_ci_sync tools.tests.test_windows_nightly_anchor_parity tools.tests.test_gha_action_versions tools.tests.test_check_gha_action_versions tools.tests.test_ps51_compat tools.tests.test_ps1_bom tools.tests.test_ci_scan_anchors tools.tests.test_root_infra_parity tools.tests.test_pre_push_dispatcher tools.tests.test_workflow_permission_concurrency_lock tools.tests.test_workflow_schedule_sync tools.tests.test_workflow_timeout_coverage tools.tests.test_check_script_parity tools.tests.test_run_root_unittests
→ REAL_RC=0，`Ran 198 tests` / `OK`
（收工前最後一次覆核：test_smoke_ci_sync + test_install_windows_nightly + test_schedule_capability_parity → REAL_RC=0，`Ran 37 tests / OK`）

【本包各檔測試數變化（per-file discover 實測）】
test_schedule_capability_parity.py：**0 → 9**（本輪核心：從零收集變成真的被四道閘門收到）
test_install_windows_nightly.py：13 → 17
test_smoke_ci_sync.py：8 → 11
⇒ 本包淨 **+16 支**被 unittest discover 收集的測試。

【機械守門工具（gate 級）】
$ python tools/check_gha_action_versions.py → REAL_RC=0（新增 `ℹ️ 巢狀排除區實查：30 份 workflow，action 世代 checkout@v4／setup-python@v5／upload-artifact@v4 與登記快照一致`；既有四行 22/1/20/13＝56 處不變）
$ python tools/check_script_parity.py → REAL_RC=0
$ python tools/check_defect_log_crossref.py → REAL_RC=0（帳本 81 筆有效狀態紀錄、4 份掃描目標皆無矛盾——確認我在 workflow 內新增的 DEF-ID 引用未造成跨檔狀態矛盾）

【lint / 編碼 / 行尾】
$ ruff check tools/check_gha_action_versions.py tools/tests/test_install_windows_nightly.py tools/tests/test_schedule_capability_parity.py tools/tests/test_smoke_ci_sync.py → REAL_RC=0 `All checks passed!`
PS 5.1 `[Parser]::ParseFile(install_windows_nightly.ps1)` → **errs=0**
`git ls-files --eol` 六個改動檔：.yml / .py 皆 `i/lf w/lf attr eol=lf`；install_windows_nightly.ps1 為 `i/lf w/crlf attr eol=crlf`（BOM=True、CRLF=234、bareLF=0）。⚠️ 我第一次寫入該 .ps1 時工作樹被寫成 LF（違反 .gitattributes `*.ps1 eol=crlf`、會被 root-infra-ci 的「.ps1 工作樹須為 CRLF」守門攔下），已自行偵測並轉回 CRLF，如實記載。
YAML：`yaml.safe_load(windows-compat-ci.yml)` OK，jobs=['windows-smoke','windows-nightly-full','windows-nightly-alert']，shell 分佈與改動前**完全相同**（pwsh 19/bash 1；powershell 2/pwsh 3；implicit 3）。

【排程系統未被變更】全部驗證只用 `-WhatIf` 與唯讀查詢；`Get-ScheduledTask -TaskName 'AutoClaude_Nightly','AutoClaude_WindowsSmoke'` 收工時仍只回 `AutoClaude_Nightly Ready`（未註冊任何新任務）。

【未跑（誠實揭露）】AutoClaude pytest 全套、根層 run_root_unittests 全跑、AISDLC_SDD ci-gate、check_loc_budget（本包零 AutoClaude 生產碼改動，LOC 預算不受影響）——依交辦由主控最後統一跑。


### Pkg-5 Scan-D 文件一致性

**未修項（not_fixed）**：

誠實揭露我沒有做的事，各附理由與證據，無靜默跳過：

【1】ONBOARDING §7 同一格的另一半「8 kept / 0 broken」（lint-imports）未納入機械比對——這是我新增的鎖範圍內、但刻意留白的缺口，不是遺漏。
  理由：驗它需要另跑 import-linter（不同工具、需 AutoClaude venv 內的 lint-imports entrypoint 存在）。根層 unittest 閘門在 CI 的 root-infra-ci / macos-compat-ci job 裡不保證裝了 AutoClaude 的 [lint] extras，硬接會把「環境沒裝選配」誤判成「文件 stale」，製造假紅（正是 DEF-101-509「鎖存在但在該平台不跑／誤紅」同型風險）。
  處置：已在 test_doc_loc_baseline_freshness_r60.py 的 docstring 邊界段逐字寫明「本鎖不驗證 8 kept / 0 broken 那半格……屬另一筆缺口，本輪未涵蓋、如實揭露」，讓下一輪讀者不會誤以為整格都有鎖。
  佐證該半格現況為真（不是帶病放行）：$ cd AutoClaude && ./.venv/Scripts/lint-imports.exe → 「Analyzed 202 files, 520 dependencies. / Contracts: 8 kept, 0 broken.」rc=0；本機 PS 5.1 上 `$env:PYTHONUTF8=1; lint-imports` → 同結果 EXITCODE=0。

【2】D-02 的機械鎖沒有掃全 repo *.md，只掃 10 份活文件名冊。
  理由（有實測支撐，不是偷懶）：我先寫了全庫 fence-aware 掃描器實跑一次，AISDLC_SDD 各版 scenarios/／docs_template/／guides/user/sample/ 的 CI/CD 與效能調校範本內有數百處 `VAR=$(...)`／`ANALYZE=true npm run build`／`COVERAGE=$(cat ...)` 形態（實測輸出逐檔逐行可列），那些是給使用者專案用的 bash/YAML 範本與時代快照，不是本 repo 開發者照著在自己機器上敲的指令；強掃會製造大量偽陽性，且與本 repo「歷史紀錄檔／時代快照不納管」的既定慣例（ONBOARDING §7 首段 🔴、check_pytest_baseline_sites.py docstring）直接衝突。名冊沿用既有納管語意並補 2 份指令密集活指引，是我判斷的正確範圍。已在 docstring 完整寫明此邊界與擴充方式。

【3】D-02 的對照要求是檔案級而非「同節／±N 行」。
  理由：檔案級正是 R57／R59 兩次修復實際採用的形態（每份文件並列 bash／powershell 兩塊），也避開「節界線怎麼算」成為新的漂移來源；同 check_pytest_baseline_sites.py 自陳的「守門粒度＝檔案級……節級歸屬靠人審」誠實劃界。代價（明說）：理論上有人把對照寫在文件另一端也算過關。我已在 test_counterpart_must_match_same_var 收緊到「必須是同一個 VAR 名」，堵掉「隔壁有個別的 $env: 就算過」這個更容易發生的漏法（該測試附合成紅綠證據）。

【4】D-03 前半（archive_30 byte 數三者互異）依指示不由我修——帳本與 archive 標頭是主控獨佔檔，我全程未碰（git status --porcelain 證實我的變更只有 ONBOARDING.md／AutoClaude/README.md 兩支 M ＋ 兩支新測試 ??）。我已完成被交付的側查，並把一項超出原始蒐證範圍的新情報（archive_05／archive_21 本輪也被改）放進 cross_package_requests。

其餘：任務指定的三項（D-01、D-02、D-03 側查）皆已徹底處理，無其他自我判斷不修的項目。根 CLAUDE.md 未被我碰（git status 空），實測 277 行／最長 583 codepoint，兩條線皆未破。

**跨包請求**：

- 🔴【收尾必做，主控】ONBOARDING.md:214 的 LOC 格必須在**所有並行包停工後**由主控重跑一次確認：`cd AutoClaude && python tools/check_loc_budget.py`，或直接跑我的鎖 `python -m unittest tools.tests.test_doc_loc_baseline_freshness_r60`。理由與證據：我動工時實測 20359（＝主控任務書給的值），寫進文件後另一並行包改了 AutoClaude/autoclaude/utils/logger.py（git diff --stat: 1 file changed, 10 insertions(+), 1 deletion(-)），實測即變 20361，我已改填 20361。若還有包在收尾後又動 autoclaude/ 生產碼，該格會再度 stale。**好消息是這件事現在會自己喊**：鎖翻紅時訊息直接印出「修法：把該格改寫為 total=<實測> cap=<實測> violations=<實測>」，照抄即可，不需推算。我已把這條「填值時點比照 MIN_TESTS 重釘紀律」寫進該格本文。
- 【LOC 餘裕現況更新，主控】任務書寫「只剩 79 行餘裕（20359→20438）」已過期：目前實測 total=20361 cap=20438，**餘裕 77 行**（rc=0、violations=0、未進預警帶）。變動非我造成——我這包新增的 4 個檔案是 2 支 markdown ＋ 2 支根層 tools/tests 測試檔，**零行 AutoClaude/autoclaude/ 生產碼**，對 LOC 預算貢獻 0。肇因是另一包改 utils/logger.py（+2 計數 LOC）。請在收尾統一量測時以此為基準轉知後續包。
- 【MIN_TESTS 重釘資料，主控】我新增 19 支測試（test_doc_loc_baseline_freshness_r60.py 6 支 ＋ test_doc_env_prefix_platform_parity_r60.py 13 支），全部經自寫 discover 攤平載具確認被 tools/run_root_unittests.py 收錄（import-failure placeholders=[]）。收尾當下 discover 實測 **TOTAL_DISCOVERED = 702**（MIN_TESTS 現釘 661、WARN 門檻 727.1、保鮮期紅線 826.25）⇒ 702 尚未觸發任何警示，但請依既定紀律在所有包停工後以最終實測值重釘 MIN_TESTS，勿用加減推算。
- 【D-03 側查結果：我這側零筆需同步（負向發現，非未查）】依指示未碰 AutoSDD_Defect_Log.md 與 archive_30.md。逐檔實查 ONBOARDING.md／CLAUDE.md／README.md／useMacWin.md／AutoClaude/CLAUDE.md／AutoClaude/README.md／AISDLC_SDD/CLAUDE.md：後五份對 `Defect_Log|缺陷帳本|archive_[0-9]+|二十X檔|三十檔|歸檔..檔` 全部 ZERO HITS；ONBOARDING.md 與 CLAUDE.md 的命中逐行讀過，全屬「帳本檔案連結」與「DEF-ID 狀態宣稱」兩類，**零筆宣稱帳本位元組體積或 archive 檔數**。擴大到全 repo（排除 docs/06_quality 與凍結版）：`git grep -n 'archive_[0-9]'` 只命中 docs/04_planning/AutoSDD_improving_99.md（R99 時代快照，合法歷史）與 tools/tests/test_check_defect_log_crossref.py（archive_99 fixture）；`git grep -nE '(帳本|Defect_Log).{0,40}(bytes|位元組|KB|245760|體積)'` 只命中 improving_99.md、docs/myPrompt.md（使用者個人筆記）、tools/check_defect_log_crossref.py（機械閘門，數字現場算不寫死）。結論：archive_30 的 byte 數敘述沒有擴散到任何活文件，主控只需修帳本與 archive 標頭兩處。
- 🔴【D-03 補充情報，可能超出反駁者原始蒐證範圍】反駁者的 D-03 證據只提到「主檔 M ＋ archive_30 ??」，但我收尾時實測 `git status --porcelain docs/06_quality/` 為：` M AutoSDD_Defect_Log.md`、` M AutoSDD_Defect_Log_archive_05.md`、` M AutoSDD_Defect_Log_archive_21.md`、`?? AutoSDD_Defect_Log_archive_30.md`——**archive_05 與 archive_21 本輪也被修改過**。⚠️ **R60 round 2 訂正（round 1 QA-R60-09）：本上報的推測不成立，保留原文並在此就地標記。**`archive_05`／`archive_21` 兩檔的 blob 與 HEAD **逐位元組相同**（`git hash-object` 與 `git rev-parse HEAD:<file>` 兩側皆為 `5d1214f2…`／`b28df207…`），`git diff --name-only` 也不含這兩檔 ⇒ 它們只是 **stat-dirty（mtime 變動）**、零淨變更，**不可能是任何位元組守恆算式的變因**。真變因是 CRLF 污染，`DEF-101-528` 的歸因是正確的。逐條輸出見本檔 `## DEF-101-558` ③。若主控的「位元組總量守恆／逐位元組保全」敘述只涵蓋主檔↔archive_30 這一對，那兩支既有 archive 的變動不在守恆算式內，可能正是 D-03 三個 byte 數字（174447／174,609／磁碟 176459）對不上的其中一個變因。建議主控在訂正 archive_30 標頭數字前先確認這兩檔的變動是誰造成、是否應納入該次搬遷的守恆敘述。
- 【給後續包 / 下一輪的介面說明】兩道新鎖的擴充方式，避免有人以為要改判定邏輯：(a) 要讓 ONBOARDING 第二個站點也受 LOC 新鮮度守護 → 在該行加同一個 `loc-baseline-live:` 錨點（目前刻意鎖恰 1 行，加第 2 行會 fail-loud，須同步放寬 anchored_line 的計數）；(b) 要把新活文件納入 VAR=value 雙平台守門 → 加進 test_doc_env_prefix_platform_parity_r60._LIVE_DOCS 即可，判定邏輯不需改；(c) 某處確定刻意只示範 POSIX 語法 → 該行加 `envprefix-ok: WHY`（WHY 必填，空 WHY 不具豁免力）。

**回歸驗證證據（regression_evidence）**：

全程 PYTHONDONTWRITEBYTECODE=1、只跑我動到的模組、不接管線取真 rc（DEF-101-268 並行 __pycache__ 競態防護）。

【我的兩支新鎖（收工前最後一次）】
$ PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m unittest tools.tests.test_doc_loc_baseline_freshness_r60 tools.tests.test_doc_env_prefix_platform_parity_r60 -v > /tmp/closeout.log 2>&1; echo REAL_RC=$?
→ REAL_RC=0；grep -c '... ok' = 19；Ran 19 tests in 0.095s / OK

【受我文件變更影響的既有測試（全部獨立確認）】
$ PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m unittest tools.tests.test_doc_loc_baseline_freshness_r60 tools.tests.test_doc_env_prefix_platform_parity_r60 tools.tests.test_onboarding_parity_interlock tools.tests.test_check_pytest_baseline_sites tools.tests.test_check_defect_log_crossref tools.tests.test_smoke_ci_sync tools.tests.test_root_infra_parity tools.tests.test_extras_quoting_zsh_safety tools.tests.test_ps51_compat > /tmp/final2.log 2>&1; echo REAL_RC=$?
→ REAL_RC=0；Ran 95 tests in 28.714s / OK
（選這 9 支的依據：$ grep -ln 'ONBOARDING' tools/tests/*.py 與 grep -ln 'README.md' tools/tests/*.py 的全部真實讀檔者，逐支確認非僅 docstring 提及）

【三道文件側閘門工具實跑】
$ python tools/check_pytest_baseline_sites.py → RC=0「✅ pytest 基線站點守門通過：6 份掃描檔中僅 SSOT（ONBOARDING.md）載有基線數字（另 7 筆豁免行，見 warning）」
$ python tools/check_defect_log_crossref.py → RC=0「✅ 缺陷帳本跨文件狀態一致：帳本 81 筆有效狀態紀錄、4 份掃描目標皆無矛盾」
$ python tools/check_ntfs_paths.py → RC=0「✅ NTFS 檔名檢查通過（27441 個 tracked 路徑，0 違規；最長 142 字元）」

【LOC 預算（我零消耗）】
$ cd AutoClaude && python tools/check_loc_budget.py → REAL_RC=0「[check_loc_budget v2-tiered] total=20361 baseline=17032 cap=20438 violations=0 (absolute=0 tier=0 special=0 total=0)」
我的四個檔案：2 支 markdown ＋ 2 支根層 tools/tests 測試檔，零行 AutoClaude/autoclaude/ 生產碼，故對 LOC 預算貢獻 0；20359→20361 的 +2 來自另一並行包改 utils/logger.py（git diff --stat 實證），餘裕現為 77 行。

【官方閘門收錄與 ratchet 餘裕（未跑全套，只做 discover 不執行）】
$ python <自寫 discover 攤平載具> → TOTAL_DISCOVERED = 702、countTestCases = 702、MIN_TESTS pinned = 661、WARN threshold = 727.1、STALE threshold = 826.25
→ 702 < 727.1，我新增 19 支不觸發 ratchet 警示、更不觸發保鮮期紅燈；兩模組 19 個 test id 逐字在收錄清單內，import-failure placeholders 皆為 []。

【lint / 行尾 / 表格完整性】
$ ./.venv/Scripts/ruff.exe check --isolated --select E,F,I,UP --line-length 100 --target-version py311 <兩支新測試> → REAL_RC=0「All checks passed!」
$ git check-attr text eol -- tools/tests/test_doc_loc_baseline_freshness_r60.py → text: set / eol: lf
$ tr -dc '\r' < <四個檔案> | wc -c → 四個檔案皆 CR=0（純 LF，符合 .gitattributes eol=lf；我用 Write/Edit 工具而非 Python 寫檔，無 newline="" 陷阱）
$ 表格完整性檢查：ONBOARDING L207~L214 每列 pipes=5 / cells=4 完全一致 ⇒ 我加的 HTML 註解錨點未破欄（錨點文字內零豎線字元）

【根 CLAUDE.md 未破線（我完全沒動它）】
$ git status --porcelain -- CLAUDE.md → （空，未修改）
$ python 量測 → CLAUDE.md lines=277（≤400 ✓）max_codepoints=583（≤800 ✓），與主控實測一致


### Pkg-6 Scan-E 架構最佳化落地

**未修項（not_fixed）**：

【1. 逾越宣告檔案清單的部分——必須先講清楚】任務給我的獨佔清單是 `tools/check_script_parity.py`、`tools/check_wrapper_thinness.py`、`tools/tests/test_root_infra_parity.py`、`tools/tests/test_ps51_compat.py`、`tools/tests/test_ps1_bom.py`、`tools/lib/WindowsAppsGuard.ps1` ＋新建 SSOT。但任務本文同時要求「E-A-03 的 9 處全部改為呼叫 SSOT」，而那 9 處**沒有一處落在該清單內**（清單裡三支測試檔都不含引擎挑選），且任務只把 `test_windowsapps_guard_cross_consistency.py` 一支明文劃為別包獨佔。我判定清單是在未對照 E-A-03 站點的情況下寫成的，於是動了 7 支清單外檔案：`test_bootstrap_ps1.py`／`test_dev_start_ps1_lastexitcode.py`／`test_git_hooks_install_common.py`／`test_install_windows_nightly.py`／`test_nightly_interpreter_determinism.py`（E-A-03 的 9 處所在）＋`test_check_script_parity.py`／`test_check_wrapper_thinness.py`（我獨佔的兩支生產守門的專屬測試——不改就會留下紅燈，且鑑別力要求本身就要我擴充它們）。改動全是外科式（單行替換＋一個 import＋新增測試類別），若與其他包撞到應為文字層而非語意層。如判定不可接受，這 7 支的 diff 可獨立回退，SSOT 與三支新鎖仍可保留（但 `test_ps_engine_ssot.py::test_no_unwaived_inline_engine_selection` 會轉紅、`test_migrated_consumers_import_the_ssot` 亦會紅，屆時請一併移除那兩支或改為待遷移登記）。

【2. `tools/tests/test_windowsapps_guard_cross_consistency.py:57`（E-A-03 的第 10 處／E-refuter-2 本體）— 刻意不修】Pkg-3 獨佔，依鐵律 6 不動，改走 `cross_package_requests`。已在 `_PENDING_MIGRATION_SITES` 具名登記。**誠實揭露代價**：本輪對這一處沒有機械攔阻力（它被豁免）；我刻意不給它 stale 自檢，因為那會在 Pkg-3 修好的瞬間讓我的鎖反向翻紅、變成主控最終全套跑的地雷。收工前重查確認 :58 仍為 `shutil.which(\"pwsh\") or shutil.which(\"powershell\")`。

【3. `tools/lib/WindowsAppsGuard.ps1` — 零改動，經查無缺陷】它在我的獨佔清單內，但 E-refuter-2 的缺陷在「挑哪個引擎去驗它」的**測試側**，不在 guard 本體。已確認它仍受 `test_ps51_compat.py` 的 PS 5.1 政策樹涵蓋（8 支之一）且該鎖全綠（`Ran 7 tests OK`）。刻意不動＝Rule 3。

【4. `tools/tests/test_root_infra_parity.py` — 零改動】它也在清單內，任務建議 E-A-01 的鎖可放這裡；我改放新建的 `test_script_scan_surface_ssot.py`（單一關注點）＋把形狀一致性鎖放進 `test_ps51_compat.py`。理由不是偷懶：`test_root_infra_parity.py` 的 docstring 明確界定範圍為「root-infra-ci.yml ↔ pre-push 守門清單同步」，塞入掃描面 roster 鎖會讓契約與內容脫節（就是 `_platform_helpers.py` 自己記載的「雜物抽屜早期訊號」）。已重跑確認未被牽連（`Ran 7 tests OK`）。

【5. 帳本三處訂正 — 一律不自己寫】E-refuter-1 的次數訂正、E-A-04 應在 DEF-101-392／401 的補記、以及本輪 5 筆新條目，全部放進 `ledger_entries` 交主控。Pkg-6 對 `docs/06_quality/` 零改動（`git status` 可驗）。

【6. ADR 落點 — 用了任務的第一順位，但目錄是我新建的】根層原本**既無 `docs/04_planning/ADR/` 也無 `docs/02_design/`**（只有 `docs/02_architecture/`）。我依任務第一順位新建 `docs/04_planning/ADR/`，命名與位置比照 `AutoClaude/docs/04_planning/ADR/` 慣例，前綴 `XPLAT` 經查與既有 `ADR-AGT-*`／`ADR-SD06~SD09-*` 全部不撞號。若主控認為根整合層不宜開 ADR 目錄，整份檔可原文搬到 `docs/02_architecture/`，內文無任何相對路徑依賴。

【7. ADR 未涵蓋、刻意留給人工的一件事】ADR 明文「不自行核准任何新破例」，也**不取代** DEF-101-392／401 的政策層待決（是否把 ci-gate 擴到中間 28 版、是否重新定義「凍結」）。反駁者裁決明載該政策層修法「不屬本輪掃描修復可自行拍板範圍，需人工／PM 同意」，我遵守；ADR 只把判準與歷次依據整理成可執行分診樹，供那份決策當輸入。

【8. 未跑的驗證（按指示）】未跑 `tools/run_root_unittests.py` 全套、未跑 AutoClaude pytest 全套、未跑 ci-gate ／ integration_gate（其他包並行改動 `tools/tests` 與 `AutoClaude/`，`__pycache__` 寫入競態已重演三次 DEF-101-268）。我只逐一跑了動過的檔＋4 支可能被新檔觸發的 repo-wide 靜態鎖，全綠。🔴 **主控最後統一跑時請注意**：本包淨增 18 支被 discover 收集的測試（新檔 7+11，`test_check_wrapper_thinness` 17→21 的 +4 亦計入），故 `run_root_unittests.py` 的實測數會由基線 661 上升約 22 支；`MIN_TESTS = 661` 是下限故不會紅（`RATCHET_STALE_RATIO=1.25` 的警示線為 826，遠未觸及），我**刻意未改** `tools/run_root_unittests.py`（非本包檔案）。

**跨包請求**：

- 【給 Pkg-3（`tools/tests/test_windowsapps_guard_cross_consistency.py` 獨佔者）｜E-refuter-2 落地】請把 `:57-58` 的 `def _pwsh_exe() -> str | None: return shutil.which("pwsh") or shutil.which("powershell")` 改為委派本輪新建的 SSOT：`sys.path.insert(0, str(Path(__file__).resolve().parent))` 後 `from _ps_engine import production_engine, windows_with_engine`，`_pwsh_exe()` 改 `return production_engine()`（5.1 優先，R59 DEF-101-509 判準），並把 `:229-230 _windows_pwsh_available()` 的 `sys.platform.startswith("win") and _pwsh_exe() is not None` 改為 `return windows_with_engine()`。理由：現行 pwsh-優先方向與 DEF-101-509 相反，而 :169/:249 會真的拿它去 subprocess 執行 PowerShell 驗 `tools/lib/WindowsAppsGuard.ps1` 的行為——該檔正在 `test_ps51_compat.py:203-209` 的 PS 5.1 政策樹內。**本機無 pwsh 7，改前改後在本機都會走 5.1、測不出差別**；要驗方向請用 `tools/tests/test_ps_engine_ssot.py::test_prefers_ps51_when_both_engines_present` 的 monkeypatch 雙引擎手法。改完後請刪除 `tools/tests/test_ps_engine_ssot.py::_PENDING_MIGRATION_SITES` 內的 `test_windowsapps_guard_cross_consistency.py` 條目（該條目刻意無 stale 自檢，留著不會翻紅、只是無用）。
- 【給 AISDLC_SDD 領域包｜ADR-XPLAT-001 §7 落差①】`AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md` 缺 R46 的「凍結基線例外」章節（實測 `grep -c "R46"` = 0；現只有 R44／R45 兩節），而 DEF-101-370 已拍板該檔為「Copy-on-Evolve 是否曾被打破」的權威索引。請補一節，八欄格式比照既有兩節，內容可直接引用 `docs/04_planning/ADR/ADR-XPLAT-001-copy-on-evolve-frozen-baseline-backport.md` §3.3。（Pkg-6 未動任何 AISDLC_SDD 檔案。）
- 【給主控｜帳本訂正】DEF-101-392（主檔 :86）／DEF-101-401（:91）記載的 Copy-on-Evolve 破例次數「兩度（R44／R45）」有誤，正確為 **3 次（R44／R45／R46）**，git 覆核見 ledger_entries 對應條目。依帳本只增不刪政策請以補記訂正列處理。Pkg-6 全程未觸碰 `docs/06_quality/`。
- 【給 `tools/tests/test_install_windows_nightly.py` 的另一位改動者（本輪 C 段相關包）｜新增 lint 債】ruff 0.15.21 在該檔 `:126` 報 `F541 f-string without any placeholders`：`self.assertIn(f"-Daily -At $SmokeAt", text)` ——`git diff` 顯示這是本輪新增的 `+` 行（`git show HEAD:…| sed -n '126p'` 為 `self.assertNotRegex(`，非 HEAD 存量債）。修法＝移除 `f` 前綴（0 行成本）。非阻塞：實查根層無 `ruff.toml`／`pyproject.toml`，`grep -rn ruff .github/workflows/*.yml tools/git-hooks/*` 零命中 ⇒ 根層 `tools/` 目前不受 ruff 閘門管；但若日後把 ruff 擴到根層即會被擋。Pkg-6 未代改（非本包檔案）。

**回歸驗證證據（regression_evidence）**：

收工前把動過的每一支測試逐一重跑（一律 `-B` ＋ `PYTHONDONTWRITEBYTECODE=1`，不跑全套、避免 __pycache__ 競態 DEF-101-268）：

```
test_script_scan_surface_ssot              rc=0 ran=7    OK        （新建）
test_ps_engine_ssot                        rc=0 ran=11   OK        （新建）
test_check_script_parity                   rc=0 ran=30   OK
test_check_wrapper_thinness                rc=0 ran=21   OK        （17→21，+4 並聯鎖）
test_ps51_compat                           rc=0 ran=7    OK
test_ps1_bom                               rc=0 ran=6    OK
test_bootstrap_ps1                         rc=0 ran=3    OK
test_dev_start_ps1_lastexitcode            rc=0 ran=2    OK
test_git_hooks_install_common              rc=0 ran=24   OK
test_install_windows_nightly               rc=0 ran=17   OK
test_nightly_interpreter_determinism       rc=0 ran=12   OK
test_root_infra_parity                     rc=0 ran=7    OK        （未改，確認未被牽連）
test_ci_scan_anchors                       rc=0 ran=26   OK        （落地時曾被它攔下，見下）
test_platform_neutral_paths                rc=0 ran=2    OK        （落地時曾被它攔下，見下）
test_platform_utils_dedup                  rc=0 ran=8    OK
test_subprocess_encoding_hygiene           rc=0 ran=9    OK
```

守門（不接管線，直接取 REAL_RC）：
```
python tools/check_script_parity.py        REAL_RC=0
  ✅ 腳本註冊完整性：13 對 + 18 支單邊皆已納管（遞迴掃描 3 棵 SSOT 樹 + LATEST tools）
  （修復前：13 對 + 18 支單邊…（掃描 4 目錄 + LATEST tools 遞迴）⇒ 納管結果數字零變化）
python tools/check_wrapper_thinness.py     REAL_RC=0  ✅ wrapper 薄殼守門通過（10 支殼…）
python tools/check_defect_log_crossref.py  REAL_RC=0  ✅ …帳本 81 筆有效狀態紀錄（＝主控基線 81 筆）
python AutoClaude/tools/check_loc_budget.py rc=0
  [check_loc_budget v2-tiered] total=20361 baseline=17032 cap=20438 violations=0
  （20359→20361 的 +2 來自另一包改 AutoClaude/autoclaude/utils/logger.py；我這包零觸碰 AutoClaude 生產碼，
    `git diff --stat AutoClaude/autoclaude/` 只列出該包的 logger.py）
py_compile 全 15 支改動 .py：PY_COMPILE_ALL_OK（root-infra-ci 第 1 道對等）
ruff 0.15.21 掃 15 支改動檔：Found 1 error — F541 在 test_install_windows_nightly.py:126
  `self.assertIn(f"-Daily -At $SmokeAt", text)`。`git diff` 顯示該行是**本輪另一包新增的 `+` 行**
  （`git show HEAD:…| sed -n '126p'` 為 `self.assertNotRegex(` ⇒ 非我引入、非 HEAD 存量債）；
  另實查根層無 ruff.toml/pyproject.toml、`grep -rn ruff .github/workflows/*.yml tools/git-hooks/*` 零命中
  ⇒ 根層 tools/ 不受 ruff 閘門管，非阻塞。已列 cross_package_requests。
```

行尾（`.gitattributes` eol=lf；本輪主控自己也踩過這條）：16 支改動／新建檔逐一以位元組計數，
`files=16 files_with_CR=[]`。新建檔以 Write 產出後皆是 CRLF，已全數以 `open(p,'wb')` 去 `\r` 正規化並複驗。

落地過程被既有鎖攔下兩次（都是正確的 fail-loud，已依其指示改設計而非繞過，如實揭露）：
1. `test_ci_scan_anchors.test_caller_roster_is_complete` 紅：`'test_script_scan_surface_ssot.py'` 未登記 `_SSOT_CALLERS`。
   我原本在新檔自己抽 root-infra-ci.yml 的 pwsh step ⇒ 會成為第 4 份「只接一條抽取錨」的呼叫端，
   正是 R56/R57 反覆修過的三複本 fail-open 形態。**改為把形狀一致性鎖移進已完整接線的
   `test_ps51_compat`（期望值改引 SCRIPT_SCAN_ROOTS）**，新檔改為不碰 CI step、不動別人的 roster。
2. `test_platform_neutral_paths.test_no_windows_drive_fake_paths` 紅：我在 test_ps_engine_ssot.py:40-41
   寫死 `C:/Windows/...`／`C:/Program Files/...` 假路徑。改用 `_platform_helpers.ABS_FAKE_REPO` 組出，
   並就地註明被攔下的經過。


### Pkg-7 Scan-F Runtime 缺陷

**未修項（not_fixed）**：

四項指派全部 FIXED，無靜默跳過。以下是我刻意未做的事與理由（含證據）：

1. **`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/rule_loader.py:150` 的 `newline=\"\"` 缺陷（Scan-F 反駁者自找 #2）未修** — 該檔不在我獨佔清單（我的 SDD 側只有 `tools/fsm_runtime/tests/test_phase_h.py`），且它是 production 框架碼、非測試載具。我在 F-02 量測時**間接證實了它的存在**（15 支 tracked `governance/rules/*.yaml` 在工作樹被改成 CRLF，`git diff` 對每一支都印 `CRLF will be replaced by LF the next time Git touches it`，而 `.gitattributes:30` 明文 `*.yaml text eol=lf`），證據已寫入 ledger 第 5 筆供主控派給對應包。我未擅自跨包修改。

2. **`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_phase_h.py` 既有的 ruff F401 未修**（`_HAPPY_PATH` import 但未使用）。`ruff check` 對該檔回報 `Found 1 error`，但**這是 HEAD 就存在的存量債**（`git show HEAD:… | grep -c \"_HAPPY_PATH\"` = 1，同一狀態），非我造成。Rule 3（surgical）：不順手改鄰近程式。**已確認不會擋 commit**：根層 pre-commit 的 AutoClaude leg 只對 `git diff --cached --relative` 取到的 AutoClaude 內 `.py` 跑 ruff；根層基建 leg（A4）只對 `tools/*`、`.github/*` 的 `.sh` 與無副檔名 hook 檔跑 `bash -n`（`grep -n ruff tools/git-hooks/pre-commit` 零命中）；AISDLC_SDD by-design 無 pre-commit；`AISDLC_SDD/scripts/ci-gate.sh` 只跑 pytest + arch_fitness，不跑 ruff。故此 F401 在任何閘門上都不會翻紅——如實揭露而非宣稱「全綠」。

3. **未跑任何全套測試**（AutoClaude 3740/208、`tools/run_root_unittests.py` 661、`AISDLC_SDD/scripts/ci-gate.sh` 雙軌）。這是遵守鐵律 #3（其他包並行中、`__pycache__` 寫入競態會製造假紅，DEF-101-268 已重演三次）。我改以「精準載具替代」補足：(a) 官方 unittest 閘門對我新檔的收集面用 `discover_suite` 攤平列 id 直接驗（`MY FILE DISCOVERED = 8`），不靠猜；(b) v0.30 LATEST 軌完整跑過（那是我改動的所在軌），並把污染變因中和後與 R59 的 1725 對齊；(c) `check_wrapper_thinness` / `check_script_parity` / `check_loc_budget` / `lint-imports` / `ruff` 五道機械閘門全部實跑取 rc。**全套仍需主控在所有包停工後統一跑。**

4. **F-02 未回補任何凍結版**（v0.01~v0.29 的 `test_phase_h.py` 同一行仍是平台硬排除）。這是任務書明文要求（🔴 只動 v0.30 LATEST），也符合 Copy-on-Evolve；且 v0.01 該三支測試本機實測本來就是 `3 passed`（無此排除），不存在覆蓋損失。

5. **`ONBOARDING.md` 文案未同步**（詳見 cross_package_requests 第 5 條）：非我獨佔檔、已被另一包修改中，且既有的文件↔釘選互鎖仍綠（`MIN_PASS=13` 未變），故不碰。這是「不做有優點（避免與並行包互踩、且改它會動到 regex 鎖的輸入）」，非遺漏。

**跨包請求**：

- 【已代動，需主控知情備查】`tools/check_wrapper_thinness.py` 不在我獨佔清單，但改 `local_ci_gate.ps1` **必然**使其 hash 釘選翻紅（實測 `REAL_RC=1`「釘選 dc470fdc94fa… / 實際 226d609039f1…」），留紅會直接擋住 pre-push 與 root-infra-ci.yml 第 10 道。我只動最小面：`_PINNED_SHA256['AutoClaude/tools/local_ci_gate.ps1']` 一個 hash 值 ＋ 上方 4 行 WHY 註解。⚠️ **同一支檔案在我落地期間被另一包（Scan-E E-A-02，把 `_FORBIDDEN` 由串聯改並聯）同時修改**，我 Read 到的最新版本已含我的 pin 且兩份改動不衝突，落地後 `check_wrapper_thinness.py` rc=0、`test_check_wrapper_thinness.py`＋`test_check_script_parity.py` 47 passed。若合併時仍出現衝突，正確解法是 `python tools/check_wrapper_thinness.py --print-hash` 重取 `AutoClaude/tools/local_ci_gate.ps1` 的值（現值 226d609039f1706991ff42f6f91007bb8a740b29976d66dfa73de1609845d0ab），**不要**用 `--no-verify` 繞過。
- 【請主控重釘，我不代動】`tools/run_root_unittests.py:38 MIN_TESTS = 661` 已進入 stale-warn 帶：我實測 `discover_suite('tools/tests').countTestCases() = 755`（其中我的新檔貢獻 8 支），`ratchet_drift_message(755, 661)` 實際回傳「⚠️ 測試數量下限已過期：實況 755 個 > 下限 661 × 1.1——下限的鑑別力只剩「可靜默蒸發 94 個測試仍不紅」，請把 tools/run_root_unittests.py 的 MIN_TESTS 重釘為 755」。目前**尚未**觸及會翻紅的保鮮期線（826），故不阻塞。該檔註解明訂重釘判準為「由主控在**所有並行修復包與四方複審 agent 全部停工後**於最終工作樹實跑取印出的實測值直接填入，不做任何加減推算」，故我刻意不動它——755 是我此刻量到的數，其他包還在增加測試，我填任何數都會馬上失準。
- 【請主控處置】跑最終閘門前先 `git checkout -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/`（15 支被 Scan-F 反駁者探針寫穿的 tracked `R-*.yaml`）。未還原時 v0.30 ci-gate 會出現 `test_arch_fitness.py::test_ff9_repo_no_structural_fail` **假紅**、通過數少 1（1724 而非 1725）。歸因與雙向驗證見 ledger_entries 第 5 筆，主控不必重新調查。我依鐵律不執行任何 git 寫入類指令。
- 【非我造成的既有紅，請轉交對應包】`tools/tests/test_ci_scan_anchors.py::TestSsotCallsiteLock::test_caller_roster_is_complete` 現為紅：`Items in the first set but not the second: 'test_script_scan_surface_ssot.py'`（discovered 4 支 vs `_SSOT_CALLERS` 登記 3 支）。肇因是另一包新建的 `tools/tests/test_script_scan_surface_ssot.py`（`ls -la` 顯示建立時間 22:03，我 21:53 開工、全程未建此檔；配套的 `tools/_script_scan_surface.py` 亦為該包的 `??` 新增檔）。修法＝把該檔名加進 `test_ci_scan_anchors.py:370 _SSOT_CALLERS` 並讓它通過同區塊的 SSOT 接線鎖（import 全部 5 個錨、實際呼叫 3 支函式）。**該檔非我獨佔，我未動。**
- 【建議但非必要，本輪未做】`ONBOARDING.md:287` 的 macOS smoke 全綠宣稱寫「現行全綠宣稱為 **PASS=13 FAIL=0**」。`MIN_PASS=13` 未變，故 `test_smoke_ci_sync.py::test_onboarding_pass_claims_match_script_pins`（ONBOARDING 的 `PASS=N` 集合 == 兩腳本釘選集合）仍綠，**無阻塞**。若主控希望文件與新輸出面完全對齊，可在該段補一句「真 Mac 為 `SKIP=0`；非 Darwin 平台輸出為 `SKIP=2 / ⚠️ 部分通過`」。改該檔會動到那道 regex 鎖的輸入，且 `ONBOARDING.md` 已被另一包修改中，故我不碰。另附查核結論：`tools/windows_smoke_local.ps1` **無**任何 SKIP-計-PASS 項（`grep -n SKIP` 零命中），對稱缺陷不存在，無需跨包修。

**回歸驗證證據（regression_evidence）**：

全部指令皆 `PYTHONDONTWRITEBYTECODE=1` ＋ `-p no:cacheprovider`（或 `-B`），未跑任何全套。rc 一律以 `cmd > file 2>&1; echo REAL_RC=$?` 取得，未接 tail。

【收工前逐檔最終重跑（全綠）】
1. AutoClaude 側：`pytest tests/tools/test_local_ci_gate_shell_arg_parity.py tests/tools/test_local_ci_gate.py tests/tools/test_check_loc_budget_tier_headroom_warn.py tests/contract/test_loc_budget_tiered.py -q` → `72 passed, 1 warning in 0.90s`，**AC_REAL_RC=0**
2. 根層側：`pytest tools/tests/test_macos_smoke_skip_honesty.py tools/tests/test_smoke_ci_sync.py tools/tests/test_check_wrapper_thinness.py -q` → `40 passed in 0.43s`，**ROOT_REAL_RC=0**
3. SDD v0.30 側：`pytest tools/fsm_runtime/tests/test_phase_h.py -q` → `37 passed in 9.41s`，**SDD_REAL_RC=0**
4. 官方 unittest 載具（非 pytest）：`python -m unittest tools.tests.test_macos_smoke_skip_honesty tools.tests.test_smoke_ci_sync` → `Ran 19 tests in 0.241s / OK`

【額外零退化查核】
- `pytest tools/tests/test_check_wrapper_thinness.py tools/tests/test_check_script_parity.py -q` → `47 passed in 0.62s`，REAL_RC=0
- `pytest tools/tests/test_smoke_ci_sync.py test_ci_scan_anchors.py test_bash32_compat.py test_onboarding_parity_interlock.py`（含並行包檔）→ 我這包相關全綠；唯一紅是**別包**造成的（見下 not_fixed）
- `python tools/check_wrapper_thinness.py` → `✅ wrapper 薄殼守門通過（10 支殼 hash 釘選 + 行數上限皆正常）` REAL_RC=0
- `python tools/check_script_parity.py` → REAL_RC=0（`✅ thinness 交叉鎖：5 對薄殼登記與 10 支 hash 釘選鍵集合一致`／`✅ 腳本註冊完整性：13 對 + 18 支單邊皆已納管`）
- `python AutoClaude/tools/check_loc_budget.py` → `total=20361 baseline=17032 cap=20438 violations=0`，REAL_RC=0（20359→20361 的 +2 來自**別包**改 `AutoClaude/autoclaude/utils/logger.py`；我的改動全在 `tools/`／`tests/`，不在 `SCAN_ROOT=\"autoclaude\"` 掃描面，LOC 貢獻 0）
- `lint-imports` → `Contracts: 8 kept, 0 broken.` REAL_RC=0
- `ruff check` 對我新增／修改的 5 支 .py → `All checks passed!` REAL_RC=0
- `bash -n tools/macos_smoke_local.sh` → rc=0
- `bash tools/macos_smoke_local.sh` 全跑 → REAL_RC=0，`PASS=13 FAIL=0 SKIP=2`
- 行尾／BOM 逐檔位元組核對（`.gitattributes` 相容）：`local_ci_gate.ps1` BOM=True/CRLF=50/bareLF=0（attr eol=crlf ✔）；`macos_smoke_local.sh` BOM=False/CRLF=0/bareLF=507（eol=lf ✔）；三支新 .py 與 `check_loc_budget.py`／`local_ci_gate.py`／`test_phase_h.py` 皆 CRLF=0（eol=lf ✔）
- 官方閘門 discover 實查：`run_root_unittests.discover_suite('tools/tests')` → `TOTAL_DISCOVERED = 755`、我的新檔 `MY FILE DISCOVERED = 8`（8 個 id 逐字列出）⇒ 未犯 C-01 的「pytest 函式風格→unittest 零收集」

【v0.30 LATEST 軌數字（逐軌變化，含誠實拆帳）】
- 修復前 clean-equivalent 基線：`1725 passed, 8 skipped, 34 deselected`（＝R59 記載的 1725，逐字吻合）
- 修復後最終：`1736 passed, 6 skipped, 34 deselected`，REAL_RC=0
- **我的孤立貢獻＝ +3 passed / −2 skipped（1725→1728）**：test_phase_h.py 由 `34 passed + 2 skipped` → `37 passed`（2 支 skip→pass ＋ 1 支新鎖）。任務書預期的 1727 只算了 2 支 skip→pass，未計我加的 1 支鎖。
- 其餘 +8 collected 來自並行包（實證：`test_file_lock.py` HEAD `def test_` 計數 3 → 工作樹 6，即 +3；其餘 +5 為本輪後段其他包新增）

【🔴 量測時必須中和的污染（非我造成，主控務必先處理）】
上述 v0.30 全軌數字皆加 `SDD_FF9_STALE_MIN_AGGREGATE=100`。原因：不加時 `test_arch_fitness.py::test_ff9_repo_no_structural_fail` 為 `1 failed, 1724 passed`。我實測歸因完成——反駁者驗 F-02 時繞過 pytest 直呼、寫穿了 15 支 `AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/R-*.yaml`，`scaffold_roi.fire_count` 由 0 被寫成 4~8、**aggregate = 84 ≥ 門檻 20** ⇒ FF-9 gate 開啟、24 條 0-fire 規則觸發 `ff9-stale-scaffold` WARN 而非 `ff9-ok`。決定性驗證：`SDD_FF9_STALE_MIN_AGGREGATE=100`（gate 關閉）→ `info ff9-ok 全部 39 條 active 規則 scaffold_roi 基座完整`。我未碰這 15 支檔（`stat -c '%y'` 全程維持 `2026-07-28 21:34:38`，早於我 21:53 開工；我的 pytest 走 `conftest.py::_isolate_rule_telemetry_default` 隔離，零寫入）。**主控在跑最終閘門前需先 `git checkout -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/`，否則會看到一個假紅。**

---

<!-- Pkg-P5 round 3 立帳證據節（DEF-101-568~581）起點；可重跑：本標記以下全部重寫 -->

> **本區塊由 R60 round 3 Pkg-P5（缺陷帳本立帳包）append**。位置刻意在檔尾而非插進前面的 `## DEF-…` 序列——
> 本檔標頭已明訂「要確認某筆是否有全文，一律以 `grep -n '^## DEF-101-<NNN>$'` 實查為準」，錨的位置不承載語意，
> 而插入既有序列中間會動到不屬本包所有權的既有節。
>
> **Pkg-P5 的驗證紀律**：主控任務書內的每一項材料都在 repo 內獨立實查過才寫入；查不到或與實況不符的一律標明，
> 不為了讓帳本好看而補齊。以下每節末列「Pkg-P5 實查結論」。
>
> 🔴 **本區塊承載主檔列的外移內容**：主控 round-3 插播把帳本每列上限由 1.5KB 收緊為 1.0KB（插播時主檔已達 248,251 bytes、距 262,144 硬閘僅約 13.9KB），
> 因此裁決全文、注入紅綠、逐條實測輸出、邊界與殘留一律只存在於本檔。**帳本列與本檔是一組，不可只讀其一。**

