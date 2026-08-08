# AutoSDD_improving_105 — R81 跨平台輪（Windows 11 真機）

> 軌道① 整合迭代第 105 份；本輪同時是**跨平台複審輪 R81**（輪號權威源＝
> `tools/check_defect_log_crossref.py::current_round()` 讀帳本「發現情境」欄，收輪前現查）。
>
> 🔴 **體例（沿用 R79／R80 並再加嚴一條）**：凡述及「已通過／已達標／尚未做／已推送」這類狀態，
> 一律附**現查指令**，不寫快照結論。凡述及「某類危害沒有機械物在守」，
> 必須同時指出該宣稱是由哪一支判準在守——否則那句話自己就是下一輪的假事實。
> **本輪再加嚴**：本檔內每一個數字都要標明它是**誰量的**（本輪本包實測／他包回報／史料快照）。
> 理由是 R80 二審實測的最大缺陷桶就是「宣稱先於查證」，而混用三種來源的數字正是它的溫床。
>
> 記號約定：`$r`＝repo 根，`$p`＝`$r\.venv\Scripts\python.exe`。

---

## §0 本輪定位與唯一驅動器

三柱對齊（根 `CLAUDE.md`〈三條改進軌道〉）：本輪主體同 R80，落在 **B 柱（手腳 AISDLC_SDD）＋
C 柱（指揮官 AutoClaude）的跨平台基礎設施**；A 柱（雙向協作橋接）本輪暫不動。
唯一驅動器＝`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`，本檔即該範本的第 105 份實例。

**開場已完成的前置**（每列標明量測來源）：

| 前置 | 實測 | 量測來源 |
|---|---|---|
| 缺陷帳本體積洩壓 | `archive_defect_log.py --apply --archive-num 64` → **35 筆／26,997 bytes** 搬出；主檔 254,778 → 231,742 | 筆數與 archive 位元組＝**本包當回合實測**（`AutoSDD_Defect_Log_archive_64.md`）；主檔前後兩個數字＝**舵手開場回報**，本包未複驗（歸檔已發生，前值結構上無法回測） |
| 主檔體積現況 | **233,698 bytes**（歸檔後又長了本輪帳本列）；fail 線 262,144 | **本包當回合實測** |
| 未結列水位 | 開場 **87** → 本包寫入三列後現查 **88**；warn 86／fail 98 | 87＝舵手開場回報；88＝**本包當回合實測**。唯一量測入口＝`& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count`（歸檔**不會**降低此數，工具自己每次都印這句） |
| 歸檔造成豁免清單過期 | `DEF-01-007`／`DEF-101-274`／`DEF-101-422` 隨 archive_64 離開主檔 ⇒ 三筆 `OVERSIZE_ROW_GRANDFATHERED` 當場過期、判準轉紅 | 現象＝舵手開場回報；**本包複驗**：三筆皆已不在該常數內、且皆在 archive_64 中，另一包已同步下修三個常數 ⇒ **今日為綠**。🔴 這是判準**正確運作**，不是缺陷；缺陷是「歸檔器自己不提示」，已立 `DEF-101-977` |
| 當前輪時鐘 | `current_round()` 由 R80 推進到 **R81** | **本包當回合實測**（本輪帳本第一列落地即前進；fail-open 窗口同時關閉，連帶讓 7 列指向 R80 的孤兒承接顯形，處置見 `DEF-101-979`） |
| 帳本閘門 | `& $p "$r\tools\check_defect_log_crossref.py"` → **rc=0** | **本包當回合實測**（含硬規則②、狀態首詞、欄數、逐列位元組、體積五道） |

---

## §1 本輪要回答的題目（舵手原始訴求逐條，不得漏答）

> 🔴 **結論欄本輪刻意留空**——它只能在收輪的**單人窗口**填，且每一格都要附當回合真跑的輸出。
> R80 的教訓：多 agent 並行期間任何「全套閘門 rc=0」的宣稱都不成立。
> Q1~Q6／S1~S3 自 R80 承接（`docs/04_planning/AutoSDD_improving_104.md` §1 為前一輪結論），
> a／b／P7 為 R80 掌舵者新提且**未交付或未交付完**者。

| 編號 | 訴求 | 驗收判準（機械可查者優先） | 結論 |
|---|---|---|---|
| **Q1** | Mac／Win 11 部署執行與開發零相容缺陷 | 鐵律三對照表的**分子**（有機械物的列數）上升、**分母**（已登記危害類數）亦上升；每一格「無機械物」都必須指出是**哪一支判準**在守那句話。🔴 R80 已證此判準只量得到「有沒有人在守」，量不到「零缺陷」——本輪若仍只交出判準面的綠，結論一律寫「Windows 側今日無已知未修相容缺陷；mac 側未量」 | **Windows 側今日無已知未修相容缺陷；mac 側未量**（判準逐字指定的措辭）。鐵律三對照表 **分子 18／分母 20**（本包當回合實測：以 Python 逐列剖析 `CLAUDE.md` 該表；棘輪 `& $p -m unittest tools.tests.test_doc_loc_baseline_freshness_r60.TestR74IronLawMechanismAccounting` → **rc=0**）。兩格仍無機械物者＝`shell=True` 的原生殼差異、副檔名判斷，本輪皆只登記診斷未建鎖。🔴 mac 真機本輪**零覆蓋**（見 `R81_HANDOFF.md` §3.4）⇒ 本列**不得**讀成「兩平台零缺陷」 |
| **Q2** | 架構簡潔－分工清楚－不重複模組；**拿掉不合理機制** | 本輪必須是**淨減法輪**：護欄層 raw-line 淨額 ≤ 0；否則走款(9)`[未附刪除清單]` 的登記手續（`[非淨減法輪]` ＋ 指名一份具名 `.md` 當逐檔清單的家），而走 ② 的輪次 Q2 一律判**未達成**。🔴 R80 未達成且重釘三次（累積 +2334），本輪的第一個問題是「上一輪那 2334 行有沒有可以拆掉的」 | **未達成**（依 §4 第一條，走款(9) 者一律如此判——登記不是及格線）。🔴 **本格刻意不複寫累積淨額那個數字**：它的唯一的家是 §3 末的 `guard-total` 那一行（受 `doc_guard_total_problems()` 對帳），在這裡再寫一份就是下一個 stale 站點。可現查者＝`& $p "$r\tools\tests\test_adr_xplat001_c1c2_lock.py" --print-guard-lines`（本包當回合 **rc=0**）。判定依據：本輪走的是款(9) 的登記手續（`[非淨減法輪]`），成長全在護欄層，逐檔清單的家＝`CrossPlatform_R81_Scan_Findings.md` §B。生產碼側為淨減（hook payload 手抄本 −39 行），**不改變判定** |
| **Q3** | Mac 開發時 Win 不落差、反之亦然 | 落差面收斂到單一 SSOT；`.ps1`／`.sh` 對等性由**行為**而非**存在性**判定。🔴 R80 的後半（行為等價）零機械物，判準本身由 `& $p "$r\tools\check_script_parity.py"` 印出的鎖清單界定其真實涵蓋範圍——本輪要讓那份清單涵蓋「可觀察介面」而非只有存在性與位元組釘選 | **部分達成**。`& $p "$r\tools\check_script_parity.py"` → **rc=0**（本包當回合實測），十一道全綠；其中「介面對等鎖：**3 對**雙原生腳本的退出碼／外部執行檔／git 子指令三面與凍結基準逐筆相符（登記在案的既有分歧 2 筆）」即 R80 缺席的**行為面**判準，本輪首次有數字。**誠實劃界**：該清單主體仍是存在性、tier 分類與 hash 釘選（13 對 + 17 支單邊納管），行為等價只覆蓋 3 對 ⇒ 距「涵蓋可觀察介面」還遠，判部分 |
| **Q4** | Windows 常犯低級錯誤的根因徹底解決 | ①**先驗證量測器符號**（`& $p "$r\tools\probe\audit_session.py" --selftest`），符號未翻正前的歸因一律不採信；②重跑 `& $p "$r\tools\probe\misstep_attribution.py"`，**報絕對筆數不報百分比**（分群是關鍵詞啟發式，量級穩健、小數不穩健）；③最大桶必須有機械物在守——R80 判定最大桶＝**宣稱先於查證**且當時零機械物，本輪的達成判準就是這一桶的機械物覆蓋是否真的建立 | **部分達成**。①**符號先驗**：`& $p "$r\tools\probe\audit_session.py" --selftest` → **rc=0**，新判準判錯 **0／10**、舊判準判錯 **6／10** ⇒ 符號已翻正，本輪歸因可採信。②`& $p "$r\tools\probe\misstep_attribution.py"` → n=1219（ledger 1103 + transcript 116），**絕對筆數**：CLAIM-FIRST **202**、LOCKBLIND **175**、BADPIPE **119**、CARRIER **113**、OTHER 610（已歸類 609）。最大桶仍是**宣稱先於查證**，與 R80 同。③該桶本輪落地**第一個**通用機械物 `TestR81GhostPathClaims`（本包重跑 **rc=0，13 tests OK**），並於本輪擴到軌道① 驅動器那一面（QA 一審 blocking）。🔴 **它只覆蓋「治理活文件裡以反引號寫出的 repo 路徑」這一角**，不宣稱涵蓋整桶 ⇒ 判部分而非達成 |
| **Q5** | 各專家挖深＋Developer 清技術債 | 未結列**真降**（非搬帳）：**新增列數 < 結案列數**；(A) 類「其實已修好只差狀態欄」逐筆附實查。🔴 現查入口＝`--unresolved-count`；開場即已越過 warn 線 86，距 fail 線 98 為個位數 ⇒ 本輪**不得只增不結** | **達成（方向對，水位仍高）**。`& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count`：開場 87 → 本包收輪當回合 **84**（**rc=0**）；全套 `check_defect_log_crossref.py` 亦 **rc=0**。本輪新增帳本列 **9** 筆（本包當回合以「發現情境」欄定位實測，跨主檔＋全部 archive）⇒ 結案列數大於新增列數，判準「新增列數 < 結案列數」成立。🔴 但距 warn 線 86 只剩 **2** 筆、距 fail 98 剩 14 筆 ⇒ **R82 的第一動作必須是先結列**（見 `R81_HANDOFF.md` §0 第 1 項）；歸檔不降此數 |
| **Q6** | 成熟度 M1~M6 | 逐條實測，附量測載具與當輪 rc；判準 SSOT＝`docs/06_quality/CrossPlatform_Maturity_Criteria.md`（門檻＝六條全達標且連續三輪，其中至少一輪是「別人來查」）。R80 為 0/6 | **0／6，與 R80 相同**。六條**逐條當回合實跑**，量測載具、rc 與「距門檻多遠」見下方 **§1.1**（本包當回合實測，非引用）。🔴 本輪把量尺補全（M2 的分母首次以欄位定位算出、M6 的兩棵樹首次同輪各跑一次 census）**不算進度**——量出來的數字一格都沒動 |
| **S1** | context 不超 90%、不要爆 | 🔴 要分清「出聲」與「**真的做到**」：90% 那道要能讓壓縮**實際發生**，不能只印字給模型看。R80 實測 0/70 session 到過 90%、3 次壓縮全是人手打的 ⇒ 該門檻連被觸發的機會都沒有。本輪判準：門檻必須落在**構得到**的水位，且動作要可稽核 | **未達成；且本包不代並行包判定實作面**（`.claude/hooks/context_budget_guard.py` 由額度軸那一包持有，本包依約不碰）。本包當回合可現查者：`& $p "$r\tools\session_resume_planner.py" --check` → **rc=0**，本 session 實測 `used 445,071／window 1,000,000／水位 44.5% → 低於 75%`。⇒ **context 軸的 75／90 兩道本輪一次都沒被觸發**，R80 判定的「0/70 session 到過 90%」這個結構問題在 context 軸上**未變**。真正的修法走的是**另一條分母**（額度軸 80／95，ADR-XPLAT-005），其實作面的 rc 以並行包交件為準 |
| **S2** | Token 用盡→下輪 reset 喚起續跑 | 憑證＝`NextRunTime` 這個**值**（不是 rc——`Get-ScheduledTask` 對不存在的工作回 rc=0）；「沒觸發」必須可偵測。🔴 R80 驗屍結論：前四段（偵測／觀測／重排／探測）成立，**第五段續跑的觸發條件設計錯了**——協定救的單位是 session，而四次撞線死的都是**扇出**，主迴圈一次都沒死。本輪判準：可續跑的工作單位要降到 workflow run，且預設動作是 **throttle** 不是 resume | **半自動**：偵測／觀測／重排／探測**四段成立**，**跨 session 扇出重派無機械路徑**，需人或 AutoClaude 重派新 run。依據＝`ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md` **§8-5**（`resumeFromRunId` 是 same-session only ⇒ 續跑鏈今天在跨 session 那一段是斷的；死者清單是**給人讀的交棒單**，不是可直接回放的 handle）與 **§8-4**（token refresh 完全沒跑過 ⇒ 無人看管過夜這條路今天是斷的）。🔴 判準兩半分開判：「可續跑單位降到 workflow run」＝**設計已落地、機械路徑未落地**；「預設動作是 throttle 不是 resume」＝已成為該 ADR 的地基（§1.2 驗屍結論）。**不得**把本列寫成「自動 resume 已經做到了」 |
| **S3** | pytest skipped 徹底解決、全部可測 | 逐筆 skip 分五類；(a) 環境未啟用類**歸零**；孤兒測試（兩平台皆不跑）列出並處置。量測入口沿用既有兩個、**刻意不另建第三個**：根層＝`& $p "$r\tools\run_root_unittests.py"` 印 `[skip census]`；AutoClaude 樹＝`& $p "$r\AutoClaude\tools\local_ci_gate.py" --census-only <pytest log>` | **未達成，且三個剖面方向不一致——刻意不只報好看的那一個**。①**根層** `tools/tests@win32`：**43 → 41**（−2；`platform=40／tool-absence=0／env-disabled=1／structural-pair=0／debt=0／untagged=0／欠債型 1`）。本包當回合實測 `& $p "$r\tools\run_root_unittests.py"`，該次 **rc=1**（`Ran 2581 tests`／`failures=8, skipped=41`），8 筆 failure **全屬並行包過渡態**（掃描面下限帶因 `tools/lib` 新增 4 支檔而由 10 撐到 21），逐筆歸因見 `CrossPlatform_R81_Review.md` §4。🔴 **env-disabled 仍為 1**，未歸零 ⇒ 判準 (a)「環境未啟用類歸零」**未達成**。②**AutoClaude 樹、pg 剖面** `AutoClaude/tests@win32+pg+nested`：**44 → 37**（−7；`platform=17／tool-absence=0／env-disabled=12／structural-pair=1／debt=7／untagged=0`），本包當回合實測 `4222 passed, 37 skipped`（pytest rc=0）、census **rc=0**；`untagged 23 → 0` 是本輪最大單筆改善。③**ONBOARDING §7 表② 的 `AutoClaude pytest tests/ -q` 欄**：**200 → 201**，**skipped 不降反升 +1**——這是本輪**唯一朝訴求反方向動的數字**，而它被寫在一列「基線回填」裡。🔴 ②與③**不衝突，因為是不同剖面**：②是本機 `.venv` ＋ 活的 docker PG（`AutoClaude/tests/conftest.py` 的 PG autodetect 會自動注 DSN，本包已實測**清空全部 PG 環境變數後仍是 37**，故驅動者是 docker 不是 env）；③的指紋錨逐字帶 `pgextras=absent interpreter=venv-clean-r81` ⇒ 那是**乾淨 venv、沒裝 postgres extras** 的剖面，②的 −7 在那裡結構上看不到（那批測試在模組級就被 importorskip 掉）。🔴 **+1 的那一支本包未識別**：重現它要重建 `venv-clean-r81`，本包未做；可確定的只有同一列 passed 亦 +15（4009 → 4024）⇒ 本輪新增的測試裡至少有一支在該剖面 skip。**不得**拿 ②的 −7 去蓋掉 ③的 +1 |
| **a** | 額度水位一律用 **%**，不是固定量（啟動帳號不同 ⇒ 絕對量在兩台機器之間不可比） | 分母的**取數管道**必須是可重跑的程式，且要能說出它取的是哪一種計費口徑。🔴 **單一校準點解不開「口徑」與「分母」兩個未知數**（R80 實測：同一組 usage 依四種口徑各給一個候選分母，四個都能湊出同一個百分比）⇒ 判準要求**多點校準**或權威來源，不得挑一個看起來合理的填進去 | **本包不判定實作面**（`tools/lib/quota_meter.py` 由並行包持有）。本包可現查並確認的結構結論：ADR-XPLAT-005 §2.1 走的是**權威來源**那一條——server 依帳號方案自己算 utilization 並回百分比 ⇒ **本 repo 不再擁有「分母」這個概念**，換帳號／換方案／換機器零常數要改（正是「啟動帳號不同」那句話要的東西）。同節並把**多點校準明文停止**，理由不是「還沒做」而是**等式不成立**（池跨產品共享、訂閱模式完全不走 token 桶、實測 10 分鐘漂 12pp 而本 session usage 解釋不了）⇒ R80 那道「四個候選分母都湊得出同一個百分比」是**偽命題**。取數層一律正規化成 0..100 float，口徑由 server 明文回答。實作面的 rc 與注入自證以並行包交件為準 |
| **b** | **80%** 少派 agent、準備下一次 reset；**95%** 停止、準備喚醒 | 兩道各自的**動作**要真的發生，不是印一行字給模型看：80% 那道要能真的降低併發，95% 那道要能真的收斂並武裝喚醒（`NextRunTime` 為憑證）。R80 零交付、repo 內零載體，帳本載體＝`DEF-101-961` | **本包不判定實作面**（`.claude/hooks/context_budget_guard.py` 由並行包持有）。本包可現查者：ADR-XPLAT-005 §2.4 已把兩道門檻的**動作**寫成機械形態（80 ⇒ `fanout_cap=2`、95 ⇒ `fanout_cap=0` 並 `exit 2`，＝那次工具呼叫不會發生，不是印一行字給模型看），§5 亦列出 M1~M13 逐條機械物；PreToolUse 註冊面本來就已涵蓋扇出工具（matcher 含 `Task`／`Agent`／`Workflow`）。🔴 **本列在 SD 一審那兩筆 blocking 收斂前不得判達成**——「派發帳併發掉行／撕行致誤擋」與「量不到時完全靜默」正好落在這一列的兩個動作上；ADR 自己在 §2.1 落地訂正表與 §8 亦逐字記載仍未落地者（L2 零 reader、`degraded` 閂鎖、載體二整段）|
| **P7** | 哨兵／hook 彈窗 | 掃描面涵蓋**全部**活躍 settings 檔（不只根層那一份）；`SHELL_FORM_CENSUS` 判準為**相等**（多＝退回 shell form、少＝轉好了沒下修基準）。🔴 驗收要正負兩面一起看：exec form 的載具解析不到時 CC **fail-open**（六支守衛靜默失效，而螢幕表徵就是「終於不閃窗了」）⇒「不閃窗」永遠不算通過 | **達成（形態面）**。`AutoClaude/.claude/settings.json` 的 6 條 shell form → **12 條 exec form**；`SHELL_FORM_CENSUS` 本包當回合實測＝`{'.claude/settings.json': 0, 'AutoClaude/.claude/settings.json': 0}`（兩格皆 0，判準為**相等**：多＝退回 shell form、少＝轉好了沒下修基準）。憑證＝於 `tools/tests/` 跑 `& $p -m unittest test_check_hooks_liveness` → **rc=0，129 tests OK**。🔴 **不得用 `tools/check_hooks_liveness.py` 的 rc 當憑證**（QA 一審注入實測：把一條 shell form 注回該 settings，該工具仍回 rc=0，因形態判準不在它射程內）。🔴 **本列刻意不宣稱「不閃窗」**——依 §4 最後一條，那個螢幕表徵與 exec form 載具解析失敗（CC fail-open、六支守衛靜默失效）完全相同 |
| **c** | 「Token 盡量不要用盡，就要停止進行任務，**記錄所有狀態**」（掌舵者逐字，舵手提供） | 「停止」與「記錄所有狀態」兩個動作都要**真的發生**且可稽核：停止＝扇出被機械擋下（`exit 2`，不是印字）；記錄＝可重啟點任務書落磁碟且含四項（已驗證什麼／還沒做什麼／下一步確切指令／禁止事項） | **部分達成（設計完整、實作面由並行包持有）**。ADR-XPLAT-005 §2.4 的 **95% 閂鎖**就是本題的答案：①`exit 2` 擋下所有扇出（`fanout_cap=0`）；②寫可重啟點任務書（既有 `write_resume_plan()`），任務書內含未完成 run 清單；③依額度種類分支。🔴 **未做的那一半照實記**：同 ADR §8-5 逐字——任務書裡的死者清單是**給人讀的交棒單**，不是可直接回放的 handle ⇒ 「記錄所有狀態」今天記得到「哪幾個 run 死了」，記不到「怎麼自動接回去」 |
| **d** | 「Token 若用盡時，下一輪 Reset 時要能**喚起任務繼續執行**」（掌舵者逐字） | 憑證＝`NextRunTime` 這個**值**（不是 rc——`Get-ScheduledTask` 對不存在的工作回 rc=0）；且「喚起之後真的繼續執行」要與「喚起了但什麼都沒做」**可區分** | **未達成（半自動）**。與 S2 是同一件事的兩面：**喚起那一段成立**（SessionStart 預防性武裝 ＋ 900 秒巡邏 ＋ 逐字稿撞線偵測，巡邏零 token）；**繼續執行那一段斷在跨 session**（ADR §8-5：`resumeFromRunId` 是 same-session only，排程器醒來的那一跑按不了它）。另 ADR §8-4：token refresh 完全沒跑過、覆核時 access token 距到期約 3.8 小時 ⇒ **無人看管過夜這條路今天是斷的**。⇒ 今天做得到的只有「有人在的互動 session 照任務書重派」那一列 |
| **e** | 「Claude Code 同 session、同 token 池、單次上限 1 小時，Reset 時間五小時，**要如何度過五小時**（是否可每 50 分鐘喚醒一次）」（掌舵者逐字） | 先驗證「五小時」這個前提本身；「每 50 分鐘」要給採用或不採用的理由，且理由必須是**量出來的**不是推想的 | **已答覆：不採用每 50 分鐘；且前提被推翻**。ADR-XPLAT-005 §2.8：①**沒有「五小時」這回事**——15 個相異撞線 episode 的實際停機 min 0.5 分／median 59.8 分／max 253.2 分（4.2 小時），**超過 5 小時者 0 個**（ADR-XPLAT-004 §2.7 量測，本輪引用未重量，重量入口＝`& $p "$r\tools\probe\reset_window_distribution.py"`）。②不採用的四個理由：50 這個數字是 `ScheduleWakeup` 的 `delaySeconds` clamp 外溢（schtasks 沒有該上限）；它把最壞死等由 15 分放大到 50 分而換不到任何東西（巡邏零 token，這一側沒有需要權衡的量），且 15 個 episode 有 7 個窗 ≤50 分鐘 ⇒ 那 7 個整個沒醒過；`ScheduleWakeup` 每醒一次是一個模型回合（實測約 20.7 萬 tokens）⇒ **斷電期間它自己也會被擋**；有了撞線前就拿得到的權威 `resets_at`，「一直醒來看看好了沒」的理由消失。③**本題的正確答案是「不要走到需要度過五小時」**——在 95% 主動收斂並武裝，把「被動等一個未知長度的窗」換成「主動停手」 |
| **f** | 「搜尋最新前沿 AI Agent 如何設計來參考（如 Claude Code、OpenAI）」（掌舵者逐字） | 只寫從本輪量測**直接推得**的結構結論，不寫二手轉述；做不到就明說做不到 | **部分達成，且 ADR 自己標為「背景不是決策依據」**。ADR-XPLAT-005 §2.10 的唯一結論：業界主流的**指數退避＋抖動在本場景結構上是錯的工具**——那是 per-request 429 的解法（等一下再送就會過），本 repo 面對的是 per-account 週期額度（等 30／60／120 秒都一樣滿，只會把探測預算燒光）；訂閱模式完全不走傳統 token 桶（`anthropic-ratelimit-tokens-remaining` 在 `claude.exe` 內 count=0，走的是 unified utilization 那一族）。⇒ 正確工具組＝**事前節流 ＋ 等一個已知時刻 ＋ 工作單位級 checkpoint 續跑**，其中第三項與 LangGraph 那類同型，前兩項是訂閱制特有、業界通用模式裡沒有的。🔴 **誠實劃界（ADR §8-9 逐字）**：只做了一次概略搜尋，**沒有逐一讀原始碼或官方文件** ⇒ 不足以支撐更細的設計決策 |

> 🔴 **本表列數的訂正（R81 SA 一審 B3）**：掌舵者訴求 6 是 **a~f 六個子項**，而本表原先只把 a、b 拉成獨立列，
> **c／d／e／f 沒有進驗收表、只活在 ADR 裡** ⇒ 收輪時結構上不會被逐條判定（任務書說「13 條」而表只有 12 列，
> 那個計數落差就是這件事的表徵）。四列已於收輪補入，逐字原文由舵手提供、視為權威。
> 同一筆 finding 另指出 `ADR-XPLAT-005` 的 a~f 字母對應有誤——本包逐字母核對後**只有 `c` 是真的錯位**
> （d／e／f 相符），處置與核對表見 `docs/06_quality/CrossPlatform_R81_Review.md` §3。

---

## §1.1 Q6 成熟度 M1〜M6 逐條實測（**本包當回合單人量測**）

> 判準 SSOT＝`docs/06_quality/CrossPlatform_Maturity_Criteria.md`（門檻在〈五個收斂條件〉末段與〈現況總判〉）。
> 體例：**每一條都指出量測載具、附當回合 rc、附「距門檻多遠」**；達不到就寫未達成——
> **留白會被下輪讀成沒問題**。🔴 本節的數字**不得被下一輪當常數引用**，一律照載具欄重跑。

| # | 量測載具（當回合真跑） | rc | 當回合讀數 | 達標？ | 距門檻多遠 |
|---|---|---|---|---|---|
| **M1** | `& $p -m unittest tools.tests.test_adr_xplat001_c1c2_lock`；`& $p "$r\tools\tests\test_adr_xplat001_c1c2_lock.py" --print-guard-lines`；ADR-XPLAT-002 §8.1 回執表現查 | **0**／**0** | `[Scan-H triplet] UEP=5 AC=47 GLC_FILES=57 GLC_LINES=67950`；`淨額 67950→67950 (+0)`；§8.1 仍是**空表**（逐字「尚無回執」）| ❌ | 門檻是**合取**，兩半皆未達：①UEP 半——§8.1 零回執，且無 ADR 正式宣告 5 為終態並凍成 shrink-only；②護欄行數半——本輪總量 65390 → **67950（+2560）**，是**繼續成長**而非「連續三輪不上升」，故該半的計時等於**從本輪重新起算** |
| **M2** | 分子＝四方一審 blocking 中的「失實宣稱」筆數（逐筆分類見 `CrossPlatform_R81_Review.md` §2、§5）；分母＝`& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count` 取當前輪後，數「發現情境」欄提及該輪的列 | **0**（分母載具） | 分母＝**9**（R81 新帳本列，跨主檔＋全部 archive，以欄位定位而非整行比對）；分子＝**6**（ARCH-01／ARCH-04／QA-01／SA-B1／SA-B5／SD-02，皆為「文件寫下的行為與磁碟實作不是同一件事」）| ❌ | 門檻是**絕對值**：連續三輪 **≤1 筆且無任何一筆 P1**。本輪 6 筆，**差一個數量級**；且四方複審本輪有跑 ⇒ 不適用 N/A，也不得記 0 |
| **M3** | 複審者對該輪每一支新鎖各做一次注入，逐筆記紅綠；抽樣面另含**既有鎖庫隨機 20 支** | — | 第三方注入**確有發生**且有留痕：QA 對 `AutoClaude/.claude/settings.json` 注回一條 shell form，`check_hooks_liveness.py` rc=0（假綠）而 `test_check_hooks_liveness` 當場 `FAILED (failures=1)`；**既有鎖庫抽樣＝0 支** | ❌ | 兩個條件都沒到：①「連續兩輪 100%」——本輪未逐支列出每一支新鎖的第三方注入紅綠，只有具名的個案；②「既有鎖庫隨機 20 支」**至今一次都沒做過**（SSOT 自陳為目前最大量測缺口），距門檻 **20 支** |
| **M4** | `& $p -m unittest tools.tests.test_doc_loc_baseline_freshness_r60.TestR75IronLawMechanismSubstance tools.tests.test_doc_loc_baseline_freshness_r60.TestR74IronLawMechanismAccounting`；`…TestR81GhostPathClaims` | **0**（15 tests OK）／**0**（13 tests OK） | 機械化的那一面全綠；**但人工複審面本輪抓到 ≥6 筆**散文與實作不符（同 M2 分子），其中 ADR-XPLAT-005 自己就有**三處**行內落地訂正（§2.1 L1~L4、§2.4 判定量與刷新形態、§2.7／§6.2 喚醒時刻）| ❌ | 門檻是**一輪內 0 筆**。本輪 ≥6 筆 ⇒ 未達。🔴 兩支鎖全綠**不構成達標證據**——它們守的是「以反引號寫出的路徑與具名機械物」，抓不到「這段散文描述的行為與程式不同」 |
| **M5** | `& $p -m unittest tools.tests.test_platform_neutral_paths.TestXplatInjectionMatrix`；`& $p -m unittest tools.tests.test_maturity_criteria_r79` | **0**／**0**（17 tests OK） | `[Xplat injection matrix] Win2mac=6/12 mac2Win=5/10` ⇒ **未攔到題數：Win→mac 6 題、mac→Win 5 題** | ❌ | 門檻是兩個方向的未攔到題數**各自 ≤1 且連續三輪不回升**。距門檻：Win→mac 還差 **5 題**、mac→Win 還差 **4 題**。防稀釋鎖全綠（新題入庫門票＝當下攔不到；已知攔不到的只准修好不准刪）⇒ 這兩個數字**不能靠加語料變好看**。質性缺口未變：**程式碼語意層仍是 0** |
| **M6** | `& $p "$r\tools\run_root_unittests.py"`（印 `[skip census] tools/tests@win32`）；`AutoClaude` 樹 `& $p -m pytest tests -q -rs` 的 log 餵給 `& $p "$r\AutoClaude\tools\local_ci_gate.py" --census-only <log>` | **1**（根層）／**0**（AutoClaude pytest）、**0**（census） | 根層：`共 41 支：platform=40／env-disabled=1／欠債型 1`；AutoClaude：`4222 passed, 37 skipped`、`AutoClaude/tests@win32+pg+nested 共 37 支：platform=17／tool-absence=0／env-disabled=12／structural-pair=1／debt=7／untagged=0／欠債型 19` | ❌ | 兩條同時成立才算達標，**兩條都沒到**：①「從未被任何軌執行過」的支數**不是 0**——census 自己印出結構性 skip **18 支**的互補剖面 `AutoClaude/tests@linux+pg+solo`「至今沒有人量過」⇒ 它們沒有任何機械證據顯示在世界上任何一處跑過；②當輪 rc 佐證這一條，根層那一跑是 **rc=1**（8 筆 failure 屬並行包過渡態，見 `CrossPlatform_R81_Review.md` §4）|

**Q6 結論：0／6。** 門檻是「六條全達標**且連續三輪**，其中至少一輪是別人來查」⇒ 即使下一輪六條全綠，
最快也要 **R84** 才談得上成熟。🔴 **本節刻意不寫「比 R80 進步」**——R80 也是 0/6，兩輪的達標欄一格都沒動；
本輪動的是量尺（M2 分母首次以欄位定位算出、M6 兩棵樹首次同輪各跑一次 census），**修好量尺不是進度**。

---

## §2 本輪方法（沿用 R80，兩點微調）

1. **多維並行深掃 → 每筆發現派獨立懷疑者反駁**（`pipeline`，非 barrier）。懷疑者預設「它是假的」，
   不確定時傾向 `is_real=false`——寧可漏抓，也不放假發現進修復階段。
2. **掃描階段全程只讀不改**（避免並行改樹造成假紅，本 repo 已三次判例）。
3. **修復階段序列化**，收輪閘門一律在**所有包停工後的單人窗口**取得。
4. **四方複審（Architect／SA／SD／QA）獨立進行**，blocking 全收斂才算完成；派工本身要落 rc，
   使「複審沒跑」是可偵測而非靜默假設。
5. 🔴 **本輪微調①：扇出規模受額度水位節制**（訴求 b）。R80 四次撞線全部是「扇出開太大」造成的，
   不是「session 跑太久」——所以扇出寬度本身要當成一個受管的資源，而不是免費的。
6. 🔴 **本輪微調②：開輪的第一個機械動作是「帳本寫第一列」**。輪號時鐘是推得值，
   時鐘沒前進時每個並行包寫下的 R81 標籤都會讓 `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`
   轉紅，而每個包看到的都是「別人造成的紅」（本輪開場實測 20 站點／7 支檔）。立案見 `DEF-101-978`。

---

## §3 本輪已落地的包（隨輪次進展回填；**未經本包複驗者一律不填**）

| 包 | 對應訴求 | 落地物 | 複驗指令與 rc | 複驗者 |
|---|---|---|---|---|
| P7 剩餘面 | **P7** | `AutoClaude/.claude/settings.json` 的 6 條 shell form → **12 條 exec form**（shell form 實測 0 條）；`tools/lib/hook_wiring.py` 的 `SHELL_FORM_CENSUS` 兩格皆為 0 | 於 `tools/tests/`：`& $p -m unittest test_check_hooks_liveness` → **rc=0**。🔴 **不得用 `check_hooks_liveness.py` 當本列憑證**：QA 複審注入實測（把一條 shell form 條目注回該 settings）該工具仍回 **rc=0**（它只驗**載具存在性**，形態判準不在它射程內），而上述 unittest 當場 `FAILED (failures=1)` 並指名「shell form 條目實測 1、基準 0」 | 本包當回合實測 |
| Q4 第一道機械物 | **Q4** | `tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR81GhostPathClaims`——治理活文件裡以反引號寫出的 repo 路徑必須真的解析得到（含大小寫逐段比對，故 Linux 上不存在的拼法在 Windows 也判得出來） | `& $p -m unittest test_doc_loc_baseline_freshness_r60.TestR81GhostPathClaims`（於 `tools/tests/`）→ **rc=0，13 tests OK** | 本包當回合實測 |
| 帳本開輪 | **Q5** | 帳本開 R81 三列（`DEF-101-977`／`978`／`979`），時鐘由 R80 推進到 R81；同時處置時鐘前進所顯形的 7 列孤兒承接（走硬規則② 跨列出口，歷史原文逐字保全、原列零位元組增長） | `& $p "$r\tools\check_defect_log_crossref.py"` → **rc=0**；`current_round()` → **81** | 本包當回合實測 |
| 收尾（單人窗口） | **Q2**／**Q5** | ① 護欄層行數棘輪重釘（本輪共**四次**，最後一次的逐檔清單見 `CrossPlatform_R81_Scan_Findings.md` §B-3）；② `tools/lib/quota_meter.py` 入口點接上 UTF-8 stdio 保護（走 SSOT，非豁免）；③ `DEF-101-870` 脫離 ADR-XPLAT-001 §4.3.1 誤入（措辭訂正見同檔 §C）；④ hook payload 手抄本收斂：`context_budget_guard.py` 改用共用層、本地 21 行刪除、`_STDIN_OWN_READER_ALLOWED` 具名排除到期移除；⑤ `AutoClaude/tools/check_loc_budget.py` 對該 hook 的 raw-line 棘輪由納管值**下釘**到搬家後的實測 1451（合法縮小後不下修＝留破口）；⑥ 兩支活躍面工作樹行尾漂移就地轉回 LF（`AutoClaude/.perf_baseline.toml`、`AutoClaude/tests/integration/test_dry_run_kernel_path.py`） | `& $p "$r\tools\run_root_unittests.py"` → **rc=0**（`Ran 2600 tests`／`OK (skipped=41)`）；`& $p "$r\tools\check_defect_log_crossref.py"` → **rc=0**；`& $p "$r\AutoClaude\tools\check_loc_budget.py"` → **rc=0 violations=0** | 收尾當回合實測 |

> 🔴 **本表刻意不替仍在跑的包寫結論**。開場已知仍在進行中者：跨平台深掃、架構減法、
> skipped 普查、帳本分流、Token% 監控 ADR、`.sh`／`.ps1` 行為等價、續航協定兩缺口。
> 它們各自的落地物與 rc 由**收尾的單人窗口**逐項複驗後才進本表。

<!-- guard-total:R81 --> **本輪護欄層累積淨額＝ 65390 → 68423（+3033）**，五次重釘：**+2369**（十一包停工後）／**+149**（Architect 複審四筆 blocking 的收斂包）／**+42**（QA 複審三筆 blocking 的收斂包；🔴 該次**不是**單人窗口，SA／SD 同時在唯讀審查）／**+443**（SD 複審收斂後的收尾包，單人窗口）／**+30**（pre-push 攔下後的補包，單人窗口；逐檔清單見 `docs/06_quality/CrossPlatform_R81_Scan_Findings.md` §B-4）。
🔴 本輪走的是款(9) 的**登記手續**（`[非淨減法輪]` ＋ 指名逐檔清單的家），依 §4 禁止事項第一條，
**Q2 一律判未達成**——登記不是及格線。成長全在護欄層。
🔴 **生產側不得寫成「淨減」**（收尾者現查訂正）：hook payload 手抄本收斂確為 −39 行，
但第四段的 −183 行（`.claude/hooks/context_budget_guard.py` 1634 → 1451）是**搬家**——
接收端 `tools/lib/quota_limits.py` 自己是 341 行的新檔，生產側合計仍為正。

---

## §4 禁止事項（沿用 R80 §4，不放寬）

- ❌ 不准為了讓數字好看而調高任何門檻／棘輪／體積上限。合法出口只有兩條：
  ① 同一次變更內刪等量以上的行（真淨減）；② 走款(9)`[未附刪除清單]` 的**登記手續**
  （`[非淨減法輪]` ＋ 指名一份具名 `.md` 當逐檔清單的家）。② **不是**「也算及格」，
  它是**讓步條款**：強制的是「承認並留下可稽核的逐檔帳」，不是「准許成長」。凡走 ② 者 Q2 判未達成。
- ❌ 不准 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1`／跳過或註解掉失敗測試。
- ❌ 不准把「已通過／已驗證／零損失」寫進任何文件，除非同一則回覆貼得出當回合真跑的輸出。
- ❌ 不准在 Windows 用 Bash 工具；不准裸 `cd`／`Set-Location` 帶相對路徑；讀 rc 不接管線。
- ❌ 不准在多 agent 並行期間宣稱「全套閘門 rc=0」。
- ❌ 不准以「act／Docker 本機全綠」代替 mac 真機結論——act 跑的是 ubuntu，
  **Linux 綠不蘊含 mac 綠**（BSD vs GNU coreutils 差異結構上不在射程內）。
- ❌ 🔴 **本輪新增**：不准把「hook 不閃窗了」當成 P7 的驗收通過。exec form 載具解析不到時
  CC 只記一行 ERROR 就放行（fail-open），六支守衛靜默失效的螢幕表徵與修好完全相同。

---

## §5 交棒（收輪時填）

> **本節在收輪的單人窗口才寫**，內容至少含四項（同「可重啟點」四條件的形狀）：
> ①本輪已驗證什麼（附實測數字與 rc）／②還沒做什麼／③下一步的**確切指令**／
> ④禁止事項。承接檔名＝`docs/04_planning/R81_HANDOFF.md`。
>
> 🔴 交棒書的既有紀律：不採信任何「已通過」宣稱而不附當回合輸出；
> 未結列若仍在 warn 線以上，交棒書必須把「先結列再開新戰場」寫成下輪的第一動作。

---

## §6 收輪產物（清單，內容隨輪次進展回填）

- `docs/06_quality/CrossPlatform_R81_Scan_Findings.md` — 多維掃描與對抗式複驗結果
- `docs/06_quality/CrossPlatform_R81_Review.md` — 四方複審結論與逐筆 blocking 處置
- `docs/04_planning/R81_HANDOFF.md` — 交棒 R82
- `docs/06_quality/AutoSDD_Defect_Log.md` — 本輪缺陷列（單列 ≤ 700 bytes，詳情進具名證據檔）

> ⚠️ 上列前三份**本輪尚未建立**（本檔寫成時實查），故刻意不以反引號以外的形態指路——
> 它們是本輪的**產出目標**，不是既有檔案。建立時記得：`CrossPlatform_*.md` 落在
> `docs/06_quality/` 即自動進入具名治理文件的發現面，未登記進 `_GOVERNANCE_DOCS` 會轉紅。
