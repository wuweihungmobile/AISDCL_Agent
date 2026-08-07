# AutoSDD Defect Log — Archive 62

> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 **6 筆已結列**。
>
> **搬遷判準的權威來源是 `tools/archive_defect_log.py`**（程式即判準，本標頭不重述細則）。
> 該工具落實 6 項搬遷判準（①狀態欄分類已結（fixed／wontfix／closed-by-decision）／②狀態欄無活躍字樣（open／routed／deferred／watch／workaround，ASCII 邊界非子字串；程式碼片段、角引號引述、與「訂正首詞（原文…接於後）：」之後到下一個 `｜` 為止的舊狀態引文內的字樣皆不算，R68 收窄／R76 補第三種）／③被 crossref 掃描目標宣稱過狀態者可搬，但搬後該宣稱必須仍解析得到（帳本家族＝主檔 ∪ archive；由 --check 判準(8) 實跑驗證，R68 改寫）／④散文帶交棒字樣者需 `--ack-handoff` 具名承認／⑤該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）／⑥無外部居所指針宣稱本列現居主檔（指針反向依賴，DEF-101-612；有則硬擋，須先訂正該指針，不接受 --ack 繞過）），
> 並在落地後以 `--check` 稽核 8 項保全判準：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針：稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致、(5)歸檔索引涵蓋性：磁碟上每支 archive 都要在歸檔索引檔有一條以它為主體的 bullet（雙向）、(6)非「立帳見」方言的居所宣稱：`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID、(7)表格列欄數：每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免、(8)跨檔宣稱可解析：掃描目標的每一句狀態宣稱都要能在帳本家族（主檔 ∪ archive）解析到，且狀態一致（判準③ 改寫後的事後條件，R68）
> （本段由該檔的 `MOVE_CRITERIA`／`CHECK_CRITERIA` 常數機械生成，逐項定義見
> `check()` docstring；**勿手改**——手寫版曾與實作脫節而被複製成永久史料）。
> **歷輪標頭曾宣稱有這樣一支腳本但 repo 內無載具**，
> 且散文所載判準與實際執行的判準不一致——R60 起改為引用可重跑的工具，見該檔 docstring。
>
> **搬遷清單**：`DEF-101-879`、`DEF-101-881`、`DEF-101-884`、`DEF-101-882`、`DEF-101-883`、`DEF-101-885`
>
> **判準全過但以 `--only`／`--keep` 具名排除、刻意留在主檔者**（DEF-101-811；排除留痕，非無聲少搬）：`DEF-101-890`
>
> **本次操作備註**：R79 清債包：搬 R78 四方複審已結列 6 筆換回主檔體積餘裕；本輪新立列 DEF-101-890 以 --keep 留主檔（帳本標頭政策：活躍列與本輪新立列一律留主檔）
>
> 餘裕一律以 `python tools/check_defect_log_crossref.py` 的實跑訊號為權威，
> 本標頭**不對餘裕做定性宣稱**（R59 SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被推翻）。
>
> **原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。查詢缺陷現況一律先看主檔缺陷總表。

## 缺陷總表（已結列，逐字保全）

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|---|---|---|---|---|---|---|
| DEF-101-879 | 2026-08-07 | R78 四方複審（SA-01／SD-01／SD-02／QA-01，三方獨立命中同一支檔） | **R77 旗艦守衛 `lint_powershell_command.py` 既漏又吵**：12 個 PowerShell 內建別名全數放行而全名版全數擋下（`select -First 5` 逃逸）；三條規則各有一步繞過（真子行程重跑得 9 個逃逸）；反向誤擋安全形態（`"rc=$LASTEXITCODE" ｜ Out-File` 先展開再進管線）；字串字面與 here-string 內的違規三條規則全誤擋 | P1 | 邊界統一為 `_CMD_START`、rc 污染改跨語句延續、比對改看**位置**先後、新增 `mask_regions()` 結構面與展開面雙面遮蔽 | fixed@R78：修後端到端 63 案 FAILURES=0；回歸鎖由「只測會過的寫法」改為漏擋與誤擋雙向逐一注入；9 道判準各附「改壞→紅→還原→綠」注入證明。詳見 `CrossPlatform_R78_Review.md` |
| DEF-101-881 | 2026-08-07 | R78 四方複審（ARCH-01～04／SD-07／SA-06） | **幽靈符號 `_FROZEN_GUARD_FILE_COUNT`：全庫零定義、十餘處引用**，其中 `check_loc_budget.py` 拿它當「整層護欄碼免受 LOC 分級管轄」的正當性依據；棘輪紅燈訊息教人跑的 `--print-guard-lines` 不存在（rc=2）；`guard_baseline_gaps()` 亦不存在；重釘零成本故該棘輪落地的同一 commit 吸收數千行而全綠 | P1 | 實作 `--print-guard-lines` 與 `guard_baseline_gaps()`；新增 append-only `_GUARD_LINES_REPIN_LOG`（不寫理由即紅、淨額結構上不可缺席）；引用逐處改述正確語意 | fixed@R78：**具名機械物鎖射程由「反引號路徑」擴到「反引號 Python 識別字」**——那正是逃逸的縫。7 道注入證明。🔴 另誠實登記 32 筆 grandfathered 幽靈名，見 `DEF-101-888` |
| DEF-101-884 | 2026-08-07 | R78 掌舵者第 2 與第 3 點（連續多輪要求，此前零機械物） | **session context 與 token 耗盡皆無觀測者**：repo 內既有的 SDD `context_ledger` 量的是 Stage 的**估算式**預算（只看 tool_input，看不到工具輸出／子代理回傳／對話本身）且在非 SDD session 休眠；根 CLAUDE.md 的暫停重啟 SOP 是純人工程序 | P2 | 新增 `context_budget_guard.py`（PostToolUse，讀逐字稿 `message.usage` 的**實測**佔用）＋ `session_resume_planner.py` | fixed@R78：三段水位（靜默／提示／exit 2 強制指引並產出可重啟點任務書骨架）；window 走「曾觀測超過下界」的可證推論並標明推斷或指定；同門檻每 session 只喊一次。與 SDD ledger 分工寫在註冊面 `_comment` |
| DEF-101-882 | 2026-08-07 | R78 四方複審（ARCH-05／QA-02／SD-05／SA-04／SA-05） | **文件宣稱與磁碟不符五筆**：M5 攔截率三處記載全停在修復前；R77 自陳的 pytest 基線至少一組實測不符且三組同住一支無人守的註解；`baseline_origin.py` 同檔相隔兩百餘行自我矛盾；交棒書把「動工前狀態」寫成「交棒時狀態」兩筆。**根因＝成熟度 SSOT 寄生在輪次專屬的掃描發現文件裡，零新鮮度守衛** | P1 | 量測值一律改為指向載具；建立輪次中立 SSOT `CrossPlatform_Maturity_Criteria.md` | fixed@R78：新增攔截率新鮮度鎖與交棒書宣稱可查性鎖（體例＝凡述及「尚未做」須附現查指令）；6 道注入證明。舊處保留原文並加指標，不刪歷史 |
| DEF-101-883 | 2026-08-07 | R78 四方複審 QA 突變測試 M4 ＋ 舵手獨立實證（ARCH-06 併入） | **PostToolUse 註冊面完全無人守**：把根 settings.json 的 matcher 由 `Write` 加 `Edit` 縮成 `Write`（＝兩支 hook 對 Edit 整支失效）→ 全套閘門 rc=0 全綠。Grep 實測：整個 `tools/tests/` 零檔提到 PostToolUse。⇒ 比「鎖沒鑑別力」深一層——**鎖可以被無聲拆掉** | P1 | 新增 `TestHookRegistrationScopeIsShrinkOnly`（matcher 只准擴大、條目移除即紅）；hook 路徑去重納管面由寫死名單改為目錄列舉減具名排除表 | fixed@R78：三向注入證明（縮小紅／擴大綠／移除紅）＋還原後雜湊等於 HEAD。🔴 它上線後第一件事就是攔下舵手自己的 wiring |
| DEF-101-885 | 2026-08-07 | R78 掌舵者第 6 點（act 與 Docker 本機全驗） | **act 通道結構上跑不完**：預設映像無 pwsh，`root-infra` 真跑第 3 步即 rc=127（R77 只能宣稱「可解析」）。連帶 `run_act.ps1` 缺 `--workflow`／`--event`，Windows 側只剩環境變數一條路而兩支專職對等檢查器全綠看不見 | P2 | 自建薄映像（pwsh 與 gh 版本自 `actions/runner-images` 逐字實查）；`.actrc` 改指；補兩支旗標並同 commit 重釘薄殼 hash | fixed@R78：`root-infra` 由第 3 步推進到第 11 步（多驗 7 步），停在別包在途的 lint 債且已修。新增 `--verify-all` 一鍵入口與不入庫的實跑帳本；旗標對等改為**現查核心 parser** 而非抄清單 |
