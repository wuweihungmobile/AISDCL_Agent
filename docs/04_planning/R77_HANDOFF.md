# R77 交棒任務書（跨平台相容性輪）

> **平台**：Windows 11 Pro build 26200 真機。工具側 PowerShell 引擎經本輪實測為 **pwsh 7.6.4**
> （非 5.1——三處文件的舊宣稱本輪已訂正）；`powershell.exe`(5.1) 是 schtasks Action 那一支。
> **本檔用途**：讓 R78 不必採信任何宣稱就能接手。凡「已通過」一律附當回合可重跑的指令。
> **體例沿用** `R76_HANDOFF.md`。

---

## 0. 🔴 R78 開場必讀的三件事

> 🔴 **R78 追加的體例（SA-04／SA-05 兩筆同型，故寫成規則而不是只修個案）：
> 交棒書凡述及「尚未做／還沒做／仍缺」的事，一律附**現查指令**，不寫快照結論。**
> 理由：交棒書記的是「收輪那一刻的狀態」，而讀者是在數天後、由別人動過的樹上讀它。
> 本節下方兩筆都被 R78 開場實查推翻（tag 其實已在遠端；`root_unittests` 其實已併進
> Windows nightly 的 STAGE-L），而照原文做的代價分別是「重推一次」與「每晚多跑一次
> 260〜313 秒的全套」。**「尚未做」是一個會過期的量測值，不是常數。**
> 機械物：`tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR78HandoffClaimsCarryLiveCommands`
> ——本節與「還沒做什麼」類章節內，凡帶「尚未／還沒／仍缺／未執行／沒跑」的條目，
> 必須附一段可執行的現查指令，或以 `<!-- handoff-claim-verified: WHY -->` 明說
> 「這件事沒有機械現查管道」。

1. **本輪四方複審一次都沒跑**（月度支出上限，`DEF-101-876`）。所有「已修畢」宣稱皆為
   **作者自證**，而本 repo 的成熟度判準 M3 明文「作者自證不計分」。**R78 第一件事是補跑複審。**
   現查該輪有無複審輸出檔（回空＝這一輪確實沒跑過）：`git ls-files 'docs/06_quality/*R77_Review*'`
   <!-- absent-if: CrossPlatform_R77_Review -->（**R90 收尾把這一筆從逃生口轉成真的證偽標的**：原標記的 WHY
   寫「無機械現查管道」，而 R90 §0.0c 的 M3 判定用的正是這條管道〔`ls docs/06_quality/ | grep 'R90_Review'`〕
   ⇒ 那個前提今天已不成立。實測佐證：真的跑過複審的 R78／R79／R80／R81／R85 五輪，`CrossPlatform_R<NN>_Review`
   這個字面在 tracked 內容裡各命中 4～8 支檔；R77 命中 0。）
2. **三個修復包完全未執行**：skipped 治理、承接稽核覆蓋率、依賴債。它們的規格書仍在
   `docs/06_quality/CrossPlatform_R77_Fix_Plan.md`（PKG-11-SKIPGOV／PKG-04-CROSSREF／PKG-12-DEBT），
   可直接照做。現查各包是否已落地：`git log --oneline --grep=PKG-11-SKIPGOV --grep=PKG-04-CROSSREF --grep=PKG-12-DEBT`
3. **30 支 `sdd-v0.NN` tag 已建但尚未推送**。下一輪若要談刪除凍結版目錄，**前提是先把 tag 推上去**
   （`git push origin 'refs/tags/sdd-v*'`）——兜底只存在本機等於沒有兜底。
   > 🔴 **R78 訂正（SA-04）：這一條在 R78 開場已為假，而它正是本節自列的「必讀」之一。**
   > 現查：`git ls-remote --tags origin 'refs/tags/sdd-v*'` 回 60 refs（annotated tag 每支
   > 兩列，`refs/tags/X` ＋ `refs/tags/X^{}`）＝**30 支已在遠端**；與 `git tag --list 'sdd-v*'`
   > 的 30 支逐名比對零差異。**兜底已經存在。**照原文再推一次雖然無害，但把「已完成」讀成
   > 「待辦」會讓 R78 誤判凍結版目錄那個決策的前提還沒到位。
   > 判斷「現在推了沒」請跑上面那兩行，不要讀這裡的結論。

---

## 1. 收輪時的實測狀態

> 🔴 **R78 請自己重跑，不要採信本表。**本 repo 已有判例：同一條指令、同一台機器、相隔十幾分鐘，
> rc 由 0 翻 1。

共用前綴：

```powershell
$r='D:\CursorProject\AISDCL_Agent'; $p="$r\.venv\Scripts\python.exe"
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
```

🔴 **讀 rc 不接管線**。本輪實測訂正了 R76 記載的方向：在 **pwsh 7.x** 上接管線會**保留前一個值**
（真 rc=3 可能讀成 0＝**真紅被讀成綠**），5.1 上寫 −1，加 `2>&1` 又會翻轉。**沒有方向可以憑記憶。**
現在有 PreToolUse 守衛會當場擋下這個形態（本輪它攔過收尾者一次）。

| 閘門 | 指令 | 收輪實測 |
|------|------|----------|
| 根層 unittest | `& $p "$r\tools\run_root_unittests.py"` | `Ran 2105 tests`／`OK (skipped=43)`／**rc=0** |
| LOC budget | `& $p "$r\AutoClaude\tools\check_loc_budget.py"` | **rc=0** |
| 缺陷帳本一致性 | `& $p "$r\tools\check_defect_log_crossref.py"` | **rc=0** |
| 帳本保全稽核 | `& $p "$r\tools\archive_defect_log.py" --check` | **rc=0** |
| ONBOARDING 基線 | `& $p "$r\tools\sync_onboarding_baselines.py" --check` | **rc=0** |
| ONBOARDING 指紋 | `& $p "$r\tools\sync_onboarding_baselines.py" --check-snapshot` | **rc=0** |
| 腳本對等 | `& $p "$r\tools\check_script_parity.py"` | **rc=0** |
| 薄殼守門 | `& $p "$r\tools\check_wrapper_thinness.py"` | **rc=0** |
| pytest 基線站點 | `& $p "$r\tools\check_pytest_baseline_sites.py"` | **rc=0** |
| GHA 版本一致性 | `& $p "$r\tools\check_gha_action_versions.py"` | **rc=0** |
| NTFS 路徑 | `& $p "$r\tools\check_ntfs_paths.py"` | **rc=0** |
| 排程漂移 | `& $p "$r\tools\check_scheduled_task_drift.py"` | `status=ok`／兩支任務各 7 項符合／**rc=0** |

**基線變動（乾淨 venv 回填，`pg_extras_state=absent` 已實查）**：

- AutoClaude pytest 出廠基線：**3919/224 → 3971/199**（skipped 少 25）
- 根層 unittest `MIN_TESTS`：**1979 → 2105**（🔴 依該行自身判準屬**中途值**，見 §4）
- provenance 新增兩欄 `interpreter`／`sdk-extra`，本次拿到真值（非佔位）

---

## 2. 掌舵者六題與三個系統問題的答案

### Q1｜全面掃描 Mac × Win11 相容性

十二維深掃，**139 筆原始發現 → 去重 127 → 49 筆 P0/P1 經對抗式複驗（存活 38、證偽 11）**。
逐筆見 `docs/06_quality/CrossPlatform_R77_Triage.md`。

🔴 **誠實劃界：mac 真機零覆蓋。**十二維一致自陳，mac 半邊全是讀碼與 POSIX 標準語意推論。

### Q2｜架構檢視與「拿掉不合理機制」

Architect 給出 **5 列減法清單**（每列附三段論：當初為何存在／理由還成立嗎／砍掉誰會發現）。
本輪落地 3 列，1 列由你拍板改為分階段，1 列判定不修：

| 減法標的 | 處置 |
|---|---|
| 護欄層**檔數**棘輪（把成長趕進巨檔，且被 LOC 工具當成「行數已有人管」的擋箭牌——該宣稱為假） | **已移除**，換 per-file 行數 shrink-only 棘輪（`DEF-101-875`） |
| LATEST 薄殼釘選第二套實作（4 表／2 檢查器／2 份 cross-lock） | **已併回**唯一實作 |
| UEP `≤4` 作為工程目標（ADR 自陳結構上不可達、空表 9 輪） | 降為政策懸置 |
| **Copy-on-Evolve 30 個凍結版目錄**（26,073 檔、92.7% 位元組重複、28 版永不被閘門執行） | **你拍板：先建 tag、本輪不刪**（見 §0-3） |
| hook 啟動 shim 15 份逐字複本 | **判定不修**——複驗證偽（立論前提「零綁定／mac 恆 127」被三道鎖與 setup-python 推翻），且動的是 PreToolUse deny 面 |

### Q3｜雙向落差（mac 開發 ↔ Windows 開發）

**實測攔截率：mac→Win 0/10（0%）、Win→mac 4/12（33%）。** <!-- xplat-rate-history: R77 動工前量測，見下方 R78 訂正 -->

> 🔴 **R78 訂正（ARCH-05）：上面那兩個數字是 R77 動工前的量測，不是收輪值。** 同一個 commit
> 落地的第六道判準把兩個方向都往上推了，而本節、M5 判準表、ADR 的 R77 列三處**全部**停在
> 修復前的值。方向是低報自己的成果，但代價落在下一輪：R78 一跑載具會拿到明顯較高的數字，
> 與這裡一比像「一輪暴衝」，於是去找一個不存在的原因。
> **前後對照**（這一輪到底動了多少）：動工前 mac→Win 0/10、Win→mac 4/12 <!-- xplat-rate-history: 動工前量測 -->
> ；**現查**（本行刻意追隨活值，不是某一輪的快照）mac→Win 5/10、Win→mac 8/12——R85／ARCH-02 把 `scan_foreign_exe_argv` 等四道判準接進 `_injection_criteria()` 後，Win→mac 由 6/12 <!-- xplat-rate-history: R78~R84 的 Win→mac 舊值，R85／ARCH-02 接線後已升，保留為沿革 --> 升到 8/12（b8-schtasks、b11-powershell-shell 兩題）。
> ⬆ 上面那一行**刻意不帶歷史標記**：它會被 `TestR78MaturityCriteriaSsot` 拿去與現場活值
> 逐字比對，一漂就紅——這是全樹唯一可以安心寫死攔截率的地方，因為它寫死不了。
> 其餘各處一律現跑：
> `python -m unittest tools.tests.test_platform_neutral_paths.TestXplatInjectionMatrix`
> （`setUpClass` 末行印 `[Xplat injection matrix] Win2mac=<hit>/<total> mac2Win=<hit>/<total>`）。
> 判準表已搬到 [`docs/06_quality/CrossPlatform_Maturity_Criteria.md`](../06_quality/CrossPlatform_Maturity_Criteria.md)。

🔴 R76 交棒書把這兩個方向**寫反了**，並誤診成「只有 mac 真機補得了」。實際上 mac→Win 的 0/10 <!-- xplat-rate-history: 同上，動工前量測 -->
**全是靜態掃描面缺口**（`os.getlogin`／`import pwd`／`os.fork`／`killpg+SIGKILL`／`os.symlink`／
`/tmp` 硬編／`chmod 0o755`／POSIX 路徑串接整類零判準），**在 Windows 上就補得起來也驗得到紅綠**；
需要 mac 真機的是執行期那一半。兩者不是同一件事。已訂正。

### Q4｜Windows 常犯低級錯誤的根因

**推翻了現行結論。**根 `CLAUDE.md` 那條「根因＝同時操作兩個 shell 的決策負荷」建立在 R71 的 n=8
樣本上、已被當成現行結論用了五輪。本輪以 n=36 重新歸因：

| 形態 | 占比 |
|---|---|
| **鎖存在但沒有鑑別力**（LOCKBLIND） | **44%** |
| 選錯載具（CARRIER，＝R71 的原結論） | **19%** |
| 其餘 | 37% |

真正的機械層根因是 **PowerShell 工具面零觀測者**：鐵律二（禁裸 `cd`）、鐵律四（宣稱先於查證）、
以及「在對的 shell 裡現寫一段沒驗過的碼」，這三類結構上不可能被任何機械物看見。
量化對照：**有觀測者的規則違規 1 次，沒觀測者的規則違規率 20~35%**——差別不在紀律寫得夠不夠嚴。

**你拍板「兩條都做」，兩條都已落地：**

1. **事後稽核器** `tools/probe/audit_session.py`——那些 inline 指令本來就逐字記在 session
   transcript 的 jsonl 裡、repo 內零消費者。這把「徹底解法」從「要改 Claude Code」降級成
   「寫一支讀 jsonl 的腳本」。
   🔴 邊界：逐字稿 untracked、機器本地、會被清 ⇒ **只能當每輪量測器，不能當 push 閘門**。
2. **PreToolUse 守衛** `.claude/hooks/lint_powershell_command.py`——只擋三件事（管線後讀 rc／
   裸 `cd`／裸 `bash` 跑 `.sh`），刻意極窄以免誤報導致機制被關掉。
   **它在本輪當場攔下收尾者一次**，是這一整條路線最直接的實證。

### Q5｜挖深與技術債

存量已量化：ruff 三棵樹 **815／62／3485**、依賴 15 筆無版本上限、三支孤兒腳本、`800` 這個值住兩個家。
🔴 **`ruff --fix` 判定不修**且理由已驗證：`I001` 會拆 import 增行而 AutoClaude LOC 總帳餘裕僅 142 行；
`F821` 是**真 bug 候選**須逐筆人工判（本輪就在護欄層抓到 3 筆真的 `F821`，是型別註記漏 import）；
在 CI 加全樹 ruff 閘門會讓 push 軌立刻紅 815 筆。屬需人工逐筆判定的多輪工作。

### Q6｜成熟度判準

M1~M6 六條**全部被指出判準本身有問題**，其中兩條特別刺眼：

- **M2（失實宣稱密度）結構上獎勵不做複審**——分子是「四方複審抓到的筆數」，所以不做複審＝完美達標。
  R72／R74 已實際發生兩次。本輪已改：該輪未做複審一律判 **N/A、禁記 0**；門檻改絕對值
  「連續三輪 ≤1 筆且無任何一筆 P1」。
- **M5（雙向注入攔截率）注入語料零落點** ⇒ 結構上不可逐輪比較。本輪已把語料變成可重跑的具名載具。

### S1｜`AutoClaude_Nightly` 還要跑多久、能不能加速

**不得退場**，而且它現在還**漏了 3 個 stage**（Windows 側缺 `root_unittests`，mac 側有）。

> 🔴 **R78 訂正（SA-05）：括號裡那句在寫下的當回合就已為假，而且照做會造成實害。**
> `root_unittests` 已由 **R77 自己**（`R77-04`）併進 Windows nightly 的 **Stage L**，
> 與 `local_ci_gate.ps1` 並列為該 stage 的第二道檢查（兩道 rc 各自留證、合併時真失敗優先
> 於 WARN）。R78 若照原文再加一次，每晚會**多跑一次 260〜313 秒的全套根層 unittest**。
> 現查（權威源是腳本自己，不是本檔）：
> `Select-String -Path AutoClaude\tools\run_local_nightly.ps1 -Pattern 'root_unittests'`
> ——命中即代表已接上；該檔第 17 行起的「反向去向帳目」也逐項寫著現況。
>
> **另外，「漏了 3 個」通篇沒有列出是哪三個**（＝一個無法被證偽的數字）。照該帳目逐項核對，
> 三項的**現況各不相同**，不是三個一樣的缺口：
> | # | 項目 | 現況 |
> |---|---|---|
> | 1 | 平台 smoke（mac `[1/4]` 跑 `macos_smoke_local.sh`） | **不是缺口**：Windows 側由獨立 schtasks 任務 `AutoClaude_WindowsSmoke` 觸發，與本檔**刻意解耦**（理由寫在該帳目內） |
> | 2 | 根層 unittest（mac `[2/4]`） | **已補**（R77-04，Stage L 第二道檢查） |
> | 3 | SDD 完整閘門（mac `[4/4]` 跑 `ci-gate.sh` 雙軌全套） | **仍是缺口**：本檔只有 `sdd-fsm-chaos`（chaos 子集），不含 v0.01/LATEST 雙軌 pytest 與 10 道 lint 硬閘 |
> ⇒ 真正還缺的是**第 3 項一項**。要不要補是另一個決策（那是最貴的一 stage），但別再用「3 個」這個數字。

觀察期四軌的終點由 **span** 綁住而非筆數（R76 收緊判準後的正確行為）：obs 最早 08-21、drift 08-22，
**前提是每晚不漏跑**。唯一合法槓桿是**提高命中率**——近 30 天實測只有 15/30 晚有進帳。
❌ 不得為了加速而放寬 `WINDOW_SPAN_MAX_FACTOR`／`STALENESS_MAX_DAYS`。

### S2｜`AutoClaude_WindowsSmoke` 與「提權指令」

**明確不得退場。**E1（雲端主通道活性）不只是「有一筆 billing 失敗」——本輪實測是
**19 天內 373/584 個 job 從未啟動**，比立案門檻差兩個數量級。

**你問的提權指令 ＝ `tools/install_windows_nightly.ps1` 的 install／uninstall 模式**
（`-Status`／`-WhatIf` 唯讀不需提權）。原因寫在該腳本第 267-268 行：註冊 **S4U 排程任務**需要
系統管理員權限，非提權時是 `Access is denied`；任務本身 RunLevel 維持 Limited，跑起來不需提權。
**現在不需要再提權**——當回合實測兩支任務 `present=true`／`drifts=[]`／`status=ok` rc=0。

### S3｜skipped 徹底解決

四組實測基線（本輪重量）：

| 環境 | passed / skipped |
|---|---|
| 出廠 cleanvenv（本輪回填後） | **3971 / 199** |
| 主 .venv（含 PG extras） | 4017 / 160 |
| nightly（四個 env 全設） | 4032 / 145 |
| 最佳可達 | 4108 / 69 |

另：根層 unittest skipped **43**（24 MAC-NATIVE／8 POSIX／11 未標籤）、SDD 側 11。
**真黑洞 33 支**（＋TLC 4~6）。

🔴 **PKG-11-SKIPGOV 這一包未執行**（額度），所以「輸出面把『未啟用』與『缺件』分開」那條
（`DEF-101-863`）本輪只前進了一部分。規格書在 fix plan 內可直接照做。

---

## 3. act ＋ Docker 本機驗證（你指定的雲端替代通道）

**核心修復**：`run_act_core.py` 原本把 workflow 寫死成模組常數 ⇒ 11 支 workflow 中只打得到 1 支。
現已加 `--workflow` 旗標 ＋ `RUN_ACT_WORKFLOW` 環境變數（給尚未轉旗標的 Windows 薄殼），
並新增**全庫 job 盤點**（`--list`）。

當回合盤點（25 個 job）：

| 類別 | 數量 |
|---|---|
| 🟡 act 可解析 | 12 |
| ❌ 帶 `services:`，act 0.2.89 panic（改走 `docker-compose.ci.yml`） | 3 |
| ❌ 無此 runner（macos ×2、windows ×2）＝**結構上零本機通道** | 4 |
| ⚠️ 無 push 觸發，需 `--event`（不加會零執行卻回 rc=0＝假綠） | 6 |

🔴 **真跑實測推翻了「✅ 可達」這個措辭**（`DEF-101-877`）：`root-infra` 的 dry-run rc=0，但**真跑到
第 3 個 step 就 rc=127**——該步需要 `pwsh`，而 act 預設映像沒裝，GitHub 的 ubuntu runner 自帶。
標記已改為「🟡 act 可解析」並固定印一行邊界說明。

**⇒ 給 R78 的判準：dry-run 全綠只證明 YAML 寫對了。要證明一支 job 通過，唯一憑證是該次執行自己的逐步輸出。**

---

## 4. 本輪最重要的一般化規則

### 4-1 🔴 agent 因外部錯誤中斷時，「失敗」不等於零產出

本輪有 5 個修復包因額度中斷而**回報遺失**，但**磁碟副作用已經落地**。其中 PKG-GUARD 的形態最危險：
判準函式、逃逸偵測都建好了，**唯獨凍結基準表沒建就斷** ⇒ 機制蓋好沒接電，引用它的測試全數 NameError。

**⇒ 收輪者必須以 `git status` 與閘門實跑核對真實狀態，不得採信 agent 的成功／失敗旗標。**
（同記憶 `workflow-agent-null-result-still-mutates`，本輪是它的第二次實證。）

### 4-2 🔴 移除一道鎖時，必須同時證明接手者有牙

檔數棘輪退場的理由是「它把病換了個地方長」，但如果不同時證明行數棘輪抓得到東西，
移除就是**淨損一道防護**。本輪為此補了一支專門的接手證明測試——而它立刻抓到收尾者自己的 +1 行。

### 4-3 🔴 「結構可達」不等於「已驗證」

act 盤點把三項結構事實都判對了（runner／services／事件），卻判不到「映像裡有沒有那支工具」。
措辭把「解析得動」寫成「✅ 可達」，讀者就會把它當成驗過了。**這是本 repo 反覆在治的那種宣稱。**

---

## 5. 交給 R78 的事（依優先序）

1. **補跑四方複審**（`DEF-101-876`）——本輪零複審，所有結論都是作者自證。
2. **補做三包**：PKG-11-SKIPGOV／PKG-04-CROSSREF／PKG-12-DEBT，規格在 fix plan 內。
3. **依複審結果重釘 `MIN_TESTS`**——本值依其自身判準屬中途值。
4. **推送 30 支 `sdd-v0.NN` tag**，然後才談凍結版目錄的刪除。
   ⚠️ 複驗已發現 `v0.02`／`v0.05` 正被兩支 bridge 測試執行、`autoclaude-ci.yml` 對那些路徑觸發
   ⇒ **直接全刪等於拆掉活閘門**。
5. **`AISDLC_SDD_INIT.md` 版號陳舊**：`v0.15`／`v0.30` 兩版的首行仍寫「v0.01 框架初始化」——
   Copy-on-Evolve 複製時版號沒跟著改（PKG-TAG 附帶發現，本輪未修）。
6. **mac 真機輪**：Q1 的 mac 半邊全是推論、Q3 的執行期那一半也只有 mac 真機補得了。

---

## 6. 禁止事項（R78 動工前先讀）

1. ❌ 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准跳過或註解掉失敗測試。
2. ❌ 不准為了讓數字好看而調高任何門檻／棘輪／體積上限。**GA 的 `WINDOW_SPAN_MAX_FACTOR` 與
   `STALENESS_MAX_DAYS` 明令不得放寬**；`_FROZEN_GUARD_LINES` 亦同（合法出口是「同一次變更內
   刪掉等量以上的行」，重釘須寫出淨額與理由）。
3. ❌ 不准把「尚未查核」寫成「已查核」。**本輪具體：四方複審未跑、三包未做、act 真跑只到第 3 步。**
4. ❌ **Windows 上禁用 Bash 工具**；禁裸 `cd`；**讀 rc 不接管線**（現在有 hook 會當場擋）。
5. ❌ 不准用 `--allow-pg-extras` 繞過 `sync_onboarding_baselines.py --write` 的拒跑。
   回填一律用乾淨 venv（只裝 `.[dev,notifications]`，`pg_extras_state` 須為 `absent`）。
6. ❌ 缺陷帳本列禁半形直線符號、列 ≤700 bytes、詳情進具名證據檔。
   **新建 `docs/06_quality/CrossPlatform_*.md` 必須同時登記進 `_GOVERNANCE_DOCS`**（本輪踩過一次）。
7. ❌ 新增 `tools/` 下的目錄時，記得補兩支 compat-CI 的 `paths:`（本輪踩過一次，`DEF-101-874`）。

---

## 7. R77 自身的失誤紀錄（本節是本檔的誠信擔保）

### 7-1 收尾者在壓縮註解時把一個不存在的輪號寫進程式碼

為了讓 `check_script_parity.py` 回到行數棘輪之內而重寫註解，順手把 `R99`（原文用來當「捏造的
遠未來輪號」的例子）留在註解裡 ⇒ 輪號鎖當場判紅。**形態＝「引述一個會被機器解析的字串時，
把它寫在會被解析的位置」**，與 R76 §7-4 完全同型，本 repo 第四次。改法是改寫成不出現該字面。

### 7-2 收尾者一次呼叫裡同時接管線與讀 `$LASTEXITCODE`

被本輪自己剛上線的 PreToolUse 守衛當場擋下。**這一筆不算負面**——它證明那條機制真的在守，
而且守的正是「有觀測者 vs 沒觀測者」那個量化差距所指的東西。記在這裡是因為它同時說明：
**收尾者本人也在那 20~35% 的違規率裡**，所以機械物不是給別人用的。

### 7-3 收尾者補的接手證明測試立刻抓到收尾者自己

補完 `_FROZEN_GUARD_LINES` 後寫的那支測試，第一次跑就報 `[成長] +1`——那 1 行正是收尾者
把註解從 2 行寫成 3 行造成的。照鎖給的合法出口壓回去，而非重釘基準。

### 7-4 🔴 本輪的最大結構性缺口不是失誤，但必須寫在同一節

**零四方複審。**這不是判斷失誤（是月度支出上限這個外部限制），但後果與失誤相同：
本檔§1 那張全綠表、§2 那些答案，**全部是作者自證**。R72／R74 已經各發生過一次，這是第三次。

⇒ **R78 讀本檔時，請把每一句「已修畢」都當成「待複驗」。**

---

## 8. 本檔取證邊界

| 內容 | 強度 |
|---|---|
| §1 十二道閘門的 rc、`MIN_TESTS`、基線數字 | **當回合真跑**（Windows 11 真機，收尾者本人） |
| §2 Q3 攔截率 0/10 與 4/12 | **引用**（PKG-01／PKG-09 的量測，收尾者未重跑）。<!-- xplat-rate-history: 動工前量測 --> 🔴 **R78 訂正：那是動工前值、且本欄自陳「未重跑」卻沒有任何人回頭跑** ⇒ 現值改為現跑 `TestXplatInjectionMatrix`，見 §2 Q3 的訂正框 |
| §2 Q4 的 n=36 歸因與 20~35% 違規率 | **引用**（Scan-W 的量測，收尾者未重跑） |
| §2 S1 的 obs 08-21／drift 08-22 | **引用** R76 的試算，本輪未重算 |
| §2 S2 的「19 天 373/584 job 未啟動」 | **引用**（PKG-05-CI 的量測） |
| §2 S3 四組 pytest 基線 | 出廠那一格＝**當回合真跑**（乾淨 venv 回填）；其餘三格**引用** |
| §3 act 盤點 25 job 與真跑 rc=127 | **當回合真跑**（收尾者本人，逐字輸出在 scratchpad） |
| §5 `v0.02`／`v0.05` 被 bridge 測試執行 | **引用**（複驗者的量測） |
| §7 四筆 | 7-1／7-2／7-3 為收尾者親身經歷；7-4 為事實陳述 |

> 🔴 **本檔寫於 commit 之前。**交棒書自己也在閘門掃描面內（`git grep --untracked`），
> R76 已因此弄紅過兩道根層鎖。收尾者在 commit 前會對「含本檔」的樹重跑一次閘門——
> 若 R78 發現本檔造成任何紅，那代表那次重跑沒做或做得不夠，請直接記在下一輪的失誤紀錄裡。
