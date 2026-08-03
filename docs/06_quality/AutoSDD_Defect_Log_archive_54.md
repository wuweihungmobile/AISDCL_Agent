# AutoSDD Defect Log — Archive 54

> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 **5 筆已結列**。
>
> **搬遷判準的權威來源是 `tools/archive_defect_log.py`**（程式即判準，本標頭不重述細則）。
> 該工具落實 6 項搬遷判準（①狀態欄分類已結（fixed／wontfix／closed-by-decision）／②狀態欄無活躍字樣（open／routed／deferred／watch／workaround，ASCII 邊界非子字串；程式碼片段與角引號引述內的字樣不算，R68 收窄）／③被 crossref 掃描目標宣稱過狀態者可搬，但搬後該宣稱必須仍解析得到（帳本家族＝主檔 ∪ archive；由 --check 判準(8) 實跑驗證，R68 改寫）／④散文帶交棒字樣者需 `--ack-handoff` 具名承認／⑤該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）／⑥無外部居所指針宣稱本列現居主檔（指針反向依賴，DEF-101-612；有則硬擋，須先訂正該指針，不接受 --ack 繞過）），
> 並在落地後以 `--check` 稽核 8 項保全判準：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針：稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致、(5)歸檔索引涵蓋性：磁碟上每支 archive 都要在歸檔索引檔有一條以它為主體的 bullet（雙向）、(6)非「立帳見」方言的居所宣稱：`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID、(7)表格列欄數：每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免、(8)跨檔宣稱可解析：掃描目標的每一句狀態宣稱都要能在帳本家族（主檔 ∪ archive）解析到，且狀態一致（判準③ 改寫後的事後條件，R68）
> （本段由該檔的 `MOVE_CRITERIA`／`CHECK_CRITERIA` 常數機械生成，逐項定義見
> `check()` docstring；**勿手改**——手寫版曾與實作脫節而被複製成永久史料）。
> **歷輪標頭曾宣稱有這樣一支腳本但 repo 內無載具**，
> 且散文所載判準與實際執行的判準不一致——R60 起改為引用可重跑的工具，見該檔 docstring。
>
> **搬遷清單**：`DEF-101-785`、`DEF-101-783`、`DEF-101-781`、`DEF-101-784`、`DEF-101-782`
>
> **本次操作備註**：R73 二審收官歸檔：搬四方複審產出的已結列
>
> 餘裕一律以 `python tools/check_defect_log_crossref.py` 的實跑訊號為權威，
> 本標頭**不對餘裕做定性宣稱**（R59 SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被推翻）。
>
> **原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。查詢缺陷現況一律先看主檔缺陷總表。

## 缺陷總表（已結列，逐字保全）

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|---|---|---|---|---|---|---|
| DEF-101-785 | 2026-08-04 | R73 四方二審（QA blocking ⑥） | 🔴 **鐵律一唯一的機械強制物本身零測試覆蓋，而它已實證漂移過一輪**。全庫 `*.py` 對 `block_bash_on_windows` **零命中**。根 `CLAUDE.md` 明載這支 hook 之所以存在，是因為純文件約束**實證無攔阻力**（R71 寫完那節的同一個回合仍用了 Bash 工具）。後果已經發生而非假想：它的指引訊息教人寫裸 `bash <script>`（在本機是壞的，`DEF-101-773`），那句錯誤指引漂了整整一輪才被 R73 抓到。**機械強制物教錯比純文件教錯更嚴重**——讀者會認為它比文件權威。同時它帶著 `.claude/settings.json` 記載過的 P0：hook 誤觸 deny 會把**所有**工具硬鎖死 ⇒「射程不得擴大」「例外一律 fail-open」不是風格偏好而是安全需求，不能靠讀 code 自覺 | P1 | 新增 `tools/tests/test_block_bash_on_windows_hook.py` | **fixed@R73** — 補四類鎖：① 行為契約以**子行程真跑**（Bash→2／Read→0／壞 JSON→2／空輸入→2；走子行程而非 import 是因為契約面是 stdin ＋ exit code）；② 非 Windows 不誤傷（注入 `os.name='posix'` 驗證，不依賴這台機器是什麼平台——`DEF-101-766` 教訓）；③ 指引訊息內容（必須指向 `Find-GitBash` SSOT、不得回頭教裸 `bash`、不得寫死磁碟機路徑、`&&` 建議必須綁生產引擎）；④ 註冊活性（必須真的掛在 `.claude/settings.json` 的 PreToolUse 且 matcher 命中 Bash——判準走 `re.search` 而非 `== "Bash"`，實測本機 matcher 是 `Bash\|Task` 正則交替，寫成相等會在 matcher 合法擴充時假紅）。33 passed |
| DEF-101-783 | 2026-08-04 | R73 四方二審（Architect B1，以 SSOT 鏡像真跑證實） | 🔴 **DEF-101-775 只修了一半：明文宣告「須同步」的 SSOT 鏡像沒動，缺陷仍活在鏡像裡，而且有 16 條 case 幫它防迴歸**。`run_local_nightly.ps1` 的 F2 區塊明文寫著「本區塊 4 條分支邏輯與 `tools/ac4_nightly_alert_parser.py` 同構（SSOT 樣板），任一邏輯變動須同步：① 該檔 ② `tests/tools/test_ac4_nightly_alert_parser.py`（16 cases）」。R73 首版改了 ps1 側卻沒動這兩個檔。Architect 二審真跑：payload＝合法 JSON ＋ 隨後一行 `[ac4_progress_check] WARN:` ⇒ `level=WARN / parsed_json=None / **stderr_lines=()**`——真值是 ALERT（已達標）被讀成解析失敗，**且連那行 WARN 的取證也一併掉了**（被吞進 json_lines 走不到 stderr 分支），而 ps1 側修法特意保住了 `[F2 stderr]` 記錄能力。`ADR-SD09-010` 記載本鏡像用途是「W1+ 遷移 ps1 至 helper-driven 模式時可直接 import」⇒ 不同步等於把缺陷埋在未來的遷移路徑上 | P1 | `AutoClaude/tools/ac4_nightly_alert_parser.py` ＋ `AutoClaude/tests/tools/test_ac4_nightly_alert_parser.py` | **fixed@R73** — `split_stdout_stderr()` 改為「累積到第一次 `json.loads` 成功即停」，其後的行**照舊走 stderr 攔截**（取證不因修 bug 而縮水）。補 2 條 case（尾隨 stderr／截斷 fail-closed），並以注入舊行為實證有牙：注入後 `test_stderr_after_complete_json_does_not_break_parsing` 轉紅（1 failed / 20 passed），還原後 **21 passed** |
| DEF-101-781 | 2026-08-04 | R73 四方二審（Architect B2／SA ②-1／SD ④ 三方獨立命中同一筆） | **DEF-101-779 的修法在同一支檔、同一個 commit 內當場重生同一個病**：`tools/install_windows_nightly.ps1` help 區塊被寫入一組**錯的**預設值（`② … 預設 23:30`，而 param 實際是 `21:30`），同段又寫「預設值＝本機現行實況」——與 param 區塊自己花 10 行解釋的「之所以**不**把兩個預設都設成現況」直接互相打臉。方向仍是危險側：讀 help 的人以為不帶參數跑不會動 smoke，實際會把它從 23:30 搬到 21:30。**「靜默改掉時間」這個陷阱沒被消滅，只是從程式碼搬進了說明文字** | P1 | `tools/install_windows_nightly.ps1` help 區塊 ＋ `tools/tests/test_install_windows_nightly.py` 新鎖 | **fixed@R73** — help 區塊改為**零時刻字面值**（預設值只有 param 區塊一個權威源，現行排程只有 `Get-ScheduledTaskInfo` 一個權威源），並補鎖 `test_help_block_contains_no_hardcoded_clock_time`：判準不是「說明要正確」（無法機械判定）而是「說明裡不准有 HH:mm」。**該鎖當場抓到 6 個殘留**，其中數筆是我自己的訂正註記在逐字引述時刻——與 `DEF-101-777` 抓到的形態完全相同（訂正註記引述假話＝製造新的假話）。25 passed |
| DEF-101-784 | 2026-08-04 | R73 四方二審（QA blocking ⑤／Architect B3 獨立命中） | **DEF-101-776 補了守門卻沒補鎖，而同輪的 DEF-101-773 結案語才剛寫下「已知缺口不得只以劃界結案（DEF-101-757）」——同輪自我違反**。實測本鎖之前全庫 `*test*.py` 對 `ENGINE-MISMATCH` **零命中**。同一支檔案上早有先例明文反對這件事：`tools/tests/test_smoke_ci_sync.py::TestMsystemGuard` 逐字寫「守門本身若沒有鎖，刪掉它全套照綠——那就與註解同級，主張自我否定」。而這個守門特別需要鎖：它被刪掉時**不會有任何紅燈**（本機照跑、CI 不執行這支腳本），直到某天有人在 mac/CI 上炸掉 | P1 | `tools/tests/test_smoke_ci_sync.py`（比照既有 TestMsystemGuard 形態） | **fixed@R73** — 補兩條鎖：① `test_engine_mismatch_guard_present_and_before_any_work`（守門存在 ＋ `exit 1` ＋ 位置早於 `[1/9]`；切窗口用**行首錨定**，因為該檔 WHY 註解裡逐字引述了 CI 側同一個判準，`text.index` 會命中註解——我第一版就是這樣寫的，實測誤判）；② `test_engine_assertion_exists_on_both_sides` 跨檔字面鎖（本機與 CI 兩側斷言必須並存，否則退回單側防護而另一側靜默降級）。33 passed |
| DEF-101-782 | 2026-08-04 | R73 四方二審（Architect N3 提出、SD 以 `-WhatIf` 實測坐實） | **參數化把一條不變量從「由構造保證」降級成「只有預設值遵守」**。「smoke 早於 nightly」在 DEF-101-779 之前是由寫死的字面值保證的；改成參數後，它只剩一條 python 靜態鎖在看**param 預設值**，真實安裝路徑（使用者顯式傳參）無人看管——SD 實測 `-WhatIf -SmokeAt 23:30 -NightlyAt 22:30` → **rc=0、零警告**（兩引擎皆同）。更糟的是該檔自己有兩處在**建議** `-SmokeAt 23:30`＝直接違反它 | P1 | `tools/install_windows_nightly.ps1` runtime 守門 ＋ `tools/tests/test_install_windows_nightly.py` 新鎖 | **fixed@R73** — 加 runtime 守門（`$SmokeAt -ge $NightlyAt` 即 exit 1）＋**顯式**旁路 `-AllowSmokeAfterNightly`（要違反可以，但必須說出口）。靜態鎖看預設值、runtime 看實際生效值，兩者合起來才涵蓋「預設」與「顯式傳參」兩條路。判準刻意用字串比較而非 `ParseExact`：`HH:mm` 零填補後字典序即時序，省掉一個受 culture 影響的 API。補鎖 `test_smoke_after_nightly_has_a_runtime_guard` |
