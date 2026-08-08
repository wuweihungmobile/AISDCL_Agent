# AutoSDD_improving_104 — R80 跨平台輪（Windows 11 真機）

> 軌道① 整合迭代第 104 份；本輪同時是**跨平台複審輪 R80**（輪號權威源＝
> `tools/check_defect_log_crossref.py::current_round()` 讀帳本「發現情境」欄，收輪前現查）。
>
> 🔴 **體例（沿用 R78／R79 並加嚴一條）**：凡述及「已通過／已達標／尚未做／已推送」這類狀態，
> 一律附**現查指令**，不寫快照結論。**本輪加嚴**：凡述及「某類危害沒有機械物在守」，
> 必須同時指出該宣稱是由哪一支判準在守——否則那句話自己就是下一輪的假事實。

---

## §0 本輪定位與唯一驅動器

三柱對齊（根 `CLAUDE.md`〈三條改進軌道〉）：本輪主體落在 **B 柱（手腳 AISDLC_SDD）＋
C 柱（指揮官 AutoClaude）的跨平台基礎設施**，A 柱（雙向協作橋接）本輪不動。

**開場已完成的前置**（附實測）：

| 前置 | 實測 |
|---|---|
| 缺陷帳本體積洩壓 | `archive_defect_log.py --apply --archive-num 63` → 41 筆／30,007 bytes；主檔 **258,426 → 232,526**（釋出 25,900），距 fail 線 262,144 餘 **29,618** |
| 未結列水位 | 開場 **85**／warn 86／fail 98（`--unresolved-count`） |
| 雲端可用性 | `gh run list` 最近 3 個 commit 全 failure，但 `gh run view <id> --json jobs` 實測 **`steps: 0`** ⇒ **Actions 帳務停擺，不是程式碼紅**。本輪全程 act + Docker 本機驗證 |
| 本機驗證載具 | docker 29.5.3｜act 0.2.89｜`autoclaude_pg` healthy（pgvector:pg18）｜**java 21.0.10 在**（⇒ TLC 軌今天可真跑） |
| 護欄實效（開場即被自己的鎖攔） | 舵手第一批指令中 `Bash` 工具與裸 `Set-Location` **各被 PreToolUse hook 當場擋下 1 次**，零副作用 |

---

## §1 本輪要回答的題目（舵手原始訴求逐條，不得漏答）

| 編號 | 訴求 | 驗收判準（機械可查者優先） |
|---|---|---|
| **Q1** | Mac／Win 11 部署執行與開發零相容缺陷 | 鐵律三對照表的分子（有機械物列數）上升；新登記危害類的分母亦上升；**每一格「無機械物」都要指出是誰在守這句話** |
| ↳ **Q1 結論** | 🔴 **未達成**（判準只量到「有沒有人在守」，量不到「零缺陷」） | 判準那一半可查且本輪為綠：`& $p -m unittest test_doc_loc_baseline_freshness_r60.TestR74IronLawMechanismAccounting test_doc_loc_baseline_freshness_r60.TestR75IronLawMechanismSubstance`（於 `tools/tests/`）——覆蓋率棘輪（分子只准升、分母也只准升）與實質判準（具名機械物必須真的在守該列主題）皆通過。**但訴求逐字是「零相容缺陷」，那件事本輪一次都沒被證明**：mac 真機零覆蓋（見 §7 交棒書取證邊界），act 跑的是 ubuntu，**Linux 綠不蘊含 mac 綠**。⇒ 誠實的說法是「Windows 側今日無已知未修相容缺陷；mac 側**未量**」。現查分母與未覆蓋類數：讀根 `CLAUDE.md`〈鐵律三〉那張表（判準讀的就是那張表本身）|
| **Q2** | 架構簡潔－分工清楚－不重複模組；**拿掉不合理機制** | 本輪必須是**淨減法輪**：護欄層 raw-line 淨額 ≤ 0，或明列「為什麼這一次的成長是必要的」並附刪除清單 |
| ↳ **Q2 結論** | 🔴 **未達成，且閘門是靠重釘棘輪基線通過的** | <!-- guard-total:R80 --> `_FROZEN_GUARD_LINES` 本輪自 HEAD 起的**累積**淨額＝ **63056 → 65390（+2334）**，分**三次**重釘：**+1528**（六個修復包停工時）／**+595**（四方一審後三個收斂包停工時）／**+211**（二審五筆 blocking 的收斂包，即本次）。🔴 **二審 `NEW-SA2-01`＝`QA2-N2` 訂正**：本格 R80 版只寫了第一次的 `63056 → 64584（+1528）`，漏掉其後兩次；掃描發現文件 §B-2 又把前兩次相加寫成 `+2029`（1528＋595＝2123，差 94）。三個站點同時錯而**沒有任何東西轉紅**，因為在此之前沒有判準看得到 `.md`。⇒ 已補判準 `doc_guard_total_problems()`（見下）。逐檔清單與**逐項必要性辯護**見 [`CrossPlatform_R80_Scan_Findings.md`](../06_quality/CrossPlatform_R80_Scan_Findings.md) §B／§B-2／§B-3（同一件事只有一個家）。掃描 S5-02 早已指出「這條棘輪是**收費站不是棘輪**，自助放行出口寫在判準訊息裡」，本輪不但沒修那個出口，**還自己走了三次**。**同一次變更給那個出口加上了登記手續**（🔴 二審 `NEW-ARCH-R80B-03`：原文寫「已把出口關上」是假的——款(9) 強制的是**承認**，不是不准成長）：`repin_log_problems()` 款(9)`[未附刪除清單]`——淨額為正的重釘列必須①有量化刪除交代（`刪 N 行`，N ≥ 淨額）或明文標記 `[非淨減法輪]`，**且**②指名一份具名 `.md` 當逐檔清單的家（刻意不受理 `--print-guard-lines`：它讀工作樹，並行改樹時每人讀到不同的數字，它是查詢入口不是紀錄）。二審再補一道**文件側**對帳：`doc_guard_total_problems()`——帶 `guard-total:<輪號>` 標記的行所引用的總量必須逐字等於 `sum(_FROZEN_GUARD_LINES.values())`、且該行自己的算術要自洽（現查：`& $p -m unittest test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet`，於 `tools/tests/`）。帳本 `DEF-101-962` |
| **Q3** | Mac 開發時 Win 不落差、反之亦然 | 落差面收斂到單一 SSOT；`.ps1`／`.sh` 對等性由**行為**而非**存在性**判定 |
| ↳ **Q3 結論** | 🔴 **未達成——判準的第二半（行為等價）今天沒有任何機械物** | 前半（單一 SSOT）本輪有推進：hook 佈線解析由七處手抄收斂成 `tools/lib/hook_wiring.py`（現查 `& $p "$r\tools\check_hooks_liveness.py"`）。**後半沒有**：`check_script_parity.py` 驗的是「存在性＋位元組釘選＋幾道具名鎖」，**不驗一般行為等價**（現查 `& $p "$r\tools\check_script_parity.py"`，讀它印出的鎖清單就是它真正涵蓋的範圍）⇒ 13 對 `.sh`／`.ps1` 可行為分歧而零訊號（掃描 S8-05，**未落地**）。🔴 收尾者自陳：本格第一版引用了一個**本輪已被架構減法包刪掉**的名冊符號，被幽靈符號鎖當場抓下——那正是 S8-05 這一格在講的「宣稱與實作對不上」，只是這次長在描述它的句子上。承接 R81 |
| **Q4** | Windows 常犯低級錯誤的根因徹底解決 | 🔴 **先驗證量測器符號**（R79 實測 `rc-after-pipe` 把正解算成違規）；符號修正後才重跑歸因；報絕對筆數不報百分比 |
| ↳ **Q4 結論** | 🔴 **根因已改判、未「徹底解決」**；最大桶是**宣稱先於查證**（絕對筆數如下） | ①**符號先驗**（判準指定的前置）：`& $p "$r\tools\probe\audit_session.py" --selftest` → rc=0，新判準 10 組全判對、**舊判準錯 6/10**（舊的把「管線左邊是變數」這個根 `CLAUDE.md` 教的正解算成違規）⇒ 符號確已翻正，歸因才有意義。②**重跑歸因**：`& $p "$r\tools\probe\misstep_attribution.py"` → rc=0。**絕對筆數（母體 n=1200＝缺陷帳本 1092 列＋逐字稿自陳失誤 108 句；單位＝「一列帳本／一句自陳」，不是「一次操作」）**：`CLAIM-FIRST` 宣稱先於查證 **196**／`LOCKBLIND` 鎖射程失明 **171**／`BADPIPE` 取數管道給假數字 **118**／`CARRIER` 選錯載具 **113**／`OTHER` 關鍵詞平手或不明顯 **602**（已歸類 598）。③🔴 **百分比不得被引用為常數**——分群是關鍵詞啟發式，腳本自己會印這句；量級穩健（桶與桶的大小關係可引用）、小數不穩健。母體與單位與 R77 那次人工分群**不同**（那次無 OTHER 桶），只可量級對照、不可逐點比較。④**與 R71／R77 的結論差異**：R71（n=8）判「選錯載具」為首，R77（人工）判「鎖無鑑別力」為首，本輪判 `CLAIM-FIRST` 為首——`CARRIER` 已掉到最小的具名桶，與「鐵律一已上機械阻斷」一致。⑤**為何仍不算徹底解決**：最大桶 `CLAIM-FIRST` 今天**沒有任何機械物**（PowerShell 攔截器守的是載具與 rc 讀法，守不到「沒跑就說已驗證」），且本輪二審五筆 blocking 有**四筆**是「文件宣稱與磁碟不符」——那正是這一桶在真實工作裡的主要形態（第五筆 `NEW-ARCH-R80B-02` 屬鎖射程失明那一桶）|
| **Q5** | 各專家挖深＋Developer 清技術債 | 未結列**真降**（非搬帳）：新增列數 < 結案列數；(A) 類「其實已修好只差狀態欄」逐筆附實查 |
| ↳ **Q5 結論** | 🔴 **按逐字判準仍是未達成**（但方向已由「相反」轉為「下降」） | 🔴 **二審 `NEW-SA2-04` 訂正本格的水位數字（原文寫「86」，而那是**第一次收斂當下**的值；其後二審又新立了列）**：本格此後**不記快照**，一律現查 `& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count`。收輪當下已**越過 warn 線 86**，距 fail 線 98 只剩個位數 ⇒ **R81 開場第一件事就是處理它**（歸檔**不會**降低此數，工具自己每次都印這句；唯一出路是結列或改派具名承接者）。以下兩個讀數是**當時的量測值**，保留是為了記錄方向，不得引用為現況：**①未結列 91 → 86**（包 C 逐筆實查後結掉 8 筆：`DEF-100-002`「修了沒人來關」、`DEF-101-274`「本列的主張今日為假」、`DEF-101-418` 復燃條件從未成立、`DEF-101-422`／`DEF-01-007`／`DEF-101-021`／`022`／`025` 六筆分流欄早已是拍板結論只是狀態字沒跟上；逐筆實查證據見 `CrossPlatform_R80_Scan_Findings.md` §C）——這是真降不是搬帳，`--unresolved-count` 前 91 後 86。**②但判準逐字寫的是「新增列數 < 結案列數」，本輪新立 14 列 > 結案 8 列 ⇒ 不及格。** 掃描列的「零成本可結」九筆中，`DEF-101-377`（只涵蓋 `.sh` 那半，`.py` 方向今日仍無機械物）與 `DEF-101-856`（六項只有第①項可結）**刻意不關**——關掉會製造假事實。承接 R81 |
| **Q6** | 成熟度 M1~M6 | 逐條實測，附量測載具與當輪 rc |
| ↳ **Q6 結論** | 🔴 **六條 0 條達標；明文門檻＝六條全達標且連續三輪，其中至少一輪是「別人來查」** | 判準 SSOT＝[`CrossPlatform_Maturity_Criteria.md`](../06_quality/CrossPlatform_Maturity_Criteria.md)（門檻寫在該檔〈五個收斂條件〉末段與〈現況總判〉）。**逐條當輪實跑**：<br>**M1 ❌** 載具 `& $p "$r\tools\run_root_unittests.py"`（末行印 `[Scan-H triplet]`）rc=0，實測 `UEP=5 AC=47 GLC_FILES=57`；`--print-guard-lines` rc=0。兩半都不成立——UEP 半要 ADR-XPLAT-002 §8.1 出現回執，該表現查**仍是空表**（逐字「（尚無回執…）」）；護欄行數半要求總量**連續三輪不上升**，而本輪自己就重釘了三次（見 Q2 結論）。<br>**M2 ❌** 分母現查 41（本輪帳本新列，跨主檔＋archive 數「發現情境」欄含 R80 者）；分子＝二審抓到的失實宣稱，光 blocking 就 5 筆（門檻是**連續三輪 ≤1 筆且無 P1**）。<br>**M3 ❌** 四方複審本輪確實跑了兩審，但門檻的第二半「抽既有鎖庫隨機 20 支做第三方注入」**至今一次都沒做過**；且本輪二審後新落地的判準（含本檔這一批）**沒有再被第三方看過** ⇒ 依 M3「作者自證不計分」，那一段強度上限是作者自己的注入紅綠。<br>**M4 ❌** 機械面綠：`& $p -m unittest test_doc_loc_baseline_freshness_r60.TestR75IronLawMechanismSubstance test_doc_loc_baseline_freshness_r60.TestR74IronLawMechanismAccounting` rc=0（15 tests OK）。但門檻是「一輪內 0 筆宣稱／實作落差」，二審實測 ≥4 筆（`NEW-ARCH-R80B-01` CLAUDE.md 兩處、`-06` 訂正註記自打嘴、`-07` hook_wiring 檔頭、`NEW-SA2-03` ADR §2.6）。<br>**M5 ❌** 載具 `& $p -m unittest test_platform_neutral_paths.TestXplatInjectionMatrix` rc=0，`setUpClass` 印 `[Xplat injection matrix] Win2mac=6/12 mac2Win=5/10` ⇒ **未攔到題數＝ 6 與 5**（門檻是兩向各 ≤1 且連續三輪不回升）。<br>**M6 ❌ 且第①條量不出確切值**。兩個入口今天**都真的會印數字**（🔴 R79 記載的「M6 那一格具名載具跑起來什麼都不印」已修，本輪實跑確認）：①根層 `& $p "$r\tools\run_root_unittests.py"` rc=0 → `[skip census] tools/tests@win32 共 43 支：platform=38／untagged=5／欠債型 5 支（目標 0）`；②AutoClaude 樹 `python -m pytest tests -q -rs` rc=0（4199 passed／44 skipped）餵給 `& $p "$r\AutoClaude\tools\local_ci_gate.py" --census-only <log>` rc=0 → `共 44 支：platform=17／tool-absence=3／env-disabled=1／untagged=23／欠債型 27 支（目標 0）`。門檻第①條「從未被任何軌執行過的測試支數為 0」**不成立**：census 自己逐字印出那 17 支結構性 skip 的互補剖面 `AutoClaude/tests@linux+pg+solo` **至今沒有人量過** ⇒ 該數字的**下界是 17、確切值量不出來**。<br>🔴 **另記兩個結構問題的現況**：R79 記載的「M1 在 SSOT 裡有兩個不等價定義」已修（門檻改合取，鎖＝`& $p -m unittest test_maturity_criteria_r79` rc=0，17 tests OK）；「M6 具名載具跑起來什麼都不印」亦已修（見上）。⇒ 這兩筆本輪**只需複驗，不需再修** |
| **S1** | context 不超 90%、不要爆 | 🔴 **要分清「出聲」與「真的做到」**：90% 那道要能讓壓縮**實際發生**，不能只印字給模型看 |
| ↳ **S1 結論** | 🔴 **未達成**——本輪把「阻斷臂射不到東西」修好了，但「壓縮實際發生」那一半仍**只是出聲** | 已修的那一半（`DEF-101-970`）：`BLOCKING_TOOLS` 圈的三個名字在本 harness 的 tool_use 裡命中 **0** 次（實際叫 `Agent`／`Workflow`），R79 為它建的鎖只把 matcher 與射程釘成相等 ⇒ **兩個都寫錯時也一致**。已補真名＋`blocking_reach_problems()`（圈到的名字須與實測 tool_use 名稱有非空交集）。現查 `& $p -m unittest test_context_budget_guard.PreToolUseBlockTest`（於 `tools/tests/`）。**未達成的那一半**：90% 那道仍只是 PostToolUse 印指引給模型看，`/compact` 是否發生取決於模型自己讀不讀——R80 實測 0/70 session 到過 90%、3 次壓縮全是人手打的，所以這個判準今天**連被觸發的機會都沒有**（門檻在那個水位，而水位到不了）。承接 R81（與訴求 b 的 80%／95% 兩道同一件事）|
| **S2** | Token 用盡→下輪 reset 喚起續跑 | 憑證＝`NextRunTime` 這個值（不是 rc）；且「沒觸發」必須可偵測 |
| ↳ **S2 結論** | 🔴 **前四段成立、第五段的觸發條件設計錯了**（＝§4.5 R81-0 的驗屍結論，不重述） | 本輪四次真實撞線、四種失敗模式，逐筆與處置見 §4.5〈R81-0〉那張表（唯一的家）。可現查的部分：憑證面 `& $p "$r\tools\session_resume_planner.py" --verify-schtasks`（取 `NextRunTime` 這個**值**，不是 rc——`Get-ScheduledTask` 對不存在的工作回 rc=0）；痕跡面 `Get-ChildItem $env:TEMP\autosdd_resume_log_*.jsonl`（沒觸發＝檔案不會長大，是可偵測的）。⇒ 判準的兩條（`NextRunTime` 為憑證、沒觸發可偵測）**今天都成立**；不成立的是訴求本身——協定救的單位是 session，而本輪四次死的都是**扇出**，主迴圈一次都沒死 ⇒ 續跑那一段結構上不會被觸發。承接 R81 |
| **S3** | pytest skipped 徹底解決、全部可測 | 逐筆 skip 分五類；(a) 環境未啟用類**歸零**；孤兒測試（兩平台皆不跑）列出並處置 |
| ↳ **S3 結論** | 🔴 **未達成**——本輪交付的是**治理**不是解決 | 逐類現況：**(1) platform**（結構性，目標**不是** 0，而是「互補剖面上真的有人跑到」）——`tools/tests@win32` 38 支的互補面本輪首次有證據（act 實測 `tools/tests@linux` 72 支入表）；`AutoClaude/tests` 那 17 支的 linux 剖面**仍無人量過**。**(2) env-disabled**：R79 已證一次可消 92 支（設三個環境變數），本輪未再推進。**(3) tool-absence／(4) debt**：小量，未動。**(5) untagged**：`win32+pg+nested` 仍 23 支、`win32+nopg+nested` 118 支——這一格才是欠債主體，本輪**一支都沒補標籤**。本輪實際做的三件事：①把根層 43 支首次納入天花板管轄；②消滅 `[sdk]` extra 那一族（唯一真正消滅的）；③P7 修復又**新增一個永久 POSIX skip 站點**。🔴 **可查量測入口（下一輪不必重新發明量法）**：根層＝`python tools/run_root_unittests.py` 會印 `[skip census] <剖面> 共 N 支：…／欠債型 M 支（目標 0）`；AutoClaude 樹＝`python AutoClaude/tools/local_ci_gate.py --census-only <pytest log>`（pre-push 與 CI 都已接這條線）。刻意**不另建第三個入口**——同一份知識再開一個家正是本 repo 反覆在治的病。帳本 `DEF-101-960` |
| **P7** | 🔴 **哨兵仍會彈 console 視窗**（舵手當輪回報） | 法醫級定案：窮盡列出 spawn 站點、實測取證（conhost 子行程為代理）、**類級**修法＋掃描器 |
| ↳ **P7 結論** | ✅ **類級修法已落地並有掃描器**；⚠️ 代價是**新增一個永久 POSIX skip 站點**（已誠實登記，見 S3 結論） | 三件事分開看：①**載具面**——`.claude/settings.json` 的 hook 由 shell form 轉 exec form（shell form 每觸發一次就經 `bash.exe` 起一個 console 視窗），根層 20 條已轉；②**直譯器面**——`quiet_python()` 補上第二層防線（無 console 父行程下 spawn 的 `creationflags`），註解此前宣稱兩層而實作只有一層（`DEF-101-956`）；③**掃描器**——`hook_form_problems()` 判準 A~F ＋ `is_command_hook()` 收斂（`DEF-101-965`：`type` 欄有三種慣例，省掉 `type` 就能逃過全部判準）。現查 `& $p "$r\tools\check_hooks_liveness.py"`；注入 `& $p -m unittest test_check_hooks_liveness`（於 `tools/tests/`）。🔴 **射程誠實劃界**：`AutoClaude/.claude/settings.json` 的 6 條**仍是 shell form**（`DEF-101-967` open，承接 R81），現況由 `SHELL_FORM_CENSUS` 相等棘輪登記為 `root=0／AutoClaude=6` ⇒ 那 6 條在 AutoClaude 子專案 session 下仍會閃窗 |
| **a** | 🔴 **掌舵者本輪新提**：額度水位一律用 **%**，不是固定量（啟動帳號不同 ⇒ 絕對量在兩台機器之間不可比） | 驗收判準＝**分母的取數管道**必須是可重跑的程式，且要能說出它取的是哪一種計費口徑。🔴 **單一校準點解不開「口徑」與「分母」兩個未知數**：舵手當輪回報 UI 真值 `Current session / 78% used / Resets in 1 hr 35 min`，同窗口 3,015 筆 usage（`input=27,969`／`cache_creation=33,952,076`／`cache_read=358,166,157`／`output=1,248,761`）依四種口徑各給一個候選分母（**1.64M／45.2M／504M／91.1M**）——四個都能「湊出 78%」。⇒ 判準必須要求**多點校準**或權威來源，不得挑一個看起來合理的填進去（同 R79「猜出來的 reset 時刻」判例：門檻會成立、百分比印得出來，只是它在錯的水位上動作） |
| **b** | 🔴 **掌舵者本輪新提**：**80%** 少派 agent、準備下一次 reset；**95%** 停止、準備喚醒 | 驗收判準＝兩道各自的**動作**要真的發生，不是印一行字給模型看（同 S1 對 90% 那道的判準，實測 0/70 session 到得了 90%、3 次壓縮全是人手打的）。80% 那道要能真的降低併發（少派 agent），95% 那道要能真的收斂並武裝喚醒（`NextRunTime` 為憑證）。🔴 **本輪零交付**：三方設計（Architect／SA／SD）已完成，但 ADR 合成與實作兩階段都在額度上限陣亡 ⇒ 它一度**既不在計畫書、也不在 ADR、也不在任何程式碼與帳本列裡**，唯一載體是 session 級暫存。本兩列＋帳本 `DEF-101-961` 就是它今天的家（本 repo 判過：記憶會遺漏 ⇒ 延後＝技術債永久消失）。**承接 R81** |

---

## §2 本輪方法（與前幾輪的差別）

1. **八維並行深掃 → 每筆發現派獨立懷疑者反駁**（`pipeline`，非 barrier）。懷疑者預設「它是假的」，
   不確定時傾向 `is_real=false` —— 寧可漏抓，也不放假發現進修復階段。
2. **掃描階段全程只讀不改**（避免並行改樹造成假紅，本 repo 已三次判例）。
3. **修復階段序列化**，收輪閘門一律在**所有包停工後的單人窗口**取得。
4. **四方複審（Architect／SA／SD／QA）獨立進行**，blocking 全收斂才算完成。
   本輪要一併處理 R79 交棒 §4 指出的結構問題：**派工本身不落任何 rc**，
   使「複審沒跑」是可偵測而非靜默假設（連續四輪靠人記得、其中兩輪實際沒跑成）。

---

## §3 承接 R79 交棒書 §4 的待辦（15 項，逐項處置記錄在收輪報告）

分四組：4.2 收斂包點名未做（4 項）／4.3 判準形狀與結構債（8 項）／4.4 需舵手拍板（3 項）。
🔴 **4.4 三筆 agent 不得代決**（Windows smoke 排程退場 vs 降頻、四支子專案 hook 是否橋進根層、
UEP 末階 PM signoff），本輪只把決策題目與利弊整理到可拍板的程度。

現查待辦全文：`docs/04_planning/R79_HANDOFF.md` §4。

---

## §4 禁止事項（沿用 R79 §5，不放寬）

- ❌ 不准為了讓數字好看而調高任何門檻／棘輪／體積上限。**合法出口有兩條**（🔴 二審 `NEW-SA2-08` 訂正：本條 R79 版寫「只有」一條，而同輪落地的款(9) 已經開了第二條，兩處直接衝突）：
  ① **同一次變更內刪等量以上的行**（真淨減）；
  ② 走款(9)`[未附刪除清單]` 的**登記手續**——理由欄明文標 `[非淨減法輪]` ＋ 指名一份具名 `.md` 當逐檔清單的家。②**不是**「也算及格」，它是**讓步條款**：它強制的是「承認並留下可稽核的逐檔帳」，不是「准許成長」。凡走 ② 的輪次，Q2 一律判**未達成**。
- ❌ 不准 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1`／跳過或註解掉失敗測試。
- ❌ 不准把「已通過／已驗證／零損失」寫進任何文件，除非同一則回覆貼得出當回合真跑的輸出。
- ❌ 不准在 Windows 用 Bash 工具；不准裸 `cd`；讀 rc 不接管線。
- ❌ 不准在多 agent 並行期間宣稱「全套閘門 rc=0」。
- ❌ 🔴 **本輪新增**：不准以「act/Docker 本機全綠」代替 mac 真機結論。act 跑的是 ubuntu，
  **Linux 綠不蘊含 mac 綠**（BSD vs GNU coreutils 差異結構上不在射程內）。

---

## §4.5 🔴 掌舵者指定的 R81 主線（2026-08-08 當輪口述，C 軌「指揮官 AutoClaude」）

> 立案脈絡：本輪續航協定第一次真正被觸發（偵測→觀測 reset→重排→探測→續跑五段全中），
> 但接回來那一跑**只是手腳**——它照任務書做事，不會在遇到「6 個修復包全數陣亡、留下半套磁碟改動」
> 這類意外時改變計畫。掌舵者當場指出真正的分工。

### R81-1｜現行啟動方式**結構上缺一個舵手**
Antigravity／Claude Code 這條路徑上，**必須把互動 session 喚醒回來**才有人做全盤判斷。
`claude -p -r <session>` 的 headless 續跑補不了這一格。
⇒ 續航協定要分兩種模式，且**模式選擇要是機械的、不是靠人記得**：
- **有人看管** → 喚醒互動 session（現行 `--resume-tick`）
- **無人看管** → 交給 AutoClaude 跑 Playbook（見 R81-2）

⚠️ 尚未驗證的隱憂（本輪未做）：自動續跑用 `-r <同一個 session id>`，會寫進互動 session 的
**同一份逐字稿**。互動 session 還開著時兩個行程寫同一個檔，安全性未驗。

### R81-2｜AutoClaude 帶目標任務啟動時，**它自己就是舵手**
掌舵者原話：「可以把 `example_playbook.yaml` 中的 `global_goal` and `tasks` 開發與測試應用起來，
這樣開發的效率最為顯著」。

現查 `AutoClaude/scripts/example_playbook.yaml`（本輪實讀），三個欄位剛好對上本輪打了一整輪的三件事：

| Playbook 欄位 | 對應本輪的什麼 |
|---|---|
| `global_goal` | **無人看管那一跑缺的判準**。檔內註解逐字：「每次修正都會以此為判斷基準，避免修正方向偏離整體目標」 |
| `evaluator_command` ／ `evaluator_timeout_seconds` | **本 repo「舉證紀律」的機械化版本**——檔內註解逐字：「AutoClaude 雙重驗證：AI 說完成不算，Evaluator 親自跑 pytest」。這正是本 repo 反覆手工執行的那條規則 |
| `global_invariants.auto_compact_interval` | 掌舵者訴求 2（context 不要爆）的**已存在**機械化版本；而本輪實測互動側那道 90% 門檻 **0/70 session 觸發過**（S2-01） |

### R81-0｜🔴 **驗屍：續航協定為什麼「沒有作用」——四次真實撞線、四種不同的失敗模式**

> 掌舵者當輪指令逐字：「請查明為何沒有作用，納入下一輪改善！**從失敗中記取教訓**」。
> 本節每一筆都有當輪稽核痕跡（`%TEMP%\autosdd_resume_log_autosdd_resume_plan_<sid>.jsonl`）為證，不是回溯推論。

| # | 時刻 | 類型 | 協定的反應 | 為什麼沒救到 | 本輪處置 |
|---|---|---|---|---|---|
| 1 | 01:23~01:40 | session limit | **五段全中**（偵測→觀測 reset→重排→探測→續跑） | 續跑那一跑 **cwd＝`C:\Windows\System32`** ⇒ 讀不到任務書、碰不到 repo，什麼都做不了 | ✅ **已修並端到端證實**（Action 補 `-WorkingDirectory`＋`_run_resume` 補 `cwd=`；續跑自報 `CWD=repo 根`）。另抓到第二個 P0：`--add-dir` 是變長參數，排在 prompt 前會**吞掉 prompt** ⇒ rc=1 而**五段痕跡全綠** |
| 2 | 02:00~06:50 | session limit | **整晚每 15 分鐘巡邏，每次都判「無未處理撞線」** | `handled_through` 的立案理由「我此刻跑得動武裝指令 ⇒ 額度是通的」**是假話**——武裝是**零 API 呼叫的本機 subprocess**。實證 `handled_through=18:38:56Z` vs 撞線 `18:36:53Z` ⇒ **撞線後 2 分鐘就被標成已解決** | ✅ **已修**：偵測面改用**全域復原證據**（誤判率先量後定判準：擴 subagent 面 14.8%／同檔證據 **81.3%**／全域證據 **0.0%**） |
| 3 | 約 12:00 | **monthly spend limit** | 無 | 🔴 **結構上無解**：它**沒有 reset 可以等**，只有掌舵者到 `claude.ai/settings/usage` 調高上限才會回來。「排程等待」對這一類是**錯的動作**——等到天亮它還是滿的 | ❌ **未處置**（見 R81-0-a） |
| 4 | 16:27~16:40 | session limit | **偵測 ✅ 觀測 reset ✅ 重排 ✅**（`arm_reset`「觀測 reset=16:40:00 尚未到 ⇒ 重排到那個時刻」），16:42 醒來判「session 還活著」→ 續巡 | **它做對了，但沒救到任何東西** | 🔴 **這一次暴露的是設計缺口，不是 bug**（見 R81-0-b） |

#### R81-0-a｜額度有兩條線，協定只認得一條
`session limit` 有 reset 時刻（可觀測、可排程）；`monthly spend limit` **沒有**。
現行 `classify_limit()` 雖有 `LIMIT_SPEND` 分類，但下游動作只有一種（排到 reset）。
⇒ **R81 要做**：對 `LIMIT_SPEND` 走**不同的分支**——不排程、改成**通知人**（它需要的是人的動作，不是時間）。
🔴 判準要能區分「等得到的」與「等不到的」，否則協定會在一個永遠不會變的狀態上空轉，而痕跡看起來一切正常。

#### R81-0-b｜🔴 **協定救的單位錯了：它救「session」，而死的是「扇出」**
本輪四次撞線，**主迴圈一次都沒死**——死的是 subagent（第一次 42 個、第二次 55 個、第四次 1 個）。
於是：偵測對了、重排對了、**續跑永遠不會觸發，而且不該觸發**（session 還活著時再起一個 headless 回合只會互相干擾）。
真正需要被救的是**那一批被打死的扇出**，而本輪那件事**只有舵手手動用 `resumeFromRunId` 做得到**
（workflow 的已完成 agent 從 cache 回放、只重跑死掉的那些——這個能力存在，但沒有任何東西會自動去按它）。

⇒ **R81 要做**（這是本輪學到最重要的一課）：
1. **把「可續跑的工作單位」從 session 降到 workflow run**：撞線時記下 `runId` 與未完成的 agent 集合，額度回來時自動 `resumeFromRunId`。
2. **承認主迴圈不會死**：協定的預設動作應該是 **throttle（少派）** 而不是 resume。這正好接上掌舵者本輪新提的 a/b
   （80% 少派、95% 停止）——而那一項本輪**零交付**（見 §1 的 a/b 兩列）。
   🔴 **兩件事其實是同一件事**：本輪四次撞線全部是「扇出開太大」造成的，而不是「session 跑太久」。
3. **無人看管時把舵手交給 AutoClaude**（見 R81-1／R81-2）——因為扇出的重派需要判斷，而 headless 續跑那一跑做不了判斷。

#### R81-0-c｜誠實記下：本輪修好的兩筆，是真的修好了
不要因為「整體仍沒救到」就把已驗證的成果一起否定：
- 第 1 次的 cwd P0 **端到端證實**（續跑自報 `CWD=repo 根`、讀得到任務書）
- 第 2 次的偵測面失明 **已修**，而且第 4 次撞線就是它第一次在真實樣本上**正確偵測到**的證據（16:27 那行 `arm_reset`）
⇒ 協定的**前四段**（偵測／觀測／重排／探測）今天可以說是成立的；**第五段（續跑）的觸發條件本身設計錯了**。

---

### R81-3｜🔴 **PostgreSQL 才是「AutoClaude 能當舵手」的結構理由**（掌舵者當輪補充提醒）

這不是實作細節，是**為什麼 AutoClaude 做得到而 `claude -p -r` 做不到**的那個原因：

| | 舵手狀態存放處 | 跨行程死亡／額度 reset 後還在嗎 |
|---|---|---|
| `claude -p -r <session>` | 只有**逐字稿** | 逐字稿在，但**沒有目標、沒有 checkpoint、沒有下次該做什麼** |
| AutoClaude ＋ Playbook | **PostgreSQL**（DAL 三後端之一） | 在。`pg_state_repository.py` 內實有 `checkpoint` 與 `scheduled_resume_at` |

本輪實查（當回合真跑）：
```
docker ps --filter name=autoclaude_pg  →  autoclaude_pg | pgvector/pgvector:pg18 | Up 36 hours (healthy)
AUTOCLAUDE_TEST_PG_DSN                 →  unset
docker exec autoclaude_pg psql -U postgres  →  FATAL: role "postgres" does not exist   ← 角色名不是 postgres，R81 要查對
Grep checkpoint|scheduled_resume_at 於 AutoClaude/autoclaude/infra/repositories/ → 8 檔命中（含 pg_state_repository.py）
```

⇒ R81 的 PG 相關動作：
- **查對連線參數**（角色名／DB 名／port）並寫進 ONBOARDING，本輪實測「猜 `postgres` 是錯的」。
- 把 Playbook 跑在 **Pg 後端**（不是 File／InMemory）——否則舵手狀態不落地，等於沒有續航能力。
- ⚠️ 連動 S3-06（本輪掃描確認）：`AUTOCLAUDE_TEST_PG_DSN` **有兩個驅動需求互斥的消費端且零驗證**，
  照文件以外的合法 DSN 形態設值會讓 15 支測試在 setup 硬炸、訊息指向 SQLAlchemy 而非 repo。**先修這個再談跑 Playbook**。
- ⚠️ 版本漂移（既有已知）：**本機 pg18 vs CI pg17**。Playbook 若依賴 PG 行為差異，兩邊會不一致。
- 順帶：設 DSN ＋ 裝 `postgres` extras 可讓 AutoClaude 的 skip 大幅下降並**暴露數支從未執行過的真 failed**（既有實測），
  與本輪包 A（skipped 歸零）同一條線。

⇒ R81 要做的不是新蓋，是**把已存在的東西接上電並實用化**（本 repo 已判過三次「機制蓋好沒接電」）：
1. 用真實的 AISDLC_SDD／AutoClaude 開發任務寫一份可跑的 Playbook（不是 auth module 範例）。
2. 驗證 `evaluator_command` 在本 repo 的閘門上真的有鑑別力（餵一個會失敗的 evaluator，確認它擋得住）。
3. 把「無人看管續跑」的載體從 `claude -p -r` 換成 `python -m autoclaude <playbook>`，**且跑在 Pg 後端**，並比較兩者的實際產出。
4. 量 `auto_compact_interval` 的實效（本輪已證互動側那道從未觸發，AutoClaude 側是否也一樣？）
5. 驗 checkpoint／`scheduled_resume_at` 真的能跨「行程被殺掉」還原——**殺行程再起，比對狀態**，不是看程式碼推論。

---

## §5 收輪產物（清單，內容隨輪次進展回填）

- `docs/06_quality/CrossPlatform_R80_Scan_Findings.md` — 八維掃描與對抗式複驗結果
- `docs/06_quality/CrossPlatform_R80_Review.md` — 四方複審結論與逐筆 blocking 處置
- `docs/04_planning/R80_HANDOFF.md` — 交棒 R81
- `docs/06_quality/AutoSDD_Defect_Log.md` — 本輪缺陷列（單列 ≤ 700 bytes，詳情進具名證據檔）
