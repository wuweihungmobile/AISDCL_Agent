# AutoSDD Defect Log — Archive 66

> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 **10 筆已結列**。
>
> **搬遷判準的權威來源是 `tools/archive_defect_log.py`**（程式即判準，本標頭不重述細則）。
> 該工具落實 6 項搬遷判準（①狀態欄分類已結（fixed／wontfix／closed-by-decision）／②狀態欄無活躍字樣（open／routed／deferred／watch／workaround，ASCII 邊界非子字串；程式碼片段、角引號引述、與「訂正首詞（原文…接於後）：」之後到下一個 `｜` 為止的舊狀態引文內的字樣皆不算，R68 收窄／R76 補第三種）／③被 crossref 掃描目標宣稱過狀態者可搬，但搬後該宣稱必須仍解析得到（帳本家族＝主檔 ∪ archive；由 --check 判準(8) 實跑驗證，R68 改寫）／④散文帶交棒字樣者需 `--ack-handoff` 具名承認／⑤該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）／⑥無外部居所指針宣稱本列現居主檔（指針反向依賴，DEF-101-612；有則硬擋，須先訂正該指針，不接受 --ack 繞過）），
> 並在落地後以 `--check` 稽核 8 項保全判準：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針：稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致、(5)歸檔索引涵蓋性：磁碟上每支 archive 都要在歸檔索引檔有一條以它為主體的 bullet（雙向）、(6)非「立帳見」方言的居所宣稱：`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID、(7)表格列欄數：每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免、(8)跨檔宣稱可解析：掃描目標的每一句狀態宣稱都要能在帳本家族（主檔 ∪ archive）解析到，且狀態一致（判準③ 改寫後的事後條件，R68）
> （本段由該檔的 `MOVE_CRITERIA`／`CHECK_CRITERIA` 常數機械生成，逐項定義見
> `check()` docstring；**勿手改**——手寫版曾與實作脫節而被複製成永久史料）。
> **歷輪標頭曾宣稱有這樣一支腳本但 repo 內無載具**，
> 且散文所載判準與實際執行的判準不一致——R60 起改為引用可重跑的工具，見該檔 docstring。
>
> **搬遷清單**：`DEF-101-848`、`DEF-200-040`、`DEF-101-959`、`DEF-101-995`、`DEF-101-022`、`DEF-101-333`、`DEF-101-979`、`DEF-101-335`、`DEF-101-923`、`DEF-101-946`
>
> **判準全過但以 `--only`／`--keep` 具名排除、刻意留在主檔者**（DEF-101-811；排除留痕，非無聲少搬）：`DEF-200-046`
>
> **本次操作備註**：R84 收斂（C5 帳本包）：只搬 ≤700 bytes 的已結列，刻意不動任何 OVERSIZE_ROW_GRANDFATHERED 成員 —— 搬走超長列會讓豁免當場過期並要求下修 defect_ledger_index.py 的兩個天花板，而該檔非本包持有面（見 DEF-200-049）。本次目的是替 R84 全輪帳本列騰出 bytes 餘裕。
>
> 餘裕一律以 `python tools/check_defect_log_crossref.py` 的實跑訊號為權威，
> 本標頭**不對餘裕做定性宣稱**（R59 SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被推翻）。
>
> **原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。查詢缺陷現況一律先看主檔缺陷總表。

## 缺陷總表（已結列，逐字保全）

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|---|---|---|---|---|---|---|
| DEF-101-848 | 2026-08-05 | R76 Scan-G＋Scan-H（PKG-F） | `docs/06_quality/CrossPlatform_Scan_Dimensions.md:303` 硬規則② 的「已實測不涵蓋」仍列**否定語意**，而 R74 起 `_REASSIGN_NEGATED_RE` 已涵蓋它；釘住該句的判準綁**字面 token** ⇒ 照規矩訂正文件反而讓根層閘門轉紅（與該檔自訂的「被涵蓋時翻紅」相反）＝有鎖在守假話 | P1 | 文件改為現況 ＋ 落**行為綁定**判準 | fixed@R76 ｜與 `orphan_backlog_problems()` docstring 對齊；機械物 `TestR76UncoveredFormListTracksActualBehaviour`（探針說未涵蓋就必須列、說已涵蓋就必須不列）；注入：該項寫回清單即紅，還原即綠 |
| DEF-200-040 | 2026-08-10 | R83 收斂：三方（SD FC-2／QA F-8／SA-09）證偽落列者自陳 | 落列者 `not_done` 稱「11 列承接 R83，R84 首列落地就全變孤兒」——**實測只有 3 列**：本回合逐輪模擬（帳本未動）`round=84 → 3 筆`＝DEF-101-992、DEF-101-995、DEF-101-998；另 8 列（938／947／950／951／960／974／978／991）帶「R82 改派」⇒ `_reassign_hit()=True`，`round=90／200` 一筆不增（見 `DEF-200-041`） | P2 | 本列即跨列改派回執（體例照 `DEF-200-016`） | closed-by-decision（改派）：上述三列承接輪次改派 **R84**（R83 零交付；前兩列距 700 上限僅剩 4／2 bytes）。原列零增長 |
| DEF-101-959 | 2026-08-08 | R80 收尾（帳本輪號前進到 R80 顯形） | `TestOrphanBacklogAgainstTheRealLedger` 的比例判準（narrow×5 < naive）隨輪號前進**結構性腐化**：實測 naive=66／narrow=20（需 ≤13）。根因＝測試側 narrow 只重寫生產規則的**一半**（漏掉「已改派即放行」兩出口）⇒ 合法改派的歷史列只增不減 | P2 | 舵手裁決②：narrow 改呼叫生產判準；naive 稻草人維持測試內獨立（同源＝恆真式） | fixed@R80：narrow 20→0、naive 66 不變；雙向注入實證（退化整列→紅、拿掉改派出口→紅、還原→綠）。WHY 見該 docstring；零門檻、鎖檔行數不變 |
| DEF-101-995 | 2026-08-09 | R82 收尾（文件面）複驗帳本對抗稽核 | tools/lib/ledger_rotation.py:35 逐字訂下「歷史不得回填、不得改寫」，而 ratchet_history_problems() 對這條紀律零觀測者：它只判相鄰段不上升＋末元素等於現值 ⇒「改寫末元素往上釘」與「把史料截成單一高值」兩形態皆回 0 problems。當回合三組對照：append-up 紅、REWRITE-last 綠、truncate(999,) 綠 | P2 | 判準須能分辨追加與改寫：已釘過的前綴要不可變（單調且只准延長的前綴斷言）；程式面不在文件包射程 | fixed@R84（三形態複驗全紅）｜CrossPlatform_R82_Scan_Findings.md §F |
| DEF-101-022 | 2026-07-10 | 跨平台修復輪四方複審第三輪（known-gap 盤點，DEF-101-007 殘餘） | **`closure_evidence._run_git` 自身繼承呼叫端 env**：v0.30 `closure_evidence.py:89` `_run_git` 未自清 GIT_DIR/GIT_WORK_TREE——屬 read-only git 查詢（rev-parse 類），實害受限；現行防線為 hook 層 `env -u` 清洗 | P3 | 縱深防禦（函式內自清 env）留待後續輪；known-gap 記入根層 `ONBOARDING.md` §9 | closed-by-decision@R80（包 C：read-only 查詢、實害受限，已知傳染路徑由 hook 層 `env -u` 阻斷 ⇒ 決定接受。詳見 CrossPlatform_R80_Scan_Findings.md §C） |
| DEF-101-333 | 2026-07-24 | R40 二審 Architect／QA 各自獨立構造（新角度攻擊） | 殘留兩類向量：死碼 dot-source（#4）與 here-string 誘餌（#5）；原文逐字保全於 CrossPlatform_R82_Ledger_Closure.md §8.5 | P3（已知方法論邊界，已在測試 docstring 誠實記載） | 徹底封閉需真 PowerShell AST 層解析，屬方法論升級非缺陷修復 | closed-by-decision@R82：依 DEF-101-400 決策準則歸檔（本列的解鎖條件與 400 的觸發條件是同一件事）；當回合實查 tools/tests/ 內 Automation.Language.Parser 命中 0 支 guard 測試 ⇒ 前提未變 |
| DEF-101-979 | 2026-08-08 | R81 開場（時鐘前進使硬規則② 顯形） | 時鐘推進到 R81 的同一刻，7 列指向 R80 而 R80 未交出的承接指派一起成為孤兒（crossref rc=1）：DEF-101-796、DEF-101-912、DEF-101-917、DEF-101-918、DEF-101-919、DEF-101-925、DEF-101-926 | P3 | 走硬規則② 的跨列出口而非就地改寫：DEF-101-796 在 `OVERSIZE_ROW_GRANDFATHERED` 內，任何增長都會撐大零容忍的超標總量棘輪 | closed-by-decision（改派）：上列 7 筆承接者一律改派 **R81**；歷史原文逐字保全、原列零位元組增長 |
| DEF-101-335 | 2026-07-24 | R40 一審 SD 對抗式驗證（新呼叫點碰撞，同 DEF-101-324 類別） | hub_sync.diff() 與 counterfactual_replay.write_report() 兩個新 SSOT 呼叫點同樣命中多對一碰撞；原文逐字保全於 CrossPlatform_R82_Ledger_Closure.md §8.6 | P3（四方一致判定非阻擋） | 併入 DEF-101-324 既有 backlog 追蹤，不需獨立修復 | closed-by-decision@R82：狀態字對齊該列自己的分流去向（逐字「不需獨立修復」）；範圍擴大的事實已回寫 DEF-101-324 狀態欄 |
| DEF-101-923 | 2026-08-07 | R79 ARCH 包（架構減法） | `check_script_parity.py` 用來支撐「這段不可刪」的事實宣稱失實：原文寫兩支 compat-CI 只跑本檔，實測兩支皆有 `run_root_unittests` step ⇒ 下一輪依它做架構決定就是拿失實前提推理 | P3 | 就地訂正並補寫原文沒寫的真缺口，新增 `TestLatestThinnessRationaleIsFactual` 把 4 個世界事實機械釘住 | fixed@R79：注入 4 形態全紅，證據見 `CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-923` 節 |
| DEF-101-946 | 2026-08-08 | R80 包 C S5-06/07 | WindowsApps bash 行為電池 5 案中 4 案被 11 列行為表嚴格覆蓋（`_VERDICT_CASES` 同檔餵四份實作、逐列比對，誘餌樣本連目錄名都逐字相同） | P3 | 刪 4 案、保留唯一無承接者的「候選不存在」案；四份實作不合併（語言邊界） | fixed@R80：詳見 CrossPlatform_R80_Subtraction_Evidence.md S5-07 節 |
